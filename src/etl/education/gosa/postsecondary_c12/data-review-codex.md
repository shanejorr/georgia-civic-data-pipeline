# Data Review: postsecondary_c12_report

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze inventory, transform logic, manifest, contract, validator report, and gold parquet reconcile; no required transform fixes were found.

## Summary

- Review date: 2026-06-11
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - `_validation.json` timestamp `2026-06-11T01:19:37.146852+00:00` is newer than manifest `generated_at` `2026-06-11T01:19:37.079865+00:00`; validation passed; bronze checksums match `bronze-data-structure.md`.

## Files Reviewed

- Transform: `src/etl/education/gosa/postsecondary_c12_report/transform.py`
- Contract: `contracts/education/postsecondary_c12_report.odcs.yaml`
- Bronze files: 13 files, `postsecondary_c_12_report_2012.xlsx` through `postsecondary_c_12_report_2024.csv`
- Gold files: 39 parquet files, `year=2008` through `year=2020`, each with `schools.parquet`, `districts.parquet`, and `states.parquet`
- Manifest: `data/gold/education/postsecondary_c12_report/_transform_manifest.json`
- Validation report: `data/gold/education/postsecondary_c12_report/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`, and relevant utility definitions in `src/utils/`.

## Contract Verification

- Schema/parquet column match: PASS - actual gold columns exactly match the contract order: `year`, `district_code`, `school_code`, `demographic`, `graduate_count`, `num_enrolled_in_college`, `num_earned_24_credits`.
- Column roles and grain: PASS - contract grain is `year`, `district_code`, `school_code`, `demographic`, matching the real natural key after detail-level geography nulling.
- Metric units and derived quality checks: PASS - all three metrics carry `unit: count`; contract quality includes non-negative checks plus subset-ordering and reporting-threshold checks.
- Categorical enums: PASS - contract enum equals actual gold demographic values: 14 canonical values, with no `asian_pacific_islander` rollup.
- Detail levels and layout metadata: PASS - contract lists `schools`, `districts`, `states`; gold has those three files for all 13 years.
- Foreign-key descriptors: PASS - contract describes district, composite school, and demographic FKs; validator and direct anti-joins found 0 unmatched keys.
- Schema hash/version consistency: PASS - version is `1.0.0`; schema hash is present; year range and available years are `2008-2020` with no gaps.

## Validator Verification

- `_validation.json` fresh + passing: PASS - timestamp `2026-06-11T01:19:37.146852+00:00`; manifest generated at `2026-06-11T01:19:37.079865+00:00`; `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - validation summary reports 21 pass, 0 fail, 0 warning; all 13 contract quality checks pass.
- Validator warnings explained: N/A - no warnings.
- Section 15b quality-check coverage (cross-column invariants authored): PASS - transform authors checks for metric subset ordering, published-count threshold, state core row completeness, exact state gender partition, race buckets not exceeding all-students totals, and no `pacific_islander` rows in 2008.

## Manifest Verification

- Files processed coverage: PASS - manifest processed all 13 current bronze files; current file inventory matches `files_processed`.
- Categorical and recode coverage: PASS - demographic `unmapped_count` is 0; manifest saw 27 raw labels/prefixes and produced the 14 canonical values expected by contract and gold.
- Row-count reconciliation: PASS - manifest `total_bronze` is 7,996 and `total_gold` is 111,370; actual parquet row counts match every manifest year. Expansion is 13x in 2008 and 14x thereafter, exactly matching the number of demographic blocks.
- Metric stats sanity: PASS - all non-null metric minimums are 10, maximums match state totals, no negative counts, and no ordering violations were found.

## Row and Join Accounting

- Bronze file/year disposition: PASS - 2012-2024 publication files map to cohort years 2008-2020 using `School Year` / `SCHOOL_YEAR`; filename year equals cohort year + 4.
- Filter accounting: N/A - no rows are filtered; manifest has no filtered section and `total_filtered` is 0.
- Join accounting: N/A - transform performs no joins. Dimension FK resolution is contract/validator-driven; direct checks found 0 missing district, school, or demographic keys.
- Deduplication accounting: PASS - pre-dedup duplicate natural-key groups were 0; dedup removed 0 rows.
- Aggregation/unpivot accounting: PASS - transform does not derive aggregates or rates; it preserves source state/district/school aggregate rows and only unpivots wide demographic blocks into long rows.

## Reconciliation Checks

- Artifact freshness: PASS - transform, manifest, contract, and validation artifacts were generated in the same run window; bronze checksums match the profiling report.
- Contract freshness: PASS - contract is emitted by `write_data_dictionary()` from the current transform; no `_metadata.json` dependency.
- Year coverage: PASS - gold years are exactly 2008-2020; all expected years have schools, districts, and states parquet files.
- Row preservation: PASS - file-level output matches expected unpivot expansion, and no dedup/filter loss occurred.
- Column coverage: PASS - all fact keys, the demographic axis, and the three count metrics from bronze are represented; district/school names and reporting year are correctly excluded.
- Recode accuracy: PASS - `Total All -> all`, `FRL/Free Reduced Lunch -> economically_disadvantaged`, `LEP -> english_learners`, `SWD/Disability -> students_with_disabilities`, race labels, and gender labels are semantically correct.
- Asian-family demographic recodes (section 5b): PASS - this is a split-convention topic. Gold emits `asian` and `pacific_islander`, emits 0 `asian_pacific_islander` rows, has 0 `pacific_islander` rows in 2008 because the source lacks that group, and state race sums equal the all-students graduate total in 2010-2016 and 2019-2020.
- Demographic mutual exclusivity (section 5a - no rollup row alongside split source rows in the same category): PASS - no combined Asian/Pacific Islander rollup is present alongside split rows; state race sums never exceed all-students totals.
- Demographic collision aggregation before dedup (section 5): N/A - observed demographic labels map one-to-one to canonical values; no collisions were present before dedup.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - actual parquet order is `year`, `district_code`, `school_code`, `demographic`, then the three metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, sections 11/12): PASS - parquet contains no forbidden columns; `detail_level` is only encoded in filenames.
- Canonical column vocabulary (section 16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - relevant metric names are canonical count names (`graduate_count`, `num_enrolled_in_college`, `num_earned_24_credits`); no prohibited variants.
- Shared categorical utilities applied (section 10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): PASS - demographic normalization uses `normalize_demographic_column`; no `grade_level` or `subject` column exists.
- Tidy long format (section 9 - no demographics/years/components as column names): PASS - gold stores one row per demographic with three metrics, not one metric column per subgroup.
- FK keys present in dimension tables (section 13 - `district_code`, `school_code`, `demographic`): PASS - direct dimension anti-joins found 0 unmatched districts, 0 unmatched composite school keys, and 0 unmatched demographics.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - contract grain and FK descriptors match actual parquet shape and validator behavior.
- Standards compliance (catch-all for sections 1-16 items not enumerated above): PASS - IDs are strings with padding preserved, counts are Int64, year is Int32, suppression markers become NULL, and state/district geography nulling matches domain rules.

## Spot Checks

### Check 1

- Bronze: `postsecondary_c_12_report_2012.xlsx`, Treutlen Middle/High School, `School Year=2008`, district `740`, school `3050`, `Total All` metrics: graduates `67`, enrolled `36`, earned 24 credits `28`.
- Transform path: `_stitch_xlsx()` and `_blocks_to_long()` at `src/etl/education/gosa/postsecondary_c12_report/transform.py:367` and `:450`; year and geography assignment at `:547` and `:651`.
- Gold: `year=2008`, `district_code=740`, `school_code=3050`, `demographic=all`, `graduate_count=67`, `num_enrolled_in_college=36`, `num_earned_24_credits=28`.
- Result: MATCH

### Check 2

- Bronze: `postsecondary_c_12_report_2012.xlsx`, Appling County High School, district `601`, school `0103`, `Black` metrics: graduates `42`, enrolled `20`, earned 24 credits suppressed (`TFS`, read as NULL).
- Transform path: suppression values are nulled during `_stitch_xlsx()` at `src/etl/education/gosa/postsecondary_c12_report/transform.py:382`; counts cast with `_to_int_expr()` at `:333`.
- Gold: `year=2008`, `district_code=601`, `school_code=0103`, `demographic=black`, `graduate_count=42`, `num_enrolled_in_college=20`, `num_earned_24_credits=NULL`.
- Result: MATCH

### Check 3

- Bronze: `postsecondary_c_12_report_2020.xlsx`, state row (`district_code_raw=ALL`, `school_code_raw=ALL`) for cohort `2016`, `Total All` metrics: graduates `103950`, enrolled `57468`, earned 24 credits `40318`; `Asian=4287`, `Pacific Islander=128`.
- Transform path: state detail detection and geography NULLing at `src/etl/education/gosa/postsecondary_c12_report/transform.py:651` and `:676`.
- Gold: `year=2016`, `district_code=NULL`, `school_code=NULL`, `demographic=all` has `103950/57468/40318`; `asian` has graduate count `4287`; `pacific_islander` has graduate count `128`.
- Result: MATCH

### Check 4

- Bronze: `postsecondary_c_12_report_2019.xlsx`, Appling County High School, `School Year=2015`, raw `school_code_raw=103`, `Total All` metrics: graduates `239`, enrolled `124`, earned 24 credits `85`.
- Transform path: school-code zero-padding at `src/etl/education/gosa/postsecondary_c12_report/transform.py:682`.
- Gold: `year=2015`, `district_code=601`, `school_code=0103`, `demographic=all`, metrics `239/124/85`.
- Result: MATCH

### Check 5

- Bronze: `postsecondary_c_12_report_2024.csv`, state row (`SCHOOL_DISTRCT_CD=ALL`, `INSTN_NUMBER=ALL`) for cohort `2020`, `Total` metrics: graduates `113189`, enrolled `60460`, earned 24 credits `36315`; `ASIAN_HS_GRADS=5240`, `PACIFIC_HS_GRADS=141`.
- Transform path: Era 3 block mapping at `src/etl/education/gosa/postsecondary_c12_report/transform.py:522`; all-string CSV read at `:588`.
- Gold: `year=2020`, `district_code=NULL`, `school_code=NULL`, `demographic=all` has `113189/60460/36315`; `asian` has `5240`; `pacific_islander` has `141`.
- Result: MATCH

## Notes

- No collapsed-row formula trace applies. The transform preserves source-published state and district aggregates; it does not compute rates, rollups, weighted averages, or derived district/state totals.
- Race math evidence from gold state rows: male plus female graduate counts equal `all` in every year; race-bucket graduate sums equal `all` in 2010-2016 and 2019-2020, are short by 1,433 in 2008, 1,779 in 2009, 8 in 2017, and 1 in 2018, and never exceed `all`.
- Current topic files are untracked in git, but the review artifacts on disk are internally fresh and consistent. This does not affect the bronze-to-gold accuracy verdict.
