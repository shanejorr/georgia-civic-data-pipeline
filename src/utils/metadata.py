"""Data dictionary and contract utilities for gold layer fact tables.

The transform's in-code schema declaration (the ``columns=[...]`` list passed to
``write_data_dictionary``) is the single source: it is projected directly into
the git-tracked ODCS data contract (``contracts/{main}/{topic}.odcs.yaml``) via
``src/utils/contract_emitter.py``. There is no longer a ``_metadata.json``
intermediary and no per-topic gold ``README.md`` — the contract is the single
documentation artifact, carrying both the machine-readable schema (the API and
validator read it) and the human-facing fields (``title`` / ``summary`` at the
topic level, ``label`` / ``short_description`` per column) consumed by the
website docs and the dashboard. Dimension tables are documented separately; this
module does not describe them.
"""

import logging
from pathlib import Path
from typing import Any

import polars as pl

from src.utils.contract_emitter import write_contract

logger = logging.getLogger(__name__)

# Canonical categorical fact-table column names across the education topics.
# Any string column named here is treated as categorical and gets a
# `validValues` enumeration regardless of cardinality, so genuinely wide
# enumerations (e.g. `subject` = 42 AP courses) are covered without relying on a
# fragile cardinality threshold. New categorical columns can be added here; ones
# not listed fall back to the cardinality test below.
KNOWN_CATEGORICAL_COLUMNS = frozenset(
    {
        "administration",
        "assessment_type",
        "ccrpi_flag",
        "completer_type",
        "credential_type",
        "demographic",
        "disability_category",
        "domain",
        "employee_type",
        "enrollment_period",
        "gender",
        "grade_cluster",
        "grade_level",
        "improvement_status",
        "indicator",
        "measure_category",
        "measure_subcategory",
        "met_ayp",
        "month",
        "offense_category",
        "release_type",
        "sex",
        "poverty_subgroup",
        "proficiency_level",
        "program",
        "race",
        "rate_type",
        "reporting_status",
        "rev_exp_category",
        "rev_exp_subcategory",
        "role",
        "staff_category",
        "sub_indicator",
        "subject",
        "test_component",
    }
)

# Geography key columns. These are identifiers, never categorical enumerations,
# so they never receive a `validValues` array no matter how few distinct values
# a given slice happens to contain.
IDENTIFIER_COLUMNS = frozenset(
    {"district_code", "school_code", "county_fips", "ori", "facility_id"}
)

# Fallback cardinality threshold for string columns NOT named in
# KNOWN_CATEGORICAL_COLUMNS: such a column is treated as categorical only if it
# has this many or fewer distinct non-null values. Known categoricals bypass
# this entirely (covered by name) and identifiers are always excluded, so this
# is restored to the original conservative value rather than being inflated to
# accommodate wide known enumerations. Shared by both the DataFrame-inference
# path (`infer_columns_from_dataframe`) and the hand-authored path
# (`write_data_dictionary`) so categorical behavior is identical across both.
CATEGORICAL_MAX_UNIQUE = 20


def infer_valid_values(
    series: pl.Series, column_name: str | None = None
) -> list[Any] | None:
    """Return sorted valid values for a column if it qualifies as categorical.

    A string (Utf8) column qualifies as categorical when EITHER its name is in
    ``KNOWN_CATEGORICAL_COLUMNS`` (any cardinality) OR its number of distinct
    non-null values does not exceed ``CATEGORICAL_MAX_UNIQUE``. Columns named in
    ``IDENTIFIER_COLUMNS`` never qualify, and non-string columns return ``None``.

    Driving known categoricals by name rather than by a cardinality threshold
    lets wide-but-genuine enumerations (e.g. ``subject``) be enumerated while
    keeping high-cardinality identifiers excluded by identity.

    This is the single source of truth for categorical detection and
    valid-value extraction; both ``infer_columns_from_dataframe`` and
    ``write_data_dictionary`` use it so the two paths behave identically.

    Args:
        series: Polars Series for a single column.
        column_name: Name of the column, used to consult the categorical
            allowlist and the identifier blocklist. When ``None`` (caller did
            not supply it), only the cardinality fallback applies.

    Returns:
        Sorted list of distinct non-null values if the column is categorical
        (and has at least one non-null value), otherwise ``None``.
    """
    if series.dtype != pl.Utf8:
        return None
    if column_name in IDENTIFIER_COLUMNS:
        return None
    is_known_categorical = column_name in KNOWN_CATEGORICAL_COLUMNS
    if not is_known_categorical and series.n_unique() > CATEGORICAL_MAX_UNIQUE:
        return None
    valid_values = series.drop_nulls().unique().sort().to_list()
    return valid_values or None


def _read_gold_dataframe(output_dir: Path) -> pl.DataFrame | None:
    """Read the gold parquet written under ``output_dir`` into one DataFrame.

    ``write_data_dictionary`` is called after a topic's gold parquet has already
    been exported to ``output_dir`` (year-partitioned, possibly split by detail
    level). This reads every parquet under ``output_dir`` so observed gold values
    can be used to fill in ``validValues`` for categorical columns.

    The read is best-effort: if no parquet files exist or the read fails for any
    reason, this returns ``None`` and the caller falls back to whatever
    ``validValues`` were hand-authored (i.e. the behavior is purely additive).

    Args:
        output_dir: Gold directory the metadata is being written to.

    Returns:
        Combined DataFrame of all parquet under ``output_dir``, or ``None``.
    """
    parquet_files = sorted(output_dir.rglob("*.parquet"))
    if not parquet_files:
        return None

    frames: list[pl.DataFrame] = []
    for pq in parquet_files:
        try:
            frames.append(pl.read_parquet(pq))
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Skipping unreadable gold parquet %s: %s", pq, exc)

    if not frames:
        return None

    # Files for different detail levels may have differing column sets
    # (e.g. school-level files carry school_code, state-level files do not),
    # so allow a non-strict vertical concat that aligns on column name.
    try:
        return pl.concat(frames, how="diagonal_relaxed")
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Could not combine gold parquet under %s: %s", output_dir, exc)
        return None


def _fill_categorical_valid_values(
    columns: list[dict[str, Any]], output_dir: Path
) -> list[dict[str, Any]]:
    """Add ``validValues`` to hand-authored categorical columns that lack them.

    For each column definition without an explicit ``validValues`` key, if the
    matching column in the exported gold parquet qualifies as categorical under
    the shared :func:`infer_valid_values` logic, its observed values are added.
    Columns that already declare ``validValues``, non-categorical columns, and
    high-cardinality columns are left untouched. The change is additive only:
    no existing keys (type, description, ordering, etc.) are modified.

    Args:
        columns: Hand-authored column definitions (mutated in place).
        output_dir: Gold directory whose parquet supplies observed values.

    Returns:
        The same ``columns`` list, with ``validValues`` filled where applicable.
    """
    gold_df = _read_gold_dataframe(output_dir)
    if gold_df is None:
        return columns

    for col in columns:
        if "validValues" in col:
            continue
        col_name = col.get("name")
        if col_name not in gold_df.columns:
            continue
        valid_values = infer_valid_values(gold_df[col_name], col_name)
        if valid_values is not None:
            col["validValues"] = valid_values

    return columns


def write_data_dictionary(
    output_dir: Path,
    name: str,
    description: str,
    title: str,
    summary: str,
    columns: list[dict[str, Any]],
    source: str,
    source_url: str | None = None,
    update_frequency: str = "annual",
    year_range: tuple[int, int] | None = None,
    partitioned_by: list[str] | None = None,
    notes: list[str] | None = None,
    limitations: str | None = None,
    usage: str | None = None,
    example_queries: list[dict[str, Any]] | None = None,
    suppressed_to_null: bool = True,
    quality_checks: list[dict[str, Any]] | None = None,
    dependent_filters: list[dict[str, Any]] | None = None,
    version: str = "1.0.0",
) -> Path:
    """Emit the ODCS contract for a dataset from its in-code declaration.

    The transform's in-code schema declaration (``columns``) is the single
    source: it is projected directly into the git-tracked ODCS contract under
    ``contracts/{main_topic}/{topic}.odcs.yaml`` — the single documentation
    artifact. There is no ``_metadata.json`` intermediary and no per-topic gold
    ``README.md`` (retired; the contract now carries the human-facing fields).

    Human-facing fields the contract now carries (for the website docs +
    dashboard, alongside the machine-readable schema):

    - ``title`` / ``summary`` — REQUIRED topic-level Title Case display name and
      a one-line plain-language summary (≈≤150 chars).
    - per column, an auto-derived Title Case ``label`` (override with a
      ``"label"`` key) and an optional ``"short_description"`` plain-language
      one-liner — author it on the key metric and the key filter columns; other
      columns fall back to the full ``description``.

    Each column dict may carry an optional ``"unit"`` key (one of count /
    proportion / ratio / score / rating / currency / percentile), plus optional
    ``"value_min"`` / ``"value_max"`` / ``"null_meaning"``. The contract emitter
    projects ``unit`` to a per-property custom property and derives the
    range-check quality SQL from it (omit ``unit`` for exempt columns).

    Three key-metric keys make the fact table's headline metric machine-readable
    (see ``src/utils/contract_emitter.py``):

    - ``"key_metric": True`` on EXACTLY ONE column — the single metric a consumer
      is most likely to want (prefer a score/proportion over a count, the most
      granular over a derived category). Required on every fact table with
      metric columns (the emitter raises otherwise). A categorical key metric
      additionally needs ``"key_metric_categorical": True`` to opt in.
    - ``"metric_component": "numerator" | "denominator"`` on the count column(s)
      that compose the key metric when it is a rate/average (must be ``unit:
      count``).
    - The third property, ``key_metric_grain_contributor``, is AUTO-DERIVED from
      the grain — no authoring needed.

    Args:
        output_dir: Gold topic directory the transform just wrote
            (``data/gold/{main_topic}/{topic}``); its name is the topic and its
            parent's name is the main_topic.
        name: Dataset name (must equal ``output_dir.name``).
        description: Dataset description (the contract ``purpose``).
        title: Required Title Case human display name (e.g. ``"High School
            Graduation Rates"``).
        summary: Required one-line plain-language description (≈≤150 chars) for
            the website docs + dashboard search.
        columns: Column definitions (the in-code schema declaration).
        source: Data source name.
        source_url: URL to source.
        update_frequency: Update frequency.
        year_range: Year range covered.
        partitioned_by: Accepted for backward compatibility; unused since the
            gold README was retired.
        notes: Accepted for backward compatibility; unused since the gold README
            was retired (transform-internal notes now live in the source only).
        limitations: Optional contract ``limitations`` override (verbatim).
        usage: Optional contract ``usage`` override (verbatim).
        example_queries: Optional contract ``example_queries`` override (verbatim).
        suppressed_to_null: Pass ``False`` for a source with no suppression so
            the contract's null_semantics + derived limitations do not claim
            NULL means "suppressed".
        quality_checks: Optional list of extra per-topic raw-SQL quality dicts
            appended to the contract's object quality (subset/formula/
            functional-dependency invariants).
        dependent_filters: Optional list of ``{"primary", "dependent", "note"?}``
            dicts declaring that ``dependent`` is only meaningful when ``primary``
            is also filtered (e.g. ``rev_exp_subcategory`` needs
            ``rev_exp_category``). Surfaced to consumers as ``filter_hints``.
        version: Contract semver (default ``1.0.0``). Bump the minor for
            additive/backward-compatible schema changes (e.g. tightening a
            column to ``required``), the major for breaking ones.

    Returns:
        Path to the written ODCS contract.
    """
    # Auto-fill validValues for any hand-authored categorical column that lacks
    # them, sourcing observed values from the gold parquet already exported to
    # output_dir. Uses the same categorical-detection logic as the
    # DataFrame-inference path so the contract's `enum` is filled consistently.
    columns = _fill_categorical_valid_values(columns, output_dir)

    # Emit the ODCS contract directly from the in-code declaration. The emitter
    # derives the topic identity from output_dir, the detail levels from the
    # gold just written, and the sub_topic from topic-status.yaml / the ETL tree.
    return write_contract(
        output_dir,
        name=name,
        description=description,
        title=title,
        summary=summary,
        columns=columns,
        source=source,
        source_url=source_url,
        update_frequency=update_frequency,
        year_range=year_range,
        limitations=limitations,
        usage=usage,
        example_queries=example_queries,
        suppressed_to_null=suppressed_to_null,
        quality_checks=quality_checks,
        dependent_filters=dependent_filters,
        version=version,
    )


def infer_columns_from_dataframe(df: pl.DataFrame) -> list[dict[str, Any]]:
    """Infer column definitions from a Polars DataFrame.

    This provides a starting point for column definitions that can be
    enriched with descriptions and examples.

    Args:
        df: Polars DataFrame to analyze.

    Returns:
        List of column definitions with name, type, and nullable.
    """
    columns = []

    for col_name in df.columns:
        col_type = str(df[col_name].dtype)
        null_count = df[col_name].null_count()

        col_def = {
            "name": col_name,
            "type": col_type,
            "nullable": null_count > 0,
            "description": "",  # To be filled in manually
        }

        # Try to get an example value
        non_null = df[col_name].drop_nulls()
        if len(non_null) > 0:
            example = non_null[0]
            # Convert to Python native type for JSON serialization
            if hasattr(example, "item"):
                example = example.item()
            col_def["example"] = example

        # For categorical string columns, capture valid values using the shared
        # categorical-detection logic (known categoricals by name, else by
        # cardinality; identifiers excluded).
        valid_values = infer_valid_values(df[col_name], col_name)
        if valid_values is not None:
            col_def["validValues"] = valid_values

        columns.append(col_def)

    return columns
