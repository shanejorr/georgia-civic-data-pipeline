# Data Review: enrollment_by_grade_level

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: bronze-to-gold row reconstruction matched the current gold output exactly after the documented 52-row 2022 sentinel-twin exclusion; no must-fix accuracy defects were found.

## Summary

- Review date: 2026-06-11
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze freshness gate passed with all 14 checksums matching and no unanalyzed files; transform mtime was before manifest generation, and `_validation.json` timestamp `2026-06-11T22:26:21.304413+00:00` is newer than manifest `generated_at` `2026-06-11T22:26:21.225836+00:00`.

## Files Reviewed

- Transform: `src/etl/education/gosa/enrollment_by_grade_level/transform.py`
- Contract: `contracts/education/enrollment_by_grade_level.odcs.yaml`
- Bronze files: 14 CSVs, `enrollment_by_grade_level_2011.csv` through `enrollment_by_grade_level_2024.csv`
- Gold files: 42 parquet files, 14 year partitions with `schools.parquet`, `districts.parquet`, and `states.parquet`
- Manifest: `data/gold/education/enrollment_by_grade_level/_transform_manifest.json`
- Validation report: `data/gold/education/enrollment_by_grade_level/_validation.json`
- Supporting docs: `docs/codex-review-contract.md`, `docs/contract-creation.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `data/bronze/education/gosa/enrollment_by_grade_level/bronze-data-structure.md`, `src/etl/education/CLAUDE.md`, `CLAUDE.md`, `STATUS.md`

## Contract Verification

- Schema/parquet column match: PASS - every one of 42 parquet files has exactly `year`, `district_code`, `school_code`, `enrollment_period`, `grade_level`, `student_count`, matching contract order.
- Column roles and grain: PASS - roles are `year`, `fk_district`, `fk_school`, `categorical`, `categorical`, and `metric`; grain is `year`, `district_code`, `school_code`, `enrollment_period`, `grade_level`, with geography NULLs at higher detail levels.
- Metric units and derived quality checks: PASS - `student_count` is `unit: count`; contract SQL includes `student_count_non_negative`.
- Categorical enums: PASS - contract enums match manifest and gold distincts: `enrollment_period={fall,spring}` and `grade_level={k,01..12}`.
- Detail levels and layout metadata: PASS - contract lists `schools`, `districts`, `states`, default `schools`, partition column `year`, and path template `education/enrollment_by_grade_level/year={year}/{detail}.parquet`.
- Foreign-key descriptors: PASS - `district_code` targets districts; `school_code` targets composite `(district_code, school_code)` schools.
- Schema hash/version consistency: PASS - contract `version: 1.0.0`, `year_range: 2011-2024`, `schema_hash: 530491b07bc53621ba83aed23c6031b4a7e6bc607c3d2b98ecaaeeacab0351cd`; current parquet layout matches.

## Validator Verification

- `_validation.json` fresh + passing: PASS - `passed: true`, timestamp newer than the manifest.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 20 pass, 0 fail; schema, grain uniqueness, contract quality SQL, foreign keys, canonical vocabulary, and geography nulling all passed.
- Validator warnings explained: PASS - null-rate warnings for `student_count` in 2021 and 2022 match the documented TFS rollout, where suppressed counts replace zeros and 1-9 values.
- Section 15b quality-check coverage (cross-column invariants authored): PASS - no partition-sum, co-null, or component-total invariant applies; authored checks cover non-empty data, categorical domains, non-negative count, state row shape, dense-era 13-grade groups, pre-2021 non-null counts, and ID lengths.

## Manifest Verification

- Files processed coverage: PASS - manifest processed all 14 current bronze CSVs, years 2011-2024, matching the bronze inventory and checksum gate.
- Categorical and recode coverage: PASS - `enrollment_period` maps `Fall -> fall`, `Spring -> spring`; `grade_level` maps `K -> k` and `1st..12th -> 01..12`; both have `unmapped_count: 0`.
- Row-count reconciliation: PASS - manifest total bronze 831,369, total gold 831,317, total filtered 52; the only loss is explicit `school_all_sentinel_twin_of_school_coded_row` in 2022.
- Metric stats sanity: PASS - `student_count` is non-negative, min is 0 in unsuppressed years and 10 in TFS/sparse years, max values trace to state aggregate rows, and null spikes align with the source suppression regime.

## Row and Join Accounting

- Bronze file/year disposition: PASS - every current bronze CSV is processed once; filename years match the single `LONG_SCHOOL_YEAR` value in each file.
- Filter accounting: PASS - exactly 52 rows are filtered, all in 2022, all `DETAIL_LVL_DESC='School'` with `INSTN_NUMBER='ALL'`; each duplicates a school-coded row for districts `7830627` or `7830636`, and neither district has district-level rows in that file.
- Join accounting: N/A - the transform performs no enrichment joins. Dimension FK checks were audited separately: 245 district keys and 2,604 school composite keys have zero missing dimension matches.
- Deduplication accounting: PASS - natural-key duplicate groups are zero in the reconstructed expected data and zero in gold; `deduplicate_by_detail_level` removed no rows beyond the explicit 2022 sentinel-twin filter.
- Aggregation/unpivot accounting: N/A - there is no aggregation, rollup derivation, weighted average, or unpivot; one eligible bronze row becomes one gold row with direct key recodes and direct count casting.

## Reconciliation Checks

- Artifact freshness: PASS - bronze freshness gate passed; manifest, contract, gold, and validation were regenerated together on 2026-06-11.
- Contract freshness: PASS - contract is emitted from the current transform/gold and has no `_metadata.json` dependency.
- Year coverage: PASS - gold has continuous years 2011-2024 and no unexpected years.
- Row preservation: PASS - independent bronze-to-gold row reconstruction produced 831,317 expected rows and compared to 831,317 gold rows with 0 mismatched row signatures.
- Column coverage: PASS - fact keys (`LONG_SCHOOL_YEAR`, `SCHOOL_DSTRCT_CD`, `INSTN_NUMBER`), fact categoricals (`ENROLLMENT_PERIOD`, `GRADE_LEVEL`), and fact metric (`ENROLLMENT_COUNT`) are carried; `#RPT_NAME`, names, and `GRADES_SERVED_DESC` are valid non-gold/dimension fields.
- Recode accuracy: PASS - period, grade, sentinel geography, and count casts match bronze semantics.
- Asian-family demographic recodes (section 5b): N/A - no demographic or race column is present.
- Demographic mutual exclusivity (section 5a - no rollup row alongside split source rows in the same category): N/A - no demographic column is present.
- Demographic collision aggregation before dedup (section 5): N/A - no demographic normalization occurs.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - parquet order is `year`, `district_code`, `school_code`, `enrollment_period`, `grade_level`, `student_count`; no demographic applies.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, sections 11/12): PASS - no forbidden column appears in gold parquet.
- Canonical column vocabulary (section 16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - `grade_level` and `student_count` use the canonical vocabulary; no assessment-specific vocabulary applies.
- Shared categorical utilities applied (section 10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): PASS - `grade_level` uses `normalize_grade_column`; no subject column exists.
- Tidy long format (section 9 - no demographics/years/components as column names): PASS - grade is a `grade_level` row value, not a set of wide grade columns.
- FK keys present in dimension tables (section 13 - `district_code`, `school_code`, `demographic`): PASS - 245 distinct district keys and 2,604 distinct `(district_code, school_code)` keys resolve; no demographic FK applies.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - row grain and categorical filters derive cleanly from the contract; FK descriptors match dimension contracts.
- Standards compliance (catch-all for section 1-16 items not enumerated above): PASS - ID strings preserve leading zeros, aggregate geography is nulled, TFS becomes NULL, zeros are preserved in 2011-2020, and year-partitioned detail-level parquet layout is correct.

## Spot Checks

### Check 1

- Bronze: `data/bronze/education/gosa/enrollment_by_grade_level/enrollment_by_grade_level_2024.csv`, `LONG_SCHOOL_YEAR=2023-24`, `DETAIL_LVL_DESC=School`, `SCHOOL_DSTRCT_CD=748`, `INSTN_NUMBER=3052`, `ENROLLMENT_PERIOD=Fall`, `GRADE_LEVEL=2nd`, `ENROLLMENT_COUNT=80`.
- Transform path: `_transform()` lines 338-400 maps year, period, grade, IDs, and count.
- Gold: `year=2024`, `district_code=748`, `school_code=3052`, `enrollment_period=fall`, `grade_level=02`, `student_count=80`.
- Result: MATCH

### Check 2

- Bronze: `data/bronze/education/gosa/enrollment_by_grade_level/enrollment_by_grade_level_2011.csv`, district row `SCHOOL_DSTRCT_CD=601`, `INSTN_NUMBER=ALL`, `ENROLLMENT_PERIOD=Fall`, `GRADE_LEVEL=K`, `ENROLLMENT_COUNT=313`.
- Transform path: `_transform()` lines 338-400 maps `INSTN_NUMBER=ALL` to `school_code=NULL`, `K` to `k`, and count to Int64.
- Gold: `year=2011`, `district_code=601`, `school_code=NULL`, `enrollment_period=fall`, `grade_level=k`, `student_count=313`.
- Result: MATCH

### Check 3

- Bronze: `data/bronze/education/gosa/enrollment_by_grade_level/enrollment_by_grade_level_2011.csv`, school row `SCHOOL_DSTRCT_CD=743`, `INSTN_NUMBER=0207`, `ENROLLMENT_PERIOD=Fall`, `GRADE_LEVEL=1st`, `ENROLLMENT_COUNT=0`.
- Transform path: `_transform()` lines 382-398 casts the metric with `strict=False` and does not NULL true zeros.
- Gold: `year=2011`, `district_code=743`, `school_code=0207`, `enrollment_period=fall`, `grade_level=01`, `student_count=0`.
- Result: MATCH

### Check 4

- Bronze: `data/bronze/education/gosa/enrollment_by_grade_level/enrollment_by_grade_level_2022.csv`, school row `SCHOOL_DSTRCT_CD=758`, `INSTN_NUMBER=0175`, `ENROLLMENT_PERIOD=Spring`, `GRADE_LEVEL=8th`, `ENROLLMENT_COUNT=TFS`.
- Transform path: `read_bronze_file()` is called with shared suppression markers at lines 408-416; `_transform()` lines 382-398 casts the already-null TFS value to `student_count=NULL`.
- Gold: `year=2022`, `district_code=758`, `school_code=0175`, `enrollment_period=spring`, `grade_level=08`, `student_count=NULL`.
- Result: MATCH

### Check 5

- Bronze: `data/bronze/education/gosa/enrollment_by_grade_level/enrollment_by_grade_level_2022.csv` has 52 `School` rows with `INSTN_NUMBER=ALL` for districts `7830627` and `7830636`.
- Transform path: `_drop_school_all_sentinel_twins()` lines 262-314 anti-joins those rows against school-coded rows on district, period, grade, and count, then records the explicit filter.
- Gold: no 2022 district-level rows for `7830627` or `7830636`; each district retains 26 school-coded rows, and manifest records 52 filtered rows.
- Result: MATCH

### Check 6

- Bronze: global maximum trace from `data/bronze/education/gosa/enrollment_by_grade_level/enrollment_by_grade_level_2022.csv`, state row `LONG_SCHOOL_YEAR=2021-22`, `SCHOOL_DSTRCT_CD=ALL`, `INSTN_NUMBER=ALL`, `ENROLLMENT_PERIOD=Fall`, `GRADE_LEVEL=9th`, `ENROLLMENT_COUNT=159821`.
- Transform path: `_transform()` lines 338-400 maps state sentinels to NULL geography, `9th` to `09`, and count to Int64.
- Gold: `year=2022`, `district_code=NULL`, `school_code=NULL`, `enrollment_period=fall`, `grade_level=09`, `student_count=159821`.
- Result: MATCH

## Notes

- No required fixes were identified.
- No formula-level recomputation is applicable because the transform does not aggregate, derive, or collapse metric values; the metric is a direct cast from `ENROLLMENT_COUNT` after source suppression handling.
- The manifest records Era 1 columns after dropping the constant `#RPT_NAME`; this is documented by the transform and does not affect gold accuracy.
