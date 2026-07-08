"""Transform certified_personnel to gold.

Source: Governor's Office of Student Achievement (GOSA) — Certified Personnel
report, compiled from local school systems' Certified/Classified Personnel
Information (CPI) submissions. 14 CSV files, one per school year 2010-11
through 2023-24. For every Georgia public school, school district, and the
state as a whole, the source publishes a complete long/tidy grid of 27
measurements (`DATA_CATEGORY` x `DATA_SUB_CATEGORY`) per employee group
(`EMPLOYEE_TYPE`: Administrators, PK-12 Teachers, Support Personnel), with
the numeric value in `MEASURE`. Gold keeps the long shape: one row per
(year, geography, employee_type, measure_category, measure_subcategory).

Design decisions (from bronze-data-structure.md + data-cleaning-standards):

- **Two near-identical eras, one pipeline, detected by column signature.**
  Era 1 (2023-2024) adds `#RPT_NAME` (verified constant
  `CERTIFIED_PERSONNEL`, asserted then dropped) and `GRADES_SERVED_DESC`
  (school metadata -> dimensions, dropped). Era 2 (2011-2022) is the bare
  9-column schema. All shared columns have identical semantics, so one
  transform function serves both eras.
- **Detail level from the `ALL` sentinels**: `SCHOOL_DSTRCT_CD == 'ALL'` ->
  state row; else `INSTN_NUMBER == 'ALL'` -> district row; else school row.
  Verified: no mixed/invalid combinations in any file (a state row always
  has both sentinels). Sentinels become NULL geography keys BEFORE zfill —
  `"ALL".str.zfill(4)` would otherwise mint a bogus `"0ALL"` code.
- **`measure_value` carries NO `unit` marker (sanctioned §4a exemption).**
  Its semantics depend on (measure_category, measure_subcategory): an integer
  headcount for 22 labels, a fractional FTE-style position count for
  positions/number, US dollars for the two salary averages, days for
  average_contract_days, and years for years_experience/average. The v1
  contract took the same exemption (no `unit` custom property, no derived
  range check on measure_value). To keep range semantics ENFORCEABLE
  despite the exemption, per-label range facts verified across all 14
  bronze years are authored as quality checks instead: global
  non-negativity (0 violations in 3,120,633 bronze values), integrality of
  the 22 headcount labels (0 fractional values), years_experience/average
  within [0, 60] (observed [0, 50]), and average_contract_days within
  [0, 366] (observed [30, 260]). Salaries get no upper cap — there is no
  physically-grounded bound (observed max: 250,831.94 annual / 2,764.56
  daily) — so non-negativity is their only range invariant.
- **`Race/Ethnicity` / `Asian` -> `asian_pacific_islander` (§5b).** The
  source publishes only 6 staff race buckets (Asian, Black, Hispanic,
  Multiracial, Native American, White) and NO Pacific Islander label in any
  era. Math test at the state rows of every year: the race-bucket sum
  equals the gender-bucket sum (the same certified-personnel population) to
  within ~0.03%, with the tiny residuals in BOTH directions (e.g. 2024
  teachers: race 123,877 vs gender 123,848) — inconsistent with a dropped
  ~0.1-0.2% NHPI population, consistent with the pre-1997 OMB combined
  bucket plus small unreported-attribute noise. Bare "Asian" is therefore
  the combined Asian/Pacific Islander bucket. certified_personnel is on
  §5b's known-combined list, and the v1 contract enum agrees. NOTE: race
  here is a measure_subcategory describing STAFF, not a `demographic` column —
  gender/race rows are measure families, so the topic has no demographic
  axis and does not join the demographics dimension.
- **No suppression in this source (all 14 years).** Every MEASURE value in
  every file parses to a valid number (no TFS/*/N/A); zero counts are
  published as real `0`. `suppressed_to_null=False` is passed to the
  contract emitter so NULL is not documented as "suppressed", and the cast
  keeps `strict=False` purely defensively.
- **No §4b masks.** No impossible values exist: no negatives, no
  out-of-scale values anywhere. Two extreme-but-conceivable findings are
  preserved + documented instead: (1) the 2016-17 `certified_personnel`
  family (professional/provisional counts) is uniformly depressed at EVERY
  level — state 2,689 professional PK-12 teachers vs ~110k in neighboring
  years, but internally consistent (district sum 2,690, school sum 2,748) —
  a source-wide scope/definition glitch for that family-year, not a broken
  aggregate; (2) average_annual_salary of 0.0 occurs for small cells where
  an entity reports positions without salary data. Both are physically
  possible values and are served as published.
- **Dedup is purely defensive.** The natural key (year, geography,
  employee_type, measure_category, measure_subcategory) is verified unique in
  every bronze file (0 duplicates), files do not overlap (one school year
  each), and zero-padding creates no collisions (40,988 entity-year combos
  before and after zfill). The collision guard runs first;
  `sort_col="measure_value"` would prefer a row with a reported value on
  any hypothetical future republication.
- **Quality checks (§15b)**, all verified against bronze across all 14
  years: family<->label containment (each of the 27 labels belongs to
  exactly one family); measure_value non-negative; headcount labels
  integral; the two physically-bounded averages within range; exactly 81
  state rows per year (27 pairs x 3 employee types); and the complete-grid
  structural fact — every (year, geography, employee_type) cell carries
  exactly 27 rows with 27 distinct labels.

Structure-doc corrections made during authoring (bronze-data-structure.md
amended, with evidence):

1. `Other *` is a CERTIFICATE LEVEL label (a fifth certificate type), not a
   Race/Ethnicity label — verified in all 14 files (the pair
   ('Certificate Level', 'Other *') is its only occurrence).
2. `SCHOOL_DSTRCT_CD` is not only 3-digit `601`-`795`: 7-digit charter
   district codes appear from the 2012 file onward.

(Re-verified after data review: `INSTN_NUMBER` IS uniformly 4-character in
all 14 files — the only 3-character value is the `ALL` sentinel, which an
earlier length scan conflated with real codes — so zfill(4) is a defensive
no-op. The `ALL` -> NULL translation must still happen BEFORE zfill, which
would otherwise mint a bogus `0ALL` code.)

Cross-level counting caveat (verified, faithful bronze passthrough): in
1,811 district cells — 100%% confined to personnel/part_time — the district
headcount is SMALLER than a single school's count in that district (e.g.
2023 district 669 support part_time: district 39, one school 41, school sum
172). Part-time staff serving multiple schools are counted once per school
assignment at school level but deduplicated at the district level, so
school rows must never be summed to rebuild district or state headcounts.
Documented in the contract limitations + README.

Judgment calls (non-interactive run):

1. Long gold shape kept (matches v1 and the bronze grain) rather than the
   structure doc's "alternative" 81-metric-column pivot — preserves bronze
   granularity, keeps the API filterable on the measure axes.
2. measure_value left unit-less with authored per-label range checks (see
   above) rather than splitting into per-unit metric columns.
3. 2016-17 certified_personnel family depression preserved per §4b
   (extreme-but-conceivable, internally consistent at all levels) and
   documented in the contract limitations + measure_value description.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

from src.utils.metadata import write_data_dictionary
from src.utils.readers import (
    extract_year_from_filename,
    list_bronze_files,
    parse_school_year,
    read_bronze_file,
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

TOPIC = "certified_personnel"
BRONZE_DIR = Path("data/bronze/education/gosa/certified_personnel")
GOLD_DIR = Path("data/gold/education/certified_personnel")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# EMPLOYEE_TYPE -> employee_type (snake_case per §10).
EMPLOYEE_TYPE_MAP: dict[str, str] = {
    "Administrators": "administrators",
    "PK-12 Teachers": "pk_12_teachers",
    "Support Personnel": "support_personnel",
}

# DATA_CATEGORY -> measure_category (snake_case per §10).
MEASURE_FAMILY_MAP: dict[str, str] = {
    "Certificate Level": "certificate_level",
    "Certified Personnel": "certified_personnel",
    "Gender": "gender",
    "Personnel": "personnel",
    "Positions": "positions",
    "Race/Ethnicity": "race_ethnicity",
    "Years Experience": "years_experience",
}

# DATA_SUB_CATEGORY -> measure_subcategory (snake_case per §10). Notes:
# - "Other *" (a Certificate Level value; the asterisk flags a source
#   footnote) -> "other".
# - "Asian" -> "asian_pacific_islander": the 6-bucket staff race scheme is
#   the pre-1997 OMB combined bucket (§5b math test in the module
#   docstring); never map to bare "asian" for this source.
MEASURE_LABEL_MAP: dict[str, str] = {
    "4 Yr Bachelor's": "4_yr_bachelors",
    "5 Yr Master's": "5_yr_masters",
    "6 Yr Specialist's": "6_yr_specialists",
    "7 Yr Doctoral": "7_yr_doctoral",
    "Other *": "other",
    "Professional": "professional",
    "Provisional": "provisional",
    "Female": "female",
    "Male": "male",
    "Full-time": "full_time",
    "Part-time": "part_time",
    "Number": "number",
    "Average Annual Salary": "average_annual_salary",
    "Average Daily Salary": "average_daily_salary",
    "Average Contract Days": "average_contract_days",
    "Asian": "asian_pacific_islander",
    "Black": "black",
    "Hispanic": "hispanic",
    "Multiracial": "multiracial",
    "Native American": "native_american",
    "White": "white",
    "< 1": "less_than_1",
    "1-10": "1_to_10",
    "11-20": "11_to_20",
    "21-30": "21_to_30",
    "> 30": "greater_than_30",
    "Average": "average",
}

# The 27 valid (measure_category, measure_subcategory) pairs — measure_category is
# functionally determined by measure_subcategory. Verified identical in all 14
# bronze files; authored as a containment quality check.
VALID_FAMILY_LABEL_PAIRS: dict[str, list[str]] = {
    "certificate_level": [
        "4_yr_bachelors",
        "5_yr_masters",
        "6_yr_specialists",
        "7_yr_doctoral",
        "other",
    ],
    "certified_personnel": ["professional", "provisional"],
    "gender": ["female", "male"],
    "personnel": ["full_time", "part_time"],
    "positions": [
        "number",
        "average_annual_salary",
        "average_daily_salary",
        "average_contract_days",
    ],
    "race_ethnicity": [
        "asian_pacific_islander",
        "black",
        "hispanic",
        "multiracial",
        "native_american",
        "white",
    ],
    "years_experience": [
        "less_than_1",
        "1_to_10",
        "11_to_20",
        "21_to_30",
        "greater_than_30",
        "average",
    ],
}

# measure_subcategory values whose measure_value is legitimately fractional:
# the FTE-style position count, the three positions averages, and the mean
# years of experience. Every OTHER label is an integer headcount (verified:
# 0 fractional values across all 14 bronze years).
FRACTIONAL_MEASURE_LABELS: list[str] = [
    "number",
    "average_annual_salary",
    "average_daily_salary",
    "average_contract_days",
    "average",
]

# Era-detection signatures (column presence), most specific first: Era 1
# adds #RPT_NAME + GRADES_SERVED_DESC on top of the common 9-column schema.
_COMMON_COLUMNS = [
    "LONG_SCHOOL_YEAR",
    "SCHOOL_DSTRCT_CD",
    "SCHOOL_DSTRCT_NM",
    "INSTN_NUMBER",
    "INSTN_NAME",
    "DATA_CATEGORY",
    "DATA_SUB_CATEGORY",
    "EMPLOYEE_TYPE",
    "MEASURE",
]
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_1_2023_2024_rpt_name": ["#RPT_NAME", "GRADES_SERVED_DESC", *_COMMON_COLUMNS],
    "era_2_2011_2022_base": _COMMON_COLUMNS,
}

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export splitting, then dropped by export_to_parquet().
# No `demographic` column — gender/race are measure families of STAFF.
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "employee_type",
    "measure_category",
    "measure_subcategory",
    "measure_value",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "employee_type": pl.Utf8,
    "measure_category": pl.Utf8,
    "measure_subcategory": pl.Utf8,
    "measure_value": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = ["measure_value"]

NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "employee_type",
    "measure_category",
    "measure_subcategory",
    "detail_level",
]

# Bronze aggregate-row sentinel in both geography code columns.
_ALL_SENTINEL = "ALL"


# =============================================================================
# Per-file transform
# =============================================================================


def _transform_era(
    df: pl.DataFrame,
    year: int,
    era: str,
    manifest: TransformManifest,
    label: str,
) -> pl.DataFrame:
    """Transform one bronze file (either era) to the gold shape.

    The eras share every semantically meaningful column; Era 1's two extras
    are an asserted constant (#RPT_NAME) and school metadata
    (GRADES_SERVED_DESC) that belongs in the schools dimension, not the
    fact table.
    """
    # Era 1's report-name column is a verified constant; a new value would
    # mean GOSA repurposed the file — fail loudly, never passthrough.
    if era == "era_1_2023_2024_rpt_name":
        observed = set(df["#RPT_NAME"].unique().to_list())
        if observed != {"CERTIFIED_PERSONNEL"}:
            raise ValueError(
                f"{label}: expected #RPT_NAME == 'CERTIFIED_PERSONNEL' only, "
                f"saw {sorted(observed)}"
            )

    # One batched with_columns: detail level from the ALL sentinels (state
    # rows carry ALL in the district column; district aggregates carry ALL
    # only in the school column — verified: no mixed combinations), plus
    # the three categorical recodes. The "99999999" sentinel default makes
    # any new bronze value fail manifest.write() instead of passing through.
    df = df.with_columns(
        pl.when(pl.col("SCHOOL_DSTRCT_CD") == _ALL_SENTINEL)
        .then(pl.lit("state"))
        .when(pl.col("INSTN_NUMBER") == _ALL_SENTINEL)
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .alias("detail_level"),
        pl.col("EMPLOYEE_TYPE")
        .replace_strict(EMPLOYEE_TYPE_MAP, default="99999999")
        .alias("employee_type"),
        pl.col("DATA_CATEGORY")
        .replace_strict(MEASURE_FAMILY_MAP, default="99999999")
        .alias("measure_category"),
        pl.col("DATA_SUB_CATEGORY")
        .replace_strict(MEASURE_LABEL_MAP, default="99999999")
        .alias("measure_subcategory"),
    )
    manifest.record_categorical(
        column="employee_type",
        map_dict=EMPLOYEE_TYPE_MAP,
        bronze_series=df["EMPLOYEE_TYPE"],
        gold_series=df["employee_type"],
    )
    manifest.record_categorical(
        column="measure_category",
        map_dict=MEASURE_FAMILY_MAP,
        bronze_series=df["DATA_CATEGORY"],
        gold_series=df["measure_category"],
    )
    manifest.record_categorical(
        column="measure_subcategory",
        map_dict=MEASURE_LABEL_MAP,
        bronze_series=df["DATA_SUB_CATEGORY"],
        gold_series=df["measure_subcategory"],
    )

    return df.select(
        pl.lit(year).cast(pl.Int32).alias("year"),
        # Sentinels -> NULL BEFORE zfill: zfill(4) would turn "ALL" into a
        # bogus "0ALL" code. zfill preserves 7-digit charter district codes
        # and is otherwise a defensive no-op (district codes are 3-char and
        # school codes uniformly 4-char in every file).
        pl.when(pl.col("SCHOOL_DSTRCT_CD") == _ALL_SENTINEL)
        .then(None)
        .otherwise(pl.col("SCHOOL_DSTRCT_CD").str.zfill(3))
        .alias("district_code"),
        pl.when(pl.col("INSTN_NUMBER") == _ALL_SENTINEL)
        .then(None)
        .otherwise(pl.col("INSTN_NUMBER").str.zfill(4))
        .alias("school_code"),
        pl.col("employee_type"),
        pl.col("measure_category"),
        pl.col("measure_subcategory"),
        # No suppression markers exist in any year (verified), so the
        # strict=False cast is purely defensive against future markers.
        pl.col("MEASURE").cast(pl.Float64, strict=False).alias("measure_value"),
        pl.col("detail_level"),
    )


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read one bronze CSV, detect its era, and transform it."""
    # All-string read: preserves zero-padded INSTN_NUMBER, the ALL
    # sentinels, and 7-digit charter codes that schema inference would
    # mis-type or strip.
    df, loss = read_bronze_file(path, infer_schema_length=0, return_loss=True)

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{path.name}: no era signature matched {df.columns}")

    # LONG_SCHOOL_YEAR is the authoritative year source (ending calendar
    # year); each file carries exactly one school year — assert it, since a
    # multi-year file would need per-row year derivation instead.
    school_years = df["LONG_SCHOOL_YEAR"].drop_nulls().unique().to_list()
    if len(school_years) != 1:
        raise ValueError(
            f"{path.name}: expected a single LONG_SCHOOL_YEAR, saw {school_years}"
        )
    year = parse_school_year(school_years[0])
    filename_year = extract_year_from_filename(path.name)
    if filename_year is not None and filename_year != year:
        logger.warning(
            "%s: filename year %d != LONG_SCHOOL_YEAR-derived %d — using the column",
            path.name,
            filename_year,
            year,
        )

    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])
    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)
    if df.height == 0:
        logger.warning("%s: bronze file is empty, skipping", path.name)
        return None

    label = f"{era} {path.name}"
    logger.info("Processing %s (year=%d, rows=%d)", label, year, df.height)
    return _transform_era(df, year, era, manifest, label)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for this topic."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform each bronze file (read-loss accounted per file).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR, extensions=[".csv"]):
        result = transform_file(path, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize dtypes across eras and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)
    logger.info("Combined %d rows across %d files", combined.height, len(all_dfs))

    # 3. Collision guard BEFORE dedup: duplicate natural keys with divergent
    # metrics would mean zfill merged two distinct entities or a file
    # republished a key — raise so it gets investigated, never let dedup
    # pick a silent winner.
    assert_no_natural_key_collisions(
        combined,
        natural_keys=NATURAL_KEYS,
        metric_cols=METRIC_COLUMNS,
        label=TOPIC,
    )
    # Tie-break: bronze keys are verified unique within every file and the
    # 14 files cover disjoint school years, so dedup is purely defensive.
    # sort_col="measure_value" prefers a row with a reported value on any
    # hypothetical future republication.
    pre_dedup = dict(combined.group_by("year").len().iter_rows())
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=[
            "year",
            "district_code",
            "school_code",
            "employee_type",
            "measure_category",
            "measure_subcategory",
        ],
        district_keys=[
            "year",
            "district_code",
            "employee_type",
            "measure_category",
            "measure_subcategory",
        ],
        state_keys=["year", "employee_type", "measure_category", "measure_subcategory"],
        sort_col="measure_value",
    )
    post_dedup = dict(combined.group_by("year").len().iter_rows())
    for year in sorted(pre_dedup):
        removed = pre_dedup[year] - post_dedup.get(year, 0)
        if removed > 0:
            manifest.record_filtered(year, removed, "duplicate_rows_deduped")

    # 4. Geography nulling — the sentinel translation already left state
    # rows (NULL, NULL) and district rows school_code=NULL, but the shared
    # rule source keeps transform and validator in lockstep. No §4b masks:
    # no impossible values exist in any year (the 2016-17
    # certified_personnel family depression is extreme-but-conceivable and
    # preserved — see module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. measure_value has zero NULLs in every year (no
    # suppression in this source), so any spike is a regression.
    spikes = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spikes.status == "warning":
        logger.warning("Unexpected NULL-rate spikes: %s", spikes.details)
    validate_output(combined, required_non_null=["year", "detail_level"])

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


def _quality_checks() -> list[dict]:
    """Cross-column / structural invariants (§15b), verified against bronze.

    Every check below was tested against all 14 bronze files (3,120,633
    rows) before authoring; observed margins are in the descriptions.
    """
    valid_pairs = ", ".join(
        f"('{family}', '{label}')"
        for family, labels in VALID_FAMILY_LABEL_PAIRS.items()
        for label in labels
    )
    fractional = ", ".join(f"'{v}'" for v in FRACTIONAL_MEASURE_LABELS)
    return [
        {
            "name": "measure_category_subcategory_valid_pair",
            "description": (
                "measure_category is functionally determined by measure_subcategory: "
                "every (measure_category, measure_subcategory) combination is one of "
                "the 27 valid pairs published by GOSA (verified identical in "
                "all 14 bronze years)."
            ),
            "dimension": "consistency",
            "query": (
                "SELECT COUNT(*) FROM {object} "
                f"WHERE (measure_category, measure_subcategory) NOT IN ({valid_pairs})"
            ),
            "mustBe": 0,
        },
        {
            "name": "measure_value_non_negative",
            "description": (
                "Every measurement in this dataset (headcounts, FTE position "
                "counts, salary/contract-day/experience averages) is "
                "non-negative. Replaces the unit-derived range check that "
                "the unit-less measure_value column would otherwise lack; "
                "verified with zero violations across all 3,120,633 bronze "
                "values."
            ),
            "dimension": "accuracy",
            "query": (
                "SELECT COUNT(*) FROM {object} "
                "WHERE measure_value IS NOT NULL AND measure_value < 0"
            ),
            "mustBe": 0,
        },
        {
            "name": "headcount_measure_subcategories_integral",
            "description": (
                "The 22 headcount labels (everything except the FTE-style "
                "positions/number count, the three positions averages, and "
                "years_experience/average) carry whole-person integer "
                "counts. Verified: zero fractional values across all 14 "
                "bronze years."
            ),
            "dimension": "accuracy",
            "query": (
                "SELECT COUNT(*) FROM {object} "
                f"WHERE measure_subcategory NOT IN ({fractional}) "
                "AND measure_value IS NOT NULL "
                "AND measure_value <> FLOOR(measure_value)"
            ),
            "mustBe": 0,
        },
        {
            "name": "years_experience_average_within_range",
            "description": (
                "Mean years of experience (years_experience/average) lies "
                "within [0, 60] — a 60-year career is the conceivable "
                "extreme. Observed bronze range across all years: [0, 50]."
            ),
            "dimension": "accuracy",
            "query": (
                "SELECT COUNT(*) FROM {object} "
                "WHERE measure_subcategory = 'average' "
                "AND measure_value IS NOT NULL "
                "AND (measure_value < 0 OR measure_value > 60)"
            ),
            "mustBe": 0,
        },
        {
            "name": "average_contract_days_within_range",
            "description": (
                "Average contract days (positions/average_contract_days) "
                "lies within [0, 366] — a contract cannot exceed a year. "
                "Observed bronze range across all years: [30, 260]."
            ),
            "dimension": "accuracy",
            "query": (
                "SELECT COUNT(*) FROM {object} "
                "WHERE measure_subcategory = 'average_contract_days' "
                "AND measure_value IS NOT NULL "
                "AND (measure_value < 0 OR measure_value > 366)"
            ),
            "mustBe": 0,
        },
        {
            "name": "state_rows_exactly_81_per_year",
            "description": (
                "Structural fact: every year carries exactly 81 state-level "
                "rows (27 measure pairs x 3 employee types). Verified in "
                "all 14 bronze years."
            ),
            "dimension": "completeness",
            "query": (
                "SELECT COUNT(*) FROM ("
                "SELECT year FROM {object} WHERE district_code IS NULL "
                "GROUP BY year HAVING COUNT(*) <> 81"
                ") AS bad"
            ),
            "mustBe": 0,
        },
        {
            "name": "complete_27_label_grid_per_cell",
            "description": (
                "Structural fact: every (year, geography, employee_type) "
                "cell carries the complete grid of exactly 27 rows with 27 "
                "distinct measure_subcategories — GOSA publishes the full "
                "measurement grid for every entity (zeros included, nothing "
                "suppressed). Verified in all 14 bronze years. GROUP BY "
                "treats NULL geography keys as equal, so the check "
                "self-scopes to each detail level."
            ),
            "dimension": "completeness",
            "query": (
                "SELECT COUNT(*) FROM ("
                "SELECT year, district_code, school_code, employee_type "
                "FROM {object} "
                "GROUP BY year, district_code, school_code, employee_type "
                "HAVING COUNT(*) <> 27 "
                "OR COUNT(DISTINCT measure_subcategory) <> 27"
                ") AS bad"
            ),
            "mustBe": 0,
        },
    ]


def _emit_contract_and_readme(year_range: tuple[int, int]) -> None:
    """Emit the ODCS contract + README. Column order == STANDARD_COLUMNS
    minus detail_level."""
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Georgia Office of Student Achievement (GOSA) Certified Personnel "
            "dataset, compiled from local school systems' Certified/"
            "Classified Personnel Information (CPI) submissions. For every "
            "Georgia public school, school district, and the state as a "
            "whole, publishes a complete grid of 27 staffing measurements "
            "per employee group (81 rows per entity-year): headcount by "
            "certificate level (Bachelor's through Doctoral, plus Other), "
            "certification status (Professional / Provisional), gender, "
            "employment status (Full/Part-time), position metrics (FTE "
            "position count, average annual/daily salary, average contract "
            "days), staff race/ethnicity, and years-of-experience bands "
            "(<1, 1-10, 11-20, 21-30, >30, plus the mean). The three "
            "employee groups are Administrators, PK-12 Teachers, and "
            "Support Personnel; coverage runs from the 2010-11 school year "
            "through 2023-24."
        ),
        title="Certified Personnel (Teachers and Staff Credentials)",
        summary=(
            "Staffing measures for Georgia school teachers, administrators, "
            "and support staff -- credentials, experience, salary, and "
            "demographics by school, district, and state, 2011-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Ending calendar year of the school year. Year 2024 = "
                    "2023-2024 school year. Derived from the bronze "
                    "`LONG_SCHOOL_YEAR` column's ending year."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "nullable": True,
                "example": "644",
                "description": (
                    "GOSA district code (FK to the education districts "
                    "dimension): 3-digit zero-padded for standard districts, "
                    "7-digit for state/commission charter schools (present "
                    "from 2012 onward). NULL for state-level aggregate rows "
                    "(the bronze sentinel `ALL`)."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "nullable": True,
                "example": "0189",
                "description": (
                    "4-digit zero-padded GOSA school code (FK to the "
                    "education schools dimension, composite key with "
                    "district_code). NULL for district-level and "
                    "state-level aggregate rows (the bronze sentinel `ALL`)."
                ),
            },
            {
                "name": "employee_type",
                "type": "string",
                "nullable": False,
                "example": "pk_12_teachers",
                "validValues": sorted(EMPLOYEE_TYPE_MAP.values()),
                "short_description": (
                    "Which staff group the measurement covers: "
                    "administrators, PK-12 teachers, or support personnel."
                ),
                "description": (
                    "Employee group this measurement covers. Snake_case "
                    "recode of bronze EMPLOYEE_TYPE: `administrators`, "
                    "`pk_12_teachers`, `support_personnel`."
                ),
            },
            {
                "name": "measure_category",
                "type": "string",
                "nullable": False,
                "example": "race_ethnicity",
                "validValues": sorted(MEASURE_FAMILY_MAP.values()),
                "short_description": (
                    "The category of staffing measure (e.g. certificate "
                    "level, gender, positions, race/ethnicity, years of "
                    "experience); pairs with measure_subcategory."
                ),
                "description": (
                    "High-level family of the measurement. Snake_case recode "
                    "of bronze DATA_CATEGORY. Together with `measure_subcategory` "
                    "it fully identifies what `measure_value` represents; "
                    "the family is functionally determined by the label "
                    "(27 valid pairs, enforced by a quality check)."
                ),
            },
            {
                "name": "measure_subcategory",
                "type": "string",
                "nullable": False,
                "example": "5_yr_masters",
                "validValues": sorted(set(MEASURE_LABEL_MAP.values())),
                "short_description": (
                    "The specific staffing measure within its family (e.g. "
                    "5_yr_masters, average_annual_salary, full_time); defines "
                    "what measure_value means and its unit."
                ),
                "description": (
                    "Specific measurement within the family. Snake_case "
                    "recode of bronze DATA_SUB_CATEGORY — e.g. "
                    "`5_yr_masters` (family `certificate_level`), "
                    "`average_annual_salary` (family `positions`), "
                    "`less_than_1` / `average` (family `years_experience`). "
                    "`other` is the fifth CERTIFICATE LEVEL bucket (bronze "
                    "`Other *`; the asterisk flags a source footnote), not "
                    "a race value. `asian_pacific_islander` is the bronze "
                    "staff-race label `Asian`: the source publishes only 6 "
                    "race buckets with no separate Pacific Islander label "
                    "in any year, and state-level race-bucket sums equal "
                    "the gender-bucket sums (same population) — the "
                    "pre-1997 OMB combined Asian + Pacific Islander bucket "
                    "per data-cleaning-standards §5b."
                ),
            },
            {
                "name": "measure_value",
                "key_metric": True,
                "type": "float64",
                "example": 42.0,
                "short_description": (
                    "The measurement's value; its unit (headcount, FTE, "
                    "dollars, days, or years) depends on measure_category and "
                    "measure_subcategory, so filter to one pair before aggregating."
                ),
                "description": (
                    "Numeric value of the measurement. UNITS DEPEND ON "
                    "(measure_category, measure_subcategory): a whole-person "
                    "headcount for the 22 count labels (all of "
                    "certificate_level, certified_personnel, gender, "
                    "personnel, race_ethnicity, and the five "
                    "years_experience bands); an FTE-style fractional "
                    "position count for positions/number; US dollars for "
                    "positions/average_annual_salary and "
                    "positions/average_daily_salary; days for "
                    "positions/average_contract_days; years (0.01 "
                    "precision) for years_experience/average. NEVER sum or "
                    "average across rows without first filtering to a "
                    "single (measure_category, measure_subcategory) pair — and "
                    "never sum `average*` labels across entities at all. "
                    "No `unit` marker is declared because the unit varies "
                    "by row; range invariants are enforced by quality "
                    "checks instead (non-negative everywhere; headcount "
                    "labels integral; experience average within [0, 60]; "
                    "contract days within [0, 366]). Known source quirk "
                    "preserved per §4b (extreme-but-conceivable): in the "
                    "2016-17 file ONLY, the certified_personnel family "
                    "(professional/provisional) is uniformly depressed at "
                    "every level (state professional PK-12 teachers = "
                    "2,689 vs ~110,000 in adjacent years) yet internally "
                    "consistent (district sum 2,690; school sum 2,748) — a "
                    "GOSA scope/definition glitch for that family-year, "
                    "served as published."
                ),
            },
        ],
        source="Governor's Office of Student Achievement (GOSA)",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        suppressed_to_null=False,
        limitations=(
            "This source has no suppression markers in any year (2010-11 "
            "through 2023-24); zero counts are published as real `0` "
            "values, and every bronze MEASURE value parses to a valid "
            "number. measure_value has heterogeneous units that depend on "
            "(measure_category, measure_subcategory): a whole-person headcount for "
            "certificate_level / certified_personnel / gender / personnel / "
            "race_ethnicity / years_experience (except `average`); an "
            "FTE-style fractional count for positions/number; US dollars "
            "for positions/average_annual_salary and "
            "positions/average_daily_salary; days for "
            "positions/average_contract_days; and a mean in years for "
            "years_experience/average. Never aggregate measure_value "
            "without first filtering to a single (measure_category, "
            "measure_subcategory) pair, and never sum `average*` labels across "
            "entities. measure_category is functionally determined by "
            "measure_subcategory (27 valid pairs). There is no `demographic` "
            "column: gender and race/ethnicity here describe STAFF and are "
            "measure families, not a cross-cutting demographic axis, so "
            "these rows do not join the demographics dimension; the "
            "race_ethnicity family uses the pre-1997 OMB combined "
            "`asian_pacific_islander` bucket (no separate Pacific Islander "
            "label exists in the source). Known source quirk: the 2016-17 "
            "certified_personnel family (professional/provisional counts) "
            "is uniformly depressed at every level (~2%% of adjacent "
            "years' magnitude) yet internally consistent across levels — "
            "preserved as published; do not trend that family across 2017. "
            "School rows must not be summed to rebuild district or state "
            "headcounts: staff serving multiple schools are counted once "
            "per school assignment but deduplicated at higher levels, so a "
            "district count can even be smaller than a single school's "
            "count (observed only in personnel/part_time; 1,811 cells). "
            "State rows have NULL district_code and school_code; district "
            "rows have NULL school_code."
        ),
        notes=[
            (
                "Three detail levels are present in every year (schools, "
                "districts, state). Split by filename per year partition: "
                "schools.parquet, districts.parquet, states.parquet. "
                "Aggregate rows have NULL geography keys (bronze marks them "
                "with the `ALL` sentinel)."
            ),
            (
                "The dataset is a complete measurement grid: every (year, "
                "geography, employee_type) cell carries exactly 27 rows — "
                "one per (measure_category, measure_subcategory) pair — and every "
                "year carries exactly 81 state rows. Both facts are "
                "enforced by quality checks."
            ),
            (
                "measure_value units vary by (measure_category, "
                "measure_subcategory): filter to one pair before any aggregation. "
                "The `average_annual_salary`, `average_daily_salary`, "
                "`average_contract_days`, and years_experience `average` "
                "labels are entity-level means — they must never be summed "
                "across entities, and a state mean is not the sum of "
                "district means."
            ),
            (
                "Staff race/ethnicity uses the pre-1997 OMB combined "
                "Asian + Pacific Islander bucket, published as "
                "`asian_pacific_islander` (bronze label `Asian`). Math "
                "test per data-cleaning-standards §5b: at the state rows "
                "of every year the 6 race-bucket sums match the "
                "gender-bucket sums (the same certified-personnel "
                "population) within ~0.03%%, with residuals in both "
                "directions — inconsistent with a dropped Pacific Islander "
                "population."
            ),
            (
                "Known source quirk (preserved per data-cleaning-standards "
                "§4b, extreme-but-conceivable): in the 2016-17 file only, "
                "the certified_personnel family reports tiny counts at "
                "every level (state professional PK-12 teachers 2,689 vs "
                "109,979 in 2015-16 and 111,745 in 2017-18) while "
                "remaining internally consistent (district sum 2,690, "
                "school sum 2,748). All other 2016-17 families are at "
                "normal magnitude. Do not trend the certified_personnel "
                "family across 2017."
            ),
            (
                "No suppression exists in this source: zeros are real "
                "measurements, and measure_value has zero NULLs in every "
                "year. average_annual_salary of 0.0 occurs at small cells "
                "where an entity reports positions without salary data."
            ),
            (
                "Do not sum school rows to rebuild district or state "
                "headcounts: staff serving multiple schools are counted "
                "once per school assignment at school level but "
                "deduplicated at higher levels. In 1,811 district cells — "
                "all in personnel/part_time — the district headcount is "
                "smaller than a single school's count in that district "
                "(e.g. 2023 district 669 support part_time: district 39, "
                "one school 41, school-row sum 172). Faithful bronze "
                "passthrough; use the published district/state rows for "
                "aggregate analysis."
            ),
        ],
        quality_checks=_quality_checks(),
    )


if __name__ == "__main__":
    main()
