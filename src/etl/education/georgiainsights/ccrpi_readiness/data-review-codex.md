# Data Review: ccrpi_readiness

## Verdict

**Status**: NEEDS FIXES
**Must-fix count**: 1

Summary: bronze, manifest, contract, validator, and gold are fresh and row-preserving, but one sub_indicator recode incorrectly collapses pre-2025 `ACT/SAT/AP/IB` rows into the 2025 `ACT/SAT/AP/IB/Cambridge` category.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze checksums pass for all 7 files; transform mtime `2026-06-12T13:57:38Z` is older than manifest `2026-06-12T14:00:05Z`; validation timestamp `2026-06-12T14:00:06Z` is newer than the manifest and reports `passed: true`.

## Files Reviewed

- Transform: `src/etl/education/georgiainsights/ccrpi_readiness/transform.py`
- Contract: `contracts/education/ccrpi_readiness.odcs.yaml`
- Bronze files: 7 xlsx files for 2018, 2019, 2021, 2022, 2023, 2024, and 2025 under `data/bronze/education/georgiainsights/ccrpi_readiness/`
- Gold files: 21 parquet files under `data/gold/education/ccrpi_readiness/year=*/{schools,districts,states}.parquet`
- Manifest: `data/gold/education/ccrpi_readiness/_transform_manifest.json`
- Validation report: `data/gold/education/ccrpi_readiness/_validation.json`
- Supporting docs: `docs/codex-review-contract.md`, `docs/contract-creation.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS - contract properties exactly match parquet columns: `year`, `district_code`, `school_code`, `demographic`, `grade_cluster`, `indicator`, `sub_indicator`, `indicator_score`, `unbenchmarked_rate`.
- Column roles and grain: PASS - roles and primary-key positions match the transform declaration and the actual natural key.
- Metric units and derived quality checks: PASS - `indicator_score` is `unit: score` with 0-100 bounds; `unbenchmarked_rate` is `unit: proportion` with a generated 0-1 check.
- Categorical enums: FAIL - enums match current gold, but the current gold includes an inaccurate merged `sub_indicator` value for pre-2025 `ACT/SAT/AP/IB` rows.
- Detail levels and layout metadata: PASS - `schools`, `districts`, and `states` exist for each produced year; 2020 is correctly absent.
- Foreign-key descriptors: PASS - contract declares district, composite school, and demographic FKs; validator reports all populated keys resolve.
- Schema hash/version consistency: PASS - contract `version: 1.0.0`, schema hash `2341973aebcc7a2615c1f0438e40a389301d20edc5271389cbb0d093e7503d6d`, and available years match the current gold layout.

## Validator Verification

- `_validation.json` fresh + passing: PASS - timestamp `2026-06-12T14:00:06.099182+00:00`, manifest `generated_at` `2026-06-12T14:00:05.884363+00:00`, `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 21 pass, 0 fail, 0 warning; contract schema, grain uniqueness, 18 quality SQL checks, FK integrity, vocabulary, and geography nulling all pass.
- Validator warnings explained: N/A - no validator warnings.
- §15b quality-check coverage (cross-column invariants authored): PASS - contract includes checks for era-specific sub_indicator/rate structure, 2021-2023 AE-only rate population, 2024-2025 rate-score mirroring, high-school-only indicators, Beyond the Core cluster scope, 2022 partial reporting, indicator rename era boundary, and sub_indicator parent nesting.

## Manifest Verification

- Files processed coverage: PASS - manifest includes all 7 current bronze files and expected eras.
- Categorical and recode coverage: FAIL - `unmapped_count` is 0 for every categorical, but the `sub_indicator` map semantically over-collapses `READINESS SCORE ON THE ACT, SAT, AP OR IB` and `ACT/SAT/AP/IB` to `act_sat_ap_ib_cambridge`.
- Row-count reconciliation: PASS - manifest total bronze and gold are both 1,611,990; every year has expansion factor 1.0 and zero filtered rows.
- Metric stats sanity: PASS - `indicator_score` range is 0-100; `unbenchmarked_rate` range is 0-1; null patterns match era structure.

## Row and Join Accounting

- Bronze file/year disposition: PASS - all current bronze files are processed; expected year gap is only 2020.
- Filter accounting: PASS - no rows are filtered; raw bronze detail-level counts match exported parquet counts by year and detail level.
- Join accounting: N/A - the transform performs no joins or lookup merges.
- Deduplication accounting: PASS - raw duplicate-key groups are 0 for every source year; gold duplicate natural-key groups are 0.
- Aggregation/unpivot accounting: N/A - the transform preserves the source row grain with no unpivot, rollup, or aggregation.

## Reconciliation Checks

- Artifact freshness: PASS - `scripts/check_bronze_freshness.py education georgiainsights ccrpi_readiness` passes; validation is fresh relative to the manifest.
- Contract freshness: PASS - contract was emitted from the current transform/gold path and there is no `_metadata.json` dependency.
- Year coverage: PASS - gold years are 2018, 2019, 2021, 2022, 2023, 2024, and 2025; 2020 is absent because CCRPI was waived.
- Row preservation: PASS - raw and gold counts match exactly by year and by detail level.
- Column coverage: PASS - all fact keys, categoricals, and metrics classified in the bronze structure doc are represented or deliberately excluded as dimension attributes (`System Name`, `School Name`, `Grade Configuration`).
- Recode accuracy: FAIL - one sub_indicator recode changes the source category meaning by adding Cambridge to pre-2025 College and Career Readiness rows.
- Asian-family demographic recodes (§5b): PASS - bronze publishes explicit `Asian/Pacific Islander` and never separate Asian or Pacific Islander rows; gold emits `asian_pacific_islander` and no split `asian`/`pacific_islander` keys.
- Demographic mutual exclusivity (§5a - no rollup row alongside split source rows in the same category): PASS - race values are `asian_pacific_islander`, `black`, `hispanic`, `multiracial`, `native_american`, and `white`; no split Asian/Pacific Islander convention is mixed in.
- Demographic collision aggregation before dedup (§5): N/A - observed reporting labels map 1:1 to canonical demographic keys aside from the American Indian label rename, which maps consistently to `native_american`.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS - actual parquet order is `year`, `district_code`, `school_code`, `demographic`, `grade_cluster`, `indicator`, `sub_indicator`, `indicator_score`, `unbenchmarked_rate`.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS - exported parquet excludes `detail_level`, names, grade configuration, and crosswalk IDs.
- Canonical column vocabulary (§16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - CCRPI score column uses `indicator_score`; rate column uses `unbenchmarked_rate`; no forbidden variants found by validation.
- Shared categorical utilities applied (§10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no `grade_level` or `subject` column; demographics use `normalize_demographic_column`.
- Tidy long format (§9 - no demographics/years/components as column names): PASS - indicator and sub_indicator are row values, not metric-column families.
- FK keys present in dimension tables (§13 - `district_code`, `school_code`, `demographic`): PASS - validator reports all 243 district keys, 2,407 composite school keys, and 10 demographic keys resolve.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): FAIL - the contract currently exposes the inaccurate pre-2025 `ACT/SAT/AP/IB` rows under the `act_sat_ap_ib_cambridge` filter value.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS - no additional standards-driven accuracy defects found.

## Spot Checks

### Check 1

- Bronze: 2019 file, City Schools of Decatur / Clairemont Elementary School, `Grade Cluster=E`, `Reporting Label=White`, `Indicator=Beyond The Core`, `Indicator Score=100`.
- Transform path: `_transform_era_1` maps IDs, demographic, grade cluster, indicator, and casts `indicator_score`; Era 1 sets `sub_indicator` and `unbenchmarked_rate` to NULL.
- Gold: `year=2019`, `district_code=773`, `school_code=0505`, `demographic=white`, `grade_cluster=elementary`, `indicator=beyond_the_core`, `sub_indicator=NULL`, `indicator_score=100.0`, `unbenchmarked_rate=NULL`.
- Result: MATCH

### Check 2

- Bronze: 2024 file, Paulding County / North Paulding High School, `Grade Cluster=H`, `Reporting Label=English Learners`, `Indicator=College and Career Readiness`, `Sub-Indicator=ASVAB`, `Unbenchmarked Rate=0`, `Indicator Score=0`.
- Transform path: `_transform_era_2` maps `ASVAB -> asvab`, casts score, and divides unbenchmarked rate by 100.
- Gold: `year=2024`, `district_code=710`, `school_code=0109`, `demographic=english_learners`, `grade_cluster=high`, `indicator=college_and_career_readiness`, `sub_indicator=asvab`, `indicator_score=0.0`, `unbenchmarked_rate=0.0`.
- Result: MATCH

### Check 3

- Bronze: 2024 file, Ware County district aggregate, `Reporting Label=Asian/Pacific Islander`, `Indicator=At or Above Grade-Level Reading`, `Sub-Indicator=All`, both metric cells `TFS`.
- Transform path: `_apply_detail_level_and_ids` nulls aggregate `school_code`, `_normalize_demographic` maps to `asian_pacific_islander`, `_transform_era_2` casts suppressed metrics to NULL.
- Gold: `year=2024`, `district_code=748`, `school_code=NULL`, `demographic=asian_pacific_islander`, `grade_cluster=high`, `indicator=at_or_above_grade_level_reading`, `sub_indicator=all`, `indicator_score=NULL`, `unbenchmarked_rate=NULL`.
- Result: MATCH

### Check 4

- Bronze: 2024 state aggregate, `College and Career Readiness`, `Sub-Indicator=ACT/SAT/AP/IB`, `Indicator Score=22.28`.
- Transform path: `SUB_INDICATOR_MAP` maps `ACT/SAT/AP/IB` to `act_sat_ap_ib_cambridge`.
- Gold: same row has `sub_indicator=act_sat_ap_ib_cambridge`, `indicator_score=22.28`, `unbenchmarked_rate=0.2228`.
- Result: MISMATCH

## Required Fixes

### Fix 1: Split pre-2025 ACT/SAT/AP/IB from ACT/SAT/AP/IB/Cambridge

- **Severity**: HIGH
- **Issue**: The transform maps 2021, 2023, and 2024 College and Career Readiness `ACT/SAT/AP/IB` rows into `act_sat_ap_ib_cambridge`, adding Cambridge to rows whose bronze label does not include Cambridge. This changes the published sub_indicator meaning and makes the API filter value inaccurate for pre-2025 data.
- **Evidence**: Bronze 2021 state row has `Sub-Indicator = Readiness score on the ACT, SAT, AP or IB`, bronze 2024 state row has `Sub-Indicator = ACT/SAT/AP/IB`, and bronze 2025 state row has `Sub-Indicator = ACT/SAT/AP/IB/Cambridge`. Current gold maps all three to `sub_indicator = act_sat_ap_ib_cambridge`; for example, the 2024 state/all/high/College and Career Readiness row with bronze `ACT/SAT/AP/IB` and score `22.28` appears in gold as `act_sat_ap_ib_cambridge`.
- **Location**: `src/etl/education/georgiainsights/ccrpi_readiness/transform.py:241-243`
- **Suggested fix**: Add a distinct canonical value such as `act_sat_ap_ib` for `READINESS SCORE ON THE ACT, SAT, AP OR IB` and `ACT/SAT/AP/IB`, keep only `ACT/SAT/AP/IB/CAMBRIDGE` mapped to `act_sat_ap_ib_cambridge`, and re-emit the contract so the `sub_indicator` enum and `sub_indicator_nests_under_parent` quality check include both valid College and Career Readiness sub-indicators.

## Notes

- No broader row-loss, join, duplicate, suppression, geography-nulling, metric-scale, FK, or demographic-exclusivity defects were found.
- The review did not read any prior `data-review-claude.md` or `data-review-codex.md` before writing this report.
