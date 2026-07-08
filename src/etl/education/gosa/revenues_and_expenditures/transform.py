"""Transform bronze revenues_and_expenditures files into gold fact tables.

Source: Governor's Office of Student Achievement (GOSA) — K-12 Revenues and
Expenditures, school years 2010-11 through 2023-24 (14 bronze CSVs, one school
year each; filename year = spring/ending year). Each bronze row reports one
(rev_exp_category, rev_exp_subcategory) cell for one entity: a total dollar
amount (``rev_exp_value``) and a per-FTE dollar amount (``rev_exp_per_pupil``)
at state, district, or school detail.

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Bronze is already tidy long; keep that shape.** Two categorical columns
  (``rev_exp_category``: 2 values, ``rev_exp_subcategory``: 17 values) plus two
  monetary metrics. No unpivot needed.
- **No ``demographic`` column.** The source has no demographic breakout —
  every row is a monetary aggregate at its geography level (§5: omit the
  column entirely).
- **Three eras, era detection by column signature.** Era 1 (2023-2024)
  renames every column (``LONG_SCHOOL_YEAR`` / ``SCHOOL_DSTRCT_CD`` /
  ``INSTN_NUMBER`` / ``DETAIL_LVL_DESC`` ...); Era 3 (2012-2014) adds
  ``FTE_COUNT`` to the base 9-column schema; Eras 2+4 (2011, 2015-2022) share
  one identical 9-column schema and are handled by a single branch (the
  bronze doc lists them separately only because Era 3 breaks contiguity).
- **Detail level.** Era 2-4 derive it from the ``ALL`` sentinels in the ID
  columns (both ALL -> state; school ALL only -> district; else school).
  Era 1 carries an explicit ``DETAIL_LVL_DESC`` whose fourth value
  ``DOE OTHER`` (GNETS, alternative schools, Pre-K centers, central offices,
  RESA admin units; 9,798 rows/year) is split by ``INSTN_NUMBER``:
    - real institution number (9,526 rows/year) -> ``school``. These same
      entities appeared under ``school`` in Era 2-4 via the ALL-marker
      heuristic (their institution codes already existed pre-Era-1), so this
      keeps history comparable — option (a) in the bronze doc.
    - ``INSTN_NUMBER='ALL'`` (272 rows/year = 16 RESA-style rollups x 17
      categories) -> ``district``. Pre-Era-1 years captured these same RESA
      codes (850-888) as district rows via the ALL-marker heuristic, and the
      bronze doc excludes them from the school slice only. Same convention
      as salaries_and_benefits.
  Both splits are recorded as manifest reclassification events and attested
  in the detail_level categorical mapping (the rollup branch under the
  synthetic key ``DOE OTHER (INSTN_NUMBER=ALL)``).
- **``FTE_COUNT`` (Era 3 only) is dropped.** Only 3 of 14 years carry it and
  ``rev_exp_per_pupil`` exists in every era as its own column. Because the FTE
  denominator is not carried to gold, a per-FTE-vs-value reconciliation
  quality check is NOT derivable in gold SQL — verified at transform time
  instead: in Era 3, ``Dollars per FTE`` = ``REV_EXP_VALUE / FTE_COUNT``
  within 0.005 wherever FTE is non-null and non-zero.
- **No §4b masks; negative dollars are real data.** Signed dollars have no
  bounded scale, so no value here is *impossible* — bronze publishes genuine
  negative adjustments in both metrics in every year (e.g. 109 negative
  ``REV_EXP_VALUE`` rows in 2011, min -4.86e7 in 2013). Preserved as-is;
  ``unit: currency`` derives no range check (per src/etl/education/CLAUDE.md).
- **The per-FTE metric is not always a true per-pupil amount.** Verified
  artifacts where ``rev_exp_per_pupil == rev_exp_value`` verbatim: the ENTIRE
  school detail level of the 2024 file (15,678/15,678 nonzero School rows +
  all DOE OTHER rows — traditional schools included, so 2024 school-level
  per-FTE values carry no per-pupil information), all 9,798 DOE OTHER rows
  of the 2023 file (plus 151 other nonzero 2023 School rows), and the
  10,414 null-FTE_COUNT rows in the 2012 file. District/state rows in
  2023-2024 carry true per-FTE values. Documented in the contract;
  preserved (the values are what GOSA publishes, and they are not
  impossible on a dollar scale).
- **``rev_exp_per_pupil`` NULLs are confined to Era 3** (667 rows: 13 in 2012
  where FTE_COUNT == 0, 382 in 2013 and 272 in 2014 where FTE_COUNT is
  NULL). Legitimate missing denominators, not suppression — pinned by the
  ``rev_exp_per_pupil_null_only_in_2012_2014`` quality check.
- **No suppression anywhere.** Unusually for GOSA, neither monetary column
  carries TFS/``*``-style markers in any year (verified: zero cast-induced
  NULLs in all 14 files). ``suppressed_to_null=False`` is passed to the
  emitter and ``rev_exp_value_never_null`` pins the completeness fact.
- **Structural completeness facts (verified on all 14 files).** Every year
  has exactly 17 state rows covering all 17 (rev_exp_category,
  rev_exp_subcategory) pairs, and every district-detail entity (districts,
  RESAs, charters) carries exactly 17 rows covering all 17 pairs.
  School-detail entities do NOT all carry 17 rows (some publish partial
  subcategory sets), so no school-level completeness check is authored.
- **Subcategory <-> category containment (verified on all 14 files).** Revenue
  rows carry only the 6 revenue-source subcategories; expenditure rows only
  the 11 expenditure-function subcategories; the two sets are disjoint and
  identical in every year. Pinned by
  ``rev_exp_category_subcategory_pairs_valid``.
- **ID formatting.** ``ALL`` sentinel -> NULL before zfill so the literal
  string can never be emitted as a code. zfill(3) pads district codes
  (7-char commission/state-charter compounds pass through unchanged — never
  truncated); zfill(4) pads school codes — required for the 2012 file, where
  a minority of school codes are published as 3-digit (``110``, ``106``)
  for the same schools that appear as ``0110``, ``0106`` everywhere else.
- **Dedup tie-break.** Each bronze file is one school year, years never
  overlap, and the per-file detail-level grain is unique in all 14 files
  (verified: zero duplicate key groups). ``assert_no_natural_key_collisions``
  guards regressions; ``sort_col="rev_exp_value"`` is the documented safety
  net (prefer the row with the larger reported dollar value over a
  null/zero placeholder if a future republication introduces duplicates).
- **Vocabulary (§16).** Column names are topic-specific (``rev_exp_category``,
  ``rev_exp_subcategory``, ``rev_exp_value``, ``rev_exp_per_pupil``) and
  collide with no registry entry. Categorical values spell out
  ``k12_expenditures`` /
  ``k12_revenues``; no cross-topic column canonicalizes "expenditure" here,
  so the deferred attendance ``pct_expense_*`` naming question is untouched.
- **Era 2-4 typo preserved in mapping.** Bronze ``School food Services``
  (lowercase ``food``) is an upstream-report typo present in every year; it
  maps to ``school_food_services``.
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

TOPIC = "revenues_and_expenditures"
BRONZE_DIR = Path("data/bronze/education/gosa/revenues_and_expenditures")
GOLD_DIR = Path("data/gold/education/revenues_and_expenditures")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Aggregate-row sentinel in the bronze ID columns (DISTRICT_CODE/SCHOOL_CODE in
# Era 2-4, SCHOOL_DSTRCT_CD/INSTN_NUMBER in Era 1). Becomes NULL in gold.
GEOGRAPHY_SENTINEL = "ALL"

# Bronze Revenues/Expenditures -> gold rev_exp_category. Two values, identical
# in every year (verified across all 14 files).
REV_EXP_TYPE_MAP: dict[str, str] = {
    "K-12 Revenues": "k12_revenues",
    "K-12 Expenditures": "k12_expenditures",
}

# Bronze Description -> gold rev_exp_subcategory. 17 functional subcategories,
# identical in every year (verified). `School food Services` preserves the
# upstream lowercase-`food` typo on the bronze side; gold normalizes the casing.
CATEGORY_MAP: dict[str, str] = {
    "Debt Services": "debt_services",
    "Federal": "federal",
    "General Administration": "general_administration",
    "Instruction": "instruction",
    "Instructional Support": "instructional_support",
    "Local": "local",
    "Maintenance and Operations": "maintenance_and_operations",
    "Media": "media",
    "Other": "other",
    "Pupil Services": "pupil_services",
    "Renovation and Capital Projects": "renovation_and_capital_projects",
    "School Administration": "school_administration",
    "School food Services": "school_food_services",
    "State Lottery": "state_lottery",
    "State Other": "state_other",
    "State QBE": "state_qbe",
    "Transportation": "transportation",
}

# The 6 revenue-source subcategories vs the 11 expenditure-function
# subcategories. Disjoint and identical in every year (verified on all 14
# bronze files); drives the rev_exp_category_subcategory_pairs_valid quality
# check.
REVENUE_CATEGORIES: list[str] = [
    "federal",
    "local",
    "other",
    "state_lottery",
    "state_other",
    "state_qbe",
]
EXPENDITURE_CATEGORIES: list[str] = [
    "debt_services",
    "general_administration",
    "instruction",
    "instructional_support",
    "maintenance_and_operations",
    "media",
    "pupil_services",
    "renovation_and_capital_projects",
    "school_administration",
    "school_food_services",
    "transportation",
]

# Era 1 explicit detail levels. `DOE OTHER` is split by INSTN_NUMBER at
# runtime (see _transform_era_1): real institution number -> school
# (Era 2-4 comparability), INSTN_NUMBER='ALL' -> district (RESA rollups).
# This dict carries the base mapping; the rollup branch is attested in the
# manifest under the synthetic key `DOE OTHER (INSTN_NUMBER=ALL)`.
DETAIL_LEVEL_MAP: dict[str, str] = {
    "State": "state",
    "District": "district",
    "School": "school",
    "DOE OTHER": "school",
}

# Era-detection signatures, most-specific first: Era 1 has wholly renamed
# columns; Era 3 is Era 2-4 plus FTE_COUNT, so it must be checked first.
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_1": [
        "LONG_SCHOOL_YEAR",
        "DETAIL_LVL_DESC",
        "SCHOOL_DSTRCT_CD",
        "INSTN_NUMBER",
        "REVENUES/EXPENDITURES",
        "DESCRIPTION",
        "REV_EXP_VALUE",
        "DOLLARS_PER_FTE",
    ],
    "era_3": [
        "SCHOOL_YEAR",
        "DISTRICT_CODE",
        "SCHOOL_CODE",
        "Revenues/Expenditures",
        "Description",
        "REV_EXP_VALUE",
        "Dollars per FTE",
        "FTE_COUNT",
    ],
    "era_2_4": [
        "SCHOOL_YEAR",
        "DISTRICT_CODE",
        "SCHOOL_CODE",
        "Revenues/Expenditures",
        "Description",
        "REV_EXP_VALUE",
        "Dollars per FTE",
    ],
}

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "rev_exp_category",
    "rev_exp_subcategory",
    "rev_exp_value",
    "rev_exp_per_pupil",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "rev_exp_category": pl.Utf8,
    "rev_exp_subcategory": pl.Utf8,
    "rev_exp_value": pl.Float64,
    "rev_exp_per_pupil": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = ["rev_exp_value", "rev_exp_per_pupil"]

NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "rev_exp_category",
    "rev_exp_subcategory",
    "detail_level",
]


# =============================================================================
# Shared helpers
# =============================================================================


def _require_columns(df: pl.DataFrame, required: list[str], label: str) -> None:
    """Raise if any expected bronze column is absent (rename-coverage guard).

    An unmatched source column silently becomes NULL in gold — the most
    common data-loss bug — so a missing column is a hard stop, not a warning.
    """
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"{label}: expected bronze column(s) missing: {missing}. "
            f"Present: {df.columns}"
        )


def _to_float_expr(col: str) -> pl.Expr:
    """Cast an all-string bronze monetary column to Float64.

    strict=False is defensive only: bronze publishes no suppression markers
    in either monetary column (verified: zero cast-induced NULLs in all 14
    files), but a future marker would become NULL instead of crashing.
    Negative values are legitimate budget adjustments — never clamped.
    """
    return pl.col(col).str.strip_chars().cast(pl.Float64, strict=False)


def _format_id_expr(col: str, width: int) -> pl.Expr:
    """Map the ALL sentinel to NULL, then zero-pad a bronze ID column.

    Sentinel-first ordering guarantees the literal string `ALL` can never be
    emitted as a code. zfill pads 3-digit district / 4-digit school codes
    (incl. the 2012 file's 3-digit school codes) and leaves 7-char
    commission/state-charter compound codes unchanged — never truncate.
    """
    cleaned = pl.col(col).str.strip_chars()
    return (
        pl.when(cleaned == GEOGRAPHY_SENTINEL)
        .then(None)
        .otherwise(cleaned.str.zfill(width))
    )


def _recode_rev_exp_type(
    df: pl.DataFrame, source_col: str, manifest: TransformManifest
) -> pl.DataFrame:
    """Recode the bronze Revenues/Expenditures bucket to gold rev_exp_category.

    Shared across eras — only the bronze column name differs. Unmapped values
    become NULL and trip the manifest's unmapped guard at write() time.
    """
    df = df.with_columns(
        pl.col(source_col)
        .str.strip_chars()
        .replace_strict(REV_EXP_TYPE_MAP, default=None)
        .alias("rev_exp_category")
    )
    manifest.record_categorical(
        column="rev_exp_category",
        map_dict=REV_EXP_TYPE_MAP,
        bronze_series=df[source_col],
        gold_series=df["rev_exp_category"],
    )
    return df


def _recode_category(
    df: pl.DataFrame, source_col: str, manifest: TransformManifest
) -> pl.DataFrame:
    """Recode the bronze Description functional category to gold rev_exp_subcategory.

    Shared across eras — 17 identical values in every year, including the
    upstream `School food Services` lowercase-`food` typo.
    """
    df = df.with_columns(
        pl.col(source_col)
        .str.strip_chars()
        .replace_strict(CATEGORY_MAP, default=None)
        .alias("rev_exp_subcategory")
    )
    manifest.record_categorical(
        column="rev_exp_subcategory",
        map_dict=CATEGORY_MAP,
        bronze_series=df[source_col],
        gold_series=df["rev_exp_subcategory"],
    )
    return df


# =============================================================================
# Era transforms
# =============================================================================


def _transform_era_2_4(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Transform the shared 9-column schema (2011, 2015-2022; Era 3 delegates).

    Detail level is derived from the ALL sentinels (no explicit column in
    these eras): both IDs ALL -> state, school ALL only -> district, else
    school. Verified spot counts: 17 state rows in every year.
    """
    _require_columns(df, ERA_SIGNATURES["era_2_4"], f"era_2_4 {year}")

    # Detail level from the sentinel pattern, then IDs (sentinel -> NULL,
    # zero-padded), then metric casts — all era-independent from here on.
    df = df.with_columns(
        pl.when(
            (pl.col("DISTRICT_CODE").str.strip_chars() == GEOGRAPHY_SENTINEL)
            & (pl.col("SCHOOL_CODE").str.strip_chars() == GEOGRAPHY_SENTINEL)
        )
        .then(pl.lit("state"))
        .when(pl.col("SCHOOL_CODE").str.strip_chars() == GEOGRAPHY_SENTINEL)
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .alias("detail_level"),
    )
    df = df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        _format_id_expr("DISTRICT_CODE", 3).alias("district_code"),
        _format_id_expr("SCHOOL_CODE", 4).alias("school_code"),
        _to_float_expr("REV_EXP_VALUE").alias("rev_exp_value"),
        _to_float_expr("Dollars per FTE").alias("rev_exp_per_pupil"),
    )
    df = _recode_rev_exp_type(df, "Revenues/Expenditures", manifest)
    df = _recode_category(df, "Description", manifest)

    # Drops DISTRICT_NAME / SCHOOL_NAME (dimension attributes, not facts).
    return df.select(STANDARD_COLUMNS)


def _transform_era_3(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Transform Era 3 (2012-2014): the 9-column schema plus FTE_COUNT.

    FTE_COUNT is dropped (3 of 14 years only; rev_exp_per_pupil exists in every
    era — see module docstring). Verified before dropping: Dollars per FTE =
    REV_EXP_VALUE / FTE_COUNT within 0.005 wherever FTE is non-null/non-zero,
    so dropping the denominator loses no information the per-FTE column
    doesn't already carry.
    """
    _require_columns(df, ERA_SIGNATURES["era_3"], f"era_3 {year}")
    return _transform_era_2_4(df.drop("FTE_COUNT"), year, manifest)


def _transform_era_1(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Transform Era 1 (2023-2024): renamed columns + explicit DOE OTHER level.

    DOE OTHER rows are split by INSTN_NUMBER before the detail-level map is
    applied (see module docstring): real institution numbers -> school
    (9,526/year; Era 2-4 comparability), INSTN_NUMBER='ALL' -> district
    (272/year; the 16 RESA-style rollups x 17 categories). Both groups are
    recorded as manifest reclassification events.
    """
    _require_columns(df, ERA_SIGNATURES["era_1"], f"era_1 {year}")

    # Hard-stop if the constant report-name column carries unexpected values:
    # anything else means another GOSA report's rows are mixed into bronze.
    rpt_names = df["#RPT_NAME"].drop_nulls().unique().to_list()
    if rpt_names != ["Revenue_and_Expenditures"]:
        raise ValueError(f"era_1 {year}: unexpected #RPT_NAME values {rpt_names}")

    is_doe_other = pl.col("DETAIL_LVL_DESC").str.strip_chars() == "DOE OTHER"
    is_instn_all = pl.col("INSTN_NUMBER").str.strip_chars() == GEOGRAPHY_SENTINEL

    # Manifest artifacts for the two DOE OTHER routing groups (4.3c): these
    # rows cross detail levels relative to their bronze label, so the repair
    # must be verifiable from the manifest, not just from log lines.
    n_rollup = df.filter(is_doe_other & is_instn_all).height
    n_school = df.filter(is_doe_other & ~is_instn_all).height
    manifest.record_reclassified(
        year,
        n_school,
        "DOE OTHER rows with a real INSTN_NUMBER routed to detail_level="
        "'school' (same entities appeared under school in Era 2-4 via the "
        "ALL-marker heuristic)",
    )
    manifest.record_reclassified(
        year,
        n_rollup,
        "DOE OTHER rows with INSTN_NUMBER='ALL' routed to detail_level="
        "'district' (RESA-style rollups, district codes 850-888; Era 2-4 "
        "carried the same codes as district rows)",
    )
    logger.info(
        "Year %d: DOE OTHER split — %d rows -> school, %d rows -> district",
        year,
        n_school,
        n_rollup,
    )

    # Detail level: the explicit DETAIL_LVL_DESC is authoritative; only the
    # DOE OTHER + INSTN_NUMBER='ALL' branch overrides the base map.
    df = df.with_columns(
        pl.when(is_doe_other & is_instn_all)
        .then(pl.lit("district"))
        .otherwise(
            pl.col("DETAIL_LVL_DESC")
            .str.strip_chars()
            .replace_strict(DETAIL_LEVEL_MAP, default=None)
        )
        .alias("detail_level"),
    )
    # Attest the conditional split in the manifest: the rollup branch is
    # keyed under a synthetic bronze label so both DOE OTHER outcomes are
    # separately reviewable.
    bronze_detail = df.select(
        pl.when(is_doe_other & is_instn_all)
        .then(pl.lit("DOE OTHER (INSTN_NUMBER=ALL)"))
        .otherwise(pl.col("DETAIL_LVL_DESC").str.strip_chars())
        .alias("DETAIL_LVL_DESC")
    )["DETAIL_LVL_DESC"]
    manifest.record_categorical(
        column="detail_level",
        map_dict={**DETAIL_LEVEL_MAP, "DOE OTHER (INSTN_NUMBER=ALL)": "district"},
        bronze_series=bronze_detail,
        gold_series=df["detail_level"],
    )

    df = df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        _format_id_expr("SCHOOL_DSTRCT_CD", 3).alias("district_code"),
        _format_id_expr("INSTN_NUMBER", 4).alias("school_code"),
        _to_float_expr("REV_EXP_VALUE").alias("rev_exp_value"),
        _to_float_expr("DOLLARS_PER_FTE").alias("rev_exp_per_pupil"),
    )
    df = _recode_rev_exp_type(df, "REVENUES/EXPENDITURES", manifest)
    df = _recode_category(df, "DESCRIPTION", manifest)

    # Drops #RPT_NAME (constant), SCHOOL_DSTRCT_NM / INSTN_NAME (dimension
    # attributes), and GRADES_SERVED_DESC (school metadata, not a fact).
    return df.select(STANDARD_COLUMNS)


# =============================================================================
# File dispatcher
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read one bronze CSV, detect its era, and transform it to gold shape.

    Year resolution: every file carries exactly one SCHOOL_YEAR /
    LONG_SCHOOL_YEAR value whose ending year must agree with the filename
    year (cross-verified for all 14 files in the bronze doc) — a misnamed
    file cannot silently mislabel a whole year.
    """
    # All-string read: zero-padded codes and the ALL sentinels are never
    # schema-inference casualties (4.3b); metrics are cast explicitly later.
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

    year_col = "LONG_SCHOOL_YEAR" if era == "era_1" else "SCHOOL_YEAR"
    school_years = df[year_col].drop_nulls().unique().to_list()
    if len(school_years) != 1:
        raise ValueError(f"{path.name}: expected one {year_col}, got {school_years}")
    year = parse_school_year(school_years[0])
    if year != filename_year:
        raise ValueError(
            f"{path.name}: {year_col} ending year {year} disagrees with "
            f"filename year {filename_year}"
        )

    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)
    if df.height == 0:
        logger.warning("Year %d: bronze file is empty, skipping %s", year, path.name)
        return None
    logger.info(
        "Processing %s as %s (year %d, %d rows)", path.name, era, year, df.height
    )

    if era == "era_1":
        return _transform_era_1(df, year, manifest)
    if era == "era_3":
        return _transform_era_3(df, year, manifest)
    return _transform_era_2_4(df, year, manifest)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for revenues_and_expenditures."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file (read-loss accounted per file).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR, extensions=[".csv"]):
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
    # mean an era-routing or DOE-OTHER-split bug and must raise, not be
    # silently deduped away.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: each file is one school year, years never overlap, and the
    # per-file detail-level grain is unique in all 14 files (verified: zero
    # duplicate key groups) — so dedup is a safety net only. Prefer the row
    # with the larger reported dollar value over a null/zero placeholder.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=[
            "year",
            "district_code",
            "school_code",
            "rev_exp_category",
            "rev_exp_subcategory",
        ],
        district_keys=[
            "year",
            "district_code",
            "rev_exp_category",
            "rev_exp_subcategory",
        ],
        state_keys=["year", "rev_exp_category", "rev_exp_subcategory"],
        sort_col="rev_exp_value",
    )

    # 4. Geography nulling (shared domain rules — idempotent here because the
    # ALL->NULL sentinel mapping already nulled aggregate IDs, but keeps the
    # transform and validator on one rule source). No §4b masks: signed
    # dollars have no bounded scale, negatives are real adjustments (see
    # module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Era 3's 667 legitimate rev_exp_per_pupil NULLs (missing/zero FTE
    # denominators) are far below the 20pp spike threshold (<=1.4%/year),
    # so no warning is expected.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(
        combined,
        required_non_null=[
            "year",
            "detail_level",
            "rev_exp_category",
            "rev_exp_subcategory",
        ],
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
    declaration order MUST match STANDARD_COLUMNS minus ``detail_level``.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "K-12 financial reporting for every Georgia public school, school "
            "district, and the state as a whole, published by the Governor's "
            "Office of Student Achievement (GOSA). Each row reports the total "
            "dollar amount and the per-FTE dollar amount for one cell of a "
            "two-bucket breakdown: K-12 Revenues across 6 revenue-source "
            "categories (federal, local, state QBE, state lottery, state "
            "other, other) and K-12 Expenditures across 11 "
            "expenditure-function categories (instruction, pupil services, "
            "instructional support, school administration, general "
            "administration, maintenance and operations, transportation, "
            "media, school food services, debt services, renovation and "
            "capital projects). Covers school years 2010-11 through 2023-24."
        ),
        title="District Revenues and Expenditures",
        summary=(
            "K-12 dollars taken in and spent by Georgia public schools and "
            "districts, broken out by revenue source and spending function, "
            "2011-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Ending (spring) calendar year of the school year (e.g. "
                    "2024 for 2023-24), parsed from the source's SCHOOL_YEAR / "
                    "LONG_SCHOOL_YEAR column and cross-checked against the "
                    "filename year."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "644",
                "description": (
                    "GOSA district code (FK to districts dimension): 3-digit "
                    "zero-padded county/city codes or 7-digit compound codes "
                    "for commission / state charter schools. Codes 850-888 "
                    "are RESA service agencies (typed 'resa' in the "
                    "dimension). NULL on state-level rows — the bronze "
                    "sentinel 'ALL' is mapped to NULL."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0189",
                "description": (
                    "4-digit zero-padded GOSA school code (composite FK to "
                    "schools dimension with district_code). NULL on district- "
                    "and state-level rows (bronze sentinel 'ALL' mapped to "
                    "NULL). The 2012 file publishes a minority of codes as "
                    "3-digit; they are zero-padded to match the other years. "
                    "2023-2024 'DOE OTHER' rows (GNETS programs, alternative "
                    "schools, Pre-K centers, central offices) carry real "
                    "institution numbers and appear under the school detail "
                    "level, matching where the pre-2023 files placed the same "
                    "entities."
                ),
            },
            {
                "name": "rev_exp_category",
                "type": "string",
                "nullable": False,
                "label": "Revenue / Expenditure Category",
                "example": "k12_expenditures",
                "validValues": sorted(REV_EXP_TYPE_MAP.values()),
                "short_description": (
                    "Whether the row is money coming in or going out: "
                    "k12_revenues or k12_expenditures. Filter with "
                    "rev_exp_subcategory since each bucket has its own "
                    "subcategory set."
                ),
                "description": (
                    "Top-level bucket — whether the row reports a revenue or "
                    "an expenditure: k12_revenues or k12_expenditures."
                ),
            },
            {
                "name": "rev_exp_subcategory",
                "type": "string",
                "nullable": False,
                "example": "instruction",
                "validValues": sorted(CATEGORY_MAP.values()),
                "short_description": (
                    "Revenue source (e.g. federal, local, state_qbe) or "
                    "spending function (e.g. instruction, transportation); "
                    "the valid set depends on rev_exp_category."
                ),
                "description": (
                    "Functional subcategory within the bucket (17 values). The "
                    "valid subset depends on rev_exp_category: revenue rows "
                    "carry only the 6 revenue-source subcategories (federal, "
                    "local, state_qbe, state_lottery, state_other, other); "
                    "expenditure rows carry only the 11 expenditure-function "
                    "subcategories. The two sets are disjoint (enforced by a "
                    "quality check), so filter on both columns together. The "
                    "bronze spelling 'School food Services' (lowercase food) "
                    "is an upstream-report typo normalized to "
                    "school_food_services."
                ),
            },
            {
                "name": "rev_exp_value",
                "type": "float64",
                "unit": "currency",
                "key_metric": True,
                "example": 3960000.00,
                "short_description": (
                    "Total dollars for this revenue source or spending "
                    "function at the row's level; negatives are real budget "
                    "adjustments."
                ),
                "description": (
                    "Total dollar amount for this (rev_exp_category, "
                    "rev_exp_subcategory) cell at the row's detail level. "
                    "Never NULL (enforced by "
                    "a quality check — the source publishes no suppression). "
                    "Negative values are legitimate budget adjustments / "
                    "corrections and are preserved; no range check applies."
                ),
            },
            {
                "name": "rev_exp_per_pupil",
                "type": "float64",
                "unit": "currency",
                "example": 6696.37,
                "null_meaning": (
                    "NULL = the entity has no FTE denominator (district "
                    "central offices, zero-FTE programs), NOT suppression. "
                    "All 667 NULLs fall in 2012-2014, the only years whose "
                    "bronze carried an FTE_COUNT column."
                ),
                "description": (
                    "Per-FTE (full-time-equivalent student) dollar amount for "
                    "the cell. Can be negative (budget adjustments). NULL "
                    "only in 2012-2014 where the bronze FTE denominator was "
                    "missing or zero (667 rows; enforced by a quality check). "
                    "Caution — not always a true per-pupil amount: in the "
                    "2024 file the source publishes rev_exp_per_pupil equal to "
                    "rev_exp_value verbatim on EVERY school-detail row "
                    "(15,678 of 15,678 nonzero rows, traditional schools "
                    "included), so 2024 school-level values carry no "
                    "per-pupil information at all; in 2023 the same artifact "
                    "covers all 9,798 DOE OTHER specialty-program rows plus "
                    "151 other school rows; in 2012 it covers the 10,414 "
                    "rows with a missing FTE_COUNT; and it frequently equals "
                    "rev_exp_value on aggregate / non-school rows in other "
                    "years. District- and state-detail rows in 2023-2024 do "
                    "carry true per-FTE values. Verify rev_exp_per_pupil <> "
                    "rev_exp_value (or sanity-check per-pupil magnitude) "
                    "before treating a school-level value as per-pupil "
                    "spending."
                ),
            },
        ],
        source="Governor's Office of Student Achievement (GOSA)",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        # No suppression anywhere in this source: zero non-numeric markers in
        # either monetary column across all 14 files (verified).
        suppressed_to_null=False,
        limitations=(
            "State rows have NULL district_code and school_code; district "
            "rows have NULL school_code. The school detail level includes "
            "non-traditional entities (central offices, GNETS programs, "
            "Pre-K centers, maintenance facilities) in every year, and "
            "district detail includes the 16 RESA service-agency rollups "
            "(district codes 850-888) — exclude both when analyzing "
            "traditional schools/districts only. rev_exp_per_pupil is not a "
            "true per-pupil amount everywhere: the 2024 file publishes it "
            "equal to rev_exp_value on every school-detail row (traditional "
            "schools included — 2024 school-level per-FTE values are totals, "
            "not per-pupil amounts), the 2023 file does so on all DOE OTHER "
            "rows, the 2012 file on its 10,414 missing-FTE rows, and it "
            "frequently equals rev_exp_value on aggregate / non-school rows "
            "in other years. State rows are published independently of "
            "district rows and do not always equal the sum of district "
            "values within a subcategory (e.g. the 2014 "
            "renovation_and_capital_projects state total runs several times "
            "the district sum) — treat each detail level as its own "
            "published series. The valid "
            "rev_exp_subcategory values are disjoint between the two "
            "rev_exp_category buckets (6 revenue-source vs 11 "
            "expenditure-function subcategories). No suppression exists in "
            "this topic — NULL never "
            "means suppressed; the only NULL metric values are 667 "
            "rev_exp_per_pupil rows in 2012-2014 with a missing/zero FTE "
            "denominator. Negative dollar values are legitimate budget "
            "adjustments and are preserved."
        ),
        notes=[
            (
                "Three detail levels in every year, exported as one file per "
                "detail level per year (schools.parquet, districts.parquet, "
                "states.parquet). Aggregate rows have NULL geography keys."
            ),
            (
                "No demographic column — the source has no demographic "
                "breakout; every row is a monetary aggregate at its "
                "geography level."
            ),
            (
                "2023-2024 files introduce an explicit 'DOE OTHER' detail "
                "level (9,798 rows/year) for specialty programs / centers. "
                "Rows with a real institution number (9,526/year) are routed "
                "to school detail (the pre-2023 files placed the same "
                "entities under school via the ALL-marker heuristic); the "
                "272 rows/year with INSTN_NUMBER='ALL' are the 16 RESA-style "
                "rollups x 17 categories, routed to district detail — the "
                "same convention as salaries_and_benefits."
            ),
            (
                "The 2012-2014 files carried a per-row FTE_COUNT column, "
                "dropped from gold (3 of 14 years only; rev_exp_per_pupil "
                "exists in every era). Verified before dropping: Dollars per "
                "FTE = REV_EXP_VALUE / FTE_COUNT within 0.005 wherever FTE "
                "is non-null and non-zero."
            ),
            (
                "rev_exp_per_pupil equals rev_exp_value verbatim wherever the "
                "source published an un-normalized per-FTE column: the "
                "entire school detail level of the 2024 file (all 25,872 "
                "rows — traditional schools included, so 2024 school-level "
                "per-FTE values are totals, not per-pupil amounts), all "
                "9,798 DOE OTHER rows of the 2023 file (plus 151 other "
                "nonzero 2023 school rows), and the 10,414 rows of the 2012 "
                "file with a missing FTE_COUNT. District- and state-detail "
                "rows in 2023-2024 carry true per-FTE values. Preserved as "
                "published."
            ),
            (
                "No suppression markers in any year; rev_exp_value is never "
                "NULL. Negative values in both metrics are legitimate budget "
                "adjustments (present in every year) and are preserved."
            ),
        ],
        quality_checks=[
            {
                "name": "rev_exp_category_subcategory_pairs_valid",
                "description": (
                    "Each (rev_exp_category, rev_exp_subcategory) pair stays "
                    "within its bucket's allowed set: revenue rows carry only "
                    "the 6 revenue-source subcategories and expenditure rows "
                    "only the 11 expenditure-function subcategories. The two "
                    "sets are disjoint and identical in every year (verified "
                    "across all 14 bronze files)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(rev_exp_category = 'k12_revenues' AND rev_exp_subcategory "
                    "NOT IN ("
                    + ", ".join(f"'{c}'" for c in REVENUE_CATEGORIES)
                    + ")) OR (rev_exp_category = 'k12_expenditures' AND "
                    "rev_exp_subcategory NOT IN ("
                    + ", ".join(f"'{c}'" for c in EXPENDITURE_CATEGORIES)
                    + "))"
                ),
                "mustBe": 0,
            },
            {
                "name": "rev_exp_value_never_null",
                "description": (
                    "The source publishes no suppression and no missing "
                    "dollar amounts: rev_exp_value is populated on every row "
                    "of all 14 bronze files (verified). A NULL means a "
                    "parsing regression or a new suppression regime — either "
                    "must be analyzed, not silently passed."
                ),
                "dimension": "completeness",
                "query": "SELECT COUNT(*) FROM {object} WHERE rev_exp_value IS NULL",
                "mustBe": 0,
            },
            {
                "name": "rev_exp_per_pupil_null_only_in_2012_2014",
                "description": (
                    "rev_exp_per_pupil NULLs are confined to 2012-2014 — the "
                    "only years whose bronze carried an FTE_COUNT column "
                    "(667 rows with a missing/zero FTE denominator: 13 in "
                    "2012, 382 in 2013, 272 in 2014). Every other year is "
                    "fully populated (verified). A NULL elsewhere means a "
                    "parsing regression or a source change."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE rev_exp_per_pupil IS "
                    "NULL AND year NOT IN (2012, 2013, 2014)"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_rows_complete_every_year",
                "description": (
                    "Every year publishes exactly 17 state rows — one per "
                    "(rev_exp_category, rev_exp_subcategory) pair, covering "
                    "all 17 pairs (verified across all 14 bronze files). "
                    "State rows self-scope via NULL geography keys."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year FROM {object} "
                    "WHERE district_code IS NULL AND school_code IS NULL "
                    "GROUP BY year HAVING COUNT(*) <> 17 OR "
                    "COUNT(DISTINCT rev_exp_category || '|' || "
                    "rev_exp_subcategory) <> 17"
                    ") AS bad_years"
                ),
                "mustBe": 0,
            },
            {
                "name": "district_entities_carry_all_17_pairs",
                "description": (
                    "Every district-detail entity (districts, RESA rollups, "
                    "charters) carries exactly 17 rows covering all 17 "
                    "(rev_exp_category, rev_exp_subcategory) pairs in every "
                    "year it appears (verified across all 14 bronze files). "
                    "School-detail entities do NOT share this property (some "
                    "publish partial subcategory sets), so the check scopes "
                    "to district rows via geography NULL-ness."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year, district_code "
                    "FROM {object} WHERE district_code IS NOT NULL AND "
                    "school_code IS NULL GROUP BY year, district_code "
                    "HAVING COUNT(*) <> 17 OR "
                    "COUNT(DISTINCT rev_exp_category || '|' || "
                    "rev_exp_subcategory) <> 17"
                    ") AS bad_entities"
                ),
                "mustBe": 0,
            },
        ],
        # rev_exp_subcategory is only meaningful within a chosen rev_exp_category
        # (the two buckets' subcategory sets are disjoint), so the two filter
        # together — surfaced to API/MCP consumers as a filter_hint.
        dependent_filters=[
            {
                "primary": "rev_exp_category",
                "dependent": "rev_exp_subcategory",
                "note": (
                    "Filter rev_exp_subcategory together with rev_exp_category — "
                    "the valid subcategory set depends on the chosen bucket "
                    "(6 revenue-source vs 11 expenditure-function values)."
                ),
            }
        ],
    )


if __name__ == "__main__":
    main()
