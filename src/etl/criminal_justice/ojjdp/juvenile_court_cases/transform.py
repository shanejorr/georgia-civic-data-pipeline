"""Transform bronze EZACO JSON exports into a gold county/year case-count fact table.

Source: OJJDP Statistical Briefing Book — *Easy Access to State and County
Juvenile Court Case Counts* (EZACO; NCJJ, National Juvenile Court Data
Archive; Georgia data from the Council of Juvenile Court Judges of Georgia).
26 JSON files, one verbatim API response per calendar year 1997-2023
(**2014 genuinely absent** — the API returns no Georgia rows; GA did not
publish that year — a source gap, never interpolated). Each file: 1 state
summary row + 159 county rows, with petitioned / non-petitioned counts of
juvenile court **cases disposed** for delinquency, status offense, and
dependency, per-1,000 rates (state row only), and per-measure reporting
flags.

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Grain: year x county_fips x case_type x petition_status** (tidy unpivot
  of the 6 wide measure columns), with a single ``case_count`` metric. The
  wide alternative (petitioned/non_petitioned as columns at case_type grain)
  was rejected because reporting coverage differs *within* a case type:
  non-petitioned measures have 0 reporting counties in 1997-2000 and
  2010-2013 while petitioned coverage peaks (152 counties) — one
  ``reporting_status`` per row needs the petition axis in the grain. The
  source publishes no total (petitioned + non_petitioned is only summable
  when neither cell is suppressed), so no total partition is emitted.
- **Coverage flag, never imputation (domain rule; jail_population
  precedent).** County reporting collapses from 152 counties (1997) to 25
  (2009) to 41 (2023). Every county appears every year; the per-measure
  ``reportingflag_*`` (0/1 on county rows) drives a ``reporting_status``
  categorical: ``reported`` (numeric value), ``suppressed`` (flag 1 with a
  suppression marker), ``not_reported`` (flag 0, value ``--``). Verified
  across all 26 files: flag 0 pairs only with ``--`` and flag 1 only with a
  numeric value or a suppression marker — any other combination hard-stops.
  Genuine zeros occur (512 county cells) and are distinguishable from
  non-reporting, so NULL is never zero-filled.
- **State rows are NCJJ's aggregate over REPORTING counties only — not
  statewide totals.** Verified: state count >= visible county sum in every
  measure-year, exactly equal whenever no county cell is suppressed. State
  rows carry ``counties_reporting`` (the state-row reportingflag, verified
  equal to the sum of the county 0/1 flags in all 156 measure-years) so
  consumers can separate caseload change from coverage change; the contract
  says plainly that state != full-GA.
- **Suppression -> NULL, never 0 (kept verbatim in bronze).** ``*`` =
  primary suppression of a cell value 1-4; ``x`` = secondary suppression of
  5-20; ``z`` = secondary suppression of >20; ``--`` = not available (every
  non-reporting county, and state cells when 0 counties report). All four
  become NULL, each recorded on the manifest per marker type via
  ``record_masked`` (firearm_homicide_deaths precedent). No §4b
  impossible-value masks beyond suppression: after marker handling every
  remaining value casts cleanly to a non-negative integer (guarded — an
  unknown non-numeric string hard-stops rather than silently NULLing).
- **Rates: source values served, state rows only.** All 6 ``*rate`` columns
  are ``--`` on every county row in all 26 files (verified), so
  ``case_rate_per_1000`` is populated on state rows only. It is the
  source's own computation — cases per 1,000 juveniles of the population
  *represented by reporting counties* (age 10 through GA's upper age 16 for
  delinquency/status offense; age 0-16 for dependency), verified to match
  count / popten<measure> x 1000 exactly — NOT a statewide rate. Served
  as-published (per-1,000, no ``unit`` marker, authored non-negativity
  check; firearm per-100k precedent). County rates are not recomputed: the
  sibling juvenile_population topic provides platform denominators.
- **Population columns are dropped.** ``poptot``/``popten``/``popzero`` are
  census denominators duplicated by the sibling juvenile_population topic
  (which serves single years of age, so any band can be rebuilt);
  ``popten<measure>``/``popzero<measure>`` are the state-row
  coverage-dependent rate denominators, documented in prose. Constants
  (``state``/``st``/``fst``/``age``/``unit``/``unit_2``/``print_state``/
  ``footnotes``) are metadata, not data.
- **Dedup tie-break.** One bronze file per year and one row per (county,
  measure) per file, so duplicate natural keys are impossible by
  construction; ``deduplicate_by_levels(sort_col="case_count")`` remains as
  the documented safety net (prefer the fuller row) should a future refresh
  add an overlapping file. The collision guard runs first and would surface
  any divergent duplicate as a hard error rather than letting dedup pick a
  winner.
- **2014 gap**: the gold year sequence 1997-2023 has a hole at 2014 —
  source truth (GA did not publish), documented in the contract, never
  interpolated.
"""

import json
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

TOPIC = "juvenile_court_cases"
BRONZE_DIR = Path("data/bronze/criminal_justice/ojjdp/juvenile_court_cases")
GOLD_DIR = Path("data/gold/criminal_justice/juvenile_court_cases")
SOURCE_URL = (
    "https://ojjdp.ojp.gov/statistical-briefing-book/data-analysis-tools/"
    "ezaco/access-case-counts"
)

# The 6 wide measure columns -> (case_type, petition_status). Each measure
# also has a sibling reportingflag_<measure> and <measure>rate column.
MEASURES: dict[str, tuple[str, str]] = {
    "petdel": ("delinquency", "petitioned"),
    "nonpetdel": ("delinquency", "non_petitioned"),
    "petsta": ("status_offense", "petitioned"),
    "nonpetsta": ("status_offense", "non_petitioned"),
    "petdep": ("dependency", "petitioned"),
    "nonpetdep": ("dependency", "non_petitioned"),
}

CASE_TYPE_MAP: dict[str, str] = {m: ct for m, (ct, _) in MEASURES.items()}
PETITION_STATUS_MAP: dict[str, str] = {m: ps for m, (_, ps) in MEASURES.items()}

CASE_TYPE_VALUES = sorted(set(CASE_TYPE_MAP.values()))
PETITION_STATUS_VALUES = sorted(set(PETITION_STATUS_MAP.values()))

# Suppression / availability markers, kept verbatim in bronze (legend from
# the tool itself, recorded in _provenance.md). Everything else must be a
# comma-separated integer (counts) or decimal (rates) — guarded, not assumed.
SUPPRESSION_MARKERS: dict[str, str] = {
    "*": "source_primary_suppression_cell_value_1_to_4",
    "x": "source_secondary_suppression_cell_value_5_to_20",
    "z": "source_secondary_suppression_cell_value_over_20",
}
UNAVAILABLE = "--"

# County-row shape marker -> reporting_status. Verified exhaustive across all
# 26 files: flag 0 pairs only with '--'; flag 1 only with numeric / * / x / z.
MARKER_TO_STATUS: dict[str, str] = {
    "flag_0_unavailable": "not_reported",
    "flag_1_numeric": "reported",
    "flag_1_suppressed_star": "suppressed",
    "flag_1_suppressed_x": "suppressed",
    "flag_1_suppressed_z": "suppressed",
}
REPORTING_STATUS_VALUES = sorted(set(MARKER_TO_STATUS.values()))

# All 38 keys of every bronze row (the state row omits `court` -> NULL).
# Missing keys beyond that, or new keys, mean the API changed — hard stop.
EXPECTED_COLUMNS: list[str] = [
    "yr",
    "state",
    "age",
    "unit",
    "unit_2",
    "print_state",
    "fst",
    "fct",
    "st",
    "court",
    "poptot",
    "popten",
    "popzero",
    "poptenpetdel",
    "poptennonpetdel",
    "poptenpetsta",
    "poptennonpetsta",
    "popzeropetdep",
    "popzerononpetdep",
    *MEASURES,
    *[f"reportingflag_{m}" for m in MEASURES],
    "footnotes",
    *[f"{m}rate" for m in MEASURES],
]

# Era detection by column signature. A single era spans all 26 files
# (identical 38-key schema, verified); the signature guards against a silent
# future API format change rather than distinguishing eras.
ERA_SIGNATURES: dict[str, list[str]] = {
    "ezaco_v1": ["yr", "fct", "petdel", "reportingflag_petdel", "petdelrate"],
}

EXPECTED_ROWS_PER_FILE = 160  # 1 state summary (fct="0") + 159 county rows

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "county_fips",
    "case_type",
    "petition_status",
    "reporting_status",
    "case_count",
    "case_rate_per_1000",
    "counties_reporting",
    "detail_level",
]

METRIC_COLUMNS: list[str] = ["case_count", "case_rate_per_1000", "counties_reporting"]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "county_fips": pl.Utf8,
    "case_type": pl.Utf8,
    "petition_status": pl.Utf8,
    "reporting_status": pl.Utf8,
    "case_count": pl.Int64,
    "case_rate_per_1000": pl.Float64,
    "counties_reporting": pl.Int64,
    "detail_level": pl.Utf8,
}

NATURAL_KEYS: list[str] = [
    "year",
    "county_fips",
    "case_type",
    "petition_status",
    "detail_level",
]


# =============================================================================
# Local EZACO JSON reader
# =============================================================================


def _read_ezaco_json(path: Path) -> tuple[pl.DataFrame, dict]:
    """Read one EZACO per-year JSON export (verbatim Socrata-style API response).

    ``read_bronze_file`` handles CSV/Excel only, so this local reader parses
    the JSON array directly with the same read-loss accounting contract:
    raw_rows = JSON array length, parsed_rows = frame height. All values are
    strings in bronze (counts carry thousands separators); the frame is built
    with an explicit all-Utf8 schema over EXPECTED_COLUMNS so the state row's
    missing `court` key becomes NULL instead of breaking schema inference
    (skill rule 4.3b analog for JSON).
    """
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{path.name}: expected a non-empty JSON array of rows")

    # Column-coverage guard: any key drift (beyond the state row's absent
    # `court`) means the upstream API changed — hard stop, never silent NULL.
    expected = set(EXPECTED_COLUMNS)
    for i, row in enumerate(rows):
        extra = set(row) - expected
        missing = expected - set(row) - {"court"}
        if extra or missing:
            raise ValueError(
                f"{path.name} row {i}: bronze schema drift — "
                f"extra keys {sorted(extra)}, missing keys {sorted(missing)}"
            )

    df = pl.DataFrame(rows, schema=dict.fromkeys(EXPECTED_COLUMNS, pl.Utf8))
    loss = {"raw_rows": len(rows), "parsed_rows": df.height, "format": "json"}
    return df, loss


def _verify_file_shape(df: pl.DataFrame, year: int, label: str) -> None:
    """Guard one export's shape: row count, state/county split, year identity."""
    if df.height != EXPECTED_ROWS_PER_FILE:
        raise ValueError(
            f"{label}: expected {EXPECTED_ROWS_PER_FILE} rows "
            f"(1 state + 159 counties), got {df.height}"
        )
    n_state = df.filter(pl.col("fct") == "0").height
    n_county = df.filter(pl.col("fct") != "0").height
    if n_state != 1 or n_county != 159:
        raise ValueError(
            f"{label}: expected 1 state row + 159 county rows, "
            f"got {n_state} + {n_county}"
        )
    if df.filter(pl.col("fct") != "0")["fct"].n_unique() != 159:
        raise ValueError(f"{label}: county fct suffixes are not unique")
    bad_years = df.filter(pl.col("yr") != str(year))
    if bad_years.height:
        raise ValueError(
            f"{label}: {bad_years.height} row(s) whose yr != filename year {year}"
        )


# =============================================================================
# Per-file transform
# =============================================================================


def _unpivot_measures(df: pl.DataFrame, year: int) -> pl.DataFrame:
    """Unpivot the 6 wide measures to long (one row per fct x measure).

    Each measure column travels with its sibling reporting flag and rate
    column, so the per-measure coverage signal stays attached to the right
    row. Output: 960 raw-string rows per file (160 x 6) with columns
    fct, measure, value_raw, flag_raw, rate_raw, year.
    """
    frames = [
        df.select(
            pl.col("fct"),
            pl.lit(measure).alias("measure"),
            pl.col(measure).alias("value_raw"),
            pl.col(f"reportingflag_{measure}").alias("flag_raw"),
            pl.col(f"{measure}rate").alias("rate_raw"),
        )
        for measure in MEASURES
    ]
    return pl.concat(frames).with_columns(pl.lit(year, dtype=pl.Int32).alias("year"))


def transform_file(path: Path, year: int, manifest: TransformManifest) -> pl.DataFrame:
    """Read + reshape one bronze year file into tagged long rows."""
    df, loss = _read_ezaco_json(path)
    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{path.name}: no era signature matched {df.columns}")
    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)

    _verify_file_shape(df, year, path.name)
    long = _unpivot_measures(df, year)
    logger.info("Processed %s: %d measure rows", path.name, long.height)
    return long


# =============================================================================
# Assembly helpers
# =============================================================================


def _strip_commas_cast(col: str, dtype: pl.DataType) -> pl.Expr:
    """Numeric cast for a bronze string cell: strip thousands separators,
    non-numeric (markers) -> NULL via strict=False."""
    return pl.col(col).str.replace_all(",", "").cast(dtype, strict=False)


def _guard_value_vocabulary(combined: pl.DataFrame) -> None:
    """Hard-stop on any cell outside the verified bronze vocabulary.

    County rows: flag must be 0/1; flag 0 pairs only with '--'; flag 1 only
    with a numeric value or a suppression marker; rates are always '--'.
    State rows: flag is a non-negative integer count; value and rate are
    numeric or '--', co-null with each other and NULL iff flag is 0. All
    verified exhaustively across the 26 files — a violation means the source
    changed and the status derivation can no longer be trusted.
    """
    is_state = pl.col("fct") == "0"
    value_num = (
        pl.col("value_raw").str.replace_all(",", "").cast(pl.Int64, strict=False)
    )
    rate_num = pl.col("rate_raw").cast(pl.Float64, strict=False)
    flag_num = pl.col("flag_raw").cast(pl.Int64, strict=False)

    checks = {
        "county flag not 0/1": ~is_state & ~pl.col("flag_raw").is_in(["0", "1"]),
        "county flag=0 without '--' value": (
            ~is_state
            & (pl.col("flag_raw") == "0")
            & (pl.col("value_raw") != UNAVAILABLE)
        ),
        "county flag=1 with unknown non-numeric value": (
            ~is_state
            & (pl.col("flag_raw") == "1")
            & value_num.is_null()
            & ~pl.col("value_raw").is_in(sorted(SUPPRESSION_MARKERS))
        ),
        "county rate not '--'": ~is_state & (pl.col("rate_raw") != UNAVAILABLE),
        "state flag non-numeric or negative": (
            is_state & (flag_num.is_null() | (flag_num < 0))
        ),
        "state value neither numeric nor '--'": (
            is_state & value_num.is_null() & (pl.col("value_raw") != UNAVAILABLE)
        ),
        "state rate neither numeric nor '--'": (
            is_state & rate_num.is_null() & (pl.col("rate_raw") != UNAVAILABLE)
        ),
        "state value/rate not co-null": (
            is_state
            & (
                (pl.col("value_raw") == UNAVAILABLE)
                != (pl.col("rate_raw") == UNAVAILABLE)
            )
        ),
        "state value availability inconsistent with flag": (
            is_state & ((pl.col("value_raw") == UNAVAILABLE) != (flag_num == 0))
        ),
        "negative count": value_num < 0,
    }
    for name, cond in checks.items():
        bad = combined.filter(cond)
        if bad.height:
            raise ValueError(
                f"Bronze vocabulary guard failed ({name}): {bad.height} row(s). "
                f"Sample:\n{bad.head(5)}"
            )


def _record_suppression_masks(
    combined: pl.DataFrame, manifest: TransformManifest
) -> None:
    """Record every marker->NULL conversion on the manifest, per marker type.

    Suppression handling (§8), not a §4b impossible-value mask — recorded via
    record_masked so masked counts are review artifacts, not just log lines
    (firearm_homicide_deaths precedent). '--' is recorded separately for
    county rows (non-reporting county) vs state rows (0 counties reported).
    """
    is_state = pl.col("fct") == "0"
    events = [
        (pl.col("value_raw") == marker, reason)
        for marker, reason in SUPPRESSION_MARKERS.items()
    ]
    events += [
        (
            ~is_state & (pl.col("value_raw") == UNAVAILABLE),
            "source_unavailable_county_did_not_report_that_measure",
        ),
        (
            is_state & (pl.col("value_raw") == UNAVAILABLE),
            "state_aggregate_unavailable_zero_counties_reporting",
        ),
    ]
    for cond, reason in events:
        hit = combined.filter(cond)
        if hit.height:
            manifest.record_masked(
                "case_count",
                hit.height,
                reason,
                years=hit["year"].unique().to_list(),
            )


def _to_gold_shape(combined: pl.DataFrame, manifest: TransformManifest) -> pl.DataFrame:
    """Derive gold columns from the verified long rows.

    County rows: 5-digit FIPS ("13" + fct zero-padded to 3 — fct suffixes are
    the odd numbers 1-321), reporting_status from the (flag, value) shape,
    NULL rate/counties_reporting. State rows: NULL FIPS + reporting_status,
    counties_reporting from the state-row flag (a count of reporting
    counties — different semantics from the county 0/1, never mixed), the
    source-computed per-1,000 rate.
    """
    is_state = pl.col("fct") == "0"

    combined = combined.with_columns(
        pl.when(is_state)
        .then(pl.lit("state"))
        .otherwise(pl.lit("county"))
        .alias("detail_level"),
        pl.when(is_state)
        .then(None)
        .otherwise(pl.lit("13") + pl.col("fct").str.zfill(3))
        .alias("county_fips"),
        pl.col("measure").replace_strict(CASE_TYPE_MAP).alias("case_type"),
        pl.col("measure").replace_strict(PETITION_STATUS_MAP).alias("petition_status"),
        _strip_commas_cast("value_raw", pl.Int64).alias("case_count"),
        # Rates are '--' on all county rows (guarded), so the strict=False
        # cast leaves county rows NULL and parses state rows.
        pl.col("rate_raw").cast(pl.Float64, strict=False).alias("case_rate_per_1000"),
        pl.when(is_state)
        .then(pl.col("flag_raw").cast(pl.Int64))
        .otherwise(None)
        .alias("counties_reporting"),
        # Row-shape marker (county rows): flag + value kind, exhaustively
        # guarded above, so replace_strict cannot hit an unmapped marker.
        pl.when(is_state)
        .then(None)
        .when(pl.col("flag_raw") == "0")
        .then(pl.lit("flag_0_unavailable"))
        .when(pl.col("value_raw") == "*")
        .then(pl.lit("flag_1_suppressed_star"))
        .when(pl.col("value_raw") == "x")
        .then(pl.lit("flag_1_suppressed_x"))
        .when(pl.col("value_raw") == "z")
        .then(pl.lit("flag_1_suppressed_z"))
        .otherwise(pl.lit("flag_1_numeric"))
        .alias("_marker"),
    )
    combined = combined.with_columns(
        pl.col("_marker")
        .replace_strict(MARKER_TO_STATUS, default=None)
        .alias("reporting_status")
    )

    # Manifest: every categorical recode, on the actual observed data.
    manifest.record_categorical(
        column="case_type",
        map_dict=CASE_TYPE_MAP,
        bronze_series=combined["measure"],
        gold_series=combined["case_type"],
    )
    manifest.record_categorical(
        column="petition_status",
        map_dict=PETITION_STATUS_MAP,
        bronze_series=combined["measure"],
        gold_series=combined["petition_status"],
    )
    county_rows = combined.filter(~is_state)
    manifest.record_categorical(
        column="reporting_status",
        map_dict=MARKER_TO_STATUS,
        bronze_series=county_rows["_marker"],
        gold_series=county_rows["reporting_status"],
    )
    # fct -> FIPS map; the state row maps to an explicit non-FIPS marker so
    # the manifest shows it handled deliberately (juvenile_population
    # precedent).
    fips_map = {
        row["fct"]: row["county_fips"]
        for row in combined.select("fct", "county_fips")
        .unique()
        .drop_nulls("county_fips")
        .to_dicts()
    }
    fips_map["0"] = "state_row_no_county_fips"
    manifest.record_categorical(
        column="county_fips",
        map_dict=fips_map,
        bronze_series=combined["fct"],
        gold_series=combined["county_fips"],
    )
    return combined.drop(
        "fct", "measure", "value_raw", "flag_raw", "rate_raw", "_marker"
    )


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for juvenile_court_cases."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + unpivot every bronze year file (read-loss accounted). The
    # year comes from the filename and is verified against every row's `yr`.
    frames: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR, extensions=[".json"]):
        year = int(path.stem.rsplit("_", 1)[-1])
        frames.append(transform_file(path, year, manifest))
    if not frames:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    combined = pl.concat(frames)
    logger.info("Unpivoted %d measure rows from %d files", combined.height, len(frames))

    # 2. Vocabulary guard, suppression accounting, gold-shape derivation.
    _guard_value_vocabulary(combined)
    _record_suppression_masks(combined, manifest)
    combined = _to_gold_shape(combined, manifest)
    combined = harmonize_columns([combined], STANDARD_COLUMNS, TARGET_TYPES)[0]

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean a routing bug and must raise, not be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: one bronze file per year, one row per (county, measure) per
    # file — duplicates are impossible by construction; sort_col "case_count"
    # is the documented safety net (prefer the fuller row) should a future
    # refresh add an overlapping file.
    combined = deduplicate_by_levels(
        combined,
        {
            "county": ["year", "county_fips", "case_type", "petition_status"],
            "state": ["year", "case_type", "petition_status"],
        },
        sort_col="case_count",
    )

    # 4. Geography nulling (shared domain rules; state rows already NULL).
    # No §4b masks: after suppression handling every value is a clean
    # non-negative integer (guarded in _guard_value_vocabulary).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=CRIMINAL_JUSTICE_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. NULL-rate spikes across years are EXPECTED and
    # documented: reporting coverage swings 152 -> 25 -> 41 counties, and
    # non-petitioned / dependency measures drop to 0 reporting counties in
    # whole eras (1997-2000, 2010-2013 non-pet; 2015, 2019, 2021-2023 dep).
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning(
            "NULL-rate spikes (documented cause: reporting-coverage swings "
            "in a voluntary county reporting system): %s",
            spike_result.details,
        )
    validate_output(
        combined,
        required_non_null=["year", "detail_level", "case_type", "petition_status"],
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
    count_null_meaning = (
        "NULL when the county did not report that measure that year "
        "(reporting_status = 'not_reported'), when the reported cell is "
        "suppressed at source (reporting_status = 'suppressed'), or on state "
        "rows when zero counties reported the measure (counties_reporting = "
        "0). Zeros are real reported zeros — never a stand-in for missing."
    )
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Juvenile court cases disposed per Georgia county per calendar "
            "year, 1997-2023 (2014 not published), from OJJDP's Easy Access "
            "to State and County Juvenile Court Case Counts (EZACO; National "
            "Center for Juvenile Justice, National Juvenile Court Data "
            "Archive; Georgia data reported by the Council of Juvenile Court "
            "Judges of Georgia). Counts are split by case type (delinquency, "
            "status offense, dependency) and handling (petitioned = formally "
            "handled, non-petitioned = informally handled). County "
            "participation is voluntary and collapses over time — 152 of 159 "
            "counties reported delinquency in 1997 but only 41 in 2023 — so "
            "every row carries a reporting_status flag, and the state "
            "summary rows aggregate REPORTING counties only (they are not "
            "statewide totals). State rows also carry the source-computed "
            "cases-per-1,000-juveniles rate and the count of reporting "
            "counties."
        ),
        title="Juvenile Court Case Counts",
        summary=(
            "Juvenile court cases disposed per Georgia county and year by "
            "case type and petition status, 1997-2023 — with explicit "
            "reporting-coverage flags (not all counties report)."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2023,
                "description": (
                    "Calendar year the cases were disposed. 2014 is absent — "
                    "Georgia did not publish that year (a source gap, not "
                    "missing data in this pipeline)."
                ),
            },
            {
                "name": "county_fips",
                "type": "string",
                "example": "13121",
                "null_meaning": (
                    "NULL on state summary rows (aggregates over reporting "
                    "counties only)."
                ),
                "description": (
                    "5-digit county FIPS code (state prefix 13) of the "
                    "county juvenile court; FK to the counties dimension. "
                    "All 159 Georgia counties appear every year, including "
                    "non-reporting ones. NULL on state summary rows."
                ),
            },
            {
                "name": "case_type",
                "type": "string",
                "nullable": False,
                "example": "delinquency",
                "validValues": CASE_TYPE_VALUES,
                "short_description": (
                    "Type of juvenile court case: delinquency, status "
                    "offense, or dependency."
                ),
                "description": (
                    "Type of juvenile court case. 'delinquency': acts that "
                    "would be crimes if committed by an adult. "
                    "'status_offense': conduct unlawful only for juveniles "
                    "(truancy, runaway, curfew). 'dependency': "
                    "abuse/neglect/dependency matters. Reporting coverage "
                    "differs by case type — dependency has zero reporting "
                    "counties in 2015, 2019, and 2021-2023."
                ),
            },
            {
                "name": "petition_status",
                "type": "string",
                "nullable": False,
                "example": "petitioned",
                "validValues": PETITION_STATUS_VALUES,
                "short_description": (
                    "How the case was handled: petitioned (formal) or "
                    "non-petitioned (informal)."
                ),
                "description": (
                    "Whether the case was handled formally ('petitioned' — a "
                    "petition was filed for an adjudicatory or waiver "
                    "hearing) or informally ('non_petitioned' — handled "
                    "without a petition, e.g. dismissed, diverted, or "
                    "informally sanctioned). The source publishes no "
                    "petitioned + non-petitioned total, and one cannot be "
                    "computed when either cell is suppressed. Reporting "
                    "coverage differs by petition status — non-petitioned "
                    "measures have zero reporting counties in 1997-2000 and "
                    "2010-2013."
                ),
            },
            {
                "name": "reporting_status",
                "type": "string",
                "validValues": REPORTING_STATUS_VALUES,
                "example": "reported",
                "null_meaning": (
                    "NULL on state summary rows (coverage there is carried "
                    "by counties_reporting instead)."
                ),
                "short_description": (
                    "Whether the county reported this measure that year: "
                    "reported, suppressed (reported but masked at source), "
                    "or not_reported."
                ),
                "description": (
                    "Coverage flag for the voluntary county reporting "
                    "system, per measure (a county can report delinquency "
                    "but not dependency). 'reported': the county reported "
                    "and the count is published. 'suppressed': the county "
                    "reported but the source masked the cell — '*' primary "
                    "suppression of values 1-4 (671 cells), 'x' secondary "
                    "suppression of values 5-20 (16 cells), 'z' secondary "
                    "suppression of a value over 20 (1 cell). "
                    "'not_reported': the county did not report that measure "
                    "(case_count is NULL; never imputed, never zero). "
                    "Distinguish not_reported from a real reported zero "
                    "using this flag, not the count."
                ),
            },
            {
                "name": "case_count",
                "type": "int64",
                "unit": "count",
                "key_metric": True,
                "example": 11708,
                "null_meaning": count_null_meaning,
                "short_description": (
                    "Juvenile court cases disposed in the county, year, case "
                    "type, and petition status."
                ),
                "description": (
                    "Number of juvenile court cases DISPOSED (cases "
                    "receiving a disposition during the calendar year, per "
                    "the source's definition) for the row's case type and "
                    "petition status. Georgia's upper age of juvenile-court "
                    "jurisdiction is 16. State rows are NCJJ's aggregate "
                    "over REPORTING counties only — never a statewide total; "
                    "compare across years only alongside counties_reporting "
                    "(coverage swings from 152 reporting counties in 1997 to "
                    "25 in 2009 to 41 in 2023). Suppressed and non-reported "
                    "cells are NULL, never zero; published zeros are real."
                ),
            },
            {
                "name": "case_rate_per_1000",
                "type": "float64",
                "example": 15.7,
                "null_meaning": (
                    "NULL on all county rows (the source publishes rates for "
                    "the state summary only) and on state rows where zero "
                    "counties reported the measure."
                ),
                "short_description": (
                    "Source-computed cases per 1,000 juveniles in reporting "
                    "counties (state rows only)."
                ),
                "description": (
                    "Cases disposed per 1,000 juveniles, as computed by the "
                    "source — state rows only (all county-row rate cells are "
                    "unpublished in every year). NOT on the platform's 0-1 "
                    "rate scale: the natural unit is cases per 1,000. The "
                    "denominator is the juvenile population OF REPORTING "
                    "COUNTIES ONLY (age 10 through the upper age 16 for "
                    "delinquency and status offense; age 0-16 for "
                    "dependency), so it tracks coverage, not the full state "
                    "juvenile population — verified equal to case_count / "
                    "reporting-population x 1000 in every published cell. "
                    "For custom rates (county-level, or statewide-population "
                    "denominators), join the juvenile_population topic."
                ),
            },
            {
                "name": "counties_reporting",
                "type": "int64",
                "unit": "count",
                "example": 41,
                "null_meaning": (
                    "NULL on county rows; populated on state summary rows only."
                ),
                "short_description": (
                    "Number of counties (of 159) that reported this measure "
                    "that year (state rows only)."
                ),
                "description": (
                    "State rows only: the number of counties (out of 159) "
                    "whose juvenile courts reported this measure that year, "
                    "as published on the source's state summary row "
                    "(verified equal to the sum of the per-county reporting "
                    "flags in every measure-year). Always read alongside "
                    "state case_count — year-over-year change in a state "
                    "total conflates caseload change with coverage change. "
                    "0 means the measure was not collected that year and the "
                    "state case_count is NULL."
                ),
            },
        ],
        source=(
            "OJJDP Statistical Briefing Book — Easy Access to State and "
            "County Juvenile Court Case Counts (EZACO)"
        ),
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        usage=(
            "Cite: Hockenberry, S. and Puzzanchera, C. Easy Access to State "
            "and County Juvenile Court Case Counts (EZACO). Online: OJJDP "
            "Statistical Briefing Book. Georgia data source: Council of "
            "Juvenile Court Judges of Georgia via the National Juvenile "
            "Court Data Archive. ALWAYS account for coverage: filter or "
            "group by reporting_status on county rows, and read state rows "
            "with counties_reporting — state figures cover reporting "
            "counties only and are NOT statewide totals. Do not sum county "
            "case_count across years or counties without checking coverage, "
            "and never treat NULL as zero. For rates with platform "
            "denominators (e.g. county-level rates or full-state juvenile "
            "population), join the juvenile_population topic on year + "
            "county_fips."
        ),
        limitations=(
            "County participation is voluntary and collapses over time: 152 "
            "of 159 counties reported delinquency in 1997, 25 in 2009, 41 "
            "in 2023; non-petitioned measures have zero reporting counties "
            "in 1997-2000 and 2010-2013, and dependency has zero in 2015, "
            "2019, and 2021-2023. State rows aggregate REPORTING counties "
            "only — they understate true statewide volume and their "
            "year-over-year change conflates caseload with coverage (use "
            "counties_reporting). 2014 is absent entirely (Georgia did not "
            "publish; never interpolated). Small counts are suppressed at "
            "source ('*' = 1-4, plus secondary suppression) — NULL, never "
            "zero — so county sums understate state rows. Rates are "
            "published for state rows only, with reporting-coverage "
            "denominators (not the full state juvenile population). "
            "Figures are cases disposed (not arrests or referrals); "
            "Georgia's upper age of juvenile-court jurisdiction is 16."
        ),
        quality_checks=[
            {
                "name": "not_reported_implies_null_count",
                "description": (
                    "A county-measure the county did not report can carry no "
                    "count — coverage is flagged, never imputed."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE reporting_status = "
                    "'not_reported' AND case_count IS NOT NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "suppressed_implies_null_count",
                "description": (
                    "A source-suppressed cell must be NULL in gold — the "
                    "masked value is never reconstructed or zero-filled."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE reporting_status = "
                    "'suppressed' AND case_count IS NOT NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "reported_implies_count_present",
                "description": (
                    "A county-measure flagged 'reported' always has a "
                    "published numeric count (verified exhaustive in bronze: "
                    "reporting flag 1 pairs only with a numeric value or a "
                    "suppression marker)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE reporting_status = "
                    "'reported' AND case_count IS NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "reporting_status_null_iff_state_row",
                "description": (
                    "reporting_status applies to county rows only: NULL on "
                    "every state row, non-NULL on every county row (state "
                    "coverage is carried by counties_reporting)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(county_fips IS NULL AND reporting_status IS NOT NULL) "
                    "OR (county_fips IS NOT NULL AND reporting_status IS "
                    "NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "counties_reporting_on_state_rows_only",
                "description": (
                    "counties_reporting is a state-row coverage measure — "
                    "NULL on every county row, populated on every state row."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(county_fips IS NOT NULL AND counties_reporting IS NOT "
                    "NULL) OR (county_fips IS NULL AND counties_reporting "
                    "IS NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "counties_reporting_matches_county_flags",
                "description": (
                    "The state row's published count of reporting counties "
                    "must equal the number of county rows with "
                    "reporting_status 'reported' or 'suppressed' for that "
                    "year and measure (verified exact in all 156 bronze "
                    "measure-years)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, case_type, petition_status, "
                    "MAX(CASE WHEN county_fips IS NULL THEN "
                    "counties_reporting END) AS cr, "
                    "SUM(CASE WHEN county_fips IS NOT NULL AND "
                    "reporting_status != 'not_reported' THEN 1 ELSE 0 END) "
                    "AS reporting_rows "
                    "FROM {object} GROUP BY year, case_type, petition_status"
                    ") WHERE cr IS NOT NULL AND cr != reporting_rows"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_count_null_iff_zero_counties_reporting",
                "description": (
                    "The state aggregate is published exactly when at least "
                    "one county reported the measure (verified exact in "
                    "bronze: state '--' pairs only with a zero reporting "
                    "flag)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE county_fips IS NULL "
                    "AND ((case_count IS NULL) != (counties_reporting = 0))"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_count_at_least_visible_county_sum",
                "description": (
                    "The state row sums reporting counties INCLUDING "
                    "suppressed cells, so it must be >= the sum of visible "
                    "county counts for every year and measure."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, case_type, petition_status, "
                    "MAX(CASE WHEN county_fips IS NULL THEN case_count END) "
                    "AS state_total, "
                    "SUM(CASE WHEN county_fips IS NOT NULL THEN case_count "
                    "END) AS county_sum "
                    "FROM {object} GROUP BY year, case_type, petition_status"
                    ") WHERE state_total IS NOT NULL AND county_sum IS NOT "
                    "NULL AND state_total < county_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_count_equals_county_sum_when_no_suppression",
                "description": (
                    "When no county cell is suppressed for a year and "
                    "measure, the state aggregate must equal the county sum "
                    "exactly (verified in bronze; the gap in other groups is "
                    "exactly the suppressed cells)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, case_type, petition_status, "
                    "MAX(CASE WHEN county_fips IS NULL THEN case_count END) "
                    "AS state_total, "
                    "SUM(CASE WHEN county_fips IS NOT NULL THEN case_count "
                    "END) AS county_sum, "
                    "SUM(CASE WHEN reporting_status = 'suppressed' THEN 1 "
                    "ELSE 0 END) AS n_suppressed "
                    "FROM {object} GROUP BY year, case_type, petition_status"
                    ") WHERE state_total IS NOT NULL AND county_sum IS NOT "
                    "NULL AND n_suppressed = 0 AND state_total != county_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "rate_on_state_rows_only",
                "description": (
                    "The source publishes per-1,000 rates for the state "
                    "summary only — every county-row rate cell is "
                    "unpublished in all 26 years (verified)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE county_fips IS NOT "
                    "NULL AND case_rate_per_1000 IS NOT NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_rate_null_iff_state_count_null",
                "description": (
                    "On state rows the published rate and count are co-null "
                    "— a rate exists exactly when the aggregate count does "
                    "(verified exact in bronze)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE county_fips IS NULL "
                    "AND ((case_rate_per_1000 IS NULL) != (case_count IS "
                    "NULL))"
                ),
                "mustBe": 0,
            },
            {
                "name": "case_rate_per_1000_non_negative",
                "description": (
                    "Rates cannot be negative. (Authored because per-1,000 "
                    "rates carry no unit marker — neither 'proportion' nor "
                    "'ratio' describes a per-1,000 scale.)"
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE case_rate_per_1000 "
                    "IS NOT NULL AND case_rate_per_1000 < 0"
                ),
                "mustBe": 0,
            },
            {
                "name": "all_159_counties_every_measure",
                "description": (
                    "Every published year lists all 159 Georgia counties for "
                    "every case type and petition status (non-reporters "
                    "included with NULL counts)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, case_type, petition_status, "
                    "COUNT(CASE WHEN county_fips IS NOT NULL THEN 1 END) "
                    "AS n_counties "
                    "FROM {object} GROUP BY year, case_type, petition_status"
                    ") WHERE n_counties != 159"
                ),
                "mustBe": 0,
            },
            {
                "name": "counties_reporting_within_159",
                "description": (
                    "No measure-year can have more reporting counties than "
                    "Georgia has counties."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE counties_reporting > 159"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
