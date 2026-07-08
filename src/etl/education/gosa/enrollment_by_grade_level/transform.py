"""Transform bronze enrollment_by_grade_level files into gold fact tables.

Source: Governor's Office of Student Achievement (GOSA) — student enrollment
counts by grade level for every Georgia public school, school district, and
the state, school years 2010-11 through 2023-24 (14 bronze CSV files; the
filename year equals the ending calendar year of the school year and is
cross-checked against the in-file LONG_SCHOOL_YEAR). Each (geography, grade,
period) cell carries one metric: the number of enrolled students, snapshotted
twice per school year (Fall and Spring — GaDOE's twice-yearly FTE enrollment
collection cycles).

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Two eras, one transform body.** Era 1 (2023-2024) adds a constant
  ``#RPT_NAME`` column ("Enrollment_by_Grade") and emits sparse rows (only
  grade x entity combinations with data — ~28.5k rows/year); Era 2
  (2011-2022) has no ``#RPT_NAME`` and emits a dense set (~65k rows/year:
  every present (entity, period) pair carries all 13 grade rows, with 0 or
  TFS for grades not served). After uppercasing column names and dropping
  ``#RPT_NAME``, both eras share the same 7 working columns, so a single
  body handles both. Era detection is by column signature, never year range.
- **2012 casing quirk.** The 2012 file alone names the metric column
  ``Enrollment_Count``; every other file uses ``ENROLLMENT_COUNT``. All
  column names are uppercased immediately after read to absorb this.
- **Three suppression regimes** for ``ENROLLMENT_COUNT``:
  (1) 2011-2020 — no suppression; ``0`` is a true zero (grade not served)
  and is preserved as a real value, never NULLed; (2) 2021-2022 — any cell
  <10 (including true zeros) is the literal ``TFS``, mapped to NULL by
  ``read_bronze_file``'s shared suppression markers; (3) 2023-2024 — TFS
  continues AND rows for non-applicable (entity x grade) combinations are
  no longer emitted at all (row count roughly halves).
- **2022 School+ALL sentinel twins are dropped (52 rows).** The 2022 file
  alone emits rows with ``DETAIL_LVL_DESC='School'`` but
  ``INSTN_NUMBER='ALL'`` for two single-school charter districts (7830627
  Atlanta SMART Academy, 7830636 Northwest Classical Academy; 26 rows
  each). Verified against bronze: every such row exactly duplicates the
  matching school-coded row's ENROLLMENT_COUNT for the same (district,
  period, grade), and neither district has District-level rows in 2022 —
  so the ALL-row is a redundant copy of the lone school, not a real
  district aggregate. Reclassifying to district level would fabricate 52
  district facts with no bronze counterpart; the rows are dropped instead,
  guarded by an exact-duplicate assertion (the drop hard-fails if a twin
  ever lacks a matching school-coded row) and recorded via
  ``manifest.record_filtered``.
- **Grade encoding.** Bronze mixes ``K`` with ordinal-suffix strings
  (``1st``..``12th``); gold uses the canonical §16 vocabulary via the
  shared ``normalize_grade_column`` (``'k'``, ``'01'``..``'12'``). This
  source publishes no PK and no cross-grade aggregate row, so ``'pk'`` /
  ``'all'`` never appear.
- **No demographic column.** No file publishes any demographic breakdown —
  every row is a total count, so the column is omitted per §5.
- **ID formatting.** ``district_code`` zfill(3) (3-char standard codes;
  7-char state-charter 782 / commission-charter 783 / state-school 799
  codes pass through unchanged — present in EVERY year 2011-2024, not just
  recent ones); ``school_code`` zfill(4). The bronze ``ALL`` sentinel in
  either ID column becomes NULL. All codes join the districts/schools
  dimensions with zero misses (verified across all 14 years).
- **Dedup tie-break.** Each bronze file covers exactly one school year and
  no file overlaps another; verified zero duplicate (year, geography,
  period, grade) keys across all 831k rows post twin-drop, so dedup is
  purely defensive. ``sort_col="num_students"`` documents the safety net:
  if a future republication introduces duplicates, prefer the row with a
  reported (non-NULL) count over a suppressed placeholder. The collision
  guard runs first so divergent-metric duplicates raise instead of being
  silently resolved.
- **No §4b masks.** The metric is a non-negative integer count; bronze
  contains only digit strings (verified: every non-TFS value matches
  ^\\d+$ in every year), so no impossible values exist to NULL.
- **Quality checks (§15b).** Single count metric, no demographics — no
  partition-sum or co-null shapes exist. Authored checks pin structural
  facts proven against bronze: exactly 13 state rows per (year, period)
  and 26 per year; the 2011-2022 dense-era invariant that every
  (geography, period) group carries all 13 grade rows; NULL counts only
  from 2021 onward (no suppression existed before); and ID length facts
  (district_code 3 or 7 chars, school_code 4 chars).

Judgment calls (non-interactive run):

1. Dropped (not reclassified) the 52 School+ALL twin rows in 2022 — see
   above; exact-duplicate guard makes the decision self-verifying.
2. Named the gold metric ``num_students`` (§16 canonical for an
   enrollment-slice count) over the structure doc's suggested
   ``enrollment_count``; the doc predates the vocabulary registry entry.
3. Bronze ``GRADES_SERVED_DESC`` (institution metadata), name columns
   (dimension attributes), and the constant ``#RPT_NAME`` are not carried
   into gold, per the structure doc's Gold Schema Classification.
"""

import logging
import re
from pathlib import Path

import polars as pl

from src.utils.grades import GRADE_LEVEL_MAP, normalize_grade_column
from src.utils.metadata import write_data_dictionary
from src.utils.readers import list_bronze_files, read_bronze_file
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

TOPIC = "enrollment_by_grade_level"
BRONZE_DIR = Path("data/bronze/education/gosa/enrollment_by_grade_level")
GOLD_DIR = Path("data/gold/education/enrollment_by_grade_level")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Bronze sentinel marking aggregate rows in the two ID columns:
# SCHOOL_DSTRCT_CD='ALL' on state rows; INSTN_NUMBER='ALL' on state and
# district rows (and, in 2022 only, on the 52 School-level twin rows).
BRONZE_ALL_SENTINEL = "ALL"

# Sentinel for unmapped categorical values (mirrors demographics/grades
# conventions so the manifest unmapped guard catches any new bronze label).
SENTINEL_UNMATCHED = "99999999"

# ENROLLMENT_PERIOD normalization: simple case folding, but routed through
# replace_strict + manifest so a new bronze label fails loudly.
ENROLLMENT_PERIOD_MAP: dict[str, str] = {
    "Fall": "fall",
    "Spring": "spring",
}

# Era detection by column signature (post-uppercase), most specific first:
# Era 1's signature is Era 2's plus #RPT_NAME, so Era 1 must be checked
# before Era 2 (whose columns are a subset of Era 1's).
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_1_2023_2024_rpt_name_sparse": [
        "#RPT_NAME",
        "LONG_SCHOOL_YEAR",
        "DETAIL_LVL_DESC",
        "SCHOOL_DSTRCT_CD",
        "INSTN_NUMBER",
        "ENROLLMENT_PERIOD",
        "GRADE_LEVEL",
        "ENROLLMENT_COUNT",
    ],
    "era_2_2011_2022_dense": [
        "LONG_SCHOOL_YEAR",
        "DETAIL_LVL_DESC",
        "SCHOOL_DSTRCT_CD",
        "INSTN_NUMBER",
        "ENROLLMENT_PERIOD",
        "GRADE_LEVEL",
        "ENROLLMENT_COUNT",
    ],
}

# The 7 bronze columns every era must carry (post-uppercase). Anything
# missing means source drift — fail loudly instead of emitting NULLs.
REQUIRED_BRONZE_COLUMNS = frozenset(
    {
        "LONG_SCHOOL_YEAR",
        "DETAIL_LVL_DESC",
        "SCHOOL_DSTRCT_CD",
        "INSTN_NUMBER",
        "ENROLLMENT_PERIOD",
        "GRADE_LEVEL",
        "ENROLLMENT_COUNT",
    }
)

# Gold fact column order. detail_level is carried for dedup / geography
# nulling / export splitting, then dropped by export_to_parquet(). No
# demographic column — this dataset has no demographic breakdowns.
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "detail_level",
    "enrollment_period",
    "grade_level",
    "num_students",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "detail_level": pl.Utf8,
    "enrollment_period": pl.Utf8,
    "grade_level": pl.Utf8,
    "num_students": pl.Int64,
}

METRIC_COLUMNS: list[str] = ["num_students"]

# Natural key for the collision guard: a fact cell is one
# (year, geography, period, grade) at one detail level.
NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "detail_level",
    "enrollment_period",
    "grade_level",
]

# Canonical grade vocabulary this source publishes (no 'pk', no 'all').
GRADE_LEVEL_VALUES: list[str] = [f"{n:02d}" for n in range(1, 13)] + ["k"]


# =============================================================================
# Helpers
# =============================================================================


def _parse_year_from_long_school_year(value: str) -> int:
    """Parse the ending calendar year from a ``YYYY-YY`` school-year string.

    Args:
        value: Bronze LONG_SCHOOL_YEAR value (e.g., ``"2023-24"``).

    Returns:
        Ending calendar year (e.g., 2024).

    Raises:
        ValueError: If the value doesn't match the ``YYYY-YY`` format.
    """
    match = re.fullmatch(r"(\d{4})-(\d{2})", value.strip())
    if not match:
        raise ValueError(f"Unexpected LONG_SCHOOL_YEAR format: {value!r}")
    start_year, end_suffix = int(match.group(1)), int(match.group(2))
    # All files are 2000s school years; the century carry is well-defined.
    return (start_year // 100) * 100 + end_suffix


def _extract_year_from_filename(name: str) -> int:
    """Extract the 4-digit year from ``enrollment_by_grade_level_YYYY.csv``.

    Anchored to the topic prefix so unrelated 4-digit substrings in a future
    filename cannot confuse year extraction.
    """
    match = re.search(r"enrollment_by_grade_level_(\d{4})", name)
    if not match:
        raise ValueError(f"Cannot extract year from filename: {name!r}")
    return int(match.group(1))


def _drop_school_all_sentinel_twins(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Drop School-level rows carrying the ``INSTN_NUMBER='ALL'`` sentinel.

    2022-only bronze quirk: two single-school charter districts (7830627,
    7830636) publish each cell twice — once school-coded, once with the
    ``ALL`` sentinel. The sentinel twin is a redundant copy of the lone
    school, not a district aggregate (neither district has District-level
    rows). Every dropped row must exactly duplicate a school-coded row's
    count for the same (district, period, grade) — guarded below so any
    future non-duplicate School+ALL row hard-fails instead of being lost.
    """
    twin_mask = (pl.col("detail_level") == "school") & (
        pl.col("INSTN_NUMBER") == BRONZE_ALL_SENTINEL
    )
    twins = df.filter(twin_mask)
    if twins.height == 0:
        return df

    join_cols = ["SCHOOL_DSTRCT_CD", "ENROLLMENT_PERIOD", "GRADE_LEVEL", "_count_chk"]
    # NULL-safe duplicate check: TFS counts are NULL after read, and polars
    # joins treat NULL != NULL — fill with a sentinel so NULL twins match.
    twins_chk = twins.with_columns(
        pl.col("ENROLLMENT_COUNT").fill_null("__NULL__").alias("_count_chk")
    )
    school_coded_chk = df.filter(
        (pl.col("detail_level") == "school") & ~twin_mask.fill_null(False)
    ).with_columns(pl.col("ENROLLMENT_COUNT").fill_null("__NULL__").alias("_count_chk"))
    unmatched = twins_chk.join(
        school_coded_chk.select(join_cols).unique(), on=join_cols, how="anti"
    )
    if unmatched.height:
        sample = unmatched.select(
            "SCHOOL_DSTRCT_CD", "ENROLLMENT_PERIOD", "GRADE_LEVEL"
        ).head(5)
        raise ValueError(
            f"Year {year}: {unmatched.height} School-level row(s) with "
            f"INSTN_NUMBER='ALL' do NOT duplicate a school-coded row — "
            f"refusing to drop. Sample: {sample.to_dicts()}"
        )

    df = df.filter(~twin_mask)
    manifest.record_filtered(
        year, twins.height, "school_all_sentinel_twin_of_school_coded_row"
    )
    logger.info(
        f"Year {year}: Dropped {twins.height} School-level row(s) with "
        f"INSTN_NUMBER='ALL' (exact duplicates of the school-coded rows for "
        f"single-school charter districts "
        f"{sorted(twins['SCHOOL_DSTRCT_CD'].unique().to_list())})."
    )
    return df


# =============================================================================
# Shared era transform body
# =============================================================================


def _transform(
    df: pl.DataFrame, year: int, era: str, manifest: TransformManifest
) -> pl.DataFrame:
    """Transform one bronze file (either era) to gold shape.

    Both eras share the same 7 working columns after uppercase + #RPT_NAME
    drop; era differences (sparsity, suppression regime) need no branching
    here because they only affect which rows/values exist, not their shape.
    """
    missing = REQUIRED_BRONZE_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Year {year} ({era}): bronze is missing required columns "
            f"{sorted(missing)}. Present: {sorted(df.columns)}"
        )

    # detail_level from the explicit bronze DETAIL_LVL_DESC; year as a
    # literal (already cross-checked against LONG_SCHOOL_YEAR upstream).
    df = df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.col("DETAIL_LVL_DESC").str.to_lowercase().alias("detail_level"),
    )

    # 2022-only quirk: School rows carrying the ALL sentinel duplicate the
    # school-coded rows of single-school charter districts — drop, guarded.
    df = _drop_school_all_sentinel_twins(df, year, manifest)

    # Normalize enrollment_period (Fall/Spring -> fall/spring), recorded so
    # the manifest unmapped guard catches any new bronze label.
    bronze_period = df["ENROLLMENT_PERIOD"]
    df = df.with_columns(
        pl.col("ENROLLMENT_PERIOD")
        .replace_strict(ENROLLMENT_PERIOD_MAP, default=SENTINEL_UNMATCHED)
        .alias("enrollment_period")
    )
    manifest.record_categorical(
        column="enrollment_period",
        map_dict=ENROLLMENT_PERIOD_MAP,
        bronze_series=bronze_period,
        gold_series=df["enrollment_period"],
    )

    # Normalize grade_level via the shared §16 normalizer (K, 1st..12th ->
    # k, 01..12). Record the effective map slice (the spellings actually
    # observed) so map_used stays reviewable; unmapped values still raise.
    bronze_grade = df["GRADE_LEVEL"]
    df = df.with_columns(normalize_grade_column("GRADE_LEVEL").alias("grade_level"))
    observed_grades = {
        str(v).strip().upper() for v in bronze_grade.drop_nulls().unique().to_list()
    }
    grade_map_slice = {
        g: GRADE_LEVEL_MAP[g] for g in observed_grades & GRADE_LEVEL_MAP.keys()
    }
    manifest.record_categorical(
        column="grade_level",
        map_dict=grade_map_slice,
        bronze_series=bronze_grade,
        gold_series=df["grade_level"],
    )

    # ID formatting: ALL sentinel -> NULL; otherwise zfill (3-char standard
    # district codes pad, 7-char charter/state-school codes pass through;
    # school codes pad to 4). Codes verified to join the dimensions.
    # Metric: TFS already NULL from read; cast strict=False so any other
    # non-numeric residue becomes NULL instead of crashing. True zeros in
    # 2011-2020 pass through as real Int64 zeros — never NULLed.
    df = df.with_columns(
        pl.when(pl.col("SCHOOL_DSTRCT_CD") == BRONZE_ALL_SENTINEL)
        .then(None)
        .otherwise(pl.col("SCHOOL_DSTRCT_CD").str.zfill(3))
        .alias("district_code"),
        pl.when(pl.col("INSTN_NUMBER") == BRONZE_ALL_SENTINEL)
        .then(None)
        .otherwise(pl.col("INSTN_NUMBER").str.zfill(4))
        .alias("school_code"),
        pl.col("ENROLLMENT_COUNT").cast(pl.Int64, strict=False).alias("num_students"),
    )

    return df.select(STANDARD_COLUMNS)


# =============================================================================
# Per-file dispatch
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read one bronze file, detect its era, and transform it to gold shape."""
    # All-string read: ID columns keep leading zeros, and the literal TFS
    # suppression marker becomes NULL via the shared SUPPRESSION_VALUES.
    df, loss = read_bronze_file(path, infer_schema_length=0, return_loss=True)
    filename_year = _extract_year_from_filename(path.name)
    manifest.record_read_loss(
        filename_year, path.name, loss["raw_rows"], loss["parsed_rows"]
    )

    # Uppercase all column names to absorb the 2012 `Enrollment_Count`
    # casing quirk before era detection ('#RPT_NAME' is unaffected).
    df = df.rename({c: c.upper() for c in df.columns})

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{path.name}: no era signature matched columns {df.columns}")

    # Era-1-only constant report-name column carries no information.
    if "#RPT_NAME" in df.columns:
        df = df.drop("#RPT_NAME")

    # Cross-check the filename year against LONG_SCHOOL_YEAR (one school
    # year per file); a mismatch means source drift, not a parse choice.
    long_years = df["LONG_SCHOOL_YEAR"].drop_nulls().unique().to_list()
    if len(long_years) != 1:
        raise ValueError(
            f"{path.name}: expected exactly one LONG_SCHOOL_YEAR, got {long_years}"
        )
    year = _parse_year_from_long_school_year(long_years[0])
    if year != filename_year:
        raise ValueError(
            f"{path.name}: filename year {filename_year} != LONG_SCHOOL_YEAR "
            f"{long_years[0]!r} ending year {year} — source drift."
        )

    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)

    if df.height == 0:
        logger.warning(f"{path.name}: bronze file is empty, skipping")
        return None

    logger.info(f"Processing {path.name} (year={year}, era={era}, rows={df.height:,})")
    return _transform(df, year, era, manifest)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for enrollment_by_grade_level."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file (read-loss accounted per file).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR):
        result = transform_file(path, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize dtypes across eras and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)
    logger.info(f"Combined {combined.height:,} rows across {len(all_dfs)} files")

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent counts
    # would mean an era-routing or sentinel-handling bug and must raise.
    # Verified zero duplicate keys in current bronze (post twin-drop).
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: each file is one non-overlapping school year, so dedup is
    # purely defensive. sort_col="num_students" prefers a row with a
    # reported count over a suppressed/NULL placeholder if a future
    # republication ever introduces duplicates.
    pre_dedup = dict(combined.group_by("year").len().iter_rows())
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=[
            "year",
            "district_code",
            "school_code",
            "enrollment_period",
            "grade_level",
        ],
        district_keys=["year", "district_code", "enrollment_period", "grade_level"],
        state_keys=["year", "enrollment_period", "grade_level"],
        sort_col="num_students",
    )
    post_dedup = dict(combined.group_by("year").len().iter_rows())
    for year in sorted(pre_dedup):
        removed = pre_dedup[year] - post_dedup.get(year, 0)
        if removed > 0:
            manifest.record_filtered(year, removed, "duplicate_rows_deduped")

    # 4. Geography nulling from the shared domain rules — defensive no-op
    # here (ALL sentinels already became NULL per-file) but keeps transform
    # and validator on one rule source. No §4b masks apply (non-negative
    # integer counts only; bronze verified all-digit strings).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Expected NULL-rate spike: 2011-2020 have 0% NULL num_students, while
    # the TFS years 2021-2022 (~58%) and 2023-2024 (~4%) exceed the median —
    # a documented consequence of the suppression-regime change.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning(
            f"NULL-rate spikes (expected, TFS regime change): {spike_result.details}"
        )
    validate_output(
        combined,
        required_non_null=["year", "detail_level", "enrollment_period", "grade_level"],
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
        f"Done. Bronze rows: {summary['total_bronze']:,}; "
        f"gold rows: {summary['total_gold']:,}; "
        f"years: {summary['years_processed']}"
    )

    # 7. ALWAYS LAST: validate the gold just written against the contract
    # just emitted. Raises GoldValidationError -> non-zero exit.
    run_topic_validation(GOLD_DIR)


def _emit_contract_and_readme(year_range: tuple[int, int]) -> None:
    """Emit the ODCS contract and gold README via ``write_data_dictionary``.

    Kept out of ``main()`` so the pipeline flow stays readable. The column
    declaration order MUST match STANDARD_COLUMNS minus ``detail_level``.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Student enrollment counts by grade level for every Georgia "
            "public school, school district, and the state, published by "
            "GOSA for school years 2010-11 through 2023-24. Each row is the "
            "total number of students enrolled in one grade (K through 12) "
            "at one entity in one enrollment-snapshot period — GaDOE counts "
            "enrollment twice per school year (Fall and Spring collection "
            "cycles), and both snapshots are preserved as distinct rows. "
            "There is no demographic breakdown: every row is a total count "
            "for its (year, geography, period, grade) cell."
        ),
        title="Enrollment by Grade Level",
        summary=(
            "Student enrollment counts by grade (K-12) for each Georgia "
            "school, district, and the state, per Fall/Spring snapshot, "
            "2011-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Ending calendar year of the school year (2024 = "
                    "2023-24). Parsed from the bronze LONG_SCHOOL_YEAR and "
                    "cross-checked against the filename year."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "nullable": True,
                "example": "601",
                "description": (
                    "GOSA district code (FK to districts dimension): "
                    "3-character zero-padded code for standard county/city "
                    "districts, or 7-character code for state-charter (782 "
                    "prefix), commission-charter (783 prefix), and state "
                    "school (799 prefix) entities — 7-character codes appear "
                    "in every year 2011-2024. NULL on state-level aggregate "
                    "rows (bronze sentinel 'ALL')."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "nullable": True,
                "example": "0103",
                "description": (
                    "4-character zero-padded GOSA school code (composite FK "
                    "to schools dimension with district_code; school codes "
                    "are not globally unique on their own). NULL on district- "
                    "and state-level aggregate rows (bronze sentinel 'ALL')."
                ),
            },
            {
                "name": "enrollment_period",
                "type": "string",
                "nullable": False,
                "example": "fall",
                "validValues": ["fall", "spring"],
                "short_description": (
                    "Enrollment snapshot within the school year: fall "
                    "(October) or spring (March); never sum across them."
                ),
                "description": (
                    "Enrollment-count snapshot within the school year: "
                    "'fall' (October collection) or 'spring' (March "
                    "collection). Both snapshots exist for nearly every "
                    "entity — queries wanting one headline count per year "
                    "must filter to a single period, never sum across them."
                ),
            },
            {
                "name": "grade_level",
                "type": "string",
                "nullable": False,
                "example": "03",
                "validValues": sorted(GRADE_LEVEL_VALUES),
                "short_description": (
                    "Grade of the students counted: 'k' for kindergarten, "
                    "'01'-'12' for grades 1-12; no pre-K or all-grades row."
                ),
                "description": (
                    "Grade level of the students counted: 'k' for "
                    "kindergarten, '01' through '12' for grades 1-12 "
                    "(canonical zero-padded codes per the shared grade "
                    "vocabulary). This source publishes no pre-K row and no "
                    "cross-grade aggregate row, so 'pk' and 'all' never "
                    "appear. Bronze spellings were K and 1st..12th."
                ),
            },
            {
                "name": "num_students",
                "type": "int64",
                "unit": "count",
                "key_metric": True,
                "nullable": True,
                "example": 80,
                "null_meaning": (
                    "Varies by year: never NULL in 2011-2020 (zeros are real "
                    "and preserved); in 2021-2022 NULL is a TFS suppression "
                    "that conflates true zeros with counts 1-9; in 2023-2024 "
                    "NULL means a suppressed <10 cell (and non-applicable "
                    "grade x entity cells are absent rows, not NULLs)."
                ),
                "short_description": (
                    "Number of students enrolled in this grade and period "
                    "at this entity."
                ),
                "description": (
                    "Number of students enrolled in this grade and period at "
                    "this entity. Three source regimes govern 0 vs NULL: "
                    "(1) 2011-2020 — no suppression; an explicit 0 is a true "
                    "zero (grade not served) and is preserved; (2) 2021-2022 "
                    "— the source replaces both true zeros and counts 1-9 "
                    "with 'TFS' (Too Few Students), stored as NULL here; "
                    "(3) 2023-2024 — TFS suppression continues AND rows for "
                    "non-applicable grade x entity combinations are no "
                    "longer emitted, roughly halving the row count per year."
                ),
            },
        ],
        source="Governor's Office of Student Achievement (GOSA)",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        # Extends (not replaces) the emitter's auto-derived prose: GOSA
        # publishes each detail level independently, so component sums do
        # not reconcile exactly to the published aggregates (data-review
        # finding; bronze-faithful source characteristic).
        limitations=(
            "Suppressed cells are NULL (not zero). State rows have NULL "
            "district_code and school_code. District rows have NULL "
            "school_code. State and district rows are independently "
            "published GOSA aggregates and may differ from the sum of their "
            "component rows by up to ~0.02%% (e.g., students enrolled in "
            "more than one district during a collection period); do not "
            "treat component sums as exact reconciliations."
        ),
        notes=[
            (
                "No demographic breakdown: every row is a total student "
                "count for its (year, geography, period, grade) cell, so "
                "the demographic column is omitted per "
                "data-cleaning-standards §5."
            ),
            (
                "Three suppression regimes: 2011-2020 publish every value "
                "exactly (including true zeros for grades an entity doesn't "
                "serve); 2021-2022 publish TFS for any count <10 (stored as "
                "NULL); 2023-2024 keep TFS and additionally stop emitting "
                "rows for non-applicable grade x entity combinations."
            ),
            (
                "Row-count asymmetry by design: 2011-2022 are dense (~65k "
                "rows/year — every present (entity, period) pair carries "
                "all 13 grade rows), 2023-2024 are sparse (~28.5k rows/year "
                "— only cells with data). The grain is unchanged; only the "
                "sparsity of no-enrollment rows differs."
            ),
            (
                "2022 bronze quirk: 52 School-level rows carrying the "
                "INSTN_NUMBER='ALL' sentinel for two single-school charter "
                "districts (7830627 Atlanta SMART Academy, 7830636 "
                "Northwest Classical Academy) were dropped — each exactly "
                "duplicates the matching school-coded row's count, and "
                "neither district publishes District-level rows in 2022. "
                "The drop is guarded by an exact-duplicate assertion."
            ),
            (
                "The 2012 file alone names the metric column "
                "Enrollment_Count (mixed case); all column names are "
                "uppercased after read to absorb the quirk."
            ),
            (
                "State-level sanity invariant: every year publishes exactly "
                "26 state rows (2 periods x 13 grades) — pinned as a "
                "quality check."
            ),
            (
                "Files are split by detail level per year partition: "
                "schools.parquet, districts.parquet, states.parquet."
            ),
        ],
        quality_checks=[
            {
                "name": "state_rows_exactly_26_per_year",
                "description": (
                    "Every year publishes exactly 26 state-level rows (2 "
                    "enrollment periods x 13 grades K-12). Fewer means data "
                    "loss; more means a dedup or sentinel-routing bug. State "
                    "rows are those with NULL district_code AND NULL "
                    "school_code. Verified to hold for all 14 years."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, COUNT(*) AS n FROM {object} "
                    "WHERE district_code IS NULL AND school_code IS NULL "
                    "GROUP BY year) t WHERE t.n <> 26"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_rows_13_grades_per_period",
                "description": (
                    "Each (year, enrollment_period) publishes exactly 13 "
                    "state-level grade rows (k, 01-12) — the per-period "
                    "refinement of the 26-per-year invariant, catching a "
                    "missing/duplicated grade even when the yearly total "
                    "still lands on 26."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, enrollment_period, COUNT(*) AS n "
                    "FROM {object} "
                    "WHERE district_code IS NULL AND school_code IS NULL "
                    "GROUP BY year, enrollment_period) t WHERE t.n <> 13"
                ),
                "mustBe": 0,
            },
            {
                "name": "dense_years_full_grade_set",
                "description": (
                    "Dense-era structural fact (2011-2022 files): every "
                    "(geography, enrollment_period) group carries exactly 13 "
                    "grade rows — the source emits all grades for every "
                    "present entity-period, with 0 or suppressed-NULL counts "
                    "for grades not served. Verified to hold for all 12 "
                    "dense years after the 2022 sentinel-twin drop. GROUP BY "
                    "treats NULL geography keys as equal, so one scan covers "
                    "state, district, and school levels. 2023-2024 are "
                    "sparse by design and excluded."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, school_code, "
                    "enrollment_period, COUNT(*) AS n FROM {object} "
                    "WHERE year <= 2022 "
                    "GROUP BY year, district_code, school_code, "
                    "enrollment_period) t WHERE t.n <> 13"
                ),
                "mustBe": 0,
            },
            {
                "name": "num_students_suppression_floor_from_2021",
                "description": (
                    "From 2021 onward the source suppresses any cell below "
                    "10 as TFS (stored as NULL), so no published "
                    "num_students under 10 can exist in 2021-2024 — a value "
                    "0-9 in those years means a suppression-handling or cast "
                    "regression. Verified: gold minimum is 10 in every "
                    "suppression-era year."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE year >= 2021 AND num_students IS NOT NULL "
                    "AND num_students < 10"
                ),
                "mustBe": 0,
            },
            {
                "name": "num_students_never_null_before_2021",
                "description": (
                    "2011-2020 bronze has no suppression and no blank cells "
                    "(every value is a digit string, including true zeros), "
                    "so a NULL num_students in those years means a cast or "
                    "read regression. TFS suppression begins in 2021."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE year <= 2020 AND num_students IS NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "district_code_length_3_or_7",
                "description": (
                    "Non-NULL district_code is a 3-character standard code "
                    "or a 7-character charter/state-school code — any other "
                    "length means zfill or sentinel handling regressed."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE district_code IS NOT NULL "
                    "AND LENGTH(district_code) NOT IN (3, 7)"
                ),
                "mustBe": 0,
            },
            {
                "name": "school_code_length_4",
                "description": (
                    "Non-NULL school_code is always zero-padded to exactly "
                    "4 characters, matching the schools dimension key."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE school_code IS NOT NULL AND LENGTH(school_code) <> 4"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
