# Data Review: georgia_student_growth_model_end_of_course

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: bronze inventory, transform logic, contract, validator report, manifest, and gold parquet reconcile with no required fixes.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH — transform mtime `2026-06-12T19:53:55.231434+00:00`, manifest generated `2026-06-12T19:54:04.747669+00:00`, validation timestamp `2026-06-12T19:54:04.824102+00:00`; validation passed and is newer than the manifest.

## Files Reviewed

- Transform: `src/etl/education/georgiainsights/georgia_student_growth_model_end_of_course/transform.py`
- Contract: `contracts/education/georgia_student_growth_model_end_of_course.odcs.yaml`
- Bronze files: 18 Excel workbooks under `data/bronze/education/georgiainsights/georgia_student_growth_model_end_of_course/` for 2015-2019 and 2023; every current checksum matches `bronze-data-structure.md`.
- Gold files: 18 parquet files under `data/gold/education/georgia_student_growth_model_end_of_course/year={2015,2016,2017,2018,2019,2023}/{schools,districts,states}.parquet`
- Manifest: `data/gold/education/georgia_student_growth_model_end_of_course/_transform_manifest.json`
- Validation report: `data/gold/education/georgia_student_growth_model_end_of_course/_validation.json`
- Supporting docs: `docs/codex-review-contract.md`, `docs/contract-creation.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `data/bronze/education/georgiainsights/georgia_student_growth_model_end_of_course/bronze-data-structure.md`, `src/etl/education/CLAUDE.md`, `AGENTS.md`, `CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS — contract properties exactly match parquet columns and order: `year`, `district_code`, `school_code`, `subject`, then 10 metric columns.
- Column roles and grain: PASS — contract grain is `year, district_code, school_code, subject`; this matches the transform's natural key after `detail_level` is encoded in filenames.
- Metric units and derived quality checks: PASS — count, proportion, and bounded percentile units are present; 17 contract quality checks pass, including received-SGP count/rate consistency and 2023 band-sum invariants.
- Categorical enums: PASS — `subject` enum equals manifest and actual gold values.
- Detail levels and layout metadata: PASS — contract lists `schools`, `districts`, `states`; all expected files exist for each emitted year.
- Foreign-key descriptors: PASS — `district_code` and composite `district_code, school_code` descriptors match education dimensions; validation reports all 210 district keys and 1,049 school keys resolve.
- Schema hash/version consistency: PASS — contract `version: 1.0.0`, `schema_hash: 3f59c82cb62f615ccd7365b3b927db2707b1bfddca3b0106c90a7bc84fd7874e`, and `year_range: 2015-2023` are coherent with current gold and transform output.

## Validator Verification

- `_validation.json` fresh + passing: PASS — timestamp is newer than manifest and `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS — 20 pass, 0 fail, 1 warning.
- Validator warnings explained: PASS — 2023 null spikes are expected because the 2023 redesigned source drops `num_tested`, `pct_received_sgp`, achievement cumulatives, and `pct_typical_or_high_growth`.
- §15b quality-check coverage (cross-column invariants authored): PASS — authored checks cover count subset, received-SGP rate formula, proficiency nesting, 2023 band sum, and old/new growth-family mutual exclusivity.

## Manifest Verification

- Files processed coverage: PASS — all 18 current bronze Excel files appear in `files_processed`; row counts from direct workbook reads match the manifest.
- Categorical and recode coverage: PASS — `subject` has `unmapped_count: 0`; all observed sheet labels and Subject/Content Area values map to canonical subject values.
- Row-count reconciliation: PASS — `total_bronze: 23861`, `total_gold: 23861`, `total_filtered: 0`; every year has expansion factor 1.0.
- Metric stats sanity: PASS — count metrics are non-negative; bounded proportions are within 0-1; `sgp_median` is within 1-99 after the documented 2016 `9999` mask.

## Row and Join Accounting

- Bronze file/year disposition: PASS — 2015-2019 and 2023 are processed; no 2020-2022 bronze files exist, and no empty gold partitions are emitted.
- Filter accounting: PASS — no fact rows are filtered; blank spacer/artifact rows are dropped before manifest bronze counts because they are not records.
- Join accounting: N/A — the transform performs no external joins; the shared charter promotion is an in-place key rewrite and is ledgered as reclassified rows.
- Deduplication accounting: PASS — natural-key collision guard runs before defensive dedup; actual gold has 0 duplicate grain rows.
- Aggregation/unpivot accounting: PASS — sheets are concatenated across subjects without aggregation or row multiplication; per-file row counts are preserved 1:1 in gold.

## Reconciliation Checks

- Artifact freshness: PASS — manifest and validation are current relative to transform.
- Contract freshness: PASS — no `_metadata.json` dependency; contract and parquet schema match.
- Year coverage: PASS — gold years are exactly `[2015, 2016, 2017, 2018, 2019, 2023]`.
- Row preservation: PASS — manifest and direct parquet counts both show 23,861 rows.
- Column coverage: PASS — all fact keys, the `subject` categorical, and all metric families documented in bronze are represented; 2023-only and 2015-2019-only metric gaps are represented as nulls in the opposite era.
- Recode accuracy: PASS — subject recodes preserve curriculum distinctions and apply shared subject normalization.
- Asian-family demographic recodes (§5b): N/A — no demographic or race axis exists.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): N/A — no demographic column exists.
- Demographic collision aggregation before dedup (§5): N/A — no demographic normalization.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS — parquet order is `year`, geography keys, `subject`, metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS — parquet contains no names, RESA, `topic`, `detail_level`, or census/crosswalk IDs.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS — uses `subject`, `num_tested`, `num_received_sgp`, and `_or_above` proficiency columns.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): PASS — `apply_subject_normalization("subject")` runs; no `grade_level` column applies.
- Tidy long format (§9 — no demographics/years/components as column names): PASS — subject is a row categorical; years are partitions.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS — manual anti-joins found 0 district and 0 school FK orphans.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS — contract marks `subject` as categorical and FK roles derive joins.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS — suppression markers become null, aggregate geography is nulled by shared rules, and percent metrics are on 0-1 scale.

## Spot Checks

### Check 1

- Bronze: `GSGM_EOC_2017_School_Level.xlsx`, sheet `EOC_9LIT_2017_School`, `Key=6090291`: `N Tested=244`, `N Received SGP=232`, `% Received SGP=95`, `Median SGP=36`, `% Proficient=33`, `% Developing=69`, `% Typical or High Growth=52`.
- Transform path: `_split_compound_key`, `_cast_metric_columns`, `_read_per_subject_stem`, lines 468-486, 560-576, 628-667.
- Gold: `year=2017`, `district_code=609`, `school_code=0291`, `subject=9th_grade_literature_and_composition`; counts preserved and percentages scaled to `0.95`, `0.33`, `0.69`, `0.52`.
- Result: MATCH

### Check 2

- Bronze: `SGP_EOC_Aggs_School_Level_2023.xlsx`, sheet `School - Algebra I`, `System Code=655`, `School Code=0193`: `Number Received SGP=27`, `SGP Median=28`, SGP bands `51.851851851851855 / 33.333333333333336 / 14.814814814814815`.
- Transform path: `_read_level_label`, `_cast_metric_columns`, lines 704-733 and 560-576.
- Gold: `year=2023`, `district_code=655`, `school_code=0193`, `subject=algebra_i`; `num_received_sgp=27`, `sgp_median=28`, SGP bands `0.518519 / 0.333333 / 0.148148`; old metric-family columns are NULL.
- Result: MATCH

### Check 3

- Bronze: `GSGM_EOC_2016_System_Level.xls`, sheet `EOC_PHY_2016_System`, 11 rows including `System Code=630` publish `9999` in five bounded metric columns.
- Transform path: `_null_9999_sentinel` and manifest mask recording, lines 510-538 and 764-772.
- Gold: `year=2016`, `district_code=630`, `school_code=NULL`, `subject=physical_science`; the five impossible `9999` values are NULL. Manifest records 11 masked values for each affected column.
- Result: MATCH

### Check 4

- Bronze: `GSGM_EOC_2015_School.xls`, sheet `EOC_9LIT_2015_School`, charter row `Key=7820108`, school `0108`, with `N Tested=86`, `N Received SGP=28`, `% Received SGP=33`, `Median SGP=59.5`.
- Transform path: `_split_compound_key` plus `promote_charter_system_to_campus_district`, lines 468-486 and 813-819; shared utility rewrites school-level `782 + 0108` to campus district `7820108`.
- Gold: `year=2015`, `district_code=7820108`, `school_code=0108`, `subject=9th_grade_literature_and_composition`; metrics are preserved and percentages scaled.
- Result: MATCH

## Notes

- No prior `data-review-claude.md` or existing `data-review-codex.md` was used to drive findings.
- Direct checks also found 0 violations for 2023 SGP band sums, 0 old/new growth metric co-occurrences, 0 `num_received_sgp > num_tested` rows, and 0 received-SGP percentage/count mismatches beyond the authored tolerance.
