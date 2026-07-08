# Data Review: pathway_graduation_rate

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze checksums, manifest row flow, contract schema, validation output, and direct row traces all support the current transform; no must-fix accuracy issues found.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - transform mtime `2026-06-12T20:02:32.776015+00:00`, manifest `2026-06-12T20:02:54.349866+00:00`, validation `2026-06-12T20:02:54.391550+00:00`; `_validation.json` passed.

## Files Reviewed

- Transform: `src/etl/education/georgiainsights/pathway_graduation_rate/transform.py`
- Contract: `contracts/education/pathway_graduation_rate.odcs.yaml`
- Bronze files: 4 Excel files, `2021 Pathways Graduation Rates.xlsx` through `2024 Pathways Graduation Rates.xlsx`; all SHA-256 checksums match `bronze-data-structure.md`.
- Gold files: 12 Parquet files, `year=2021..2024/{states,districts,schools}.parquet`, plus manifest and validation report.
- Manifest: `data/gold/education/pathway_graduation_rate/_transform_manifest.json`
- Validation report: `data/gold/education/pathway_graduation_rate/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`, and relevant utility modules.

## Contract Verification

- Schema/parquet column match: PASS - validator reports all 12 Parquet files match the contract; actual columns are `year`, `district_code`, `school_code`, and the four pathway-rate metrics in contract order.
- Column roles and grain: PASS - contract custom properties mark `year`, `fk_district`, `fk_school`, and four metric columns; grain is `year, district_code, school_code`, matching the 1-row-per-geography source.
- Metric units and derived quality checks: PASS - all four pathway metrics are `unit: proportion` with `[0, 1]` SQL guards; rates are correctly divided from 0-100 bronze values to 0-1 gold values.
- Categorical enums: N/A - no demographic or topic categorical columns.
- Detail levels and layout metadata: PASS - contract lists `schools`, `districts`, `states`, default `schools`, partition column `year`, and path template `education/pathway_graduation_rate/year={year}/{detail}.parquet`.
- Foreign-key descriptors: PASS - contract declares `district_code -> districts` and composite `school_code -> schools`; validation reports all 197 district keys and all 514 school keys resolve.
- Schema hash/version consistency: PASS - contract version is `1.0.0`, schema hash is `e31c596116d259a2604d2e2b2753906ccb45e31dcf57095c7d32dfae0cc552bd`, and top-level custom properties list available years `2021-2024` with no gaps.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp is after manifest generation and `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - validation summary is 21 pass, 0 fail, 0 warning.
- Validator warnings explained: N/A - no warnings.
- §15b quality-check coverage (cross-column invariants authored): PASS - contract includes `one_state_row_per_year` and `no_all_zero_pathway_rows`; the four rates are independent overlapping rates, so no partition-sums-to-one invariant applies.

## Manifest Verification

- Files processed coverage: PASS - manifest processes exactly the 4 current bronze Excel files, one per year from 2021 through 2024, and checksum freshness check passes.
- Categorical and recode coverage: N/A - no categorical mappings, consistent with no demographic or categorical columns.
- Row-count reconciliation: PASS - manifest records 2,773 bronze rows and 2,773 gold rows, with per-year 1.0 expansion: 688, 690, 694, and 701 rows.
- Metric stats sanity: PASS - all four metric max values are 1.0, minimums are within `[0, 1]`, and null counts match suppression plus the documented 2021 all-zero mask.

## Row and Join Accounting

- Bronze file/year disposition: PASS - all four bronze files are processed; in-file `COHORT YEAR` is cross-checked against filename year in `transform_file()`.
- Filter accounting: N/A - no rows are filtered; the 47 all-zero 2021 rows are row-preserved with metric values masked to NULL.
- Join accounting: N/A - transform performs no joins; FK integrity is validated after export against dimensions.
- Deduplication accounting: PASS - direct bronze duplicate checks found 0 duplicate `(COHORT YEAR, SYSTEM ID, SCHOOL ID)` groups in every file; defensive dedup removed no rows because manifest bronze and gold counts match.
- Aggregation/unpivot accounting: N/A - no aggregation or unpivot; the four pathway areas remain independent metric columns.

## Reconciliation Checks

- Artifact freshness: PASS - transform, manifest, validation, bronze checksums, and gold row counts are mutually current.
- Contract freshness: PASS - contract reflects the current transform/gold layout and has no `_metadata.json` dependency.
- Year coverage: PASS - current bronze and gold both cover only 2021, 2022, 2023, and 2024.
- Row preservation: PASS - 1:1 bronze-to-gold row flow by year and detail level: 2021 `(1 state, 195 district, 492 school)`, 2022 `(1, 194, 495)`, 2023 `(1, 195, 498)`, 2024 `(1, 197, 503)`.
- Column coverage: PASS - fact keys and all four metric fields are present; `SYSTEM NAME` and `SCHOOL NAME` are correctly excluded as dimension attributes.
- Recode accuracy: PASS - `ALL` sentinels become NULL before padding, school IDs are `zfill(4)`, standard district IDs are `zfill(3)`, and 7-digit charter district IDs are preserved.
- Asian-family demographic recodes (§5b): N/A - no demographic column or race metrics.
- Demographic mutual exclusivity (§5a - no rollup row alongside split source rows in the same category): N/A - no demographic column.
- Demographic collision aggregation before dedup (§5): N/A - no demographic normalization.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS - actual parquet order is `year`, `district_code`, `school_code`, then the four metric columns.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS - no forbidden fact-table columns are present in gold parquet.
- Canonical column vocabulary (§16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - pathway rate columns use `_rate` without redundant `_pct`; no other §16 vocabulary applies.
- Shared categorical utilities applied (§10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no grade or subject columns.
- Tidy long format (§9 - no demographics/years/components as column names): PASS - no year, demographic, or test-component values are encoded as columns; the four source metric fields are distinct measures, not a categorical axis requiring unpivot.
- FK keys present in dimension tables (§13 - `district_code`, `school_code`, `demographic`): PASS - validator confirms district and composite school keys resolve; no demographic FK applies.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - row grain and FK joins derive from contract custom properties; no filterable categorical columns exist.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS - suppression markers become NULL, percentages are on 0-1 scale, aggregate geography is nulled, and gold is year-partitioned with no empty files.

## Spot Checks

### Check 1

- Bronze: `2024 Pathways Graduation Rates.xlsx`, state row `SYSTEM ID=ALL`, `SCHOOL ID=ALL`, metrics `99.50`, `99.26`, `97.89`, `98.24`.
- Transform path: `_transform_one_year()` lines 220-280 nulls aggregate IDs, derives `detail_level`, casts year, and divides the four metrics by 100.
- Gold: `year=2024/states.parquet` row has `district_code=NULL`, `school_code=NULL`, rates `0.995`, `0.9926`, `0.9789`, `0.9824`.
- Result: MATCH

### Check 2

- Bronze: `2024 Pathways Graduation Rates.xlsx`, Carroll County KidsPeace `SYSTEM ID=622`, `SCHOOL ID=0112`, metrics `NA`, `NA`, `NA`, `NA` after the shared reader converts suppression markers to NULL.
- Transform path: `_transform_one_year()` lines 246-280 preserves IDs (`622`, `0112`) and casts NULL metrics through to NULL.
- Gold: `year=2024/schools.parquet` row `district_code=622`, `school_code=0112` has all four pathway metrics NULL.
- Result: MATCH

### Check 3

- Bronze: `2021 Pathways Graduation Rates.xlsx`, Carroll County KidsPeace `SYSTEM ID=622`, `SCHOOL ID=112`, metrics `0`, `0`, `0`, `0`; direct bronze scan found 47 rows with all four 2021 metrics exactly zero.
- Transform path: `_null_2021_zero_suppression()` lines 344-383 masks all four metrics to NULL for 2021 rows where all four rates are exactly 0 and records 47 masked values per metric in the manifest.
- Gold: `year=2021/schools.parquet` row `district_code=622`, `school_code=0112` has all four pathway metrics NULL; gold has 47 rows with all four metrics NULL and 0 rows with all four metrics still zero.
- Result: MATCH

### Check 4

- Bronze: `2021 Pathways Graduation Rates.xlsx`, Atkinson County district row `SYSTEM ID=602`, `SCHOOL ID=ALL`, metrics `100`, `0`, `100`, `97.65`.
- Transform path: `_transform_one_year()` lines 220-280 nulls `SCHOOL ID=ALL`, pads `district_code`, and scales metrics; `_null_2021_zero_suppression()` lines 361-382 does not mask partial-zero rows.
- Gold: `year=2021/districts.parquet` row `district_code=602`, `school_code=NULL` has rates `1.0`, `0.0`, `1.0`, `0.9765`.
- Result: MATCH

## Notes

- No prior `data-review-claude.md` or existing `data-review-codex.md` was read before writing this report.
- The bronze structure report contains a stale projected `_metadata.json` path in its old layout example, but its corrections section explicitly supersedes that; current transform/contract artifacts use the ODCS contract path and are fresh.
- The contract limitation notes that a 2025 upstream source file exists but is not yet ingested. This review is scoped to the current local bronze inventory and does not treat missing future bronze acquisition as a transform correctness defect.
