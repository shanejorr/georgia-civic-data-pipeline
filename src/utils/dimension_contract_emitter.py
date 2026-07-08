"""Emit ODCS v3.1.0 data contracts for the gold dimension tables.

This module is the dimension-table sibling of
``src/utils/contract_emitter.py`` (which emits the per-topic *fact* contracts).
Where the fact emitter projects a transform's in-code column declaration, the
dimension schemas are small and known, so each dimension contract's schema is
authored *in-code here* (the enum vocabularies are derived live from the build
scripts' code constants — ``DISTRICT_TYPE_RULES`` / ``DISTRICT_TYPE_OVERRIDES`` /
``HARDCODED_DISTRICTS`` for ``district_type`` and ``DEMOGRAPHIC_CATEGORIES`` for
``demographic_category`` — so they never drift from the live data).

Each dimension contract:

- declares the dimension's columns as ODCS ``properties`` with a per-property
  ``customProperties.column_role`` of ``key`` (a primary-key column) or
  ``attribute`` (a non-key column), and native ``primaryKey`` /
  ``primaryKeyPosition`` on the key columns;
- carries schema-object custom properties ``entity_kind: dimension``,
  ``scope: domain|global`` and ``physical_basename`` — and DELIBERATELY OMITS
  ``sub_topic`` / ``detail_levels`` / ``default_detail`` so the API's fact-topic
  loader never mistakes a dimension contract for a topic;
- emits a ``non_empty`` quality check plus one ``{col}_in_allowed_values`` SQL
  check per enumerated column, mirroring the fact emitter (every check carries
  ``type: sql`` so ``datacontract test`` does not silently skip it);
- carries a deterministic top-level ``schema_hash`` custom property (same
  canonicalization style as the fact emitter — sorted enums, no timestamps).

The contracts live at:

- ``contracts/education/_dimensions/districts.odcs.yaml``
- ``contracts/education/_dimensions/schools.odcs.yaml``
- ``contracts/_dimensions/demographics.odcs.yaml``

They are NOT yet read by the REST API (the registry wires them in a later
phase); they exist so FK targets resolve to real machine-readable schemas and
so MCP/LLM consumers can discover the cross-dataset link key and demographics
semantics.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from src.utils.contract_emitter import TYPE_MAP, clean

REPO = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO / "contracts"

# S3 bucket + local root for the gold layer (mirrors the fact emitter's
# servers). Dimension parquets live under these roots.
S3_GOLD_BUCKET = "georgia-data-gold"
LOCAL_GOLD_ROOT = "data/gold"


def _property(
    name: str,
    col_type: str,
    *,
    role: str,
    required: bool,
    description: str,
    pk_position: int | None = None,
    enum: list[str] | None = None,
    examples: list[Any] | None = None,
    extra_custom_props: list[dict] | None = None,
    relationships: list[dict] | None = None,
) -> dict:
    """Build one ODCS property dict for a dimension column.

    Args:
        name: Column name.
        col_type: Source/arrow logical type key for :data:`TYPE_MAP`.
        role: ``key`` (primary-key column) or ``attribute`` (non-key column).
        required: Whether the column is NOT-NULL (``required: true``).
        description: Human-readable column description.
        pk_position: 1-based primary-key position; sets native ``primaryKey`` +
            ``primaryKeyPosition`` when given.
        enum: Allowed string values; promoted to the ODCS ``enum`` field.
        examples: Sample values (emitted as ``examples``).
        extra_custom_props: Additional per-property custom properties (e.g. the
            ``link_key`` descriptor on ``district_census_id``).
        relationships: ODCS property-level ``relationships`` entries (e.g. the
            schools dim's ``district_code`` -> ``districts.district_code`` FK).

    Returns:
        An ODCS property dict.
    """
    logical, physical = TYPE_MAP.get(col_type, ("string", col_type))
    prop: dict = {
        "name": name,
        "logicalType": logical,
        "physicalType": physical,
        "required": required,
        "description": clean(description),
    }
    if examples:
        prop["examples"] = list(examples)
    if enum and logical == "string":
        prop["enum"] = list(enum)
    if relationships:
        prop["relationships"] = list(relationships)

    custom_props: list[dict] = [{"property": "column_role", "value": role}]
    if extra_custom_props:
        custom_props.extend(extra_custom_props)
    prop["customProperties"] = custom_props

    if pk_position is not None:
        prop["primaryKey"] = True
        prop["primaryKeyPosition"] = pk_position
    return prop


def _enum_quality(properties: list[dict]) -> list[dict]:
    """Derive one ``{col}_in_allowed_values`` SQL check per enumerated column."""
    checks: list[dict] = []
    for prop in properties:
        enum = prop.get("enum")
        if not enum:
            continue
        name = prop["name"]
        quoted = ", ".join("'" + str(v).replace("'", "''") + "'" for v in enum)
        checks.append(
            {
                "name": f"{name}_in_allowed_values",
                "description": (f"{name} is one of the {len(enum)} canonical values."),
                "dimension": "conformity",
                "query": (
                    f"SELECT COUNT(*) FROM {{object}} WHERE {name} IS NOT NULL "
                    f"AND {name} NOT IN ({quoted})"
                ),
                "mustBe": 0,
            }
        )
    return checks


def _pk_quality(primary_key: list[str]) -> list[dict]:
    """Derive primary-key integrity checks: non-null per key column + uniqueness.

    Every dimension's headline guarantee is that its primary key uniquely
    identifies a row (composite for schools). These checks make that guarantee
    enforceable by ``datacontract test`` rather than relying on the build script.
    """
    checks: list[dict] = []
    for col in primary_key:
        checks.append(
            {
                "name": f"{col}_not_null",
                "description": f"Primary-key column {col} is never NULL.",
                "dimension": "completeness",
                "query": f"SELECT COUNT(*) FROM {{object}} WHERE {col} IS NULL",
                "mustBe": 0,
            }
        )
    cols = ", ".join(primary_key)
    pk_label = f"({cols})" if len(primary_key) > 1 else cols
    checks.append(
        {
            "name": "primary_key_unique",
            "description": (
                f"The primary key {pk_label} is unique (no duplicate rows)."
            ),
            "dimension": "uniqueness",
            "query": (
                f"SELECT COUNT(*) FROM (SELECT {cols} FROM {{object}} "
                f"GROUP BY {cols} HAVING COUNT(*) > 1)"
            ),
            "mustBe": 0,
        }
    )
    return checks


def _schema_hash(properties: list[dict], primary_key: list[str]) -> str:
    """Deterministic sha256 over the dimension schema shape.

    Canonical structure mirrors the fact emitter's :func:`_schema_hash`: one
    entry per property in declared order =
    ``[name, logicalType, physicalType, required, column_role, sorted(enum or
    [])]``, plus the ordered primary-key list at the end. No timestamps, enums
    sorted, property order is the deterministic authored order.
    """
    canonical: list = []
    for prop in properties:
        role = next(
            (
                cp["value"]
                for cp in prop.get("customProperties", [])
                if cp.get("property") == "column_role"
            ),
            None,
        )
        canonical.append(
            [
                prop["name"],
                prop.get("logicalType"),
                prop.get("physicalType"),
                bool(prop.get("required", False)),
                role,
                sorted(prop.get("enum") or []),
            ]
        )
    canonical.append(primary_key)
    blob = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_dimension_contract(
    *,
    dim_id: str,
    name: str,
    scope: str,
    domain: str,
    physical_basename: str,
    description: dict,
    tags: list[str],
    s3_location: str,
    local_path: str,
    schema_description: str,
    granularity: str,
    properties: list[dict],
    schema_custom_props: list[dict] | None = None,
    extra_quality: list[dict] | None = None,
) -> dict:
    """Build the full ODCS contract document for one dimension table.

    Args:
        dim_id: Contract ``id`` (e.g. ``education._dimensions.districts``).
        name: Contract ``name`` and schema-object name (the dim basename).
        scope: ``domain`` (education-scoped dims) or ``global`` (shared dims).
        domain: ODCS ``domain`` (``education`` or ``shared``).
        physical_basename: The dim parquet basename (``districts`` / ``schools``
            / ``demographics``).
        description: ``{purpose, usage, limitations}`` description block.
        tags: Top-level tags.
        s3_location: S3 glob for the dim parquet.
        local_path: Local path for the dim parquet.
        schema_description: Schema-object description.
        granularity: ``dataGranularityDescription`` sentence.
        properties: Pre-built ODCS property dicts (see :func:`_property`).
        schema_custom_props: Extra schema-object custom properties to append
            after the routing/guard props (e.g. ``link_keys`` / ``semantics``).

    Returns:
        The ODCS contract document as a dict (ready for ``yaml.safe_dump``).
    """
    primary_key = [
        p["name"]
        for p in sorted(
            (p for p in properties if "primaryKeyPosition" in p),
            key=lambda p: p["primaryKeyPosition"],
        )
    ]

    object_quality: list[dict] = [
        {
            "name": "non_empty",
            "description": "The dimension has at least one row.",
            "dimension": "completeness",
            "query": "SELECT COUNT(*) FROM {object}",
            "mustBeGreaterThan": 0,
        }
    ]
    object_quality += _enum_quality(properties)
    # Primary-key integrity (non-null key columns + uniqueness of the PK).
    object_quality += _pk_quality(primary_key)
    # Per-dimension semantic checks (e.g. school_code shape, standard-district
    # Census coverage) authored at the call site.
    object_quality += list(extra_quality or [])
    # ODCS quality.type defaults to `library`; a raw-SQL check MUST declare
    # `type: sql` or `datacontract test` silently skips it. Put `type` first.
    object_quality = [
        ({"type": "sql", **q} if "query" in q and "type" not in q else q)
        for q in object_quality
    ]

    # Schema-object custom properties. THE GUARD + routing inputs: entity_kind /
    # scope / physical_basename. DELIBERATELY no sub_topic / detail_levels /
    # default_detail — their absence keeps the fact-topic loader from ever
    # parsing a dimension contract as a topic.
    object_custom_props: list[dict] = [
        {"property": "entity_kind", "value": "dimension"},
        {"property": "scope", "value": scope},
        {"property": "physical_basename", "value": physical_basename},
    ]
    if schema_custom_props:
        object_custom_props.extend(schema_custom_props)

    return {
        "apiVersion": "v3.1.0",
        "kind": "DataContract",
        "id": dim_id,
        "name": name,
        "version": "1.0.0",
        "status": "active",
        "domain": domain,
        "tenant": "georgia-public-data",
        "description": {
            "purpose": clean(description["purpose"]),
            "usage": clean(description["usage"]),
            "limitations": clean(description["limitations"]),
        },
        "tags": tags,
        "servers": [
            {
                "server": "s3_gold",
                "type": "s3",
                "location": s3_location,
                "format": "parquet",
            },
            {
                "server": "local_gold",
                "type": "local",
                "path": local_path,
                "format": "parquet",
            },
        ],
        "schema": [
            {
                "name": name,
                "logicalType": "object",
                "physicalType": "parquet",
                "physicalName": physical_basename,
                "description": clean(schema_description),
                "dataGranularityDescription": clean(granularity),
                "customProperties": object_custom_props,
                "properties": properties,
                "quality": object_quality,
            }
        ],
        "customProperties": [
            {"property": "schema_hash", "value": _schema_hash(properties, primary_key)},
        ],
    }


def write_dimension_contract(out_path: Path, contract: dict) -> Path:
    """Write a dimension contract to ``out_path`` (creating parent dirs)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as fh:
        yaml.safe_dump(contract, fh, sort_keys=False, width=100, allow_unicode=True)
    return out_path


# --------------------------------------------------------------------------- #
# Per-dimension contract builders. Each reads the live code constants so the
# enum vocabularies never drift from the build scripts / demographics module.
# --------------------------------------------------------------------------- #


def _district_type_enum() -> list[str]:
    """Derive the ``district_type`` enum from the live build_dimensions constants.

    Union of ``{"standard"}`` (the prefix-rule fallback), every
    ``DISTRICT_TYPE_RULES`` value, every ``DISTRICT_TYPE_OVERRIDES`` value, and
    every ``HARDCODED_DISTRICTS`` type. Sorted for determinism.
    """
    from src.etl.education.build_dimensions import (
        DISTRICT_TYPE_OVERRIDES,
        DISTRICT_TYPE_RULES,
        HARDCODED_DISTRICTS,
    )

    types: set[str] = {"standard"}
    types.update(t for _, t in DISTRICT_TYPE_RULES)
    types.update(DISTRICT_TYPE_OVERRIDES.values())
    types.update(t for (_, _, t) in HARDCODED_DISTRICTS.values())
    return sorted(types)


def build_districts_contract() -> dict:
    """Build the education districts dimension contract."""
    district_types = _district_type_enum()
    type_gloss = (
        "Values: standard (Census-matchable school district), state_charter "
        "(state-authorized charter, incl. legacy pre-782 charters), "
        "commission_charter (State Charter Schools Commission-authorized), "
        "state_school (799-prefix Georgia state schools -- Deaf/Blind), "
        "state_agency (state agency reporting education programs under a "
        "district code -- Depts. of Corrections/Juvenile Justice/Human "
        "Resources/Labor; no Census ID), state_special (state-managed "
        "pseudo-district aggregates, e.g. Residential Treatment Center), resa "
        "(Regional Educational Service Agency, 850-888 range; not a "
        "Census-matchable district)."
    )

    properties = [
        _property(
            "district_code",
            "string",
            role="key",
            required=True,
            pk_position=1,
            description=(
                "GOSA district code: 3-digit (zero-padded) for standard "
                "districts, 7-digit for charter districts. A small allowlist of "
                "non-numeric pseudo-district codes (e.g. RTC) is also permitted. "
                "Primary key; natural join key for every education fact table's "
                "district_code FK."
            ),
            examples=["601"],
        ),
        _property(
            "district_name",
            "string",
            role="attribute",
            required=False,
            description="District name in title case (latest name; no history).",
            examples=["Fulton County"],
        ),
        _property(
            "district_census_id",
            "string",
            role="attribute",
            required=False,
            description=(
                "5-digit Census Bureau school-district code (e.g. 00060) for "
                "cross-dataset linking -- the value of the crosswalk's "
                "school_district column. This is a Census SCHOOL-DISTRICT code, "
                "NOT a county FIPS and NOT the 7-digit NCES LEA ID; a school "
                "district does not map 1:1 to a county. To reach county-level "
                "Census data, join through the crosswalk "
                "(school_district -> county FIPS). Charters and state schools "
                "are mapped to their host county's primary Census school "
                "district where known; NULL for RESAs, state agencies, "
                "state-special pseudo-districts, and any charter/state school "
                "without a host-county mapping. Sourced via "
                "src/utils/crosswalks.py."
            ),
            examples=["00060"],
            extra_custom_props=[
                {
                    "property": "link_key",
                    "value": {
                        "target": "census.school_district",
                        "via": "crosswalks.ga_census_crosswalk",
                        "note": (
                            "5-digit Census school-district code (NOT a county "
                            "FIPS). To link to county-level Census data, join "
                            "through the crosswalk school_district -> county "
                            "FIPS (a district is not 1:1 with a county). NULL "
                            "for RESAs, state agencies, state-special "
                            "pseudo-districts, and unmapped charters/state "
                            "schools."
                        ),
                    },
                }
            ],
        ),
        _property(
            "district_type",
            "string",
            role="attribute",
            required=False,
            enum=district_types,
            description=("Classification of the reporting entity. " + type_gloss),
            examples=["standard"],
        ),
    ]

    # Schema-object summary of the cross-dataset link key so MCP consumers find
    # it without scanning per-property customProperties.
    schema_custom_props = [
        {
            "property": "link_keys",
            "value": [
                {
                    "column": "district_census_id",
                    "target": "census.school_district",
                    "via": "crosswalks.ga_census_crosswalk",
                    "note": (
                        "5-digit Census school-district code (NOT a county "
                        "FIPS). To link to county-level Census data, join "
                        "through the crosswalk school_district -> county FIPS "
                        "(a district is not 1:1 with a county). NULL for RESAs, "
                        "state agencies, state-special pseudo-districts, and "
                        "unmapped charters/state schools."
                    ),
                }
            ],
        }
    ]

    # Standard (Census-matchable) districts must always resolve a Census ID.
    # Charters/state schools/RESAs/state agencies legitimately may be NULL.
    extra_quality = [
        {
            "name": "standard_districts_have_census_id",
            "description": (
                "Every standard (Census-matchable) district has a non-null "
                "district_census_id."
            ),
            "dimension": "completeness",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE district_type = 'standard' "
                "AND district_census_id IS NULL"
            ),
            "mustBe": 0,
        }
    ]

    return build_dimension_contract(
        dim_id="education._dimensions.districts",
        name="districts",
        scope="domain",
        domain="education",
        physical_basename="districts",
        description={
            "purpose": (
                "Education districts dimension. One row per GOSA district code "
                "with its latest name, district type, and the 5-digit Census "
                "school-district code used for cross-dataset linking."
            ),
            "usage": (
                "Join from any education fact table's district_code FK on "
                "district_code to attach district_name / district_type, and use "
                "district_census_id to link to Census school-district data "
                "(and, via the crosswalk, to county-level Census datasets -- a "
                "district is not 1:1 with a county)."
            ),
            "limitations": (
                "Latest name only (no slowly-changing history). "
                "district_census_id is the Census school-district code (NOT a "
                "county FIPS); it is NULL for RESAs, state agencies, and "
                "state-special pseudo-districts, and for any charter/state "
                "school lacking a host-county mapping. Charters and state "
                "schools are otherwise mapped to their host county's primary "
                "Census school district."
            ),
        },
        tags=["education", "dimension", "districts"],
        s3_location=(f"s3://{S3_GOLD_BUCKET}/education/_dimensions/districts.parquet"),
        local_path=f"{LOCAL_GOLD_ROOT}/education/_dimensions/districts.parquet",
        schema_description=(
            "Districts dimension table; single (non-partitioned) Parquet file."
        ),
        granularity="One row per district_code.",
        properties=properties,
        schema_custom_props=schema_custom_props,
        extra_quality=extra_quality,
    )


def build_schools_contract() -> dict:
    """Build the education schools dimension contract."""
    properties = [
        _property(
            "district_code",
            "string",
            role="key",
            required=True,
            pk_position=1,
            description=(
                "GOSA district code (zero-padded). Composite primary key part 1 "
                "and FK to the districts dimension."
            ),
            examples=["601"],
            relationships=[{"to": "districts.district_code"}],
        ),
        _property(
            "school_code",
            "string",
            role="key",
            required=True,
            pk_position=2,
            description=(
                "4-digit GOSA school code (zero-padded). Composite primary key "
                "part 2. NOT globally unique on its own."
            ),
            examples=["0103"],
        ),
        _property(
            "school_name",
            "string",
            role="attribute",
            required=False,
            description="School name in title case (latest name; no history).",
            examples=["Centennial High School"],
        ),
    ]

    schema_custom_props = [
        {
            "property": "composite_key_note",
            "value": (
                "school_code is NOT globally unique -- the same 4-digit code "
                "(e.g. 0101) recurs across districts. The primary key is the "
                "(district_code, school_code) pair."
            ),
        }
    ]

    extra_quality = [
        {
            "name": "school_code_is_4_char",
            "description": "school_code is a 4-character zero-padded code.",
            "dimension": "conformity",
            "query": (
                "SELECT COUNT(*) FROM {object} WHERE school_code IS NOT NULL "
                "AND LENGTH(school_code) != 4"
            ),
            "mustBe": 0,
        }
    ]

    return build_dimension_contract(
        dim_id="education._dimensions.schools",
        name="schools",
        scope="domain",
        domain="education",
        physical_basename="schools",
        description={
            "purpose": (
                "Education schools dimension. One row per "
                "(district_code, school_code) pair with the school's latest "
                "name."
            ),
            "usage": (
                "Join from an education fact table on BOTH district_code AND "
                "school_code (the composite key) to attach school_name. Joining "
                "on school_code alone is incorrect -- school codes are not "
                "globally unique."
            ),
            "limitations": (
                "Latest name only (no slowly-changing history). school_code is "
                "not globally unique; always join on the composite key."
            ),
        },
        tags=["education", "dimension", "schools"],
        s3_location=(f"s3://{S3_GOLD_BUCKET}/education/_dimensions/schools.parquet"),
        local_path=f"{LOCAL_GOLD_ROOT}/education/_dimensions/schools.parquet",
        schema_description=(
            "Schools dimension table; single (non-partitioned) Parquet file. "
            "Composite primary key (district_code, school_code)."
        ),
        granularity="One row per (district_code, school_code) pair.",
        properties=properties,
        schema_custom_props=schema_custom_props,
        extra_quality=extra_quality,
    )


def build_demographics_contract() -> dict:
    """Build the global demographics dimension contract."""
    from src.utils.demographics import DEMOGRAPHIC_CATEGORIES

    categories = sorted(set(DEMOGRAPHIC_CATEGORIES.values()))

    properties = [
        _property(
            "demographic",
            "string",
            role="key",
            required=True,
            pk_position=1,
            description=(
                "Canonical demographic code (snake_case). Primary key; natural "
                "join key for every fact table's demographic FK."
            ),
            examples=["black"],
        ),
        _property(
            "demographic_label",
            "string",
            role="attribute",
            required=False,
            description="Human-readable demographic label.",
            examples=["Black"],
        ),
        _property(
            "demographic_category",
            "string",
            role="attribute",
            required=False,
            enum=categories,
            description=(
                "Category the demographic belongs to (e.g. race, gender, "
                "economic, special_population, grade, aggregate)."
            ),
            examples=["race"],
        ),
    ]

    schema_custom_props = [
        {
            "property": "semantics",
            "value": {
                "mutual_exclusivity": (
                    "Within a demographic_category, the demographic values are "
                    "mutually exclusive (a student appears in exactly one per "
                    "category)."
                ),
                "denominator": (
                    "The 'all' demographic is the unfiltered total and the "
                    "denominator for share calculations."
                ),
                "combined_buckets": (
                    "asian_pacific_islander is mutually exclusive with the split "
                    "asian/pacific_islander pair -- a topic publishes one or the "
                    "other."
                ),
                "code_source": (
                    "This dimension is data-driven and carries no enum of "
                    "demographic codes; the canonical code list is the UNION of "
                    "the per-topic fact-table demographic enums, which remain "
                    "the source of truth for validating a fact's demographic "
                    "values."
                ),
            },
        }
    ]

    return build_dimension_contract(
        dim_id="_dimensions.demographics",
        name="demographics",
        scope="global",
        domain="shared",
        physical_basename="demographics",
        description={
            "purpose": (
                "Global demographics dimension shared across all domains. One "
                "row per canonical demographic code with its label and "
                "category."
            ),
            "usage": (
                "Join from any fact table's demographic FK on demographic to "
                "attach demographic_label / demographic_category."
            ),
            "limitations": (
                "Within a category, demographic values are mutually exclusive; "
                "only the 'all' total overlaps the category-specific rows. See "
                "the schema 'semantics' custom property for the full rules."
            ),
        },
        tags=["shared", "dimension", "demographics"],
        s3_location=f"s3://{S3_GOLD_BUCKET}/_dimensions/demographics.parquet",
        local_path=f"{LOCAL_GOLD_ROOT}/_dimensions/demographics.parquet",
        schema_description=(
            "Demographics dimension table; single (non-partitioned) Parquet "
            "file. Shared globally across domains."
        ),
        granularity="One row per demographic code.",
        properties=properties,
        schema_custom_props=schema_custom_props,
    )


def build_counties_contract() -> dict:
    """Build the global counties dimension contract."""
    properties = [
        _property(
            "county_fips",
            "string",
            role="key",
            required=True,
            pk_position=1,
            description=(
                "5-digit county FIPS code (state prefix 13 + 3-digit county). "
                "Primary key; natural join key for every fact table's "
                "county_fips FK."
            ),
            examples=["13121"],
        ),
        _property(
            "county_name",
            "string",
            role="attribute",
            required=True,
            description="County name in title case, without 'County' suffix.",
            examples=["Fulton"],
        ),
    ]

    extra_quality = [
        {
            "name": "county_fips_is_5_digit_ga",
            "description": (
                "county_fips is a 5-digit code with Georgia state prefix 13."
            ),
            "dimension": "conformity",
            "query": (
                "SELECT COUNT(*) FROM {object} "
                "WHERE county_fips IS NOT NULL "
                "AND NOT regexp_matches(county_fips, '^13[0-9]{3}$')"
            ),
            "mustBe": 0,
        },
        {
            "name": "all_159_counties_present",
            "description": "Georgia has exactly 159 counties.",
            "dimension": "completeness",
            "query": "SELECT COUNT(*) FROM {object}",
            "mustBe": 159,
        },
    ]

    return build_dimension_contract(
        dim_id="_dimensions.counties",
        name="counties",
        scope="global",
        domain="shared",
        physical_basename="counties",
        description={
            "purpose": (
                "Global Georgia counties dimension shared across all domains. "
                "One row per county with its 5-digit FIPS code and name."
            ),
            "usage": (
                "Join from any fact table's county_fips FK on county_fips to "
                "attach county_name."
            ),
            "limitations": (
                "Counties only (159 rows); consolidated city-county "
                "governments appear under the county name (e.g. "
                "Athens-Clarke under Clarke). Name-to-FIPS resolution for "
                "source data happens upstream via "
                "src/utils/crosswalks.add_county_fips."
            ),
        },
        tags=["shared", "dimension", "counties", "geography"],
        s3_location=f"s3://{S3_GOLD_BUCKET}/_dimensions/counties.parquet",
        local_path=f"{LOCAL_GOLD_ROOT}/_dimensions/counties.parquet",
        schema_description=(
            "Counties dimension table; single (non-partitioned) Parquet file. "
            "Shared globally across domains."
        ),
        granularity="One row per Georgia county.",
        properties=properties,
        extra_quality=extra_quality,
    )


def districts_contract_path() -> Path:
    """Return the git-tracked path for the districts dimension contract."""
    return CONTRACTS_DIR / "education" / "_dimensions" / "districts.odcs.yaml"


def schools_contract_path() -> Path:
    """Return the git-tracked path for the schools dimension contract."""
    return CONTRACTS_DIR / "education" / "_dimensions" / "schools.odcs.yaml"


def demographics_contract_path() -> Path:
    """Return the git-tracked path for the demographics dimension contract."""
    return CONTRACTS_DIR / "_dimensions" / "demographics.odcs.yaml"


def emit_districts_contract() -> Path:
    """Build + write the districts dimension contract; return its path."""
    return write_dimension_contract(
        districts_contract_path(), build_districts_contract()
    )


def emit_schools_contract() -> Path:
    """Build + write the schools dimension contract; return its path."""
    return write_dimension_contract(schools_contract_path(), build_schools_contract())


def emit_demographics_contract() -> Path:
    """Build + write the demographics dimension contract; return its path."""
    return write_dimension_contract(
        demographics_contract_path(), build_demographics_contract()
    )


def counties_contract_path() -> Path:
    """Return the git-tracked path for the counties dimension contract."""
    return CONTRACTS_DIR / "_dimensions" / "counties.odcs.yaml"


def emit_counties_contract() -> Path:
    """Build + write the counties dimension contract; return its path."""
    return write_dimension_contract(counties_contract_path(), build_counties_contract())
