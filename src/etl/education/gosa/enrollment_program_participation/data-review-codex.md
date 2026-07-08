# Data Review: enrollment_program_participation

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: the current gold output reconciles to the shared GOSA enrollment-by-subgroup/programs bronze for all 314,190 program rows, with no required transform fixes.

## Summary

- Review date: 2026-06-11
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - `transform.py` and the shared bronze helper both predate `_transform_manifest.json`; `_validation.json` timestamp is after the manifest `generated_at`; all 21 shared bronze file checksums still match `bronze-data-structure.md`.

## Files Reviewed

- Transform: `src/etl/education/gosa/enrollment_program_participation/transform.py`
- Shared source helper: `src/etl/education/gosa/_enrollment_subgroup_programs_shared.py`
- Contract: `contracts/education/enrollment_program_participation.odcs.yaml`
- Bronze files: 21 files in `data/bronze/education/gosa/enrollment_by_subgroup_programs/`; 2011-2024 feed this derived topic and 2004-2010 are intentionally excluded because they publish no program columns.
- Gold files: 42 parquet files under `data/gold/education/enrollment_program_participation/year=2011` through `year=2024`, with `schools.parquet`, `districts.parquet`, and `states.parquet` for every year.
- Manifest: `data/gold/education/enrollment_program_participation/_transform_manifest.json`
- Validation report: `data/gold/education/enrollment_program_participation/_validation.json`
- Supporting docs: `STATUS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`, `docs/contract-creation.md`, `docs/codex-review-contract.md`, `data/bronze/education/gosa/enrollment_by_subgroup_programs/bronze-data-structure.md`, and the data-cleaning/review skill docs.

## Contract Verification

- Schema/parquet column match: PASS - every parquet file has exactly `year`, `district_code`, `school_code`, `program`, `student_count`, `participation_rate`, matching the contract order.
- Column roles and grain: PASS - the contract grain is `year`, `district_code`, `school_code`, `program`; roles are year, district FK, school FK, categorical, and two metrics.
- Metric units and derived quality checks: PASS - `student_count` is `unit: count`; `participation_rate` is `unit: proportion`; contract SQL enforces non-negative counts and rates in [0, 1].
- Categorical enums: PASS - `program` enum contains the nine canonical program values and matches manifest/gold distinct values.
- Detail levels and layout metadata: PASS - contract declares `schools`, `districts`, and `states`, default `schools`, year partitioning, local/S3 gold paths, and a coherent path template.
- Foreign-key descriptors: PASS - `district_code` targets districts and `school_code` targets the composite schools key; validator confirms all populated keys resolve.
- Schema hash/version consistency: PASS - contract version is `1.0.0`, year range is `2011-2024`, available years match gold, and schema hash is `bfe2a3feefadb4608d84003fe481d44844a504a8795f72e4e094f13f679d7cae`.

## Validator Verification

- `_validation.json` fresh + passing: PASS - manifest generated at `2026-06-11T19:59:09.294455+00:00`; validation timestamp is `2026-06-11T19:59:09.365264+00:00`; `"passed": true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - schema, grain uniqueness, quality SQL, foreign keys, canonical vocabulary, geography nulling, and suppression marker checks all passed.
- Validator warnings explained: PASS - null-rate warnings on `student_count` in 2021-2024 and `participation_rate` in 2023-2024 match the documented TFS rollout: count suppression begins in 2021 and percentage suppression begins in 2023.
- Section 15b quality-check coverage (cross-column invariants authored): PASS - contract includes structural checks for nine program rows per entity-year, the pre-2013 `special_ed_pk` rate mask, the 2011/2019 `alt_programs` count mask, and count/rate co-null behavior outside known asymmetries.

## Manifest Verification

- Files processed coverage: PASS - manifest processes the 14 program-bearing files from 2011-2024; 2004-2010 are skipped by `MIN_YEAR = 2011` with a code-backed reason because no program columns exist in those files.
- Categorical and recode coverage: PASS - `program` maps all nine wide `count_*` source columns to canonical program keys; `unmapped_count` is 0.
- Row-count reconciliation: PASS - manifest records 34,910 bronze entity rows and 314,190 gold rows, exactly a 9.0x expansion for every year.
- Metric stats sanity: PASS - final metric stats are non-negative for counts and within [0, 1] for rates; masked-value records explain 5,012 pre-2013 `special_ed_pk` rates and 4,938 2011/2019 `alt_programs` counts.

## Row and Join Accounting

- Bronze file/year disposition: PASS - 2011-2024 source files are processed; 2004-2010 are validly excluded as programless source years for this derived topic.
- Filter accounting: N/A - no source rows are filtered for this topic; masks null invalid metrics while preserving rows, and the 2022 charter correction reclassifies two rows rather than dropping them.
- Join accounting: N/A - the transform performs no data joins or lookup enrichments; only contract-driven FK validation occurs after export.
- Deduplication accounting: PASS - direct checks found zero duplicate gold natural keys and zero nine-row entity violations; dedup removed no rows.
- Aggregation/unpivot accounting: PASS - the unpivot is a pure 9-way reshape from one source entity row to nine program rows; no aggregation or collapsed-row formula is used.

## Reconciliation Checks

- Artifact freshness: PASS - transform/helper mtimes are before the manifest; validation is after the manifest; bronze checksums match the profiling report.
- Contract freshness: PASS - contract was emitted with the current gold and has no `_metadata.json` dependency.
- Year coverage: PASS - gold covers exactly 2011-2024; this matches the program-column era in bronze.
- Row preservation: PASS - direct bronze detail counts for sampled years reconcile to gold rows divided by nine, and an all-year ledger found no 9x violations.
- Column coverage: PASS - every 2011-2024 program count/rate bronze column has a corresponding long-form `program`, `student_count`, and `participation_rate` disposition.
- Recode accuracy: PASS - program values correctly represent Remedial 6-8, EIP K-5, Remedial 9-12, Special Ed K-12, ESOL, Special Ed PK, Vocation 9-12, Alternative Programs, and Gifted.
- Asian-family demographic recodes (section 5b): N/A - this program-participation fact table emits no demographic or wide demographic-share columns; Asian/PI handling is owned by the shared helper and the sibling demographic-share topic.
- Demographic mutual exclusivity (section 5a - no rollup row alongside split source rows in the same category): N/A - no demographic column is emitted.
- Demographic collision aggregation before dedup (section 5): N/A - no demographic normalization or demographic collision can occur in this topic.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - actual parquet order is `year`, geography keys, `program`, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, sections 11/12): PASS - no forbidden fact-table columns are present in gold.
- Canonical column vocabulary (section 16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - `student_count` and `participation_rate` follow enrollment/count/rate conventions; no assessment-specific vocabulary applies.
- Shared categorical utilities applied (section 10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no grade or subject column is emitted.
- Tidy long format (section 9 - no demographics/years/components as column names): PASS - the nine program column pairs are unpivoted into one `program` categorical plus two metrics.
- FK keys present in dimension tables (section 13 - `district_code`, `school_code`, `demographic`): PASS - validator reports 246 district keys and 2,658 composite school keys resolve.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - `program` is the only filterable topic categorical; row grain and FK joins are contract-derived and match parquet.
- Standards compliance (catch-all for sections 1-16 items not enumerated above): PASS - IDs are strings with leading zeros preserved, aggregate geography is nulled, suppression markers become NULL, and impossible values are masked rather than row-dropped.

## Spot Checks

### Check 1

- Bronze: `data/bronze/education/gosa/enrollment_by_subgroup_programs/enrollment_by_subgroup_programs_2024.csv`, Appling County High School `SCHOOL_DSTRCT_CD=601`, `INSTN_NUMBER=0103`, `ENROLL_COUNT_GIFTED=68`, `ENROLL_PCT_GIFTED=6.4`.
- Transform path: shared Era C rename/scale in `_enrollment_subgroup_programs_shared.py:631-729`, then `_unpivot_program_pairs()` in `transform.py:176-212`.
- Gold: `year=2024`, `district_code=601`, `school_code=0103`, `program=gifted`, `student_count=68`, `participation_rate=0.064`.
- Result: MATCH

### Check 2

- Bronze: `enrollment_by_subgroup_programs_2021.csv`, Appling County Primary `601/0277`, raw `ENROLL_COUNT_GIFTED=TFS`, `ENROLL_PCT_GIFTED=1.6`.
- Transform path: `read_bronze_file()` nulls TFS, Era B scales percentages, and `_unpivot_program_pairs()` emits the `gifted` row.
- Gold: `year=2021`, `district_code=601`, `school_code=0277`, `program=gifted`, `student_count=NULL`, `participation_rate=0.016`.
- Result: MATCH

### Check 3

- Bronze: `enrollment_by_subgroup_programs_2012.xlsx`, row `SCHOOL_DSTRCT_CD=644`, `INSTN_NUMBER=0503`, `ENROLL_COUNT_SPECIAL_ED_PK=243`, `ENROLL_PCT_SPECIAL_ED_PK=759.4`.
- Transform path: Era B scales the rate to 7.594, then `_null_pre_2013_special_ed_pk_rates()` in `transform.py:220-255` masks the impossible pre-2013 rate while preserving the count.
- Gold: `year=2012`, `district_code=644`, `school_code=0503`, `program=special_ed_pk`, `student_count=243`, `participation_rate=NULL`.
- Result: MATCH

### Check 4

- Bronze: `enrollment_by_subgroup_programs_2019.csv`, state row `SCHOOL_DSTRCT_CD=ALL`, `INSTN_NUMBER=ALL`, `ENROLL_COUNT_ALT_PROGRAMS=1602163`, `ENROLL_PCT_ALT_PROGRAMS=0.8`.
- Transform path: Era B scales the rate to 0.008, then `_null_alt_programs_count_publishing_error()` in `transform.py:292-344` masks the corrupted count because the companion rate is below 0.95.
- Gold: `year=2019`, state row, `program=alt_programs`, `student_count=NULL`, `participation_rate=0.008`.
- Result: MATCH

### Check 5

- Bronze: `enrollment_by_subgroup_programs_2022.csv`, mislabeled charter aggregate `DETAIL_LVL_DESC=School`, `SCHOOL_DSTRCT_CD=7830636`, `INSTN_NUMBER=ALL`, `ENROLL_COUNT_SPECIAL_ED_K12=41`, `ENROLL_PCT_SPECIAL_ED_K12=8.1`.
- Transform path: 2022 reclassification in `_enrollment_subgroup_programs_shared.py:676-698`, geography nulling in `transform.py:403-409`, then unpivot.
- Gold: `year=2022`, `district_code=7830636`, `school_code=NULL`, `program=special_ed_k_12`, `student_count=41`, `participation_rate=0.081`.
- Result: MATCH

## Notes

- The skill's literal derived bronze path for this topic would be `data/bronze/education/gosa/enrollment_program_participation/`, but this is intentionally a derived split topic. The transform source of truth is the shared bronze directory `data/bronze/education/gosa/enrollment_by_subgroup_programs/`, and the report audits that actual source path.
- A full program-row reconciliation rebuilt all expected 2011-2024 long rows from bronze program columns, applied only the documented `special_ed_pk` and `alt_programs` masks, and compared to gold: expected rows 314,190, gold rows 314,190, joined rows 314,190, count mismatches 0, rate mismatches 0.
