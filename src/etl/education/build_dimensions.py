"""Build education dimension tables (districts and schools) from bronze data.

Scans GOSA bronze (Era 3+, 2011 onward) and Georgia Insights bronze to extract
district and school information, then produces:
  - data/gold/education/_dimensions/districts.parquet
  - data/gold/education/_dimensions/schools.parquet

Pre-2011 GOSA bronze (Era 1/2) is scanned for both schools (school-level
rows) and districts (district aggregate rows where ``school == "ALL"``).
Pre-2011 records are applied to each dimension as a **fallback only** —
codes already present in Era 3+ keep their canonical modern name (so
"Atlanta Public Schools" is never overridden by the older "Atlanta City").
The fallback recovers entities that closed before 2011, including charter
districts like 795 (CCAT), 796 (Odyssey), 797 (KidsPeace), and 798
(Mountain Education Center). Pre-2011 schools use a compound
``SysSchoolID`` of the form ``"<system>:<school>"`` where ``school == "ALL"``
indicates a district aggregate row.

Hard-coded district entries are applied for sentinel agencies that report
under a district code but never appear in GOSA bronze under that code with a
clean name (e.g., Department of Corrections, Department of Human Resources).

Usage:
    uv run python -m src.etl.education.build_dimensions
"""

import csv
import io
import logging
import re
import zipfile
from pathlib import Path

import pandas as pd
import polars as pl

from src.utils.crosswalks import add_census_district_code
from src.utils.dimension_contract_emitter import (
    emit_districts_contract,
    emit_schools_contract,
)
from src.utils.readers import (
    extract_year_from_filename,
    list_bronze_files,
    read_bronze_file,
)
from src.utils.transformers import title_case_name

logger = logging.getLogger(__name__)

GOSA_BRONZE_ROOT = Path("data/bronze/education/gosa")
GEORGIA_INSIGHTS_BRONZE_ROOT = Path("data/bronze/education/georgiainsights")
OUTPUT_DIR = Path("data/gold/education/_dimensions")

# District code column names across eras and topics.
#
# Several Era 3+ topics ship bronze with non-canonical headers that the
# dim build must still pick up so the schools/districts dims contain every
# (district_code, school_code) pair the topic transforms emit. Examples
# observed in bronze (2011-2024):
#   • SCHOOL_DISTRCT_CD          — canonical Era 3 (most topics, 2011-2023)
#   • SCHOOL_DSTRCT_CD           — Era 4 rename (most topics, 2024+; missing the 'I')
#   • DISTRICT_CODE              — revenues_and_expenditures (2011-2022)
#   • School District Code       — retained_students (2011-2022)
#   • School_District_Code       — retained_students (2023-2024, underscore-separated)
#   • SYSTEM_ID                  — direct_certification_* (2014-2016)
#
# Same idea for district name, school code, and school name — each topic
# has its own conventions. The scanner tries each alias in order and uses
# the first one it finds. Sentinel/aggregate rows (school_code in
# SCHOOL_SENTINELS, district_code in DISTRICT_SENTINELS) are filtered out
# downstream regardless of which column name was used.
DISTRICT_CODE_COLUMNS = [
    "SCHOOL_DISTRCT_CD",
    "SCHOOL_DSTRCT_CD",
    "DISTRICT_CODE",
    "School District Code",
    "School_District_Code",
    "SYSTEM_ID",
]

# District name column variants.
DISTRICT_NAME_COLUMNS = [
    "SCHOOL_DSTRCT_NM",
    "DISTRICT_NAME",
    "School District Name",
    "School_District_Name",
    "SYSTEM_NAME",
]

# School code column variants.
SCHOOL_CODE_COLUMNS = [
    "INSTN_NUMBER",
    "SCHOOL_CODE",
    "School Code",
    "School_Code",
    "SCHOOL_ID",
]

# School name column variants.
SCHOOL_NAME_COLUMNS = [
    "INSTN_NAME",
    "SCHOOL_NAME",
    "School Name",
    "School_Name",
]

# Compound district+school ID column names used by GOSA Era 1/2 (pre-2011)
# bronze. Format is ``"<system>:<school>"`` where school is "ALL" for
# district aggregates. Multiple capitalizations exist; check all.
PRE2011_COMPOUND_ID_COLUMNS = [
    "SysSchoolID",
    "SysSchoolid",
    "SysSchoolId",
    "SYSSCHOOLID",
    "ID",
]

# School name column variants in pre-2011 bronze.
PRE2011_SCHOOL_NAME_COLUMNS = [
    "School Name",
    "SchoolName",
    "SchoolNme",
    "schoolname",
]

# District (system) name column variants in pre-2011 bronze. Only some
# pre-2011 sources carry this — most omit it.
PRE2011_DISTRICT_NAME_COLUMNS = [
    "System Name",
    "systemname",
    "SystemName",
]

# Sentinel values in school_code that indicate aggregate rows, not real schools.
# Compared after upstream uppercasing, so entries here must be uppercase.
SCHOOL_SENTINELS = {"ALL", "SCHOOL_ALL", "9999", "0000"}

# Some bronze files publish unused "placeholder" school codes with a trailing
# `x` (e.g., `2052X`, `3060X`, `4752X`, `4050X`, `3055X`). None of these are
# referenced by any fact table — they survive as dimension pollution. Drop
# any code that ends in `X` after uppercasing.
SCHOOL_CODE_X_SUFFIX_RE = re.compile(r"X$")

# Sentinel values in district_code/name that indicate aggregate rows, not real
# districts. Compared after upstream uppercasing.
DISTRICT_SENTINELS = {
    "ALL",
    "ALL SYSTEMS",
    "DISTRICT_ALL",
    "STATE OF GEORGIA",
    "STATEWIDE",
}

# District type classification by GOSA code prefix.
# Standard districts use 3-digit codes; charter and specialty schools use 7-digit codes.
DISTRICT_TYPE_RULES: list[tuple[str, str]] = [
    ("782", "state_charter"),
    ("783", "commission_charter"),
    ("799", "state_school"),
]

# Explicit district_type for specific 3-digit agency codes that the prefix
# rules would otherwise misclassify as `standard`. These are real GOSA
# reporting entities that are NOT Census-matchable school districts, so
# leaving them typed `standard` (a) mislabels them in the public API and
# (b) drags the standard-district Census match rate below the >95% target
# (they legitimately have no `district_census_id`). Pulling them out of
# `standard` makes `standard` mean "Census-matchable school district"
# (match rate ~100%) and gives consumers an honest `district_type`.
#
#   - `resa`  — Regional Educational Service Agencies (16 service agencies
#               in the 850-888 range; not districts, no Census ID).
#   - `state_agency` — state agencies that report education programs under a
#               district code but are not themselves schools (Depts. of
#               Juvenile Justice / Labor here; Depts. of Corrections (890)
#               and Human Resources (892) carry the same type via
#               HARDCODED_DISTRICTS). Distinct from `state_school`, which is
#               reserved for the 799-prefix Georgia state schools (Deaf /
#               Blind).
#   - `state_charter` / `state_special` — legacy charter and residential
#               special schools that predate the 782/783 charter numbering.
#
# Codes are matched after zfill(3). Verified against the live dimension on
# 2026-06-01: these are exactly the 24 `standard`-typed rows with a NULL
# district_census_id.
DISTRICT_TYPE_OVERRIDES: dict[str, str] = {
    # Regional Educational Service Agencies (RESAs)
    "850": "resa",  # Northwest Georgia RESA
    "852": "resa",  # North Georgia RESA
    "854": "resa",  # Pioneer RESA
    "856": "resa",  # Metro RESA
    "858": "resa",  # Northeast Georgia RESA
    "860": "resa",  # West Georgia RESA
    "862": "resa",  # Griffin RESA
    "864": "resa",  # Middle Georgia RESA
    "866": "resa",  # Oconee RESA
    "868": "resa",  # Central Savannah River RESA
    "872": "resa",  # Chattahoochee-Flint RESA
    "876": "resa",  # Heart of Georgia RESA
    "880": "resa",  # First District RESA
    "884": "resa",  # Southwest Georgia RESA
    "886": "resa",  # Coastal Plains RESA
    "888": "resa",  # Okefenokee RESA
    # State agencies reporting education data under a district code (not
    # schools themselves) — grouped under `state_agency` with the
    # HARDCODED_DISTRICTS Depts. of Corrections (890) / Human Resources (892).
    "891": "state_agency",  # Department of Juvenile Justice
    "896": "state_agency",  # Department of Labor
    # Legacy charter / special schools (pre-782/783 numbering)
    "768": "state_charter",  # Ivy Prep
    "770": "state_charter",  # Scholars Academy
    "795": "state_charter",  # Charter Conservatory for Arts and Technology
    "796": "state_charter",  # Odyssey
    "798": "state_charter",  # Mountain Education Center
    "797": "state_special",  # KidsPeace (residential treatment facility)
}

# Hard-coded district entries for state agencies that report under a
# district code but appear inconsistently in bronze. These take precedence
# over bronze-derived names if a code collision occurs.
#
# Schema: district_code -> (district_name, district_census_id, district_type)
HARDCODED_DISTRICTS: dict[str, tuple[str, str | None, str]] = {
    # Department of Corrections operates education programs in state
    # prisons. Appears in Georgia Insights enrollment files (FY2011+) and
    # in numerous derived gold facts but never in GOSA bronze under code
    # 890 with a clean district name. Typed `state_agency` (a state agency
    # running education programs, not a school) alongside DJJ/DOL.
    "890": ("Department of Corrections", None, "state_agency"),
    # Department of Human Resources historically operated youth detention
    # education programs. Appears in 2011-2017 Georgia Insights enrollment
    # files only. Typed `state_agency` (see Dept. of Corrections above).
    "892": ("Department of Human Resources", None, "state_agency"),
    # Residential Treatment Center — a state-managed aggregate covering
    # students educated in residential treatment facilities across Georgia.
    # Appears in GOSA CCRPI bronze (content_mastery 2015-2017,
    # graduation_rate 2015-2018) as a non-numeric pseudo-district code.
    # Classified as `state_special` to distinguish from numeric GOSA
    # district codes — this is the canonical home for non-numeric pseudo-
    # district aggregates.
    "RTC": ("Residential Treatment Center", None, "state_special"),
}

# Allowlist of non-numeric pseudo-district codes that survive the post-
# build length guard. Add a code here ONLY when it also appears in
# HARDCODED_DISTRICTS with an explicit district_type — this is the single
# place to document non-3/7-digit codes.
PSEUDO_DISTRICT_CODES: set[str] = {"RTC"}


def _detect_col(columns: list[str], candidates: list[str]) -> str | None:
    """Find the first matching column name in a DataFrame's columns.

    Args:
        columns: List of column names from the bronze file.
        candidates: List of accepted column-name aliases in priority order.

    Returns:
        The matching column name, or None if no alias is present.
    """
    column_set = set(columns)
    for col in candidates:
        if col in column_set:
            return col
    return None


def _detect_district_code_col(columns: list[str]) -> str | None:
    """Find the district code column name in a DataFrame's columns."""
    return _detect_col(columns, DISTRICT_CODE_COLUMNS)


def _classify_district_type(code: str) -> str:
    """Classify a district by its GOSA code.

    Explicit per-code overrides (RESAs, state agencies, legacy charter /
    special schools) win over the prefix rules so genuine non-districts are
    not emitted as `standard`. Falls back to the code-prefix rules, then to
    `standard`.

    Args:
        code: GOSA district code string (zfill(3)-normalized).

    Returns:
        District type string.
    """
    if code in DISTRICT_TYPE_OVERRIDES:
        return DISTRICT_TYPE_OVERRIDES[code]
    for prefix, district_type in DISTRICT_TYPE_RULES:
        if code.startswith(prefix):
            return district_type
    return "standard"


def scan_bronze_entities() -> pl.DataFrame:
    """Scan all GOSA bronze files to collect district and school entities.

    Only processes Era 3+ files (2011 onward). Header conventions vary by
    topic and year, so for each column slot (district_code, district_name,
    school_code, school_name) the scanner tries every alias listed in the
    module-level ``*_COLUMNS`` lists and uses the first one it finds.
    Earlier eras use a compound ``SysSchoolID`` column and are handled by
    ``scan_pre2011_gosa_schools``/``scan_pre2011_gosa_districts``.

    A file is included if it has at least a district code column and a
    district name column. School code/name are optional — many topics are
    district- or state-level only.

    Returns:
        DataFrame with columns: district_code, district_name, school_code,
        school_name, year.
    """
    all_records: list[pl.DataFrame] = []

    topic_dirs = sorted(d for d in GOSA_BRONZE_ROOT.iterdir() if d.is_dir())
    logger.info(f"Scanning {len(topic_dirs)} GOSA topics for dimension data")

    for topic_dir in topic_dirs:
        files = list_bronze_files(topic_dir)
        for path in files:
            year = extract_year_from_filename(path.name)
            if year is None or year < 2011:
                continue

            try:
                df = read_bronze_file(path)
            except Exception as e:
                logger.warning(f"Failed to read {path}: {e}")
                continue

            # Detect each column slot independently so that topics with
            # non-canonical headers (e.g., revenues_and_expenditures uses
            # DISTRICT_CODE/SCHOOL_CODE/DISTRICT_NAME/SCHOOL_NAME for
            # 2011-2022; retained_students uses "School District Code"
            # style headers) still contribute their entities.
            district_code_col = _detect_col(df.columns, DISTRICT_CODE_COLUMNS)
            district_name_col = _detect_col(df.columns, DISTRICT_NAME_COLUMNS)
            if district_code_col is None or district_name_col is None:
                continue

            school_code_col = _detect_col(df.columns, SCHOOL_CODE_COLUMNS)
            school_name_col = _detect_col(df.columns, SCHOOL_NAME_COLUMNS)
            has_school = school_code_col is not None and school_name_col is not None

            # Extract relevant columns, renaming to standard names
            select_exprs = [
                pl.col(district_code_col)
                .cast(pl.Utf8)
                .str.strip_chars()
                .alias("district_code"),
                pl.col(district_name_col)
                .cast(pl.Utf8)
                .str.strip_chars()
                .alias("district_name"),
                pl.lit(year).cast(pl.Int32).alias("year"),
            ]

            if has_school:
                select_exprs.extend(
                    [
                        pl.col(school_code_col)
                        .cast(pl.Utf8)
                        .str.strip_chars()
                        .alias("school_code"),
                        pl.col(school_name_col)
                        .cast(pl.Utf8)
                        .str.strip_chars()
                        .alias("school_name"),
                    ]
                )
            else:
                select_exprs.extend(
                    [
                        pl.lit(None).cast(pl.Utf8).alias("school_code"),
                        pl.lit(None).cast(pl.Utf8).alias("school_name"),
                    ]
                )

            extracted = df.select(select_exprs)
            all_records.append(extracted)

    if not all_records:
        raise ValueError("No bronze files found with expected columns")

    combined = pl.concat(all_records)
    logger.info(f"Collected {combined.height:,} raw entity records from bronze files")
    return combined


def scan_pre2011_gosa_schools() -> pl.DataFrame | None:
    """Scan pre-2011 GOSA bronze for the schools dimension only.

    Pre-2011 GOSA files use a compound ``SysSchoolID`` column of the form
    ``"<system>:<school>"`` where ``school == "ALL"`` is a district
    aggregate row. School names are in one of several columns
    (``School Name``, ``SchoolName``, ``SchoolNme``, ``schoolname``).

    These years are scanned for the school dim. District-aggregate rows
    (``school == "ALL"``) are skipped here and harvested separately by
    ``scan_pre2011_gosa_districts``; both are applied to their respective
    dims as fallbacks only, so canonical Era 3+ names always win for codes
    that exist in both eras (e.g., "Atlanta Public Schools" is preserved
    over the older "Atlanta City"). Pre-2011 schools are added when their
    composite key is not already present in the Era 3+ scan, providing a
    fallback for schools that closed before 2011.

    Returns:
        DataFrame with columns: ``district_code``, ``school_code``,
        ``school_name``, ``year``. ``district_name`` is intentionally
        omitted — pre-2011 sources may carry a system name but it is not
        used for the districts dim. Returns None if no records were found.
    """
    all_records: list[pl.DataFrame] = []

    topic_dirs = sorted(d for d in GOSA_BRONZE_ROOT.iterdir() if d.is_dir())

    for topic_dir in topic_dirs:
        files = list_bronze_files(topic_dir)
        for path in files:
            year = extract_year_from_filename(path.name)
            if year is None or year >= 2011:
                continue

            try:
                df = read_bronze_file(path)
            except Exception as e:
                logger.warning(f"Failed to read pre-2011 {path}: {e}")
                continue

            # Detect compound ID column for this file's variant
            id_col = next(
                (c for c in PRE2011_COMPOUND_ID_COLUMNS if c in df.columns),
                None,
            )
            if id_col is None:
                continue

            # Detect school name column variant
            name_col = next(
                (c for c in PRE2011_SCHOOL_NAME_COLUMNS if c in df.columns),
                None,
            )
            if name_col is None:
                continue

            try:
                # Parse compound ID into (district_code, school_code).
                # Skip rows where the school component is "ALL" — those
                # are district aggregates and don't belong in the school
                # dim. Bronze rows with a missing/empty ``school_name`` are
                # kept and back-filled with a stable placeholder name so
                # the (district_code, school_code) pair is still present
                # in the schools dim — topic fact tables otherwise produce
                # orphan FKs that silently break API joins. Mirrors the
                # ``HARDCODED_DISTRICTS`` precedent: fact rows stay clean,
                # dim absorbs the messiness.
                #
                # Note on the validity filter: a handful of pre-2011 CSV
                # files have parser-corruption rows where the compound ID
                # split produces strings with commas/quotes/etc. We require
                # district_code to look like a normal numeric district
                # code (1-7 digits, optionally with a hyphen for the 2015
                # ``782-0410`` charter shape) and school_code to start
                # with at least one digit (real bronze sometimes carries a
                # legitimate trailing alphanumeric tag like ``2052x``).
                ext = (
                    df.select([id_col, name_col])
                    .with_columns(
                        pl.col(id_col).cast(pl.Utf8).str.strip_chars().alias("_id"),
                        pl.col(name_col)
                        .cast(pl.Utf8)
                        .str.strip_chars()
                        .alias("school_name"),
                    )
                    .filter(pl.col("_id").str.contains(":"))
                    .with_columns(
                        pl.col("_id").str.split(":").list.get(0).alias("district_code"),
                        pl.col("_id").str.split(":").list.get(1).alias("school_code"),
                    )
                    .filter(
                        pl.col("school_code").is_not_null()
                        & ~pl.col("school_code")
                        .str.to_uppercase()
                        .is_in(SCHOOL_SENTINELS)
                        # Reject parser-corruption rows whose codes don't
                        # match the expected shape.
                        & pl.col("district_code").str.contains(r"^\d{1,7}(-\d+)?$")
                        & pl.col("school_code").str.contains(r"^\d+[A-Za-z]?$")
                        # Reject rows whose school_code becomes a sentinel
                        # after zfill (e.g. bronze ``069:0`` → ``0000``).
                        & ~pl.col("school_code")
                        .str.zfill(4)
                        .str.to_uppercase()
                        .is_in(SCHOOL_SENTINELS)
                    )
                    .with_columns(
                        # Back-fill null/empty school names with a stable
                        # placeholder so the composite key is preserved.
                        pl.when(
                            pl.col("school_name").is_null()
                            | (pl.col("school_name").str.len_chars() == 0)
                        )
                        .then(
                            pl.format(
                                "Unknown School {} ({})",
                                pl.col("school_code"),
                                pl.col("district_code"),
                            )
                        )
                        .otherwise(pl.col("school_name"))
                        .alias("school_name")
                    )
                    .select(["district_code", "school_code", "school_name"])
                    .with_columns(pl.lit(year).cast(pl.Int32).alias("year"))
                )
                if ext.height > 0:
                    all_records.append(ext)
            except Exception as e:
                logger.debug(f"Pre-2011 parse failed for {path}: {e}")
                continue

    if not all_records:
        logger.info("Pre-2011 GOSA scan: no school records extracted")
        return None

    combined = pl.concat(all_records, how="diagonal")
    logger.info(
        f"Pre-2011 GOSA scan: collected {combined.height:,} school records "
        f"from years 2004-2010"
    )
    return combined


def scan_pre2011_gosa_districts() -> pl.DataFrame | None:
    """Scan pre-2011 GOSA bronze for district aggregate rows.

    Pre-2011 GOSA files carry a compound ``SysSchoolID`` of the form
    ``"<system>:<school>"`` where ``school == "ALL"`` indicates a district
    aggregate row. The district name on those aggregate rows lives in the
    same school-name column variant (``School Name`` / ``SchoolName`` /
    ``SchoolNme`` / ``schoolname``).

    Used as a **fallback only** by ``build_districts`` — codes already
    present in Era 3+ keep their canonical modern name, so this never
    overrides "Atlanta Public Schools" with the older "Atlanta City". It
    fills in pre-2011-only districts (e.g., 795 CCAT, 796 Odyssey,
    797 KidsPeace, 798 Mountain Education Center) that closed or merged
    before Era 3+ began.

    Returns:
        DataFrame with columns: ``district_code``, ``district_name``,
        ``year``. Returns None if no records were found.
    """
    all_records: list[pl.DataFrame] = []

    topic_dirs = sorted(d for d in GOSA_BRONZE_ROOT.iterdir() if d.is_dir())

    for topic_dir in topic_dirs:
        files = list_bronze_files(topic_dir)
        for path in files:
            year = extract_year_from_filename(path.name)
            if year is None or year >= 2011:
                continue

            try:
                df = read_bronze_file(path)
            except Exception as e:
                logger.warning(f"Failed to read pre-2011 {path}: {e}")
                continue

            id_col = next(
                (c for c in PRE2011_COMPOUND_ID_COLUMNS if c in df.columns),
                None,
            )
            if id_col is None:
                continue

            # The district name on aggregate rows lives in the school-name
            # column variant. Prefer an explicit system-name column when
            # the file carries one.
            name_col = next(
                (c for c in PRE2011_DISTRICT_NAME_COLUMNS if c in df.columns),
                None,
            )
            if name_col is None:
                name_col = next(
                    (c for c in PRE2011_SCHOOL_NAME_COLUMNS if c in df.columns),
                    None,
                )
            if name_col is None:
                continue

            try:
                ext = (
                    df.select([id_col, name_col])
                    .with_columns(
                        pl.col(id_col).cast(pl.Utf8).str.strip_chars().alias("_id"),
                        pl.col(name_col)
                        .cast(pl.Utf8)
                        .str.strip_chars()
                        .alias("district_name"),
                    )
                    .filter(pl.col("_id").str.contains(":"))
                    .with_columns(
                        pl.col("_id").str.split(":").list.get(0).alias("district_code"),
                        pl.col("_id").str.split(":").list.get(1).alias("school_code"),
                    )
                    # Keep only district-aggregate rows (school component = "ALL").
                    .filter(
                        pl.col("school_code").str.to_uppercase().is_in(SCHOOL_SENTINELS)
                        & pl.col("district_code").is_not_null()
                        & (pl.col("district_code").str.len_chars() > 0)
                        & ~pl.col("district_code")
                        .str.to_uppercase()
                        .is_in(DISTRICT_SENTINELS)
                        & pl.col("district_name").is_not_null()
                        & (pl.col("district_name").str.len_chars() > 0)
                    )
                    .select(["district_code", "district_name"])
                    .with_columns(pl.lit(year).cast(pl.Int32).alias("year"))
                )
                if ext.height > 0:
                    all_records.append(ext)
            except Exception as e:
                logger.debug(f"Pre-2011 districts parse failed for {path}: {e}")
                continue

    if not all_records:
        logger.info("Pre-2011 GOSA districts scan: no records extracted")
        return None

    combined = pl.concat(all_records, how="diagonal")
    logger.info(
        f"Pre-2011 GOSA districts scan: collected {combined.height:,} district "
        f"aggregate records from years 2004-2010"
    )
    return combined


# Canonical header names for Georgia Insights bronze columns. Bronze headers
# are normalized via _canon_gi_col (uppercase + whitespace collapsed) before
# lookup. Multiple names per slot because sub_topics use different conventions
# (EOC uses "System Code", CCRPI uses "System ID", etc.).
_GI_DISTRICT_CODE_HEADERS = ("SYSTEM CODE", "SYSTEM ID")
_GI_SCHOOL_CODE_HEADERS = ("SCHOOL CODE", "SCHOOL ID")
_GI_DISTRICT_NAME_HEADERS = ("SYSTEM NAME",)
_GI_SCHOOL_NAME_HEADERS = ("SCHOOL NAME",)
# Some Spring 2016 EOC school files ship a single compound 7-digit "Key"
# column (system_code * 10000 + school_code) instead of separate code columns.
_GI_COMPOUND_KEY_HEADERS = ("KEY",)

# Header row offsets to try when reading a Georgia Insights sheet. EOC files
# have a title on row 0 and the real header on row 1 (single) or rows 1-2
# (multi-row, 2024+). CCRPI files have the header on row 0. We try each
# offset and keep the first one whose columns match an expected code header.
_GI_HEADER_TRIES: tuple[int | list[int], ...] = (1, [1, 2], 0)


def _canon_gi_col(col) -> str:
    """Canonicalize a Georgia Insights bronze column name.

    For multi-row headers, pandas returns tuples; take the last level (the
    leaf header) and fold to uppercase with whitespace collapsed.
    """
    if isinstance(col, tuple):
        col = col[-1]
    return " ".join(str(col).upper().split())


def _extract_gi_entities_from_pdf(pdf: pd.DataFrame, year: int) -> pl.DataFrame | None:
    """Extract entity records from a single Georgia Insights sheet.

    Returns None if the sheet has no recognizable code columns (common for
    state-only files where the only subject identifier is "Content Area").
    """
    if pdf.empty:
        return None

    # Flatten all column names to canonical uppercase strings before handing
    # to polars. Pandas multi-row headers produce MultiIndex columns (tuples)
    # which polars cannot address by lookup; taking the leaf level here
    # standardizes single-row and multi-row headers to the same shape.
    pdf = pdf.copy()
    pdf.columns = [_canon_gi_col(c) for c in pdf.columns]
    # Drop duplicate canonical names (rare but possible when two leaves
    # collide after canonicalization, e.g. empty "Unnamed" siblings).
    pdf = pdf.loc[:, ~pd.Index(pdf.columns).duplicated()]

    canonical_cols = set(pdf.columns)

    dist_code_col = next(
        (h for h in _GI_DISTRICT_CODE_HEADERS if h in canonical_cols), None
    )
    compound_key_col = next(
        (h for h in _GI_COMPOUND_KEY_HEADERS if h in canonical_cols), None
    )
    if dist_code_col is None and compound_key_col is None:
        return None

    sch_code_col = next(
        (h for h in _GI_SCHOOL_CODE_HEADERS if h in canonical_cols), None
    )
    dist_name_col = next(
        (h for h in _GI_DISTRICT_NAME_HEADERS if h in canonical_cols), None
    )
    sch_name_col = next(
        (h for h in _GI_SCHOOL_NAME_HEADERS if h in canonical_cols), None
    )

    df = pl.from_pandas(pdf.astype(str))

    if compound_key_col is not None and dist_code_col is None:
        # Compound 7-digit key → 3-digit district + 4-digit school.
        df = df.with_columns(
            pl.col(compound_key_col).str.strip_chars().alias("_key_raw")
        )
        df = df.filter(pl.col("_key_raw").str.len_chars() == 7)
        df = df.with_columns(
            pl.col("_key_raw").str.slice(0, 3).alias("district_code"),
            pl.col("_key_raw").str.slice(3, 4).alias("school_code"),
        )
    else:
        df = df.with_columns(
            pl.col(dist_code_col).str.strip_chars().alias("district_code")
        )
        if sch_code_col is not None:
            df = df.with_columns(
                pl.col(sch_code_col).str.strip_chars().alias("school_code")
            )
        else:
            df = df.with_columns(pl.lit(None).cast(pl.Utf8).alias("school_code"))

    df = df.with_columns(
        (
            pl.col(dist_name_col).str.strip_chars()
            if dist_name_col is not None
            else pl.lit(None).cast(pl.Utf8)
        ).alias("district_name"),
        (
            pl.col(sch_name_col).str.strip_chars()
            if sch_name_col is not None
            else pl.lit(None).cast(pl.Utf8)
        ).alias("school_name"),
        pl.lit(year).cast(pl.Int32).alias("year"),
    )

    df = df.select(
        ["district_code", "district_name", "school_code", "school_name", "year"]
    )

    # Drop the "nan" strings that come from pandas.astype(str) on NaN cells.
    for col in ("district_code", "district_name", "school_code", "school_name"):
        df = df.with_columns(
            pl.when(pl.col(col).str.to_lowercase().is_in(["nan", "none", ""]))
            .then(None)
            .otherwise(pl.col(col))
            .alias(col)
        )

    # Filter out aggregate/sentinel rows and obviously-invalid district codes.
    df = df.filter(
        pl.col("district_code").is_not_null()
        & ~pl.col("district_code").str.to_uppercase().is_in(DISTRICT_SENTINELS)
    )

    return df if df.height > 0 else None


def _read_gi_sheets(
    source: Path | io.BytesIO, label: str
) -> dict[str, pd.DataFrame] | None:
    """Read every sheet in a Georgia Insights Excel file.

    Tries each header offset in _GI_HEADER_TRIES and returns the first result
    whose first sheet contains an expected code column. Returns None if no
    offset produces recognizable columns.
    """
    for header in _GI_HEADER_TRIES:
        try:
            sheets = pd.read_excel(source, sheet_name=None, header=header, dtype=str)
        except Exception as e:
            logger.debug(f"Failed to read {label} with header={header}: {e}")
            if isinstance(source, io.BytesIO):
                source.seek(0)
            continue

        # Check whether any sheet has a recognizable code header.
        for pdf in sheets.values():
            canonical = {_canon_gi_col(c) for c in pdf.columns}
            if canonical & (
                set(_GI_DISTRICT_CODE_HEADERS) | set(_GI_COMPOUND_KEY_HEADERS)
            ):
                return sheets
        if isinstance(source, io.BytesIO):
            source.seek(0)

    return None


def _read_gi_csv(path: Path) -> pd.DataFrame | None:
    """Read a Georgia Insights CSV file with multi-line header tolerance.

    GI enrollment CSVs typically begin with 3-4 preamble lines (e.g., a
    title row, a sub-title, a date row, an empty separator) before the
    real header line. The header line is the first line that begins with
    a recognized code column name (e.g., "System ID,") possibly preceded
    by a quote.

    Returns:
        A pandas DataFrame, or None if no recognizable header was found
        within the first 20 lines.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.debug(f"Failed to read GI CSV {path}: {e}")
        return None

    lines = text.split("\n")
    header_row = None
    for i, line in enumerate(lines[:20]):
        # Use the csv module to parse the first row tokens robustly
        # (handles quoted values like "System ID","System Name",...).
        try:
            first_tokens = next(csv.reader([line]))
        except Exception:
            continue
        canonical_first = {_canon_gi_col(t) for t in first_tokens}
        if canonical_first & (
            set(_GI_DISTRICT_CODE_HEADERS) | set(_GI_COMPOUND_KEY_HEADERS)
        ):
            header_row = i
            break

    if header_row is None:
        return None

    try:
        # ``skiprows`` (not ``header``) is correct here because preamble
        # rows often have a single un-quoted text cell whose width
        # mismatches the real header row's column count, which confuses
        # pandas's column-count alignment when ``header`` is used alone.
        return pd.read_csv(
            io.StringIO(text),
            skiprows=header_row,
            dtype=str,
            on_bad_lines="skip",
        )
    except Exception as e:
        logger.debug(f"Pandas CSV read failed for {path}: {e}")
        return None


def scan_georgia_insights_entities() -> pl.DataFrame | None:
    """Scan all Georgia Insights Excel/zip bronze files for district/school entities.

    Walks every sub_topic under ``GEORGIA_INSIGHTS_BRONZE_ROOT``, reads each
    xls/xlsx (and inner sheets within zip archives), and extracts
    identifier + name records for dimensions. Files whose headers do not
    match any expected code column are skipped silently — they are assumed
    to be state-only or non-geography-keyed topics.

    CSV files are NOT included here — they are scanned separately by
    ``scan_georgia_insights_csv_fallback`` and used only as a fallback for
    codes not otherwise present in the dim. This preserves the historical
    "State Charter Schools-" naming for charter codes that have since been
    rebranded by GADOE to "State Specialty Schools I-" in the FTE
    enrollment CSVs (older bronze for other topics still references the
    old names, and the rename would otherwise break name-based matching
    in those topics' transforms).

    Returns None if the directory does not exist or no entities were
    extracted; callers should tolerate None to allow dimension rebuilds to
    proceed from GOSA alone.
    """
    if not GEORGIA_INSIGHTS_BRONZE_ROOT.exists():
        return None

    all_records: list[pl.DataFrame] = []
    files_scanned = 0
    files_skipped = 0

    topic_dirs = [
        d for d in sorted(GEORGIA_INSIGHTS_BRONZE_ROOT.rglob("*")) if d.is_dir()
    ]
    logger.info(
        f"Scanning Georgia Insights bronze under {GEORGIA_INSIGHTS_BRONZE_ROOT}"
    )

    for topic_dir in topic_dirs:
        for path in sorted(topic_dir.iterdir()):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix not in (".xls", ".xlsx", ".zip"):
                continue

            year = extract_year_from_filename(path.name)
            if year is None:
                continue

            files_scanned += 1

            if suffix == ".zip":
                try:
                    with zipfile.ZipFile(path) as zf:
                        for inner_name in zf.namelist():
                            if not inner_name.lower().endswith((".xls", ".xlsx")):
                                continue
                            with zf.open(inner_name) as fh:
                                buf = io.BytesIO(fh.read())
                            label = f"{path.name}:{inner_name}"
                            sheets = _read_gi_sheets(buf, label)
                            if sheets is None:
                                files_skipped += 1
                                continue
                            for pdf in sheets.values():
                                rec = _extract_gi_entities_from_pdf(pdf, year)
                                if rec is not None:
                                    all_records.append(rec)
                except zipfile.BadZipFile as e:
                    logger.warning(f"Bad zip {path}: {e}")
                    files_skipped += 1
                continue

            sheets = _read_gi_sheets(path, path.name)
            if sheets is None:
                files_skipped += 1
                continue
            for pdf in sheets.values():
                rec = _extract_gi_entities_from_pdf(pdf, year)
                if rec is not None:
                    all_records.append(rec)

    if not all_records:
        logger.info(
            f"Georgia Insights scan: no entities extracted "
            f"({files_scanned} files scanned, {files_skipped} skipped)"
        )
        return None

    combined = pl.concat(all_records)
    logger.info(
        f"Georgia Insights scan: collected {combined.height:,} raw entity "
        f"records from {files_scanned} files ({files_skipped} skipped)"
    )
    return combined


def scan_georgia_insights_csv_fallback() -> pl.DataFrame | None:
    """Scan Georgia Insights CSV bronze files (used as a fallback only).

    GI CSVs (FTE Enrollment series, etc.) carry district/school identifiers
    that the Excel/zip scanner doesn't see — most importantly the
    Department of Corrections (890) and Department of Human Resources (892)
    sentinel agencies, which never appear with clean district names in
    GOSA bronze. They also carry rebranded charter names ("State Specialty
    Schools I-…") that DIFFER from the historical names other topics'
    bronze still uses ("State Charter Schools-…").

    To avoid breaking name-based matching in transforms that consume older
    bronze, the caller should treat this DataFrame as a supplement only:
    add codes that are missing from the primary scan, never overwrite
    existing entries.

    Returns:
        DataFrame with columns: ``district_code``, ``district_name``,
        ``school_code``, ``school_name``, ``year``. Returns None if the
        directory does not exist or no entities were extracted.
    """
    if not GEORGIA_INSIGHTS_BRONZE_ROOT.exists():
        return None

    all_records: list[pl.DataFrame] = []
    files_scanned = 0
    files_skipped = 0

    topic_dirs = [
        d for d in sorted(GEORGIA_INSIGHTS_BRONZE_ROOT.rglob("*")) if d.is_dir()
    ]

    for topic_dir in topic_dirs:
        for path in sorted(topic_dir.iterdir()):
            if not path.is_file() or path.suffix.lower() != ".csv":
                continue

            year = extract_year_from_filename(path.name)
            if year is None:
                continue

            files_scanned += 1
            pdf = _read_gi_csv(path)
            if pdf is None:
                files_skipped += 1
                continue
            rec = _extract_gi_entities_from_pdf(pdf, year)
            if rec is not None:
                all_records.append(rec)

    if not all_records:
        logger.info(
            f"Georgia Insights CSV fallback: no entities extracted "
            f"({files_scanned} files scanned, {files_skipped} skipped)"
        )
        return None

    combined = pl.concat(all_records)
    logger.info(
        f"Georgia Insights CSV fallback: collected {combined.height:,} raw "
        f"entity records from {files_scanned} files ({files_skipped} skipped)"
    )
    return combined


def build_districts(
    raw: pl.DataFrame,
    fallback_raw: pl.DataFrame | None = None,
    pre2011_fallback_raw: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """Build the districts dimension table from raw scan data.

    Deduplicates by district_code, keeping the latest year's name.
    Adds census IDs and classifies district types. Fallback scans are
    layered in priority order:

    1. ``raw`` (Era 3+ GOSA + Georgia Insights Excel) — canonical modern names.
    2. ``fallback_raw`` (Georgia Insights CSV) — fills in codes the primary
       scan didn't see (e.g., Department of Corrections code 890).
    3. ``pre2011_fallback_raw`` (pre-2011 GOSA aggregate rows) — fills in
       codes that closed before 2011 (e.g., 795 CCAT, 798 Mountain Education
       Center).

    Existing codes are never overwritten by a fallback — this preserves
    stable canonical names across rebrands. Hard-coded entries from
    ``HARDCODED_DISTRICTS`` are then merged in: they replace any
    bronze-derived row with a colliding code, and are added if missing.

    Args:
        raw: Raw scan data from scan_bronze_entities() (and optionally
            ``scan_georgia_insights_entities``).
        fallback_raw: Optional supplementary scan (e.g. from
            ``scan_georgia_insights_csv_fallback``) used to fill in codes
            absent from the primary scan.
        pre2011_fallback_raw: Optional pre-2011 GOSA district scan from
            ``scan_pre2011_gosa_districts()``, applied after ``fallback_raw``
            to recover codes that disappeared before Era 3+.

    Returns:
        Districts dimension DataFrame.
    """
    districts = (
        raw.select(["district_code", "district_name", "year"])
        .filter(
            pl.col("district_code").is_not_null()
            & pl.col("district_name").is_not_null()
            # Filter out aggregate-level sentinel values that are not real districts
            & ~pl.col("district_code").str.to_uppercase().is_in(DISTRICT_SENTINELS)
            & ~pl.col("district_name").str.to_uppercase().is_in(DISTRICT_SENTINELS)
        )
        .unique()
    )

    # Canonicalize: strip hyphens before zfill so the 2015-era charter code
    # ``782-0410`` collapses onto the 2016+ form ``7820410``. Topic transforms
    # already strip hyphens on the fact-table side; doing the same here keeps
    # the dim PK in sync. Then zero-pad to 3 digits (preserves 7-digit
    # charter codes).
    districts = districts.with_columns(
        pl.col("district_code").str.replace_all("-", "").str.zfill(3)
    )

    # Keep the latest name per district code. Sort by year descending so when
    # the same numeric code appears in both the hyphenated (2015) and
    # unhyphenated (2016+) shape, the modern name wins after canonicalization.
    # Name ascending is the SECONDARY sort key: when two different names share
    # the same latest year, the winner must be deterministic (alphabetical) —
    # an unstable tie-break here made every rebuild flip ~67 district names,
    # which breaks hash-based drift detection.
    districts = (
        districts.sort(["year", "district_name"], descending=[True, False])
        .group_by("district_code")
        .first()
        .drop("year")
    )

    # Merge in fallback codes (e.g. from GI CSVs) that are missing from
    # the primary scan. Anti-join on district_code so we never overwrite
    # an existing name — only add new codes.
    if fallback_raw is not None and fallback_raw.height > 0:
        fb = (
            fallback_raw.select(["district_code", "district_name", "year"])
            .filter(
                pl.col("district_code").is_not_null()
                & pl.col("district_name").is_not_null()
                & ~pl.col("district_code").str.to_uppercase().is_in(DISTRICT_SENTINELS)
                & ~pl.col("district_name").str.to_uppercase().is_in(DISTRICT_SENTINELS)
            )
            .unique()
            .with_columns(pl.col("district_code").str.replace_all("-", "").str.zfill(3))
            .sort(["year", "district_name"], descending=[True, False])
            .group_by("district_code")
            .first()
            .drop("year")
        )
        existing_codes = districts.select("district_code")
        new_codes = fb.join(existing_codes, on="district_code", how="anti")
        if new_codes.height > 0:
            logger.info(
                f"Adding {new_codes.height} districts from fallback scan "
                f"(codes not in primary scan)"
            )
            districts = pl.concat([districts, new_codes], how="diagonal")

    # Merge in pre-2011 GOSA district aggregates as a final fallback. Anti-join
    # on district_code so modern canonical names always win for codes that
    # exist in both eras.
    if pre2011_fallback_raw is not None and pre2011_fallback_raw.height > 0:
        pre = (
            pre2011_fallback_raw.select(["district_code", "district_name", "year"])
            .filter(
                pl.col("district_code").is_not_null()
                & pl.col("district_name").is_not_null()
                & ~pl.col("district_code").str.to_uppercase().is_in(DISTRICT_SENTINELS)
                & ~pl.col("district_name").str.to_uppercase().is_in(DISTRICT_SENTINELS)
            )
            .unique()
            .with_columns(pl.col("district_code").str.replace_all("-", "").str.zfill(3))
            .sort(["year", "district_name"], descending=[True, False])
            .group_by("district_code")
            .first()
            .drop("year")
        )
        existing_codes = districts.select("district_code")
        new_codes = pre.join(existing_codes, on="district_code", how="anti")
        if new_codes.height > 0:
            logger.info(
                f"Adding {new_codes.height} districts from pre-2011 GOSA scan "
                f"(codes not in primary or CSV fallback scans)"
            )
            districts = pl.concat([districts, new_codes], how="diagonal")

    # Apply title case with proper noun handling (DeKalb, McIntosh, etc.)
    districts = districts.with_columns(
        title_case_name(pl.col("district_name")).alias("district_name")
    )

    # Add Census district ID via crosswalk matching
    districts = add_census_district_code(
        districts,
        district_name_col="district_name",
        output_col="district_census_id",
        district_code_col="district_code",
    )

    # Classify district type by code prefix
    districts = districts.with_columns(
        pl.col("district_code")
        .map_elements(_classify_district_type, return_dtype=pl.Utf8)
        .alias("district_type")
    )

    # Final column order
    districts = districts.select(
        [
            "district_code",
            "district_name",
            "district_census_id",
            "district_type",
        ]
    )

    # Merge in hard-coded entries. These take precedence over any
    # bronze-derived row with the same code (e.g., a misspelling or a
    # transient pre-merger name) and are inserted if the code is missing.
    if HARDCODED_DISTRICTS:
        hardcoded = pl.DataFrame(
            {
                "district_code": list(HARDCODED_DISTRICTS.keys()),
                "district_name": [v[0] for v in HARDCODED_DISTRICTS.values()],
                "district_census_id": [v[1] for v in HARDCODED_DISTRICTS.values()],
                "district_type": [v[2] for v in HARDCODED_DISTRICTS.values()],
            },
            schema={
                "district_code": pl.Utf8,
                "district_name": pl.Utf8,
                "district_census_id": pl.Utf8,
                "district_type": pl.Utf8,
            },
        )
        # Drop bronze rows whose code is hard-coded, then concat.
        districts = districts.filter(
            ~pl.col("district_code").is_in(list(HARDCODED_DISTRICTS.keys()))
        )
        districts = pl.concat([districts, hardcoded])

    # Post-merge length guard. Education district codes are either 3-digit
    # standard codes or 7-digit charter codes (per src/etl/education/CLAUDE.md
    # ID rules), with a small allowlist of formal pseudo-district codes
    # (PSEUDO_DISTRICT_CODES) that survive the guard. Anything else slipped
    # through earlier filtering — drop it so the dimension doesn't expose
    # junk codes via the API.
    code_len = pl.col("district_code").str.len_chars()
    valid_shape = code_len.is_in([3, 7]) | pl.col("district_code").is_in(
        list(PSEUDO_DISTRICT_CODES)
    )
    bad_lengths = districts.filter(~valid_shape)
    if bad_lengths.height > 0:
        samples = bad_lengths.head(5).to_dicts()
        logger.warning(
            f"Dropping {bad_lengths.height} districts with invalid code shapes "
            f"(must be 3 or 7 chars, or in PSEUDO_DISTRICT_CODES). "
            f"Samples: {samples}"
        )
        districts = districts.filter(valid_shape)

    districts = districts.sort("district_code")
    return districts


def build_schools(
    raw: pl.DataFrame,
    pre2011_raw: pl.DataFrame | None = None,
    fallback_raw: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """Build the schools dimension table from raw scan data.

    Deduplicates by (school_code, district_code) composite key, keeping
    the latest year's name from Era 3+ bronze.

    Fallbacks are layered in priority order, each anti-joined on the
    composite key so an existing canonical name is never overwritten:

    1. ``raw`` (Era 3+ GOSA + Georgia Insights Excel) — canonical modern names.
    2. ``fallback_raw`` (Georgia Insights CSV) — fills in keys the primary
       scan didn't see (e.g., DOC school 0198 under district 890). GI CSVs
       carry the school identifier as a compound ``"NNNN-School Name"``
       string in either the school_code or school_name slot; both shapes
       are parsed into a clean ``(school_code, school_name)`` pair before
       merging.
    3. ``pre2011_raw`` (pre-2011 GOSA, ``SysSchoolID``) — fills in schools
       that closed before 2011 (used by older topics like ``act_scores``,
       ``sat_scores_*``, ``high_school_completers``).

    Args:
        raw: Raw scan data from scan_bronze_entities() (Era 3+, 2011+).
        pre2011_raw: Optional pre-2011 GOSA scan data from
            ``scan_pre2011_gosa_schools()``. Each row needs
            ``district_code``, ``school_code``, ``school_name``, ``year``.
        fallback_raw: Optional Georgia Insights CSV scan from
            ``scan_georgia_insights_csv_fallback()``. Compound
            ``"NNNN-Name"`` strings are parsed automatically.

    Returns:
        Schools dimension DataFrame.
    """
    schools = raw.select(
        ["school_code", "school_name", "district_code", "year"]
    ).filter(
        pl.col("school_code").is_not_null()
        & pl.col("school_name").is_not_null()
        & ~pl.col("school_code").str.to_uppercase().is_in(SCHOOL_SENTINELS)
    )

    # Format codes. Strip hyphens from district_code first so 2015-era charter
    # codes (``782-0410``) collapse onto the 2016+ form (``7820410``); topic
    # transforms do the same on the fact-table side.
    schools = schools.with_columns(
        pl.col("school_code").str.zfill(4),
        pl.col("district_code").str.replace_all("-", "").str.zfill(3),
    )

    # Keep the latest name per (school_code, district_code) composite key.
    # School codes are NOT globally unique — the same code (e.g., "0101") can
    # appear in many districts. Sort by year descending, take first per pair.
    schools = (
        schools.sort(["year", "school_name"], descending=[True, False])
        .group_by(["school_code", "district_code"])
        .first()
        .drop("year")
    )

    # Merge GI CSV fallback schools for keys not already present. GI enrollment
    # CSVs ship the school identifier as a compound ``"NNNN-School Name"``
    # string in either the school_code or school_name slot (varies by file).
    # Parse it into a clean (code, name) pair, then anti-join.
    if fallback_raw is not None and fallback_raw.height > 0:
        # Coalesce the compound string from whichever slot the file used.
        fb = fallback_raw.select(
            ["district_code", "school_code", "school_name", "year"]
        ).with_columns(
            pl.coalesce(pl.col("school_code"), pl.col("school_name")).alias("_compound")
        )
        # Keep only rows where the compound matches the expected NNNN-Name
        # shape; everything else (e.g., bare codes already handled by the
        # primary scan, or stray sentinel rows) is ignored.
        fb = fb.filter(
            pl.col("_compound").is_not_null()
            & pl.col("_compound").str.contains(r"^\d+-")
            & pl.col("district_code").is_not_null()
        )
        if fb.height > 0:
            fb = fb.with_columns(
                pl.col("_compound").str.extract(r"^(\d+)-", 1).alias("_parsed_code"),
                pl.col("_compound")
                .str.extract(r"^\d+-(.*)$", 1)
                .str.strip_chars()
                .alias("_parsed_name"),
            ).filter(
                pl.col("_parsed_code").is_not_null()
                & pl.col("_parsed_name").is_not_null()
                & (pl.col("_parsed_name").str.len_chars() > 0)
                & ~pl.col("_parsed_code").str.to_uppercase().is_in(SCHOOL_SENTINELS)
            )
        if fb.height > 0:
            fb = (
                fb.with_columns(
                    pl.col("_parsed_code").str.zfill(4).alias("school_code"),
                    pl.col("_parsed_name").alias("school_name"),
                    pl.col("district_code")
                    .str.replace_all("-", "")
                    .str.zfill(3)
                    .alias("district_code"),
                )
                .select(["school_code", "school_name", "district_code", "year"])
                # Latest year wins among GI CSV observations for a given key.
                .sort(["year", "school_name"], descending=[True, False])
                .group_by(["school_code", "district_code"])
                .first()
                .drop("year")
            )
            existing_keys = schools.select(["school_code", "district_code"])
            fb_only = fb.join(
                existing_keys,
                on=["school_code", "district_code"],
                how="anti",
            )
            if fb_only.height > 0:
                logger.info(
                    f"Adding {fb_only.height:,} schools from GI CSV fallback "
                    f"(keys not present in Era 3+ scan)"
                )
                schools = pl.concat([schools, fb_only], how="diagonal")

    # Merge pre-2011 schools as a fallback for keys not already present.
    if pre2011_raw is not None and pre2011_raw.height > 0:
        pre = pre2011_raw.select(
            ["school_code", "school_name", "district_code", "year"]
        ).filter(
            pl.col("school_code").is_not_null()
            & pl.col("school_name").is_not_null()
            & ~pl.col("school_code").str.to_uppercase().is_in(SCHOOL_SENTINELS)
        )
        pre = pre.with_columns(
            pl.col("school_code").str.zfill(4),
            pl.col("district_code").str.replace_all("-", "").str.zfill(3),
        )
        # Latest *pre-2011* observation wins per composite key.
        pre = (
            pre.sort(["year", "school_name"], descending=[True, False])
            .group_by(["school_code", "district_code"])
            .first()
            .drop("year")
        )
        # Anti-join against Era 3+ keys so we never overwrite an active
        # school's canonical name.
        existing_keys = schools.select(["school_code", "district_code"])
        pre_only = pre.join(
            existing_keys,
            on=["school_code", "district_code"],
            how="anti",
        )
        if pre_only.height > 0:
            logger.info(
                f"Adding {pre_only.height:,} pre-2011 schools as fallbacks "
                f"for keys not present in Era 3+ scan"
            )
            schools = pl.concat([schools, pre_only], how="diagonal")

    # Post-merge cleanup: drop pollution rows that survived the per-source
    # filters above.
    #
    # 1. `X`-suffix school codes (e.g., `2052X`, `3060X`, `4752X`, `4050X`,
    #    `3055X`) appear in some bronze sources as placeholder rows but are
    #    never referenced by any fact table. They should not be exposed as
    #    real schools via the API.
    # 2. Sentinel `district_code` values like `DISTRICT_ALL` only ever pair
    #    with sentinel school rows. Drop them defensively.
    # 3. After the above, every surviving school_code must be exactly 4
    #    chars (per src/etl/education/CLAUDE.md ID rules).
    school_upper = pl.col("school_code").str.to_uppercase()
    sentinel_mask = school_upper.str.contains(SCHOOL_CODE_X_SUFFIX_RE.pattern) | pl.col(
        "district_code"
    ).str.to_uppercase().is_in(DISTRICT_SENTINELS)
    dropped = schools.filter(sentinel_mask)
    if dropped.height > 0:
        samples = dropped.head(5).to_dicts()
        logger.warning(
            f"Dropping {dropped.height} school rows with sentinel / "
            f"X-suffix codes. Samples: {samples}"
        )
        schools = schools.filter(~sentinel_mask)

    bad_len = schools.filter(pl.col("school_code").str.len_chars() != 4)
    if bad_len.height > 0:
        samples = bad_len.head(5).to_dicts()
        logger.warning(
            f"Dropping {bad_len.height} schools with school_code length != 4. "
            f"Samples: {samples}"
        )
        schools = schools.filter(pl.col("school_code").str.len_chars() == 4)

    # Apply title case with proper noun handling
    schools = schools.with_columns(
        title_case_name(pl.col("school_name")).alias("school_name")
    )

    # Final column order and sort. Lead with the composite primary key in its
    # canonical order (district_code, school_code) so the on-disk parquet matches
    # the schools dimension contract's property/primaryKey order, then the
    # attribute. (The API joins by name, but ordering the parquet to the contract
    # keeps strict schema-conformance consumers happy.)
    schools = schools.select(
        [
            "district_code",
            "school_code",
            "school_name",
        ]
    ).sort("district_code", "school_code")

    return schools


class DimensionBuildError(RuntimeError):
    """Raised when a freshly built dimension fails its health assertions."""


def _previous_row_count(parquet_path: Path) -> int | None:
    """Row count of the existing dimension parquet, or None if absent."""
    if not parquet_path.exists():
        return None
    try:
        return pl.read_parquet(parquet_path).height
    except Exception:  # pragma: no cover - unreadable previous build
        return None


def _assert_no_shrinkage(name: str, new_height: int, previous: int | None) -> None:
    """Fail when a rebuild drops rows vs the previous build.

    Dimensions are append-mostly (entities close but stay in the dim with
    their latest name); a shrinking rebuild usually means a bronze scan
    silently lost a source. Set ALLOW_DIM_SHRINK=1 to override deliberately.
    """
    import os

    if previous is not None and new_height < previous:
        if os.environ.get("ALLOW_DIM_SHRINK") == "1":
            logger.warning(
                f"{name}: row count shrank {previous} -> {new_height} "
                "(allowed via ALLOW_DIM_SHRINK=1)"
            )
            return
        raise DimensionBuildError(
            f"{name}: rebuild shrank from {previous} to {new_height} rows. "
            "If deliberate (e.g. a dropped sentinel), re-run with "
            "ALLOW_DIM_SHRINK=1."
        )


def _assert_districts_health(districts: pl.DataFrame) -> None:
    """Hard gates on the districts dimension (replaces log-and-hope)."""
    dupes = districts.filter(pl.col("district_code").is_duplicated())
    if dupes.height > 0:
        raise DimensionBuildError(
            f"districts: {dupes.height} duplicate district_code rows: "
            f"{dupes['district_code'].unique().to_list()[:10]}"
        )

    bad_shape = districts.filter(
        ~pl.col("district_code").str.len_chars().is_in([3, 7])
        & ~pl.col("district_code").is_in(list(PSEUDO_DISTRICT_CODES))
    )
    if bad_shape.height > 0:
        raise DimensionBuildError(
            f"districts: {bad_shape.height} codes outside the 3/7-digit + "
            f"allowlist shapes: {bad_shape['district_code'].to_list()[:10]}"
        )

    # Every standard district must carry a census ID (the contract's
    # standard_districts_have_census_id rule). Unmatched names are fixed by
    # adding a DISTRICT_NAME_OVERRIDES entry — failing here is the prompt.
    unmatched = districts.filter(
        pl.col("district_census_id").is_null() & (pl.col("district_type") == "standard")
    )
    if unmatched.height > 0:
        raise DimensionBuildError(
            f"districts: {unmatched.height} standard district(s) without "
            f"census IDs: {unmatched['district_name'].to_list()}. Add "
            "DISTRICT_NAME_OVERRIDES entries in src/utils/crosswalks.py."
        )


def _assert_schools_health(schools: pl.DataFrame, districts: pl.DataFrame) -> None:
    """Hard gates on the schools dimension."""
    dupes = schools.filter(pl.struct(["district_code", "school_code"]).is_duplicated())
    if dupes.height > 0:
        raise DimensionBuildError(
            f"schools: {dupes.height} duplicate (district_code, school_code) "
            f"rows: {dupes.head(10).to_dicts()}"
        )

    bad_len = schools.filter(pl.col("school_code").str.len_chars() != 4)
    if bad_len.height > 0:
        raise DimensionBuildError(
            f"schools: {bad_len.height} school_code values not 4 chars: "
            f"{bad_len['school_code'].to_list()[:10]}"
        )

    # Intra-dimension referential integrity: every school's district must
    # exist in the districts dim, or fact joins through schools will strand.
    orphans = schools.join(
        districts.select("district_code").unique(),
        on="district_code",
        how="anti",
    )
    if orphans.height > 0:
        raise DimensionBuildError(
            f"schools: {orphans.height} school(s) reference district codes "
            f"missing from the districts dim: "
            f"{orphans['district_code'].unique().to_list()[:10]}"
        )


def _run_dimension_contract_quality(contract_path: Path, parquet_path: Path) -> None:
    """Execute the dimension contract's quality SQL against the new parquet."""
    from src.utils import contract_reader
    from src.utils.validators import check_contract_quality_sql

    contract = contract_reader.load_contract(contract_path)
    result = check_contract_quality_sql(parquet_path, contract)
    if result.status == "fail":
        raise DimensionBuildError(
            f"{parquet_path.name}: contract quality checks failed — "
            f"{result.details or [result.message]}"
        )
    logger.info(f"{parquet_path.name}: {result.message}")


def main() -> None:
    """Build and export education dimension tables."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Preflight: the manual crosswalk overrides must still point at real
    # crosswalk entries, or census matching silently degrades.
    from src.utils.crosswalks import check_crosswalk_overrides

    override_problems = check_crosswalk_overrides()
    if override_problems:
        raise DimensionBuildError(
            "crosswalk override map(s) reference entries missing from the "
            f"crosswalk artifact: {override_problems}"
        )

    # Scan GOSA bronze (Era 3+), Georgia Insights Excel bronze, pre-2011
    # GOSA bronze (schools and district aggregates), and Georgia Insights
    # CSV bronze. Each supplementary source is optional — missing or
    # unreadable files never block a build.
    #   • Pre-2011 GOSA schools: schools dim, fills in pre-2011-only school
    #     keys (see scan_pre2011_gosa_schools).
    #   • Pre-2011 GOSA districts: districts dim, fills in pre-2011-only
    #     district codes (e.g., 795 CCAT, 798 Mountain Education Center).
    #   • GI CSV: both dims, applied as a fallback (only fills in codes
    #     the primary scan didn't see, e.g. Department of Corrections
    #     code 890 and its school 0198). It is NOT mixed into the primary
    #     scan because GI CSVs use rebranded charter names ("State
    #     Specialty Schools I-…") that differ from older bronze.
    raw_gosa = scan_bronze_entities()
    raw_gi = scan_georgia_insights_entities()
    raw_pre2011 = scan_pre2011_gosa_schools()
    raw_pre2011_districts = scan_pre2011_gosa_districts()
    raw_gi_csv = scan_georgia_insights_csv_fallback()
    if raw_gi is not None:
        # diagonal concat aligns by column name so the two scanners do not
        # need to emit columns in the same order.
        raw = pl.concat([raw_gosa, raw_gi], how="diagonal")
    else:
        raw = raw_gosa

    # Capture previous row counts BEFORE overwriting, for shrink detection.
    prev_districts = _previous_row_count(OUTPUT_DIR / "districts.parquet")
    prev_schools = _previous_row_count(OUTPUT_DIR / "schools.parquet")

    # Build districts (CSV scan + pre-2011 GOSA aggregates supply fallback codes)
    districts = build_districts(
        raw,
        fallback_raw=raw_gi_csv,
        pre2011_fallback_raw=raw_pre2011_districts,
    )

    # Hard gates before anything is written: PK uniqueness, code shapes,
    # standard-district census coverage, row-count regression.
    _assert_districts_health(districts)
    _assert_no_shrinkage("districts", districts.height, prev_districts)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    districts.write_parquet(OUTPUT_DIR / "districts.parquet")

    # Emit the git-tracked ODCS contract for the districts dimension (mirrors
    # the transform-emits-contract pattern). The contract's district_type enum
    # is derived from the live code constants, so it never drifts.
    districts_contract = emit_districts_contract()
    logger.info(f"Emitted districts dimension contract to {districts_contract}")

    # Run the contract's own quality SQL against the parquet just written.
    _run_dimension_contract_quality(
        districts_contract, OUTPUT_DIR / "districts.parquet"
    )

    # Log district stats
    census_matched = districts.filter(pl.col("district_census_id").is_not_null()).height
    census_rate = census_matched / districts.height if districts.height > 0 else 0
    type_counts = districts.group_by("district_type").len().sort("district_type")
    logger.info(
        f"Wrote {districts.height} districts to {OUTPUT_DIR / 'districts.parquet'} "
        f"(census match rate: {census_rate:.1%})"
    )
    for row in type_counts.iter_rows(named=True):
        logger.info(f"  {row['district_type']}: {row['len']}")

    # Build schools (GI CSV + pre-2011 fallbacks merged in build_schools)
    schools = build_schools(
        raw,
        pre2011_raw=raw_pre2011,
        fallback_raw=raw_gi_csv,
    )

    _assert_schools_health(schools, districts)
    _assert_no_shrinkage("schools", schools.height, prev_schools)

    schools.write_parquet(OUTPUT_DIR / "schools.parquet")
    logger.info(f"Wrote {schools.height} schools to {OUTPUT_DIR / 'schools.parquet'}")

    # Emit the git-tracked ODCS contract for the schools dimension (composite
    # primary key: district_code + school_code).
    schools_contract = emit_schools_contract()
    logger.info(f"Emitted schools dimension contract to {schools_contract}")

    _run_dimension_contract_quality(schools_contract, OUTPUT_DIR / "schools.parquet")


if __name__ == "__main__":
    main()
