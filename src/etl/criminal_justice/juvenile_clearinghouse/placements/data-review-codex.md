# Data Review: placements

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze, transform logic, contract, validator output, manifest, and gold parquet reconcile; no bronze-to-gold correctness fixes are required.

## Summary

- Review date: 2026-07-02
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze checksum matches the structure report; transform mtime `2026-07-02T20:43:33Z` is older than manifest `2026-07-02T20:43:53Z`; validation `2026-07-02T20:46:14Z` is newer than the manifest and passed.

## Files Reviewed

- Transform: `src/etl/criminal_justice/juvenile_clearinghouse/placements/transform.py`
- Contract: `contracts/criminal_justice/placements.odcs.yaml`
- Bronze files: `data/bronze/criminal_justice/juvenile_clearinghouse/placements/decision_point_placements_raw_data_2026-06.csv` plus `_provenance.md` and `bronze-data-structure.md`
- Gold files: 32 parquet files, `year=2010` through `year=2025`, each with `counties.parquet` and `states.parquet`
- Manifest: `data/gold/criminal_justice/placements/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/placements/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, data-cleaning standards, ETL guides, and `src/etl/criminal_justice/CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS - contract columns exactly match parquet order: `year`, `county_fips`, `demographic`, `facility_type`, `num_new_placements`, `num_placements`, `num_youth`.
- Column roles and grain: PASS - grain is `year`, `county_fips`, `demographic`, `facility_type`; state rows use NULL `county_fips`.
- Metric units and derived quality checks: PASS - all three metrics are `unit: count`; contract quality checks enforce non-negative counts plus `num_new_placements <= num_placements` and `num_youth <= num_placements`.
- Categorical enums: PASS - contract enums match actual gold values: 9 demographics and 3 facility types.
- Detail levels and layout metadata: PASS - `counties` and `states`, partitioned by `year`, path template `criminal_justice/placements/year={year}/{detail}.parquet`.
- Foreign-key descriptors: PASS - `county_fips -> counties` and `demographic -> demographics`.
- Schema hash/version consistency: PASS - version `1.0.0`, schema hash present, available years 2010-2025 with no gaps.

## Validator Verification

- `_validation.json` fresh + passing: PASS - `passed: true`, 20 pass / 0 fail / 0 warning.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - schema, order, grain uniqueness, 14 contract SQL checks, both FKs, geography nulling, and canonical vocabulary all passed.
- Validator warnings explained: N/A - no warnings.
- S15b quality-check coverage (cross-column invariants authored): PASS - authored checks cover count bounds, subset relationships, facility partitions, race/gender placement partitions, and county totals within state totals.

## Manifest Verification

- Files processed coverage: PASS - manifest processes the single current CSV, 433,844 bronze rows, schema `era_1_2010_2025_placement_level`; checksum freshness gate passed.
- Categorical and recode coverage: PASS - `county_fips`, `demographic`, and `facility_type` all have `unmapped_count: 0`; actual bronze distinct values match the manifest.
- Row-count reconciliation: PASS - gold has 32,656 rows. The large manifest compression from 433,844 bronze rows is explained by offense-row to placement-tuple reduction and county/state aggregation; explicit disposition events are 16 invalid year-window rows and 3,934 out-of-state placement tuples excluded only from county rows.
- Metric stats sanity: PASS - all metric counts are non-null and non-negative; `num_new_placements` min 0, `num_placements` min 1, `num_youth` min 1.

## Row and Join Accounting

- Bronze file/year disposition: PASS - the one cumulative file covers years 2010-2025 and all years appear in gold.
- Filter accounting: PASS - 16 rows where `Year` falls outside `[admitted, terminated]` are dropped and recorded; out-of-state residence placement tuples are excluded from county-level rows and kept in state rollups.
- Join accounting: PASS - county name to FIPS resolution has 0 unmatched non-OUT OF STATE names; all 159 gold county keys resolve in the counties dimension.
- Deduplication accounting: PASS - aggregation produces one row per natural key; duplicate natural-key count in gold is 0. The post-aggregation dedup path is a no-op safety net.
- Aggregation/unpivot accounting: PASS - 433,828 retained bronze rows reduce to 147,474 placement tuples, then to 32,656 gold cells via demographic and facility-type rollups.

## Reconciliation Checks

- Artifact freshness: PASS - transform, manifest, contract, validation, bronze profile, and parquet are current.
- Contract freshness: PASS - contract emitted from current transform/gold; no `_metadata.json` dependency.
- Year coverage: PASS - 2010-2025 present in bronze, manifest, contract, and gold.
- Row preservation: PASS - offense rows collapse to distinct `(year, juvenile, admitted_date, site)` placement tuples; state `all/all` rows recompute exactly from those tuples.
- Column coverage: PASS - all fact keys, categoricals, and metrics trace to bronze columns or documented rollup constants; PII and free-text/detail fields stay out of gold.
- Recode accuracy: PASS - `RYDC -> rydc`, `YDC -> ydc`; gender/race values map to canonical demographics; 160 residence labels are resolved or explicitly treated as state-rollup-only.
- Asian-family demographic recodes (S5b): PASS - source is individual-level with one mutually exclusive race per row, no Pacific Islander label, and an explicit `Other` race bucket; transform documents `Asian -> asian` and does not emit `asian_pacific_islander`.
- Demographic mutual exclusivity (S5a): PASS - race rows are `asian`, `black`, `hispanic`, `native_american`, `other`, `white`; gender rows are `female`, `male`; no same-axis rollup appears alongside split race values except the allowed `all` aggregate lane.
- Demographic collision aggregation before dedup (S5): PASS - grouping happens after canonical demographic normalization, so aliases would aggregate before dedup; no observed alias collision exists.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, S1): PASS - actual parquet order matches.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, S11/S12): PASS - exported parquet contains only fact keys, categoricals, and metrics.
- Canonical column vocabulary (S16): PASS - no education-specific vocabulary applies; `county_fips`, `demographic`, `facility_type`, and `num_*` metric names are coherent.
- Shared categorical utilities applied (S10a): PASS - demographics use `normalize_demographic_column`; no grade or subject columns exist.
- Tidy long format (S9): PASS - demographics and facility type are row values, not metric columns.
- FK keys present in dimension tables (S13): PASS - validation confirms all county and demographic keys resolve.
- Contract-driven API semantics: PASS - row grain and filterable categoricals are contract-visible; county and demographic FKs are declared.
- Standards compliance: PASS - IDs remain strings, counts are Int64, no suppression markers survive, no name/crosswalk/PII columns are served.

## Spot Checks

### Check 1

- Bronze: all retained 2025 placement tuples after cleaning.
- Transform path: `_clean_rows` -> `_reduce_to_placements` -> `_aggregate_slices` (`transform.py:317-420`, `425-519`, `619-653`).
- Gold: state `year=2025`, `county_fips=NULL`, `demographic=all`, `facility_type=all` has `num_new_placements=3752`, `num_placements=6081`, `num_youth=4854`.
- Result: MATCH - independent recomputation produced exactly 3,752 new placements, 6,081 placements, and 4,854 youths.

### Check 2

- Bronze: two 2022 CALHOUN residence placement tuples for juvenile `1856354` have NULL admission dates at TERRELL and WAYCROSS, plus one ordinary RYDC placement in the cell.
- Transform path: sentinel/NULL admitted dates are not new admissions; placement counts use tuple count (`transform.py:483-493`, `603-616`).
- Gold: `year=2022`, `county_fips=13037`, `demographic=all`, `facility_type=rydc` has `num_new_placements=1`, `num_placements=3`, `num_youth=2`.
- Result: MATCH - the NULL-admission placements count as active placements and youths but not as new placements.

### Check 3

- Bronze: 2025 OUT OF STATE residence placement tuples compute to 70 new placements, 99 placements, and 88 youths.
- Transform path: `_resolve_county_fips` maps OUT OF STATE to state-rollup-only; county aggregation filters NULL `county_fips`, while state aggregation keeps all placements (`transform.py:557-595`, `674-698`).
- Gold: 2025 state `all/all` row is 6,081 placements; county `all/all` sum is 5,982 placements, leaving an out-of-state gap of 99.
- Result: MATCH - out-of-state placements are excluded from county rows and retained in the statewide row.

### Check 4

- Bronze: juvenile `1972926` in 2025 has three distinct GLYNN residence RYDC placement tuples after collapsing five offense rows: SAVANNAH on 2025-03-26, SAVANNAH on 2025-05-15, and WAYCROSS on 2025-05-15.
- Transform path: placement identity is `(year, juvenile_id, admitted_date, site_name)` and `is_new` is true when admitted year equals row year (`transform.py:440-493`).
- Gold: the relevant GLYNN/Black/male/RYDC aggregate includes these three as new placements and active placements.
- Result: MATCH - tuple identity preserves same-day different-site placements rather than collapsing them by youth/year.

## Notes

- No must-fix items were identified.
- The source's official "new instances" definition excludes undetectable same-type transfers. The transform serves a documented tuple-based `num_new_placements` reconstruction and discloses the likely overstatement in the contract; this is not a transform accuracy defect against the served metric definition.
- No additional small-cell masking is applied because the public source is already pseudonymized row-level data and gold aggregates are less disclosive than bronze; this is documented in `transform.py` and the contract.
