"""Transform bronze NHTSA FARS annual zips into a county-year gold fact table.

Source: NHTSA Fatality Analysis Reporting System (FARS) — the federal census
of every fatal motor-vehicle traffic crash in the US (a crash with >= 1 death
within 30 days), one national zip per year, 1975-2024. Only the accident
table (one row per fatal crash) is read; zips are never extracted to disk
(provenance contract) — members are read directly via ``zipfile``.

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Grain: county_fips x year, densified to all 159 counties.** FARS is a
  census, so a county-year absent from bronze is a TRUE ZERO, not missing
  data (structure doc ETL #9). The transform builds the full 159-county x
  50-year grid with 0 crash/fatality counts, plus one statewide row per year.
- **v1 metric scope: crash counts, fatality counts, drinking-driver crash
  counts.** PEDS (1991+ only), VE_FORMS/VE_TOTAL (definition changes in
  2005), PERSONS (definition changes in 2011), and person-level demographics
  are deliberately omitted — fewer, well-verified metrics across all 50
  years over era-gapped ones (structure doc ETL #4/#5/#13). A demographic
  breakdown would be a separate person-file topic.
- **County code -> FIPS (verified, not assumed).** FARS ``COUNTY`` is the
  GSA/GLC geographic locator code, NOT nominally FIPS. Verified empirically
  for this run against the 2016/2018/2024 ``COUNTYNAME`` label twins: every
  GA code maps to the counties dimension with 0 name mismatches — for
  Georgia, GLC code == the 3-digit county FIPS suffix. ``county_fips`` is
  built as ``"13" + zfill(3)`` and validated by membership against the
  global counties dimension.
- **Unknown/invalid county codes -> state-only (structure doc ETL #2).**
  126 crash rows across the 50 years carry sentinel or invalid codes
  (999/0 = unknown; 510/520/507 in 1976-1981; scattered even/out-of-range
  codes 1986-1994, single rows 2001-2006). The crash is NEVER dropped — its
  ``county_fips`` becomes NULL, it is excluded from county rows, and it
  still counts in the statewide row. Statewide totals can therefore exceed
  the county-row sum (by <= 27 crashes in the worst year, 1980); an authored
  quality check enforces state >= county-sum, and the contract documents
  the gap.
- **Alcohol metric: police-reported ``DRUNK_DR``, 1975-2020 only.**
  ``crashes_with_drunk_driver`` counts crashes with >= 1 drinking driver as
  reported by police (``DRUNK_DR`` >= 1; observed values 0-4, no unknown
  sentinels in any GA year — verified this run). NHTSA dropped the column
  permanently from 2021 on, so the metric is NULL (not 0) for 2021+ — an
  authored quality check enforces the era boundary. This is NOT NHTSA's
  published "alcohol-impaired-driving" series (which uses multiply-imputed
  driver BAC >= .08 from the MI files, absent 1975-1981); the simple
  police-reported flag is the only convention available across the full
  1975-2020 span and the contract says so.
- **Year from the filename, verified against the data.** ``YEAR`` is
  2-digit for 1975-1997; the transform normalizes (1900 + YY) and hard-fails
  if the accident table's year does not equal the filename year (verified
  identical for all 50 files).
- **No §4b masks apply.** All metrics are aggregated counts derived from
  row counts and ``FATALS``/``DRUNK_DR``; verified across all 50 GA years:
  FATALS is 1-7 (a fatal crash has >= 1 death by definition; no zeros or
  negatives anywhere) and DRUNK_DR is 0-4 with no sentinel codes. There is
  no impossible value to NULL. Unknown county codes are geography nulling
  (above), not metric masking.
- **No suppression.** FARS is unsuppressed public-domain microdata;
  ``suppressed_to_null=False``. Zeros are real (census).
- **Read-loss accounting.** Members are read from the zips (not via
  ``read_bronze_file``, which takes filesystem paths), so raw-vs-parsed is
  computed directly: physical data lines in the decompressed member vs
  parsed rows. Verified 0 loss for all 50 files this run.
- **Dedup tie-break.** One zip per year and one accident table per zip, and
  county rows are produced by a single group_by — duplicate natural keys
  are impossible by construction. ``deduplicate_by_levels(sort_col=
  "traffic_fatalities")`` remains as the documented safety net (prefer the
  fuller row) should a future refresh add an overlapping file; the collision
  guard runs first and would hard-fail on any divergent duplicate.
- **Fatal-only scope.** No injury-only or property-damage crashes — never
  present these counts as total crash volume (structure doc ETL #10).
  Counts are by state/county of crash occurrence, matching NHTSA's
  published state fatality series.
"""

import io
import logging
import re
import zipfile
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

TOPIC = "fatal_crashes"
BRONZE_DIR = Path("data/bronze/criminal_justice/traffic_safety/fatal_crashes")
GOLD_DIR = Path("data/gold/criminal_justice/fatal_crashes")
COUNTIES_DIM_PATH = Path("data/gold/_dimensions/counties.parquet")
SOURCE_URL = (
    "https://www.nhtsa.gov/research-data/fatality-analysis-reporting-system-fars"
)

FILENAME_RE = re.compile(r"FARS(\d{4})NationalCSV\.zip$")

# Georgia state FIPS code (FARS STATE column).
GEORGIA_STATE_FIPS = 13

# Last data year in which FARS published DRUNK_DR (dropped permanently from
# 2021 on — structure doc ETL #3). Drives NULL-vs-0 for the alcohol metric
# and the contract's era-coverage quality check.
DRUNK_DR_LAST_YEAR = 2020

# Era detection by column signature (most-specific first): the only era
# difference that matters for this county-year count table is DRUNK_DR
# presence. 2021+ files dropped DRUNK_DR but carry VE_TOTAL (2005+ column),
# so the second signature catches them without a hardcoded year range.
ERA_SIGNATURES: dict[str, list[str]] = {
    "fars_with_drunk_dr": ["STATE", "COUNTY", "YEAR", "FATALS", "DRUNK_DR"],
    "fars_post_drunk_dr": ["STATE", "COUNTY", "YEAR", "FATALS", "VE_TOTAL"],
}

METRIC_COLUMNS: list[str] = [
    "fatal_crashes",
    "traffic_fatalities",
    "crashes_with_drunk_driver",
]

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "county_fips",
    *METRIC_COLUMNS,
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "county_fips": pl.Utf8,
    **{c: pl.Int64 for c in METRIC_COLUMNS},
    "detail_level": pl.Utf8,
}

NATURAL_KEYS: list[str] = ["year", "county_fips", "detail_level"]


# =============================================================================
# Bronze reading (zip members, never extracted)
# =============================================================================


def _read_accident_member(path: Path) -> tuple[pl.DataFrame, int]:
    """Read the accident table from a FARS annual zip, without extracting.

    Member names/case and nesting vary by era (root-level ACCIDENT.CSV
    1975-2009, FARS{year}NationalCSV/accident.csv 2015+, mixed in between),
    so the member is matched case-insensitively by basename. All columns are
    read as Utf8 (infer_schema_length=0) and cast explicitly — schema
    inference mis-types columns like MILEPT (floats among ints) and would
    strip any leading zeros. 2021-2022 headers carry a UTF-8 BOM, stripped
    from the first column name.

    Returns:
        (national accident DataFrame, physical data-line count of the member)
    """
    with zipfile.ZipFile(path) as zf:
        members = [
            n for n in zf.namelist() if n.lower().rsplit("/", 1)[-1] == "accident.csv"
        ]
        if len(members) != 1:
            raise ValueError(
                f"{path.name}: expected exactly 1 accident.csv member, got {members}"
            )
        raw = zf.read(members[0])

    df = pl.read_csv(io.BytesIO(raw), infer_schema_length=0, encoding="utf8-lossy")
    # 2021-2022 files carry a UTF-8 BOM on the header row; strip it so the
    # first column is "STATE", not "﻿STATE".
    df.columns = [c.lstrip("﻿") for c in df.columns]

    # Physical data lines (newlines minus header) for read-loss accounting.
    # Verified equal to parsed rows for all 50 files (no quoted-newline
    # fields in any accident table).
    raw_lines = raw.count(b"\n") - 1
    return df, raw_lines


def transform_file(path: Path, year: int, manifest: TransformManifest) -> pl.DataFrame:
    """Read one FARS annual zip into Georgia crash-level rows.

    Emits one row per GA fatal crash with: year (Int32, from the verified
    filename), the raw COUNTY code string, FATALS, and DRUNK_DR (NULL column
    in the post-2020 era). FIPS resolution and aggregation happen in main()
    across all years at once.
    """
    df, raw_lines = _read_accident_member(path)

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{path.name}: no era signature matched {df.columns}")

    manifest.record_read_loss(year, path.name, raw_lines, df.height)
    manifest.record_file(path, year, era, df.height, df.columns)

    # Scope filter: Georgia rows only (STATE = 13). FARS files are national;
    # non-GA rows are out of topic scope, recorded explicitly for provenance.
    ga = df.filter(pl.col("STATE").cast(pl.Int64) == GEORGIA_STATE_FIPS)

    # Verify the GA slice's YEAR equals the filename year (2-digit for
    # 1975-1997: normalize 1900 + YY). A mismatch means the zip content and
    # name disagree — hard-stop, never trust one silently over the other.
    # Checked on the GA slice because a handful of OUT-OF-SCOPE rows in early
    # files carry the in-band unknown-date sentinel YEAR = 99 (e.g. 3
    # non-Georgia rows in 1975); every Georgia row in all 50 files has a
    # real year (verified this run).
    years_in_data = sorted(
        y + 1900 if y < 100 else y for y in ga["YEAR"].cast(pl.Int64).unique().to_list()
    )
    if years_in_data != [year]:
        raise ValueError(
            f"{path.name}: GA YEAR column {years_in_data} != filename year {year}"
        )
    manifest.record_bronze(year, ga.height)
    manifest.record_filtered(
        year, df.height - ga.height, "out_of_scope_non_georgia_states"
    )
    logger.info(
        "%s: %d national rows -> %d Georgia fatal crashes (era %s)",
        path.name,
        df.height,
        ga.height,
        era,
    )

    # DRUNK_DR is genuinely absent in the post-2020 era (dropped by NHTSA,
    # structure doc ETL #3) — emit a typed NULL column, logged per §4.2 so a
    # rename bug could never masquerade as an absent column.
    if era == "fars_with_drunk_dr":
        drunk_expr = pl.col("DRUNK_DR").cast(pl.Int64).alias("drunk_dr")
    else:
        logger.info(
            "%s: DRUNK_DR absent by era (%s) — crashes_with_drunk_driver "
            "will be NULL for %d",
            path.name,
            era,
            year,
        )
        drunk_expr = pl.lit(None).cast(pl.Int64).alias("drunk_dr")

    return ga.select(
        pl.lit(year, dtype=pl.Int32).alias("year"),
        pl.col("COUNTY").cast(pl.Utf8).str.strip_chars().alias("county_raw"),
        pl.col("FATALS").cast(pl.Int64).alias("fatals"),
        drunk_expr,
    )


# =============================================================================
# County FIPS resolution
# =============================================================================


def _resolve_county_fips(
    crashes: pl.DataFrame, dim_fips: list[str], manifest: TransformManifest
) -> pl.DataFrame:
    """Map the FARS GSA county code to county_fips; invalid codes -> NULL.

    For Georgia the GSA/GLC code equals the 3-digit county FIPS suffix —
    verified against the 2016/2018/2024 COUNTYNAME label twins with 0
    mismatches (structure doc ETL #2). Candidate FIPS is "13" + zfill(3),
    validated by membership against the global counties dimension. Sentinel
    and invalid codes (999/0 unknown; 510/520/507 in 1976-1981; scattered
    even/out-of-range codes 1986-1994) become NULL: the crash is never
    dropped — it counts at state level only.
    """
    crashes = crashes.with_columns(
        (
            pl.lit("13")
            + pl.col("county_raw").cast(pl.Int64).cast(pl.Utf8).str.zfill(3)
        ).alias("_candidate_fips")
    ).with_columns(
        pl.when(pl.col("_candidate_fips").is_in(dim_fips))
        .then(pl.col("_candidate_fips"))
        .otherwise(None)
        .alias("county_fips")
    )

    invalid = crashes.filter(pl.col("county_fips").is_null())
    if invalid.height:
        by_year = invalid.group_by("year").len().sort("year").to_dicts()
        logger.warning(
            "%d crash row(s) carry unknown/invalid county codes -> NULL "
            "county_fips (state-level only). Codes: %s; by year: %s",
            invalid.height,
            sorted(invalid["county_raw"].unique().to_list(), key=int),
            {r["year"]: r["len"] for r in by_year},
        )

    # Record the observed code -> FIPS map (invalid codes map to None) so the
    # review has 100%% coverage of the geography recode. Building the map from
    # observed codes keeps unmapped_count at 0 by construction; the real
    # guard is the dimension-membership test above.
    code_map = {
        row["county_raw"]: row["county_fips"]
        for row in crashes.select("county_raw", "county_fips").unique().to_dicts()
    }
    manifest.record_categorical(
        column="county_fips",
        map_dict=code_map,
        bronze_series=crashes["county_raw"],
        gold_series=crashes["county_fips"],
    )
    return crashes.drop("_candidate_fips")


# =============================================================================
# Aggregation to county-year / state-year
# =============================================================================

# Aggregations shared by the county and state group-bys. The drinking-driver
# count is NULL (not 0) when the group has no DRUNK_DR data (2021+ era).
_AGG_EXPRS: list[pl.Expr] = [
    pl.len().cast(pl.Int64).alias("fatal_crashes"),
    pl.col("fatals").sum().cast(pl.Int64).alias("traffic_fatalities"),
    pl.when(pl.col("drunk_dr").count() > 0)
    .then((pl.col("drunk_dr") >= 1).sum())
    .otherwise(None)
    .cast(pl.Int64)
    .alias("crashes_with_drunk_driver"),
]


def _build_county_rows(
    crashes: pl.DataFrame, dim_fips: list[str], years: list[int]
) -> pl.DataFrame:
    """Aggregate to county x year and densify to the full 159-county grid.

    FARS is a census (every qualifying fatal crash is in the file), so a
    county-year with no crash rows is a real zero — the grid guarantees all
    159 counties appear in every year. crashes_with_drunk_driver is
    zero-filled only in years where DRUNK_DR exists (<= 2020); it stays NULL
    for 2021+ because the variable is unpublished, not zero. Crashes with
    NULL county_fips (unknown county) are excluded here — they count at
    state level only.
    """
    county = (
        crashes.filter(pl.col("county_fips").is_not_null())
        .group_by("year", "county_fips")
        .agg(_AGG_EXPRS)
    )

    grid = pl.DataFrame(
        {"year": [y for y in years for _ in dim_fips]},
        schema={"year": pl.Int32},
    ).with_columns(pl.Series("county_fips", dim_fips * len(years), dtype=pl.Utf8))

    dense = grid.join(county, on=["year", "county_fips"], how="left").with_columns(
        pl.col("fatal_crashes").fill_null(0),
        pl.col("traffic_fatalities").fill_null(0),
        # Zero only within the DRUNK_DR era; 2021+ stays NULL (unpublished).
        pl.when(pl.col("year") <= DRUNK_DR_LAST_YEAR)
        .then(pl.col("crashes_with_drunk_driver").fill_null(0))
        .otherwise(pl.col("crashes_with_drunk_driver"))
        .alias("crashes_with_drunk_driver"),
        pl.lit("county").alias("detail_level"),
    )
    zero_rows = dense.filter(pl.col("fatal_crashes") == 0).height
    logger.info(
        "Densified county grid: %d rows (%d counties x %d years; %d true-zero "
        "county-years)",
        dense.height,
        len(dim_fips),
        len(years),
        zero_rows,
    )
    return dense


def _build_state_rows(crashes: pl.DataFrame) -> pl.DataFrame:
    """Build one statewide row per year over ALL Georgia crashes.

    Includes unknown-county crashes (NULL county_fips), so the state totals
    are the authoritative statewide counts and can exceed the county-row sum
    in years with unknown-county rows (126 crashes across 50 years).
    """
    return (
        crashes.group_by("year")
        .agg(_AGG_EXPRS)
        .with_columns(
            pl.lit(None).cast(pl.Utf8).alias("county_fips"),
            pl.lit("state").alias("detail_level"),
        )
    )


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for fatal_crashes."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read each annual zip (year from the verified filename), one at a
    # time — only the GA slice of the accident table is kept in memory.
    frames: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR, extensions=[".zip"]):
        match = FILENAME_RE.search(path.name)
        if not match:
            raise ValueError(f"Unexpected bronze filename: {path.name}")
        frames.append(transform_file(path, int(match.group(1)), manifest))
    if not frames:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    crashes = pl.concat(frames)
    years = sorted(crashes["year"].unique().to_list())
    logger.info(
        "Read %d Georgia fatal-crash rows across %d years (%d-%d)",
        crashes.height,
        len(years),
        years[0],
        years[-1],
    )

    # 2. Resolve county FIPS (invalid codes -> NULL, state-only), then
    # aggregate: densified county grid + statewide rows. The counties
    # dimension is read once and shared by validation + densification.
    dim_fips = sorted(pl.read_parquet(COUNTIES_DIM_PATH)["county_fips"].to_list())
    crashes = _resolve_county_fips(crashes, dim_fips, manifest)
    county = _build_county_rows(crashes, dim_fips, years)
    states = _build_state_rows(crashes)
    combined = pl.concat(
        harmonize_columns([county, states], STANDARD_COLUMNS, TARGET_TYPES)
    )
    logger.info("Combined %d gold-shaped rows", combined.height)

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean an aggregation bug and must raise, not be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: one zip per year and a single group_by per level make
    # duplicate keys impossible by construction; sort_col
    # "traffic_fatalities" is the documented safety net (prefer the fuller
    # row) should a future refresh add an overlapping file.
    combined = deduplicate_by_levels(
        combined,
        {
            "county": ["year", "county_fips"],
            "state": ["year"],
        },
        sort_col="traffic_fatalities",
    )

    # 4. Geography nulling (shared domain rules; state rows already NULL).
    # No §4b masks apply — see module docstring (FATALS 1-7 and DRUNK_DR 0-4
    # verified across all 50 GA years; nothing impossible to NULL).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=CRIMINAL_JUSTICE_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. The crashes_with_drunk_driver NULL-rate spike from
    # 2021 on is EXPECTED and documented: NHTSA dropped DRUNK_DR after 2020.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning(
            "NULL-rate spikes (documented cause: DRUNK_DR unpublished from "
            "2021 on): %s",
            spike_result.details,
        )
    validate_output(combined, required_non_null=["year", "detail_level"])

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
    _emit_contract(year_range=(years[0], years[-1]))

    summary = manifest.tracker.summary()
    logger.info(
        "Done. Bronze GA crash rows: %s; gold rows: %s; years: %s",
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
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Fatal motor-vehicle traffic crashes and traffic fatalities per "
            "Georgia county per year, 1975-2024, from NHTSA's Fatality "
            "Analysis Reporting System (FARS) — the federal census of every "
            "crash on a public road with at least one death within 30 days. "
            "One row per county per year (all 159 counties every year; "
            "county-years with no fatal crash are real zeros, not missing "
            "data) plus one statewide row per year. Metrics: fatal crash "
            "count, total deaths, and (1975-2020) crashes involving at "
            "least one drinking driver as reported by police. Fatal crashes "
            "only — this is not total crash volume."
        ),
        title="Fatal Traffic Crashes by County",
        summary=(
            "Annual fatal motor-vehicle crash and traffic fatality counts "
            "for each Georgia county from the federal FARS census, 1975 "
            "onward."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Calendar year of the crash (FARS data year; verified "
                    "equal to the source file year for all 50 files)."
                ),
            },
            {
                "name": "county_fips",
                "type": "string",
                "example": "13121",
                "null_meaning": "NULL on statewide rollup rows.",
                "description": (
                    "5-digit county FIPS code (state prefix 13) of the "
                    "county where the crash occurred; FK to the counties "
                    "dimension. NULL on statewide rollup rows. Derived from "
                    "the FARS GSA/GLC county code, which for Georgia equals "
                    "the 3-digit county FIPS suffix (verified against the "
                    "FARS county-name labels with zero mismatches). 126 "
                    "crashes across 1975-2006 carry unknown/invalid county "
                    "codes at source (e.g. code 999 = unknown) — those "
                    "crashes count in the statewide row only, so county "
                    "rows can sum to slightly less than the statewide row "
                    "in those years (worst gap: 27 crashes in 1980)."
                ),
            },
            {
                "name": "fatal_crashes",
                "type": "int64",
                "nullable": False,
                "unit": "count",
                "example": 87,
                "description": (
                    "Number of fatal motor-vehicle traffic crashes (crashes "
                    "with at least one death within 30 days) in the county "
                    "that year. FARS is a census, so 0 is a real zero — the "
                    "county had no fatal crash that year. Fatal crashes "
                    "only; never interpret as total crash volume."
                ),
            },
            {
                "name": "traffic_fatalities",
                "type": "int64",
                "nullable": False,
                "unit": "count",
                "key_metric": True,
                "example": 95,
                "description": (
                    "Number of people killed in those crashes (deaths "
                    "within 30 days of the crash, per the FARS FATALS "
                    "count). Always >= fatal_crashes on rows with any "
                    "crashes, since every fatal crash has at least one "
                    "death (per-crash deaths observed: 1-7). Counted by "
                    "county/state of crash occurrence, matching NHTSA's "
                    "published state fatality series."
                ),
            },
            {
                "name": "crashes_with_drunk_driver",
                "type": "int64",
                "unit": "count",
                "example": 20,
                "null_meaning": (
                    "NULL for 2021 onward: NHTSA dropped the DRUNK_DR "
                    "variable after data year 2020, so the metric is "
                    "unpublished (not zero) in those years."
                ),
                "description": (
                    "Number of fatal crashes involving at least one "
                    "drinking driver, per the police-reported FARS DRUNK_DR "
                    "count (values 0-4 observed; no unknown sentinels in "
                    "any Georgia year). Available 1975-2020 only — NHTSA "
                    "dropped DRUNK_DR from 2021 on, so the column is NULL "
                    "(not 0) for 2021+. This is the simple police-reported "
                    "drinking-driver flag, NOT NHTSA's published "
                    "'alcohol-impaired-driving' fatality series (which uses "
                    "multiply-imputed driver BAC >= .08 and is not "
                    "comparable); police-reported drinking is typically an "
                    "undercount of alcohol involvement."
                ),
            },
        ],
        source="NHTSA Fatality Analysis Reporting System (FARS)",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        suppressed_to_null=False,
        usage=(
            "Cite NHTSA FARS (US DOT; public domain). traffic_fatalities is "
            "the headline metric. Zeros are real: a county-year with 0 "
            "means no fatal crash occurred there. Use statewide rows for "
            "state totals — they include the few crashes with unknown "
            "county (county rows can sum slightly lower in 1975-2006). Do "
            "not present fatal_crashes as total crash volume (FARS excludes "
            "non-fatal crashes), and do not compare "
            "crashes_with_drunk_driver to NHTSA's imputed-BAC "
            "alcohol-impaired series."
        ),
        limitations=(
            "State rows have NULL county_fips. Fatal crashes only — no "
            "injury-only or property-damage crashes, so this is not total "
            "crash volume. crashes_with_drunk_driver covers 1975-2020 only "
            "(NHTSA dropped the police-reported DRUNK_DR variable after "
            "2020; NULL thereafter) and undercounts alcohol involvement "
            "relative to NHTSA's imputed-BAC series. 126 crashes across "
            "1975-2006 have unknown/invalid county codes and count at "
            "state level only, so county rows sum to slightly less than "
            "the statewide row in those years. Counts are by state/county "
            "of crash occurrence, not victim residence."
        ),
        quality_checks=[
            {
                "name": "fatalities_gte_crashes",
                "description": (
                    "Every fatal crash kills at least one person, so "
                    "traffic_fatalities must be >= fatal_crashes on every "
                    "row (equality only when both are 0 or every crash had "
                    "exactly one death)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE fatal_crashes IS "
                    "NOT NULL AND traffic_fatalities IS NOT NULL AND "
                    "traffic_fatalities < fatal_crashes"
                ),
                "mustBe": 0,
            },
            {
                "name": "zero_crashes_implies_zero_fatalities",
                "description": (
                    "A county-year with no fatal crashes can have no "
                    "traffic deaths — fatalities must be 0 wherever "
                    "fatal_crashes is 0 (the densified true-zero rows)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE fatal_crashes = 0 "
                    "AND traffic_fatalities != 0"
                ),
                "mustBe": 0,
            },
            {
                "name": "drunk_driver_crashes_subset_of_crashes",
                "description": (
                    "Crashes with a drinking driver are a subset of all "
                    "fatal crashes — the count can never exceed "
                    "fatal_crashes."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "crashes_with_drunk_driver IS NOT NULL AND "
                    "crashes_with_drunk_driver > fatal_crashes"
                ),
                "mustBe": 0,
            },
            {
                "name": "drunk_driver_metric_era_coverage",
                "description": (
                    "The police-reported DRUNK_DR variable exists for data "
                    "years 1975-2020 and was dropped permanently from 2021 "
                    "— crashes_with_drunk_driver must be populated (0 is "
                    "real) through 2020 and NULL from 2021 on, on every "
                    "row."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE (year <= 2020 AND "
                    "crashes_with_drunk_driver IS NULL) OR (year >= 2021 "
                    "AND crashes_with_drunk_driver IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "all_159_counties_every_year",
                "description": (
                    "FARS is a census and the county grid is densified — "
                    "every year must carry exactly 159 county rows "
                    "(true zeros included)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, COUNT(CASE WHEN county_fips IS NOT NULL "
                    "THEN 1 END) AS n_counties "
                    "FROM {object} GROUP BY year"
                    ") WHERE n_counties != 159"
                ),
                "mustBe": 0,
            },
            {
                "name": "one_state_row_every_year",
                "description": (
                    "Exactly one statewide rollup row per year (Georgia has "
                    "fatal crashes in every FARS year)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, COUNT(CASE WHEN county_fips IS NULL THEN "
                    "1 END) AS n_state "
                    "FROM {object} GROUP BY year"
                    ") WHERE n_state != 1"
                ),
                "mustBe": 0,
            },
            *[
                {
                    "name": f"state_{col}_gte_county_sum",
                    "description": (
                        "Statewide rows include the few crashes with "
                        "unknown county codes (excluded from county rows), "
                        f"so the state {col} must be >= the sum of the "
                        "county rows for every year — never less."
                    ),
                    "dimension": "consistency",
                    "query": (
                        "SELECT COUNT(*) FROM ("
                        "SELECT year, "
                        f"MAX(CASE WHEN county_fips IS NULL THEN {col} END) "
                        "AS state_total, "
                        f"SUM(CASE WHEN county_fips IS NOT NULL THEN {col} "
                        "END) AS county_sum "
                        "FROM {object} GROUP BY year"
                        ") WHERE state_total IS NOT NULL AND county_sum IS "
                        "NOT NULL AND state_total < county_sum"
                    ),
                    "mustBe": 0,
                }
                for col in METRIC_COLUMNS
            ],
        ],
    )


if __name__ == "__main__":
    main()
