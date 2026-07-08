"""Transform the FBI CDE national hate-crime master file into a gold fact table.

Source: FBI Crime Data Explorer "Hate Crime" additional dataset —
``hate_crime.zip`` containing one national incident-level CSV (1991-2024,
265,834 rows; 1,983 Georgia rows). Each bronze row is one bias-motivated
criminal incident reported by a law-enforcement agency (ORI). Gold aggregates
Georgia incidents to county x year x bias motivation, plus a statewide rollup.

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Grain: year x county_fips x bias_motivation (+ statewide rollup).** The
  atomic bias motivation (32 observed GA values, 35 national) is preserved as
  the grain categorical — rolling up to the FBI's six bias categories would
  irrecoverably collapse civically distinct series (anti_black vs anti_white
  vs anti_hispanic), while the category rollup is exactly recoverable by
  grouping. ``bias_category`` (race_ethnicity_ancestry / religion /
  sexual_orientation / disability / gender / gender_identity / unknown) is
  denormalized as a functionally dependent attribute (authored check).
  ``offense_category`` is deliberately NOT a second grain categorical: with
  only ~2,000 incidents over 34 years, county x bias cells are already mostly
  single-incident, and a bias x offense grain would be almost entirely 1s.
- **Multi-bias incidents are exploded, once per atomic bias.** 15 GA rows
  carry semicolon-delimited multi-value ``bias_desc`` (e.g. "Anti-Black or
  African American;Anti-White"); each contributes one row per atomic bias so
  no bias series silently loses incidents. Consequence (documented in the
  contract): ``incident_count`` is additive across counties (an incident
  belongs to one agency) but NOT across bias motivations — summing it over
  bias rows double-counts multi-bias incidents. The redundant
  ``multiple_bias``/``multiple_offense`` M/S flags are dropped (verified
  exact mirrors of the semicolons in bronze-data-structure.md).
- **County attribution: primary county via the ORI crosswalk.** All 224 GA
  hate-crime ORIs resolve in ``data/gold/crosswalks/ori_to_county.parquet``
  (the two agencies absent from the CDE agency API — Watkinsville PD,
  Southern Polytechnic State University — are patched into the crosswalk
  build itself). 16 multi-county agencies covering 600 rows (30%%, dominated
  by Atlanta PD -> Fulton) are attributed wholly to their PRIMARY county,
  never split or double-counted — same convention as the nibrs_offenses /
  nibrs_arrests siblings, called out in the contract limitations. ORIs whose
  crosswalk county is NULL (statewide agencies) would count toward state rows
  only; zero such ORIs appear in this file today (guarded + logged).
- **Reporting coverage confounds trends; absence is NOT zero.** Hate-crime
  reporting is voluntary and notoriously under-reported: GA participation
  jumped from ~11 to 71 reporting agencies in 2019 (NIBRS transition) and has
  declined since 2021. Absent county-years are left absent — never
  zero-filled — because a county with no row has no *reports*, not
  necessarily no hate crime. Every row carries an ``agencies_reporting``
  companion: distinct agencies in the geography that reported >= 1 hate-crime
  incident that year. Unlike the NIBRS-master siblings there is no
  participation roster in this file (zero-report agencies are
  indistinguishable from non-participating ones) and no reporting-program
  field, so no ``coverage`` flag column is emitted — the file predates NIBRS
  (1991+) and the Oct-2019 flag boundary does not apply; the caveat lives in
  the contract limitations instead.
- **Metrics.** ``incident_count`` (key metric — distinct bias-motivated
  incidents; hate-crime statistics are incident counts by convention),
  ``victim_count`` (sum of ``total_individual_victims``: individual human
  victims; 0 = entity-only victims such as vandalized businesses), and
  ``known_offender_count`` (sum of ``total_offender_count``, which counts
  KNOWN offenders — bronze 0 means "offender unknown" and correctly
  contributes zero known offenders). The bronze ``victim_count`` column
  (victim *entity types*, not people) and the NIBRS-only adult/juvenile
  splits (null for all SRS-era submissions) are excluded as misleading;
  offender race/ethnicity is excluded because offender demographics do not
  share the demographics-dimension semantics of victim/population datasets.
- **victim_count NULL propagation.** 15 GA incidents (2017-2019) have NULL
  ``total_individual_victims``. A cell containing any such incident gets a
  NULL ``victim_count`` (never an understated sum), per the suppression->NULL
  convention; documented via ``null_meaning``.
- **Extreme-but-conceivable value preserved (§4b).** The 2017 Gwinnett County
  PD incident with ``total_individual_victims = 100`` (mass-victim
  intimidation, Anti-Islamic;Anti-Multiple Races) is conceivable and kept —
  documented in the contract, not masked. No impossible values exist (all
  metrics are counts derived from non-negative sources), so no §4b masks; the
  source publishes hate-crime counts unsuppressed (``suppressed_to_null=False``).
- **Dedup tie-break.** A single national file with globally unique
  ``incident_id`` (asserted) and one single-pass aggregation make duplicate
  natural keys impossible by construction; ``deduplicate_by_levels(
  sort_col="incident_count")`` remains as the documented safety net (prefer
  the fuller row) should a future refresh add overlapping files. The
  collision guard runs first and hard-fails on divergent duplicates.
- **Refresh safety.** The bias vocabulary map covers all 35 NATIONAL atomic
  values (GA shows 32 today — Anti-Hindu, Anti-Jehovah's Witness and
  "Unknown (offender's motivation not known)" have no GA incidents yet), and
  any bias label missing from the map hard-fails rather than guessing. The
  CDE re-publishes the master file with late submissions (2024 is likely
  still filling in), so refreshes rewrite all years.
"""

import logging
import zipfile
from pathlib import Path

import polars as pl

from src.etl.criminal_justice.fbi_cde._nibrs_shared import (
    load_ori_county_crosswalk,
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

TOPIC = "hate_crimes"
BRONZE_DIR = Path("data/bronze/criminal_justice/fbi_cde/hate_crimes")
GOLD_DIR = Path("data/gold/criminal_justice/hate_crimes")
SOURCE_URL = "https://cde.ucr.cjis.gov"

ZIP_PATH = BRONZE_DIR / "hate_crime.zip"
CSV_MEMBER_BASENAME = "hate_crime.csv"

# The master file's year span is 1991-2024 with a uniform 28-column schema —
# a single era, detected by its column signature (never by year ranges).
ERA_SIGNATURES: dict[str, list[str]] = {
    "hate_crime_master_v1": ["incident_id", "data_year", "ori", "bias_desc"],
}

# Atomic bias-motivation vocabulary: FBI ``bias_desc`` label -> (snake_case
# bias_motivation, FBI bias category). Pinned to the FULL national vocabulary
# (35 atomic values extracted from the 2025-07-09 master file) so a GA refresh
# surfacing a new-to-Georgia label (Anti-Hindu, Anti-Jehovah's Witness,
# unknown motivation) maps cleanly; a label absent from this map hard-fails.
# Naming: disambiguating parentheticals are kept (anti_gay_male,
# anti_lesbian_female, anti_lgbt_mixed_group); pure gloss/enumeration
# parentheticals are dropped (anti_islamic, anti_eastern_orthodox).
BIAS_VOCAB: dict[str, tuple[str, str]] = {
    # Race / ethnicity / ancestry
    "Anti-American Indian or Alaska Native": (
        "anti_american_indian_or_alaska_native",
        "race_ethnicity_ancestry",
    ),
    "Anti-Arab": ("anti_arab", "race_ethnicity_ancestry"),
    "Anti-Asian": ("anti_asian", "race_ethnicity_ancestry"),
    "Anti-Black or African American": (
        "anti_black_or_african_american",
        "race_ethnicity_ancestry",
    ),
    "Anti-Hispanic or Latino": ("anti_hispanic_or_latino", "race_ethnicity_ancestry"),
    "Anti-Multiple Races, Group": (
        "anti_multiple_races_group",
        "race_ethnicity_ancestry",
    ),
    "Anti-Native Hawaiian or Other Pacific Islander": (
        "anti_native_hawaiian_or_other_pacific_islander",
        "race_ethnicity_ancestry",
    ),
    "Anti-Other Race/Ethnicity/Ancestry": (
        "anti_other_race_ethnicity_ancestry",
        "race_ethnicity_ancestry",
    ),
    "Anti-White": ("anti_white", "race_ethnicity_ancestry"),
    # Religion
    "Anti-Atheism/Agnosticism": ("anti_atheism_agnosticism", "religion"),
    "Anti-Buddhist": ("anti_buddhist", "religion"),
    "Anti-Catholic": ("anti_catholic", "religion"),
    "Anti-Church of Jesus Christ": ("anti_church_of_jesus_christ", "religion"),
    "Anti-Eastern Orthodox (Russian, Greek, Other)": (
        "anti_eastern_orthodox",
        "religion",
    ),
    "Anti-Hindu": ("anti_hindu", "religion"),
    "Anti-Islamic (Muslim)": ("anti_islamic", "religion"),
    "Anti-Jehovah's Witness": ("anti_jehovahs_witness", "religion"),
    "Anti-Jewish": ("anti_jewish", "religion"),
    "Anti-Multiple Religions, Group": ("anti_multiple_religions_group", "religion"),
    "Anti-Other Christian": ("anti_other_christian", "religion"),
    "Anti-Other Religion": ("anti_other_religion", "religion"),
    "Anti-Protestant": ("anti_protestant", "religion"),
    "Anti-Sikh": ("anti_sikh", "religion"),
    # Sexual orientation
    "Anti-Bisexual": ("anti_bisexual", "sexual_orientation"),
    "Anti-Gay (Male)": ("anti_gay_male", "sexual_orientation"),
    "Anti-Heterosexual": ("anti_heterosexual", "sexual_orientation"),
    "Anti-Lesbian (Female)": ("anti_lesbian_female", "sexual_orientation"),
    "Anti-Lesbian, Gay, Bisexual, or Transgender (Mixed Group)": (
        "anti_lgbt_mixed_group",
        "sexual_orientation",
    ),
    # Disability
    "Anti-Mental Disability": ("anti_mental_disability", "disability"),
    "Anti-Physical Disability": ("anti_physical_disability", "disability"),
    # Gender
    "Anti-Female": ("anti_female", "gender"),
    "Anti-Male": ("anti_male", "gender"),
    # Gender identity
    "Anti-Gender Non-Conforming": ("anti_gender_non_conforming", "gender_identity"),
    "Anti-Transgender": ("anti_transgender", "gender_identity"),
    # Motivation not established (appears nationally, not yet in GA)
    "Unknown (offender's motivation not known)": ("unknown_motivation", "unknown"),
}

BIAS_MOTIVATION_MAP: dict[str, str] = {k: v[0] for k, v in BIAS_VOCAB.items()}
BIAS_CATEGORY_MAP: dict[str, str] = {k: v[1] for k, v in BIAS_VOCAB.items()}
BIAS_CATEGORY_VALUES: list[str] = sorted(set(BIAS_CATEGORY_MAP.values()))

METRIC_COLUMNS: list[str] = [
    "incident_count",
    "victim_count",
    "known_offender_count",
    "agencies_reporting",
]

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "county_fips",
    "bias_motivation",
    "bias_category",
    *METRIC_COLUMNS,
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "county_fips": pl.Utf8,
    "bias_motivation": pl.Utf8,
    "bias_category": pl.Utf8,
    **{c: pl.Int64 for c in METRIC_COLUMNS},
    "detail_level": pl.Utf8,
}

# bias_motivation determines bias_category (enforced by an authored quality
# check), so these keys uniquely identify a row even though the auto-derived
# contract grain also lists the dependent categorical.
NATURAL_KEYS: list[str] = ["year", "county_fips", "bias_motivation", "detail_level"]


# =============================================================================
# Bronze load
# =============================================================================


def _load_georgia_incidents(manifest: TransformManifest) -> pl.DataFrame:
    """Read the national master CSV from the zip and filter to Georgia.

    Read all-string (``infer_schema_length=0``) because default schema
    inference fails at row ~10k on the literal ``NULL`` strings in
    ``total_individual_victims``; numeric columns are cast explicitly below.
    The file spans 1991-2024, so bronze row counts are recorded per data
    year (national), with the non-Georgia drop recorded per year as an
    explicit filter event.
    """
    if not ZIP_PATH.exists():
        raise FileNotFoundError(f"Bronze zip missing: {ZIP_PATH}")
    with zipfile.ZipFile(ZIP_PATH) as zf:
        members = [n for n in zf.namelist() if n.endswith(CSV_MEMBER_BASENAME)]
    logger.info("Reading %s member(s) %s", ZIP_PATH.name, members)

    df, loss = read_member_csv(ZIP_PATH, CSV_MEMBER_BASENAME)
    # The master file is one multi-year national CSV; read loss (if any) is
    # recorded under the latest data year present.
    latest_year = int(df["data_year"].cast(pl.Int32).max())
    manifest.record_read_loss(
        latest_year,
        f"{ZIP_PATH.name}:{CSV_MEMBER_BASENAME}",
        int(loss["raw_rows"]),
        int(loss["parsed_rows"]),
    )

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{ZIP_PATH.name}: no era signature matched {df.columns}")
    manifest.record_file(ZIP_PATH, latest_year, era, df.height, df.columns)

    require_columns(
        df,
        [
            "incident_id",
            "data_year",
            "ori",
            "state_abbr",
            "incident_date",
            "bias_desc",
            "total_individual_victims",
            "total_offender_count",
        ],
        f"{ZIP_PATH.name}:{CSV_MEMBER_BASENAME}",
    )

    df = df.with_columns(pl.col("data_year").cast(pl.Int32).alias("year"))

    # Per-year bronze accounting: national rows recorded as bronze, with the
    # non-Georgia drop per year recorded as an explicit filter so the
    # bronze-vs-gold arithmetic in the manifest stays explainable.
    national_by_year = {
        r["year"]: r["len"] for r in df.group_by("year").len().to_dicts()
    }
    ga = df.filter(pl.col("state_abbr") == "GA")
    ga_by_year = {r["year"]: r["len"] for r in ga.group_by("year").len().to_dicts()}
    for year in sorted(national_by_year):
        manifest.record_bronze(year, national_by_year[year])
        dropped = national_by_year[year] - ga_by_year.get(year, 0)
        if dropped:
            manifest.record_filtered(year, dropped, "non_georgia_state_row")
    logger.info(
        "Filtered national file to Georgia: %d of %d rows kept (state_abbr == 'GA')",
        ga.height,
        df.height,
    )

    # Structural guards from the structure doc — cheap, refresh-proof.
    dup_ids = ga.height - ga["incident_id"].n_unique()
    if dup_ids:
        raise ValueError(f"{ZIP_PATH.name}: {dup_ids} duplicate GA incident_id rows")
    date_mismatch = ga.filter(
        pl.col("incident_date").str.slice(0, 4).cast(pl.Int32) != pl.col("year")
    )
    if date_mismatch.height:
        raise ValueError(
            f"{ZIP_PATH.name}: {date_mismatch.height} GA rows where "
            "year(incident_date) != data_year"
        )

    # Explicit casts off the all-string read. total_individual_victims uses
    # strict=False so the literal 'NULL' strings (15 GA rows) become null;
    # total_offender_count is documented never-null (0 = offender unknown),
    # so any null after cast is a hard failure, not a silent zero.
    ga = ga.with_columns(
        pl.col("total_individual_victims")
        .cast(pl.Int64, strict=False)
        .alias("individual_victims"),
        pl.col("total_offender_count")
        .cast(pl.Int64, strict=False)
        .alias("known_offenders"),
    )
    if ga["known_offenders"].null_count():
        raise ValueError(
            f"{ZIP_PATH.name}: {ga['known_offenders'].null_count()} GA rows with "
            "non-numeric total_offender_count (documented never-null)"
        )
    null_victims = ga.filter(pl.col("individual_victims").is_null())
    if null_victims.height:
        logger.warning(
            "%d GA incidents have NULL total_individual_victims (years %s) — "
            "cells containing them get NULL victim_count, never an understated "
            "sum",
            null_victims.height,
            sorted(null_victims["year"].unique().to_list()),
        )
    return ga.select(
        "year",
        "incident_id",
        "ori",
        "bias_desc",
        "individual_victims",
        "known_offenders",
    )


def _attach_county(
    ga: pl.DataFrame, crosswalk: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Join incidents -> ORI -> primary county via the shared crosswalk.

    Every GA ORI must exist in the crosswalk (hard fail otherwise — never
    silently NULLed). A crosswalk match with NULL county marks a statewide
    agency (GBI, State Patrol): those incidents roll up to the state row
    only. Zero such ORIs appear among hate-crime reporters today.
    """
    unmatched = ga.select("ori").unique().join(crosswalk, on="ori", how="anti")
    if unmatched.height:
        raise ValueError(
            "ORIs missing from ori_to_county crosswalk — rebuild the "
            f"crosswalk: {unmatched['ori'].sort().to_list()}"
        )
    ga = ga.join(crosswalk.select("ori", "county_fips"), on="ori", how="left")

    statewide = ga.filter(pl.col("county_fips").is_null())
    if statewide.height:
        # Statewide agencies have no primary county: their incidents count
        # toward the state rollup only. None exist in the current file.
        logger.warning(
            "%d GA incidents from statewide (no-county) agencies %s count "
            "toward state rows only",
            statewide.height,
            statewide["ori"].unique().sort().to_list(),
        )

    # Manifest: the ORI -> primary-county attribution is this topic's
    # geography recode; record the slice actually observed on incident rows.
    ori_map = {
        row["ori"]: (row["county_fips"] or "unassigned_statewide")
        for row in ga.select("ori", "county_fips").unique().to_dicts()
    }
    manifest.record_categorical(
        column="county_fips",
        map_dict=ori_map,
        bronze_series=ga["ori"],
        gold_series=ga["county_fips"],
    )
    multi = (
        ga.select("ori")
        .unique()
        .join(
            crosswalk.filter(pl.col("multi_county")).select("ori"),
            on="ori",
            how="semi",
        )
    )
    if multi.height:
        affected = ga.join(multi, on="ori", how="semi").height
        logger.info(
            "%d hate-crime-reporting agencies span multiple counties (%d "
            "incidents, incl. Atlanta PD -> Fulton); each is attributed "
            "wholly to its primary county",
            multi.height,
            affected,
        )
    return ga


def _explode_bias(ga: pl.DataFrame, manifest: TransformManifest) -> pl.DataFrame:
    """Explode semicolon-delimited multi-bias incidents to incident-bias pairs.

    15 GA incidents carry 2-3 atomic biases; each contributes one pair per
    bias so no bias series loses incidents (incident_count is consequently
    NOT additive across bias motivations — documented in the contract). Any
    bias label missing from the pinned national vocabulary hard-fails.
    """
    exploded = (
        ga.with_columns(pl.col("bias_desc").str.split(";"))
        .explode("bias_desc")
        .with_columns(pl.col("bias_desc").str.strip_chars())
    )
    added = exploded.height - ga.height
    logger.info(
        "Exploded multi-bias incidents: %d incidents -> %d incident-bias pairs (+%d)",
        ga.height,
        exploded.height,
        added,
    )
    # A repeated atomic bias within one incident would double-count it in its
    # own bias cell — dedupe defensively (zero observed today).
    before = exploded.height
    exploded = exploded.unique(subset=["incident_id", "bias_desc"], keep="first")
    if exploded.height != before:
        dropped = before - exploded.height
        logger.warning(
            "Dropped %d repeated (incident, bias) pairs within single incidents",
            dropped,
        )
        manifest.record_filtered(
            int(exploded["year"].max()), dropped, "repeated_bias_within_incident"
        )

    unknown = exploded.filter(~pl.col("bias_desc").is_in(list(BIAS_VOCAB)))
    if unknown.height:
        raise ValueError(
            "bias_desc values missing from the pinned national vocabulary "
            f"(map them, never guess): {unknown['bias_desc'].unique().sort().to_list()}"
        )
    exploded = exploded.with_columns(
        pl.col("bias_desc")
        .replace_strict(BIAS_MOTIVATION_MAP)
        .alias("bias_motivation"),
        pl.col("bias_desc").replace_strict(BIAS_CATEGORY_MAP).alias("bias_category"),
    )
    for col, map_dict in [
        ("bias_motivation", BIAS_MOTIVATION_MAP),
        ("bias_category", BIAS_CATEGORY_MAP),
    ]:
        manifest.record_categorical(
            column=col,
            map_dict=map_dict,
            bronze_series=exploded["bias_desc"],
            gold_series=exploded[col],
        )
    return exploded


# =============================================================================
# Aggregation
# =============================================================================


def _reporting_agency_counts(ga: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Count distinct agencies with >= 1 reported hate crime, per geography.

    NOT a participation roster: the master file only contains agencies that
    reported at least one incident, so zero-report participants are
    indistinguishable from non-participants (documented in the contract).
    County counts use the agency's primary county; a statewide (NULL-county)
    agency would count in the state figure only.
    """
    county = (
        ga.filter(pl.col("county_fips").is_not_null())
        .select("year", "county_fips", "ori")
        .unique()
        .group_by("year", "county_fips")
        .agg(pl.len().cast(pl.Int64).alias("agencies_reporting"))
    )
    state = (
        ga.select("year", "ori")
        .unique()
        .group_by("year")
        .agg(pl.len().cast(pl.Int64).alias("agencies_reporting"))
    )
    return county, state


def _aggregate(exploded: pl.DataFrame, ga: pl.DataFrame) -> pl.DataFrame:
    """Aggregate incident-bias pairs to county and state grain.

    County rows count incidents from agencies attributed to that (primary)
    county; the state row counts ALL incidents including any statewide
    agencies, so state >= sum(counties) structurally (equal today).
    victim_count propagates NULL when any contributing incident's individual-
    victim count is unreported (never an understated sum).
    """
    aggs = [
        pl.col("incident_id").n_unique().cast(pl.Int64).alias("incident_count"),
        pl.when(pl.col("individual_victims").is_null().any())
        .then(pl.lit(None, dtype=pl.Int64))
        .otherwise(pl.col("individual_victims").sum())
        .alias("victim_count"),
        pl.col("known_offenders").sum().cast(pl.Int64).alias("known_offender_count"),
    ]
    group_cols = ["bias_motivation", "bias_category"]
    county_roster, state_roster = _reporting_agency_counts(ga)

    county = (
        exploded.filter(pl.col("county_fips").is_not_null())
        .group_by(["year", "county_fips", *group_cols])
        .agg(aggs)
        .join(county_roster, on=["year", "county_fips"], how="left")
        .with_columns(pl.lit("county").alias("detail_level"))
    )
    if county["agencies_reporting"].null_count():
        raise ValueError("county rows without a reporting-agency count")

    state = (
        exploded.group_by(["year", *group_cols])
        .agg(aggs)
        .join(state_roster, on="year", how="left")
        .with_columns(
            pl.lit(None).cast(pl.Utf8).alias("county_fips"),
            pl.lit("state").alias("detail_level"),
        )
    )
    if state["agencies_reporting"].null_count():
        raise ValueError("state rows without a reporting-agency count")
    return pl.concat([county, state.select(county.columns)], how="vertical")


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for hate_crimes."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)
    crosswalk = load_ori_county_crosswalk()

    # 1. Read the national master file, filter to GA, attach counties,
    #    explode multi-bias incidents, aggregate.
    ga = _load_georgia_incidents(manifest)
    ga = _attach_county(ga, crosswalk, manifest)
    exploded = _explode_bias(ga, manifest)
    result = _aggregate(exploded, ga)
    logger.info(
        "Aggregated %d incident-bias pairs -> %d gold rows (%d county, %d state)",
        exploded.height,
        result.height,
        result.filter(pl.col("detail_level") == "county").height,
        result.filter(pl.col("detail_level") == "state").height,
    )

    # 2. Harmonize to the gold schema (single era, so a one-frame pass).
    combined = pl.concat(harmonize_columns([result], STANDARD_COLUMNS, TARGET_TYPES))

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean an aggregation/join bug and must raise, not be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: one national file with globally unique incident_id (asserted)
    # + a single-pass aggregation make duplicate keys impossible by
    # construction; sort_col "incident_count" is the documented safety net
    # (prefer the fuller row) should a future refresh add overlapping files.
    combined = deduplicate_by_levels(
        combined,
        {
            "county": ["year", "county_fips", "bias_motivation"],
            "state": ["year", "bias_motivation"],
        },
        sort_col="incident_count",
    )

    # 4. Geography nulling (shared domain rules; state rows already NULL).
    # No §4b masks apply: metrics are counts/sums of non-negative sources, so
    # impossible values cannot occur; the 2017 Gwinnett 100-victim incident is
    # extreme-but-conceivable and preserved (see module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=CRIMINAL_JUSTICE_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. victim_count carries documented NULLs (2017-2019),
    # so spikes are surfaced as warnings with a known cause.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(
        combined,
        required_non_null=["year", "bias_motivation", "bias_category", "detail_level"],
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
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Bias-motivated (hate crime) criminal incidents reported by "
            "Georgia law-enforcement agencies to the FBI's UCR hate crime "
            "collection, aggregated from the national incident-level master "
            "file to county x year x bias motivation (32 observed atomic "
            "bias motivations with the FBI's bias-category rollup), plus a "
            "statewide rollup, 1991 onward. Hate-crime reporting is "
            "voluntary and severely under-reported: the number of Georgia "
            "agencies reporting any hate crime jumped from about 11 to 71 in "
            "2019 with the NIBRS transition and has declined since 2021, so "
            "year-over-year change largely reflects reporting participation, "
            "not underlying incidence. A county-year with no row means no "
            "REPORTS, never zero hate crime. Incidents are attributed to the "
            "reporting agency's primary county via the ORI-to-county "
            "crosswalk."
        ),
        title="FBI Hate Crime Incidents by County",
        summary=(
            "Hate crime incidents reported by Georgia law-enforcement "
            "agencies (FBI UCR hate crime collection), by county, year, and "
            "bias motivation, 1991 onward."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Calendar year the incidents occurred (data year; matches "
                    "the incident date on every row)."
                ),
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
                    "spanning multiple counties (16 of the 224 reporting "
                    "agencies, covering about 30%% of incidents — dominated "
                    "by Atlanta PD, attributed to Fulton) are attributed "
                    "wholly to their primary county, never split."
                ),
            },
            {
                "name": "bias_motivation",
                "type": "string",
                "nullable": False,
                "example": "anti_black_or_african_american",
                "short_description": (
                    "Atomic FBI bias motivation (e.g. "
                    "anti_black_or_african_american, anti_jewish, "
                    "anti_gay_male)."
                ),
                "description": (
                    "Atomic FBI bias motivation, snake_cased from the "
                    "national hate-crime vocabulary (35 national values; 32 "
                    "observed in Georgia). A multi-bias incident (15 in "
                    "Georgia) appears once under EACH of its bias "
                    "motivations, so incident_count is NOT additive across "
                    "bias motivations — sum within one bias motivation or "
                    "use bias_category with care. Each bias_motivation maps "
                    "to exactly one bias_category."
                ),
            },
            {
                "name": "bias_category",
                "type": "string",
                "nullable": False,
                "validValues": BIAS_CATEGORY_VALUES,
                "example": "race_ethnicity_ancestry",
                "short_description": (
                    "FBI bias category: race_ethnicity_ancestry, religion, "
                    "sexual_orientation, disability, gender, gender_identity "
                    "(or unknown)."
                ),
                "description": (
                    "The FBI's standard bias-category rollup, functionally "
                    "dependent on bias_motivation: race_ethnicity_ancestry, "
                    "religion, sexual_orientation, disability, gender, "
                    "gender_identity, plus unknown for the national "
                    "'motivation not known' value (no Georgia incidents "
                    "yet). Filter or group by it for category-level counts; "
                    "note a multi-bias incident spanning two categories is "
                    "counted once under each."
                ),
            },
            {
                "name": "incident_count",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "key_metric": True,
                "example": 12,
                "short_description": (
                    "Hate-crime incidents with this bias motivation reported "
                    "in the county and year (raw reports — reporting is "
                    "voluntary and under-reported)."
                ),
                "description": (
                    "Number of distinct bias-motivated incidents with this "
                    "bias motivation reported by agencies attributed to the "
                    "county in the year. Raw agency reports: hate-crime "
                    "reporting is voluntary and severely under-reported, and "
                    "agency participation varies sharply by year (about 11 "
                    "agencies before 2019, 71-82 in 2019-2021, declining "
                    "since) — read alongside agencies_reporting, and never "
                    "treat an absent county-year as zero hate crime. "
                    "Additive across counties (an incident belongs to one "
                    "agency) but NOT across bias motivations: a multi-bias "
                    "incident is counted once under each of its biases."
                ),
            },
            {
                "name": "victim_count",
                "type": "int64",
                "unit": "count",
                "example": 14,
                "null_meaning": (
                    "NULL when the individual-victim count was unreported "
                    "for any contributing incident (15 Georgia incidents, "
                    "2017-2019)."
                ),
                "short_description": (
                    "Individual (human) victims across the row's incidents; "
                    "0 means only entity victims (businesses, institutions)."
                ),
                "description": (
                    "Total individual (human) victims across the row's "
                    "incidents. 0 is real: it means every victim was an "
                    "entity (business, government, religious organization), "
                    "e.g. vandalism of an institution. NULL when any "
                    "contributing incident's individual-victim count was "
                    "unreported (15 Georgia incidents, 2017-2019) — a sum "
                    "is never understated. One extreme value is preserved "
                    "as published: a 2017 Gwinnett County intimidation "
                    "incident with 100 individual victims (mass-victim "
                    "incident; conceivable, not masked). Victims of a "
                    "multi-bias incident are counted under each of its bias "
                    "motivations."
                ),
            },
            {
                "name": "known_offender_count",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "example": 9,
                "short_description": (
                    "Known offenders across the row's incidents; incidents "
                    "with unidentified offenders contribute zero."
                ),
                "description": (
                    "Total KNOWN offenders across the row's incidents (the "
                    "FBI convention: an incident whose offenders were never "
                    "identified reports zero known offenders — about a third "
                    "of Georgia incidents). A count lower than "
                    "incident_count therefore signals unidentified "
                    "offenders, not fewer offenders. Offenders of a "
                    "multi-bias incident are counted under each of its bias "
                    "motivations."
                ),
            },
            {
                "name": "agencies_reporting",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "example": 12,
                "short_description": (
                    "Agencies in the geography that reported at least one "
                    "hate crime that year — a coverage companion, NOT a "
                    "participation roster."
                ),
                "description": (
                    "Coverage companion: the number of distinct agencies "
                    "(by primary county on county rows; statewide on state "
                    "rows) that reported AT LEAST ONE hate-crime incident "
                    "in the year. The source file contains no participation "
                    "roster, so agencies that participated but reported "
                    "zero hate crimes are indistinguishable from "
                    "non-participants — this counts agencies with reports, "
                    "not agencies covered. Constant across bias motivations "
                    "within a county-year. Essential context: Georgia went "
                    "from about 2-11 reporting agencies per year "
                    "(1991-2018) to 71-82 (2019-2021), then declined to 45 "
                    "by 2024 — trends largely track reporting coverage."
                ),
            },
        ],
        source="FBI Crime Data Explorer, national hate crime master file",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        suppressed_to_null=False,
        usage=(
            "Cite the FBI Crime Data Explorer (cde.ucr.cjis.gov) hate crime "
            "data collection. Counts are raw voluntary agency reports: "
            "never interpret an absent county-year (or a low count) as low "
            "hate-crime incidence — under-reporting is severe and "
            "participation varies sharply by year (read alongside "
            "agencies_reporting). Sum incident_count across counties "
            "freely; never sum across bias motivations (multi-bias "
            "incidents are counted once per bias). Rates require an "
            "external population denominator (not served here)."
        ),
        limitations=(
            "State rows have NULL county_fips. Hate-crime reporting is "
            "voluntary and notoriously under-reported: a county-year with "
            "no row means no reports were submitted, never that no hate "
            "crime occurred, and absent county-years are deliberately left "
            "absent rather than zero-filled. Agency participation varies "
            "sharply by year (about 2-11 Georgia agencies through 2018, "
            "71-82 in 2019-2021, 45 by 2024, driven by the NIBRS "
            "transition), so year-over-year change largely reflects "
            "reporting coverage; pre-2019 county coverage is dominated by "
            "a handful of large agencies. The file has no participation "
            "roster and no reporting-program field, so no coverage flag "
            "column is possible — agencies_reporting counts only agencies "
            "with at least one report. Incidents are attributed to the "
            "reporting agency's primary county (agencies spanning multiple "
            "counties are not split; Atlanta PD is attributed to Fulton), "
            "which follows the agency, not the incident location. "
            "Multi-bias incidents are counted once under each bias "
            "motivation, so bias-level counts sum slightly above the "
            "distinct-incident total. Victim counts cover individual "
            "(human) victims only; offender counts cover known offenders "
            "only. No demographic breakdowns are served: the file carries "
            "offender race/ethnicity, but offender demographics do not "
            "share the victim/population semantics of the demographics "
            "dimension. The FBI publishes hate-crime counts unsuppressed."
        ),
        quality_checks=[
            {
                "name": "incident_count_at_least_one",
                "description": (
                    "Rows exist only for county-year-bias combinations with "
                    "at least one reported incident — a zero or negative "
                    "count means the aggregation broke."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE incident_count IS "
                    "NULL OR incident_count < 1"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_incident_total_covers_county_sum",
                "description": (
                    "The state row counts ALL agencies (including any "
                    "statewide agency with no county), so for every (year, "
                    "bias_motivation) with county rows a state row must "
                    "exist with incident_count >= the county sum (equal "
                    "today; a statewide-agency report would make it "
                    "strictly greater)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, bias_motivation, "
                    "MAX(CASE WHEN county_fips IS NULL THEN incident_count "
                    "END) AS state_total, "
                    "SUM(CASE WHEN county_fips IS NOT NULL THEN "
                    "incident_count END) AS county_sum "
                    "FROM {object} GROUP BY year, bias_motivation"
                    ") WHERE county_sum IS NOT NULL AND (state_total IS "
                    "NULL OR state_total < county_sum)"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_known_offender_total_covers_county_sum",
                "description": (
                    "known_offender_count is a plain sum over incidents, so "
                    "the state row must be >= the county sum for every "
                    "(year, bias_motivation) — equal today, strictly "
                    "greater only if a statewide agency ever reports."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, bias_motivation, "
                    "MAX(CASE WHEN county_fips IS NULL THEN "
                    "known_offender_count END) AS state_total, "
                    "SUM(CASE WHEN county_fips IS NOT NULL THEN "
                    "known_offender_count END) AS county_sum "
                    "FROM {object} GROUP BY year, bias_motivation"
                    ") WHERE county_sum IS NOT NULL AND (state_total IS "
                    "NULL OR state_total < county_sum)"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_victim_total_covers_county_sum",
                "description": (
                    "victim_count is a plain sum over incidents, so the "
                    "state row must be >= the county sum for every (year, "
                    "bias_motivation). NULL-aware: the check only binds "
                    "where both cells are non-NULL — NULL propagation means "
                    "a state cell containing any NULL-victim incident is "
                    "itself NULL and exempt."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, bias_motivation, "
                    "MAX(CASE WHEN county_fips IS NULL THEN "
                    "victim_count END) AS state_total, "
                    "SUM(CASE WHEN county_fips IS NOT NULL THEN "
                    "victim_count END) AS county_sum "
                    "FROM {object} GROUP BY year, bias_motivation"
                    ") WHERE county_sum IS NOT NULL AND state_total IS "
                    "NOT NULL AND state_total < county_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "bias_motivation_determines_category",
                "description": (
                    "bias_category is a denormalized attribute of "
                    "bias_motivation (pinned national vocabulary) — each "
                    "bias_motivation must map to exactly one category, or "
                    "category rollups would double count."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT bias_motivation, "
                    "COUNT(DISTINCT bias_category) AS nc "
                    "FROM {object} GROUP BY bias_motivation"
                    ") WHERE nc > 1"
                ),
                "mustBe": 0,
            },
            {
                "name": "agencies_reporting_constant_within_year_county",
                "description": (
                    "agencies_reporting describes the geography's reporting "
                    "agencies for the year, not the bias motivation — it "
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
                    "Every row's incidents came from at least one reporting "
                    "agency in the geography."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE agencies_reporting "
                    "IS NULL OR agencies_reporting < 1"
                ),
                "mustBe": 0,
            },
            {
                "name": "agencies_reporting_not_exceeding_incident_sum",
                "description": (
                    "Each counted agency reported at least one incident, "
                    "and summing incident_count over bias motivations only "
                    "overstates distinct incidents, so agencies_reporting "
                    "<= the (year, county) incident_count sum."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, "
                    "MAX(agencies_reporting) AS agencies, "
                    "SUM(incident_count) AS incident_sum "
                    "FROM {object} GROUP BY year, county_fips"
                    ") WHERE agencies > incident_sum"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
