# Data Review: enrollment_march_gender_race_ethnicity

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: current bronze, manifest, validation, contract, and gold parquet reconcile; no must-fix bronze-to-gold accuracy defects found.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - `transform.py` mtime `2026-06-12T16:28:03Z`, manifest `generated_at` `2026-06-12T16:28:10Z`, validation timestamp `2026-06-12T16:28:10Z`; validation passed.

## Files Reviewed

- Transform: `src/etl/education/georgiainsights/enrollment_march_gender_race_ethnicity/transform.py`
- Shared lookup: `src/etl/education/georgiainsights/_enrollment_race_lookups.py`
- Contract: `contracts/education/enrollment_march_gender_race_ethnicity.odcs.yaml`
- Bronze files: 32 CSV files, 2010-2025, District + School per year; all current checksums match `bronze-data-structure.md`.
- Gold files: 48 parquet files, `year=2010` through `year=2025`, each with `states.parquet`, `districts.parquet`, and `schools.parquet`.
- Manifest: `data/gold/education/enrollment_march_gender_race_ethnicity/_transform_manifest.json`
- Validation report: `data/gold/education/enrollment_march_gender_race_ethnicity/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`.

## Contract Verification

- Schema/parquet column match: PASS - contract properties exactly match parquet order: `year`, `district_code`, `school_code`, `race`, `gender`, `student_count`.
- Column roles and grain: PASS - roles are `year`, `fk_district`, `fk_school`, `categorical`, `categorical`, `metric`; grain is `(year, district_code, school_code, race, gender)`.
- Metric units and derived quality checks: PASS - `student_count` has `unit: count`; contract includes non-negative and suppression-floor SQL checks.
- Categorical enums: PASS - contract enums match manifest and gold distinct values: race has seven split race/ethnicity values; gender has `female`, `male`.
- Detail levels and layout metadata: PASS - contract lists `schools`, `districts`, `states`, `path_template`, `available_years` 2010-2025, and no year gaps.
- Foreign-key descriptors: PASS - `district_code` and composite school FK descriptors are present; validator resolved 250 district keys and 2705 school composite keys.
- Schema hash/version consistency: PASS - version `1.0.0`, schema hash `1cdd6e5ae6719bfdf75e40e5470b8dbf10b209d491c22b9bf2eb6a1019c57ab2`.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp is after manifest generation and reports `"passed": true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 21 pass, 0 fail, 0 warning; `contract_parquet_schema`, `grain_uniqueness`, `contract_quality_sql`, `foreign_keys`, and `canonical_vocabulary` all passed.
- Validator warnings explained: N/A - no warnings.
- §15b quality-check coverage (cross-column invariants authored): PASS - contract checks enforce count non-negativity, suppression floor, no suppressed state rows, and exactly 14 state race x gender rows per year.

## Manifest Verification

- Files processed coverage: PASS - all 32 current CSVs are in `files_processed`, years 2010-2025; no extra or missing current bronze files.
- Categorical and recode coverage: PASS - `gender` and `race` mappings have `unmapped_count: 0`; actual bronze values match map coverage after the documented `Total` gender filter.
- Row-count reconciliation: PASS - manifest has `total_bronze=120336`, `total_gold=561344`, and explicit filtered events for 40112 dropped gender-total rows plus 224 duplicate state rows.
- Metric stats sanity: PASS - `student_count` is `Int64`; gold min non-null is 15, max is 383296, and nulls reflect source `*` suppression.

## Row and Join Accounting

- Bronze file/year disposition: PASS - every profiled CSV is processed once; file checksums match the bronze structure report.
- Filter accounting: PASS - `Gender == "Total"` rows are explicitly dropped as redundant with Female + Male; 40112 rows recorded. Duplicate state rows from District/School files are explicitly recorded; 224 rows.
- Join accounting: N/A - transform performs no data joins or lookups; FK resolution is validator-checked after export.
- Deduplication accounting: PASS - only duplicate natural keys are identical state-row twins from District and School files; no divergent duplicates and final natural-key duplicate count is 0.
- Aggregation/unpivot accounting: PASS - wide seven race/ethnicity columns are unpivoted to long rows; expected row formula `14 * (district entities + school entities + 1)` matches actual gold for all 16 years.

## Reconciliation Checks

- Artifact freshness: PASS - manifest, contract, validation, and parquet are from the current transform run.
- Contract freshness: PASS - contract emitted from current transform/gold; no `_metadata.json` dependency.
- Year coverage: PASS - bronze, manifest, contract, and gold all cover 2010-2025 with no gaps.
- Row preservation: PASS - per-year gold counts match derived source shape exactly, including dropped total rows and deduped state twins.
- Column coverage: PASS - source fact keys/categoricals/metrics map to `year`, `district_code`, `school_code`, `race`, `gender`, `student_count`; names are excluded as dimension attributes.
- Recode accuracy: PASS - race map preserves split `asian` and `pacific_islander`; `Ethnic Hispanic` is treated as a non-overlapping partition bucket; gender maps Female/Male and drops Total.
- Asian-family demographic recodes (§5b): PASS - bronze has separate `Race Asian` and `Race Pacific Islander` columns in every file; gold emits split `asian` and `pacific_islander` and no `asian_pacific_islander` rollup.
- Demographic mutual exclusivity (§5a - no rollup row alongside split source rows in the same category): PASS - race values are the seven source partition buckets only; no combined Asian/Pacific Islander row is present.
- Demographic collision aggregation before dedup (§5): N/A - this cross-classified topic uses `race` and `gender` categoricals, not a single `demographic` column; race columns map 1:1.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS - actual order is `year`, geography FKs, race/gender categoricals, metric, matching the domain exception for race x gender cross-classifications.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS - parquet contains no forbidden fact-table columns.
- Canonical column vocabulary (§16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): N/A - none of those column families apply; `race` + `gender` follows the education domain convention for this topic.
- Shared categorical utilities applied (§10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no grade or subject columns.
- Tidy long format (§9 - no demographics/years/components as column names): PASS - wide race columns are unpivoted; gold has one `race` categorical and one `student_count` metric.
- FK keys present in dimension tables (§13 - `district_code`, `school_code`, `demographic`): PASS - validator resolved all district and composite school keys; race/gender values also exist in the demographics dimension vocabulary.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - contract exposes `race` and `gender` as independent categorical filters and FKs derive from contract metadata.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS - IDs are strings with leading zeros preserved, suppression markers become null, counts are non-negative, and output is year-partitioned with no empty parquet files.

## Spot Checks

### Check 1

- Bronze: 2025 School CSV state Female row has `Race Black=309028`.
- Transform path: `_read_bronze_csv()` skips the preamble and nulls `*`; `_transform_file_frame()` drops `Total`, maps `Female -> female`, unpivots `Race Black`, and maps it to `race=black` (`transform.py:189-378`).
- Gold: `year=2025`, state row, `race=black`, `gender=female`, `student_count=309028`.
- Result: MATCH

### Check 2

- Bronze: 2025 District CSV Appling County (`System ID=601`) Male row has `Race White=989`.
- Transform path: district rows keep `district_code='601'`, `school_code=NULL`, map `Male -> male`, unpivot `Race White -> white` (`transform.py:287-378`).
- Gold: `year=2025`, `district_code='601'`, `school_code=NULL`, `race=white`, `gender=male`, `student_count=989`.
- Result: MATCH

### Check 3

- Bronze: 2025 School CSV Oak Grove Elementary (`System ID=644`, `School ID=3063-Oak Grove Elementary School`) Male row has `Ethnic Hispanic=20`, `Race Asian=22`, `Race Black=32`, `Race White=154`, `Two or more Races=21`.
- Transform path: school code regex extracts `3063`, race columns unpivot, and strict map emits `hispanic`, `asian`, `black`, `white`, `multiracial` (`transform.py:332-378`).
- Gold: matching rows for `district_code='644'`, `school_code='3063'`, `gender=male` have counts 20, 22, 32, 154, and 21 for those five race values.
- Result: MATCH

### Check 4

- Bronze: 2025 School CSV Northeast Middle School (`System ID=737`, `School ID=3052-Northeast Middle School`) Male row has `Race Asian=*`, `Race AmericanIndian=*`, `Race Pacific Islander=*`, `Two or more Races=*`, plus `Ethnic Hispanic=89`, `Race Black=131`, `Race White=121`.
- Transform path: `_read_bronze_csv()` registers `*` as null; count casts use `strict=False`; unpivot preserves nulls per cell (`transform.py:223-228`, `transform.py:342-378`).
- Gold: matching `district_code='737'`, `school_code='3052'`, `gender=male` rows have null counts for `asian`, `native_american`, `pacific_islander`, and `multiracial`; counts 89, 131, 121 for `hispanic`, `black`, `white`.
- Result: MATCH

### Check 5

- Bronze: 2025 state rows in both District and School CSVs are identical; Female + Male equals Total for each of the seven race/ethnicity columns.
- Transform path: drops `Gender == "Total"` before unpivot, then deduplicates identical state twins after collision guard (`transform.py:295-305`, `transform.py:441-474`).
- Gold: 2025 state output has exactly 14 rows, two genders by seven race values, and no `gender=total`.
- Result: MATCH

## Notes

- No required fixes. The bronze structure report contains a correction noting that the original schema-classification table used `demographic`, but the current domain convention and actual gold correctly use separate `race` and `gender` columns for this cross-classified topic.
