# Data Review: revenues_and_expenditures

## Verdict

**Status**: NEEDS FIXES
**Must-fix count**: 1

Summary: bronze-to-gold row and value preservation checks pass, but the transform-authored contract text understates a material 2024 `dollars_per_fte` source artifact.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze freshness check passed for all 14 CSVs; transform mtime `2026-06-12T12:16:32.804694+00:00`, manifest `2026-06-12T12:16:41.049326+00:00`, validation `2026-06-12T12:16:41.134963+00:00`.

## Files Reviewed

- Transform: `src/etl/education/gosa/revenues_and_expenditures/transform.py`
- Contract: `contracts/education/revenues_and_expenditures.odcs.yaml`
- Bronze files: 14 CSVs, `revenues_and_expenditures_2011.csv` through `revenues_and_expenditures_2024.csv`
- Gold files: 42 parquet files, `year=2011` through `year=2024`, each with `schools.parquet`, `districts.parquet`, and `states.parquet`
- Manifest: `data/gold/education/revenues_and_expenditures/_transform_manifest.json`
- Validation report: `data/gold/education/revenues_and_expenditures/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`, `data/bronze/education/gosa/revenues_and_expenditures/bronze-data-structure.md`.

## Contract Verification

- Schema/parquet column match: PASS - contract properties exactly match actual parquet columns: `year`, `district_code`, `school_code`, `rev_exp_type`, `category`, `rev_exp_value`, `dollars_per_fte`.
- Column roles and grain: PASS - roles are `year`, `fk_district`, `fk_school`, two categoricals, and two metrics; grain is `year`, geography keys, `rev_exp_type`, `category`.
- Metric units and derived quality checks: PASS - both metrics are `unit: currency`, appropriate for signed dollar amounts with no non-negative range guard.
- Categorical enums: PASS - contract enums match manifest and gold distinct values for `rev_exp_type` and `category`.
- Detail levels and layout metadata: PASS - contract lists `schools`, `districts`, `states`; gold has all three files for every year.
- Foreign-key descriptors: PASS - validation confirms all 254 district keys and 3,880 composite school keys resolve.
- Schema hash/version consistency: PASS - contract is `version: 1.0.0`, `schema_hash: 5fb333f25290ab469febda5d0737236e962192710fccbd0763bf8ee25fd7bfc6`, and `year_range: 2011-2024`.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp is after manifest generation and reports `"passed": true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 21 checks passed, 0 failed, 0 warnings.
- Validator warnings explained: N/A - validation emitted no warnings.
- §15b quality-check coverage (cross-column invariants authored): PASS - authored checks cover valid `rev_exp_type`/`category` pairs, `rev_exp_value` completeness, `dollars_per_fte` null-year confinement, state-row completeness, and district-row 17-pair completeness.

## Manifest Verification

- Files processed coverage: PASS - manifest covers all 14 current bronze CSVs, 2011-2024, and the checksum gate passed with no unanalyzed files.
- Categorical and recode coverage: PASS - three recorded categoricals have `unmapped_count: 0`; maps match actual bronze values and gold values.
- Row-count reconciliation: PASS - `total_bronze` and actual gold row count both equal 499,468; each year has expansion factor 1.0 and no filters.
- Metric stats sanity: PASS - signed currency values, including negatives, are preserved; `dollars_per_fte` has exactly 667 nulls in 2012-2014 and `rev_exp_value` has zero nulls.

## Row and Join Accounting

- Bronze file/year disposition: PASS - every CSV is processed once; filename spring year matches the single school-year value inside each file.
- Filter accounting: N/A - no rows are filtered; manifest `total_filtered` is 0.
- Join accounting: N/A - transform performs no data joins.
- Deduplication accounting: PASS - natural-key duplicate check found no actual duplicate groups in gold; dedup is a safety net and did not change row counts.
- Aggregation/unpivot accounting: PASS - no aggregation or unpivot occurs; row flow is 1:1 from bronze to gold.

## Reconciliation Checks

- Artifact freshness: PASS - transform, manifest, validation, bronze checksums, and gold outputs are current.
- Contract freshness: PASS - contract was emitted from the current transform/gold run; no `_metadata.json` dependency.
- Year coverage: PASS - gold has 2011-2024 and no unexpected years.
- Row preservation: PASS - bronze and gold counts match by year and normalized detail level; all 42 year/detail comparisons have diff 0.
- Column coverage: PASS - all fact keys, categoricals, and metrics have direct lineage; name columns and `GRADES_SERVED_DESC` are validly excluded as dimension/metadata fields, and partial `FTE_COUNT` is validly excluded after formula verification.
- Recode accuracy: PASS - `K-12 Revenues` -> `k12_revenues`, `K-12 Expenditures` -> `k12_expenditures`, and all 17 category labels map correctly, including `School food Services` -> `school_food_services`.
- Asian-family demographic recodes (§5b): N/A - no demographic column or race metrics.
- Demographic mutual exclusivity (§5a - no rollup row alongside split source rows in the same category): N/A - no demographic column.
- Demographic collision aggregation before dedup (§5): N/A - no demographic column.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS - actual parquet order is `year`, `district_code`, `school_code`, `rev_exp_type`, `category`, `rev_exp_value`, `dollars_per_fte`.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS - exported parquet contains no forbidden columns.
- Canonical column vocabulary (§16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - no shared assessment/proficiency vocabulary applies; topic-specific financial names are coherent.
- Shared categorical utilities applied (§10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no grade or subject columns.
- Tidy long format (§9 - no demographics/years/components as column names): PASS - source is already long and gold remains long.
- FK keys present in dimension tables (§13 - `district_code`, `school_code`, `demographic`): PASS - validation confirms all district and composite school keys resolve.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - row grain and categorical filters derive cleanly from the contract.
- Standards compliance (catch-all for §1-§16 items not enumerated above): FAIL - the transform-authored `dollars_per_fte` contract/README text is materially incomplete for 2024 school rows.

## Spot Checks

### Check 1

- Bronze: `revenues_and_expenditures_2024.csv`, Bloomingdale Elementary School `(SCHOOL_DSTRCT_CD=625, INSTN_NUMBER=4052)`, `K-12 Expenditures` / `Media`, `REV_EXP_VALUE=96247.94`, `DOLLARS_PER_FTE=96247.94`.
- Transform path: `_transform_era_1()` lines 508-516 casts metrics, zero-pads IDs, and recodes category/type.
- Gold: `year=2024`, `district_code=625`, `school_code=4052`, `rev_exp_type=k12_expenditures`, `category=media`, `rev_exp_value=96247.94`, `dollars_per_fte=96247.94`.
- Result: MATCH

### Check 2

- Bronze: `revenues_and_expenditures_2022.csv`, Idlewood Elementary School `(DISTRICT_CODE=644, SCHOOL_CODE=1059)`, `K-12 Expenditures` / `School food Services`, `REV_EXP_VALUE=0`, `Dollars per FTE=0`.
- Transform path: `_transform_era_2_4()` lines 392-414 derives `school`, zero-pads IDs, maps `School food Services` to `school_food_services`, and preserves metrics.
- Gold: `year=2022`, `district_code=644`, `school_code=1059`, `category=school_food_services`, `rev_exp_value=0.0`, `dollars_per_fte=0.0`.
- Result: MATCH

### Check 3

- Bronze: `revenues_and_expenditures_2013.csv`, Okefenokee RESA `(DISTRICT_CODE=888, SCHOOL_CODE=ALL)`, `K-12 Revenues` / `State Other`, `REV_EXP_VALUE=510618`, `Dollars per FTE=null`, `FTE_COUNT=null`.
- Transform path: `_transform_era_3()` lines 417-429 drops partial `FTE_COUNT` after validation and delegates to `_transform_era_2_4()` for district-level nulling and metric preservation.
- Gold: `year=2013`, `district_code=888`, `school_code=null`, `rev_exp_type=k12_revenues`, `category=state_other`, `rev_exp_value=510618.0`, `dollars_per_fte=null`.
- Result: MATCH

### Check 4

- Bronze: `revenues_and_expenditures_2012.csv`, Howard High School `(DISTRICT_CODE=611, SCHOOL_CODE=105)`, `K-12 Expenditures` / `Instruction`, `REV_EXP_VALUE=5751295.96`, `Dollars per FTE=5135.09`, `FTE_COUNT=1120`.
- Transform path: `_format_id_expr()` lines 312-325 pads `105` to `0105`; `_transform_era_2_4()` lines 403-414 preserves metric values.
- Gold: `year=2012`, `district_code=611`, `school_code=0105`, `category=instruction`, `rev_exp_value=5751295.96`, `dollars_per_fte=5135.09`.
- Result: MATCH

### Check 5

- Bronze: `revenues_and_expenditures_2024.csv`, International Student Center `(DETAIL_LVL_DESC=DOE OTHER, SCHOOL_DSTRCT_CD=644, INSTN_NUMBER=6015)`, `K-12 Expenditures` / `Debt Services`, `REV_EXP_VALUE=0.00`, `DOLLARS_PER_FTE=0.00`.
- Transform path: `_transform_era_1()` lines 451-506 routes DOE OTHER rows with real `INSTN_NUMBER` to `school` and records the reclassification.
- Gold: `year=2024`, `district_code=644`, `school_code=6015`, `category=debt_services`, `rev_exp_value=0.0`, `dollars_per_fte=0.0`.
- Result: MATCH

## Required Fixes

### Fix 1: Correct `dollars_per_fte` semantics for 2024 school rows

- **Severity**: MEDIUM
- **Issue**: The transform-authored contract and README text tells consumers to filter to school-detail traditional schools before treating `dollars_per_fte` as per-pupil spending, but that is false for the 2024 file: every school-detail row, including ordinary schools, has `DOLLARS_PER_FTE` equal to `REV_EXP_VALUE`. The values are preserved from bronze, but the emitted metadata misstates when the metric is analytically meaningful.
- **Evidence**: Bronze `data/bronze/education/gosa/revenues_and_expenditures/revenues_and_expenditures_2024.csv` has 35,398 of 35,398 `DETAIL_LVL_DESC='School'` rows where `DOLLARS_PER_FTE == REV_EXP_VALUE`; example Bloomingdale Elementary `(625,4052)`, `Media`, has `REV_EXP_VALUE=96247.94` and `DOLLARS_PER_FTE=96247.94`. Gold `data/gold/education/revenues_and_expenditures/year=2024/schools.parquet` preserves the same row as `rev_exp_value=96247.94` and `dollars_per_fte=96247.94`. Transform logic at lines 790-803 and 815-831 documents the artifact only for 2023-2024 DOE OTHER / aggregate / non-school rows and says filtering to school-detail traditional schools is enough, which the 2024 bronze and gold disprove.
- **Location**: `src/etl/education/gosa/revenues_and_expenditures/transform.py:790-803`, `src/etl/education/gosa/revenues_and_expenditures/transform.py:815-831`, `src/etl/education/gosa/revenues_and_expenditures/transform.py:862-867`
- **Suggested fix**: Update the `dollars_per_fte` column description, limitations, and notes emitted by `_emit_contract_and_readme()` to state explicitly that all 2024 school-detail rows also publish `DOLLARS_PER_FTE == REV_EXP_VALUE` verbatim, so the metric should be treated as a reported source field and not a reliable per-FTE/per-pupil amount for 2024 school rows. Re-run the transform so the contract and README are re-emitted.

## Notes

- No prior `data-review-claude.md` or `data-review-codex.md` was read before forming these findings.
- The required fix is metadata emitted from `transform.py`, not a gold value change. Direct bronze-to-gold value preservation is otherwise correct for the checks performed.
