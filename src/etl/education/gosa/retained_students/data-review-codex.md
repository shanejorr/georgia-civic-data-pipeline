# Data Review: retained_students

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Contract, manifest, validator, bronze inventory, and gold parquet all reconcile; no bronze-to-gold correctness fixes are required.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH — transform mtime 2026-06-12T02:27:19Z, manifest generated_at 2026-06-12T02:27:48Z, validation timestamp 2026-06-12T02:27:48Z; validation is newer than the manifest and reports passed.

## Files Reviewed

- Transform: `src/etl/education/gosa/retained_students/transform.py`
- Contract: `contracts/education/retained_students.odcs.yaml`
- Bronze files: 21 retained_students files, `retained_students_2004.csv` through `retained_students_2024.csv`, plus `bronze-data-structure.md`
- Gold files: 63 parquet files, `year=2004` through `year=2024`, each with `states.parquet`, `districts.parquet`, and `schools.parquet`
- Manifest: `data/gold/education/retained_students/_transform_manifest.json`
- Validation report: `data/gold/education/retained_students/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, data-cleaning standards, education domain conventions, transform/review/fix workflow skills

## Contract Verification

- Schema/parquet column match: PASS — contract properties match actual parquet order exactly: `year`, `district_code`, `school_code`, `demographic`, `retained_count`, `student_count`, `pct_of_retained_cohort`.
- Column roles and grain: PASS — grain is one row per year, geography keys, and demographic; actual gold has zero duplicate grain tuples.
- Metric units and derived quality checks: PASS — `retained_count` and `student_count` are `count`; `pct_of_retained_cohort` is `proportion`; validator confirms non-negative counts and proportion range.
- Categorical enums: PASS — contract demographic enum matches manifest and gold values: `all`, `asian_pacific_islander`, `black`, `female`, `hispanic`, `male`, `multiracial`, `native_american`, `white`.
- Detail levels and layout metadata: PASS — contract lists `schools`, `districts`, `states`; gold has all three files for every year 2004-2024.
- Foreign-key descriptors: PASS — validator and direct checks found 0 missing district, school, or demographic FK values; school FK uses the composite `(district_code, school_code)` key.
- Schema hash/version consistency: PASS — contract version is `1.0.0`, year range is `2004-2024`, and schema hash is present (`f76fa41129994a745d50d5ed9e6535d2e92634cea9feab02b275ff33573de926`).

## Validator Verification

- `_validation.json` fresh + passing: PASS — `passed: true`, timestamp 2026-06-12T02:27:48.962062, newer than manifest generated_at.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS — all checks passed, including `contract_parquet_schema`, `grain_uniqueness`, `contract_quality_sql`, `foreign_keys`, `canonical_vocabulary`, and geography nulling for all three detail levels.
- Validator warnings explained: N/A — validation reports no null-rate spike warnings.
- §15b quality-check coverage (cross-column invariants authored): PASS — contract quality includes retained_count <= student_count, `pct_of_retained_cohort` NULL on `all`, student_count availability constraints, and race/gender partition checks.

## Manifest Verification

- Files processed coverage: PASS — current bronze inventory exactly matches manifest `files_processed` for all 21 source files; `scripts/check_bronze_freshness.py education gosa retained_students` passed all checksums with no unanalyzed files.
- Categorical and recode coverage: PASS — `detail_level` and `demographic` mappings have `unmapped_count: 0`; the effective demographic map records `Asian/Pacific Islander -> asian_pacific_islander`.
- Row-count reconciliation: PASS — manifest totals are 51,005 bronze rows -> 458,559 gold rows. Every year expands by 9x except 2010, where 54 explicit bronze removals (1 malformed SysSchoolid + 53 duplicate SysSchoolid rows) yield 22,068 gold rows.
- Metric stats sanity: PASS — `retained_count` and `student_count` are non-negative, `pct_of_retained_cohort` ranges 0-1, and 2012 `student_count` is manifest-recorded as masked for 2,485 rows due to corrupt enrollment.

## Row and Join Accounting

- Bronze file/year disposition: PASS — 21 source files cover 2004-2024 and all are processed into matching gold years.
- Filter accounting: PASS — only 2010 filters are explicit and source-backed: one malformed `SysSchoolid=" Few Students"` row and 53 duplicate `SysSchoolid` rows, before 9-row demographic expansion.
- Join accounting: N/A — transform performs no merge/join enrichment; FK resolution is validated after export against dimensions.
- Deduplication accounting: PASS — bronze-level 2010 duplicate handling keeps the most complete row per `SysSchoolid`; final natural-key collision guard and validator grain check both pass.
- Aggregation/unpivot accounting: PASS — each source entity expands to one `all` row plus eight demographic rows; no aggregation collapse is performed except 2010 duplicate removal before expansion.

## Reconciliation Checks

- Artifact freshness: PASS — bronze checksums, manifest, validation, contract, and gold are mutually current.
- Contract freshness: PASS — contract is emitted from the current transform/gold path; no `_metadata.json` dependency.
- Year coverage: PASS — actual gold years are 2004-2024 with no gaps or unexpected years.
- Row preservation: PASS — gold row counts match the expected 9x expansion by source entity after documented 2010 filters.
- Column coverage: PASS — all fact keys, metrics, and demographic categoricals described in the bronze profile have a gold disposition; names, grades-served, report-name constants, redundant denominator copies, and 2009 unnamed artifacts are validly excluded.
- Recode accuracy: PASS — `State/District/School` detail levels and all demographic values map correctly; `MultiRacial` and `Multiracial` both map to `multiracial`.
- Asian-family demographic recodes (§5b): PASS — no bronze era publishes a separate Pacific Islander bucket, gold emits `asian_pacific_islander` only, and state-level race sums equal the `all` retained total in every year checked across 2004-2024.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): PASS — gold has no `asian` or `pacific_islander` rows; only the combined `asian_pacific_islander` convention is emitted.
- Demographic collision aggregation before dedup (§5): N/A — source labels plus synthetic `all` map to nine distinct canonical values; no demographic collisions occur.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS — actual parquet order is `year`, `district_code`, `school_code`, `demographic`, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS — no forbidden fact-table columns are present.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS — retained-students uses canonical `student_count` and `pct_of_retained_cohort`; no assessment-specific columns apply.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): PASS — demographics use `normalize_demographic_column`; grade/subject columns are not emitted.
- Tidy long format (§9 — no demographics/years/components as column names): PASS — demographic buckets are rows, not columns.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS — direct anti-join checks found 0 missing district, school, and demographic keys.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS — ODCS roles and FK custom properties match the fact shape and validator output.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS — ID formatting, suppression-to-null, geography nulling, scale, and masking behavior align with the standards.

## Spot Checks

### Check 1

- Bronze: `retained_students_2024.csv`, Appling County district row (`School_District_Code=601`, `School_Code=ALL`): `Total_Enrolled=3237.00000`, `Total_Retained=58`, `Number_of_Black=13`, `Percentage_of_Black=22`, `Number_of_Male=32`, `Percentage_of_Male=55`.
- Transform path: `_transform_tidy()` normalizes era-1 column names, casts counts through `_count_expr()`, divides percentages via `_pct_expr()`, expands through `_melt_to_long()`, and nulls district `school_code`.
- Gold: `year=2024`, `district_code='601'`, `school_code=NULL`: `all.retained_count=58`, `all.student_count=3237`, `black.retained_count=13`, `black.pct_of_retained_cohort=0.22`, `male.retained_count=32`, `male.pct_of_retained_cohort=0.55`.
- Result: MATCH

### Check 2

- Bronze: `retained_students_2007.xls`, `SysSchoolid=601:103`: `Retained_NN=42`, `Retained_TB=21`, `Retained_PB=50`, `Retained_TH=1`, `Retained_PH=2.4`, `Retained_TU=1`, `Retained_PU=2.4`, `Retained_TW=19`, `Retained_PW=45.2`.
- Transform path: `_transform_wide_v1()` treats `Retained_NN` as total retained, maps suffix `U` to `Multiracial`, zfills school code to `0103`, and expands to demographic rows.
- Gold: `year=2007`, `district_code='601'`, `school_code='0103'`: `all=42`, `black=21/0.5`, `hispanic=1/0.024`, `multiracial=1/0.024`, `white=19/0.452`.
- Result: MATCH

### Check 3

- Bronze: `retained_students_2009.xls`, state row: `Retained Total Students=61642`, `Retained Total White=20064`, published `Retained Percent White=61.1`; `Retained Total Multiracial=1584`, published `Retained Percent Multiracial=61.1`; `Retained Percent Male=61.1`.
- Transform path: `_transform_wide_v2()` recognizes the 2009 corrupted White/Multiracial percent columns and derives percentage as `count / Retained Total Students`.
- Gold: state 2009 `white.pct_of_retained_cohort=0.325492` and `multiracial.pct_of_retained_cohort=0.025697`, while `male.pct_of_retained_cohort=0.611`.
- Result: MATCH

### Check 4

- Bronze: `retained_students_2012.xlsx`, state row: `Total Enrolled=27864309`, `Total Retained=56406`, `Number of Asians=1043`, `Percentage of Asians=2`.
- Transform path: `_null_corrupt_2012_student_count()` masks 2012 `student_count` after harmonization/dedup/geography nulling and records 2,485 masked values in the manifest.
- Gold: state 2012 `all.retained_count=56406`, `all.student_count=NULL`, `asian_pacific_islander.retained_count=1043`, `asian_pacific_islander.pct_of_retained_cohort=0.02`.
- Result: MATCH

### Check 5

- Bronze: `retained_students_2022.csv`, rows for districts `7830627` and `7830636` have `Data Reporting Level=School` with `School Code=ALL`.
- Transform path: `_transform_tidy()` reclassifies School+ALL sentinel rows to district detail and records `reclassified` count 2 for 2022.
- Gold: `year=2022`, `district_code='7830627'`, `school_code=NULL` exists at district grain with `student_count=123` on the `all` row.
- Result: MATCH

### Check 6

- Bronze: `retained_students_2010.csv`, one malformed `SysSchoolid` row lacks `:`, and `SysSchoolid=746:4050` appears twice with one less complete twin.
- Transform path: `_filter_malformed_sysschoolid()` removes the malformed row; `_dedup_bronze_duplicates()` keeps the most complete duplicate before expansion.
- Gold: manifest records 54 explicit filtered rows in 2010; 2010 gold row count is 22,068, equal to `(2506 - 54) * 9`.
- Result: MATCH

## Notes

- No prior `data-review-claude.md` or existing `data-review-codex.md` was used to drive findings.
- Review is read-only except for writing this report.
- Local git status shows this topic's transform, contract, gold, and report are untracked in the current worktree; the audit treated the on-disk artifacts as the current pipeline output.
