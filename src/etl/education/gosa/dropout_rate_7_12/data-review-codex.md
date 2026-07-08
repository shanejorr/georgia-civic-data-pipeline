# Data Review: dropout_rate_7_12

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze, transform, contract, validator, manifest, and gold output reconcile cleanly; no must-fix bronze-to-gold accuracy defects were found.

## Summary

- Review date: 2026-06-10
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - `scripts/check_bronze_freshness.py education gosa dropout_rate_7_12` passed; `transform.py` mtime is 2026-06-10T16:34:01.619872+00:00, manifest `generated_at` is 2026-06-10T16:34:02.871866+00:00, and validation timestamp is 2026-06-10T16:34:02.936813+00:00.

## Files Reviewed

- Transform: `src/etl/education/gosa/dropout_rate_7_12/transform.py`
- Contract: `contracts/education/dropout_rate_7_12.odcs.yaml`
- Bronze files: 14 CSV files, `dropout_rate_7_12_2011.csv` through `dropout_rate_7_12_2024.csv`
- Gold files: 42 parquet files, `year=2011` through `year=2024`, each with `districts.parquet`, `schools.parquet`, and `states.parquet`
- Manifest: `data/gold/education/dropout_rate_7_12/_transform_manifest.json`
- Validation report: `data/gold/education/dropout_rate_7_12/_validation.json`
- Supporting docs: `STATUS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`, `docs/contract-creation.md`, `docs/codex-review-contract.md`, data-cleaning standards, transform-topic, data-review, fix-from-reviews, full-pipeline, and bronze-data-structure skills

## Contract Verification

- Schema/parquet column match: PASS - contract properties are `year`, `district_code`, `school_code`, `demographic`, `dropout_count`, `dropout_rate`; all 42 parquet files have the same columns in that order.
- Column roles and grain: PASS - roles are `year`, `fk_district`, `fk_school`, `fk_demographic`, `metric`, `metric`; grain is `year`, `district_code`, `school_code`, `demographic`, matching the gold natural key across detail files.
- Metric units and derived quality checks: PASS - `dropout_count` is `unit: count` with non-negative quality SQL; `dropout_rate` is `unit: proportion` with `[0, 1]` quality SQL. Topic quality checks cover co-suppression, state non-suppression, count threshold, race and gender state partitions, and 2020-2022 English-learner absence.
- Categorical enums: PASS - `demographic` enum contains the 15 canonical keys produced by gold; 2020-2022 correctly omit `english_learners` rows while the contract permits the cross-year vocabulary.
- Detail levels and layout metadata: PASS - contract declares `schools`, `districts`, `states`, default `schools`, partition column `year`, and path template `education/dropout_rate_7_12/year={year}/{detail}.parquet`.
- Foreign-key descriptors: PASS - contract declares `district_code -> districts`, composite `school_code -> schools` on `district_code, school_code`, and `demographic -> demographics`.
- Schema hash/version consistency: PASS - contract version is `1.0.0`; custom properties carry `year_range: 2011-2024`, `available_years` 2011-2024 with no gaps, and `schema_hash: 3fc2466c7ccb0dbe743f50879e78d5cf39c1f6c2494810b608855754f0551466`.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp 2026-06-10T16:34:02.936813+00:00 is newer than manifest `generated_at` 2026-06-10T16:34:02.871866+00:00, with `"passed": true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 21 pass, 0 fail, 0 warning. The report includes passing `contract_parquet_schema`, `grain_uniqueness`, `contract_quality_sql`, `foreign_keys`, and `canonical_vocabulary`.
- Validator warnings explained: N/A - validation has zero warnings.
- section 15b quality-check coverage (cross-column invariants authored): PASS - authored quality SQL covers co-suppression, `dropout_count >= 10` when published, unsuppressed state rows, race/gender state count reconciliation, and the 2020-2022 English-learner gap. No aggregation-derived district/state rows are computed by the transform.

## Manifest Verification

- Files processed coverage: PASS - manifest lists all 14 current bronze CSV files. The freshness gate confirms all 14 checksums match `bronze-data-structure.md` and no unanalyzed files exist.
- Categorical and recode coverage: PASS - `detail_level` and `demographic` both have `unmapped_count: 0`. Manifest maps `Asian/Pacific Islander -> asian_pacific_islander`, `American Indian/Alaskan -> native_american`, `Multi-Racial -> multiracial`, `Students With Disability -> students_with_disabilities`, and all other observed labels to the expected canonical keys.
- Row-count reconciliation: PASS - total bronze rows 250,292 equal total gold rows 250,292. Every year has expansion factor 1.0 and filtered count 0.
- Metric stats sanity: PASS - final gold ranges are `dropout_count` min 10, max 24,061 and `dropout_rate` min 0.002, max 0.936; null counts match between count and rate (199,820 each), proving co-suppression.

## Row and Join Accounting

- Bronze file/year disposition: PASS - files span 2011-2024; `LONG_SCHOOL_YEAR` agrees with filename year for each file; era 1 is 2023-2024 and era 2 is 2011-2022.
- Filter accounting: N/A - the transform does not filter rows. It reclassifies 28 source rows in 2022 but preserves them, so bronze and gold row counts remain equal.
- Join accounting: N/A - the transform performs no joins or lookups. Downstream FK resolution is covered by validation and passes for 242 district keys, 1,191 composite school keys, and 15 demographic keys.
- Deduplication accounting: PASS - the transform runs the collision guard and dedup safety net, but the null-safe full reconciliation found 0 duplicate expected keys and 0 duplicate gold keys; no rows were removed.
- Aggregation/unpivot accounting: N/A - the source is already long at one row per year/geography/demographic. The only formula-level transformation is scaling `PROGRAM_PERCENT / 100` to `dropout_rate`.

## Reconciliation Checks

- Artifact freshness: PASS - `check_bronze_freshness.py` passed, manifest is newer than `transform.py`, and validation is newer than manifest.
- Contract freshness: PASS - current contract matches current parquet columns and validation consumed it successfully; there is no `_metadata.json` dependency.
- Year coverage: PASS - bronze, manifest, contract available years, and gold partitions all cover 2011-2024 with no gaps.
- Row preservation: PASS - independent null-safe bronze-derived expected table had 250,292 rows; gold had 250,292 rows; join by `year`, `district_code`, `school_code`, `demographic`, and detail level found 250,292 matches, 0 missing keys, 0 extra keys, and 0 value mismatches.
- Column coverage: PASS - fact keys `LONG_SCHOOL_YEAR`, `SCHOOL_DSTRCT_CD`, `INSTN_NUMBER`, and `LABEL_LVL_1_DESC` map to `year`, `district_code`, `school_code`, and `demographic`; metrics `PROGRAM_TOTAL` and `PROGRAM_PERCENT` map to `dropout_count` and `dropout_rate`; names and `GRADES_SERVED_DESC` are correctly excluded as dimension/metadata fields.
- Recode accuracy: PASS - `State`, `District`, `School` map to `state`, `district`, `school`; all 15 observed demographic labels map to the intended canonical keys with no fallback values.
- Asian-family demographic recodes (section 5b): PASS - bronze publishes explicit `Asian/Pacific Islander` and no split Pacific Islander row. State-level race-bucket counts equal the `all` count in every year 2011-2024; gold emits `asian_pacific_islander` and has 0 rows for `asian` or `pacific_islander`.
- Demographic mutual exclusivity (section 5a - no rollup row alongside split source rows in the same category): PASS - gold race values use the combined convention only: `asian_pacific_islander`, `black`, `hispanic`, `multiracial`, `native_american`, and `white`; split `asian` and `pacific_islander` are absent.
- Demographic collision aggregation before dedup (section 5): N/A - 15 raw labels map to 15 distinct canonical keys; no raw demographic collisions exist.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - parquet order is `year`, `district_code`, `school_code`, `demographic`, `dropout_count`, `dropout_rate`.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, sections 11/12): PASS - gold parquet excludes `topic`, `detail_level`, `school_year`, `district_name`, `school_name`, `district_census_id`, `GRADES_SERVED_DESC`, and report-name fields.
- Canonical column vocabulary (section 16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - `dropout_count` and `dropout_rate` are semantically appropriate; no forbidden vocabulary variants appear.
- Shared categorical utilities applied (section 10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no `grade_level` or `subject` column exists. Demographics use the shared `normalize_demographic_column`.
- Tidy long format (section 9 - no demographics/years/components as column names): PASS - demographic is a row key; years are partitions; there are no wide demographic or year columns.
- FK keys present in dimension tables (section 13 - `district_code`, `school_code`, `demographic`): PASS - validator reports all 242 district keys, all 1,191 composite school keys, and all 15 demographic keys resolve.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - grain and FK descriptors are contract-derived and coherent; `demographic` enum and FK allow API consumers to filter and join correctly.
- Standards compliance (catch-all for sections 1-16 items not enumerated above): PASS - IDs are strings with leading zeros preserved, aggregate geography keys are null, suppression markers become null, rate scale is 0-1, and metric units match contract semantics.

## Spot Checks

### Check 1

- Bronze: `data/bronze/education/gosa/dropout_rate_7_12/dropout_rate_7_12_2024.csv`, state row `LONG_SCHOOL_YEAR=2023-24`, `LABEL_LVL_1_DESC=7-12 Drop Outs -ALL Students`, `PROGRAM_TOTAL=20203`, `PROGRAM_PERCENT=2.3`.
- Transform path: `transform.py:375-387` validates year, `transform.py:420-431` nulls aggregate geography and divides percent by 100.
- Gold: `data/gold/education/dropout_rate_7_12/year=2024/states.parquet` row has `year=2024`, `district_code=NULL`, `school_code=NULL`, `demographic=all`, `dropout_count=20203`, `dropout_rate=0.023`.
- Result: MATCH

### Check 2

- Bronze: `dropout_rate_7_12_2024.csv`, Redan Middle School row `SCHOOL_DSTRCT_CD=644`, `INSTN_NUMBER=0205`, `LABEL_LVL_1_DESC=7-12 Drop Outs -Black`, `PROGRAM_TOTAL=20`, `PROGRAM_PERCENT=4.7`.
- Transform path: `transform.py:410-431` maps demographic/geography and scales the rate.
- Gold: `year=2024/schools.parquet` row has `district_code=644`, `school_code=0205`, `demographic=black`, `dropout_count=20`, `dropout_rate=0.047`.
- Result: MATCH

### Check 3

- Bronze: `dropout_rate_7_12_2011.csv`, Sandy Creek High School row `SCHOOL_DSTRCT_CD=656`, `INSTN_NUMBER=0192`, `LABEL_LVL_1_DESC=7-12 Drop Outs -Migrant`, `PROGRAM_TOTAL=NULL`, `PROGRAM_PERCENT=NULL`.
- Transform path: `transform.py:223-239` casts null/suppressed metrics with `strict=False`, preserving nulls.
- Gold: `year=2011/schools.parquet` row has `district_code=656`, `school_code=0192`, `demographic=migrant`, `dropout_count=NULL`, `dropout_rate=NULL`.
- Result: MATCH

### Check 4

- Bronze: `dropout_rate_7_12_2022.csv` has 28 rows labeled `DETAIL_LVL_DESC=School` with `INSTN_NUMBER=ALL`: 14 for `7830627` State Charter Schools II- Atlanta SMART Academy and 14 for `7830636` State Charter Schools II- Northwest Classical Academy.
- Transform path: `transform.py:268-306` reclassifies any `School` row with `INSTN_NUMBER=ALL` to district detail and records the event in the manifest.
- Gold: `year=2022/districts.parquet` contains the rows with `district_code=7830627` and `7830636`, `school_code=NULL`; `year=2022/schools.parquet` has 0 rows for those districts with `school_code=NULL`.
- Result: MATCH

### Check 5

- Bronze: state-level race counts use the explicit `Asian/Pacific Islander` label and six race buckets. The race-bucket `dropout_count` sum equals the `ALL Students` count in every year; examples include 2011 `21325 = 21325`, 2022 `23013 = 23013`, and 2024 `20203 = 20203`.
- Transform path: `transform.py:309-339` normalizes demographics through the shared alias map; `transform.py:744-763` authors the race partition quality SQL.
- Gold: state rows emit `asian_pacific_islander`, never `asian` or `pacific_islander`; the contract quality check `state_race_partition_sums_to_all` passes.
- Result: MATCH

## Notes

- Prior review report contents were not read before forming this verdict.
- The full-row reconciliation used null-safe key matching because district and state aggregate rows intentionally have null lower-level geography keys.
- No must-fix items were found, so this PASS report intentionally omits a required-fixes section.
