"""Gold data validation utilities.

This module provides reusable validation checks for gold Parquet fact tables.
Each check function returns a CheckResult with pass/fail/warning status.
The ValidationRunner orchestrates all checks and produces a ValidationReport.

Schema source: the ODCS contract (``contracts/{main}/{topic}.odcs.yaml``) is the
single schema source. ``check_contract_parquet_schema`` verifies the on-disk
parquet matches the contract's declared columns (names + order), and the
percentage-scale classification is read back from the contract's per-column
``unit`` markers (NOT declared in ``TOPIC_CONFIG``).

Percentage scale: per data-cleaning-standards §4, percentage columns split into
two buckets, authored in the transform's ``unit`` key and emitted as a contract
``unit`` custom property:

- **Bounded proportions** (``unit: proportion``) must satisfy 0 ≤ value ≤ 1.
  Anything above 1 is a bug — the source likely uses 0-100 scaling.
- **Decimal ratios** (``unit: ratio``) are divided by 100 from a 0-100
  bronze source but may legitimately exceed 1 when the real-world numerator
  can exceed the denominator (mobility rates, participation in early years,
  salary/expense fractions of a chosen base, etc.). Still flagged if median
  suggests un-scaled 0-100 values.

Exempt columns (scores, ratings, percentile ranks, counts, currency) carry a
non-percentage ``unit`` (or none) and stay listed in
``TOPIC_CONFIG['exempt_pct_columns']`` so they are excluded from the scale check.

Usage:
    Per-topic validate.py scripts define topic-specific config and delegate
    to ValidationRunner. The pct bounded/ratio split is NOT declared here —
    it comes from the contract:

    ```python
    from src.utils.validators import ValidationRunner, EDUCATION_DOMAIN_CONFIG

    runner = ValidationRunner(
        gold_dir=Path("data/gold/education/act_scores"),
        domain_config=EDUCATION_DOMAIN_CONFIG,
        topic_config={
            "metric_columns": ["avg_score", "num_tested"],
            "exempt_pct_columns": ["avg_score"],
            "categorical_columns": ["test_component"],
            "type_spec": {"year": pl.Int32, ...},
        },
    )
    report = runner.run_all()
    report.write_json()
    ```
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import polars as pl
import yaml

from src.utils import contract_reader
from src.utils._checks import CheckResult, check_demographics
from src.utils.contract_emitter import contract_path_for
from src.utils.demographics import DEMOGRAPHIC_CATEGORIES
from src.utils.readers import SUPPRESSION_VALUES
from src.utils.vocabulary import vocabulary_violations

# Re-exported so existing code that does
# `from src.utils.validators import CheckResult, check_demographics` keeps
# working. The canonical definitions live in src.utils._checks.
__all__ = [
    "CheckResult",
    "check_demographics",
    # the remaining public symbols are defined below
]

logger = logging.getLogger(__name__)

# Snake case pattern: lowercase letters, digits, underscores only.
# First character may be a letter or a digit so canonical categorical values
# like `4_year`, `5_year`, or `9th_grade_literature_and_composition` are
# accepted — these read as snake_case and are unambiguous despite the leading
# digit. Column names are not affected in practice (no column in the project
# starts with a digit); this regex is shared with the column-naming check.
_SNAKE_CASE_RE = re.compile(r"^[a-z0-9][a-z0-9_]*$")

# Patterns that suggest column names contain years (wide-format indicator)
_YEAR_COLUMN_RE = re.compile(r"(^|_)(19|20)\d{2}(_|$)")

# Demographic names whose appearance as a column name suggests wide format.
# Derived from DEMOGRAPHIC_CATEGORIES so new demographics are picked up
# automatically when added to demographics.py. Only race and gender are
# checked since those are the dimensions most commonly seen as column suffixes
# in bronze sources (e.g., `pct_male`, `count_asian`).
_DEMOGRAPHIC_COLUMN_PATTERNS = {
    d for d, cat in DEMOGRAPHIC_CATEGORIES.items() if cat in {"race", "gender"}
}


# =============================================================================
# Domain Configs
# =============================================================================

EDUCATION_DOMAIN_CONFIG: dict = {
    "expected_column_prefix": ["year", "district_code", "school_code"],
    "forbidden_fact_columns": [
        "district_name",
        "school_name",
        "district_census_id",
        "school_year",
        "topic",
        "detail_level",
    ],
    "id_rules": {"district_code": 3, "school_code": 4},
    "detail_level_geography_rules": {
        "states": {"district_code": "null", "school_code": "null"},
        "districts": {"district_code": "not_null", "school_code": "null"},
        "schools": {"district_code": "not_null", "school_code": "not_null"},
    },
}

CRIMINAL_JUSTICE_DOMAIN_CONFIG: dict = {
    "expected_column_prefix": ["year", "county_fips"],
    "forbidden_fact_columns": [
        "county_name",
        "county",
        "topic",
        "detail_level",
    ],
    "id_rules": {"county_fips": 5},
    "detail_level_geography_rules": {
        "states": {"county_fips": "null"},
        "counties": {"county_fips": "not_null"},
        # Federal-district-grain topics (federal_justice/*): the district enum
        # is the geography; there is no county_fips column (the check skips
        # absent columns, so this documents intent and silences the
        # unknown-level warning).
        "federal_districts": {"county_fips": "null"},
    },
}

# Registry of domain configs keyed by main_topic, so contract-driven entry
# points (run_topic_validation, scripts/validate_topic.py) can resolve the
# right domain rules from the gold path alone.
DOMAIN_CONFIGS: dict[str, dict] = {
    "education": EDUCATION_DOMAIN_CONFIG,
    "criminal_justice": CRIMINAL_JUSTICE_DOMAIN_CONFIG,
}


class GoldValidationError(RuntimeError):
    """Raised when gold data fails validation (or its contract is missing)."""


# =============================================================================
# Validation Report
# =============================================================================


@dataclass
class ValidationReport:
    """Aggregated results from all validation checks.

    Attributes:
        topic: Topic identifier (e.g., "act_scores").
        gold_dir: Path to the gold directory that was validated.
        checks: List of individual check results.
        timestamp: ISO timestamp of when the report was generated.
    """

    topic: str
    gold_dir: Path
    checks: list[CheckResult] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def passed(self) -> bool:
        """True if no checks have status 'fail'."""
        return all(c.status != "fail" for c in self.checks)

    @property
    def summary_counts(self) -> dict[str, int]:
        """Count of checks by status."""
        counts: dict[str, int] = {"pass": 0, "fail": 0, "warning": 0}
        for c in self.checks:
            counts[c.status] = counts.get(c.status, 0) + 1
        return counts

    def to_dict(self) -> dict:
        """Serialize the full report to a dictionary."""
        counts = self.summary_counts
        return {
            "topic": self.topic,
            "gold_dir": str(self.gold_dir),
            "timestamp": self.timestamp,
            "passed": self.passed,
            "summary": counts,
            "checks": [c.to_dict() for c in self.checks],
        }

    def write_json(self, path: Path | None = None) -> Path:
        """Write report to JSON file.

        Args:
            path: Output path. Defaults to {gold_dir}/_validation.json.

        Returns:
            Path to the written file.
        """
        if path is None:
            path = self.gold_dir / "_validation.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n")
        counts = self.summary_counts
        logger.info(
            "Validation: %d passed, %d failed, %d warnings -> %s",
            counts["pass"],
            counts["fail"],
            counts["warning"],
            path,
        )
        return path


# =============================================================================
# Individual Check Functions
# =============================================================================


def check_column_naming(df: pl.DataFrame) -> CheckResult:
    """Verify all column names are snake_case."""
    bad = [c for c in df.columns if not _SNAKE_CASE_RE.match(c)]
    if bad:
        return CheckResult(
            name="column_naming",
            status="fail",
            message=f"{len(bad)} column(s) are not snake_case",
            details=bad,
        )
    return CheckResult(
        name="column_naming",
        status="pass",
        message="All columns are snake_case",
    )


def check_column_order(
    df: pl.DataFrame,
    expected_prefix: list[str],
) -> CheckResult:
    """Verify columns start with the expected prefix order.

    Args:
        df: DataFrame to check.
        expected_prefix: Expected leading columns
            (e.g., ["year", "district_code", "school_code"]).
    """
    # Only check columns that exist in this file.
    # State-level files may not have district_code/school_code.
    present_prefix = [c for c in expected_prefix if c in df.columns]
    actual_prefix = df.columns[: len(present_prefix)]

    if actual_prefix != present_prefix:
        return CheckResult(
            name="column_order",
            status="fail",
            message="Column order does not match expected prefix",
            details=[
                f"Expected: {present_prefix}",
                f"Actual:   {actual_prefix}",
            ],
        )
    return CheckResult(
        name="column_order",
        status="pass",
        message="Column order matches expected prefix",
    )


def check_star_schema_compliance(
    df: pl.DataFrame,
    forbidden_columns: list[str],
) -> CheckResult:
    """Verify no name/crosswalk/excluded columns appear in fact table.

    Args:
        df: DataFrame to check.
        forbidden_columns: Column names that should not be in fact tables.
    """
    found = [c for c in forbidden_columns if c in df.columns]
    if found:
        return CheckResult(
            name="star_schema_compliance",
            status="fail",
            message=f"{len(found)} forbidden column(s) in fact table",
            details=found,
        )
    return CheckResult(
        name="star_schema_compliance",
        status="pass",
        message="No forbidden columns in fact table",
    )


def check_data_types(
    df: pl.DataFrame,
    type_spec: dict[str, pl.DataType],
) -> CheckResult:
    """Verify each column in type_spec exists and matches its expected dtype.

    A column declared in `type_spec` but absent from the DataFrame is a failure:
    it signals schema drift between transform and validate. Previously this case
    was silently skipped, which let renamed-or-removed columns (e.g. the
    ``no_positive_movement_pct`` -> ``pct_no_positive_movement`` rename) slip
    through validation while breaking downstream API consumers that trust
    metadata.

    Args:
        df: DataFrame to check.
        type_spec: Mapping of column name to expected dtype.
    """
    mismatches: list[str] = []
    missing: list[str] = []
    for col, expected_dtype in type_spec.items():
        if col not in df.columns:
            missing.append(col)
            continue
        actual = df[col].dtype
        if actual != expected_dtype:
            mismatches.append(f"{col}: expected {expected_dtype}, got {actual}")

    if missing or mismatches:
        details = [f"missing: {c}" for c in missing] + mismatches
        msg_parts = []
        if missing:
            msg_parts.append(f"{len(missing)} expected column(s) missing")
        if mismatches:
            msg_parts.append(f"{len(mismatches)} column(s) have wrong dtype")
        return CheckResult(
            name="data_types",
            status="fail",
            message="; ".join(msg_parts),
            details=details,
        )
    return CheckResult(
        name="data_types",
        status="pass",
        message="All column dtypes match specification",
    )


def _contract_property_names(contract: dict) -> list[str]:
    """Return the declared column names, in order, from an ODCS contract."""
    schema = contract.get("schema") or []
    if not schema:
        return []
    return [p["name"] for p in (schema[0].get("properties") or []) if "name" in p]


def contract_path_for_gold_dir(gold_dir: Path) -> Path:
    """Map a gold topic dir (``data/gold/{main}/{topic}``) to its contract path."""
    resolved = gold_dir.resolve()
    return contract_path_for(resolved.parent.name, resolved.name)


def check_contract_parquet_schema(
    gold_dir: Path, contract_path: Path | None = None
) -> CheckResult:
    """Verify every parquet in a topic's gold dir matches the ODCS contract.

    The contract (``contracts/{main}/{topic}.odcs.yaml``) is the schema the API
    registry trusts to drive query construction — column names, logical types,
    and order. If the on-disk parquet diverges (e.g. transform was updated but
    never re-run, or columns reordered) the API will 500. This check compares
    each ``year=*/*.parquet``'s column names + order against the contract's
    ``schema[0].properties[]``. Any mismatch (extras, missing, reorder) fails
    with file-level detail.

    Skipped (warning) when the contract is absent — that is a separate gap,
    surfaced explicitly so it can't masquerade as a pass. (Non-approved topics
    have no committed contract; the transform emits one on its next run.)

    Args:
        gold_dir: Path to the gold topic directory
            (e.g. data/gold/education/ccrpi_progress).
        contract_path: Explicit contract path (defaults to the one derived from
            ``gold_dir``). Useful for tests that build a fixture tree.
    """
    if contract_path is None:
        contract_path = contract_path_for_gold_dir(gold_dir)
    if not contract_path.exists():
        return CheckResult(
            name="contract_parquet_schema",
            status="warning",
            message=f"No contract at {contract_path}",
        )

    try:
        contract = yaml.safe_load(contract_path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        return CheckResult(
            name="contract_parquet_schema",
            status="fail",
            message=f"Failed to read contract: {exc}",
        )

    expected_cols = _contract_property_names(contract)
    if not expected_cols:
        return CheckResult(
            name="contract_parquet_schema",
            status="fail",
            message="contract has no schema properties",
        )
    expected_set = set(expected_cols)

    violations: list[str] = []
    parquet_files = sorted(
        p for p in gold_dir.rglob("*.parquet") if not p.name.startswith("_")
    )
    if not parquet_files:
        return CheckResult(
            name="contract_parquet_schema",
            status="fail",
            message="No parquet files found under gold_dir",
        )

    for path in parquet_files:
        rel = path.relative_to(gold_dir).as_posix()
        # collect_schema() avoids loading row data — schema-only is enough.
        actual_cols = pl.scan_parquet(path).collect_schema().names()
        actual_set = set(actual_cols)

        extras = actual_set - expected_set
        missing = expected_set - actual_set
        if extras or missing:
            parts = []
            if missing:
                parts.append(f"missing={sorted(missing)}")
            if extras:
                parts.append(f"extras={sorted(extras)}")
            violations.append(f"{rel}: column set mismatch ({'; '.join(parts)})")
            # Skip order check when the sets disagree — order diff would be noise.
            continue

        if actual_cols != expected_cols:
            pairs = enumerate(zip(expected_cols, actual_cols, strict=True))
            for i, (exp, got) in pairs:
                if exp != got:
                    violations.append(
                        f"{rel}: column order differs at index {i} "
                        f"(contract={exp!r}, parquet={got!r})"
                    )
                    break

    if violations:
        return CheckResult(
            name="contract_parquet_schema",
            status="fail",
            message=f"{len(violations)} parquet file(s) disagree with the contract",
            details=violations,
        )
    return CheckResult(
        name="contract_parquet_schema",
        status="pass",
        message=f"All {len(parquet_files)} parquet file(s) match the contract",
    )


def check_percentage_scale(
    df: pl.DataFrame,
    pct_columns_bounded: list[str] | None = None,
    pct_columns_ratio: list[str] | None = None,
    exempt_columns: list[str] | None = None,
    pct_columns: list[str] | None = None,
) -> CheckResult:
    """Verify percentage columns follow the bounded vs ratio rules.

    Two heuristics, applied per bucket:
    1. Max check: bounded columns must have max ≤ 1.001 (small float
       tolerance). Ratio columns may exceed 1 legitimately, so the max check
       only fires for clearly-mis-scaled values (max > 100 / median > 1.5).
    2. Median check: median > 1.5 signals the column is still on a 0-100
       scale even when values happen to cluster below 100. Applies to both
       buckets.

    Args:
        df: DataFrame to check.
        pct_columns_bounded: Columns that must satisfy 0 ≤ value ≤ 1.
            Anything above 1.001 is a fail.
        pct_columns_ratio: Columns that were divided by 100 from a 0-100
            source but may legitimately exceed 1. Median check still
            applies — a column whose typical value is far above 1 likely
            never got divided.
        exempt_columns: Columns exempt from this check entirely (scores,
            ratings, percentile ranks — anything not on a 0-1 scale by
            design).
        pct_columns: Deprecated. Treated as bounded for backward compat.
    """
    bounded = list(pct_columns_bounded or [])
    if pct_columns:
        # Legacy callers passed all percentage columns through pct_columns,
        # which mirrored the old "must be 0-1" behavior. Treat as bounded.
        bounded.extend(c for c in pct_columns if c not in bounded)
    ratio = list(pct_columns_ratio or [])
    exempt = set(exempt_columns or [])

    bounded_to_check = [
        c for c in bounded if c in df.columns and c not in exempt and c not in ratio
    ]
    ratio_to_check = [c for c in ratio if c in df.columns and c not in exempt]

    if not bounded_to_check and not ratio_to_check:
        return CheckResult(
            name="percentage_scale",
            status="pass",
            message="No percentage columns to check",
        )

    bounded_max_tolerance = 1.001
    median_threshold = 1.5  # signals values are still on 0-100 scale.

    violations: list[str] = []

    for col in bounded_to_check:
        non_null = df[col].drop_nulls()
        if non_null.len() == 0:
            continue
        max_val = non_null.max()
        median_val = non_null.median()
        if max_val is not None and max_val > bounded_max_tolerance:
            violations.append(f"{col}: max={max_val} (bounded column, must be 0-1)")
        elif median_val is not None and median_val > median_threshold:
            violations.append(
                f"{col}: median={median_val:.3f} (bounded column appears "
                "to be on 0-100 scale)"
            )

    for col in ratio_to_check:
        non_null = df[col].drop_nulls()
        if non_null.len() == 0:
            continue
        median_val = non_null.median()
        if median_val is not None and median_val > median_threshold:
            # Even ratio columns shouldn't typically sit far above 1.0 —
            # that pattern suggests the divide-by-100 step was missed.
            violations.append(
                f"{col}: median={median_val:.3f} (ratio column, but typical "
                "value > 1.5 suggests un-scaled 0-100 values)"
            )

    if violations:
        return CheckResult(
            name="percentage_scale",
            status="fail",
            message=f"{len(violations)} column(s) failed percentage-scale check",
            details=violations,
        )
    return CheckResult(
        name="percentage_scale",
        status="pass",
        message="All percentage columns pass scale check",
    )


def check_geography_nulling(
    df: pl.DataFrame,
    detail_level: str,
    geography_rules: dict[str, dict[str, str]],
) -> CheckResult:
    """Verify geography columns are NULL where required by detail level.

    Args:
        df: DataFrame for a single detail level file.
        detail_level: The detail level (e.g., "states", "districts", "schools").
        geography_rules: Rules per detail level. Each rule maps column name to
            "null" (must be all NULL) or "not_null" (must have no NULLs).
    """
    if detail_level not in geography_rules:
        return CheckResult(
            name="geography_nulling",
            status="warning",
            message=f"No geography rules for detail level '{detail_level}'",
        )

    rules = geography_rules[detail_level]
    violations = []

    for col, rule in rules.items():
        if col not in df.columns:
            continue
        null_count = df[col].null_count()
        total = df.height

        if rule == "null" and null_count != total:
            non_null = total - null_count
            violations.append(
                f"{col}: expected all NULL for {detail_level}, "
                f"but {non_null} rows have values"
            )
        elif rule == "not_null" and null_count > 0:
            violations.append(
                f"{col}: expected no NULLs for {detail_level}, "
                f"but {null_count} rows are NULL"
            )

    if violations:
        return CheckResult(
            name="geography_nulling",
            status="fail",
            message=f"Geography nulling violations in {detail_level}",
            details=violations,
        )
    return CheckResult(
        name="geography_nulling",
        status="pass",
        message=f"Geography nulling correct for {detail_level}",
    )


def check_id_formatting(
    df: pl.DataFrame,
    id_rules: dict[str, int],
) -> CheckResult:
    """Verify ID columns are strings with correct minimum zero-padding.

    Args:
        df: DataFrame to check.
        id_rules: Mapping of column name to minimum width (e.g., {"district_code": 3}).
    """
    issues = []

    for col, min_width in id_rules.items():
        if col not in df.columns:
            continue

        # Must be string type
        if df[col].dtype != pl.Utf8:
            issues.append(f"{col}: expected Utf8, got {df[col].dtype}")
            continue

        # Check minimum length on non-null values
        non_null = df[col].drop_nulls()
        if non_null.len() == 0:
            continue

        too_short = non_null.filter(non_null.str.len_bytes() < min_width)
        if too_short.len() > 0:
            samples = too_short.unique().head(5).to_list()
            issues.append(
                f"{col}: {too_short.len()} values shorter than {min_width} chars, "
                f"samples: {samples}"
            )

    if issues:
        return CheckResult(
            name="id_formatting",
            status="fail",
            message="ID formatting issues found",
            details=issues,
        )
    return CheckResult(
        name="id_formatting",
        status="pass",
        message="All ID columns correctly formatted",
    )


def check_no_suppression_markers(df: pl.DataFrame) -> CheckResult:
    """Verify no known suppression markers remain in string columns.

    All suppression values should have been converted to NULL during transform.
    """
    # Only check string columns
    string_cols = [c for c in df.columns if df[c].dtype == pl.Utf8]
    found = []

    for col in string_cols:
        values = df[col].drop_nulls().unique().to_list()
        markers = [v for v in values if v in SUPPRESSION_VALUES]
        if markers:
            found.append(f"{col}: {markers}")

    if found:
        return CheckResult(
            name="no_suppression_markers",
            status="fail",
            message="Suppression markers found in string columns",
            details=found,
        )
    return CheckResult(
        name="no_suppression_markers",
        status="pass",
        message="No suppression markers in string columns",
    )


def check_tidy_format(df: pl.DataFrame) -> CheckResult:
    """Heuristic check that data is in long/tidy format.

    Flags column names that contain year patterns or demographic names,
    which suggest the data is still in wide format.
    """
    issues = []

    for col in df.columns:
        if _YEAR_COLUMN_RE.search(col):
            issues.append(f"Column '{col}' contains a year pattern (wide format?)")

        # Check if column name matches a demographic category
        col_lower = col.lower()
        for demo in _DEMOGRAPHIC_COLUMN_PATTERNS:
            if (
                col_lower == demo
                or col_lower.startswith(f"{demo}_")
                or col_lower.endswith(f"_{demo}")
            ):
                # Skip known valid columns
                if col in ("demographic",):
                    continue
                issues.append(
                    f"Column '{col}' matches demographic "
                    f"pattern '{demo}' (wide format?)"
                )

    if issues:
        return CheckResult(
            name="tidy_format",
            status="warning",
            message="Possible wide-format columns detected",
            details=issues,
        )
    return CheckResult(
        name="tidy_format",
        status="pass",
        message="No wide-format column patterns detected",
    )


def check_no_empty_files(gold_dir: Path) -> CheckResult:
    """Verify no parquet files in the gold directory have 0 rows."""
    empty_files = []

    for pq_file in sorted(gold_dir.rglob("*.parquet")):
        try:
            df = pl.read_parquet(pq_file)
            if df.height == 0:
                empty_files.append(str(pq_file.relative_to(gold_dir)))
        except Exception as e:
            empty_files.append(f"{pq_file.relative_to(gold_dir)} (read error: {e})")

    if empty_files:
        return CheckResult(
            name="no_empty_files",
            status="fail",
            message=f"{len(empty_files)} empty parquet file(s)",
            details=empty_files,
        )
    return CheckResult(
        name="no_empty_files",
        status="pass",
        message="All parquet files have data",
    )


def check_year_non_null(df: pl.DataFrame) -> CheckResult:
    """Verify year column has no NULL values."""
    if "year" not in df.columns:
        return CheckResult(
            name="year_non_null",
            status="fail",
            message="No 'year' column found",
        )

    null_count = df["year"].null_count()
    if null_count > 0:
        return CheckResult(
            name="year_non_null",
            status="fail",
            message=f"Year column has {null_count} NULL values",
        )
    return CheckResult(
        name="year_non_null",
        status="pass",
        message="Year column has no NULLs",
    )


def check_null_rate_spikes(
    df: pl.DataFrame,
    metric_columns: list[str],
    threshold: float = 0.2,
) -> CheckResult:
    """Flag per-year NULL rate spikes that exceed threshold above the median.

    A spike of >20pp above the median NULL rate suggests data loss for that year.

    Args:
        df: DataFrame to check.
        metric_columns: Columns to check for NULL rate spikes.
        threshold: Maximum acceptable deviation above median (default 0.2 = 20pp).
    """
    cols_to_check = [c for c in metric_columns if c in df.columns]
    if not cols_to_check or "year" not in df.columns:
        return CheckResult(
            name="null_rate_spikes",
            status="pass",
            message="No metric columns or year column to check",
        )

    spikes = []
    years = sorted(df["year"].unique().to_list())

    for col in cols_to_check:
        null_rates = {}
        for year in years:
            year_df = df.filter(pl.col("year") == year)
            total = year_df.height
            if total == 0:
                continue
            null_count = year_df[col].null_count()
            null_rates[year] = null_count / total

        if not null_rates:
            continue

        rates = list(null_rates.values())
        rates.sort()
        median_rate = rates[len(rates) // 2]

        for year, rate in null_rates.items():
            if rate - median_rate > threshold:
                spikes.append(
                    f"{col} year={year}: null_rate={rate:.1%} "
                    f"(median={median_rate:.1%}, delta={rate - median_rate:.1%})"
                )

    if spikes:
        return CheckResult(
            name="null_rate_spikes",
            status="warning",
            message=f"{len(spikes)} NULL rate spike(s) detected",
            details=spikes,
        )
    return CheckResult(
        name="null_rate_spikes",
        status="pass",
        message="No NULL rate spikes above threshold",
    )


def check_categorical_normalization(
    df: pl.DataFrame,
    categorical_columns: list[str],
) -> CheckResult:
    """Verify all values in categorical columns are snake_case.

    Args:
        df: DataFrame to check.
        categorical_columns: Columns whose values should be snake_case.
    """
    issues = []

    for col in categorical_columns:
        if col not in df.columns:
            continue
        # snake_case normalization targets string vocabularies. A boolean
        # categorical (e.g. an is_* flag) is normalized by construction —
        # its Python repr (True/False) would false-positive the regex.
        if df[col].dtype == pl.Boolean:
            continue
        values = df[col].drop_nulls().unique().to_list()
        bad = [v for v in values if not _SNAKE_CASE_RE.match(str(v))]
        if bad:
            issues.append(f"{col}: non-snake_case values: {bad}")

    if issues:
        return CheckResult(
            name="categorical_normalization",
            status="fail",
            message="Categorical values not normalized to snake_case",
            details=issues,
        )
    return CheckResult(
        name="categorical_normalization",
        status="pass",
        message="All categorical values are snake_case",
    )


def check_canonical_vocabulary(df: pl.DataFrame) -> CheckResult:
    """Verify no column uses a forbidden variant of a canonical name.

    The registry lives in ``src/utils/vocabulary.py`` (the machine-readable
    half of data-cleaning-standards §16).
    """
    hits = vocabulary_violations(df.columns)
    if hits:
        return CheckResult(
            name="canonical_vocabulary",
            status="fail",
            message=f"{len(hits)} column(s) use non-canonical names",
            details=[f"{col}: use '{canonical}'" for col, canonical in hits],
        )
    return CheckResult(
        name="canonical_vocabulary",
        status="pass",
        message="All column names follow the canonical vocabulary",
    )


def check_grain_uniqueness(df: pl.DataFrame, grain: list[str]) -> CheckResult:
    """Verify gold has exactly one row per contract-declared grain tuple.

    Run in polars on the combined frame: ``group_by`` treats NULL keys as
    equal, which is correct here — two state rows (NULL geography) with the
    same year + categoricals are genuine duplicates and must be caught.
    """
    if not grain:
        return CheckResult(
            name="grain_uniqueness",
            status="fail",
            message="Contract declares no grain / primary key",
        )
    missing = [c for c in grain if c not in df.columns]
    if missing:
        return CheckResult(
            name="grain_uniqueness",
            status="fail",
            message="Grain column(s) missing from gold",
            details=missing,
        )
    dups = df.group_by(grain).len().filter(pl.col("len") > 1)
    if dups.height > 0:
        sample = dups.sort("len", descending=True).head(5).to_dicts()
        return CheckResult(
            name="grain_uniqueness",
            status="fail",
            message=f"{dups.height} duplicate grain group(s) on {grain}",
            details=[str(row) for row in sample],
        )
    return CheckResult(
        name="grain_uniqueness",
        status="pass",
        message=f"One row per grain tuple ({grain})",
    )


def check_contract_quality_sql(gold_path: Path, contract: dict) -> CheckResult:
    """Execute the contract's own ``type: sql`` quality checks against gold.

    Runs every quality entry on a fresh, private in-memory DuckDB connection
    (only ``CREATE VIEW`` + ``SELECT``; never shares the API's engine
    connection). The contract's **literal** query string is executed with only
    the ``{object}`` placeholder substituted — never rebuilt from parsed YAML,
    so quoted zero-padded enum values round-trip exactly as emitted.

    Note: the view unions all detail levels (``detail_level`` is encoded in
    filenames, not a column), so hand-authored checks must self-scope via
    geography NULL-ness when they only hold at one level.

    Args:
        gold_path: Gold topic directory (globbed ``**/*.parquet``) or a single
            parquet file (e.g. a dimension table).
        contract: Parsed ODCS contract dict.
    """
    entries = contract_reader.quality_sql_entries(contract)
    if not entries:
        return CheckResult(
            name="contract_quality_sql",
            status="pass",
            message="Contract declares no SQL quality checks",
        )

    resolved = gold_path.resolve()
    if resolved.is_file():
        parquet_glob = resolved.as_posix()
    else:
        parquet_glob = f"{resolved.as_posix()}/**/*.parquet"

    failures: list[str] = []
    passed = 0
    con = duckdb.connect()
    try:
        # Cap the connection so a pathological check (e.g. a self-join whose
        # intermediate explodes) fails as a recorded check failure instead of
        # growing until the kernel OOM-kills the whole transform process.
        con.execute("SET memory_limit='4GB'")
        con.execute("SET threads=4")
        con.execute(
            "CREATE VIEW obj AS SELECT * FROM read_parquet("
            f"'{parquet_glob}', hive_partitioning=true)"
        )
        for entry in entries:
            name = entry.get("name", "?")
            sql = entry["query"].replace("{object}", "obj")
            try:
                value = con.execute(sql).fetchone()[0]
            except duckdb.Error as exc:
                failures.append(f"{name}: query error: {exc}")
                continue
            if value is None:
                failures.append(f"{name}: query returned NULL")
                continue
            if "mustBe" in entry:
                ok, rule = value == entry["mustBe"], f"== {entry['mustBe']}"
            elif "mustBeGreaterThan" in entry:
                ok = value > entry["mustBeGreaterThan"]
                rule = f"> {entry['mustBeGreaterThan']}"
            elif "mustBeLessThan" in entry:
                ok = value < entry["mustBeLessThan"]
                rule = f"< {entry['mustBeLessThan']}"
            else:
                failures.append(f"{name}: no assertion key (mustBe*)")
                continue
            if ok:
                passed += 1
            else:
                failures.append(f"{name}: result={value} expected {rule}")
    finally:
        con.close()

    if failures:
        return CheckResult(
            name="contract_quality_sql",
            status="fail",
            message=(
                f"{len(failures)}/{len(entries)} contract quality check(s) failed"
            ),
            details=failures,
        )
    return CheckResult(
        name="contract_quality_sql",
        status="pass",
        message=f"All {passed} contract quality checks pass",
    )


def check_foreign_keys(
    df: pl.DataFrame,
    gold_dir: Path,
    foreign_keys: list[dict],
) -> CheckResult:
    """Verify every populated FK in gold exists in its dimension table.

    Driven by the contract's ``foreign_keys`` descriptors — composite-aware
    (the schools FK joins on ``(district_code, school_code)``) and
    scope-aware (``domain`` -> ``data/gold/{main}/_dimensions/``, ``global``
    -> ``data/gold/_dimensions/``). A missing dimension parquet is a hard
    fail: the join spine must exist before facts ship.
    """
    if not foreign_keys:
        return CheckResult(
            name="foreign_keys",
            status="pass",
            message="Contract declares no foreign keys",
        )

    resolved = gold_dir.resolve()
    main_topic = resolved.parent.name
    gold_root = resolved.parent.parent

    failures: list[str] = []
    passes: list[str] = []
    for fk in foreign_keys:
        col = fk.get("column")
        target_cols = list(fk.get("target_columns") or [])
        target_obj = fk.get("target_object")
        scope = fk.get("scope", "domain")

        dim_dir = (
            gold_root / "_dimensions"
            if scope == "global"
            else gold_root / main_topic / "_dimensions"
        )
        dim_path = dim_dir / f"{target_obj}.parquet"

        if col not in df.columns:
            # Absent column is the contract_parquet_schema check's finding.
            continue
        missing_targets = [c for c in target_cols if c not in df.columns]
        if missing_targets:
            failures.append(
                f"{col} -> {target_obj}: fact missing join column(s) {missing_targets}"
            )
            continue
        if not dim_path.exists():
            failures.append(f"{col} -> {target_obj}: dimension missing at {dim_path}")
            continue

        fact_keys = df.filter(pl.col(col).is_not_null()).select(target_cols).unique()
        if fact_keys.height == 0:
            # No populated keys (e.g. an always-NULL school_code on a
            # district-only topic) — nothing to join, vacuously valid.
            passes.append(f"{col} -> {target_obj}: no populated keys")
            continue
        dim_keys = pl.read_parquet(dim_path, columns=target_cols).unique()
        orphans = fact_keys.join(dim_keys, on=target_cols, how="anti")
        if orphans.height > 0:
            sample = orphans.head(5).to_dicts()
            failures.append(
                f"{col} -> {target_obj} on {target_cols}: "
                f"{orphans.height} orphan key(s), sample {sample}"
            )
        else:
            passes.append(f"{col} -> {target_obj}: all {fact_keys.height} keys resolve")

    if failures:
        return CheckResult(
            name="foreign_keys",
            status="fail",
            message=f"{len(failures)} foreign key violation(s)",
            details=failures,
        )
    return CheckResult(
        name="foreign_keys",
        status="pass",
        message="All foreign keys resolve in their dimensions",
        details=passes,
    )


# =============================================================================
# Validation Runner
# =============================================================================


class ValidationRunner:
    """Orchestrates all validation checks for a gold topic directory.

    Reads all parquet files once, runs all applicable checks, and produces
    a ValidationReport.

    Args:
        gold_dir: Path to the gold topic directory
            (e.g., data/gold/education/act_scores).
        domain_config: Domain-level configuration (geography rules, ID rules, etc.).
        topic_config: Topic-specific configuration. Pass ``None`` (the default)
            to derive it from the topic's ODCS contract via
            ``contract_reader.derive_topic_config`` — the standard path now
            that per-topic validate.py files no longer exist. An explicit dict
            (including ``{}``) is used as-is.
        contract: Optional pre-parsed contract dict. When omitted, the
            contract is loaded lazily from ``contract_path_for_gold_dir`` on
            first use (kept lazy + module-level so tests can monkeypatch the
            path resolution).
    """

    def __init__(
        self,
        gold_dir: Path,
        domain_config: dict,
        topic_config: dict | None = None,
        contract: dict | None = None,
    ) -> None:
        self.gold_dir = gold_dir
        self.domain_config = domain_config
        self.topic = gold_dir.name
        self._contract_cache: dict | None = contract
        self._contract_loaded = contract is not None
        if topic_config is None:
            if self.contract is None:
                raise GoldValidationError(
                    f"{self.topic}: cannot derive validation config — no "
                    f"contract at {contract_path_for_gold_dir(gold_dir)}"
                )
            topic_config = contract_reader.derive_topic_config(self.contract)
        self.topic_config = topic_config

    @property
    def contract(self) -> dict | None:
        """The topic's parsed ODCS contract, loaded lazily and cached.

        Resolution goes through the module-level ``contract_path_for_gold_dir``
        name at call time. Returns ``None`` (cached) when the contract is
        missing or unreadable — legacy tolerance for fixture trees; the
        contract-driven entry point ``run_topic_validation`` hard-fails on a
        missing contract before constructing the runner.
        """
        if self._contract_loaded:
            return self._contract_cache
        self._contract_loaded = True
        contract_path = contract_path_for_gold_dir(self.gold_dir)
        if not contract_path.exists():
            self._contract_cache = None
            return None
        try:
            self._contract_cache = yaml.safe_load(contract_path.read_text())
        except (OSError, yaml.YAMLError):
            self._contract_cache = None
        return self._contract_cache

    def _pct_classification_from_contract(self) -> tuple[list[str], list[str]]:
        """Read the (bounded, ratio) percentage-column sets from the contract.

        Thin delegate over ``contract_reader.pct_classification`` using the
        runner's cached contract. The contract — not ``TOPIC_CONFIG`` — is the
        source of the percentage classification. Returns empty lists when no
        contract exists (legacy fixture path).
        """
        if self.contract is None:
            return [], []
        try:
            return contract_reader.pct_classification(self.contract)
        except ValueError:
            return [], []

    def run_all(self) -> ValidationReport:
        """Run all validation checks and return a report."""
        report = ValidationReport(topic=self.topic, gold_dir=self.gold_dir)

        # Check for empty files first (filesystem-level)
        report.checks.append(check_no_empty_files(self.gold_dir))

        # Contract-vs-parquet schema check: scan-only, runs before any
        # DataFrames are materialized. Catches the class of bug where the
        # API registry's view of a topic (driven by the ODCS contract) diverges
        # from the on-disk parquet schema — invisible to per-DataFrame checks.
        report.checks.append(check_contract_parquet_schema(self.gold_dir))

        # Read all parquet files grouped by detail level
        detail_level_dfs = self._read_parquet_files()
        if not detail_level_dfs:
            report.checks.append(
                CheckResult(
                    name="data_found",
                    status="fail",
                    message="No parquet files found in gold directory",
                )
            )
            return report

        # Concatenate all data for cross-file checks
        all_dfs = []
        for dfs in detail_level_dfs.values():
            all_dfs.extend(dfs)
        combined = pl.concat(all_dfs, how="diagonal")

        # Run checks on combined data
        report.checks.append(check_column_naming(combined))
        report.checks.append(
            check_column_order(
                combined,
                self.domain_config.get("expected_column_prefix", []),
            )
        )
        report.checks.append(
            check_star_schema_compliance(
                combined,
                self.domain_config.get("forbidden_fact_columns", []),
            )
        )
        report.checks.append(
            check_data_types(
                combined,
                self.topic_config.get("type_spec", {}),
            )
        )
        # Percentage-scale classification (bounded vs ratio) is sourced from the
        # ODCS contract's per-column `unit` markers — authored in the transform
        # and read back here (`proportion` -> bounded, `ratio` -> ratio).
        # `TOPIC_CONFIG` no longer declares pct_columns_bounded/pct_columns_ratio
        # (the contract is the source). `exempt_pct_columns` stays in
        # TOPIC_CONFIG: exempt columns carry no percentage unit, so the contract
        # cannot enumerate them.
        bounded_from_contract, ratio_from_contract = (
            self._pct_classification_from_contract()
        )
        report.checks.append(
            check_percentage_scale(
                combined,
                pct_columns_bounded=bounded_from_contract,
                pct_columns_ratio=ratio_from_contract,
                exempt_columns=self.topic_config.get("exempt_pct_columns", []),
                pct_columns=self.topic_config.get("pct_columns", []),
            )
        )
        report.checks.append(check_demographics(combined))
        report.checks.append(check_no_suppression_markers(combined))
        report.checks.append(check_tidy_format(combined))
        report.checks.append(check_year_non_null(combined))
        report.checks.append(
            check_null_rate_spikes(
                combined,
                self.topic_config.get("metric_columns", []),
            )
        )
        report.checks.append(
            check_categorical_normalization(
                combined,
                self.topic_config.get("categorical_columns", []),
            )
        )
        report.checks.append(
            check_id_formatting(
                combined,
                self.domain_config.get("id_rules", {}),
            )
        )

        # Contract-driven checks: grain uniqueness, the contract's own quality
        # SQL, and FK integrity against the dimension tables. These need the
        # contract; without one (legacy fixture path) they degrade to warnings
        # — the contract-driven entry point run_topic_validation() hard-fails
        # on a missing contract long before reaching here.
        report.checks.append(check_canonical_vocabulary(combined))
        if self.contract is not None:
            report.checks.append(
                check_grain_uniqueness(
                    combined, contract_reader.grain_columns(self.contract)
                )
            )
            report.checks.append(
                check_contract_quality_sql(self.gold_dir, self.contract)
            )
            report.checks.append(
                check_foreign_keys(
                    combined,
                    self.gold_dir,
                    contract_reader.foreign_keys(self.contract),
                )
            )
        else:
            for name in ("grain_uniqueness", "contract_quality_sql", "foreign_keys"):
                report.checks.append(
                    CheckResult(
                        name=name,
                        status="warning",
                        message="No contract — check skipped",
                    )
                )

        # Run geography nulling checks per detail level
        geo_rules = self.domain_config.get("detail_level_geography_rules", {})
        for detail_level, dfs in detail_level_dfs.items():
            level_combined = pl.concat(dfs, how="diagonal")
            report.checks.append(
                check_geography_nulling(
                    level_combined,
                    detail_level,
                    geo_rules,
                )
            )

        return report

    def _read_parquet_files(self) -> dict[str, list[pl.DataFrame]]:
        """Read all parquet files grouped by detail level.

        Returns:
            Dict mapping detail level name (e.g., "schools") to list of DataFrames.
        """
        result: dict[str, list[pl.DataFrame]] = {}

        for pq_file in sorted(self.gold_dir.rglob("*.parquet")):
            # Skip non-data files
            if pq_file.name.startswith("_"):
                continue

            # Infer detail level from filename (e.g., "schools.parquet" -> "schools")
            detail_level = pq_file.stem

            try:
                df = pl.read_parquet(pq_file)
                if detail_level not in result:
                    result[detail_level] = []
                result[detail_level].append(df)
            except Exception as e:
                logger.warning("Failed to read %s: %s", pq_file, e)

        return result


# =============================================================================
# Contract-driven entry point
# =============================================================================


def run_topic_validation(
    gold_dir: Path,
    *,
    contract_path: Path | None = None,
    domain_config: dict | None = None,
    write_report: bool = True,
    raise_on_failure: bool = True,
) -> ValidationReport:
    """Validate a gold topic directory against its ODCS contract.

    The standard validation entry point: every ``transform.py`` calls this as
    the last statement of ``main()`` (after ``write_data_dictionary``, so the
    contract on disk is the one this run just emitted), and
    ``scripts/validate_topic.py`` wraps it as a CLI. There are no per-topic
    validate.py files — the entire topic config derives from the contract.

    A missing or unparseable contract is a precondition failure: a fail report
    is still written (so artifacts always reflect the outcome) and
    ``GoldValidationError`` is raised **unconditionally** — ``raise_on_failure``
    governs check failures only.

    Args:
        gold_dir: Gold topic directory (``data/gold/{main}/{topic}``).
        contract_path: Override for tests; defaults to the path derived from
            ``gold_dir``.
        domain_config: Override; defaults to ``DOMAIN_CONFIGS[main_topic]``.
        write_report: Write ``_validation.json`` next to the gold data.
        raise_on_failure: Raise ``GoldValidationError`` when any check fails.

    Returns:
        The ``ValidationReport`` (when it didn't raise).
    """
    resolved = gold_dir.resolve()
    main_topic = resolved.parent.name
    if contract_path is None:
        contract_path = contract_path_for_gold_dir(resolved)
    if domain_config is None:
        # An unregistered main_topic must fail loudly: falling back to {} would
        # silently skip every geography/ID/prefix rule for a whole new domain.
        if main_topic not in DOMAIN_CONFIGS:
            raise GoldValidationError(
                f"{resolved.name}: main_topic '{main_topic}' has no entry in "
                "DOMAIN_CONFIGS (src/utils/validators.py) — register a domain "
                "config before validating topics under it."
            )
        domain_config = DOMAIN_CONFIGS[main_topic]

    try:
        contract = contract_reader.load_contract(contract_path)
    except (contract_reader.ContractMissingError, ValueError, yaml.YAMLError) as exc:
        report = ValidationReport(topic=resolved.name, gold_dir=resolved)
        report.checks.append(
            CheckResult(
                name="contract_present",
                status="fail",
                message=str(exc),
            )
        )
        if write_report:
            report.write_json()
        raise GoldValidationError(
            f"{resolved.name}: contract precondition failed — {exc}"
        ) from exc

    runner = ValidationRunner(
        gold_dir=resolved,
        domain_config=domain_config,
        topic_config=None,
        contract=contract,
    )
    report = runner.run_all()
    if write_report:
        report.write_json()
    if not report.passed and raise_on_failure:
        counts = report.summary_counts
        failing = [c.name for c in report.checks if c.status == "fail"]
        raise GoldValidationError(
            f"{resolved.name}: validation failed "
            f"({counts['fail']} fail / {counts['pass']} pass) — {failing}"
        )
    return report
