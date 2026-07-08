# Data Review: out_of_home_placement

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze-to-gold reconstruction matches the served parquet cell-for-cell; no required fixes found.

## Summary

- Review date: 2026-07-02
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze checksum gate passed for the single CSV; transform mtime `2026-07-02T13:16:35Z` precedes manifest `2026-07-02T13:19:29Z`, and validation `2026-07-02T13:21:02Z` is newer than the manifest with `passed: true`.

## Files Reviewed

- Transform: `src/etl/criminal_justice/juvenile_clearinghouse/out_of_home_placement/transform.py`
- Contract: `contracts/criminal_justice/out_of_home_placement.odcs.yaml`
- Bronze files: `decision_point_raw_data_ohp_stp_2026-06.csv` plus `_provenance.md` and `bronze-data-structure.md`; checksum gate reported 1/1 data file matching and no unanalyzed files.
- Gold files: 21 `year=YYYY/counties.parquet` files for 2005-2025; no state files.
- Manifest: `data/gold/criminal_justice/out_of_home_placement/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/out_of_home_placement/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, data-cleaning standards and checklist, bronze/transform/review/fix/full-pipeline skills, `AGENTS.md`, `CLAUDE.md`, `src/etl/CLAUDE.md`, `src/etl/criminal_justice/CLAUDE.md`, and relevant `src/utils/` modules.

## Contract Verification

- Schema/parquet column match: PASS - contract properties exactly match parquet order: `year`, `county_fips`, `demographic`, `all_commitments`, `felony_commitments`, `felony_commitments_ohp`, `all_stp_admissions`, `felony_stp_admissions`.
- Column roles and grain: PASS - roles are `year`, `fk_county`, `fk_demographic`, and five `metric` columns; grain is `year`, `county_fips`, `demographic`, matching actual uniqueness.
- Metric units and derived quality checks: PASS - all metrics are `unit: count`; non-negative checks are emitted and pass.
- Categorical enums: PASS - `demographic` enum is `all`, `black`, `hispanic`, `other`, `white`, matching manifest and gold distinct values.
- Detail levels and layout metadata: PASS - `detail_levels: [counties]`, default `counties`, path template, partition column, local and S3 servers match actual layout.
- Foreign-key descriptors: PASS - `county_fips -> counties` and `demographic -> demographics` descriptors match the actual keys; no school/district FK applies.
- Schema hash/version consistency: PASS - version `1.0.0`, schema hash `a1589d9ae9e7de3e21c0b9fe09487172023a284780d9f892e5877f3a56d36b69`, year range `2005-2025`, and available years match gold.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp `2026-07-02T13:21:02.399130+00:00` is newer than manifest `2026-07-02T13:19:29.839121+00:00`; `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 19 checks passed, 0 failed, 0 warnings; `contract_parquet_schema`, `grain_uniqueness`, `contract_quality_sql`, `foreign_keys`, and `canonical_vocabulary` all pass.
- Validator warnings explained: N/A - validation reported no warnings.
- section 15b quality-check coverage (cross-column invariants authored): PASS - contract has 15 SQL checks covering non-empty, demographic enum, non-negative counts, subset relationships, race-sum-to-total invariants, and structural NULL/populated rules for race vs all rows.

## Manifest Verification

- Files processed coverage: PASS - manifest processed the single current CSV, row count 2,921, fixed 16-column schema, era `era_1_2005_2025_single_csv`; markdown/provenance files are non-data docs.
- Categorical and recode coverage: PASS - demographic map covers `All`, `Black`, `White`, `Hispanic`, `Other`; produced canonical values `all`, `black`, `white`, `hispanic`, `other`; `unmapped_count: 0`.
- Row-count reconciliation: PASS - bronze 2,921 rows; explicit OUT OF STATE drops 21; kept county-years 2,900; gold rows 14,500 = 2,900 x 5 demographic rows. Per-year expected gold counts exactly matched actual.
- Metric stats sanity: PASS - count metrics are non-negative; expected NULL pattern is 80% NULL for unsplit metrics because they are published only on `demographic='all'`; split metrics are populated on all rows.

## Row and Join Accounting

- Bronze file/year disposition: PASS - one CSV spans 2005-2025; all 21 years appear in manifest and gold.
- Filter accounting: PASS - exactly 21 OUT OF STATE pseudo-county rows, one per year, are explicitly filtered as not representable with the counties FK; no gold row has `county_fips` NULL or `13222`.
- Join accounting: PASS - transform does not enrich fact rows through a row-multiplying join. Its county dimension guard verifies 159 kept `(CountyName, CountyFips)` pairs; validator confirms all 159 county keys and all 5 demographic keys resolve.
- Deduplication accounting: PASS - bronze has 0 duplicate `(CountyName, PeriodYear)` groups and kept rows have 0 duplicate `(CountyFips, PeriodYear)` groups; gold has 0 duplicate natural-key groups.
- Aggregation/unpivot accounting: PASS - no collapsed aggregation is performed. Wide race splits are unpivoted into five rows per kept county-year; independent reconstruction from bronze produced 14,500 rows and matched gold exactly.

## Reconciliation Checks

- Artifact freshness: PASS - bronze checksum gate passed; required manifest, contract, validation report, bronze profile, gold parquet, and transform are present and fresh.
- Contract freshness: PASS - contract matches current parquet schema/order and has no `_metadata.json` dependency.
- Year coverage: PASS - bronze, manifest, contract available years, and gold all cover 2005-2025 with no gaps.
- Row preservation: PASS - all kept bronze county-year rows are preserved as five gold demographic rows; only documented OUT OF STATE pseudo-county rows are excluded.
- Column coverage: PASS - every fact key, fact categorical, and fact metric in the bronze profile maps to gold; `CountyName` is correctly excluded as a dimension attribute.
- Recode accuracy: PASS - demographic recodes are semantically correct for the source's four exhaustive race buckets.
- Asian-family demographic recodes (section 5b): N/A - source has no Asian or Pacific Islander labels; its four race buckets sum to the parent totals, and `Other` is documented as absorbing remaining race categories.
- Demographic mutual exclusivity (section 5a - no rollup row alongside split source rows in the same category): PASS - race values are `black`, `white`, `hispanic`, `other`; `all` is the only aggregate lane; no split/combined Asian-family collision exists.
- Demographic collision aggregation before dedup (section 5): N/A - transform-controlled labels map one-to-one to canonical demographics, so no collisions occur.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - parquet order is `year`, `county_fips`, `demographic`, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, section 11/12): PASS - gold parquet contains no `CountyName`, `county_name`, `topic`, `detail_level`, or crosswalk IDs.
- Canonical column vocabulary (section 16): PASS - validator reports no canonical vocabulary violations.
- Shared categorical utilities applied (section 10a): PASS - demographic normalization uses `normalize_demographic_column`; no grade/subject columns apply.
- Tidy long format (section 9): PASS - race splits are in `demographic`, not wide race columns; years are partitions and row values, not columns.
- FK keys present in dimension tables (section 13): PASS - all 159 county FIPS values resolve in `data/gold/_dimensions/counties.parquet`; all 5 demographics resolve in `data/gold/_dimensions/demographics.parquet`.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - contract exposes county and demographic FKs, demographic enum/filter surface, count units, and key metric `felony_commitments_ohp`. Contract limitations document that race rows do not publish the headline OHP metric.
- Standards compliance (catch-all for sections 1-16 items not enumerated above): PASS - IDs are strings, counts are `Int64`, year is `Int32`, no suppression markers survive, no direct gold edit/stale output detected, and no unsupported state rollup is fabricated.

## Spot Checks

### Check 1

- Bronze: CSV row 57, `FULTON`, `PeriodYear=2005`, `CountyFips=13121`, `AllCommitments=85`, `FelonyCommitments=34`, `FelonyCommitmentsOhp=16`, `AllStpAdmissions=73`, `FelonyStpAdmissions=14`, race splits `31/2/1/0` felony and `67/2/4/0` STP for Black/White/Hispanic/Other.
- Transform path: `_transform_ohp_stp` unpivots all and race rows at `transform.py:315-354`.
- Gold: `year=2005`, `county_fips=13121` has `all` row `85,34,16,73,14`; `black=31/67`, `white=2/2`, `hispanic=1/4`, `other=0/0` for the split metrics and NULLs for unsplit race metrics.
- Result: MATCH

### Check 2

- Bronze: CSV row 2873, `MADISON`, `PeriodYear=2025`, `CountyFips=13195`, `AllCommitments=3`, `FelonyCommitments=3`, `FelonyCommitmentsOhp=2`, `AllStpAdmissions=3`, `FelonyStpAdmissions=2`, race splits `1/2/0/0` felony and `1/2/0/0` STP.
- Transform path: strict year/count casts, FIPS guard, and race unpivot at `transform.py:299-354`.
- Gold: `year=2025`, `county_fips=13195` has matching `all`, `black`, `white`, `hispanic`, and `other` rows; race-row unsplit metrics are NULL.
- Result: MATCH

### Check 3

- Bronze: CSV row 172, `CHATHAM`, `PeriodYear=2006`, `CountyFips=13051`, max headline `FelonyCommitmentsOhp=102`, with `AllCommitments=233`, `FelonyCommitments=123`, `AllStpAdmissions=203`, `FelonyStpAdmissions=63`; felony race sum `113+6+2+2=123`, STP race sum `189+13+1+0=203`.
- Transform path: subset metrics preserved on the `all` row and race split metrics unpivoted at `transform.py:315-354`; subset/race-sum checks authored at `transform.py:650-790`.
- Gold: `year=2006`, `county_fips=13051` has `all` row `233,123,102,203,63` and race rows matching the bronze split values.
- Result: MATCH

### Check 4

- Bronze: CSV row 2885, `OUT OF STATE`, `PeriodYear=2025`, `CountyFips=NULL`, `AllCommitments=5`, `FelonyCommitments=5`, `FelonyCommitmentsOhp=0`; similar OUT OF STATE rows exist once per year.
- Transform path: `_drop_out_of_state_and_key_fips` filters these pseudo-county rows and records them at `transform.py:242-282`.
- Gold: no 2025 row exists with `county_fips IS NULL` or `county_fips='13222'`; manifest records `out_of_state_pseudo_county_row: 21`.
- Result: MATCH

### Check 5

- Bronze: independent in-memory reconstruction from the CSV dropped only OUT OF STATE rows, cast counts, created one `all` row plus four race rows per kept county-year, and selected the contract columns.
- Transform path: same intended flow as `transform.py:285-354`, without importing the transform.
- Gold: reconstructed expected rows = 14,500; actual gold rows = 14,500; full sorted DataFrames were equal.
- Result: MATCH

## Notes

- No prior `data-review-claude.md` or existing `data-review-codex.md` content was read before forming this verdict.
- No transform, contract, bronze, gold, docs, or utility files were edited.
