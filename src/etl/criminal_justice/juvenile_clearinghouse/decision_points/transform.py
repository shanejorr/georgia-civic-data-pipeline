"""Transform bronze decision_points files into a gold county/year fact table.

Source: Georgia Juvenile Justice Data Clearinghouse (juveniledata.georgiacourts.gov)
"Raw Data" downloads for the Juvenile Justice Decision Points dashboard —
decision-point counts defined with the US DOJ under the JJDP Act.

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Only Raw Data 1 (youth-level, statewide, 2010-2025) is ingested.** The
  bronze dir also holds Raw Data 2, a county/year/month case-flow aggregate
  covering only a growing 65-county self-reporting subset (44-62 counties per
  year, 2005-2025) with a different metric set and universe. The structure doc
  is explicit: the two files measure different things at different grains and
  must not be unioned; one topic emits one fact table/contract, so Raw Data 2
  is excluded here (logged + recorded on the manifest as an excluded file) and
  should ship as its own sibling topic (working name: a case-flow topic under
  juvenile_clearinghouse) once its bronze is split out.
- **PII rule: youth-level rows never reach gold.** Raw Data 1 is one row per
  pseudonymized juvenile (NEWJUVID) x year x county x court type x
  active/terminated flag. The transform aggregates to county/year (x
  demographic) cells; NEWJUVID is consumed to derive distinct-youth counts and
  is never exported. No additional small-cell suppression is applied: the
  source itself publishes the pseudonymized youth-level file, so county/year
  aggregates are strictly less disclosive than the public source.
- **Demographic axes.** Race (White/Black/AmInd/Asian/Hispanic/Other) and
  gender (MALE/FEMALE) are youth attributes in bronze. Gold packs three
  overlapping axes into `demographic` per project convention: `all` (every
  youth), one row per race value, one row per gender value. Consumers filter
  to one axis; the `all` row is the unfiltered total.
- **Asian / Pacific Islander (S5b).** The source has no Pacific Islander
  bucket anywhere and no total rows, so the S5b math test is inapplicable.
  Because both files carry an explicit `Other` catch-all and the data is
  modern (2010+), bare `Asian` is mapped to `asian` per the structure doc's
  recommendation, with the caveat documented in the contract (flagged for
  data review). `Hispanic` is a mutually exclusive race bucket per the source
  ("All races except Hispanic are populations not considered Hispanic").
- **Race/gender inconsistencies (documented, preserved).** The source reports
  a small number of youths under more than one race or gender across row
  segments — entirely confined to 2025 in the current publication (228
  multi-race and 247 multi-gender youths, ~1.8% of 2025 youths; zero in
  2010–2024). In 2010–2024 race/gender num_youth partitions the 'all' row
  exactly; in 2025 race/gender num_youth sums ~2% above it (a youth reported
  under two race values is counted once in each bucket). Summed event counts
  partition exactly in every year (each bronze row carries exactly one race
  and one gender). The partition quality checks are authored on an event
  count (num_offenses), not num_youth.
- **Court Type (D/I/S) is summed over.** The single-letter codes are
  undocumented at the source (verified against the definitions page
  2026-07-02). The structure doc sanctions either keeping the raw letters or
  summing over the axis; the axis is dropped so gold never serves codes whose
  semantics cannot be documented. Re-add as a categorical if the Clearinghouse
  confirms the code meanings.
- **Active/terminated flag is dropped.** The (1)ACTIVE-(0)TERMINATED flag is
  a publication-time case status, not a fact about the data year: its share
  is 0.000 for 2010-2014 rows and rises monotonically to ~0.42 for 2024-2025
  rows in the 2026 publication. Serving it as a per-year metric would read as
  "active youths in <year>" and mislead. (It is part of the bronze row grain;
  dropping the column loses no event counts — sums and distinct-youth counts
  are unaffected.)
- **Secure placement flags -> distinct-youth counts.** Secure Detention
  (RYDC) / Secure Confinement (YDC) are 0/1 indicators (mutually exclusive
  when non-null; NULL = no new secure placement, which is a real zero for
  aggregation, not suppression). Gold counts distinct youths with flag == 1
  per cell. Source coverage collapses in 2023-2025 (62/81/72 flagged rows
  statewide vs 200-500 in earlier years) — documented as possibly incomplete
  in the contract; the values are preserved as published (not provably
  impossible, so not a S4b case).
- **OUT OF STATE rows (3,300 youth-years, ~1%%).** Raw Data 1's County Name
  carries all 159 GA counties plus `OUT OF STATE`. Those rows cannot carry a
  county FIPS and are excluded from county-level rows (recorded via
  record_filtered) but are included in the state-level rollup, so statewide
  totals cover the full published universe.
- **State rollup is synthesized from the youth-level microdata.** Bronze has
  no state rows. Unlike education topics (where re-aggregation would
  undercount suppressed cells), this source has NO suppression and gold is
  built from the complete youth-level file, so the state rows are exact —
  and they preserve information a consumer cannot reconstruct from county
  rows: statewide distinct-youth counts (a youth appearing in multiple
  counties is counted once statewide) and the OUT OF STATE contribution.
- **Duplicate handling.** At the bronze grain (NEWJUVID x year x county x
  court type x active flag) 351 key groups repeat: 38 byte-identical
  duplicate rows are dropped (logged + record_filtered — republished repeats,
  not data) and the remaining same-key rows with different metric values are
  the same youth reported in segments, which the county/year SUM aggregation
  absorbs, per the structure doc ("Aggregation by SUM is the safe reduction").
- **Dedup tie-break.** A single bronze file feeds gold and every cell is
  produced by one group_by, so post-aggregation duplicates are impossible by
  construction; `deduplicate_by_levels(sort_col="num_youth")` remains as the
  documented safety net (prefer the fuller row) should a future refresh add
  an overlapping file. The collision guard runs first and would surface any
  divergent duplicate as a hard error rather than letting dedup pick a winner.
- **No S4b masks.** All metrics are non-negative integer counts derived by
  summation/distinct-counting over clean bronze integers (verified: no
  negatives, no nulls, funnel sanity `adjudications <= offenses` and
  `petitions <= offenses` holds on every bronze row); no impossible values
  exist to NULL.
- **No suppression.** The source publishes clean integers with no markers
  (structure doc), so `suppressed_to_null=False` and gold metric columns are
  fully non-null; zeros are real zeros.
"""

import logging
from pathlib import Path

import polars as pl

from src.utils.crosswalks import add_county_fips
from src.utils.demographics import DEMOGRAPHIC_ALIASES, normalize_demographic_column
from src.utils.metadata import write_data_dictionary
from src.utils.readers import list_bronze_files, read_bronze_file
from src.utils.transformers import (
    COUNTY_DETAIL_LEVEL_FILES,
    TransformManifest,
    assert_no_natural_key_collisions,
    deduplicate_by_levels,
    detect_era_by_columns,
    export_to_parquet,
    harmonize_columns,
    null_aggregate_geography,
    validate_output,
)
from src.utils.validators import (
    CRIMINAL_JUSTICE_DOMAIN_CONFIG,
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

TOPIC = "decision_points"
BRONZE_DIR = Path("data/bronze/criminal_justice/juvenile_clearinghouse/decision_points")
GOLD_DIR = Path("data/gold/criminal_justice/decision_points")
SOURCE_URL = "https://juveniledata.georgiacourts.gov/dashboards-reports/"

# Era detection by column signature (per file, not per year — each CSV keeps
# one schema across all its years). Most-specific-first ordering is moot here
# because the signatures are disjoint.
ERA_SIGNATURES: dict[str, list[str]] = {
    "raw_data_1_youth_level": ["NEWJUVID", "Period Year", "Court Type"],
    "raw_data_2_case_flow": ["County", "Year", "Month", "Case Type"],
}

# Bronze event-count column -> gold column, in gold output order (funnel-ish:
# offenses -> diversion -> petition -> adjudication -> disposition -> transfer).
# Exact header strings are load-bearing (verified against the 2026-06 file).
EVENT_SUM_COLUMNS: dict[str, str] = {
    "Number of offenses": "num_offenses",
    "Diversions (all types)": "num_diversions",
    "Petitions": "num_petitions",
    "Delinquent Adjudications (Misd. And Felony)": "num_delinquent_adjudications",
    "Unique Adjudication Date Count": "num_adjudication_dates",
    "Probation orders": "num_probation_orders",
    "Commitments orders": "num_commitment_orders",
    "Superior Court Sentenced": "num_superior_court_sentences",
}

# 0/1 indicator flags (NULL = no new secure placement) -> distinct-youth counts.
RYDC_COLUMN = "Secure Detention (RYDC)"
YDC_COLUMN = "Secure Confinement (YDC)"

# Bronze columns consumed but not summed (grain / attributes / dropped axes).
RAW1_REQUIRED_COLUMNS: list[str] = [
    "NEWJUVID",
    "Period Year",
    "County Name",
    "Court Type",
    "Gender",
    "Race Value",
    *EVENT_SUM_COLUMNS.keys(),
    RYDC_COLUMN,
    YDC_COLUMN,
    "(1)ACTIVE JUVENILE - (0)TERMINATED JUVENILE",
]

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "county_fips",
    "demographic",
    "num_youth",
    "num_offenses",
    "num_diversions",
    "num_petitions",
    "num_delinquent_adjudications",
    "num_adjudication_dates",
    "num_probation_orders",
    "num_commitment_orders",
    "num_superior_court_sentences",
    "num_secure_detention_youth",
    "num_secure_confinement_youth",
    "detail_level",
]

METRIC_COLUMNS: list[str] = [
    "num_youth",
    "num_offenses",
    "num_diversions",
    "num_petitions",
    "num_delinquent_adjudications",
    "num_adjudication_dates",
    "num_probation_orders",
    "num_commitment_orders",
    "num_superior_court_sentences",
    "num_secure_detention_youth",
    "num_secure_confinement_youth",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "county_fips": pl.Utf8,
    "demographic": pl.Utf8,
    **{c: pl.Int64 for c in METRIC_COLUMNS},
    "detail_level": pl.Utf8,
}

NATURAL_KEYS: list[str] = ["year", "county_fips", "demographic", "detail_level"]

# County Name value carried by youths handled by Georgia courts but not
# attributable to a Georgia county — excluded from county rows, included in
# the state rollup (see module docstring).
OUT_OF_STATE_LABEL = "OUT OF STATE"

# The race values gold can emit (used by the race-partition quality check;
# gender is male/female). Kept in one place so the check and the contract
# enum documentation cannot drift.
RACE_DEMOGRAPHICS: list[str] = [
    "asian",
    "black",
    "hispanic",
    "native_american",
    "other",
    "white",
]
GENDER_DEMOGRAPHICS: list[str] = ["female", "male"]


# =============================================================================
# Guards
# =============================================================================


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


def _assert_clean_casts(df: pl.DataFrame, columns: list[str], label: str) -> None:
    """Raise if a strict=False cast introduced NULLs into a zero-null column.

    The structure doc verifies every event-count column parses as clean Int64
    with zero nulls; a NULL after casting means the source format regressed
    (new suppression markers, stray text) and must be analyzed, not passed on.
    """
    for col in columns:
        n_null = df[col].null_count()
        if n_null:
            raise ValueError(
                f"{label}: {n_null} NULL(s) appeared casting '{col}' — "
                "bronze has zero nulls here; investigate the source format"
            )


def _assert_binary_flags(df: pl.DataFrame, columns: list[str], label: str) -> None:
    """Raise if a 0/1 indicator flag carries any value other than 0/1/NULL.

    The secure-placement columns are indicators, not counts; any other value
    would silently corrupt the distinct-youth flag counting semantics.
    """
    for col in columns:
        bad = df.filter(pl.col(col).is_not_null() & ~pl.col(col).is_in([0, 1]))
        if bad.height:
            raise ValueError(
                f"{label}: '{col}' carries non-binary value(s): "
                f"{bad[col].unique().to_list()[:5]}"
            )


# =============================================================================
# Raw Data 1 (youth-level) transform
# =============================================================================


def _drop_exact_duplicates(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Drop byte-identical duplicate rows (38 in the 2026-06 file), logged.

    Same-key rows with DIFFERENT metric values are intentionally kept — they
    are the same youth reported in segments within a year, and the county/year
    SUM aggregation absorbs them (structure doc "Row Grain"). Only exact
    repeats, which would double-count events under SUM, are removed.
    """
    before = df.group_by("year").len().rename({"len": "_before"})
    deduped = df.unique(maintain_order=True)
    if deduped.height == df.height:
        return df
    after = deduped.group_by("year").len().rename({"len": "_after"})
    per_year = before.join(after, on="year", how="left").with_columns(
        (pl.col("_before") - pl.col("_after").fill_null(0)).alias("_removed")
    )
    for row in per_year.filter(pl.col("_removed") > 0).sort("year").to_dicts():
        manifest.record_filtered(
            row["year"], row["_removed"], "byte_identical_duplicate_row"
        )
    logger.warning(
        "Dropped %d byte-identical duplicate youth-level row(s) before "
        "aggregation (republished repeats would double-count events under SUM)",
        df.height - deduped.height,
    )
    return deduped


def _record_demographic_mapping(df: pl.DataFrame, manifest: TransformManifest) -> None:
    """Record the demographic recode on the manifest (per skill rule 4.3a).

    Demographics use the shared DEMOGRAPHIC_ALIASES, never a topic-local map;
    the manifest records the EFFECTIVE slice — the aliases actually hit by the
    observed race + gender labels — which keeps map_used reviewable while
    preserving the unmapped guard (a label missing from the aliases stays out
    of the map and is counted as unmapped, which blocks the run).
    """
    bronze_series = pl.concat(
        [
            df["Race Value"].cast(pl.Utf8),
            df["Gender"].cast(pl.Utf8),
        ]
    )
    gold_series = pl.concat(
        [
            df.select(normalize_demographic_column("Race Value").alias("d"))["d"],
            df.select(normalize_demographic_column("Gender").alias("d"))["d"],
        ]
    )
    observed = bronze_series.drop_nulls().unique().to_list()
    effective_map = {
        label: DEMOGRAPHIC_ALIASES[label.strip().upper()]
        for label in observed
        if label.strip().upper() in DEMOGRAPHIC_ALIASES
    }
    manifest.record_categorical(
        column="demographic",
        map_dict=effective_map,
        bronze_series=bronze_series,
        gold_series=gold_series,
    )


def _resolve_county_fips(df: pl.DataFrame, manifest: TransformManifest) -> pl.DataFrame:
    """Join county FIPS by name; hard-stop on any unexpected unmatched name.

    All 159 Georgia county names in Raw Data 1 resolve against the global
    counties dimension; only OUT OF STATE is legitimately FIPS-less (state
    rollup only). Any other unmatched name means the crosswalk or the source
    changed and must be fixed via COUNTY_NAME_OVERRIDES, never silently NULLed.
    """
    df = add_county_fips(df, "County Name")
    unmatched = df.filter(
        pl.col("county_fips").is_null() & (pl.col("County Name") != OUT_OF_STATE_LABEL)
    )
    if unmatched.height:
        raise ValueError(
            "Unmatched county name(s) — add to COUNTY_NAME_OVERRIDES: "
            f"{unmatched['County Name'].unique().sort().to_list()}"
        )

    # Record the observed name -> FIPS mapping. OUT OF STATE is mapped to an
    # explicit non-FIPS marker so the manifest shows it handled deliberately
    # (excluded from county rows, kept in state rows) rather than unmapped.
    county_map = {
        row["County Name"]: row["county_fips"]
        for row in df.select("County Name", "county_fips")
        .unique()
        .drop_nulls("county_fips")
        .to_dicts()
    }
    county_map[OUT_OF_STATE_LABEL] = "state_rollup_only_no_county_fips"
    manifest.record_categorical(
        column="county_fips",
        map_dict=county_map,
        bronze_series=df["County Name"],
        gold_series=df["county_fips"],
    )
    return df


def _aggregation_exprs() -> list[pl.Expr]:
    """Cell-level aggregations: distinct youths, event sums, flagged youths.

    Distinct-youth counts use n_unique(NEWJUVID) — never a sum of rows —
    because a youth can appear on multiple rows per cell (court-type and
    active/terminated segments). n_unique over an empty/filtered set is 0,
    which is a real zero for this unsuppressed source.
    """
    return [
        pl.col("NEWJUVID").n_unique().alias("num_youth"),
        *[pl.col(src).sum().alias(dst) for src, dst in EVENT_SUM_COLUMNS.items()],
        pl.col("NEWJUVID")
        .filter(pl.col("_rydc") == 1)
        .n_unique()
        .alias("num_secure_detention_youth"),
        pl.col("NEWJUVID")
        .filter(pl.col("_ydc") == 1)
        .n_unique()
        .alias("num_secure_confinement_youth"),
    ]


def _aggregate_slices(
    base: pl.DataFrame, geo_cols: list[str], detail_level: str
) -> pl.DataFrame:
    """Aggregate one detail level across the three demographic slices.

    Emits `all` (every youth), per-race, and per-gender rows — three
    overlapping axes packed into `demographic` per project convention (§5a:
    within-axis values are mutually exclusive per bronze row; `all` overlaps
    everything). Grouping happens on the ALREADY-normalized demographic, so
    any labels aliasing to one canonical value are aggregated, not deduped.
    """
    frames = []
    for demo_expr in (
        pl.lit("all"),
        normalize_demographic_column("Race Value"),
        normalize_demographic_column("Gender"),
    ):
        frames.append(
            base.with_columns(demo_expr.alias("demographic"))
            .group_by(["year", *geo_cols, "demographic"])
            .agg(_aggregation_exprs())
        )
    out = pl.concat(frames).with_columns(pl.lit(detail_level).alias("detail_level"))
    if "county_fips" not in geo_cols:
        out = out.with_columns(pl.lit(None).cast(pl.Utf8).alias("county_fips"))
    return out


def _transform_youth_level(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Transform the Raw Data 1 youth-level file into county + state gold rows.

    Casts and guards the bronze columns, drops byte-identical repeats,
    resolves county FIPS, then aggregates youth-level rows to
    county/year/demographic and state/year/demographic cells. The Court Type
    and active/terminated axes are summed over (see module docstring), and
    NEWJUVID is consumed by the aggregation — no youth-level data leaves this
    function (PII rule).
    """
    _require_columns(df, RAW1_REQUIRED_COLUMNS, "raw_data_1")

    event_cols = list(EVENT_SUM_COLUMNS.keys())
    df = df.with_columns(
        pl.col("Period Year").cast(pl.Int32, strict=False).alias("year"),
        *[pl.col(c).cast(pl.Int64, strict=False).alias(c) for c in event_cols],
        pl.col(RYDC_COLUMN).cast(pl.Int64, strict=False).alias("_rydc"),
        pl.col(YDC_COLUMN).cast(pl.Int64, strict=False).alias("_ydc"),
    )
    _assert_clean_casts(df, ["year", *event_cols], "raw_data_1")
    _assert_binary_flags(df, ["_rydc", "_ydc"], "raw_data_1")

    # Per-year bronze accounting BEFORE any row removal.
    for row in df.group_by("year").len().sort("year").to_dicts():
        manifest.record_bronze(row["year"], row["len"])

    df = _drop_exact_duplicates(df, manifest)
    _record_demographic_mapping(df, manifest)
    df = _resolve_county_fips(df, manifest)

    # County rows exclude OUT OF STATE youths (no FIPS to key on); the state
    # rollup keeps them so statewide totals cover the full published universe.
    oos = df.filter(pl.col("county_fips").is_null())
    if oos.height:
        logger.info(
            "Excluding %d OUT OF STATE youth-year row(s) from county-level "
            "rows (kept in the state rollup)",
            oos.height,
        )
        for row in oos.group_by("year").len().sort("year").to_dicts():
            manifest.record_filtered(
                row["year"],
                row["len"],
                "out_of_state_rows_excluded_from_county_level_kept_in_state",
            )

    counties = _aggregate_slices(
        df.filter(pl.col("county_fips").is_not_null()),
        geo_cols=["county_fips"],
        detail_level="county",
    )
    # State rows aggregate the FULL youth-level file (all counties + OUT OF
    # STATE): exact, because the source is unsuppressed microdata, and they
    # carry statewide distinct-youth counts a consumer cannot rebuild from
    # county rows (a youth in several counties counts once statewide).
    states = _aggregate_slices(df, geo_cols=[], detail_level="state")

    logger.info(
        "Aggregated %d youth-level rows into %d county and %d state cells",
        df.height,
        counties.height,
        states.height,
    )
    return pl.concat(
        [counties.select(STANDARD_COLUMNS), states.select(STANDARD_COLUMNS)]
    )


# =============================================================================
# File routing
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read one bronze file, detect its schema, and route or exclude it.

    Raw Data 1 (youth-level) feeds the fact table. Raw Data 2 (the 65-county
    case-flow aggregate) is recorded on the manifest as an excluded file and
    skipped — see the module docstring for the one-topic-one-table rationale.
    All-string read (infer_schema_length=0) per skill rule 4.3b: both files
    are cast explicitly so schema inference can never mis-type a column.
    """
    df, loss = read_bronze_file(path, return_loss=True, infer_schema_length=0)
    # Defensive header cleanup (both files start with a UTF-8 BOM, which the
    # reader strips; stray padding would otherwise break exact-name matching).
    df = df.rename({c: c.strip() for c in df.columns if c != c.strip()})

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{path.name}: no era signature matched columns {df.columns}")

    if era == "raw_data_2_case_flow":
        # Excluded from this topic (different universe/grain — see module
        # docstring). record_file (not record_bronze) so the manifest shows
        # the file was seen and deliberately excluded, without polluting the
        # per-year bronze-vs-gold accounting of the ingested file.
        year_max = int(df["Year"].cast(pl.Int32).max())
        manifest.record_file(
            path, year_max, "raw_data_2_case_flow_EXCLUDED", df.height, df.columns
        )
        logger.warning(
            "EXCLUDED %s (%d rows): county/month case-flow aggregate for a "
            "65-county self-reporting subset — a different universe and grain "
            "from the youth-level file; candidate separate topic (not unioned "
            "per bronze-data-structure.md ETL #1)",
            path.name,
            df.height,
        )
        return None

    year_max = int(df["Period Year"].cast(pl.Int32).max())
    # The file spans 2010-2025 internally (filename carries only the upload
    # month); record_file's single year slot gets the max data year.
    manifest.record_read_loss(
        year_max, path.name, loss["raw_rows"], loss["parsed_rows"]
    )
    manifest.record_file(path, year_max, era, df.height, df.columns)
    logger.info("Processing %s as %s (%d rows)", path.name, era, df.height)
    return _transform_youth_level(df, manifest)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for decision_points."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file (read-loss accounted per file).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR):
        result = transform_file(path, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize columns/dtypes and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)
    logger.info("Combined %d gold-shaped rows", combined.height)

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean an aggregation bug and must raise, not be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: one bronze file feeds gold and every cell comes from one
    # group_by, so duplicates are impossible by construction; sort_col
    # "num_youth" is the documented safety net (prefer the fuller row) should
    # a future refresh introduce an overlapping file.
    combined = deduplicate_by_levels(
        combined,
        {
            "county": ["year", "county_fips", "demographic"],
            "state": ["year", "demographic"],
        },
        sort_col="num_youth",
    )

    # 4. Geography nulling (shared domain rules). No §4b masks apply — all
    # metrics are counts derived from clean bronze integers (module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=CRIMINAL_JUSTICE_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. Metrics are fully non-null (no suppression), so any
    # null-rate spike would indicate a transform regression.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(combined, required_non_null=["year", "detail_level", "demographic"])

    # 5. Manifest stats on the FINAL DataFrame, then export.
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(
        combined,
        GOLD_DIR,
        STANDARD_COLUMNS,
        detail_level_files=COUNTY_DETAIL_LEVEL_FILES,
    )
    manifest.write(GOLD_DIR)

    # 6. Contract from the in-code column declaration.
    _emit_contract(
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


def _emit_contract(year_range: tuple[int, int]) -> None:
    """Emit the ODCS contract via ``write_data_dictionary``.

    The column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level`` — the contract's properties (and the validator's schema
    check) follow it.
    """
    demographic_values = sorted(["all", *RACE_DEMOGRAPHICS, *GENDER_DEMOGRAPHICS])
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Juvenile-justice decision-point counts for Georgia counties, "
            "aggregated from the Georgia Juvenile Justice Data Clearinghouse's "
            "pseudonymized youth-level file: distinct youths with "
            "juvenile-court contact and their counts of offenses, diversions, "
            "petitions, delinquent adjudications, probation orders, commitment "
            "orders, superior-court sentences, and new secure placements, by "
            "county, race, and gender, 2010-2025. Decision points are defined "
            "with the US DOJ under the JJDP Act."
        ),
        title="Juvenile Justice Decision Points",
        summary=(
            "Youths in Georgia's juvenile courts and key decision-point counts "
            "(offenses, diversions, petitions, adjudications, commitments) by "
            "county, race, and gender, 2010-2025."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Calendar year of the juvenile-court contact (source "
                    "'Period Year'; not a fiscal or school year)."
                ),
            },
            {
                "name": "county_fips",
                "type": "string",
                "example": "13121",
                "description": (
                    "5-digit county FIPS code (state prefix 13) of the Georgia "
                    "county reporting the youth's court contact; FK to the "
                    "counties dimension. NULL on state-level rows. Youths "
                    "labeled OUT OF STATE by the source (~1%% of youth-years) "
                    "carry no county and appear only in the state rollup."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "all",
                "validValues": demographic_values,
                "short_description": (
                    "Youth group the row covers: every youth (all), one race "
                    "group, or one gender group."
                ),
                "description": (
                    "Demographic slice. Three overlapping axes are packed into "
                    "this column: 'all' (every youth), race "
                    "(asian/black/hispanic/native_american/other/white), and "
                    "gender (male/female) — filter to one axis; summing across "
                    "axes double-counts. Race values follow the source's "
                    "6-bucket scheme: hispanic is a mutually exclusive bucket "
                    "(other races exclude Hispanic youths), and no Pacific "
                    "Islander bucket exists anywhere in the source — bare "
                    "source 'Asian' is mapped to asian as published, with any "
                    "Pacific Islander youths most plausibly reported in the "
                    "explicit 'other' catch-all. The source reports a small "
                    "number of youths under more than one race or gender "
                    "across row segments — entirely confined to 2025 in the "
                    "current publication (228 multi-race and 247 multi-gender "
                    "youths, ~1.8% of 2025 youths; zero in 2010-2024). Such a "
                    "youth is counted once in each reported bucket, so in "
                    "2010-2024 race/gender num_youth partitions the 'all' row "
                    "exactly, while in 2025 it sums ~2% above it."
                ),
            },
            {
                "name": "num_youth",
                "type": "int64",
                "unit": "count",
                "key_metric": True,
                "example": 512,
                "short_description": (
                    "Distinct youths with juvenile-court contact in the "
                    "county, year, and demographic group."
                ),
                "description": (
                    "Distinct youths (pseudonymized source IDs) with "
                    "juvenile-court contact in the cell. NOT additive: a youth "
                    "with contact in two counties counts once in each county "
                    "but once statewide, so county rows generally sum above "
                    "the state row — though out-of-state youths (counted only "
                    "statewide) can reverse this, as in 2025; likewise never "
                    "sum across demographic values or "
                    "years. Every counted youth has at least one offense "
                    "(rows exist only where contact occurred), so "
                    "num_offenses >= num_youth in every cell."
                ),
            },
            {
                "name": "num_offenses",
                "type": "int64",
                "unit": "count",
                "example": 1024,
                "description": (
                    "Total offenses across the cell's youths in the year. "
                    "Event counts (this and the following columns) are sums "
                    "over youth-level rows and, unlike num_youth, partition "
                    "exactly across the race axis and across the gender axis."
                ),
            },
            {
                "name": "num_diversions",
                "type": "int64",
                "unit": "count",
                "example": 96,
                "description": (
                    "Diversions of all types (informal adjustment, abeyance, "
                    "diverted complaint withheld, mediation, nolle prosequi)."
                ),
            },
            {
                "name": "num_petitions",
                "type": "int64",
                "unit": "count",
                "example": 256,
                "description": "Petitioned cases (formal court filings).",
            },
            {
                "name": "num_delinquent_adjudications",
                "type": "int64",
                "unit": "count",
                "example": 128,
                "description": (
                    "Delinquent adjudications, misdemeanor and felony combined "
                    "(charge-level: one youth adjudicated on three charges "
                    "contributes 3)."
                ),
            },
            {
                "name": "num_adjudication_dates",
                "type": "int64",
                "unit": "count",
                "example": 100,
                "description": (
                    "Sum over youths of each youth's count of DISTINCT "
                    "adjudication dates (a youth adjudicated on three separate "
                    "dates contributes 3; multiple charges adjudicated the "
                    "same day contribute 1). Can exceed "
                    "num_delinquent_adjudications because the source's date "
                    "count is not limited to misdemeanor/felony delinquent "
                    "adjudications."
                ),
            },
            {
                "name": "num_probation_orders",
                "type": "int64",
                "unit": "count",
                "example": 64,
                "description": "Probation orders entered.",
            },
            {
                "name": "num_commitment_orders",
                "type": "int64",
                "unit": "count",
                "example": 16,
                "description": (
                    "Commitment orders entered (commitments to the Department "
                    "of Juvenile Justice)."
                ),
            },
            {
                "name": "num_superior_court_sentences",
                "type": "int64",
                "unit": "count",
                "example": 2,
                "description": (
                    "Cases sentenced in superior court (youths handled in the "
                    "adult system, e.g. SB 440 offenses)."
                ),
            },
            {
                "name": "num_secure_detention_youth",
                "type": "int64",
                "unit": "count",
                "example": 12,
                "description": (
                    "Distinct youths in the cell with a NEW secure detention "
                    "(RYDC — Regional Youth Detention Center) placement in the "
                    "year, from the source's 0/1 indicator. Likely INCOMPLETE "
                    "for 2023-2025: the source flags only 62/81/72 youth-rows "
                    "statewide in those years vs roughly 200-500 in every "
                    "earlier year — treat recent-year secure-placement counts "
                    "as a floor, not a total."
                ),
            },
            {
                "name": "num_secure_confinement_youth",
                "type": "int64",
                "unit": "count",
                "example": 3,
                "description": (
                    "Distinct youths in the cell with a NEW secure confinement "
                    "(YDC — Youth Development Campus) placement in the year, "
                    "from the source's 0/1 indicator (mutually exclusive with "
                    "the RYDC indicator per youth-row). Same 2023-2025 "
                    "incompleteness caveat as num_secure_detention_youth."
                ),
            },
        ],
        source="Georgia Juvenile Justice Data Clearinghouse",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        suppressed_to_null=False,
        usage=(
            "Attribute the Georgia Juvenile Justice Data Clearinghouse "
            "(juveniledata.georgiacourts.gov). Filter demographic to one axis "
            "at a time ('all', the race values, or the gender values); use "
            "state rows for statewide figures instead of summing county rows "
            "(distinct-youth counts are not additive across counties, and "
            "out-of-state youths appear only in the state rollup)."
        ),
        limitations=(
            "State rows have NULL county_fips. The source publishes no "
            "suppression — metric values are never NULL and zeros are real. "
            "Distinct-youth counts (num_youth and the two secure-placement "
            "counts) are not additive across counties, demographic values, or "
            "years; summed event counts are additive within one demographic "
            "axis. Youths labeled OUT OF STATE by the source (~1%% of "
            "youth-years) are included in state rows but absent from county "
            "rows, so county event counts sum slightly below the state row. "
            "The source's undocumented court-type axis (codes D/I/S) and its "
            "publication-time active/terminated case-status flag are "
            "aggregated over and not served. Secure-placement counts are "
            "likely incomplete for 2023-2025 (source indicator coverage "
            "collapses in those years). The companion county/month case-flow "
            "file published alongside this data (65 self-reporting counties, "
            "2005-2025) is a different universe and is not included in this "
            "dataset."
        ),
        quality_checks=[
            {
                "name": "num_offenses_at_least_num_youth",
                "description": (
                    "Every youth-level source row carries at least one "
                    "offense, so each cell's offense total must be at least "
                    "its distinct-youth count."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE num_youth IS NOT NULL "
                    "AND num_offenses IS NOT NULL AND num_offenses < num_youth"
                ),
                "mustBe": 0,
            },
            {
                "name": "delinquent_adjudications_within_offenses",
                "description": (
                    "Delinquent adjudications cannot exceed offenses; holds "
                    "row-wise in bronze (verified: zero violations) and is "
                    "preserved by summation."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "num_delinquent_adjudications IS NOT NULL AND "
                    "num_offenses IS NOT NULL AND "
                    "num_delinquent_adjudications > num_offenses"
                ),
                "mustBe": 0,
            },
            {
                "name": "petitions_within_offenses",
                "description": (
                    "Petitioned cases cannot exceed offenses; holds row-wise "
                    "in bronze (verified: zero violations) and is preserved "
                    "by summation."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE num_petitions IS NOT "
                    "NULL AND num_offenses IS NOT NULL AND "
                    "num_petitions > num_offenses"
                ),
                "mustBe": 0,
            },
            {
                "name": "secure_placement_youth_within_num_youth",
                "description": (
                    "Youths with a new secure detention or confinement "
                    "placement are a subset of the cell's distinct youths "
                    "(both flag counts are n_unique over the same youth set)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "num_secure_detention_youth > num_youth OR "
                    "num_secure_confinement_youth > num_youth"
                ),
                "mustBe": 0,
            },
            {
                "name": "race_partition_num_offenses",
                "description": (
                    "Every youth-level row carries exactly one race value, so "
                    "summed event counts partition exactly across the race "
                    "axis: per (year, county_fips) the six race rows' "
                    "num_offenses must sum to the 'all' row's num_offenses. "
                    "GROUP BY treats the NULL county_fips of state rows as "
                    "one group, so the invariant is enforced at both levels."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, "
                    "MAX(CASE WHEN demographic = 'all' THEN num_offenses END) "
                    "AS total, "
                    "SUM(CASE WHEN demographic IN ('asian','black','hispanic',"
                    "'native_american','other','white') THEN num_offenses END) "
                    "AS race_sum "
                    "FROM {object} GROUP BY year, county_fips"
                    ") WHERE total IS NOT NULL AND race_sum IS NOT NULL "
                    "AND total != race_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "gender_partition_num_offenses",
                "description": (
                    "Every youth-level row carries exactly one gender value, "
                    "so per (year, county_fips) the male + female rows' "
                    "num_offenses must sum to the 'all' row's num_offenses."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, "
                    "MAX(CASE WHEN demographic = 'all' THEN num_offenses END) "
                    "AS total, "
                    "SUM(CASE WHEN demographic IN ('female','male') "
                    "THEN num_offenses END) AS gender_sum "
                    "FROM {object} GROUP BY year, county_fips"
                    ") WHERE total IS NOT NULL AND gender_sum IS NOT NULL "
                    "AND total != gender_sum"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
