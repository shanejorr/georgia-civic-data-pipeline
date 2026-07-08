# Data Review: hope_eligible_graduates

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Current gold output is fresh, validator-passing, and reconciles to the 21 bronze files with the documented 2004 and 2008 aggregation/merge exceptions.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH — `scripts/check_bronze_freshness.py education gosa hope_eligible_graduates` passed for all 21 files; manifest generated at `2026-06-12T02:26:29.256814+00:00`; validation generated at `2026-06-12T02:26:29.319111+00:00`.

## Files Reviewed

- Transform: `src/etl/education/gosa/hope_eligible_graduates/transform.py`
- Contract: `contracts/education/hope_eligible_graduates.odcs.yaml`
- Bronze files: 21 files, `hope_eligible_graduates_2004.csv` through `hope_eligible_graduates_2024.csv`
- Gold files: 63 parquet files, `year=2004` through `year=2024`, each with `schools.parquet`, `districts.parquet`, and `states.parquet`
- Manifest: `data/gold/education/hope_eligible_graduates/_transform_manifest.json`
- Validation report: `data/gold/education/hope_eligible_graduates/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `data/bronze/education/gosa/hope_eligible_graduates/bronze-data-structure.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `src/etl/education/CLAUDE.md`, `AGENTS.md`, `CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS — validator checked all 63 parquet files; actual columns are `year`, `district_code`, `school_code`, `graduate_count`, `hope_eligible_count`, `hope_eligible_rate`, matching contract order.
- Column roles and grain: PASS — contract grain is `year`, `district_code`, `school_code`; transform `NATURAL_KEYS` matches; no duplicate gold grain tuples found.
- Metric units and derived quality checks: PASS — count metrics are `unit: count`; `hope_eligible_rate` is `unit: proportion`; contract enforces non-negative counts, rate in `[0, 1]`, eligible count not exceeding graduates, rate/count reconciliation, suppression co-null structure, and exactly one state row per year.
- Categorical enums: PASS — only runtime categorical is `detail_level`, which is exported as filenames; manifest maps `STATE/DISTRICT/SCHOOL` to `state/district/school` with `unmapped_count: 0`.
- Detail levels and layout metadata: PASS — contract lists `schools`, `districts`, `states`; gold has exactly those files for every year.
- Foreign-key descriptors: PASS — contract describes `district_code -> districts` and composite `school_code -> schools`; validator reports all 203 district keys and all 623 school keys resolve.
- Schema hash/version consistency: PASS — contract `version: 1.0.0`, `year_range: 2004-2024`, and schema hash `9e0a478cd9c2089ec4bd5fd9e951cbbc796901bda917559f97cae6f40e3e85ef` are coherent with current gold layout.

## Validator Verification

- `_validation.json` fresh + passing: PASS — validation timestamp is later than manifest timestamp and `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS — 21 checks passed, 0 failed, 0 warnings.
- Validator warnings explained: N/A — validation reported no warnings.
- §15b quality-check coverage (cross-column invariants authored): PASS — authored SQL covers non-empty output, metric ranges, eligible <= graduates, rate formula tolerance, suppression co-null behavior, and one state row per year.

## Manifest Verification

- Files processed coverage: PASS — manifest records all 21 bronze files and all expected years 2004-2024.
- Categorical and recode coverage: PASS — `detail_level` recode saw all three expected bronze values and no unmapped values.
- Row-count reconciliation: PASS — manifest `total_bronze: 12432`, `total_gold: 12771`; expansion is explained by 2004 derived district rows and 2008 derived district/state rows, with 11 explicitly recorded merge/drop dispositions.
- Metric stats sanity: PASS — counts are non-negative, rates are 0-1, eligible never exceeds graduates, and rate reconciliation over gold has 0 rows over the 0.005 tolerance.

## Row and Join Accounting

- Bronze file/year disposition: PASS — every bronze file is processed exactly once; filename/in-file school-year checks are implemented for `LONG_SCHOOL_YEAR` files.
- Filter accounting: PASS — 2004 drops 1 junk footer row and sums 8 trailing-`x` subtally rows; 2008 drops 1 fully orphaned null-ID row and sums 1 duplicate school-key pair. These 11 explicit dispositions are recorded in the manifest.
- Join accounting: N/A — the transform performs no enrichment joins; FK validation against dimensions passes after export.
- Deduplication accounting: PASS — era-specific duplicate groups are summed before the global collision guard; post-transform gold has 0 duplicate natural-key tuples.
- Aggregation/unpivot accounting: PASS — no wide-to-long unpivot is needed; 2004 district aggregates and 2008 district/state aggregates recompute `sum(eligible) / sum(graduates)` and reconcile to tested examples.

## Reconciliation Checks

- Artifact freshness: PASS — bronze checksums match the structure report; manifest, contract, validation, and parquet are from the current successful transform run.
- Contract freshness: PASS — contract is emitted by `write_data_dictionary()` from transform lines 884-1005 and validation confirms parquet schema match; no `_metadata.json` dependency.
- Year coverage: PASS — gold years are exactly 2004-2024.
- Row preservation: PASS — direct years preserve bronze row counts; row-changing years reconcile: 2004 `348 -> 513` via footer drop, 8 merges, and 174 derived districts; 2008 `382 -> 556` via 376 school rows, 179 derived districts, 1 derived state, 4 folded null-school rows, 1 orphan exclusion, and 1 duplicate-key merge.
- Column coverage: PASS — fact keys and metrics in the bronze structure report are represented; names, report labels, in-file year labels, and composite raw IDs are validly excluded or split.
- Recode accuracy: PASS — geography sentinel nulling, 4-digit school-code padding, 3-digit district-code padding, and 0-100 to 0-1 rate scaling match bronze and standards.
- Asian-family demographic recodes (§5b): N/A — the topic has no demographic breakdowns.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): N/A — no demographic column.
- Demographic collision aggregation before dedup (§5): N/A — no demographic column.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS — parquet order is `year`, `district_code`, `school_code`, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS — parquet has no forbidden columns; `detail_level` is encoded by filename.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS — `graduate_count`, `hope_eligible_count`, and `hope_eligible_rate` are semantically clear; no redundant `_pct` column is emitted.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A — no grade or subject column.
- Tidy long format (§9 — no demographics/years/components as column names): PASS — one observation per year/geography row; no year or category values are encoded as columns.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS — direct checks found 0 unmatched district keys and 0 unmatched composite school keys.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS — row grain is natural-key based; no user-facing categoricals beyond geography; FK descriptors match dimensions.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS — IDs remain strings with leading zeros, rates are proportions, suppression markers are null, and aggregate geography nulling is correct for all files.

## Spot Checks

### Check 1

- Bronze: `data/bronze/education/gosa/hope_eligible_graduates/hope_eligible_graduates_2024.csv`, Ware County High School row: `SCHOOL_DISTRCT_CD=748`, `INSTN_NUMBER=0195`, `NUMBER_OF_GRADUATES=335`, `HOPE_ELIGIBLE=170`, `HOPE_ELIGIBLE_PCT=50.75`.
- Transform path: `_transform_era1()` lines 412-441; `DETAIL_LVL_DESC` recode, geography formatting, metric casting, and percent division by 100.
- Gold: `data/gold/education/hope_eligible_graduates/year=2024/schools.parquet`, `district_code=748`, `school_code=0195`, `graduate_count=335`, `hope_eligible_count=170`, `hope_eligible_rate=0.5075`.
- Result: MATCH

### Check 2

- Bronze: `data/bronze/education/gosa/hope_eligible_graduates/hope_eligible_graduates_2010.xls`, `Sysschoolid=ALL:ALL`, `Number of Graduates=89851`, `Number Eligible=34285`, `Percent Eligible=38.2`.
- Transform path: `_transform_era3()` lines 478-485 via `_transform_composite_key_era()` lines 457-475; `ALL:ALL` becomes state-level NULL geography and rate is divided by 100.
- Gold: `data/gold/education/hope_eligible_graduates/year=2010/states.parquet`, `district_code=NULL`, `school_code=NULL`, `graduate_count=89851`, `hope_eligible_count=34285`, `hope_eligible_rate=0.382`.
- Result: MATCH

### Check 3

- Bronze: `data/bronze/education/gosa/hope_eligible_graduates/hope_eligible_graduates_2004.csv`, duplicate/subtally pair `622:2052` and `622:2052x`: graduates `181 + 176`, eligible `112 + 113`.
- Transform path: `_transform_era7_2004_2005()` lines 647-736; strips trailing `x`, groups duplicate natural keys, sums counts, and recomputes rate only for merged groups.
- Gold: `data/gold/education/hope_eligible_graduates/year=2004/schools.parquet`, `district_code=622`, `school_code=2052`, `graduate_count=357`, `hope_eligible_count=225`, `hope_eligible_rate=0.630252`.
- Result: MATCH

### Check 4

- Bronze: `data/bronze/education/gosa/hope_eligible_graduates/hope_eligible_graduates_2008.xls`, five null-school rows: four valid-district rows total 226 graduates / 42 eligible; one fully orphaned Renaissance Academy row has 28 graduates / 0 eligible and is excluded by the bronze state sheet.
- Transform path: `_transform_era4_2008()` lines 488-624; valid-district null-school rows are folded into district/state aggregates only; orphan row is manifest-recorded as excluded; district/state aggregates are derived from school rows plus the fold rows.
- Gold: `data/gold/education/hope_eligible_graduates/year=2008/states.parquet` has `graduate_count=81569`, `hope_eligible_count=31443`, `hope_eligible_rate=0.385477`; school-level sums are 81343 / 31401 and district-level sums are 81569 / 31443.
- Result: MATCH

### Check 5

- Bronze: `data/bronze/education/gosa/hope_eligible_graduates/hope_eligible_graduates_2008.xls`, duplicate key `721/2574`: Westside High School `241/61` plus Westside Comprehensive High School `140/30`.
- Transform path: `_transform_era4_2008()` lines 573-604; duplicate school key group is summed and rate is recomputed as `91 / 381`.
- Gold: `data/gold/education/hope_eligible_graduates/year=2008/schools.parquet`, `district_code=721`, `school_code=2574`, `graduate_count=381`, `hope_eligible_count=91`, `hope_eligible_rate=0.238845`.
- Result: MATCH

## Notes

- I did not read any prior `data-review-claude.md` or `data-review-codex.md` before completing the independent review.
- No required fixes were identified.
