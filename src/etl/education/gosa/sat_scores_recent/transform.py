"""Transform bronze sat_scores_recent files into gold fact tables.

Source: Governor's Office of Student Achievement (GOSA) — SAT Scores (most
recent administration), 2004-2024 (22 bronze files; 2016 ships in two
formats). For every Georgia public high school, plus official district and
state rollups, reports the average SAT score and the number of students
tested per SAT section (`test_component`), using each student's most-recent
attempt. The sibling topic ``sat_scores_highest`` covers best-attempt scores.

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Six bronze schema eras, one long gold fact.**
    * Era 1 (2004-2006, wide 72 cols, verbose demographic suffixes) and
      Era 2 (2007, same shape, single-letter suffixes ``0ABFHMNORW``):
      state/district/school rows encoded in a compound ``SysSchoolID``
      (``ALL:ALL`` / ``{d}:ALL`` / ``{d}:{s}``). The ``Recent Total`` /
      ``Recent Verbal`` / ``Recent Math`` score columns are unpivoted into
      one row per (demographic x test_component); the per-demographic
      ``Number Taken`` count attaches to each of that demographic's
      component rows.
    * Era 3 (2008-2010, wide 52 cols): adds ``Recent Writing`` and a
      standalone non-suffixed ``Recent Total`` (the V+M+W composite,
      600-2400, All Students only — distinct from the suffixed
      ``Recent Total{code}`` V+M composite). Drops the ``R`` suffix. A
      legend row (NULL ``SysSchoolId``) is dropped per file.
    * Era 4 (2011-2015 + 2016_old_format, long 15 cols), Era 5 (2016_new
      + 2017-2022, long 14 cols — NATIONAL_AVG dropped), Era 6 (2023-2024,
      long 17 cols — adds ``#ASSMT_CD``/``HIGHEST_RECENT_IND`` constants,
      restores NATIONAL_AVG, renames the district column): one bronze row
      per (school x test_component). School rows map 1:1; district and
      state rows are materialized from the side-by-side ``DSTRCT_*`` /
      ``STATE_*`` context columns, never re-aggregated from school rows
      (GOSA suppresses school metrics under n<10 while publishing
      unsuppressed official aggregates).
- **High* columns are NOT this topic's data.** The 2004-2010 bronze files
  are byte-identical to ``sat_scores_highest``'s (same SHA-256) — one shared
  publication carrying both measure families. This transform takes only the
  ``Recent*`` columns; the ``High*`` best-attempt columns belong to the
  sibling topic, which extracts them from its own copy of the same files.
- **Demographics exist only in Eras 1-3.** Eras 4-6 publish
  ``SUBGRP_DESC = 'All Students'`` on every row (verified for all 15 long
  files) -> ``demographic = 'all'``. Eras 1-3 demographic vocabulary:
  All Students, Asian, Black, Female, Hispanic, Male, American Indian,
  O (Other), R (no-response; data only in 2004), White.
- **Asian is the combined Asian/Pacific Islander bucket (§5b).** The
  average-score math test is inapplicable, so the structural test applies:
  no era of this bronze (nor of the byte-identical sibling) ever publishes a
  separate Pacific Islander row or column, and sibling GOSA reports from the
  same vintage use the explicit "Asian/Pacific Islander" label for the same
  concept (sat_scores_recent is on the §5b known-combined list). The
  topic-local ``ASIAN_PI_REMAP`` rewrites the bronze label BEFORE
  ``normalize_demographic_column`` so it canonicalizes to
  ``asian_pacific_islander``, never bare ``asian``. ``DEMOGRAPHIC_ALIASES``
  is not touched globally.
- **No demographic-collision aggregation needed.** Each Era 1-3 label maps
  to a distinct canonical key (verified: 10 labels -> 10 canonicals), so no
  two raw labels can collapse onto one natural key;
  ``assert_no_natural_key_collisions`` still guards the assumption.
- **Zero-sentinel suppression in Eras 1-3.** The wide files encode "no test
  takers in this demographic" as a paired (score=0, count=0) cell (e.g. 181
  Asian zeros in 2005); 2004 uses blanks instead. A zero score is impossible
  on any SAT scale (min section score 200), so ``avg_score`` is NULLed
  whenever ``num_tested == 0`` while the real zero count is kept. This is a
  suppression-encoding repair at melt time (like TFS -> NULL), not a §4b
  mask. The single score-with-zero-count case (2010 charter district
  7830103 'CCAT', standalone V+M+W = 1450 with Number Taken0 = 0) is nulled
  by the same rule — an average over zero test-takers cannot exist.
- **Empty unpivoted cells are dropped (Eras 1-3 only).** A melted row where
  BOTH metrics are NULL is a blank wide-format cell (demographic not
  reported for that entity), not an observation — dropping it avoids
  millions of all-null rows (most 2004 elementary-school rows are entirely
  blank). Recorded via ``record_filtered``. Era 4-6 school rows with TFS
  suppression are real per-school observations at the topic grain and ARE
  preserved as (NULL, NULL) rows.
- **2004 file needs a pinned reader.** The polars/pandas CSV chain mangles
  the file (a quoted-comma school name plus two truncated trailing
  fragments defeat it, silently losing 26 rows). The stdlib ``csv`` module
  parses all 2245 data rows correctly; the 2 short fragments (48 and 11
  fields — truncated re-appends of the Wilkinson County district row and
  the Mays High School row, both of which appear intact earlier in the
  file) are dropped with a read-loss note. The file also re-appends a
  25-row trailing block of intact duplicate rows (districts 758/759/761 —
  e.g. ``758:ALL`` Wilkinson County, populated ``759:176`` Worth County
  High School and ``759:ALL`` Worth County); every twin is byte-identical,
  and dedup removes the 72 melted duplicate rows.
- **2016 dual-format files: keep both.** ``2016_old_format`` carries the
  pre-redesign components (Combined/Mathematics/Reading/Writing) for the
  2015-16 cohort; ``2016_new_format`` carries the redesigned-SAT components.
  The vocabularies are disjoint, so the natural key never collides; dropping
  either would discard legitimate cohort data.
- **test_component vocabulary.** Pre-redesign single sections are unified
  across the 2004-2010 wide vs 2011-2016 long file-format boundary
  (``Recent Verbal`` == 2011 ``Verbal`` == 2012+ ``Reading`` -> ``reading``;
  same 200-800 section), but the vocabulary is NOT unified across the 2016
  SAT redesign: old-SAT ``combined`` (V+M+W, 600-2400) vs redesigned
  ``combined_test_score`` (Math+EBRW, 400-1600) etc. stay distinct because
  they measure on different scales.
- **District/state materialization uses a modal (count, score) PAIR vote.**
  The Era 4-6 context columns are constant within their groups in every
  file except 2024, where three rows (Bishop Hall Charter 736:0100,
  McDonough Middle 675:4050, Pleasant Valley Innovative 705:0108 — all with
  NULL school metrics) carry alternate-scale aggregates on the Combined
  Test Score component (e.g. state pair (37140, 505.4) vs the true
  (32976, 1043.6) carried by 435 school-supported rows). The vote picks,
  per group: (1) pairs observed on school-supported rows, then (2) highest
  occurrence count, then (3) earliest bronze row — so the three anomalous
  rows can never outvote the official aggregates. Aggregating the pair as a
  unit prevents splicing a count from one bronze row with a score from
  another. Groups whose count column is entirely NULL (fully TFS-suppressed
  districts) are preserved as (NULL, NULL) district rows.
- **National benchmark data dropped.** The Era 4-6 ``NATIONAL_*`` columns
  are out of scope — education detail levels are school/district/state per
  ``src/etl/education/CLAUDE.md``, and national rows would collide with
  state rows on the natural key.
- **§4b known-bad masks.** ``_null_invalid_sat_scores`` NULLs ``avg_score``
  values outside their component's physical SAT scale (rows and
  ``num_tested`` preserved): sections 200-800, V+M composites 400-1600,
  V+M+W composites 600-2400, essay dimensions 2-8, essay total 6-24. The 16
  known defects: 2009 Carroll County district V+M+W=2751; 2010 Rockdale
  County High (722:3052) V+M+W=3114 / V+M=2133 / Verbal=1039 / Math=1094 /
  Writing=981 and Elberta Open Campus (676:3050) Verbal=819; plus nine
  2011-2015 school/district ``writing`` averages below the 200 floor (as
  low as 92). The redesigned ``reading_test_score`` / ``writlang_test_score``
  are excluded: GOSA publishes them on a rescaled axis (observed 180-338,
  consistent with 10x the College Board 10-40 test-score scale, NOT the
  200-800 the bronze doc suggests) with no clean published ceiling, so they
  carry no enforceable bound. Extreme-but-conceivable values (e.g. Elberta's
  2010 V+M+W total of 2287, <= 2400) are preserved and documented.
- **``num_tested`` is Float64 — documented §16 exception.** Era 5-6 bronze
  publishes fractional ``INSTN_NUM_TESTED_CNT`` on the Combined Test Score
  component (the equal-weight mean of the three section test-taker counts --
  Math, Reading, Writing & Language -- not a headcount, e.g. (47+37+37)/3 ->
  40.3) and fractional district counts in 2023-24 (e.g. 4159.3). Verified
  against the source: exact thirds where published full-precision, rounded
  to one decimal from ~2020. Rounding to an integer would silently lose
  precision; the column keeps its canonical name and the Float64 type
  signals that fractional values are possible. Do NOT round.
- **Dedup tie-break.** Every bronze file covers a distinct year, eras do
  not overlap, and the two 2016 files use disjoint component vocabularies,
  so duplicates can only be within-file repeats. The one known case is
  2004's re-appended 25-row trailing block (districts 758/759/761 — e.g.
  Wilkinson County ``758:ALL``, Worth County High ``759:176``): all twins
  are byte-identical, and dedup removes the 72 melted duplicate rows.
  ``sort_col="num_tested"`` prefers the row with a reported, larger count
  over a suppressed placeholder — for identical twins it simply keeps one.
"""

import csv
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

TOPIC = "sat_scores_recent"
BRONZE_DIR = Path("data/bronze/education/gosa/sat_scores_recent")
GOLD_DIR = Path("data/gold/education/sat_scores_recent")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Era 4-6 TEST_CMPNT_TYP_CD -> canonical test_component. The two redesigned
# test-score codes carry a literal double space before "Score" — load-bearing,
# preserved verbatim. 2011's "Verbal" and 2012+'s "Reading" are the same
# pre-redesign 200-800 section -> one canonical value.
TEST_COMPONENT_MAP: dict[str, str] = {
    # Pre-redesign SAT (Era 4: 2011-2015 + 2016_old_format)
    "Combined": "combined",
    "Mathematics": "mathematics",
    "Verbal": "reading",
    "Reading": "reading",
    "Writing": "writing",
    # Redesigned SAT (Era 5: 2016_new_format-2022; Era 6: 2023-2024)
    "Combined Test Score": "combined_test_score",
    "Math Section Score - New": "math_section_score",
    "Evidence Based Reading and Writing - New": "evidence_based_reading_and_writing",
    "Reading Test  Score - New": "reading_test_score",
    "WritLang Test  Score - New": "writlang_test_score",
    "Essay Reading Score - New": "essay_reading_score",
    "Essay Analysis Score - New": "essay_analysis_score",
    "Essay Writing Score - New": "essay_writing_score",
    "Essay Total": "essay_total",
}

# Era 1-3 wide score-column prefixes -> canonical test_component. The
# suffixed "Recent Total" is the V+M composite in every wide era; Era 3's
# standalone non-suffixed "Recent Total" (V+M+W) is handled separately.
ERA12_COMPONENTS: dict[str, str] = {
    "Recent Total": "verbal_math",
    "Recent Verbal": "reading",
    "Recent Math": "mathematics",
}
ERA3_SUFFIXED_COMPONENTS: dict[str, str] = {
    **ERA12_COMPONENTS,
    "Recent Writing": "writing",
}

# Era 1 (2004-2006) demographic tokens, verbatim from column names. Single
# letters O / R concatenate without a space ("Recent TotalO"); verbose
# tokens take a space ("Recent Total Asian").
ERA1_DEMOGRAPHIC_TOKENS: list[str] = [
    "All Students",
    "Asian",
    "Black",
    "Female",
    "Hispanic",
    "Male",
    "American Indian",
    "O",
    "R",
    "White",
]

# Era 2 (2007) single-letter suffixes -> the Era 1 verbose label vocabulary
# (so one demographic-recording path serves both). Era 3 drops the R slot.
ERA2_SUFFIX_TO_LABEL: dict[str, str] = {
    "0": "All Students",
    "A": "Asian",
    "B": "Black",
    "F": "Female",
    "H": "Hispanic",
    "M": "Male",
    "N": "American Indian",
    "O": "O",
    "R": "R",
    "W": "White",
}
ERA3_SUFFIX_TO_LABEL: dict[str, str] = {
    k: v for k, v in ERA2_SUFFIX_TO_LABEL.items() if k != "R"
}

# Topic-local §5b remap: this bronze's bare "Asian" is the pre-1997 OMB
# combined Asian + Pacific Islander bucket (structural test — no separate
# Pacific Islander row/column exists in any era, and sibling GOSA reports
# use the explicit combined label). Applied BEFORE
# normalize_demographic_column; never edit DEMOGRAPHIC_ALIASES globally.
ASIAN_PI_REMAP: dict[str, str] = {"Asian": "Asian/Pacific Islander"}

# Era-detection signatures, most-specific first. Era 4 is an Era 5 superset
# (NATIONAL_AVG_SCORE_VAL); Era 6 renames the district column and adds the
# #ASSMT_CD flag. Era 1 vs Era 2 differ by demographic-suffix style; Era 3
# renames the ID column to lowercase-d SysSchoolId.
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_6": ["#ASSMT_CD", "HIGHEST_RECENT_IND", "SCHOOL_DSTRCT_CD"],
    "era_4": ["LONG_SCHOOL_YEAR", "SCHOOL_DISTRCT_CD", "NATIONAL_AVG_SCORE_VAL"],
    "era_5": ["LONG_SCHOOL_YEAR", "SCHOOL_DISTRCT_CD", "TEST_CMPNT_TYP_CD"],
    "era_1": ["SysSchoolID", "Recent Total All Students"],
    "era_2": ["SysSchoolID", "SchoolNme", "Recent Total0"],
    "era_3": ["SysSchoolId", "Recent Writing0"],
}

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "test_component",
    "num_tested",
    "avg_score",
    "detail_level",
]

# num_tested is Float64 — documented §16 exception (fractional Era 5-6
# counts on the Combined Test Score component). Do not "fix" to Int64.
TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "demographic": pl.Utf8,
    "test_component": pl.Utf8,
    "num_tested": pl.Float64,
    "avg_score": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = ["num_tested", "avg_score"]

NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "test_component",
    "detail_level",
]

# Physical SAT scale per test_component (§4b mask + contract quality check).
# An entity's AVERAGE cannot fall outside the per-student score range.
# reading_test_score / writlang_test_score are intentionally absent: GOSA
# publishes them on a rescaled axis (observed 180-338; consistent with 10x
# the College Board 10-40 test-score scale) with no clean published ceiling,
# so no value is provably impossible.
SAT_SCORE_RANGES: dict[str, tuple[float, float]] = {
    # 200-800 single sections (pre-redesign and redesigned)
    "reading": (200.0, 800.0),
    "mathematics": (200.0, 800.0),
    "writing": (200.0, 800.0),
    "math_section_score": (200.0, 800.0),
    "evidence_based_reading_and_writing": (200.0, 800.0),
    # Two-section composites
    "verbal_math": (400.0, 1600.0),
    "combined_test_score": (400.0, 1600.0),
    # Three-section composites
    "verbal_math_writing": (600.0, 2400.0),
    "combined": (600.0, 2400.0),
    # Essay dimensions (2 readers x 1-4) and their published total
    "essay_reading_score": (2.0, 8.0),
    "essay_analysis_score": (2.0, 8.0),
    "essay_writing_score": (2.0, 8.0),
    "essay_total": (6.0, 24.0),
}

# Era 4-6 metric column pairs per detail level: (count column, score column).
LONG_LEVEL_METRICS: dict[str, tuple[str, str]] = {
    "school": ("INSTN_NUM_TESTED_CNT", "INSTN_AVG_SCORE_VAL"),
    "district": ("DSTRCT_NUM_TESTED_CNT", "DSTRCT_AVG_SCORE_VAL"),
    "state": ("STATE_NUM_TESTED_CNT", "STATE_AVG_SCORE_VAL"),
}


# =============================================================================
# Casting helpers
# =============================================================================


def _to_float_expr(col: str) -> pl.Expr:
    """Cast a bronze metric column to Float64 through a string round-trip.

    Bronze mixes representations per year (all-Utf8 reads, xls strings,
    2024's trailing-dot "1973891.", Era 2's literal "NULL"). Casting to Utf8
    first, stripping, then a non-strict Float64 cast handles all of them;
    non-numeric residue becomes NULL.
    """
    return pl.col(col).cast(pl.Utf8).str.strip_chars().cast(pl.Float64, strict=False)


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
# 2004 pinned reader
# =============================================================================


def _read_2004_csv(path: Path) -> tuple[pl.DataFrame, int, int]:
    """Read the 2004 file with the stdlib csv module (pinned repair).

    The polars/pandas reader chain mangles this file (a quoted-comma school
    name plus two truncated trailing fragments defeat it, silently losing 26
    rows); stdlib ``csv`` parses all 2245 well-formed data rows. The two
    short rows (48 and 11 fields) are truncated re-appends of rows that
    appear intact earlier in the file (758:ALL Wilkinson County, 761:182
    Mays High School) — dropped here and accounted as read loss with a note.

    Returns:
        (DataFrame with all-Utf8 columns, raw_data_rows, parsed_rows).
    """
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    header = rows[0]
    data = [r for r in rows[1:] if r]
    good = [r for r in data if len(r) == len(header)]
    bad = [r for r in data if len(r) != len(header)]
    if bad:
        logger.warning(
            "2004: dropping %d truncated row fragment(s) with %s fields "
            "(re-appends of rows present intact elsewhere): %s",
            len(bad),
            [len(r) for r in bad],
            [r[:2] for r in bad],
        )
    df = pl.DataFrame(
        {h: [r[i] for r in good] for i, h in enumerate(header)},
        schema={h: pl.Utf8 for h in header},
    )
    # Empty strings are this era's blank cells -> NULL like every other read.
    df = df.with_columns(
        pl.when(pl.col(c).str.strip_chars() == "")
        .then(None)
        .otherwise(pl.col(c))
        .alias(c)
        for c in df.columns
    )
    return df, len(data), len(good)


# =============================================================================
# Eras 1-3 (2004-2010): compound-ID wide format with demographic suffixes
# =============================================================================


def _split_compound_id(
    df: pl.DataFrame,
    id_col: str,
    year: int,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Classify and split the Era 1-3 compound ``SysSchool*`` ID.

    Adds ``detail_level`` (state/district/school) plus ``_district_raw`` /
    ``_school_raw`` part columns. Drops the Era 3 legend row (NULL id) and
    any malformed IDs, both logged via ``record_filtered``.
    """
    # Era 3 files carry one legend row (NULL id; explanatory text in the
    # Recent Total cells). It is documentation, not data.
    n_legend = df.filter(pl.col(id_col).is_null()).height
    if n_legend:
        logger.info(
            "Year %d: dropping %d legend row(s) with NULL %s", year, n_legend, id_col
        )
        manifest.record_filtered(year, n_legend, "era3_legend_row")
        df = df.filter(pl.col(id_col).is_not_null())

    # The ALL sentinel comparison is case-insensitive because 2005 publishes
    # `All:All` while the other years publish `ALL:ALL`.
    ids = pl.col(id_col).cast(pl.Utf8).str.strip_chars()
    df = df.with_columns(ids.alias("_id"))
    df = df.with_columns(pl.col("_id").str.to_uppercase().alias("_id_upper"))
    df = df.with_columns(
        pl.when(pl.col("_id_upper") == "ALL:ALL")
        .then(pl.lit("state"))
        .when(pl.col("_id_upper").str.ends_with(":ALL"))
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .alias("detail_level")
    )

    # Split the compound ID on the first colon into district / school parts.
    df = df.with_columns(
        pl.col("_id")
        .str.split_exact(":", 1)
        .struct.rename_fields(["_district_raw", "_school_raw"])
        .alias("_parts")
    ).unnest("_parts")

    # Malformed-ID guard: district part must be digits for district/school
    # rows, school part must be digits for school rows. No repair proof
    # exists for unknown malformations, so they are dropped loudly.
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

    # Geography keys: zero-pad per domain CLAUDE.md (zfill preserves 7-digit
    # charter codes); aggregate levels get NULLs (null_aggregate_geography
    # re-asserts this in main()).
    return df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.when(pl.col("detail_level") == "state")
        .then(None)
        .otherwise(pl.col("_district_raw").str.zfill(3))
        .alias("district_code"),
        pl.when(pl.col("detail_level") != "school")
        .then(None)
        .otherwise(pl.col("_school_raw").str.zfill(4))
        .alias("school_code"),
    )


def _melt_wide_demographics(
    df: pl.DataFrame,
    year: int,
    cells: list[tuple[str, str, str, str, str]],
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Unpivot Era 1-3 (demographic x component) wide cells into long rows.

    Args:
        df: DataFrame with year/geography/detail_level columns already built.
        year: Reporting year (logging / manifest).
        cells: One tuple per (demographic, component) cell:
            (raw_label, component_pseudo_label, gold_component, score_col,
            count_col). ``component_pseudo_label`` is the disambiguated
            bronze prefix recorded in the manifest (the categorical lives in
            column HEADERS in these eras, not in row values) — it keeps the
            two distinct "Recent Total" semantics (suffixed V+M vs Era 3
            standalone V+M+W) separate in the manifest key space.
        manifest: Manifest for categorical / filter recording.

    Returns:
        Long DataFrame with STANDARD_COLUMNS.
    """
    id_cols = ["year", "district_code", "school_code", "detail_level"]
    parts: list[pl.DataFrame] = []
    component_map: dict[str, str] = {}
    demo_map: dict[str, str] = {}

    for raw_label, component_label, component, score_col, count_col in cells:
        component_map[component_label] = component
        # Composed effective demographic map: bronze label -> canonical key
        # (via the §5b Asian remap where it applies). Recorded so the
        # manifest shows the aliases actually hit, with unmapped guard.
        demo_map[raw_label] = DEMOGRAPHIC_ALIASES[
            ASIAN_PI_REMAP.get(raw_label, raw_label).upper()
        ]
        count_expr = _to_float_expr(count_col)
        score_expr = _to_float_expr(score_col)
        parts.append(
            df.select(
                *id_cols,
                pl.lit(raw_label).alias("_demo_raw"),
                pl.lit(component_label).alias("_component_raw"),
                pl.lit(component).alias("test_component"),
                count_expr.alias("num_tested"),
                # Zero-sentinel: (0, 0) pairs mean "no test takers"; a zero
                # score is impossible on any SAT scale, so the score is
                # NULLed whenever the count is zero (the real 0 count stays).
                pl.when(count_expr == 0)
                .then(None)
                .otherwise(score_expr)
                .alias("avg_score"),
            )
        )

    long_df = pl.concat(parts)

    # Canonical demographic path (§5): topic-local Asian/PI remap first,
    # then the shared normalizer. Recorded with the composed effective map.
    long_df = long_df.with_columns(
        normalize_demographic_column(pl.col("_demo_raw").replace(ASIAN_PI_REMAP)).alias(
            "demographic"
        )
    )
    manifest.record_categorical(
        column="demographic",
        map_dict=demo_map,
        bronze_series=long_df["_demo_raw"],
        gold_series=long_df["demographic"],
    )
    manifest.record_categorical(
        column="test_component",
        map_dict=component_map,
        bronze_series=long_df["_component_raw"],
        gold_series=long_df["test_component"],
    )

    # A melted row where BOTH metrics are NULL is a blank wide cell (the
    # demographic was not reported for this entity), not an observation.
    n_empty = long_df.filter(
        pl.col("num_tested").is_null() & pl.col("avg_score").is_null()
    ).height
    if n_empty:
        logger.info(
            "Year %d: dropping %d empty (both-NULL) demographic x component cells",
            year,
            n_empty,
        )
        manifest.record_filtered(year, n_empty, "empty_demographic_component_cell")
        long_df = long_df.filter(
            pl.col("num_tested").is_not_null() | pl.col("avg_score").is_not_null()
        )
    return long_df.select(STANDARD_COLUMNS)


def _component_pseudo_label(prefix: str) -> str:
    """Disambiguate the suffixed "Recent Total" (V+M) in the manifest.

    Era 3 also has a standalone non-suffixed "Recent Total" column carrying
    the V+M+W composite; tagging the suffixed variant keeps both mappings
    visible in the manifest instead of one clobbering the other.
    """
    return "Recent Total (V+M, suffixed)" if prefix == "Recent Total" else prefix


def _era1_cells() -> list[tuple[str, str, str, str, str]]:
    """Era 1 (demographic, component) cell specs with verbose suffixes."""
    cells = []
    for token in ERA1_DEMOGRAPHIC_TOKENS:
        # Single-letter tokens concatenate without a space ("Recent TotalO");
        # verbose tokens take a space ("Recent Total Asian").
        sep = "" if token in ("O", "R") else " "
        count_col = f"Number Taken{sep}{token}"
        for prefix, component in ERA12_COMPONENTS.items():
            cells.append(
                (
                    token,
                    _component_pseudo_label(prefix),
                    component,
                    f"{prefix}{sep}{token}",
                    count_col,
                )
            )
    return cells


def _era23_cells(
    suffix_to_label: dict[str, str],
    components: dict[str, str],
) -> list[tuple[str, str, str, str, str]]:
    """Era 2/3 cell specs with single-letter concatenated suffixes."""
    cells = []
    for suffix, label in suffix_to_label.items():
        count_col = f"Number Taken{suffix}"
        for prefix, component in components.items():
            cells.append(
                (
                    label,
                    _component_pseudo_label(prefix),
                    component,
                    f"{prefix}{suffix}",
                    count_col,
                )
            )
    return cells


def _transform_era12(
    df: pl.DataFrame,
    year: int,
    era: str,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Transform an Era 1/2 wide file into long gold rows."""
    df = _split_compound_id(df, "SysSchoolID", year, manifest)
    cells = (
        _era1_cells()
        if era == "era_1"
        else _era23_cells(ERA2_SUFFIX_TO_LABEL, ERA12_COMPONENTS)
    )
    _require_columns(
        df, sorted({c[3] for c in cells} | {c[4] for c in cells}), f"{era} {year}"
    )
    return _melt_wide_demographics(df, year, cells, manifest)


def _transform_era3(
    df: pl.DataFrame,
    year: int,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Transform an Era 3 wide file (adds Writing + standalone V+M+W)."""
    df = _split_compound_id(df, "SysSchoolId", year, manifest)
    cells = _era23_cells(ERA3_SUFFIX_TO_LABEL, ERA3_SUFFIXED_COMPONENTS)
    # The standalone non-suffixed "Recent Total" is the V+M+W composite
    # (600-2400, All Students only) — a different measure from the suffixed
    # "Recent Total{code}" V+M composite, so it gets its own component value.
    cells.append(
        (
            "All Students",
            "Recent Total (V+M+W, standalone)",
            "verbal_math_writing",
            "Recent Total",
            "Number Taken0",
        )
    )
    _require_columns(
        df, sorted({c[3] for c in cells} | {c[4] for c in cells}), f"era_3 {year}"
    )
    return _melt_wide_demographics(df, year, cells, manifest)


# =============================================================================
# Eras 4-6 (2011-2024): long format with side-by-side aggregates
# =============================================================================


def _validate_long_constants(df: pl.DataFrame, year: int) -> None:
    """Hard-stop if the Era 4-6 constant columns carry unexpected values.

    SUBGRP_DESC must be 'All Students' (anything else changes the fact grain
    to demographic breakdowns and must be analyzed, not silently collapsed).
    Era 6's #ASSMT_CD must be 'SAT' and HIGHEST_RECENT_IND must be 'Recent'
    (anything else means foreign rows are mixed into this topic's bronze).
    """
    subgroups = df["SUBGRP_DESC"].drop_nulls().unique().to_list()
    if subgroups != ["All Students"]:
        raise ValueError(
            f"era_4/5/6 {year}: unexpected SUBGRP_DESC values {subgroups}; "
            "the transform assumes the All Students-only grain in long eras"
        )
    if "#ASSMT_CD" in df.columns:
        assessments = df["#ASSMT_CD"].drop_nulls().unique().to_list()
        if assessments != ["SAT"]:
            raise ValueError(f"era_6 {year}: unexpected #ASSMT_CD values {assessments}")
    if "HIGHEST_RECENT_IND" in df.columns:
        flags = df["HIGHEST_RECENT_IND"].drop_nulls().unique().to_list()
        if flags != ["Recent"]:
            raise ValueError(
                f"era_6 {year}: unexpected HIGHEST_RECENT_IND values {flags}"
            )


def _modal_aggregate_rows(
    base: pl.DataFrame,
    level: str,
    year: int,
) -> pl.DataFrame:
    """Materialize official district/state rows via a modal (count, score) vote.

    Bronze repeats the rollup columns on every school row. They are constant
    within their groups in every file except 2024, where three anomalous
    rows (all with NULL school metrics) carry alternate-scale aggregates on
    the Combined Test Score component. The vote aggregates the (count, score)
    pair AS A UNIT (never splicing a count from one bronze row with a score
    from another) and picks, per group: (1) pairs observed on at least one
    school-supported row, then (2) highest occurrence count, then (3) the
    earliest bronze row (deterministic). Groups whose count column is
    entirely NULL (fully TFS-suppressed districts) are preserved as
    (NULL, NULL) rows — real suppressed rollup observations.
    """
    num_col, avg_col = LONG_LEVEL_METRICS[level]
    school_num, school_avg = LONG_LEVEL_METRICS["school"]
    group_keys = (
        ["year", "district_code", "demographic", "test_component"]
        if level == "district"
        else ["year", "demographic", "test_component"]
    )
    nulled_geo = (
        ["school_code"] if level == "district" else ["district_code", "school_code"]
    )

    votes = (
        base.with_row_index("_idx")
        .with_columns(
            _to_float_expr(num_col).alias("_num"),
            _to_float_expr(avg_col).alias("_avg"),
            (
                _to_float_expr(school_num).is_not_null()
                | _to_float_expr(school_avg).is_not_null()
            ).alias("_school_supported"),
        )
        .filter(pl.col("_num").is_not_null() | pl.col("_avg").is_not_null())
    )
    counted = votes.group_by([*group_keys, "_num", "_avg"]).agg(
        pl.len().alias("_n"),
        pl.col("_school_supported").any().alias("_sup"),
        pl.col("_idx").min().alias("_first"),
    )

    divergent = counted.group_by(group_keys).len().filter(pl.col("len") > 1)
    if divergent.height:
        sample = (
            counted.join(divergent.select(group_keys), on=group_keys)
            .sort([*group_keys, "_n"])
            .head(12)
            .to_dicts()
        )
        logger.warning(
            "Year %d: %d %s group(s) carry divergent aggregate (count, score) "
            "pairs; resolving by school-supported-then-modal vote. Sample: %s",
            year,
            divergent.height,
            level,
            sample,
        )

    winners = (
        counted.sort(
            [*group_keys, "_sup", "_n", "_first"],
            descending=[False] * len(group_keys) + [True, True, False],
        )
        .group_by(group_keys, maintain_order=True)
        .agg(
            pl.col("_num").first().alias("num_tested"),
            pl.col("_avg").first().alias("avg_score"),
        )
    )

    # Re-attach groups whose every row had NULL metrics (fully suppressed).
    all_groups = base.select(group_keys).unique()
    missing = all_groups.join(winners.select(group_keys), on=group_keys, how="anti")
    if missing.height:
        missing = missing.with_columns(
            pl.lit(None).cast(pl.Float64).alias("num_tested"),
            pl.lit(None).cast(pl.Float64).alias("avg_score"),
        )
        winners = pl.concat([winners, missing], how="vertical_relaxed")

    return winners.with_columns(
        pl.lit(level).alias("detail_level"),
        *[pl.lit(None).cast(pl.Utf8).alias(c) for c in nulled_geo],
    ).select(STANDARD_COLUMNS)


def _transform_long(
    df: pl.DataFrame,
    year: int,
    district_col: str,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Transform an Era 4/5/6 long file into gold rows at three detail levels.

    Every bronze row is one (school x test_component) observation carrying
    district/state context columns. School rows map 1:1 (TFS-suppressed
    metrics stay as NULL-metric rows); district and state rows are
    materialized from the official context columns via the modal-pair vote.
    National columns are out of scope and dropped.
    """
    metric_cols = [c for pair in LONG_LEVEL_METRICS.values() for c in pair]
    _require_columns(
        df,
        [district_col, "INSTN_NUMBER", "SUBGRP_DESC", "TEST_CMPNT_TYP_CD"]
        + metric_cols,
        f"era_4/5/6 {year}",
    )
    _validate_long_constants(df, year)

    base = df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        # zfill(3) pads 3-digit county codes and passes 7-digit charter
        # codes through unchanged (never truncate).
        pl.col(district_col)
        .cast(pl.Utf8)
        .str.strip_chars()
        .str.zfill(3)
        .alias("district_code"),
        pl.col("INSTN_NUMBER")
        .cast(pl.Utf8)
        .str.strip_chars()
        .str.zfill(4)
        .alias("school_code"),
        pl.col("TEST_CMPNT_TYP_CD")
        .replace_strict(TEST_COMPONENT_MAP, default=None)
        .alias("test_component"),
        normalize_demographic_column("SUBGRP_DESC").alias("demographic"),
    )
    manifest.record_categorical(
        column="test_component",
        map_dict=TEST_COMPONENT_MAP,
        bronze_series=base["TEST_CMPNT_TYP_CD"],
        gold_series=base["test_component"],
    )
    # Effective alias slice for the constant subgroup label (§4.3a).
    manifest.record_categorical(
        column="demographic",
        map_dict={"All Students": DEMOGRAPHIC_ALIASES["ALL STUDENTS"]},
        bronze_series=base["SUBGRP_DESC"],
        gold_series=base["demographic"],
    )

    school_num, school_avg = LONG_LEVEL_METRICS["school"]
    schools = base.select(
        "year",
        "district_code",
        "school_code",
        "demographic",
        "test_component",
        _to_float_expr(school_num).alias("num_tested"),
        _to_float_expr(school_avg).alias("avg_score"),
    ).with_columns(pl.lit("school").alias("detail_level"))

    districts = _modal_aggregate_rows(base, "district", year)
    states = _modal_aggregate_rows(base, "state", year)
    logger.info(
        "Year %d: materialized %d school, %d district, %d state rows",
        year,
        schools.height,
        districts.height,
        states.height,
    )
    return pl.concat([schools.select(STANDARD_COLUMNS), districts, states])


# =============================================================================
# File routing
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame:
    """Read one bronze file, detect its era, and route to the era transform.

    Year resolution: Era 1-3 files carry no year column (filename year is
    the reporting year); Era 4-6 derive the year from ``LONG_SCHOOL_YEAR``
    and cross-check the filename so a misnamed file cannot mislabel a year.
    """
    filename_year = extract_year_from_filename(path.name)
    if filename_year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")

    if path.name == "sat_scores_recent_2004.csv":
        # Pinned reader: the generic CSV chain silently loses 26 rows of
        # this file (see _read_2004_csv). The 2-row loss recorded here is
        # the two truncated re-appended fragments, legitimate by note.
        df, raw_rows, parsed_rows = _read_2004_csv(path)
        manifest.record_read_loss(
            filename_year,
            path.name,
            raw_rows,
            parsed_rows,
            note=(
                "2 truncated trailing fragments (48 and 11 fields vs 72) are "
                "re-appends of rows present intact earlier in the file "
                "(758:ALL Wilkinson County, 761:182 Mays High School); "
                "parsed with stdlib csv because the generic reader chain "
                "drops 26 rows on this file"
            ),
        )
    else:
        # All-string read (§4.3b): sentinel strings and zero-padded codes
        # mis-type under schema inference.
        df, loss = read_bronze_file(path, infer_schema_length=0, return_loss=True)
        manifest.record_read_loss(
            filename_year, path.name, loss["raw_rows"], loss["parsed_rows"]
        )

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{path.name}: no era signature matched columns {df.columns}")

    if era in ("era_4", "era_5", "era_6"):
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

    if era in ("era_1", "era_2"):
        return _transform_era12(df, year, era, manifest)
    if era == "era_3":
        return _transform_era3(df, year, manifest)
    if era == "era_6":
        return _transform_long(df, year, "SCHOOL_DSTRCT_CD", manifest)
    return _transform_long(df, year, "SCHOOL_DISTRCT_CD", manifest)


# =============================================================================
# §4b known-bad mask
# =============================================================================


def _null_invalid_sat_scores(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """NULL ``avg_score`` values outside their component's SAT scale (§4b).

    An entity's AVERAGE cannot fall outside the per-student score range of
    its component (see SAT_SCORE_RANGES). The known defects are 16 GOSA
    publication errors: seven above their ceilings (2009 Carroll County
    district V+M+W=2751; 2010 Rockdale County High V+M+W=3114, V+M=2133,
    Verbal=1039, Math=1094, Writing=981; 2010 Elberta Open Campus
    Verbal=819) and nine 2011-2015 ``writing`` averages below the 200
    section floor (as low as 92). Each value is NULLed — the same
    convention as suppression — while ``num_tested`` and the row are
    preserved. reading_test_score / writlang_test_score have no enforceable
    bound (GOSA rescaled axis) and are excluded. Extreme-but-conceivable
    values (Elberta's 2010 V+M+W=2287 <= 2400) are preserved + documented.
    """
    invalid = pl.lit(False)
    for component, (lo, hi) in SAT_SCORE_RANGES.items():
        invalid = invalid | (
            (pl.col("test_component") == component)
            & pl.col("avg_score").is_not_null()
            & ((pl.col("avg_score") < lo) | (pl.col("avg_score") > hi))
        )

    bad = df.filter(invalid)
    if bad.height:
        by_component = dict(
            bad.group_by("test_component").len().sort("test_component").iter_rows()
        )
        manifest.record_masked(
            "avg_score",
            bad.height,
            "outside_sat_component_scale",
            years=sorted(bad["year"].unique().to_list()),
        )
        logger.warning(
            "§4b: NULLing %d impossible avg_score value(s) outside their "
            "component's SAT scale. By component: %s. Rows: %s",
            bad.height,
            by_component,
            bad.select(
                "year", "district_code", "school_code", "test_component", "avg_score"
            )
            .sort("year")
            .head(20)
            .to_dicts(),
        )
    return df.with_columns(
        pl.when(invalid).then(None).otherwise(pl.col("avg_score")).alias("avg_score")
    )


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for sat_scores_recent."""
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
    # Tie-break: every bronze file is a distinct year, eras don't overlap,
    # and the two 2016 files use disjoint component vocabularies, so only
    # within-file repeats can dedup (known case: 2004's re-appended 25-row
    # trailing block, districts 758/759/761 — 72 byte-identical melted
    # twins). Prefer the row with a reported (non-null, larger) num_tested
    # over a suppressed placeholder.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=[
            "year",
            "district_code",
            "school_code",
            "demographic",
            "test_component",
        ],
        district_keys=["year", "district_code", "demographic", "test_component"],
        state_keys=["year", "demographic", "test_component"],
        sort_col="num_tested",
    )

    # 4. Geography nulling (shared domain rules), then the §4b mask.
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )
    combined = _null_invalid_sat_scores(combined, manifest)

    # Pre-export sanity: NULL-rate spikes are warnings with a bronze-real
    # cause — essay components are sparse, and TFS suppression rises sharply
    # in 2020-2024 (shrinking SAT participation pushes more schools under
    # GOSA's n<10 threshold: 656 suppressed school cells in 2023 alone).
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(
        combined,
        required_non_null=["year", "detail_level", "demographic", "test_component"],
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


def _component_scale_violation_sql() -> str:
    """Build the per-component scale predicate from SAT_SCORE_RANGES."""
    return " OR ".join(
        f"(test_component = '{component}' "
        f"AND (avg_score < {lo:g} OR avg_score > {hi:g}))"
        for component, (lo, hi) in SAT_SCORE_RANGES.items()
    )


# DuckDB join predicate aligning two copies of the union view on the same
# entity (NULL-safe so state/district rows join their own level).
def _emit_contract_and_readme(year_range: tuple[int, int]) -> None:
    """Emit the ODCS contract and gold README via ``write_data_dictionary``.

    The column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level`` — the contract's properties (and the validator's
    schema check) follow it.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        # 1.1.0: num_tested short_description added (fractional combined-score
        # counts are source-published averages, not headcounts).
        version="1.1.0",
        description=(
            "Average SAT scores (most recent administration per student) and "
            "number of students tested for Georgia public high schools, with "
            "official district and state rollups, by SAT test component. "
            "2004-2010 additionally break out demographic subgroups; 2011 "
            "onward is all-students only. Spans the 2016 SAT redesign: "
            "pre-redesign components (verbal_math, reading, mathematics, "
            "writing, combined, verbal_math_writing) and redesigned "
            "components (combined_test_score, math_section_score, "
            "evidence_based_reading_and_writing, reading_test_score, "
            "writlang_test_score, essay components) are distinct categorical "
            "values because they measure on different scales. Best-attempt "
            "scores live in the sibling topic sat_scores_highest."
        ),
        title="SAT Scores (Most Recent Administration)",
        summary=(
            "Average SAT scores by section for Georgia public high schools, "
            "using each student's most recent test date, 2004-2024."
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
                    "zero-padded county/city codes or 7-digit charter codes. "
                    "NULL on state-level rows."
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
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "all",
                "validValues": [
                    "all",
                    "asian_pacific_islander",
                    "black",
                    "female",
                    "hispanic",
                    "male",
                    "native_american",
                    "other",
                    "race_unknown",
                    "white",
                ],
                "short_description": (
                    "Student race or gender subgroup; breakdowns exist only "
                    "for 2004-2010, every later row is 'all'."
                ),
                "description": (
                    "Demographic subgroup (FK to the global demographics "
                    "dimension). Subgroup breakdowns exist only for 2004-2010; "
                    "from 2011 onward the source publishes all-students rows "
                    "only, so every 2011+ row is 'all'. The "
                    "asian_pacific_islander key reflects the source's pre-1997 "
                    "OMB combined Asian + Pacific Islander bucket (the bronze "
                    "label is bare 'Asian', but no era publishes a separate "
                    "Pacific Islander row and sibling GOSA reports use the "
                    "explicit combined label) — it is NOT an Asian-only count, "
                    "per data-cleaning-standards section 5b. race_unknown "
                    "(no-response) carries data only in 2004; 2005-2007 publish "
                    "the slot empty and 2008+ drop it."
                ),
            },
            {
                "name": "test_component",
                "type": "string",
                "nullable": False,
                "example": "combined_test_score",
                "validValues": sorted(
                    set(TEST_COMPONENT_MAP.values())
                    | set(ERA3_SUFFIXED_COMPONENTS.values())
                    | {"verbal_math", "verbal_math_writing"}
                ),
                "short_description": (
                    "Which SAT section or composite the score is for; scales "
                    "differ, so never compare across components."
                ),
                "description": (
                    "SAT test component. Pre-redesign (scales in "
                    "parentheses): reading (200-800; published as 'Verbal' "
                    "until 2011, the same Critical Reading section, "
                    "2004-2016), mathematics (200-800, 2004-2016), writing "
                    "(200-800, 2008-2016), verbal_math (V+M composite, "
                    "400-1600, 2004-2010), verbal_math_writing (V+M+W "
                    "composite, 600-2400, 2008-2010, all-students only), "
                    "combined (V+M+W composite, 600-2400, 2011-2016). "
                    "Redesigned SAT (2016 onward): combined_test_score "
                    "(Math+EBRW, 400-1600), math_section_score (200-800), "
                    "evidence_based_reading_and_writing (200-800, 2016-2019 "
                    "only), reading_test_score and writlang_test_score "
                    "(GOSA-rescaled test scores, observed 180-338), "
                    "essay_reading_score / essay_analysis_score / "
                    "essay_writing_score (2-8) and essay_total (6-24, a "
                    "GOSA-derived sum of the three essay dimensions, not an "
                    "official College Board score). Old and redesigned "
                    "components are distinct values because they measure on "
                    "different scales."
                ),
            },
            {
                "name": "num_tested",
                "type": "float64",
                "metric_component": "denominator",
                "unit": "count",
                "short_description": (
                    "Number of students tested; on the combined test score "
                    "the source reports the average of the three section "
                    "counts, so it can be fractional, not a headcount."
                ),
                "example": 156.0,
                "null_meaning": (
                    "Suppressed by GOSA (too few students; TFS marker in "
                    "2011-2024 sources)."
                ),
                "description": (
                    "Number of students tested. Float64, NOT Int64 — a "
                    "documented exception to the integer-count convention "
                    "(data-cleaning-standards section 16): 2016-2024 sources "
                    "publish fractional counts on the combined_test_score "
                    "component because GOSA reports it as the equal-weight "
                    "mean of the three SAT section test-taker counts (Math, "
                    "Reading, Writing & Language), not a headcount (e.g. "
                    "(47+37+37)/3 -> 40.3 — exact thirds where published "
                    "full-precision, rounded to one decimal from ~2020), and "
                    "2023-24 district counts are fractional throughout (e.g. "
                    "4159.3). Rounding to an integer would silently lose "
                    "precision, so values are carried as published. 2004-2010 "
                    "sources publish one "
                    "count per (entity, demographic), repeated on each of "
                    "that demographic's component rows; 2011-2024 publish "
                    "true per-component counts. Either way, summing "
                    "num_tested across test_component double-counts students "
                    "— filter to one component for headcounts. A 0 means the "
                    "source reported zero test-takers for that demographic "
                    "(2004-2010 only)."
                ),
            },
            {
                "name": "avg_score",
                "type": "float64",
                "key_metric": True,
                "unit": "score",
                "example": 982.3,
                "null_meaning": (
                    "Suppressed by GOSA (too few test-takers), a zero-test-"
                    "taker demographic cell (2004-2010), or one of 16 "
                    "impossible source values NULLed by the transform."
                ),
                "short_description": (
                    "Average most-recent-attempt SAT score; on the scale of "
                    "the section named by test_component."
                ),
                "description": (
                    "Average SAT score. The scale varies by test_component "
                    "(sections 200-800; verbal_math / combined_test_score "
                    "400-1600; combined / verbal_math_writing 600-2400; "
                    "essay dimensions 2-8; essay_total 6-24), so this column "
                    "carries no single value_min/value_max — the "
                    "avg_score_within_component_scale quality check enforces "
                    "the per-component ranges instead. reading_test_score "
                    "and writlang_test_score are excluded from that check: "
                    "GOSA publishes them on a rescaled axis (observed "
                    "180-338, consistent with 10x the College Board 10-40 "
                    "test-score scale) with no clean published ceiling. "
                    "Known source defects NULLed by the transform per "
                    "data-cleaning-standards section 4b (rows and num_tested "
                    "preserved): seven values above their component ceilings "
                    "— the 2009 Carroll County district verbal_math_writing "
                    "of 2751 (> 2400), and in 2010 Rockdale County High "
                    "School (722:3052) verbal_math_writing=3114, "
                    "verbal_math=2133, reading=1039, mathematics=1094, "
                    "writing=981 plus Elberta Open Campus (676:3050) "
                    "reading=819 (> 800) — and nine 2011-2015 writing "
                    "averages below the 200 section floor (as low as 92, all "
                    "small schools/districts). This revises the "
                    "preserve-bronze default for those values; the "
                    "per-component range check remains enforceable because "
                    "of it. Extreme-but-conceivable values are preserved: "
                    "Elberta Open Campus's 2010 verbal_math_writing of 2287 "
                    "is within the 600-2400 scale and is carried as "
                    "published (suspect — the same row's reading section is "
                    "impossible — but not provably wrong itself)."
                ),
            },
        ],
        source="GOSA",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        limitations=(
            "Suppressed cells are NULL (not zero). State rows have NULL "
            "district_code and school_code; district rows have NULL "
            "school_code. Scores are NOT comparable across the 2016 SAT "
            "redesign boundary — use the distinct pre-redesign vs redesigned "
            "test_component values, never mix them in one time series. "
            "Demographic subgroups exist only for 2004-2010. num_tested can "
            "be fractional (see column description). reading_test_score / "
            "writlang_test_score are on a GOSA-rescaled axis, not the "
            "College Board 10-40 scale and not the 200-800 section scale."
        ),
        notes=[
            (
                "The 2004-2010 bronze files are byte-identical to "
                "sat_scores_highest's (one shared GOSA publication carrying "
                "both measure families). This topic extracts only the "
                "Recent* (most-recent-attempt) columns; the High* "
                "(best-attempt) columns belong to the sibling topic."
            ),
            (
                "District and state rows are the official GOSA aggregates "
                "(2004-2010: published ALL:ALL / {district}:ALL rollup rows; "
                "2011-2024: the DSTRCT_*/STATE_* context columns), never "
                "re-aggregated from school rows — school-level suppression "
                "(n<10) would undercount official totals."
            ),
            (
                "2011-2024 district/state values are taken as the modal "
                "(count, score) PAIR per group with school-supported rows "
                "preferred. Needed for 2024 only: three bronze rows (Bishop "
                "Hall Charter 736:0100, McDonough Middle 675:4050, Pleasant "
                "Valley Innovative 705:0108 — all with suppressed school "
                "metrics) carry alternate-scale aggregates on "
                "combined_test_score (e.g. state pair (37140, 505.4) vs the "
                "official (32976, 1043.6) carried by 435 rows); the vote "
                "keeps the official pairs."
            ),
            (
                "National benchmark columns (2011-2024 NATIONAL_*) are out "
                "of scope and dropped — education detail levels are "
                "school/district/state."
            ),
            (
                "2004-2010 sources encode 'no test takers in this "
                "demographic' as paired (score=0, count=0) cells (2004 uses "
                "blanks). A zero score is impossible on any SAT scale, so "
                "avg_score is NULLed wherever num_tested = 0 while the real "
                "zero count is kept. The one score-with-zero-count case "
                "(2010 charter district 7830103 'CCAT', verbal_math_writing "
                "= 1450 with count 0) is nulled by the same rule. Wide "
                "cells where BOTH metrics are blank are dropped as "
                "non-observations."
            ),
            (
                "The 2004 file is parsed with the stdlib csv module: the "
                "generic reader chain silently loses 26 rows on it (a "
                "quoted-comma school name plus two truncated trailing "
                "fragments). The two fragments (48 and 11 fields vs 72) are "
                "re-appends of rows present intact earlier in the file and "
                "are dropped; the file also re-appends a 25-row trailing "
                "block of intact duplicates (districts 758/759/761 — e.g. "
                "758:ALL Wilkinson County, populated 759:176 Worth County "
                "High School rows), all byte-identical twins; dedup removes "
                "the 72 melted duplicate rows."
            ),
            (
                "Both 2016 files are kept: 2016_old_format carries the "
                "pre-redesign components for the 2015-16 cohort and "
                "2016_new_format the redesigned components — disjoint "
                "vocabularies, no key collisions. 2016 is therefore the one "
                "year with both component families."
            ),
            (
                "Era 3 (2008-2010) files carry a legend row (NULL entity id, "
                "explanatory text in the Recent Total cells) that is dropped, "
                "and a standalone non-suffixed 'Recent Total' column — the "
                "V+M+W composite (600-2400, all-students only) — distinct "
                "from the suffixed V+M composite, emitted as "
                "verbal_math_writing."
            ),
            (
                "Evidence Based Reading and Writing is published 2016-2019 "
                "only (dropped from the source from 2020 onward); essay "
                "components appear from 2016. Writing (pre-redesign section) "
                "exists 2008-2016."
            ),
            (
                "16 impossible avg_score values are NULLed per "
                "data-cleaning-standards section 4b (see the avg_score "
                "column description for the full list); "
                "extreme-but-conceivable values (Elberta Open Campus 2010 "
                "verbal_math_writing = 2287) are preserved and documented."
            ),
            (
                "NULL rates for avg_score are structurally higher in "
                "2020-2024: SAT participation fell (COVID + test-optional "
                "admissions), pushing more schools under GOSA's n<10 TFS "
                "suppression threshold (656 suppressed school cells in 2023; "
                "544 in 2020), and essay components are sparsely reported."
            ),
        ],
        quality_checks=[
            {
                "name": "avg_score_within_component_scale",
                "description": (
                    "Each test_component's avg_score stays within its "
                    "physical SAT scale (sections 200-800; verbal_math / "
                    "combined_test_score 400-1600; combined / "
                    "verbal_math_writing 600-2400; essay dimensions 2-8; "
                    "essay_total 6-24). The GOSA-rescaled reading_test_score "
                    "/ writlang_test_score components have no published "
                    "ceiling and are intentionally excluded."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE avg_score IS NOT NULL "
                    f"AND ({_component_scale_violation_sql()})"
                ),
                "mustBe": 0,
            },
            {
                "name": "avg_score_requires_positive_num_tested",
                "description": (
                    "A published average implies at least one reported "
                    "test-taker: avg_score must not be non-NULL while "
                    "num_tested is NULL or < 1. Holds in every era (counts "
                    "are published even for suppressed-score rows; verified "
                    "across all 22 bronze files)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE avg_score IS NOT NULL "
                    "AND (num_tested IS NULL OR num_tested < 1)"
                ),
                "mustBe": 0,
            },
            {
                "name": "demographic_breakdowns_only_2004_2010",
                "description": (
                    "Demographic subgroup rows exist only in the 2004-2010 "
                    "wide-format sources; every 2011+ bronze row is "
                    "'All Students'."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE demographic != 'all' AND year > 2010"
                ),
                "mustBe": 0,
            },
            {
                "name": "pre_redesign_components_within_year_windows",
                "description": (
                    "Pre-redesign components only appear in their source "
                    "year windows: verbal_math 2004-2010, "
                    "verbal_math_writing 2008-2010, writing 2008-2016, "
                    "combined 2011-2016, reading/mathematics 2004-2016."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(test_component = 'verbal_math' "
                    "AND (year < 2004 OR year > 2010)) "
                    "OR (test_component = 'verbal_math_writing' "
                    "AND (year < 2008 OR year > 2010)) "
                    "OR (test_component = 'writing' "
                    "AND (year < 2008 OR year > 2016)) "
                    "OR (test_component = 'combined' "
                    "AND (year < 2011 OR year > 2016)) "
                    "OR (test_component IN ('reading', 'mathematics') "
                    "AND (year < 2004 OR year > 2016))"
                ),
                "mustBe": 0,
            },
            {
                "name": "redesigned_components_within_year_windows",
                "description": (
                    "Redesigned-SAT components first appear in 2016; "
                    "evidence_based_reading_and_writing exists 2016-2019 "
                    "only (dropped from the source from 2020 onward)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(test_component IN ('combined_test_score', "
                    "'math_section_score', 'reading_test_score', "
                    "'writlang_test_score', 'essay_reading_score', "
                    "'essay_analysis_score', 'essay_writing_score', "
                    "'essay_total') AND year < 2016) "
                    "OR (test_component = 'evidence_based_reading_and_writing' "
                    "AND (year < 2016 OR year > 2019))"
                ),
                "mustBe": 0,
            },
            {
                "name": "verbal_math_reconciles_with_sections",
                "description": (
                    "The 2004-2010 verbal_math composite equals "
                    "reading + mathematics within rounding tolerance "
                    "(means are linear; each published average is rounded "
                    "independently, so the composite can deviate by up to "
                    "~1 point per section; 23,442 complete groups, max "
                    "observed deviation within 1.5)."
                ),
                "dimension": "consistency",
                # Conditional-aggregation pivot (NOT a self-join — see the
                # essay_total check comment): GROUP BY treats NULL geography
                # keys as equal, keeping state/district/school levels apart.
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, school_code, demographic, "
                    "MAX(CASE WHEN test_component = 'verbal_math' "
                    "THEN avg_score END) AS composite, "
                    "MAX(CASE WHEN test_component = 'reading' "
                    "THEN avg_score END) AS reading, "
                    "MAX(CASE WHEN test_component = 'mathematics' "
                    "THEN avg_score END) AS mathematics "
                    "FROM {object} WHERE test_component IN ('verbal_math', "
                    "'reading', 'mathematics') "
                    "AND year BETWEEN 2004 AND 2010 "
                    "GROUP BY year, district_code, school_code, demographic"
                    ") WHERE composite IS NOT NULL AND reading IS NOT NULL "
                    "AND mathematics IS NOT NULL "
                    "AND ABS(composite - (reading + mathematics)) > 1.5"
                ),
                "mustBe": 0,
            },
            {
                "name": "verbal_math_writing_reconciles_with_sections",
                "description": (
                    "The 2008-2010 standalone verbal_math_writing composite "
                    "equals reading + mathematics + writing within rounding "
                    "tolerance (three independently rounded section means; "
                    "1,632 complete groups, max observed deviation within "
                    "2.0)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, school_code, demographic, "
                    "MAX(CASE WHEN test_component = 'verbal_math_writing' "
                    "THEN avg_score END) AS composite, "
                    "MAX(CASE WHEN test_component = 'reading' "
                    "THEN avg_score END) AS reading, "
                    "MAX(CASE WHEN test_component = 'mathematics' "
                    "THEN avg_score END) AS mathematics, "
                    "MAX(CASE WHEN test_component = 'writing' "
                    "THEN avg_score END) AS writing "
                    "FROM {object} WHERE test_component IN "
                    "('verbal_math_writing', 'reading', 'mathematics', "
                    "'writing') AND year BETWEEN 2008 AND 2010 "
                    "GROUP BY year, district_code, school_code, demographic"
                    ") WHERE composite IS NOT NULL AND reading IS NOT NULL "
                    "AND mathematics IS NOT NULL AND writing IS NOT NULL "
                    "AND ABS(composite - (reading + mathematics + writing)) "
                    "> 2.0"
                ),
                "mustBe": 0,
            },
            {
                "name": "combined_reconciles_with_sections",
                "description": (
                    "The 2011-2016 combined composite (V+M+W, 600-2400) "
                    "equals reading + mathematics + writing within rounding "
                    "tolerance (three independently rounded section means; "
                    "3,474 complete groups, max observed deviation within "
                    "2.0)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, school_code, demographic, "
                    "MAX(CASE WHEN test_component = 'combined' "
                    "THEN avg_score END) AS composite, "
                    "MAX(CASE WHEN test_component = 'reading' "
                    "THEN avg_score END) AS reading, "
                    "MAX(CASE WHEN test_component = 'mathematics' "
                    "THEN avg_score END) AS mathematics, "
                    "MAX(CASE WHEN test_component = 'writing' "
                    "THEN avg_score END) AS writing "
                    "FROM {object} WHERE test_component IN ('combined', "
                    "'reading', 'mathematics', 'writing') "
                    "AND year BETWEEN 2011 AND 2016 "
                    "GROUP BY year, district_code, school_code, demographic"
                    ") WHERE composite IS NOT NULL AND reading IS NOT NULL "
                    "AND mathematics IS NOT NULL AND writing IS NOT NULL "
                    "AND ABS(composite - (reading + mathematics + writing)) "
                    "> 2.0"
                ),
                "mustBe": 0,
            },
            {
                "name": "combined_test_score_reconciles_with_sections",
                "description": (
                    "The 2016-2019 redesigned-SAT combined_test_score equals "
                    "math_section_score + evidence_based_reading_and_writing "
                    "within rounding tolerance (EBRW is published 2016-2019 "
                    "only, so the window ends there; 2,243 complete groups, "
                    "max observed deviation within 1.5)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, school_code, demographic, "
                    "MAX(CASE WHEN test_component = 'combined_test_score' "
                    "THEN avg_score END) AS composite, "
                    "MAX(CASE WHEN test_component = 'math_section_score' "
                    "THEN avg_score END) AS math_section, "
                    "MAX(CASE WHEN test_component = "
                    "'evidence_based_reading_and_writing' "
                    "THEN avg_score END) AS ebrw "
                    "FROM {object} WHERE test_component IN "
                    "('combined_test_score', 'math_section_score', "
                    "'evidence_based_reading_and_writing') "
                    "AND year BETWEEN 2016 AND 2019 "
                    "GROUP BY year, district_code, school_code, demographic"
                    ") WHERE composite IS NOT NULL AND math_section IS NOT "
                    "NULL AND ebrw IS NOT NULL "
                    "AND ABS(composite - (math_section + ebrw)) > 1.5"
                ),
                "mustBe": 0,
            },
            {
                "name": "essay_total_reconciles_with_dimensions",
                "description": (
                    "The published essay_total equals the sum of the three "
                    "essay dimension averages within rounding tolerance "
                    "(means are linear; each published average is rounded, "
                    "observed max deviation 1.0)."
                ),
                "dimension": "consistency",
                # Conditional-aggregation pivot, not a self-join: GROUP BY
                # treats NULL geography keys as equal (the IS NOT DISTINCT
                # FROM semantics), and a join formulation explodes — DuckDB
                # hoists the INDF conditions to the top join, leaving inner
                # joins keyed on (year, demographic) alone, which is
                # degenerate here (essay rows are all demographic = 'all').
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, school_code, demographic, "
                    "MAX(CASE WHEN test_component = 'essay_total' "
                    "THEN avg_score END) AS total, "
                    "MAX(CASE WHEN test_component = 'essay_reading_score' "
                    "THEN avg_score END) AS reading, "
                    "MAX(CASE WHEN test_component = 'essay_analysis_score' "
                    "THEN avg_score END) AS analysis, "
                    "MAX(CASE WHEN test_component = 'essay_writing_score' "
                    "THEN avg_score END) AS writing "
                    "FROM {object} WHERE test_component IN ('essay_total', "
                    "'essay_reading_score', 'essay_analysis_score', "
                    "'essay_writing_score') "
                    "GROUP BY year, district_code, school_code, demographic"
                    ") WHERE total IS NOT NULL AND reading IS NOT NULL "
                    "AND analysis IS NOT NULL AND writing IS NOT NULL "
                    "AND ABS(total - (reading + analysis + writing)) > 1.5"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_all_students_rows_never_suppressed",
                "description": (
                    "GOSA publishes unsuppressed statewide all-students "
                    "aggregates in every era: state-level rows "
                    "(district_code and school_code both NULL) with "
                    "demographic = 'all' must carry non-NULL num_tested and "
                    "avg_score."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE district_code IS NULL "
                    "AND school_code IS NULL AND demographic = 'all' "
                    "AND (num_tested IS NULL OR avg_score IS NULL)"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
