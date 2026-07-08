# Data Review: graduation_rate_4_year_cohort

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze, transform, contract, validator, manifest, and gold output reconcile; no must-fix bronze-to-gold accuracy defects were found.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH — bronze freshness gate passed for all 21 files; manifest generated at `2026-06-12T01:35:21.209592+00:00`; validation timestamp `2026-06-12T01:35:21.295177+00:00`, passed `true`.

## Files Reviewed

- Transform: `src/etl/education/gosa/graduation_rate_4_year_cohort/transform.py`
- Contract: `contracts/education/graduation_rate_4_year_cohort.odcs.yaml`
- Bronze files: 21 files, `graduation_rate_4_year_cohort_2004.csv` through `graduation_rate_4_year_cohort_2024.csv`
- Gold files: 63 parquet files, `year=2004` through `year=2024`, with `states.parquet`, `districts.parquet`, and `schools.parquet` in every year
- Manifest: `data/gold/education/graduation_rate_4_year_cohort/_transform_manifest.json`
- Validation report: `data/gold/education/graduation_rate_4_year_cohort/_validation.json`
- Supporting docs: `STATUS.md`, `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `CLAUDE.md`, `AGENTS.md`, `src/etl/education/CLAUDE.md`, and relevant utility modules.

## Contract Verification

- Schema/parquet column match: PASS — gold columns exactly match contract properties: `year`, `district_code`, `school_code`, `demographic`, `graduate_count`, `cohort_size`, `graduation_rate`.
- Column roles and grain: PASS — grain is `year`, `district_code`, `school_code`, `demographic`; actual duplicate grain groups = 0.
- Metric units and derived quality checks: PASS — `graduate_count` and `cohort_size` are `count`; `graduation_rate` is bounded `proportion`; metric ranges are `graduate_count 0..117661`, `cohort_size 0..137710`, `graduation_rate 0.0..1.0`.
- Categorical enums: PASS — contract demographic enum matches actual 18 gold values and manifest `gold_values_produced`.
- Detail levels and layout metadata: PASS — all years have `states`, `districts`, and `schools`; path template and partitioning match current gold layout.
- Foreign-key descriptors: PASS — validation reports all 248 district keys, 2325 composite school keys, and 18 demographic keys resolve.
- Schema hash/version consistency: PASS — contract version is `1.0.0`; schema hash is `ab4fd4139e172bfa89f3b0877a4a57c821a7ab5bfeed23ba27b7cfe2e5ef426c`.

## Validator Verification

- `_validation.json` fresh + passing: PASS — validation timestamp is newer than manifest generated_at and `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS — 20 pass, 0 fail, 1 warning.
- Validator warnings explained: PASS — warnings are expected source-driven null spikes: 2004 enumerates mostly non-cohort schools, and 2012-2016 omit `TOTAL_COUNT`.
- §15b quality-check coverage (cross-column invariants authored): PASS — contract enforces nonnegative/range checks, count <= cohort, rate/count reconciliation excluding the documented 2010 migrant defect, graduate/rate co-suppression, 2012-2016 cohort-size absence, state race/gender partitions, 2011+ reporting threshold, expanded subgroup years, and 2021 English-learner absence.

## Manifest Verification

- Files processed coverage: PASS — manifest processed all 21 current bronze files, matching the checksum-verified inventory.
- Categorical and recode coverage: PASS — `demographic` and `detail_level` have `unmapped_count: 0`; all observed labels are accounted for.
- Row-count reconciliation: PASS — actual gold row count is 242,039, matching manifest `total_gold`; wide-era expansion factors and explicit duplicate removals reconcile.
- Metric stats sanity: PASS — rates are on 0-1 scale; counts are nonnegative; 2012-2016 `cohort_size` is 100% NULL as source-documented.

## Row and Join Accounting

- Bronze file/year disposition: PASS — all source years 2004-2024 are represented in gold.
- Filter accounting: PASS — the one malformed 2004 row lacking a `:` delimiter is filtered; 2004 and 2009 duplicate wide-era twins are deduplicated after value-equivalence checks.
- Join accounting: N/A — the transform does not enrich fact rows through joins; validator confirms dimension FK resolvability.
- Deduplication accounting: PASS — 2004 has 50 duplicate `SysSchoolID` groups and 2009 has 2, all value-identical after casting; gold 2004 row count reconciles as `2270 * 15 - 50 * 15 = 33300`.
- Aggregation/unpivot accounting: PASS — 2004-2010 wide files expand 15 demographic triplets per valid source row; 2011-2024 tidy rows preserve one source row to one gold row.

## Reconciliation Checks

- Artifact freshness: PASS — bronze freshness, manifest, validation, contract, and gold are current.
- Contract freshness: PASS — contract matches parquet schema/order and has no `_metadata.json` dependency.
- Year coverage: PASS — gold covers 21 years, 2004 through 2024.
- Row preservation: PASS — manifest and actual parquet row counts match expected wide expansion, tidy preservation, malformed-row removal, and duplicate-twin dedup.
- Column coverage: PASS — fact keys, demographic, and metrics from the bronze schema classification are mapped; names, grade spans, and report labels are correctly excluded as dimension or non-gold fields.
- Recode accuracy: PASS — demographic labels map semantically, including `Students Without Disability` -> `students_without_disabilities`, `Not Economically Disadv` -> `not_economically_disadvantaged`, and 2018+ `Active Duty`/`Foster`/`Homeless`.
- Asian-family demographic recodes (§5b): PASS — wide-era bare `Asian` is correctly remapped to `asian_pacific_islander`; state race-bucket graduate counts and cohort sizes sum exactly to `all` in every year; no `asian` or `pacific_islander` gold rows are emitted.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): PASS — groups containing `asian_pacific_islander` alongside `asian` or `pacific_islander`: 0.
- Demographic collision aggregation before dedup (§5): N/A — no multiple raw labels in the same source grain collapse into a divergent canonical duplicate.
- Fact-table column order (year → geo → demographic → categoricals → metrics, §1): PASS — actual parquet order is `year`, `district_code`, `school_code`, `demographic`, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS — exported fact files contain only the 7 contract columns.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS — graduation metrics use canonical `graduate_count`, `cohort_size`, and `graduation_rate`.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A — no grade or subject column; demographic normalization uses the shared utility.
- Tidy long format (§9 — no demographics/years/components as column names): PASS — wide-era demographic triplets are unpivoted into the `demographic` axis.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS — independent checks found 0 unmatched districts, 0 unmatched composite school keys, and 0 unmatched demographics.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS — contract grain and FK descriptors match the served star-schema fact table.
- Standards compliance (catch-all for §1–§16 items not enumerated above): PASS — percentage scaling, suppression-to-null from 2007 onward, geography nulling, ID formatting, and metric dtypes all match standards.

## Spot Checks

### Check 1

- Bronze: `graduation_rate_4_year_cohort_2005.csv`, `SysSchoolID=741:201`, Callaway High School: All Students rate/count/cohort = `63.5`, `108`, `170`; Asian rate/count/cohort = `0`, `0`, `1`.
- Transform path: `_transform_wide()` lines 489-548 divides rates by 100, casts counts, splits `SysSchoolID`, zero-pads `school_code`, and maps wide bare Asian to `Asian/Pacific Islander`.
- Gold: `year=2005`, `district_code=741`, `school_code=0201`: `all` = `108`, `170`, `0.635`; `asian_pacific_islander` = `0`, `1`, `0.0`.
- Result: MATCH

### Check 2

- Bronze: `graduation_rate_4_year_cohort_2010.xls`, `SysSchoolID=601:103`: All Students `80.2`, `202`, `252`; Asian fields are `Too few Students`; Black `80.3`, `49`, `61`.
- Transform path: `_transform_wide()` lines 489-548 casts with `strict=False`, turning the suppression string into NULL, then normalizes the demographic.
- Gold: `year=2010`, `district_code=601`, `school_code=0103`: `all` = `202`, `252`, `0.802`; `asian_pacific_islander` all metrics NULL; `black` = `49`, `61`, `0.803`.
- Result: MATCH

### Check 3

- Bronze: `graduation_rate_4_year_cohort_2014.csv`, Appling County district Black: `LONG_SCHOOL_YEAR=2013-14`, `PROGRAM_TOTAL=39`, `PROGRAM_PERCENT=79.6`, no `TOTAL_COUNT` column.
- Transform path: `_transform_tidy()` lines 585-653 detects absent `TOTAL_COUNT` and emits NULL `cohort_size` rather than deriving from rounded rates.
- Gold: `year=2014`, `district_code=601`, `school_code=NULL`, `demographic=black`: `graduate_count=39`, `cohort_size=NULL`, `graduation_rate=0.796`.
- Result: MATCH

### Check 4

- Bronze: raw `graduation_rate_4_year_cohort_2024.csv`, Appling County district rows: All Students `225`, `93.75`, `240`; Black `57`, `91.94`, `62`; Active Duty suppressed to null by the reader.
- Transform path: `_transform_tidy()` lines 654-669 parses ending year, nulls `ALL` school sentinel, casts counts, and divides `PROGRAM_PERCENT` by 100.
- Gold: `year=2024`, `district_code=601`, `school_code=NULL`: `all` = `225`, `240`, `0.9375`; `black` = `57`, `62`, `0.9194`; `active_duty` metrics NULL.
- Result: MATCH

### Check 5

- Bronze: `graduation_rate_4_year_cohort_2010.xls` migrant defect rows: `ALL:ALL` has `65.5`, `110`, `110`; `635:ALL` and `635:1554` have `69.6`, `23`, `23`.
- Transform path: transform docstring lines 60-70 and quality check lines 1108-1130 preserve the individually possible source values while excluding only these documented rows from rate/count reconciliation.
- Gold: 2010 migrant rows preserve `graduation_rate=0.655`, `graduate_count=110`, `cohort_size=110` at state and `0.696`, `23`, `23` for Colquitt district and school.
- Result: MATCH

### Check 6

- Bronze: raw 2024 partial-suppression sample, `district_code=602`, `LABEL_LVL_1_DESC='Grad Rate -Students With Disability'`: `PROGRAM_TOTAL=TFS`, `PROGRAM_PERCENT=TFS`, `TOTAL_COUNT=12`.
- Transform path: `read_bronze_file()` converts `TFS` to NULL; `_transform_tidy()` preserves present `TOTAL_COUNT`.
- Gold: `year=2024`, `district_code=602`, `school_code=NULL`, `demographic=students_with_disabilities`: `graduate_count=NULL`, `cohort_size=12`, `graduation_rate=NULL`.
- Result: MATCH

## Needs Follow-up

- Contract/README wording should be tightened on the 2023-2024 partial-suppression detail level. The transform notes say the 369/339 rows are district-level, but raw and gold checks show 2023 = 74 district + 295 school and 2024 = 68 district + 271 school. This does not change gold values or row coverage, but the emitted metadata should say district and school rows.

## Notes

- `_validation.json` warning details are source-explained and do not indicate a transform defect.
- No prior `data-review-claude.md` or existing `data-review-codex.md` was used to form findings.
