"""Transform the shared enrollment_by_subgroup_programs bronze into tidy
program-participation gold (``enrollment_program_participation``).

Source: Governor's Office of Student Achievement (GOSA) — "Enrollment by
Subgroup Programs". This DERIVED topic exposes the program-participation
side of that publication: for every Georgia public school, district, and
the state, the count and share of students enrolled in each of 9 state
instructional programs (Remedial 6-8, EIP K-5, Remedial 9-12, Special Ed
K-12, ESOL, Special Ed Pre-K, Vocational 9-12, Alternative Programs,
Gifted). The sibling topic ``enrollment_demographic_shares`` exposes the
demographic-share side of the SAME bronze files; everything the two topics
must agree on byte-for-byte (reading, era routing, IDs, the 0-100 -> 0-1
scaling, the 2022 charter-aggregate reclassification) lives in
``_enrollment_subgroup_programs_shared``.

Design decisions (clean-room from bronze-data-structure.md + standards;
every bronze claim re-verified 2026-06-11):

- **Coverage starts at 2011.** The 2004-2010 bronze (Era A) predates the
  program-column schema expansion — those files publish no program columns
  at all, so ``build_combined_wide_dataframe(manifest, min_year=2011)``
  skips them entirely (not read, not in the manifest). Emitting pre-2011
  rows would fabricate NULL-only program observations the bronze never
  made. Era-A demographic coverage lives in the sibling topic.
- **Tidy long unpivot.** The 9 wide (``count_<program>``, ``pct_<program>``)
  pairs become one row per (year, district_code, school_code, program) with
  ``num_students`` + ``participation_rate``. Expansion factor is exactly
  9x the wide row count; the unpivot is pure column selection/renaming —
  the shared module hands over final metric values (counts already Int64
  with TFS/blank -> NULL; rates already on the 0-1 scale) and no further
  arithmetic is applied here.
- **NULL-vs-zero policy.** A NULL metric means "program not offered /
  not applicable at this entity" (the dominant cause 2011-2022, e.g.
  grade 6-8 remediation at a high school) or "suppressed" (TFS: count
  columns 2021+, percentage columns 2023+). NULL is never coerced to 0 —
  zero would falsely assert the entity was measured with no participants.
- **Pre-2013 ``special_ed_pk`` rate mask (§4b).** Bronze
  ``ENROLL_PCT_SPECIAL_ED_PK`` switches denominator between the 2012 and
  2013 files: re-verified 2011 mean 0.9%%/max 644%%, 2012 mean 1.0%%/max
  759%% (mechanically impossible as a share) vs 2013+ mean ~19%% capped at
  exactly 100%%, while the companion count stays steady (~11/row). The
  shift coincides with the May 2013 CCRPI launch when GOSA standardized on
  the program-served-grades denominator. Pre-2013 rates are on an unknown,
  undocumented base and cannot be re-normalized, so ``participation_rate``
  is NULLed for ``special_ed_pk`` in 2011-2012 (5,012 values;
  ``num_students`` is preserved). A defensive companion mask NULLs any
  2013+ ``special_ed_pk`` rate > 1.0 (zero such values today).
- **2011/2019 ``alt_programs`` count publishing error (§4b).** In exactly
  those two years GOSA published ``ENROLL_COUNT_ALT_PROGRAMS`` equal to
  the entity's TOTAL enrollment, not the alt-program subset, while the
  companion percentage stayed correct. Re-verified: the state row carries
  1,533,435 (2011) / 1,602,163 (2019) vs 10k-33k in every other year, and
  61 district rows exceed 5,000 in each error year vs exactly 1 elsewhere.
  The corruption reaches school level (each school's own enrollment), so
  no absolute threshold works; the companion rate separates the cases
  cleanly — bogus rows top out at rate 0.937/0.939 while genuine
  all-alternative entities sit at >= 0.95, where count == enrollment is
  correct. ``num_students`` is NULLed for ``alt_programs`` rows in
  2011/2019 wherever the rate is < 0.95 or NULL (4,938 values; a NULL rate
  cannot vouch for the count — zero such rows in practice). The rate is
  always preserved.
- **``participation_rate`` is ``unit: proportion``.** Post-mask, every
  published rate satisfies 0 <= rate <= 1 (re-verified: only the masked
  pre-2013 special_ed_pk values ever exceeded 1.0; every other program's
  maximum is exactly 1.0). The bounded check is enforced by the contract,
  not weakened — the impossible values are NULLed, not exempted.
- **Count/rate co-null structure.** Re-verified across all 14 years: the
  bronze publishes count and rate as an all-or-nothing pair except in
  2021-2022, where TFS suppresses ONLY the count columns (rates stay
  numeric). The two §4b masks add the only other asymmetries. This is
  pinned by the ``count_rate_co_null_outside_known_asymmetries`` quality
  check.
- **Dedup tie-break.** Re-verified: zero duplicate (year, detail_level,
  district_code, school_code) keys anywhere in 2011-2024 (the bronze
  repeats live in 2004/2009, outside this topic's coverage), so
  ``assert_no_natural_key_collisions`` + ``deduplicate_by_detail_level``
  are pure safety nets; ``sort_col="num_students"`` is the documented
  tie-break (prefer a populated count over a hypothetical null twin).
- **Detail levels.** state/district/school per the shared module; the two
  2022 single-school charter aggregates mislabeled School/'ALL' are
  reclassified to district upstream (recorded via ``record_reclassified``
  into this manifest).
"""

import logging
from pathlib import Path

import polars as pl

from src.etl.education.gosa._enrollment_subgroup_programs_shared import (
    BRONZE_DIR,
    PROGRAM_COUNT_COLUMNS,
    PROGRAM_PCT_COLUMNS,
    PROGRAMS,
    WIDE_KEY_COLUMNS,
    build_combined_wide_dataframe,
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

TOPIC = "enrollment_program_participation"
GOLD_DIR = Path("data/gold/education/enrollment_program_participation")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Pre-2011 bronze publishes no program columns; skip those files entirely.
MIN_YEAR = 2011

# Wide bronze-derived column -> canonical program key (mechanical: strip the
# count_ prefix). Listed via PROGRAMS so the manifest carries the exact map
# and future program additions must be wired through the shared module.
COUNT_COLUMN_TO_PROGRAM: dict[str, str] = {f"count_{p}": p for p in PROGRAMS}

# Gold fact column order. detail_level is carried through dedup / geography
# nulling / export splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "program",
    "num_students",
    "participation_rate",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "program": pl.Utf8,
    "num_students": pl.Int64,
    "participation_rate": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = ["num_students", "participation_rate"]

# Natural key on the long frame (pre-dedup, detail_level still present).
NATURAL_KEYS: list[str] = [
    "year",
    "detail_level",
    "district_code",
    "school_code",
    "program",
]


# =============================================================================
# Unpivot
# =============================================================================


def _unpivot_program_pairs(
    wide: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Unpivot the 9 (count_*, pct_*) program pairs into tidy long rows.

    One sub-frame per program (keys + that program's count/rate + a literal
    ``program``), then vertical concat — the column-name -> program mapping
    stays verifiable by inspection against PROGRAMS. Pure selection/aliasing:
    no arithmetic touches the metric values the shared module produced.
    """
    frames: list[pl.DataFrame] = []
    for program in PROGRAMS:
        count_col = f"count_{program}"
        pct_col = f"pct_{program}"
        frames.append(
            wide.select(
                *WIDE_KEY_COLUMNS,
                pl.lit(program).alias("program"),
                pl.col(count_col).alias("num_students"),
                pl.col(pct_col).alias("participation_rate"),
            )
        )
    long_df = pl.concat(frames, how="vertical")

    # Manifest: the categorical recoded here is "wide program-count column
    # name -> canonical program key"; reconstruct the bronze side from the
    # gold value so the recorded mapping reflects rows actually emitted.
    bronze_series = long_df.select(
        pl.concat_str([pl.lit("count_"), pl.col("program")]).alias("_bronze_col")
    )["_bronze_col"]
    manifest.record_categorical(
        column="program",
        map_dict=COUNT_COLUMN_TO_PROGRAM,
        bronze_series=bronze_series,
        gold_series=long_df["program"],
    )
    return long_df


# =============================================================================
# §4b masks (impossible / publisher-error values -> NULL)
# =============================================================================


def _null_pre_2013_special_ed_pk_rates(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """NULL pre-2013 special_ed_pk participation rates (denominator drift).

    Pre-2013 GOSA published ENROLL_PCT_SPECIAL_ED_PK on a different,
    undocumented denominator (2011/2012 means ~1%% with maxima of 644%%/759%%
    — impossible as a share — vs 2013+ means ~19%% capped at exactly 100%%,
    with the companion count steady). The values cannot be re-normalized, so
    they are masked per §4b; num_students is preserved.
    """
    cond = (
        (pl.col("program") == "special_ed_pk")
        & (pl.col("year") < 2013)
        & pl.col("participation_rate").is_not_null()
    )
    n = df.filter(cond).height
    if n > 0:
        years = sorted(df.filter(cond)["year"].unique().to_list())
        manifest.record_masked(
            column="participation_rate",
            count=n,
            reason=(
                "pre_2013_special_ed_pk_denominator_drift — pre-2013 GOSA "
                "published the rate on an undocumented denominator (maxima "
                "644-759%, impossible as a share); not re-normalizable, so "
                "masked per §4b. num_students preserved."
            ),
            years=years,
        )
    return df.with_columns(
        pl.when((pl.col("program") == "special_ed_pk") & (pl.col("year") < 2013))
        .then(None)
        .otherwise(pl.col("participation_rate"))
        .alias("participation_rate")
    )


def _null_impossible_special_ed_pk_rates(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Defensively NULL any 2013+ special_ed_pk rate > 1.0 (impossible).

    Zero such values exist today (re-verified: 2013+ maxima are exactly
    1.0); this guard keeps the bounded-proportion contract check honest if
    a future bronze refresh reintroduces the pre-2013 denominator.
    """
    cond = (pl.col("program") == "special_ed_pk") & (pl.col("participation_rate") > 1.0)
    n = df.filter(cond).height
    if n > 0:
        years = sorted(df.filter(cond)["year"].unique().to_list())
        logger.warning(
            "NULLing %d unexpected special_ed_pk participation_rate value(s) "
            "> 1.0 in years %s (impossible for a bounded share)",
            n,
            years,
        )
        manifest.record_masked(
            column="participation_rate",
            count=n,
            reason="special_ed_pk_rate_above_1_impossible_for_bounded_share",
            years=years,
        )
        df = df.with_columns(
            pl.when(cond)
            .then(None)
            .otherwise(pl.col("participation_rate"))
            .alias("participation_rate")
        )
    return df


def _null_alt_programs_count_publishing_error(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """NULL the 2011/2019 alt_programs counts that equal total enrollment.

    In exactly 2011 and 2019 GOSA published the alt-programs count as the
    entity's TOTAL enrollment (state row 1.53M/1.60M vs 10k-33k every other
    year; 61 district rows > 5,000 vs exactly 1 elsewhere) while the
    companion rate stayed correct. The corruption reaches school level, so
    the rate is the only reliable separator: bogus rows top out at rate
    0.937/0.939; genuine all-alternative entities (rate >= 0.95) keep their
    count, where count == enrollment is legitimately true. A NULL rate
    cannot vouch for the count, so it is masked too (zero such rows in
    practice). The rate itself is always preserved.
    """
    cond = (
        (pl.col("program") == "alt_programs")
        & pl.col("year").is_in([2011, 2019])
        & pl.col("num_students").is_not_null()
        & (
            pl.col("participation_rate").is_null()
            | (pl.col("participation_rate") < 0.95)
        )
    )
    masked = df.filter(cond)
    if masked.height > 0:
        by_year = dict(sorted(masked.group_by("year").len().iter_rows()))
        logger.warning(
            "NULLing %d alt_programs num_students value(s) in 2011/2019 "
            "(GOSA publishing error: count equals total enrollment, not the "
            "alt-program subset). Per-year: %s. All-alternative entities "
            "(rate >= 0.95) keep their count.",
            masked.height,
            by_year,
        )
        manifest.record_masked(
            column="num_students",
            count=masked.height,
            reason=(
                "alt_programs_count_publishing_error_2011_2019 — bronze "
                "count equals total enrollment, not the alt-program subset "
                "(state/district/school levels all affected); masked where "
                "companion rate < 0.95 or NULL, kept for genuine "
                "all-alternative entities (rate >= 0.95)."
            ),
            years=sorted(masked["year"].unique().to_list()),
        )
    return df.with_columns(
        pl.when(cond).then(None).otherwise(pl.col("num_students")).alias("num_students")
    )


# =============================================================================
# Pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for enrollment_program_participation."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Shared bronze layer: reads the 2011-2024 files (min_year skips the
    # programless Era A bronze entirely), records read-loss / files / bronze
    # counts / the 2022 charter reclassification into THIS topic's manifest,
    # and returns the wide frame with final metric values (counts Int64,
    # rates already 0-1).
    wide = build_combined_wide_dataframe(manifest, min_year=MIN_YEAR)

    # 2. Project to the columns this topic owns (demographic shares and AYP
    # categoricals belong to the sibling topic) and unpivot to one row per
    # program per entity-year.
    wide = wide.select(WIDE_KEY_COLUMNS + PROGRAM_COUNT_COLUMNS + PROGRAM_PCT_COLUMNS)
    long_df = _unpivot_program_pairs(wide, manifest)
    logger.info(
        "Unpivoted %s wide rows into %s long rows (x9 programs)",
        f"{wide.height:,}",
        f"{long_df.height:,}",
    )

    # 3. Harmonize to the declared schema (defensive: types already match).
    long_df = harmonize_columns([long_df], STANDARD_COLUMNS, TARGET_TYPES)[0]

    # 4. Collision guard BEFORE dedup. Re-verified: zero duplicate keys exist
    # in 2011-2024 (the known bronze repeats are 2004/2009, outside this
    # topic's coverage), so guard + dedup are pure safety nets here.
    assert_no_natural_key_collisions(
        long_df,
        natural_keys=NATURAL_KEYS,
        metric_cols=METRIC_COLUMNS,
    )
    # Tie-break: prefer the row with a populated count over a hypothetical
    # null twin (no removals expected; any removal is recorded below).
    before_by_year = dict(long_df.group_by("year").len().iter_rows())
    long_df = deduplicate_by_detail_level(
        long_df,
        school_keys=["year", "district_code", "school_code", "program"],
        district_keys=["year", "district_code", "program"],
        state_keys=["year", "program"],
        sort_col="num_students",
    )
    after_by_year = dict(long_df.group_by("year").len().iter_rows())
    for year in sorted(before_by_year):
        removed = before_by_year[year] - after_by_year.get(year, 0)
        if removed > 0:
            manifest.record_filtered(
                year, removed, "duplicate_long_rows_removed_by_dedup_safety_net"
            )

    # 5. Geography nulling per the shared domain rules (state rows: both
    # keys NULL; district rows: school_code NULL).
    long_df = null_aggregate_geography(
        long_df,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # 6. §4b masks at the standard seam (after dedup/geography-nulling,
    # before manifest stats and export).
    long_df = _null_pre_2013_special_ed_pk_rates(long_df, manifest)
    long_df = _null_impossible_special_ed_pk_rates(long_df, manifest)
    long_df = _null_alt_programs_count_publishing_error(long_df, manifest)

    # Expected NULL-rate spikes: the 2021 TFS rollout on count columns and
    # the 2023 TFS expansion to percentage columns; plus the 2011/2012
    # special_ed_pk rate mask. All documented above.
    spike_result = check_null_rate_spikes(long_df, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes (documented causes): %s", spike_result.details)

    validate_output(long_df, required_non_null=["year", "detail_level", "program"])

    # 7. Manifest stats on the FINAL frame, then export + manifest.
    manifest.record_gold_from_dataframe(long_df)
    manifest.compute_metric_stats(long_df, METRIC_COLUMNS)
    export_to_parquet(long_df, GOLD_DIR, STANDARD_COLUMNS)
    manifest.write(GOLD_DIR)

    # 8. Contract + README from the in-code column declaration.
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

    # 9. ALWAYS LAST: validate the gold just written against the contract
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
        description=(
            "Georgia Office of Student Achievement (GOSA) enrollment program "
            "participation. For every Georgia public school, school district, "
            "and the state as a whole, the count and share of students "
            "enrolled in each of nine state instructional programs: Remedial "
            "grades 6-8, Early Intervention Program (EIP) K-5, Remedial "
            "grades 9-12, Special Education K-12, ESOL, Special Education "
            "Pre-K, Vocational grades 9-12, Alternative Programs, and "
            "Gifted. This topic is COMPUTED from the shared GOSA 'Enrollment "
            "by Subgroup Programs' bronze (FTE enrollment disaggregated by "
            "subgroup); the companion enrollment_demographic_shares topic "
            "exposes the demographic-share side of the same files. "
            "participation_rate is the share GOSA publishes for each "
            "program: students in the program over the entity's total FTE "
            "enrollment in the grades the program serves (the denominator "
            "GOSA standardized on at the May 2013 CCRPI launch). Coverage "
            "spans school years 2010-11 through 2023-24 — the 2004-2010 "
            "bronze files predate the program-column schema expansion and "
            "publish no program data, so those years are excluded (the "
            "companion topic covers their demographic-share columns)."
        ),
        title="Enrollment Program Participation",
        summary=(
            "Share of students enrolled in nine state instructional programs "
            "(gifted, special ed, ESOL, etc.) by Georgia school, district, "
            "and statewide, 2011-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Ending calendar year of the school year (2024 = the "
                    "2023-24 school year). Sourced from LONG_SCHOOL_YEAR "
                    "(cross-checked against the bronze filename). Coverage "
                    "starts at 2011: the 2004-2010 bronze publishes no "
                    "program columns and is excluded from this topic."
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
                "name": "program",
                "type": "string",
                "nullable": False,
                "example": "gifted",
                "validValues": sorted(PROGRAMS),
                "description": (
                    "Canonical instructional-program code. Exactly nine "
                    "values: remedial_gr_6_8, eip_k_5, remedial_gr_9_12, "
                    "special_ed_k_12, esol, special_ed_pk, vocation_9_12, "
                    "alt_programs, gifted. Derived from the bronze "
                    "ENROLL_COUNT_<PROGRAM> column name (lowercased, with "
                    "SPECIAL_ED_K12 regularized to special_ed_k_12). Every "
                    "entity-year carries all nine program rows; programs the "
                    "entity does not offer carry NULL metrics."
                ),
                "short_description": (
                    "Which instructional program the row is for; one of nine "
                    "codes (gifted, special ed, ESOL, EIP, remedial, etc.)."
                ),
            },
            {
                "name": "num_students",
                "type": "int64",
                "unit": "count",
                "metric_component": "numerator",
                "example": 42,
                "description": (
                    "Number of students enrolled in the program at the "
                    "entity. NULL when the program does not apply to the "
                    "entity (e.g., grade 6-8 remediation at a high school) "
                    "or when the bronze cell was TFS-suppressed (count "
                    "columns from 2021). For alt_programs in 2011 and 2019 "
                    "the count is additionally NULLed wherever the companion "
                    "rate is < 0.95 or NULL — a GOSA publishing error in "
                    "exactly those two years set the count to the entity's "
                    "TOTAL enrollment (state row 1.53M/1.60M vs 10k-33k in "
                    "every other year), not the alt-program subset; genuine "
                    "all-alternative entities (rate >= 0.95, where count = "
                    "enrollment is correct) keep their count, and the rate "
                    "is always preserved."
                ),
                "null_meaning": (
                    "Several causes share the same NULL: (a) the program "
                    "does not apply to the entity — preserved as NULL, never "
                    "coerced to 0; (b) TFS small-cell suppression in the "
                    "program count columns (2021 onward); (c) for "
                    "alt_programs in 2011/2019, the publisher-error mask "
                    "(bronze count equalled total enrollment). NULL is NOT "
                    "a real zero."
                ),
            },
            {
                "name": "participation_rate",
                "type": "float64",
                "unit": "proportion",
                "key_metric": True,
                "example": 0.12,
                "short_description": (
                    "Share of the entity's enrollment in this program, on a "
                    "0-1 scale; denominator is the grades the program serves."
                ),
                "description": (
                    "Share of the entity's FTE enrollment (in the grades the "
                    "program serves) enrolled in the program, on the 0-1 "
                    "decimal scale (bronze 0-100 divided by 100) and bounded "
                    "on [0, 1] — the published maximum is exactly 1.0. NULL "
                    "when the program does not apply or the bronze cell was "
                    "TFS-suppressed (percentage columns from 2023). "
                    "special_ed_pk rates are NULL for 2011-2012: pre-2013 "
                    "GOSA published the rate on a different, undocumented "
                    "denominator (maxima of 644-759%%, impossible as a "
                    "share) that cannot be re-normalized; the values are "
                    "masked per the known-source-defect policy rather than "
                    "published, so the column stays genuinely bounded. The "
                    "companion num_students for special_ed_pk is preserved "
                    "in those years. Any 2013+ special_ed_pk rate > 1.0 "
                    "would be defensively NULLed too (none exist today)."
                ),
                "null_meaning": (
                    "Multiple causes share the same NULL: the program does "
                    "not apply to the entity; TFS small-cell suppression "
                    "(percentage columns 2023 onward); or the pre-2013 "
                    "special_ed_pk denominator-drift mask (2011-2012). NULL "
                    "is NOT a real zero participation rate."
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
                "Derived topic: the bronze publishes 9 (count, percent) "
                "program column pairs alongside 12 demographic-share "
                "columns; this topic unpivots the program pairs into one "
                "row per (year, district_code, school_code, program), the "
                "sibling enrollment_demographic_shares topic unpivots the "
                "demographic columns."
            ),
            (
                "Coverage starts at 2011. The 2004-2010 bronze predates the "
                "program-column schema expansion; emitting NULL-only rows "
                "for those years would fabricate observations the bronze "
                "never made."
            ),
            (
                "Program-not-applicable NULL semantics: a NULL metric means "
                "the entity does not offer the program (e.g., grade 6-8 "
                "remediation at an elementary school), not zero "
                "participants. NULLs are preserved, never coerced to 0."
            ),
            (
                "Pre-2013 special_ed_pk participation_rate is NULL "
                "(2011-2012): pre-2013 GOSA used a different, undocumented "
                "denominator (means ~1% with maxima 644-759% vs 2013+ means "
                "~19% capped at 100%, companion count steady). The shift "
                "coincides with the May 2013 CCRPI launch. num_students is "
                "preserved for all years."
            ),
            (
                "alt_programs count publishing error: in 2011 and 2019 GOSA "
                "published the count as the entity's TOTAL enrollment (state "
                "1.53M/1.60M vs 10k-33k every other year) while the rate "
                "stayed correct. The count is NULLed in those two years "
                "wherever the rate is < 0.95 or NULL; genuine "
                "all-alternative entities (rate >= 0.95) keep their count. "
                "The rate is always preserved."
            ),
            (
                "Suppression regimes: no TFS through 2020; 2021-2022 TFS "
                "hits the 9 program count columns only (rates stay "
                "numeric); 2023-2024 TFS extends to the program percentage "
                "columns as well."
            ),
            (
                "Every covered year produces exactly one state row per "
                "program, and every entity-year carries exactly nine "
                "program rows."
            ),
        ],
        quality_checks=[
            {
                "name": "nine_program_rows_per_entity_year",
                "description": (
                    "Structural fact: the unpivot emits one row per program "
                    "for all nine state instructional programs at every "
                    "entity-year (non-applicable programs carry NULL metrics "
                    "rather than being dropped), so every (year, "
                    "district_code, school_code) group must contain exactly "
                    "nine rows. GROUP BY treats NULL geography keys as "
                    "equal, which matches entity identity across detail "
                    "levels."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, school_code "
                    "FROM {object} "
                    "GROUP BY year, district_code, school_code "
                    "HAVING COUNT(*) <> 9) AS bad_entities"
                ),
                "mustBe": 0,
            },
            {
                "name": "special_ed_pk_rate_null_pre_2013",
                "description": (
                    "Structural fact of the documented mask: pre-2013 GOSA "
                    "published special_ed_pk rates on a different, "
                    "undocumented denominator, so every special_ed_pk row "
                    "before 2013 must carry a NULL participation_rate "
                    "(num_students remains populated)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE program = 'special_ed_pk' AND year < 2013 "
                    "AND participation_rate IS NOT NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "alt_programs_count_kept_only_for_all_alt_entities_2011_2019",
                "description": (
                    "Structural fact of the documented mask: in the 2011/"
                    "2019 publishing-error years an alt_programs "
                    "num_students may survive only on genuine "
                    "all-alternative entities, i.e. rows whose "
                    "participation_rate is >= 0.95. Any surviving count "
                    "with a lower or NULL rate means the publisher-error "
                    "mask regressed."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE program = 'alt_programs' AND year IN (2011, 2019) "
                    "AND num_students IS NOT NULL "
                    "AND (participation_rate IS NULL "
                    "OR participation_rate < 0.95)"
                ),
                "mustBe": 0,
            },
            {
                "name": "count_rate_co_null_outside_known_asymmetries",
                "description": (
                    "Co-null rule: bronze publishes count and rate as an "
                    "all-or-nothing pair (program-not-applicable NULLs both; "
                    "2023+ TFS suppresses both), so outside the three known "
                    "asymmetries — 2021-2022 TFS hitting only count columns, "
                    "the pre-2013 special_ed_pk rate mask, and the 2011/2019 "
                    "alt_programs count mask — num_students and "
                    "participation_rate must be NULL or non-NULL together. "
                    "Verified to hold on every other (year, program) slice."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE year NOT IN (2021, 2022) "
                    "AND NOT (program = 'special_ed_pk' AND year < 2013) "
                    "AND NOT (program = 'alt_programs' "
                    "AND year IN (2011, 2019)) "
                    "AND ((num_students IS NULL) <> "
                    "(participation_rate IS NULL))"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
