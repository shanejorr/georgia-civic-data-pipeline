"""Tests for the canonical column vocabulary registry (§16, machine-readable)."""

from src.utils.vocabulary import vocabulary_violations


class TestVocabularyViolations:
    def test_flags_exact_variants(self):
        hits = dict(vocabulary_violations(["number_tested", "grade", "flag"]))
        assert hits == {
            "number_tested": "num_tested",
            "grade": "grade_level",
            "flag": "ccrpi_flag",
        }

    def test_flags_and_above_suffix_mechanically(self):
        hits = dict(vocabulary_violations(["pct_proficient_learner_and_above"]))
        assert hits == {
            "pct_proficient_learner_and_above": "pct_proficient_learner_or_above"
        }

    def test_flags_rate_pct_suffix_mechanically(self):
        hits = dict(vocabulary_violations(["completion_rate_pct"]))
        assert hits == {"completion_rate_pct": "completion_rate"}

    def test_flags_share_suffix_with_guidance(self):
        hits = dict(vocabulary_violations(["enrollment_share"]))
        assert hits == {"enrollment_share": "pct_of_<denominator>"}

    def test_sanctioned_average_daily_columns_pass(self):
        # "Average Daily Attendance" is a term of art — sanctioned exception.
        assert (
            vocabulary_violations(
                ["average_daily_attendance_rate", "average_daily_absenteeism_rate"]
            )
            == []
        )

    def test_canonical_columns_pass(self):
        canonical = [
            "year",
            "district_code",
            "school_code",
            "demographic",
            "num_tested",
            "num_students",
            "num_graduates",
            "num_cohort",
            "grade_level",
            "subject",
            "test_component",
            "ccrpi_flag",
            "indicator_target",
            "indicator_score",
            "graduation_rate",
            "pct_proficient_learner_or_above",
            "pct_of_enrollment",
        ]
        assert vocabulary_violations(canonical) == []

    def test_no_substring_matching(self):
        # Exact-name rules only: a column merely containing "grade" or "flag"
        # is not a violation.
        assert vocabulary_violations(["grade_cluster", "red_flag_count"]) == []
