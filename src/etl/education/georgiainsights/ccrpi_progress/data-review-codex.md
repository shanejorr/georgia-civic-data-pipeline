# Data Review: ccrpi_progress

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Current gold output faithfully preserves the eight Georgia Insights CCRPI Progress bronze workbooks; no required transform fixes were found.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH — bronze freshness gate passed for all 8 checksums; transform mtime 2026-06-12T12:53:15Z precedes manifest generation 2026-06-12T12:54:05Z; validation timestamp 2026-06-12T12:54:05Z is newer than the manifest and passed.

## Files Reviewed

- Transform: `src/etl/education/georgiainsights/ccrpi_progress/transform.py`
- Contract: `contracts/education/ccrpi_progress.odcs.yaml`
- Bronze files: 8 XLSX files, 2018-2025, under `data/bronze/education/georgiainsights/ccrpi_progress/`
- Gold files: 24 parquet files, `year=2018` through `year=2025`, with `schools.parquet`, `districts.parquet`, and `states.parquet` in every year
- Manifest: `data/gold/education/ccrpi_progress/_transform_manifest.json`
- Validation report: `data/gold/education/ccrpi_progress/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS — contract properties exactly match parquet order: `year`, `district_code`, `school_code`, `demographic`, `grade_cluster`, `indicator`, `ccrpi_flag`, `indicator_score`, `target`, and the four `pct_*` band columns.
- Column roles and grain: PASS — contract grain is `year`, `district_code`, `school_code`, `demographic`, `grade_cluster`, `indicator`; `ccrpi_flag` is correctly excluded because it is a nullable target outcome attribute.
- Metric units and derived quality checks: PASS — `indicator_score` and `target` are `score` with [0, 100] guards; the four band columns are `proportion` with [0, 1] guards.
- Categorical enums: PASS — contract enums match manifest and gold values for demographic, grade_cluster, indicator, and ccrpi_flag.
- Detail levels and layout metadata: PASS — contract lists `schools`, `districts`, `states`; gold has all three files in all eight year partitions.
- Foreign-key descriptors: PASS — validation resolved all 242 district keys, 2,411 composite school keys, and 10 demographic keys.
- Schema hash/version consistency: PASS — contract version is `1.0.0`; schema_hash is `97f8971a4768c786f30a0f203f97d4c5a4677bce2a4a71dc5d3f4b1939402662`; year_range is `2018-2025`.

## Validator Verification

- `_validation.json` fresh + passing: PASS — `passed: true`, 21 pass / 0 fail / 0 warning, timestamp 2026-06-12T12:54:05.252352+00:00.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS — `contract_parquet_schema`, `grain_uniqueness`, `contract_quality_sql`, `foreign_keys`, and `canonical_vocabulary` all passed.
- Validator warnings explained: N/A — no validator warnings.
- §15b quality-check coverage (cross-column invariants authored): PASS — contract includes band partition, band all-or-nothing suppression, Era B-only band columns, target/flag scope, target/flag absence in 2020-2022, and ELP-only-year demographic constraints.

## Manifest Verification

- Files processed coverage: PASS — all 8 current bronze workbooks appear in `files_processed` with the expected eras and row counts; checksum audit reported all 8 files unchanged and no unanalyzed files.
- Categorical and recode coverage: PASS — all recorded mappings have `unmapped_count: 0`; observed bronze labels cover grade cluster E/M/H, indicator label drift, ccrpi flags G/R/Y, and 14 demographic spelling variants.
- Row-count reconciliation: PASS — manifest totals are 365,558 bronze rows and 365,558 gold rows; every year has expansion factor 1.0 and zero filtered rows.
- Metric stats sanity: PASS — `indicator_score` range is 0.0-100.0, `target` range is 5.74-90.0, and band proportions are within 0.0-1.0 with non-null values only in 2021-2022.

## Row and Join Accounting

- Bronze file/year disposition: PASS — 2018, 2019, 2020, 2023, 2024, and 2025 route to Era A; 2021 and 2022 route to Era B; every bronze row has a one-to-one gold row.
- Filter accounting: N/A — no transform filters remove rows; manifest filtered counts are zero in all years.
- Join accounting: PASS — the transform performs no data-changing joins; post-export FK joins are contract-driven and validator-verified against dimensions.
- Deduplication accounting: PASS — an independent bronze natural-key audit found 0 duplicate key groups in each of 2018-2025 before dedup; gold grain uniqueness also passed.
- Aggregation/unpivot accounting: N/A — the transform does not derive aggregate rows or unpivot; state/district/school rows are source-published and preserved by detail level.

## Reconciliation Checks

- Artifact freshness: PASS — transform, manifest, validation, contract, and gold are current enough for review.
- Contract freshness: PASS — contract matches current parquet and is emitted by the transform; no `_metadata.json` dependency.
- Year coverage: PASS — expected years 2018-2025 are present, with no gaps or unexpected partitions.
- Row preservation: PASS — actual gold row counts by detail level exactly match the bronze name-derived detail counts, e.g. 2024 has 53,382 school rows, 14,742 district rows, and 63 state rows in both bronze and gold.
- Column coverage: PASS — every fact key, metric, and categorical from the bronze structure classification is represented or validly excluded as dimension-only (`System Name`, `School Name`, `Grade Configuration`) or redundant year metadata.
- Recode accuracy: PASS — indicator drift maps to three stable time-series keys; E/M/H maps to elementary/middle/high; G/Y/R maps to green/yellow/red; `NA` and `TFS` become null.
- Asian-family demographic recodes (§5b): PASS — bronze publishes explicit `Asian/Pacific Islander` / `Asian / Pacific Islander` combined labels and no split Asian or Pacific Islander rows; gold emits `asian_pacific_islander` only.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): PASS — no natural-key group contains `asian_pacific_islander` alongside `asian` or `pacific_islander`.
- Demographic collision aggregation before dedup (§5): N/A — observed demographic aliases map one-to-one into the 10 canonical keys; no collisions require aggregation.
- Fact-table column order (year → geo → demographic → categoricals → metrics, §1): PASS — parquet order is year, district_code, school_code, demographic, grade_cluster, indicator, ccrpi_flag, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS — exported parquet contains no topic, detail_level, name, school_year, or census/crosswalk columns.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS — CCRPI uses canonical `indicator_score`, `target`, and `ccrpi_flag`; band metrics use clear `pct_*` proportion names.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A — topic has no `grade_level` or `subject` column; demographic normalization uses the shared utility.
- Tidy long format (§9 — no demographics/years/components as column names): PASS — demographics, grade clusters, and indicators are row values; no year- or demographic-keyed wide columns remain.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS — validator confirms all populated FK values resolve, including composite school keys.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS — categorical filters and FK joins are derivable from the contract; `ccrpi_flag` is filterable but excluded from the natural grain.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS — ID padding, aggregate geography nulling, suppression-to-null, metric units, and contract quality SQL all conform.

## Spot Checks

### Check 1

- Bronze: `2024 CCRPI Progress Scores, Targets, and Flags by Subgroup.xlsx`, Wilcox County Elementary, `System ID=756`, `School ID=195`, `Grade Cluster=E`, `Reporting Label=Students With Disability`, `Indicator=Mathematics`, `Indicator Score=78.96`, `Target=NA`, `Flag=NA`.
- Transform path: `_transform_era_a` lines 489-539 maps IDs, demographic, grade cluster, indicator, score, target, and flag.
- Gold: `district_code=756`, `school_code=0195`, `demographic=students_with_disabilities`, `grade_cluster=elementary`, `indicator=mathematics_growth`, `indicator_score=78.96`, `target=NULL`, `ccrpi_flag=NULL`.
- Result: MATCH

### Check 2

- Bronze: `2022 Progress Towards English Language Proficiency 11.16.22.xlsx`, Hollis Hand Elementary, `System ID=741`, `School ID=194`, `Grade Cluster=E`, band values `16.67`, `10`, `20`, `53.33`, `Progress Towards ELP Rate=100.00+`.
- Transform path: `_transform_era_b` lines 542-612 hard-codes `progress_towards_elp`, maps `100.00+` to 100, and divides band percentages by 100.
- Gold: `district_code=741`, `school_code=0194`, `demographic=english_learners`, `indicator_score=100.0`, band proportions `0.1667`, `0.1`, `0.2`, `0.5333`.
- Result: MATCH

### Check 3

- Bronze: `2018 CCRPI Progress Scores, Targets, Flags by Subgroup 12_14_18.xlsx`, state row with `System Name=All Systems`, `School Name=All Schools`, `Reporting Label=Asian/Pacific Islander`, `Indicator=ELP Progress`, `Grade Cluster=E`, `Indicator Score=100`.
- Transform path: `_apply_detail_level_and_ids` lines 375-404 nulls aggregate geography; `_normalize_demographic` lines 407-435 uses shared aliases.
- Gold: `district_code=NULL`, `school_code=NULL`, `demographic=asian_pacific_islander`, `grade_cluster=elementary`, `indicator=progress_towards_elp`, `indicator_score=100.0`.
- Result: MATCH

### Check 4

- Bronze: `2024 CCRPI Progress Scores, Targets, and Flags by Subgroup.xlsx`, State Charter Schools II - Northwest Classical Academy district row, `Reporting Label=Asian/Pacific Islander`, `Indicator=Mathematics`, `Indicator Score=TFS/NA after read`, `Target=NA`, `Flag=NA`.
- Transform path: `_score_expr` lines 465-481 casts non-numeric/suppressed values to null; aggregate school sentinel handling runs at lines 393-404.
- Gold: `district_code=7830636`, `school_code=NULL`, `demographic=asian_pacific_islander`, `indicator=mathematics_growth`, `indicator_score=NULL`, `target=NULL`, `ccrpi_flag=NULL`.
- Result: MATCH

### Check 5

- Bronze: `2018 CCRPI Progress Scores, Targets, Flags by Subgroup 12_14_18.xlsx`, Appling County Elementary, `System ID=601`, `School ID=0177`, `Reporting Label=English Learners`, `Indicator=ELP Progress`, `Indicator Score=100`, `Target=89.05`, `Flag=G`.
- Transform path: `_transform_era_a` lines 523-535 maps demographic, ELP indicator, score, target, and flag.
- Gold: `district_code=601`, `school_code=0177`, `demographic=english_learners`, `indicator=progress_towards_elp`, `indicator_score=100.0`, `target=89.05`, `ccrpi_flag=green`.
- Result: MATCH

## Notes

- No required fixes were found.
- There are no collapsed-row formulas to recompute: all bronze rows are source-published fact observations and the transform preserves them one-to-one.
- Worktree note: the topic artifacts are currently untracked/modified in git, but artifact timestamps and checksum validation show the on-disk review set is internally fresh.
