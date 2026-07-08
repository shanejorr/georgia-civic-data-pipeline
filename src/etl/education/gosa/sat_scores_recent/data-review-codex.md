# Data Review: sat_scores_recent

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Contract, manifest, validator, bronze inventory, and gold Parquet reconcile; no bronze-to-gold accuracy defects requiring transform changes were found.

## Summary

- Review date: 2026-06-10
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze checksum gate passed for all 22 files; transform mtime 2026-06-10T22:07:17Z is earlier than manifest generated_at 2026-06-10T22:09:05Z, and validation timestamp 2026-06-10T22:09:05Z is later than the manifest.

## Files Reviewed

- Transform: `src/etl/education/gosa/sat_scores_recent/transform.py`
- Contract: `contracts/education/sat_scores_recent.odcs.yaml`
- Bronze files: 22 files, `sat_scores_recent_2004.csv` through `sat_scores_recent_2024.csv`, including both 2016 old and new format files
- Gold files: 63 Parquet files, 21 years x 3 detail files (`schools.parquet`, `districts.parquet`, `states.parquet`)
- Manifest: `data/gold/education/sat_scores_recent/_transform_manifest.json`
- Validation report: `data/gold/education/sat_scores_recent/_validation.json`
- Supporting docs: `docs/codex-review-contract.md`, `docs/contract-creation.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`, and relevant utility snippets from `src/utils/`.

## Contract Verification

- Schema/parquet column match: PASS - every gold file has `year`, `district_code`, `school_code`, `demographic`, `test_component`, `num_tested`, `avg_score` in contract order.
- Column roles and grain: PASS - contract grain is `year`, `district_code`, `school_code`, `demographic`, `test_component`; actual gold has zero duplicate grain rows.
- Metric units and derived quality checks: PASS - `num_tested` is `unit: count` and Float64 per the documented SAT exception; `avg_score` is `unit: score` with a component-specific SQL range check.
- Categorical enums: PASS - contract enums match manifest and actual gold values for 10 demographics and 15 test components.
- Detail levels and layout metadata: PASS - contract detail levels are `schools`, `districts`, `states`; gold has all three for every available year.
- Foreign-key descriptors: PASS - `district_code`, composite `(district_code, school_code)`, and `demographic` descriptors match dimensions; direct FK checks found 0 unmatched district, school, or demographic keys.
- Schema hash/version consistency: PASS - contract version is `1.0.0`, schema hash is present, year range is 2004-2024, and available years match the gold layout.

## Validator Verification

- `_validation.json` fresh + passing: PASS - `passed: true`; validation timestamp is later than manifest generation.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - all checks passed except the expected null-rate warning.
- Validator warnings explained: PASS - null-rate warnings are source-consistent: `avg_score` spikes in 2008-2010 align with sparse wide demographic cells and `Too Few Students`; `num_tested` spikes in 2021-2023 align with increased TFS suppression in low-participation recent SAT files.
- section 15b quality-check coverage (cross-column invariants authored): PASS - contract includes 11 SQL checks covering non-empty data, enum conformance, count non-negativity, component score ranges, `avg_score` requiring positive `num_tested`, demographic year windows, test-component year windows, essay-total reconciliation, and unsuppressed state all-students rows.

## Manifest Verification

- Files processed coverage: PASS - manifest processed all 22 current bronze data files; no current file is missing and no processed file is absent from disk.
- Categorical and recode coverage: PASS - `demographic` and `test_component` both have `unmapped_count: 0`; `Asian` maps to `asian_pacific_islander`; old and redesigned SAT component vocabularies stay distinct.
- Row-count reconciliation: PASS - 44,422 bronze rows produced 175,971 gold rows through expected wide-to-long expansion and official aggregate materialization; 59,052 blank wide cells and 3 legend rows are explicitly filtered.
- Metric stats sanity: PASS - metric ranges are plausible after the 16 recorded `avg_score` masks; contract quality SQL confirms no remaining out-of-component-scale SAT scores.

## Row and Join Accounting

- Bronze file/year disposition: PASS - 2004-2024 are represented; both 2016 files are retained because old-format and redesigned-format component vocabularies are disjoint.
- Filter accounting: PASS - the only read loss is the documented 2004 two-row truncated-fragment event with a note; explicit filters are 59,052 empty wide cells and 3 era-3 legend rows.
- Join accounting: N/A - the transform performs no external joins; district and state rows are materialized from bronze context columns.
- Deduplication accounting: PASS - pre-dedup reconstruction had 72 duplicate-key groups, all in 2004, all metric-identical; final gold removes the duplicate copies without choosing among divergent values.
- Aggregation/unpivot accounting: PASS - eras 1-3 unpivot wide demographic x component cells; eras 4-6 preserve school rows and materialize official district/state rows with a modal `(num_tested, avg_score)` pair vote.

## Reconciliation Checks

- Artifact freshness: PASS - bronze checksum gate passed and manifest/validation are current.
- Contract freshness: PASS - contract matches current gold and has no `_metadata.json` dependency.
- Year coverage: PASS - gold covers every reporting year 2004-2024, with 2016 including both old and redesigned SAT components.
- Row preservation: PASS - school rows in long eras map 1:1; district/state rows trace to official context columns; wide-era blank cells are filtered only when both metrics are null.
- Column coverage: PASS - fact keys, `demographic`, `test_component`, `num_tested`, and `avg_score` all have source lineage; names, national benchmarks, and constant assessment flags are validly excluded.
- Recode accuracy: PASS - component mappings preserve SAT redesign scale differences; `Verbal`/`Reading` pre-redesign sections normalize to `reading`, while redesigned `reading_test_score` remains separate.
- Asian-family demographic recodes (section 5b): PASS - actual wide bronze and the structure report have no Pacific Islander/NHPI label, `rg -i "pacific|hawaiian|nhpi"` found no source bucket, and gold emits `asian_pacific_islander` with no `asian` or `pacific_islander` rows.
- Demographic mutual exclusivity (section 5a - no rollup row alongside split source rows in the same category): PASS - gold has `asian_pacific_islander` only for the Asian-family bucket, with no split Asian or Pacific Islander rows.
- Demographic collision aggregation before dedup (section 5): N/A - each observed wide-era demographic label maps to a distinct canonical key; long eras are all-students only.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - actual Parquet order is `year`, `district_code`, `school_code`, `demographic`, `test_component`, `num_tested`, `avg_score`.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, sections 11/12): PASS - exported fact files contain none of the forbidden columns.
- Canonical column vocabulary (section 16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - assessment count uses canonical `num_tested`; SAT section axis uses `test_component`; no forbidden variants are present.
- Shared categorical utilities applied (section 10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no `grade_level` or `subject` column; demographic normalization uses the shared demographic utility.
- Tidy long format (section 9 - no demographics/years/components as column names): PASS - demographics and SAT components are row values in long format.
- FK keys present in dimension tables (section 13 - `district_code`, `school_code`, `demographic`): PASS - direct checks found 0 unmatched district keys across 193 distinct districts, 0 unmatched composite school keys across 578 schools, and 0 unmatched demographics across 10 values.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - grain and FK descriptors are coherent with the API/validator contract surface.
- Standards compliance (catch-all for sections 1-16 items not enumerated above): PASS - IDs are string-padded, aggregate geography is nulled, suppression markers become nulls, impossible scores are masked, and gold is year-partitioned with no empty files.

## Spot Checks

### Check 1

- Bronze: `sat_scores_recent_2007.xls`, row `SysSchoolID=601:103` / Appling County High School has `Recent TotalA=0`, `Recent VerbalA=0`, `Recent MathA=0`, and `Number TakenA=0`.
- Transform path: `_era23_cells()` + `_melt_wide_demographics()` lines 642-705; `Asian` is remapped through `ASIAN_PI_REMAP`, and zero-count score cells null `avg_score`.
- Gold: `year=2007`, `district_code=601`, `school_code=0103`, `demographic=asian_pacific_islander`, `test_component=verbal_math`, `num_tested=0.0`, `avg_score=NULL`.
- Result: MATCH

### Check 2

- Bronze: `sat_scores_recent_2010.xls`, row `SysSchoolId=722:3052` / Rockdale County High School has impossible averages `Recent Total=3114`, `Recent Total0=2133`, `Recent Verbal0=1039`, `Recent Math0=1094`, `Recent Writing0=981`, with `Number Taken0=219`.
- Transform path: `_null_invalid_sat_scores()` lines 991-1041 applies the component SAT scale mask after geography nulling and before manifest/export.
- Gold: matching all-students component rows preserve `num_tested=219.0` and set `avg_score=NULL` for `verbal_math_writing`, `verbal_math`, `reading`, `mathematics`, and `writing`.
- Result: MATCH

### Check 3

- Bronze: `sat_scores_recent_2013.csv`, William S. Hutchings Career Center row has `SCHOOL_DISTRCT_CD=611`, `INSTN_NUMBER=303`, `TEST_CMPNT_TYP_CD=Reading`, `INSTN_NUM_TESTED_CNT=26`, `INSTN_AVG_SCORE_VAL=429`.
- Transform path: `_transform_long()` lines 831-907 maps school rows directly and zero-pads `INSTN_NUMBER` to `school_code`.
- Gold: `year=2013`, `district_code=611`, `school_code=0303`, `demographic=all`, `test_component=reading`, `num_tested=26.0`, `avg_score=429.0`.
- Result: MATCH

### Check 4

- Bronze: `sat_scores_recent_2024.csv`, `Combined Test Score` state aggregate pairs are `(32976.0, 1043.6)` on 435 school-supported rows and anomalous `(37140.0, 505.4)` on 3 rows with suppressed school metrics.
- Transform path: `_modal_aggregate_rows()` lines 739-828 selects school-supported pairs before modal count and materializes the state row.
- Gold: `year=2024`, state `combined_test_score`, `demographic=all`, `num_tested=32976.0`, `avg_score=1043.6`.
- Result: MATCH

### Check 5

- Bronze: each 2008-2010 `.xls` file contains one legend row with null `SysSchoolId` and explanatory text in `Recent Total`.
- Transform path: `_split_compound_id()` lines 446-454 records and drops the legend row as `era3_legend_row`.
- Gold: manifest records exactly 3 `era3_legend_row` filters; no gold rows have null `year`, null `demographic`, or legend text in metric columns.
- Result: MATCH

## Notes

- No prior `data-review-claude.md` or existing `data-review-codex.md` report was read before forming these findings.
- The transform comments cite one 2004 duplicate example, but the actual source has a broader set of repeated 2004 entity rows. The audit reconstructed 72 duplicate gold-key groups and found all duplicate metrics identical, so this is documentation narrowness rather than a gold accuracy defect.
