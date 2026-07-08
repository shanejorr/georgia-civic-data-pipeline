"""Transform bronze hope_eligible_graduates files into gold fact tables.

Source: Governor's Office of Student Achievement (GOSA) — HOPE Eligibility
report. For every Georgia public high school, school district, and the state
as a whole, GOSA publishes the count of graduating seniors who met the
academic eligibility criteria for Georgia's HOPE scholarship program.
Coverage: spring 2004 through spring 2024 (21 files; filename year = spring
graduation year in every era, per structure-doc ETL note 4).

Grain: one row per (year, district_code, school_code) — geography keys NULL
at higher aggregation levels. Three metrics: ``num_graduates`` (regular
high-school graduates), ``num_hope_eligible`` (subset meeting HOPE academic
eligibility), ``hope_eligible_rate`` (the share, bronze 0-100 divided by 100
onto the 0-1 proportion scale per §4).

Design decisions (from bronze-data-structure.md, re-verified against bronze):

- **Seven schema eras, one tidy gold shape.** Era 1 (2023-2024) adds
  ``#RPT_NAME`` + explicit ``DETAIL_LVL_DESC``; Era 2 (2009, 2011-2022) is
  the LONG_SCHOOL_YEAR schema with ``ALL`` sentinels marking rollup rows;
  Era 3 (2010), Era 5 (2007), Era 6 (2006), and Era 7 (2004-2005) ship a
  composite ``{district}:{school}`` key under four different column-name
  spellings; Era 4 (2008) is the Report Card multi-sheet export. Era
  detection is by column signature (Era 1 listed before Era 2 because its
  signature is a strict superset; Eras 5/7 are disambiguated by the
  graduate-count column name).
- **Year derivation.** Filename year is canonical for every era. Eras 1-2
  carry LONG_SCHOOL_YEAR (``YYYY-YY``); its ending year is asserted equal to
  the filename year (raises on drift). Era 4's constant ``Data Year`` column
  is likewise asserted. The 2005 file reuses the stale header ``Number of
  2004 Graduates`` — a label artifact only; per-school values differ from
  the 2004 file, so the data is the spring-2005 cohort (ETL note 2).
- **2005 file is a mislabeled XLS.** Despite the ``.csv`` extension it is an
  OLE binary; ``read_bronze_file`` detects the real format via magic bytes.
- **TFS suppression → NULL.** Modern eras (2009, 2011-2024) censor cells
  with the literal ``TFS`` (Too Few Students; the 2009 source SQL applies it
  when graduates <= 9). ``read_bronze_file`` nulls it at read time;
  ``strict=False`` casts are a second net. NULL has a second bronze cause in
  Era 2: genuinely blank cells — values GOSA left unreported (verified: 2014
  and 2020 contain zero ``TFS`` yet carry 12-37 truly empty metric cells per
  column; other Era 2 years mix both causes). Both arrive as NULL through
  the reader and are indistinguishable in gold. Verified co-null structure
  across all 12,432 bronze rows: num_graduates NULL always implies the
  other two metrics NULL (281 fully-null rows; partial censoring affects
  only num_hope_eligible and/or the rate — 269 + 244 + 1 rows) — pinned by
  the ``suppression_nulls_graduates_last`` quality check. Pre-2008 + 2010
  files have no suppression at all; their zeros are real zeros.
- **2004 quirks (Era 7).** (a) One trailing junk/footer row (NUL-padded
  ``SYSSCHOOLID``, all other fields null) is dropped and manifest-recorded.
  (b) Eight school codes carry a trailing ``x`` (e.g. ``644:775x``), each
  with a canonical same-named sibling row (verified); they are separately
  tallied sub-groups of the same school, so the ``x`` is stripped and the 8
  colliding pairs are summed (rate recomputed as eligible/graduates for the
  8 merged rows ONLY — the 338 singleton schools keep the bronze published
  1-decimal rate; recomputing those would silently replace published
  values). (c) Bronze has no district rollups (school + state only), so
  district aggregates for 2004's 174 districts are derived by summing school
  rows (rate = sum(eligible)/sum(graduates), a graduate-weighted mean).
  (d) Known bronze artifact: the official 2004 state row (68,163 graduates /
  42,233 eligible) exceeds the itemized school-row sums (68,029 / 42,146) by
  ~0.2%; both are preserved as published — user rollups from schools or
  districts to state run ~0.2% short for 2004 only.
- **2008 (Era 4) is school-level-only bronze.** The ``System Level`` and
  ``State Level`` sheets are exact pre-aggregations of the ``School Level``
  sheet (state: 31,443 / 81,569 / 38.5477% — verified), so only ``School
  Level`` is read and district + state aggregates are derived, keeping era
  handling uniform. Of the 5 rows with null ``School ID``: 4 carry a valid
  ``System ID`` (alternative campuses / evening schools) — they are excluded
  from the schools fact (no key) but their counts are folded into the
  district + state aggregates (manifest: reclassified); 1 row (RENAISSANCE
  ACADEMY, 28 graduates / 0 eligible) is fully orphaned (null System ID,
  School ID, System Name) and is excluded everywhere — matching the bronze
  State Level total, which also excludes it (manifest: filtered).
- **2008 duplicate school key.** Bronze publishes two distinct rows under
  key 721/2574 (WESTSIDE HIGH SCHOOL, 241/61 + WESTSIDE COMPREHENSIVE HIGH
  SCHOOL, 140/30). Both carry real students; they are summed (not deduped).
  The merge regroups all 2008 school rows and recomputes
  ``hope_eligible_rate = eligible/graduates`` for every 2008 school row.
  This is semantically a no-op for the singletons: bronze 2008 ``Percent
  Eligible`` is itself the full-precision ratio (measured
  max |bronze/100 - e/g| ~ 1e-15, pure float ulp noise on 60 of 381 rows),
  unlike the 1-decimal-rounded pre-2008 years — and it keeps the merged
  Westside row and the derived aggregates arithmetically consistent.
- **Composite-key splitting (Eras 3/5/6/7).** ``{district}:{school}`` splits
  on the first ``:``; ``ALL`` on either side is a rollup sentinel that
  becomes NULL, then detail level derives from the NULL pattern (state =
  both NULL; district = school NULL; school = both present).
- **ID formatting.** ``district_code`` zfill(3) (7-digit charter /
  state-school codes such as 7820412 appear from late Era 2 onward and pass
  through unchanged); ``school_code`` zfill(4) (bronze mixes unpadded
  3/4-digit and zero-padded 4-digit across eras and years — including
  *within* the 2008 file, whose School ID cells are mixed numeric/text).
- **Series break 2006 -> 2007 (real, preserved).** State percent eligible
  drops from ~62% (2004-2006) to ~38% (2007+). Starting with the class of
  2007 the Georgia Student Finance Commission began computing each student's
  HOPE GPA directly from electronic transcripts instead of the
  school-reported GPA. Documented, not "fixed".
- **No demographic column.** No era publishes any demographic breakdown —
  every row is the all-students total, so the column is omitted per §5.
- **No §4b masks.** All values are physically possible: counts are
  non-negative, every bronze rate reconciles with eligible/graduates within
  0.0005 on the 0-1 scale (max measured deviation; 1-decimal bronze
  rounding), and eligible never exceeds graduates (0 violations measured
  across all 21 files).
- **Dedup tie-break.** After the era-internal merges above, the natural key
  is unique across all 21 files (verified: the only bronze duplicate keys
  are the 8 2004 trailing-x pairs and the 2008 Westside pair, both summed
  before the global guard). ``sort_col="num_graduates"`` remains as the
  documented defensive net — prefer the row with the larger populated cohort
  over a hypothetical placeholder twin.
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

TOPIC = "hope_eligible_graduates"
BRONZE_DIR = Path("data/bronze/education/gosa/hope_eligible_graduates")
GOLD_DIR = Path("data/gold/education/hope_eligible_graduates")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Rollup sentinel used by every era's geography codes (state rows set the
# district code to ALL; state + district rows set the school code to ALL).
BRONZE_ALL_SENTINEL = "ALL"

# Era 1's explicit detail-level labels -> gold detail_level values.
DETAIL_LEVEL_MAP: dict[str, str] = {
    "STATE": "state",
    "DISTRICT": "district",
    "SCHOOL": "school",
}

# Era-detection signatures, most-specific first (detect_era_by_columns
# returns the first signature fully present). Era 1's column set is a strict
# superset of Era 2's, so Era 1 must be listed first. Eras 5 and 7 share the
# SYSSCHOOLID + SchoolNme pair and are disambiguated by the graduate-count
# column name (each file carries exactly one of the two spellings).
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_1_2023_2024_detail_lvl_desc": [
        "#RPT_NAME",
        "DETAIL_LVL_DESC",
        "LONG_SCHOOL_YEAR",
        "SCHOOL_DISTRCT_CD",
        "INSTN_NUMBER",
        "NUMBER_OF_GRADUATES",
        "HOPE_ELIGIBLE",
        "HOPE_ELIGIBLE_PCT",
    ],
    "era_2_2009_2011_2022_long_school_year": [
        "LONG_SCHOOL_YEAR",
        "SCHOOL_DISTRCT_CD",
        "INSTN_NUMBER",
        "NUMBER_OF_GRADUATES",
        "HOPE_ELIGIBLE",
        "HOPE_ELIGIBLE_PCT",
    ],
    "era_3_2010_sysschoolid": [
        "Sysschoolid",
        "System/School Name",
        "Number of Graduates",
        "Number Eligible",
        "Percent Eligible",
    ],
    "era_4_2008_report_card": [
        "Data Year",
        "System ID",
        "School ID",
        "# Eligible for HOPE 2008",
        "Number of Regular Graduates - Report Card",
        "Percent Eligible",
    ],
    "era_5_2007_sysschoolid_uppercase": [
        "SYSSCHOOLID",
        "SchoolNme",
        "Number of Graduates",
        "Number Eligible",
        "Percent Eligible",
    ],
    "era_6_2006_sysschoolid_titlecase": [
        "SysSchoolID",
        "School Name",
        "Number of Graduates",
        "Number Eligible",
        "Percent Eligible",
    ],
    "era_7_2004_2005_stale_header": [
        "SYSSCHOOLID",
        "SchoolNme",
        "Number of 2004 Graduates",
        "Number Eligible",
        "Percent Eligible",
    ],
}

# Gold fact column order. detail_level is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
# No demographic column — no era has demographic breakdowns (§5).
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "num_graduates",
    "num_hope_eligible",
    "hope_eligible_rate",
    "detail_level",
]

# Counts use Int64 — the state rollup exceeds 100K graduates by 2022.
TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "num_graduates": pl.Int64,
    "num_hope_eligible": pl.Int64,
    "hope_eligible_rate": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = [
    "num_graduates",
    "num_hope_eligible",
    "hope_eligible_rate",
]

# The contract grain. detail_level is deliberately excluded: uniqueness must
# hold ACROSS detail levels (a district row and a school row may never share
# the same NULL-pattern key tuple).
NATURAL_KEYS: list[str] = ["year", "district_code", "school_code"]


# =============================================================================
# Shared helpers
# =============================================================================


def _format_geography_codes(
    df: pl.DataFrame, district_raw_col: str, school_raw_col: str
) -> pl.DataFrame:
    """Null the ALL rollup sentinels and zero-pad both geography codes.

    district_code: zfill(3) pads the standard 3-digit codes; 7-digit charter
    / state-school codes (e.g. 7820412, present from late Era 2 onward) pass
    through unchanged. school_code: zfill(4) normalizes the unpadded 3/4-digit
    spellings that several eras (and individual 2008 cells) ship.
    """
    return df.with_columns(
        pl.when(pl.col(district_raw_col) == BRONZE_ALL_SENTINEL)
        .then(None)
        .otherwise(pl.col(district_raw_col).str.zfill(3))
        .alias("district_code"),
        pl.when(pl.col(school_raw_col) == BRONZE_ALL_SENTINEL)
        .then(None)
        .otherwise(pl.col(school_raw_col).str.zfill(4))
        .alias("school_code"),
    ).drop([district_raw_col, school_raw_col])


def _derive_detail_level_from_sentinels(df: pl.DataFrame) -> pl.DataFrame:
    """Derive detail_level from the geography NULL pattern (post-nulling).

    Both codes NULL -> state; school NULL only -> district; else school.
    Used by every era except Era 1 (explicit DETAIL_LVL_DESC) and Era 4
    (school-level-only bronze; aggregate rows are derived, not classified).
    """
    return df.with_columns(
        pl.when(pl.col("district_code").is_null() & pl.col("school_code").is_null())
        .then(pl.lit("state"))
        .when(pl.col("school_code").is_null())
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .alias("detail_level")
    )


def _cast_metrics(
    df: pl.DataFrame, graduate_col: str, eligible_col: str, pct_col: str
) -> pl.DataFrame:
    """Cast the three metrics to gold dtypes; scale percent from 0-100 to 0-1.

    All bronze columns arrive as Utf8 (infer_schema_length=0 / dtype=str
    reads); TFS suppression markers were already nulled by read_bronze_file,
    and strict=False nulls any residual non-numeric string instead of
    raising.
    """
    return df.with_columns(
        pl.col(graduate_col).cast(pl.Int64, strict=False).alias("num_graduates"),
        pl.col(eligible_col).cast(pl.Int64, strict=False).alias("num_hope_eligible"),
        # Bronze percent is 0-100 in every era (structure-doc ETL note 16);
        # gold convention is the 0-1 proportion scale (§4).
        (pl.col(pct_col).cast(pl.Float64, strict=False) / 100.0).alias(
            "hope_eligible_rate"
        ),
    ).drop([graduate_col, eligible_col, pct_col])


def _split_composite_key(df: pl.DataFrame, key_col: str) -> pl.DataFrame:
    """Split a ``{district}:{school}`` composite key into raw code columns.

    Splits at the first ``:`` only (no school code contains a colon, but
    n=1 keeps the parse well-defined if one ever did). The raw halves still
    carry the ALL sentinels for _format_geography_codes to null.
    """
    return (
        df.with_columns(
            pl.col(key_col)
            .str.split_exact(":", n=1)
            .struct.rename_fields(["district_code_raw", "school_code_raw"])
            .alias("_split")
        )
        .unnest("_split")
        .drop(key_col)
    )


def _derive_aggregates(
    school_df: pl.DataFrame, year: int, include_state: bool
) -> pl.DataFrame:
    """Derive district (and optionally state) aggregate rows from school rows.

    Used where bronze omits the rollups: Era 4 / 2008 (district + state) and
    Era 7 / 2004 (district only — bronze has school + state). Counts are
    summed; the rate is the graduate-weighted mean sum(eligible) /
    sum(graduates) — NULL when the graduate sum is not positive — which
    matches how GOSA's own pre-aggregated 2008 sheets are computed.
    """
    district_agg = (
        school_df.group_by("district_code")
        .agg(
            pl.col("num_graduates").sum(),
            pl.col("num_hope_eligible").sum(),
        )
        .with_columns(
            pl.when(pl.col("num_graduates") > 0)
            .then(pl.col("num_hope_eligible") / pl.col("num_graduates"))
            .otherwise(None)
            .alias("hope_eligible_rate"),
            pl.lit(None).cast(pl.Utf8).alias("school_code"),
            pl.lit(year).cast(pl.Int32).alias("year"),
            pl.lit("district").alias("detail_level"),
        )
    )
    logger.info(
        "Year %d: derived %d district aggregate rows", year, district_agg.height
    )
    aggregates = [district_agg.select(STANDARD_COLUMNS)]

    if include_state:
        state_agg = school_df.select(
            pl.col("num_graduates").sum(),
            pl.col("num_hope_eligible").sum(),
        ).with_columns(
            pl.when(pl.col("num_graduates") > 0)
            .then(pl.col("num_hope_eligible") / pl.col("num_graduates"))
            .otherwise(None)
            .alias("hope_eligible_rate"),
            pl.lit(None).cast(pl.Utf8).alias("district_code"),
            pl.lit(None).cast(pl.Utf8).alias("school_code"),
            pl.lit(year).cast(pl.Int32).alias("year"),
            pl.lit("state").alias("detail_level"),
        )
        logger.info("Year %d: derived 1 state aggregate row", year)
        aggregates.append(state_agg.select(STANDARD_COLUMNS))

    return pl.concat(aggregates)


def _assert_in_file_year(path_name: str, in_file_year: int, filename_year: int) -> None:
    """Raise when an in-file year column disagrees with the filename year."""
    if in_file_year != filename_year:
        raise ValueError(
            f"{path_name}: in-file year {in_file_year} != filename year "
            f"{filename_year} — source drift, refusing to guess."
        )


# =============================================================================
# Era transforms
# =============================================================================


def _transform_era1(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Era 1 (2023-2024): explicit DETAIL_LVL_DESC + #RPT_NAME columns.

    detail_level is a recode of the bronze label (recorded to the manifest);
    geography sentinels and metric handling match Era 2.
    """
    # #RPT_NAME is the constant report label; LONG_SCHOOL_YEAR was already
    # asserted against the filename year by the dispatcher; the two name
    # columns are dimension attributes.
    df = df.drop(["#RPT_NAME", "LONG_SCHOOL_YEAR", "SCHOOL_DSTRCT_NM", "INSTN_NAME"])

    # Recode the bronze level label via replace_strict so an unexpected
    # label raises instead of passing through silently.
    bronze_levels = df["DETAIL_LVL_DESC"]
    df = df.with_columns(
        pl.col("DETAIL_LVL_DESC").replace_strict(DETAIL_LEVEL_MAP).alias("detail_level")
    ).drop("DETAIL_LVL_DESC")
    manifest.record_categorical(
        column="detail_level",
        map_dict=DETAIL_LEVEL_MAP,
        bronze_series=bronze_levels,
        gold_series=df["detail_level"],
    )

    df = _format_geography_codes(df, "SCHOOL_DISTRCT_CD", "INSTN_NUMBER")
    df = _cast_metrics(df, "NUMBER_OF_GRADUATES", "HOPE_ELIGIBLE", "HOPE_ELIGIBLE_PCT")
    df = df.with_columns(pl.lit(year).cast(pl.Int32).alias("year"))
    return df.select(STANDARD_COLUMNS)


def _transform_era2(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Era 2 (2009, 2011-2022): no DETAIL_LVL_DESC — level from ALL sentinels."""
    del manifest  # No recoded categoricals — detail_level is derived.
    df = df.drop(["LONG_SCHOOL_YEAR", "SCHOOL_DSTRCT_NM", "INSTN_NAME"])
    df = _format_geography_codes(df, "SCHOOL_DISTRCT_CD", "INSTN_NUMBER")
    df = _derive_detail_level_from_sentinels(df)
    df = _cast_metrics(df, "NUMBER_OF_GRADUATES", "HOPE_ELIGIBLE", "HOPE_ELIGIBLE_PCT")
    df = df.with_columns(pl.lit(year).cast(pl.Int32).alias("year"))
    return df.select(STANDARD_COLUMNS)


def _transform_composite_key_era(
    df: pl.DataFrame,
    year: int,
    key_col: str,
    name_col: str,
    graduate_col: str,
) -> pl.DataFrame:
    """Shared body for the composite-key eras (3, 5, 6, and 7's core).

    The four eras differ only in column-name spellings: the composite key
    column, the name column, and (Era 7) the graduate-count column.
    """
    df = df.drop(name_col)
    df = _split_composite_key(df, key_col)
    df = _format_geography_codes(df, "district_code_raw", "school_code_raw")
    df = _derive_detail_level_from_sentinels(df)
    df = _cast_metrics(df, graduate_col, "Number Eligible", "Percent Eligible")
    df = df.with_columns(pl.lit(year).cast(pl.Int32).alias("year"))
    return df.select(STANDARD_COLUMNS)


def _transform_era3(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Era 3 (2010): composite ``Sysschoolid`` + ``System/School Name``."""
    del manifest
    return _transform_composite_key_era(
        df, year, "Sysschoolid", "System/School Name", "Number of Graduates"
    )


def _transform_era4_2008(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Era 4 (2008): Report Card School Level sheet; aggregates derived.

    The reader loads only the first sheet (School Level — the atomic grain);
    the pre-aggregated System Level / State Level sheets are exact rollups
    of it (verified) and are intentionally not read. Row policy (verified
    against bronze, matches the bronze State Level totals):

    - 376 school rows with valid keys -> schools fact (the two rows sharing
      key 721/2574 — Westside High + Westside Comprehensive High — are
      distinct schools whose students are summed under the shared code).
    - 4 null-School-ID rows with a valid System ID (alternative campuses /
      evening schools; 226 graduates / 42 eligible) -> folded into district
      + state aggregates only (manifest: reclassified).
    - 1 fully orphaned row (RENAISSANCE ACADEMY: null System ID, School ID,
      System Name; 28 graduates / 0 eligible) -> excluded everywhere, as
      the bronze State Level sheet itself does (manifest: filtered).
    """
    # The in-file year columns are constant 2008; assert rather than trust.
    data_year = int(float(df["Data Year"].drop_nulls()[0]))
    _assert_in_file_year("hope_eligible_graduates_2008.xls", data_year, year)

    # Constants + dimension-attribute name columns.
    df = df.drop(
        [
            "Data Year",
            "Report Card Year",
            "Data Type",
            "Report Card Section",
            "System Name",
            "School Name",
        ]
    )

    # NULL ids must survive formatting (no ALL sentinels in this era).
    df = df.with_columns(
        pl.when(pl.col("System ID").is_null())
        .then(None)
        .otherwise(pl.col("System ID").str.zfill(3))
        .alias("district_code"),
        pl.when(pl.col("School ID").is_null())
        .then(None)
        .otherwise(pl.col("School ID").str.zfill(4))
        .alias("school_code"),
    ).drop(["System ID", "School ID"])

    df = _cast_metrics(
        df,
        "Number of Regular Graduates - Report Card",
        "# Eligible for HOPE 2008",
        "Percent Eligible",
    )
    df = df.with_columns(pl.lit(year).cast(pl.Int32).alias("year"))

    # --- Partition by id completeness --------------------------------
    school_rows = df.filter(pl.col("school_code").is_not_null())
    fold_rows = df.filter(
        pl.col("school_code").is_null() & pl.col("district_code").is_not_null()
    )
    orphan_rows = df.filter(
        pl.col("school_code").is_null() & pl.col("district_code").is_null()
    )
    if fold_rows.height > 0:
        manifest.record_reclassified(
            year,
            fold_rows.height,
            "null school_code rows with valid district folded into district/state "
            "aggregates only (alternative campuses without a school code)",
        )
    if orphan_rows.height > 0:
        manifest.record_filtered(
            year,
            orphan_rows.height,
            "fully_orphaned_null_id_row_excluded_from_all_levels",
        )
        logger.warning(
            "Year %d: dropping %d fully-orphaned row(s) (null district AND "
            "school id) — excluded from every aggregate, matching the bronze "
            "State Level sheet",
            year,
            orphan_rows.height,
        )

    # --- Sum the duplicate school key, recompute rate -----------------
    # Two real schools share key 721/2574; their cohorts are summed. The
    # group_by covers ALL school rows and recomputes the rate as e/g, which
    # is exact for singletons too: 2008 bronze Percent Eligible IS the
    # full-precision ratio (max |bronze/100 - e/g| ~ 1e-15 ulp noise), so no
    # published value changes — and the merged row + derived aggregates stay
    # arithmetically consistent.
    dup_groups = school_rows.group_by(NATURAL_KEYS).len().filter(pl.col("len") > 1)
    if dup_groups.height > 0:
        merged_away = int(dup_groups["len"].sum()) - dup_groups.height
        logger.info(
            "Year %d: summing %d duplicate school key group(s): %s",
            year,
            dup_groups.height,
            dup_groups.select(NATURAL_KEYS).to_dicts(),
        )
        manifest.record_filtered(
            year, merged_away, "duplicate_school_key_rows_summed_not_deduped"
        )
        school_rows = (
            school_rows.group_by(NATURAL_KEYS)
            .agg(
                pl.col("num_graduates").sum(),
                pl.col("num_hope_eligible").sum(),
            )
            .with_columns(
                pl.when(pl.col("num_graduates") > 0)
                .then(pl.col("num_hope_eligible") / pl.col("num_graduates"))
                .otherwise(None)
                .alias("hope_eligible_rate")
            )
        )

    school_out = school_rows.with_columns(
        pl.lit("school").alias("detail_level")
    ).select(STANDARD_COLUMNS)

    # District + state aggregates: schools plus the 4 fold rows (Renaissance
    # excluded — bronze State Level also excludes it, totals verified equal).
    agg_source_cols = [
        "year",
        "district_code",
        "school_code",
        "num_graduates",
        "num_hope_eligible",
        "hope_eligible_rate",
    ]
    rows_for_aggregates = pl.concat(
        [school_rows.select(agg_source_cols), fold_rows.select(agg_source_cols)]
    )
    aggregates = _derive_aggregates(rows_for_aggregates, year, include_state=True)
    return pl.concat([school_out, aggregates])


def _transform_era5(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Era 5 (2007): composite ``SYSSCHOOLID`` + ``SchoolNme``."""
    del manifest
    return _transform_composite_key_era(
        df, year, "SYSSCHOOLID", "SchoolNme", "Number of Graduates"
    )


def _transform_era6(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Era 6 (2006): composite ``SysSchoolID`` + ``School Name`` (with space)."""
    del manifest
    return _transform_composite_key_era(
        df, year, "SysSchoolID", "School Name", "Number of Graduates"
    )


def _transform_era7_2004_2005(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Era 7 (2004-2005): stale ``Number of 2004 Graduates`` header.

    Both files reuse the 2004-labeled graduate column; the 2005 values are
    the spring-2005 cohort (per-school numbers differ from 2004 — verified
    in the structure doc), so the label is ignored and the filename year
    wins. 2004 additionally has a junk footer row, eight trailing-x
    sub-tally school codes, and no district rollups (see module docstring).
    """
    # Junk footer row (2004 only): NUL-padded SYSSCHOOLID, all else null.
    # Filtering on null SchoolNme covers it without touching real rows
    # (2005 has zero null names — verified).
    junk = df.filter(pl.col("SchoolNme").is_null())
    if junk.height > 0:
        logger.info("Year %d: dropping %d junk footer row(s)", year, junk.height)
        manifest.record_filtered(year, junk.height, "footer_junk_row_all_null")
        df = df.filter(pl.col("SchoolNme").is_not_null())

    # Trailing-x school codes (2004 only): eight `{code}x` rows are
    # separately tallied sub-groups of a canonical same-named sibling row
    # (verified: every stripped code has a sibling). Strip the suffix so the
    # pair collides, then sum below.
    x_count = int(df["SYSSCHOOLID"].str.contains(r"x$").sum())
    if x_count > 0:
        logger.info(
            "Year %d: stripping trailing 'x' from %d sub-tally school code(s)",
            year,
            x_count,
        )
        df = df.with_columns(pl.col("SYSSCHOOLID").str.strip_suffix("x"))

    df = _transform_composite_key_era(
        df, year, "SYSSCHOOLID", "SchoolNme", "Number of 2004 Graduates"
    )

    # Sum the collided x-pairs (2004 only). Unlike Era 4, ONLY the duplicate
    # groups are regrouped: the bronze rate here is 1-decimal rounded, so
    # recomputing it for the 338 singleton schools would silently replace
    # published values; the 8 merged rows get the exact recomputed ratio.
    school_rows = df.filter(pl.col("detail_level") == "school")
    other_rows = df.filter(pl.col("detail_level") != "school")
    dup_groups = school_rows.group_by(NATURAL_KEYS).len().filter(pl.col("len") > 1)
    if dup_groups.height > 0:
        merged_away = int(dup_groups["len"].sum()) - dup_groups.height
        logger.info(
            "Year %d: summing %d sub-tally school key pair(s) after trailing-x "
            "normalization",
            year,
            dup_groups.height,
        )
        manifest.record_filtered(
            year, merged_away, "trailing_x_subtally_rows_summed_into_canonical_school"
        )
        duplicates = school_rows.join(
            dup_groups.select(NATURAL_KEYS), on=NATURAL_KEYS, how="semi"
        )
        singletons = school_rows.join(
            dup_groups.select(NATURAL_KEYS), on=NATURAL_KEYS, how="anti"
        )
        merged = (
            duplicates.group_by(NATURAL_KEYS)
            .agg(
                pl.col("detail_level").first(),
                pl.col("num_graduates").sum(),
                pl.col("num_hope_eligible").sum(),
            )
            .with_columns(
                pl.when(pl.col("num_graduates") > 0)
                .then(pl.col("num_hope_eligible") / pl.col("num_graduates"))
                .otherwise(None)
                .alias("hope_eligible_rate")
            )
            .select(STANDARD_COLUMNS)
        )
        school_rows = pl.concat([singletons, merged])
        df = pl.concat([other_rows, school_rows])

    # 2004 ships no district rollup rows (school + state only) — derive the
    # district level from the merged school rows so every year carries all
    # three detail levels. (2005 ships its own rollups; no-op there.)
    has_district_rows = df.filter(pl.col("detail_level") == "district").height > 0
    if not has_district_rows:
        district_agg = _derive_aggregates(
            df.filter(pl.col("detail_level") == "school"), year, include_state=False
        )
        df = pl.concat([df, district_agg])

    return df


# Era name -> transform function (dispatch table).
_ERA_TRANSFORMS = {
    "era_1_2023_2024_detail_lvl_desc": _transform_era1,
    "era_2_2009_2011_2022_long_school_year": _transform_era2,
    "era_3_2010_sysschoolid": _transform_era3,
    "era_4_2008_report_card": _transform_era4_2008,
    "era_5_2007_sysschoolid_uppercase": _transform_era5,
    "era_6_2006_sysschoolid_titlecase": _transform_era6,
    "era_7_2004_2005_stale_header": _transform_era7_2004_2005,
}


# =============================================================================
# File dispatcher
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read one bronze file, detect its era, cross-check the year, and route.

    All columns are read as Utf8 (infer_schema_length=0 for CSV; the shared
    XLS reader is all-string by construction) so suppression markers and the
    ALL sentinels survive until explicit casting (§4.3b).
    """
    year = extract_year_from_filename(path.name)
    if year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")

    df, loss = read_bronze_file(path, infer_schema_length=0, return_loss=True)
    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{path.name}: no era signature matched {sorted(df.columns)}")

    # Eras 1-2 carry LONG_SCHOOL_YEAR (`YYYY-YY`); assert its ending year
    # equals the filename year so a misnamed file fails loudly (ETL note 4).
    if "LONG_SCHOOL_YEAR" in df.columns:
        in_file = parse_school_year(df["LONG_SCHOOL_YEAR"].drop_nulls()[0])
        _assert_in_file_year(path.name, in_file, year)

    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)

    if df.height == 0:
        logger.warning("Year %d: bronze file %s is empty, skipping", year, path.name)
        return None

    logger.info(
        "Processing %s (year=%d, era=%s, rows=%d)", path.name, year, era, df.height
    )
    return _ERA_TRANSFORMS[era](df, year, manifest)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for hope_eligible_graduates."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform all 21 bronze files (read-loss accounted per file).
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

    # 3. Collision guard BEFORE dedup: after the era-internal sums (2004
    # trailing-x pairs, 2008 Westside pair) the natural key is unique across
    # all files — any collision here is a routing/aggregation bug.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: no duplicates expected (each file covers one year; verified
    # unique post-merge). Defensive net only — prefer the row with the larger
    # populated graduating cohort over a null/placeholder twin.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code"],
        district_keys=["year", "district_code"],
        state_keys=["year"],
        sort_col="num_graduates",
    )

    # 4. Geography nulling (shared domain rules — idempotent here: every era
    # already nulls its sentinels; transform and validator share one rule
    # source). No §4b masks: all values are physically possible (see module
    # docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # NULL-rate spikes are expected in the TFS years (2009, 2011-2024
    # suppress small cohorts) vs the suppression-free 2004-2008 + 2010 —
    # informational.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning(
            "NULL-rate spikes (expected — TFS years): %s", spike_result.details
        )
    validate_output(combined, required_non_null=["year", "detail_level"])

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

    The column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level`` — the contract properties (and the validator's schema
    check) follow it.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Governor's Office of Student Achievement (GOSA) HOPE "
            "Eligibility dataset. For every Georgia public high school, "
            "school district, and the state as a whole, reports the number "
            "of graduating seniors who met the academic eligibility "
            "criteria for Georgia's HOPE scholarship program. Three "
            "metrics: num_graduates (regular graduates), "
            "num_hope_eligible (subset that met HOPE academic "
            "eligibility), and hope_eligible_rate (the share that met "
            "eligibility, on a 0-1 decimal scale). Coverage: spring 2004 "
            "through spring 2024 (21 files; filename year = spring "
            "graduation year). No demographic / gender / race breakdowns — "
            "every row is the all-students total. There is a substantive "
            "series break between 2006 and 2007: state-level percent "
            "eligible drops from ~62%% (2006) to ~38%% (2007+). This "
            "reflects a real methodology change in HOPE eligibility "
            "determination, not a data-processing artifact: beginning with "
            "the high school graduating class of 2007, the Georgia Student "
            "Finance Commission (GSFC) began computing each student's HOPE "
            "GPA directly from electronic high-school transcript data (the "
            "GSFC-calculated HOPE GPA) rather than relying on the "
            "school-reported GPA used previously. The break is preserved "
            "as published, not 'fixed'. Treat 2004-2006 and 2007-2024 as "
            "separate eras when comparing percentages."
        ),
        title="HOPE-Eligible Graduates",
        summary=(
            "Georgia high school graduates who met the academic eligibility "
            "criteria for the HOPE scholarship, by school, district, and "
            "state, 2004-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Spring graduation year (e.g., 2024 = spring-2024 "
                    "graduating class, 2023-2024 school year). For Era 1 "
                    "and Era 2 files the filename year is cross-checked "
                    "against the LONG_SCHOOL_YEAR column's ending year and "
                    "must match."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "3-digit GOSA district code (zero-padded). 7-digit "
                    "charter / state-school codes pass through unchanged "
                    "(e.g., 7820412). NULL for state-level aggregate rows. "
                    "FK to districts dimension."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0103",
                "description": (
                    "4-digit GOSA school code (zero-padded). NULL for "
                    "district- and state-level aggregate rows. FK to "
                    "schools dimension (composite PK with district_code). "
                    "Bronze padding is inconsistent across eras (the "
                    "composite-key eras ship unpadded 3-digit codes; Era 2 "
                    "mixes by year; 2008 mixes within the file); the "
                    "transform normalizes to 4 digits via zfill."
                ),
            },
            {
                "name": "num_graduates",
                "metric_component": "denominator",
                "type": "int64",
                "unit": "count",
                "example": 335,
                "description": (
                    "Number of regular high-school graduates in the cohort. "
                    "NULL when suppressed in bronze (TFS = Too Few "
                    "Students, applied per the 2009 source SQL when "
                    "graduates <= 9; affects 2009 and 2011-2024) or when "
                    "the bronze cell is genuinely blank — a value GOSA left "
                    "unreported (all 2014 and 2020 NULLs are blank cells; "
                    "those files contain no TFS markers). The 2004-2008 and "
                    "2010 files have no suppression, so their values are "
                    "uncensored."
                ),
            },
            {
                "name": "num_hope_eligible",
                "metric_component": "numerator",
                "type": "int64",
                "unit": "count",
                "example": 170,
                "description": (
                    "Number of graduates in this cohort who met HOPE "
                    "academic eligibility (GPA + required-course "
                    "requirements). NULL when TFS-suppressed or when the "
                    "bronze cell is genuinely blank (both occur in "
                    "2011-2020; see the suppression note). May be 0 (e.g., "
                    "Renaissance Academy in 2008 had 28 graduates and 0 "
                    "HOPE-eligible — a real zero, not suppression). Never "
                    "exceeds num_graduates (enforced by a quality check; 0 "
                    "violations in bronze)."
                ),
            },
            {
                "name": "hope_eligible_rate",
                "key_metric": True,
                "type": "float64",
                "unit": "proportion",
                "example": 0.5075,
                "short_description": (
                    "Share of graduates that met HOPE academic eligibility, "
                    "on a 0-1 scale; NULL when suppressed (too few students)."
                ),
                "description": (
                    "Share of graduates that met HOPE academic eligibility, "
                    "on a 0-1 decimal scale (bronze 0-100 divided by 100). "
                    "NULL when TFS-suppressed or genuinely blank in bronze "
                    "(see the suppression note). For derived district + state "
                    "aggregates (2008 all levels above school; 2004 "
                    "district level) and bronze rows merged under one "
                    "school code (the 2004 trailing-x pairs, the 2008 "
                    "Westside pair), this is computed as "
                    "num_hope_eligible / num_graduates — a "
                    "graduate-count weighted mean across the contributing "
                    "rows. Reconciles with the published counts within "
                    "0.005 everywhere (measured max deviation 0.0005, from "
                    "1-decimal bronze rounding)."
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
                "Series break between 2006 and 2007: state-level percent "
                "eligible drops from ~62%% (2004-2006) to ~38%% (2007+). "
                "Real methodology change (GSFC-calculated HOPE GPA from "
                "electronic transcripts, replacing school-reported GPA), "
                "preserved as published. Treat 2004-2006 and 2007-2024 as "
                "separate eras when comparing percentages."
            ),
            (
                "Suppression: cells with graduating cohort <= 9 are "
                "suppressed in bronze as the literal string TFS (Too Few "
                "Students) and become NULL in gold. TFS appears in 2009 "
                "and most of 2011-2024 (full three-metric suppression in "
                "2009, 2021-2024; only num_hope_eligible and/or the rate "
                "in 2011-2013 and 2015-2019) — but TFS is NOT the only "
                "NULL mechanism: a small number of rows per year in "
                "2011-2020 (9-24 num_graduates cells, up to 37 "
                "eligible/rate cells) carry genuinely blank metric cells "
                "in bronze — unreported special programs / treatment "
                "centers — which are also NULL in gold, and 2014 and 2020 "
                "contain no TFS literals at all (their NULLs are entirely "
                "blank-driven). The 2004-2008 and 2010 files have no "
                "suppression — a literal 0 there is a true zero."
            ),
            (
                "2008 bronze is school-level only (the Report Card System "
                "Level / State Level sheets are exact pre-aggregations and "
                "are not read). District + state aggregate rows for 2008 "
                "are derived: counts summed, rate = sum(eligible) / "
                "sum(graduates). Four null-school-id rows (alternative "
                "campuses with a valid district; 226 graduates / 42 "
                "eligible) are folded into the district/state aggregates "
                "only; the fully orphaned RENAISSANCE ACADEMY row (28 "
                "graduates, 0 eligible, no district) is excluded "
                "everywhere — matching the bronze State Level total "
                "exactly (81,569 graduates / 31,443 eligible)."
            ),
            (
                "2008 also publishes two distinct schools (Westside High "
                "School and Westside Comprehensive High School) under the "
                "single key 721/2574; their cohorts are summed into one "
                "row (381 graduates / 91 eligible) rather than deduped."
            ),
            (
                "2004 has no district rollup rows in bronze (school + "
                "state only); the transform derives the 174 district "
                "aggregates from school rows so every year carries all "
                "three detail levels. Known 2004 bronze artifact: the "
                "official state row (68,163 graduates / 42,233 eligible) "
                "is ~0.2%% higher than the sum of itemized school rows "
                "(68,029 / 42,146); both preserved as published."
            ),
            (
                "2004 contains eight school codes with a trailing 'x' "
                "(e.g. 644:775x) — separately tallied sub-groups of a "
                "canonical same-named sibling row. The suffix is stripped "
                "and each pair is summed; the merged rows' rate is "
                "recomputed from the summed counts. One junk footer row "
                "(all fields null) is dropped."
            ),
            (
                "2005 file quirk: delivered with a .csv extension but is "
                "actually a legacy XLS binary (read via magic-byte "
                "detection). It also reuses the stale 2004 column header "
                "'Number of 2004 Graduates' — the values are the "
                "spring-2005 cohort; year assignment uses the filename."
            ),
            (
                "ID padding: school codes are zero-padded to 4 digits and "
                "district codes to 3 (7-digit charter / state-school codes "
                "pass through), normalizing the mixed bronze padding for "
                "dimension joins."
            ),
            (
                "No demographic breakdowns in any era — the demographic "
                "column is omitted entirely per data-cleaning-standards §5."
            ),
        ],
        limitations=(
            "Suppressed cells are NULL (not zero). State rows have NULL "
            "district_code and school_code; district rows have NULL "
            "school_code. Derived-aggregate caveat: for 2008 the bronze "
            "ships only school-level rows, so all district and state "
            "aggregate rows are derived here (sum of counts, "
            "graduate-count-weighted mean for hope_eligible_rate); the "
            "derived 2008 state total matches the bronze State Level sheet "
            "exactly (Renaissance Academy, fully orphaned, is excluded by "
            "both). For 2004 the bronze has school + state rows but no "
            "district rollups, so the 2004 district rows are likewise "
            "derived from the school rows. A separate known 2004 bronze "
            "artifact means the official state total (68,163 graduates / "
            "42,233 eligible) is ~0.2% higher than the sum of itemized "
            "2004 school rows, so a user roll-up from schools/districts "
            "to state will be ~0.2% short for 2004 only."
        ),
        quality_checks=[
            {
                "name": "num_hope_eligible_not_exceeding_num_graduates",
                "description": (
                    "The HOPE-eligible subset (num_hope_eligible) never "
                    "exceeds the graduating cohort (num_graduates) where "
                    "both are present. Verified 0 violations across all "
                    "21 bronze files."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE num_hope_eligible IS NOT NULL "
                    "AND num_graduates IS NOT NULL "
                    "AND num_hope_eligible > num_graduates"
                ),
                "mustBe": 0,
            },
            {
                "name": "hope_eligible_rate_reconciles_with_count_over_graduates",
                "description": (
                    "Where all three metrics are present and "
                    "num_graduates > 0, the published rate equals "
                    "num_hope_eligible / num_graduates within 0.005 "
                    "(0.5pp). Measured max bronze deviation is 0.0005 — "
                    "half-ulp of the 1-decimal rounding used in 2004-2007 "
                    "and 2010; derived/merged rows are exact by "
                    "construction."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE hope_eligible_rate IS NOT NULL "
                    "AND num_hope_eligible IS NOT NULL "
                    "AND num_graduates IS NOT NULL AND num_graduates > 0 "
                    "AND ABS(hope_eligible_rate "
                    "- (CAST(num_hope_eligible AS DOUBLE) "
                    "/ num_graduates)) > 0.005"
                ),
                "mustBe": 0,
            },
            {
                "name": "suppression_nulls_graduates_last",
                "description": (
                    "Co-null structure of TFS suppression: whenever "
                    "num_graduates is NULL, num_hope_eligible and "
                    "hope_eligible_rate are NULL too (full suppression "
                    "censors all three together; partial suppression "
                    "censors only the eligible count and/or the rate, "
                    "never the graduate count alone). Verified 0 "
                    "violations across all bronze years."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE num_graduates IS NULL "
                    "AND (num_hope_eligible IS NOT NULL "
                    "OR hope_eligible_rate IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "exactly_one_state_row_per_year",
                "description": (
                    "Structural fact: every published year carries exactly "
                    "one statewide rollup row (both geography keys NULL) — "
                    "from bronze in 20 years, derived from school rows in "
                    "2008. More or fewer means a level-classification or "
                    "aggregation bug."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year FROM {object} "
                    "WHERE district_code IS NULL AND school_code IS NULL "
                    "GROUP BY year HAVING COUNT(*) <> 1"
                    ") AS bad_years"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
