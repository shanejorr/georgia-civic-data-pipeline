# Data Review: certified_personnel

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze, transform, contract, validator, and gold output reconcile exactly; no must-fix accuracy issues were found.

## Summary

- Review date: 2026-06-11
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - transform mtime 2026-06-11T18:41:39Z precedes manifest generation 2026-06-11T18:42:02.426748Z; validation timestamp 2026-06-11T18:42:02.596044Z is newer than the manifest and reports `passed: true`; current bronze checksums match `bronze-data-structure.md`.

## Files Reviewed

- Transform: `src/etl/education/gosa/certified_personnel/transform.py`
- Contract: `contracts/education/certified_personnel.odcs.yaml`
- Bronze files: 14 CSV files, `certified_personnel_2011.csv` through `certified_personnel_2024.csv`
- Gold files: 42 parquet files, three detail files (`schools.parquet`, `districts.parquet`, `states.parquet`) for each year 2011-2024
- Manifest: `data/gold/education/certified_personnel/_transform_manifest.json`
- Validation report: `data/gold/education/certified_personnel/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`, and relevant shared utilities under `src/utils/`.

## Contract Verification

- Schema/parquet column match: PASS - contract columns are exactly `year`, `district_code`, `school_code`, `employee_type`, `measure_family`, `measure_label`, `measure_value`; all 42 parquet files match this order.
- Column roles and grain: PASS - roles are year, district FK, school FK, categoricals, and metric; contract grain is `year + district_code + school_code + employee_type + measure_family + measure_label`, matching the actual natural key.
- Metric units and derived quality checks: PASS - `measure_value` is intentionally unit-exempt because units vary by row; transform authors range and structural SQL checks instead, and validator reports all 11 contract quality checks passing.
- Categorical enums: PASS - contract enums for `employee_type`, `measure_family`, and `measure_label` match manifest `gold_values_produced` and actual gold distinct values.
- Detail levels and layout metadata: PASS - contract reports `schools`, `districts`, and `states`, with path template `education/certified_personnel/year={year}/{detail}.parquet`; gold layout matches.
- Foreign-key descriptors: PASS - contract has district and composite school FK descriptors; direct anti-joins found 0 unmatched district keys across 242 keys and 0 unmatched school keys across 3,328 `(district_code, school_code)` keys.
- Schema hash/version consistency: PASS - contract version is `1.0.0`, schema hash is `58b8da2cd1d4898b621e2e8405a632a1ff9897bd69f4c339ba4aa202b0ebe26b`, and contract year metadata covers 2011-2024 with no gaps.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp is newer than `generated_at`, with `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - validation summary is 21 pass, 0 fail, 0 warning.
- Validator warnings explained: N/A - validation reports no warnings.
- §15b quality-check coverage (cross-column invariants authored): PASS - authored checks cover valid family-label pairs, non-negative values, integral headcount labels, bounded experience/contract-day averages, exactly 81 state rows per year, and the complete 27-label grid per geography/employee cell.

## Manifest Verification

- Files processed coverage: PASS - manifest lists all 14 current bronze CSV files with expected eras and row counts; current file inventory and checksums match the bronze structure report.
- Categorical and recode coverage: PASS - `employee_type`, `measure_family`, and `measure_label` mappings cover every observed bronze value, with `unmapped_count: 0` for all three.
- Row-count reconciliation: PASS - manifest reports 3,120,633 bronze rows and 3,120,633 gold rows, with 1.0 expansion factor and 0 filtered rows for every year.
- Metric stats sanity: PASS - `measure_value` has 0 nulls in every year, min 0.0, no negative values, and expected heterogeneous maxima driven by salary rows.

## Row and Join Accounting

- Bronze file/year disposition: PASS - each CSV maps to one data year from `LONG_SCHOOL_YEAR`; years 2011-2024 are all present and no extra bronze source files are unaccounted for.
- Filter accounting: N/A - no rows are filtered; full-row comparison found every bronze row represented in gold.
- Join accounting: N/A - the transform performs no source joins; downstream FK validation and direct anti-joins both pass.
- Deduplication accounting: PASS - raw and zero-padded natural-key duplicate checks found 0 duplicate groups, so the defensive dedup step removes no rows.
- Aggregation/unpivot accounting: PASS - the transform preserves the source's long shape and does not aggregate or unpivot; exact expected-vs-gold comparison found 0 missing rows and 0 extra rows.

## Reconciliation Checks

- Artifact freshness: PASS - transform, manifest, validation, contract, bronze checksums, and gold partitions are mutually current.
- Contract freshness: PASS - contract is emitted from the current transform/gold run; there is no `_metadata.json` dependency.
- Year coverage: PASS - 2011-2024 appear in bronze, manifest, contract `available_years`, and gold.
- Row preservation: PASS - reconstructed expected rows from all bronze CSVs match gold exactly, including detail-file placement.
- Column coverage: PASS - all fact keys, categoricals, and `MEASURE` are represented; name and grade-served metadata are correctly excluded as non-fact attributes.
- Recode accuracy: PASS - all 3 employee types, 7 measure families, and 27 measure labels are semantically correct; `Other *` is preserved as the certificate-level `other` label, not as race.
- Asian-family demographic recodes (§5b): PASS - the source has no Pacific Islander/NHPI split label; bronze `Race/Ethnicity` / `Asian` maps to gold `asian_pacific_islander`, and gold contains no `asian` or `pacific_islander` split label.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): N/A - there is no `demographic` column; staff race is a measure label family, and the race labels use one combined Asian/Pacific Islander convention.
- Demographic collision aggregation before dedup (§5): N/A - no demographic column and no demographic normalization collision path.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS - parquet order is `year`, geography keys, categoricals, then metric.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS - exported parquet contains no forbidden fact-table columns.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - validator's canonical vocabulary check passes; this topic does not emit those specialized columns.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no `grade_level` or `subject` columns.
- Tidy long format (§9 — no demographics/years/components as column names): PASS - source long key-value shape is preserved as `employee_type`, `measure_family`, `measure_label`, `measure_value`; validator tidy-format check passes.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS - direct checks found 0 unmatched district keys and 0 unmatched composite school keys; no demographic FK applies.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - contract roles expose all three categoricals as filters and both education geography joins as FKs.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS - no suppression markers survive, IDs remain strings with leading zeros, aggregate geography keys are NULL, and custom SQL covers the heterogeneous unit exemption.

## Spot Checks

### Check 1

- Bronze: `certified_personnel_2024.csv`, `LONG_SCHOOL_YEAR=2023-24`, district `741`, school `0189`, `EMPLOYEE_TYPE=Support Personnel`, `DATA_CATEGORY=Certificate Level`, `DATA_SUB_CATEGORY=5 Yr Master's`, `MEASURE=3`
- Transform path: `_transform_era()` lines 351-407 maps employee/category/label, derives year, preserves IDs, and casts `MEASURE` to `measure_value`
- Gold: `year=2024/schools.parquet` row `district_code=741`, `school_code=0189`, `employee_type=support_personnel`, `measure_family=certificate_level`, `measure_label=5_yr_masters`, `measure_value=3.0`
- Result: MATCH

### Check 2

- Bronze: `certified_personnel_2022.csv`, `LONG_SCHOOL_YEAR=2021-22`, district `737`, school `8014`, `EMPLOYEE_TYPE=Administrators`, `DATA_CATEGORY=Race/Ethnicity`, `DATA_SUB_CATEGORY=Black`, `MEASURE=0`
- Transform path: `_transform_era()` lines 358-405 recodes `Administrators -> administrators`, `Race/Ethnicity -> race_ethnicity`, `Black -> black`, and casts zero as a real value
- Gold: `year=2022/schools.parquet` row `district_code=737`, `school_code=8014`, `employee_type=administrators`, `measure_family=race_ethnicity`, `measure_label=black`, `measure_value=0.0`
- Result: MATCH

### Check 3

- Bronze: `certified_personnel_2024.csv`, district aggregate row `SCHOOL_DSTRCT_CD=732`, `INSTN_NUMBER=ALL`, `DATA_SUB_CATEGORY=7 Yr Doctoral`, `EMPLOYEE_TYPE=Support Personnel`, `MEASURE=4`
- Transform path: `_transform_era()` lines 351-399 classifies `INSTN_NUMBER=ALL` as district detail and emits `school_code=NULL`; `export_to_parquet()` writes it to `districts.parquet`
- Gold: `year=2024/districts.parquet` row `district_code=732`, `school_code=NULL`, `employee_type=support_personnel`, `measure_family=certificate_level`, `measure_label=7_yr_doctoral`, `measure_value=4.0`
- Result: MATCH

### Check 4

- Bronze: `certified_personnel_2024.csv`, state row `SCHOOL_DSTRCT_CD=ALL`, `INSTN_NUMBER=ALL`, `EMPLOYEE_TYPE=PK-12 Teachers`, `DATA_CATEGORY=Race/Ethnicity`, `DATA_SUB_CATEGORY=Asian`, `MEASURE=2083`
- Transform path: `MEASURE_LABEL_MAP` lines 172-205 maps `Asian -> asian_pacific_islander`; `_transform_era()` lines 351-405 nulls state geography and preserves the value
- Gold: `year=2024/states.parquet` row `district_code=NULL`, `school_code=NULL`, `employee_type=pk_12_teachers`, `measure_family=race_ethnicity`, `measure_label=asian_pacific_islander`, `measure_value=2083.0`
- Result: MATCH

### Check 5

- Bronze: `certified_personnel_2017.csv`, state row `LONG_SCHOOL_YEAR=2016-17`, `EMPLOYEE_TYPE=PK-12 Teachers`, `DATA_CATEGORY=Certified Personnel`, `DATA_SUB_CATEGORY=Professional`, `MEASURE=2689`
- Transform path: `_transform_era()` lines 351-405 preserves the source value; the module docstring and contract document this 2017 family as an extreme-but-conceivable source quirk rather than masking it
- Gold: `year=2017/states.parquet` row `district_code=NULL`, `school_code=NULL`, `employee_type=pk_12_teachers`, `measure_family=certified_personnel`, `measure_label=professional`, `measure_value=2689.0`; same-year sums are districts 2690.0, schools 2748.0, state 2689.0
- Result: MATCH

## Notes

- No collapsed-row formula trace applies because the transform does not aggregate, roll up, or pivot rows; source aggregate rows are preserved as their own state/district observations.
- Independent full-row reconciliation reconstructed the expected gold rows from all bronze CSVs and found `EXPECTED_NOT_IN_GOLD=0` and `GOLD_NOT_IN_EXPECTED=0`.
- The source has no suppression markers in `MEASURE`; all 3,120,633 values parse as numeric, with 0 nonnumeric values and 0 negative values.
- Asian-family check: in 2024 state rows, race-bucket sums versus gender-bucket sums differ by at most 0.0321% across employee types; across all years the max absolute relative difference is 0.0376%, supporting the combined-bucket treatment rather than a dropped NHPI split.
