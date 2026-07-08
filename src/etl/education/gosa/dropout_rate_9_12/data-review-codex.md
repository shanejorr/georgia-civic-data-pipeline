# Data Review: dropout_rate_9_12

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Current gold output is fresh, validator-passing, and matches an independent row-by-row reconstruction from all 14 bronze CSV files.

## Summary

- Review date: 2026-06-10
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - manifest generated at `2026-06-10T17:40:37.388344+00:00`, after `transform.py` mtime `2026-06-10T17:39:54.098768+00:00`; validation timestamp `2026-06-10T17:40:37.450811+00:00` is newer than the manifest and reports `passed: true`.

## Files Reviewed

- Transform: `src/etl/education/gosa/dropout_rate_9_12/transform.py`
- Contract: `contracts/education/dropout_rate_9_12.odcs.yaml`
- Bronze files: 14 CSV files, `dropout_rate_9_12_2011.csv` through `dropout_rate_9_12_2024.csv`
- Gold files: 42 parquet files, three detail files (`states.parquet`, `districts.parquet`, `schools.parquet`) for each year 2011-2024
- Manifest: `data/gold/education/dropout_rate_9_12/_transform_manifest.json`
- Validation report: `data/gold/education/dropout_rate_9_12/_validation.json`
- Supporting docs: `docs/codex-review-contract.md`, `docs/contract-creation.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS - all 42 parquet files match contract order: `year`, `district_code`, `school_code`, `demographic`, `dropout_count`, `dropout_rate`.
- Column roles and grain: PASS - contract grain is `year`, `district_code`, `school_code`, `demographic`; `detail_level` is correctly encoded by output filename and absent from parquet.
- Metric units and derived quality checks: PASS - `dropout_count` is `unit: count`; `dropout_rate` is `unit: proportion`; derived non-negative and `[0, 1]` quality checks are present and pass.
- Categorical enums: PASS - `demographic` contract enum matches manifest and actual gold distinct values.
- Detail levels and layout metadata: PASS - contract lists `schools`, `districts`, `states`, path template `education/dropout_rate_9_12/year={year}/{detail}.parquet`, and local/S3 servers.
- Foreign-key descriptors: PASS - contract declares `district_code -> districts`, composite `district_code + school_code -> schools`, and `demographic -> demographics`.
- Schema hash/version consistency: PASS - contract version is `1.0.0`; schema hash is `3fc2466c7ccb0dbe743f50879e78d5cf39c1f6c2494810b608855754f0551466`; year range is 2011-2024 with no gaps.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp is newer than the manifest and `passed` is `true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 21 checks passed, 0 failed, 0 warnings; contract quality SQL reports all 12 checks passing.
- Validator warnings explained: N/A - validation has no warnings.
- Section 15b quality-check coverage (cross-column invariants authored): PASS - contract enforces co-suppression, state rows non-null, count threshold, state race/gender/economic/disability partition sums, and the 2020-2022 English-learner absence rule.

## Manifest Verification

- Files processed coverage: PASS - manifest lists all 14 current bronze CSV files; official freshness gate reports all checksums match and no unanalyzed files.
- Categorical and recode coverage: PASS - `demographic` and `detail_level` mappings have `unmapped_count: 0`; manifest values match actual bronze labels and gold distinct values.
- Row-count reconciliation: PASS - manifest `total_bronze` and `total_gold` are both 143,634; every year has expansion factor 1.0 and filtered count 0.
- Metric stats sanity: PASS - final gold stats show `dropout_count` min 10 and max 21,500; `dropout_rate` min 0.002 and max 0.936 on the 0-1 scale; count/rate null counts match exactly by year.

## Row and Join Accounting

- Bronze file/year disposition: PASS - every current bronze file from 2011-2024 is processed once and mapped to the same ending school year as `LONG_SCHOOL_YEAR`.
- Filter accounting: N/A - no rows are filtered; all 143,634 bronze rows are preserved.
- Join accounting: N/A - transform performs no data joins or lookups; validator FK checks confirm downstream dimension joins resolve.
- Deduplication accounting: PASS - independent checks found 0 duplicate natural-key groups in expected bronze-shaped rows and 0 in actual gold; `assert_no_natural_key_collisions()` precedes `deduplicate_by_detail_level()`.
- Aggregation/unpivot accounting: N/A - no aggregation, rollup synthesis, or unpivoting occurs. The only shape repair is the 2022 reclassification of 28 `School`-labeled aggregate rows with `INSTN_NUMBER=ALL` to district output.

## Reconciliation Checks

- Artifact freshness: PASS - manifest, contract, validation, bronze inventory, and gold parquet are mutually current.
- Contract freshness: PASS - contract was emitted at `2026-06-10T17:40:37.431449+00:00` from current transform/gold; no `_metadata.json` dependency.
- Year coverage: PASS - bronze, manifest, contract, and gold all cover 2011-2024.
- Row preservation: PASS - independent reconstruction from all bronze rows produced 143,634 expected rows; gold has 143,634 rows; missing actual rows: 0; extra gold rows: 0; value mismatches: 0.
- Column coverage: PASS - fact keys and metrics from `LONG_SCHOOL_YEAR`, `SCHOOL_DSTRCT_CD`, `INSTN_NUMBER`, `LABEL_LVL_1_DESC`, `PROGRAM_TOTAL`, and `PROGRAM_PERCENT` are represented; name and grade-served fields are validly excluded as dimensions/metadata.
- Recode accuracy: PASS - `State`, `District`, `School` map to detail files; all 15 demographic labels map to the expected canonical keys, with 14-label source years in 2020-2022 accurately reflected.
- Asian-family demographic recodes (section 5b): PASS - bronze publishes explicit `Asian/Pacific Islander`; gold emits `asian_pacific_islander`, emits 0 `asian` rows, emits 0 `pacific_islander` rows, and state race-bucket counts sum exactly to `all` for every year 2011-2024.
- Demographic mutual exclusivity (section 5a - no rollup row alongside split source rows in the same category): PASS - no natural-key group contains `asian_pacific_islander` alongside `asian` or `pacific_islander`; source uses a single combined race bucket.
- Demographic collision aggregation before dedup (section 5): N/A - observed 15 source labels map to 15 distinct canonical keys; no alias collision is present.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - parquet order is `year`, `district_code`, `school_code`, `demographic`, `dropout_count`, `dropout_rate`.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, sections 11/12): PASS - no forbidden fact-table columns are present.
- Canonical column vocabulary (section 16): PASS - metric names use `dropout_count` and `dropout_rate`; no `_pct` suffix or forbidden variant appears.
- Shared categorical utilities applied (section 10a): PASS - demographic normalization uses `normalize_demographic_column`; no grade or subject column exists.
- Tidy long format (section 9 - no demographics/years/components as column names): PASS - demographic is a row value, not a wide column family.
- FK keys present in dimension tables (section 13): PASS - 241 district keys, 619 composite school keys, and 15 demographic keys all resolve; unmatched counts are 0.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - contract exposes `demographic` as a categorical/filter key and all FK metadata needed for API/MCP joins.
- Standards compliance (catch-all for sections 1-16 items not enumerated above): PASS - IDs are strings with zero padding preserved, suppression markers become null, rates are on 0-1 scale, and gold is year-partitioned with no empty files.

## Spot Checks

### Check 1

- Bronze: `dropout_rate_9_12_2024.csv`, state `ALL Students`, `PROGRAM_TOTAL=16616`, `PROGRAM_PERCENT=2.8`
- Transform path: `transform.py:381-440` parses year, nulls aggregate geography, maps demographic, casts count, and divides percent by 100
- Gold: `year=2024/states.parquet`, `district_code=NULL`, `school_code=NULL`, `demographic=all`, `dropout_count=16616`, `dropout_rate=0.028`
- Result: MATCH

### Check 2

- Bronze: `dropout_rate_9_12_2024.csv`, state `Asian/Pacific Islander`, `PROGRAM_TOTAL=238`, `PROGRAM_PERCENT=.8`
- Transform path: `transform.py:315-345` normalizes demographic; `transform.py:436-437` casts metrics and scales rate
- Gold: `year=2024/states.parquet`, `demographic=asian_pacific_islander`, `dropout_count=238`, `dropout_rate=0.008`
- Result: MATCH

### Check 3

- Bronze: `dropout_rate_9_12_2011.csv`, district `667`, school `0189`, `Economically Disadvantaged`, `PROGRAM_TOTAL=152`, `PROGRAM_PERCENT=33`
- Transform path: `transform.py:381-440` maps school-year 2010-11 to `year=2011`, preserves zero-padded school code, maps demographic, and scales rate
- Gold: `year=2011/schools.parquet`, `district_code=667`, `school_code=0189`, `demographic=economically_disadvantaged`, `dropout_count=152`, `dropout_rate=0.33`
- Result: MATCH

### Check 4

- Bronze: `dropout_rate_9_12_2024.csv`, district `601`, `ALL Students`, `PROGRAM_TOTAL=TFS`, `PROGRAM_PERCENT=TFS`
- Transform path: `transform.py:364-371` reads suppression-aware bronze; `transform.py:436-437` casts suppressed metrics to null
- Gold: `year=2024/districts.parquet`, `district_code=601`, `school_code=NULL`, `demographic=all`, `dropout_count=NULL`, `dropout_rate=NULL`
- Result: MATCH

### Check 5

- Bronze: `dropout_rate_9_12_2022.csv`, source row has `DETAIL_LVL_DESC=School`, `SCHOOL_DSTRCT_CD=7830627`, `INSTN_NUMBER=ALL`, `ALL Students`, both metrics `TFS`
- Transform path: `transform.py:274-312` reclassifies `School` rows with the aggregate `INSTN_NUMBER=ALL` sentinel to district detail
- Gold: `year=2022/districts.parquet`, `district_code=7830627`, `school_code=NULL`, `demographic=all`, `dropout_count=NULL`, `dropout_rate=NULL`
- Result: MATCH

## Notes

- No prior `data-review-claude.md` or existing `data-review-codex.md` content was read before this report was written.
- Formula-level aggregation trace is not applicable: this transform is row-preserving and does not collapse multiple bronze rows into one gold row. The formula-level metric check here is the all-row rate scaling comparison (`PROGRAM_PERCENT / 100 = dropout_rate`) and count casting comparison.
- The review did not re-run the transform or standalone validator because those commands rewrite runtime artifacts; the current `_validation.json` was inspected as the passing output of the latest transform run.
