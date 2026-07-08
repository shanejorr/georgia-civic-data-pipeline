"""Transform bronze advanced_placement_scores files into gold fact tables.

Source: Governor's Office of Student Achievement (GOSA) — Advanced Placement
(AP) Scores, 2004-2024 (21 bronze files). For every Georgia public school,
plus official district and state rollups, reports the number of distinct
students taking AP exams, the total exams administered, the count of exams
scoring 3 or higher (College Board's "qualifying" threshold), and a derived
pass rate.

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Five bronze schema eras, one long gold fact.**
    * Era A (2004-2007, wide, 6 cols): compound ``SysSchoolID``
      (``ALL:ALL`` = state, ``{d}:ALL`` = district, else school). The 2005
      file is an XLS binary mislabeled ``.csv`` (read_bronze_file detects the
      OLE magic bytes and routes to the XLS reader).
    * Era B (2008-2009, wide, 7 cols): adds ``System Name``; the compound ID
      is ``SysSchoolid`` (lowercase ``id``).
    * Era C (2010, wide, 6 cols): ``Sysschoolid`` plus the literal
      ``School or Distict  Name`` header (misspelling + double space).
    * Era D (2011-2022, tidy, 9 cols): per-subject rows keyed by
      ``TEST_CMPNT_TYP_NM``; detail level inferred from the
      ``DISTRICT_ALL`` / ``SCHOOL_ALL`` ID sentinels.
    * Era E (2023-2024, tidy, 11 cols): adds ``#RPT_NAME`` (constant
      ``"AP COUNTS"``, asserted) and ``DETAIL_LVL_DESC``; sentinels simplify
      to ``"ALL"``; the qualifying-count column is renamed
      ``NUMBER_TESTS_3_OR_HIGHER``. ``detail_level`` derives from
      ``DETAIL_LVL_DESC`` (strip the `` ALL SUBJECTS`` suffix, lowercase) and
      is cross-checked against the ID-sentinel inference (verified 0
      mismatches in both years; a mismatch raises).

- **``subject`` is the per-row AP subject (snake_case).** Eras D-E carry 41
  specific subjects plus the cross-subject ``ALL Subjects`` aggregate; Eras
  A-C publish only the cross-subject totals, emitted as
  ``subject = "all_subjects"``. The shared ``apply_subject_normalization``
  backstop runs after the topic map (a verified no-op on 2004-2024 bronze —
  the map already emits §16-canonical values).

- **``ALL Subjects`` rows are NOT derivable by summing subject rows** —
  ``num_tested`` counts distinct students across subjects (a student taking
  Calculus and Biology counts once), while subject rows count subject-level
  participants. The aggregate is carried verbatim from bronze.

- **No ``demographic`` column.** No era publishes race/gender/economic
  breakdowns (bronze-data-structure.md "Summary"); per data-cleaning-
  standards §5 the column is omitted. No grade column exists either, so no
  shared grade normalizer is needed.

- **``tests_3_or_higher_rate`` is recomputed from counts** as
  ``num_tests_3_or_higher / num_tests_taken`` on the 0-1 scale. Eras A-C
  ship a 0-100 ``Percentage of Test Scores 3 or Higher`` bronze column
  (dropped — recomputed values agree within 0.0005, i.e. source rounding);
  Eras D-E ship no rate column at all. NULL when either count is NULL or
  the denominator is 0.

- **Dropped rows (all logged + ``record_filtered``):**
    * 2004: one trailing junk row whose ``SysSchoolID`` is NUL-byte garbage
      with no ``:`` delimiter and all-null metrics.
    * 2005: one ``644:xxxx`` row (no school name, metrics 2/2/2) — its
      non-numeric school code violates the school-code format and cannot
      join the schools dimension, and GOSA's own rollup EXCLUDES it: the
      ``644:ALL`` district total (2577/4076/1760) equals the district's
      school-row sums without the xxxx row exactly, so dropping it loses
      nothing the source itself counted.
    * 2007: one ``678:9999`` placeholder-school row (no name, all metrics 0)
      — ``9999``/``0000`` mirror the ``SCHOOL_SENTINELS`` exclusion in
      ``src/etl/education/build_dimensions.py``; the genuine ``678:ALL``
      district row is preserved.

- **Pinned legacy duplicate keys are SUMMED, not deduped.** Eras B-C publish
  five duplicate-key groups that are partial counts of the same entity, not
  re-publications — proven by reconciliation arithmetic against the same
  file's other rows:
    * 2009 districts 611 (Bibb + "Bibb County"), 667 (Gwinnett + "Gwinnett
      County"), 710 (Paulding + "Paulding County"): the pairwise sums equal
      the district's school-row sums (exactly for 710: 639/792/245; within
      the suppressed-cell remainder for 611/667).
    * 2009 school 722:0176 (Heritage High, 213/417/251 + 63/70/22): district
      722's published total (738/1231/543) equals its school-row sums ONLY
      when both rows are summed.
    * 2008 school 761:0195 (41/60/1 + 5/NULL/NULL): district 761's published
      total (606/903/244) reconciles with school sums including both rows.
  Aggregation semantics: ``num_tested`` sums non-null components (all-null →
  NULL); ``num_tests_taken`` / ``num_tests_3_or_higher`` go NULL when ANY
  component is suppressed (summing a partial component would fabricate a
  complete-looking denominator and a misleading pass rate);
  ``tests_3_or_higher_rate`` is recomputed from the aggregated counts. The
  five groups are PINNED — any other duplicate key raises so future bronze
  drift cannot be silently aggregated. ``assert_no_natural_key_collisions``
  runs after this step and before dedup.

- **Dedup tie-break.** Every bronze file is a distinct year and eras do not
  overlap, so after the pinned aggregation no duplicates remain;
  ``sort_col="num_tests_taken"`` is the documented safety net (prefer a row
  with a reported count over a suppressed placeholder).

- **3 bronze rows publish ``num_tested > num_tests_taken``** (impossible if
  both counts were accurate — every tested student sits at least one exam):
  2005 school 611:0204 (Rutland HS, 33 students / 23 tests) and 2008
  district 652 + school 652:0176 (Elbert County, 10/9 — a single-school
  district, so the same defect appears at both levels). Each value is
  individually plausible and the wrong-side column is unknowable, so per
  §4b's extreme-vs-impossible test the rows are PRESERVED + documented (the
  same treatment as act_scores' 2010 district inconsistencies), not masked.
  A pinned quality check enforces the invariant everywhere else.

- **§4b mask: 8 misassigned 2005 district rollup rows.** The 2005 bronze
  publishes district ``:ALL`` totals that provably belong to OTHER districts
  — an alphabetical-adjacency shift plus an exact Jefferson County (681) <->
  Jefferson City (779) swap in GOSA's rollup generation. Proof: 2005 has
  zero suppression and 120 of 128 district rollups equal their own
  school-row sums EXACTLY; the 8 exceptions decode by exact three-metric
  donor matches (``MISASSIGNED_2005_DISTRICT_ROLLUPS``): Putnam 717 carries
  Rabun 719's totals, Randolph 720 carries Richmond 721's, Richmond 721
  carries Rockdale 722's, Rockdale 722 carries Rome City 785's (Rome's own
  rollup is ALSO correct — its totals are served twice), and 681/779 carry
  each other's; Screven 724 (published 167/202/111 vs own sums 67/104/51)
  and Wilkinson 758 (37/38/14 vs 10/11/0) mismatch their own sums with no
  identified in-file donor. 2004→2006 trend confirms every case (e.g.
  Rockdale tests 833 → published 97 / own 842 → 950; Randolph students 3 →
  published 489 → 1). All four metrics on the 8 rows are NULLed by
  ``_null_2005_misassigned_district_rollups`` (rows + school-level rows
  preserved; v1 served the defect verbatim, so this intentionally breaks v1
  parity). The ``district_not_below_own_max_school`` quality check pins the
  defect class (current violators: only 681 and 722 pre-mask; zero
  post-mask).

- **Suppression varies by era** (all → NULL):
    * Era A: blank cells (2004 has 47 of 414 bronze rows blank in the
      tests/score columns; 2005-2007 blanks coincide with zero-test rows).
    * Eras B-C: literal ``"Too Few Students"`` (nulled by
      ``read_bronze_file``'s SUPPRESSION_VALUES).
    * Era D 2011-2019: EMPTY CELLS in ``NUMBER_TESTS_TAKEN`` /
      ``NOTESTS_3ORHIGHER`` (~2,000-2,800/yr; no TFS in those columns), plus
      ``TFS`` in ``NUMBER_OF_STUDENTS_TESTED`` (2011-2015, 2019 only —
      2016-2018 publish unsuppressed student counts down to n=1).
    * Era D 2020-2022: ``TFS`` in all three metrics plus residual empty
      cells in ``NOTESTS_3ORHIGHER`` (70 / 132 / 160 rows).
    * Era E: ``TFS`` only.

Pipeline: read each file (loss-accounted) → era detect by column signature →
era transform → harmonize/concat → pinned legacy duplicate aggregation →
collision guard → dedup safety net → geography nulling → validate → manifest
→ export → contract/README → run_topic_validation (always last).
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

TOPIC = "advanced_placement_scores"
BRONZE_DIR = Path("data/bronze/education/gosa/advanced_placement_scores")
GOLD_DIR = Path("data/gold/education/advanced_placement_scores")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Aggregate-sentinel strings used in the ID columns across eras. All map to
# NULL geography. Verified uppercase-only in every file (no `All:All` casing).
AGG_SENTINELS: list[str] = ["ALL", "DISTRICT_ALL", "SCHOOL_ALL"]

# Legacy placeholder school codes mirroring SCHOOL_SENTINELS in
# src/etl/education/build_dimensions.py — not real schools, cannot join the
# schools dimension. Only observed case: 2007 `678:9999` (all metrics 0).
PLACEHOLDER_SCHOOL_CODES: list[str] = ["9999", "0000"]

# Bronze `TEST_CMPNT_TYP_NM` (Eras D-E) -> gold `subject`. All 42 distinct
# values observed across 2011-2024 bronze. `ALL Subjects` is the cross-subject
# aggregate and also the constant assigned to every legacy-era (A-C) row.
# `Calculus A` is GOSA's literal label for AP Calculus AB (pairs with
# `Calculus BC`); `Physics B` and `Latin: Vergil` are discontinued legacy
# exams correctly retained for the years they were administered.
SUBJECT_MAP: dict[str, str] = {
    "ALL Subjects": "all_subjects",
    "African American Studies": "african_american_studies",
    "Art History": "art_history",
    "Art: Studio 2-D Design": "art_studio_2d_design",
    "Art: Studio 3-D Design": "art_studio_3d_design",
    "Art: Studio Drawing": "art_studio_drawing",
    "Biology": "biology",
    "Calculus A": "calculus_a",
    "Calculus BC": "calculus_bc",
    "Capstone": "capstone",
    "Capstone Research": "capstone_research",
    "Chemistry": "chemistry",
    "Chinese Lang. & Culture": "chinese_language_and_culture",
    "Computer Science A": "computer_science_a",
    "Computer Science Principles": "computer_science_principles",
    "Economics: Macro": "economics_macro",
    "Economics: Micro": "economics_micro",
    "Eng. Language & Comp": "english_language_and_composition",
    "Eng. Literature & Comp": "english_literature_and_composition",
    "Environmental Science": "environmental_science",
    "European History": "european_history",
    "French Language": "french_language",
    "Geography: Human": "human_geography",
    "German Language": "german_language",
    "Gov. & Pol. Comp": "government_and_politics_comparative",
    "Gov. & Pol. U.S.": "government_and_politics_us",
    "Italian Lang. & Culture": "italian_language_and_culture",
    "Japanese Lang. & Culture": "japanese_language_and_culture",
    "Latin: Vergil": "latin_vergil",
    "Music Theory": "music_theory",
    "Physics 1": "physics_1",
    "Physics 2": "physics_2",
    "Physics B": "physics_b",
    "Physics C: Elec & Magnetism": "physics_c_electricity_and_magnetism",
    "Physics C: Mechanics": "physics_c_mechanics",
    "Precalculus": "precalculus",
    "Psychology": "psychology",
    "Spanish Language": "spanish_language",
    "Spanish Literature": "spanish_literature",
    "Statistics": "statistics",
    "U.S. History": "us_history",
    "World History": "world_history",
}

# Era-detection signatures, most-specific first. Era E's column set is a
# strict superset of Era D's, so E is checked first; Eras A/B/C carry three
# distinct compound-ID column spellings (and only B has `System Name`).
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_e": [
        "#RPT_NAME",
        "DETAIL_LVL_DESC",
        "TEST_CMPNT_TYP_NM",
        "NUMBER_TESTS_3_OR_HIGHER",
    ],
    "era_d": ["LONG_SCHOOL_YEAR", "TEST_CMPNT_TYP_NM", "NOTESTS_3ORHIGHER"],
    "era_b": ["SysSchoolid", "System Name", "Number of Tests Taken"],
    "era_c": ["Sysschoolid", "School or Distict  Name", "Number of Tests Taken"],
    "era_a": ["SysSchoolID", "SchoolNme", "Number of Tests Taken"],
}

# Identical wide-era metric headers shared by Eras A, B, and C.
LEGACY_METRIC_RENAMES: dict[str, str] = {
    "Number of Students Taking Tests": "num_tested",
    "Number of Tests Taken": "num_tests_taken",
    "Number of Test Scores 3 or Higher": "num_tests_3_or_higher",
}

# Gold column order. `detail_level` is carried through dedup / geography
# nulling / export splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "subject",
    "num_tested",
    "num_tests_taken",
    "num_tests_3_or_higher",
    "tests_3_or_higher_rate",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "subject": pl.Utf8,
    "num_tested": pl.Int64,
    "num_tests_taken": pl.Int64,
    "num_tests_3_or_higher": pl.Int64,
    "tests_3_or_higher_rate": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = [
    "num_tested",
    "num_tests_taken",
    "num_tests_3_or_higher",
    "tests_3_or_higher_rate",
]

NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "detail_level",
    "subject",
]

# The 8 PINNED 2005 district rollup rows whose published totals provably
# belong to other districts (§4b mask; full proof in module docstring).
# Keys are the affected district_codes; values are the identified donor
# district whose school-row sums exactly equal the published triple (None
# where no in-file donor matches — the published values still contradict
# the district's own school sums and 2004/2006 trend).
MISASSIGNED_2005_DISTRICT_ROLLUPS: dict[str, str | None] = {
    "681": "779",  # Jefferson County <- Jefferson City (exact swap)
    "717": "719",  # Putnam <- Rabun
    "720": "721",  # Randolph <- Richmond (489/772/318 served to a ~3-student district)
    "721": "722",  # Richmond <- Rockdale
    "722": "785",  # Rockdale <- Rome City (Rome's own rollup is also correct)
    "724": None,  # Screven: published 167/202/111 vs own school sums 67/104/51
    "758": None,  # Wilkinson: published 37/38/14 vs own school sums 10/11/0
    "779": "681",  # Jefferson City <- Jefferson County (exact swap)
}

# The five PINNED legacy duplicate-key groups whose rows are partial counts
# of one entity and must be summed (arithmetic proofs in module docstring).
# Tuples are (year, district_code, school_code, detail_level) post-zfill;
# subject is always "all_subjects" in these eras. Any OTHER duplicate key
# raises — no unproven group may be silently aggregated.
EXPECTED_LEGACY_DUP_KEYS: set[tuple[int, str | None, str | None, str]] = {
    (2008, "761", "0195", "school"),
    (2009, "611", None, "district"),
    (2009, "667", None, "district"),
    (2009, "710", None, "district"),
    (2009, "722", "0176", "school"),
}


# =============================================================================
# Shared expression helpers
# =============================================================================


def _detail_level_expr(district_raw: pl.Expr, school_raw: pl.Expr) -> pl.Expr:
    """Classify detail level from aggregate sentinels in the raw ID columns.

    Rule (Eras A-D; Era E uses DETAIL_LVL_DESC and cross-checks against this):
    both parts sentinel -> state; school part sentinel only -> district;
    otherwise -> school.
    """
    return (
        pl.when(district_raw.is_in(AGG_SENTINELS) & school_raw.is_in(AGG_SENTINELS))
        .then(pl.lit("state"))
        .when(school_raw.is_in(AGG_SENTINELS))
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .cast(pl.Utf8)
    )


def _geography_exprs(district_raw: str, school_raw: str) -> list[pl.Expr]:
    """Map raw ID columns to gold district_code / school_code.

    Sentinels -> NULL; surviving codes zero-padded per the education domain
    rules (zfill(3) preserves 7-digit charter codes; zfill(4) aligns 3- and
    4-digit school codes across years).
    """
    return [
        pl.when(pl.col(district_raw).is_in(AGG_SENTINELS))
        .then(None)
        .otherwise(pl.col(district_raw).cast(pl.Utf8).str.strip_chars().str.zfill(3))
        .alias("district_code"),
        pl.when(pl.col(school_raw).is_in(AGG_SENTINELS))
        .then(None)
        .otherwise(pl.col(school_raw).cast(pl.Utf8).str.strip_chars().str.zfill(4))
        .alias("school_code"),
    ]


def _pct_expr() -> pl.Expr:
    """Derive tests_3_or_higher_rate = num_tests_3_or_higher / num_tests_taken.

    0-1 scale per data-cleaning-standards §4; NULL when either count is NULL
    or the denominator is 0 (no divide-by-zero). Recomputed (rather than
    carried from the legacy bronze 0-100 column) so the metric exists on one
    scale across all eras — Eras D-E ship no rate column at all.
    """
    return (
        pl.when(
            pl.col("num_tests_taken").is_null()
            | pl.col("num_tests_3_or_higher").is_null()
            | (pl.col("num_tests_taken") == 0)
        )
        .then(None)
        .otherwise(
            pl.col("num_tests_3_or_higher").cast(pl.Float64)
            / pl.col("num_tests_taken").cast(pl.Float64)
        )
        .alias("tests_3_or_higher_rate")
    )


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


def _cast_count_exprs(renames: dict[str, str]) -> list[pl.Expr]:
    """Int64 casts for bronze count columns (strict=False).

    All bronze reads are all-string (infer_schema_length=0 / xls dtype=str),
    so the non-strict cast nulls every suppression residue: blank cells,
    empty strings, and any TFS/'Too Few Students' marker not already nulled
    by read_bronze_file.
    """
    return [
        pl.col(src).cast(pl.Int64, strict=False).alias(dst)
        for src, dst in renames.items()
    ]


# =============================================================================
# Era A/B/C (2004-2010): wide format, compound ID, no subject breakdown
# =============================================================================


def _split_compound_id(
    df: pl.DataFrame,
    id_col: str,
    year: int,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Split the legacy compound ``{district}:{school}`` ID; drop bad rows.

    Three pinned drop classes (each logged + record_filtered):
    1. Rows without the ``:`` delimiter — the 2004 trailing junk row whose ID
       is NUL-byte garbage with all-null metrics.
    2. Non-numeric, non-sentinel school codes — the 2005 ``644:xxxx`` row;
       violates the school-code format, cannot join the schools dimension,
       and is EXCLUDED from GOSA's own ``644:ALL`` rollup (the district
       total equals the school-row sums without it, exactly).
    3. Placeholder school codes ``9999``/``0000`` — the 2007 ``678:9999`` row
       (no name, all metrics 0); mirrors the dimensions build's
       SCHOOL_SENTINELS exclusion.
    """
    ids = pl.col(id_col).cast(pl.Utf8).str.strip_chars()
    no_colon = df.filter(ids.is_null() | ~ids.str.contains(":", literal=True))
    if no_colon.height:
        # Sample logged via repr-safe ascii (the 2004 junk ID is NUL bytes).
        logger.warning(
            "Year %d: dropping %d row(s) with no compound-ID delimiter: %s",
            year,
            no_colon.height,
            [repr(v)[:40] for v in no_colon[id_col].head(3).to_list()],
        )
        manifest.record_filtered(year, no_colon.height, "missing_compound_id_delimiter")
        df = df.filter(ids.is_not_null() & ids.str.contains(":", literal=True))

    parts = ids.str.split(":")
    df = df.with_columns(
        parts.list.get(0, null_on_oob=True).alias("_district_raw"),
        parts.list.get(1, null_on_oob=True).alias("_school_raw"),
    )

    # Guard both ID halves: each must be a sentinel or numeric. Known case is
    # the 2005 `644:xxxx` school half; a malformed district half has never
    # been observed and would also be dropped loudly here.
    malformed = (
        ~pl.col("_district_raw").is_in(AGG_SENTINELS)
        & ~pl.col("_district_raw").str.contains(r"^\d+$")
    ) | (
        ~pl.col("_school_raw").is_in(AGG_SENTINELS)
        & ~pl.col("_school_raw").str.contains(r"^\d+$")
    )
    bad = df.filter(malformed)
    if bad.height:
        logger.warning(
            "Year %d: dropping %d row(s) with malformed compound ID: %s",
            year,
            bad.height,
            bad.select("_district_raw", "_school_raw").to_dicts(),
        )
        manifest.record_filtered(year, bad.height, "malformed_compound_id")
        df = df.filter(~malformed)

    placeholder = pl.col("_school_raw").is_in(PLACEHOLDER_SCHOOL_CODES)
    ph_rows = df.filter(placeholder)
    if ph_rows.height:
        logger.warning(
            "Year %d: dropping %d placeholder-school row(s) (school code in %s): %s",
            year,
            ph_rows.height,
            PLACEHOLDER_SCHOOL_CODES,
            ph_rows.select("_district_raw", "_school_raw").to_dicts(),
        )
        manifest.record_filtered(year, ph_rows.height, "placeholder_school_code")
        df = df.filter(~placeholder)
    return df


def _transform_legacy(
    df: pl.DataFrame,
    year: int,
    id_col: str,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Transform an Era A/B/C wide file (2004-2010) into gold rows.

    The three legacy eras share identical metric headers and differ only in
    the compound-ID column spelling and which name columns exist (all name
    columns are dimension attributes and dropped here). Every legacy row is
    the cross-subject total -> ``subject = "all_subjects"``. The bronze
    0-100 ``Percentage of Test Scores 3 or Higher`` column is dropped and
    recomputed from counts (module docstring).
    """
    _require_columns(df, [id_col, *LEGACY_METRIC_RENAMES], f"legacy {year}")
    df = _split_compound_id(df, id_col, year, manifest)

    df = df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        _detail_level_expr(pl.col("_district_raw"), pl.col("_school_raw")).alias(
            "detail_level"
        ),
        # Legacy eras have no subject breakdown — every row is the
        # cross-subject total, matching Eras D-E's `ALL Subjects` rows.
        pl.lit("all_subjects").alias("subject"),
        *_cast_count_exprs(LEGACY_METRIC_RENAMES),
        *_geography_exprs("_district_raw", "_school_raw"),
    )
    df = df.with_columns(_pct_expr())
    return df.select(STANDARD_COLUMNS)


# =============================================================================
# Era D/E (2011-2024): tidy format with per-subject breakdown
# =============================================================================


def _era_e_detail_level(df: pl.DataFrame, year: int) -> pl.DataFrame:
    """Derive Era E ``detail_level`` from DETAIL_LVL_DESC with cross-checks.

    DETAIL_LVL_DESC has six values: SCHOOL / DISTRICT / STATE plus
    ``… ALL SUBJECTS`` variants marking the per-entity cross-subject rows.
    The suffix is redundant with ``subject = all_subjects`` (verified) and
    the base level must agree with the ID-sentinel inference (verified) —
    either disagreement means the source changed shape, so both raise.
    """
    df = df.with_columns(
        pl.col("DETAIL_LVL_DESC")
        .str.replace(" ALL SUBJECTS", "", literal=True)
        .str.to_lowercase()
        .alias("detail_level")
    )

    suffix_mismatch = df.filter(
        pl.col("DETAIL_LVL_DESC").str.ends_with("ALL SUBJECTS")
        != (pl.col("TEST_CMPNT_TYP_NM") == "ALL Subjects")
    )
    if suffix_mismatch.height:
        raise ValueError(
            f"era_e {year}: {suffix_mismatch.height} row(s) where the "
            f"DETAIL_LVL_DESC 'ALL SUBJECTS' suffix disagrees with "
            f"TEST_CMPNT_TYP_NM: {suffix_mismatch.head(5).to_dicts()}"
        )

    sentinel_level = _detail_level_expr(
        pl.col("SCHOOL_DISTRCT_CD"), pl.col("INSTN_NUMBER")
    )
    level_mismatch = df.filter(pl.col("detail_level") != sentinel_level)
    if level_mismatch.height:
        raise ValueError(
            f"era_e {year}: {level_mismatch.height} row(s) where "
            f"DETAIL_LVL_DESC disagrees with the ID-sentinel detail level: "
            f"{level_mismatch.head(5).to_dicts()}"
        )
    return df


def _transform_tidy(
    df: pl.DataFrame,
    year: int,
    era: str,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Transform an Era D/E tidy file (2011-2024) into gold rows.

    Era differences: the qualifying-count column name (``NOTESTS_3ORHIGHER``
    vs ``NUMBER_TESTS_3_OR_HIGHER``), the detail-level source (ID sentinels
    vs ``DETAIL_LVL_DESC``), and Era E's constant ``#RPT_NAME`` (asserted).
    """
    t3_col = "NUMBER_TESTS_3_OR_HIGHER" if era == "era_e" else "NOTESTS_3ORHIGHER"
    renames = {
        "NUMBER_OF_STUDENTS_TESTED": "num_tested",
        "NUMBER_TESTS_TAKEN": "num_tests_taken",
        t3_col: "num_tests_3_or_higher",
    }
    _require_columns(
        df,
        ["SCHOOL_DISTRCT_CD", "INSTN_NUMBER", "TEST_CMPNT_TYP_NM", *renames],
        f"{era} {year}",
    )

    if era == "era_e":
        # Constant-column guard: any other value means non-AP rows are mixed
        # into this topic's bronze.
        rpt_names = df["#RPT_NAME"].drop_nulls().unique().to_list()
        if rpt_names != ["AP COUNTS"]:
            raise ValueError(f"era_e {year}: unexpected #RPT_NAME values {rpt_names}")
        df = _era_e_detail_level(df, year)
    else:
        df = df.with_columns(
            _detail_level_expr(
                pl.col("SCHOOL_DISTRCT_CD"), pl.col("INSTN_NUMBER")
            ).alias("detail_level")
        )

    # Subject: topic-local snake_case map (unmapped -> sentinel so the
    # manifest guard raises), then the shared spelling-variant backstop — a
    # verified no-op on 2004-2024 bronze (SUBJECT_MAP already emits §16
    # canonical values) that catches future GOSA label drift.
    bronze_subject = df["TEST_CMPNT_TYP_NM"]
    df = df.with_columns(
        pl.col("TEST_CMPNT_TYP_NM")
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

    df = df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        *_cast_count_exprs(renames),
        *_geography_exprs("SCHOOL_DISTRCT_CD", "INSTN_NUMBER"),
    )
    df = df.with_columns(_pct_expr())
    return df.select(STANDARD_COLUMNS)


# =============================================================================
# File routing
# =============================================================================

# Era -> (transform function, fixed args). Legacy eras differ only in the
# compound-ID column spelling.
ERA_ROUTES = {
    "era_a": (_transform_legacy, ("SysSchoolID",)),
    "era_b": (_transform_legacy, ("SysSchoolid",)),
    "era_c": (_transform_legacy, ("Sysschoolid",)),
    "era_d": (_transform_tidy, ("era_d",)),
    "era_e": (_transform_tidy, ("era_e",)),
}


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read one bronze file, detect its era, and route to the era transform.

    All reads are all-string (``infer_schema_length=0``; XLS files are read
    dtype=str by the shared reader, which also detects the 2005 mislabeled
    ``.csv``-that-is-XLS via magic bytes). Year resolution: legacy eras carry
    no year column (filename year is authoritative); tidy eras carry
    ``LONG_SCHOOL_YEAR``, whose ending year is cross-checked against the
    filename so a misnamed file cannot mislabel a whole year.
    """
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

    if era in ("era_d", "era_e"):
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

    logger.info(
        "Processing %s as %s (year %d, %d rows)", path.name, era, year, df.height
    )
    func, args = ERA_ROUTES[era]
    return func(df, year, *args, manifest)


# =============================================================================
# Pinned legacy duplicate aggregation
# =============================================================================


def _aggregate_pinned_legacy_duplicates(
    combined: pl.DataFrame,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Sum the five pinned 2008-2009 partial-count duplicate key groups.

    The groups are proven partial counts of one entity (reconciliation
    arithmetic in the module docstring), so dedup would silently discard
    real bronze counts — they must be summed instead. The observed duplicate
    key set must EXACTLY equal ``EXPECTED_LEGACY_DUP_KEYS``; anything else
    raises, so an unproven future duplicate is never silently aggregated
    (it would instead hit ``assert_no_natural_key_collisions`` in main()).

    Null-poisoning sum semantics (see module docstring): ``num_tested`` sums
    the non-null components (all-null -> NULL); ``num_tests_taken`` and
    ``num_tests_3_or_higher`` go NULL when ANY component is suppressed;
    ``tests_3_or_higher_rate`` is recomputed from the aggregated counts.
    """
    is_dup = pl.len().over(NATURAL_KEYS) > 1
    dup_rows = combined.filter(is_dup)
    if dup_rows.height == 0:
        return combined

    observed = {
        (r["year"], r["district_code"], r["school_code"], r["detail_level"])
        for r in dup_rows.select("year", "district_code", "school_code", "detail_level")
        .unique()
        .to_dicts()
    }
    if observed != EXPECTED_LEGACY_DUP_KEYS:
        raise ValueError(
            "Unexpected duplicate natural-key group(s) — only the five pinned "
            f"2008-2009 partial-count groups may be summed. Observed: "
            f"{sorted(observed, key=str)}; expected: "
            f"{sorted(EXPECTED_LEGACY_DUP_KEYS, key=str)}"
        )

    aggregated = (
        dup_rows.group_by(NATURAL_KEYS)
        .agg(
            # num_tested: participation is published even when score detail
            # is suppressed, so the non-null sum is the documented
            # lower-bound total; all-null -> NULL.
            pl.when(pl.col("num_tested").null_count() == pl.col("num_tested").len())
            .then(None)
            .otherwise(pl.col("num_tested").sum())
            .cast(pl.Int64)
            .alias("num_tested"),
            # Test/score counts: ANY suppressed component -> NULL, so a
            # partial component never fabricates a complete-looking total
            # (or a misleading recomputed pass rate).
            pl.when(pl.col("num_tests_taken").null_count() > 0)
            .then(None)
            .otherwise(pl.col("num_tests_taken").sum())
            .cast(pl.Int64)
            .alias("num_tests_taken"),
            pl.when(pl.col("num_tests_3_or_higher").null_count() > 0)
            .then(None)
            .otherwise(pl.col("num_tests_3_or_higher").sum())
            .cast(pl.Int64)
            .alias("num_tests_3_or_higher"),
        )
        .with_columns(_pct_expr())
        .select(STANDARD_COLUMNS)
    )

    # Manifest accounting: rows collapsed per year = duplicate rows minus the
    # surviving aggregated entity rows.
    collapsed_per_year = (
        dup_rows.group_by("year")
        .agg(pl.len().alias("_rows"))
        .join(aggregated.group_by("year").len().rename({"len": "_groups"}), on="year")
        .with_columns((pl.col("_rows") - pl.col("_groups")).alias("_collapsed"))
    )
    for row in collapsed_per_year.iter_rows(named=True):
        manifest.record_filtered(
            row["year"], row["_collapsed"], "pinned_partial_count_rows_summed"
        )
    logger.warning(
        "Summed %d pinned legacy duplicate row(s) into %d entity row(s): %s",
        dup_rows.height,
        aggregated.height,
        sorted(observed, key=str),
    )
    return pl.concat([combined.filter(~is_dup), aggregated])


# =============================================================================
# §4b known-bad mask
# =============================================================================


def _null_2005_misassigned_district_rollups(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """NULL all four metrics on the 8 misassigned 2005 district rollups (§4b).

    The 2005 source's district ``:ALL`` rows for the 8 districts in
    ``MISASSIGNED_2005_DISTRICT_ROLLUPS`` publish totals that provably belong
    to other districts (exact donor matches / contradiction with the
    district's own suppression-free school sums and the 2004/2006 trend —
    full proof in the module docstring). The values cannot be each district's
    own totals, so they are publication errors, not data: all four metrics
    are NULLed while the rows (and the unaffected school-level rows) are
    preserved. The count is pinned — anything other than exactly 8 matching
    rows means the source or upstream logic changed, and raises.
    """
    mask = (
        (pl.col("year") == 2005)
        & (pl.col("detail_level") == "district")
        & pl.col("district_code").is_in(list(MISASSIGNED_2005_DISTRICT_ROLLUPS))
    )
    n = df.filter(mask).height
    if n != len(MISASSIGNED_2005_DISTRICT_ROLLUPS):
        raise ValueError(
            f"§4b 2005 rollup mask expected exactly "
            f"{len(MISASSIGNED_2005_DISTRICT_ROLLUPS)} pinned district rows, "
            f"found {n} — bronze or upstream logic changed; re-verify the "
            f"misassignment proof before masking"
        )
    # Every published triple on the 8 rows is fully non-null, so the masked
    # count is n for each metric (pct included — it derives from the counts).
    for col in METRIC_COLUMNS:
        manifest.record_masked(
            col,
            n,
            "2005_district_rollup_misassigned_at_source",
            years=[2005],
        )
    logger.warning(
        "§4b: NULLing all metrics on %d misassigned 2005 district rollup "
        "row(s) (districts %s) — published totals belong to other districts",
        n,
        sorted(MISASSIGNED_2005_DISTRICT_ROLLUPS),
    )
    return df.with_columns(
        [pl.when(mask).then(None).otherwise(pl.col(c)).alias(c) for c in METRIC_COLUMNS]
    )


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for advanced_placement_scores."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file (read-loss accounted per file).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR, extensions=[".csv", ".xls"]):
        result = transform_file(path, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize columns/dtypes across eras and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)
    logger.info("Combined %d rows across %d files", combined.height, len(all_dfs))

    # 3. Sum the pinned 2008-2009 partial-count duplicates (proven same-entity
    # rows; dedup would discard real counts), THEN the collision guard —
    # any remaining duplicate key with divergent metrics raises.
    combined = _aggregate_pinned_legacy_duplicates(combined, manifest)
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: each bronze file is a distinct year and eras don't overlap,
    # so no duplicates remain post-aggregation; sort_col="num_tests_taken" is
    # the safety net (prefer a reported count over a suppressed placeholder).
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code", "subject"],
        district_keys=["year", "district_code", "subject"],
        state_keys=["year", "subject"],
        sort_col="num_tests_taken",
    )

    # 4. Geography nulling (shared domain rules; idempotent here because the
    # sentinel-to-NULL mapping already ran in the era functions).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # §4b mask: the 8 misassigned 2005 district rollups (module docstring).
    # The 3 pinned num_tested > num_tests_taken rows are NOT masked — each
    # value is individually plausible and the wrong-side column is
    # unknowable, so they are preserved + documented per §4b's
    # extreme-vs-impossible test.
    combined = _null_2005_misassigned_district_rollups(combined, manifest)

    # Pre-export sanity. NULL-rate profile is era-driven and documented:
    # tidy-era suppression (TFS / empty cells) nulls ~30-50% of counts while
    # legacy years null ~0-11%, so legacy years sit BELOW the median and no
    # +20pp spike is expected.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
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

    Column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level`` — the contract's properties (and the validator's schema
    check) follow it.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Advanced Placement (AP) exam participation and qualifying-score "
            "counts for Georgia public high schools, with official district "
            "and state rollups, published by GOSA for 2004-2024. Each row "
            "reports the number of distinct students taking AP exams, the "
            "total exams administered, the count of exams scoring 3 or "
            "higher (College Board's qualifying threshold), and a derived "
            "pass rate (tests_3_or_higher_rate). Years 2011-2024 break the "
            "counts down by AP subject in addition to a cross-subject "
            "all_subjects total; years 2004-2010 publish only the "
            "cross-subject total."
        ),
        title="Advanced Placement (AP) Exam Scores",
        summary=(
            "AP college-level exam participation and pass rates (share scoring "
            "3 or higher) by Georgia school, district, and AP subject, "
            "2004-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Ending calendar year of the school year (2024 = the "
                    "2023-24 school year). 2011-2024 sources carry a "
                    "LONG_SCHOOL_YEAR column whose ending year is "
                    "cross-checked against the filename; 2004-2010 sources "
                    "have no year column and the filename year is used."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "GOSA district code (FK to districts dimension): 3-digit "
                    "zero-padded county/city codes or 7-digit charter codes. "
                    "NULL on state-level rows. Bronze aggregate sentinels "
                    "(ALL / DISTRICT_ALL) map to NULL."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0103",
                "description": (
                    "GOSA school code, zero-padded to 4 characters (composite "
                    "FK to schools dimension with district_code; not globally "
                    "unique on its own). NULL on district- and state-level "
                    "rows. Bronze aggregate sentinels (ALL / SCHOOL_ALL / "
                    "DISTRICT_ALL) map to NULL."
                ),
            },
            {
                "name": "subject",
                "type": "string",
                "nullable": False,
                "example": "calculus_a",
                "validValues": sorted(set(SUBJECT_MAP.values())),
                "short_description": (
                    "Which AP exam subject the row covers; all_subjects is the "
                    "cross-subject total (distinct students, not a sum of the "
                    "per-subject rows)."
                ),
                "description": (
                    "AP subject (snake_case recode of the source's "
                    "TEST_CMPNT_TYP_NM). all_subjects is the cross-subject "
                    "aggregate: the only value present for 2004-2010 (the "
                    "legacy sources have no per-subject breakdown) and one "
                    "row per entity alongside the per-subject rows for "
                    "2011-2024. all_subjects rows are NOT the sum of the "
                    "subject rows — num_tested counts distinct students "
                    "across subjects there. calculus_a is GOSA's literal "
                    "label for AP Calculus AB (it pairs with calculus_bc), "
                    "not a normalization error; physics_b and latin_vergil "
                    "are discontinued legacy AP exams retained for the years "
                    "they were administered."
                ),
            },
            {
                "name": "num_tested",
                "type": "int64",
                "unit": "count",
                "example": 17,
                "null_meaning": (
                    "Suppressed by GOSA (TFS / Too Few Students marker, or a "
                    "blank cell in 2004-2007 and 2011-2022 sources), or one "
                    "of the 8 masked 2005 district rollup rows (misassigned "
                    "at source — see notes)."
                ),
                "description": (
                    "Number of distinct students who sat at least one AP exam "
                    "(all_subjects rows) or who sat the specific subject's "
                    "exam (per-subject rows). Summing per-subject num_tested "
                    "double-counts students who took multiple subjects; "
                    "summing school rows can likewise slightly exceed the "
                    "published district/state rollups (median gap 2) because "
                    "the rollup counts each student once even when "
                    "school-level attribution counts a mid-year mover at "
                    "more than one school. Three source rows publish "
                    "num_tested greater than num_tests_taken — impossible if "
                    "both counts were accurate, but the wrong-side column is "
                    "unknowable, so the published values are preserved and "
                    "documented: 2005 district 611 school 0204 (Rutland HS, "
                    "33 students / 23 tests) and 2008 district 652 (Elbert "
                    "County, 10/9, appearing on both the school 0176 row and "
                    "the single-school district row)."
                ),
            },
            {
                "name": "num_tests_taken",
                "type": "int64",
                "metric_component": "denominator",
                "unit": "count",
                "example": 17,
                "null_meaning": (
                    "Suppressed by GOSA (TFS / Too Few Students marker, or a "
                    "blank cell — the dominant suppression form in 2004-2007 "
                    "and 2011-2019 sources), or one of the 8 masked 2005 "
                    "district rollup rows (misassigned at source — see "
                    "notes)."
                ),
                "description": (
                    "Total AP exams administered (a student can take exams in "
                    "multiple subjects, and the College Board counts each "
                    "exam). 47 of 414 bronze rows in 2004 leave this blank; "
                    "2011-2019 sources suppress via empty cells, 2020-2024 "
                    "via TFS."
                ),
            },
            {
                "name": "num_tests_3_or_higher",
                "type": "int64",
                "metric_component": "numerator",
                "unit": "count",
                "example": 12,
                "null_meaning": (
                    "Suppressed by GOSA (TFS / Too Few Students marker, or a "
                    "blank/empty cell), or one of the 8 masked 2005 district "
                    "rollup rows (misassigned at source — see notes). "
                    "Suppressed independently of the other two counts and "
                    "roughly twice as often in 2023-2024."
                ),
                "description": (
                    "Number of AP exams that scored 3 or higher (College "
                    "Board's qualifying threshold; scores run 1-5). Never "
                    "exceeds num_tests_taken where both are reported "
                    "(enforced by a quality check)."
                ),
            },
            {
                "name": "tests_3_or_higher_rate",
                "type": "float64",
                "key_metric": True,
                "unit": "proportion",
                "example": 0.706,
                "short_description": (
                    "Share of AP exams that scored 3 or higher (College "
                    "Board's qualifying threshold), on a 0-1 scale; higher is "
                    "better."
                ),
                "null_meaning": (
                    "Not derivable: num_tests_taken or num_tests_3_or_higher "
                    "is suppressed (or masked on the 8 misassigned 2005 "
                    "district rollup rows), or num_tests_taken is 0."
                ),
                "description": (
                    "Share of administered exams that scored 3 or higher, "
                    "derived by the transform as num_tests_3_or_higher / "
                    "num_tests_taken on the 0-1 scale (the pct_* "
                    "share-of-denominator companion to "
                    "num_tests_3_or_higher). 2004-2010 sources publish a "
                    "0-100 percentage column that is dropped and recomputed "
                    "(recomputed values agree within 0.0005 — source "
                    "rounding); 2011-2024 sources publish no rate column. "
                    "NULL when either count is suppressed or the denominator "
                    "is 0."
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
                "Three detail levels in every year, split by filename "
                "(schools.parquet / districts.parquet / states.parquet per "
                "year partition); aggregate rows carry NULL geography keys."
            ),
            (
                "subject axis: 2011-2024 rows carry 41 distinct AP subjects "
                "plus the all_subjects cross-subject total; 2004-2010 rows "
                "are always all_subjects. Filter to a consistent subject "
                "value before aggregating across rows."
            ),
            (
                "all_subjects rows are NOT derivable from per-subject rows: "
                "their num_tested counts distinct students across subjects "
                "(a student taking Calculus and Biology counts once), while "
                "subject rows count subject-level participants. The "
                "aggregate is carried verbatim from the source."
            ),
            (
                "Five 2008-2009 duplicate-key groups are partial counts of "
                "one entity published as two rows (e.g. Gwinnett + 'Gwinnett "
                "County'; Heritage High 722:0176 split across two snapshots) "
                "and are summed by the transform — proven by reconciliation "
                "against the same file's district/school totals. Counts go "
                "NULL when any component is suppressed."
            ),
            (
                "Three source rows publish num_tested > num_tests_taken "
                "(2005 Rutland HS 33/23; 2008 Elbert County 10/9 at school "
                "and district level). Impossible if both counts were "
                "accurate, but neither side is provably the wrong one — "
                "preserved and pinned as exclusions in the "
                "num_tested_within_num_tests_taken quality check."
            ),
            (
                "Masked per data-cleaning-standards 4b: the 2005 source's "
                "district rollup rows for 8 districts publish totals that "
                "provably belong to OTHER districts (an "
                "alphabetical-adjacency shift plus an exact Jefferson "
                "County/Jefferson City swap in GOSA's rollup generation), "
                "so all four metrics are NULL on those rows. Proof: 2005 "
                "has zero suppression and 120 of 128 district rollups equal "
                "their own school-row sums exactly; the 8 exceptions decode "
                "by exact donor matches — Jefferson County 681 <-> "
                "Jefferson City 779 (swap); Putnam 717 carries Rabun 719's "
                "totals; Randolph 720 carries Richmond 721's; Richmond 721 "
                "carries Rockdale 722's; Rockdale 722 carries Rome City "
                "785's (Rome's own rollup is also correct — served twice); "
                "Screven 724 (published 167/202/111 vs own sums 67/104/51) "
                "and Wilkinson 758 (37/38/14 vs 10/11/0) contradict their "
                "own sums with no identified donor. The 2004-to-2006 trend "
                "confirms every case. The affected districts' 2005 "
                "school-level rows are correct and preserved; because 2005 "
                "has no suppression, analysts can recover a district's true "
                "2005 totals by summing its school rows (exact for the "
                "test-count metrics; num_tested may overcount mid-year "
                "movers slightly)."
            ),
            (
                "Dropped rows: the 2004 trailing junk row (NUL-byte ID, no "
                "metrics), the 2005 malformed 644:xxxx school row (excluded "
                "from GOSA's own 644:ALL rollup, which equals the district's "
                "school-row sums without it), and the 2007 678:9999 "
                "placeholder-school row (all metrics 0)."
            ),
            (
                "Suppression: 2004-2007 blank cells; 2008-2010 'Too Few "
                "Students'; 2011-2019 empty cells in the test/score counts "
                "plus TFS in num_tested (2016-2018 publish unsuppressed "
                "student counts down to n=1); 2020-2024 TFS (2020-2022 also "
                "have 70/132/160 residual empty cells in the qualifying "
                "count). All forms become NULL."
            ),
            (
                "Schema eras: A (2004-2007 wide, SysSchoolID; the 2005 file "
                "is an XLS binary mislabeled .csv, detected via magic "
                "bytes), B (2008-2009 wide, SysSchoolid + System Name), C "
                "(2010 wide, Sysschoolid + the literal 'School or Distict  "
                "Name' header), D (2011-2022 tidy per-subject, "
                "NOTESTS_3ORHIGHER), E (2023-2024 tidy, adds #RPT_NAME + "
                "DETAIL_LVL_DESC, renames to NUMBER_TESTS_3_OR_HIGHER)."
            ),
        ],
        quality_checks=[
            {
                "name": "tests_3_or_higher_within_tests_taken",
                "description": (
                    "Qualifying exams are a subset of administered exams: "
                    "where both counts are reported, num_tests_3_or_higher "
                    "cannot exceed num_tests_taken. Holds with zero "
                    "violations in every bronze year 2004-2024."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE num_tests_3_or_higher IS NOT NULL "
                    "AND num_tests_taken IS NOT NULL "
                    "AND num_tests_3_or_higher > num_tests_taken"
                ),
                "mustBe": 0,
            },
            {
                "name": "num_tested_within_num_tests_taken",
                "description": (
                    "Every tested student sits at least one exam, so "
                    "num_tested cannot exceed num_tests_taken where both are "
                    "reported — except the three pinned source defects "
                    "preserved per data-cleaning-standards section 4b: 2005 "
                    "district 611 school 0204 (33/23) and 2008 district 652 "
                    "(10/9, on the school 0176 row and the district row). "
                    "Any other violation is a new defect and fails."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE num_tested IS NOT NULL "
                    "AND num_tests_taken IS NOT NULL "
                    "AND num_tested > num_tests_taken "
                    "AND NOT (year = 2005 AND district_code = '611' "
                    "AND school_code = '0204') "
                    "AND NOT (year = 2008 AND district_code = '652' "
                    "AND (school_code = '0176' OR school_code IS NULL))"
                ),
                "mustBe": 0,
            },
            {
                "name": "tests_3_or_higher_rate_matches_counts",
                "description": (
                    "tests_3_or_higher_rate is derived by the transform as "
                    "num_tests_3_or_higher / num_tests_taken; wherever the "
                    "inputs are present with a positive denominator the "
                    "stored value must equal the recomputed ratio."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE tests_3_or_higher_rate IS NOT NULL "
                    "AND num_tests_taken IS NOT NULL AND num_tests_taken > 0 "
                    "AND num_tests_3_or_higher IS NOT NULL "
                    "AND ABS(tests_3_or_higher_rate - "
                    "(CAST(num_tests_3_or_higher AS DOUBLE) / "
                    "num_tests_taken)) > 1e-9"
                ),
                "mustBe": 0,
            },
            {
                "name": "tests_3_or_higher_rate_co_null_with_inputs",
                "description": (
                    "Co-null contract of the derived rate: "
                    "tests_3_or_higher_rate is non-NULL if and only if "
                    "num_tests_taken is reported and positive and "
                    "num_tests_3_or_higher is reported."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE (tests_3_or_higher_rate IS NOT NULL "
                    "AND (num_tests_taken IS NULL OR num_tests_taken = 0 "
                    "OR num_tests_3_or_higher IS NULL)) "
                    "OR (tests_3_or_higher_rate IS NULL "
                    "AND num_tests_taken IS NOT NULL AND num_tests_taken > 0 "
                    "AND num_tests_3_or_higher IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "district_not_below_own_max_school",
                "description": (
                    "A district rollup can never be smaller than its own "
                    "largest school row for the same year and subject (a "
                    "school's students/tests are a subset of its "
                    "district's). Pins the 2005 misassigned-rollup defect "
                    "class: pre-mask the only violators were the defective "
                    "2005 rows (districts 681, 722); post-mask zero. "
                    "Written as one conditional-aggregation scan per "
                    "data-cleaning-standards section 15b (never a "
                    "self-join)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, subject, "
                    "MAX(CASE WHEN school_code IS NULL THEN num_tested END) "
                    "AS d_nt, "
                    "MAX(CASE WHEN school_code IS NOT NULL THEN num_tested "
                    "END) AS s_nt, "
                    "MAX(CASE WHEN school_code IS NULL THEN num_tests_taken "
                    "END) AS d_tt, "
                    "MAX(CASE WHEN school_code IS NOT NULL THEN "
                    "num_tests_taken END) AS s_tt, "
                    "MAX(CASE WHEN school_code IS NULL THEN "
                    "num_tests_3_or_higher END) AS d_t3, "
                    "MAX(CASE WHEN school_code IS NOT NULL THEN "
                    "num_tests_3_or_higher END) AS s_t3 "
                    "FROM {object} WHERE district_code IS NOT NULL "
                    "GROUP BY year, district_code, subject"
                    ") WHERE "
                    "(d_nt IS NOT NULL AND s_nt IS NOT NULL AND d_nt < s_nt) "
                    "OR (d_tt IS NOT NULL AND s_tt IS NOT NULL "
                    "AND d_tt < s_tt) "
                    "OR (d_t3 IS NOT NULL AND s_t3 IS NOT NULL "
                    "AND d_t3 < s_t3)"
                ),
                "mustBe": 0,
            },
            {
                "name": "legacy_years_all_subjects_only",
                "description": (
                    "2004-2010 sources have no per-subject breakdown — every "
                    "row in those years must carry subject = 'all_subjects'."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE year <= 2010 AND subject != 'all_subjects'"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
