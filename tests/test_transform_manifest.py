"""Tests for TransformManifest and related dataclasses."""

import json
from pathlib import Path

import polars as pl
import pytest

from src.utils.transformers import (
    CategoricalMapping,
    MetricStats,
    TransformManifest,
)

# =============================================================================
# MetricStats
# =============================================================================


class TestMetricStats:
    def test_to_dict(self):
        stats = MetricStats(
            non_null_count=100,
            null_count=10,
            null_pct=0.09090909,
            min_val=1.5,
            max_val=36.0,
            mean_val=21.3456789,
        )
        d = stats.to_dict()
        assert d["non_null_count"] == 100
        assert d["null_count"] == 10
        assert d["null_pct"] == 0.0909
        assert d["min_val"] == 1.5
        assert d["max_val"] == 36.0
        assert d["mean_val"] == 21.3457

    def test_to_dict_all_null(self):
        stats = MetricStats(
            non_null_count=0,
            null_count=50,
            null_pct=1.0,
            min_val=None,
            max_val=None,
            mean_val=None,
        )
        d = stats.to_dict()
        assert d["min_val"] is None
        assert d["max_val"] is None
        assert d["mean_val"] is None


# =============================================================================
# CategoricalMapping
# =============================================================================


class TestCategoricalMapping:
    def test_to_dict_sorts_values(self):
        mapping = CategoricalMapping(
            map_used={"B": "b", "A": "a"},
            bronze_values_seen=["B", "A"],
            gold_values_produced=["b", "a"],
            unmapped_count=0,
            unmapped_values=[],
        )
        d = mapping.to_dict()
        assert d["bronze_values_seen"] == ["A", "B"]
        assert d["gold_values_produced"] == ["a", "b"]


# =============================================================================
# TransformManifest
# =============================================================================


class TestTransformManifest:
    @pytest.fixture
    def manifest(self, tmp_path: Path) -> TransformManifest:
        return TransformManifest(
            topic="test_topic",
            bronze_dir=tmp_path / "bronze",
            gold_dir=tmp_path / "gold",
        )

    def test_record_bronze_delegates_to_tracker(self, manifest: TransformManifest):
        manifest.record_bronze(2020, 500)
        assert manifest.tracker.bronze_rows_by_year[2020] == 500

    def test_record_gold_from_dataframe_delegates_to_tracker(
        self, manifest: TransformManifest
    ):
        manifest.record_bronze(2020, 500)
        df = pl.DataFrame({"year": [2020] * 450})
        manifest.record_gold_from_dataframe(df)
        assert manifest.tracker.gold_rows_by_year[2020] == 450
        assert manifest.tracker.expansion_factors[2020] == pytest.approx(0.9)

    def test_record_file(self, manifest: TransformManifest, tmp_path: Path):
        manifest.record_file(
            path=tmp_path / "data.xlsx",
            year=2020,
            era="era_3",
            bronze_rows=500,
            bronze_columns=["COL_A", "COL_B"],
        )
        assert len(manifest.files_processed) == 1
        assert manifest.files_processed[0]["file"] == "data.xlsx"
        assert manifest.files_processed[0]["year"] == 2020
        assert manifest.files_processed[0]["era"] == "era_3"
        assert manifest.files_processed[0]["bronze_rows"] == 500
        assert manifest.files_processed[0]["bronze_columns"] == ["COL_A", "COL_B"]

    def test_record_categorical_basic(self, manifest: TransformManifest):
        map_dict = {"Composite": "composite", "English": "english", "Math": "math"}
        bronze_series = pl.Series("raw", ["Composite", "English", "Math", "Composite"])
        gold_series = pl.Series("mapped", ["composite", "english", "math", "composite"])

        manifest.record_categorical(
            "test_component", map_dict, bronze_series, gold_series
        )

        cat = manifest.categorical_mappings["test_component"]
        assert cat.map_used == map_dict
        assert sorted(cat.bronze_values_seen) == ["Composite", "English", "Math"]
        assert sorted(cat.gold_values_produced) == ["composite", "english", "math"]
        assert cat.unmapped_count == 0
        assert cat.unmapped_values == []

    def test_record_categorical_with_unmapped(self, manifest: TransformManifest):
        map_dict = {"Composite": "composite", "English": "english"}
        bronze_series = pl.Series("raw", ["Composite", "English", "Unknown"])
        gold_series = pl.Series("mapped", ["composite", "english", "99999999"])

        manifest.record_categorical(
            "test_component", map_dict, bronze_series, gold_series
        )

        cat = manifest.categorical_mappings["test_component"]
        assert cat.unmapped_count == 1
        assert cat.unmapped_values == ["Unknown"]

    def test_record_categorical_merges_across_eras(self, manifest: TransformManifest):
        # Era 1 has subjects A and B
        map1 = {"A": "a", "B": "b"}
        manifest.record_categorical(
            "subject",
            map1,
            pl.Series("raw", ["A", "B"]),
            pl.Series("mapped", ["a", "b"]),
        )

        # Era 2 has subjects B and C
        map2 = {"B": "b", "C": "c"}
        manifest.record_categorical(
            "subject",
            map2,
            pl.Series("raw", ["B", "C"]),
            pl.Series("mapped", ["b", "c"]),
        )

        cat = manifest.categorical_mappings["subject"]
        assert sorted(cat.bronze_values_seen) == ["A", "B", "C"]
        assert sorted(cat.gold_values_produced) == ["a", "b", "c"]
        assert cat.map_used == {"A": "a", "B": "b", "C": "c"}
        assert cat.unmapped_count == 0

    def test_record_categorical_handles_nulls(self, manifest: TransformManifest):
        map_dict = {"X": "x"}
        bronze_series = pl.Series("raw", ["X", None, "X"])
        gold_series = pl.Series("mapped", ["x", None, "x"])

        manifest.record_categorical("col", map_dict, bronze_series, gold_series)

        cat = manifest.categorical_mappings["col"]
        assert cat.bronze_values_seen == ["X"]
        assert cat.gold_values_produced == ["x"]

    def test_compute_metric_stats(self, manifest: TransformManifest):
        df = pl.DataFrame(
            {
                "year": [2020, 2020, 2020, 2021, 2021],
                "score": [20.0, 25.0, None, 30.0, 35.0],
                "count": [100, 200, 300, 400, 500],
            }
        )
        manifest.compute_metric_stats(df, ["score", "count"])

        # Check score stats for 2020
        score_2020 = manifest.metric_stats["score"][2020]
        assert score_2020.non_null_count == 2
        assert score_2020.null_count == 1
        assert score_2020.null_pct == pytest.approx(1 / 3)
        assert score_2020.min_val == 20.0
        assert score_2020.max_val == 25.0
        assert score_2020.mean_val == 22.5

        # Check count stats for 2021
        count_2021 = manifest.metric_stats["count"][2021]
        assert count_2021.non_null_count == 2
        assert count_2021.null_count == 0
        assert count_2021.min_val == 400.0
        assert count_2021.max_val == 500.0

    def test_compute_metric_stats_missing_column(self, manifest: TransformManifest):
        df = pl.DataFrame({"year": [2020], "score": [10.0]})
        manifest.compute_metric_stats(df, ["score", "nonexistent"])
        assert "score" in manifest.metric_stats
        assert "nonexistent" not in manifest.metric_stats

    def test_to_dict_structure(self, manifest: TransformManifest, tmp_path: Path):
        manifest.record_file(tmp_path / "f.xlsx", 2020, "era_3", 100, ["A", "B"])
        manifest.record_bronze(2020, 100)
        manifest.record_categorical(
            "cat",
            {"X": "x"},
            pl.Series("r", ["X"]),
            pl.Series("m", ["x"]),
        )

        # Final DataFrame has 90 rows — 10 were dropped (dedup / filter).
        df = pl.DataFrame({"year": [2020] * 90, "val": [1.0] * 90})
        manifest.record_gold_from_dataframe(df)
        manifest.compute_metric_stats(df, ["val"])

        d = manifest.to_dict()

        assert "generated_at" in d
        assert d["topic"] == "test_topic"
        assert d["row_counts"]["total_bronze"] == 100
        assert d["row_counts"]["total_gold"] == 90
        # total_filtered is derived as bronze - gold, capturing every source
        # of row loss (explicit filters, dedup, collision aggregation).
        assert d["row_counts"]["total_filtered"] == 10
        assert d["row_counts"]["years_processed"] == 1
        assert "2020" in d["row_counts"]["by_year"]
        assert d["row_counts"]["by_year"]["2020"]["filtered"] == 10
        assert "cat" in d["categorical_mappings"]
        assert "val" in d["metric_stats"]
        assert "2020" in d["metric_stats"]["val"]

    def test_record_filtered_surfaces_in_manifest_for_expand(
        self, manifest: TransformManifest
    ):
        # Mirror retained_students 2010: an unpivot/expand year where gold rows
        # far exceed bronze rows, so the derived `filtered` figure is 0 but 54
        # rows (1 malformed + 53 dedup) were intentionally removed.
        manifest.record_bronze(2010, 2506)
        manifest.record_filtered(2010, 1, "malformed_sysschoolid")
        manifest.record_filtered(2010, 53, "duplicate_sysschoolid")
        df = pl.DataFrame({"year": [2010] * 22068, "val": [1.0] * 22068})
        manifest.record_gold_from_dataframe(df)

        d = manifest.to_dict()
        rc = d["row_counts"]
        # Derived filtered figure is unchanged (0 for an expand transform).
        assert rc["total_filtered"] == 0
        assert rc["by_year"]["2010"]["filtered"] == 0
        # Explicit filtered events surface additively.
        assert rc["by_year"]["2010"]["filtered_explicit"] == 54
        assert rc["total_filtered_explicit"] == 54
        assert rc["filtered_explicit_by_reason"] == {
            "malformed_sysschoolid": 1,
            "duplicate_sysschoolid": 53,
        }

    def test_to_dict_omits_explicit_filter_rollups_when_no_events(
        self, manifest: TransformManifest
    ):
        # Backward compatibility: without explicit events, the row_counts block
        # carries no `total_filtered_explicit` / `filtered_explicit_by_reason`
        # keys (per-year `filtered_explicit` defaults to 0).
        manifest.record_bronze(2020, 100)
        manifest.record_gold_from_dataframe(pl.DataFrame({"year": [2020] * 90}))
        rc = manifest.to_dict()["row_counts"]
        assert "total_filtered_explicit" not in rc
        assert "filtered_explicit_by_reason" not in rc
        assert rc["by_year"]["2020"]["filtered_explicit"] == 0

    def test_write_creates_json(self, manifest: TransformManifest, tmp_path: Path):
        manifest.record_bronze(2020, 50)
        df = pl.DataFrame({"year": [2020] * 50})
        manifest.record_gold_from_dataframe(df)

        gold_dir = tmp_path / "gold"
        gold_dir.mkdir()
        result_path = manifest.write(gold_dir)

        assert result_path == gold_dir / "_transform_manifest.json"
        assert result_path.exists()

        data = json.loads(result_path.read_text())
        assert data["topic"] == "test_topic"
        assert data["row_counts"]["total_bronze"] == 50

    def test_write_creates_directory_if_needed(
        self, manifest: TransformManifest, tmp_path: Path
    ):
        gold_dir = tmp_path / "new" / "nested" / "dir"
        result_path = manifest.write(gold_dir)
        assert result_path.exists()

    def test_write_raises_on_unmapped_categoricals(
        self, manifest: TransformManifest, tmp_path: Path
    ):
        manifest.record_categorical(
            "subject",
            {"Math": "math"},
            pl.Series("r", ["Math", "Unknown"]),
            pl.Series("m", ["math", "99999999"]),
        )
        gold_dir = tmp_path / "gold"
        with pytest.raises(ValueError, match="unmapped categorical"):
            manifest.write(gold_dir)
        # Manifest is written before the raise so the user can inspect it.
        assert (gold_dir / "_transform_manifest.json").exists()

    def test_write_allows_unmapped_when_strict_disabled(
        self, manifest: TransformManifest, tmp_path: Path
    ):
        manifest.record_categorical(
            "subject",
            {"Math": "math"},
            pl.Series("r", ["Math", "Unknown"]),
            pl.Series("m", ["math", "99999999"]),
        )
        gold_dir = tmp_path / "gold"
        # Should not raise when strict_unmapped=False.
        result = manifest.write(gold_dir, strict_unmapped=False)
        assert result.exists()

    def test_roundtrip_json_is_valid(self, manifest: TransformManifest, tmp_path: Path):
        """Verify the manifest JSON can be read back and has expected types."""
        manifest.record_file(tmp_path / "f.csv", 2020, "era_1", 200, ["A"])
        manifest.record_bronze(2020, 200)
        manifest.record_categorical(
            "subject",
            {"Math": "math", "Science": "science"},
            pl.Series("r", ["Math", "Science", "Math"]),
            pl.Series("m", ["math", "science", "math"]),
        )
        # Final DataFrame has 180 rows — 20 were dropped during transform.
        df = pl.DataFrame(
            {
                "year": [2020] * 180,
                "score": [10.0] * 90 + [20.0] * 90,
            }
        )
        manifest.record_gold_from_dataframe(df)
        manifest.compute_metric_stats(df, ["score"])

        gold_dir = tmp_path / "gold"
        manifest.write(gold_dir)

        # Read it back
        data = json.loads((gold_dir / "_transform_manifest.json").read_text())

        # Verify key structural properties
        assert isinstance(data["generated_at"], str)
        assert isinstance(data["files_processed"], list)
        assert isinstance(data["row_counts"]["by_year"], dict)
        assert isinstance(data["categorical_mappings"]["subject"]["map_used"], dict)
        assert isinstance(data["metric_stats"]["score"]["2020"]["min_val"], float)
        # Derived filtered count (bronze - gold).
        assert data["row_counts"]["total_filtered"] == 20
