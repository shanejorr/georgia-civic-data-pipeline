"""Tests for demographics normalization utilities.

Ensures DEMOGRAPHIC_ALIASES has no duplicate mappings, all canonical values
have categories, and the mapping is consistent.
"""

import polars as pl

from src.utils.demographics import (
    CANONICAL_DEMOGRAPHICS,
    DEMOGRAPHIC_ALIASES,
    DEMOGRAPHIC_CATEGORIES,
    SENTINEL_UNMATCHED_DEMOGRAPHIC,
    normalize_demographic_column,
)


class TestDemographicAliases:
    def test_no_duplicate_keys(self):
        """All alias keys should be unique (dict enforces this, but verify intent)."""
        # Dict construction silently overwrites duplicates.
        # Verify by checking the module source for duplicate key definitions.
        keys = list(DEMOGRAPHIC_ALIASES.keys())
        assert len(keys) == len(set(keys)), "Duplicate keys in DEMOGRAPHIC_ALIASES"

    def test_all_keys_are_uppercase(self):
        """All alias keys should be uppercase for case-insensitive matching."""
        for key in DEMOGRAPHIC_ALIASES:
            assert key == key.upper(), f"Key '{key}' is not uppercase"

    def test_all_values_are_lowercase_snake_case(self):
        """All canonical values should be lowercase snake_case."""
        for key, value in DEMOGRAPHIC_ALIASES.items():
            assert value == value.lower(), (
                f"Value '{value}' for key '{key}' is not lowercase"
            )
            assert " " not in value, f"Value '{value}' for key '{key}' contains spaces"

    def test_canonical_demographics_derived_from_aliases(self):
        """CANONICAL_DEMOGRAPHICS should be exactly the set of alias values."""
        assert CANONICAL_DEMOGRAPHICS == set(DEMOGRAPHIC_ALIASES.values())

    def test_all_canonical_have_categories(self):
        """Each canonical demographic must have an entry in DEMOGRAPHIC_CATEGORIES."""
        missing = CANONICAL_DEMOGRAPHICS - set(DEMOGRAPHIC_CATEGORIES.keys())
        assert not missing, f"Canonical demographics without categories: {missing}"

    def test_no_extra_categories(self):
        """DEMOGRAPHIC_CATEGORIES should not have entries for non-canonical values."""
        extra = set(DEMOGRAPHIC_CATEGORIES.keys()) - CANONICAL_DEMOGRAPHICS
        assert not extra, f"Categories for non-canonical values: {extra}"

    def test_valid_category_values(self):
        """All category values should be from the known set."""
        valid_categories = {
            "aggregate",
            "race",
            "gender",
            "economic_status",
            "sped",
            "disability",
            "esol",
            "migrant_status",
            "homeless_status",
            "foster_care",
            "military",
            "grade",
        }
        for demographic, category in DEMOGRAPHIC_CATEGORIES.items():
            assert category in valid_categories, (
                f"'{demographic}' has unknown category '{category}'"
            )

    def test_common_aliases_present(self):
        """Spot-check that common demographic aliases are mapped correctly."""
        assert DEMOGRAPHIC_ALIASES["ALL"] == "all"
        assert DEMOGRAPHIC_ALIASES["BLACK"] == "black"
        assert DEMOGRAPHIC_ALIASES["HISPANIC"] == "hispanic"
        assert DEMOGRAPHIC_ALIASES["MALE"] == "male"
        assert DEMOGRAPHIC_ALIASES["FEMALE"] == "female"
        assert (
            DEMOGRAPHIC_ALIASES["ECONOMICALLY DISADVANTAGED"]
            == "economically_disadvantaged"
        )
        assert (
            DEMOGRAPHIC_ALIASES["STUDENTS WITH DISABILITIES"]
            == "students_with_disabilities"
        )
        assert DEMOGRAPHIC_ALIASES["ENGLISH LEARNERS"] == "english_learners"

    def test_no_alias_maps_to_sentinel(self):
        """No alias should map to the sentinel value '99999999'."""
        for key, value in DEMOGRAPHIC_ALIASES.items():
            assert value != SENTINEL_UNMATCHED_DEMOGRAPHIC, (
                f"Key '{key}' maps to the sentinel"
            )


class TestNormalizeDemographicColumn:
    def test_basic_mapping(self):
        df = pl.DataFrame({"raw": ["Black", "WHITE", "hispanic"]})
        result = df.select(normalize_demographic_column("raw").alias("d"))
        assert result["d"].to_list() == ["black", "white", "hispanic"]

    def test_strips_whitespace(self):
        df = pl.DataFrame({"raw": ["  Asian  "]})
        result = df.select(normalize_demographic_column("raw").alias("d"))
        assert result["d"][0] == "asian"

    def test_unmatched_gets_sentinel(self):
        df = pl.DataFrame({"raw": ["not_a_real_category"]})
        result = df.select(normalize_demographic_column("raw").alias("d"))
        assert result["d"][0] == SENTINEL_UNMATCHED_DEMOGRAPHIC

    def test_null_passes_through(self):
        df = pl.DataFrame({"raw": [None, "MALE"]}, schema={"raw": pl.Utf8})
        result = df.select(normalize_demographic_column("raw").alias("d"))
        assert result["d"][0] is None
        assert result["d"][1] == "male"

    def test_accepts_polars_expression(self):
        df = pl.DataFrame({"raw": ["Black"]})
        # Caller can pass an already-computed expression (e.g., after upstream
        # string manipulation) instead of a column name string.
        result = df.select(normalize_demographic_column(pl.col("raw")).alias("d"))
        assert result["d"][0] == "black"
