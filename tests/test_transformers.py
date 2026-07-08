"""Tests for shared transformer utilities.

Covers harmonize_columns, deduplicate_by_detail_level, validate_output,
export_to_parquet, and title_case_name — the core functions that all
topic transforms depend on.
"""

import polars as pl
import pytest

from src.utils.transformers import (
    RowCountTracker,
    aggregate_demographic_collisions,
    deduplicate_by_detail_level,
    detect_era_by_columns,
    export_to_parquet,
    harmonize_columns,
    null_aggregate_geography,
    title_case_name,
    validate_output,
)

# =============================================================================
# RowCountTracker
# =============================================================================


class TestRowCountTracker:
    def test_record_and_summary(self):
        tracker = RowCountTracker()
        tracker.record_bronze(2020, 100)
        tracker.record_bronze(2021, 200)
        df = pl.DataFrame({"year": [2020] * 90 + [2021] * 180})
        tracker.record_gold_from_dataframe(df)

        summary = tracker.summary()
        assert summary["total_bronze"] == 300
        assert summary["total_gold"] == 270
        # total_filtered is derived as bronze - gold (captures dedup/filter loss).
        assert summary["total_filtered"] == 30
        assert summary["years_processed"] == 2

    def test_expansion_factor(self):
        tracker = RowCountTracker()
        tracker.record_bronze(2020, 100)
        df = pl.DataFrame({"year": [2020] * 300})
        tracker.record_gold_from_dataframe(df)
        assert tracker.expansion_factors[2020] == 3.0

    def test_record_gold_from_dataframe_overwrites_prior_state(self):
        # Calling twice should not accumulate — the second call is authoritative.
        tracker = RowCountTracker()
        tracker.record_bronze(2020, 100)
        tracker.record_gold_from_dataframe(pl.DataFrame({"year": [2020] * 50}))
        tracker.record_gold_from_dataframe(pl.DataFrame({"year": [2020] * 40}))
        assert tracker.gold_rows_by_year == {2020: 40}
        assert tracker.expansion_factors[2020] == 0.4

    def test_record_gold_from_dataframe_custom_year_col(self):
        tracker = RowCountTracker()
        tracker.record_bronze(2020, 100)
        df = pl.DataFrame({"report_year": [2020] * 90})
        tracker.record_gold_from_dataframe(df, year_col="report_year")
        assert tracker.gold_rows_by_year == {2020: 90}

    def test_record_gold_from_dataframe_missing_year_col_raises(self):
        tracker = RowCountTracker()
        df = pl.DataFrame({"other_col": [1, 2, 3]})
        with pytest.raises(ValueError, match="year column 'year' not in"):
            tracker.record_gold_from_dataframe(df)

    def test_filtered_by_year_derives_from_bronze_minus_gold(self):
        tracker = RowCountTracker()
        tracker.record_bronze(2020, 100)
        tracker.record_bronze(2021, 200)
        df = pl.DataFrame({"year": [2020] * 90 + [2021] * 200})
        tracker.record_gold_from_dataframe(df)
        filtered = tracker.filtered_by_year()
        assert filtered == {2020: 10, 2021: 0}

    def test_summary_omits_explicit_filtered_when_no_events(self):
        # Backward compatibility: with no explicit events recorded, the summary
        # carries only the original keys and no `filtered_explicit*` keys.
        tracker = RowCountTracker()
        tracker.record_bronze(2020, 100)
        tracker.record_gold_from_dataframe(pl.DataFrame({"year": [2020] * 90}))
        summary = tracker.summary()
        assert summary["total_filtered"] == 10
        assert "filtered_explicit" not in summary
        assert "filtered_explicit_by_year" not in summary

    def test_record_filtered_surfaces_in_expand_summary(self):
        # Unpivot/expand transform: gold rows > bronze rows, so the derived
        # `bronze - gold` filtered figure is 0. The explicit filter events must
        # still surface additively without changing total_filtered.
        tracker = RowCountTracker()
        tracker.record_bronze(2010, 2506)
        # Expansion: each bronze row fans out to ~9 demographic rows.
        tracker.record_gold_from_dataframe(pl.DataFrame({"year": [2010] * 22068}))
        tracker.record_filtered(2010, 1, "malformed_sysschoolid")
        tracker.record_filtered(2010, 53, "duplicate_sysschoolid")

        summary = tracker.summary()
        # Derived figure is unchanged (still 0 for an expand transform).
        assert summary["total_filtered"] == 0
        # Explicit events surface additively.
        assert summary["filtered_explicit"] == 54
        assert summary["filtered_explicit_by_year"] == {2010: 54}
        assert summary["filtered_explicit_by_reason"] == {
            "malformed_sysschoolid": 1,
            "duplicate_sysschoolid": 53,
        }

    def test_record_filtered_ignores_zero_and_negative_counts(self):
        # Defensive no-op call sites (count 0) must not litter the manifest.
        tracker = RowCountTracker()
        tracker.record_filtered(2008, 0, "duplicate_sysschoolid")
        tracker.record_filtered(2008, -3, "malformed_sysschoolid")
        assert tracker.filtered_events == []
        # Summary stays in its original shape when every event was a no-op.
        assert "filtered_explicit" not in tracker.summary()


# =============================================================================
# harmonize_columns
# =============================================================================


class TestHarmonizeColumns:
    def test_adds_missing_columns_as_null(self):
        df1 = pl.DataFrame({"year": [2020], "metric_a": [1.0]})
        df2 = pl.DataFrame({"year": [2021], "metric_b": [2.0]})
        standard = ["year", "metric_a", "metric_b"]
        target_types = {"metric_a": pl.Float64, "metric_b": pl.Float64}

        result = harmonize_columns([df1, df2], standard, target_types)
        assert len(result) == 2

        # df1 should now have metric_b as null
        assert "metric_b" in result[0].columns
        assert result[0]["metric_b"].null_count() == 1

        # df2 should now have metric_a as null
        assert "metric_a" in result[1].columns
        assert result[1]["metric_a"].null_count() == 1

    def test_column_order_matches_standard(self):
        df = pl.DataFrame({"metric_b": [1.0], "year": [2020], "metric_a": [2.0]})
        standard = ["year", "metric_a", "metric_b"]

        result = harmonize_columns([df], standard)
        assert result[0].columns == ["year", "metric_a", "metric_b"]

    def test_casts_existing_columns_to_target_types(self):
        df = pl.DataFrame({"year": [2020], "count": ["100"]})
        standard = ["year", "count"]
        target_types = {"count": pl.Int64}

        result = harmonize_columns([df], standard, target_types)
        assert result[0]["count"].dtype == pl.Int64
        assert result[0]["count"][0] == 100

    def test_empty_list_returns_empty(self):
        result = harmonize_columns([], ["year"])
        assert result == []

    def test_extra_columns_appended_alphabetically(self):
        df = pl.DataFrame({"year": [2020], "zzz": [1], "aaa": [2]})
        standard = ["year"]

        result = harmonize_columns([df], standard)
        assert result[0].columns == ["year", "aaa", "zzz"]

    def test_missing_column_defaults_to_utf8(self):
        df1 = pl.DataFrame({"year": [2020], "name": ["test"]})
        df2 = pl.DataFrame({"year": [2021]})
        standard = ["year", "name"]

        result = harmonize_columns([df1, df2], standard)
        assert result[1]["name"].dtype == pl.Utf8


# =============================================================================
# deduplicate_by_detail_level
# =============================================================================


class TestDeduplicateByDetailLevel:
    def test_removes_duplicates_keeping_higher_value(self):
        df = pl.DataFrame(
            {
                "year": [2020, 2020],
                "district_code": ["001", "001"],
                "school_code": ["0001", "0001"],
                "detail_level": ["school", "school"],
                "demographic": ["all", "all"],
                "num_tested": [100, 50],
            }
        )
        school_keys = ["year", "district_code", "school_code", "demographic"]
        district_keys = ["year", "district_code", "demographic"]
        state_keys = ["year", "demographic"]

        result = deduplicate_by_detail_level(df, school_keys, district_keys, state_keys)
        assert result.height == 1
        assert result["num_tested"][0] == 100

    def test_prefers_non_null_over_null(self):
        df = pl.DataFrame(
            {
                "year": [2020, 2020],
                "district_code": ["001", "001"],
                "detail_level": ["district", "district"],
                "demographic": ["all", "all"],
                "num_tested": [None, 50],
            }
        )
        school_keys = ["year", "district_code", "school_code", "demographic"]
        district_keys = ["year", "district_code", "demographic"]
        state_keys = ["year", "demographic"]

        result = deduplicate_by_detail_level(df, school_keys, district_keys, state_keys)
        assert result.height == 1
        assert result["num_tested"][0] == 50

    def test_no_duplicates_unchanged(self):
        df = pl.DataFrame(
            {
                "year": [2020, 2021],
                "detail_level": ["state", "state"],
                "demographic": ["all", "all"],
                "num_tested": [100, 200],
            }
        )
        result = deduplicate_by_detail_level(
            df,
            ["year", "demographic"],
            ["year", "demographic"],
            ["year", "demographic"],
        )
        assert result.height == 2

    def test_handles_multiple_detail_levels(self):
        df = pl.DataFrame(
            {
                "year": [2020, 2020, 2020, 2020],
                "district_code": [None, "001", "001", "001"],
                "school_code": [None, None, "0001", "0001"],
                "detail_level": ["state", "district", "school", "school"],
                "demographic": ["all", "all", "all", "all"],
                "num_tested": [1000, 500, 100, 80],
            }
        )
        school_keys = ["year", "district_code", "school_code", "demographic"]
        district_keys = ["year", "district_code", "demographic"]
        state_keys = ["year", "demographic"]

        result = deduplicate_by_detail_level(df, school_keys, district_keys, state_keys)
        assert result.height == 3  # one per detail level


# =============================================================================
# validate_output
# =============================================================================


class TestValidateOutput:
    def test_passes_valid_data(self):
        df = pl.DataFrame(
            {
                "year": pl.Series([2020], dtype=pl.Int32),
                "detail_level": ["state"],
                "demographic": ["all"],
                "district_code": pl.Series([None], dtype=pl.Utf8),
            }
        )
        assert validate_output(df) is True

    def test_fails_on_unmatched_demographics(self):
        df = pl.DataFrame(
            {
                "year": [2020],
                "detail_level": ["state"],
                "demographic": ["99999999"],
            }
        )
        assert validate_output(df) is False

    def test_fails_on_invalid_demographic_value(self):
        df = pl.DataFrame(
            {
                "year": [2020],
                "detail_level": ["state"],
                "demographic": ["not_a_real_demographic"],
            }
        )
        assert validate_output(df) is False

    def test_fails_on_integer_id_column(self):
        df = pl.DataFrame(
            {
                "year": [2020],
                "detail_level": ["district"],
                "district_code": [1],  # Should be string
            }
        )
        assert validate_output(df) is False

    def test_passes_without_demographic_column(self):
        df = pl.DataFrame(
            {
                "year": [2020],
                "detail_level": ["state"],
            }
        )
        assert validate_output(df) is True

    def test_raises_on_log_only_false(self):
        df = pl.DataFrame(
            {
                "year": [2020],
                "detail_level": ["state"],
                "demographic": ["99999999"],
            }
        )
        with pytest.raises(AssertionError):
            validate_output(df, log_only=False)


# =============================================================================
# export_to_parquet
# =============================================================================


class TestExportToParquet:
    def test_creates_year_partitioned_files(self, tmp_path):
        df = pl.DataFrame(
            {
                "year": [2020, 2020, 2021],
                "detail_level": ["state", "district", "state"],
                "district_code": [None, "001", None],
                "num_tested": [1000, 500, 1100],
            }
        )
        standard_columns = ["year", "detail_level", "district_code", "num_tested"]

        export_to_parquet(df, tmp_path, standard_columns)

        assert (tmp_path / "year=2020" / "states.parquet").exists()
        assert (tmp_path / "year=2020" / "districts.parquet").exists()
        assert (tmp_path / "year=2021" / "states.parquet").exists()
        assert not (tmp_path / "year=2021" / "districts.parquet").exists()

    def test_drops_detail_level_from_output(self, tmp_path):
        df = pl.DataFrame(
            {
                "year": [2020],
                "detail_level": ["state"],
                "num_tested": [1000],
            }
        )
        export_to_parquet(df, tmp_path, ["year", "detail_level", "num_tested"])

        result = pl.read_parquet(tmp_path / "year=2020" / "states.parquet")
        assert "detail_level" not in result.columns

    def test_does_not_create_empty_files(self, tmp_path):
        df = pl.DataFrame(
            {
                "year": [2020],
                "detail_level": ["state"],
                "num_tested": [1000],
            }
        )
        export_to_parquet(df, tmp_path, ["year", "detail_level", "num_tested"])

        assert not (tmp_path / "year=2020" / "schools.parquet").exists()
        assert not (tmp_path / "year=2020" / "districts.parquet").exists()

    def test_selects_standard_columns_only(self, tmp_path):
        df = pl.DataFrame(
            {
                "year": [2020],
                "detail_level": ["state"],
                "num_tested": [1000],
                "extra_col": ["should be dropped"],
            }
        )
        standard_columns = ["year", "detail_level", "num_tested"]

        export_to_parquet(df, tmp_path, standard_columns)

        result = pl.read_parquet(tmp_path / "year=2020" / "states.parquet")
        assert "extra_col" not in result.columns


# =============================================================================
# title_case_name
# =============================================================================


class TestTitleCaseName:
    def test_basic_title_case(self):
        df = pl.DataFrame({"name": ["FULTON COUNTY"]})
        result = df.select(pl.col("name").pipe(title_case_name))
        assert result["name"][0] == "Fulton County"

    def test_dekalb_override(self):
        df = pl.DataFrame({"name": ["DEKALB COUNTY"]})
        result = df.select(pl.col("name").pipe(title_case_name))
        assert result["name"][0] == "DeKalb County"

    def test_mcduffie_override(self):
        df = pl.DataFrame({"name": ["MCDUFFIE COUNTY"]})
        result = df.select(pl.col("name").pipe(title_case_name))
        assert result["name"][0] == "McDuffie County"

    def test_steam_override(self):
        df = pl.DataFrame({"name": ["STEAM ACADEMY"]})
        result = df.select(pl.col("name").pipe(title_case_name))
        assert result["name"][0] == "STEAM Academy"

    def test_roman_numeral_ii(self):
        df = pl.DataFrame({"name": ["CHARTER SCHOOLS II"]})
        result = df.select(pl.col("name").pipe(title_case_name))
        assert result["name"][0] == "Charter Schools II"

    def test_strips_whitespace(self):
        df = pl.DataFrame({"name": ["  FULTON COUNTY  "]})
        result = df.select(pl.col("name").pipe(title_case_name))
        assert result["name"][0] == "Fulton County"


# =============================================================================
# aggregate_demographic_collisions
# =============================================================================


class TestAggregateDemographicCollisions:
    def test_collapses_two_colliding_rows(self):
        # Two raw "Hispanic" subgroups both normalized to "hispanic" produce
        # duplicate natural keys. Counts must sum; scores must weight-average.
        df = pl.DataFrame(
            {
                "year": [2005, 2005],
                "district_code": ["001", "001"],
                "demographic": ["hispanic", "hispanic"],
                "test_component": ["english", "english"],
                "num_tested": [10, 30],
                "avg_score": [20.0, 24.0],
            }
        )
        result = aggregate_demographic_collisions(
            df,
            natural_key_cols=[
                "year",
                "district_code",
                "demographic",
                "test_component",
            ],
            sum_cols=["num_tested"],
            weighted_avg_cols={"avg_score": "num_tested"},
        )
        assert result.height == 1
        assert result["num_tested"][0] == 40
        # weighted avg = (10*20 + 30*24) / 40 = 23.0
        assert result["avg_score"][0] == 23.0

    def test_noncolliding_rows_passthrough(self):
        df = pl.DataFrame(
            {
                "year": [2005, 2005],
                "demographic": ["hispanic", "white"],
                "num_tested": [10, 20],
                "avg_score": [20.0, 22.0],
            }
        )
        result = aggregate_demographic_collisions(
            df,
            natural_key_cols=["year", "demographic"],
            sum_cols=["num_tested"],
            weighted_avg_cols={"avg_score": "num_tested"},
        )
        assert result.height == 2
        assert sorted(result["num_tested"].to_list()) == [10, 20]

    def test_no_collisions_returns_input_unchanged(self):
        df = pl.DataFrame(
            {
                "year": [2020, 2021],
                "demographic": ["all", "all"],
                "num_tested": [100, 200],
            }
        )
        result = aggregate_demographic_collisions(
            df,
            natural_key_cols=["year", "demographic"],
            sum_cols=["num_tested"],
        )
        assert result.height == 2

    def test_weighted_avg_ignores_null_metrics(self):
        # When one colliding row has a null score, the weight from that row
        # must be excluded from the denominator (otherwise the weighted avg is
        # diluted by zero).
        df = pl.DataFrame(
            {
                "year": [2020, 2020],
                "demographic": ["hispanic", "hispanic"],
                "num_tested": [10, 40],
                "avg_score": [None, 25.0],
            },
            schema={
                "year": pl.Int64,
                "demographic": pl.Utf8,
                "num_tested": pl.Int64,
                "avg_score": pl.Float64,
            },
        )
        result = aggregate_demographic_collisions(
            df,
            natural_key_cols=["year", "demographic"],
            sum_cols=["num_tested"],
            weighted_avg_cols={"avg_score": "num_tested"},
        )
        assert result.height == 1
        assert result["num_tested"][0] == 50
        assert result["avg_score"][0] == 25.0


# =============================================================================
# null_aggregate_geography
# =============================================================================


class TestNullAggregateGeography:
    _RULES = {
        "states": {"district_code": "null", "school_code": "null"},
        "districts": {"district_code": "not_null", "school_code": "null"},
        "schools": {"district_code": "not_null", "school_code": "not_null"},
    }

    def test_nulls_at_state_level(self):
        df = pl.DataFrame(
            {
                "detail_level": ["state", "district", "school"],
                "district_code": ["ALL", "001", "001"],
                "school_code": ["ALL", "ALL", "0001"],
            }
        )
        result = null_aggregate_geography(df, "detail_level", self._RULES)
        assert result["district_code"].to_list() == [None, "001", "001"]
        assert result["school_code"].to_list() == [None, None, "0001"]

    def test_handles_singular_level_keys(self):
        # Education domain config uses plural detail level keys ("states"),
        # but the detail_level column values are singular ("state"). The
        # helper must accept both conventions.
        df = pl.DataFrame(
            {
                "detail_level": ["state"],
                "district_code": ["XYZ"],
                "school_code": ["ABC"],
            }
        )
        result = null_aggregate_geography(df, "detail_level", self._RULES)
        assert result["district_code"][0] is None
        assert result["school_code"][0] is None

    def test_missing_detail_level_col_noop(self):
        df = pl.DataFrame({"district_code": ["001"]})
        result = null_aggregate_geography(df, "detail_level", self._RULES)
        assert result["district_code"][0] == "001"


# =============================================================================
# detect_era_by_columns
# =============================================================================


class TestDetectEraByColumns:
    _SIGS = {
        "era_3": ["TEST_CMPNT_TYP_CD"],
        "era_1": ["SysSchoolID", "Composite All Students"],
        "era_2": ["SysSchoolid"],
    }

    def test_returns_first_matching_era(self):
        df = pl.DataFrame({"TEST_CMPNT_TYP_CD": ["X"]})
        assert detect_era_by_columns(df, self._SIGS) == "era_3"

    def test_requires_all_signature_columns(self):
        df = pl.DataFrame({"SysSchoolID": ["X"]})
        # era_1 requires BOTH SysSchoolID AND Composite All Students,
        # so this should not match era_1.
        assert detect_era_by_columns(df, self._SIGS) is None

    def test_ordering_determines_match(self):
        # A df with both SysSchoolID and SysSchoolid (hypothetical) should
        # match whichever era appears first in the signatures dict.
        df = pl.DataFrame(
            {
                "SysSchoolID": ["X"],
                "Composite All Students": ["Y"],
                "SysSchoolid": ["Z"],
            }
        )
        assert detect_era_by_columns(df, self._SIGS) == "era_1"

    def test_no_match_returns_none(self):
        df = pl.DataFrame({"unrelated_col": [1]})
        assert detect_era_by_columns(df, self._SIGS) is None
