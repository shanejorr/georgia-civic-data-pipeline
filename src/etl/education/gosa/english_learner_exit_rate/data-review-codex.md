# Data Review: english_learners_el_exit_rate

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze rows reconcile one-to-one with gold after documented scaling, geography nulling, and FY2024 unverifiable-rate masking; no required transform fixes were found.

## Summary

- Review date: 2026-06-11
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - `scripts/check_bronze_freshness.py education gosa english_learners_el_exit_rate` passed for all 12 bronze CSV checksums with no unanalyzed files; transform mtime `2026-06-11T22:24:00.893377+00:00` is before manifest `generated_at` `2026-06-11T22:24:07.776412+00:00`; validation timestamp `2026-06-11T22:24:07.819685+00:00` is after the manifest and reports `passed: true`.

## Files Reviewed

- Transform: `src/etl/education/gosa/english_learners_el_exit_rate/transform.py`
- Contract: `contracts/education/english_learners_el_exit_rate.odcs.yaml`
- Bronze files: 12 CSVs - `district_FY2019.csv` through `district_FY2024.csv` and `state_FY2019.csv` through `state_FY2024.csv`
- Gold files: 12 parquet files - `year=2019` through `year=2024`, each with `districts.parquet` and `states.parquet`
- Manifest: `data/gold/education/english_learners_el_exit_rate/_transform_manifest.json`
- Validation report: `data/gold/education/english_learners_el_exit_rate/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`, `src/utils/readers.py`, `src/utils/transformers.py`

## Contract Verification

- Schema/parquet column match: PASS - contract properties and every parquet file use `year`, `district_code`, `school_code`, `el_exit_count`, `el_student_count`, `el_exit_rate` in that order.
- Column roles and grain: PASS - roles are `year`, `fk_district`, `fk_school`, and metrics; contract grain is `year`, `district_code`, `school_code`, matching the district/state natural key with nullable higher-level geography.
- Metric units and derived quality checks: PASS - `el_exit_count` and `el_student_count` are `unit: count`; `el_exit_rate` is `unit: proportion`; contract quality includes non-negative count checks and `el_exit_rate_within_unit_interval`.
- Categorical enums: N/A - the gold output has no categorical or demographic column, and `categorical_mappings` is empty by design.
- Detail levels and layout metadata: PASS - contract declares `detail_levels: [districts, states]`, `default_detail: districts`, partition column `year`, and path template `education/english_learners_el_exit_rate/year={year}/{detail}.parquet`.
- Foreign-key descriptors: PASS - `district_code` targets `districts.district_code`; `school_code` targets the composite schools key `district_code`, `school_code`. Actual gold has 241 populated district keys and all resolve; no school keys are populated.
- Schema hash/version consistency: PASS - contract is `version: 1.0.0`, `status: active`, `year_range: 2019-2024`, `schema_hash: 17460628cb5370c6bec17717e50e6af3dd0a8413ee6f9a5ccaf25b89cd2af10b`, consistent with the current gold layout and manifest years.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp is after manifest generation and reports `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - validation summary is 20 pass, 0 fail, 0 warning; `contract_parquet_schema`, `grain_uniqueness`, `contract_quality_sql`, `foreign_keys`, `canonical_vocabulary`, and geography nulling all passed.
- Validator warnings explained: N/A - validation reported no warnings.
- section 15b quality-check coverage (cross-column invariants authored): PASS - contract quality covers the structural `school_code` null invariant, exactly one state row per year, state metrics never null, exit count within student count, suppression hierarchy, both rate/count co-null directions, and rate reconciliation to `el_exit_count / el_student_count` within 0.0006.

## Manifest Verification

- Files processed coverage: PASS - manifest lists all 12 current bronze CSVs with the expected eras and row counts.
- Categorical and recode coverage: PASS - no categorical recodes apply; `categorical_mappings` is `{}` and there are no unmapped categorical values.
- Row-count reconciliation: PASS - manifest reports `total_bronze: 1336`, `total_gold: 1336`, `total_filtered: 0`; each year has expansion factor 1.0.
- Metric stats sanity: PASS - counts are non-negative; `el_exit_rate` is within [0, 1] after scaling and masking; final gold ranges are `el_exit_count` 10-15519, `el_student_count` 10-155372, and `el_exit_rate` 0.015-0.467.

## Row and Join Accounting

- Bronze file/year disposition: PASS - every current bronze CSV is processed; the legacy report-card duplicate source is not in this bronze directory and is documented as dropped during bronze consolidation after zero row-level value mismatches.
- Filter accounting: N/A - no rows are filtered. The only value-level mask is 130 FY2024 `el_exit_rate` cells with suppressed underlying counts, recorded in `masked_values`.
- Join accounting: N/A - the transform performs no joins. Validator FK checks and a direct dimension anti-join found 0 missing district keys; `school_code` is always NULL.
- Deduplication accounting: PASS - each district bronze file has unique `SYSTEM_ID` values; actual gold has 0 duplicate groups on `year`, `district_code`, `school_code`; no dedup row loss appears in the 1,336 -> 1,336 row ledger.
- Aggregation/unpivot accounting: N/A - no aggregation or unpivot occurs. Each bronze district or state row maps to exactly one gold row.

## Reconciliation Checks

- Artifact freshness: PASS - bronze checksums match the structure report, manifest and validation are current, and validation passed.
- Contract freshness: PASS - contract is emitted from the current transform/gold contract path with no `_metadata.json` dependency; contract schema matches parquet.
- Year coverage: PASS - bronze, manifest, contract, and gold all cover 2019-2024 with no gaps.
- Row preservation: PASS - independent null-safe bronze-to-gold reconstruction produced 1,336 expected rows and 1,336 gold rows, with 0 missing rows, 0 extra rows, and 0 metric mismatches after documented rate scaling and FY2024 masking.
- Column coverage: PASS - `FISCAL_YEAR`, district `SYSTEM_ID`, all metric columns, and synthesized `school_code` are accounted for; `#RPT_NAME`, `SYSTEM_NAME`, and state 2023 constants are correctly excluded as constants or dimension attributes.
- Recode accuracy: N/A - no categorical recodes apply.
- Asian-family demographic recodes (section 5b): N/A - no demographic or race fields exist.
- Demographic mutual exclusivity (section 5a - no rollup row alongside split source rows in the same category): N/A - no demographic column exists.
- Demographic collision aggregation before dedup (section 5): N/A - no demographic normalization applies.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - actual parquet order is `year`, `district_code`, `school_code`, then the three metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, section 11/12): PASS - actual gold contains none of `topic`, `detail_level`, `district_name`, `school_name`, `district_census_id`, or `school_year`.
- Canonical column vocabulary (section 16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - topic-specific metric names are clear and no forbidden vocabulary variants are present; validator `canonical_vocabulary` passed.
- Shared categorical utilities applied (section 10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no `grade_level`, `subject`, or `demographic` output column exists.
- Tidy long format (section 9 - no demographics/years/components as column names): PASS - gold has one row per year/geography observation and no wide demographic/year columns.
- FK keys present in dimension tables (section 13 - `district_code`, `school_code`, `demographic`): PASS - 241 populated district keys all resolve in `data/gold/education/_dimensions/districts.parquet`; there are 0 populated `school_code` rows; no demographic key applies.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - row grain is contract-derived, there are no filterable categoricals, and FK descriptors match the dimension contracts.
- Standards compliance (catch-all for section 1-16 items not enumerated above): PASS - ID columns are strings, rates are 0-1 proportions, suppressed values are NULL, geography is nulled by detail level, and no fact-table names or crosswalk IDs are retained.

## Spot Checks

### Check 1

- Bronze: `data/bronze/education/gosa/english_learners_el_exit_rate/district_FY2019.csv`, `SYSTEM_ID=601`, Appling County: `EL_EXIT_COUNT=37`, `EL_STUDENT_COUNT=274`, `EL_EXIT_RATE=13.5`.
- Transform path: `_to_gold()` lines 236-303 casts counts, divides rate by 100, emits `district_code=601`, and sets `school_code=NULL`.
- Gold: `data/gold/education/english_learners_el_exit_rate/year=2019/districts.parquet`, `district_code=601`: `el_exit_count=37`, `el_student_count=274`, `el_exit_rate=0.135`, `school_code=NULL`.
- Result: MATCH

### Check 2

- Bronze: `data/bronze/education/gosa/english_learners_el_exit_rate/state_FY2023.csv`: constants `SYSTEM_ID=State of Georgia`, `SYSTEM_NAME=State of Georgia`, `EL_EXIT_COUNT=14215`, `EL_STUDENT_COUNT=143070`, `EL_EXIT_RATE=9.94`.
- Transform path: `_prepare_for_era()` lines 306-327 drops the state constants; `_to_gold()` lines 236-303 emits state geography as NULL and scales the rate.
- Gold: `data/gold/education/english_learners_el_exit_rate/year=2023/states.parquet`: `district_code=NULL`, `school_code=NULL`, `el_exit_count=14215`, `el_student_count=143070`, `el_exit_rate=0.0994`.
- Result: MATCH

### Check 3

- Bronze: `data/bronze/education/gosa/english_learners_el_exit_rate/district_FY2024.csv`, `SYSTEM_ID=604`, Baker County: `EL_EXIT_COUNT=TFS`, `EL_STUDENT_COUNT=19`, `EL_EXIT_RATE=5.3`.
- Transform path: `_to_gold()` lines 285-303 turns `TFS` into NULL and scales rate to 0.053; `_null_unverifiable_rates()` lines 413-457 NULLs `el_exit_rate` because one underlying count is suppressed.
- Gold: `data/gold/education/english_learners_el_exit_rate/year=2024/districts.parquet`, `district_code=604`: `el_exit_count=NULL`, `el_student_count=19`, `el_exit_rate=NULL`.
- Result: MATCH

### Check 4

- Bronze: `data/bronze/education/gosa/english_learners_el_exit_rate/district_FY2024.csv`, `SYSTEM_ID=7820612`, Ivy Preparatory Academy: `EL_EXIT_COUNT=TFS`, `EL_STUDENT_COUNT=TFS`, `EL_EXIT_RATE=100`.
- Transform path: `_null_unverifiable_rates()` lines 413-457 masks the published numeric rate because both counts are suppressed; manifest records the 130 FY2024 masked rate cells.
- Gold: `data/gold/education/english_learners_el_exit_rate/year=2024/districts.parquet`, `district_code=7820612`: `el_exit_count=NULL`, `el_student_count=NULL`, `el_exit_rate=NULL`.
- Result: MATCH

### Check 5

- Bronze: `data/bronze/education/gosa/english_learners_el_exit_rate/district_FY2023.csv`, `SYSTEM_ID=890`: `SYSTEM_NAME=NULL`, `EL_EXIT_COUNT=TFS`, `EL_STUDENT_COUNT=TFS`, `EL_EXIT_RATE=TFS`.
- Transform path: `_to_gold()` lines 236-303 drops `SYSTEM_NAME` as a dimension attribute, preserves `district_code=890`, and casts suppressed metrics to NULL.
- Gold: `data/gold/education/english_learners_el_exit_rate/year=2023/districts.parquet`, `district_code=890`: `school_code=NULL`, all three metrics NULL.
- Result: MATCH

## Notes

- I did not read any prior `data-review-claude.md` or existing `data-review-codex.md` before completing this review.
- The FY2024 rate mask is value-level only, not row loss: the bronze has 130 district rows where a numeric `EL_EXIT_RATE` appears with at least one `TFS` count, and gold retains all 130 rows while NULLing only `el_exit_rate`. The mask is documented in the transform, contract, manifest, and enforced by contract quality checks.
- Full rate reconciliation on 576 rows with all three metrics present found maximum absolute difference `0.0005000000000000004`, within the contract tolerance of 0.0006.
- `git status` shows this topic's transform directory, contract, and gold directory are currently untracked local artifacts, and the bronze structure report is modified. That does not block this audit because freshness was verified against the current filesystem artifacts.
