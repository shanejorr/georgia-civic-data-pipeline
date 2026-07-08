# Data Review: recidivism_reconviction

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: The current gold output is fresh, validator-clean, and reconciles exactly to all 192 source PDF matrix cells; no transform accuracy fixes are required.

## Summary

- Review date: 2026-07-07
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze checksum gate passed for both PDFs; transform mtime `2026-07-07T04:06:26.247812+00:00`, manifest `2026-07-07T04:17:18.229192+00:00`, validation `2026-07-07T04:17:18.287811+00:00`.

## Files Reviewed

- Transform: `src/etl/criminal_justice/gdc/recidivism_reconviction/transform.py`
- Contract: `contracts/criminal_justice/recidivism_reconviction.odcs.yaml`
- Bronze files: `reconviction_3yr_cy.pdf`, `reconviction_3yr_fy.pdf`; direct `pdftotext -layout` inspection confirmed the two 8-row x 12-year matrices.
- Gold files: 13 `states.parquet` files under `data/gold/criminal_justice/recidivism_reconviction/year=2011` through `year=2023`.
- Manifest: `data/gold/criminal_justice/recidivism_reconviction/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/recidivism_reconviction/_validation.json`
- Supporting docs: `bronze-data-structure.md`, `_provenance.md`, `docs/codex-review-contract.md`, `docs/contract-creation.md`, data-cleaning standards, criminal-justice domain conventions, ETL guide, and sibling GDC transform patterns.

## Contract Verification

- Schema/parquet column match: PASS - contract properties and every parquet file use `year`, `demographic`, `reporting_period`, `facility_type`, `reconviction_rate_3yr` in that order.
- Column roles and grain: PASS - grain is `year, demographic, reporting_period, facility_type`; roles match the transform declaration and source matrix axes.
- Metric units and derived quality checks: PASS - `reconviction_rate_3yr` is `unit: proportion`, key metric, and the contract includes the derived `[0,1]` quality check.
- Categorical enums: PASS - contract enums match manifest and gold values: `demographic` = `all/female`, `reporting_period` = `calendar_year/fiscal_year`, `facility_type` = `all/county_ci/private_prison/state_prison_ibc/transition_center`.
- Detail levels and layout metadata: PASS - contract declares `detail_levels: [states]`, `default_detail: states`, partition by `year`, and `path_template` matching the gold layout.
- Foreign-key descriptors: PASS - demographic FK only; `all` and `female` resolve in `data/gold/_dimensions/demographics.parquet`. No `county_fips` is present because this GDC source is statewide only, matching the established sibling `inmate_population` convention.
- Schema hash/version consistency: PASS - version `1.0.0`, schema hash `a6ed7bbae00fe7481f49c9830e33ec6bdf51e727869e34ccef85edf96c523ae2`, available years `2011-2023` with no gaps.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp is after manifest generation and reports `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 19 pass, 0 fail, 0 warning; schema, grain uniqueness, all 10 quality SQL checks, FK, and vocabulary checks pass.
- Validator warnings explained: N/A - no warnings.
- §15b quality-check coverage (cross-column invariants authored): PASS - authored checks cover year floor, non-null rate cells, 8 rows per cohort edition, full-cohort rollup bracket, and female facility-type shape; source publishes no numerator/denominator counts, so no component-total invariant applies.

## Manifest Verification

- Files processed coverage: PASS - manifest processes both current data PDFs; `_provenance.md` and `bronze-data-structure.md` are documentation artifacts. Current SHA-256 values match the structure report.
- Categorical and recode coverage: PASS - every observed raw label/title maps semantically to the expected gold value and every `unmapped_count` is 0.
- Row-count reconciliation: PASS - manifest records 192 source matrix cells and 192 gold rows; per-year counts match expected CY-only 2011, FY-only 2023, and both editions for 2012-2022.
- Metric stats sanity: PASS - rates range from `0.097` to `0.339`, null count is 0 in every year, and values are on the 0-1 proportion scale.

## Row and Join Accounting

- Bronze file/year disposition: PASS - CY PDF contributes 8 rows for each cohort year 2011-2022; FY PDF contributes 8 rows for each fiscal cohort year 2012-2023.
- Filter accounting: PASS - `YEAR_FLOOR = 2000` removes 0 rows because all source cohort years are 2011-2023.
- Join accounting: N/A - transform performs no data joins; the only FK validation is demographic dimension membership after export.
- Deduplication accounting: PASS - natural-key collision guard runs before `deduplicate_by_levels`; actual gold has 0 duplicate grain groups.
- Aggregation/unpivot accounting: PASS - the only reshape is wide PDF matrix cells to long observations. No rates are derived or aggregated; `facility_type='all'` rows are source-published rollups.

## Reconciliation Checks

- Artifact freshness: PASS - transform, manifest, contract, validation, and bronze checksums are current.
- Contract freshness: PASS - contract was emitted after the manifest from the current transform/gold and has no `_metadata.json` dependency.
- Year coverage: PASS - gold years are 2011-2023; CY covers 2011-2022 and FY covers 2012-2023.
- Row preservation: PASS - an independent `pdftotext` reconciliation produced 192 expected cells, 192 gold rows, 0 missing rows, 0 extra rows, and 0 value mismatches.
- Column coverage: PASS - source year header, edition, row stub facility/sex, and cell rate all land in gold; report date/page furniture are correctly excluded.
- Recode accuracy: PASS - raw row-label casing drift is normalized without semantic collapse; all-facility rows map to the `facility_type='all'` rollup lane, not a member facility.
- Asian-family demographic recodes (§5b): N/A - source has no race/ethnicity demographics.
- Demographic mutual exclusivity (§5a - no rollup row alongside split source rows in the same category): PASS - demographic values are only `all` and `female`; no male row is synthesized and `all` is the permitted overlap lane.
- Demographic collision aggregation before dedup (§5): N/A - raw sex labels map one-to-one to `all` or `female`; no subgroup collision exists.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS - statewide-only established GDC pattern has no geography key; remaining order is `year`, `demographic`, categoricals, metric.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS - parquet contains none of these; `detail_level` is encoded by `states.parquet`.
- Canonical column vocabulary (§16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - validator reports no canonical vocabulary violations; education-specific vocabulary is N/A.
- Shared categorical utilities applied (§10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no grade or subject column; demographic uses `normalize_demographic_column`.
- Tidy long format (§9 - no demographics/years/components as column names): PASS - wide PDF year columns are unpivoted into one row per cohort-year observation.
- FK keys present in dimension tables (§13 - `district_code`, `school_code`, `demographic`): PASS - demographic FK resolves for `all` and `female`; no district, school, or county FK is present for this statewide-only source.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - categorical filters are `reporting_period` and `facility_type`; demographic FK enables `demographic_category` filtering.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS - no suppression markers, no impossible values, no §4b masks, no read-loss events, and no unstated row loss.

## Spot Checks

### Check 1

- Bronze: Independent `pdftotext` parse of both PDFs produced 192 expected observations from 16 physical matrix rows x 12 year columns. Examples include CY `All inmate facilities **` 2011 = `26.90`, CY `All Female Facilities **` 2012 = `20.80`, FY `Female transition centers` 2022 = `9.70`, and FY `State prison, IBCs` 2023 = `33.90`.
- Transform path: `_parse_matrix` and `transform_file`, `transform.py:249-440`; rates are divided by 100 at `transform.py:434-439`.
- Gold: Reconciliation against `data/gold/criminal_justice/recidivism_reconviction/year=*/*.parquet` found 192 expected rows, 192 gold rows, 0 missing, 0 extra, 0 mismatches.
- Result: MATCH

### Check 2

- Bronze: `reconviction_3yr_cy.pdf`, row `All inmate facilities **`, cohort year `2011`, value `26.90`.
- Transform path: row label maps to `demographic='all'`, `facility_type='all'`; `rate_percent / 100.0` at `transform.py:434-439`.
- Gold: `year=2011`, `demographic='all'`, `reporting_period='calendar_year'`, `facility_type='all'`, `reconviction_rate_3yr=0.269`.
- Result: MATCH

### Check 3

- Bronze: `reconviction_3yr_cy.pdf`, row `All Female Facilities **`, cohort year `2012`, value `20.80`.
- Transform path: raw sex label `Female` normalizes through `normalize_demographic_column`; rollup row maps to `facility_type='all'`, `transform.py:381-439`.
- Gold: `year=2012`, `demographic='female'`, `reporting_period='calendar_year'`, `facility_type='all'`, `reconviction_rate_3yr=0.208`.
- Result: MATCH

### Check 4

- Bronze: `reconviction_3yr_fy.pdf`, row `Female transition centers`, cohort year `2022`, value `9.70` (the global minimum).
- Transform path: FY title maps to `reporting_period='fiscal_year'`; lowercase row-label drift normalizes before mapping, `transform.py:264-277` and `transform.py:381-439`.
- Gold: `year=2022`, `demographic='female'`, `reporting_period='fiscal_year'`, `facility_type='transition_center'`, `reconviction_rate_3yr=0.097`.
- Result: MATCH

### Check 5

- Bronze: `reconviction_3yr_fy.pdf`, row `State prison, IBCs`, cohort year `2023`, value `33.90` (the global maximum).
- Transform path: raw facility stub maps to `state_prison_ibc`; value is divided by 100, `transform.py:389-439`.
- Gold: `year=2023`, `demographic='all'`, `reporting_period='fiscal_year'`, `facility_type='state_prison_ibc'`, `reconviction_rate_3yr=0.339`.
- Result: MATCH

### Check 6

- Bronze: CY 2012 female rollup `All Female Facilities **` = `20.80`; member female rows are `Female State prison, IBCs` = `20.60` and `Female Transition centers` = `19.80`.
- Transform path: transform preserves all three as source-published rows and deliberately does not derive or bracket-check the female rollup, `transform.py:66-77` and `transform.py:810-821`.
- Gold: `female/all/calendar_year/2012=0.208`, `female/state_prison_ibc/calendar_year/2012=0.206`, `female/transition_center/calendar_year/2012=0.198`; the rollup exceeding both members confirms the member rows do not exhaust the female rollup.
- Result: MATCH

## Notes

- No prior `data-review-claude.md` or existing `data-review-codex.md` content was used to form this review.
- Existing worktree status showed `src/etl/criminal_justice/gdc/recidivism_reconviction/data-review-claude.md` already modified; this review did not read or alter it.
- No must-fix findings were identified, so `## Required Fixes` is intentionally omitted.
