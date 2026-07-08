"""Transform bronze dropout_rate_9_12 files into gold fact tables.

Source: Governor's Office of Student Achievement (GOSA) — 9-12 Dropouts,
2011-2024 (14 bronze files, one school year each). For every Georgia public
school, plus official district and state rollups, reports the number of
grade 9-12 dropouts (``num_dropouts``) and the dropout rate
(``dropout_rate``) by demographic subgroup.

Design decisions (from bronze-data-structure.md and data-cleaning-standards;
every invariant below was re-verified against THIS topic's 14 bronze files,
not inherited from the dropout_rate_7_12 sibling):

- **Two near-identical eras, one pipeline.** Era 1 (2023-2024) adds a leading
  constant ``#RPT_NAME`` column ("9-12 Dropouts"); Era 2 (2011-2022) is the
  same 10 columns without it. Both route through one transform function; the
  era difference is detection-only (``detect_era_by_columns``, most-specific
  signature first) plus an Era 1 constant guard on ``#RPT_NAME``.
- **All-string bronze read.** Files are read with ``infer_schema_length=0``
  so geography codes keep leading zeros and the ``ALL`` sentinels can never
  be schema-inference casualties. Suppression markers are handled at read
  time by ``read_bronze_file`` (2011-2020 blank cells and 2021-2024 ``TFS``
  literals both arrive as NULL); metrics are cast explicitly afterwards.
- **Heavy suppression is bronze-real.** GOSA suppresses any cell below the
  n=10 reporting threshold, which blanks ~64-75%% of school-level rows in
  every year. ``num_dropouts`` and ``dropout_rate`` are always co-suppressed
  (verified across all 14 files: zero rows where exactly one is missing) and
  every published count is >= 10 — both pinned as contract quality checks.
- **Asian / Pacific Islander is the combined bucket (§5b).** The bronze
  publishes the explicit label ``Asian/Pacific Islander`` as one of six race
  buckets and never a separate Pacific Islander row. The §5b math test
  confirms the convention: at the state level the six race-bucket counts sum
  EXACTLY to the ALL Students total in every year 2011-2024 (as do
  male+female), so Pacific Islanders are folded in, not dropped. The shared
  alias maps the label to ``asian_pacific_islander`` (pre-1997 OMB combined
  bucket) — never split, no synthesized rollup rows.
- **Demographic labels carry a constant prefix.** Every ``LABEL_LVL_1_DESC``
  starts with ``"9-12 Drop Outs -"``; the prefix is stripped and the
  remainder normalized via the shared ``normalize_demographic_column()``
  (15 labels -> 15 distinct canonical keys; no subgroup collisions, so
  ``aggregate_demographic_collisions`` is not needed — the collision guard
  in ``main()`` would catch any surprise).
- **Limited English Proficient gap.** The 2020-2022 files drop the Limited
  English Proficient subgroup (14 labels instead of 15); it returns in 2023.
  Re-verified per-file for this topic — the gap years match the 7-12
  sibling exactly. The transform maps whatever labels appear; the gap is
  pinned as a quality check so a silent reappearance/disappearance is caught.
- **2022 mislabeled district aggregates, reclassified.** The 2022 file
  labels the district-aggregate rows of two state-charter districts —
  7830627 (State Charter Schools II- Atlanta SMART Academy) and 7830636
  (State Charter Schools II- Northwest Classical Academy) — as
  ``DETAIL_LVL_DESC=School`` while carrying the ``INSTN_NUMBER=ALL``
  aggregate sentinel (28 rows, all suppressed). 2023 and 2024 publish the
  same rows correctly as District. The sentinel itself proves the row is an
  aggregate, so any "School" row with ``INSTN_NUMBER=ALL`` is reclassified
  to district detail (logged per file; the natural-key collision guard
  protects against a reclassified row colliding with a genuine district
  row — verified: 2022 has zero genuine District rows for these codes).
- **No §4b masks.** A full scan of all 14 bronze files found no impossible
  values: ``PROGRAM_TOTAL`` spans [10, 21500] (non-negative integers) and
  ``PROGRAM_PERCENT`` spans [0.2, 93.6] on the 0-100 source scale — nothing
  outside the metrics' defined domains, so no ``_null_*`` helper exists and
  the manifest carries no ``masked_values`` section.
- **Dedup tie-break.** Each bronze file covers exactly one school year and
  years never overlap across files; the bronze grain
  (detail level x district x school x demographic) is unique within every
  file (verified: zero duplicate key groups in any year), so no duplicates
  are expected. ``sort_col="num_dropouts"`` remains as the documented
  safety net: prefer the row with a reported (non-null, larger) count over
  a suppressed placeholder.
"""

import logging
from pathlib import Path

import polars as pl

from src.utils.demographics import (
    DEMOGRAPHIC_ALIASES,
    normalize_demographic_column,
)
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

TOPIC = "dropout_rate_9_12"
BRONZE_DIR = Path("data/bronze/education/gosa/dropout_rate_9_12")
GOLD_DIR = Path("data/gold/education/dropout_rate_9_12")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Every LABEL_LVL_1_DESC value starts with this constant prefix (note the
# space inside "Drop Outs" and the unspaced trailing hyphen).
DEMOGRAPHIC_LABEL_PREFIX = "9-12 Drop Outs -"

# Era 1's constant #RPT_NAME value (no space variant: "Dropouts").
ERA1_REPORT_NAME = "9-12 Dropouts"

# Aggregate-row sentinel in SCHOOL_DSTRCT_CD (state rows) and INSTN_NUMBER
# (state + district rows). Becomes NULL in gold, never a key value.
GEOGRAPHY_SENTINEL = "ALL"

DETAIL_LEVEL_MAP: dict[str, str] = {
    "State": "state",
    "District": "district",
    "School": "school",
}

# Era-detection signatures, most-specific first (Era 2 is an Era 1 subset:
# the only schema difference is Era 1's leading constant #RPT_NAME column).
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_1": ["#RPT_NAME", "LONG_SCHOOL_YEAR", "PROGRAM_TOTAL"],
    "era_2": ["LONG_SCHOOL_YEAR", "PROGRAM_TOTAL"],
}

# Bronze columns every file must carry (rename-coverage guard). An unmatched
# source column silently becomes NULL in gold — the most common data-loss bug.
REQUIRED_BRONZE_COLUMNS: list[str] = [
    "LONG_SCHOOL_YEAR",
    "DETAIL_LVL_DESC",
    "SCHOOL_DSTRCT_CD",
    "INSTN_NUMBER",
    "LABEL_LVL_1_DESC",
    "PROGRAM_TOTAL",
    "PROGRAM_PERCENT",
]

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "num_dropouts",
    "dropout_rate",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "demographic": pl.Utf8,
    "num_dropouts": pl.Int64,
    "dropout_rate": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = ["num_dropouts", "dropout_rate"]

NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "detail_level",
]

# The 15 canonical demographic keys this topic publishes (14 in 2020-2022,
# which lack english_learners). Used for the contract enum and the
# partition-sum quality checks.
DEMOGRAPHIC_VALUES: list[str] = sorted(
    [
        "all",
        "asian_pacific_islander",
        "black",
        "economically_disadvantaged",
        "english_learners",
        "female",
        "hispanic",
        "male",
        "migrant",
        "multiracial",
        "native_american",
        "not_economically_disadvantaged",
        "students_with_disabilities",
        "students_without_disabilities",
        "white",
    ]
)

# The six mutually exclusive race buckets (combined Asian/PI convention —
# see module docstring). At the state level these sum exactly to the `all`
# total in every year, which the partition-sum quality check enforces.
RACE_BUCKET_KEYS: list[str] = [
    "asian_pacific_islander",
    "black",
    "hispanic",
    "multiracial",
    "native_american",
    "white",
]


# =============================================================================
# Casting helpers
# =============================================================================


def _to_float_expr(col: str) -> pl.Expr:
    """Cast an all-string bronze metric column to Float64.

    Suppression markers (TFS, blanks) already arrived as NULL from
    ``read_bronze_file``; ``strict=False`` nulls any other non-numeric
    residue instead of failing the cast.
    """
    return pl.col(col).str.strip_chars().cast(pl.Float64, strict=False)


def _to_int_expr(col: str) -> pl.Expr:
    """Cast an all-string bronze count column to Int64 via Float64.

    The Float64 hop tolerates decimal-formatted counts ("16.0") without
    silently nulling them; counts are integral so the Int64 cast is exact.
    """
    return _to_float_expr(col).cast(pl.Int64)


def _require_columns(df: pl.DataFrame, required: list[str], label: str) -> None:
    """Raise if any expected bronze column is absent (rename-coverage guard)."""
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"{label}: expected bronze column(s) missing: {missing}. "
            f"Present: {df.columns}"
        )


# =============================================================================
# Per-file transform (both eras share one shape)
# =============================================================================


def _validate_era1_constants(df: pl.DataFrame, year: int) -> None:
    """Hard-stop if Era 1's constant #RPT_NAME column carries unexpected values.

    Anything other than "9-12 Dropouts" means non-dropout report rows are
    mixed into this topic's bronze and must be analyzed, not silently kept.
    """
    rpt_names = df["#RPT_NAME"].drop_nulls().unique().to_list()
    if rpt_names != [ERA1_REPORT_NAME]:
        raise ValueError(f"era_1 {year}: unexpected #RPT_NAME values {rpt_names}")


def _reclassify_mislabeled_aggregates(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Reclassify "School" rows carrying the INSTN_NUMBER=ALL sentinel.

    The ALL sentinel marks an aggregate row by definition, so a School-labeled
    row with it is a source mislabeling of a district aggregate. Known case:
    the 2022 file mislabels the district rows of two state-charter districts
    (7830627 Atlanta SMART Academy, 7830636 Northwest Classical Academy;
    28 rows, all suppressed) — 2023/2024 publish the same rows correctly as
    District. Applied generically because the sentinel itself is the proof;
    the collision guard in main() catches any clash with a genuine district
    row (verified: 2022 has none for these codes).
    """
    mislabeled = (pl.col("detail_level") == "school") & (
        pl.col("INSTN_NUMBER").str.strip_chars() == GEOGRAPHY_SENTINEL
    )
    mislabeled_df = df.filter(mislabeled)
    if mislabeled_df.height:
        affected = mislabeled_df["SCHOOL_DSTRCT_CD"].unique().sort().to_list()
        # Manifest artifact: the data review verifies repairs from here, not logs.
        manifest.record_reclassified(
            year, mislabeled_df.height, "school_labeled_aggregate_to_district"
        )
        logger.warning(
            "Year %d: reclassifying %d School-labeled row(s) with the "
            "INSTN_NUMBER=ALL aggregate sentinel to district detail "
            "(districts: %s) — source mislabeling, see module docstring",
            year,
            mislabeled_df.height,
            affected,
        )
        df = df.with_columns(
            pl.when(mislabeled)
            .then(pl.lit("district"))
            .otherwise(pl.col("detail_level"))
            .alias("detail_level")
        )
    return df


def _map_demographics(df: pl.DataFrame, manifest: TransformManifest) -> pl.DataFrame:
    """Map LABEL_LVL_1_DESC to the canonical ``demographic`` column.

    Strips the constant label prefix, then normalizes via the shared
    canonical path (§5). The source's explicit "Asian/Pacific Islander"
    label maps to the combined ``asian_pacific_islander`` bucket — confirmed
    by the §5b math test (see module docstring).
    """
    df = df.with_columns(
        pl.col("LABEL_LVL_1_DESC")
        .str.strip_prefix(DEMOGRAPHIC_LABEL_PREFIX)
        .alias("_demographic_raw")
    ).with_columns(
        normalize_demographic_column("_demographic_raw").alias("demographic")
    )
    # Record the effective slice of the shared alias map: only the aliases
    # this file's labels actually hit, so the manifest stays reviewable while
    # the unmapped guard still flags any label the shared map cannot place.
    observed_upper = {
        str(v).strip().upper()
        for v in df["_demographic_raw"].drop_nulls().unique().to_list()
    }
    effective_map = {
        k: v for k, v in DEMOGRAPHIC_ALIASES.items() if k in observed_upper
    }
    manifest.record_categorical(
        column="demographic",
        map_dict=effective_map,
        bronze_series=df["_demographic_raw"],
        gold_series=df["demographic"],
    )
    return df


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame:
    """Read one bronze file, detect its era, and transform it to gold shape.

    Year resolution: every file carries exactly one LONG_SCHOOL_YEAR value
    whose ending year must agree with the filename year, so a misnamed file
    cannot silently mislabel a whole year.

    Args:
        path: Bronze file path.
        manifest: Manifest for read-loss / file / bronze-count / categorical
            recording.

    Returns:
        Gold-shaped DataFrame with STANDARD_COLUMNS.
    """
    # All-string read: geography codes keep leading zeros and sentinels are
    # never inference casualties; TFS/blank suppression arrives as NULL.
    df, loss = read_bronze_file(path, infer_schema_length=0, return_loss=True)
    filename_year = extract_year_from_filename(path.name)
    if filename_year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")
    manifest.record_read_loss(
        filename_year, path.name, loss["raw_rows"], loss["parsed_rows"]
    )

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{path.name}: no era signature matched columns {df.columns}")
    _require_columns(df, REQUIRED_BRONZE_COLUMNS, f"{era} {path.name}")
    if era == "era_1":
        _validate_era1_constants(df, filename_year)

    # Exactly one LONG_SCHOOL_YEAR value per file; its ending year must agree
    # with the filename year.
    school_years = df["LONG_SCHOOL_YEAR"].drop_nulls().unique().to_list()
    if len(school_years) != 1:
        raise ValueError(
            f"{path.name}: expected one LONG_SCHOOL_YEAR, got {school_years}"
        )
    year = parse_school_year(school_years[0])
    if year != filename_year:
        raise ValueError(
            f"{path.name}: LONG_SCHOOL_YEAR ending year {year} disagrees "
            f"with filename year {filename_year}"
        )

    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)
    logger.info("Processing %s as %s (year %d)", path.name, era, year)

    # Detail level: State/District/School -> state/district/school. Unmapped
    # values become NULL and surface via the manifest's unmapped guard.
    df = df.with_columns(
        pl.col("DETAIL_LVL_DESC")
        .replace_strict(DETAIL_LEVEL_MAP, default=None)
        .alias("detail_level")
    )
    manifest.record_categorical(
        column="detail_level",
        map_dict=DETAIL_LEVEL_MAP,
        bronze_series=df["DETAIL_LVL_DESC"],
        gold_series=df["detail_level"],
    )

    # Source mislabeling repair (2022): aggregate rows labeled School.
    df = _reclassify_mislabeled_aggregates(df, year, manifest)

    # Demographics: shared-alias normalization after prefix stripping (§5/§5b).
    df = _map_demographics(df, manifest)

    # Geography keys: ALL sentinels -> NULL (never carried into gold);
    # zfill pads 3-digit county codes / 4-digit school codes and passes
    # 7-digit state-charter codes through unchanged (never truncate).
    # Metrics: counts via the exact Float64->Int64 hop; the 0-100 source
    # percentage is divided by 100 onto the 0-1 proportion scale (§4).
    district_clean = pl.col("SCHOOL_DSTRCT_CD").str.strip_chars()
    school_clean = pl.col("INSTN_NUMBER").str.strip_chars()
    df = df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.when(district_clean == GEOGRAPHY_SENTINEL)
        .then(None)
        .otherwise(district_clean.str.zfill(3))
        .alias("district_code"),
        pl.when(school_clean == GEOGRAPHY_SENTINEL)
        .then(None)
        .otherwise(school_clean.str.zfill(4))
        .alias("school_code"),
        _to_int_expr("PROGRAM_TOTAL").alias("num_dropouts"),
        (_to_float_expr("PROGRAM_PERCENT") / 100.0).alias("dropout_rate"),
    )

    return df.select(STANDARD_COLUMNS)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for dropout_rate_9_12."""
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
    # mean an alias/reclassification bug and must raise, not be deduped away.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: each bronze file is a distinct school year with no overlap,
    # and the per-file grain is unique (verified across all 14 files), so no
    # duplicates are expected; prefer the row with a reported (non-null,
    # larger) num_dropouts over a suppressed placeholder as the safety net.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code", "demographic"],
        district_keys=["year", "district_code", "demographic"],
        state_keys=["year", "demographic"],
        sort_col="num_dropouts",
    )

    # 4. Geography nulling (shared domain rules). No §4b masks: the full
    # bronze scan found no impossible values (see module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. Suppression NULL rates are heavy (~64-75% of school
    # rows) but rise only gradually across years, so no spike is expected.
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

    Kept out of ``main()`` so the pipeline flow stays readable. The column
    declaration order MUST match STANDARD_COLUMNS minus ``detail_level`` —
    the contract's properties (and the validator's schema check) follow it.
    """
    race_list = ", ".join(f"'{k}'" for k in RACE_BUCKET_KEYS)
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Number and rate of grade 9-12 dropouts for Georgia public "
            "schools, with official district and state rollups, by "
            "demographic subgroup (race/ethnicity, gender, economic status, "
            "English proficiency, migrant status, disability status). "
            "Published by GOSA for school years 2010-11 through 2023-24."
        ),
        title="Grades 9-12 Dropout Rates",
        summary=(
            "Georgia grade 9-12 dropout counts and rates by school, "
            "district, and demographic subgroup, 2011-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Ending (spring) calendar year of the school year (e.g. "
                    "2024 for 2023-24), parsed from the source's "
                    "LONG_SCHOOL_YEAR and cross-checked against the filename."
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
                "example": "0105",
                "description": (
                    "GOSA school code, zero-padded to 4 characters (composite "
                    "FK to schools dimension with district_code; not globally "
                    "unique on its own). NULL on district- and state-level "
                    "rows."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "all",
                "validValues": DEMOGRAPHIC_VALUES,
                "short_description": (
                    "Student subgroup the row counts: 'all' plus race, "
                    "gender, economic, English-proficiency, migrant, and "
                    "disability categories; mutually exclusive within a "
                    "category."
                ),
                "description": (
                    "Demographic subgroup (FK to the global demographics "
                    "dimension). Race buckets use the combined "
                    "asian_pacific_islander key (pre-1997 OMB convention): "
                    "the source publishes a single 'Asian/Pacific Islander' "
                    "label and its six race buckets sum exactly to the 'all' "
                    "total at the state level in every year, so Pacific "
                    "Islanders are folded in, never published separately. "
                    "english_learners rows are absent in 2020-2022 (the "
                    "source dropped the Limited English Proficient subgroup "
                    "in those files). 'all' is the unfiltered total and "
                    "overlaps every other value; subgroups are mutually "
                    "exclusive only within their own category (race, gender, "
                    "economic, special population)."
                ),
            },
            {
                "name": "num_dropouts",
                "type": "int64",
                "metric_component": "numerator",
                "unit": "count",
                "example": 27,
                "null_meaning": (
                    "Suppressed by GOSA (cell below the n=10 reporting "
                    "threshold; blank cells in 2011-2020 sources, TFS "
                    "literals in 2021-2024)."
                ),
                "description": (
                    "Number of students in grades 9-12 who dropped out "
                    "during the school year. Published values are always "
                    ">= 10 because GOSA suppresses smaller cells; ~64-75%% "
                    "of school-level rows are suppressed (NULL) in every "
                    "year. Always co-suppressed with dropout_rate."
                ),
            },
            {
                "name": "dropout_rate",
                "type": "float64",
                "key_metric": True,
                "unit": "proportion",
                "example": 0.028,
                "null_meaning": (
                    "Suppressed by GOSA (cell below the n=10 reporting "
                    "threshold; always co-suppressed with num_dropouts)."
                ),
                "short_description": (
                    "Share of grade 9-12 students who dropped out during "
                    "the school year, on a 0-1 scale."
                ),
                "description": (
                    "Grade 9-12 dropout rate as a proportion (0-1 scale): "
                    "dropouts divided by the subgroup's grade 9-12 "
                    "enrollment. The source publishes 0-100 percentages with "
                    "one decimal place (observed 0.2-93.6 across all years); "
                    "divided by 100. Always co-suppressed with num_dropouts."
                ),
            },
        ],
        source="GOSA",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        # Derived prose plus the suppression-scale caveat consumers need.
        limitations=(
            "Suppressed cells are NULL (not zero): GOSA suppresses any cell "
            "below the n=10 reporting threshold, which blanks ~64-75%% of "
            "school-level rows in every year — school-level analyses should "
            "expect sparse coverage, and summing only published subgroup "
            "counts undercounts true totals at school grain (use district or "
            "state rows for official aggregates). State rows have NULL "
            "district_code and school_code; district rows have NULL "
            "school_code. The race axis uses the combined "
            "asian_pacific_islander bucket — not comparable row-for-row "
            "with split-convention topics without aggregating those topics' "
            "asian + pacific_islander rows at query time. english_learners "
            "rows are absent in 2020-2022."
        ),
        notes=[
            (
                "Suppression representation differs by era and both become "
                "NULL: 2011-2020 sources use blank cells, 2021-2024 sources "
                "use the literal 'TFS' (too few students). num_dropouts and "
                "dropout_rate are always co-suppressed (verified: zero rows "
                "in any year where exactly one of the two is missing)."
            ),
            (
                "Published num_dropouts values are always >= 10 — the "
                "source's n=10 cell-size suppression threshold. Enforced by "
                "a quality check so a future sub-threshold value surfaces."
            ),
            (
                "Asian/Pacific Islander is the combined pre-1997 OMB bucket "
                "(asian_pacific_islander), per data-cleaning-standards §5b: "
                "the source publishes six race buckets whose state-level "
                "counts sum EXACTLY to the ALL Students total in every year "
                "2011-2024 (male+female do too), proving Pacific Islanders "
                "are folded into the bucket rather than dropped. The split "
                "asian / pacific_islander keys are never emitted."
            ),
            (
                "2022 source defect, repaired: the 2022 file labels the "
                "district-aggregate rows of two state-charter districts as "
                "School-level while carrying the INSTN_NUMBER=ALL aggregate "
                "sentinel — 7830627 (State Charter Schools II- Atlanta SMART "
                "Academy) and 7830636 (State Charter Schools II- Northwest "
                "Classical Academy), 28 rows, all suppressed. 2023 and 2024 "
                "publish the same rows correctly as District; the transform "
                "reclassifies sentinel-bearing School rows to district "
                "detail (logged)."
            ),
            (
                "The demographic axis has 15 subgroups in most years but 14 "
                "in 2020-2022, where the source dropped the Limited English "
                "Proficient subgroup (it returns in 2023). Pinned by a "
                "quality check."
            ),
            (
                "Sibling topic dropout_rate_7_12 covers the same population "
                "extended down to grades 7-8; the two topics share source "
                "structure and conventions but are published separately by "
                "GOSA and are not additive (9-12 is a subset of 7-12)."
            ),
            (
                "Metric NULL rates are high (~64-75%% of school rows) but "
                "drift only gradually across years — heavy suppression is "
                "bronze-real, not a transform defect."
            ),
        ],
        quality_checks=[
            {
                "name": "dropout_metrics_co_suppressed",
                "description": (
                    "GOSA suppresses num_dropouts and dropout_rate together "
                    "in every era (blank cells 2011-2020, TFS 2021-2024): no "
                    "row may have exactly one of the two metrics NULL."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(num_dropouts IS NULL) <> (dropout_rate IS NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_rows_never_suppressed",
                "description": (
                    "GOSA publishes unsuppressed statewide aggregates in "
                    "every year: state-level rows (district_code and "
                    "school_code both NULL) must carry non-NULL "
                    "num_dropouts and dropout_rate."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE district_code IS "
                    "NULL AND school_code IS NULL "
                    "AND (num_dropouts IS NULL OR dropout_rate IS NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "num_dropouts_meets_reporting_threshold",
                "description": (
                    "Every published num_dropouts is >= 10 — GOSA's n=10 "
                    "cell-size suppression threshold (verified across all "
                    "bronze years). A smaller value means a suppression "
                    "regression or a scale/column-swap error."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "num_dropouts IS NOT NULL AND num_dropouts < 10"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_race_partition_sums_to_all",
                "description": (
                    "At the state level the six mutually exclusive race "
                    "buckets partition the dropout population: their "
                    "num_dropouts values sum exactly to the 'all' total in "
                    "every year (the §5b math test that proves the combined "
                    "Asian/Pacific Islander convention). State rows are "
                    "never suppressed, so the sum is NULL-safe."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year FROM {object} "
                    "WHERE district_code IS NULL AND school_code IS NULL "
                    "GROUP BY year HAVING "
                    f"SUM(CASE WHEN demographic IN ({race_list}) "
                    "THEN num_dropouts ELSE 0 END) <> "
                    "MAX(CASE WHEN demographic = 'all' THEN num_dropouts "
                    "END)) AS bad_years"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_gender_partition_sums_to_all",
                "description": (
                    "At the state level male + female num_dropouts sums "
                    "exactly to the 'all' total in every year (verified "
                    "across all bronze years; state rows are never "
                    "suppressed)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year FROM {object} "
                    "WHERE district_code IS NULL AND school_code IS NULL "
                    "GROUP BY year HAVING "
                    "SUM(CASE WHEN demographic IN ('male', 'female') "
                    "THEN num_dropouts ELSE 0 END) <> "
                    "MAX(CASE WHEN demographic = 'all' THEN num_dropouts "
                    "END)) AS bad_years"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_economic_partition_sums_to_all",
                "description": (
                    "At the state level economically_disadvantaged + "
                    "not_economically_disadvantaged num_dropouts sums "
                    "exactly to the 'all' total in every year (verified "
                    "across all bronze years; state rows are never "
                    "suppressed)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year FROM {object} "
                    "WHERE district_code IS NULL AND school_code IS NULL "
                    "GROUP BY year HAVING "
                    "SUM(CASE WHEN demographic IN "
                    "('economically_disadvantaged', "
                    "'not_economically_disadvantaged') "
                    "THEN num_dropouts ELSE 0 END) <> "
                    "MAX(CASE WHEN demographic = 'all' THEN num_dropouts "
                    "END)) AS bad_years"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_disability_partition_sums_to_all",
                "description": (
                    "At the state level students_with_disabilities + "
                    "students_without_disabilities num_dropouts sums "
                    "exactly to the 'all' total in every year (verified "
                    "across all bronze years; state rows are never "
                    "suppressed)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year FROM {object} "
                    "WHERE district_code IS NULL AND school_code IS NULL "
                    "GROUP BY year HAVING "
                    "SUM(CASE WHEN demographic IN "
                    "('students_with_disabilities', "
                    "'students_without_disabilities') "
                    "THEN num_dropouts ELSE 0 END) <> "
                    "MAX(CASE WHEN demographic = 'all' THEN num_dropouts "
                    "END)) AS bad_years"
                ),
                "mustBe": 0,
            },
            {
                "name": "english_learners_absent_2020_2022",
                "description": (
                    "The source dropped the Limited English Proficient "
                    "subgroup in the 2020, 2021, and 2022 files (present in "
                    "all other years): no english_learners rows may exist "
                    "in those years."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "demographic = 'english_learners' "
                    "AND year IN (2020, 2021, 2022)"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
