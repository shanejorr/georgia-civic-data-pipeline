"""Tests for contract_reader — deriving validation config from ODCS contracts.

The reader is the validation-side mirror of contract_emitter: the emitter
projects the transform's in-code declaration into the contract, the reader
derives the entire validation config back out of it. The round-trip test at
the bottom locks the two together.
"""

import polars as pl
import pytest

from src.utils import contract_reader
from src.utils.contract_emitter import build_contract


def _contract(properties: list[dict], custom_props: list[dict] | None = None) -> dict:
    return {
        "schema": [
            {
                "name": "fixture_topic",
                "properties": properties,
                "customProperties": custom_props or [],
            }
        ]
    }


def _prop(
    name: str,
    physical: str,
    role: str | None = None,
    unit: str | None = None,
    pk_position: int | None = None,
) -> dict:
    custom = []
    if role:
        custom.append({"property": "column_role", "value": role})
    if unit:
        custom.append({"property": "unit", "value": unit})
    prop: dict = {
        "name": name,
        "logicalType": "string",
        "physicalType": physical,
        "customProperties": custom,
    }
    if pk_position is not None:
        prop["primaryKey"] = True
        prop["primaryKeyPosition"] = pk_position
    return prop


class TestDeriveTypeSpec:
    def test_maps_all_physical_types(self):
        contract = _contract(
            [
                _prop("a", "int"),
                _prop("b", "bigint"),
                _prop("c", "double"),
                _prop("d", "float"),
                _prop("e", "string"),
                _prop("f", "boolean"),
                _prop("g", "date"),
            ]
        )
        spec = contract_reader.derive_type_spec(contract)
        assert spec == {
            "a": pl.Int32,
            "b": pl.Int64,
            "c": pl.Float64,
            "d": pl.Float32,
            "e": pl.Utf8,
            "f": pl.Boolean,
            "g": pl.Date,
        }

    def test_raises_on_unknown_physical_type(self):
        # The emitter's TYPE_MAP fallback leaks a typo'd transform `type`
        # straight into physicalType — derivation must fail loudly, not
        # silently map to Utf8.
        contract = _contract([_prop("a", "varchar")])
        with pytest.raises(ValueError, match="unknown physicalType"):
            contract_reader.derive_type_spec(contract)

    def test_raises_on_missing_physical_type(self):
        contract = _contract([{"name": "a", "logicalType": "string"}])
        with pytest.raises(ValueError, match="unknown physicalType"):
            contract_reader.derive_type_spec(contract)


class TestDeriveTopicConfig:
    def test_roles_drive_the_lists(self):
        contract = _contract(
            [
                _prop("year", "int", role="year"),
                _prop("district_code", "string", role="fk_district"),
                _prop("test_component", "string", role="categorical"),
                _prop("num_tested", "bigint", role="metric", unit="count"),
                _prop("avg_score", "double", role="metric", unit="score"),
                _prop("graduation_rate", "double", role="metric", unit="proportion"),
                _prop("mobility_rate", "double", role="metric", unit="ratio"),
            ]
        )
        config = contract_reader.derive_topic_config(contract)
        assert config["metric_columns"] == [
            "num_tested",
            "avg_score",
            "graduation_rate",
            "mobility_rate",
        ]
        assert config["categorical_columns"] == ["test_component"]
        # Exempt = metrics whose unit is NOT proportion/ratio (incl. unit-less).
        assert config["exempt_pct_columns"] == ["num_tested", "avg_score"]
        assert config["type_spec"]["year"] == pl.Int32

    def test_unitless_metric_is_exempt(self):
        contract = _contract([_prop("scale_score_std_dev", "double", role="metric")])
        config = contract_reader.derive_topic_config(contract)
        assert config["exempt_pct_columns"] == ["scale_score_std_dev"]


class TestPctClassification:
    def test_splits_bounded_and_ratio(self):
        contract = _contract(
            [
                _prop("graduation_rate", "double", role="metric", unit="proportion"),
                _prop("mobility_rate", "double", role="metric", unit="ratio"),
                _prop("avg_score", "double", role="metric", unit="score"),
            ]
        )
        bounded, ratio = contract_reader.pct_classification(contract)
        assert bounded == ["graduation_rate"]
        assert ratio == ["mobility_rate"]


class TestGrainColumns:
    def test_grain_from_custom_property(self):
        contract = _contract(
            [_prop("year", "int")],
            custom_props=[{"property": "grain", "value": ["year", "district_code"]}],
        )
        assert contract_reader.grain_columns(contract) == ["year", "district_code"]

    def test_grain_falls_back_to_primary_key_position(self):
        contract = _contract(
            [
                _prop("district_code", "string", pk_position=2),
                _prop("year", "int", pk_position=1),
                _prop("num_tested", "bigint"),
            ]
        )
        assert contract_reader.grain_columns(contract) == ["year", "district_code"]


class TestForeignKeysAndQuality:
    def test_reads_fk_descriptors_and_sql_entries(self):
        contract = _contract(
            [_prop("year", "int")],
            custom_props=[
                {
                    "property": "foreign_keys",
                    "value": [
                        {
                            "column": "district_code",
                            "target_object": "districts",
                            "target_columns": ["district_code"],
                            "scope": "domain",
                        }
                    ],
                }
            ],
        )
        contract["schema"][0]["quality"] = [
            {"type": "sql", "name": "q1", "query": "SELECT 1", "mustBe": 1},
            {"type": "library", "name": "not_sql"},
            {"type": "sql", "name": "no_query"},
        ]
        fks = contract_reader.foreign_keys(contract)
        assert fks[0]["target_object"] == "districts"
        entries = contract_reader.quality_sql_entries(contract)
        assert [e["name"] for e in entries] == ["q1"]


class TestEmitterReaderRoundTrip:
    def test_round_trip_against_build_contract(self):
        """Lock the reader to the emitter: a contract built by build_contract
        derives back to the expected validation config."""
        contract = build_contract(
            "education",
            "gosa",
            "fixture_topic",
            description="Fixture.",
            title="Fixture Topic",
            summary="Fixture topic for the round-trip test.",
            columns=[
                {"name": "year", "type": "int32", "nullable": False},
                {"name": "district_code", "type": "string"},
                {"name": "school_code", "type": "string"},
                {"name": "test_component", "type": "string", "validValues": ["a"]},
                {
                    "name": "num_tested",
                    "type": "int64",
                    "unit": "count",
                    "metric_component": "denominator",
                },
                {
                    "name": "avg_score",
                    "type": "float64",
                    "unit": "score",
                    "value_min": 1,
                    "value_max": 36,
                    "key_metric": True,
                },
                {"name": "graduation_rate", "type": "float64", "unit": "proportion"},
            ],
            source="GOSA",
            source_url=None,
            update_frequency="annual",
            year_range=(2020, 2024),
            detail_levels=["schools", "districts", "states"],
        )
        config = contract_reader.derive_topic_config(contract)
        assert config["type_spec"] == {
            "year": pl.Int32,
            "district_code": pl.Utf8,
            "school_code": pl.Utf8,
            "test_component": pl.Utf8,
            "num_tested": pl.Int64,
            "avg_score": pl.Float64,
            "graduation_rate": pl.Float64,
        }
        assert config["metric_columns"] == [
            "num_tested",
            "avg_score",
            "graduation_rate",
        ]
        assert config["categorical_columns"] == ["test_component"]
        assert config["exempt_pct_columns"] == ["num_tested", "avg_score"]

        bounded, ratio = contract_reader.pct_classification(contract)
        assert bounded == ["graduation_rate"]
        assert ratio == []

        # Grain: year + FKs + categoricals, in declared order.
        assert contract_reader.grain_columns(contract) == [
            "year",
            "district_code",
            "school_code",
            "test_component",
        ]

        # FK descriptors present for the three FK columns; schools composite.
        fks = {fk["column"]: fk for fk in contract_reader.foreign_keys(contract)}
        assert fks["school_code"]["target_columns"] == [
            "district_code",
            "school_code",
        ]

        # Derived quality SQL exists and is readable back.
        names = {e["name"] for e in contract_reader.quality_sql_entries(contract)}
        assert "non_empty" in names
        assert "avg_score_within_range" in names
        assert "graduation_rate_within_unit_interval" in names
