"""Transform bronze georgia_milestones_end_of_course_lexile to gold.

Source: Governor's Office of Student Achievement (GOSA) — Georgia Milestones
End-of-Course (EOC) Lexile assessment results. For each (entity x subject)
combination the bronze file reports five Lexile-distribution measures derived
from Georgia's two English Language Arts EOC courses: 9th Grade Literature
and Composition and American Literature and Composition. Coverage spans
school years 2014-15 through 2023-24 (9 files; 2019-20 absent — EOC testing
suspended due to COVID-19).

Key data-model decisions (from bronze-data-structure.md, re-verified against
all 9 bronze files where noted):

- **Single era (2015-2024).** Every file shares the same 12-column tidy-long
  header. Era detection still runs by column signature so schema drift fails
  loudly instead of silently NULLing metrics.

- **Course-based reporting — no grade_level column.** Verified: bronze has
  no grade column anywhere (unlike the EOG Lexile sibling, which reports by
  grade). The row axis is the EOC course (`SUBJECT_CODE`), so gold carries
  `subject` only.

- **No demographic breakdown.** Verified: bronze has no subgroup column;
  every row is implicitly "All Students". Per data-cleaning-standards §5 the
  `demographic` column is omitted entirely (it would be constant `all`).

- **Detail levels from the explicit DETAIL_LEVEL column,** cross-checked
  against the `"All"` sentinels (title case — NOT the uppercase `"ALL"` other
  GOSA topics use). Verified in all 9 files with zero exceptions: State Level
  rows have district AND school sentinels, District Level rows have only the
  school sentinel, School Level rows have neither. A mismatch is a hard stop
  (bronze drift), not a silent reclassification.

- **Metrics map straight across** (no unpivot — bronze is already tidy):
      TOTAL_STUDENTS_TESTED       -> num_tested                      (Int64)
      STUDENTS_WITH_LEXILE        -> num_with_lexile                 (Int64)
      NO_LEXILE_SCORE             -> num_without_lexile              (Int64)
      LEXILE_ON_OR_ABOVE_MIDPOINT -> num_at_or_above_lexile_midpoint (Int64)
      AVG_LEXILE_SCORE            -> avg_lexile_score                (Float64)
  None are percentages — §4 (0-1 rescaling) does not apply.
  `num_with_lexile` / `num_without_lexile` follow the §16 tiebreaker
  (condition counts use `num_*`, and these two are §16's own examples).

- **num_without_lexile is a retained source count, NOT derivable.** Verified:
  of the 140 rows (all years) where tested, with-Lexile, and without-Lexile
  are all numeric, 45 disagree with the arithmetic complement
  `num_tested - num_with_lexile` (largest gap 99 students, in 2021). The
  column is GOSA's independently published count and carries information the
  other measures cannot reconstruct, so it is kept — and NO
  with+without=tested partition check is authored, because the source
  demonstrably violates it. This corrects the structure doc's "typically
  recovers the same number" claim (see doc amendment note there).

- **Cross-column invariants verified with zero violations across all 9
  files, authored as quality checks (§15b):**
    1. num_with_lexile <= num_tested (subset).
    2. num_at_or_above_lexile_midpoint <= num_with_lexile (subset of the
       Lexile-receiving population, NOT of num_tested).
    3. avg_lexile_score reported <=> num_with_lexile reported (perfect
       biconditional — both are statistics of the same population).
    4. num_at_or_above_lexile_midpoint reported => num_with_lexile reported
       (one-directional: midpoint is the more heavily suppressed column).
    5. num_with_lexile reported => num_tested reported (one-directional:
       exactly 2 bronze rows have tested reported with with-Lexile
       suppressed — 2015 Polk County school 0207 and 2016 Bleckley County
       school 0115 — so only this direction is provable).
    6. The 9th-grade course never appears after 2021 (real curriculum
       change; GOSA moved 9th-grade ELA off the EOC program).

- **No §4b mask.** avg_lexile_score observed range is 707.0-1679.3 across
  all years/levels — comfortably inside the contract's [0, 2000] guard; no
  negative counts exist. Nothing impossible to NULL; no rows filtered,
  masked, or reclassified.

- **LEXILE_ON_OR_ABOVE_MIDPOINT is a count, not a percentage.** Verified at
  the 2024 state row: 69,660 of 132,835 students with a Lexile (52.4%).
  Derive a share by dividing by num_with_lexile (not num_tested).

- **Missing-value regimes differ by era**: 2015-2019 files contain ZERO
  `TFS` strings — missingness is genuinely blank metric cells (419 all-blank
  metric rows: 82/77/84/87/89 by year); 2021-2024 use the literal `TFS`
  (Too Few Students) marker. Both become NULL: read_bronze_file nulls TFS,
  and strict=False casts absorb blank residue. num_without_lexile is
  ~94-99% NULL in every year — a real data characteristic (few students
  fail to receive a Lexile), not a bug.

- **ID formatting**: district_code zfill(3) — 7-digit state-charter codes
  (7820xxx/7830xxx) pass through unchanged, never truncated; school_code
  zfill(4) reconciles the 2015-2019 unpadded 3/4-char INSTN_NUMBER with the
  2021-2024 zero-padded form so one physical school keys identically across
  years. The `"All"` sentinel becomes NULL before padding.

- **Year** derives from the filename and is cross-checked against the
  file's single SCHOOL_YEAR value (always equal; verified). 2020 is
  genuinely absent (COVID-19) — no partition is emitted. 2021 is a
  COVID-impacted partial year (~50% of typical rows; the 9th-grade course
  has only 84 rows, mostly district/state level).

- **Dedup tie-break**: each bronze file is a distinct year with no
  within-file duplicate natural keys (verified per file), so
  deduplicate_by_detail_level is a pure safety net. sort_col="num_tested"
  prefers a reported, larger-count row over a suppressed placeholder should
  a republish ever introduce a duplicate. assert_no_natural_key_collisions
  runs first so a divergent duplicate fails loudly instead of being
  silently resolved.

Natural PK: (year, district_code, school_code, subject), with NULL
geography at aggregate detail levels.
"""

import logging
from pathlib import Path

import polars as pl

from src.utils.metadata import write_data_dictionary
from src.utils.readers import (
    extract_year_from_filename,
    list_bronze_files,
    read_bronze_file,
)
from src.utils.subjects import apply_subject_normalization
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

TOPIC = "georgia_milestones_end_of_course_lexile"
BRONZE_DIR = Path("data/bronze/education/gosa/georgia_milestones_end_of_course_lexile")
GOLD_DIR = Path("data/gold/education/georgia_milestones_end_of_course_lexile")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Bronze sentinel marking aggregate rows in SCHOOL_DSTRCT_CD / INSTN_NUMBER.
# This topic uses title-case "All" (NOT the uppercase "ALL" of sibling GOSA
# topics like the EOC assessment files) — verified in all 9 files.
BRONZE_ALL_SENTINEL = "All"

# Bronze DETAIL_LEVEL literals -> gold detail_level values. Gold uses the
# singular forms deduplicate_by_detail_level filters on; export_to_parquet
# maps them to the plural filenames (states/districts/schools.parquet) and
# null_aggregate_geography accepts either form of the domain rule keys.
DETAIL_LEVEL_MAP: dict[str, str] = {
    "State Level": "state",
    "District Level": "district",
    "School Level": "school",
}

# Bronze SUBJECT_CODE -> gold `subject` (§16 canonical snake_case). Only two
# values appear across all 9 files. The 9th-grade course phases out after
# 2021 (a real curriculum change, kept for historical years); American
# Literature is the sole subject 2022-2024.
SUBJECT_MAP: dict[str, str] = {
    "9th Grade Literature and Composition": "9th_grade_literature_and_composition",
    "American Literature and Composition": "american_literature_and_composition",
}

# Single-era column signature — detection by columns (never year ranges) so
# unexpected schema drift in a future file fails loudly.
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_1_2015_2024": [
        "SCHOOL_YEAR",
        "DETAIL_LEVEL",
        "SCHOOL_DSTRCT_CD",
        "INSTN_NUMBER",
        "SUBJECT_CODE",
        "TOTAL_STUDENTS_TESTED",
        "STUDENTS_WITH_LEXILE",
        "LEXILE_ON_OR_ABOVE_MIDPOINT",
        "NO_LEXILE_SCORE",
        "AVG_LEXILE_SCORE",
    ],
}

# Gold fact column order per §1: year, geography keys, categoricals, metrics.
# No demographic (constant "All Students") and no grade_level (course-based
# reporting). detail_level is carried for dedup / geography nulling / export
# splitting, then dropped by export_to_parquet.
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "subject",
    "num_tested",
    "num_with_lexile",
    "num_without_lexile",
    "num_at_or_above_lexile_midpoint",
    "avg_lexile_score",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "subject": pl.Utf8,
    "num_tested": pl.Int64,
    "num_with_lexile": pl.Int64,
    "num_without_lexile": pl.Int64,
    "num_at_or_above_lexile_midpoint": pl.Int64,
    "avg_lexile_score": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = [
    "num_tested",
    "num_with_lexile",
    "num_without_lexile",
    "num_at_or_above_lexile_midpoint",
    "avg_lexile_score",
]

# Natural key for the collision guard. detail_level is included so the
# pre-nulled geography patterns (state rows already NULL/NULL) cannot alias
# across levels.
NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "detail_level",
    "subject",
]


# =============================================================================
# Helpers
# =============================================================================


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


def _assert_school_year_matches(df: pl.DataFrame, year: int, label: str) -> None:
    """Cross-check the file's single SCHOOL_YEAR against the filename year.

    Every row in every bronze file carries SCHOOL_YEAR equal to the filename
    year (the ending calendar year of the school year; verified across all 9
    files). A mismatch signals bronze drift — fail loudly rather than emit a
    silently mislabeled year of gold data.
    """
    unique_years = df["SCHOOL_YEAR"].drop_nulls().unique().to_list()
    if len(unique_years) != 1:
        raise ValueError(
            f"{label}: expected exactly one SCHOOL_YEAR value, got {unique_years!r}"
        )
    if int(unique_years[0]) != year:
        raise ValueError(
            f"{label}: filename year {year} != SCHOOL_YEAR {unique_years[0]!r} "
            f"— source drift, re-check bronze."
        )


def _assert_sentinels_match_detail_level(df: pl.DataFrame, label: str) -> None:
    """Hard-stop if the "All" sentinels disagree with the declared DETAIL_LEVEL.

    Verified across all 9 bronze files with zero exceptions: State Level rows
    carry the sentinel in both geography columns, District Level rows only in
    INSTN_NUMBER, School Level rows in neither. A disagreement would mean an
    aggregate row is about to be keyed as a real entity (or vice versa), so
    it is bronze drift worth a crash, not a warning.
    """
    is_all_district = pl.col("SCHOOL_DSTRCT_CD") == BRONZE_ALL_SENTINEL
    is_all_school = pl.col("INSTN_NUMBER") == BRONZE_ALL_SENTINEL
    bad = df.filter(
        ((pl.col("DETAIL_LEVEL") == "State Level") & ~(is_all_district & is_all_school))
        | (
            (pl.col("DETAIL_LEVEL") == "District Level")
            & ~(~is_all_district & is_all_school)
        )
        | (
            (pl.col("DETAIL_LEVEL") == "School Level")
            & ~(~is_all_district & ~is_all_school)
        )
    )
    if bad.height > 0:
        sample = bad.select(["DETAIL_LEVEL", "SCHOOL_DSTRCT_CD", "INSTN_NUMBER"])
        raise ValueError(
            f"{label}: {bad.height} row(s) where the 'All' sentinels disagree "
            f"with DETAIL_LEVEL. Sample:\n{sample.head(5)}"
        )


# =============================================================================
# Era 1 (2015-2024): single tidy-long EOC Lexile fact
# =============================================================================


def _transform_era1(
    df: pl.DataFrame,
    year: int,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Transform one bronze file into the gold fact-table shape.

    All 9 files share the same 12-column schema; the only per-year quirks
    are INSTN_NUMBER zero-padding (handled by zfill) and subject coverage
    (handled by the value set itself).
    """
    _require_columns(df, ERA_SIGNATURES["era_1_2015_2024"], f"year {year}")
    _assert_school_year_matches(df, year, f"year {year}")
    _assert_sentinels_match_detail_level(df, f"year {year}")

    # Detail level from the explicit bronze column (sentinels were verified
    # consistent above). Unmapped literals become the sentinel so the
    # manifest's unmapped guard raises rather than silently emitting it.
    bronze_detail = df["DETAIL_LEVEL"]
    df = df.with_columns(
        pl.col("DETAIL_LEVEL")
        .replace_strict(DETAIL_LEVEL_MAP, default="99999999")
        .alias("detail_level")
    )
    manifest.record_categorical(
        column="detail_level",
        map_dict=DETAIL_LEVEL_MAP,
        bronze_series=bronze_detail,
        gold_series=df["detail_level"],
    )

    # Geography keys: the title-case "All" sentinel becomes NULL before
    # padding so the literal string is never zfilled. zfill(3) passes
    # 7-digit state-charter codes (7820xxx/7830xxx) through unchanged —
    # never truncate; zfill(4) reconciles the 2015-2019 unpadded
    # INSTN_NUMBER (e.g. `103`) with the 2021-2024 zero-padded form (`0103`).
    df = df.with_columns(
        pl.when(pl.col("SCHOOL_DSTRCT_CD") == BRONZE_ALL_SENTINEL)
        .then(None)
        .otherwise(pl.col("SCHOOL_DSTRCT_CD").cast(pl.Utf8).str.zfill(3))
        .alias("district_code"),
        pl.when(pl.col("INSTN_NUMBER") == BRONZE_ALL_SENTINEL)
        .then(None)
        .otherwise(pl.col("INSTN_NUMBER").cast(pl.Utf8).str.zfill(4))
        .alias("school_code"),
        pl.lit(year).cast(pl.Int32).alias("year"),
    )

    # Subject: topic-local snake_case map (unmapped -> sentinel so the
    # manifest guard raises), then the shared spelling-variant backstop —
    # a no-op on current data since SUBJECT_MAP already emits §16 canonical
    # values, but it catches future GOSA label drift.
    bronze_subject = df["SUBJECT_CODE"]
    df = df.with_columns(
        pl.col("SUBJECT_CODE")
        .replace_strict(SUBJECT_MAP, default="99999999")
        .alias("subject")
    )
    df = df.with_columns(apply_subject_normalization("subject").alias("subject"))
    manifest.record_categorical(
        column="subject",
        map_dict=SUBJECT_MAP,
        bronze_series=bronze_subject,
        gold_series=df["subject"],
    )

    # Metrics: counts to Int64, the Lexile measure to Float64. None are
    # percentages — no /100. strict=False nulls any non-numeric residue:
    # the 2015-2019 blank cells (no TFS exists in those files) and any TFS
    # not already nulled by read_bronze_file's suppression handling.
    df = df.with_columns(
        pl.col("TOTAL_STUDENTS_TESTED")
        .cast(pl.Int64, strict=False)
        .alias("num_tested"),
        pl.col("STUDENTS_WITH_LEXILE")
        .cast(pl.Int64, strict=False)
        .alias("num_with_lexile"),
        # NO_LEXILE_SCORE is GOSA's independently published count, NOT the
        # complement num_tested - num_with_lexile (45 of 140 numeric rows
        # disagree, by up to 99 students) — retained, never derived.
        pl.col("NO_LEXILE_SCORE")
        .cast(pl.Int64, strict=False)
        .alias("num_without_lexile"),
        pl.col("LEXILE_ON_OR_ABOVE_MIDPOINT")
        .cast(pl.Int64, strict=False)
        .alias("num_at_or_above_lexile_midpoint"),
        pl.col("AVG_LEXILE_SCORE")
        .cast(pl.Float64, strict=False)
        .alias("avg_lexile_score"),
    )

    return df.select(STANDARD_COLUMNS)


# =============================================================================
# File dispatcher
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read one bronze file, detect its era, and route to the era handler."""
    # infer_schema_length=0 forces all-Utf8 (§4.3b) so zero-padded 2021-2024
    # school codes keep their leading zeros and every metric is cast
    # explicitly downstream with strict=False.
    df, loss = read_bronze_file(path, infer_schema_length=0, return_loss=True)

    year = extract_year_from_filename(path.name)
    if year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")
    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(
            f"{path.name}: no era signature matched columns {df.columns[:15]}..."
        )

    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)

    if df.height == 0:
        logger.warning(f"Year {year}: bronze file is empty, skipping: {path.name}")
        return None

    logger.info(f"Processing {path.name} (year={year}, era={era}, rows={df.height:,})")

    return _transform_era1(df, year, manifest)


# =============================================================================
# Pipeline orchestration
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for EOC Lexile scores."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform each bronze file (read-loss accounted per file).
    # 9 files: 2015-2019 and 2021-2024 (2020 absent — COVID-19).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR):
        result = transform_file(path, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize columns/dtypes across years and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs, how="vertical")
    logger.info(f"Combined all years: {combined.height:,} rows")

    # 3. Collision guard BEFORE dedup: a duplicate key with divergent metrics
    # is an alias/aggregation bug and must raise, never be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: each file is a distinct year with no within-file duplicate
    # keys (verified per file) — dedup is a pure safety net. sort_col=
    # "num_tested" prefers a reported, larger-count row over a suppressed
    # placeholder should a republish ever introduce a duplicate.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code", "subject"],
        district_keys=["year", "district_code", "subject"],
        state_keys=["year", "subject"],
        sort_col="num_tested",
    )

    # 4. Geography nulling — shared rule source keeps transform and
    # validator in lockstep. No §4b mask: avg_lexile_score observed
    # 707.0-1679.3 (inside [0, 2000]) and no negative counts exist
    # (see module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. num_without_lexile is ~94-99% NULL in every year
    # (GOSA suppresses it almost everywhere) — uniform, so no spike expected;
    # 2021 metric NULL rates run higher (COVID-impacted partial coverage)
    # but stay under the 20pp spike threshold.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning(f"NULL-rate spikes: {spike_result.details}")
    validate_output(combined, required_non_null=["year", "detail_level", "subject"])

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
        f"Gold rows: {summary['total_gold']:,}; "
        f"Years: {summary['years_processed']}"
    )

    # 7. ALWAYS LAST: validate the gold just written against the contract
    # just emitted. Raises GoldValidationError -> non-zero exit.
    run_topic_validation(GOLD_DIR)


def _emit_contract_and_readme(year_range: tuple[int, int]) -> None:
    """Emit the ODCS contract and gold README via ``write_data_dictionary``.

    The column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level`` — the contract's properties (and the validator's
    schema check) follow it.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Governor's Office of Student Achievement (GOSA) Georgia "
            "Milestones End-of-Course (EOC) Lexile assessment dataset. "
            "Reports Lexile reading-measure distributions derived from "
            "Georgia's two English Language Arts EOC courses (9th Grade "
            "Literature and Composition, American Literature and "
            "Composition). Each row is one (entity x subject) combination "
            "with five measures: total students tested, students with a "
            "Lexile measure, students without a Lexile score, students with "
            "Lexile at or above the grade-level midpoint (the 'on-track "
            "reader' threshold), and the average Lexile measure. Coverage "
            "is school years 2014-15 through 2023-24 (2019-20 absent — EOC "
            "testing suspended due to COVID-19) at state, district, and "
            "school detail levels. No demographic breakdown — every row is "
            "implicitly 'All Students'."
        ),
        title="Georgia Milestones EOC Lexile Reading Scores",
        summary=(
            "Lexile reading-measure distributions from Georgia's two ELA "
            "End-of-Course exams by school, district, and state, 2015-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Ending calendar year of the school year (e.g., 2024 = "
                    "2023-24). Derived from the filename and cross-checked "
                    "against the bronze SCHOOL_YEAR column. 2020 is absent "
                    "(EOC testing suspended during COVID-19 closures)."
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
                "example": "0100",
                "description": (
                    "GOSA school code, zero-padded to 4 characters "
                    "(composite FK to schools dimension with district_code; "
                    "not globally unique on its own). NULL on district- and "
                    "state-level rows."
                ),
            },
            {
                "name": "subject",
                "type": "string",
                "nullable": False,
                "example": "american_literature_and_composition",
                "validValues": sorted(set(SUBJECT_MAP.values())),
                "short_description": (
                    "Which ELA End-of-Course exam the row covers: 9th Grade "
                    "Literature (through 2021) or American Literature."
                ),
                "description": (
                    "ELA EOC course this row measures, snake_case canonical. "
                    "9th_grade_literature_and_composition is present "
                    "2015-2021 (only 84 rows in 2021) and retired after 2021 "
                    "— a real curriculum change (GOSA moved 9th-grade ELA "
                    "off the EOC program), not a relabeling. "
                    "american_literature_and_composition is present every "
                    "year and is the sole subject from 2022."
                ),
            },
            {
                "name": "num_tested",
                "type": "int64",
                "unit": "count",
                "example": 287,
                "null_meaning": (
                    "2015-2019: genuinely blank source cell; 2021-2024: "
                    "GOSA TFS ('Too Few Students') suppression."
                ),
                "description": (
                    "Count of students who took the subject's EOC. Bronze "
                    "TOTAL_STUDENTS_TESTED. NULL when the source cell is "
                    "blank (2015-2019 — those files contain no TFS) or "
                    "TFS-suppressed (2021-2024); 4-18%% of rows depending "
                    "on year."
                ),
            },
            {
                "name": "num_with_lexile",
                "type": "int64",
                "unit": "count",
                "metric_component": "denominator",
                "example": 287,
                "null_meaning": (
                    "2015-2019: genuinely blank source cell; 2021-2024: "
                    "GOSA TFS suppression."
                ),
                "description": (
                    "Count of tested students whose EOC produced a usable "
                    "Lexile measure — equal to or slightly below num_tested, "
                    "never above it (enforced). Reported exactly when "
                    "avg_lexile_score is reported (enforced biconditional). "
                    "Bronze STUDENTS_WITH_LEXILE; NULL when blank "
                    "(2015-2019) or TFS-suppressed (2021-2024). In "
                    "all years only 2 rows have num_tested reported with "
                    "this column missing (2015 Polk County school 0207; "
                    "2016 Bleckley County school 0115 — blank cells, not "
                    "TFS)."
                ),
            },
            {
                "name": "num_without_lexile",
                "type": "int64",
                "unit": "count",
                "example": 30,
                "null_meaning": (
                    "Blank source cell (2015-2019) or GOSA TFS suppression "
                    "(2021-2024) — ~94-99%% of rows in every year; only "
                    "1-37 rows per year carry a numeric value."
                ),
                "description": (
                    "Count of tested students who did NOT receive a usable "
                    "Lexile measure, as published by GOSA (bronze "
                    "NO_LEXILE_SCORE). This is an independently reported "
                    "source count, NOT the arithmetic complement num_tested "
                    "- num_with_lexile: of the 140 rows (all years) where "
                    "all three counts are numeric, 45 disagree with that "
                    "derivation (by up to 99 students), so the published "
                    "column is retained rather than derived and no "
                    "with+without=tested check is enforced. Heavily "
                    "suppressed (~94-99%% NULL)."
                ),
            },
            {
                "name": "num_at_or_above_lexile_midpoint",
                "type": "int64",
                "unit": "count",
                "example": 65,
                "null_meaning": (
                    "Blank source cell (2015-2019) or GOSA TFS suppression "
                    "(2021-2024) — the most-missing count after "
                    "num_without_lexile (~10-29%% of rows by year)."
                ),
                "description": (
                    "Count of students whose Lexile measure was at or above "
                    "the midpoint of the course's Lexile range (GOSA's "
                    "'on-track reader' / grade-level threshold: 1050L for "
                    "9th Grade Literature, 1185L for American Literature). "
                    "A raw COUNT, not a percentage (2024 state row: 69,660 "
                    "of 132,835 students with a Lexile = 52.4%%) — derive a "
                    "share by dividing by num_with_lexile (the population "
                    "with a valid Lexile), not num_tested. Never exceeds "
                    "num_with_lexile (enforced). Bronze "
                    "LEXILE_ON_OR_ABOVE_MIDPOINT; NULL when suppressed."
                ),
            },
            {
                "name": "avg_lexile_score",
                "type": "float64",
                "unit": "score",
                "value_min": 0,
                "value_max": 2000,
                "key_metric": True,
                "example": 1119.9,
                "short_description": (
                    "Average Lexile reading measure (on the natural Lexile "
                    "scale, not a percentage) among students who received one."
                ),
                "null_meaning": (
                    "Blank source cell (2015-2019) or GOSA TFS suppression "
                    "(2021-2024) — exactly when num_with_lexile is missing."
                ),
                "description": (
                    "Average Lexile reading measure among students who "
                    "received one, reported to one decimal place. The "
                    "Lexile reader scale runs from below 0L (BR / Beginning "
                    "Reader) to above 2000L; the contract enforces 0-2000 "
                    "for these entity-level averages (observed range "
                    "707.0-1679.3 across all years and detail levels — a "
                    "below-0 BR average is unreachable for an EOC cohort). "
                    "NOT a percentage — no 0-1 rescaling; the natural "
                    "Lexile scale is preserved. Reported exactly when "
                    "num_with_lexile is reported (enforced biconditional). "
                    "Bronze AVG_LEXILE_SCORE; NULL when suppressed."
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
                "Single bronze era (2015-2024): every file shares the same "
                "12-column tidy-long schema. The only cross-year quirks are "
                "(a) INSTN_NUMBER zero-padding (unpadded 3/4-char in "
                "2015-2019, 4-char zero-padded in 2021-2024 — normalized to "
                "zfill(4) in gold) and (b) subject coverage (the 9th-grade "
                "course drops out after 2021)."
            ),
            (
                "Missing year: 2020 (school year 2019-20) — EOC testing was "
                "suspended statewide due to COVID-19 closures. Gold simply "
                "has no rows for 2020."
            ),
            (
                "2021 is a COVID-impacted partial year: ~50% of a typical "
                "year's rows (747 vs ~1,480), and the 9th-grade course has "
                "only 84 rows (vs 663 for American Literature) — mostly "
                "district/state level with sparse school coverage."
            ),
            (
                "Missing-value regimes differ by era: 2015-2019 files "
                "contain ZERO TFS strings — missingness is genuinely blank "
                "metric cells (419 all-blank metric rows: 82/77/84/87/89 by "
                "year); 2021-2024 use the literal TFS (Too Few Students) "
                "marker. Both become NULL in gold. num_without_lexile is "
                "~94-99% NULL in every year — a real characteristic of the "
                "source (few students fail to receive a Lexile), not a "
                "defect."
            ),
            (
                "Retained source count: num_without_lexile (bronze "
                "NO_LEXILE_SCORE) is GOSA's independently published count "
                "and does NOT equal num_tested - num_with_lexile for 45 of "
                "the 140 fully-numeric rows (differences up to 99 "
                "students). It cannot be reconstructed from the other "
                "measures, so it is carried to gold — and no "
                "with+without=tested partition check is authored, because "
                "the source demonstrably violates it."
            ),
            (
                "num_at_or_above_lexile_midpoint is a COUNT, not a "
                "percentage. To derive the share at or above the midpoint, "
                "divide by num_with_lexile (the population with a valid "
                "Lexile), not num_tested."
            ),
            (
                "avg_lexile_score is the Lexile measure itself (observed "
                "707.0-1679.3) — not a percentage; never rescaled."
            ),
            (
                "No demographic breakdown and no grade_level: every bronze "
                "row is implicitly 'All Students' and reporting is by EOC "
                "course (not grade), so the gold fact table carries "
                "`subject` as its only categorical. The EOG Lexile sibling "
                "topic is grade-based and does carry grade_level."
            ),
            (
                "ID formatting: district_code zfill(3) with 7-digit "
                "state-charter codes (7820xxx/7830xxx) passed through "
                "unchanged; school_code zfill(4) reconciles the 2015-2019 "
                "unpadded INSTN_NUMBER (e.g. 103) with the 2021-2024 "
                "zero-padded form (0103) so one physical school keys "
                "identically across years."
            ),
            (
                "Files are partitioned by year and split by detail level: "
                "schools.parquet, districts.parquet, states.parquet."
            ),
            (
                "Disambiguation: the sibling topics georgia_milestones_"
                "end_of_course_by_grade_level (achievement levels) "
                "and georgia_milestones_end_of_grade_lexile "
                "(EOG/grade-based Lexile) measure different things. Gold "
                "for this topic is built only from the "
                "georgia_milestones_end_of_course_lexile/ "
                "bronze directory."
            ),
        ],
        quality_checks=[
            {
                "name": "lexile_population_within_tested",
                "description": (
                    "num_with_lexile counts a subset of tested students, so "
                    "it must not exceed num_tested where both are present "
                    "(verified in bronze 2015-2024 with zero violations)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "num_with_lexile IS NOT NULL "
                    "AND num_tested IS NOT NULL "
                    "AND num_with_lexile > num_tested"
                ),
                "mustBe": 0,
            },
            {
                "name": "no_lexile_count_within_tested",
                "description": (
                    "num_without_lexile counts a subset of tested students, "
                    "so it must not exceed num_tested where both are "
                    "present (verified in bronze 2015-2024: zero violations "
                    "across all 140 fully-observable rows). Completes the "
                    "subset-check family alongside num_with_lexile and the "
                    "midpoint count."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "num_without_lexile IS NOT NULL "
                    "AND num_tested IS NOT NULL "
                    "AND num_without_lexile > num_tested"
                ),
                "mustBe": 0,
            },
            {
                "name": "midpoint_count_within_lexile_population",
                "description": (
                    "num_at_or_above_lexile_midpoint counts a subset of the "
                    "students with a Lexile measure, so it must not exceed "
                    "num_with_lexile where both are present (verified in "
                    "bronze 2015-2024 with zero violations)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "num_at_or_above_lexile_midpoint IS NOT NULL "
                    "AND num_with_lexile IS NOT NULL "
                    "AND num_at_or_above_lexile_midpoint > num_with_lexile"
                ),
                "mustBe": 0,
            },
            {
                "name": "avg_lexile_reported_iff_lexile_population_reported",
                "description": (
                    "avg_lexile_score and num_with_lexile are statistics of "
                    "the same population (students who received a Lexile) "
                    "and are suppressed together: each is NULL exactly when "
                    "the other is (verified in bronze 2015-2024 with zero "
                    "violations in either direction)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(avg_lexile_score IS NULL) != (num_with_lexile IS NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "midpoint_reported_implies_lexile_population_reported",
                "description": (
                    "A reported num_at_or_above_lexile_midpoint implies its "
                    "denominator population num_with_lexile is reported "
                    "(verified in bronze 2015-2024 with zero violations; "
                    "the converse does not hold — the midpoint count is "
                    "suppressed more often)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "num_at_or_above_lexile_midpoint IS NOT NULL "
                    "AND num_with_lexile IS NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "lexile_population_reported_implies_tested_reported",
                "description": (
                    "A reported num_with_lexile implies num_tested is "
                    "reported (verified in bronze 2015-2024 with zero "
                    "violations; the converse has exactly 2 source "
                    "exceptions — 2015 Polk County school 0207 and 2016 "
                    "Bleckley County school 0115 — so only this direction "
                    "is enforced)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "num_with_lexile IS NOT NULL "
                    "AND num_tested IS NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "ninth_grade_subject_retired_after_2021",
                "description": (
                    "The 9th Grade Literature and Composition EOC was "
                    "retired after 2021 (GOSA moved 9th-grade ELA off the "
                    "EOC program) — it must never appear in later years "
                    "(verified: 2022-2024 bronze contains only American "
                    "Literature rows)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "subject = '9th_grade_literature_and_composition' "
                    "AND year > 2021"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
