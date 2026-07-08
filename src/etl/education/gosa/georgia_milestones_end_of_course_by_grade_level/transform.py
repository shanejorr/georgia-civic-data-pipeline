"""Transform bronze georgia_milestones_end_of_course_by_grade_level
files to gold.

Source: Governor's Office of Student Achievement (GOSA) — Georgia Milestones
End-of-Course (EOC) assessment results **disaggregated by grade level**. For
each (entity x grade x demographic subgroup x course) combination the bronze
file reports the count and percentage of test-takers at each of four
achievement levels (Beginning / Developing / Proficient / Distinguished
Learner) plus the overall Number Tested. Coverage spans school years 2014-15
through 2023-24 (9 files; 2019-20 absent — EOC testing suspended during the
initial COVID-19 closures).

Key data-model decisions (from bronze-data-structure.md, verified against
bronze where noted):

- **Two bronze eras, one shared transform route.** Era 1 (2015-2023, 8
  files) is a 17-column tidy format; Era 2 (2024, 1 file) prepends a single
  constant-valued column (``#ASSMT_CD`` = "EOC_by_GRADE") that is dropped
  before the shared route runs. Achievement-level column names are identical
  across eras. Era detection is by column signature (``#ASSMT_CD`` presence),
  never by year range.

- **Grade is a real categorical and part of the natural key.** Unlike the
  non-by-grade sister topic (constant "ALL GRADES"), ``ACDMC_LVL`` carries
  real grades 7-12. Bronze padding differs by era (2015-2019 unpadded
  ``7``..``12``; 2021-2024 zero-padded ``07``..``12``); the shared
  ``normalize_grade_column`` resolves both spellings to the canonical
  2-char zero-padded form per data-cleaning-standards §16.

- **Canonical metric names per §16**: ``num_tested``,
  ``num_<level>_learner`` / ``pct_<level>_learner`` for the four achievement
  bands, plus the two derived cumulatives ``pct_developing_learner_or_above``
  (= developing + proficient + distinguished) and
  ``pct_proficient_learner_or_above`` (= proficient + distinguished).
  Polars ``+`` NULL-propagation makes either cumulative NULL whenever any
  summand is NULL (suppression-as-NULL preserved). Publisher rounding of the
  per-level percentages can push a cumulative sum one rounding unit above
  1.0 (e.g. 1.001); ``_cap_or_above`` snaps overages within 0.005 back to
  1.0 while letting anything larger through so the bounded-proportion
  validator would flag a genuine anomaly.

- **Percentage scaling**: every ``*_PCT`` column is on the 0-100 bronze
  scale and is divided by 100 (gold 0-1 per §4). All six pct columns are
  bounded proportions (``unit: proportion``).

- **Demographics use the split race convention.** Bronze publishes separate
  ``Asian`` and ``Native Hawaiian or Other Pacific Islander`` rows in every
  year (verified across all 9 files), so bare "Asian" is genuinely
  Asian-only and maps to canonical ``asian`` — no §5b combined-bucket remap.
  The 22 cross-era labels (18-core + Active Duty [2021 only], Homeless
  [2021+], Military Connected [2022+], Foster Care [2022+]) are all covered
  by ``DEMOGRAPHIC_ALIASES``. ``active_duty`` and ``military_connected`` are
  distinct, NON-ADDITIVE keys (active_duty is a subset of
  military_connected) and never co-occur in the same year, so no same-year
  collision exists and ``aggregate_demographic_collisions`` is not needed —
  the collision guard fails loudly if a future alias change introduces one.

- **Subject (not test_component).** ``TEST_CMPNT_TYP_NM`` is academic
  content, so the gold categorical is ``subject`` per §16, snake_cased via
  the topic-local SUBJECT_MAP and passed through the shared
  ``apply_subject_normalization`` backstop. The 11-course cross-era value
  set reflects real curriculum changes (5 courses retired after 2021;
  Algebra I / Geometry first administered 2016; Algebra: Concepts and
  Connections added 2024) — verified per file and enforced as a contract
  quality check. Historical course identities are preserved verbatim.

- **Suppression (verified against all 9 files — corrects stale structure-
  doc claims).** ``NUM_TESTED_CNT`` carries the ``TFS`` marker in EVERY
  year, including 2021-2023 (4,352 / 3,472 / 3,588 rows; the doc's
  row-level notes previously claimed it was never suppressed in those
  years). Mechanism differs by era: every 2015-2019 file (not just 2015,
  as the doc previously claimed) uses genuine empty CSV fields for the
  count/pct columns on exactly its fully-suppressed rows (7,335 / 8,436 /
  8,329 / 7,812 / 7,631), and the ``*_PCT`` columns never carry the TFS
  string in those years; 2021-2023 use TFS strings throughout, including
  the pct columns. Strict co-null behavior verified: in 2015-2023,
  ``num_tested`` NULL ⇔ all four pcts NULL; in 2024 GOSA publishes the
  rounded percentage distribution even when every count is TFS (76,074
  rows), so 2024 pcts are real signal, not division artifacts. In ALL
  years, a reported ``num_tested`` implies all four pcts reported.
  ``read_bronze_file`` nulls the TFS strings; ``strict=False`` casts null
  the empty fields.

- **Count reconciliation is an upper bound, not an equality.** Verified per
  file: where all five counts are reported, the four level counts sum
  exactly to ``num_tested`` in 2015-2022, but undershoot it in 2023 (1 row,
  -3) and 2024 (249 rows, up to -70) — test-takers without a valid
  achievement-level score are included in ``num_tested`` but in no band.
  No row in any year has the sum (or any single band count) EXCEED
  ``num_tested``, so the contract enforces the ≤ form only.

- **The four-band pct partition undershoots 1.0 and is NOT enforced as a
  partition-sums-to-one check.** Verified: per-row pct sums fall in
  [0.999, 1.002] for 2015-2022 but drop as low as 0.91 in 2023 and 0.068 in
  2024 (same valid-score cause as the count undershoot; most extreme on
  2024 rows whose counts are fully suppressed). Only the rounding-bounded
  upper limit (sum ≤ ~1.002) is a real invariant and is what the contract
  enforces.

- **Irregular published zeros in three year/column pairs (bronze-faithful
  pass-through, measured directly).** 2017 ``DEVELOPING_CNT`` is the only
  year/column where suppression was ENTIRELY absent (zero TFS markers;
  3,001 literal ``0`` values; ~7%% null rate vs 43-75%% elsewhere). Two
  siblings carry published zeros alongside normal TFS suppression: 2015
  ``DISTINGUISHED_CNT`` (4,940 zeros; null rate ~52%% vs 75-79%% in
  2016-2019) and 2017 ``PROFICIENT_CNT`` (824 zeros). No other
  year/column pair has any literal zeros. All three conflate true zeros
  with should-have-been-suppressed small counts; documented in the
  contract column descriptions, not repaired.

- **No §4b mask.** No impossible values exist: counts are non-negative by
  construction, every bronze pct is within 0-100, and the capped
  cumulatives cannot exceed 1.0. Range checks derive from each column's
  ``unit``.

- **IDs and detail levels**: district_code zfill(3) (7-digit state-charter
  codes pass through; never truncated), school_code zfill(4) (fixes the
  2015-2019 3/4-char mix). Detail level derives from the ``ALL`` sentinels
  (state: both ALL; district: school ALL; school: neither — no
  district==ALL/school!=ALL rows exist). Sentinels become NULL geography
  per EDUCATION_DOMAIN_CONFIG, shared with the validator.

- **Dedup tie-break**: each bronze file is a distinct year and the eras do
  not overlap, and no within-file duplicate natural keys exist (verified
  per file), so ``deduplicate_by_detail_level`` is a pure safety net;
  ``sort_col="num_tested"`` documents the preference for a reported,
  larger-count row over a suppressed placeholder should a republish ever
  introduce one. ``assert_no_natural_key_collisions`` runs first so a
  divergent duplicate fails loudly instead of being silently resolved.

- **Year**: derived from the filename (= ending calendar year of the school
  year) and cross-checked against the file's single ``LONG_SCHOOL_YEAR``
  value (``YYYY-YY``); a mismatch is a hard stop. 2020 is genuinely absent
  (COVID-19) — no interpolation.

Natural PK: (year, district_code, school_code, demographic, grade_level,
subject), with NULL geography per detail level.
"""

import logging
from pathlib import Path

import polars as pl

from src.utils.demographics import DEMOGRAPHIC_ALIASES, normalize_demographic_column
from src.utils.grades import GRADE_LEVEL_MAP, normalize_grade_column
from src.utils.metadata import write_data_dictionary
from src.utils.readers import (
    extract_year_from_filename,
    list_bronze_files,
    parse_school_year,
    read_bronze_file,
)
from src.utils.subjects import apply_subject_normalization
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

TOPIC = "georgia_milestones_end_of_course_by_grade_level"
BRONZE_DIR = Path(
    "data/bronze/education/gosa/georgia_milestones_end_of_course_by_grade_level"
)
GOLD_DIR = Path("data/gold/education/georgia_milestones_end_of_course_by_grade_level")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Bronze sentinel marking aggregate rows in SCHOOL_DISTRCT_CD / INSTN_NUMBER.
# Both eras use the same uppercase literal.
BRONZE_ALL_SENTINEL = "ALL"

# Bronze TEST_CMPNT_TYP_NM -> gold `subject` (snake_case, §16 canonical).
# Every distinct bronze value across all 9 files is mapped explicitly so the
# manifest's unmapped guard stays at 0. The set reflects real curriculum
# evolution (courses added/retired over time), not label drift — each
# historical course keeps its own identity. Matches the sister
# `_eoc_assessment` topic's canonical set for cross-topic consistency.
SUBJECT_MAP: dict[str, str] = {
    "9th Grade Literature and Composition": "9th_grade_literature_and_composition",
    "Algebra I": "algebra_i",
    "Algebra: Concepts and Connections": "algebra_concepts_and_connections",
    "American Literature and Composition": "american_literature_and_composition",
    "Analytic Geometry": "analytic_geometry",
    "Biology": "biology",
    "Coordinate Algebra": "coordinate_algebra",
    "Economics/Business/Free Enterprise": "economics_business_free_enterprise",
    "Geometry": "geometry",
    "Physical Science": "physical_science",
    "US History": "us_history",
}

# The five courses retired after the 2021 administration (real curriculum
# change, verified per file) — used by a contract quality check.
RETIRED_AFTER_2021: list[str] = [
    "9th_grade_literature_and_composition",
    "analytic_geometry",
    "economics_business_free_enterprise",
    "geometry",
    "physical_science",
]

# Era-detection signatures, most-specific first. Both eras share ACDMC_LVL
# (unlike the non-by-grade sister), so Era 2's distinguishing column is the
# prepended `#ASSMT_CD` constant.
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_2_2024": [
        "#ASSMT_CD",
        "LONG_SCHOOL_YEAR",
        "SCHOOL_DISTRCT_CD",
        "INSTN_NUMBER",
        "ACDMC_LVL",
        "SUBGROUP_NAME",
        "TEST_CMPNT_TYP_NM",
        "BEGIN_CNT",
        "DISTINGUISHED_CNT",
    ],
    "era_1_2015_2023": [
        "LONG_SCHOOL_YEAR",
        "SCHOOL_DISTRCT_CD",
        "INSTN_NUMBER",
        "ACDMC_LVL",
        "SUBGROUP_NAME",
        "TEST_CMPNT_TYP_NM",
        "NUM_TESTED_CNT",
        "BEGIN_CNT",
        "DEVELOPING_CNT",
        "PROFICIENT_CNT",
        "DISTINGUISHED_CNT",
        "BEGIN_PCT",
        "DEVELOPING_PCT",
        "PROFICIENT_PCT",
        "DISTINGUISHED_PCT",
    ],
}

# Gold fact column order per data-cleaning-standards §1: year, geography
# keys, demographic, topic categoricals, metrics. `detail_level` is carried
# through dedup / geography nulling / export splitting, then dropped by
# export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "grade_level",
    "subject",
    "num_tested",
    "num_beginning_learner",
    "num_developing_learner",
    "num_proficient_learner",
    "num_distinguished_learner",
    "pct_beginning_learner",
    "pct_developing_learner",
    "pct_proficient_learner",
    "pct_distinguished_learner",
    "pct_developing_learner_or_above",
    "pct_proficient_learner_or_above",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "demographic": pl.Utf8,
    "grade_level": pl.Utf8,
    "subject": pl.Utf8,
    "num_tested": pl.Int64,
    "num_beginning_learner": pl.Int64,
    "num_developing_learner": pl.Int64,
    "num_proficient_learner": pl.Int64,
    "num_distinguished_learner": pl.Int64,
    "pct_beginning_learner": pl.Float64,
    "pct_developing_learner": pl.Float64,
    "pct_proficient_learner": pl.Float64,
    "pct_distinguished_learner": pl.Float64,
    "pct_developing_learner_or_above": pl.Float64,
    "pct_proficient_learner_or_above": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = [
    "num_tested",
    "num_beginning_learner",
    "num_developing_learner",
    "num_proficient_learner",
    "num_distinguished_learner",
    "pct_beginning_learner",
    "pct_developing_learner",
    "pct_proficient_learner",
    "pct_distinguished_learner",
    "pct_developing_learner_or_above",
    "pct_proficient_learner_or_above",
]

# Natural key for the collision guard. detail_level is included so the
# pre-nulled geography patterns (state rows already NULL/NULL) cannot alias
# across levels.
NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "detail_level",
    "demographic",
    "grade_level",
    "subject",
]

# Bronze achievement-level column pairs (identical across both eras).
COUNT_MAP: dict[str, str] = {
    "BEGIN_CNT": "num_beginning_learner",
    "DEVELOPING_CNT": "num_developing_learner",
    "PROFICIENT_CNT": "num_proficient_learner",
    "DISTINGUISHED_CNT": "num_distinguished_learner",
}
PCT_MAP: dict[str, str] = {
    "BEGIN_PCT": "pct_beginning_learner",
    "DEVELOPING_PCT": "pct_developing_learner",
    "PROFICIENT_PCT": "pct_proficient_learner",
    "DISTINGUISHED_PCT": "pct_distinguished_learner",
}

# Tolerance for clamping publisher-rounding overshoot in the derived
# `_or_above` cumulatives. Bronze ships per-level pcts pre-rounded to one
# decimal on the 0-100 scale; summing up to three of them can land one
# rounding unit above 1.0 (max observed bronze sum: 100.2). A probability
# cannot exceed 1.0, so small overages snap back to 1.0.
_OR_ABOVE_ROUNDING_TOLERANCE = 0.005


def _cap_or_above(expr: pl.Expr) -> pl.Expr:
    """Cap small publisher-rounding overshoot above 1.0 in cumulative pcts.

    Values in (1.0, 1.0 + tolerance] snap to 1.0; values <= 1.0 pass through;
    values further above 1.0 also pass through so the bounded-proportion
    validator can flag genuine anomalies. NULL in -> NULL out (polars
    arithmetic NULL-propagation upstream).
    """
    return (
        pl.when((expr > 1.0) & (expr <= 1.0 + _OR_ABOVE_ROUNDING_TOLERANCE))
        .then(1.0)
        .otherwise(expr)
    )


# =============================================================================
# Helpers
# =============================================================================


def _record_effective_slice(
    manifest: TransformManifest,
    column: str,
    full_map: dict[str, str],
    bronze_series: pl.Series,
    gold_series: pl.Series,
) -> None:
    """Record a shared-map categorical using only the aliases actually hit.

    Shared maps (DEMOGRAPHIC_ALIASES, GRADE_LEVEL_MAP) have far more entries
    than any one topic uses; recording the effective slice keeps the
    manifest's map_used reviewable while preserving the unmapped guard
    (observed values missing from the full map still surface as unmapped).
    """
    observed_upper = {
        str(v).strip().upper() for v in bronze_series.drop_nulls().unique().to_list()
    }
    effective_map = {k: v for k, v in full_map.items() if k in observed_upper}
    manifest.record_categorical(
        column=column,
        map_dict=effective_map,
        bronze_series=bronze_series,
        gold_series=gold_series,
    )


def _require_columns(df: pl.DataFrame, required: list[str], label: str) -> None:
    """Raise if any expected bronze column is absent (rename-coverage guard).

    An unmatched source column silently becomes NULL in gold — the most
    common data-loss bug — so a missing expected column is a hard stop.
    """
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"{label}: expected bronze column(s) missing: {missing}. "
            f"Present: {df.columns}"
        )


def _assert_school_year_matches(df: pl.DataFrame, year: int, label: str) -> None:
    """Cross-check the file's single LONG_SCHOOL_YEAR against the filename year.

    The filename year equals the ending calendar year of the school year for
    every file in this topic; disagreement means bronze drift and is a hard
    stop rather than a silently mislabeled year of gold data.
    """
    school_years = df["LONG_SCHOOL_YEAR"].drop_nulls().unique().to_list()
    if len(school_years) != 1:
        raise ValueError(
            f"{label}: expected exactly one LONG_SCHOOL_YEAR, got {school_years}"
        )
    ending = parse_school_year(school_years[0])
    if ending != year:
        raise ValueError(
            f"{label}: filename year {year} != LONG_SCHOOL_YEAR "
            f"{school_years[0]!r} ending year {ending} — re-check bronze."
        )


# =============================================================================
# Shared era transform (Era 1 2015-2023 / Era 2 2024)
# =============================================================================


def _transform_era(
    df: pl.DataFrame,
    year: int,
    era: str,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Transform one bronze file (either era) into gold-shaped rows.

    Era 2 differs from Era 1 only by the prepended `#ASSMT_CD` constant,
    which the caller drops before this function runs — everything else
    (column names, suppression markers, row grain) is identical.
    """
    required = (
        [
            "LONG_SCHOOL_YEAR",
            "SCHOOL_DISTRCT_CD",
            "INSTN_NUMBER",
            "ACDMC_LVL",
            "SUBGROUP_NAME",
            "TEST_CMPNT_TYP_NM",
            "NUM_TESTED_CNT",
        ]
        + list(COUNT_MAP)
        + list(PCT_MAP)
    )
    _require_columns(df, required, f"{era} year {year}")
    _assert_school_year_matches(df, year, f"{era} year {year}")

    # Detail level from the ALL sentinels: (ALL, ALL) -> state;
    # (code, ALL) -> district; (code, code) -> school. No
    # (ALL, non-ALL) rows exist in any file (verified in the bronze report).
    df = df.with_columns(
        pl.when(
            (pl.col("SCHOOL_DISTRCT_CD") == BRONZE_ALL_SENTINEL)
            & (pl.col("INSTN_NUMBER") == BRONZE_ALL_SENTINEL)
        )
        .then(pl.lit("state"))
        .when(pl.col("INSTN_NUMBER") == BRONZE_ALL_SENTINEL)
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .cast(pl.Utf8)
        .alias("detail_level"),
    )

    # Geography keys: the ALL sentinel becomes NULL before zero-padding so
    # the literal string is never padded; zfill(3) passes 7-digit
    # state-charter codes through unchanged (never truncate), zfill(4)
    # fixes the 2015-2019 3/4-char school-code mix.
    df = df.with_columns(
        pl.when(pl.col("SCHOOL_DISTRCT_CD") == BRONZE_ALL_SENTINEL)
        .then(None)
        .otherwise(pl.col("SCHOOL_DISTRCT_CD").cast(pl.Utf8).str.zfill(3))
        .alias("district_code"),
        pl.when(pl.col("INSTN_NUMBER") == BRONZE_ALL_SENTINEL)
        .then(None)
        .otherwise(pl.col("INSTN_NUMBER").cast(pl.Utf8).str.zfill(4))
        .alias("school_code"),
        pl.lit(year).cast(pl.Int32).alias("year"),
    )

    # Grade level: shared normalizer resolves the cross-era padding split
    # (`7` in 2015-2019 vs `07` in 2021-2024) to canonical 2-char codes.
    bronze_grade = df["ACDMC_LVL"]
    df = df.with_columns(normalize_grade_column("ACDMC_LVL").alias("grade_level"))
    _record_effective_slice(
        manifest, "grade_level", GRADE_LEVEL_MAP, bronze_grade, df["grade_level"]
    )

    # Subject: topic-local snake_case map (unmapped -> sentinel so the
    # manifest guard raises), then the shared spelling-variant backstop —
    # a no-op on current data since SUBJECT_MAP already emits §16 canonical
    # values, but it catches future GOSA label drift.
    bronze_subject = df["TEST_CMPNT_TYP_NM"]
    df = df.with_columns(
        pl.col("TEST_CMPNT_TYP_NM")
        .replace_strict(SUBJECT_MAP, default="99999999")
        .alias("subject")
    )
    df = df.with_columns(apply_subject_normalization("subject").alias("subject"))
    manifest.record_categorical(
        column="subject",
        map_dict=SUBJECT_MAP,
        bronze_series=bronze_subject,
        gold_series=df["subject"],
    )

    # Demographic: the single canonical path. Split race convention applies
    # (bronze has separate Asian and Pacific Islander rows in every year),
    # so no §5b combined-bucket remap is needed.
    bronze_demo = df["SUBGROUP_NAME"]
    df = df.with_columns(
        normalize_demographic_column("SUBGROUP_NAME").alias("demographic")
    )
    _record_effective_slice(
        manifest, "demographic", DEMOGRAPHIC_ALIASES, bronze_demo, df["demographic"]
    )

    # Metrics: counts to Int64, pcts to Float64 / 100 (bronze 0-100 scale).
    # strict=False nulls residual non-numeric values (2015's genuine empty
    # CSV fields arrive as nulls already; TFS was nulled by the reader).
    cast_exprs: list[pl.Expr] = [
        pl.col("NUM_TESTED_CNT").cast(pl.Int64, strict=False).alias("num_tested"),
    ]
    cast_exprs += [
        pl.col(bronze_name).cast(pl.Int64, strict=False).alias(gold_name)
        for bronze_name, gold_name in COUNT_MAP.items()
    ]
    cast_exprs += [
        (pl.col(bronze_name).cast(pl.Float64, strict=False) / 100.0).alias(gold_name)
        for bronze_name, gold_name in PCT_MAP.items()
    ]
    df = df.with_columns(cast_exprs)

    # Cumulative `_or_above` columns derived from the per-level pcts via `+`
    # so NULL propagates (suppression-as-NULL); rounding overshoot above 1.0
    # is capped within tolerance (see _cap_or_above).
    df = df.with_columns(
        _cap_or_above(
            pl.col("pct_developing_learner")
            + pl.col("pct_proficient_learner")
            + pl.col("pct_distinguished_learner")
        ).alias("pct_developing_learner_or_above"),
        _cap_or_above(
            pl.col("pct_proficient_learner") + pl.col("pct_distinguished_learner")
        ).alias("pct_proficient_learner_or_above"),
    )

    return df.select(STANDARD_COLUMNS)


# =============================================================================
# File dispatcher
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read one bronze file, detect its era, and route to the era handler."""
    # infer_schema_length=0 forces all-Utf8 so zero-padded codes keep their
    # leading zeros and every metric is cast explicitly downstream (§4.3b).
    df, loss = read_bronze_file(path, infer_schema_length=0, return_loss=True)

    year = extract_year_from_filename(path.name)
    if year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")
    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(
            f"{path.name}: no era signature matched columns {df.columns[:15]}..."
        )

    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)

    if df.height == 0:
        logger.warning(f"Year {year}: bronze file is empty, skipping: {path.name}")
        return None

    logger.info(f"Processing {path.name} (year={year}, era={era}, rows={df.height:,})")

    if era == "era_2_2024":
        # The 2024-only `#ASSMT_CD` column is constant "EOC_by_GRADE" (note:
        # different from the sister topic's "EOC") — verify, then drop.
        assmt_vals = df["#ASSMT_CD"].drop_nulls().unique().to_list()
        if assmt_vals != ["EOC_by_GRADE"]:
            raise ValueError(f"{era} year {year}: unexpected #ASSMT_CD {assmt_vals}")
        df = df.drop("#ASSMT_CD")

    return _transform_era(df, year, era, manifest)


# =============================================================================
# Pipeline orchestration
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for EOC assessment by grade."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform each bronze file (read-loss accounted per file).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR):
        result = transform_file(path, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize columns/dtypes across eras and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs, how="vertical")
    logger.info(f"Combined all years: {combined.height:,} rows")

    # 3. Collision guard BEFORE dedup: a duplicate key with divergent metrics
    # is an alias/aggregation bug and must raise, never be silently deduped.
    # aggregate_demographic_collisions is not needed: every bronze label maps
    # to a distinct canonical key, and active_duty (2021) / military_connected
    # (2022+) never co-occur in a year — the guard is the protection should a
    # future alias change introduce a same-key collision.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: each file is a distinct year, eras don't overlap, and no
    # within-file duplicate keys exist (verified) — dedup is a safety net.
    # sort_col="num_tested" prefers a reported, larger-count row over a
    # suppressed placeholder should a republish ever introduce a duplicate.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=[
            "year",
            "district_code",
            "school_code",
            "demographic",
            "grade_level",
            "subject",
        ],
        district_keys=[
            "year",
            "district_code",
            "demographic",
            "grade_level",
            "subject",
        ],
        state_keys=["year", "demographic", "grade_level", "subject"],
        sort_col="num_tested",
    )

    # 4. Geography nulling — shared rule source keeps transform and
    # validator in lockstep. No §4b mask: no impossible values exist in
    # this source (see module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. Expected NULL-rate spikes (warnings, documented):
    # num_tested ~55% NULL in 2024 (GOSA extended TFS to NUM_TESTED_CNT);
    # num_developing_learner ~7% NULL in 2017 vs 43-75% elsewhere (the 2017
    # missing-suppression anomaly); per-level counts increasingly suppressed
    # in later years.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning(f"NULL-rate spikes: {spike_result.details}")
    validate_output(
        combined,
        required_non_null=[
            "year",
            "detail_level",
            "demographic",
            "grade_level",
            "subject",
        ],
    )

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
        f"Done. Bronze rows: {summary['total_bronze']:,}; "
        f"Gold rows: {summary['total_gold']:,}; "
        f"Years: {summary['years_processed']}"
    )

    # 7. ALWAYS LAST: validate the gold just written against the contract
    # just emitted. Raises GoldValidationError -> non-zero exit.
    run_topic_validation(GOLD_DIR)


def _emit_contract_and_readme(year_range: tuple[int, int]) -> None:
    """Emit the ODCS contract and gold README via ``write_data_dictionary``.

    The column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level`` — the contract's properties (and the validator's
    schema check) follow it.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Georgia Milestones End-of-Course (EOC) assessment results "
            "disaggregated by the grade level of the test-taker, published "
            "by the Governor's Office of Student Achievement (GOSA). Each "
            "row is one (entity x grade x demographic subgroup x course) "
            "combination reporting the number of students tested plus the "
            "count and percentage at each of four achievement levels "
            "(Beginning, Developing, Proficient, Distinguished Learner) and "
            "two derived cumulative shares. Covers school years 2014-15 "
            "through 2023-24 (2019-20 absent — EOC testing suspended due to "
            "COVID-19) at state, district, and school detail levels."
        ),
        title="Georgia Milestones End-of-Course (EOC) Results by Grade",
        summary=(
            "Georgia Milestones high school course achievement results broken "
            "out by test-taker grade, course, and subgroup, 2015-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Ending calendar year of the school year (e.g., 2024 = "
                    "2023-24). Derived from the filename and cross-checked "
                    "against the source's LONG_SCHOOL_YEAR. 2020 is absent "
                    "(EOC testing suspended during COVID-19 closures)."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "GOSA district code (FK to districts dimension): 3-digit "
                    "zero-padded county/city codes or 7-digit state-charter "
                    "codes. NULL on state-level rows."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0386",
                "description": (
                    "GOSA school code, zero-padded to 4 characters "
                    "(composite FK to schools dimension with district_code; "
                    "not globally unique on its own). NULL on district- and "
                    "state-level rows."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "all",
                "description": (
                    "Canonical demographic subgroup code (FK to the global "
                    "demographics dimension), normalized from bronze "
                    "SUBGROUP_NAME. This topic uses the SPLIT race "
                    "convention — separate asian and pacific_islander rows "
                    "in every year (no combined asian_pacific_islander "
                    "bucket). Coverage grew over time: the stable 18-key "
                    "core (2015+), plus active_duty and homeless from 2021, "
                    "with active_duty renamed at the source to "
                    "military_connected from 2022 alongside new foster_care "
                    "rows. NON-ADDITIVE MILITARY KEYS: active_duty "
                    "(dependents of currently-serving active-duty members) "
                    "is a subset of military_connected (any DoD-connected "
                    "family) — never sum the two."
                ),
                "short_description": (
                    "Demographic subgroup the row reports; 'all' is the "
                    "overall figure (subgroups are non-additive)."
                ),
            },
            {
                "name": "grade_level",
                "type": "string",
                "nullable": False,
                "example": "09",
                "validValues": ["07", "08", "09", "10", "11", "12"],
                "description": (
                    "Grade level of the test-takers this row represents, as "
                    "a 2-char zero-padded string. Bronze ACDMC_LVL is "
                    "unpadded (7..12) in 2015-2019 and zero-padded (07..12) "
                    "in 2021-2024; gold normalizes both to 07-12. Grade 7 "
                    "is rare (the small set of 7th graders taking EOC "
                    "courses early); grade 12 includes retake/make-up "
                    "administrations."
                ),
                "short_description": (
                    "Grade level of the test-takers, 07-12; grade 7 is rare "
                    "and grade 12 includes retakes."
                ),
            },
            {
                "name": "subject",
                "type": "string",
                "nullable": False,
                "example": "biology",
                "validValues": sorted(set(SUBJECT_MAP.values())),
                "description": (
                    "EOC course assessed, snake_case canonical. The value "
                    "set tracks real curriculum changes: "
                    "9th_grade_literature_and_composition, "
                    "analytic_geometry, economics_business_free_enterprise, "
                    "geometry, and physical_science were retired after "
                    "2021; algebra_i and geometry first administered 2016; "
                    "algebra_concepts_and_connections added 2024 "
                    "(replacing coordinate_algebra over time). Historical "
                    "course identities are preserved — algebra_i, "
                    "coordinate_algebra, and "
                    "algebra_concepts_and_connections are distinct courses, "
                    "not aliases."
                ),
                "short_description": (
                    "EOC course assessed (e.g. biology, algebra_i, "
                    "us_history); the value set tracks curriculum changes "
                    "over time."
                ),
            },
            {
                "name": "num_tested",
                "type": "int64",
                "unit": "count",
                "metric_component": "denominator",
                "example": 33,
                "null_meaning": (
                    "Suppressed by GOSA (TFS, 'Too Few Students'). Affects "
                    "every year: ~7-8% of rows in 2015-2019, ~5-8% in "
                    "2021-2023, and ~55% in 2024 when GOSA broadened "
                    "suppression of this column."
                ),
                "description": (
                    "Count of students in this grade tested on this EOC "
                    "course in this (entity x demographic) cell. Includes "
                    "test-takers without a valid achievement-level score, "
                    "so it can exceed the sum of the four num_*_learner "
                    "counts (observed in 2023-2024; the sum never exceeds "
                    "num_tested). Suppressed (NULL) in every year, most "
                    "heavily in 2024 (~55%% of rows) where the pct_* "
                    "columns still carry the rounded distribution."
                ),
            },
            {
                "name": "num_beginning_learner",
                "type": "int64",
                "unit": "count",
                "example": 30,
                "null_meaning": "Suppressed by GOSA (TFS, 'Too Few Students').",
                "description": (
                    "Count of students scoring Beginning Learner (lowest of "
                    "the four achievement levels). Bronze BEGIN_CNT; NULL "
                    "when suppressed (TFS string, or — on the fully-"
                    "suppressed rows of every 2015-2019 file — genuine "
                    "empty CSV fields)."
                ),
            },
            {
                "name": "num_developing_learner",
                "type": "int64",
                "unit": "count",
                "example": 15,
                "null_meaning": (
                    "Suppressed by GOSA (TFS) — except 2017, where the "
                    "source failed to suppress this column."
                ),
                "description": (
                    "Count of students scoring Developing Learner. Bronze "
                    "DEVELOPING_CNT. 2017 ANOMALY: the 2017 source file is "
                    "the only year/column where suppression was ENTIRELY "
                    "absent (zero TFS markers) — it carries 3,001 literal "
                    "0 values and a ~7%% null rate vs 43-75%% in every "
                    "other year, conflating true zeros with small counts "
                    "the publisher should have suppressed. Two sibling "
                    "columns show the same published-zero irregularity in "
                    "single years (num_distinguished_learner 2015: 4,940 "
                    "zeros; num_proficient_learner 2017: 824 zeros — see "
                    "those columns); no other year/column pair has any "
                    "literal zeros. Bronze-faithful pass-through; do not "
                    "compare 2017 values for this column directly against "
                    "other years."
                ),
            },
            {
                "name": "num_proficient_learner",
                "type": "int64",
                "unit": "count",
                "example": 12,
                "null_meaning": "Suppressed by GOSA (TFS, 'Too Few Students').",
                "description": (
                    "Count of students scoring Proficient Learner. Bronze "
                    "PROFICIENT_CNT; NULL when suppressed. 2017 CAVEAT: "
                    "the 2017 source published 824 literal 0 values for "
                    "this column (TFS suppression was still applied to "
                    "47,937 other cells) — no other year has any. The "
                    "zeros conflate true zeros with small counts that "
                    "would normally be suppressed; bronze-faithful "
                    "pass-through."
                ),
            },
            {
                "name": "num_distinguished_learner",
                "type": "int64",
                "unit": "count",
                "example": 5,
                "null_meaning": "Suppressed by GOSA (TFS, 'Too Few Students').",
                "description": (
                    "Count of students scoring Distinguished Learner "
                    "(highest level). The most heavily suppressed metric "
                    "(~80%% NULL in 2023, ~88%% in 2024) — few cells have "
                    "enough distinguished scorers to clear the threshold. "
                    "2015 CAVEAT: the 2015 source published 4,940 literal "
                    "0 values for this column (TFS suppression was still "
                    "applied to 48,267 other cells), depressing the 2015 "
                    "null rate to ~52%% vs 75-79%% in 2016-2019 (2015 min "
                    "is 0 vs 10 elsewhere); no other year has any. The "
                    "zeros conflate true zeros with small counts that "
                    "would normally be suppressed — do not compare 2015 "
                    "values for this column directly against later years; "
                    "bronze-faithful pass-through."
                ),
            },
            {
                "name": "pct_beginning_learner",
                "type": "float64",
                "unit": "proportion",
                "example": 0.909,
                "null_meaning": (
                    "Suppressed by GOSA — in 2015-2023 exactly when "
                    "num_tested is suppressed; never NULL in 2024."
                ),
                "description": (
                    "Share of tested students scoring Beginning Learner, "
                    "0-1 scale (bronze 0-100 divided by 100). In 2015-2023 "
                    "NULL exactly when num_tested is NULL (fully suppressed "
                    "cell); in 2024 always reported — GOSA publishes the "
                    "rounded distribution even when every count is "
                    "suppressed. The four pct_*_learner shares are computed "
                    "against num_tested and can sum to less than 1.0 when "
                    "some test-takers lack a valid achievement-level score "
                    "(pronounced in 2023-2024); they never sum above ~1.002 "
                    "(rounding)."
                ),
            },
            {
                "name": "pct_developing_learner",
                "type": "float64",
                "unit": "proportion",
                "example": 0.091,
                "null_meaning": (
                    "Suppressed by GOSA — in 2015-2023 exactly when "
                    "num_tested is suppressed; never NULL in 2024."
                ),
                "description": (
                    "Share of tested students scoring Developing Learner, "
                    "0-1 scale. Same suppression and partition behavior as "
                    "pct_beginning_learner."
                ),
            },
            {
                "name": "pct_proficient_learner",
                "type": "float64",
                "unit": "proportion",
                "example": 0.25,
                "null_meaning": (
                    "Suppressed by GOSA — in 2015-2023 exactly when "
                    "num_tested is suppressed; never NULL in 2024."
                ),
                "description": (
                    "Share of tested students scoring Proficient Learner, "
                    "0-1 scale. Same suppression and partition behavior as "
                    "pct_beginning_learner."
                ),
            },
            {
                "name": "pct_distinguished_learner",
                "type": "float64",
                "unit": "proportion",
                "example": 0.104,
                "null_meaning": (
                    "Suppressed by GOSA — in 2015-2023 exactly when "
                    "num_tested is suppressed; never NULL in 2024."
                ),
                "description": (
                    "Share of tested students scoring Distinguished "
                    "Learner, 0-1 scale. Same suppression and partition "
                    "behavior as pct_beginning_learner."
                ),
            },
            {
                "name": "pct_developing_learner_or_above",
                "type": "float64",
                "unit": "proportion",
                "example": 0.605,
                "null_meaning": (
                    "NULL whenever any of the three summand shares is NULL "
                    "(suppression propagates)."
                ),
                "description": (
                    "Cumulative share at Developing Learner or higher, "
                    "derived at transform time as pct_developing_learner + "
                    "pct_proficient_learner + pct_distinguished_learner "
                    "(0-1 scale). Sums of publisher-rounded shares landing "
                    "within 0.005 above 1.0 are capped to 1.0. NULL "
                    "whenever any summand is NULL."
                ),
            },
            {
                "name": "pct_proficient_learner_or_above",
                "type": "float64",
                "unit": "proportion",
                "key_metric": True,
                "example": 0.354,
                "short_description": (
                    "Share of tested students scoring Proficient Learner or "
                    "higher, on a 0-1 scale (the headline EOC proficiency "
                    "rate)."
                ),
                "null_meaning": (
                    "NULL whenever either summand share is NULL "
                    "(suppression propagates)."
                ),
                "description": (
                    "Cumulative share at Proficient Learner or higher "
                    "(the headline 'proficiency rate'), derived at "
                    "transform time as pct_proficient_learner + "
                    "pct_distinguished_learner (0-1 scale). Sums of "
                    "publisher-rounded shares landing within 0.005 above "
                    "1.0 are capped to 1.0. NULL whenever either summand "
                    "is NULL."
                ),
            },
        ],
        source="Governor's Office of Student Achievement (GOSA)",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        notes=[
            (
                "Two bronze eras share one gold schema: Era 1 (2015-2023) "
                "is a 17-column tidy format; Era 2 (2024) adds one "
                "constant-valued column (#ASSMT_CD = 'EOC_by_GRADE') that "
                "is dropped. Achievement-level columns are identical "
                "across eras."
            ),
            (
                "Missing year: 2020 (school year 2019-20) — EOC testing "
                "was suspended due to COVID-19 school closures. Gold "
                "simply has no rows for 2020. The 2021 file is also much "
                "smaller (53,855 bronze rows vs ~119,000 pre-COVID) due "
                "to reduced administration."
            ),
            (
                "Suppression: NUM_TESTED_CNT carries the TFS marker in "
                "EVERY year (2015: 7,335; 2016-2019: ~7,600-8,400; "
                "2021-2023: ~3,500-4,400; 2024: 76,074 = ~55% of rows). "
                "Mechanism differs by era: every 2015-2019 file uses "
                "genuine empty CSV fields on the count/pct columns of "
                "its fully-suppressed rows (the pct columns never carry "
                "the TFS string in those years); 2021-2023 use TFS "
                "strings throughout, including the pct columns. Either "
                "way, in 2015-2023 the four pct columns are NULL exactly "
                "when num_tested is NULL; in 2024 the pct columns are "
                "never suppressed — GOSA publishes the rounded "
                "distribution even when every count is TFS."
            ),
            (
                "Count reconciliation: where all five counts are "
                "reported, the four level counts sum exactly to "
                "num_tested in 2015-2022 but undershoot it on 1 row in "
                "2023 and 249 rows in 2024 (by up to 70) — test-takers "
                "without a valid achievement-level score count toward "
                "num_tested but no band. The sum never exceeds "
                "num_tested in any year (enforced)."
            ),
            (
                "The four pct_*_learner shares can sum below 1.0 (as low "
                "as ~0.91 in 2023 and ~0.07 in 2024) for the same "
                "valid-score reason; only the rounding-bounded upper "
                "limit (~1.002) is enforced as a quality check."
            ),
            (
                "Irregular published zeros in three year/column pairs "
                "(bronze-faithful pass-through, all measured directly): "
                "2017 DEVELOPING_CNT carries 3,001 literal zeros with "
                "suppression entirely absent (zero TFS; ~7% null rate vs "
                "43-75% elsewhere); 2015 DISTINGUISHED_CNT carries 4,940 "
                "literal zeros alongside normal TFS suppression "
                "(depressing its null rate to ~52% vs 75-79% in "
                "2016-2019); 2017 PROFICIENT_CNT carries 824 literal "
                "zeros alongside normal TFS suppression. No other "
                "year/column pair has any literal zeros. In all three "
                "cases the zeros conflate true zeros with small counts "
                "that would normally be suppressed — avoid direct "
                "cross-year comparison for those columns in those years."
            ),
            (
                "Military demographic keys are NON-ADDITIVE: active_duty "
                "(2021 bronze label 'Active Duty') is a subset of "
                "military_connected ('Military Connected', 2022+). They "
                "never co-occur in a year and must not be summed."
            ),
            (
                "Curriculum changes: 9th Grade Literature and "
                "Composition, Analytic Geometry, Economics/Business/Free "
                "Enterprise, Geometry, and Physical Science were retired "
                "after 2021; Algebra I and Geometry first appear in 2016; "
                "Algebra: Concepts and Connections appears in 2024 and is "
                "replacing Coordinate Algebra. Historical course values "
                "are preserved verbatim."
            ),
            (
                "ID formatting: district_code zfill(3) with 7-digit "
                "state-charter codes (e.g., 7830642) passed through "
                "unchanged; school_code zfill(4) fixes the 2015-2019 "
                "3/4-char INSTN_NUMBER mix."
            ),
            (
                "Files are partitioned by year and split by detail "
                "level: schools.parquet, districts.parquet, "
                "states.parquet."
            ),
        ],
        quality_checks=[
            {
                "name": "pcts_present_when_num_tested_reported",
                "description": (
                    "In every source year, a reported (non-NULL) num_tested "
                    "implies all four achievement-level shares are reported "
                    "(verified in bronze 2015-2024 with zero exceptions)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE num_tested IS NOT NULL "
                    "AND (pct_beginning_learner IS NULL "
                    "OR pct_developing_learner IS NULL "
                    "OR pct_proficient_learner IS NULL "
                    "OR pct_distinguished_learner IS NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "pct_levels_never_null_in_2024",
                "description": (
                    "The 2024 source publishes the rounded achievement-"
                    "level distribution on every row, even when all counts "
                    "are suppressed (verified: 0 NULLs across 138,747 "
                    "rows x 4 shares) — the fact that makes 2024's "
                    "suppressed-cell percentages usable signal. Guards "
                    "the served 'never NULL in 2024' claim against a "
                    "future re-publish or transform regression."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year = 2024 "
                    "AND (pct_beginning_learner IS NULL "
                    "OR pct_developing_learner IS NULL "
                    "OR pct_proficient_learner IS NULL "
                    "OR pct_distinguished_learner IS NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "pre_2024_full_suppression_co_null",
                "description": (
                    "Through 2023, a suppressed num_tested means the whole "
                    "cell is suppressed: all four achievement-level shares "
                    "must also be NULL. (2024 broke this pattern at the "
                    "source — shares are published even when counts are "
                    "suppressed — so the rule is scoped to year < 2024.)"
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year < 2024 "
                    "AND num_tested IS NULL "
                    "AND (pct_beginning_learner IS NOT NULL "
                    "OR pct_developing_learner IS NOT NULL "
                    "OR pct_proficient_learner IS NOT NULL "
                    "OR pct_distinguished_learner IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "level_counts_sum_le_num_tested",
                "description": (
                    "Where all four achievement-level counts and num_tested "
                    "are reported, the level counts sum to at most "
                    "num_tested (exact equality holds 2015-2022; 2023-2024 "
                    "undershoot because test-takers without a valid "
                    "achievement-level score are in num_tested but no band; "
                    "the sum never exceeds it in any source year)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE num_tested IS NOT NULL "
                    "AND num_beginning_learner IS NOT NULL "
                    "AND num_developing_learner IS NOT NULL "
                    "AND num_proficient_learner IS NOT NULL "
                    "AND num_distinguished_learner IS NOT NULL "
                    "AND (num_beginning_learner + num_developing_learner "
                    "+ num_proficient_learner + num_distinguished_learner) "
                    "> num_tested"
                ),
                "mustBe": 0,
            },
            {
                "name": "no_level_count_exceeds_num_tested",
                "description": (
                    "No single achievement-level count may exceed the "
                    "number of students tested in the same cell."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE num_tested IS NOT NULL "
                    "AND (num_beginning_learner > num_tested "
                    "OR num_developing_learner > num_tested "
                    "OR num_proficient_learner > num_tested "
                    "OR num_distinguished_learner > num_tested)"
                ),
                "mustBe": 0,
            },
            {
                "name": "pct_levels_sum_at_most_one_within_rounding",
                "description": (
                    "Where all four shares are reported, their sum may not "
                    "exceed 1.0 by more than publisher rounding (bronze "
                    "max observed: 100.2 on the 0-100 scale). The sum CAN "
                    "legitimately fall below 1.0 (test-takers without a "
                    "valid achievement-level score), so no lower bound is "
                    "asserted."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE pct_beginning_learner IS NOT NULL "
                    "AND pct_developing_learner IS NOT NULL "
                    "AND pct_proficient_learner IS NOT NULL "
                    "AND pct_distinguished_learner IS NOT NULL "
                    "AND (pct_beginning_learner + pct_developing_learner "
                    "+ pct_proficient_learner + pct_distinguished_learner) "
                    "> 1.0025"
                ),
                "mustBe": 0,
            },
            {
                "name": "developing_or_above_equals_component_sum",
                "description": (
                    "pct_developing_learner_or_above equals "
                    "pct_developing_learner + pct_proficient_learner + "
                    "pct_distinguished_learner within the 0.005 "
                    "rounding-cap tolerance, and is non-NULL whenever all "
                    "three summands are non-NULL."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE pct_developing_learner IS NOT NULL "
                    "AND pct_proficient_learner IS NOT NULL "
                    "AND pct_distinguished_learner IS NOT NULL "
                    "AND (pct_developing_learner_or_above IS NULL "
                    "OR ABS(pct_developing_learner_or_above "
                    "- (pct_developing_learner + pct_proficient_learner "
                    "+ pct_distinguished_learner)) > 0.0051)"
                ),
                "mustBe": 0,
            },
            {
                "name": "proficient_or_above_equals_component_sum",
                "description": (
                    "pct_proficient_learner_or_above equals "
                    "pct_proficient_learner + pct_distinguished_learner "
                    "within the 0.005 rounding-cap tolerance, and is "
                    "non-NULL whenever both summands are non-NULL."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE pct_proficient_learner IS NOT NULL "
                    "AND pct_distinguished_learner IS NOT NULL "
                    "AND (pct_proficient_learner_or_above IS NULL "
                    "OR ABS(pct_proficient_learner_or_above "
                    "- (pct_proficient_learner + pct_distinguished_learner)) "
                    "> 0.0051)"
                ),
                "mustBe": 0,
            },
            {
                "name": "subject_curriculum_year_ranges",
                "description": (
                    "Course availability matches the verified curriculum "
                    "timeline: the five courses retired after 2021 "
                    "(9th_grade_literature_and_composition, "
                    "analytic_geometry, economics_business_free_enterprise, "
                    "geometry, physical_science) never appear after 2021; "
                    "algebra_concepts_and_connections only from 2024; "
                    "algebra_i and geometry not before 2016."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(subject IN ('9th_grade_literature_and_composition', "
                    "'analytic_geometry', 'economics_business_free_enterprise', "
                    "'geometry', 'physical_science') AND year > 2021) "
                    "OR (subject = 'algebra_concepts_and_connections' "
                    "AND year < 2024) "
                    "OR (subject IN ('algebra_i', 'geometry') AND year < 2016)"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
