# Data Review: act_scores

## Verdict

**Status**: NEEDS FIXES
**Must-fix count**: 1

Summary: current artifacts are fresh and validator-clean, but the transform omits usable 2004 Georgia state demographic ACT score/count facts from gold.

## Summary

- Review date: 2026-06-10
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH — `transform.py` mtime is 2026-06-10T13:53:30Z, manifest `generated_at` is 2026-06-10T13:56:40Z, validation timestamp is 2026-06-10T13:58:47Z, and `scripts/check_bronze_freshness.py education gosa act_scores` reports all 21 bronze checksums match with no unanalyzed files.

## Files Reviewed

- Transform: `src/etl/education/gosa/act_scores/transform.py`
- Contract: `contracts/education/act_scores.odcs.yaml`
- Bronze files: 21 source files, `act_scores_2004.csv` through `act_scores_2024.csv`
- Gold files: 63 parquet files, `year=2004` through `year=2024`, each with `schools.parquet`, `districts.parquet`, and `states.parquet`
- Manifest: `data/gold/education/act_scores/_transform_manifest.json`
- Validation report: `data/gold/education/act_scores/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`, and relevant shared utilities.

## Contract Verification

- Schema/parquet column match: PASS — all 63 parquet files have `['year', 'district_code', 'school_code', 'test_component', 'num_tested', 'avg_score']`, matching `schema[0].properties[]` in the ODCS contract.
- Column roles and grain: FAIL — the emitted schema and current parquet agree with each other, but the real 2004 source grain includes state-level demographic observations that require `demographic` in the natural key.
- Metric units and derived quality checks: PASS — `num_tested` has `unit: count`; `avg_score` has `unit: score`, `value_min: 1`, and `value_max: 36`; derived quality SQL checks pass.
- Categorical enums: PASS — contract, manifest, and actual gold all have the same `test_component` enum: `combined_english_writing`, `composite`, `english`, `mathematics`, `reading`, `science`, `writing_subscore`.
- Detail levels and layout metadata: PASS — contract detail levels are `schools`, `districts`, and `states`; `path_template`, `partition_columns`, and available years match current gold.
- Foreign-key descriptors: PASS — `district_code` targets the districts dimension; `school_code` targets the composite `(district_code, school_code)` schools dimension.
- Schema hash/version consistency: PASS — contract version is `1.0.0`, schema hash is present, year range is `2004-2024`, and contract available years match gold.

## Validator Verification

- `_validation.json` fresh + passing: PASS — validation timestamp 2026-06-10T13:58:47Z is newer than manifest `generated_at`, and `"passed": true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS — validation reports 20 pass, 0 fail, 1 warning; schema, grain uniqueness, contract quality SQL, foreign keys, canonical vocabulary, and geography nulling all pass.
- Validator warnings explained: PASS — null-rate warnings for 2021, 2022, and 2024 match bronze school-level suppression spikes: 2021 has 810/2199 null school counts and scores, 2022 has 683/2413, and 2024 has 899/2402.
- §15b quality-check coverage (cross-column invariants authored): PASS — authored checks cover positive count when average exists, non-suppressed state rows, and component year ranges.

## Manifest Verification

- Files processed coverage: PASS — manifest lists all 21 current bronze files with expected years and eras.
- Categorical and recode coverage: FAIL — `test_component` coverage is complete with `unmapped_count = 0`, but the manifest has no `demographic` mapping because the transform drops the 2004 Georgia state demographic source columns before gold emission.
- Row-count reconciliation: PASS — current all-students row shape reconciles: 2004 is `(519 - 1 national row) * 5 = 2590`; 2005-2010 are 5x wide-to-long expansions; 2011-2024 equal school rows plus unique official district/state context rows, with 20 explicit 2022 all-null duplicate rows removed.
- Metric stats sanity: PASS — gold `avg_score` range is 4.2-35.5 after the 2006 impossible scores are nulled; `num_tested` is non-negative with expected suppression nulls in 2011-2024.

## Row and Join Accounting

- Bronze file/year disposition: FAIL — every file is processed, but usable 2004 Georgia state demographic score/count columns have no gold disposition other than being omitted.
- Filter accounting: PASS — row filters are accounted for: one 2004 national benchmark row and twenty 2022 all-null duplicate school rows.
- Join accounting: N/A — the transform performs no data joins; FK joins are validated post-export against dimensions.
- Deduplication accounting: PASS — the pre-dedup collision guard runs, and the only duplicate source keys found are the documented 2022 all-null placeholder twins.
- Aggregation/unpivot accounting: PASS — 2004-2010 all-students columns expand 5x by component; 2011-2024 district/state rows are materialized from official constant context columns, not re-aggregated from suppressed school rows.

## Reconciliation Checks

- Artifact freshness: PASS — bronze checksums, manifest, validation, contract, and gold layout are current.
- Contract freshness: PASS — contract is emitted from current transform/gold; no `_metadata.json` dependency was used.
- Year coverage: PASS — gold covers every source year, 2004-2024, with no gaps.
- Row preservation: FAIL — current gold preserves all-students rows but loses 40 usable Georgia state demographic rows from 2004.
- Column coverage: FAIL — 2004 `ALL:ALL` demographic score/count columns are valid fact metrics and are not represented in gold.
- Recode accuracy: PASS for `test_component`; FAIL for omitted demographic labels because no demographic recode is attempted.
- Asian-family demographic recodes (§5b): FAIL — the 2004 source label `Asian-American/Pacific Islander` is the combined bucket and should become `asian_pacific_islander` if preserved, but it is currently dropped.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): PASS for current gold because no demographic column exists; fix must preserve this by emitting either the combined Asian/Pacific Islander convention and aggregating the two Hispanic source labels into one canonical `hispanic` row, not by adding overlapping split/rollup rows.
- Demographic collision aggregation before dedup (§5): FAIL — the 2004 source has two Hispanic labels that would normalize to `hispanic`; current transform drops them instead of aggregating with count-sum and weighted-average score.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): FAIL relative to the full source grain because `demographic` is missing.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS — parquet files contain no forbidden fact-table columns.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS — `num_tested`, `test_component`, and `avg_score` follow canonical assessment vocabulary.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A — no grade or subject column.
- Tidy long format (§9 — no demographics/years/components as column names): FAIL — current gold is tidy for all-students components, but 2004 demographic observations remain trapped in bronze column names and are omitted.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS for current geography keys — 190 district keys and 546 composite school keys all resolve, with no duplicate dimension keys. Demographic FK must be added if the fix adds `demographic`.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): FAIL — API consumers cannot filter/query the valid 2004 state demographic facts because the contract lacks `demographic`.
- Standards compliance (catch-all for §1-§16 items not enumerated above): FAIL — preserving source fact metrics takes priority; the current transform intentionally omits valid source facts.

## Spot Checks

### Check 1

- Bronze: `data/bronze/education/gosa/act_scores/act_scores_2004.csv`, `SysSchoolID=ALL:ALL`, `Composite Asian-American/Pacific Islander=21.8`, `Asian-American/Pacific Islander Number Tested=605`; same state row also has populated female, male, Black, White, Native American, and Hispanic subgroup score/count cells.
- Transform path: `_transform_era12()` logs and drops demographic columns at `transform.py:356-369`, then unpivots only `ERA12_SCORE_COLUMNS` at `transform.py:391-410`.
- Gold: `year=2004/states.parquet` has only five all-students rows and no `demographic` column; state composite is `num_tested=20510`, `avg_score=20.0`.
- Result: MISMATCH

### Check 2

- Bronze: `data/bronze/education/gosa/act_scores/act_scores_2006.xls`, Campbell High School `633:1054` and Cedar Grove High School `644:172` have ten section scores from 36.9 through 41.5, above the ACT 1-36 scale.
- Transform path: `_null_invalid_act_scores()` at `transform.py:667-707`.
- Gold: 2006 rows for `633/1054` and `644/0172` preserve `num_tested` values 225 and 183 and set all ten `avg_score` values to NULL.
- Result: MATCH

### Check 3

- Bronze: `data/bronze/education/gosa/act_scores/act_scores_2011.csv`, Appling `601/103`, Composite: school `15/15.8`, district `15/15.8`, state `28789/19.8`.
- Transform path: `_transform_era34()` materializes school rows and official district/state context rows at `transform.py:568-597`.
- Gold: 2011 composite rows for school `601/0103`, district `601/NULL`, and state `NULL/NULL` exactly match those counts and scores.
- Result: MATCH

### Check 4

- Bronze: `data/bronze/education/gosa/act_scores/act_scores_2022.csv` has 20 duplicate `(district, school, component)` groups where one renamed-school row is all NULL, e.g. Cass High School with data beside New Cass High School all NULL.
- Transform path: `_drop_placeholder_twins()` at `transform.py:418-452`.
- Gold: the 20 surviving rows keep the data-carrying values, e.g. `608/0114` composite `num_tested=32`, `avg_score=19.8`, and no duplicate grain rows remain.
- Result: MATCH

### Check 5

- Bronze: `data/bronze/education/gosa/act_scores/act_scores_2008.xls`, `602:103` Atkinson County High School has suppressed Composite score (`Too Few Students` -> NULL) and `All Students Number Tested=5`.
- Transform path: `_to_float_expr()` / `_to_int_expr()` in the Era 1/2 unpivot path at `transform.py:213-230` and `transform.py:391-410`.
- Gold: 2008 `602/0103/composite` has `num_tested=5`, `avg_score=NULL`.
- Result: MATCH

### Check 6

- Bronze: `data/bronze/education/gosa/act_scores/act_scores_2024.csv`, `601/0103/Composite` has TFS/null district and school metrics and state `14727/21.0`.
- Transform path: `_transform_era34()` casts suppression markers through `_to_float_expr()` / `_to_int_expr()` and materializes all three detail levels at `transform.py:541-597`.
- Gold: 2024 `601/0103/composite` and district `601/NULL/composite` are NULL/NULL, while state composite is `14727/21.0`.
- Result: MATCH

## Required Fixes

### Fix 1: Preserve 2004 Georgia state demographic facts

- **Severity**: HIGH
- **Issue**: The transform drops valid 2004 Georgia state ACT score/count observations for demographic subgroups. These are not national benchmark rows and not dimension attributes; they are source fact metrics at the state detail level.
- **Evidence**: Bronze `data/bronze/education/gosa/act_scores/act_scores_2004.csv` has populated Georgia `ALL:ALL` demographic cells, e.g. `Composite Asian-American/Pacific Islander=21.8` with `Asian-American/Pacific Islander Number Tested=605`, `Composite Female=20.1` with `Female Number Tested=12299`, and 40 state subgroup score rows across five ACT components. Current gold `data/gold/education/act_scores/year=2004/states.parquet` has only five all-students rows and no `demographic` column. Transform logic at `transform.py:356-410` logs the 48 demographic columns as dropped and unpivots only the five all-students score columns.
- **Location**: `src/etl/education/gosa/act_scores/transform.py:356-410`
- **Suggested fix**: Preserve the 2004 `ALL:ALL` demographic score/count columns as state-level gold rows instead of dropping them. Add `demographic` to `STANDARD_COLUMNS`, `NATURAL_KEYS`, and the contract column declaration; emit `demographic='all'` for current all-students rows; unpivot the 2004 state demographic score/count pairs into rows keyed by `year`, NULL geography, `demographic`, and `test_component`; map `Asian-American/Pacific Islander` to `asian_pacific_islander`; aggregate the two Hispanic source labels into canonical `hispanic` with `num_tested` summed and `avg_score` weighted by `num_tested`; record the demographic mapping in the manifest; keep national benchmark rows out of scope.
