"""Canonical cross-topic column vocabulary — the machine-readable §16 registry.

The data-cleaning-standards skill §16 holds the *rationale* for each canonical
name; this module holds the enforceable registry. The shared validator's
``check_canonical_vocabulary`` runs :func:`vocabulary_violations` over every
gold fact table, so a forbidden variant fails validation deterministically
instead of relying on a reviewer to notice.

Rules of the registry (mirrors §16's "when to extend this list"):

- Add an entry only when two or more topics have actually published the same
  concept under different names — encode resolved conflicts, don't anticipate.
- Exact-name matching only. No substring heuristics: ``flag`` is forbidden,
  ``ccrpi_flag`` is canonical, and a hypothetical ``red_flag_count`` is not
  this registry's business.
- Sanctioned exceptions live in :data:`EXEMPT_COLUMNS` (terms of art that look
  like violations but are deliberate).
"""

from __future__ import annotations

from collections.abc import Iterable

# Forbidden column name -> the canonical name to use instead. Exact matches.
CANONICAL_VARIANTS: dict[str, str] = {
    # Count of distinct students tested (§16) -> num_tested
    "number_tested": "num_tested",
    "num_students_tested": "num_tested",
    "total_students_tested": "num_tested",
    "n_tested": "num_tested",
    # Enrollment / cohort denominator (§16) -> num_students (num_ count standard)
    "student_count": "num_students",
    "total_students": "num_students",
    "enrollment_count": "num_students",
    "enrolled_count": "num_students",
    # Adjusted graduation-cohort denominator (§16) -> num_cohort
    "cohort_size": "num_cohort",
    # High-school graduates (§16) -> num_graduates
    "graduates": "num_graduates",
    "total_graduated": "num_graduates",
    "graduate_count": "num_graduates",
    # Dropouts (§16) -> num_dropouts
    "dropout_count": "num_dropouts",
    # Student Growth Percentile count (§16) -> num_sgp_received (sgp leading)
    "n_received_sgp": "num_sgp_received",
    "number_received_sgp": "num_sgp_received",
    "num_received_sgp": "num_sgp_received",
    # SGP receipt rate / growth-band share carry the sgp qualifier (§16)
    "pct_received_sgp": "sgp_received_rate",
    "pct_typical_or_high_growth": "pct_sgp_typical_or_high_growth",
    # Share of enrolled who tested — one canonical across EOC/EOG/WIDA (§16)
    "pct_enrolled_tested": "enrolled_tested_rate",
    "enrollment_tested_rate": "enrolled_tested_rate",
    "enrollment_tested_in_domain_rate": "enrolled_tested_in_domain_rate",
    # Academic grade axis (§16) -> grade_level
    "grade": "grade_level",
    # Assessment subject (§16) -> subject
    "content_area": "subject",
    # CCRPI color flag (§16) -> ccrpi_flag
    "flag": "ccrpi_flag",
    # CCRPI improvement target (§16) -> indicator_target
    "ccrpi_target": "indicator_target",
    "target": "indicator_target",
    # Redundant _pct doubles (§16) — already-scaled rates/scores
    "indicator_score_pct": "indicator_score",
    "unbenchmarked_rate_pct": "unbenchmarked_rate",
    "dropout_rate_pct": "dropout_rate",
    "graduation_rate_pct": "graduation_rate",
    "mobility_rate_pct": "mobility_rate",
}

# Suffix rules: (forbidden_suffix, replacement_suffix_or_guidance, mechanical).
# Mechanical rules produce the canonical name by substitution; advisory rules
# can only suggest a direction (the canonical name needs human naming).
SUFFIX_RULES: list[tuple[str, str, bool]] = [
    ("_and_above", "_or_above", True),
    ("_rate_pct", "_rate", True),
    ("_share", "pct_of_<denominator>", False),
]

# Sanctioned exceptions — canonical names that would otherwise trip a rule.
EXEMPT_COLUMNS: frozenset[str] = frozenset(
    {
        # "Average Daily Attendance" is a fixed term of art in school finance
        # reporting (§16) — the spelled-out prefix is deliberate.
        "average_daily_attendance_rate",
        "average_daily_absenteeism_rate",
    }
)


def vocabulary_violations(columns: Iterable[str]) -> list[tuple[str, str]]:
    """Return ``(column, canonical_suggestion)`` pairs for forbidden names.

    Exact-name variants are checked first, then suffix rules. Columns in
    :data:`EXEMPT_COLUMNS` never violate.
    """
    violations: list[tuple[str, str]] = []
    for col in columns:
        if col in EXEMPT_COLUMNS:
            continue
        if col in CANONICAL_VARIANTS:
            violations.append((col, CANONICAL_VARIANTS[col]))
            continue
        for suffix, replacement, mechanical in SUFFIX_RULES:
            if col.endswith(suffix):
                if mechanical:
                    suggestion = col[: -len(suffix)] + replacement
                else:
                    suggestion = replacement
                violations.append((col, suggestion))
                break
    return violations
