# Data Review: inmate_releases_county

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: The current gold output accurately preserves the two GDC PDF tables under the documented county/state grain; no required fixes were found.

## Summary

- Review date: 2026-07-07
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - transform mtime 2026-07-07T04:06:26Z; manifest generated 2026-07-07T04:09:33Z; contract mtime 2026-07-07T04:09:33Z; validation timestamp 2026-07-07T04:09:33Z and passed.

## Files Reviewed

- Transform: `src/etl/criminal_justice/gdc/inmate_releases_county/transform.py`
- Contract: `contracts/criminal_justice/inmate_releases_county.odcs.yaml`
- Bronze files: `inmate_release_by_county_cy.pdf`, `inmate_release_by_county_fy.pdf`
- Gold files: 12 parquet files under `data/gold/criminal_justice/inmate_releases_county/year=*/{counties,states}.parquet`
- Manifest: `data/gold/criminal_justice/inmate_releases_county/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/inmate_releases_county/_validation.json`
- Supporting docs: `bronze-data-structure.md`, `_provenance.md`, repo contract/cleaning standards, criminal justice ETL conventions

## Contract Verification

- Schema/parquet column match: PASS - every parquet file has `year`, `county_fips`, `reporting_period`, `inmate_releases` in contract order.
- Column roles and grain: PASS - `year` is the year role, `county_fips` is `fk_county`, `reporting_period` is categorical, `inmate_releases` is the count metric; grain is `year`, `county_fips`, `reporting_period`.
- Metric units and derived quality checks: PASS - `inmate_releases` has `unit: count`, `key_metric: true`, and non-negative / present quality checks.
- Categorical enums: PASS - `reporting_period` enum is exactly `calendar_year`, `fiscal_year`, matching manifest and gold.
- Detail levels and layout metadata: PASS - detail levels are `counties` and `states`; path template is `criminal_justice/inmate_releases_county/year={year}/{detail}.parquet`.
- Foreign-key descriptors: PASS - `county_fips` targets the global `counties` dimension on `county_fips`; 159 populated fact keys resolve.
- Schema hash/version consistency: PASS - contract version is `1.0.0`, schema hash is `c4a7ef2bce93d8898677eec223417cf0c01ec56c5adb69bc8170a4361a5c2e2e`, and contract mtime follows the manifest.

## Validator Verification

- `_validation.json` fresh + passing: PASS - timestamp is newer than manifest generation; `"passed": true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - validation summary is 20 pass, 0 fail, 0 warning.
- Validator warnings explained: N/A - no warnings were emitted.
- Section 15b quality-check coverage (cross-column invariants authored): PASS - contract quality SQL covers non-empty output, reporting-period enum, non-negative/present counts, year floor, 159 county rows per year/edition, one state row per year/edition, state total >= county sum, and five years per reporting period. Exact county + residual = Total reconciliation is asserted in `transform.py` before residual exclusion.

## Manifest Verification

- Files processed coverage: PASS - manifest processes both current non-doc bronze PDFs and no extra files; checksums match `bronze-data-structure.md`; `scripts/check_bronze_freshness.py criminal_justice gdc inmate_releases_county` passed.
- Categorical and recode coverage: PASS - `county_fips` records 159 county label -> FIPS mappings with `unmapped_count: 0`; `reporting_period` maps both printed subtitles to the two canonical values with `unmapped_count: 0`.
- Row-count reconciliation: PASS - logical bronze cells total 1,620, gold rows total 1,600, and the 20 filtered rows are exactly two non-county residual rows per year-edition.
- Metric stats sanity: PASS - `inmate_releases` is non-null, non-negative, integer, and ranges from 0 to 13,730; zeros are source-backed.

## Row and Join Accounting

- Bronze file/year disposition: PASS - CY PDF contributes 2021-2025; FY PDF contributes 2022-2026; both are represented in `files_processed`.
- Filter accounting: PASS - only `999 - Other Custody/Out Of State` and `Unknown, not reported` are filtered, after total reconciliation, with 20 filtered row-year cells recorded under `residual_non_county_rows_excluded_after_total_reconciliation(...)`.
- Join accounting: PASS - county-name resolution produces 159 distinct county FIPS values; normalized counties dimension has no duplicate normalized names; fact keys have 0 orphans.
- Deduplication accounting: PASS - duplicate natural-key count is 0; `deduplicate_by_levels` is a no-op safety net after `assert_no_natural_key_collisions`.
- Aggregation/unpivot accounting: PASS - wide year columns are reshaped to one row per county/state, year, and reporting period; state rows are not derived by summing gold counties, they preserve the PDF `Total` row.

## Reconciliation Checks

- Artifact freshness: PASS - bronze checksums, manifest, contract, and validation are current.
- Contract freshness: PASS - contract emitted from current transform/gold; no `_metadata.json` dependency.
- Year coverage: PASS - `calendar_year` covers 2021-2025 and `fiscal_year` covers 2022-2026; gold partitions span 2021-2026 with no gaps.
- Row preservation: PASS - independent `pdftotext -layout` parse found 1,600 served county/state row-year cells and 0 value mismatches against gold after treating the state row as the NULL county key.
- Column coverage: PASS - gold columns trace to PDF year headers, county labels, report edition subtitle, and integer cells; GDC row prefixes and county names are excluded correctly as non-fact attributes.
- Recode accuracy: PASS - subtitle recodes are semantically correct; county label mappings use county names, not GDC's non-FIPS row index. Examples: `001 - Appling County -> 13001`, `094 - Macon County -> 13193`, `106 - Muscogee County -> 13215`.
- Asian-family demographic recodes (section 5b): N/A - no demographic column.
- Demographic mutual exclusivity (section 5a): N/A - no demographic column.
- Demographic collision aggregation before dedup (section 5): N/A - no demographic column.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - `year`, `county_fips`, `reporting_period`, `inmate_releases`.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, sections 11/12): PASS - exported parquet excludes `detail_level`, `_raw_label`, `_county_name`, and all name fields.
- Canonical column vocabulary (section 16): PASS - validator reports canonical vocabulary clean.
- Shared categorical utilities applied (section 10a): N/A - no grade or subject column.
- Tidy long format (section 9): PASS - years are rows, not metric columns, in gold.
- FK keys present in dimension tables (section 13): PASS - 159 distinct `county_fips` values resolve to `data/gold/_dimensions/counties.parquet`.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - `reporting_period` is filterable, `county_fips` joins to counties, and the key metric is declared as `inmate_releases`.
- Standards compliance (catch-all for sections 1-16 items not enumerated above): PASS - no suppression markers, no percentage scale issues, no impossible count values, no direct gold edits, and no stale output detected.

## Spot Checks

### Check 1

- Bronze: CY PDF row `001 - Appling County` has 2021-2025 values `32, 39, 29, 34, 40`.
- Transform path: `_parse_edition` reads the repeated header and integer row; `transform_file` emits one long row per year; `_resolve_county_fips` maps Appling by county name.
- Gold: `county_fips=13001`, `reporting_period=calendar_year` has `inmate_releases` 32, 39, 29, 34, 40 for 2021-2025.
- Result: MATCH

### Check 2

- Bronze: CY PDF row `026 - Chattahoochee County` has 2025 value `0`.
- Transform path: `_DATA_ROW_RE` parses integer zero; no suppression or masking is applied because zeros are real.
- Gold: `year=2025`, `county_fips=13053`, `reporting_period=calendar_year`, `inmate_releases=0`.
- Result: MATCH

### Check 3

- Bronze: FY PDF row `060 - Fulton County` has 2022-2026 values `955, 895, 883, 964, 1,087`.
- Transform path: subtitle maps to `fiscal_year`; county name maps to FIPS `13121`; thousands commas are stripped during integer parsing.
- Gold: `county_fips=13121`, `reporting_period=fiscal_year` has `inmate_releases` 955, 895, 883, 964, 1087 for 2022-2026.
- Result: MATCH

### Check 4

- Bronze: CY PDF row `094 - Macon County` has 2025 value `19`; FY PDF row has 2026 value `24`.
- Transform path: `_resolve_county_fips` maps bare `Macon County` to real Macon County FIPS `13193`, not Bibb/Macon-Bibb.
- Gold: `year=2025`, `calendar_year`, `county_fips=13193`, `inmate_releases=19`; `year=2026`, `fiscal_year`, `county_fips=13193`, `inmate_releases=24`.
- Result: MATCH

### Check 5

- Bronze: CY 2025 residuals are `999 - Other Custody/Out Of State = 2`, `Unknown, not reported = 1,047`, and `Total = 13,422`.
- Transform path: `_reconcile_totals` verifies 159 county rows + residuals equal the printed Total, then `transform_file` filters residual rows and emits `Total` as the state row.
- Gold: CY 2025 county sum is 12,373; state row is 13,422; residual gap is 1,049, exactly `2 + 1,047`.
- Result: MATCH

## Notes

- Independent `pdftotext -layout` parsing found each PDF has four identical repeated year headers, 162 table rows, 159 county rows, two residual rows, and one Total row.
- Reconciliation from that independent parse was exact for all 10 year/reporting-period combinations: `county_sum + residual = Total`, with diff 0.
- The residual rows are not served as separate fact rows by design. Their counts remain represented in the state Total row, and the contract warns users that county rows sum below statewide totals.
