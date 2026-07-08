"""Shared loading logic for the FBI NIBRS master-zip topics.

``nibrs_offenses`` and ``nibrs_arrests`` share the same bronze archives
(``GA-{year}.zip`` under each topic's bronze dir — one FBI Crime Data
Explorer relational NIBRS extract per data year). This module owns the
zip/member mechanics both topics need so neither re-implements them:

- **Year discovery** from the ``GA-{year}.zip`` filenames.
- **Member resolution by basename.** Folder layout inside the zips varies
  non-monotonically (2018/2019/2020/2023 nest members under a ``GA/`` folder;
  2021/2022/2024 are flat) — never address members by literal path.
- **All-string CSV reads with read-loss accounting.** NIBRS extracts carry
  zero-padded codes (``090``, ``23*``) and era-1 quoted-UPPERCASE headers;
  members are read with ``infer_schema_length=0`` (every column Utf8) and
  headers lowercased so era 1 (2018-2020, ``"DATA_YEAR"``) and era 2
  (2021-2024, ``data_year``) unify. Raw data-line counts come from a second
  streaming pass over the compressed member so parser row loss is visible to
  the manifest.
- **The incident -> agency -> ORI join inputs** (``load_incidents`` /
  ``load_agencies``) that both the offense and arrestee segments need to
  reach geography, and the ORI -> county crosswalk reader.
"""

import io
import logging
import re
import zipfile
from pathlib import Path

import polars as pl

logger = logging.getLogger(__name__)

NIBRS_ZIP_RE = re.compile(r"^GA-(\d{4})\.zip$")

ORI_TO_COUNTY_PARQUET = Path("data/gold/crosswalks/ori_to_county.parquet")

# Georgia's SRS -> NIBRS transition completed around Oct 2019; 2020 is the
# first full-participation calendar year. 2018-2019 cover early-adopter
# agencies only (37 / 276 distinct agencies vs 401-455 later) — a
# methodological coverage flag shared by every NIBRS-master topic so the
# values can never drift between siblings (domain rule: version
# methodological breaks, never pool across them).
FULL_PARTICIPATION_START_YEAR = 2020
COVERAGE_PARTIAL = "partial_adoption"
COVERAGE_FULL = "full_participation"

# Pinned Group A offense vocabulary: NIBRS offense code -> (offense_type,
# offense_category, crime_against), generated from GA-2024.zip's
# NIBRS_OFFENSE_TYPE lookup (all 72 Group A codes; snake_cased). Pinning the
# latest lookup keeps labels stable across data years (the code sets are
# identical 2018-2024; 11D was renamed "Fondling" -> "Criminal Sexual
# Contact" in the 2024 lookup and the 2024 wording wins). "23*" (the
# unspecified-larceny wildcard code) gets an explicit descriptive name.
# Shared by nibrs_offenses (offense segment) and nibrs_arrests (arrestee
# segments) so the served offense_type values are identical across topics.
GROUP_A_OFFENSE_VOCAB: dict[str, tuple[str, str, str]] = {
    "09A": ("murder_and_nonnegligent_manslaughter", "homicide_offenses", "person"),
    "09B": ("negligent_manslaughter", "homicide_offenses", "person"),
    "09C": ("justifiable_homicide", "homicide_offenses", "person"),
    "100": ("kidnapping_abduction", "kidnapping_abduction", "person"),
    "101": ("treason", "other_offenses", "society"),
    "103": ("espionage", "other_offenses", "society"),
    "11A": ("rape", "sex_offenses", "person"),
    "11B": ("sodomy", "sex_offenses", "person"),
    "11C": ("sexual_assault_with_an_object", "sex_offenses", "person"),
    "11D": ("criminal_sexual_contact", "sex_offenses", "person"),
    "120": ("robbery", "robbery", "property"),
    "13A": ("aggravated_assault", "assault_offenses", "person"),
    "13B": ("simple_assault", "assault_offenses", "person"),
    "13C": ("intimidation", "assault_offenses", "person"),
    "200": ("arson", "arson", "property"),
    "210": ("extortion_blackmail", "extortion_blackmail", "property"),
    "220": ("burglary_breaking_entering", "burglary_breaking_entering", "property"),
    "23*": ("larceny_theft_not_specified", "larceny_theft_offenses", "property"),
    "23A": ("pocket_picking", "larceny_theft_offenses", "property"),
    "23B": ("purse_snatching", "larceny_theft_offenses", "property"),
    "23C": ("shoplifting", "larceny_theft_offenses", "property"),
    "23D": ("theft_from_building", "larceny_theft_offenses", "property"),
    "23E": (
        "theft_from_coin_operated_machine_or_device",
        "larceny_theft_offenses",
        "property",
    ),
    "23F": ("theft_from_motor_vehicle", "larceny_theft_offenses", "property"),
    "23G": (
        "theft_of_motor_vehicle_parts_or_accessories",
        "larceny_theft_offenses",
        "property",
    ),
    "23H": ("all_other_larceny", "larceny_theft_offenses", "property"),
    "240": ("motor_vehicle_theft", "motor_vehicle_theft", "property"),
    "250": ("counterfeiting_forgery", "counterfeiting_forgery", "property"),
    "26A": ("false_pretenses_swindle_confidence_game", "fraud_offenses", "property"),
    "26B": (
        "credit_card_automated_teller_machine_fraud",
        "fraud_offenses",
        "property",
    ),
    "26C": ("impersonation", "fraud_offenses", "property"),
    "26D": ("welfare_fraud", "fraud_offenses", "property"),
    "26E": ("wire_fraud", "fraud_offenses", "property"),
    "26F": ("identity_theft", "fraud_offenses", "property"),
    "26G": ("hacking_computer_invasion", "fraud_offenses", "property"),
    "26H": ("money_laundering", "other_offenses", "society"),
    "270": ("embezzlement", "embezzlement", "property"),
    "280": ("stolen_property_offenses", "stolen_property_offenses", "property"),
    "290": (
        "destruction_damage_vandalism_of_property",
        "destruction_damage_vandalism_of_property",
        "property",
    ),
    "30A": ("illegal_entry_into_the_united_states", "other_offenses", "society"),
    "30B": ("false_citizenship", "other_offenses", "society"),
    "30C": ("smuggling_aliens", "other_offenses", "society"),
    "30D": ("re_entry_after_deportation", "other_offenses", "society"),
    "35A": ("drug_narcotic_violations", "drug_narcotic_offenses", "society"),
    "35B": ("drug_equipment_violations", "drug_narcotic_offenses", "society"),
    "360": ("failure_to_register_as_a_sex_offender", "other_offenses", "society"),
    "36A": ("incest", "sex_offenses_non_forcible", "person"),
    "36B": ("statutory_rape", "sex_offenses_non_forcible", "person"),
    "370": ("pornography_obscene_material", "pornography_obscene_material", "society"),
    "39A": ("betting_wagering", "gambling_offenses", "society"),
    "39B": ("operating_promoting_assisting_gambling", "gambling_offenses", "society"),
    "39C": ("gambling_equipment_violation", "gambling_offenses", "society"),
    "39D": ("sports_tampering", "gambling_offenses", "society"),
    "40A": ("prostitution", "prostitution_offenses", "society"),
    "40B": ("assisting_or_promoting_prostitution", "prostitution_offenses", "society"),
    "40C": ("purchasing_prostitution", "prostitution_offenses", "society"),
    "49A": ("harboring_escapee_concealing_from_arrest", "other_offenses", "society"),
    "49B": ("flight_to_avoid_prosecution", "other_offenses", "society"),
    "49C": ("flight_to_avoid_deportation", "other_offenses", "society"),
    "510": ("bribery", "bribery", "property"),
    "520": ("weapon_law_violations", "weapon_law_violations", "society"),
    "521": ("violation_of_national_firearm_act_of_1934", "other_offenses", "society"),
    "522": ("weapons_of_mass_destruction", "other_offenses", "society"),
    "526": ("explosives_violation", "other_offenses", "society"),
    "58A": ("import_violations", "other_offenses", "society"),
    "58B": ("export_violations", "other_offenses", "society"),
    "61A": ("federal_liquor_offenses", "other_offenses", "society"),
    "61B": ("federal_tobacco_offenses", "other_offenses", "society"),
    "620": ("wildlife_trafficking", "other_offenses", "society"),
    "64A": ("human_trafficking_commercial_sex_acts", "human_trafficking", "person"),
    "64B": ("human_trafficking_involuntary_servitude", "human_trafficking", "person"),
    "720": ("animal_cruelty", "animal_cruelty", "society"),
}


def nibrs_zip_paths(bronze_dir: Path) -> list[tuple[int, Path]]:
    """Return (data_year, path) for every GA-{year}.zip, sorted by year.

    The filename year equals the ``data_year`` inside every segment (verified
    in bronze-data-structure.md); callers must still assert the equality on
    the frames they read (``assert_data_year``).
    """
    pairs = []
    for path in sorted(bronze_dir.glob("GA-*.zip")):
        match = NIBRS_ZIP_RE.match(path.name)
        if not match:
            raise ValueError(f"Unexpected NIBRS zip filename: {path.name}")
        pairs.append((int(match.group(1)), path))
    return pairs


def _resolve_member(zf: zipfile.ZipFile, basename: str) -> str:
    """Resolve a member by basename, case-insensitively, ignoring folders.

    Zip layout is not predictable from the year (2023 reverted to a nested
    ``GA/`` folder after 2021/2022 were flat), so members are located by
    basename only. Raises if the basename is missing or ambiguous.
    """
    matches = [
        name
        for name in zf.namelist()
        if name.rsplit("/", 1)[-1].lower() == basename.lower()
    ]
    if len(matches) != 1:
        raise KeyError(
            f"{zf.filename}: expected exactly one member named {basename!r}, "
            f"found {matches}"
        )
    return matches[0]


def _count_raw_data_rows(zf: zipfile.ZipFile, member: str) -> int:
    """Count physical data lines (excluding the header) of a zipped CSV.

    Streams the decompressed member in chunks so large segments never load
    twice into memory. The count is an upper bound when fields contain quoted
    newlines — callers record any parsed < raw delta on the manifest for the
    data review to adjudicate.
    """
    newlines = 0
    last_chunk = b""
    with zf.open(member) as handle:
        while chunk := handle.read(1 << 20):
            newlines += chunk.count(b"\n")
            last_chunk = chunk
    if last_chunk and not last_chunk.endswith(b"\n"):
        newlines += 1  # final line without trailing newline
    return max(newlines - 1, 0)  # minus the header line


def read_member_csv(
    zip_path: Path, basename: str
) -> tuple[pl.DataFrame, dict[str, int | str]]:
    """Read one CSV member of a NIBRS zip as all-string with lowercase headers.

    All columns are Utf8 (``infer_schema_length=0``) because NIBRS extracts
    carry zero-padded offense codes (``090``) and sentinel-ish flags that
    schema inference would corrupt; callers cast explicitly. Headers are
    lowercased so era-1 (quoted-UPPERCASE) and era-2 (lowercase) frames carry
    identical column names. Returns ``(df, loss)`` where ``loss`` mirrors
    ``read_bronze_file(..., return_loss=True)`` for manifest accounting.
    """
    with zipfile.ZipFile(zip_path) as zf:
        member = _resolve_member(zf, basename)
        raw_rows = _count_raw_data_rows(zf, member)
        df = pl.read_csv(io.BytesIO(zf.read(member)), infer_schema_length=0)
    df = df.rename({c: c.lower() for c in df.columns})
    loss = {"raw_rows": raw_rows, "parsed_rows": df.height, "format": "csv"}
    return df, loss


def require_columns(df: pl.DataFrame, columns: list[str], label: str) -> None:
    """Hard-stop when an expected column is missing from a member frame.

    A missing source column would otherwise surface as a confusing join/select
    error (or, worse, a silently NULL gold column) — fail with the exact
    missing names instead.
    """
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(
            f"{label}: missing expected column(s) {missing}; has {df.columns}"
        )


def assert_data_year(df: pl.DataFrame, year: int, label: str) -> None:
    """Assert every row's data_year equals the zip filename year (hard fail)."""
    observed = df["data_year"].unique().to_list()
    if observed != [str(year)]:
        raise ValueError(
            f"{label}: data_year values {observed} != filename year {year}"
        )


def load_incidents(zip_path: Path) -> tuple[pl.DataFrame, dict[str, int | str]]:
    """Load NIBRS_incident keyed columns: (incident_id, agency_id, data_year).

    Hard-fails on duplicate incident_id — a duplicate would silently inflate
    every segment joined through it.
    """
    df, loss = read_member_csv(zip_path, "NIBRS_incident.csv")
    require_columns(
        df, ["incident_id", "agency_id", "data_year"], f"{zip_path.name}:NIBRS_incident"
    )
    dup = df.height - df["incident_id"].n_unique()
    if dup:
        raise ValueError(
            f"{zip_path.name}:NIBRS_incident: {dup} duplicate incident_id rows"
        )
    return df.select("incident_id", "agency_id", "data_year"), loss


def load_agencies(zip_path: Path) -> tuple[pl.DataFrame, dict[str, int | str]]:
    """Load the per-year agency roster: unique (agency_id, ori, data_year).

    One row per agency that reported NIBRS data for the year — the roster is
    the coverage denominator for the adoption-ramp years (37 distinct
    agencies in 2018 vs 434-455 from 2021 on).

    **The GA-2018 extract publishes 12 exact-duplicate roster rows** (49 rows,
    37 distinct agencies; every duplicate is byte-identical) — joining the
    roster without deduplication silently inflates every 2018 count by ~48%%.
    Full-row duplicates on (agency_id, ori) are dropped here with a warning
    (callers can compute the dropped count as ``loss["parsed_rows"] -
    df.height`` and record it on their manifest); an agency_id carrying two
    DIFFERENT oris (or vice versa) is ambiguity, not repetition, and
    hard-fails.
    """
    df, loss = read_member_csv(zip_path, "agencies.csv")
    require_columns(df, ["agency_id", "ori", "data_year"], f"{zip_path.name}:agencies")
    df = df.select("agency_id", "ori", "data_year")
    dup = df.height - df.unique().height
    if dup:
        logger.warning(
            "%s:agencies: dropped %d exact-duplicate roster row(s) "
            "(source publishes repeated agency rows; e.g. GA-2018 lists 49 "
            "rows for 37 agencies)",
            zip_path.name,
            dup,
        )
        df = df.unique()
    if df["agency_id"].n_unique() != df.height or df["ori"].n_unique() != df.height:
        raise ValueError(
            f"{zip_path.name}:agencies: agency_id<->ori mapping is not 1:1 "
            "after exact-duplicate removal — resolve before joining"
        )
    return df, loss


def load_ori_county_crosswalk() -> pl.DataFrame:
    """Load the ORI -> county crosswalk (ori, county_fips, multi_county).

    ``county_fips`` is the agency's PRIMARY county (27 of 434 agencies span
    multiple counties in 2024 — each is attributed wholly to its primary
    county, never split or double-counted). NULL ``county_fips`` marks the 12
    statewide agencies (GBI, State Patrol, Ports Authority) that belong to no
    single county — callers decide how those roll up (typically state-row
    only). Hard-fails on duplicate ori (would fan out fact joins).
    """
    xw = pl.read_parquet(ORI_TO_COUNTY_PARQUET).select(
        "ori", "county_fips", "multi_county"
    )
    dup = xw.height - xw["ori"].n_unique()
    if dup:
        raise ValueError(f"ori_to_county crosswalk: {dup} duplicate ori rows")
    return xw
