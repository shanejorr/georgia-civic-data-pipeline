"""Transform bronze georgia_milestones_end_of_grade files into gold fact tables.

Source: Georgia Insights (GaDOE) — Georgia Milestones End-of-Grade (EOG)
assessment results for grades 3-8, published annually (no 2020 release —
COVID cancelled the administration) at three detail levels (state,
system/district, school). There are no demographic breakdowns anywhere in
this bronze, so per data-cleaning-standards §5 the ``demographic`` column is
omitted from gold. Grade is the primary row axis and lives in
``grade_level`` ('03'..'08').

Every sheet is a two-row pivot header: row 0 title banner, row 1
subject-block super-header (merged across each block), row 2 metric
sub-header. Reads use pandas ``header=[1, 2]`` + ``dtype=str`` (pandas
forward-fills merged header cells itself); the shared ``read_bronze_file``
reads only the first sheet of a workbook, so multi-sheet/zip reading uses
local helpers — the GeorgiaInsights precedent set by the EOC sibling.
Whole-sheet Excel reads cannot drop records at parse time, so read-loss
raw == parsed by construction and no read-loss events are recorded.

Era routing is STRUCTURAL (zip vs. workbook sheet count), not year-tag
based. Three file shapes (re-verified against all 30 files during
authoring):

- ``zip_per_grade`` — 2015-2021 system/school zips: six single-sheet
  member workbooks, one grade each (2015 members are legacy ``.xls``
  double-nested under a redundant directory; grade parsed from the member
  basename).
- ``state_all_grades_single_sheet`` — 2015-2021 state files: one sheet,
  all six grades as ROWS in a ``Grade`` column; 2018+ append a Lexile
  legend + footnotes below the data.
- ``consolidated_multi_sheet`` — 2022-2025 workbooks (every detail
  level): six per-grade sheets (``State - Grade 3`` … ``School -
  Grade 8``), grade parsed from the sheet name.

Design decisions (each re-verified against bronze during authoring):

- **Wide → long unpivot.** Each (sheet row × subject block) becomes one
  gold row keyed (year, detail_level, district_code, school_code,
  grade_level, subject, assessment_type). Block super-headers carry both
  the subject and, in 2016-2021, an ``- EOG`` / ``- EOC`` / ``- EOG and
  EOC Combined`` variant suffix that maps to ``assessment_type``
  (middle-schoolers taking End-of-Course exams early; bare blocks and
  2022+ are ``eog``). EOC/Combined triples were re-verified to exist for
  Mathematics (2016-2019 gr 6-8), Science (2016-2021 gr 8, plus state
  columns), and English Language Arts (2018-2019) — never for Social
  Studies.

- **NaN vs. '--' distinction.** Reads do NOT pass ``na_values``: a truly
  empty (NaN) block cell means the block does not exist for that row,
  while the suppression marker ``'--'`` is a real-but-suppressed
  observation. Per block, rows whose every metric cell is NaN are dropped
  before casting (structural absence, not data); suppression markers then
  become NULL via ``strict=False`` casts, so fully-suppressed school /
  district rows survive as all-NULL-metric observations.

- **Placeholder blocks.** State readers drop post-cast all-NULL-metric
  rows (a state aggregate cannot be small-N suppressed — an all-'--'
  state row is a non-administered placeholder, e.g. the EOC columns for
  grades 3-5 in the 2016-2021 state files). In ``main()``, whole
  (year, detail_level, grade_level, subject, assessment_type) groups in
  which EVERY row is all-NULL are dropped as non-administered placeholder
  blocks (e.g. 2016 grade-6 system Science-EOC, all '--'); genuine
  small-N suppression survives because such groups still contain
  unsuppressed entities. Both drops are ledgered.

- **Metric-family folding (§16 "Assessment subject").** Bronze ships
  ``Reading Status`` (Lexile, 2018+) and ``SGP English Language Arts`` /
  ``SGP Mathematics`` (2024+, grades 4-8) as parallel subject blocks, but
  they are metric families measured on the parent subject's test-taker
  population. After concat, ``_fold_metric_family_rows()`` left-joins the
  child metric columns onto the parent academic row in the same
  (year, detail_level, geography, grade_level, assessment_type) cell and
  drops the child row (ledgered per year). Orphan child rows with no
  parent are relabelled to the parent subject in place (ledgered as
  reclassified). The Reading Status block's own ``Number Tested`` (and
  2021 ``Percent of Enrolled Students Tested``) are intentionally NOT
  folded — the parent ELA row keeps its own counts; in current bronze the
  two counts are equal in practice.

- **2021 grade-8 System merged-cell artifact.** In ``Spring 2021 EOG -
  System Level - Grade 8.xlsx`` the ELA-EOG block leaves the ``Percent of
  Enrolled Students Tested`` sub-header cell blank; pandas forward-fills
  it to ``Number Tested.1``. The values under it are participation rates
  (91.57, 89.92, 100 …), so ``_repair_missing_pct_enrolled()`` relabels a
  within-block duplicate sub-header to the missing metric — but only in
  sheets where other blocks carry that metric. Verified to fire exactly
  once across all 30 files.

- **Percent columns ship 0-100 in every era** (re-verified per era) and
  are divided by 100 to the canonical 0-1 scale; floating-point residue
  within 1e-9 of the [0, 1] boundaries is snapped to the boundary.
  ``avg_scale_score`` (140-830 EOG scale), ``scale_score_std_dev`` and
  ``sgp_median`` (percentile rank; Float64 because even populations yield
  .5 medians) keep their natural scales.

- **2015 identity repairs** (both ledgered as reclassified):
  (a) 2015 system files key the State/Commission Charter campuses with
  hyphenated codes (``782-0110``); the hyphen is stripped, yielding the
  same 7-digit campus codes 2016+ files use. 2015 school files instead
  carry the bare SYSTEM codes 782/783 — the shared
  ``_charter_district_promotion`` module promotes those rows to the
  7-digit campus codes (system + school code) in ``main()``.
  (b) 2015 files reuse ``System Code = 799`` for three distinct state
  schools (Atlanta Area Schools, GA Academy for the Blind, GA School for
  the Deaf); 2016+ bronze and the districts dimension key them as
  ``7991893`` / ``7991894`` / ``7991895``, so 2015 rows are remapped via
  the system name (district level) / school code (school level).

- **Footnote / legend rows are filtered explicitly** (ledgered per file):
  the Lexile reading-status footnote (``^/*To achieve…``), the 2018-2021
  state-file Lexile threshold legend (``Grade`` header row + ``Lexile <
  NNNL`` body rows), and the 2021 COVID notes (``Note:…``, ``For more
  information…``, ``https://…``). A full-file scan verified no real
  district/school name starts with any filter prefix.

- **Dedup tie-break**: each (year, detail_level) is fed by exactly one
  bronze file and natural keys are unique within files, so dedup is
  purely defensive; ``sort_col="num_tested"`` would prefer a row with a
  reported count over a placeholder. ``assert_no_natural_key_collisions``
  runs first (after folding + promotion) so any repair-induced duplicate
  key with DIVERGENT metrics fails loudly instead of being silently
  resolved.

Known bronze-data-structure.md claims corrected during authoring (see the
doc's Corrections section): 2017 is NOT ELA/Math-only (Science + Social
Studies at grades 5 and 8, with Science EOC triples at grade 8); the
EOG/EOC split starts in 2016, not 2018, and never applies to Social
Studies; per-grade 2018-2019 files carry EOC blocks only at grades 6-8
(the all-'--' elementary EOC columns exist only in the all-grades state
files); 2022 grade 8 retains Science / Social Studies and already adds HS
Physical Science (not 2023).
"""

import io
import logging
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import polars as pl

from src.etl.education.georgiainsights._charter_district_promotion import (
    promote_charter_system_to_campus_district,
)
from src.utils.grades import normalize_grade_column
from src.utils.metadata import write_data_dictionary
from src.utils.readers import list_bronze_files
from src.utils.subjects import apply_subject_normalization
from src.utils.transformers import (
    TransformManifest,
    assert_no_natural_key_collisions,
    deduplicate_by_detail_level,
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

TOPIC = "georgia_milestones_end_of_grade"
BRONZE_DIR = Path(
    "data/bronze/education/georgiainsights/georgia_milestones_end_of_grade"
)
GOLD_DIR = Path("data/gold/education/georgia_milestones_end_of_grade")

# =============================================================================
# Normalization maps
# =============================================================================

ASSESSMENT_TYPE_EOG = "eog"
ASSESSMENT_TYPE_EOC = "eoc"
ASSESSMENT_TYPE_COMBINED = "eog_and_eoc_combined"

# Canonicalized super-header (UPPERCASE, footnote daggers */^ stripped,
# whitespace collapsed — see _canonical_super) → (interim subject,
# assessment_type). Every key was observed in bronze (full 30-file header
# inventory during authoring); _unpivot_blocks RAISES on anything unmapped.
#
# reading_status / sgp_* are INTERIM labels only: per §16 "Assessment
# subject" they are metric families, not academic subjects, and
# _fold_metric_family_rows() merges their metric columns onto the parent
# academic row after concat. They never appear in gold.
SUBJECT_BLOCK_MAP: dict[str, tuple[str, str]] = {
    # Reading Status — Lexile metric family on ELA test takers (2018+).
    # Source ships "Reading Status*" (2018-2019 + 2021 state) and
    # "Reading Status^" (2021-2025 system/school + 2022+ state).
    "READING STATUS": ("reading_status", ASSESSMENT_TYPE_EOG),
    # English Language Arts — EOC/Combined variants observed 2018-2019;
    # bare ELA coexists with the EOC variants in the per-grade files.
    "ENGLISH LANGUAGE ARTS": ("english_language_arts", ASSESSMENT_TYPE_EOG),
    "ENGLISH LANGUAGE ARTS - EOG": ("english_language_arts", ASSESSMENT_TYPE_EOG),
    "ENGLISH LANGUAGE ARTS - EOC": ("english_language_arts", ASSESSMENT_TYPE_EOC),
    "ENGLISH LANGUAGE ARTS - EOG AND EOC COMBINED": (
        "english_language_arts",
        ASSESSMENT_TYPE_COMBINED,
    ),
    # Mathematics — EOC/Combined variants observed 2016-2019 (grades 6-8).
    "MATHEMATICS": ("mathematics", ASSESSMENT_TYPE_EOG),
    "MATHEMATICS - EOG": ("mathematics", ASSESSMENT_TYPE_EOG),
    "MATHEMATICS - EOC": ("mathematics", ASSESSMENT_TYPE_EOC),
    "MATHEMATICS - EOG AND EOC COMBINED": ("mathematics", ASSESSMENT_TYPE_COMBINED),
    # Science — EOC/Combined variants observed 2016-2021 (grade 8 +
    # state-file columns).
    "SCIENCE": ("science", ASSESSMENT_TYPE_EOG),
    "SCIENCE - EOG": ("science", ASSESSMENT_TYPE_EOG),
    "SCIENCE - EOC": ("science", ASSESSMENT_TYPE_EOC),
    "SCIENCE - EOG AND EOC COMBINED": ("science", ASSESSMENT_TYPE_COMBINED),
    # Social Studies — never has EOC/Combined variants in this bronze.
    "SOCIAL STUDIES": ("social_studies", ASSESSMENT_TYPE_EOG),
    "SOCIAL STUDIES - EOG": ("social_studies", ASSESSMENT_TYPE_EOG),
    # HS Physical Science — grade 8 only, 2022 onward (8th-graders taking
    # the high-school course early). Canonical physical_science aligns
    # with georgia_milestones_end_of_course; the grade-8 distinction is
    # carried by grade_level, not the subject label.
    "HS PHYSICAL SCIENCE": ("physical_science", ASSESSMENT_TYPE_EOG),
    # SGP metric families — grades 4-8 ELA/Math, 2024 onward (interim).
    "SGP ENGLISH LANGUAGE ARTS": ("sgp_english_language_arts", ASSESSMENT_TYPE_EOG),
    "SGP MATHEMATICS": ("sgp_mathematics", ASSESSMENT_TYPE_EOG),
}

# Canonicalized metric sub-header (UPPERCASE, whitespace collapsed, Lexile
# parenthetical + pandas ".N" dedup suffix stripped — see _canonical_metric)
# → gold metric column. Full 30-file inventory; _unpivot_blocks raises on
# unmapped metrics.
METRIC_NAME_MAP: dict[str, str] = {
    "NUMBER TESTED": "num_tested",
    "MEAN SCALE SCORE": "avg_scale_score",
    "STANDARD DEVIATION": "scale_score_std_dev",
    "% BEGINNING LEARNER": "pct_beginning_learner",
    "% DEVELOPING LEARNER": "pct_developing_learner",
    "% PROFICIENT LEARNER": "pct_proficient_learner",
    "% DISTINGUISHED LEARNER": "pct_distinguished_learner",
    "% DEVELOPING LEARNER & ABOVE": "pct_developing_learner_or_above",
    "% PROFICIENT LEARNER & ABOVE": "pct_proficient_learner_or_above",
    # Reading Status — per-grade files annotate the grade-specific Lexile
    # threshold in a parenthetical that _canonical_metric strips.
    "% BELOW GRADE LEVEL": "pct_below_grade_level_lexile",
    "% GRADE LEVEL OR ABOVE": "pct_grade_level_or_above_lexile",
    # COVID-era participation column — 2021 files only.
    "PERCENT OF ENROLLED STUDENTS TESTED": "enrolled_tested_rate",
    # SGP block — 2024 onward, grades 4-8 ELA/Math.
    "NUMBER RECEIVED SGP": "num_sgp_received",
    "SGP MEDIAN": "sgp_median",
    "% SGP LOW GROWTH": "pct_sgp_low_growth",
    "% SGP TYPICAL GROWTH": "pct_sgp_typical_growth",
    # Bronze typo: the 2024/2025 State grade-5 SGP Mathematics block ships
    # "% SGPTypical Growth" (missing space). Same metric.
    "% SGPTYPICAL GROWTH": "pct_sgp_typical_growth",
    "% SGP HIGH GROWTH": "pct_sgp_high_growth",
}

# Identifier super-headers → flat destination columns. "_drop" columns are
# dimension attributes (names live in the dimension tables, RESA on the
# districts dimension). "_name_tmp" is kept through the unpivot ONLY so the
# 2015 district-level 799 remap can dispatch on the system name; it is
# dropped before any frame leaves a reader.
_IDENTIFIER_MAP: dict[str, str] = {
    "SYSTEM CODE": "district_code",
    "SCHOOL CODE": "school_code",
    "SYSTEM NAME": "_name_tmp",
    "SCHOOL NAME": "_drop",
    "RESA": "_drop",
    "GRADE": "_grade_raw",
}

# Some files merge the System Name column under the "System Code"
# super-header (e.g. 2017/2019/2021 system grade 3-4 members ship
# ('System Code', 'System Name')). When the SUB-header itself is an
# identifier, its classification wins over the parent's.
_IDENTIFIER_CHILD_OVERRIDES: dict[str, str] = {
    "SYSTEM NAME": "_name_tmp",
    "SCHOOL NAME": "_drop",
    "RESA": "_drop",
    "RESANAME_RPT": "_drop",
}

# =============================================================================
# Gold schema
# =============================================================================

METRIC_COLUMNS: list[str] = [
    "num_tested",
    "avg_scale_score",
    "scale_score_std_dev",
    "pct_beginning_learner",
    "pct_developing_learner",
    "pct_proficient_learner",
    "pct_distinguished_learner",
    "pct_developing_learner_or_above",
    "pct_proficient_learner_or_above",
    "pct_below_grade_level_lexile",
    "pct_grade_level_or_above_lexile",
    "enrolled_tested_rate",
    "num_sgp_received",
    "sgp_median",
    "pct_sgp_low_growth",
    "pct_sgp_typical_growth",
    "pct_sgp_high_growth",
]

STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "detail_level",
    "grade_level",
    "subject",
    "assessment_type",
    *METRIC_COLUMNS,
]

# sgp_median is a percentile rank but Float64: even SGP populations yield
# half-integer medians (.5). scale scores / std dev keep natural scale.
TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "detail_level": pl.Utf8,
    "grade_level": pl.Utf8,
    "subject": pl.Utf8,
    "assessment_type": pl.Utf8,
    "num_tested": pl.Int64,
    "avg_scale_score": pl.Float64,
    "scale_score_std_dev": pl.Float64,
    "pct_beginning_learner": pl.Float64,
    "pct_developing_learner": pl.Float64,
    "pct_proficient_learner": pl.Float64,
    "pct_distinguished_learner": pl.Float64,
    "pct_developing_learner_or_above": pl.Float64,
    "pct_proficient_learner_or_above": pl.Float64,
    "pct_below_grade_level_lexile": pl.Float64,
    "pct_grade_level_or_above_lexile": pl.Float64,
    "enrolled_tested_rate": pl.Float64,
    "num_sgp_received": pl.Int64,
    "sgp_median": pl.Float64,
    "pct_sgp_low_growth": pl.Float64,
    "pct_sgp_typical_growth": pl.Float64,
    "pct_sgp_high_growth": pl.Float64,
}

# Percent columns divided by 100 to the gold 0-1 scale. Scores, counts and
# the SGP median percentile are excluded (natural scale preserved).
# enrolled_tested_rate is a 0-1 rate too (bronze ships 0-100) but lacks the
# pct_ prefix, so it is added explicitly.
_PCT_COLUMNS: set[str] = {c for c in METRIC_COLUMNS if c.startswith("pct_")} | {
    "enrolled_tested_rate"
}

# Snap floating-point residue around the [0, 1] boundaries (bronze stores
# spreadsheet sums like `a + b - 100` as e.g. -3.55e-15). Larger deviations
# still surface as real out-of-range values via the contract range checks.
_PCT_CLAMP_TOLERANCE = 1e-9

# Footnote / legend row prefixes (matched with str.starts_with against every
# string column of the wide frame) and the Lexile-legend body marker
# (matched with contains). Observed across the 30-file scan: the reading
# status footnote ("^To achieve…" / "*To achieve…"), the 2021 state COVID
# notes, and the 2018-2021 state Lexile legend ("Grade" header row +
# "Lexile < 520L" body rows, whose first column otherwise looks like a
# grade number). A full scan verified no real district/school name starts
# with any of these prefixes.
_FOOTNOTE_PREFIXES: tuple[str, ...] = (
    "^",
    "*",
    "Note:",
    "For more information",
    "https://",
    "Grade",
    "Below",
    "Lexile",
)
_LEXILE_LEGEND_MARKER = "Lexile <"

# 2015 bronze reuses System Code `799` for three distinct state schools;
# 2016+ bronze and the districts dimension key them with unique 7-digit
# codes. District-level rows dispatch on the (ALL CAPS) 2015 system name,
# school-level rows on the school code the entities already carry.
_STATE_SCHOOL_799_BY_NAME: dict[str, str] = {
    "ATLANTA AREA SCHOOLS": "7991893",
    "GA ACADEMY FOR BLIND": "7991894",
    "GA SCHOOL FOR DEAF": "7991895",
}
_STATE_SCHOOL_799_BY_SCHOOL_CODE: dict[str, str] = {
    "1893": "7991893",
    "1894": "7991894",
    "1895": "7991895",
}
_STATE_SCHOOL_799_REASON = (
    "2015 shared state-school district_code 799 remapped to the unique "
    "7-digit codes (7991893/7991894/7991895) used by 2016+ bronze and the "
    "districts dimension"
)

# Metric-family folds: (child interim subject, parent subject, columns
# copied onto the parent row). The child's num_tested (and 2021
# enrolled_tested_rate) are intentionally NOT folded — the parent row keeps
# its own counts (see module docstring).
_METRIC_FAMILY_FOLDS: list[tuple[str, str, list[str]]] = [
    (
        "reading_status",
        "english_language_arts",
        ["pct_below_grade_level_lexile", "pct_grade_level_or_above_lexile"],
    ),
    (
        "sgp_english_language_arts",
        "english_language_arts",
        [
            "num_sgp_received",
            "sgp_median",
            "pct_sgp_low_growth",
            "pct_sgp_typical_growth",
            "pct_sgp_high_growth",
        ],
    ),
    (
        "sgp_mathematics",
        "mathematics",
        [
            "num_sgp_received",
            "sgp_median",
            "pct_sgp_low_growth",
            "pct_sgp_typical_growth",
            "pct_sgp_high_growth",
        ],
    ),
]

# Interim child label → final gold subject (for the manifest ledger).
_FOLD_PARENT: dict[str, str] = {
    child: parent for child, parent, _ in _METRIC_FAMILY_FOLDS
}

# Sentinel for null-aware fold joins: district/school codes are NULL at
# aggregate detail levels and polars equi-joins treat null != null. Used
# only on throwaway join-key copies — never lands in gold.
_JOIN_NULL_SENTINEL = "__NULL__"
_FOLD_JOIN_KEYS = [
    "year",
    "detail_level",
    "district_code",
    "school_code",
    "grade_level",
    "assessment_type",
]
_NULLABLE_JOIN_KEYS = ("district_code", "school_code")


@dataclass
class CategoricalLedgers:
    """Raw-label → gold-value ledgers accumulated across files for the manifest."""

    subject: dict[str, str] = field(default_factory=dict)
    assessment_type: dict[str, str] = field(default_factory=dict)
    grade_level: dict[str, str] = field(default_factory=dict)


# =============================================================================
# Filename / sheet parsing
# =============================================================================


def _parse_filename(filename: str) -> tuple[int, str]:
    """Extract (year, detail_level) from a bronze filename.

    "Spring YYYY" labels the school year ENDING in calendar year YYYY
    (bronze-data-structure.md §1), so the filename year is the data year.
    Detail level comes from the School / System / State token present in
    every filename.
    """
    match = re.search(r"Spring[-_ ]?(\d{4})", filename, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"Cannot parse Spring year from filename: {filename!r}")
    year = int(match.group(1))

    lower = filename.lower()
    if "school" in lower:
        detail = "school"
    elif "system" in lower:
        detail = "district"
    elif "state" in lower:
        detail = "state"
    else:
        raise ValueError(f"Cannot parse detail level from filename: {filename!r}")
    return year, detail


def _parse_grade_token(name: str) -> int | None:
    """Extract a grade 3-8 from a sheet name or zip member basename.

    Handles "State - Grade 3" / "School - Grade 8" (2022+ sheets),
    "Spring 2018 EOG - System Level - Grade 6.xlsx" (2017-2021 members),
    and "Gr3_System.xls" (2015-2016 members).
    """
    match = re.search(r"Grade[-_ ]?(\d)", name, flags=re.IGNORECASE)
    if not match:
        match = re.search(r"Gr(\d)", name)
    if match:
        grade = int(match.group(1))
        if 3 <= grade <= 8:
            return grade
    return None


# =============================================================================
# Header canonicalization
# =============================================================================


def _is_blank_header(value: object) -> bool:
    """True for None/NaN/pandas 'Unnamed: N_level_M' placeholder labels."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return True
    return str(value).startswith("Unnamed:")


def _canonical_super(raw: object) -> str:
    """Canonicalize a super-header for SUBJECT_BLOCK_MAP / identifier lookup.

    Strips the Reading Status footnote daggers (* / ^ — "Reading Status*"
    and "Reading Status^" are the same block), collapses whitespace runs
    (incl. the embedded newline in "School \\nCode"), and uppercases.
    """
    if _is_blank_header(raw):
        return ""
    s = str(raw).replace("*", "").replace("^", "")
    return " ".join(s.split()).strip().upper()


def _canonical_metric(raw: object) -> str:
    """Canonicalize a metric sub-header for METRIC_NAME_MAP lookup.

    Strips the per-grade Lexile threshold parenthetical ("% Below Grade
    Level (Lexile < 520L)" → "% BELOW GRADE LEVEL"), pandas' ".N" duplicate
    suffix (merged-cell artifacts), and collapses whitespace/newlines.
    """
    if _is_blank_header(raw):
        return ""
    s = str(raw)
    s = re.sub(r"\(Lexile[^)]*\)", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\.\d+$", "", s)
    return " ".join(s.split()).strip().upper()


@dataclass
class _SheetColumn:
    """One classified column of a two-row-header sheet."""

    pandas_col: object  # the original pandas column label (tuple)
    dest: str | None = None  # flat identifier destination, if an id column
    super_raw: str = ""  # display form of the super-header
    super_canon: str = ""
    metric_canon: str = ""


def _classify_columns(pdf: pd.DataFrame, context: str) -> list[_SheetColumn]:
    """Classify every sheet column as identifier or (subject, metric) block.

    pandas forward-fills merged header cells itself (verified: the ELA
    parent spans its block; the 2021 blank sub-header arrives as "Number
    Tested.1"), so only defensive parent back-fill is applied for genuinely
    empty parents. Raises on any unknown super-header or metric — silent
    drops on unknown headers are the most common bronze-to-gold data-loss
    bug.
    """
    cols: list[_SheetColumn] = []
    last_super_raw: object = None
    for col in pdf.columns:
        parent = col[0] if isinstance(col, tuple) else col
        sub = col[1] if isinstance(col, tuple) and len(col) > 1 else None
        # Defensive: pandas marks an unmerged blank parent "Unnamed:
        # N_level_0" — inherit the preceding real super-header.
        if _is_blank_header(parent) and last_super_raw is not None:
            parent = last_super_raw
        elif not _is_blank_header(parent):
            last_super_raw = parent

        super_canon = _canonical_super(parent)
        sub_canon_id = _canonical_super(sub)

        # Identifier columns: the sub-header's classification wins when it
        # is itself an identifier (merged "System Code"/"System Name").
        if sub_canon_id in _IDENTIFIER_CHILD_OVERRIDES:
            cols.append(
                _SheetColumn(col, dest=_IDENTIFIER_CHILD_OVERRIDES[sub_canon_id])
            )
            continue
        if super_canon in _IDENTIFIER_MAP:
            cols.append(_SheetColumn(col, dest=_IDENTIFIER_MAP[super_canon]))
            continue

        metric_canon = _canonical_metric(sub)
        if super_canon not in SUBJECT_BLOCK_MAP:
            raise ValueError(
                f"{context}: unknown super-header {parent!r} (canon "
                f"{super_canon!r}). Extend SUBJECT_BLOCK_MAP."
            )
        if metric_canon not in METRIC_NAME_MAP:
            raise ValueError(
                f"{context}: unknown metric sub-header {sub!r} (canon "
                f"{metric_canon!r}) under {parent!r}. Extend METRIC_NAME_MAP."
            )
        display = " ".join(str(parent).split()).strip()
        cols.append(
            _SheetColumn(
                col,
                super_raw=display,
                super_canon=super_canon,
                metric_canon=metric_canon,
            )
        )
    return cols


def _repair_missing_pct_enrolled(cols: list[_SheetColumn], context: str) -> int:
    """Relabel the 2021 grade-8 System merged-cell artifact (see docstring).

    In a sheet where at least one block carries PERCENT OF ENROLLED
    STUDENTS TESTED, a block that lacks it but carries a duplicated metric
    sub-header (pandas ".N" forward-fill residue of a blank cell) has that
    duplicate relabelled to the missing participation metric. Verified to
    fire exactly once across all 30 bronze files (Spring 2021 System
    Grade 8, ELA-EOG block, values 89-100 confirm participation rates).
    """
    pct_key = "PERCENT OF ENROLLED STUDENTS TESTED"
    by_block: dict[str, list[_SheetColumn]] = {}
    for c in cols:
        if c.dest is None:
            by_block.setdefault(c.super_canon, []).append(c)
    if not any(c.metric_canon == pct_key for b in by_block.values() for c in b):
        return 0

    repairs = 0
    for block_key, block_cols in by_block.items():
        metrics = [c.metric_canon for c in block_cols]
        if pct_key in metrics:
            continue
        seen: set[str] = set()
        for c in block_cols:
            if c.metric_canon in seen:
                logger.warning(
                    f"{context}: relabelling duplicate {c.metric_canon!r} in "
                    f"block {block_key!r} to {pct_key!r} (blank sub-header "
                    f"merged-cell artifact)"
                )
                c.metric_canon = pct_key
                repairs += 1
                break
            seen.add(c.metric_canon)
    return repairs


# =============================================================================
# Frame-level helpers
# =============================================================================


def _filter_footnote_rows(df: pl.DataFrame) -> tuple[pl.DataFrame, int]:
    """Drop footnote / Lexile-legend rows from a wide string frame.

    A row is dropped when ANY string column starts with a footnote prefix
    or contains the Lexile-legend body marker ("Lexile < 520L" …). Applied
    to the wide frame BEFORE unpivot so legend text in the Grade / code
    columns cannot masquerade as data.
    """
    str_cols = [c for c in df.columns if df.schema[c] == pl.Utf8]
    if not str_cols or df.height == 0:
        return df, 0
    pred = None
    for c in str_cols:
        stripped = pl.col(c).str.strip_chars()
        p = stripped.str.contains(_LEXILE_LEGEND_MARKER, literal=True).fill_null(False)
        for prefix in _FOOTNOTE_PREFIXES:
            p = p | stripped.str.starts_with(prefix).fill_null(False)
        pred = p if pred is None else pred | p
    filtered = df.filter(~pred)
    return filtered, df.height - filtered.height


def _format_ids(df: pl.DataFrame) -> pl.DataFrame:
    """Zero-pad district_code (3) / school_code (4) where present.

    Strips the trailing ".0" float-cast residue from the xls eras and the
    embedded hyphen in 2015 system-file charter campus codes ("782-0110" →
    "7820110" — the same 7-digit form 2016+ files publish directly). zfill
    never truncates, so 7-digit codes survive.
    """
    exprs = []
    if "district_code" in df.columns:
        exprs.append(
            pl.col("district_code")
            .cast(pl.Utf8, strict=False)
            .str.strip_chars()
            .str.replace(r"\.0$", "")
            .str.replace_all("-", "")
            .str.zfill(3)
            .alias("district_code")
        )
    if "school_code" in df.columns:
        exprs.append(
            pl.col("school_code")
            .cast(pl.Utf8, strict=False)
            .str.strip_chars()
            .str.replace(r"\.0$", "")
            .str.zfill(4)
            .alias("school_code")
        )
    return df.with_columns(exprs) if exprs else df


def _remap_2015_state_school_codes(
    df: pl.DataFrame, year: int, detail_level: str, manifest: TransformManifest
) -> pl.DataFrame:
    """Remap 2015 district_code='799' rows to their unique 7-digit codes.

    See _STATE_SCHOOL_799_BY_NAME. District-level rows dispatch on the
    temporary system-name column; school-level rows on the school code.
    Ledgered as manifest reclassified events. Drops `_name_tmp`
    unconditionally so it never leaves the reader.
    """
    if year == 2015 and "district_code" in df.columns:
        if detail_level == "district" and "_name_tmp" in df.columns:
            eligible = (pl.col("district_code") == "799") & pl.col(
                "_name_tmp"
            ).str.strip_chars().is_in(list(_STATE_SCHOOL_799_BY_NAME))
            n = int(df.select(eligible.sum()).item())
            if n:
                df = df.with_columns(
                    pl.when(eligible)
                    .then(
                        pl.col("_name_tmp")
                        .str.strip_chars()
                        .replace_strict(
                            _STATE_SCHOOL_799_BY_NAME,
                            default=pl.col("district_code"),
                        )
                    )
                    .otherwise(pl.col("district_code"))
                    .alias("district_code")
                )
                manifest.record_reclassified(year, n, _STATE_SCHOOL_799_REASON)
                logger.info(f"  Remapped {n} district-level 799 state-school row(s)")
        elif detail_level == "school" and "school_code" in df.columns:
            eligible = (pl.col("district_code") == "799") & pl.col("school_code").is_in(
                list(_STATE_SCHOOL_799_BY_SCHOOL_CODE)
            )
            n = int(df.select(eligible.sum()).item())
            if n:
                df = df.with_columns(
                    pl.when(eligible)
                    .then(
                        pl.col("school_code").replace_strict(
                            _STATE_SCHOOL_799_BY_SCHOOL_CODE,
                            default=pl.col("district_code"),
                        )
                    )
                    .otherwise(pl.col("district_code"))
                    .alias("district_code")
                )
                manifest.record_reclassified(year, n, _STATE_SCHOOL_799_REASON)
                logger.info(f"  Remapped {n} school-level 799 state-school row(s)")

    if "_name_tmp" in df.columns:
        df = df.drop("_name_tmp")
    return df


def _cast_and_scale_metrics(df: pl.DataFrame) -> pl.DataFrame:
    """Cast metric columns to TARGET_TYPES; scale percent columns to 0-1.

    ``strict=False`` so suppression markers ('--') land as NULL. Percent
    columns divide by 100 exactly once (here, at the reader tail — block
    level casts to Float64 without scaling), then snap residue within
    _PCT_CLAMP_TOLERANCE of the [0, 1] boundaries.
    """
    exprs = []
    for col in METRIC_COLUMNS:
        if col not in df.columns:
            continue
        if col in _PCT_COLUMNS:
            scaled = pl.col(col).cast(pl.Float64, strict=False) / 100.0
            exprs.append(
                pl.when((scaled < 0) & (scaled > -_PCT_CLAMP_TOLERANCE))
                .then(0.0)
                .when((scaled > 1) & (scaled < 1 + _PCT_CLAMP_TOLERANCE))
                .then(1.0)
                .otherwise(scaled)
                .alias(col)
            )
        else:
            exprs.append(pl.col(col).cast(TARGET_TYPES[col], strict=False).alias(col))
    return df.with_columns(exprs) if exprs else df


def _drop_all_null_metric_rows(df: pl.DataFrame) -> tuple[pl.DataFrame, int]:
    """Drop rows whose every present metric column is NULL (post-cast).

    State readers only: a state aggregate cannot be small-N suppressed, so
    an all-'--' state row is a non-administered placeholder (e.g. the EOC
    columns for grades 3-5 in the 2016-2021 state files), not data.
    """
    present = [c for c in METRIC_COLUMNS if c in df.columns]
    if not present or df.height == 0:
        return df, 0
    keep = pl.any_horizontal([pl.col(c).is_not_null() for c in present])
    filtered = df.filter(keep)
    return filtered, df.height - filtered.height


# =============================================================================
# Sheet-level unpivot
# =============================================================================


def _unpivot_blocks(
    pdf: pd.DataFrame,
    *,
    context: str,
    ledgers: CategoricalLedgers,
) -> tuple[pl.DataFrame, int]:
    """Unpivot a classified two-row-header sheet into long subject rows.

    Returns (long_frame, n_footnote_rows). Steps:

    1. Drop all-NaN columns, classify every column (raises on unknowns),
       apply the pct_enrolled sub-header repair.
    2. Flatten to unique string column names and convert to polars (all
       Utf8 — reads use dtype=str).
    3. Filter footnote/legend rows on the wide frame.
    4. Per (subject, assessment_type) block: keep id columns + the block's
       metrics renamed to gold names (first occurrence wins on residual
       duplicates), drop rows whose every metric cell is NaN — a truly
       empty cell means the block does not exist for that row, while '--'
       suppression strings survive to become NULL at the cast — then cast
       metrics to Float64 (unscaled; the /100 happens once at the reader
       tail).
    5. Harmonize + concat the block frames.
    """
    non_empty = [c for c in pdf.columns if not pdf[c].isna().all()]
    pdf = pdf.loc[:, non_empty]
    cols = _classify_columns(pdf, context)
    _repair_missing_pct_enrolled(cols, context)

    # Flatten to unique string names: identifier columns take their dest
    # (dropping "_drop" ones), block columns take positional placeholders.
    keep_names: list[str] = []
    keep_idx: list[int] = []
    block_cols: list[tuple[str, _SheetColumn]] = []
    seen_dests: set[str] = set()
    for i, c in enumerate(cols):
        if c.dest == "_drop":
            continue
        if c.dest is not None:
            # Defensive: a repeated identifier (two columns mapping to the
            # same dest) keeps the first occurrence only.
            if c.dest in seen_dests:
                logger.warning(f"{context}: duplicate identifier column {c.dest!r}")
                continue
            seen_dests.add(c.dest)
            keep_names.append(c.dest)
            keep_idx.append(i)
        else:
            name = f"_block_{i}"
            keep_names.append(name)
            keep_idx.append(i)
            block_cols.append((name, c))

    flat = pdf.iloc[:, keep_idx].copy()
    flat.columns = keep_names
    df = pl.from_pandas(flat)
    if df.width and df.height:
        df = df.filter(~pl.all_horizontal(pl.all().is_null()))
    df, n_footnotes = _filter_footnote_rows(df)
    # Rechunk after the row filters: filtering interleaved rows fragments
    # the frame into single-row chunks, and polars' divide-by-literal kernel
    # is ULP-different on 1-row chunks (true IEEE division) vs multi-row
    # chunks (reciprocal multiply). Compacting here pins the downstream /100
    # scaling to one deterministic chunk layout — one chunk per sheet — so
    # re-runs (and the v1 parity baseline, whose reader compacted the frame
    # via a pandas round trip at this same point) reproduce bit-identical
    # floats.
    df = df.rechunk()

    id_cols = [c for c in keep_names if not c.startswith("_block_")]

    # Group block columns by (subject, assessment_type).
    groups: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for name, c in block_cols:
        subject, assessment = SUBJECT_BLOCK_MAP[c.super_canon]
        gold_metric = METRIC_NAME_MAP[c.metric_canon]
        groups.setdefault((subject, assessment), []).append((name, gold_metric))
        ledgers.subject[c.super_raw] = subject
        ledgers.assessment_type[c.super_raw] = assessment

    frames: list[pl.DataFrame] = []
    for (subject, assessment), members in groups.items():
        rename: dict[str, str] = {}
        for name, gold_metric in members:
            if gold_metric in rename.values():
                # Residual duplicate metric within one block (post-repair).
                # First occurrence wins; deterministic and loud.
                logger.warning(
                    f"{context}: dropping duplicate metric {gold_metric!r} "
                    f"in block {subject!r}/{assessment!r}"
                )
                continue
            rename[name] = gold_metric
        block = df.select(id_cols + list(rename)).rename(rename)
        metric_names = list(rename.values())
        # NaN block cells = block absent for this row (drop); '--'
        # suppression strings are non-null and survive.
        block = block.filter(
            pl.any_horizontal([pl.col(m).is_not_null() for m in metric_names])
        )
        block = block.with_columns(
            [pl.col(m).cast(pl.Float64, strict=False).alias(m) for m in metric_names]
        )
        block = block.with_columns(
            pl.lit(subject).alias("subject"),
            pl.lit(assessment).alias("assessment_type"),
        )
        frames.append(block)

    if not frames:
        raise ValueError(f"{context}: no subject blocks found")
    frames = harmonize_columns(frames, STANDARD_COLUMNS, TARGET_TYPES)
    return pl.concat(frames, how="vertical"), n_footnotes


def _finalize_member_frame(
    df: pl.DataFrame,
    *,
    year: int,
    detail_level: str,
    grade: int | None,
    manifest: TransformManifest,
    ledgers: CategoricalLedgers,
) -> pl.DataFrame:
    """Apply the shared reader tail to one member/sheet long frame.

    Attaches grade_level (zero-padded), guarantees geography columns,
    formats IDs, applies the 2015 state-school 799 remap, casts + scales
    metrics, and annotates year / detail_level.
    """
    if grade is not None:
        df = df.with_columns(pl.lit(f"{grade:02d}").alias("grade_level"))
        ledgers.grade_level[str(grade)] = f"{grade:02d}"
    for col in ("district_code", "school_code"):
        if col not in df.columns:
            df = df.with_columns(pl.lit(None).cast(pl.Utf8).alias(col))
    df = _format_ids(df)
    df = _remap_2015_state_school_codes(df, year, detail_level, manifest)
    df = _cast_and_scale_metrics(df)
    return df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.lit(detail_level).alias("detail_level"),
    )


# =============================================================================
# Readers (one per structural file shape)
# =============================================================================


def _read_state_all_grades_single_sheet(
    path: Path,
    year: int,
    manifest: TransformManifest,
    ledgers: CategoricalLedgers,
) -> tuple[pl.DataFrame, int]:
    """Read a 2015-2021 state file: one sheet, all six grades as rows.

    The Grade column ('3'..'8') becomes grade_level. 2018-2021 files stack
    a Lexile legend + footnotes below the data (filtered + ledgered); the
    grade 3-8 integer filter is a second guard against legend residue.
    Post-cast all-NULL-metric rows (the all-'--' EOC placeholder columns
    for elementary grades) are dropped — state aggregates cannot be small-N
    suppressed.
    """
    engine = "xlrd" if path.suffix.lower() == ".xls" else None
    pdf = pd.read_excel(path, sheet_name=0, header=[1, 2], dtype=str, engine=engine)
    df, n_footnotes = _unpivot_blocks(pdf, context=path.name, ledgers=ledgers)

    if "_grade_raw" not in df.columns:
        raise ValueError(f"{path.name}: state file lacks a 'Grade' column")
    raw_grades = df["_grade_raw"].drop_nulls().unique().to_list()
    df = df.with_columns(
        pl.col("_grade_raw")
        .cast(pl.Utf8, strict=False)
        .str.replace(r"\.0$", "")
        .str.strip_chars()
        .cast(pl.Int32, strict=False)
        .alias("_grade_int")
    ).drop("_grade_raw")
    before = df.height
    df = df.filter(pl.col("_grade_int").is_between(3, 8, closed="both"))
    dropped = before - df.height
    if dropped:
        logger.info(f"  Dropped {dropped} row(s) with non-grade-3-8 Grade values")
    df = df.with_columns(
        pl.col("_grade_int").cast(pl.Utf8).str.zfill(2).alias("grade_level")
    ).drop("_grade_int")
    for raw in raw_grades:
        token = str(raw).strip().removesuffix(".0")
        if token.isdigit() and 3 <= int(token) <= 8:
            ledgers.grade_level[token] = f"{int(token):02d}"

    df = _finalize_member_frame(
        df,
        year=year,
        detail_level="state",
        grade=None,
        manifest=manifest,
        ledgers=ledgers,
    )
    df, n_placeholder = _drop_all_null_metric_rows(df)
    if n_placeholder:
        manifest.record_filtered(
            year, n_placeholder, "state_non_administered_placeholder_row"
        )
        logger.info(f"  Dropped {n_placeholder} all-null state placeholder row(s)")
    return df, n_footnotes


def _read_zip_per_grade(
    path: Path,
    year: int,
    detail_level: str,
    manifest: TransformManifest,
    ledgers: CategoricalLedgers,
) -> tuple[pl.DataFrame, int]:
    """Read a 2015-2021 system/school zip of six per-grade workbooks.

    Grade comes from the member basename (2015 zips double-nest members
    under a redundant directory — basename only). 2015 members are legacy
    .xls (xlrd engine). Fully-suppressed (all-'--') rows are PRESERVED at
    these detail levels — small-N suppression of a real observation.
    """
    frames: list[pl.DataFrame] = []
    n_footnotes = 0
    with zipfile.ZipFile(path) as zf:
        for member in zf.namelist():
            basename = member.rsplit("/", 1)[-1]
            if not basename or not basename.lower().endswith((".xls", ".xlsx")):
                continue
            grade = _parse_grade_token(basename)
            if grade is None:
                raise ValueError(f"{path.name}:{member}: cannot parse grade")
            engine = "xlrd" if basename.lower().endswith(".xls") else "openpyxl"
            pdf = pd.read_excel(
                io.BytesIO(zf.read(member)),
                sheet_name=0,
                header=[1, 2],
                dtype=str,
                engine=engine,
            )
            df, n = _unpivot_blocks(
                pdf, context=f"{path.name}:{basename}", ledgers=ledgers
            )
            n_footnotes += n
            if "_grade_raw" in df.columns:
                # Defensive: per-grade members carry no Grade column today.
                df = df.drop("_grade_raw")
            frames.append(
                _finalize_member_frame(
                    df,
                    year=year,
                    detail_level=detail_level,
                    grade=grade,
                    manifest=manifest,
                    ledgers=ledgers,
                )
            )
    if not frames:
        raise ValueError(f"{path.name}: no member workbooks in zip")
    frames = harmonize_columns(frames, STANDARD_COLUMNS, TARGET_TYPES)
    return pl.concat(frames, how="vertical"), n_footnotes


def _read_consolidated_multi_sheet(
    path: Path,
    year: int,
    detail_level: str,
    manifest: TransformManifest,
    ledgers: CategoricalLedgers,
) -> tuple[pl.DataFrame, int]:
    """Read a 2022-2025 consolidated workbook: six per-grade sheets.

    Grade comes from the sheet name; the redundant in-sheet Grade column on
    state sheets is dropped. State sheets drop post-cast all-NULL rows
    (non-administered placeholders); system/school sheets preserve them
    (small-N suppression).
    """
    xl = pd.ExcelFile(path)
    frames: list[pl.DataFrame] = []
    n_footnotes = 0
    for sheet_name in xl.sheet_names:
        grade = _parse_grade_token(sheet_name)
        if grade is None:
            raise ValueError(f"{path.name}:{sheet_name}: cannot parse grade")
        pdf = xl.parse(sheet_name=sheet_name, header=[1, 2], dtype=str)
        df, n = _unpivot_blocks(
            pdf, context=f"{path.name}:{sheet_name}", ledgers=ledgers
        )
        n_footnotes += n
        if "_grade_raw" in df.columns:
            # Grade is taken from the sheet name; the in-sheet column on
            # state sheets is redundant.
            df = df.drop("_grade_raw")
        df = _finalize_member_frame(
            df,
            year=year,
            detail_level=detail_level,
            grade=grade,
            manifest=manifest,
            ledgers=ledgers,
        )
        if detail_level == "state":
            df, n_placeholder = _drop_all_null_metric_rows(df)
            if n_placeholder:
                manifest.record_filtered(
                    year, n_placeholder, "state_non_administered_placeholder_row"
                )
        frames.append(df)
    if not frames:
        raise ValueError(f"{path.name}: no sheets read")
    frames = harmonize_columns(frames, STANDARD_COLUMNS, TARGET_TYPES)
    return pl.concat(frames, how="vertical"), n_footnotes


# =============================================================================
# File-level dispatch
# =============================================================================


def _detect_file_shape(path: Path) -> str:
    """Structural shape detection (no filename year tags).

    - zip → per-grade member workbooks (2015-2021 system/school).
    - direct workbook with ONE sheet → state all-grades-as-rows file
      (only 2015-2021 state files have a single sheet).
    - direct workbook with multiple sheets → consolidated per-grade-sheet
      workbook (2022+, any detail level).
    """
    if path.suffix.lower() == ".zip":
        return "zip_per_grade"
    engine = "xlrd" if path.suffix.lower() == ".xls" else None
    n_sheets = len(pd.ExcelFile(path, engine=engine).sheet_names)
    return (
        "state_all_grades_single_sheet" if n_sheets == 1 else "consolidated_multi_sheet"
    )


def transform_file(
    path: Path, manifest: TransformManifest, ledgers: CategoricalLedgers
) -> pl.DataFrame | None:
    """Transform one bronze file into a long frame; record manifest entries.

    Whole-sheet Excel reads cannot drop records at parse time (read-loss
    raw == parsed by construction), so no read-loss events are recorded.
    Footnote/legend rows are ledgered via record_filtered.
    """
    year, detail_level = _parse_filename(path.name)
    shape = _detect_file_shape(path)
    logger.info(f"{path.name}: year={year} detail={detail_level} shape={shape}")

    if shape == "state_all_grades_single_sheet":
        if detail_level != "state":
            raise ValueError(f"{path.name}: single-sheet workbook is not state-level")
        df, n_footnotes = _read_state_all_grades_single_sheet(
            path, year, manifest, ledgers
        )
    elif shape == "zip_per_grade":
        df, n_footnotes = _read_zip_per_grade(
            path, year, detail_level, manifest, ledgers
        )
    else:
        df, n_footnotes = _read_consolidated_multi_sheet(
            path, year, detail_level, manifest, ledgers
        )

    manifest.record_file(path, year, shape, df.height, df.columns)
    manifest.record_bronze(year, df.height)
    if n_footnotes:
        manifest.record_filtered(year, n_footnotes, "footnote_or_legend_row")
        logger.info(f"  Dropped {n_footnotes} footnote/legend row(s)")

    if df.height == 0:
        logger.warning(f"{path.name}: no data rows after transform")
        return None
    return df


# =============================================================================
# Combined-frame steps
# =============================================================================


def _drop_all_null_placeholder_groups(
    combined: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Drop (year, detail, grade, subject, assessment) groups with no data.

    A group in which EVERY row has all metric columns NULL is a
    non-administered placeholder block (e.g. 2016 grade-6 system
    Science-EOC: the columns exist but every cell is '--'), not a set of
    suppressed observations — genuine small-N suppression leaves at least
    one unsuppressed entity in the group. Ledgered per year.
    """
    group_keys = ["year", "detail_level", "grade_level", "subject", "assessment_type"]
    has_metric = pl.any_horizontal(
        [pl.col(c).is_not_null() for c in METRIC_COLUMNS]
    ).alias("_row_has_metric")
    combined = combined.with_columns(has_metric).with_columns(
        pl.col("_row_has_metric").any().over(group_keys).alias("_group_has_metric")
    )
    dropped = combined.filter(~pl.col("_group_has_metric"))
    if dropped.height:
        per_year = dropped.group_by("year").agg(pl.len().alias("n")).sort("year")
        for yr, n in per_year.iter_rows():
            manifest.record_filtered(
                int(yr), int(n), "non_administered_placeholder_block"
            )
        sample = dropped.select(group_keys).unique().sort(group_keys).head(8).rows()
        logger.info(
            f"Dropped {dropped.height:,} rows from all-null placeholder "
            f"blocks (sample groups: {sample})"
        )
    return combined.filter(pl.col("_group_has_metric")).drop(
        ["_row_has_metric", "_group_has_metric"]
    )


def _fold_metric_family_rows(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Fold reading_status / sgp_* rows onto their parent academic rows.

    For each fold (child, parent, columns): child rows are matched to the
    parent row sharing (year, detail_level, district_code, school_code,
    grade_level, assessment_type) — NULL geography matched via a sentinel —
    and their metric columns are copied onto the parent (the parent's own
    columns win, but they are structurally NULL for these metric-family
    columns). Matched child rows are then dropped (ledgered per year);
    orphan child rows with no parent are relabelled to the parent subject
    in place (ledgered as reclassified) so their metrics still surface
    under the proper academic subject.
    """
    jk = [f"_jk_{c}" for c in _FOLD_JOIN_KEYS]

    for child_label, parent_label, fold_cols in _METRIC_FAMILY_FOLDS:
        if df.filter(pl.col("subject") == child_label).height == 0:
            continue
        df = df.with_columns(
            [
                (
                    pl.col(c).fill_null(_JOIN_NULL_SENTINEL)
                    if c in _NULLABLE_JOIN_KEYS
                    else pl.col(c)
                ).alias(f"_jk_{c}")
                for c in _FOLD_JOIN_KEYS
            ]
        )
        child = df.filter(pl.col("subject") == child_label)
        rest = df.filter(pl.col("subject") != child_label)
        parent_keys = (
            rest.filter(pl.col("subject") == parent_label)
            .select(jk)
            .unique()
            .with_columns(pl.lit(True).alias("_has_parent"))
        )
        child = child.join(parent_keys, on=jk, how="left")
        matched = child.filter(pl.col("_has_parent"))
        orphans = child.filter(pl.col("_has_parent").is_null()).drop("_has_parent")

        # Copy the child metric columns onto the matching parent rows.
        fold_src = matched.select(
            jk + [pl.col(c).alias(f"_fold_{c}") for c in fold_cols]
        )
        parent_part = rest.filter(pl.col("subject") == parent_label).join(
            fold_src, on=jk, how="left"
        )
        parent_part = parent_part.with_columns(
            [pl.coalesce([pl.col(c), pl.col(f"_fold_{c}")]).alias(c) for c in fold_cols]
        ).drop([f"_fold_{c}" for c in fold_cols])
        others = rest.filter(pl.col("subject") != parent_label)

        # Orphans survive with the subject relabelled to the parent.
        if orphans.height:
            orphans = orphans.with_columns(pl.lit(parent_label).alias("subject"))
            per_year = orphans.group_by("year").agg(pl.len().alias("n")).sort("year")
            for yr, n in per_year.iter_rows():
                manifest.record_reclassified(
                    int(yr),
                    int(n),
                    f"orphan {child_label} row relabelled to {parent_label} "
                    f"(no parent row in the same natural-key cell)",
                )
            logger.info(
                f"  {child_label}: {orphans.height} orphan row(s) relabelled "
                f"to {parent_label}"
            )

        per_year = matched.group_by("year").agg(pl.len().alias("n")).sort("year")
        for yr, n in per_year.iter_rows():
            manifest.record_filtered(
                int(yr),
                int(n),
                f"{child_label}_rows_folded_into_{parent_label}",
            )
        logger.info(
            f"Folded {matched.height:,} {child_label} row(s) onto {parent_label} rows"
        )

        df = pl.concat(
            [parent_part, others, orphans.select(parent_part.columns)],
            how="vertical",
        ).drop(jk)

    return df


# =============================================================================
# Pipeline orchestration
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for georgia_milestones_end_of_grade."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)
    ledgers = CategoricalLedgers()
    frames: list[pl.DataFrame] = []

    for path in list_bronze_files(BRONZE_DIR, extensions=[".xls", ".xlsx", ".zip"]):
        df = transform_file(path, manifest, ledgers)
        if df is not None and df.height > 0:
            frames.append(df)

    if not frames:
        raise RuntimeError("No bronze data transformed — check bronze directory")

    # Eras carry different column subsets (no Reading Status before 2018,
    # std dev only 2022+, enrolled_tested_rate only 2021, SGP only 2024+);
    # harmonize adds the missing columns as typed NULLs.
    frames = harmonize_columns(frames, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(frames, how="vertical")
    logger.info(f"Combined all frames: {combined.height:,} rows")

    # Drop non-administered placeholder blocks (whole all-null groups),
    # then fold the Reading Status / SGP metric families onto their parent
    # academic subject rows (interim labels never reach gold).
    combined = _drop_all_null_placeholder_groups(combined, manifest)
    combined = _fold_metric_family_rows(combined, manifest)

    # §10a backstop: the local maps already produce canonical values (and
    # raise on unmapped labels); the shared normalizers keep the vocabulary
    # aligned with the cross-topic registries even if the local maps drift.
    combined = combined.with_columns(
        normalize_grade_column("grade_level").alias("grade_level"),
        apply_subject_normalization("subject").alias("subject"),
    )

    # Charter SYSTEM → CAMPUS district codes on school-level rows (2015
    # school files key charter campuses under the umbrella codes 782/783;
    # 2016+ files already publish the 7-digit campus codes). Ledgered as
    # manifest reclassified events by the shared module. Runs before the
    # collision guard + dedup so any rewrite-induced duplicate key is
    # surfaced by the standard machinery.
    combined = promote_charter_system_to_campus_district(combined, manifest=manifest)

    # Guard BEFORE dedup: duplicate keys with DIVERGENT metrics mean an
    # alias/promotion/fold bug and must fail loudly. detail_level is part
    # of the key because district aggregates share (year, district, grade,
    # subject, assessment) with state rows once geography is NULLed.
    natural_keys = [
        "year",
        "detail_level",
        "district_code",
        "school_code",
        "grade_level",
        "subject",
        "assessment_type",
    ]
    assert_no_natural_key_collisions(combined, natural_keys, METRIC_COLUMNS)

    # Defensive dedup: each (year, detail_level) comes from exactly one
    # bronze file and keys are unique within files (the guard above would
    # have raised otherwise). sort_col="num_tested" prefers a row with a
    # reported count over a placeholder if a true duplicate ever appears.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=[
            "year",
            "district_code",
            "school_code",
            "grade_level",
            "subject",
            "assessment_type",
        ],
        district_keys=[
            "year",
            "district_code",
            "grade_level",
            "subject",
            "assessment_type",
        ],
        state_keys=["year", "grade_level", "subject", "assessment_type"],
        sort_col="num_tested",
    )

    # Shared geography-nulling rules (validator reads the same config).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    validate_output(combined, required_non_null=["year", "detail_level"])

    # Manifest stats on the FINAL frame, then export.
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(combined, GOLD_DIR, STANDARD_COLUMNS)

    # Categorical ledgers. The subject ledger maps every observed raw
    # super-header to its FINAL gold subject (metric-family blocks resolve
    # to their fold parent — the interim labels never reach gold).
    subject_map = {
        raw: _FOLD_PARENT.get(interim, interim)
        for raw, interim in sorted(ledgers.subject.items())
    }
    manifest.record_categorical(
        column="subject",
        map_dict=subject_map,
        bronze_series=pl.Series("subject_raw", list(subject_map)),
        gold_series=combined["subject"],
    )
    manifest.record_categorical(
        column="assessment_type",
        map_dict=dict(sorted(ledgers.assessment_type.items())),
        bronze_series=pl.Series("super_raw", sorted(ledgers.assessment_type)),
        gold_series=combined["assessment_type"],
    )
    manifest.record_categorical(
        column="grade_level",
        map_dict=dict(sorted(ledgers.grade_level.items())),
        bronze_series=pl.Series("grade_raw", sorted(ledgers.grade_level)),
        gold_series=combined["grade_level"],
    )
    manifest.write(GOLD_DIR)

    # Known legitimate NULL spikes (warnings only): scale_score_std_dev is
    # null pre-2022; Lexile metrics are null outside ELA rows / pre-2018;
    # enrolled_tested_rate is null outside 2021; SGP metrics are null
    # outside 2024+ ELA/Math grades 4-8.
    spike = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike.status == "warning":
        for detail in spike.details or []:
            logger.warning(f"NULL rate spike: {detail}")

    year_min = int(combined["year"].min())
    year_max = int(combined["year"].max())

    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Georgia Milestones End-of-Grade (EOG) assessment results for "
            "grades 3-8 — published annually (except 2020, cancelled due to "
            "COVID) at the state, district/system, and school level. The "
            "primary metrics are the count of students tested, the mean "
            "scale score, and the share of students at each of the four "
            "achievement levels (Beginning / Developing / Proficient / "
            "Distinguished Learner) plus the two cumulative shares. English "
            "Language Arts rows additionally carry Reading Status metrics "
            "(pct_below_grade_level_lexile / pct_grade_level_or_above_lexile)"
            " from 2018 onward, anchored to grade-specific Lexile thresholds "
            "(520L for grade 3, 740L for grade 4, 830L for grade 5, 925L for "
            "grade 6, 970L for grade 7, 1010L for grade 8). 2016-2021 grade "
            "6-8 rows split affected subjects into EOG / EOC / Combined "
            "variants to represent middle-schoolers taking end-of-course "
            "exams early (captured in the assessment_type column). 2022+ "
            "drops the EOC variants (moved to the "
            "georgia_milestones_end_of_course topic), adds a Standard "
            "Deviation metric per subject, and adds Physical Science for "
            "grade 8. 2024-2025 adds Student Growth Percentile (SGP) metrics "
            "— num_sgp_received, sgp_median, pct_sgp_low_growth, "
            "pct_sgp_typical_growth, pct_sgp_high_growth — reported on the "
            "parent ELA / Mathematics rows for grades 4-8."
        ),
        title="Georgia Milestones End-of-Grade (EOG) Results",
        summary=(
            "Georgia Milestones grades 3-8 test results by school, district, "
            "grade, and subject, 2015-2025."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "description": (
                    "Ending calendar year of the school year (e.g., 2025 = "
                    "school year 2024-2025). 2020 is absent — the COVID-19 "
                    "pandemic cancelled the administration."
                ),
                "nullable": False,
                "example": 2024,
            },
            {
                "name": "district_code",
                "type": "string",
                "description": (
                    "3-digit GOSA district/system code (FK to districts "
                    "dimension). 7-digit charter / state-school campus codes "
                    "are preserved in full; 2015 school-level rows published "
                    "under the bare charter SYSTEM codes 782/783 are promoted "
                    "to the 7-digit campus code (system + school code), and "
                    "the 2015 shared state-school code 799 is remapped to the "
                    "unique 7991893/7991894/7991895 codes used from 2016. "
                    "NULL for state-level rows."
                ),
                "nullable": True,
                "example": "601",
            },
            {
                "name": "school_code",
                "type": "string",
                "description": (
                    "4-digit GOSA school code (FK to schools dimension, "
                    "composite with district_code). NULL for district- and "
                    "state-level rows."
                ),
                "nullable": True,
                "example": "0177",
            },
            {
                "name": "grade_level",
                "type": "string",
                "description": (
                    "Grade level, zero-padded 2-char string ('03'..'08'). "
                    "Georgia Milestones EOG is administered only to grades "
                    "3-8. Same encoding as the other per-grade education "
                    "topics."
                ),
                "short_description": (
                    "Tested grade, 03 through 08 (Milestones EOG covers only "
                    "grades 3-8)."
                ),
                "nullable": False,
                "example": "05",
                "validValues": ["03", "04", "05", "06", "07", "08"],
            },
            {
                "name": "subject",
                "type": "string",
                "description": (
                    "Snake-case academic content area: english_language_arts,"
                    " mathematics, science, social_studies, physical_science "
                    "(grade 8 only, from 2022 — 8th-graders taking the "
                    "high-school Physical Science course early; bronze labels "
                    "it 'HS Physical Science'). Bronze ships Reading Status "
                    "and Student Growth Percentile (SGP) as parallel "
                    '"subject" blocks, but those are metric families '
                    "computed on the ELA / Mathematics test-taker population "
                    "— the transform folds their metric columns onto the "
                    "parent ELA / Mathematics row "
                    "(pct_below_grade_level_lexile, "
                    "pct_grade_level_or_above_lexile, num_sgp_received, "
                    "sgp_median, pct_sgp_*) and drops the parallel rows."
                ),
                "short_description": (
                    "The content area tested (english_language_arts, "
                    "mathematics, science, social_studies, physical_science)."
                ),
                "nullable": False,
                "example": "mathematics",
                "validValues": [
                    "english_language_arts",
                    "mathematics",
                    "science",
                    "social_studies",
                    "physical_science",
                ],
            },
            {
                "name": "assessment_type",
                "type": "string",
                "description": (
                    "Differentiates regular EOG from the middle-school EOG / "
                    "EOC / Combined triples that existed in 2016-2021 "
                    "(middle-schoolers taking End-of-Course exams early: "
                    "Mathematics 2016-2019, Science 2016-2021, English "
                    "Language Arts 2018-2019 — never Social Studies). 2015 "
                    "and 2022+ data is always `eog`. Filter assessment_type "
                    "= 'eog' for the canonical comparison-safe year-over-year"
                    " EOG-only time series."
                ),
                "short_description": (
                    "Marks regular EOG vs the 2016-2021 early end-of-course "
                    "variants; use eog for year-over-year comparisons."
                ),
                "nullable": False,
                "example": "eog",
                "validValues": ["eog", "eoc", "eog_and_eoc_combined"],
            },
            {
                "name": "num_tested",
                "unit": "count",
                "metric_component": "denominator",
                "type": "int64",
                "description": (
                    "Number of students who took the test. NULL when the "
                    "source suppresses the cell ('--') for small populations."
                ),
                "nullable": True,
                "example": 271,
            },
            {
                "name": "avg_scale_score",
                "unit": "score",
                "key_metric": True,
                "value_min": 140,
                "value_max": 830,
                "type": "float64",
                "description": (
                    "Mean scale score on the EOG scale. Georgia Milestones "
                    "EOG scale scores span 140-830 across grades/subjects "
                    "(per-grade min/max differ; the envelope runs from the "
                    "grade-6 ELA floor of 140 to the grade-3 ELA ceiling of "
                    "830, per the GaDOE EOG Score Interpretation Guide); the "
                    "contract enforces that range. NOT converted to 0-1 — "
                    "scale scores are preserved as-is per education "
                    "CLAUDE.md. Never published for eoc / "
                    "eog_and_eoc_combined rows (the bronze EOC blocks ship "
                    "no Mean Scale Score column)."
                ),
                "short_description": (
                    "Average end-of-grade scale score (140-830 scale); higher "
                    "means stronger performance."
                ),
                "nullable": True,
                "example": 502.8,
            },
            {
                "name": "scale_score_std_dev",
                "type": "float64",
                "description": (
                    "Standard deviation of the scale scores — a dispersion "
                    "measure, NOT a bounded score. Units are scale-score "
                    "points; the value is always >= 0. Exempt from unit/range "
                    "checks (it has no fixed upper bound). Published from "
                    "2022 onward; NULL for all earlier years."
                ),
                "nullable": True,
                "example": 64.0,
            },
            {
                "name": "pct_beginning_learner",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share of tested students at the Beginning Learner level "
                    "(0-1 decimal scale; bronze 0-100 divided by 100)."
                ),
                "nullable": True,
                "example": 0.369,
            },
            {
                "name": "pct_developing_learner",
                "unit": "proportion",
                "type": "float64",
                "description": "Share at Developing Learner (0-1 scale).",
                "nullable": True,
                "example": 0.302,
            },
            {
                "name": "pct_proficient_learner",
                "unit": "proportion",
                "type": "float64",
                "description": "Share at Proficient Learner (0-1 scale).",
                "nullable": True,
                "example": 0.233,
            },
            {
                "name": "pct_distinguished_learner",
                "unit": "proportion",
                "type": "float64",
                "description": "Share at Distinguished Learner (0-1 scale).",
                "nullable": True,
                "example": 0.095,
            },
            {
                "name": "pct_developing_learner_or_above",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share at Developing Learner or higher (= developing + "
                    "proficient + distinguished). Published by the source "
                    "and preserved verbatim rather than re-derived."
                ),
                "nullable": True,
                "example": 0.631,
            },
            {
                "name": "pct_proficient_learner_or_above",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share at Proficient Learner or higher (= proficient + "
                    "distinguished). Published by the source and preserved "
                    "verbatim."
                ),
                "nullable": True,
                "example": 0.328,
            },
            {
                "name": "pct_below_grade_level_lexile",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Reading Status: share of ELA test takers reading BELOW "
                    "the grade-specific Lexile threshold (2018 onward). "
                    "Populated only on english_language_arts rows. The "
                    "threshold is 520L / 740L / 830L / 925L / 970L / 1010L "
                    "for grades 3 / 4 / 5 / 6 / 7 / 8 — documented here "
                    "rather than encoded in the column name so the schema "
                    "stays grade-agnostic."
                ),
                "nullable": True,
                "example": 0.354,
            },
            {
                "name": "pct_grade_level_or_above_lexile",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Reading Status: share of ELA test takers reading at or "
                    "above the grade-specific Lexile threshold; complement "
                    "of pct_below_grade_level_lexile. Populated only on "
                    "english_language_arts rows (2018 onward)."
                ),
                "nullable": True,
                "example": 0.646,
            },
            {
                "name": "enrolled_tested_rate",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share of enrolled students who actually tested. "
                    "Published ONLY by the 2021 files (testing was optional "
                    "during COVID, so participation is essential context); "
                    "NULL for every other year. The 2021 grade-8 system file "
                    "leaves this sub-header blank in the ELA-EOG block (a "
                    "merged-cell artifact); the transform repairs the header "
                    "so the published participation rates are preserved."
                ),
                "nullable": True,
                "example": 0.793,
            },
            {
                "name": "num_sgp_received",
                "unit": "count",
                "type": "int64",
                "description": (
                    "Number of students with a Student Growth Percentile. "
                    "Populated only on english_language_arts / mathematics "
                    "rows at grades 4-8 from 2024 onward. Counted on the "
                    "SGP-scored subset of test takers — distinct from "
                    "num_tested. NULL elsewhere."
                ),
                "nullable": True,
                "example": 139,
            },
            {
                "name": "sgp_median",
                "unit": "percentile",
                "type": "float64",
                "description": (
                    "Median Student Growth Percentile (1-99 percentile rank, "
                    "preserved on its natural scale per "
                    "data-cleaning-standards §4). Float64 because "
                    "even-population groups yield half-integer medians."
                ),
                "nullable": True,
                "example": 51.5,
            },
            {
                "name": "pct_sgp_low_growth",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share of SGP-scored students in the Low Growth band (0-1 scale)."
                ),
                "nullable": True,
                "example": 0.33,
            },
            {
                "name": "pct_sgp_typical_growth",
                "unit": "proportion",
                "type": "float64",
                "description": "Share in the Typical Growth band (0-1 scale).",
                "nullable": True,
                "example": 0.34,
            },
            {
                "name": "pct_sgp_high_growth",
                "unit": "proportion",
                "type": "float64",
                "description": "Share in the High Growth band (0-1 scale).",
                "nullable": True,
                "example": 0.33,
            },
        ],
        source=(
            "Georgia Insights (GaDOE) — Georgia Milestones End-of-Grade Assessment"
        ),
        source_url="https://georgiainsights.gadoe.org/data-downloads/",
        update_frequency="annual",
        year_range=(year_min, year_max),
        partitioned_by=["year"],
        notes=[
            (
                "No 2020 data: the Spring 2020 administration was cancelled "
                "due to the COVID-19 pandemic. 2021 uniquely includes "
                "enrolled_tested_rate reflecting participation drops."
            ),
            (
                "Reading Status is reported on the parent "
                "english_language_arts row via pct_below_grade_level_lexile "
                "/ pct_grade_level_or_above_lexile (2018 onward). Bronze "
                'ships these as a parallel "Reading Status" block; the '
                "transform folds them onto the academic ELA row. The Reading "
                "Status block's own Number Tested is not carried — the ELA "
                "row keeps its own count (the two are equal in current "
                "bronze)."
            ),
            (
                "SGP metrics are reported on the parent "
                "english_language_arts / mathematics rows (grades 4-8, "
                '2024+). Bronze ships them as parallel "SGP …" blocks; the '
                "transform folds them onto the parent rows."
            ),
            (
                "2016-2021 grades 6-8 include assessment_type values eoc and "
                "eog_and_eoc_combined alongside the regular eog rows "
                "(middle-schoolers taking end-of-course exams early). For a "
                "clean EOG-only time series, filter assessment_type = 'eog'."
            ),
            (
                "Subject coverage varies by year and grade: Science and "
                "Social Studies cover all grades 3-8 only in 2015-2016, then "
                "narrow to grades 5 and 8 (Social Studies grade 8 only from "
                "2021, grade 5 dropping after 2019; Science grade 5+8 except "
                "2022's grade-8-and-5-only layout). Physical Science exists "
                "only at grade 8 from 2022."
            ),
            (
                "All percent columns are on the 0-1 decimal scale per "
                "data-cleaning-standards §4 (bronze ships 0-100). Scale "
                "scores, standard deviation, and SGP median preserve their "
                "natural scales."
            ),
            (
                "Legitimate NULL metric spikes: scale_score_std_dev is NULL "
                "pre-2022; Reading Status metrics are NULL outside ELA rows "
                "and pre-2018; enrolled_tested_rate is NULL outside 2021; SGP "
                "metrics are NULL outside 2024+ ELA/Math grades 4-8."
            ),
        ],
        quality_checks=[
            {
                "name": "achievement_levels_sum_to_one",
                "description": (
                    "The four mutually exclusive achievement levels "
                    "(Beginning, Developing, Proficient, Distinguished) "
                    "partition the tested population and sum to 1.0 "
                    "(+/-0.02 rounding tolerance) wherever all four are "
                    "present."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "pct_beginning_learner IS NOT NULL "
                    "AND pct_developing_learner IS NOT NULL "
                    "AND pct_proficient_learner IS NOT NULL "
                    "AND pct_distinguished_learner IS NOT NULL "
                    "AND ABS(pct_beginning_learner + pct_developing_learner "
                    "+ pct_proficient_learner + pct_distinguished_learner "
                    "- 1.0) > 0.02"
                ),
                "mustBe": 0,
            },
            {
                "name": "developing_or_above_consistent_with_components",
                "description": (
                    "The published cumulative pct_developing_learner_or_above"
                    " equals developing + proficient + distinguished "
                    "(+/-0.02) wherever all are present."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "pct_developing_learner_or_above IS NOT NULL "
                    "AND pct_developing_learner IS NOT NULL "
                    "AND pct_proficient_learner IS NOT NULL "
                    "AND pct_distinguished_learner IS NOT NULL "
                    "AND ABS(pct_developing_learner_or_above - "
                    "(pct_developing_learner + pct_proficient_learner + "
                    "pct_distinguished_learner)) > 0.02"
                ),
                "mustBe": 0,
            },
            {
                "name": "proficient_or_above_consistent_with_components",
                "description": (
                    "The published cumulative pct_proficient_learner_or_above"
                    " equals proficient + distinguished (+/-0.02) wherever "
                    "all are present."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "pct_proficient_learner_or_above IS NOT NULL "
                    "AND pct_proficient_learner IS NOT NULL "
                    "AND pct_distinguished_learner IS NOT NULL "
                    "AND ABS(pct_proficient_learner_or_above - "
                    "(pct_proficient_learner + pct_distinguished_learner)) "
                    "> 0.02"
                ),
                "mustBe": 0,
            },
            {
                "name": "lexile_reading_status_complement",
                "description": (
                    "The Reading Status split (below vs at-or-above the "
                    "grade-specific Lexile threshold) is a complement pair "
                    "summing to 1.0 (+/-0.02) wherever both are present."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "pct_below_grade_level_lexile IS NOT NULL "
                    "AND pct_grade_level_or_above_lexile IS NOT NULL "
                    "AND ABS(pct_below_grade_level_lexile "
                    "+ pct_grade_level_or_above_lexile - 1.0) > 0.02"
                ),
                "mustBe": 0,
            },
            {
                "name": "lexile_metrics_only_on_ela_rows",
                "description": (
                    "Reading Status (Lexile) metrics are measured on the ELA "
                    "test-taker population and appear only on "
                    "english_language_arts rows."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(pct_below_grade_level_lexile IS NOT NULL "
                    "OR pct_grade_level_or_above_lexile IS NOT NULL) "
                    "AND subject <> 'english_language_arts'"
                ),
                "mustBe": 0,
            },
            {
                "name": "sgp_growth_bands_sum_to_one",
                "description": (
                    "The three SGP growth bands (Low, Typical, High) "
                    "partition the SGP-scored students and sum to 1.0 "
                    "(+/-0.02) wherever all three are present."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "pct_sgp_low_growth IS NOT NULL "
                    "AND pct_sgp_typical_growth IS NOT NULL "
                    "AND pct_sgp_high_growth IS NOT NULL "
                    "AND ABS(pct_sgp_low_growth + pct_sgp_typical_growth "
                    "+ pct_sgp_high_growth - 1.0) > 0.02"
                ),
                "mustBe": 0,
            },
            {
                "name": "sgp_metrics_only_on_ela_math_grades_4_to_8",
                "description": (
                    "SGP metrics are published only for ELA / Mathematics at "
                    "grades 4-8 (the source ships no grade-3 SGP block)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(num_sgp_received IS NOT NULL OR sgp_median IS NOT NULL "
                    "OR pct_sgp_low_growth IS NOT NULL "
                    "OR pct_sgp_typical_growth IS NOT NULL "
                    "OR pct_sgp_high_growth IS NOT NULL) "
                    "AND (subject NOT IN ('english_language_arts', "
                    "'mathematics') OR grade_level = '03')"
                ),
                "mustBe": 0,
            },
            {
                "name": "enrolled_tested_rate_only_in_2021",
                "description": (
                    "enrolled_tested_rate is a COVID-era column published "
                    "only by the 2021 files."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "enrolled_tested_rate IS NOT NULL AND year <> 2021"
                ),
                "mustBe": 0,
            },
            {
                "name": "lexile_metrics_only_2018_onward",
                "description": (
                    "Reading Status (Lexile) metrics first appear in the "
                    "2018 bronze — never populated for earlier years."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(pct_below_grade_level_lexile IS NOT NULL "
                    "OR pct_grade_level_or_above_lexile IS NOT NULL) "
                    "AND year < 2018"
                ),
                "mustBe": 0,
            },
            {
                "name": "scale_score_std_dev_only_2022_onward",
                "description": (
                    "scale_score_std_dev is published only from 2022 — "
                    "never populated for earlier years."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "scale_score_std_dev IS NOT NULL AND year < 2022"
                ),
                "mustBe": 0,
            },
            {
                "name": "sgp_metrics_only_2024_onward",
                "description": (
                    "SGP metrics first appear in the 2024 bronze — never "
                    "populated for earlier years."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(num_sgp_received IS NOT NULL OR sgp_median IS NOT NULL "
                    "OR pct_sgp_low_growth IS NOT NULL "
                    "OR pct_sgp_typical_growth IS NOT NULL "
                    "OR pct_sgp_high_growth IS NOT NULL) "
                    "AND year < 2024"
                ),
                "mustBe": 0,
            },
            {
                "name": "no_scale_scores_on_eoc_rows",
                "description": (
                    "The bronze EOC / Combined blocks ship no Mean Scale "
                    "Score or Standard Deviation columns, so scale scores "
                    "are never populated on non-eog rows."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(avg_scale_score IS NOT NULL "
                    "OR scale_score_std_dev IS NOT NULL) "
                    "AND assessment_type <> 'eog'"
                ),
                "mustBe": 0,
            },
            {
                "name": "eoc_variants_only_2016_to_2021",
                "description": (
                    "The eoc / eog_and_eoc_combined assessment types exist "
                    "only in the 2016-2021 bronze (the EOG/EOC split era)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "assessment_type <> 'eog' "
                    "AND (year < 2016 OR year > 2021)"
                ),
                "mustBe": 0,
            },
            {
                "name": "scale_score_std_dev_non_negative",
                "description": (
                    "scale_score_std_dev is a standard deviation (dispersion "
                    "of scale scores), so it is always >= 0 where present. "
                    "It is exempt from the bounded-score range check."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "scale_score_std_dev IS NOT NULL "
                    "AND scale_score_std_dev < 0"
                ),
                "mustBe": 0,
            },
        ],
    )

    # ALWAYS LAST: validate the gold just written against the contract just
    # emitted; raises (non-zero exit) on any failure.
    run_topic_validation(GOLD_DIR)

    summary = manifest.tracker.summary()
    logger.info(
        f"Done. Bronze rows: {summary['total_bronze']:,}; "
        f"Gold rows: {summary['total_gold']:,}; "
        f"Years: {summary['years_processed']}"
    )


if __name__ == "__main__":
    main()
