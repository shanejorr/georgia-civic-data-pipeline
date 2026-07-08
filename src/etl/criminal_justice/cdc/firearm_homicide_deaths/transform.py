"""Transform CDC WONDER firearm/homicide mortality exports into a gold fact table.

Source: CDC WONDER Multiple Cause of Death (NCHS/NVSS death certificates) —
8 tab-delimited exports: 4 cause categories x 2 dataset vintages, Georgia
counties, 1999-2024. Gold serves county x year x cause_category with deaths,
population, crude death rate, and (bridged-race years only) age-adjusted
death rate — both rates per 100,000 residents.

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Dataset vintages are stitched, never blended: D77 serves 1999-2017, D157
  serves 2018-2024.** The two WONDER vintages (D77 bridged-race 1999-2020;
  D157 single-race 2018-2024) overlap 2018-2020. The overlap is verified
  IDENTICAL at runtime (raw-string equality on Deaths incl. 'Suppressed'
  markers, and on Population; numeric crude rates equal where both publish) —
  a hard assertion, so the stitch introduces no discontinuity in counts.
  D157 wins the overlap because (a) it publishes 853 more numeric crude-rate
  cells there (rates for 0- and 10-19-death rows that D77 masks 'Unreliable',
  incl. every 2018-2020 legal-intervention rate) and the crude rate is the
  key metric, (b) rate conventions then stay uniform across the whole
  single-race era instead of flipping mid-era at 2021, and (c) future WONDER
  refreshes extend D157 naturally. Cost: 114 age-adjusted-rate cells that
  D77 publishes for 2018-2020 are forgone (age_adjusted_rate_per_100k is
  served 1999-2017 only). The year-derived ``dataset_vintage`` categorical
  (bridged_race / single_race) makes the methodology break machine-readable —
  the same versioning pattern as nibrs_offenses' ``coverage`` flag.
- **cause_category is a NON-ADDITIVE grain categorical.** The four WONDER
  cause definitions overlap: firearm_homicide is a subset of BOTH
  firearm_deaths (all-intent firearm deaths) and homicide (all-mechanism
  homicides), and legal_intervention deaths are mostly firearm deaths too.
  Summing deaths across cause_category values double-counts; the
  categorical-with-documentation shape matches the overdose_deaths
  drug_category precedent, and containment is enforced by an authored
  quality check (firearm_homicide <= firearm_deaths and <= homicide).
- **Suppression -> NULL, never 0** (§8 + domain rule). 'Suppressed' (death
  count 1-9, privacy) NULLs the count and its rates; 'Unreliable' (D77 rates
  from < 20 deaths, including all D77 zero-death rows) NULLs the rate only —
  the count survives. True zeros are published as 0 (show-zeros was on) and
  are real. Marker-vs-NULL accounting is exact: after the strict=False cast,
  each column's null count must equal its marker count (any other junk value
  hard-fails), and every mask is recorded on the manifest per column x
  cause x marker. In the D157 era zero-death rows carry a real 0.0 crude
  rate and rates are published for ALL unsuppressed counts, so crude-rate
  NULL density drops at the 2017->2018 vintage boundary (documented; the
  null-rate-spike warning has this known cause).
- **95%% CI columns are dropped.** D157 publishes crude-rate lower/upper 95%%
  CI bounds (D77 does not). They are not served: no other topic serves
  interval estimates, the platform metric vocabulary has no CI concept, and
  they would be NULL for 1999-2017. Documented here and in the contract
  limitations; the bronze files retain them for a future additive change.
- **Rates are per 100,000 population — named *_per_100k, no `unit`.** Same
  sanctioned-unclassifiable treatment as overdose_deaths: `proportion` and
  `ratio` both misdescribe a per-100k rate, so the rate columns declare no
  unit and carry authored non-negativity quality checks instead.
- **Key metric: crude_rate_per_100k** (§4c: rate over count; the
  age-adjusted rate is absent 2018+, the crude rate spans every year).
  deaths is its numerator and population its denominator (both
  metric_component-flagged counts). population is never suppressed.
- **No state rows.** WONDER omitted totals ("Totals are not available ...
  due to suppression constraints") and a state total cannot be recomputed
  from county rows (suppressed cells are missing) — county detail level
  only, county_fips never NULL.
- **Dedup tie-break.** The stitch filter (D77 rows with year >= 2018 dropped
  before concat, after the overlap-identity assertion) makes cross-vintage
  duplicates structurally impossible, so `deduplicate_by_levels` is a
  belt-and-braces no-op: sort_col="deaths" (prefer the fuller row) and the
  removed count is asserted to be exactly 0.
- **No §4b impossible-value masks.** After suppression handling, counts and
  rates are non-negative by construction; the maxima (county crude rate
  65.3 per 100k; 258 deaths in Fulton) are extreme-but-conceivable published
  values and are preserved.
- **Local TSV reader.** `read_bronze_file` cannot parse WONDER's layout
  (tab-delimited with a '---'-delimited footer metadata block), so
  `_read_wonder_tsv` reads it directly — same read-loss accounting contract
  (raw data-line count vs parsed rows) as the shared reader, mirroring the
  overdose_deaths `read_oasis_csv` precedent.
"""

import io
import logging
from pathlib import Path

import polars as pl

from src.utils.metadata import write_data_dictionary
from src.utils.readers import list_bronze_files
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

TOPIC = "firearm_homicide_deaths"
BRONZE_DIR = Path("data/bronze/criminal_justice/cdc/firearm_homicide_deaths")
GOLD_DIR = Path("data/gold/criminal_justice/firearm_homicide_deaths")
SOURCE_URL = "https://wonder.cdc.gov/mcd.html"

# The four WONDER cause definitions, keyed by the filename slug (the part
# before '_by_county_year_'); values are the gold cause_category codes
# (identical — the slugs are already canonical snake_case). OVERLAPPING,
# never additive: firearm_homicide ⊆ firearm_deaths and ⊆ homicide.
CAUSE_CATEGORIES: dict[str, str] = {
    "firearm_deaths": "firearm_deaths",
    "firearm_homicide": "firearm_homicide",
    "homicide": "homicide",
    "legal_intervention": "legal_intervention",
}
CAUSE_CATEGORY_VALUES: list[str] = sorted(CAUSE_CATEGORIES.values())

# Era detection by column signature (most-specific first): only D157 carries
# CI columns; only D77 carries the age-adjusted rate.
ERA_SIGNATURES: dict[str, list[str]] = {
    "d157_single_race": ["Crude Rate Upper 95% Confidence Interval"],
    "d77_bridged_race": ["Age Adjusted Rate"],
}
VINTAGE_BY_ERA: dict[str, str] = {
    "d77_bridged_race": "bridged_race",
    "d157_single_race": "single_race",
}
DATASET_VINTAGE_VALUES: list[str] = sorted(VINTAGE_BY_ERA.values())

# Stitch boundary (see module docstring): D77 serves 1999-2017; the verified-
# identical 2018-2020 D77 overlap rows are dropped in favor of D157.
D157_START_YEAR = 2018
OVERLAP_YEARS = (2018, 2019, 2020)

# WONDER cell markers (verbatim in bronze; the ONLY permitted non-numeric
# values — anything else in a metric cell hard-fails the marker accounting).
SUPPRESSED = "Suppressed"  # death count 1-9 (privacy); count AND rates masked
UNRELIABLE = "Unreliable"  # D77 rate from < 20 deaths; rate masked, count kept

FOOTER_MARKER = '"---"'
N_COUNTIES = 159

METRIC_COLUMNS: list[str] = [
    "deaths",
    "population",
    "crude_rate_per_100k",
    "age_adjusted_rate_per_100k",
]

# Gold fact column order. `detail_level` is carried through dedup/export
# splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "county_fips",
    "cause_category",
    "dataset_vintage",
    *METRIC_COLUMNS,
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "county_fips": pl.Utf8,
    "cause_category": pl.Utf8,
    "dataset_vintage": pl.Utf8,
    "deaths": pl.Int64,
    "population": pl.Int64,
    "crude_rate_per_100k": pl.Float64,
    "age_adjusted_rate_per_100k": pl.Float64,
    "detail_level": pl.Utf8,
}

# dataset_vintage is deliberately EXCLUDED so any cross-vintage duplicate
# (a stitch-filter bug) collides loudly in the guard instead of surviving
# as two rows per key.
NATURAL_KEYS: list[str] = ["year", "county_fips", "cause_category", "detail_level"]

# Bronze metric column -> (gold name, markers legal in that column, dtype).
# D157 has no Age Adjusted Rate (absent columns are skipped per file) and
# publishes no 'Unreliable' markers — enforced by the marker accounting.
METRIC_SOURCE_SPEC: list[tuple[str, str, set[str], pl.DataType]] = [
    ("Deaths", "deaths", {SUPPRESSED}, pl.Int64),
    ("Population", "population", set(), pl.Int64),  # never suppressed
    ("Crude Rate", "crude_rate_per_100k", {SUPPRESSED, UNRELIABLE}, pl.Float64),
    (
        "Age Adjusted Rate",
        "age_adjusted_rate_per_100k",
        {SUPPRESSED, UNRELIABLE},
        pl.Float64,
    ),
]


# =============================================================================
# Bronze reading
# =============================================================================


def _read_wonder_tsv(path: Path) -> tuple[pl.DataFrame, dict]:
    """Read a CDC WONDER TSV export, stopping at the '---' footer block.

    WONDER exports are tab-delimited with a header row, N data rows, then a
    literal "---" line followed by ~60 footer rows (Dataset, Query
    Parameters, Caveats) that are not tabular data. Parsing stops at the
    FIRST footer marker; everything above it is data. All columns are read
    as Utf8 (infer_schema_length=0) so suppression markers and zero-padded
    FIPS codes survive intact.

    Returns (df, loss) with the same read-loss accounting contract as
    read_bronze_file: raw_rows = physical data-line count, parsed_rows =
    frame height.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        footer_at = next(
            i for i, line in enumerate(lines) if line.strip() == FOOTER_MARKER
        )
    except StopIteration:
        raise ValueError(
            f"{path.name}: no {FOOTER_MARKER} footer marker found — not a "
            "complete WONDER export (truncated download?)"
        ) from None

    header, data_lines = lines[0], lines[1:footer_at]
    df = pl.read_csv(
        io.StringIO("\n".join([header, *data_lines])),
        separator="\t",
        quote_char='"',
        infer_schema_length=0,  # all Utf8: keep markers + zero-padded FIPS
    )
    loss = {"raw_rows": len(data_lines), "parsed_rows": df.height, "format": "tsv"}
    return df, loss


def _parse_cause_slug(filename: str) -> str:
    """Extract the cause-category slug from a WONDER export filename.

    The cause is encoded in the filename ONLY (nothing inside the file
    identifies it except the footer Query Parameters), so an unknown slug
    must hard-fail rather than be guessed.
    """
    slug = filename.split("_by_county_year_")[0]
    if slug not in CAUSE_CATEGORIES:
        raise ValueError(
            f"{filename}: unknown cause slug {slug!r} — a new WONDER export "
            "must be mapped in CAUSE_CATEGORIES, never guessed"
        )
    return slug


# =============================================================================
# Overlap verification (the never-blend guarantee)
# =============================================================================


def _verify_overlap_identity(
    d77_raw: pl.DataFrame, d157_raw: pl.DataFrame, cause: str
) -> None:
    """Assert the 2018-2020 vintage overlap is identical before stitching.

    Deaths (including 'Suppressed' markers) and Population must match as raw
    strings for every overlap county-year; numeric crude rates must match
    where BOTH vintages publish one. The only sanctioned asymmetry is rate
    availability: D77 masks < 20-death rates 'Unreliable' where D157
    publishes them. Any other divergence means the vintages disagree and the
    stitch decision must be revisited — hard fail.
    """
    overlap_years = [str(y) for y in OVERLAP_YEARS]
    lhs = d77_raw.filter(pl.col("Year Code").is_in(overlap_years)).select(
        pl.col("County Code").alias("county_fips"),
        pl.col("Year Code").alias("year"),
        pl.col("Deaths").alias("deaths_d77"),
        pl.col("Population").alias("population_d77"),
        pl.col("Crude Rate").cast(pl.Float64, strict=False).alias("crude_d77"),
    )
    rhs = d157_raw.filter(pl.col("Year Code").is_in(overlap_years)).select(
        pl.col("County Code").alias("county_fips"),
        pl.col("Year Code").alias("year"),
        pl.col("Deaths").alias("deaths_d157"),
        pl.col("Population").alias("population_d157"),
        pl.col("Crude Rate").cast(pl.Float64, strict=False).alias("crude_d157"),
    )
    expected = N_COUNTIES * len(OVERLAP_YEARS)
    joined = lhs.join(rhs, on=["county_fips", "year"], how="full", coalesce=True)
    if lhs.height != expected or rhs.height != expected or joined.height != expected:
        raise ValueError(
            f"{cause}: overlap grids misaligned — d77={lhs.height}, "
            f"d157={rhs.height}, joined={joined.height}, expected {expected}"
        )

    mismatched = joined.filter(
        (pl.col("deaths_d77") != pl.col("deaths_d157"))
        | pl.col("deaths_d77").is_null()
        | pl.col("deaths_d157").is_null()
        | (pl.col("population_d77") != pl.col("population_d157"))
        | (
            pl.col("crude_d77").is_not_null()
            & pl.col("crude_d157").is_not_null()
            & ((pl.col("crude_d77") - pl.col("crude_d157")).abs() > 1e-9)
        )
    )
    if mismatched.height:
        raise ValueError(
            f"{cause}: {mismatched.height} overlap county-year(s) DIVERGE "
            f"across vintages — never blend; investigate before stitching. "
            f"Sample:\n{mismatched.head(10)}"
        )
    logger.info(
        "%s: 2018-2020 vintage overlap verified identical (%d county-years)",
        cause,
        expected,
    )


# =============================================================================
# Per-file transform
# =============================================================================


def _cast_and_mask_metrics(
    df: pl.DataFrame,
    era: str,
    cause: str,
    path_name: str,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Cast metric columns, converting WONDER markers to NULL with accounting.

    For each metric column: bronze must have zero true nulls on data rows,
    and after the strict=False cast the null count must equal the marker
    count — so nothing non-numeric can slip to NULL unrecorded. Every mask
    is recorded on the manifest per column x cause x marker (suppressed
    counts 1-9; D77 unreliable rates from < 20 deaths).
    """
    exprs: list[pl.Expr] = []
    mask_events: list[tuple[str, int, str, list[int]]] = []
    for src_col, gold_col, legal_markers, dtype in METRIC_SOURCE_SPEC:
        if src_col not in df.columns:
            # D157 files carry no Age Adjusted Rate (WONDER forbids it at
            # county grain there) — emit a typed NULL column, logged.
            logger.info(
                "%s: source column %r absent (era %s) — emitting NULL %s",
                path_name,
                src_col,
                era,
                gold_col,
            )
            exprs.append(pl.lit(None).cast(dtype).alias(gold_col))
            continue

        if df[src_col].null_count():
            raise ValueError(
                f"{path_name}: {df[src_col].null_count()} true-null cells in "
                f"{src_col!r} — bronze data rows should never be blank"
            )
        junk = df.filter(
            pl.col(src_col).cast(pl.Float64, strict=False).is_null()
            & ~pl.col(src_col).is_in(sorted(legal_markers))
        )
        if junk.height:
            raise ValueError(
                f"{path_name}: {junk.height} non-numeric {src_col!r} cells "
                f"that are not known markers: {junk[src_col].unique().to_list()[:5]}"
            )
        for marker, reason in (
            (SUPPRESSED, "cdc_wonder_suppressed_death_count_1_to_9"),
            (UNRELIABLE, "cdc_wonder_unreliable_rate_from_lt_20_deaths"),
        ):
            if marker not in legal_markers:
                continue
            hit = df.filter(pl.col(src_col) == marker)
            if hit.height:
                mask_events.append(
                    (
                        gold_col,
                        hit.height,
                        f"{reason} ({cause}, {era})",
                        sorted(hit["year"].unique().to_list()),
                    )
                )
        exprs.append(pl.col(src_col).cast(dtype, strict=False).alias(gold_col))

    df = df.with_columns(exprs)
    for gold_col, count, reason, years in mask_events:
        manifest.record_masked(gold_col, count, reason, years=years)
    return df


def transform_file(
    path: Path,
    df_raw: pl.DataFrame,
    era: str,
    loss: dict,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Reshape one WONDER export to gold columns, applying the vintage stitch.

    Uses 'Year Code' (the 'Year' column carries a '2024 ' trailing-space
    defect in D157 files) and 'County Code' (already 5-char zero-padded
    FIPS). D77 rows in the verified-identical 2018-2020 overlap are dropped
    here — recorded as filtered — so D157 serves those years (module
    docstring).
    """
    cause = CAUSE_CATEGORIES[_parse_cause_slug(path.name)]
    df = df_raw.with_columns(
        pl.col("Year Code").cast(pl.Int32, strict=False).alias("year"),
        pl.col("County Code").alias("county_fips"),
    )
    if df["year"].null_count():
        raise ValueError(f"{path.name}: unparseable 'Year Code' values")
    bad_fips = df.filter(~pl.col("county_fips").str.contains(r"^13\d{3}$"))
    if bad_fips.height:
        raise ValueError(
            f"{path.name}: {bad_fips.height} malformed county FIPS: "
            f"{bad_fips['county_fips'].unique().to_list()[:5]}"
        )

    max_year = int(df["year"].max())
    manifest.record_read_loss(
        max_year, path.name, int(loss["raw_rows"]), int(loss["parsed_rows"])
    )
    manifest.record_file(path, max_year, era, df_raw.height, df_raw.columns)
    # Bronze accounting covers the FULL file (overlap rows included); the
    # stitch drop below is recorded as filtered so bronze - filtered = gold.
    for row in df.group_by("year").len().sort("year").to_dicts():
        manifest.record_bronze(int(row["year"]), int(row["len"]))

    if era == "d77_bridged_race":
        # Vintage stitch: D157 wins the verified-identical 2018-2020 overlap
        # (more published crude rates — see module docstring for the full
        # rationale). Exact per-year drop counts are asserted.
        dropped = df.filter(pl.col("year") >= D157_START_YEAR)
        df = df.filter(pl.col("year") < D157_START_YEAR)
        drop_counts = {
            int(r["year"]): int(r["len"])
            for r in dropped.group_by("year").len().to_dicts()
        }
        if drop_counts != {y: N_COUNTIES for y in OVERLAP_YEARS}:
            raise ValueError(
                f"{path.name}: unexpected overlap-drop shape {drop_counts}; "
                f"expected {N_COUNTIES} rows for each of {OVERLAP_YEARS}"
            )
        for year, n in sorted(drop_counts.items()):
            manifest.record_filtered(
                year, n, "d77_overlap_year_served_from_d157_vintage"
            )
        logger.info(
            "%s: dropped %d verified-identical 2018-2020 overlap rows "
            "(served from the single-race vintage instead)",
            path.name,
            dropped.height,
        )

    df = _cast_and_mask_metrics(df, era, cause, path.name, manifest)
    if df["population"].null_count():
        raise ValueError(
            f"{path.name}: NULL population values — WONDER never suppresses "
            "population denominators; investigate"
        )

    return df.with_columns(
        pl.lit(cause).alias("cause_category"),
        pl.lit(VINTAGE_BY_ERA[era]).alias("dataset_vintage"),
        pl.lit("county").alias("detail_level"),
    ).select(STANDARD_COLUMNS)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for firearm_homicide_deaths."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read all 8 exports up front (era-detected by column signature) so
    # the cross-vintage overlap identity can be asserted per cause BEFORE
    # any stitching. The full 4-cause x 2-vintage matrix is required.
    files = list_bronze_files(BRONZE_DIR, extensions=[".txt"])
    raw: dict[tuple[str, str], tuple[Path, pl.DataFrame, dict]] = {}
    for path in files:
        df_raw, loss = _read_wonder_tsv(path)
        era = detect_era_by_columns(df_raw, ERA_SIGNATURES)
        if era is None:
            raise ValueError(f"{path.name}: columns match no known WONDER era")
        raw[(_parse_cause_slug(path.name), era)] = (path, df_raw, loss)
    expected_matrix = {(c, e) for c in CAUSE_CATEGORIES for e in ERA_SIGNATURES}
    if set(raw) != expected_matrix:
        raise ValueError(
            f"Bronze file matrix incomplete: missing {expected_matrix - set(raw)}"
        )

    # 2. Never-blend gate: assert the 2018-2020 overlap is identical across
    # vintages for every cause, then transform each file (stitch applied).
    all_dfs: list[pl.DataFrame] = []
    for cause in sorted(CAUSE_CATEGORIES):
        _verify_overlap_identity(
            raw[(cause, "d77_bridged_race")][1],
            raw[(cause, "d157_single_race")][1],
            cause,
        )
        for era in sorted(ERA_SIGNATURES):
            path, df_raw, loss = raw[(cause, era)]
            df = transform_file(path, df_raw, era, loss, manifest)
            if df.height > 0:
                all_dfs.append(df)

    # 3. Harmonize + concat, then record the filename-derived cause and the
    # era-derived vintage categoricals (both identity-coded at this point).
    combined = pl.concat(harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES))
    manifest.record_categorical(
        column="cause_category",
        map_dict=CAUSE_CATEGORIES,
        bronze_series=combined["cause_category"],
        gold_series=combined["cause_category"],
    )
    manifest.record_categorical(
        column="dataset_vintage",
        map_dict={v: v for v in VINTAGE_BY_ERA.values()},
        bronze_series=combined["dataset_vintage"],
        gold_series=combined["dataset_vintage"],
    )

    # 4. Collision guard (keys EXCLUDE dataset_vintage so any stitch bug
    # surfaces as a divergent duplicate), then a belt-and-braces dedup:
    # the stitch makes duplicates structurally impossible, so the tie-break
    # (sort_col="deaths", prefer the fuller row) must remove exactly 0 rows.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    before = combined.height
    combined = deduplicate_by_levels(
        combined,
        {"county": ["year", "county_fips", "cause_category"]},
        sort_col="deaths",
    )
    if before - combined.height != 0:
        raise ValueError(
            f"Dedup removed {before - combined.height} rows; the vintage "
            "stitch guarantees uniqueness, so any removal is a bug"
        )

    # 5. Geography nulling (shared domain seam; county-only topic, so this
    # is a no-op guard). No §4b masks apply — see module docstring.
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=CRIMINAL_JUSTICE_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. Known spike causes: age_adjusted_rate_per_100k is
    # structurally 100% NULL from 2018 (absent in the single-race vintage);
    # crude-rate NULL density falls at 2018 (D157 publishes < 20-death rates).
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning(
            "NULL-rate spikes (known causes: vintage rate conventions — see "
            "module docstring): %s",
            spike_result.details,
        )
    validate_output(
        combined,
        required_non_null=[
            "year",
            "county_fips",
            "cause_category",
            "dataset_vintage",
            "population",
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
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        title="Firearm and Homicide Deaths by County",
        summary=(
            "Firearm deaths, homicides, firearm homicides, and "
            "legal-intervention deaths with rates per 100,000 for Georgia "
            "counties by year, from death certificates, 1999 onward."
        ),
        description=(
            "Deaths and death rates per 100,000 residents for Georgia "
            "counties by year and cause category, from official death "
            "certificates (CDC WONDER Multiple Cause of Death, NCHS/NVSS), "
            "1999 onward. Four OVERLAPPING cause categories are served: all "
            "firearm deaths (any intent, including suicide), homicide (any "
            "mechanism), firearm homicide (the intersection of the first "
            "two), and legal intervention. A firearm homicide is counted in "
            "ALL THREE of the first categories, so deaths must NEVER be "
            "summed across cause_category values — always filter to a single "
            "category. Deaths are attributed to the decedent's county of "
            "residence. County-year death counts of 1-9 are suppressed at "
            "source (NULL); a 0 is a true zero. Two source vintages are "
            "stitched without overlap: bridged-race (1999-2017) and single-"
            "race (2018 onward), flagged by dataset_vintage; counts are "
            "verified identical across vintages in the overlap years, but "
            "rate availability differs (see column descriptions)."
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
                "nullable": False,
                "example": "13121",
                "description": (
                    "5-digit county FIPS code (state prefix 13) of the "
                    "decedent's county of residence; FK to the counties "
                    "dimension. Never NULL — this topic has no statewide "
                    "rows (CDC WONDER withholds state totals for these "
                    "queries due to suppression constraints, and a state "
                    "total cannot be recomputed from county rows because "
                    "suppressed cells are missing)."
                ),
            },
            {
                "name": "cause_category",
                "type": "string",
                "nullable": False,
                "validValues": CAUSE_CATEGORY_VALUES,
                "example": "firearm_homicide",
                "short_description": (
                    "Cause-of-death category — categories OVERLAP (a firearm "
                    "homicide is also a firearm death AND a homicide); never "
                    "sum across categories."
                ),
                "description": (
                    "Cause-of-death category (ICD-10 injury intent/mechanism "
                    "recodes of the underlying cause). THE CATEGORIES OVERLAP "
                    "AND ARE NOT ADDITIVE: firearm_deaths = all firearm "
                    "deaths of any intent (homicide + suicide + unintentional "
                    "+ legal intervention + undetermined); homicide = "
                    "homicides by any mechanism; firearm_homicide = homicide "
                    "intent AND firearm mechanism, a subset of BOTH of the "
                    "first two; legal_intervention = deaths caused by law "
                    "enforcement acting in the line of duty (any mechanism, "
                    "mostly firearm). Summing deaths across cause_category "
                    "values double-counts — always filter to ONE category."
                ),
            },
            {
                "name": "dataset_vintage",
                "type": "string",
                "nullable": False,
                "validValues": DATASET_VINTAGE_VALUES,
                "example": "single_race",
                "short_description": (
                    "Source methodology vintage: bridged_race serves "
                    "1999-2017, single_race serves 2018 onward (never "
                    "blended)."
                ),
                "description": (
                    "CDC WONDER dataset vintage serving the row — a "
                    "methodology flag, not an extra grain axis: each year is "
                    "served by exactly ONE vintage. bridged_race = Multiple "
                    "Cause of Death 1999-2020 with bridged-race population "
                    "denominators (serves 1999-2017 here); single_race = "
                    "Multiple Cause of Death 2018-present with single-race "
                    "denominators (serves 2018 onward). The vintages overlap "
                    "2018-2020 at source; death counts and populations are "
                    "verified identical there, and the single-race vintage "
                    "is served because it publishes crude rates for all "
                    "unsuppressed counts (the bridged-race vintage masks "
                    "rates from fewer than 20 deaths as 'Unreliable'). "
                    "Consequence: crude-rate coverage and zero-death rate "
                    "conventions change at the 2017/2018 boundary, and the "
                    "age-adjusted rate ends at 2017."
                ),
            },
            {
                "name": "deaths",
                "type": "int64",
                "unit": "count",
                "metric_component": "numerator",
                "example": 12,
                "null_meaning": (
                    "NULL = suppressed at source: the true count is 1-9 "
                    "(CDC privacy rule for sub-national death counts)."
                ),
                "short_description": (
                    "Resident deaths in the cause category (NULL = "
                    "suppressed count of 1-9; 0 is a true zero)."
                ),
                "description": (
                    "Count of resident deaths in the cause category. "
                    "Suppressed at source (NULL) when the true count is 1-9; "
                    "a published 0 is a true zero. 61-68%% of county-years "
                    "are suppressed for the firearm/homicide categories — "
                    "expected for rare events at county grain. Numerator of "
                    "crude_rate_per_100k. NOT additive across cause_category "
                    "values (see cause_category)."
                ),
            },
            {
                "name": "population",
                "type": "int64",
                "unit": "count",
                "metric_component": "denominator",
                "nullable": False,
                "example": 28877,
                "short_description": (
                    "County resident population (rate denominator; never suppressed)."
                ),
                "description": (
                    "County resident population for the year — the "
                    "denominator of the death rates. Never suppressed. "
                    "Bridged-race postcensal/intercensal estimates through "
                    "2017; single-race estimates from 2018 (2024 uses "
                    "Vintage 2024 postcensal estimates). Identical across "
                    "the four cause categories for a county-year."
                ),
            },
            {
                "name": "crude_rate_per_100k",
                "type": "float64",
                "key_metric": True,
                "example": 17.6,
                "null_meaning": (
                    "NULL = masked at source: the death count is suppressed "
                    "(1-9), or — 1999-2017 rows only — the rate is based on "
                    "fewer than 20 deaths and flagged 'Unreliable'."
                ),
                "short_description": (
                    "Crude death rate per 100,000 residents (NULL when the "
                    "count is suppressed; through 2017 also when based on "
                    "fewer than 20 deaths)."
                ),
                "description": (
                    "Crude death rate per 100,000 residents (source-"
                    "computed; equals deaths / population x 100,000). NOT on "
                    "the platform's 0-1 rate scale — the natural unit is "
                    "deaths per 100,000. NULL whenever deaths is suppressed. "
                    "Additionally, on bridged_race rows (1999-2017) WONDER "
                    "masks rates computed from fewer than 20 deaths as "
                    "'Unreliable' (NULL here, count preserved), including "
                    "all zero-death rows; on single_race rows (2018 onward) "
                    "rates are published for every unsuppressed count and "
                    "zero-death rows carry a true 0.0. Rate coverage "
                    "therefore improves sharply from 2018."
                ),
            },
            {
                "name": "age_adjusted_rate_per_100k",
                "type": "float64",
                "example": 15.8,
                "null_meaning": (
                    "NULL on all rows from 2018 onward (not published at "
                    "county grain in the single-race vintage); on 1999-2017 "
                    "rows, NULL = suppressed count (1-9) or rate based on "
                    "fewer than 20 deaths ('Unreliable')."
                ),
                "short_description": (
                    "Age-adjusted death rate per 100,000 (2000 US standard "
                    "population); published 1999-2017 only."
                ),
                "description": (
                    "Age-adjusted death rate per 100,000 residents (source-"
                    "computed, standardized to the 2000 US standard "
                    "population) — preferable to the crude rate when "
                    "comparing counties with different age structures. NOT "
                    "on the platform's 0-1 rate scale. Published on "
                    "bridged_race rows (1999-2017) only: CDC WONDER does not "
                    "permit age-adjusted rates at county grain in the "
                    "single-race vintage, so every row from 2018 onward is "
                    "NULL. On 1999-2017 rows it shares the crude rate's "
                    "masking (NULL when the count is suppressed or the rate "
                    "is based on fewer than 20 deaths)."
                ),
            },
        ],
        source=(
            "CDC WONDER, Multiple Cause of Death (NCHS/NVSS death "
            "certificates; bridged-race 1999-2020 and single-race "
            "2018-present datasets)"
        ),
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        usage=(
            "Cite: Centers for Disease Control and Prevention, National "
            "Center for Health Statistics, Multiple Cause of Death data on "
            "CDC WONDER (wonder.cdc.gov). ALWAYS filter to a single "
            "cause_category — the categories overlap (a firearm homicide is "
            "also a firearm death and a homicide) and summing across them "
            "double-counts. Do not sum county deaths into a state total: "
            "suppressed county-years (counts of 1-9) are missing, so the "
            "sum understates the true total. Use crude_rate_per_100k for "
            "the full time series; age_adjusted_rate_per_100k (1999-2017 "
            "only) for cross-county comparisons in those years. Compare "
            "rate coverage across the 2017/2018 dataset_vintage boundary "
            "with care."
        ),
        limitations=(
            "County-year death counts of 1-9 are suppressed at source "
            "(NULL, never zero) — 61-68%% of county-years for the firearm "
            "and homicide categories — so small-county coverage is sparse "
            "and county sums understate state totals (no state rows are "
            "served; WONDER withholds them for these queries). Cause "
            "categories overlap and are not additive. Two source vintages "
            "are stitched at 2017/2018 (dataset_vintage): death counts are "
            "verified identical in the source overlap, but rate conventions "
            "differ — through 2017 rates from fewer than 20 deaths "
            "(including zero-death rows) are masked 'Unreliable' (NULL), "
            "while from 2018 rates are published for every unsuppressed "
            "count; the age-adjusted rate is unavailable from 2018 at "
            "county grain. The source's crude-rate 95%% confidence-interval "
            "bounds (published 2018 onward) are not served. Deaths are "
            "counted by county of residence, not occurrence. 2024 "
            "populations are Vintage 2024 postcensal estimates and recent "
            "years may be revised."
        ),
        quality_checks=[
            {
                "name": "crude_rate_per_100k_non_negative",
                "description": (
                    "Rates cannot be negative. (Authored because per-100k "
                    "rates carry no unit marker.)"
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "crude_rate_per_100k IS NOT NULL AND "
                    "crude_rate_per_100k < 0"
                ),
                "mustBe": 0,
            },
            {
                "name": "age_adjusted_rate_per_100k_non_negative",
                "description": (
                    "Rates cannot be negative. (Authored because per-100k "
                    "rates carry no unit marker.)"
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "age_adjusted_rate_per_100k IS NOT NULL AND "
                    "age_adjusted_rate_per_100k < 0"
                ),
                "mustBe": 0,
            },
            {
                "name": "suppressed_deaths_implies_null_rates",
                "description": (
                    "WONDER suppresses the rates whenever the death count "
                    "is suppressed — a NULL deaths cell can never carry a "
                    "published rate."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE deaths IS NULL "
                    "AND (crude_rate_per_100k IS NOT NULL OR "
                    "age_adjusted_rate_per_100k IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "bridged_race_rates_require_20_deaths",
                "description": (
                    "In the bridged-race vintage (1999-2017) WONDER masks "
                    "rates computed from fewer than 20 deaths as "
                    "'Unreliable' — a published rate on such a row means "
                    "the marker handling broke."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE dataset_vintage = "
                    "'bridged_race' AND deaths IS NOT NULL AND deaths < 20 "
                    "AND (crude_rate_per_100k IS NOT NULL OR "
                    "age_adjusted_rate_per_100k IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "single_race_crude_rate_coverage",
                "description": (
                    "In the single-race vintage every unsuppressed count "
                    "has a published crude rate, and a zero-death row has a "
                    "true rate of exactly 0."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE dataset_vintage = "
                    "'single_race' AND ((deaths IS NOT NULL AND "
                    "crude_rate_per_100k IS NULL) OR (deaths = 0 AND "
                    "crude_rate_per_100k <> 0))"
                ),
                "mustBe": 0,
            },
            {
                "name": "age_adjusted_rate_bridged_race_only",
                "description": (
                    "CDC WONDER does not publish age-adjusted rates at "
                    "county grain in the single-race vintage — every "
                    "single_race row must have a NULL age-adjusted rate."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE dataset_vintage = "
                    "'single_race' AND age_adjusted_rate_per_100k IS NOT NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "crude_rate_reconciles_with_deaths_and_population",
                "description": (
                    "The published crude rate must equal deaths / "
                    "population x 100,000 within source rounding (rates are "
                    "published to 1 decimal, so max rounding error 0.05)."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "crude_rate_per_100k IS NOT NULL AND deaths IS NOT NULL "
                    "AND population > 0 AND ABS(crude_rate_per_100k - "
                    "deaths * 100000.0 / population) > 0.051"
                ),
                "mustBe": 0,
            },
            {
                "name": "vintage_year_alignment",
                "description": (
                    "The vintage stitch is a clean year split: bridged_race "
                    "serves 1999-2017 and single_race serves 2018 onward — "
                    "each year comes from exactly one vintage (never "
                    "blended)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE (dataset_vintage "
                    "= 'bridged_race' AND year NOT BETWEEN 1999 AND 2017) "
                    "OR (dataset_vintage = 'single_race' AND year < 2018)"
                ),
                "mustBe": 0,
            },
            {
                "name": "firearm_homicide_contained_in_parents",
                "description": (
                    "Category containment: firearm_homicide (homicide "
                    "intent AND firearm mechanism) can exceed neither "
                    "firearm_deaths nor homicide within a county-year, "
                    "wherever both counts are published."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, "
                    "MAX(CASE WHEN cause_category = 'firearm_deaths' THEN "
                    "deaths END) AS fd, "
                    "MAX(CASE WHEN cause_category = 'homicide' THEN deaths "
                    "END) AS hom, "
                    "MAX(CASE WHEN cause_category = 'firearm_homicide' "
                    "THEN deaths END) AS fh "
                    "FROM {object} GROUP BY year, county_fips"
                    ") WHERE fh IS NOT NULL AND ((fd IS NOT NULL AND fh > "
                    "fd) OR (hom IS NOT NULL AND fh > hom))"
                ),
                "mustBe": 0,
            },
            {
                "name": "population_consistent_across_causes",
                "description": (
                    "The population denominator is a property of the "
                    "county-year, not the cause — all four cause rows for a "
                    "county-year must carry the same population."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, COUNT(DISTINCT population) "
                    "AS n FROM {object} GROUP BY year, county_fips"
                    ") WHERE n <> 1"
                ),
                "mustBe": 0,
            },
            {
                "name": "all_159_counties_every_year_and_cause",
                "description": (
                    "WONDER publishes a full county grid (show-zeros was "
                    "on; suppression NULLs cells, never removes rows) — "
                    "every (year, cause_category) must have exactly 159 "
                    "county rows."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, cause_category, COUNT(*) AS n "
                    "FROM {object} GROUP BY year, cause_category"
                    ") WHERE n <> 159"
                ),
                "mustBe": 0,
            },
            {
                "name": "all_four_causes_every_year",
                "description": (
                    "Every served year must carry all four cause "
                    "categories (the county-grid check alone cannot detect "
                    "a whole missing cause)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, COUNT(DISTINCT cause_category) AS n "
                    "FROM {object} GROUP BY year"
                    ") WHERE n <> 4"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
