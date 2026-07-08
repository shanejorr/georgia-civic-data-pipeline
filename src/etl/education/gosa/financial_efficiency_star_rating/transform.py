"""Transform bronze financial_efficiency_star_rating files into multi-level gold.

Source: Governor's Office of Student Achievement (GOSA) — Financial Efficiency
Star Rating (FESR). For Georgia public school districts and schools the source
publishes per-pupil expenditure (PPE) inputs, a CCRPI-derived annual Single
Score, rolling 3-year averages + a PPE percentile (district rating files only),
and an FESR star rating in 0.5 increments.

**This topic merges two formerly separate GOSA download families** —
``financial_efficiency_star_rating_fesr_district`` (one row per district; 180
traditional Georgia systems, codes 601-793; 2016-2024) and
``financial_efficiency_star_rating_fesr_school`` (one row per school; 2017-2024)
— into a single star-schema fact table with two detail levels
(``districts`` / ``schools``). The two families are distinct downloads that
share the per-pupil-expenditure metric vocabulary but diverge structurally; a
single transform body handles both behind a per-family dispatch keyed on the
``_fesr_district_`` / ``_fesr_school_`` infix in each filename (mirrors the
``direct_certification`` consolidation template).

Detail levels in the merged fact table (``detail_level`` is implicit in the
parquet filename per ``src/etl/education/CLAUDE.md`` and is dropped on export):

- ``district`` — ``district_code`` populated, ``school_code`` NULL (district
  family rows).
- ``school``   — both geography keys populated (school family rows).

Because ``detail_level`` is not a stored column, the merged quality checks
discriminate detail by the geography-key NULL pattern in the unioned table
(school ⟺ ``school_code IS NOT NULL``; district ⟺ ``school_code IS NULL``).

Schema union (the central merge decision):

- **Shared columns** (same name in BOTH families, verified-identical derivation,
  populated for both levels): ``year``, ``district_code``, ``school_code``,
  ``total_expenditures``, ``fte_enrollment``, ``per_pupil_expenditure``,
  ``federal_per_pupil_expenditure``, ``state_local_per_pupil_expenditure``,
  ``ccrpi_single_score``, ``fesr_star_rating``, ``is_non_compliant``. Verified
  in gold (FY2018): ``per_pupil_expenditure = total_expenditures /
  fte_enrollment`` holds to $0.005 in BOTH families, and the federal/state-local
  per-pupil split reconciles in both — so these are genuinely the same quantity.
- **District-only** (NULL on school rows): ``federal_expenditures``,
  ``state_local_expenditures`` (the federal/SL split of the district's
  ``total_expenditures``), ``ccrpi_three_year_avg``, and the two rolling
  metrics renamed per C-1: ``per_pupil_expenditure_three_year_avg`` (was
  ``ppe_three_year_avg``) and ``per_pupil_expenditure_percentile`` (was
  ``ppe_percentile``).
- **School-only** (NULL on district rows): ``included_expenditures``,
  ``included_federal_expenditures``, ``included_state_local_expenditures``,
  ``excluded_expenditures``, ``total_federal_expenditures``,
  ``total_state_local_expenditures``, ``pct_of_district_enrollment``.

**Federal / state-local split — kept SEPARATE, not unified.** The district's
``federal_expenditures``/``state_local_expenditures`` and the school's
``total_federal_expenditures``/``total_state_local_expenditures`` are the SAME
semantic quantity: each is the federal (resp. state+local) share of the shared
``total_expenditures`` column (the district reconciles
``federal + state_local = total_expenditures`` to ~$0; the school reconciles
``total_federal + total_state_local = total_expenditures`` to ~$0; both split
the same ``total_expenditures``). They are nevertheless KEPT AS DISTINCT
COLUMNS because (a) the two source downloads name them differently and the merge
rule keeps differently-named columns separate unless unification is both
verified-identical AND lossless; (b) the school family additionally publishes a
**different** federal/SL split — the ``included_*`` columns, which divide the
PRE-allocation ``included_expenditures`` (verified: ``included / fte`` does NOT
equal PPE, gap ~$8,493, whereas ``total / fte`` does) — so a school row has TWO
federal splits while a district row has ONE; collapsing the district's single
split into the school's ``total_*`` columns would silently assert the district
has no ``included_*`` analog (it does not) and would mix two download
provenances under one name. Keeping them separate preserves both meanings
without fabrication; the equivalence is stated in each column's description.

Per-family value handling is carried verbatim from the two source transforms —
the merge changes routing, column population, and the contract, never the
per-file value logic:

District family (Pattern A-E, 2016-2024):
  - Tidy-long reshape of each wide rolling-window workbook to one row per
    (district, fiscal year), FY2014-FY2024.
  - Rolling/rating metrics (per_pupil_expenditure_three_year_avg,
    ccrpi_three_year_avg, per_pupil_expenditure_percentile, fesr_star_rating,
    is_non_compliant) attach only to the report-year row (FY2016-FY2019, FY2024).
  - Fiscal-year overlaps resolved by a column-wise merge: non-financial columns
    take report-year-then-newest first-non-null; the financial block is taken
    atomically from a row with a complete federal+state-local breakdown so
    ``federal + state_local = total`` stays additive in every gold row.
  - The 2018 ``FESR='Non-Compliant'`` sentinel (Talbot 730) → NULL rating +
    is_non_compliant=True.

School family (era_2017-era_2024, 2017-2024):
  - Tidy-long reshape to one row per (district, school, fiscal year),
    FY2017-FY2024.
  - fesr_star_rating attaches only to each publishing report's newest fiscal
    year (FY17/FY18/FY19/FY24; program paused FY20-FY23).
  - Fiscal-year overlaps resolved by a column-wise first-non-null merge,
    canonical (earliest, Y-named) publication first.
  - §4b placeholder-$0 masking on unreported/non-compliant FY17-FY18 rows
    (runs at the era seam, pre-merge); is_non_compliant derived from FY17/FY18
    string sentinels, the FY19 ``note``, and the FY21 PPE sentinel.
  - Negative GOSA restatements (Atlanta 660) preserved per §4b.

Cross-family judgment calls (non-interactive merge):

1. ``default_detail`` resolves to the finest level present (``schools``) via
   auto-derivation — matching the platform convention (e.g. direct_certification).
2. NO cross-level "school rows sum to their district row" invariant is asserted:
   the families are independent GOSA downloads with different code universes
   (the school family carries 29 charter district codes the district family
   never publishes) and neither source transform reconciled them.
3. The two families share NO (year, district_code, school_code) keys — every
   school row has a non-NULL school_code and every district row has a NULL
   school_code — so the union never collides across levels (detail_level is part
   of the natural key).
"""

import logging
from pathlib import Path
from typing import Callable

import polars as pl

from src.utils.metadata import write_data_dictionary
from src.utils.readers import (
    extract_year_from_filename,
    list_bronze_files,
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

TOPIC = "financial_efficiency_star_rating"
BRONZE_DIR = Path("data/bronze/education/gosa/financial_efficiency_star_rating")
GOLD_DIR = Path("data/gold/education/financial_efficiency_star_rating")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Merged gold fact column order. `detail_level` is carried for export splitting
# and dropped by export_to_parquet(). No `demographic` column (no breakdowns).
#
# Block layout: shared key cols, then the shared total/PPE block, then the
# district-only financial split + rolling metrics, then the school-only
# included/excluded split + enrollment share, then the shared rating outcome.
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    # --- shared headline financial block (both levels) ---
    "total_expenditures",
    "fte_enrollment",
    "per_pupil_expenditure",
    "federal_per_pupil_expenditure",
    "state_local_per_pupil_expenditure",
    # --- district-only: federal/SL split of total_expenditures ---
    "federal_expenditures",
    "state_local_expenditures",
    # --- school-only: pre-allocation included split + post-allocation total split ---
    "included_expenditures",
    "included_federal_expenditures",
    "included_state_local_expenditures",
    "excluded_expenditures",
    "total_federal_expenditures",
    "total_state_local_expenditures",
    "pct_of_district_enrollment",
    # --- shared annual academic score ---
    "ccrpi_single_score",
    # --- district-only rolling/percentile metrics (report-year rows only) ---
    "per_pupil_expenditure_three_year_avg",
    "ccrpi_three_year_avg",
    "per_pupil_expenditure_percentile",
    # --- shared rating outcome ---
    "fesr_star_rating",
    "is_non_compliant",
    # carried through, dropped on export
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "total_expenditures": pl.Float64,
    "fte_enrollment": pl.Int64,
    "per_pupil_expenditure": pl.Float64,
    "federal_per_pupil_expenditure": pl.Float64,
    "state_local_per_pupil_expenditure": pl.Float64,
    "federal_expenditures": pl.Float64,
    "state_local_expenditures": pl.Float64,
    "included_expenditures": pl.Float64,
    "included_federal_expenditures": pl.Float64,
    "included_state_local_expenditures": pl.Float64,
    "excluded_expenditures": pl.Float64,
    "total_federal_expenditures": pl.Float64,
    "total_state_local_expenditures": pl.Float64,
    "pct_of_district_enrollment": pl.Float64,
    "ccrpi_single_score": pl.Float64,
    "per_pupil_expenditure_three_year_avg": pl.Float64,
    "ccrpi_three_year_avg": pl.Float64,
    "per_pupil_expenditure_percentile": pl.Int64,
    "fesr_star_rating": pl.Float64,
    "is_non_compliant": pl.Boolean,
    "detail_level": pl.Utf8,
}

# Numeric metric columns (manifest stats + NULL-spike checks + collision guard).
# `is_non_compliant` is boolean and excluded from numeric stats.
METRIC_COLUMNS: list[str] = [
    "total_expenditures",
    "fte_enrollment",
    "per_pupil_expenditure",
    "federal_per_pupil_expenditure",
    "state_local_per_pupil_expenditure",
    "federal_expenditures",
    "state_local_expenditures",
    "included_expenditures",
    "included_federal_expenditures",
    "included_state_local_expenditures",
    "excluded_expenditures",
    "total_federal_expenditures",
    "total_state_local_expenditures",
    "pct_of_district_enrollment",
    "ccrpi_single_score",
    "per_pupil_expenditure_three_year_avg",
    "ccrpi_three_year_avg",
    "per_pupil_expenditure_percentile",
    "fesr_star_rating",
]

NATURAL_KEYS: list[str] = ["year", "district_code", "school_code", "detail_level"]

# Columns each family does NOT publish — materialized as typed NULLs so both
# families harmonize to the unioned STANDARD_COLUMNS schema before concat.
DISTRICT_ONLY_COLUMNS: list[str] = [
    "federal_expenditures",
    "state_local_expenditures",
    "per_pupil_expenditure_three_year_avg",
    "ccrpi_three_year_avg",
    "per_pupil_expenditure_percentile",
]
SCHOOL_ONLY_COLUMNS: list[str] = [
    "included_expenditures",
    "included_federal_expenditures",
    "included_state_local_expenditures",
    "excluded_expenditures",
    "total_federal_expenditures",
    "total_state_local_expenditures",
    "pct_of_district_enrollment",
]


def _null_columns(names: list[str]) -> list[pl.Expr]:
    """Typed-NULL literal expressions for the columns a family does not publish."""
    return [pl.lit(None).cast(TARGET_TYPES[c]).alias(c) for c in names]


# =============================================================================
# Casting helpers (shared by both families)
# =============================================================================


def _money(col: str) -> pl.Expr:
    """Cast an all-string bronze metric column to Float64 (non-numeric -> NULL)."""
    return pl.col(col).cast(pl.Float64, strict=False)


def _count(col: str) -> pl.Expr:
    """Cast an all-string bronze count column to Int64 via Float64 (e.g. "984.0")."""
    return pl.col(col).cast(pl.Float64, strict=False).cast(pl.Int64, strict=False)


def _num(expr: pl.Expr) -> pl.Expr:
    """Cast an all-string bronze expression to Float64 (non-numeric -> NULL)."""
    return expr.cast(pl.Float64, strict=False)


def _int(expr: pl.Expr) -> pl.Expr:
    """Cast an all-string bronze expression to Int64 via Float64."""
    return expr.cast(pl.Float64, strict=False).cast(pl.Int64, strict=False)


# =============================================================================
# DISTRICT FAMILY — era logic (detail_level "district")
# =============================================================================

# Report years whose workbooks publish rolling averages + percentile + rating.
DISTRICT_RATING_REPORT_YEARS: tuple[int, ...] = (2016, 2017, 2018, 2019, 2024)

# Non-numeric publisher status in the 2018 FESR column (Talbot County 730).
FESR_NON_COMPLIANT_SENTINELS_DISTRICT: set[str] = {"Non-Compliant"}

# The seven per-fiscal-year financial inputs merged atomically so the federal
# + state_local = total identity stays additive in every gold row.
DISTRICT_FINANCIAL_BLOCK: list[str] = [
    "total_expenditures",
    "federal_expenditures",
    "state_local_expenditures",
    "fte_enrollment",
    "per_pupil_expenditure",
    "federal_per_pupil_expenditure",
    "state_local_per_pupil_expenditure",
]
DISTRICT_PER_YEAR_METRICS: list[str] = DISTRICT_FINANCIAL_BLOCK + ["ccrpi_single_score"]
# Report-level metrics attached only to the report-year row (C-1-renamed).
DISTRICT_ROLLING_METRICS: list[str] = [
    "per_pupil_expenditure_three_year_avg",
    "ccrpi_three_year_avg",
    "per_pupil_expenditure_percentile",
    "fesr_star_rating",
]

# Rolling/rating bronze headers: 2016-2018 use upper-case AVG/PCTL; 2019/2024
# use mixed-case Avg/pctl. (FESR header is constant.)
DISTRICT_ROLLING_MAP_UPPER: dict[str, str] = {
    "per_pupil_expenditure_three_year_avg": "PPE_AVG",
    "ccrpi_three_year_avg": "SS_AVG",
    "per_pupil_expenditure_percentile": "PPE_PCTL",
    "fesr_star_rating": "FESR",
}
DISTRICT_ROLLING_MAP_MIXED: dict[str, str] = {
    "per_pupil_expenditure_three_year_avg": "PPE_Avg",
    "ccrpi_three_year_avg": "SS_Avg",
    "per_pupil_expenditure_percentile": "PPE_pctl",
    "fesr_star_rating": "FESR",
}


def _district_pattern_a_map(fy: int) -> dict[str, str | None]:
    """2016 workbook: 4-digit suffixes, no federal/state-local breakdown."""
    return {
        "total_expenditures": f"Expenditures_{fy}",
        "federal_expenditures": None,
        "state_local_expenditures": None,
        "fte_enrollment": f"FTE_{fy}",
        "per_pupil_expenditure": f"PPE_{fy}",
        "federal_per_pupil_expenditure": None,
        "state_local_per_pupil_expenditure": None,
        "ccrpi_single_score": f"SingleScore_{fy}",
    }


def _district_pattern_b_map(fy: int) -> dict[str, str | None]:
    """2017-2018 workbooks: 4-digit suffixes with Federal_Exp_*/State_Local_Exp_*."""
    return {
        "total_expenditures": f"Expenditures_{fy}",
        "federal_expenditures": f"Federal_Exp_{fy}",
        "state_local_expenditures": f"State_Local_Exp_{fy}",
        "fte_enrollment": f"FTE_{fy}",
        "per_pupil_expenditure": f"PPE_{fy}",
        "federal_per_pupil_expenditure": f"Federal_Exp_PPE_{fy}",
        "state_local_per_pupil_expenditure": f"State_Local_Exp_PPE_{fy}",
        "ccrpi_single_score": f"SingleScore_{fy}",
    }


def _district_pattern_c_map(fy: int) -> dict[str, str | None]:
    """2019/2024 workbooks: 2-digit suffixes, School_Amt_*/k12_enrollment_* naming."""
    yy = f"{fy % 100:02d}"
    return {
        "total_expenditures": f"School_Amt_{yy}",
        "federal_expenditures": f"Federal_Amt_{yy}",
        "state_local_expenditures": f"State_Local_Amt_{yy}",
        "fte_enrollment": f"k12_enrollment_{yy}",
        "per_pupil_expenditure": f"PPE_{yy}",
        "federal_per_pupil_expenditure": f"Federal_PPE_{yy}",
        "state_local_per_pupil_expenditure": f"State_Local_PPE_{yy}",
        "ccrpi_single_score": f"SingleScore_{fy}",
    }


def _district_pattern_d_map(
    total_prefix: str,
) -> Callable[[int], dict[str, str | None]]:
    """2020-2023 workbooks: single-year PPE inputs, no score/rating columns."""

    def _map(fy: int) -> dict[str, str | None]:
        yy = f"{fy % 100:02d}"
        return {
            "total_expenditures": f"{total_prefix}_{yy}",
            "federal_expenditures": f"Federal_Amt_{yy}",
            "state_local_expenditures": f"State_Local_Amt_{yy}",
            "fte_enrollment": f"k12_enrollment_{yy}",
            "per_pupil_expenditure": f"PPE_{yy}",
            "federal_per_pupil_expenditure": f"PPE_Fed_{yy}",
            "state_local_per_pupil_expenditure": f"PPE_SL_{yy}",
            "ccrpi_single_score": None,
        }

    return _map


DISTRICT_ERA_SPECS: dict[str, dict] = {
    "era_2016": {
        "report_year": 2016,
        "id_col": "System ID",
        "fiscal_years": (2014, 2015, 2016),
        "per_year_map": _district_pattern_a_map,
        "rolling_map": DISTRICT_ROLLING_MAP_UPPER,
    },
    "era_2017": {
        "report_year": 2017,
        "id_col": "systemid",
        "fiscal_years": (2015, 2016, 2017),
        "per_year_map": _district_pattern_b_map,
        "rolling_map": DISTRICT_ROLLING_MAP_UPPER,
    },
    "era_2018": {
        "report_year": 2018,
        "id_col": "systemid",
        "fiscal_years": (2016, 2017, 2018),
        "per_year_map": _district_pattern_b_map,
        "rolling_map": DISTRICT_ROLLING_MAP_UPPER,
    },
    "era_2019": {
        "report_year": 2019,
        "id_col": "SystemId",
        "fiscal_years": (2017, 2018, 2019),
        "per_year_map": _district_pattern_c_map,
        "rolling_map": DISTRICT_ROLLING_MAP_MIXED,
    },
    "era_2020": {
        "report_year": 2020,
        "id_col": "SystemID",
        "fiscal_years": (2020,),
        "per_year_map": _district_pattern_d_map("School_Amt"),
        "rolling_map": None,
    },
    "era_2021": {
        "report_year": 2021,
        "id_col": "SystemID",
        "fiscal_years": (2021,),
        "per_year_map": _district_pattern_d_map("School_Amt"),
        "rolling_map": None,
    },
    "era_2022": {
        "report_year": 2022,
        "id_col": "DISTRICT_ID",
        "fiscal_years": (2022,),
        "per_year_map": _district_pattern_d_map("amount"),
        "rolling_map": None,
    },
    "era_2023": {
        "report_year": 2023,
        "id_col": "DISTRICT_ID",
        "fiscal_years": (2023,),
        "per_year_map": _district_pattern_d_map("amount"),
        "rolling_map": None,
    },
    "era_2024": {
        "report_year": 2024,
        "id_col": "system_id",
        "fiscal_years": (2019, 2023, 2024),
        "per_year_map": _district_pattern_c_map,
        "rolling_map": DISTRICT_ROLLING_MAP_MIXED,
    },
}

DISTRICT_ERA_SIGNATURES: dict[str, list[str]] = {
    "era_2024": ["system_id", "School_Amt_24"],
    "era_2023": ["DISTRICT_ID", "amount_23"],
    "era_2022": ["DISTRICT_ID", "amount_22"],
    "era_2021": ["SystemID", "School_Amt_21"],
    "era_2020": ["SystemID", "School_Amt_20"],
    "era_2019": ["SystemId", "School_Amt_19"],
    "era_2018": ["systemid", "Expenditures_2018"],
    "era_2017": ["systemid", "Expenditures_2015"],
    "era_2016": ["System ID", "Expenditures_2014"],
}


def _district_require_columns(
    df: pl.DataFrame, required: list[str], label: str
) -> None:
    """Raise if any expected bronze column is absent (rename-coverage guard)."""
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"{label}: expected bronze column(s) missing: {missing}. "
            f"Present: {df.columns}"
        )


def _district_build_year_frame(
    df: pl.DataFrame,
    fiscal_year: int,
    report_year: int,
    mapping: dict[str, str | None],
) -> pl.DataFrame:
    """Build the long-format MERGED-schema frame for one district fiscal year.

    School-only columns are emitted as typed NULLs (district rows have no
    included/excluded split or enrollment share). Rolling/rating columns +
    is_non_compliant start NULL; _district_attach_rolling overwrites them on
    the report-year frame only. `_report_year` tracks the publishing workbook.
    """
    exprs: list[pl.Expr] = [
        pl.lit(fiscal_year).cast(pl.Int32).alias("year"),
        pl.col("_raw_system_id").cast(pl.Utf8).str.zfill(3).alias("district_code"),
        pl.lit(None).cast(pl.Utf8).alias("school_code"),
        pl.lit("district").alias("detail_level"),
        pl.lit(report_year).cast(pl.Int32).alias("_report_year"),
    ]
    for col in DISTRICT_PER_YEAR_METRICS:
        bronze_col = mapping[col]
        if bronze_col is None:
            exprs.append(pl.lit(None).cast(TARGET_TYPES[col]).alias(col))
        elif TARGET_TYPES[col] == pl.Int64:
            exprs.append(_count(bronze_col).alias(col))
        else:
            exprs.append(_money(bronze_col).alias(col))
    for col in DISTRICT_ROLLING_METRICS + ["is_non_compliant"]:
        exprs.append(pl.lit(None).cast(TARGET_TYPES[col]).alias(col))
    # School-only columns: always NULL on district rows.
    exprs.extend(_null_columns(SCHOOL_ONLY_COLUMNS))
    return df.select(exprs)


def _district_attach_rolling(
    year_frames: list[pl.DataFrame],
    report_year: int,
    df: pl.DataFrame,
    rolling_map: dict[str, str],
    manifest: TransformManifest,
) -> list[pl.DataFrame]:
    """Overwrite the report-year frame's rolling/rating columns with bronze values."""
    raw_fesr = pl.col(rolling_map["fesr_star_rating"]).cast(pl.Utf8)

    n_sentinel = int(
        df.select(
            raw_fesr.is_in(list(FESR_NON_COMPLIANT_SENTINELS_DISTRICT)).sum()
        ).item()
    )
    if n_sentinel:
        manifest.record_masked(
            column="fesr_star_rating",
            count=n_sentinel,
            reason=(
                "bronze FESR='Non-Compliant' publisher status (not a numeric "
                "rating) on a district row — rating NULLed, status preserved "
                "via is_non_compliant=True (Talbot County 730, 2018 report)"
            ),
            years=[report_year],
        )

    rolling = df.select(
        pl.col("_raw_system_id").cast(pl.Utf8).str.zfill(3).alias("district_code"),
        _money(rolling_map["per_pupil_expenditure_three_year_avg"]).alias(
            "per_pupil_expenditure_three_year_avg"
        ),
        _money(rolling_map["ccrpi_three_year_avg"]).alias("ccrpi_three_year_avg"),
        _count(rolling_map["per_pupil_expenditure_percentile"]).alias(
            "per_pupil_expenditure_percentile"
        ),
        _money(rolling_map["fesr_star_rating"]).alias("fesr_star_rating"),
        pl.when(raw_fesr.is_null())
        .then(None)
        .when(raw_fesr.is_in(list(FESR_NON_COMPLIANT_SENTINELS_DISTRICT)))
        .then(True)
        .otherwise(False)
        .cast(pl.Boolean)
        .alias("is_non_compliant"),
    )

    updated: list[pl.DataFrame] = []
    overlay_cols = DISTRICT_ROLLING_METRICS + ["is_non_compliant"]
    for frame in year_frames:
        if int(frame["year"].head(1).item()) != report_year:
            updated.append(frame)
            continue
        merged = (
            frame.drop(overlay_cols)
            .join(rolling, on="district_code", how="left")
            .select(frame.columns)
        )
        updated.append(merged)
    return updated


def _transform_district_file(
    path: Path, manifest: TransformManifest
) -> list[pl.DataFrame]:
    """Read one district workbook, detect its era, unpivot to per-fiscal-year frames."""
    filename_year = extract_year_from_filename(path.name)
    if filename_year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")

    df, loss = read_bronze_file(path, return_loss=True)
    manifest.record_read_loss(
        filename_year, path.name, loss["raw_rows"], loss["parsed_rows"]
    )

    # 2018 workbook ships ` FTE_2016 ` / ` FTE_2017 ` headers with stray
    # whitespace — strip every header before era detection and mapping.
    strip_renames = {c: c.strip() for c in df.columns if c != c.strip()}
    if strip_renames:
        logger.info(
            "%s: stripped whitespace from %d column header(s): %s",
            path.name,
            len(strip_renames),
            sorted(strip_renames),
        )
        df = df.rename(strip_renames)

    era = detect_era_by_columns(df, DISTRICT_ERA_SIGNATURES)
    if era is None:
        raise ValueError(
            f"{path.name}: no district era signature matched columns {df.columns}"
        )
    spec = DISTRICT_ERA_SPECS[era]
    if spec["report_year"] != filename_year:
        raise ValueError(
            f"{path.name}: column-detected era {era} disagrees with filename "
            f"year {filename_year}"
        )
    manifest.record_file(path, filename_year, era, df.height, df.columns)
    logger.info(
        "Processing %s as district/%s (report year %d, %d rows)",
        path.name,
        era,
        filename_year,
        df.height,
    )

    # 2023 workbook's constant SCHOOL_YEAR — cross-check then drop.
    if "SCHOOL_YEAR" in df.columns:
        school_years = df["SCHOOL_YEAR"].cast(pl.Utf8).unique().to_list()
        if school_years != [str(filename_year)]:
            raise ValueError(
                f"{path.name}: SCHOOL_YEAR values {school_years} disagree "
                f"with filename year {filename_year}"
            )

    required = [spec["id_col"]]
    structurally_absent: list[str] = []
    for fy in spec["fiscal_years"]:
        for gold_col, bronze_col in spec["per_year_map"](fy).items():
            if bronze_col is None:
                structurally_absent.append(f"{gold_col} (FY{fy})")
            else:
                required.append(bronze_col)
    if spec["rolling_map"] is not None:
        required.extend(spec["rolling_map"].values())
    _district_require_columns(df, required, f"district/{era} {path.name}")
    if structurally_absent:
        logger.info(
            "%s: structurally absent in bronze (emitted as NULL): %s",
            path.name,
            structurally_absent,
        )

    df = df.rename({spec["id_col"]: "_raw_system_id"})
    year_frames = [
        _district_build_year_frame(
            df,
            fiscal_year=fy,
            report_year=spec["report_year"],
            mapping=spec["per_year_map"](fy),
        )
        for fy in spec["fiscal_years"]
    ]
    if spec["rolling_map"] is not None:
        year_frames = _district_attach_rolling(
            year_frames,
            report_year=spec["report_year"],
            df=df,
            rolling_map=spec["rolling_map"],
            manifest=manifest,
        )
    else:
        logger.info(
            "%s: Pattern D workbook — no rolling/rating columns (program pause); "
            "rolling metrics + is_non_compliant stay NULL for FY%d.",
            path.name,
            spec["report_year"],
        )
    return year_frames


def _merge_district_overlaps(
    combined: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Collapse overlapping (year, district_code) district rows via column-wise merge.

    Non-financial columns: report-year-then-newest first-non-null. The seven
    financial-block columns: taken atomically from a row with a complete
    federal+state-local breakdown (then report-year, then newest), keeping
    federal + state_local = total additive in every gold row.
    """
    initial = combined.height
    combined = combined.with_columns(
        (pl.col("year") == pl.col("_report_year")).alias("_is_report_year"),
        (
            pl.col("total_expenditures").is_not_null()
            & pl.col("federal_expenditures").is_not_null()
            & pl.col("state_local_expenditures").is_not_null()
        ).alias("_has_complete_financial_block"),
    )

    main_sorted = combined.sort(
        ["year", "district_code", "_is_report_year", "_report_year"],
        descending=[False, False, True, True],
    )
    block_sorted = combined.sort(
        [
            "year",
            "district_code",
            "_has_complete_financial_block",
            "_is_report_year",
            "_report_year",
        ],
        descending=[False, False, True, True, True],
    )

    merge_cols = [c for c in STANDARD_COLUMNS if c not in ("year", "district_code")]
    non_financial_cols = [c for c in merge_cols if c not in DISTRICT_FINANCIAL_BLOCK]
    main_agg = main_sorted.group_by(["year", "district_code"]).agg(
        [pl.col(c).drop_nulls().first().alias(c) for c in non_financial_cols]
    )
    block_agg = block_sorted.group_by(["year", "district_code"]).agg(
        [pl.col(c).drop_nulls().first().alias(c) for c in DISTRICT_FINANCIAL_BLOCK]
    )
    merged = main_agg.join(block_agg, on=["year", "district_code"], how="inner")

    pre = dict(combined.group_by("year").len().iter_rows())
    post = dict(merged.group_by("year").len().iter_rows())
    for year in sorted(pre):
        removed = pre[year] - post.get(year, 0)
        if removed > 0:
            manifest.record_filtered(
                int(year), int(removed), "district_fiscal_year_overlap_merged"
            )
    logger.info(
        "District fiscal-year overlap merge: %s -> %s rows (%s merged)",
        f"{initial:,}",
        f"{merged.height:,}",
        f"{initial - merged.height:,}",
    )
    return merged.select([c for c in STANDARD_COLUMNS if c != "_report_year"])


# =============================================================================
# SCHOOL FAMILY — era logic (detail_level "school")
# =============================================================================

SCHOOL_ERA_SIGNATURES: dict[str, list[str]] = {
    "era_2024": ["schoolyear", "single_score_24", "school_ppe_24"],
    "era_2023": ["school_year", "schoolid2", "school_ppe_23"],
    "era_2019": ["singlescore_19", "school_ppe_19", "amount_17", "school_ppe_17"],
    "era_2022": ["included_school_amnt_22", "ppe_22", "fte_enroll_22"],
    "era_2021": ["school_ppe_21", "k12_enrollment_21"],
    "era_2020": ["school_ppe_20", "k12_enrollment_20"],
    "era_2018": ["Included_School_Amt_18", "PPE_18", "FESR"],
    "era_2017": ["Included_School_Amt_17", "PPE_17", "FESR"],
}

SCHOOL_ERA_REPORT_YEAR: dict[str, int] = {
    "era_2017": 2017,
    "era_2018": 2018,
    "era_2019": 2019,
    "era_2020": 2020,
    "era_2021": 2021,
    "era_2022": 2022,
    "era_2023": 2023,
    "era_2024": 2024,
}

# 2017/2018 FESR string sentinels that flag non-compliance.
FESR_NON_COMPLIANT_SENTINELS_SCHOOL: set[str] = {
    "Non-Compliant",
    "Non-Compliant in 2017",
    "Non-Compliant in 2018",
}

# Per-fiscal-year metrics every school era maps from bronze (fesr_star_rating /
# is_non_compliant are report-year-only and attached separately).
SCHOOL_PER_YEAR_METRICS: list[str] = [
    "included_expenditures",
    "included_federal_expenditures",
    "included_state_local_expenditures",
    "excluded_expenditures",
    "total_expenditures",
    "total_federal_expenditures",
    "total_state_local_expenditures",
    "fte_enrollment",
    "pct_of_district_enrollment",
    "per_pupil_expenditure",
    "federal_per_pupil_expenditure",
    "state_local_per_pupil_expenditure",
    "ccrpi_single_score",
]


def _zfill3(expr: pl.Expr) -> pl.Expr:
    return expr.cast(pl.Utf8).str.zfill(3)


def _zfill4(expr: pl.Expr) -> pl.Expr:
    return expr.cast(pl.Utf8).str.zfill(4)


def _school_prepare_ids(
    df: pl.DataFrame, district_col: str, school_col: str
) -> pl.DataFrame:
    """Attach `_raw_district_code` (zfill3) and `_raw_school_code` (zfill4)."""
    return df.with_columns(
        _zfill3(pl.col(district_col)).alias("_raw_district_code"),
        _zfill4(pl.col(school_col)).alias("_raw_school_code"),
    )


def _school_build_year_frame(
    df: pl.DataFrame,
    fiscal_year: int,
    report_year: int,
    mapping: dict[str, str | None],
) -> pl.DataFrame:
    """Build the long-format MERGED-schema frame for one school fiscal year.

    District-only columns are emitted as typed NULLs. fesr_star_rating /
    is_non_compliant start NULL here; the caller overlays them via
    `_school_attach_report_year_metrics` on the appropriate frames.
    """
    missing = [
        bronze for bronze in mapping.values() if bronze and bronze not in df.columns
    ]
    if missing:
        raise ValueError(
            f"FY{fiscal_year} (report {report_year}): mapped bronze columns "
            f"missing from file: {missing}. Present: {df.columns}"
        )

    exprs: list[pl.Expr] = [
        pl.lit(fiscal_year).cast(pl.Int32).alias("year"),
        pl.col("_raw_district_code").alias("district_code"),
        pl.col("_raw_school_code").alias("school_code"),
        pl.lit(report_year).cast(pl.Int32).alias("_report_year"),
    ]
    absent: list[str] = []
    for col in SCHOOL_PER_YEAR_METRICS:
        bronze_col = mapping.get(col)
        target_dtype = TARGET_TYPES[col]
        if bronze_col is None:
            absent.append(col)
            exprs.append(pl.lit(None).cast(target_dtype).alias(col))
        elif target_dtype == pl.Int64:
            exprs.append(_int(pl.col(bronze_col)).alias(col))
        else:
            exprs.append(_num(pl.col(bronze_col)).alias(col))
    if absent:
        logger.info(
            "FY%d (report %d): metrics not published by this era -> NULL: %s",
            fiscal_year,
            report_year,
            absent,
        )

    exprs.append(pl.lit(None).cast(pl.Float64).alias("fesr_star_rating"))
    exprs.append(pl.lit(None).cast(pl.Boolean).alias("is_non_compliant"))
    exprs.append(pl.lit("school").alias("detail_level"))
    # District-only columns: always NULL on school rows.
    exprs.extend(_null_columns(DISTRICT_ONLY_COLUMNS))
    return df.select(exprs)


def _school_attach_report_year_metrics(
    year_frames: list[pl.DataFrame],
    report_year: int,
    df: pl.DataFrame,
    fesr_col: str,
    fesr_is_string: bool,
) -> list[pl.DataFrame]:
    """Overlay fesr_star_rating + is_non_compliant onto the right school frame(s)."""
    if fesr_is_string:
        raw_fesr = pl.col(fesr_col)
        sentinel_year_map: dict[str, int] = {
            "Non-Compliant": report_year,
            "Non-Compliant in 2017": 2017,
            "Non-Compliant in 2018": 2018,
        }
        flag_year_expr = pl.lit(None).cast(pl.Int32)
        for sentinel, fy in sentinel_year_map.items():
            flag_year_expr = (
                pl.when(raw_fesr == sentinel)
                .then(pl.lit(fy).cast(pl.Int32))
                .otherwise(flag_year_expr)
            )
        overlay = df.select(
            pl.col("_raw_district_code").alias("district_code"),
            pl.col("_raw_school_code").alias("school_code"),
            _num(raw_fesr).alias("fesr_star_rating"),
            pl.when(raw_fesr.is_null())
            .then(None)
            .when(raw_fesr.is_in(list(FESR_NON_COMPLIANT_SENTINELS_SCHOOL)))
            .then(True)
            .otherwise(False)
            .cast(pl.Boolean)
            .alias("is_non_compliant"),
            flag_year_expr.alias("_flag_year"),
        )
    else:
        overlay = df.select(
            pl.col("_raw_district_code").alias("district_code"),
            pl.col("_raw_school_code").alias("school_code"),
            _num(pl.col(fesr_col)).alias("fesr_star_rating"),
            pl.lit(None).cast(pl.Boolean).alias("is_non_compliant"),
            pl.lit(None).cast(pl.Int32).alias("_flag_year"),
        )

    report_year_overlay = overlay.drop("_flag_year")

    routed_overlays: dict[int, pl.DataFrame] = {}
    if fesr_is_string:
        frame_years = {int(f["year"].head(1).item()) for f in year_frames}
        for fy in frame_years - {report_year}:
            sub = overlay.filter(pl.col("_flag_year") == fy).select(
                "district_code",
                "school_code",
                pl.col("is_non_compliant").alias("_routed_flag"),
            )
            if sub.height:
                routed_overlays[fy] = sub

    updated: list[pl.DataFrame] = []
    for frame in year_frames:
        fy = int(frame["year"].head(1).item())
        if fy == report_year:
            merged = (
                frame.drop("fesr_star_rating", "is_non_compliant")
                .join(
                    report_year_overlay, on=["district_code", "school_code"], how="left"
                )
                .select(frame.columns)
            )
            updated.append(merged)
        elif fy in routed_overlays:
            merged = (
                frame.join(
                    routed_overlays[fy], on=["district_code", "school_code"], how="left"
                )
                .with_columns(
                    pl.coalesce("_routed_flag", "is_non_compliant").alias(
                        "is_non_compliant"
                    )
                )
                .select(frame.columns)
            )
            updated.append(merged)
        else:
            updated.append(frame)
    return updated


def _school_null_placeholder_zero_amounts(
    df: pl.DataFrame,
    fiscal_year: int,
    report_year: int,
    fesr_col: str,
    amt_cols: dict[str, str],
    fte_col: str | None,
    ppe_col: str,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """§4b mask: NULL zero-dollar placeholders on unreported school observations."""
    fy_sentinels = [f"Non-Compliant in {fiscal_year}", "Non-Compliant"]

    ppe_null = _num(pl.col(ppe_col)).is_null()
    sentinel_for_fy = pl.col(fesr_col).is_in(fy_sentinels)
    if fte_col is not None:
        fte_null = _num(pl.col(fte_col)).is_null()
        placeholder = (fte_null & ppe_null) | (sentinel_for_fy & ppe_null)
    else:
        placeholder = sentinel_for_fy & ppe_null

    for gold_col, amt_col in amt_cols.items():
        mask = placeholder & (_num(pl.col(amt_col)) == 0)
        count = df.select(mask.sum().alias("n")).item()
        if count:
            manifest.record_masked(
                column=gold_col,
                count=int(count),
                reason=(
                    f"placeholder $0 in bronze '{amt_col}' ({report_year} "
                    f"file) on unreported/non-compliant FY{fiscal_year} school "
                    f"rows (FTE+PPE NULL or non-compliance sentinel with NULL "
                    f"PPE) — §4b NULLed"
                ),
                years=[fiscal_year],
            )
        df = df.with_columns(
            pl.when(mask).then(None).otherwise(pl.col(amt_col)).alias(amt_col)
        )
    return df


def _warn_negative_amounts(df: pl.DataFrame, label: str) -> None:
    """Log preserved negative dollar values (§4b extreme-but-conceivable)."""
    negative_cols = [
        "included_expenditures",
        "excluded_expenditures",
        "total_expenditures",
        "per_pupil_expenditure",
    ]
    for col in negative_cols:
        neg = df.filter(pl.col(col) < 0)
        if neg.height:
            logger.warning(
                "%s: %d negative %s value(s) preserved per §4b. Sample: %s",
                label,
                neg.height,
                col,
                neg.select("year", "district_code", "school_code", col)
                .head(3)
                .to_dicts(),
            )


def _school_era_2017(
    df: pl.DataFrame, manifest: TransformManifest
) -> list[pl.DataFrame]:
    """School era 2017: FY17 block, PascalCase ids, string FESR with sentinels."""
    df = _school_prepare_ids(df, "SystemId", "SchoolId")
    df = _school_null_placeholder_zero_amounts(
        df,
        fiscal_year=2017,
        report_year=2017,
        fesr_col="FESR",
        amt_cols={
            "included_expenditures": "Included_School_Amt_17",
            "included_federal_expenditures": "Included_Federal_Amt_17",
            "included_state_local_expenditures": "Included_State_Local_Amt_17",
            "excluded_expenditures": "Excluded_School_Amt_17",
            "total_expenditures": "Total_Amt_17",
            "total_federal_expenditures": "Total_Federal_Amt_17",
            "total_state_local_expenditures": "Total_State_Local_Amt_17",
        },
        fte_col=None,
        ppe_col="PPE_17",
        manifest=manifest,
    )
    frames = [
        _school_build_year_frame(
            df,
            fiscal_year=2017,
            report_year=2017,
            mapping={
                "included_expenditures": "Included_School_Amt_17",
                "included_federal_expenditures": "Included_Federal_Amt_17",
                "included_state_local_expenditures": "Included_State_Local_Amt_17",
                "excluded_expenditures": "Excluded_School_Amt_17",
                "total_expenditures": "Total_Amt_17",
                "total_federal_expenditures": "Total_Federal_Amt_17",
                "total_state_local_expenditures": "Total_State_Local_Amt_17",
                "fte_enrollment": "FTE_enroll_17",
                "pct_of_district_enrollment": "enroll_pct_17",
                "per_pupil_expenditure": "PPE_17",
                "federal_per_pupil_expenditure": "Federal_PPE_17",
                "state_local_per_pupil_expenditure": "State_Local_PPE_17",
                "ccrpi_single_score": None,
            },
        )
    ]
    return _school_attach_report_year_metrics(
        frames, report_year=2017, df=df, fesr_col="FESR", fesr_is_string=True
    )


def _school_era_2018(
    df: pl.DataFrame, manifest: TransformManifest
) -> list[pl.DataFrame]:
    """School era 2018: FY17+FY18 blocks; FESR string with year-named sentinels."""
    df = _school_prepare_ids(df, "SystemId", "SchoolId")
    for fy in (2017, 2018):
        yy = f"{fy % 100:02d}"
        df = _school_null_placeholder_zero_amounts(
            df,
            fiscal_year=fy,
            report_year=2018,
            fesr_col="FESR",
            amt_cols={
                "included_expenditures": f"Included_School_Amt_{yy}",
                "included_federal_expenditures": f"Included_Federal_Amt_{yy}",
                "included_state_local_expenditures": f"Included_State_Local_Amt_{yy}",
                "excluded_expenditures": f"Excluded_School_Amt_{yy}",
                "total_expenditures": f"Total_Amt_{yy}",
                "total_federal_expenditures": f"Total_Federal_Amt_{yy}",
                "total_state_local_expenditures": f"Total_State_Local_Amt_{yy}",
            },
            fte_col=f"FTE_enroll_{yy}",
            ppe_col=f"PPE_{yy}",
            manifest=manifest,
        )
    frames = [
        _school_build_year_frame(
            df,
            fiscal_year=fy,
            report_year=2018,
            mapping={
                "included_expenditures": f"Included_School_Amt_{yy}",
                "included_federal_expenditures": f"Included_Federal_Amt_{yy}",
                "included_state_local_expenditures": f"Included_State_Local_Amt_{yy}",
                "excluded_expenditures": f"Excluded_School_Amt_{yy}",
                "total_expenditures": f"Total_Amt_{yy}",
                "total_federal_expenditures": f"Total_Federal_Amt_{yy}",
                "total_state_local_expenditures": f"Total_State_Local_Amt_{yy}",
                "fte_enrollment": f"FTE_enroll_{yy}",
                "pct_of_district_enrollment": f"enroll_pct_{yy}",
                "per_pupil_expenditure": f"PPE_{yy}",
                "federal_per_pupil_expenditure": f"Federal_PPE_{yy}",
                "state_local_per_pupil_expenditure": f"State_Local_PPE_{yy}",
                "ccrpi_single_score": None,
            },
        )
        for fy, yy in ((2017, "17"), (2018, "18"))
    ]
    return _school_attach_report_year_metrics(
        frames, report_year=2018, df=df, fesr_col="FESR", fesr_is_string=True
    )


def _school_era_2019(
    df: pl.DataFrame, manifest: TransformManifest
) -> list[pl.DataFrame]:
    """School era 2019: FY17+FY18+FY19 blocks, lowercase ids, numeric FESR + note."""
    del manifest  # No §4b masks in this era (unreported cells are NULL).
    df = _school_prepare_ids(df, "systemid", "schoolid")

    note_overlay = (
        df.select(
            pl.col("_raw_district_code").alias("district_code"),
            pl.col("_raw_school_code").alias("school_code"),
            pl.col("note")
            .str.to_lowercase()
            .str.contains("non-compliant")
            .fill_null(False)
            .alias("_noted"),
        )
        .filter(pl.col("_noted"))
        .drop("_noted")
    )
    if note_overlay.height:
        logger.info(
            "2019 school file: %d school(s) flagged non-compliant via note: %s",
            note_overlay.height,
            note_overlay.to_dicts(),
        )

    frames = []
    for fy in (2017, 2018, 2019):
        yy = f"{fy % 100:02d}"
        frames.append(
            _school_build_year_frame(
                df,
                fiscal_year=fy,
                report_year=2019,
                mapping={
                    "included_expenditures": f"amount_{yy}",
                    "included_federal_expenditures": f"Federal_Amt_{yy}",
                    "included_state_local_expenditures": f"State_Local_Amt_{yy}",
                    "excluded_expenditures": (
                        "excluded_19" if fy == 2019 else f"Excluded_Amt_{yy}"
                    ),
                    "total_expenditures": f"school_with_cc_{yy}",
                    "total_federal_expenditures": f"school_with_cc_fed_{yy}",
                    "total_state_local_expenditures": f"school_with_cc_state_{yy}",
                    "fte_enrollment": f"k12_enrollment_{yy}",
                    "pct_of_district_enrollment": f"enroll_pct_{yy}",
                    "per_pupil_expenditure": f"school_ppe_{yy}",
                    "federal_per_pupil_expenditure": f"school_ppe_fed_{yy}",
                    "state_local_per_pupil_expenditure": f"school_ppe_sl_{yy}",
                    "ccrpi_single_score": f"singlescore_{yy}",
                },
            )
        )
    frames = _school_attach_report_year_metrics(
        frames, report_year=2019, df=df, fesr_col="FESR", fesr_is_string=False
    )

    if note_overlay.height == 0:
        return frames
    updated = []
    for frame in frames:
        if int(frame["year"].head(1).item()) != 2019:
            updated.append(frame)
            continue
        updated.append(
            frame.join(
                note_overlay.with_columns(pl.lit(True).alias("_flag")),
                on=["district_code", "school_code"],
                how="left",
            )
            .with_columns(
                pl.coalesce("_flag", "is_non_compliant").alias("is_non_compliant")
            )
            .select(frame.columns)
        )
    return updated


def _school_transform_single_year(
    df: pl.DataFrame,
    fiscal_year: int,
    school_col: str,
    mapping: dict[str, str | None],
) -> list[pl.DataFrame]:
    """Shared body for the PPE-only single-fiscal-year school files (2020-2023)."""
    df = _school_prepare_ids(df, "systemid", school_col)
    return [
        _school_build_year_frame(
            df, fiscal_year=fiscal_year, report_year=fiscal_year, mapping=mapping
        )
    ]


def _school_era_2020(
    df: pl.DataFrame, manifest: TransformManifest
) -> list[pl.DataFrame]:
    """School era 2020: PPE-only; unsuffixed amounts, `weight` share, `_20` PPE."""
    del manifest
    return _school_transform_single_year(
        df,
        fiscal_year=2020,
        school_col="schoolid",
        mapping={
            "included_expenditures": "amount",
            "included_federal_expenditures": "Federal_Amt",
            "included_state_local_expenditures": "State_Local_Amt",
            "excluded_expenditures": "excluded",
            "total_expenditures": "school_with_cc",
            "total_federal_expenditures": "school_with_cc_fed",
            "total_state_local_expenditures": "school_with_cc_state",
            "fte_enrollment": "k12_enrollment_20",
            "pct_of_district_enrollment": "weight",
            "per_pupil_expenditure": "school_ppe_20",
            "federal_per_pupil_expenditure": "school_ppe_fed_20",
            "state_local_per_pupil_expenditure": "school_ppe_sl_20",
            "ccrpi_single_score": None,
        },
    )


def _school_era_2021(
    df: pl.DataFrame, manifest: TransformManifest
) -> list[pl.DataFrame]:
    """School era 2021: like 2020 (`_21` PPE) + one PPE-sentinel non-compliance."""
    del manifest
    ppe_cols = ("school_ppe_21", "school_ppe_fed_21", "school_ppe_sl_21")
    non_compliant_expr = pl.any_horizontal(
        [pl.col(c) == "Non-Compliant" for c in ppe_cols if c in df.columns]
    )
    overlay = (
        _school_prepare_ids(df, "systemid", "schoolid")
        .select(
            pl.col("_raw_district_code").alias("district_code"),
            pl.col("_raw_school_code").alias("school_code"),
            non_compliant_expr.fill_null(False).alias("_flag"),
        )
        .filter(pl.col("_flag"))
        .with_columns(pl.lit(True).alias("_flag"))
    )
    if overlay.height:
        logger.info(
            "2021 school file: %d school(s) with `Non-Compliant` PPE sentinel: %s",
            overlay.height,
            overlay.select("district_code", "school_code").to_dicts(),
        )

    frames = _school_transform_single_year(
        df,
        fiscal_year=2021,
        school_col="schoolid",
        mapping={
            "included_expenditures": "amount",
            "included_federal_expenditures": "Federal_Amt",
            "included_state_local_expenditures": "State_Local_Amt",
            "excluded_expenditures": "excluded",
            "total_expenditures": "school_with_cc",
            "total_federal_expenditures": "school_with_cc_fed",
            "total_state_local_expenditures": "school_with_cc_state",
            "fte_enrollment": "k12_enrollment_21",
            "pct_of_district_enrollment": "weight",
            "per_pupil_expenditure": "school_ppe_21",
            "federal_per_pupil_expenditure": "school_ppe_fed_21",
            "state_local_per_pupil_expenditure": "school_ppe_sl_21",
            "ccrpi_single_score": None,
        },
    )
    if overlay.height == 0:
        return frames
    return [
        frame.join(overlay, on=["district_code", "school_code"], how="left")
        .with_columns(
            pl.coalesce("_flag", "is_non_compliant").alias("is_non_compliant")
        )
        .select(frame.columns)
        for frame in frames
    ]


def _school_era_2022(
    df: pl.DataFrame, manifest: TransformManifest
) -> list[pl.DataFrame]:
    """School era 2022: snake_case naming with bronze typos preserved."""
    del manifest
    return _school_transform_single_year(
        df,
        fiscal_year=2022,
        school_col="schoolid",
        mapping={
            "included_expenditures": "included_school_amnt_22",
            "included_federal_expenditures": "included_fed_amt_22",
            "included_state_local_expenditures": "included_sl_amt_22",
            "excluded_expenditures": "excluded_school_amt_22",
            "total_expenditures": "total_exp_22",
            "total_federal_expenditures": "total_fed_exp_22",
            "total_state_local_expenditures": "total_sl_exp_22",
            "fte_enrollment": "fte_enroll_22",
            "pct_of_district_enrollment": "school_enroll_pct_22",
            "per_pupil_expenditure": "ppe_22",
            "federal_per_pupil_expenditure": "fed_ppe_22",
            "state_local_per_pupil_expenditure": "sl_ppe_22",
            "ccrpi_single_score": None,
        },
    )


def _school_era_2023(
    df: pl.DataFrame, manifest: TransformManifest
) -> list[pl.DataFrame]:
    """School era 2023: hybrid naming; `schoolid2` (zero-padded) is canonical."""
    del manifest
    return _school_transform_single_year(
        df,
        fiscal_year=2023,
        school_col="schoolid2",
        mapping={
            "included_expenditures": "included_school_amnt_23",
            "included_federal_expenditures": "included_fed_amnt_23",
            "included_state_local_expenditures": "included_SL_amnt_23",
            "excluded_expenditures": "excluded_school_amnt_23",
            "total_expenditures": "school_with_cc",
            "total_federal_expenditures": "school_with_cc_fed",
            "total_state_local_expenditures": "school_with_cc_state",
            "fte_enrollment": "k12_enrollment_23",
            "pct_of_district_enrollment": "school_enroll_pct_23",
            "per_pupil_expenditure": "school_ppe_23",
            "federal_per_pupil_expenditure": "school_ppe_fed_23",
            "state_local_per_pupil_expenditure": "school_ppe_sl_23",
            "ccrpi_single_score": None,
        },
    )


def _school_era_2024(
    df: pl.DataFrame, manifest: TransformManifest
) -> list[pl.DataFrame]:
    """School era 2024: FESR resumes; FY19+FY23+FY24 blocks, `weight_{yy}` shares."""
    del manifest
    df = _school_prepare_ids(df, "systemid", "schoolid")
    single_score_cols = {
        2019: "singlescore_19",
        2023: "single_score_23",
        2024: "single_score_24",
    }
    frames = []
    for fy in (2019, 2023, 2024):
        yy = f"{fy % 100:02d}"
        frames.append(
            _school_build_year_frame(
                df,
                fiscal_year=fy,
                report_year=2024,
                mapping={
                    "included_expenditures": f"amount_{yy}",
                    "included_federal_expenditures": f"Federal_Amt_{yy}",
                    "included_state_local_expenditures": f"State_Local_Amt_{yy}",
                    "excluded_expenditures": f"excluded_{yy}",
                    "total_expenditures": f"school_with_cc_{yy}",
                    "total_federal_expenditures": f"school_with_cc_fed_{yy}",
                    "total_state_local_expenditures": f"school_with_cc_state_{yy}",
                    "fte_enrollment": f"k12_enrollment_{yy}",
                    "pct_of_district_enrollment": f"weight_{yy}",
                    "per_pupil_expenditure": f"school_ppe_{yy}",
                    "federal_per_pupil_expenditure": f"school_ppe_fed_{yy}",
                    "state_local_per_pupil_expenditure": f"school_ppe_sl_{yy}",
                    "ccrpi_single_score": single_score_cols[fy],
                },
            )
        )
    return _school_attach_report_year_metrics(
        frames, report_year=2024, df=df, fesr_col="FESR", fesr_is_string=False
    )


SCHOOL_ERA_HANDLERS = {
    "era_2017": _school_era_2017,
    "era_2018": _school_era_2018,
    "era_2019": _school_era_2019,
    "era_2020": _school_era_2020,
    "era_2021": _school_era_2021,
    "era_2022": _school_era_2022,
    "era_2023": _school_era_2023,
    "era_2024": _school_era_2024,
}


def _transform_school_file(
    path: Path, manifest: TransformManifest
) -> list[pl.DataFrame]:
    """Read one school workbook, detect its era, and transform it."""
    df, loss = read_bronze_file(path, return_loss=True)

    filename_year = extract_year_from_filename(path.name)
    if filename_year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")
    manifest.record_read_loss(
        filename_year, path.name, loss["raw_rows"], loss["parsed_rows"]
    )

    era = detect_era_by_columns(df, SCHOOL_ERA_SIGNATURES)
    if era is None:
        raise ValueError(
            f"{path.name}: no school era signature matched columns {df.columns}"
        )
    if SCHOOL_ERA_REPORT_YEAR[era] != filename_year:
        raise ValueError(
            f"{path.name}: filename year {filename_year} but column signature "
            f"matched {era} — investigate before ingesting"
        )

    manifest.record_file(path, filename_year, era, df.height, df.columns)

    if df.height == 0:
        logger.warning("%s: bronze file is empty, skipping", path.name)
        return []

    logger.info(
        "Processing %s as school/%s (report year %d, %d rows)",
        path.name,
        era,
        filename_year,
        df.height,
    )
    return SCHOOL_ERA_HANDLERS[era](df, manifest)


def _merge_school_overlaps(
    combined: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Collapse duplicate (year, district, school) school rows column-wise.

    Sort duplicates by `_report_year` ASCENDING and take each column's first
    non-null value, so the earliest (Y-named, canonical) publication wins and
    later rolling-window republications only fill gaps.
    """
    key_cols = ["year", "district_code", "school_code"]
    merge_cols = [c for c in STANDARD_COLUMNS if c not in (*key_cols, "_report_year")]

    pre = dict(combined.group_by("year").len().iter_rows())
    combined = combined.sort(key_cols + ["_report_year"])
    merged = combined.group_by(key_cols).agg(
        [pl.col(c).drop_nulls().first().alias(c) for c in merge_cols]
    )
    post = dict(merged.group_by("year").len().iter_rows())
    total_merged = 0
    for year in sorted(pre):
        removed = pre[year] - post.get(year, 0)
        if removed > 0:
            manifest.record_filtered(
                year, removed, "school_fiscal_year_overlap_merged_first_non_null"
            )
            total_merged += removed
    logger.info(
        "School fiscal-year overlap merge: %s -> %s rows (%s collapsed)",
        f"{combined.height:,}",
        f"{merged.height:,}",
        f"{total_merged:,}",
    )
    return merged.select([c for c in STANDARD_COLUMNS if c != "_report_year"])


# =============================================================================
# Per-file dispatch (route by filename family infix)
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> list[pl.DataFrame]:
    """Dispatch one bronze file to the district or school family transform.

    The merged bronze dir holds both download families; the ``_fesr_district_`` /
    ``_fesr_school_`` infix in the filename selects the per-family reader + era
    logic. Anything else is an unrecognized file and must stop the pipeline.
    """
    name = path.name
    if "_fesr_district_" in name:
        return _transform_district_file(path, manifest)
    if "_fesr_school_" in name:
        return _transform_school_file(path, manifest)
    raise ValueError(
        f"{name}: cannot route — filename carries neither '_fesr_district_' "
        f"nor '_fesr_school_' family infix"
    )


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for the merged FESR topic."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file from BOTH families, tagging each
    # frame's family so the two per-family overlap merges run independently
    # (district keys on district_code; school keys on district+school).
    extended_cols = STANDARD_COLUMNS + ["_report_year"]
    extended_types = {**TARGET_TYPES, "_report_year": pl.Int32}

    district_frames: list[pl.DataFrame] = []
    school_frames: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR):
        is_district = "_fesr_district_" in path.name
        for frame in transform_file(path, manifest):
            if frame.height == 0:
                continue
            manifest.record_bronze(int(frame["year"].head(1).item()), frame.height)
            (district_frames if is_district else school_frames).append(frame)
    if not district_frames and not school_frames:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Per-family harmonize + concat + within-publication collision guard +
    # the family-specific overlap merge. Both families harmonize to the SAME
    # unioned schema (each emits the other family's columns as typed NULLs).
    merged_parts: list[pl.DataFrame] = []

    if district_frames:
        district_frames = harmonize_columns(
            district_frames, extended_cols, extended_types
        )
        district = pl.concat(district_frames)
        logger.info("District: combined %d rows (pre-merge)", district.height)
        assert_no_natural_key_collisions(
            district,
            natural_keys=NATURAL_KEYS + ["_report_year"],
            metric_cols=METRIC_COLUMNS,
            label="district within single publication",
        )
        district = _merge_district_overlaps(district, manifest)
        merged_parts.append(district)

    if school_frames:
        school_frames = harmonize_columns(school_frames, extended_cols, extended_types)
        school = pl.concat(school_frames, how="vertical")
        logger.info("School: combined %d rows (pre-merge)", school.height)
        assert_no_natural_key_collisions(
            school,
            natural_keys=NATURAL_KEYS + ["_report_year"],
            metric_cols=METRIC_COLUMNS,
            label="school per-publication",
        )
        school = _merge_school_overlaps(school, manifest)
        # Drop fully-null school fact rows (rolling-window files list schools
        # that did not exist in earlier fiscal years of the window).
        fact_cols = METRIC_COLUMNS + ["is_non_compliant"]
        null_rows = school.filter(
            ~pl.any_horizontal([pl.col(c).is_not_null() for c in fact_cols])
        )
        if null_rows.height:
            for year, n in sorted(null_rows.group_by("year").len().iter_rows()):
                manifest.record_filtered(
                    year, n, "all_null_fact_row_dropped_school_absent_from_fiscal_year"
                )
            logger.info(
                "Dropped %s fully-null school fact rows", f"{null_rows.height:,}"
            )
            school = school.filter(
                pl.any_horizontal([pl.col(c).is_not_null() for c in fact_cols])
            )
        merged_parts.append(school)

    # 3. Union the two levels into one fact table. detail_level is part of the
    # natural key and the two families share no (year, district, school) keys
    # (every school row has a non-NULL school_code; every district row NULL),
    # so the union never collides across levels.
    combined = pl.concat(merged_parts) if len(merged_parts) > 1 else merged_parts[0]
    combined = combined.select(STANDARD_COLUMNS)
    logger.info("Unioned %d rows across both detail levels", combined.height)

    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break (safety net only): the per-family merges already guarantee one
    # row per natural key; prefer the row with reported spending.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code"],
        district_keys=["year", "district_code"],
        state_keys=["year"],
        sort_col="per_pupil_expenditure",
    )

    # 4. Geography nulling (shared domain rules). school_code is already NULL on
    # district rows; both keys populated on school rows. No further §4b masks
    # here (district sentinel handled in _district_attach_rolling; school
    # placeholder-zero mask at the era seam; negatives preserved per §4b).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )
    _warn_negative_amounts(combined, "final gold")

    # Pre-export sanity. Structural NULL patterns (level-specific columns NULL
    # on the other level, rolling metrics only on report years, program pause)
    # are expected to trip the spike detector — logged for reviewer cross-check.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning(
            "NULL-rate spikes (expected structural patterns — see module "
            "docstring): %s",
            spike_result.details,
        )
    validate_output(
        combined, required_non_null=["year", "detail_level", "district_code"]
    )

    # 5. Manifest stats on the FINAL DataFrame, then export to districts /
    # schools parquet by detail level.
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(combined, GOLD_DIR, STANDARD_COLUMNS)
    manifest.write(GOLD_DIR)

    # 6. Contract + README from the in-code column declaration. detail_levels /
    # default_detail are auto-discovered from the gold layout (schools/districts
    # -> default schools).
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

    # 7. ALWAYS LAST: validate the gold just written against the contract just
    # emitted. Raises GoldValidationError -> non-zero exit.
    run_topic_validation(GOLD_DIR)


def _emit_contract_and_readme(year_range: tuple[int, int]) -> None:
    """Emit the ODCS contract and gold README via ``write_data_dictionary``.

    The column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level``. Quality checks discriminate detail level by the
    geography-key NULL pattern (detail_level is implicit in the parquet
    filename and absent from the unioned validation view).
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Georgia Office of Student Achievement (GOSA) Financial Efficiency "
            "Star Rating (FESR) dataset at two detail levels in one fact "
            "table: district (one row per traditional Georgia school system, "
            "FY2014-FY2024) and school (one row per school, FY2017-FY2024). "
            "Reports per-pupil expenditure (PPE) inputs — total, federal, and "
            "state/local — full-time-equivalent K-12 enrollment, a CCRPI-"
            "derived annual Single Score, and the FESR star rating (0.5-5.0 in "
            "0.5 increments). District rows additionally carry the federal vs "
            "state/local split of total expenditures, three-year rolling PPE "
            "and Single Score averages, and a PPE percentile rank; school rows "
            "additionally carry the pre-allocation included/excluded "
            "expenditure split and the school's share of district enrollment. "
            "Coverage in tidy long form, one row per (district[, school], "
            "fiscal year). FESR and the rolling metrics are populated only on "
            "the fiscal year each publishing report treats as its newest year "
            "(FY2016-FY2019, FY2024 for districts; FY2017-FY2019, FY2024 for "
            "schools); GOSA paused the program 2020-2023. Merges the formerly "
            "separate financial_efficiency_star_rating_fesr_district and "
            "financial_efficiency_star_rating_fesr_school topics."
        ),
        title="Financial Efficiency Star Rating (FESR)",
        summary=(
            "Per-pupil spending, CCRPI scores, and 0.5-5 financial efficiency "
            "star ratings for Georgia school districts and schools, 2014-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Fiscal year the row's PPE inputs refer to (e.g. FY2024 = "
                    "2023-24 school year). Differs from the bronze filename "
                    "year for back-window rows: each rolling report covers up "
                    "to 3 fiscal years, but gold keys every row by the actual "
                    "fiscal year."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "nullable": False,
                "example": "657",
                "description": (
                    "GOSA district/system code (FK to districts dimension), "
                    "zero-padded to 3 digits (7-digit codes are charter "
                    "authorizers, school rows only). District-detail rows cover "
                    "the 180 traditional school systems (codes 601-793); "
                    "school-detail rows additionally include charter "
                    "authorizer codes. Populated on every row."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0103",
                "null_meaning": (
                    "Populated only on school-detail rows; NULL on every "
                    "district-detail row (the district level has no school "
                    "code). The geography-key NULL pattern is how detail level "
                    "is read from the unioned table."
                ),
                "description": (
                    "GOSA school code, zero-padded to 4 characters (composite "
                    "FK to schools dimension with district_code; not globally "
                    "unique on its own). Populated on school rows only — "
                    "district aggregate rows carry NULL."
                ),
            },
            {
                "name": "total_expenditures",
                "type": "float64",
                "unit": "currency",
                "example": 8125000.0,
                "description": (
                    "Total expenditures for the fiscal year (nominal dollars, "
                    "not inflation-adjusted). For DISTRICT rows this is the "
                    "district's total included expenditures (= "
                    "federal_expenditures + state_local_expenditures within "
                    "$1, enforced by a quality check). For SCHOOL rows this is "
                    "the per-school total — included expenditures plus the "
                    "school's allocated share of district central costs (= "
                    "total_federal_expenditures + total_state_local_"
                    "expenditures within $10; from FY22 also folds in "
                    "Allocated CCA and Alternative Program costs, so FY22+ "
                    "school totals are not strictly comparable to FY17-FY21). "
                    "per_pupil_expenditure = total_expenditures / "
                    "fte_enrollment at both levels."
                ),
            },
            {
                "name": "fte_enrollment",
                "type": "int64",
                "unit": "count",
                "metric_component": "denominator",
                "example": 984,
                "description": (
                    "Full-time-equivalent K-12 enrollment, the denominator of "
                    "per_pupil_expenditure (per_pupil_expenditure = "
                    "total_expenditures / fte_enrollment within rounding at "
                    "both detail levels, enforced by a quality check)."
                ),
            },
            {
                "name": "per_pupil_expenditure",
                "type": "float64",
                "unit": "currency",
                "key_metric": True,
                "label": "Per-Pupil Expenditure",
                "example": 9349.52,
                "short_description": (
                    "Total dollars spent per student for the fiscal year "
                    "(nominal, not inflation-adjusted)."
                ),
                "description": (
                    "Per-pupil expenditure for the fiscal year (nominal "
                    "dollars) = total_expenditures / fte_enrollment, as "
                    "published (rounded to cents by the source). A few Atlanta "
                    "(district 660) school rows in FY21/FY22 are negative — "
                    "faithful GOSA restatements preserved per §4b, not errors."
                ),
            },
            {
                "name": "federal_per_pupil_expenditure",
                "type": "float64",
                "unit": "currency",
                "example": 578.3,
                "null_meaning": (
                    "NULL for district FY2014 (the 2016 workbook, the only "
                    "source covering FY14, published no federal/state-local "
                    "breakdown)."
                ),
                "description": (
                    "Federal portion of per_pupil_expenditure (nominal "
                    "dollars). federal_per_pupil_expenditure + "
                    "state_local_per_pupil_expenditure = "
                    "per_pupil_expenditure within rounding (enforced by a "
                    "quality check). NULL for district FY2014."
                ),
            },
            {
                "name": "state_local_per_pupil_expenditure",
                "type": "float64",
                "unit": "currency",
                "example": 8771.22,
                "null_meaning": "NULL for district FY2014 (no breakdown published).",
                "description": (
                    "State + local portion of per_pupil_expenditure (nominal "
                    "dollars). NULL for district FY2014."
                ),
            },
            {
                "name": "federal_expenditures",
                "type": "float64",
                "unit": "currency",
                "example": 5542000.0,
                "null_meaning": (
                    "Populated on DISTRICT rows only (NULL on every school "
                    "row — schools instead publish total_federal_expenditures, "
                    "the same federal share of total_expenditures, plus the "
                    "distinct included_federal_expenditures pre-allocation "
                    "split). Also NULL for district FY2014, whose only source "
                    "published totals without a breakdown."
                ),
                "description": (
                    "Federal portion of the district's total_expenditures "
                    "(nominal dollars). District-detail rows only. The "
                    "school-level analogue of this quantity is "
                    "total_federal_expenditures (both split the shared "
                    "total_expenditures column); they are kept as separate "
                    "columns because the school download names them "
                    "differently and additionally publishes the "
                    "pre-allocation included_* split, which districts do not."
                ),
            },
            {
                "name": "state_local_expenditures",
                "type": "float64",
                "unit": "currency",
                "example": 79501000.0,
                "null_meaning": (
                    "Populated on DISTRICT rows only (NULL on every school "
                    "row — schools publish total_state_local_expenditures "
                    "instead). Also NULL for district FY2014 (no breakdown)."
                ),
                "description": (
                    "State + local portion of the district's "
                    "total_expenditures (nominal dollars). District-detail "
                    "rows only; the school-level analogue is "
                    "total_state_local_expenditures."
                ),
            },
            {
                "name": "included_expenditures",
                "type": "float64",
                "unit": "currency",
                "example": 7413403.4,
                "null_meaning": (
                    "Populated on SCHOOL rows only (NULL on every district "
                    "row — the district download has no pre-allocation "
                    "included split; a district's total_expenditures IS its "
                    "included total)."
                ),
                "description": (
                    "Total included expenditures for the school (nominal "
                    "dollars), BEFORE allocation of district central costs — "
                    "the school's total_expenditures equals "
                    "included_expenditures plus its allocated central-cost "
                    "share. School-detail rows only. Placeholder $0 values on "
                    "unreported/non-compliant FY17-FY18 rows are NULLed per "
                    "§4b (see limitations)."
                ),
            },
            {
                "name": "included_federal_expenditures",
                "type": "float64",
                "unit": "currency",
                "example": 456789.0,
                "null_meaning": (
                    "Populated on SCHOOL rows only (NULL on district rows)."
                ),
                "description": (
                    "Federal portion of the school's included_expenditures "
                    "(nominal dollars). included_federal_expenditures + "
                    "included_state_local_expenditures = included_expenditures "
                    "(exact in the canonical bronze blocks; enforced by a "
                    "quality check). School-detail rows only. FY17-FY18 "
                    "placeholder $0 values NULLed per §4b."
                ),
            },
            {
                "name": "included_state_local_expenditures",
                "type": "float64",
                "unit": "currency",
                "example": 6956614.4,
                "null_meaning": (
                    "Populated on SCHOOL rows only (NULL on district rows)."
                ),
                "description": (
                    "State + local portion of the school's "
                    "included_expenditures (nominal dollars). School-detail "
                    "rows only. FY17-FY18 placeholder $0 values NULLed per §4b."
                ),
            },
            {
                "name": "excluded_expenditures",
                "type": "float64",
                "unit": "currency",
                "example": 120000.0,
                "null_meaning": (
                    "Populated on SCHOOL rows only (NULL on district rows)."
                ),
                "description": (
                    "Expenditures excluded from the PPE computation (nominal "
                    "dollars) per the FESR methodology. NOT a component of "
                    "total_expenditures (totals = included + allocated central "
                    "costs). School-detail rows only. A few rows per year carry "
                    "negative values — faithful GOSA restatements preserved "
                    "per §4b. FY17-FY18 placeholder $0 values NULLed per §4b."
                ),
            },
            {
                "name": "total_federal_expenditures",
                "type": "float64",
                "unit": "currency",
                "example": 500000.0,
                "null_meaning": (
                    "Populated on SCHOOL rows only (NULL on district rows — "
                    "the district analogue is federal_expenditures)."
                ),
                "description": (
                    "Federal portion of the school's total_expenditures "
                    "(post-allocation; nominal dollars). The school-level "
                    "analogue of the district's federal_expenditures (both "
                    "split the shared total_expenditures). School-detail rows "
                    "only. FY17-FY18 placeholder $0 values NULLed per §4b."
                ),
            },
            {
                "name": "total_state_local_expenditures",
                "type": "float64",
                "unit": "currency",
                "example": 7625000.0,
                "null_meaning": (
                    "Populated on SCHOOL rows only (NULL on district rows — "
                    "the district analogue is state_local_expenditures)."
                ),
                "description": (
                    "State + local portion of the school's total_expenditures "
                    "(post-allocation; nominal dollars). School-detail rows "
                    "only; the district analogue is state_local_expenditures. "
                    "FY17-FY18 placeholder $0 values NULLed per §4b."
                ),
            },
            {
                "name": "pct_of_district_enrollment",
                "type": "float64",
                "unit": "proportion",
                "example": 0.2912,
                "null_meaning": (
                    "Populated on SCHOOL rows only (NULL on district rows). "
                    "Also NULL for charter/excluded schools outside the "
                    "district rollup."
                ),
                "description": (
                    "The school's share of its district's total enrollment, "
                    "0-1 decimal (0.2912 = 29.12%%), used by the FESR "
                    "methodology to allocate district central costs. "
                    "School-detail rows only. Caveat: within-district sums are "
                    "not a strict partition — they exceed 1.0 in 55 "
                    "district-years (up to 1.82), faithful to bronze."
                ),
            },
            {
                "name": "ccrpi_single_score",
                "type": "float64",
                "unit": "score",
                "example": 76.2,
                "null_meaning": (
                    "NULL for FY2020-FY2022 (CCRPI paused). For schools, also "
                    "NULL for FY17/FY18 schools absent from the 2019 file (the "
                    "only file carrying their score). For districts, populated "
                    "on every fiscal year a workbook covers except the pause."
                ),
                "description": (
                    "CCRPI-derived annual Single Score, preserved as published "
                    "(a GOSA score, not a rate). Typically a 0-100 scale; FY17 "
                    "school scores may exceed 100 due to early-CCRPI "
                    "challenge-point scoring (29 rows reach ~108.2), so no "
                    "upper bound is enforced (a negative score is impossible — "
                    "enforced). NULL for FY2020-FY2022 (program pause)."
                ),
            },
            {
                "name": "per_pupil_expenditure_three_year_avg",
                "type": "float64",
                "unit": "currency",
                "example": 9024.04,
                "null_meaning": (
                    "Populated on DISTRICT report-year rows only (FY2016-"
                    "FY2019, FY2024); NULL on every school row and on "
                    "non-report-year district rows. Schools do not publish "
                    "rolling averages (derivable from yearly values)."
                ),
                "description": (
                    "Three-year rolling average of per_pupil_expenditure "
                    "(nominal dollars), attributed to the publishing district "
                    "report's newest fiscal year (FY2016, FY2017, FY2018, "
                    "FY2019, FY2024) and NULL elsewhere. FY2024's window is "
                    "non-contiguous (FY19+FY23+FY24). District-detail rows "
                    "only. C-1 rename of the former ppe_three_year_avg."
                ),
            },
            {
                "name": "ccrpi_three_year_avg",
                "type": "float64",
                "unit": "score",
                "value_min": 0,
                "value_max": 100,
                "example": 71.2,
                "null_meaning": (
                    "Populated on DISTRICT report-year rows only (FY2016-"
                    "FY2019, FY2024); NULL on every school row and on "
                    "non-report-year district rows."
                ),
                "description": (
                    "Three-year rolling average of ccrpi_single_score (0-100 "
                    "scale), attributed to district report-year rows only "
                    "(see per_pupil_expenditure_three_year_avg). "
                    "District-detail rows only."
                ),
            },
            {
                "name": "per_pupil_expenditure_percentile",
                "type": "int64",
                "unit": "percentile",
                "example": 76,
                "null_meaning": (
                    "Populated on DISTRICT report-year rows only (FY2016-"
                    "FY2019, FY2024); NULL on every school row and on "
                    "non-report-year district rows."
                ),
                "description": (
                    "Percentile rank (1-100 integer) of the district's "
                    "per_pupil_expenditure_three_year_avg among all 180 "
                    "Georgia districts in the same report — population-based, "
                    "not a national percentile. Higher = more spending per "
                    "pupil. District report-year rows only. C-1 rename of the "
                    "former ppe_percentile."
                ),
            },
            {
                "name": "fesr_star_rating",
                "type": "float64",
                "unit": "rating",
                "value_min": 0.5,
                "value_max": 5,
                "example": 3.5,
                "null_meaning": (
                    "Populated only on the fiscal year each publishing report "
                    "treats as its newest year (district: FY2016-FY2019, "
                    "FY2024; school: FY2017-FY2019, FY2024); NULL during the "
                    "FY2020-FY2023 program pause, off report years, and where "
                    "the publisher issued a 'Non-Compliant' status or no "
                    "rating instead (is_non_compliant=true or, for schools, "
                    "the `.` sentinel)."
                ),
                "description": (
                    "Financial Efficiency Star Rating in 0.5 increments. "
                    "Districts: observed 1.0-5.0; schools: 0.5-5.0 (the value "
                    "range spans both levels). Populated only on report-year "
                    "rows; half-steps enforced by a quality check. Bronze "
                    "stores it as Float64 in early files and as strings in "
                    "later files; non-numeric publisher statuses (district "
                    "'Non-Compliant'; school '.', 'Non-Compliant[ in 20YY]') "
                    "are NULLed here, with non-compliance preserved via "
                    "is_non_compliant."
                ),
            },
            {
                "name": "is_non_compliant",
                "type": "boolean",
                "exclude_from_grain": True,
                "example": False,
                "null_meaning": (
                    "NULL wherever no FESR compliance outcome was published — "
                    "all non-report-year rows, the FY2020-FY2023 pause, and "
                    "the numeric-FESR school files (2019/2024) that publish "
                    "ratings without a flag."
                ),
                "short_description": (
                    "True when the district or school was flagged "
                    "non-compliant with financial reporting (no star rating "
                    "issued); false when a rating was published."
                ),
                "description": (
                    "FESR publication outcome: true when the source flags the "
                    "entity non-compliant (no star rating exists, so "
                    "fesr_star_rating is NULL — enforced by a quality check); "
                    "false when a numeric rating was published; NULL when no "
                    "FESR outcome was published. Districts: the 2018 report's "
                    "'Non-Compliant' status (Talbot County 730). Schools: "
                    "FY17/FY18 string sentinels, the FY19 note (Cirrus "
                    "Charter, 7830611/0611), and the FY21 PPE sentinel "
                    "(7830629/0629)."
                ),
            },
        ],
        source="Governor's Office of Student Achievement (GOSA)",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        suppressed_to_null=False,
        limitations=(
            "Two detail levels (district, school) in one fact table, split by "
            "parquet filename; school_code is NULL on district rows. Detail "
            "level is read from the geography-key NULL pattern. The district "
            "level covers FY2014-FY2024 (180 traditional systems, codes "
            "601-793, no charters/RESAs/state agencies); the school level "
            "covers FY2017-FY2024 (all schools, including charter authorizers). "
            "School-level and district-level rows come from two independent "
            "GOSA downloads whose K-12 bases need not reconcile, so school "
            "rows are NOT guaranteed to sum to their district row. Level-"
            "specific columns are NULL on the other level: federal_"
            "expenditures / state_local_expenditures and the three rolling/"
            "percentile metrics are district-only; included_* / excluded_"
            "expenditures / total_federal_expenditures / total_state_local_"
            "expenditures / pct_of_district_enrollment are school-only. The "
            "district federal_expenditures and the school "
            "total_federal_expenditures are the same federal share of "
            "total_expenditures but are kept as separate columns (different "
            "source naming; schools also publish the distinct pre-allocation "
            "included_* split). fesr_star_rating and the rolling/percentile "
            "metrics are populated only on the report-year row of each "
            "rolling-window publication; GOSA paused the program FY2020-FY2023 "
            "(those years carry only PPE inputs), and ccrpi_single_score is "
            "additionally NULL for FY2020-FY2022 (CCRPI paused). District "
            "federal/state-local breakdowns are NULL for FY2014 (the only "
            "source covering FY14 published totals only). FY2022 methodology "
            "change: from FY22 school total_expenditures (and "
            "per_pupil_expenditure) additionally include Allocated CCA and "
            "Alternative Program costs, so FY22+ school totals are not "
            "strictly comparable to FY17-FY21. Placeholder $0 school "
            "expenditure amounts on unreported/non-compliant FY17-FY18 rows "
            "are NULLed per §4b (see _transform_manifest.json masked_values). "
            "A small number of district 660 (Atlanta) school rows carry "
            "negative expenditure / per-pupil values — faithful GOSA "
            "restatements preserved as-is. Currency is nominal dollars (not "
            "inflation-adjusted). No cell-level small-cell suppression exists "
            "in this source; NULLs are structural or §4b masks, never "
            "suppression."
        ),
        notes=[
            (
                "Two detail levels in one fact table: district (one row per "
                "system, school_code NULL, FY2014-FY2024) and school (one row "
                "per school, both keys populated, FY2017-FY2024). "
                "districts.parquet and schools.parquet under each year "
                "partition; detail_level is implicit in the filename and not a "
                "stored column. Merges the formerly separate "
                "financial_efficiency_star_rating_fesr_district and "
                "financial_efficiency_star_rating_fesr_school topics."
            ),
            (
                "Shared columns (same name + verified-identical derivation, "
                "populated for both levels): total_expenditures, "
                "fte_enrollment, per_pupil_expenditure, "
                "federal_per_pupil_expenditure, "
                "state_local_per_pupil_expenditure, ccrpi_single_score, "
                "fesr_star_rating, is_non_compliant. Verified in FY2018 gold: "
                "per_pupil_expenditure = total_expenditures / fte_enrollment "
                "to $0.005 in both families."
            ),
            (
                "Federal/state-local split kept separate, not unified: the "
                "district's federal_expenditures/state_local_expenditures and "
                "the school's total_federal_expenditures/"
                "total_state_local_expenditures are the same federal/SL share "
                "of the shared total_expenditures (each reconciles to ~$0), "
                "but are kept as distinct columns because the two downloads "
                "name them differently and the school family additionally "
                "publishes the pre-allocation included_* split (which divides "
                "included_expenditures, not total — included/fte does NOT "
                "equal PPE, gap ~$8,493), a split districts do not have. "
                "Unifying would assert a district included_* analog that does "
                "not exist."
            ),
            (
                "Rolling metrics (per_pupil_expenditure_three_year_avg, "
                "ccrpi_three_year_avg, per_pupil_expenditure_percentile) are "
                "district-only and renamed per C-1 from ppe_three_year_avg / "
                "ppe_percentile. Schools do not publish rolling averages "
                "(derivable from yearly values)."
            ),
            (
                "FESR is attributed to the fiscal year each publishing report "
                "treats as its newest year (district: FY16-FY19, FY24; "
                "school: FY17-FY19, FY24). GOSA paused the program FY20-FY23. "
                "The 2024 report revived the rating with a non-contiguous "
                "FY19+FY23+FY24 window."
            ),
            (
                "Fiscal-year overlaps are resolved per family before the "
                "union: the district family uses a column-wise merge keeping "
                "the financial block atomic (federal + state_local = total "
                "additive); the school family uses a first-non-null merge with "
                "the canonical Y-named publication winning. The two families "
                "share no (year, district_code, school_code) keys, so the "
                "union never collides across levels."
            ),
            (
                "FESR data type and sentinels: districts store FESR numeric in "
                "2016-2018 and as strings in 2019/2024, with the one "
                "'Non-Compliant' status in 2018 (Talbot 730). Schools store "
                "it as strings in 2017/2018 (sentinels '.', 'Non-Compliant', "
                "'Non-Compliant in 20YY') and numeric in 2019/2024. Sentinels "
                "land as NULL ratings; non-compliance is preserved via "
                "is_non_compliant."
            ),
            (
                "§4b masking (school family): placeholder $0 expenditure "
                "amounts on unreported/non-compliant FY17-FY18 rows are NULLed "
                "so fake zero-dollar facts are not served; counts per column "
                "and year are in the manifest's masked_values. Negative "
                "expenditure / per-pupil values (Atlanta district 660 school "
                "rows in FY21/FY22; scattered negative excluded amounts) are "
                "faithful GOSA restatements preserved per §4b."
            ),
            (
                "Currency is nominal dollars (not inflation-adjusted). All "
                "metrics preserved verbatim from the publisher — no "
                "re-computation. FESR methodology evolved across years; "
                "year-over-year comparisons should account for GOSA-documented "
                "methodology drift."
            ),
            (
                "No demographic column — the source publishes no race, gender, "
                "or economic breakdowns in any era of either family."
            ),
        ],
        quality_checks=_quality_checks(),
    )


def _quality_checks() -> list[dict]:
    """Merged cross-column invariants from BOTH source transforms (§15b).

    Level-specific checks discriminate detail by the geography-key NULL pattern
    (school ⟺ school_code IS NOT NULL; district ⟺ school_code IS NULL). Range
    checks (unit-derived) are emitted automatically and not duplicated here.
    """
    return [
        # --- shared rating outcome (both levels) ---
        {
            "name": "fesr_star_rating_half_step",
            "description": (
                "fesr_star_rating is a half-step rating: 2x the value is a "
                "whole number (0.5 increments)."
            ),
            "dimension": "accuracy",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE fesr_star_rating IS NOT "
                "NULL AND (fesr_star_rating * 2) != ROUND(fesr_star_rating * 2)"
            ),
            "mustBe": 0,
        },
        {
            "name": "non_compliant_implies_no_rating",
            "description": (
                "Co-null rule: is_non_compliant = TRUE implies "
                "fesr_star_rating IS NULL (a non-compliant outcome replaces "
                "the star rating) at both detail levels."
            ),
            "dimension": "consistency",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE is_non_compliant = TRUE "
                "AND fesr_star_rating IS NOT NULL"
            ),
            "mustBe": 0,
        },
        {
            "name": "fesr_only_in_publication_years",
            "description": (
                "Structural fact: FESR is published only in FY2016-FY2019 and "
                "FY2024 (program paused FY2020-FY2023). The district level "
                "starts FY2016, the school level FY2017; no rating exists "
                "outside these years at either level."
            ),
            "dimension": "consistency",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE fesr_star_rating IS NOT "
                "NULL AND year NOT IN (2016, 2017, 2018, 2019, 2024)"
            ),
            "mustBe": 0,
        },
        # --- shared per-pupil identity (both levels) ---
        {
            "name": "ppe_consistent_with_total_over_fte",
            "description": (
                "per_pupil_expenditure = total_expenditures / fte_enrollment "
                "within $0.05 wherever all three are published and enrollment "
                "is positive, at BOTH detail levels (source rounds PPE to "
                "cents; max observed deviation ~$0.021)."
            ),
            "dimension": "consistency",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE per_pupil_expenditure IS "
                "NOT NULL AND total_expenditures IS NOT NULL AND "
                "fte_enrollment IS NOT NULL AND fte_enrollment > 0 AND "
                "ABS(per_pupil_expenditure - total_expenditures / "
                "fte_enrollment) > 0.05"
            ),
            "mustBe": 0,
        },
        {
            "name": "per_pupil_components_reconcile",
            "description": (
                "federal_per_pupil_expenditure + "
                "state_local_per_pupil_expenditure = per_pupil_expenditure "
                "within $0.20 wherever all three are published, at both detail "
                "levels (canonical blocks reconcile within ~$0.016; the "
                "loosest rows are two FY17 schools from the 2019 file's "
                "re-keyed back-window at $0.170)."
            ),
            "dimension": "consistency",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE per_pupil_expenditure IS "
                "NOT NULL AND federal_per_pupil_expenditure IS NOT NULL AND "
                "state_local_per_pupil_expenditure IS NOT NULL AND "
                "ABS(per_pupil_expenditure - (federal_per_pupil_expenditure + "
                "state_local_per_pupil_expenditure)) > 0.20"
            ),
            "mustBe": 0,
        },
        # --- district-only: federal/SL split reconciles with total ---
        {
            "name": "district_expenditure_components_reconcile",
            "description": (
                "District rows (school_code IS NULL): federal_expenditures + "
                "state_local_expenditures = total_expenditures within $1 "
                "wherever the breakdown exists (exact to the cent in every "
                "gold-source block)."
            ),
            "dimension": "consistency",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE school_code IS NULL AND "
                "total_expenditures IS NOT NULL AND federal_expenditures IS "
                "NOT NULL AND state_local_expenditures IS NOT NULL AND "
                "ABS(federal_expenditures + state_local_expenditures - "
                "total_expenditures) > 1.0"
            ),
            "mustBe": 0,
        },
        # --- school-only: included split + total split reconcile ---
        {
            "name": "school_included_components_reconcile",
            "description": (
                "School rows (school_code IS NOT NULL): "
                "included_federal_expenditures + "
                "included_state_local_expenditures = included_expenditures "
                "within $1 wherever all three are published (exact in the "
                "canonical bronze blocks; gold max gap $0.00)."
            ),
            "dimension": "consistency",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE school_code IS NOT NULL "
                "AND included_expenditures IS NOT NULL AND "
                "included_federal_expenditures IS NOT NULL AND "
                "included_state_local_expenditures IS NOT NULL AND "
                "ABS(included_expenditures - (included_federal_expenditures + "
                "included_state_local_expenditures)) > 1.0"
            ),
            "mustBe": 0,
        },
        {
            "name": "school_total_components_reconcile",
            "description": (
                "School rows: total_federal_expenditures + "
                "total_state_local_expenditures = total_expenditures within "
                "$10 wherever all three are published (GOSA rounding noise; "
                "gold max gap $7.00, FY20)."
            ),
            "dimension": "consistency",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE school_code IS NOT NULL "
                "AND total_expenditures IS NOT NULL AND "
                "total_federal_expenditures IS NOT NULL AND "
                "total_state_local_expenditures IS NOT NULL AND "
                "ABS(total_expenditures - (total_federal_expenditures + "
                "total_state_local_expenditures)) > 10.0"
            ),
            "mustBe": 0,
        },
        # --- district-only: rolling metrics only on report years ---
        {
            "name": "district_rolling_metrics_only_on_report_years",
            "description": (
                "District rolling/percentile metrics "
                "(per_pupil_expenditure_three_year_avg, ccrpi_three_year_avg, "
                "per_pupil_expenditure_percentile) exist only on district "
                "report-year rows (FY2016-FY2019, FY2024) and are NULL on "
                "every school row and every other district fiscal year."
            ),
            "dimension": "consistency",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE "
                "(per_pupil_expenditure_three_year_avg IS NOT NULL OR "
                "ccrpi_three_year_avg IS NOT NULL OR "
                "per_pupil_expenditure_percentile IS NOT NULL) AND "
                "(school_code IS NOT NULL OR year NOT IN "
                "(2016, 2017, 2018, 2019, 2024))"
            ),
            "mustBe": 0,
        },
        {
            "name": "district_rating_implies_window_metrics_present",
            "description": (
                "On district rows, a published star rating is computed from "
                "the rolling window, so a non-NULL fesr_star_rating implies "
                "per_pupil_expenditure_three_year_avg, ccrpi_three_year_avg, "
                "and per_pupil_expenditure_percentile are all populated on the "
                "same row."
            ),
            "dimension": "completeness",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE school_code IS NULL AND "
                "fesr_star_rating IS NOT NULL AND "
                "(per_pupil_expenditure_three_year_avg IS NULL OR "
                "ccrpi_three_year_avg IS NULL OR "
                "per_pupil_expenditure_percentile IS NULL)"
            ),
            "mustBe": 0,
        },
        # --- level-specific column population (the merge invariant) ---
        {
            "name": "school_only_columns_null_on_district_rows",
            "description": (
                "School-only columns (included_*, excluded_expenditures, "
                "total_federal/state_local_expenditures, "
                "pct_of_district_enrollment) must be NULL on every district "
                "row (school_code IS NULL) — they have no district analog."
            ),
            "dimension": "consistency",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE school_code IS NULL AND "
                "(included_expenditures IS NOT NULL OR "
                "included_federal_expenditures IS NOT NULL OR "
                "included_state_local_expenditures IS NOT NULL OR "
                "excluded_expenditures IS NOT NULL OR "
                "total_federal_expenditures IS NOT NULL OR "
                "total_state_local_expenditures IS NOT NULL OR "
                "pct_of_district_enrollment IS NOT NULL)"
            ),
            "mustBe": 0,
        },
        {
            "name": "district_only_columns_null_on_school_rows",
            "description": (
                "District-only columns (federal_expenditures, "
                "state_local_expenditures, and the three rolling/percentile "
                "metrics) must be NULL on every school row "
                "(school_code IS NOT NULL)."
            ),
            "dimension": "consistency",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE school_code IS NOT NULL "
                "AND (federal_expenditures IS NOT NULL OR "
                "state_local_expenditures IS NOT NULL OR "
                "per_pupil_expenditure_three_year_avg IS NOT NULL OR "
                "ccrpi_three_year_avg IS NOT NULL OR "
                "per_pupil_expenditure_percentile IS NOT NULL)"
            ),
            "mustBe": 0,
        },
        # --- shared academic score floor ---
        {
            "name": "ccrpi_single_score_non_negative",
            "description": (
                "ccrpi_single_score is a 0-100-style score with no upper bound "
                "enforced (FY17 early-CCRPI challenge points reach ~108.2), "
                "but a negative score is impossible."
            ),
            "dimension": "accuracy",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE ccrpi_single_score IS NOT "
                "NULL AND ccrpi_single_score < 0"
            ),
            "mustBe": 0,
        },
        # --- geography-key shape (both levels) ---
        {
            "name": "district_code_never_null",
            "description": (
                "Every row (district or school) carries a populated "
                "district_code — this topic has no state-rollup rows."
            ),
            "dimension": "completeness",
            "query": "SELECT COUNT(*) FROM {object} WHERE district_code IS NULL",
            "mustBe": 0,
        },
        {
            "name": "district_code_length_3_or_7",
            "description": (
                "district_code is a 3-char county/city code or a 7-char "
                "charter-authorizer code — any other length means the ID "
                "formatting regressed."
            ),
            "dimension": "consistency",
            "query": (
                "SELECT COUNT(*) FROM {object} "
                "WHERE LENGTH(district_code) NOT IN (3, 7)"
            ),
            "mustBe": 0,
        },
        {
            "name": "school_code_length_4_when_present",
            "description": (
                "Where populated (school rows), school_code is zero-padded to "
                "exactly 4 characters, matching the schools dimension key."
            ),
            "dimension": "consistency",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE school_code IS NOT NULL "
                "AND LENGTH(school_code) <> 4"
            ),
            "mustBe": 0,
        },
        {
            "name": "district_universe_complete_per_year",
            "description": (
                "Every fiscal year carries exactly one district row for each "
                "of the 180 traditional districts (identical code universe in "
                "all 9 district bronze files). A different count means rows "
                "were dropped or a new entity appeared."
            ),
            "dimension": "completeness",
            "query": (
                "SELECT COUNT(*) FROM (SELECT year FROM {object} "
                "WHERE school_code IS NULL GROUP BY year "
                "HAVING COUNT(*) <> 180 OR COUNT(DISTINCT district_code) <> 180"
                ") AS bad_years"
            ),
            "mustBe": 0,
        },
    ]


if __name__ == "__main__":
    main()
