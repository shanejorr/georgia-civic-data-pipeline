"""Tests for src/utils/metadata.py data-dictionary generation.

Focus: the categorical auto-fill (`_fill_categorical_valid_values`) populates
`validValues` for hand-authored categorical columns that lack them — sourcing
observed values from the exported gold parquet — reusing the same
categorical-detection logic as the DataFrame-inference path, while leaving
non-categorical and high-cardinality columns untouched. These `validValues`
become the contract's `enum` when `write_data_dictionary` emits the ODCS
contract (there is no longer a `_metadata.json`), so the auto-fill is verified
directly on the column declaration the emitter consumes.
"""

import polars as pl
import pytest

from src.utils.metadata import (
    CATEGORICAL_MAX_UNIQUE,
    IDENTIFIER_COLUMNS,
    KNOWN_CATEGORICAL_COLUMNS,
    _fill_categorical_valid_values,
    infer_columns_from_dataframe,
    infer_valid_values,
)


def _write_gold_parquet(gold_dir, df: pl.DataFrame) -> None:
    """Write a gold parquet under a year partition, mimicking a real topic."""
    part = gold_dir / "year=2024"
    part.mkdir(parents=True, exist_ok=True)
    df.write_parquet(part / "states.parquet")


def test_infer_valid_values_categorical():
    """A low-cardinality string column yields sorted distinct non-null values."""
    s = pl.Series("demographic", ["white", "black", "all", "white", None])
    assert infer_valid_values(s, "demographic") == ["all", "black", "white"]


def test_infer_valid_values_high_cardinality_returns_none():
    """An UNKNOWN string column above the cardinality fallback returns None."""
    values = [f"code_{i}" for i in range(CATEGORICAL_MAX_UNIQUE + 1)]
    s = pl.Series("some_freeform_code", values)
    assert infer_valid_values(s, "some_freeform_code") is None


def test_infer_valid_values_non_string_returns_none():
    """Numeric columns are never categorical."""
    s = pl.Series("student_count", [1, 2, 3, 4])
    assert infer_valid_values(s, "student_count") is None


def test_known_categorical_bypasses_cardinality_cap():
    """A column named in the allowlist is categorical regardless of cardinality.

    `subject` reaches 42 distinct AP courses — well past the cardinality cap —
    but is enumerated because it is a known categorical, not by hitting a
    threshold.
    """
    assert "subject" in KNOWN_CATEGORICAL_COLUMNS
    wide_subject = [f"subject_{i}" for i in range(CATEGORICAL_MAX_UNIQUE + 25)]
    result = infer_valid_values(pl.Series("subject", wide_subject), "subject")
    assert result is not None
    assert len(result) == CATEGORICAL_MAX_UNIQUE + 25

    # A wide demographic enumeration (race+gender+grade+status, ~28 values) is
    # likewise covered by name, not by an inflated threshold.
    wide_demographic = [f"demo_{i}" for i in range(28)]
    assert (
        infer_valid_values(pl.Series("demographic", wide_demographic), "demographic")
        is not None
    )


def test_identifier_columns_never_categorical():
    """Identifier columns are excluded even when a slice has few distinct values."""
    assert "district_code" in IDENTIFIER_COLUMNS
    s = pl.Series("district_code", ["601", "602", "603"])  # only 3 distinct
    assert infer_valid_values(s, "district_code") is None
    school = pl.Series("school_code", ["0101", "0102"])
    assert infer_valid_values(school, "school_code") is None


def test_unknown_column_uses_cardinality_fallback():
    """A column not in the allowlist falls back to the cardinality cap."""
    # At the cap -> categorical; over the cap -> None (unknown column name).
    small = [f"v{i}" for i in range(CATEGORICAL_MAX_UNIQUE)]
    assert infer_valid_values(pl.Series("mystery", small), "mystery") is not None
    big = [f"v{i}" for i in range(CATEGORICAL_MAX_UNIQUE + 1)]
    assert infer_valid_values(pl.Series("mystery", big), "mystery") is None


def test_fill_categorical_valid_values_from_gold(tmp_path):
    """A hand-authored categorical column with no validValues gets them filled
    from observed gold values; a high-cardinality column does NOT.

    These filled `validValues` become the contract's `enum` at emit time.
    """
    gold_dir = tmp_path / "gold_topic"
    df = pl.DataFrame(
        {
            "year": [2024, 2024, 2024],
            # low-cardinality categorical, hand-authored without validValues
            "demographic": ["all", "white", "black"],
            # high-cardinality string -> must NOT get validValues
            "district_code": [f"d{i:03d}" for i in range(3)],
            # numeric metric -> must NOT get validValues
            "student_count": [10, 20, 30],
        }
    )
    # Make district_code genuinely high-cardinality (> threshold) by expanding.
    big = pl.DataFrame(
        {
            "year": [2024] * (CATEGORICAL_MAX_UNIQUE + 5),
            "demographic": ["all"] * (CATEGORICAL_MAX_UNIQUE + 5),
            "district_code": [f"d{i:03d}" for i in range(CATEGORICAL_MAX_UNIQUE + 5)],
            "student_count": list(range(CATEGORICAL_MAX_UNIQUE + 5)),
        }
    )
    df = pl.concat([df, big])
    _write_gold_parquet(gold_dir, df)

    columns = [
        {"name": "year", "type": "int32", "description": "Ending year."},
        {
            "name": "demographic",
            "type": "string",
            "description": "Canonical demographic code.",
        },
        {
            "name": "district_code",
            "type": "string",
            "description": "GOSA district code.",
        },
        {
            "name": "student_count",
            "type": "int64",
            "description": "Student count.",
        },
    ]

    filled = _fill_categorical_valid_values(columns, gold_dir)
    by_name = {c["name"]: c for c in filled}

    # Categorical column got validValues from observed gold values.
    assert by_name["demographic"].get("validValues") == ["all", "black", "white"]
    # High-cardinality and numeric columns left untouched.
    assert "validValues" not in by_name["district_code"]
    assert "validValues" not in by_name["student_count"]
    # year (numeric) untouched too.
    assert "validValues" not in by_name["year"]


def test_fill_categorical_preserves_existing_valid_values(tmp_path):
    """A hand-authored validValues array is preserved, not overwritten by
    observed gold values."""
    gold_dir = tmp_path / "gold_topic2"
    df = pl.DataFrame(
        {
            "year": [2024, 2024],
            "flag": ["green", "red"],
        }
    )
    _write_gold_parquet(gold_dir, df)

    hand_authored = ["green", "green_star", "red", "yellow"]
    columns = [
        {"name": "year", "type": "int32", "description": "Year."},
        {
            "name": "flag",
            "type": "string",
            "description": "CCRPI color flag.",
            # explicit allowed domain, broader than observed gold values
            "validValues": list(hand_authored),
        },
    ]

    filled = _fill_categorical_valid_values(columns, gold_dir)
    by_name = {c["name"]: c for c in filled}
    assert by_name["flag"]["validValues"] == hand_authored


def test_fill_categorical_no_parquet_is_additive(tmp_path):
    """When no gold parquet exists, columns are left exactly as authored."""
    gold_dir = tmp_path / "empty_topic"
    gold_dir.mkdir(parents=True, exist_ok=True)
    columns = [
        {"name": "year", "type": "int32", "description": "Year."},
        {"name": "demographic", "type": "string", "description": "Demo."},
    ]
    filled = _fill_categorical_valid_values(columns, gold_dir)
    by_name = {c["name"]: c for c in filled}
    assert "validValues" not in by_name["demographic"]


def test_infer_columns_from_dataframe_uses_shared_logic():
    """The DataFrame-inference path uses the same categorical detection."""
    df = pl.DataFrame(
        {
            "demographic": ["all", "white", "black"],
            "district_code": [f"d{i:03d}" for i in range(3)],
        }
    )
    cols = {c["name"]: c for c in infer_columns_from_dataframe(df)}
    assert cols["demographic"]["validValues"] == ["all", "black", "white"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
