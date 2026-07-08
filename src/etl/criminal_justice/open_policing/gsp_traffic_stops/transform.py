"""Transform SOPP Georgia state-patrol stop microdata into a county/year fact table.

Source: Stanford Open Policing Project (SOPP) standardized traffic-stop
microdata for Georgia — one row per Georgia State Patrol / Department of
Public Safety stop, 2012-01-01 to 2016-12-31 (1,906,772 rows). The bronze is
a single zip whose one CSV member is read directly through ``zipfile``
(never extracted to disk — provenance/PII contract).

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **PII rule: stop-level rows never reach gold.** Only three bronze columns
  are ever read (``date``, ``county_name``, ``subject_race``); the stop-level
  frame is aggregated to (year x county x race) counts inside the read
  function and discarded. None of raw_row_number, time, location, lat, lng,
  officer_id_hash, violation, or the vehicle descriptors are read at all.
- **Grain: county_fips x year x demographic (+ a statewide rollup).** Single
  metric ``traffic_stops`` = count of stop rows per cell. State rows follow
  the domain convention (detail_level="state", NULL county_fips) and cover
  the FULL stop universe, including the 10 stops with no mappable county.
- **Warnings-only, single-agency scope.** ``outcome`` is the constant
  ``warning`` and ``type`` the constant ``vehicular`` for every row (verified
  in the structure doc) — both carry zero information and are dropped.
  Georgia supplied no search / contraband / citation / arrest columns, so the
  dataset supports stop-volume and stop-composition analysis only; this is
  stated prominently in the contract description and limitations.
- **Unknown race -> ``race_unknown``.** ``subject_race`` is the source's NA
  sentinel for 47.1% of stops. The global demographics dimension carries the
  canonical ``race_unknown`` value (category ``race``; aliases UNKNOWN / NOT
  REPORTED), so NA race is published as ``race_unknown`` rather than dropped:
  every stop is represented in the race splits and the six race-axis values
  partition the ``all`` row exactly (enforced by an authored quality check).
  This deliberately revises the "NULL demographic stays NULL" default, which
  targets row-per-demographic aggregate sources — here NULL is a real
  population of stops (race not recorded), not an aggregate marker.
- **Asian / Pacific Islander (S5b).** The source publishes only the combined
  ``asian/pacific islander`` bucket (8,753 stops) with no separate Pacific
  Islander value anywhere -> mapped to ``asian_pacific_islander``, never bare
  ``asian``; no split pair is emitted. The source's standardization folds raw
  ``Native American`` into ``other`` (documented in the contract).
- **Unmappable counties: excluded from county rows, kept in the state
  rollup.** 159 real county names (1,906,762 stops) resolve 1:1 via
  ``add_county_fips`` after stripping the " County" suffix. The remaining 10
  stops — 9 under seven ``G###`` placeholder codes plus 1 with no county —
  cannot carry a FIPS and follow the decision_points OUT OF STATE precedent:
  excluded from county-level rows (``record_filtered``, documented in the
  contract) and included in state rows so statewide totals cover the full
  published universe. Any unmatched name that is NOT a G-code placeholder
  hard-stops the run (a real county failing to match is a crosswalk bug,
  never a silent NULL).
- **Year floor (orchestrator hard rule).** Rows with year < 2000 are filtered
  defensively before export (none exist — data is 2012-2016) and the floor is
  recorded in the contract limitations and enforced by a quality check.
- **Dedup tie-break.** A single bronze file feeds gold and every cell is
  produced by one group_by, so duplicate natural keys are impossible by
  construction; ``deduplicate_by_levels(sort_col="traffic_stops")`` remains
  as the documented safety net (prefer the fuller row) should a future
  refresh add an overlapping file. The collision guard runs first and would
  surface any divergent duplicate as a hard error.
- **No S4b masks.** The single metric is a row count computed by this
  transform (never a source-published value), so no impossible source values
  exist to NULL. ``lat``/``lng`` garbage documented in the structure doc is
  moot — coordinates are never read.
- **No suppression.** SOPP microdata is unsuppressed (every stop is a row);
  ``suppressed_to_null=False`` and gold metric cells are fully non-null —
  cells exist only where at least one stop occurred (no zero-fill).
- **License.** ODC-BY 1.0 (Open Data Commons Attribution) — attribution to
  the Stanford Open Policing Project is carried in the contract ``usage``.
"""

import logging
import re
import zipfile
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

TOPIC = "gsp_traffic_stops"
BRONZE_DIR = Path("data/bronze/criminal_justice/open_policing/gsp_traffic_stops")
GOLD_DIR = Path("data/gold/criminal_justice/gsp_traffic_stops")
SOURCE_URL = "https://openpolicing.stanford.edu/data/"

# Orchestrator hard rule: no gold rows before this year (data is 2012-2016;
# the filter is defensive and the floor is documented in the contract).
YEAR_FLOOR = 2000

# The three bronze columns this transform is allowed to read (PII contract —
# everything else stays in bronze and is never materialized).
READ_COLUMNS: list[str] = ["date", "county_name", "subject_race"]

# The full 19-column CSV member header, in order (structure doc "Eras").
# Verified byte-exact against the member at read time; any deviation is a
# source format change and must hard-stop, not pass on.
EXPECTED_HEADER: list[str] = [
    "raw_row_number",
    "date",
    "time",
    "location",
    "lat",
    "lng",
    "county_name",
    "subject_race",
    "subject_sex",
    "officer_id_hash",
    "department_name",
    "type",
    "violation",
    "outcome",
    "vehicle_color",
    "vehicle_make",
    "vehicle_model",
    "vehicle_year",
    "raw_race",
]

# Era detection by column signature over the member header. A single era
# spans the whole (frozen) file; the signature guards against a silent future
# format change rather than distinguishing eras.
ERA_SIGNATURES: dict[str, list[str]] = {
    "sopp_ga_statewide_v1": [
        "raw_row_number",
        "date",
        "county_name",
        "subject_race",
        "raw_race",
    ],
}

# Fill label for the source's NA race sentinel, applied BEFORE
# normalize_demographic_column: "UNKNOWN" aliases to the canonical
# race_unknown dimension value (module docstring, "Unknown race").
UNKNOWN_RACE_FILL = "unknown"

# The race-axis values gold emits (used by the partition quality check and
# the contract enum so the two cannot drift). asian_pacific_islander is the
# source's combined bucket (S5b); race_unknown covers unrecorded race.
RACE_DEMOGRAPHICS: list[str] = [
    "asian_pacific_islander",
    "black",
    "hispanic",
    "other",
    "race_unknown",
    "white",
]

# Unmatched county base names must look like the source's G### placeholder
# codes (e.g. "G047"); anything else is a real county that failed to match.
G_PLACEHOLDER_RE = re.compile(r"^G\d{3}$")

# Manifest marker for county labels that legitimately carry no FIPS
# (mirrors the decision_points OUT OF STATE convention).
NO_FIPS_MARKER = "state_rollup_only_no_county_fips"

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "county_fips",
    "demographic",
    "traffic_stops",
    "detail_level",
]

METRIC_COLUMNS: list[str] = ["traffic_stops"]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "county_fips": pl.Utf8,
    "demographic": pl.Utf8,
    "traffic_stops": pl.Int64,
    "detail_level": pl.Utf8,
}

NATURAL_KEYS: list[str] = ["year", "county_fips", "demographic", "detail_level"]

# Total stops with no mappable county in the frozen 2012-2016 file (9 G###
# placeholder rows + 1 NULL county row) — the documented bound for the
# state-covers-county-sum quality check.
UNMAPPABLE_STOPS_BOUND = 10


# =============================================================================
# Bronze read (zip member -> aggregated counts; stop-level rows die here)
# =============================================================================


def _scan_member_header_and_lines(
    zf: zipfile.ZipFile, member: str
) -> tuple[list[str], int]:
    """Stream the CSV member once to capture the header and count raw rows.

    Streams in 4 MiB chunks so the 408 MB member is never held in memory.
    Raw data rows = physical lines minus the header line; exact for this file
    (the structure doc verifies 1,906,772 rows parse cleanly), and any
    divergence from the parsed count is surfaced via record_read_loss.
    """
    newlines = 0
    header_buf = b""
    header: list[str] | None = None
    last_byte = b""
    with zf.open(member) as fh:
        while True:
            chunk = fh.read(1 << 22)
            if not chunk:
                break
            newlines += chunk.count(b"\n")
            last_byte = chunk[-1:]
            if header is None:
                header_buf += chunk
                nl = header_buf.find(b"\n")
                if nl != -1:
                    header = header_buf.decode("utf-8")[:nl].rstrip("\r").split(",")
                    header_buf = b""
    if header is None:
        raise ValueError(f"{member}: no header line found")
    total_lines = newlines + (0 if last_byte == b"\n" else 1)
    return header, total_lines - 1


def _read_stop_counts(path: Path, manifest: TransformManifest) -> pl.DataFrame:
    """Read the zip's CSV member and aggregate to (year, county, race) counts.

    The stop-level frame exists only inside this function (PII rule): it is
    reduced to at most a few thousand (year x county_name x subject_race)
    rows with an ``n_stops`` weight before returning. Only READ_COLUMNS are
    materialized; the literal string "NA" is the file's null sentinel.
    """
    with zipfile.ZipFile(path) as zf:
        members = zf.namelist()
        if len(members) != 1:
            raise ValueError(f"{path.name}: expected 1 zip member, got {members}")
        member = members[0]

        header, raw_rows = _scan_member_header_and_lines(zf, member)
        # Exact-header guard: an unmatched source column silently NULLs in
        # gold — any header change must hard-stop and be re-analyzed.
        if header != EXPECTED_HEADER:
            raise ValueError(f"{member}: header changed — new era? Got: {header}")
        era = detect_era_by_columns(
            pl.DataFrame(schema=dict.fromkeys(header, pl.Utf8)), ERA_SIGNATURES
        )
        if era is None:
            raise ValueError(f"{member}: no era signature matched {header}")

        # All-string read (skill rule 4.3b) restricted to the three needed
        # columns; "NA" (the file's only null marker) becomes true NULL.
        with zf.open(member) as fh:
            stops = pl.read_csv(
                fh,
                columns=READ_COLUMNS,
                infer_schema_length=0,
                null_values=["NA"],
            )

    manifest.record_read_loss(2016, path.name, raw_rows, stops.height)
    manifest.record_file(path, 2016, era, stops.height, header)
    logger.info(
        "Read %s rows x %d columns from %s (member %s) as %s",
        f"{stops.height:,}",
        stops.width,
        path.name,
        member,
        era,
    )

    # Year from the ISO stop date. The date column has zero NAs in the frozen
    # file; a NULL year would mean format drift and must hard-stop.
    stops = stops.with_columns(
        pl.col("date").str.slice(0, 4).cast(pl.Int32, strict=False).alias("year")
    )
    if stops["year"].null_count():
        raise ValueError(
            f"{path.name}: {stops['year'].null_count()} stop(s) with unparseable "
            "date — bronze has zero date NAs; investigate the source format"
        )

    # Aggregate IMMEDIATELY (PII + memory rule): the 1.9M-row stop frame
    # collapses to <=(5 years x 167 county labels x 6 race values) count rows.
    counts = stops.group_by("year", "county_name", "subject_race").agg(
        pl.len().cast(pl.Int64).alias("n_stops")
    )
    del stops

    per_year = counts.group_by("year").agg(pl.col("n_stops").sum()).sort("year")
    for row in per_year.to_dicts():
        manifest.record_bronze(row["year"], row["n_stops"])
    return counts


# =============================================================================
# Recodes on the aggregated counts frame
# =============================================================================


def _apply_year_floor(df: pl.DataFrame, manifest: TransformManifest) -> pl.DataFrame:
    """Drop pre-2000 rows (orchestrator hard rule; defensive — none exist)."""
    dropped = df.filter(pl.col("year") < YEAR_FLOOR)
    if dropped.height:
        for row in dropped.group_by("year").agg(pl.col("n_stops").sum()).to_dicts():
            manifest.record_filtered(
                row["year"], row["n_stops"], "year_before_2000_floor"
            )
        logger.warning(
            "Year floor: dropped %d stop(s) before %d (years: %s)",
            dropped["n_stops"].sum(),
            YEAR_FLOOR,
            sorted(dropped["year"].unique().to_list()),
        )
    return df.filter(pl.col("year") >= YEAR_FLOOR)


def _resolve_demographic(df: pl.DataFrame, manifest: TransformManifest) -> pl.DataFrame:
    """Map subject_race to canonical demographics; NA race -> race_unknown.

    The NA sentinel (47.1% of stops — driver race not recorded) is filled
    with the "unknown" label BEFORE the shared normalizer so it canonicalizes
    to the dimension's race_unknown value: every stop is represented in the
    race splits and the race axis partitions the 'all' row exactly. The
    effective DEMOGRAPHIC_ALIASES slice is recorded per skill rule 4.3a; a
    label missing from the aliases stays unmapped and blocks the run.
    """
    filled = pl.col("subject_race").fill_null(UNKNOWN_RACE_FILL)
    df = df.with_columns(normalize_demographic_column(filled).alias("demographic"))

    bronze_series = df.select(filled.alias("r"))["r"]
    observed = bronze_series.unique().to_list()
    effective_map = {
        label: DEMOGRAPHIC_ALIASES[label.strip().upper()]
        for label in observed
        if label.strip().upper() in DEMOGRAPHIC_ALIASES
    }
    manifest.record_categorical(
        column="demographic",
        map_dict=effective_map,
        bronze_series=bronze_series,
        gold_series=df["demographic"],
    )

    unexpected = set(df["demographic"].unique().to_list()) - set(RACE_DEMOGRAPHICS)
    if unexpected:
        raise ValueError(
            f"Unexpected demographic value(s) after normalization: {unexpected}"
        )
    return df


def _resolve_county_fips(df: pl.DataFrame, manifest: TransformManifest) -> pl.DataFrame:
    """Strip the " County" suffix and join county FIPS; guard the residual.

    159 real names resolve 1:1 against the global counties dimension. The
    only tolerated non-matches are the source's G### placeholder codes and
    the NULL county row (10 stops total) — they carry no FIPS and appear only
    in the state rollup. Any OTHER unmatched name is a real county that
    failed to match (crosswalk/source drift) and hard-stops the run.
    """
    df = df.with_columns(
        pl.col("county_name").str.strip_suffix(" County").alias("_county_base")
    )
    df = add_county_fips(df, "_county_base")

    unmatched = df.filter(
        pl.col("county_fips").is_null() & pl.col("_county_base").is_not_null()
    )
    bad_names = [
        n
        for n in unmatched["_county_base"].unique().sort().to_list()
        if not G_PLACEHOLDER_RE.match(n)
    ]
    if bad_names:
        raise ValueError(
            "Unmatched real county name(s) — crosswalk or source drift, "
            f"never silently NULLed: {bad_names}"
        )

    # Record the observed name -> FIPS recode. Placeholder codes map to an
    # explicit non-FIPS marker so the manifest shows them handled
    # deliberately (state rollup only) rather than unmapped.
    county_map = {
        row["_county_base"]: row["county_fips"]
        for row in df.select("_county_base", "county_fips")
        .unique()
        .drop_nulls("county_fips")
        .to_dicts()
    }
    for name in unmatched["_county_base"].unique().sort().to_list():
        county_map[name] = NO_FIPS_MARKER
    manifest.record_categorical(
        column="county_fips",
        map_dict=county_map,
        bronze_series=df["_county_base"],
        gold_series=df["county_fips"],
    )

    # The unmappable stops (placeholders + the NULL county row) are excluded
    # from county-level cells but kept in the state rollup.
    no_fips = df.filter(pl.col("county_fips").is_null())
    if no_fips.height:
        total = no_fips["n_stops"].sum()
        if total > UNMAPPABLE_STOPS_BOUND:
            raise ValueError(
                f"{total} stops with no mappable county exceeds the documented "
                f"bound of {UNMAPPABLE_STOPS_BOUND} — bronze changed; re-analyze"
            )
        for row in (
            no_fips.group_by("year")
            .agg(pl.col("n_stops").sum())
            .sort("year")
            .to_dicts()
        ):
            manifest.record_filtered(
                row["year"],
                row["n_stops"],
                "unmappable_county_excluded_from_county_level_kept_in_state",
            )
        logger.warning(
            "%d stop(s) with no mappable county (G### placeholders + NULL) "
            "excluded from county rows, kept in the state rollup: %s",
            total,
            no_fips["_county_base"].unique().sort().to_list(),
        )
    return df.drop("_county_base")


# =============================================================================
# Aggregation to gold cells
# =============================================================================


def _aggregate_level(
    df: pl.DataFrame, geo_cols: list[str], detail_level: str
) -> pl.DataFrame:
    """Aggregate one detail level across the 'all' and race demographic slices.

    Emits 'all' (every stop) plus one row per race-axis value — two
    overlapping slices packed into `demographic` per project convention (§5a:
    race values, including race_unknown, are mutually exclusive per stop;
    'all' is the unfiltered total). Grouping happens on the ALREADY-normalized
    demographic, so labels aliasing to one canonical value aggregate here
    rather than reaching dedup.
    """
    frames = []
    for demo_expr in (pl.lit("all"), pl.col("demographic")):
        frames.append(
            df.with_columns(demo_expr.alias("demographic"))
            .group_by(["year", *geo_cols, "demographic"])
            .agg(pl.col("n_stops").sum().cast(pl.Int64).alias("traffic_stops"))
        )
    out = pl.concat(frames).with_columns(pl.lit(detail_level).alias("detail_level"))
    if "county_fips" not in geo_cols:
        out = out.with_columns(pl.lit(None).cast(pl.Utf8).alias("county_fips"))
    return out


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for gsp_traffic_stops."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read the single zip bronze file -> aggregated counts (read-loss
    # accounted; stop-level rows never leave the read function).
    paths = list_bronze_files(BRONZE_DIR, extensions=[".zip"])
    if len(paths) != 1:
        raise ValueError(f"Expected exactly 1 bronze zip in {BRONZE_DIR}, got {paths}")
    counts = _read_stop_counts(paths[0], manifest)

    # 2. Recodes on the aggregated frame: year floor, demographics, FIPS.
    counts = _apply_year_floor(counts, manifest)
    counts = _resolve_demographic(counts, manifest)
    counts = _resolve_county_fips(counts, manifest)

    # 3. County cells (mappable stops only) + state rollup (every stop,
    # including the 10 with no mappable county), then harmonize + concat.
    counties = _aggregate_level(
        counts.filter(pl.col("county_fips").is_not_null()),
        geo_cols=["county_fips"],
        detail_level="county",
    )
    states = _aggregate_level(counts, geo_cols=[], detail_level="state")
    logger.info(
        "Aggregated %s stops into %d county and %d state cells",
        f"{counts['n_stops'].sum():,}",
        counties.height,
        states.height,
    )
    combined = pl.concat(
        harmonize_columns(
            [counties.select(STANDARD_COLUMNS), states.select(STANDARD_COLUMNS)],
            STANDARD_COLUMNS,
            TARGET_TYPES,
        )
    )

    # 4. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean an aggregation bug and must raise, not be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: one bronze file feeds gold and every cell comes from one
    # group_by, so duplicates are impossible by construction; sort_col
    # "traffic_stops" is the documented safety net (prefer the fuller row)
    # should a future refresh introduce an overlapping file.
    combined = deduplicate_by_levels(
        combined,
        {
            "county": ["year", "county_fips", "demographic"],
            "state": ["year", "demographic"],
        },
        sort_col="traffic_stops",
    )

    # 5. Geography nulling (shared domain rules; state rows already NULL).
    # No §4b masks apply — the single metric is a transform-computed row
    # count, never a source-published value (module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=CRIMINAL_JUSTICE_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. The metric is fully non-null by construction (cells
    # only exist where stops occurred), so any spike is a regression.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(combined, required_non_null=["year", "demographic", "detail_level"])

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
    demographic_values = sorted(["all", *RACE_DEMOGRAPHICS])
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Traffic stops by the Georgia State Patrol (Georgia Department of "
            "Public Safety), counted per county, year, and driver race group "
            "from the Stanford Open Policing Project's standardized stop-level "
            "records, 2012-2016. IMPORTANT SCOPE: every stop in this dataset "
            "resulted in a WARNING — Georgia supplied warnings-only data with "
            "no citation, arrest, search, or contraband fields — so it "
            "supports stop-volume and stop-composition analysis only (who "
            "gets stopped, where), never search-rate, hit-rate, citation, or "
            "arrest-disparity metrics. Single agency: state patrol stops "
            "only, not municipal police or sheriff's office stops. Driver "
            "race was not recorded for 47.1% of stops, served as the "
            "race_unknown group so race groups always sum to the all row."
        ),
        title="State Patrol Traffic Stops",
        summary=(
            "Georgia State Patrol traffic stops (all warnings) per county, "
            "year, and driver race group, 2012-2016, from the Stanford Open "
            "Policing Project."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2014,
                "description": (
                    "Calendar year of the stop, derived from the stop date. "
                    "Coverage is 2012-2016 and frozen (the source project no "
                    "longer updates); rows before 2000 are excluded by a "
                    "project-wide floor (none occur in this source)."
                ),
            },
            {
                "name": "county_fips",
                "type": "string",
                "example": "13121",
                "null_meaning": "NULL on statewide rollup rows.",
                "description": (
                    "5-digit county FIPS code (state prefix 13) of the county "
                    "where the stop occurred; FK to the counties dimension. "
                    "NULL on statewide rollup rows. 10 of 1,906,772 stops (9 "
                    "under G-code placeholder county labels, 1 with no county "
                    "recorded) cannot be mapped to a county and are counted "
                    "only in the statewide rows."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "all",
                "validValues": demographic_values,
                "short_description": (
                    "Driver race group the row covers: every stop (all), one "
                    "of the source's race groups, or race_unknown."
                ),
                "description": (
                    "Driver race group. 'all' is the unfiltered total; the "
                    "remaining values are the source's standardized, mutually "
                    "exclusive race buckets plus race_unknown, and together "
                    "they partition the all row exactly — summing the six "
                    "non-all values reproduces it. asian_pacific_islander is "
                    "the source's combined bucket (no separate Asian or "
                    "Pacific Islander values exist anywhere in the source). "
                    "hispanic is an exclusive bucket (other buckets exclude "
                    "Hispanic drivers), and the source's standardization "
                    "folds Native American drivers into 'other'. race_unknown "
                    "covers stops where driver race was not recorded — 47.1% "
                    "of all stops, so compare race-group shares with that "
                    "denominator caveat in mind."
                ),
            },
            {
                "name": "traffic_stops",
                "type": "int64",
                "nullable": False,
                "unit": "count",
                "key_metric": True,
                "example": 21641,
                "short_description": (
                    "Number of state patrol traffic stops (each resulting in "
                    "a warning) in the county, year, and driver race group."
                ),
                "description": (
                    "Count of Georgia State Patrol traffic stops in the cell, "
                    "aggregated from stop-level records (one record per "
                    "stop). Every stop in the source resulted in a warning, "
                    "so this equals the count of warnings issued. Cells exist "
                    "only where at least one stop occurred — there are no "
                    "zero-filled cells, and the metric is never NULL."
                ),
            },
        ],
        source=(
            "Stanford Open Policing Project — Georgia statewide traffic "
            "stops (Georgia Department of Public Safety / State Patrol)"
        ),
        source_url=SOURCE_URL,
        update_frequency="static (frozen source; 2012-2016 is complete and final)",
        year_range=year_range,
        suppressed_to_null=False,
        usage=(
            "Attribute the Stanford Open Policing Project "
            "(openpolicing.stanford.edu); the data is licensed ODC-BY 1.0 "
            "(Open Data Commons Attribution License). Filter demographic = "
            "'all' for total stop volume, or exclude 'all' to compare race "
            "groups (they are mutually exclusive and sum to the all row). "
            "Always interpret race composition alongside the race_unknown "
            "share — driver race is unrecorded for 47.1% of stops overall "
            "and the share varies by county and year. This dataset measures "
            "state-patrol warning stops only; do not treat it as total "
            "traffic enforcement in a county, and do not derive search, "
            "citation, or arrest metrics from it (none exist for Georgia)."
        ),
        limitations=(
            "State rows have NULL county_fips. Warnings-only, single-agency "
            "data: Georgia supplied only Georgia State Patrol / Department "
            "of Public Safety stops that resulted in warnings — no citation, "
            "arrest, search, or contraband fields exist, so the dataset "
            "supports stop-volume and stop-composition analysis only, and it "
            "excludes municipal police and sheriff stops. Driver race is not "
            "recorded for 47.1% of stops (served as race_unknown); "
            "race-group shares carry that denominator caveat. 10 of "
            "1,906,772 stops carry unmappable county labels and are excluded "
            "from county rows but included in statewide rows, so county rows "
            "sum at most 10 stops below the statewide row. Coverage is "
            "frozen at 2012-2016; rows before calendar year 2000 are "
            "excluded by a project-wide floor (none occur in this source). A "
            "residual 302 stops carry Department of Natural Resources or "
            "Georgia State Patrol agency labels rather than the Department "
            "of Public Safety label and are included. The source has no "
            "suppression: cells exist only where stops occurred, and counts "
            "are never NULL."
        ),
        quality_checks=[
            {
                "name": "race_partition_traffic_stops",
                "description": (
                    "Every stop carries exactly one race-axis value "
                    "(including race_unknown for unrecorded race), so per "
                    "(year, county_fips) the six race rows must sum exactly "
                    "to the 'all' row. GROUP BY treats the NULL county_fips "
                    "of state rows as one group, so the invariant is "
                    "enforced at both detail levels."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, "
                    "MAX(CASE WHEN demographic = 'all' THEN traffic_stops "
                    "END) AS total, "
                    "SUM(CASE WHEN demographic IN ("
                    + ",".join(f"'{d}'" for d in RACE_DEMOGRAPHICS)
                    + ") THEN traffic_stops END) AS race_sum "
                    "FROM {object} GROUP BY year, county_fips"
                    ") WHERE total IS NOT NULL AND race_sum IS NOT NULL "
                    "AND total != race_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_covers_county_sum",
                "description": (
                    "State rows count every stop while county rows exclude "
                    "the 10 stops with unmappable county labels, so per "
                    "(year, demographic) the state value must be at least "
                    "the county sum and exceed it by at most 10."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, demographic, "
                    "MAX(CASE WHEN county_fips IS NULL THEN traffic_stops "
                    "END) AS state_total, "
                    "SUM(CASE WHEN county_fips IS NOT NULL THEN "
                    "traffic_stops END) AS county_sum "
                    "FROM {object} GROUP BY year, demographic"
                    ") WHERE state_total IS NOT NULL AND county_sum IS NOT "
                    "NULL AND (county_sum > state_total OR "
                    f"state_total - county_sum > {UNMAPPABLE_STOPS_BOUND})"
                ),
                "mustBe": 0,
            },
            {
                "name": "traffic_stops_positive",
                "description": (
                    "Cells are emitted only for observed (year, geography, "
                    "demographic) groups — no zero-fill — so every count "
                    "must be at least 1."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE traffic_stops IS "
                    "NULL OR traffic_stops < 1"
                ),
                "mustBe": 0,
            },
            {
                "name": "year_at_or_after_2000",
                "description": (
                    "Project-wide year floor: no gold rows before calendar "
                    "year 2000 (the source spans 2012-2016)."
                ),
                "dimension": "accuracy",
                "query": (f"SELECT COUNT(*) FROM {{object}} WHERE year < {YEAR_FLOOR}"),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
