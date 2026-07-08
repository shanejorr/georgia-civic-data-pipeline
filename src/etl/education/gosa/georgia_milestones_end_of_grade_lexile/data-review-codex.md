# Data Review: georgia_milestones_end_of_grade_eog_lexile_scores

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze-to-gold row coverage, schema, recodes, metric values, geography nulling, and validator output all reconcile; no must-fix transformation defects found.

## Summary

- Review date: 2026-06-11
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze checksum gate passed for all 9 CSVs; transform mtime `2026-06-12T00:04:10Z`, manifest `generated_at=2026-06-12T00:04:24Z`, validation `timestamp=2026-06-12T00:04:24Z`, validation passed.

## Files Reviewed

- Transform: `src/etl/education/gosa/georgia_milestones_end_of_grade_eog_lexile_scores/transform.py`
- Contract: `contracts/education/georgia_milestones_end_of_grade_eog_lexile_scores.odcs.yaml`
- Bronze files: 9 CSVs for years 2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024 under `data/bronze/education/gosa/georgia_milestones_end_of_grade_eog_lexile_scores/`
- Gold files: 27 parquet files, one `states.parquet`, `districts.parquet`, and `schools.parquet` for each processed year under `data/gold/education/georgia_milestones_end_of_grade_eog_lexile_scores/`
- Manifest: `data/gold/education/georgia_milestones_end_of_grade_eog_lexile_scores/_transform_manifest.json`
- Validation report: `data/gold/education/georgia_milestones_end_of_grade_eog_lexile_scores/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`, relevant utility modules, and sibling Lexile/Milestones transforms.

## Contract Verification

- Schema/parquet column match: PASS - all 27 parquet files match contract order: `year`, `district_code`, `school_code`, `grade_level`, `subject`, `num_tested`, `num_with_lexile`, `num_at_or_above_lexile_midpoint`, `num_without_lexile`, `avg_lexile_score`.
- Column roles and grain: PASS - contract roles match the transform declaration; grain is `year`, `district_code`, `school_code`, `grade_level`, `subject`, with nullable geography keys for aggregate levels.
- Metric units and derived quality checks: PASS - four counts use `unit: count`; `avg_lexile_score` uses `unit: score`, `value_min: 0`, `value_max: 2000`; all derived range/non-negative checks are present.
- Categorical enums: PASS - `grade_level` enum is `03`-`08`, `subject` enum is `english_language_arts`; both match manifest and gold distinct values.
- Detail levels and layout metadata: PASS - `detail_levels=['schools','districts','states']`, default detail `schools`, partition column `year`, and path template match current layout.
- Foreign-key descriptors: PASS - `district_code -> districts`; `school_code -> schools` with composite target `(district_code, school_code)`.
- Schema hash/version consistency: PASS - contract version is `1.0.0`, schema hash is present (`971f8f1c82d6b245c78083940fd83a5c5f13c30c86c1051d6cc24a1426f20420`), and contract mtime follows the manifest from the same transform run.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp is after manifest generation and reports `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - validator reports 20 pass, 0 fail, 1 warning; schema, grain uniqueness, quality SQL, foreign keys, geography nulling, and canonical vocabulary all pass.
- Validator warnings explained: PASS - the only warning is `num_without_lexile` null-rate spikes in 2021-2024; raw bronze has 6,387 / 6,766 / 6,837 / 6,870 nulls in that column after `TFS` suppression for 2021-2024, matching the transform notes and contract caveat.
- section 15b quality-check coverage (cross-column invariants authored): PASS - authored checks enforce the valid subset relationships; the stronger `num_with_lexile + num_without_lexile = num_tested` identity is correctly not authored because source aggregate rows demonstrably fail it.

## Manifest Verification

- Files processed coverage: PASS - manifest lists exactly the 9 current bronze CSVs; `check_bronze_freshness.py` reports all checksums match and no unanalyzed files.
- Categorical and recode coverage: PASS - `detail_level`, `grade_level`, and fixed `subject` all have `unmapped_count=0`; manifest produced values match gold and contract enums.
- Row-count reconciliation: PASS - manifest reports 60,908 bronze rows and 60,908 gold rows, zero filtered rows, and per-year expansion factor `1.0` for every processed year.
- Metric stats sanity: PASS - counts are non-negative; `avg_lexile_score` ranges 300.0-1435.0, within the 0-2000 contract range; no metric scale issue.

## Row and Join Accounting

- Bronze file/year disposition: PASS - all source years on disk are processed; 2020 is absent in bronze and absent in gold, with source-backed COVID testing-suspension rationale.
- Filter accounting: N/A - the transform records no filters and direct reconstruction shows one output row per source row.
- Join accounting: N/A - the transform performs no joins/lookups; validator FK checks confirm all populated district and composite school keys resolve in dimensions.
- Deduplication accounting: PASS - duplicate natural-key count is 0 in every bronze file and 0 in gold; `deduplicate_by_detail_level(..., sort_col="num_tested")` is a no-op safety net.
- Aggregation/unpivot accounting: N/A - no unpivot or row collapse occurs; state and district rows are source-published aggregate rows and are preserved, not recomputed.

## Reconciliation Checks

- Artifact freshness: PASS - transform, contract, manifest, validation, bronze inventory, and gold inventory are current and mutually consistent.
- Contract freshness: PASS - contract was emitted from the current transform/gold run; no `_metadata.json` dependency.
- Year coverage: PASS - gold years are 2015-2019 and 2021-2024, matching bronze and contract `available_years`; 2020 is correctly absent.
- Row preservation: PASS - independently reconstructed expected rows from bronze matched actual gold exactly: 60,908 expected rows, 60,908 gold rows, 0 missing, 0 extra.
- Column coverage: PASS - every fact key, categorical, and metric field from the bronze profile is represented or validly excluded as a dimension/non-gold attribute; no names or `SCHOOL_YEAR` leak into gold.
- Recode accuracy: PASS - `State/District/School Level` map to `state/district/school`; grades `03`-`08` remain canonical; fixed ELA subject is source-backed by the Lexile EOG topic.
- Asian-family demographic recodes (section 5b): N/A - no demographic/race axis in bronze or gold.
- Demographic mutual exclusivity (section 5a - no rollup row alongside split source rows in the same category): N/A - no demographic column.
- Demographic collision aggregation before dedup (section 5): N/A - no demographic normalization/collisions.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - parquet order is `year`, geography keys, categoricals, metrics; no demographic column applies.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, section 11/section 12): PASS - parquet files contain no `topic`, `detail_level`, `district_name`, `school_name`, `district_census_id`, or `school_year`.
- Canonical column vocabulary (section 16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - column names are canonical for assessment/Lexile topics.
- Shared categorical utilities applied (section 10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): PASS - transform uses `normalize_grade_column` and `apply_subject_normalization`.
- Tidy long format (section 9 - no demographics/years/components as column names): PASS - rows are one year/geography/grade/subject observation; no year or demographic values are encoded as columns.
- FK keys present in dimension tables (section 13 - `district_code`, `school_code`, `demographic`): PASS - validator reports 236 district keys and 1,968 school keys resolve; no demographic FK applies.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - contract exposes `grade_level` and `subject` as categoricals and declares the expected district/school FK joins.
- Standards compliance (catch-all for section 1-section 16 items not enumerated above): PASS - percentages do not apply, suppression markers become null, IDs remain strings with leading zeroes preserved, and aggregate geography nulling validates.

## Spot Checks

### Check 1

- Bronze: `georgia_milestones_end_of_grade_eog_lexile_scores_2024.csv`, Clayton County / Roberta T. Smith Elementary (`SCHOOL_DSTRCT_CD=631`, `INSTN_NUMBER=0200`), grade `04`: tested `132`, with Lexile `132`, midpoint `19`, no Lexile `TFS`, average `607`.
- Transform path: `_transform_era1()` lines 280-348 maps detail/grade/subject and casts metrics with `strict=False`; `export_to_parquet()` drops detail level to `schools.parquet`.
- Gold: `year=2024/schools.parquet`, `district_code=631`, `school_code=0200`, `grade_level=04`, `subject=english_language_arts`: `num_tested=132`, `num_with_lexile=132`, `num_at_or_above_lexile_midpoint=19`, `num_without_lexile=NULL`, `avg_lexile_score=607.0`.
- Result: MATCH

### Check 2

- Bronze: `georgia_milestones_end_of_grade_eog_lexile_scores_2015.csv`, state aggregate grade `03`: district/school sentinels `All`, tested `132718`, with Lexile `131772`, midpoint `61786`, without Lexile `1272`, average `639.2`.
- Transform path: lines 295-309 convert `All` geography sentinels to NULL and set `year`; lines 425-431 apply shared aggregate geography nulling.
- Gold: `year=2015/states.parquet`, `district_code=NULL`, `school_code=NULL`, `grade_level=03`: `num_tested=132718`, `num_with_lexile=131772`, `num_at_or_above_lexile_midpoint=61786`, `num_without_lexile=1272`, `avg_lexile_score=639.2`.
- Result: MATCH

### Check 3

- Bronze: `georgia_milestones_end_of_grade_eog_lexile_scores_2019.csv`, Taliaferro County district row (`SCHOOL_DSTRCT_CD=731`, `INSTN_NUMBER=All`), grade `03`: all five metric cells blank/null.
- Transform path: lines 339-346 cast metric columns with `strict=False`, preserving blanks as NULL; lines 417-423 dedup by detail level without changing the row.
- Gold: `year=2019/districts.parquet`, `district_code=731`, `school_code=NULL`, `grade_level=03`: all five metrics are NULL.
- Result: MATCH

### Check 4

- Bronze: `georgia_milestones_end_of_grade_eog_lexile_scores_2023.csv`, state aggregate grade `03`: tested `123974`, with Lexile `123891`, midpoint `56992`, without Lexile `166`, average `645.4`; the source-published with+without total does not reconcile to tested.
- Transform path: lines 343-348 maps the published metrics straight across; lines 643-685 author only the subset checks, not the invalid sum identity.
- Gold: `year=2023/states.parquet`, `district_code=NULL`, `school_code=NULL`, `grade_level=03`: the same five published metric values are preserved exactly.
- Result: MATCH

## Needs Follow-up

- The bronze profile and transform/contract prose understate blank metric cells before 2019: direct reads show blank/null metric cells in 2015-2018 as well as 2019. The transformation is still accurate because those blanks are preserved as NULL and the full reconstructed bronze frame matches gold exactly; this is documentation/metadata precision, not a must-fix data defect.

## Notes

- Prior `data-review-claude.md` / existing `data-review-codex.md` content was not read before these findings.
- No deeper optional checks were deferred; no early-stop condition triggered.
