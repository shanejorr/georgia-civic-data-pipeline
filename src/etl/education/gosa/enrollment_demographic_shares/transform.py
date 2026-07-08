"""Transform the shared enrollment_by_subgroup_programs bronze into tidy
demographic-share gold (``enrollment_demographic_shares``).

Source: Governor's Office of Student Achievement (GOSA) — "Enrollment by
Subgroup Programs", 21 files spanning school years 2003-04 through 2023-24.
This DERIVED topic exposes the demographic-share side of that publication:
for every Georgia public school, district, and the state, the share of
enrollment in each of 12 demographic subgroups. The sibling topic
``enrollment_program_participation`` exposes the program side of the SAME
bronze files; all bronze reading/era/ID/scaling logic both topics must agree
on lives in ``_enrollment_subgroup_programs_shared``.

Design decisions (clean-room from bronze-data-structure.md + standards;
every bronze claim re-verified 2026-06-11):

- **Tidy long unpivot.** The 12 wide ``pct_<demographic>`` columns become
  one row per (year, district_code, school_code, demographic). Expansion
  factor is exactly 12x the (deduplicated) wide row count.
- **Uniform demographic grid.** Era gaps (pre-2011 bronze has no migrant /
  male / female columns; 2012-2017 bronze drops male/female) emit rows with
  ``enrollment_ratio = NULL`` rather than dropping the rows, so every
  entity-year carries the same 12 demographics. Pinned by the
  ``twelve_demographic_rows_per_entity`` and ``era_gap_demographics_null``
  quality checks.
- **Asian/Pacific Islander (§5b).** Bronze publishes exactly 6 race buckets
  in all 21 years and never a separate Pacific Islander column anywhere.
  The math test is inconclusive here (race percentages are integer-rounded:
  verified state-row race sums are 101 in 2004, 99 in 2011 — pure rounding
  noise), so the structural argument governs, and §5b's known-combined list
  already includes this bronze: bare "Asian" is the pre-1997 OMB combined
  bucket, mapped to ``asian_pacific_islander``. The remap happens BEFORE
  ``normalize_demographic_column`` via the column->label map below.
- **No ``all`` row.** GOSA publishes no category-total share column, so no
  ``all`` demographic exists in this topic (nothing to unpivot from).
- **``enrollment_ratio`` is ``unit: ratio``, not ``proportion``.** Bronze
  is 0-100 (divided by 100 here, §4), but bronze legitimately exceeds 100
  for special-population shares at alternative/behavioral/early-childhood/
  state-special schools, where the count of students served exceeds the
  October FTE snapshot denominator: verified maxima are ED 132 (2008
  Mountain Creek Academy, 705:0108) -> 1.32 and SWD 117 (2004 Butler Early
  Childhood Center, 611:0179) -> 1.17. These are extreme-but-conceivable
  (§4b: preserve + document), so the bounded-proportion check would be
  wrong; the ``enrollment_ratio_sane_upper_bound`` quality check (<= 1.5)
  still catches any unscaled 0-100 regression.
- **AYP-era denormalization.** ``met_ayp`` / ``improvement_status`` are
  entity-level NCLB indicators published 2004-2010 only; the unpivot
  repeats them across the 12 demographic rows per entity (intentional —
  no sidecar table). NULL from 2011 on (pinned by
  ``ayp_columns_null_post_2010``). Sentinels ('', ' ', '.', 'N/A') -> NULL;
  codes lowercase via shared maps recorded to the manifest. Both are
  **excluded from the row grain** (``exclude_from_grain``): they describe
  the entity-year rather than identify the row — (year, district_code,
  school_code, demographic) is unique on its own in every year — and
  keeping them in the grain forced serving-layer consumers to pin a value,
  which silently excluded every post-2010 (NULL-era) row.
- **Race partition-sum check omitted; male+female check authored.** Race
  shares are published as integer-rounded percentages (six values each
  rounded to 1pp -> sums legitimately land anywhere near 0.97-1.03), real
  all-zero race rows exist, and 2023-2024 TFS suppression NULLs individual
  cells — no race tolerance is provable from bronze without also masking
  real data errors, so per §15b that absence is documented here. The
  male+female pair, however, IS provably tight: across all 19,921 pairs
  where both shares are non-NULL, |male + female - 1| <= 0.03 with zero
  violations, so ``male_female_shares_sum_to_one`` pins it (NULL-guarded).
- **Dedup tie-break.** Bronze repeats verified: 2004 has 109 exact
  duplicate rows (full-row byte-identical repeats); 2009 has 4 duplicate
  key groups (2 byte-identical; 2 — Ivy Prep 768:ALL, Scholars Academy
  770:ALL — differ only in the School Name / Grades dimension attributes
  that never enter the fact table, with all 9 shares and both AYP values
  identical). ``assert_no_natural_key_collisions`` (metrics + both AYP
  categoricals) proves the duplicates agree on every fact column before
  ``deduplicate_by_detail_level`` removes them; ``sort_col=
  "enrollment_ratio"`` is the documented safety-net tie-break (prefer a
  populated share over a hypothetical null twin). Removals are recorded
  per year via ``manifest.record_filtered``.
- **2011 LEP school-level sparsity.** The 2011 file suppresses
  ``ENROLL_PERCENT_LEP`` on ~87%% of school rows (district/state complete;
  2012+ complete) — GOSA's pre-CCRPI cell-suppression policy. Values
  present are real; nothing is imputed. Surfaces as an expected
  english_learners NULL-rate spike in 2011.
- **Detail levels.** state/district/school; 2009 and 2010 publish no state
  row (none is synthesized). The 2022 single-school charter aggregates
  mislabeled School/'ALL' are reclassified to district in the shared module
  (recorded via ``record_reclassified``).
- **No §4b masks.** No value in any era is impossible on the metric's
  domain (the >1.0 ratios are real published GOSA artifacts, documented
  above; negatives do not occur — verified).
"""

import logging
from pathlib import Path

import polars as pl

from src.etl.education.gosa._enrollment_subgroup_programs_shared import (
    BRONZE_DIR,
    DEMOGRAPHIC_PCT_COLUMNS,
    WIDE_AYP_COLUMNS,
    WIDE_KEY_COLUMNS,
    build_combined_wide_dataframe,
)
from src.utils.demographics import (
    DEMOGRAPHIC_ALIASES,
    SENTINEL_UNMATCHED_DEMOGRAPHIC,
    normalize_demographic_column,
)
from src.utils.metadata import write_data_dictionary
from src.utils.transformers import (
    TransformManifest,
    assert_no_natural_key_collisions,
    deduplicate_by_detail_level,
    export_to_parquet,
    harmonize_columns,
    null_aggregate_geography,
    validate_output,
)
from src.utils.validators import (
    EDUCATION_DOMAIN_CONFIG,
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

TOPIC = "enrollment_demographic_shares"
GOLD_DIR = Path("data/gold/education/enrollment_demographic_shares")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Wide column -> the demographic label fed to normalize_demographic_column.
# Labels mirror the bronze column semantics, with one deliberate exception:
# the bronze ASIAN columns carry the label "Asian/Pacific Islander" — the
# §5b topic-local remap of GOSA's combined 6-bucket "Asian" (see module
# docstring). DEMOGRAPHIC_ALIASES then canonicalizes every label.
DEMOGRAPHIC_SOURCE_LABELS: dict[str, str] = {
    "pct_asian_pacific_islander": "Asian/Pacific Islander",
    "pct_black": "Black",
    "pct_hispanic": "Hispanic",
    "pct_native_american": "Native American",
    "pct_multiracial": "Multiracial",
    "pct_white": "White",
    "pct_migrant": "Migrant",
    "pct_economically_disadvantaged": "Economically Disadvantaged",
    "pct_students_with_disabilities": "Students With Disabilities",
    "pct_english_learners": "Limited English Proficient",
    "pct_male": "Male",
    "pct_female": "Female",
}

# Gold fact column order. detail_level is carried through dedup / geography
# nulling / export splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    # Entity-level AYP categoricals, denormalized across the 12 demographic
    # rows per entity-year (2004-2010 only; NULL thereafter).
    "met_ayp",
    "improvement_status",
    "enrollment_ratio",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "demographic": pl.Utf8,
    "met_ayp": pl.Utf8,
    "improvement_status": pl.Utf8,
    "enrollment_ratio": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = ["enrollment_ratio"]

# Natural key on the long frame (pre-dedup, detail_level still present).
NATURAL_KEYS: list[str] = [
    "year",
    "detail_level",
    "district_code",
    "school_code",
    "demographic",
]


# =============================================================================
# Unpivot
# =============================================================================


def _unpivot_demographic_shares(
    wide: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Unpivot the 12 demographic-share columns into tidy long rows.

    Each wide row emits exactly 12 long rows (one per demographic); keys and
    the AYP categoricals ride along verbatim. The demographic value is
    derived from the source column identity: wide column -> §5b-aware label
    -> ``normalize_demographic_column`` -> canonical key, and the full
    two-hop mapping is recorded to the manifest (column names as the bronze
    side, per skill §4.3a's effective-slice rule for the alias hop).
    """
    long_df = wide.unpivot(
        on=DEMOGRAPHIC_PCT_COLUMNS,
        index=WIDE_KEY_COLUMNS + WIDE_AYP_COLUMNS,
        variable_name="_pct_column",
        value_name="enrollment_ratio",
    )

    # Hop 1: wide column -> demographic label (raises on drift via
    # replace_strict with no default — every wide column must be mapped).
    long_df = long_df.with_columns(
        pl.col("_pct_column")
        .replace_strict(DEMOGRAPHIC_SOURCE_LABELS)
        .alias("_demographic_label")
    )
    # Hop 2: label -> canonical key via the shared alias path (§5).
    long_df = long_df.with_columns(
        normalize_demographic_column("_demographic_label").alias("demographic")
    )

    # The label set is fixed at authoring time, so the sentinel firing means
    # DEMOGRAPHIC_ALIASES changed underneath us — fail loudly, never export.
    bad = long_df.filter(
        pl.col("demographic").is_null()
        | (pl.col("demographic") == SENTINEL_UNMATCHED_DEMOGRAPHIC)
    )
    if bad.height > 0:
        raise ValueError(
            f"{bad.height} unpivoted rows produced an unmatched/NULL "
            f"demographic: {bad['_demographic_label'].unique().to_list()}"
        )

    # Manifest: record both hops in one reviewable map — wide column ->
    # canonical key (mechanical) plus the effective DEMOGRAPHIC_ALIASES
    # slice (label -> canonical key) actually hit (§4.3a).
    alias_slice = {
        label: DEMOGRAPHIC_ALIASES[label.upper()]
        for label in DEMOGRAPHIC_SOURCE_LABELS.values()
    }
    column_to_key = {
        col: DEMOGRAPHIC_ALIASES[label.upper()]
        for col, label in DEMOGRAPHIC_SOURCE_LABELS.items()
    }
    manifest.record_categorical(
        column="demographic",
        map_dict={**column_to_key, **alias_slice},
        bronze_series=long_df["_pct_column"],
        gold_series=long_df["demographic"],
    )

    return long_df.drop("_pct_column", "_demographic_label")


# =============================================================================
# Pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for enrollment_demographic_shares."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Shared bronze layer: reads all 21 files, records read-loss / files /
    # bronze counts / the 2004 junk-row filter / the 2022 reclassification /
    # AYP recodings into THIS topic's manifest, and returns the wide frame.
    wide = build_combined_wide_dataframe(manifest)

    # 2. Project to the columns this topic owns (the program pairs belong to
    # the sibling topic) and unpivot to one row per demographic.
    wide = wide.select(WIDE_KEY_COLUMNS + WIDE_AYP_COLUMNS + DEMOGRAPHIC_PCT_COLUMNS)
    long_df = _unpivot_demographic_shares(wide, manifest)
    logger.info(
        "Unpivoted %s wide rows into %s long rows (x12 demographics)",
        f"{wide.height:,}",
        f"{long_df.height:,}",
    )

    # 3. Harmonize to the declared schema (defensive: types already match).
    long_df = harmonize_columns([long_df], STANDARD_COLUMNS, TARGET_TYPES)[0]

    # 4. Collision guard BEFORE dedup: the known bronze duplicates (2004:
    # 109 exact repeats; 2009: 4 groups) must agree on the share AND both
    # AYP categoricals — divergence means an era-routing/alias bug.
    assert_no_natural_key_collisions(
        long_df,
        natural_keys=NATURAL_KEYS,
        metric_cols=["enrollment_ratio", "met_ayp", "improvement_status"],
    )
    # Tie-break: duplicates are proven identical on every fact column, so
    # the winner is immaterial; prefer a populated share over a null twin
    # as the documented safety net.
    before_by_year = dict(long_df.group_by("year").len().iter_rows())
    long_df = deduplicate_by_detail_level(
        long_df,
        school_keys=["year", "district_code", "school_code", "demographic"],
        district_keys=["year", "district_code", "demographic"],
        state_keys=["year", "demographic"],
        sort_col="enrollment_ratio",
    )
    after_by_year = dict(long_df.group_by("year").len().iter_rows())
    for year in sorted(before_by_year):
        removed = before_by_year[year] - after_by_year.get(year, 0)
        if removed > 0:
            manifest.record_filtered(
                year,
                removed,
                "duplicate_long_rows_removed_by_dedup"
                "_bronze_repeats_verified_identical_on_all_fact_columns",
            )

    # 5. Geography nulling per the shared domain rules (state rows: both
    # keys NULL; district rows: school_code NULL). No §4b masks (docstring).
    long_df = null_aggregate_geography(
        long_df,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Expected NULL-rate spikes: Era A's 3-of-12 missing demographics (25%
    # floor pre-2011), the 2011 LEP school suppression, and 2023-24 TFS.
    spike_result = check_null_rate_spikes(long_df, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes (documented causes): %s", spike_result.details)

    validate_output(long_df, required_non_null=["year", "detail_level", "demographic"])

    # 6. Manifest stats on the FINAL frame, then export + manifest.
    manifest.record_gold_from_dataframe(long_df)
    manifest.compute_metric_stats(long_df, METRIC_COLUMNS)
    export_to_parquet(long_df, GOLD_DIR, STANDARD_COLUMNS)
    manifest.write(GOLD_DIR)

    # 7. Contract + README from the in-code column declaration.
    _emit_contract_and_readme(
        year_range=(int(long_df["year"].min()), int(long_df["year"].max()))
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


def _emit_contract_and_readme(year_range: tuple[int, int]) -> None:
    """Emit the ODCS contract and README via ``write_data_dictionary``.

    Column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level`` — the contract properties and the validator's schema
    check follow it.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        # 2.0.0: met_ayp / improvement_status dropped from the row grain
        # (attribute flags, not identity axes) — a breaking grain change.
        version="2.0.0",
        description=(
            "Georgia Office of Student Achievement (GOSA) enrollment "
            "demographic shares. For every Georgia public school, school "
            "district, and the state as a whole, the share of enrollment in "
            "each of 12 demographic subgroups: six race/ethnicity buckets "
            "(Asian/Pacific Islander, Black, Hispanic, Native American, "
            "Multiracial, White), two sexes (male, female — published 2011 "
            "and 2018 onward), and four special populations (migrant — "
            "published 2011 onward, economically disadvantaged, students "
            "with disabilities, English learners). This topic is COMPUTED "
            "from the shared GOSA 'Enrollment by Subgroup Programs' bronze "
            "(FTE enrollment disaggregated by subgroup); the companion "
            "enrollment_program_participation topic exposes the program-"
            "participation side of the same files. enrollment_ratio is the "
            "share GOSA publishes for each subgroup: the subgroup's FTE "
            "count over the entity's total FTE enrollment (October snapshot "
            "denominator). Coverage spans school years 2003-04 through "
            "2023-24. The 2004-2010 files also carry the NCLB-era Met AYP "
            "and Improvement Status indicators, denormalized across the 12 "
            "demographic rows per entity-year and NULL from 2011 on (AYP "
            "retired). Demographics whose column a source year does not "
            "publish (pre-2011 migrant/male/female; 2012-2017 male/female) "
            "are emitted with NULL enrollment_ratio so the 12-demographic "
            "grid is uniform across years."
        ),
        title="Enrollment Demographic Shares",
        summary=(
            "Each demographic subgroup's share of enrollment by Georgia "
            "school, district, and statewide, 2004-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Ending calendar year of the school year (2024 = the "
                    "2023-24 school year). Sourced from LONG_SCHOOL_YEAR for "
                    "2011+ (cross-checked against the filename); from the "
                    "bronze filename for 2004-2010."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "GOSA district code (FK to districts dimension): 3-digit "
                    "zero-padded for standard districts, 7-digit for charter "
                    "districts. NULL on state-level aggregate rows."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0103",
                "description": (
                    "4-digit zero-padded GOSA school code (composite FK to "
                    "schools dimension with district_code). NULL on district- "
                    "and state-level aggregate rows."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "black",
                "description": (
                    "Canonical demographic code (FK to demographics "
                    "dimension). Exactly 12 values: asian_pacific_islander, "
                    "black, hispanic, native_american, multiracial, white, "
                    "migrant, economically_disadvantaged, "
                    "students_with_disabilities, english_learners, male, "
                    "female. The bronze 'Asian' bucket is GOSA's pre-1997 "
                    "OMB combined Asian + Pacific Islander bucket (the "
                    "source publishes only 6 race buckets and never a "
                    "separate Pacific Islander column), so it maps to "
                    "asian_pacific_islander per data-cleaning-standards "
                    "section 5b. No 'all' row exists — GOSA publishes no "
                    "category-total share in this report."
                ),
                "short_description": (
                    "Which demographic subgroup the share is for; one of 12 "
                    "race, sex, and special-population codes (no 'all' row)."
                ),
            },
            {
                "name": "met_ayp",
                "type": "string",
                "exclude_from_grain": True,
                "example": "yes",
                "null_meaning": (
                    "NULL for 2011+ (AYP retired) and for 2004-2010 rows "
                    "whose bronze value was blank or N/A."
                ),
                "description": (
                    "NCLB-era Adequate Yearly Progress indicator (yes/no), "
                    "published 2004-2010 only. An entity-level value "
                    "repeated (denormalized) across the 12 demographic rows "
                    "of the same (year, district, school) tuple. Bronze "
                    "sentinels blank/N/A are NULL."
                ),
                "short_description": (
                    "NCLB-era Adequate Yearly Progress flag (yes/no); "
                    "populated 2004-2010 only, NULL afterward."
                ),
            },
            {
                "name": "improvement_status",
                "type": "string",
                "exclude_from_grain": True,
                "example": "adeq",
                "null_meaning": (
                    "NULL for 2011+ (AYP retired) and for 2004-2010 rows "
                    "whose bronze value was blank or '.'."
                ),
                "description": (
                    "NCLB-era school improvement-status code (adeq, "
                    "adeq_dnm, dist, ni, ni_ayp), published 2004-2010 only "
                    "and denormalized across the 12 demographic rows per "
                    "entity-year. Bronze sentinels '.' and blank are NULL."
                ),
                "short_description": (
                    "NCLB-era school improvement-status code; populated "
                    "2004-2010 only, NULL afterward."
                ),
            },
            {
                "name": "enrollment_ratio",
                "type": "float64",
                "unit": "ratio",
                "key_metric": True,
                "example": 0.25,
                "short_description": (
                    "This subgroup's share of the entity's total FTE "
                    "enrollment, on a 0-1 scale (may exceed 1.0 for ED/SWD "
                    "at some special schools)."
                ),
                "description": (
                    "Share of the entity's total FTE enrollment in this "
                    "demographic, on the 0-1 decimal scale (bronze 0-100 "
                    "divided by 100). NULL when the bronze cell was "
                    "suppressed (TFS — program-wide from 2023) or when the "
                    "source year does not publish the demographic's column "
                    "(pre-2011 migrant/male/female; 2012-2017 male/female; "
                    "2011 additionally suppresses English-learner shares on "
                    "~87%% of school rows). Declared unit: ratio rather than "
                    "proportion per section 4a: GOSA's published shares for "
                    "economically_disadvantaged and "
                    "students_with_disabilities legitimately exceed 1.0 at "
                    "alternative/behavioral/early-childhood/state-special "
                    "schools in 2004-2010 where the served count exceeds "
                    "the October FTE snapshot denominator (verified maxima: "
                    "1.32 ED at 2008 Mountain Creek Academy, 1.17 SWD at "
                    "2004 Butler Early Childhood Center); all other "
                    "demographics stay within [0, 1.02] (rounding "
                    "artifacts). Values are preserved per section 4b "
                    "(extreme-but-conceivable, not impossible). Note the "
                    "statewide economically_disadvantaged share dips to "
                    "0.45 in 2022 between 0.56 (2021) and 0.59 (2023) — "
                    "bronze-confirmed as published, likely a pandemic-era "
                    "direct-certification artifact; treat the 2022 ED "
                    "series with care."
                ),
            },
        ],
        source="Governor's Office of Student Achievement (GOSA)",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        notes=[
            (
                "Derived topic: the bronze publishes the 12 demographic-"
                "share columns and 9 program (count, percent) pairs side by "
                "side; this topic unpivots the demographic columns, the "
                "sibling enrollment_program_participation topic unpivots "
                "the program pairs."
            ),
            (
                "Uniform demographic grid: every (year, entity) tuple "
                "carries exactly 12 demographic rows; era-gap demographics "
                "(pre-2011 migrant/male/female, 2012-2017 male/female) are "
                "NULL rather than absent."
            ),
            (
                "enrollment_ratio is a decimal ratio (0-1 scale): values "
                "above 1.0 occur only for economically_disadvantaged (max "
                "1.32) and students_with_disabilities (max 1.17) at "
                "alternative/early-childhood/state-special schools in "
                "2004-2010, where students served exceed the October FTE "
                "snapshot denominator."
            ),
            (
                "AYP-era categoricals (met_ayp, improvement_status) are "
                "populated 2004-2010 only and repeated across the 12 "
                "demographic rows per entity-year (denormalized — no "
                "sidecar table)."
            ),
            (
                "State rows are absent in 2009 and 2010 (GOSA published no "
                "state aggregate in those files; none is synthesized), so "
                "those partitions have no states.parquet."
            ),
            (
                "Suppression regimes: no TFS through 2020; 2021-2022 TFS "
                "hits only program count columns (sibling topic); 2023-2024 "
                "TFS extends to all demographic-share columns. The 2011 "
                "file suppresses English-learner shares on ~87%% of school "
                "rows (pre-CCRPI policy); 2012+ is complete."
            ),
            (
                "Bronze repeats removed by dedup: 2004 carries 109 exact "
                "duplicate rows (plus one malformed ID='2' junk row, "
                "dropped); 2009 carries 4 duplicate-key groups that agree "
                "on every fact column. All removals are recorded in the "
                "transform manifest."
            ),
        ],
        # Override the auto-derived examples: the derived third query would
        # pair met_ayp with the latest year, but met_ayp is NULL from 2011
        # on, so that query would mislead with zero rows. Scope the AYP
        # example to an AYP-era year instead.
        example_queries=[
            {
                "description": "Latest year (2024), schools detail",
                "query": (
                    "SELECT * FROM enrollment_demographic_shares "
                    "WHERE year = 2024 LIMIT 100"
                ),
            },
            {
                "description": "Economically disadvantaged share in 2024",
                "query": (
                    "SELECT * FROM enrollment_demographic_shares "
                    "WHERE demographic = 'economically_disadvantaged' "
                    "AND year = 2024 LIMIT 100"
                ),
            },
            {
                "description": (
                    "AYP-era slice: met_ayp = 'yes' in 2010 (met_ayp / "
                    "improvement_status are only populated 2004-2010)"
                ),
                "query": (
                    "SELECT * FROM enrollment_demographic_shares "
                    "WHERE met_ayp = 'yes' AND year = 2010 LIMIT 100"
                ),
            },
        ],
        quality_checks=[
            {
                "name": "enrollment_ratio_sane_upper_bound",
                "description": (
                    "enrollment_ratio is unit: ratio, so the derived range "
                    "check only enforces >= 0 — an unscaled 0-100 "
                    "regression would slip through. The legitimate above-"
                    "1.0 ratios (ED/SWD at alternative/early-childhood/"
                    "state-special schools, 2004-2010) top out at a "
                    "verified 1.32, so any value above 1.5 means an "
                    "unscaled value, not a real share."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE enrollment_ratio IS NOT NULL "
                    "AND enrollment_ratio > 1.5"
                ),
                "mustBe": 0,
            },
            {
                "name": "ayp_columns_null_post_2010",
                "description": (
                    "Structural fact: the NCLB AYP program ended after the "
                    "2009-10 school year and the 2011+ bronze publishes no "
                    "Met AYP / Improvement Status columns, so both "
                    "categoricals must be NULL on every row from 2011 on."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year >= 2011 AND "
                    "(met_ayp IS NOT NULL OR improvement_status IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "era_gap_demographics_null",
                "description": (
                    "Structural fact: the pre-2011 bronze publishes no "
                    "migrant/male/female columns and the 2012-2017 bronze "
                    "publishes no male/female columns, so those demographic "
                    "rows must carry NULL enrollment_ratio in those years "
                    "(the grid rows exist; the metric cannot)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE enrollment_ratio IS NOT NULL AND ("
                    "(year <= 2010 AND demographic IN "
                    "('migrant', 'male', 'female')) OR "
                    "(year BETWEEN 2012 AND 2017 AND demographic IN "
                    "('male', 'female')))"
                ),
                "mustBe": 0,
            },
            {
                "name": "twelve_demographic_rows_per_entity",
                "description": (
                    "Structural fact: the unpivot emits all 12 demographic "
                    "rows for every (year, district_code, school_code) "
                    "entity (era-gap demographics as NULL-metric rows), so "
                    "every entity-year group must contain exactly 12 rows. "
                    "GROUP BY treats NULL geography keys as equal, which "
                    "matches the entity identity across detail levels."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, school_code "
                    "FROM {object} "
                    "GROUP BY year, district_code, school_code "
                    "HAVING COUNT(*) <> 12) AS bad_entities"
                ),
                "mustBe": 0,
            },
            {
                "name": "male_female_shares_sum_to_one",
                "description": (
                    "Where bronze publishes both sex shares (2011 and "
                    "2018+), male + female must sum to 1 within the "
                    "1pp-per-bucket integer rounding (verified: 0 of "
                    "19,921 non-NULL pairs deviate beyond 0.03). "
                    "NULL-guarded — TFS-suppressed and era-gap cells are "
                    "skipped. The race partition carries no analogous "
                    "check: six integer-rounded buckets plus real all-zero "
                    "race rows make no tolerance provable (see the "
                    "transform docstring)."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, school_code, "
                    "MAX(CASE WHEN demographic = 'male' THEN "
                    "enrollment_ratio END) AS m, "
                    "MAX(CASE WHEN demographic = 'female' THEN "
                    "enrollment_ratio END) AS f "
                    "FROM {object} "
                    "GROUP BY year, district_code, school_code"
                    ") WHERE m IS NOT NULL AND f IS NOT NULL "
                    "AND ABS(m + f - 1.0) > 0.03"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
