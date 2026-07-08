"""Transform bronze ccrpi_graduation_rate files into gold fact tables.

Source: Georgia Insights (GaDOE) — Georgia's high school graduation rates at
the school, district, and state level by demographic subgroup, published
across SIX distinct file families (bronze: 26 readable xls/xlsx/csv files
spanning 2012-2025; one 125-page PDF is superseded — see below):

    A. CCRPI Graduation Rates (2018-2020, 2022-2025 releases) — 4-year and
       5-year rates as long-format rows discriminated by `Graduation Rate
       Type`, plus a CCRPI improvement `Target` and color `Flag` (absent in
       the 2022 file; all-NA in 2020 per the COVID CCRPI suspension). The
       2022-2025 workbooks carry TWO `School Year` values each (prior year's
       5-year cohort + current year's 4-year cohort); 2018-2020 carry one.
    B. Legacy Graduation Rate (2012-2014) — pre-CCRPI 4-year rate only.
       2012-2013 publish school+district rows only (no state aggregate);
       2014 introduces the state row. Column naming drifts per year.
    C. Standalone 4-Year Cohort (data years 2015-2022, 2024-2025) — two
       sheets per file: an `All Students` sheet with `Graduation Class Size`
       + `Total Graduated` counts (ALL Students demographic only) and a
       `Subgroup` sheet with rates for all 10 demographics (no counts).
    D. Standalone 5-Year Graduation Rate (2021 only) — fills the 5-year gap
       left by the missing 2021 CCRPI release. Rate only, no counts.
    E. On-Time Graduation Rate (2021-2024) — the SB 431 (2020) statutory
       measure (students continuously enrolled from Oct 1 of 9th grade who
       graduate by the regular date). School-level rows ONLY. Carries
       `Total Enrolled` + `Total Graduated` counts.
    F. GOSA 4-Year Cohort CSV (2023 only) — the 2023 standalone 4-year
       release exists in bronze only as a 125-page typeset PDF
       (`...12.14.23.pdf`, unreadable; superseded). The GOSA portal CSV
       carries the same release with numerator/denominator counts and an
       18-demographic breakdown (adds active_duty, female/male, foster_care,
       homeless, migrant, not_economically_disadvantaged,
       students_without_disabilities over the 10-subgroup standard).

Gold design — one `graduation_rate` metric discriminated by `rate_type`
(`4_year` / `5_year` / `on_time`); `num_cohort` (denominator) and
`num_graduates` (numerator) counts; CCRPI `indicator_target` + `ccrpi_flag`.

Key decisions (each re-verified against THIS topic's bronze during
authoring — see bronze-data-structure.md, incl. its Corrections section):

- **String-typed multi-sheet reads.** The shared ``read_bronze_file`` reads
  only a workbook's first sheet, so Excel reads go through a local pandas
  helper (precedent: ccrpi_content_mastery / attendance_dashboard) using
  ``dtype=str`` + ``SUPPRESSION_VALUES``. String typing preserves the
  literal ``"ALL"`` aggregate sentinels (re-verified: Family A state rows
  carry the literal string ``"ALL"`` in `System ID` in EVERY year — the
  "NULL System ID" in the structure doc is a type-inference artifact, now
  documented in its Corrections section) and zero-padded school codes.
  Whole-sheet Excel reads cannot drop rows, so read-loss raw == parsed by
  construction; the Family F CSV goes through the shared reader with
  ``return_loss=True`` + ``infer_schema_length=0``.

- **Year per family.** Family A/B/E carry an authoritative year column
  (used per row; cross-checked against the filename year — A workbooks may
  carry {year-1, year}). Family C/D have NO year column: the data year
  comes from the filename, with `FILENAME_DATA_YEARS` pinning the files
  whose names carry no parseable year and the one offset file
  (`...02.19.18.xlsx` is a February 2018 release of the 2017 cohort —
  verified in the structure doc by cross-referencing state ALL-Students
  values against the matching CCRPI releases). Family F's
  `LONG_SCHOOL_YEAR` (`2022-23` -> 2023) is cross-checked in code.

- **Detail level from "ALL" sentinels** (state = ALL/ALL, district =
  code/ALL, school = code/code), cross-checked against the `Reporting
  Level` / `DETAIL_LVL_DESC` column wherever one exists (C/D/E/F; raises on
  any disagreement). Family B 2012-2013 have no sentinels and no state
  rows — their `REPORTING LEVEL` column is the only source. Sentinels are
  NULLed before zfill so "ALL" is never zero-padded.

- **RTC pseudo-district (2015-2018).** Family C files for data years
  2015-2018 carry `System ID="RTC"` district-level rows (School ID="ALL";
  1 row in the All-Students sheet + 10 in the Subgroup sheet per file) —
  the Residential Treatment Center aggregate. `RTC` is an allowlisted
  pseudo-district code in the districts dimension (education CLAUDE.md), so
  these rows are kept as district-level facts. Missing from the structure
  doc — added to its Corrections section.

- **Family C two-sheet combine.** The Subgroup sheet is the base (rates for
  all 10 demographics, incl. an ALL row whose rate is byte-identical to the
  All-Students sheet's rate in every file except 12.08.21, max diff 0.01pp);
  the All-Students sheet contributes `num_cohort`/`num_graduates`,
  left-joined onto the `all`-demographic rows by (detail_level, district,
  school). The 09_19_18 file's All-Students sheet has 30 entities absent
  from its Subgroup sheet — all 30 are fully suppressed (every metric `Too
  Few Students`), so the subgroup-as-base design loses zero data
  (re-verified). Family D's `ALL Student` sheet is a strict subset of its
  `Subgroup` sheet (669/671 keys, rates identical) and is skipped.

- **Cross-family merge (the dedup decision).** Families A/C/F all publish
  the 4-year rate for overlapping years; A and D overlap for the 2021
  5-year measure. Overlaps are resolved by an explicit source-precedence
  merge — sort by family rank a(0) < d(1) < b(2) < c(3) < e(4) < f(5), then
  take the first non-null value per metric within each natural key — so
  CCRPI's rate/indicator_target/flag and the standalone release's counts land on one
  gold row. CCRPI (A) is the accountability-grade release and wins wherever
  it published a value; Family F's rate surfaces only for 2023 keys with no
  CCRPI counterpart (~small-cell rows GaDOE released through the GOSA
  channel while suppressing in the CCRPI workbook). Because the natural-key
  collision guard would (correctly) flag these deliberate cross-family
  overlaps, the guard runs scoped WITHIN each source family (key +
  `_source_family`) — the true no-alias-collapse invariant — and the merge
  is the documented cross-family resolution. `deduplicate_by_detail_level`
  is not used: the merge's group_by guarantees per-key uniqueness, which
  the validator's grain check re-verifies.

- **2021 5-year A/D overlap.** The 2022 CCRPI workbook's prior-year (2021)
  5-year slice disagrees with Family D's standalone December 2021 release
  (the primary publication for that measure). SCHOOL-level Family A 2021
  5-year rows that Family D republishes are dropped (recorded via
  ``manifest.record_filtered``), making D authoritative at school level;
  Family-A-only school keys are retained. At district/state level Family A
  wins under the a<d precedence (v1-parity behavior: its key-matched drop
  never matched aggregate rows whose school_code is NULL). The asymmetry is
  preserved deliberately for baseline parity and documented in the contract.

- **Rate vs count cutoff caveat.** `graduation_rate` is sourced from the
  CCRPI snapshot (A) where available while `num_cohort`/`num_graduates`
  come from the standalone cohort releases (C/F) published at different
  cutoffs; even within one Family C release the published rate and counts
  reconcile only to ~0.4pp (02.19.18 file). `num_graduates / num_cohort ≈
  graduation_rate` is therefore NOT an invariant for 4-year rows and no
  such quality check is authored. It IS exact (to published rounding,
  ≤0.005pp) for `on_time` rows, whose rate and counts ship in one file —
  authored as a quality check.

- **Demographics.** All families publish the explicit `Asian/Pacific
  Islander` combined bucket and never separate Asian or Pacific Islander
  rows (§5b: combined-convention topic; split keys never emitted).
  `American Indian/Alaskan` (pre-2022 labels) and `American Indian/Alaskan
  Native` (2022+) both fold to `native_american`; Family F's `Limited
  English Proficient` folds to `english_learners`. No two labels within one
  file map to the same canonical key (re-verified: 18 distinct canonicals
  from F's 18 labels, 10 from the others), so no
  `aggregate_demographic_collisions` pass is needed — the scoped collision
  guard fails loudly on any future drift.

- **Suppression.** `TFS` / `Too Few Students` / `NA` become NULL at read
  via SUPPRESSION_VALUES; `No Data` / `No Data Found` (not in the shared
  set) become NULL via `strict=False` numeric casts. All metric NULLs mean
  "suppressed or not published".

- **No §4b masks.** Every observed value is inside its metric's domain:
  rates within [0, 100] bronze / [0, 1] gold in every family,
  indicator_targets within [2.2, 90], counts non-negative,
  `num_graduates <= num_cohort`
  with zero violations source-wide (all re-verified).

Natural key: (year, district_code, school_code, demographic, detail_level,
rate_type). `ccrpi_flag` is a derived performance attribute functionally
determined by the rest of the key and is excluded from the contract grain.
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
    parse_school_year,
    read_bronze_file,
)
from src.utils.transformers import (
    TransformManifest,
    assert_no_natural_key_collisions,
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

TOPIC = "ccrpi_graduation_rate"
BRONZE_DIR = Path("data/bronze/education/georgiainsights/ccrpi_graduation_rate")
GOLD_DIR = Path("data/gold/education/ccrpi_graduation_rate")
SOURCE_URL = "https://georgiainsights.gadoe.org/data-downloads/"

# Non-data sheets skipped by the multi-sheet readers: `FAQs` (Family A 2022,
# Family C 12.08.21, Family D) is empty metadata; `Details` (Family E) quotes
# the SB 431 methodology.
SKIP_SHEETS: set[str] = {"FAQs", "Details", "Read Me", "ReadMe", "Notes"}

# Aggregate-row sentinel in the ID columns (literal string under dtype=str
# reads in every family that has aggregate rows). Becomes NULL in gold.
AGGREGATE_SENTINEL = "ALL"

# Data years for files whose names carry no parseable data year (dotted /
# underscored publication dates), plus the one offset file. Years are the
# structure doc's inferences, cross-referenced there against state
# ALL-Students values in the matching CCRPI releases.
FILENAME_DATA_YEARS: dict[str, int] = {
    # February 2018 publication of the 2017 cohort (filename year = data
    # year + 1) — the only offset file in the directory.
    "4-Year Cohort Graduation Rate State District School by Subgroup 02.19.18.xlsx": 2017,  # noqa: E501
    "4-Year Cohort Graduation Rate State District School by Subgroups_09_19_18.xlsx": 2018,  # noqa: E501
    "4-Year Cohort Graduation Rate State District School by Subgroups_11_26_19.xlsx": 2019,  # noqa: E501
    "4-Year Cohort Graduation Rate State District School by Subgroups 11_20_20.xlsx": 2020,  # noqa: E501
    "4-Year Cohort Graduation Rate State District School by Subgroup 12.08.21.xlsx": 2021,  # noqa: E501
    "4-Year Cohort Graduation Rate State District School by Subgroup 10_06_22.xlsx": 2022,  # noqa: E501
    "5-Year Graduation Rate by Subgroup 12.08.21.xlsx": 2021,
}

# Family A `Graduation Rate Type` -> gold rate_type (snake_case per §10).
GRAD_RATE_TYPE_MAP: dict[str, str] = {
    "4-YEAR GRADUATION RATE": "4_year",
    "5-YEAR GRADUATION RATE": "5_year",
}

# CCRPI color flag -> descriptive values per data-cleaning-standards §16.
# Bronze `NA` becomes NULL at read via SUPPRESSION_VALUES. The graduation
# indicator never awards `G*` in any bronze year 2018-2025 (re-verified), so
# no green_star mapping exists — do not add one speculatively.
CCRPI_FLAG_MAP: dict[str, str] = {
    "G": "green",
    "Y": "yellow",
    "R": "red",
}

# `Reporting Level` / `DETAIL_LVL_DESC` -> detail_level (pipeline-internal
# column; never lands in gold, so it is not manifest-recorded).
REPORTING_LEVEL_MAP: dict[str, str] = {
    "SCHOOL": "school",
    "SYSTEM": "district",
    "DISTRICT": "district",
    "STATE": "state",
}

# Family C/D header drift: 2015 ships ALL-CAPS headers (one with a trailing
# space, stripped before lookup); 2016+ ship Title Case. Both funnel into the
# Title Case canonical form so the rename maps stay stable.
_FAMILY_CD_HEADER_CANONICAL: dict[str, str] = {
    "REPORTING LEVEL": "Reporting Level",
    "SYSTEM ID": "System ID",
    "SCHOOL ID": "School ID",
    "SYSTEM NAME": "System Name",
    "SCHOOL NAME": "School Name",
    "REPORTING LABEL": "Reporting Label",
    "GRADUATION CLASS SIZE": "Graduation Class Size",
    "TOTAL GRADUATED": "Total Graduated",
    "GRADUATION RATE": "Graduation Rate",
}

# Family C sheet-name drift across years.
FAMILY_C_ALL_SHEETS: set[str] = {"All Students", "All Student", "ALL Student"}
FAMILY_C_SUBGROUP_SHEETS: set[str] = {"Subgroups", "Subgroup", "Student Group"}

# Cross-family merge precedence (lower rank wins per metric). Family A
# (CCRPI) is the accountability-grade release; D is the primary 2021 5-year
# publication; B/C/E never overlap a higher source on a published metric;
# F (GOSA CSV) is lowest so its 2023 rate survives only where A has no row.
MERGE_PRECEDENCE: dict[str, int] = {"a": 0, "d": 1, "b": 2, "c": 3, "e": 4, "f": 5}

# Tolerance for the informational cross-source rate-disagreement log
# (absolute difference on the 0-1 scale = 0.5 percentage points).
RATE_DISAGREEMENT_TOLERANCE = 0.005

# Gold fact column order. `detail_level` is carried through merge /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "detail_level",
    "rate_type",
    "graduation_rate",
    "num_cohort",
    "num_graduates",
    "indicator_target",
    "ccrpi_flag",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "demographic": pl.Utf8,
    "detail_level": pl.Utf8,
    "rate_type": pl.Utf8,
    "graduation_rate": pl.Float64,
    "num_cohort": pl.Int64,
    "num_graduates": pl.Int64,
    "indicator_target": pl.Float64,
    "ccrpi_flag": pl.Utf8,
}

# Numeric metric columns (manifest stats + null-rate spike check). The
# string-valued `ccrpi_flag` joins them only in the collision guard.
METRIC_COLUMNS: list[str] = [
    "graduation_rate",
    "num_cohort",
    "num_graduates",
    "indicator_target",
]

NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "detail_level",
    "rate_type",
]

# The 18 canonical demographics this topic publishes (contract enum). The 10
# cross-era subgroups appear 2012-2025; the other 8 arrive only via the 2023
# Family F GOSA CSV's wider breakdown.
DEMOGRAPHIC_VALUES: list[str] = sorted(
    [
        "all",
        # Race — combined Asian/Pacific Islander bucket (§5b); the source
        # never publishes separate Asian or Pacific Islander rows.
        "asian_pacific_islander",
        "black",
        "hispanic",
        "multiracial",
        "native_american",
        "white",
        # Special populations / programs (10-subgroup standard).
        "economically_disadvantaged",
        "english_learners",
        "students_with_disabilities",
        # Family F (2023 4-year) extras.
        "active_duty",
        "female",
        "male",
        "foster_care",
        "homeless",
        "migrant",
        "not_economically_disadvantaged",
        "students_without_disabilities",
    ]
)


# =============================================================================
# Bronze reading (string-typed pandas, per-sheet, disclaimer-aware)
# =============================================================================


def _read_sheet(path: Path, sheet: str, header_row: int = 0) -> pl.DataFrame:
    """Read one Excel sheet as an all-Utf8 polars frame, headers stripped.

    ``dtype=str`` preserves "ALL" sentinels and zero-padded codes that type
    inference destroys; SUPPRESSION_VALUES (TFS, Too Few Students, NA, ...)
    arrive as NULL. Header whitespace is stripped (2015 ships "SCHOOL ID "
    with a trailing space; the 2021 On-Time file ships " Year").
    """
    pdf = pd.read_excel(
        path,
        sheet_name=sheet,
        dtype=str,
        na_values=list(SUPPRESSION_VALUES),
        header=header_row,
    )
    pdf.columns = [str(c).strip() for c in pdf.columns]
    return pl.from_pandas(pdf)


def _read_sheet_required(
    path: Path,
    sheet: str,
    required: list[str],
    canonicalize_cd: bool = False,
) -> pl.DataFrame:
    """Read a sheet, auto-detecting a row-0 disclaimer via required columns.

    Family C 12.08.21 / 10_06_22 ship a USDA waiver disclaimer and every
    Family E file ships the SB 431 statutory text in row 0. Rather than
    hardcode per-file header rows, read at header_row=0 and retry at
    header_row=1 when the required columns are absent — self-verifying for
    any future disclaimer-topped republish.
    """
    df = _read_sheet(path, sheet, header_row=0)
    if canonicalize_cd:
        df = _canonicalize_cd_headers(df)
    if all(c in df.columns for c in required):
        return df
    logger.info(
        "  %s :: %r: required columns absent at header_row=0 — retrying at "
        "header_row=1 (disclaimer row)",
        path.name,
        sheet,
    )
    df = _read_sheet(path, sheet, header_row=1)
    if canonicalize_cd:
        df = _canonicalize_cd_headers(df)
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"{path.name} sheet {sheet!r}: required column(s) {missing} not "
            f"found at header_row 0 or 1. Present: {sorted(df.columns)}"
        )
    return df


def _canonicalize_cd_headers(df: pl.DataFrame) -> pl.DataFrame:
    """Funnel Family C/D ALL-CAPS header drift into Title Case canonicals."""
    rename = {
        c: _FAMILY_CD_HEADER_CANONICAL[c.upper()]
        for c in df.columns
        if c.upper() in _FAMILY_CD_HEADER_CANONICAL
        and c != _FAMILY_CD_HEADER_CANONICAL[c.upper()]
    }
    return df.rename(rename) if rename else df


def _single_data_sheet(path: Path) -> str:
    """Return the lone data sheet name of a Family A/B workbook.

    Family A carries one data sheet (name drifts across years) plus an
    occasional FAQs sheet; Family B 2012-2013 .xls files carry empty
    Sheet2/Sheet3 placeholders. The first sheet that is non-skipped and
    non-empty wins.
    """
    xl = pd.ExcelFile(path)
    for sheet in xl.sheet_names:
        if sheet in SKIP_SHEETS:
            continue
        probe = pd.read_excel(path, sheet_name=sheet, dtype=str, nrows=5)
        if probe.empty or len(probe.columns) < 3:
            continue
        return sheet
    raise ValueError(f"{path.name}: no non-empty data sheet found")


# =============================================================================
# Shared helpers
# =============================================================================


def _require_columns(df: pl.DataFrame, required: list[str], label: str) -> None:
    """Raise if any expected bronze column is absent (rename-coverage guard).

    An unmatched source column silently becomes NULL in gold — the most
    common data-loss bug — so a missing column fails loudly instead.
    """
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"{label}: expected bronze column(s) missing: {missing}. "
            f"Present: {sorted(df.columns)}"
        )


def _apply_categorical_map(
    df: pl.DataFrame,
    raw_col: str,
    gold_col: str,
    mapping: dict[str, str],
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Strip/uppercase a raw column, map it strictly, and record the result.

    ``replace_strict(default=None)`` keeps NULL as NULL and turns any
    unmapped bronze value into NULL — which ``record_categorical`` counts as
    unmapped, making ``manifest.write()`` raise before bad gold lands.
    """
    raw_expr = pl.col(raw_col).cast(pl.Utf8).str.strip_chars().str.to_uppercase()
    normalized = df.select(raw_expr.alias("_norm"))["_norm"]
    df = df.with_columns(raw_expr.replace_strict(mapping, default=None).alias(gold_col))
    manifest.record_categorical(
        column=gold_col,
        map_dict=mapping,
        bronze_series=normalized,
        gold_series=df[gold_col],
    )
    return df.drop(raw_col) if raw_col != gold_col else df


def _record_literal_rate_type(
    df: pl.DataFrame, value: str, manifest: TransformManifest
) -> None:
    """Record a synthetic (literal) rate_type so the manifest's categorical
    contract covers families whose rate_type never passes through a map
    (B/C/D/E/F hardcode it; only Family A carries a bronze column)."""
    manifest.record_categorical(
        column="rate_type",
        map_dict={value: value},
        bronze_series=df["rate_type"],
        gold_series=df["rate_type"],
    )


def _normalize_demographic(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Normalize `demographic_raw` via the shared canonical path (§5).

    Records the effective slice of DEMOGRAPHIC_ALIASES — only the aliases
    this file's labels actually hit — keeping the manifest reviewable while
    the unmapped guard still flags any label the shared map cannot place.
    """
    df = df.with_columns(
        normalize_demographic_column("demographic_raw").alias("demographic")
    )
    observed_upper = {
        str(v).strip().upper()
        for v in df["demographic_raw"].drop_nulls().unique().to_list()
    }
    effective_map = {
        k: v for k, v in DEMOGRAPHIC_ALIASES.items() if k in observed_upper
    }
    manifest.record_categorical(
        column="demographic",
        map_dict=effective_map,
        bronze_series=df["demographic_raw"],
        gold_series=df["demographic"],
    )
    return df.drop("demographic_raw")


def _derive_detail_level(df: pl.DataFrame, label: str) -> pl.DataFrame:
    """Derive detail_level from "ALL" sentinels, then NULL + zfill the IDs.

    state = ALL/ALL, district = code/ALL, school = code/code. The fourth
    quadrant (ALL district with a concrete school) is structurally absent in
    every file and raises if it ever appears. Sentinels become NULL BEFORE
    zfill so "ALL" is never padded; zfill(3) pads 3-digit district codes
    while passing 7-digit charter codes and the allowlisted "RTC"
    pseudo-district through; zfill(4) restores school leading zeros.
    """
    is_dist_all = pl.col("district_code") == AGGREGATE_SENTINEL
    is_sch_all = pl.col("school_code") == AGGREGATE_SENTINEL
    bad = df.filter(is_dist_all & ~is_sch_all.fill_null(False)).height
    if bad:
        raise ValueError(
            f"{label}: {bad} row(s) with district 'ALL' but a concrete "
            f"school code — unknown detail level"
        )
    return df.with_columns(
        pl.when(is_dist_all & is_sch_all)
        .then(pl.lit("state"))
        .when(is_sch_all)
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .alias("detail_level"),
        pl.when(is_dist_all)
        .then(None)
        .otherwise(pl.col("district_code").str.zfill(3))
        .alias("district_code"),
        pl.when(is_sch_all)
        .then(None)
        .otherwise(pl.col("school_code").str.zfill(4))
        .alias("school_code"),
    )


def _check_reporting_level(df: pl.DataFrame, raw_col: str, label: str) -> pl.DataFrame:
    """Cross-check the source's reporting-level column against the
    sentinel-derived detail_level, then drop it. Raises on any disagreement
    or unmapped level value — a mismatch would mean the "ALL" sentinel rules
    misread this file."""
    mapped = (
        pl.col(raw_col)
        .cast(pl.Utf8)
        .str.strip_chars()
        .str.to_uppercase()
        .replace_strict(REPORTING_LEVEL_MAP, default=None)
    )
    mismatch = df.filter(mapped != pl.col("detail_level")).height
    unmapped = df.filter(mapped.is_null() & pl.col(raw_col).is_not_null()).height
    if mismatch or unmapped:
        raise ValueError(
            f"{label}: reporting-level column disagrees with sentinel-derived "
            f"detail_level ({mismatch} mismatch(es), {unmapped} unmapped)"
        )
    return df.drop(raw_col)


def _rate_0_1(col: str) -> pl.Expr:
    """Bronze 0-100 percentage -> gold 0-1 float (suppression text -> NULL)."""
    return (pl.col(col).cast(pl.Float64, strict=False) / 100.0).alias(col)


def _int_count(col: str) -> pl.Expr:
    """Bronze count (string, possibly '236.0') -> Int64 (text -> NULL)."""
    return (
        pl.col(col).cast(pl.Float64, strict=False).cast(pl.Int64, strict=False)
    ).alias(col)


def _null_fill(df: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    """NULL-fill gold columns this family's bronze does not publish."""
    return df.with_columns([pl.lit(None).cast(TARGET_TYPES[c]).alias(c) for c in cols])


# =============================================================================
# Family A: CCRPI Graduation Rates (2018-2020, 2022-2025 releases)
# =============================================================================


def _transform_family_a(
    path: Path, file_year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """CCRPI release — long format with a Graduation Rate Type column.

    Each row's year comes from the bronze `School Year` column (2022-2025
    workbooks carry the prior year's 5-year slice alongside the current
    4-year slice), cross-checked against the filename year. The 2022 file
    omits Target/Flag entirely; 2020 ships them as all-`NA` (COVID CCRPI
    suspension), which SUPPRESSION_VALUES turns into NULL at read.
    """
    sheet = _single_data_sheet(path)
    df = _read_sheet(path, sheet)

    rename = {
        "School Year": "year",
        "System ID": "district_code",
        "School ID": "school_code",
        "Reporting Label": "demographic_raw",
        "Graduation Rate Type": "rate_type_raw",
        "Graduation Rate": "graduation_rate",
    }
    has_target_flag = "Target" in df.columns and "Flag" in df.columns
    if has_target_flag:
        rename.update({"Target": "indicator_target", "Flag": "ccrpi_flag_raw"})
    elif file_year != 2022:
        # Only the 2022 release is known to omit Target/Flag — any other
        # year missing them is a schema surprise, not a known gap.
        raise ValueError(f"{path.name}: Target/Flag columns missing (year != 2022)")
    _require_columns(df, list(rename), f"family A {file_year}")
    df = df.rename(rename).select(list(rename.values()))

    # Year cross-check: a CCRPI workbook carries its filename year and
    # (2022+) the prior year's 5-year slice — nothing else.
    df = df.with_columns(pl.col("year").cast(pl.Int32, strict=False))
    years = set(df["year"].drop_nulls().unique().to_list())
    if df["year"].null_count() or not (
        file_year in years and years <= {file_year - 1, file_year}
    ):
        raise ValueError(
            f"{path.name}: sheet School Year values {sorted(years)} "
            f"inconsistent with filename year {file_year}"
        )
    # Book bronze counts under each row's actual School Year so per-year
    # bronze counts reconcile against gold's year distribution.
    for row in df.group_by("year").len().sort("year").iter_rows(named=True):
        manifest.record_bronze(int(row["year"]), int(row["len"]))

    df = _derive_detail_level(df, f"family A {file_year}")
    df = _normalize_demographic(df, manifest)
    df = _apply_categorical_map(
        df, "rate_type_raw", "rate_type", GRAD_RATE_TYPE_MAP, manifest
    )
    df = df.with_columns(_rate_0_1("graduation_rate"))
    if has_target_flag:
        # The indicator_target is an improvement target on the same 0-100
        # bronze scale as the rate -> 0-1 in gold (within-topic scale
        # invariant, §16).
        df = df.with_columns(_rate_0_1("indicator_target"))
        df = _apply_categorical_map(
            df, "ccrpi_flag_raw", "ccrpi_flag", CCRPI_FLAG_MAP, manifest
        )
    else:
        df = _null_fill(df, ["indicator_target", "ccrpi_flag"])
    df = _null_fill(df, ["num_cohort", "num_graduates"])
    return df.select(STANDARD_COLUMNS)


# =============================================================================
# Family B: Legacy Graduation Rate (2012-2014)
# =============================================================================


def _transform_family_b(
    path: Path, file_year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Pre-CCRPI legacy release — 4-year rate only, drifting column names.

    Sub-variants by column signature: 2012 (REPORTING CATEGORY), 2013
    (REPORTING LABEL), 2014 (Reporting Category Code, no REPORTING LEVEL).
    2012-2013 publish school+district rows only (REPORTING LEVEL is the
    only level source — no "ALL" sentinels in the district column); 2014
    introduces the state row and the ID-sentinel convention.
    """
    sheet = _single_data_sheet(path)
    df = _read_sheet(path, sheet)
    cols = set(df.columns)
    if "REPORTING CATEGORY" in cols:
        demo_col, level_col, variant = "REPORTING CATEGORY", "REPORTING LEVEL", "2012"
    elif "REPORTING LABEL" in cols:
        demo_col, level_col, variant = "REPORTING LABEL", "REPORTING LEVEL", "2013"
    elif "Reporting Category Code" in cols:
        demo_col, level_col, variant = "Reporting Category Code", None, "2014"
    else:
        raise ValueError(
            f"{path.name}: no known legacy signature. Columns: {sorted(cols)}"
        )

    rename = {
        "COHORT YEAR" if variant != "2014" else "Cohort Year": "year",
        "SYSTEM ID" if variant != "2014" else "System ID": "district_code",
        "SCHOOL ID" if variant != "2014" else "School ID": "school_code",
        demo_col: "demographic_raw",
        "GRADUATION RATE" if variant != "2014" else "Graduation Rate": (
            "graduation_rate"
        ),
    }
    keep = list(rename) + ([level_col] if level_col else [])
    _require_columns(df, keep, f"family B {variant}")
    df = df.select(keep).rename(rename)

    # Year cross-check: COHORT YEAR is a single value equal to the filename
    # year in all three legacy files.
    df = df.with_columns(pl.col("year").cast(pl.Int32, strict=False))
    years = set(df["year"].drop_nulls().unique().to_list())
    if df["year"].null_count() or years != {file_year}:
        raise ValueError(
            f"{path.name}: COHORT YEAR values {sorted(years)} != filename "
            f"year {file_year}"
        )
    manifest.record_bronze(file_year, df.height)

    if level_col:
        # 2012-2013: REPORTING LEVEL drives the level (School/System; no
        # state rows exist), then sentinel-derived levels are cross-checked
        # against it (district rows DO carry School ID="ALL").
        df = _derive_detail_level(df, f"family B {variant}")
        df = _check_reporting_level(df, level_col, f"family B {variant}")
    else:
        df = _derive_detail_level(df, f"family B {variant}")

    df = _normalize_demographic(df, manifest)
    df = df.with_columns(
        _rate_0_1("graduation_rate"),
        pl.lit("4_year").alias("rate_type"),
    )
    _record_literal_rate_type(df, "4_year", manifest)
    df = _null_fill(
        df, ["num_cohort", "num_graduates", "indicator_target", "ccrpi_flag"]
    )
    return df.select(STANDARD_COLUMNS)


# =============================================================================
# Family C: Standalone 4-Year Cohort (2015-2022, 2024-2025)
# =============================================================================


def _transform_family_c(
    path: Path, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Standalone 4-year cohort release — two-sheet combine.

    The Subgroup sheet (all 10 demographics, rate only) is the base; the
    All-Students sheet contributes num_cohort/num_graduates, left-joined
    onto the `all`-demographic rows by (detail_level, district, school).
    Re-verified: the All-Students sheet's rate is identical to the Subgroup
    sheet's ALL row (max diff 0.01pp, 12.08.21 file only), and the 30
    All-Students-only entities in the 09_19_18 file are fully suppressed —
    the subgroup-as-base design loses zero data.
    """
    xl = pd.ExcelFile(path)
    sheets = set(xl.sheet_names)
    all_match = sheets & FAMILY_C_ALL_SHEETS
    sub_match = sheets & FAMILY_C_SUBGROUP_SHEETS
    if len(all_match) != 1 or len(sub_match) != 1:
        raise ValueError(
            f"{path.name}: expected one All-Students and one Subgroup sheet; "
            f"found {sorted(sheets)}"
        )

    base_cols = ["Reporting Level", "System ID", "School ID", "Reporting Label"]
    all_df = _read_sheet_required(
        path,
        all_match.pop(),
        required=base_cols + ["Graduation Class Size", "Total Graduated"],
        canonicalize_cd=True,
    )
    sub_df = _read_sheet_required(
        path,
        sub_match.pop(),
        required=base_cols + ["Graduation Rate"],
        canonicalize_cd=True,
    )
    manifest.record_bronze(year, all_df.height + sub_df.height)

    # --- All-Students sheet -> counts frame keyed on geography ----------
    all_df = all_df.select(
        base_cols[:3] + ["Graduation Class Size", "Total Graduated"]
    ).rename(
        {
            "System ID": "district_code",
            "School ID": "school_code",
            "Graduation Class Size": "num_cohort",
            "Total Graduated": "num_graduates",
        }
    )
    all_df = _derive_detail_level(all_df, f"family C {year} (All Students)")
    all_df = _check_reporting_level(
        all_df, "Reporting Level", f"family C {year} (All Students)"
    )
    counts = all_df.with_columns(
        _int_count("num_cohort"), _int_count("num_graduates")
    ).select(
        [
            "detail_level",
            "district_code",
            "school_code",
            "num_cohort",
            "num_graduates",
        ]
    )

    # --- Subgroup sheet -> per-demographic rate rows ---------------------
    sub_df = sub_df.select(base_cols + ["Graduation Rate"]).rename(
        {
            "System ID": "district_code",
            "School ID": "school_code",
            "Reporting Label": "demographic_raw",
            "Graduation Rate": "graduation_rate",
        }
    )
    sub_df = _derive_detail_level(sub_df, f"family C {year} (Subgroup)")
    sub_df = _check_reporting_level(
        sub_df, "Reporting Level", f"family C {year} (Subgroup)"
    )
    sub_df = _normalize_demographic(sub_df, manifest)
    sub_df = sub_df.with_columns(_rate_0_1("graduation_rate"))

    # Counts join: nulls_equal so aggregate keys (state: both IDs NULL;
    # district: school NULL) match. Counts attach only to the `all` rows —
    # the All-Students sheet measures the ALL Students cohort only.
    sub_df = sub_df.join(
        counts,
        on=["detail_level", "district_code", "school_code"],
        how="left",
        nulls_equal=True,
    ).with_columns(
        pl.when(pl.col("demographic") == "all")
        .then(pl.col("num_cohort"))
        .otherwise(None)
        .alias("num_cohort"),
        pl.when(pl.col("demographic") == "all")
        .then(pl.col("num_graduates"))
        .otherwise(None)
        .alias("num_graduates"),
    )

    sub_df = sub_df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.lit("4_year").alias("rate_type"),
    )
    _record_literal_rate_type(sub_df, "4_year", manifest)
    sub_df = _null_fill(sub_df, ["indicator_target", "ccrpi_flag"])
    return sub_df.select(STANDARD_COLUMNS)


# =============================================================================
# Family D: Standalone 5-Year Graduation Rate (2021 only)
# =============================================================================


def _transform_family_d(
    path: Path, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """One-off standalone 5-year release — Subgroup sheet only, rate only.

    The `ALL Student` sheet is a strict subset of the `Subgroup` sheet
    (re-verified: 669 of 671 ALL-row keys, rates byte-identical, zero
    ALL-sheet-only keys) and is skipped to avoid within-file duplication.
    """
    base_cols = ["Reporting Level", "System ID", "School ID", "Reporting Label"]
    df = _read_sheet_required(
        path,
        "Subgroup",
        required=base_cols + ["Graduation Rate"],
        canonicalize_cd=True,
    )
    manifest.record_bronze(year, df.height)
    logger.info(
        "%s: skipping 'ALL Student' sheet — verified strict subset of the "
        "Subgroup sheet (identical rates)",
        path.name,
    )

    df = df.select(base_cols + ["Graduation Rate"]).rename(
        {
            "System ID": "district_code",
            "School ID": "school_code",
            "Reporting Label": "demographic_raw",
            "Graduation Rate": "graduation_rate",
        }
    )
    df = _derive_detail_level(df, f"family D {year}")
    df = _check_reporting_level(df, "Reporting Level", f"family D {year}")
    df = _normalize_demographic(df, manifest)
    df = df.with_columns(
        _rate_0_1("graduation_rate"),
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.lit("5_year").alias("rate_type"),
    )
    _record_literal_rate_type(df, "5_year", manifest)
    df = _null_fill(
        df, ["num_cohort", "num_graduates", "indicator_target", "ccrpi_flag"]
    )
    return df.select(STANDARD_COLUMNS)


# =============================================================================
# Family E: On-Time Graduation Rate (2021-2024)
# =============================================================================


def _transform_family_e(
    path: Path, file_year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """SB 431 on-time release — school-level rows only, rate + both counts.

    Every file ships the statutory definition in row 0 (header auto-detect).
    `Total Enrolled` (first-time 9th graders on Oct 1 four years prior) is
    the on-time denominator and lands in `num_cohort`; rate and counts ship
    together in one file and reconcile to published rounding (≤0.005pp) —
    authored as a contract quality check.
    """
    rename = {
        "Year": "year",
        "System ID": "district_code",
        "School ID": "school_code",
        "Reporting Label": "demographic_raw",
        "Total Enrolled": "num_cohort",
        "Total Graduated": "num_graduates",
        "On-Time Graduation Rate": "graduation_rate",
    }
    df = _read_sheet_required(
        path,
        "On-Time Graduation by Subgroup",
        required=list(rename) + ["Reporting Level"],
    )
    df = df.select(list(rename) + ["Reporting Level"]).rename(rename)

    # Year cross-check: single bronze Year value equal to the filename year.
    df = df.with_columns(pl.col("year").cast(pl.Int32, strict=False))
    years = set(df["year"].drop_nulls().unique().to_list())
    if df["year"].null_count() or years != {file_year}:
        raise ValueError(
            f"{path.name}: Year values {sorted(years)} != filename year {file_year}"
        )
    manifest.record_bronze(file_year, df.height)

    # Every row is school-level (no "ALL" sentinels in this family) —
    # asserted via the Reporting Level column rather than assumed.
    df = df.with_columns(
        pl.lit("school").alias("detail_level"),
        pl.col("district_code").str.zfill(3),
        pl.col("school_code").str.zfill(4),
    )
    df = _check_reporting_level(df, "Reporting Level", f"family E {file_year}")

    df = _normalize_demographic(df, manifest)
    df = df.with_columns(
        _rate_0_1("graduation_rate"),
        _int_count("num_cohort"),
        _int_count("num_graduates"),
        pl.lit("on_time").alias("rate_type"),
    )
    _record_literal_rate_type(df, "on_time", manifest)
    df = _null_fill(df, ["indicator_target", "ccrpi_flag"])
    return df.select(STANDARD_COLUMNS)


# =============================================================================
# Family F: GOSA 4-Year Cohort CSV (2023 count-gap fill)
# =============================================================================


def _transform_family_f(
    path: Path, file_year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """GOSA-portal CSV for the 2023 4-year cohort (supersedes the PDF).

    Supplies the 2023 `num_cohort`/`num_graduates` the CCRPI workbook
    omits, an 18-demographic breakdown, AND a rate — merged at the lowest
    precedence so the CCRPI rate stays authoritative wherever both publish
    a key; the GOSA rate survives only for keys with no CCRPI counterpart.
    """
    df, loss = read_bronze_file(path, return_loss=True, infer_schema_length=0)
    manifest.record_read_loss(
        file_year, path.name, loss["raw_rows"], loss["parsed_rows"]
    )
    rename = {
        "LONG_SCHOOL_YEAR": "school_year_raw",
        "DETAIL_LVL_DESC": "reporting_level_raw",
        "SCHOOL_DSTRCT_CD": "district_code",
        "INSTN_NUMBER": "school_code",
        "LABEL_LVL_1_DESC": "demographic_raw",
        "PROGRAM_TOTAL": "num_graduates",
        "PROGRAM_PERCENT": "graduation_rate",
        "TOTAL_COUNT": "num_cohort",
    }
    _require_columns(df, list(rename), "family F")
    df = df.select(list(rename)).rename(rename)
    manifest.record_bronze(file_year, df.height)

    # Year cross-check: the lone LONG_SCHOOL_YEAR is `2022-23` -> 2023.
    spans = set(df["school_year_raw"].drop_nulls().unique().to_list())
    sheet_years = {parse_school_year(s) for s in spans}
    if sheet_years != {file_year}:
        raise ValueError(
            f"{path.name}: LONG_SCHOOL_YEAR {sorted(spans)} != filename "
            f"year {file_year}"
        )
    df = df.drop("school_year_raw")

    df = _derive_detail_level(df, "family F")
    df = _check_reporting_level(df, "reporting_level_raw", "family F")

    # Demographic labels carry a "Grad Rate -" prefix ("Grad Rate -ALL
    # Students"); strip it so the shared aliases see the bare label.
    df = df.with_columns(pl.col("demographic_raw").str.strip_prefix("Grad Rate -"))
    df = _normalize_demographic(df, manifest)

    df = df.with_columns(
        _rate_0_1("graduation_rate"),
        _int_count("num_cohort"),
        _int_count("num_graduates"),
        pl.lit(file_year).cast(pl.Int32).alias("year"),
        pl.lit("4_year").alias("rate_type"),
    )
    _record_literal_rate_type(df, "4_year", manifest)
    df = _null_fill(df, ["indicator_target", "ccrpi_flag"])
    return df.select(STANDARD_COLUMNS)


# =============================================================================
# File dispatcher
# =============================================================================


def _classify_file(name: str) -> str:
    """Map a bronze filename to its family key.

    Classification is filename-based (not column-based) because Families C
    and D share an identical column schema — only the `4-Year`/`5-Year`
    filename prefix tells the cohort definitions apart.
    """
    if name.startswith("GOSA_"):
        return "f"
    if "On Time" in name:
        return "e"
    if name.startswith("5-Year"):
        return "d"
    if "4-Year Cohort" in name:
        return "c"
    if name[:4] in {"2012", "2013", "2014"}:
        return "b"
    # CCRPI accountability releases ("YYYY CCRPI ..." plus the 2020 file,
    # which dropped the CCRPI prefix but is structurally identical).
    if "CCRPI" in name or name.startswith("2020 Graduation Rate Scores"):
        return "a"
    raise ValueError(f"Cannot classify bronze file into a family: {name}")


def transform_file(
    path: Path, year: int, manifest: TransformManifest
) -> pl.DataFrame | None:
    """Dispatch one bronze file to its family transform; tag provenance.

    Excel reads load whole sheets via pandas (rows cannot be dropped at
    parse time), so read-loss raw == parsed by construction and the record
    call is a structural no-op for every family but F (CSV, accounted via
    the shared reader's raw-line counting).
    """
    family = _classify_file(path.name)
    era = {
        "a": "family_a_ccrpi",
        "b": "family_b_legacy",
        "c": "family_c_standalone_4yr",
        "d": "family_d_standalone_5yr",
        "e": "family_e_on_time",
        "f": "family_f_gosa_csv",
    }[family]
    fn = {
        "a": _transform_family_a,
        "b": _transform_family_b,
        "c": _transform_family_c,
        "d": _transform_family_d,
        "e": _transform_family_e,
        "f": _transform_family_f,
    }[family]
    df = fn(path, year, manifest)
    manifest.record_file(path, year, era, df.height, df.columns)
    if family != "f":
        manifest.record_read_loss(year, path.name, df.height, df.height)
    logger.info(
        "Processed %s (family=%s, year=%d): %d rows",
        path.name,
        family,
        year,
        df.height,
    )
    if df.height == 0:
        logger.warning("%s produced 0 rows — skipping", path.name)
        return None
    return df.with_columns(pl.lit(family).alias("_source_family"))


# =============================================================================
# Cross-family merge
# =============================================================================


def _drop_superseded_a_2021_5yr(
    combined: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Drop Family A's 2021 5-year SCHOOL rows that Family D republishes.

    The 2022 CCRPI workbook's prior-year (2021) 5-year slice disagrees
    materially with Family D's standalone December 2021 release — the
    primary publication for that measure. School-level A rows whose exact
    natural key D republishes are dropped so D's rate wins there;
    Family-A-only school keys (entities D never published) are retained.
    District/state 2021 5-year keys keep Family A's value under the a<d
    merge precedence (their NULL geography keys never match this equi-join)
    — a deliberate v1-parity asymmetry documented in the contract.
    """
    a_mask = (
        (pl.col("_source_family") == "a")
        & (pl.col("year") == 2021)
        & (pl.col("rate_type") == "5_year")
    )
    d_keys = (
        combined.filter(
            (pl.col("_source_family") == "d")
            & (pl.col("year") == 2021)
            & (pl.col("rate_type") == "5_year")
        )
        .select(NATURAL_KEYS)
        .unique()
        .with_columns(pl.lit(True).alias("_d_has_key"))
    )
    before = combined.height
    # NULL keys intentionally do not match (no nulls_equal): only
    # school-level rows (fully populated keys) can be superseded.
    combined = (
        combined.join(d_keys, on=NATURAL_KEYS, how="left")
        .filter(~(a_mask & pl.col("_d_has_key").fill_null(False)))
        .drop("_d_has_key")
    )
    dropped = before - combined.height
    if dropped:
        manifest.record_filtered(
            2021,
            dropped,
            "family A 2021 5-year school rows superseded by the family D "
            "standalone release (primary publication for that measure)",
        )
    return combined


def _merge_cross_family(combined: pl.DataFrame) -> pl.DataFrame:
    """Collapse cross-family overlap via source precedence.

    Rows are rank-sorted by MERGE_PRECEDENCE (stable), then grouped on the
    natural key taking the first non-null value per metric — CCRPI's
    rate/indicator_target/flag and the standalone releases' counts land on one gold
    row. Cross-source rate disagreements (>0.5pp) are logged with samples;
    the highest-precedence published rate always wins.
    """
    rank = pl.DataFrame(
        {
            "_source_family": list(MERGE_PRECEDENCE),
            "_source_rank": list(MERGE_PRECEDENCE.values()),
        }
    )
    metric_cols = [c for c in STANDARD_COLUMNS if c not in NATURAL_KEYS]

    overlap = combined.group_by(NATURAL_KEYS).len().filter(pl.col("len") > 1)
    logger.info(
        "Cross-family merge: %d natural keys covered by >1 source row "
        "(of %d total rows)",
        overlap.height,
        combined.height,
    )

    # Informational: published-rate disagreement across sources (>0.5pp).
    spread = (
        combined.filter(pl.col("graduation_rate").is_not_null())
        .group_by(NATURAL_KEYS)
        .agg(
            (pl.col("graduation_rate").max() - pl.col("graduation_rate").min()).alias(
                "_spread"
            ),
            pl.col("_source_family").unique().sort().alias("_sources"),
        )
        .filter(pl.col("_spread") > RATE_DISAGREEMENT_TOLERANCE)
    )
    if spread.height:
        by_year = spread.group_by("year").len().sort("year")
        logger.warning(
            "Cross-source rate disagreement >%.3f at %d key(s) (%s); the "
            "highest-precedence source's rate is kept",
            RATE_DISAGREEMENT_TOLERANCE,
            spread.height,
            ", ".join(
                f"{r['year']}: {r['len']}" for r in by_year.iter_rows(named=True)
            ),
        )
        for r in spread.sort("_spread", descending=True).head(3).iter_rows(named=True):
            logger.warning(
                "  sample: year=%s district=%s school=%s demo=%s type=%s "
                "sources=%s spread=%.4f",
                r["year"],
                r["district_code"],
                r["school_code"],
                r["demographic"],
                r["rate_type"],
                r["_sources"],
                r["_spread"],
            )

    merged = (
        combined.join(rank, on="_source_family", how="left")
        .sort("_source_rank")
        .group_by(NATURAL_KEYS)
        .agg([pl.col(c).drop_nulls().first().alias(c) for c in metric_cols])
        .select(STANDARD_COLUMNS)
    )
    logger.info("After cross-family merge: %d rows", merged.height)
    return merged


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for ccrpi_graduation_rate."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file. The 125-page 2023 4-year PDF is
    # excluded by extension — its content is superseded by the Family F GOSA
    # CSV (counts + rate) and the 2023 CCRPI workbook (rate/indicator_target/flag).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR, extensions=[".xls", ".xlsx", ".csv"]):
        year = FILENAME_DATA_YEARS.get(path.name) or extract_year_from_filename(
            path.name
        )
        if year is None:
            raise ValueError(f"Cannot determine data year for: {path.name}")
        result = transform_file(path, year, manifest)
        if result is not None:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize columns/dtypes and concatenate across families.
    all_dfs = harmonize_columns(
        all_dfs, STANDARD_COLUMNS + ["_source_family"], TARGET_TYPES
    )
    combined = pl.concat(all_dfs)
    logger.info("Combined %d rows across %d frames", combined.height, len(all_dfs))

    # 3. Collision guard scoped WITHIN each source family: duplicate keys
    # with divergent metrics inside one family mean an alias-collapse bug
    # and must raise. Cross-family overlap is deliberate and is resolved by
    # the documented precedence merge below (which replaces dedup — its
    # group_by guarantees per-key uniqueness; the validator's grain check
    # re-verifies it).
    assert_no_natural_key_collisions(
        combined,
        natural_keys=NATURAL_KEYS + ["_source_family"],
        metric_cols=METRIC_COLUMNS + ["ccrpi_flag"],
    )
    combined = _drop_superseded_a_2021_5yr(combined, manifest)
    combined = _merge_cross_family(combined)

    # 4. Geography nulling (shared domain rules — transform and validator
    # read the same dict). No §4b masks: every observed value is within its
    # metric's possible domain (module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Expected NULL-rate spikes (documented bronze gaps): counts are 100%
    # NULL for 2012-2014 and for every 5-year row; indicator_target/ccrpi_flag
    # are
    # NULL outside CCRPI flag-bearing years (2018-2019, 2022 5-yr,
    # 2023-2025).
    spikes = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spikes.status == "warning":
        logger.warning("NULL-rate spikes (expected bronze gaps): %s", spikes.details)
    validate_output(
        combined,
        required_non_null=["year", "detail_level", "demographic", "rate_type"],
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

    The column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level`` — the contract properties (and the validator's schema
    check) follow it.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Georgia high school graduation rates at the school, district, "
            "and state level by demographic subgroup, 2012-2025. A single "
            "`graduation_rate` column (0-1 scale) carries three distinct "
            "methodologies discriminated by `rate_type`: the federal "
            "adjusted 4-year cohort rate (2012-2025), the 5-year cohort "
            "variant (2018-2024), and the Senate Bill 431 on-time rate "
            "(2021-2024, school-level only). `num_cohort` and "
            "`num_graduates` carry the published denominator/numerator "
            "where a source ships them; CCRPI accountability years add an "
            "improvement `indicator_target` and color `ccrpi_flag`. Sources "
            "span six "
            "release families (CCRPI workbooks, legacy 2012-2014 releases, "
            "standalone 4-year and 5-year cohort releases, SB 431 on-time "
            "releases, and a GOSA-portal CSV that fills the 2023 4-year "
            "count gap), merged by source precedence. This topic publishes "
            "the underlying graduation rates by methodology and demographic; "
            "the CCRPI Graduation Rate component score as it feeds the "
            "accountability index (a distinct benchmarked value, not equal to "
            "the raw 4-year rate) — alongside the overall CCRPI score and the "
            "other four component scores — lives in the "
            "`ccrpi_scoring_by_component` topic (the CCRPI overview)."
        ),
        title="High School Graduation Rates",
        summary=(
            "Georgia high school graduation rates by school, district, and "
            "demographic subgroup, 2012-2025."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Graduation (cohort end) calendar year. For `4_year` "
                    "rows, the spring the cohort was due to graduate; for "
                    "`5_year` rows, the cohort's 4-year year + 1 had already "
                    "passed (the rate is published one year later but keyed "
                    "to the cohort year measured); for `on_time` rows, the "
                    "SB 431 graduation year. Sourced from the bronze year "
                    "column where one exists (CCRPI/legacy/on-time files; "
                    "cross-checked against the filename) and from the "
                    "filename for the standalone cohort releases. The "
                    "February 2018 standalone release carries 2017-cohort "
                    "data and lands in 2017."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "3-digit GOSA district code (zero-padded) for standard "
                    "districts; 7-digit code for state-charter/state-school "
                    "operators; the allowlisted pseudo-district code `RTC` "
                    "(Residential Treatment Center aggregate, data years "
                    "2015-2018 only). NULL for state-level rows. FK to the "
                    "districts dimension."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0103",
                "description": (
                    "4-digit GOSA school code (zero-padded; later bronze "
                    "years strip leading zeros). NULL for district- and "
                    "state-level rows. FK to the schools dimension "
                    "(composite key with district_code)."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "black",
                "short_description": (
                    "Student subgroup the row reports — race, gender, economic "
                    "status, disability, and more; 'all' is the total."
                ),
                "validValues": DEMOGRAPHIC_VALUES,
                "description": (
                    "Canonical demographic code (FK to demographics "
                    "dimension). 10 subgroups are reported across every era "
                    "(all, asian_pacific_islander, black, hispanic, white, "
                    "multiracial, native_american, "
                    "economically_disadvantaged, english_learners, "
                    "students_with_disabilities); 8 more (active_duty, "
                    "female, male, foster_care, homeless, migrant, "
                    "not_economically_disadvantaged, "
                    "students_without_disabilities) appear ONLY in 2023 via "
                    "the GOSA 4-year cohort CSV's wider breakdown. Race uses "
                    "the combined `asian_pacific_islander` bucket — no "
                    "source file publishes separate Asian or Pacific "
                    "Islander rows. `American Indian/Alaskan [Native]` "
                    "label drift folds to `native_american`; the GOSA CSV's "
                    "`Limited English Proficient` folds to "
                    "`english_learners`."
                ),
            },
            {
                "name": "rate_type",
                "type": "string",
                "nullable": False,
                "example": "4_year",
                "short_description": (
                    "Which graduation-rate methodology the row uses: 4-year "
                    "cohort, 5-year cohort, or the SB 431 on-time rate."
                ),
                "validValues": ["4_year", "5_year", "on_time"],
                "description": (
                    "Graduation-rate methodology: `4_year` (federal "
                    "adjusted 4-year cohort rate, 2012-2025), `5_year` "
                    "(5-year cohort variant, 2018-2024), or `on_time` "
                    "(SB 431 statutory measure — continuous enrollment from "
                    "Oct 1 of 9th grade — 2021-2024, school-level rows "
                    "only). Denominator semantics differ per type (see "
                    "num_cohort)."
                ),
            },
            {
                "name": "graduation_rate",
                "type": "float64",
                "unit": "proportion",
                "key_metric": True,
                "short_description": (
                    "Share of the cohort that graduated, on a 0-1 scale; which "
                    "methodology applies is set by rate_type."
                ),
                "example": 0.8544,
                "null_meaning": (
                    "Suppressed by GaDOE/GOSA (`TFS`/`Too Few Students`, "
                    "`No Data`, `No Data Found`) or not published for this "
                    "key by any source."
                ),
                "description": (
                    "Graduation rate on the 0-1 decimal scale (bronze ships "
                    "0-100; divided by 100). Interpretation follows "
                    "rate_type. For overlapping 4-year keys the CCRPI "
                    "accountability value wins by source precedence; "
                    "standalone cohort releases fill years CCRPI does not "
                    "cover, and ~200 small-cell 2023 keys carry the GOSA "
                    "CSV rate that the CCRPI workbook suppressed. CAVEAT: "
                    "the rate and the count pair can come from releases "
                    "published at different cutoffs — do NOT assume "
                    "num_graduates / num_cohort equals graduation_rate "
                    "for `4_year` rows (it reconciles only to ~0.4pp even "
                    "within one release). For `on_time` rows the identity "
                    "holds to published rounding and is enforced as a "
                    "quality check."
                ),
            },
            {
                "name": "num_cohort",
                "type": "int64",
                "unit": "count",
                "metric_component": "denominator",
                "example": 134822,
                "null_meaning": (
                    "Source published no denominator for this key: all "
                    "2012-2014 and `5_year` rows, non-`all` demographics in "
                    "standalone 4-year years (counts ship for ALL Students "
                    "only, except 2023's GOSA CSV), or suppressed (TFS)."
                ),
                "description": (
                    "Published cohort denominator. For `4_year` rows: the "
                    "federal adjusted cohort (first-time 9th graders four "
                    "years prior, adjusted for transfers) from the "
                    "standalone cohort releases — ALL-Students demographic "
                    "only in 2015-2022/2024-2025, all 18 demographics in "
                    "2023 via the GOSA CSV. For `on_time` rows: `Total "
                    "Enrolled` per SB 431 (continuous enrollment from Oct "
                    "1). Never published for `5_year` rows or the 2012-2014 "
                    "legacy years."
                ),
            },
            {
                "name": "num_graduates",
                "type": "int64",
                "unit": "count",
                "metric_component": "numerator",
                "example": 113735,
                "null_meaning": (
                    "Source published no numerator for this key (same "
                    "coverage as num_cohort) or suppressed (TFS)."
                ),
                "description": (
                    "Published count of graduates (cohort numerator). Same "
                    "source coverage as num_cohort. Never exceeds "
                    "num_cohort (0 violations source-wide; enforced as a "
                    "quality check). CAVEAT: published at a different "
                    "cutoff than the CCRPI graduation_rate for 4-year rows "
                    "— see graduation_rate."
                ),
            },
            {
                "name": "indicator_target",
                "type": "float64",
                "unit": "proportion",
                "example": 0.8454,
                "null_meaning": (
                    "Row outside CCRPI flag-bearing coverage (see "
                    "description), suppressed (`TFS`), or the 2020 COVID "
                    "suspension (all `NA` at source)."
                ),
                "description": (
                    "CCRPI improvement target on the same 0-1 scale as "
                    "graduation_rate (observed range [0.022, 0.9]). "
                    "Published for 4-year and 5-year rows in 2018-2019 and "
                    "2023-2025 releases: years 2018, 2019, 2023, 2024 carry "
                    "both rate types, 2022 carries 5-year only (the 2023 "
                    "workbook's prior-year slice; the 2022 release itself "
                    "omitted the column), 2025 carries 4-year only (its "
                    "5-year slice lands in 2024). 2020 is all NULL (COVID "
                    "CCRPI suspension). NOT cross-topic comparable: each "
                    "CCRPI topic's target inherits its companion metric's "
                    "scale (§16)."
                ),
            },
            {
                "name": "ccrpi_flag",
                "type": "string",
                "exclude_from_grain": True,
                "example": "green",
                "short_description": (
                    "CCRPI performance color (green/yellow/red) for whether the "
                    "school met its graduation improvement target."
                ),
                "validValues": sorted(set(CCRPI_FLAG_MAP.values())),
                "null_meaning": (
                    "Row outside CCRPI flag-bearing coverage (same years as "
                    "indicator_target), bronze `NA` (no indicator_target to "
                    "compare), or a non-CCRPI rate_type (`on_time`)."
                ),
                "description": (
                    "CCRPI performance color flag: `green` (met the "
                    "improvement target), `yellow` (improved but short of "
                    "target), or `red` (did not improve); bronze G/Y/R "
                    "recoded per §16. The graduation indicator never awards "
                    "`green_star` in any bronze year (2018-2025, verified). "
                    "Same publication coverage as indicator_target. A derived "
                    "performance attribute functionally determined by the "
                    "rest of the row key, so it is excluded from the "
                    "contract grain."
                ),
            },
        ],
        source="Georgia Insights (GaDOE) / GOSA",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        notes=[
            (
                "Six bronze release families merge into one fact table: "
                "CCRPI workbooks (rate/indicator_target/flag), legacy 2012-2014 "
                "releases, standalone 4-year cohort releases (counts for "
                "the ALL Students demographic), a one-off standalone "
                "5-year release (2021), SB 431 on-time releases "
                "(2021-2024), and a GOSA-portal CSV that fills the 2023 "
                "4-year count gap with an 18-demographic breakdown. "
                "Overlapping keys resolve by source precedence (CCRPI "
                "wins); each metric takes the highest-precedence non-null "
                "value, so a single row can mix the CCRPI rate with "
                "standalone-release counts published at a different "
                "cutoff."
            ),
            (
                "There is no 2021 CCRPI release (COVID suspension): 2021 "
                "4-year data comes from the standalone release and 2021 "
                "5-year data from the one-off standalone 5-year release. "
                "2021 5-year SCHOOL rows republished by that standalone "
                "release supersede the 2022 CCRPI workbook's prior-year "
                "slice (which disagrees materially); district/state 2021 "
                "5-year rows retain the CCRPI-workbook value under the "
                "merge precedence — an asymmetry preserved from the "
                "approved v1 baseline."
            ),
            (
                "The 125-page PDF `4-Year Cohort Graduation Rate State "
                "District School by Subgroups_12.14.23.pdf` is not "
                "ingested: the 2023 CCRPI workbook supplies the 2023 "
                "rate/indicator_target/flag and the GOSA CSV "
                "`GOSA_4-Year_Cohort_Graduation_Rate_2022-23_12.15.23.csv` "
                "supplies the counts (plus rates for ~200 small-cell keys "
                "the CCRPI workbook suppressed)."
            ),
            (
                "Counts coverage: num_cohort/num_graduates exist only "
                "where a source published them — ALL-Students rows in "
                "standalone 4-year years (2015-2022, 2024-2025), all "
                "demographics in 2023 (GOSA CSV), and every on_time row. "
                "They are never published for 5-year rows or 2012-2014."
            ),
            (
                "Do NOT assume num_graduates / num_cohort equals "
                "graduation_rate for `4_year` rows: the rate (CCRPI "
                "snapshot) and counts (standalone cohort releases) are "
                "published at different cutoffs, and even within one "
                "release reconcile only to ~0.4pp. The identity holds to "
                "published rounding for `on_time` rows and is enforced as "
                "a quality check there."
            ),
            (
                "The `RTC` (Residential Treatment Center) pseudo-district "
                "aggregates state RTC facilities in the standalone 4-year "
                "releases for data years 2015-2018 and is an allowlisted "
                "district_code in the districts dimension (district_type "
                "`state_special`)."
            ),
            (
                "2012-2013 publish school+district rows only (state "
                "aggregates begin in 2014); on_time rows are school-level "
                "only. The 2025 partition is thinner than 2024 because "
                "the 2025 CCRPI workbook's 5-year slice lands in 2024 and "
                "no on-time release exists yet for 2025."
            ),
            (
                "Race uses the combined `asian_pacific_islander` bucket: "
                "every file publishes the explicit `Asian/Pacific "
                "Islander` label and never separate Asian or Pacific "
                "Islander rows; the split keys are never emitted (§5b)."
            ),
            (
                "Suppression markers (`TFS`, `Too Few Students`, `No "
                "Data`, `No Data Found`, `NA`) become NULL. The 2018 "
                "standalone release's All-Students sheet lists 30 "
                "entities absent from its Subgroup sheet — all fully "
                "suppressed, so no data is lost by the subgroup-as-base "
                "two-sheet combine."
            ),
        ],
        quality_checks=[
            {
                "name": "num_graduates_not_exceeding_num_cohort",
                "description": (
                    "The numerator never exceeds the denominator on rows "
                    "where both counts are published. Verified against "
                    "bronze: 0 violations in every release family."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE num_graduates IS "
                    "NOT NULL AND num_cohort IS NOT NULL AND "
                    "num_graduates > num_cohort"
                ),
                "mustBe": 0,
            },
            {
                "name": "on_time_rate_reconciles_with_counts",
                "description": (
                    "For on_time rows the rate and both counts ship in one "
                    "file and reconcile exactly to published rounding: "
                    "|graduation_rate - num_graduates/num_cohort| <= "
                    "0.0001 (bronze max deviation 0.005 on the 0-100 scale "
                    "= half the last published decimal). Scoped to on_time "
                    "— 4-year rows mix sources at different cutoffs and "
                    "legitimately do not reconcile."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE rate_type = "
                    "'on_time' AND graduation_rate IS NOT NULL AND "
                    "num_graduates IS NOT NULL AND num_cohort IS NOT "
                    "NULL AND num_cohort > 0 AND ABS(graduation_rate - "
                    "CAST(num_graduates AS DOUBLE) / num_cohort) > "
                    "0.0001"
                ),
                "mustBe": 0,
            },
            {
                "name": "on_time_counts_co_null",
                "description": (
                    "On-time suppression is all-or-nothing: rate, "
                    "num_cohort, and num_graduates are either all "
                    "published or all NULL on every on_time row (verified "
                    "against bronze 2021-2024: 0 partial rows)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE rate_type = "
                    "'on_time' AND ((num_cohort IS NULL) <> "
                    "(num_graduates IS NULL) OR (num_cohort IS NULL) <> "
                    "(graduation_rate IS NULL))"
                ),
                "mustBe": 0,
            },
            {
                "name": "on_time_rows_are_school_level",
                "description": (
                    "Structural: the SB 431 on-time release publishes "
                    "school-level rows only — every on_time row carries "
                    "both geography keys (self-scoped via geography "
                    "NULL-ness; there are no district or state on_time "
                    "aggregates)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE rate_type = "
                    "'on_time' AND (district_code IS NULL OR school_code "
                    "IS NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "five_year_rows_never_carry_counts",
                "description": (
                    "Structural: no source publishes 5-year cohort counts "
                    "— num_cohort and num_graduates are NULL on every "
                    "5_year row."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE rate_type = "
                    "'5_year' AND (num_cohort IS NOT NULL OR "
                    "num_graduates IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "indicator_target_flag_publication_coverage",
                "description": (
                    "indicator_target and ccrpi_flag are non-NULL only in "
                    "the CCRPI "
                    "flag-bearing (year, rate_type) slices: 2018/2019/2023/"
                    "2024 both cohort types, 2022 5-year only (the 2022 "
                    "release omitted the columns; its 5-year slice arrives "
                    "via the 2023 workbook), 2025 4-year only. This also "
                    "pins the 2020 COVID suppression (all NA at source) "
                    "and that on_time rows never carry CCRPI constructs."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE (indicator_target "
                    "IS NOT NULL OR ccrpi_flag IS NOT NULL) AND NOT ((year IN "
                    "(2018, 2019, 2023, 2024) AND rate_type IN ('4_year', "
                    "'5_year')) OR (year = 2022 AND rate_type = '5_year') "
                    "OR (year = 2025 AND rate_type = '4_year'))"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
