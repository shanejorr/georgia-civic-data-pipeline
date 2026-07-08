"""Transform bronze ccrpi_climate_star_rating files into gold fact tables.

Source: Georgia Insights (GaDOE). The bronze files publish two CCRPI (College
and Career Ready Performance Index) metrics at the school level, but this topic
carries only ONE of them to gold:

    1. School Climate Star Rating — ordinal 1-5 whole-star rating built from
       four equally weighted components (surveys, student discipline, safe /
       substance-free environment, school-wide attendance).
       Published 2014-2019 and 2024. THIS is the topic's sole metric.

The bronze also carries the CCRPI Single Score (the 0-100 composite
accountability score), but it is intentionally NOT published here (removed in
contract v2.0.0): it was stale — dropped from the 2024 release, so 2014-2019
only — and is fully duplicated by the `ccrpi_scoring_by_component` topic, whose
`ccrpi_single_score` column is a strict superset (more years — adds 2012-2013 —
plus district and state aggregates). The transform reads past the bronze column
and drops it.

Bronze: seven single-sheet xlsx/xls files (2014-2019 + 2024; 2020-2023 are
absent — Georgia paused CCRPI during COVID). Re-verified during authoring:

- **School-only.** No file carries an "ALL"/aggregate sentinel or a NULL in
  either ID column — every row is one school. The transform still guards the
  assumption: any aggregate sentinel in an ID column raises (a sentinel would
  mean district/state rows appeared and the school-only shape broke).
- **In-file year is authoritative.** Each file holds exactly one distinct
  `Year`/`School Year` value. Six filenames carry that same year; the 2014
  data ships in `CCRPI Score and School Climate Star Rating 04.14.15.xlsx`
  (an April 2015 publication date, no parseable 20XX year). The transform
  raises when a parseable filename year disagrees with the in-file year.
- **One byte-identical duplicate row** in the 2015 file (Murray County 705 /
  Spring Place Elementary School 1052, CCRPI 68.6, star 5 — twice). The
  collision guard tolerates it (identical metrics); dedup drops one copy and
  the drop is recorded via ``manifest.record_filtered``. No other duplicate
  keys exist source-wide. Documented in the structure doc's Corrections
  section.
- **No read loss.** All bronze reads are whole-sheet Excel loads via the
  shared ``read_bronze_file`` (single data sheet per file — no multi-sheet
  helper needed), so raw == parsed by construction;
  ``manifest.record_read_loss`` is still called with the loss dict for
  auditability (a structural no-op).
- **No §4b masks.** Star ratings are whole values in {1..5} in every file
  (0 out-of-scale values; the whole-star invariant is authored as a quality
  check).
- **`NA` markers, not blank cells.** Raw-cell inspection shows EVERY star
  rating NULL in EVERY year originates from a literal `NA` text marker — there
  are zero blank rating cells in any file (per-year `NA` counts: star rating
  17/28/35/11/42/42/60 for 2014-2019+2024). The markers mean "no rating
  published" (e.g., the 2018 DJJ Atlanta Youth Detention Center's star `NA` is
  a not-rated facility), not necessarily privacy suppression. The shared
  reader's SUPPRESSION_VALUES nulls them at read; strict=False casts catch
  residue.

No demographic breakdowns and no topic-specific categorical columns exist —
the `demographic` column is omitted per data-cleaning-standards §5 and no
``record_categorical`` calls are needed (nothing is recoded), so the
manifest's unmapped guard is trivially satisfied.

Natural key: (year, district_code, school_code) — one row per school per
year, detail level always "school" (only schools.parquet is written).
"""

import logging
from pathlib import Path

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

TOPIC = "ccrpi_climate_star_rating"
BRONZE_DIR = Path("data/bronze/education/georgiainsights/ccrpi_climate_star_rating")
GOLD_DIR = Path("data/gold/education/ccrpi_climate_star_rating")
SOURCE_URL = "https://georgiainsights.gadoe.org/data-downloads/"

# Era signatures, most specific first (first match wins). era_3's signature
# is a strict subset of era_2's, so era_2 MUST precede it — otherwise the
# 2019 file (which has CCRPI Single Score) would mis-route to era_3.
ERA_SIGNATURES: dict[str, list[str]] = {
    # 2014-2018 releases: `Year` column, both metrics.
    "era_1_year_both_metrics": [
        "Year",
        "CCRPI Single Score",
        "School Climate Star Rating",
    ],
    # 2019 release: `School Year` column, both metrics.
    "era_2_school_year_both_metrics": [
        "School Year",
        "CCRPI Single Score",
        "School Climate Star Rating",
    ],
    # 2024 release: `School Year` column, climate star rating only.
    "era_3_climate_only": ["School Year", "School Climate Star Rating"],
}

# Bronze -> gold renames shared by every era (the year column is normalized
# separately because its bronze name drifts: `Year` vs `School Year`).
# System Name / School Name are dimension attributes and never enter the
# fact table (education domain CLAUDE.md). The bronze `CCRPI Single Score`
# column is deliberately NOT renamed — it is left in place and dropped by the
# final select (see module docstring; it lives in ccrpi_scoring_by_component).
COLUMN_RENAME_BASE: dict[str, str] = {
    "System ID": "district_code",
    "School ID": "school_code",
    "School Climate Star Rating": "school_climate_star_rating",
}

# Aggregate-row sentinel that siblings' bronze uses in ID columns. This
# topic's bronze has none (re-verified) — its presence would invalidate the
# school-only shape, so it raises rather than being silently nulled.
AGGREGATE_SENTINEL = "ALL"

# Gold column order. `detail_level` is carried for the export splitter and
# dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "detail_level",
    "school_climate_star_rating",
]

# `school_climate_star_rating` is Float64 (not Int8) so the API exposes one
# star-rating type across topics — FESR star ratings take half-steps
# (data-cleaning-standards §3). CCRPI climate values are whole stars 1-5;
# 1.0-5.0 loses nothing. The star rating is ordinal, not scaled to 0-1
# (education CLAUDE.md "Percentage Scale Exceptions").
TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "detail_level": pl.Utf8,
    "school_climate_star_rating": pl.Float64,
}

METRIC_COLUMNS: list[str] = [
    "school_climate_star_rating",
]

# detail_level is constant ("school") but stays in the key so the guard and
# dedup operate on the same per-level grain the validator checks.
NATURAL_KEYS: list[str] = ["year", "district_code", "school_code", "detail_level"]


# =============================================================================
# Era transform
# =============================================================================


def _transform_one_file(
    df: pl.DataFrame,
    year: int,
) -> pl.DataFrame:
    """Transform one bronze file's frame into gold-shaped school rows.

    The only schema difference across eras that reaches gold is the year
    column's bronze name (`Year` vs `School Year`, already normalized by the
    caller). The bronze `CCRPI Single Score` column (present 2014-2019, gone in
    2024) is left un-renamed and dropped by the final select — this topic
    publishes only the climate star rating.
    """
    # Rename-coverage guard: an unmatched source column silently becomes
    # NULL in gold (the most common data-loss bug) — fail loudly instead.
    # Every era carries the three columns we keep.
    missing = set(COLUMN_RENAME_BASE) - set(df.columns)
    if missing:
        raise ValueError(
            f"Year {year}: bronze missing expected column(s) "
            f"{sorted(missing)}. Present: {sorted(df.columns)}"
        )
    df = df.rename({b: g for b, g in COLUMN_RENAME_BASE.items() if b in df.columns})

    # School-only shape guard: no file carries aggregate sentinel or NULL
    # IDs (re-verified). If either ever appears, district/state rows have
    # entered the feed and the constant detail_level below would be wrong.
    bad = df.filter(
        pl.col("district_code").is_null()
        | pl.col("school_code").is_null()
        | (pl.col("district_code").str.to_uppercase() == AGGREGATE_SENTINEL)
        | (pl.col("school_code").str.to_uppercase() == AGGREGATE_SENTINEL)
    ).height
    if bad:
        raise ValueError(
            f"Year {year}: {bad} row(s) with NULL or "
            f"'{AGGREGATE_SENTINEL}' ID values — school-only assumption broke"
        )

    # ID formatting (education domain CLAUDE.md): zfill(3) pads standard
    # 3-digit district codes and passes 7-digit charter codes through
    # untouched (never truncate); zfill(4) restores school leading zeros —
    # critical for 2024, whose school codes arrive as bare integers ("100").
    df = df.with_columns(
        pl.col("district_code").cast(pl.Utf8).str.zfill(3),
        pl.col("school_code").cast(pl.Utf8).str.zfill(4),
    )

    # Metric cast uses strict=False so any non-numeric residue (the `NA`
    # markers present in every file are already NULL via SUPPRESSION_VALUES
    # at read; this is belt-and-suspenders) becomes NULL instead of raising.
    df = df.with_columns(
        pl.col("year").cast(pl.Int32, strict=False),
        pl.col("school_climate_star_rating").cast(pl.Float64, strict=False),
    )

    # Every row is school-level (guarded above), so detail_level is constant.
    df = df.with_columns(pl.lit("school").alias("detail_level"))
    return df.select(STANDARD_COLUMNS)


# =============================================================================
# File dispatcher
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read one bronze file, resolve its data year, and route by era.

    The data year comes from the in-file `Year`/`School Year` column (the
    source of truth per the structure doc): the 2014 data ships in a file
    whose name carries only the 04.14.15 publication date. A parseable
    filename year that DISAGREES with the in-file year raises — currently
    all six dated filenames agree.
    """
    # Whole-sheet Excel read: every file has a single data sheet, so the
    # shared reader (first sheet, all-Utf8, SUPPRESSION_VALUES -> NULL)
    # suffices. raw == parsed by construction for Excel; record_read_loss is
    # called (after the year is resolved) for auditability and is a
    # structural no-op here.
    df, loss = read_bronze_file(path, return_loss=True)

    if df.height == 0:
        logger.warning("%s: bronze file is empty — skipping", path.name)
        return None

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        # Unrecognized schema = hard failure; silent skipping would quietly
        # drop a year from gold.
        raise ValueError(
            f"{path.name}: no era signature matches columns {df.columns}. "
            f"Update ERA_SIGNATURES if this is a new schema."
        )

    # Normalize the year column name, then pin the single in-file year.
    bronze_columns = list(df.columns)
    year_col = "Year" if "Year" in df.columns else "School Year"
    df = df.rename({year_col: "year"})
    year_vals = df["year"].cast(pl.Int32, strict=False).drop_nulls().unique().to_list()
    if len(year_vals) != 1:
        raise ValueError(
            f"{path.name}: expected exactly one in-file year, got {year_vals}"
        )
    year = int(year_vals[0])

    # Filename-vs-sheet year cross-check (sibling CCRPI precedent). The
    # 2014 file's name has no parseable 20XX year (publication date
    # 04.14.15) — logged, in-file year wins.
    filename_year = extract_year_from_filename(path.name)
    if filename_year is None:
        logger.info(
            "%s: no parseable filename year (publication-date name) — using "
            "in-file year %d",
            path.name,
            year,
        )
    elif filename_year != year:
        raise ValueError(
            f"{path.name}: filename year {filename_year} != in-file year {year}"
        )

    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])
    manifest.record_file(path, year, era, df.height, bronze_columns)
    manifest.record_bronze(year, df.height)

    result = _transform_one_file(df, year)
    logger.info("Processed %s (%s, year=%d): %d rows", path.name, era, year, df.height)
    return result


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for ccrpi_climate_star_rating."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file (single-sheet Excel only).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR, extensions=[".xlsx", ".xls"]):
        result = transform_file(path, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize dtypes/columns across eras and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)
    logger.info("Combined %d rows across %d files", combined.height, len(all_dfs))

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # would mean alias collapse and must raise. The only duplicate key
    # source-wide is the byte-identical 2015 Spring Place Elementary pair
    # (705/1052), which the guard tolerates (identical metrics).
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Dedup tie-break: prefer the row with the higher (non-null-first)
    # school_climate_star_rating, so a hypothetical all-null placeholder twin
    # loses to the data-bearing row. Moot today — the lone duplicate pair is
    # byte-identical — but explicit per transform-topic §4.6.
    before_dedup = combined
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code"],
        district_keys=["year", "district_code"],
        state_keys=["year"],
        sort_col="school_climate_star_rating",
    )
    if combined.height != before_dedup.height:
        dropped = (
            before_dedup.group_by("year")
            .len()
            .join(combined.group_by("year").len(), on="year", suffix="_after")
            .with_columns((pl.col("len") - pl.col("len_after")).alias("_dropped"))
            .filter(pl.col("_dropped") > 0)
        )
        for row in dropped.iter_rows(named=True):
            manifest.record_filtered(
                int(row["year"]),
                int(row["_dropped"]),
                "byte-identical duplicate row in bronze (dedup keep-first)",
            )

    # 4. Geography nulling — a structural no-op here (every row is school-
    # level), run for consistency with the shared pipeline contract. No §4b
    # masks: star ratings are whole 1-5 everywhere; CCRPI scores above 100
    # (max 110.3 in 2016) are legitimate bonus-point-era values, preserved
    # and documented (module docstring + contract description).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # school_climate_star_rating carries only small, stable per-year NA counts
    # (11-60 of ~2,300 rows); any spike is logged, never fatal.
    spikes = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spikes.status == "warning":
        logger.warning("NULL-rate spikes (expected bronze gaps): %s", spikes.details)
    validate_output(
        combined,
        required_non_null=["year", "detail_level", "district_code", "school_code"],
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

    Column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level`` — contract properties (and the validator's schema
    check) follow it.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Georgia public schools' School Climate Star Rating (CCRPI) from "
            "Georgia Insights / GaDOE: an ordinal 1-5 whole-star rating built "
            "from four equally weighted components (climate surveys, student "
            "discipline, safe & substance-free environment, school-wide "
            "attendance), published 2014-2019 and 2024. School-level only — "
            "the source publishes no district or state aggregate rows — with "
            "no demographic breakdowns. Years 2020-2023 are absent (Georgia "
            "paused CCRPI during COVID). The CCRPI Single Score that GaDOE "
            "paired with this rating is not carried here; it lives in the "
            "`ccrpi_scoring_by_component` topic."
        ),
        title="CCRPI Climate Star Rating",
        summary=(
            "Georgia public schools' 1-5 School Climate Star Rating (a CCRPI "
            "component), school-level, 2014-2019 and 2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2018,
                "description": (
                    "Ending calendar year of the school year (e.g., 2018 = "
                    "2017-2018). Sourced from the in-file Year / School Year "
                    "column, not the filename — the 2014 data ships in a "
                    "file named with its 04.14.15 publication date. Coverage: "
                    "2014-2019 and 2024 (2020-2023 absent; COVID CCRPI "
                    "pause)."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "nullable": False,
                "example": "601",
                "description": (
                    "GOSA district code (FK to districts dimension): "
                    "standard 3-digit codes zero-padded; 7-digit state-"
                    "charter / state-school operator codes (e.g., '7820108') "
                    "preserved in full. Non-NULL on every row — this topic "
                    "is school-level only."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "nullable": False,
                "example": "0103",
                "description": (
                    "4-digit GOSA school code, zero-padded (FK to schools "
                    "dimension; composite key with district_code). The 2024 "
                    "file ships bare integer codes ('100'), padded to align "
                    "with prior years ('0100'). Non-NULL on every row."
                ),
            },
            {
                "name": "school_climate_star_rating",
                "type": "float64",
                "unit": "rating",
                "value_min": 1,
                "value_max": 5,
                "key_metric": True,
                "example": 4.0,
                "short_description": (
                    "Overall school climate rating from 1 (most in need of "
                    "improvement) to 5 (excellent); NULL if not rated."
                ),
                "null_meaning": (
                    "School did not receive a climate rating — a literal "
                    "`NA` text marker in bronze (typically new schools, "
                    "special-purpose facilities such as youth detention "
                    "centers, and very small enrollments); 11-60 NULLs per "
                    "year, every one tracing to an `NA` marker, never a "
                    "blank cell."
                ),
                "description": (
                    "School Climate Star Rating, ordinal 1-5 — a diagnostic "
                    "measure of school climate from four equally weighted "
                    "(25%% each) components: (1) student/teacher/parent "
                    "climate surveys, (2) student discipline (weighted "
                    "suspension rate), (3) safe & substance-free learning "
                    "environment, (4) school-wide attendance. 5 = excellent, "
                    "1 = most in need of improvement. Whole stars only — no "
                    "half-steps in any bronze year (enforced as a quality "
                    "check) — but stored Float64 for cross-topic consistency "
                    "with the half-step FESR star ratings, so the API "
                    "exposes one star-rating type. NOT scaled to 0-1."
                ),
            },
        ],
        source="Georgia Insights (GaDOE)",
        source_url=SOURCE_URL,
        update_frequency="annual",
        # Breaking change: ccrpi_single_score removed (was the key metric);
        # school_climate_star_rating is now the sole metric + key metric.
        version="2.0.0",
        year_range=year_range,
        partitioned_by=["year"],
        notes=[
            (
                "Year coverage: 2014-2019 and 2024. Years 2020-2023 are "
                "absent because Georgia paused CCRPI calculation during "
                "COVID; do not interpolate."
            ),
            (
                "school_climate_star_rating is on a 1-5 ordinal scale — "
                "exempt from the 0-1 percentage convention per education "
                "domain rules."
            ),
            (
                "All rows are school-level; the source publishes no "
                "district or state aggregates, so only schools.parquet is "
                "written per year."
            ),
            (
                "The 2015 bronze file contains one byte-identical duplicate "
                "row (Murray County 705 / Spring Place Elementary School "
                "1052); one copy is dropped, so gold 2015 has 2,270 rows vs "
                "2,271 bronze rows."
            ),
            (
                "Every star-rating NULL in every year originates from a "
                "literal `NA` text marker in bronze — no file contains a "
                "blank rating cell (verified at raw-cell level). The markers "
                "mean 'no rating published', not necessarily privacy "
                "suppression, and become NULL at read via the shared "
                "reader's suppression handling."
            ),
            (
                "The CCRPI Single Score is intentionally not published in "
                "this topic (removed in contract v2.0.0): it was stale "
                "(2014-2019 only, dropped from the 2024 release) and fully "
                "duplicated by ccrpi_scoring_by_component, whose "
                "ccrpi_single_score column is a strict superset."
            ),
        ],
        quality_checks=[
            {
                # The derived [1, 5] range check would let a fractional 2.5
                # pass; CCRPI climate ratings are whole stars only (verified
                # in every bronze year — unlike the half-step FESR ratings).
                "name": "school_climate_star_rating_whole_star",
                "description": (
                    "school_climate_star_rating is a whole star in "
                    "{1, 2, 3, 4, 5} when present — no half-steps in any "
                    "bronze year 2014-2019/2024 (verified: 0 violations)."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "school_climate_star_rating IS NOT NULL AND "
                    "school_climate_star_rating NOT IN (1, 2, 3, 4, 5)"
                ),
                "mustBe": 0,
            },
            {
                # Structural fact: school-only topic — both geography keys
                # are populated on every row (no aggregate rows in source).
                "name": "all_rows_school_level",
                "description": (
                    "The source publishes school-level rows only: "
                    "district_code and school_code are non-NULL on every "
                    "row (no district/state aggregates exist in any bronze "
                    "file)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE district_code IS "
                    "NULL OR school_code IS NULL"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
