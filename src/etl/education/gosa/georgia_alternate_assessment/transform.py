"""Transform bronze georgia_alternate_assessment files into gold fact tables.

Source: Governor's Office of Student Achievement (GOSA) — Georgia Alternate
Assessment (GAA) participation and achievement-level results for Georgia
public school students with significant cognitive disabilities. 16 bronze
files cover 2004-2007 and 2011-2024 (2008-2010 are GOSA archive gaps;
2020-2021 are COVID testing suspensions).

Era routing (column-signature detection, most-specific first):

    * Era 1 (2004-2006): 4-col participation summary keyed by the compound
      `SysSchoolID` (`"<district>:<school>"`, `ALL` sentinel on either side).
      Metrics: enrollment in AYP-applicable grades + count taking the GAA.
      No demographics, no subject, no achievement levels. The 2005/2006
      files carry `.csv` extensions but are OLE2 Excel binaries —
      `read_bronze_file` detects the real format via magic bytes.
    * Era 2 (2007): same 4 semantic columns renamed lowercase/short
      (`sysschoolid` / `schoolname` / `Enroll` / `Number`). Real `.xls`.
    * Era 3 (2011-2018): 16-col tidy achievement fact per (entity x
      subgroup x subject). 3-tier scoring (LIMITED/PARTIAL/ADEQUATE); the
      `THUROUGH_*` columns (source typo) are reserved-but-never-populated
      (verified: only 0/null in all 8 files) and are dropped — the gold
      `*_distinguished_learner` metrics are NULL for this era, never 0.
      Suppression = null cells.
    * Era 4 (2019): generic `Level1`-`Level4` names; first 4-tier year, all
      levels populated. `INSTN_NUMBER` is NOT zero-padded in this one file
      (`"100"` not `"0100"`) — zfill(4) at gold time fixes it.
    * Era 5 (2022-2023): typo corrected to `THOROUGH_*`; 4-tier; `"TFS"`
      string suppression (mapped to NULL by the shared reader).
    * Era 6 (2024): adds `#ASSMT_CD` = "GAA" and `ACDMC_LVL` = "ALL GRADES"
      constants (verified constant, dropped) and renames levels to the
      Milestones names (`BEGIN`/`DEVELOPING`/`PROFICIENT`/`DISTINGUISHED`,
      `*_PCT`). Suppressed rows are now EMITTED with `"TFS"` fills instead
      of omitted (row count jumps ~15K -> ~64K), `NUM_TESTED_CNT` is itself
      suppressed on ~84% of rows, while `BEGIN/DEVELOPING/PROFICIENT_PCT`
      are never suppressed — percentages remain usable signal on otherwise
      fully suppressed rows.

Achievement-level unification (gold names per data-cleaning-standards §16):

    beginning     <- LIMITED (E3/E5) / Level1 (E4) / BEGIN (E6)
    developing    <- PARTIAL (E3/E5) / Level2 (E4) / DEVELOPING (E6)
    proficient    <- ADEQUATE (E3/E5) / Level3 (E4) / PROFICIENT (E6)
    distinguished <- Level4 (E4) / THOROUGH (E5) / DISTINGUISHED (E6);
                     NULL for Era 3 (tier did not exist) and Eras 1-2.

Derived cumulative `_or_above` columns (era-aware):

    * 4-tier eras (2019+): developing_or_above = developing + proficient +
      distinguished; proficient_or_above = proficient + distinguished.
      NULL-propagates on any suppressed summand.
    * Era 3 (2011-2018, 3-tier): the distinguished tier is ABSENT, not a
      null summand — developing_or_above = developing + proficient and
      proficient_or_above = proficient, so Era 3 cumulatives are populated.
    * Publisher-rounded per-level pcts can sum slightly past 1.0 (bronze max
      100.1 on the 0-100 scale, verified per file); `_cap_or_above` snaps
      overshoot within +0.005 back to 1.0 so the `proportion` unit contract
      holds. Larger overshoot would pass through and fail validation.

Era 1-2 data repairs (all manifest-recorded):

    * 2004 has one fully-null trailing row (id null) — dropped.
    * 2004 republishes 136 rows as exact duplicates (districts 644-647) —
      one copy kept (lossless), recorded as `exact_duplicate_row`.
    * 2004 has one all-null-metrics placeholder twin: `647:3058 Northside
      Elementary` appears once with null metrics and once (as "Northside
      Elementary School") with enrollment=406 / tested=10. The all-null twin
      is dropped BEFORE the collision guard per the sanctioned §4.6 pattern
      (the guard counts NULL as divergent), recorded as
      `all_null_placeholder_twin`.

Known source quirks preserved (extreme-but-conceivable, §4b):

    * 644:3058 (DeKalb, Margaret Harris-adjacent special school) reports
      num_tested > num_enrolled_ayp_grades in 2004 (51 > 44) and 2005
      (52 > 50). Conceivable: the enrollment denominator counts only AYP
      grades (1-8, 11) while the GAA is administered to students in other
      grades too. Preserved + documented; no num_tested <= enrollment
      quality check is authored because the source disproves it.
    * The "Homeless" subgroup's four level percentages sum to ~50%% instead
      of ~100%% (denominator inconsistency at the source). 2022-2023 show it
      on a handful of district/state rows (50 in 2022, 77 in 2023); in 2024
      the quirk is SYSTEMATIC — all 1,135 Homeless rows at every detail
      level (4 state, 300 district, 831 school) publish shares summing to
      0.499-0.501. Preserved as published; the partition-sums-to-one
      quality check is therefore scoped to 2011-2019 and only an
      upper-bound check is asserted for 2022+.

No §4b impossible-value mask is needed: every bronze percentage is within
0-100 and every count is non-negative (verified across all 16 files).

Demographics: Era 3-6 `SUBGROUP_NAME` (22 labels by 2024) normalize via the
shared DEMOGRAPHIC_ALIASES with zero unmapped values. This is a
split-convention topic (§5b): bronze publishes separate "Asian" and "Native
Hawaiian or Other Pacific Islander" rows, so bare "Asian" is genuinely
Asian-only. Every observed label maps to a distinct canonical key
("Active Duty" -> active_duty and "Military Connected" -> military_connected
are intentionally distinct, nested keys), so no demographic collisions can
occur and `aggregate_demographic_collisions` is not needed; the collision
guard protects against future alias changes. Eras 1-2 have no demographic
axis — those rows carry the literal `demographic = "all"`.
"""

import logging
from pathlib import Path

import polars as pl

from src.utils.demographics import DEMOGRAPHIC_ALIASES, normalize_demographic_column
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

TOPIC = "georgia_alternate_assessment"
BRONZE_DIR = Path("data/bronze/education/gosa/georgia_alternate_assessment")
GOLD_DIR = Path("data/gold/education/georgia_alternate_assessment")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Bronze sentinel marking aggregate rows. Era 3-6 use it directly in
# SCHOOL_DISTRCT_CD / INSTN_NUMBER; Eras 1-2 use the same token on either
# side of the ":" in the compound SysSchoolID. Always uppercase in source
# (verified: no mixed-case variants in any file).
BRONZE_ALL_SENTINEL = "ALL"

# Bronze TEST_CMPNT_TYP_NM -> gold `subject` (§16 canonical snake_case).
# The four GAA content areas are stable across every tiered era.
SUBJECT_MAP: dict[str, str] = {
    "English Language Arts": "english_language_arts",
    "Mathematics": "mathematics",
    "Science": "science",
    "Social Studies": "social_studies",
}

# Era-detection signatures, most-specific first. Era 6 is Era-5-shaped plus
# new constants and Milestones level names; Era 4 is distinguished by the
# generic Level1/Level4 names; Era 3 by the THUROUGH typo. Era 1 vs Era 2 is
# the `SysSchoolID` vs `sysschoolid` casing.
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_6_2024": [
        "#ASSMT_CD",
        "ACDMC_LVL",
        "LONG_SCHOOL_YEAR",
        "SCHOOL_DISTRCT_CD",
        "INSTN_NUMBER",
        "BEGIN_CNT",
        "DISTINGUISHED_CNT",
    ],
    "era_5_2022_2023": [
        "LONG_SCHOOL_YEAR",
        "SCHOOL_DISTRCT_CD",
        "INSTN_NUMBER",
        "TEST_CMPNT_TYP_NM",
        "LIMITED_CNT",
        "THOROUGH_CNT",
    ],
    "era_4_2019": [
        "LONG_SCHOOL_YEAR",
        "SCHOOL_DISTRCT_CD",
        "INSTN_NUMBER",
        "TEST_CMPNT_TYP_NM",
        "Level1_CNT",
        "Level4_CNT",
    ],
    "era_3_2011_2018": [
        "LONG_SCHOOL_YEAR",
        "SCHOOL_DISTRCT_CD",
        "INSTN_NUMBER",
        "TEST_CMPNT_TYP_NM",
        "LIMITED_CNT",
        "THUROUGH_CNT",
    ],
    "era_1_2004_2006": [
        "SysSchoolID",
        "School Name",
        "Enrollment in Grades Applicable to AYP Grades 1 through 8 and 11",
        "Number of Students Taking the GAA",
    ],
    "era_2_2007": [
        "sysschoolid",
        "schoolname",
        "Enroll",
        "Number",
    ],
}

# Gold fact column order per §1: year, geography keys, demographic, topic
# categoricals, metrics. `detail_level` is carried for dedup / geography
# nulling / export splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "subject",
    "num_enrolled_ayp_grades",
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
    "subject": pl.Utf8,
    "num_enrolled_ayp_grades": pl.Int64,
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
    "num_enrolled_ayp_grades",
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
# pre-nulled geography patterns (district rows already carry school_code
# NULL) cannot alias across levels. subject is NULL for Era 1-2 rows —
# polars group_by treats NULL keys as equal, which is the wanted semantics.
NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "detail_level",
    "demographic",
    "subject",
]

# Bronze achievement-level column -> gold metric name, per era. Era 3 has no
# 4th tier (THUROUGH_* dropped; gold distinguished metrics stay NULL).
ERA3_COUNT_MAP: dict[str, str] = {
    "LIMITED_CNT": "num_beginning_learner",
    "PARTIAL_CNT": "num_developing_learner",
    "ADEQUATE_CNT": "num_proficient_learner",
}
ERA3_PCT_MAP: dict[str, str] = {
    "LIMITED_PERCENT": "pct_beginning_learner",
    "PARTIAL_PERCENT": "pct_developing_learner",
    "ADEQUATE_PERCENT": "pct_proficient_learner",
}
ERA4_COUNT_MAP: dict[str, str] = {
    "Level1_CNT": "num_beginning_learner",
    "Level2_CNT": "num_developing_learner",
    "Level3_CNT": "num_proficient_learner",
    "Level4_CNT": "num_distinguished_learner",
}
ERA4_PCT_MAP: dict[str, str] = {
    "Level1_PERCENT": "pct_beginning_learner",
    "Level2_PERCENT": "pct_developing_learner",
    "Level3_PERCENT": "pct_proficient_learner",
    "Level4_PERCENT": "pct_distinguished_learner",
}
ERA5_COUNT_MAP: dict[str, str] = {
    "LIMITED_CNT": "num_beginning_learner",
    "PARTIAL_CNT": "num_developing_learner",
    "ADEQUATE_CNT": "num_proficient_learner",
    "THOROUGH_CNT": "num_distinguished_learner",
}
ERA5_PCT_MAP: dict[str, str] = {
    "LIMITED_PERCENT": "pct_beginning_learner",
    "PARTIAL_PERCENT": "pct_developing_learner",
    "ADEQUATE_PERCENT": "pct_proficient_learner",
    "THOROUGH_PERCENT": "pct_distinguished_learner",
}
ERA6_COUNT_MAP: dict[str, str] = {
    "BEGIN_CNT": "num_beginning_learner",
    "DEVELOPING_CNT": "num_developing_learner",
    "PROFICIENT_CNT": "num_proficient_learner",
    "DISTINGUISHED_CNT": "num_distinguished_learner",
}
ERA6_PCT_MAP: dict[str, str] = {
    "BEGIN_PCT": "pct_beginning_learner",
    "DEVELOPING_PCT": "pct_developing_learner",
    "PROFICIENT_PCT": "pct_proficient_learner",
    "DISTINGUISHED_PCT": "pct_distinguished_learner",
}

# Era-3 bronze columns with the source typo `THUROUGH` — always 0/null
# (verified per file), dropped so gold never serves an all-zero phantom tier.
ERA3_THUROUGH_COLS: tuple[str, ...] = ("THUROUGH_CNT", "THUROUGH_PERCENT")

# Publisher-rounding tolerance for the derived `_or_above` cumulatives.
# Bronze per-level pcts are rounded to one decimal on the 0-100 scale, so
# their sum can overshoot 100 by up to 0.1 (verified max 100.1 across all
# files). A proportion cannot exceed 1.0 — overshoot within this tolerance
# is snapped back to 1.0; anything larger passes through for the validator
# to flag (none exists in current bronze).
_OR_ABOVE_ROUNDING_TOLERANCE = 0.005


# =============================================================================
# Helpers
# =============================================================================


def _cap_or_above(expr: pl.Expr) -> pl.Expr:
    """Snap publisher-rounding overshoot just above 1.0 back to 1.0."""
    return (
        pl.when((expr > 1.0) & (expr <= 1.0 + _OR_ABOVE_ROUNDING_TOLERANCE))
        .then(1.0)
        .otherwise(expr)
    )


def _null_if_all(col: pl.Expr) -> pl.Expr:
    """Return NULL where the value equals the bronze `ALL` sentinel."""
    return pl.when(col == BRONZE_ALL_SENTINEL).then(None).otherwise(col)


def _format_district_code(col: pl.Expr) -> pl.Expr:
    """zfill(3) district codes; 7-digit state-charter codes pass unchanged."""
    return col.cast(pl.Utf8).str.zfill(3)


def _format_school_code(col: pl.Expr) -> pl.Expr:
    """zfill(4) school codes — fixes Era 4 (2019) unpadded INSTN_NUMBER."""
    return col.cast(pl.Utf8).str.zfill(4)


def _assert_school_year_matches(df: pl.DataFrame, year: int, era: str) -> None:
    """Fail loudly if LONG_SCHOOL_YEAR's ending year != the filename year.

    Era 3-6 files carry exactly one LONG_SCHOOL_YEAR value ("YYYY-YY"); a
    mismatch would mean bronze drift, which must halt rather than mislabel
    a whole year of data.
    """
    observed = df["LONG_SCHOOL_YEAR"].drop_nulls().unique().to_list()
    if len(observed) != 1 or parse_school_year(observed[0]) != year:
        raise ValueError(
            f"{era} year {year}: LONG_SCHOOL_YEAR {observed!r} does not match "
            f"the filename year — bronze drift, re-check the source file."
        )


# =============================================================================
# Eras 1-2 (2004-2007): participation-only summary
# =============================================================================


def _transform_era12(
    df: pl.DataFrame,
    year: int,
    era: str,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Transform a 2004-2007 participation-summary file (Era 1 or Era 2).

    Both eras carry two metrics (`num_enrolled_ayp_grades`, `num_tested`) per
    entity at all three detail levels, with no demographic or subject axis.
    Gold rows get `demographic = "all"`, `subject = NULL`, and NULL for
    every achievement-level metric. The only Era 1 vs Era 2 difference is
    column naming.
    """
    if era == "era_1_2004_2006":
        id_col = "SysSchoolID"
        enroll_col = "Enrollment in Grades Applicable to AYP Grades 1 through 8 and 11"
        tested_col = "Number of Students Taking the GAA"
    else:  # era_2_2007
        id_col = "sysschoolid"
        enroll_col = "Enroll"
        tested_col = "Number"

    # Missing source columns would silently NULL a whole year's metrics —
    # fail loudly instead (rename-coverage verification, §4.1).
    missing = {id_col, enroll_col, tested_col} - set(df.columns)
    if missing:
        raise ValueError(
            f"{era} year {year}: bronze is missing expected columns {missing}; "
            f"available: {sorted(df.columns)}"
        )

    # Drop fully-null trailing rows (2004 has exactly one). A null id makes
    # the row unidentifiable; its metrics are null too (verified).
    before = df.height
    df = df.filter(pl.col(id_col).is_not_null())
    dropped = before - df.height
    if dropped:
        logger.info(f"{era} year {year}: dropped {dropped} fully-null trailing row(s)")
        manifest.record_filtered(year, dropped, "all_null_trailing_row")

    # Split the compound id: "ALL:ALL" -> state, "<d>:ALL" -> district,
    # "<d>:<s>" -> school. The token is always uppercase in source.
    split = pl.col(id_col).str.split_exact(":", 1)
    df = df.with_columns(
        split.struct.field("field_0").alias("_district_raw"),
        split.struct.field("field_1").alias("_school_raw"),
    )
    df = df.with_columns(
        pl.when(
            (pl.col("_district_raw") == BRONZE_ALL_SENTINEL)
            & (pl.col("_school_raw") == BRONZE_ALL_SENTINEL)
        )
        .then(pl.lit("state"))
        .when(pl.col("_school_raw") == BRONZE_ALL_SENTINEL)
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .cast(pl.Utf8)
        .alias("detail_level"),
    )

    # ALL -> NULL before zfill so the sentinel never becomes a padded code.
    df = df.with_columns(
        _format_district_code(_null_if_all(pl.col("_district_raw"))).alias(
            "district_code"
        ),
        _format_school_code(_null_if_all(pl.col("_school_raw"))).alias("school_code"),
        pl.lit(year).cast(pl.Int32).alias("year"),
        # No demographic axis in these years — the row is the full population.
        pl.lit("all").cast(pl.Utf8).alias("demographic"),
        pl.lit(None).cast(pl.Utf8).alias("subject"),
        pl.col(enroll_col)
        .cast(pl.Int64, strict=False)
        .alias("num_enrolled_ayp_grades"),
        pl.col(tested_col).cast(pl.Int64, strict=False).alias("num_tested"),
    )
    df = df.select([c for c in STANDARD_COLUMNS if c in df.columns])

    # 2004 republishes some rows verbatim (136 exact duplicates, districts
    # 644-647). Keeping one copy is lossless; divergent duplicates survive
    # for the placeholder-twin filter / collision guard below.
    before = df.height
    dup_sample = df.filter(df.is_duplicated()).head(3).to_dicts()
    df = df.unique(maintain_order=False)
    dup_dropped = before - df.height
    if dup_dropped:
        logger.info(
            f"{era} year {year}: dropped {dup_dropped} exact-duplicate "
            f"row(s); sample: {dup_sample}"
        )
        manifest.record_filtered(year, dup_dropped, "exact_duplicate_row")

    # §4.6 all-null placeholder twin: drop rows whose metrics are both NULL
    # when a same-key row with data exists (2004: 647:3058 "Northside
    # Elementary" null twin alongside the populated row). The collision
    # guard counts NULL as divergent, so the twin must go before the guard.
    keys = ["year", "district_code", "school_code", "detail_level"]
    row_has_data = (
        pl.col("num_enrolled_ayp_grades").is_not_null()
        | pl.col("num_tested").is_not_null()
    )
    is_placeholder_twin = (
        ~row_has_data & row_has_data.any().over(keys) & (pl.len().over(keys) > 1)
    )
    twins = df.filter(is_placeholder_twin)
    if twins.height:
        logger.info(
            f"{era} year {year}: dropped {twins.height} all-null placeholder "
            f"twin(s): {twins.select(keys).to_dicts()}"
        )
        manifest.record_filtered(year, twins.height, "all_null_placeholder_twin")
        df = df.filter(~is_placeholder_twin)

    # No categorical recoding occurs in Eras 1-2 (demographic is a constant
    # literal; there is no subject) — nothing to record on the manifest.
    return df


# =============================================================================
# Eras 3-6 (2011-2024): tidy achievement-level fact
# =============================================================================


def _transform_era36(
    df: pl.DataFrame,
    year: int,
    era: str,
    count_map: dict[str, str],
    pct_map: dict[str, str],
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Shared transform for the four tiered eras (3-6).

    The eras share one structural shape — a tidy row per (entity x subgroup
    x subject) with level counts and percentages — and differ only in the
    achievement-level column names (count_map / pct_map) and in whether the
    distinguished tier exists (absent from Era 3's map).
    """
    required = (
        {
            "LONG_SCHOOL_YEAR",
            "SCHOOL_DISTRCT_CD",
            "INSTN_NUMBER",
            "SUBGROUP_NAME",
            "TEST_CMPNT_TYP_NM",
            "NUM_TESTED_CNT",
        }
        | set(count_map)
        | set(pct_map)
    )
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"{era} year {year}: bronze is missing expected columns "
            f"{sorted(missing)}; available: {sorted(df.columns)}"
        )

    _assert_school_year_matches(df, year, era)

    # Detail level from the ALL sentinels: both ALL -> state; school-side
    # ALL only -> district; both real codes -> school.
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

    # ALL -> NULL before zfill; zfill(4) also repairs Era 4's unpadded codes.
    df = df.with_columns(
        _format_district_code(_null_if_all(pl.col("SCHOOL_DISTRCT_CD"))).alias(
            "district_code"
        ),
        _format_school_code(_null_if_all(pl.col("INSTN_NUMBER"))).alias("school_code"),
        pl.lit(year).cast(pl.Int32).alias("year"),
    )

    # Subject: topic-local map, then the shared §10a normalizer (a no-op for
    # these four canonical values; guards against future vocabulary drift).
    bronze_subject = df["TEST_CMPNT_TYP_NM"]
    df = df.with_columns(
        apply_subject_normalization(
            pl.col("TEST_CMPNT_TYP_NM").replace_strict(SUBJECT_MAP, default="99999999")
        ).alias("subject")
    )
    manifest.record_categorical(
        column="subject",
        map_dict=SUBJECT_MAP,
        bronze_series=bronze_subject,
        gold_series=df["subject"],
    )

    # Demographic: the shared canonical path. Record the EFFECTIVE alias
    # slice (§4.3a) — the aliases actually hit, not all ~200 — preserving
    # the manifest's unmapped guard.
    bronze_demo = df["SUBGROUP_NAME"]
    df = df.with_columns(
        normalize_demographic_column("SUBGROUP_NAME").alias("demographic")
    )
    effective_aliases = {
        label: DEMOGRAPHIC_ALIASES[label.strip().upper()]
        for label in bronze_demo.drop_nulls().unique().to_list()
        if label.strip().upper() in DEMOGRAPHIC_ALIASES
    }
    manifest.record_categorical(
        column="demographic",
        map_dict=effective_aliases,
        bronze_series=bronze_demo,
        gold_series=df["demographic"],
    )

    # Metric casts. Bronze is all-Utf8 (infer_schema_length=0) with "TFS"
    # already nulled by the shared reader; strict=False nulls any residue.
    # Percentages are 0-100 in bronze -> divide by 100 (§4).
    cast_exprs: list[pl.Expr] = [
        pl.col("NUM_TESTED_CNT").cast(pl.Int64, strict=False).alias("num_tested"),
    ]
    for bronze_name, gold_name in count_map.items():
        cast_exprs.append(
            pl.col(bronze_name).cast(pl.Int64, strict=False).alias(gold_name)
        )
    for bronze_name, gold_name in pct_map.items():
        cast_exprs.append(
            (pl.col(bronze_name).cast(pl.Float64, strict=False) / 100.0).alias(
                gold_name
            )
        )
    df = df.with_columns(cast_exprs)

    # Era 3 has no distinguished tier — emit typed NULLs (never 0) so the
    # 3-tier years cannot be mistaken for "zero distinguished learners".
    has_distinguished = "pct_distinguished_learner" in pct_map.values()
    if not has_distinguished:
        df = df.with_columns(
            pl.lit(None).cast(pl.Int64).alias("num_distinguished_learner"),
            pl.lit(None).cast(pl.Float64).alias("pct_distinguished_learner"),
        )

    # Eras 3-6 never publish the AYP-grades enrollment column.
    df = df.with_columns(
        pl.lit(None).cast(pl.Int64).alias("num_enrolled_ayp_grades"),
    )

    # Derived cumulative `_or_above` shares. NULL-propagation on suppressed
    # summands is the standard; Era 3's absent distinguished tier is OMITTED
    # from the sums (not a null summand) so 3-tier cumulatives stay
    # computable. `_cap_or_above` snaps rounding overshoot back to 1.0.
    if has_distinguished:
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
    else:
        df = df.with_columns(
            _cap_or_above(
                pl.col("pct_developing_learner") + pl.col("pct_proficient_learner")
            ).alias("pct_developing_learner_or_above"),
            _cap_or_above(pl.col("pct_proficient_learner")).alias(
                "pct_proficient_learner_or_above"
            ),
        )

    return df.select(STANDARD_COLUMNS)


# =============================================================================
# File dispatcher
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read one bronze file, detect its era, and route to the era handler."""
    # infer_schema_length=0 forces all-Utf8 so zero-padded codes keep their
    # leading zeros and every metric is cast explicitly downstream (§4.3b).
    # (Ignored for the three Excel files, which already read as strings.)
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

    if era in ("era_1_2004_2006", "era_2_2007"):
        return _transform_era12(df, year, era, manifest)
    if era == "era_3_2011_2018":
        # Drop the reserved-but-empty THUROUGH columns (source typo; only
        # 0/null) so gold never carries an all-zero phantom 4th tier.
        df = df.drop([c for c in ERA3_THUROUGH_COLS if c in df.columns])
        return _transform_era36(df, year, era, ERA3_COUNT_MAP, ERA3_PCT_MAP, manifest)
    if era == "era_4_2019":
        return _transform_era36(df, year, era, ERA4_COUNT_MAP, ERA4_PCT_MAP, manifest)
    if era == "era_5_2022_2023":
        return _transform_era36(df, year, era, ERA5_COUNT_MAP, ERA5_PCT_MAP, manifest)
    if era == "era_6_2024":
        # Verify then drop the two 2024-only constants — topic identity and
        # an all-grades marker carry no row-level signal.
        for col, expected in (("#ASSMT_CD", "GAA"), ("ACDMC_LVL", "ALL GRADES")):
            vals = df[col].drop_nulls().unique().to_list()
            if vals != [expected]:
                raise ValueError(f"{era} year {year}: unexpected {col} values {vals}")
        df = df.drop(["#ASSMT_CD", "ACDMC_LVL"])
        return _transform_era36(df, year, era, ERA6_COUNT_MAP, ERA6_PCT_MAP, manifest)
    raise ValueError(f"Unhandled era: {era}")


# =============================================================================
# Pipeline orchestration
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for the GAA topic."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform each bronze file (read-loss accounted per file).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR, extensions=[".csv", ".xls"]):
        result = transform_file(path, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize columns/dtypes across eras and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs, how="vertical")
    logger.info(f"Combined all years: {combined.height:,} rows")

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean an alias/aggregation bug and must raise, never be silently
    # deduped. aggregate_demographic_collisions is not needed — every
    # observed bronze label maps to a distinct canonical key (verified;
    # "Active Duty" -> active_duty and "Military Connected" ->
    # military_connected are intentionally distinct nested keys), and the
    # 2004 exact-duplicate/placeholder-twin repairs run upstream in
    # _transform_era12.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: one bronze file per year, in-file natural keys are unique
    # (verified for every Era 3-6 file) and the Era 1-2 duplicates are
    # repaired upstream — dedup is a pure safety net. sort_col="num_tested"
    # prefers a reported, larger-count row over a suppressed placeholder
    # should a future republish ever introduce a duplicate.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code", "demographic", "subject"],
        district_keys=["year", "district_code", "demographic", "subject"],
        state_keys=["year", "demographic", "subject"],
        sort_col="num_tested",
    )

    # 4. Geography nulling via the shared rule source (transform and
    # validator can't disagree). The era handlers already null the ALL
    # sentinels, so this is a formal no-op enforcement pass.
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # No §4b mask: no impossible values exist in this source (verified —
    # every bronze pct is 0-100, every count >= 0; the 644:3058 2004/2005
    # num_tested > num_enrolled_ayp_grades rows are conceivable because the
    # enrollment denominator only counts AYP grades — preserved, documented).

    # Pre-export sanity. Expected NULL-rate spikes (warnings, documented):
    # num_enrolled_ayp_grades is 100%% NULL from 2011 on; distinguished
    # metrics are 100%% NULL for 2011-2018 (3-tier era); num_tested is ~84%%
    # NULL in 2024 (suppression policy change); all pct/level metrics are
    # 100%% NULL for 2004-2007 (participation-only era).
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning(f"NULL-rate spikes: {spike_result.details}")
    validate_output(
        combined,
        required_non_null=["year", "detail_level", "demographic"],
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
            "Georgia Alternate Assessment (GAA) participation and "
            "achievement-level results for Georgia public school students "
            "with significant cognitive disabilities, published by the "
            "Governor's Office of Student Achievement (GOSA). The GAA is a "
            "separate assessment from Georgia Milestones, taken by students "
            "whose IEP team determines they cannot access the general "
            "assessment. Two measure regimes share one schema: 2004-2007 is "
            "a participation summary (enrollment in AYP-applicable grades "
            "plus the count of students taking the GAA per school/district/"
            "state, no demographics, no subject), while 2011-2024 is a tidy "
            "achievement-level fact per (entity x demographic subgroup x "
            "subject) with counts and percentages at up to four achievement "
            "levels plus two derived cumulative shares. 2011-2018 is the "
            "portfolio-based 3-tier GAA 1.0 (no distinguished tier — those "
            "metrics are NULL, not 0); the Milestones-aligned 4-tier GAA "
            "2.0 begins in 2019. Coverage: 2004-2007, 2011-2019, 2022-2024 "
            "(2008-2010 are GOSA archive gaps; 2020-2021 COVID testing "
            "suspensions)."
        ),
        title="Georgia Alternate Assessment (GAA)",
        summary=(
            "Achievement results on the alternate assessment for Georgia "
            "students with significant cognitive disabilities, by subject and "
            "subgroup, 2004-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Ending calendar year of the school year (e.g., 2024 = "
                    "2023-24). Derived from the filename; for 2011-2024 "
                    "cross-checked against the source's LONG_SCHOOL_YEAR. "
                    "2008-2010 and 2020-2021 are absent from the source."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "GOSA district code (FK to districts dimension): "
                    "3-digit zero-padded standard code or 7-digit "
                    "state-charter code. NULL on state-level aggregate rows."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0103",
                "description": (
                    "4-digit zero-padded GOSA school code (FK to schools "
                    "dimension as the composite (district_code, school_code) "
                    "key). NULL on district- and state-level aggregate rows. "
                    "The 2019 source file ships codes unpadded; zfill(4) "
                    "restores the dimension's 4-char format."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "all",
                "description": (
                    "Canonical demographic subgroup (FK to the global "
                    "demographics dimension). 'all' for every 2004-2007 row "
                    "(no demographic breakdown published in those years); "
                    "2011-2024 rows carry the full subgroup set (race, "
                    "gender, economic status, special populations). This "
                    "topic uses the SPLIT race convention — separate `asian` "
                    "and `pacific_islander` rows, never the combined "
                    "rollup. NON-ADDITIVE MILITARY KEYS: `active_duty` "
                    "(dependents of currently-serving members) is a SUBSET "
                    "of `military_connected` (any DoD-connected family); "
                    "both appear from 2022 on — do not sum them across the "
                    "demographic axis."
                ),
                "short_description": (
                    "Demographic subgroup the row reports; 'all' for every "
                    "2004-2007 row and for the overall figure thereafter."
                ),
            },
            {
                "name": "subject",
                "type": "string",
                "example": "mathematics",
                "validValues": sorted(set(SUBJECT_MAP.values())),
                "description": (
                    "GAA content area being assessed — one of the four GAA "
                    "subjects (english_language_arts, mathematics, science, "
                    "social_studies). NULL for 2004-2007 rows, which report "
                    "only overall participation with no subject detail."
                ),
                "short_description": (
                    "Content area assessed (ELA, math, science, or social "
                    "studies); NULL for 2004-2007 participation-only rows."
                ),
            },
            {
                "name": "num_enrolled_ayp_grades",
                "type": "int64",
                "unit": "count",
                "example": 540,
                "description": (
                    "Total enrollment in AYP-applicable grades (grades 1-8 "
                    "and 11). Published ONLY for 2004-2007; NULL for every "
                    "2011-2024 row (GOSA stopped publishing the column). "
                    "Note: num_tested can legitimately exceed this value "
                    "(e.g., DeKalb school 644:3058 in 2004-2005) because "
                    "the GAA is also administered in non-AYP grades while "
                    "this denominator counts AYP grades only."
                ),
            },
            {
                "name": "num_tested",
                "type": "int64",
                "unit": "count",
                "metric_component": "denominator",
                "example": 22,
                "description": (
                    "Count of students taking the GAA in this cell. Always "
                    "reported 2004(*)-2023; in 2024 GOSA suppressed it (TFS) "
                    "on ~84%% of rows while still publishing the level "
                    "percentages, so most 2024 rows have NULL num_tested "
                    "with non-NULL pct_*_learner values. (*) A handful of "
                    "2004 rows have NULL metrics as published."
                ),
            },
            {
                "name": "num_beginning_learner",
                "type": "int64",
                "unit": "count",
                "example": 3,
                "description": (
                    "Count scoring at the lowest achievement tier. Unifies "
                    "the era namings LIMITED (2011-2018, 2022-2023), Level1 "
                    "(2019), and BEGIN (2024). NULL for 2004-2007 (no "
                    "achievement detail) and for suppressed cells."
                ),
            },
            {
                "name": "num_developing_learner",
                "type": "int64",
                "unit": "count",
                "example": 8,
                "description": (
                    "Count scoring at the second tier (PARTIAL / Level2 / "
                    "DEVELOPING across eras). NULL for 2004-2007 and for "
                    "suppressed cells."
                ),
            },
            {
                "name": "num_proficient_learner",
                "type": "int64",
                "unit": "count",
                "example": 11,
                "description": (
                    "Count scoring at the third tier (ADEQUATE / Level3 / "
                    "PROFICIENT across eras). NULL for 2004-2007 and for "
                    "suppressed cells."
                ),
            },
            {
                "name": "num_distinguished_learner",
                "type": "int64",
                "unit": "count",
                "example": 4,
                "description": (
                    "Count scoring at the highest (4th) achievement tier "
                    "(Level4 / THOROUGH / DISTINGUISHED across eras). NULL "
                    "for 2004-2007 AND for all of 2011-2018: the GAA used "
                    "3-tier scoring then and the tier did not exist (the "
                    "source's reserved THUROUGH column, always 0/empty, is "
                    "dropped rather than served as a phantom all-zero "
                    "metric). Also NULL for suppressed cells."
                ),
            },
            {
                "name": "pct_beginning_learner",
                "type": "float64",
                "unit": "proportion",
                "example": 0.095,
                "description": (
                    "Share of tested students at the lowest tier, 0-1 scale "
                    "(bronze publishes 0-100; divided by 100). NULL for "
                    "2004-2007 and suppressed cells."
                ),
            },
            {
                "name": "pct_developing_learner",
                "type": "float64",
                "unit": "proportion",
                "example": 0.25,
                "description": (
                    "Share at the second tier, 0-1 scale. NULL for "
                    "2004-2007 and suppressed cells."
                ),
            },
            {
                "name": "pct_proficient_learner",
                "type": "float64",
                "unit": "proportion",
                "example": 0.381,
                "description": (
                    "Share at the third tier, 0-1 scale. NULL for 2004-2007 "
                    "and suppressed cells."
                ),
            },
            {
                "name": "pct_distinguished_learner",
                "type": "float64",
                "unit": "proportion",
                "example": 0.524,
                "description": (
                    "Share at the highest tier, 0-1 scale. NULL for "
                    "2004-2007, for ALL of 2011-2018 (3-tier era — tier did "
                    "not exist), and for suppressed cells."
                ),
            },
            {
                "name": "pct_developing_learner_or_above",
                "type": "float64",
                "unit": "proportion",
                "example": 0.905,
                "description": (
                    "Derived cumulative share at Developing or higher, 0-1 "
                    "scale. For 4-tier years (2019+): developing + "
                    "proficient + distinguished (NULL when any summand is "
                    "suppressed). For the 3-tier 2011-2018 era the absent "
                    "distinguished tier is omitted from the sum (developing "
                    "+ proficient), so those years ARE populated. "
                    "Publisher-rounded summands can overshoot 1.0 by up to "
                    "0.001; overshoot within 0.005 is capped to 1.0. NULL "
                    "for 2004-2007."
                ),
            },
            {
                "name": "pct_proficient_learner_or_above",
                "type": "float64",
                "unit": "proportion",
                "key_metric": True,
                "example": 0.655,
                "short_description": (
                    "Share of tested students scoring Proficient Learner or "
                    "higher, on a 0-1 scale (the headline GAA proficiency "
                    "rate)."
                ),
                "description": (
                    "Derived cumulative share at Proficient or higher, 0-1 "
                    "scale. For 4-tier years (2019+): proficient + "
                    "distinguished; for 3-tier 2011-2018 it equals "
                    "pct_proficient_learner. Rounding overshoot within "
                    "0.005 is capped to 1.0. NULL for 2004-2007 and when a "
                    "summand is suppressed."
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
                "Two measure regimes share one schema. 2004-2007 rows "
                "populate only num_enrolled_ayp_grades and num_tested with "
                "demographic='all' and subject NULL; 2011-2024 rows "
                "populate subject, the demographic subgroups, and the "
                "achievement-level metrics with num_enrolled_ayp_grades NULL."
            ),
            (
                "2011-2018 used 3-tier GAA scoring — the distinguished "
                "metrics are NULL (never 0) for those years, and the "
                "derived _or_above cumulatives omit the absent tier rather "
                "than NULL-propagating through it."
            ),
            (
                "Suppression: 2011-2019 suppress with empty cells; "
                "2022-2024 use the 'TFS' marker (mapped to NULL). In 2024 "
                "suppressed rows are emitted rather than omitted (~64K rows "
                "vs ~15K), num_tested itself is suppressed on ~84%% of rows, "
                "and the beginning/developing/proficient percentages are "
                "never suppressed."
            ),
            (
                "The 'Homeless' subgroup's level percentages sum to ~50%% "
                "instead of ~100%% (source denominator inconsistency vs the "
                "published counts): a few district/state rows in 2022 (50) "
                "and 2023 (77), and systematically in 2024 — ALL 1,135 "
                "Homeless rows at every detail level (4 state, 300 "
                "district, 831 school) publish shares summing to "
                "0.499-0.501. Preserved as published; partition-sum "
                "expectations only hold 2011-2019."
            ),
            (
                "Military demographic keys are NON-ADDITIVE: active_duty is "
                "a subset of military_connected; both appear from 2022 on. "
                "Do not sum them across the demographic axis."
            ),
            (
                "2004 source repairs: one fully-null trailing row, 136 "
                "exact-duplicate rows, and one all-null placeholder twin "
                "(647:3058) were dropped — all recorded in the transform "
                "manifest."
            ),
            (
                "num_tested can exceed num_enrolled_ayp_grades (644:3058 in "
                "2004 and 2005): the GAA is administered in non-AYP grades "
                "while the enrollment denominator counts grades 1-8 and 11 "
                "only. Preserved as published."
            ),
            (
                "The 2005 and 2006 bronze files carry .csv extensions but "
                "are OLE2 Excel binaries; the shared reader detects the "
                "real format via magic bytes."
            ),
            (
                "Files are partitioned by year and split by detail level: "
                "schools.parquet, districts.parquet, states.parquet."
            ),
        ],
        quality_checks=[
            {
                "name": "participation_era_row_shape",
                "description": (
                    "2004-2007 rows are participation-only: demographic is "
                    "'all', subject is NULL, and every achievement-level "
                    "metric (counts, shares, cumulatives) is NULL."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year <= 2007 AND ("
                    "demographic != 'all' OR subject IS NOT NULL "
                    "OR num_beginning_learner IS NOT NULL "
                    "OR num_developing_learner IS NOT NULL "
                    "OR num_proficient_learner IS NOT NULL "
                    "OR num_distinguished_learner IS NOT NULL "
                    "OR pct_beginning_learner IS NOT NULL "
                    "OR pct_developing_learner IS NOT NULL "
                    "OR pct_proficient_learner IS NOT NULL "
                    "OR pct_distinguished_learner IS NOT NULL "
                    "OR pct_developing_learner_or_above IS NOT NULL "
                    "OR pct_proficient_learner_or_above IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "achievement_era_row_shape",
                "description": (
                    "2011-2024 rows always carry a subject and never carry "
                    "the AYP-grades enrollment (the source stopped "
                    "publishing it after 2007)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year >= 2011 AND "
                    "(subject IS NULL OR num_enrolled_ayp_grades IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "era3_distinguished_tier_absent",
                "description": (
                    "2011-2018 used 3-tier scoring: the distinguished count "
                    "and share are NULL for every row in those years "
                    "(verified — the source's reserved 4th-tier column is "
                    "only ever 0/empty)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year BETWEEN 2011 "
                    "AND 2018 AND (num_distinguished_learner IS NOT NULL "
                    "OR pct_distinguished_learner IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "num_tested_always_reported_2011_2023",
                "description": (
                    "NUM_TESTED_CNT is never suppressed in the 2011-2023 "
                    "source files (verified: zero nulls); only 2024 "
                    "suppresses it."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year BETWEEN 2011 "
                    "AND 2023 AND num_tested IS NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "level_counts_sum_le_num_tested",
                "description": (
                    "The reported achievement-level counts (NULLs treated "
                    "as 0) never sum past num_tested (verified across all "
                    "source years; 2022+ can undershoot because some tested "
                    "students receive no band)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE num_tested IS NOT "
                    "NULL AND (COALESCE(num_beginning_learner, 0) "
                    "+ COALESCE(num_developing_learner, 0) "
                    "+ COALESCE(num_proficient_learner, 0) "
                    "+ COALESCE(num_distinguished_learner, 0)) > num_tested"
                ),
                "mustBe": 0,
            },
            {
                "name": "no_single_level_count_exceeds_num_tested",
                "description": (
                    "No individual achievement-level count exceeds the "
                    "number of students tested in the same cell."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE num_tested IS NOT "
                    "NULL AND (num_beginning_learner > num_tested "
                    "OR num_developing_learner > num_tested "
                    "OR num_proficient_learner > num_tested "
                    "OR num_distinguished_learner > num_tested)"
                ),
                "mustBe": 0,
            },
            {
                "name": "level_counts_sum_equals_num_tested_2011_2019",
                "description": (
                    "In 2011-2019, where the active-tier counts are all "
                    "reported they sum EXACTLY to num_tested (verified, "
                    "zero exceptions; the active tiers are three for "
                    "2011-2018 and four for 2019). 2022+ relaxes to <= "
                    "because some tested students receive no band."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE num_tested IS NOT "
                    "NULL AND ((year BETWEEN 2011 AND 2018 "
                    "AND num_beginning_learner IS NOT NULL "
                    "AND num_developing_learner IS NOT NULL "
                    "AND num_proficient_learner IS NOT NULL "
                    "AND num_beginning_learner + num_developing_learner "
                    "+ num_proficient_learner != num_tested) "
                    "OR (year = 2019 "
                    "AND num_beginning_learner IS NOT NULL "
                    "AND num_developing_learner IS NOT NULL "
                    "AND num_proficient_learner IS NOT NULL "
                    "AND num_distinguished_learner IS NOT NULL "
                    "AND num_beginning_learner + num_developing_learner "
                    "+ num_proficient_learner + num_distinguished_learner "
                    "!= num_tested))"
                ),
                "mustBe": 0,
            },
            {
                "name": "count_pct_co_null_2011_2019",
                "description": (
                    "In 2011-2019, suppression is all-or-nothing per tier: "
                    "a level count is NULL exactly when its share is NULL "
                    "(verified per row, zero mismatches). 2022+ breaks this "
                    "at the source (e.g., 2024 publishes shares without "
                    "counts), so the rule is scoped."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year BETWEEN 2011 "
                    "AND 2019 AND ("
                    "(num_beginning_learner IS NULL) "
                    "!= (pct_beginning_learner IS NULL) "
                    "OR (num_developing_learner IS NULL) "
                    "!= (pct_developing_learner IS NULL) "
                    "OR (num_proficient_learner IS NULL) "
                    "!= (pct_proficient_learner IS NULL) "
                    "OR (year = 2019 AND (num_distinguished_learner IS NULL) "
                    "!= (pct_distinguished_learner IS NULL)))"
                ),
                "mustBe": 0,
            },
            {
                "name": "pct_levels_partition_2011_2019",
                "description": (
                    "In 2011-2019, where all active-tier shares are "
                    "reported they partition the tested population: their "
                    "sum is 1.0 within publisher rounding (bronze observed "
                    "99.9-100.2 on the 0-100 scale). Not asserted for 2022+ "
                    "where the source's Homeless-subgroup denominator "
                    "inconsistency allows large undershoot (sums ~0.5; "
                    "systematic across all 1,135 Homeless rows in 2024)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "((year BETWEEN 2011 AND 2018 "
                    "AND pct_beginning_learner IS NOT NULL "
                    "AND pct_developing_learner IS NOT NULL "
                    "AND pct_proficient_learner IS NOT NULL "
                    "AND ABS(pct_beginning_learner + pct_developing_learner "
                    "+ pct_proficient_learner - 1.0) > 0.0025) "
                    "OR (year = 2019 "
                    "AND pct_beginning_learner IS NOT NULL "
                    "AND pct_developing_learner IS NOT NULL "
                    "AND pct_proficient_learner IS NOT NULL "
                    "AND pct_distinguished_learner IS NOT NULL "
                    "AND ABS(pct_beginning_learner + pct_developing_learner "
                    "+ pct_proficient_learner + pct_distinguished_learner "
                    "- 1.0) > 0.0025))"
                ),
                "mustBe": 0,
            },
            {
                "name": "pct_levels_sum_at_most_one_2022_on",
                "description": (
                    "From 2022 on, where all four shares are reported their "
                    "sum may exceed 1.0 only by publisher rounding (bronze "
                    "max 100.2 on the 0-100 scale). The sum CAN fall well "
                    "below 1.0 — the source's Homeless-subgroup rows sum to "
                    "~0.5 (50 rows in 2022, 77 in 2023, and ALL 1,135 "
                    "Homeless rows at every detail level in 2024) — so no "
                    "lower bound is asserted."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year >= 2022 "
                    "AND pct_beginning_learner IS NOT NULL "
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
                "name": "developing_or_above_reconciles_4tier",
                "description": (
                    "For 4-tier years (2019+), pct_developing_learner_or_"
                    "above equals developing + proficient + distinguished "
                    "within the 0.005 rounding-cap tolerance and is non-NULL "
                    "whenever all three summands are non-NULL."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year >= 2019 "
                    "AND pct_developing_learner IS NOT NULL "
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
                "name": "proficient_or_above_reconciles_4tier",
                "description": (
                    "For 4-tier years (2019+), pct_proficient_learner_or_"
                    "above equals proficient + distinguished within the "
                    "0.005 rounding-cap tolerance and is non-NULL whenever "
                    "both summands are non-NULL."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year >= 2019 "
                    "AND pct_proficient_learner IS NOT NULL "
                    "AND pct_distinguished_learner IS NOT NULL "
                    "AND (pct_proficient_learner_or_above IS NULL "
                    "OR ABS(pct_proficient_learner_or_above "
                    "- (pct_proficient_learner + pct_distinguished_learner)) "
                    "> 0.0051)"
                ),
                "mustBe": 0,
            },
            {
                "name": "or_above_reconciles_3tier_era",
                "description": (
                    "For the 3-tier 2011-2018 era the cumulatives omit the "
                    "absent distinguished tier: developing_or_above = "
                    "developing + proficient and proficient_or_above = "
                    "proficient (within the 0.005 rounding-cap tolerance), "
                    "non-NULL whenever the summands are non-NULL."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year BETWEEN 2011 "
                    "AND 2018 AND ((pct_developing_learner IS NOT NULL "
                    "AND pct_proficient_learner IS NOT NULL "
                    "AND (pct_developing_learner_or_above IS NULL "
                    "OR ABS(pct_developing_learner_or_above "
                    "- (pct_developing_learner + pct_proficient_learner)) "
                    "> 0.0051)) "
                    "OR (pct_proficient_learner IS NOT NULL "
                    "AND (pct_proficient_learner_or_above IS NULL "
                    "OR ABS(pct_proficient_learner_or_above "
                    "- pct_proficient_learner) > 0.0051)))"
                ),
                "mustBe": 0,
            },
            {
                "name": "pcts_published_when_counts_suppressed_2024",
                "description": (
                    "The 2024 source publishes the beginning, developing, "
                    "and proficient shares on EVERY row, even fully "
                    "suppressed ones (verified: zero NULLs across 63,689 "
                    "rows) — the property that makes 2024's suppressed "
                    "cells still carry usable signal. Only the "
                    "distinguished share is occasionally suppressed."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year = 2024 "
                    "AND (pct_beginning_learner IS NULL "
                    "OR pct_developing_learner IS NULL "
                    "OR pct_proficient_learner IS NULL)"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
