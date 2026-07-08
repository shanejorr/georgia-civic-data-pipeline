"""Unit tests for the total/"all" sentinel detector (``src.utils.sentinels``).

Mirrors the dashboard's ``sentinel.test.ts`` cases so the two implementations stay
in lockstep — in particular the whole-token rule (no substring matches).
"""

from __future__ import annotations

from src.utils.sentinels import find_sentinel


def test_prefers_exact_all():
    assert find_sentinel(["black", "all", "hispanic"]) == "all"
    # Case-insensitive, original case preserved.
    assert find_sentinel(["Black", "All"]) == "All"


def test_other_sentinel_tokens():
    assert find_sentinel(["math", "english", "composite", "overall"]) == "overall"
    assert find_sentinel(["k12", "total"]) == "total"
    assert find_sentinel(["statewide", "region_a"]) == "statewide"


def test_no_sentinel_returns_none():
    assert find_sentinel(["composite", "english", "math"]) is None
    assert find_sentinel(["k", "1", "2", "3"]) is None


def test_whole_token_only_no_substring():
    # "combined_english_writing" must NOT match the "combined" token.
    assert find_sentinel(["combined_english_writing", "math"]) is None


def test_empty_and_none():
    assert find_sentinel(None) is None
    assert find_sentinel([]) is None
