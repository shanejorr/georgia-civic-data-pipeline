"""Tests for shared validator schema checks.

Covers the checks that guard against transform-vs-API schema drift
(`check_data_types`, `check_contract_parquet_schema`) and the contract-driven
suite added for the clean-start pipeline: grain uniqueness, the contract's own
quality SQL, FK integrity against dimensions, canonical vocabulary, and the
`run_topic_validation` entry point that replaces per-topic validate.py files.
"""

from pathlib import Path

import polars as pl
import pytest
import yaml

from src.utils.validators import (
    GoldValidationError,
    ValidationRunner,
    check_canonical_vocabulary,
    check_contract_parquet_schema,
    check_contract_quality_sql,
    check_data_types,
    check_foreign_keys,
    check_grain_uniqueness,
    run_topic_validation,
)


def _write_contract(contract_path: Path, column_names: list[str]) -> Path:
    """Write a minimal ODCS contract declaring the given columns, in order."""
    contract = {
        "apiVersion": "v3.1.0",
        "kind": "DataContract",
        "id": "education.fixture_topic",
        "name": "fixture_topic",
        "schema": [
            {
                "name": "fixture_topic",
                "properties": [
                    {"name": c, "logicalType": "string"} for c in column_names
                ],
            }
        ],
    }
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False))
    return contract_path


def _write_parquet(gold_dir: Path, year: int, columns: list[str]) -> Path:
    year_dir = gold_dir / f"year={year}"
    year_dir.mkdir(parents=True, exist_ok=True)
    df = pl.DataFrame({c: ["x"] for c in columns})
    path = year_dir / "schools.parquet"
    df.write_parquet(path)
    return path


# =============================================================================
# check_data_types
# =============================================================================


class TestCheckDataTypes:
    def test_passes_when_all_columns_match(self):
        df = pl.DataFrame({"year": [2024], "name": ["a"]}).with_columns(
            pl.col("year").cast(pl.Int32)
        )
        result = check_data_types(df, {"year": pl.Int32, "name": pl.Utf8})
        assert result.status == "pass"

    def test_fails_on_missing_expected_column(self):
        # type_spec declares `score` but DataFrame doesn't ship it. Previously
        # this case slipped past validation; the regenerated check must flag it.
        df = pl.DataFrame({"year": [2024]}).with_columns(pl.col("year").cast(pl.Int32))
        result = check_data_types(df, {"year": pl.Int32, "score": pl.Float64})
        assert result.status == "fail"
        assert any("missing: score" in d for d in (result.details or []))

    def test_fails_on_dtype_mismatch(self):
        df = pl.DataFrame({"year": ["2024"]})  # Utf8, not Int32
        result = check_data_types(df, {"year": pl.Int32})
        assert result.status == "fail"
        assert any("year:" in d and "expected" in d for d in (result.details or []))

    def test_reports_both_missing_and_dtype_mismatch(self):
        df = pl.DataFrame({"year": ["2024"]})
        result = check_data_types(df, {"year": pl.Int32, "score": pl.Float64})
        assert result.status == "fail"
        details = result.details or []
        assert any("missing: score" in d for d in details)
        assert any("year:" in d for d in details)


# =============================================================================
# check_contract_parquet_schema
# =============================================================================


class TestCheckContractParquetSchema:
    def test_passes_on_matching_schema(self, tmp_path: Path):
        gold_dir = tmp_path / "topic"
        gold_dir.mkdir()
        cols = ["year", "district_code", "school_code", "score"]
        contract = _write_contract(tmp_path / "fixture_topic.odcs.yaml", cols)
        _write_parquet(gold_dir, 2024, cols)
        result = check_contract_parquet_schema(gold_dir, contract_path=contract)
        assert result.status == "pass"

    def test_fails_on_column_name_mismatch(self, tmp_path: Path):
        # Parquet column was renamed without updating the contract (this is
        # exactly the ccrpi_progress regression: parquet shipped *_pct, the
        # schema declared pct_*).
        gold_dir = tmp_path / "topic"
        gold_dir.mkdir()
        contract = _write_contract(
            tmp_path / "fixture_topic.odcs.yaml", ["year", "pct_no_positive_movement"]
        )
        _write_parquet(gold_dir, 2024, ["year", "no_positive_movement_pct"])
        result = check_contract_parquet_schema(gold_dir, contract_path=contract)
        assert result.status == "fail"
        details = " ".join(result.details or [])
        assert "missing=['pct_no_positive_movement']" in details
        assert "extras=['no_positive_movement_pct']" in details

    def test_fails_on_column_order_mismatch(self, tmp_path: Path):
        # Same column set, swapped order — the bug shape that
        # enrollment_demographic_shares had until the schema reorder.
        gold_dir = tmp_path / "topic"
        gold_dir.mkdir()
        contract = _write_contract(
            tmp_path / "fixture_topic.odcs.yaml",
            ["year", "met_ayp", "pct_of_enrollment"],
        )
        _write_parquet(gold_dir, 2024, ["year", "pct_of_enrollment", "met_ayp"])
        result = check_contract_parquet_schema(gold_dir, contract_path=contract)
        assert result.status == "fail"
        details = " ".join(result.details or [])
        assert "column order differs" in details
        assert "index 1" in details
        assert "'met_ayp'" in details
        assert "'pct_of_enrollment'" in details

    def test_warns_when_contract_missing(self, tmp_path: Path):
        gold_dir = tmp_path / "topic"
        gold_dir.mkdir()
        _write_parquet(gold_dir, 2024, ["year", "score"])
        result = check_contract_parquet_schema(
            gold_dir, contract_path=tmp_path / "absent.odcs.yaml"
        )
        assert result.status == "warning"


# =============================================================================
# check_grain_uniqueness
# =============================================================================


class TestCheckGrainUniqueness:
    def test_passes_on_unique_grain(self):
        df = pl.DataFrame(
            {"year": [2024, 2024], "district_code": ["601", "602"], "v": [1, 2]}
        )
        result = check_grain_uniqueness(df, ["year", "district_code"])
        assert result.status == "pass"

    def test_fails_on_duplicate_rows(self):
        df = pl.DataFrame(
            {"year": [2024, 2024], "district_code": ["601", "601"], "v": [1, 2]}
        )
        result = check_grain_uniqueness(df, ["year", "district_code"])
        assert result.status == "fail"
        assert "1 duplicate grain group" in result.message

    def test_null_grain_keys_count_as_duplicates(self):
        # Two state rows (NULL geography) with the same year ARE duplicates —
        # polars group_by treats NULL keys as equal, which is what we want.
        df = pl.DataFrame(
            {"year": [2024, 2024], "district_code": [None, None], "v": [1, 2]}
        )
        result = check_grain_uniqueness(df, ["year", "district_code"])
        assert result.status == "fail"

    def test_fails_on_missing_grain_column(self):
        df = pl.DataFrame({"year": [2024]})
        result = check_grain_uniqueness(df, ["year", "district_code"])
        assert result.status == "fail"
        assert "district_code" in (result.details or [])

    def test_fails_on_empty_grain(self):
        df = pl.DataFrame({"year": [2024]})
        result = check_grain_uniqueness(df, [])
        assert result.status == "fail"


# =============================================================================
# check_contract_quality_sql
# =============================================================================


def _quality_contract(quality: list[dict]) -> dict:
    return {"schema": [{"name": "t", "properties": [], "quality": quality}]}


class TestCheckContractQualitySql:
    @pytest.fixture()
    def gold_dir(self, tmp_path: Path) -> Path:
        gold_dir = tmp_path / "education" / "fixture_topic"
        year_dir = gold_dir / "year=2024"
        year_dir.mkdir(parents=True)
        pl.DataFrame(
            {
                "year": pl.Series([2024, 2024], dtype=pl.Int32),
                "grade_level": ["08", "09"],
                "graduation_rate": [0.95, 1.4],
            }
        ).write_parquet(year_dir / "schools.parquet")
        return gold_dir

    def test_must_be_pass_and_fail(self, gold_dir: Path):
        contract = _quality_contract(
            [
                {
                    "type": "sql",
                    "name": "rate_within_unit_interval",
                    "query": (
                        "SELECT COUNT(*) FROM {object} WHERE graduation_rate "
                        "IS NOT NULL AND (graduation_rate < 0 OR graduation_rate > 1)"
                    ),
                    "mustBe": 0,
                }
            ]
        )
        result = check_contract_quality_sql(gold_dir, contract)
        assert result.status == "fail"
        assert any("result=1 expected == 0" in d for d in result.details or [])

    def test_must_be_greater_than_and_less_than(self, gold_dir: Path):
        contract = _quality_contract(
            [
                {
                    "type": "sql",
                    "name": "non_empty",
                    "query": "SELECT COUNT(*) FROM {object}",
                    "mustBeGreaterThan": 0,
                },
                {
                    "type": "sql",
                    "name": "small",
                    "query": "SELECT COUNT(*) FROM {object}",
                    "mustBeLessThan": 100,
                },
            ]
        )
        result = check_contract_quality_sql(gold_dir, contract)
        assert result.status == "pass"
        assert "All 2 contract quality checks pass" in result.message

    def test_query_error_reports_fail_not_crash(self, gold_dir: Path):
        contract = _quality_contract(
            [
                {
                    "type": "sql",
                    "name": "bad_column",
                    "query": "SELECT COUNT(*) FROM {object} WHERE nonexistent > 0",
                    "mustBe": 0,
                }
            ]
        )
        result = check_contract_quality_sql(gold_dir, contract)
        assert result.status == "fail"
        assert any("query error" in d for d in result.details or [])

    def test_enum_check_matches_zero_padded_strings(self, gold_dir: Path):
        # The contract's literal SQL embeds quoted '08'/'09' — executing it
        # verbatim must NOT coerce them to integers (which would silently
        # neuter the check).
        contract = _quality_contract(
            [
                {
                    "type": "sql",
                    "name": "grade_level_in_allowed_values",
                    "query": (
                        "SELECT COUNT(*) FROM {object} WHERE grade_level IS NOT "
                        "NULL AND grade_level NOT IN ('08', '09')"
                    ),
                    "mustBe": 0,
                }
            ]
        )
        result = check_contract_quality_sql(gold_dir, contract)
        assert result.status == "pass"

    def test_no_sql_entries_passes(self, gold_dir: Path):
        result = check_contract_quality_sql(gold_dir, _quality_contract([]))
        assert result.status == "pass"

    def test_single_parquet_file_target(self, gold_dir: Path):
        # Dimension builds validate a single parquet file, not a directory.
        single = gold_dir / "year=2024" / "schools.parquet"
        contract = _quality_contract(
            [
                {
                    "type": "sql",
                    "name": "non_empty",
                    "query": "SELECT COUNT(*) FROM {object}",
                    "mustBeGreaterThan": 0,
                }
            ]
        )
        result = check_contract_quality_sql(single, contract)
        assert result.status == "pass"


# =============================================================================
# check_foreign_keys
# =============================================================================


class TestCheckForeignKeys:
    @pytest.fixture()
    def tree(self, tmp_path: Path) -> dict:
        """Gold tree: root/_dimensions, root/education/_dimensions, topic."""
        root = tmp_path / "gold"
        edu_dims = root / "education" / "_dimensions"
        global_dims = root / "_dimensions"
        edu_dims.mkdir(parents=True)
        global_dims.mkdir(parents=True)
        pl.DataFrame({"district_code": ["601", "602"]}).write_parquet(
            edu_dims / "districts.parquet"
        )
        pl.DataFrame(
            {"district_code": ["601", "602"], "school_code": ["0103", "0103"]}
        ).write_parquet(edu_dims / "schools.parquet")
        pl.DataFrame({"demographic": ["all", "black"]}).write_parquet(
            global_dims / "demographics.parquet"
        )
        gold_dir = root / "education" / "fixture_topic"
        gold_dir.mkdir(parents=True)
        return {"root": root, "gold_dir": gold_dir}

    DISTRICT_FK = {
        "column": "district_code",
        "target_object": "districts",
        "target_columns": ["district_code"],
        "scope": "domain",
    }
    SCHOOL_FK = {
        "column": "school_code",
        "target_object": "schools",
        "target_columns": ["district_code", "school_code"],
        "scope": "domain",
    }
    DEMO_FK = {
        "column": "demographic",
        "target_object": "demographics",
        "target_columns": ["demographic"],
        "scope": "global",
    }

    def test_passes_when_keys_resolve(self, tree: dict):
        df = pl.DataFrame(
            {
                "district_code": ["601", "602", None],
                "school_code": ["0103", None, None],
                "demographic": ["all", "black", "all"],
            }
        )
        result = check_foreign_keys(
            df, tree["gold_dir"], [self.DISTRICT_FK, self.SCHOOL_FK, self.DEMO_FK]
        )
        assert result.status == "pass"

    def test_fails_on_orphan_key_with_samples(self, tree: dict):
        df = pl.DataFrame({"district_code": ["601", "999"]})
        result = check_foreign_keys(df, tree["gold_dir"], [self.DISTRICT_FK])
        assert result.status == "fail"
        assert any("1 orphan key" in d and "999" in d for d in result.details or [])

    def test_composite_school_key_requires_pair_match(self, tree: dict):
        # school 0103 exists, but only under districts 601/602 — the same
        # code under 603 is an orphan a single-column check would miss.
        df = pl.DataFrame({"district_code": ["603"], "school_code": ["0103"]})
        result = check_foreign_keys(df, tree["gold_dir"], [self.SCHOOL_FK])
        assert result.status == "fail"

    def test_global_scope_resolves_root_dimensions(self, tree: dict):
        df = pl.DataFrame({"demographic": ["all", "martian"]})
        result = check_foreign_keys(df, tree["gold_dir"], [self.DEMO_FK])
        assert result.status == "fail"
        assert any("martian" in d for d in result.details or [])

    def test_fails_when_dimension_parquet_missing(self, tree: dict):
        df = pl.DataFrame({"district_code": ["601"]})
        fk = dict(self.DISTRICT_FK, target_object="nonexistent")
        result = check_foreign_keys(df, tree["gold_dir"], [fk])
        assert result.status == "fail"
        assert any("dimension missing" in d for d in result.details or [])

    def test_null_fk_rows_ignored(self, tree: dict):
        df = pl.DataFrame({"district_code": [None, None]})
        result = check_foreign_keys(df, tree["gold_dir"], [self.DISTRICT_FK])
        assert result.status == "pass"

    def test_no_fks_passes(self, tree: dict):
        result = check_foreign_keys(pl.DataFrame({"a": [1]}), tree["gold_dir"], [])
        assert result.status == "pass"


# =============================================================================
# check_canonical_vocabulary
# =============================================================================


class TestCheckCanonicalVocabulary:
    def test_flags_variant_columns(self):
        df = pl.DataFrame({"year": [1], "number_tested": [2]})
        result = check_canonical_vocabulary(df)
        assert result.status == "fail"
        assert any("num_tested" in d for d in result.details or [])

    def test_canonical_columns_pass(self):
        df = pl.DataFrame({"year": [1], "num_tested": [2], "grade_level": ["08"]})
        assert check_canonical_vocabulary(df).status == "pass"


# =============================================================================
# run_topic_validation (the contract-driven entry point)
# =============================================================================


def _full_fixture(tmp_path: Path) -> dict:
    """A complete passing fixture: gold tree + dimensions + contract file."""
    root = tmp_path / "gold"
    edu_dims = root / "education" / "_dimensions"
    edu_dims.mkdir(parents=True)
    pl.DataFrame({"district_code": ["601"]}).write_parquet(
        edu_dims / "districts.parquet"
    )

    gold_dir = root / "education" / "fixture_topic"
    year_dir = gold_dir / "year=2024"
    year_dir.mkdir(parents=True)
    pl.DataFrame(
        {
            "year": pl.Series([2024], dtype=pl.Int32),
            "district_code": ["601"],
            "school_code": ["0103"],
            "num_tested": pl.Series([10], dtype=pl.Int64),
        }
    ).write_parquet(year_dir / "schools.parquet")

    contract = {
        "schema": [
            {
                "name": "fixture_topic",
                "properties": [
                    {
                        "name": "year",
                        "logicalType": "integer",
                        "physicalType": "int",
                        "customProperties": [
                            {"property": "column_role", "value": "year"}
                        ],
                    },
                    {
                        "name": "district_code",
                        "logicalType": "string",
                        "physicalType": "string",
                        "customProperties": [
                            {"property": "column_role", "value": "fk_district"}
                        ],
                    },
                    {
                        "name": "school_code",
                        "logicalType": "string",
                        "physicalType": "string",
                        "customProperties": [
                            {"property": "column_role", "value": "fk_school"}
                        ],
                    },
                    {
                        "name": "num_tested",
                        "logicalType": "integer",
                        "physicalType": "bigint",
                        "customProperties": [
                            {"property": "column_role", "value": "metric"},
                            {"property": "unit", "value": "count"},
                        ],
                    },
                ],
                "customProperties": [
                    {
                        "property": "grain",
                        "value": ["year", "district_code", "school_code"],
                    },
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
                    },
                ],
                "quality": [
                    {
                        "type": "sql",
                        "name": "non_empty",
                        "query": "SELECT COUNT(*) FROM {object}",
                        "mustBeGreaterThan": 0,
                    },
                    {
                        "type": "sql",
                        "name": "num_tested_non_negative",
                        "query": (
                            "SELECT COUNT(*) FROM {object} WHERE num_tested "
                            "IS NOT NULL AND num_tested < 0"
                        ),
                        "mustBe": 0,
                    },
                ],
            }
        ]
    }
    contract_path = tmp_path / "fixture_topic.odcs.yaml"
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False))
    return {"gold_dir": gold_dir, "contract_path": contract_path}


class TestRunTopicValidation:
    def test_end_to_end_pass_writes_validation_json(self, tmp_path: Path):
        fx = _full_fixture(tmp_path)
        report = run_topic_validation(fx["gold_dir"], contract_path=fx["contract_path"])
        assert report.passed
        assert (fx["gold_dir"] / "_validation.json").exists()
        names = {c.name for c in report.checks}
        assert {
            "grain_uniqueness",
            "contract_quality_sql",
            "foreign_keys",
            "canonical_vocabulary",
        } <= names

    def test_missing_contract_writes_fail_report_and_raises(self, tmp_path: Path):
        fx = _full_fixture(tmp_path)
        with pytest.raises(GoldValidationError, match="contract precondition"):
            run_topic_validation(
                fx["gold_dir"],
                contract_path=tmp_path / "absent.odcs.yaml",
                raise_on_failure=False,  # precondition raises regardless
            )
        val = (fx["gold_dir"] / "_validation.json").read_text()
        assert "contract_present" in val

    def test_check_failure_raises_gold_validation_error(self, tmp_path: Path):
        fx = _full_fixture(tmp_path)
        # Orphan the FK: rewrite gold with a district missing from the dim.
        pl.DataFrame(
            {
                "year": pl.Series([2024], dtype=pl.Int32),
                "district_code": ["999"],
                "school_code": ["0103"],
                "num_tested": pl.Series([10], dtype=pl.Int64),
            }
        ).write_parquet(fx["gold_dir"] / "year=2024" / "schools.parquet")
        with pytest.raises(GoldValidationError, match="foreign_keys"):
            run_topic_validation(fx["gold_dir"], contract_path=fx["contract_path"])

    def test_raise_on_failure_false_returns_failed_report(self, tmp_path: Path):
        fx = _full_fixture(tmp_path)
        pl.DataFrame(
            {
                "year": pl.Series([2024], dtype=pl.Int32),
                "district_code": ["999"],
                "school_code": ["0103"],
                "num_tested": pl.Series([10], dtype=pl.Int64),
            }
        ).write_parquet(fx["gold_dir"] / "year=2024" / "schools.parquet")
        report = run_topic_validation(
            fx["gold_dir"], contract_path=fx["contract_path"], raise_on_failure=False
        )
        assert not report.passed

    def test_explicit_topic_config_still_supported(self, tmp_path: Path):
        # Legacy/fixture path: an explicit dict (even {}) means "do not
        # derive from the contract".
        fx = _full_fixture(tmp_path)
        runner = ValidationRunner(
            gold_dir=fx["gold_dir"],
            domain_config={},
            topic_config={},
        )
        report = runner.run_all()
        # Without a contract at the default path, the contract-driven checks
        # degrade to warnings, never crash.
        statuses = {c.name: c.status for c in report.checks}
        assert statuses["grain_uniqueness"] == "warning"
        assert statuses["contract_quality_sql"] == "warning"
        assert statuses["foreign_keys"] == "warning"
