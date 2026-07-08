"""Transform bronze FBI NIBRS master zips into a gold arrest-count fact table.

Source: FBI Crime Data Explorer NIBRS master state extracts for Georgia
(GA-2018.zip ... GA-2024.zip) — the same relational archives as the sibling
``nibrs_offenses`` topic (**shared bronze**: the zips live once under
``data/bronze/criminal_justice/fbi_cde/nibrs_offenses/``; this topic's bronze
dir holds only a pointer ``_provenance.md``). This topic serves the ARRESTEE
side: ``NIBRS_ARRESTEE.csv`` (incident-linked arrests, all 7 years) and
``NIBRS_ARRESTEE_GROUPB.csv`` (standalone Group B arrest reports, 2022-2024
only), aggregated to county x year x offense type x arrest type x demographic.
Zip/member mechanics and the pinned Group A offense vocabulary are shared via
``src/etl/criminal_justice/fbi_cde/_nibrs_shared.py``.

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Grain: year x county_fips x demographic x reporting_segment x
  offense_type x arrest_type (+ statewide rollup).** One gold row per
  demographic slice of an aggregation cell; ``offense_category``,
  ``crime_against``, and ``offense_group`` ride along as functionally
  dependent attributes of ``offense_type`` (authored check), and ``coverage``
  depends on ``year`` — mirroring the nibrs_offenses conventions so the two
  topics join cleanly on offense_type.
- **Two reporting segments, never blended.** Bronze inspection showed the
  incident-linked file carries Group B offense codes too (538-2,519
  rows/year from 2019 — an arrest attached to a Group A incident may be for
  a Group B offense), while the standalone Group B arrest-report segment
  (~half of all arrests: 94,440 of 190,873 in 2024) only exists 2022+ and has
  NO incident/agency link (confirmed against the zips' postgres_setup.sql) —
  so it can never be placed in a county. Folding the two together would
  fabricate a 2021->2022 jump in every 90x state series. Every row therefore
  carries ``reporting_segment`` (``group_a_incident_linked`` /
  ``group_b_arrest_report``); Group B report rows are state-level only and
  start in 2022 (both authored checks). County trends for Group B offense
  types (DUI, disorderly conduct, ...) reflect only the incident-linked
  slice and vastly understate totals — documented in the contract.
- **Physical arrests, not segments: ``multiple_indicator == 'M'`` rows are
  excluded.** NIBRS Data Element 44 marks one segment C(ount) and the rest
  M(ultiple) when a single arrest clears several incidents; counting M rows
  (683-2,353/year) would double-count the same physical arrest. Recorded via
  ``record_filtered`` per year. The Group B segment has no such column (one
  row per arrest report).
- **Demographics: race and sex as demographic rows; age and ethnicity as
  count partitions.** Race (era-1 ids 0/1/2/3/4/8, era-2 ids
  10/20/30/40/50/98 — the id spaces are re-numbered between eras, so each
  era maps through its own hardcoded lookup verified against that era's
  REF_RACE) and sex (M/F, no unknowns in any year) become ``demographic``
  rows via the shared aliases: all, asian, black, native_american,
  pacific_islander, white, race_unknown, male, female. NIBRS publishes
  SPLIT Asian and Pacific Islander codes (post-1997 OMB; no combined bucket
  appears in any year), so the split keys are correct per §5b. Each category
  partitions the ``all`` row exactly (authored checks). Age and Hispanic
  ethnicity are served as metric partitions of ``arrest_count``
  (juvenile/adult/age_unknown; hispanic/not_hispanic/ethnicity_unknown)
  rather than demographic rows: NIBRS race and ethnicity are separate fields
  (race values are NOT Hispanic-exclusive), and the shared vocabulary
  registers ``hispanic`` in the ``race`` demographic_category, so emitting
  hispanic rows would double-count against the race rows when consumers sum
  the race category (§5a); no juvenile/adult canonical demographic keys
  exist. The count-partition representation preserves the data without
  violating mutual exclusivity — and gives age/ethnicity splits WITHIN each
  race/sex row for free.
- **Age sentinels.** Era 2 encodes unknown age as ``age_num == '00'`` with
  ``age_id == 103`` ("Unknown"; verified equivalent in every era-2 year —
  age 0 is a sentinel, NOT infant arrestees, correcting the structure doc's
  data-entry-artifact hypothesis). Era 1 encodes unknown as NULL ``age_num``
  with ``AGE_ID 4`` (Unknown) or ``AGE_ID 6`` (Over 98 — bucketed adult).
  Any other NULL age hard-fails. Juvenile = under 18 at arrest.
- **County attribution: primary county; statewide agencies to state only.**
  Incident-linked arrests join incident -> agency -> ORI -> the
  ori_to_county crosswalk; multi-county agencies are attributed wholly to
  their PRIMARY county, and statewide agencies (NULL crosswalk county) roll
  to state rows only. Unmatched ORIs hard-fail. Mirrors nibrs_offenses,
  including the 2018 duplicate-roster dedup and the per-year
  ``agencies_reporting`` coverage companion metric.
- **Methodology: NIBRS raw counts, unestimated; coverage flag shared with
  the sibling** (partial_adoption 2018-2019, full_participation 2020+ from
  ``_nibrs_shared``), never blended or estimated. ``data_year`` is the fact
  year (Group A arrest dates spill into the next calendar year because
  arrests attach to the incident's year).
- **Excluded bronze attributes** (documented per structure doc): the weapon
  child segments (NIBRS_ARRESTEE_WEAPON / _GROUPB_WEAPON — child grain,
  98%% unarmed), ``resident_code`` (26-34%% missing),
  ``under_18_disposition_code`` (juvenile-only; future juvenile-justice
  topic), ``clearance_ind`` (100%% blank), ``age_id``/``age_range_*``
  (redundant with age_num), and ``arrest_date`` (spills across calendar
  years; data_year is the grain year).
- **No §4b masks.** Every metric is derived by counting rows, so impossible
  values (negative/fractional counts) cannot occur; NIBRS master extracts
  have no suppression (``suppressed_to_null=False``).
- **Dedup tie-break.** One zip per data year and single-pass aggregation per
  zip make duplicate natural keys impossible by construction;
  ``deduplicate_by_levels(sort_col="arrest_count")`` remains as the
  documented safety net (prefer the fuller row) should a future refresh add
  overlapping files. The collision guard runs first and hard-fails on any
  divergent duplicate rather than letting dedup pick a winner.
"""

import logging
import zipfile
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
from src.utils.demographics import DEMOGRAPHIC_ALIASES, normalize_demographic_column
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

TOPIC = "nibrs_arrests"
# Shared bronze: the GA-{year}.zip archives live once under the sibling
# nibrs_offenses topic (this topic's own bronze dir holds only _provenance.md).
BRONZE_DIR = Path("data/bronze/criminal_justice/fbi_cde/nibrs_offenses")
GOLD_DIR = Path("data/gold/criminal_justice/nibrs_arrests")
SOURCE_URL = "https://cde.ucr.cjis.gov"

COVERAGE_VALUES = [COVERAGE_FULL, COVERAGE_PARTIAL]

# Era detection by column signature on the (lowercased) arrestee frame.
# Era 1 (2018-2020) carries the surrogate offense_type_id (joined to the SAME
# zip's NIBRS_OFFENSE_TYPE lookup to recover offense_code); era 2 (2021-2024)
# carries offense_code directly. The code-id systems for race/ethnicity/age
# were renumbered along with the column rename, so the era also selects the
# demographic recode maps below.
ERA_SIGNATURES: dict[str, list[str]] = {
    "nibrs_v1_uppercase_id_join": ["offense_type_id"],
    "nibrs_v2_lowercase_code_join": ["offense_code"],
}
ERA_V1 = "nibrs_v1_uppercase_id_join"
ERA_V2 = "nibrs_v2_lowercase_code_join"

# The two NIBRS arrest reporting paths — versioned as a grain categorical
# because the standalone Group B arrest-report segment only exists 2022+ and
# has no agency link (state rows only); folding it into the incident-linked
# series would fabricate a 2021->2022 jump for every Group B offense type.
SEGMENT_LINKED = "group_a_incident_linked"
SEGMENT_GROUPB = "group_b_arrest_report"
GROUPB_SEGMENT_START_YEAR = 2022

# Group B offense vocabulary: code -> (offense_type, offense_category,
# crime_against), generated from GA-2024.zip's NIBRS_OFFENSE_TYPE lookup
# (same pinned-2024 convention as the shared Group A vocabulary). Group B
# codes are arrest-only in NIBRS: they appear here (both segments) but never
# in the sibling nibrs_offenses topic. 90I Runaway is grouped by the FBI as
# neither A nor B ("Not a Crime"); it appears in the data (2 rows, 2020).
GROUP_B_OFFENSE_VOCAB: dict[str, tuple[str, str, str]] = {
    "90A": ("bad_checks", "bad_checks", "property"),
    "90B": (
        "curfew_loitering_vagrancy_violations",
        "curfew_loitering_vagrancy_violations",
        "society",
    ),
    "90C": ("disorderly_conduct", "disorderly_conduct", "society"),
    "90D": ("driving_under_the_influence", "driving_under_the_influence", "society"),
    "90E": ("drunkenness", "drunkenness", "society"),
    "90F": ("family_offenses_nonviolent", "family_offenses_nonviolent", "person"),
    "90G": ("liquor_law_violations", "liquor_law_violations", "society"),
    "90H": ("peeping_tom", "peeping_tom", "person"),
    "90I": ("runaway", "other_offenses", "not_a_crime"),
    "90J": ("trespass_of_real_property", "trespass_of_real_property", "society"),
    "90K": ("failure_to_appear", "other_offenses", "society"),
    "90L": ("federal_resource_violations", "other_offenses", "society"),
    "90M": ("perjury", "other_offenses", "society"),
    "90Z": ("all_other_offenses", "all_other_offenses", "society"),
}

# Arrests can be for any Group A or Group B offense, so the arrest vocabulary
# is the union of the shared Group A vocabulary and the Group B one above.
OFFENSE_VOCAB: dict[str, tuple[str, str, str]] = {
    **GROUP_A_OFFENSE_VOCAB,
    **GROUP_B_OFFENSE_VOCAB,
}
OFFENSE_TYPE_MAP: dict[str, str] = {c: v[0] for c, v in OFFENSE_VOCAB.items()}
OFFENSE_CATEGORY_MAP: dict[str, str] = {c: v[1] for c, v in OFFENSE_VOCAB.items()}
CRIME_AGAINST_MAP: dict[str, str] = {c: v[2] for c, v in OFFENSE_VOCAB.items()}
CRIME_AGAINST_VALUES = ["not_a_crime", "person", "property", "society"]
# offense_group is the FBI's A/B taxonomy, dependent on the code: Group B
# codes (90x) are arrest-only offenses; 90I Runaway is grouped as neither
# ("Not a Crime" per the FBI lookup, offense_group blank).
OFFENSE_GROUP_MAP: dict[str, str] = {
    **{c: "group_a" for c in GROUP_A_OFFENSE_VOCAB},
    **{c: "group_b" for c in GROUP_B_OFFENSE_VOCAB},
    "90I": "not_a_crime",
}
OFFENSE_GROUP_VALUES = ["group_a", "group_b", "not_a_crime"]

# NIBRS arrest type (Data Element 42) — ids stable across both eras
# (verified against NIBRS_ARREST_TYPE.csv in 2018-2024).
ARREST_TYPE_MAP: dict[str, str] = {
    "1": "on_view",
    "2": "summoned_cited",
    "3": "taken_into_custody",
}
ARREST_TYPE_VALUES = sorted(set(ARREST_TYPE_MAP.values()))

# Race id -> raw label (fed to the shared demographic aliases). The id
# spaces were RENUMBERED between eras (e.g. Black = 2 in era 1 but 20 in
# era 2; 98 = Multiple in era 1 but Unknown in era 2), so each era maps
# through its own lookup — verified against each era's REF_RACE.csv. NIBRS
# publishes split Asian / Pacific Islander codes (post-1997 OMB); any code
# outside the map (e.g. Multiple, Not Specified — never observed in GA
# 2018-2024) hard-fails via replace_strict rather than guessing.
ERA1_RACE_LABELS: dict[str, str] = {
    "0": "UNKNOWN",
    "1": "WHITE",
    "2": "BLACK",
    "3": "AMERICAN INDIAN",
    "4": "ASIAN",
    "8": "PACIFIC ISLANDER",
}
ERA2_RACE_LABELS: dict[str, str] = {
    "10": "WHITE",
    "20": "BLACK",
    "30": "AMERICAN INDIAN",
    "40": "ASIAN",
    "50": "PACIFIC ISLANDER",
    "98": "UNKNOWN",
}

# Sex code -> raw label (no unknown code appears in any year; a new code
# hard-fails via replace_strict).
SEX_LABELS: dict[str, str] = {"M": "MALE", "F": "FEMALE"}

# Ethnicity id -> partition bucket, per era (NIBRS_ETHNICITY.csv renumbered
# ids between eras). Era 1 encodes unreported ethnicity as NULL (filled to
# the literal 'unreported' before mapping); era 2 uses 50 = Not Specified.
# Unknown / Not Specified / unreported all land in ethnicity_unknown.
ETHNICITY_UNREPORTED = "unreported"
ERA1_ETHNICITY_MAP: dict[str, str] = {
    "1": "hispanic",
    "2": "not_hispanic",
    "3": "ethnicity_unknown",
    ETHNICITY_UNREPORTED: "ethnicity_unknown",
}
ERA2_ETHNICITY_MAP: dict[str, str] = {
    "10": "hispanic",
    "20": "not_hispanic",
    "40": "ethnicity_unknown",
    "50": "ethnicity_unknown",
}

# Age-bucket boundary: NIBRS reports age at arrest; under 18 = juvenile.
JUVENILE_AGE_LIMIT = 18
# Era-2 unknown-age sentinel: age_num '00' <=> age_id 103 'Unknown'
# (verified equivalent in every era-2 year; era 1 never publishes '00').
AGE_UNKNOWN_SENTINEL = "00"
# Era-1 special AGE_ID codes carrying NULL age_num.
ERA1_AGE_ID_UNKNOWN = "4"  # 'Unknown'
ERA1_AGE_ID_OVER_98 = "6"  # 'Over 98' — an adult with unpublished age

METRIC_COLUMNS: list[str] = [
    "arrest_count",
    "juvenile_count",
    "adult_count",
    "age_unknown_count",
    "hispanic_count",
    "not_hispanic_count",
    "ethnicity_unknown_count",
    "agencies_reporting",
]

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "county_fips",
    "demographic",
    "coverage",
    "reporting_segment",
    "offense_type",
    "offense_category",
    "crime_against",
    "offense_group",
    "arrest_type",
    *METRIC_COLUMNS,
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "county_fips": pl.Utf8,
    "demographic": pl.Utf8,
    "coverage": pl.Utf8,
    "reporting_segment": pl.Utf8,
    "offense_type": pl.Utf8,
    "offense_category": pl.Utf8,
    "crime_against": pl.Utf8,
    "offense_group": pl.Utf8,
    "arrest_type": pl.Utf8,
    **{c: pl.Int64 for c in METRIC_COLUMNS},
    "detail_level": pl.Utf8,
}

# offense_type determines offense_category / crime_against / offense_group
# (authored check) and year determines coverage, so these keys uniquely
# identify a row even though the auto-derived contract grain also lists the
# dependent categoricals.
NATURAL_KEYS: list[str] = [
    "year",
    "county_fips",
    "demographic",
    "reporting_segment",
    "offense_type",
    "arrest_type",
    "detail_level",
]

DEMOGRAPHIC_VALUES: list[str] = [
    "all",
    "asian",
    "black",
    "female",
    "male",
    "native_american",
    "pacific_islander",
    "race_unknown",
    "white",
]

# Arrestee-level working columns every segment frame is reduced to before
# recode/aggregation (plus the era-specific inputs consumed by _recode).
_SEGMENT_COLUMNS = [
    "county_fips",
    "offense_code",
    "arrest_type_id",
    "race_id",
    "sex_code",
    "ethnicity_id",
    "age_id",
    "age_num",
]


# =============================================================================
# Per-zip loading
# =============================================================================


def _member_exists(zip_path: Path, basename: str) -> bool:
    """True when the zip has exactly one member with this basename."""
    with zipfile.ZipFile(zip_path) as zf:
        matches = [
            n for n in zf.namelist() if n.rsplit("/", 1)[-1].lower() == basename.lower()
        ]
    return len(matches) == 1


def _load_linked_arrestees(
    zip_path: Path, year: int, manifest: TransformManifest
) -> tuple[pl.DataFrame, str]:
    """Load the incident-linked arrestee segment with a canonical offense_code.

    Era 1 recovers offense_code by joining the SAME zip's NIBRS_OFFENSE_TYPE
    lookup on the surrogate offense_type_id (the id spaces are per-extract);
    era 2 carries offense_code natively. Excludes 'M' multiple-indicator
    segments (duplicate segments of one physical arrest that cleared several
    incidents — NIBRS DE-44) with a recorded filter count.
    """
    arrestees, loss = read_member_csv(zip_path, "NIBRS_ARRESTEE.csv")
    manifest.record_read_loss(
        year,
        f"{zip_path.name}:NIBRS_ARRESTEE.csv",
        loss["raw_rows"],
        loss["parsed_rows"],
    )

    era = detect_era_by_columns(arrestees, ERA_SIGNATURES)
    if era is None:
        raise ValueError(
            f"{zip_path.name}: no era signature matched {arrestees.columns}"
        )
    manifest.record_file(zip_path, year, era, arrestees.height, arrestees.columns)
    # Bronze row concept: raw arrestee segments as published (pre-filter), so
    # the manifest counts reconcile with the structure doc's member row counts
    # and record_filtered explains the M-segment exclusion below.
    manifest.record_bronze(year, arrestees.height)

    require_columns(
        arrestees,
        [
            "data_year",
            "incident_id",
            "arrest_type_id",
            "multiple_indicator",
            "age_id",
            "age_num",
            "sex_code",
            "race_id",
            "ethnicity_id",
        ],
        f"{zip_path.name}:NIBRS_ARRESTEE",
    )
    assert_data_year(arrestees, year, f"{zip_path.name}:NIBRS_ARRESTEE")

    # One physical arrest clearing several incidents publishes one 'C' (Count)
    # segment plus duplicate 'M' (Multiple) segments — counting M rows would
    # double-count the same arrest (683-2,353 rows/year).
    m_rows = arrestees.filter(pl.col("multiple_indicator") == "M").height
    if m_rows:
        logger.info(
            "Year %d: excluding %d 'M' multiple-indicator segments "
            "(duplicate segments of one arrest clearing several incidents)",
            year,
            m_rows,
        )
        manifest.record_filtered(
            year, m_rows, "multiple_indicator_M_duplicate_arrest_segments"
        )
        arrestees = arrestees.filter(pl.col("multiple_indicator") != "M")

    if era == ERA_V1:
        # Era-1 lookup join must use the SAME zip's NIBRS_OFFENSE_TYPE — the
        # surrogate offense_type_id space is per-extract.
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
        arrestees = arrestees.join(
            lookup.select("offense_type_id", "offense_code"),
            on="offense_type_id",
            how="left",
        )
    null_codes = arrestees["offense_code"].null_count()
    if null_codes:
        raise ValueError(
            f"{zip_path.name}: {null_codes} arrestee rows resolved no offense_code"
        )
    return (
        arrestees.select(
            "incident_id", *[c for c in _SEGMENT_COLUMNS if c != "county_fips"]
        ),
        era,
    )


def _load_groupb_arrestees(
    zip_path: Path, year: int, manifest: TransformManifest
) -> pl.DataFrame | None:
    """Load the standalone Group B arrest-report segment (2022+ only).

    The member has no incident/agency link at all (confirmed against the
    zips' postgres_setup.sql), so county_fips is NULL by construction — these
    arrests can only feed state rows. Absent before 2022 (returns None);
    missing in a 2022+ zip hard-fails.
    """
    if not _member_exists(zip_path, "NIBRS_ARRESTEE_GROUPB.csv"):
        if year >= GROUPB_SEGMENT_START_YEAR:
            raise ValueError(
                f"{zip_path.name}: NIBRS_ARRESTEE_GROUPB.csv expected from "
                f"{GROUPB_SEGMENT_START_YEAR} on but not found"
            )
        return None

    groupb, loss = read_member_csv(zip_path, "NIBRS_ARRESTEE_GROUPB.csv")
    manifest.record_read_loss(
        year,
        f"{zip_path.name}:NIBRS_ARRESTEE_GROUPB.csv",
        loss["raw_rows"],
        loss["parsed_rows"],
    )
    era = detect_era_by_columns(groupb, ERA_SIGNATURES)
    if era != ERA_V2:
        # The segment only exists in era-2 years; anything else means the
        # extract layout changed and the recode maps must be re-verified.
        raise ValueError(f"{zip_path.name}: Group B segment matched era {era!r}")
    manifest.record_file(zip_path, year, f"{era}_groupb", groupb.height, groupb.columns)
    manifest.record_bronze(year, groupb.height)

    require_columns(
        groupb,
        [
            "data_year",
            "offense_code",
            "arrest_type_id",
            "age_id",
            "age_num",
            "sex_code",
            "race_id",
            "ethnicity_id",
        ],
        f"{zip_path.name}:NIBRS_ARRESTEE_GROUPB",
    )
    assert_data_year(groupb, year, f"{zip_path.name}:NIBRS_ARRESTEE_GROUPB")
    # No agency link exists -> state rows only.
    return groupb.with_columns(pl.lit(None).cast(pl.Utf8).alias("county_fips")).select(
        _SEGMENT_COLUMNS
    )


def _attach_county(
    linked: pl.DataFrame,
    zip_path: Path,
    year: int,
    crosswalk: pl.DataFrame,
    manifest: TransformManifest,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Join incident-linked arrests -> incident -> agency ORI -> primary county.

    Returns (arrest rows with county_fips, per-county reporting-agency roster
    counts). Every arrest must resolve an ORI, and every ORI must exist in
    the crosswalk — anything unmatched hard-fails (never silently NULLed).
    NULL county_fips after a successful crosswalk match marks a statewide
    agency (GBI, State Patrol, ...): those arrests roll up to state rows only.
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

    linked = (
        linked.join(
            incidents.select("incident_id", "agency_id"), on="incident_id", how="left"
        )
        .join(agencies.select("agency_id", "ori"), on="agency_id", how="left")
        .join(crosswalk.select("ori", "county_fips"), on="ori", how="left")
    )
    if linked["ori"].null_count():
        raise ValueError(
            f"{zip_path.name}: arrestee rows failed the incident->agency join "
            f"({linked['ori'].null_count()} rows with no ORI)"
        )
    statewide = linked.filter(pl.col("county_fips").is_null())
    if statewide.height:
        # Statewide agencies have no primary county: their arrests roll up to
        # the state row only (zero such offense rows existed 2018-2024 in the
        # sibling topic; log loudly either way).
        logger.warning(
            "Year %d: %d arrest rows from statewide (no-county) agencies %s "
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
    # geography recode; record the slice actually observed on arrest rows.
    ori_map = {
        row["ori"]: (row["county_fips"] or "unassigned_statewide")
        for row in linked.select("ori", "county_fips").unique().to_dicts()
    }
    manifest.record_categorical(
        column="county_fips",
        map_dict=ori_map,
        bronze_series=linked["ori"],
        gold_series=linked["county_fips"],
    )
    return linked.select(_SEGMENT_COLUMNS), roster


# =============================================================================
# Recodes and demographic expansion
# =============================================================================


def _recode(
    df: pl.DataFrame, era: str, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Recode one segment frame: offense vocabulary, arrest type, race label,
    sex label, ethnicity bucket, and age bucket.

    Every map is era-scoped where the id systems changed (race, ethnicity)
    and applied with replace_strict so an unmapped code hard-fails instead of
    silently NULLing. Age buckets come from age_num with two documented
    sentinel paths: era-2 '00' = Unknown (age_id 103), era-1 NULL age_num
    with AGE_ID 4 (Unknown) or 6 (Over 98 -> adult).
    """
    race_map = ERA1_RACE_LABELS if era == ERA_V1 else ERA2_RACE_LABELS
    eth_map = ERA1_ETHNICITY_MAP if era == ERA_V1 else ERA2_ETHNICITY_MAP

    # Era 1 encodes unreported ethnicity as NULL (14,993 rows in 2020);
    # fill to a literal so the recode map covers it and the manifest shows it.
    df = df.with_columns(pl.col("ethnicity_id").fill_null(ETHNICITY_UNREPORTED))

    df = df.with_columns(
        pl.col("offense_code").replace_strict(OFFENSE_TYPE_MAP).alias("offense_type"),
        pl.col("offense_code")
        .replace_strict(OFFENSE_CATEGORY_MAP)
        .alias("offense_category"),
        pl.col("offense_code").replace_strict(CRIME_AGAINST_MAP).alias("crime_against"),
        pl.col("offense_code").replace_strict(OFFENSE_GROUP_MAP).alias("offense_group"),
        pl.col("arrest_type_id").replace_strict(ARREST_TYPE_MAP).alias("arrest_type"),
        pl.col("race_id").replace_strict(race_map).alias("race_label"),
        pl.col("sex_code").replace_strict(SEX_LABELS).alias("sex_label"),
        pl.col("ethnicity_id").replace_strict(eth_map).alias("ethnicity_bucket"),
    )

    # Age bucket. Era-agnostic rule (verified against every year's data):
    # '00' is the era-2 Unknown sentinel (never published by era 1); NULL
    # age_num only occurs in era 1, where AGE_ID separates Unknown (4) from
    # Over 98 (6, an adult with unpublished age). Any other NULL hard-fails.
    age_int = pl.col("age_num").cast(pl.Int64, strict=True)
    df = df.with_columns(
        pl.when(pl.col("age_num") == AGE_UNKNOWN_SENTINEL)
        .then(pl.lit("age_unknown"))
        .when(pl.col("age_num").is_null() & (pl.col("age_id") == ERA1_AGE_ID_UNKNOWN))
        .then(pl.lit("age_unknown"))
        .when(pl.col("age_num").is_null() & (pl.col("age_id") == ERA1_AGE_ID_OVER_98))
        .then(pl.lit("adult"))
        .when(age_int < JUVENILE_AGE_LIMIT)
        .then(pl.lit("juvenile"))
        .when(age_int >= JUVENILE_AGE_LIMIT)
        .then(pl.lit("adult"))
        .alias("age_bucket")
    )
    unbucketed = df["age_bucket"].null_count()
    if unbucketed:
        raise ValueError(
            f"Year {year}: {unbucketed} arrestee rows with NULL age_num and an "
            "unrecognized age_id — extend the era-1 sentinel handling"
        )

    for col, map_dict, bronze_col in [
        ("offense_type", OFFENSE_TYPE_MAP, "offense_code"),
        ("offense_category", OFFENSE_CATEGORY_MAP, "offense_code"),
        ("crime_against", CRIME_AGAINST_MAP, "offense_code"),
        ("offense_group", OFFENSE_GROUP_MAP, "offense_code"),
        ("arrest_type", ARREST_TYPE_MAP, "arrest_type_id"),
        ("race_label", race_map, "race_id"),
        ("sex_label", SEX_LABELS, "sex_code"),
        ("ethnicity_bucket", eth_map, "ethnicity_id"),
    ]:
        manifest.record_categorical(
            column=col,
            map_dict=map_dict,
            bronze_series=df[bronze_col],
            gold_series=df[col],
        )
    # The age bucketing is threshold logic, not a vocabulary map — record the
    # effective map actually applied (each observed age value + the era-1
    # sentinel age_id codes) so the review can verify it end to end.
    age_bronze = pl.coalesce(
        pl.col("age_num"), pl.lit("age_id_") + pl.col("age_id")
    ).alias("_age_bronze")
    df = df.with_columns(age_bronze)
    age_map: dict[str, str] = {}
    for row in df.select("_age_bronze", "age_bucket").unique().to_dicts():
        age_map[row["_age_bronze"]] = row["age_bucket"]
    manifest.record_categorical(
        column="age_bucket",
        map_dict=age_map,
        bronze_series=df["_age_bronze"],
        gold_series=df["age_bucket"],
    )
    return df.drop("_age_bronze")


def _expand_demographics(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Emit the three demographic slices of every arrest row: all, race, sex.

    Each arrestee carries exactly one race label (Unknown included) and one
    sex label, so within a cell the race rows and the sex rows each partition
    the 'all' row exactly (authored quality checks). Labels normalize through
    the shared aliases; collisions are impossible by construction (each label
    maps to a distinct canonical key) and aggregation groups on the canonical
    value anyway.
    """
    slices = [
        df.with_columns(pl.lit("ALL").alias("demographic_raw")),
        df.with_columns(pl.col("race_label").alias("demographic_raw")),
        df.with_columns(pl.col("sex_label").alias("demographic_raw")),
    ]
    expanded = pl.concat(slices, how="vertical").with_columns(
        normalize_demographic_column("demographic_raw").alias("demographic")
    )
    # Record the effective alias slice (§4.3a): the aliases actually hit,
    # not all ~200. A label missing from the shared aliases raises KeyError.
    observed = expanded["demographic_raw"].unique().sort().to_list()
    manifest.record_categorical(
        column="demographic",
        map_dict={label: DEMOGRAPHIC_ALIASES[label.upper()] for label in observed},
        bronze_series=expanded["demographic_raw"],
        gold_series=expanded["demographic"],
    )
    return expanded


# =============================================================================
# Aggregation
# =============================================================================


def _aggregate(expanded: pl.DataFrame, roster: pl.DataFrame, year: int) -> pl.DataFrame:
    """Aggregate demographic-sliced arrest rows to county and state grain.

    County rows count incident-linked arrests from agencies attributed to
    that (primary) county; state rows count ALL arrests (statewide agencies
    and the county-less Group B report segment included), so within a segment
    state >= sum(counties) structurally. Age and ethnicity partitions ride
    each row as conditional counts.
    """
    group_cols = [
        "reporting_segment",
        "offense_type",
        "offense_category",
        "crime_against",
        "offense_group",
        "arrest_type",
        "demographic",
    ]
    aggs = [
        pl.len().cast(pl.Int64).alias("arrest_count"),
        (pl.col("age_bucket") == "juvenile")
        .sum()
        .cast(pl.Int64)
        .alias("juvenile_count"),
        (pl.col("age_bucket") == "adult").sum().cast(pl.Int64).alias("adult_count"),
        (pl.col("age_bucket") == "age_unknown")
        .sum()
        .cast(pl.Int64)
        .alias("age_unknown_count"),
        (pl.col("ethnicity_bucket") == "hispanic")
        .sum()
        .cast(pl.Int64)
        .alias("hispanic_count"),
        (pl.col("ethnicity_bucket") == "not_hispanic")
        .sum()
        .cast(pl.Int64)
        .alias("not_hispanic_count"),
        (pl.col("ethnicity_bucket") == "ethnicity_unknown")
        .sum()
        .cast(pl.Int64)
        .alias("ethnicity_unknown_count"),
    ]
    county = (
        expanded.filter(pl.col("county_fips").is_not_null())
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
        expanded.group_by(group_cols)
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
    """Transform one GA-{year}.zip into county + state arrest-count rows.

    Processes one year at a time (segment frames are dropped after the
    aggregation) so all seven years never sit in memory together.
    """
    linked, era = _load_linked_arrestees(zip_path, year, manifest)
    linked, roster = _attach_county(linked, zip_path, year, crosswalk, manifest)
    linked = linked.with_columns(pl.lit(SEGMENT_LINKED).alias("reporting_segment"))
    frames = [_recode(linked, era, year, manifest)]

    groupb = _load_groupb_arrestees(zip_path, year, manifest)
    if groupb is not None:
        groupb = groupb.with_columns(pl.lit(SEGMENT_GROUPB).alias("reporting_segment"))
        # The standalone segment only exists in era-2 years (enforced above).
        frames.append(_recode(groupb, ERA_V2, year, manifest))

    arrests = pl.concat(frames, how="vertical")
    expanded = _expand_demographics(arrests, year, manifest)
    result = _aggregate(expanded, roster, year)
    logger.info(
        "Year %d: %d arrest rows (%d incident-linked + %d Group B reports) "
        "-> %d gold rows (%d county, %d state)",
        year,
        arrests.height,
        linked.height,
        arrests.height - linked.height,
        result.height,
        result.filter(pl.col("detail_level") == "county").height,
        result.filter(pl.col("detail_level") == "state").height,
    )
    return result


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for nibrs_arrests."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)
    crosswalk = load_ori_county_crosswalk()

    # 1. Read + transform each year's zip (memory-conscious: one at a time).
    frames: list[pl.DataFrame] = []
    for year, zip_path in nibrs_zip_paths(BRONZE_DIR):
        frames.append(transform_zip(zip_path, year, crosswalk, manifest))
    if not frames:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize + concat, then record the year-derived coverage recode.
    combined = pl.concat(harmonize_columns(frames, STANDARD_COLUMNS, TARGET_TYPES))
    manifest.record_categorical(
        column="coverage",
        map_dict={
            str(y): (
                COVERAGE_PARTIAL if y < FULL_PARTICIPATION_START_YEAR else COVERAGE_FULL
            )
            for y in combined["year"].unique().to_list()
        },
        bronze_series=combined["year"].cast(pl.Utf8),
        gold_series=combined["coverage"],
    )
    logger.info("Combined %d gold-shaped rows", combined.height)

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean an aggregation/join bug and must raise, not be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: one zip per data year + single-pass per-zip aggregation make
    # duplicate keys impossible by construction; sort_col "arrest_count" is
    # the documented safety net (prefer the fuller row) should a future
    # refresh introduce overlapping files.
    combined = deduplicate_by_levels(
        combined,
        {
            "county": [k for k in NATURAL_KEYS if k not in ("detail_level",)],
            "state": [
                k for k in NATURAL_KEYS if k not in ("county_fips", "detail_level")
            ],
        },
        sort_col="arrest_count",
    )

    # 4. Geography nulling (shared domain rules; state rows already NULL).
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
        required_non_null=[
            "year",
            "demographic",
            "coverage",
            "reporting_segment",
            "offense_type",
            "arrest_type",
            "detail_level",
        ],
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
        "Done. Bronze arrestee rows: %s; gold rows: %s; years: %s",
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
            "Arrests reported by Georgia law-enforcement agencies to the "
            "FBI's National Incident-Based Reporting System (NIBRS), "
            "aggregated from arrestee-level master extracts to county x year "
            "x offense type x arrest type x demographic, plus a statewide "
            "rollup. Counts are physical arrests (duplicate NIBRS "
            "multiple-arrest segments excluded) — raw agency reports, "
            "unestimated and unadjusted for non-reporting agencies. Arrests "
            "reach NIBRS by two paths that are served as separate "
            "reporting_segment values, never blended: arrests tied to a "
            "Group A incident (county-attributable via the reporting "
            "agency's primary county, all years) and standalone Group B "
            "arrest reports (drunkenness, DUI, disorderly conduct, ... — "
            "arrest-only offenses with no agency link in the extracts: "
            "state-level only, published 2022 onward, roughly half of all "
            "arrests). Georgia transitioned from SRS summary reporting to "
            "NIBRS around October 2019, so every row also carries the "
            "coverage flag and agencies_reporting companion count shared "
            "with the nibrs_offenses topic. Demographic rows cover race "
            "(NIBRS split Asian / Pacific Islander convention, plus "
            "race_unknown) and sex; arrestee age (juvenile/adult) and "
            "Hispanic ethnicity are served as count partitions of every row "
            "because NIBRS reports race and ethnicity as separate fields."
        ),
        title="NIBRS Arrests by County",
        summary=(
            "Arrests reported by Georgia law-enforcement agencies (FBI "
            "NIBRS), by county, year, offense type, arrest type, and "
            "arrestee demographic, 2018 onward."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "NIBRS data year (the year of the linked incident for "
                    "Group A arrests; arrest dates can spill into the "
                    "following calendar year)."
                ),
            },
            {
                "name": "county_fips",
                "type": "string",
                "example": "13121",
                "null_meaning": (
                    "NULL on statewide rollup rows (including every "
                    "group_b_arrest_report row)."
                ),
                "description": (
                    "5-digit county FIPS code (state prefix 13) of the "
                    "reporting agency's primary county; FK to the counties "
                    "dimension. NULL on statewide rollup rows. Agencies "
                    "spanning multiple counties are attributed wholly to "
                    "their primary county; statewide agencies (GBI, State "
                    "Patrol) and all standalone Group B arrest reports "
                    "(which carry no agency link) count toward state rows "
                    "only."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "validValues": DEMOGRAPHIC_VALUES,
                "example": "all",
                "short_description": (
                    "Arrestee subgroup the row describes (race or sex); "
                    "'all' is every arrestee."
                ),
                "description": (
                    "Arrestee subgroup: 'all' (every arrestee in the cell), "
                    "a race value (NIBRS split convention: asian and "
                    "pacific_islander are separate; race_unknown is the "
                    "agency-reported Unknown code), or a sex value "
                    "(male/female — NIBRS publishes no unknown sex). Race "
                    "rows and sex rows each partition the 'all' row exactly; "
                    "filter to one category when summing. NIBRS ethnicity "
                    "(Hispanic origin) is a separate field from race and is "
                    "served via the hispanic_count / not_hispanic_count / "
                    "ethnicity_unknown_count partition on every row instead "
                    "of demographic rows, which keeps race rows mutually "
                    "exclusive."
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
                    "agencies reported (37 in 2018 — just 315 arrest "
                    "segments — and 276 in 2019), so these years are NOT "
                    "comparable to later years as a state series. "
                    "'full_participation' (2020 onward): statewide NIBRS "
                    "reporting, though the agency roster still varies by "
                    "year (401-455 agencies) — use agencies_reporting to "
                    "separate arrest-volume change from participation "
                    "change."
                ),
            },
            {
                "name": "reporting_segment",
                "type": "string",
                "nullable": False,
                "validValues": [SEGMENT_LINKED, SEGMENT_GROUPB],
                "example": SEGMENT_LINKED,
                "short_description": (
                    "NIBRS reporting path: arrests tied to a Group A "
                    "incident (county-attributable, all years) vs standalone "
                    "Group B arrest reports (state-only, 2022 onward)."
                ),
                "description": (
                    "The NIBRS path the arrest was reported through — a "
                    "coverage boundary, never summed across without noting "
                    "it. 'group_a_incident_linked': arrestee segments of "
                    "Group A incidents (all years, county-attributable; the "
                    "arrest offense can still be a Group B code when the "
                    "arrest cleared a Group A incident). "
                    "'group_b_arrest_report': standalone Group B arrest "
                    "reports (roughly half of all arrests), published in "
                    "the Georgia extracts only from 2022 and carrying no "
                    "agency link — state rows only. A Group B offense "
                    "type's state series therefore jumps in 2022 for "
                    "segment-blind sums, and its county rows reflect only "
                    "the incident-linked slice."
                ),
            },
            {
                "name": "offense_type",
                "type": "string",
                "nullable": False,
                "example": "drug_narcotic_violations",
                "short_description": (
                    "NIBRS offense the arrest was for (e.g. "
                    "drug_narcotic_violations, simple_assault, "
                    "driving_under_the_influence)."
                ),
                "description": (
                    "NIBRS offense type of the arrest (Group A and Group B "
                    "codes), snake_cased from the FBI offense-type lookup "
                    "pinned to the 2024 vocabulary so labels never vary by "
                    "data year — identical values to the nibrs_offenses "
                    "topic, which serves Group A only (Group B offenses are "
                    "arrest-only in NIBRS: DUI, disorderly conduct, "
                    "drunkenness, liquor law violations, trespass, curfew, "
                    "nonviolent family offenses, bad checks, runaway, and "
                    "all_other_offenses). Sum arrest_count over offense "
                    "types within a cell for an all-offenses total; each "
                    "offense type maps to exactly one offense_category, "
                    "crime_against, and offense_group."
                ),
            },
            {
                "name": "offense_category",
                "type": "string",
                "nullable": False,
                "example": "drug_narcotic_offenses",
                "short_description": (
                    "FBI offense category grouping related offense types "
                    "(e.g. assault_offenses groups aggravated_assault, "
                    "simple_assault, intimidation)."
                ),
                "description": (
                    "FBI offense category (pinned 2024 vocabulary) grouping "
                    "related offense types — e.g. assault_offenses covers "
                    "aggravated_assault, simple_assault, and intimidation; "
                    "most Group B offenses are their own category. "
                    "Functionally dependent on offense_type: filter or "
                    "group by it for category-level counts without double "
                    "counting."
                ),
            },
            {
                "name": "crime_against",
                "type": "string",
                "nullable": False,
                "validValues": CRIME_AGAINST_VALUES,
                "example": "society",
                "short_description": (
                    "NIBRS crime-against class: person, property, society, "
                    "or not_a_crime (runaway only)."
                ),
                "description": (
                    "NIBRS crime-against class, functionally dependent on "
                    "offense_type. 'not_a_crime' applies only to runaway "
                    "(NIBRS code 90I) — juveniles taken into protective "
                    "custody, which the FBI classifies as not a crime; a "
                    "handful of such arrest segments appear in 2020."
                ),
            },
            {
                "name": "offense_group",
                "type": "string",
                "nullable": False,
                "validValues": OFFENSE_GROUP_VALUES,
                "example": "group_a",
                "short_description": (
                    "FBI offense taxonomy of the arrest offense: group_a "
                    "(incident-based offenses), group_b (arrest-only "
                    "offenses), or not_a_crime (runaway)."
                ),
                "description": (
                    "FBI offense-code taxonomy, functionally dependent on "
                    "offense_type: 'group_a' offenses are reported as full "
                    "NIBRS incidents (and also appear in the nibrs_offenses "
                    "topic); 'group_b' offenses are arrest-only (90x codes) "
                    "and exist in NIBRS only when an arrest occurs; "
                    "'not_a_crime' is runaway (90I). Distinct from "
                    "reporting_segment: a Group B-coded arrest that cleared "
                    "a Group A incident is reported through the "
                    "incident-linked segment."
                ),
            },
            {
                "name": "arrest_type",
                "type": "string",
                "nullable": False,
                "validValues": ARREST_TYPE_VALUES,
                "example": "taken_into_custody",
                "short_description": (
                    "How the arrest was effected: on_view, summoned_cited, "
                    "or taken_into_custody."
                ),
                "description": (
                    "NIBRS arrest type (Data Element 42): 'on_view' "
                    "(apprehended without a warrant or prior incident "
                    "report), 'summoned_cited' (cited to appear, not taken "
                    "into custody), or 'taken_into_custody' (arrested on a "
                    "warrant or after an incident report). Arrest counts "
                    "are additive across arrest types."
                ),
            },
            {
                "name": "arrest_count",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "key_metric": True,
                "example": 1542,
                "short_description": (
                    "Number of arrests of arrestees in this demographic for "
                    "this offense and arrest type in the county and year "
                    "(raw NIBRS counts, unestimated)."
                ),
                "description": (
                    "Number of physical arrests in the cell: NIBRS arrestee "
                    "segments after excluding duplicate 'M' "
                    "multiple-indicator segments (one arrest clearing "
                    "several Group A incidents publishes one counted "
                    "segment plus duplicates; roughly 2%% of segments are "
                    "excluded as duplicates). An arrestee arrested on "
                    "several occasions in the year is counted once per "
                    "arrest. Raw, unestimated agency reports — interpret "
                    "across years together with coverage, "
                    "reporting_segment, and agencies_reporting. Equals "
                    "juvenile_count + adult_count + age_unknown_count and "
                    "hispanic_count + not_hispanic_count + "
                    "ethnicity_unknown_count on every row."
                ),
            },
            {
                "name": "juvenile_count",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "example": 120,
                "description": (
                    "Arrests of arrestees under 18 at arrest. "
                    "juvenile_count + adult_count + age_unknown_count = "
                    "arrest_count."
                ),
            },
            {
                "name": "adult_count",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "example": 1400,
                "description": (
                    "Arrests of arrestees 18 or older at arrest (including "
                    "the era-1 'Over 98' code, an adult with unpublished "
                    "age). juvenile_count + adult_count + age_unknown_count "
                    "= arrest_count."
                ),
            },
            {
                "name": "age_unknown_count",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "example": 22,
                "description": (
                    "Arrests with unknown arrestee age. The extracts encode "
                    "unknown age as 0 from 2021 on (age code 'Unknown') and "
                    "as a blank age with the Unknown age code in 2018-2020 "
                    "— an age of 0 is a sentinel, not an infant arrestee. "
                    "juvenile_count + adult_count + age_unknown_count = "
                    "arrest_count."
                ),
            },
            {
                "name": "hispanic_count",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "example": 130,
                "short_description": (
                    "Arrests of arrestees reported as Hispanic or Latino "
                    "(NIBRS ethnicity is separate from race)."
                ),
                "description": (
                    "Arrests of arrestees whose NIBRS ethnicity is Hispanic "
                    "or Latino. Ethnicity is a separate NIBRS field from "
                    "race (race values are not Hispanic-exclusive), so it "
                    "is served as a count partition on every row rather "
                    "than as demographic rows — on a race-demographic row "
                    "this is the Hispanic share of that race group. "
                    "hispanic_count + not_hispanic_count + "
                    "ethnicity_unknown_count = arrest_count."
                ),
            },
            {
                "name": "not_hispanic_count",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "example": 1300,
                "description": (
                    "Arrests of arrestees whose NIBRS ethnicity is Not "
                    "Hispanic or Latino. hispanic_count + "
                    "not_hispanic_count + ethnicity_unknown_count = "
                    "arrest_count."
                ),
            },
            {
                "name": "ethnicity_unknown_count",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "example": 112,
                "description": (
                    "Arrests with unknown or unreported arrestee ethnicity "
                    "(the NIBRS Unknown and Not Specified codes plus "
                    "2018-2020 blanks; roughly 23-32%% of arrests per year "
                    "from 2019, and 44%% in the tiny 2018 early-adopter "
                    "sample). hispanic_count + not_hispanic_count + "
                    "ethnicity_unknown_count = arrest_count."
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
                    "Coverage companion, identical in construction to the "
                    "nibrs_offenses topic: the number of distinct agencies "
                    "on the year's NIBRS reporting roster (the 2018 "
                    "extract's 12 exact-duplicate roster rows are "
                    "deduplicated) — for county rows, agencies whose "
                    "primary county is this county; for statewide rows, all "
                    "reporting agencies (37 in 2018, 276 in 2019, 401-455 "
                    "from 2020). Constant across offense types, arrest "
                    "types, segments, and demographics within a "
                    "county-year. Essential for the adoption ramp: rising "
                    "arrest counts alongside a rising agency count reflect "
                    "coverage, not necessarily enforcement."
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
            "2020+) or across reporting_segment without noting the coverage "
            "breaks, and read county trends alongside agencies_reporting. "
            "Sum arrest_count freely across offense types, arrest types, "
            "and (within one demographic category) demographics; always "
            "filter demographic to 'all' or to a single category (race OR "
            "sex) first. Arrest rates require an external population "
            "denominator (not served here). Arrest counts measure "
            "enforcement activity, not crime prevalence, and NIBRS race/"
            "ethnicity values are officer-reported."
        ),
        limitations=(
            "State rows have NULL county_fips. Counts are unestimated raw "
            "agency reports: 2018-2019 cover early-adopter agencies only "
            "(37 / 276 agencies; 2018 has just 315 arrest segments) and are "
            "not comparable to 2020+ as a state series. Standalone Group B "
            "arrest reports (roughly half of all arrests) appear only from "
            "2022 and carry no agency link, so they are state-only "
            "(reporting_segment = 'group_b_arrest_report'); county rows for "
            "Group B offense types reflect only arrests tied to Group A "
            "incidents and vastly understate those offenses. Arrests are "
            "attributed to the reporting agency's primary county — "
            "multi-county agencies are not split. Race and sex demographic "
            "rows are officer-reported; Hispanic ethnicity is a separate "
            "NIBRS field served as count partitions (unknown/unreported "
            "ethnicity runs roughly 23-32%% per year from 2019, and 44%% "
            "in the tiny 2018 sample). Arrestee weapon, resident "
            "status, and juvenile disposition attributes are not served. "
            "NIBRS master extracts have no suppression — a cell with no "
            "arrests simply has no row."
        ),
        quality_checks=[
            {
                "name": "age_partition_sums_to_arrest_count",
                "description": (
                    "Every arrest is bucketed juvenile, adult, or unknown "
                    "age, so the three partition counts must sum exactly to "
                    "arrest_count on every row."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE arrest_count IS NOT "
                    "NULL AND (juvenile_count IS NULL OR adult_count IS NULL "
                    "OR age_unknown_count IS NULL OR juvenile_count + "
                    "adult_count + age_unknown_count != arrest_count)"
                ),
                "mustBe": 0,
            },
            {
                "name": "ethnicity_partition_sums_to_arrest_count",
                "description": (
                    "Every arrest is bucketed Hispanic, not Hispanic, or "
                    "unknown ethnicity, so the three partition counts must "
                    "sum exactly to arrest_count on every row."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE arrest_count IS NOT "
                    "NULL AND (hispanic_count IS NULL OR not_hispanic_count "
                    "IS NULL OR ethnicity_unknown_count IS NULL OR "
                    "hispanic_count + not_hispanic_count + "
                    "ethnicity_unknown_count != arrest_count)"
                ),
                "mustBe": 0,
            },
            {
                "name": "race_rows_sum_to_all_row",
                "description": (
                    "Every arrestee carries exactly one race value (Unknown "
                    "included), so within a cell the race demographic rows "
                    "must sum exactly to the 'all' row — the §5a mutual-"
                    "exclusivity guarantee for the race category."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, reporting_segment, "
                    "offense_type, arrest_type, "
                    "MAX(CASE WHEN demographic = 'all' THEN arrest_count "
                    "END) AS all_count, "
                    "SUM(CASE WHEN demographic IN ('asian', 'black', "
                    "'native_american', 'pacific_islander', 'race_unknown', "
                    "'white') THEN arrest_count END) AS race_sum "
                    "FROM {object} "
                    "GROUP BY year, county_fips, reporting_segment, "
                    "offense_type, arrest_type"
                    ") WHERE all_count IS NULL OR race_sum IS NULL "
                    "OR race_sum != all_count"
                ),
                "mustBe": 0,
            },
            {
                "name": "sex_rows_sum_to_all_row",
                "description": (
                    "Every arrestee is reported male or female (no unknown "
                    "sex appears in any year), so within a cell the sex "
                    "demographic rows must sum exactly to the 'all' row."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, reporting_segment, "
                    "offense_type, arrest_type, "
                    "MAX(CASE WHEN demographic = 'all' THEN arrest_count "
                    "END) AS all_count, "
                    "SUM(CASE WHEN demographic IN ('male', 'female') THEN "
                    "arrest_count END) AS sex_sum "
                    "FROM {object} "
                    "GROUP BY year, county_fips, reporting_segment, "
                    "offense_type, arrest_type"
                    ") WHERE all_count IS NULL OR sex_sum IS NULL "
                    "OR sex_sum != all_count"
                ),
                "mustBe": 0,
            },
            {
                "name": "arrest_count_at_least_one",
                "description": (
                    "Rows exist only for cells with at least one arrest — a "
                    "zero or negative count means the aggregation broke."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE arrest_count IS "
                    "NULL OR arrest_count < 1"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_arrest_total_covers_county_sum",
                "description": (
                    "The state row counts ALL arrests in the segment "
                    "(statewide agencies included), so for every cell with "
                    "county rows a state row must exist with arrest_count "
                    ">= the county sum."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, reporting_segment, offense_type, "
                    "arrest_type, demographic, "
                    "MAX(CASE WHEN county_fips IS NULL THEN arrest_count "
                    "END) AS state_total, "
                    "SUM(CASE WHEN county_fips IS NOT NULL THEN "
                    "arrest_count END) AS county_sum "
                    "FROM {object} GROUP BY year, reporting_segment, "
                    "offense_type, arrest_type, demographic"
                    ") WHERE county_sum IS NOT NULL AND (state_total IS NULL "
                    "OR state_total < county_sum)"
                ),
                "mustBe": 0,
            },
            {
                "name": "group_b_report_rows_are_state_only",
                "description": (
                    "Standalone Group B arrest reports carry no agency link "
                    "in the extracts, so no group_b_arrest_report row can "
                    "have a county."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE reporting_segment "
                    "= 'group_b_arrest_report' AND county_fips IS NOT NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "group_b_report_segment_starts_2022",
                "description": (
                    "The Georgia extracts publish the standalone Group B "
                    "arrest-report segment only from 2022 — an earlier row "
                    "means the coverage break is mislabeled."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE reporting_segment "
                    "= 'group_b_arrest_report' AND year < 2022"
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
                "name": "offense_type_determines_dependent_attributes",
                "description": (
                    "offense_category, crime_against, and offense_group are "
                    "denormalized attributes of offense_type (pinned 2024 "
                    "vocabulary) — each offense_type must map to exactly "
                    "one value of each, or category rollups would double "
                    "count."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT offense_type, "
                    "COUNT(DISTINCT offense_category) AS nc, "
                    "COUNT(DISTINCT crime_against) AS na, "
                    "COUNT(DISTINCT offense_group) AS ng "
                    "FROM {object} GROUP BY offense_type"
                    ") WHERE nc > 1 OR na > 1 OR ng > 1"
                ),
                "mustBe": 0,
            },
            {
                "name": "agencies_reporting_constant_within_year_county",
                "description": (
                    "agencies_reporting describes the year's reporting "
                    "roster for the geography, not the cell — it must be "
                    "identical on every row of a (year, county) group (and "
                    "on every state row of a year)."
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
                    "Every county row's arrests come from at least one "
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
        ],
    )


if __name__ == "__main__":
    main()
