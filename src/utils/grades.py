"""Grade-level normalization utilities.

Single canonical path for converting raw bronze grade values into the
project's canonical `grade_level` vocabulary.

Canonical values (per data-cleaning-standards §16):

- Zero-padded 2-char strings `'01'`, `'02'`, …, `'12'` for grades 1–12.
- `'k'` for kindergarten.
- `'pk'` for pre-kindergarten.
- `'all'` for true cross-grade aggregate rows that cannot be reconstructed
  from per-grade rows (rare; only used when the source publishes an
  AllGrades summary as a distinct row).

Usage:

    ```python
    from src.utils.grades import normalize_grade_column

    df = df.with_columns(
        normalize_grade_column("grade_raw").alias("grade_level")
    )
    ```

Adding new mappings: extend `GRADE_LEVEL_MAP` with the bronze spelling
(uppercased, stripped) as the key and the canonical value as the value.
The transform's `TransformManifest.record_categorical()` will detect any
unmapped bronze value and raise — that is the signal to add a mapping
here rather than patch the transform locally.
"""

import polars as pl

# Sentinel emitted when a raw value does not match any known spelling.
# Mirrors the demographics module so downstream validators / manifests
# detect it consistently. Validators flag rows that end up with this
# value — the fix is always to add the missing mapping here, not to
# filter the row out.
SENTINEL_UNMATCHED_GRADE_LEVEL: str = "99999999"


# Mapping from raw bronze spellings to canonical grade_level values.
# Keys are compared after `.str.strip_chars().str.to_uppercase()`, so
# entries here must be uppercase. The map covers the common spellings
# observed across GOSA, Georgia Insights, and Milestones bronze; add new
# ones as fresh sources appear.
GRADE_LEVEL_MAP: dict[str, str] = {
    # Pre-kindergarten
    "PK": "pk",
    "PRE-K": "pk",
    "PRE K": "pk",
    "PREK": "pk",
    "PRE-KINDERGARTEN": "pk",
    "PRE KINDERGARTEN": "pk",
    "PRE_KINDERGARTEN": "pk",
    "PREKINDERGARTEN": "pk",
    "GRADE PK": "pk",
    "GRADE_PK": "pk",
    # Kindergarten
    "K": "k",
    "KK": "k",
    "KINDERGARTEN": "k",
    "GRADE K": "k",
    "GRADE_K": "k",
    "GRADE KK": "k",
    "GRADE_KK": "k",
    # Numeric grades — bare, padded, and "Grade N" / "Nth" / "grade_N" forms.
    **{
        spelling: canonical
        for n, canonical in (
            (1, "01"),
            (2, "02"),
            (3, "03"),
            (4, "04"),
            (5, "05"),
            (6, "06"),
            (7, "07"),
            (8, "08"),
            (9, "09"),
            (10, "10"),
            (11, "11"),
            (12, "12"),
        )
        for spelling in (
            str(n),
            f"{n:02d}",
            f"GRADE {n}",
            f"GRADE_{n}",
            f"GRADE-{n}",
            f"GRADE{n:02d}",
            f"GRADE {n:02d}",
            f"GRADE_{n:02d}",
            # Ordinal forms (1st .. 12th)
            f"{n}ST" if n % 10 == 1 and n != 11 else None,
            f"{n}ND" if n % 10 == 2 and n != 12 else None,
            f"{n}RD" if n % 10 == 3 and n != 13 else None,
        )
        if spelling is not None
    },
    # "th" ordinals (4th–12th excluding 11th/12th which are handled below)
    "4TH": "04",
    "5TH": "05",
    "6TH": "06",
    "7TH": "07",
    "8TH": "08",
    "9TH": "09",
    "10TH": "10",
    "11TH": "11",
    "12TH": "12",
    # Cross-grade aggregate
    "ALL": "all",
    "ALL GRADES": "all",
    "ALLGRADES": "all",
    "ALL_GRADES": "all",
    "TOTAL": "all",
}


def normalize_grade_column(col: str | pl.Expr) -> pl.Expr:
    """Normalize a raw grade column to canonical `grade_level` values.

    Casts to string, strips whitespace, uppercases, then maps via
    `GRADE_LEVEL_MAP`. Unmatched values become
    `SENTINEL_UNMATCHED_GRADE_LEVEL` so the validator / manifest can
    flag them (the fix is to extend the map, not filter rows).

    NULL values pass through as NULL.

    Args:
        col: Column name (str) or Polars expression producing the raw
            grade values.

    Returns:
        Polars expression producing the canonical grade_level string.

    Example:
        ```python
        df = df.with_columns(
            normalize_grade_column("grade_raw").alias("grade_level")
        )
        ```
    """
    expr = pl.col(col) if isinstance(col, str) else col
    normalized = (
        expr.cast(pl.Utf8)
        .str.strip_chars()
        .str.to_uppercase()
        .replace_strict(GRADE_LEVEL_MAP, default=SENTINEL_UNMATCHED_GRADE_LEVEL)
    )
    return pl.when(expr.is_null()).then(None).otherwise(normalized)
