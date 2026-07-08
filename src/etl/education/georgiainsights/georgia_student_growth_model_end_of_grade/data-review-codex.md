# Data Review: georgia_student_growth_model_end_of_grade

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Contract, manifest, validation, bronze files, and gold parquet reconcile; no bronze-to-gold accuracy defects requiring transform changes were found.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - `check_bronze_freshness.py` passed for all 18 bronze files; transform mtime `2026-06-12T19:51:09Z` is before manifest generation `2026-06-12T19:51:52Z`, and validation timestamp `2026-06-12T19:51:52Z` is not older than the manifest.

## Files Reviewed

- Transform: `src/etl/education/georgiainsights/georgia_student_growth_model_end_of_grade/transform.py`
- Contract: `contracts/education/georgia_student_growth_model_end_of_grade.odcs.yaml`
- Bronze files: 18 Excel workbooks under `data/bronze/education/georgiainsights/georgia_student_growth_model_end_of_grade/` covering 2015-2019 and 2023.
- Gold files: 18 parquet files under `data/gold/education/georgia_student_growth_model_end_of_grade/year=*/{schools,districts,states}.parquet`
- Manifest: `data/gold/education/georgia_student_growth_model_end_of_grade/_transform_manifest.json`
- Validation report: `data/gold/education/georgia_student_growth_model_end_of_grade/_validation.json`
- Supporting docs: `docs/codex-review-contract.md`, `docs/contract-creation.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `data/bronze/education/georgiainsights/georgia_student_growth_model_end_of_grade/bronze-data-structure.md`, `src/etl/education/CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS - actual parquet columns exactly match the contract property order: `year`, `district_code`, `school_code`, `grade_level`, `subject`, then 10 metric columns.
- Column roles and grain: PASS - contract grain is `year`, `district_code`, `school_code`, `grade_level`, `subject`; this matches `NATURAL_KEYS` after `detail_level` is encoded by file path and removed from parquet.
- Metric units and derived quality checks: PASS - counts use `count`, proportion metrics use `proportion`, and `sgp_median` uses `percentile` with `value_min: 1` and `value_max: 99`.
- Categorical enums: PASS - contract enums match manifest and gold distinct values: grades `all`, `04`-`08`; subjects `english_language_arts`, `mathematics`, `science`, `social_studies`.
- Detail levels and layout metadata: PASS - contract detail levels are `schools`, `districts`, `states`, matching the 18 partition files.
- Foreign-key descriptors: PASS - contract declares `district_code -> districts` and composite `school_code -> schools` through `(district_code, school_code)`.
- Schema hash/version consistency: PASS - contract is `version: 1.0.0`, active, with schema hash present and gold layout covering available years 2015, 2016, 2017, 2018, 2019, and 2023.

## Validator Verification

- `_validation.json` fresh + passing: PASS - `passed: true`; timestamp is not older than manifest generation.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - validation reports 20 pass, 0 fail, 1 warning; schema, grain uniqueness, 17 quality SQL checks, FKs, vocabulary, and geography nulling all pass.
- Validator warnings explained: PASS - the 5 null-rate warnings are the documented 2023 metric break: `num_tested`, `pct_received_sgp`, achievement percentages, and `pct_typical_or_high_growth` are not reported in 2023.
- §15b quality-check coverage (cross-column invariants authored): PASS - authored checks cover `num_received_sgp <= num_tested`, `pct_received_sgp` matching counts, proficiency nesting, and 2023 SGP growth bands summing to one.

## Manifest Verification

- Files processed coverage: PASS - manifest lists all 18 current bronze workbooks; checksum gate reports no changed or unanalyzed files.
- Categorical and recode coverage: PASS - `grade_level` and `subject` both have `unmapped_count: 0`; map entries are semantically correct for grade tokens and subject headers.
- Row-count reconciliation: PASS - manifest `total_bronze` equals `total_gold` at 111,678 rows, with 0 filtered rows and expansion factor 1.0 for every year after the wide-to-long transform's ledgered row basis.
- Metric stats sanity: PASS - proportion metrics are within 0-1; `sgp_median` exported range is 1.0 to 97.0 after the documented empty-cohort mask; count metrics are non-negative.

## Row and Join Accounting

- Bronze file/year disposition: PASS - direct workbook scans produced the same long-row counts as `files_processed` for every file.
- Filter accounting: PASS - no rows were filtered; the defensive unparseable-grade filter did not fire.
- Join accounting: N/A - the transform performs no data joins; the only key mutation is row-preserving charter campus promotion.
- Deduplication accounting: PASS - duplicate natural-key count in gold is 0; `assert_no_natural_key_collisions()` runs before defensive deduplication.
- Aggregation/unpivot accounting: PASS - each source row x subject block becomes one gold row; no aggregate recomputation is performed. Published `AllGrades` rows are preserved as `grade_level="all"` because medians are not reconstructable from per-grade medians.

## Reconciliation Checks

- Artifact freshness: PASS - bronze freshness, manifest, validation, and gold all align.
- Contract freshness: PASS - contract matches current parquet and has no `_metadata.json` dependency.
- Year coverage: PASS - gold contains exactly 2015, 2016, 2017, 2018, 2019, and 2023, matching bronze and documented 2020-2022 gaps.
- Row preservation: PASS - yearly row counts match manifest: 28,560; 28,692; 14,396; 14,526; 14,594; 10,910.
- Column coverage: PASS - fact keys, `grade_level`, `subject`, and all era-specific metrics have traced source columns or documented NULL absence by era.
- Recode accuracy: PASS - grade and subject recodes match the actual bronze labels and shared normalizers.
- Asian-family demographic recodes (§5b): N/A - no demographic column or race bucket exists in this topic.
- Demographic mutual exclusivity (§5a - no rollup row alongside split source rows in the same category): N/A - no demographic column.
- Demographic collision aggregation before dedup (§5): N/A - no demographic column.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS - actual parquet order is `year`, `district_code`, `school_code`, `grade_level`, `subject`, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS - parquet contains no forbidden fact-table columns; `detail_level` is encoded in file names.
- Canonical column vocabulary (§16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - names use canonical `grade_level`, `subject`, `num_tested`, `num_received_sgp`, and `_or_above`.
- Shared categorical utilities applied (§10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): PASS - transform applies both shared normalizers before manifest and export.
- Tidy long format (§9 - no demographics/years/components as column names): PASS - subject is a row categorical, not wide columns.
- FK keys present in dimension tables (§13 - `district_code`, `school_code`, `demographic`): PASS - direct anti-joins found 0 unmatched district keys and 0 unmatched composite school keys.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - grain and FK descriptors support the expected REST/MCP semantics.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS - suppression markers are NULL, ID strings preserve padding, detail-level nulling is correct per file, and the manifest records masked and reclassified events.

## Spot Checks

### Check 1

- Bronze: `GSGM_EOG_2015_School.xls`, `EOG_AllGrades_2015_School`, Appling County Elementary (`KEY=6010177`), ELA: `N Tested=356`, `N Received SGP=343`, `% Received SGP=96`, `Median SGP=43`, `% Proficient=22`, `% Developing=60`, `% Typical or High=59`.
- Transform path: flat header reader and key split in `transform.py:533`-`580`, `_split_compound_key()` in `transform.py:463`-`476`, percent scaling in `transform.py:498`-`516`.
- Gold: `year=2015`, `district_code='601'`, `school_code='0177'`, `grade_level='all'`, `subject='english_language_arts'`, metrics `356`, `343`, `0.96`, `43.0`, `0.22`, `0.60`, `0.59`.
- Result: MATCH

### Check 2

- Bronze: `GSGM_EOG_2018_School_Level.xlsx`, `EOG_Grade8_2018_School`, Appling County Middle (`System Code=601`, `School Code=195`), Mathematics: `Number Tested=249`, `Number Received SGP=241`, `% Received SGP=97`, `Median SGP=59`, `% Proficient=44`, `% Developing=86`, `% Typical or High=78`.
- Transform path: two-row pivot reader in `transform.py:583`-`649`, grade normalization in `transform.py:665`-`687`, percent scaling in `transform.py:498`-`516`.
- Gold: `year=2018`, `district_code='601'`, `school_code='0195'`, `grade_level='08'`, `subject='mathematics'`, metrics `249`, `241`, `0.97`, `59.0`, `0.44`, `0.86`, `0.78`.
- Result: MATCH

### Check 3

- Bronze: `SGP_EOG_Aggs_School_Level_2023.xlsx`, `Grade4_School_2023`, Appling County Elementary (`System Code=601`, `School Code=0177`), ELA: `Number Received SGP=164`, `Median SGP=45.5`, `% Low Growth=39.02439024390244`, `% Typical Growth=30.48780487804878`, `% High Growth=30.48780487804878`; Math: `165`, `52`, `29.09090909090909`, `34.54545454545455`, `36.36363636363637`.
- Transform path: two-row pivot reader in `transform.py:583`-`649`; 2023 metric mapping in `_BRONZE_HEADER_MAP` at `transform.py:214`-`217`; percent scaling in `transform.py:498`-`516`.
- Gold: ELA row has `num_received_sgp=164`, `sgp_median=45.5`, SGP bands `0.390244`, `0.304878`, `0.304878`; Math row has `165`, `52.0`, `0.290909`, `0.345455`, `0.363636`; legacy metrics are NULL.
- Result: MATCH

### Check 4

- Bronze: empty-cohort examples in `GSGM_EOG_2016_School_Level.xls` and `GSGM_EOG_2018_School_Level.xlsx` publish `N Tested=0`, `N Received SGP=0`, and `Median SGP=0`.
- Transform path: `_null_empty_cohort_sgp_median()` in `transform.py:750`-`781`.
- Gold: 34 zero-cohort rows retain zero count fields and have `sgp_median=NULL`; manifest records `masked_values` count 34 for years 2016 and 2018.
- Result: MATCH

## Notes

- The five statewide rows where `sgp_median` is not exactly 50 were checked against the state workbooks and match the published bronze values, so they are source values rather than transform defects.
- No collapsed-row formula exists beyond preserving published aggregate `AllGrades` rows. The formula-level checks applicable here are direct quality checks: 2023 SGP bands sum to one (0 bad rows), `pct_received_sgp` matches counts within tolerance, and proficiency is nested within developing-or-above.
