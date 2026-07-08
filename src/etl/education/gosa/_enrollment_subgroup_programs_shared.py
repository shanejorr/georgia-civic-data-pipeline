"""Shared bronze layer for the two enrollment_by_subgroup_programs gold topics.

The GOSA "Enrollment by Subgroup / Programs" bronze (21 files, 2004-2024)
publishes BOTH 12 demographic-share columns and 9 program (count, percent)
pairs in a single wide row per (year, entity). The pipeline splits that
publication into two tidy-long gold topics that consume this module:

    * ``enrollment_demographic_shares`` — unpivots the 12 demographic-share
      columns plus the AYP-era ``met_ayp`` / ``improvement_status``
      categoricals (2004-2024).
    * ``enrollment_program_participation`` — unpivots the 9
      (count, percent) program pairs (2011-2024 only; pre-2011 bronze has
      no program columns).

This module owns everything the two topics must agree on byte-for-byte:
file reading (incl. the multi-sheet 2005-2008 Excel workbooks and the
mislabeled 2006 ``.csv`` that is really an XLS), era detection, year
derivation, detail-level derivation, ID parsing/zero-padding, ``ALL``
sentinel nulling, AYP categorical recoding, the 0-100 -> 0-1 metric
scaling, and all manifest bookkeeping for those steps.

Public interface (the two consumer transforms use ONLY these names):

    Constants
        BRONZE_DIR                  bronze directory (shared by both topics)
        DEMOGRAPHIC_PCT_COLUMNS     the 12 wide demographic-share columns
        PROGRAMS                    the 9 canonical program keys
        PROGRAM_COUNT_COLUMNS       ``count_<program>`` (Int64)
        PROGRAM_PCT_COLUMNS         ``pct_<program>`` (Float64, 0-1)
        WIDE_KEY_COLUMNS            year / district_code / school_code /
                                    detail_level
        WIDE_AYP_COLUMNS            met_ayp / improvement_status
        WIDE_STANDARD_COLUMNS       full wide-frame column order
        WIDE_TARGET_TYPES           dtype per wide column
        MET_AYP_MAP                 AYP recoding map (also used for enums)
        IMPROVEMENT_STATUS_MAP      improvement-status recoding map

    Function
        build_combined_wide_dataframe(manifest, min_year=None)
            Reads every bronze file (optionally skipping files whose
            filename year is below ``min_year``), returns ONE wide frame
            with WIDE_STANDARD_COLUMNS. Columns a given era does not
            publish are typed NULLs. Records read-loss, file info, bronze
            row counts, the 2004 junk-row filter, the 2022 charter
            reclassification, and the AYP categorical recodings against
            the manifest passed in.

Era map (collapsed from the 7 bronze eras in bronze-data-structure.md;
detection is by column signature, never by year range):

    * era_a_2004_2006      ``ID`` identifier, 15 AYP-era columns. 2004 is a
                           CSV; 2005/2006 are 3-sheet Excel workbooks
                           (2006 has a ``.csv`` extension but XLS magic
                           bytes — detected by content, not name).
    * era_a_2007_2009      identical but the identifier is ``SysSchoolID``.
                           2007/2008 are 3-sheet workbooks (2007's school
                           sheet is lowercase "School level" — lookup is
                           case-insensitive); 2009 is a single combined
                           school+district sheet with NO state row.
    * era_a_2010           abbreviated lowercase headers (A/B/H/N/U/W/L/
                           ED/S, ayp_status, ni_status); single sheet,
                           NO state row.
    * era_b_2011_2022      modern 35/37-column layout with DETAIL_LVL_DESC
                           and the 9 program pairs. MALE/FEMALE exist in
                           2011 and 2018-2022 but not 2012-2017.
    * era_c_2023_2024      era_b plus a leading ``#RPT_NAME`` column and the
                           ``ENROLL_PERCENT_*`` -> ``ENROLL_PCT_*`` rename —
                           EXCEPT ``ENROLL_PERCENT_EIP_K_5`` which GOSA never
                           renamed. TFS suppression expands to all 30 metric
                           columns.

Decisions this module owns (verified against bronze 2026-06-11):

    * **Asian/Pacific Islander (standards §5b).** Bronze publishes exactly
      6 race buckets in every one of the 21 years and never a separate
      Pacific Islander column. The integer-rounded state race sums (99-101)
      make the §5b math test inconclusive, so the structural argument
      governs: GOSA's 6-bucket scheme folds NHPI into "Asian"
      (pre-1997 OMB combined bucket), and §5b lists
      ``enrollment_by_subgroup_programs`` as a known combined-bucket
      source. The bronze ASIAN columns therefore map to
      ``pct_asian_pacific_islander``, never ``pct_asian``.
    * **2004 junk row.** The 2004 CSV carries one malformed row with
      ``ID='2'`` (no colon, every other cell NULL). It is dropped loudly
      and recorded via ``manifest.record_filtered``.
    * **2022 charter aggregates reclassified.** Two 2022 rows are labeled
      ``DETAIL_LVL_DESC='School'`` with ``INSTN_NUMBER='ALL'`` — they are
      the district aggregates of the single-school charter districts
      7830627 (Atlanta SMART Academy) and 7830636 (Northwest Classical
      Academy), which have no other District row. They are reclassified to
      ``district`` and recorded via ``manifest.record_reclassified``.
    * **Scaling.** Every bronze percentage is on the 0-100 scale in every
      era (structure doc); this module divides by 100 once so both topics
      land on the standards §4 0-1 scale identically. Values may slightly
      exceed 100 in bronze (ED max 132, SWD max 117 — GOSA artifacts where
      the served count exceeds the October FTE snapshot denominator);
      they are preserved, and the unit/range policy is each topic's call.
    * **TFS / blanks.** ``read_bronze_file`` (and the same
      ``SUPPRESSION_VALUES`` passed to the multi-sheet reader) nulls TFS
      and friends at read time; remaining empty strings become NULL via
      ``strict=False`` casts. Leading-dot decimals (".4", Era C) parse
      correctly to 0.4.
    * **No deduplication here.** Bronze repeats exist (2004: 109 exact
      duplicate rows; 2009: 4 duplicate-key groups that agree on every
      fact column) — dedup belongs at each topic's own grain, so each
      consumer runs its own collision guard + dedup after unpivoting.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import polars as pl

from src.utils.readers import (
    SUPPRESSION_VALUES,
    _detect_file_type,  # single source of magic-byte truth (2006 is XLS-as-.csv)
    list_bronze_files,
    read_bronze_file,
)
from src.utils.transformers import TransformManifest, detect_era_by_columns

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration shared by both topics
# =============================================================================

BRONZE_DIR = Path("data/bronze/education/gosa/enrollment_by_subgroup_programs")

# Bronze sentinel marking "aggregate row" in identifier columns (every era).
_ALL_SENTINEL = "ALL"

# Blank-ish sentinels in the AYP categorical columns ('.', '', ' ').
# 'N/A' is already nulled at read time via SUPPRESSION_VALUES.
_AYP_NULL_SENTINELS: dict[str, None] = {"": None, ".": None}

# The 12 wide demographic-share columns. The suffix after ``pct_`` is the
# canonical demographic key (src/utils/demographics.py). The ASIAN bronze
# columns map to the combined asian_pacific_islander bucket per §5b — see
# the module docstring.
DEMOGRAPHIC_PCT_COLUMNS: list[str] = [
    "pct_asian_pacific_islander",
    "pct_black",
    "pct_hispanic",
    "pct_native_american",
    "pct_multiracial",
    "pct_white",
    "pct_migrant",
    "pct_economically_disadvantaged",
    "pct_students_with_disabilities",
    "pct_english_learners",
    "pct_male",
    "pct_female",
]

# The 9 programs (Era B/C only), each published as a (count, pct) pair.
# The key doubles as the canonical ``program`` value for the program topic.
PROGRAMS: list[str] = [
    "remedial_gr_6_8",
    "eip_k_5",
    "remedial_gr_9_12",
    "special_ed_k_12",
    "esol",
    "special_ed_pk",
    "vocation_9_12",
    "alt_programs",
    "gifted",
]
PROGRAM_COUNT_COLUMNS: list[str] = [f"count_{p}" for p in PROGRAMS]
PROGRAM_PCT_COLUMNS: list[str] = [f"pct_{p}" for p in PROGRAMS]

WIDE_KEY_COLUMNS: list[str] = ["year", "district_code", "school_code", "detail_level"]
WIDE_AYP_COLUMNS: list[str] = ["met_ayp", "improvement_status"]
WIDE_STANDARD_COLUMNS: list[str] = (
    WIDE_KEY_COLUMNS
    + WIDE_AYP_COLUMNS
    + DEMOGRAPHIC_PCT_COLUMNS
    + PROGRAM_COUNT_COLUMNS
    + PROGRAM_PCT_COLUMNS
)
WIDE_TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "detail_level": pl.Utf8,
    "met_ayp": pl.Utf8,
    "improvement_status": pl.Utf8,
    **{c: pl.Float64 for c in DEMOGRAPHIC_PCT_COLUMNS},
    **{c: pl.Int64 for c in PROGRAM_COUNT_COLUMNS},
    **{c: pl.Float64 for c in PROGRAM_PCT_COLUMNS},
}

# AYP categorical recoding maps (Era A only; columns vanish from 2011 on).
# Bronze inventory verified across 2004-2010: Yes/No (plus blanks / N/A) and
# the five improvement codes (plus '.', ' ', '' sentinels -> NULL).
MET_AYP_MAP: dict[str, str] = {
    "Yes": "yes",
    "No": "no",
}
IMPROVEMENT_STATUS_MAP: dict[str, str] = {
    "ADEQ": "adeq",
    "ADEQ_DNM": "adeq_dnm",
    "DIST": "dist",
    "NI": "ni",
    "NI_AYP": "ni_ayp",
}


# =============================================================================
# Era detection (column signatures, most-specific first)
# =============================================================================

_ERA_C = "era_c_2023_2024"
_ERA_B = "era_b_2011_2022"
_ERA_A_2010 = "era_a_2010_abbreviated"
_ERA_A_0709 = "era_a_2007_2009"
_ERA_A_0406 = "era_a_2004_2006"

_ERA_SIGNATURES: dict[str, list[str]] = {
    # Era C adds the #RPT_NAME column on top of the Era B layout.
    _ERA_C: ["#RPT_NAME", "DETAIL_LVL_DESC", "LONG_SCHOOL_YEAR"],
    _ERA_B: ["DETAIL_LVL_DESC", "INSTN_NUMBER", "SCHOOL_DSTRCT_CD", "LONG_SCHOOL_YEAR"],
    # 2010 abbreviates every header (lowercase names + single-letter races).
    _ERA_A_2010: ["SysSchoolID", "systemname", "ayp_status", "ni_status"],
    _ERA_A_0709: ["SysSchoolID", "System Name", "Met AYP"],
    _ERA_A_0406: ["ID", "System Name", "Met AYP"],
}

_ERA_A_ALL = {_ERA_A_2010, _ERA_A_0709, _ERA_A_0406}


# -----------------------------------------------------------------------------
# Era A renames: bronze column -> wide working name (suffix _raw = pre-scale).
# -----------------------------------------------------------------------------
# 2004-2009 share one 15-column schema; only the identifier name differs
# (``ID`` vs ``SysSchoolID``) and ``MultiracialPercentage of Enrollment``
# carries GOSA's missing-space typo in every 2004-2009 file.
_ERA_A_RENAME_2004_2009: dict[str, str] = {
    "ID": "_bronze_id",
    "SysSchoolID": "_bronze_id",
    "Met AYP": "_met_ayp_raw",
    "Improvement Status": "_improvement_status_raw",
    "Asian Percentage of Enrollment": "_raw_pct_asian_pacific_islander",
    "Black Percentage of Enrollment": "_raw_pct_black",
    "Hispanic Percentage of Enrollment": "_raw_pct_hispanic",
    "Native American Percentage of Enrollment": "_raw_pct_native_american",
    # GOSA header typo: no space between "Multiracial" and "Percentage".
    "MultiracialPercentage of Enrollment": "_raw_pct_multiracial",
    "White Percentage of Enrollment": "_raw_pct_white",
    "Limited English Proficient Percentage of Enrollment": (
        "_raw_pct_english_learners"
    ),
    "Economically Disadvantaged Percentage of Enrollment": (
        "_raw_pct_economically_disadvantaged"
    ),
    "With Disabilities Percentage of Enrollment": (
        "_raw_pct_students_with_disabilities"
    ),
}

# 2010 abbreviates everything; same targets so downstream logic is uniform.
_ERA_A_RENAME_2010: dict[str, str] = {
    "SysSchoolID": "_bronze_id",
    "ayp_status": "_met_ayp_raw",
    "ni_status": "_improvement_status_raw",
    "A": "_raw_pct_asian_pacific_islander",
    "B": "_raw_pct_black",
    "H": "_raw_pct_hispanic",
    "N": "_raw_pct_native_american",
    "U": "_raw_pct_multiracial",
    "W": "_raw_pct_white",
    "L": "_raw_pct_english_learners",
    "ED": "_raw_pct_economically_disadvantaged",
    "S": "_raw_pct_students_with_disabilities",
}

# Era A name/grades columns: dimension attributes, dropped from the wide frame.
_ERA_A_DROP_COLUMNS: dict[str, list[str]] = {
    _ERA_A_0406: ["System Name", "School Name", "Grades"],
    _ERA_A_0709: ["System Name", "School Name", "Grades"],
    _ERA_A_2010: ["systemname", "schoolname", "graderange"],
}


# -----------------------------------------------------------------------------
# Era B/C rename: bronze column -> wide gold name.
# -----------------------------------------------------------------------------
# Listed literally (both PERCENT and PCT spellings) so the EIP quirk is
# explicit: GOSA renamed the 12 demographic/sex columns to ENROLL_PCT_* in
# Era C but never renamed ENROLL_PERCENT_EIP_K_5 — a mechanical
# _PERCENT_ -> _PCT_ substitution would corrupt that column.
_ERA_BC_RENAME: dict[str, str] = {
    # Demographic shares (Era B spelling, then Era C spelling).
    "ENROLL_PERCENT_ASIAN": "pct_asian_pacific_islander",
    "ENROLL_PCT_ASIAN": "pct_asian_pacific_islander",
    "ENROLL_PERCENT_BLACK": "pct_black",
    "ENROLL_PCT_BLACK": "pct_black",
    "ENROLL_PERCENT_HISPANIC": "pct_hispanic",
    "ENROLL_PCT_HISPANIC": "pct_hispanic",
    "ENROLL_PERCENT_NATIVE": "pct_native_american",
    "ENROLL_PCT_NATIVE": "pct_native_american",
    "ENROLL_PERCENT_MULTIRACIAL": "pct_multiracial",
    "ENROLL_PCT_MULTIRACIAL": "pct_multiracial",
    "ENROLL_PERCENT_WHITE": "pct_white",
    "ENROLL_PCT_WHITE": "pct_white",
    "ENROLL_PERCENT_MIGRANT": "pct_migrant",
    "ENROLL_PCT_MIGRANT": "pct_migrant",
    "ENROLL_PERCENT_ED": "pct_economically_disadvantaged",
    "ENROLL_PCT_ED": "pct_economically_disadvantaged",
    "ENROLL_PERCENT_SWD": "pct_students_with_disabilities",
    "ENROLL_PCT_SWD": "pct_students_with_disabilities",
    "ENROLL_PERCENT_LEP": "pct_english_learners",
    "ENROLL_PCT_LEP": "pct_english_learners",
    "ENROLL_PERCENT_MALE": "pct_male",
    "ENROLL_PCT_MALE": "pct_male",
    "ENROLL_PERCENT_FEMALE": "pct_female",
    "ENROLL_PCT_FEMALE": "pct_female",
    # Program counts (names stable across Era B/C).
    "ENROLL_COUNT_REMEDIAL_GR_6_8": "count_remedial_gr_6_8",
    "ENROLL_COUNT_EIP_K_5": "count_eip_k_5",
    "ENROLL_COUNT_REMEDIAL_GR_9_12": "count_remedial_gr_9_12",
    "ENROLL_COUNT_SPECIAL_ED_K12": "count_special_ed_k_12",
    "ENROLL_COUNT_ESOL": "count_esol",
    "ENROLL_COUNT_SPECIAL_ED_PK": "count_special_ed_pk",
    "ENROLL_COUNT_VOCATION_9_12": "count_vocation_9_12",
    "ENROLL_COUNT_ALT_PROGRAMS": "count_alt_programs",
    "ENROLL_COUNT_GIFTED": "count_gifted",
    # Program percentages. ENROLL_PERCENT_EIP_K_5 keeps its PERCENT spelling
    # in every era (the one exception to the Era C rename).
    "ENROLL_PCT_REMEDIAL_GR_6_8": "pct_remedial_gr_6_8",
    "ENROLL_PERCENT_EIP_K_5": "pct_eip_k_5",
    "ENROLL_PCT_REMEDIAL_GR_9_12": "pct_remedial_gr_9_12",
    "ENROLL_PCT_SPECIAL_ED_K12": "pct_special_ed_k_12",
    "ENROLL_PCT_ESOL": "pct_esol",
    "ENROLL_PCT_SPECIAL_ED_PK": "pct_special_ed_pk",
    "ENROLL_PCT_VOCATION_9_12": "pct_vocation_9_12",
    "ENROLL_PCT_ALT_PROGRAMS": "pct_alt_programs",
    "ENROLL_PCT_GIFTED": "pct_gifted",
}

# Wide demographic columns that must exist after the Era B/C rename in EVERY
# 2011+ file (the sex pair is legitimately absent 2012-2017, and migrant is
# always present 2011+; a miss here means a silent rename bug — §4.1).
_ERA_BC_REQUIRED_DEMO: set[str] = {
    "pct_asian_pacific_islander",
    "pct_black",
    "pct_hispanic",
    "pct_native_american",
    "pct_multiracial",
    "pct_white",
    "pct_migrant",
    "pct_economically_disadvantaged",
    "pct_students_with_disabilities",
    "pct_english_learners",
}

# Multi-sheet workbooks (2005-2008): sheet name (lowercased) -> detail level.
_SHEET_TO_LEVEL: dict[str, str] = {
    "school level": "school",
    "system level": "district",
    "state level": "state",
}


# =============================================================================
# Small helpers
# =============================================================================


def _year_from_filename(name: str) -> int:
    """Parse the trailing 4-digit year from ``..._YYYY.{csv,xls,xlsx}``.

    Strict on purpose: a rename of the bronze files should fail loudly, not
    fall back to a fuzzy regex match.
    """
    tail = Path(name).stem.rsplit("_", 1)[-1]
    if len(tail) != 4 or not tail.isdigit():
        raise ValueError(f"Cannot parse year from bronze filename: {name!r}")
    return int(tail)


def _ending_year_from_long_school_year(value: str) -> int:
    """``'2023-24'`` -> 2024 (the ending calendar year of the school year)."""
    value = value.strip()
    if len(value) != 7 or value[4] != "-":
        raise ValueError(f"Unexpected LONG_SCHOOL_YEAR value: {value!r}")
    return (int(value[:4]) // 100) * 100 + int(value[5:])


def _null_if_all(col: pl.Expr) -> pl.Expr:
    """NULL out the ``ALL`` aggregate sentinel in an identifier column."""
    return pl.when(col == _ALL_SENTINEL).then(None).otherwise(col)


def _format_district_code(col: pl.Expr) -> pl.Expr:
    """Zero-pad district codes to width 3 (no-op for 7-digit charter codes)."""
    return col.cast(pl.Utf8).str.strip_chars().str.zfill(3)


def _format_school_code(col: pl.Expr) -> pl.Expr:
    """Zero-pad school codes to width 4 (bronze publishes 3-4 digit codes)."""
    return col.cast(pl.Utf8).str.strip_chars().str.zfill(4)


def _clean_ayp_sentinels(col: pl.Expr) -> pl.Expr:
    """Collapse AYP blank-ish sentinels ('', ' ', '.') to real NULLs.

    Applied before ``replace_strict`` so the recoding maps only enumerate
    real codes ('N/A' is already NULL via read-time SUPPRESSION_VALUES).
    """
    return col.cast(pl.Utf8).str.strip_chars().replace(_AYP_NULL_SENTINELS)


def _pad_missing_wide_columns(df: pl.DataFrame, year: int, era: str) -> pl.DataFrame:
    """Add typed-NULL columns for every wide column the era lacks (§4.2).

    Each fallback is logged: for Era A the absences are structural (no
    program columns, no migrant/male/female); for Era B 2012-2017 only the
    sex pair is absent. Anything else missing would indicate a rename bug —
    the per-era required-column checks raise before this point.
    """
    exprs: list[pl.Expr] = []
    missing: list[str] = []
    for col in WIDE_STANDARD_COLUMNS:
        if col not in df.columns:
            exprs.append(pl.lit(None).cast(WIDE_TARGET_TYPES[col]).alias(col))
            missing.append(col)
    if missing:
        logger.info(
            "Year %d (%s): %d wide column(s) not published by this era, "
            "emitted as typed NULLs: %s",
            year,
            era,
            len(missing),
            missing,
        )
        df = df.with_columns(exprs)
    return df


def _read_multisheet_excel(workbook: pd.ExcelFile, name: str) -> pl.DataFrame:
    """Read a 2005-2008 level-sheet workbook into one tagged frame.

    ``read_bronze_file`` reads only the first sheet, which would silently
    drop the district and state rollups, so the three level sheets are read
    explicitly (case-insensitively — 2007 ships 'School level') and tagged
    with ``_detail_level_from_sheet``. Empty placeholder sheets are skipped.
    The already-open ``pd.ExcelFile`` is reused so the workbook is parsed
    only once.
    """
    frames: list[pl.DataFrame] = []
    for sheet in workbook.sheet_names:
        level = _SHEET_TO_LEVEL.get(sheet.lower().strip())
        if level is None:
            continue
        pdf = workbook.parse(
            sheet_name=sheet,
            dtype=str,
            na_values=list(SUPPRESSION_VALUES),
        )
        if pdf.empty:
            continue
        frames.append(
            pl.from_pandas(pdf).with_columns(
                pl.lit(level).alias("_detail_level_from_sheet")
            )
        )
    if not frames:
        raise ValueError(f"No readable level sheets in {name}")
    return pl.concat(frames, how="diagonal_relaxed")


def _read_bronze(path: Path) -> tuple[pl.DataFrame, dict]:
    """Read one bronze file, routing multi-sheet workbooks explicitly.

    Returns ``(df, loss_dict)``. File type comes from magic bytes (the 2006
    file is an XLS with a ``.csv`` extension). Excel reads have
    ``raw == parsed`` by construction (pandas loads whole sheets), so the
    loss dict for the multi-sheet path is parity-by-construction too.
    """
    file_type = _detect_file_type(path)
    if file_type in ("xls", "xlsx"):
        engine = "openpyxl" if file_type == "xlsx" else "xlrd"
        workbook = pd.ExcelFile(path, engine=engine)
        sheet_keys = {s.lower().strip() for s in workbook.sheet_names}
        if _SHEET_TO_LEVEL.keys() & sheet_keys:
            df = _read_multisheet_excel(workbook, path.name)
            return df, {
                "raw_rows": df.height,
                "parsed_rows": df.height,
                "format": file_type,
            }
    # Single-sheet Excel (2009 data is in the first sheet; 2010's only sheet
    # is Sheet3; 2012's only sheet is 'Export Worksheet') and all CSVs.
    # infer_schema_length=0 forces all-Utf8 so zero-padded codes and
    # sentinel strings survive (§4.3b); every cast downstream is explicit.
    return read_bronze_file(path, infer_schema_length=0, return_loss=True)


# =============================================================================
# Era A (2004-2010)
# =============================================================================


def _transform_era_a(
    df: pl.DataFrame,
    year: int,
    era: str,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Transform one AYP-era file (2004-2010) to the common wide schema."""
    rename_map = _ERA_A_RENAME_2010 if era == _ERA_A_2010 else _ERA_A_RENAME_2004_2009

    # Rename-coverage check (§4.1): every era-A metric/AYP column must be
    # present (identifier aliases checked separately) or the year would
    # silently lose a column.
    identifier_aliases = {"ID", "SysSchoolID"}
    missing = [
        c for c in rename_map if c not in identifier_aliases and c not in df.columns
    ]
    if not identifier_aliases & set(df.columns):
        raise ValueError(f"Year {year} ({era}): no ID/SysSchoolID column found")
    if missing:
        raise ValueError(
            f"Year {year} ({era}): bronze is missing expected columns {missing}"
        )

    df = df.rename({k: v for k, v in rename_map.items() if k in df.columns})
    df = df.drop([c for c in _ERA_A_DROP_COLUMNS[era] if c in df.columns])

    if "_detail_level_from_sheet" not in df.columns:
        # 2004 carries one malformed junk row (ID='2', no colon, all other
        # cells NULL) — drop it loudly and record the filter.
        malformed = df.filter(~pl.col("_bronze_id").str.contains(":"))
        if malformed.height > 0:
            logger.warning(
                "Year %d: dropping %d malformed identifier row(s) (no colon): %s",
                year,
                malformed.height,
                malformed["_bronze_id"].to_list(),
            )
            manifest.record_filtered(
                year, malformed.height, "malformed_identifier_junk_row"
            )
            df = df.filter(pl.col("_bronze_id").str.contains(":"))

    # --- Scale the 9 Era-A demographic shares to the 0-1 scale (§4) -------
    # strict=False: any residual non-numeric string becomes NULL.
    # One single-expression with_columns per column, applied BEFORE any
    # multi-expression with_columns: polars preserves the per-sheet chunk
    # layout from the 2005-2008 multisheet concat through single-expression
    # calls, so the 1-row State Level chunk is divided by the scalar
    # true-division kernel. A multi-expression call rechunks the frame
    # first, and the SIMD kernel multiplies by the reciprocal instead,
    # flipping e.g. 47/100 by 1 ulp (0x1.e147ae147ae15p-2 vs ...14p-2) —
    # which would silently change parquet bytes for state rows.
    for gold in DEMOGRAPHIC_PCT_COLUMNS:
        raw = f"_raw_{gold}"
        if raw in df.columns:
            df = df.with_columns(
                (pl.col(raw).cast(pl.Float64, strict=False) / 100.0).alias(gold)
            )

    # --- Detail level: sheet tag (2005-2008) or identifier pattern --------
    if "_detail_level_from_sheet" in df.columns:
        df = df.rename({"_detail_level_from_sheet": "detail_level"})
    else:
        # ALL:ALL = state; NNN:ALL = district; NNN:school = school.
        # 2009/2010 publish no state row — the pattern simply never fires.
        df = df.with_columns(
            pl.when(pl.col("_bronze_id") == f"{_ALL_SENTINEL}:{_ALL_SENTINEL}")
            .then(pl.lit("state"))
            .when(pl.col("_bronze_id").str.ends_with(f":{_ALL_SENTINEL}"))
            .then(pl.lit("district"))
            .otherwise(pl.lit("school"))
            .alias("detail_level")
        )

    # --- Split <SystemID>:<SchoolID>, null ALL sentinels, zero-pad --------
    id_parts = pl.col("_bronze_id").str.split_exact(":", 1)
    df = df.with_columns(
        _format_district_code(_null_if_all(id_parts.struct.field("field_0"))).alias(
            "district_code"
        ),
        _format_school_code(_null_if_all(id_parts.struct.field("field_1"))).alias(
            "school_code"
        ),
        pl.lit(year).cast(pl.Int32).alias("year"),
        # AYP sentinel cleanup ('', ' ', '.' -> NULL; 'N/A' nulled at read).
        _clean_ayp_sentinels(pl.col("_met_ayp_raw")).alias("_met_ayp_clean"),
        _clean_ayp_sentinels(pl.col("_improvement_status_raw")).alias(
            "_improvement_status_clean"
        ),
    )

    # --- Recode AYP categoricals + record against the manifest ------------
    df = df.with_columns(
        pl.col("_met_ayp_clean")
        .replace_strict(MET_AYP_MAP, default=None)
        .alias("met_ayp"),
        pl.col("_improvement_status_clean")
        .replace_strict(IMPROVEMENT_STATUS_MAP, default=None)
        .alias("improvement_status"),
    )
    manifest.record_categorical(
        column="met_ayp",
        map_dict=MET_AYP_MAP,
        bronze_series=df["_met_ayp_clean"],
        gold_series=df["met_ayp"],
    )
    manifest.record_categorical(
        column="improvement_status",
        map_dict=IMPROVEMENT_STATUS_MAP,
        bronze_series=df["_improvement_status_clean"],
        gold_series=df["improvement_status"],
    )

    df = _pad_missing_wide_columns(df, year, era)
    return df.select(WIDE_STANDARD_COLUMNS)


# =============================================================================
# Era B/C (2011-2024)
# =============================================================================


def _transform_era_bc(
    df: pl.DataFrame,
    year: int,
    era: str,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Transform one modern file (2011-2024) to the common wide schema."""
    if "#RPT_NAME" in df.columns:
        # Era-C-only constant ('Enrollment_by_Subgroup_Metrics') — no signal.
        df = df.drop("#RPT_NAME")

    # Cross-check the filename year against LONG_SCHOOL_YEAR (source drift
    # between the two would mis-partition an entire year).
    long_year = df["LONG_SCHOOL_YEAR"].drop_nulls()[0]
    computed = _ending_year_from_long_school_year(long_year)
    if computed != year:
        raise ValueError(
            f"Year {year}: LONG_SCHOOL_YEAR {long_year!r} ends in {computed} — "
            f"filename/source drift"
        )

    df = df.rename({k: v for k, v in _ERA_BC_RENAME.items() if k in df.columns})

    # Rename-coverage check (§4.1): nothing ENROLL_* may survive the rename,
    # and the 10 always-published demographic columns must all be present.
    leftover = [c for c in df.columns if c.startswith("ENROLL_")]
    if leftover:
        raise ValueError(
            f"Year {year} ({era}): unmapped bronze metric columns {leftover}"
        )
    missing_demo = _ERA_BC_REQUIRED_DEMO - set(df.columns)
    if missing_demo:
        raise ValueError(
            f"Year {year} ({era}): demographic columns missing after rename: "
            f"{sorted(missing_demo)}"
        )
    if "pct_male" not in df.columns:
        # Documented era gap: the sex pair exists in 2011 and 2018+ only.
        logger.info(
            "Year %d (%s): sex columns not published (2012-2017 gap) — "
            "pct_male/pct_female will be typed NULLs",
            year,
            era,
        )

    # --- Detail level + the 2022 charter-aggregate repair ------------------
    # Two 2022 rows are labeled School but carry INSTN_NUMBER='ALL': the
    # district aggregates of single-school charter districts 7830627/7830636
    # (verified: no other District row exists for either code, and the row
    # values duplicate the school row). Reclassify to district so they don't
    # land in a schools partition with NULL school_code.
    reclassify = (pl.col("DETAIL_LVL_DESC").str.to_lowercase() == "school") & (
        pl.col("INSTN_NUMBER") == _ALL_SENTINEL
    )
    n_reclassified = df.filter(reclassify).height
    if n_reclassified > 0:
        manifest.record_reclassified(
            year,
            n_reclassified,
            "school_labeled_rows_with_INSTN_NUMBER_ALL_reclassified_to_district"
            "_single_school_charter_aggregates",
        )
    df = df.with_columns(
        pl.when(reclassify)
        .then(pl.lit("district"))
        .otherwise(pl.col("DETAIL_LVL_DESC").str.to_lowercase())
        .alias("detail_level")
    )

    # --- Geography keys: null ALL sentinels, zero-pad ----------------------
    df = df.with_columns(
        _format_district_code(_null_if_all(pl.col("SCHOOL_DSTRCT_CD"))).alias(
            "district_code"
        ),
        _format_school_code(_null_if_all(pl.col("INSTN_NUMBER"))).alias("school_code"),
        pl.lit(year).cast(pl.Int32).alias("year"),
        # AYP columns do not exist from 2011 on (program retired).
        pl.lit(None).cast(pl.Utf8).alias("met_ayp"),
        pl.lit(None).cast(pl.Utf8).alias("improvement_status"),
    )

    # --- Cast + scale metrics (§4): percentages /100, counts Int64 ---------
    # strict=False nulls residual non-numeric strings (TFS already nulled at
    # read; '' from quoted-empty CSV cells nulls here).
    df = df.with_columns(
        [
            (pl.col(c).cast(pl.Float64, strict=False) / 100.0).alias(c)
            for c in DEMOGRAPHIC_PCT_COLUMNS + PROGRAM_PCT_COLUMNS
            if c in df.columns
        ]
        + [
            pl.col(c).cast(pl.Int64, strict=False).alias(c)
            for c in PROGRAM_COUNT_COLUMNS
            if c in df.columns
        ]
    )

    df = _pad_missing_wide_columns(df, year, era)
    return df.select(WIDE_STANDARD_COLUMNS)


# =============================================================================
# Public entry point
# =============================================================================


def build_combined_wide_dataframe(
    manifest: TransformManifest,
    *,
    min_year: int | None = None,
) -> pl.DataFrame:
    """Read all bronze files into one wide frame with WIDE_STANDARD_COLUMNS.

    Args:
        manifest: The consuming topic's manifest. Receives read-loss events,
            file records, bronze row counts, the 2004 junk-row filter, the
            2022 reclassification, and (when Era A files are read) the
            ``met_ayp`` / ``improvement_status`` categorical recordings.
        min_year: When set, bronze files whose filename year is below this
            are skipped entirely (not read, not recorded). The program topic
            passes 2011 because pre-2011 bronze publishes no program columns;
            the demographic topic reads everything.

    Returns:
        One row per bronze entity row (duplicates included — each consumer
        dedups at its own grain), with every era-missing column as a typed
        NULL. Percentage columns are on the 0-1 scale; counts are Int64.
    """
    frames: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR):
        year = _year_from_filename(path.name)
        if min_year is not None and year < min_year:
            logger.info(
                "Skipping %s (year %d < min_year %d — era publishes no "
                "columns this topic consumes)",
                path.name,
                year,
                min_year,
            )
            continue

        df, loss = _read_bronze(path)
        manifest.record_read_loss(
            year, path.name, loss["raw_rows"], loss["parsed_rows"]
        )

        era = detect_era_by_columns(df, _ERA_SIGNATURES)
        if era is None:
            raise ValueError(
                f"{path.name}: no era signature matched columns {df.columns}"
            )
        manifest.record_file(path, year, era, df.height, df.columns)
        manifest.record_bronze(year, df.height)
        logger.info(
            "Year %d: read %s rows from %s (%s)",
            year,
            f"{df.height:,}",
            path.name,
            era,
        )

        if era in _ERA_A_ALL:
            frames.append(_transform_era_a(df, year, era, manifest))
        else:
            frames.append(_transform_era_bc(df, year, era, manifest))

    if not frames:
        raise RuntimeError(f"No bronze data transformed from {BRONZE_DIR}")

    # Every per-era frame is already select(WIDE_STANDARD_COLUMNS) with
    # WIDE_TARGET_TYPES dtypes, so plain vertical concat is schema-safe.
    combined = pl.concat(frames, how="vertical")
    logger.info("Combined wide frame: %s rows", f"{combined.height:,}")
    return combined


__all__ = [
    "BRONZE_DIR",
    "DEMOGRAPHIC_PCT_COLUMNS",
    "IMPROVEMENT_STATUS_MAP",
    "MET_AYP_MAP",
    "PROGRAMS",
    "PROGRAM_COUNT_COLUMNS",
    "PROGRAM_PCT_COLUMNS",
    "WIDE_AYP_COLUMNS",
    "WIDE_KEY_COLUMNS",
    "WIDE_STANDARD_COLUMNS",
    "WIDE_TARGET_TYPES",
    "build_combined_wide_dataframe",
]
