# Data Review: georgia_milestones_end_of_grade

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Contract, manifest, validator, bronze coverage, recodes, row accounting, and targeted bronze-to-gold traces support the current transform; no must-fix accuracy defects found.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH — `transform.py` mtime 2026-06-12T19:06:47+00:00, manifest generated 2026-06-12T19:07:20+00:00, validation timestamp 2026-06-12T19:07:21+00:00 with `"passed": true`; bronze freshness check passed all 30 checksums with no unanalyzed files.

## Files Reviewed

- Transform: `src/etl/education/georgiainsights/georgia_milestones_end_of_grade/transform.py`
- Contract: `contracts/education/georgia_milestones_end_of_grade.odcs.yaml`
- Bronze files: 30 current `.xls` / `.xlsx` / `.zip` files under `data/bronze/education/georgiainsights/georgia_milestones_end_of_grade/`, spanning 2015-2019 and 2021-2025; 2020 absent by source cancellation.
- Gold files: 30 parquet files under `data/gold/education/georgia_milestones_end_of_grade/year=*/{schools,districts,states}.parquet`, total 235,248 rows.
- Manifest: `data/gold/education/georgia_milestones_end_of_grade/_transform_manifest.json`
- Validation report: `data/gold/education/georgia_milestones_end_of_grade/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, data-cleaning standards, bronze structure report, education `CLAUDE.md`, and relevant shared utility modules.

## Contract Verification

- Schema/parquet column match: PASS — contract property order exactly matches parquet columns: `year`, geography keys, `grade_level`, `subject`, `assessment_type`, then metrics.
- Column roles and grain: PASS — contract grain is `year, district_code, school_code, grade_level, subject, assessment_type`; validation confirms grain uniqueness.
- Metric units and derived quality checks: PASS — counts, score bounds, proportions, SGP percentile, and custom std-dev non-negative checks are present; `scale_score_std_dev` has no `unit` but is guarded by explicit quality SQL.
- Categorical enums: PASS — `grade_level`, `subject`, and `assessment_type` enums match manifest `gold_values_produced` and actual gold distinct values.
- Detail levels and layout metadata: PASS — `schools`, `districts`, `states`; path template and available years match the gold layout.
- Foreign-key descriptors: PASS — `district_code` joins districts and `school_code` joins schools on `(district_code, school_code)`; manual anti-joins found 0 unmatched district rows and 0 unmatched school rows.
- Schema hash/version consistency: PASS — contract version is `1.0.0`, schema hash is `a0a3f13273ab49ff497eff9e1c3b7fa5993ee879e21517306070f02a049263db`, and current gold schema matches the emitted contract.

## Validator Verification

- `_validation.json` fresh + passing: PASS — validation timestamp is newer than manifest generation and `"passed": true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS — schema, grain uniqueness, all 30 contract quality checks, foreign keys, canonical vocabulary, and geography nulling passed.
- Validator warnings explained: PASS — the single warning is 8 null-rate spikes; Lexile is structurally absent before 2018, and 2018-2019 `avg_scale_score` spikes are from preserved EOC/Combined rows whose score/proficiency cells are suppressed while source rows remain valid observations.
- §15b quality-check coverage (cross-column invariants authored): PASS — achievement-band partition, cumulative proficiency, Lexile complement, Lexile-on-ELA, SGP partition, SGP placement, 2021-only participation, EOC-era bounds, and std-dev non-negative checks are authored and passing.

## Manifest Verification

- Files processed coverage: PASS — manifest lists all 30 current bronze data files; no current file is missing from `files_processed`, and no processed file is absent from disk.
- Categorical and recode coverage: PASS — `subject`, `assessment_type`, and `grade_level` each have `unmapped_count: 0`; maps correctly fold Reading Status and SGP blocks into parent academic subjects.
- Row-count reconciliation: PASS — manifest `total_gold` is 235,248 and matches actual parquet count. Explicit filtering is accounted for by footnote/legend rows, state placeholders, all-null non-administered blocks, and folded Reading Status/SGP child rows.
- Metric stats sanity: PASS — percent metrics are on 0-1 scale, score ranges are within contract bounds, counts are non-negative, and SGP metrics appear only in 2024-2025 ELA/Math grades 4-8.

## Row and Join Accounting

- Bronze file/year disposition: PASS — every current bronze file is processed; years covered are 2015-2019 and 2021-2025, matching source inventory and gold partitions.
- Filter accounting: PASS — filters are ledgered: 183 footnote/legend rows, 106 state placeholders, 2,434 non-administered placeholder rows, 48,278 Reading Status child rows folded, and 21,984 SGP child rows folded.
- Join accounting: PASS — metric-family folding uses parent-key existence and null-aware geography sentinels; checks found no interim `reading_status` / `sgp_*` subjects in final gold and no Lexile/SGP metrics on invalid subjects.
- Deduplication accounting: PASS — no duplicate rows exist at the contract grain; dedup is defensive after `assert_no_natural_key_collisions`.
- Aggregation/unpivot accounting: PASS — bronze subject blocks are unpivoted into subject rows, and child metric-family rows are folded onto parent ELA/Math rows; no count aggregation or weighted average is introduced by the transform.

## Reconciliation Checks

- Artifact freshness: PASS — bronze checksums, manifest, validation, contract, and gold are current relative to each other.
- Contract freshness: PASS — contract is emitted by current transform/gold and there is no `_metadata.json` dependency.
- Year coverage: PASS — gold years are `[2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025]`; 2020 is absent by source cancellation.
- Row preservation: PASS — row losses are explained by documented filters/folds; suppressed district/school rows are preserved as NULL metrics when the group has real observations.
- Column coverage: PASS — fact keys and categoricals land in gold; names/RESA are excluded as dimension attributes; metric headers map to the declared metric columns.
- Recode accuracy: PASS — `English Language Arts - EOC` -> `subject=english_language_arts, assessment_type=eoc`, `HS Physical Science` -> `physical_science`, `Reading Status*` / `Reading Status^` -> folded ELA metrics, and `% SGPTypical Growth` -> `pct_sgp_typical_growth` are correct.
- Asian-family demographic recodes (§5b): N/A — this topic has no demographic column or race/ethnicity values.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): N/A — no demographic axis.
- Demographic collision aggregation before dedup (§5): N/A — no demographic axis.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS — actual parquet order is `year`, `district_code`, `school_code`, `grade_level`, `subject`, `assessment_type`, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS — actual parquet columns omit `topic`, `detail_level`, `district_name`, `school_name`, `RESA`, and census IDs.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS — canonical names are used, including `num_tested`, `grade_level`, `subject`, `num_received_sgp`, and `_or_above` proficiency thresholds.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): PASS — transform applies both shared normalizers after local maps.
- Tidy long format (§9 — no demographics/years/components as column names): PASS — subjects and assessment variants are categorical values; metric-family blocks are folded into parent rows.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS — 0 district FK misses, 0 composite school FK misses; demographic N/A.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS — contract roles expose grade, subject, and assessment filters plus district/school joins.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS — suppression becomes NULL, IDs remain strings with leading zeros, aggregate geography is nulled by shared rules, and metric units/quality checks support API semantics.

## Spot Checks

### Check 1

- Bronze: `Spring 2015 EOG System.zip` member `Gr3_System.xls`, APPLING COUNTY row: ELA `Number Tested=271`, `Mean Scale Score=497.95571955719555`, `% Beginning Learner=33.579335793357934`, `% Proficient Learner & Above=30.99630996309963`.
- Transform path: `_read_zip_per_grade()` -> `_unpivot_blocks()` -> `_finalize_member_frame()` -> `_cast_and_scale_metrics()` (`transform.py:1036-1088`, `826-938`, `941-968`, `779-803`).
- Gold: `year=2015, district_code=601, school_code=NULL, grade_level=03, subject=english_language_arts, assessment_type=eog` has `num_tested=271`, `avg_scale_score=497.95571955719555`, `pct_beginning_learner=0.33579335793357934`, `pct_proficient_learner_or_above=0.3099630996309963`.
- Result: MATCH

### Check 2

- Bronze: `Spring 2021 EOG - System Level.zip` member `Spring 2021 EOG - System Level - Grade 8.xlsx`, APPLING COUNTY row: ELA-EOG headers include duplicated `Number Tested` / `Number Tested.1`; values are `239` and `91.570881`, where the second is the missing participation-rate column.
- Transform path: `_repair_missing_pct_enrolled()` relabels the duplicate sub-header, then `_cast_and_scale_metrics()` divides by 100 (`transform.py:626-661`, `779-803`).
- Gold: `year=2021, district_code=601, grade_level=08, subject=english_language_arts, assessment_type=eog` has `num_tested=239`, `pct_enrolled_tested=0.91570881`, `avg_scale_score=508.640167`, plus folded Lexile metrics `0.34309623` / `0.65690377`.
- Result: MATCH

### Check 3

- Bronze: `Spring-2025-EOG-State-Level-All-Grades.xlsx`, sheet `State - Grade 5`, Mathematics SGP block has `% SGPTypical Growth` (missing space) with value `30.91767949299847`; same row has `Number Received SGP=118974`, `SGP Median=50`, `% SGP Low Growth=34.341116546472335`, `% SGP High Growth=34.74120396052919`.
- Transform path: `METRIC_NAME_MAP` maps `% SGPTYPICAL GROWTH` to `pct_sgp_typical_growth`, and `_fold_metric_family_rows()` copies SGP metrics onto the parent Mathematics row (`transform.py:241-265`, `1245-1331`).
- Gold: `year=2025, state, grade_level=05, subject=mathematics, assessment_type=eog` has `num_received_sgp=118974`, `sgp_median=50.0`, `pct_sgp_low_growth=0.34341116546472335`, `pct_sgp_typical_growth=0.3091767949299847`, `pct_sgp_high_growth=0.3474120396052919`.
- Result: MATCH

### Check 4

- Bronze: `Spring_2018_EOG-State_Level.xlsx`, grade 3 state row: `Reading Status*` has `% Below Grade Level=31.698990772349845` and `% Grade Level or Above=68.30100922765016`; ELA-EOG has `Number Tested=134162` and `Mean Scale Score=504.36698170868056`.
- Transform path: `Reading Status*` maps to interim `reading_status`, then `_fold_metric_family_rows()` folds Lexile metrics onto the parent `english_language_arts` row (`transform.py:199-204`, `1245-1331`).
- Gold: `year=2018, state, grade_level=03, subject=english_language_arts, assessment_type=eog` has ELA metrics plus `pct_below_grade_level_lexile=0.31698990772349845` and `pct_grade_level_or_above_lexile=0.6830100922765016`; no `reading_status` subject rows remain.
- Result: MATCH

### Check 5

- Bronze: `Spring 2021 EOG - System Level.zip`, APPLING COUNTY grade 8 Science-EOC row has all `--` metric cells; Science Combined has `Number Tested=238`, participation `91.187739`, and proficiency percentages.
- Transform path: suppression casts with `strict=False`; all-null placeholder groups are dropped only when the whole year/detail/grade/subject/assessment group has no data, so small-N suppressed entity rows survive (`transform.py:779-803`, `1210-1242`).
- Gold: `year=2021, district_code=601, grade_level=08, subject=science, assessment_type=eoc` is present with NULL metrics, while Science Combined preserves `num_tested=238`, `pct_enrolled_tested=0.91187739`, and scaled proficiency metrics.
- Result: MATCH

## Notes

- The bronze structure report contains corrected-era notes; direct bronze inspection confirms the transform follows the corrected 2016-2021 EOG/EOC split, 2017 Science/Social Studies coverage, 2021 merged header repair, and 2022 Physical Science presence.
- Manual checks found 0 duplicate contract-grain rows, 0 FK misses, 0 geography-nulling violations, 0 interim metric-family subjects in gold, and max component reconciliation deltas of about 0.001 (within the contract tolerance).
- No `## Required Fixes` section is included because status is PASS.
