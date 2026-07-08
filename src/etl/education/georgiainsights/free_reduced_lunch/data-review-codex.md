# Data Review: free_reduced_lunch

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Current gold output is fresh, validator-passing, and reconciles 1:1 to all 28 bronze CSV data rows with no row loss, extra rows, rate mismatches, or recode defects found.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - transform mtime `2026-06-12T17:36:07.942622+00:00`; manifest generated `2026-06-12T17:36:16.016159+00:00`; validation timestamp `2026-06-12T17:36:16.069327+00:00`, passed true.

## Files Reviewed

- Transform: `src/etl/education/georgiainsights/free_reduced_lunch/transform.py`
- Contract: `contracts/education/free_reduced_lunch.odcs.yaml`
- Bronze files: 28 CSVs, `Free Reduced Lunch (FRL) Fiscal Year2013 District.csv` through `Free Reduced Lunch (FRL) Fiscal Year2026 School.csv`
- Gold files: 42 parquet files, three detail files (`districts.parquet`, `schools.parquet`, `states.parquet`) for each year 2013-2026
- Manifest: `data/gold/education/free_reduced_lunch/_transform_manifest.json`
- Validation report: `data/gold/education/free_reduced_lunch/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS - all parquet files use `year`, `district_code`, `school_code`, `reporting_status`, `free_reduced_lunch_rate` in contract order.
- Column roles and grain: PASS - roles are year, fk_district, fk_school, categorical, metric; validator confirmed one row per `year`, `district_code`, `school_code`, `reporting_status`.
- Metric units and derived quality checks: PASS - `free_reduced_lunch_rate` has `unit: proportion`; contract includes unit interval and publication-band checks plus status/rate co-null checks.
- Categorical enums: PASS - contract enum and manifest/gold values are `not_participating`, `reported`, `suppressed_privacy_band`.
- Detail levels and layout metadata: PASS - contract detail levels are `schools`, `districts`, `states`; gold layout has exactly those files for each year.
- Foreign-key descriptors: PASS - contract declares `district_code -> districts` and composite `school_code -> schools`; validator resolved 250 district keys and 2,568 school key pairs.
- Schema hash/version consistency: PASS - contract version is `1.0.0`; schema hash is `3a1e4394f33288dc91c72a06d9977bce94215412ce53a5277dab6094a4047f42`; year range and available years are 2013-2026.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp is after manifest generation and reports `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 21 checks passed, 0 failed, 0 warnings.
- Validator warnings explained: N/A - validation emitted no warnings.
- §15b quality-check coverage (cross-column invariants authored): PASS - contract includes status/rate co-null checks, reporting_status non-null, publication band, and one state row per year.

## Manifest Verification

- Files processed coverage: PASS - manifest lists all 28 current CSVs; current bronze inventory matches; `scripts/check_bronze_freshness.py education georgiainsights free_reduced_lunch` passed all checksums and found no unanalyzed files.
- Categorical and recode coverage: PASS - `reporting_status` maps `* -> suppressed_privacy_band`, `# -> not_participating`, `NA -> not_participating`; `unmapped_count` is 0.
- Row-count reconciliation: PASS - manifest reports 35,141 bronze rows and 35,141 gold rows, `filtered: 0`, expansion factor 1.0 for every year; actual parquet row count is 35,141.
- Metric stats sanity: PASS - non-null rates are on 0-1 scale with observed range 0.05-0.95; null rates correspond to suppression/non-participation markers.

## Row and Join Accounting

- Bronze file/year disposition: PASS - every CSV is processed; two files per year for 2013-2026.
- Filter accounting: PASS - zero rows filtered; footer lines are excluded before CSV parsing and are not source data rows.
- Join accounting: N/A - transform performs no data joins; FK resolution is validated after export against dimension tables.
- Deduplication accounting: PASS - collision guard runs on `year`, `district_code`, `school_code`, `detail_level`; duplicate natural keys in gold are 0, so dedup is a no-op.
- Aggregation/unpivot accounting: N/A - no aggregation or unpivoting; each footer-stripped bronze data row maps to exactly one gold row.

## Reconciliation Checks

- Artifact freshness: PASS - transform, manifest, validation, bronze checksums, and gold files are consistent.
- Contract freshness: PASS - contract is emitted from the current transform/gold path with no `_metadata.json` dependency.
- Year coverage: PASS - gold years are exactly 2013-2026.
- Row preservation: PASS - independent all-row comparison produced 35,141 expected rows vs 35,141 actual rows, 0 missing, 0 extra, 0 rate mismatches.
- Column coverage: PASS - filename year, `System ID`, `School ID - School Name`, and `KK-12 % FRL` have clear gold lineage; name columns are correctly excluded as dimensions.
- Recode accuracy: PASS - numeric FRL cells become `reported` with rate divided by 100; `*`, `#`, and `NA` become null rates with distinct reporting status semantics.
- Asian-family demographic recodes (§5b): N/A - source has no demographic or race axis.
- Demographic mutual exclusivity (§5a - no rollup row alongside split source rows in the same category): N/A - no demographic column.
- Demographic collision aggregation before dedup (§5): N/A - no demographic recoding.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS - parquet order is `year`, `district_code`, `school_code`, `reporting_status`, `free_reduced_lunch_rate`.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS - actual gold contains none of those columns.
- Canonical column vocabulary (§16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - `free_reduced_lunch_rate` follows the rate naming convention; no grade/subject/proficiency columns apply.
- Shared categorical utilities applied (§10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no grade or subject columns.
- Tidy long format (§9 - no demographics/years/components as column names): PASS - no wide categorical columns.
- FK keys present in dimension tables (§13 - `district_code`, `school_code`, `demographic`): PASS - validator confirmed all district keys and composite school keys resolve.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - row grain, `reporting_status` enum, and FK descriptors are contract-backed and validator-passing.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS - IDs are strings, aggregate geography nulling is correct, suppression markers do not survive as string fact values, and rate scaling is correct.

## Spot Checks

### Check 1

- Bronze: `Free Reduced Lunch (FRL) Fiscal Year2024 District.csv`, Camden County: `System ID=620`, `KK-12 % FRL=53.31`
- Transform path: `_transform_district_frame` and `_with_rate_and_status`, lines 326-383 and 270-318
- Gold: `year=2024/districts.parquet` row `district_code=620`, `school_code=NULL`, `reporting_status=reported`, `free_reduced_lunch_rate=0.5331`
- Result: MATCH

### Check 2

- Bronze: `Free Reduced Lunch (FRL) Fiscal Year2024 School.csv`, Muscogee County / Wynnton Elementary School: `System ID=706`, `School ID - School Name=' 4070 - Wynnton Elementary School'`, `KK-12 % FRL=*`
- Transform path: `_transform_school_frame` and `_with_rate_and_status`, lines 386-438 and 270-318
- Gold: `year=2024/schools.parquet` row `district_code=706`, `school_code=4070`, `reporting_status=suppressed_privacy_band`, `free_reduced_lunch_rate=NULL`
- Result: MATCH

### Check 3

- Bronze: `Free Reduced Lunch (FRL) Fiscal Year2016 District.csv`, state specialty school row `System ID=7820613`, `KK-12 % FRL=NA`
- Transform path: `FRL_STATUS_MAP` and `_with_rate_and_status`, lines 148-152 and 270-318
- Gold: `year=2016/districts.parquet` row `district_code=7820613`, `reporting_status=not_participating`, `free_reduced_lunch_rate=NULL`
- Result: MATCH

### Check 4

- Bronze: `Free Reduced Lunch (FRL) Fiscal Year2026 District.csv`, statewide row `System ID` blank, `System Name=State-Wide Total`, `KK-12 % FRL=68.6`
- Transform path: `_transform_district_frame`, lines 338-383, then `null_aggregate_geography`, lines 530-534
- Gold: `year=2026/states.parquet` row `district_code=NULL`, `school_code=NULL`, `reporting_status=reported`, `free_reduced_lunch_rate=0.686`
- Result: MATCH

## Notes

- No collapsed-row formula trace applies because the transform does not aggregate, roll up, or unpivot; state rows are source rows from District CSVs.
- No prior `data-review-claude.md` or `data-review-codex.md` was used as evidence for this review.
