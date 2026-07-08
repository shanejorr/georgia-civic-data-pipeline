"""Transform bronze ccrpi_progress files into gold fact tables.

Source: Georgia Insights (GaDOE) — CCRPI Progress measures how much students
improve year-over-year on Georgia Milestones (English Language Arts and
Mathematics) and how much English Learners progress toward English Language
Proficiency (ELP). Each row reports an ``indicator_score`` (0-100 progress
score) plus, where published, an improvement ``indicator_target`` (0-100) and
a ``ccrpi_flag`` (green / yellow / red — did the entity meet its target).

Bronze coverage: 8 single-data-sheet xlsx files, 2018-2025, two NON-CONTIGUOUS
schema eras (era routed by column signature, never by year):

- **Era A — Score / Target / Flag** (2018, 2019, 2020, 2023, 2024, 2025):
  12 columns, one row per entity x grade cluster x demographic x indicator.
  2020 is ELP-only (GaDOE published only the Progress Towards Language
  Proficiency component that year) but keeps the Era A layout.
- **Era B — ELP band movement** (2021, 2022): 13 columns, ELP-only, one row
  per entity x grade cluster x ``English Learners``. The composite
  ``Progress Towards ELP Rate`` continues the Era A ELP ``indicator_score``
  time series; four extra band-movement shares have no Era A equivalent and
  are surfaced as Era-B-only ``pct_*`` proportion columns.

Design decisions (every invariant re-verified against THIS topic's 8 bronze
files during authoring — see bronze-data-structure.md):

- **Per-file data sheet lookup.** The data sheet name drifts across years
  (``Progress by Subgroup`` / ``ELP by Subgroup`` / ``ELP`` / ``Progress -
  Student Group``) and 2021/2022 carry an empty ``FAQs`` metadata sheet. The
  shared ``read_bronze_file`` reads only the first sheet, which here is
  always the data sheet — but the per-year lookup + first-non-skipped-sheet
  fallback in the local ``_read_progress_sheet`` helper is more explicit and
  resilient (precedent: attendance_dashboard's ``_read_data_sheets``). Excel
  reads load whole sheets via pandas, so read-loss raw == parsed by
  construction; the loss event is still recorded per file.

- **Detail level from the name columns.** ``System Name == 'All Systems'``
  -> state; else ``School Name == 'All Schools'`` -> district; else school.
  The name test is era- and year-stable, while the ID columns drift between
  Int64 / String / zero-padded / literal-``ALL`` encodings. ``ALL`` ID
  sentinels become NULL before zfill so padding touches only digit codes.

- **Indicator labels drift across years** and are collapsed to a 3-value
  canonical vocabulary (``english_language_arts_growth``,
  ``mathematics_growth``, ``progress_towards_elp``): 2018 uses growth-
  explicit labels, 2019/2020 drop "Growth" and say "Language Proficiency",
  2023+ spell out "English Language Proficiency". Era B has no Indicator
  column — every row is implicitly the ELP indicator (hard-coded constant,
  recorded in the manifest).

- **`100.00+` overage marker -> 100.0.** Appears in 2023 Indicator Score
  (4,131 cells) and the Era B composite rate (2021: 202, 2022: 466). It
  means "exceeded 100%% progress"; mapped to exactly 100 before the numeric
  cast so top performers keep the ceiling value instead of being NULLed.

- **Scales.** ``indicator_score`` and ``indicator_target`` are 0-100 CCRPI
  scores (exempt from the 0-1 percentage rule per education CLAUDE.md;
  ``unit: score`` with [0, 100] bounds). The four Era B band-movement
  columns are shares of the EL population on a 0-100 bronze scale, divided
  by 100 to the canonical 0-1 proportion scale (``unit: proportion``); they
  partition the population (sum = 1.0 within 0.0002 — authored as a quality
  check).

- **Flag.** Bronze ``G`` / ``Y`` / ``R`` -> ``green`` / ``yellow`` / ``red``
  (§16 vocabulary); ``NA`` (no flag) becomes NULL on read via
  SUPPRESSION_VALUES. ``G*``/green_star never appears in this topic's bronze
  (verified all 6 Era A files). Verified structural facts, authored as
  quality checks: indicator_target/flag are populated ONLY on the ELP
  indicator and ONLY for the english_learners demographic (every Era A year,
  including 2018 where ELP scores exist for all 10 demographics), and never
  in 2020-2022.

- **Asian / Pacific Islander is the combined bucket (§5b).** Every era ships
  a single explicit ``Asian/Pacific Islander`` label (spacing drifts in
  2019) and never a separate Asian or Pacific Islander row. The shared
  aliases canonicalize it to ``asian_pacific_islander``; the split keys are
  never emitted. No topic-local remap needed.

- **No demographic collisions.** The 10 bronze Reporting Labels map 1:1 onto
  10 distinct canonical keys in every year (label spelling drift in 2018 /
  2019 is alias-level, not collision-level), so
  ``aggregate_demographic_collisions`` is not needed; the natural-key
  collision guard still runs and would catch future drift.

- **Dedup tie-break**: each bronze year ships exactly one file and the
  natural key is unique within every file (0 duplicate key groups verified
  across all 8 years), so no duplicates are expected;
  ``sort_col="indicator_score"`` is the documented defensive tie-break
  (prefer the row with a reported, higher score over a placeholder).

- **No §4b masks.** After the overage mapping, every observed
  indicator_score / indicator_target / band value lies inside its defined
  scale (scores within [0, 100] — the global minimum 0.0 is a genuine 2021
  Era B composite rate with 100%% no-positive-movement; the Era A minimum is
  3.13 — indicator_targets within [5.74, 90]; bands within [0, 100] on the
  bronze
  scale). Nothing to NULL.
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

TOPIC = "ccrpi_progress"
BRONZE_DIR = Path("data/bronze/education/georgiainsights/ccrpi_progress")
GOLD_DIR = Path("data/gold/education/ccrpi_progress")
SOURCE_URL = "https://georgiainsights.gadoe.org/data-downloads/"

# Data sheet name per file year (drifts across years). Unknown years fall back
# to the first sheet not in SKIP_SHEETS so a new GaDOE naming convention does
# not silently read the wrong sheet.
SHEET_NAME_BY_YEAR: dict[int, str] = {
    2018: "Progress by Subgroup",
    2019: "Progress by Subgroup",
    2020: "Progress by Subgroup",
    2021: "ELP by Subgroup",
    2022: "ELP",
    2023: "Progress by Subgroup",
    2024: "Progress by Subgroup",
    2025: "Progress - Student Group",
}

# Metadata-only sheets that must never be ingested. The 2021/2022 `FAQs`
# sheet is empty (polars raises NoDataError on a direct read).
SKIP_SHEETS: set[str] = {"FAQs", "Read Me", "ReadMe", "Notes"}

# Era signatures over canonicalized (uppercase, whitespace-collapsed) headers.
# Ordered most-specific first; detect_era_by_columns returns the first match
# and transform_file raises if nothing matches (unknown schema fails loudly).
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_a_score_target_flag": ["INDICATOR", "INDICATOR SCORE", "TARGET", "FLAG"],
    "era_b_elp_band_movement": [
        "PROGRESS TOWARDS ELP RATE",
        "NO POSITIVE MOVEMENT",
        "MOVED ONE BAND",
    ],
}

# Indicator label drift (Era A): 2018 growth-explicit labels; 2019/2020 say
# "Language Proficiency"; 2023+ spell out "English". All three concepts are
# continuous time series — only the label changed.
INDICATOR_MAP: dict[str, str] = {
    "ELA GROWTH": "english_language_arts_growth",
    "MATHEMATICS GROWTH": "mathematics_growth",
    "ELP PROGRESS": "progress_towards_elp",
    "ENGLISH LANGUAGE ARTS": "english_language_arts_growth",
    "MATHEMATICS": "mathematics_growth",
    "PROGRESS TOWARDS LANGUAGE PROFICIENCY": "progress_towards_elp",
    "PROGRESS TOWARDS ENGLISH LANGUAGE PROFICIENCY": "progress_towards_elp",
}

# Grade cluster single letters -> snake_case words (E/M/H in every year).
GRADE_CLUSTER_MAP: dict[str, str] = {
    "E": "elementary",
    "M": "middle",
    "H": "high",
}

# CCRPI flag codes -> §16 canonical colors. Bronze `NA` (no flag) becomes
# NULL via SUPPRESSION_VALUES on read; `G*` never appears in this topic.
CCRPI_FLAG_MAP: dict[str, str] = {
    "G": "green",
    "Y": "yellow",
    "R": "red",
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
    "ccrpi_flag",
    "indicator_score",
    "indicator_target",
    "pct_no_positive_movement",
    "pct_moved_less_than_one_band",
    "pct_moved_one_band",
    "pct_moved_more_than_one_band",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "demographic": pl.Utf8,
    "detail_level": pl.Utf8,
    "grade_cluster": pl.Utf8,
    "indicator": pl.Utf8,
    "ccrpi_flag": pl.Utf8,
    "indicator_score": pl.Float64,
    "indicator_target": pl.Float64,
    "pct_no_positive_movement": pl.Float64,
    "pct_moved_less_than_one_band": pl.Float64,
    "pct_moved_one_band": pl.Float64,
    "pct_moved_more_than_one_band": pl.Float64,
}

METRIC_COLUMNS: list[str] = [
    "indicator_score",
    "indicator_target",
    "pct_no_positive_movement",
    "pct_moved_less_than_one_band",
    "pct_moved_one_band",
    "pct_moved_more_than_one_band",
]

BAND_MOVEMENT_COLUMNS: list[str] = [
    "pct_no_positive_movement",
    "pct_moved_less_than_one_band",
    "pct_moved_one_band",
    "pct_moved_more_than_one_band",
]

# `indicator` is part of the key: Era A reports up to three indicators per
# entity x cluster x demographic, Era B exactly one.
NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "detail_level",
    "grade_cluster",
    "indicator",
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
# Bronze reading (per-file sheet lookup)
# =============================================================================


def _canonicalize_header(name: str) -> str:
    """Uppercase + collapse whitespace so header drift cannot break renames."""
    return " ".join(name.replace("\n", " ").replace("\r", " ").split()).upper()


def _read_progress_sheet(path: Path, year: int) -> tuple[pl.DataFrame, dict]:
    """Read the single data sheet of one bronze xlsx.

    The shared ``read_bronze_file`` reads only a workbook's first sheet; the
    sheet NAME drifts across years here, so this local helper resolves it via
    ``SHEET_NAME_BY_YEAR`` (falling back to the first non-``SKIP_SHEETS``
    sheet) and reads with the same ``dtype=str`` + ``SUPPRESSION_VALUES``
    conventions as the shared XLSX path. ``dtype=str`` keeps mixed-type
    columns (numbers + ``100.00+``) intact and preserves zero-padded IDs;
    suppression markers (``TFS``, ``NA``, ...) arrive as NULL.

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
    filename year (verified for all 8 files; String-typed in 2021). A
    mismatch means a misnamed or mis-filled file — fail loudly.
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
    else school) is identical across all 8 years, while the ID encodings
    drift (Int64 vs String, null vs literal 'ALL', zero-padded or not).
    'ALL' sentinels become NULL before zfill so padding only touches digit
    codes; zfill(3)/zfill(4) pads standard codes while passing 7-digit
    state-charter operator codes through untouched (never truncated).
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
    the 2018/2019 spelling drift (American Indian, Asian/Pacific spacing,
    Disability casing).
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


def _score_expr(raw_col: str, alias: str) -> pl.Expr:
    """Cast a 0-100 score column to Float64, mapping `100.00+` to 100.

    The overage marker means "exceeded 100%% progress" (2023 Indicator Score;
    2021/2022 composite ELP rate). Mapping it to exactly 100 before the cast
    preserves top performers at the ceiling instead of NULLing them via
    strict=False. Residual non-numeric strings (none observed beyond the
    suppression markers the reader already nulled) would become NULL.
    """
    return (
        pl.col(raw_col)
        .cast(pl.Utf8)
        .str.strip_chars()
        .replace({"100.00+": "100"})
        .cast(pl.Float64, strict=False)
        .alias(alias)
    )


# =============================================================================
# Era transform functions
# =============================================================================


def _transform_era_a(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Era A (2018, 2019, 2020, 2023, 2024, 2025): Score / Target / Flag.

    One row per entity x grade cluster x demographic x indicator. 2020 is
    ELP-only (1 indicator, english_learners only, no targets/flags). The
    four Era-B band-movement columns do not exist — emitted as typed NULLs
    so the cross-era schema is uniform.
    """
    rename_map = {
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
        "TARGET": "indicator_target_raw",
        "FLAG": "ccrpi_flag_raw",
    }
    _require_columns(df, list(rename_map), f"{TOPIC} {year} era_a")
    df = df.rename(rename_map)

    _check_sheet_year(df, year, f"{TOPIC} {year} era_a")
    df = df.with_columns(pl.lit(year).cast(pl.Int32).alias("year"))

    df = _apply_detail_level_and_ids(df)
    df = _normalize_demographic(df, manifest)
    df = _map_categorical(
        df, "grade_cluster_raw", "grade_cluster", GRADE_CLUSTER_MAP, manifest
    )
    df = _map_categorical(df, "indicator_raw", "indicator", INDICATOR_MAP, manifest)
    df = _map_categorical(df, "ccrpi_flag_raw", "ccrpi_flag", CCRPI_FLAG_MAP, manifest)

    df = df.with_columns(
        # 0-100 score; `100.00+` (2023 only in Era A) -> 100.
        _score_expr("indicator_score_raw", "indicator_score"),
        # 0-100 indicator_target; bronze `NA` (no target applies) and `TFS`
        # (suppressed) already arrive as NULL via the dtype=str +
        # SUPPRESSION_VALUES read, so a plain cast suffices.
        pl.col("indicator_target_raw")
        .cast(pl.Float64, strict=False)
        .alias("indicator_target"),
        # Era-B-only band-movement columns: typed NULLs for harmonization.
        *[pl.lit(None).cast(pl.Float64).alias(c) for c in BAND_MOVEMENT_COLUMNS],
    )
    return df.select(STANDARD_COLUMNS)


def _transform_era_b(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Era B (2021, 2022): ELP-only band-movement schema.

    One row per entity x grade cluster x `English Learners`. The composite
    `Progress Towards ELP Rate` continues the Era A ELP indicator_score
    series (same 0-100 concept, same `100.00+` overage marker); the four
    band shares are divided by 100 to the 0-1 proportion scale.
    `indicator_target` / `ccrpi_flag` do not exist in this era — emitted as
    typed NULLs.
    """
    rename_map = {
        "SCHOOL YEAR": "year",
        "SYSTEM ID": "district_code",
        "SYSTEM NAME": "system_name",
        "SCHOOL ID": "school_code",
        "SCHOOL NAME": "school_name",
        "GRADE CONFIGURATION": "grade_configuration",
        "GRADE CLUSTER": "grade_cluster_raw",
        "REPORTING LABEL": "demographic_raw",
        "NO POSITIVE MOVEMENT": "no_positive_movement_raw",
        "MOVED LESS THAN ONE BAND": "moved_less_than_one_band_raw",
        "MOVED ONE BAND": "moved_one_band_raw",
        "MOVED MORE THAN ONE BAND": "moved_more_than_one_band_raw",
        "PROGRESS TOWARDS ELP RATE": "indicator_score_raw",
    }
    _require_columns(df, list(rename_map), f"{TOPIC} {year} era_b")
    df = df.rename(rename_map)

    _check_sheet_year(df, year, f"{TOPIC} {year} era_b")
    df = df.with_columns(pl.lit(year).cast(pl.Int32).alias("year"))

    df = _apply_detail_level_and_ids(df)
    df = _normalize_demographic(df, manifest)
    df = _map_categorical(
        df, "grade_cluster_raw", "grade_cluster", GRADE_CLUSTER_MAP, manifest
    )

    # Era B has no Indicator column — the whole sheet IS the ELP indicator.
    # Hard-code the canonical value and record the implicit mapping so the
    # manifest's `indicator` coverage spans Era B too.
    df = df.with_columns(pl.lit("progress_towards_elp").alias("indicator"))
    manifest.record_categorical(
        column="indicator",
        map_dict={"PROGRESS TOWARDS ELP RATE": "progress_towards_elp"},
        bronze_series=pl.Series(
            "_era_b_implicit", ["PROGRESS TOWARDS ELP RATE"] * df.height
        ),
        gold_series=df["indicator"],
    )

    band_renames = [
        ("no_positive_movement_raw", "pct_no_positive_movement"),
        ("moved_less_than_one_band_raw", "pct_moved_less_than_one_band"),
        ("moved_one_band_raw", "pct_moved_one_band"),
        ("moved_more_than_one_band_raw", "pct_moved_more_than_one_band"),
    ]
    df = df.with_columns(
        # Composite ELP rate -> indicator_score (0-100 score; `100.00+` -> 100).
        _score_expr("indicator_score_raw", "indicator_score"),
        # Band shares: bronze 0-100 -> canonical 0-1 proportion scale (§4).
        # `TFS` already NULL via the suppression-aware read.
        *[
            (pl.col(raw).cast(pl.Float64, strict=False) / 100.0).alias(gold)
            for raw, gold in band_renames
        ],
        # Era A-only columns: typed NULLs for harmonization.
        pl.lit(None).cast(pl.Float64).alias("indicator_target"),
        pl.lit(None).cast(pl.Utf8).alias("ccrpi_flag"),
    )
    return df.select(STANDARD_COLUMNS)


# =============================================================================
# File dispatcher
# =============================================================================

_ERA_FUNCS = {
    "era_a_score_target_flag": _transform_era_a,
    "era_b_elp_band_movement": _transform_era_b,
}


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read one bronze workbook, detect its era, and transform it."""
    year = extract_year_from_filename(path.name)
    if year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")

    df, loss = _read_progress_sheet(path, year)
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
    """Run the full bronze-to-gold pipeline for ccrpi_progress."""
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
    # unique within every file (0 duplicate key groups verified across all 8
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
    # observed value is within its metric's defined scale (module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. Expected null-rate spikes: indicator_target/ccrpi_flag
    # are
    # structurally absent in 2020-2022 and the band columns exist only in
    # 2021-2022 — era gaps per bronze-data-structure.md, not bugs.
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
            "Georgia Insights (GaDOE) CCRPI Progress component. Measures the "
            "rate at which students improve year-over-year on Georgia "
            "Milestones assessments (English Language Arts and Mathematics) "
            "and the rate at which English Learners progress toward English "
            "Language Proficiency (ELP), for every Georgia public school, "
            "school district, and the state. Reports a 0-100 "
            "`indicator_score` plus, where published, a 0-100 improvement "
            "`indicator_target` and a green/yellow/red `ccrpi_flag`, per grade "
            "cluster "
            "(elementary/middle/high), demographic subgroup, and indicator. "
            "2020 is ELP-only (the only component GaDOE published that "
            "year). For 2021 and 2022 GaDOE published only the ELP component "
            "in a band-movement schema: four Era-B-only `pct_*` proportion "
            "columns partition English Learners by ELP band movement, and "
            "the composite ELP rate continues the `indicator_score` series. "
            "Coverage: 2018-2025, 8 files, no gap years. This is the deep-dive "
            "into the CCRPI Progress component only (by demographic and "
            "indicator); the overall CCRPI score and the side-by-side "
            "scorecard of all five rolled-up component scores — including the "
            "rolled-up Progress component score — live in the "
            "`ccrpi_scoring_by_component` topic (the CCRPI overview)."
        ),
        title="CCRPI Progress",
        summary=(
            "Georgia student year-over-year growth scores (the CCRPI "
            "Progress component) by indicator, grade cluster, and "
            "demographic subgroup, 2018-2025."
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
                    "column, cross-checked against the filename year."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "3-digit GOSA district code (zero-padded) for standard "
                    "districts; 7-digit code for state-charter systems. "
                    "NULL for state-level aggregate rows. The bronze `ALL` "
                    "sentinel (2021 state rows) becomes NULL. FK to "
                    "districts dimension."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0194",
                "description": (
                    "4-digit GOSA school code (zero-padded; some bronze "
                    "years strip the leading zero, others pre-pad). NULL "
                    "for district- and state-level aggregate rows (bronze "
                    "encodes these as the literal `ALL` or a true null "
                    "depending on year). FK to schools dimension (composite "
                    "key with district_code)."
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
                    "a special population; ELP rows are English-learners-"
                    "only from 2019 on."
                ),
                "description": (
                    "Canonical demographic code (FK to demographics "
                    "dimension). `all` is the unfiltered total. Race uses "
                    "the combined `asian_pacific_islander` bucket — the "
                    "source never publishes separate Asian or Pacific "
                    "Islander rows in any year. Era A ELA/Math rows cover "
                    "all 10 groups; ELP rows cover all 10 groups in 2018 "
                    "but only `english_learners` from 2019 on; the ELP-only "
                    "releases (2020-2022) contain only `english_learners`. "
                    "Bronze label spelling drift (American Indian variants, "
                    "Asian/Pacific spacing, Disability casing) resolves via "
                    "the shared demographic aliases."
                ),
            },
            {
                "name": "grade_cluster",
                "type": "string",
                "nullable": False,
                "example": "elementary",
                "validValues": sorted(set(GRADE_CLUSTER_MAP.values())),
                "short_description": (
                    "Grade band the row covers: elementary, middle, or high."
                ),
                "description": (
                    "Grade band the row measures: `elementary`, `middle`, "
                    "or `high` (bronze single letters E/M/H). A school "
                    "spanning multiple bands has one row per band."
                ),
            },
            {
                "name": "indicator",
                "type": "string",
                "nullable": False,
                "example": "progress_towards_elp",
                "validValues": sorted(set(INDICATOR_MAP.values())),
                "short_description": (
                    "Which growth measure the row reports: ELA growth, math "
                    "growth, or progress toward English language "
                    "proficiency."
                ),
                "description": (
                    "Progress indicator measured. Source labels drift "
                    "(2018: `ELA Growth` / `Mathematics Growth` / `ELP "
                    "Progress`; 2019-2020: `English Language Arts` / "
                    "`Mathematics` / `Progress Towards Language "
                    "Proficiency`; 2023+: spelled-out `...English Language "
                    "Proficiency`) and collapse to three canonical values "
                    "so each forms a continuous time series. Every Era B "
                    "(2021-2022) row is `progress_towards_elp` — that era's "
                    "sheet has no indicator column because it reports only "
                    "the ELP component."
                ),
            },
            {
                "name": "ccrpi_flag",
                "type": "string",
                "exclude_from_grain": True,
                "example": "green",
                "validValues": sorted(set(CCRPI_FLAG_MAP.values())),
                "short_description": (
                    "Improvement-target flag (green = met, yellow, red); set "
                    "only on English-learner ELP-progress rows."
                ),
                "null_meaning": (
                    "No flag published: bronze `NA` (target not applicable "
                    "or suppressed), all ELA/Math rows, all non-EL rows, "
                    "and all of 2020-2022."
                ),
                "description": (
                    "CCRPI improvement-target flag: `green` (met target), "
                    "`yellow`, `red`. `green_star` exists in the §16 CCRPI "
                    "vocabulary but never appears in this topic's bronze "
                    "(verified 2018-2025). Populated ONLY on "
                    "`progress_towards_elp` rows for the `english_learners` "
                    "demographic in 2018, 2019, 2023, 2024, 2025 — ELA/Math "
                    "growth rows and the 2020-2022 releases never carry a "
                    "flag. Derived performance attribute functionally "
                    "determined by the rest of the row key, so excluded "
                    "from the contract grain."
                ),
            },
            {
                "name": "indicator_score",
                "type": "float64",
                "unit": "score",
                "value_min": 0,
                "value_max": 100,
                "key_metric": True,
                "example": 82.72,
                "short_description": (
                    "Progress (growth) score on a 0-100 scale; NULL when "
                    "suppressed or not applicable."
                ),
                "null_meaning": (
                    "Suppressed by GaDOE (`TFS` — Too Few Students) or not "
                    "applicable/not published (`NA`)."
                ),
                "description": (
                    "Progress score on the 0-100 CCRPI score scale (NOT a "
                    "percentage — score columns are exempt from the 0-1 "
                    "convention). Era A: the bronze `Indicator Score`. Era "
                    "B (2021-2022): the composite `Progress Towards ELP "
                    "Rate`, the same ELP-progress concept, so the ELP time "
                    "series is continuous across eras. The `100.00+` "
                    "overage marker (2023: 4,131 cells; 2021: 202; 2022: "
                    "466) means progress exceeded 100%% and is mapped to "
                    "exactly 100 before the numeric cast. Observed range "
                    "0-100 (the minimum 0.0 is a genuine 2021 Era B "
                    "composite rate — 100%% of that school's English "
                    "Learners had no positive band movement; the Era A "
                    "minimum is 3.13)."
                ),
            },
            {
                "name": "indicator_target",
                "type": "float64",
                "unit": "score",
                "value_min": 0,
                "value_max": 100,
                "example": 75.0,
                "null_meaning": (
                    "Bronze `NA` (no target applies — all ELA/Math rows, "
                    "all non-EL rows, all of 2020-2022) or `TFS` (target "
                    "suppressed for small N)."
                ),
                "description": (
                    "ELP improvement target on the same 0-100 score scale "
                    "as indicator_score. Populated ONLY on "
                    "`progress_towards_elp` rows for the `english_learners` "
                    "demographic in 2018, 2019, 2023, 2024, 2025 (Era B "
                    "bronze has no target column; 2020 published none). "
                    "Observed range 5.74-90."
                ),
            },
            {
                "name": "pct_no_positive_movement",
                "type": "float64",
                "unit": "proportion",
                "example": 0.1963,
                "null_meaning": (
                    "Era A row (column exists only in the 2021-2022 "
                    "schema), or suppressed (`TFS`) — Era B suppression is "
                    "all-or-nothing across the four band columns and the "
                    "composite rate."
                ),
                "description": (
                    "Share of English Learners with no positive ELP "
                    "band movement. 0-1 decimal scale (bronze 0-100, "
                    "divided by 100). Era B (2021-2022) only; 100%% NULL in "
                    "every Era A year. The four band columns partition the "
                    "EL population (sum = 1.0 within rounding)."
                ),
            },
            {
                "name": "pct_moved_less_than_one_band",
                "type": "float64",
                "unit": "proportion",
                "example": 0.1586,
                "null_meaning": (
                    "Era A row (column exists only in the 2021-2022 "
                    "schema), or suppressed (`TFS`)."
                ),
                "description": (
                    "Share of English Learners whose ELP growth was "
                    "positive but less than one band. 0-1 decimal scale "
                    "(bronze 0-100, divided by 100). Era B (2021-2022) "
                    "only; 100%% NULL in every Era A year."
                ),
            },
            {
                "name": "pct_moved_one_band",
                "type": "float64",
                "unit": "proportion",
                "example": 0.2487,
                "null_meaning": (
                    "Era A row (column exists only in the 2021-2022 "
                    "schema), or suppressed (`TFS`)."
                ),
                "description": (
                    "Share of English Learners who moved up exactly one "
                    "ELP band. 0-1 decimal scale (bronze 0-100, divided by "
                    "100). Era B (2021-2022) only; 100%% NULL in every Era "
                    "A year."
                ),
            },
            {
                "name": "pct_moved_more_than_one_band",
                "type": "float64",
                "unit": "proportion",
                "example": 0.3964,
                "null_meaning": (
                    "Era A row (column exists only in the 2021-2022 "
                    "schema), or suppressed (`TFS`)."
                ),
                "description": (
                    "Share of English Learners who moved up more than one "
                    "ELP band. 0-1 decimal scale (bronze 0-100, divided by "
                    "100). Era B (2021-2022) only; 100%% NULL in every Era "
                    "A year."
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
                "Two non-contiguous schema eras. Era A (2018-2020, "
                "2023-2025): Score / Target / Flag. Era B (2021-2022): "
                "ELP-only band movement. The Era B composite ELP rate is "
                "published as `indicator_score` with `indicator = "
                "'progress_towards_elp'`, so the ELP series is continuous "
                "2018-2025."
            ),
            (
                "indicator_score and indicator_target are 0-100 CCRPI scores "
                "(exempt from the 0-1 percentage convention). The four "
                "band-movement `pct_*` columns ARE 0-1 proportions "
                "(bronze 0-100, divided by 100) and partition the EL "
                "population."
            ),
            (
                "The `100.00+` overage marker (2023 indicator score; "
                "2021/2022 composite ELP rate) maps to exactly 100 before "
                "the numeric cast — progress exceeded 100%, so the ceiling "
                "value is preserved rather than NULLed."
            ),
            (
                "indicator_target and ccrpi_flag are published ONLY for the "
                "ELP indicator x english_learners cells, and never in "
                "2020-2022. ELA/Math growth rows carry scores only."
            ),
            (
                "Demographic coverage varies by design: ELA/Math rows span "
                "10 demographic groups; ELP rows span all 10 groups in "
                "2018 but only english_learners from 2019 on; 2020-2022 "
                "(ELP-only releases) contain only english_learners."
            ),
            (
                "Race uses the combined `asian_pacific_islander` bucket: "
                "the source publishes the explicit `Asian/Pacific "
                "Islander` label and never separate Asian or Pacific "
                "Islander rows. The split keys are never emitted."
            ),
            (
                "State-level rows have NULL district_code and school_code; "
                "district rows have NULL school_code. Bronze `ALL` "
                "sentinels become NULL. Names live in the dimension "
                "tables, not in this fact table."
            ),
        ],
        quality_checks=[
            {
                "name": "band_movement_partitions_to_one",
                "description": (
                    "The four ELP band-movement proportions partition the "
                    "EL population: where all four are populated they sum "
                    "to 1.0 (+/-0.005). Verified on both Era B bronze "
                    "files: max deviation 0.0002 (independent rounding of "
                    "each share to 2 decimals on the 0-100 scale)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "pct_no_positive_movement IS NOT NULL AND "
                    "pct_moved_less_than_one_band IS NOT NULL AND "
                    "pct_moved_one_band IS NOT NULL AND "
                    "pct_moved_more_than_one_band IS NOT NULL AND "
                    "ABS(pct_no_positive_movement + "
                    "pct_moved_less_than_one_band + pct_moved_one_band + "
                    "pct_moved_more_than_one_band - 1.0) > 0.005"
                ),
                "mustBe": 0,
            },
            {
                "name": "band_movement_suppression_all_or_nothing",
                "description": (
                    "Era B suppression is all-or-nothing: within 2021-2022, "
                    "a row has the four band columns and indicator_score "
                    "either all populated or all NULL. Verified on both "
                    "Era B bronze files: 0 partially suppressed rows."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year IN (2021, 2022) "
                    "AND ((pct_no_positive_movement IS NULL) <> "
                    "(pct_moved_less_than_one_band IS NULL) OR "
                    "(pct_no_positive_movement IS NULL) <> "
                    "(pct_moved_one_band IS NULL) OR "
                    "(pct_no_positive_movement IS NULL) <> "
                    "(pct_moved_more_than_one_band IS NULL) OR "
                    "(pct_no_positive_movement IS NULL) <> "
                    "(indicator_score IS NULL))"
                ),
                "mustBe": 0,
            },
            {
                "name": "band_movement_era_b_only",
                "description": (
                    "The four band-movement columns exist only in the "
                    "2021-2022 bronze schema — structurally NULL in every "
                    "other year."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "year NOT IN (2021, 2022) AND "
                    "(pct_no_positive_movement IS NOT NULL OR "
                    "pct_moved_less_than_one_band IS NOT NULL OR "
                    "pct_moved_one_band IS NOT NULL OR "
                    "pct_moved_more_than_one_band IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "indicator_target_flag_only_on_elp_indicator",
                "description": (
                    "indicator_target and ccrpi_flag are published only for "
                    "the Progress Towards ELP indicator — ELA/Math growth "
                    "rows never carry either (verified in every Era A bronze "
                    "file, including 2018)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(indicator_target IS NOT NULL OR ccrpi_flag IS NOT NULL) "
                    "AND indicator <> 'progress_towards_elp'"
                ),
                "mustBe": 0,
            },
            {
                "name": "indicator_target_flag_only_for_english_learners",
                "description": (
                    "indicator_target and ccrpi_flag are published only for "
                    "the english_learners demographic — in 2018, where ELP "
                    "rows span all 10 demographic groups, the 9 non-EL "
                    "groups carry scores but never a target or flag "
                    "(verified in bronze)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(indicator_target IS NOT NULL OR ccrpi_flag IS NOT NULL) "
                    "AND demographic <> 'english_learners'"
                ),
                "mustBe": 0,
            },
            {
                "name": "indicator_target_flag_absent_2020_through_2022",
                "description": (
                    "No targets or flags exist in 2020-2022: the 2020 "
                    "ELP-only release published neither, and the Era B "
                    "(2021-2022) schema has no target/flag columns."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "year IN (2020, 2021, 2022) AND "
                    "(indicator_target IS NOT NULL OR ccrpi_flag IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "elp_only_years_english_learners_only",
                "description": (
                    "The ELP-only releases (2020, 2021, 2022) contain only "
                    "the english_learners demographic (verified in bronze: "
                    "one Reporting Label value in each of those files)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "year IN (2020, 2021, 2022) AND "
                    "demographic <> 'english_learners'"
                ),
                "mustBe": 0,
            },
            {
                "name": "elp_only_years_elp_indicator_only",
                "description": (
                    "The ELP-only releases (2020, 2021, 2022) contain only "
                    "the progress_towards_elp indicator (verified in "
                    "bronze: 2020 has a single Indicator value; the Era B "
                    "sheets have no indicator column at all)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "year IN (2020, 2021, 2022) AND "
                    "indicator <> 'progress_towards_elp'"
                ),
                "mustBe": 0,
            },
            {
                "name": "elp_rows_english_learners_only_post_2018",
                "description": (
                    "From 2019 on, ELP-indicator rows exist only for the "
                    "english_learners demographic — only 2018 publishes "
                    "ELP rows for all 10 demographic groups (verified in "
                    "bronze; see the structure doc's Corrections section). "
                    "Year-pinned to the verified years so a legitimate "
                    "future re-expansion of ELP demographic coverage "
                    "cannot break the pipeline; 2020-2022 are covered by "
                    "elp_only_years_english_learners_only."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "year IN (2019, 2023, 2024, 2025) AND "
                    "indicator = 'progress_towards_elp' AND "
                    "demographic <> 'english_learners'"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
