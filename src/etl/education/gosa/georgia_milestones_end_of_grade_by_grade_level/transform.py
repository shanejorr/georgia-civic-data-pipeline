"""Transform bronze georgia_milestones_end_of_grade_by_grade_level
files to gold.

Source: Governor's Office of Student Achievement (GOSA) — Georgia Milestones
End-of-Grade (EOG) assessment results disaggregated by individual grade level
(grades 3-8). Each bronze row is one (entity x grade x demographic subgroup x
subject) cell reporting the total Number Tested plus the count and percentage
of test-takers at each of four achievement levels (Beginning, Developing,
Proficient, Distinguished). Coverage: school years 2014-15 through 2023-24
(9 files; 2019-20 absent — EOG administration cancelled during the COVID-19
school closures).

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Two bronze eras, one shared transform.** Era 1 (2015-2023, 8 files) is a
  17-column tidy format; Era 2 (2024, 1 file) prepends one constant column
  ``#ASSMT_CD = "EOG_by_GRADE"`` (validated then dropped — no signal). All
  other columns are identical, so both eras route through one function.
- **Year = filename year, cross-checked.** Each file carries exactly one
  ``LONG_SCHOOL_YEAR`` (``YYYY-YY``); its ending calendar year must equal the
  filename year or the transform raises (source-drift guard).
- **Detail levels from the ``ALL`` sentinels.** ``SCHOOL_DISTRCT_CD == "ALL"``
  and ``INSTN_NUMBER == "ALL"`` -> state; only ``INSTN_NUMBER == "ALL"`` ->
  district; otherwise school. No (district=ALL, school!=ALL) rows exist in any
  file (verified). Sentinels become NULL geography keys in gold.
- **ID formatting.** ``district_code`` zfill(3) (7-digit state-charter /
  state-school codes pass through unchanged — never truncated);
  ``school_code`` zfill(4) (2015 and 2019 publish unpadded 3-char codes that
  the zfill repairs to the cross-year standard).
- **``grade_level`` is the grain-distinguishing categorical.** Bronze
  ``ACDMC_LVL`` is unpadded (``3``-``8``) in 2015/2019 and zero-padded
  (``03``-``08``) elsewhere; the shared ``normalize_grade_column`` resolves
  both to the canonical 2-char form ``03``-``08`` (data-cleaning-standards
  §16).
- **``subject``** (academic content, §16): the four core EOG subjects appear
  in every year; ``Physical Science`` was added in 2022 (an 8th-grade
  accelerated option — a real addition, never merged with ``science``).
  Topic-local snake_case map, then the shared ``apply_subject_normalization``
  (a no-op for these five values, applied for cross-topic consistency).
- **Demographics use the split race convention (§5a/§5b).** Bronze publishes
  separate ``Asian`` and ``Native Hawaiian or Other Pacific Islander`` rows
  in every file (verified across all 9 files), so bare "Asian" is genuinely
  Asian-only — no combined-bucket remap. Gold keeps ``asian`` and
  ``pacific_islander`` distinct and never synthesizes a rollup row.
  Subgroup evolution: 18 core labels (2015-2019); 2021 adds ``Active Duty``
  and ``Homeless``; 2022+ renames ``Active Duty`` -> ``Military Connected``
  and adds ``Foster Care`` (21 labels). ``active_duty`` (2021) and
  ``military_connected`` (2022+) are distinct canonical keys that never
  co-occur in a year, and no two bronze labels normalize to the same
  canonical key within a year — so no demographic-collision aggregation is
  needed; ``assert_no_natural_key_collisions`` hard-fails if that ever
  changes. NOTE: active_duty is a SUBSET of military_connected conceptually
  (non-additive across years; documented in the contract).
- **Suppression** mixes the ``TFS`` string ("Too Few Students") and genuine
  empty CSV fields, varying by year (2015/2019: both; 2016-2018: empties
  only; 2021-2023: TFS only, occasionally on the pct columns; 2024: TFS on
  counts including ~30%% of NUM_TESTED_CNT, never on pct columns). Reading
  with ``infer_schema_length=0`` (all-Utf8) plus ``read_bronze_file``'s
  suppression-marker nulling and non-strict numeric casts converts both
  mechanisms to NULL.
- **Percentage scaling.** All ``*_PCT`` columns are 0-100 in bronze; divided
  by 100 to the canonical 0-1 scale (§4). Verified per level:
  |pct/100 - count/num_tested| <= 0.0005 wherever all parts are non-null —
  the published percentages are exact shares of ``num_tested`` rounded to one
  decimal (authored as a quality check).
- **Cumulative ``_or_above`` columns are derived** (bronze does not publish
  them): developing+proficient+distinguished and proficient+distinguished.
  Summing publisher-rounded per-level pcts can overshoot 1.0 by one rounding
  unit (bronze max sum 100.1); a probability cannot exceed 1.0, so overshoot
  within ``_OR_ABOVE_ROUNDING_TOLERANCE`` (0.005) snaps to 1.0. Larger
  excursions pass through for the bounded-proportion validator to flag.
  Polars NULL-propagation keeps either cumulative NULL when any summand is
  NULL (suppression-as-NULL preserved).
- **Foster Care reporting quirks (2022-2024), preserved bronze-faithfully.**
  Every row in any year whose four per-level percentages do NOT sum to ~1 is
  a ``Foster Care`` row (verified: 206/282/4,738 deviating rows in
  2022/2023/2024, zero in 2015-2021, all Foster Care):
    * 28 fully-unsuppressed state-level Foster Care rows (7/11/10 in
      2022/2023/2024) carry level counts summing to LESS than num_tested —
      students tested but not assigned a performance level at publication
      time. The shortfall never exceeds num_tested in the other direction.
    * The remaining deviators are partially- or fully-suppressed Foster Care
      cells where the published percentages cover only the unsuppressed
      levels, including an all-four-zero placeholder pattern (157/173/4,106
      rows) on cells whose counts are entirely suppressed.
  Zeros and shortfalls are published GOSA values on a possible domain — not
  §4b-impossible — so they are preserved exactly and documented in the
  contract; the partition-sum quality check is scoped to exclude
  ``foster_care`` (where it provably holds with margin ~0.002).
- **Dedup tie-break.** Each bronze file covers a distinct year and no file
  contains duplicate natural keys (verified per file: zero duplicate
  (district, school, grade, subgroup, subject) tuples), so dedup is a safety
  net only; ``sort_col="num_tested"`` prefers the row with a reported,
  larger count over a suppressed placeholder if bronze ever republishes.
- **Not in gold:** name columns (dimension attributes), the Era 2 constant
  ``#ASSMT_CD``, and ``LONG_SCHOOL_YEAR`` (derivable from ``year``).
- **Natural PK:** (year, district_code, school_code, demographic,
  grade_level, subject) with geography NULLs per detail level — the
  ``grade_level`` key is what distinguishes this topic from the all-grades
  rollup sibling. Grade x subject availability is naturally sparse (Science /
  Social Studies restricted to grades 5/8 from 2017, Social Studies to grade
  8 from 2021, Physical Science grade 8 only) and the sparsity is preserved —
  no fabricated cells; rare out-of-pattern audit/retest rows are retained.
"""

import logging
from pathlib import Path

import polars as pl

from src.utils.demographics import (
    DEMOGRAPHIC_ALIASES,
    normalize_demographic_column,
)
from src.utils.grades import GRADE_LEVEL_MAP, normalize_grade_column
from src.utils.metadata import write_data_dictionary
from src.utils.readers import (
    extract_year_from_filename,
    list_bronze_files,
    parse_school_year,
    read_bronze_file,
)
from src.utils.subjects import (
    SUBJECT_NORMALIZATION_MAP,
    apply_subject_normalization,
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

TOPIC = "georgia_milestones_end_of_grade_by_grade_level"
BRONZE_DIR = Path(
    "data/bronze/education/gosa/georgia_milestones_end_of_grade_by_grade_level"
)
GOLD_DIR = Path("data/gold/education/georgia_milestones_end_of_grade_by_grade_level")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Bronze sentinel marking aggregate rows in SCHOOL_DISTRCT_CD / INSTN_NUMBER.
# Both eras use the same uppercase literal.
BRONZE_ALL_SENTINEL = "ALL"

# Era 2's constant assessment-code column (name literally starts with '#').
ASSMT_CD_COLUMN = "#ASSMT_CD"
ASSMT_CD_EXPECTED = "EOG_by_GRADE"

# Bronze TEST_CMPNT_TYP_NM -> gold `subject` (snake_case, §10/§16). The five
# values are the full cross-era set: four core EOG subjects in every file;
# Physical Science added in 2022. Every distinct bronze value is mapped
# explicitly so the manifest's unmapped guard stays meaningful.
SUBJECT_MAP: dict[str, str] = {
    "English Language Arts": "english_language_arts",
    "Mathematics": "mathematics",
    "Science": "science",
    "Social Studies": "social_studies",
    "Physical Science": "physical_science",
}

# Achievement-level bronze->gold column pairs, identical across both eras.
# Canonical naming per data-cleaning-standards §16 (proficiency bands).
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

# Era-detection signatures, most-specific first: Era 2 is an Era-1 superset
# distinguished only by the prepended constant `#ASSMT_CD`.
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_2_2024": [
        ASSMT_CD_COLUMN,
        "LONG_SCHOOL_YEAR",
        "SCHOOL_DISTRCT_CD",
        "INSTN_NUMBER",
        "ACDMC_LVL",
        "SUBGROUP_NAME",
        "TEST_CMPNT_TYP_NM",
        "BEGIN_CNT",
        "BEGIN_PCT",
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

# Gold fact column order (data-cleaning-standards §1): year, geography keys,
# demographic, topic categoricals, metrics. `detail_level` is carried through
# dedup / geography-nulling / export-splitting, then dropped by
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

# Natural key for the collision guard (detail_level included so the same
# district-aggregate and school keys can't shadow each other).
NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "detail_level",
    "demographic",
    "grade_level",
    "subject",
]

# Tolerance for snapping publisher-rounding overshoot in the derived
# `_or_above` cumulatives back to 1.0. Bronze per-level pcts are rounded to
# one decimal on the 0-100 scale, so summing three of them can land at most
# one rounding unit above 100 (verified bronze max: 100.1 -> 1.001 on the 0-1
# scale). A probability cannot exceed 1.0; anything above the tolerance is a
# real anomaly and passes through for the bounded-proportion check to flag.
_OR_ABOVE_ROUNDING_TOLERANCE = 0.005


# =============================================================================
# Helpers
# =============================================================================


def _cap_or_above(expr: pl.Expr) -> pl.Expr:
    """Snap small publisher-rounding overshoot above 1.0 back to 1.0.

    Values in (1.0, 1.0 + tolerance] become exactly 1.0; everything else
    (including NULL, via polars NULL-propagation) passes through unchanged.
    """
    return (
        pl.when((expr > 1.0) & (expr <= 1.0 + _OR_ABOVE_ROUNDING_TOLERANCE))
        .then(1.0)
        .otherwise(expr)
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


def _resolve_year(df: pl.DataFrame, path: Path) -> int:
    """Resolve the reporting year and cross-check filename vs file content.

    The filename year is the ending calendar year of the school year; each
    file carries exactly one LONG_SCHOOL_YEAR whose ending year must agree.
    A mismatch means bronze drift and fails loudly.
    """
    filename_year = extract_year_from_filename(path.name)
    if filename_year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")
    school_years = df["LONG_SCHOOL_YEAR"].drop_nulls().unique().to_list()
    if len(school_years) != 1:
        raise ValueError(
            f"{path.name}: expected one LONG_SCHOOL_YEAR, got {school_years}"
        )
    content_year = parse_school_year(school_years[0])
    if content_year != filename_year:
        raise ValueError(
            f"{path.name}: LONG_SCHOOL_YEAR {school_years[0]!r} ending year "
            f"{content_year} disagrees with filename year {filename_year}"
        )
    return filename_year


# =============================================================================
# Shared era transform (Era 1 and Era 2 differ only by one dropped constant)
# =============================================================================


def _transform_era(
    df: pl.DataFrame,
    year: int,
    era: str,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Transform one bronze file (either era) into gold-shaped rows.

    Both eras share the same tidy (entity x grade x subgroup x subject) row
    grain and identical metric column names; Era 2's constant `#ASSMT_CD`
    has already been validated and dropped by the caller.
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
    _require_columns(df, required, f"{era} {year}")

    # Detail level from the ALL sentinels: (ALL, ALL) -> state;
    # (code, ALL) -> district; (code, code) -> school. The structure doc
    # confirms no (ALL, code) rows exist in any file.
    district_clean = pl.col("SCHOOL_DISTRCT_CD").str.strip_chars()
    school_clean = pl.col("INSTN_NUMBER").str.strip_chars()
    df = df.with_columns(
        pl.when(
            (district_clean == BRONZE_ALL_SENTINEL)
            & (school_clean == BRONZE_ALL_SENTINEL)
        )
        .then(pl.lit("state"))
        .when(school_clean == BRONZE_ALL_SENTINEL)
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .alias("detail_level"),
        # Geography keys: sentinel -> NULL before zfill so "ALL" can never be
        # zero-padded into a fake code; zfill(3) pads standard district codes
        # while passing 7-digit state-charter codes through; zfill(4) repairs
        # the unpadded 2015/2019 school codes.
        pl.when(district_clean == BRONZE_ALL_SENTINEL)
        .then(None)
        .otherwise(district_clean.str.zfill(3))
        .alias("district_code"),
        pl.when(school_clean == BRONZE_ALL_SENTINEL)
        .then(None)
        .otherwise(school_clean.str.zfill(4))
        .alias("school_code"),
        pl.lit(year).cast(pl.Int32).alias("year"),
    )

    # Grade level: shared normalizer resolves the unpadded-vs-padded bronze
    # variants ('3' in 2015/2019, '03' elsewhere) to canonical '03'-'08'.
    bronze_grade = df["ACDMC_LVL"]
    df = df.with_columns(normalize_grade_column("ACDMC_LVL").alias("grade_level"))
    observed_grades = {
        str(v).strip().upper() for v in bronze_grade.drop_nulls().unique().to_list()
    }
    manifest.record_categorical(
        column="grade_level",
        map_dict={k: v for k, v in GRADE_LEVEL_MAP.items() if k in observed_grades},
        bronze_series=bronze_grade,
        gold_series=df["grade_level"],
    )

    # Subject: topic-local snake_case map, then the shared spelling
    # normalizer (no-op for these five values; applied per the checklist so
    # cross-topic variants can never diverge silently).
    bronze_subject = df["TEST_CMPNT_TYP_NM"]
    df = df.with_columns(
        pl.col("TEST_CMPNT_TYP_NM")
        .replace_strict(SUBJECT_MAP, default=None)
        .pipe(apply_subject_normalization)
        .alias("subject")
    )
    manifest.record_categorical(
        column="subject",
        map_dict={**SUBJECT_MAP, **SUBJECT_NORMALIZATION_MAP},
        bronze_series=bronze_subject,
        gold_series=df["subject"],
    )

    # Demographic: the shared canonical path (strip/upper/alias-map). The
    # manifest records the effective alias slice — the aliases actually hit
    # this year — per /transform-topic §4.3a, keeping map_used reviewable.
    bronze_demo = df["SUBGROUP_NAME"]
    df = df.with_columns(
        normalize_demographic_column("SUBGROUP_NAME").alias("demographic")
    )
    observed_demo = {
        str(v).strip().upper() for v in bronze_demo.drop_nulls().unique().to_list()
    }
    manifest.record_categorical(
        column="demographic",
        map_dict={k: v for k, v in DEMOGRAPHIC_ALIASES.items() if k in observed_demo},
        bronze_series=bronze_demo,
        gold_series=df["demographic"],
    )

    # Metrics: counts to Int64, percentages to Float64 / 100 (bronze 0-100 ->
    # gold 0-1, §4). strict=False turns residual non-numeric residue (empty
    # fields in 2015-2019; any stray TFS already nulled by read_bronze_file)
    # into NULL instead of raising.
    cast_exprs: list[pl.Expr] = [
        pl.col("NUM_TESTED_CNT").cast(pl.Int64, strict=False).alias("num_tested"),
    ]
    cast_exprs += [
        pl.col(src).cast(pl.Int64, strict=False).alias(dst)
        for src, dst in COUNT_MAP.items()
    ]
    cast_exprs += [
        (pl.col(src).cast(pl.Float64, strict=False) / 100.0).alias(dst)
        for src, dst in PCT_MAP.items()
    ]
    df = df.with_columns(cast_exprs)

    # Derived cumulative thresholds (§16 `_or_above`). NULL whenever any
    # summand is NULL (suppression-as-NULL); rounding overshoot above 1.0 is
    # snapped back within _OR_ABOVE_ROUNDING_TOLERANCE (see module docstring).
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
# File routing
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame:
    """Read one bronze file, detect its era, and route to the era transform.

    All columns are read as Utf8 (``infer_schema_length=0``) so suppressed
    values and zero-padded codes survive intact; every numeric cast happens
    explicitly downstream (§4.3b).
    """
    df, loss = read_bronze_file(path, infer_schema_length=0, return_loss=True)
    year = _resolve_year(df, path)
    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{path.name}: no era signature matched columns {df.columns}")

    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)
    logger.info(
        "Processing %s as %s (year %d, %d rows)", path.name, era, year, df.height
    )

    if era == "era_2_2024":
        # Validate then drop the Era-2 constant. Any value other than the
        # expected code means foreign rows are mixed into this topic's bronze.
        codes = df[ASSMT_CD_COLUMN].drop_nulls().unique().to_list()
        if codes != [ASSMT_CD_EXPECTED]:
            raise ValueError(
                f"{path.name}: unexpected {ASSMT_CD_COLUMN} values {codes} "
                f"(expected only {ASSMT_CD_EXPECTED!r})"
            )
        df = df.drop(ASSMT_CD_COLUMN)

    return _transform_era(df, year, era, manifest)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for EOG assessment by grade."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file (read-loss accounted per file).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR):
        result = transform_file(path, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize columns/dtypes across eras and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)
    logger.info("Combined %d rows across %d files", combined.height, len(all_dfs))

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean an alias/aggregation bug and must raise, not be silently deduped.
    # (Also why no demographic-collision aggregation step exists: no two
    # bronze labels normalize to one canonical key in the same year — Active
    # Duty is 2021-only, Military Connected 2022+, and they map to distinct
    # keys — so any future collision must trip this guard for analysis.)
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: each file is a distinct year and no file carries duplicate
    # natural keys (verified in bronze), so dedup is a safety net; prefer the
    # row with a reported, larger num_tested over a suppressed placeholder.
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

    # 4. Geography nulling from the shared domain rules (transform and
    # validator share one rule source, so they cannot disagree).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. NULL-rate spikes are expected with a documented
    # bronze cause: suppression patterns vary by year (counts ~TFS-heavy in
    # 2015/2019/2021+, near-zero NULLs in 2016-2018; num_tested ~30% NULL in
    # 2024 when GOSA extended TFS to NUM_TESTED_CNT).
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes (documented cause): %s", spike_result.details)
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

    Kept out of ``main()`` so the pipeline flow stays readable. The column
    declaration order MUST match STANDARD_COLUMNS minus ``detail_level`` —
    the contract's properties (and the validator's schema check) follow it.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Georgia Milestones End-of-Grade (EOG) assessment results for "
            "Georgia public-school students in grades 3-8, disaggregated by "
            "individual grade level. Each row is one (entity x grade x "
            "demographic subgroup x subject) cell reporting the number of "
            "students tested plus the count and percentage of test-takers at "
            "each of four achievement levels (Beginning, Developing, "
            "Proficient, Distinguished), with derived cumulative "
            "developing-or-above and proficient-or-above shares. State, "
            "district, and school detail levels. School years 2014-15 "
            "through 2023-24; 2019-20 is absent (EOG administration "
            "cancelled, COVID-19)."
        ),
        title="Georgia Milestones End-of-Grade Assessment by Grade",
        summary=(
            "Georgia Milestones End-of-Grade achievement levels by grade, "
            "subject, and demographic for schools, districts, and the state, "
            "2015-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Ending calendar year of the school year (e.g., 2024 = "
                    "2023-24), from the filename and cross-checked against "
                    "the file's LONG_SCHOOL_YEAR. 2020 has no rows (EOG "
                    "cancelled during COVID-19 closures)."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "GOSA district code (FK to districts dimension): 3-digit "
                    "zero-padded standard codes or 7-digit state-charter / "
                    "commission-charter / state-school codes. NULL on "
                    "state-level rows."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0103",
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
                "short_description": (
                    "Student subgroup the row covers (race, gender, "
                    "economic, disability, English-learner, etc.); 'all' is "
                    "all students."
                ),
                "description": (
                    "Canonical demographic subgroup (FK to the global "
                    "demographics dimension), normalized from bronze "
                    "SUBGROUP_NAME. This topic uses the split race "
                    "convention: asian and pacific_islander are separate, "
                    "mutually exclusive rows (the source publishes both "
                    "labels in every year). 18 core subgroups in 2015-2019; "
                    "active_duty and homeless added in 2021; foster_care and "
                    "military_connected (renaming active_duty) added in "
                    "2022. NON-ADDITIVE MILITARY KEYS: active_duty (2021) "
                    "and military_connected (2022+) never co-occur in a "
                    "year, but conceptually active-duty dependents are a "
                    "subset of military-connected students — do not sum the "
                    "two keys across years as if disjoint."
                ),
            },
            {
                "name": "grade_level",
                "type": "string",
                "nullable": False,
                "example": "05",
                "validValues": ["03", "04", "05", "06", "07", "08"],
                "short_description": (
                    "Grade tested, 03-08; this is the grade-by-grade "
                    "breakout that distinguishes this topic from the "
                    "all-grades rollup."
                ),
                "description": (
                    "Grade of the test-takers in this row, as a canonical "
                    "2-char zero-padded string. Bronze ACDMC_LVL is unpadded "
                    "(3-8) in 2015 and 2019 and zero-padded (03-08) in all "
                    "other years; gold normalizes both to 03-08. This column "
                    "is the grain difference vs the all-grades rollup "
                    "sibling topic."
                ),
            },
            {
                "name": "subject",
                "type": "string",
                "nullable": False,
                "example": "mathematics",
                "validValues": sorted(set(SUBJECT_MAP.values())),
                "short_description": (
                    "EOG content area tested (ELA, mathematics, science, "
                    "social studies, physical science); coverage varies by "
                    "grade and year."
                ),
                "description": (
                    "EOG academic subject. english_language_arts and "
                    "mathematics span grades 3-8 in every year; science and "
                    "social_studies are restricted to grades 5 and 8 from "
                    "2017 (social_studies to grade 8 only from 2021); "
                    "physical_science (2022+) is an 8th-grade accelerated "
                    "option. The natural grade x subject sparsity is "
                    "preserved — untested combinations have no rows; rare "
                    "out-of-pattern audit/retest cells are retained."
                ),
            },
            {
                "name": "num_tested",
                "type": "int64",
                "unit": "count",
                "metric_component": "denominator",
                "example": 144,
                "null_meaning": (
                    "Suppressed by GOSA (TFS, too few students). Rare before "
                    "2024; ~30%% of 2024 rows."
                ),
                "description": (
                    "Number of students tested in this (entity x grade x "
                    "subgroup x subject) cell. NULL when GOSA suppressed the "
                    "cell (TFS); in 2024 GOSA extended suppression to this "
                    "column (~30%% of rows) while still publishing the "
                    "rounded percentage distribution."
                ),
            },
            {
                "name": "num_beginning_learner",
                "type": "int64",
                "unit": "count",
                "example": 11,
                "null_meaning": "Suppressed by GOSA (TFS or empty source field).",
                "description": (
                    "Count of students at the lowest achievement level "
                    "(Beginning Learner). Bronze BEGIN_CNT; NULL when "
                    "suppressed."
                ),
            },
            {
                "name": "num_developing_learner",
                "type": "int64",
                "unit": "count",
                "example": 35,
                "null_meaning": "Suppressed by GOSA (TFS or empty source field).",
                "description": (
                    "Count of students at the second achievement level "
                    "(Developing Learner). Bronze DEVELOPING_CNT; NULL when "
                    "suppressed."
                ),
            },
            {
                "name": "num_proficient_learner",
                "type": "int64",
                "unit": "count",
                "example": 70,
                "null_meaning": "Suppressed by GOSA (TFS or empty source field).",
                "description": (
                    "Count of students at the third achievement level "
                    "(Proficient Learner). Bronze PROFICIENT_CNT; NULL when "
                    "suppressed."
                ),
            },
            {
                "name": "num_distinguished_learner",
                "type": "int64",
                "unit": "count",
                "example": 28,
                "null_meaning": "Suppressed by GOSA (TFS or empty source field).",
                "description": (
                    "Count of students at the highest achievement level "
                    "(Distinguished Learner). Bronze DISTINGUISHED_CNT; the "
                    "most-suppressed metric (~70-76%% of rows in recent "
                    "years — few cells have enough distinguished scorers to "
                    "clear the threshold)."
                ),
            },
            {
                "name": "pct_beginning_learner",
                "type": "float64",
                "unit": "proportion",
                "example": 0.157,
                "null_meaning": (
                    "Suppressed by GOSA (whole-cell suppression; never NULL in 2024)."
                ),
                "description": (
                    "Share of tested students at the Beginning level, 0-1 "
                    "scale (bronze 0-100 divided by 100). Published shares "
                    "are exact to one decimal on the 0-100 scale against "
                    "num_tested. CAVEAT: on foster_care rows from 2022 "
                    "onward the four level shares can sum below 1 (students "
                    "tested but not assigned a level, plus all-zero "
                    "placeholder rows on fully-suppressed cells) — published "
                    "GOSA values are preserved exactly."
                ),
            },
            {
                "name": "pct_developing_learner",
                "type": "float64",
                "unit": "proportion",
                "example": 0.549,
                "null_meaning": (
                    "Suppressed by GOSA (whole-cell suppression; never NULL in 2024)."
                ),
                "description": (
                    "Share of tested students at the Developing level, 0-1 "
                    "scale. See pct_beginning_learner for the foster_care "
                    "caveat."
                ),
            },
            {
                "name": "pct_proficient_learner",
                "type": "float64",
                "unit": "proportion",
                "example": 0.255,
                "null_meaning": (
                    "Suppressed by GOSA (whole-cell suppression; never NULL in 2024)."
                ),
                "description": (
                    "Share of tested students at the Proficient level, 0-1 "
                    "scale. See pct_beginning_learner for the foster_care "
                    "caveat."
                ),
            },
            {
                "name": "pct_distinguished_learner",
                "type": "float64",
                "unit": "proportion",
                "example": 0.039,
                "null_meaning": (
                    "Suppressed by GOSA (whole-cell suppression; never NULL in 2024)."
                ),
                "description": (
                    "Share of tested students at the Distinguished level, "
                    "0-1 scale. See pct_beginning_learner for the "
                    "foster_care caveat."
                ),
            },
            {
                "name": "pct_developing_learner_or_above",
                "type": "float64",
                "unit": "proportion",
                "example": 0.843,
                "null_meaning": "NULL whenever any of its three summands is NULL.",
                "description": (
                    "Derived cumulative share at Developing or above "
                    "(developing + proficient + distinguished), 0-1 scale. "
                    "Computed at transform time from the published per-level "
                    "shares; sums of publisher-rounded shares that land "
                    "within 0.005 above 1.0 are snapped to 1.0 (a share "
                    "cannot exceed 1)."
                ),
            },
            {
                "name": "pct_proficient_learner_or_above",
                "type": "float64",
                "unit": "proportion",
                "key_metric": True,
                "short_description": (
                    "Share of tested students scoring Proficient or "
                    "Distinguished (proficient-or-above), on a 0-1 scale; "
                    "the headline achievement measure."
                ),
                "example": 0.294,
                "null_meaning": "NULL whenever either summand is NULL.",
                "description": (
                    "Derived cumulative share at Proficient or above "
                    "(proficient + distinguished), 0-1 scale. Computed at "
                    "transform time from the published per-level shares; "
                    "rounding overshoot above 1.0 within 0.005 is snapped "
                    "to 1.0."
                ),
            },
        ],
        source="Governor's Office of Student Achievement (GOSA)",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        limitations=(
            "Suppressed cells are NULL (not zero). State rows have NULL "
            "district_code and school_code; district rows have NULL "
            "school_code. 2020 has no rows (EOG cancelled during COVID-19). "
            "Grade x subject coverage is naturally sparse and changes over "
            "time (science/social_studies grades 5+8 only from 2017, "
            "social_studies grade 8 only from 2021, physical_science grade 8 "
            "only). Foster Care caveat (2022-2024): the foster_care rows are "
            "the only rows whose four per-level shares can fail to sum to 1 "
            "— 28 fully-unsuppressed state-level rows carry level counts "
            "summing below num_tested (students tested but not assigned a "
            "performance level at publication), and partially- or "
            "fully-suppressed foster_care cells publish shares covering "
            "only the unsuppressed levels, including an all-four-zeros "
            "placeholder pattern. The published GOSA values are preserved "
            "exactly rather than reconciled."
        ),
        quality_checks=[
            {
                "name": "pct_levels_sum_to_one_excluding_foster_care",
                "description": (
                    "The four achievement-level shares partition the tested "
                    "population: where all four are non-NULL they must sum "
                    "to 1.0 within rounding (+/-0.02) on every row except "
                    "demographic = 'foster_care' (the documented source "
                    "quirk where partially-suppressed and "
                    "unassigned-level rows sum below 1). Verified in bronze: "
                    "every deviating row in every year is a Foster Care row; "
                    "all other rows deviate by at most 0.002."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "demographic != 'foster_care' "
                    "AND pct_beginning_learner IS NOT NULL "
                    "AND pct_developing_learner IS NOT NULL "
                    "AND pct_proficient_learner IS NOT NULL "
                    "AND pct_distinguished_learner IS NOT NULL "
                    "AND ABS((pct_beginning_learner + pct_developing_learner "
                    "+ pct_proficient_learner + pct_distinguished_learner) "
                    "- 1.0) > 0.02"
                ),
                "mustBe": 0,
            },
            {
                "name": "pct_developing_or_above_equals_level_sum",
                "description": (
                    "pct_developing_learner_or_above equals developing + "
                    "proficient + distinguished within rounding tolerance "
                    "(+/-0.011, covering the 0.005 overshoot snap) wherever "
                    "all summands are non-NULL. Holds by construction — the "
                    "column is derived from these summands."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "pct_developing_learner_or_above IS NOT NULL "
                    "AND pct_developing_learner IS NOT NULL "
                    "AND pct_proficient_learner IS NOT NULL "
                    "AND pct_distinguished_learner IS NOT NULL "
                    "AND ABS(pct_developing_learner_or_above "
                    "- (pct_developing_learner + pct_proficient_learner "
                    "+ pct_distinguished_learner)) > 0.011"
                ),
                "mustBe": 0,
            },
            {
                "name": "pct_proficient_or_above_equals_level_sum",
                "description": (
                    "pct_proficient_learner_or_above equals proficient + "
                    "distinguished within rounding tolerance (+/-0.011) "
                    "wherever both summands are non-NULL. Holds by "
                    "construction."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "pct_proficient_learner_or_above IS NOT NULL "
                    "AND pct_proficient_learner IS NOT NULL "
                    "AND pct_distinguished_learner IS NOT NULL "
                    "AND ABS(pct_proficient_learner_or_above "
                    "- (pct_proficient_learner + pct_distinguished_learner)) "
                    "> 0.011"
                ),
                "mustBe": 0,
            },
            {
                "name": "proficient_or_above_never_exceeds_developing_or_above",
                "description": (
                    "Nested cumulative thresholds: the proficient-or-above "
                    "share can never exceed the developing-or-above share "
                    "(+0.001 float slack) where both are non-NULL."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "pct_proficient_learner_or_above IS NOT NULL "
                    "AND pct_developing_learner_or_above IS NOT NULL "
                    "AND pct_proficient_learner_or_above "
                    "> pct_developing_learner_or_above + 0.001"
                ),
                "mustBe": 0,
            },
            {
                "name": "level_count_never_exceeds_num_tested",
                "description": (
                    "No single achievement-level count can exceed the number "
                    "tested in its cell. Verified: zero violations in every "
                    "bronze year."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE num_tested IS NOT NULL "
                    "AND ((num_beginning_learner IS NOT NULL AND "
                    "num_beginning_learner > num_tested) "
                    "OR (num_developing_learner IS NOT NULL AND "
                    "num_developing_learner > num_tested) "
                    "OR (num_proficient_learner IS NOT NULL AND "
                    "num_proficient_learner > num_tested) "
                    "OR (num_distinguished_learner IS NOT NULL AND "
                    "num_distinguished_learner > num_tested))"
                ),
                "mustBe": 0,
            },
            {
                "name": "level_counts_sum_never_exceed_num_tested",
                "description": (
                    "Where all four level counts and num_tested are "
                    "non-NULL, the level counts sum to at most num_tested "
                    "(the four levels partition test-takers; the only "
                    "source deviation — 28 state-level foster_care rows — "
                    "falls short, never over)."
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
                "name": "level_counts_sum_equals_num_tested_below_state",
                "description": (
                    "On district- and school-level rows (district_code IS "
                    "NOT NULL — quality SQL self-scopes by geography "
                    "NULL-ness), fully-unsuppressed cells reconcile exactly: "
                    "the four level counts sum to num_tested. The only "
                    "source exceptions are 28 STATE-level foster_care rows "
                    "(2022-2024), excluded by the scope and documented in "
                    "limitations."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE district_code IS NOT NULL "
                    "AND num_tested IS NOT NULL "
                    "AND num_beginning_learner IS NOT NULL "
                    "AND num_developing_learner IS NOT NULL "
                    "AND num_proficient_learner IS NOT NULL "
                    "AND num_distinguished_learner IS NOT NULL "
                    "AND (num_beginning_learner + num_developing_learner "
                    "+ num_proficient_learner + num_distinguished_learner) "
                    "!= num_tested"
                ),
                "mustBe": 0,
            },
            {
                "name": "pct_matches_count_share",
                "description": (
                    "Each published level share equals its level count "
                    "divided by num_tested within one-decimal source "
                    "rounding (+/-0.0006 on the 0-1 scale) wherever count, "
                    "share, and num_tested are all non-NULL. Verified max "
                    "bronze deviation 0.0005 — holds even on the foster_care "
                    "shortfall rows (shares are computed against num_tested)."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE num_tested IS NOT NULL "
                    "AND num_tested > 0 AND ("
                    "(pct_beginning_learner IS NOT NULL AND "
                    "num_beginning_learner IS NOT NULL AND "
                    "ABS(pct_beginning_learner - CAST(num_beginning_learner "
                    "AS DOUBLE) / num_tested) > 0.0006) "
                    "OR (pct_developing_learner IS NOT NULL AND "
                    "num_developing_learner IS NOT NULL AND "
                    "ABS(pct_developing_learner - CAST(num_developing_learner "
                    "AS DOUBLE) / num_tested) > 0.0006) "
                    "OR (pct_proficient_learner IS NOT NULL AND "
                    "num_proficient_learner IS NOT NULL AND "
                    "ABS(pct_proficient_learner - CAST(num_proficient_learner "
                    "AS DOUBLE) / num_tested) > 0.0006) "
                    "OR (pct_distinguished_learner IS NOT NULL AND "
                    "num_distinguished_learner IS NOT NULL AND "
                    "ABS(pct_distinguished_learner - "
                    "CAST(num_distinguished_learner AS DOUBLE) / num_tested) "
                    "> 0.0006))"
                ),
                "mustBe": 0,
            },
        ],
        notes=[
            (
                "Two bronze eras share one gold schema: Era 1 (2015-2023, 8 "
                "files) is the 17-column tidy by-grade format; Era 2 (2024) "
                "adds only the constant '#ASSMT_CD' = 'EOG_by_GRADE', "
                "validated and dropped. 2020 is absent (COVID-19)."
            ),
            (
                "grade_level is part of the natural key — this topic "
                "disaggregates the all-grades rollup sibling "
                "(georgia_milestones_end_of_grade_eog_assessment) into one "
                "row per grade 3-8. Do not merge the two topics; they are "
                "different grains. Lexile scores live in a third sibling "
                "(georgia_milestones_end_of_grade_lexile)."
            ),
            (
                "Race rows follow the split convention (asian and "
                "pacific_islander published separately in every year); no "
                "combined asian_pacific_islander rollup exists or is "
                "synthesized (data-cleaning-standards §5a/§5b)."
            ),
            (
                "Military keys are non-additive: active_duty (2021 only) "
                "and military_connected (2022+, the renamed label) are "
                "distinct canonical keys; active-duty dependents are "
                "conceptually a subset of military-connected students."
            ),
            (
                "Suppression mechanisms vary by year: 2015/2019 use both "
                "'TFS' strings and empty fields; 2016-2018 use empty fields "
                "only; 2021-2023 use 'TFS' only (occasionally on the pct "
                "columns); 2024 extends 'TFS' to NUM_TESTED_CNT (~30% of "
                "rows) while pct columns are never suppressed there. All "
                "suppressed values are NULL in gold."
            ),
            (
                "The two cumulative '_or_above' columns are derived at "
                "transform time from the published per-level shares "
                "(bronze does not publish them); sums landing within 0.005 "
                "above 1.0 from publisher rounding are snapped to 1.0."
            ),
            (
                "Foster Care (2022-2024) is the only subgroup whose level "
                "shares can fail to sum to 1: 28 state-level rows have "
                "level counts summing below num_tested (tested but no "
                "level assigned), and partially/fully suppressed "
                "foster_care cells publish shares covering only "
                "unsuppressed levels (including all-four-zeros placeholder "
                "rows). Published values preserved exactly."
            ),
            (
                "ID formatting: district_code zfill(3) with 7-digit "
                "state-administered codes passed through; school_code "
                "zfill(4) repairs the unpadded 2015/2019 codes."
            ),
        ],
    )


if __name__ == "__main__":
    main()
