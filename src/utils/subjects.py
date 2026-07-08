"""Subject normalization for assessment topics.

Per data-cleaning-standards §16, the assessed academic content area is
named **`subject`** across Milestones EOC/EOG, GAA, SGM, AP, CCRPI
content mastery, and Lexile. Use **`test_component`** only for true
non-academic test sections (SAT/ACT math, reading, etc.).

This module resolves spelling variants observed across topics. Curriculum-
era differences that reflect distinct course standards
(`algebra_i` vs `coordinate_algebra`; `geometry` vs `analytic_geometry`)
stay distinct because they ARE different courses, not aliases.

Usage:

    ```python
    from src.utils.subjects import (
        SUBJECT_NORMALIZATION_MAP,
        apply_subject_normalization,
    )

    # After the topic's local subject map produces snake_case values,
    # canonicalize spelling variants:
    df = df.with_columns(apply_subject_normalization("subject").alias("subject"))
    ```

Adding new mappings: extend `SUBJECT_NORMALIZATION_MAP` only when two
or more topics publish equivalent spellings under different snake_case
names. Curriculum-era distinctions are NOT mappings — they are kept
distinct on purpose.
"""

import polars as pl

# Map of spelling-variant snake_case → canonical snake_case. Keys are the
# variant forms the topic transforms produce; values are the canonical
# names per data-cleaning-standards §16. The map operates AFTER the
# topic-local snake_case normalization, so all keys are lowercase
# snake_case.
SUBJECT_NORMALIZATION_MAP: dict[str, str] = {
    # US History
    "united_states_history": "us_history",
    # 9th-grade literature family
    "9th_grade_literature": "9th_grade_literature_and_composition",
    "ninth_grade_literature": "9th_grade_literature_and_composition",
    "ninth_grade_literature_and_composition": "9th_grade_literature_and_composition",
    # American literature
    "american_literature": "american_literature_and_composition",
    # Economics
    "economics": "economics_business_free_enterprise",
}


def apply_subject_normalization(col: str | pl.Expr) -> pl.Expr:
    """Apply shared subject-spelling resolution after the topic-local map.

    Behavior:
    - Values listed in `SUBJECT_NORMALIZATION_MAP` are replaced with their
      canonical form.
    - Values not listed pass through unchanged. Curriculum-era distinct
      courses such as `algebra_i`, `coordinate_algebra`,
      `algebra_concepts_and_connections`, `geometry`, `analytic_geometry`,
      and `geometry_analytic_geometry` are intentionally preserved.
    - NULL values pass through as NULL.

    Args:
        col: Column name (str) or Polars expression producing snake_case
            subject values from a topic-local subject map.

    Returns:
        Polars expression producing the canonical subject string.

    Example:
        ```python
        df = df.with_columns(
            apply_subject_normalization("subject").alias("subject")
        )
        ```
    """
    expr = pl.col(col) if isinstance(col, str) else col
    # `replace` (not `replace_strict`) lets unmapped values pass through.
    return expr.replace(SUBJECT_NORMALIZATION_MAP)
