"""Transform bronze postsecondary_c12 files into gold fact tables.

Source: Governor's Office of Student Achievement (GOSA) — Postsecondary C12
Report. For every Georgia public high school, plus official district and
state rollups, reports three raw student counts per demographic subgroup
along the HS-graduate-to-postsecondary pipeline: ``num_graduates`` (HS
graduates in the cohort year), ``num_enrolled_in_college`` (graduates who
enrolled in a postsecondary institution), and ``num_earned_24_credits``
(graduates who accumulated >= 24 postsecondary credit hours within 2 years
of initial enrollment). 13 bronze files, publication years 2012-2024,
covering HS graduating cohorts 2008-2020 (filename year = cohort year + 4).

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Three eras, two read paths.** Eras 1-2 (2012-2022) are XLSX with a
  three-row header (Row 0 = "TFS stands for Too Few Students" note, Row 1 =
  merged demographic-group labels, Row 2 = repeated metric labels, data from
  Row 3). The XLSX path stitches the header manually (pandas ``header=None,
  dtype=str``, forward-fill Row 1, synthesize ``{demo}__{metric}`` names)
  because ``read_bronze_file`` would consume the note cell as a header. Era
  boundaries within XLSX are detected from the stitched column set via
  ``detect_era_by_columns`` — Era 1 (the 2012 file, cohort 2008) lacks the
  Pacific Islander group (13 demographics x 3 metrics); Era 2 (2013-2022,
  cohorts 2009-2018) carries 14. Era 3 (2023-2024 CSVs, cohorts 2019-2020)
  is flat snake-case-ish columns (``{PREFIX}_{METRIC}``) read through
  ``read_bronze_file(..., infer_schema_length=0)``; the lone column-name
  outlier is ``TOTAL_ENROLLED_IN_COLLEGE`` (every other prefix uses
  ``{PREFIX}_IN_COLLEGE``).
- **Read-loss accounting.** The CSV path uses ``read_bronze_file(...,
  return_loss=True)``. The stitched XLSX path loads whole sheets via pandas,
  where raw == parsed by construction (the same parity ``read_bronze_file``
  reports for Excel); the loss call is still made with that parity so the
  accounting convention is uniform.
- **Gold year = HS graduating cohort year**, taken from the single
  ``School Year`` / ``SCHOOL_YEAR`` value inside each file (Era 3 stores it
  as a float string, ``"2019.00000"``), never the filename. The transform
  hard-fails unless filename year == cohort year + 4 (the offset is
  consistent across all 13 files), so a misnamed file cannot mislabel a
  cohort.
- **Asian / Pacific Islander uses the SPLIT convention (§5a/§5b).** From
  cohort 2009 onward the source publishes a separate Pacific Islander group
  alongside Asian, and the §5b math test confirms the scheme is complete and
  non-overlapping: at the state level the seven race buckets (hispanic,
  multiracial, native_american, asian, black, white, pacific_islander) sum
  EXACTLY to the Total All graduate count in 2010-2016 and 2019-2020 (gaps
  of <= 8 students in 2017-2018, unclassified-race residue). Bare "Asian"
  therefore maps to ``asian`` (Asian-only), never the combined bucket. No
  rollup rows are synthesized.
- **Cohort 2008 (Era 1) has no Pacific Islander group** — those rows are
  simply absent for year=2008 (never padded with NULL-metric rows, which
  would misrepresent unobserved data as observed-and-suppressed). In
  2008-2009 the state race-bucket sums fall short of Total All by 1,433 /
  1,779 students — far more than a plausible NHPI count (~100), so the gap
  is unclassified-race residue from the era's incomplete race scheme, not
  evidence that Pacific Islanders were folded into "Asian"; gender
  (male+female) sums exactly to Total All in every year, supporting the
  partition reading. "Asian" stays ``asian`` in Era 1 too, consistent with
  the rest of the series and the §5b registry (this topic is listed
  split-convention).
- **C12 enrollment is Georgia-institutions-only** (re-verified empirically,
  not just inherited from v1): for the same cohort 2016 the sibling C11
  report publishes 71,095 enrolled statewide vs C12's 57,468, while the
  graduate counts agree (103,947 vs 103,950). C11 counts enrollment
  anywhere in the nation; C12 only counts institutions where credit-hour
  data is available (Georgia), so C11 and C12 enrollment figures are NOT
  comparable. The bronze-data-structure.md overview line saying "in-state
  or out-of-state" appears to be copied from the C11 doc and contradicts
  this 19%% same-cohort gap; the empirical evidence wins.
- **Suppression**: every metric cell below 10 is published as the literal
  ``TFS`` (confirmed by the Oracle generator in the 2020 file's SQL sheet:
  ``CASE WHEN {metric} < 10 THEN 'TFS' ...``). TFS arrives as NULL from
  both read paths (``SUPPRESSION_VALUES``); every published value is >= 10
  (verified across all 13 files; pinned as a quality check). NULL means
  suppressed, never zero.
- **Metric ordering invariant** (verified empirically, zero violations
  across all files and demographics): ``num_earned_24_credits <=
  num_enrolled_in_college <= num_graduates`` wherever both sides are
  published. All three pairwise orderings are pinned as quality checks
  (the grads-vs-credits pair also covers rows where the middle metric is
  suppressed).
- **State gender partition is exact**: at the state level male + female
  equals the Total All value for ALL THREE metrics in every cohort year
  (verified, diff 0 in 13/13 years), and the state-level all/male/female
  rows are never suppressed. Both facts are pinned as quality checks. The
  race-bucket sums are NOT exact in every year (see above), so the race
  check is directional only: published race-bucket sums never exceed the
  'all' total (also a §5a mutual-exclusivity guard — a synthesized rollup
  row would overshoot).
- **Geography sentinels and detail level.** ``School Code == 'ALL'`` marks
  district aggregates; ``District Code == 'ALL'`` marks the state row
  (reading XLSX via pandas dtype=str yields the literal 'ALL' in every
  file, including 2015-2019 — the structure doc's "null district code on
  the state row" was an artifact of polars' integer coercion, which this
  transform does not use). Each file is verified to contain exactly one
  state entity. The (district='ALL', school=code) combination never occurs
  (verified). Sentinels become NULL in gold via the shared
  ``null_aggregate_geography`` rules.
- **ID formatting.** 2015-2019 files strip leading zeros from school codes
  ("103" for the "0103" published in adjacent years — verified to be the
  same school, Appling County High School); ``zfill(4)`` restores them.
  District codes are 3-digit standard or 7-digit state-charter strings;
  ``zfill(3)`` pads without truncating.
- **Dedup tie-break.** Each bronze file covers exactly one cohort year,
  years never overlap across files, and the per-file entity grain is unique
  (verified: zero duplicate (district, school) keys in any file), so no
  duplicates are expected. ``sort_col="num_graduates"`` remains as the
  documented safety net: prefer the row with a reported (non-null, larger)
  cohort over a suppressed placeholder.
- **No §4b masks.** A full scan of all 13 files found no impossible values:
  every published metric is an integer in [10, 113,189] (the state-total
  graduate count), no negatives, no out-of-scale values, and the ordering
  invariant holds everywhere — so no ``_null_*`` helper exists and the
  manifest carries no ``masked_values`` section.
- **No demographic collisions**: the 13/14 bronze labels map 1:1 onto
  distinct canonical keys (no two labels share a canonical value), so
  ``aggregate_demographic_collisions`` is unnecessary; the collision guard
  in ``main()`` would surface any future drift.
"""

import logging
from pathlib import Path

import pandas as pd
import polars as pl

from src.utils.demographics import (
    DEMOGRAPHIC_ALIASES,
    normalize_demographic_column,
)
from src.utils.metadata import write_data_dictionary
from src.utils.readers import (
    SUPPRESSION_VALUES,
    extract_year_from_filename,
    list_bronze_files,
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

TOPIC = "postsecondary_c12"
BRONZE_DIR = Path("data/bronze/education/gosa/postsecondary_c12")
GOLD_DIR = Path("data/gold/education/postsecondary_c12")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Filename (publication) year = HS graduating cohort year + this offset:
# C12 tracks enrollment plus 24-credit completion within 2 years of
# enrollment, published 4 years after graduation. Consistent in all files.
FILENAME_YEAR_OFFSET = 4

# Aggregate-row sentinel: School Code = ALL on district rows; District Code =
# ALL on the state row. Becomes NULL in gold, never a key value.
GEOGRAPHY_SENTINEL = "ALL"

# --- XLSX (Eras 1-2) three-row header constants ----------------------------

# Row 0 of every C12 XLSX data sheet opens with this note; its absence means
# the layout drifted and the stitcher must not guess.
XLSX_TFS_NOTE_FRAGMENT = "TFS stands for"

# Row 2's first five cells are the identifier columns, always in this order.
XLSX_ID_LABELS: list[str] = [
    "School Year",
    "School District Code",
    "School District Name",
    "School Code",
    "School Name",
]

# Internal names for the five identifier columns after stitching. The name
# columns are carried only so the stitcher's output is self-describing; they
# are never selected into gold (names live in the dimension tables).
XLSX_ID_NAMES: list[str] = [
    "school_year",
    "district_code_raw",
    "district_name_raw",
    "school_code_raw",
    "school_name_raw",
]

# Row 2's repeated per-group metric labels -> short metric keys used in the
# stitched "{demographic}__{metric_key}" column names.
XLSX_METRIC_LABEL_TO_KEY: dict[str, str] = {
    "Total High School Graduates": "hs_grads",
    "Number of High School Graduates Enrolled in Postsecondary Institution": (
        "in_college"
    ),
    "Number that Completed 1yr of Credit within 2 Years of Enrollment": (
        "earned_24credits"
    ),
}

# --- Era 3 (2023-2024 CSV) constants ----------------------------------------

# Demographic column prefixes in the Era 3 CSV header. Every prefix has a
# direct entry in the shared DEMOGRAPHIC_ALIASES (TOTAL -> all, FRL ->
# economically_disadvantaged, SWD -> students_with_disabilities, NATIVE ->
# native_american, TWOORMORE -> multiracial, PACIFIC -> pacific_islander, ...)
# so the raw prefix itself is the recorded bronze label.
ERA3_PREFIXES: list[str] = [
    "TOTAL",
    "MALE",
    "FEMALE",
    "FRL",
    "MIGRANT",
    "LEP",
    "SWD",
    "HISPANIC",
    "TWOORMORE",
    "NATIVE",
    "ASIAN",
    "BLACK",
    "WHITE",
    "PACIFIC",
]

# Era-detection signatures, most-specific first. The two XLSX eras are told
# apart by the Pacific Islander group present in the stitched column set
# (Era 2) and absent in Era 1 (the 2012 file / cohort 2008).
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_3_csv": [
        "SCHOOL_YEAR",
        "SCHOOL_DISTRCT_CD",
        "INSTN_NUMBER",
        "TOTAL_ENROLLED_IN_COLLEGE",
    ],
    "era_2_xlsx": ["school_year", "Pacific Islander__hs_grads"],
    "era_1_xlsx": ["school_year", "Asian__hs_grads"],
}

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "num_graduates",
    "num_enrolled_in_college",
    "num_earned_24_credits",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "demographic": pl.Utf8,
    "num_graduates": pl.Int64,
    "num_enrolled_in_college": pl.Int64,
    "num_earned_24_credits": pl.Int64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = [
    "num_graduates",
    "num_enrolled_in_college",
    "num_earned_24_credits",
]

NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "detail_level",
]

# The 14 canonical demographic keys this topic publishes (13 in cohort 2008,
# which lacks pacific_islander). Used for the contract enum.
DEMOGRAPHIC_VALUES: list[str] = sorted(
    [
        "all",
        "asian",
        "black",
        "economically_disadvantaged",
        "english_learners",
        "female",
        "hispanic",
        "male",
        "migrant",
        "multiracial",
        "native_american",
        "pacific_islander",
        "students_with_disabilities",
        "white",
    ]
)

# The seven mutually exclusive split-convention race buckets (§5a/§5b). At
# the state level their published sums never exceed the 'all' total (exact
# equality 2010-2016 and 2019-2020) — enforced directionally by a quality
# check.
RACE_BUCKET_KEYS: list[str] = [
    "asian",
    "black",
    "hispanic",
    "multiracial",
    "native_american",
    "pacific_islander",
    "white",
]


# =============================================================================
# Casting helpers
# =============================================================================


def _to_int_expr(col: str) -> pl.Expr:
    """Cast an all-string bronze count column to Int64 via a Float64 hop.

    Suppression markers (TFS) already arrived as NULL from both read paths;
    ``strict=False`` nulls any other non-numeric residue. The Float64 hop
    tolerates decimal-formatted counts ("16.0") without silently nulling
    them; counts are integral so the Int64 cast is exact.
    """
    return pl.col(col).str.strip_chars().cast(pl.Float64, strict=False).cast(pl.Int64)


# =============================================================================
# XLSX header stitching (Eras 1-2)
# =============================================================================


def _forward_fill_labels(labels: list) -> list[str | None]:
    """Forward-fill merged-cell demographic labels across metric columns.

    Row 1 carries each demographic group's name only above the first of its
    three metric columns; the other two arrive as NaN/None/blank and must
    inherit the previous label.
    """
    result: list[str | None] = []
    last: str | None = None
    for v in labels:
        if v is None or (isinstance(v, float) and pd.isna(v)) or not str(v).strip():
            result.append(last)
        else:
            last = str(v).strip()
            result.append(last)
    return result


def _stitch_xlsx(path: Path) -> pl.DataFrame:
    """Read a C12 XLSX and return an all-string frame with flat column names.

    Reads sheet 0 with ``header=None, dtype=str`` (the metadata sheets —
    2012's ``Sheet1`` label dump and 2020's ``SQL`` generator sheet — are
    never sheet 0), verifies the Row 0 TFS note, forward-fills the Row 1
    demographic labels, validates the Row 2 identifier labels, and
    synthesizes ``{demographic}__{metric_key}`` names for the 39/42 metric
    columns. Suppression markers are nulled at read time via ``na_values``
    (the same set ``read_bronze_file`` applies).

    Returns:
        Polars DataFrame: 5 identifier columns (XLSX_ID_NAMES) + metric
        columns, all Utf8, data rows only.
    """
    pdf = pd.read_excel(
        path,
        sheet_name=0,
        engine="openpyxl",
        header=None,
        dtype=str,
        na_values=list(SUPPRESSION_VALUES),
    )

    # Fail-fast layout guards: the stitcher hard-codes row positions, so the
    # note cell and the identifier labels must be exactly where documented.
    first_cell = pdf.iat[0, 0]
    if not (isinstance(first_cell, str) and XLSX_TFS_NOTE_FRAGMENT in first_cell):
        raise ValueError(
            f"{path.name}: expected the TFS note in cell A1, got "
            f"{first_cell!r} — bronze layout drifted; re-run "
            "/bronze-data-structure before transforming."
        )
    metric_labels = [
        str(v).strip() if not (isinstance(v, float) and pd.isna(v)) else None
        for v in pdf.iloc[2].tolist()
    ]
    if metric_labels[:5] != XLSX_ID_LABELS:
        raise ValueError(
            f"{path.name}: identifier columns shifted — expected "
            f"{XLSX_ID_LABELS}, got {metric_labels[:5]}"
        )

    demo_labels = _forward_fill_labels(pdf.iloc[1].tolist())

    # Build flat names: 5 identifier columns, then {demo}__{metric_key} per
    # metric column. Trailing all-empty columns (pandas sometimes reads
    # them) get a sentinel name and are dropped below.
    flat_columns: list[str] = list(XLSX_ID_NAMES)
    for i in range(5, len(metric_labels)):
        demo, metric = demo_labels[i], metric_labels[i]
        if demo is None or metric is None:
            flat_columns.append(f"_unused_{i}")
            continue
        metric_key = XLSX_METRIC_LABEL_TO_KEY.get(metric)
        if metric_key is None:
            raise ValueError(
                f"{path.name}: unexpected metric label at column {i}: "
                f"{metric!r} (known: {list(XLSX_METRIC_LABEL_TO_KEY)})"
            )
        flat_columns.append(f"{demo}__{metric_key}")

    body = pdf.iloc[3:].copy()
    body.columns = flat_columns
    unused = [c for c in body.columns if c.startswith("_unused_")]
    if unused:
        logger.info("%s: dropping %d empty trailing column(s)", path.name, len(unused))
        body = body.drop(columns=unused)

    # Force Utf8 on every column: a 100%-suppressed metric column (e.g. the
    # 2012 file's Migrant earned-credits column, fully TFS -> fully NaN)
    # arrives from pandas as a Null-dtype series, which the .str casts in
    # _to_int_expr cannot handle.
    return pl.from_pandas(body, include_index=False).with_columns(
        pl.all().cast(pl.Utf8)
    )


# =============================================================================
# Shared long-format builder
# =============================================================================


def _blocks_to_long(
    df: pl.DataFrame,
    district_col: str,
    school_col: str,
    blocks: list[tuple[str, str, str, str]],
) -> pl.DataFrame:
    """Unpivot one wide bronze frame into long (entity x demographic) rows.

    Bronze is wide — 3 metric columns per demographic group. Each block is
    ``(bronze_demographic_label, grads_col, in_college_col, earned_col)``;
    one sub-frame per block is built and concatenated (the §9 pattern for
    multiple metrics per category).

    Args:
        df: All-string bronze frame (stitched XLSX or raw Era 3 CSV).
        district_col: Bronze district-code column name.
        school_col: Bronze school-code column name.
        blocks: One tuple per demographic group present in this file.

    Returns:
        Long frame: _district_raw, _school_raw, _demographic_raw + the three
        Int64 metric columns.
    """
    missing = [c for _, *cols in blocks for c in cols if c not in df.columns]
    if missing:
        # Rename-coverage guard: an unmatched source column would silently
        # become NULL in gold — the most common data-loss bug.
        raise ValueError(f"Expected bronze metric column(s) missing: {missing}")

    frames = [
        df.select(
            pl.col(district_col).str.strip_chars().alias("_district_raw"),
            pl.col(school_col).str.strip_chars().alias("_school_raw"),
            pl.lit(label).alias("_demographic_raw"),
            _to_int_expr(grads_col).alias("num_graduates"),
            _to_int_expr(college_col).alias("num_enrolled_in_college"),
            _to_int_expr(earned_col).alias("num_earned_24_credits"),
        )
        for label, grads_col, college_col, earned_col in blocks
    ]
    return pl.concat(frames)


def _xlsx_blocks(df: pl.DataFrame, path_name: str) -> list[tuple[str, str, str, str]]:
    """Derive demographic blocks from a stitched XLSX column set.

    Each demographic group must contribute exactly its three metric columns;
    a partial group means the stitcher mislabeled something.
    """
    demo_order: list[str] = []
    for c in df.columns:
        if "__" in c:
            demo = c.split("__", 1)[0]
            if demo not in demo_order:
                demo_order.append(demo)
    blocks = []
    for demo in demo_order:
        cols = (
            f"{demo}__hs_grads",
            f"{demo}__in_college",
            f"{demo}__earned_24credits",
        )
        present = [c for c in cols if c in df.columns]
        if len(present) != 3:
            raise ValueError(
                f"{path_name}: demographic group {demo!r} has "
                f"{len(present)}/3 metric columns ({present})"
            )
        blocks.append((demo, *cols))
    return blocks


def _era3_blocks() -> list[tuple[str, str, str, str]]:
    """Era 3 CSV demographic blocks from the fixed prefix list.

    The single naming outlier: the TOTAL group's enrollment column is
    ``TOTAL_ENROLLED_IN_COLLEGE`` (every other prefix uses
    ``{PREFIX}_IN_COLLEGE``).
    """
    return [
        (
            prefix,
            f"{prefix}_HS_GRADS",
            "TOTAL_ENROLLED_IN_COLLEGE"
            if prefix == "TOTAL"
            else f"{prefix}_IN_COLLEGE",
            f"{prefix}_EARNED_24CREDITS",
        )
        for prefix in ERA3_PREFIXES
    ]


# =============================================================================
# Per-file transform
# =============================================================================


def _resolve_cohort_year(df: pl.DataFrame, year_col: str, path: Path) -> int:
    """Resolve the HS graduating cohort year from inside the bronze file.

    Every file carries exactly one School Year value (Era 3 stores it as a
    float string like "2019.00000" — the float hop normalizes it). The
    filename publication year must equal cohort year + 4, so a misnamed or
    misrouted file fails loudly instead of mislabeling a cohort.
    """
    values = df[year_col].drop_nulls().unique().to_list()
    if len(values) != 1:
        raise ValueError(f"{path.name}: expected one {year_col} value, got {values}")
    try:
        year = int(float(str(values[0])))
    except ValueError as exc:
        raise ValueError(
            f"{path.name}: cannot parse {year_col} value {values[0]!r}"
        ) from exc

    filename_year = extract_year_from_filename(path.name)
    if filename_year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")
    if filename_year != year + FILENAME_YEAR_OFFSET:
        raise ValueError(
            f"{path.name}: filename year {filename_year} != cohort year "
            f"{year} + {FILENAME_YEAR_OFFSET} — offset drifted from "
            "bronze-data-structure.md"
        )
    return year


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame:
    """Read one bronze file, detect its era, and transform it to gold shape.

    Args:
        path: Bronze file path.
        manifest: Manifest for read-loss / file / bronze-count / categorical
            recording.

    Returns:
        Gold-shaped DataFrame with STANDARD_COLUMNS.
    """
    if path.suffix.lower() == ".csv":
        # All-string read: codes keep leading zeros, ALL sentinels and the
        # float-string SCHOOL_YEAR survive; TFS arrives as NULL.
        df, loss = read_bronze_file(path, infer_schema_length=0, return_loss=True)
        year_col, district_col, school_col = (
            "SCHOOL_YEAR",
            "SCHOOL_DISTRCT_CD",
            "INSTN_NUMBER",
        )
    else:
        # Stitched XLSX read (three-row header). Whole-sheet pandas loads
        # have raw == parsed by construction; record the parity so the
        # read-loss convention is uniform across both paths.
        df = _stitch_xlsx(path)
        loss = {"raw_rows": df.height, "parsed_rows": df.height}
        year_col, district_col, school_col = (
            "school_year",
            "district_code_raw",
            "school_code_raw",
        )

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{path.name}: no era signature matched columns {df.columns}")

    year = _resolve_cohort_year(df, year_col, path)
    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])
    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)
    logger.info(
        "Processing %s as %s (cohort year %d, %d entity rows)",
        path.name,
        era,
        year,
        df.height,
    )

    # Wide -> long: one row per (entity, demographic) with 3 count metrics.
    blocks = _era3_blocks() if era == "era_3_csv" else _xlsx_blocks(df, path.name)
    long = _blocks_to_long(df, district_col, school_col, blocks)

    # Demographics: shared-alias normalization (§5). Bare "Asian" maps to
    # asian — split convention, verified by the §5b math test (docstring).
    long = long.with_columns(
        normalize_demographic_column("_demographic_raw").alias("demographic")
    )
    # Record the effective slice of the shared alias map: only the aliases
    # this file's labels actually hit, so the manifest stays reviewable
    # while the unmapped guard still flags any label the map cannot place.
    observed_upper = {
        str(v).strip().upper()
        for v in long["_demographic_raw"].drop_nulls().unique().to_list()
    }
    effective_map = {
        k: v for k, v in DEMOGRAPHIC_ALIASES.items() if k in observed_upper
    }
    manifest.record_categorical(
        column="demographic",
        map_dict=effective_map,
        bronze_series=long["_demographic_raw"],
        gold_series=long["demographic"],
    )

    # Detail level from the ALL sentinels: state (district=ALL), district
    # (school=ALL), school (both real codes). The (district=ALL,
    # school=code) combination never occurs in this source (verified).
    long = long.with_columns(
        pl.when(pl.col("_district_raw") == GEOGRAPHY_SENTINEL)
        .then(pl.lit("state"))
        .when(pl.col("_school_raw") == GEOGRAPHY_SENTINEL)
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .alias("detail_level"),
    )
    # Structure guard: exactly one state entity per file (one row per
    # demographic block). A zero count means the ALL sentinel drifted (e.g.
    # a blank state-row district code) and rows are being mis-leveled.
    state_rows = long.filter(pl.col("detail_level") == "state").height
    if state_rows != len(blocks):
        raise ValueError(
            f"{path.name}: expected exactly 1 state entity "
            f"({len(blocks)} state rows after unpivot), got {state_rows}"
        )

    # Geography keys: ALL sentinel -> NULL (never a key value); zfill pads
    # 3-digit district / 4-digit school codes (restoring the leading zeros
    # the 2015-2019 files strip) and passes 7-digit charter codes through
    # unchanged (never truncate).
    long = long.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.when(pl.col("_district_raw") == GEOGRAPHY_SENTINEL)
        .then(None)
        .otherwise(pl.col("_district_raw").str.zfill(3))
        .alias("district_code"),
        pl.when(pl.col("_school_raw") == GEOGRAPHY_SENTINEL)
        .then(None)
        .otherwise(pl.col("_school_raw").str.zfill(4))
        .alias("school_code"),
    )

    return long.select(STANDARD_COLUMNS)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for postsecondary_c12."""
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
    # mean an alias/era-routing bug and must raise, not be deduped away.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: each bronze file is a distinct cohort year with no overlap,
    # and the per-file entity grain is unique (verified across all 13
    # files), so no duplicates are expected; prefer the row with a reported
    # (non-null, larger) num_graduates over a suppressed placeholder as
    # the documented safety net.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code", "demographic"],
        district_keys=["year", "district_code", "demographic"],
        state_keys=["year", "demographic"],
        sort_col="num_graduates",
    )

    # 4. Geography nulling (shared domain rules; a no-op for the sentinel
    # rows already nulled per file, but keeps transform + validator on one
    # rule source). No §4b masks: the full bronze scan found no impossible
    # values (see module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. Suppression NULL rates are heavy at school level
    # for sparse subgroups but uniform across years; no spike expected.
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
            "GOSA Postsecondary C12 Report: three raw student counts per "
            "demographic subgroup along the high-school-graduate-to-"
            "postsecondary pipeline, for every Georgia public high school "
            "with official district and state rollups — high school "
            "graduates in the cohort year (num_graduates), graduates who "
            "enrolled in a Georgia postsecondary institution "
            "(num_enrolled_in_college), and graduates who earned at least "
            "24 postsecondary credit hours (roughly one year of college) "
            "within two years of initial enrollment "
            "(num_earned_24_credits). IMPORTANT: unlike the sibling C11 "
            "report, which counts enrollment in institutions anywhere in "
            "the nation, C12 counts Georgia institutions only (verified: "
            "for the same 2016 cohort C11 reports 71,095 enrolled statewide "
            "vs C12's 57,468, while graduate counts agree), so C11 and C12 "
            "enrollment figures are NOT directly comparable. Covers HS "
            "graduating cohorts 2008-2020; no rates are published — derive "
            "college-going rate as num_enrolled_in_college / num_graduates "
            "and credit-earning rate as num_earned_24_credits / "
            "num_graduates at query time."
        ),
        title="Postsecondary Outcomes of HS Graduates (C12, Georgia)",
        summary=(
            "How many Georgia public high school graduates enrolled in a "
            "Georgia college and earned a year of credit, by school, "
            "district, and demographic subgroup, 2008-2020 cohorts."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2020,
                "description": (
                    "HS graduating cohort year (ending calendar year of the "
                    "school year; 2020 means the class of 2019-20), parsed "
                    "from the source's School Year column and cross-checked "
                    "against the filename (publication year = cohort year + "
                    "4). Never the publication year."
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
                    "GOSA school code, zero-padded to 4 characters "
                    "(composite FK to schools dimension with district_code; "
                    "not globally unique on its own). The 2015-2019 source "
                    "files strip leading zeros; the transform restores them. "
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
                    "Student subgroup the row covers (race, gender, economic, "
                    "or special-population); 'all' is the cohort total. Race "
                    "uses the split asian / pacific_islander convention."
                ),
                "description": (
                    "Demographic subgroup (FK to the global demographics "
                    "dimension). Race uses the SPLIT convention: asian and "
                    "pacific_islander are separate buckets (the source "
                    "publishes a distinct Pacific Islander group from "
                    "cohort 2009 onward, and at the state level the seven "
                    "race buckets sum exactly to the all-students total in "
                    "most years), never the combined "
                    "asian_pacific_islander rollup. pacific_islander rows "
                    "are absent (not NULL) in year=2008 — the 2012 source "
                    "file does not carry the group. 'all' is the "
                    "unfiltered total and overlaps every other value; "
                    "subgroups are mutually exclusive only within their "
                    "own category (race, gender, economic status, special "
                    "population)."
                ),
            },
            {
                "name": "num_graduates",
                "type": "int64",
                "unit": "count",
                "example": 140,
                "null_meaning": (
                    "Suppressed by GOSA: counts below 10 are published as "
                    "the literal TFS (Too Few Students)."
                ),
                "description": (
                    "Number of students in the demographic subgroup who "
                    "graduated from high school in the cohort year. "
                    "Published values are always >= 10 (GOSA suppresses "
                    "smaller cells as TFS). The denominator for both "
                    "derived rates."
                ),
            },
            {
                "name": "num_enrolled_in_college",
                "type": "int64",
                "unit": "count",
                "key_metric": True,
                "example": 96,
                "short_description": (
                    "Count of the cohort's graduates who enrolled in a "
                    "Georgia college; divide by num_graduates for the "
                    "in-state college-going rate (Georgia institutions only)."
                ),
                "null_meaning": (
                    "Suppressed by GOSA: counts below 10 are published as "
                    "the literal TFS (Too Few Students)."
                ),
                "description": (
                    "Number of those graduates who enrolled in a "
                    "postsecondary institution located in Georgia (public "
                    "or private, 2-year or 4-year). Georgia institutions "
                    "ONLY — the sibling C11 report counts enrollment "
                    "anywhere in the nation, so C11 and C12 enrollment "
                    "figures are not comparable. Never exceeds "
                    "num_graduates where both are published (enforced by "
                    "a quality check)."
                ),
            },
            {
                "name": "num_earned_24_credits",
                "type": "int64",
                "unit": "count",
                "example": 58,
                "null_meaning": (
                    "Suppressed by GOSA: counts below 10 are published as "
                    "the literal TFS (Too Few Students)."
                ),
                "description": (
                    "Number of those graduates who accumulated at least 24 "
                    "credit hours of postsecondary coursework — roughly one "
                    "year of college instruction — within two years of "
                    "initial enrollment; a persistence / college-readiness "
                    "signal. Never exceeds num_enrolled_in_college or "
                    "num_graduates where both are published (enforced by "
                    "quality checks)."
                ),
            },
        ],
        source="GOSA",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        limitations=(
            "Suppressed cells are NULL (not zero): GOSA publishes counts "
            "below 10 as TFS, so sparse subgroups (pacific_islander, "
            "native_american, migrant) are almost universally suppressed at "
            "school level, and summing only published school rows "
            "undercounts true totals — use district or state rows for "
            "official aggregates (a district total is NOT the sum of its "
            "published school rows). num_enrolled_in_college counts "
            "enrollment in GEORGIA institutions only; it is not comparable "
            "to the C11 report's nationwide enrollment count. "
            "pacific_islander rows are absent in year=2008. State rows have "
            "NULL district_code and school_code; district rows have NULL "
            "school_code."
        ),
        notes=[
            (
                "Gold year is the HS graduating cohort year (2008-2020), "
                "not the publication year in the filename (cohort + 4: C12 "
                "measures enrollment plus 24-credit completion within 2 "
                "years of enrollment, published 4 years after graduation)."
            ),
            (
                "Suppression: every metric cell below 10 students is "
                "published as the literal TFS — confirmed by the Oracle "
                "generator query shipped in the 2020 file's SQL sheet "
                "(CASE WHEN {metric} < 10 THEN 'TFS' ...). All published "
                "values are >= 10 (enforced by a quality check); TFS "
                "becomes NULL in gold and never zero."
            ),
            (
                "Georgia-only enrollment scope, verified empirically: for "
                "the same 2016 cohort the C11 report (nationwide) publishes "
                "71,095 enrolled statewide vs C12's 57,468, while the "
                "graduate counts agree (103,947 vs 103,950). C12's "
                "enrollment and credit measures cover institutions where "
                "Georgia credit-hour data exists."
            ),
            (
                "Race uses the split convention (data-cleaning-standards "
                "§5b): a separate Pacific Islander group exists from cohort "
                "2009 onward, and the seven state-level race-bucket "
                "graduate counts sum EXACTLY to the all-students total in "
                "2010-2016 and 2019-2020 (within 8 in 2017-2018), so bare "
                "'Asian' is Asian-only (asian), never the combined bucket. "
                "In cohorts 2008-2009 the race buckets fall short of the "
                "total by 1,433 / 1,779 students (unclassified-race residue "
                "in the early scheme; male+female still sums exactly)."
            ),
            (
                "Cohort 2008 (the 2012 file) lacks the Pacific Islander "
                "group entirely — gold has no pacific_islander rows for "
                "year=2008 (absent, not NULL), so consumers can distinguish "
                "not-collected from suppressed."
            ),
            (
                "At the state level male + female equals the all-students "
                "value for all three metrics in every year (verified, "
                "enforced by a quality check), and state all/male/female "
                "rows are never suppressed. 'Total All' is NOT always the "
                "race-bucket sum (see above) — always use the published "
                "'all' rows rather than summing subgroups."
            ),
            (
                "The 2015-2019 files store school codes without leading "
                "zeros ('103' vs '0103' in adjacent years — verified to be "
                "the same school); the transform zero-pads to 4 characters. "
                "District codes are 3-digit standard or 7-digit "
                "state-charter strings."
            ),
            (
                "No rates are published in bronze. Derive college-going "
                "rate as num_enrolled_in_college / num_graduates and "
                "credit-earning rate as num_earned_24_credits / "
                "num_graduates; NULLs propagate."
            ),
        ],
        quality_checks=[
            {
                "name": "num_enrolled_in_college_within_num_graduates",
                "description": (
                    "College enrollees are a subset of the graduate cohort: "
                    "num_enrolled_in_college never exceeds num_graduates "
                    "where both are published (verified across all bronze "
                    "years with zero violations)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "num_enrolled_in_college IS NOT NULL AND "
                    "num_graduates IS NOT NULL AND "
                    "num_enrolled_in_college > num_graduates"
                ),
                "mustBe": 0,
            },
            {
                "name": "num_earned_24_credits_within_enrolled",
                "description": (
                    "24-credit earners are a subset of college enrollees: "
                    "num_earned_24_credits never exceeds "
                    "num_enrolled_in_college where both are published "
                    "(verified across all bronze years with zero "
                    "violations)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "num_earned_24_credits IS NOT NULL AND "
                    "num_enrolled_in_college IS NOT NULL AND "
                    "num_earned_24_credits > num_enrolled_in_college"
                ),
                "mustBe": 0,
            },
            {
                "name": "num_earned_24_credits_within_num_graduates",
                "description": (
                    "24-credit earners are a subset of the graduate cohort: "
                    "num_earned_24_credits never exceeds num_graduates "
                    "where both are published — also covers rows where the "
                    "intermediate enrollment count is suppressed."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "num_earned_24_credits IS NOT NULL AND "
                    "num_graduates IS NOT NULL AND "
                    "num_earned_24_credits > num_graduates"
                ),
                "mustBe": 0,
            },
            {
                "name": "published_counts_meet_reporting_threshold",
                "description": (
                    "GOSA suppresses any metric cell below 10 as TFS (per "
                    "the Oracle generator in the 2020 file's SQL sheet), so "
                    "every published count is >= 10. A smaller value means "
                    "a suppression regression or column-swap error."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(num_graduates IS NOT NULL AND num_graduates < 10) "
                    "OR (num_enrolled_in_college IS NOT NULL AND "
                    "num_enrolled_in_college < 10) "
                    "OR (num_earned_24_credits IS NOT NULL AND "
                    "num_earned_24_credits < 10)"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_core_rows_never_suppressed",
                "description": (
                    "GOSA publishes unsuppressed statewide aggregates for "
                    "the all/male/female subgroups in every year (verified "
                    "across all bronze files): state-level rows "
                    "(district_code and school_code both NULL) for those "
                    "demographics carry all three metrics."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "district_code IS NULL AND school_code IS NULL "
                    "AND demographic IN ('all', 'male', 'female') "
                    "AND (num_graduates IS NULL "
                    "OR num_enrolled_in_college IS NULL "
                    "OR num_earned_24_credits IS NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_gender_partition_sums_to_all",
                "description": (
                    "At the state level male + female sums exactly to the "
                    "'all' value for ALL THREE metrics in every cohort year "
                    "(verified, diff 0 in 13/13 years). Pivoted via "
                    "conditional aggregation per data-cleaning-standards "
                    "§15b (never a self-join); the companion completeness "
                    "check guarantees the compared cells are non-NULL."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, "
                    "SUM(CASE WHEN demographic IN ('male', 'female') "
                    "THEN num_graduates END) AS mf_grads, "
                    "MAX(CASE WHEN demographic = 'all' "
                    "THEN num_graduates END) AS all_grads, "
                    "SUM(CASE WHEN demographic IN ('male', 'female') "
                    "THEN num_enrolled_in_college END) AS mf_enrolled, "
                    "MAX(CASE WHEN demographic = 'all' "
                    "THEN num_enrolled_in_college END) AS all_enrolled, "
                    "SUM(CASE WHEN demographic IN ('male', 'female') "
                    "THEN num_earned_24_credits END) AS mf_earned, "
                    "MAX(CASE WHEN demographic = 'all' "
                    "THEN num_earned_24_credits END) AS all_earned "
                    "FROM {object} "
                    "WHERE district_code IS NULL AND school_code IS NULL "
                    "GROUP BY year"
                    ") WHERE mf_grads <> all_grads "
                    "OR mf_enrolled <> all_enrolled "
                    "OR mf_earned <> all_earned"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_race_sum_within_all_total",
                "description": (
                    "The seven split-convention race buckets are mutually "
                    "exclusive (§5a), so their published state-level sums "
                    "never exceed the 'all' total for any metric in any "
                    "year (exact equality 2010-2016 and 2019-2020; short "
                    "by unclassified-race residue in 2008-2009 and by <= 8 "
                    "in 2017-2018). An overshoot would mean a synthesized "
                    "rollup row or double-counted bucket. NULL race cells "
                    "(suppressed) contribute zero, which only lowers the "
                    "sum."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, "
                    f"SUM(CASE WHEN demographic IN ({race_list}) "
                    "THEN num_graduates ELSE 0 END) AS race_grads, "
                    "MAX(CASE WHEN demographic = 'all' "
                    "THEN num_graduates END) AS all_grads, "
                    f"SUM(CASE WHEN demographic IN ({race_list}) "
                    "THEN num_enrolled_in_college ELSE 0 END) AS race_enr, "
                    "MAX(CASE WHEN demographic = 'all' "
                    "THEN num_enrolled_in_college END) AS all_enr, "
                    f"SUM(CASE WHEN demographic IN ({race_list}) "
                    "THEN num_earned_24_credits ELSE 0 END) AS race_earned, "
                    "MAX(CASE WHEN demographic = 'all' "
                    "THEN num_earned_24_credits END) AS all_earned "
                    "FROM {object} "
                    "WHERE district_code IS NULL AND school_code IS NULL "
                    "GROUP BY year"
                    ") WHERE race_grads > all_grads "
                    "OR race_enr > all_enr "
                    "OR race_earned > all_earned"
                ),
                "mustBe": 0,
            },
            {
                "name": "pacific_islander_absent_2008",
                "description": (
                    "The 2012 source file (cohort 2008) does not carry the "
                    "Pacific Islander group; the transform never pads "
                    "unobserved demographics, so no pacific_islander rows "
                    "may exist in year=2008."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "demographic = 'pacific_islander' AND year = 2008"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
