# Data Review: salaries_and_benefits

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: bronze checksums, manifest, contract, validator, and keyed bronze-to-gold comparisons all support the current transform; no must-fix accuracy issues found.

## Summary

- Review date: 2026-06-10
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze freshness gate passed for all 14 CSV files; transform mtime `2026-06-10T17:02:02.198635+00:00`, manifest `generated_at` `2026-06-10T17:08:26.224161+00:00`, validation timestamp `2026-06-10T17:08:26.283882+00:00`

## Files Reviewed

- Transform: `src/etl/education/gosa/salaries_and_benefits/transform.py`
- Contract: `contracts/education/salaries_and_benefits.odcs.yaml`
- Bronze files: 14 CSV files, `salaries_and_benefits_2011.csv` through `salaries_and_benefits_2024.csv`
- Gold files: 28 parquet files, `districts.parquet` and `states.parquet` for each year 2011-2024
- Manifest: `data/gold/education/salaries_and_benefits/_transform_manifest.json`
- Validation report: `data/gold/education/salaries_and_benefits/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`, and relevant utility snippets

## Contract Verification

- Schema/parquet column match: PASS - contract, transform `STANDARD_COLUMNS` minus `detail_level`, and sampled parquet order all match: `year`, `district_code`, `school_code`, `staff_category`, seven metrics
- Column roles and grain: PASS - roles are year, `fk_district`, `fk_school`, categorical `staff_category`, and metric columns; grain is `year`, `district_code`, `school_code`, `staff_category`
- Metric units and derived quality checks: PASS - dollar columns are `currency`; four `pct_*` columns are `ratio` with non-negative SQL checks, which is correct for source values above 100 in 2021
- Categorical enums: PASS - `staff_category` enum is exactly `general_administration`, `school_administration`, `teachers_and_paraprofessionals`, matching manifest and gold
- Detail levels and layout metadata: PASS - contract detail levels are `districts` and `states`, default `districts`, path template `education/salaries_and_benefits/year={year}/{detail}.parquet`
- Foreign-key descriptors: PASS - `district_code` targets districts; `school_code` targets the composite schools key but has no populated values in this district-only topic
- Schema hash/version consistency: PASS - version `1.0.0`, schema hash `9382b972c0107d427932df1c149dd4585fa8a0e96a310849bedb7a92b95c937f`, year range `2011-2024`, no year gaps

## Validator Verification

- `_validation.json` fresh + passing: PASS - `passed: true`; validation timestamp is newer than manifest generation
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 20 validation checks passed, including contract/parquet schema, grain uniqueness, all 11 contract quality SQL checks, foreign keys, and canonical vocabulary
- Validator warnings explained: N/A - validator reported 0 warnings
- §15b quality-check coverage (cross-column invariants authored): PASS - contract enforces component reconciliation, all-null `school_code`, no metric nulls, one row per staff category per entity, RESA presence every year, and ratio non-negativity

## Manifest Verification

- Files processed coverage: PASS - all 14 current bronze CSV files appear in `files_processed`; bronze freshness check reports all checksums match and no unanalyzed files
- Categorical and recode coverage: PASS - `staff_category` and Era 2 `detail_level` mappings have `unmapped_count: 0`; Era 1 detail level is derived from the `ALL` sentinel and verified by row counts
- Row-count reconciliation: PASS - total bronze rows `9,312`, total gold rows `9,312`, total filtered `0`; every year has expansion factor `1.0`
- Metric stats sanity: PASS - all seven metrics have zero nulls; ratios are non-negative and max at `1.2731`; negative dollar values are source-backed refunds/restatements and preserved as currency

## Row and Join Accounting

- Bronze file/year disposition: PASS - every file from 2011-2024 is processed once, with `LONG_SCHOOL_YEAR` cross-checked against filename year
- Filter accounting: N/A - no rows are filtered; manifest `total_filtered` is `0`
- Join accounting: N/A - transform performs no joins or lookups; FK coverage is validated post-export
- Deduplication accounting: PASS - bronze per-file `SCHOOL_DSTRCT_CD` x `CATEGORY` duplicate groups are 0; expected and gold grains are both unique
- Aggregation/unpivot accounting: N/A - source is already long by `CATEGORY`; state rows are source-published rows, not derived aggregates

## Reconciliation Checks

- Artifact freshness: PASS - bronze checksums match; manifest and validation are current relative to transform mtime
- Contract freshness: PASS - contract schema matches current transform declaration and parquet; no `_metadata.json` dependency used
- Year coverage: PASS - current bronze, manifest, contract, and gold all cover 2011-2024
- Row preservation: PASS - independent CSV parsing and scaling produced 9,312 expected rows; null-sentinel keyed comparison joined all 9,312 rows with 0 missing keys, 0 extra keys, and 0 metric mismatches
- Column coverage: PASS - `LONG_SCHOOL_YEAR`, `SCHOOL_DSTRCT_CD`, `CATEGORY`, all dollar metrics, and all four percentage metrics feed gold; names, constant institution fields, `#RPT_NAME`, and `GRADES_SERVED_DESC` are validly excluded from the fact table
- Recode accuracy: PASS - staff category recodes are semantically correct; Era 2 `State` -> `state`, `District` -> `district`, and `DOE OTHER` -> `district` are documented and preserve RESA codes
- Asian-family demographic recodes (§5b): N/A - no demographic column or Asian-family wide metrics
- Demographic mutual exclusivity (§5a - no rollup row alongside split source rows in the same category): N/A - no demographic column
- Demographic collision aggregation before dedup (§5): N/A - no demographic normalization
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS - parquet order is `year`, `district_code`, `school_code`, `staff_category`, then metrics
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS - exported parquet excludes `detail_level`, district names, school names, census IDs, `topic`, school year, and institution labels
- Canonical column vocabulary (§16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - no forbidden variants detected; finance metric names are descriptive and education-specific
- Shared categorical utilities applied (§10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no `grade_level` or `subject` column
- Tidy long format (§9 - no demographics/years/components as column names): PASS - staff category is a row categorical; years and categories are not encoded as metric columns
- FK keys present in dimension tables (§13 - `district_code`, `school_code`, `demographic`): PASS - 254 populated district keys all resolve in `data/gold/education/_dimensions/districts.parquet`; `school_code` has 0 populated rows
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - row grain and `staff_category` filter surface are contract-derived; state rows use null geography and district rows include queryable RESA codes
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS - IDs stay strings, percentages are scaled to 0-1 ratios, suppression markers do not survive, and district-only `school_code` is retained as all-null

## Spot Checks

### Check 1

- Bronze: `data/bronze/education/gosa/salaries_and_benefits/salaries_and_benefits_2011.csv`, state `Teachers and Paraprofessionals`, `LONG_SCHOOL_YEAR=2010-11`, `SCHOOL_DSTRCT_CD=ALL`, `SALARIES=5932372355.19`, `BENEFITS=2185019947.74`, `SALARIES_AND_BENEFITS=8117392302.93`, `% Rev- GF/Title/Lottery=54.21`
- Transform path: `transform_file()` lines 349-405 parse year, null the `ALL` district sentinel, recode staff category, cast dollars, and divide percent columns by 100
- Gold: `year=2011`, `district_code=NULL`, `school_code=NULL`, `staff_category=teachers_and_paraprofessionals`, `salaries_dollars=5932372355.19`, `benefits_dollars=2185019947.74`, `salaries_and_benefits_dollars=8117392302.93`, `pct_revenue_gf_title_lottery=0.5421`
- Result: MATCH

### Check 2

- Bronze: `data/bronze/education/gosa/salaries_and_benefits/salaries_and_benefits_2022.csv`, Charlton County `Teachers and Paraprofessionals`, `SCHOOL_DSTRCT_CD=624`, `SALARIES=6204434.85`, `BENEFITS=3059444.6`, `SALARIES_AND_BENEFITS=9263879.45`, `% Exp-Total K-12=40.58`
- Transform path: `transform_file()` lines 395-405 zero-pads district code, keeps `school_code` null, casts metrics, and scales percent columns
- Gold: `year=2022`, `district_code=624`, `staff_category=teachers_and_paraprofessionals`, `salaries_dollars=6204434.85`, `benefits_dollars=3059444.6`, `salaries_and_benefits_dollars=9263879.45`, `pct_expense_total_k12=0.4058`
- Result: MATCH

### Check 3

- Bronze: `data/bronze/education/gosa/salaries_and_benefits/salaries_and_benefits_2023.csv`, `DETAIL_LVL_DESC=DOE OTHER`, district code `850`, Northwest Georgia RESA `General Administration`, `SALARIES=155001.96`, `BENEFITS=90932`, `SALARIES_AND_BENEFITS=245933.96`, `EXP_TOTAL_K_12=2.5`
- Transform path: `_detail_level_era2()` lines 291-310 maps `DOE OTHER` to district detail; lines 395-405 preserve code `850` and scale `EXP_TOTAL_K_12`
- Gold: `year=2023`, `district_code=850`, `school_code=NULL`, `staff_category=general_administration`, `salaries_dollars=155001.96`, `benefits_dollars=90932.0`, `salaries_and_benefits_dollars=245933.96`, `pct_expense_total_k12=0.025`
- Result: MATCH

### Check 4

- Bronze: `data/bronze/education/gosa/salaries_and_benefits/salaries_and_benefits_2021.csv`, Forsyth County `Teachers and Paraprofessionals`, `% Rev- GF/Title/Lottery=122.53`, `% Rev- Total K-12=101.23`, `% Exp- GF/Title/Lottery=127.31`, `% Exp-Total K-12=90.44`
- Transform path: lines 48-56 document ratios above 100 as valid; lines 403-405 divide by 100; contract marks the four columns as `unit: ratio`
- Gold: `district_code=658`, `staff_category=teachers_and_paraprofessionals`, `pct_revenue_gf_title_lottery=1.2253`, `pct_revenue_total_k12=1.0123`, `pct_expense_gf_title_lottery=1.2731`, `pct_expense_total_k12=0.9044`
- Result: MATCH

### Check 5

- Bronze: `data/bronze/education/gosa/salaries_and_benefits/salaries_and_benefits_2024.csv`, district `7830619`, `General Administration`, `SALARIES=-2000`, `BENEFITS=25409.58`, `SALARIES_AND_BENEFITS=23409.58`
- Transform path: lines 42-47 document negative dollars as preserved currency; lines 403-405 cast dollars without nulling them
- Gold: `year=2024`, `district_code=7830619`, `staff_category=general_administration`, `salaries_dollars=-2000.0`, `benefits_dollars=25409.58`, `salaries_and_benefits_dollars=23409.58`
- Result: MATCH

## Notes

- Existing `data-review-claude.md` was intentionally not read before completing this independent review.
- No collapsed-row or derived-aggregate formula exists in this transform; the applicable formula-level check is component reconciliation, and sampled source rows plus the contract SQL show `SALARIES + BENEFITS = SALARIES_AND_BENEFITS` with zero violations.
