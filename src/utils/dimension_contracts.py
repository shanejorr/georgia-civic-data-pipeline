"""Shared dimension-contract discovery — the single source of truth for which
dimension contracts exist, their primary keys, and how their on-disk parquet is
located.

Both the serving layer (``src.api.registry.build_registry``) and the pipeline's
referential-integrity check (``scripts/check_referential_integrity.py``) need to
know the same three facts about each gold dimension:

* **which** dimension contracts exist (the two ``_dimensions/`` directories and
  the ``entity_kind: dimension`` marker that identifies a dimension contract);
* each dimension's **primary key** (ordered by ``primaryKeyPosition``);
* how to resolve its **parquet path** (``scope`` + ``physical_basename`` +
  domain ``main_topic``).

Keeping these here means the integrity check verifies *exactly* the dimensions
(and PK columns, and files) the running API depends on — they cannot drift apart
because they read the same code. The API registry wraps each discovered
dimension into a much richer ``DimensionSpec`` (columns, link keys, semantics,
…) via ``dim_spec_from_contract``; this module only exposes the lean metadata
that both consumers share. Pure functions over parsed contract dicts; the only
I/O is :func:`iter_dimension_metadata`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def dimension_source_dirs(contracts_dir: Path) -> list[tuple[Path, str | None]]:
    """The ``(directory, domain main_topic)`` pairs the dimension glob walks.

    Domain-scoped dims live under ``contracts/education/_dimensions/`` (their
    domain ``main_topic`` is ``education``); global dims live under
    ``contracts/_dimensions/`` (``main_topic`` is ``None``). The order —
    education first, then global — is the discovery order the registry and the
    integrity check both iterate in.
    """
    return [
        (contracts_dir / "education" / "_dimensions", "education"),
        (contracts_dir / "_dimensions", None),
    ]


def _schema_custom_property(schema_obj: dict[str, Any], name: str) -> Any:
    for cp in schema_obj.get("customProperties", []) or []:
        if cp.get("property") == name:
            return cp.get("value")
    return None


def _property_custom_property(prop: dict[str, Any], name: str) -> Any:
    for cp in prop.get("customProperties", []) or []:
        if cp.get("property") == name:
            return cp.get("value")
    return None


def is_dimension_contract(contract: dict[str, Any]) -> bool:
    """True iff the contract's schema object is marked ``entity_kind: dimension``.

    The absence of this marker (and of ``sub_topic``/``detail_levels``) is the
    guard that keeps a dimension contract from being parsed as a fact topic, and
    vice versa.
    """
    schema = contract.get("schema") or []
    if not schema:
        return False
    return _schema_custom_property(schema[0], "entity_kind") == "dimension"


def dimension_primary_key(contract: dict[str, Any]) -> tuple[str, ...]:
    """The dimension's primary key: key columns ordered by ``primaryKeyPosition``.

    Matches ``dim_spec_from_contract``'s derivation exactly — a column is part of
    the PK iff its ``column_role`` custom property is ``key`` and it carries a
    ``primaryKeyPosition`` — so the integrity check asserts uniqueness on the
    same columns the API joins on (composite ``(district_code, school_code)`` for
    schools).
    """
    schema_obj = contract["schema"][0]
    keyed: list[tuple[int, str]] = []
    for prop in schema_obj.get("properties", []) or []:
        role = _property_custom_property(prop, "column_role")
        pos = prop.get("primaryKeyPosition")
        if role == "key" and pos is not None:
            keyed.append((int(pos), prop["name"]))
    keyed.sort()
    return tuple(name for _, name in keyed)


@dataclass(frozen=True)
class DimensionMeta:
    """Lean metadata about one gold dimension, shared across serving + pipeline.

    The subset of ``DimensionSpec`` needed to locate a dimension's parquet and
    assert its primary-key invariant, derived straight from the dimension
    contract.
    """

    name: str
    scope: str  # "domain" | "global"
    main_topic: str | None  # set for domain-scoped dims, None for global
    physical_basename: str
    primary_key: tuple[str, ...]
    source_path: Path


def dimension_parquet_path(gold_root: Path, meta: DimensionMeta) -> Path:
    """Resolve a dimension's on-disk parquet path (mirrors the API engine).

    Global dims live at ``<gold_root>/_dimensions/<basename>.parquet``; domain
    dims at ``<gold_root>/<main_topic>/_dimensions/<basename>.parquet`` (falling
    back to ``education`` for a domain dim with no ``main_topic``, matching the
    engine).
    """
    if meta.scope == "global":
        return gold_root / "_dimensions" / f"{meta.physical_basename}.parquet"
    sub = meta.main_topic or "education"
    return gold_root / sub / "_dimensions" / f"{meta.physical_basename}.parquet"


def iter_dimension_metadata(contracts_dir: Path) -> list[DimensionMeta]:
    """Discover every dimension contract under ``contracts_dir`` as lean metadata.

    Walks the two ``_dimensions/`` directories (education first, then global; see
    :func:`dimension_source_dirs`), reading each ``*.odcs.yaml`` in sorted order
    and keeping the ones marked ``entity_kind: dimension``. The resulting order
    matches the API registry's dimension-discovery pass.

    Unlike the registry's resilient boot (which skips a malformed dimension
    contract and keeps serving), this raises on an unreadable/malformed contract
    — the integrity check *wants* a hard failure if a dimension the API relies on
    cannot be read.
    """
    out: list[DimensionMeta] = []
    for dim_dir, dim_main_topic in dimension_source_dirs(contracts_dir):
        if not dim_dir.is_dir():
            continue
        for dim_path in sorted(dim_dir.glob("*.odcs.yaml")):
            contract = yaml.safe_load(dim_path.read_text())
            if not isinstance(contract, dict) or not is_dimension_contract(contract):
                continue
            schema_obj = contract["schema"][0]
            scope = _schema_custom_property(schema_obj, "scope")
            physical_basename = _schema_custom_property(schema_obj, "physical_basename")
            out.append(
                DimensionMeta(
                    name=contract["name"],
                    scope=scope,
                    main_topic=dim_main_topic if scope == "domain" else None,
                    physical_basename=physical_basename,
                    primary_key=dimension_primary_key(contract),
                    source_path=dim_path,
                )
            )
    return out
