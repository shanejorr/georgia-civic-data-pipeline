# Data Review: juvenile_court_cases

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze JSON rows, categorical recodes, suppression handling, county/state row counts, contract schema, validator output, and gold parquet values reconcile with no required transform fixes.

## Summary

- Review date: 2026-07-03
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH — bronze freshness gate passed; transform mtime `2026-07-03T01:13:03+00:00` predates manifest `2026-07-03T01:18:09+00:00`; validation `2026-07-03T01:19:19+00:00` is newer than the manifest and passed.

## Files Reviewed

- Transform: `src/etl/criminal_justice/ojjdp/juvenile_court_cases/transform.py`
- Contract: `contracts/criminal_justice/juvenile_court_cases.odcs.yaml`
- Bronze files: 26 JSON files, `ezaco_ga_county_case_counts_1997.json` through `ezaco_ga_county_case_counts_2023.json`, with 2014 absent by source design
- Gold files: 52 parquet files, `year=*/counties.parquet` and `year=*/states.parquet` for 26 years
- Manifest: `data/gold/criminal_justice/juvenile_court_cases/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/juvenile_court_cases/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, data-cleaning standards/checklist, bronze/transform/review/fix/full-pipeline skills, `AGENTS.md`, `CLAUDE.md`, `src/etl/criminal_justice/CLAUDE.md`, topic `bronze-data-structure.md`, topic `_provenance.md`, and relevant shared utility snippets

## Contract Verification

- Schema/parquet column match: PASS — contract properties exactly match parquet columns: `year`, `county_fips`, `case_type`, `petition_status`, `reporting_status`, `case_count`, `case_rate_per_1000`, `counties_reporting`.
- Column roles and grain: PASS — contract grain is `year`, `county_fips`, `case_type`, `petition_status`, `reporting_status`; roles match the transform's authored columns and the exported star-schema fact table.
- Metric units and derived quality checks: PASS — `case_count` and `counties_reporting` carry `unit: count`; `case_rate_per_1000` intentionally omits a 0-1 unit and has an authored non-negative SQL check.
- Categorical enums: PASS — contract enums match manifest/gold values for `case_type`, `petition_status`, and `reporting_status`.
- Detail levels and layout metadata: PASS — contract advertises `counties` and `states`, partitioned by `year`, with path template `criminal_justice/juvenile_court_cases/year={year}/{detail}.parquet`.
- Foreign-key descriptors: PASS — `county_fips` targets the global counties dimension; direct FK check found all 159 county keys resolve.
- Schema hash/version consistency: PASS — version is `1.0.0`, schema hash is `0e0036f7ce4fb3de8f7a72a1742fd9359de3fc305224d00bacdfe9495a4e39e7`, and gold/contract were emitted in the same run.

## Validator Verification

- `_validation.json` fresh + passing: PASS — validation timestamp `2026-07-03T01:19:19.691864+00:00`; `passed: true`; summary `19 pass`, `0 fail`, `1 warning`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS — schema, grain uniqueness, 20 contract SQL checks, FK integrity, canonical vocabulary, and geography nulling all passed.
- Validator warnings explained: PASS — null-rate warnings for `case_count` in 2009, 2015-2017, 2019, and 2021-2023 match the documented voluntary-reporting coverage collapse.
- §15b quality-check coverage (cross-column invariants authored): PASS — contract checks enforce reporting status/count co-null rules, state coverage counts, state-vs-county sum relationships, state-only rates, all 159 county rows per measure, and county-count bounds.

## Manifest Verification

- Files processed coverage: PASS — all 26 current bronze JSON files appear in `files_processed`; no missing or extra manifest files; checksums pass.
- Categorical and recode coverage: PASS — `unmapped_count == 0` for `case_type`, `petition_status`, `reporting_status`, and `county_fips`; maps are semantically correct.
- Row-count reconciliation: PASS — each bronze file has 160 rows; each year expands to 960 gold rows via 6-measure unpivot; total bronze 4,160 and total gold 24,960.
- Metric stats sanity: PASS — counts are non-negative; rates are non-negative source per-1,000 values; `case_count` NULL spikes align with reporting gaps and suppression.

## Row and Join Accounting

- Bronze file/year disposition: PASS — 1997-2013 and 2015-2023 are processed; 2014 is absent from bronze and absent from gold.
- Filter accounting: N/A — no source rows are filtered; all 160 rows per file survive as 6 unpivoted measure rows.
- Join accounting: N/A — no transform-time joins; county FIPS is derived from source `fst`/`fct`, and post-export FK validation resolves all 159 counties.
- Deduplication accounting: PASS — no duplicate final grain groups exist; safety dedup does not remove rows in the current one-file-per-year inventory.
- Aggregation/unpivot accounting: PASS — unpivot expansion is exactly 160 rows x 6 measures = 960 rows per year; state rows preserve NCJJ state aggregates rather than deriving new totals.

## Reconciliation Checks

- Artifact freshness: PASS — bronze freshness gate passed and validation is newer than manifest.
- Contract freshness: PASS — contract was emitted immediately after the manifest from current transform/gold; no `_metadata.json` dependency.
- Year coverage: PASS — gold years are 1997-2013 and 2015-2023; there are zero 2014 rows.
- Row preservation: PASS — every bronze row has six gold measure rows; county detail has 159 counties x 6 rows = 954 rows per year, state detail has 6 rows per year.
- Column coverage: PASS — fact keys/categoricals/metrics from the structure report are represented or validly documented as dropped dimension/metadata fields.
- Recode accuracy: PASS — `petdel/nonpetdel/petsta/nonpetsta/petdep/nonpetdep` map correctly to `case_type` and `petition_status`; reporting flag/value shapes map correctly to `reported`, `suppressed`, and `not_reported`.
- Asian-family demographic recodes (§5b): N/A — no demographic/race fields exist.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): N/A — no demographic column.
- Demographic collision aggregation before dedup (§5): N/A — no demographic normalization.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS — parquet order is `year`, `county_fips`, categoricals, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS — exported parquet omits `detail_level`, `court`, names, and metadata constants.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): N/A — no education assessment vocabulary applies; CJ column names are descriptive and snake_case.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A — no grade or subject column.
- Tidy long format (§9 — no demographics/years/components as column names): PASS — six wide source measures are unpivoted into `case_type` x `petition_status` rows.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS — all 159 `county_fips` values appear in `data/gold/_dimensions/counties.parquet`.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS — categoricals are independent filters; county FK joins derive from the contract.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS — suppression markers become NULL, zeros remain real zeros, state geography is NULL, and county FIPS strings preserve the `13` prefix and leading zeros.

## Spot Checks

### Check 1

- Bronze: `ezaco_ga_county_case_counts_1997.json`, Atkinson `fct="3"`, `petdep="*"`, `reportingflag_petdep="1"`.
- Transform path: `_unpivot_measures()` and `_to_gold_shape()` (`transform.py:301-319`, `447-538`) map `petdep` to dependency/petitioned and marker `*` to suppressed NULL.
- Gold: `year=1997`, `county_fips="13003"`, `case_type="dependency"`, `petition_status="petitioned"`, `reporting_status="suppressed"`, `case_count=NULL`.
- Result: MATCH

### Check 2

- Bronze: `ezaco_ga_county_case_counts_2009.json`, Bartow `fct="15"`, `nonpetsta="154"`, `reportingflag_nonpetsta="1"`.
- Transform path: `_strip_commas_cast()` and `_to_gold_shape()` (`transform.py:344-347`, `447-538`) cast the count and map `nonpetsta` to status offense/non-petitioned.
- Gold: `year=2009`, `county_fips="13015"`, `case_type="status_offense"`, `petition_status="non_petitioned"`, `reporting_status="reported"`, `case_count=154`.
- Result: MATCH

### Check 3

- Bronze: `ezaco_ga_county_case_counts_2023.json`, Bartow `fct="15"`, `nonpetsta="*"`, `reportingflag_nonpetsta="1"`.
- Transform path: `_record_suppression_masks()` records marker masks and `_to_gold_shape()` emits `reporting_status="suppressed"` (`transform.py:411-445`, `447-538`).
- Gold: `year=2023`, `county_fips="13015"`, `case_type="status_offense"`, `petition_status="non_petitioned"`, `case_count=NULL`, `case_rate_per_1000=NULL`.
- Result: MATCH

### Check 4

- Bronze: `ezaco_ga_county_case_counts_2023.json`, state row `fct="0"`, `petdel="11,708"`, `reportingflag_petdel="41"`, `petdelrate="15.70"`.
- Transform path: `_to_gold_shape()` emits NULL county FIPS, NULL reporting_status, state rate, and counties_reporting (`transform.py:447-538`).
- Gold: `year=2023`, state delinquency/petitioned row has `county_fips=NULL`, `case_count=11708`, `case_rate_per_1000=15.7`, `counties_reporting=41`.
- Result: MATCH

### Check 5

- Bronze: `ezaco_ga_county_case_counts_2023.json`, Appling `fct="1"`, `petdep="--"`, `reportingflag_petdep="0"`.
- Transform path: guarded row-shape logic maps flag 0 + `--` to `not_reported` and NULL count (`transform.py:350-409`, `478-496`).
- Gold: `year=2023`, `county_fips="13001"`, dependency/petitioned row has `reporting_status="not_reported"`, `case_count=NULL`.
- Result: MATCH

### Check 6

- Bronze: aggregate reconciliation examples: 1997 `petdel` state `61,619` vs visible county sum `61,612` with 3 suppressed cells; 2023 `petdel` state `11,708` equals visible county sum `11,708`; 2023 `petdep` state `--` with 0 reporting counties.
- Transform path: state rows are preserved as source aggregates; contract quality checks enforce state/counties relationships (`transform.py:1006-1049`).
- Gold: state/counties relationship checks pass in `_validation.json` and direct recomputation produced no state/count reconciliation errors.
- Result: MATCH

## Needs Follow-up

- The transform/contract wording says state rates were verified equal to `case_count / reporting-population x 1000` exactly. One direct display-denominator recomputation differs by 0.01 (`2009 petdel`: `16685 / 441000 * 1000 = 37.83`, source/gold rate `37.84`), likely because the source displays rounded population denominators while serving its own rounded rate. The served gold value correctly preserves the bronze rate, so this is metadata wording only, not a transform accuracy fix.

## Notes

- No prior `data-review-claude.md` or `data-review-codex.md` content was read before this report.
- The validator warning is expected for this topic because reporting coverage changes sharply by year and measure.
- No required fixes were found.
