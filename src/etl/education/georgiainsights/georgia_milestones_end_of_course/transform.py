"""Transform bronze georgia_milestones_end_of_course files into gold fact tables.

Source: Georgia Insights (GaDOE) — Georgia Milestones End-of-Course (EOC)
assessment results for high-school content areas (literature, algebra
courses, Biology, US History, etc.). Each school year publishes up to three
administrations — Winter (mid-year retest), Spring (primary end-of-year),
Full-Year (fall+winter+spring aggregate) — each at three detail levels
(state, system/district, school). Bronze ships 72 files spanning Winter 2014
through Full-Year 2024-2025; there are no demographic breakdowns anywhere in
this bronze, so per data-cleaning-standards §5 the ``demographic`` column is
omitted from gold.

Era routing is STRUCTURAL (zip member count / workbook sheet count), not
year-tag based. Four file shapes exist (bronze-data-structure.md "Excel
Sheet Structure", re-verified against all 72 files during authoring):

- ``state_single_sheet`` — 6 state files 2014-2017: single sheet, subjects
  are ROWS in a ``Content Area`` column; ``header=1``.
- ``zip_per_subject`` — 12 School/System zips 2014-2017: one single-sheet
  workbook per subject; ``header=1`` per member, subject from the member
  filename.
- ``zip_multi_sheet_xlsx`` — Spring 2018 School/System zips wrapping a
  single multi-sheet xlsx; read like ``xlsx_multi_sheet``.
- ``xlsx_multi_sheet`` — every direct multi-sheet workbook (Winter 2017 —
  Full-Year 2024-2025): ``header=[1, 2]`` two-row header, subject from the
  sheet name.

All reads go through pandas with ``dtype=str`` + topic suppression markers
as ``na_values`` (the shared ``read_bronze_file`` reads only the first sheet
of a workbook, so multi-sheet/zip reading uses a local helper — the
GeorgiaInsights precedent set by attendance_dashboard / ccrpi_*). Whole-sheet
Excel reads cannot drop records at parse time, so read-loss raw == parsed by
construction and no read-loss events are recorded.

Design decisions (each re-verified against bronze during authoring):

- **Year + administration come ONLY from the filename.** ``Winter YYYY`` →
  year = YYYY+1 (a winter administration is the mid-year retest of the
  school year ending the NEXT spring); ``Spring YYYY`` → YYYY;
  ``Full[ _-]Year YYYY1-YYYY2`` → YYYY2; ``Full_Year_YYYY`` → YYYY (the
  sheet titles spell out "Full Year 2020-2021 ... 2021"). The range form is
  matched before the single-year form so ``Full-Year-2024-2025`` cannot
  mis-parse as 2024.

- **administration is a fact categorical** (``winter`` / ``spring`` /
  ``full_year``): the three slices are NOT duplicates of each other (winter
  is a retest cohort, spring the primary administration, full_year the
  aggregate), so each is kept as its own row keyed by
  (year, administration, geography, subject).

- **Subject labels normalize to one snake_case vocabulary.** Raw labels come
  from three places (sheet names, zip member filenames, the ``Content
  Area`` column in 2014-2017 state files) with heavy drift ("History",
  "U. S. History", "U S History", "United States History" are all
  us_history). The local ``SUBJECT_MAP`` covers every observed label and
  RAISES on anything unmapped; the shared ``apply_subject_normalization``
  runs as a §10a backstop. "Phys(ical) Science Gr8" (Full-Year 2020-2021's
  8th-grade-only administration) folds into ``physical_science`` — the
  metrics describe the same course content and the grade-aware sibling
  topics carry grade detail; the fold is documented in the contract.

- **Percent columns ship 0-100 in every era** (re-verified per era) and are
  divided by 100 to the canonical 0-1 scale. Floating-point residue within
  1e-9 of the [0, 1] boundaries (bronze stores sums like ``a + b - 100`` as
  ``-3.55e-15``) is snapped to the boundary; real out-of-range values would
  still fail the contract range checks. ``avg_scale_score`` (140-820 EOC
  scale), ``scale_score_std_dev`` and ``sgp_median`` (1-99 percentile rank,
  Float64 because 2025 bronze publishes half-point medians like 61.5) keep
  their natural scales.

- **Suppression → NULL, row kept.** Markers vary by era (``'--'``,
  ``'---'``, ``'     -----'``); all are nulled at read time via
  ``na_values`` plus an explicit post-read marker sweep. Suppressed rows
  keep geography + ``num_tested`` (never suppressed), so they survive the
  all-null-metric filter below.

- **Footnote rows are filtered explicitly** (ledgered per file as
  ``footnote_row``): the observed set is the Lexile reading-status footnote
  (``^To achieve…`` / ``*To achieve…``), the Full-Year 2020-2021 COVID
  notes (``Note:…``, ``For more information…``, ``The EOG analysis…``,
  ``https://…``, ``*Only spring…``), and Spring 2015's ``Results for all
  students…`` placeholder members.

- **Rows whose EVERY metric (incl. num_tested) is NULL are dropped**
  (ledgered as ``all_metric_columns_null``). These are template/footer
  residue, not data: the Spring-2024 and Full-Year-2023-2024 "Algebra CC"
  sheets are EMPTY templates (header-only at school/system level, one
  all-NaN state row) — which is why year=2024 has no algebra_cc rows. The
  first populated Algebra CC data is Winter-2024 (year=2025, no SGP block)
  and Spring/Full-Year 2025 (with SGP).

- **Charter SYSTEM→CAMPUS promotion** (shared
  ``_charter_district_promotion`` module): 2015-2017 school-level rows
  report State/Commission Charter campuses under the umbrella SYSTEM codes
  782/783; they are rewritten to the 7-digit campus codes
  (district_code + school_code) the repo keys school rows on. Promotions
  are ledgered per year as manifest ``reclassified`` events.

- **Dedup tie-break**: each (year, administration, detail_level) is fed by
  exactly one bronze file and natural keys are unique within files, so
  dedup is purely defensive; ``sort_col="num_tested"`` would prefer a row
  with a reported count over a placeholder. ``assert_no_natural_key_
  collisions`` runs first (after promotion) so a promotion-induced or
  bronze-duplicate key with DIVERGENT metrics fails loudly instead of being
  silently resolved.

Natural key: (year, administration, detail_level via filename,
district_code, school_code, subject).

Known bronze quirks corrected in bronze-data-structure.md (Corrections
section): Standard Deviation already present in Winter-2021 (Era 5) files;
Winter-2024 Algebra CC has NO SGP block; Spring-2024 / Full-Year-2023-2024
Algebra CC sheets are empty templates; the "blank row 2" in Winter/Spring
2016 *School* workbooks does not exist (only the Winter 2016 *State* file
has it).
"""

import io
import logging
import re
import zipfile
from pathlib import Path

import pandas as pd
import polars as pl

from src.etl.education.georgiainsights._charter_district_promotion import (
    promote_charter_system_to_campus_district,
)
from src.utils.metadata import write_data_dictionary
from src.utils.readers import SUPPRESSION_VALUES, list_bronze_files
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

TOPIC = "georgia_milestones_end_of_course"
BRONZE_DIR = Path(
    "data/bronze/education/georgiainsights/georgia_milestones_end_of_course"
)
GOLD_DIR = Path("data/gold/education/georgia_milestones_end_of_course")

# =============================================================================
# Normalization maps
# =============================================================================

# Season token (from the filename) → administration categorical. Winter files
# carry a +1 year offset (mid-year retest of the school year ending the next
# spring); the range Full-Year form must match before the single-year form.
ADMINISTRATION_MAP: dict[str, str] = {
    "Winter": "winter",
    "Spring": "spring",
    "Full Year": "full_year",
}

_ADMIN_FILENAME_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"Full[-_ ]Year[-_ ]?(\d{4})-(\d{4})", re.IGNORECASE), "Full Year"),
    (re.compile(r"Full[-_ ]Year[-_ ]?(\d{4})", re.IGNORECASE), "Full Year"),
    (re.compile(r"Winter[-_ ](\d{4})", re.IGNORECASE), "Winter"),
    (re.compile(r"Spring[-_ ](\d{4})", re.IGNORECASE), "Spring"),
]

# Canonicalized subject key (lowercase, whitespace→underscore — produced by
# _canonical_subject after stripping detail-level prefixes / file suffixes /
# the Spring-2017 member-name marker) → canonical gold subject. Every key was
# observed in bronze (sheet names, zip member basenames, or Content Area
# column values across the 6 single-sheet state files); _canonical_subject
# RAISES on labels not covered here. Canonical values follow §16 / the shared
# subject vocabulary: full `_and_composition` forms, `us_history`,
# `economics_business_free_enterprise`. Curriculum-era distinct courses
# (coordinate_algebra / algebra_i / algebra_concepts_and_connections;
# geometry / analytic_geometry) stay distinct on purpose.
SUBJECT_MAP: dict[str, str] = {
    # 9th Grade Literature & Composition (2014-2020; discontinued after)
    "9th_grade_literature": "9th_grade_literature_and_composition",
    "9th_grade_literature_&_composition": "9th_grade_literature_and_composition",
    "9th_grade_literature_and_composition": "9th_grade_literature_and_composition",
    "ninth_grade_literature_&_composition": "9th_grade_literature_and_composition",
    # American Literature & Composition (all eras)
    "american_literature": "american_literature_and_composition",
    "american_literature_&_composition": "american_literature_and_composition",
    "american_literature_and_composition": "american_literature_and_composition",
    # Algebra family — three DISTINCT courses across curriculum eras
    "coordinate_algebra": "coordinate_algebra",
    "algebra_i": "algebra_i",
    "algebra_cc": "algebra_concepts_and_connections",
    # Geometry family — two DISTINCT courses
    "analytic_geometry": "analytic_geometry",
    "geometry": "geometry",
    # Biology (all eras)
    "biology": "biology",
    # Physical Science. "Phys(ical) Science Gr8" is Full-Year 2020-2021's
    # 8th-grade-only administration of the same course — folded into
    # physical_science (see module docstring).
    "physical_science": "physical_science",
    "phys_science_gr8": "physical_science",
    "physical_science_gr8": "physical_science",
    # US History — the heaviest label drift in the topic
    "history": "us_history",
    "us_history": "us_history",
    "u_s_history": "us_history",
    "u._s._history": "us_history",
    "u.s._history": "us_history",
    "united_states_history": "us_history",
    # Economics (2014-2020; discontinued after)
    "economics": "economics_business_free_enterprise",
    "economics/business/free_enterprise": "economics_business_free_enterprise",
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
    "num_sgp_received",
    "sgp_median",
    "pct_sgp_low_growth",
    "pct_sgp_typical_growth",
    "pct_sgp_high_growth",
    "enrolled_tested_rate",
]

STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "detail_level",
    "administration",
    "subject",
    *METRIC_COLUMNS,
]

# sgp_median is a 1-99 percentile rank but Float64 because 2025 bronze
# publishes half-point medians (61.5 etc. — 81 such values re-verified in
# Spring-2025 American Literature alone).
TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "detail_level": pl.Utf8,
    "administration": pl.Utf8,
    "subject": pl.Utf8,
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
    "num_sgp_received": pl.Int64,
    "sgp_median": pl.Float64,
    "pct_sgp_low_growth": pl.Float64,
    "pct_sgp_typical_growth": pl.Float64,
    "pct_sgp_high_growth": pl.Float64,
    "enrolled_tested_rate": pl.Float64,
}

# Percent columns that are divided by 100 to the gold 0-1 scale. Score /
# count / percentile columns are excluded (natural scale preserved).
# enrolled_tested_rate is a 0-1 rate too (bronze ships 0-100) but lacks the
# pct_ prefix, so it is added explicitly.
_PCT_COLUMNS: set[str] = {c for c in METRIC_COLUMNS if c.startswith("pct_")} | {
    "enrolled_tested_rate"
}

# Snap floating-point residue around the [0, 1] boundaries (bronze stores
# spreadsheet sums like `a + b - 100` as e.g. -3.55e-15, which would land in
# gold as a negative share). Larger deviations still surface as real
# out-of-range values via the contract range checks.
_PCT_CLAMP_TOLERANCE = 1e-9

# Era-specific suppression markers on top of the shared set
# (bronze-data-structure.md §11): '--' (Era 4+ universal), '---'
# (Spring 2016 School), '     -----' (5 spaces + 5 dashes, Winter 2014 /
# Spring 2015).
_TOPIC_SUPPRESSION_VALUES: set[str] = SUPPRESSION_VALUES | {
    "--",
    "---",
    "     -----",
}

# Canonical bronze header (UPPERCASE, whitespace-collapsed — see
# _canonical_header) → gold column. Destinations starting with "_" are
# either intentional drops (names/RESA are dimension attributes) or
# intermediates (_compound_key, _subject_raw) resolved by the readers.
_HEADER_MAP: dict[str, str] = {
    "SYSTEM CODE": "district_code",
    "SCHOOL CODE": "school_code",
    "SYSTEM NAME": "_drop_name",
    "SCHOOL NAME": "_drop_name",
    "RESA": "_drop_resa",
    # 2015/2016 School workbooks: 7-digit Key = system(3) + school(4)
    "KEY": "_compound_key",
    # State files where subjects are rows; redundant column on modern state sheets
    "CONTENT AREA": "_subject_raw",
    # Number tested — Winter 2014 / Spring 2015 use bare "N " (trailing space)
    "N": "num_tested",
    "NUMBER TESTED": "num_tested",
    "MEAN SCALE SCORE": "avg_scale_score",
    # Spring 2015 System (era-unique), Winter 2021, and Spring 2022 onward
    "STANDARD DEVIATION": "scale_score_std_dev",
    "% BEGINNING LEARNER": "pct_beginning_learner",
    "% DEVELOPING LEARNER": "pct_developing_learner",
    "% PROFICIENT LEARNER": "pct_proficient_learner",
    "% DISTINGUISHED LEARNER": "pct_distinguished_learner",
    "% DEVELOPING LEARNER & ABOVE": "pct_developing_learner_or_above",
    "% PROFICIENT LEARNER & ABOVE": "pct_proficient_learner_or_above",
    # Reading Status sub-headers — per-course Lexile thresholds (1050L for
    # 9th Grade Lit, 1185L for American Lit from 2021; both flatten into one
    # column pair, threshold documented in the contract)
    "% BELOW GRADE LEVEL (LEXILE < 1050L)": "pct_below_grade_level_lexile",
    "% BELOW GRADE LEVEL (LEXILE < 1185L)": "pct_below_grade_level_lexile",
    "% GRADE LEVEL OR ABOVE (LEXILE ≥ 1050L)": "pct_grade_level_or_above_lexile",
    "% GRADE LEVEL OR ABOVE (LEXILE ≥ 1185L)": "pct_grade_level_or_above_lexile",
    # COVID participation column — Full-Year 2020-2021 only
    "PERCENT OF ENROLLED STUDENTS TESTED": "enrolled_tested_rate",
    # SGP sub-headers — populated data exists from year=2025 only
    "NUMBER RECEIVED SGP": "num_sgp_received",
    "SGP MEDIAN": "sgp_median",
    "% SGP LOW GROWTH": "pct_sgp_low_growth",
    "% SGP TYPICAL GROWTH": "pct_sgp_typical_growth",
    "% SGP HIGH GROWTH": "pct_sgp_high_growth",
}

_DROP_DESTINATIONS: set[str] = {"_drop_name", "_drop_resa"}

# Columns a frame may legitimately carry after rename. Anything else means a
# new/unknown bronze header — fail loudly rather than silently dropping data.
_ALLOWED_POST_RENAME: set[str] = set(METRIC_COLUMNS) | {
    "district_code",
    "school_code",
    "_compound_key",
    "_subject_raw",
}

# Footnote / footer-row prefixes observed across all 72 files (full-file scan
# during authoring; see module docstring). Matched with str.starts_with
# against every string column. Conservative: none of these can be a real
# district/school name or Content Area value.
_FOOTNOTE_PREFIXES: tuple[str, ...] = (
    "^",
    "Note:",
    "*To achieve",
    "*Only spring",
    "Results for all students",
    "For more information",
    "The EOG analysis",
    "https://",
)


# =============================================================================
# Filename parsing
# =============================================================================


def _parse_filename(filename: str) -> tuple[int, str, str, str]:
    """Extract (year, administration, detail_level, season_token) from a name.

    Year semantics (bronze-data-structure.md §1): Winter YYYY → YYYY + 1
    (the school year that ends the NEXT spring); Spring YYYY → YYYY;
    Full-Year range → the end year; Full_Year_YYYY → YYYY. Detail level
    comes from the School/System/State token present in every filename.
    """
    season = None
    year = None
    for pattern, token in _ADMIN_FILENAME_PATTERNS:
        match = pattern.search(filename)
        if match:
            season = token
            if token == "Winter":
                year = int(match.group(1)) + 1
            elif len(match.groups()) == 2:
                year = int(match.group(2))
            else:
                year = int(match.group(1))
            break
    if season is None or year is None:
        raise ValueError(f"Cannot parse administration/year from {filename!r}")

    lower = filename.lower()
    if "school" in lower:
        detail = "school"
    elif "system" in lower:
        detail = "district"
    elif "state" in lower:
        detail = "state"
    else:
        raise ValueError(f"Cannot parse detail level from {filename!r}")

    return year, ADMINISTRATION_MAP[season], detail, season


# =============================================================================
# Subject + header canonicalization
# =============================================================================


def _canonical_subject(raw: str, *, context: str) -> str:
    """Normalize a raw subject label to the canonical gold value.

    Accepts sheet names ("School - Algebra CC"), zip member basenames
    ("U S History_System.xlsx", "Spring 2017 EOC - School Level -
    Biology.xlsx"), and Content Area column values ("U. S. History").
    Raises on anything not covered by SUBJECT_MAP so new labels cannot
    silently produce wrong subjects.
    """
    s = str(raw).strip()
    # Detail-level prefix used by sheet names and 2014-2015 member names.
    for prefix in ("School -", "System -", "State -"):
        if s.startswith(prefix):
            s = s[len(prefix) :].strip()
            break
    # File suffixes on zip member basenames (longest first).
    for suffix in (
        "_School.xlsx",
        "_System.xlsx",
        "_School.xls",
        "_System.xls",
        ".xlsx",
        ".xls",
    ):
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
            break
    # Spring 2017 members: "Spring 2017 EOC - School Level - <subject>".
    for marker in ("EOC - School Level - ", "EOC - System Level - "):
        if marker in s:
            s = s.split(marker, 1)[1].strip()
            break
    key = re.sub(r"\s+", "_", s.lower().strip())
    subject = SUBJECT_MAP.get(key)
    if subject is None:
        raise ValueError(
            f"{context}: unmapped subject label {raw!r} (key {key!r}). "
            f"Add it to SUBJECT_MAP."
        )
    return subject


def _canonical_header(name: object) -> str:
    """Canonicalize a bronze header for _HEADER_MAP lookup.

    Handles the two-row-header MultiIndex tuples pandas produces for
    ``header=[1, 2]`` reads: the sub-header (row 2) carries the real metric
    name under the merged "Reading Status*/^" and "SGP " parents, so a
    non-empty sub-header wins; pandas' "Unnamed: N_level_1" placeholders
    count as empty. Scalar headers are uppercased with whitespace runs
    (including embedded newlines like "Number\\nTested") collapsed and the
    footnote daggers (* ^) on parents are irrelevant because parents only
    survive when the sub-header is empty.
    """
    if isinstance(name, tuple):
        parent = "" if name[0] is None or pd.isna(name[0]) else str(name[0])
        sub = ""
        if len(name) > 1 and name[1] is not None and not pd.isna(name[1]):
            sub = str(name[1])
        if sub.startswith("Unnamed:"):
            sub = ""
        if parent.startswith("Unnamed:"):
            parent = ""
        name = sub if sub else parent
    s = str(name).replace("\n", " ").replace("\r", " ")
    return " ".join(s.split()).strip().upper()


# =============================================================================
# Frame-level helpers
# =============================================================================


def _frame_from_pandas(pdf: pd.DataFrame, *, context: str) -> pl.DataFrame:
    """Convert a raw pandas read into a renamed polars frame.

    Steps: drop all-NaN columns (trailing unnamed/None columns, and the
    duplicate forward-filled MultiIndex tails on state sheets) BEFORE header
    canonicalization so duplicates cannot collide; canonicalize headers;
    rename via _HEADER_MAP (dropping name/RESA dimension attributes); drop
    fully-null rows (blank spacers); raise on any unknown surviving header.
    """
    non_empty = [c for c in pdf.columns if not pdf[c].isna().all()]
    pdf = pdf.loc[:, non_empty]
    pdf.columns = [_canonical_header(c) for c in pdf.columns]

    df = pl.from_pandas(pdf)
    # Empty template sheets (2024 Algebra CC) reduce to a 0x0 frame here;
    # all_horizontal needs at least one column, so guard the spacer filter.
    if df.width and df.height:
        df = df.filter(~pl.all_horizontal(pl.all().is_null()))

    rename = {
        c: _HEADER_MAP[c]
        for c in df.columns
        if c in _HEADER_MAP and _HEADER_MAP[c] not in _DROP_DESTINATIONS
    }
    drop = [
        c
        for c in df.columns
        if c in _HEADER_MAP and _HEADER_MAP[c] in _DROP_DESTINATIONS
    ]
    df = df.rename(rename)
    if drop:
        df = df.drop(drop)

    unknown = [c for c in df.columns if c not in _ALLOWED_POST_RENAME]
    if unknown:
        raise ValueError(
            f"{context}: unknown bronze header(s) {unknown} — extend "
            f"_HEADER_MAP (silent drops hide data loss)."
        )
    return df


def _filter_footnote_rows(df: pl.DataFrame) -> tuple[pl.DataFrame, int]:
    """Drop rows where ANY string column starts with a footnote prefix.

    Applied BEFORE ID formatting / subject mapping so footer text landing in
    the first column (System Code / Content Area) cannot masquerade as a
    district code or trip the unmapped-subject guard.
    """
    str_cols = [c for c in df.columns if df.schema[c] == pl.Utf8]
    if not str_cols or df.height == 0:
        return df, 0
    pred = None
    for c in str_cols:
        for prefix in _FOOTNOTE_PREFIXES:
            p = pl.col(c).str.starts_with(prefix).fill_null(False)
            pred = p if pred is None else pred | p
    filtered = df.filter(~pred)
    return filtered, df.height - filtered.height


def _split_compound_key(df: pl.DataFrame) -> pl.DataFrame:
    """Split the 2015/2016 School ``Key`` (system*10000 + school) column.

    7-digit int like 6010103 → district_code "601" + school_code "0103".
    """
    if "_compound_key" not in df.columns:
        return df
    padded = (
        pl.col("_compound_key")
        .cast(pl.Utf8, strict=False)
        .str.replace(r"\.0$", "")
        .str.zfill(7)
    )
    return df.with_columns(
        padded.str.slice(0, 3).alias("district_code"),
        padded.str.slice(3, 4).alias("school_code"),
    ).drop("_compound_key")


def _format_ids(df: pl.DataFrame) -> pl.DataFrame:
    """Zero-pad district_code (3) / school_code (4) where present.

    Strips the trailing ".0" float-cast residue from the xls eras, then
    zfills — zfill never truncates, so 7-digit charter campus codes survive.
    Covers the Spring 2017 bare-int School Code quirk (103 → "0103").
    """
    exprs = []
    for col, width in (("district_code", 3), ("school_code", 4)):
        if col in df.columns:
            exprs.append(
                pl.col(col)
                .cast(pl.Utf8, strict=False)
                .str.replace(r"\.0$", "")
                .str.zfill(width)
                .alias(col)
            )
    return df.with_columns(exprs) if exprs else df


def _null_suppression_markers(df: pl.DataFrame) -> pl.DataFrame:
    """Null any residual suppression marker / blank in string metric columns.

    ``na_values`` at read time catches exact markers; this sweep adds the
    stripped-equality and whitespace-only cases for metric columns that are
    still Utf8 (the readers bypass read_bronze_file, so the shared marker
    handling does not apply).
    """
    markers = list(_TOPIC_SUPPRESSION_VALUES)
    exprs = []
    for col in METRIC_COLUMNS:
        if col in df.columns and df.schema[col] == pl.Utf8:
            stripped = pl.col(col).str.strip_chars()
            is_marker = stripped.is_in(markers) | (stripped == "")
            exprs.append(
                pl.when(is_marker).then(None).otherwise(pl.col(col)).alias(col)
            )
    return df.with_columns(exprs) if exprs else df


def _cast_metric_columns(df: pl.DataFrame) -> pl.DataFrame:
    """Cast metrics to TARGET_TYPES; scale percent columns to 0-1.

    ``strict=False`` so any remaining non-numeric string lands as NULL.
    Percent columns divide by 100 then snap residue within
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


def _annotate(
    df: pl.DataFrame, year: int, administration: str, detail_level: str
) -> pl.DataFrame:
    """Attach the year / administration / detail_level fact columns."""
    return df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.lit(administration).alias("administration"),
        pl.lit(detail_level).alias("detail_level"),
    )


# =============================================================================
# Readers (one per structural file shape)
# =============================================================================


def _read_state_single_sheet(
    path: Path, year: int, administration: str, subject_ledger: dict[str, str]
) -> tuple[pl.DataFrame, int]:
    """Read a 2014-2017 state file: one sheet, one row per Content Area."""
    pdf = pd.read_excel(
        path,
        sheet_name=0,
        header=1,
        dtype=str,
        na_values=list(_TOPIC_SUPPRESSION_VALUES),
    )
    df = _frame_from_pandas(pdf, context=path.name)
    if "_subject_raw" not in df.columns:
        raise ValueError(f"{path.name}: state file lacks a 'Content Area' column")

    # Footnotes first so footer text cannot reach the subject map.
    df, n_footnotes = _filter_footnote_rows(df)

    raw_subjects = df["_subject_raw"].drop_nulls().unique().to_list()
    mapping = {raw: _canonical_subject(raw, context=path.name) for raw in raw_subjects}
    subject_ledger.update(mapping)
    df = (
        df.with_columns(
            pl.col("_subject_raw")
            .replace_strict(mapping, default=None)
            .alias("subject")
        )
        .drop("_subject_raw")
        .filter(pl.col("subject").is_not_null())
    )

    df = _null_suppression_markers(df)
    df = _cast_metric_columns(df)
    return _annotate(df, year, administration, "state"), n_footnotes


def _read_zip_per_subject(
    path: Path,
    year: int,
    administration: str,
    detail_level: str,
    subject_ledger: dict[str, str],
) -> tuple[pl.DataFrame, int]:
    """Read a 2014-2017 zip whose members are one single-sheet workbook each.

    Subject comes from the member basename (Winter_2016_EOC_School.zip nests
    members under a subdirectory — basename only). Single-row header
    (row 0 title, row 1 header).
    """
    frames: list[pl.DataFrame] = []
    n_footnotes = 0
    with zipfile.ZipFile(path) as zf:
        for member in zf.namelist():
            if member.endswith("/"):
                continue
            basename = member.rsplit("/", 1)[-1]
            subject = _canonical_subject(basename, context=f"{path.name}:{member}")
            subject_ledger[basename] = subject
            buf = zf.read(member)
            engine = "xlrd" if basename.lower().endswith(".xls") else "openpyxl"
            pdf = pd.read_excel(
                io.BytesIO(buf),
                sheet_name=0,
                engine=engine,
                header=1,
                dtype=str,
                na_values=list(_TOPIC_SUPPRESSION_VALUES),
            )
            df = _frame_from_pandas(pdf, context=f"{path.name}:{member}")
            df, n = _filter_footnote_rows(df)
            n_footnotes += n
            df = _split_compound_key(df)
            df = _format_ids(df)
            df = _null_suppression_markers(df)
            df = _cast_metric_columns(df)
            df = df.with_columns(pl.lit(subject).alias("subject"))
            frames.append(_annotate(df, year, administration, detail_level))

    if not frames:
        raise ValueError(f"{path.name}: no member workbooks in zip")
    # Members differ in column sets (Spring 2015 System has Standard
    # Deviation; school vs system shapes) — harmonize before concat.
    frames = harmonize_columns(frames, STANDARD_COLUMNS, TARGET_TYPES)
    return pl.concat(frames, how="vertical"), n_footnotes


def _read_multi_sheet_workbook(
    source: Path | io.BytesIO,
    *,
    filename: str,
    year: int,
    administration: str,
    detail_level: str,
    subject_ledger: dict[str, str],
) -> tuple[pl.DataFrame, int]:
    """Read a Winter-2017+ multi-sheet workbook (two-row header layout).

    One sheet per subject (sheet name carries the label). ``header=[1, 2]``:
    row 1 is the main header, row 2 the sub-header that names the Reading
    Status / SGP columns (blank elsewhere — data always starts at row 3 in
    this era). State sheets carry a redundant ``Content Area`` column that
    is dropped in favor of the sheet name.
    """
    xl = pd.ExcelFile(source)
    frames: list[pl.DataFrame] = []
    n_footnotes = 0
    for sheet_name in xl.sheet_names:
        subject = _canonical_subject(sheet_name, context=f"{filename}:{sheet_name}")
        subject_ledger[sheet_name] = subject
        pdf = xl.parse(
            sheet_name=sheet_name,
            header=[1, 2],
            dtype=str,
            na_values=list(_TOPIC_SUPPRESSION_VALUES),
        )
        df = _frame_from_pandas(pdf, context=f"{filename}:{sheet_name}")
        df, n = _filter_footnote_rows(df)
        n_footnotes += n
        if "_subject_raw" in df.columns:
            # Redundant with the sheet name on state sheets.
            df = df.drop("_subject_raw")
        df = _format_ids(df)
        df = _null_suppression_markers(df)
        df = _cast_metric_columns(df)
        df = df.with_columns(pl.lit(subject).alias("subject"))
        frames.append(_annotate(df, year, administration, detail_level))

    if not frames:
        raise ValueError(f"{filename}: no sheets read")
    frames = harmonize_columns(frames, STANDARD_COLUMNS, TARGET_TYPES)
    return pl.concat(frames, how="vertical"), n_footnotes


# =============================================================================
# File-level dispatch
# =============================================================================


def _detect_file_shape(path: Path) -> str:
    """Structural era detection (no filename year tags).

    - zip with one member → a wrapped multi-sheet xlsx (Spring 2018);
      zip with many members → one workbook per subject (2014-2017).
    - direct workbook with one sheet → state all-content-areas file
      (subjects are rows; only state files have a single sheet);
      multiple sheets → modern multi-sheet layout (two-row header).
    """
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            members = [m for m in zf.namelist() if not m.endswith("/")]
        return "zip_multi_sheet_xlsx" if len(members) == 1 else "zip_per_subject"
    n_sheets = len(pd.ExcelFile(path).sheet_names)
    return "state_single_sheet" if n_sheets == 1 else "xlsx_multi_sheet"


def transform_file(
    path: Path, manifest: TransformManifest, subject_ledger: dict[str, str]
) -> tuple[pl.DataFrame | None, str]:
    """Transform one bronze file; returns (frame, season_token).

    Whole-sheet Excel reads cannot drop records at parse time (read-loss
    raw == parsed by construction), so no read-loss events are recorded.
    Footnote rows and all-metric-null residue are ledgered via
    record_filtered.
    """
    year, administration, detail_level, season = _parse_filename(path.name)
    shape = _detect_file_shape(path)
    logger.info(
        f"{path.name}: year={year} admin={administration} "
        f"detail={detail_level} shape={shape}"
    )

    if shape == "state_single_sheet":
        if detail_level != "state":
            raise ValueError(f"{path.name}: single-sheet workbook is not state-level")
        df, n_footnotes = _read_state_single_sheet(
            path, year, administration, subject_ledger
        )
    elif shape == "zip_per_subject":
        df, n_footnotes = _read_zip_per_subject(
            path, year, administration, detail_level, subject_ledger
        )
    elif shape == "zip_multi_sheet_xlsx":
        with zipfile.ZipFile(path) as zf:
            members = [m for m in zf.namelist() if not m.endswith("/")]
            buf = zf.read(members[0])
        df, n_footnotes = _read_multi_sheet_workbook(
            io.BytesIO(buf),
            filename=f"{path.name}:{members[0]}",
            year=year,
            administration=administration,
            detail_level=detail_level,
            subject_ledger=subject_ledger,
        )
    else:
        df, n_footnotes = _read_multi_sheet_workbook(
            path,
            filename=path.name,
            year=year,
            administration=administration,
            detail_level=detail_level,
            subject_ledger=subject_ledger,
        )

    manifest.record_file(path, year, shape, df.height, df.columns)
    manifest.record_bronze(year, df.height)
    if n_footnotes:
        manifest.record_filtered(year, n_footnotes, "footnote_row")
        logger.info(f"  Dropped {n_footnotes} footnote row(s)")

    # Drop rows with NO data in any metric column (num_tested included —
    # it is never suppressed, so genuinely suppressed rows survive). These
    # are template/footer residue, incl. the empty 2024 Algebra CC sheets.
    present_metrics = [m for m in METRIC_COLUMNS if m in df.columns]
    if present_metrics:
        keep = pl.any_horizontal([pl.col(m).is_not_null() for m in present_metrics])
        before = df.height
        df = df.filter(keep)
        dropped = before - df.height
        if dropped:
            manifest.record_filtered(year, dropped, "all_metric_columns_null")
            logger.info(f"  Dropped {dropped} all-metric-null row(s)")

    if df.height == 0:
        logger.warning(f"{path.name}: no data rows after transform")
        return None, season
    return df, season


# =============================================================================
# Pipeline orchestration
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for georgia_milestones_end_of_course."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)
    subject_ledger: dict[str, str] = {}
    admin_tokens: list[str] = []
    frames: list[pl.DataFrame] = []

    # The shared extract_year_from_filename cannot express the Winter year
    # offset (Winter YYYY = school year ending YYYY+1) — _parse_filename owns
    # year + administration + detail-level parsing for this topic.
    for path in list_bronze_files(BRONZE_DIR, extensions=[".xls", ".xlsx", ".zip"]):
        df, season = transform_file(path, manifest, subject_ledger)
        admin_tokens.append(season)
        if df is not None and df.height > 0:
            frames.append(df)

    if not frames:
        raise RuntimeError("No bronze data transformed — check bronze directory")

    # Eras carry different column subsets (no SGP before 2025, no Standard
    # Deviation in most eras, enrolled_tested_rate only in Full-Year
    # 2020-2021); harmonize adds the missing columns as typed NULLs.
    frames = harmonize_columns(frames, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(frames, how="vertical")
    logger.info(f"Combined all frames: {combined.height:,} rows")

    # §10a backstop: the local SUBJECT_MAP already produces canonical values
    # (and raises on unmapped labels); this keeps the vocabulary aligned with
    # the shared cross-topic normalizer even if the local map drifts.
    combined = combined.with_columns(
        apply_subject_normalization("subject").alias("subject")
    )

    # Charter SYSTEM → CAMPUS district codes on school-level rows (2015-2017
    # bronze quirk; ledgered as manifest reclassified events). Runs before
    # the collision guard + dedup so any key collision the rewrite creates
    # is surfaced/resolved by the standard machinery. (2017 is the only year
    # carrying both representations, in disjoint administrations — no
    # collision in practice.)
    combined = promote_charter_system_to_campus_district(combined, manifest=manifest)

    # Guard BEFORE dedup: duplicate keys with DIVERGENT metrics mean an
    # alias/promotion bug and must fail loudly. detail_level is part of the
    # key because district aggregates share (year, district, admin, subject)
    # with their school rows once school_code is NULL-harmonized.
    natural_keys = [
        "year",
        "detail_level",
        "district_code",
        "school_code",
        "administration",
        "subject",
    ]
    assert_no_natural_key_collisions(combined, natural_keys, METRIC_COLUMNS)

    # Defensive dedup: each (year, administration, detail_level) comes from
    # exactly one bronze file and keys are unique within files (re-verified —
    # the guard above would have raised otherwise). sort_col="num_tested"
    # prefers a row with a reported count over a placeholder if a true
    # duplicate ever appears.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=[
            "year",
            "district_code",
            "school_code",
            "administration",
            "subject",
        ],
        district_keys=["year", "district_code", "administration", "subject"],
        state_keys=["year", "administration", "subject"],
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

    # Categorical ledgers: subject as the effective raw-label → canonical map
    # observed across sheet names / zip members / Content Area values;
    # administration as the season-token map (filename-derived vocabulary).
    manifest.record_categorical(
        column="subject",
        map_dict=dict(sorted(subject_ledger.items())),
        bronze_series=pl.Series("subject_raw", sorted(subject_ledger.keys())),
        gold_series=combined["subject"],
    )
    manifest.record_categorical(
        column="administration",
        map_dict=ADMINISTRATION_MAP,
        bronze_series=pl.Series("season", admin_tokens),
        gold_series=combined["administration"],
    )
    manifest.write(GOLD_DIR)

    # Known legitimate NULL spikes (warnings only): SGP metrics are null
    # outside year=2025 Algebra CC / American Lit; Reading Status is null
    # outside literature subjects; scale_score_std_dev is null outside
    # Spring-2015-System / Winter-2021 / 2022+; enrolled_tested_rate is null
    # outside Full-Year 2020-2021.
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
            "Georgia Milestones End-of-Course (EOC) assessment results for "
            "high-school core content areas, published for each of up to "
            "three administrations per school year (Winter mid-year retest, "
            "Spring primary, Full-Year aggregate) at the state, "
            "district/system, and school level. Core metrics are the count "
            "of students tested, the mean scale score, and the share of "
            "students at each of the four achievement levels (Beginning, "
            "Developing, Proficient, Distinguished Learner) plus the two "
            "cumulative shares. Literature subjects add a Reading Status "
            "split against a per-course Lexile threshold (9th Grade "
            "Literature 1050L through 2020; American Literature 1185L). "
            "Student Growth Percentile (SGP) metrics appear in the source "
            "layout from Spring 2024 but carry data only from the 2024-2025 "
            "school year (Algebra: Concepts & Connections and American "
            "Literature). Full-Year 2020-2021 uniquely includes "
            "enrolled_tested_rate, reflecting COVID-era participation drops."
        ),
        title="Georgia Milestones End-of-Course (EOC) Results",
        summary=(
            "Georgia Milestones high-school end-of-course test results by "
            "school, district, and subject, 2015-2025."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "description": (
                    "Ending calendar year of the school year (e.g., 2024 = "
                    "school year 2023-2024). Winter administrations are "
                    "stored under the school year they fall inside: Winter "
                    "2014 EOC is the 2014-2015 mid-year retest, stored as "
                    "year=2015."
                ),
                "nullable": False,
                "example": 2024,
            },
            {
                "name": "district_code",
                "type": "string",
                "description": (
                    "3-digit GOSA district/system code (FK to districts "
                    "dimension). School-level rows for State/Commission "
                    "Charter campuses use the 7-digit campus code (system "
                    "782/783 + school code) — 2015-2017 bronze published "
                    "those rows under the bare system code and they are "
                    "promoted here. NULL for state-level rows."
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
                "example": "0103",
            },
            {
                "name": "administration",
                "type": "string",
                "description": (
                    "Which of the three publications a row comes from: "
                    "winter = mid-year retest, spring = primary end-of-year "
                    "administration, full_year = fall+winter+spring "
                    "aggregate. The three slices are distinct cohorts, not "
                    "duplicates."
                ),
                "short_description": (
                    "Which test window the row covers: winter retest, spring "
                    "primary, or the full-year aggregate."
                ),
                "nullable": False,
                "example": "spring",
                "validValues": ["winter", "spring", "full_year"],
            },
            {
                "name": "subject",
                "type": "string",
                "description": (
                    "Snake-case EOC content area. The tested slate changed "
                    "over time: 8-10 subjects through 2020 (incl. 9th Grade "
                    "Literature, Physical Science, Economics, two algebra "
                    "and two geometry courses), 5 from 2021, and 4 from "
                    "2024 (american_literature_and_composition, "
                    "algebra_concepts_and_connections, biology, us_history)."
                    " Full-Year 2020-2021's 8th-grade Physical Science "
                    "administration is folded into physical_science."
                ),
                "short_description": (
                    "The high-school course tested (e.g. biology, us_history, "
                    "american_literature_and_composition)."
                ),
                "nullable": False,
                "example": "biology",
            },
            {
                "name": "num_tested",
                "unit": "count",
                "metric_component": "denominator",
                "type": "int64",
                "description": (
                    "Number of students tested. Never suppressed by the "
                    "source — non-null on every row."
                ),
                "nullable": True,
                "example": 132,
            },
            {
                "name": "avg_scale_score",
                "unit": "score",
                "key_metric": True,
                "value_min": 140,
                "value_max": 820,
                "type": "float64",
                "description": (
                    "Mean scale score on the Georgia Milestones EOC scale. "
                    "Reported scores span roughly 400-650; the contract "
                    "enforces the full published EOC scale range of 140-820 "
                    "(per-course bounds differ; Biology spans the full "
                    "range per the GaDOE EOC Score Interpretation Guide). "
                    "Preserved on its natural scale."
                ),
                "short_description": (
                    "Average end-of-course scale score (about 400-650 in "
                    "practice); higher means stronger performance."
                ),
                "nullable": True,
                "example": 525.3,
            },
            {
                "name": "scale_score_std_dev",
                "type": "float64",
                "description": (
                    "Standard deviation of the scale scores — a dispersion "
                    "measure, NOT a bounded score. Units are scale-score "
                    "points; the value is always >= 0. Exempt from unit/range "
                    "checks (it has no fixed upper bound). Published only by "
                    "Spring 2015 system-level files, Winter 2021 files, and "
                    "every file from Spring 2022 onward; NULL elsewhere."
                ),
                "nullable": True,
                "example": 57.4,
            },
            {
                "name": "pct_beginning_learner",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share of tested students at the Beginning Learner "
                    "level (0-1 scale; bronze 0-100 divided by 100)."
                ),
                "nullable": True,
                "example": 0.2113,
            },
            {
                "name": "pct_developing_learner",
                "unit": "proportion",
                "type": "float64",
                "description": "Share at Developing Learner (0-1 scale).",
                "nullable": True,
                "example": 0.3333,
            },
            {
                "name": "pct_proficient_learner",
                "unit": "proportion",
                "type": "float64",
                "description": "Share at Proficient Learner (0-1 scale).",
                "nullable": True,
                "example": 0.3525,
            },
            {
                "name": "pct_distinguished_learner",
                "unit": "proportion",
                "type": "float64",
                "description": "Share at Distinguished Learner (0-1 scale).",
                "nullable": True,
                "example": 0.1026,
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
                "example": 0.7885,
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
                "example": 0.4551,
            },
            {
                "name": "pct_below_grade_level_lexile",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Reading Status: share of tested students reading below "
                    "the course's Lexile threshold. Populated only for "
                    "literature subjects. The threshold is per course, not "
                    "per year: 9th Grade Literature uses 1050L (reported "
                    "2018-2020) and American Literature 1185L (reported "
                    "2018 onward; the 2018-2020 American Literature files "
                    "label the threshold 1050L in their headers but the "
                    "course moved to 1185L from 2021)."
                ),
                "nullable": True,
                "example": 0.3397,
            },
            {
                "name": "pct_grade_level_or_above_lexile",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Reading Status: share reading at or above the Lexile "
                    "threshold; complement of pct_below_grade_level_lexile. "
                    "Populated only for literature subjects."
                ),
                "nullable": True,
                "example": 0.6603,
            },
            {
                "name": "num_sgp_received",
                "unit": "count",
                "type": "int64",
                "description": (
                    "Number of tested students who received a Student "
                    "Growth Percentile. SGP columns exist in the source "
                    "layout from Spring 2024, but the 2024 Algebra CC "
                    "sheets are empty templates — populated data starts "
                    "with the 2024-2025 school year (year=2025) for "
                    "algebra_concepts_and_connections and "
                    "american_literature_and_composition. NULL elsewhere."
                ),
                "nullable": True,
                "example": 143,
            },
            {
                "name": "sgp_median",
                "unit": "percentile",
                "type": "float64",
                "description": (
                    "Median Student Growth Percentile (1-99 percentile "
                    "rank, preserved on its natural scale per "
                    "data-cleaning-standards §4). Float64 because 2025 "
                    "bronze publishes half-point medians (e.g. 61.5)."
                ),
                "nullable": True,
                "example": 52.0,
            },
            {
                "name": "pct_sgp_low_growth",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share of SGP-scored students in the Low Growth band (0-1 scale)."
                ),
                "nullable": True,
                "example": 0.3287,
            },
            {
                "name": "pct_sgp_typical_growth",
                "unit": "proportion",
                "type": "float64",
                "description": "Share in the Typical Growth band (0-1 scale).",
                "nullable": True,
                "example": 0.3217,
            },
            {
                "name": "pct_sgp_high_growth",
                "unit": "proportion",
                "type": "float64",
                "description": "Share in the High Growth band (0-1 scale).",
                "nullable": True,
                "example": 0.3497,
            },
            {
                "name": "enrolled_tested_rate",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share of enrolled students who actually tested. "
                    "Published ONLY by the Full-Year 2020-2021 files (COVID "
                    "participation year); NULL for every other "
                    "administration."
                ),
                "nullable": True,
                "example": 0.9912,
            },
        ],
        source=(
            "Georgia Insights (GaDOE) — Georgia Milestones End-of-Course Assessment"
        ),
        source_url="https://georgiainsights.gadoe.org/data-downloads/",
        update_frequency="triannual",
        year_range=(year_min, year_max),
        partitioned_by=["year"],
        notes=[
            (
                "Winter administrations are stored under the ending year of "
                "the school year they fall inside (Winter 2014 EOC = school "
                "year 2014-2015 = year 2015)."
            ),
            (
                "Each school year can carry up to three rows per (geography, "
                "subject) — one per administration. They are not duplicates: "
                "winter retesters are a different cohort from spring "
                "primary, and full_year aggregates across fall+winter+spring."
            ),
            (
                "All percent columns are 0-1 decimal scale (bronze ships "
                "0-100). avg_scale_score, scale_score_std_dev, and "
                "sgp_median keep their natural scales."
            ),
            (
                "year=2024 contains no algebra_cc rows: the Spring-2024 and "
                "Full-Year-2023-2024 Algebra CC sheets in the harvested "
                "workbooks are empty templates (header-only, or one all-null "
                "state row). Winter-2024 Algebra CC is populated and lands "
                "under year=2025. GaDOE has published combined Winter+Spring "
                "2024 Algebra CC results elsewhere; ingesting them requires "
                "re-harvesting the bronze workbooks."
            ),
            (
                "Legitimate NULL-rate spikes: SGP metrics are null outside "
                "year=2025 Algebra CC / American Literature; Reading Status "
                "metrics are null outside literature subjects; "
                "scale_score_std_dev is null outside Spring-2015 system "
                "files, Winter-2021, and 2022+; enrolled_tested_rate is null "
                "outside Full-Year 2020-2021."
            ),
            (
                "2014-2016 legacy xls files truncate school names to 13-16 "
                "chars; names never enter the fact table — the schools "
                "dimension sources names from the latest era."
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
                    "The published cumulative pct_developing_learner_or_above "
                    "equals developing + proficient + distinguished "
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
                    "The published cumulative pct_proficient_learner_or_above "
                    "equals proficient + distinguished (+/-0.02) wherever "
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
                    "Lexile threshold) is a complement pair summing to 1.0 "
                    "(+/-0.02) wherever both are present."
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
                "name": "lexile_metrics_only_on_literature_subjects",
                "description": (
                    "Reading Status (Lexile) metrics are published only for "
                    "the two literature courses."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(pct_below_grade_level_lexile IS NOT NULL "
                    "OR pct_grade_level_or_above_lexile IS NOT NULL) "
                    "AND subject NOT IN "
                    "('9th_grade_literature_and_composition', "
                    "'american_literature_and_composition')"
                ),
                "mustBe": 0,
            },
            {
                "name": "sgp_metrics_only_on_sgp_subjects",
                "description": (
                    "SGP metrics are published only for Algebra: Concepts & "
                    "Connections and American Literature (first populated "
                    "data year=2025)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(num_sgp_received IS NOT NULL OR sgp_median IS NOT NULL "
                    "OR pct_sgp_low_growth IS NOT NULL "
                    "OR pct_sgp_typical_growth IS NOT NULL "
                    "OR pct_sgp_high_growth IS NOT NULL) "
                    "AND subject NOT IN ('algebra_concepts_and_connections', "
                    "'american_literature_and_composition')"
                ),
                "mustBe": 0,
            },
            {
                "name": "enrolled_tested_rate_only_in_full_year_2021",
                "description": (
                    "enrolled_tested_rate is a COVID-era column published "
                    "only by the Full-Year 2020-2021 files."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "enrolled_tested_rate IS NOT NULL "
                    "AND NOT (administration = 'full_year' AND year = 2021)"
                ),
                "mustBe": 0,
            },
            {
                "name": "num_tested_never_null",
                "description": (
                    "The source never suppresses the tested count — every "
                    "surviving gold row carries num_tested (rows with no "
                    "metrics at all are filtered as template residue)."
                ),
                "dimension": "completeness",
                "query": ("SELECT COUNT(*) FROM {object} WHERE num_tested IS NULL"),
                "mustBe": 0,
            },
            {
                "name": "sgp_count_within_tested",
                "description": (
                    "num_sgp_received never exceeds num_tested — SGP "
                    "recipients are a subset of tested students. Verified "
                    "on all 3,590 SGP-bearing rows in bronze."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE num_sgp_received "
                    "IS NOT NULL AND num_tested IS NOT NULL AND "
                    "num_sgp_received > num_tested"
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
