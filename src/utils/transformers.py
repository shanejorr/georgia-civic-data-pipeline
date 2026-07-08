"""Common transformer utilities for GOSA ETL pipelines.

This module provides shared functions and classes used across multiple
GOSA transform pipelines to ensure consistency and reduce code duplication.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from src.utils._checks import check_demographics

logger = logging.getLogger(__name__)


# =============================================================================
# Row Count Tracking
# =============================================================================


@dataclass
class RowCountTracker:
    """Track row counts throughout the transformation pipeline.

    Monitors data volume at each stage to detect unexpected data loss or expansion.
    The expansion factor helps identify when row counts change significantly (e.g.,
    due to filtering invalid rows, wide-to-long transformations, or data quality
    issues).

    Gold counts are populated by a single call to `record_gold_from_dataframe()`
    on the *final* combined DataFrame, so that dedup/aggregation steps that
    change row counts are reflected correctly. Per-year filtered counts are
    derived at summary time as `bronze - gold` rather than tracked separately,
    which captures every source of row loss (explicit filters, dedup, etc.).

    The derived `bronze - gold` figure goes to 0 for unpivot/expand transforms
    (gold rows > bronze rows), hiding intentional row removal. Transforms can
    additionally call `record_filtered(year, count, reason)` to log explicit
    filter/dedup events that survive the expansion; these are surfaced
    additively in `summary()` (as `filtered_explicit` plus a per-year /
    per-reason breakdown) without altering the derived `total_filtered`.

    Attributes:
        bronze_rows_by_year: Row counts from bronze files by year.
        gold_rows_by_year: Row counts in gold output by year — populated by
            `record_gold_from_dataframe()`.
        expansion_factors: Ratio of gold to bronze rows by year.
        filtered_events: Explicit filter/dedup events as a list of dicts
            ({"year", "count", "reason"}), populated by `record_filtered()`.
    """

    bronze_rows_by_year: dict[int, int] = field(default_factory=dict)
    gold_rows_by_year: dict[int, int] = field(default_factory=dict)
    expansion_factors: dict[int, float] = field(default_factory=dict)
    filtered_events: list[dict] = field(default_factory=list)

    def record_filtered(self, year: int, count: int, reason: str) -> None:
        """Record an explicit filter/dedup event (rows intentionally removed).

        Use this to make intentional row removal visible in the manifest even
        when the transform is an unpivot/expand (gold rows > bronze rows), where
        the derived `bronze - gold` filtered figure is always 0 and would
        otherwise hide the removal.

        This is purely additive — it does NOT affect `gold_rows_by_year`,
        `expansion_factors`, or the derived `total_filtered`/`filtered_by_year`
        values (those remain `bronze - gold`). Events accumulate across calls;
        a `count` of 0 is ignored so defensive no-op call sites don't litter the
        manifest.

        Args:
            year: Calendar year the rows were removed from.
            count: Number of rows removed (ignored if <= 0).
            reason: Short human-readable reason (e.g., "malformed_sysschoolid",
                "duplicate_sysschoolid").
        """
        if count <= 0:
            return
        self.filtered_events.append(
            {"year": int(year), "count": int(count), "reason": str(reason)}
        )
        logger.info(
            f"Year {year}: Recorded {count:,} explicitly filtered row(s) "
            f"(reason: {reason})"
        )

    def filtered_explicit_by_year(self) -> dict[int, int]:
        """Total explicitly-filtered rows per year (sum of recorded events)."""
        result: dict[int, int] = {}
        for event in self.filtered_events:
            year = event["year"]
            result[year] = result.get(year, 0) + event["count"]
        return result

    def filtered_explicit_by_reason(self) -> dict[str, int]:
        """Total explicitly-filtered rows per reason (sum of recorded events)."""
        result: dict[str, int] = {}
        for event in self.filtered_events:
            reason = event["reason"]
            result[reason] = result.get(reason, 0) + event["count"]
        return result

    def record_bronze(self, year: int, count: int) -> None:
        """Record bronze row count for a year.

        Accumulates across multiple calls for the same year so topics whose
        bronze ecosystem is multiple files per year (e.g., a CCRPI file plus
        a standalone cohort file for the same year) get the true total
        instead of only the last file's count.

        Args:
            year: Calendar year.
            count: Number of rows in bronze file.
        """
        self.bronze_rows_by_year[year] = self.bronze_rows_by_year.get(year, 0) + count
        logger.info(f"Year {year}: Read {count:,} bronze rows")

    def record_gold_from_dataframe(
        self,
        df: pl.DataFrame,
        year_col: str = "year",
    ) -> None:
        """Populate per-year gold counts from the final combined DataFrame.

        Call this once in `main()` after every row-changing operation
        (harmonize, concat, dedup, collision aggregation, geography nulling)
        and before export. Computing counts from the final DataFrame is the
        only way to guarantee the manifest matches the parquet files that
        actually land on disk.

        Any existing gold counts are cleared first so this call is the
        authoritative record — callers should not mix this with per-file
        gold recording.

        Args:
            df: The final combined DataFrame, just before export.
            year_col: Name of the year column. Defaults to "year".

        Raises:
            ValueError: If `year_col` is not present in `df`.
        """
        if year_col not in df.columns:
            raise ValueError(
                f"record_gold_from_dataframe: year column '{year_col}' not in "
                f"DataFrame. Available columns: {df.columns}"
            )

        self.gold_rows_by_year.clear()
        self.expansion_factors.clear()

        # Group by year once; avoids iterating distinct years with filter().
        year_counts = df.group_by(year_col).len().sort(year_col)
        for row in year_counts.iter_rows(named=True):
            year = int(row[year_col])
            count = int(row["len"])
            self.gold_rows_by_year[year] = count
            bronze = self.bronze_rows_by_year.get(year)
            if bronze:
                factor = count / bronze
                self.expansion_factors[year] = factor
                logger.info(
                    f"Year {year}: Produced {count:,} gold rows "
                    f"(expansion factor: {factor:.2f}x)"
                )
            else:
                logger.info(f"Year {year}: Produced {count:,} gold rows")

    def filtered_by_year(self) -> dict[int, int]:
        """Derived per-year filtered counts (`bronze - gold`, clamped >= 0).

        Returns a new dict covering every year that has either a bronze or
        gold count recorded. Years with no bronze count report 0 (can't
        meaningfully derive filtering without a baseline).
        """
        years = set(self.bronze_rows_by_year) | set(self.gold_rows_by_year)
        result: dict[int, int] = {}
        for year in sorted(years):
            bronze = self.bronze_rows_by_year.get(year, 0)
            gold = self.gold_rows_by_year.get(year, 0)
            result[year] = max(bronze - gold, 0)
        return result

    def summary(self) -> dict:
        """Return summary statistics.

        Returns:
            Dictionary with total bronze, gold, filtered rows and years processed.
            `total_filtered` is derived as `max(total_bronze - total_gold, 0)`
            (unchanged, backward compatible). When explicit filter/dedup events
            have been recorded via `record_filtered()`, the summary additionally
            carries `filtered_explicit` (grand total), `filtered_explicit_by_year`
            (per-year totals), and `filtered_explicit_by_reason` (per-reason
            totals). These keys are omitted when no events were recorded so the
            shape is unchanged for transforms that don't use them.
        """
        total_bronze = sum(self.bronze_rows_by_year.values())
        total_gold = sum(self.gold_rows_by_year.values())
        result = {
            "total_bronze": total_bronze,
            "total_gold": total_gold,
            "total_filtered": max(total_bronze - total_gold, 0),
            "years_processed": len(self.bronze_rows_by_year),
        }
        if self.filtered_events:
            by_year = self.filtered_explicit_by_year()
            result["filtered_explicit"] = sum(by_year.values())
            result["filtered_explicit_by_year"] = by_year
            result["filtered_explicit_by_reason"] = self.filtered_explicit_by_reason()
        return result


# =============================================================================
# Column Harmonization
# =============================================================================


def harmonize_columns(
    dfs: list[pl.DataFrame],
    standard_columns: list[str],
    target_types: dict[str, pl.DataType] | None = None,
) -> list[pl.DataFrame]:
    """Ensure all DataFrames have the same columns, types, and order for concatenation.

    Different schema eras may have slightly different column sets or types.
    This function harmonizes them to enable pl.concat() to work without errors.

    Args:
        dfs: List of DataFrames to harmonize.
        standard_columns: List of columns in desired order (standard columns first).
        target_types: Optional dict mapping column names to target Polars data types.

    Returns:
        List of DataFrames with consistent columns, types, and order.
    """
    if not dfs:
        return dfs

    if target_types is None:
        target_types = {}

    # Collect the union of all columns across all DataFrames.
    # Different schema eras may have slightly different column sets.
    all_columns = set()
    for df in dfs:
        all_columns.update(df.columns)

    # Build column order with standard_columns first for predictable output.
    # Any extra columns (unlikely) are appended alphabetically.
    column_order = [c for c in standard_columns if c in all_columns]
    extra_cols = sorted(all_columns - set(column_order))
    column_order.extend(extra_cols)

    # Process each DataFrame to ensure uniform schema.
    # This enables pl.concat() to work without column mismatches.
    harmonized = []
    for df in dfs:
        # Add columns that exist in other DataFrames but not this one.
        # Uses NULL values with the correct target type to avoid schema conflicts.
        missing = all_columns - set(df.columns)
        for col in missing:
            if col in target_types:
                # Create null column with correct target type.
                df = df.with_columns(pl.lit(None).cast(target_types[col]).alias(col))
            else:
                # Default to Utf8 for unknown columns to avoid Null type conflicts.
                df = df.with_columns(pl.lit(None).cast(pl.Utf8).alias(col))

        # Cast existing columns to target types for consistent schema.
        # Prevents type conflicts when concatenating DataFrames from different eras.
        for col, dtype in target_types.items():
            if col in df.columns:
                df = df.with_columns(pl.col(col).cast(dtype))

        # Reorder columns to match standard output order.
        df = df.select(column_order)

        harmonized.append(df)

    return harmonized


# =============================================================================
# Output Validation
# =============================================================================


def validate_output(
    df: pl.DataFrame,
    required_non_null: list[str] | None = None,
    log_only: bool = True,
) -> bool:
    """Comprehensive validation of transformed data.

    Runs multiple validation checks to ensure data quality before export.
    Delegates demographic validation to validators.check_demographics so
    transform-time and post-export validation use identical logic.

    Args:
        df: Transformed DataFrame.
        required_non_null: List of columns that must not contain NULL values.
            Defaults to ["year", "detail_level"]. Note: "demographic" is only
            required for datasets with demographic breakdowns.
        log_only: If True, only log errors. If False, raise AssertionError on failure.

    Returns:
        True if all validations pass, False otherwise.

    Raises:
        AssertionError: If log_only=False and any validation fails.
    """
    if required_non_null is None:
        required_non_null = ["year", "detail_level"]

    all_valid = True

    # Demographic validation: single source of truth is validators.check_demographics.
    if "demographic" in df.columns:
        result = check_demographics(df)
        if result.status == "fail":
            all_valid = False
            msg = f"{result.message}: {result.details}"
            if log_only:
                logger.error(msg)
            else:
                raise AssertionError(msg)

    # Check required metadata columns are never null.
    # These columns are essential for API queries and data integrity.
    for col in required_non_null:
        if col in df.columns:
            null_count = df[col].null_count()
            if null_count > 0:
                msg = f"Column {col} has {null_count} null values"
                if log_only:
                    logger.warning(msg)
                else:
                    all_valid = False
                    raise AssertionError(msg)

    # Validate ID columns are strings (not accidentally integers).
    # District/school codes must be strings to preserve leading zeros (e.g., "001");
    # county FIPS must stay strings to preserve the "13" state prefix.
    string_cols = ["district_code", "school_code", "county_fips"]
    for col in string_cols:
        if col in df.columns:
            dtype = df[col].dtype
            if dtype != pl.Utf8:
                all_valid = False
                msg = f"Column {col} should be string, got {dtype}"
                if log_only:
                    logger.error(msg)
                else:
                    raise AssertionError(msg)

    # Log summary statistics for manual review.
    # Helps identify unexpected data patterns or missing years.
    logger.info("Validation summary:")
    logger.info(f"  Total rows: {df.height:,}")
    logger.info(f"  Years: {sorted(df['year'].unique().to_list())}")
    if "detail_level" in df.columns:
        logger.info(f"  Detail levels: {df['detail_level'].unique().to_list()}")
    if "demographic" in df.columns:
        logger.info(f"  Demographics: {df['demographic'].unique().to_list()}")

    return all_valid


# =============================================================================
# Parquet Export
# =============================================================================


# Default detail-level -> output filename map for education topics.
# Non-education domains pass their own map to export_to_parquet().
EDUCATION_DETAIL_LEVEL_FILES: dict[str, str] = {
    "school": "schools.parquet",
    "district": "districts.parquet",
    "state": "states.parquet",
}

# Detail-level -> output filename map for county-grain domains (criminal_justice).
COUNTY_DETAIL_LEVEL_FILES: dict[str, str] = {
    "county": "counties.parquet",
    "state": "states.parquet",
}

# Detail-level -> output filename map for federal-district-grain topics
# (criminal_justice/federal_justice): the district IS the geography — there is
# no county_fips, so district rows carry detail_level='federal_district' and
# export as federal_districts.parquet. The 'state' entry is a safety valve for
# a future statewide-rollup row (export silently drops unmapped levels).
FEDERAL_DISTRICT_DETAIL_LEVEL_FILES: dict[str, str] = {
    "federal_district": "federal_districts.parquet",
    "state": "states.parquet",
}


def export_to_parquet(
    df: pl.DataFrame,
    output_dir: Path,
    standard_columns: list[str],
    detail_level_files: dict[str, str] | None = None,
) -> None:
    """Export transformed data to year-partitioned Parquet files.

    When `detail_level` is present, emits one file per (year, detail_level) pair.
    When `detail_level` is absent, emits a single `data.parquet` per year.

    The `detail_level` column is dropped from output because it is implicit in
    the filename.

    Args:
        df: Transformed DataFrame.
        output_dir: Path to gold directory for output files.
        standard_columns: List of columns in desired output order.
        detail_level_files: Mapping of detail_level value -> output filename.
            Defaults to EDUCATION_DETAIL_LEVEL_FILES. Pass a domain-specific
            map for non-education topics. Ignored if `detail_level` not in df.
    """
    # Select columns in standard order and drop any extras.
    final_cols = [c for c in standard_columns if c in df.columns]
    df = df.select(final_cols)

    # Sort by all output columns so parquet bytes are reproducible across runs.
    # Upstream ops (group_by, unique) don't guarantee row order, which made
    # sha256-based drift detection trip on every re-run even when data matched.
    df = df.sort(final_cols, nulls_last=True)

    has_detail_level = "detail_level" in df.columns
    level_file_map = detail_level_files or EDUCATION_DETAIL_LEVEL_FILES

    # Partition output by year for efficient querying.
    # API queries typically filter by year first.
    for year in sorted(df["year"].unique().to_list()):
        year_df = df.filter(pl.col("year") == year)
        year_dir = output_dir / f"year={year}"
        year_dir.mkdir(parents=True, exist_ok=True)

        if not has_detail_level:
            # Single file per year for topics without detail-level splits.
            output_path = year_dir / "data.parquet"
            year_df.write_parquet(output_path)
            logger.info(f"Wrote {year_df.height:,} rows to {output_path}")
            continue

        # Split each year into separate files by detail level.
        for level, filename in level_file_map.items():
            level_df = year_df.filter(pl.col("detail_level") == level)
            if level_df.height == 0:
                continue
            # Drop detail_level — it's implicit in the filename.
            level_df = level_df.drop("detail_level")
            output_path = year_dir / filename
            level_df.write_parquet(output_path)
            logger.info(f"Wrote {level_df.height:,} rows to {output_path}")


# =============================================================================
# Deduplication
# =============================================================================


def assert_no_natural_key_collisions(
    df: pl.DataFrame,
    natural_keys: list[str],
    metric_cols: list[str],
    *,
    diagnostic_cols: list[str] | None = None,
    label: str = "",
) -> None:
    """Raise if multiple rows share a natural key but disagree on metric values.

    Use this guard *before* `deduplicate_by_detail_level` to surface alias /
    name-resolution bugs that would otherwise be hidden when dedup silently
    keeps one row and drops the rest. Same-valued duplicates (true repeats)
    are tolerated; metric-divergent duplicates raise with a sample of the
    offending rows so the alias can be corrected.

    Args:
        df: DataFrame about to be deduplicated.
        natural_keys: Columns that should uniquely identify a fact row.
        metric_cols: Metric columns whose values must agree across duplicates.
        diagnostic_cols: Extra columns (e.g. raw bronze names) to include in
            the error message to help identify the root cause. Optional.
        label: Topic / context label for the error message (e.g. detail level).
    """
    available_keys = [c for c in natural_keys if c in df.columns]
    available_metrics = [c for c in metric_cols if c in df.columns]
    if not available_keys or not available_metrics:
        return

    dup_keys = (
        df.group_by(available_keys)
        .agg(pl.len().alias("_n"))
        .filter(pl.col("_n") > 1)
        .drop("_n")
    )
    if dup_keys.height == 0:
        return

    dup_rows = df.join(dup_keys, on=available_keys, how="inner")
    divergent = (
        dup_rows.group_by(available_keys)
        .agg([pl.col(m).n_unique().alias(f"_nu_{m}") for m in available_metrics])
        .filter(pl.any_horizontal([pl.col(f"_nu_{m}") > 1 for m in available_metrics]))
        .select(available_keys)
    )
    if divergent.height == 0:
        return

    extras = [c for c in (diagnostic_cols or []) if c in dup_rows.columns]
    sample = (
        dup_rows.join(divergent, on=available_keys, how="inner")
        .select(available_keys + available_metrics + extras)
        .head(20)
    )
    suffix = f" ({label})" if label else ""
    raise ValueError(
        f"Natural key collision{suffix}: {divergent.height} key group(s) "
        f"have rows with divergent metric values. This usually means a "
        f"manual alias is collapsing distinct entities. Sample:\n{sample}"
    )


def deduplicate_by_detail_level(
    df: pl.DataFrame,
    school_keys: list[str],
    district_keys: list[str],
    state_keys: list[str],
    sort_col: str = "num_tested",
) -> pl.DataFrame:
    """Remove duplicate rows by natural key columns for each education detail level.

    Thin wrapper over deduplicate_by_levels for the education school/district/state
    levels. See deduplicate_by_levels for the strategy.

    Args:
        df: DataFrame potentially containing duplicates.
        school_keys: Key columns for school-level deduplication.
        district_keys: Key columns for district-level deduplication.
        state_keys: Key columns for state-level deduplication.
        sort_col: Column to use for preferring rows (default: "num_tested").

    Returns:
        DataFrame with duplicates removed.
    """
    return deduplicate_by_levels(
        df,
        {"school": school_keys, "district": district_keys, "state": state_keys},
        sort_col=sort_col,
    )


def deduplicate_by_levels(
    df: pl.DataFrame,
    level_keys: dict[str, list[str]],
    sort_col: str = "num_tested",
) -> pl.DataFrame:
    """Remove duplicate rows by natural key columns for each detail level.

    Source data sometimes has duplicate entries for the same natural key
    (e.g., overlapping source files or repeated rows in bronze data).

    Deduplication strategy:
    - Group by key columns
    - Keep the row with non-null sort_col (prefer actual data over placeholders)
    - If both have data, keep the row with higher value

    Rows whose detail_level is not a key of level_keys are dropped (matching the
    historical behavior of the education wrapper, which only emitted the three
    known levels).

    Args:
        df: DataFrame potentially containing duplicates.
        level_keys: Mapping of detail_level value -> natural key columns for
            that level (e.g. {"county": [...], "state": [...]}).
        sort_col: Column to use for preferring rows.

    Returns:
        DataFrame with duplicates removed.
    """
    initial_count = df.height
    result_dfs = []

    # Process each detail level separately
    for level, keys in level_keys.items():
        level_df = df.filter(pl.col("detail_level") == level)
        if level_df.height == 0:
            continue

        # Check which key columns exist
        available_keys = [k for k in keys if k in level_df.columns]

        # Add sort key: sort_col with nulls as 0 (so rows with data sort first)
        if sort_col in level_df.columns:
            level_df = level_df.with_columns(
                pl.col(sort_col).fill_null(0).alias("_sort_key")
            )

            # Sort by key columns, then by _sort_key descending
            # This ensures we keep the row with actual data (highest value)
            sorted_df = level_df.sort(
                available_keys + ["_sort_key"],
                descending=[False] * len(available_keys) + [True],
            )

            # Keep first row per key combination (the one with highest value)
            deduped = sorted_df.unique(subset=available_keys, keep="first")

            # Drop sort helper column
            deduped = deduped.drop("_sort_key")
        else:
            # No sort column, just dedupe keeping first
            deduped = level_df.unique(subset=available_keys, keep="first")

        result_dfs.append(deduped)

    if not result_dfs:
        return df

    result = pl.concat(result_dfs, how="diagonal")
    removed_count = initial_count - result.height

    if removed_count > 0:
        logger.info(
            f"Deduplicated {removed_count} rows (source data quality issues: "
            f"renamed schools, typos, duplicate entries)"
        )

    return result


# =============================================================================
# Demographic Subgroup Collision Aggregation
# =============================================================================


def aggregate_demographic_collisions(
    df: pl.DataFrame,
    natural_key_cols: list[str],
    sum_cols: list[str] | None = None,
    weighted_avg_cols: dict[str, str] | None = None,
    mean_cols: list[str] | None = None,
) -> pl.DataFrame:
    """Collapse rows that share a natural key after demographic normalization.

    When multiple raw demographic labels normalize to the same canonical value
    (e.g., two Hispanic subgroups both -> "hispanic"), the resulting rows share
    a natural key but carry different metric values. Per data-cleaning-standards
    section 5, these must be aggregated explicitly — summed for counts, weighted-
    averaged for rates/scores — rather than silently discarded by dedup.

    Rows that are already unique on the natural key pass through unchanged.

    Args:
        df: DataFrame potentially containing collisions.
        natural_key_cols: Columns whose duplicate combinations indicate a collision
            (e.g., ["year", "district_code", "school_code", "demographic",
            "test_component"]). Columns not present in df are skipped.
        sum_cols: Metric columns to sum when collapsing (count-like metrics).
        weighted_avg_cols: Metric columns to weighted-average when collapsing.
            Keys are metric column names; values are the weight column name
            (e.g., {"avg_score": "num_tested"}). The weight column is typically
            a count and must also appear in `sum_cols` so it survives the aggregation.
        mean_cols: Metric columns to simple-average (use only when no weight
            column is available; prefer weighted_avg_cols).

    Returns:
        DataFrame with colliding rows collapsed. Logs the number of keys that
        had collisions and a sample.
    """
    sum_cols = sum_cols or []
    weighted_avg_cols = weighted_avg_cols or {}
    mean_cols = mean_cols or []

    # Restrict to columns actually present so callers can pass a superset.
    keys = [k for k in natural_key_cols if k in df.columns]
    if not keys:
        return df

    # Count how many rows share each natural key. If every group has a single
    # row, there are no collisions and we return the input unchanged.
    group_counts = df.group_by(keys).len().rename({"len": "_collision_count"})
    collisions = group_counts.filter(pl.col("_collision_count") > 1)
    if collisions.height == 0:
        return df

    total_collision_rows = int(
        collisions.select(pl.col("_collision_count").sum()).item()
    )
    sample = (
        collisions.sort("_collision_count", descending=True)
        .head(5)
        .select(keys + ["_collision_count"])
        .to_dicts()
    )
    logger.info(
        f"Demographic subgroup collisions detected: {collisions.height} key(s) "
        f"cover {total_collision_rows:,} rows. Aggregating. Sample: {sample}"
    )

    # Build aggregation expressions. Weighted averages are computed as
    # sum(metric * weight) / sum(weight), treating nulls as missing data.
    agg_exprs: list[pl.Expr] = []
    for col in sum_cols:
        if col in df.columns:
            agg_exprs.append(pl.col(col).sum().alias(col))

    for metric_col, weight_col in weighted_avg_cols.items():
        if metric_col not in df.columns or weight_col not in df.columns:
            continue
        numerator = (pl.col(metric_col) * pl.col(weight_col)).sum()
        denominator = (
            pl.when(pl.col(metric_col).is_not_null())
            .then(pl.col(weight_col))
            .otherwise(None)
            .sum()
        )
        agg_exprs.append(
            pl.when(denominator > 0)
            .then(numerator / denominator)
            .otherwise(None)
            .alias(metric_col)
        )

    for col in mean_cols:
        if col in df.columns:
            agg_exprs.append(pl.col(col).mean().alias(col))

    # Preserve any remaining columns by taking the first value per group.
    # This covers derived/constant columns that are the same across collisions.
    aggregated_cols = set(sum_cols) | set(weighted_avg_cols) | set(mean_cols)
    passthrough_cols = [
        c for c in df.columns if c not in keys and c not in aggregated_cols
    ]
    for col in passthrough_cols:
        agg_exprs.append(pl.col(col).first().alias(col))

    result = df.group_by(keys).agg(agg_exprs).select(df.columns)
    return result


# =============================================================================
# Detail-Level Geography Nulling
# =============================================================================


def null_aggregate_geography(
    df: pl.DataFrame,
    detail_level_col: str,
    geography_rules: dict[str, dict[str, str]],
) -> pl.DataFrame:
    """Null geography columns at aggregate detail levels per the domain rules.

    Applies the same rule structure used by validators.check_geography_nulling,
    so transform output and validation expectations cannot diverge.

    The `geography_rules` dict maps each detail level name to a dict of
    {column_name: "null" | "not_null"}. Columns marked "null" for a given
    detail level are set to NULL on rows at that level. "not_null" rules are
    not enforced here (validators handle that); this helper only nulls.

    Args:
        df: DataFrame with a detail_level_col column.
        detail_level_col: Name of the column holding the detail level string
            (typically "detail_level").
        geography_rules: Mapping of detail level -> {col: "null" | "not_null"}.
            Accepts both singular ("state", "district", "school") and plural
            ("states", "districts", "schools") keys for convenience — see
            EDUCATION_DOMAIN_CONFIG which uses plural keys.

    Returns:
        DataFrame with geography columns nulled at the appropriate detail levels.
    """
    if detail_level_col not in df.columns:
        return df

    # Normalize rule keys so callers can pass EDUCATION_DOMAIN_CONFIG directly
    # (plural "states") or domain-specific singular names ("state"). An explicit
    # map, not `[:-1]` stripping — "counties"[:-1] is "countie", which would
    # silently never match county rows.
    plural_to_singular = {
        "states": "state",
        "districts": "district",
        "schools": "school",
        "counties": "county",
    }
    normalized_rules: dict[str, dict[str, str]] = {}
    for level, cols in geography_rules.items():
        normalized_rules[level] = cols
        singular = plural_to_singular.get(level)
        if singular is None and level.endswith("s"):
            singular = level[:-1]
        if singular:
            normalized_rules[singular] = cols

    exprs: list[pl.Expr] = []
    seen_cols: set[str] = set()
    for level, cols in normalized_rules.items():
        for col, rule in cols.items():
            if rule != "null" or col not in df.columns or col in seen_cols:
                continue
            # A single CASE expression per column covers all levels that null it.
            levels_nulling_this_col = [
                lvl
                for lvl, rules in normalized_rules.items()
                if rules.get(col) == "null"
            ]
            exprs.append(
                pl.when(pl.col(detail_level_col).is_in(levels_nulling_this_col))
                .then(None)
                .otherwise(pl.col(col))
                .alias(col)
            )
            seen_cols.add(col)

    if not exprs:
        return df
    return df.with_columns(exprs)


# =============================================================================
# Era Detection
# =============================================================================


def detect_era_by_columns(
    df: pl.DataFrame,
    era_signatures: dict[str, list[str]],
) -> str | None:
    """Return the first era whose signature columns are all present in df.

    Era detection by column presence is more resilient than year-range detection
    because source systems occasionally ship a new schema mid-year or republish
    old years in a new format.

    Args:
        df: DataFrame to inspect.
        era_signatures: Ordered mapping of era name to the list of column names
            that must all be present for that era. Ordering matters — the first
            matching era wins, so put more-specific signatures first.

    Returns:
        The first matching era name, or None if no era matches.
    """
    cols = set(df.columns)
    for era, signature in era_signatures.items():
        if all(c in cols for c in signature):
            return era
    return None


# =============================================================================
# Name Title Casing
# =============================================================================

_PROPER_NOUN_OVERRIDES_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "reference"
    / "proper_noun_overrides.json"
)


def _load_proper_noun_overrides() -> dict[str, str]:
    """Load proper-noun overrides from data/reference/proper_noun_overrides.json.

    Falls back to an empty dict if the file is missing so utility imports never
    fail in environments without the data directory (e.g., Lambda bundles).
    """
    try:
        raw = json.loads(_PROPER_NOUN_OVERRIDES_PATH.read_text())
    except FileNotFoundError:
        logger.warning(
            "Proper noun overrides file not found at %s; title-casing will not "
            "apply overrides.",
            _PROPER_NOUN_OVERRIDES_PATH,
        )
        return {}
    return dict(raw.get("overrides", {}))


_PROPER_NOUN_OVERRIDES: dict[str, str] = _load_proper_noun_overrides()


def title_case_name(s: pl.Expr) -> pl.Expr:
    """Apply title case while preserving known proper-noun capitalisation.

    Polars' built-in to_titlecase() lowercases all characters after the first
    in each word, corrupting mixed-case proper nouns like "DeKalb" or acronyms
    like "STEAM". This function applies title case then restores known overrides.

    Args:
        s: Polars expression containing name strings (district_name, school_name).

    Returns:
        Expression with title case applied and proper nouns restored.
    """
    result = s.str.strip_chars().str.to_titlecase()
    for wrong, right in _PROPER_NOUN_OVERRIDES.items():
        result = result.str.replace_all(wrong, right, literal=True)
    # Fix possessive / contracted apostrophes. polars `str.to_titlecase`
    # capitalizes the letter after an apostrophe ("Eagle's" → "Eagle'S"),
    # which is wrong for English possessives and contractions. Lowercase
    # the post-apostrophe letter via a Python UDF (polars's Rust regex
    # has no case-modifier replacement syntax).
    result = result.map_elements(_lowercase_after_apostrophe, return_dtype=pl.Utf8)
    return result


def _lowercase_after_apostrophe(value: str | None) -> str | None:
    """Lowercase the letter directly following an apostrophe.

    Handles single-letter possessives (`'S` → `'s`) and multi-letter
    contractions (`'Ll` → `'ll`, `'Ve` → `'ve`, `'Re` → `'re`,
    `'Em` → `'em`). Used by `title_case_name` to undo polars's
    `to_titlecase` over-capitalization of post-apostrophe letters.
    """
    if value is None:
        return None
    return _APOSTROPHE_CASE_RE.sub(
        lambda m: f"{m.group(1)}'{m.group(2).lower()}", value
    )


_APOSTROPHE_CASE_RE = re.compile(r"([A-Za-z])'([A-Z][a-z]?)")


# =============================================================================
# Transform Manifest
# =============================================================================


@dataclass
class MetricStats:
    """Summary statistics for a single metric column in a single year.

    Attributes:
        non_null_count: Number of non-null values.
        null_count: Number of null values.
        null_pct: Fraction of values that are null (0.0-1.0).
        min_val: Minimum non-null value, or None if all null.
        max_val: Maximum non-null value, or None if all null.
        mean_val: Mean of non-null values, or None if all null.
    """

    non_null_count: int
    null_count: int
    null_pct: float
    min_val: float | None
    max_val: float | None
    mean_val: float | None

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "non_null_count": self.non_null_count,
            "null_count": self.null_count,
            "null_pct": round(self.null_pct, 4),
            "min_val": self.min_val,
            "max_val": self.max_val,
            "mean_val": round(self.mean_val, 4) if self.mean_val is not None else None,
        }


@dataclass
class CategoricalMapping:
    """Records what a categorical recoding map did at runtime.

    Captures the declared map, the actual values observed in bronze and gold,
    and any bronze values that were not covered by the map.

    Attributes:
        map_used: The recoding dictionary applied (bronze_value -> gold_value).
        bronze_values_seen: Distinct non-null bronze values actually observed.
        gold_values_produced: Distinct non-null gold values actually produced.
        unmapped_count: Number of distinct bronze values not in the map.
        unmapped_values: The specific bronze values not in the map.
    """

    map_used: dict[str, str]
    bronze_values_seen: list[str]
    gold_values_produced: list[str]
    unmapped_count: int
    unmapped_values: list[str]

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "map_used": self.map_used,
            "bronze_values_seen": sorted(self.bronze_values_seen),
            "gold_values_produced": sorted(self.gold_values_produced),
            "unmapped_count": self.unmapped_count,
            "unmapped_values": sorted(self.unmapped_values),
        }


@dataclass
class TransformManifest:
    """Records what a transform.py actually did at runtime.

    This manifest is the contract between the transform and the data-review
    skill. It captures categorical mappings applied, metric summary statistics,
    row flow, and file processing details so the review can systematically
    verify 100% of recodings instead of spot-checking a few entities.

    Usage in transform.py::

        manifest = TransformManifest(
            topic="act_scores",
            bronze_dir=BRONZE_DIR,
            gold_dir=GOLD_DIR,
        )

        # Per-file, after reading bronze and applying a categorical map:
        manifest.record_bronze(year, df.height)
        manifest.record_categorical(
            "test_component", TEST_COMPONENT_MAP,
            bronze_series=df["TEST_CMPNT_TYP_CD"],
            gold_series=result["test_component"],
        )

        # Once in main(), after harmonize + concat + dedup + geography nulling
        # and just before export — so gold counts reflect what actually lands
        # on disk (not a pre-dedup intermediate state):
        manifest.record_gold_from_dataframe(combined)
        manifest.compute_metric_stats(combined, ["num_tested", "avg_score"])
        manifest.write(GOLD_DIR)

    Attributes:
        topic: The topic name (e.g., "act_scores").
        bronze_dir: Path to the bronze data directory.
        gold_dir: Path to the gold data directory.
        tracker: Composed RowCountTracker for bronze/gold/filtered counts.
        files_processed: List of dicts describing each bronze file processed.
        categorical_mappings: Column name -> CategoricalMapping for each
            categorical recoding applied.
        metric_stats: Column name -> year -> MetricStats for each metric.
    """

    topic: str
    bronze_dir: Path
    gold_dir: Path
    tracker: RowCountTracker = field(default_factory=RowCountTracker)
    files_processed: list[dict] = field(default_factory=list)
    categorical_mappings: dict[str, CategoricalMapping] = field(default_factory=dict)
    metric_stats: dict[str, dict[int, MetricStats]] = field(default_factory=dict)
    read_loss_events: list[dict] = field(default_factory=list)
    masked_values: list[dict] = field(default_factory=list)
    reclassified_events: list[dict] = field(default_factory=list)

    # --- Convenience delegates to RowCountTracker ---

    def record_bronze(self, year: int, count: int) -> None:
        """Record bronze row count for a year. Delegates to tracker."""
        self.tracker.record_bronze(year, count)

    def record_filtered(self, year: int, count: int, reason: str) -> None:
        """Record an explicit filter/dedup event. Delegates to tracker.

        Lets unpivot/expand transforms surface intentional row removal in the
        manifest even though the derived `bronze - gold` figure is 0. See
        `RowCountTracker.record_filtered`.
        """
        self.tracker.record_filtered(year, count, reason)

    def record_gold_from_dataframe(
        self,
        df: pl.DataFrame,
        year_col: str = "year",
    ) -> None:
        """Populate gold row counts from the final combined DataFrame.

        Call once in main() after dedup/geography-nulling and before export.
        Delegates to tracker.
        """
        self.tracker.record_gold_from_dataframe(df, year_col=year_col)

    def record_read_loss(
        self,
        year: int,
        file: str,
        raw_rows: int,
        parsed_rows: int,
        note: str | None = None,
    ) -> None:
        """Record read-time row loss for a bronze file (raw > parsed).

        Call with the loss dict from ``read_bronze_file(..., return_loss=True)``.
        No-op when nothing was lost. Any recorded loss is a blocking finding
        at data-review time unless the event carries a ``note`` explaining why
        the loss is legitimate (e.g. quoted multi-line fields inflating the
        raw line count).
        """
        if parsed_rows >= raw_rows:
            return
        event = {
            "year": int(year),
            "file": str(file),
            "raw_rows": int(raw_rows),
            "parsed_rows": int(parsed_rows),
            "lost_rows": int(raw_rows - parsed_rows),
        }
        if note:
            event["note"] = str(note)
        self.read_loss_events.append(event)
        logger.warning(
            f"Read loss in {file} (year {year}): raw={raw_rows:,} "
            f"parsed={parsed_rows:,} lost={raw_rows - parsed_rows:,}"
            + (f" — {note}" if note else "")
        )

    def record_masked(
        self,
        column: str,
        count: int,
        reason: str,
        years: list[int] | None = None,
    ) -> None:
        """Record a §4b known-bad-value mask (impossible values set to NULL).

        Makes masking derive-from-artifacts: the data review verifies masked
        counts from the manifest instead of scraping runtime logs. Call once
        per `_null_*` helper application with the number of values masked.
        """
        if count <= 0:
            return
        event = {"column": str(column), "count": int(count), "reason": str(reason)}
        if years:
            event["years"] = sorted(int(y) for y in years)
        self.masked_values.append(event)
        logger.warning(
            f"§4b mask: {column} — {count:,} value(s) NULLed ({reason})"
            + (f" years={event.get('years')}" if years else "")
        )

    def record_reclassified(
        self,
        year: int,
        count: int,
        reason: str,
    ) -> None:
        """Record rows whose detail level / identity was repaired in place.

        Reclassified rows are neither filtered nor masked, so without this
        they leave no artifact trace — only log lines. Recording them lets
        the data review verify repairs from the manifest.
        """
        if count <= 0:
            return
        self.reclassified_events.append(
            {"year": int(year), "count": int(count), "reason": str(reason)}
        )
        logger.info(f"Year {year}: Reclassified {count:,} row(s) ({reason})")

    # --- File recording ---

    def record_file(
        self,
        path: Path,
        year: int,
        era: str,
        bronze_rows: int,
        bronze_columns: list[str],
    ) -> None:
        """Record a bronze file that was processed.

        Args:
            path: Path to the bronze file.
            year: Data year extracted from the file.
            era: Era identifier (e.g., "era_3").
            bronze_rows: Number of rows in the bronze file.
            bronze_columns: Column names in the bronze file.
        """
        self.files_processed.append(
            {
                "file": path.name,
                "year": year,
                "era": era,
                "bronze_rows": bronze_rows,
                "bronze_columns": bronze_columns,
            }
        )

    # --- Categorical mapping recording ---

    def record_categorical(
        self,
        column: str,
        map_dict: dict[str, str],
        bronze_series: pl.Series,
        gold_series: pl.Series,
    ) -> None:
        """Record what a categorical recoding map did on actual data.

        Call this after applying a recoding map. Pass the raw bronze Series
        (before mapping) and the gold Series (after mapping) so the manifest
        captures actual observed values, not just declared intent.

        When called multiple times for the same column (e.g., across eras),
        values are merged — bronze_values_seen and gold_values_produced
        accumulate across all calls.

        Args:
            column: Gold column name (e.g., "test_component").
            map_dict: The recoding dictionary that was applied.
            bronze_series: The raw Polars Series before mapping.
            gold_series: The mapped Polars Series after mapping.
        """
        bronze_vals = set(bronze_series.drop_nulls().unique().sort().to_list())
        gold_vals = set(gold_series.drop_nulls().unique().sort().to_list())

        # Bronze values not covered by the map
        bronze_str_vals = {str(v) for v in bronze_vals}
        map_keys_upper = {k.upper(): k for k in map_dict}
        unmapped = {
            v
            for v in bronze_str_vals
            if v not in map_dict and v.upper() not in map_keys_upper
        }

        if column in self.categorical_mappings:
            # Merge with existing mapping from a previous era
            existing = self.categorical_mappings[column]
            merged_bronze = set(existing.bronze_values_seen) | bronze_str_vals
            merged_gold = set(existing.gold_values_produced) | {
                str(v) for v in gold_vals
            }
            merged_unmapped = set(existing.unmapped_values) | unmapped
            self.categorical_mappings[column] = CategoricalMapping(
                map_used=existing.map_used | map_dict,
                bronze_values_seen=sorted(merged_bronze),
                gold_values_produced=sorted(merged_gold),
                unmapped_count=len(merged_unmapped),
                unmapped_values=sorted(merged_unmapped),
            )
        else:
            self.categorical_mappings[column] = CategoricalMapping(
                map_used=dict(map_dict),
                bronze_values_seen=sorted(bronze_str_vals),
                gold_values_produced=sorted(str(v) for v in gold_vals),
                unmapped_count=len(unmapped),
                unmapped_values=sorted(unmapped),
            )

        if unmapped:
            logger.warning(
                f"Categorical '{column}': {len(unmapped)} unmapped bronze values: "
                f"{sorted(unmapped)}"
            )

    # --- Metric stats ---

    def compute_metric_stats(
        self,
        df: pl.DataFrame,
        metric_columns: list[str],
    ) -> None:
        """Compute per-year summary statistics for metric columns.

        Call this once on the final combined DataFrame (after harmonize +
        deduplicate, before export). Automatically iterates all metric columns
        and all years.

        Args:
            df: The final combined DataFrame with a "year" column.
            metric_columns: List of metric column names to compute stats for.
        """
        years = sorted(df["year"].unique().to_list())

        for col in metric_columns:
            if col not in df.columns:
                logger.warning(f"Metric column '{col}' not found in DataFrame")
                continue

            self.metric_stats[col] = {}

            for year in years:
                year_series = df.filter(pl.col("year") == year)[col]
                total = year_series.len()
                null_count = year_series.null_count()
                non_null = total - null_count
                null_pct = null_count / total if total > 0 else 0.0

                if non_null > 0:
                    vals = year_series.drop_nulls()
                    min_val = vals.min()
                    max_val = vals.max()
                    mean_val = vals.mean()
                else:
                    min_val = None
                    max_val = None
                    mean_val = None

                self.metric_stats[col][year] = MetricStats(
                    non_null_count=non_null,
                    null_count=null_count,
                    null_pct=null_pct,
                    min_val=float(min_val) if min_val is not None else None,
                    max_val=float(max_val) if max_val is not None else None,
                    mean_val=float(mean_val) if mean_val is not None else None,
                )

    # --- Serialization ---

    def to_dict(self) -> dict:
        """Serialize the full manifest to a plain dictionary.

        Per-year `filtered` and `total_filtered` are derived as
        `max(bronze - gold, 0)` so the manifest captures row loss from
        every source (explicit filters, dedup, collision aggregation).

        Explicit filter/dedup events recorded via `record_filtered()` are
        surfaced additively: each per-year entry gains a `filtered_explicit`
        count, and `row_counts` gains `total_filtered_explicit` plus a
        `filtered_explicit_by_reason` breakdown. These appear only when events
        were recorded, so the JSON shape is unchanged for transforms that
        don't use the feature. The derived `filtered` / `total_filtered`
        fields are left untouched for backward compatibility.
        """
        filtered_by_year = self.tracker.filtered_by_year()
        explicit_by_year = self.tracker.filtered_explicit_by_year()
        explicit_by_reason = self.tracker.filtered_explicit_by_reason()
        total_bronze = sum(self.tracker.bronze_rows_by_year.values())
        total_gold = sum(self.tracker.gold_rows_by_year.values())
        row_counts: dict = {
            "total_bronze": total_bronze,
            "total_gold": total_gold,
            "total_filtered": max(total_bronze - total_gold, 0),
            "years_processed": len(self.tracker.bronze_rows_by_year),
            "by_year": {
                str(year): {
                    "bronze": self.tracker.bronze_rows_by_year.get(year, 0),
                    "gold": self.tracker.gold_rows_by_year.get(year, 0),
                    "filtered": filtered_by_year.get(year, 0),
                    "filtered_explicit": explicit_by_year.get(year, 0),
                    "expansion_factor": self.tracker.expansion_factors.get(year),
                }
                for year in sorted(
                    set(self.tracker.bronze_rows_by_year)
                    | set(self.tracker.gold_rows_by_year)
                    | set(explicit_by_year)
                )
            },
        }
        # Only emit the explicit-filter rollups when events were recorded so
        # the manifest shape is unchanged for transforms that don't use them.
        if self.tracker.filtered_events:
            row_counts["total_filtered_explicit"] = sum(explicit_by_year.values())
            row_counts["filtered_explicit_by_reason"] = explicit_by_reason
        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "topic": self.topic,
            "files_processed": self.files_processed,
            "row_counts": row_counts,
            "categorical_mappings": {
                col: mapping.to_dict()
                for col, mapping in sorted(self.categorical_mappings.items())
            },
            "metric_stats": {
                col: {
                    str(year): stats.to_dict()
                    for year, stats in sorted(year_stats.items())
                }
                for col, year_stats in sorted(self.metric_stats.items())
            },
        }
        # Only emit read_loss / masked_values when events were recorded so the
        # manifest shape is unchanged for transforms that don't use them.
        if self.read_loss_events:
            result["read_loss"] = self.read_loss_events
        if self.masked_values:
            result["masked_values"] = self.masked_values
        if self.reclassified_events:
            result["reclassified"] = self.reclassified_events
        return result

    def write(self, output_dir: Path, strict_unmapped: bool = True) -> Path:
        """Write the manifest as JSON to the gold directory.

        Args:
            output_dir: Path to the gold data directory.
            strict_unmapped: If True (default), raise ValueError after writing
                when any categorical mapping has `unmapped_count > 0`. Per
                data-cleaning-standards §14, unmapped bronze values mean the
                recoding map is incomplete and gold is wrong — fix the map and
                re-run. Pass False only for inspection/debugging scripts.

        Returns:
            Path to the written manifest file.

        Raises:
            ValueError: If strict_unmapped=True and any categorical has
                unmapped_count > 0. The manifest is written first so the user
                can inspect the unmapped values.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = output_dir / "_transform_manifest.json"
        manifest_path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n"
        )
        logger.info(f"Wrote transform manifest to {manifest_path}")

        if strict_unmapped:
            unmapped = {
                col: mapping.unmapped_values
                for col, mapping in self.categorical_mappings.items()
                if mapping.unmapped_count > 0
            }
            if unmapped:
                details = "; ".join(
                    f"{col}={values}" for col, values in sorted(unmapped.items())
                )
                raise ValueError(
                    f"Transform has unmapped categorical values — fix the "
                    f"recoding maps and re-run. Unmapped: {details}. "
                    f"See {manifest_path} for full report."
                )

        return manifest_path
