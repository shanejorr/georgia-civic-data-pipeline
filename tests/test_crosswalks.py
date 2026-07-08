"""Tests for crosswalk utilities.

Focuses on the vectorized Polars-expression helpers that don't require the
full crosswalk parquet to be present.
"""

import polars as pl

from src.utils.crosswalks import (
    normalize_district_name,
    normalize_district_name_expr,
)


class TestNormalizeDistrictNameScalar:
    def test_strips_school_district_suffix(self):
        assert normalize_district_name("Appling County School District") == (
            "appling county"
        )

    def test_public_schools_suffix_stripped(self):
        # " public schools" is stripped first by suffix matching; the
        # "X public" -> "X city" rule only kicks in when the prior suffix is
        # " schools" alone. The final city-suffix is added by
        # DISTRICT_NAME_OVERRIDES at a later step.
        assert normalize_district_name("Dalton Public Schools") == "dalton"

    def test_public_trailing_rewrites_to_city(self):
        # Direct test of the "X public" -> "X city" branch when " schools"
        # was the matched suffix.
        assert normalize_district_name("Dalton Public") == "dalton city"

    def test_empty_string(self):
        assert normalize_district_name("") == ""


class TestNormalizeDistrictNameExpr:
    def test_matches_scalar_on_canonical_cases(self):
        # The vectorized form must match the scalar form on the main cases.
        inputs = [
            "Appling County School District",
            "Fulton County School District",
            "Atlanta Public Schools",
            "Dalton Public Schools",
            "Thomas County Schools",
            "Clarke County",
        ]
        expected = [normalize_district_name(x) for x in inputs]

        df = pl.DataFrame({"name": inputs})
        result = df.select(normalize_district_name_expr("name").alias("n"))
        assert result["n"].to_list() == expected

    def test_collapses_internal_whitespace(self):
        df = pl.DataFrame({"name": ["  Appling   County  "]})
        result = df.select(normalize_district_name_expr("name").alias("n"))
        assert result["n"][0] == "appling county"

    def test_null_passes_through(self):
        df = pl.DataFrame({"name": [None]}, schema={"name": pl.Utf8})
        result = df.select(normalize_district_name_expr("name").alias("n"))
        assert result["n"][0] is None
