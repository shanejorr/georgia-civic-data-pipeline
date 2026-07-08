# Data Review: enrollment_october_gender_race_ethnicity

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: current bronze, transform, contract, validator, manifest, and gold output reconcile with no must-fix accuracy findings.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze checksum gate passed for all 34 CSV files; transform mtime `2026-06-12T16:34:24.918066+00:00` is older than manifest `2026-06-12T16:34:50.782206+00:00`; validation timestamp `2026-06-12T16:34:50.855616+00:00` is fresh and passing.

## Files Reviewed

- Transform: `src/etl/education/georgiainsights/enrollment_october_gender_race_ethnicity/transform.py`
- Contract: `contracts/education/enrollment_october_gender_race_ethnicity.odcs.yaml`
- Bronze files: 34 CSV files, `Fiscal Year2010-1` through `Fiscal Year2026-1`, one District and one School file per year
- Gold files: 51 parquet files, `year=2010` through `year=2026`, with `states.parquet`, `districts.parquet`, and `schools.parquet` per year
- Manifest: `data/gold/education/enrollment_october_gender_race_ethnicity/_transform_manifest.json`
- Validation report: `data/gold/education/enrollment_october_gender_race_ethnicity/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`, and `src/etl/education/georgiainsights/_enrollment_race_lookups.py`

## Contract Verification

- Schema/parquet column match: PASS - contract properties and actual parquet columns are `year`, `district_code`, `school_code`, `race`, `gender`, `student_count`; validation checked all 51 parquet files.
- Column roles and grain: PASS - roles are year, district FK, school FK, categorical race, categorical gender, metric student_count; grain is `(year, district_code, school_code, race, gender)`.
- Metric units and derived quality checks: PASS - `student_count` is `unit: count`; contract includes non-negative and suppression-floor checks.
- Categorical enums: PASS - contract, manifest, and gold all agree on race values `asian`, `black`, `hispanic`, `multiracial`, `native_american`, `pacific_islander`, `white`; gender values are `female`, `male`.
- Detail levels and layout metadata: PASS - contract declares `schools`, `districts`, `states`; gold has all three files for every year 2010-2026.
- Foreign-key descriptors: PASS - `district_code` targets districts; `school_code` targets composite `(district_code, school_code)` schools.
- Schema hash/version consistency: PASS - version is `1.0.0`; schema hash is `1cdd6e5ae6719bfdf75e40e5470b8dbf10b209d491c22b9bf2eb6a1019c57ab2`.

## Validator Verification

- `_validation.json` fresh + passing: PASS - passed true; validation timestamp is newer than manifest generation.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 21 pass, 0 fail, 0 warning.
- Validator warnings explained: N/A - validation emitted no warnings.
- §15b quality-check coverage (cross-column invariants authored): PASS - contract enforces non-empty data, categorical enums, count non-negativity, suppression floor, no suppressed state rows, and complete 14-row state race x gender partitions.

## Manifest Verification

- Files processed coverage: PASS - manifest lists all 34 current bronze CSV files with no missing or extra files.
- Categorical and recode coverage: PASS - gender and race both have `unmapped_count: 0`; manifest maps all observed bronze values.
- Row-count reconciliation: PASS - manifest `total_gold` is 599,760 and matches actual parquet row count.
- Metric stats sanity: PASS - `student_count` min is 15, max is 387,073, and nulls reflect source `*` suppression.

## Row and Join Accounting

- Bronze file/year disposition: PASS - every District and School CSV from 2010-2026 is processed once.
- Filter accounting: PASS - `Gender == "Total"` rows are explicitly dropped; direct bronze audit found 0 cases where Total was published while Female or Male was missing, and 0 complete-cell `Total != Female + Male` violations. Duplicate state rows are explicitly recorded and removed.
- Join accounting: N/A - transform performs no data joins.
- Deduplication accounting: PASS - duplicate state rows from District and School files are value-identical for all 17 years; gold keeps exactly one state row per `(year, race, gender)`.
- Aggregation/unpivot accounting: PASS - seven race/ethnicity columns unpivot to seven race rows; no value aggregation is performed. Per-year expected rows `14 * (1 + district_count + school_pair_count)` match actual gold for every year.

## Reconciliation Checks

- Artifact freshness: PASS - bronze checksum gate passed; transform, manifest, validation, contract, and gold are current relative to one another.
- Contract freshness: PASS - contract matches current transform/gold and has no `_metadata.json` dependency.
- Year coverage: PASS - bronze and gold cover 2010-2026 with no gaps.
- Row preservation: PASS - actual gold by year equals the independently recomputed expected row count for every year; 2026 is 14 state + 3,318 district + 32,424 school = 35,756 rows.
- Column coverage: PASS - fact keys, race, gender, and `student_count` all trace to filename metadata or bronze columns; dimension attributes `System Name` and school names are excluded from fact output.
- Recode accuracy: PASS - `Female -> female`, `Male -> male`; `Ethnic Hispanic -> hispanic`, `Race AmericanIndian -> native_american`, `Race Asian -> asian`, `Race Black -> black`, `Race Pacific Islander -> pacific_islander`, `Race White -> white`, `Two or more Races -> multiracial`.
- Asian-family demographic recodes (§5b): PASS - bronze publishes separate `Race Asian` and `Race Pacific Islander` columns in every file, so split `asian` and `pacific_islander` keys are correct.
- Demographic mutual exclusivity (§5a - no rollup row alongside split source rows in the same category): PASS - gold has split `asian` and `pacific_islander` and no `asian_pacific_islander` rollup.
- Demographic collision aggregation before dedup (§5): N/A - this topic uses `race` and `gender` categorical axes, not a single `demographic` column; race mappings are one-to-one.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS - actual order is `year`, geography keys, race/gender categoricals, then metric.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS - actual parquet contains none of these columns.
- Canonical column vocabulary (§16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - `student_count` is the canonical enrollment count metric; no grade, subject, assessment, proficiency, or rate columns apply.
- Shared categorical utilities applied (§10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no grade or subject columns.
- Tidy long format (§9 - no demographics/years/components as column names): PASS - wide race columns are unpivoted into `race` rows.
- FK keys present in dimension tables (§13 - `district_code`, `school_code`, `demographic`): PASS - 256 fact district keys and 2,720 fact school composite keys all resolve; dimension key duplicates are 0.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - race and gender are filterable categoricals; FKs and grain derive cleanly from the contract.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS - suppression markers become NULL, IDs remain strings with leading zeros preserved, state/district/school geography nulling passes validation, and no impossible count values are present.

## Spot Checks

### Check 1

- Bronze: `FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2010-1 District.csv`, `System ID=601`, `Gender=Female`, `Race White=1065`.
- Transform path: `_read_bronze_csv()` strips headers and nulls `*`; `_transform_file_frame()` maps district row, gender `Female -> female`, unpivots `Race White -> white`.
- Gold: `year=2010`, `district_code=601`, `school_code=NULL`, `race=white`, `gender=female`, `student_count=1065`.
- Result: MATCH

### Check 2

- Bronze: `FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2026-1 School.csv`, `System ID=737`, `School ID=3052-Northeast Middle School`, `Gender=Male`, `Race Black=127`.
- Transform path: school code regex extracts `3052`; gender maps to `male`; race column unpivots to `black`.
- Gold: `year=2026`, `district_code=737`, `school_code=3052`, `race=black`, `gender=male`, `student_count=127`.
- Result: MATCH

### Check 3

- Bronze: `FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2026-1 School.csv`, `System ID=737`, `School ID=3052-Northeast Middle School`, `Gender=Male`, `Race Asian=*`.
- Transform path: local CSV reader registers `*` as NULL; unpivot preserves the row with NULL `student_count`.
- Gold: `year=2026`, `district_code=737`, `school_code=3052`, `race=asian`, `gender=male`, `student_count=NULL`.
- Result: MATCH

### Check 4

- Bronze: 2026 state Female Hispanic appears in both District and School files with `Ethnic Hispanic=164663`.
- Transform path: both state rows enter as duplicates, `assert_no_natural_key_collisions()` verifies identical metrics, and `deduplicate_by_detail_level()` keeps one.
- Gold: exactly one `year=2026`, state-level, `race=hispanic`, `gender=female` row with `student_count=164663`.
- Result: MATCH

## Notes

- No `## Required Fixes` section is included because the verdict is PASS.
- Prior review reports were not read before completing this independent review.
