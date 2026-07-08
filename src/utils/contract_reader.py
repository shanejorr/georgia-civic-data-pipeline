"""Read-side mirror of ``contract_emitter.py`` — derive config from a contract.

The ODCS contract (``contracts/{main}/{topic}.odcs.yaml``) is the single
machine-readable schema artifact, emitted by each topic's transform. This
module is the one place that *reads* it back for validation purposes:

- ``derive_topic_config`` projects the contract into the validation config
  shape (``type_spec`` / ``metric_columns`` / ``categorical_columns`` /
  ``exempt_pct_columns``) that per-topic ``validate.py`` files used to declare
  by hand. There are no per-topic validation files anymore — the contract is
  the source.
- ``pct_classification`` reads the bounded/ratio percentage split from the
  per-column ``unit`` markers.
- ``grain_columns`` / ``foreign_keys`` / ``quality_sql_entries`` expose the
  contract's row grain, FK descriptors, and executable quality SQL for the
  corresponding validator checks.

Everything here is a pure function over a parsed contract dict; the only I/O
is :func:`load_contract`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl
import yaml

# Inverse of contract_emitter.TYPE_MAP's physicalType column. The emitter only
# ever writes these seven values; anything else in a contract means the
# transform declared an unknown logical type (the emitter's fallback leaks the
# raw string into physicalType), so derivation RAISES rather than guessing.
PHYSICAL_TYPE_TO_POLARS: dict[str, pl.DataType] = {
    "int": pl.Int32,
    "bigint": pl.Int64,
    "double": pl.Float64,
    "float": pl.Float32,
    "string": pl.Utf8,
    "boolean": pl.Boolean,
    "date": pl.Date,
}

# Percentage units: the only two units the percentage-scale check cares about.
PERCENTAGE_UNITS: frozenset[str] = frozenset({"proportion", "ratio"})


class ContractMissingError(FileNotFoundError):
    """Raised when a topic's contract file does not exist."""


def load_contract(contract_path: Path) -> dict:
    """Load and parse an ODCS contract. Raises if missing or unparseable."""
    if not contract_path.exists():
        raise ContractMissingError(f"No contract at {contract_path}")
    contract = yaml.safe_load(contract_path.read_text())
    if not isinstance(contract, dict):
        raise ValueError(f"Contract at {contract_path} is not a mapping")
    return contract


def schema_object(contract: dict) -> dict:
    """Return ``schema[0]`` (the fact/dimension object). Raises if absent."""
    schema = contract.get("schema") or []
    if not schema:
        raise ValueError("contract has no schema objects")
    return schema[0]


def object_custom_value(contract: dict, name: str, default: Any = None) -> Any:
    """Read a schema-object-level custom property by name."""
    for cp in schema_object(contract).get("customProperties") or []:
        if cp.get("property") == name:
            return cp.get("value")
    return default


def property_custom_value(prop: dict, name: str) -> Any | None:
    """Read a per-property custom property by name."""
    for cp in prop.get("customProperties") or []:
        if cp.get("property") == name:
            return cp.get("value")
    return None


def _properties(contract: dict) -> list[dict]:
    return schema_object(contract).get("properties") or []


def derive_type_spec(contract: dict) -> dict[str, pl.DataType]:
    """Map every contract property to its expected polars dtype.

    Raises ``ValueError`` on an unknown/missing ``physicalType`` — that is
    contract corruption (a typo'd ``type`` in the transform's column
    declaration leaks through the emitter's fallback), not a case to paper
    over with Utf8.
    """
    type_spec: dict[str, pl.DataType] = {}
    for prop in _properties(contract):
        name = prop.get("name")
        physical = prop.get("physicalType")
        if physical not in PHYSICAL_TYPE_TO_POLARS:
            raise ValueError(
                f"contract property {name!r} has unknown physicalType "
                f"{physical!r} (expected one of "
                f"{sorted(PHYSICAL_TYPE_TO_POLARS)})"
            )
        type_spec[name] = PHYSICAL_TYPE_TO_POLARS[physical]
    return type_spec


def derive_topic_config(contract: dict) -> dict:
    """Project the contract into the validation TOPIC_CONFIG shape.

    - ``type_spec``: every property, via :data:`PHYSICAL_TYPE_TO_POLARS`.
    - ``metric_columns``: properties with ``column_role == "metric"``, in
      declared order (feeds the null-rate spike check).
    - ``categorical_columns``: properties with ``column_role == "categorical"``
      (values must be snake_case).
    - ``exempt_pct_columns``: metric columns whose ``unit`` is NOT a
      percentage unit (proportion/ratio) — including metrics with no ``unit``
      at all. The bounded/ratio split itself is read separately via
      :func:`pct_classification`; this key only tells the percentage-scale
      check which metrics to ignore.
    """
    metric_columns: list[str] = []
    categorical_columns: list[str] = []
    exempt_pct_columns: list[str] = []

    for prop in _properties(contract):
        name = prop.get("name")
        role = property_custom_value(prop, "column_role")
        if role == "metric":
            metric_columns.append(name)
            unit = property_custom_value(prop, "unit")
            if unit not in PERCENTAGE_UNITS:
                exempt_pct_columns.append(name)
        elif role == "categorical":
            categorical_columns.append(name)

    return {
        "type_spec": derive_type_spec(contract),
        "metric_columns": metric_columns,
        "categorical_columns": categorical_columns,
        "exempt_pct_columns": exempt_pct_columns,
    }


def pct_classification(contract: dict) -> tuple[list[str], list[str]]:
    """Return the (bounded, ratio) percentage-column lists from ``unit`` markers."""
    bounded: list[str] = []
    ratio: list[str] = []
    for prop in _properties(contract):
        unit = property_custom_value(prop, "unit")
        if unit == "proportion":
            bounded.append(prop["name"])
        elif unit == "ratio":
            ratio.append(prop["name"])
    return bounded, ratio


def grain_columns(contract: dict) -> list[str]:
    """The contract's row grain: ``grain`` custom property, else PK positions."""
    grain = object_custom_value(contract, "grain")
    if grain:
        return list(grain)
    keyed = [
        (p["primaryKeyPosition"], p["name"])
        for p in _properties(contract)
        if p.get("primaryKey") and p.get("primaryKeyPosition") is not None
    ]
    return [name for _, name in sorted(keyed)]


def foreign_keys(contract: dict) -> list[dict]:
    """The schema-object ``foreign_keys`` descriptors (may be empty)."""
    return list(object_custom_value(contract, "foreign_keys", default=[]) or [])


def quality_sql_entries(contract: dict) -> list[dict]:
    """Executable quality checks: ``type: sql`` entries with a query."""
    entries = schema_object(contract).get("quality") or []
    return [q for q in entries if q.get("type") == "sql" and q.get("query")]
