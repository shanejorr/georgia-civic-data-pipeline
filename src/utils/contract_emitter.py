"""Emit ODCS v3.1.0 data contracts directly from a transform's schema declaration.

This module is the single source of truth for projecting a topic's in-code
schema declaration (the ``columns=[...]`` list each ``transform.py`` already
authors, plus topic-level metadata) into a git-tracked ODCS contract under
``contracts/{main_topic}/{topic}.odcs.yaml``.

It folds in the projection logic that previously lived in
``scripts/generate_contracts.py`` — column properties, ``column_role``,
``detail_levels`` / ``default_detail``, quality SQL, descriptions, ``sub_topic``,
``year_range`` — so the contract is emitted at transform time with NO separate
generate step and NO ``_metadata.json`` intermediary.

Metric units (``unit``)
-----------------------
The metric semantics are authored in the transform's column declaration via an
optional per-column ``"unit"`` key (omit it for unitless/exempt columns). The
emitter projects that marker to a first-class per-property custom property
``unit`` (mirroring the established ``column_role`` pattern) AND derives the
range-check quality SQL from it:

- ``proportion`` -> bounded on [0, 1] (``{n}_within_unit_interval``);
- ``ratio`` -> non-negative, may exceed 1 (``{n}_non_negative``);
- ``count`` -> non-negative (``{n}_non_negative``);
- ``score`` / ``rating`` / ``percentile`` -> within ``[value_min, value_max]``
  when bounds are resolvable (``percentile`` defaults to 0-100) (``{n}_within_range``);
- ``currency`` -> no derived range check.

``validate.py`` reads the marker back from the contract (``proportion`` ->
bounded bucket, ``ratio`` -> ratio bucket), so the contract — not ``validate.py``
— is the source of the percentage classification.

Key-metric semantics
--------------------
Three properties (``key_metric`` / ``key_metric_grain_contributor`` /
``metric_component``) make a fact table's headline metric machine-readable. They
are parsed by the registry (``src/api/registry.py``) and surfaced on the serving
layer -- the REST schema endpoint, MCP ``describe_dataset``, and (as
``is_key_metric``) the ``query_dataset``/``aggregate`` result columns -- not just
in the contract file:

- ``key_metric`` -- authored ``"key_metric": true`` on EXACTLY ONE column: the
  single metric a consumer is most likely to want given the topic description
  (prefer a score/proportion over a count, the most granular over a category
  derived from it). Emitted both as a per-property marker AND as a schema-object
  pointer ``{property: key_metric, value: <colname>}`` so a consumer resolves the
  headline metric in one lookup (mirrors the native ``primaryKey`` <-> object
  ``grain`` duality). ``build_contract`` RAISES when a table with metric columns
  declares no key metric; ``build_properties`` RAISES when more than one is
  declared. A categorical key metric (rare: a category with no underlying
  numeric) requires an explicit ``"key_metric_categorical": true`` opt-in.
- ``key_metric_grain_contributor`` -- AUTO-DERIVED (no authoring): the grain
  columns that disaggregate the key metric, i.e. ``grain`` minus ``year`` minus
  the geography columns (:data:`GEOGRAPHY_GRAIN_COLUMNS`). Keeps ``demographic``
  (a non-geography FK) and every categorical axis (``test_component``,
  ``grade_level``, ...). Take the distinct values of these columns and no key
  metric value is collapsed.
- ``metric_component`` -- authored ``"numerator"`` / ``"denominator"`` on the
  count column(s) that compose the key metric (only when it is a rate / average /
  proportion). The column must carry ``unit: count``.

NOTE: ``"pct_scale"`` was renamed to ``"unit"``. A leftover ``pct_scale`` key on
a column dict now RAISES so an incomplete migration fails loudly.

Detail levels are read from the gold the transform just wrote (the
``year=*/*.parquet`` basenames under ``output_dir``); no separate filesystem
discovery pass is needed because the transform produced exactly those files.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

from src.utils.sentinels import find_sentinel


class _QuotedStr(str):
    """A string the YAML dumper always renders single-quoted.

    Used to force string-typed ``enum`` values and ``examples`` to emit quoted
    even when they look numeric (e.g. zero-padded codes like ``08`` / ``0189``).
    Without this, PyYAML emits ``08``/``09`` bare (not valid YAML ints) while
    quoting ``'01'``/``'10'``, producing a type-inconsistent enum that a
    YAML-1.2 / JSON-Schema / type-aware consumer can mis-coerce to an integer.
    """


def _represent_quoted_str(dumper: yaml.Dumper, data: _QuotedStr):
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data), style="'")


# Register on the SafeDumper used by write_contract so _QuotedStr scalars always
# round-trip single-quoted (plain ``str`` is unaffected — only enum/example
# values are wrapped). Module-load side effect, idempotent.
yaml.SafeDumper.add_representer(_QuotedStr, _represent_quoted_str)


def _quote_if_str(value: Any) -> Any:
    """Wrap a plain string in :class:`_QuotedStr`; other values pass through."""
    return _QuotedStr(value) if isinstance(value, str) else value


REPO = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO / "contracts"
STATUS_FILE = REPO / "topic-status.yaml"
ETL_ROOT = REPO / "src" / "etl"

# polars/arrow logical type -> (ODCS logicalType, physicalType hint).
TYPE_MAP: dict[str, tuple[str, str]] = {
    "int32": ("integer", "int"),
    "int64": ("integer", "bigint"),
    "float64": ("number", "double"),
    "float32": ("number", "float"),
    "string": ("string", "string"),
    "bool": ("boolean", "boolean"),
    "boolean": ("boolean", "boolean"),
    "date": ("date", "date"),
}

# Fact-table FK columns -> dimension object they reference (by exact column name).
KNOWN_FK: dict[str, str] = {
    "district_code": "districts",
    "school_code": "schools",
    "demographic": "demographics",
    "county_fips": "counties",
}

# Column-name -> explicit role. Mirrors the role taxonomy the API registry uses
# to drive routing (dimension joins, the `category` filter, the metric output
# set). Baking it into the contract removes the boot-time heuristic.
FK_ROLE: dict[str, str] = {
    "district_code": "fk_district",
    "school_code": "fk_school",
    "demographic": "fk_demographic",
    "county_fips": "fk_county",
}

# Detail-level parquet basenames a topic may publish, in default-pick priority
# (schools > districts > counties > federal_districts > states).
DETAIL_PRIORITY: tuple[str, ...] = (
    "schools",
    "districts",
    "counties",
    "federal_districts",
    "states",
)

# Allowed values of the per-column ``unit`` authoring key / contract marker.
UNIT_VALUES: frozenset[str] = frozenset(
    {"count", "proportion", "ratio", "score", "rating", "currency", "percentile"}
)

# Geography identifier columns excluded from ``key_metric_grain_contributor``.
# These (with ``year``) are always part of the grain but are NOT the metric's
# disaggregation axes — only demographic/categorical breakdown columns are.
GEOGRAPHY_GRAIN_COLUMNS: frozenset[str] = frozenset(
    {"district_code", "school_code", "county_fips", "tract_geoid", "state_fips"}
)

# Allowed values of the per-column ``metric_component`` authoring key.
METRIC_COMPONENT_VALUES: frozenset[str] = frozenset({"numerator", "denominator"})

# --- Human-readable label derivation -----------------------------------------
# A column/topic ``label`` is the Title Case display name a human sees (chart
# axis, table header, picker option) vs. the snake_case machine ``name``. It is
# auto-derived from the name by ``derive_label`` and overridable per column via
# a ``label`` key in the transform's column declaration. Tokens matching an
# acronym are upper-cased wholesale; a few unambiguous abbreviations expand;
# minor words stay lower-case unless first.
LABEL_ACRONYMS: frozenset[str] = frozenset(
    {
        "act",
        "sat",
        "ap",
        "ib",
        "el",
        "ell",
        "esol",
        "esl",
        "sped",
        "ccrpi",
        "gaa",
        "eoc",
        "eog",
        "fte",
        "frl",
        "hope",
        "resa",
        "gnets",
        "fesr",
        "gosa",
        "gadoe",
        "sb",
        "id",
        "fips",
        "geoid",
        "wida",
        "access",
        "usda",
        "iep",
        "sgp",
        "sgm",
        "us",
        "ga",
        "nces",
        "lea",
        "rtc",
        "tfs",
        "cte",
        "ctae",
        "eip",
        "ada",
        "fy",
        "c11",
        "c12",
    }
)
# Minor words kept lower-case in Title Case (unless they are the first token).
LABEL_MINOR_WORDS: frozenset[str] = frozenset(
    {
        "of",
        "and",
        "the",
        "to",
        "per",
        "or",
        "for",
        "in",
        "by",
        "a",
        "an",
        "vs",
        "at",
        "on",
        "with",
    }
)
# Safe, unambiguous abbreviation expansions applied before Title-casing.
LABEL_EXPANSIONS: dict[str, str] = {
    "pct": "Percent",
    "num": "Number",
    "avg": "Average",
}

# FK column -> the join descriptor emitted in the schema-object ``foreign_keys``
# custom property, so non-API consumers (MCP, ad-hoc tooling) can resolve a join
# without reading the dimension contract. The ``school_code`` entry uses a
# COMPOSITE target key (district_code + school_code) because school codes are not
# globally unique — this is the accuracy fix over the old single-column join.
FK_DESCRIPTORS: dict[str, dict[str, Any]] = {
    "district_code": {
        "column": "district_code",
        "target_object": "districts",
        "target_columns": ["district_code"],
        # Must match the districts dimension contract's attribute columns (in
        # declared order) — incl. the cross-dataset link key district_census_id
        # — so the redundant fact-side block stays in sync with the actual join
        # (asserted by tests/api/test_contracts_consistency.py).
        "attribute_columns": ["district_name", "district_census_id", "district_type"],
        "scope": "domain",
    },
    "school_code": {
        "column": "school_code",
        "target_object": "schools",
        "target_columns": ["district_code", "school_code"],
        "attribute_columns": ["school_name"],
        "scope": "domain",
    },
    "demographic": {
        "column": "demographic",
        "target_object": "demographics",
        "target_columns": ["demographic"],
        "attribute_columns": ["demographic_label", "demographic_category"],
        "scope": "global",
    },
    "county_fips": {
        "column": "county_fips",
        "target_object": "counties",
        "target_columns": ["county_fips"],
        "attribute_columns": ["county_name"],
        "scope": "global",
    },
}

# Per-topic value invariants not derivable from the column declaration. SQL runs
# on DuckDB via `datacontract test`; {object} is the ODCS placeholder for the
# current object.
DOMAIN_QUALITY: dict[str, list[dict]] = {
    "attendance": [
        {
            "name": "absentee_tiers_partition_population",
            "description": (
                "Where num_students > 0, the three absentee tiers "
                "(<=5, 6-15, >15 days) "
                "partition the population and sum to 1.0 (+/-0.02)."
            ),
            "dimension": "consistency",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE num_students > 0 "
                "AND five_or_fewer_days_absent_rate IS NOT NULL "
                "AND six_to_fifteen_days_absent_rate IS NOT NULL "
                "AND over_15_days_absent_rate IS NOT NULL "
                "AND ABS(five_or_fewer_days_absent_rate "
                "+ six_to_fifteen_days_absent_rate "
                "+ over_15_days_absent_rate - 1.0) > 0.02"
            ),
            "mustBe": 0,
        }
    ],
}


def clean(text: str | None) -> str:
    """Collapse whitespace and undouble ``%%`` for prose fields."""
    return re.sub(r"\s+", " ", (text or "").replace("%%", "%")).strip()


def column_role(name: str, logical_type: str) -> str:
    """Assign an explicit role to a fact column.

    Matches the registry's historical ``_classify_column`` logic exactly:
    ``year`` -> ``year``; the three FK columns -> ``fk_*``; numeric columns
    (``integer``/``number``) -> ``metric``; everything else -> ``categorical``.
    """
    if name == "year":
        return "year"
    if name in FK_ROLE:
        return FK_ROLE[name]
    if logical_type in ("integer", "number"):
        return "metric"
    return "categorical"


def derive_label(name: str) -> str:
    """Derive a Title Case human display name from a snake_case name.

    Mechanical and deterministic: split on ``_``; upper-case acronym tokens
    (:data:`LABEL_ACRONYMS`); expand a few unambiguous abbreviations
    (:data:`LABEL_EXPANSIONS`); keep minor words (:data:`LABEL_MINOR_WORDS`)
    lower-case unless first; leave pure-digit tokens as-is; otherwise
    capitalize. Used for both per-column labels and the topic title fallback;
    the transform may override either via a ``label`` key / ``title`` kwarg
    when the derived form reads wrong (e.g. ``rev_exp_type``).
    """
    tokens = [t for t in str(name).split("_") if t]
    out: list[str] = []
    for i, tok in enumerate(tokens):
        low = tok.lower()
        if low in LABEL_ACRONYMS:
            out.append(low.upper())
        elif low in LABEL_EXPANSIONS:
            out.append(LABEL_EXPANSIONS[low])
        elif tok.isdigit():
            out.append(tok)
        elif low in LABEL_MINOR_WORDS and i != 0:
            out.append(low)
        else:
            out.append(tok[:1].upper() + tok[1:])
    return " ".join(out) or str(name)


def detect_detail_levels(output_dir: Path) -> list[str]:
    """Discover detail levels from the gold ``year=*/*.parquet`` layout.

    Reads the basenames the transform just wrote under ``output_dir`` (the gold
    topic directory). Returns the subset of ``DETAIL_PRIORITY`` present, ordered
    by the default-pick priority so element 0 is the default detail level. A
    topic with no ``detail_level`` split writes a single ``data.parquet`` per
    year and therefore reports no detail levels.
    """
    found: set[str] = set()
    if output_dir.exists():
        for year_dir in output_dir.glob("year=*"):
            if not year_dir.is_dir():
                continue
            for parquet in year_dir.glob("*.parquet"):
                if parquet.stem in DETAIL_PRIORITY:
                    found.add(parquet.stem)
    return [d for d in DETAIL_PRIORITY if d in found]


def resolve_sub_topic(main_topic: str, topic: str) -> str:
    """Resolve a topic's ``sub_topic`` from ``topic-status.yaml`` or the ETL tree.

    The gold layout is flattened (``data/gold/{main}/{topic}``) and does not
    carry the sub_topic, so it is resolved from the authoritative
    ``topic-status.yaml`` key (``{main}/{sub}/{topic}``) with a fallback to
    scanning ``src/etl/{main}/*/{topic}/`` — the same resolution the standalone
    generator used. Raises if it cannot be determined, because the API registry
    requires a non-empty ``sub_topic``.
    """
    if STATUS_FILE.exists():
        status = yaml.safe_load(STATUS_FILE.read_text()) or {}
        for key in status.get("topics") or {}:
            parts = key.split("/")
            if len(parts) == 3 and parts[0] == main_topic and parts[2] == topic:
                return parts[1]
    main_dir = ETL_ROOT / main_topic
    if main_dir.exists():
        for sub_dir in sorted(main_dir.iterdir()):
            if sub_dir.is_dir() and (sub_dir / topic).is_dir():
                return sub_dir.name
    raise ValueError(
        f"could not resolve sub_topic for {main_topic}/{topic} "
        "(not in topic-status.yaml and not found under src/etl/)"
    )


def _validate_unit(col: dict[str, Any]) -> str | None:
    """Read and validate the authored ``unit`` key off a column dict.

    Returns the unit string (or ``None`` when the column declares no unit — that
    is a legitimately exempt column). Raises ``ValueError`` when:

    - the column still carries a legacy ``pct_scale`` key (renamed to ``unit``);
    - the ``unit`` value is not one of :data:`UNIT_VALUES`;
    - both ``value_min`` and ``value_max`` are given and ``value_min`` >
      ``value_max``.
    """
    # Safety net: a leftover pct_scale key means the transform wasn't migrated.
    # Fail loudly rather than silently dropping its range check.
    if "pct_scale" in col:
        raise ValueError(
            f"column {col.get('name')!r}: 'pct_scale' was renamed to 'unit' "
            "(use proportion/ratio); update the transform"
        )

    unit = col.get("unit")
    if unit is None:
        return None
    if unit not in UNIT_VALUES:
        raise ValueError(
            f"column {col.get('name')!r} has invalid unit {unit!r} "
            f"(allowed: {sorted(UNIT_VALUES)} or omit for exempt)"
        )

    vmin = col.get("value_min")
    vmax = col.get("value_max")
    if vmin is not None and vmax is not None and vmin > vmax:
        raise ValueError(
            f"column {col.get('name')!r} has value_min {vmin!r} > value_max {vmax!r}"
        )
    return unit


def _validate_metric_component(col: dict[str, Any]) -> str | None:
    """Read and validate the authored ``metric_component`` key off a column dict.

    Returns ``"numerator"`` / ``"denominator"`` (or ``None`` when the column
    declares none). Raises ``ValueError`` when the value is not one of
    :data:`METRIC_COMPONENT_VALUES`, or when it is set on a column that is not a
    count (``unit != "count"``) — a numerator/denominator of a rate is always a
    count, and flagging the rate column itself is the common mistake to catch.
    """
    mc = col.get("metric_component")
    if mc is None:
        return None
    if mc not in METRIC_COMPONENT_VALUES:
        raise ValueError(
            f"column {col.get('name')!r} has invalid metric_component {mc!r} "
            f"(allowed: {sorted(METRIC_COMPONENT_VALUES)})"
        )
    if col.get("unit") != "count":
        raise ValueError(
            f"column {col.get('name')!r}: metric_component is only valid on a "
            f"count column (unit='count'), got unit={col.get('unit')!r}"
        )
    return mc


def _range_check_for_unit(name: str, unit: str, vmin: Any, vmax: Any) -> dict | None:
    """Derive the range-check quality dict for a column from its ``unit``.

    Returns ``None`` when the unit implies no range check (e.g. ``currency``, or
    a ``score``/``rating`` without resolvable bounds). The check ``name`` for
    ``proportion``/``ratio``/``count`` is reused verbatim from the pre-rename
    emitter so already-marked topics churn minimally.
    """
    if unit == "proportion":
        return {
            "name": f"{name}_within_unit_interval",
            "description": f"{name} is a bounded proportion on the [0, 1] scale.",
            "dimension": "accuracy",
            "query": (
                f"SELECT COUNT(*) FROM {{object}} WHERE {name} IS NOT NULL "
                f"AND ({name} < 0 OR {name} > 1)"
            ),
            "mustBe": 0,
        }
    if unit in ("ratio", "count"):
        kind = (
            "ratio (>= 0; may legitimately exceed 1.0)"
            if unit == "ratio"
            else "count (>= 0)"
        )
        return {
            "name": f"{name}_non_negative",
            "description": f"{name} is a {kind}.",
            "dimension": "accuracy",
            "query": (
                f"SELECT COUNT(*) FROM {{object}} WHERE {name} IS NOT NULL "
                f"AND {name} < 0"
            ),
            "mustBe": 0,
        }
    if unit in ("score", "rating", "percentile"):
        lo, hi = vmin, vmax
        if unit == "percentile":
            lo = 0 if lo is None else lo
            hi = 100 if hi is None else hi
        if lo is None or hi is None:
            # A score/rating with no bounds gets no derived range check.
            return None
        return {
            "name": f"{name}_within_range",
            "description": f"{name} is within its declared [{lo}, {hi}] range.",
            "dimension": "accuracy",
            "query": (
                f"SELECT COUNT(*) FROM {{object}} WHERE {name} IS NOT NULL "
                f"AND ({name} < {lo} OR {name} > {hi})"
            ),
            "mustBe": 0,
        }
    # currency (and anything else) -> no derived range check.
    return None


def build_properties(columns: list[dict]) -> tuple[list[dict], list[dict]]:
    """Project the in-code column declaration to ODCS properties + quality SQL.

    Each ``col`` is the same dict shape the transforms author for
    ``write_data_dictionary``: ``name``, ``type``, ``description`` (optional),
    ``example`` (optional), ``nullable`` (optional, default True),
    ``validValues`` (optional), plus the new optional ``unit`` /
    ``value_min`` / ``value_max`` / ``null_meaning`` keys.
    """
    properties: list[dict] = []
    derived_quality: list[dict] = []

    # At-most-one key metric. (Exactly-one — i.e. that a table WITH metrics
    # declares one — is enforced in build_contract, where the grain and full
    # role classification are known, so low-level build_properties unit tests on
    # a single non-metric column stay valid.)
    key_metric_cols = [c["name"] for c in columns if c.get("key_metric")]
    if len(key_metric_cols) > 1:
        raise ValueError(
            f"multiple key_metric columns declared ({key_metric_cols}); "
            "exactly one allowed per fact table"
        )

    for col in columns:
        name = col["name"]
        logical, physical = TYPE_MAP.get(col["type"], ("string", col["type"]))
        prop: dict = {
            "name": name,
            "logicalType": logical,
            "physicalType": physical,
            "required": not col.get("nullable", True),
        }
        if col.get("description"):
            prop["description"] = clean(col["description"])
        if "example" in col and col["example"] is not None:
            # Force-quote string examples so numeric-looking codes (e.g. the
            # zero-padded school_code '0189') emit quoted, matching the enum.
            prop["examples"] = [_quote_if_str(col["example"])]
        if name in KNOWN_FK:
            if name == "school_code":
                # Composite FK: the schools dimension PK is the pair
                # (district_code, school_code), so a single-column relationship
                # would invite an incorrect non-composite join from MCP/ODCS
                # consumers reading the property-level relationships block. Emit
                # BOTH key parts (the authoritative join is also in the
                # schema-object `foreign_keys` custom property).
                prop["relationships"] = [
                    {"to": "schools.district_code"},
                    {"to": "schools.school_code"},
                ]
            else:
                prop["relationships"] = [{"to": f"{KNOWN_FK[name]}.{name}"}]

        valid = col.get("validValues")
        # Promote the allowlist to the standard ODCS `enum` property field so
        # the API reads valid values as a first-class field instead of parsing
        # the quality SQL below. String values are force-quoted (see _QuotedStr)
        # so zero-padded codes like '08'/'09' emit quoted, consistent with the
        # rest of the enum and the quality SQL.
        if valid and logical == "string":
            prop["enum"] = [_quote_if_str(v) for v in valid]

        # Explicit column role (year/fk_*/categorical/metric) so the registry
        # never has to infer it at boot. ODCS-compliant custom property.
        custom_props = [
            {"property": "column_role", "value": column_role(name, logical)}
        ]
        # Human display name (Title Case). Auto-derived from the column name,
        # overridable via the column's ``label`` key when the derived form reads
        # wrong. Always emitted so every column carries a human label.
        custom_props.append(
            {"property": "label", "value": col.get("label") or derive_label(name)}
        )
        # Optional plain-language one-liner for human docs / dashboard search,
        # authored on the key metric and the key filter columns (others fall
        # back to the full ``description``). Not part of the schema hash.
        if col.get("short_description"):
            custom_props.append(
                {
                    "property": "short_description",
                    "value": clean(col["short_description"]),
                }
            )
        # Metric unit marker, authored in the transform. Omitted for exempt
        # columns. Mirrors the column_role custom-property pattern. RAISES if a
        # leftover `pct_scale` key is present (renamed to `unit`).
        unit = _validate_unit(col)
        vmin = col.get("value_min")
        vmax = col.get("value_max")
        if unit is not None:
            custom_props.append({"property": "unit", "value": unit})
            if vmin is not None:
                custom_props.append({"property": "value_min", "value": vmin})
            if vmax is not None:
                custom_props.append({"property": "value_max", "value": vmax})
        # Optional per-column null semantics override (what NULL means here).
        if col.get("null_meaning") is not None:
            custom_props.append(
                {"property": "null_meaning", "value": col["null_meaning"]}
            )
        # Key-metric marker (authored on exactly one column). A non-metric (e.g.
        # categorical) key metric is allowed only with an explicit opt-in so the
        # unusual case is loud rather than a silent role mismatch.
        if col.get("key_metric"):
            role = column_role(name, logical)
            if role != "metric" and not col.get("key_metric_categorical"):
                raise ValueError(
                    f"column {name!r}: key_metric set on a non-metric column "
                    f"(role={role!r}); set key_metric_categorical=True to confirm "
                    "a categorical key metric"
                )
            custom_props.append({"property": "key_metric", "value": True})
        # Numerator/denominator of the key metric (count columns only).
        metric_component = _validate_metric_component(col)
        if metric_component is not None:
            custom_props.append(
                {"property": "metric_component", "value": metric_component}
            )
        # Total/"all" sentinel for enum columns: whether the allowlist carries an
        # aggregate total value and which one (e.g. ``all`` / ``total``). Derived
        # from the enum via the shared sentinel helper (the single source of
        # truth, mirrored in the dashboard). A grain-contributor categorical with
        # no total "cannot be aggregated" — consumers must pin a single value.
        if valid and logical == "string":
            total_value = find_sentinel([str(v) for v in valid])
            custom_props.append(
                {"property": "has_total", "value": total_value is not None}
            )
            if total_value is not None:
                custom_props.append(
                    {"property": "total_value", "value": _quote_if_str(total_value)}
                )
        prop["customProperties"] = custom_props

        if valid and logical == "string":
            quoted = ", ".join("'" + str(v).replace("'", "''") + "'" for v in valid)
            derived_quality.append(
                {
                    "name": f"{name}_in_allowed_values",
                    "description": (
                        f"{name} is one of the {len(valid)} canonical codes."
                    ),
                    "dimension": "conformity",
                    "query": (
                        f"SELECT COUNT(*) FROM {{object}} WHERE {name} IS NOT "
                        f"NULL AND {name} NOT IN ({quoted})"
                    ),
                    "mustBe": 0,
                }
            )

        # Range checks DERIVED from the per-column unit marker.
        if unit is not None:
            range_check = _range_check_for_unit(name, unit, vmin, vmax)
            if range_check is not None:
                derived_quality.append(range_check)

        properties.append(prop)
    return properties, derived_quality


def _unit_for_property(prop: dict) -> str | None:
    """Return the ``unit`` custom-property value for a projected property, if any."""
    for cp in prop.get("customProperties") or []:
        if cp.get("property") == "unit":
            return cp.get("value")
    return None


def derive_grain(
    properties: list[dict], exclude: frozenset[str] | set[str] = frozenset()
) -> list[str]:
    """Derive the logical row grain from projected properties, in declared order.

    Grain = ``year`` (if present) + present FK columns (district_code,
    school_code, demographic, in declared order) + all categorical columns, all
    classified via :func:`column_role` (the same function the emitter uses
    everywhere). The order is the property declaration order.

    ``exclude`` names are dropped from the grain even when their role would
    otherwise place them there. Use it (via a column's ``exclude_from_grain``
    key) for derived attribute categoricals that describe a row rather than
    identify it — e.g. a per-row status flag like ``ccrpi_flag`` /
    ``is_non_compliant`` that is functionally dependent on the real key and so
    is not a row-identity axis (and is NULL-bearing, making a NULL-in-PK odd).
    """
    grain: list[str] = []
    for prop in properties:
        if prop["name"] in exclude:
            continue
        role = column_role(prop["name"], prop.get("logicalType", ""))
        if role == "year" or role.startswith("fk_") or role == "categorical":
            grain.append(prop["name"])
    return grain


def detect_years(output_dir: Path) -> list[int]:
    """Discover the sorted list of years present from the gold ``year=*`` layout.

    Reads the ``year=YYYY`` partition dir names the transform just wrote under
    ``output_dir``. Used to emit machine-readable ``available_years`` /
    ``year_gaps`` custom properties so API/MCP query planners do not assume a
    contiguous range from ``year_range`` alone.
    """
    years: set[int] = set()
    if output_dir.exists():
        for year_dir in output_dir.glob("year=*"):
            if not year_dir.is_dir():
                continue
            raw = year_dir.name.split("=", 1)[1]
            try:
                years.add(int(raw))
            except ValueError:
                continue
    return sorted(years)


def _apply_primary_key(properties: list[dict], grain: list[str]) -> None:
    """Mark each grain property with native ``primaryKey`` + ``primaryKeyPosition``.

    Mutates ``properties`` in place. ``primaryKeyPosition`` is 1-based in grain
    order. ``required`` is intentionally NOT changed — FK columns stay nullable
    (they are NULL at higher aggregation levels); the primaryKey here is the
    logical cross-detail-level key, not a not-null constraint.
    """
    position = {name: i + 1 for i, name in enumerate(grain)}
    for prop in properties:
        if prop["name"] in position:
            prop["primaryKey"] = True
            prop["primaryKeyPosition"] = position[prop["name"]]


def _apply_grain_contributors(properties: list[dict], grain: list[str]) -> None:
    """Flag the grain columns that disaggregate the key metric.

    Mutates ``properties`` in place, appending a
    ``key_metric_grain_contributor: true`` custom property to each grain column
    that is neither ``year`` nor a geography identifier
    (:data:`GEOGRAPHY_GRAIN_COLUMNS`). These are exactly the demographic /
    categorical breakdown axes (``demographic``, ``test_component``,
    ``grade_level``, ...) — take their distinct values and no key-metric value is
    collapsed. Derived from the final grain, so it cannot drift from it and
    correctly excludes ``exclude_from_grain`` columns (already absent from grain).
    """
    contributors = set(grain) - {"year"} - GEOGRAPHY_GRAIN_COLUMNS
    for prop in properties:
        if prop["name"] in contributors:
            prop.setdefault("customProperties", []).append(
                {"property": "key_metric_grain_contributor", "value": True}
            )


def _custom_value(prop: dict, name: str) -> Any:
    """Return a projected property's custom-property value by name, else None."""
    for cp in prop.get("customProperties") or []:
        if cp.get("property") == name:
            return cp.get("value")
    return None


def _key_metric_name(properties: list[dict]) -> str | None:
    """Return the name of the column flagged ``key_metric``, if any."""
    for prop in properties:
        if _custom_value(prop, "key_metric") is True:
            return prop["name"]
    return None


def _granularity_sentence(
    grain: list[str], detail_levels: list[str] | None = None
) -> str:
    """Build the native ``dataGranularityDescription`` sentence from the grain.

    The "(geography columns are NULL at higher aggregation levels)" qualifier is
    only accurate when the topic actually publishes more than one detail level
    (so a row can be a state/district aggregate with NULL geography). For a
    single-detail-level topic (e.g. school-only) no higher aggregation level
    exists, so the qualifier is dropped to avoid misleading consumers.
    """
    if not grain:
        return "One row per record."
    base = "One row per " + ", ".join(grain)
    if detail_levels and len(detail_levels) >= 2:
        return base + " (geography columns are NULL at higher aggregation levels)."
    return base + "."


def _derive_limitations(
    detail_levels: list[str], suppressed_to_null: bool = True
) -> str:
    """Derive accurate limitations prose from the topic's detail levels.

    ``suppressed_to_null`` controls the opening sentence: a topic whose source
    has no suppression (so a 0 is real and NULL never means "suppressed")
    should pass ``False`` to drop the misleading "Suppressed cells are NULL"
    line. Topics needing fully custom prose pass an explicit ``limitations``
    override upstream instead.
    """
    if suppressed_to_null:
        parts = ["Suppressed cells are NULL (not zero)."]
    else:
        parts = ["This source has no suppression; a 0 is a real reported value."]
    if "states" in detail_levels:
        if "counties" in detail_levels:
            parts.append("State rows have NULL county_fips.")
        else:
            parts.append("State rows have NULL district_code and school_code.")
    if "districts" in detail_levels:
        parts.append("District rows have NULL school_code.")
    if not detail_levels:
        parts.append("This table is not geography-partitioned.")
    return " ".join(parts)


def _derive_usage(properties: list[dict]) -> str:
    """Derive a usage sentence conditional on which FK columns exist."""
    names = {p["name"] for p in properties}
    joins: list[str] = []
    if "district_code" in names:
        joins.append("the districts dimension on district_code")
    if "school_code" in names:
        joins.append("the schools dimension on district_code + school_code")
    if "county_fips" in names:
        joins.append("the counties dimension on county_fips")
    if "demographic" in names:
        joins.append("the demographics dimension on demographic")
    sentences = ["Star-schema fact table."]
    if joins:
        sentences.append("Join " + "; ".join(joins) + ".")
    sentences.append("Read directly with DuckDB over Parquet.")
    return " ".join(sentences)


def _build_foreign_keys(properties: list[dict]) -> list[dict]:
    """Emit one FK descriptor per FK column present (for non-API consumers)."""
    names = {p["name"] for p in properties}
    return [
        FK_DESCRIPTORS[col]
        for col in ("district_code", "school_code", "county_fips", "demographic")
        if col in names and col in FK_DESCRIPTORS
    ]


def _latest_year_with_value(
    output_dir: Path | None, column: str, value: str, year_max: int
) -> int:
    """Latest gold year in which ``column == value`` has rows (else ``year_max``).

    A filtered example query must pair its filter value with a year that value
    actually covers: an era-bound enum value (e.g. a ``calendar_year`` edition
    ending a year before the ``fiscal_year`` edition) paired with the topic's
    global latest year yields a zero-row example. Scans only ``column`` +
    ``year`` from the gold the transform just wrote, so the result is
    deterministic for a given gold output. Falls back to ``year_max`` when no
    gold is available (``output_dir=None``) or the scan cannot resolve.
    """
    if output_dir is None:
        return year_max
    import polars as pl  # local: only transforms hit this path, and they have it

    try:
        latest = (
            pl.scan_parquet(str(output_dir / "year=*" / "*.parquet"))
            .filter(pl.col(column) == value)
            .select(pl.col("year").max())
            .collect()
            .item()
        )
    except Exception:  # noqa: BLE001 — malformed gold already fails validation
        return year_max
    return int(latest) if latest is not None else year_max


def _build_example_queries(
    topic: str,
    properties: list[dict],
    year_max: int | None,
    default_detail: str | None,
    output_dir: Path | None = None,
) -> list[dict]:
    """Derive 2-3 deterministic example DuckDB queries from the topic shape.

    Deterministic by construction: uses ``year_max`` from the year range, the
    first FK example, and the first categorical example / first sorted enum
    value. Any query whose inputs are absent is skipped. Filtered examples
    pair the filter value with the latest gold year that value actually
    covers (see :func:`_latest_year_with_value`), so no derived example
    returns zero rows.
    """
    queries: list[dict] = []
    if year_max is None:
        return queries

    # 1. Latest year + default detail.
    detail_note = f", {default_detail} detail" if default_detail else ""
    queries.append(
        {
            "description": f"Latest year ({year_max}){detail_note}".rstrip(),
            "query": f"SELECT * FROM {topic} WHERE year = {year_max} LIMIT 100",
        }
    )

    # 2. Filter by a sample district_code (if present and carries an example).
    for prop in properties:
        if prop["name"] != "district_code":
            continue
        examples = prop.get("examples") or []
        if examples:
            val = examples[0]
            yr = _latest_year_with_value(output_dir, "district_code", val, year_max)
            queries.append(
                {
                    "description": f"District {val} in {yr}",
                    "query": (
                        f"SELECT * FROM {topic} WHERE district_code = '{val}' "
                        f"AND year = {yr} LIMIT 100"
                    ),
                }
            )
        break

    # 3. Filter by the first categorical column's example, else its first enum.
    for prop in properties:
        role = column_role(prop["name"], prop.get("logicalType", ""))
        if role != "categorical":
            continue
        col = prop["name"]
        examples = prop.get("examples") or []
        enum = prop.get("enum") or []
        if examples:
            val = examples[0]
        elif enum:
            val = sorted(enum)[0]
        else:
            break
        yr = _latest_year_with_value(output_dir, col, val, year_max)
        queries.append(
            {
                "description": f"Filter by {col} = {val}",
                "query": (
                    f"SELECT * FROM {topic} WHERE {col} = '{val}' "
                    f"AND year = {yr} LIMIT 100"
                ),
            }
        )
        break

    return queries


def _schema_hash(properties: list[dict], grain: list[str]) -> str:
    """Deterministic sha256 over the projected schema shape.

    Canonical structure: one entry per property in declared order =
    ``[name, logicalType, physicalType, required, column_role, unit_or_null,
    sorted(enum or [])]``, plus the grain list at the end. No timestamps, no set
    iteration (enums sorted), property order is the deterministic authored order.
    A description-only change does NOT alter the hash; a rename or type change
    does.
    """
    canonical: list = []
    for prop in properties:
        canonical.append(
            [
                prop["name"],
                prop.get("logicalType"),
                prop.get("physicalType"),
                bool(prop.get("required", False)),
                column_role(prop["name"], prop.get("logicalType", "")),
                _unit_for_property(prop),
                sorted(prop.get("enum") or []),
            ]
        )
    canonical.append(grain)
    blob = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_contract(
    main_topic: str,
    sub_topic: str,
    topic: str,
    *,
    description: str,
    title: str,
    summary: str,
    columns: list[dict],
    source: str | None,
    source_url: str | None,
    update_frequency: str | None,
    year_range: tuple[int, int] | list[int] | None,
    detail_levels: list[str],
    limitations: str | None = None,
    usage: str | None = None,
    example_queries: list[dict] | None = None,
    suppressed_to_null: bool = True,
    quality_checks: list[dict] | None = None,
    available_years: list[int] | None = None,
    dependent_filters: list[dict] | None = None,
    version: str = "1.0.0",
    output_dir: Path | None = None,
) -> dict:
    """Build the full ODCS contract document for one topic.

    Pure projection from the in-code declaration. All additions over the legacy
    contract are additive custom properties (or the native ODCS ``primaryKey`` /
    ``primaryKeyPosition`` / ``dataGranularityDescription`` fields), except the
    ``pct_scale``->``unit`` rename.

    Optional ``limitations`` / ``usage`` / ``example_queries`` overrides, when
    given, are used verbatim (limitations/usage cleaned) instead of the derived
    prose / queries.

    ``suppressed_to_null`` (default True) sets the ``null_semantics`` custom
    property and the derived-limitations opening sentence; pass ``False`` for a
    source with no suppression so the contract does not claim NULL means
    "suppressed". ``quality_checks`` is a list of extra raw-SQL quality dicts
    (same shape as :data:`DOMAIN_QUALITY` entries) authored per-topic in the
    transform and appended to the object quality. ``available_years``, when
    given, emits machine-readable ``available_years`` + derived ``year_gaps``
    custom properties so consumers do not assume a contiguous ``year_range``.
    ``version`` is the contract semver (default ``1.0.0``); bump the minor for
    additive/backward-compatible schema changes (e.g. tightening a column to
    ``required``) and the major for breaking ones.
    """
    # Human-facing topic metadata (required): a Title Case display ``title`` and
    # a one-line plain-language ``summary`` for the website docs + dashboard
    # search. Authored in the transform; the emitter refuses to ship a contract
    # without them so every served topic is human-discoverable.
    title_text = clean(title)
    summary_text = clean(summary)
    if not title_text:
        raise ValueError(
            f"topic {topic!r}: 'title' is required (human-readable display name)"
        )
    if not summary_text:
        raise ValueError(
            f"topic {topic!r}: 'summary' is required "
            "(one-line plain-language description)"
        )

    properties, derived_quality = build_properties(columns)
    default_detail = detail_levels[0] if detail_levels else None

    # #4 grain / logical primary key (auto-derived, mutates properties in place).
    # Columns flagged ``exclude_from_grain`` (derived attribute flags) are kept
    # out of the grain/PK even though their role would otherwise include them.
    grain_exclude = {c["name"] for c in columns if c.get("exclude_from_grain")}
    grain = derive_grain(properties, grain_exclude)
    _apply_primary_key(properties, grain)
    # Flag the key metric's disaggregation axes (auto-derived from the grain).
    _apply_grain_contributors(properties, grain)

    # Exactly-one key metric: any fact table with metric columns must name its
    # single headline metric. (At-most-one is enforced upstream in
    # build_properties; here we also require at-least-one when metrics exist.)
    key_metric_col = _key_metric_name(properties)
    metric_cols = [
        p["name"] for p in properties if _custom_value(p, "column_role") == "metric"
    ]
    if metric_cols and key_metric_col is None:
        raise ValueError(
            f"topic {topic!r}: a fact table with metric columns ({metric_cols}) "
            'must declare exactly one key_metric (set "key_metric": True on the '
            "single headline metric column)"
        )

    object_quality: list[dict] = [
        {
            "name": "non_empty",
            "description": "The dataset has at least one row.",
            "dimension": "completeness",
            "query": "SELECT COUNT(*) FROM {object}",
            "mustBeGreaterThan": 0,
        }
    ]
    object_quality += derived_quality
    object_quality += DOMAIN_QUALITY.get(topic, [])
    # Per-topic semantic checks authored in the transform (subset/formula/
    # functional-dependency invariants the column declaration can't express).
    object_quality += list(quality_checks or [])
    # ODCS quality.type defaults to `library`; raw-SQL checks MUST declare
    # `type: sql` or the CLI silently skips them. Put `type` first.
    object_quality = [
        ({"type": "sql", **q} if "query" in q and "type" not in q else q)
        for q in object_quality
    ]

    yr = year_range or [None, None]
    year_max = yr[1] if isinstance(yr[1], int) else None

    # #6 limitations + usage prose (derived unless overridden).
    limitations_text = (
        clean(limitations)
        if limitations is not None
        else _derive_limitations(detail_levels, suppressed_to_null)
    )
    usage_text = clean(usage) if usage is not None else _derive_usage(properties)

    # #9 example queries (derived unless overridden; output_dir grounds the
    # filtered examples in years the filter value actually covers).
    examples = (
        example_queries
        if example_queries is not None
        else _build_example_queries(
            topic, properties, year_max, default_detail, output_dir
        )
    )

    # #7 self-describing layout.
    path_template = f"{main_topic}/{topic}/year={{year}}/{{detail}}.parquet"

    # Top-level custom properties: provenance + deterministic schema hash, plus
    # machine-readable year coverage (available_years + derived year_gaps) when
    # the caller supplied the years present in gold, so consumers do not assume
    # ``year_range`` is contiguous.
    top_custom_props: list[dict] = [
        # Human-facing topic metadata first (display name + scannable one-liner).
        {"property": "title", "value": title_text},
        {"property": "summary", "value": summary_text},
        {"property": "source", "value": source},
        {"property": "source_url", "value": source_url},
        {"property": "update_frequency", "value": update_frequency},
        {"property": "year_range", "value": f"{yr[0]}-{yr[1]}"},
        # #8 deterministic schema hash (no timestamps; sorted enums).
        {"property": "schema_hash", "value": _schema_hash(properties, grain)},
    ]
    if available_years:
        years_present = sorted(set(available_years))
        gaps = [
            y
            for y in range(years_present[0], years_present[-1] + 1)
            if y not in set(years_present)
        ]
        top_custom_props.append({"property": "available_years", "value": years_present})
        top_custom_props.append({"property": "year_gaps", "value": gaps})

    # Schema-object custom properties: API routing inputs + the new semantics
    # for MCP/LLM consumers (grain, null semantics, layout, foreign keys, etc.).
    schema_custom_props = [
        {"property": "sub_topic", "value": sub_topic},
        {"property": "detail_levels", "value": detail_levels},
        {"property": "default_detail", "value": default_detail},
        {"property": "grain", "value": grain},
        # Schema-object pointer to the headline metric (one-lookup resolution for
        # MCP/LLM consumers). Omitted only for the degenerate metric-less case.
        *(
            [{"property": "key_metric", "value": key_metric_col}]
            if key_metric_col is not None
            else []
        ),
        {
            "property": "null_semantics",
            "value": {
                "suppressed_to_null": suppressed_to_null,
                "zero_is_real": True,
            },
        },
        {"property": "partition_columns", "value": ["year"]},
        {"property": "path_template", "value": path_template},
        {"property": "foreign_keys", "value": _build_foreign_keys(properties)},
        {"property": "example_queries", "value": examples},
        # Paired-filter groups (author-declared): each {primary, dependent, note?}
        # marks a dependent categorical only meaningful alongside its primary
        # (e.g. rev_exp_subcategory needs rev_exp_category). Omitted when none.
        *(
            [{"property": "dependent_filter", "value": dependent_filters}]
            if dependent_filters
            else []
        ),
    ]

    return {
        "apiVersion": "v3.1.0",
        "kind": "DataContract",
        "id": f"{main_topic}.{topic}",
        "name": topic,
        "version": version,
        "status": "active",
        "domain": main_topic,
        "tenant": "georgia-public-data",
        "description": {
            "purpose": clean(description),
            "usage": usage_text,
            "limitations": limitations_text,
        },
        "tags": [
            main_topic,
            clean(source).lower().split("(")[0].strip() or "unknown",
            topic,
        ],
        "servers": [
            {
                "server": "s3_gold",
                "type": "s3",
                "location": f"s3://georgia-data-gold/{main_topic}/{topic}/**/*.parquet",
                "format": "parquet",
            },
            {
                "server": "local_gold",
                "type": "local",
                # ODCS `local`-type servers require `path` (+ `format`); only
                # `s3`/object-store servers use `location`. Using `location`
                # here fails `datacontract lint` ("servers[1] must contain
                # ['path']").
                "path": f"data/gold/{main_topic}/{topic}/**/*.parquet",
                "format": "parquet",
            },
        ],
        "schema": [
            {
                "name": topic,
                "logicalType": "object",
                "physicalType": "parquet",
                "physicalName": topic,
                "description": (
                    f"{topic} fact table, year-partitioned Parquet "
                    "(split by detail level where present)."
                ),
                # Native ODCS grain description (human sentence).
                "dataGranularityDescription": _granularity_sentence(
                    grain, detail_levels
                ),
                # Detail levels + sub_topic + the new semantics are API/MCP
                # inputs ODCS has no native field for; encoded as custom props.
                "customProperties": schema_custom_props,
                "properties": properties,
                "quality": object_quality,
            }
        ],
        "customProperties": top_custom_props,
    }


def contract_path_for(main_topic: str, topic: str) -> Path:
    """Return the git-tracked contract path for a topic."""
    return CONTRACTS_DIR / main_topic / f"{topic}.odcs.yaml"


def write_contract(
    output_dir: Path,
    *,
    name: str,
    description: str,
    title: str,
    summary: str,
    columns: list[dict],
    source: str | None = None,
    source_url: str | None = None,
    update_frequency: str | None = "annual",
    year_range: tuple[int, int] | list[int] | None = None,
    limitations: str | None = None,
    usage: str | None = None,
    example_queries: list[dict] | None = None,
    suppressed_to_null: bool = True,
    quality_checks: list[dict] | None = None,
    dependent_filters: list[dict] | None = None,
    version: str = "1.0.0",
) -> Path:
    """Emit the ODCS contract for a topic to ``contracts/{main}/{topic}.odcs.yaml``.

    Called at transform time (via ``write_data_dictionary``). Derives the topic
    identity from ``output_dir`` (``data/gold/{main}/{topic}``), the detail
    levels and the years present from the gold the transform just wrote under
    ``output_dir``, and the ``sub_topic`` from ``topic-status.yaml`` / the ETL
    tree.

    Args:
        output_dir: Gold topic directory the transform just wrote
            (e.g. ``data/gold/education/act_scores``).
        name: Topic name (e.g. ``act_scores``); must equal the gold dir name.
        description: Dataset description (the contract ``purpose``).
        title: Required Title Case human display name (e.g. ``"High School
            Graduation Rates"``) — the contract ``title`` custom property.
        summary: Required one-line plain-language description (≈≤150 chars) for
            website docs + dashboard search — the contract ``summary`` property.
        columns: In-code column declaration (the same dicts authored for
            ``write_data_dictionary``), each optionally carrying ``unit`` /
            ``value_min`` / ``value_max`` / ``null_meaning`` /
            ``exclude_from_grain``.
        source / source_url / update_frequency / year_range: topic-level metadata.
        limitations / usage / example_queries: optional overrides used verbatim
            instead of the derived prose / queries.
        suppressed_to_null: False for a source with no suppression (drives
            null_semantics + derived limitations).
        quality_checks: extra per-topic raw-SQL quality dicts appended to the
            contract's object quality.
        version: contract semver (default ``1.0.0``); bump the minor for
            additive schema changes (e.g. a column tightened to ``required``).

    Returns:
        Path to the written contract file.
    """
    resolved = output_dir.resolve()
    topic = resolved.name
    main_topic = resolved.parent.name
    sub_topic = resolve_sub_topic(main_topic, topic)
    detail_levels = detect_detail_levels(output_dir)
    available_years = detect_years(output_dir)

    contract = build_contract(
        main_topic,
        sub_topic,
        topic,
        description=description,
        title=title,
        summary=summary,
        columns=columns,
        source=source,
        source_url=source_url,
        update_frequency=update_frequency,
        year_range=year_range,
        detail_levels=detail_levels,
        limitations=limitations,
        usage=usage,
        example_queries=example_queries,
        suppressed_to_null=suppressed_to_null,
        quality_checks=quality_checks,
        available_years=available_years,
        dependent_filters=dependent_filters,
        version=version,
        output_dir=output_dir,
    )

    out = contract_path_for(main_topic, topic)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as fh:
        yaml.safe_dump(contract, fh, sort_keys=False, width=100, allow_unicode=True)
    return out
