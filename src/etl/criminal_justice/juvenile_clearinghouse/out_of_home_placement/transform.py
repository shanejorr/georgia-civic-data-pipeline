"""Transform bronze out_of_home_placement data into a gold fact table.

Source: Georgia Juvenile Justice Data Clearinghouse (Judicial Council / AOC),
"Juvenile Justice Decision Point Raw Data — OHP & STP", one CSV covering
2005-2025. County-by-year counts of juvenile-court commitments to DJJ and
short-term program (STP) admissions, including the topic's namesake measure:
felony commitments resulting in out-of-home placement (OHP).

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Single era, single file.** One fixed 16-column CamelCase header covers all
  21 years; era detection still runs by column signature so a future schema
  change hard-fails instead of silently misparsing.
- **Grain: county x year x demographic.** The bronze wide race splits
  (Black/White/Hispanic/Other on ``FelonyCommitments`` and
  ``AllStpAdmissions``) are unpivoted into a ``demographic`` column: each
  bronze county-year row becomes one ``all`` row carrying all five metrics
  plus four race rows carrying only the two split metrics (the three unsplit
  metrics are NULL on race rows by design — the source does not publish
  them). 5x row expansion.
- **Race buckets are exhaustive; no Asian/PI conflation risk (§5b).** The
  source publishes exactly four race buckets and the structure doc verified
  across all 2,921 rows that Black+White+Hispanic+Other equals the parent
  total for both split measures (0 mismatches). ``Other`` therefore absorbs
  Asian, Pacific Islander, Native American, multiracial, and unknown youth,
  and Hispanic is treated by the source as a race-level bucket. The labels
  map to the existing dimension codes ``black``/``white``/``hispanic``/
  ``other`` — no combined-bucket remap applies and no rollup-vs-split
  duplication is possible. The race-sum identities are enforced as contract
  quality checks.
- **OUT OF STATE pseudo-county rows are dropped (21 rows, one per year).**
  The bronze carries an ``OUT OF STATE`` row with a bogus FIPS (``13222`` —
  not a Georgia county — for 2005-2022, then blank/literal ``"NULL"`` for
  2023-2025). A county-grain fact table with an FK to the counties dimension
  cannot carry these rows, and the counts are small (4-68 commitments/yr).
  Dropped explicitly, logged, and recorded via ``record_filtered``.
- **County-only detail level — no state rows.** The bronze publishes no
  state rollup rows and none are synthesized: with the OUT OF STATE rows
  dropped, a summed "state total" would silently exclude out-of-state
  commitments, and manufacturing aggregate rows would violate the
  preserve-bronze-granularity default. Documented in the contract
  limitations (consumers can SUM counties for in-state totals).
- **Sparse panel is meaningful absence, not missing data.** 2,921 bronze
  rows vs a full 160x21 panel: the structure doc verified no all-zero rows
  exist, so an absent county-year means no recorded activity (absence ~ 0).
  No zero rows are manufactured; documented in the contract.
- **CountyFips is trusted directly** (this is the only clearinghouse file
  that ships FIPS codes) but double-guarded: every kept row must match
  ``^13\\d{3}$`` and every (CountyName, CountyFips) pair must agree with the
  global counties dimension (hard stop on mismatch), so a bronze
  mis-assignment cannot pass silently. CountyName itself is a dimension
  attribute and is dropped from the fact table.
- **No suppression anywhere** — counts of 1 and 2 are published as-is, so
  the contract is emitted with ``suppressed_to_null=False`` and NULL means
  only "not published for race rows".
- **No §4b masks.** All metric values are within the defined domain
  (non-negative counts; bronze min 0, no impossible values). The bogus
  ``13222`` FIPS is handled by the OUT OF STATE row *filter* above, not a
  value mask.
- **Dedup tie-break.** The bronze grain (CountyName, PeriodYear) is verified
  unique and there is only one file, so no duplicates are expected after the
  unpivot; ``sort_col="felony_commitments"`` is the documented safety net
  (populated on every gold row — ``all`` and race alike — so it prefers a
  data-carrying row over a hypothetical null placeholder).
- **PeriodYear basis is undocumented at the source.** Neither the CSV nor
  the definitions page states calendar vs state fiscal year; the definitions
  page only says measures count events whose "instance started during the
  reporting period". The contract describes the column as the source's
  reporting period year and flags the ambiguity rather than asserting a
  basis the source does not state.
"""

import logging
from pathlib import Path

import polars as pl

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

TOPIC = "out_of_home_placement"
BRONZE_DIR = Path(
    "data/bronze/criminal_justice/juvenile_clearinghouse/out_of_home_placement"
)
GOLD_DIR = Path("data/gold/criminal_justice/out_of_home_placement")
COUNTIES_DIMENSION = Path("data/gold/_dimensions/counties.parquet")
SOURCE_URL = "https://juveniledata.georgiacourts.gov/dashboards-reports/"

# The five bronze measure columns and their gold names. Order is load-bearing:
# it is the gold metric column order.
MEASURE_COLUMNS: dict[str, str] = {
    "AllCommitments": "all_commitments",
    "FelonyCommitments": "felony_commitments",
    "FelonyCommitmentsOhp": "felony_commitments_ohp",
    "AllStpAdmissions": "all_stp_admissions",
    "FelonyStpAdmissions": "felony_stp_admissions",
}

# Race-split bronze columns per raw demographic label: each label maps to its
# (felony commitments, all STP admissions) column pair. Only these two
# measures carry race splits; the other three are NULL on race rows.
RACE_SPLIT_COLUMNS: dict[str, tuple[str, str]] = {
    "Black": ("FelonyCommitBlack", "AllStpAdmissionBlack"),
    "White": ("FelonyCommitWhite", "AllStpAdmissionWhite"),
    "Hispanic": ("FelonyCommitHispanic", "AllStpAdmissionHispanic"),
    "Other": ("FelonyCommitOther", "AllStpAdmissionOther"),
}

# Era-detection signature: the FIPS + CamelCase header combination is unique
# to this clearinghouse file (the sibling files use a label+code scheme).
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_1_2005_2025_single_csv": [
        "CountyName",
        "PeriodYear",
        "CountyFips",
        *MEASURE_COLUMNS.keys(),
    ],
}

# Gold fact column order. `detail_level` is carried through dedup / export
# splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "county_fips",
    "demographic",
    *MEASURE_COLUMNS.values(),
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "county_fips": pl.Utf8,
    "demographic": pl.Utf8,
    **{gold: pl.Int64 for gold in MEASURE_COLUMNS.values()},
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = list(MEASURE_COLUMNS.values())

NATURAL_KEYS: list[str] = ["year", "county_fips", "demographic", "detail_level"]

# The bronze pseudo-county holding commitments of Georgia youth attributed to
# out-of-state jurisdictions. Not representable in a county-grain fact table
# (bogus FIPS 13222 through 2022, blank/"NULL" after) — dropped, logged.
OUT_OF_STATE_LABEL = "OUT OF STATE"


# =============================================================================
# Helpers
# =============================================================================


def _to_int_expr(col: str) -> pl.Expr:
    """Cast an all-string bronze count column to Int64.

    The file is read with ``infer_schema_length=0`` (every column Utf8) per
    data-cleaning-standards §4.3b, so counts arrive as strings like "11".
    ``strict=False`` would silently NULL junk; counts here have zero nulls in
    bronze, so junk must fail loudly — hence a strict cast after stripping.
    """
    return pl.col(col).str.strip_chars().cast(pl.Int64, strict=True)


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


def _assert_fips_match_counties_dimension(df: pl.DataFrame) -> None:
    """Hard-stop unless every kept (CountyName, CountyFips) pair agrees with
    the global counties dimension.

    The FK validation check only proves the FIPS *exists*; this guard also
    proves the bronze assigned it to the right county name, so a source
    mis-assignment (e.g. a shifted FIPS column) cannot pass silently.
    """
    pairs = df.select(
        pl.col("CountyName").str.strip_chars().str.to_uppercase().alias("_name"),
        pl.col("county_fips"),
    ).unique()
    dim = pl.read_parquet(COUNTIES_DIMENSION).select(
        pl.col("county_fips"),
        pl.col("county_name").str.to_uppercase().alias("_dim_name"),
    )
    joined = pairs.join(dim, on="county_fips", how="left")
    mismatched = joined.filter(
        pl.col("_dim_name").is_null() | (pl.col("_dim_name") != pl.col("_name"))
    )
    if mismatched.height:
        raise ValueError(
            "Bronze CountyName/CountyFips pairs disagree with the counties "
            f"dimension: {mismatched.to_dicts()}"
        )
    logger.info(
        "All %d (CountyName, CountyFips) pairs match the counties dimension",
        pairs.height,
    )


# =============================================================================
# Era transform
# =============================================================================


def _drop_out_of_state_and_key_fips(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Drop OUT OF STATE pseudo-county rows and attach a guarded county_fips.

    The OUT OF STATE rows (one per year) carry a bogus FIPS (13222 through
    2022, blank/"NULL" after) and cannot live in a county-grain fact table
    with an FK to the counties dimension (see module docstring). Every kept
    row's FIPS is then format-guarded and cross-checked against the counties
    dimension.
    """
    oos_mask = (
        pl.col("CountyName").str.strip_chars().str.to_uppercase() == OUT_OF_STATE_LABEL
    )
    oos = df.filter(oos_mask)
    if oos.height:
        logger.warning(
            "Dropping %d OUT OF STATE pseudo-county row(s) (years %s; "
            "all_commitments sample %s) — not representable at county grain",
            oos.height,
            sorted(oos["year"].unique().to_list()),
            oos["AllCommitments"].head(5).to_list(),
        )
        for row in oos.group_by("year").len().sort("year").iter_rows(named=True):
            manifest.record_filtered(
                row["year"], row["len"], "out_of_state_pseudo_county_row"
            )
        df = df.filter(~oos_mask)

    # county_fips: bronze ships true 5-digit Georgia FIPS as strings (the
    # file is read all-Utf8, so leading digits are untouched). Guard the
    # format hard — every kept row must be a 13xxx county code.
    df = df.with_columns(pl.col("CountyFips").str.strip_chars().alias("county_fips"))
    bad_fips = df.filter(~pl.col("county_fips").str.contains(r"^13\d{3}$"))
    if bad_fips.height:
        raise ValueError(
            "Non-Georgia county FIPS on kept rows: "
            f"{bad_fips.select('CountyName', 'year', 'county_fips').to_dicts()[:10]}"
        )
    _assert_fips_match_counties_dimension(df)
    return df


def _transform_ohp_stp(df: pl.DataFrame, manifest: TransformManifest) -> pl.DataFrame:
    """Transform the single OHP/STP bronze file into gold-shaped rows.

    Drops OUT OF STATE pseudo-county rows, validates FIPS codes against the
    counties dimension, and unpivots the wide race splits into a
    ``demographic`` column (one ``all`` row + four race rows per bronze row).
    """
    race_cols = [c for pair in RACE_SPLIT_COLUMNS.values() for c in pair]
    _require_columns(
        df,
        ["CountyName", "PeriodYear", "CountyFips", *MEASURE_COLUMNS, *race_cols],
        "era_1 2005-2025",
    )

    # Strict Int32 year cast: PeriodYear is a plain 4-digit year in every row;
    # anything else must fail loudly, not become NULL.
    df = df.with_columns(
        pl.col("PeriodYear").str.strip_chars().cast(pl.Int32, strict=True).alias("year")
    )

    # Per-year bronze counts (single multi-year file, so record per year here
    # rather than per file).
    for row in df.group_by("year").len().sort("year").iter_rows(named=True):
        manifest.record_bronze(row["year"], row["len"])

    df = _drop_out_of_state_and_key_fips(df, manifest)

    # Unpivot: one `all` row carrying all five measures, plus one row per
    # race bucket carrying only the two race-split measures (the other three
    # are NULL by design — the source does not publish them by race).
    all_rows = df.select(
        "year",
        "county_fips",
        pl.lit("All").alias("_demographic_raw"),
        *[_to_int_expr(bronze).alias(gold) for bronze, gold in MEASURE_COLUMNS.items()],
    )
    race_frames = []
    for label, (felony_col, stp_col) in RACE_SPLIT_COLUMNS.items():
        race_frames.append(
            df.select(
                "year",
                "county_fips",
                pl.lit(label).alias("_demographic_raw"),
                pl.lit(None).cast(pl.Int64).alias("all_commitments"),
                _to_int_expr(felony_col).alias("felony_commitments"),
                pl.lit(None).cast(pl.Int64).alias("felony_commitments_ohp"),
                _to_int_expr(stp_col).alias("all_stp_admissions"),
                pl.lit(None).cast(pl.Int64).alias("felony_stp_admissions"),
            )
        )
    long_df = pl.concat([all_rows, *race_frames])

    # Demographic normalization via the shared canonical path (§5). The raw
    # labels are transform-controlled literals, so the effective alias slice
    # (§4.3a) is recorded rather than the full ~200-entry alias table.
    long_df = long_df.with_columns(
        normalize_demographic_column("_demographic_raw").alias("demographic")
    )
    observed_labels = ["All", *RACE_SPLIT_COLUMNS.keys()]
    manifest.record_categorical(
        column="demographic",
        map_dict={
            lbl.upper(): DEMOGRAPHIC_ALIASES[lbl.upper()] for lbl in observed_labels
        },
        bronze_series=long_df["_demographic_raw"],
        gold_series=long_df["demographic"],
    )

    long_df = long_df.with_columns(pl.lit("county").alias("detail_level"))
    return long_df.select(STANDARD_COLUMNS)


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame:
    """Read the bronze file, verify its era signature, and transform it.

    Read all-Utf8 (``infer_schema_length=0``) per §4.3b: the file carries a
    literal ``"NULL"`` string in CountyFips and zero-padded-looking codes, so
    schema inference is unsafe. Read loss is accounted; the file spans
    2005-2025, so file-level manifest events are recorded under the latest
    data year.
    """
    df, loss = read_bronze_file(path, infer_schema_length=0, return_loss=True)

    # Defensive BOM strip: the file starts with a UTF-8 BOM; polars handles
    # it, but if a future re-download changes encoding the header must not
    # silently become '﻿CountyName' and dodge era detection.
    first = df.columns[0]
    if first.startswith("﻿"):
        df = df.rename({first: first.lstrip("﻿")})

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{path.name}: no era signature matched columns {df.columns}")

    # Single file spanning 2005-2025: file-level events keyed to the latest
    # data year present (per-year bronze counts are recorded in the era fn).
    latest_year = int(df["PeriodYear"].cast(pl.Int32, strict=True).max())
    manifest.record_read_loss(
        latest_year, path.name, loss["raw_rows"], loss["parsed_rows"]
    )
    manifest.record_file(path, latest_year, era, df.height, df.columns)
    logger.info("Processing %s as %s (%d rows)", path.name, era, df.height)

    return _transform_ohp_stp(df, manifest)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for out_of_home_placement."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform each bronze file (a single CSV for this topic; the
    # loop keeps the standard shape if the source ever splits by year).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR):
        result = transform_file(path, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize + concat (one frame today; keeps the standard seam).
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)
    logger.info("Combined %d rows across %d frame(s)", combined.height, len(all_dfs))

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean an unpivot/aggregation bug and must raise, not be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: one bronze file whose (county, year) grain is verified
    # unique, so no duplicates are expected; felony_commitments is populated
    # on every gold row (all + race), making it the safety-net preference
    # for a data-carrying row over a hypothetical null placeholder.
    combined = deduplicate_by_levels(
        combined,
        {"county": ["year", "county_fips", "demographic"]},
        sort_col="felony_commitments",
    )

    # 4. Geography nulling (shared domain rules — a no-op today because the
    # topic has no state rows, but keeps transform and validator on the same
    # rule source). No §4b masks apply: see module docstring.
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=CRIMINAL_JUSTICE_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. Race-row NULLs on the three unsplit metrics are
    # uniform across years, so no spike is expected; any warning here needs
    # a documented cause before approval.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(
        combined,
        required_non_null=["year", "detail_level", "county_fips", "demographic"],
    )

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
    race_null_meaning = (
        "Not published for race rows — the source splits only felony "
        "commitments and STP admissions by race. Populated on every "
        "demographic='all' row (the source has no suppression)."
    )
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "County-level counts of juvenile-court commitments to the Georgia "
            "Department of Juvenile Justice (DJJ) and short-term program (STP) "
            "admissions, 2005-2025, from the Georgia Juvenile Justice Data "
            "Clearinghouse. Five measures per county-year: all commitments, "
            "felony commitments, felony commitments resulting in out-of-home "
            "placement (OHP), all STP admissions, and felony STP admissions. "
            "Felony commitments and all STP admissions additionally carry "
            "four-way race splits (black / white / hispanic / other)."
        ),
        title="Juvenile Commitments and Out-of-Home Placement",
        summary=(
            "Juvenile-court commitments to DJJ, felony commitments resulting "
            "in out-of-home placement, and short-term program admissions by "
            "Georgia county and race, 2005-2025."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2025,
                "description": (
                    "Reporting period year as published in the source's "
                    "PeriodYear column (2005-2025). The source does not state "
                    "whether the period is a calendar year or a state fiscal "
                    "year; its definitions page only says measures count "
                    "events whose instance started during the reporting "
                    "period."
                ),
            },
            {
                "name": "county_fips",
                "type": "string",
                "example": "13121",
                "description": (
                    "5-digit Georgia county FIPS code (FK to the counties "
                    "dimension), published directly by the source. Never NULL "
                    "in this topic: there are no state rollup rows, and the "
                    "source's OUT OF STATE pseudo-county rows (which carry an "
                    "invalid FIPS) are excluded."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "all",
                "short_description": (
                    "Race of the youth: all (every youth), black, white, "
                    "hispanic, or other."
                ),
                "description": (
                    "Youth race bucket (FK to demographics dimension): all, "
                    "black, white, hispanic, other. The source's four race "
                    "buckets are mutually exclusive and exhaustive (race sums "
                    "equal the parent totals in every row): hispanic is "
                    "treated as a race-level bucket, and other absorbs Asian, "
                    "Pacific Islander, Native American, multiracial, and "
                    "unknown youth. Race rows carry only felony_commitments "
                    "and all_stp_admissions; the other three measures are "
                    "published only at demographic='all'."
                ),
            },
            {
                "name": "all_commitments",
                "type": "int64",
                "unit": "count",
                "example": 12,
                "null_meaning": race_null_meaning,
                "description": (
                    "All juvenile-court commitments to DJJ: petitioned cases "
                    "where, among all charges in the case, the most serious "
                    "outcome is a commitment to DJJ (unique cases). Published "
                    "only at demographic='all' (NULL on race rows)."
                ),
            },
            {
                "name": "felony_commitments",
                "type": "int64",
                "unit": "count",
                "example": 7,
                "description": (
                    "Juvenile-court commitments to DJJ where the offense is a "
                    "felony. The one measure (with all_stp_admissions) split "
                    "by race: race-row values sum exactly to the "
                    "demographic='all' value within each county-year."
                ),
            },
            {
                "name": "felony_commitments_ohp",
                "type": "int64",
                "unit": "count",
                "key_metric": True,
                "example": 5,
                "null_meaning": race_null_meaning,
                "short_description": (
                    "Felony commitments that resulted in the youth being "
                    "placed out of the home (the topic's headline measure)."
                ),
                "description": (
                    "Felony commitments to DJJ resulting in out-of-home "
                    "placement (OHP) — the topic's namesake headline measure. "
                    "A subset of felony_commitments. Published only at "
                    "demographic='all' (NULL on race rows)."
                ),
            },
            {
                "name": "all_stp_admissions",
                "type": "int64",
                "unit": "count",
                "example": 14,
                "description": (
                    "All short-term program (STP) admissions — youth placed "
                    "in a Short Term Program, a form of secure juvenile "
                    "correctional confinement. The one measure (with "
                    "felony_commitments) split by race: race-row values sum "
                    "exactly to the demographic='all' value within each "
                    "county-year."
                ),
            },
            {
                "name": "felony_stp_admissions",
                "type": "int64",
                "unit": "count",
                "example": 6,
                "null_meaning": race_null_meaning,
                "description": (
                    "Short-term program admissions where the offense is a "
                    "felony. A subset of all_stp_admissions. Published only "
                    "at demographic='all' (NULL on race rows)."
                ),
            },
        ],
        source="Georgia Juvenile Justice Data Clearinghouse",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        # The source has no suppression (counts of 1 and 2 are published
        # as-is), so NULL must not be described as "suppressed".
        suppressed_to_null=False,
        limitations=(
            "County rows only — the source publishes no state rollup rows "
            "and none are synthesized. Summing counties yields in-state "
            "totals only: the source's OUT OF STATE pseudo-county rows (4-68 "
            "commitments per year, invalid county FIPS) are excluded from "
            "this dataset. The panel is sparse: a county-year absent from "
            "the data means the county had no recorded activity that year "
            "(the source publishes no all-zero rows), not missing data. "
            "Race splits exist only for felony_commitments and "
            "all_stp_admissions; the other three measures are NULL on race "
            "rows. The source does not state whether PeriodYear is a "
            "calendar or state fiscal year."
        ),
        quality_checks=[
            {
                "name": "felony_commitments_within_all_commitments",
                "description": (
                    "Felony commitments are a subset of all commitments: "
                    "felony_commitments must not exceed all_commitments "
                    "(verified 0 violations in bronze). Both populated only "
                    "at demographic='all'; NULL-guarded."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "all_commitments IS NOT NULL AND felony_commitments IS NOT NULL "
                    "AND felony_commitments > all_commitments"
                ),
                "mustBe": 0,
            },
            {
                "name": "ohp_within_felony_commitments",
                "description": (
                    "Out-of-home placements are a subset of felony "
                    "commitments: felony_commitments_ohp must not exceed "
                    "felony_commitments (verified 0 violations in bronze)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "felony_commitments_ohp IS NOT NULL "
                    "AND felony_commitments IS NOT NULL "
                    "AND felony_commitments_ohp > felony_commitments"
                ),
                "mustBe": 0,
            },
            {
                "name": "felony_stp_within_all_stp_admissions",
                "description": (
                    "Felony STP admissions are a subset of all STP "
                    "admissions: felony_stp_admissions must not exceed "
                    "all_stp_admissions (verified 0 violations in bronze)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "felony_stp_admissions IS NOT NULL "
                    "AND all_stp_admissions IS NOT NULL "
                    "AND felony_stp_admissions > all_stp_admissions"
                ),
                "mustBe": 0,
            },
            {
                # Pivot-with-conditional-aggregation, never a self-join (§15b).
                "name": "race_felony_commitments_sum_to_total",
                "description": (
                    "The four race buckets are mutually exclusive and "
                    "exhaustive: race-row felony_commitments must sum exactly "
                    "to the demographic='all' value within each county-year "
                    "(verified 0 mismatches in bronze)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, "
                    "MAX(CASE WHEN demographic = 'all' THEN felony_commitments "
                    "END) AS total, "
                    "SUM(CASE WHEN demographic != 'all' THEN felony_commitments "
                    "END) AS race_sum "
                    "FROM {object} GROUP BY year, county_fips"
                    ") WHERE total IS NOT NULL AND race_sum IS NOT NULL "
                    "AND total != race_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "race_stp_admissions_sum_to_total",
                "description": (
                    "Race-row all_stp_admissions must sum exactly to the "
                    "demographic='all' value within each county-year "
                    "(verified 0 mismatches in bronze)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, "
                    "MAX(CASE WHEN demographic = 'all' THEN all_stp_admissions "
                    "END) AS total, "
                    "SUM(CASE WHEN demographic != 'all' THEN all_stp_admissions "
                    "END) AS race_sum "
                    "FROM {object} GROUP BY year, county_fips"
                    ") WHERE total IS NOT NULL AND race_sum IS NOT NULL "
                    "AND total != race_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "race_rows_unsplit_metrics_null",
                "description": (
                    "Structural: the source publishes all_commitments, "
                    "felony_commitments_ohp, and felony_stp_admissions only "
                    "at demographic='all' — they must be NULL on race rows."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE demographic != 'all' "
                    "AND (all_commitments IS NOT NULL "
                    "OR felony_commitments_ohp IS NOT NULL "
                    "OR felony_stp_admissions IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "race_rows_split_metrics_populated",
                "description": (
                    "Structural: the two race-split measures are published "
                    "for every race bucket in every bronze row — race rows "
                    "must carry non-NULL felony_commitments and "
                    "all_stp_admissions."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE demographic != 'all' "
                    "AND (felony_commitments IS NULL "
                    "OR all_stp_admissions IS NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "all_rows_fully_populated",
                "description": (
                    "Structural: the source has no suppression, so every "
                    "demographic='all' row must carry all five measures "
                    "non-NULL."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE demographic = 'all' "
                    "AND (all_commitments IS NULL OR felony_commitments IS NULL "
                    "OR felony_commitments_ohp IS NULL "
                    "OR all_stp_admissions IS NULL "
                    "OR felony_stp_admissions IS NULL)"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
