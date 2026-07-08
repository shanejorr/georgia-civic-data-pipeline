# Data Review: postsecondary_c11_report

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: bronze file coverage, row expansion, recodes, contract schema, validator checks, and sampled values all match; no transform accuracy fixes required.

## Summary

- Review date: 2026-06-11
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze freshness passed; transform mtime 2026-06-11T00:50:46Z is older than manifest 2026-06-11T01:17:52Z, contract 2026-06-11T01:17:52Z, and validation 2026-06-11T01:17:52Z.

## Files Reviewed

- Transform: `src/etl/education/gosa/postsecondary_c11_report/transform.py`
- Contract: `contracts/education/postsecondary_c11_report.odcs.yaml`
- Bronze files: 13 files, `postsecondary_c_11_report_2012.xlsx` through `postsecondary_c_11_report_2024.csv`
- Gold files: 39 parquet files under `data/gold/education/postsecondary_c11_report/year=2010` through `year=2022`
- Manifest: `data/gold/education/postsecondary_c11_report/_transform_manifest.json`
- Validation report: `data/gold/education/postsecondary_c11_report/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `data/bronze/education/gosa/postsecondary_c11_report/bronze-data-structure.md`, `src/etl/education/CLAUDE.md`, data-cleaning standards and review/fix skills

## Contract Verification

- Schema/parquet column match: PASS - all parquet files use `year`, `district_code`, `school_code`, `demographic`, `graduate_count`, `num_enrolled_in_college` in contract order.
- Column roles and grain: PASS - contract grain is year + nullable geography keys + demographic, matching the natural fact grain and aggregate geography nulling.
- Metric units and derived quality checks: PASS - both metrics are `unit: count`; contract quality checks enforce non-negative counts plus topic-specific invariants.
- Categorical enums: PASS - contract enum, manifest `gold_values_produced`, and gold distinct values all contain the same 14 demographics; no `asian_pacific_islander` rows are emitted.
- Detail levels and layout metadata: PASS - contract declares `schools`, `districts`, and `states`, with `education/postsecondary_c11_report/year={year}/{detail}.parquet`.
- Foreign-key descriptors: PASS - district, composite school, and demographic FKs are present and match dimension contracts.
- Schema hash/version consistency: PASS - version is `1.0.0`, schema hash is `eda332ef3584a7a2c7a6d5d4a665fccbfb645779aef6b10f3ffb28a06ea01e96`, and available years are 2010-2022 with no gaps.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp is newer than the manifest and reports `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 21 pass, 0 fail, 0 warning; all 12 contract quality SQL checks pass.
- Validator warnings explained: N/A - validation reports no warnings.
- Section 15b quality-check coverage (cross-column invariants authored): PASS - checks cover `num_enrolled_in_college <= graduate_count`, suppression threshold, suppressed graduate implication, unsuppressed state rows, state gender and race partitions, and Pacific Islander structural coverage.

## Manifest Verification

- Files processed coverage: PASS - manifest processes all 13 current bronze files, with cohort years 2010-2022 and the documented filename year = cohort year + 2 offset.
- Categorical and recode coverage: PASS - `demographic` has 0 unmapped values; every observed bronze label maps to the expected canonical demographic.
- Row-count reconciliation: PASS - total bronze rows 8,156 expand to 113,596 gold rows; 2010 expands by 13 groups and 2011-2022 by 14 groups, exactly matching actual gold counts.
- Metric stats sanity: PASS - counts are non-negative, published minima are 10, null rates are stable and source-backed suppression is about 47-56 percent by metric/year.

## Row and Join Accounting

- Bronze file/year disposition: PASS - every current bronze data file is processed; no ignored source data files remain.
- Filter accounting: N/A - no row filters are applied; `total_filtered` is 0 and row expansion matches the wide-to-long design.
- Join accounting: N/A - transform performs no data joins or lookups; validator and direct checks show 0 unmatched district, school, or demographic keys.
- Deduplication accounting: PASS - source entity keys are unique per file, final natural-key duplicates are 0, and no dedup row loss is observed.
- Aggregation/unpivot accounting: PASS - transform unpivots one source entity row into 13 or 14 demographic rows; it does not aggregate or collapse source rows.

## Reconciliation Checks

- Artifact freshness: PASS - bronze checksums match `bronze-data-structure.md`; no unanalyzed files were found.
- Contract freshness: PASS - contract was emitted after the manifest in the same transform run and has no `_metadata.json` dependency.
- Year coverage: PASS - bronze publication years 2012-2024 map to gold cohort years 2010-2022.
- Row preservation: PASS - independent file ledger by year/detail exactly matches gold row counts.
- Column coverage: PASS - fact keys, demographic labels, and the two metric families are represented; names, report name, and publication year are validly excluded.
- Recode accuracy: PASS - labels such as `Total All`/`TOTAL`, `Free Reduced Lunch`/`FRL`, `Disability`/`SWD`, `Two or More Race(s)`/`TWOORMORE`, `American Indian or Alaskan Native`/`NATIVE`, and `Pacific Islander`/`PACIFIC` map correctly.
- Asian-family demographic recodes (section 5b): PASS - the topic uses the split convention: 2011-2022 have separate Asian and Pacific Islander rows, 2010 has no Pacific Islander source group, and gold emits no combined `asian_pacific_islander` rows.
- Demographic mutual exclusivity (section 5a - no rollup row alongside split source rows in the same category): PASS - there are 0 natural-key groups containing combined Asian/Pacific Islander alongside split Asian or Pacific Islander.
- Demographic collision aggregation before dedup (section 5): N/A - observed source labels map to distinct canonical demographics, so there are no demographic collisions to aggregate.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - parquet order is year, district_code, school_code, demographic, graduate_count, num_enrolled_in_college.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, sections 11/12): PASS - gold parquet contains only keys and metrics; `detail_level` is encoded by filename.
- Canonical column vocabulary (section 16): PASS - `graduate_count` is canonical and `num_enrolled_in_college` matches the sibling postsecondary schema; no forbidden variants appear.
- Shared categorical utilities applied (section 10a): PASS - demographic normalization uses `normalize_demographic_column`; there are no grade or subject columns.
- Tidy long format (section 9): PASS - demographic groups are rows, not metric-family columns.
- FK keys present in dimension tables (section 13): PASS - direct dimension checks found 0 unmatched districts, 0 unmatched composite school keys, and 0 unmatched demographics.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - contract roles expose demographic as the only categorical filter and FKs are dimension-joinable.
- Standards compliance (catch-all for sections 1-16 items not enumerated above): PASS - suppression, count scale, geography nulling, ID formatting, manifest completeness, and validation all conform.

## Spot Checks

### Check 1

- Bronze: `postsecondary_c_11_report_2012.xlsx`, year 2010, Towns County High School (`district=739`, `school=204`), `Black` has `TFS` / `TFS`.
- Transform path: `_read_excel_stitched()` and `_unpivot_to_long()` lines 329-555 convert `TFS` to NULL, zero-pad school code, and map `Black` to `black`.
- Gold: `year=2010`, `district_code='739'`, `school_code='0204'`, `demographic='black'`, both metrics NULL.
- Result: MATCH

### Check 2

- Bronze: `postsecondary_c_11_report_2012.xlsx`, same source row, `White` has 55 graduates and 43 enrolled.
- Transform path: `_unpivot_to_long()` lines 475-555.
- Gold: `year=2010`, `district_code='739'`, `school_code='0204'`, `demographic='white'`, `graduate_count=55`, `num_enrolled_in_college=43`.
- Result: MATCH

### Check 3

- Bronze: `postsecondary_c_11_report_2013.xlsx`, state row (`ALL` / `ALL`), `Pacific Islander` has 67 graduates and 44 enrolled.
- Transform path: `transform_file()` lines 571-666 and `_unpivot_to_long()` lines 475-555.
- Gold: `year=2011`, state file with `district_code=NULL`, `school_code=NULL`, `demographic='pacific_islander'`, values 67 and 44.
- Result: MATCH

### Check 4

- Bronze: `postsecondary_c_11_report_2019.xlsx`, Appling County district aggregate (`district=601`, `school=ALL`), `Total All` has 198 graduates and 118 enrolled.
- Transform path: geography sentinel handling in `_unpivot_to_long()` lines 500-529 and shared nulling in `main()` lines 709-715.
- Gold: `year=2017`, `district_code='601'`, `school_code=NULL`, `demographic='all'`, values 198 and 118.
- Result: MATCH

### Check 5

- Bronze: `postsecondary_c_11_report_2024.csv`, Appling County High School (`district=601`, `school=0103`), `TOTAL` has 220 graduates and 109 enrolled.
- Transform path: CSV read and pair resolution in `transform_file()` lines 591-628, then `_unpivot_to_long()` lines 475-555.
- Gold: `year=2022`, `district_code='601'`, `school_code='0103'`, `demographic='all'`, values 220 and 109.
- Result: MATCH

## Notes

- No previous `data-review-claude.md` or `data-review-codex.md` was read before writing this report.
- No collapsed-row formula trace is required because the transform does not aggregate or collapse bronze rows; independent checks instead verified unpivot expansion and state-level gender/race reconciliation.
- The bronze profiling prose has a minor 2010 detail-count typo, but the actual 2012 workbook contains 1 state, 179 district, and 408 school rows; gold matches the actual file exactly.
