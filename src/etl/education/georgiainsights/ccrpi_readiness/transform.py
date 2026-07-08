"""Transform bronze ccrpi_readiness files into gold fact tables.

Source: Georgia Insights (GaDOE) — the CCRPI Readiness component measures
student readiness for the next level via six sub-metrics that vary by grade
cluster: Literacy / At or Above Grade-Level Reading (E/M/H), Student
Attendance / Attendance (E/M/H), Beyond the Core (E/M enrichment-course
participation), Accelerated Enrollment (H college-level credit), Pathway
Completion (H), and College and Career Readiness (H). Each row reports a
0-100 ``indicator_score``; Era 2 adds an unbenchmarked participation rate
for Accelerated Enrollment.

Bronze coverage: 7 single-data-sheet xlsx files, 2018-2025 (no 2020 — CCRPI
was not calculated under the COVID federal waiver). Two schema eras, routed
by column signature (never by year):

- **Era 1 — base** (2018, 2019): 10 columns, no Sub-Indicator and no
  Unbenchmarked Rate. One row per entity x grade cluster x demographic x
  indicator.
- **Era 2 — sub-indicator** (2021-2025): 12 columns, adds ``Sub-Indicator``
  and ``Unbenchmarked Rate (Accelerated Enrollment)``. One row per entity x
  grade cluster x demographic x indicator x sub-indicator.

Design decisions (every invariant re-verified against THIS topic's 7 bronze
files during authoring — see bronze-data-structure.md and its Corrections
section):

- **Per-file data sheet lookup.** The data sheet is ``Readiness by
  Subgroup`` in 2018-2024 and ``Readiness - Student Group`` in 2025;
  2021/2022 also ship an empty ``FAQs`` metadata sheet that must be skipped.
  The 2022 data sheet carries a DOE pandemic disclaimer in row 0, so its
  header is row 1 (every other year: row 0). A local ``_read_readiness_sheet``
  helper resolves sheet + header row per year (precedent: ccrpi_progress /
  attendance_dashboard local readers; shared ``read_bronze_file`` reads only
  a workbook's first sheet with header row 0). Excel reads load whole sheets
  via pandas, so read-loss raw == parsed by construction; the loss event is
  still recorded per file.

- **Detail level from the name columns.** ``System Name == 'All Systems'``
  -> state; else ``School Name == 'All Schools'`` -> district; else school.
  Name-based detection is stable across all 7 years while the ID encodings
  are sentinel-laden: contrary to the original structure-doc claim of null
  IDs on aggregate rows, EVERY year encodes aggregate IDs as the literal
  string ``ALL`` (0 truly empty ID cells in any file; ``ALL`` appears on
  exactly the aggregate rows). ``ALL`` becomes NULL before zfill so padding
  touches only digit codes (zfill(3)/zfill(4); 7-digit state-charter
  operator codes pass through untouched, never truncated).

- **Indicator labels drift across years** and collapse to 8 canonical
  values. ``Beyond The Core`` (2018-2019, capital T) unifies with ``Beyond
  the Core`` (2021+). ``Literacy`` / ``Student Attendance`` (2018-2022) are kept
  DISTINCT from their 2023+ renames ``At or Above Grade-Level Reading`` /
  ``Attendance`` because GaDOE revised the underlying methodology in 2023
  (structure doc flags this; concatenating the series would splice two
  different measurements under one name).

- **Sub-Indicator (Era 2 only).** The literal ``All`` marks the rolled-up
  parent-indicator score for indicators that have sub-breakdowns; the
  literal ``NA`` (2021-2022 only) marks indicators with no sub-breakdown at
  all (Literacy, Student Attendance). Both mean "this row is the overall
  indicator score" and both map to gold ``all``. The suppression-aware read
  nulls the ``NA`` token, so Era 2 fills null sub-indicator with ``NA``
  before mapping (restores the bronze token for faithful manifest
  recording). Label drift 2021->2023+ (casing, verbose 2021 CCR labels, the
  ACT/SAT/AP/IB[/Cambridge] evolution) collapses to 16 canonical
  sub-components + ``all``. Era 1 rows carry NULL sub_indicator (bronze has
  no such column — NULL means "not collected", distinct from ``all``).

- **Scales.** ``indicator_score`` is a 0-100 CCRPI score and stays 0-100
  (``unit: score``, [0, 100] — exempt from the 0-1 percentage rule per
  education CLAUDE.md, matching ccrpi_content_mastery / ccrpi_progress).
  ``unbenchmarked_rate`` is a participation rate, divided by 100 to the
  canonical 0-1 proportion scale (``unit: proportion``).

- **Unbenchmarked Rate population shifts mid-era** (verified per year):
  2021-2023 populate it ONLY on Accelerated Enrollment rows (0 numeric
  values on non-AE rows); 2024-2025 populate it on every row, where non-AE
  values are a cell-identical copy of ``Indicator Score`` (raw strings equal
  on 100%% of non-AE rows, max |diff| = 0.0). Both columns pass through
  verbatim (rate rescaled to 0-1) — the redundancy is bronze's, and dropping
  it would discard the AE-row signal where the two genuinely differ.

- **Suppression markers.** ``TFS`` (2018, 2019, 2023-2025) / ``Too Few
  Students`` (spelled out in 2021-2022 — the structure doc only listed
  ``TFS``) and ``NA`` become NULL via the suppression-aware read. No other
  non-numeric token appears in either metric column in any year.

- **Asian / Pacific Islander is the combined bucket (§5b).** Every year
  ships the single explicit ``Asian/Pacific Islander`` label and never a
  separate Asian or Pacific Islander row. The shared aliases canonicalize it
  to ``asian_pacific_islander``; the split keys are never emitted. No
  topic-local remap needed.

- **No demographic collisions.** The 10 bronze Reporting Labels map 1:1
  onto 10 distinct canonical keys in every year (the only drift is
  ``American Indian/Alaskan`` (2018-2021) vs ``American Indian/Alaskan
  Native`` (2022+), an alias-level rename), so
  ``aggregate_demographic_collisions`` is not needed; the natural-key
  collision guard still runs and would catch future drift.

- **Dedup tie-break**: each bronze year ships exactly one file and the
  natural key is unique within every file (0 duplicate key groups verified
  across all 7 years), so no duplicates are expected;
  ``sort_col="indicator_score"`` is the documented defensive tie-break
  (prefer the row with a reported, higher score over a placeholder).

- **No §4b masks.** Every observed value of both metrics lies inside the
  0-100 bronze scale in every year (verified min=0, max=100 per file).
  Nothing to NULL beyond suppression.
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
    detect_era_by_columns,
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

TOPIC = "ccrpi_readiness"
BRONZE_DIR = Path("data/bronze/education/georgiainsights/ccrpi_readiness")
GOLD_DIR = Path("data/gold/education/ccrpi_readiness")
SOURCE_URL = "https://georgiainsights.gadoe.org/data-downloads/"

# Data sheet name per file year (renamed in 2025). Unknown years fall back to
# the first sheet not in SKIP_SHEETS so a new GaDOE naming convention does not
# silently read the wrong sheet.
SHEET_NAME_BY_YEAR: dict[int, str] = {
    2018: "Readiness by Subgroup",
    2019: "Readiness by Subgroup",
    2021: "Readiness by Subgroup",
    2022: "Readiness by Subgroup",
    2023: "Readiness by Subgroup",
    2024: "Readiness by Subgroup",
    2025: "Readiness - Student Group",
}

# Metadata-only sheets that must never be ingested. The 2021/2022 `FAQs`
# sheet holds explanatory prose, not tabular data.
SKIP_SHEETS: set[str] = {"FAQs", "Read Me", "ReadMe", "Notes"}

# 2022 ships a single-cell DOE pandemic disclaimer in row 0; the real header
# is row 1. Every other year has the header on row 0.
HEADER_ROW_BY_YEAR: dict[int, int] = {2022: 1}

# Era signatures over canonicalized (uppercase, whitespace-collapsed) headers.
# Ordered most-specific first; detect_era_by_columns returns the first match
# and transform_file raises if nothing matches (unknown schema fails loudly).
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_2_sub_indicator": [
        "INDICATOR",
        "SUB-INDICATOR",
        "INDICATOR SCORE",
        "UNBENCHMARKED RATE (ACCELERATED ENROLLMENT)",
    ],
    "era_1_base": [
        "INDICATOR",
        "INDICATOR SCORE",
        "REPORTING LABEL",
        "GRADE CLUSTER",
    ],
}

# Indicator label drift -> 8 canonical values. `Beyond The Core` (2018-2019)
# and `Beyond the Core` (2021+) collapse via the uppercase lookup. Literacy /
# Student Attendance (2018-2022) stay DISTINCT from the 2023+ renames —
# GaDOE revised the methodology in 2023, so the series must not be spliced.
INDICATOR_MAP: dict[str, str] = {
    "ACCELERATED ENROLLMENT": "accelerated_enrollment",
    "BEYOND THE CORE": "beyond_the_core",
    "COLLEGE AND CAREER READINESS": "college_and_career_readiness",
    "PATHWAY COMPLETION": "pathway_completion",
    "LITERACY": "literacy",
    "STUDENT ATTENDANCE": "student_attendance",
    "AT OR ABOVE GRADE-LEVEL READING": "at_or_above_grade_level_reading",
    "ATTENDANCE": "attendance",
}

# Sub-Indicator label drift (Era 2 only) -> 16 sub-components + `all`.
# Bronze `All` (rolled-up score) and bronze `NA` (no sub-breakdown exists;
# 2021-2022 only) both mean "overall indicator score" -> gold `all`. The
# read nulls the `NA` token via SUPPRESSION_VALUES; Era 2 restores it with
# fill_null("NA") BEFORE this map runs (see _transform_era_2).
SUB_INDICATOR_MAP: dict[str, str] = {
    "ALL": "all",
    "NA": "all",
    # Beyond the Core sub-components (mixed casing 2021-2022 vs 2023+).
    "FINE ARTS": "fine_arts",
    "WORLD LANGUAGE": "world_language",
    "CAREER EXPLORATORY": "career_exploratory",
    "COMPUTER SCIENCE": "computer_science",
    # Physical Education: 2021 uses "or"; 2022+ uses "/".
    "PHYSICAL EDUCATION OR HEALTH": "physical_education_health",
    "PHYSICAL EDUCATION/HEALTH": "physical_education_health",
    # Accelerated Enrollment sub-components.
    "ADVANCED PLACEMENT": "advanced_placement",
    "DUAL ENROLLMENT": "dual_enrollment",
    "INTERNATIONAL BACCALAUREATE": "international_baccalaureate",
    "ADVANCED ACADEMIC": "advanced_academic",
    "CAMBRIDGE": "cambridge",
    # Pathway Completion sub-component.
    "CTAE": "ctae",
    # College and Career Readiness sub-components — verbose 2021 labels
    # shorten in 2023+; the ACT/SAT/AP/IB bundle gains Cambridge in 2025.
    # All three label generations describe the same readiness-evidence
    # bucket, so they unify on the widest canonical token.
    "READINESS SCORE ON THE ACT, SAT, AP OR IB": "act_sat_ap_ib_cambridge",
    "ACT/SAT/AP/IB": "act_sat_ap_ib_cambridge",
    "ACT/SAT/AP/IB/CAMBRIDGE": "act_sat_ap_ib_cambridge",
    "END OF PATHWAY ASSESSMENT (EOPA)": "eopa",
    "EOPA": "eopa",
    "ENTERING TCSG/USG WITHOUT NEEDING REMEDIATION": "tcsg_usg",
    "TCSG/USG": "tcsg_usg",
    "WORK-BASED LEARNING": "work_based_learning",
    "ASVAB": "asvab",
}

# Grade cluster single letters -> snake_case words (E/M/H in every year).
GRADE_CLUSTER_MAP: dict[str, str] = {
    "E": "elementary",
    "M": "middle",
    "H": "high",
}

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "detail_level",
    "grade_cluster",
    "indicator",
    "sub_indicator",
    "indicator_score",
    "unbenchmarked_rate",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "demographic": pl.Utf8,
    "detail_level": pl.Utf8,
    "grade_cluster": pl.Utf8,
    "indicator": pl.Utf8,
    "sub_indicator": pl.Utf8,
    "indicator_score": pl.Float64,
    "unbenchmarked_rate": pl.Float64,
}

METRIC_COLUMNS: list[str] = [
    "indicator_score",
    "unbenchmarked_rate",
]

# `indicator` and `sub_indicator` are part of the key: each entity x cluster
# x demographic reports up to 6 indicators, and Era 2 breaks indicators into
# sub-components (each its own row). Era 1 rows have NULL sub_indicator.
NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "detail_level",
    "grade_cluster",
    "indicator",
    "sub_indicator",
]

# The 10 canonical demographic keys this topic publishes (contract enum).
# Combined Asian/Pacific Islander bucket per §5b — see module docstring.
DEMOGRAPHIC_VALUES: list[str] = sorted(
    [
        "all",
        "asian_pacific_islander",
        "black",
        "economically_disadvantaged",
        "english_learners",
        "hispanic",
        "multiracial",
        "native_american",
        "students_with_disabilities",
        "white",
    ]
)


# =============================================================================
# Bronze reading (per-file sheet + header-row lookup)
# =============================================================================


def _canonicalize_header(name: str) -> str:
    """Uppercase + collapse whitespace so header drift cannot break renames."""
    return " ".join(name.replace("\n", " ").replace("\r", " ").split()).upper()


def _read_readiness_sheet(path: Path, year: int) -> tuple[pl.DataFrame, dict]:
    """Read the single data sheet of one bronze xlsx.

    The shared ``read_bronze_file`` reads only a workbook's first sheet with
    header row 0; here the sheet NAME changes in 2025 and the 2022 header
    sits on row 1 under a DOE disclaimer, so this local helper resolves both
    via ``SHEET_NAME_BY_YEAR`` / ``HEADER_ROW_BY_YEAR`` (falling back to the
    first non-``SKIP_SHEETS`` sheet) and reads with the same ``dtype=str`` +
    ``SUPPRESSION_VALUES`` conventions as the shared XLSX path. ``dtype=str``
    preserves ID strings exactly; suppression markers (``TFS``, ``Too Few
    Students``, ``NA``, ...) arrive as NULL.

    Returns:
        ``(df, loss)`` — the all-Utf8 frame with canonicalized UPPERCASE
        headers, and a read-loss dict. Excel reads load whole sheets via
        pandas (no rows can be dropped at parse time), so raw == parsed by
        construction.
    """
    xl = pd.ExcelFile(path, engine="openpyxl")
    expected = SHEET_NAME_BY_YEAR.get(year)
    if expected is not None and expected in xl.sheet_names:
        target_sheet = expected
    else:
        target_sheet = next((s for s in xl.sheet_names if s not in SKIP_SHEETS), None)
        if target_sheet is None:
            raise ValueError(
                f"{path.name}: no readable data sheet found "
                f"(sheets={xl.sheet_names}, expected={expected!r})"
            )
        logger.warning(
            "%s: expected sheet %r not found; falling back to %r",
            path.name,
            expected,
            target_sheet,
        )

    pdf = pd.read_excel(
        xl,
        sheet_name=target_sheet,
        dtype=str,
        na_values=list(SUPPRESSION_VALUES),
        header=HEADER_ROW_BY_YEAR.get(year, 0),
    )
    pdf.columns = [_canonicalize_header(c) for c in pdf.columns]
    df = pl.from_pandas(pdf)
    loss = {"raw_rows": df.height, "parsed_rows": df.height, "format": "xlsx"}
    return df, loss


# =============================================================================
# Shared helpers (both eras)
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


def _check_sheet_year(df: pl.DataFrame, year: int, label: str) -> None:
    """Cross-check the sheet's School Year column against the filename year.

    Every bronze file stores a single calendar-year value equal to the
    filename year (verified for all 7 files; String-typed in 2021 but
    dtype=str makes every year a string here). A mismatch means a misnamed
    or mis-filled file — fail loudly.
    """
    seen = df["year"].drop_nulls().unique().to_list()
    if seen != [str(year)]:
        raise ValueError(
            f"{label}: sheet School Year values {seen} disagree with "
            f"filename year {year}"
        )


def _apply_detail_level_and_ids(df: pl.DataFrame) -> pl.DataFrame:
    """Derive detail_level from the NAME columns and normalize the ID keys.

    Name-based detection (state = 'All Systems', district = 'All Schools',
    else school) is identical across all 7 years. Aggregate rows carry the
    literal `ALL` sentinel in BOTH ID columns in every year (verified: 0
    empty ID cells anywhere; `ALL` appears on exactly the aggregate rows —
    the structure doc's original claim of null IDs was a typed-read
    artifact, see its Corrections section). `ALL` becomes NULL before zfill
    so padding only touches digit codes; zfill(3)/zfill(4) pads standard
    codes while passing 7-digit state-charter operator codes through
    untouched (never truncated).
    """
    df = df.with_columns(
        pl.when(pl.col("system_name") == "All Systems")
        .then(pl.lit("state"))
        .when(pl.col("school_name") == "All Schools")
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .alias("detail_level"),
    )
    return df.with_columns(
        pl.when(pl.col("district_code").cast(pl.Utf8) == "ALL")
        .then(None)
        .otherwise(pl.col("district_code").cast(pl.Utf8))
        .str.zfill(3)
        .alias("district_code"),
        pl.when(pl.col("school_code").cast(pl.Utf8) == "ALL")
        .then(None)
        .otherwise(pl.col("school_code").cast(pl.Utf8))
        .str.zfill(4)
        .alias("school_code"),
    )


def _normalize_demographic(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Normalize `demographic_raw` via the shared canonical path (§5).

    Records the EFFECTIVE alias slice (only the aliases this frame's labels
    actually hit) so the manifest stays reviewable while the unmapped guard
    still flags any label the shared map cannot place. All observed labels
    across all years are covered by DEMOGRAPHIC_ALIASES (verified), including
    the `American Indian/Alaskan` (2018-2021) -> `American Indian/Alaskan
    Native` (2022+) rename — both alias to native_american.
    """
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
    return df.drop("demographic_raw")


def _map_categorical(
    df: pl.DataFrame,
    raw_col: str,
    gold_col: str,
    mapping: dict[str, str],
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Apply a strict categorical map (strip+uppercase first) and record it.

    `default=None` routes unmapped bronze values into the manifest's
    unmapped_values, and manifest.write() raises on any of them — the last
    line of defense against silent vocabulary drift.
    """
    normalized = pl.col(raw_col).cast(pl.Utf8).str.strip_chars().str.to_uppercase()
    bronze_series = df.select(normalized.alias("_norm"))["_norm"]
    df = df.with_columns(
        normalized.replace_strict(mapping, default=None).alias(gold_col)
    )
    manifest.record_categorical(
        column=gold_col,
        map_dict=mapping,
        bronze_series=bronze_series,
        gold_series=df[gold_col],
    )
    return df.drop(raw_col)


def _common_transform(
    df: pl.DataFrame, year: int, manifest: TransformManifest, label: str
) -> pl.DataFrame:
    """Steps shared verbatim by both eras (post-rename)."""
    _check_sheet_year(df, year, label)
    df = df.with_columns(pl.lit(year).cast(pl.Int32).alias("year"))
    df = _apply_detail_level_and_ids(df)
    df = _normalize_demographic(df, manifest)
    df = _map_categorical(
        df, "grade_cluster_raw", "grade_cluster", GRADE_CLUSTER_MAP, manifest
    )
    return _map_categorical(df, "indicator_raw", "indicator", INDICATOR_MAP, manifest)


# =============================================================================
# Era transform functions
# =============================================================================

# Bronze columns common to both eras (canonicalized uppercase -> working name).
_BASE_RENAME: dict[str, str] = {
    "SCHOOL YEAR": "year",
    "SYSTEM ID": "district_code",
    "SYSTEM NAME": "system_name",
    "SCHOOL ID": "school_code",
    "SCHOOL NAME": "school_name",
    # School attribute (comma-separated grade list) — dimension-style
    # descriptor, not a measurement; verified present, then dropped.
    "GRADE CONFIGURATION": "grade_configuration",
    "GRADE CLUSTER": "grade_cluster_raw",
    "REPORTING LABEL": "demographic_raw",
    "INDICATOR": "indicator_raw",
    "INDICATOR SCORE": "indicator_score_raw",
}


def _transform_era_1(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Era 1 (2018, 2019): 10-column base layout.

    No Sub-Indicator and no Unbenchmarked Rate in bronze — both emitted as
    typed NULLs so the cross-era schema is uniform (NULL sub_indicator means
    "not collected", deliberately distinct from Era 2's `all`).
    """
    rename_map = dict(_BASE_RENAME)
    _require_columns(df, list(rename_map), f"{TOPIC} {year} era_1")
    df = df.rename(rename_map)
    df = _common_transform(df, year, manifest, f"{TOPIC} {year} era_1")

    df = df.with_columns(
        # 0-100 CCRPI score, preserved on its natural scale. Suppression
        # markers (TFS / NA) are already NULL from the read.
        pl.col("indicator_score_raw")
        .cast(pl.Float64, strict=False)
        .alias("indicator_score"),
        # Era-2-only columns: typed NULLs for harmonization.
        pl.lit(None).cast(pl.Utf8).alias("sub_indicator"),
        pl.lit(None).cast(pl.Float64).alias("unbenchmarked_rate"),
    )
    return df.select(STANDARD_COLUMNS)


def _transform_era_2(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Era 2 (2021-2025): 12-column layout with Sub-Indicator + Unbenchmarked Rate.

    One row per entity x cluster x demographic x indicator x sub-indicator.
    The bronze `NA` sub-indicator token (2021-2022; "no sub-breakdown
    exists") is nulled by the suppression-aware read and restored here with
    fill_null("NA") so the map and the manifest see the real bronze token;
    `NA` and `All` both map to gold `all` per the structure doc ("Treat `NA`
    as semantically equivalent to `All`").
    """
    rename_map = dict(_BASE_RENAME) | {
        "SUB-INDICATOR": "sub_indicator_raw",
        "UNBENCHMARKED RATE (ACCELERATED ENROLLMENT)": "unbenchmarked_rate_raw",
    }
    _require_columns(df, list(rename_map), f"{TOPIC} {year} era_2")
    df = df.rename(rename_map)
    df = _common_transform(df, year, manifest, f"{TOPIC} {year} era_2")

    df = df.with_columns(pl.col("sub_indicator_raw").fill_null("NA"))
    df = _map_categorical(
        df, "sub_indicator_raw", "sub_indicator", SUB_INDICATOR_MAP, manifest
    )

    df = df.with_columns(
        # 0-100 CCRPI score, preserved on its natural scale.
        pl.col("indicator_score_raw")
        .cast(pl.Float64, strict=False)
        .alias("indicator_score"),
        # Participation rate: bronze 0-100 -> canonical 0-1 proportion (§4).
        # 2021-2023 populate it only on Accelerated Enrollment rows;
        # 2024-2025 populate every row (non-AE values mirror the score).
        (pl.col("unbenchmarked_rate_raw").cast(pl.Float64, strict=False) / 100.0).alias(
            "unbenchmarked_rate"
        ),
    )
    return df.select(STANDARD_COLUMNS)


# =============================================================================
# File dispatcher
# =============================================================================

_ERA_FUNCS = {
    "era_1_base": _transform_era_1,
    "era_2_sub_indicator": _transform_era_2,
}


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read one bronze workbook, detect its era, and transform it."""
    year = extract_year_from_filename(path.name)
    if year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")

    df, loss = _read_readiness_sheet(path, year)
    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(
            f"{path.name} (year={year}): could not detect era from columns "
            f"{sorted(df.columns)} — update ERA_SIGNATURES if this is a new "
            f"schema."
        )
    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)

    if df.height == 0:
        logger.warning("Year %d: bronze file %s is empty, skipping", year, path.name)
        return None
    logger.info(
        "Processing %s (year=%d, era=%s, %d rows)", path.name, year, era, df.height
    )
    return _ERA_FUNCS[era](df, year, manifest)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for ccrpi_readiness."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file (read-loss accounted per file).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR, extensions=[".xlsx"]):
        result = transform_file(path, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize columns/dtypes across the two eras and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)
    logger.info("Combined %d rows across %d files", combined.height, len(all_dfs))

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean an alias-collapse bug and must raise, not be deduped away. (No
    # demographic collisions exist — the 10 bronze labels map 1:1 onto 10
    # canonical keys in every year — so aggregate_demographic_collisions is
    # not needed; see module docstring.)
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: each year ships exactly one file and the natural key is
    # unique within every file (0 duplicate key groups verified across all 7
    # years); prefer the row with a reported (non-null, higher) score as the
    # defensive safety net.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=[k for k in NATURAL_KEYS if k != "detail_level"],
        district_keys=[
            k for k in NATURAL_KEYS if k not in ("detail_level", "school_code")
        ],
        state_keys=[
            k
            for k in NATURAL_KEYS
            if k not in ("detail_level", "district_code", "school_code")
        ],
        sort_col="indicator_score",
    )

    # 4. Geography nulling (shared domain rules — transform and validator
    # read the same dict, so they cannot disagree). No §4b masks: every
    # observed metric value is within the 0-100 scale (module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. Expected null-rate spikes: unbenchmarked_rate is
    # structurally 100%% NULL in Era 1 (2018-2019, no bronze column) and
    # ~94%% NULL in 2021-2023 (populated only on Accelerated Enrollment
    # rows) — era gaps per bronze-data-structure.md, not bugs.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes (expected era gaps): %s", spike_result.details)
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

    Column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level`` — the contract properties (and the validator's schema
    check) follow it.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Georgia Insights (GaDOE) CCRPI Readiness component. Reports each "
            "Georgia public school's (and aggregated district / state) 0-100 "
            "score on the CCRPI Readiness indicators, per grade cluster "
            "(elementary/middle/high) and demographic subgroup. Six "
            "indicators vary by grade cluster: Literacy / At or Above "
            "Grade-Level Reading (E/M/H), Student Attendance / Attendance "
            "(E/M/H), Beyond the Core (E/M enrichment-course enrollment), "
            "Accelerated Enrollment (H college-level credit: AP, Dual "
            "Enrollment, IB, Advanced Academic, Cambridge), Pathway "
            "Completion (H), and College and Career Readiness (H). From 2021 "
            "the source adds a sub-indicator axis breaking each indicator "
            "into its components, plus an unbenchmarked participation rate "
            "for Accelerated Enrollment. Coverage: 2018-2019 and 2021-2025 "
            "(no 2020 — CCRPI was not calculated under the COVID federal "
            "waiver). This is the deep-dive into the CCRPI Readiness component "
            "only (by demographic, indicator, and sub-indicator); the overall "
            "CCRPI score and the side-by-side scorecard of all five rolled-up "
            "component scores — including the rolled-up Readiness component "
            "score — live in the `ccrpi_scoring_by_component` topic (the CCRPI "
            "overview)."
        ),
        title="CCRPI Readiness",
        summary=(
            "Georgia school readiness scores (the CCRPI Readiness component) "
            "by indicator, sub-indicator, grade cluster, and demographic "
            "subgroup, 2018-2025."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Ending calendar year of the school year (2024 = "
                    "2023-2024). Sourced from the bronze `School Year` "
                    "column, cross-checked against the filename year. No "
                    "2020 partition exists — CCRPI was waived that year."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "3-digit GOSA district code (zero-padded) for standard "
                    "districts; 7-digit code for state-charter systems "
                    "(preserved in full, never truncated). NULL for "
                    "state-level aggregate rows — the bronze `ALL` sentinel "
                    "becomes NULL. FK to districts dimension."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0194",
                "description": (
                    "4-digit GOSA school code (zero-padded). NULL for "
                    "district- and state-level aggregate rows — the bronze "
                    "`ALL` sentinel becomes NULL. FK to schools dimension "
                    "(composite key with district_code)."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "english_learners",
                "validValues": DEMOGRAPHIC_VALUES,
                "short_description": (
                    "Which student group the row covers - `all`, a race, or "
                    "a special population; all 10 groups appear every year."
                ),
                "description": (
                    "Canonical demographic code (FK to demographics "
                    "dimension). All 10 groups are reported in every year. "
                    "`all` is the unfiltered total. Race uses the combined "
                    "`asian_pacific_islander` bucket — the source publishes "
                    "the explicit `Asian/Pacific Islander` label and never "
                    "separate Asian or Pacific Islander rows in any year. "
                    "The `American Indian/Alaskan` (2018-2021) vs `American "
                    "Indian/Alaskan Native` (2022+) label rename resolves "
                    "via the shared demographic aliases."
                ),
            },
            {
                "name": "grade_cluster",
                "type": "string",
                "nullable": False,
                "example": "elementary",
                "validValues": sorted(set(GRADE_CLUSTER_MAP.values())),
                "short_description": (
                    "Grade band the row covers: elementary, middle, or high "
                    "(some indicators exist only at certain bands)."
                ),
                "description": (
                    "Grade band the row measures: `elementary`, `middle`, "
                    "or `high` (bronze single letters E/M/H). A school "
                    "spanning multiple bands has one row per band. "
                    "Indicator availability is cluster-bound: Accelerated "
                    "Enrollment, Pathway Completion, and College and Career "
                    "Readiness exist only at `high`; Beyond the Core only "
                    "at `elementary`/`middle` (verified in every year)."
                ),
            },
            {
                "name": "indicator",
                "type": "string",
                "nullable": False,
                "example": "beyond_the_core",
                "validValues": sorted(set(INDICATOR_MAP.values())),
                "short_description": (
                    "Which readiness measure the row reports (e.g. literacy, "
                    "attendance, accelerated enrollment, pathway "
                    "completion)."
                ),
                "description": (
                    "Readiness indicator measured, snake_case. `Beyond The "
                    "Core` (2018-2019 casing) unifies with `Beyond the Core` "
                    "(2021+). `literacy` / `student_attendance` (2018-2022) "
                    "are kept DISTINCT from their 2023+ successors "
                    "`at_or_above_grade_level_reading` / `attendance` — "
                    "GaDOE revised the underlying methodology with the 2023 "
                    "rename, so the two series must not be concatenated. "
                    "2022 published only 4 indicators (no Student "
                    "Attendance, no College and Career Readiness) per the "
                    "DOE pandemic disclaimer in that file."
                ),
            },
            {
                "name": "sub_indicator",
                "type": "string",
                "example": "fine_arts",
                "validValues": sorted(set(SUB_INDICATOR_MAP.values())),
                "short_description": (
                    "Component within the parent indicator (2021 on); `all` "
                    "is the rolled-up indicator score; NULL before 2021."
                ),
                "null_meaning": (
                    "Era 1 row (2018-2019): bronze had no Sub-Indicator "
                    "column, so no sub-breakdown was collected. NULL is "
                    "deliberately distinct from `all` (Era 2's explicit "
                    "rolled-up-score marker)."
                ),
                "description": (
                    "Component within the parent indicator (2021-2025 "
                    "only), snake_case. `all` is the rolled-up parent-"
                    "indicator score — it unifies bronze `All` (indicators "
                    "WITH sub-breakdowns) and bronze `NA` (2021-2022; "
                    "indicators with no sub-breakdown at all, i.e. Literacy "
                    "and Student Attendance). 16 sub-component values nest "
                    "strictly under their parent indicator (verified in "
                    "every Era 2 year); `fine_arts` and `world_language` "
                    "appear under BOTH `beyond_the_core` and "
                    "`pathway_completion`, and `international_baccalaureate` "
                    "under both `accelerated_enrollment` and (2022-2023 "
                    "only) `pathway_completion`. Label drift collapses: "
                    "casing variants (`Fine arts`, `Advanced academic`), "
                    "the 2021 verbose College and Career Readiness labels "
                    "(`Readiness score on the ACT, SAT, AP or IB`, `End of "
                    "pathway assessment (EOPA)`, `Entering TCSG/USG without "
                    "needing remediation`), and the ACT/SAT/AP/IB -> "
                    "ACT/SAT/AP/IB/Cambridge evolution all unify "
                    "(`act_sat_ap_ib_cambridge`, `eopa`, `tcsg_usg`). NOTE: "
                    "Cambridge exams qualify only from 2025 — "
                    "`act_sat_ap_ib_cambridge` rows in 2021-2024 measured "
                    "ACT/SAT/AP/IB only; this is one continuous series whose "
                    "qualifying-assessment list widened in 2025."
                ),
            },
            {
                "name": "indicator_score",
                "type": "float64",
                "unit": "score",
                "value_min": 0,
                "value_max": 100,
                "key_metric": True,
                "example": 78.52,
                "short_description": (
                    "Benchmarked readiness score on a 0-100 scale; NULL when "
                    "suppressed or not applicable."
                ),
                "null_meaning": (
                    "Suppressed by GaDOE (`TFS` / `Too Few Students` — too "
                    "few students in the subgroup) or not applicable / not "
                    "reported (`NA`)."
                ),
                "description": (
                    "Benchmarked CCRPI Readiness score on the 0-100 CCRPI "
                    "score scale (NOT a percentage — score columns are "
                    "exempt from the 0-1 convention per education "
                    "CLAUDE.md, matching ccrpi_content_mastery and "
                    "ccrpi_progress). Observed range is exactly [0, 100] in "
                    "every year; CCRPI caps component scores at 100."
                ),
            },
            {
                "name": "unbenchmarked_rate",
                "type": "float64",
                "unit": "proportion",
                "example": 0.4217,
                "null_meaning": (
                    "Era 1 row (2018-2019: column absent from bronze); a "
                    "2021-2023 non-Accelerated-Enrollment row (bronze `NA` "
                    "— rate published only for Accelerated Enrollment in "
                    "those years); or suppressed (`TFS` / `Too Few "
                    "Students`)."
                ),
                "description": (
                    "Raw Accelerated Enrollment participation rate before "
                    "CCRPI benchmark scaling, on the 0-1 decimal scale "
                    "(bronze 0-100, divided by 100). Population pattern "
                    "shifts mid-era (verified per year): 2021-2023 populate "
                    "it ONLY on `accelerated_enrollment` rows; 2024-2025 "
                    "populate every row, where non-AE values are a "
                    "cell-identical redundant copy of `indicator_score` "
                    "(divided by 100). Only `accelerated_enrollment` rows "
                    "carry independent information; on AE rows the rate and "
                    "the score are always co-published (co-null)."
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
                "Year coverage: 2018-2019 and 2021-2025. No 2020 partition "
                "— Georgia did not calculate CCRPI that year under the "
                "COVID federal accountability waiver. The gap is genuine, "
                "not a pipeline bug."
            ),
            (
                "Two schema eras. Era 1 (2018-2019) has no Sub-Indicator "
                "and no Unbenchmarked Rate columns — those gold columns are "
                "NULL for Era 1 rows. Era 2 (2021-2025) adds both. NULL "
                "sub_indicator (Era 1, not collected) is distinct from "
                "`all` (Era 2, explicit rolled-up score)."
            ),
            (
                "2022 is a partial release per the DOE disclaimer embedded "
                "in row 0 of that file's data sheet: no Student Attendance "
                "and no College and Career Readiness indicators. The "
                "transform reads the 2022 header from row 1."
            ),
            (
                "`indicator_score` is a 0-100 CCRPI score (exempt from the "
                "0-1 percentage convention). `unbenchmarked_rate` IS on the "
                "0-1 decimal scale (bronze 0-100, divided by 100)."
            ),
            (
                "`literacy` / `student_attendance` (2018-2022) and "
                "`at_or_above_grade_level_reading` / `attendance` "
                "(2023-2025) are deliberately separate indicator values — "
                "GaDOE revised the methodology alongside the 2023 rename; "
                "do not concatenate the series."
            ),
            (
                "Bronze aggregate rows carry the literal `ALL` sentinel in "
                "System ID / School ID in every year; these become NULL "
                "(state rows: both NULL; district rows: school_code NULL). "
                "Names live in the dimension tables, not in this fact "
                "table."
            ),
            (
                "Race uses the combined `asian_pacific_islander` bucket: "
                "the source publishes the explicit `Asian/Pacific Islander` "
                "label and never separate Asian or Pacific Islander rows. "
                "The split keys are never emitted."
            ),
        ],
        quality_checks=[
            {
                "name": "era1_no_sub_indicator",
                "description": (
                    "Era 1 (2018-2019) bronze has no Sub-Indicator column, "
                    "so sub_indicator is structurally NULL in those years."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "year IN (2018, 2019) AND sub_indicator IS NOT NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "era2_sub_indicator_always_present",
                "description": (
                    "Every Era 2 (2021-2025) bronze row carries a "
                    "Sub-Indicator token (`All`, `NA`, or a component), so "
                    "sub_indicator is never NULL from 2021 on (the bronze "
                    "`NA` token is restored and mapped to `all`, not left "
                    "NULL)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "year >= 2021 AND sub_indicator IS NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "era1_no_unbenchmarked_rate",
                "description": (
                    "Era 1 (2018-2019) bronze has no Unbenchmarked Rate "
                    "column, so unbenchmarked_rate is structurally NULL in "
                    "those years."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "year IN (2018, 2019) AND unbenchmarked_rate IS NOT NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "unbenchmarked_rate_ae_only_2021_2023",
                "description": (
                    "In 2021-2023 bronze publishes the unbenchmarked rate "
                    "ONLY for Accelerated Enrollment rows (verified: 0 "
                    "numeric values on non-AE rows in each of those files; "
                    "non-AE cells hold the `NA` marker)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "year IN (2021, 2022, 2023) AND "
                    "indicator <> 'accelerated_enrollment' AND "
                    "unbenchmarked_rate IS NOT NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "unbenchmarked_rate_mirrors_score_2024_2025",
                "description": (
                    "In 2024-2025 bronze publishes the unbenchmarked rate "
                    "on every row, where non-Accelerated-Enrollment values "
                    "are a cell-identical copy of Indicator Score (verified: "
                    "raw strings equal on 100%% of non-AE rows, both files). "
                    "Gold therefore has unbenchmarked_rate = "
                    "indicator_score / 100 on those rows, with matching "
                    "nullness."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "year IN (2024, 2025) AND "
                    "indicator <> 'accelerated_enrollment' AND "
                    "((unbenchmarked_rate IS NULL) <> (indicator_score IS NULL) "
                    "OR (unbenchmarked_rate IS NOT NULL AND "
                    "ABS(unbenchmarked_rate * 100 - indicator_score) > 0.001))"
                ),
                "mustBe": 0,
            },
            {
                "name": "ae_rate_and_score_co_null",
                "description": (
                    "On Accelerated Enrollment rows (Era 2), the "
                    "unbenchmarked rate and the indicator score are always "
                    "co-published: both numeric or both suppressed "
                    "(verified: 0 one-sided rows in every Era 2 file)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "year >= 2021 AND indicator = 'accelerated_enrollment' "
                    "AND (unbenchmarked_rate IS NULL) <> "
                    "(indicator_score IS NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "hs_only_indicators_high_cluster",
                "description": (
                    "Accelerated Enrollment, Pathway Completion, and "
                    "College and Career Readiness are high-school "
                    "indicators — published only at grade_cluster = 'high' "
                    "in every year (verified across all 7 files)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "indicator IN ('accelerated_enrollment', "
                    "'pathway_completion', 'college_and_career_readiness') "
                    "AND grade_cluster <> 'high'"
                ),
                "mustBe": 0,
            },
            {
                "name": "beyond_the_core_elementary_middle_only",
                "description": (
                    "Beyond the Core is published only at the elementary "
                    "and middle grade clusters in every year (verified "
                    "across all 7 files)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "indicator = 'beyond_the_core' AND "
                    "grade_cluster NOT IN ('elementary', 'middle')"
                ),
                "mustBe": 0,
            },
            {
                "name": "indicator_rename_era_boundary",
                "description": (
                    "The 2023 methodology revision renamed Literacy -> At "
                    "or Above Grade-Level Reading and Student Attendance -> "
                    "Attendance: the old labels appear only through 2022 "
                    "and the new labels only from 2023 (verified per year)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(indicator IN ('literacy', 'student_attendance') AND "
                    "year > 2022) OR "
                    "(indicator IN ('at_or_above_grade_level_reading', "
                    "'attendance') AND year < 2023)"
                ),
                "mustBe": 0,
            },
            {
                "name": "partial_2022_no_attendance_or_ccr",
                "description": (
                    "The 2022 release omitted Student Attendance and "
                    "College and Career Readiness per the DOE pandemic "
                    "disclaimer embedded in the file (verified: 2022 "
                    "publishes only 4 indicators)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year = 2022 AND "
                    "indicator IN ('student_attendance', 'attendance', "
                    "'college_and_career_readiness')"
                ),
                "mustBe": 0,
            },
            {
                "name": "sub_indicator_nests_under_parent",
                "description": (
                    "Every non-`all` sub-indicator nests under its parent "
                    "indicator (allowed pairs verified in every Era 2 "
                    "bronze file): Beyond the Core {career_exploratory, "
                    "computer_science, fine_arts, physical_education_health, "
                    "world_language}; Accelerated Enrollment "
                    "{advanced_placement, dual_enrollment, "
                    "international_baccalaureate, cambridge}; College and "
                    "Career Readiness {act_sat_ap_ib_cambridge, asvab, "
                    "eopa, tcsg_usg, work_based_learning}; Pathway "
                    "Completion {advanced_academic, ctae, fine_arts, "
                    "world_language, international_baccalaureate}. The "
                    "no-breakdown indicators (literacy, student_attendance, "
                    "at_or_above_grade_level_reading, attendance) carry "
                    "only `all`."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "sub_indicator IS NOT NULL AND sub_indicator <> 'all' "
                    "AND NOT ("
                    "(indicator = 'beyond_the_core' AND sub_indicator IN "
                    "('career_exploratory', 'computer_science', 'fine_arts', "
                    "'physical_education_health', 'world_language')) OR "
                    "(indicator = 'accelerated_enrollment' AND sub_indicator "
                    "IN ('advanced_placement', 'dual_enrollment', "
                    "'international_baccalaureate', 'cambridge')) OR "
                    "(indicator = 'college_and_career_readiness' AND "
                    "sub_indicator IN ('act_sat_ap_ib_cambridge', 'asvab', "
                    "'eopa', 'tcsg_usg', 'work_based_learning')) OR "
                    "(indicator = 'pathway_completion' AND sub_indicator IN "
                    "('advanced_academic', 'ctae', 'fine_arts', "
                    "'world_language', 'international_baccalaureate')))"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
