# Data Review: georgia_milestones_end_of_course_eoc_lexile_scores

## Verdict

**Status**: NEEDS FIXES
**Must-fix count**: 1

Summary: Bronze-to-gold row coverage and metric values match, but the transform-emitted contract misstates NULL semantics by describing pre-2021 blank source cells as only TFS suppression.

## Summary

- Review date: 2026-06-11
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - transform mtime 2026-06-12T00:06:15Z precedes manifest generated_at 2026-06-12T00:06:28Z, validation timestamp 2026-06-12T00:06:28Z is newer than the manifest, and `scripts/check_bronze_freshness.py` passed for all 9 bronze files.

## Files Reviewed

- Transform: `src/etl/education/gosa/georgia_milestones_end_of_course_eoc_lexile_scores/transform.py`
- Contract: `contracts/education/georgia_milestones_end_of_course_eoc_lexile_scores.odcs.yaml`
- Bronze files: 9 CSV files for 2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, and 2024 under `data/bronze/education/gosa/georgia_milestones_end_of_course_eoc_lexile_scores/`
- Gold files: 27 Parquet files under `data/gold/education/georgia_milestones_end_of_course_eoc_lexile_scores/year=*/{schools,districts,states}.parquet`
- Manifest: `data/gold/education/georgia_milestones_end_of_course_eoc_lexile_scores/_transform_manifest.json`
- Validation report: `data/gold/education/georgia_milestones_end_of_course_eoc_lexile_scores/_validation.json`
- Supporting docs: `docs/codex-review-contract.md`, `docs/contract-creation.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `src/etl/education/CLAUDE.md`, and the topic `bronze-data-structure.md`

## Contract Verification

- Schema/parquet column match: PASS - contract properties exactly match every parquet file: `year`, `district_code`, `school_code`, `subject`, `num_tested`, `num_with_lexile`, `num_without_lexile`, `num_at_or_above_lexile_midpoint`, `avg_lexile_score`.
- Column roles and grain: PASS - roles are `year`, `fk_district`, `fk_school`, `categorical`, and metric; contract grain is `year, district_code, school_code, subject`.
- Metric units and derived quality checks: PASS - count metrics use `unit: count`; `avg_lexile_score` uses `unit: score` with `[0, 2000]`; the contract has 13 SQL quality checks.
- Categorical enums: PASS - `subject` enum matches manifest and gold values: `9th_grade_literature_and_composition`, `american_literature_and_composition`.
- Detail levels and layout metadata: PASS - contract detail levels are `schools`, `districts`, `states`; gold has those files for all 9 years and no 2020 partition.
- Foreign-key descriptors: PASS - `district_code` targets districts and `school_code` targets the composite schools key; validator reports all 206 district keys and 763 school keys resolve.
- Schema hash/version consistency: PASS - contract version is `1.0.0`, schema_hash is present, available years match gold, and year gap is `[2020]`.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp `2026-06-12T00:06:28.818944+00:00` is newer than manifest `generated_at` and `"passed": true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 21 pass, 0 fail, 0 warning.
- Validator warnings explained: N/A - no warnings.
- Section 15b quality-check coverage (cross-column invariants authored): PASS - subset checks, co-null checks, and the 9th-grade post-2021 retirement invariant are authored and pass; the intentionally invalid `with + without = tested` identity is correctly not authored.

## Manifest Verification

- Files processed coverage: PASS - manifest lists all 9 current bronze CSVs with matching years, row counts, and one era.
- Categorical and recode coverage: PASS - `detail_level` and `subject` both have `unmapped_count: 0`; map entries are semantically correct.
- Row-count reconciliation: PASS - manifest total_bronze and total_gold are both 10,082, with 0 filtered rows and 1.0 expansion for every processed year.
- Metric stats sanity: PASS - metric ranges are non-negative; `avg_lexile_score` range is 707.0 to 1679.3; null rates match the source blanks/TFS pattern. The source of NULLs is misdescribed in contract text; see Fix 1.

## Row and Join Accounting

- Bronze file/year disposition: PASS - all 9 bronze files are processed; 2020 is absent from bronze and gold by source rule.
- Filter accounting: N/A - no rows are filtered; row preservation is 1:1.
- Join accounting: N/A - the transform performs no data joins or lookup joins; FK joins are validator-checked against dimensions.
- Deduplication accounting: PASS - no duplicate natural keys exist before or after export; defensive dedup does not change row counts.
- Aggregation/unpivot accounting: N/A - bronze is already tidy long format; no aggregation, rollup, or unpivot changes row counts.

## Reconciliation Checks

- Artifact freshness: PASS - bronze checksums match the structure report; no unanalyzed bronze files; manifest and validation are current.
- Contract freshness: PASS - contract was emitted with the current transform/gold run and has no `_metadata.json` dependency.
- Year coverage: PASS - gold years are 2015-2019 and 2021-2024; 2020 is correctly absent.
- Row preservation: PASS - independent recomputation found 0 missing keys, 0 extra keys, and 10,082 null-safe key matches.
- Column coverage: PASS - every fact key, fact categorical, and fact metric from the bronze classification has a gold disposition; name columns are excluded as dimensions.
- Recode accuracy: PASS - `State/District/School Level` map to `state/district/school`, and the two EOC subject labels map to the contract enum values.
- Asian-family demographic recodes (Section 5b): N/A - no demographic or race fields exist.
- Demographic mutual exclusivity (Section 5a): N/A - no demographic column is emitted because all rows are implicitly all students.
- Demographic collision aggregation before dedup (Section 5): N/A - no demographic normalization or collisions.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, Section 1): PASS - actual parquet order is `year`, geography keys, `subject`, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, Sections 11/12): PASS - parquet files do not contain forbidden fact-table columns.
- Canonical column vocabulary (Section 16): PASS - `subject`, `num_tested`, `num_with_lexile`, `num_without_lexile`, `num_at_or_above_lexile_midpoint`, and `avg_lexile_score` follow the canonical vocabulary.
- Shared categorical utilities applied (Section 10a): PASS - `subject` uses topic map plus `apply_subject_normalization`; no `grade_level` column exists.
- Tidy long format (Section 9): PASS - subjects are row values, years are partitions/columns, and no category is encoded as metric columns.
- FK keys present in dimension tables (Section 13): PASS - validator reports all district and composite school keys resolve.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): FAIL - row grain and FK/filter semantics are correct, but per-metric `null_meaning`/notes say NULL means TFS suppression only while 2015-2019 blank source cells also become NULL.
- Standards compliance (catch-all for Sections 1-16): FAIL - values comply, but contract null semantics must be corrected to include blank source cells.

## Spot Checks

### Check 1

- Bronze: 2024 state American Literature row has `All/All`, `TOTAL_STUDENTS_TESTED=132865`, `STUDENTS_WITH_LEXILE=132835`, `LEXILE_ON_OR_ABOVE_MIDPOINT=69660`, `NO_LEXILE_SCORE=87`, `AVG_LEXILE_SCORE=1287.7`.
- Transform path: `_transform_era1`, lines 331-409; aggregate geography is nulled in `main`, lines 494-498.
- Gold: `year=2024/states.parquet` has `district_code=NULL`, `school_code=NULL`, `subject=american_literature_and_composition`, and the same five metric values.
- Result: MATCH

### Check 2

- Bronze: 2015 Richmond County Cross Creek High School row has `SCHOOL_DSTRCT_CD=721`, `INSTN_NUMBER=100`, American Literature, `317/317/TFS/179/1315.6`.
- Transform path: school code is zero-padded in `_transform_era1`, lines 348-361; metrics cast at lines 390-408.
- Gold: `year=2015/schools.parquet` has `district_code=721`, `school_code=0100`, `subject=american_literature_and_composition`, `num_tested=317`, `num_with_lexile=317`, `num_without_lexile=NULL`, `num_at_or_above_lexile_midpoint=179`, `avg_lexile_score=1315.6`.
- Result: MATCH

### Check 3

- Bronze: 2024 Baker County Learning Academy school row has `TFS` in all five metric fields.
- Transform path: `read_bronze_file` plus `strict=False` metric casts in `_transform_era1`, lines 388-408.
- Gold: `year=2024/schools.parquet` has `district_code=604`, `school_code=0183`, American Literature, and all five metric columns NULL.
- Result: MATCH

### Check 4

- Bronze: 2015 Polk County Harpst Academy `INSTN_NUMBER=207`, 9th Grade Literature row has `TOTAL_STUDENTS_TESTED=10` with Lexile population, midpoint, no-Lexile, and average fields blank/NULL.
- Transform path: school code padding and metric casts in `_transform_era1`, lines 348-408.
- Gold: `year=2015/schools.parquet` has `district_code=715`, `school_code=0207`, `subject=9th_grade_literature_and_composition`, `num_tested=10`, and the other four metrics NULL.
- Result: MATCH

### Check 5

- Bronze: 2021 state 9th Grade Literature row has `TOTAL_STUDENTS_TESTED=81`, `STUDENTS_WITH_LEXILE=81`, `LEXILE_ON_OR_ABOVE_MIDPOINT=59`, `NO_LEXILE_SCORE=TFS`, `AVG_LEXILE_SCORE=1299.4`.
- Transform path: subject map and metrics in `_transform_era1`, lines 365-408.
- Gold: `year=2021/states.parquet` has null geography, `subject=9th_grade_literature_and_composition`, `num_tested=81`, `num_with_lexile=81`, `num_without_lexile=NULL`, `num_at_or_above_lexile_midpoint=59`, `avg_lexile_score=1299.4`.
- Result: MATCH

## Notes

- Independent recomputation from all bronze CSVs produced 0 missing gold keys, 0 extra gold keys, and 0 mismatches across all five metric columns after null-safe key comparison.
- No value-level data loss, row multiplication, recode failure, FK failure, or metric-scale issue was found.

## Required Fixes

### Fix 1: Correct NULL semantics for pre-2021 blank metric cells

- **Severity**: MEDIUM
- **Issue**: The transform-emitted contract and notes say metric NULLs are TFS suppression only, but actual 2015-2019 bronze uses blank metric cells that also become NULL in gold. The gold values are preserved correctly, but the contract/API metadata gives users the wrong null meaning for a large subset of NULLs.
- **Evidence**: Current bronze has 419 all-blank metric rows in 2015-2019 (`82, 77, 84, 87, 89` by year). For `TOTAL_STUDENTS_TESTED`, 2015-2019 have `0` TFS cells but `419` blank cells; 2021-2024 use TFS. Example: bronze `georgia_milestones_end_of_course_eoc_lexile_scores_2015.csv` Polk County Harpst Academy, `INSTN_NUMBER=207`, American Literature row has all five metric cells blank, and gold `year=2015/schools.parquet` row `district_code=715`, `school_code=0207`, `subject=american_literature_and_composition` has all five metrics NULL. Transform lines 613-703 and 732-736 describe NULLs as TFS/suppression only.
- **Location**: `src/etl/education/gosa/georgia_milestones_end_of_course_eoc_lexile_scores/transform.py:79`, `src/etl/education/gosa/georgia_milestones_end_of_course_eoc_lexile_scores/transform.py:388`, `src/etl/education/gosa/georgia_milestones_end_of_course_eoc_lexile_scores/transform.py:613`, `src/etl/education/gosa/georgia_milestones_end_of_course_eoc_lexile_scores/transform.py:625`, `src/etl/education/gosa/georgia_milestones_end_of_course_eoc_lexile_scores/transform.py:642`, `src/etl/education/gosa/georgia_milestones_end_of_course_eoc_lexile_scores/transform.py:664`, `src/etl/education/gosa/georgia_milestones_end_of_course_eoc_lexile_scores/transform.py:688`, `src/etl/education/gosa/georgia_milestones_end_of_course_eoc_lexile_scores/transform.py:732`
- **Suggested fix**: Update the transform docstring, metric comments, `null_meaning` strings, metric descriptions, and notes emitted by `write_data_dictionary()` to state that 2015-2019 blank source cells and 2021-2024 `TFS` source cells both become NULL. Do not change the metric casts or filter rows unless a separate source rule is established; the current bronze-to-gold values are correct.
