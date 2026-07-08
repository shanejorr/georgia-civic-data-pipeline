"""Transform bronze retained_students files into gold fact tables.

Source: Governor's Office of Student Achievement (GOSA) — Retained K-12
report, school years 2003-04 through 2023-24 (21 bronze files, one per
year). For every Georgia public school, district, and the state, reports
the number of K-12 students retained (held back), the total K-12
enrollment (2011 onward only), and a demographic breakdown of the
retained population: counts and shares of retained by race (6 buckets)
and gender.

Design decisions (every invariant re-verified against THIS topic's 21
bronze files during authoring — see bronze-data-structure.md, including
its Corrections section):

- **Four bronze eras, three transform paths.**
    * tidy (2011-2024): explicit ``Data Reporting Level``, split district/
      school code columns, ``Total Enrolled`` + ``Total Retained``, and one
      ``Number of {demo}`` / ``Percentage of {demo}`` pair per demographic.
      2023-2024 (era 1) uses underscore separators and adds a constant
      ``#RPT_NAME`` column ("Retained K-12", guarded); 2011-2022 (era 2)
      uses space separators. One function handles both via an era-1 rename.
    * wide_v1 (2007-2008): cryptic ``Retained_T{X}``/``_P{X}`` suffix codes
      with compound ``SysSchoolid`` geography. ``Retained_NN`` IS the total
      retained count and the 7 other ``Retained_N*`` columns are redundant
      copies of it (verified 100%% equal in both years).
    * wide_v2 (2004-2006, 2009, 2010): human-readable wide layout
      (``Retained Total {Demo}`` / ``Retained Percent {Demo}``), compound
      ``SysSchoolid``. ``Retained Total Students`` IS the total retained;
      the no-"Total" ``Retained {Demo}`` columns (2004-2006, 2009) are
      redundant copies of it and are not selected.

- **Structure-doc correction: the wide eras publish NO enrollment.** The
  bronze doc originally read ``Retained_NN`` / ``Retained Total Students``
  as "Total Enrolled". They are the TOTAL RETAINED count: at every state
  row 2004-2010 the value (58,302 ... 59,999) equals both the race-bucket
  sum and the male+female sum of the retained counts, and is ~3.5%% of
  Georgia's ~1.6M K-12 enrollment. ``num_students`` is therefore NULL for
  every 2004-2010 row; only the tidy era carries enrollment.

- **Asian / Pacific Islander is the combined bucket (§5b).** The source has
  exactly 6 race buckets and never a separate Pacific Islander row. The
  math test proves the convention: the 6 race-bucket retained counts sum
  EXACTLY to the total retained at the state row in every year 2004-2024
  (and at every row where all 6 are published — 0 mismatches across all
  21 files). Bare bronze "Asian"/"Asians" is remapped to
  "Asian/Pacific Islander" before normalization so it canonicalizes to
  ``asian_pacific_islander``. Never split, no synthesized rollup rows.

- **Gold shape: tidy long, one row per (year, geography, demographic).**
  The synthetic ``all`` demographic row carries the overall
  ``num_retained`` (and ``num_students`` where published);
  per-demographic rows carry the demographic's retained count and
  ``pct_of_retained_cohort`` — the SHARE of the retained cohort in that
  demographic (bronze 0-100, divided by 100), NOT a within-demographic
  retention rate. ``pct_of_retained_cohort`` is NULL on ``all`` rows (100%%
  by definition); ``num_students`` is NULL on every non-``all`` row
  (bronze has no per-demographic enrollment).

- **§4b mask: 2012 ``Total Enrolled`` is corrupt — num_students NULLed.**
  The 2012 file publishes enrollment inflated ~17x at every detail level
  (state row 27,864,309 vs ~1.63M/1.66M in 2011/2013). Serving it would
  produce silently-wrong retention rates (~0.2%% vs the real ~3.4%%), so
  ``num_students`` is NULLed for all 2012 rows via
  ``_null_corrupt_2012_num_students`` (manifest-recorded);
  ``num_retained`` for 2012 is internally consistent and preserved.

- **2009 corrupted percent columns, derived from counts.** In the 2009
  file only, ``Retained Percent White`` and ``Retained Percent
  Multiracial`` are corrupted — both publish the Male percentage at the
  state row (61.1 vs derived 32.5 White / 2.6 Multiracial), with 656 White
  and 57 Multiracial rows off by >1pp file-wide (every other demographic
  and year matches count/total exactly; apparent mismatches elsewhere are
  0/0 rows). The counts and the total are internally consistent, so for
  these two (year, demo) pairs ``pct_of_retained_cohort`` is derived as
  ``count / total`` instead of trusting the published percent.

- **2010 bronze defects.** One malformed row (``SysSchoolid=" Few
  Students"``, no colon, all metrics NULL — an export artifact) is dropped
  and manifest-recorded. 53 SysSchoolid keys appear twice: 52 pairs are
  byte-identical and 1 (746:4050 Chattanooga Valley Elementary) has an
  incomplete twin whose extra cells are suppressed; the bronze-level dedup
  keeps the most complete row per key (manifest-recorded). Deduping at the
  bronze stage (before the 9-row demographic expansion) keeps the
  collision guard meaningful and avoids aggregating all-NULL
  ``num_students`` into spurious zeros.

- **2022 mislabeled aggregates, reclassified.** The 2022 file labels the
  district-aggregate rows of two state-charter districts (7830627,
  7830636) as ``Data Reporting Level=School`` while carrying the
  ``School Code=ALL`` aggregate sentinel (2 bronze rows). The sentinel
  proves the rows are aggregates; they are reclassified to district detail
  (manifest-recorded). 2022 has no genuine District rows for those codes,
  so no collision (the guard would catch one).

- **Suppression markers** (all → NULL): ``TFS`` (2021-2024), ``Too Few
  Students`` (2011-2020, 2010), literal ``NULL`` strings (5-8 rows in
  2005-2007; nulled by the readers/casts), true empty cells (2009, plus
  1-2 strays in 2010). 2004 and 2008 have no markers. ``read_bronze_file``
  plus strict=False casts cover every variant.

- **Dedup tie-break.** Years never overlap across files and the bronze
  grain is unique within every file after the 2010 bronze-level dedup, so
  no natural-key duplicates are expected; ``sort_col="num_retained"``
  remains as the documented safety net (prefer a reported count over a
  suppressed placeholder).

- **Quality checks (§15b).** Race and gender partition sums are authored
  as NULL-guarded conditional-aggregation checks at every level (verified:
  0 mismatches across all 21 files where all components are published);
  plus retained<=enrollment, the structural num_students availability
  rule, and pct-NULL-on-all. Percent partition sums are NOT authored: the
  tidy-era source rounds shares to whole percents (state sums range
  99-101) and 2023/2024 suppress the state American Indian share, so the
  count-based checks pin the same invariant exactly without the fragility.
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

TOPIC = "retained_students"
BRONZE_DIR = Path("data/bronze/education/gosa/retained_students")
GOLD_DIR = Path("data/gold/education/retained_students")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Aggregate-row sentinel: tidy-era `School District Code` (state rows) and
# `School Code` (state + district rows), and both halves of the wide-era
# compound `SysSchoolid`. Becomes NULL in gold, never a key value.
GEOGRAPHY_SENTINEL = "ALL"

# Era 1's constant #RPT_NAME value — anything else means foreign report rows.
ERA1_REPORT_NAME = "Retained K-12"

DETAIL_LEVEL_MAP: dict[str, str] = {
    "State": "state",
    "District": "district",
    "School": "school",
}

# Era-detection signatures, most-specific first (tidy era 1 is a superset of
# era 2 after accounting for the `_` vs ` ` separator; the wide eras are
# disambiguated by their unique total-retained column names).
ERA_SIGNATURES: dict[str, list[str]] = {
    "tidy_era1_2023_2024": ["#RPT_NAME", "School_Year", "Data_Reporting_Level"],
    "tidy_era2_2011_2022": ["School Year", "Data Reporting Level"],
    "wide_v1_2007_2008": ["SysSchoolid", "Retained_NN", "Retained_TN"],
    "wide_v2_2004_2010": ["SysSchoolid", "Retained Total Students"],
}

# Tidy-era demographic column suffixes in the era-2 (space-separated)
# spelling; era 1 uses the same words with `_` separators. Order is the
# bronze column order; output order is irrelevant (export sorts rows).
TIDY_DEMO_SUFFIXES: list[str] = [
    "Asians",
    "American Indian",
    "Black",
    "Hispanic",
    "MultiRacial",
    "White",
    "Male",
    "Female",
]

# Wide_v1 (2007-2008) suffix codes -> bronze demographic label.
# `Retained_T{X}` = retained count, `Retained_P{X}` = share-of-retained pct.
# `U` is Multiracial ("Unclassified"): confirmed by column position and by
# state-row continuity with 2009's explicit Multiracial column.
WIDE_V1_DEMO_LABELS: dict[str, str] = {
    "N": "American Indian",
    "A": "Asian",
    "B": "Black",
    "H": "Hispanic",
    "U": "Multiracial",
    "W": "White",
    "M": "Male",
    "F": "Female",
}

# Wide_v1 total-retained column. The other `Retained_N*` columns are
# redundant copies (verified 100% equal in 2007 and 2008) and are ignored.
WIDE_V1_TOTAL_COL = "Retained_NN"

# Wide_v2 (2004-2006, 2009, 2010) demographic labels.
# Count column: `Retained Total {Label}`; percent: `Retained Percent {Label}`.
WIDE_V2_DEMO_LABELS: list[str] = [
    "American Indian",
    "Asian",
    "Black",
    "Hispanic",
    "Multiracial",
    "White",
    "Male",
    "Female",
]

# Wide_v2 total-retained column. The no-"Total" `Retained {Demo}` columns
# (2004-2006, 2009 only) are redundant copies of it (verified: zero non-null
# mismatches) and are never selected.
WIDE_V2_TOTAL_COL = "Retained Total Students"

# 2009-only corrupted percent columns (see module docstring): for these
# (year -> demo labels) the share is derived from count/total instead of the
# published percent. Counts and the total are internally consistent in 2009.
WIDE_V2_CORRUPTED_PCT: dict[int, set[str]] = {
    2009: {"White", "Multiracial"},
}

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "num_retained",
    "num_students",
    "pct_of_retained_cohort",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "demographic": pl.Utf8,
    "num_retained": pl.Int64,
    "num_students": pl.Int64,
    "pct_of_retained_cohort": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = [
    "num_retained",
    "num_students",
    "pct_of_retained_cohort",
]

NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "detail_level",
]

# The 9 canonical demographic keys this topic publishes (contract enum).
DEMOGRAPHIC_VALUES: list[str] = sorted(
    [
        "all",
        "asian_pacific_islander",
        "black",
        "female",
        "hispanic",
        "male",
        "multiracial",
        "native_american",
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
# Shared helpers
# =============================================================================


def _raw_demographic_label(bronze_label: str) -> str:
    """Remap bare bronze 'Asian'/'Asians' to the combined OMB bucket label.

    This source has only 6 race buckets and the race-bucket retained counts
    sum exactly to the total retained at the state row in every year
    2004-2024 — Pacific Islanders are folded in, not dropped (§5b math
    test). Mapping the bare label through DEMOGRAPHIC_ALIASES would
    canonicalize to `asian` and falsely imply an Asian-only bucket; the
    remap canonicalizes to `asian_pacific_islander` instead.
    """
    if bronze_label in {"Asian", "Asians"}:
        return "Asian/Pacific Islander"
    return bronze_label


def _count_expr(col: str) -> pl.Expr:
    """Cast an all-string bronze count column to Int64 via Float64.

    The Float64 hop tolerates float-formatted count strings (Era 1
    `Total_Enrolled` is "3237.00000"; pandas-read Excel counts are "42.0")
    without silently nulling them. strict=False on both casts turns any
    residual non-numeric string (suppression markers the reader missed,
    e.g. literal "NULL") into NULL instead of failing.
    """
    return pl.col(col).cast(pl.Float64, strict=False).cast(pl.Int64, strict=False)


def _pct_expr(col: str) -> pl.Expr:
    """Cast a bronze 0-100 percent column to the 0-1 proportion scale (§4)."""
    return pl.col(col).cast(pl.Float64, strict=False) / 100.0


def _require_columns(df: pl.DataFrame, required: list[str], label: str) -> None:
    """Raise if any expected bronze column is absent (rename-coverage guard).

    An unmatched source column silently becomes NULL in gold — the most
    common data-loss bug — so a missing column fails loudly instead.
    """
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"{label}: expected bronze column(s) missing: {missing}. "
            f"Present: {sorted(df.columns)}"
        )


def _melt_to_long(
    df: pl.DataFrame,
    all_retained_expr: pl.Expr,
    all_student_expr: pl.Expr,
    demo_specs: list[tuple[str, pl.Expr, pl.Expr]],
) -> pl.DataFrame:
    """Build the tidy long frame: one `all` row + one row per demographic.

    The caller must have already derived `year`, `district_code`,
    `school_code`, and `detail_level` on `df`. The `all` row carries the
    overall retained count (and enrollment where the era publishes it) with
    a NULL share (100%% by definition); each demographic row carries that
    demographic's retained count and share, with NULL `num_students`
    (bronze never publishes per-demographic enrollment).

    Args:
        df: Entity-grain DataFrame with the geography keys derived.
        all_retained_expr: Expression for the overall retained count.
        all_student_expr: Expression for total enrollment (NULL literal for
            the wide eras, which publish no enrollment).
        demo_specs: One (bronze_label, num_retained_expr, pct_expr) per
            demographic.

    Returns:
        Long DataFrame with a `demographic_raw` column (pre-normalization).
    """
    key_cols = [
        pl.col("year"),
        pl.col("district_code"),
        pl.col("school_code"),
        pl.col("detail_level"),
    ]
    frames = [
        df.select(
            *key_cols,
            pl.lit("all").alias("demographic_raw"),
            all_retained_expr.alias("num_retained"),
            all_student_expr.alias("num_students"),
            pl.lit(None).cast(pl.Float64).alias("pct_of_retained_cohort"),
        )
    ]
    for label, count_expr, pct_expr in demo_specs:
        frames.append(
            df.select(
                *key_cols,
                pl.lit(_raw_demographic_label(label)).alias("demographic_raw"),
                count_expr.alias("num_retained"),
                pl.lit(None).cast(pl.Int64).alias("num_students"),
                pct_expr.alias("pct_of_retained_cohort"),
            )
        )
    return pl.concat(frames, how="vertical")


def _normalize_demographics(
    melted: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Normalize `demographic_raw` via the shared canonical path (§5).

    Records the effective slice of the shared alias map — only the aliases
    this file's labels actually hit — so the manifest stays reviewable while
    the unmapped guard still flags any label the shared map cannot place.
    """
    melted = melted.with_columns(
        normalize_demographic_column("demographic_raw").alias("demographic")
    )
    observed_upper = {
        str(v).strip().upper()
        for v in melted["demographic_raw"].drop_nulls().unique().to_list()
    }
    effective_map = {
        k: v for k, v in DEMOGRAPHIC_ALIASES.items() if k in observed_upper
    }
    manifest.record_categorical(
        column="demographic",
        map_dict=effective_map,
        bronze_series=melted["demographic_raw"],
        gold_series=melted["demographic"],
    )
    return melted.select(STANDARD_COLUMNS)


# =============================================================================
# Wide-era helpers (2004-2010): compound SysSchoolid geography
# =============================================================================


def _filter_malformed_sysschoolid(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Drop rows whose SysSchoolid lacks the `:` delimiter.

    Known case: 2010 has exactly one row with `SysSchoolid=" Few Students"`
    (all metrics NULL) — a corrupt export artifact, not an entity. Rows
    without `:` cannot yield geography and would corrupt the split.
    """
    bad_mask = pl.col("SysSchoolid").is_null() | ~pl.col("SysSchoolid").str.contains(
        ":"
    )
    bad = df.filter(bad_mask)
    if bad.height:
        logger.warning(
            "Year %d: dropping %d malformed bronze row(s) with SysSchoolid "
            "lacking ':'. Sample: %s",
            year,
            bad.height,
            bad["SysSchoolid"].head(5).to_list(),
        )
        df = df.filter(~bad_mask)
        # Explicit manifest record: the per-demographic expansion makes the
        # derived bronze-minus-gold count meaningless for this removal.
        manifest.record_filtered(year, bad.height, "malformed_sysschoolid")
    return df


def _dedup_bronze_duplicates(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Keep one row per SysSchoolid, preferring the most complete row.

    Known case: 2010 publishes 53 SysSchoolid keys twice — 52 byte-identical
    pairs plus one (746:4050) whose twin has extra suppressed (NULL) cells.
    Tie-break: most non-null metric cells wins (the suppressed twin loses);
    identical pairs are unaffected by order. Deduping at the bronze stage —
    before the 9-row demographic expansion — keeps the natural-key collision
    guard meaningful downstream.
    """
    dup_keys = df.group_by("SysSchoolid").len().filter(pl.col("len") > 1).height
    if dup_keys == 0:
        return df

    before = df.height
    metric_cols = [
        c for c in df.columns if c not in ("SysSchoolid", "School Name", "SchoolNme")
    ]
    df = (
        df.with_columns(
            pl.sum_horizontal(
                [pl.col(c).is_not_null().cast(pl.Int32) for c in metric_cols]
            ).alias("_non_null_count")
        )
        .sort("_non_null_count", descending=True)
        .unique(subset=["SysSchoolid"], keep="first", maintain_order=True)
        .drop("_non_null_count")
    )
    dropped = before - df.height
    logger.warning(
        "Year %d: dropped %d duplicate bronze row(s) across %d duplicated "
        "SysSchoolid key(s); kept the most complete row per key.",
        year,
        dropped,
        dup_keys,
    )
    manifest.record_filtered(year, dropped, "duplicate_sysschoolid")
    return df


def _derive_wide_geography(df: pl.DataFrame, year: int) -> pl.DataFrame:
    """Derive year + detail_level + geography keys from compound SysSchoolid.

    Format `{district}:{school}`: `ALL:ALL` -> state, `{district}:ALL` ->
    district, `{district}:{school}` -> school. District zfill(3) preserves
    7-digit charter codes; school zfill(4) pads the unpadded wide-era codes
    (e.g. `103` -> `0103`) to the tidy-era format. The `:` split is reliable
    (malformed rows were filtered upstream; neither half contains a colon).
    """
    parts = pl.col("SysSchoolid").str.split_exact(":", 1)
    dist_raw = parts.struct.field("field_0")
    sch_raw = parts.struct.field("field_1")
    return df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.when((dist_raw == GEOGRAPHY_SENTINEL) & (sch_raw == GEOGRAPHY_SENTINEL))
        .then(pl.lit("state"))
        .when(sch_raw == GEOGRAPHY_SENTINEL)
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .alias("detail_level"),
        pl.when(dist_raw == GEOGRAPHY_SENTINEL)
        .then(None)
        .otherwise(dist_raw.cast(pl.Utf8).str.zfill(3))
        .alias("district_code"),
        pl.when(sch_raw == GEOGRAPHY_SENTINEL)
        .then(None)
        .otherwise(sch_raw.cast(pl.Utf8).str.zfill(4))
        .alias("school_code"),
    )


# =============================================================================
# Era transforms
# =============================================================================


def _transform_wide_v1(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Transform a wide_v1 (2007-2008) file into gold long rows.

    `Retained_NN` is the total retained count (NOT enrollment — see module
    docstring); the era publishes no enrollment, so `num_students` is NULL
    everywhere. The redundant `Retained_N{A,B,F,H,M,U,W}` copies of NN are
    never selected.
    """
    required = ["SysSchoolid", WIDE_V1_TOTAL_COL]
    for suffix in WIDE_V1_DEMO_LABELS:
        required += [f"Retained_T{suffix}", f"Retained_P{suffix}"]
    _require_columns(df, required, f"wide_v1 {year}")

    df = _filter_malformed_sysschoolid(df, year, manifest)
    df = _dedup_bronze_duplicates(df, year, manifest)
    df = _derive_wide_geography(df, year)

    demo_specs = [
        (label, _count_expr(f"Retained_T{suffix}"), _pct_expr(f"Retained_P{suffix}"))
        for suffix, label in WIDE_V1_DEMO_LABELS.items()
    ]
    melted = _melt_to_long(
        df,
        all_retained_expr=_count_expr(WIDE_V1_TOTAL_COL),
        all_student_expr=pl.lit(None).cast(pl.Int64),
        demo_specs=demo_specs,
    )
    return _normalize_demographics(melted, manifest)


def _transform_wide_v2(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Transform a wide_v2 (2004-2006, 2009, 2010) file into gold long rows.

    `Retained Total Students` is the total retained count (NOT enrollment);
    no enrollment exists in this era, so `num_students` is NULL everywhere.
    The redundant no-"Total" `Retained {Demo}` copies (2004-2006, 2009) and
    2009's two stray unnamed Excel-artifact columns are never selected.

    For the 2009 corrupted percent columns (White, Multiracial) the share is
    derived from `count / total` instead of the published percent (see
    module docstring; counts and total are internally consistent in 2009).
    """
    required = ["SysSchoolid", WIDE_V2_TOTAL_COL]
    for label in WIDE_V2_DEMO_LABELS:
        required += [f"Retained Total {label}", f"Retained Percent {label}"]
    _require_columns(df, required, f"wide_v2 {year}")

    df = _filter_malformed_sysschoolid(df, year, manifest)
    df = _dedup_bronze_duplicates(df, year, manifest)
    df = _derive_wide_geography(df, year)

    corrupted = WIDE_V2_CORRUPTED_PCT.get(year, set())
    if corrupted:
        logger.warning(
            "Year %d: deriving pct_of_retained_cohort from counts for %s "
            "(published percent columns are corrupt — see module docstring).",
            year,
            sorted(corrupted),
        )
    demo_specs = []
    for label in WIDE_V2_DEMO_LABELS:
        count_col = f"Retained Total {label}"
        if label in corrupted:
            # Derive the share from the trustworthy counts. NULL-safe: NULL
            # when count or total is NULL, and when total is 0 (0/0 has no
            # defined share; bronze publishes 0 there, but a derived value
            # must not fabricate one).
            count_f = pl.col(count_col).cast(pl.Float64, strict=False)
            total_f = pl.col(WIDE_V2_TOTAL_COL).cast(pl.Float64, strict=False)
            pct = (
                pl.when(total_f.is_not_null() & (total_f > 0))
                .then(count_f / total_f)
                .otherwise(None)
            )
        else:
            pct = _pct_expr(f"Retained Percent {label}")
        demo_specs.append((label, _count_expr(count_col), pct))

    melted = _melt_to_long(
        df,
        all_retained_expr=_count_expr(WIDE_V2_TOTAL_COL),
        all_student_expr=pl.lit(None).cast(pl.Int64),
        demo_specs=demo_specs,
    )
    return _normalize_demographics(melted, manifest)


def _transform_tidy(
    df: pl.DataFrame, year: int, manifest: TransformManifest, era: str
) -> pl.DataFrame:
    """Transform a tidy-era (2011-2024) file into gold long rows.

    The only era with enrollment: `Total Enrolled` lands on the `all` row's
    `num_students` (bronze publishes no per-demographic enrollment). Era 1
    (2023-2024) differs from era 2 only by `_` separators and the constant
    `#RPT_NAME` column, unified here by a rename.
    """
    if era == "tidy_era1_2023_2024":
        # Era 1 constant guard: foreign #RPT_NAME values mean non-retained
        # report rows are mixed into this topic's bronze — fail loudly.
        rpt = df["#RPT_NAME"].drop_nulls().unique().to_list()
        if rpt != [ERA1_REPORT_NAME]:
            raise ValueError(f"tidy_era1 {year}: unexpected #RPT_NAME values {rpt}")
        # Unify on the era-2 space-separated spellings; one code path below.
        rename = {c: c.replace("_", " ") for c in df.columns if c not in ("#RPT_NAME",)}
        df = df.drop("#RPT_NAME").rename(rename)
        # Era 1 spells it "Number of American Indian" after the underscore
        # swap — identical to era 2, so no special-casing is needed.

    required = [
        "School Year",
        "Data Reporting Level",
        "School District Code",
        "School Code",
        "Total Enrolled",
        "Total Retained",
    ]
    for suffix in TIDY_DEMO_SUFFIXES:
        required += [f"Number of {suffix}", f"Percentage of {suffix}"]
    _require_columns(df, required, f"{era} {year}")

    # Detail level: State/District/School -> snake_case; unmapped values
    # surface via the manifest's unmapped guard.
    df = df.with_columns(
        pl.col("Data Reporting Level")
        .replace_strict(DETAIL_LEVEL_MAP, default=None)
        .alias("detail_level")
    )
    manifest.record_categorical(
        column="detail_level",
        map_dict=DETAIL_LEVEL_MAP,
        bronze_series=df["Data Reporting Level"],
        gold_series=df["detail_level"],
    )

    # Source mislabeling repair: a "School" row carrying the School Code=ALL
    # aggregate sentinel is a district aggregate by definition (2022: two
    # state-charter districts, 7830627/7830636). Reclassify to district.
    mislabeled = (pl.col("detail_level") == "school") & (
        pl.col("School Code") == GEOGRAPHY_SENTINEL
    )
    n_mislabeled = df.filter(mislabeled).height
    if n_mislabeled:
        affected = df.filter(mislabeled)["School District Code"].unique().to_list()
        manifest.record_reclassified(
            year, n_mislabeled, "school_labeled_aggregate_to_district"
        )
        logger.warning(
            "Year %d: reclassified %d School-labeled aggregate row(s) "
            "(School Code='ALL') to district detail (districts: %s).",
            year,
            n_mislabeled,
            sorted(affected),
        )
        df = df.with_columns(
            pl.when(mislabeled)
            .then(pl.lit("district"))
            .otherwise(pl.col("detail_level"))
            .alias("detail_level")
        )

    # Geography keys: ALL sentinel -> NULL; zfill pads 3-digit district /
    # 4-digit school codes and passes 7-digit charter codes through.
    df = df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.when(pl.col("School District Code") == GEOGRAPHY_SENTINEL)
        .then(None)
        .otherwise(pl.col("School District Code").cast(pl.Utf8).str.zfill(3))
        .alias("district_code"),
        pl.when(pl.col("School Code") == GEOGRAPHY_SENTINEL)
        .then(None)
        .otherwise(pl.col("School Code").cast(pl.Utf8).str.zfill(4))
        .alias("school_code"),
    )

    demo_specs = [
        (
            suffix,
            _count_expr(f"Number of {suffix}"),
            _pct_expr(f"Percentage of {suffix}"),
        )
        for suffix in TIDY_DEMO_SUFFIXES
    ]
    melted = _melt_to_long(
        df,
        all_retained_expr=_count_expr("Total Retained"),
        all_student_expr=_count_expr("Total Enrolled"),
        demo_specs=demo_specs,
    )
    return _normalize_demographics(melted, manifest)


# =============================================================================
# File dispatcher
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read one bronze file, detect its era, and route to its transform.

    Year resolution: tidy files carry exactly one `School Year` value whose
    ending year must agree with the filename year (a misnamed file cannot
    silently mislabel a year); wide files have no year column, so the
    filename year (= ending calendar year of the school year, the GOSA
    convention) is canonical.
    """
    # All-string read: geography codes keep leading zeros and the ALL
    # sentinels survive schema inference. Suppression markers (TFS / Too Few
    # Students) arrive as NULL from the reader; the mislabeled-XLS 2005/2006
    # files and the true .xls 2007-2009 files are detected by magic bytes
    # and read via pandas (dtype=str), where raw == parsed by construction.
    df, loss = read_bronze_file(path, infer_schema_length=0, return_loss=True)
    filename_year = extract_year_from_filename(path.name)
    if filename_year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")
    manifest.record_read_loss(
        filename_year, path.name, loss["raw_rows"], loss["parsed_rows"]
    )

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(
            f"{path.name}: no era signature matched columns {sorted(df.columns)}"
        )

    # Resolve + cross-check the year for tidy eras (wide eras: filename only).
    year_col = "School_Year" if "School_Year" in df.columns else "School Year"
    if year_col in df.columns:
        school_years = df[year_col].drop_nulls().unique().to_list()
        if len(school_years) != 1:
            raise ValueError(
                f"{path.name}: expected one {year_col} value, got {school_years}"
            )
        year = parse_school_year(school_years[0])
        if year != filename_year:
            raise ValueError(
                f"{path.name}: {year_col} ending year {year} disagrees with "
                f"filename year {filename_year}"
            )
    else:
        year = filename_year

    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)
    if df.height == 0:
        logger.warning("Year %d: bronze file %s is empty, skipping", year, path.name)
        return None
    logger.info(
        "Processing %s as %s (year %d, %d rows)", path.name, era, year, df.height
    )

    if era == "wide_v1_2007_2008":
        return _transform_wide_v1(df, year, manifest)
    if era == "wide_v2_2004_2010":
        return _transform_wide_v2(df, year, manifest)
    return _transform_tidy(df, year, manifest, era)


# =============================================================================
# §4b mask
# =============================================================================


def _null_corrupt_2012_num_students(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """NULL `num_students` for all 2012 rows (§4b corrupt source values).

    The 2012 bronze `Total Enrolled` is inflated ~17x at every detail level
    (state row 27,864,309 vs ~1.63M in 2011 / ~1.66M in 2013; the state's
    K-12 enrollment cannot exceed its population). The values are impossible,
    so they are NULLed rather than served; `num_retained` for 2012 is
    internally consistent (race/gender sums match) and is preserved.
    """
    mask = (pl.col("year") == 2012) & pl.col("num_students").is_not_null()
    count = df.filter(mask).height
    if count:
        df = df.with_columns(
            pl.when(pl.col("year") == 2012)
            .then(None)
            .otherwise(pl.col("num_students"))
            .alias("num_students")
        )
        manifest.record_masked(
            column="num_students",
            count=count,
            reason=(
                "2012 bronze Total Enrolled corrupt (inflated ~17x at every "
                "detail level; state row 27,864,309 vs ~1.65M expected)"
            ),
            years=[2012],
        )
    return df


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for retained_students."""
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
    # mean an alias/reclassification bug and must raise, not be deduped away.
    # (No demographic collisions exist: 8 bronze labels + synthetic `all`
    # map to 9 distinct canonical keys in every era, so
    # aggregate_demographic_collisions is not needed.)
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: years never overlap across files and the bronze grain is
    # unique within every file after the 2010 bronze-level dedup, so no
    # duplicates are expected; prefer the row with a reported (non-null,
    # larger) num_retained over a suppressed placeholder as the safety net.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code", "demographic"],
        district_keys=["year", "district_code", "demographic"],
        state_keys=["year", "demographic"],
        sort_col="num_retained",
    )

    # 4. Geography nulling (shared domain rules), then the §4b mask.
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )
    combined = _null_corrupt_2012_num_students(combined, manifest)

    # Pre-export sanity. num_students is structurally NULL for 2004-2010
    # (no enrollment in the wide eras), for 2012 (§4b mask), and for every
    # non-`all` row — the spike check will warn; expected and documented.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning(
            "NULL-rate spikes (expected for num_students): %s", spike_result.details
        )
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

    The column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level`` — the contract properties (and the validator's schema
    check) follow it.
    """
    race_list = ", ".join(f"'{k}'" for k in RACE_BUCKET_KEYS)
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Georgia Office of Student Achievement (GOSA) Retained K-12 "
            "dataset. For every Georgia public school, school district, and "
            "the state as a whole, reports the total number of students "
            "retained (held back) in grades K-12 during the school year, "
            "the total K-12 enrollment (2011 onward only), and a "
            "demographic breakdown of the retained population — counts and "
            "shares of retained by race and gender. The race axis carries "
            "six canonical codes (`native_american`, "
            "`asian_pacific_islander` — the bronze `Asian`/`Asians` label "
            "is a combined Asian/Pacific Islander bucket, with no separate "
            "Pacific Islander row — `black`, `hispanic`, `multiracial`, "
            "`white`); gender is `male`/`female`. Coverage spans the "
            "2003-04 school year (filename year 2004) through the 2023-24 "
            "school year (filename year 2024) — 21 files."
        ),
        title="Retained (Held-Back) K-12 Students",
        summary=(
            "Students held back a grade in Georgia public schools, with "
            "counts and the race/gender makeup of the retained group, by "
            "school and district, 2004-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Ending calendar year of the school year (2024 = "
                    "2023-2024). Sourced from the bronze `School Year` / "
                    "`School_Year` column for 2011-2024 (cross-checked "
                    "against the filename); from the filename for 2004-2010 "
                    "(no year column in those eras)."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "3-digit GOSA district code (zero-padded) for standard "
                    "districts; 7-digit code for state charter / state "
                    "school networks. NULL for state-level aggregate rows. "
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
                    "schools dimension (composite key with district_code)."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "black",
                "validValues": DEMOGRAPHIC_VALUES,
                "short_description": (
                    "Student subgroup the row covers (race or gender); 'all' "
                    "is the whole retained group. Race uses the combined "
                    "asian_pacific_islander bucket."
                ),
                "description": (
                    "Canonical demographic code (FK to demographics "
                    "dimension). `all` is the overall retained cohort; race "
                    "uses the combined `asian_pacific_islander` bucket "
                    "(pre-1997 OMB convention: the six race-bucket retained "
                    "counts sum exactly to the total retained at the state "
                    "row in every year, so Pacific Islanders are folded in, "
                    "never published separately); gender is `male`/"
                    "`female`. Race values are mutually exclusive with each "
                    "other, as are gender values; `all` overlaps both axes."
                ),
            },
            {
                "name": "num_retained",
                "type": "int64",
                "metric_component": "numerator",
                "unit": "count",
                "example": 13,
                "null_meaning": (
                    "Suppressed by GOSA (cell below the privacy reporting "
                    "threshold; `TFS` / `Too Few Students` markers, plus "
                    "blank cells in 2009)."
                ),
                "description": (
                    "Number of K-12 students in this demographic at this "
                    "entity who were retained (held back) during the school "
                    "year. For `demographic = all`, the total retained "
                    "count. NULL when suppressed."
                ),
            },
            {
                "name": "num_students",
                "type": "int64",
                "metric_component": "denominator",
                "unit": "count",
                "example": 3237,
                "null_meaning": (
                    "Enrollment not published for this cell: every "
                    "non-`all` demographic row (no per-demographic "
                    "enrollment exists), every row in 2004-2010 (the "
                    "wide-format bronze publishes no enrollment column) and "
                    "in 2012 (corrupt source enrollment, NULLed per §4b), "
                    "plus 8 2016 `all` rows whose source enrollment was "
                    "unpublished. NOT a suppression marker."
                ),
                "description": (
                    "Total K-12 enrollment at this entity. Populated only "
                    "on `demographic = all` rows in 2011 and 2013-2024. "
                    "NULL for every non-`all` row (bronze publishes no "
                    "per-demographic enrollment) and for every row in "
                    "2004-2010 (the wide-era bronze publishes no enrollment "
                    "at all — its total columns are retained counts). 2012 "
                    "is fully NULL: the 2012 bronze `Total Enrolled` is "
                    "corrupt (inflated ~17x at every detail level, state "
                    "row 27,864,309 vs ~1.65M expected) and is NULLed per "
                    "the known-source-defect rule; 2012 `num_retained` is "
                    "internally consistent and preserved. With "
                    "`num_retained` on `all` rows this yields an overall "
                    "retention rate."
                ),
            },
            {
                "name": "pct_of_retained_cohort",
                "type": "float64",
                "key_metric": True,
                "unit": "proportion",
                "example": 0.22,
                "short_description": (
                    "Share of this entity's retained students who are in this "
                    "demographic, on a 0-1 scale; a makeup share, NOT a "
                    "retention rate, and NULL on the 'all' row."
                ),
                "null_meaning": (
                    "NULL on `demographic = all` rows (the share is 100%% "
                    "by definition and not emitted) and when suppressed."
                ),
                "description": (
                    "Share of the entity's total retained cohort who belong "
                    "to this demographic, 0-1 scale (bronze 0-100 divided "
                    "by 100; whole-percent precision in 2011-2024). NOT a "
                    "within-demographic retention rate. In 2009 the "
                    "published White and Multiracial percent columns are "
                    "corrupt (both repeat the Male share); for those two "
                    "demographics in 2009 the share is derived as "
                    "num_retained / total retained from the internally "
                    "consistent counts instead."
                ),
            },
        ],
        source="Governor's Office of Student Achievement (GOSA)",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        limitations=(
            "`num_students` (total K-12 enrollment) is available only on "
            "`demographic = all` rows for 2011 and 2013-2024. It is NULL "
            "for every non-`all` demographic row (bronze has no "
            "per-demographic enrollment), for every row in 2004-2010 (the "
            "wide-format bronze publishes no enrollment column), and for "
            "all of 2012 (corrupt bronze `Total Enrolled`, inflated ~17x, "
            "is NULLed); 8 2016 `all` rows are also NULL where source "
            "enrollment was unpublished. An overall retention rate "
            "(`num_retained` / `num_students`) is therefore computable "
            "only on `demographic = all` rows in 2011 and 2013-2024. "
            "`pct_of_retained_cohort` is a SHARE of the total retained "
            "cohort that belongs to each demographic (it sums toward 1.0 "
            "across race demographics and across gender demographics "
            "within an entity), NOT a within-demographic retention rate; "
            "it is NULL on `demographic = all` rows (100%% by definition). "
            "Suppressed cells (cohort below the privacy threshold) null "
            "`num_retained` and `pct_of_retained_cohort`."
        ),
        notes=[
            (
                "Percentage scale: `pct_of_retained_cohort` is 0-1 decimal "
                "(bronze 0-100 divided by 100). The tidy-era source rounds "
                "shares to whole percents, so race/gender shares within an "
                "entity sum to 0.99-1.01 in 2011-2024."
            ),
            (
                "The wide-era (2004-2010) total columns — `Retained_NN` "
                "(2007-2008) and `Retained Total Students` (2004-2006, "
                "2009-2010) — are TOTAL RETAINED counts, not enrollment: at "
                "every state row their value equals both the race-bucket "
                "sum and the male+female sum of retained counts and is "
                "~3.5%% of Georgia's ~1.6M K-12 enrollment."
            ),
            (
                "Suppression markers by era, all NULL in gold: `TFS` "
                "(2021-2024), `Too Few Students` (2011-2020 and 2010), "
                "literal `NULL` strings (5-8 rows each in 2005-2007), true "
                "blank cells (2009, plus 1-2 strays in 2010). 2004 and "
                "2008 publish no suppressed cells."
            ),
            (
                "Asian/Pacific Islander is the combined pre-1997 OMB bucket "
                "(`asian_pacific_islander`): the source has exactly six "
                "race buckets and their retained counts sum exactly to the "
                "total retained wherever all six are published (0 "
                "mismatches across all 21 files), so Pacific Islanders are "
                "folded in rather than dropped. The split asian / "
                "pacific_islander keys are never emitted."
            ),
            (
                "2009 source defect, repaired: `Retained Percent White` and "
                "`Retained Percent Multiracial` are corrupt (both repeat "
                "the Male share; 656 White and 57 Multiracial rows off by "
                ">1pp). The transform derives those two shares from the "
                "internally consistent counts (count / total retained)."
            ),
            (
                "2012 source defect, masked: `Total Enrolled` is inflated "
                "~17x at every detail level; `num_students` is NULLed for "
                "all 2012 rows (num_retained preserved)."
            ),
            (
                "2010 source defects: one malformed export row "
                "(`SysSchoolid=' Few Students'`, all metrics NULL) is "
                "dropped; 53 duplicated SysSchoolid keys (52 identical "
                "pairs, 1 incomplete twin) are deduplicated keeping the "
                "most complete row per key."
            ),
            (
                "2022 source defect, repaired: two state-charter district "
                "aggregate rows (districts 7830627, 7830636) are mislabeled "
                "School while carrying the School Code=ALL sentinel; "
                "reclassified to district detail."
            ),
            (
                "Redundant bronze columns never selected: wide_v1's "
                "`Retained_N{A,B,F,H,M,U,W}` are copies of `Retained_NN`; "
                "wide_v2's no-'Total' `Retained {Demo}` columns (2004-2006, "
                "2009) are copies of `Retained Total Students`; 2009 also "
                "carries two stray unnamed Excel-artifact columns."
            ),
            (
                "State-level rows have NULL district_code and school_code; "
                "district rows have NULL school_code. Bronze sentinels "
                "(`ALL`, `ALL:ALL`, `All Column Values`) become NULL. Names "
                "and `Grades Served` live in the dimension tables, not in "
                "this fact table."
            ),
        ],
        quality_checks=[
            {
                "name": "num_retained_le_num_students",
                "description": (
                    "num_retained never exceeds num_students where both "
                    "are populated (retained students are a subset of "
                    "enrollment). Verified on bronze: zero violations in "
                    "every tidy-era year."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE num_retained IS "
                    "NOT NULL AND num_students IS NOT NULL AND "
                    "num_retained > num_students"
                ),
                "mustBe": 0,
            },
            {
                "name": "pct_of_retained_cohort_null_for_all",
                "description": (
                    "pct_of_retained_cohort is NULL on `demographic = all` "
                    "rows (the share is 100%% by definition and not "
                    "emitted)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE demographic = "
                    "'all' AND pct_of_retained_cohort IS NOT NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "num_students_only_on_all_rows_in_published_years",
                "description": (
                    "num_students is structurally NULL outside `demographic "
                    "= all` rows in 2011 and 2013-2024: the bronze publishes "
                    "no per-demographic enrollment, no enrollment at all for "
                    "2004-2010, and corrupt (masked) enrollment for 2012."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE num_students IS "
                    "NOT NULL AND (demographic <> 'all' OR year <= 2010 OR "
                    "year = 2012)"
                ),
                "mustBe": 0,
            },
            {
                "name": "race_partition_sums_to_total",
                "description": (
                    "The six mutually exclusive race buckets partition the "
                    "retained cohort: wherever all six race num_retaineds "
                    "and the `all` total are published for an entity, the "
                    "race sum equals the total exactly (the §5b math test; "
                    "verified with 0 mismatches across all 21 bronze "
                    "files). NULL-guarded: suppressed cells exempt the "
                    "entity."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, school_code, "
                    "MAX(CASE WHEN demographic = 'all' THEN num_retained "
                    "END) AS total, "
                    "SUM(CASE WHEN demographic <> 'all' THEN num_retained "
                    "END) AS race_sum, "
                    "COUNT(CASE WHEN demographic <> 'all' AND "
                    "num_retained IS NOT NULL THEN 1 END) AS n_published "
                    f"FROM {{object}} WHERE demographic IN ('all', {race_list}) "
                    "GROUP BY year, district_code, school_code"
                    ") WHERE total IS NOT NULL AND n_published = 6 "
                    "AND race_sum <> total"
                ),
                "mustBe": 0,
            },
            {
                "name": "gender_partition_sums_to_total",
                "description": (
                    "male + female num_retained equals the `all` total "
                    "wherever all three are published for an entity "
                    "(verified with 0 mismatches across all 21 bronze "
                    "files). NULL-guarded: suppressed cells exempt the "
                    "entity."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, school_code, "
                    "MAX(CASE WHEN demographic = 'all' THEN num_retained "
                    "END) AS total, "
                    "SUM(CASE WHEN demographic <> 'all' THEN num_retained "
                    "END) AS gender_sum, "
                    "COUNT(CASE WHEN demographic <> 'all' AND "
                    "num_retained IS NOT NULL THEN 1 END) AS n_published "
                    "FROM {object} WHERE demographic IN ('all', 'male', "
                    "'female') "
                    "GROUP BY year, district_code, school_code"
                    ") WHERE total IS NOT NULL AND n_published = 2 "
                    "AND gender_sum <> total"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
