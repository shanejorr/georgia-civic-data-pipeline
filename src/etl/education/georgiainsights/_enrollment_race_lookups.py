"""Shared race/ethnicity and gender lookups for the Georgia Insights FTE
enrollment gender-race topics.

Two sibling topics ingest structurally identical bronze (one District CSV +
one School CSV per fiscal year, seven wide race/ethnicity count columns, a
three-value ``Gender`` column) and publish the same race x gender
cross-classified gold shape:

- ``enrollment_march_gender_race_ethnicity``  (FTE Cycle 3, ``-3`` files)
- ``enrollment_october_gender_race_ethnicity`` (FTE Cycle 1, ``-1`` files)

This module is the single source for the vocabulary both transforms share,
so the two topics cannot drift if the bronze schema gains or renames a race
bucket. It holds constants and one pure guard function only — no I/O, no
polars expressions.

Why a strict topic-local map instead of ``normalize_demographic_column()``:
the keys here are **bronze column names** (e.g. ``"Race AmericanIndian"``),
not student-facing demographic labels, and the gold column is ``race`` (not
``demographic``) per the race x gender two-column convention in
``src/etl/education/CLAUDE.md``. A strict map fails loudly when a new race
column appears in bronze, which is the desired behavior for a vocabulary
change.

Race-bucket structure decision (data-cleaning-standards section 5a/5b),
made ONCE here for both topics: this source publishes the post-1997 OMB
**split** convention — separate ``Race Asian`` and ``Race Pacific Islander``
columns exist in every file of both topics — so gold publishes the split
``asian`` / ``pacific_islander`` keys and never the combined
``asian_pacific_islander`` rollup. ``Ethnic Hispanic`` is a non-overlapping
ethnicity bucket alongside the six race buckets (GaDOE FTE coding gives
Hispanic ethnicity precedence over race), so the seven values partition
total enrollment; verified for March 2025: 1,396,583 (six race buckets) +
340,147 (Hispanic) = 1,736,730 = published statewide FTE enrollment.

All seven canonical race keys and both gender keys already exist in
``data/gold/_dimensions/demographics.parquet``.
"""

from collections.abc import Iterable

# Bronze race/ethnicity column name (after header .strip()) -> canonical
# race key. Insertion order matches the bronze column order and drives the
# unpivot stacking order in both transforms.
RACE_ETHNICITY_TO_RACE: dict[str, str] = {
    "Ethnic Hispanic": "hispanic",
    "Race AmericanIndian": "native_american",
    "Race Asian": "asian",
    "Race Black": "black",
    "Race Pacific Islander": "pacific_islander",
    "Race White": "white",
    "Two or more Races": "multiracial",
}

# Ordered list of the seven bronze race/ethnicity column names — derived
# from the map's keys so the two can never disagree.
RACE_ETHNICITY_COLUMNS: list[str] = list(RACE_ETHNICITY_TO_RACE.keys())

# Sorted canonical race keys, for contract `validValues` enumerations.
RACE_VALUES: list[str] = sorted(RACE_ETHNICITY_TO_RACE.values())

# Bronze `Gender` value -> gold `gender` value. The third bronze value,
# GENDER_TOTAL_LABEL, is dropped before this map applies (see below), so
# the map intentionally covers only the two published gold values.
GENDER_MAP: dict[str, str] = {
    "Female": "female",
    "Male": "male",
}

# Sorted gold gender values, for contract `validValues` enumerations.
GENDER_VALUES: list[str] = sorted(GENDER_MAP.values())

# The bronze `Gender` value that is arithmetically redundant (equals
# Female + Male on every fully published cell — verified row-by-row across
# both topics' bronze) and is dropped during transform so consumers cannot
# double-count by summing over gender.
GENDER_TOTAL_LABEL: str = "Total"


def require_race_columns(columns: Iterable[str], context: str) -> None:
    """Raise if any of the seven race/ethnicity bronze columns is missing.

    An unmatched source column silently becomes NULL in gold — the most
    common class of data-loss bug — so both transforms call this guard on
    every file's (stripped) header before transforming it.

    Args:
        columns: The bronze frame's column names, post-strip.
        context: Label for the error message (e.g. "march 2025 school").

    Raises:
        ValueError: When one or more expected race/ethnicity columns are
            absent from ``columns``.
    """
    present = set(columns)
    missing = [c for c in RACE_ETHNICITY_COLUMNS if c not in present]
    if missing:
        raise ValueError(
            f"{context}: expected race/ethnicity bronze column(s) missing: "
            f"{missing}. Present: {sorted(present)}"
        )
