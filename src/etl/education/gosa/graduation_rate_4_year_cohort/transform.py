"""Transform bronze graduation_rate_4_year_cohort files into gold fact tables.

Source: Governor's Office of Student Achievement (GOSA) — Four-Year Cohort
Graduation Rate, 2004-2024 (21 bronze files, one school year each). For every
Georgia public school, plus official district and state rollups, reports the
federal four-year adjusted-cohort graduation rate (``graduation_rate``), the
number of graduates (``num_graduates``), and the adjusted cohort size
(``num_cohort``) by demographic subgroup.

Design decisions (from bronze-data-structure.md and data-cleaning-standards;
every invariant below was re-verified against this topic's 21 bronze files):

- **Six bronze eras collapse to three transform paths.**
    * wide_v1 (2004-2006): wide CSV/XLS with human-readable headers
      ("Graduation Rate Asian", "Number Taken Asian", "Approximate Class
      Size Asian", ...). 15 demographic triplets x 3 metrics = 45 metric
      columns + 2 ID columns. The class-size column for Native American
      drops the word "Native" ("Approximate Class Size Amer/Alaskan
      Native") — a bronze column-name inconsistency handled by listing the
      literal name in the triplet map. 2005/2006 carry ``.csv`` extensions
      but are XLS binaries — ``read_bronze_file`` detects this via magic
      bytes and routes to the Excel reader transparently.
    * wide_v2 (2007-2010): wide XLS with cryptic ``GradRate_{P|N|S}{code}``
      columns (15 demographic suffix codes x 3 metrics). The name column is
      misspelled ``SchoolNme`` in bronze.
    * tidy (2011-2024): long format with explicit ``LABEL_LVL_1_DESC``.
      2023-2024 add a leading constant ``#RPT_NAME`` column ("Graduation
      Rate"), guarded and dropped. ``TOTAL_COUNT`` (the cohort denominator)
      exists in 2011 and 2017-2024 but is ABSENT in 2012-2016.
- **Asian / Pacific Islander is the combined bucket in every year (§5b).**
  The tidy era publishes the explicit label "Asian/Pacific Islander". The
  wide eras publish bare "Asian" — the §5b math test proves it is the same
  pre-1997 OMB combined bucket: at the state row the six race-bucket
  graduate counts AND cohort sizes sum EXACTLY to the All Students totals in
  every year 2004-2010 (e.g. 2005: race N 67,547 = all N; race S 97,359 =
  all S), so Pacific Islanders are folded in, not dropped. The wide-era
  triplet maps therefore relabel bare "Asian" to "Asian/Pacific Islander"
  BEFORE ``normalize_demographic_column()`` runs (topic-local override; the
  global ``ASIAN`` alias is untouched). Never split, no synthesized rollups.
- **Suppression differs per era; markers become NULL, zeros stay.**
    * 2004-2009: literal zeros stand in for suppressed cells (e.g. rate 0.0
      / 0 graduates / cohort 1) and are INDISTINGUISHABLE from real zeros —
      passed through to gold as published and documented in the contract.
      Measured per file: 2007/2008/2009 contain ZERO "Too few Students"
      cells, zero blanks, and zero NULLs (1,818 / 1,805 / 1,774 zero-rate
      cells instead) — the marker era starts in 2010, not 2007 as the
      structure doc originally claimed.
    * 2010 only: literal "Too few Students" strings (9,573 cells = 3,191
      suppressed triplets) — survive the read (the marker's exact casing is
      not in SUPPRESSION_VALUES) and are nulled by ``strict=False`` casts.
    * 2011-2020: blank cells (NULL at read time).
    * 2021-2024: literal "TFS" — nulled at read time by ``read_bronze_file``.
  From 2011 onward every published count is >= 10 (GOSA's n=10 reporting
  threshold; verified per file) — pinned as a quality check. 2023-2024
  additionally publish TOTAL_COUNT for 369/339 rows whose rate and graduate
  count are TFS-suppressed (partial suppression: num_cohort present, other
  metrics NULL; mostly school-level — 295/74 school/district in 2023,
  271/68 in 2024) — so only num_graduates<->graduation_rate are
  co-suppressed (verified: zero rows in any year where exactly one of the
  two is missing).
- **2004-2010 predate the federal ACGR methodology.** Georgia first
  reported the federal four-year adjusted-cohort graduation rate (ACGR) in
  2011; the 2004-2010 figures are the state's earlier leaver-based rate
  (the wide-era denominator is literally named "Approximate Class Size").
  The state all-students rate breaks 0.808 (2010) -> 0.6747 (2011) at
  exactly that boundary — a methodology break, not a real decline. Values
  are preserved as published; the contract carries a do-not-trend caveat.
- **num_cohort is NULL for 2012-2016 (Era 4).** The source does not publish
  TOTAL_COUNT in those years. We do NOT derive it from
  ``round(num_graduates / graduation_rate)`` — the published rate has
  rounding error — so gold keeps NULL and consumers choose their own
  estimate. Pinned as a structural quality check.
- **2010 migrant source defect — preserved per §4b (extreme-but-conceivable).**
  The only rate/count/cohort mismatches in any year are the three
  non-suppressed migrant rows of 2010: the state aggregate (rate 65.5%%,
  N=110, S=110) and the Colquitt County district + school rows (rate 69.6%%,
  N=23, S=23). N=S yet rate != 100%% — internally inconsistent, but every
  value is individually possible, so the rows are preserved exactly as
  published (no §4b mask) and documented in the contract. The
  rate-reconciliation quality check excludes (year=2010 AND
  demographic='migrant'); everywhere else the max deviation between the
  published rate and N/S is 0.0005 (bronze rounds the percent to 1 decimal),
  enforced with a 0.001 tolerance.
- **No §4b masks.** Full scan of all 21 files: no negative counts, no rates
  outside [0, 100], zero num_graduates > num_cohort violations. The 2010
  migrant rows above are the only anomaly and are conceivable-and-preserved.
- **Wide-era duplicate-row twins resolved by dedup.** 2004 has 50 duplicate
  SysSchoolIDs (an artifact of the malformed source export) and 2009 has 2
  (renamed single-school charters: 768:ALL Ivy Prep, 770:ALL Scholars
  Academy, one twin lacking the name). Verified: after casting, every twin
  pair is VALUE-IDENTICAL on all 45 metrics (the one 2004 group that differs
  pre-cast — 751:194 Martha Puckett Middle School — differs only by
  empty-string vs NULL cells, identical after ``strict=False`` casts). The
  collision guard therefore passes (no divergent metrics) and
  ``deduplicate_by_detail_level`` drops one twin per pair; the removal is
  recorded per year via ``manifest.record_filtered``.
- **Malformed 2004 row dropped.** 2004.csv contains exactly one corrupt row
  (``SysSchoolID='0"'``, ``SchoolName='10'``) lacking the ``:`` delimiter;
  it cannot be assigned a detail level and is dropped + recorded. Read-loss
  accounting shows raw=parsed=2271 for 2004 (polars salvages the malformed
  chunk; the corrupt row is the in-band residue).
- **Detail levels.** Wide eras derive from the compound SysSchoolID
  (``ALL:ALL`` -> state; ``{district}:ALL`` -> district; else school). Every
  wide year also carries ``799:ALL`` ("State Schools") — a real district
  code for the state-school virtual district, kept as a district-level row;
  only ``ALL:ALL`` becomes the state row. The tidy era uses
  ``DETAIL_LVL_DESC``; as a defensive guard any School-labeled row carrying
  the ``INSTN_NUMBER=ALL`` aggregate sentinel is reclassified to district
  (verified: zero such rows exist in this topic's bronze — the guard exists
  because sibling GOSA topics have the defect).
- **Demographic set varies by year (pinned by quality checks).** 2004-2017
  publish 15 subgroups; 2018 adds Active Duty, Foster, and Homeless (18);
  2021 drops Limited English Proficient (17 — returns in 2022). Note the
  bronze-data-structure doc's "2020 onwards" claim for the expansion was
  measured wrong — the 18-label set starts in the 2018 file.
- **Dedup tie-break.** Years never overlap across files and the tidy-era
  bronze grain is unique per file (verified: zero duplicate key groups in
  any tidy year), so the only duplicates are the value-identical wide-era
  twins above. ``sort_col="num_cohort"`` is the documented safety net:
  prefer the row with a reported (non-null, larger) cohort over a
  placeholder; for identical twins the winner is value-irrelevant.
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

TOPIC = "graduation_rate_4_year_cohort"
BRONZE_DIR = Path("data/bronze/education/gosa/graduation_rate_4_year_cohort")
GOLD_DIR = Path("data/gold/education/graduation_rate_4_year_cohort")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Aggregate-row sentinel: wide eras use it inside the compound SysSchoolID
# ("ALL:ALL", "601:ALL"); the tidy era uses it in SCHOOL_DSTRCT_CD (state
# rows) and INSTN_NUMBER (state + district rows). Becomes NULL in gold.
ALL_SENTINEL = "ALL"

# Constant prefix on every tidy-era LABEL_LVL_1_DESC value ("Grad Rate -ALL
# Students"); stripped before demographic normalization.
TIDY_DEMOGRAPHIC_PREFIX = "Grad Rate -"

# Era 6's constant #RPT_NAME value — guarded so foreign report rows can never
# silently enter this topic.
ERA6_REPORT_NAME = "Graduation Rate"

DETAIL_LEVEL_MAP: dict[str, str] = {
    "State": "state",
    "District": "district",
    "School": "school",
}

# Wide-era v1 (2004-2006) column triplets: demographic label -> (rate,
# graduates, cohort) bronze column names. The label is what
# normalize_demographic_column() later maps via DEMOGRAPHIC_ALIASES.
# Bare bronze "Asian" is relabeled "Asian/Pacific Islander" here — the §5b
# math test proves the combined bucket (race sums equal the All Students
# totals exactly at the state row in 2004-2006; see module docstring).
# "Approximate Class Size Amer/Alaskan Native" drops the word "Native" in
# bronze — the literal name is listed on purpose, not a typo.
WIDE_V1_DEMO_TRIPLETS: dict[str, tuple[str, str, str]] = {
    "All Students": (
        "Graduation Rate All Students",
        "Number Taken All Students",
        "Approximate Class Size All Students",
    ),
    "Asian/Pacific Islander": (
        "Graduation Rate Asian",
        "Number Taken Asian",
        "Approximate Class Size Asian",
    ),
    "Black": (
        "Graduation Rate Black",
        "Number Taken Black",
        "Approximate Class Size Black",
    ),
    "Hispanic": (
        "Graduation Rate Hispanic",
        "Number Taken Hispanic",
        "Approximate Class Size Hispanic",
    ),
    "Native Amer/Alaskan Native": (
        "Graduation Rate Native Amer/Alaskan Native",
        "Number Taken Native Amer/Alaskan Native",
        "Approximate Class Size Amer/Alaskan Native",
    ),
    "White": (
        "Graduation Rate White",
        "Number Taken White",
        "Approximate Class Size White",
    ),
    "Multiracial": (
        "Graduation Rate Multiracial",
        "Number Taken Multiracial",
        "Approximate Class Size Multiracial",
    ),
    "Male": (
        "Graduation Rate Male",
        "Number Taken Male",
        "Approximate Class Size Male",
    ),
    "Female": (
        "Graduation Rate Female",
        "Number Taken Female",
        "Approximate Class Size Female",
    ),
    "Students with Disabilities": (
        "Graduation Rate Students with Disabilities",
        "Number Taken Students with Disabilities",
        "Approximate Class Size Students with Disabilities",
    ),
    "Students without Disabilities": (
        "Graduation Rate Students without Disabilities",
        "Number Taken Students without Disabilities",
        "Approximate Class Size Students without Disabilities",
    ),
    "Limited English Proficient": (
        "Graduation Rate Limited English Proficient",
        "Number Taken Limited English Proficient",
        "Approximate Class Size Limited English Proficient",
    ),
    "Economically Disadvantaged": (
        "Graduation Rate Economically Disadvantaged",
        "Number Taken Economically Disadvantaged",
        "Approximate Class Size Economically Disadvantaged",
    ),
    "Not Economically Disadv": (
        "Graduation Rate Not Economically Disadv",
        "Number Taken Not Economically Disadv",
        "Approximate Class Size Not Economically Disadv",
    ),
    "Migrant": (
        "Graduation Rate Migrant",
        "Number Taken Migrant",
        "Approximate Class Size Migrant",
    ),
}

# Wide-era v2 (2007-2010) demographic suffix codes -> labels. Each suffix S
# yields the triplet GradRate_P{S} (rate %), GradRate_N{S} (graduates),
# GradRate_S{S} (cohort). Suffix semantics verified against Era 1 values in
# the structure doc: u = multiracial, RL = "regular learners" (non-SWD).
# Bare "Asian" (suffix a) relabeled to the combined bucket exactly as in
# wide_v1 — the §5b math test holds in 2007-2010 too (see module docstring).
WIDE_V2_DEMO_SUFFIXES: dict[str, str] = {
    "0": "All Students",
    "a": "Asian/Pacific Islander",
    "b": "Black",
    "h": "Hispanic",
    "n": "Native Amer/Alaskan Native",
    "w": "White",
    "u": "Multiracial",
    "m": "Male",
    "f": "Female",
    "S": "Students With Disabilities",
    "RL": "Students Without Disabilities",
    "L": "Limited English Proficient",
    "_ed": "Economically Disadvantaged",
    "_ned": "Not Economically Disadvantaged",
    "_mig": "Migrant",
}

WIDE_V2_DEMO_TRIPLETS: dict[str, tuple[str, str, str]] = {
    label: (f"GradRate_P{sfx}", f"GradRate_N{sfx}", f"GradRate_S{sfx}")
    for sfx, label in WIDE_V2_DEMO_SUFFIXES.items()
}

# Era-detection signatures, most-specific first (tidy era 6 is a strict
# superset of eras 3-5; the wide eras disambiguate on their unique headers).
ERA_SIGNATURES: dict[str, list[str]] = {
    "tidy_2023_2024": [
        "#RPT_NAME",
        "LONG_SCHOOL_YEAR",
        "DETAIL_LVL_DESC",
        "LABEL_LVL_1_DESC",
        "PROGRAM_TOTAL",
        "PROGRAM_PERCENT",
    ],
    "tidy_2011_2022": [
        "LONG_SCHOOL_YEAR",
        "DETAIL_LVL_DESC",
        "LABEL_LVL_1_DESC",
        "PROGRAM_TOTAL",
        "PROGRAM_PERCENT",
    ],
    "wide_v2_2007_2010": ["SysSchoolID", "SchoolNme", "GradRate_P0"],
    "wide_v1_2004_2006": [
        "SysSchoolID",
        "SchoolName",
        "Graduation Rate All Students",
    ],
}

# Tidy-era bronze columns every file must carry (rename-coverage guard).
REQUIRED_TIDY_COLUMNS: list[str] = [
    "LONG_SCHOOL_YEAR",
    "DETAIL_LVL_DESC",
    "SCHOOL_DSTRCT_CD",
    "INSTN_NUMBER",
    "LABEL_LVL_1_DESC",
    "PROGRAM_TOTAL",
    "PROGRAM_PERCENT",
]

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "num_graduates",
    "num_cohort",
    "graduation_rate",
    "detail_level",
]

# Int64 counts: the state-level cohort exceeds 130,000 students.
TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "demographic": pl.Utf8,
    "num_graduates": pl.Int64,
    "num_cohort": pl.Int64,
    "graduation_rate": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = ["num_graduates", "num_cohort", "graduation_rate"]

NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "detail_level",
]

# The 18 canonical demographic keys this topic publishes (15 in 2004-2017;
# active_duty / foster_care / homeless from 2018; english_learners absent in
# 2021 only). Used for the contract enum and the year-scoped quality checks.
DEMOGRAPHIC_VALUES: list[str] = sorted(
    [
        "all",
        "active_duty",
        "asian_pacific_islander",
        "black",
        "economically_disadvantaged",
        "english_learners",
        "female",
        "foster_care",
        "hispanic",
        "homeless",
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
# Their state-level graduate counts sum exactly to the `all` total in every
# year 2004-2024 — the §5b math test, enforced as a quality check.
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


def _require_columns(df: pl.DataFrame, required: list[str], label: str) -> None:
    """Raise if any expected bronze column is absent (rename-coverage guard).

    An unmatched source column would silently become NULL in gold — the most
    common data-loss bug — so missing columns fail loudly instead.
    """
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"{label}: expected bronze column(s) missing: {missing}. "
            f"Present: {df.columns}"
        )


def _record_demographics(df: pl.DataFrame, manifest: TransformManifest) -> None:
    """Record the demographic recoding using the effective alias slice.

    Records only the DEMOGRAPHIC_ALIASES entries this file's labels actually
    hit (keeps map_used reviewable) while preserving the unmapped guard.
    """
    observed_upper = {
        str(v).strip().upper()
        for v in df["_demographic_raw"].drop_nulls().unique().to_list()
    }
    effective_map = {
        k: v for k, v in DEMOGRAPHIC_ALIASES.items() if k in observed_upper
    }
    manifest.record_categorical(
        column="demographic",
        map_dict=effective_map,
        bronze_series=df["_demographic_raw"],
        gold_series=df["demographic"],
    )


# =============================================================================
# Wide eras (2004-2010): one row per entity, demographic triplets in columns
# =============================================================================


def _transform_wide(
    df: pl.DataFrame,
    year: int,
    manifest: TransformManifest,
    triplets: dict[str, tuple[str, str, str]],
    name_col: str,
) -> pl.DataFrame:
    """Unpivot a wide-era bronze file (either wide era) into tidy gold rows.

    Both wide eras share the same shape — compound ``SysSchoolID`` plus one
    (rate, graduates, cohort) column triplet per demographic — and differ
    only in the triplet column names, so one function serves both.

    Args:
        df: Bronze DataFrame (all-string columns).
        year: Calendar year from the filename (wide eras have no year column).
        manifest: Manifest for filter/categorical recording.

    Returns:
        Gold-shaped DataFrame with STANDARD_COLUMNS.
    """
    # Rename-coverage guard: every triplet column must exist.
    expected = [c for triplet in triplets.values() for c in triplet]
    _require_columns(df, expected + ["SysSchoolID", name_col], f"wide {year}")

    # Drop corrupt rows lacking the `{district}:{school}` delimiter. Known
    # case: 2004.csv has exactly one (SysSchoolID='0"') from a malformed
    # source export; it cannot be assigned a detail level.
    bad = df.filter(~pl.col("SysSchoolID").str.contains(":"))
    if bad.height:
        logger.warning(
            "Year %d: dropping %d malformed bronze row(s) with SysSchoolID "
            "lacking ':' (sample: %s)",
            year,
            bad.height,
            bad["SysSchoolID"].head(5).to_list(),
        )
        manifest.record_filtered(year, bad.height, "malformed_sysschoolid_row")
        df = df.filter(pl.col("SysSchoolID").str.contains(":"))

    # Unpivot: one sub-frame per demographic triplet, then vertical concat.
    # Rate: 0-100 percent -> 0-1 proportion (§4). Counts: direct Int64 cast
    # (verified: zero decimal-formatted count cells in any wide file);
    # strict=False nulls suppression residue ("Too few Students", '').
    frames: list[pl.DataFrame] = []
    for label, (rate_col, num_col, denom_col) in triplets.items():
        frames.append(
            df.select(
                pl.col("SysSchoolID"),
                (pl.col(rate_col).cast(pl.Float64, strict=False) / 100.0).alias(
                    "graduation_rate"
                ),
                pl.col(num_col).cast(pl.Int64, strict=False).alias("num_graduates"),
                pl.col(denom_col).cast(pl.Int64, strict=False).alias("num_cohort"),
                pl.lit(label).alias("_demographic_raw"),
            )
        )
    melted = pl.concat(frames, how="vertical")

    # Decompose the compound ID and derive the detail level:
    #   ALL:ALL -> state; {district}:ALL -> district; else school.
    # 799:ALL ("State Schools") is a real district code for the state-school
    # virtual district and stays a district-level row in every wide year;
    # only ALL:ALL is the state row (structure doc consideration 10).
    melted = melted.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.col("SysSchoolID").str.split_exact(":", 1).alias("_id"),
    ).with_columns(
        pl.col("_id").struct.field("field_0").alias("_dist_raw"),
        pl.col("_id").struct.field("field_1").alias("_sch_raw"),
    )
    melted = melted.with_columns(
        pl.when(
            (pl.col("_dist_raw") == ALL_SENTINEL) & (pl.col("_sch_raw") == ALL_SENTINEL)
        )
        .then(pl.lit("state"))
        .when(pl.col("_sch_raw") == ALL_SENTINEL)
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .alias("detail_level"),
        # ALL sentinel -> NULL; zfill aligns wide-era unpadded school codes
        # ("103") with the tidy-era 4-digit format ("0103"). Never truncate.
        pl.when(pl.col("_dist_raw") == ALL_SENTINEL)
        .then(None)
        .otherwise(pl.col("_dist_raw").str.zfill(3))
        .alias("district_code"),
        pl.when(pl.col("_sch_raw") == ALL_SENTINEL)
        .then(None)
        .otherwise(pl.col("_sch_raw").str.zfill(4))
        .alias("school_code"),
    )

    # Demographics: triplet labels (with the §5b Asian relabel already
    # applied in the map) through the shared canonical path.
    melted = melted.with_columns(
        normalize_demographic_column("_demographic_raw").alias("demographic")
    )
    _record_demographics(melted, manifest)

    return melted.select(STANDARD_COLUMNS)


# =============================================================================
# Tidy era (2011-2024): long format with explicit LABEL_LVL_1_DESC
# =============================================================================


def _validate_era6_constants(df: pl.DataFrame, year: int) -> None:
    """Hard-stop if era 6's constant #RPT_NAME column carries other values.

    Anything other than "Graduation Rate" means foreign report rows are mixed
    into this topic's bronze and must be analyzed, not silently kept.
    """
    rpt_names = df["#RPT_NAME"].drop_nulls().unique().to_list()
    if rpt_names != [ERA6_REPORT_NAME]:
        raise ValueError(f"tidy {year}: unexpected #RPT_NAME values {rpt_names}")


def _transform_tidy(
    df: pl.DataFrame,
    year: int,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Transform a tidy-era (2011-2024) bronze file into gold rows.

    Args:
        df: Bronze DataFrame (all-string columns).
        year: Ending calendar year (already cross-checked against filename).
        manifest: Manifest for categorical/reclassification recording.

    Returns:
        Gold-shaped DataFrame. ``num_cohort`` is NULL for 2012-2016, whose
        bronze does not publish TOTAL_COUNT.
    """
    _require_columns(df, REQUIRED_TIDY_COLUMNS, f"tidy {year}")

    # Era 4 (2012-2016) does not publish the cohort denominator. Emit NULL
    # num_cohort rather than deriving an estimate from the rounded rate —
    # logged so a rename bug masquerading as an absent column is visible.
    has_total_count = "TOTAL_COUNT" in df.columns
    if not has_total_count:
        logger.info(
            "Year %d: bronze has no TOTAL_COUNT column (Era 4, 2012-2016) — "
            "num_cohort will be NULL for this year",
            year,
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

    # Defensive repair: a School-labeled row carrying the INSTN_NUMBER=ALL
    # aggregate sentinel is a district aggregate by definition. Verified:
    # zero such rows in this topic's bronze (sibling GOSA topics have the
    # defect, so the guard stays); recorded if it ever fires.
    mislabeled = (pl.col("detail_level") == "school") & (
        pl.col("INSTN_NUMBER").str.strip_chars() == ALL_SENTINEL
    )
    n_mislabeled = df.filter(mislabeled).height
    if n_mislabeled:
        manifest.record_reclassified(
            year, n_mislabeled, "school_labeled_aggregate_to_district"
        )
        df = df.with_columns(
            pl.when(mislabeled)
            .then(pl.lit("district"))
            .otherwise(pl.col("detail_level"))
            .alias("detail_level")
        )

    # Demographics: strip the constant "Grad Rate -" prefix, then normalize
    # via the shared canonical path. The tidy era's explicit "Asian/Pacific
    # Islander" label maps to the combined asian_pacific_islander bucket.
    df = df.with_columns(
        pl.col("LABEL_LVL_1_DESC")
        .str.strip_prefix(TIDY_DEMOGRAPHIC_PREFIX)
        .str.strip_chars()
        .alias("_demographic_raw")
    ).with_columns(
        normalize_demographic_column("_demographic_raw").alias("demographic")
    )
    _record_demographics(df, manifest)

    # Geography keys: ALL sentinels -> NULL; zfill(3) keeps 3-digit county
    # codes padded and passes 7-digit state-charter codes through unchanged
    # (never truncate); zfill(4) for school codes. Metrics: counts via
    # direct Int64 cast (verified: no decimal-formatted cells); the 0-100
    # source percent is divided by 100 onto the 0-1 proportion scale (§4).
    # TFS suppression literals (2021+) already arrived as NULL from
    # read_bronze_file; strict=False nulls any other residue.
    cohort_expr = (
        pl.col("TOTAL_COUNT").cast(pl.Int64, strict=False)
        if has_total_count
        else pl.lit(None).cast(pl.Int64)
    )
    df = df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.when(pl.col("SCHOOL_DSTRCT_CD") == ALL_SENTINEL)
        .then(None)
        .otherwise(pl.col("SCHOOL_DSTRCT_CD").str.zfill(3))
        .alias("district_code"),
        pl.when(pl.col("INSTN_NUMBER") == ALL_SENTINEL)
        .then(None)
        .otherwise(pl.col("INSTN_NUMBER").str.zfill(4))
        .alias("school_code"),
        pl.col("PROGRAM_TOTAL").cast(pl.Int64, strict=False).alias("num_graduates"),
        cohort_expr.alias("num_cohort"),
        (pl.col("PROGRAM_PERCENT").cast(pl.Float64, strict=False) / 100.0).alias(
            "graduation_rate"
        ),
    )

    return df.select(STANDARD_COLUMNS)


# =============================================================================
# File dispatcher
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read one bronze file, detect its era, and transform it to gold shape.

    Year resolution: tidy files carry exactly one LONG_SCHOOL_YEAR value
    whose ending year must agree with the filename year (a misnamed file
    cannot silently mislabel a whole year); wide files have no year column,
    so the filename year is authoritative.

    Args:
        path: Bronze file path.
        manifest: Manifest for read-loss / file / bronze-count / categorical
            recording.

    Returns:
        Gold-shaped DataFrame, or None for an empty bronze file.
    """
    # All-string read: geography codes keep leading zeros and the ALL
    # sentinels are never schema-inference casualties. Magic-byte detection
    # routes the XLS-mislabeled-as-.csv 2005/2006 files to the Excel reader.
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

    if era.startswith("tidy"):
        if era == "tidy_2023_2024":
            _validate_era6_constants(df, filename_year)
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
    if df.height == 0:
        logger.warning("Year %d: bronze file %s is empty, skipping", year, path.name)
        return None
    logger.info("Processing %s as %s (year %d)", path.name, era, year)

    if era == "wide_v1_2004_2006":
        return _transform_wide(df, year, manifest, WIDE_V1_DEMO_TRIPLETS, "SchoolName")
    if era == "wide_v2_2007_2010":
        return _transform_wide(df, year, manifest, WIDE_V2_DEMO_TRIPLETS, "SchoolNme")
    return _transform_tidy(df, year, manifest)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for graduation_rate_4_year_cohort."""
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
    # The wide-era twin rows (2004: 50 entities, 2009: 2) pass because they
    # are value-identical after casting (verified — see module docstring).
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: years never overlap across files and the tidy-era grain is
    # unique per file, so the only duplicates are the value-identical
    # wide-era twins; prefer the row with a reported (non-null, larger)
    # num_cohort over a placeholder as the documented safety net.
    pre_dedup = dict(
        combined.group_by("year").len().iter_rows()
    )  # year -> rows before dedup, for per-year removal accounting below
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code", "demographic"],
        district_keys=["year", "district_code", "demographic"],
        state_keys=["year", "demographic"],
        sort_col="num_cohort",
    )
    # Manifest artifact for the twin removals (2004: 750 rows = 50 twins x
    # 15 demographics; 2009: 30 rows = 2 twins x 15).
    for year, n_before in sorted(pre_dedup.items()):
        n_after = combined.filter(pl.col("year") == year).height
        if n_before > n_after:
            manifest.record_filtered(
                year, n_before - n_after, "duplicate_bronze_twin_rows_deduplicated"
            )

    # 4. Geography nulling (shared domain rules). No §4b masks: the full
    # bronze scan found no impossible values; the 2010 migrant inconsistency
    # is preserved per §4b extreme-but-conceivable (see module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. num_cohort is 100% NULL for 2012-2016 (Era 4 has
    # no denominator) — the spike check will warn on those years; documented.
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
    declaration order MUST match STANDARD_COLUMNS minus ``detail_level`` —
    the contract's properties (and the validator's schema check) follow it.
    """
    race_list = ", ".join(f"'{k}'" for k in RACE_BUCKET_KEYS)
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Four-year high-school graduation rate for Georgia public "
            "schools, with official district and state rollups, by "
            "demographic subgroup (race/ethnicity, gender, disability "
            "status, English proficiency, economic status, and special "
            "populations). Reports the graduation rate, the number of "
            "graduates, and the cohort size. Published by GOSA for school "
            "years 2003-04 through 2023-24. 2011 onward is the federal "
            "four-year adjusted-cohort graduation rate (ACGR); 2004-2010 "
            "predate Georgia's ACGR adoption and use the state's earlier "
            "leaver-based methodology — the two halves are not trend-"
            "comparable (see limitations). This is the long historical "
            "4-year series with demographic breakdowns; the sibling "
            "ccrpi_graduation_rate topic carries the GaDOE CCRPI release "
            "(2012 onward, 4- and 5-year rates with CCRPI target/flag "
            "context)."
        ),
        title="Four-Year Cohort Graduation Rate",
        summary=(
            "Share of the four-year high school cohort that graduated, by "
            "school, district, and state and demographic subgroup, "
            "2004-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Ending (spring) calendar year of the cohort's "
                    "graduating school year (2024 = the 2023-24 cohort). "
                    "Parsed from the source's LONG_SCHOOL_YEAR and "
                    "cross-checked against the filename for 2011-2024; from "
                    "the filename for 2004-2010 (no year column in those "
                    "eras)."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "GOSA district code (FK to districts dimension): "
                    "3-digit zero-padded county/city codes or 7-digit "
                    "state-charter codes. Code 799 is the state-school "
                    "virtual district ('State Schools'), published as a "
                    "district-level aggregate in 2004-2010. NULL on "
                    "state-level rows."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0103",
                "description": (
                    "GOSA school code, zero-padded to 4 characters "
                    "(composite FK to schools dimension with district_code; "
                    "not globally unique on its own). NULL on district- and "
                    "state-level rows."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "all",
                "validValues": DEMOGRAPHIC_VALUES,
                "short_description": (
                    "Student subgroup the row reports (race/ethnicity, "
                    "gender, disability, economic status, special "
                    "population); 'all' is the total."
                ),
                "description": (
                    "Demographic subgroup (FK to the global demographics "
                    "dimension). Race buckets use the combined "
                    "asian_pacific_islander key (pre-1997 OMB convention) "
                    "in every year: 2011+ bronze publishes the explicit "
                    "'Asian/Pacific Islander' label, and the bare 'Asian' "
                    "label of 2004-2010 is the same combined bucket — the "
                    "six race-bucket counts sum exactly to the All Students "
                    "totals at the state level in every year, so Pacific "
                    "Islanders are folded in, never published separately. "
                    "2004-2017 publish 15 subgroups; active_duty, "
                    "foster_care, and homeless appear from 2018; "
                    "english_learners is absent in 2021 only. 'all' is the "
                    "unfiltered total and overlaps every other value; "
                    "subgroups are mutually exclusive only within their own "
                    "category (race, gender, disability, economic, special "
                    "population)."
                ),
            },
            {
                "name": "num_graduates",
                "metric_component": "numerator",
                "type": "int64",
                "unit": "count",
                "example": 225,
                "null_meaning": (
                    "Suppressed by GOSA ('Too few Students' literals in "
                    "2010, blank cells 2011-2020, TFS literals 2021-2024). "
                    "2004-2009 have no suppression NULLs — those sources "
                    "publish literal zeros instead. Always co-suppressed "
                    "with graduation_rate."
                ),
                "description": (
                    "Number of students in the subgroup's cohort who "
                    "graduated with a regular diploma within four years of "
                    "first entering 9th grade (from 2011 the federal "
                    "adjusted-cohort numerator; 2004-2010 use the state's "
                    "earlier leaver-based accounting). Published values are "
                    ">= 10 from 2011 onward (GOSA's n=10 reporting "
                    "threshold). 2004-2009 use literal zeros for suppressed "
                    "cells — a zero in those years may be real or "
                    "suppressed and the two cannot be distinguished in "
                    "source. The three non-suppressed 2010 migrant rows are "
                    "internally inconsistent in bronze (num_graduates = "
                    "num_cohort yet graduation_rate != 1.0; "
                    "graduation_rate is the authoritative figure) and are "
                    "preserved as published."
                ),
            },
            {
                "name": "num_cohort",
                "metric_component": "denominator",
                "type": "int64",
                "unit": "count",
                "example": 240,
                "null_meaning": (
                    "Suppressed by GOSA, or unpublished: the source has no "
                    "cohort denominator at all for 2012-2016."
                ),
                "description": (
                    "Cohort size — the denominator of the graduation rate. "
                    "From 2011 this is the federal adjusted four-year "
                    "cohort (first-time 9th-graders four years prior, plus "
                    "transfers in, minus transfers out); the 2004-2010 "
                    "denominator is the source's 'Approximate Class Size' "
                    "(pre-ACGR leaver-based methodology). NULL for ALL rows "
                    "in 2012-2016 (the source does not publish TOTAL_COUNT "
                    "in those years; consumers may estimate "
                    "round(num_graduates / graduation_rate) at their own "
                    "rounding risk). In 2023-2024 some rows — mostly "
                    "school-level (295 school / 74 district in 2023, 271 / "
                    "68 in 2024) — publish num_cohort while num_graduates "
                    "and graduation_rate are suppressed (partial "
                    "suppression). Published values are >= 10 from 2011 "
                    "onward. 2004-2009 zeros may be real or suppressed (see "
                    "num_graduates)."
                ),
            },
            {
                "name": "graduation_rate",
                "key_metric": True,
                "type": "float64",
                "unit": "proportion",
                "example": 0.9375,
                "null_meaning": (
                    "Suppressed by GOSA ('Too few Students' literals in "
                    "2010, blank cells 2011-2020, TFS literals 2021-2024). "
                    "2004-2009 have no suppression NULLs — those sources "
                    "publish literal zeros instead. Always co-suppressed "
                    "with num_graduates."
                ),
                "short_description": (
                    "Share of the four-year cohort that graduated, on a "
                    "0-1 scale; 2011+ is the federal ACGR, 2004-2010 a "
                    "non-comparable older method."
                ),
                "description": (
                    "Four-year graduation rate as a proportion (0-1 "
                    "scale): num_graduates divided by num_cohort. From "
                    "2011 this is the federal adjusted-cohort rate (ACGR); "
                    "2004-2010 use Georgia's earlier leaver-based "
                    "methodology and are NOT trend-comparable with 2011+ "
                    "(state rate breaks 0.808 -> 0.675 at the 2010->2011 "
                    "boundary). The source publishes 0-100 percentages (1-2 "
                    "decimal places); divided by 100. Reconciles with "
                    "num_graduates / num_cohort within 0.001 everywhere "
                    "except the three documented 2010 migrant defect rows. "
                    "Zeros in 2004-2009 may be real or suppressed (see "
                    "num_graduates)."
                ),
            },
        ],
        source="Governor's Office of Student Achievement (GOSA)",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        limitations=(
            "2004-2010 figures predate Georgia's adoption of the federal "
            "four-year adjusted-cohort methodology (ACGR, first reported "
            "2011) and use the state's earlier leaver-based rate; the "
            "2010->2011 state rate drop (~81%% to ~67%%) is a methodology "
            "break, not a real decline — do not trend across it. "
            "Suppressed cells are NULL (not zero) from 2010 onward, but "
            "2004-2009 sources use literal ZEROS for suppressed cells — a "
            "zero rate/count in those years may be real or suppressed and "
            "cannot be distinguished; treat very small cohorts in "
            "2004-2009 with caution. num_cohort is NULL for every row in "
            "2012-2016 (the source publishes no denominator in those "
            "years). School rows do not always sum to the published "
            "district row (49 of ~3,850 district-years publish a district "
            "num_graduates below the visible school sum, source-"
            "published, e.g. 2016 Whitfield 709 vs 810) — use the "
            "official district/state rows for rollups rather than summing "
            "school rows. The race axis uses "
            "the combined asian_pacific_islander bucket — not comparable "
            "row-for-row with split-convention topics without aggregating "
            "those topics' asian + pacific_islander rows at query time. "
            "State rows have NULL district_code and school_code; district "
            "rows have NULL school_code."
        ),
        notes=[
            (
                "Methodology break at 2010->2011: Georgia first reported "
                "the federal four-year adjusted-cohort graduation rate "
                "(ACGR) in 2011. The 2004-2010 figures are the state's "
                "earlier leaver-based rate (the wide-era denominator "
                "column is literally named 'Approximate Class Size'); the "
                "state all-students rate breaks 0.808 (2010) -> 0.675 "
                "(2011) at exactly that boundary. Do not trend across "
                "2010->2011."
            ),
            (
                "Suppression markers by era, all NULL in gold: 2010 'Too "
                "few Students' literals (the only marker year — measured: "
                "2007-2009 contain zero markers, zero blanks, and zero "
                "NULLs); 2011-2020 blank cells; 2021-2024 'TFS' literals. "
                "2004-2009 instead publish literal zeros that cannot be "
                "told apart from real zeros and are preserved as-is. From "
                "2011 onward every published count is >= 10 (GOSA's n=10 "
                "reporting threshold; enforced by a quality check)."
            ),
            (
                "num_graduates and graduation_rate are always "
                "co-suppressed (verified: zero rows in any year where "
                "exactly one of the two is missing). num_cohort is NOT "
                "always co-suppressed: 2023-2024 publish it on 369/339 "
                "rows whose other metrics are TFS-suppressed (mostly "
                "school-level: 295 school / 74 district in 2023, 271 / 68 "
                "in 2024), and 2012-2016 omit it entirely."
            ),
            (
                "Asian/Pacific Islander is the combined pre-1997 OMB "
                "bucket (asian_pacific_islander) in every year, per "
                "data-cleaning-standards §5b: the six race buckets' "
                "state-level graduate counts and cohort sizes sum EXACTLY "
                "to the All Students totals in every year 2004-2024 "
                "(male+female do too), proving Pacific Islanders are "
                "folded in rather than dropped. The bare 'Asian' label of "
                "2004-2010 is relabeled to the combined bucket in the "
                "transform; the split asian / pacific_islander keys are "
                "never emitted."
            ),
            (
                "2010 source defect, preserved: the three non-suppressed "
                "migrant rows of 2010 — the state aggregate "
                "(graduation_rate=0.655, num_graduates=110, "
                "num_cohort=110) and the Colquitt County district and "
                "school rows (rate=0.696, count=23, cohort=23) — are "
                "internally inconsistent in bronze (count equals cohort "
                "yet rate != 1.0; the rate is the authoritative figure). "
                "All values are individually possible, so the rows are "
                "preserved exactly as published (data-cleaning-standards "
                "§4b extreme-but-conceivable) and excluded from the "
                "rate-reconciliation quality check."
            ),
            (
                "Demographic set varies by year: 15 subgroups in "
                "2004-2017; Active Duty, Foster, and Homeless appear from "
                "the 2018 file (18 subgroups); Limited English Proficient "
                "is absent in the 2021 file only (17). Earlier years "
                "simply have no rows for the later subgroups — absence "
                "means not collected, not zero."
            ),
            (
                "Wide-era source duplicates, deduplicated: 2004 carries 50 "
                "duplicate SysSchoolIDs (malformed-export artifact) and "
                "2009 carries 2 (renamed single-school charters); every "
                "twin pair is value-identical after casting, so dedup "
                "drops one twin per pair (780 rows total) with no value "
                "judgment. One corrupt 2004 row (SysSchoolID='0\"') lacking "
                "the district:school delimiter is dropped."
            ),
            (
                "Schema eras: 2004-2006 wide format with human-readable "
                "headers (2005/2006 are XLS binaries mislabeled .csv, "
                "detected by magic bytes); 2007-2010 wide format with "
                "cryptic GradRate_* codes; 2011-2024 tidy long format. "
                "2023-2024 add a constant '#RPT_NAME' column (dropped). "
                "Entity names and GRADES_SERVED_DESC are dimension "
                "attributes, not fact columns."
            ),
            (
                "Known NULL-rate spikes, both bronze-real: (1) 2004 "
                "enumerates every Georgia public school — including "
                "elementary/middle schools with no graduating cohort — "
                "with blank metrics on ~77%% of rows (2005 onward "
                "enumerate only entities with cohorts); the blanks are "
                "in-band empty cells, not read loss. (2) num_cohort is "
                "100%% NULL in 2012-2016 because the source publishes no "
                "denominator in those years."
            ),
        ],
        quality_checks=[
            {
                "name": "num_graduates_not_exceeding_num_cohort",
                "description": (
                    "The four-year adjusted-cohort numerator "
                    "(num_graduates) never exceeds its denominator "
                    "(num_cohort) where both are present. Verified 0 "
                    "violations across all bronze years 2004-2024."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE num_graduates IS NOT NULL "
                    "AND num_cohort IS NOT NULL "
                    "AND num_graduates > num_cohort"
                ),
                "mustBe": 0,
            },
            {
                "name": "graduation_rate_reconciles_with_counts",
                "description": (
                    "Where rate, count, and cohort are all present and the "
                    "cohort is positive, the published rate equals "
                    "num_graduates / num_cohort within 0.001 (the source "
                    "rounds the percent to 1-2 decimals; measured max "
                    "legitimate deviation 0.0005). Excludes the three "
                    "documented 2010 migrant defect rows (year=2010 AND "
                    "demographic='migrant'), the only violations in any "
                    "year — see notes."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE graduation_rate IS NOT NULL "
                    "AND num_graduates IS NOT NULL "
                    "AND num_cohort IS NOT NULL AND num_cohort > 0 "
                    "AND NOT (year = 2010 AND demographic = 'migrant') "
                    "AND ABS(graduation_rate "
                    "- (CAST(num_graduates AS DOUBLE) / num_cohort)) "
                    "> 0.001"
                ),
                "mustBe": 0,
            },
            {
                "name": "num_graduates_and_rate_co_suppressed",
                "description": (
                    "GOSA suppresses num_graduates and graduation_rate "
                    "together in every era: no row may have exactly one of "
                    "the two missing (verified across all 21 bronze "
                    "files). num_cohort is exempt — 2023-2024 publish it "
                    "on partially suppressed rows and 2012-2016 omit it."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(num_graduates IS NULL) <> (graduation_rate IS NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "num_cohort_unpublished_2012_2016",
                "description": (
                    "The source publishes no cohort denominator "
                    "(TOTAL_COUNT) in 2012-2016, and the transform does "
                    "not derive one from the rounded rate: num_cohort "
                    "must be NULL on every row in those years."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "year BETWEEN 2012 AND 2016 AND num_cohort IS NOT NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_race_partition_sums_to_all",
                "description": (
                    "At the state level the six mutually exclusive race "
                    "buckets partition the graduating cohort: their "
                    "num_graduates values sum exactly to the 'all' total "
                    "in every year (the §5b math test proving the combined "
                    "Asian/Pacific Islander convention; verified "
                    "2004-2024). State race rows are never suppressed."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year FROM {object} "
                    "WHERE district_code IS NULL AND school_code IS NULL "
                    "GROUP BY year HAVING "
                    f"SUM(CASE WHEN demographic IN ({race_list}) "
                    "THEN num_graduates ELSE 0 END) <> "
                    "MAX(CASE WHEN demographic = 'all' THEN num_graduates "
                    "END)) AS bad_years"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_gender_partition_sums_to_all",
                "description": (
                    "At the state level male + female num_graduates sums "
                    "exactly to the 'all' total in every year (verified "
                    "2004-2024; state gender rows are never suppressed)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year FROM {object} "
                    "WHERE district_code IS NULL AND school_code IS NULL "
                    "GROUP BY year HAVING "
                    "SUM(CASE WHEN demographic IN ('male', 'female') "
                    "THEN num_graduates ELSE 0 END) <> "
                    "MAX(CASE WHEN demographic = 'all' THEN num_graduates "
                    "END)) AS bad_years"
                ),
                "mustBe": 0,
            },
            {
                "name": "published_counts_meet_reporting_threshold_2011_on",
                "description": (
                    "From 2011 onward every published num_graduates and "
                    "num_cohort is >= 10 — GOSA's n=10 cell-size "
                    "suppression threshold (verified per file). A smaller "
                    "value means a suppression regression or column swap. "
                    "2004-2010 are exempt: the wide eras publish "
                    "sub-threshold values (including suppression zeros)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year >= 2011 AND "
                    "((num_graduates IS NOT NULL AND num_graduates < 10) "
                    "OR (num_cohort IS NOT NULL AND num_cohort < 10))"
                ),
                "mustBe": 0,
            },
            {
                "name": "expanded_subgroups_absent_before_2018",
                "description": (
                    "Active Duty, Foster, and Homeless first appear in the "
                    "2018 file: no active_duty / foster_care / homeless "
                    "rows may exist before 2018."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year < 2018 AND "
                    "demographic IN ('active_duty', 'foster_care', "
                    "'homeless')"
                ),
                "mustBe": 0,
            },
            {
                "name": "english_learners_absent_2021",
                "description": (
                    "The 2021 file drops the Limited English Proficient "
                    "subgroup (present in every other year 2004-2024): no "
                    "english_learners rows may exist in 2021."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year = 2021 AND "
                    "demographic = 'english_learners'"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
