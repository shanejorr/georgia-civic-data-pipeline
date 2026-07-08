"""Transform bronze georgia_student_growth_model_end_of_course into gold facts.

Source: Georgia Insights (GaDOE) — the Georgia Student Growth Model
(GSGM / Student Growth Percentile, SGP) on End-of-Course assessments.
Each row carries growth-related measures for one (state / district /
school) x subject cohort. Bronze ships 18 Excel workbooks: six reporting
years (2015-2019, 2023) x three detail levels (State, System, School).
No 2020-2022 files exist (GSGM was not reported in the COVID years), so
gold emits no partitions for those years. There are no demographic or
grade breakdowns anywhere in this bronze — every row is "All Students"
on a course-based assessment — so per data-cleaning-standards §5 the
``demographic`` column is omitted and there is no ``grade_level``.

Sheet layouts are detected STRUCTURALLY from the sheet-name shapes (not
from hardcoded year ranges). Three layouts exist (re-verified against
all 18 files during authoring):

- ``per_subject_stem`` — sheets named ``EOC_<STEM>_<YYYY>_<Level>`` (all
  2015-2019 System/School files plus 2015 State): one subject per sheet,
  subject from the stem. The 2015 State sheets also carry a redundant
  ``Subject`` column — cross-checked against the stem, then dropped.
- ``state_combined`` — a single sheet named ``EOC_<YYYY>_State``
  (2016-2019 State): subjects are ROWS in a ``Subject`` column.
- ``level_label`` — sheets named ``<Level> - <Subject>`` (all 2023
  files): subject from the sheet name; the 2023 State sheets also carry
  a redundant ``Content Area`` column (cross-checked, then dropped).

All reads go through pandas with ``header=1`` (row 0 is a title row),
``dtype=str``, and the topic suppression markers as ``na_values`` (the
GeorgiaInsights precedent — the shared ``read_bronze_file`` reads only
the first sheet of a workbook). Whole-sheet Excel reads cannot drop
records at parse time, so read-loss raw == parsed by construction and no
read-loss events are recorded. Blank spacer rows (the 2023 files have an
all-blank row between header and data) are structural padding, not
records, and are dropped before bronze counts are recorded.

Design decisions (each re-verified against bronze during authoring):

- **Year + detail level come ONLY from the filename** (no year column
  exists in the data). Filename year = spring / school-year-end year for
  both patterns (``GSGM_EOC_YYYY_*`` and ``SGP_EOC_Aggs_*_YYYY``). The
  sheet names of stem-layout files embed the same year and the level
  token — both are asserted against the filename as a belt-and-suspenders
  check.

- **The 2015-2017 School ``Key`` is district(3) + school(4).** A 7-digit
  compound code: the FIRST THREE digits are the GOSA district code and
  the last four the school code (e.g. 6010103 = 601 + 0103, 8915001 =
  891 + 5001, 7820108 = 782 + 0108). The bronze structure doc's original
  claim of a constant leading-6 prefix with ``[1:4]``/``[4:]`` slicing is
  wrong — observed district prefixes span 601-799 and 891, matching the
  3-digit codes the 2018+ files publish for the same schools (see the
  Corrections section of bronze-data-structure.md).

- **Charter SYSTEM→CAMPUS promotion** (shared
  ``_charter_district_promotion`` module): 2015-2017 School ``Key`` rows
  for State/Commission Charter campuses parse to the umbrella SYSTEM
  codes 782/783 + school code; they are rewritten to the 7-digit campus
  codes (district_code + school_code) the repo keys school-level rows on
  — matching the representation the 2018+ files already use. Promotions
  are ledgered per year as manifest ``reclassified`` events.

- **Suppression → NULL, row kept.** Markers vary by era: ``----``
  (2015-2016 and residually in 2017's ``%% Proficient Learner and
  above``), ``TFS`` (2017-2019, incl. the 2019 ``N/Number Received SGP``
  count columns), ``--`` (2023), and 33 stray ``NULL`` literals in the
  2017 School file (31 in %% Proficient Learner and above; 1 each in
  %% Developing Learner and above and %% Typical or High Growth). All
  are nulled at read time via ``na_values``. Additionally,
  the 2016 System Physical Science sheet stores an UNDOCUMENTED numeric
  sentinel ``9999`` in 11 rows x 5 metric columns — impossible values on
  the 0-100 / 1-99 scales, treated per §4b as suppression: NULLed by a
  dedicated sweep over the percent + sgp_median columns and ledgered via
  ``manifest.record_masked`` (a count column could in principle hold a
  legitimate 9999, so the sweep deliberately excludes count columns;
  bronze was scanned — no 9999 exists outside the five PHY-2016 metric
  columns).

- **Percent columns ship 0-100 in every era** (rounded integers
  2015-2018, many-decimal floats in 2019/2023 — re-verified per era) and
  are divided by 100 to the canonical 0-1 scale at sheet level.
  ``sgp_median`` is a 1-99 percentile rank (Float64 — bronze publishes
  half-point medians like 43.5) and keeps its natural scale.

- **Era 1-2 and Era 3 growth metrics are NOT merged.**
  ``pct_sgp_typical_or_high_growth`` (2015-2019) is the share with SGP >= 35;
  2023 replaces it with a three-band split (``pct_sgp_low_growth`` < 35,
  ``pct_sgp_typical_growth`` 35-65, ``pct_sgp_high_growth`` > 65).
  2023's "typical" excludes "high", so the columns stay separate, each
  NULL in the years the other was reported. 2023 also drops
  ``num_tested`` / ``sgp_received_rate`` and the two achievement-level
  cumulatives entirely (genuine bronze gaps, NULL in gold).

- **No footnote/footer rows exist in this bronze** (full-file scan of
  every sheet during authoring found no non-numeric residue outside the
  documented suppression markers), so no footnote filter is needed. The
  one structural oddity — EOC_AGE_2019_System ends with 119 blank rows
  plus an orphan row whose only content is a lone TFS marker with no
  geography — reduces to fully-blank rows once markers are nulled and is
  dropped by the spacer filter (see bronze-data-structure.md
  Corrections).

- **Dedup tie-break**: each (year, detail_level) slice is fed by exactly
  one bronze file and natural keys are unique within files, so dedup is
  purely defensive; ``sort_col="num_tested"`` would prefer a row with a
  reported count over a placeholder. ``assert_no_natural_key_collisions``
  runs first (after promotion) so a duplicate key with DIVERGENT metrics
  fails loudly instead of being silently resolved.

Quality-check note: the candidate invariant "pct_sgp_typical_or_high_growth
== pct_sgp_typical_growth + pct_sgp_high_growth" is NOT authorable — the
two metric families never co-occur on a row (different eras), which is
itself enforced via the era_growth_metrics_mutually_exclusive check.

Natural key: (year, detail_level via filename, district_code,
school_code, subject).
"""

import logging
import re
from pathlib import Path

import pandas as pd
import polars as pl

from src.etl.education.georgiainsights._charter_district_promotion import (
    promote_charter_system_to_campus_district,
)
from src.utils.metadata import write_data_dictionary
from src.utils.readers import SUPPRESSION_VALUES, list_bronze_files
from src.utils.subjects import apply_subject_normalization
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

TOPIC = "georgia_student_growth_model_end_of_course"
BRONZE_DIR = Path(
    "data/bronze/education/georgiainsights/georgia_student_growth_model_end_of_course"
)
GOLD_DIR = Path("data/gold/education/georgia_student_growth_model_end_of_course")

# =============================================================================
# Subject normalization
# =============================================================================

# Sheet-name stem (EOC_<STEM>_<YYYY>_<Level>) -> canonical subject. The 2015
# ECO sheets label the subject "Economics" and the 2016 ones
# "Economics/Business/Free Enterprise" — both stems map to the canonical
# long form per §16. Curriculum-era distinct courses (coordinate_algebra /
# algebra_i; analytic_geometry / geometry) stay distinct on purpose.
SHEET_STEM_TO_SUBJECT: dict[str, str] = {
    "9LIT": "9th_grade_literature_and_composition",
    "AMLIT": "american_literature_and_composition",
    "CAL": "coordinate_algebra",
    "AGE": "analytic_geometry",
    "ALG": "algebra_i",
    "GEO": "geometry",
    "BIO": "biology",
    "PHY": "physical_science",
    "USH": "us_history",
    "ECO": "economics_business_free_enterprise",
}

# Lowercased, whitespace-collapsed Subject / Content Area column value (and
# 2023 sheet-name label) -> canonical subject. Every key was observed in
# bronze; lookups raise on anything unmapped so new labels cannot silently
# produce wrong subjects.
SUBJECT_VALUE_MAP: dict[str, str] = {
    "ninth grade literature & composition": "9th_grade_literature_and_composition",
    "american literature & composition": "american_literature_and_composition",
    "coordinate algebra": "coordinate_algebra",
    "analytic geometry": "analytic_geometry",
    "algebra i": "algebra_i",
    "geometry": "geometry",
    "biology": "biology",
    "physical science": "physical_science",
    "united states history": "us_history",
    # 2015 short form and 2016+ long form are the same course (§16).
    "economics": "economics_business_free_enterprise",
    "economics/business/free enterprise": "economics_business_free_enterprise",
}

# =============================================================================
# Gold schema
# =============================================================================

METRIC_COLUMNS: list[str] = [
    "num_tested",
    "num_sgp_received",
    "sgp_received_rate",
    "sgp_median",
    "pct_proficient_learner_or_above",
    "pct_developing_learner_or_above",
    "pct_sgp_typical_or_high_growth",
    "pct_sgp_low_growth",
    "pct_sgp_typical_growth",
    "pct_sgp_high_growth",
]

STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "detail_level",
    "subject",
    *METRIC_COLUMNS,
]

# sgp_median is a 1-99 percentile rank but Float64 — bronze publishes
# half-point medians (e.g. 43.5) at every detail level.
TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "detail_level": pl.Utf8,
    "subject": pl.Utf8,
    "num_tested": pl.Int64,
    "num_sgp_received": pl.Int64,
    "sgp_received_rate": pl.Float64,
    "sgp_median": pl.Float64,
    "pct_proficient_learner_or_above": pl.Float64,
    "pct_developing_learner_or_above": pl.Float64,
    "pct_sgp_typical_or_high_growth": pl.Float64,
    "pct_sgp_low_growth": pl.Float64,
    "pct_sgp_typical_growth": pl.Float64,
    "pct_sgp_high_growth": pl.Float64,
}

NATURAL_KEYS: list[str] = [
    "year",
    "detail_level",
    "district_code",
    "school_code",
    "subject",
]

# Percent columns divided by 100 to the gold 0-1 scale. Counts and the
# sgp_median percentile rank keep their natural scales. sgp_received_rate
# is a 0-1 rate too (bronze ships 0-100) but lacks the pct_ prefix, so it
# is added explicitly.
_PCT_COLUMNS: set[str] = {c for c in METRIC_COLUMNS if c.startswith("pct_")} | {
    "sgp_received_rate"
}

# Era-specific suppression markers on top of the shared set
# (bronze-data-structure.md suppression tables + Corrections): "----"
# (2015-2016, plus 2017 '% Proficient Learner and above' residue), "--"
# (2023), "NULL" (33 stray literals in 2017 School across 3 pct columns;
# also a pandas default NA, listed explicitly for documentation). "TFS"
# is in the shared set.
# The 2016-PHY "9999" sentinel is handled by _null_9999_sentinel so it
# can be counted and ledgered.
_TOPIC_SUPPRESSION_VALUES: set[str] = SUPPRESSION_VALUES | {"----", "--", "NULL"}

# Canonical bronze header (UPPERCASE, whitespace-collapsed — embedded
# newlines like "Median \nSGP" and trailing spaces like "RESA " normalize
# away) -> gold column. "_drop_*" destinations are intentional drops
# (constant State column, dimension-attribute names, RESA); "_compound_key"
# and "_subject_raw" are intermediates resolved by the per-layout readers.
_HEADER_MAP: dict[str, str] = {
    "SYSTEM CODE": "district_code",
    "SCHOOL CODE": "school_code",
    # 2015-2017 School: 7-digit Key = district(3) + school(4).
    "KEY": "_compound_key",
    "STATE": "_drop_state",  # constant "Georgia" (2015-2017 State files)
    "SYSTEM NAME": "_drop_name",
    "SCHOOL NAME": "_drop_name",
    "RESA": "_drop_resa",  # 2023 only — a district attribute, not a fact
    # Subject column (State files); 2023 renames it to "Content Area".
    "SUBJECT": "_subject_raw",
    "CONTENT AREA": "_subject_raw",
    # Counts — Era 1 / school files use short forms, Era 2 state+system and
    # 2023 use long forms.
    "N TESTED": "num_tested",
    "NUMBER TESTED": "num_tested",
    "N RECEIVED SGP": "num_sgp_received",
    "NUMBER RECEIVED SGP": "num_sgp_received",
    "% RECEIVED SGP": "sgp_received_rate",
    # 2023 inverts the word order.
    "MEDIAN SGP": "sgp_median",
    "SGP MEDIAN": "sgp_median",
    # 2019 capitalizes "Above"; the uppercase canonical form covers both.
    "% PROFICIENT LEARNER AND ABOVE": "pct_proficient_learner_or_above",
    "% DEVELOPING LEARNER AND ABOVE": "pct_developing_learner_or_above",
    "% TYPICAL OR HIGH GROWTH": "pct_sgp_typical_or_high_growth",
    # 2023 three-band split.
    "% SGP LOW GROWTH": "pct_sgp_low_growth",
    "% SGP TYPICAL GROWTH": "pct_sgp_typical_growth",
    "% SGP HIGH GROWTH": "pct_sgp_high_growth",
}

_DROP_DESTINATIONS: set[str] = {"_drop_state", "_drop_name", "_drop_resa"}

# Columns swept for the 2016-PHY "9999" numeric suppression sentinel: only
# columns where 9999 is IMPOSSIBLE (percent 0-100 scales + the 1-99
# sgp_median). Count columns are deliberately excluded — a count of 9999 is
# conceivable, and bronze holds no 9999 in any count column (verified).
_SENTINEL_9999_COLUMNS: list[str] = [
    "sgp_received_rate",
    "sgp_median",
    "pct_proficient_learner_or_above",
    "pct_developing_learner_or_above",
    "pct_sgp_typical_or_high_growth",
    "pct_sgp_low_growth",
    "pct_sgp_typical_growth",
    "pct_sgp_high_growth",
]

# Sheet-name shapes (structural layout detection — no year ranges).
_STEM_SHEET_RE = re.compile(r"^EOC_([A-Z0-9]+)_(\d{4})_(State|System|School)$")
_COMBINED_SHEET_RE = re.compile(r"^EOC_(\d{4})_State$")
_LEVEL_LABEL_SHEET_RE = re.compile(r"^(State|System|School) - (.+)$")

_LEVEL_TOKEN_TO_DETAIL: dict[str, str] = {
    "State": "state",
    "System": "district",
    "School": "school",
}


# =============================================================================
# Filename parsing + layout detection
# =============================================================================


def _parse_filename(filename: str) -> tuple[int, str]:
    """Extract (year, detail_level) from a bronze filename.

    Both patterns (``GSGM_EOC_YYYY_{Level}[_Level]`` and
    ``SGP_EOC_Aggs_{Level}_Level_YYYY``) carry exactly one 4-digit year —
    the spring / school-year-end year — and a State/System/School token.
    "System" is the bronze word for the gold "district" detail level.
    """
    year_match = re.search(r"20\d{2}", filename)
    if not year_match:
        raise ValueError(f"Cannot parse year from {filename!r}")
    year = int(year_match.group())

    lower = filename.lower()
    if "school" in lower:
        detail = "school"
    elif "system" in lower:
        detail = "district"
    elif "state" in lower:
        detail = "state"
    else:
        raise ValueError(f"Cannot parse detail level from {filename!r}")
    return year, detail


def _detect_layout(sheet_names: list[str], *, context: str) -> str:
    """Detect the workbook layout structurally from its sheet names.

    - ``per_subject_stem``: every sheet matches ``EOC_<STEM>_<YYYY>_<Level>``
      (2015-2019 System/School + 2015 State).
    - ``state_combined``: a single ``EOC_<YYYY>_State`` sheet where subjects
      are rows in a Subject column (2016-2019 State).
    - ``level_label``: every sheet matches ``<Level> - <Subject>`` (2023).
    """
    if all(_STEM_SHEET_RE.match(s) for s in sheet_names):
        return "per_subject_stem"
    if len(sheet_names) == 1 and _COMBINED_SHEET_RE.match(sheet_names[0]):
        return "state_combined"
    if all(_LEVEL_LABEL_SHEET_RE.match(s) for s in sheet_names):
        return "level_label"
    raise ValueError(f"{context}: unrecognized sheet layout {sheet_names}")


# =============================================================================
# Header / value canonicalization
# =============================================================================


def _canonical_header(name: object) -> str:
    """Canonicalize a bronze header for _HEADER_MAP lookup.

    Collapses embedded newlines ("Median \\nSGP", "Number\\nReceived SGP"),
    whitespace runs, and trailing spaces ("RESA "), and uppercases so case
    drift ("and Above" vs "and above") lands on one key.
    """
    s = str(name).replace("\n", " ").replace("\r", " ")
    return " ".join(s.split()).strip().upper()


def _canonical_subject_value(raw: object, *, context: str) -> str:
    """Map a Subject / Content Area value (or 2023 label) to the canonical subject.

    Raises on unmapped labels — silent fall-through would mislabel rows.
    """
    key = " ".join(str(raw).strip().lower().split())
    subject = SUBJECT_VALUE_MAP.get(key)
    if subject is None:
        raise ValueError(
            f"{context}: unmapped subject label {raw!r} (key {key!r}). "
            f"Add it to SUBJECT_VALUE_MAP."
        )
    return subject


# =============================================================================
# Frame-level helpers
# =============================================================================


def _read_sheet(xl: pd.ExcelFile, sheet_name: str, *, context: str) -> pl.DataFrame:
    """Read one sheet (title row 0, header row 1) into a canonicalized frame.

    ``dtype=str`` keeps mixed numeric/suppression columns intact and
    preserves zero-padded codes; ``na_values`` nulls every documented
    suppression marker on read. Fully-blank spacer rows (the 2023 files
    have one between header and data) are structural padding, not records,
    and are dropped (logged) before bronze row counts are recorded.
    """
    pdf = xl.parse(
        sheet_name=sheet_name,
        header=1,
        dtype=str,
        na_values=list(_TOPIC_SUPPRESSION_VALUES),
    )
    pdf.columns = [_canonical_header(c) for c in pdf.columns]
    df = pl.from_pandas(pdf)
    if df.width and df.height:
        before = df.height
        df = df.filter(~pl.all_horizontal(pl.all().is_null()))
        if before - df.height:
            logger.info(f"{context}: dropped {before - df.height} blank spacer row(s)")
    return df


def _rename_and_drop(df: pl.DataFrame, *, context: str) -> pl.DataFrame:
    """Rename bronze headers to gold names; drop name/State/RESA columns.

    Raises on any header not in _HEADER_MAP — an unknown column is almost
    always a rename miss that would otherwise silently become NULL in gold.
    """
    unknown = [c for c in df.columns if c not in _HEADER_MAP]
    if unknown:
        raise ValueError(
            f"{context}: unknown bronze header(s) {unknown} — extend "
            f"_HEADER_MAP (silent drops hide data loss)."
        )
    rename = {
        c: _HEADER_MAP[c]
        for c in df.columns
        if _HEADER_MAP[c] not in _DROP_DESTINATIONS
    }
    drop = [c for c in df.columns if _HEADER_MAP[c] in _DROP_DESTINATIONS]
    df = df.rename(rename)
    if drop:
        df = df.drop(drop)
    return df


def _split_compound_key(df: pl.DataFrame) -> pl.DataFrame:
    """Split the 2015-2017 School ``Key`` into district + school codes.

    The 7-digit Key is district(3) + school(4) — e.g. 6010103 -> "601" +
    "0103", 8915001 -> "891" + "5001". There is NO constant prefix (see
    module docstring / bronze-data-structure.md Corrections).
    """
    if "_compound_key" not in df.columns:
        return df
    padded = (
        pl.col("_compound_key")
        .cast(pl.Utf8, strict=False)
        .str.replace(r"\.0$", "")
        .str.zfill(7)
    )
    return df.with_columns(
        padded.str.slice(0, 3).alias("district_code"),
        padded.str.slice(3, 4).alias("school_code"),
    ).drop("_compound_key")


def _format_ids(df: pl.DataFrame) -> pl.DataFrame:
    """Zero-pad district_code (3) / school_code (4) where present.

    Strips float-cast ".0" residue first, then zfills — zfill never
    truncates, so 7-digit charter campus codes survive. Covers the 2018
    bare-int codes (103 -> "0103"); idempotent for the already-padded
    2019/2023 strings.
    """
    exprs = []
    for col, width in (("district_code", 3), ("school_code", 4)):
        if col in df.columns:
            exprs.append(
                pl.col(col)
                .cast(pl.Utf8, strict=False)
                .str.replace(r"\.0$", "")
                .str.zfill(width)
                .alias(col)
            )
    return df.with_columns(exprs) if exprs else df


def _null_9999_sentinel(df: pl.DataFrame) -> tuple[pl.DataFrame, dict[str, int]]:
    """NULL the undocumented ``9999`` suppression sentinel (§4b).

    The 2016 System Physical Science sheet stores 9999 in 11 rows x 5
    metric columns — impossible on the 0-100 percent and 1-99 sgp_median
    scales, so it is a suppression sentinel, not data. Swept only over the
    percent + sgp_median columns (a count of 9999 is conceivable; none
    exists in bronze). Returns the frame plus per-column masked counts for
    the manifest ledger.
    """
    counts: dict[str, int] = {}
    exprs = []
    for col in _SENTINEL_9999_COLUMNS:
        if col not in df.columns or df.schema[col] != pl.Utf8:
            continue
        is_sentinel = (
            pl.col(col)
            .str.strip_chars()
            .str.replace(r"\.0$", "")
            .eq("9999")
            .fill_null(False)
        )
        n = int(df.select(is_sentinel.sum()).item())
        if n:
            counts[col] = n
            exprs.append(
                pl.when(is_sentinel).then(None).otherwise(pl.col(col)).alias(col)
            )
    return (df.with_columns(exprs) if exprs else df), counts


def _null_residual_markers(df: pl.DataFrame) -> pl.DataFrame:
    """Defensive sweep: null stripped-equal markers / blanks in string metrics.

    ``na_values`` catches exact markers at read time; this covers
    whitespace-wrapped variants in metric columns still Utf8 (these reads
    bypass read_bronze_file, so the shared marker handling never runs).
    """
    markers = list(_TOPIC_SUPPRESSION_VALUES)
    exprs = []
    for col in METRIC_COLUMNS:
        if col in df.columns and df.schema[col] == pl.Utf8:
            stripped = pl.col(col).str.strip_chars()
            is_marker = stripped.is_in(markers) | (stripped == "")
            exprs.append(
                pl.when(is_marker).then(None).otherwise(pl.col(col)).alias(col)
            )
    return df.with_columns(exprs) if exprs else df


def _cast_metric_columns(df: pl.DataFrame) -> pl.DataFrame:
    """Cast metrics to TARGET_TYPES; scale percent columns from 0-100 to 0-1.

    ``strict=False`` so any remaining non-numeric string lands as NULL.
    Counts and the sgp_median percentile rank keep their natural scales.
    """
    exprs = []
    for col in METRIC_COLUMNS:
        if col not in df.columns:
            continue
        if col in _PCT_COLUMNS:
            exprs.append(
                (pl.col(col).cast(pl.Float64, strict=False) / 100.0).alias(col)
            )
        else:
            exprs.append(pl.col(col).cast(TARGET_TYPES[col], strict=False).alias(col))
    return df.with_columns(exprs) if exprs else df


def _verify_redundant_subject_column(
    df: pl.DataFrame,
    sheet_subject: str,
    *,
    context: str,
    subject_ledger: dict[str, str],
) -> pl.DataFrame:
    """Cross-check a redundant Subject/Content Area column, then drop it.

    The 2015 State and 2023 State sheets carry the subject BOTH in the
    sheet name and as a column. The column values must map to the same
    canonical subject as the sheet name — a mismatch means the subject
    routing is wrong, so raise rather than pick a winner.
    """
    if "_subject_raw" not in df.columns:
        return df
    for raw in df["_subject_raw"].drop_nulls().unique().to_list():
        mapped = _canonical_subject_value(raw, context=context)
        subject_ledger[str(raw)] = mapped
        if mapped != sheet_subject:
            raise ValueError(
                f"{context}: Subject column value {raw!r} maps to {mapped!r} "
                f"but the sheet name implies {sheet_subject!r}"
            )
    return df.drop("_subject_raw")


def _finalize_sheet(
    df: pl.DataFrame, year: int, detail_level: str, subject: str | None
) -> pl.DataFrame:
    """Shared tail: split key -> pad IDs -> marker sweep -> cast -> annotate."""
    df = _split_compound_key(df)
    df = _format_ids(df)
    df = _null_residual_markers(df)
    df = _cast_metric_columns(df)
    exprs = [
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.lit(detail_level).alias("detail_level"),
    ]
    if subject is not None:
        exprs.append(pl.lit(subject).alias("subject"))
    return df.with_columns(exprs)


# =============================================================================
# Per-layout readers
# =============================================================================


def _read_per_subject_stem(
    xl: pd.ExcelFile,
    path: Path,
    year: int,
    detail_level: str,
    subject_ledger: dict[str, str],
) -> tuple[pl.DataFrame, dict[str, int]]:
    """Read a stem-layout workbook (one subject per ``EOC_<STEM>_..`` sheet)."""
    frames: list[pl.DataFrame] = []
    masked_counts: dict[str, int] = {}
    for sheet_name in xl.sheet_names:
        match = _STEM_SHEET_RE.match(sheet_name)
        context = f"{path.name}:{sheet_name}"
        # Belt-and-suspenders: the sheet name embeds the year + level —
        # both must agree with the filename-derived values.
        if int(match.group(2)) != year:
            raise ValueError(f"{context}: sheet year != filename year {year}")
        if _LEVEL_TOKEN_TO_DETAIL[match.group(3)] != detail_level:
            raise ValueError(f"{context}: sheet level != filename level")
        stem = match.group(1)
        subject = SHEET_STEM_TO_SUBJECT.get(stem)
        if subject is None:
            raise ValueError(
                f"{context}: unmapped sheet stem {stem!r}. "
                f"Add it to SHEET_STEM_TO_SUBJECT."
            )
        subject_ledger[sheet_name] = subject

        df = _read_sheet(xl, sheet_name, context=context)
        df = _rename_and_drop(df, context=context)
        df = _verify_redundant_subject_column(
            df, subject, context=context, subject_ledger=subject_ledger
        )
        df, counts = _null_9999_sentinel(df)
        for col, n in counts.items():
            masked_counts[col] = masked_counts.get(col, 0) + n
        frames.append(_finalize_sheet(df, year, detail_level, subject))

    frames = harmonize_columns(frames, STANDARD_COLUMNS, TARGET_TYPES)
    return pl.concat(frames, how="vertical"), masked_counts


def _read_state_combined(
    xl: pd.ExcelFile,
    path: Path,
    year: int,
    detail_level: str,
    subject_ledger: dict[str, str],
) -> tuple[pl.DataFrame, dict[str, int]]:
    """Read a combined State sheet where subjects are rows in a Subject column."""
    sheet_name = xl.sheet_names[0]
    context = f"{path.name}:{sheet_name}"
    df = _read_sheet(xl, sheet_name, context=context)
    df = _rename_and_drop(df, context=context)
    if "_subject_raw" not in df.columns:
        raise ValueError(f"{context}: combined state sheet lacks a Subject column")

    mapping = {
        str(raw): _canonical_subject_value(raw, context=context)
        for raw in df["_subject_raw"].drop_nulls().unique().to_list()
    }
    subject_ledger.update(mapping)
    df = df.with_columns(
        pl.col("_subject_raw").replace_strict(mapping, default=None).alias("subject")
    ).drop("_subject_raw")
    # _canonical_subject_value raised on unmapped labels, so a NULL subject
    # here can only come from a NULL Subject cell — log if the defensive
    # filter ever fires.
    before = df.height
    df = df.filter(pl.col("subject").is_not_null())
    if before - df.height:
        logger.warning(f"{context}: dropped {before - df.height} NULL-subject row(s)")
    df, masked_counts = _null_9999_sentinel(df)
    return _finalize_sheet(df, year, detail_level, subject=None), masked_counts


def _read_level_label(
    xl: pd.ExcelFile,
    path: Path,
    year: int,
    detail_level: str,
    subject_ledger: dict[str, str],
) -> tuple[pl.DataFrame, dict[str, int]]:
    """Read a 2023-layout workbook (sheets named ``<Level> - <Subject>``)."""
    frames: list[pl.DataFrame] = []
    masked_counts: dict[str, int] = {}
    for sheet_name in xl.sheet_names:
        match = _LEVEL_LABEL_SHEET_RE.match(sheet_name)
        context = f"{path.name}:{sheet_name}"
        if _LEVEL_TOKEN_TO_DETAIL[match.group(1)] != detail_level:
            raise ValueError(f"{context}: sheet level != filename level")
        subject = _canonical_subject_value(match.group(2), context=context)
        subject_ledger[sheet_name] = subject

        df = _read_sheet(xl, sheet_name, context=context)
        df = _rename_and_drop(df, context=context)
        df = _verify_redundant_subject_column(
            df, subject, context=context, subject_ledger=subject_ledger
        )
        df, counts = _null_9999_sentinel(df)
        for col, n in counts.items():
            masked_counts[col] = masked_counts.get(col, 0) + n
        frames.append(_finalize_sheet(df, year, detail_level, subject))

    frames = harmonize_columns(frames, STANDARD_COLUMNS, TARGET_TYPES)
    return pl.concat(frames, how="vertical"), masked_counts


# =============================================================================
# File-level dispatch
# =============================================================================


def transform_file(
    path: Path, manifest: TransformManifest, subject_ledger: dict[str, str]
) -> pl.DataFrame | None:
    """Transform one bronze workbook; records manifest entries.

    Whole-sheet Excel reads cannot drop records at parse time (read-loss
    raw == parsed by construction), so no read-loss events are recorded.
    The 9999 sentinel sweep is ledgered via record_masked.
    """
    year, detail_level = _parse_filename(path.name)
    xl = pd.ExcelFile(path)
    layout = _detect_layout(xl.sheet_names, context=path.name)
    logger.info(f"{path.name}: year={year} detail={detail_level} layout={layout}")

    reader = {
        "per_subject_stem": _read_per_subject_stem,
        "state_combined": _read_state_combined,
        "level_label": _read_level_label,
    }[layout]
    df, masked_counts = reader(xl, path, year, detail_level, subject_ledger)

    manifest.record_file(path, year, layout, df.height, df.columns)
    manifest.record_bronze(year, df.height)
    for col, n in masked_counts.items():
        manifest.record_masked(
            col,
            n,
            f"undocumented numeric suppression sentinel 9999 in {path.name} "
            f"(impossible on the column's 0-100 / 1-99 scale; treated as "
            f"suppression per §4b)",
            years=[year],
        )

    if df.height == 0:
        logger.warning(f"{path.name}: no data rows after transform")
        return None
    return df


# =============================================================================
# Pipeline orchestration
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for this topic."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)
    subject_ledger: dict[str, str] = {}
    frames: list[pl.DataFrame] = []

    for path in list_bronze_files(BRONZE_DIR, extensions=[".xls", ".xlsx"]):
        df = transform_file(path, manifest, subject_ledger)
        if df is not None and df.height > 0:
            frames.append(df)

    if not frames:
        raise RuntimeError("No bronze data transformed — check bronze directory")

    # Eras carry different column subsets (no SGP bands before 2023; no
    # num_tested / sgp_received_rate / achievement cumulatives / typical-or-
    # high in 2023); harmonize adds the missing columns as typed NULLs.
    frames = harmonize_columns(frames, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(frames, how="vertical")
    logger.info(f"Combined all frames: {combined.height:,} rows")

    # §10a backstop: the local maps already produce canonical values (and
    # raise on unmapped labels); this keeps the vocabulary aligned with the
    # shared cross-topic normalizer even if the local maps drift.
    combined = combined.with_columns(
        apply_subject_normalization("subject").alias("subject")
    )

    # Charter SYSTEM -> CAMPUS district codes on school-level rows: the
    # 2015-2017 School Key rows for 782/783 campuses parse to the umbrella
    # system codes; promote to the 7-digit campus codes used by 2018+ files
    # and the rest of the repo. Ledgered as manifest reclassified events.
    # Runs before the collision guard + dedup so any promotion-induced key
    # collision is surfaced by the standard machinery.
    combined = promote_charter_system_to_campus_district(combined, manifest=manifest)

    # Guard BEFORE dedup: duplicate keys with DIVERGENT metrics mean an
    # alias/promotion bug and must fail loudly rather than be resolved by
    # the dedup tie-break.
    assert_no_natural_key_collisions(combined, NATURAL_KEYS, METRIC_COLUMNS)

    # Defensive dedup: each (year, detail_level) slice comes from exactly
    # one bronze file and keys are unique within files (the guard above
    # would have raised otherwise). sort_col="num_tested" prefers a row
    # with a reported count over a placeholder if a duplicate ever appears.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code", "subject"],
        district_keys=["year", "district_code", "subject"],
        state_keys=["year", "subject"],
        sort_col="num_tested",
    )

    # Shared geography-nulling rules (validator reads the same config).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    validate_output(combined, required_non_null=["year", "detail_level"])

    # Manifest stats on the FINAL frame, then export.
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(combined, GOLD_DIR, STANDARD_COLUMNS)

    # Subject ledger: every observed raw label (sheet names, Subject /
    # Content Area column values) -> canonical subject, for 100%
    # categorical-recoding coverage at data-review time.
    manifest.record_categorical(
        column="subject",
        map_dict=dict(sorted(subject_ledger.items())),
        bronze_series=pl.Series("subject_raw", sorted(subject_ledger.keys())),
        gold_series=combined["subject"],
    )
    manifest.write(GOLD_DIR)

    # Known legitimate NULL spikes (warnings only): the 2023 redesign drops
    # num_tested / sgp_received_rate / the achievement cumulatives /
    # pct_sgp_typical_or_high_growth, and the three SGP band columns exist ONLY
    # in 2023 — genuine bronze coverage gaps, not transform bugs.
    spike = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike.status == "warning":
        for detail in spike.details or []:
            logger.warning(f"NULL rate spike: {detail}")

    year_min = int(combined["year"].min())
    year_max = int(combined["year"].max())

    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Georgia Student Growth Model (GSGM / Student Growth "
            "Percentile) results on Georgia Milestones End-of-Course "
            "assessments, at the state, district/system, and school level "
            "per subject. Core metrics are the median Student Growth "
            "Percentile (1-99), the count of students receiving an SGP, "
            "and growth-share metrics. 2015-2019 publish the count and "
            "share of tested students with an SGP, two achievement-level "
            "cumulative shares (Proficient / Developing Learner or above), "
            "and the share with Typical-or-High growth (SGP >= 35). The "
            "Full-Year 2022-2023 report (year 2023) redesigns the metric "
            "set: a three-band SGP split (Low < 35, Typical 35-65, High > "
            "65) replaces the single typical-or-high share, and the tested "
            "counts, received-SGP share, and achievement shares are no "
            "longer reported. No GSGM was published for 2020-2022 (COVID). "
            "Subject coverage narrows from 8-10 subjects (2015-2016) to "
            "six (2017-2019) to two algebra courses (2023)."
        ),
        title="Student Growth Model (SGM) End-of-Course Results",
        summary=(
            "Student growth percentiles on Georgia Milestones end-of-course "
            "tests by school, district, and subject, 2015-2023."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "description": (
                    "Ending calendar year of the school year (e.g., 2017 = "
                    "school year 2016-2017). Published years: 2015-2019 and "
                    "2023 (the Full-Year 2022-2023 report). No 2020-2022 "
                    "data exists."
                ),
                "nullable": False,
                "example": 2017,
            },
            {
                "name": "district_code",
                "type": "string",
                "description": (
                    "3-digit GOSA district/system code (FK to districts "
                    "dimension). School-level rows for State/Commission "
                    "Charter campuses use the 7-digit campus code (system "
                    "782/783 + school code) — the 2015-2017 School files "
                    "published those rows under the bare system code inside "
                    "the compound Key and they are promoted here. NULL for "
                    "state-level rows."
                ),
                "nullable": True,
                "example": "601",
            },
            {
                "name": "school_code",
                "type": "string",
                "description": (
                    "4-digit GOSA school code (FK to schools dimension, "
                    "composite with district_code). NULL for district- and "
                    "state-level rows."
                ),
                "nullable": True,
                "example": "0103",
            },
            {
                "name": "subject",
                "type": "string",
                "description": (
                    "Snake-case EOC subject. 2015 reports eight subjects "
                    "(9th_grade_literature_and_composition, "
                    "american_literature_and_composition, "
                    "coordinate_algebra, analytic_geometry, biology, "
                    "physical_science, us_history, "
                    "economics_business_free_enterprise); 2016 adds "
                    "algebra_i and geometry (ten); 2017-2019 report the six "
                    "literature/math subjects; 2023 reports only "
                    "coordinate_algebra and algebra_i."
                ),
                "short_description": (
                    "The end-of-course subject (e.g. algebra_i, biology, "
                    "american_literature_and_composition)."
                ),
                "nullable": False,
                "example": "algebra_i",
            },
            {
                "name": "num_tested",
                "unit": "count",
                "type": "int64",
                "description": (
                    "Number of students who took the EOC assessment. Never "
                    "suppressed where published. NULL in 2023 (the "
                    "Full-Year 2022-2023 report does not publish tested "
                    "counts)."
                ),
                "nullable": True,
                "example": 255,
            },
            {
                "name": "num_sgp_received",
                "unit": "count",
                "metric_component": "denominator",
                "type": "int64",
                "description": (
                    "Number of students with enough prior-year scores to "
                    "receive a Student Growth Percentile (a subset of "
                    "num_tested). Suppressed (NULL) for small cohorts in "
                    "the 2019 files only."
                ),
                "nullable": True,
                "example": 245,
            },
            {
                "name": "sgp_received_rate",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share of tested students who received an SGP "
                    "(num_sgp_received / num_tested), 0-1 scale (bronze "
                    "0-100 divided by 100). NULL in 2023 (not reported)."
                ),
                "nullable": True,
                "example": 0.96,
            },
            {
                "name": "sgp_median",
                "unit": "percentile",
                "key_metric": True,
                "value_min": 1,
                "value_max": 99,
                "type": "float64",
                "description": (
                    "Median Student Growth Percentile on the 1-99 "
                    "percentile-rank scale (preserved verbatim — not a "
                    "share; there is no SGP of 0 or 100, so the range guard "
                    "is tightened from the percentile default [0, 100] to "
                    "[1, 99]). Float64 because bronze publishes half-point "
                    "medians (e.g., 43.5). The 2016 System Physical Science "
                    "sheet stored an undocumented 9999 suppression sentinel "
                    "in 11 rows — impossible on this scale, NULLed per §4b."
                ),
                "short_description": (
                    "Median student growth percentile (1-99); 50 is average "
                    "growth, higher means faster growth than similar peers."
                ),
                "nullable": True,
                "example": 52.0,
            },
            {
                "name": "pct_proficient_learner_or_above",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share of tested students at the Proficient Learner "
                    "achievement level or higher on the EOC assessment "
                    "itself (0-1 scale). Published 2015-2019 only; NULL in "
                    "2023. The 9999 sentinel note on sgp_median also "
                    "applies (11 NULLed values in 2016 Physical Science "
                    "system rows)."
                ),
                "nullable": True,
                "example": 0.42,
            },
            {
                "name": "pct_developing_learner_or_above",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share of tested students at the Developing Learner "
                    "achievement level or higher on the EOC assessment "
                    "(0-1 scale). Published 2015-2019 only; NULL in 2023."
                ),
                "nullable": True,
                "example": 0.80,
            },
            {
                "name": "pct_sgp_typical_or_high_growth",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share of SGP-scored students with SGP >= 35 (Typical "
                    "or High growth), 0-1 scale. Published 2015-2019 only — "
                    "2023 replaces it with the three-band split. NOT equal "
                    "to pct_sgp_typical_growth, which excludes High."
                ),
                "nullable": True,
                "example": 0.68,
            },
            {
                "name": "pct_sgp_low_growth",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share of SGP-scored students in the Low Growth band "
                    "(SGP < 35), 0-1 scale. 2023 only; NULL for 2015-2019."
                ),
                "nullable": True,
                "example": 0.22,
            },
            {
                "name": "pct_sgp_typical_growth",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share of SGP-scored students in the Typical Growth "
                    "band (35 <= SGP <= 65), 0-1 scale. 2023 only; NULL for "
                    "2015-2019. Excludes High growth — not comparable to "
                    "pct_sgp_typical_or_high_growth."
                ),
                "nullable": True,
                "example": 0.35,
            },
            {
                "name": "pct_sgp_high_growth",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share of SGP-scored students in the High Growth band "
                    "(SGP > 65), 0-1 scale. 2023 only; NULL for 2015-2019."
                ),
                "nullable": True,
                "example": 0.43,
            },
        ],
        source=(
            "Georgia Insights (GaDOE) — Georgia Student Growth Model on "
            "End-of-Course assessments"
        ),
        source_url="https://georgiainsights.gadoe.org/data-downloads/",
        update_frequency="annual",
        year_range=(year_min, year_max),
        partitioned_by=["year"],
        notes=[
            (
                "No GSGM data exists for 2020-2022 (not reported during the "
                "COVID years); gold emits partitions only for 2015-2019 and "
                "2023."
            ),
            (
                "2023 (Full-Year 2022-2023) covers only coordinate_algebra "
                "and algebra_i and redesigns the metric set: the three SGP "
                "band shares replace pct_sgp_typical_or_high_growth, and "
                "num_tested / sgp_received_rate / the achievement cumulatives "
                "are not reported."
            ),
            (
                "All percent columns are 0-1 decimal scale (bronze ships "
                "0-100). sgp_median keeps its natural 1-99 percentile-rank "
                "scale and can carry half-point values."
            ),
            (
                "Suppression markers vary by era ('----' in 2015-2016 and "
                "residually in 2017, 'TFS' in 2017-2019, '--' in 2023, 33 "
                "stray 'NULL' literals in 2017 School — 31 in % Proficient "
                "Learner and above, 1 each in % Developing Learner and "
                "above and % Typical or High Growth — and an undocumented "
                "9999 numeric sentinel in the 2016 System Physical Science "
                "sheet) — all land as NULL in gold."
            ),
            (
                "School-level rows for State/Commission Charter campuses "
                "(systems 782/783) are keyed on the 7-digit campus district "
                "code; 2015-2017 bronze published them under the bare "
                "system code and they are promoted during transform "
                "(ledgered as manifest reclassified events)."
            ),
        ],
        quality_checks=[
            {
                "name": "num_sgp_received_le_num_tested",
                "description": (
                    "Students receiving an SGP are a subset of those "
                    "tested, so num_sgp_received <= num_tested wherever "
                    "both are present (verified 0 violations across all "
                    "22,191 bronze rows publishing both counts)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "num_sgp_received IS NOT NULL "
                    "AND num_tested IS NOT NULL "
                    "AND num_sgp_received > num_tested"
                ),
                "mustBe": 0,
            },
            {
                "name": "sgp_received_rate_matches_counts",
                "description": (
                    "sgp_received_rate equals num_sgp_received / num_tested "
                    "(+/-0.02 for publisher rounding; max observed bronze "
                    "deviation is 0.005) wherever the counts and the rate "
                    "are all present and num_tested > 0."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "sgp_received_rate IS NOT NULL "
                    "AND num_sgp_received IS NOT NULL "
                    "AND num_tested IS NOT NULL "
                    "AND num_tested > 0 "
                    "AND ABS(sgp_received_rate "
                    "- (CAST(num_sgp_received AS DOUBLE) / num_tested)) > 0.02"
                ),
                "mustBe": 0,
            },
            {
                "name": "proficient_le_developing_or_above",
                "description": (
                    "Proficient-or-above is nested within "
                    "Developing-or-above, so pct_proficient_learner_or_above "
                    "<= pct_developing_learner_or_above wherever both are "
                    "present (verified 0 violations in bronze)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "pct_proficient_learner_or_above IS NOT NULL "
                    "AND pct_developing_learner_or_above IS NOT NULL "
                    "AND pct_proficient_learner_or_above "
                    "> pct_developing_learner_or_above + 0.0001"
                ),
                "mustBe": 0,
            },
            {
                "name": "sgp_growth_bands_sum_to_one",
                "description": (
                    "The three SGP growth bands (Low, Typical, High) "
                    "partition the SGP-scored students and sum to 1.0 "
                    "(+/-0.02; max observed bronze deviation is ~1e-14) "
                    "wherever all three are present."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "pct_sgp_low_growth IS NOT NULL "
                    "AND pct_sgp_typical_growth IS NOT NULL "
                    "AND pct_sgp_high_growth IS NOT NULL "
                    "AND ABS(pct_sgp_low_growth + pct_sgp_typical_growth "
                    "+ pct_sgp_high_growth - 1.0) > 0.02"
                ),
                "mustBe": 0,
            },
            {
                "name": "era_growth_metrics_mutually_exclusive",
                "description": (
                    "The 2015-2019 two-bucket growth share and the 2023 "
                    "three-band split come from different report designs "
                    "and never co-occur on a row: "
                    "pct_sgp_typical_or_high_growth is NULL wherever any SGP "
                    "band share is present, and vice versa."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "pct_sgp_typical_or_high_growth IS NOT NULL "
                    "AND (pct_sgp_low_growth IS NOT NULL "
                    "OR pct_sgp_typical_growth IS NOT NULL "
                    "OR pct_sgp_high_growth IS NOT NULL)"
                ),
                "mustBe": 0,
            },
        ],
    )

    # ALWAYS LAST: validate against the contract just emitted. Raises on
    # any failure so the transform exits non-zero.
    run_topic_validation(GOLD_DIR)

    summary = manifest.tracker.summary()
    logger.info(
        f"Done. Bronze rows: {summary['total_bronze']:,}; "
        f"Gold rows: {summary['total_gold']:,}; "
        f"Years: {summary['years_processed']}"
    )


if __name__ == "__main__":
    main()
