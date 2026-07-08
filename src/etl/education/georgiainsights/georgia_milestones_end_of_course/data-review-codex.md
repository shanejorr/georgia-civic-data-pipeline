# Data Review: georgia_milestones_end_of_course

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Contract, manifest, validator, bronze files, and gold parquet reconcile; no must-fix bronze-to-gold accuracy issues were found.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH — `scripts/check_bronze_freshness.py` passed for all 72 bronze files; transform mtime `2026-06-12T18:21:44Z`, manifest `2026-06-12T18:24:23Z`, validation `2026-06-12T18:24:23Z`, validation passed.

## Files Reviewed

- Transform: `src/etl/education/georgiainsights/georgia_milestones_end_of_course/transform.py`
- Contract: `contracts/education/georgia_milestones_end_of_course.odcs.yaml`
- Bronze files: 72 `.xls` / `.xlsx` / `.zip` files under `data/bronze/education/georgiainsights/georgia_milestones_end_of_course/`
- Gold files: 33 parquet files, `year=2015` through `year=2025`, each with `schools.parquet`, `districts.parquet`, and `states.parquet`
- Manifest: `data/gold/education/georgia_milestones_end_of_course/_transform_manifest.json`
- Validation report: `data/gold/education/georgia_milestones_end_of_course/_validation.json`
- Supporting docs: `docs/codex-review-contract.md`, `docs/contract-creation.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `data/bronze/education/georgiainsights/georgia_milestones_end_of_course/bronze-data-structure.md`, `src/etl/education/CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS — contract columns exactly match sampled parquet order: `year`, `district_code`, `school_code`, `administration`, `subject`, then 17 metric columns.
- Column roles and grain: PASS — `year`, education FKs, `administration`, and `subject` define the natural grain; no demographic column is expected because bronze has no demographic breakdown.
- Metric units and derived quality checks: PASS — count, score, percentile, and proportion units are coherent; contract includes range and consistency checks for bounded proportions, counts, `avg_scale_score`, `sgp_median`, achievement-level sums, Lexile complements, SGP bands, and subject-specific metric placement.
- Categorical enums: PASS — `administration` enum is `winter`, `spring`, `full_year`; `subject` enum contains the 11 canonical subject values produced in gold.
- Detail levels and layout metadata: PASS — contract lists `schools`, `districts`, and `states`; gold has all three detail files for each year from 2015 through 2025.
- Foreign-key descriptors: PASS — district and composite school FK descriptors match education dimension conventions.
- Schema hash/version consistency: PASS — contract version is `1.0.0`; schema hash is present; year range and available years match gold layout.

## Validator Verification

- `_validation.json` fresh + passing: PASS — validation timestamp is newer than manifest timestamp and `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS — 21 validation checks passed, including `contract_parquet_schema`, `grain_uniqueness`, `contract_quality_sql`, `foreign_keys`, `canonical_vocabulary`, and geography nulling.
- Validator warnings explained: N/A — validation summary reports 0 warnings.
- §15b quality-check coverage (cross-column invariants authored): PASS — authored checks cover achievement partition sums, cumulative proficiency consistency, Lexile complements, SGP growth-band sums, SGP subject scope, Lexile subject scope, `pct_enrolled_tested` scope, and non-null `num_tested`.

## Manifest Verification

- Files processed coverage: PASS — all 72 current bronze files appear in `files_processed`; no missing or extra files.
- Categorical and recode coverage: PASS — independent raw subject-label inventory found 118 labels, all present in the manifest; `administration` and `subject` both have `unmapped_count: 0`.
- Row-count reconciliation: PASS — manifest `total_gold` is 94,753 and actual parquet row count is 94,753. Manifest explains 159 explicit filtered rows: 150 `footnote_row` and 9 `all_metric_columns_null`.
- Metric stats sanity: PASS — proportions are within `[0, 1]`, counts are non-negative, `avg_scale_score` is within EOC scale bounds, and SGP percentile values are within 0-100.

## Row and Join Accounting

- Bronze file/year disposition: PASS — filename parsing maps Winter to ending school year +1, Spring to same year, and Full-Year range to end year; manifest years cover 2015-2025 with no gaps.
- Filter accounting: PASS — transform filters footnote/footer rows at lines 546-562 and all-null template rows at lines 876-887; traced 2024 Algebra CC state rows are all-null template rows and absent from gold as documented.
- Join accounting: N/A — the transform does not join external lookup tables. Charter code promotion is a pure column rewrite, ledgered as reclassified rows for 2015-2017.
- Deduplication accounting: PASS — collision guard runs before defensive dedup at lines 941-972; actual gold has zero duplicate natural keys.
- Aggregation/unpivot accounting: PASS — no transform-time aggregation or rollup is performed; rows are preserved after sheet/member concatenation except the documented filters.

## Reconciliation Checks

- Artifact freshness: PASS — bronze freshness gate passed and runtime artifacts are current relative to the transform.
- Contract freshness: PASS — contract was emitted after the transform run and matches current parquet; no `_metadata.json` dependency.
- Year coverage: PASS — gold years are 2015-2025, matching manifest and filename-derived source coverage.
- Row preservation: PASS — row counts reconcile to manifest; filtered rows are documented template/footer rows, not observations.
- Column coverage: PASS — source metric columns map to gold metrics; name/RESA columns are excluded as dimension/non-fact attributes.
- Recode accuracy: PASS — subject aliases such as `History`, `U. S. History`, and `United States History` all map to `us_history`; `Algebra CC` maps to `algebra_concepts_and_connections`; administration values derive correctly from filename seasons.
- Asian-family demographic recodes (§5b): N/A — no demographic column or race bucket exists in this topic.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): N/A — no demographic breakdown exists.
- Demographic collision aggregation before dedup (§5): N/A — no demographic normalization or demographic collision path exists.
- Fact-table column order (year → geo → demographic → categoricals → metrics, §1): PASS — parquet order is `year`, `district_code`, `school_code`, then `administration`, `subject`, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS — exported parquet excludes `detail_level`, names, RESA, and census IDs.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS — uses `subject`, `num_tested`, `num_received_sgp`, `pct_*_learner`, and `_or_above` proficiency threshold names.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): PASS — `subject` is passed through `apply_subject_normalization`; no `grade_level` column exists.
- Tidy long format (§9 — no demographics/years/components as column names): PASS — subjects and administrations are row values, not wide columns.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS — validation reports all 222 district keys and all 1,188 composite school keys resolve.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS — contract exposes `administration` and `subject` as categoricals and FKs derive from the education dimension contracts.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS — IDs are strings, percent metrics are 0-1, suppressed metrics are null, and no prohibited fact-table attributes are present.

## Spot Checks

### Check 1

- Bronze: `Winter 2014 EOC School.zip`, member `School - History.xls`, row for Appling High: `System Code=601`, `School Code=103`, `N=117`, `Mean Scale Score=516.1709401709402`, `% Beginning Learner=21.367521367521366`.
- Transform path: `_read_zip_per_subject()` plus `_format_ids()` and `_cast_metric_columns()` at `transform.py:702-749` and `transform.py:624-647`.
- Gold: `year=2015/schools.parquet` row `district_code='601'`, `school_code='0103'`, `administration='winter'`, `subject='us_history'` has `num_tested=117`, `avg_scale_score=516.1709401709402`, `pct_beginning_learner=0.21367521367521367`.
- Result: MATCH

### Check 2

- Bronze: `Winter 2014 EOC School.zip`, member `School - History.xls`, Baldwin High row has `N=4` and suppression marker `-----` for score and proficiency metrics.
- Transform path: `_null_suppression_markers()` and `_cast_metric_columns()` at `transform.py:604-647`; all-null filter keeps the row because `num_tested` is non-null.
- Gold: `year=2015/schools.parquet` row `district_code='605'`, `school_code='0189'`, `administration='winter'`, `subject='us_history'` has `num_tested=4` and null score/proficiency metrics.
- Result: MATCH

### Check 3

- Bronze: `Spring-2025-EOC-School-Level.xlsx`, sheet `School - American Literature`, Appling County High row has `Number Tested=156`, Lexile below/above `33.97435897435897` / `66.02564102564102`, `Number Received SGP=143`, `SGP Median=52`, and SGP bands `32.86713286713287`, `32.16783216783217`, `34.96503496503497`.
- Transform path: `_read_multi_sheet_workbook()` plus `_canonical_header()` and `_cast_metric_columns()` at `transform.py:752-796` and `transform.py:624-647`.
- Gold: `year=2025/schools.parquet` row `district_code='601'`, `school_code='0103'`, `administration='spring'`, `subject='american_literature_and_composition'` has `num_tested=156`, Lexile `0.3397435897435897` / `0.6602564102564102`, `num_received_sgp=143`, `sgp_median=52.0`, and SGP bands `0.3286713286713287`, `0.32167832167832167`, `0.3496503496503497`.
- Result: MATCH

### Check 4

- Bronze: `Spring-2024-EOC-State-Level.xlsx` and `Full-Year-2023-2024-EOC-State-Level.xlsx`, sheet `State - Algebra CC`, each contains one row for `Algebra: Concepts and Connections` with every metric cell blank; school/system Algebra CC sheets are header-only.
- Transform path: all-metric-null template filter at `transform.py:876-887`.
- Gold: `year=2024/*.parquet` contains 0 rows where `subject='algebra_concepts_and_connections'`; `year=2025` winter Algebra CC has populated rows from `Winter-2024-*`.
- Result: MATCH

## Notes

- No collapsed-row or aggregate recomputation case exists in this transform; the transform preserves source aggregate rows as published rather than deriving district/state rows from school rows.
- The manifest's `filtered_explicit` count includes footnote rows filtered before `record_bronze()`, so `total_gold = total_bronze - all_metric_columns_null` while footnotes remain separately ledgered as explicit filters.
