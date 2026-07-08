"""Transform bronze student_mobility_rate files into one multi-level gold table.

Source: Governor's Office of Student Achievement (GOSA) — annual student
mobility (churn) rate for Georgia public schools and districts, school years
2011-12 through 2023-24. The single published metric is the mobility rate: the
share of students enrolled at any point during the school year but not for the
full year. GOSA computes it as a churn rate — student entries plus withdrawals
between the fall count date and May 1, over the fall-count enrollment — so it
counts moves rather than movers and can legitimately exceed 100%%.

**This topic merges two formerly separate GOSA download families** —
``student_mobility_rates_school`` (one row per school) and
``student_mobility_rates_district`` (one row per district) — into a single
star-schema fact table with two detail levels (``school`` / ``district``).
The two families are distinct downloads with identical metric semantics; the
only structural difference is detail level. A single transform body handles
both behind a per-family dispatch keyed on the ``_school_`` / ``_district_``
infix in each filename.

Detail levels in the merged fact table (``detail_level`` is implicit in the
parquet filename per ``src/etl/education/CLAUDE.md`` and is dropped on export):

- ``school``   — both geography keys populated (school family rows).
- ``district`` — ``district_code`` populated, ``school_code`` NULL (district
  family rows).

There is no ``state`` level — neither family publishes a statewide rollup.
Because ``detail_level`` is not a stored column, the merged quality checks
discriminate detail by the geography-key NULL pattern in the unioned table
(school ⟺ ``school_code IS NOT NULL``; district ⟺ ``school_code IS NULL``).

Design decisions (carried verbatim from the two source transforms — the merge
changes routing and the contract, never the per-file value handling):

- **One metric, ``mobility_rate`` (unit: ratio).** Bronze publishes 0-100; the
  transform divides by 100 (§4). It is a decimal ratio, NOT a bounded
  proportion (§4a): the churn methodology counts moves, not movers, so values
  above 1.0 are legitimate at high-churn facilities (alternative schools, DJJ
  sites, residential treatment centers). The bronze metric column is
  ``mobility_rate`` (2012-2020) then ``mobility`` (2021-2024) in both families,
  semantically identical; era-routed per family.
- **2014 district file is dropped (the school-level anomaly).** Despite the
  topic name, the district family's 2014 file publishes one row per *school*
  (2,261 rows keyed by ``sys_sch``/``school_name``) with no enrollment counts,
  so GOSA's district-level 2014 rate cannot be reconstructed. It is detected by
  signature, recorded via ``manifest.record_filtered``, and dropped from the
  district detail. The byte-identical school family 2014 file supplies 2014's
  school-level rows, so the merged table has full 2014 *school* coverage and a
  documented 2014 *district* gap.
- **District family: exactly 180 districts per year (school_code NULL).** All
  12 district-level files carry the same 180 three-digit codes (601-793), zero
  nulls, no 7-digit charter codes, no state rollup. Pinned by the
  ``district_detail_180_per_year`` quality check (scoped to district-detail
  rows so school rows do not perturb the count).
- **School family: compound ``sys_sch`` splits to the domain dimension scheme.**
    * 6/7-char codes (regular districts): district = first 3 chars, school =
      remainder zero-padded to 4 (``601103`` -> ``601``/``0103``).
    * 10-char codes prefixed ``782``/``783`` (charters): district = first 7
      chars, school = last 3 zero-padded to 4 (``7820108108`` ->
      ``7820108``/``0108``); the 3-char tail repeats the district tail.
    * Codes prefixed ``799`` (state schools): district = first 3, school =
      chars[3:7] zero-padded — covers both the 11-char 2012-2019 form
      (``79918931893`` -> ``799``/``1893``) and the bare 7-char 2020-2024 form
      (``7991893`` -> ``799``/``1893``); both split to identical keys. A shape
      guard hard-stops on any code that fits none of these patterns.
- **No ``demographic`` column.** No era of either family publishes any
  breakdown — every row is implicitly all-students, so the column is omitted
  per §5.
- **No suppression (``suppressed_to_null=False``).** No TFS/``*``/N-A markers
  exist in any file of either family. The district family has zero NULLs; the
  school family has exactly four genuinely blank mobility cells — one each in
  2019, 2020, 2021, 2024 — that become true NULL via the strict=False cast.
  Both facts are pinned by quality checks.
- **2020 Eagle's Landing Academy outlier is PRESERVED (§4b
  extreme-but-conceivable).** sys_sch=701298 (Mitchell County) publishes
  11500.0 raw (115.0 post-divide), ~17x the next 2020 extreme (657.9). A churn
  ratio has no defined upper bound, so it is kept, flagged by the sanity
  warning on every run, and documented in the contract column. No §4b masks
  apply to this topic.

Judgment calls (non-interactive merge):

1. ``default_detail`` is left to auto-derivation, which resolves to the finest
   level present (``schools``), matching the platform convention. Not
   overridden.
2. The cross-level "school rows sum to their district row" invariant is NOT
   asserted: the school and district families are independent GOSA downloads
   whose mobility numerators (the district rate rolls up entry/withdrawal
   counts, not row-averages of the school rates) need not reconcile, and
   neither source transform verified it.
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

TOPIC = "student_mobility_rate"
BRONZE_DIR = Path("data/bronze/education/gosa/student_mobility_rate")
GOLD_DIR = Path("data/gold/education/student_mobility_rate")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
# No `demographic` column — neither family publishes any breakdown (§5).
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "mobility_rate",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "mobility_rate": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = ["mobility_rate"]

NATURAL_KEYS: list[str] = ["year", "district_code", "school_code", "detail_level"]

# Post-divide sanity threshold (10.0 = 1,000%% raw). School-family values above
# it are preserved but warned about on every run — see module docstring.
SANITY_THRESHOLD = 10.0

# Every district-level bronze file carries exactly 180 districts (verified: the
# identical 3-digit code set in all 12 district-level files). A deviation is a
# red flag — warn at transform time; the district_detail_180_per_year contract
# check enforces it.
EXPECTED_DISTRICTS_PER_YEAR = 180


# =============================================================================
# DISTRICT FAMILY — readers + era transform (rows: detail_level "district")
# =============================================================================

# Era-detection signatures, most-specific first (detect_era_by_columns returns
# the first signature fully present). The 2014 school-level anomaly leads
# because its sys_sch/school_name columns are unique to that file; Era 3 is the
# _hs-suffixed name column, Era 4 the renamed metric. Era 1 (plain) goes last.
DISTRICT_ERA_SIGNATURES: dict[str, list[str]] = {
    "era_2_2014_school_level_anomaly": ["sys_sch", "school_name", "mobility_rate"],
    "era_3_2019_2020_nm_hs": [
        "school_district_cd",
        "school_district_nm_hs",
        "mobility_rate",
    ],
    "era_4_2021_2024_mobility_renamed": [
        "school_district_cd",
        "school_district_nm",
        "mobility",
    ],
    "era_1_standard": ["school_district_cd", "school_district_nm", "mobility_rate"],
}

# The school-level anomaly era in the district family: detected explicitly so it
# is dropped with a manifest record instead of school IDs being silently
# treated as districts. The byte-identical school family file supplies 2014.
DISTRICT_ERA_2014_SCHOOL_ANOMALY = "era_2_2014_school_level_anomaly"

# Era-routed bronze metric column: Era 4 renamed `mobility_rate` to `mobility`.
DISTRICT_METRIC_SOURCE_BY_ERA: dict[str, str] = {
    "era_1_standard": "mobility_rate",
    "era_3_2019_2020_nm_hs": "mobility_rate",
    "era_4_2021_2024_mobility_renamed": "mobility",
}


def _transform_district_era(df: pl.DataFrame, year: int, era: str) -> pl.DataFrame:
    """Transform one district-family bronze file (eras 1, 3, 4) to gold shape.

    The three district eras differ only in column names; the era-routed metric
    pick is the whole difference. The district name columns are dimension
    attributes and are not carried into the fact table. Every row is district
    detail (school_code NULL) — no aggregate rows exist in this family.
    """
    metric_col = DISTRICT_METRIC_SOURCE_BY_ERA[era]
    # Rename-coverage guard (§4.1): the era signature guarantees the metric
    # column, but a hard check keeps a silent-NULL rename bug impossible.
    if metric_col not in df.columns:
        raise ValueError(
            f"district/{era} year {year}: expected metric column '{metric_col}' "
            f"missing. Present: {df.columns}"
        )

    # Geography: district codes arrive as clean 3-char digit strings (601-793;
    # verified, no 7-digit charters in this series); zfill(3) pads defensively
    # and never truncates. school_code is always NULL — district detail.
    # Metric: bronze publishes 0-100; divide by 100 onto the 0-1 ratio scale
    # (§4/§4a). strict=False is a defensive guard — the series is fully numeric.
    df = df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.col("school_district_cd")
        .str.strip_chars()
        .str.zfill(3)
        .alias("district_code"),
        pl.lit(None).cast(pl.Utf8).alias("school_code"),
        (pl.col(metric_col).cast(pl.Float64, strict=False) / 100.0).alias(
            "mobility_rate"
        ),
        pl.lit("district").alias("detail_level"),
    )
    return df.select(STANDARD_COLUMNS)


def _transform_district_file(
    path: Path, manifest: TransformManifest
) -> pl.DataFrame | None:
    """Read one district-family bronze file, detect its era, route it.

    The 2014 school-level anomaly is detected by signature and dropped (no rows
    returned), with the drop recorded so the district 2014 gap is reviewable
    rather than a silent absence.
    """
    # Year comes from the filename (..._district_YYYY.xls) — no in-file year
    # column exists in any era to cross-check against.
    year = extract_year_from_filename(path.name)
    if year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")

    df, loss = read_bronze_file(path, return_loss=True)
    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])

    era = detect_era_by_columns(df, DISTRICT_ERA_SIGNATURES)
    if era is None:
        raise ValueError(
            f"{path.name}: no district-family era signature matched "
            f"columns {df.columns}"
        )

    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)

    # 2014 school-level anomaly: drop from district detail (no enrollment
    # weights to reconstruct the district rate); the school family carries 2014.
    if era == DISTRICT_ERA_2014_SCHOOL_ANOMALY:
        manifest.record_filtered(
            year,
            df.height,
            "district_2014_school_level_anomaly_dropped_school_family_carries_it",
        )
        logger.warning(
            "Year %d: DROPPING %s — district file is school-level (%s rows), "
            "not district-level; no enrollment weights exist to reconstruct the "
            "district rate. The school family's identical 2014 file supplies "
            "2014 school rows; the district detail has a documented 2014 gap.",
            year,
            path.name,
            f"{df.height:,}",
        )
        return None

    if df.height != EXPECTED_DISTRICTS_PER_YEAR:
        # Warn only: the district_detail_180_per_year contract check is the
        # enforcement point, so a legitimate future change fails validation
        # loudly instead of being silently ingested.
        logger.warning(
            "Year %d (district): expected %d district rows, got %d — investigate",
            year,
            EXPECTED_DISTRICTS_PER_YEAR,
            df.height,
        )

    logger.info(
        "Processing %s as district/%s (year %d, %d rows)",
        path.name,
        era,
        year,
        df.height,
    )
    return _transform_district_era(df, year, era)


# =============================================================================
# SCHOOL FAMILY — readers + era transform (rows: detail_level "school")
# =============================================================================

# Era-detection signatures, most-specific first. Era B's `_hs` name columns and
# Era C's renamed `mobility` metric are each unique to their era; Era A
# (original names) is listed last as the historical-layout match.
SCHOOL_ERA_SIGNATURES: dict[str, list[str]] = {
    "era_b_2019_2020_hs_suffix": [
        "sys_sch",
        "school_district_nm_hs",
        "school_name_hs",
        "mobility_rate",
    ],
    "era_c_2021_2024_mobility_renamed": [
        "sys_sch",
        "school_district_nm",
        "school_name",
        "mobility",
    ],
    "era_a_2012_2018_original": [
        "sys_sch",
        "school_district_nm",
        "school_name",
        "mobility_rate",
    ],
}

# Bronze metric source column per school era (the only cross-era difference that
# matters; the name columns are dimension attributes and are not carried).
SCHOOL_ERA_METRIC_COLUMN: dict[str, str] = {
    "era_b_2019_2020_hs_suffix": "mobility_rate",
    "era_c_2021_2024_mobility_renamed": "mobility",
    "era_a_2012_2018_original": "mobility_rate",
}

# Charter authorizers publish 10-char compound codes with a 7-char district
# prefix (every 7-digit district in the districts dimension starts with 782 or
# 783). State schools (deaf/blind) publish under the 799 authorizer as 11-char
# codes with a duplicated school tail (2012-2019) or plain 7-char codes
# (2020-2024).
CHARTER_DISTRICT_PREFIXES: tuple[str, ...] = ("782", "783")
STATE_SCHOOL_PREFIX = "799"


def _assert_sys_sch_shapes(df: pl.DataFrame, label: str) -> None:
    """Hard-stop on any sys_sch code the split rules do not cover.

    A malformed or novel code shape would silently mis-derive the geography
    keys (the most damaging failure for a fact table), so every code must be
    digit-only and match one of the three known patterns: 6/7-char regular,
    10-char charter (782/783 prefix), 7/11-char state school (799 prefix).
    """
    code = pl.col("sys_sch")
    is_charter = code.str.slice(0, 3).is_in(list(CHARTER_DISTRICT_PREFIXES))
    is_state_school = code.str.starts_with(STATE_SCHOOL_PREFIX)
    handled = code.str.contains(r"^\d+$") & (
        # Regular district schools: 3-char district + 3/4-char school.
        (code.str.len_chars().is_in([6, 7]) & ~is_charter & ~is_state_school)
        # Charter authorizers: 7-char district + 3-char repeated tail.
        | (is_charter & (code.str.len_chars() == 10))
        # State schools: 799 + 4-char school, either bare (7 chars, 2020-2024)
        # or with a 4-char duplicate tail (11 chars, 2012-2019).
        | (is_state_school & code.str.len_chars().is_in([7, 11]))
    )
    bad = df.filter(~handled)
    if bad.height:
        raise ValueError(
            f"{label}: {bad.height} sys_sch value(s) match no known code "
            f"shape — investigate before splitting: "
            f"{bad['sys_sch'].head(10).to_list()}"
        )


def _split_sys_sch(df: pl.DataFrame) -> pl.DataFrame:
    """Split compound ``sys_sch`` into ``district_code`` + ``school_code``.

    Pattern rules (shape-guarded by _assert_sys_sch_shapes; verified to join
    29,625/29,625 rows against the schools and districts dimensions):
      * 782/783 charter codes: district = first 7 chars, school = chars[7:]
        zero-padded to 4 (the 3-char tail repeats the district tail).
      * 799 state-school codes: district = first 3 chars, school = chars[3:7]
        zero-padded — covers both the 11-char 2012-2019 form and the bare
        7-char 2020-2024 form, which split to identical keys.
      * Everything else: district = first 3 chars, school = chars[3:]
        zero-padded to 4.
    """
    is_charter = (
        pl.col("sys_sch").str.slice(0, 3).is_in(list(CHARTER_DISTRICT_PREFIXES))
    )
    is_state_school = pl.col("sys_sch").str.starts_with(STATE_SCHOOL_PREFIX)
    return df.with_columns(
        pl.when(is_charter)
        .then(pl.col("sys_sch").str.slice(0, 7))
        .otherwise(pl.col("sys_sch").str.slice(0, 3))
        .alias("district_code"),
        pl.when(is_charter)
        .then(pl.col("sys_sch").str.slice(7).str.zfill(4))
        .when(is_state_school)
        .then(pl.col("sys_sch").str.slice(3, 4).str.zfill(4))
        .otherwise(pl.col("sys_sch").str.slice(3).str.zfill(4))
        .alias("school_code"),
    )


def _transform_school_era(
    df: pl.DataFrame,
    year: int,
    era: str,
    label: str,
) -> pl.DataFrame:
    """Transform one school-family bronze file (any era) to gold shape.

    Every row in every era is a single school (no aggregate rows exist in this
    family), so detail_level is the constant "school"; the year comes from the
    filename (no in-file year column in any era).
    """
    # Rename-coverage guard: the era's metric column must be present, or the
    # metric would silently become NULL for the whole year.
    metric_col = SCHOOL_ERA_METRIC_COLUMN[era]
    if metric_col not in df.columns:
        raise ValueError(
            f"{label}: expected metric column '{metric_col}' missing. "
            f"Present: {df.columns}"
        )

    df = df.with_columns(pl.col("sys_sch").str.strip_chars().alias("sys_sch"))
    _assert_sys_sch_shapes(df, label)
    df = _split_sys_sch(df)

    df = df.select(
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.col("district_code"),
        pl.col("school_code"),
        # Bronze publishes 0-100 (all-string Excel read); divide by 100 onto
        # the 0-1 scale per §4. strict=False turns the four genuinely blank
        # cells (2019/2020/2021/2024) into true NULLs; values above 1.0 are
        # legitimate churn ratios and are preserved (unit: ratio, §4a).
        (
            pl.col(metric_col).str.strip_chars().cast(pl.Float64, strict=False) / 100.0
        ).alias("mobility_rate"),
        pl.lit("school").alias("detail_level"),
    )

    # Sanity warning for extreme churn (§4b extreme-but-conceivable — preserved,
    # never capped or dropped). Includes the known 2020 Eagle's Landing Academy
    # suspected source defect (raw 11500 -> 115.0).
    extreme = df.filter(pl.col("mobility_rate") > SANITY_THRESHOLD)
    if extreme.height:
        logger.warning(
            "%s: %d row(s) with mobility_rate > %.1f (>%d%% raw) — preserved "
            "as-is per §4b. Sample: %s",
            label,
            extreme.height,
            SANITY_THRESHOLD,
            int(SANITY_THRESHOLD * 100),
            extreme.select("district_code", "school_code", "mobility_rate")
            .head(5)
            .to_dicts(),
        )

    return df


def _transform_school_file(
    path: Path, manifest: TransformManifest
) -> pl.DataFrame | None:
    """Read one school-family bronze file, detect its era, transform it."""
    # All-string read: keeps the variable-length sys_sch codes intact and makes
    # every cast explicit. XLS files are read whole-sheet via pandas, so raw ==
    # parsed by construction — still recorded for the manifest.
    df, loss = read_bronze_file(path, infer_schema_length=0, return_loss=True)

    # Year is ONLY in the filename (no year column in any era); it is the ending
    # calendar year of the school year per GOSA convention.
    year = extract_year_from_filename(path.name)
    if year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")
    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])

    era = detect_era_by_columns(df, SCHOOL_ERA_SIGNATURES)
    if era is None:
        raise ValueError(
            f"{path.name}: no school-family era signature matched columns {df.columns}"
        )
    label = f"school/{era} {path.name}"

    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)

    if df.height == 0:
        logger.warning("%s: bronze file is empty, skipping", path.name)
        return None

    logger.info(
        "Processing %s as school/%s (year %d, %d rows)", path.name, era, year, df.height
    )
    return _transform_school_era(df, year, era, label)


# =============================================================================
# Per-file dispatch (route by filename family infix)
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Dispatch one bronze file to the school or district family transform.

    The merged bronze dir holds both download families; the ``_school_`` /
    ``_district_`` infix in the filename selects the per-family reader + era
    logic. Anything else is an unrecognized file and must stop the pipeline.
    """
    name = path.name
    if "_school_" in name:
        return _transform_school_file(path, manifest)
    if "_district_" in name:
        return _transform_district_file(path, manifest)
    raise ValueError(
        f"{name}: cannot route — filename carries neither '_school_' nor "
        f"'_district_' family infix"
    )


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for the merged student_mobility_rate."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file from BOTH families (read-loss
    # accounted per file; the district family's 2014 school-level file is
    # recorded, then dropped — the school family carries 2014).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR):
        result = transform_file(path, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize columns/dtypes across eras + families and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)
    logger.info("Combined %d rows across %d files", combined.height, len(all_dfs))

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean an era-routing or ID-formatting bug and must raise, never be silently
    # deduped. detail_level is part of the natural key, so a school and a
    # district row that share (year, district_code) never collide (school rows
    # carry a non-NULL school_code).
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: each file is one non-overlapping school year with no in-file
    # duplicates, so dedup is purely defensive. sort_col="mobility_rate" prefers
    # a row with a reported rate over a blank placeholder if a future
    # republication introduces duplicates.
    pre_dedup = dict(combined.group_by("year").len().iter_rows())
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code"],
        district_keys=["year", "district_code"],
        state_keys=["year"],
        sort_col="mobility_rate",
    )
    post_dedup = dict(combined.group_by("year").len().iter_rows())
    for year in sorted(pre_dedup):
        removed = pre_dedup[year] - post_dedup.get(year, 0)
        if removed > 0:
            manifest.record_filtered(year, removed, "duplicate_rows_deduped")

    # 4. Geography nulling via the shared domain rules: district rows keep
    # school_code NULL; school rows keep both keys. A structural no-op here
    # (every district row already has school_code NULL and every school row has
    # both keys populated) but run so transform and validator share one rule
    # source. No §4b masks apply (the 2020 outlier is preserved).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. Expected NULLs: exactly one blank school mobility cell
    # in each of 2019, 2020, 2021, 2024 (~0.04%% of those years) — no spike
    # expected. Only year + detail_level + district_code are universally
    # non-null (school rows additionally carry school_code).
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(
        combined, required_non_null=["year", "detail_level", "district_code"]
    )

    # 5. Manifest stats on the FINAL DataFrame, then export to schools /
    # districts parquet by detail level.
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(combined, GOLD_DIR, STANDARD_COLUMNS)
    manifest.write(GOLD_DIR)

    # 6. Contract + README from the in-code column declaration. detail_levels /
    # default_detail are auto-discovered from the gold layout the export just
    # wrote (schools/districts -> default schools).
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
    geography-key NULL pattern (detail_level is implicit in the parquet filename
    and absent from the unioned validation view).
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Annual student mobility (churn) rate for Georgia public schools "
            "and districts, published by GOSA for school years 2011-12 through "
            "2023-24 (filename year = ending calendar year, e.g. 2024 = "
            "2023-24). Mobility is the share of students enrolled at any point "
            "during the school year but not for the full year; GOSA computes it "
            "as a churn rate — student entries plus withdrawals between the "
            "fall count date and May 1, over the fall-count enrollment — so it "
            "counts moves rather than movers and can legitimately exceed 100%%. "
            "One fact table at two detail levels: school (one row per school) "
            "and district (one row per district / system). No demographic "
            "breakdowns. Merges the formerly separate "
            "student_mobility_rates_school and student_mobility_rates_district "
            "topics."
        ),
        title="Student Mobility Rates",
        summary=(
            "How often students change schools in each Georgia public school "
            "and district, as an annual churn rate, 2012-2024 (no 2014 "
            "district rows)."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Ending (spring) calendar year of the school year (e.g. "
                    "2024 for 2023-24), taken from the bronze filename — no "
                    "in-file year column exists in either family."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "null_meaning": (
                    "Never NULL — neither family publishes a statewide "
                    "aggregate, so every school and district row carries a "
                    "populated district_code."
                ),
                "description": (
                    "GOSA district code (FK to districts dimension), "
                    "zero-padded to 3 digits for standard county/city "
                    "districts (codes 601-793) and the 799 state-schools "
                    "authorizer; 7-digit state/commission-charter authorizer "
                    "codes (782xxxx/783xxxx, school rows only) are preserved "
                    "unchanged. On district-detail rows it is the bronze "
                    "school_district_cd; on school-detail rows it is the first "
                    "3 (or 7) characters of the compound sys_sch code. Never "
                    "NULL."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0103",
                "null_meaning": (
                    "Populated only on school-detail rows; NULL on every "
                    "district-detail row (the district level has no school "
                    "code). The column is shared across the education key "
                    "shape."
                ),
                "description": (
                    "GOSA school code, zero-padded to 4 characters (composite "
                    "FK to schools dimension with district_code; not globally "
                    "unique on its own). Populated on school rows only — "
                    "district rows carry NULL. Extracted from the compound "
                    "bronze sys_sch code: chars after the 3-char district "
                    "prefix for regular districts ('601103' -> '0103'), chars "
                    "4-7 for 799 state-school codes (both the 11-char "
                    "2012-2019 form '79918931893' and the 7-char 2020-2024 "
                    "form '7991893' -> '1893'), or the last 3 chars for "
                    "10-char charter codes ('7820108108' -> '0108')."
                ),
            },
            {
                "name": "mobility_rate",
                "key_metric": True,
                "type": "float64",
                "unit": "ratio",
                "example": 0.214,
                "null_meaning": (
                    "The source cell was genuinely blank (no rate published "
                    "for that school that year) — NOT small-cell suppression. "
                    "Exactly four such blanks exist, all school-detail: one "
                    "each in 2019, 2020, 2021, and 2024. District rows are "
                    "never NULL."
                ),
                "short_description": (
                    "Student churn rate (0-1 scale): student moves per fall "
                    "enrollment; counts moves, so it can exceed 1.0."
                ),
                "description": (
                    "Student mobility (churn) rate on the 0-1 scale (0.214 = "
                    "21.4%%): student entries plus withdrawals between the fall "
                    "count date and May 1, divided by fall-count enrollment. "
                    "Bronze publishes 0-100; divided by 100 per "
                    "data-cleaning-standards §4. A ratio, not a bounded "
                    "proportion: the metric counts student moves rather than "
                    "distinct students, so values above 1.0 are legitimate and "
                    "preserved — at the school level 33-59 rows per year exceed "
                    "1.0 at alternative schools, DJJ facilities, and "
                    "residential treatment centers (e.g. 5.333 = 533.3%% at "
                    "Lighthouse Care Center of Augusta, 2024). District-level "
                    "values stay below 1.0 in all published years (max 0.59 in "
                    "2016). One school value is a suspected source defect "
                    "preserved per §4b (extreme-but-conceivable): 2020 "
                    "district_code=701 / school_code=0298 (Eagle's Landing "
                    "Academy) publishes 115.0 (raw 11500), ~17x that year's "
                    "next extreme (657.9); it is retained, not capped, and "
                    "flagged by the transform's sanity warning. Bronze column "
                    "name: mobility_rate (2012-2020), renamed to mobility "
                    "(2021-2024) in both families, semantically identical."
                ),
            },
        ],
        source="GOSA",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        # No suppression anywhere in either family — every district publishes a
        # numeric rate in every year, and the only school NULLs are four blank
        # cells (pinned by mobility_rate quality checks).
        suppressed_to_null=False,
        limitations=(
            "Two detail levels (school, district) in one fact table, split by "
            "parquet filename; school_code is NULL on district rows. No "
            "statewide rollup is published in either family, so state figures "
            "cannot be read from this table. The district level has a "
            "documented 2014 gap: GOSA published the 2014 district file at the "
            "school level only (a file byte-identical to the school family's "
            "2014 file), with no enrollment counts from which to reconstruct "
            "the district rate, so the district 2014 rows are omitted; 2014 "
            "school-level rows are present (from the school family). The "
            "school-level and district-level rows come from two independent "
            "GOSA downloads — the district rate rolls up entry/withdrawal "
            "counts rather than averaging the school rates — so school rows are "
            "NOT guaranteed to reconcile with their district row. Mobility is a "
            "churn ratio, not a bounded proportion: it counts moves rather than "
            "movers, so school-level values above 1.0 are legitimate and "
            "preserved (one suspected 2020 source defect, Eagle's Landing "
            "Academy at 115.0, is retained per §4b). No suppression exists in "
            "this topic — the only NULLs are four genuinely blank school cells "
            "(2019, 2020, 2021, 2024); NULL never means suppressed."
        ),
        notes=[
            (
                "Two detail levels: school (one row per school, both geography "
                "keys populated) and district (one row per district/system, "
                "school_code NULL). schools.parquet under every year partition; "
                "districts.parquet under every year partition except 2014 "
                "(district gap). detail_level is implicit in the filename and "
                "is not a stored column. No states.parquet — neither family "
                "publishes a statewide rollup."
            ),
            (
                "mobility_rate is on the 0-1 scale (bronze publishes 0-100; "
                "divided by 100 per data-cleaning-standards §4). It is a "
                "decimal ratio, not a bounded proportion: the churn methodology "
                "counts moves, not movers, so school-level values above 1.0 are "
                "legitimate (33-59 rows per year) at high-churn facilities. "
                "District-level values stay below 1.0 in all published years."
            ),
            (
                "2014 district rows are intentionally omitted. The bronze 2014 "
                "district file is school-level (2,261 rows keyed by "
                "sys_sch/school_name, byte-identical to the school family's "
                "2014 file) with no enrollment column, so GOSA's district "
                "number cannot be reproduced from it. The drop is recorded in "
                "the transform manifest; 2014 school-level rows are present via "
                "the school family."
            ),
            (
                "Compound bronze sys_sch codes (school family) split to the "
                "domain dimension scheme: regular districts "
                "first-3/remainder-zfill4; 782/783 charter authorizers "
                "first-7/last-3-zfill4 (the 3-char tail repeats the district "
                "tail); 799 state schools first-3/chars-4-7 (published as "
                "11-char codes with a duplicated school tail in 2012-2019, then "
                "as bare 7-char codes from 2020 — both split to identical "
                "keys). All 29,625 school rows join the schools and districts "
                "dimensions with zero misses."
            ),
            (
                "Era renames normalized to gold. District family: "
                "school_district_nm_hs (2019-2020) and mobility (2021-2024). "
                "School family: school_district_nm_hs/school_name_hs "
                "(2019-2020) and mobility (2021-2024). District/school names "
                "are dimension attributes and are not carried into the fact "
                "table."
            ),
            (
                "No suppression markers exist in any file. The district family "
                "has zero NULLs; the school family has exactly four blank "
                "mobility cells (one each in 2019, 2020, 2021, 2024) that "
                "become true NULLs — both facts are pinned as quality checks."
            ),
            (
                "2020 school outlier preserved: Eagle's Landing Academy "
                "(district 701, school 0298) publishes raw 11500.0 (gold "
                "115.0), a suspected source defect ~17x the next 2020 extreme. "
                "Preserved per §4b extreme-but-conceivable (churn has no "
                "defined upper bound) and flagged by the transform's "
                "sanity-threshold warning on every run."
            ),
            (
                "No demographic column: neither family publishes any race, "
                "gender, or economic-status breakdown in any era; every row is "
                "implicitly an all-students aggregate."
            ),
        ],
        quality_checks=[
            {
                "name": "no_state_rows",
                "description": (
                    "Structural fact: neither family publishes a statewide "
                    "rollup, so every gold row (school or district detail) has "
                    "a populated district_code. A NULL district_code means a "
                    "state row appeared or an ID parse failed — either must be "
                    "analyzed."
                ),
                "dimension": "consistency",
                "query": ("SELECT COUNT(*) FROM {object} WHERE district_code IS NULL"),
                "mustBe": 0,
            },
            {
                "name": "district_code_length_3_or_7",
                "description": (
                    "district_code is a 3-character standard county/city / "
                    "state-schools code or a 7-character charter-authorizer "
                    "code (school rows only) — any other length means the ID "
                    "formatting or the sys_sch split regressed."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE LENGTH(district_code) NOT IN (3, 7)"
                ),
                "mustBe": 0,
            },
            {
                "name": "school_code_length_4",
                "description": (
                    "Where populated (school-detail rows), school_code is "
                    "always zero-padded to exactly 4 characters, matching the "
                    "schools dimension key format."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE school_code IS NOT NULL AND LENGTH(school_code) <> 4"
                ),
                "mustBe": 0,
            },
            {
                "name": "district_detail_180_per_year",
                "description": (
                    "Every published year carries exactly one district-detail "
                    "row for each of the same 180 standard districts (verified: "
                    "the identical 3-digit code set in all 12 district-level "
                    "bronze files; 2014 is omitted). District-detail rows are "
                    "the school_code IS NULL rows. A deviation means a "
                    "dropped/added entity or a mis-routed file and must be "
                    "analyzed."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year FROM {object} "
                    "WHERE school_code IS NULL GROUP BY year "
                    "HAVING COUNT(*) <> 180 "
                    "OR COUNT(DISTINCT district_code) <> 180) AS bad_years"
                ),
                "mustBe": 0,
            },
            {
                "name": "no_district_rows_2014",
                "description": (
                    "Structural fact: the district family's 2014 file is "
                    "school-level and is dropped, so there must be zero "
                    "district-detail rows (school_code IS NULL) in 2014. A "
                    "district row in 2014 means the school-level anomaly file "
                    "was mis-routed as district data."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE year = 2014 AND school_code IS NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "district_mobility_rate_never_null",
                "description": (
                    "The district family has no suppression and no blank "
                    "cells: every district-detail row (school_code IS NULL) in "
                    "every published year carries a numeric mobility_rate. A "
                    "NULL there means a parsing/era-routing regression."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE school_code IS NULL AND mobility_rate IS NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "school_mobility_nulls_only_in_known_years",
                "description": (
                    "The source has no suppression; the only NULL mobility_rate "
                    "values are the four genuinely blank school-level bronze "
                    "cells, one each in 2019, 2020, 2021, and 2024. A NULL in "
                    "any other year (or on a district row) means a cast or "
                    "era-routing regression."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE mobility_rate IS NULL "
                    "AND year NOT IN (2019, 2020, 2021, 2024)"
                ),
                "mustBe": 0,
            },
            {
                "name": "school_mobility_at_most_one_null_per_year",
                "description": (
                    "Each of the four known-blank years carries exactly one "
                    "blank school cell, so no year may have more than one NULL "
                    "mobility_rate (pins the no-suppression fact; a larger count "
                    "would mean a column-rename or cast regression)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year FROM {object} WHERE mobility_rate IS NULL "
                    "GROUP BY year HAVING COUNT(*) > 1) AS bad_years"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
