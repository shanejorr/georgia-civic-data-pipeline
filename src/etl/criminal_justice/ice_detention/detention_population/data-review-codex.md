# Data Review: detention_population

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze, transform, contract, validator, manifest, and gold output reconcile; no required transform fixes were found.

## Summary

- Review date: 2026-07-02
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - transform mtime `2026-07-02T21:43:55.947179+00:00`, manifest `2026-07-02T21:44:15.146484+00:00`, validation `2026-07-02T21:45:31.063823+00:00`; all bronze checksums match `bronze-data-structure.md`.

## Files Reviewed

- Transform: `src/etl/criminal_justice/ice_detention/detention_population/transform.py`
- Contract: `contracts/criminal_justice/detention_population.odcs.yaml`
- Bronze files: 15 profiled files, including 8 ICE fiscal-year workbooks, DDP `detention-management.xlsx`, DDP daily-population parquet, 2 PII parquets, and 3 DDP codebooks.
- Gold files: 16 parquet files under `data/gold/criminal_justice/detention_population/year=2019..2026/{counties,states}.parquet`
- Manifest: `data/gold/criminal_justice/detention_population/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/detention_population/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, data-cleaning standards, ETL workflow docs, `src/etl/CLAUDE.md`, and `src/etl/criminal_justice/CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS - contract properties exactly match the 22 parquet columns in order.
- Column roles and grain: PASS - grain is `year`, `county_fips`, `month`; `county_fips` is `fk_county`, `month` is categorical, and all measures are metrics.
- Metric units and derived quality checks: PASS - all metrics carry `unit: count`; range checks enforce non-negative values and authored SQL covers row-family nulls, ADP partitions, subset constraints, and state rollups.
- Categorical enums: PASS - `month` enum is `01`-`12` plus `all`, matching actual gold and manifest values.
- Detail levels and layout metadata: PASS - detail levels are `counties` and `states`, partitioned by `year`, path template is coherent with actual files.
- Foreign-key descriptors: PASS - `county_fips -> counties` is declared and validator confirms all 14 populated county keys resolve.
- Schema hash/version consistency: PASS - version is `1.0.0`, schema hash is `1fa3b1218a4c4b01a7f5d927f390ba85882880e935fd2eb29b4edd50ada546e4`, and contract was emitted from the current run.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp is after manifest generation and `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 19 pass, 0 fail; contract schema, grain uniqueness, quality SQL, foreign keys, canonical vocabulary, and geography nulling all pass.
- Validator warnings explained: PASS - one tidy-format warning flags `avg_daily_male` and `avg_daily_female`; this is an intentional monthly metric family, not a demographic axis.
- Section 15b quality-check coverage (cross-column invariants authored): PASS - contract has 30 SQL checks, including monthly/fiscal null-family checks, ADP partition sums, mandatory/subset constraints, and state key-metric rollup.

## Manifest Verification

- Files processed coverage: PASS - all current bronze files have disposition: DDP collation and daily panel processed, ICE workbooks verification-only, duplicate FY2025 workbook excluded, PII/codebook files excluded with code-backed reasons.
- Categorical and recode coverage: PASS - `facility_code`, `county_fips`, and `month` have `unmapped_count: 0`; facility name variants and facility-to-county mappings are represented in manifest values.
- Row-count reconciliation: PASS - manifest total gold is 671, matching actual parquet. Explicit filters are 656 superseded intra-FY snapshots and 200 partial FY2026-03 facility-days; remaining row reduction is aggregation from facility snapshots/days to county/state rows.
- Metric stats sanity: PASS - metric ranges are non-negative; the single key-metric NULL is the documented FY2019 Charlton ADP omission while guaranteed-minimum beds are preserved.

## Row and Join Accounting

- Bronze file/year disposition: PASS - FY2019-FY2026 fiscal-year rows come from DDP collation; FY2020-FY2026 workbooks verify the selected collation values; FY2023-FY2026 monthly rows come from the DDP daily panel.
- Filter accounting: PASS - latest snapshot per facility-FY drops superseded rows by design; FY2026-03 is dropped because only 10 of 31 days are present; duplicate FY2025 workbook is byte-identical and verification-only.
- Join accounting: PASS - GA facility crosswalk has 23 rows and 23 unique `facility_id` values; the daily panel joins 20 GA facilities with 1,257 days each and no join multiplication. Facility-FY rows left-join to county FIPS with no NULL county results.
- Deduplication accounting: PASS - no duplicate final grain rows exist; collision guard runs before `deduplicate_by_levels`, and actual duplicate grain count is 0.
- Aggregation/unpivot accounting: PASS - no unpivot is used. Facility-FY rows aggregate to county/state `month='all'`; facility-day rows aggregate to county-day totals and then county-month means, then state sums.

## Reconciliation Checks

- Artifact freshness: PASS - bronze checksums match, transform predates manifest, validation predates neither manifest nor gold.
- Contract freshness: PASS - contract was emitted by current transform/gold path with no `_metadata.json` dependency.
- Year coverage: PASS - gold covers FY2019-FY2026; monthly rows begin FY2023 as the DDP daily panel starts 2022-10-01.
- Row preservation: PASS - all row-count shifts are accounted for by scoping to GA, latest-snapshot selection, partial-month exclusion, and county/state aggregation.
- Column coverage: PASS - fact keys and metrics from the selected source families land in gold or are explicitly excluded as dimension attributes, PII, documentation, ALOS/book-in judgment exclusions, or verification-only workbook fields.
- Recode accuracy: PASS - facility-name variants normalize to the intended DETLOC codes; DETLOC codes map to expected Georgia county FIPS; month values preserve fiscal-year calendar-month semantics.
- Asian-family demographic recodes (section 5b): N/A - no race or demographic column exists.
- Demographic mutual exclusivity (section 5a): N/A - gender is served as monthly metric columns, not as a `demographic` axis.
- Demographic collision aggregation before dedup (section 5): N/A - no demographic normalization is performed.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - actual order is `year`, `county_fips`, `month`, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, sections 11/12): PASS - no forbidden or facility-identifying columns appear in parquet.
- Canonical column vocabulary (section 16): PASS - validator reports canonical vocabulary clean.
- Shared categorical utilities applied (section 10a): N/A - no grade, subject, or demographic shared-normalizer columns.
- Tidy long format (section 9): PASS - `month` is long/tidy; gender split metrics are intentional source metrics and the validator warning is explained.
- FK keys present in dimension tables (section 13): PASS - `county_fips -> counties` resolves for all 14 populated county keys.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - `month` is filterable with `has_total: true`; `county_fips` joins through the counties dimension; key metric is `avg_daily_population`.
- Standards compliance (catch-all for sections 1-16 items not enumerated above): PASS - no suppression markers survive, zeros are real, no gold was edited directly, and the transform validates itself.

## Spot Checks

### Check 1

- Bronze: `ddp/detention-management.xlsx`, Facilities sheet, `STEWART DETENTION CENTER`, FY2026 latest `file_date=2026-04-09`, has `male_crim=539.420765`, `male_non_crim=1161.273224`, `female_crim=57.36612`, `female_non_crim=267.743169`, `guaranteed_minimum=1600`; official FY2026 workbook row has the same values.
- Transform path: `transform.py:407-448`, `transform.py:698-720`
- Gold: `year=2026`, `county_fips='13259'`, `month='all'` has `avg_daily_population=2025.8032779999999`, the same component values, and `guaranteed_minimum_beds=1600`.
- Result: MATCH

### Check 2

- Bronze: `ddp/detention-management.xlsx`, `IRWIN COUNTY DETENTION CENTER`, FY2021 latest facility snapshot `file_date=2021-10-01`, has component sum `179.342723004695 + 72.8309859154931 + 20.830985915493 + 14.3145539906103 = 287.3192488262914`; the final FY2021 workbook has no Irwin row.
- Transform path: `transform.py:44-53`, `transform.py:407-448`, `transform.py:698-720`
- Gold: `year=2021`, `county_fips='13155'`, `month='all'` has `avg_daily_population=287.3192488262914` and `guaranteed_minimum_beds=600`.
- Result: MATCH

### Check 3

- Bronze: FY2019 DDP collation rows for `FIPCMGA` and `FIPCAGA` in Charlton County have NULL ADP components and guaranteed minimums `544` and `338`.
- Transform path: `transform.py:286-294`, `transform.py:698-720`
- Gold: `year=2019`, `county_fips='13049'`, `month='all'` has NULL ADP metrics and `guaranteed_minimum_beds=882`.
- Result: MATCH

### Check 4

- Bronze: DDP daily panel for Charlton County, FY2025 month `10`, facilities `FIPCAGA`, `FIPCDGA`, `FIPCMGA`, and `GADRYJM`, 31 complete days; county-day means are `n_detained=866.258064516129`, `n_detained_male=866.258064516129`, `n_detained_female=0.0`, `n_detained_convicted_criminal=205.61290322580646`, `n_detained_possibly_under_18=0.0`.
- Transform path: `transform.py:630-690`
- Gold: `year=2025`, `county_fips='13049'`, `month='10'` has the same five monthly values and NULL fiscal-year-only metrics.
- Result: MATCH

### Check 5

- Bronze: DDP daily panel has FY2026 month `03` with only 10 of 31 calendar days.
- Transform path: `transform.py:640-672`
- Gold: no FY2026 `month='03'` rows; manifest records `partial_calendar_month_at_panel_edge: 200` filtered facility-days.
- Result: MATCH

### Check 6

- Bronze/gold aggregate: FY2026 month `02` statewide daily-panel mean recomputed from GA county-day totals is `avg_daily_population=4574.535714285715`, `avg_daily_male=4210.392857142858`, `avg_daily_female=360.3571428571429`, `avg_daily_convicted_criminal=1395.4285714285716`, `avg_daily_possibly_under_18=0.17857142857142858`.
- Transform path: `transform.py:723-732`, `transform.py:776-779`
- Gold: `year=2026`, `county_fips=NULL`, `month='02'` has the same values; all state rows equal summed counties for every metric.
- Result: MATCH

## Notes

- Prior `data-review-claude.md` and any prior `data-review-codex.md` were not read before this report.
- The DDP daily crosswalk has three GA crosswalk facilities absent from the daily panel (`GMHATGA`, `PCRMMGA`, `PHPMHGA`); these produce no daily rows and do not affect the 14 counties present in monthly gold.
- No required fixes were identified.
