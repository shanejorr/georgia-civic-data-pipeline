"""Transform bronze high_school_completers files into gold fact tables.

Source: Governor's Office of Student Achievement (GOSA) — HS Completer
Credentials report, school years 2010-11 through 2023-24 (14 bronze files,
one school year each). For every Georgia public school, plus official
district and state rollups, reports the number of high-school completers
(``num_completers``) by credential type and demographic subgroup, and each
demographic's share of the credential's completers
(``pct_of_credential_type``).

Design decisions (from bronze-data-structure.md and data-cleaning-standards;
every invariant below was re-verified against THIS topic's 14 bronze files):

- **Two near-identical eras, one pipeline.** Era 2 (2023-2024) adds a leading
  constant ``#RPT_NAME`` column ("HS Completer Credentials"); Era 1
  (2011-2022) is the same 11 columns without it. Both route through one
  transform function; the era difference is detection-only
  (``detect_era_by_columns``, most-specific signature first) plus an Era 2
  constant guard on ``#RPT_NAME``.
- **Detail level is implicit in the geography sentinels.** Bronze has no
  ``DETAIL_LVL_DESC`` column; the ``ALL`` sentinel encodes the level:
  district=ALL + school=ALL -> state; district=code + school=ALL -> district;
  district=code + school=code -> school. The combination (district=ALL,
  school=code) never occurs (verified: 0 rows across all 14 files).
- **`pct_of_credential_type` is the demographic's share of the credential.**
  Verified exactly across 2011/2022/2024 state rows: PROGRAM_PERCENT equals
  the row's PROGRAM_TOTAL divided by the credential's demographic=Total
  PROGRAM_TOTAL, x100 (e.g. 2022 state General Education Diplomas: Male
  55,853 / 114,359 = 48.8). bronze-data-structure.md originally claimed the
  denominator was the COMPLETER_TYPE total (credentials summing to ~100%%
  within a completer type) — disproved by the 2022 state Other Completers
  rows where BOTH credentials carry PROGRAM_PERCENT=100 (Certificates=18,
  Special Ed=189; under the old claim they would read 8.7 / 91.3). The
  structure doc has been amended. Demographic=Total rows are always exactly
  100 where non-null (0 violations in 14 files); pinned as a quality check.
- **Asian is the combined Asian/Pacific Islander bucket (§5b).** Bronze has
  only 6 race buckets and never a separate Pacific Islander row. The §5b
  math test is exact: in every group where all six race-bucket counts and
  the Total count are published — 6,369 (geography x completer_type x
  credential) groups across all years, including every complete state group
  — the race counts sum EXACTLY to the Total. Pacific Islanders are folded
  in, not dropped, so the bare "Asian" label is remapped topic-locally to
  "Asian/Pacific Islander" BEFORE ``normalize_demographic_column()`` (which
  canonicalizes it to ``asian_pacific_islander``). Never split, no
  synthesized rollup rows. Sibling GOSA reports (dropout_rate_*) publish the
  same concept under the explicit "Asian/Pacific Islander" label.
- **Suppression representation varies by year; all forms become NULL.**
  Re-verified per file (the structure doc's original "TFS is the only
  marker" claim was 2022-specific and has been amended):
    * 2011: 9,073 rows blank in BOTH metrics; plus 10,339 rows with
      PROGRAM_TOTAL=TFS but a published PROGRAM_PERCENT.
    * 2012-2017 and 2021: blank cells only, perfectly co-located in both
      metrics (no TFS anywhere).
    * 2018-2020: blanks co-located in both metrics, plus 2,319 / 2,230 /
      2,130 rows with PROGRAM_TOTAL=TFS and a published PROGRAM_PERCENT.
    * 2022: TFS only, both metrics co-suppressed (30,026 rows each).
    * 2023-2024: TFS only; 1,953 / 1,860 count-suppressed rows keep a
      published percent.
  In every year: ``num_completers`` non-null implies
  ``pct_of_credential_type`` non-null (0 violations) — pinned as a quality
  check. Literal 0 counts are real values (not suppression) and appear only
  in 2012-2017 and 2021-2022.
- **Two topic categoricals.** ``credential_type`` (6 snake_case values;
  2011 predates "General Education Diplomas" so it has only 5) and
  ``completer_type`` (graduates / other_completers). completer_type is
  functionally determined by credential_type (the four diploma credentials
  are Graduates; Special Education Diplomas and Certificates of Attendance
  are Other Completers) but is kept as a meaningful cohort grouping; the
  dependency is pinned as a quality check. ``LABEL_SORT_ORDER`` (redundant
  integer code) and the name columns are dropped.
- **No §4b masks.** A full scan of all 14 bronze files found no impossible
  values: counts are non-negative (0-119,764) and PROGRAM_PERCENT spans
  [0, 100] on the 0-100 source scale — nothing outside the metrics' defined
  domains, so no ``_null_*`` helper exists and the manifest carries no
  ``masked_values`` section.
- **Dedup tie-break.** Each bronze file covers exactly one school year and
  years never overlap across files; the bronze grain (geography x
  completer_type x credential x demographic) is unique within every file
  (verified: 0 duplicate key groups in any year), so no duplicates are
  expected. ``sort_col="num_completers"`` remains as the documented safety
  net: prefer the row with a reported (non-null, larger) count over a
  suppressed placeholder.
- **ID formatting.** district_code zfill(3) pads standard 3-digit codes and
  passes 7-digit state-charter codes through unchanged; school_code zfill(4)
  normalizes the inconsistent bronze padding (the 2011/2018/2019/2020 files
  mix 3- and 4-char codes; all other files are uniformly 4-char).
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

TOPIC = "high_school_completers"
BRONZE_DIR = Path("data/bronze/education/gosa/high_school_completers")
GOLD_DIR = Path("data/gold/education/high_school_completers")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Era 2's constant #RPT_NAME value.
ERA2_REPORT_NAME = "HS Completer Credentials"

# Aggregate-row sentinel in SCHOOL_DSTRCT_CD (state rows) and INSTN_NUMBER
# (state + district rows). Becomes NULL in gold, never a key value.
GEOGRAPHY_SENTINEL = "ALL"

# Era-detection signatures, most-specific first (Era 1 is an Era 2 subset:
# the only schema difference is Era 2's leading constant #RPT_NAME column).
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_2_with_rpt_name": ["#RPT_NAME", "LONG_SCHOOL_YEAR", "PROGRAM_TOTAL"],
    "era_1": ["LONG_SCHOOL_YEAR", "PROGRAM_TOTAL"],
}

# Bronze columns every file must carry (rename-coverage guard). An unmatched
# source column silently becomes NULL in gold — the most common data-loss bug.
REQUIRED_BRONZE_COLUMNS: list[str] = [
    "LONG_SCHOOL_YEAR",
    "SCHOOL_DSTRCT_CD",
    "INSTN_NUMBER",
    "COMPLETER_TYPE",
    "LABEL_LVL_1_DESC",
    "LABEL_LVL_5_CD",
    "PROGRAM_TOTAL",
    "PROGRAM_PERCENT",
]

# Bronze columns that are dropped, not transformed: the constant Era 2 report
# label, the two name columns (dimension attributes), and LABEL_SORT_ORDER
# (an integer one-to-one with LABEL_LVL_1_DESC, with a different order in the
# 2011 file — pure presentation metadata).
DROPPED_BRONZE_COLUMNS: list[str] = [
    "#RPT_NAME",
    "SCHOOL_DSTRCT_NM",
    "INSTN_NAME",
    "LABEL_SORT_ORDER",
]

# LABEL_LVL_1_DESC -> snake_case credential_type. The bronze labels carry
# punctuation (periods, an ampersand) and title-case "Of", so we map
# explicitly rather than mechanically lowercasing. The 2011 file lacks
# "General Education Diplomas" (5 labels); 2012+ files carry all 6.
CREDENTIAL_TYPE_MAP: dict[str, str] = {
    "Certificates Of Attendance": "certificates_of_attendance",
    "Diplomas with Both College Prep. & Voc.": "diplomas_college_prep_and_vocational",
    "Diplomas with College Prep Endorsements": "diplomas_college_prep",
    "Diplomas with Vocational Endorsements": "diplomas_vocational",
    "General Education Diplomas": "general_education_diplomas",
    "Special Education Diplomas": "special_education_diplomas",
}

# COMPLETER_TYPE -> snake_case. Functionally determined by credential_type
# (pinned as a quality check) but kept as a meaningful cohort grouping.
COMPLETER_TYPE_MAP: dict[str, str] = {
    "Graduates": "graduates",
    "Other Completers": "other_completers",
}

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "completer_type",
    "credential_type",
    "num_completers",
    "pct_of_credential_type",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "demographic": pl.Utf8,
    "completer_type": pl.Utf8,
    "credential_type": pl.Utf8,
    "num_completers": pl.Int64,
    "pct_of_credential_type": pl.Float64,
}

METRIC_COLUMNS: list[str] = ["num_completers", "pct_of_credential_type"]

NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "completer_type",
    "credential_type",
    "detail_level",
]

# The 9 canonical demographic keys this topic publishes (combined Asian/PI
# convention — see module docstring). Used for the contract enum and the
# partition-sum quality checks.
DEMOGRAPHIC_VALUES: list[str] = sorted(
    [
        "all",
        "asian_pacific_islander",
        "black",
        "female",
        "hispanic",
        "male",
        "multiracial",
        "native_american",
        "white",
    ]
)

# The six mutually exclusive race buckets. In every complete group their
# num_completers values sum exactly to the 'all' total (the §5b math test),
# which the race partition quality checks enforce.
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


def _reject_unexpected_columns(df: pl.DataFrame, label: str) -> None:
    """Raise on bronze columns that are neither transformed nor known-dropped.

    A new upstream column must be triaged (drop vs. propagate) rather than
    silently ignored.
    """
    known = set(REQUIRED_BRONZE_COLUMNS) | set(DROPPED_BRONZE_COLUMNS)
    extra = [c for c in df.columns if c not in known]
    if extra:
        raise ValueError(
            f"{label}: unexpected bronze column(s) {extra}. Add to "
            f"DROPPED_BRONZE_COLUMNS or transform them explicitly."
        )


# =============================================================================
# Per-file transform (both eras share one shape)
# =============================================================================


def _validate_era2_constants(df: pl.DataFrame, year: int) -> None:
    """Hard-stop if Era 2's constant #RPT_NAME column carries unexpected values.

    Anything other than "HS Completer Credentials" means rows from a different
    GOSA report are mixed into this topic's bronze and must be analyzed, not
    silently kept.
    """
    rpt_names = df["#RPT_NAME"].drop_nulls().unique().to_list()
    if rpt_names != [ERA2_REPORT_NAME]:
        raise ValueError(
            f"era_2_with_rpt_name {year}: unexpected #RPT_NAME values {rpt_names}"
        )


def _map_demographics(df: pl.DataFrame, manifest: TransformManifest) -> pl.DataFrame:
    """Map LABEL_LVL_5_CD to the canonical ``demographic`` column.

    The bare bronze "Asian" label is remapped topic-locally to the combined
    "Asian/Pacific Islander" bucket BEFORE the shared normalization: bronze
    has only 6 race buckets, no separate Pacific Islander row anywhere, and
    the §5b math test is exact (race-bucket counts sum to the Total in all
    6,369 complete groups), proving Pacific Islanders are folded in. The
    shared alias then canonicalizes to ``asian_pacific_islander``.
    """
    df = df.with_columns(
        pl.when(pl.col("LABEL_LVL_5_CD") == "Asian")
        .then(pl.lit("Asian/Pacific Islander"))
        .otherwise(pl.col("LABEL_LVL_5_CD"))
        .alias("_demographic_remapped")
    ).with_columns(
        normalize_demographic_column("_demographic_remapped").alias("demographic")
    )
    # Record the effective slice of the shared alias map — only the aliases
    # this file's labels actually hit — with the ASIAN entry overridden to
    # reflect the topic-local combined-bucket remap actually applied. The raw
    # pre-remap series is passed so bronze_values_seen records "Asian".
    observed_upper = {
        str(v).strip().upper()
        for v in df["LABEL_LVL_5_CD"].drop_nulls().unique().to_list()
    }
    effective_map = {
        k: v for k, v in DEMOGRAPHIC_ALIASES.items() if k in observed_upper
    }
    if "ASIAN" in effective_map:
        effective_map["ASIAN"] = "asian_pacific_islander"
    manifest.record_categorical(
        column="demographic",
        map_dict=effective_map,
        bronze_series=df["LABEL_LVL_5_CD"],
        gold_series=df["demographic"],
    )
    return df.drop("_demographic_remapped")


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame:
    """Read one bronze file, detect its era, and transform it to gold shape.

    Year resolution: every file carries exactly one LONG_SCHOOL_YEAR value
    (``YYYY-YY``) whose ending year must agree with the filename year, so a
    misnamed file cannot silently mislabel a whole year.

    Args:
        path: Bronze file path.
        manifest: Manifest for read-loss / file / bronze-count / categorical
            recording.

    Returns:
        Gold-shaped DataFrame with STANDARD_COLUMNS.
    """
    # All-string read: geography codes keep leading zeros and the ALL
    # sentinels are never schema-inference casualties; TFS/blank suppression
    # arrives as NULL (read_bronze_file's suppression-aware null list).
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
    _reject_unexpected_columns(df, f"{era} {path.name}")
    if era == "era_2_with_rpt_name":
        _validate_era2_constants(df, filename_year)

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

    # Detail level from the geography sentinels (bronze has no detail-level
    # column): ALL+ALL -> state; code+ALL -> district; code+code -> school.
    # The (ALL, code) combination never occurs — guarded below so a new
    # bronze quirk fails loudly instead of being silently misclassified.
    district_clean = pl.col("SCHOOL_DSTRCT_CD").str.strip_chars()
    school_clean = pl.col("INSTN_NUMBER").str.strip_chars()
    bad_combo = df.filter(
        (district_clean == GEOGRAPHY_SENTINEL) & (school_clean != GEOGRAPHY_SENTINEL)
    ).height
    if bad_combo:
        raise ValueError(
            f"{path.name}: {bad_combo} row(s) with district=ALL but a "
            f"concrete school code — unknown detail-level shape"
        )
    df = df.with_columns(
        pl.when(
            (district_clean == GEOGRAPHY_SENTINEL)
            & (school_clean == GEOGRAPHY_SENTINEL)
        )
        .then(pl.lit("state"))
        .when(school_clean == GEOGRAPHY_SENTINEL)
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .alias("detail_level")
    )

    # Demographics: topic-local combined-bucket remap + shared normalization.
    df = _map_demographics(df, manifest)

    # credential_type: explicit map (punctuation-bearing labels); unmapped
    # values fall through to the manifest sentinel so write() raises with the
    # offending label listed instead of crashing mid-pipeline.
    df = df.with_columns(
        pl.col("LABEL_LVL_1_DESC")
        .replace_strict(CREDENTIAL_TYPE_MAP, default="99999999")
        .alias("credential_type")
    )
    manifest.record_categorical(
        column="credential_type",
        map_dict=CREDENTIAL_TYPE_MAP,
        bronze_series=df["LABEL_LVL_1_DESC"],
        gold_series=df["credential_type"],
    )

    # completer_type: two stable values across all years.
    df = df.with_columns(
        pl.col("COMPLETER_TYPE")
        .replace_strict(COMPLETER_TYPE_MAP, default="99999999")
        .alias("completer_type")
    )
    manifest.record_categorical(
        column="completer_type",
        map_dict=COMPLETER_TYPE_MAP,
        bronze_series=df["COMPLETER_TYPE"],
        gold_series=df["completer_type"],
    )

    # Geography keys: ALL sentinels -> NULL (never carried into gold);
    # zfill pads 3-digit district / 4-digit school codes and passes 7-digit
    # state-charter codes through unchanged (never truncate).
    # Metrics: counts via the exact Float64->Int64 hop; the 0-100 source
    # percentage is divided by 100 onto the 0-1 proportion scale (§4).
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
        _to_int_expr("PROGRAM_TOTAL").alias("num_completers"),
        (_to_float_expr("PROGRAM_PERCENT") / 100.0).alias("pct_of_credential_type"),
    )

    return df.select(STANDARD_COLUMNS)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for high_school_completers."""
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
    # mean an alias/normalization bug and must raise, not be deduped away.
    # (9 bronze demographic labels map to 9 distinct canonical keys, so no
    # subgroup collisions exist for aggregate_demographic_collisions to fix;
    # this guard would catch any future label drift.)
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: each bronze file is a distinct school year with no overlap,
    # and the per-file grain is unique (verified: 0 duplicate key groups in
    # any of the 14 files), so no duplicates are expected; prefer the row
    # with a reported (non-null, larger) num_completers over a suppressed
    # placeholder as the safety net.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=[
            "year",
            "district_code",
            "school_code",
            "demographic",
            "completer_type",
            "credential_type",
        ],
        district_keys=[
            "year",
            "district_code",
            "demographic",
            "completer_type",
            "credential_type",
        ],
        state_keys=["year", "demographic", "completer_type", "credential_type"],
        sort_col="num_completers",
    )

    # 4. Geography nulling (shared domain rules). No §4b masks: the full
    # bronze scan found no impossible values (see module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. Suppression NULL rates are heavy (~65-90% of rows,
    # rising gradually as GOSA tightened suppression) — bronze-real, and the
    # per-year drift stays under the spike threshold.
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
            "Number of Georgia public high-school completers by credential "
            "type (General Education Diplomas, Diplomas with College Prep "
            "Endorsements, Diplomas with Vocational Endorsements, Diplomas "
            "with Both College Prep and Vocational Endorsements, Special "
            "Education Diplomas, Certificates of Attendance) and completer "
            "type (graduates vs. other completers), broken out by 9 "
            "demographic subgroups (gender, race/ethnicity, and the "
            "all-students total), with each demographic's share of the "
            "credential's completers. School, district, and state levels, "
            "school years 2010-11 through 2023-24, published by GOSA."
        ),
        title="High School Completers",
        summary=(
            "Counts of Georgia high school completers by diploma or "
            "certificate type, by school, district, and state and "
            "demographic subgroup, 2011-2024."
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
                "example": "0390",
                "description": (
                    "GOSA school code, zero-padded to 4 characters (composite "
                    "FK to schools dimension with district_code; not globally "
                    "unique on its own). The 2011, 2018, 2019, and 2020 "
                    "source files mix 3- and 4-character codes; the transform "
                    "normalizes all years to 4 characters. NULL on district- "
                    "and state-level rows."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "all",
                "validValues": DEMOGRAPHIC_VALUES,
                "short_description": (
                    "Demographic subgroup: all students, gender, or one of six "
                    "race/ethnicity buckets (Asian is combined Asian/Pacific "
                    "Islander)."
                ),
                "description": (
                    "Demographic subgroup (FK to the global demographics "
                    "dimension): the all-students total, gender (male, "
                    "female), and six race/ethnicity buckets. Race uses the "
                    "combined asian_pacific_islander key (pre-1997 OMB "
                    "convention): the source publishes a bare 'Asian' label "
                    "with no separate Pacific Islander row, and the six race "
                    "buckets sum exactly to the Total in every fully "
                    "published group, so Pacific Islanders are folded in, "
                    "never dropped. 'all' is the unfiltered total and "
                    "overlaps every other value; subgroups are mutually "
                    "exclusive only within their own category (race, gender)."
                ),
            },
            {
                "name": "completer_type",
                "type": "string",
                "nullable": False,
                "example": "graduates",
                "validValues": sorted(set(COMPLETER_TYPE_MAP.values())),
                "short_description": (
                    "High-level cohort: graduates (the four diploma credentials) "
                    "vs. other_completers (special-ed diplomas and certificates "
                    "of attendance)."
                ),
                "description": (
                    "High-level completer cohort: 'graduates' covers the four "
                    "diploma credentials (general education, college prep, "
                    "vocational, both); 'other_completers' covers Special "
                    "Education Diplomas and Certificates of Attendance "
                    "(students who did not meet the full diploma "
                    "course/assessment criteria). Functionally determined by "
                    "credential_type (each credential belongs to exactly one "
                    "completer_type; enforced by a quality check). NOT the "
                    "denominator of pct_of_credential_type — that metric's "
                    "denominator is the single credential's total."
                ),
            },
            {
                "name": "credential_type",
                "type": "string",
                "nullable": False,
                "example": "general_education_diplomas",
                "validValues": sorted(set(CREDENTIAL_TYPE_MAP.values())),
                "short_description": (
                    "Specific credential earned: general-education, college-prep, "
                    "vocational, or both diplomas, special-ed diplomas, or "
                    "certificates of attendance."
                ),
                "description": (
                    "Specific credential earned. Six values from 2012 "
                    "onward; the 2010-11 school year (year=2011) predates "
                    "'general_education_diplomas' and carries only the other "
                    "five. From 2012 onward Georgia phased out endorsement "
                    "diplomas, so general_education_diplomas dominates "
                    "Graduates counts in later years."
                ),
            },
            {
                "name": "num_completers",
                "key_metric": True,
                "type": "int64",
                "unit": "count",
                "short_description": (
                    "Number of completers in this demographic who earned this "
                    "credential during the school year; NULL means GOSA "
                    "suppressed a small cell, not zero."
                ),
                "example": 114359,
                "null_meaning": (
                    "Suppressed by GOSA (small cell). Blank cells in the "
                    "2011-2021 sources and/or 'TFS' (Too Few Students) "
                    "literals in 2011, 2018-2020, and 2022-2024 — all become "
                    "NULL."
                ),
                "description": (
                    "Number of completers in this demographic who earned "
                    "this credential during the school year at this "
                    "school/district/state. Literal 0 is a real published "
                    "value (appears only in 2012-2017 and 2021-2022); NULL "
                    "is suppression. In 2023-2024 every published count is "
                    ">= 10; earlier years publish smaller values."
                ),
            },
            {
                "name": "pct_of_credential_type",
                "type": "float64",
                "unit": "proportion",
                "example": 0.488,
                "null_meaning": (
                    "Suppressed by GOSA. In 2011, 2018-2020, and 2023-2024 "
                    "the source publishes this share for some rows whose "
                    "num_completers is suppressed, so it can be non-NULL "
                    "while num_completers is NULL — never the reverse."
                ),
                "description": (
                    "Share of the credential's completers who belong to this "
                    "demographic — a demographic-within-credential share on "
                    "the 0-1 scale (source publishes 0-100 with one decimal; "
                    "divided by 100). The denominator is the credential's "
                    "own demographic='all' total at the same geography, NOT "
                    "the completer_type cohort total: rows with "
                    "demographic='all' are always exactly 1.0 where "
                    "published, gender pairs sum to ~1, and the six race "
                    "buckets sum to ~1 within a credential (all pinned as "
                    "quality checks). Credentials do NOT sum to 1 within a "
                    "completer_type."
                ),
            },
        ],
        source="GOSA",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        limitations=(
            "Suppressed cells are NULL (not zero): GOSA suppresses small "
            "cells, blanking ~65-90%% of num_completers values depending on "
            "the year (suppression tightened over time), and even some "
            "state-level cells (e.g. the phased-out endorsement-diploma "
            "credentials in recent years) — school-level analyses should "
            "expect sparse coverage, and summing only published subgroup "
            "counts undercounts true totals. pct_of_credential_type is a "
            "demographic composition share (demographic within credential), "
            "not a credential-mix share — do not sum it across credentials. "
            "State rows have NULL district_code and school_code; district "
            "rows have NULL school_code. The race axis uses the combined "
            "asian_pacific_islander bucket — not comparable row-for-row "
            "with split-convention topics without aggregating those topics' "
            "asian + pacific_islander rows at query time. year=2011 lacks "
            "the general_education_diplomas credential (it did not exist "
            "yet)."
        ),
        notes=[
            (
                "Suppression representation varies by year and all forms "
                "become NULL: 2011 has 9,073 rows blank in both metrics "
                "plus 10,339 TFS counts with a published percent; "
                "2012-2017 and 2021 use blank cells only (both metrics "
                "co-suppressed); 2018-2020 use blanks plus ~2.1-2.3k TFS "
                "counts with a published percent; 2022 uses TFS only (both "
                "metrics co-suppressed); 2023-2024 use TFS only with "
                "~1.9k count-suppressed rows keeping a published percent. "
                "In every year a published num_completers implies a "
                "published pct_of_credential_type (pinned as a quality "
                "check)."
            ),
            (
                "pct_of_credential_type semantics (verified exactly against "
                "bronze): the row's num_completers divided by the "
                "credential's demographic='all' num_completers at the same "
                "geography. E.g. 2022 state General Education Diplomas: "
                "Male 55,853 / 114,359 = 48.8%% -> 0.488. demographic='all' "
                "rows are exactly 1.0 wherever published."
            ),
            (
                "Asian/Pacific Islander is the combined pre-1997 OMB bucket "
                "(asian_pacific_islander), per data-cleaning-standards §5b: "
                "the source has only six race buckets and no separate "
                "Pacific Islander row, and race-bucket counts sum EXACTLY "
                "to the Total in all 6,369 fully published groups across "
                "all 14 years. The split asian / pacific_islander keys are "
                "never emitted."
            ),
            (
                "Credential evolution: 'General Education Diplomas' did not "
                "exist in the 2010-11 school year, so year=2011 has 5 "
                "credentials instead of 6. From 2012 onward Georgia moved "
                "to a single diploma, so the three endorsement-diploma "
                "credentials fade to zero/suppressed in later years (by "
                "2022-2024 they are TFS even at the state level)."
            ),
            (
                "Literal 0 counts are real published values, not "
                "suppression; they appear only in 2012-2017 and 2021-2022."
            ),
            (
                "ID padding: the 2011, 2018, 2019, and 2020 source files "
                "mix 3- and 4-character school codes; the transform "
                "zero-pads to 4 characters so school_code joins to the "
                "schools dimension are consistent across years."
            ),
            (
                "Names (SCHOOL_DSTRCT_NM, INSTN_NAME) live in the dimension "
                "tables; LABEL_SORT_ORDER (a presentation sort key, "
                "one-to-one with credential_type) and Era 2's constant "
                "#RPT_NAME column are dropped."
            ),
        ],
        quality_checks=[
            {
                "name": "credential_type_determines_completer_type",
                "description": (
                    "Functional dependency: each credential_type maps to "
                    "exactly one completer_type (graduates = the four "
                    "diploma credentials; other_completers = Special "
                    "Education Diplomas + Certificates of Attendance). "
                    "Independent enum checks on the two columns would "
                    "otherwise allow an invalid pairing."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT credential_type FROM {object} "
                    "GROUP BY credential_type "
                    "HAVING COUNT(DISTINCT completer_type) > 1)"
                ),
                "mustBe": 0,
            },
            {
                "name": "count_present_implies_pct_present",
                "description": (
                    "In every bronze year a published num_completers comes "
                    "with a published pct_of_credential_type (verified: 0 "
                    "violations across all 14 files); the reverse does not "
                    "hold (percent survives count suppression in 2011, "
                    "2018-2020, 2023-2024)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "num_completers IS NOT NULL "
                    "AND pct_of_credential_type IS NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "all_demographic_share_is_one",
                "description": (
                    "pct_of_credential_type is the demographic's share of "
                    "the credential's total, so demographic='all' rows are "
                    "exactly 100%% (1.0) wherever published — the source "
                    "publishes them as the literal 100 (verified: 0 "
                    "violations across all 14 files)."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "demographic = 'all' "
                    "AND pct_of_credential_type IS NOT NULL "
                    "AND ABS(pct_of_credential_type - 1.0) > 1e-9"
                ),
                "mustBe": 0,
            },
            {
                "name": "gender_count_partition_exact",
                "description": (
                    "male + female num_completers equals the 'all' total "
                    "exactly in every group where all three are published "
                    "(verified: 11,214 complete groups across all years, 0 "
                    "violations). Pivot with conditional aggregation — "
                    "GROUP BY treats NULL geography keys as equal, scoping "
                    "each detail level correctly."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, school_code, "
                    "completer_type, credential_type, "
                    "MAX(CASE WHEN demographic = 'male' "
                    "THEN num_completers END) AS m, "
                    "MAX(CASE WHEN demographic = 'female' "
                    "THEN num_completers END) AS f, "
                    "MAX(CASE WHEN demographic = 'all' "
                    "THEN num_completers END) AS t "
                    "FROM {object} "
                    "GROUP BY year, district_code, school_code, "
                    "completer_type, credential_type"
                    ") WHERE m IS NOT NULL AND f IS NOT NULL "
                    "AND t IS NOT NULL AND m + f <> t"
                ),
                "mustBe": 0,
            },
            {
                "name": "race_count_partition_exact",
                "description": (
                    "The six race buckets partition each credential's "
                    "completers: their num_completers values sum exactly "
                    "to the 'all' total in every group where all six and "
                    "the total are published (verified: 6,369 complete "
                    "groups across all years, 0 violations — the §5b math "
                    "test proving the combined Asian/Pacific Islander "
                    "convention)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, school_code, "
                    "completer_type, credential_type, "
                    f"SUM(CASE WHEN demographic IN ({race_list}) "
                    "THEN num_completers END) AS race_sum, "
                    f"COUNT(CASE WHEN demographic IN ({race_list}) "
                    "AND num_completers IS NOT NULL THEN 1 END) AS race_nn, "
                    "MAX(CASE WHEN demographic = 'all' "
                    "THEN num_completers END) AS t "
                    "FROM {object} "
                    "GROUP BY year, district_code, school_code, "
                    "completer_type, credential_type"
                    ") WHERE race_nn = 6 AND t IS NOT NULL "
                    "AND race_sum <> t"
                ),
                "mustBe": 0,
            },
            {
                "name": "gender_pct_partition_sums_to_one",
                "description": (
                    "male + female pct_of_credential_type sums to 1.0 "
                    "within rounding (source rounds each share to one "
                    "decimal on the 0-100 scale, so the pair can be off by "
                    "up to 0.001; observed max deviation is exactly 0.001 "
                    "across all years) in every group where both are "
                    "published."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, school_code, "
                    "completer_type, credential_type, "
                    "MAX(CASE WHEN demographic = 'male' "
                    "THEN pct_of_credential_type END) AS m, "
                    "MAX(CASE WHEN demographic = 'female' "
                    "THEN pct_of_credential_type END) AS f "
                    "FROM {object} "
                    "GROUP BY year, district_code, school_code, "
                    "completer_type, credential_type"
                    ") WHERE m IS NOT NULL AND f IS NOT NULL "
                    "AND ABS(m + f - 1.0) > 0.002"
                ),
                "mustBe": 0,
            },
            {
                "name": "race_pct_partition_sums_to_one",
                "description": (
                    "The six race buckets' pct_of_credential_type values "
                    "sum to 1.0 within rounding (six one-decimal roundings "
                    "on the 0-100 scale allow up to 0.003 deviation; "
                    "observed max is 0.002 across all years) in every group "
                    "where all six are published."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, school_code, "
                    "completer_type, credential_type, "
                    f"SUM(CASE WHEN demographic IN ({race_list}) "
                    "THEN pct_of_credential_type END) AS race_sum, "
                    f"COUNT(CASE WHEN demographic IN ({race_list}) "
                    "AND pct_of_credential_type IS NOT NULL THEN 1 END) "
                    "AS race_nn "
                    "FROM {object} "
                    "GROUP BY year, district_code, school_code, "
                    "completer_type, credential_type"
                    ") WHERE race_nn = 6 AND ABS(race_sum - 1.0) > 0.004"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
