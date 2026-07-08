"""Transform bronze sat_scores_highest files into gold fact tables.

Source: Governor's Office of Student Achievement (GOSA) — SAT Scores
(highest score across administrations), 2004-2024 (22 bronze files; 2016 is
published in two complementary files spanning the old-SAT / redesigned-SAT
transition). For Georgia public high schools, plus official district and
state rollups, reports the average SAT score per test section
(``test_component``) using each student's HIGHEST section score when they
tested multiple times, and the number of students tested. The most-recent
variant lives in the sibling ``sat_scores_recent`` topic; the two topics
share the same canonical column names and ``test_component`` vocabulary.

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Five bronze schema eras, one long gold fact.**
    * Era 1 (2004-2006, 72 wide cols; verbose demographic headers): rows are
      compound ``SysSchoolID`` entities (``ALL:ALL`` state / ``{d}:ALL``
      district / ``{d}:{s}`` school). Only the ``High *`` score columns and
      ``Number Taken *`` count columns feed this topic — the ``Recent *``
      columns are the sibling topic's measure and are ignored here.
    * Era 2 (2007, 72 wide cols; single-letter demographic suffixes
      ``0/A/B/F/H/M/N/O/R/W``): same compound-ID layout. All demographic-split
      ``High *`` columns are the literal string "NULL" in bronze (no data),
      so 2007 subgroup rows are count-only.
    * Era 3 (2008-2010, 52 wide cols; adds ``High Writing0``, drops the ``R``
      suffix, keeps ``High *`` for All Students only): row index 1 is a
      sub-header annotation row ("(Verbal+Math+Writing)" / "Verbal and
      Math"), dropped and recorded via ``record_filtered``. Subgroup rows
      are count-only (per-demographic ``Number Taken{X}`` still published).
    * Era 4 (2011-2022, tidy 14 cols) / Era 5 (2023-2024, tidy 17 cols;
      renames ``SCHOOL_DISTRCT_CD`` -> ``SCHOOL_DSTRCT_CD``, adds
      ``#ASSMT_CD``/``HIGHEST_RECENT_IND``/``NATIONAL_AVG_SCORE_VAL``):
      one bronze row per (school x test component) carrying district/state
      (and Era 5 national) context columns. School rows map 1:1; district
      and state rows are materialized from the context columns (see the
      modal-pair note below), never re-aggregated from suppressed school
      rows. National data is out of scope (education detail levels are
      school/district/state) and never emitted.
- **test_component vocabulary is era-aware and shared with the sibling.**
  Old-SAT sections fold across file-format eras: 2004-2010 ``High Verbal`` /
  ``High Math`` and 2011-2016 ``Reading`` / ``Mathematics`` are the same
  200-800 sections -> ``reading`` / ``mathematics``. The 2004-2010 ``High
  Total`` is the Verbal+Math total (400-1600) -> ``verbal_math``: empirical
  proof that Era 3's ``High Total0`` is V+M, not V+M+W — bronze satisfies
  ``High Total0 == High Verbal0 + High Math0`` exactly (max abs diff 0.0 in
  2007-2010, <=1 in 2005), and the state-level High Total0 (~987-991) tracks
  Recent Total0 (V+M ~971-976), not Recent Total (V+M+W ~1442). The
  2011-2016 ``Combined`` is the three-section V+M+W total (600-2400;
  state value 1338 == 486+490+361 in 2011) -> ``combined`` and stays
  distinct from ``verbal_math`` and from the redesigned-SAT
  ``combined_test_score`` (400-1600). Redesigned components (2016+) keep
  their own names; the two 2016 files have disjoint vocabularies, so the
  transition year cannot collide on the natural key.
- **Demographics exist in gold because Eras 1-3 publish them.** Era 1
  (2004-2006) carries real demographic-split High scores + counts; Era 2
  (2007) and Era 3 (2008-2010) carry per-demographic counts only (score
  columns "NULL"-string or absent) -> count-only subgroup rows
  (``num_tested`` populated, ``avg_score`` NULL). Eras 4-5 publish only
  "All Students" -> ``demographic='all'``. Wide cells with neither a count
  nor a score (e.g. the ~1,700 elementary/middle-school rows in the 2004
  file that are blank across every metric) produce no gold row — a blank
  Era 1-3 cell means "not collected", unlike the explicit Era 4-5 TFS
  suppression which IS kept as a NULL-metric row.
- **§5b Asian/Pacific Islander.** Eras 1-3 publish bare "Asian" within a
  6-bucket race scheme (Asian, Black, Hispanic, American Indian, White,
  Other/No-Response) with no separate Pacific Islander row in any era. The
  math test is inapplicable (average metrics), so the structural test
  applies: no era of this source ever publishes a Pacific Islander bucket,
  and sibling GOSA reports (e.g. ACT's "Asian-American/Pacific Islander"
  columns) label the same concept explicitly as the combined bucket. Bronze
  "Asian" is therefore the pre-1997 OMB combined bucket: a topic-local remap
  sends it to ``asian_pacific_islander`` (never a global alias edit). The
  ``O`` suffix -> ``other`` and ``R`` ("No Response") -> ``race_unknown``
  via the shared aliases. Race buckets in gold stay mutually exclusive
  (§5a): no split ``asian``/``pacific_islander`` rows are ever emitted.
- **2004 file corruption (two records, both proven duplicates).** The 2004
  CSV (latin-1) contains two structurally broken records: physical record
  2221 (48 fields) is byte-for-byte the LAST 48 fields of the complete
  Wilkinson County ``758:ALL`` row that follows it (first field mangled to
  ``,386"``), and the final record (11 fields, file truncated mid-value) is
  the FIRST 11 fields of the Mays High School ``761:182`` row already
  complete at record 2009. Both fragments are dropped (logged +
  ``record_filtered``); no information is lost. The stock CSV readers
  mis-parse this file (polars/pandas chokes on the unbalanced quote;
  the truncation fallback silently loses 26 rows), so Era 1 true-CSVs are
  read with Python's ``csv`` module instead — read-loss accounted: 2,247
  physical data lines -> 2,247 parsed records.
- **2024 component mix-up rows (Era 5).** Three 2024 bronze rows — McDonough
  Middle (675:4050), Pleasant Valley Innovative (705:0108), Bishop Hall
  Charter (736:0100), all rows with NULL school metrics — carry the *Math
  Section Score* district/state aggregates on their *Combined Test Score*
  rows (e.g. state pair (37143, 505.4) = the 2024 Math Section state values
  vs (32979, 1043.6) on the other 435 Combined rows; district pairs 470.0 /
  469.4 / 473.6 are Math-scale values). District and state rollups are
  therefore materialized by a **modal (count, score) pair vote** per group:
  rows whose school metrics are NULL are excluded from the vote whenever the
  group also contains rows backed by real school data (evidence
  restriction), the most frequent surviving pair wins, and any residual tie
  raises instead of guessing. The pair is aggregated as a unit so a count
  from one bronze row can never be spliced onto a score from another. The
  three mix-up rows are recorded via ``record_reclassified``
  ("rollup_context_overridden_no_school_evidence", at the district and
  state levels) — they fall out at the evidence restriction, before loser
  counting, so they are recorded separately from out-voted voters; their
  school-level metrics are NULL, so school rows are unaffected.
- **§4b known-bad masks (20 avg_score values NULLed, rows + counts kept).**
  A school *average* cannot fall outside the per-student scale of its
  component, so out-of-scale averages are publication errors, not data:
  (a) 2009: Heritage High (722:176) reading=1022 / mathematics=995 /
  writing=976 / verbal_math=2017, South Atlanta Leadership (761:308)
  writing=811 — 5 values; (b) 2010: Rockdale County High (722:3052)
  reading=1055 / mathematics=1113 / writing=1009 / verbal_math=2168,
  Elberta Open Campus (676:3050) reading=822 — 5 values; (c) 2011-2015
  old-SAT ``writing`` averages below the 200 section floor (as low as 112):
  7 school values + 3 district rollup values = 10. All 20 are NULLed by
  ``_null_invalid_sat_scores`` (recorded per component via
  ``record_masked``), and the contract's per-component range quality check
  keeps the invariant enforceable. Two in-range values are PRESERVED +
  documented instead (extreme-but-conceivable / contaminated-but-in-range):
  2010 Elberta ``verbal_math``=1522 (its reading component 822 is masked,
  so the total cannot be proven wrong by range) and the systematically
  deflated 2011-2016 ``writing`` averages (state 361-406 vs ~470 on the
  recent basis) — see the contract limitations.
- **``num_tested`` is Float64 — documented §16 exception.** Era 4/5 bronze
  publishes fractional counts on the ``Combined Test Score`` component
  (GOSA reports it as the equal-weight mean of the three SAT section
  test-taker counts -- Math, Reading, Writing & Language -- not a headcount,
  e.g. (47+37+37)/3 -> 40.3; 153 fractional values in 2016, 261 in 2024).
  Verified against the source: the means are exact thirds in 2016-2019
  (fractional part .333/.667; value x 3 is integral) and rounded to one
  decimal from ~2020 (.3/.7). Fractional counts occur ONLY on
  ``combined_test_score`` (a quality check pins this). Rounding to an
  integer would lose precision, so the column stays Float64.
- **num_tested semantics differ across eras.** Eras 1-3 publish one count
  per (entity, demographic) administration, repeated on each of that
  demographic's component rows; Eras 4-5 publish true per-component counts.
  Either way, summing ``num_tested`` across ``test_component`` double-counts
  students.
- **Dedup tie-break.** Every bronze file covers a distinct year, and the two
  2016 files have disjoint component vocabularies, so duplicates can only
  arise within a single file. One within-file block exists: the 2004 CSV
  publishes 25 entities twice with byte-identical values (Wilkinson County
  ``758:ALL``; the Worth County ``759:{176,177,193,196,3051,ALL}`` block;
  the Atlanta ``761:*`` block) — 72 gold-grain rows after unpivot/elision,
  proven metric-identical by ``assert_no_natural_key_collisions`` (which
  raises on divergent duplicates) and collapsed to one row each by the
  dedup; the per-year delta is recorded via ``record_filtered``
  ("identical_duplicate_rows"). ``sort_col="num_tested"`` is the documented
  tie-break for any future non-identical repeat (prefer the row with a
  reported, larger count over a suppressed placeholder).
"""

import csv
import io
import logging
from pathlib import Path

import polars as pl

from src.utils.demographics import DEMOGRAPHIC_ALIASES
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

TOPIC = "sat_scores_highest"
BRONZE_DIR = Path("data/bronze/education/gosa/sat_scores_highest")
GOLD_DIR = Path("data/gold/education/sat_scores_highest")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Era 4/5 bronze TEST_CMPNT_TYP_CD row values -> canonical test_component.
# NOTE: "Reading Test  Score - New" and "WritLang Test  Score - New" carry a
# LITERAL DOUBLE SPACE between "Test" and "Score" in bronze (2016_new-2024).
# Vocabulary is shared verbatim with the sibling sat_scores_recent topic.
TEST_COMPONENT_MAP: dict[str, str] = {
    # Old-SAT codes (2011-2015 files + 2016_old_format.csv)
    "Combined": "combined",
    "Mathematics": "mathematics",
    "Reading": "reading",
    "Writing": "writing",
    # Redesigned-SAT codes (2016_new_format.csv-2022 + Era 5 2023-2024)
    "Combined Test Score": "combined_test_score",
    "Math Section Score - New": "math_section_score",
    "Reading Test  Score - New": "reading_test_score",  # double space in bronze
    "WritLang Test  Score - New": "writlang_test_score",  # double space in bronze
    "Evidence Based Reading and Writing - New": "evidence_based_reading_and_writing",
    "Essay Reading Score - New": "essay_reading_score",
    "Essay Analysis Score - New": "essay_analysis_score",
    "Essay Writing Score - New": "essay_writing_score",
    "Essay Total": "essay_total",
}

# Era 1-3 wide score-column PREFIX -> canonical test_component. The bronze
# encodes the categorical in column headers ("High Total All Students",
# "High Verbal0", ...); the unpivot routes through this dict and records the
# literal prefixes in the manifest. "High Writing" exists in Era 3 only.
# `verbal_math` (not `combined`) because High Total is the two-section V+M
# total — see the module docstring for the T == V + M proof.
ERA123_HIGH_PREFIXES: dict[str, str] = {
    "High Total": "verbal_math",
    "High Verbal": "reading",
    "High Math": "mathematics",
    "High Writing": "writing",
}

# Era 1 verbose demographic tokens as they appear inside column names.
# "O" (Other) and "R" (No Response) are suffix-style with NO space even in
# Era 1 ("High TotalO", "Number TakenR"). Order matches bronze layout.
ERA1_DEMO_TOKENS: list[str] = [
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

# Era 2/3 single-letter column suffixes -> raw demographic label fed to the
# alias table. Era 3 dropped "R". "O"/"R" pass through as-is — the shared
# aliases map O -> other, R -> race_unknown (GOSA "No Response").
ERA23_SUFFIX_TO_LABEL: dict[str, str] = {
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

# Valid per-component SAT scales (avg of per-student scores cannot leave the
# per-student scale). Mirrors the sibling sat_scores_recent dict; the
# `verbal_math_writing` entry is the sibling's Era 3 Recent V+M+W component
# and never occurs in this topic (kept for vocabulary parity, harmless as a
# keyed lookup). GOSA reports the redesigned `reading_test_score` /
# `writlang_test_score` on a rescaled axis (observed 191.7-335.4) with no
# clean published ceiling — intentionally unbounded here.
SAT_SCORE_RANGES: dict[str, tuple[float, float]] = {
    # 200-800 single sections
    "reading": (200.0, 800.0),
    "mathematics": (200.0, 800.0),
    "writing": (200.0, 800.0),
    "evidence_based_reading_and_writing": (200.0, 800.0),
    "math_section_score": (200.0, 800.0),
    # 400-1600 two-section composites
    "verbal_math": (400.0, 1600.0),
    "combined_test_score": (400.0, 1600.0),
    # 600-2400 three-section composites
    "verbal_math_writing": (600.0, 2400.0),
    "combined": (600.0, 2400.0),
    # Redesigned-SAT essay dimensions (2 readers x 1-4 = 2-8; total 6-24)
    "essay_reading_score": (2.0, 8.0),
    "essay_analysis_score": (2.0, 8.0),
    "essay_writing_score": (2.0, 8.0),
    "essay_total": (6.0, 24.0),
}

# Era-detection signatures, most specific first (Era 5 superset columns
# first; Eras 1-3 are distinguished by header style, never by year).
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_5": [
        "#ASSMT_CD",
        "HIGHEST_RECENT_IND",
        "SCHOOL_DSTRCT_CD",
        "TEST_CMPNT_TYP_CD",
    ],
    "era_4": ["LONG_SCHOOL_YEAR", "SCHOOL_DISTRCT_CD", "TEST_CMPNT_TYP_CD"],
    # Era 1: verbose demographic headers; Era 2: suffix headers + capital-D
    # SysSchoolID; Era 3: lowercase-d SysSchoolId + the Writing column.
    "era_1": ["SysSchoolID", "High Total All Students"],
    "era_2": ["SysSchoolID", "High Total0"],
    "era_3": ["SysSchoolId", "High Writing0"],
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

# num_tested is Float64 — documented §16 exception (fractional Era 4/5
# Combined Test Score counts; see module docstring). Do NOT round.
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


# =============================================================================
# Shared casting / demographic helpers
# =============================================================================


def _to_float_expr(col: str) -> pl.Expr:
    """Cast a bronze metric column to Float64 through a string round-trip.

    Bronze mixes formats per year (xls strings "952", CSV strings, the 2024
    trailing-dot "1973891.", blank cells). Utf8 -> strip -> strip trailing
    "." -> non-strict Float64 handles all of them; suppression markers and
    other non-numeric residue become NULL.
    """
    return (
        pl.col(col)
        .cast(pl.Utf8)
        .str.strip_chars()
        .str.strip_chars_end(".")
        .cast(pl.Float64, strict=False)
    )


def _raw_demographic_label(bronze_label: str) -> str:
    """Remap bare "Asian" to the combined OMB bucket for this topic (§5b).

    Eras 1-3 publish a 6-bucket race scheme with no Pacific Islander row in
    any era of this source; sibling GOSA reports label the same concept
    "Asian-American/Pacific Islander" explicitly. Bronze "Asian" is the
    pre-1997 combined bucket, so it must canonicalize to
    asian_pacific_islander, never asian. Topic-local by design — the global
    alias table stays untouched.
    """
    if bronze_label == "Asian":
        return "Asian/Pacific Islander"
    return bronze_label


def _demographic_gold_value(raw_label: str) -> str:
    """Resolve a raw bronze demographic label to its canonical gold value."""
    return DEMOGRAPHIC_ALIASES[_raw_demographic_label(raw_label).upper()]


def _record_demographics(
    manifest: TransformManifest, observed_labels: list[str]
) -> None:
    """Record the demographic mapping actually applied (skill §4.3a).

    The map records the EFFECTIVE end-to-end slice for this topic — the raw
    bronze label (pre-remap, e.g. "Asian") to the final gold value (e.g.
    asian_pacific_islander) — so the §5b override is visible in the manifest
    rather than buried in code.
    """
    effective = {lbl: _demographic_gold_value(lbl) for lbl in set(observed_labels)}
    manifest.record_categorical(
        column="demographic",
        map_dict=effective,
        bronze_series=pl.Series(observed_labels, dtype=pl.Utf8),
        gold_series=pl.Series(
            [effective[lbl] for lbl in observed_labels], dtype=pl.Utf8
        ),
    )


def _require_columns(df: pl.DataFrame, required: list[str], label: str) -> None:
    """Raise if an expected bronze column is absent (rename-coverage guard).

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
# Era 1 robust CSV reader (the 2004 file defeats the stock readers)
# =============================================================================


def _read_era1_csv(path: Path) -> tuple[pl.DataFrame, dict, int]:
    """Read an Era 1 true-CSV with Python's csv module (latin-1, all-string).

    The 2004 file contains two corrupted records (a 48-field mid-file
    fragment and an 11-field truncated final record — both proven partial
    duplicates of complete rows, see module docstring) that make polars
    error out and push pandas/the truncation fallback into silently losing
    26 rows. csv.reader parses all 2,247 records; the two wrong-field-count
    fragments are dropped here (count returned for record_filtered).

    Returns:
        (all-string DataFrame, read-loss dict, n_fragments_dropped)
    """
    text = path.read_bytes().decode("latin-1")
    records = list(csv.reader(io.StringIO(text)))
    header, data = records[0], records[1:]
    raw_lines = sum(1 for line in text.splitlines() if line.strip()) - 1

    good = [r for r in data if len(r) == len(header)]
    fragments = [r for r in data if len(r) != len(header)]
    for frag in fragments:
        logger.warning(
            "%s: dropping corrupted %d-field fragment record (partial "
            "duplicate of a complete row): %s",
            path.name,
            len(frag),
            frag[:3],
        )

    df = pl.DataFrame(
        {h: [r[i] for r in good] for i, h in enumerate(header)},
        schema={h: pl.Utf8 for h in header},
    )
    # Blank cells -> NULL so downstream non-null tests mean "has data".
    df = df.with_columns(pl.all().str.strip_chars().replace("", None))
    loss = {"raw_rows": raw_lines, "parsed_rows": len(data), "format": "csv"}
    return df, loss, len(fragments)


# =============================================================================
# Eras 1-3 (2004-2010): compound-ID wide format
# =============================================================================


def _split_compound_id(
    df: pl.DataFrame, id_col: str, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Classify detail level and split the Era 1-3 compound ``SysSchool*`` ID.

    ``ALL:ALL`` -> state, ``{d}:ALL`` -> district, ``{d}:{s}`` -> school.
    The Era 3 sub-header annotation row (NULL id) and any malformed ID are
    dropped and recorded — no repairable malformations exist in this source
    (verified: every non-null ID in every file matches the three shapes).
    """
    # Sub-header / null-ID rows (Era 3 row index 1) carry no entity.
    n_null = df.filter(pl.col(id_col).is_null()).height
    if n_null:
        manifest.record_filtered(year, n_null, "era3_sub_header_annotation_row")
        logger.info("Year %d: dropped %d sub-header/null-ID row(s)", year, n_null)
        df = df.filter(pl.col(id_col).is_not_null())

    ids = pl.col(id_col).cast(pl.Utf8).str.strip_chars()
    df = df.with_columns(ids.alias("_id"), ids.str.to_uppercase().alias("_id_upper"))
    df = df.with_columns(
        pl.when(pl.col("_id_upper") == "ALL:ALL")
        .then(pl.lit("state"))
        .when(pl.col("_id_upper").str.ends_with(":ALL"))
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .alias("detail_level")
    )
    df = df.with_columns(
        pl.col("_id")
        .str.split_exact(":", 1)
        .struct.rename_fields(["_district_raw", "_school_raw"])
        .alias("_parts")
    ).unnest("_parts")

    # Malformed-ID guard: district part must be digits on district/school
    # rows; school part must be digits on school rows. None expected.
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
            "Year %d: dropping %d malformed %s row(s): %s",
            year,
            bad.height,
            id_col,
            bad["_id"].head(5).to_list(),
        )
        manifest.record_filtered(year, bad.height, "malformed_sys_school_id")
        df = df.filter(~malformed)

    # Geography keys per domain CLAUDE.md (zfill; aggregate levels NULL —
    # null_aggregate_geography re-asserts this in main()).
    return df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.when(pl.col("detail_level") == "state")
        .then(None)
        .otherwise(pl.col("_district_raw").str.zfill(3))
        .alias("district_code"),
        pl.when(pl.col("detail_level") == "school")
        .then(pl.col("_school_raw").str.zfill(4))
        .otherwise(None)
        .alias("school_code"),
    )


def _unpivot_era123(
    df: pl.DataFrame,
    year: int,
    cells: list[tuple[str, str, str | None, str]],
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Unpivot resolved (demographic x component) cells into long gold rows.

    Args:
        df: Bronze frame with year/geography/detail_level already attached.
        year: Reporting year (for filter recording).
        cells: One tuple per cell: (raw_demographic_label, test_component,
            score_column_or_None, count_column). A None score column emits a
            count-only row (Era 2 "NULL"-string subgroups read as null
            anyway; Era 3 subgroups have no High columns at all).
        manifest: For categorical / filter recording.

    Returns:
        Long DataFrame with STANDARD_COLUMNS. Cells where both metrics are
        NULL produce no row (blank wide cell = not collected; the count of
        elided cell-rows is recorded for transparency).
    """
    id_cols = ["year", "district_code", "school_code", "detail_level"]
    frames: list[pl.DataFrame] = []
    observed_labels: list[str] = []
    prefix_bronze: list[str] = []
    prefix_gold: list[str] = []

    for raw_label, component, score_col, count_col in cells:
        observed_labels.append(raw_label)
        gold_demo = _demographic_gold_value(raw_label)
        score_expr = (
            _to_float_expr(score_col) if score_col else pl.lit(None, dtype=pl.Float64)
        )
        frames.append(
            df.select(
                *id_cols,
                pl.lit(gold_demo).alias("demographic"),
                pl.lit(component).alias("test_component"),
                _to_float_expr(count_col).alias("num_tested"),
                score_expr.alias("avg_score"),
            )
        )

    long_df = pl.concat(frames, how="vertical")

    # Blank-cell elision: a wide cell with neither count nor score is "not
    # collected" (e.g. 2004 elementary schools blank on every metric) and
    # produces no observation. Recorded so the expansion factor is auditable.
    n_empty = long_df.filter(
        pl.col("num_tested").is_null() & pl.col("avg_score").is_null()
    ).height
    if n_empty:
        manifest.record_filtered(year, n_empty, "empty_demographic_component_cells")
        logger.info(
            "Year %d: elided %d empty (demographic x component) cell row(s)",
            year,
            n_empty,
        )
        long_df = long_df.filter(
            pl.col("num_tested").is_not_null() | pl.col("avg_score").is_not_null()
        )

    _record_demographics(manifest, observed_labels)

    # Record the test_component mapping with the literal bronze column
    # prefixes as keys ("High Total" -> verbal_math, ...). Identical across
    # Eras 1-3, so the manifest merge is collision-free.
    for raw_label, component, score_col, _count_col in cells:
        prefix = next(
            (p for p, g in ERA123_HIGH_PREFIXES.items() if g == component), None
        )
        if prefix is not None:
            prefix_bronze.append(prefix)
            prefix_gold.append(component)
    manifest.record_categorical(
        column="test_component",
        map_dict=ERA123_HIGH_PREFIXES,
        bronze_series=pl.Series(prefix_bronze, dtype=pl.Utf8),
        gold_series=pl.Series(prefix_gold, dtype=pl.Utf8),
    )

    return long_df.select(STANDARD_COLUMNS)


def _transform_era1(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Era 1 (2004-2006): verbose demographic headers, 3 High components.

    Cell resolution handles the two header quirks: "High Verbal  Asian"
    (double space, all three years) and the no-space "O"/"R" suffix columns
    ("High TotalO", "Number TakenR").
    """
    era1_prefixes = {
        p: g for p, g in ERA123_HIGH_PREFIXES.items() if p != "High Writing"
    }
    _require_columns(
        df,
        ["SysSchoolID", "Number Taken All Students", "High Total All Students"],
        f"era_1 {year}",
    )
    df = _split_compound_id(df, "SysSchoolID", year, manifest)

    cells: list[tuple[str, str, str | None, str]] = []
    for token in ERA1_DEMO_TOKENS:
        joiner = "" if token in {"O", "R"} else " "
        count_col = f"Number Taken{joiner}{token}"
        _require_columns(df, [count_col], f"era_1 {year} demographic {token!r}")
        for prefix, component in era1_prefixes.items():
            candidates = [f"{prefix}{joiner}{token}"]
            if prefix == "High Verbal" and token == "Asian":
                candidates.insert(0, "High Verbal  Asian")  # double-space typo
            score_col = next((c for c in candidates if c in df.columns), None)
            if score_col is None:
                # All Era 1 files carry the full matrix — a miss is a bug.
                raise ValueError(
                    f"era_1 {year}: no score column for {prefix!r} x {token!r}; "
                    f"tried {candidates}"
                )
            cells.append((token, component, score_col, count_col))
    return _unpivot_era123(df, year, cells, manifest)


def _transform_era23(
    df: pl.DataFrame, year: int, era: str, manifest: TransformManifest
) -> pl.DataFrame:
    """Era 2 (2007) / Era 3 (2008-2010): single-letter demographic suffixes.

    Era 2: full 10-suffix matrix exists for every High prefix, but every
    demographic-split High column is the literal "NULL" string (read as
    null) — subgroup rows come out count-only naturally. Era 3: High columns
    exist for "0" (All Students) only and the R suffix is gone; subgroups
    are count-only by construction (no score column to reference).
    """
    id_col = "SysSchoolID" if era == "era_2" else "SysSchoolId"
    prefixes = dict(ERA123_HIGH_PREFIXES)
    if era == "era_2":
        prefixes.pop("High Writing")  # Writing starts in 2008
        suffixes = list(ERA23_SUFFIX_TO_LABEL)
    else:
        suffixes = [s for s in ERA23_SUFFIX_TO_LABEL if s != "R"]

    _require_columns(df, [id_col, "Number Taken0"], f"{era} {year}")
    df = _split_compound_id(df, id_col, year, manifest)

    cells: list[tuple[str, str, str | None, str]] = []
    for suffix in suffixes:
        count_col = f"Number Taken{suffix}"
        _require_columns(df, [count_col], f"{era} {year} suffix {suffix!r}")
        raw_label = ERA23_SUFFIX_TO_LABEL[suffix]
        for prefix, component in prefixes.items():
            score_col = f"{prefix}{suffix}"
            if score_col not in df.columns:
                if suffix == "0":
                    # All-Students High columns must exist in both eras.
                    raise ValueError(f"{era} {year}: missing column {score_col!r}")
                score_col = None  # Era 3 subgroups: count-only by design
            cells.append((raw_label, component, score_col, count_col))
    return _unpivot_era123(df, year, cells, manifest)


# =============================================================================
# Eras 4-5 (2011-2024): tidy format with side-by-side aggregate context
# =============================================================================


def _validate_era45_constants(df: pl.DataFrame, year: int) -> None:
    """Hard-stop if the Era 4/5 constant columns carry unexpected values.

    SUBGRP_DESC must be 'All Students' (anything else changes the fact grain
    and must be analyzed, not silently collapsed); Era 5's #ASSMT_CD must be
    'SAT' and HIGHEST_RECENT_IND must be 'Highest' (anything else means the
    wrong dataset is mixed into this topic's bronze).
    """
    subgroups = df["SUBGRP_DESC"].drop_nulls().unique().to_list()
    if subgroups != ["All Students"]:
        raise ValueError(
            f"era_4/5 {year}: unexpected SUBGRP_DESC values {subgroups}; "
            "the transform assumes the All Students-only grain"
        )
    if "#ASSMT_CD" in df.columns:
        assessments = df["#ASSMT_CD"].drop_nulls().unique().to_list()
        if assessments != ["SAT"]:
            raise ValueError(f"era_5 {year}: unexpected #ASSMT_CD {assessments}")
    if "HIGHEST_RECENT_IND" in df.columns:
        indicators = df["HIGHEST_RECENT_IND"].drop_nulls().unique().to_list()
        if indicators != ["Highest"]:
            raise ValueError(
                f"era_5 {year}: unexpected HIGHEST_RECENT_IND {indicators} — "
                "non-Highest rows belong to the sibling sat_scores_recent"
            )


def _modal_pair_rollup(
    base: pl.DataFrame,
    level: str,
    year: int,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Materialize official district/state rows via a modal (count, score) vote.

    Era 4/5 bronze repeats the rollup columns on every school row. They are
    constant within their groups in every year except 2024, where three
    no-school-data rows carry Math Section aggregates on their Combined Test
    Score rows (see module docstring). Resolution, applied per group:

    1. Rows with a NULL rollup count are excluded from the vote (a group
       that is all-NULL yields one (NULL, NULL) row — GOSA suppressed the
       rollup, the observation itself is real).
    2. When the group mixes rows that carry real school metrics with rows
       that don't, only the school-evidence rows vote (the 2024 mix-up rows
       all lack school metrics; this also breaks the 1-vs-1 Thomas County
       tie in favor of the row backed by a real high school).
    3. The most frequent surviving (count, score) PAIR wins — the pair is
       aggregated as a unit so a count from one bronze row is never spliced
       onto a score from another. A residual tie raises; no silent guess.

    Two kinds of overridden bronze rows are recorded via
    ``record_reclassified``: surviving voters whose pair lost the vote
    ("outvoted_modal_pair") and evidence-excluded rows whose pair differs
    from the winner ("overridden_no_school_evidence" — the 2024 mix-up
    rows, which never vote and so cannot appear in the loser count).
    """
    count_col, score_col = (
        ("DSTRCT_NUM_TESTED_CNT", "DSTRCT_AVG_SCORE_VAL")
        if level == "district"
        else ("STATE_NUM_TESTED_CNT", "STATE_AVG_SCORE_VAL")
    )
    group_keys = (
        ["year", "district_code", "demographic", "test_component"]
        if level == "district"
        else ["year", "demographic", "test_component"]
    )
    nulled_geo = (
        ["school_code"] if level == "district" else ["district_code", "school_code"]
    )

    work = base.with_columns(
        _to_float_expr(count_col).alias("_cnt"),
        _to_float_expr(score_col).alias("_avg"),
        (
            pl.col("INSTN_NUM_TESTED_CNT").is_not_null()
            & pl.col("INSTN_AVG_SCORE_VAL").is_not_null()
        ).alias("_has_school_evidence"),
    )

    # Step 1: NULL-count rows don't vote; all-NULL groups survive as
    # (NULL, NULL) suppressed-rollup rows.
    candidates = work.filter(pl.col("_cnt").is_not_null())
    all_null_groups = (
        work.select(group_keys)
        .unique()
        .join(candidates.select(group_keys).unique(), on=group_keys, how="anti")
    )

    # Step 2: evidence restriction, only where the group is mixed. The
    # excluded rows are kept aside so any whose context pair the vote
    # overrides can be recorded (the 2024 mix-up rows fall out here, before
    # loser counting — without this they would leave no manifest trace).
    candidates = candidates.with_columns(
        pl.col("_has_school_evidence").any().over(group_keys).alias("_grp_has_ev")
    )
    voters = candidates.filter(~pl.col("_grp_has_ev") | pl.col("_has_school_evidence"))
    excluded = candidates.filter(
        pl.col("_grp_has_ev") & ~pl.col("_has_school_evidence")
    )

    # Step 3: modal pair per group; residual tie -> hard stop.
    tallied = (
        voters.group_by([*group_keys, "_cnt", "_avg"])
        .agg(pl.len().alias("_votes"))
        .sort([*group_keys, "_votes"], descending=[False] * len(group_keys) + [True])
    )
    top_two = tallied.with_columns(
        pl.col("_votes").rank("ordinal", descending=True).over(group_keys).alias("_rk"),
        pl.col("_votes").max().over(group_keys).alias("_max_votes"),
        pl.len().over(group_keys).alias("_n_pairs"),
    )
    ties = top_two.filter(
        (pl.col("_n_pairs") > 1)
        & (pl.col("_votes") == pl.col("_max_votes"))
        & (pl.col("_rk") > 1)
    )
    if ties.height:
        raise ValueError(
            f"{level} rollup modal-pair tie in year {year} — refusing to "
            f"guess between divergent bronze aggregates:\n"
            f"{ties.select([*group_keys, '_cnt', '_avg', '_votes']).head(10)}"
        )
    winners = top_two.filter(pl.col("_rk") == 1)

    # Out-voted bronze rows = voters whose pair lost. Record as reclassified
    # (their aggregate context was repaired by the vote; no row was dropped).
    losers = voters.join(
        winners.select([*group_keys, "_cnt", "_avg"]),
        on=group_keys,
        how="inner",
        suffix="_win",
    ).filter(
        (pl.col("_cnt") != pl.col("_cnt_win")) | (pl.col("_avg") != pl.col("_avg_win"))
    )
    if losers.height:
        manifest.record_reclassified(
            year,
            losers.height,
            f"{level}_rollup_context_outvoted_modal_pair",
        )
        logger.warning(
            "Year %d: %d bronze row(s) carried divergent %s rollup context "
            "and were out-voted (modal pair). Sample: %s",
            year,
            losers.height,
            level,
            losers.select(
                "district_code", "school_code", "test_component", "_cnt", "_avg"
            )
            .head(5)
            .to_dicts(),
        )

    # Evidence-excluded rows whose context pair the vote overrode (the 2024
    # Math-Section-on-Combined mix-up rows): they never voted, so the loser
    # count above cannot see them — recorded separately for auditability.
    overridden = excluded.join(
        winners.select([*group_keys, "_cnt", "_avg"]),
        on=group_keys,
        how="inner",
        suffix="_win",
    ).filter(
        (pl.col("_cnt") != pl.col("_cnt_win")) | (pl.col("_avg") != pl.col("_avg_win"))
    )
    if overridden.height:
        manifest.record_reclassified(
            year,
            overridden.height,
            f"{level}_rollup_context_overridden_no_school_evidence",
        )
        logger.warning(
            "Year %d: %d no-school-evidence bronze row(s) carried divergent "
            "%s rollup context and were overridden by the evidence-backed "
            "modal pair. Sample: %s",
            year,
            overridden.height,
            level,
            overridden.select(
                "district_code", "school_code", "test_component", "_cnt", "_avg"
            )
            .head(5)
            .to_dicts(),
        )

    rollups = pl.concat(
        [
            winners.select(
                *group_keys,
                pl.col("_cnt").alias("num_tested"),
                pl.col("_avg").alias("avg_score"),
            ),
            all_null_groups.with_columns(
                pl.lit(None, dtype=pl.Float64).alias("num_tested"),
                pl.lit(None, dtype=pl.Float64).alias("avg_score"),
            ),
        ],
        how="vertical",
    )
    return rollups.with_columns(
        pl.lit(level).alias("detail_level"),
        *[pl.lit(None, dtype=pl.Utf8).alias(c) for c in nulled_geo],
    ).select(STANDARD_COLUMNS)


def _transform_era45(
    df: pl.DataFrame,
    year: int,
    district_col: str,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Era 4/5: school rows 1:1; district/state rows from context columns.

    NATIONAL_* context is out of scope (education detail levels are
    school/district/state) and never emitted.
    """
    _require_columns(
        df,
        [
            district_col,
            "INSTN_NUMBER",
            "SUBGRP_DESC",
            "TEST_CMPNT_TYP_CD",
            "INSTN_NUM_TESTED_CNT",
            "INSTN_AVG_SCORE_VAL",
            "DSTRCT_NUM_TESTED_CNT",
            "DSTRCT_AVG_SCORE_VAL",
            "STATE_NUM_TESTED_CNT",
            "STATE_AVG_SCORE_VAL",
        ],
        f"era_4/5 {year}",
    )
    _validate_era45_constants(df, year)

    base = df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        # zfill(3) pads 3-digit county codes and passes 7-digit state-charter
        # codes through unchanged (never truncate).
        pl.col(district_col)
        .cast(pl.Utf8)
        .str.strip_chars()
        .str.zfill(3)
        .alias("district_code"),
        # zfill(4) so the inconsistently padded 2011-2019 codes ('100' vs
        # '0100') compare across years.
        pl.col("INSTN_NUMBER")
        .cast(pl.Utf8)
        .str.strip_chars()
        .str.zfill(4)
        .alias("school_code"),
        pl.col("TEST_CMPNT_TYP_CD")
        .replace_strict(TEST_COMPONENT_MAP, default=None)
        .alias("test_component"),
        pl.lit(_demographic_gold_value("All Students")).alias("demographic"),
    )
    manifest.record_categorical(
        column="test_component",
        map_dict=TEST_COMPONENT_MAP,
        bronze_series=base["TEST_CMPNT_TYP_CD"],
        gold_series=base["test_component"],
    )
    _record_demographics(manifest, ["All Students"])

    schools = base.select(
        "year",
        "district_code",
        "school_code",
        "demographic",
        "test_component",
        _to_float_expr("INSTN_NUM_TESTED_CNT").alias("num_tested"),
        _to_float_expr("INSTN_AVG_SCORE_VAL").alias("avg_score"),
        pl.lit("school").alias("detail_level"),
    ).select(STANDARD_COLUMNS)

    districts = _modal_pair_rollup(base, "district", year, manifest)
    states = _modal_pair_rollup(base, "state", year, manifest)

    logger.info(
        "Year %d: materialized %d school, %d district, %d state rows",
        year,
        schools.height,
        districts.height,
        states.height,
    )
    return pl.concat([schools, districts, states], how="vertical")


# =============================================================================
# File routing
# =============================================================================


def _peek_csv_header(path: Path) -> list[str]:
    """Read just the header fields of a text CSV (latin-1 tolerant)."""
    with open(path, "rb") as fh:
        first = fh.readline().decode("latin-1")
    return next(csv.reader(io.StringIO(first)))


def _is_xls(path: Path) -> bool:
    """True when the file's magic bytes are OLE2 (XLS), whatever its suffix."""
    with open(path, "rb") as fh:
        return fh.read(8) == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame:
    """Read one bronze file, detect its era by columns, and route.

    Reader selection is structural, not year-based: XLS magic bytes (covers
    the 2005/2006 ``.csv``-named XLS binaries) -> shared xlrd reader;
    true CSVs whose header carries the Era 1 ``SysSchoolID`` signature ->
    the robust csv-module reader (the 2004 file defeats the stock readers,
    see module docstring); all other CSVs -> shared reader with
    ``infer_schema_length=0`` (all-string, preserves zero-padded codes; TFS
    et al. null at read time).

    Year resolution: Eras 1-3 carry no year column (filename year is the
    reporting year); Eras 4-5 derive it from ``LONG_SCHOOL_YEAR`` and
    cross-check the filename so a misnamed file cannot mislabel a year.
    """
    filename_year = extract_year_from_filename(path.name)
    if filename_year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")

    n_fragments = 0
    if not _is_xls(path) and "SysSchoolID" in _peek_csv_header(path):
        df, loss, n_fragments = _read_era1_csv(path)
    else:
        df, loss = read_bronze_file(path, infer_schema_length=0, return_loss=True)
    manifest.record_read_loss(
        filename_year, path.name, loss["raw_rows"], loss["parsed_rows"]
    )

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{path.name}: no era signature matched {df.columns[:8]}")

    if era in ("era_4", "era_5"):
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

    # Bronze counts include corrupted fragments (they are bronze records);
    # the fragment drop is then visible as an explicit filter event.
    manifest.record_file(path, year, era, df.height + n_fragments, df.columns)
    manifest.record_bronze(year, df.height + n_fragments)
    if n_fragments:
        manifest.record_filtered(
            year, n_fragments, "corrupted_partial_duplicate_fragments"
        )
    logger.info("Processing %s as %s (year %d)", path.name, era, year)

    if era == "era_1":
        return _transform_era1(df, year, manifest)
    if era in ("era_2", "era_3"):
        return _transform_era23(df, year, era, manifest)
    district_col = "SCHOOL_DISTRCT_CD" if era == "era_4" else "SCHOOL_DSTRCT_CD"
    return _transform_era45(df, year, district_col, manifest)


# =============================================================================
# §4b known-bad mask
# =============================================================================


def _null_invalid_sat_scores(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """NULL ``avg_score`` values outside their component's SAT scale (§4b).

    An average of per-student scores cannot leave the per-student scale, so
    out-of-scale values are publication errors, not data. 20 known values
    (see module docstring): 10 above their ceilings in 2009-2010 (Era 3
    wide files) and 10 old-SAT ``writing`` averages below the 200 floor in
    2011-2015 (7 school + 3 district rollup values, as low as 112).
    ``num_tested`` and the rows are preserved; the per-component range
    quality check in the contract keeps the invariant enforceable.
    """
    invalid_expr = pl.lit(False)
    for component, (lo, hi) in SAT_SCORE_RANGES.items():
        invalid_expr = invalid_expr | (
            (pl.col("test_component") == component)
            & pl.col("avg_score").is_not_null()
            & ((pl.col("avg_score") < lo) | (pl.col("avg_score") > hi))
        )

    invalid = df.filter(invalid_expr)
    if invalid.height:
        for component, group in invalid.group_by("test_component"):
            years = sorted(group["year"].unique().to_list())
            manifest.record_masked(
                "avg_score",
                group.height,
                f"outside_sat_scale_{component[0]}",
                years=years,
            )
        logger.warning(
            "§4b: NULLing %d impossible avg_score value(s) outside their "
            "component scale. Sample: %s",
            invalid.height,
            invalid.select(
                "year",
                "district_code",
                "school_code",
                "test_component",
                "avg_score",
            )
            .head(20)
            .to_dicts(),
        )
    return df.with_columns(
        pl.when(invalid_expr)
        .then(None)
        .otherwise(pl.col("avg_score"))
        .alias("avg_score")
    )


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for sat_scores_highest."""
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
    combined = pl.concat(all_dfs, how="vertical")
    logger.info("Combined %d rows across %d files", combined.height, len(all_dfs))

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean an alias/aggregation bug and must raise, not be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: every bronze file is a distinct year and the two 2016 files
    # have disjoint component vocabularies, so duplicates can only be
    # within-file repeats — one known block: the 2004 CSV publishes 25
    # entities twice byte-identically (Wilkinson/Worth/Atlanta; 72
    # gold-grain rows, proven identical by the collision guard above).
    # Prefer the row with a reported (non-null, larger) num_tested over a
    # suppressed placeholder. The per-year dedup delta is recorded below so
    # the manifest cell math reconciles exactly.
    pre_dedup_by_year = {
        int(row["year"]): int(row["len"])
        for row in combined.group_by("year").len().iter_rows(named=True)
    }
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
    for row in combined.group_by("year").len().iter_rows(named=True):
        n_deduped = pre_dedup_by_year[int(row["year"])] - int(row["len"])
        manifest.record_filtered(
            int(row["year"]), n_deduped, "identical_duplicate_rows"
        )

    # 4. Geography nulling (shared domain rules), then the §4b mask.
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )
    combined = _null_invalid_sat_scores(combined, manifest)

    # Pre-export sanity. NULL-rate spikes are expected with documented bronze
    # causes: avg_score is NULL on all 2007-2010 subgroup rows (count-only
    # eras) and Era 4/5 TFS suppression grows over time.
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


def _quality_checks() -> list[dict]:
    """Author the topic's cross-column invariants (§15b)."""
    range_violation = " OR ".join(
        f"(test_component = '{component}' AND (avg_score < {lo} OR avg_score > {hi}))"
        for component, (lo, hi) in SAT_SCORE_RANGES.items()
    )
    new_sat_components = (
        "'combined_test_score','math_section_score','reading_test_score',"
        "'writlang_test_score','essay_reading_score','essay_analysis_score',"
        "'essay_writing_score','essay_total'"
    )
    return [
        {
            "name": "avg_score_within_component_scale",
            "description": (
                "Each test_component's avg_score stays within its physical "
                "SAT scale (sections 200-800; verbal_math / "
                "combined_test_score 400-1600; combined 600-2400; essay "
                "dimensions 2-8; essay_total 6-24). The GOSA-rescaled "
                "reading_test_score / writlang_test_score components have no "
                "published ceiling and are intentionally excluded. Enforces "
                "the transform's known-bad mask."
            ),
            "dimension": "accuracy",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE avg_score IS NOT NULL "
                f"AND ({range_violation})"
            ),
            "mustBe": 0,
        },
        {
            "name": "verbal_math_equals_reading_plus_mathematics",
            "description": (
                "2004-2010 wide bronze satisfies High Total = High Verbal + "
                "High Math exactly (max abs diff 0.0 in 2007-2010, <= 1 in "
                "2005), so every gold verbal_math row must equal its "
                "matching reading + mathematics rows within 1 point when all "
                "three are non-NULL (masked/suppressed rows drop out via the "
                "NULL guard)."
            ),
            "dimension": "consistency",
            # Conditional-aggregation pivot, not a self-join: GROUP BY treats
            # NULL geography keys as equal (IS NOT DISTINCT FROM semantics)
            # and avoids the join-plan blowup the sibling topic hit when
            # DuckDB hoisted INDF conditions off the inner joins (see
            # data-cleaning-standards §15b).
            "query": (
                "SELECT COUNT(*) FROM ("
                "SELECT year, district_code, school_code, demographic, "
                "MAX(CASE WHEN test_component = 'verbal_math' "
                "THEN avg_score END) AS total, "
                "MAX(CASE WHEN test_component = 'reading' "
                "THEN avg_score END) AS reading, "
                "MAX(CASE WHEN test_component = 'mathematics' "
                "THEN avg_score END) AS mathematics "
                "FROM {object} WHERE year <= 2010 AND test_component IN "
                "('verbal_math', 'reading', 'mathematics') "
                "GROUP BY year, district_code, school_code, demographic"
                ") WHERE total IS NOT NULL AND reading IS NOT NULL "
                "AND mathematics IS NOT NULL "
                "AND ABS(total - reading - mathematics) > 1.0"
            ),
            "mustBe": 0,
        },
        {
            "name": "combined_equals_reading_plus_mathematics_plus_writing",
            "description": (
                "2011-2016 old-SAT files publish combined as the three-"
                "section V+M+W total (600-2400), so every gold combined row "
                "must equal its matching reading + mathematics + writing "
                "rows within 1 point when all four are non-NULL "
                "(empirically holds on all 3,473 complete groups, max abs "
                "diff 1.0; masked/suppressed rows drop out via the NULL "
                "guard)."
            ),
            "dimension": "consistency",
            # Same conditional-aggregation pivot as the verbal_math check
            # above — never a self-join (data-cleaning-standards §15b).
            "query": (
                "SELECT COUNT(*) FROM ("
                "SELECT year, district_code, school_code, demographic, "
                "MAX(CASE WHEN test_component = 'combined' "
                "THEN avg_score END) AS total, "
                "MAX(CASE WHEN test_component = 'reading' "
                "THEN avg_score END) AS reading, "
                "MAX(CASE WHEN test_component = 'mathematics' "
                "THEN avg_score END) AS mathematics, "
                "MAX(CASE WHEN test_component = 'writing' "
                "THEN avg_score END) AS writing "
                "FROM {object} WHERE year BETWEEN 2011 AND 2016 "
                "AND test_component IN "
                "('combined', 'reading', 'mathematics', 'writing') "
                "GROUP BY year, district_code, school_code, demographic"
                ") WHERE total IS NOT NULL AND reading IS NOT NULL "
                "AND mathematics IS NOT NULL AND writing IS NOT NULL "
                "AND ABS(total - reading - mathematics - writing) > 1.0"
            ),
            "mustBe": 0,
        },
        {
            "name": "test_component_year_coverage",
            "description": (
                "Each test_component appears only in the years its source "
                "era publishes it: verbal_math 2004-2010; reading/"
                "mathematics 2004-2016 (old SAT); writing 2008-2016; "
                "combined 2011-2016; redesigned-SAT components 2016+; "
                "evidence_based_reading_and_writing 2016-2019 only."
            ),
            "dimension": "consistency",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE "
                "(test_component = 'verbal_math' AND year > 2010) "
                "OR (test_component IN ('reading','mathematics') AND year > 2016) "
                "OR (test_component = 'writing' AND (year < 2008 OR year > 2016)) "
                "OR (test_component = 'combined' AND (year < 2011 OR year > 2016)) "
                "OR (test_component = 'evidence_based_reading_and_writing' "
                "AND (year < 2016 OR year > 2019)) "
                f"OR (test_component IN ({new_sat_components}) AND year < 2016)"
            ),
            "mustBe": 0,
        },
        {
            "name": "demographic_breakdowns_only_pre_2011",
            "description": (
                "Only the 2004-2010 wide bronze publishes demographic "
                "breakdowns; every 2011+ row is demographic = 'all'."
            ),
            "dimension": "consistency",
            "query": (
                "SELECT COUNT(*) FROM {object} "
                "WHERE year >= 2011 AND demographic != 'all'"
            ),
            "mustBe": 0,
        },
        {
            "name": "subgroup_scores_only_2004_2006",
            "description": (
                "Demographic-split HIGHEST scores exist only in 2004-2006 "
                "bronze; 2007-2010 subgroup rows are count-only (the 2007 "
                "demographic High columns are the literal 'NULL' string and "
                "2008-2010 publish no subgroup High columns), so any "
                "non-'all' row outside 2004-2006 must have NULL avg_score."
            ),
            "dimension": "consistency",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE demographic != 'all' "
                "AND avg_score IS NOT NULL AND (year < 2004 OR year > 2006)"
            ),
            "mustBe": 0,
        },
        {
            "name": "avg_score_requires_positive_num_tested",
            "description": (
                "A published average implies at least one reported "
                "test-taker: avg_score must not be non-NULL while num_tested "
                "is NULL or < 1. Verified to hold in every bronze era "
                "(counts are published even where scores are suppressed)."
            ),
            "dimension": "consistency",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE avg_score IS NOT NULL "
                "AND (num_tested IS NULL OR num_tested < 1)"
            ),
            "mustBe": 0,
        },
        {
            "name": "state_rows_always_have_num_tested",
            "description": (
                "GOSA publishes unsuppressed statewide counts in every era: "
                "state-level rows (district_code and school_code both NULL) "
                "must carry non-NULL num_tested."
            ),
            "dimension": "completeness",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE district_code IS NULL "
                "AND school_code IS NULL AND num_tested IS NULL"
            ),
            "mustBe": 0,
        },
        {
            "name": "fractional_num_tested_only_on_combined_test_score",
            "description": (
                "GOSA publishes fractional test-taker counts ONLY on the "
                "redesigned-SAT Combined Test Score component (the "
                "equal-weight mean of the three section counts — the reason "
                "num_tested is Float64); every other component's count must "
                "be integral."
            ),
            "dimension": "consistency",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE num_tested IS NOT NULL "
                "AND test_component != 'combined_test_score' "
                "AND num_tested != ROUND(num_tested)"
            ),
            "mustBe": 0,
        },
    ]


def _emit_contract_and_readme(year_range: tuple[int, int]) -> None:
    """Emit the ODCS contract and gold README via ``write_data_dictionary``.

    The column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level`` — the contract's properties (and the validator's schema
    check) follow it.
    """
    demographic_values = sorted({_demographic_gold_value(t) for t in ERA1_DEMO_TOKENS})
    component_values = sorted(
        set(TEST_COMPONENT_MAP.values()) | set(ERA123_HIGH_PREFIXES.values())
    )
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        # 1.1.0: num_tested short_description added (fractional combined-score
        # counts are source-published averages, not headcounts).
        version="1.1.0",
        description=(
            "Average SAT scores by test section for Georgia public high "
            "schools, with official district and state rollups, using each "
            "student's HIGHEST section score across SAT administrations "
            "(the companion sat_scores_recent topic reports the most-recent "
            "administration instead). Spans the 2004-2024 GOSA publications "
            "across the old SAT (Verbal/Math, later +Writing) and the 2016 "
            "redesigned SAT (Evidence-Based Reading and Writing, Math, "
            "optional Essay)."
        ),
        title="SAT Scores (Highest Section Score)",
        summary=(
            "Average SAT scores by section for Georgia public high schools, "
            "using each student's highest score across test dates, 2004-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Reporting year. For 2011-2024 this is the spring "
                    "(ending) calendar year of the school year in the "
                    "source's LONG_SCHOOL_YEAR; for 2004-2010 the source "
                    "carries no year column and the filename publication "
                    "year is used."
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
                    "not globally unique on its own). NULL on district- and "
                    "state-level rows."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "all",
                "validValues": demographic_values,
                "short_description": (
                    "Student race or gender subgroup; breakdowns exist only "
                    "for 2004-2010, every later row is 'all'."
                ),
                "description": (
                    "Student demographic (FK to demographics dimension). "
                    "Breakdowns exist only for 2004-2010: race buckets "
                    "(asian_pacific_islander, black, hispanic, "
                    "native_american, white, other, race_unknown) and gender "
                    "(female, male); every 2011-2024 row is 'all'. The "
                    "source's bare 'Asian' label is the pre-1997 OMB "
                    "COMBINED Asian/Pacific Islander bucket (no era of this "
                    "source publishes a separate Pacific Islander row), so "
                    "it maps to asian_pacific_islander — race buckets are "
                    "mutually exclusive within this topic. 2007-2010 "
                    "subgroup rows carry counts only (avg_score is NULL); "
                    "race_unknown ('No Response') carries data in 2004 only "
                    "(the source's R columns exist through 2007 but are "
                    "blank in 2005-2006 and literal-'NULL' in 2007)."
                ),
            },
            {
                "name": "test_component",
                "type": "string",
                "nullable": False,
                "example": "combined_test_score",
                "validValues": component_values,
                "short_description": (
                    "Which SAT section or composite the score is for; scales "
                    "differ, so never compare across components."
                ),
                "description": (
                    "SAT section/composite, era-aware: 2004-2010 wide files "
                    "publish reading (source 'High Verbal'), mathematics "
                    "('High Math'), verbal_math (their 400-1600 two-section "
                    "total, equal to reading + mathematics) and writing "
                    "(2008-2010); 2011-2016 old-SAT files publish reading, "
                    "mathematics, writing and combined (the 600-2400 "
                    "three-section total); 2016-2024 redesigned-SAT files "
                    "publish combined_test_score (400-1600), "
                    "math_section_score (200-800), reading_test_score / "
                    "writlang_test_score (GOSA-rescaled 10-40 section tests, "
                    "observed ~190-340), evidence_based_reading_and_writing "
                    "(200-800, 2016-2019 only), and the essay components "
                    "(essay_reading_score / essay_analysis_score / "
                    "essay_writing_score on 2-8, essay_total on 6-24). "
                    "Old-SAT and redesigned-SAT composites are NOT "
                    "comparable across 2016."
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
                "example": 104,
                "null_meaning": (
                    "Suppressed by GOSA (TFS marker, 2011-2024) or not "
                    "published for that rollup."
                ),
                "description": (
                    "Number of students tested. Float64 by documented "
                    "exception (data-cleaning-standards §16): 2016-2024 "
                    "bronze publishes FRACTIONAL counts on the "
                    "combined_test_score component because GOSA reports it "
                    "as the equal-weight mean of the three SAT section "
                    "test-taker counts (Math, Reading, Writing & Language), "
                    "not a headcount (e.g. (47+37+37)/3 -> 40.3 — exact "
                    "thirds in 2016-2019, rounded to one decimal from ~2020); "
                    "rounding to an integer would lose precision, and every "
                    "other component's count is integral (enforced by a "
                    "quality check). 2004-2010 sources publish one count per "
                    "(entity, demographic) administration, repeated on each "
                    "of that demographic's component rows; 2011-2024 "
                    "sources publish true per-component counts. Either way, "
                    "summing num_tested across test_component double-counts "
                    "students — filter to one component for headcounts. A "
                    "count of 0 is a real observation (zero students in "
                    "that demographic took the SAT)."
                ),
            },
            {
                "name": "avg_score",
                "type": "float64",
                "key_metric": True,
                "unit": "score",
                "example": 1043.6,
                "null_meaning": (
                    "Suppressed by GOSA (too few test-takers), a count-only "
                    "observation (all 2007-2010 demographic subgroup rows), "
                    "or one of 20 impossible source values NULLed by the "
                    "transform (2009-2015)."
                ),
                "short_description": (
                    "Average highest-attempt SAT score; on the scale of the "
                    "section named by test_component."
                ),
                "description": (
                    "Average SAT score on the component's own scale (see "
                    "test_component; scales range from essay 2-8 up to "
                    "combined 600-2400, so never aggregate avg_score across "
                    "components). Known source defects NULLed per "
                    "data-cleaning-standards §4b (rows and num_tested "
                    "preserved; 20 values): (a) 2009 Heritage High School "
                    "(722:176) published reading=1022, mathematics=995, "
                    "writing=976, verbal_math=2017 and South Atlanta "
                    "Leadership (761:308) writing=811 — all above the "
                    "200-800 / 400-1600 scales; (b) 2010 Rockdale County "
                    "High (722:3052) published reading=1055, "
                    "mathematics=1113, writing=1009, verbal_math=2168 and "
                    "Elberta Open Campus (676:3050) reading=822; (c) "
                    "2011-2015 published 10 old-SAT writing averages below "
                    "the 200 section floor (7 school + 3 district rollup "
                    "values, as low as 112). An average cannot leave the "
                    "per-student scale, so these are publication errors; "
                    "NULLing them revises the preserve-bronze default for "
                    "this column and keeps the per-component range quality "
                    "check enforceable. Preserved-but-flagged instead: 2010 "
                    "Elberta verbal_math=1522 (in range, but its masked "
                    "reading component makes it suspect) and the "
                    "systematically low 2011-2016 writing averages (state "
                    "361-406 vs ~470 on the recent-SAT basis) — see "
                    "limitations."
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
            "school_code. avg_score scales differ by test_component — never "
            "compare or aggregate across components, and never sum "
            "num_tested across components (it double-counts students). "
            "Old-SAT (pre-2016) and redesigned-SAT (2016+) results are not "
            "comparable. HIGHEST-basis caveat for the old-SAT writing "
            "component (2011-2016): GOSA's published averages are "
            "systematically far below the recent-basis values (state "
            "361-406 vs ~470) and 10 values fall below the section's 200 "
            "floor (NULLed); in-range writing values — and the combined "
            "composite that embeds them — appear deflated on the highest "
            "basis and should be used with caution. The 2010 Elberta Open "
            "Campus verbal_math value (1522) is preserved although its "
            "reading component (822) was impossible and NULLed."
        ),
        notes=[
            (
                "Topic semantics: scores reflect each student's HIGHEST "
                "section score across SAT administrations. The sibling "
                "sat_scores_recent topic reports the most-recent "
                "administration with the same column names and "
                "test_component vocabulary."
            ),
            (
                "District and state rows are the official GOSA aggregates "
                "(2004-2010: published ':ALL' / 'ALL:ALL' rollup rows; "
                "2011-2024: the DSTRCT_*/STATE_* context columns), never "
                "re-aggregated from suppressed school rows."
            ),
            (
                "2024 source defect, resolved by a modal-pair vote: three "
                "bronze rows without school data (McDonough Middle 675:4050, "
                "Pleasant Valley Innovative 705:0108, Bishop Hall Charter "
                "736:0100) carry the Math Section Score district/state "
                "aggregates on their Combined Test Score rows; the "
                "majority (count, score) pair from rows backed by real "
                "school data wins."
            ),
            (
                "The 2004 file contains two corrupted records — a 48-field "
                "mid-file fragment and an 11-field truncated final record — "
                "both byte-identical partial duplicates of complete rows "
                "(Wilkinson County 758:ALL and Mays High School 761:182); "
                "they are dropped with no information loss."
            ),
            (
                "2004-2010 demographic coverage: 2004-2006 publish full "
                "demographic-split highest scores and counts; 2007 publishes "
                "subgroup counts with literal-'NULL' score cells; 2008-2010 "
                "publish subgroup counts only. Subgroup rows in 2007-2010 "
                "therefore carry num_tested with avg_score NULL."
            ),
            (
                "Race buckets 2004-2010 use the pre-1997 OMB combined "
                "Asian/Pacific Islander concept under the source's bare "
                "'Asian' label (no era publishes a separate Pacific "
                "Islander row); gold maps it to asian_pacific_islander. "
                "'No Response' (R) maps to race_unknown and carries data in "
                "2004 only — the R columns exist through 2007 but are blank "
                "in 2005-2006 and literal-'NULL' in 2007; 'Other' (O) maps "
                "to other."
            ),
            (
                "Blank wide-format cells (2004-2010), e.g. the ~1,700 "
                "elementary/middle-school rows in the 2004 file with no SAT "
                "data, produce no gold rows. Explicit Era 4/5 TFS "
                "suppression IS kept as NULL-metric rows (the observation "
                "exists; the value is suppressed)."
            ),
            (
                "National benchmark data (NATIONAL_* columns, 2011-2024) is "
                "out of scope — education detail levels are school/district/"
                "state."
            ),
            (
                "NULL rates for avg_score are structurally high in "
                "2007-2010 (count-only subgroup rows) and rise from 2020 "
                "(COVID-era test-optional admissions push more schools "
                "under GOSA's suppression threshold) — both mirror bronze."
            ),
        ],
        quality_checks=_quality_checks(),
    )


if __name__ == "__main__":
    main()
