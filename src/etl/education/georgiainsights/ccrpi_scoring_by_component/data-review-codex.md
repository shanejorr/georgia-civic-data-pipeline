# Data Review: ccrpi_scoring_by_component

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: bronze, transform, contract, validator, and gold reconcile; no must-fix accuracy defects were found.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - transform mtime 2026-06-12T15:56:46.708875+00:00, manifest generated_at 2026-06-12T15:56:58.108482+00:00, validation timestamp 2026-06-12T15:56:58.193743+00:00; validation passed and is newer than the manifest.

## Files Reviewed

- Transform: `src/etl/education/georgiainsights/ccrpi_scoring_by_component/transform.py`
- Contract: `contracts/education/ccrpi_scoring_by_component.odcs.yaml`
- Bronze files: 12 Excel files, 2012-2019 and 2022-2025; all current SHA-256 checksums match `bronze-data-structure.md`.
- Gold files: 36 parquet files, `year={2012-2019,2022-2025}/{schools,districts,states}.parquet`.
- Manifest: `data/gold/education/ccrpi_scoring_by_component/_transform_manifest.json`
- Validation report: `data/gold/education/ccrpi_scoring_by_component/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, data-cleaning standards, education `CLAUDE.md`, bronze structure report, relevant shared utils.

## Contract Verification

- Schema/parquet column match: PASS - contract properties match the actual parquet column names and order: `year`, `district_code`, `school_code`, `grade_cluster`, then 13 metric columns.
- Column roles and grain: PASS - `year`, district/school FKs, `grade_cluster` categorical, and metric roles agree with transform output; grain is `year, district_code, school_code, grade_cluster`.
- Metric units and derived quality checks: PASS - score/rate units are coherent; 0-100 component scores carry range checks, `graduation_rate` is `unit: proportion`, and bonus-bearing aggregate scores intentionally have no max bound.
- Categorical enums: PASS - `grade_cluster` enum is `elementary`, `high`, `middle`, matching manifest and gold distinct values.
- Detail levels and layout metadata: PASS - `schools`, `districts`, and `states` detail files exist for every reported year, with year partitioning and local/S3 path templates.
- Foreign-key descriptors: PASS - `district_code` and composite `district_code, school_code` school FK descriptors match the dimensions model.
- Schema hash/version consistency: PASS - version is `1.0.0`; schema hash is present and validation confirms contract/parquet consistency.

## Validator Verification

- `_validation.json` fresh + passing: PASS - `passed: true`; timestamp is newer than manifest.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 20 pass, 0 fail; schema, data types, grain uniqueness, 14 contract quality checks, canonical vocabulary, geography nulling, and FKs all passed.
- Validator warnings explained: PASS - null-rate spikes on `ccrpi_score` and `ccrpi_single_score` in 2022-2025 are source-expected: 2022 COVID blackout and 2023+ source columns dropped.
- §15b quality-check coverage (cross-column invariants authored): PASS - quality checks cover era-scoped null structure, 2022 blackout, points-era component sum, points-era co-null trio, and graduation-rate high-cluster-only structure.

## Manifest Verification

- Files processed coverage: PASS - all 12 current bronze files appear in `files_processed` with expected years and eras.
- Categorical and recode coverage: PASS - only `grade_cluster` is recoded; `E/M/H` map to `elementary/middle/high`, `unmapped_count` is 0, and gold values match the contract enum.
- Row-count reconciliation: PASS - manifest records 37,279 bronze rows and 37,279 gold rows, no filters, expansion factor 1.0 for every year.
- Metric stats sanity: PASS - score-era component ranges are within 0-100, points metrics are non-negative and era-scoped, `graduation_rate` is within 0-1 after scaling, and aggregate scores over 100 are documented bonus-score overshoot.

## Row and Join Accounting

- Bronze file/year disposition: PASS - every profiled bronze file is processed once; 2020 and 2021 are absent by source/COVID pause and are not synthesized.
- Filter accounting: N/A - transform records no filters; every bronze row lands in gold.
- Join accounting: N/A - no transform-time joins are used. FK validation against dimensions passes with 246 district keys and 2,576 school keys resolved.
- Deduplication accounting: PASS - sampled per-file duplicate checks found 0 duplicate natural keys; combined gold has 0 duplicate `year, district_code, school_code, grade_cluster` keys, and defensive dedup removed no rows.
- Aggregation/unpivot accounting: N/A - no source rows are aggregated or unpivoted; this is a row-preserving harmonization.

## Reconciliation Checks

- Artifact freshness: PASS - transform, manifest, validation, contract, bronze checksums, and gold layout are current and mutually consistent.
- Contract freshness: PASS - contract is emitted from the transform and matches current parquet; no `_metadata.json` dependency.
- Year coverage: PASS - gold years are 2012-2019 and 2022-2025, matching bronze and contract `available_years`; 2020-2021 are gaps.
- Row preservation: PASS - 37,279 in, 37,279 out; detail rows total 29,757 schools, 7,486 districts, 36 states.
- Column coverage: PASS - fact keys, `grade_cluster`, all points-era metrics, score-era metrics, and aggregate scores have lineage from bronze columns or documented structural nulls.
- Recode accuracy: PASS - header canonicalization covers casing, trailing whitespace, and embedded newline drift; `grade_cluster` recode is semantically correct.
- Asian-family demographic recodes (§5b): N/A - no demographic or race columns.
- Demographic mutual exclusivity (§5a - no rollup row alongside split source rows in the same category): N/A - no demographic column.
- Demographic collision aggregation before dedup (§5): N/A - no demographic column.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS - parquet starts with `year`, `district_code`, `school_code`, then categorical `grade_cluster`, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS - parquet contains no name columns, no `topic`, no `detail_level`, and no crosswalk IDs.
- Canonical column vocabulary (§16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - validation reports no vocabulary violations; CCRPI-specific names are descriptive and contract-documented.
- Shared categorical utilities applied (§10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no `grade_level` or `subject` column; `grade_cluster` is topic-specific.
- Tidy long format (§9 - no demographics/years/components as column names): PASS - the only categorical axis is `grade_cluster`; metric families are columns because they are distinct measures, not categorical levels.
- FK keys present in dimension tables (§13 - `district_code`, `school_code`, `demographic`): PASS - all populated district and composite school keys resolve; `RTC` rows resolve as district-level pseudo-district facts in 2015-2017.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - `grade_cluster` is the sole filterable categorical and FK joins are contract-described.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS - suppression markers are null, ID strings preserve leading zeros, aggregate sentinels are nulled, and percentage/rate scale is correct.

## Spot Checks

### Check 1

- Bronze: `2013 Scoring By Component for Public Release v2.xls`, Carrollton Elementary (`SYSTEM ID=766`, `SCHOOL ID=0193`, `GRADE CLUSTER=E`) has `ACHIEVEMENT POINTS=49.5`, `PROGRESS POINTS=NA`, `ACHIEVEMENT GAP POINTS=6`, `CHALLENGE POINTS=5`, `CCRPI SCORE=79`, `SINGLE SCORE=79`.
- Transform path: `_read_data_sheet()` nulls `NA`; `transform_file()` maps IDs, `E -> elementary`, casts metrics, and selects standard columns.
- Gold: `year=2013/schools.parquet` row `district_code=766`, `school_code=0193`, `grade_cluster=elementary` has `achievement_points=49.5`, `progress_points=NULL`, `achievement_gap_points=6.0`, `challenge_points=5.0`, `ccrpi_score=79.0`, `ccrpi_single_score=79.0`.
- Result: MATCH

### Check 2

- Bronze: `2019 CCRPI Scoring by Component_04_01_20.xls`, Cherokee High (`SYSTEM ID=628`, `SCHOOL ID=5050`, `GRADE CLUSTER=H`) has score-era values `Content Mastery=73.2`, `Progress=80.3`, `Closing Gaps=68.8`, `Readiness=72.5`, `Graduation Rate=81.3`, `CCRPI Score=76.0`, `Single Score=76.0`.
- Transform path: score-era metric map, Float64 casts, and `graduation_rate / 100.0`.
- Gold: `year=2019/schools.parquet` has `content_mastery=73.2`, `progress=80.3`, `closing_gaps=68.8`, `readiness=72.5`, `graduation_rate=0.813`, `ccrpi_score=76.0`, `ccrpi_single_score=76.0`.
- Result: MATCH

### Check 3

- Bronze: `2024 CCRPI Scoring by Component.xlsx`, Greenville High (`SYSTEM ID=699`, raw `SCHOOL ID=300`, `GRADE CLUSTER=H`) has `Content Mastery=36.1`, `Progress=39.1`, `Closing Gaps=100`, `Readiness=70.1`, `Graduation Rate=85`, and no aggregate score columns.
- Transform path: `_null_id_sentinels_and_format()` zero-pads `300 -> 0300`; era 4 omits aggregate score renames, leaving aggregate score columns structurally null after harmonization; `graduation_rate` is divided by 100.
- Gold: `year=2024/schools.parquet` row `district_code=699`, `school_code=0300`, `grade_cluster=high` has matching score metrics, `graduation_rate=0.85`, and `ccrpi_score=NULL`, `ccrpi_single_score=NULL`.
- Result: MATCH

### Check 4

- Bronze: `2015 CCRPI Scoring By Component 07.14.16.xlsx` has three RTC rows with `SYSTEM ID=RTC`, `SCHOOL ID=ALL`, `SCHOOL NAME=All RTC Schools`, one per grade cluster; elementary row has `CCRPI SCORE=39.1`.
- Transform path: detail derivation treats `SCHOOL ID=ALL` with real district code `RTC` as district-level, then nulls school sentinel; `RTC` is preserved as an allowlisted pseudo-district.
- Gold: `year=2015/districts.parquet` has `district_code=RTC`, `school_code=NULL`, `grade_cluster=elementary`, `ccrpi_score=39.1`; total RTC gold rows are three each in 2015, 2016, and 2017.
- Result: MATCH

### Check 5

- Bronze: `2022 CCRPI Scoring by Component 11.16.22.xlsx`, state high-cluster row has `Content Mastery=64.7`, `Progress=NA`, `Closing Gaps=NA`, `Readiness=73.2`, `Graduation Rate=84.7`, `CCRPI Score=NA`, `Single Score=NA`.
- Transform path: 2022 disclaimer row is detected by missing key columns and re-read with header row 1; suppression values become null; `graduation_rate` is divided by 100.
- Gold: `year=2022/states.parquet` high row has content/readiness populated, progress/closing gaps/aggregate scores null, and graduation rate scaled to 0.847.
- Result: MATCH

### Check 6

- Bronze: points-era component identity is directly preserved. A 2016 complete row in gold has `achievement_points=30.0`, `progress_points=33.8`, `achievement_gap_points=6.7`, `challenge_points=1.2`; the recomputed sum is `71.7`, matching `ccrpi_score=71.7`.
- Transform path: points metrics are cast from source columns without aggregation; contract quality check `points_era_components_sum_to_ccrpi_score` enforces the identity.
- Gold: all points-era rows with complete component values have 0 component-sum violations under the authored 0.05 tolerance.
- Result: MATCH

## Notes

- I did not read any prior Claude or Codex review report before completing this review.
- Existing worktree changes outside this report were left untouched.
- No required fixes are present.
