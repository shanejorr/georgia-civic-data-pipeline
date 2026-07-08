"""Transform GA DPH OASIS violent/external-cause mortality exports into gold.

Source: OASIS Data Table Tool (death-certificate data, Georgia Office of Vital
Records) — 20 CSVs: 4 violent/external-cause categories x 5 layouts (county x
year + state-grain age/race/ethnicity/sex breakdowns), 1994-2024. Gold serves
county x year x cause_of_death (all-demographics) plus state x year x
cause_of_death x demographic (race and sex breakdowns), with deaths, crude
death rate, and age-adjusted death rate (both per 100,000 population).

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **cause_of_death is a NON-ADDITIVE grain categorical.** Unlike the sibling
  overdose_deaths (whose drug categories overlap), the four OASIS detailed
  causes here — homicide (Assault), suicide (Intentional Self-Harm),
  legal_intervention, accidental_shooting (unintentional firearm) — are
  MUTUALLY EXCLUSIVE (each death has exactly one underlying cause). They are
  still non-additive in the served sense: they are 4 of many external causes,
  so there is no all-causes rollup row and their sum is not a served total —
  no 'all' value is fabricated. Same categorical-with-documentation shape as
  overdose_deaths / hate_crimes; the dashboard's required-single-select
  behavior applies.
- **ICD-9 -> ICD-10 comparability break versioned via icd_revision.** Deaths
  are ICD-9-coded for 1994-1998 and ICD-10-coded from 1999 (the NCHS
  comparability break). Per the domain rule "version methodological breaks,
  never pool across them" (COJ/ASJ coverage-flag precedent), the fact table
  carries an `icd_revision` categorical ('icd9' for 1994-1998, 'icd10' from
  1999), enforced by an authored quality check, so consumers can never draw
  1994-2024 as one seamless series without seeing the flag; the limitations
  prose documents the break.
- **Demographics: race + sex served at state grain; age + ethnicity deferred
  to v2** — identical reasoning to overdose_deaths: breakdowns exist ONLY at
  state grain; race publishes the post-1997 OMB split pair (separate Asian
  and Native Hawaiian/Other Pacific Islander buckets -> asian /
  pacific_islander; no §5b remap — the 7 buckets, incl. the all-zero Unknown,
  sum exactly to All Races for all 4 causes, e.g. homicide 1,058 in 2023) and
  sex reconciles exactly. Age needs a demographics-dimension expansion;
  OASIS ethnicity is a separate axis overlapping the race buckets (serving
  both would break §5a exclusivity within race). The 8 skipped files remain
  in bronze, checksummed and analyzed.
- **Suppression sentinels are numeric, nulled by value.** Rates carry
  negative sentinels (-5 = suppressed, fewer than 5 deaths; -2 = no
  population denominator — one 1999 suicide NHOPI row with deaths=1; other
  codes possible on refresh) — any negative rate -> NULL (never 0), masked
  counts recorded on the manifest. Death COUNTS are never suppressed: an
  empty deaths cell is a true zero per OASIS (verified by exact
  reconciliation: counties, race buckets, and sexes each sum to the state
  total) and is filled with 0. Zero-death rows render their rates
  inconsistently (0.0 or empty) and are normalized to 0.0 — a true-zero-
  deaths row has a true rate of 0 (positive-rate contradictions hard-fail).
- **Rates are per 100,000 population — named *_per_100k, no `unit`.** Same
  rationale as overdose_deaths: `proportion` and `ratio` both misdescribe a
  per-100k rate, so the columns declare no unit and carry authored
  non-negativity quality checks instead.
- **Key metric: death_rate_per_100k** (crude rate) — present at every served
  grain (age-adjusted rates are structurally absent for a future age
  breakdown). deaths is its numerator; the population denominator is not
  published.
- **Derived duplicate rows dropped with equality assertions** (shared OASIS
  helpers): 'selected_years_total' year rows, 'County Summary' geography rows
  (assert equal to the Georgia row), and 'Selected {Races|Sexes} Total'
  breakdown rows (assert equal to the 'All ...' row).
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
  non-negative counts; the max county homicide rate (89.4 per 100k, a small
  county with an unsuppressed count) is extreme-but-conceivable, preserved.
- **OASIS vs CDC WONDER.** OASIS has no all-intents firearm cause (only
  accidental_shooting); the platform's canonical firearm series is the
  cdc/firearm_homicide_deaths topic. Both derive from the same NCHS
  underlying-cause death certificates, residence-based — the contract
  limitations cross-reference the two homicide series to prevent confusion.
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

TOPIC = "violent_deaths"
BRONZE_DIR = Path("data/bronze/criminal_justice/dph_oasis/violent_deaths")
GOLD_DIR = Path("data/gold/criminal_justice/violent_deaths")
SOURCE_URL = "https://oasis.state.ga.us/dtt/mortality"

# The four OASIS violent/external-cause categories, keyed by the filename slug
# (the part before '__'); values are the gold cause_of_death codes (identical —
# the slugs are already canonical snake_case). MUTUALLY EXCLUSIVE, but with no
# all-causes rollup: never sum them to fabricate a total (module docstring).
CAUSES: dict[str, str] = {
    "homicide": "homicide",
    "suicide": "suicide",
    "legal_intervention": "legal_intervention",
    "accidental_shooting": "accidental_shooting",
}
CAUSE_VALUES: list[str] = sorted(CAUSES.values())

# ICD-revision flag values: deaths are ICD-9-coded through 1998 and
# ICD-10-coded from 1999 (NCHS comparability break — module docstring).
ICD9_MAX_YEAR = 1998
ICD_REVISION_VALUES: list[str] = ["icd10", "icd9"]

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
    "cause_of_death",
    "icd_revision",
    *METRIC_COLUMNS,
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "county_fips": pl.Utf8,
    "demographic": pl.Utf8,
    "cause_of_death": pl.Utf8,
    "icd_revision": pl.Utf8,
    "deaths": pl.Int64,
    "death_rate_per_100k": pl.Float64,
    "age_adjusted_death_rate_per_100k": pl.Float64,
    "detail_level": pl.Utf8,
}

NATURAL_KEYS: list[str] = [
    "year",
    "county_fips",
    "demographic",
    "cause_of_death",
    "icd_revision",
    "detail_level",
]

# Race buckets served at state grain (post-1997 OMB split pair; sum exactly to
# the 'all' row per year x cause). Shared by the transform and the authored
# partition quality checks. race_unknown is published with zero deaths in
# every year to date.
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
    if cause_slug not in CAUSES:
        raise ValueError(
            f"{path.name}: unknown cause slug {cause_slug!r} — a new OASIS "
            "cause category must be mapped in CAUSES, never guessed"
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
        df.with_columns(
            pl.lit(CAUSES[cause_slug]).alias("cause_of_death"),
            # ICD-revision flag: the NCHS ICD-9 -> ICD-10 comparability break
            # sits at 1998/1999 — versioned as a fact column, never pooled.
            pl.when(pl.col("year") <= ICD9_MAX_YEAR)
            .then(pl.lit("icd9"))
            .otherwise(pl.lit("icd10"))
            .alias("icd_revision"),
        )
        .rename(RATE_RENAMES)
        .select(STANDARD_COLUMNS)
    )


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for violent_deaths."""
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

    # cause_of_death derives from the filename slug (identity map) and
    # icd_revision from the year — recorded so the manifest's categorical
    # coverage includes both.
    manifest.record_categorical(
        column="cause_of_death",
        map_dict=CAUSES,
        bronze_series=combined["cause_of_death"],
        gold_series=combined["cause_of_death"],
    )
    manifest.record_categorical(
        column="icd_revision",
        map_dict={v: v for v in ICD_REVISION_VALUES},
        bronze_series=combined["icd_revision"],
        gold_series=combined["icd_revision"],
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
                "deaths; -2 = not applicable, no population denominator)"
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
        state_all.height - state_all.select("year", "cause_of_death").unique().height
    )
    before = combined.height
    combined = deduplicate_by_levels(
        combined,
        {
            "county": ["year", "county_fips", "demographic", "cause_of_death"],
            "state": ["year", "demographic", "cause_of_death"],
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
    # county-rate maxima are extreme-but-conceivable and preserved.
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=CRIMINAL_JUSTICE_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. Rate NULLs are suppression (<5 deaths), which is
    # densest for the rare causes (legal_intervention, accidental_shooting)
    # — spikes are expected with a known cause and surface as warnings.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(
        combined,
        required_non_null=[
            "year",
            "demographic",
            "cause_of_death",
            "icd_revision",
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
        title="Violent Deaths by County",
        summary=(
            "Homicide, suicide, legal-intervention, and accidental-shooting "
            "deaths and death rates per 100,000 for Georgia counties by "
            "year, from death certificates, 1994 onward."
        ),
        description=(
            "Violent and external-cause deaths, crude death rates, and "
            "age-adjusted death rates (both per 100,000 population) for "
            "Georgia, from official death-certificate data (Georgia "
            "Department of Public Health OASIS, Office of Vital Records), "
            "1994 onward. Four MUTUALLY EXCLUSIVE cause categories are "
            "served: homicide (Assault), suicide (Intentional Self-Harm), "
            "legal intervention (deaths caused by law enforcement), and "
            "accidental shooting (unintentional firearm deaths). Each death "
            "has exactly one underlying cause, but the four causes are only "
            "a subset of all external causes — there is NO all-causes total "
            "row and summing across cause_of_death values does not produce "
            "any published total; always filter to a single cause. County x "
            "year rows cover all demographics combined; statewide rows add "
            "race and sex breakdowns. Deaths are ICD-9-coded for 1994-1998 "
            "and ICD-10-coded from 1999 (icd_revision flag) — trends across "
            "that break are approximate. Rates based on fewer than 5 deaths "
            "are suppressed at source (NULL); death counts are never "
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
                "name": "cause_of_death",
                "type": "string",
                "nullable": False,
                "validValues": CAUSE_VALUES,
                "example": "homicide",
                "short_description": (
                    "OASIS cause category — the four causes are mutually "
                    "exclusive but have no all-causes total; filter to one."
                ),
                "description": (
                    "OASIS detailed cause-of-death category. The four causes "
                    "are MUTUALLY EXCLUSIVE (each death has exactly one "
                    "underlying cause): homicide = Assault (deaths "
                    "deliberately inflicted by another person, excluding "
                    "legal intervention); suicide = Intentional Self-Harm; "
                    "legal_intervention = deaths caused by law-enforcement "
                    "action; accidental_shooting = unintentional firearm "
                    "deaths (OASIS's only firearm-specific cause — for "
                    "all-intents firearm deaths use the "
                    "firearm_homicide_deaths topic from CDC WONDER). There "
                    "is NO all-causes rollup: the four categories are a "
                    "subset of all external causes, so their sum is not a "
                    "published total — always filter to a single cause."
                ),
            },
            {
                "name": "icd_revision",
                "type": "string",
                "nullable": False,
                "validValues": ICD_REVISION_VALUES,
                "example": "icd10",
                "short_description": (
                    "Cause-coding revision: icd9 for 1994-1998, icd10 from "
                    "1999 — a comparability break, not one seamless series."
                ),
                "description": (
                    "ICD revision used to code the underlying cause of "
                    "death: 'icd9' for deaths in 1994-1998, 'icd10' from "
                    "1999 onward (the NCHS comparability break). Cause "
                    "definitions differ slightly between revisions, so "
                    "trend comparisons spanning 1998/1999 are approximate — "
                    "treat the two revisions as separate series rather than "
                    "one seamless 1994-2024 trend. The flag is a pure "
                    "function of year."
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
                    "Resident deaths from the cause (never suppressed; 0 is "
                    "a true zero)."
                ),
                "description": (
                    "Count of resident deaths from the cause. Never "
                    "suppressed at source: 0 is a true zero (bronze renders "
                    "zeros as empty cells, filled to 0 here — verified by "
                    "exact reconciliation: county, race, and sex slices "
                    "each sum to the statewide total). Numerator of the "
                    "death rates. The four cause_of_death values are "
                    "mutually exclusive but do not sum to any published "
                    "total (see cause_of_death)."
                ),
            },
            {
                "name": "death_rate_per_100k",
                "type": "float64",
                "key_metric": True,
                "example": 8.9,
                "null_meaning": (
                    "NULL = suppressed at source: rate based on fewer than "
                    "5 deaths (the row's exact deaths count, 1-4, is still "
                    "published)."
                ),
                "short_description": (
                    "Crude death rate per 100,000 residents (suppressed to "
                    "NULL when based on fewer than 5 deaths)."
                ),
                "description": (
                    "Crude death rate per 100,000 residents "
                    "(source-computed). NOT on the platform's 0-1 rate "
                    "scale — the natural unit is deaths per 100,000 "
                    "population. Suppressed at source (NULL, bronze "
                    "sentinel -5) when based on fewer than 5 deaths — the "
                    "row's exact deaths count is still published, so heavy "
                    "NULL density in small counties and for the rare causes "
                    "(legal_intervention, accidental_shooting) is expected. "
                    "One 1999 suicide pacific_islander row is NULL from the "
                    "source's not-applicable sentinel (-2, no population "
                    "denominator). 0.0 on zero-death rows (normalized from "
                    "the source's inconsistent zero rendering)."
                ),
            },
            {
                "name": "age_adjusted_death_rate_per_100k",
                "type": "float64",
                "example": 9.4,
                "null_meaning": (
                    "NULL = suppressed at source: rate based on fewer than 5 deaths."
                ),
                "short_description": (
                    "Age-adjusted death rate per 100,000 (2000 US standard population)."
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
            "filter to a single cause_of_death — the causes are mutually "
            "exclusive but have no all-causes total, so a sum across them "
            "is not a published statistic. Filter to a single demographic "
            "axis (race OR sex) on statewide rows. Use "
            "age_adjusted_death_rate_per_100k for cross-county or cross-"
            "group comparisons; deaths are additive across counties within "
            "one cause (county deaths sum exactly to the statewide row). "
            "Treat icd_revision = 'icd9' (1994-1998) and 'icd10' (1999 "
            "onward) as separate series when analyzing trends."
        ),
        limitations=(
            "Statewide rows have NULL county_fips. The four cause "
            "categories are mutually exclusive but cover only a subset of "
            "external causes — there is no all-causes rollup and summing "
            "across cause_of_death values does not reproduce any published "
            "total. Deaths are ICD-9-coded for 1994-1998 and ICD-10-coded "
            "from 1999 (icd_revision flag; NCHS comparability break) — "
            "cause definitions shift slightly at the break, so 1994-1998 "
            "is NOT seamlessly comparable with 1999 onward. Rates based on "
            "fewer than 5 deaths are suppressed to NULL at source (rate "
            "suppression only — the exact deaths count is always "
            "published), which leaves rate coverage sparse for small "
            "counties and the rare causes (legal_intervention, "
            "accidental_shooting). Demographic breakdowns (race, sex) "
            "exist only on statewide rows; county rows are all-"
            "demographics-combined. The source's state-grain age and "
            "ethnicity breakdowns are not yet served. OASIS has NO "
            "all-intents firearm category (accidental_shooting covers "
            "unintentional firearm deaths only) — for firearm deaths "
            "across intents, and for a second homicide series, see the "
            "firearm_homicide_deaths topic (CDC WONDER). Both series "
            "derive from the same NCHS death-certificate data and count "
            "deaths by county of residence, but they are not "
            "interchangeable: this topic's homicide counts all "
            "mechanisms and never suppresses counts, while the WONDER "
            "topic suppresses county-year counts of 1-9 and serves "
            "firearm-specific homicide; small definitional and revision-"
            "timing differences can also produce slightly different "
            "counts. Recent years may be revised as late death "
            "certificates are filed."
        ),
        quality_checks=[
            {
                "name": "death_rate_per_100k_non_negative",
                "description": (
                    "Negative rate values are OASIS suppression/N-A "
                    "sentinels and must have been nulled — a surviving "
                    "negative means the sentinel mask broke. (Authored "
                    "because per-100k rates carry no unit marker.)"
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
                    "Negative rate values are OASIS suppression/N-A "
                    "sentinels and must have been nulled."
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
                    "based on fewer than 5 deaths (the one -2 no-denominator "
                    "row also has deaths in 1-4), and zero-death rows are "
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
                "name": "icd_revision_partitions_at_1999",
                "description": (
                    "The ICD-revision flag is a pure function of year: "
                    "'icd9' for 1994-1998, 'icd10' from 1999 (NCHS "
                    "comparability break) — any other pairing means the "
                    "flag derivation broke."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(year <= 1998 AND icd_revision <> 'icd9') OR "
                    "(year >= 1999 AND icd_revision <> 'icd10')"
                ),
                "mustBe": 0,
            },
            {
                "name": "county_deaths_sum_to_state_total",
                "description": (
                    "Deaths are never suppressed and every county is "
                    "published, so the 159 county rows must sum EXACTLY to "
                    "the statewide 'all' row for every (year, "
                    "cause_of_death)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, cause_of_death, "
                    "MAX(CASE WHEN county_fips IS NULL AND demographic = "
                    "'all' THEN deaths END) AS state_total, "
                    "SUM(CASE WHEN county_fips IS NOT NULL THEN deaths "
                    "END) AS county_sum "
                    "FROM {object} GROUP BY year, cause_of_death"
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
                    "cause_of_death)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, cause_of_death, "
                    "MAX(CASE WHEN demographic = 'all' THEN deaths END) "
                    "AS all_deaths, "
                    "SUM(CASE WHEN demographic IN ('asian', 'black', "
                    "'multiracial', 'native_american', 'pacific_islander', "
                    "'race_unknown', 'white') THEN deaths END) AS race_sum "
                    "FROM {object} WHERE county_fips IS NULL "
                    "GROUP BY year, cause_of_death"
                    ") WHERE all_deaths IS NULL OR race_sum IS NULL OR "
                    "all_deaths <> race_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "sex_deaths_partition_to_state_total",
                "description": (
                    "Female + male deaths must sum EXACTLY to the statewide "
                    "'all' row for every (year, cause_of_death)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, cause_of_death, "
                    "MAX(CASE WHEN demographic = 'all' THEN deaths END) "
                    "AS all_deaths, "
                    "SUM(CASE WHEN demographic IN ('female', 'male') THEN "
                    "deaths END) AS sex_sum "
                    "FROM {object} WHERE county_fips IS NULL "
                    "GROUP BY year, cause_of_death"
                    ") WHERE all_deaths IS NULL OR sex_sum IS NULL OR "
                    "all_deaths <> sex_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "all_159_counties_every_year_and_cause",
                "description": (
                    "OASIS publishes a full county grid (deaths are never "
                    "suppressed) — every (year, cause_of_death) must have "
                    "exactly 159 county rows."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, cause_of_death, COUNT(*) AS n "
                    "FROM {object} WHERE county_fips IS NOT NULL "
                    "GROUP BY year, cause_of_death"
                    ") WHERE n <> 159"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_demographic_grid_complete",
                "description": (
                    "Every (year, cause_of_death) must have exactly 10 "
                    "statewide rows: 'all' + 7 race buckets + female + "
                    "male."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, cause_of_death, COUNT(*) AS n "
                    "FROM {object} WHERE county_fips IS NULL "
                    "GROUP BY year, cause_of_death"
                    ") WHERE n <> 10"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
