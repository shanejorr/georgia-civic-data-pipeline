"""Transform the FBI CDE law-enforcement-employees file into a gold fact table.

Source: FBI Crime Data Explorer "Law Enforcement Employees" (LEE / Police
Employee) bulk file — one NATIONAL agency x year staffing snapshot per row,
1960-2025 (``lee_1960_2025.csv``). Filtered to Georgia (26,180 of 785,127
rows; the national remainder is out of topic scope, not a data-quality
filter) and aggregated to county x year x demographic (sex), plus a
statewide rollup.

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Grain: year x county_fips x demographic (all / male / female).** Bronze
  publishes nine exact-partition counts per agency (male/female/total for
  officers, civilians, and all employees; verified exact on all 26,180 GA
  rows — zero violations). The sex splits are served tidy per §5a: a
  ``demographic`` column with mutually exclusive ``male`` / ``female`` rows
  plus the ``all`` aggregate row, never wide sex-prefixed columns. All nine
  bronze counts are exactly recoverable from the three metric columns x
  three demographic rows.
- **County attribution: ORI -> primary county, statewide agencies to state
  only.** Agencies join ``data/gold/crosswalks/ori_to_county.parquet``
  (full coverage: all 817 GA ORIs resolve; hard-fail if a future release
  adds one the crosswalk lacks). Multi-county agencies (41 ORIs, 1,531
  agency-years) are attributed wholly to their PRIMARY county — never
  split, never double-counted. The 12 statewide ORIs with NULL crosswalk
  county (GBI HQ + field offices, State Patrol HQ, Ports Authority; 113
  agency-years) contribute to state rows only — unlike the NIBRS siblings
  these DO carry employees (GSP HQ alone reports ~32k officer-years), so
  the state total strictly exceeds the county sum in most years (authored
  invariant: state >= county sum).
- **Source header typo ``cilvilian``.** Bronze spells the civilian columns
  ``male_cilvilian_ct`` / ``female_cilvilian_ct``. Era detection is by
  column signature: the typo header maps to the corrected ``civilian``
  spelling, and a hypothetical future release that fixes the typo is
  detected as its own era instead of silently NULLing the columns. The
  recode is visible in the manifest era name.
- **``population`` and ``pe_ct_per_1000`` are EXCLUDED (judgment call).**
  ``population`` is each agency's own service population, and agency
  jurisdictions overlap: a city PD's residents are also inside the
  sheriff's county jurisdiction, and UCR avoids the double count by
  attributing overlapping population to one ORI ("0 = population attributed
  to another agency"), so a county sum of agency populations is neither a
  census count nor internally consistent across years (it shifts with the
  reporting roster, not with residents). Summing it would invite bogus
  per-capita rates. It is excluded; consumers needing a denominator should
  use Census county population. ``pe_ct_per_1000`` is derived from it
  (total_pe / population x 1000, verified to rounding) and is excluded for
  the same reason. ``agencies_reporting`` is served instead as the coverage
  companion.
- **Voluntary reporting — coverage varies by year, never zero-filled.** UCR
  police-employee reporting is voluntary: 44-76 GA agencies reported in the
  1960s vs ~350-530 from 2014 on. A county-year with no reporting agency
  simply has no row (absent, never zero), and every row carries
  ``agencies_reporting`` (the count of agencies aggregated into the cell)
  so consumers can separate staffing change from reporting-coverage change.
  This file is the UCR program from 1960 on — the Oct-2019 SRS->NIBRS
  transition flag used by the NIBRS-master siblings does NOT apply here.
- **238 zero-employee agency-years preserved.** ``total_pe_ct == 0`` rows
  are agencies that filed a zero report (defunct/merged/contract-policing
  agencies) — extreme-but-conceivable per §4b, so they are preserved (they
  still count toward ``agencies_reporting``) and documented, not masked.
- **Seven provably-erroneous agency-year filings excluded (§4b).** Four
  known-bad source filings (identified in data review) are dropped
  pre-aggregation via the pinned ``KNOWN_BAD_AGENCY_YEARS`` screen, each
  recorded on the manifest as an explicit filter event and documented in
  the contract limitations: the "GDC Internal Affairs" ORI filing the
  entire Department of Corrections' statewide staffing in 1994/1995/1998
  (identical 9,334/4,852/14,186 triple vs 17 officers in 1999 — inflated
  Fulton ~3.4x and the state rows ~45%); the GSP Valdosta post duplicating
  the statewide GSP HQ filing in 1993/1994 (844/1,974 vs HQ's 845/1,976
  the same years — double-counted the State Patrol and inflated Lowndes
  5.4x); Bowdon 2016 (467 officers for a town of 2,078 vs 6-8 in all
  neighboring years); and Cobb County Park Rangers 2001 (508 officers
  duplicating Cobb County PD's same-year 537 vs the rangers' historic
  13-14). Beyond these, all nine count columns are clean non-negative
  Int64 on the GA subset (zero nulls, zero negatives) and the source has
  no suppression (``suppressed_to_null=False``).
- **Dedup tie-break.** Bronze ``ori x data_year`` is unique (verified, 0
  duplicates) and the single-pass aggregation cannot emit duplicate keys,
  so duplicates are impossible by construction;
  ``deduplicate_by_levels(sort_col="officer_count")`` remains the
  documented safety net (prefer the fuller row) should a future refresh
  add overlapping files. The collision guard runs first and hard-fails on
  any divergent duplicate rather than letting dedup pick a winner.
- **Agency attributes stay out of gold.** ``pub_agency_name`` /
  ``pub_agency_unit`` / ``agency_type_name`` / ``population_group_desc``
  are attributes of a (future) agencies dimension, not of a county-grain
  fact; ``county_name`` is superseded by the crosswalk (its comma-joined
  multi-county values and ``NOT SPECIFIED`` sentinel make it a secondary
  signal only).
"""

import logging
from pathlib import Path

import polars as pl

from src.etl.criminal_justice.fbi_cde._nibrs_shared import load_ori_county_crosswalk
from src.utils.demographics import DEMOGRAPHIC_ALIASES, normalize_demographic_column
from src.utils.metadata import write_data_dictionary
from src.utils.readers import read_bronze_file
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

TOPIC = "law_enforcement_employees"
BRONZE_DIR = Path("data/bronze/criminal_justice/fbi_cde/law_enforcement_employees")
GOLD_DIR = Path("data/gold/criminal_justice/law_enforcement_employees")
SOURCE_URL = "https://cde.ucr.cjis.gov"

# Era detection by column signature. The published header misspells the
# civilian columns ("cilvilian"); if a future release silently fixes the
# typo, the corrected spelling is its own era rather than a silent NULL
# (bronze-data-structure.md: "select columns defensively").
ERA_SIGNATURES: dict[str, list[str]] = {
    "lee_v1_cilvilian_typo_header": ["male_cilvilian_ct"],
    "lee_v2_corrected_header": ["male_civilian_ct"],
}

# Bronze count column -> corrected working name, per era. Only the civilian
# columns differ (the source typo); everything else is shared.
SHARED_COUNT_RENAMES: dict[str, str] = {
    "male_officer_ct": "male_officer",
    "male_total_ct": "male_total",
    "female_officer_ct": "female_officer",
    "female_total_ct": "female_total",
    "officer_ct": "all_officer",
    "civilian_ct": "all_civilian",
    "total_pe_ct": "all_total",
}
ERA_COUNT_RENAMES: dict[str, dict[str, str]] = {
    "lee_v1_cilvilian_typo_header": {
        **SHARED_COUNT_RENAMES,
        # Source header typo "cilvilian" -> corrected "civilian" spelling.
        "male_cilvilian_ct": "male_civilian",
        "female_cilvilian_ct": "female_civilian",
    },
    "lee_v2_corrected_header": {
        **SHARED_COUNT_RENAMES,
        "male_civilian_ct": "male_civilian",
        "female_civilian_ct": "female_civilian",
    },
}

# Tidy layout: raw sex label -> the per-agency working columns holding that
# slice's (officer, civilian, total) counts. "All" is the aggregate lane
# (§5a): male + female partition it exactly (verified on all GA rows).
DEMOGRAPHIC_SLICES: dict[str, tuple[str, str, str]] = {
    "All": ("all_officer", "all_civilian", "all_total"),
    "Male": ("male_officer", "male_civilian", "male_total"),
    "Female": ("female_officer", "female_civilian", "female_total"),
}

METRIC_COLUMNS: list[str] = [
    "officer_count",
    "civilian_count",
    "total_employee_count",
    "agencies_reporting",
]

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "county_fips",
    "demographic",
    *METRIC_COLUMNS,
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "county_fips": pl.Utf8,
    "demographic": pl.Utf8,
    **{c: pl.Int64 for c in METRIC_COLUMNS},
    "detail_level": pl.Utf8,
}

NATURAL_KEYS: list[str] = ["year", "county_fips", "demographic", "detail_level"]

# §4b known-bad screen: provably erroneous single-agency filings, pinned by
# (ori, data_year) and dropped BEFORE aggregation (data-review-claude.md
# Fixes 1-4). Each is either a whole-department misfiling under a small
# unit's ORI, a same-year duplicate of another agency's filing, or an
# impossible headcount for the jurisdiction — all verified against the
# agency's own bronze time series. Dropped rows are recorded on the
# manifest as explicit filter events and documented in the contract
# limitations. A pin that no longer matches bronze (e.g. the source fixes
# the filing upstream) logs a stale-pin warning instead of failing.
KNOWN_BAD_AGENCY_YEARS: dict[tuple[str, int], str] = {
    ("GA0603200", 1994): (
        "GDC Internal Affairs filed the whole Department of Corrections "
        "(9,334/4,852/14,186; the unit itself reports 17/3/20 in 1999)"
    ),
    ("GA0603200", 1995): (
        "GDC Internal Affairs filed the whole Department of Corrections "
        "(identical 9,334/4,852/14,186 triple repeated from 1994)"
    ),
    ("GA0603200", 1998): (
        "GDC Internal Affairs filed the whole Department of Corrections "
        "(identical 9,334/4,852/14,186 triple; global maxima of the file)"
    ),
    ("GAGSP3100", 1993): (
        "GSP Valdosta post duplicated the statewide GSP HQ filing "
        "(844 officers/1,974 total vs HQ's 845/1,976 the same year; the "
        "post itself files 19-25 in 1996-98)"
    ),
    ("GAGSP3100", 1994): (
        "GSP Valdosta post duplicated the statewide GSP HQ filing "
        "(844 officers/1,974 total; the post itself files 19-25 in 1996-98)"
    ),
    ("GA0220300", 2016): (
        "Bowdon PD filed 467 officers/260 civilians for a service "
        "population of 2,078 (6-8 officers in all neighboring years)"
    ),
    ("GA0331400", 2001): (
        "Cobb County Park Rangers filed 508 officers/564 total, a "
        "near-duplicate of Cobb County PD's same-year 537/627 (rangers "
        "historically file 13-14)"
    ),
}


# =============================================================================
# Bronze load + transform
# =============================================================================


def _load_georgia_agency_years(manifest: TransformManifest) -> pl.DataFrame:
    """Read the national LEE file and return clean GA agency-year rows.

    Returns one row per (ori, year) with Int64 working count columns
    (typo-corrected names) — the topic's bronze row concept is the GA
    subset (the national remainder is out of scope, logged not recorded).
    """
    paths = sorted(BRONZE_DIR.glob("lee_*.csv"))
    if len(paths) != 1:
        raise ValueError(f"Expected exactly one lee_*.csv in {BRONZE_DIR}: {paths}")
    path = paths[0]

    # All-string read (4.3b): the file carries literal "NULL" sentinels
    # (pub_agency_unit, pe_ct_per_1000) and zero-padded ORIs; cast explicitly.
    df, loss = read_bronze_file(
        path, return_loss=True, infer_schema_length=0, null_values={"NULL"}
    )

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{path.name}: no era signature matched {df.columns}")
    renames = ERA_COUNT_RENAMES[era]
    expected = ["data_year", "ori", "state_abbr", *renames]
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: missing expected column(s) {missing}")

    # Scope filter, not a quality filter: the file is national; this topic
    # serves Georgia. 26,180 of 785,127 rows survive (structure doc).
    ga = df.filter(pl.col("state_abbr") == "GA")
    logger.info(
        "%s: filtered national file to Georgia — kept %d of %d rows (era %s)",
        path.name,
        ga.height,
        df.height,
        era,
    )
    if ga.height == 0:
        raise ValueError(f"{path.name}: zero Georgia rows after the state filter")

    latest_year = int(ga["data_year"].cast(pl.Int32).max())
    manifest.record_read_loss(
        latest_year, path.name, loss["raw_rows"], loss["parsed_rows"]
    )
    manifest.record_file(path, latest_year, era, ga.height, df.columns)
    # Per-year bronze counts (GA agency rows) — the year axis lives inside
    # the single file, so record_bronze runs per data_year, not per file.
    for row in (
        ga.group_by(pl.col("data_year").cast(pl.Int32))
        .len()
        .sort("data_year")
        .iter_rows()
    ):
        manifest.record_bronze(int(row[0]), int(row[1]))

    ga = ga.select(
        pl.col("data_year").cast(pl.Int32).alias("year"),
        pl.col("ori"),
        *[
            # Strict cast: the structure doc verified all nine count columns
            # are clean integers on the GA subset — a cast failure means the
            # source changed and must be investigated, not silently NULLed.
            pl.col(src).cast(pl.Int64).alias(dst)
            for src, dst in renames.items()
        ],
    )
    if ga.height != ga.select("ori", "year").unique().height:
        raise ValueError("LEE bronze grain violated: duplicate (ori, year) rows")
    return _drop_known_bad_filings(ga, manifest)


def _drop_known_bad_filings(
    ga: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Drop the pinned provably-erroneous agency-year filings (§4b).

    Whole-department misfilings, same-year duplicates of another agency's
    filing, and impossible headcounts (see ``KNOWN_BAD_AGENCY_YEARS``)
    would otherwise inflate their county-year 2.7-5.4x and the state rows
    up to ~45%. Each drop is recorded as an explicit manifest filter
    event; a pin absent from bronze logs a stale-pin warning.
    """
    for (ori, year), reason in KNOWN_BAD_AGENCY_YEARS.items():
        mask = (pl.col("ori") == ori) & (pl.col("year") == year)
        n_bad = ga.filter(mask).height
        if n_bad == 0:
            logger.warning(
                "Known-bad pin (%s, %d) not found in bronze — stale pin? "
                "Check whether the source fixed the filing upstream.",
                ori,
                year,
            )
            continue
        ga = ga.filter(~mask)
        manifest.record_filtered(
            year, n_bad, f"known-bad filing (§4b): {ori} {year} — {reason}"
        )
        logger.info(
            "Dropped known-bad filing %s %d (%d row): %s", ori, year, n_bad, reason
        )
    return ga


def _attach_county(agencies: pl.DataFrame, manifest: TransformManifest) -> pl.DataFrame:
    """Join agency-years -> ORI -> primary county via the shared crosswalk.

    Every ORI must exist in the crosswalk — anything unmatched hard-fails
    (never silently NULLed). A NULL county_fips after a successful match
    marks a statewide agency (GBI, State Patrol HQ, Ports Authority):
    those roll up to state rows only.
    """
    crosswalk = load_ori_county_crosswalk()
    unmatched = agencies.join(crosswalk, on="ori", how="anti")
    if unmatched.height:
        raise ValueError(
            "ORIs missing from ori_to_county crosswalk — rebuild it: "
            f"{unmatched['ori'].unique().sort().to_list()}"
        )
    joined = agencies.join(
        crosswalk.select("ori", "county_fips", "multi_county"), on="ori", how="left"
    )

    statewide = joined.filter(pl.col("county_fips").is_null())
    if statewide.height:
        # Unlike the NIBRS siblings, statewide agencies DO carry employees
        # here (GSP HQ ~32k officer-years) — state rows strictly exceed the
        # county sum. Log the slice so the review can tie it out.
        logger.info(
            "%d agency-years from %d statewide (no-county) agencies count "
            "toward state rows only (%s)",
            statewide.height,
            statewide["ori"].n_unique(),
            statewide["ori"].unique().sort().to_list(),
        )
    multi = joined.filter(pl.col("multi_county"))
    if multi.height:
        logger.info(
            "%d agency-years from %d multi-county agencies; each is "
            "attributed wholly to its primary county",
            multi.height,
            multi["ori"].n_unique(),
        )

    # Manifest: the ORI -> primary-county attribution is the topic's
    # geography recode; record the slice actually observed (4.3a-style).
    ori_map = {
        row["ori"]: (row["county_fips"] or "unassigned_statewide")
        for row in joined.select("ori", "county_fips").unique().to_dicts()
    }
    manifest.record_categorical(
        column="county_fips",
        map_dict=ori_map,
        bronze_series=joined["ori"],
        gold_series=joined["county_fips"],
    )
    return joined.drop("multi_county")


def _tidy_demographics(wide: pl.DataFrame, manifest: TransformManifest) -> pl.DataFrame:
    """Unpivot the nine wide sex-split sums into tidy demographic rows.

    One sub-frame per sex slice (§9: multiple metrics per category), with
    the raw label normalized through the shared demographic aliases (§5).
    male + female partition the all row exactly (authored quality check).
    """
    slice_prefixes = ("all_", "male_", "female_")
    key_cols = [
        c for c in wide.columns if not any(c.startswith(p) for p in slice_prefixes)
    ]
    frames = []
    for raw_label, (officer, civilian, total) in DEMOGRAPHIC_SLICES.items():
        frames.append(
            wide.select(
                *key_cols,
                pl.lit(raw_label).alias("demographic_raw"),
                pl.col(officer).alias("officer_count"),
                pl.col(civilian).alias("civilian_count"),
                pl.col(total).alias("total_employee_count"),
            )
        )
    tidy = pl.concat(frames).with_columns(
        normalize_demographic_column("demographic_raw").alias("demographic")
    )
    # Record the effective alias slice (4.3a): only the labels this topic
    # actually feeds through DEMOGRAPHIC_ALIASES, keeping map_used reviewable.
    manifest.record_categorical(
        column="demographic",
        map_dict={
            label: DEMOGRAPHIC_ALIASES[label.upper()] for label in DEMOGRAPHIC_SLICES
        },
        bronze_series=tidy["demographic_raw"],
        gold_series=tidy["demographic"],
    )
    return tidy.drop("demographic_raw")


def _aggregate(agencies: pl.DataFrame) -> pl.DataFrame:
    """Aggregate agency-years to county and state grain (wide, then tidy).

    County rows sum agencies attributed to that (primary) county; state
    rows sum ALL reporting agencies including the statewide (no-county)
    ones, so state >= county sum structurally. agencies_reporting counts
    the agency rows aggregated into the cell (grain-unique per ori-year),
    zero-report agencies included — it describes reporting coverage.
    """
    sum_cols = [c for cols in DEMOGRAPHIC_SLICES.values() for c in cols]
    aggs = [
        *[pl.col(c).sum() for c in sum_cols],
        pl.len().cast(pl.Int64).alias("agencies_reporting"),
    ]
    county = (
        agencies.filter(pl.col("county_fips").is_not_null())
        .group_by("year", "county_fips")
        .agg(aggs)
        .with_columns(pl.lit("county").alias("detail_level"))
    )
    state = (
        agencies.group_by("year")
        .agg(aggs)
        .with_columns(
            pl.lit(None).cast(pl.Utf8).alias("county_fips"),
            pl.lit("state").alias("detail_level"),
        )
    )
    return pl.concat([county, state.select(county.columns)], how="vertical")


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for law_enforcement_employees."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read the national file, filter to GA, correct the typo header.
    agencies = _load_georgia_agency_years(manifest)

    # 2. ORI -> primary county (statewide agencies to state rows only).
    agencies = _attach_county(agencies, manifest)

    # 3. Aggregate to county + state grain, then tidy the sex splits.
    combined = _tidy_demographics(_aggregate(agencies), manifest)
    logger.info(
        "Aggregated %d agency-years into %d gold rows", agencies.height, combined.height
    )

    # 4. Harmonize, collision guard, THEN dedup.
    combined = pl.concat(harmonize_columns([combined], STANDARD_COLUMNS, TARGET_TYPES))
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: bronze (ori, year) is unique and the aggregation is
    # single-pass over one file, so duplicate keys are impossible by
    # construction; sort_col "officer_count" is the documented safety net
    # (prefer the fuller row) should a future refresh add overlapping files.
    combined = deduplicate_by_levels(
        combined,
        {
            "county": ["year", "county_fips", "demographic"],
            "state": ["year", "demographic"],
        },
        sort_col="officer_count",
    )

    # 5. Geography nulling (shared domain rules; state rows already NULL).
    # No cell-level §4b masks apply here: the known-bad screen already ran
    # pre-aggregation (KNOWN_BAD_AGENCY_YEARS); the surviving counts are
    # clean non-negative Int64 and sums cannot manufacture impossible values.
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
        "Done. Bronze agency-years: %s; gold rows: %s; years: %s",
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
        description=(
            "Law-enforcement staffing in Georgia from the FBI's Uniform "
            "Crime Reporting police-employee (LEE) collection: sworn "
            "officers and civilian employees per county and year, 1960 "
            "onward, split by sex (male / female / all), as-reported head "
            "counts (typically October 31). Reporting is voluntary and "
            "coverage grew over time — 44-76 Georgia agencies reported per "
            "year in the 1960s vs roughly 350-530 from 2014 on — so every "
            "row carries an agencies_reporting companion count and "
            "county-years with no reporting agency are absent, never "
            "zero-filled: long-run change mixes staffing change with "
            "reporting-coverage change. Employees are attributed to the "
            "reporting agency's primary county via the ORI-to-county "
            "crosswalk; statewide agencies (GBI, State Patrol, Ports "
            "Authority) count toward state rows only, so the state total "
            "exceeds the county sum."
        ),
        title="Law Enforcement Employees by County",
        summary=(
            "Sworn-officer and civilian staffing of Georgia law-enforcement "
            "agencies (FBI UCR police-employee data), by county, year, and "
            "sex, 1960 onward."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2025,
                "description": (
                    "Calendar year of the staffing snapshot (typically an "
                    "October 31 head count)."
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
                    "spanning multiple counties are attributed wholly to "
                    "their primary county; statewide agencies with no "
                    "primary county (GBI, State Patrol, Ports Authority) "
                    "count toward state rows only, so the state row "
                    "exceeds the county sum."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "validValues": ["all", "female", "male"],
                "example": "all",
                "description": (
                    "Employee sex: male and female partition each count "
                    "exactly (male + female = all); the all row is the "
                    "aggregate lane. Filter demographic = 'all' for "
                    "headline staffing totals and exclude it when summing "
                    "across sexes."
                ),
            },
            {
                "name": "officer_count",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "key_metric": True,
                "example": 1748,
                "short_description": (
                    "Sworn officers employed by the county's reporting "
                    "agencies in the year."
                ),
                "description": (
                    "Full-time sworn law-enforcement officers employed by "
                    "agencies attributed to the county at the annual "
                    "snapshot, for the row's sex slice. As-reported "
                    "voluntary UCR counts — interpret trends alongside "
                    "agencies_reporting, especially before the 2010s. A "
                    "small number of agency-years report zero employees "
                    "(defunct or merged agencies filing zero reports); "
                    "these are preserved as reported."
                ),
            },
            {
                "name": "civilian_count",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "example": 512,
                "description": (
                    "Full-time civilian (non-sworn) employees of agencies "
                    "attributed to the county at the annual snapshot, for "
                    "the row's sex slice. officer_count + civilian_count = "
                    "total_employee_count."
                ),
            },
            {
                "name": "total_employee_count",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "example": 2260,
                "description": (
                    "Total police employees (sworn officers plus civilian "
                    "employees) of agencies attributed to the county, for "
                    "the row's sex slice. Equals officer_count + "
                    "civilian_count exactly."
                ),
            },
            {
                "name": "agencies_reporting",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "example": 18,
                "short_description": (
                    "Law-enforcement agencies that filed a police-employee "
                    "report for the year (county roster on county rows, "
                    "statewide roster on state rows)."
                ),
                "description": (
                    "Coverage companion: the number of agencies whose "
                    "report is aggregated into the row — for county rows, "
                    "agencies whose primary county is this county; for "
                    "statewide rows, all reporting Georgia agencies "
                    "(including statewide agencies with no primary "
                    "county). Constant across the sex slices of a "
                    "county-year (it describes the reporting roster, not "
                    "the sex split). Reporting is voluntary: 44-76 "
                    "agencies per year in the 1960s vs ~350-530 from 2014 "
                    "on, so rising staffing counts partly reflect rising "
                    "coverage. Zero-employee reports still count as "
                    "reporting."
                ),
            },
        ],
        source="FBI Crime Data Explorer, Law Enforcement Employees (LEE) bulk file",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        suppressed_to_null=False,
        usage=(
            "Cite the FBI Crime Data Explorer (cde.ucr.cjis.gov), Law "
            "Enforcement Employees data. Counts are voluntary as-reported "
            "head counts: read any trend alongside agencies_reporting "
            "(coverage grew roughly tenfold between the 1960s and the "
            "2010s), and never treat a missing county-year as zero "
            "staffing. Filter demographic = 'all' for totals; male and "
            "female rows partition every count exactly. Per-capita "
            "staffing rates require an external population denominator "
            "such as Census county population — agency jurisdiction "
            "populations overlap (a city's residents are also in the "
            "sheriff's county jurisdiction) and are deliberately not "
            "served."
        ),
        limitations=(
            "State rows have NULL county_fips. Reporting is voluntary and "
            "coverage varies by year (44-76 Georgia agencies in the 1960s "
            "vs ~350-530 from 2014 on): county-years with no reporting "
            "agency are absent rather than zero, and long-run comparisons "
            "mix staffing change with coverage change — use "
            "agencies_reporting to separate them. Employees are attributed "
            "to the reporting agency's primary county: multi-county "
            "agencies are not split, and statewide agencies (GBI, State "
            "Patrol, Ports Authority) appear in state rows only, so the "
            "state row strictly exceeds the county sum in most years. Other "
            "agencies with statewide or regional operations but a primary "
            "county on file (e.g. DOT police, DNR region offices, MARTA "
            "transit police) are counted in their headquarters county — "
            "mostly Fulton, roughly 270 of Fulton's ~4,000 officers in "
            "2024. The "
            "source's agency service-population column (and the derived "
            "employees-per-1,000 rate) is deliberately excluded: "
            "overlapping city/county jurisdictions make county sums of "
            "agency populations meaningless as a denominator. A small "
            "number of agency-years report zero employees and are "
            "preserved as reported. The source has no suppression. Seven "
            "provably erroneous agency-year filings are excluded from the "
            "aggregates: a Department of Corrections unit that filed the "
            "entire department's statewide staffing under Fulton County in "
            "1994, 1995, and 1998; a State Patrol post that duplicated the "
            "statewide State Patrol filing under Lowndes County in 1993 "
            "and 1994; an impossible Bowdon 2016 filing (Carroll County); "
            "and a Cobb County Park Rangers 2001 filing duplicating the "
            "county police department's. Occasional implausible "
            "single-agency filings may survive in this voluntary "
            "as-reported source."
        ),
        quality_checks=[
            {
                "name": "officer_plus_civilian_equals_total",
                "description": (
                    "Sworn officers and civilian employees partition total "
                    "police employees, so the two components must sum "
                    "exactly to total_employee_count on every row (exact "
                    "in bronze on all Georgia agency-years)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE officer_count IS "
                    "NOT NULL AND civilian_count IS NOT NULL AND "
                    "total_employee_count IS NOT NULL AND officer_count + "
                    "civilian_count != total_employee_count"
                ),
                "mustBe": 0,
            },
            {
                "name": "sex_partition_sums_to_all",
                "description": (
                    "male and female rows partition every count exactly "
                    "(§5a): within each year-county cell, male + female "
                    "must equal the all row for officer_count, "
                    "civilian_count, and total_employee_count."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, "
                    "MAX(CASE WHEN demographic = 'all' THEN officer_count END)"
                    " AS a_off, "
                    "MAX(CASE WHEN demographic = 'male' THEN officer_count END)"
                    " AS m_off, "
                    "MAX(CASE WHEN demographic = 'female' THEN officer_count END)"
                    " AS f_off, "
                    "MAX(CASE WHEN demographic = 'all' THEN civilian_count END)"
                    " AS a_civ, "
                    "MAX(CASE WHEN demographic = 'male' THEN civilian_count END)"
                    " AS m_civ, "
                    "MAX(CASE WHEN demographic = 'female' THEN civilian_count END)"
                    " AS f_civ, "
                    "MAX(CASE WHEN demographic = 'all' THEN total_employee_count END)"
                    " AS a_tot, "
                    "MAX(CASE WHEN demographic = 'male' THEN total_employee_count END)"
                    " AS m_tot, "
                    "MAX(CASE WHEN demographic = 'female' THEN total_employee_count "
                    "END) AS f_tot "
                    "FROM {object} GROUP BY year, county_fips"
                    ") WHERE (a_off IS NOT NULL AND m_off IS NOT NULL AND "
                    "f_off IS NOT NULL AND m_off + f_off != a_off) OR "
                    "(a_civ IS NOT NULL AND m_civ IS NOT NULL AND f_civ IS "
                    "NOT NULL AND m_civ + f_civ != a_civ) OR "
                    "(a_tot IS NOT NULL AND m_tot IS NOT NULL AND f_tot IS "
                    "NOT NULL AND m_tot + f_tot != a_tot)"
                ),
                "mustBe": 0,
            },
            {
                "name": "three_demographic_rows_per_cell",
                "description": (
                    "Every year-county cell (and every statewide year "
                    "cell) is emitted with exactly its all, male, and "
                    "female rows — a different count means the tidy "
                    "unpivot broke."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, COUNT(*) AS n "
                    "FROM {object} GROUP BY year, county_fips"
                    ") WHERE n != 3"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_total_covers_county_sum",
                "description": (
                    "The state row sums ALL reporting agencies including "
                    "statewide (no-county) agencies like the State Patrol "
                    "and GBI, so for every year the state officer_count at "
                    "demographic = 'all' must be >= the county sum "
                    "(strictly greater whenever a statewide agency "
                    "reported)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, "
                    "MAX(CASE WHEN county_fips IS NULL THEN officer_count "
                    "END) AS state_total, "
                    "SUM(CASE WHEN county_fips IS NOT NULL THEN "
                    "officer_count END) AS county_sum "
                    "FROM {object} WHERE demographic = 'all' GROUP BY year"
                    ") WHERE county_sum IS NOT NULL AND (state_total IS "
                    "NULL OR state_total < county_sum)"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_agencies_reporting_covers_county_sum",
                "description": (
                    "The statewide reporting roster includes every "
                    "county-attributed agency plus the statewide agencies, "
                    "so per year the state agencies_reporting must be >= "
                    "the sum of county agencies_reporting."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, "
                    "MAX(CASE WHEN county_fips IS NULL THEN "
                    "agencies_reporting END) AS state_n, "
                    "SUM(CASE WHEN county_fips IS NOT NULL THEN "
                    "agencies_reporting END) AS county_n "
                    "FROM {object} WHERE demographic = 'all' GROUP BY year"
                    ") WHERE county_n IS NOT NULL AND (state_n IS NULL OR "
                    "state_n < county_n)"
                ),
                "mustBe": 0,
            },
            {
                "name": "agencies_reporting_constant_within_year_county",
                "description": (
                    "agencies_reporting describes the year's reporting "
                    "roster for the geography, not the sex slice — it must "
                    "be identical on the all, male, and female rows of a "
                    "year-county cell."
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
                    "Rows exist only for county-years (or state-years) "
                    "with at least one filed report — a zero or NULL "
                    "roster count means the aggregation broke."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "agencies_reporting IS NULL OR agencies_reporting < 1"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
