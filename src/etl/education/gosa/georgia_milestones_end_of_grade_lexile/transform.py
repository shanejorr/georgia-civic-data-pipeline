"""Transform bronze georgia_milestones_end_of_grade_lexile to gold.

Source: Governor's Office of Student Achievement (GOSA) — Lexile reading-score
outcomes for students taking the Georgia Milestones End-of-Grade (EOG) English
Language Arts assessment in grades 3-8. Each bronze row is one (entity x
grade) cell at one of three detail levels (state / district / school) with
five measures: students tested, students who received a Lexile measure,
students at or above the grade-band "stretch midpoint", students without a
Lexile score, and the average Lexile measure. Coverage: school years 2014-15
through 2023-24 (9 files; 2019-20 absent — EOG testing suspended, COVID-19).

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Single bronze era (2015-2024).** All 9 files share the identical
  12-column header. Era detection still runs by column signature so schema
  drift fails loudly instead of silently NULLing metrics. The only cross-year
  difference is dtype/suppression semantics: 2015-2019 metric fields are pure
  numerics (every 2015-2019 file carries genuinely empty metric fields —
  126-143 per metric column per year: 2015: 129-131, 2016: 126-127,
  2017: 128, 2018: 136-137, 2019: 141-143); 2021-2024 encode
  small-cell suppression as the literal string ``TFS``. Reading all-Utf8
  (``infer_schema_length=0``) + ``read_bronze_file``'s suppression nulling +
  non-strict casts handles both regimes uniformly (§4.3b).
- **Year = filename year, cross-checked.** Every file carries exactly one
  SCHOOL_YEAR value equal to the filename year (verified across all 9 files);
  a mismatch raises (source-drift guard).
- **Detail level from the explicit DETAIL_LEVEL column** ("State Level" /
  "District Level" / "School Level"); aggregate rows mark geography with the
  literal title-case ``"All"`` (NOT the uppercase ``"ALL"`` other GOSA topics
  use). Sentinels become NULL geography keys before zfill so a padded
  sentinel can never masquerade as a real code.
- **ID formatting.** ``district_code`` zfill(3) (7-digit state-charter codes
  pass through unchanged); ``school_code`` zfill(4). Verified in raw CSV
  bytes: every non-"All" INSTN_NUMBER is exactly 4 chars in every year, so
  the zfills are defensive no-ops here.
- **grade_level** via the shared ``normalize_grade_column``. Raw CSV stores
  the grade as a quoted, zero-padded 2-char string ("03"-"08") in every year
  (verified in raw bytes; schema inference would parse it as integer 3-8,
  which is what the structure doc's dtype tables reflect).
- **Fixed ``subject`` constant.** Bronze has no subject column — every Lexile
  measure derives from the EOG English Language Arts assessment. Per §16 the
  fact table still emits ``subject = "english_language_arts"`` on every row
  (piped through the shared ``apply_subject_normalization``, a no-op) so API
  consumers can filter Milestones topics by subject uniformly. The manifest
  records this as a categorical with a synthetic one-element bronze series
  reflecting the implicit source value.
- **No demographic column.** Bronze has no subgroup axis — every row is
  implicitly "All Students", so per §5 the column is omitted entirely.
- **Metrics map straight across** (all counts Int64, the Lexile average
  Float64; nothing is a percentage, so §4 0-1 scaling does not apply):
      TOTAL_STUDENTS_TESTED       -> num_tested
      STUDENTS_WITH_LEXILE        -> num_with_lexile
      LEXILE_ON_OR_ABOVE_MIDPOINT -> num_at_or_above_lexile_midpoint
      NO_LEXILE_SCORE             -> num_without_lexile
      AVG_LEXILE_SCORE            -> avg_lexile_score
- **No §4b masks needed.** Observed avg_lexile_score spans 300.0-1435.0
  across all years — comfortably inside the contract's enforceable [0, 2000]
  Lexile bounds — and no count is negative. Nothing to NULL; the masked
  ledger is intentionally empty.
- **Quality checks (verified 0 violations in every bronze year):**
  the count-nesting chain num_at_or_above_lexile_midpoint <= num_with_lexile
  <= num_tested, and num_without_lexile <= num_tested. The *sum* identity
  (with + without = tested) is NOT authored: it fails in every year (e.g.
  403 rows in 2015; 2023/2024 state- and district-level rows fall short by
  up to 15,807 because NO_LEXILE_SCORE aggregates do not reconcile against
  the tested totals) — documented as a limitation instead.
- **num_without_lexile is ~99% suppressed from 2021 onward** (almost every
  cell is below GOSA's TFS threshold). Retained for pre-2020 comparability;
  the resulting per-year NULL-rate spike is a documented data
  characteristic, not a bug.
- **Dedup tie-break.** Each bronze file covers a distinct year and no file
  contains duplicate (detail_level x district x school x grade) keys
  (verified per file: zero duplicates), so dedup is a safety net only;
  ``sort_col="num_tested"`` prefers a reported, larger count over a
  suppressed placeholder if bronze ever republishes a key.
- **Not in gold:** name columns (SCHOOL_DSTRCT_NM / INSTN_NAME — dimension
  attributes) and SCHOOL_YEAR (derivable from ``year``).
- **Natural PK:** (year, district_code, school_code, grade_level, subject)
  with geography NULLs per detail level. ``subject`` is constant but kept in
  the key for parity with sibling Milestones assessment topics.
- **Disambiguation:** the sibling topics
  ``georgia_milestones_end_of_grade_by_grade_level`` (achievement
  levels by grade) and ``georgia_milestones_end_of_course_lexile``
  (course-based EOC Lexile, no grade_level) are distinct grains/measures.
  This transform reads only from this topic's bronze directory.
"""

import logging
from pathlib import Path

import polars as pl

from src.utils.grades import GRADE_LEVEL_MAP, normalize_grade_column
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

TOPIC = "georgia_milestones_end_of_grade_lexile"
BRONZE_DIR = Path("data/bronze/education/gosa/georgia_milestones_end_of_grade_lexile")
GOLD_DIR = Path("data/gold/education/georgia_milestones_end_of_grade_lexile")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Bronze sentinel marking aggregate rows in SCHOOL_DSTRCT_CD / INSTN_NUMBER.
# This topic uses title-case "All" (verified in all 9 files), unlike the
# uppercase "ALL" used by e.g. the EOG assessment-by-grade sibling.
BRONZE_ALL_SENTINEL = "All"

# Bronze DETAIL_LEVEL literal -> gold detail_level value. Gold uses the
# singular forms EDUCATION_DETAIL_LEVEL_FILES / EDUCATION_DOMAIN_CONFIG expect
# (they drive export filenames and geography-nulling rules).
DETAIL_LEVEL_MAP: dict[str, str] = {
    "State Level": "state",
    "District Level": "district",
    "School Level": "school",
}

# Fixed subject constant: every row derives from the EOG English Language
# Arts assessment (Lexile measures exist only for ELA). See module docstring.
LEXILE_SUBJECT = "english_language_arts"
SUBJECT_MAP: dict[str, str] = {"English Language Arts": LEXILE_SUBJECT}

# Bronze metric column -> (gold name, dtype). All five map straight across;
# counts are Int64 and the Lexile average Float64 (§3). None are percentages.
METRIC_MAP: dict[str, tuple[str, pl.DataType]] = {
    "TOTAL_STUDENTS_TESTED": ("num_tested", pl.Int64),
    "STUDENTS_WITH_LEXILE": ("num_with_lexile", pl.Int64),
    "LEXILE_ON_OR_ABOVE_MIDPOINT": ("num_at_or_above_lexile_midpoint", pl.Int64),
    "NO_LEXILE_SCORE": ("num_without_lexile", pl.Int64),
    "AVG_LEXILE_SCORE": ("avg_lexile_score", pl.Float64),
}

# Single-era signature; detection by column presence so any header drift in a
# future bronze drop raises instead of silently NULLing metrics.
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_1_2015_2024": [
        "SCHOOL_YEAR",
        "DETAIL_LEVEL",
        "SCHOOL_DSTRCT_CD",
        "INSTN_NUMBER",
        "ACDMC_LVL_CD",
        *METRIC_MAP.keys(),
    ],
}

# Gold fact column order (§1): year, geography keys, categoricals, metrics.
# `detail_level` is carried through dedup / geography-nulling / export
# splitting, then dropped by export_to_parquet(). No `demographic` column —
# bronze has no subgroup axis (§5).
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "grade_level",
    "subject",
    "num_tested",
    "num_with_lexile",
    "num_at_or_above_lexile_midpoint",
    "num_without_lexile",
    "avg_lexile_score",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "grade_level": pl.Utf8,
    "subject": pl.Utf8,
    "num_tested": pl.Int64,
    "num_with_lexile": pl.Int64,
    "num_at_or_above_lexile_midpoint": pl.Int64,
    "num_without_lexile": pl.Int64,
    "avg_lexile_score": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = [gold for gold, _ in METRIC_MAP.values()]

# Natural key for the collision guard (detail_level included so district
# aggregates can never shadow school rows under NULL-equal grouping).
NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "detail_level",
    "grade_level",
    "subject",
]


# =============================================================================
# Helpers
# =============================================================================


def _resolve_year(df: pl.DataFrame, path: Path) -> int:
    """Resolve the reporting year and cross-check filename vs file content.

    The filename year is the ending calendar year of the school year; every
    file carries exactly one SCHOOL_YEAR equal to it (verified across all 9
    files). A mismatch means bronze drift and fails loudly.
    """
    filename_year = extract_year_from_filename(path.name)
    if filename_year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")
    school_years = df["SCHOOL_YEAR"].drop_nulls().unique().to_list()
    if len(school_years) != 1:
        raise ValueError(f"{path.name}: expected one SCHOOL_YEAR, got {school_years}")
    try:
        content_year = int(str(school_years[0]).strip())
    except ValueError as err:
        raise ValueError(
            f"{path.name}: SCHOOL_YEAR {school_years[0]!r} is not an integer"
        ) from err
    if content_year != filename_year:
        raise ValueError(
            f"{path.name}: SCHOOL_YEAR {content_year} disagrees with "
            f"filename year {filename_year} — source drift, re-check bronze"
        )
    return filename_year


# =============================================================================
# Era transform
# =============================================================================


def _transform_era1(
    df: pl.DataFrame,
    year: int,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Transform one bronze file into gold-shaped rows.

    Single era: all 9 files share the same 12-column schema. The 2021
    numeric->Utf8 dtype shift (TFS suppression) is absorbed by reading
    all-Utf8 and casting with strict=False.
    """
    # Rename-coverage guard: a missing expected column would silently become
    # NULL for the whole year — the most common data-loss bug — so hard-stop.
    required = ["DETAIL_LEVEL", "SCHOOL_DSTRCT_CD", "INSTN_NUMBER", "ACDMC_LVL_CD"]
    required += list(METRIC_MAP)
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Year {year}: expected bronze column(s) missing: {missing}. "
            f"Present: {df.columns}"
        )

    # Detail level from the explicit bronze literal; unmapped values become
    # the sentinel so the manifest's unmapped guard trips on new literals.
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

    # Geography keys: title-case "All" sentinel -> NULL before zfill so a
    # padded sentinel can never look like a real code; zfill(3) pads standard
    # district codes while 7-digit charter codes pass through; zfill(4) is a
    # verified no-op (all bronze school codes are already 4-char).
    df = df.with_columns(
        pl.when(pl.col("SCHOOL_DSTRCT_CD") == BRONZE_ALL_SENTINEL)
        .then(None)
        .otherwise(pl.col("SCHOOL_DSTRCT_CD").str.zfill(3))
        .alias("district_code"),
        pl.when(pl.col("INSTN_NUMBER") == BRONZE_ALL_SENTINEL)
        .then(None)
        .otherwise(pl.col("INSTN_NUMBER").str.zfill(4))
        .alias("school_code"),
        pl.lit(year).cast(pl.Int32).alias("year"),
    )

    # Grade level: bronze is already the zero-padded 2-char form "03"-"08";
    # the shared normalizer canonicalizes and sentinels anything unexpected.
    bronze_grade = df["ACDMC_LVL_CD"]
    df = df.with_columns(normalize_grade_column("ACDMC_LVL_CD").alias("grade_level"))
    observed_grades = {
        str(v).strip().upper() for v in bronze_grade.drop_nulls().unique().to_list()
    }
    manifest.record_categorical(
        column="grade_level",
        map_dict={k: v for k, v in GRADE_LEVEL_MAP.items() if k in observed_grades},
        bronze_series=bronze_grade,
        gold_series=df["grade_level"],
    )

    # Subject: fixed constant (no bronze column — Lexile is ELA-only), piped
    # through the shared spelling normalizer (a no-op) per the checklist. The
    # manifest's bronze series is a synthetic one-element series carrying the
    # implicit source value; record_categorical only inspects unique values.
    df = df.with_columns(
        apply_subject_normalization(pl.lit(LEXILE_SUBJECT)).alias("subject")
    )
    manifest.record_categorical(
        column="subject",
        map_dict=SUBJECT_MAP,
        bronze_series=pl.Series("subject_bronze", ["English Language Arts"]),
        gold_series=df["subject"],
    )

    # Metrics: counts -> Int64, Lexile average -> Float64. strict=False turns
    # residual non-numerics (any TFS not already nulled by read_bronze_file,
    # the 2015-2019 empty fields) into NULL instead of raising. No 0-1
    # rescaling — nothing here is a percentage (§4 does not apply).
    df = df.with_columns(
        pl.col(src).cast(dtype, strict=False).alias(gold)
        for src, (gold, dtype) in METRIC_MAP.items()
    )

    return df.select(STANDARD_COLUMNS)


# =============================================================================
# File routing
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read one bronze file, detect its era, and route to the era handler.

    All columns are read as Utf8 (``infer_schema_length=0``) so suppression
    markers and zero-padded codes survive intact; numeric casts happen
    explicitly downstream (§4.3b).
    """
    df, loss = read_bronze_file(path, infer_schema_length=0, return_loss=True)
    year = _resolve_year(df, path)
    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{path.name}: no era signature matched columns {df.columns}")

    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)

    if df.height == 0:
        logger.warning("Year %d: bronze file is empty, skipping %s", year, path.name)
        return None

    logger.info(
        "Processing %s as %s (year %d, %d rows)", path.name, era, year, df.height
    )
    return _transform_era1(df, year, manifest)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for EOG Lexile scores."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file (read-loss accounted per file).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR):
        result = transform_file(path, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize columns/dtypes and concatenate (single era — the
    # harmonize step is the standard guard against stray column drift).
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)
    logger.info("Combined %d rows across %d files", combined.height, len(all_dfs))

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean an upstream bug and must raise, not be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: each file is a distinct year and no file carries duplicate
    # natural keys (verified per file: zero duplicates), so dedup is a safety
    # net; prefer the row with a reported, larger num_tested over a
    # suppressed placeholder if bronze ever republishes a key.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code", "grade_level", "subject"],
        district_keys=["year", "district_code", "grade_level", "subject"],
        state_keys=["year", "grade_level", "subject"],
        sort_col="num_tested",
    )

    # 4. Geography nulling from the shared domain rules (transform and
    # validator share one rule source, so they cannot disagree).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. The num_without_lexile NULL-rate spike is expected
    # with a documented bronze cause: ~99% of 2021+ cells are TFS-suppressed
    # (pre/post-COVID suppression-regime discontinuity), vs ~0-2% before.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes (documented cause): %s", spike_result.details)
    validate_output(
        combined,
        required_non_null=["year", "detail_level", "grade_level", "subject"],
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
            "Lexile reading-score outcomes for Georgia public-school students "
            "taking the Georgia Milestones End-of-Grade (EOG) English "
            "Language Arts assessment in grades 3-8. Each row is one (entity "
            "x grade) cell reporting students tested, students who received a "
            "Lexile measure, students whose Lexile met or exceeded the "
            "grade-band stretch midpoint (a national reading-level "
            "benchmark), students without a Lexile score, and the average "
            "Lexile measure. State, district, and school detail levels; no "
            "demographic breakdown (every row is implicitly All Students). "
            "School years 2014-15 through 2023-24; 2019-20 is absent (EOG "
            "testing suspended, COVID-19)."
        ),
        title="Georgia Milestones End-of-Grade Lexile Reading Scores",
        summary=(
            "Lexile reading-measure distributions by grade at school, "
            "district, and state level, 2015-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Ending calendar year of the school year (e.g., 2024 = "
                    "2023-24), from the filename and cross-checked against "
                    "the file's SCHOOL_YEAR column. 2020 has no rows (EOG "
                    "testing suspended during COVID-19 closures)."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "GOSA district code (FK to districts dimension): 3-digit "
                    "zero-padded standard codes or 7-digit state-charter "
                    "codes. NULL on state-level rows."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0200",
                "description": (
                    "GOSA school code, zero-padded to 4 characters "
                    "(composite FK to schools dimension with district_code; "
                    "not globally unique on its own). NULL on district- and "
                    "state-level rows."
                ),
            },
            {
                "name": "grade_level",
                "type": "string",
                "nullable": False,
                "example": "04",
                "validValues": ["03", "04", "05", "06", "07", "08"],
                "short_description": (
                    "Grade the EOG ELA assessment was given to, as a "
                    "2-char code (03-08; EOG covers grades 3-8)."
                ),
                "description": (
                    "Grade the EOG ELA assessment was administered to, as a "
                    "canonical 2-char zero-padded string (03-08; EOG covers "
                    "grades 3-8 only). Bronze ACDMC_LVL_CD is already "
                    "zero-padded in every year."
                ),
            },
            {
                "name": "subject",
                "type": "string",
                "nullable": False,
                "example": "english_language_arts",
                "validValues": [LEXILE_SUBJECT],
                "short_description": (
                    "Academic subject; always english_language_arts "
                    "(Lexile measures exist only for the EOG ELA test)."
                ),
                "description": (
                    "Academic subject. Fixed constant english_language_arts: "
                    "every Lexile measure derives from the EOG English "
                    "Language Arts assessment (bronze has no subject column). "
                    "Included for canonical-vocabulary parity with sibling "
                    "Milestones assessment topics so API consumers can filter "
                    "by subject uniformly."
                ),
            },
            {
                "name": "num_tested",
                "type": "int64",
                "unit": "count",
                "example": 132,
                "null_meaning": (
                    "2015-2019: genuinely empty source cell; 2021+: GOSA "
                    "TFS (too few students) suppression."
                ),
                "description": (
                    "Count of students who took the EOG ELA assessment in "
                    "this cell. Bronze TOTAL_STUDENTS_TESTED. NULL when "
                    "suppressed (TFS, 2021+) or genuinely empty in the "
                    "source (every 2015-2019 file, 126-141 cells per year)."
                ),
            },
            {
                "name": "num_with_lexile",
                "type": "int64",
                "unit": "count",
                "metric_component": "denominator",
                "example": 132,
                "null_meaning": (
                    "2015-2019: genuinely empty source cell; 2021+: GOSA "
                    "TFS (too few students) suppression."
                ),
                "description": (
                    "Count of tested students who received a usable Lexile "
                    "measure; never exceeds num_tested (verified, authored as "
                    "a quality check). Bronze STUDENTS_WITH_LEXILE. NULL when "
                    "suppressed."
                ),
            },
            {
                "name": "num_at_or_above_lexile_midpoint",
                "type": "int64",
                "unit": "count",
                "example": 19,
                "null_meaning": (
                    "2015-2019: genuinely empty source cell; 2021+: GOSA "
                    "TFS (too few students) suppression."
                ),
                # Do NOT equate GOSA's "midpoint" with published GaDOE
                # grade-band lower bounds — the exact per-grade thresholds are
                # not documented in this source, so keep GOSA's own label.
                "description": (
                    "Count of students whose Lexile measure was at or above "
                    "the grade-band stretch midpoint (GOSA's on-track-reader "
                    "threshold). A raw COUNT, not a percentage — to derive "
                    "the share, divide by num_with_lexile (the population "
                    "with a valid Lexile), not num_tested. Never exceeds "
                    "num_with_lexile (verified, authored as a quality check). "
                    "Bronze LEXILE_ON_OR_ABOVE_MIDPOINT. NULL when suppressed."
                ),
            },
            {
                "name": "num_without_lexile",
                "type": "int64",
                "unit": "count",
                "example": 3,
                "null_meaning": (
                    "2015-2019: genuinely empty source cell; 2021+: GOSA "
                    "TFS suppression (~99%% of rows from 2021 onward)."
                ),
                "description": (
                    "Count of tested students who did not receive a Lexile "
                    "measure. Bronze NO_LEXILE_SCORE. From 2021 onward ~99%% "
                    "of cells are TFS-suppressed (few students at any school "
                    "lack a Lexile), so the column is ~99%% NULL post-COVID; "
                    "retained for pre-2020 comparability. CAVEAT: "
                    "num_with_lexile + num_without_lexile does NOT reliably "
                    "equal num_tested — small +/- discrepancies exist in "
                    "every year, and 2023/2024 state- and district-level "
                    "rows fall short by thousands (the published aggregate "
                    "does not reconcile); published values are preserved "
                    "exactly."
                ),
            },
            {
                "name": "avg_lexile_score",
                "type": "float64",
                "unit": "score",
                "value_min": 0,
                "value_max": 2000,
                "key_metric": True,
                "example": 607.0,
                "short_description": (
                    "Average Lexile reading measure among students who got "
                    "one, on the natural Lexile scale; not a percentage."
                ),
                "null_meaning": (
                    "2015-2019: genuinely empty source cell; 2021+: GOSA "
                    "TFS (too few students) suppression."
                ),
                "description": (
                    "Average Lexile reading measure among students who "
                    "received one, to one decimal place on the natural "
                    "Lexile scale (observed 300.0-1435.0 across all years; "
                    "the contract enforces 0-2000 — a Beginning-Reader BR "
                    "floor below 0 is unreachable by a school/grade "
                    "average). NOT a percentage; never rescaled. Bronze "
                    "AVG_LEXILE_SCORE. NULL when suppressed."
                ),
            },
        ],
        source="Governor's Office of Student Achievement (GOSA)",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        quality_checks=[
            {
                "name": "lexile_counts_subset_chain",
                "description": (
                    "Count nesting holds wherever both endpoints of a pair "
                    "are non-NULL: num_at_or_above_lexile_midpoint <= "
                    "num_with_lexile <= num_tested. Verified 0 violations in "
                    "every bronze year; NULLs are exempt because TFS "
                    "suppression can hit either endpoint independently."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(num_at_or_above_lexile_midpoint IS NOT NULL "
                    "AND num_with_lexile IS NOT NULL "
                    "AND num_at_or_above_lexile_midpoint > num_with_lexile) "
                    "OR (num_with_lexile IS NOT NULL "
                    "AND num_tested IS NOT NULL "
                    "AND num_with_lexile > num_tested)"
                ),
                "mustBe": 0,
            },
            {
                "name": "num_without_lexile_never_exceeds_num_tested",
                "description": (
                    "Students without a Lexile measure are a subset of "
                    "students tested: num_without_lexile <= num_tested "
                    "wherever both are non-NULL. Verified 0 violations in "
                    "every bronze year. (The stronger sum identity "
                    "num_with_lexile + num_without_lexile = num_tested is "
                    "deliberately NOT enforced — it fails in every year, by "
                    "thousands on 2023/2024 aggregate rows.)"
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
        ],
        notes=[
            (
                "Single bronze era (2015-2024): all 9 files share one "
                "12-column header. The only cross-year quirk is the 2021 "
                "shift from pure-numeric metric fields to strings carrying "
                "the TFS suppression marker, absorbed by all-Utf8 reads and "
                "non-strict casts."
            ),
            (
                "Missing year: 2020 (school year 2019-20) — EOG testing "
                "suspended statewide due to COVID-19. Gold has no 2020 "
                "partition; do not interpolate."
            ),
            (
                "Suppression: TFS (Too Few Students) appears from 2021 "
                "onward and becomes NULL in gold. num_without_lexile is the "
                "extreme case (~99%% of 2021+ cells suppressed), producing a "
                "documented pre/post-COVID NULL-rate discontinuity. Every "
                "2015-2019 file additionally carries genuinely empty metric "
                "fields (126-143 per metric column per year), which also "
                "become NULL in gold — pre-2021 NULLs are empty source "
                "cells, not TFS."
            ),
            (
                "The sum identity num_with_lexile + num_without_lexile = "
                "num_tested is only approximate and is NOT enforced: every "
                "year has small +/- discrepancies (e.g., 403 rows in 2015), "
                "and 2023/2024 state- and district-level rows fall short by "
                "up to 15,807 because the published NO_LEXILE_SCORE "
                "aggregates do not reconcile against tested totals."
            ),
            (
                "num_at_or_above_lexile_midpoint is a COUNT, not a "
                "percentage. To derive the share at or above the midpoint, "
                "divide by num_with_lexile (the population with a valid "
                "Lexile), not num_tested."
            ),
            (
                "No demographic breakdown: bronze has no subgroup axis, so "
                "per data-cleaning-standards section 5 the demographic "
                "column is omitted entirely."
            ),
            (
                "subject is a fixed constant (english_language_arts) — "
                "Lexile measures exist only for the EOG ELA assessment. The "
                "column is emitted for filter parity with sibling Milestones "
                "topics."
            ),
            (
                "ID formatting: district_code zfill(3) with 7-digit "
                "state-charter codes passed through; school_code zfill(4) "
                "(bronze INSTN_NUMBER is already 4-char zero-padded in every "
                "year — verified in raw CSV bytes)."
            ),
            (
                "Disambiguation: georgia_milestones_end_of_grade_"
                "by_grade_level reports achievement levels (not "
                "Lexile); georgia_milestones_end_of_course_lexile "
                "is the course-based EOC Lexile sibling (no grade_level). "
                "Different grains — do not merge."
            ),
        ],
    )


if __name__ == "__main__":
    main()
