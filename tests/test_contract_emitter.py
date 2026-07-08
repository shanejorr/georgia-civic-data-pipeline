"""Tests for src/utils/contract_emitter.py — the fact-contract emitter.

These call ``build_contract`` / ``build_properties`` directly with synthetic
column dicts (no real transforms are run). They cover the Phase-1 enrichments:
``unit`` (replacing ``pct_scale``) + derived range checks, grain / logical
primary key, accurate limitations + usage, null semantics, self-describing
layout, deterministic ``schema_hash``, auto-derived example queries, and the
``foreign_keys`` custom property (with the composite school join).
"""

from pathlib import Path

import pytest
import yaml

from src.utils.contract_emitter import (
    build_contract,
    build_properties,
    derive_label,
)
from src.utils.validators import ValidationRunner

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _col(name, type_="float64", **extra):
    """Build a synthetic column declaration dict (transform shape).

    ``type_`` is the polars/arrow logical type key the emitter's TYPE_MAP keys
    on (e.g. ``float64`` -> number, ``int64`` -> integer, ``string``).
    """
    col = {"name": name, "type": type_}
    col.update(extra)
    return col


def _schema_cp(contract: dict) -> dict:
    """Return the schema-object customProperties as a {property: value} dict."""
    cps = contract["schema"][0].get("customProperties") or []
    return {cp["property"]: cp["value"] for cp in cps}


def _top_cp(contract: dict) -> dict:
    """Return the top-level customProperties as a {property: value} dict."""
    return {cp["property"]: cp["value"] for cp in contract["customProperties"]}


def _prop_cp(prop: dict) -> dict:
    """Return a property's customProperties as a {property: value} dict."""
    return {cp["property"]: cp["value"] for cp in (prop.get("customProperties") or [])}


def _build(columns, **kwargs):
    """Build a contract with sensible defaults for the synthetic columns.

    To satisfy the emitter's exactly-one-key_metric requirement without every
    test declaring it, flag the first metric (``unit``-bearing) column as the
    key metric when none is flagged. Tests that exercise key_metric behaviour
    pass their own flag (or none, for the metric-less degenerate case).
    """
    columns = [dict(c) for c in columns]
    if not any(c.get("key_metric") for c in columns):
        for c in columns:
            if c.get("unit") is not None:
                c["key_metric"] = True
                break
    params = {
        "description": "Synthetic topic for tests.",
        "title": "Synthetic Topic",
        "summary": "A synthetic topic used by the emitter unit tests.",
        "columns": columns,
        "source": "Test Source (TS)",
        "source_url": "https://example.org/",
        "update_frequency": "annual",
        "year_range": (2020, 2024),
        "detail_levels": ["schools", "districts", "states"],
    }
    params.update(kwargs)
    return build_contract("education", "gosa", "synthetic_topic", **params)


# ---------------------------------------------------------------------------
# #3 — unit + derived range checks
# ---------------------------------------------------------------------------


def test_unit_proportion_emits_bounded_check_and_property():
    props, quality = build_properties([_col("rate", unit="proportion")])
    assert _prop_cp(props[0])["unit"] == "proportion"
    q = {c["name"]: c for c in quality}
    assert "rate_within_unit_interval" in q
    assert q["rate_within_unit_interval"]["query"].endswith(
        "WHERE rate IS NOT NULL AND (rate < 0 OR rate > 1)"
    )
    assert q["rate_within_unit_interval"]["mustBe"] == 0
    assert q["rate_within_unit_interval"]["dimension"] == "accuracy"


def test_unit_ratio_emits_non_negative_check():
    props, quality = build_properties([_col("mobility", unit="ratio")])
    assert _prop_cp(props[0])["unit"] == "ratio"
    q = {c["name"]: c for c in quality}
    assert "mobility_non_negative" in q
    assert q["mobility_non_negative"]["query"].endswith(
        "WHERE mobility IS NOT NULL AND mobility < 0"
    )


def test_unit_count_emits_non_negative_check():
    props, quality = build_properties([_col("student_count", "int64", unit="count")])
    assert _prop_cp(props[0])["unit"] == "count"
    q = {c["name"]: c for c in quality}
    assert "student_count_non_negative" in q
    assert q["student_count_non_negative"]["query"].endswith(
        "WHERE student_count IS NOT NULL AND student_count < 0"
    )


def test_unit_score_with_bounds_emits_range_check():
    props, quality = build_properties(
        [_col("act_score", unit="score", value_min=1, value_max=36)]
    )
    cp = _prop_cp(props[0])
    assert cp["unit"] == "score"
    assert cp["value_min"] == 1
    assert cp["value_max"] == 36
    q = {c["name"]: c for c in quality}
    assert "act_score_within_range" in q
    assert q["act_score_within_range"]["query"].endswith(
        "WHERE act_score IS NOT NULL AND (act_score < 1 OR act_score > 36)"
    )


def test_unit_score_without_bounds_emits_no_range_check():
    props, quality = build_properties([_col("rating", unit="score")])
    assert _prop_cp(props[0])["unit"] == "score"
    assert quality == []


def test_unit_percentile_defaults_to_0_100():
    props, quality = build_properties([_col("pctile", unit="percentile")])
    q = {c["name"]: c for c in quality}
    assert "pctile_within_range" in q
    assert q["pctile_within_range"]["query"].endswith(
        "WHERE pctile IS NOT NULL AND (pctile < 0 OR pctile > 100)"
    )


def test_unit_currency_emits_no_range_check():
    props, quality = build_properties([_col("salary", "int64", unit="currency")])
    assert _prop_cp(props[0])["unit"] == "currency"
    assert quality == []


def test_exempt_column_has_no_unit_property():
    props, quality = build_properties([_col("plain_metric")])
    assert "unit" not in _prop_cp(props[0])
    assert quality == []


# ---------------------------------------------------------------------------
# #3 — _validate_unit error paths (via build_properties)
# ---------------------------------------------------------------------------


def test_unknown_unit_raises():
    with pytest.raises(ValueError, match="invalid unit"):
        build_properties([_col("x", unit="bogus")])


def test_value_min_greater_than_max_raises():
    with pytest.raises(ValueError, match="value_min"):
        build_properties([_col("x", unit="score", value_min=10, value_max=1)])


def test_leftover_pct_scale_key_raises():
    with pytest.raises(ValueError, match="'pct_scale' was renamed to 'unit'"):
        build_properties([{"name": "x", "type": "number", "pct_scale": "bounded"}])


# ---------------------------------------------------------------------------
# #4 — grain / primary key
# ---------------------------------------------------------------------------


def test_grain_order_year_fks_categoricals():
    columns = [
        _col("year", "int32"),
        _col("district_code", "string"),
        _col("school_code", "string"),
        _col("demographic", "string"),
        _col("subject", "string"),
        _col("score", "float64", unit="proportion"),
    ]
    contract = _build(columns)
    assert _schema_cp(contract)["grain"] == [
        "year",
        "district_code",
        "school_code",
        "demographic",
        "subject",
    ]
    by_name = {p["name"]: p for p in contract["schema"][0]["properties"]}
    # primaryKey + 1-based position on each grain property, in grain order.
    assert by_name["year"]["primaryKey"] is True
    assert by_name["year"]["primaryKeyPosition"] == 1
    assert by_name["district_code"]["primaryKeyPosition"] == 2
    assert by_name["school_code"]["primaryKeyPosition"] == 3
    assert by_name["demographic"]["primaryKeyPosition"] == 4
    assert by_name["subject"]["primaryKeyPosition"] == 5
    # The metric is NOT part of the grain.
    assert "primaryKey" not in by_name["score"]
    # FK columns stay nullable despite being part of the logical PK.
    assert by_name["district_code"]["required"] is False


def test_data_granularity_description_text():
    columns = [_col("year", "int32"), _col("district_code", "string")]
    contract = _build(columns, detail_levels=["districts", "states"])
    grain_desc = contract["schema"][0]["dataGranularityDescription"]
    assert grain_desc == (
        "One row per year, district_code "
        "(geography columns are NULL at higher aggregation levels)."
    )


def test_grain_with_no_categoricals():
    columns = [
        _col("year", "int32"),
        _col("district_code", "string"),
        _col("metric", "float64", unit="count"),
    ]
    contract = _build(columns)
    assert _schema_cp(contract)["grain"] == ["year", "district_code"]


def test_grain_with_two_categoricals():
    columns = [
        _col("year", "int32"),
        _col("race", "string"),
        _col("gender", "string"),
        _col("metric", "float64", unit="count"),
    ]
    contract = _build(columns)
    # race + gender are categorical, both in the grain (after year).
    assert _schema_cp(contract)["grain"] == ["year", "race", "gender"]
    by_name = {p["name"]: p for p in contract["schema"][0]["properties"]}
    assert by_name["race"]["primaryKeyPosition"] == 2
    assert by_name["gender"]["primaryKeyPosition"] == 3


# ---------------------------------------------------------------------------
# #6 — limitations + usage + null semantics
# ---------------------------------------------------------------------------


def test_limitations_schools_districts_states():
    contract = _build(
        [_col("year", "int32")], detail_levels=["schools", "districts", "states"]
    )
    lim = contract["description"]["limitations"]
    assert "Suppressed cells are NULL (not zero)." in lim
    assert "State rows have NULL district_code and school_code." in lim
    assert "District rows have NULL school_code." in lim


def test_limitations_districts_only():
    contract = _build([_col("year", "int32")], detail_levels=["districts"])
    lim = contract["description"]["limitations"]
    assert "District rows have NULL school_code." in lim
    assert "State rows" not in lim


def test_limitations_schools_only():
    contract = _build([_col("year", "int32")], detail_levels=["schools"])
    lim = contract["description"]["limitations"]
    assert lim == "Suppressed cells are NULL (not zero)."


def test_limitations_no_detail():
    contract = _build([_col("year", "int32")], detail_levels=[])
    lim = contract["description"]["limitations"]
    assert "This table is not geography-partitioned." in lim


def test_limitations_override_wins():
    contract = _build([_col("year", "int32")], limitations="Custom limitation text.")
    assert contract["description"]["limitations"] == "Custom limitation text."


def test_usage_conditional_on_fk_presence():
    # schools + districts + demographic present.
    full = _build(
        [
            _col("year", "int32"),
            _col("district_code", "string"),
            _col("school_code", "string"),
            _col("demographic", "string"),
        ]
    )
    usage = full["description"]["usage"]
    assert "districts dimension on district_code" in usage
    assert "schools dimension on district_code + school_code" in usage
    assert "demographics dimension on demographic" in usage
    assert "Read directly with DuckDB over Parquet." in usage

    # No FK columns -> no join sentence, still mentions DuckDB.
    bare = _build([_col("year", "int32"), _col("metric", "float64", unit="count")])
    bare_usage = bare["description"]["usage"]
    assert "dimension" not in bare_usage
    assert "Read directly with DuckDB over Parquet." in bare_usage


def test_usage_override_wins():
    contract = _build([_col("year", "int32")], usage="Custom usage text.")
    assert contract["description"]["usage"] == "Custom usage text."


def test_null_semantics_present():
    contract = _build([_col("year", "int32")])
    assert _schema_cp(contract)["null_semantics"] == {
        "suppressed_to_null": True,
        "zero_is_real": True,
    }


def test_per_column_null_meaning_emitted():
    props, _ = build_properties(
        [_col("metric", "float64", unit="count", null_meaning="suppressed (n<10)")]
    )
    assert _prop_cp(props[0])["null_meaning"] == "suppressed (n<10)"


# ---------------------------------------------------------------------------
# #7 — self-describing layout
# ---------------------------------------------------------------------------


def test_layout_custom_properties():
    contract = _build([_col("year", "int32")])
    scp = _schema_cp(contract)
    assert scp["partition_columns"] == ["year"]
    assert (
        scp["path_template"] == "education/synthetic_topic/year={year}/{detail}.parquet"
    )


def test_local_gold_server_present():
    contract = _build([_col("year", "int32")])
    servers = {s["server"]: s for s in contract["servers"]}
    assert "s3_gold" in servers
    assert "local_gold" in servers
    assert servers["local_gold"]["type"] == "local"
    # ODCS `local`-type servers use `path` (not `location`, which is `s3`-only).
    assert (
        servers["local_gold"]["path"]
        == "data/gold/education/synthetic_topic/**/*.parquet"
    )


# ---------------------------------------------------------------------------
# #8 — deterministic schema_hash
# ---------------------------------------------------------------------------


def _hash(contract: dict) -> str:
    return _top_cp(contract)["schema_hash"]


def test_schema_hash_deterministic():
    columns = [
        _col("year", "int32"),
        _col("district_code", "string"),
        _col("rate", "float64", unit="proportion"),
    ]
    h1 = _hash(_build([dict(c) for c in columns]))
    h2 = _hash(_build([dict(c) for c in columns]))
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex


def test_schema_hash_changes_on_rename():
    base = [_col("year", "int32"), _col("rate", "float64", unit="proportion")]
    renamed = [_col("year", "int32"), _col("ratio_val", "float64", unit="proportion")]
    assert _hash(_build(base)) != _hash(_build(renamed))


def test_schema_hash_changes_on_type_change():
    base = [_col("metric", "int64", unit="count")]
    changed = [_col("metric", "float64", unit="ratio")]
    assert _hash(_build(base)) != _hash(_build(changed))


def test_schema_hash_unchanged_on_description_only_change():
    base = [_col("rate", "float64", unit="proportion", description="Original.")]
    described = [
        _col(
            "rate", "float64", unit="proportion", description="Totally different prose."
        )
    ]
    assert _hash(_build(base)) == _hash(_build(described))


# ---------------------------------------------------------------------------
# #9 — example_queries
# ---------------------------------------------------------------------------


def test_example_queries_structure_and_determinism():
    columns = [
        _col("year", "int32"),
        _col("district_code", "string", example="601"),
        _col("subject", "string", example="mathematics"),
        _col("rate", "float64", unit="proportion"),
    ]
    contract = _build([dict(c) for c in columns])
    queries = _schema_cp(contract)["example_queries"]
    assert isinstance(queries, list)
    assert 2 <= len(queries) <= 3
    # First query is latest year + default detail.
    assert (
        queries[0]["query"]
        == "SELECT * FROM synthetic_topic WHERE year = 2024 LIMIT 100"
    )
    assert "2024" in queries[0]["description"]
    assert "schools detail" in queries[0]["description"]
    # FK sample query references the district example.
    assert any("district_code = '601'" in q["query"] for q in queries)
    # Categorical sample query references the subject example.
    assert any("subject = 'mathematics'" in q["query"] for q in queries)
    # Determinism: same inputs -> identical queries.
    again = _build([dict(c) for c in columns])
    assert _schema_cp(again)["example_queries"] == queries


def test_example_queries_skips_absent_inputs():
    # No FK example, categorical without example but with enum.
    columns = [
        _col("year", "int32"),
        _col("flag", "string", validValues=["green", "red"]),
        _col("metric", "float64", unit="count"),
    ]
    contract = _build(columns)
    queries = _schema_cp(contract)["example_queries"]
    # latest-year query + categorical-via-first-sorted-enum query.
    assert queries[0]["query"].startswith(
        "SELECT * FROM synthetic_topic WHERE year = 2024"
    )
    assert any("flag = 'green'" in q["query"] for q in queries)


def test_example_queries_override_wins():
    custom = [{"description": "custom", "query": "SELECT 1"}]
    contract = _build([_col("year", "int32")], example_queries=custom)
    assert _schema_cp(contract)["example_queries"] == custom


# ---------------------------------------------------------------------------
# #1-emit — foreign_keys (composite school key)
# ---------------------------------------------------------------------------


def test_foreign_keys_composite_school_key():
    columns = [
        _col("year", "int32"),
        _col("district_code", "string"),
        _col("school_code", "string"),
        _col("demographic", "string"),
    ]
    contract = _build(columns)
    fks = {fk["column"]: fk for fk in _schema_cp(contract)["foreign_keys"]}
    assert set(fks) == {"district_code", "school_code", "demographic"}
    # The accuracy fix: schools join is COMPOSITE.
    assert fks["school_code"]["target_columns"] == ["district_code", "school_code"]
    assert fks["school_code"]["target_object"] == "schools"
    assert fks["school_code"]["scope"] == "domain"
    assert fks["district_code"]["target_columns"] == ["district_code"]
    assert fks["demographic"]["scope"] == "global"


def test_foreign_keys_only_present_columns():
    # districts-only topic: no school_code, no demographic.
    columns = [_col("year", "int32"), _col("district_code", "string")]
    contract = _build(columns, detail_levels=["districts"])
    cols = [fk["column"] for fk in _schema_cp(contract)["foreign_keys"]]
    assert cols == ["district_code"]


# ---------------------------------------------------------------------------
# Validator integration — unit -> bounded/ratio split
# ---------------------------------------------------------------------------


def _write_contract_with_units(
    contract_path: Path, unit_by_col: dict[str, str]
) -> None:
    """Write a minimal ODCS contract with per-column `unit` custom properties."""
    properties = []
    for name, unit in unit_by_col.items():
        properties.append(
            {
                "name": name,
                "logicalType": "number",
                "customProperties": [
                    {"property": "column_role", "value": "metric"},
                    {"property": "unit", "value": unit},
                ],
            }
        )
    contract = {
        "apiVersion": "v3.1.0",
        "kind": "DataContract",
        "id": "education.unit_topic",
        "name": "unit_topic",
        "schema": [{"name": "unit_topic", "properties": properties}],
    }
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False))


def test_validator_reads_unit_split(tmp_path):
    """`_pct_classification_from_contract` maps proportion->bounded, ratio->ratio."""
    gold_dir = tmp_path / "education" / "unit_topic"
    gold_dir.mkdir(parents=True)
    contract_path = tmp_path / "contracts" / "education" / "unit_topic.odcs.yaml"
    _write_contract_with_units(
        contract_path,
        {
            "bounded_rate": "proportion",
            "ratio_rate": "ratio",
            "raw_count": "count",  # ignored (not a pct bucket)
        },
    )

    runner = ValidationRunner(gold_dir=gold_dir, domain_config={}, topic_config={})

    # Point the classification reader at our fixture contract.
    import src.utils.validators as validators_mod

    original = validators_mod.contract_path_for_gold_dir
    validators_mod.contract_path_for_gold_dir = lambda _gd: contract_path
    try:
        bounded, ratio = runner._pct_classification_from_contract()
    finally:
        validators_mod.contract_path_for_gold_dir = original

    assert bounded == ["bounded_rate"]
    assert ratio == ["ratio_rate"]


# ---------------------------------------------------------------------------
# key_metric / key_metric_grain_contributor / metric_component
# ---------------------------------------------------------------------------


def test_key_metric_property_and_object_pointer():
    # Mirrors the act_scores example: avg_score is the key metric, num_tested its
    # denominator, test_component a grain contributor.
    columns = [
        _col("year", "int32"),
        _col("test_component", "string"),
        _col("num_tested", "int64", unit="count", metric_component="denominator"),
        _col(
            "avg_score",
            "float64",
            unit="score",
            value_min=1,
            value_max=36,
            key_metric=True,
        ),
    ]
    contract = _build(columns)
    by_name = {p["name"]: p for p in contract["schema"][0]["properties"]}
    # Per-property marker on exactly the flagged column.
    assert _prop_cp(by_name["avg_score"])["key_metric"] is True
    assert "key_metric" not in _prop_cp(by_name["num_tested"])
    # Schema-object pointer resolves the headline metric in one lookup.
    assert _schema_cp(contract)["key_metric"] == "avg_score"
    # The denominator marker rides on the count column.
    assert _prop_cp(by_name["num_tested"])["metric_component"] == "denominator"


def test_exactly_one_key_metric_required_when_metrics_present():
    # build_contract directly (bypassing _build's auto-flag) with metrics but no
    # key_metric -> raises.
    with pytest.raises(ValueError, match="must declare exactly one key_metric"):
        build_contract(
            "education",
            "gosa",
            "synthetic_topic",
            description="d",
            title="Synthetic Topic",
            summary="Synthetic topic for tests.",
            columns=[_col("year", "int32"), _col("rate", "float64", unit="proportion")],
            source="TS",
            source_url=None,
            update_frequency="annual",
            year_range=(2020, 2024),
            detail_levels=["schools"],
        )


def test_metricless_table_needs_no_key_metric():
    # A degenerate table with no metric columns is allowed without a key_metric.
    contract = _build([_col("year", "int32"), _col("district_code", "string")])
    assert "key_metric" not in _schema_cp(contract)


def test_two_key_metrics_raises():
    with pytest.raises(ValueError, match="multiple key_metric"):
        build_properties(
            [
                _col("a", "float64", unit="score", key_metric=True),
                _col("b", "float64", unit="proportion", key_metric=True),
            ]
        )


def test_metric_component_numerator_and_denominator():
    props, _ = build_properties(
        [
            _col("graduate_count", "int64", unit="count", metric_component="numerator"),
            _col("cohort_size", "int64", unit="count", metric_component="denominator"),
        ]
    )
    cps = {p["name"]: _prop_cp(p) for p in props}
    assert cps["graduate_count"]["metric_component"] == "numerator"
    assert cps["cohort_size"]["metric_component"] == "denominator"


def test_metric_component_rejects_non_count():
    with pytest.raises(ValueError, match="only valid on a count column"):
        build_properties(
            [_col("rate", "float64", unit="proportion", metric_component="numerator")]
        )


def test_metric_component_invalid_value_raises():
    with pytest.raises(ValueError, match="invalid metric_component"):
        build_properties([_col("n", "int64", unit="count", metric_component="ratio")])


def test_grain_contributor_flags_demographic_and_categoricals_not_geo():
    # The load-bearing test: #2 == demographic + categoricals, NOT year/geography.
    columns = [
        _col("year", "int32"),
        _col("district_code", "string"),
        _col("school_code", "string"),
        _col("demographic", "string"),
        _col("subject", "string"),
        _col("score", "float64", unit="proportion", key_metric=True),
    ]
    contract = _build(columns)
    by_name = {p["name"]: p for p in contract["schema"][0]["properties"]}

    def is_contrib(name):
        return _prop_cp(by_name[name]).get("key_metric_grain_contributor") is True

    assert is_contrib("demographic")
    assert is_contrib("subject")
    assert not is_contrib("year")
    assert not is_contrib("district_code")
    assert not is_contrib("school_code")
    assert not is_contrib("score")  # the metric itself is never a contributor


def test_grain_contributor_excludes_exclude_from_grain():
    columns = [
        _col("year", "int32"),
        _col("ccrpi_flag", "string", exclude_from_grain=True),
        _col(
            "score",
            "float64",
            unit="score",
            value_min=0,
            value_max=100,
            key_metric=True,
        ),
    ]
    contract = _build(columns)
    by_name = {p["name"]: p for p in contract["schema"][0]["properties"]}
    # Not flagged, and not in the grain.
    assert _prop_cp(by_name["ccrpi_flag"]).get("key_metric_grain_contributor") is None
    assert "ccrpi_flag" not in _schema_cp(contract)["grain"]


def test_categorical_key_metric_requires_opt_in():
    # A string (categorical) key metric without the opt-in raises.
    with pytest.raises(ValueError, match="key_metric_categorical"):
        build_properties([_col("proficiency_level", "string", key_metric=True)])
    # With the opt-in it emits the marker.
    props, _ = build_properties(
        [
            _col(
                "proficiency_level",
                "string",
                key_metric=True,
                key_metric_categorical=True,
            )
        ]
    )
    assert _prop_cp(props[0])["key_metric"] is True


def test_schema_hash_unchanged_by_new_props():
    # key_metric / metric_component are NOT part of the schema hash, so enriching
    # a contract with them does not churn the hash (rollout-safety guarantee).
    base = [
        _col("year", "int32"),
        _col("graduate_count", "int64", unit="count"),
        _col("rate", "float64", unit="proportion", key_metric=True),
    ]
    enriched = [
        _col("year", "int32"),
        _col("graduate_count", "int64", unit="count", metric_component="numerator"),
        _col("rate", "float64", unit="proportion", key_metric=True),
    ]
    assert _hash(_build([dict(c) for c in base])) == _hash(
        _build([dict(c) for c in enriched])
    )


# ---------------------------------------------------------------------------
# Human-facing fields — title / summary / label / short_description
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,expected",
    [
        ("graduation_rate", "Graduation Rate"),
        ("cohort_size", "Cohort Size"),
        ("el_exit_rate", "EL Exit Rate"),
        ("revenues_and_expenditures", "Revenues and Expenditures"),
        ("dollars_per_fte", "Dollars per FTE"),
        ("ccrpi_flag", "CCRPI Flag"),
        ("out_of_field_teachers", "Out of Field Teachers"),
        ("pct_of_enrollment", "Percent of Enrollment"),
        ("num_tested", "Number Tested"),
        ("district_census_id", "District Census ID"),
        ("dropout_rate_9_12", "Dropout Rate 9 12"),
        ("sat_scores_recent", "SAT Scores Recent"),
    ],
)
def test_derive_label(name, expected):
    assert derive_label(name) == expected


def test_label_auto_derived_and_overridable():
    props, _ = build_properties(
        [
            _col("graduation_rate", "float64", unit="proportion"),
            _col("rev_exp_type", "string", label="Revenue / expenditure type"),
        ]
    )
    cps = {p["name"]: _prop_cp(p) for p in props}
    # Auto-derived Title Case label on every column.
    assert cps["graduation_rate"]["label"] == "Graduation Rate"
    # Explicit override wins over the derived form.
    assert cps["rev_exp_type"]["label"] == "Revenue / expenditure type"


def test_short_description_emitted_when_authored_and_omitted_otherwise():
    props, _ = build_properties(
        [
            _col(
                "rate",
                "float64",
                unit="proportion",
                short_description="Share of the cohort that graduated.",
            ),
            _col("cohort_size", "int64", unit="count"),
        ]
    )
    cps = {p["name"]: _prop_cp(p) for p in props}
    assert cps["rate"]["short_description"] == "Share of the cohort that graduated."
    # A column with no authored short_description carries none.
    assert "short_description" not in cps["cohort_size"]


def test_title_and_summary_emitted_as_top_custom_properties():
    contract = _build(
        [_col("year", "int32"), _col("rate", "float64", unit="proportion")],
        title="High School Graduation Rates",
        summary="Graduation rates by school, district, and subgroup, 2012-2025.",
    )
    top = _top_cp(contract)
    assert top["title"] == "High School Graduation Rates"
    assert top["summary"] == (
        "Graduation rates by school, district, and subgroup, 2012-2025."
    )


def test_missing_title_raises():
    with pytest.raises(ValueError, match="'title' is required"):
        _build([_col("year", "int32")], title="")


def test_missing_summary_raises():
    with pytest.raises(ValueError, match="'summary' is required"):
        _build([_col("year", "int32")], summary="   ")


def test_human_fields_not_in_schema_hash():
    # label / short_description / title / summary must not churn the schema hash
    # (rollout-safety: enriching a contract with human fields needs no version
    # bump and triggers no gold re-approval).
    base = [_col("year", "int32"), _col("rate", "float64", unit="proportion")]
    enriched = [
        _col("year", "int32"),
        _col(
            "rate",
            "float64",
            unit="proportion",
            label="The Rate",
            short_description="A one-liner.",
        ),
    ]
    h_base = _top_cp(_build([dict(c) for c in base]))["schema_hash"]
    h_enriched = _top_cp(
        _build([dict(c) for c in enriched], title="Other", summary="Other summary.")
    )["schema_hash"]
    assert h_base == h_enriched


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
