"""Transform bronze attendance files into gold fact tables.

Source: Governor's Office of Student Achievement (GOSA) — Attendance,
2004-2024 (21 bronze files, one school year each; filename year = ending
calendar year). For every Georgia public school, plus official district and
state rollups, reports the distribution of students across three absentee
tiers (5 or fewer, 6-15, more than 15 days absent), a chronic-absence rate
(10%% or more of enrolled days; 2018+ only), and the student count in the
denominator, by demographic subgroup.

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Eight bronze eras collapse to two transform paths.** Eras 1-4 (2004-2010)
  are wide format: 60 metric columns (4 metrics x 15 demographic labels) and
  a compound ``district:school`` entity key under three identifier-casing
  variants (``SysSchoolID`` / ``sysschoolid`` / ``SchoolID``). Eras 5-8
  (2011-2024) are tidy long format keyed by ``DETAIL_LVL_DESC`` with the same
  4 metrics x 15 demographics as column-name suffixes, plus 15
  ``CHRONIC_ABSENT_PERC_*`` columns in 2011 and 2018-2024 and a leading
  constant ``#RPT_NAME`` column in 2023-2024. Era detection is by column
  signature (most-specific first), never by year range.
- **Asian / Pacific Islander is the combined bucket (§5b).** The bronze
  publishes only six race buckets (Asian, Black, Hispanic, Multiracial,
  Native American, White) and never a separate Pacific Islander row or
  column in any era. The §5b math test confirms the pre-1997 OMB convention:
  at the state level the six race-bucket student counts sum EXACTLY to the
  ALL Students total in 20 of 21 years (male+female sum exactly in all 21).
  The single exception is 2013, where the race buckets fall short of the
  total by exactly 8 students out of 1,837,279 (0.0004%% — an unallocated-
  records artifact, three orders of magnitude below Georgia's ~0.1-0.2%%
  NHPI share, so it is not a dropped-Pacific-Islander signal). The bare
  ``Asian`` / ``ASIAN`` label is therefore remapped topic-locally to
  ``Asian/Pacific Islander`` BEFORE ``normalize_demographic_column()`` —
  the shared ``DEMOGRAPHIC_ALIASES`` is never edited, and no rollup rows
  are synthesized alongside split rows. Both facts are pinned as contract
  quality checks (exact partition for year <> 2013; the 2013 gap pinned at
  exactly 8).
- **Zero-population placeholder zeros are masked (§4b).** In 2005-2020 (wide
  2005-2010 and tidy 2011-2020), when a demographic subgroup has zero
  students the source publishes ``0`` for every percentage metric instead of
  leaving the cell blank: count = 0 with all three tiers exactly 0.0 (the
  tiers of a real population must sum to ~100, so an all-zero triple proves
  a placeholder, not a measurement) and, where the chronic column exists
  (2011, 2018-2020), chronic = 0.0 as well. All of 2011's non-null chronic
  values (8,351) are exactly these count-0 placeholders, which is why 2011
  publishes no real chronic data. These placeholder rates are set to NULL
  (rows and the count = 0 kept); 2004 already publishes NULL in this
  situation, so the mask makes all eras consistent. Recorded via
  ``manifest.record_masked`` per column and enforced by the
  ``zero_population_rates_null`` quality check.
- **Impossible zero student counts are masked (§4b).** In 2023 (5 rows) and
  2024 (6 rows) — all FEMALE rows at tiny special-population schools — the
  source publishes ``STUDENT_COUNT_FEMALE = 0`` alongside non-zero published
  percentages for the same subgroup. Sibling counts prove the population is
  non-empty (e.g. East DeKalb Special Education Center 2023: ALL = 80,
  MALE = 71, so 9 female students exist while FEMALE count reads 0) — a
  zero count cannot carry non-zero rates, so the count is the impossible
  value (a sub-threshold count published as 0 instead of TFS). The count is
  set to NULL; the published rates are kept.
- **2004 ends with a corrupted trailing re-paste block (dropped).** The
  file's last 23 lines re-publish the rows for districts 754-756: one
  partial line carrying only the tail of the intact 754:197 White County
  High School record (no entity key, values misaligned), then 21
  byte-identical duplicate lines, then a final line that is a TRUNCATED
  copy of the intact 756:101 record (52 of 62 fields; the cut field reads
  "42" where the original reads "42.4", so its metrics diverge). The whole
  block is dropped explicitly before the collision guard
  (``_drop_corrupt_trailing_repaste_block``, recorded via
  ``record_filtered``: 1 + 22 rows) — detection is evidence-based (an
  unkeyable row marks the block start and the function hard-stops if any
  subsequent key is not a duplicate of an intact earlier row). Every block
  key has an intact earlier row, so nothing is lost.
- **Dedup tie-break.** Each bronze file covers exactly one school year and
  years never overlap across files; after the 2004 block drop, the only
  duplicate keys are 2009's republished 768:ALL / 770:ALL charter aggregate
  rows (byte-identical metrics; one copy has a NULL name), which pass the
  collision guard and are removed by dedup (2 keys x 15 demographics =
  30 gold-grain rows). ``sort_col="num_students"`` is the documented
  safety net: prefer the row with a reported (non-null, larger) student
  count over a placeholder.
- **2022 mislabeled district aggregates, reclassified (§4.3c).** The 2022
  file labels the district-aggregate rows of two state-charter districts —
  7830627 (State Charter Schools II- Atlanta SMART Academy) and 7830636
  (State Charter Schools II- Northwest Classical Academy) — as
  ``DETAIL_LVL_DESC=School`` while carrying the ``INSTN_NUMBER=ALL``
  aggregate sentinel (2 rows; no genuine District twin exists for either
  code). The sentinel itself proves the row is an aggregate, so any
  "School" row with it is reclassified to district detail (recorded via
  ``record_reclassified``; the collision guard protects against a clash
  with a genuine district row). The same defect is documented in the GOSA
  dropout_rate_7_12 2022 file.
- **Chronic absence coverage.** ``chronically_absent_rate`` is published only
  from 2018 on: the wide era (2004-2010) and Era 6 (2012-2017) never carry
  the column (emitted as typed NULL with a log line), and 2011's column
  holds only zero-population placeholders (NULL after the mask). Pinned by
  the ``chronically_absent_rate_null_through_2017`` quality check.
- **Suppression.** 2004 publishes blank cells for some subgroups (including
  count > 0 rows with unpublished tier rates — up to state level); 2021-2022
  use the ``TFS`` literal; 2023-2024 mix ``TFS`` and blank cells. All become
  NULL via ``read_bronze_file``'s suppression handling + strict=False casts.
  2018-2020 have no suppression at all. Suppression is per-cell in 2023-2024,
  so no co-null invariant exists between the tier metrics.
"""

import logging
from pathlib import Path

import polars as pl

from src.utils.demographics import (
    DEMOGRAPHIC_ALIASES,
    normalize_demographic_column,
)
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

TOPIC = "attendance"
BRONZE_DIR = Path("data/bronze/education/gosa/attendance")
GOLD_DIR = Path("data/gold/education/attendance")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Aggregate-row sentinel in the geography code columns (and inside the
# wide-era compound key). Becomes NULL in gold, never a key value.
GEOGRAPHY_SENTINEL = "ALL"

DETAIL_LEVEL_MAP: dict[str, str] = {
    "State": "state",
    "District": "district",
    "School": "school",
}

# §5b topic-local override: bare "Asian" is the combined pre-1997 OMB
# Asian + Pacific Islander bucket for this source (state-level race sums
# equal the all-students total — see module docstring). Applied BEFORE
# normalize_demographic_column(); DEMOGRAPHIC_ALIASES is never edited.
ASIAN_PI_REMAP: dict[str, str] = {
    "Asian": "Asian/Pacific Islander",
    "ASIAN": "Asian/Pacific Islander",
}

# Wide-era (2004-2010) demographic labels exactly as embedded in the 60
# metric column names ("Number of Students {label}", etc.).
WIDE_DEMOGRAPHIC_LABELS: list[str] = [
    "All",
    "Economically Disadvantaged",
    "Migrant",
    "Not Economically Disadvantaged",
    "Asian",
    "Black",
    "Female",
    "Hispanic",
    "Limited English Proficient",
    "Male",
    "Native Amer/Alaskan Native",
    "Students without Disabilities",
    "Students with Disabilities",
    "Multiracial",
    "White",
]

# Wide-era metric column-name prefixes -> gold column.
WIDE_METRIC_PREFIXES: dict[str, str] = {
    "Number of Students": "num_students",
    "5 or Fewer Days Absent": "five_or_fewer_days_absent_rate",
    "6 to 15 Days Absent": "six_to_fifteen_days_absent_rate",
    "More than 15 Days Absent": "over_15_days_absent_rate",
}

# Tidy-era (2011-2024) demographic column-name suffixes. HISPANI (sic) is the
# literal truncated suffix in the bronze; INDIAN is Native American/Alaskan.
TIDY_DEMOGRAPHIC_SUFFIXES: list[str] = [
    "ALL",
    "INDIAN",
    "ASIAN",
    "BLACK",
    "WHITE",
    "HISPANI",
    "MULTI",
    "FEMALE",
    "MALE",
    "SWD",
    "NOT_SWD",
    "ED",
    "NOT_ED",
    "LEP",
    "MIGRANT",
]

# Tidy-era metric column-name prefixes -> gold column (chronic handled
# separately because Era 6 lacks the columns entirely).
TIDY_METRIC_PREFIXES: dict[str, str] = {
    "STUDENT_COUNT": "num_students",
    "FIVE_OR_FEWER_PERCENT": "five_or_fewer_days_absent_rate",
    "SIX_TO_FIFTEEN_PERCENT": "six_to_fifteen_days_absent_rate",
    "OVER_15_PERCENT": "over_15_days_absent_rate",
}
TIDY_CHRONIC_PREFIX = "CHRONIC_ABSENT_PERC"

# Era-detection signatures, most-specific first. The three tidy signatures
# are supersets of each other (#RPT_NAME > chronic columns > base), so order
# matters; the three wide signatures are disjoint identifier-casing variants.
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_8_tidy_rpt": ["#RPT_NAME", "LONG_SCHOOL_YEAR", "STUDENT_COUNT_ALL"],
    "era_5_7_tidy_chronic": [
        "LONG_SCHOOL_YEAR",
        "STUDENT_COUNT_ALL",
        "CHRONIC_ABSENT_PERC_ALL",
    ],
    "era_6_tidy": ["LONG_SCHOOL_YEAR", "STUDENT_COUNT_ALL"],
    "era_1_wide": ["SysSchoolID", "School Name", "Number of Students All"],
    "era_2_4_wide": ["sysschoolid", "schoolname", "Number of Students All"],
    "era_3_wide": ["SchoolID", "School Name", "Number of Students All"],
}

WIDE_ERAS = {"era_1_wide", "era_2_4_wide", "era_3_wide"}

# Wide-era identifier columns per era: (entity_id_col, entity_name_col).
WIDE_ID_COLUMNS: dict[str, tuple[str, str]] = {
    "era_1_wide": ("SysSchoolID", "School Name"),
    "era_2_4_wide": ("sysschoolid", "schoolname"),
    "era_3_wide": ("SchoolID", "School Name"),
}

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "num_students",
    "five_or_fewer_days_absent_rate",
    "six_to_fifteen_days_absent_rate",
    "over_15_days_absent_rate",
    "chronically_absent_rate",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "demographic": pl.Utf8,
    "num_students": pl.Int64,
    "five_or_fewer_days_absent_rate": pl.Float64,
    "six_to_fifteen_days_absent_rate": pl.Float64,
    "over_15_days_absent_rate": pl.Float64,
    "chronically_absent_rate": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = [
    "num_students",
    "five_or_fewer_days_absent_rate",
    "six_to_fifteen_days_absent_rate",
    "over_15_days_absent_rate",
    "chronically_absent_rate",
]

# The four percentage metrics (everything except num_students).
RATE_COLUMNS: list[str] = METRIC_COLUMNS[1:]

NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "detail_level",
]

# The 15 canonical demographic keys this topic publishes in every year.
DEMOGRAPHIC_VALUES: list[str] = sorted(
    [
        "all",
        "asian_pacific_islander",
        "black",
        "economically_disadvantaged",
        "english_learners",
        "female",
        "hispanic",
        "male",
        "migrant",
        "multiracial",
        "native_american",
        "not_economically_disadvantaged",
        "students_with_disabilities",
        "students_without_disabilities",
        "white",
    ]
)

# The six mutually exclusive race buckets (combined Asian/PI convention).
RACE_BUCKET_KEYS: list[str] = [
    "asian_pacific_islander",
    "black",
    "hispanic",
    "multiracial",
    "native_american",
    "white",
]


# =============================================================================
# Casting helpers
# =============================================================================


def _to_float_expr(col: str) -> pl.Expr:
    """Cast an all-string bronze metric column to Float64.

    Suppression markers (TFS, blanks) already arrived as NULL from
    ``read_bronze_file``; ``strict=False`` nulls any other non-numeric
    residue instead of failing the cast.
    """
    return pl.col(col).str.strip_chars().cast(pl.Float64, strict=False)


def _to_rate_expr(col: str) -> pl.Expr:
    """Cast a 0-100 bronze percentage column onto the 0-1 proportion scale."""
    return _to_float_expr(col) / 100.0


def _to_int_expr(col: str) -> pl.Expr:
    """Cast an all-string bronze count column to Int64 via Float64.

    The Float64 hop tolerates decimal-formatted counts ("954.0" from Excel
    string reads) without silently nulling them; counts are integral so the
    Int64 cast is exact.
    """
    return _to_float_expr(col).cast(pl.Int64)


def _require_columns(df: pl.DataFrame, required: list[str], label: str) -> None:
    """Raise if any expected bronze column is absent (rename-coverage guard).

    An unmatched source column silently becomes NULL in gold — the most
    common data-loss bug — so every expected metric column is asserted
    present before any selection happens.
    """
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"{label}: expected bronze column(s) missing: {missing}. "
            f"Present: {df.columns}"
        )


# =============================================================================
# Shared demographic normalization (§5 / §5b)
# =============================================================================


def _normalize_demographics(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Normalize ``_demographic_raw`` to the canonical ``demographic`` column.

    Applies the §5b topic-local remap first — bare "Asian"/"ASIAN" becomes
    "Asian/Pacific Islander" (the math test proves the combined bucket; see
    module docstring) — then the shared canonical path. The manifest records
    the effective alias slice with the override substituted, so the review
    sees ASIAN -> asian_pacific_islander explicitly.
    """
    df = df.with_columns(
        pl.col("_demographic_raw").replace(ASIAN_PI_REMAP).alias("_demographic_src")
    ).with_columns(
        normalize_demographic_column("_demographic_src").alias("demographic")
    )
    observed_upper = {
        str(v).strip().upper()
        for v in df["_demographic_raw"].drop_nulls().unique().to_list()
    }
    effective_map = {
        k: v for k, v in DEMOGRAPHIC_ALIASES.items() if k in observed_upper
    }
    # Document the topic-local §5b override in the manifest's map_used.
    if "ASIAN" in observed_upper:
        effective_map["ASIAN"] = "asian_pacific_islander"
    manifest.record_categorical(
        column="demographic",
        map_dict=effective_map,
        bronze_series=df["_demographic_raw"],
        gold_series=df["demographic"],
    )
    return df


# =============================================================================
# Wide era (2004-2010): unpivot 60 metric columns to tidy rows
# =============================================================================


def _drop_corrupt_trailing_repaste_block(
    df: pl.DataFrame, id_col: str, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Drop a corrupted trailing re-paste block marked by an unkeyable row.

    Known case (2004): the file's last 23 lines re-publish the rows for
    districts 754-756 — a partial line carrying only the tail of the intact
    754:197 record (no entity key, values misaligned), then 21 byte-identical
    duplicate lines, then a final line that is a TRUNCATED copy of the intact
    756:101 record (52 of 62 fields; its last field is cut from "42.4" to
    "42", so it diverges from the original and would trip the collision
    guard). Every key in the block has an intact earlier row, so dropping
    the whole block loses nothing.

    Detection is evidence-based, not positional: the first NULL/blank entity
    key marks the block start, and the function HARD-STOPS unless every
    keyed row at or after that point duplicates an entity key seen earlier
    in the file — a novel key would mean real data after the corruption
    marker, which must be analyzed, not dropped.
    """
    bad = pl.col(id_col).is_null() | (pl.col(id_col).str.strip_chars() == "")
    if df.filter(bad).height == 0:
        return df

    df = df.with_row_index("_idx")
    block_start = int(df.filter(bad)["_idx"].min())
    intact = df.filter(pl.col("_idx") < block_start)
    block = df.filter(pl.col("_idx") >= block_start)
    block_keyed = block.filter(~bad)

    # Hard-stop guard: the block must be a pure re-paste of earlier keys.
    novel = block_keyed.join(
        intact.select(pl.col(id_col).str.strip_chars().alias(id_col)).unique(),
        left_on=pl.col(id_col).str.strip_chars(),
        right_on=id_col,
        how="anti",
    )
    if novel.height:
        raise ValueError(
            f"Year {year}: {novel.height} row(s) after the unkeyable corruption "
            f"marker carry entity keys not seen earlier in the file "
            f"({novel[id_col].head(5).to_list()}) — not a pure re-paste block; "
            f"investigate before dropping."
        )

    n_unkeyable = block.height - block_keyed.height
    manifest.record_filtered(
        year, n_unkeyable, "corrupt_partial_record_missing_entity_id"
    )
    manifest.record_filtered(
        year, block_keyed.height, "corrupt_trailing_repaste_block_duplicates"
    )
    logger.warning(
        "Year %d: dropping corrupted trailing re-paste block of %d row(s) "
        "(%d unkeyable partial + %d duplicate re-pastes of intact earlier "
        "rows, incl. one truncated copy); keys: %s",
        year,
        block.height,
        n_unkeyable,
        block_keyed.height,
        sorted(block_keyed[id_col].unique().to_list())[:25],
    )
    return intact.drop("_idx")


def _transform_wide(
    df: pl.DataFrame,
    year: int,
    era: str,
    manifest: TransformManifest,
    label: str,
) -> pl.DataFrame:
    """Transform one wide-era file (2004-2010) to gold shape.

    Unpivots the 60 metric columns (4 metrics x 15 demographic labels) into
    one row per entity x demographic, deriving the detail level from the
    compound ``district:school`` key pattern (ALL:ALL = state, X:ALL =
    district, else school).
    """
    id_col, _name_col = WIDE_ID_COLUMNS[era]
    expected = [id_col] + [
        f"{prefix} {demo}"
        for demo in WIDE_DEMOGRAPHIC_LABELS
        for prefix in WIDE_METRIC_PREFIXES
    ]
    _require_columns(df, expected, label)

    df = _drop_corrupt_trailing_repaste_block(df, id_col, year, manifest)

    # Compound-key parsing: "{district}:{school}". Guard the 2-part shape so
    # a malformed key can never silently mis-derive geography.
    df = df.with_columns(pl.col(id_col).str.strip_chars().str.split(":").alias("_p"))
    bad_keys = df.filter(pl.col("_p").list.len() != 2)
    if bad_keys.height:
        raise ValueError(
            f"{label}: {bad_keys.height} row(s) with malformed entity key: "
            f"{bad_keys[id_col].head(5).to_list()}"
        )
    df = df.with_columns(
        pl.col("_p").list.get(0).alias("_district_raw"),
        pl.col("_p").list.get(1).alias("_school_raw"),
    ).with_columns(
        # Detail level from the sentinel pattern: ALL:ALL = state,
        # {district}:ALL = district aggregate, else school.
        pl.when(pl.col("_district_raw") == GEOGRAPHY_SENTINEL)
        .then(pl.lit("state"))
        .when(pl.col("_school_raw") == GEOGRAPHY_SENTINEL)
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .alias("detail_level"),
        # ALL sentinels -> NULL; zfill pads 3-digit district / 4-digit school
        # codes and passes 7-digit charter codes (present from 2010) through
        # unchanged. Wide-era school codes are unpadded ("103" -> "0103").
        pl.when(pl.col("_district_raw") == GEOGRAPHY_SENTINEL)
        .then(None)
        .otherwise(pl.col("_district_raw").str.zfill(3))
        .alias("district_code"),
        pl.when(pl.col("_school_raw") == GEOGRAPHY_SENTINEL)
        .then(None)
        .otherwise(pl.col("_school_raw").str.zfill(4))
        .alias("school_code"),
    )

    # Unpivot: one sub-frame per demographic label, then concat. Chronic
    # absence is never published in the wide era — typed NULL by design.
    logger.info(
        "%s: chronic-absence columns not published in the wide era — "
        "emitting NULL chronically_absent_rate",
        label,
    )
    frames = [
        df.select(
            pl.lit(year).cast(pl.Int32).alias("year"),
            pl.col("district_code"),
            pl.col("school_code"),
            pl.lit(demo).alias("_demographic_raw"),
            _to_int_expr(f"Number of Students {demo}").alias("num_students"),
            _to_rate_expr(f"5 or Fewer Days Absent {demo}").alias(
                "five_or_fewer_days_absent_rate"
            ),
            _to_rate_expr(f"6 to 15 Days Absent {demo}").alias(
                "six_to_fifteen_days_absent_rate"
            ),
            _to_rate_expr(f"More than 15 Days Absent {demo}").alias(
                "over_15_days_absent_rate"
            ),
            pl.lit(None).cast(pl.Float64).alias("chronically_absent_rate"),
            pl.col("detail_level"),
        )
        for demo in WIDE_DEMOGRAPHIC_LABELS
    ]
    out = _normalize_demographics(pl.concat(frames), manifest)
    return out.select(STANDARD_COLUMNS)


# =============================================================================
# Tidy era (2011-2024): suffix-driven melt of demographic column groups
# =============================================================================


def _reclassify_mislabeled_aggregates(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Reclassify "School" rows carrying the INSTN_NUMBER=ALL sentinel (§4.3c).

    The ALL sentinel marks an aggregate row by definition, so a School-labeled
    row with it is a source mislabeling of a district aggregate. Known case:
    the 2022 file mislabels the district-aggregate rows of two state-charter
    districts — 7830627 (State Charter Schools II- Atlanta SMART Academy) and
    7830636 (State Charter Schools II- Northwest Classical Academy), 2 rows,
    neither with a genuine District twin — the same defect documented for the
    GOSA dropout_rate_7_12 2022 file. Applied generically because the
    sentinel itself is the proof; the collision guard in main() catches any
    clash with a genuine district row.
    """
    mislabeled = (pl.col("detail_level") == "school") & (
        pl.col("INSTN_NUMBER").str.strip_chars() == GEOGRAPHY_SENTINEL
    )
    mislabeled_df = df.filter(mislabeled)
    if mislabeled_df.height:
        affected = mislabeled_df["SCHOOL_DSTRCT_CD"].unique().sort().to_list()
        # Manifest artifact: the data review verifies repairs from here.
        manifest.record_reclassified(
            year, mislabeled_df.height, "school_labeled_aggregate_to_district"
        )
        logger.warning(
            "Year %d: reclassifying %d School-labeled row(s) carrying the "
            "INSTN_NUMBER=ALL aggregate sentinel to district detail "
            "(districts: %s) — source mislabeling, see module docstring",
            year,
            mislabeled_df.height,
            affected,
        )
        df = df.with_columns(
            pl.when(mislabeled)
            .then(pl.lit("district"))
            .otherwise(pl.col("detail_level"))
            .alias("detail_level")
        )
    return df


def _validate_era8_constants(df: pl.DataFrame, label: str) -> None:
    """Hard-stop if Era 8's constant #RPT_NAME column carries unexpected values.

    Anything other than "Attendance" means non-attendance report rows are
    mixed into this topic's bronze and must be analyzed, not silently kept.
    """
    rpt_names = df["#RPT_NAME"].drop_nulls().unique().to_list()
    if rpt_names != ["Attendance"]:
        raise ValueError(f"{label}: unexpected #RPT_NAME values {rpt_names}")


def _transform_tidy(
    df: pl.DataFrame,
    year: int,
    era: str,
    manifest: TransformManifest,
    label: str,
) -> pl.DataFrame:
    """Transform one tidy-era file (2011-2024) to gold shape.

    Each bronze row is one entity at one detail level; the 15 demographic
    groups live as column-name suffixes and are melted to one gold row per
    entity x demographic. Era 6 (2012-2017) lacks the chronic-absence
    columns entirely (logged, emitted as typed NULL).
    """
    expected = ["DETAIL_LVL_DESC", "SCHOOL_DSTRCT_CD", "INSTN_NUMBER"] + [
        f"{prefix}_{suffix}"
        for suffix in TIDY_DEMOGRAPHIC_SUFFIXES
        for prefix in TIDY_METRIC_PREFIXES
    ]
    _require_columns(df, expected, label)
    if era == "era_8_tidy_rpt":
        _validate_era8_constants(df, label)

    # Chronic columns exist in 2011 + 2018-2024 only. If present, all 15
    # suffixes must be present (partial coverage would be a rename bug).
    has_chronic = f"{TIDY_CHRONIC_PREFIX}_ALL" in df.columns
    if has_chronic:
        _require_columns(
            df,
            [f"{TIDY_CHRONIC_PREFIX}_{s}" for s in TIDY_DEMOGRAPHIC_SUFFIXES],
            label,
        )
    else:
        # Expected for Era 6 (2012-2017) per the structure doc; the log line
        # surfaces the fallback in case it ever fires for another year.
        logger.info(
            "%s: no %s_* columns — emitting NULL chronically_absent_rate",
            label,
            TIDY_CHRONIC_PREFIX,
        )

    # Detail level: State/District/School -> state/district/school. Unmapped
    # values become NULL and surface via the manifest's unmapped guard.
    df = df.with_columns(
        pl.col("DETAIL_LVL_DESC")
        .replace_strict(DETAIL_LEVEL_MAP, default=None)
        .alias("detail_level")
    )
    manifest.record_categorical(
        column="detail_level",
        map_dict=DETAIL_LEVEL_MAP,
        bronze_series=df["DETAIL_LVL_DESC"],
        gold_series=df["detail_level"],
    )

    # Source mislabeling repair (2022): aggregate rows labeled School.
    df = _reclassify_mislabeled_aggregates(df, year, manifest)

    # Geography keys: ALL sentinels -> NULL; zfill pads 3-digit district /
    # 4-digit school codes and passes 7-digit charter codes through unchanged.
    district_clean = pl.col("SCHOOL_DSTRCT_CD").str.strip_chars()
    school_clean = pl.col("INSTN_NUMBER").str.strip_chars()
    df = df.with_columns(
        pl.when(district_clean == GEOGRAPHY_SENTINEL)
        .then(None)
        .otherwise(district_clean.str.zfill(3))
        .alias("district_code"),
        pl.when(school_clean == GEOGRAPHY_SENTINEL)
        .then(None)
        .otherwise(school_clean.str.zfill(4))
        .alias("school_code"),
    )

    frames = [
        df.select(
            pl.lit(year).cast(pl.Int32).alias("year"),
            pl.col("district_code"),
            pl.col("school_code"),
            pl.lit(suffix).alias("_demographic_raw"),
            _to_int_expr(f"STUDENT_COUNT_{suffix}").alias("num_students"),
            _to_rate_expr(f"FIVE_OR_FEWER_PERCENT_{suffix}").alias(
                "five_or_fewer_days_absent_rate"
            ),
            _to_rate_expr(f"SIX_TO_FIFTEEN_PERCENT_{suffix}").alias(
                "six_to_fifteen_days_absent_rate"
            ),
            _to_rate_expr(f"OVER_15_PERCENT_{suffix}").alias(
                "over_15_days_absent_rate"
            ),
            (
                _to_rate_expr(f"{TIDY_CHRONIC_PREFIX}_{suffix}")
                if has_chronic
                else pl.lit(None).cast(pl.Float64)
            ).alias("chronically_absent_rate"),
            pl.col("detail_level"),
        )
        for suffix in TIDY_DEMOGRAPHIC_SUFFIXES
    ]
    out = _normalize_demographics(pl.concat(frames), manifest)
    return out.select(STANDARD_COLUMNS)


# =============================================================================
# Per-file dispatch
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame:
    """Read one bronze file, detect its era, and transform it to gold shape.

    Year resolution: wide-era files carry no year column, so the filename
    year (= school-year ending year, confirmed by year-over-year enrollment
    changes for the same school) is authoritative. Tidy-era files carry
    exactly one LONG_SCHOOL_YEAR whose ending year must agree with the
    filename year, so a misnamed file cannot silently mislabel a whole year.
    """
    # All-string read: geography codes keep leading zeros and the ALL
    # sentinels are never schema-inference casualties; TFS/blank suppression
    # arrives as NULL. XLS/XLSX (incl. the two XLS-mislabeled-.csv files,
    # dispatched by magic bytes) are read dtype=str by read_bronze_file.
    df, loss = read_bronze_file(path, infer_schema_length=0, return_loss=True)
    filename_year = extract_year_from_filename(path.name)
    if filename_year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")
    manifest.record_read_loss(
        filename_year, path.name, loss["raw_rows"], loss["parsed_rows"]
    )

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{path.name}: no era signature matched columns {df.columns}")
    label = f"{era} {path.name}"

    if era in WIDE_ERAS:
        year = filename_year
    else:
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

    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)
    logger.info("Processing %s as %s (year %d)", path.name, era, year)

    if era in WIDE_ERAS:
        return _transform_wide(df, year, era, manifest, label)
    return _transform_tidy(df, year, era, manifest, label)


# =============================================================================
# §4b masks
# =============================================================================


def _null_zero_population_placeholder_rates(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """NULL placeholder 0.0 rates published for zero-student subgroups (§4b).

    In 2005-2020 the source publishes 0 for every percentage metric when a
    demographic subgroup has zero students (num_students = 0 with all rates
    exactly 0.0 or blank). The three tiers of a real population must sum to
    ~1.0, so an all-zero set proves a placeholder, not a measurement — the
    rates are undefined for an empty denominator. Rates become NULL; the row
    and the real num_students = 0 are kept. 2004 already publishes NULL
    here, so this makes all eras consistent.
    """
    placeholder = (
        (pl.col("num_students") == 0)
        & pl.all_horizontal(
            [pl.col(c).is_null() | (pl.col(c) == 0.0) for c in RATE_COLUMNS]
        )
        & pl.any_horizontal([pl.col(c).is_not_null() for c in RATE_COLUMNS])
    )
    affected = df.filter(placeholder)
    if affected.height:
        logger.warning(
            "§4b: NULLing placeholder zero rates on %d zero-population row(s)",
            affected.height,
        )
        for col in RATE_COLUMNS:
            col_hit = affected.filter(pl.col(col).is_not_null())
            if col_hit.height:
                manifest.record_masked(
                    col,
                    col_hit.height,
                    "zero_population_placeholder_zero_rate",
                    years=sorted(col_hit["year"].unique().to_list()),
                )
        df = df.with_columns(
            [
                pl.when(placeholder).then(None).otherwise(pl.col(c)).alias(c)
                for c in RATE_COLUMNS
            ]
        )
    return df


def _null_impossible_zero_num_students(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """NULL num_students = 0 published alongside non-zero rates (§4b).

    2023-2024 publish STUDENT_COUNT_FEMALE = 0 with non-zero attendance
    rates at a handful of tiny special-population schools. A zero-student
    population cannot carry non-zero rates; the published non-zero rates
    themselves prove the population is non-empty (corroborated by ALL-minus-
    MALE arithmetic where sibling counts are published — 7 of 11 rows; the
    other 4 have TFS-suppressed siblings), so
    the count is the impossible value — a sub-threshold count published as
    0 instead of TFS. The count becomes NULL; the published rates are kept.
    Disjoint from the placeholder mask (which requires all rates 0/NULL).
    """
    impossible = (pl.col("num_students") == 0) & pl.any_horizontal(
        [pl.col(c).is_not_null() & (pl.col(c) > 0) for c in RATE_COLUMNS]
    )
    affected = df.filter(impossible)
    if affected.height:
        manifest.record_masked(
            "num_students",
            affected.height,
            "impossible_zero_count_with_published_rates",
            years=sorted(affected["year"].unique().to_list()),
        )
        logger.warning(
            "§4b: NULLing num_students on %d row(s) where count=0 "
            "contradicts published non-zero rates (demographics: %s)",
            affected.height,
            affected["demographic"].unique().to_list(),
        )
        df = df.with_columns(
            pl.when(impossible)
            .then(None)
            .otherwise(pl.col("num_students"))
            .alias("num_students")
        )
    return df


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for attendance."""
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
    # mean an alias/parsing bug and must raise, not be deduped away. The
    # known duplicates (2004 trailing re-paste block, 2009 republished
    # charter aggregates) are byte-identical, so they pass the guard.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: each bronze file is a distinct school year with no overlap
    # across files; the only duplicate keys are byte-identical republished
    # rows, so the winner is value-identical. sort_col="num_students" is the
    # documented safety net: prefer a reported (non-null, larger) count.
    pre_dedup = dict(combined.group_by("year").len().iter_rows())
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code", "demographic"],
        district_keys=["year", "district_code", "demographic"],
        state_keys=["year", "demographic"],
        sort_col="num_students",
    )
    # Surface the dedup removals as explicit manifest provenance per year.
    post_dedup = dict(combined.group_by("year").len().iter_rows())
    for year in sorted(pre_dedup):
        removed = pre_dedup[year] - post_dedup.get(year, 0)
        if removed > 0:
            manifest.record_filtered(
                year, removed, "exact_duplicate_republished_rows_deduped"
            )

    # 4. Geography nulling (shared domain rules), then the two §4b masks
    # (after dedup/geography, before manifest stats and export).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )
    combined = _null_zero_population_placeholder_rates(combined, manifest)
    combined = _null_impossible_zero_num_students(combined, manifest)

    # Pre-export sanity. NULL-rate spikes are expected and documented: the
    # suppression regime changes by era (TFS from 2021; per-cell TFS+blank in
    # 2023-2024) and the zero-population mask adds NULLs in 2005-2020.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(combined, required_non_null=["year", "detail_level", "demographic"])

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
    declaration order MUST match STANDARD_COLUMNS minus ``detail_level``.
    The absentee-tier partition check is pre-registered in the emitter's
    DOMAIN_QUALITY["attendance"] and is appended automatically — it is NOT
    duplicated here.
    """
    race_list = ", ".join(f"'{k}'" for k in RACE_BUCKET_KEYS)
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Distribution of Georgia public-school students across three "
            "absentee tiers (5 or fewer, 6-15, and more than 15 days absent "
            "during the school year), plus a chronic-absence rate (10%% or "
            "more of enrolled days; published from 2018) and the student "
            "count in the denominator, for every school with official "
            "district and state rollups, by demographic subgroup "
            "(race/ethnicity, gender, economic status, English proficiency, "
            "migrant status, disability status). Published by GOSA for "
            "school years 2003-04 through 2023-24."
        ),
        title="Student Attendance and Chronic Absenteeism",
        summary=(
            "Student attendance tiers and chronic-absence rates by Georgia "
            "school, district, and demographic subgroup, 2004-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Ending (spring) calendar year of the school year (e.g. "
                    "2024 for 2023-24). 2011-2024 files carry a "
                    "LONG_SCHOOL_YEAR cross-checked against the filename; "
                    "2004-2010 files carry no year column, so the filename "
                    "year (verified as the ending year via year-over-year "
                    "enrollment continuity) is authoritative."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "GOSA district code (FK to districts dimension): 3-digit "
                    "zero-padded county/city codes or 7-digit state-charter "
                    "codes (present from 2010). NULL on state-level rows."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0103",
                "description": (
                    "GOSA school code, zero-padded to 4 characters (composite "
                    "FK to schools dimension with district_code; not globally "
                    "unique on its own). 2004-2010 sources publish unpadded "
                    "codes ('103'), zero-padded here to align with 2011-2024. "
                    "NULL on district- and state-level rows."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "all",
                "validValues": DEMOGRAPHIC_VALUES,
                "short_description": (
                    "Student subgroup the row describes (race, gender, "
                    "economic status, English learner, migrant, or "
                    "disability); 'all' is every student."
                ),
                "description": (
                    "Demographic subgroup (FK to the global demographics "
                    "dimension); 15 subgroups in every year. Race buckets use "
                    "the combined asian_pacific_islander key (pre-1997 OMB "
                    "convention): the source publishes six race buckets with "
                    "a bare 'Asian' label and never a separate Pacific "
                    "Islander row, and the six buckets' state-level student "
                    "counts sum exactly to the 'all' total in every year "
                    "except 2013 (where they fall short by exactly 8 of 1.84M "
                    "students — an unallocated-records artifact, not a "
                    "dropped-Pacific-Islander population). 'all' is the "
                    "unfiltered total and overlaps every other value; "
                    "subgroups are mutually exclusive only within their own "
                    "category (race, gender, economic, English proficiency, "
                    "disability, migrant)."
                ),
            },
            {
                "name": "num_students",
                "type": "int64",
                "metric_component": "denominator",
                "unit": "count",
                "example": 954,
                "null_meaning": (
                    "Suppressed by GOSA (TFS literals 2021-2024, blank cells "
                    "2023-2024), or masked: 11 rows in 2023-2024 published an "
                    "impossible count of 0 alongside non-zero rates."
                ),
                "description": (
                    "Number of students in the subgroup used as the "
                    "denominator for the rate metrics. A real 0 means the "
                    "subgroup has no students at that entity. §4b mask: in "
                    "2023 (5 rows) and 2024 (6 rows) the source published "
                    "STUDENT_COUNT_FEMALE = 0 alongside non-zero published "
                    "rates at tiny special-population schools (e.g. East "
                    "DeKalb Special Education Center 2023: all=80, male=71, "
                    "female reads 0) — a zero population cannot carry "
                    "non-zero rates, so those counts are NULLed and the "
                    "rates kept."
                ),
            },
            {
                "name": "five_or_fewer_days_absent_rate",
                "type": "float64",
                "unit": "proportion",
                "example": 0.452,
                "null_meaning": (
                    "Suppressed by GOSA (blank cells in 2004, TFS/blank from "
                    "2021), or a zero-population placeholder masked to NULL "
                    "(2005-2020)."
                ),
                "description": (
                    "Proportion of the subgroup absent five or fewer days "
                    "during the school year (0-1 scale; source publishes "
                    "0-100, divided by 100). Together with the 6-15 and "
                    "over-15 tiers it partitions the subgroup population "
                    "(sums to ~1.0). §4b mask: in 2005-2020 the source "
                    "publishes 0 for all rate metrics when the subgroup has "
                    "zero students; those placeholder zeros are NULLed "
                    "(rates of an empty population are undefined; 2004 "
                    "already publishes NULL there)."
                ),
            },
            {
                "name": "six_to_fifteen_days_absent_rate",
                "type": "float64",
                "unit": "proportion",
                "example": 0.381,
                "null_meaning": (
                    "Suppressed by GOSA (blank cells in 2004, TFS/blank from "
                    "2021), or a zero-population placeholder masked to NULL "
                    "(2005-2020)."
                ),
                "description": (
                    "Proportion of the subgroup absent six to fifteen days "
                    "during the school year (0-1 scale; source publishes "
                    "0-100, divided by 100). Middle tier of the three-tier "
                    "partition. Zero-population placeholder zeros NULLed in "
                    "2005-2020 (see five_or_fewer_days_absent_rate)."
                ),
            },
            {
                "name": "over_15_days_absent_rate",
                "type": "float64",
                "unit": "proportion",
                "example": 0.168,
                "null_meaning": (
                    "Suppressed by GOSA (blank cells in 2004, TFS/blank from "
                    "2021), or a zero-population placeholder masked to NULL "
                    "(2005-2020)."
                ),
                "description": (
                    "Proportion of the subgroup absent more than fifteen "
                    "days during the school year (0-1 scale; source "
                    "publishes 0-100, divided by 100). Top tier of the "
                    "three-tier partition; often used as a chronic-"
                    "absenteeism proxy but distinct from "
                    "chronically_absent_rate (different cutoff definitions). "
                    "Zero-population placeholder zeros NULLed in 2005-2020 "
                    "(see five_or_fewer_days_absent_rate)."
                ),
            },
            {
                "name": "chronically_absent_rate",
                "type": "float64",
                "key_metric": True,
                "unit": "proportion",
                "example": 0.121,
                "short_description": (
                    "Share of the subgroup chronically absent (missing 10%% "
                    "or more of enrolled days), on a 0-1 scale; published from "
                    "2018."
                ),
                "null_meaning": (
                    "Not published before 2018 (no column 2004-2010 and "
                    "2012-2017; 2011's column holds only zero-population "
                    "placeholders), suppressed (TFS/blank 2021-2024), or a "
                    "zero-population placeholder masked to NULL (2018-2020)."
                ),
                "description": (
                    "Proportion of the subgroup chronically absent — absent "
                    "10%% or more of enrolled days, the federal definition "
                    "(0-1 scale; source publishes 0-100, divided by 100). "
                    "Published 2018-2024 only: the column does not exist in "
                    "the 2004-2010 and 2012-2017 sources, and the 2011 "
                    "column's only non-null values are zero-population "
                    "placeholder zeros (masked to NULL), so 2004-2017 is "
                    "entirely NULL. NOT equal to over_15_days_absent_rate — "
                    "the cutoffs differ (10%% of enrolled days vs a fixed "
                    "15-day count)."
                ),
            },
        ],
        source="GOSA",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        limitations=(
            "Suppressed cells are NULL (not zero): 2004 publishes blank "
            "cells for many subgroups (including some state-level rows); "
            "2021-2022 use the TFS (too few students) literal; 2023-2024 mix "
            "TFS and blank cells per cell, so the tier metrics are not "
            "co-suppressed and small-population subgroups (notably "
            "native_american) are mostly NULL in 2021-2024. "
            "chronically_absent_rate is NULL for every year before 2018. "
            "Rate metrics are NULL (masked) where a subgroup has zero "
            "students. State rows have NULL district_code and school_code; "
            "district rows have NULL school_code. The race axis uses the "
            "combined asian_pacific_islander bucket — not comparable "
            "row-for-row with split-convention topics without aggregating "
            "those topics' asian + pacific_islander rows at query time."
        ),
        notes=[
            (
                "The three absentee tiers partition each subgroup's "
                "population: five_or_fewer + six_to_fifteen + over_15 sums "
                "to ~1.0 (+/-0.02 rounding tolerance) wherever all three are "
                "published and num_students > 0 — enforced by the "
                "absentee_tiers_partition_population quality check."
            ),
            (
                "Asian/Pacific Islander is the combined pre-1997 OMB bucket "
                "(asian_pacific_islander), per data-cleaning-standards §5b: "
                "the source publishes six race buckets (bare 'Asian' label, "
                "no Pacific Islander row anywhere in any era) whose "
                "state-level counts sum exactly to the ALL Students total in "
                "every year except 2013 (short by exactly 8 students of "
                "1.84M; male+female sum exactly in all 21 years). The split "
                "asian / pacific_islander keys are never emitted."
            ),
            (
                "§4b masks: (1) 2005-2020 zero-population placeholder zeros "
                "— the source publishes 0 for every rate metric when a "
                "subgroup has zero students; those rates are NULLed (the "
                "row and the count=0 are kept; 2004 already publishes NULL "
                "there). All of 2011's non-null chronic values were these "
                "placeholders, so 2011 has no real chronic data. (2) 2023-"
                "2024 impossible zero counts — 11 FEMALE rows at tiny "
                "special-population schools publish count=0 alongside "
                "non-zero rates; the published rates prove the population is "
                "non-empty, so the count is NULLed and the rates kept."
            ),
            (
                "2004 source defect, repaired: the file ends with a "
                "corrupted trailing re-paste block for districts 754-756 — "
                "one partial line (the tail of the intact 754:197 record, "
                "no entity key), 21 byte-identical duplicate lines, and a "
                "final truncated copy of the 756:101 record (52 of 62 "
                "fields). The whole block is dropped (every key has an "
                "intact earlier row, so nothing is lost). 2009 republishes "
                "the 768:ALL and 770:ALL charter aggregate rows with "
                "identical metrics (dedup-resolved)."
            ),
            (
                "2022 source defect, repaired: the 2022 file labels the "
                "district-aggregate rows of two state-charter districts as "
                "School-level while carrying the INSTN_NUMBER=ALL aggregate "
                "sentinel — 7830627 (State Charter Schools II- Atlanta "
                "SMART Academy) and 7830636 (State Charter Schools II- "
                "Northwest Classical Academy), 2 rows. The transform "
                "reclassifies sentinel-bearing School rows to district "
                "detail (logged and recorded in the manifest)."
            ),
            (
                "Suppression regime changes by era: none in 2005-2020 "
                "(beyond the placeholder zeros), blank cells in 2004, TFS "
                "literals in 2021-2022, TFS + blank mixed per cell in "
                "2023-2024. NULL-rate differences across years reflect the "
                "source, not transform defects."
            ),
            (
                "GRADES_SERVED_DESC (grade span served) and entity names are "
                "institution metadata, not attendance facts — names live in "
                "the dimension tables. The 2023-2024 #RPT_NAME column is a "
                "constant report label, dropped after a constant guard."
            ),
        ],
        quality_checks=[
            {
                "name": "state_race_partition_sums_to_all",
                "description": (
                    "At the state level the six mutually exclusive race "
                    "buckets partition the student population: their "
                    "num_students values sum exactly to the 'all' total in "
                    "every year except 2013 (the §5b math test proving the "
                    "combined Asian/Pacific Islander convention). State "
                    "counts are never suppressed."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year FROM {object} "
                    "WHERE district_code IS NULL AND school_code IS NULL "
                    "AND year <> 2013 GROUP BY year HAVING "
                    f"SUM(CASE WHEN demographic IN ({race_list}) "
                    "THEN num_students ELSE 0 END) <> "
                    "MAX(CASE WHEN demographic = 'all' THEN num_students "
                    "END)) AS bad_years"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_race_partition_2013_gap_is_8",
                "description": (
                    "The single race-partition exception: in 2013 the six "
                    "state-level race-bucket counts fall short of the 'all' "
                    "total by exactly 8 students (unallocated records, "
                    "0.0004%% of 1,837,279 — three orders of magnitude below "
                    "the expected Pacific Islander share, so not a dropped "
                    "population). Pinned exactly so any drift surfaces."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year FROM {object} "
                    "WHERE district_code IS NULL AND school_code IS NULL "
                    "AND year = 2013 GROUP BY year HAVING "
                    "MAX(CASE WHEN demographic = 'all' THEN num_students "
                    "END) - "
                    f"SUM(CASE WHEN demographic IN ({race_list}) "
                    "THEN num_students ELSE 0 END) <> 8) AS bad_years"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_gender_partition_sums_to_all",
                "description": (
                    "At the state level male + female num_students sums "
                    "exactly to the 'all' total in every year (verified "
                    "across all 21 bronze years; state counts are never "
                    "suppressed)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year FROM {object} "
                    "WHERE district_code IS NULL AND school_code IS NULL "
                    "GROUP BY year HAVING "
                    "SUM(CASE WHEN demographic IN ('male', 'female') "
                    "THEN num_students ELSE 0 END) <> "
                    "MAX(CASE WHEN demographic = 'all' THEN num_students "
                    "END)) AS bad_years"
                ),
                "mustBe": 0,
            },
            {
                "name": "zero_population_rates_null",
                "description": (
                    "A subgroup with zero students has no defined rates: "
                    "every row with num_students = 0 carries NULL for all "
                    "four rate metrics (enforces the §4b zero-population "
                    "placeholder mask; the source's placeholder 0.0 rates "
                    "for empty subgroups in 2005-2020 are NULLed)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE num_students = 0 "
                    "AND (five_or_fewer_days_absent_rate IS NOT NULL "
                    "OR six_to_fifteen_days_absent_rate IS NOT NULL "
                    "OR over_15_days_absent_rate IS NOT NULL "
                    "OR chronically_absent_rate IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "chronically_absent_rate_null_through_2017",
                "description": (
                    "Chronic absence is published from 2018 only: the "
                    "2004-2010 and 2012-2017 sources have no chronic "
                    "column, and 2011's column holds only zero-population "
                    "placeholders (masked). No non-NULL "
                    "chronically_absent_rate may exist before 2018."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year <= 2017 "
                    "AND chronically_absent_rate IS NOT NULL"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
