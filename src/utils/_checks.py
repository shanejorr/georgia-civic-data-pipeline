"""Shared validation primitives used by both transformers.py and validators.py.

This module is a leaf — it only depends on polars and other primitives
(demographics) and must not import from ``src.utils.transformers`` or
``src.utils.validators``. Both of those modules import from here, which
breaks the transformers ↔ validators cycle that previously required an
in-function import inside ``transformers.validate_output``.

Keep this module's public surface small: the ``CheckResult`` dataclass and
individual check functions that are needed at transform time as well as at
post-export validation time.
"""

from dataclasses import dataclass, field

import polars as pl

from src.utils.demographics import CANONICAL_DEMOGRAPHICS


@dataclass
class CheckResult:
    """Result of a single validation check.

    Attributes:
        name: Short identifier (e.g., "column_naming").
        status: One of "pass", "fail", "warning".
        message: Human-readable summary.
        details: Specific issues found.
    """

    name: str
    status: str
    message: str
    details: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON output."""
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
        }


def check_demographics(df: pl.DataFrame) -> CheckResult:
    """Verify demographic column has canonical values and no sentinels.

    Only runs if 'demographic' column exists.
    """
    if "demographic" not in df.columns:
        return CheckResult(
            name="demographics",
            status="pass",
            message="No demographic column (skipped)",
        )

    values = df["demographic"].drop_nulls().unique().to_list()
    details = []

    # Check for sentinel value indicating failed normalization
    if "99999999" in values:
        sentinel_count = df.filter(pl.col("demographic") == "99999999").height
        details.append(f"Found {sentinel_count} rows with sentinel '99999999'")

    # Check for non-canonical values
    non_canonical = [
        v for v in values if v not in CANONICAL_DEMOGRAPHICS and v != "99999999"
    ]
    if non_canonical:
        details.append(f"Non-canonical values: {non_canonical}")

    if details:
        return CheckResult(
            name="demographics",
            status="fail",
            message="Demographic validation failed",
            details=details,
        )
    return CheckResult(
        name="demographics",
        status="pass",
        message=f"All {len(values)} demographic values are canonical",
    )
