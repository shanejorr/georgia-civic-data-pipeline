"""Transform bronze attendance_dashboard files into gold fact tables.

Source: Georgia Insights (GaDOE) Attendance Dashboard — one xlsx per school
year, 2018-2025. For every Georgia public school, district, and the state,
reports three closely related absenteeism metrics plus the enrollment
denominator, broken out by grade level and by demographic subgroup:

- ``chronically_absent_rate`` — share of students absent >=10%% of their
  enrolled days (the federal chronic-absenteeism definition).
- ``average_daily_absenteeism_rate`` — total absent-days / total
  enrolled-days.
- ``average_daily_attendance_rate`` — total present-days / total
  enrolled-days (the complement of the absenteeism rate).
- ``num_students`` — the enrollment denominator; never suppressed.

Design decisions (every invariant re-verified against THIS topic's 8 bronze
files during authoring — see bronze-data-structure.md):

- **Single era, three data sheets per file.** All 8 files share an identical
  11-column layout across three parallel data sheets (``All Students``,
  ``Grade Level``, ``Subgroups``) that are vertically concatenated; the
  ``Read Me`` sheet is documentation only and is never ingested. The shared
  ``read_bronze_file`` reads only a workbook's first sheet (which here is
  ``Read Me``), so sheet reading goes through a local pandas
  ``read_excel(sheet_name=[...])`` helper using the same ``dtype=str`` +
  ``SUPPRESSION_VALUES`` conventions as the shared XLSX path. Excel reads
  load whole sheets (nothing is dropped at parse time), so read-loss
  raw == parsed by construction.

- **Grade-in-demographic policy** (per ``src/etl/education/CLAUDE.md``):
  bronze publishes grade values (``Kindergarten``, ``Grade 1``..``Grade 12``)
  as one slice among many demographic-style breakouts in the
  ``Group``/``Subgroup`` columns, alongside race/ethnicity, gender, and
  special populations. Grade is therefore kept INSIDE the ``demographic``
  column (long-form keys ``kindergarten``, ``grade_1``..``grade_12``) rather
  than torn into a separate ``grade_level`` axis — a separate axis would
  force fabricating cells the source does not measure (e.g. grade_3 x black).

- **Asian / Pacific Islander is the combined bucket (§5b).** Bronze
  publishes the explicit label ``Asian/Pacific Islander`` (pre-1997 OMB
  6-bucket race convention) and never a separate Asian or Pacific Islander
  row in any year. The label canonicalizes to ``asian_pacific_islander`` via
  the shared aliases — no topic-local remap is needed and the split
  ``asian`` / ``pacific_islander`` keys are never emitted.

- **No demographic collisions.** The 28 bronze ``Subgroup`` labels map 1:1
  onto 28 distinct canonical demographic keys (verified across all 8 years —
  the lexicon is identical in every file), so
  ``aggregate_demographic_collisions`` is not needed; the natural-key
  collision guard still runs and would catch any future label drift.

- **Suppression**: ``TFS`` ("Too Few Students") is the only marker, and it
  is always all-or-nothing across the three rate columns (0 partially
  suppressed rows across all 24 file/sheet combinations — authored as a
  quality check). ``num_students`` is never suppressed (0 nulls in bronze —
  authored as a quality check). Depending on the file/sheet, suppression
  arrives as the ``TFS`` string or as a true empty cell; the ``dtype=str``
  read + ``strict=False`` casts normalize both to NULL.

- **Complement invariant**: ``average_daily_attendance_rate +
  average_daily_absenteeism_rate = 1.0`` row-by-row; max observed deviation
  across all 8 files is 0.001 (independent rounding of each rate to 3
  decimals at publication). Authored as a quality check with 0.005 tolerance.

- **Geography sentinels**: aggregate rows carry the literal ``"All"`` in
  ``System ID`` / ``School ID`` (state = All/All, district = code/All,
  school = code/code). The fourth quadrant (All + digit school code) is
  structurally absent in every year — guarded with a hard raise. District
  codes zfill(3) (preserving 7-digit state-charter codes), school codes
  zfill(4) (bronze strips leading zeros from some 4-digit codes).

- **Dedup tie-break**: each xlsx covers exactly one year and the bronze
  grain is unique within each file, so no natural-key duplicates are
  expected; ``sort_col="num_students"`` is the documented defensive
  tie-break (prefer the row with a reported, larger enrollment over a
  placeholder).

- **All three rate columns are already on the 0-1 scale** in every file and
  sheet (verified min/max; max observed value is exactly 1.0). No division
  by 100 is applied. All are bounded proportions (``unit: proportion``).
"""

import logging
from pathlib import Path

import pandas as pd
import polars as pl

from src.utils.demographics import (
    DEMOGRAPHIC_ALIASES,
    normalize_demographic_column,
)
from src.utils.metadata import write_data_dictionary
from src.utils.readers import (
    SUPPRESSION_VALUES,
    extract_year_from_filename,
    list_bronze_files,
)
from src.utils.transformers import (
    TransformManifest,
    assert_no_natural_key_collisions,
    deduplicate_by_detail_level,
    export_to_parquet,
    harmonize_columns,
    null_aggregate_geography,
    validate_output,
)
from src.utils.validators import (
    EDUCATION_DOMAIN_CONFIG,
    check_null_rate_spikes,
    run_topic_validation,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

TOPIC = "attendance_dashboard"
BRONZE_DIR = Path("data/bronze/education/georgiainsights/attendance_dashboard")
GOLD_DIR = Path("data/gold/education/attendance_dashboard")
SOURCE_URL = "https://georgiainsights.gadoe.org/data-downloads/"

# The three data sheets in every bronze workbook. The `Read Me` sheet is
# metadata only (metric definitions, the TFS acronym) and is never ingested.
DATA_SHEETS: list[str] = ["All Students", "Grade Level", "Subgroups"]

# Aggregate-row sentinel in `System ID` / `School ID` (title-case in this
# source, unlike GOSA's upper-case `ALL`). Becomes NULL in gold.
GEOGRAPHY_SENTINEL = "All"

# Bronze -> gold column rename. Five bronze headers embed literal `\n` line
# breaks, so an explicit full-name map is required — substring matching would
# silently miss them and the columns would become NULL in gold.
COLUMN_RENAME: dict[str, str] = {
    "School \nYear": "year",
    "System \nID": "district_code",
    "School \nID": "school_code",
    "Subgroup": "demographic_raw",
    "Total \nStudents": "num_students",
    "Chronically Absent \n(10% or more)": "chronically_absent_rate",
    "Average Daily Absenteeism Rate": "average_daily_absenteeism_rate",
    "Average Daily Attendance Rate": "average_daily_attendance_rate",
}

# Bronze columns intentionally NOT selected: `System Name` / `School Name`
# are dimension attributes (live in the districts/schools dimensions), and
# `Group` is the sheet's demographic-category label — fully redundant once
# `Subgroup` is mapped to a canonical demographic code.
BRONZE_ONLY_COLUMNS: list[str] = ["System Name", "School Name", "Group"]

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "num_students",
    "chronically_absent_rate",
    "average_daily_absenteeism_rate",
    "average_daily_attendance_rate",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "demographic": pl.Utf8,
    "num_students": pl.Int64,
    "chronically_absent_rate": pl.Float64,
    "average_daily_absenteeism_rate": pl.Float64,
    "average_daily_attendance_rate": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = [
    "num_students",
    "chronically_absent_rate",
    "average_daily_absenteeism_rate",
    "average_daily_attendance_rate",
]

RATE_COLUMNS: list[str] = [
    "chronically_absent_rate",
    "average_daily_absenteeism_rate",
    "average_daily_attendance_rate",
]

NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "detail_level",
]

# The 28 canonical demographic keys this topic publishes (contract enum).
# The bronze Subgroup lexicon is identical across all 8 years and maps 1:1.
DEMOGRAPHIC_VALUES: list[str] = sorted(
    [
        "all",
        # Grade slice (grade-in-demographic policy; see module docstring).
        "kindergarten",
        *[f"grade_{g}" for g in range(1, 13)],
        # Race (combined Asian/Pacific Islander bucket — §5b).
        "native_american",
        "asian_pacific_islander",
        "black",
        "hispanic",
        "multiracial",
        "white",
        # Gender.
        "female",
        "male",
        # Special populations.
        "students_with_disabilities",
        "students_without_disabilities",
        "economically_disadvantaged",
        "english_learners",
        "homeless",
        "migrant",
    ]
)


# =============================================================================
# Bronze reading (multi-sheet xlsx)
# =============================================================================


def _read_data_sheets(path: Path) -> tuple[pl.DataFrame, dict]:
    """Read the three data sheets of one bronze xlsx and concatenate them.

    The shared ``read_bronze_file`` reads only a workbook's first sheet —
    here that is the documentation-only ``Read Me`` sheet — so the three data
    sheets are read directly via pandas with the same ``dtype=str`` +
    ``SUPPRESSION_VALUES`` conventions the shared XLSX path uses. ``dtype=str``
    collapses the source's dtype drift (the rate columns are Float64 in some
    file/sheet combinations and Utf8-with-``TFS`` in others) into one Utf8
    schema; suppression markers arrive as NULL. A single ``read_excel`` call
    parses the workbook once for all three sheets.

    Returns:
        ``(df, loss)`` — the concatenated all-Utf8 frame and a read-loss
        dict. Excel reads load whole sheets via pandas (no rows can be
        dropped at parse time), so raw == parsed by construction.
    """
    sheets = pd.read_excel(
        path,
        sheet_name=DATA_SHEETS,
        engine="openpyxl",
        dtype=str,
        na_values=list(SUPPRESSION_VALUES),
    )
    # The three sheets share an identical 11-column schema in every year;
    # `how="vertical"` raises on any mismatch instead of silently aligning.
    df = pl.concat(
        [pl.from_pandas(sheets[name]) for name in DATA_SHEETS], how="vertical"
    )
    loss = {"raw_rows": df.height, "parsed_rows": df.height, "format": "xlsx"}
    return df, loss


# =============================================================================
# Shared helpers
# =============================================================================


def _require_columns(df: pl.DataFrame, required: list[str], label: str) -> None:
    """Raise if any expected bronze column is absent (rename-coverage guard).

    An unmatched source column silently becomes NULL in gold — the most
    common data-loss bug — so a missing column fails loudly instead.
    """
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"{label}: expected bronze column(s) missing: {missing}. "
            f"Present: {sorted(df.columns)}"
        )


# =============================================================================
# Year transform (single era)
# =============================================================================


def _transform_year(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Transform one year's concatenated 3-sheet frame into gold rows.

    Single-era topic: all 8 files (2018-2025) share the same 11 columns.
    Detail level derives from the ``"All"`` sentinels in the ID columns
    (state = All/All, district = code/All, school = code/code).
    """
    _require_columns(df, list(COLUMN_RENAME) + BRONZE_ONLY_COLUMNS, f"{TOPIC} {year}")
    df = df.rename(COLUMN_RENAME)

    # Year cross-check: the sheet's `School \nYear` is a single value equal
    # to the filename year (the spring/ending year of the school year). A
    # mismatch means a misnamed or mis-filled file — fail loudly.
    sheet_years = df["year"].drop_nulls().unique().to_list()
    if sheet_years != [str(year)]:
        raise ValueError(
            f"{TOPIC} {year}: sheet School Year values {sheet_years} disagree "
            f"with filename year {year}"
        )

    # Structural guard: the (System ID = "All", School ID = digits) quadrant
    # is absent in every bronze year; such a row has no derivable detail
    # level, so its appearance must fail loudly rather than mislabel rows.
    bad_quadrant = df.filter(
        (pl.col("district_code") == GEOGRAPHY_SENTINEL)
        & (pl.col("school_code") != GEOGRAPHY_SENTINEL)
    ).height
    if bad_quadrant:
        raise ValueError(
            f"{TOPIC} {year}: {bad_quadrant} row(s) with System ID='All' but "
            f"a concrete School ID — unknown detail level"
        )

    is_dist_all = pl.col("district_code") == GEOGRAPHY_SENTINEL
    is_sch_all = pl.col("school_code") == GEOGRAPHY_SENTINEL
    df = df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        # Detail level from the sentinel pattern (the bad quadrant was
        # excluded above, so `otherwise` can only be a genuine school row).
        pl.when(is_dist_all & is_sch_all)
        .then(pl.lit("state"))
        .when(is_sch_all)
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .alias("detail_level"),
        # Geography keys: "All" sentinel -> NULL; zfill(3) pads 3-digit
        # district codes while passing 7-digit state-charter codes through;
        # zfill(4) restores the leading zero bronze strips from some
        # 4-digit school codes (e.g. "618" -> "0618").
        pl.when(is_dist_all)
        .then(None)
        .otherwise(pl.col("district_code").str.zfill(3))
        .alias("district_code"),
        pl.when(is_sch_all)
        .then(None)
        .otherwise(pl.col("school_code").str.zfill(4))
        .alias("school_code"),
        # Counts hop through Float64 so a float-formatted count string would
        # survive; strict=False turns any residual non-numeric string into
        # NULL. (Bronze counts are clean integers — 0 NULLs expected.)
        pl.col("num_students")
        .cast(pl.Float64, strict=False)
        .cast(pl.Int64, strict=False)
        .alias("num_students"),
        # Rates are already 0-1 scale (verified every file/sheet) — cast
        # only; strict=False nulls any suppression string the reader missed.
        *[pl.col(c).cast(pl.Float64, strict=False).alias(c) for c in RATE_COLUMNS],
    )

    # Demographic normalization via the shared canonical path (§5). Record
    # the effective slice of the alias map — only the aliases this file's
    # labels actually hit — so the manifest stays reviewable while the
    # unmapped guard still flags any label the shared map cannot place.
    df = df.with_columns(
        normalize_demographic_column("demographic_raw").alias("demographic")
    )
    observed_upper = {
        str(v).strip().upper()
        for v in df["demographic_raw"].drop_nulls().unique().to_list()
    }
    effective_map = {
        k: v for k, v in DEMOGRAPHIC_ALIASES.items() if k in observed_upper
    }
    manifest.record_categorical(
        column="demographic",
        map_dict=effective_map,
        bronze_series=df["demographic_raw"],
        gold_series=df["demographic"],
    )

    return df.select(STANDARD_COLUMNS)


# =============================================================================
# File dispatcher
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read one bronze workbook (3 data sheets) and transform it."""
    year = extract_year_from_filename(path.name)
    if year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")

    df, loss = _read_data_sheets(path)
    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])
    # Single-era topic; the era name documents why there is no dispatch.
    manifest.record_file(
        path, year, "era_1_2018_2025_three_sheet_xlsx", df.height, df.columns
    )
    manifest.record_bronze(year, df.height)

    if df.height == 0:
        logger.warning("Year %d: bronze file %s is empty, skipping", year, path.name)
        return None
    logger.info("Processing %s (year %d, %d rows)", path.name, year, df.height)
    return _transform_year(df, year, manifest)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for attendance_dashboard."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file (read-loss accounted per file).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR, extensions=[".xlsx"]):
        result = transform_file(path, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize columns/dtypes across years and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)
    logger.info("Combined %d rows across %d files", combined.height, len(all_dfs))

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean an alias-collapse bug and must raise, not be deduped away. (No
    # demographic collisions exist: the 28 bronze Subgroup labels map 1:1
    # onto 28 canonical keys, so aggregate_demographic_collisions is not
    # needed — see module docstring.)
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: each xlsx covers exactly one year and the bronze grain is
    # unique within every file, so no duplicates are expected; prefer the
    # row with a reported (non-null, larger) enrollment as the safety net.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code", "demographic"],
        district_keys=["year", "district_code", "demographic"],
        state_keys=["year", "demographic"],
        sort_col="num_students",
    )

    # 4. Geography nulling (shared domain rules — transform and validator
    # read the same dict, so they cannot disagree). No §4b masks: every
    # observed value is within its metric's defined scale.
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. Rate suppression varies by year (e.g. the Grade
    # Level sheet has more TFS rows in 2021/2023/2024) — the spike check
    # warns; expected and documented.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(combined, required_non_null=["year", "detail_level", "demographic"])

    # 5. Manifest stats on the FINAL DataFrame, then export.
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(combined, GOLD_DIR, STANDARD_COLUMNS)
    manifest.write(GOLD_DIR)

    # 6. Contract + README from the in-code column declaration.
    _emit_contract_and_readme(
        year_range=(int(combined["year"].min()), int(combined["year"].max()))
    )

    summary = manifest.tracker.summary()
    logger.info(
        "Done. Bronze rows: %s; gold rows: %s; years: %s",
        f"{summary['total_bronze']:,}",
        f"{summary['total_gold']:,}",
        summary["years_processed"],
    )

    # 7. ALWAYS LAST: validate the gold just written against the contract
    # just emitted. Raises GoldValidationError -> non-zero exit.
    run_topic_validation(GOLD_DIR)


def _emit_contract_and_readme(year_range: tuple[int, int]) -> None:
    """Emit the ODCS contract and gold README via ``write_data_dictionary``.

    The column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level`` — the contract properties (and the validator's schema
    check) follow it.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Georgia Insights (GaDOE) Attendance Dashboard. For every "
            "Georgia public school, school district, and the state as a "
            "whole, reports three absenteeism metrics — the chronic "
            "absenteeism rate (share of students absent 10%% or more of "
            "their enrolled days), the average daily absenteeism rate, and "
            "the average daily attendance rate — plus the enrollment "
            "denominator, broken out by grade level (kindergarten through "
            "grade 12) and by demographic subgroup (race/ethnicity with the "
            "combined `asian_pacific_islander` bucket, gender, students "
            "with/without disabilities, economically disadvantaged, English "
            "learners, homeless, and migrant). Coverage spans the 2017-18 "
            "school year (year 2018) through the 2024-25 school year (year "
            "2025) — 8 files, no gap years."
        ),
        title="School Attendance and Chronic Absenteeism",
        summary=(
            "Georgia school, district, and state absenteeism and attendance "
            "rates by grade and demographic subgroup, 2018-2025."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2025,
                "description": (
                    "Ending calendar year of the school year (2025 = "
                    "2024-2025). Sourced from the bronze `School Year` "
                    "column, cross-checked against the filename year."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "3-digit GOSA district code (zero-padded) for standard "
                    "districts; 7-digit code for state-charter / "
                    "state-specialty systems. NULL for state-level "
                    "aggregate rows. FK to districts dimension."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0618",
                "description": (
                    "4-digit GOSA school code (zero-padded; bronze strips "
                    "the leading zero from some codes). NULL for district- "
                    "and state-level aggregate rows. FK to schools "
                    "dimension (composite key with district_code)."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "black",
                "validValues": DEMOGRAPHIC_VALUES,
                "short_description": (
                    "Which student group the row covers - `all`, a grade "
                    "level (kindergarten through grade 12), a race, a "
                    "gender, or a special population."
                ),
                "description": (
                    "Canonical demographic code (FK to demographics "
                    "dimension). `all` is the unfiltered total; grade "
                    "levels are encoded INSIDE this column (`kindergarten`, "
                    "`grade_1`..`grade_12`) per the grade-in-demographic "
                    "policy — there is no separate grade_level axis; race "
                    "uses the combined `asian_pacific_islander` bucket "
                    "(pre-1997 OMB 6-bucket convention — the source never "
                    "publishes separate Asian or Pacific Islander rows); "
                    "plus gender (`male`/`female`) and special-population "
                    "codes. Values are mutually exclusive within a "
                    "category; `all` overlaps every category."
                ),
            },
            {
                "name": "num_students",
                "type": "int64",
                "unit": "count",
                "metric_component": "denominator",
                "nullable": False,
                "example": 913,
                "description": (
                    "Enrollment denominator for this (entity, demographic) "
                    "cell — the number of students the three rate columns "
                    "are computed over. Never suppressed in source (always "
                    "populated, even on rows whose rates are suppressed)."
                ),
            },
            {
                "name": "chronically_absent_rate",
                "type": "float64",
                "unit": "proportion",
                "key_metric": True,
                "example": 0.284,
                "short_description": (
                    "Share of students absent 10%% or more of their enrolled "
                    "days, on a 0-1 scale; NULL when suppressed."
                ),
                "null_meaning": (
                    "Suppressed by GaDOE (`TFS` — Too Few Students). "
                    "Suppression is all-or-nothing across the three rate "
                    "columns."
                ),
                "description": (
                    "Share of students absent 10%% or more of their "
                    "enrolled days (the federal chronic-absenteeism "
                    "definition). 0-1 decimal scale, as published — no "
                    "rescaling applied. NULL when suppressed."
                ),
            },
            {
                "name": "average_daily_absenteeism_rate",
                "type": "float64",
                "unit": "proportion",
                "example": 0.081,
                "null_meaning": (
                    "Suppressed by GaDOE (`TFS` — Too Few Students). "
                    "Suppression is all-or-nothing across the three rate "
                    "columns."
                ),
                "description": (
                    "Total absent-days divided by total enrolled-days. 0-1 "
                    "decimal scale, as published. The complement of "
                    "average_daily_attendance_rate. NULL when suppressed."
                ),
            },
            {
                "name": "average_daily_attendance_rate",
                "type": "float64",
                "unit": "proportion",
                "example": 0.919,
                "null_meaning": (
                    "Suppressed by GaDOE (`TFS` — Too Few Students). "
                    "Suppression is all-or-nothing across the three rate "
                    "columns."
                ),
                "description": (
                    "Total present-days divided by total enrolled-days "
                    "(Average Daily Attendance, a fixed term of art in "
                    "school reporting). 0-1 decimal scale, as published. "
                    "Equals 1 - average_daily_absenteeism_rate within "
                    "0.001 (independent rounding of each rate to 3 "
                    "decimals); preserved so analysts need not recompute. "
                    "NULL when suppressed."
                ),
            },
        ],
        source="Georgia Insights (GaDOE)",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        notes=[
            (
                "All three rate columns are published on the 0-1 decimal "
                "scale; no rescaling is applied by the transform."
            ),
            (
                "`TFS` (Too Few Students) is the only suppression marker, "
                "and it is always all-or-nothing across the three rate "
                "columns — no row anywhere in the source is partially "
                "suppressed. `num_students` is never suppressed."
            ),
            (
                "Grade levels live inside the `demographic` column "
                "(`kindergarten`, `grade_1`..`grade_12`) per the "
                "grade-in-demographic policy: bronze reports grade as one "
                "slice among the demographic breakouts, so a separate "
                "grade_level axis would fabricate unmeasured cells."
            ),
            (
                "Race uses the combined `asian_pacific_islander` bucket: "
                "the source publishes the explicit `Asian/Pacific Islander` "
                "label and never a separate Asian or Pacific Islander row. "
                "The split `asian` / `pacific_islander` keys are never "
                "emitted."
            ),
            (
                "average_daily_attendance_rate + "
                "average_daily_absenteeism_rate = 1.0 row-by-row within "
                "0.001 (each rate is independently rounded to 3 decimals "
                "at publication)."
            ),
            (
                "State-level rows have NULL district_code and school_code; "
                "district rows have NULL school_code. The bronze `All` "
                "sentinels become NULL. Names live in the dimension "
                "tables, not in this fact table."
            ),
        ],
        quality_checks=[
            {
                "name": "attendance_absenteeism_complement",
                "description": (
                    "average_daily_attendance_rate + "
                    "average_daily_absenteeism_rate sums to 1.0 (+/-0.005) "
                    "on every row where both are populated (they are "
                    "complements; max bronze deviation is 0.001 from "
                    "independent 3-decimal rounding). Verified on all 8 "
                    "bronze files: 0 violations."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "average_daily_attendance_rate IS NOT NULL AND "
                    "average_daily_absenteeism_rate IS NOT NULL AND "
                    "ABS(average_daily_attendance_rate + "
                    "average_daily_absenteeism_rate - 1.0) > 0.005"
                ),
                "mustBe": 0,
            },
            {
                "name": "rate_suppression_all_or_nothing",
                "description": (
                    "Suppression is all-or-nothing across the three rate "
                    "columns: a row has either all three rates populated "
                    "or all three NULL. Verified on all 24 bronze "
                    "file/sheet combinations: 0 partially suppressed rows."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(chronically_absent_rate IS NULL) <> "
                    "(average_daily_absenteeism_rate IS NULL) OR "
                    "(chronically_absent_rate IS NULL) <> "
                    "(average_daily_attendance_rate IS NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "num_students_never_null",
                "description": (
                    "num_students (the enrollment denominator) is never "
                    "suppressed or missing — populated on every row in "
                    "every bronze file, including rows whose rates are "
                    "suppressed."
                ),
                "dimension": "completeness",
                "query": ("SELECT COUNT(*) FROM {object} WHERE num_students IS NULL"),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
