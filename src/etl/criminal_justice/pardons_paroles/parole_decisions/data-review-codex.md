# Data Review: parole_decisions

## Verdict

**Status**: NEEDS FIXES
**Must-fix count**: 1

Summary: served release, guideline, life-case, revocation, population, completion-rate, and expenditure values reconcile to the PDFs, but the transform omits the cost-avoidance / cost-per-day metric family that the bronze profile classifies as fact metrics.

## Summary

- Review date: 2026-07-07
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze freshness gate passed for all 25 PDF checksums; transform mtime `2026-07-07T04:06:26Z` is older than manifest `2026-07-07T04:35:49Z`; validation timestamp `2026-07-07T04:35:49Z` is newer than the manifest and passed.

## Files Reviewed

- Transform: `src/etl/criminal_justice/pardons_paroles/parole_decisions/transform.py`
- Contract: `contracts/criminal_justice/parole_decisions.odcs.yaml`
- Bronze files: 25 PDFs, FY2001-FY2025 with FY2015 absent and `annual_report_fy2016_spread.pdf` kept as a duplicate provenance file only
- Gold files: 24 `year=*/states.parquet` files, years 2001-2014 and 2016-2025
- Manifest: `data/gold/criminal_justice/parole_decisions/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/parole_decisions/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, data-cleaning standards, transform-topic, data-review-claude, fix-from-reviews, full-pipeline, `AGENTS.md`, `CLAUDE.md`, `src/etl/CLAUDE.md`, `src/etl/criminal_justice/CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS - contract properties exactly match the 22 parquet columns in order.
- Column roles and grain: PASS - `year` is the year key, `supervision_era` is categorical, all remaining columns are metrics; grain is `year, supervision_era`.
- Metric units and derived quality checks: PASS - count metrics are `unit: count`, `parole_completion_rate` is `unit: proportion`, and `total_expenditures` is `unit: currency`.
- Categorical enums: PASS - `supervision_era` enum is `board, dcs`, matching manifest and gold.
- Detail levels and layout metadata: PASS - contract declares `states`, path template `criminal_justice/parole_decisions/year={year}/{detail}.parquet`, and no foreign keys.
- Foreign-key descriptors: PASS - statewide-only state series follows the established criminal-justice pattern used by `inmate_population`; no county FK is declared.
- Schema hash/version consistency: PASS - contract version is `1.0.0`, schema hash `6caab5ad63e796fe14882ea42cc517ca18e1671d41792ebce1d34591638a9713`.

## Validator Verification

- `_validation.json` fresh + passing: PASS - `passed: true`; validation timestamp is newer than manifest generation.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 18 pass, 0 fail, 1 warning; `contract_parquet_schema`, `grain_uniqueness`, `contract_quality_sql`, `foreign_keys`, and `canonical_vocabulary` all pass.
- Validator warnings explained: PASS - 39 null-rate warnings match era-scoped metric availability documented in the contract and enforced by `EXPECTED_COVERAGE`.
- §15b quality-check coverage (cross-column invariants authored): PASS - quality SQL covers year floor, FY2015 gap, HB310 era flag, key metric non-nullness, life-decision sum, release-component bounds/reconciliation, parole-release/certificate exclusivity, guidelines initial <= total, and DCS-only start population.

## Manifest Verification

- Files processed coverage: PASS - 24 processed PDFs match the 24 real fiscal years; FY2015 is absent by source, and `annual_report_fy2016_spread.pdf` is intentionally skipped as a duplicate.
- Categorical and recode coverage: PASS - `metric_source_label` has 99 observed labels and `unmapped_count: 0`; `supervision_era` has `board` and `dcs` with `unmapped_count: 0`.
- Row-count reconciliation: PASS - `total_bronze: 24`, `total_gold: 24`, `total_filtered: 0`; every processed fiscal year is one bronze report row to one gold state row.
- Metric stats sanity: PASS for served metrics - count metrics are non-negative, completion rates are 0.60-0.74 on the 0-1 scale, and currency values match published nominal-dollar totals where served.

## Row and Join Accounting

- Bronze file/year disposition: PASS - all current bronze PDFs are processed except `annual_report_fy2016_spread.pdf`, which is documented as a duplicate of the standard FY2016 report.
- Filter accounting: PASS - no rows are filtered; the year floor is defensive only and removes nothing.
- Join accounting: N/A - no joins or lookup enrichment occur.
- Deduplication accounting: PASS - one row per fiscal year; collision guard runs before `deduplicate_by_levels`, and actual duplicate grain count is zero.
- Aggregation/unpivot accounting: N/A - no source rows collapse into aggregate rows; component sums are used as verification checks, not as gold row aggregation.

## Reconciliation Checks

- Artifact freshness: PASS - bronze freshness, manifest, validation, contract, and parquet are current.
- Contract freshness: PASS - contract was emitted from the current transform/gold and has no `_metadata.json` dependency.
- Year coverage: PASS - gold years are 2001-2014 and 2016-2025; no FY2015 partition exists.
- Row preservation: PASS - 24 processed reports produce 24 gold rows with no unexplained row loss or multiplication.
- Column coverage: FAIL - the bronze profile classifies cost avoidance / cost-per-day as fact metrics, but transform, contract, manifest metric stats, and gold all omit that metric family.
- Recode accuracy: PASS - sampled label crosswalks match source semantics, including `Total Prison Releases by Parole -> total_releases`, `Parole Certificates -> parole_certificates`, and `Total Guidelines Decisions -> guidelines_decisions_total`.
- Asian-family demographic recodes (§5b): N/A - no demographic column or race buckets.
- Demographic mutual exclusivity (§5a): N/A - no demographic column.
- Demographic collision aggregation before dedup (§5): N/A - no demographic normalization.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS - `year`, `supervision_era`, then metrics; no geography/demographic columns exist for this statewide-only series.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS - parquet omits `topic`, `detail_level`, names, and crosswalk IDs.
- Canonical column vocabulary (§16): PASS - validator reports no vocabulary violations.
- Shared categorical utilities applied (§10a): N/A - no grade or subject columns.
- Tidy long format (§9): PASS - no years, demographics, or components are encoded as wide categorical columns.
- FK keys present in dimension tables (§13): N/A - no foreign keys are declared.
- Contract-driven API semantics: PASS for current schema - `supervision_era` is the only filterable categorical and `total_releases` is the key metric.
- Standards compliance: FAIL - source-classified cost fact metrics are silently lost from the served fact table.

## Spot Checks

### Check 1

- Bronze: `annual_report_fy2001.pdf` text has `TOTAL RELEASES 10,164`, `TOTAL DECISIONS UNDER GUIDELINES 13,630`, life denied/granted `577 + 135 = 712`, and `TOTAL EXPENDITURES $50,837,957`.
- Transform path: table label crosswalk in `TABLE_LABELS` plus `_verify_year`, then row assembly in `main()`.
- Gold: FY2001 has `total_releases=10164`, `guidelines_decisions_total=13630`, `life_cases_denied=577`, `life_cases_granted=135`, `life_decisions_total=712`, `total_expenditures=50837957.0`.
- Result: MATCH

### Check 2

- Bronze: `annual_report_fy2009.pdf` prose says Board members completed `75,245` individual votes, Board action released `12,938` offenders to parole supervision, and `66%` successfully completed parole.
- Transform path: year-scoped prose regexes for FY2009 `total_releases`, `clemency_votes`, and `parole_completion_rate`.
- Gold: FY2009 has `total_releases=12938`, `clemency_votes=75245`, `parole_completion_rate=0.66`, and table-only metrics are NULL.
- Result: MATCH

### Check 3

- Bronze: `annual_report_fy2013.pdf` clemency table has `TOTAL RELEASES 15,634`, `INITIAL DECISIONS UNDER GUIDELINES 14,915`, `TOTAL DISCHARGES 11,846`, `Pardon 1,349`, `Restoration of Rights 232`, and `TOTAL PAROLE POPULATION 27,285`; prose says completion rate was `74%`.
- Transform path: table crosswalk, prose completion-rate regex, and population component sum check.
- Gold: FY2013 has `total_releases=15634`, `guidelines_decisions_initial=14915`, `total_discharges=11846`, `pardons_granted=1349`, `rights_restorations=232`, `parole_population_end=27285`, `parole_completion_rate=0.74`.
- Result: MATCH

### Check 4

- Bronze: `annual_report_fy2016.pdf` has `Parole Certificates 7,233`, `Total Prison Releases by Parole 13,374`, `Total Guidelines Decisions 8,439`, `Life Sentenced Cases Denied Parole 1,504`, `Total Life Sentenced Case Decisions 1,667`, population `23,859` to `22,901`, completion `72%`, revocations `2,505`, and `Total: $45,782,940`.
- Transform path: era-3 table crosswalk, prose patterns, expenditure line extraction, DCS population chain check.
- Gold: FY2016 has `parole_certificates=7233`, `total_releases=13374`, `guidelines_decisions_total=8439`, `life_cases_denied=1504`, `life_decisions_total=1667`, `parole_population_start=23859`, `parole_population_end=22901`, `parole_completion_rate=0.72`, `parole_revocations=2505`, `total_expenditures=45782940.0`.
- Result: MATCH

### Check 5

- Bronze: `annual_report_fy2025.pdf` has `CLEMENCY VOTES 76,261`, `COMPLETED PAROLE 73%`, `Parole Certificates 4,037`, `Total Prison Releases by Parole 5,588`, `Total Guidelines Decisions 13,743`, `Life Sentence Cases Denied 2,154`, `Total Life Sentence Case Decisions 2,277`, population `15,105` to `14,568`, revocations `1,273`, discharges `4,729`, and `Total FY25 Expenditures $21,634,700.96`.
- Transform path: era-3 table/prose/band extraction and expenditure line extraction.
- Gold: FY2025 has `clemency_votes=76261`, `parole_completion_rate=0.73`, `parole_certificates=4037`, `total_releases=5588`, `guidelines_decisions_total=13743`, `life_cases_denied=2154`, `life_decisions_total=2277`, `parole_population_start=15105`, `parole_population_end=14568`, `parole_revocations=1273`, `total_discharges=4729`, `total_expenditures=21634700.96`.
- Result: MATCH

### Check 6

- Bronze: `annual_report_fy2025.pdf` also publishes cost metrics: `2025 Fiscal Year Cost Avoidance $380 MILLION`, prose that annual cost avoidance is calculated at more than `$380 million`, and cost per day of incarceration `$80.31` vs parole `$3.13`.
- Transform path: no `cost_avoidance`, `incarceration_cost_per_day`, or `parole_cost_per_day` entries exist in `METRIC_COLUMNS`, extraction patterns, `EXPECTED_COVERAGE`, or the contract column declaration.
- Gold: FY2025 has no cost-avoidance or cost-per-day columns; the only cost-like column is `total_expenditures`.
- Result: MISMATCH

## Needs Follow-up

- FY2002, FY2007, and FY2008 rely on image-table transcriptions in `TRANSCRIBED_VALUES`; the current headless review verified their file disposition, gold values, and runtime sum/anchor checks, but did not re-OCR the image table values. No mismatch was found from the available artifacts.

## Required Fixes

### Fix 1: Preserve published cost-avoidance metrics

- **Severity**: HIGH
- **Issue**: The transform drops a source metric family that the bronze profile classifies as gold fact metrics: cost avoidance and parole-vs-prison cost per day. This is source-to-gold data loss, not a documented exclusion in `transform.py`.
- **Evidence**: `data/bronze/criminal_justice/pardons_paroles/parole_decisions/bronze-data-structure.md:103` says cost avoidance / cost-per-day appears across eras and to "Keep the raw published figure + its stated basis"; line 129 classifies it as `fact_metric`. Actual bronze confirms it: FY2013 says annual cost avoidance was `$408,884,195`, and FY2025 says `2025 Fiscal Year Cost Avoidance $380 MILLION`, incarceration cost per day `$80.31`, and parole cost per day `$3.13`. Gold `data/gold/criminal_justice/parole_decisions/year=2025/states.parquet` has no `cost_avoidance`, `incarceration_cost_per_day`, or `parole_cost_per_day` columns; transform `METRIC_COLUMNS` and the contract columns only include `total_expenditures` as a cost-like metric.
- **Location**: `src/etl/criminal_justice/pardons_paroles/parole_decisions/transform.py:146`
- **Suggested fix**: Add the published cost metrics to the schema (`METRIC_COLUMNS`, `STANDARD_COLUMNS`, `TARGET_TYPES`, `EXPECTED_COVERAGE`, and `write_data_dictionary` columns) and extract them from the PDFs without recomputing: at minimum `cost_avoidance` (`unit: currency`), and where the reports publish them, `incarceration_cost_per_day` and `parole_cost_per_day` (`unit: currency`). Add year-scoped extraction/anchor checks and contract `null_meaning` descriptions that document the era-specific basis.

## Notes

- I did not read any prior topic review report before deriving this report's findings.
- The accidental OCR probe artifact `-.png` was removed immediately; no extra review artifacts remain outside `data-review-codex.md`.
