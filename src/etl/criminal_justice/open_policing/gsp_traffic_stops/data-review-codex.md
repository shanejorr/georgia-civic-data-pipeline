# Data Review: gsp_traffic_stops

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze stop-level rows reconcile to county/year/race and statewide gold counts; contract, manifest, validator, and direct parquet checks show no required transform fixes.

## Summary

- Review date: 2026-07-07
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze checksum gate passed; transform mtime `2026-07-07T04:06:26+00:00` is older than manifest `2026-07-07T04:27:31.367082+00:00`; validation timestamp `2026-07-07T04:27:31.415151+00:00` is fresh and passing.

## Files Reviewed

- Transform: `src/etl/criminal_justice/open_policing/gsp_traffic_stops/transform.py`
- Contract: `contracts/criminal_justice/gsp_traffic_stops.odcs.yaml`
- Bronze files: `yg821jf8611_ga_statewide_2020_04_01.csv.zip` plus `bronze-data-structure.md` and `_provenance.md`
- Gold files: 10 parquet files, `year=2012` through `year=2016`, each with `counties.parquet` and `states.parquet`
- Manifest: `data/gold/criminal_justice/gsp_traffic_stops/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/gsp_traffic_stops/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, data-cleaning standards, transform/review/fix/full-pipeline skills, root `AGENTS.md`/`CLAUDE.md`, and `src/etl/criminal_justice/CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS - contract and parquet both expose `year, county_fips, demographic, traffic_stops` in that order.
- Column roles and grain: PASS - roles are `year`, `fk_county`, `fk_demographic`, and `metric`; grain is `year, county_fips, demographic`.
- Metric units and derived quality checks: PASS - `traffic_stops` is `unit: count`, key metric, non-negative, and positive for emitted cells.
- Categorical enums: PASS - demographic enum exactly matches gold distinct values: `all`, `asian_pacific_islander`, `black`, `hispanic`, `other`, `race_unknown`, `white`.
- Detail levels and layout metadata: PASS - contract lists `counties` and `states`, path template matches `criminal_justice/gsp_traffic_stops/year={year}/{detail}.parquet`, and current layout matches.
- Foreign-key descriptors: PASS - `county_fips -> counties` and `demographic -> demographics`; validator confirms all 159 counties and all 7 demographics resolve.
- Schema hash/version consistency: PASS - version `1.0.0`, schema hash `a9064c5e243b69cd245d5f1179c4452ce26594605e0ff92c4a9ad091589d024a`, current contract metadata matches gold layout and year range 2012-2016.

## Validator Verification

- `_validation.json` fresh + passing: PASS - `passed: true`, 20 pass, 0 fail, 0 warnings.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - `contract_parquet_schema`, `grain_uniqueness`, `contract_quality_sql`, `foreign_keys`, and `canonical_vocabulary` all passed.
- Validator warnings explained: N/A - no validator warnings.
- section 15b quality-check coverage (cross-column invariants authored): PASS - quality SQL covers race partition to `all`, state-vs-county sum bounds for the 10 unmappable stops, positive counts, non-negative counts, demographic enum, non-empty data, and the 2000 year floor.

## Manifest Verification

- Files processed coverage: PASS - the single zip member is recorded with the expected 19-column header and 1,906,772 parsed rows; per-year row ledger covers 2012-2016 from the `date` column.
- Categorical and recode coverage: PASS - `county_fips` and `demographic` mappings have `unmapped_count: 0`; `asian/pacific islander` maps to `asian_pacific_islander`; null `subject_race` is intentionally filled to `race_unknown`.
- Row-count reconciliation: PASS - bronze year counts are 372,285; 415,242; 411,036; 369,441; 338,768. Gold rows total 5,284 after aggregation, and explicit filtering records only 10 unmappable-county stops excluded from county rows but retained in state rows.
- Metric stats sanity: PASS - `traffic_stops` is non-null, minimum 1, maximum equals each year state total, and no negative or zero emitted cells exist.

## Row and Join Accounting

- Bronze file/year disposition: PASS - all stop rows in the only bronze zip are processed; years derive from `date`, not the release-date filename.
- Filter accounting: PASS - no pre-2000 rows exist; exactly 10 no-FIPS stops are explicitly recorded as excluded from county detail and retained in state detail.
- Join accounting: PASS - `add_county_fips` resolves 159 real Georgia county names; the only no-FIPS rows are seven `G### County` placeholder labels totaling 9 stops plus 1 null county.
- Deduplication accounting: PASS - no duplicate natural keys in actual gold; collision guard runs before `deduplicate_by_levels`, and the safety tie-break is documented.
- Aggregation/unpivot accounting: PASS - stop-level rows collapse by `year, county_fips, demographic`; each level emits `all` plus mutually exclusive race values, and quality SQL verifies race rows sum to `all`.

## Reconciliation Checks

- Artifact freshness: PASS - checksum gate passed and validation is newer than the manifest.
- Contract freshness: PASS - contract is emitted by the current transform/gold path and has no `_metadata.json` dependency.
- Year coverage: PASS - actual bronze and gold years are 2012, 2013, 2014, 2015, and 2016 only.
- Row preservation: PASS - state `all` rows equal raw bronze year counts exactly; county sums differ only by the documented 10 no-FIPS stops.
- Column coverage: PASS - gold columns trace to `date`, `county_name`, `subject_race`, and row counts; stop-level PII/free-text columns are intentionally excluded.
- Recode accuracy: PASS - county FIPS mappings match the counties dimension; demographic mappings match SOPP race semantics and manifest evidence.
- Asian-family demographic recodes (section 5b): PASS - bronze has combined `asian/pacific islander` only, no separate Pacific Islander value, and gold emits `asian_pacific_islander` with no `asian` or `pacific_islander`.
- Demographic mutual exclusivity (section 5a - no rollup row alongside split source rows in the same category): PASS - race values are mutually exclusive; `all` is the only overlapping total.
- Demographic collision aggregation before dedup (section 5): N/A - source standardized race labels are already one-to-one after the intentional unknown fill; any same-canonical aggregation happens in `_aggregate_level`.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - parquet order is `year, county_fips, demographic, traffic_stops`.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, section 11/12): PASS - exported parquet has no forbidden columns.
- Canonical column vocabulary (section 16): PASS - `traffic_stops`, `county_fips`, and `demographic` match project vocabulary; education-only names are not applicable.
- Shared categorical utilities applied (section 10a): PASS - demographic normalization uses `normalize_demographic_column`; no grade or subject columns exist.
- Tidy long format (section 9): PASS - race groups are rows, not columns.
- FK keys present in dimension tables (section 13): PASS - validator confirms county and demographic FKs resolve.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - grain and FK descriptors are derived from contract roles; demographic is an FK/filterable dimension key.
- Standards compliance (catch-all for sections 1-16 items not enumerated above): PASS - no suppression markers, no percentage scale issue, county/state geography nulling is contract-validated, and stop-level PII remains out of gold.

## Spot Checks

### Check 1

- Bronze: `2012`, `Long County`, `subject_race = NA`; direct zip aggregation gives 1,436 stops after `NA -> race_unknown`.
- Transform path: `_read_stop_counts` and `_resolve_demographic`, lines 251-318 and 343-375; county aggregation lines 508-513.
- Gold: `year=2012/counties.parquet`, `county_fips=13183`, `demographic=race_unknown`, `traffic_stops=1436`.
- Result: MATCH

### Check 2

- Bronze: `2012`, `Laurens County`, `subject_race = white`; direct zip aggregation gives 1,620 stops.
- Transform path: `_resolve_county_fips` and `_aggregate_level`, lines 378-452 and 460-482.
- Gold: `year=2012/counties.parquet`, `county_fips=13175`, `demographic=white`, `traffic_stops=1620`.
- Result: MATCH

### Check 3

- Bronze: `2014`, `Fulton County`, `subject_race = black`; direct zip aggregation gives 5,370 stops.
- Transform path: `_resolve_demographic`, `_resolve_county_fips`, `_aggregate_level`, lines 343-482.
- Gold: `year=2014/counties.parquet`, `county_fips=13121`, `demographic=black`, `traffic_stops=5370`.
- Result: MATCH

### Check 4

- Bronze: 2013 total raw stop rows = 415,242; exact no-FIPS rows in 2013 are four `race_unknown` stops under `G139 County` and `G213 County`.
- Transform path: no-FIPS handling lines 425-452 and state rollup lines 506-513.
- Gold: 2013 state `all` = 415,242; 2013 county `all` sum = 415,238; 2013 state-minus-county `race_unknown` = 4.
- Result: MATCH

### Check 5

- Bronze: `subject_race` distinct counts are null 898,309; white 660,855; black 297,156; hispanic 33,715; asian/pacific islander 8,753; other 7,984.
- Transform path: unknown fill and demographic normalization lines 343-375; race partition quality check lines 737-761.
- Gold: state-level race rows per year sum exactly to each `all` row, and demographic values are `asian_pacific_islander`, `black`, `hispanic`, `other`, `race_unknown`, `white`.
- Result: MATCH

## Notes

- The source includes 298 `GEORGIA DEPARTMENT OF NATURAL RESOURCES` rows and 4 `GEORGIA STATE PATROL` rows alongside 1,906,470 `GEORGIA DEPARTMENT OF PUBLIC SAFETY` rows. The transform intentionally includes them in the full SOPP statewide universe, and the contract limitations disclose the 302-row residual, so this is not a must-fix accuracy defect.
- The manifest records the single multi-year zip once in `files_processed` with `year: 2016`; the authoritative per-year bronze counts are correctly recorded in `row_counts` from the stop `date` field.
