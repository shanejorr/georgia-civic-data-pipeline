"""Transform bronze FBI NIBRS master zips into a gold offense-count fact table.

Source: FBI Crime Data Explorer NIBRS master state extracts for Georgia
(GA-2018.zip ... GA-2024.zip) — relational incident-level segment tables.
This topic serves the OFFENSE side (NIBRS_OFFENSE joined through
NIBRS_incident -> agencies -> the ORI-to-county crosswalk), aggregated to
county x year x offense type. The arrestee segments in the same zips belong
to the sibling ``nibrs_arrests`` topic; zip/member mechanics shared by both
live in ``src/etl/criminal_justice/fbi_cde/_nibrs_shared.py``.

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Grain: year x county_fips x offense_type (+ statewide rollup).** The
  orchestration brief asked for category-level rollups; gold instead keeps
  the full NIBRS offense-code granularity (52 observed codes, served as
  descriptive snake_case ``offense_type`` values per the no-source-codes
  convention) and denormalizes ``offense_category`` (35 FBI categories) and
  ``crime_against`` (person/property/society) as functionally dependent
  attributes — "preserve bronze granularity" wins because category rollups
  are exactly recoverable by grouping, while e.g. aggravated vs simple
  assault would be unrecoverable at category grain. Both attributes are
  code-dependent, not category-dependent ("Other Offenses" spans two
  crime_against values), so they ride the offense_type grain safely.
- **Pinned offense vocabulary (2024 lookup).** Offense labels come from a
  hardcoded map generated from GA-2024.zip's NIBRS_OFFENSE_TYPE (the latest
  lookup), so labels cannot flap by data year (the 11D "Fondling" ->
  "Criminal Sexual Contact" rename is pinned to the 2024 wording). Era 1
  (2018-2020) joins OFFENSE -> OFFENSE_TYPE on the surrogate
  ``offense_type_id`` FROM THE SAME ZIP to recover ``offense_code``; era 2
  (2021-2024) carries ``offense_code`` directly. Codes then map through the
  pinned vocabulary for every year.
- **Group A only, guarded.** Only Group A offenses appear in NIBRS_OFFENSE
  (Group B are arrest-only; ``90I`` Runaway is "Not a Crime"). The pinned
  vocabulary covers all 72 Group A codes; any non-Group-A code that ever
  appears is filtered with a logged count + ``record_filtered`` (zero today),
  and any UNKNOWN code hard-fails.
- **County attribution: primary county, statewide agencies to state only.**
  Agencies join the ORI crosswalk; multi-county agencies (27 of 434 in 2024)
  are attributed wholly to their PRIMARY county — never split, never
  double-counted. Agencies with NULL crosswalk county (GBI, State Patrol,
  Ports Authority — 12 statewide ORIs) contribute to the state rollup only;
  zero such agencies reported incidents in 2018-2024, so state currently
  equals the county sum exactly, and the authored invariant is
  ``state >= county sum`` (structural, survives a future GBI submission).
- **Methodology: NIBRS raw counts, unestimated; coverage flag, never
  blending.** Georgia transitioned from SRS to NIBRS around Oct 2019 —
  2018-2019 are early-adopter years (37 / 276 distinct agencies; the 2018
  roster publishes 49 rows with 12 exact duplicates, deduplicated before the
  join so 2018 counts are not inflated) and NOT comparable to later years as
  a state series. Every row carries a ``coverage``
  categorical (``partial_adoption`` 2018-2019, ``full_participation``
  2020+) plus an ``agencies_reporting`` coverage companion metric (the
  year's reporting-agency roster count: statewide on state rows, the
  county's roster count on county rows, constant within year x county by an
  authored check), so consumers can separate crime change from adoption
  change.
- **SRS estimates sidecar EXCLUDED.** ``srs_estimates/estimated_crimes_1979_
  2024.csv`` is state-grain ESTIMATED SRS index-crime data whose category
  vocabulary (hierarchy-ruled violent/property indexes) does not align with
  NIBRS offense categories; splicing it in — even labeled — would invite
  cross-methodology series. Excluded from this topic (recorded on the
  manifest) per the domain rule "version methodological breaks, never pool
  across them"; the 1979+ SRS history should ship as its own topic if wanted.
- **No demographic column.** The offense segment carries no person
  attributes; victim/offender/arrestee demographics belong to sibling NIBRS
  topics. Emitting demographic splits here would require victim-side joins
  that change the unit of count (victims, not offenses), so none are served.
- **Metrics.** ``offense_count`` (key metric: count of NIBRS_OFFENSE rows —
  the FBI's offense-count convention), its attempted/completed partition
  (``completed_count + attempted_count = offense_count``, authored check),
  ``incident_count`` (distinct incidents involving the offense type —
  additive across counties, NOT additive across offense types because one
  incident can carry several offense types; documented), and
  ``agencies_reporting``.
- **``cleared_except_id`` excluded.** Exceptional clearance is an
  incident-grain attribute (one flag per incident, not per offense), and
  exceptional clearance is not cleared-by-arrest — serving it as an
  offense-grain count would misstate both. A companion clearance metric can
  ship in a future minor version if wanted.
- **No §4b masks.** Every metric is derived by counting rows, so impossible
  values (negative/fractional counts) cannot occur; there is no suppression
  in NIBRS master extracts (``suppressed_to_null=False``).
- **Dedup tie-break.** One zip per data year and single-pass aggregation per
  zip make duplicate natural keys impossible by construction;
  ``deduplicate_by_levels(sort_col="offense_count")`` remains as the
  documented safety net (prefer the fuller row) should a future refresh add
  overlapping files. The collision guard runs first and hard-fails on any
  divergent duplicate rather than letting dedup pick a winner.
"""

import logging
from pathlib import Path

import polars as pl

from src.etl.criminal_justice.fbi_cde._nibrs_shared import (
    COVERAGE_FULL,
    COVERAGE_PARTIAL,
    FULL_PARTICIPATION_START_YEAR,
    GROUP_A_OFFENSE_VOCAB,
    assert_data_year,
    load_agencies,
    load_incidents,
    load_ori_county_crosswalk,
    nibrs_zip_paths,
    read_member_csv,
    require_columns,
)
from src.utils.metadata import write_data_dictionary
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

TOPIC = "nibrs_offenses"
BRONZE_DIR = Path("data/bronze/criminal_justice/fbi_cde/nibrs_offenses")
GOLD_DIR = Path("data/gold/criminal_justice/nibrs_offenses")
SOURCE_URL = "https://cde.ucr.cjis.gov"

SRS_SIDECAR = BRONZE_DIR / "srs_estimates" / "estimated_crimes_1979_2024.csv"

# Coverage flag for Georgia's Oct-2019 SRS -> NIBRS transition — the values
# and boundary year live in _nibrs_shared so the nibrs_arrests sibling can
# never drift from them. Not an era-detection year range (file formats are
# detected by column signature below).
COVERAGE_VALUES = [COVERAGE_FULL, COVERAGE_PARTIAL]

# Era detection by column signature on the (lowercased) NIBRS_OFFENSE frame.
# Era 1 (2018-2020) joins the offense-type lookup on the surrogate
# offense_type_id; era 2 (2021-2024) carries offense_code directly. The two
# signatures are mutually exclusive, so ordering is cosmetic.
ERA_SIGNATURES: dict[str, list[str]] = {
    "nibrs_v1_uppercase_id_join": ["offense_type_id"],
    "nibrs_v2_lowercase_code_join": ["offense_code"],
}

# Pinned offense vocabulary: NIBRS offense code -> (offense_type,
# offense_category, crime_against). The Group A vocabulary itself lives in
# _nibrs_shared (GROUP_A_OFFENSE_VOCAB, generated from GA-2024.zip's
# NIBRS_OFFENSE_TYPE lookup) so the nibrs_arrests sibling serves identical
# offense_type values; this topic serves Group A only (the offense segment
# carries no Group B rows — guarded below).
OFFENSE_VOCAB: dict[str, tuple[str, str, str]] = GROUP_A_OFFENSE_VOCAB

OFFENSE_TYPE_MAP: dict[str, str] = {c: v[0] for c, v in OFFENSE_VOCAB.items()}
OFFENSE_CATEGORY_MAP: dict[str, str] = {c: v[1] for c, v in OFFENSE_VOCAB.items()}
CRIME_AGAINST_MAP: dict[str, str] = {c: v[2] for c, v in OFFENSE_VOCAB.items()}
CRIME_AGAINST_VALUES = ["person", "property", "society"]

# Attempted/completed pivot recode for NIBRS attempt_complete_flag.
ATTEMPT_STATUS_MAP: dict[str, str] = {"C": "completed", "A": "attempted"}

METRIC_COLUMNS: list[str] = [
    "offense_count",
    "completed_count",
    "attempted_count",
    "incident_count",
    "agencies_reporting",
]

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "county_fips",
    "coverage",
    "offense_type",
    "offense_category",
    "crime_against",
    *METRIC_COLUMNS,
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "county_fips": pl.Utf8,
    "coverage": pl.Utf8,
    "offense_type": pl.Utf8,
    "offense_category": pl.Utf8,
    "crime_against": pl.Utf8,
    **{c: pl.Int64 for c in METRIC_COLUMNS},
    "detail_level": pl.Utf8,
}

# offense_type determines offense_category and crime_against (enforced by an
# authored quality check), and year determines coverage, so these keys
# uniquely identify a row even though the auto-derived contract grain also
# lists the dependent categoricals.
NATURAL_KEYS: list[str] = ["year", "county_fips", "offense_type", "detail_level"]


# =============================================================================
# Per-zip transform
# =============================================================================


def _load_offenses(
    zip_path: Path, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Load NIBRS_OFFENSE for one zip with a canonical offense_code column.

    Era 1 recovers offense_code by joining the SAME zip's NIBRS_OFFENSE_TYPE
    lookup on the surrogate offense_type_id (the id spaces are per-extract, so
    a cross-year lookup would be wrong); era 2 carries offense_code natively.
    The offense member is the topic's bronze row concept — recorded as the
    zip's file entry and bronze count.
    """
    offenses, loss = read_member_csv(zip_path, "NIBRS_OFFENSE.csv")
    manifest.record_read_loss(
        year,
        f"{zip_path.name}:NIBRS_OFFENSE.csv",
        loss["raw_rows"],
        loss["parsed_rows"],
    )

    era = detect_era_by_columns(offenses, ERA_SIGNATURES)
    if era is None:
        raise ValueError(
            f"{zip_path.name}: no era signature matched {offenses.columns}"
        )
    manifest.record_file(zip_path, year, era, offenses.height, offenses.columns)
    manifest.record_bronze(year, offenses.height)

    require_columns(
        offenses,
        ["data_year", "incident_id", "attempt_complete_flag"],
        f"{zip_path.name}:NIBRS_OFFENSE",
    )
    assert_data_year(offenses, year, f"{zip_path.name}:NIBRS_OFFENSE")

    if era == "nibrs_v1_uppercase_id_join":
        lookup, lk_loss = read_member_csv(zip_path, "NIBRS_OFFENSE_TYPE.csv")
        manifest.record_read_loss(
            year,
            f"{zip_path.name}:NIBRS_OFFENSE_TYPE.csv",
            lk_loss["raw_rows"],
            lk_loss["parsed_rows"],
        )
        require_columns(
            lookup,
            ["offense_type_id", "offense_code"],
            f"{zip_path.name}:NIBRS_OFFENSE_TYPE",
        )
        offenses = offenses.join(
            lookup.select("offense_type_id", "offense_code"),
            on="offense_type_id",
            how="left",
        )
    null_codes = offenses["offense_code"].null_count()
    if null_codes:
        raise ValueError(
            f"{zip_path.name}: {null_codes} offense rows resolved no offense_code"
        )
    return offenses.select("incident_id", "offense_code", "attempt_complete_flag")


def _attach_county(
    offenses: pl.DataFrame,
    zip_path: Path,
    year: int,
    crosswalk: pl.DataFrame,
    manifest: TransformManifest,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Join offenses -> incident -> agency ORI -> primary county.

    Returns (offense rows with ori/county_fips, per-county reporting-agency
    roster counts). Every offense must resolve an ORI, and every ORI must
    exist in the crosswalk — anything unmatched hard-fails (never silently
    NULLed). NULL county_fips after a successful crosswalk match marks a
    statewide agency (rolls up to the state row only).
    """
    incidents, inc_loss = load_incidents(zip_path)
    manifest.record_read_loss(
        year,
        f"{zip_path.name}:NIBRS_incident.csv",
        inc_loss["raw_rows"],
        inc_loss["parsed_rows"],
    )
    assert_data_year(incidents, year, f"{zip_path.name}:NIBRS_incident")

    agencies, ag_loss = load_agencies(zip_path)
    manifest.record_read_loss(
        year,
        f"{zip_path.name}:agencies.csv",
        ag_loss["raw_rows"],
        ag_loss["parsed_rows"],
    )
    assert_data_year(agencies, year, f"{zip_path.name}:agencies")
    # GA-2018 publishes 12 exact-duplicate roster rows (49 rows, 37 distinct
    # agencies); load_agencies drops full-row duplicates so the roster join
    # cannot fan out fact rows. Record the drop as manifest provenance.
    dup_roster = int(ag_loss["parsed_rows"]) - agencies.height
    if dup_roster:
        manifest.record_filtered(
            year, dup_roster, "exact_duplicate_agency_roster_rows_dropped"
        )

    unmatched_oris = agencies.join(crosswalk, on="ori", how="anti")
    if unmatched_oris.height:
        raise ValueError(
            f"{zip_path.name}: ORIs missing from ori_to_county crosswalk — "
            f"rebuild the crosswalk: {unmatched_oris['ori'].to_list()}"
        )

    offenses = (
        offenses.join(
            incidents.select("incident_id", "agency_id"), on="incident_id", how="left"
        )
        .join(agencies.select("agency_id", "ori"), on="agency_id", how="left")
        .join(crosswalk.select("ori", "county_fips"), on="ori", how="left")
    )
    if offenses["ori"].null_count():
        raise ValueError(
            f"{zip_path.name}: offense rows failed the incident->agency join "
            f"({offenses['ori'].null_count()} rows with no ORI)"
        )
    statewide = offenses.filter(pl.col("county_fips").is_null())
    if statewide.height:
        # Statewide agencies (GBI, State Patrol, ...) have no primary county:
        # their offenses roll up to the state row only. Zero such rows exist
        # in 2018-2024; log loudly if that ever changes.
        logger.warning(
            "Year %d: %d offense rows from statewide (no-county) agencies %s "
            "count toward state rows only",
            year,
            statewide.height,
            statewide["ori"].unique().sort().to_list(),
        )

    # Coverage roster: agencies that reported NIBRS data this year, counted
    # per primary county (statewide agencies counted in the state total only).
    agency_geo = agencies.join(
        crosswalk.select("ori", "county_fips"), on="ori", how="left"
    )
    roster = (
        agency_geo.filter(pl.col("county_fips").is_not_null())
        .group_by("county_fips")
        .agg(pl.len().cast(pl.Int64).alias("agencies_reporting"))
        .with_columns(pl.lit(agencies.height, dtype=pl.Int64).alias("_state_agencies"))
    )

    # Manifest: the ORI -> primary-county attribution is the topic's
    # geography recode; record the slice actually observed on offense rows.
    ori_map = {
        row["ori"]: (row["county_fips"] or "unassigned_statewide")
        for row in offenses.select("ori", "county_fips").unique().to_dicts()
    }
    manifest.record_categorical(
        column="county_fips",
        map_dict=ori_map,
        bronze_series=offenses["ori"],
        gold_series=offenses["county_fips"],
    )
    multi = agency_geo.join(
        crosswalk.filter(pl.col("multi_county")).select("ori"), on="ori", how="semi"
    )
    if multi.height:
        logger.info(
            "Year %d: %d reporting agencies span multiple counties; each is "
            "attributed wholly to its primary county",
            year,
            multi.height,
        )
    return offenses, roster


def _map_offense_vocabulary(
    offenses: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Map offense codes through the pinned 2024 vocabulary (Group A only).

    Non-Group-A codes (Group B 90A-90M are arrest-only; 90I Runaway is "Not a
    Crime") should never appear in NIBRS_OFFENSE — if one does, it is
    filtered with a recorded count; a code UNKNOWN to the 2024 lookup
    hard-fails (a new NIBRS code requires a vocabulary decision, not a guess).
    """
    # Non-Group-A codes are all 90-prefixed (Group B 90A-90M, Runaway 90I);
    # every Group A code lives in the pinned vocabulary, so the predicate
    # cleanly separates "known non-Group-A" from "unknown new code".
    non_group_a = pl.col("offense_code").str.starts_with("90") & ~pl.col(
        "offense_code"
    ).is_in(list(OFFENSE_VOCAB))
    known_non_group_a = offenses.filter(non_group_a)
    if known_non_group_a.height:
        logger.warning(
            "Year %d: filtered %d non-Group-A offense rows (codes %s) — "
            "Group B / Runaway rows do not belong in the offense segment",
            year,
            known_non_group_a.height,
            known_non_group_a["offense_code"].unique().sort().to_list(),
        )
        manifest.record_filtered(
            year, known_non_group_a.height, "non_group_a_offense_code"
        )
        offenses = offenses.filter(~non_group_a)

    unknown = offenses.filter(~pl.col("offense_code").is_in(list(OFFENSE_VOCAB)))
    if unknown.height:
        raise ValueError(
            f"Year {year}: offense codes missing from the pinned 2024 "
            f"vocabulary: {unknown['offense_code'].unique().sort().to_list()}"
        )

    offenses = offenses.with_columns(
        pl.col("offense_code").replace_strict(OFFENSE_TYPE_MAP).alias("offense_type"),
        pl.col("offense_code")
        .replace_strict(OFFENSE_CATEGORY_MAP)
        .alias("offense_category"),
        pl.col("offense_code").replace_strict(CRIME_AGAINST_MAP).alias("crime_against"),
        pl.col("attempt_complete_flag")
        .replace_strict(ATTEMPT_STATUS_MAP)
        .alias("attempt_status"),
    )
    for col, map_dict in [
        ("offense_type", OFFENSE_TYPE_MAP),
        ("offense_category", OFFENSE_CATEGORY_MAP),
        ("crime_against", CRIME_AGAINST_MAP),
    ]:
        manifest.record_categorical(
            column=col,
            map_dict=map_dict,
            bronze_series=offenses["offense_code"],
            gold_series=offenses[col],
        )
    manifest.record_categorical(
        column="attempt_status",
        map_dict=ATTEMPT_STATUS_MAP,
        bronze_series=offenses["attempt_complete_flag"],
        gold_series=offenses["attempt_status"],
    )
    return offenses


def _aggregate(offenses: pl.DataFrame, roster: pl.DataFrame, year: int) -> pl.DataFrame:
    """Aggregate offense rows to county and state grain for one year.

    County rows count offenses from agencies attributed to that (primary)
    county; the state row counts ALL offenses including statewide agencies,
    so state >= sum(counties) structurally (equal in 2018-2024).
    incident_count is n_unique(incident_id) within the cell — additive across
    counties (an incident belongs to one agency), NOT across offense types.
    """
    group_cols = ["offense_type", "offense_category", "crime_against"]
    aggs = [
        pl.len().cast(pl.Int64).alias("offense_count"),
        (pl.col("attempt_status") == "completed")
        .sum()
        .cast(pl.Int64)
        .alias("completed_count"),
        (pl.col("attempt_status") == "attempted")
        .sum()
        .cast(pl.Int64)
        .alias("attempted_count"),
        pl.col("incident_id").n_unique().cast(pl.Int64).alias("incident_count"),
    ]
    county = (
        offenses.filter(pl.col("county_fips").is_not_null())
        .group_by(["county_fips", *group_cols])
        .agg(aggs)
        .join(
            roster.select("county_fips", "agencies_reporting"),
            on="county_fips",
            how="left",
        )
        .with_columns(pl.lit("county").alias("detail_level"))
    )
    if county["agencies_reporting"].null_count():
        raise ValueError(
            f"Year {year}: county rows without a reporting-agency roster count"
        )
    state_agencies = int(roster["_state_agencies"][0]) if roster.height else 0
    state = (
        offenses.group_by(group_cols)
        .agg(aggs)
        .with_columns(
            pl.lit(None).cast(pl.Utf8).alias("county_fips"),
            pl.lit(state_agencies, dtype=pl.Int64).alias("agencies_reporting"),
            pl.lit("state").alias("detail_level"),
        )
    )
    coverage = (
        COVERAGE_PARTIAL if year < FULL_PARTICIPATION_START_YEAR else COVERAGE_FULL
    )
    return pl.concat(
        [county, state.select(county.columns)], how="vertical"
    ).with_columns(
        pl.lit(year, dtype=pl.Int32).alias("year"),
        pl.lit(coverage).alias("coverage"),
    )


def transform_zip(
    zip_path: Path,
    year: int,
    crosswalk: pl.DataFrame,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Transform one GA-{year}.zip into county + state offense-count rows.

    Processes one year at a time (segment frames are dropped after the
    aggregation) so all seven years never sit in memory together.
    """
    offenses = _load_offenses(zip_path, year, manifest)
    offenses, roster = _attach_county(offenses, zip_path, year, crosswalk, manifest)
    offenses = _map_offense_vocabulary(offenses, year, manifest)
    result = _aggregate(offenses, roster, year)
    logger.info(
        "Year %d: %d offense rows -> %d gold rows (%d county, %d state)",
        year,
        offenses.height,
        result.height,
        result.filter(pl.col("detail_level") == "county").height,
        result.filter(pl.col("detail_level") == "state").height,
    )
    return result


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for nibrs_offenses."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)
    crosswalk = load_ori_county_crosswalk()

    # 1. Record the SRS estimates sidecar as deliberately excluded: estimated
    # SRS index-crime state series (1979-2024) on an incompatible category
    # vocabulary — never spliced with unestimated NIBRS counts (domain rule:
    # version methodological breaks, never pool across them).
    manifest.record_file(SRS_SIDECAR, 2024, "srs_estimates_EXCLUDED", 0, [])
    logger.warning(
        "EXCLUDED %s: state-grain ESTIMATED SRS index-crime series; its "
        "hierarchy-ruled categories do not align with NIBRS offense "
        "categories and must not be pooled with unestimated NIBRS counts "
        "(ship as its own topic if wanted)",
        SRS_SIDECAR.name,
    )

    # 2. Read + transform each year's zip (memory-conscious: one at a time).
    frames: list[pl.DataFrame] = []
    for year, zip_path in nibrs_zip_paths(BRONZE_DIR):
        frames.append(transform_zip(zip_path, year, crosswalk, manifest))
    if not frames:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 3. Harmonize + concat, then record the year-derived coverage recode.
    combined = pl.concat(harmonize_columns(frames, STANDARD_COLUMNS, TARGET_TYPES))
    year_strs = combined["year"].cast(pl.Utf8)
    manifest.record_categorical(
        column="coverage",
        map_dict={
            str(y): (
                COVERAGE_PARTIAL if y < FULL_PARTICIPATION_START_YEAR else COVERAGE_FULL
            )
            for y in combined["year"].unique().to_list()
        },
        bronze_series=year_strs,
        gold_series=combined["coverage"],
    )
    logger.info("Combined %d gold-shaped rows", combined.height)

    # 4. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean an aggregation/join bug and must raise, not be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: one zip per data year + single-pass per-zip aggregation make
    # duplicate keys impossible by construction; sort_col "offense_count" is
    # the documented safety net (prefer the fuller row) should a future
    # refresh introduce overlapping files.
    combined = deduplicate_by_levels(
        combined,
        {
            "county": ["year", "county_fips", "offense_type"],
            "state": ["year", "offense_type"],
        },
        sort_col="offense_count",
    )

    # 5. Geography nulling (shared domain rules; state rows already NULL).
    # No §4b masks apply: every metric is a derived row count, so impossible
    # values cannot occur (see module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=CRIMINAL_JUSTICE_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. Metrics are never NULL by construction, so any
    # null-rate spike is a hard bug worth surfacing.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(
        combined,
        required_non_null=["year", "coverage", "offense_type", "detail_level"],
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
        "Done. Bronze offense rows: %s; gold rows: %s; years: %s",
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
            "Reported criminal offenses in Georgia from the FBI's National "
            "Incident-Based Reporting System (NIBRS), aggregated from "
            "incident-level master extracts to county x year x offense type "
            "(all 52 observed NIBRS Group A offense codes, with the FBI's "
            "offense category and crime-against class), plus a statewide "
            "rollup. Counts are raw agency reports — unestimated and "
            "unadjusted for non-reporting agencies. Georgia transitioned "
            "from SRS summary reporting to NIBRS around October 2019: "
            "2018-2019 cover early-adopter agencies only (37 and 276 "
            "agencies vs 401-455 from 2020 on), so every row carries a "
            "coverage flag and an agencies_reporting companion count — "
            "year-over-year change across the transition reflects adoption, "
            "not crime. Offenses are attributed to the reporting agency's "
            "primary county via the ORI-to-county crosswalk."
        ),
        title="NIBRS Reported Offenses by County",
        summary=(
            "Criminal offenses reported by Georgia law-enforcement agencies "
            "(FBI NIBRS), by county, year, and offense type, 2018 onward."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": "Calendar year the incidents occurred (data year).",
            },
            {
                "name": "county_fips",
                "type": "string",
                "example": "13121",
                "null_meaning": "NULL on statewide rollup rows.",
                "description": (
                    "5-digit county FIPS code (state prefix 13) of the "
                    "reporting agency's primary county; FK to the counties "
                    "dimension. NULL on statewide rollup rows. Agencies "
                    "spanning multiple counties (27 of 434 in 2024) are "
                    "attributed wholly to their primary county; statewide "
                    "agencies with no primary county (GBI, State Patrol) "
                    "count toward state rows only (none reported incidents "
                    "in 2018-2024)."
                ),
            },
            {
                "name": "coverage",
                "type": "string",
                "nullable": False,
                "validValues": COVERAGE_VALUES,
                "example": COVERAGE_FULL,
                "short_description": (
                    "NIBRS adoption phase: partial_adoption (2018-2019 "
                    "early-adopter agencies only) or full_participation "
                    "(2020 onward)."
                ),
                "description": (
                    "Methodology coverage flag for Georgia's SRS-to-NIBRS "
                    "transition (completed around October 2019). "
                    "'partial_adoption' (2018-2019): only early-adopter "
                    "agencies reported (37 in 2018, 276 in 2019) — these "
                    "years are NOT comparable to later years as a state "
                    "series. 'full_participation' (2020 onward): statewide "
                    "NIBRS reporting, though the agency roster still varies "
                    "by year (401-455 agencies) — use agencies_reporting to "
                    "separate crime change from participation change."
                ),
            },
            {
                "name": "offense_type",
                "type": "string",
                "nullable": False,
                "example": "aggravated_assault",
                "short_description": (
                    "NIBRS Group A offense type (e.g. aggravated_assault, "
                    "burglary_breaking_entering, shoplifting)."
                ),
                "description": (
                    "NIBRS Group A offense type, snake_cased from the FBI "
                    "offense-type lookup pinned to the 2024 vocabulary so "
                    "labels never vary by data year (NIBRS code 11D is "
                    "served under its current name criminal_sexual_contact; "
                    "earlier lookups called it Fondling). Group B offenses "
                    "are arrest-only in NIBRS and do not appear in offense "
                    "data. Sum offense_count over offense types within a "
                    "county-year for an all-offenses total; each offense "
                    "type maps to exactly one offense_category and "
                    "crime_against."
                ),
            },
            {
                "name": "offense_category",
                "type": "string",
                "nullable": False,
                "example": "assault_offenses",
                "short_description": (
                    "FBI offense category grouping related offense types "
                    "(e.g. assault_offenses groups aggravated_assault, "
                    "simple_assault, intimidation)."
                ),
                "description": (
                    "FBI offense category (pinned 2024 vocabulary) grouping "
                    "related offense types — e.g. assault_offenses covers "
                    "aggravated_assault, simple_assault, and intimidation. "
                    "Functionally dependent on offense_type: filter or group "
                    "by it for category-level counts without double "
                    "counting."
                ),
            },
            {
                "name": "crime_against",
                "type": "string",
                "nullable": False,
                "validValues": CRIME_AGAINST_VALUES,
                "example": "person",
                "short_description": (
                    "NIBRS crime-against class: person, property, or society."
                ),
                "description": (
                    "NIBRS crime-against class (person / property / "
                    "society), functionally dependent on offense_type. Note "
                    "it is NOT dependent on offense_category alone — the "
                    "other_offenses category spans property and society "
                    "offense types."
                ),
            },
            {
                "name": "offense_count",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "key_metric": True,
                "example": 1542,
                "short_description": (
                    "Number of reported offenses of this type in the county "
                    "and year (raw NIBRS counts, unestimated)."
                ),
                "description": (
                    "Number of offense reports (NIBRS offense-segment rows) "
                    "of this type submitted by agencies attributed to the "
                    "county in the year. Raw, unestimated agency reports — "
                    "an incident with several offense types contributes one "
                    "offense per type (the FBI's offense-count convention). "
                    "Equals completed_count + attempted_count. Interpret "
                    "across years together with coverage and "
                    "agencies_reporting: the series mixes crime change with "
                    "NIBRS adoption change, especially 2018-2020."
                ),
            },
            {
                "name": "completed_count",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "example": 1490,
                "description": (
                    "Offenses reported as completed (NIBRS "
                    "attempt_complete_flag 'C'). completed_count + "
                    "attempted_count = offense_count."
                ),
            },
            {
                "name": "attempted_count",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "example": 52,
                "description": (
                    "Offenses reported as attempted but not completed "
                    "(NIBRS attempt_complete_flag 'A'). completed_count + "
                    "attempted_count = offense_count."
                ),
            },
            {
                "name": "incident_count",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "example": 1301,
                "short_description": (
                    "Distinct criminal incidents involving at least one "
                    "offense of this type (not additive across offense "
                    "types)."
                ),
                "description": (
                    "Distinct NIBRS incidents involving at least one offense "
                    "of this type in the county and year. Always between 1 "
                    "and offense_count. In the GA extracts an offense type "
                    "appears at most once per incident, so incident_count "
                    "equals offense_count within a row; the column is kept "
                    "for grouped rollups, where the two diverge. Additive "
                    "across counties (an incident belongs to one agency) but "
                    "NOT additive across offense types — one incident can "
                    "involve several offense types and is counted once under "
                    "each; summing incident_count over offense types "
                    "overstates total incidents."
                ),
            },
            {
                "name": "agencies_reporting",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "example": 434,
                "short_description": (
                    "Law-enforcement agencies that reported NIBRS data that "
                    "year (county roster on county rows, statewide roster "
                    "on state rows)."
                ),
                "description": (
                    "Coverage companion: the number of distinct agencies on "
                    "the year's NIBRS reporting roster (the 2018 extract's "
                    "12 exact-duplicate roster rows are deduplicated) — for "
                    "county rows, agencies whose primary county is this "
                    "county; for statewide rows, all reporting agencies (37 "
                    "in 2018, 276 in 2019, 401-455 from 2020). Constant across "
                    "offense types within a county-year (it describes the "
                    "roster, not the offense type). Essential for "
                    "interpreting the adoption ramp: a rising offense count "
                    "alongside a rising agency count reflects coverage, not "
                    "necessarily crime."
                ),
            },
        ],
        source="FBI Crime Data Explorer, NIBRS master state extracts (Georgia)",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        suppressed_to_null=False,
        usage=(
            "Cite the FBI Crime Data Explorer (cde.ucr.cjis.gov), NIBRS "
            "master extracts for Georgia. Counts are raw and unestimated: "
            "never compare across the coverage flag boundary (2018-2019 vs "
            "2020+) without noting the NIBRS adoption ramp, and read county "
            "trends alongside agencies_reporting. Sum offense_count across "
            "offense types freely; never sum incident_count across offense "
            "types. Crime rates require an external population denominator "
            "(not served here)."
        ),
        limitations=(
            "State rows have NULL county_fips. Counts are unestimated raw "
            "agency reports: 2018-2019 cover early-adopter agencies only "
            "(37 / 276 agencies) and are not comparable to 2020+ as a state "
            "series; even full-participation years vary in roster size "
            "(401-455 agencies). Offenses are attributed to the reporting "
            "agency's primary county — agencies spanning multiple counties "
            "are not split, and offenses handled by one county's agency on "
            "another county's behalf follow the agency, not the offense "
            "location. No demographic breakdowns (the NIBRS offense segment "
            "carries none; victim/offender demographics belong to sibling "
            "NIBRS topics). The SRS estimated index-crime series (1979-2024) "
            "is deliberately excluded: it is estimated, hierarchy-ruled "
            "summary data on an incompatible category vocabulary. NIBRS "
            "master extracts have no suppression — a county-year-offense "
            "combination with no reports simply has no row."
        ),
        quality_checks=[
            {
                "name": "completed_plus_attempted_equals_offense_count",
                "description": (
                    "Every offense is flagged completed or attempted, so the "
                    "two partition counts must sum exactly to offense_count "
                    "on every row."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE offense_count IS NOT "
                    "NULL AND completed_count IS NOT NULL AND attempted_count "
                    "IS NOT NULL AND completed_count + attempted_count != "
                    "offense_count"
                ),
                "mustBe": 0,
            },
            {
                "name": "offense_count_at_least_one",
                "description": (
                    "Rows exist only for county-year-offense combinations "
                    "with at least one report — a zero or negative count "
                    "means the aggregation broke."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE offense_count IS "
                    "NULL OR offense_count < 1"
                ),
                "mustBe": 0,
            },
            {
                "name": "incident_count_between_one_and_offense_count",
                "description": (
                    "Each counted incident carries at least one offense of "
                    "the type, and each offense belongs to exactly one "
                    "incident, so 1 <= incident_count <= offense_count."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE incident_count IS "
                    "NULL OR incident_count < 1 OR incident_count > "
                    "offense_count"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_offense_total_covers_county_sum",
                "description": (
                    "The state row counts ALL agencies (including statewide "
                    "agencies with no county), so for every (year, "
                    "offense_type) with county rows a state row must exist "
                    "with offense_count >= the county sum (equal in "
                    "2018-2024; a statewide-agency submission would make it "
                    "strictly greater)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, offense_type, "
                    "MAX(CASE WHEN county_fips IS NULL THEN offense_count "
                    "END) AS state_total, "
                    "SUM(CASE WHEN county_fips IS NOT NULL THEN "
                    "offense_count END) AS county_sum "
                    "FROM {object} GROUP BY year, offense_type"
                    ") WHERE county_sum IS NOT NULL AND (state_total IS NULL "
                    "OR state_total < county_sum)"
                ),
                "mustBe": 0,
            },
            {
                "name": "agencies_reporting_constant_within_year_county",
                "description": (
                    "agencies_reporting describes the year's reporting "
                    "roster for the geography, not the offense type — it "
                    "must be identical on every row of a (year, county) "
                    "group (and on every state row of a year)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, "
                    "COUNT(DISTINCT agencies_reporting) AS n "
                    "FROM {object} GROUP BY year, county_fips"
                    ") WHERE n > 1"
                ),
                "mustBe": 0,
            },
            {
                "name": "agencies_reporting_at_least_one",
                "description": (
                    "Every county row's offenses come from at least one "
                    "agency rostered to that county, and every state row "
                    "from at least one reporting agency."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE agencies_reporting "
                    "IS NULL OR agencies_reporting < 1"
                ),
                "mustBe": 0,
            },
            {
                "name": "coverage_matches_transition_year",
                "description": (
                    "The coverage flag versions Georgia's Oct-2019 SRS-to-"
                    "NIBRS transition: partial_adoption before 2020, "
                    "full_participation from 2020 on — a mismatch means the "
                    "methodological break is mislabeled."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(year < 2020 AND coverage != 'partial_adoption') OR "
                    "(year >= 2020 AND coverage != 'full_participation')"
                ),
                "mustBe": 0,
            },
            {
                "name": "offense_type_determines_category_and_crime_against",
                "description": (
                    "offense_category and crime_against are denormalized "
                    "attributes of offense_type (pinned 2024 vocabulary) — "
                    "each offense_type must map to exactly one value of "
                    "each, or category rollups would double count."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT offense_type, "
                    "COUNT(DISTINCT offense_category) AS nc, "
                    "COUNT(DISTINCT crime_against) AS na "
                    "FROM {object} GROUP BY offense_type"
                    ") WHERE nc > 1 OR na > 1"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
