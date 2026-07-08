"""Transform bronze act_scores files into gold fact tables.

Source: Governor's Office of Student Achievement (GOSA) — ACT Scores,
2004-2024 (21 bronze files). For every Georgia public school, plus official
district and state rollups, reports the average ACT scaled score (1-36) and
the number of students tested per ACT section (`test_component`).

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Four bronze schema eras, one long gold fact.**
    * Era 1 (2004-2007, 56 wide cols): state/district/school rows encoded in
      a compound ``SysSchoolID`` (``ALL:ALL`` / ``{d}:ALL`` / ``{d}:{s}``).
      The 40 demographic score columns + 8 demographic count columns are
      dropped per structure-doc §ETL-3 (2004 populated only at state/national
      rows; 2005 holds ``' '`` placeholders; 2006-2007 blank everywhere), so
      only the five "All Students" scores + one count survive. Wide → long
      unpivot on test component (5x row expansion).
    * Era 2 (2008-2010, 8 wide cols): same compound-ID split (note the
      lowercase-d ``SysSchoolid``); already "All Students"-only. Same 5x
      unpivot.
    * Era 3 (2011-2023, 15 long cols) / Era 4 (2024, + ``#ASSMT_CD`` and
      ``HIGHEST_RECENT_IND`` constants, district column renamed to
      ``SCHOOL_DSTRCT_CD``): already long on test component. Every bronze row
      is a school row; district and state rows are materialized from the
      side-by-side ``DSTRCT_*`` / ``STATE_*`` context columns (verified
      constant within their groups), NOT re-aggregated from school rows —
      GOSA suppresses school metrics under n<10 while publishing unsuppressed
      official aggregates, so re-aggregation would undercount by ~4-18%.
- **No ``demographic`` column.** Era 1 demographic columns are dropped as
  unusable, and Eras 2-4 publish only "All Students"; per
  data-cleaning-standards §5 the column is omitted when every row would be
  ``all``.
- **National benchmark data dropped.** The 2004 ``NATIONAL`` row and the Era
  3/4 ``NATIONAL_*`` columns are out of scope — education detail levels are
  school / district / state per ``src/etl/education/CLAUDE.md``.
- **``num_tested`` semantics differ across eras.** Eras 1-2 publish a single
  per-entity count ("All Students Number Tested") which this transform
  attaches to each of the five section rows; Eras 3-4 publish true
  per-section counts. Either way, summing ``num_tested`` across
  ``test_component`` double-counts students.
- **Pinned 2004 ID repair.** Bronze 2004 carries one mangled ID,
  ``69::ALL9``. Three independent proofs identify it as the ``699:ALL``
  district-total row for Meriwether County: (a) 699 is the only district
  with school rows but no ``:ALL`` row in 2004; (b) its count (35) equals
  the sum of the two 699 schools' counts (14 + 21); (c) its composite (15.7)
  equals the schools' count-weighted blend (15.74); and 2005 publishes a
  normal ``699:All`` row. The transform repairs the literal ``69::ALL9`` to
  ``699:ALL`` (logged); any OTHER malformed ID has no such proof and is
  dropped with a warning instead.
- **Pinned 2007 district-row swap repair.** In the 2007 bronze, the
  ``{d}:ALL`` district-total rows of three county/city name-twin pairs carry
  each other's values — Calhoun County (619) <-> Calhoun City (765), Decatur
  County (643) <-> City Schools of Decatur (773), Jefferson County (681) <->
  Jefferson City (779). Proof: each 2007 district row is byte-for-byte its
  twin's school row (e.g. ``643:ALL`` "Decatur County" 22.6/22.5/22.5/23.3/
  21.7 | 61 == ``773:3050`` Decatur High School), while in 2004-2006 and
  2008 each of these single-school districts' ``:ALL`` row equals its OWN
  school row exactly. The school rows carry correct IDs and names in 2007 —
  only the district rows are crossed, so the transform re-attributes the six
  district rows symmetrically (``DISTRICT_ROW_SWAPS_2007``, logged), the
  same pinned-repair philosophy as ``SYS_ID_REPAIRS``.
- **2022 placeholder twins.** The 2022 file lists two school rows for the
  same ``(district, school code, component)`` key when a school was renamed
  (e.g. "Cass High School" with data next to "New Cass High School" with
  all-null metrics; 20 key groups, 20 all-null rows). The all-null twin
  carries no information and is dropped explicitly (logged via
  ``record_filtered``) BEFORE the natural-key collision guard, so the guard
  still catches genuinely divergent duplicates.
- **§4b known-bad masks.** Two pinned defect classes are NULLed by
  ``_null_invalid_act_scores`` (rows and ``num_tested`` preserved): (a) the
  2006 bronze publishes 10 impossible ``avg_score`` values (36.9-41.5, above
  the ACT 1-36 scale) for Campbell High School (633:1054) and Cedar Grove
  High School (644:0172) — any ``avg_score`` outside [1, 36] is NULLed and
  the contract pins ``value_min: 1`` / ``value_max: 36`` so the range check
  stays enforceable; (b) the 2009 ``761:ALL`` Atlanta City district row
  publishes 34.2-35.5, but the district's own 14 school rows (945 of its
  949 students, composites 15.4-20.2) bound every component at <= 17.70
  even with all unattributed students at a perfect 36 — provably impossible
  and unrecoverable, so the five district ``avg_score`` values are NULLed.
- **2016 writing scale anomaly (documented, not changed).** ACT's
  September 2015 - June 2016 "enhanced writing" window reported the Writing
  subscore on a 1-36 scale: gold 2016 ``writing_subscore`` runs 11.8-23.1
  (mean 17.2) vs 4.2-8.5 (mean ~6.6) in every other year. Bronze-faithful;
  documented in the contract and enforced by a quality check that pins the
  2-12 scale in every year except 2016.
- **2010 district rows are internally inconsistent (documented).** ~30
  districts' published 2010 ``{d}:ALL`` means fall outside the feasible
  range implied by their own school rows, in both directions (e.g. 615
  Bryan County composite 19.6|89 vs a 21.37 school-weighted floor; 792
  Valdosta City science 14.6|111 vs its only school's 18.2|110), and the
  2010 state count (39,436) is an outlier vs 2009/2011. Both row sets come
  from the same bronze file and neither is provably wrong — likely a
  cohort/basis difference, not row-level typos — so the rows are preserved
  and the basis question is documented as a contract caveat.
- **Dedup tie-break.** Each bronze file covers a distinct year and the eras
  do not overlap, so duplicates can only arise within a single file. After
  the placeholder-twin drop, none are expected; ``sort_col="num_tested"``
  remains as the documented safety net (prefer the row with a reported,
  larger count over a suppressed placeholder).
"""

import logging
from pathlib import Path

import polars as pl

from src.utils.metadata import write_data_dictionary
from src.utils.readers import (
    extract_year_from_filename,
    list_bronze_files,
    parse_school_year,
    read_bronze_file,
)
from src.utils.transformers import (
    TransformManifest,
    assert_no_natural_key_collisions,
    deduplicate_by_detail_level,
    detect_era_by_columns,
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

TOPIC = "act_scores"
BRONZE_DIR = Path("data/bronze/education/gosa/act_scores")
GOLD_DIR = Path("data/gold/education/act_scores")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Single source of truth for the test_component vocabulary across all eras.
# Era 3/4 carry the bare labels as TEST_CMPNT_TYP_CD values; Era 1/2 carry
# the categorical in their wide score-column HEADERS ("... All Students"),
# which the unpivot surfaces as raw values mapped through this same dict so
# the manifest records the true bronze labels. "Science Reasoning" (Era 1/2)
# and "Science" (Era 3/4) are the same ACT section -> one canonical value.
TEST_COMPONENT_MAP: dict[str, str] = {
    # Era 3/4 TEST_CMPNT_TYP_CD values.
    "Composite": "composite",
    "English": "english",
    "Mathematics": "mathematics",
    "Reading": "reading",
    "Science": "science",
    "Writing Subscore": "writing_subscore",
    "Combined English Writing": "combined_english_writing",
    # Era 1/2 wide score-column names (categorical embedded in the header).
    "Composite All Students": "composite",
    "English All Students": "english",
    "Mathematics All Students": "mathematics",
    "Reading All Students": "reading",
    "Science Reasoning All Students": "science",
}

# The five Era 1/2 "All Students" score columns kept after dropping the 48
# unusable demographic columns. Exact header strings are load-bearing.
ERA12_SCORE_COLUMNS: list[str] = [
    "Composite All Students",
    "English All Students",
    "Mathematics All Students",
    "Reading All Students",
    "Science Reasoning All Students",
]
ERA12_COUNT_COLUMN = "All Students Number Tested"

# Era 3/4 metric column pairs per detail level: (count column, score column).
ERA34_LEVEL_METRICS: dict[str, tuple[str, str]] = {
    "school": ("INSTN_NUM_TESTED_CNT", "INSTN_AVG_SCORE_VAL"),
    "district": ("DSTRCT_NUM_TESTED_CNT", "DSTRCT_AVG_SCORE_VAL"),
    "state": ("STATE_NUM_TESTED_CNT", "STATE_AVG_SCORE_VAL"),
}

# Era-detection signatures, most-specific first (Era 4 is an Era-3 superset;
# Era 1 and Era 2 differ by ID-column casing and the demographic columns).
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_4": ["#ASSMT_CD", "SCHOOL_DSTRCT_CD", "TEST_CMPNT_TYP_CD"],
    "era_3": ["LONG_SCHOOL_YEAR", "SCHOOL_DISTRCT_CD", "TEST_CMPNT_TYP_CD"],
    # Era 1 has the demographic columns Era 2 dropped; the uppercase-D
    # SysSchoolID plus one demographic column is unique to Era 1.
    "era_1": ["SysSchoolID", "Composite Asian-American/Pacific Islander"],
    # Era 2: lowercase-d SysSchoolid (a distinct string to polars).
    "era_2": ["SysSchoolid", "Composite All Students"],
}

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "test_component",
    "num_tested",
    "avg_score",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "test_component": pl.Utf8,
    "num_tested": pl.Int64,
    "avg_score": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = ["num_tested", "avg_score"]

NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "test_component",
    "detail_level",
]

# Valid ACT scaled-score range; values outside it are impossible (§4b).
ACT_SCORE_MIN = 1.0
ACT_SCORE_MAX = 36.0

# The one proven 2004 ID repair (see module docstring). Keyed on the literal
# bronze string so it can never touch any other row.
SYS_ID_REPAIRS: dict[str, str] = {"69::ALL9": "699:ALL"}

# Pinned 2007-only repair of swapped district-total rows (see module
# docstring). In the 2007 bronze, the `{d}:ALL` rows of three county/city
# name-twin pairs carry each other's values — each district's row is
# byte-for-byte its twin's school row, while in 2004-2006 and 2008 each of
# these single-school districts' `:ALL` row equals its OWN school row
# exactly. Applied symmetrically to district rows in the 2007 file only.
DISTRICT_ROW_SWAPS_2007: dict[str, str] = {
    "619": "765",  # Calhoun County <-> Calhoun City
    "765": "619",
    "643": "773",  # Decatur County <-> City Schools of Decatur
    "773": "643",
    "681": "779",  # Jefferson County <-> Jefferson City
    "779": "681",
}

# Pinned §4b mask for the 2009 Atlanta City district row (see module
# docstring): bronze publishes avg scores of 34.2-35.5 for `761:ALL`, but the
# district's own school rows bound every component at <= 17.70 — the values
# are provably impossible and unrecoverable, so avg_score is NULLed
# (num_tested 949 is consistent with the school rows and preserved).
INFEASIBLE_2009_ATLANTA_DISTRICT = "761"


# =============================================================================
# Casting helpers
# =============================================================================


def _to_float_expr(col: str) -> pl.Expr:
    """Cast a bronze metric column to Float64 through a string round-trip.

    Bronze sources mix dtypes per year (CSV-inferred floats, xls-as-string
    "20.8", 2005's ``' '`` placeholders, 2024's trailing-dot "1374791.").
    Casting to Utf8 first, stripping, then a non-strict Float64 cast handles
    all of them; non-numeric residue becomes NULL.
    """
    return pl.col(col).cast(pl.Utf8).str.strip_chars().cast(pl.Float64, strict=False)


def _to_int_expr(col: str) -> pl.Expr:
    """Cast a bronze count column to Int64 via Float64.

    The Float64 hop tolerates xls string counts ("16", "16.0") and
    trailing-dot formatting; counts are integral so the Int64 cast is exact.
    """
    return _to_float_expr(col).cast(pl.Int64)


def _require_columns(df: pl.DataFrame, required: list[str], label: str) -> None:
    """Raise if any expected bronze column is absent (rename-coverage guard).

    An unmatched source column silently becomes NULL in gold — the most
    common data-loss bug — so a missing expected column is a hard stop.
    """
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"{label}: expected bronze column(s) missing: {missing}. "
            f"Present: {df.columns}"
        )


# =============================================================================
# Era 1 & 2 (2004-2010): compound-ID wide format
# =============================================================================


def _split_compound_id(
    df: pl.DataFrame,
    id_col: str,
    year: int,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Repair, classify, and split the Era 1/2 compound ``SysSchool*`` ID.

    Adds ``detail_level`` (state/district/school) plus ``_district_raw`` /
    ``_school_raw`` part columns; drops national benchmark rows and any
    malformed IDs (both logged via ``record_filtered``).
    """
    # Pinned repair of the proven 2004 ID typo before any classification.
    ids = pl.col(id_col).cast(pl.Utf8).str.strip_chars()
    n_repaired = df.filter(ids.is_in(list(SYS_ID_REPAIRS.keys()))).height
    if n_repaired:
        logger.warning(
            "Year %d: repairing %d mangled SysSchoolID(s) %s — see module "
            "docstring for the arithmetic proof",
            year,
            n_repaired,
            SYS_ID_REPAIRS,
        )
    df = df.with_columns(ids.replace(SYS_ID_REPAIRS).alias("_id"))

    # Classify detail level from the compound ID. The ALL sentinel comparison
    # is case-insensitive because 2005 publishes `All:All` / `{d}:All` while
    # 2004/2006/2007 publish `ALL:ALL` / `{d}:ALL`.
    df = df.with_columns(pl.col("_id").str.to_uppercase().alias("_id_upper"))
    df = df.with_columns(
        pl.when(pl.col("_id_upper") == "NATIONAL")
        .then(pl.lit("national"))
        .when(pl.col("_id_upper") == "ALL:ALL")
        .then(pl.lit("state"))
        .when(pl.col("_id_upper").str.ends_with(":ALL"))
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .alias("detail_level")
    )

    # National benchmark rows (2004 only) are out of scope for the
    # school/district/state detail levels.
    n_national = df.filter(pl.col("detail_level") == "national").height
    if n_national:
        manifest.record_filtered(year, n_national, "national_benchmark_row")
        df = df.filter(pl.col("detail_level") != "national")

    # Split the compound ID on the first colon into district / school parts.
    df = df.with_columns(
        pl.col("_id")
        .str.split_exact(":", 1)
        .struct.rename_fields(["_district_raw", "_school_raw"])
        .alias("_parts")
    ).unnest("_parts")

    # Malformed-ID guard: district part must be digits for district/school
    # rows, school part must be digits for school rows. No proof exists for
    # repairing unknown malformations, so they are dropped loudly.
    malformed = (
        pl.col("detail_level").is_in(["district", "school"])
        & ~pl.col("_district_raw").str.contains(r"^\d+$")
    ) | (
        (pl.col("detail_level") == "school")
        & ~pl.col("_school_raw").str.contains(r"^\d+$")
    )
    bad = df.filter(malformed)
    if bad.height:
        logger.warning(
            "Year %d: dropping %d row(s) with malformed %s: %s",
            year,
            bad.height,
            id_col,
            bad["_id"].head(5).to_list(),
        )
        manifest.record_filtered(year, bad.height, "malformed_sys_school_id")
        df = df.filter(~malformed)
    return df


def _transform_era12(
    df: pl.DataFrame,
    year: int,
    id_col: str,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Transform an Era 1/2 wide file into long gold rows.

    Splits the compound ``SysSchoolID``/``SysSchoolid`` into geography keys +
    ``detail_level``, drops national rows, and unpivots the five "All
    Students" score columns into one row per test component, attaching the
    single per-entity count to each.

    Args:
        df: Bronze DataFrame.
        year: Reporting year (from the filename; Era 1/2 carry no year column).
        id_col: ``SysSchoolID`` (Era 1) or ``SysSchoolid`` (Era 2).
        manifest: Manifest for categorical / filter recording.

    Returns:
        Long DataFrame with STANDARD_COLUMNS.
    """
    _require_columns(
        df, [id_col, *ERA12_SCORE_COLUMNS, ERA12_COUNT_COLUMN], f"era_1/2 {year}"
    )
    dropped_cols = [
        c
        for c in df.columns
        if c not in {id_col, "School Name", *ERA12_SCORE_COLUMNS, ERA12_COUNT_COLUMN}
    ]
    if dropped_cols:
        # Demographic score/count columns are unusable in Era 1 (see module
        # docstring); names live in dimension tables, not facts.
        logger.info(
            "Year %d: dropping %d demographic columns (unusable per "
            "bronze-data-structure.md §ETL-3)",
            year,
            len(dropped_cols),
        )

    df = _split_compound_id(df, id_col, year, manifest)

    # Pinned 2007 repair: re-attribute the swapped county/city district-total
    # rows to their true districts (see DISTRICT_ROW_SWAPS_2007). Only the
    # district part of district-level rows is remapped — school rows carry
    # the correct IDs/names in the 2007 bronze and are untouched.
    if year == 2007:
        swap_targets = pl.col("detail_level").eq("district") & pl.col(
            "_district_raw"
        ).is_in(list(DISTRICT_ROW_SWAPS_2007.keys()))
        n_swapped = df.filter(swap_targets).height
        if n_swapped:
            logger.warning(
                "Year %d: re-attributing %d swapped district-total row(s) "
                "between county/city name twins %s — see module docstring "
                "for the four-year mirror proof",
                year,
                n_swapped,
                sorted(DISTRICT_ROW_SWAPS_2007.items()),
            )
            df = df.with_columns(
                pl.when(swap_targets)
                .then(pl.col("_district_raw").replace(DISTRICT_ROW_SWAPS_2007))
                .otherwise(pl.col("_district_raw"))
                .alias("_district_raw")
            )

    # Geography keys: zero-pad per domain CLAUDE.md; aggregate levels get
    # NULLs (null_aggregate_geography re-asserts this in main()).
    df = df.with_columns(
        pl.when(pl.col("detail_level") == "state")
        .then(None)
        .otherwise(pl.col("_district_raw").str.zfill(3))
        .alias("district_code"),
        pl.when(pl.col("detail_level") != "school")
        .then(None)
        .otherwise(pl.col("_school_raw").str.zfill(4))
        .alias("school_code"),
        pl.lit(year).cast(pl.Int32).alias("year"),
        _to_int_expr(ERA12_COUNT_COLUMN).alias("num_tested"),
    )

    # Wide -> long: one row per test component. The single per-entity count
    # is attached to each of the five component rows (Era 1/2 publish one
    # administration-level count, not per-section counts).
    long_df = df.unpivot(
        on=ERA12_SCORE_COLUMNS,
        index=["year", "district_code", "school_code", "detail_level", "num_tested"],
        variable_name="_component_raw",
        value_name="_avg_raw",
    )
    long_df = long_df.with_columns(
        pl.col("_component_raw")
        .replace_strict(TEST_COMPONENT_MAP, default=None)
        .alias("test_component"),
        _to_float_expr("_avg_raw").alias("avg_score"),
    )
    manifest.record_categorical(
        column="test_component",
        map_dict=TEST_COMPONENT_MAP,
        bronze_series=long_df["_component_raw"],
        gold_series=long_df["test_component"],
    )

    return long_df.select(STANDARD_COLUMNS)


# =============================================================================
# Era 3 & 4 (2011-2024): long format with side-by-side aggregates
# =============================================================================


def _drop_placeholder_twins(
    schools: pl.DataFrame,
    year: int,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Drop all-null school rows that duplicate a data-carrying key (2022).

    The 2022 file repeats 20 (district, school, component) keys with an
    all-null metric row under a renamed school name (e.g. "New Cass High
    School" next to "Cass High School" with data). The all-null twin carries
    no information — dropping it explicitly (logged) lets the collision
    guard still catch genuinely divergent duplicates. Lone all-null rows
    (suppressed schools) are preserved.
    """
    key = ["year", "district_code", "school_code", "test_component"]
    schools = schools.with_columns(
        (pl.col("num_tested").is_not_null() | pl.col("avg_score").is_not_null()).alias(
            "_has_data"
        )
    ).with_columns(
        pl.len().over(key).alias("_n"),
        pl.col("_has_data").any().over(key).alias("_group_has_data"),
    )
    placeholder = (pl.col("_n") > 1) & pl.col("_group_has_data") & ~pl.col("_has_data")
    n_placeholder = schools.filter(placeholder).height
    if n_placeholder:
        logger.warning(
            "Year %d: dropping %d all-null placeholder school row(s) that "
            "duplicate a data-carrying row (renamed-school twins)",
            year,
            n_placeholder,
        )
        manifest.record_filtered(year, n_placeholder, "all_null_duplicate_school_row")
        schools = schools.filter(~placeholder)
    return schools.drop(["_has_data", "_n", "_group_has_data"])


def _validate_era34_constants(df: pl.DataFrame, year: int) -> None:
    """Hard-stop if the Era 3/4 constant columns carry unexpected values.

    SUBGRP_DESC must be 'All Students' (anything else changes the fact grain
    to demographic breakdowns and must be analyzed, not silently collapsed);
    Era 4's #ASSMT_CD must be 'ACT' (anything else means non-ACT rows are
    mixed into this topic's bronze).
    """
    subgroups = df["SUBGRP_DESC"].drop_nulls().unique().to_list()
    if subgroups != ["All Students"]:
        raise ValueError(
            f"era_3/4 {year}: unexpected SUBGRP_DESC values {subgroups}; "
            "the transform assumes the All Students-only grain"
        )
    if "#ASSMT_CD" in df.columns:
        assessments = df["#ASSMT_CD"].drop_nulls().unique().to_list()
        if assessments != ["ACT"]:
            raise ValueError(f"era_4 {year}: unexpected #ASSMT_CD values {assessments}")


def _era34_aggregate_rows(base: pl.DataFrame, level: str) -> pl.DataFrame:
    """Materialize official district/state rows from Era 3/4 context columns.

    The DSTRCT_* / STATE_* values are constant within their group (verified
    for every year 2011-2024), so selecting group keys + metrics and calling
    ``unique()`` yields exactly one row per group — any divergence would
    surface as duplicate keys and trip the collision guard in ``main()``.
    """
    num_col, avg_col = ERA34_LEVEL_METRICS[level]
    group_keys = (
        ["year", "district_code", "test_component"]
        if level == "district"
        else ["year", "test_component"]
    )
    nulled_geo = (
        ["school_code"] if level == "district" else ["district_code", "school_code"]
    )
    return (
        base.select(
            *group_keys,
            _to_int_expr(num_col).alias("num_tested"),
            _to_float_expr(avg_col).alias("avg_score"),
        )
        .unique()
        .with_columns(
            pl.lit(level).alias("detail_level"),
            *[pl.lit(None).cast(pl.Utf8).alias(c) for c in nulled_geo],
        )
    )


def _transform_era34(
    df: pl.DataFrame,
    year: int,
    district_col: str,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Transform an Era 3/4 long file into gold rows at three detail levels.

    Every bronze row is one (school x test component) observation carrying
    district/state context columns. School rows map 1:1; district and state
    rows are materialized from the official context columns via ``unique()``
    (constant within their groups — divergence would surface as duplicate
    keys and trip the collision guard in ``main()``).

    Args:
        df: Bronze DataFrame.
        year: Year parsed from ``LONG_SCHOOL_YEAR`` (already cross-checked
            against the filename by the caller).
        district_col: ``SCHOOL_DISTRCT_CD`` (Era 3) or ``SCHOOL_DSTRCT_CD``
            (Era 4 renamed it).
        manifest: Manifest for categorical / filter recording.

    Returns:
        Long DataFrame with STANDARD_COLUMNS (school + district + state rows).
    """
    metric_cols = [c for pair in ERA34_LEVEL_METRICS.values() for c in pair]
    _require_columns(
        df,
        [district_col, "INSTN_NUMBER", "SUBGRP_DESC", "TEST_CMPNT_TYP_CD"]
        + metric_cols,
        f"era_3/4 {year}",
    )

    _validate_era34_constants(df, year)

    base = df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        # zfill(3) pads 3-digit county codes and passes 7-digit
        # state-charter codes through unchanged (never truncate).
        pl.col(district_col)
        .cast(pl.Utf8)
        .str.strip_chars()
        .str.zfill(3)
        .alias("district_code"),
        # School codes are zero-padded to 4 chars so inconsistently-padded
        # early Era 3 codes ('100' vs '0100') compare across years.
        pl.col("INSTN_NUMBER")
        .cast(pl.Utf8)
        .str.strip_chars()
        .str.zfill(4)
        .alias("school_code"),
        pl.col("TEST_CMPNT_TYP_CD")
        .replace_strict(TEST_COMPONENT_MAP, default=None)
        .alias("test_component"),
    )
    manifest.record_categorical(
        column="test_component",
        map_dict=TEST_COMPONENT_MAP,
        bronze_series=base["TEST_CMPNT_TYP_CD"],
        gold_series=base["test_component"],
    )

    school_num, school_avg = ERA34_LEVEL_METRICS["school"]
    schools = base.select(
        "year",
        "district_code",
        "school_code",
        "test_component",
        _to_int_expr(school_num).alias("num_tested"),
        _to_float_expr(school_avg).alias("avg_score"),
    ).with_columns(pl.lit("school").alias("detail_level"))
    schools = _drop_placeholder_twins(schools, year, manifest)

    # District and state rows come from the official side-by-side context
    # columns (never re-aggregated from suppressed school rows).
    districts = _era34_aggregate_rows(base, "district")
    states = _era34_aggregate_rows(base, "state")

    logger.info(
        "Year %d: materialized %d school, %d district, %d state rows",
        year,
        schools.height,
        districts.height,
        states.height,
    )
    return pl.concat(
        [
            schools.select(STANDARD_COLUMNS),
            districts.select(STANDARD_COLUMNS),
            states.select(STANDARD_COLUMNS),
        ]
    )


# =============================================================================
# File routing
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame:
    """Read one bronze file, detect its era, and route to the era transform.

    Year resolution follows bronze-data-structure.md §ETL-1/§ETL-13: Era 1/2
    files carry no year column (filename year is the reporting year); Era 3/4
    derive the year from ``LONG_SCHOOL_YEAR`` and cross-check the filename so
    a silently misnamed file cannot mislabel a whole year.

    Args:
        path: Bronze file path.
        manifest: Manifest for read-loss / file / bronze-count recording.

    Returns:
        Gold-shaped DataFrame for this file.
    """
    df, loss = read_bronze_file(path, return_loss=True)
    filename_year = extract_year_from_filename(path.name)
    if filename_year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")
    manifest.record_read_loss(
        filename_year, path.name, loss["raw_rows"], loss["parsed_rows"]
    )

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{path.name}: no era signature matched columns {df.columns}")

    if era in ("era_3", "era_4"):
        # Exactly one LONG_SCHOOL_YEAR value per file; its ending year must
        # agree with the filename year.
        school_years = df["LONG_SCHOOL_YEAR"].drop_nulls().unique().to_list()
        if len(school_years) != 1:
            raise ValueError(
                f"{path.name}: expected one LONG_SCHOOL_YEAR, got {school_years}"
            )
        year = parse_school_year(school_years[0])
        if year != filename_year:
            raise ValueError(
                f"{path.name}: LONG_SCHOOL_YEAR ending year {year} disagrees "
                f"with filename year {filename_year}"
            )
    else:
        year = filename_year

    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)
    logger.info("Processing %s as %s (year %d)", path.name, era, year)

    if era == "era_1":
        return _transform_era12(df, year, "SysSchoolID", manifest)
    if era == "era_2":
        return _transform_era12(df, year, "SysSchoolid", manifest)
    if era == "era_3":
        return _transform_era34(df, year, "SCHOOL_DISTRCT_CD", manifest)
    return _transform_era34(df, year, "SCHOOL_DSTRCT_CD", manifest)


# =============================================================================
# §4b known-bad mask
# =============================================================================


def _null_invalid_act_scores(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """NULL ``avg_score`` values that are provably impossible (§4b).

    Two pinned defect classes, both NULLed — the same convention as
    suppression — while ``num_tested`` and the rows are preserved:

    * **Out-of-scale values.** ACT scaled scores are defined on 1-36; values
      outside that range are publication errors, not data. The known case:
      2006 bronze carries 10 values of 36.9-41.5 for Campbell High School
      (633:1054) and Cedar Grove High School (644:0172). The contract pins
      ``value_min: 1`` / ``value_max: 36`` so the derived range check remains
      an enforceable invariant.
    * **The 2009 Atlanta City district row.** Bronze publishes 34.2-35.5 for
      ``761:ALL`` while the district's own 14 school rows (945 of its 949
      students) bound every component at <= 17.70 even if every unattributed
      student scored a perfect 36 — provably impossible, true values
      unrecoverable, so the five district ``avg_score`` values are NULLed
      (the consistent ``num_tested`` of 949 is preserved).

    Args:
        df: Combined gold-shaped DataFrame (post dedup / geography nulling).

    Returns:
        DataFrame with impossible ``avg_score`` set to NULL.
    """
    out_of_range = pl.col("avg_score").is_not_null() & (
        (pl.col("avg_score") < ACT_SCORE_MIN) | (pl.col("avg_score") > ACT_SCORE_MAX)
    )
    infeasible_atlanta_2009 = (
        pl.col("avg_score").is_not_null()
        & (pl.col("year") == 2009)
        & (pl.col("detail_level") == "district")
        & (pl.col("district_code") == INFEASIBLE_2009_ATLANTA_DISTRICT)
    )
    masked = out_of_range | infeasible_atlanta_2009
    invalid = df.filter(masked)
    if invalid.height:
        # §4b masks are recorded in the manifest so the data review verifies
        # counts from an artifact rather than scraping runtime logs.
        n_oor = df.filter(out_of_range).height
        n_atl = df.filter(infeasible_atlanta_2009).height
        if n_oor:
            manifest.record_masked(
                "avg_score", n_oor, "outside_act_1_36_scale", years=[2006]
            )
        if n_atl:
            manifest.record_masked(
                "avg_score",
                n_atl,
                "infeasible_2009_atlanta_district_row",
                years=[2009],
            )
        logger.warning(
            "§4b: NULLing %d impossible avg_score value(s) — outside "
            "[%g, %g] or the pinned infeasible 2009 Atlanta district row "
            "(years %s; sample %s)",
            invalid.height,
            ACT_SCORE_MIN,
            ACT_SCORE_MAX,
            sorted(invalid["year"].unique().to_list()),
            invalid.select(
                "year", "district_code", "school_code", "test_component", "avg_score"
            )
            .head(15)
            .to_dicts(),
        )
    return df.with_columns(
        pl.when(masked).then(None).otherwise(pl.col("avg_score")).alias("avg_score")
    )


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for act_scores."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file (read-loss accounted per file).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR):
        result = transform_file(path, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize columns/dtypes across eras and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)
    logger.info("Combined %d rows across %d files", combined.height, len(all_dfs))

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean an alias/aggregation bug and must raise, not be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: every bronze file is a distinct year and eras don't overlap,
    # so duplicates can only be within-file repeats; prefer the row with a
    # reported (non-null, larger) num_tested over a suppressed placeholder.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code", "test_component"],
        district_keys=["year", "district_code", "test_component"],
        state_keys=["year", "test_component"],
        sort_col="num_tested",
    )

    # 4. Geography nulling (shared domain rules), then the §4b mask.
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )
    combined = _null_invalid_act_scores(combined, manifest)

    # Pre-export sanity: NULL-rate spikes are warnings with a documented,
    # bronze-real cause — Georgia ACT participation fell sharply from 2021
    # (COVID + test-optional admissions), so far more schools fall under the
    # n<10 suppression threshold: bronze school-row suppression is ~37% in
    # 2021, ~28% in 2022, ~37% in 2024 vs ~10% in 2015.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(
        combined, required_non_null=["year", "detail_level", "test_component"]
    )

    # 5. Manifest stats on the FINAL DataFrame, then export.
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(combined, GOLD_DIR, STANDARD_COLUMNS)
    manifest.write(GOLD_DIR)

    # 6. Contract + README from the in-code column declaration.
    _emit_contract_and_readme(
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


def _emit_contract_and_readme(year_range: tuple[int, int]) -> None:
    """Emit the ODCS contract and gold README via ``write_data_dictionary``.

    Kept out of ``main()`` so the pipeline flow stays readable. The column
    declaration order MUST match STANDARD_COLUMNS minus ``detail_level`` —
    the contract's properties (and the validator's schema check) follow it.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Average ACT scaled scores (1-36) and number of students tested "
            "for Georgia public schools, with official district and state "
            "rollups, by ACT test component. Covers graduating-class ACT "
            "results published by GOSA from 2004 through 2024."
        ),
        title="ACT College Readiness Test Scores",
        summary=(
            "Average ACT college-admissions test scores and number of "
            "students tested, by Georgia school, district, and ACT section, "
            "2004-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Reporting year. For 2011-2024 this is the spring (ending) "
                    "calendar year of the school year in the source's "
                    "LONG_SCHOOL_YEAR; for 2004-2010 the source carries no "
                    "year column and the filename publication year is used."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "GOSA district code (FK to districts dimension): 3-digit "
                    "zero-padded county/city codes or 7-digit state-charter "
                    "codes. NULL on state-level rows."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0103",
                "description": (
                    "GOSA school code, zero-padded to 4 characters (composite "
                    "FK to schools dimension with district_code; not globally "
                    "unique on its own). NULL on district- and state-level rows."
                ),
            },
            {
                "name": "test_component",
                "type": "string",
                "nullable": False,
                "example": "composite",
                "validValues": sorted(set(TEST_COMPONENT_MAP.values())),
                "short_description": (
                    "Which ACT section the score covers: composite (overall), "
                    "english, mathematics, reading, science, or writing."
                ),
                "description": (
                    "ACT section. composite, english, mathematics, reading, "
                    "and science are reported in all years (2004-2010 label "
                    "science as 'Science Reasoning'); writing_subscore appears "
                    "from 2011 onward; combined_english_writing only in "
                    "2011-2015 (students who took both English and the "
                    "optional Writing section)."
                ),
            },
            {
                "name": "num_tested",
                "type": "int64",
                "metric_component": "denominator",
                "unit": "count",
                "example": 24,
                "null_meaning": (
                    "Suppressed by GOSA (too few students to report; "
                    "TFS marker in 2011-2024 sources)."
                ),
                "description": (
                    "Number of students tested. 2004-2010 sources publish one "
                    "count per school/district/state entity, which is repeated "
                    "on each of that entity's five test_component rows; "
                    "2011-2024 sources publish true per-component counts. In "
                    "either case, summing num_tested across test_component "
                    "double-counts students — filter to one component "
                    "(typically composite) for headcounts."
                ),
            },
            {
                "name": "avg_score",
                "type": "float64",
                "key_metric": True,
                "unit": "score",
                "value_min": 1,
                "value_max": 36,
                "example": 18.1,
                "short_description": (
                    "Average ACT scaled score on the 1-36 scale (writing "
                    "subscore uses a 2-12 scale, except 2016); higher is "
                    "better."
                ),
                "null_meaning": (
                    "Suppressed by GOSA (too few test-takers), or one of 15 "
                    "impossible source values (10 in 2006, 5 in 2009) NULLed "
                    "by the transform."
                ),
                "description": (
                    "Average ACT scaled score. The 1-36 ACT scale applies to "
                    "every test_component except writing_subscore, which the "
                    "source reports on the ACT writing domain 2-12 scale "
                    "(typical statewide averages 6-7) in every year EXCEPT "
                    "2016: ACT's September 2015-June 2016 'enhanced writing' "
                    "window reported writing on a 1-36 scale, so 2016 "
                    "writing_subscore values run 11.8-23.1 (mean ~17.2) vs "
                    "4.2-8.5 in all other years — do not read 2016 as a "
                    "writing-performance jump in time series. The [1, 36] "
                    "range check below bounds all components and years. NULL "
                    "when GOSA suppressed the value (too few test-takers). "
                    "Known source defects NULLed by the transform per "
                    "data-cleaning-standards §4b (rows and num_tested "
                    "preserved): (a) the 2006 publication reported 10 "
                    "impossible values of 36.9-41.5 (above the ACT scale "
                    "maximum of 36) across the five sections for Campbell "
                    "High School (district 633, school 1054) and Cedar Grove "
                    "High School (district 644, school 0172) — any avg_score "
                    "outside [1, 36] is NULLed; (b) the 2009 Atlanta City "
                    "district rows (district 761) published scores of "
                    "34.2-35.5 while the district's own school rows bound "
                    "every section at or below 17.7 — the five district "
                    "avg_score values are NULLed (num_tested 949 is "
                    "consistent with the school rows and preserved). This "
                    "revises the preserve-bronze default for this column; "
                    "the 1-36 range check below remains enforceable because "
                    "of it."
                ),
            },
        ],
        source="GOSA",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        # Derived prose plus two source-data caveats contract consumers need:
        # the 2010 district-row basis inconsistency and the 2016 writing scale.
        limitations=(
            "Suppressed cells are NULL (not zero). State rows have NULL "
            "district_code and school_code. District rows have NULL "
            "school_code. 2010 caveat: the 2010 source's district-total rows "
            "are internally inconsistent with its own school rows (~30 "
            "districts' published means fall outside the feasible range "
            "implied by their school rows, in both directions; the 2010 "
            "state count is also an outlier vs adjacent years); the "
            "reporting basis is unknown and the published rows are preserved "
            "unchanged — use 2010 district aggregates with caution. 2016 "
            "writing_subscore is on a 1-36 scale (ACT's 'enhanced writing' "
            "window) vs the 2-12 writing domain scale in every other year."
        ),
        notes=[
            (
                "District and state rows are the official GOSA aggregates "
                "(2004-2010: published rollup rows; 2011-2024: the DSTRCT_*/"
                "STATE_* context columns), never re-aggregated from school "
                "rows — school-level suppression (n<10) would undercount "
                "official totals by ~4-18%."
            ),
            (
                "National benchmark data (the 2004 NATIONAL row and the "
                "2011-2024 NATIONAL_* columns) is out of scope and dropped."
            ),
            (
                "num_tested semantics differ across eras: 2004-2010 publish "
                "one per-entity count repeated across that entity's five "
                "component rows; 2011-2024 publish per-component counts. "
                "Never sum num_tested across test_component."
            ),
            (
                "2004 source typo '69::ALL9' is repaired to '699:ALL' "
                "(Meriwether County district total): 699 is the only district "
                "missing a rollup row that year, and the row's count (35) and "
                "composite (15.7) match the sum (14+21) and count-weighted "
                "blend (15.74) of the two 699 schools exactly."
            ),
            (
                "2007 source defect, repaired: the district-total rows of "
                "three county/city name-twin pairs were swapped at the "
                "source — Calhoun County (619) <-> Calhoun City (765), "
                "Decatur County (643) <-> City Schools of Decatur (773), "
                "Jefferson County (681) <-> Jefferson City (779). Each 2007 "
                "district row is byte-for-byte its twin's school row, while "
                "in 2004-2006 and 2008 each of these single-school "
                "districts' rollup equals its own school exactly; the "
                "transform re-attributes the six 2007 district rows to "
                "their true districts."
            ),
            (
                "2016 writing_subscore is on a different scale: ACT's "
                "September 2015-June 2016 'enhanced writing' window "
                "reported writing on a 1-36 scale (2016 values 11.8-23.1, "
                "mean ~17.2) vs the 2-12 writing domain scale in every "
                "other year (4.2-8.5). Bronze-faithful — not a data error; "
                "exclude or rescale 2016 in writing time series."
            ),
            (
                "2010 caveat: the 2010 source's district-total rows are "
                "internally inconsistent with its own school rows — ~30 "
                "districts' published district means fall outside the "
                "mathematically feasible range implied by their school "
                "rows, in both directions, and the 2010 state count "
                "(39,436) is an outlier vs 2009 (30,548) and 2011 (28,789). "
                "The reporting basis is unknown (possibly a different "
                "student cohort); the published rows are preserved "
                "unchanged. Use 2010 district aggregates with caution."
            ),
            (
                "The 2022 source duplicates 20 school/component keys with an "
                "all-null metrics row under a renamed school name (e.g. 'New "
                "Cass High School' alongside 'Cass High School'); the "
                "informationless all-null twins are dropped."
            ),
            (
                "2004-2007 bronze demographic score/count columns are dropped "
                "as unusable (only state/national rows ever populated, blank "
                "or whitespace elsewhere); no demographic column exists in "
                "this topic — every row is all-students."
            ),
            (
                "NULL rates for both metrics spike in 2021, 2022, and 2024 "
                "(~29-39%% vs a ~9-12%% median). This mirrors the bronze: "
                "Georgia ACT participation fell sharply from 2021 (COVID and "
                "test-optional admissions), pushing far more schools under "
                "GOSA's n<10 suppression threshold."
            ),
        ],
        quality_checks=[
            {
                "name": "avg_score_requires_positive_num_tested",
                "description": (
                    "A published average score implies at least one reported "
                    "test-taker: avg_score must not be non-NULL while "
                    "num_tested is NULL or < 1. Holds in every era (counts "
                    "are published even for suppressed-score rows)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE avg_score IS NOT NULL "
                    "AND (num_tested IS NULL OR num_tested < 1)"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_rows_never_suppressed",
                "description": (
                    "GOSA publishes unsuppressed statewide aggregates in every "
                    "era: state-level rows (district_code and school_code both "
                    "NULL) must carry non-NULL num_tested and avg_score."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE district_code IS NULL "
                    "AND school_code IS NULL "
                    "AND (num_tested IS NULL OR avg_score IS NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "combined_english_writing_year_range",
                "description": (
                    "The combined_english_writing component exists only in the "
                    "2011-2015 source files (dropped from 2016 onward, absent "
                    "before 2011)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "test_component = 'combined_english_writing' "
                    "AND (year < 2011 OR year > 2015)"
                ),
                "mustBe": 0,
            },
            {
                "name": "writing_subscore_year_range",
                "description": (
                    "The writing_subscore component first appears in the 2011 "
                    "source files; 2004-2010 bronze has no writing column."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "test_component = 'writing_subscore' AND year < 2011"
                ),
                "mustBe": 0,
            },
            {
                "name": "writing_subscore_scale_outside_2016",
                "description": (
                    "writing_subscore is on the ACT writing domain 2-12 scale "
                    "in every year except 2016 (the 1-36 'enhanced writing' "
                    "window); outside 2016 no average may exceed 12. Catches "
                    "future scale or column-swap errors."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "test_component = 'writing_subscore' AND year != 2016 "
                    "AND avg_score > 12"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
