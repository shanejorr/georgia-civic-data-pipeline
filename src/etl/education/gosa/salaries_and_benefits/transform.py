"""Transform bronze salaries_and_benefits files into gold fact tables.

Source: Governor's Office of Student Achievement (GOSA) — Salaries and
Benefits, 2011-2024 (14 bronze files, one school year each). For every
Georgia district (plus RESA service-agency aggregates and the official state
rollup) reports salary and benefit dollars for three staff categories
(``staff_category``) and those salary+benefit totals as a share of four
district revenue/expenditure bases.

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **District-only topic; ``school_code`` always NULL.** Bronze publishes only
  district and state rows (``INSTN_NUMBER`` is the constant ``ALL``
  sentinel). Per ``src/etl/education/CLAUDE.md`` the fact table still emits
  ``school_code`` — always NULL — so every education fact shares the same
  key-column shape. Pinned by the ``school_code_always_null`` quality check.
- **Two near-identical eras, one pipeline.** Era 1 (2011-2022, 13 cols) uses
  ``% Rev-``/``% Exp-`` percent headers and flags state rows only via the
  ``SCHOOL_DSTRCT_CD='ALL'`` sentinel. Era 2 (2023-2024, 16 cols) renames the
  four percent columns to ``REV__``/``EXP_`` identifiers and adds
  ``#RPT_NAME`` / ``DETAIL_LVL_DESC`` / ``GRADES_SERVED_DESC``. The pct
  rename map is era-routed; everything else is shared.
- **RESA rows kept at district detail (cross-topic convention).** Both eras
  carry 48 rows/year for the 16 Regional Education Service Agencies
  (district codes 850-888): Era 1 as bare codes indistinguishable from
  districts, Era 2 flagged ``DETAIL_LVL_DESC='DOE OTHER'``. Verified: Era 2's
  DOE OTHER rows are exactly the 850-888 code set, and no RESA code ever
  appears under the District label. They are routed to
  ``detail_level='district'`` in both eras — same convention as
  revenues_and_expenditures — keeping their natural codes queryable (the
  districts dimension types them ``resa``). Pinned by the
  ``resa_rows_present_every_year`` quality check (16 distinct codes/year).
- **All-string bronze read.** Files are read with ``infer_schema_length=0``
  so the ``ALL`` sentinels and district codes are never schema-inference
  casualties. Era 1 dollar columns mix plain floats with quoted
  plain unquoted floats; a defensive comma-strip guards hypothetical
  comma-grouped exports (none exist in the current bronze).
- **No suppression anywhere.** Unlike most GOSA topics, all 7 metric columns
  are fully populated in every file (verified: zero NULLs, no TFS/``*``
  markers). ``suppressed_to_null=False`` is passed to the contract emitter
  and the ``metrics_never_null`` quality check pins the fact so a future
  suppression regime surfaces loudly.
- **Negative dollars are real data, preserved.** Refunds/restatements
  produce rare small negatives: BENEFITS in 2011, 2012, 2022 (1 row each,
  min -191,629.60) and SALARIES in 2024 (1 row, -2,000.00). They are within
  the metrics' defined domain (signed dollars), so they are preserved per
  §4b's extreme-but-conceivable rule and ``unit: currency`` derives no range
  check. No §4b masks exist in this topic.
- **The four pct_* columns are decimal ratios, not bounded proportions.**
  The 0-100 source scale is divided by 100 (§4), but the numerator
  (salaries+benefits) can legitimately exceed the chosen revenue/expenditure
  base: the 2021 file (school year 2020-21, the COVID year) publishes 144
  rows above 100 — mostly Teachers and Paraprofessionals, including the
  state rollup itself (% Exp- GF/Title/Lottery 107.98) — with a maximum of
  127.31 (→ 1.2731 after /100). The 2021 file runs ~2x adjacent years
  across ALL metrics including dollars (state Teachers S&B: 10.53B in 2020,
  20.98B in 2021, 10.89B in 2022; 94% of districts at ~2x their 2020/2022
  average) — consistent with a two-year-cumulative source publication, not
  a typo; preserved, so all four columns carry ``unit: ratio`` (auto check
  ``>= 0`` only; bronze minimum is 0.0 in every year).
- **Component reconciliation.** ``SALARIES + BENEFITS =
  SALARIES_AND_BENEFITS`` within $1 in every row of all 14 files (verified:
  zero violations). Pinned by the
  ``salaries_and_benefits_reconciles_with_components`` quality check.
- **Every entity carries exactly 3 staff_category rows.** Verified in all 14
  files: each district/RESA/state entity appears exactly once per category
  (General Administration, School Administration, Teachers and
  Paraprofessionals). Pinned by ``staff_category_complete_per_entity``.
- **Dedup tie-break.** Each bronze file covers exactly one school year
  (cross-checked LONG_SCHOOL_YEAR vs filename) and years never overlap; the
  per-file grain (district x category) is unique in every file (verified:
  zero duplicate key groups). No duplicates are expected;
  ``sort_col="salaries_and_benefits"`` remains as the documented
  safety net — prefer the row with the larger reported total over a
  null/zero placeholder.
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

TOPIC = "salaries_and_benefits"
BRONZE_DIR = Path("data/bronze/education/gosa/salaries_and_benefits")
GOLD_DIR = Path("data/gold/education/salaries_and_benefits")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Aggregate-row sentinel in SCHOOL_DSTRCT_CD (state rows). Becomes NULL in
# gold, never a key value. INSTN_NUMBER is constantly 'ALL' (no school rows).
GEOGRAPHY_SENTINEL = "ALL"

# The three staff categories — identical labels in every file 2011-2024.
STAFF_CATEGORY_MAP: dict[str, str] = {
    "General Administration": "general_administration",
    "School Administration": "school_administration",
    "Teachers and Paraprofessionals": "teachers_and_paraprofessionals",
}

# Era 2 explicit detail levels. DOE OTHER marks the 16 RESA aggregate rows
# (codes 850-888), routed to district detail per the cross-topic convention
# (see module docstring) — their natural codes stay queryable and the
# districts dimension types them 'resa'.
DETAIL_LEVEL_MAP: dict[str, str] = {
    "State": "state",
    "District": "district",
    "DOE OTHER": "district",
}

# Era-routed renames for the four percent columns (the main schema change
# between eras). Both map onto one set of gold ratio columns.
PCT_RENAMES_ERA1: dict[str, str] = {
    "% Rev- GF/Title/Lottery": "pct_revenue_gf_title_lottery",
    "% Rev- Total K-12": "pct_revenue_total_k12",
    "% Exp- GF/Title/Lottery": "pct_expense_gf_title_lottery",
    "% Exp-Total K-12": "pct_expense_total_k12",
}
PCT_RENAMES_ERA2: dict[str, str] = {
    "REV__GF/TITLE/LOTTERY": "pct_revenue_gf_title_lottery",
    "REV__TOTAL_K_12": "pct_revenue_total_k12",
    "EXP__GF/TITLE/LOTTERY": "pct_expense_gf_title_lottery",
    "EXP_TOTAL_K_12": "pct_expense_total_k12",
}

# Dollar columns share names across eras.
DOLLAR_RENAMES: dict[str, str] = {
    "SALARIES": "salaries",
    "BENEFITS": "benefits",
    "SALARIES_AND_BENEFITS": "salaries_and_benefits",
}

# Era-detection signatures, most-specific first (Era 2 adds #RPT_NAME /
# DETAIL_LVL_DESC and renames the percent columns; Era 1 is detected by its
# own distinctive percent header).
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_2": ["#RPT_NAME", "DETAIL_LVL_DESC", "REV__TOTAL_K_12"],
    "era_1": ["LONG_SCHOOL_YEAR", "% Rev- Total K-12"],
}

# Bronze columns every file must carry regardless of era (rename-coverage
# guard). The era-specific percent headers are checked separately in
# transform_file — an unmatched source column silently becomes NULL in gold,
# the most common data-loss bug.
REQUIRED_BRONZE_COLUMNS: list[str] = [
    "LONG_SCHOOL_YEAR",
    "SCHOOL_DSTRCT_CD",
    "CATEGORY",
    "SALARIES",
    "BENEFITS",
    "SALARIES_AND_BENEFITS",
]

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "staff_category",
    "salaries",
    "benefits",
    "salaries_and_benefits",
    "pct_revenue_gf_title_lottery",
    "pct_revenue_total_k12",
    "pct_expense_gf_title_lottery",
    "pct_expense_total_k12",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "staff_category": pl.Utf8,
    "salaries": pl.Float64,
    "benefits": pl.Float64,
    "salaries_and_benefits": pl.Float64,
    "pct_revenue_gf_title_lottery": pl.Float64,
    "pct_revenue_total_k12": pl.Float64,
    "pct_expense_gf_title_lottery": pl.Float64,
    "pct_expense_total_k12": pl.Float64,
    "detail_level": pl.Utf8,
}

DOLLAR_COLUMNS: list[str] = list(DOLLAR_RENAMES.values())
PCT_COLUMNS: list[str] = list(PCT_RENAMES_ERA1.values())
METRIC_COLUMNS: list[str] = DOLLAR_COLUMNS + PCT_COLUMNS

NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "staff_category",
    "detail_level",
]


# =============================================================================
# Casting helpers
# =============================================================================


def _to_float_expr(col: str) -> pl.Expr:
    """Cast an all-string bronze metric column to Float64.

    Dollar columns are plain floats in all current bronze; the comma-strip
    is a defensive guard only. ``strict=False`` nulls any
    other non-numeric residue instead of failing the cast (none observed —
    this topic has no suppression markers).
    """
    return (
        pl.col(col)
        .str.strip_chars()
        .str.replace_all(",", "")
        .cast(pl.Float64, strict=False)
    )


def _require_columns(df: pl.DataFrame, required: list[str], label: str) -> None:
    """Raise if any expected bronze column is absent (rename-coverage guard)."""
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"{label}: expected bronze column(s) missing: {missing}. "
            f"Present: {df.columns}"
        )


# =============================================================================
# Per-file transform (eras share one shape; pct renames + detail level differ)
# =============================================================================


def _validate_era2_constants(df: pl.DataFrame, year: int) -> None:
    """Hard-stop if Era 2's constant #RPT_NAME column carries unexpected values.

    Anything other than "Salary_and_Benefits" means rows from another GOSA
    report are mixed into this topic's bronze and must be analyzed, not
    silently kept.
    """
    rpt_names = df["#RPT_NAME"].drop_nulls().unique().to_list()
    if rpt_names != ["Salary_and_Benefits"]:
        raise ValueError(f"era_2 {year}: unexpected #RPT_NAME values {rpt_names}")


def _detail_level_era1(df: pl.DataFrame) -> pl.DataFrame:
    """Derive Era 1's implicit detail level from the district-code sentinel.

    Era 1 has no detail-level column: SCHOOL_DSTRCT_CD='ALL' marks the state
    rollup; every other row — including the 16 RESA aggregates (bare 8xx
    codes) — is district detail, matching Era 2's explicit District/DOE OTHER
    routing.
    """
    return df.with_columns(
        pl.when(pl.col("SCHOOL_DSTRCT_CD").str.strip_chars() == GEOGRAPHY_SENTINEL)
        .then(pl.lit("state"))
        .otherwise(pl.lit("district"))
        .alias("detail_level")
    )


def _detail_level_era2(df: pl.DataFrame, manifest: TransformManifest) -> pl.DataFrame:
    """Map Era 2's explicit DETAIL_LVL_DESC to canonical detail levels.

    DOE OTHER (the 16 RESA aggregates) routes to district detail per the
    cross-topic convention (see module docstring). Unmapped values become
    NULL and surface via the manifest's unmapped guard.
    """
    df = df.with_columns(
        pl.col("DETAIL_LVL_DESC")
        .str.strip_chars()
        .replace_strict(DETAIL_LEVEL_MAP, default=None)
        .alias("detail_level")
    )
    manifest.record_categorical(
        column="detail_level",
        map_dict=DETAIL_LEVEL_MAP,
        bronze_series=df["DETAIL_LVL_DESC"],
        gold_series=df["detail_level"],
    )
    return df


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame:
    """Read one bronze file, detect its era, and transform it to gold shape.

    Year resolution: every file carries exactly one LONG_SCHOOL_YEAR value
    whose ending year must agree with the filename year, so a misnamed file
    cannot silently mislabel a whole year.

    Args:
        path: Bronze file path.
        manifest: Manifest for read-loss / file / bronze-count / categorical
            recording.

    Returns:
        Gold-shaped DataFrame with STANDARD_COLUMNS.
    """
    # All-string read: district codes and the ALL sentinels are never
    # schema-inference casualties; the comma-strip is defensive only
    # survive intact for explicit cleaning in _to_float_expr.
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
    pct_renames = PCT_RENAMES_ERA2 if era == "era_2" else PCT_RENAMES_ERA1
    _require_columns(
        df, REQUIRED_BRONZE_COLUMNS + list(pct_renames.keys()), f"{era} {path.name}"
    )
    if era == "era_2":
        _validate_era2_constants(df, filename_year)

    # Exactly one LONG_SCHOOL_YEAR value per file; its ending year must agree
    # with the filename year.
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

    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)
    logger.info("Processing %s as %s (year %d)", path.name, era, year)

    # Detail level: Era 1 derives it from the ALL sentinel; Era 2 maps the
    # explicit DETAIL_LVL_DESC (DOE OTHER -> district, see module docstring).
    if era == "era_2":
        df = _detail_level_era2(df, manifest)
    else:
        df = _detail_level_era1(df)

    # Staff category: identical three labels in every file 2011-2024.
    df = df.with_columns(
        pl.col("CATEGORY")
        .str.strip_chars()
        .replace_strict(STAFF_CATEGORY_MAP, default=None)
        .alias("staff_category")
    )
    manifest.record_categorical(
        column="staff_category",
        map_dict=STAFF_CATEGORY_MAP,
        bronze_series=df["CATEGORY"],
        gold_series=df["staff_category"],
    )

    # Geography keys: the ALL sentinel -> NULL (never carried into gold);
    # zfill(3) pads 3-digit county/RESA codes and passes 7-digit charter
    # codes through unchanged (never truncate). school_code is always NULL —
    # district-only topic, column kept for the shared education key shape.
    # Metrics: dollars stay on their natural signed-dollar scale (negatives
    # are real refunds/restatements); the 0-100 source percentages are
    # divided by 100 onto the 0-1 ratio scale (§4/§4a).
    district_clean = pl.col("SCHOOL_DSTRCT_CD").str.strip_chars()
    df = df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.when(district_clean == GEOGRAPHY_SENTINEL)
        .then(None)
        .otherwise(district_clean.str.zfill(3))
        .alias("district_code"),
        pl.lit(None).cast(pl.Utf8).alias("school_code"),
        *[_to_float_expr(src).alias(dst) for src, dst in DOLLAR_RENAMES.items()],
        *[(_to_float_expr(src) / 100.0).alias(dst) for src, dst in pct_renames.items()],
    )

    return df.select(STANDARD_COLUMNS)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for salaries_and_benefits."""
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
    # mean an alias/era-routing bug and must raise, not be deduped away.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: each bronze file is a distinct school year with no overlap,
    # and the per-file grain (district x category) is unique in all 14 files
    # (verified: zero duplicate key groups), so no duplicates are expected;
    # prefer the row with the larger reported salaries_and_benefits total
    # over a null/zero placeholder as the safety net.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code", "staff_category"],
        district_keys=["year", "district_code", "staff_category"],
        state_keys=["year", "staff_category"],
        sort_col="salaries_and_benefits",
    )

    # 4. Geography nulling (shared domain rules). No §4b masks: the full
    # bronze scan found no impossible values — negative dollars are real
    # refunds/restatements and the >1.0 2021 ratios are a systematic
    # 2021 ~2x source anomaly (see module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. This topic has no suppression — every metric is
    # fully populated in every year, so no NULL-rate spike is expected.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(
        combined, required_non_null=["year", "detail_level", "staff_category"]
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
            "Salary and benefit expenditures for Georgia public school "
            "districts (with RESA service-agency aggregates and the official "
            "state rollup) by staff category — teachers and "
            "paraprofessionals, school administration, and general "
            "administration — plus those salary+benefit totals as a share of "
            "four district revenue and expenditure bases. Published by GOSA "
            "for school years 2010-11 through 2023-24."
        ),
        title="District Salaries and Benefits",
        summary=(
            "What Georgia school districts spend on salaries and benefits by "
            "staff category, with that spending as a share of district "
            "revenue and expenditures, 2011-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Ending (spring) calendar year of the school year (e.g. "
                    "2024 for 2023-24), parsed from the source's "
                    "LONG_SCHOOL_YEAR and cross-checked against the filename."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "GOSA district code (FK to districts dimension): 3-digit "
                    "zero-padded county/city codes or 7-digit state-charter "
                    "codes. Codes 850-888 are the 16 Regional Education "
                    "Service Agencies (RESAs) — service-agency aggregates "
                    "kept at district detail (the dimension types them "
                    "'resa'); exclude them when analyzing traditional LEAs. "
                    "NULL on state-level rows."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "null_meaning": (
                    "Always NULL — this topic publishes no school-level "
                    "rows; the column exists so every education fact table "
                    "shares the same key shape."
                ),
                "description": (
                    "GOSA school code (composite FK to schools dimension "
                    "with district_code). Always NULL in this district-only "
                    "topic — the source reports no school-level detail "
                    "(enforced by a quality check)."
                ),
            },
            {
                "name": "staff_category",
                "type": "string",
                "nullable": False,
                "example": "teachers_and_paraprofessionals",
                "validValues": sorted(STAFF_CATEGORY_MAP.values()),
                "short_description": (
                    "Which staff the dollars cover: "
                    "teachers_and_paraprofessionals, school_administration, "
                    "or general_administration (one row per category)."
                ),
                "description": (
                    "Staff category the row's salary and benefit dollars "
                    "cover: teachers_and_paraprofessionals, "
                    "school_administration (principals and school-level "
                    "administrators), or general_administration "
                    "(district-office administration). Every entity carries "
                    "exactly one row per category per year."
                ),
            },
            {
                "name": "salaries",
                "type": "float64",
                "unit": "currency",
                "example": 6204400.0,
                "description": (
                    "Total salary dollars paid for the staff category. "
                    "Rare small negatives are real refunds/restatements "
                    "published by the source and preserved (one 2024 row at "
                    "-2,000.00); no range check applies."
                ),
            },
            {
                "name": "benefits",
                "type": "float64",
                "unit": "currency",
                "example": 3059444.0,
                "description": (
                    "Total benefit dollars paid for the staff category. "
                    "Rare small negatives are real refunds/restatements "
                    "published by the source and preserved (one row each in "
                    "2011, 2012, and 2022; minimum -191,629.60); no range "
                    "check applies."
                ),
            },
            {
                "name": "salaries_and_benefits",
                "type": "float64",
                "unit": "currency",
                "key_metric": True,
                "example": 9263900.0,
                "short_description": (
                    "Total salary plus benefit dollars the district spent on "
                    "this staff category in the year."
                ),
                "description": (
                    "Total salary plus benefit dollars for the staff "
                    "category. Equals salaries + benefits "
                    "within $1 in every row (source-published total; "
                    "enforced by a quality check)."
                ),
            },
            {
                "name": "pct_revenue_gf_title_lottery",
                "type": "float64",
                "unit": "ratio",
                "example": 0.4183,
                "description": (
                    "Salaries+benefits for the category as a share of "
                    "district revenue from General Fund / Title / Lottery "
                    "sources (0-1 decimal scale; source publishes 0-100 and "
                    "is divided by 100). A ratio, not a bounded proportion: "
                    "the 2021 file (school year 2020-21, the COVID year) "
                    "systematically publishes values above 1.0 — including "
                    "the state rollup — with a maximum of 1.2346, because "
                    "category spending exceeded the GF/Title/Lottery revenue "
                    "base that year; preserved as published."
                ),
            },
            {
                "name": "pct_revenue_total_k12",
                "type": "float64",
                "unit": "ratio",
                "example": 0.3727,
                "description": (
                    "Salaries+benefits for the category as a share of total "
                    "district K-12 revenue (0-1 decimal scale; source "
                    "publishes 0-100 and is divided by 100). A ratio, not a "
                    "bounded proportion: the 2021 file publishes values up "
                    "to 1.0413 (2021 values run ~2x adjacent "
                    "years across all metrics; likely a two-year-cumulative "
                    "publication); preserved as "
                    "published."
                ),
            },
            {
                "name": "pct_expense_gf_title_lottery",
                "type": "float64",
                "unit": "ratio",
                "example": 0.4558,
                "description": (
                    "Salaries+benefits for the category as a share of "
                    "district expenditures from General Fund / Title / "
                    "Lottery funds (0-1 decimal scale; source publishes "
                    "0-100 and is divided by 100). A ratio, not a bounded "
                    "proportion: the 2021 file systematically publishes "
                    "values above 1.0 — the state Teachers and "
                    "Paraprofessionals rollup is 1.0798 and the maximum is "
                    "1.2731 (2021 values run ~2x adjacent "
                    "years across all metrics; likely a two-year-cumulative "
                    "publication); preserved as "
                    "published."
                ),
            },
            {
                "name": "pct_expense_total_k12",
                "type": "float64",
                "unit": "ratio",
                "example": 0.4058,
                "description": (
                    "Salaries+benefits for the category as a share of total "
                    "district K-12 expenditures (0-1 decimal scale; source "
                    "publishes 0-100 and is divided by 100). A ratio, not a "
                    "bounded proportion: the 2021 file publishes values up "
                    "to 1.2103 (2021 values run ~2x adjacent "
                    "years across all metrics; likely a two-year-cumulative "
                    "publication); preserved as "
                    "published."
                ),
            },
        ],
        source="GOSA",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        # This topic has no suppression — every metric is published for every
        # row in every year (pinned by the metrics_never_null quality check).
        suppressed_to_null=False,
        # Derived prose plus the RESA-in-district-detail caveat and the 2021
        # ratio caveat contract consumers need.
        limitations=(
            "State rows have NULL district_code. school_code is always NULL "
            "— this is a district-only topic (no school-level detail "
            "exists at the source). District-detail rows include the 16 "
            "Regional Education Service Agencies (district codes 850-888), "
            "which are service-agency aggregates rather than school "
            "districts — exclude district_code between '850' and '888' when "
            "analyzing traditional LEAs, and do not sum district rows to "
            "reproduce the state rollup without accounting for them. The "
            "four pct_* columns are decimal ratios that legitimately exceed "
            "1.0 in 2021 (school year 2020-21): category spending exceeded "
            "the chosen bases that year, up to 1.2731 — the 2021 file runs ~2x "
            "adjacent years across all metrics (dollars included), consistent "
            "with a two-year-cumulative publication. "
            "No suppression exists in this topic — NULL never means "
            "suppressed."
        ),
        notes=[
            (
                "Era rename: 2011-2022 files use '% Rev- GF/Title/Lottery'-"
                "style percent headers; 2023-2024 files rename them to "
                "REV__/EXP_-style identifiers and add explicit detail-level "
                "flags. Both eras map onto the same four pct_* gold columns."
            ),
            (
                "RESA rows (district codes 850-888, 16 agencies x 3 "
                "categories = 48 rows/year) appear in every year of both "
                "eras: 2011-2022 as bare codes indistinguishable from "
                "districts, 2023-2024 flagged DETAIL_LVL_DESC='DOE OTHER'. "
                "Both are kept at district detail — the same convention as "
                "revenues_and_expenditures — and the districts dimension "
                "types them 'resa'."
            ),
            (
                "No suppression: all seven metric columns are fully "
                "populated in every row of all 14 files (no TFS/*/blank "
                "markers). Pinned by the metrics_never_null quality check so "
                "a future suppression regime surfaces loudly."
            ),
            (
                "Negative dollar values are real data, preserved: "
                "refunds/restatements produce one negative benefits "
                "row each in 2011, 2012, and 2022 (minimum -191,629.60) and "
                "one negative salaries row in 2024 (-2,000.00)."
            ),
            (
                "The 2021 file (school year 2020-21, the COVID year) "
                "publishes 144 rows with pct_* values above 100 on the "
                "source scale — mostly Teachers and Paraprofessionals, "
                "including the state rollup — with a maximum of 127.31 "
                "(1.2731 after /100). Systematic pandemic-year base effect, "
                "not typos; preserved, and the four pct_* columns carry "
                "unit: ratio rather than proportion."
            ),
            (
                "salaries_and_benefits equals salaries + "
                "benefits within $1 in every row of all 14 files "
                "(source-published total; enforced by a quality check)."
            ),
            (
                "Constant bronze columns are dropped: #RPT_NAME (Era 2), "
                "INSTN_NUMBER ('ALL'), INSTN_NAME ('All Column Values'). "
                "GRADES_SERVED_DESC (Era 2 only, near-constant, NULL for "
                "RESAs) is institution metadata, not a fact; district names "
                "live in the districts dimension."
            ),
        ],
        quality_checks=[
            {
                "name": "salaries_and_benefits_reconciles_with_components",
                "description": (
                    "The published total must equal the sum of its published "
                    "components: salaries_and_benefits = "
                    "salaries + benefits within $1 "
                    "(verified: zero violations across all 14 bronze files)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "salaries IS NOT NULL "
                    "AND benefits IS NOT NULL "
                    "AND salaries_and_benefits IS NOT NULL "
                    "AND ABS(salaries + benefits - "
                    "salaries_and_benefits) > 1.0"
                ),
                "mustBe": 0,
            },
            {
                "name": "school_code_always_null",
                "description": (
                    "Structural fact: this is a district-only topic — the "
                    "source publishes no school-level rows, so school_code "
                    "(kept for the shared education key shape) must be NULL "
                    "on every row."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE school_code IS NOT NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "metrics_never_null",
                "description": (
                    "This topic has no suppression: all seven metric columns "
                    "are fully populated in every row of every year "
                    "(verified across all 14 bronze files). A NULL means a "
                    "parsing regression or a new suppression regime — "
                    "either must be analyzed, not silently passed."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "salaries IS NULL OR benefits IS NULL "
                    "OR salaries_and_benefits IS NULL "
                    "OR pct_revenue_gf_title_lottery IS NULL "
                    "OR pct_revenue_total_k12 IS NULL "
                    "OR pct_expense_gf_title_lottery IS NULL "
                    "OR pct_expense_total_k12 IS NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "staff_category_complete_per_entity",
                "description": (
                    "Every entity (each district/RESA, and the state rollup "
                    "as the NULL-district group) carries exactly one row per "
                    "staff category per year — three rows in total "
                    "(verified across all 14 bronze files)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year, "
                    "COALESCE(district_code, '__state__') AS entity "
                    "FROM {object} GROUP BY year, "
                    "COALESCE(district_code, '__state__') "
                    "HAVING COUNT(*) <> 3 "
                    "OR COUNT(DISTINCT staff_category) <> 3) AS bad_entities"
                ),
                "mustBe": 0,
            },
            {
                "name": "resa_rows_present_every_year",
                "description": (
                    "Both eras publish the 16 RESA service-agency aggregates "
                    "(district codes 850-888) at district detail in every "
                    "year (Era 1 as bare codes, Era 2 as DOE OTHER rows). A "
                    "different count means RESA rows were dropped or a new "
                    "aggregate entity appeared — either must be analyzed."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year FROM {object} "
                    "WHERE district_code IS NOT NULL "
                    "AND LENGTH(district_code) = 3 "
                    "AND district_code BETWEEN '850' AND '888' "
                    "GROUP BY year "
                    "HAVING COUNT(DISTINCT district_code) <> 16) AS bad_years"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_rows_present_every_year",
                "description": (
                    "Every year publishes the statewide rollup: exactly 3 "
                    "state rows (one per staff_category) with NULL "
                    "district_code. staff_category_complete_per_entity "
                    "cannot catch a wholly missing state group."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year FROM {object} "
                    "WHERE district_code IS NULL GROUP BY year "
                    "HAVING COUNT(*) <> 3) AS bad_years"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
