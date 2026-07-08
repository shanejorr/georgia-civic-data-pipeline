# Data Review: attendance_dashboard

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze, transform, contract, validator, manifest, and gold output reconcile with no must-fix accuracy defects.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH — bronze checksum gate passed; manifest generated at `2026-06-12T12:18:02.163317+00:00`; validation timestamp `2026-06-12T12:18:02.246647+00:00`, passed.

## Files Reviewed

- Transform: `src/etl/education/georgiainsights/attendance_dashboard/transform.py`
- Contract: `contracts/education/attendance_dashboard.odcs.yaml`
- Bronze files: 8 xlsx workbooks, `Attendance Dashboard Data - 2018.xlsx` through `Attendance Dashboard Data - 2025.xlsx`
- Gold files: 24 parquet files, `year=2018` through `year=2025`, each with `schools.parquet`, `districts.parquet`, and `states.parquet`
- Manifest: `data/gold/education/attendance_dashboard/_transform_manifest.json`
- Validation report: `data/gold/education/attendance_dashboard/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`, and `data/bronze/education/georgiainsights/attendance_dashboard/bronze-data-structure.md`.

## Contract Verification

- Schema/parquet column match: PASS — contract properties exactly match gold columns and order: `year`, `district_code`, `school_code`, `demographic`, `student_count`, `chronically_absent_rate`, `average_daily_absenteeism_rate`, `average_daily_attendance_rate`.
- Column roles and grain: PASS — contract grain is one row per `year`, `district_code`, `school_code`, `demographic`; geography keys are nullable for aggregate levels.
- Metric units and derived quality checks: PASS — `student_count` is `count`; the three rate metrics are bounded `proportion`; contract includes non-negative/range checks plus topic-specific complement and suppression invariants.
- Categorical enums: PASS — contract demographic enum contains 28 values and matches manifest `gold_values_produced` and actual gold distinct values.
- Detail levels and layout metadata: PASS — `schools`, `districts`, and `states` are present for all 2018-2025 partitions; `path_template` and `year_range` match disk layout.
- Foreign-key descriptors: PASS — contract declares `district_code`, composite `school_code` via `(district_code, school_code)`, and `demographic`; validator reports all keys resolve.
- Schema hash/version consistency: PASS — version is `1.0.0`; schema hash is present; contract metadata and current gold schema are coherent.

## Validator Verification

- `_validation.json` fresh + passing: PASS — validation timestamp is newer than manifest and `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS — 21 pass, 0 fail, 0 warning; all 9 contract quality SQL checks passed.
- Validator warnings explained: N/A — no warnings were emitted.
- §15b quality-check coverage (cross-column invariants authored): PASS — authored checks cover attendance/absenteeism complement, all-or-nothing suppression across the three rates, and non-null `student_count`.

## Manifest Verification

- Files processed coverage: PASS — all 8 checksum-verified bronze xlsx files appear in `files_processed`; no unanalyzed bronze files.
- Categorical and recode coverage: PASS — demographic mapping records all 28 observed subgroup labels; `unmapped_count` is 0.
- Row-count reconciliation: PASS — total bronze rows = 386,836 and total gold rows = 386,836; each year has expansion factor 1.0 and zero filtered rows.
- Metric stats sanity: PASS — rates are on 0-1 scale; `student_count` is non-null and non-negative; metric null counts align with suppression.

## Row and Join Accounting

- Bronze file/year disposition: PASS — all source workbooks for 2018-2025 are processed; `Read Me` is correctly skipped as metadata, while `All Students`, `Grade Level`, and `Subgroups` are concatenated.
- Filter accounting: N/A — no source data rows are filtered; manifest reports `total_filtered: 0`.
- Join accounting: N/A — transform performs no data joins; downstream FK joins are validated against dimensions.
- Deduplication accounting: PASS — no duplicate gold grain rows; direct row count remains one-to-one after defensive dedup.
- Aggregation/unpivot accounting: PASS — no aggregation or unpivot is performed; the transform preserves the source's already-long subgroup rows.

## Reconciliation Checks

- Artifact freshness: PASS — `scripts/check_bronze_freshness.py education georgiainsights attendance_dashboard` passed.
- Contract freshness: PASS — contract was emitted from the current transform/gold; no `_metadata.json` dependency.
- Year coverage: PASS — expected 2018-2025 years are present; no unexpected years or gaps.
- Row preservation: PASS — an independent normalized full-row comparison found `bronze_not_in_gold = 0` and `gold_not_in_bronze = 0`.
- Column coverage: PASS — all fact keys and fact metrics classified in the bronze structure report are represented; names and `Group` are validly excluded.
- Recode accuracy: PASS — `Subgroup` values map semantically to canonical demographics, including `English Learner` -> `english_learners` and disability singular labels -> plural canonical keys.
- Asian-family demographic recodes (§5b): PASS — bronze explicitly publishes `Asian/Pacific Islander`; gold emits `asian_pacific_islander` and never emits split `asian` or `pacific_islander`.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): PASS — no natural-key group has combined Asian/Pacific Islander alongside split Asian/Pacific Islander values.
- Demographic collision aggregation before dedup (§5): N/A — observed labels map 1:1 to canonical keys; no demographic collision exists.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS — actual parquet order matches the contract and standard order.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS — gold fact files contain no forbidden columns.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS — `student_count` and named `average_daily_*` rates follow documented vocabulary.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A — no `grade_level` or `subject` column; grade values intentionally live in `demographic`.
- Tidy long format (§9 — no demographics/years/components as column names): PASS — subgroup values are rows in `demographic`, not columns.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS — validation reports 243 district keys, 2,409 school keys, and 28 demographic keys all resolve.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS — grain, demographic enum, and FK descriptors are coherent with API/validator expectations.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS — ID padding, geography nulling, suppression-to-null, percentage scale, and star-schema exclusions are correct.

## Spot Checks

### Check 1

- Bronze: `Attendance Dashboard Data - 2025.xlsx`, `All Students`, state row: `System ID=All`, `School ID=All`, `Subgroup=All`, `Total Students=1749935`, rates `0.195`, `0.065`, `0.935`.
- Transform path: `_transform_year` lines 331-364 maps `All/All` to state, nulls geography keys, casts count/rates; lines 371-386 normalizes `All` to `all`.
- Gold: `year=2025/states.parquet` row has `district_code=NULL`, `school_code=NULL`, `demographic=all`, `student_count=1749935`, rates `0.195`, `0.065`, `0.935`.
- Result: MATCH

### Check 2

- Bronze: `Attendance Dashboard Data - 2025.xlsx`, `All Students`, Druid Hills High School: `System ID=644`, `School ID=2055`, `Subgroup=All`, `Total Students=1568`, rates `0.393`, `0.108`, `0.892`.
- Transform path: `_transform_year` lines 331-364 treats concrete system/school IDs as school detail, applies string padding, and casts metrics.
- Gold: `year=2025/schools.parquet` row has `district_code=644`, `school_code=2055`, `demographic=all`, `student_count=1568`, rates `0.393`, `0.108`, `0.892`.
- Result: MATCH

### Check 3

- Bronze: `Attendance Dashboard Data - 2025.xlsx`, `Subgroups`, Beaverdale Elementary black row: `System ID=755`, `School ID=206`, `Subgroup=Black`, `Total Students=5`, all three rate cells `TFS`.
- Transform path: `_read_data_sheets` lines 256-268 reads suppression-capable sheets; `_transform_year` lines 362-364 casts `TFS` to null and lines 371-386 maps `Black` to `black`.
- Gold: `year=2025/schools.parquet` row has `district_code=755`, `school_code=0206`, `demographic=black`, `student_count=5`, all three rates NULL.
- Result: MATCH

### Check 4

- Bronze: `Attendance Dashboard Data - 2018.xlsx`, `Subgroups`, state race row: `Subgroup=Asian/Pacific Islander`, `Total Students=75507`, rates `0.051`, `0.031`, `0.969`.
- Transform path: demographic normalization at lines 371-386 uses the shared alias map; the contract declaration at lines 559-577 documents the combined bucket convention.
- Gold: `year=2018/states.parquet` row has `demographic=asian_pacific_islander`, `student_count=75507`, rates `0.051`, `0.031`, `0.969`; no split Asian/Pacific Islander rows are present.
- Result: MATCH

## Notes

- No must-fix findings were identified.
- The source is already long by subgroup sheet; no formula-level aggregation case exists for this transform. The row-level preservation check is stronger here than sampled aggregate recomputation because every exported row was independently matched back to a transformed bronze row.
