"""Total/"all" sentinel detection over a categorical column's enum values.

A Python port of ``web/src/lib/dashboard/sentinel.ts`` — the single heuristic
that decides whether a categorical carries an aggregate "total/all" value (e.g.
``all`` / ``total`` / ``overall``). A grain-contributor categorical that HAS a
sentinel can be collapsed to that one value ("don't disaggregate"); one that has
NONE "cannot be aggregated" and must be filtered to a single value before its key
metric is meaningful — the dashboard turns it into a required single-select and
the MCP advises the same.

Kept in step with the dashboard's ``SENTINEL_TOKENS`` so both faces classify a
column identically. Matching is on the WHOLE normalized token, never a substring
— so ``all_grades_tested`` is NOT a total just because it contains ``all``.

``combined`` is deliberately NOT a token: in this data it denotes a composite
*score* (e.g. the SAT ``combined`` V+M+W value, which exists only 2011-2016),
not an "every category" total — treating it as one silently truncated the
series to the years that composite was published.

The contract emitter writes the result of this helper onto each enum column as
``has_total`` / ``total_value`` custom properties, so the registry (and every
downstream consumer) reads an authoritative marker instead of re-running the
heuristic. The registry also calls this directly as a fallback for contracts
emitted before the marker existed.
"""

from __future__ import annotations

from collections.abc import Iterable

# Whole-token markers that denote an aggregate "total" / "all" row. Mirrors
# ``SENTINEL_TOKENS`` in web/src/lib/dashboard/sentinel.ts — KEEP IN SYNC.
SENTINEL_TOKENS = frozenset(
    {
        "all",
        "all_students",
        "total",
        "overall",
        "statewide",
        "all_grades",
        "all_subjects",
        "all_categories",
    }
)


def _norm(value: str) -> str:
    return value.strip().lower()


def find_sentinel(values: Iterable[str] | None) -> str | None:
    """Return the enum's total/all value, or ``None`` if it has none.

    Prefers an exact ``all`` (case-insensitive); otherwise the first value whose
    normalized whole token is in :data:`SENTINEL_TOKENS`. Returns the ORIGINAL
    value (case preserved) so it can be used directly as a filter value.
    """
    if values is None:
        return None
    vals = [v for v in values if v is not None]
    for v in vals:
        if _norm(str(v)) == "all":
            return v
    for v in vals:
        if _norm(str(v)) in SENTINEL_TOKENS:
            return v
    return None
