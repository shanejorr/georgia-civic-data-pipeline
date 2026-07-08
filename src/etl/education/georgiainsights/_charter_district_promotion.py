"""Promote charter SYSTEM district codes to 7-digit CAMPUS codes.

Georgia's two charter umbrella systems — State Charter Schools (district
code ``782``) and State Commission Charter Schools (``783``) — are reporting
containers, not physical campuses. Every campus that reports under one of
them also has its own 7-digit CAMPUS district code formed by concatenating
the 3-digit system code with the campus's 4-digit school code::

    system 782 + school 0614  ->  campus district 7820614

The districts dimension carries BOTH representations (a 782/783 SYSTEM row
and a 7-digit CAMPUS row for each such school), but the repo convention —
followed by the GOSA topics and the educator-qualification overrides — keys
school-level fact rows on the CAMPUS code so ``(district_code,
school_code)`` joins line up across topics. A handful of GeorgiaInsights
topics (this Milestones EOC/EOG family and both SGM topics) published their
early years (~2015-2017) under the SYSTEM code instead, which breaks those
cross-topic joins.

This module is the single shared fix. It is intentionally narrow:

* Only SCHOOL-LEVEL rows are rewritten — rows where ``district_code`` is in
  :data:`CHARTER_SYSTEM_DISTRICT_CODES` AND ``school_code`` is non-null.
  District- and state-aggregate rows (NULL ``school_code``) are never
  touched, so the 782/783 district-level aggregates remain valid
  districts-dimension FKs.
* ``school_code`` itself is never modified.
* No other district code is affected.

Every promoted ``district_code + school_code`` campus code has an FK-valid
twin in both the districts and schools dimensions (the dimension build
ingests both representations), so the rewrite is FK-safe by construction;
the per-topic contract FK validation still re-verifies this on every run.

Usage (consumed read-only by ``georgia_milestones_end_of_course``,
``georgia_milestones_end_of_grade``, and the two
``georgia_student_growth_model_*`` topics)::

    from src.etl.education.georgiainsights._charter_district_promotion import (
        promote_charter_system_to_campus_district,
    )

    combined = promote_charter_system_to_campus_district(combined, manifest=manifest)

Call it AFTER district/school code formatting (zero-padding) and BEFORE the
natural-key collision guard + dedup, so any key collision the rewrite could
create (a system-coded row meeting an already-campus-coded row) is surfaced
by the transform's existing machinery instead of slipping through.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:  # pragma: no cover - typing only
    from src.utils.transformers import TransformManifest

logger = logging.getLogger(__name__)

# The two charter SYSTEM district codes that must be promoted on school-level
# rows: State Charter Schools (782) and State Commission Charter Schools (783).
CHARTER_SYSTEM_DISTRICT_CODES: tuple[str, ...] = ("782", "783")

# Ledger text recorded for every promotion (manifest `reclassified` events).
PROMOTION_REASON: str = (
    "charter SYSTEM district_code (782/783) promoted to 7-digit CAMPUS code "
    "(district_code + school_code) on school-level rows"
)


def promote_charter_system_to_campus_district(
    df: pl.DataFrame,
    *,
    manifest: TransformManifest | None = None,
    year_col: str = "year",
) -> pl.DataFrame:
    """Rewrite school-level 782/783 district codes to their campus codes.

    For every row where ``district_code`` is one of
    :data:`CHARTER_SYSTEM_DISTRICT_CODES` and ``school_code`` is non-null,
    set ``district_code = district_code + school_code`` (string concat — the
    7-digit campus code). All other rows pass through unchanged. The
    operation is a pure column rewrite: row count, row order, and every
    other column are preserved.

    Args:
        df: Long fact DataFrame with Utf8 ``district_code`` and
            ``school_code`` columns (school-level rows have both non-null;
            aggregate rows carry NULL ``school_code``).
        manifest: Optional ``TransformManifest``. When given, promoted-row
            counts are ledgered per year via ``record_reclassified`` with
            :data:`PROMOTION_REASON`, so promotions are reviewable manifest
            artifacts rather than log lines.
        year_col: Column used to group the manifest ledger entries.

    Returns:
        The DataFrame with promoted ``district_code`` values.

    Raises:
        ValueError: If ``district_code`` or ``school_code`` is missing —
            calling this on a frame without school-level geography keys is a
            consumer bug, not a no-op.
    """
    missing = [c for c in ("district_code", "school_code") if c not in df.columns]
    if missing:
        raise ValueError(
            f"promote_charter_system_to_campus_district requires district_code "
            f"and school_code columns; missing: {missing}"
        )

    # Eligibility: school-level rows under a charter SYSTEM code. Aggregate
    # rows (NULL school_code) and every other district code pass through.
    eligible = (
        pl.col("district_code").is_in(CHARTER_SYSTEM_DISTRICT_CODES)
        & pl.col("school_code").is_not_null()
    )

    n_eligible = int(df.select(eligible.sum()).item())
    if n_eligible == 0:
        return df

    if manifest is not None and year_col in df.columns:
        # Ledger the promotion per year so the data review can verify the
        # repair from the manifest (reclassified events), not from logs.
        per_year = (
            df.filter(eligible)
            .group_by(year_col)
            .agg(pl.len().alias("n"))
            .sort(year_col)
        )
        for year, count in per_year.iter_rows():
            manifest.record_reclassified(int(year), int(count), PROMOTION_REASON)

    df = df.with_columns(
        pl.when(eligible)
        .then(pl.col("district_code") + pl.col("school_code"))
        .otherwise(pl.col("district_code"))
        .alias("district_code")
    )
    logger.info(
        "Promoted %d school-level charter-system row(s) (district_code 782/783) "
        "to 7-digit campus district codes",
        n_eligible,
    )
    return df
