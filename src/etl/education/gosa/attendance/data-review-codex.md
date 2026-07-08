# Data Review: attendance

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze-to-gold coverage, recodes, row counts, metric scales, special repairs, contract metadata, and current gold parquet all reconcile; no transform accuracy fixes are required.

## Summary

- Review date: 2026-06-10
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH — bronze freshness gate passed for all 21 files; transform mtime `2026-06-10T18:14:00.728558+00:00`, manifest `generated_at` `2026-06-10T18:16:12.513480+00:00`, validation timestamp `2026-06-10T18:16:12.644815+00:00`, validation `passed: true`.

## Files Reviewed

- Transform: `src/etl/education/gosa/attendance/transform.py`
- Contract: `contracts/education/attendance.odcs.yaml`
- Bronze files: 21 files, `attendance_2004.csv` through `attendance_2024.csv`; current row counts and columns match `files_processed`; checksum gate passed.
- Gold files: 63 parquet files, `year=2004` through `year=2024`, each with `schools.parquet`, `districts.parquet`, and `states.parquet`.
- Manifest: `data/gold/education/attendance/_transform_manifest.json`
- Validation report: `data/gold/education/attendance/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`, and relevant shared utility code.

## Contract Verification

- Schema/parquet column match: PASS — every parquet file has exactly `year`, `district_code`, `school_code`, `demographic`, `student_count`, `five_or_fewer_days_absent_rate`, `six_to_fifteen_days_absent_rate`, `over_15_days_absent_rate`, `chronically_absent_rate`, matching `schema[0].properties[]`.
- Column roles and grain: PASS — roles are coherent (`year`, `fk_district`, `fk_school`, `fk_demographic`, metrics); grain is `year + district_code + school_code + demographic`, with aggregate geography nulling.
- Metric units and derived quality checks: PASS — `student_count` is `count`; all four rates are `proportion`; the contract includes non-negative and `[0,1]` checks plus attendance-specific invariants.
- Categorical enums: PASS — contract demographic enum equals actual gold values: `all`, `asian_pacific_islander`, `black`, `economically_disadvantaged`, `english_learners`, `female`, `hispanic`, `male`, `migrant`, `multiracial`, `native_american`, `not_economically_disadvantaged`, `students_with_disabilities`, `students_without_disabilities`, `white`.
- Detail levels and layout metadata: PASS — `detail_levels` are `schools`, `districts`, `states`; default detail is `schools`; path template is `education/attendance/year={year}/{detail}.parquet`.
- Foreign-key descriptors: PASS — district, composite school, and demographic FK descriptors are present and match dimension contracts.
- Schema hash/version consistency: PASS — version is `1.0.0`; schema hash is `16ed7214c48f5ee3b1234fce5087258ee2c3c19743a945fc7273a07afce22ab9`; year range is `2004-2024` with no gaps.

## Validator Verification

- `_validation.json` fresh + passing: PASS — validation timestamp is after manifest generation and `passed` is `true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS — validation summary is 20 pass, 0 fail, 1 warning; `contract_parquet_schema`, `grain_uniqueness`, `contract_quality_sql`, `foreign_keys`, and `canonical_vocabulary` all pass.
- Validator warnings explained: PASS — `student_count` null-rate spikes in 2021-2024 match the documented GOSA `TFS`/blank suppression regime; direct gold rates are 23.4%, 22.7%, 22.5%, and 22.4%.
- §15b quality-check coverage (cross-column invariants authored): PASS — contract enforces tier partitioning, state race and gender partitions, the 2013 race-count gap, zero-population rate nulling, and chronic-rate nulling through 2017.

## Manifest Verification

- Files processed coverage: PASS — all 21 current bronze files appear in `files_processed` with matching rows, years, eras, and column lists; no manifest-only files or unanalyzed files exist.
- Categorical and recode coverage: PASS — manifest records `demographic` and `detail_level`; both have `unmapped_count: 0`; `ASIAN` maps to `asian_pacific_islander`.
- Row-count reconciliation: PASS — total bronze rows are 51,238 and total gold rows are 768,195. Ordinary years expand by exactly 15 demographic rows; 2004 drops 23 corrupt source rows before expansion; 2009 drops 30 post-unpivot duplicate rows.
- Metric stats sanity: PASS — `student_count` is non-negative; all rate metrics are within `[0,1]`; `chronically_absent_rate` is fully null through 2017 and populated from 2018 forward as documented.

## Row and Join Accounting

- Bronze file/year disposition: PASS — every bronze file from 2004-2024 is processed once, with year from filename for wide eras and cross-checked `LONG_SCHOOL_YEAR` for 2011-2024.
- Filter accounting: PASS — explicit filters are documented: 2004 corrupt trailing block (`1` unkeyable row + `22` duplicate re-paste rows) and 2009 duplicate republished rows (`30` gold-grain rows).
- Join accounting: N/A — transform performs no data joins or lookup enrichments; FK validation against dimensions passes after export.
- Deduplication accounting: PASS — duplicate 2009 district aggregate keys `768:ALL` and `770:ALL` carry identical metrics; dedup removes `2 keys x 15 demographics = 30` rows.
- Aggregation/unpivot accounting: PASS — no aggregation is used; wide and tidy source rows are reshaped to 15 demographic rows per entity. Detail-level counts match source row counts times 15 after documented repairs.

## Reconciliation Checks

- Artifact freshness: PASS — bronze checksum gate, manifest, validation, contract, and gold layout are internally current.
- Contract freshness: PASS — contract was emitted from current transform/gold; no `_metadata.json` dependency was used.
- Year coverage: PASS — gold covers every year 2004-2024 and no extra years.
- Row preservation: PASS — row ledger reconciles by year; no unexplained row loss or multiplication.
- Column coverage: PASS — every `fact_key`, `fact_metric`, and `fact_categorical` from the structure report has a disposition; names, grade spans, `#RPT_NAME`, and detail labels are correctly excluded from the fact table.
- Recode accuracy: PASS — all demographic aliases and detail-level recodes are semantically correct and manifest-covered.
- Asian-family demographic recodes (§5b): PASS — actual bronze columns/values contain no Pacific Islander, Native Hawaiian, or NHPI label; gold has `asian_pacific_islander` rows and zero `asian`/`pacific_islander` rows. State race sums equal `all` in 20 years and have the documented 2013 gap of 8.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): PASS — the topic uses only the combined Asian/PI convention; no split race rows coexist with it.
- Demographic collision aggregation before dedup (§5): PASS — no same-file raw demographic collision creates duplicate natural keys after normalization; final duplicate grain count is 0.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS — actual parquet order matches the contract and standard order.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS — parquet contains no forbidden fact-table columns; `detail_level` is encoded by filename.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS — attendance rate columns use `_rate` and no non-applicable vocabulary appears.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A — no `grade_level` or `subject`; demographics use `normalize_demographic_column`.
- Tidy long format (§9 — no demographics/years/components as column names): PASS — final data is long by `demographic`; no wide demographic metric columns remain.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS — all 252 district keys, 2,911 composite school keys, and 15 demographic keys resolve.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS — grain, enum, FK descriptors, and layout metadata are coherent with registry/API expectations.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS — percentage scale, suppression handling, geography nulling, natural keys, and manifest completeness are all supported by artifacts.

## Spot Checks

### Check 1

- Bronze: `attendance_2006.csv` (actual XLS) row `SysSchoolID=601:103`, Appling County High School: `Number of Students All=954`, `5 or Fewer=45.2`, `6 to 15=38.1`, `More than 15=16.8`; Asian row has `Number of Students Asian=5`, `100`, `0`, `0`.
- Transform path: wide unpivot and scaling in `src/etl/education/gosa/attendance/transform.py:489`; Asian/PI remap in `src/etl/education/gosa/attendance/transform.py:384`.
- Gold: `year=2006/schools.parquet` has `601/0103/all` with `954`, `0.452`, `0.381`, `0.168`, `chronically_absent_rate=NULL`; `601/0103/asian_pacific_islander` has `5`, `1.0`, `0.0`, `0.0`.
- Result: MATCH

### Check 2

- Bronze: `attendance_2011.csv` row `LONG_SCHOOL_YEAR=2010-11`, `DETAIL_LVL_DESC=School`, `SCHOOL_DSTRCT_CD=601`, `INSTN_NUMBER=0103`: `STUDENT_COUNT_ALL=991`, rates `27.5`, `46.3`, `26.1`, `CHRONIC_ABSENT_PERC_ALL=NULL`.
- Transform path: tidy suffix melt and year cross-check in `src/etl/education/gosa/attendance/transform.py:637` and `src/etl/education/gosa/attendance/transform.py:773`.
- Gold: `year=2011/schools.parquet` has `601/0103/all` with `991`, `0.275`, `0.463`, `0.261`, `chronically_absent_rate=NULL`.
- Result: MATCH

### Check 3

- Bronze: raw `attendance_2022.csv` row `601/0103`, Appling County High School has `STUDENT_COUNT_ASIAN=TFS` and all Asian rate/chronic fields `TFS`.
- Transform path: suppression read handling in `src/etl/education/gosa/attendance/transform.py:753`; tidy melt in `src/etl/education/gosa/attendance/transform.py:710`; Asian/PI remap in `src/etl/education/gosa/attendance/transform.py:384`.
- Gold: `year=2022/schools.parquet` has `601/0103/asian_pacific_islander` with all five metrics NULL.
- Result: MATCH

### Check 4

- Bronze: `attendance_2024.csv` includes six school rows with `STUDENT_COUNT_FEMALE=0` and non-zero female rates; e.g. `604/0183` Baker County Learning Academy has `OVER_15_PERCENT_FEMALE=100` and `CHRONIC_ABSENT_PERC_FEMALE=100`.
- Transform path: impossible zero-count mask in `src/etl/education/gosa/attendance/transform.py:845`.
- Gold: `year=2024/schools.parquet` has `604/0183/female` with `student_count=NULL`, `over_15_days_absent_rate=1.0`, and `chronically_absent_rate=1.0`.
- Result: MATCH

### Check 5

- Bronze: `attendance_2022.csv` has two rows with `DETAIL_LVL_DESC=School` and `INSTN_NUMBER=ALL`: districts `7830627` and `7830636`, with all-student counts `144` and `542`.
- Transform path: aggregate sentinel reclassification in `src/etl/education/gosa/attendance/transform.py:584`.
- Gold: `year=2022/districts.parquet` has district-level rows `7830627/all` and `7830636/all`, `school_code=NULL`, counts `144` and `542`, and scaled rates matching bronze.
- Result: MATCH

### Check 6

- Bronze: `attendance_2004.csv` has a trailing corrupt block starting at row index `2220`: one blank-key row and 22 keyed rows whose keys already occurred earlier; `attendance_2009.xls` has duplicate aggregate keys `768:ALL` and `770:ALL` with identical metrics.
- Transform path: corrupt block drop in `src/etl/education/gosa/attendance/transform.py:424`; collision guard and dedup in `src/etl/education/gosa/attendance/transform.py:911`.
- Gold: 2004 gold has `(2243 - 23) * 15 = 33,300` rows; 2009 gold has `(2417 * 15) - 30 = 36,225` rows. No duplicate natural-key groups remain.
- Result: MATCH

## Notes

- I did not read any prior `data-review-claude.md` or `data-review-codex.md` before completing these findings.
- No repo files were changed except this report.
