"""Transform GA DPH OASIS drug-overdose mortality exports into a gold fact table.

Source: OASIS Data Table Tool (death-certificate data, Georgia Office of Vital
Records) — 30 CSVs: 6 overlapping drug-cause categories x 5 layouts (county x
year + state-grain age/race/ethnicity/sex breakdowns), 1999-2024. Gold serves
county x year x drug_category (all-demographics) plus state x year x
drug_category x demographic (race and sex breakdowns), with deaths, crude
death rate, and age-adjusted death rate (both per 100,000 population).

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **drug_category is a NON-ADDITIVE grain categorical.** The six OASIS cause
  categories overlap: all_drug_overdoses ⊃ all_opioids ⊃ each opioid subtype,
  and the subtypes overlap each other (a poly-drug death counts in EVERY
  matching category — 2023 subtype deaths sum to 3,609 vs 1,838 for
  all_opioids). Summing deaths across drug_category values is therefore
  invalid; the categorical-with-documentation shape (over 18 wide metric
  columns) matches the hate_crimes bias_motivation precedent and the
  dashboard's required-single-select behavior for a grain categorical with no
  'all' sentinel value. Cause definitions are the tool's "Without F-Codes"
  variants (ICD-10 mental/behavioral underlying causes excluded).
- **Demographics: race + sex served at state grain; age + ethnicity deferred
  to v2.** The bronze demographic breakdowns exist ONLY at state grain
  (county x demographic is almost entirely suppressed upstream and was not
  exported). Race publishes the post-1997 OMB split pair (separate Asian and
  Native Hawaiian/Other Pacific Islander buckets → asian / pacific_islander;
  no §5b remap — the 7 buckets sum exactly to All Races, e.g. 2,521 in 2023)
  and sex (female/male) also reconciles exactly, so both map cleanly onto the
  existing global demographics dimension. The age files (20 buckets) and
  ethnicity files (Hispanic / Not Hispanic / Unknown) are deliberately NOT
  ingested: (a) the demographics dimension has no age-bucket keys and no
  ethnicity category — serving them requires a global dimension expansion
  (new demographic_category values change the REST/MCP filter surface for
  every topic), out of scope for one topic; (b) OASIS ethnicity is a separate
  axis OVERLAPPING the race buckets (a Hispanic decedent also appears in a
  race bucket), while the dimension files hispanic under demographic_category
  = race — serving both would break §5a mutual exclusivity within the race
  category for this topic. Adding them later is additive (new demographic
  values, no schema change). The 12 skipped files remain in bronze,
  checksummed and analyzed.
- **Suppression sentinels are numeric, nulled by value.** Rates carry
  negative sentinels (-5 = suppressed, fewer than 5 deaths; -2 = no
  population denominator; other codes possible on refresh) — any negative
  rate → NULL (never 0), masked counts recorded on the manifest. Death
  COUNTS are never suppressed: an empty deaths cell is a true zero per OASIS
  (verified by exact reconciliation: counties, race buckets, and sexes each
  sum to the state total) and is filled with 0. Zero-death rows render their
  rates inconsistently (0.0 or empty) and are normalized to 0.0 — a
  true-zero-deaths row has a true rate of 0 (positive-rate contradictions
  hard-fail; none exist today).
- **Rates are per 100,000 population — named *_per_100k, no `unit`.** The
  unit vocabulary has no per-population-rate concept: `proportion` ([0,1])
  and `ratio` ("divided by 100 from a 0-100 source"; validator fails a ratio
  column whose median exceeds 1.5) both misdescribe a per-100k rate, so the
  columns declare no unit (the sanctioned unclassifiable case) and carry
  authored non-negativity quality checks instead. The explicit _per_100k
  suffix keeps the bare `_rate` name from implying the platform's 0-1 rate
  scale (§4).
- **Key metric: death_rate_per_100k** (crude rate). Preferred over the count
  per §4c (rate over count) and over the age-adjusted rate because the crude
  rate is present at every served grain and stays present if v2 adds the age
  breakdown (age-adjusted rates are structurally absent for age-stratified
  rows — the tool disallows the combination). deaths is its numerator
  (metric_component); the population denominator is not published.
- **Derived duplicate rows dropped with equality assertions** (shared OASIS
  helpers): 'selected_years_total' year rows, 'County Summary' geography rows
  (assert equal to the Georgia row), and 'Selected {Races|Sexes} Total'
  breakdown rows (assert equal to the 'All …' row).
- **Dedup tie-break.** The statewide 'all' row is republished identically in
  three layouts per cause (county file's Georgia row, race file's All Races,
  sex file's All Sexes). The collision guard runs first and hard-fails unless
  the triplicates agree on every metric (a free cross-file reconciliation);
  deduplicate_by_levels(sort_col="deaths") then keeps one — the tie-break is
  immaterial because survivors are identical by assertion, and the removed
  count is asserted to equal the exact duplicate count. A single one-shot
  export (no overlapping vintages) makes any other duplicate impossible.
- **No §4b impossible-value masks beyond the suppression sentinels.** After
  sentinel nulling, rates are non-negative by construction and deaths are
  non-negative counts; the max county rate (86.2 per 100k) and max state
  count (2,687 in 2022) are extreme-but-conceivable epidemic-era values,
  preserved as published.
"""

import logging
from pathlib import Path

import polars as pl

from src.etl.criminal_justice.dph_oasis._oasis_shared import (
    OASIS_TOTAL_YEAR,
    cast_oasis_metrics,
    detect_oasis_layout,
    drop_county_summary_rows,
    drop_selected_total_rows,
    drop_total_year_rows,
    normalize_zero_death_rates,
    null_sentinel_rates,
    read_oasis_csv,
)
from src.utils.demographics import (
    DEMOGRAPHIC_ALIASES,
    SENTINEL_UNMATCHED_DEMOGRAPHIC,
    normalize_demographic_column,
)
from src.utils.metadata import write_data_dictionary
from src.utils.readers import list_bronze_files
from src.utils.transformers import (
    COUNTY_DETAIL_LEVEL_FILES,
    TransformManifest,
    assert_no_natural_key_collisions,
    deduplicate_by_levels,
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

TOPIC = "overdose_deaths"
BRONZE_DIR = Path("data/bronze/criminal_justice/dph_oasis/overdose_deaths")
GOLD_DIR = Path("data/gold/criminal_justice/overdose_deaths")
SOURCE_URL = "https://oasis.state.ga.us/dtt/mortalitydrugoverdoses"

# The six OASIS drug-overdose cause categories, keyed by the filename slug
# (the part before '__'); values are the gold drug_category codes (identical —
# the slugs are already canonical snake_case). OVERLAPPING, never additive.
DRUG_CATEGORIES: dict[str, str] = {
    "all_drug_overdoses": "all_drug_overdoses",
    "all_opioids": "all_opioids",
    "heroin": "heroin",
    "methadone": "methadone",
    "natural_semisynthetic_synthetic_opioids": (
        "natural_semisynthetic_synthetic_opioids"
    ),
    "synthetic_opioids_excl_methadone": "synthetic_opioids_excl_methadone",
}
DRUG_CATEGORY_VALUES: list[str] = sorted(DRUG_CATEGORIES.values())

# State-grain breakdown layouts served in v1 vs deferred (see module
# docstring: age needs dimension expansion; ethnicity overlaps the race axis).
INGESTED_LAYOUTS = {"county", "race", "sex"}
DEFERRED_LAYOUTS = {"age", "ethnicity"}

# Gold metric names: rates renamed with an explicit per-100k suffix so the
# bare `_rate` name never implies the platform's 0-1 rate scale (§4).
RATE_RENAMES: dict[str, str] = {
    "death_rate": "death_rate_per_100k",
    "age_adjusted_death_rate": "age_adjusted_death_rate_per_100k",
}
GOLD_RATE_COLUMNS: list[str] = list(RATE_RENAMES.values())

METRIC_COLUMNS: list[str] = ["deaths", *GOLD_RATE_COLUMNS]

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "county_fips",
    "demographic",
    "drug_category",
    *METRIC_COLUMNS,
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "county_fips": pl.Utf8,
    "demographic": pl.Utf8,
    "drug_category": pl.Utf8,
    "deaths": pl.Int64,
    "death_rate_per_100k": pl.Float64,
    "age_adjusted_death_rate_per_100k": pl.Float64,
    "detail_level": pl.Utf8,
}

NATURAL_KEYS: list[str] = [
    "year",
    "county_fips",
    "demographic",
    "drug_category",
    "detail_level",
]

# Race buckets served at state grain (post-1997 OMB split pair; sum exactly to
# the 'all' row per year x cause). Shared by the transform and the authored
# partition quality checks.
RACE_BUCKETS: list[str] = [
    "asian",
    "black",
    "multiracial",
    "native_american",
    "pacific_islander",
    "race_unknown",
    "white",
]


# =============================================================================
# Per-file transform
# =============================================================================


def _record_bronze_accounting(
    df_raw: pl.DataFrame, manifest: TransformManifest, max_year: int
) -> None:
    """Record per-year bronze counts, lumping derived total rows into max_year.

    The 'selected_years_total' rows carry no calendar year; they are recorded
    as bronze under the latest data year and immediately recorded as filtered
    there, so the manifest's bronze totals equal the raw file row counts and
    the bronze-minus-gold arithmetic stays explainable.
    """
    real = df_raw.filter(pl.col("year") != OASIS_TOTAL_YEAR)
    per_year = {
        int(r["year"]): r["len"]
        for r in real.with_columns(pl.col("year").cast(pl.Int32))
        .group_by("year")
        .len()
        .to_dicts()
    }
    for year in sorted(per_year):
        manifest.record_bronze(year, per_year[year])
    n_total_rows = df_raw.height - real.height
    if n_total_rows:
        manifest.record_bronze(max_year, n_total_rows)
        manifest.record_filtered(
            max_year, n_total_rows, "derived_selected_years_total_row"
        )


def _tidy_county_layout(
    df: pl.DataFrame, path_name: str, manifest: TransformManifest
) -> pl.DataFrame:
    """Reshape a county-layout frame: Georgia row -> state, counties -> county.

    Bronze county_fips is a bare code: '13' on the Georgia (statewide) row —
    nulled here per the state-grain convention — and 5-digit '13xxx' on
    county rows (asserted; FK to the counties dimension).
    """
    df, n_summary = drop_county_summary_rows(df, path_name)
    for year in sorted(df["year"].unique().to_list()):
        # One County Summary row per year per file (its total-year row was
        # already dropped with the year filter).
        manifest.record_filtered(int(year), 1, "derived_county_summary_row")
    if n_summary != df["year"].n_unique():
        raise ValueError(
            f"{path_name}: expected one County Summary row per year, "
            f"dropped {n_summary} for {df['year'].n_unique()} years"
        )

    bad_fips = df.filter(
        pl.col("geography") != "Georgia",
        ~pl.col("county_fips").str.contains(r"^13\d{3}$"),
    )
    if bad_fips.height:
        raise ValueError(
            f"{path_name}: {bad_fips.height} county rows with malformed "
            f"county_fips: {bad_fips['county_fips'].unique().to_list()[:10]}"
        )

    return df.with_columns(
        # The Georgia row is the statewide total (bronze fips '13'): route to
        # the state detail level with NULL county_fips.
        pl.when(pl.col("geography") == "Georgia")
        .then(None)
        .otherwise(pl.col("county_fips"))
        .alias("county_fips"),
        pl.when(pl.col("geography") == "Georgia")
        .then(pl.lit("state"))
        .otherwise(pl.lit("county"))
        .alias("detail_level"),
        # County files are all-demographics-combined.
        pl.lit("all").alias("demographic"),
    )


def _tidy_breakdown_layout(
    df: pl.DataFrame, layout: str, path_name: str, manifest: TransformManifest
) -> pl.DataFrame:
    """Reshape a race/sex breakdown frame (state grain only).

    The breakdown column maps to the shared demographic vocabulary via
    normalize_demographic_column; the effective alias slice is recorded on
    the manifest (skill 4.3a). Unmatched labels hard-fail immediately.
    """
    df, n_total = drop_selected_total_rows(df, layout, path_name)
    for year in sorted(df["year"].unique().to_list()):
        manifest.record_filtered(int(year), 1, f"derived_selected_{layout}_total_row")
    if n_total != df["year"].n_unique():
        raise ValueError(
            f"{path_name}: expected one Selected-Total row per year, "
            f"dropped {n_total} for {df['year'].n_unique()} years"
        )

    non_georgia = df.filter(pl.col("geography") != "Georgia")
    if non_georgia.height:
        raise ValueError(
            f"{path_name}: breakdown layout should be state-grain only, found "
            f"geographies {non_georgia['geography'].unique().to_list()}"
        )

    df = df.with_columns(normalize_demographic_column(layout).alias("demographic"))
    unmatched = df.filter(pl.col("demographic") == SENTINEL_UNMATCHED_DEMOGRAPHIC)
    if unmatched.height:
        raise ValueError(
            f"{path_name}: unmatched demographic labels "
            f"{unmatched[layout].unique().to_list()} — add aliases to "
            "src/utils/demographics.py, never drop rows"
        )
    # Record the EFFECTIVE alias slice (the aliases actually hit, not all
    # ~200) so map_used stays reviewable while the unmapped guard holds.
    observed = df[layout].unique().to_list()
    alias_slice = {
        label: DEMOGRAPHIC_ALIASES[label.upper()]
        for label in observed
        if label.upper() in DEMOGRAPHIC_ALIASES
    }
    manifest.record_categorical(
        column="demographic",
        map_dict=alias_slice,
        bronze_series=df[layout],
        gold_series=df["demographic"],
    )

    return df.with_columns(
        pl.lit(None).cast(pl.Utf8).alias("county_fips"),
        pl.lit("state").alias("detail_level"),
    )


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read one OASIS export, route by layout, return a gold-shaped frame.

    Returns None for the deferred age/ethnicity layouts (see module
    docstring) — those files are read only far enough to detect their layout
    by column signature, then skipped with a log line.
    """
    df_raw, loss = read_oasis_csv(path)
    layout = detect_oasis_layout(df_raw, path.name)

    cause_slug = path.name.split("__")[0]
    if cause_slug not in DRUG_CATEGORIES:
        raise ValueError(
            f"{path.name}: unknown cause slug {cause_slug!r} — a new OASIS "
            "cause category must be mapped in DRUG_CATEGORIES, never guessed"
        )

    if layout in DEFERRED_LAYOUTS:
        logger.info(
            "Skipping %s: %s breakdown deferred to v2 (age needs a "
            "demographics-dimension expansion; ethnicity overlaps the race "
            "axis — see module docstring)",
            path.name,
            layout,
        )
        return None
    if layout not in INGESTED_LAYOUTS:  # defensive: signatures cover all 5
        raise ValueError(f"{path.name}: unhandled layout {layout!r}")

    max_year = int(
        df_raw.filter(pl.col("year") != OASIS_TOTAL_YEAR)["year"].cast(pl.Int32).max()
    )
    manifest.record_read_loss(
        max_year, path.name, int(loss["raw_rows"]), int(loss["parsed_rows"])
    )
    manifest.record_file(
        path, max_year, f"oasis_{layout}_v1", df_raw.height, df_raw.columns
    )
    _record_bronze_accounting(df_raw, manifest, max_year)

    df = cast_oasis_metrics(df_raw, path.name)
    df, _ = drop_total_year_rows(df, path.name)

    if layout == "county":
        df = _tidy_county_layout(df, path.name, manifest)
    else:
        df = _tidy_breakdown_layout(df, layout, path.name, manifest)

    return (
        df.with_columns(pl.lit(DRUG_CATEGORIES[cause_slug]).alias("drug_category"))
        .rename(RATE_RENAMES)
        .select(STANDARD_COLUMNS)
    )


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for overdose_deaths."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform each bronze file (age/ethnicity layouts skipped).
    all_dfs: list[pl.DataFrame] = []
    n_skipped = 0
    for path in list_bronze_files(BRONZE_DIR):
        df = transform_file(path, manifest)
        if df is None:
            n_skipped += 1
        elif df.height > 0:
            all_dfs.append(df)
    logger.info(
        "Ingested %d file(s); skipped %d deferred age/ethnicity file(s)",
        len(all_dfs),
        n_skipped,
    )
    if not all_dfs:
        raise ValueError("No bronze files ingested")

    # 2. Harmonize + concat across layouts.
    combined = pl.concat(harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES))

    # drug_category derives from the filename slug (identity map) — recorded
    # so the manifest's categorical coverage includes it.
    manifest.record_categorical(
        column="drug_category",
        map_dict=DRUG_CATEGORIES,
        bronze_series=combined["drug_category"],
        gold_series=combined["drug_category"],
    )

    # 3a. Normalize inconsistent zero-death rate rendering (0.0 vs empty vs
    # sentinel) to a true 0.0 BEFORE sentinel masking, so suppression masks
    # only count rows with 1+ events. Positive-rate contradictions hard-fail.
    combined, zero_filled = normalize_zero_death_rates(combined, GOLD_RATE_COLUMNS)
    for col, n in zero_filled.items():
        if n:
            logger.info(
                "Normalized %d zero-death %s cell(s) to 0.0 (inconsistent "
                "bronze zero-rendering; a zero-death row has a true rate of 0)",
                n,
                col,
            )

    # 3b. Suppression: any remaining negative rate is an OASIS sentinel
    # (-5 = fewer than 5 deaths; -2 = no denominator) -> NULL, never 0.
    combined, mask_stats = null_sentinel_rates(combined, GOLD_RATE_COLUMNS)
    for col, stats in mask_stats.items():
        manifest.record_masked(
            col,
            int(stats["count"]),
            reason=(
                "oasis_rate_suppression_sentinel (negative sentinel values "
                f"{stats['sentinels']}; -5 = rate suppressed, fewer than 5 "
                "deaths)"
            ),
            years=[int(y) for y in stats["years"]],
        )

    # 4. Collision guard BEFORE dedup: the statewide 'all' row appears in 3
    # layouts per cause-year (county/race/sex files) and MUST agree on every
    # metric — the guard doubles as a cross-file reconciliation assertion.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: survivors are identical by the guard above, so sort_col
    # "deaths" (prefer the fuller row) is immaterial; the removed count is
    # asserted below to equal the exact triplicate surplus.
    state_all = combined.filter(
        pl.col("detail_level") == "state", pl.col("demographic") == "all"
    )
    expected_removed = (
        state_all.height - state_all.select("year", "drug_category").unique().height
    )
    before = combined.height
    combined = deduplicate_by_levels(
        combined,
        {
            "county": ["year", "county_fips", "demographic", "drug_category"],
            "state": ["year", "demographic", "drug_category"],
        },
        sort_col="deaths",
    )
    removed = before - combined.height
    if removed != expected_removed:
        raise ValueError(
            f"Dedup removed {removed} rows, expected exactly "
            f"{expected_removed} duplicate statewide 'all' rows"
        )

    # 5. Geography nulling (shared domain rules; state rows already NULL).
    # No further §4b masks apply: after sentinel nulling, rates are
    # non-negative by construction and deaths are non-negative counts; the
    # epidemic-era maxima are extreme-but-conceivable and preserved.
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=CRIMINAL_JUSTICE_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. Rate NULLs are suppression (<5 deaths), which is
    # densest in low-count years/causes — spikes are expected with a known
    # cause and surface as warnings.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(
        combined,
        required_non_null=[
            "year",
            "demographic",
            "drug_category",
            "deaths",
            "detail_level",
        ],
    )

    # 6. Manifest stats on the FINAL DataFrame, then export.
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(
        combined,
        GOLD_DIR,
        STANDARD_COLUMNS,
        detail_level_files=COUNTY_DETAIL_LEVEL_FILES,
    )
    manifest.write(GOLD_DIR)

    # 7. Contract from the in-code column declaration.
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

    # 8. ALWAYS LAST: validate the gold just written against the contract
    # just emitted. Raises GoldValidationError -> non-zero exit.
    run_topic_validation(GOLD_DIR)


def _emit_contract(year_range: tuple[int, int]) -> None:
    """Emit the ODCS contract via ``write_data_dictionary``.

    The column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level``.
    """
    race_list = ", ".join(RACE_BUCKETS)
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        title="Drug Overdose Deaths by County",
        summary=(
            "Drug-overdose deaths and death rates per 100,000 for Georgia "
            "counties by year and drug category (opioids, fentanyl-class, "
            "heroin, methadone), from death certificates, 1999 onward."
        ),
        description=(
            "Drug-overdose deaths, crude death rates, and age-adjusted death "
            "rates (both per 100,000 population) for Georgia, from official "
            "death-certificate data (Georgia Department of Public Health "
            "OASIS, Office of Vital Records), 1999 onward. Six OVERLAPPING "
            "drug-cause categories are served: all drug overdoses, all "
            "opioids, natural/semi-synthetic/synthetic opioids, synthetic "
            "opioids other than methadone (the fentanyl-class category), "
            "heroin, and methadone. A poly-drug death is counted in every "
            "matching category, so deaths must NEVER be summed across "
            "drug_category values — always filter to a single category. "
            "County x year rows cover all demographics combined; statewide "
            "rows add race and sex breakdowns. Rates based on fewer than 5 "
            "deaths are suppressed at source (NULL); death counts are never "
            "suppressed, and a 0 is a true zero."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Calendar year of death (year the death occurred, not "
                    "the publication year)."
                ),
            },
            {
                "name": "county_fips",
                "type": "string",
                "example": "13121",
                "null_meaning": "NULL on statewide rows.",
                "description": (
                    "5-digit county FIPS code (state prefix 13) of the "
                    "decedent's county of residence; FK to the counties "
                    "dimension. NULL on statewide rows. Deaths are counted "
                    "by residence, not by where the death occurred."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "all",
                "short_description": (
                    "Demographic slice: 'all' everywhere; race and sex "
                    "breakdowns on statewide rows only."
                ),
                "description": (
                    "Demographic slice. County rows are always 'all' (the "
                    "source suppresses nearly all county-level demographic "
                    "cells, so they are not published); statewide rows carry "
                    "'all' plus two overlapping axes: race (" + race_list + ") "
                    "and sex (female, male). Filter to one axis — summing "
                    "race rows and sex rows together double-counts. Race "
                    "uses the post-1997 OMB split convention (separate asian "
                    "and pacific_islander buckets, no combined rollup); the "
                    "seven race buckets are mutually exclusive and sum "
                    "exactly to the 'all' row, as do female + male. "
                    "race_unknown is published by the source and has zero "
                    "deaths in every year to date. Age and ethnicity "
                    "breakdowns exist in the source at state grain but are "
                    "not yet served."
                ),
            },
            {
                "name": "drug_category",
                "type": "string",
                "nullable": False,
                "validValues": DRUG_CATEGORY_VALUES,
                "example": "all_drug_overdoses",
                "short_description": (
                    "OASIS drug-cause category — categories OVERLAP (a "
                    "poly-drug death counts in every matching one); never "
                    "sum across categories."
                ),
                "description": (
                    "OASIS drug-overdose cause category. THE CATEGORIES "
                    "OVERLAP AND ARE NOT ADDITIVE: all_drug_overdoses "
                    "contains all_opioids, which contains the four opioid "
                    "sub-types (natural_semisynthetic_synthetic_opioids, "
                    "synthetic_opioids_excl_methadone, heroin, methadone), "
                    "and the sub-types overlap each other — a death "
                    "involving both heroin and fentanyl is counted in both. "
                    "Summing deaths across drug_category values double-"
                    "counts (2023 statewide: the four sub-types sum to "
                    "3,609 deaths vs 1,838 actual all-opioid deaths); "
                    "always filter to ONE category. "
                    "synthetic_opioids_excl_methadone (ICD-10 T40.4) is the "
                    "fentanyl-class category. Definitions are the OASIS "
                    "'Without F-Codes' variants (deaths whose underlying "
                    "cause is an ICD-10 mental/behavioral F-code are "
                    "excluded)."
                ),
            },
            {
                "name": "deaths",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "metric_component": "numerator",
                "example": 12,
                "short_description": (
                    "Resident drug-overdose deaths in the category (never "
                    "suppressed; 0 is a true zero)."
                ),
                "description": (
                    "Count of resident deaths in the drug category. Never "
                    "suppressed at source: 0 is a true zero (bronze renders "
                    "zeros as empty cells, filled to 0 here — verified by "
                    "exact reconciliation: county, race, and sex slices "
                    "each sum to the statewide total). Numerator of the "
                    "death rates. NOT additive across drug_category values "
                    "(see drug_category)."
                ),
            },
            {
                "name": "death_rate_per_100k",
                "type": "float64",
                "key_metric": True,
                "example": 21.6,
                "null_meaning": (
                    "NULL = suppressed at source: rate based on fewer than "
                    "5 deaths (the row's exact deaths count, 1-4, is still "
                    "published)."
                ),
                "short_description": (
                    "Crude drug-overdose death rate per 100,000 residents "
                    "(suppressed to NULL when based on fewer than 5 deaths)."
                ),
                "description": (
                    "Crude death rate per 100,000 residents "
                    "(source-computed). NOT on the platform's 0-1 rate "
                    "scale — the natural unit is deaths per 100,000 "
                    "population. Suppressed at source (NULL, bronze "
                    "sentinel -5) when based on fewer than 5 deaths; the "
                    "row's exact deaths count is still published, so heavy "
                    "NULL density in small counties and rare categories is "
                    "expected. 0.0 on zero-death rows (normalized from the "
                    "source's inconsistent zero rendering)."
                ),
            },
            {
                "name": "age_adjusted_death_rate_per_100k",
                "type": "float64",
                "example": 23.2,
                "null_meaning": (
                    "NULL = suppressed at source: rate based on fewer than 5 deaths."
                ),
                "short_description": (
                    "Age-adjusted drug-overdose death rate per 100,000 "
                    "(2000 US standard population)."
                ),
                "description": (
                    "Age-adjusted death rate per 100,000 residents "
                    "(source-computed, standardized to the 2000 US standard "
                    "population) — use this one when comparing counties or "
                    "demographic groups with different age structures. NOT "
                    "on the platform's 0-1 rate scale. Same suppression as "
                    "the crude rate (NULL when based on fewer than 5 "
                    "deaths); 0.0 on zero-death rows."
                ),
            },
        ],
        source=(
            "Georgia Department of Public Health, OASIS Data Table Tool "
            "(death-certificate data, Office of Vital Records)"
        ),
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        usage=(
            "Cite the Georgia Department of Public Health, Office of Health "
            "Indicators for Planning (OASIS, oasis.state.ga.us). ALWAYS "
            "filter to a single drug_category — the categories overlap and "
            "summing across them double-counts poly-drug deaths. Filter to "
            "a single demographic axis (race OR sex) on statewide rows. Use "
            "age_adjusted_death_rate_per_100k for cross-county or cross-"
            "group comparisons; deaths and rates are additive across "
            "counties within one category (county deaths sum exactly to "
            "the statewide row)."
        ),
        limitations=(
            "Statewide rows have NULL county_fips. Drug-cause categories "
            "overlap (a poly-drug death is counted in every matching "
            "category), so deaths summed across drug_category values "
            "overstate the true total — filter to one category. Rates "
            "based on fewer than 5 deaths are suppressed to NULL at source "
            "(rate suppression only — the exact deaths count is always "
            "published), which leaves rate coverage sparse for small "
            "counties and rare categories (heroin, methadone). Demographic "
            "breakdowns (race, sex) exist only on statewide rows; county "
            "rows are all-demographics-combined because county-level "
            "demographic cells are almost entirely suppressed at source. "
            "The source's state-grain age and ethnicity breakdowns are not "
            "yet served (the ethnicity axis overlaps the race buckets and "
            "the platform has no age-bucket demographics yet). Cause "
            "definitions exclude deaths whose underlying cause is an "
            "ICD-10 mental/behavioral F-code ('Without F-Codes'), so "
            "totals may sit slightly below other published overdose "
            "series. Deaths are counted by county of residence. Recent "
            "years may be revised as late death certificates are filed."
        ),
        quality_checks=[
            {
                "name": "death_rate_per_100k_non_negative",
                "description": (
                    "Negative rate values are OASIS suppression sentinels "
                    "and must have been nulled — a surviving negative means "
                    "the sentinel mask broke. (Authored because per-100k "
                    "rates carry no unit marker.)"
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "death_rate_per_100k IS NOT NULL AND "
                    "death_rate_per_100k < 0"
                ),
                "mustBe": 0,
            },
            {
                "name": "age_adjusted_death_rate_per_100k_non_negative",
                "description": (
                    "Negative rate values are OASIS suppression sentinels "
                    "and must have been nulled."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "age_adjusted_death_rate_per_100k IS NOT NULL AND "
                    "age_adjusted_death_rate_per_100k < 0"
                ),
                "mustBe": 0,
            },
            {
                "name": "rates_null_only_when_deaths_1_to_4",
                "description": (
                    "Rate suppression at source applies exactly to rates "
                    "based on fewer than 5 deaths, and zero-death rows are "
                    "normalized to 0.0 — so a NULL rate must sit on a row "
                    "with 1-4 deaths."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(death_rate_per_100k IS NULL OR "
                    "age_adjusted_death_rate_per_100k IS NULL) AND "
                    "deaths NOT BETWEEN 1 AND 4"
                ),
                "mustBe": 0,
            },
            {
                "name": "zero_deaths_implies_zero_rates",
                "description": (
                    "A zero-death row has a true rate of 0 (normalized from "
                    "the source's inconsistent zero rendering) — both rates "
                    "must be exactly 0."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE deaths = 0 AND "
                    "(death_rate_per_100k IS NULL OR death_rate_per_100k "
                    "<> 0 OR age_adjusted_death_rate_per_100k IS NULL OR "
                    "age_adjusted_death_rate_per_100k <> 0)"
                ),
                "mustBe": 0,
            },
            {
                "name": "demographic_breakdowns_state_only",
                "description": (
                    "The source publishes demographic breakdowns only at "
                    "state grain — every county row must be demographic = "
                    "'all'."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE county_fips IS "
                    "NOT NULL AND demographic <> 'all'"
                ),
                "mustBe": 0,
            },
            {
                "name": "county_deaths_sum_to_state_total",
                "description": (
                    "Deaths are never suppressed and every county is "
                    "published, so the 159 county rows must sum EXACTLY to "
                    "the statewide 'all' row for every (year, "
                    "drug_category)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, drug_category, "
                    "MAX(CASE WHEN county_fips IS NULL AND demographic = "
                    "'all' THEN deaths END) AS state_total, "
                    "SUM(CASE WHEN county_fips IS NOT NULL THEN deaths "
                    "END) AS county_sum "
                    "FROM {object} GROUP BY year, drug_category"
                    ") WHERE state_total IS NULL OR county_sum IS NULL OR "
                    "state_total <> county_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "race_deaths_partition_to_state_total",
                "description": (
                    "The seven race buckets (split asian / pacific_islander "
                    "convention, including the always-zero race_unknown) "
                    "are mutually exclusive and exhaustive — they must sum "
                    "EXACTLY to the statewide 'all' row for every (year, "
                    "drug_category)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, drug_category, "
                    "MAX(CASE WHEN demographic = 'all' THEN deaths END) "
                    "AS all_deaths, "
                    "SUM(CASE WHEN demographic IN ('asian', 'black', "
                    "'multiracial', 'native_american', 'pacific_islander', "
                    "'race_unknown', 'white') THEN deaths END) AS race_sum "
                    "FROM {object} WHERE county_fips IS NULL "
                    "GROUP BY year, drug_category"
                    ") WHERE all_deaths IS NULL OR race_sum IS NULL OR "
                    "all_deaths <> race_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "sex_deaths_partition_to_state_total",
                "description": (
                    "Female + male deaths must sum EXACTLY to the statewide "
                    "'all' row for every (year, drug_category)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, drug_category, "
                    "MAX(CASE WHEN demographic = 'all' THEN deaths END) "
                    "AS all_deaths, "
                    "SUM(CASE WHEN demographic IN ('female', 'male') THEN "
                    "deaths END) AS sex_sum "
                    "FROM {object} WHERE county_fips IS NULL "
                    "GROUP BY year, drug_category"
                    ") WHERE all_deaths IS NULL OR sex_sum IS NULL OR "
                    "all_deaths <> sex_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "opioid_category_hierarchy",
                "description": (
                    "Category containment: all_opioids deaths cannot exceed "
                    "all_drug_overdoses, and no opioid sub-type can exceed "
                    "all_opioids, within any (year, geography, demographic) "
                    "cell. (Sub-types may legitimately SUM above "
                    "all_opioids — poly-drug overlap.)"
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, demographic, "
                    "MAX(CASE WHEN drug_category = 'all_drug_overdoses' "
                    "THEN deaths END) AS all_drugs, "
                    "MAX(CASE WHEN drug_category = 'all_opioids' THEN "
                    "deaths END) AS opioids, "
                    "MAX(CASE WHEN drug_category = 'heroin' THEN deaths "
                    "END) AS heroin, "
                    "MAX(CASE WHEN drug_category = 'methadone' THEN deaths "
                    "END) AS methadone, "
                    "MAX(CASE WHEN drug_category = "
                    "'natural_semisynthetic_synthetic_opioids' THEN deaths "
                    "END) AS nss_opioids, "
                    "MAX(CASE WHEN drug_category = "
                    "'synthetic_opioids_excl_methadone' THEN deaths END) "
                    "AS synthetic "
                    "FROM {object} GROUP BY year, county_fips, demographic"
                    ") WHERE opioids > all_drugs OR heroin > opioids OR "
                    "methadone > opioids OR nss_opioids > opioids OR "
                    "synthetic > opioids"
                ),
                "mustBe": 0,
            },
            {
                "name": "all_159_counties_every_year_and_category",
                "description": (
                    "OASIS publishes a full county grid (deaths are never "
                    "suppressed) — every (year, drug_category) must have "
                    "exactly 159 county rows."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, drug_category, COUNT(*) AS n "
                    "FROM {object} WHERE county_fips IS NOT NULL "
                    "GROUP BY year, drug_category"
                    ") WHERE n <> 159"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_demographic_grid_complete",
                "description": (
                    "Every (year, drug_category) must have exactly 10 "
                    "statewide rows: 'all' + 7 race buckets + female + "
                    "male."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, drug_category, COUNT(*) AS n "
                    "FROM {object} WHERE county_fips IS NULL "
                    "GROUP BY year, drug_category"
                    ") WHERE n <> 10"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
