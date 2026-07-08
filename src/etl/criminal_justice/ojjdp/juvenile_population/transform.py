"""Transform bronze EZAPOP exports into a gold county/year population fact table.

Source: OJJDP Statistical Briefing Book — *Easy Access to Juvenile Populations*
(EZAPOP; NCJJ from Census Bureau / NCHS bridged-race county population
estimates). 28 CSV exports, each a county x year (1990-2024) matrix for one
population slice: the juvenile (ages 0-17) headline, total resident population
(all ages), 2 sex + 4 bridged-race + 2 ethnicity splits of juveniles, and 18
single-year-of-age files.

This is a DENOMINATOR topic: it supplies the county juvenile-population base
counts that turn the other criminal_justice topics' raw counts into rates.

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Grain: year x county_fips x demographic x age_group** — the source
  publishes one-way marginals only (no cross-tabs), so the grain never
  multiplies axes: demographic marginals (sex/race) exist only at
  age_group='00_17' (the slice the source splits), and age rows
  ('00'..'17', 'all_ages') exist only at demographic='all'. A structural
  quality check enforces this shape.
- **All 18 single ages are kept** (age_group '00'..'17') rather than
  pre-picked bands: preserving bronze granularity lets consumers rebuild ANY
  age band — notably ages 10-16, the Georgia delinquency-jurisdiction
  denominator (GA upper age = 16) matching EZACO's `popten` — without
  exploding the grain (age rows exist only at demographic='all', so the
  single ages add 18 rows per county-year, not 18 x 7).
- **'all_ages' rows are total resident population** (adults included) —
  kept as context/denominator for county-level rates, distinguished from
  juvenile counts by the explicit age_group level so the two can never be
  confused under one metric name.
- **Ethnicity is served as metric partition columns**
  (`hispanic_population` / `not_hispanic_population` on the demographic='all',
  age_group='00_17' rows), NOT as demographic rows — following the
  nibrs_arrests precedent: EZAPOP race is NCHS *bridged race* (each race
  bucket includes Hispanic and non-Hispanic persons) while ethnicity is a
  separate any-race marginal, and the shared demographics dimension registers
  `hispanic` in the `race` demographic_category — so emitting hispanic rows
  alongside the race rows would double-count when consumers sum the race axis
  (data-cleaning-standards §5a). Note this differs from decision_points,
  whose DJJ race buckets ARE Hispanic-exclusive and publish `hispanic` rows;
  the two classification systems are documented in the contract.
- **Asian / Pacific Islander (§5b).** Bronze has only 4 bridged-race buckets
  (White, Black, American Indian, Asian) with no Pacific Islander bucket
  anywhere, and the math test is exact: the 4 buckets sum to the juvenile
  total at every county x year (verified in bronze-data-structure.md), so
  bronze "Asian" is the pre-1997-OMB combined bucket. A topic-local remap
  sends it to `asian_pacific_islander` before normalization; there is no
  Multiracial bucket either (bridged-race estimates allocate multiracial
  persons into the 4 single-race buckets, which is why the sum is exact).
- **'All Counties' rows become state-level rows** (detail_level='state',
  county_fips NULL), matching the decision_points convention. Bronze verifies
  All Counties = sum of the 159 county rows exactly; a quality check keeps
  that invariant enforceable in gold.
- **Local reader.** `read_bronze_file` cannot parse the EZAPOP layout (a
  1-3-line quoted `Selecting:` preamble before the header, a 3-line citation
  footer, and a trailing comma on every data row), so `_read_ezapop_csv`
  reads it directly with the same read-loss accounting contract as the shared
  reader — mirroring the firearm_homicide_deaths `_read_wonder_tsv` and
  overdose_deaths `read_oasis_csv` precedents. The header row is located
  dynamically (first line whose first cell is `counts`), never by a
  hard-coded skip count. Each file's `Selecting:` block is asserted to carry
  the filter line its filename promises, and the derived `Total` column is
  verified against the horizontal sum of the 35 year columns (then dropped)
  so a column-shift parse bug cannot pass silently.
- **Dedup tie-break.** The 28 files are disjoint slices — each
  (year, county, demographic, age_group) cell comes from exactly one file —
  so post-concat duplicates are impossible by construction;
  `deduplicate_by_levels(sort_col="population")` remains as the documented
  safety net (prefer the fuller row) should a future refresh add an
  overlapping export. The collision guard runs first and would surface any
  divergent duplicate as a hard error rather than letting dedup pick a winner.
- **No suppression, no §4b masks.** Census-derived estimates with full
  coverage: every value in every file casts cleanly to a non-negative
  integer (verified across all 28 files in bronze-data-structure.md — no
  markers, no nulls), so `suppressed_to_null=False`, any NULL introduced by
  casting is treated as a parse bug (hard stop), and no impossible values
  exist to NULL. Zeros are real zeros (small counties genuinely have zero
  juveniles in some race buckets).
- **Estimates are a vintage.** The tool serves only the current estimate
  vintage (1990-2024, published 2026); historical values are revised between
  vintages. Bronze checksums pin the archival snapshot.
"""

import io
import logging
from pathlib import Path

import polars as pl

from src.utils.crosswalks import add_county_fips
from src.utils.demographics import DEMOGRAPHIC_ALIASES, normalize_demographic_column
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

TOPIC = "juvenile_population"
BRONZE_DIR = Path("data/bronze/criminal_justice/ojjdp/juvenile_population")
GOLD_DIR = Path("data/gold/criminal_justice/juvenile_population")
SOURCE_URL = "https://www.ojjdp.gov/ojstatbb/ezapop/"

# Expected data years (columns of every export) and expected data rows
# (All Counties + 159 county rows) — both verified in the structure doc.
EXPECTED_YEARS = [str(y) for y in range(1990, 2025)]
EXPECTED_DATA_ROWS = 160

STATEWIDE_LABEL = "All Counties"

# Combined pre-1997-OMB race bucket: bronze "Asian" includes Pacific
# Islanders (math test exact — see module docstring / §5b). The remap runs
# BEFORE normalize_demographic_column so the shared aliases stay untouched.
ASIAN_COMBINED_LABEL = "Asian/Pacific Islander"

# Each bronze file is one population slice, encoded in the filename (and
# echoed in the in-file `Selecting:` preamble, which is asserted against
# `selecting` below). `demographic_raw` is the source-style label fed to the
# shared demographic normalizer; ethnicity files instead land in a metric
# partition column (`ethnicity_col`) — see module docstring.
AGE_JUVENILES = "00_17"
FILE_SLICES: dict[str, dict[str, str]] = {
    "ezapop_ga_county_year_all_ages.csv": {
        "demographic_raw": "All",
        "age_group": "all_ages",
        # No Age/Sex/Race/Ethnicity filter — the Year line is the whole block.
        "selecting": "Year = 1990",
    },
    "ezapop_ga_county_year_juveniles_age00_17.csv": {
        "demographic_raw": "All",
        "age_group": AGE_JUVENILES,
        "selecting": (
            "Age = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17"
        ),
    },
    "ezapop_ga_county_year_juveniles_sex_male.csv": {
        "demographic_raw": "Male",
        "age_group": AGE_JUVENILES,
        "selecting": "Sex = Male",
    },
    "ezapop_ga_county_year_juveniles_sex_female.csv": {
        "demographic_raw": "Female",
        "age_group": AGE_JUVENILES,
        "selecting": "Sex = Female",
    },
    "ezapop_ga_county_year_juveniles_race_white.csv": {
        "demographic_raw": "White",
        "age_group": AGE_JUVENILES,
        "selecting": "Race = White",
    },
    "ezapop_ga_county_year_juveniles_race_black.csv": {
        "demographic_raw": "Black",
        "age_group": AGE_JUVENILES,
        "selecting": "Race = Black",
    },
    "ezapop_ga_county_year_juveniles_race_american_indian.csv": {
        "demographic_raw": "American Indian",
        "age_group": AGE_JUVENILES,
        "selecting": "Race = American Indian",
    },
    "ezapop_ga_county_year_juveniles_race_asian.csv": {
        # §5b combined-bucket remap (see module docstring).
        "demographic_raw": ASIAN_COMBINED_LABEL,
        "age_group": AGE_JUVENILES,
        "selecting": "Race = Asian",
    },
    "ezapop_ga_county_year_juveniles_ethnicity_hispanic.csv": {
        "ethnicity_col": "hispanic_population",
        "selecting": "Ethnicity = Hispanic",
    },
    "ezapop_ga_county_year_juveniles_ethnicity_non_hispanic.csv": {
        "ethnicity_col": "not_hispanic_population",
        "selecting": "Ethnicity = Non Hispanic",
    },
    # Single year of age, juveniles only (demographic='all').
    **{
        f"ezapop_ga_county_year_age_{age:02d}.csv": {
            "demographic_raw": "All",
            "age_group": f"{age:02d}",
            "selecting": f"Age = {age}",
        }
        for age in range(18)
    },
}

SINGLE_AGE_VALUES = [f"{age:02d}" for age in range(18)]
AGE_GROUP_VALUES = ["all_ages", AGE_JUVENILES, *SINGLE_AGE_VALUES]

RACE_DEMOGRAPHICS = ["asian_pacific_islander", "black", "native_american", "white"]
SEX_DEMOGRAPHICS = ["female", "male"]
DEMOGRAPHIC_VALUES = sorted(["all", *SEX_DEMOGRAPHICS, *RACE_DEMOGRAPHICS])

ETHNICITY_COLUMNS = ["hispanic_population", "not_hispanic_population"]

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "county_fips",
    "demographic",
    "age_group",
    "population",
    *ETHNICITY_COLUMNS,
    "detail_level",
]

METRIC_COLUMNS: list[str] = ["population", *ETHNICITY_COLUMNS]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "county_fips": pl.Utf8,
    "demographic": pl.Utf8,
    "age_group": pl.Utf8,
    **{c: pl.Int64 for c in METRIC_COLUMNS},
    "detail_level": pl.Utf8,
}

NATURAL_KEYS: list[str] = [
    "year",
    "county_fips",
    "demographic",
    "age_group",
    "detail_level",
]


# =============================================================================
# Local EZAPOP reader
# =============================================================================


def _read_ezapop_csv(path: Path) -> tuple[pl.DataFrame, dict, list[str]]:
    """Read one EZAPOP county-comparison CSV export.

    The layout: 2 quoted title lines, a blank line, a 1-3-line quoted
    `Selecting:` filter block, the header row (`counts,1990,...,2024,Total`),
    160 data rows (each with a trailing comma -> empty 38th field), then a
    blank line and a 3-line citation footer. The header row is located
    dynamically as the first line whose first cell is `counts` (the preamble
    length varies with the number of filters); data stops at the first blank
    line after it.

    All columns are read as Utf8 (infer_schema_length=0) and cast explicitly
    by the caller. Returns (df, loss, preamble_lines) with the same read-loss
    accounting contract as read_bronze_file: raw_rows = physical data-line
    count between header and footer, parsed_rows = frame height.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    header_at = next(
        (
            i
            for i, line in enumerate(lines)
            if line.lstrip().startswith(('"counts"', "counts,"))
        ),
        None,
    )
    if header_at is None:
        raise ValueError(f"{path.name}: no 'counts' header row found — layout changed?")

    data_lines: list[str] = []
    for line in lines[header_at + 1 :]:
        if not line.strip():
            break  # blank line separates data from the citation footer
        data_lines.append(line)

    df = pl.read_csv(
        io.StringIO("\n".join([lines[header_at], *data_lines])),
        infer_schema_length=0,  # all Utf8; cast explicitly (skill rule 4.3b)
    )
    # Every data row ends with a trailing comma, which parses as an unnamed
    # empty final column — drop it (structure doc "trailing empty" artifact).
    empty_cols = [c for c in df.columns if df[c].drop_nulls().is_empty()]
    df = df.drop(empty_cols)

    loss = {"raw_rows": len(data_lines), "parsed_rows": df.height, "format": "csv"}
    return df, loss, lines[:header_at]


def _verify_export(
    df: pl.DataFrame, preamble: list[str], expected_selecting: str, label: str
) -> None:
    """Guard one export's shape: slice identity, row count, columns, Total.

    - The `Selecting:` preamble must carry the filter line the filename
      promises, so a mis-saved export cannot be ingested under the wrong slice.
    - Exactly 160 data rows (All Counties + 159 counties) and the 35 expected
      year columns + Total.
    - The derived `Total` column must equal the horizontal sum of the 35 year
      columns on every row — an exact parse-integrity check (verified exact in
      bronze) that catches any column shift or truncation.
    """
    preamble_text = "\n".join(preamble)
    if expected_selecting not in preamble_text:
        raise ValueError(
            f"{label}: 'Selecting:' block lacks expected filter "
            f"{expected_selecting!r} — file/slice mismatch. Preamble: "
            f"{preamble_text!r}"
        )
    if df.height != EXPECTED_DATA_ROWS:
        raise ValueError(
            f"{label}: expected {EXPECTED_DATA_ROWS} data rows "
            f"(All Counties + 159 counties), got {df.height}"
        )
    missing = [c for c in ["counts", *EXPECTED_YEARS, "Total"] if c not in df.columns]
    if missing:
        raise ValueError(f"{label}: missing expected column(s): {missing}")

    bad_totals = (
        df.with_columns(
            pl.sum_horizontal(
                [pl.col(y).cast(pl.Int64, strict=False) for y in EXPECTED_YEARS]
            ).alias("_year_sum"),
            pl.col("Total").cast(pl.Int64, strict=False).alias("_total"),
        )
        .filter(
            pl.col("_year_sum").is_null()
            | pl.col("_total").is_null()
            | (pl.col("_year_sum") != pl.col("_total"))
        )
        .height
    )
    if bad_totals:
        raise ValueError(
            f"{label}: {bad_totals} row(s) where Total != sum of year columns "
            "— parse integrity failure (column shift or non-integer values)"
        )


# =============================================================================
# Per-file transform
# =============================================================================


def _unpivot_years(df: pl.DataFrame, label: str) -> pl.DataFrame:
    """Unpivot the 35 year columns to long (county_raw, year, population).

    The derived `Total` column is dropped (row sum across years — verified by
    `_verify_export`, not a served metric). Population casts must introduce
    zero NULLs: this source has no suppression, so a NULL after casting is a
    parse bug, not data (hard stop).
    """
    long = (
        df.select("counts", *EXPECTED_YEARS)
        .unpivot(
            index="counts", on=EXPECTED_YEARS, variable_name="year", value_name="_raw"
        )
        .with_columns(
            pl.col("counts").alias("county_raw"),
            pl.col("year").cast(pl.Int32),
            pl.col("_raw").cast(pl.Int64, strict=False).alias("population"),
        )
        .drop("counts", "_raw")
    )
    n_null = long["population"].null_count()
    if n_null:
        raise ValueError(
            f"{label}: {n_null} NULL(s) casting population — bronze has zero "
            "nulls and no suppression; investigate the source format"
        )
    return long


def transform_file(path: Path, manifest: TransformManifest) -> tuple[str, pl.DataFrame]:
    """Read + reshape one bronze export into a tagged long frame.

    Returns ("base", df) for the 26 demographic/age slices (columns:
    county_raw, year, demographic, age_group, population) or
    ("ethnicity", df) for the 2 ethnicity marginals (columns: county_raw,
    year, <ethnicity_col>), which main() pivots into metric partition columns.
    The slice comes from the FILE_SLICES map keyed by filename — an unknown
    filename is a hard stop (it would mean unanalyzed bronze slipped past the
    freshness gate).
    """
    slice_spec = FILE_SLICES.get(path.name)
    if slice_spec is None:
        raise ValueError(f"Unexpected bronze file (not in FILE_SLICES): {path.name}")

    df, loss, preamble = _read_ezapop_csv(path)
    _verify_export(df, preamble, slice_spec["selecting"], path.name)

    # The files span 1990-2024 internally; record_file's single year slot gets
    # the max data year, matching the decision_points convention.
    manifest.record_read_loss(2024, path.name, loss["raw_rows"], loss["parsed_rows"])
    manifest.record_file(path, 2024, "ezapop_county_comparison", df.height, df.columns)

    long = _unpivot_years(df, path.name)
    # Per-year bronze accounting on the unpivoted county-cells (160 per year
    # per file), accumulated across the 28 files.
    for row in long.group_by("year").len().sort("year").to_dicts():
        manifest.record_bronze(row["year"], row["len"])

    ethnicity_col = slice_spec.get("ethnicity_col")
    if ethnicity_col:
        logger.info(
            "Processing %s as ethnicity partition column %s", path.name, ethnicity_col
        )
        return "ethnicity", long.rename({"population": ethnicity_col})

    raw_label = slice_spec["demographic_raw"]
    long = long.with_columns(
        pl.lit(raw_label).alias("_demographic_raw"),
        normalize_demographic_column(pl.lit(raw_label)).alias("demographic"),
        pl.lit(slice_spec["age_group"]).alias("age_group"),
    )
    # Effective-slice recording (skill rule 4.3a): only the alias this file's
    # label actually hit, so map_used stays reviewable while the unmapped
    # guard is preserved. The race_asian file's label arrives here already
    # remapped to the combined bucket; the map documents the original bronze
    # label "Asian" -> asian_pacific_islander decision (§5b).
    bronze_label = "Asian" if raw_label == ASIAN_COMBINED_LABEL else raw_label
    manifest.record_categorical(
        column="demographic",
        map_dict={bronze_label: DEMOGRAPHIC_ALIASES[raw_label.upper()]},
        bronze_series=pl.Series([bronze_label]),
        gold_series=long["demographic"],
    )
    manifest.record_categorical(
        column="age_group",
        map_dict={path.name: slice_spec["age_group"]},
        bronze_series=pl.Series([path.name]),
        gold_series=long["age_group"],
    )
    logger.info(
        "Processing %s as demographic=%s age_group=%s",
        path.name,
        long["demographic"][0],
        slice_spec["age_group"],
    )
    return "base", long.drop("_demographic_raw")


# =============================================================================
# Assembly helpers
# =============================================================================


def _join_ethnicity(
    base: pl.DataFrame, ethnicity_frames: list[pl.DataFrame]
) -> pl.DataFrame:
    """Attach the two ethnicity marginals as metric partition columns.

    The ethnicity exports cover juveniles 0-17 as a whole (no cross-tabs), so
    hispanic_population / not_hispanic_population are populated ONLY on the
    demographic='all', age_group='00_17' rows and NULL everywhere else — a
    structural NULL (split not published for that slice), not suppression.
    Join coverage is guarded: every (all, 00_17) cell must receive both values.
    """
    if len(ethnicity_frames) != 2:
        raise ValueError(
            f"Expected 2 ethnicity files, got {len(ethnicity_frames)} — "
            "bronze inventory changed"
        )
    eth = ethnicity_frames[0].join(
        ethnicity_frames[1], on=["county_raw", "year"], how="full", coalesce=True
    )
    if eth.select(pl.any_horizontal(pl.all().is_null().any())).item():
        raise ValueError(
            "Ethnicity files disagree on county/year coverage — "
            "hispanic and non-hispanic exports must align exactly"
        )

    is_target = (pl.col("demographic") == "all") & (
        pl.col("age_group") == AGE_JUVENILES
    )
    base = base.join(eth, on=["county_raw", "year"], how="left").with_columns(
        [
            pl.when(is_target).then(pl.col(c)).otherwise(None).alias(c)
            for c in ETHNICITY_COLUMNS
        ]
    )
    uncovered = base.filter(
        is_target
        & (
            pl.col("hispanic_population").is_null()
            | pl.col("not_hispanic_population").is_null()
        )
    )
    if uncovered.height:
        raise ValueError(
            f"{uncovered.height} juvenile-total cell(s) missing an ethnicity "
            f"value after join: {uncovered.head(5)}"
        )
    return base


def _resolve_geography(df: pl.DataFrame, manifest: TransformManifest) -> pl.DataFrame:
    """Split detail levels and resolve county names to FIPS.

    'All Counties' is the statewide aggregate -> detail_level='state' with
    NULL county_fips (decision_points convention). Every other name must
    resolve against the global counties dimension ('De Kalb' resolves via the
    COUNTY_NAME_OVERRIDES spacing-variant entry); an unmatched name is a hard
    stop, never a silent NULL.
    """
    df = df.with_columns(
        pl.when(pl.col("county_raw") == STATEWIDE_LABEL)
        .then(pl.lit("state"))
        .otherwise(pl.lit("county"))
        .alias("detail_level")
    )
    df = add_county_fips(df, "county_raw")
    unmatched = df.filter(
        pl.col("county_fips").is_null() & (pl.col("detail_level") == "county")
    )
    if unmatched.height:
        raise ValueError(
            "Unmatched county name(s) — add to COUNTY_NAME_OVERRIDES: "
            f"{unmatched['county_raw'].unique().sort().to_list()}"
        )

    # Record the observed name -> FIPS mapping; the statewide label maps to an
    # explicit non-FIPS marker so the manifest shows it handled deliberately.
    county_map = {
        row["county_raw"]: row["county_fips"]
        for row in df.select("county_raw", "county_fips")
        .unique()
        .drop_nulls("county_fips")
        .to_dicts()
    }
    county_map[STATEWIDE_LABEL] = "state_row_no_county_fips"
    manifest.record_categorical(
        column="county_fips",
        map_dict=county_map,
        bronze_series=df["county_raw"],
        gold_series=df["county_fips"],
    )
    return df.drop("county_raw")


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for juvenile_population."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + reshape every bronze export (read-loss accounted per file).
    base_frames: list[pl.DataFrame] = []
    ethnicity_frames: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR):
        kind, frame = transform_file(path, manifest)
        if kind == "ethnicity":
            ethnicity_frames.append(frame)
        else:
            base_frames.append(frame)
    if not base_frames:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    combined = pl.concat(base_frames)

    # 2. Ethnicity marginals become metric partition columns on the juvenile
    # total rows (module docstring); the 2 x 160 bronze rows per year that
    # fold into columns are recorded as explicitly filtered so the per-year
    # bronze-vs-gold accounting stays explainable.
    combined = _join_ethnicity(combined, ethnicity_frames)
    for year in range(1990, 2025):
        manifest.record_filtered(
            year,
            2 * EXPECTED_DATA_ROWS,
            "ethnicity_marginal_rows_pivoted_to_partition_columns",
        )

    # 3. Geography: state/county split + name -> FIPS resolution.
    combined = _resolve_geography(combined, manifest)
    combined = harmonize_columns([combined], STANDARD_COLUMNS, TARGET_TYPES)[0]
    logger.info("Combined %d gold-shaped rows", combined.height)

    # 4. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean a slice-routing bug and must raise, not be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: the 28 exports are disjoint one-way slices, so every cell
    # comes from exactly one file and duplicates are impossible by
    # construction; sort_col "population" is the documented safety net
    # (prefer the fuller row) should a future refresh overlap slices.
    combined = deduplicate_by_levels(
        combined,
        {
            "county": ["year", "county_fips", "demographic", "age_group"],
            "state": ["year", "demographic", "age_group"],
        },
        sort_col="population",
    )

    # 5. Geography nulling (shared domain rules). No §4b masks apply — every
    # value is a clean non-negative Census-estimate integer (module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=CRIMINAL_JUSTICE_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. population is fully non-null (no suppression); the
    # ethnicity columns carry a constant structural null pattern across years,
    # so any per-year spike would indicate a transform regression.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(
        combined,
        required_non_null=[
            "year",
            "detail_level",
            "demographic",
            "age_group",
            "population",
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
    ``detail_level`` — the contract's properties (and the validator's schema
    check) follow it.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "County-level population denominators for Georgia, 1990-2024, from "
            "OJJDP's Easy Access to Juvenile Populations (EZAPOP; NCJJ "
            "tabulations of Census Bureau / NCHS bridged-race county "
            "population estimates): juveniles (ages 0-17) per county per "
            "year — the base counts for turning juvenile-justice counts into "
            "rates — split by sex, bridged race, Hispanic ethnicity, and "
            "single year of age (so any age band can be rebuilt, e.g. ages "
            "10-16 for Georgia's delinquency jurisdiction), plus total "
            "resident population (all ages) for context."
        ),
        title="Juvenile Population Estimates",
        summary=(
            "Georgia county juvenile (ages 0-17) population estimates by sex, "
            "race, ethnicity, and single year of age, 1990-2024 — rate "
            "denominators for juvenile-justice data."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": "Calendar year of the population estimate.",
            },
            {
                "name": "county_fips",
                "type": "string",
                "example": "13121",
                "description": (
                    "5-digit county FIPS code (state prefix 13) of the Georgia "
                    "county; FK to the counties dimension. NULL on state-level "
                    "rows (the source's 'All Counties' aggregate, which equals "
                    "the sum of the 159 county rows exactly)."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "all",
                "validValues": DEMOGRAPHIC_VALUES,
                "short_description": (
                    "Population group the row covers: all juveniles, one sex "
                    "group, or one race group."
                ),
                "description": (
                    "Demographic slice. Two overlapping axes plus the total "
                    "are packed into this column: 'all', sex (female/male), "
                    "and bridged race (asian_pacific_islander/black/"
                    "native_american/white) — filter to one axis; summing "
                    "across axes double-counts. Sex and race splits are "
                    "published for the juvenile total only, so non-'all' "
                    "values appear only where age_group = '00_17'. Race is "
                    "NCHS bridged race: each bucket includes persons of both "
                    "Hispanic and non-Hispanic ethnicity (ethnicity is served "
                    "separately in hispanic_population / "
                    "not_hispanic_population), there is no multiracial bucket "
                    "(multiracial persons are allocated into the four "
                    "single-race buckets), and the source's 'Asian' bucket is "
                    "the pre-1997 OMB combined Asian + Pacific Islander "
                    "bucket (the four race buckets sum exactly to the "
                    "juvenile total), hence asian_pacific_islander. NOTE: "
                    "this race classification differs from sources with "
                    "Hispanic-exclusive race buckets (e.g. the decision_points "
                    "topic) — when computing race-specific rates against such "
                    "sources, document the mismatch."
                ),
            },
            {
                "name": "age_group",
                "type": "string",
                "nullable": False,
                "example": "00_17",
                "validValues": sorted(AGE_GROUP_VALUES),
                "short_description": (
                    "Age slice: all juveniles (00_17), a single year of age "
                    "(00-17), or the total resident population (all_ages)."
                ),
                "description": (
                    "Age slice of the row. '00_17' is the juvenile total "
                    "(ages 0-17) — the headline denominator; '00'..'17' are "
                    "single years of age (published for demographic = 'all' "
                    "only), which sum exactly to '00_17' and let consumers "
                    "build any age band — e.g. ages 10-16, Georgia's "
                    "delinquency-jurisdiction population (upper age 16); "
                    "'all_ages' is the total resident population including "
                    "adults (context/denominator for county-level rates, "
                    "demographic = 'all' only). Never sum across age_group "
                    "values that overlap ('00_17' and 'all_ages' contain the "
                    "single ages)."
                ),
            },
            {
                "name": "population",
                "type": "int64",
                "nullable": False,
                "unit": "count",
                "key_metric": True,
                "example": 16130,
                "short_description": (
                    "Estimated residents in the county, year, demographic "
                    "group, and age slice."
                ),
                "description": (
                    "Estimated resident population of the cell (Census Bureau "
                    "/ NCHS bridged-race county estimates as tabulated by "
                    "NCJJ). Never NULL — the source has full coverage of all "
                    "159 counties in every year with no suppression; zeros "
                    "are real (small counties can have zero juveniles in a "
                    "race bucket). Estimates are the current vintage "
                    "(published 2026) and are revised between vintages."
                ),
            },
            {
                "name": "hispanic_population",
                "type": "int64",
                "unit": "count",
                "example": 4056,
                "null_meaning": (
                    "The ethnicity split is published only for the juvenile "
                    "total (demographic = 'all', age_group = '00_17'); NULL "
                    "on every other row is structural, not suppression."
                ),
                "description": (
                    "Estimated Hispanic (any race) juveniles ages 0-17 — an "
                    "ethnicity partition of the row's population, populated "
                    "only where demographic = 'all' and age_group = '00_17'. "
                    "Served as a column rather than a demographic row because "
                    "bridged-race buckets include Hispanic persons: a "
                    "hispanic row would double-count against the race rows "
                    "when summing the race axis. hispanic_population + "
                    "not_hispanic_population = population on every populated "
                    "row."
                ),
            },
            {
                "name": "not_hispanic_population",
                "type": "int64",
                "unit": "count",
                "example": 12074,
                "null_meaning": (
                    "The ethnicity split is published only for the juvenile "
                    "total (demographic = 'all', age_group = '00_17'); NULL "
                    "on every other row is structural, not suppression."
                ),
                "description": (
                    "Estimated non-Hispanic (any race) juveniles ages 0-17 — "
                    "the complement of hispanic_population, populated only "
                    "where demographic = 'all' and age_group = '00_17'."
                ),
            },
        ],
        source="OJJDP Statistical Briefing Book — Easy Access to Juvenile Populations",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        suppressed_to_null=False,
        usage=(
            "Cite: Puzzanchera, C., Sladky, A. and Kang, W. (2026). Easy "
            "Access to Juvenile Populations: 1990-2024. This is a DENOMINATOR "
            "dataset: join on year + county_fips (+ demographic) to turn "
            "juvenile-justice counts into rates. Use age_group = '00_17' for "
            "juvenile rates; sum single ages 10-16 for Georgia "
            "delinquency-jurisdiction rates; use 'all_ages' for whole-"
            "population rates. Filter demographic to one axis at a time and "
            "never sum overlapping age_group values."
        ),
        limitations=(
            "State rows have NULL county_fips and equal the county sum "
            "exactly. Values are model-based Census/NCHS bridged-race "
            "estimates of the current vintage, not enumerated counts — "
            "historical values are revised between vintages. Race buckets "
            "are bridged race (include both ethnicities; no multiracial "
            "bucket; Asian includes Pacific Islanders), so they are not "
            "directly comparable to sources with Hispanic-exclusive race "
            "buckets or post-1997 OMB race schemes. Sex, race, and ethnicity "
            "splits exist only for the juvenile total (age_group '00_17'); "
            "single ages and all_ages exist only for demographic 'all' — the "
            "source publishes one-way marginals, never cross-tabulations. "
            "The ethnicity split is served as the hispanic_population / "
            "not_hispanic_population columns, NULL outside the juvenile-"
            "total rows (structural, not suppression)."
        ),
        quality_checks=[
            {
                "name": "population_never_null",
                "description": (
                    "The source has full coverage with no suppression; a NULL "
                    "population would mean a parse or join regression."
                ),
                "dimension": "completeness",
                "query": "SELECT COUNT(*) FROM {object} WHERE population IS NULL",
                "mustBe": 0,
            },
            {
                "name": "sex_partition_of_juvenile_total",
                "description": (
                    "male + female must equal the 'all' juvenile total per "
                    "(year, county_fips) at age_group '00_17' (verified exact "
                    "in bronze). GROUP BY treats the NULL county_fips of "
                    "state rows as one group, enforcing both levels."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, "
                    "MAX(CASE WHEN demographic = 'all' THEN population END) "
                    "AS total, "
                    "SUM(CASE WHEN demographic IN ('female','male') "
                    "THEN population END) AS sex_sum "
                    "FROM {object} WHERE age_group = '00_17' "
                    "GROUP BY year, county_fips"
                    ") WHERE total IS NOT NULL AND sex_sum IS NOT NULL "
                    "AND total != sex_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "race_partition_of_juvenile_total",
                "description": (
                    "The four bridged-race buckets must sum exactly to the "
                    "'all' juvenile total per (year, county_fips) — the "
                    "structural fact that also proves 'Asian' is the combined "
                    "Asian/Pacific Islander bucket and that multiracial "
                    "persons are allocated into the four buckets."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, "
                    "MAX(CASE WHEN demographic = 'all' THEN population END) "
                    "AS total, "
                    "SUM(CASE WHEN demographic IN ('asian_pacific_islander',"
                    "'black','native_american','white') THEN population END) "
                    "AS race_sum "
                    "FROM {object} WHERE age_group = '00_17' "
                    "GROUP BY year, county_fips"
                    ") WHERE total IS NOT NULL AND race_sum IS NOT NULL "
                    "AND total != race_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "ethnicity_partition_of_juvenile_total",
                "description": (
                    "hispanic_population + not_hispanic_population must equal "
                    "population on every row where the split is published "
                    "(verified exact in bronze)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE hispanic_population IS NOT NULL "
                    "AND not_hispanic_population IS NOT NULL "
                    "AND population IS NOT NULL "
                    "AND hispanic_population + not_hispanic_population "
                    "!= population"
                ),
                "mustBe": 0,
            },
            {
                "name": "single_ages_sum_to_juvenile_total",
                "description": (
                    "The 18 single-year-of-age rows must sum exactly to the "
                    "'00_17' juvenile total per (year, county_fips) at "
                    "demographic 'all' (verified exact in bronze) — the "
                    "guarantee that lets consumers build any age band."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, "
                    "MAX(CASE WHEN age_group = '00_17' THEN population END) "
                    "AS total, "
                    "SUM(CASE WHEN age_group IN ('00','01','02','03','04',"
                    "'05','06','07','08','09','10','11','12','13','14','15',"
                    "'16','17') THEN population END) AS age_sum "
                    "FROM {object} WHERE demographic = 'all' "
                    "GROUP BY year, county_fips"
                    ") WHERE total IS NOT NULL AND age_sum IS NOT NULL "
                    "AND total != age_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_row_equals_county_sum",
                "description": (
                    "The source's 'All Counties' statewide row equals the sum "
                    "of the 159 county rows exactly in every file (verified "
                    "in bronze); preserved per (year, demographic, age_group)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, demographic, age_group, "
                    "SUM(CASE WHEN county_fips IS NULL THEN population END) "
                    "AS state_total, "
                    "SUM(CASE WHEN county_fips IS NOT NULL THEN population "
                    "END) AS county_sum "
                    "FROM {object} GROUP BY year, demographic, age_group"
                    ") WHERE state_total IS NOT NULL AND county_sum IS NOT "
                    "NULL AND state_total != county_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "juveniles_within_total_population",
                "description": (
                    "The juvenile (0-17) population cannot exceed the total "
                    "resident population of the same county and year."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, "
                    "MAX(CASE WHEN age_group = 'all_ages' THEN population "
                    "END) AS everyone, "
                    "MAX(CASE WHEN age_group = '00_17' THEN population END) "
                    "AS juveniles "
                    "FROM {object} WHERE demographic = 'all' "
                    "GROUP BY year, county_fips"
                    ") WHERE everyone IS NOT NULL AND juveniles IS NOT NULL "
                    "AND juveniles > everyone"
                ),
                "mustBe": 0,
            },
            {
                "name": "ethnicity_columns_structural_nulls",
                "description": (
                    "The ethnicity partition columns are populated on exactly "
                    "the juvenile-total rows (demographic 'all', age_group "
                    "'00_17') and NULL everywhere else — the source publishes "
                    "the split only for that slice."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(demographic = 'all' AND age_group = '00_17' AND "
                    "(hispanic_population IS NULL OR not_hispanic_population "
                    "IS NULL)) OR ((demographic != 'all' OR age_group != "
                    "'00_17') AND (hispanic_population IS NOT NULL OR "
                    "not_hispanic_population IS NOT NULL))"
                ),
                "mustBe": 0,
            },
            {
                "name": "demographic_splits_only_for_juvenile_total",
                "description": (
                    "Sex and race marginals are published for the juvenile "
                    "total only — a non-'all' demographic on any other "
                    "age_group would mean a slice-routing bug (the source "
                    "has no such cross-tabs)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE demographic != 'all' AND age_group != '00_17'"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
