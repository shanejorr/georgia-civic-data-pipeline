# Data Review: educator_qualifications_inexperienced_teachers_leaders

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Current gold output faithfully preserves the bronze rows, categorical meanings, suppression semantics, name-resolution exceptions, and metric scale; no must-fix transform defects were found.

## Summary

- Review date: 2026-06-11
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - `transform.py` mtime `2026-06-11T17:31:12.580043+00:00`; manifest generated `2026-06-11T17:31:38.502274+00:00`; validation timestamp `2026-06-11T17:31:38.588148+00:00`; validation passed.

## Files Reviewed

- Transform: `src/etl/education/gosa/educator_qualifications_inexperienced_teachers_leaders/transform.py`
- Contract: `contracts/education/educator_qualifications_inexperienced_teachers_leaders.odcs.yaml`
- Bronze files: 7 CSVs, `educator_qualifications_inexperienced_teachers_leaders_2018.csv` through `educator_qualifications_inexperienced_teachers_leaders_2024.csv`
- Gold files: 21 parquet files, `year=2018..2024/{schools,districts,states}.parquet`
- Manifest: `data/gold/education/educator_qualifications_inexperienced_teachers_leaders/_transform_manifest.json`
- Validation report: `data/gold/education/educator_qualifications_inexperienced_teachers_leaders/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `src/etl/education/CLAUDE.md`, `AGENTS.md`, `CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS - every parquet file has columns `year`, `district_code`, `school_code`, `role`, `poverty_subgroup`, `total_fte`, `inexperienced_fte`, `inexperienced_fte_rate`, exactly matching the contract order.
- Column roles and grain: PASS - contract grain is `year`, `district_code`, `school_code`, `role`, `poverty_subgroup`; `role` and `poverty_subgroup` are categoricals and the three FTE/rate columns are metrics.
- Metric units and derived quality checks: PASS - `total_fte` and `inexperienced_fte` are nonnegative count-like FTE metrics; `inexperienced_fte_rate` is a bounded 0-1 `proportion`; all 13 contract SQL checks are present.
- Categorical enums: PASS - contract enums match manifest and actual gold values: `role={leaders, teachers}` and `poverty_subgroup={high_poverty, low_poverty, not_applicable, total, unknown}`.
- Detail levels and layout metadata: PASS - contract declares `schools`, `districts`, `states`; path template is `education/educator_qualifications_inexperienced_teachers_leaders/year={year}/{detail}.parquet`; all seven years publish all three detail files.
- Foreign-key descriptors: PASS - contract declares `district_code -> districts` and composite `school_code -> schools` on `(district_code, school_code)`.
- Schema hash/version consistency: PASS - contract `version: 1.0.0`, `schema_hash: 97f942f22b6bb4ed8c400d5006fa87998929f352b6c65529faec9cd00e51b4dc`, and `year_range: 2018-2024` match the current gold layout and transform-emitted schema.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp is newer than manifest generation and `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 21 checks passed, 0 failed, 0 warnings; validator reports all 13 contract quality SQL checks pass.
- Validator warnings explained: N/A - validator recorded no warnings.
- section 15b quality-check coverage (cross-column invariants authored): PASS - authored checks cover numerator within denominator, rate reconciliation, school poverty-stratum duplication, single school stratum per role, Teachers exclusion from `not_applicable`/`unknown`, aggregate high+low poverty within total, and exactly six state rows per year. Manual extensions also found 0 school rate mirror mismatches and 0 aggregate `inexperienced_fte` high+low excesses.

## Manifest Verification

- Files processed coverage: PASS - manifest processed all seven current bronze CSVs; `scripts/check_bronze_freshness.py education gosa educator_qualifications_inexperienced_teachers_leaders` passed with all checksums matching and no unanalyzed files.
- Categorical and recode coverage: PASS - `role` maps `Teachers -> teachers`, `Leaders -> leaders`; `poverty_subgroup` maps all five source values to canonical snake_case; both have `unmapped_count: 0`.
- Row-count reconciliation: PASS - manifest total bronze `45,112`, total gold `45,093`, total filtered `19`; the 19 rows are fully explained by 2023-2024 documented drops/dedup.
- Metric stats sanity: PASS - rates range 0.0-1.0; all metrics are nonnegative; 2021+ null spikes align with `TFS` suppression while 2018-2020 preserve true zero values.

## Row and Join Accounting

- Bronze file/year disposition: PASS - 2018-2022 preserve 1:1 row counts; 2023 transforms 6,485 bronze rows to 6,470 gold rows after 138 reclassifications and 15 documented drops; 2024 transforms 6,462 bronze rows to 6,458 gold rows after 60 reclassifications, 3 documented drops, and 1 identical duplicate collapse.
- Filter accounting: PASS - explicit removals are `source_gap_district` 4, `force_drop_ambiguous_truncated_district_aggregate` 7, `source_gap_school` 7, and `duplicate_rows_deduped` 1.
- Join accounting: PASS - `_attach_codes()` joins one resolved code row per unique raw name/detail combination back to the transformed rows; direct FK audit found 0 unmatched district keys and 0 unmatched composite school keys.
- Deduplication accounting: PASS - the only duplicate natural key before dedup is the 2024 district-level `7820121/leaders/total` Utopian pair with identical metrics `(NULL, NULL, 1.0)`; dedup removes one row.
- Aggregation/unpivot accounting: N/A - no wide-to-long expansion or transform-computed aggregate rows; district and state rows are source-published. The only collapse is the identical Utopian duplicate noted above.

## Reconciliation Checks

- Artifact freshness: PASS - transform, manifest, validation, contract, bronze inventory, and gold files are mutually current.
- Contract freshness: PASS - contract is emitted from the transform schema and current gold layout; no `_metadata.json` dependency is used.
- Year coverage: PASS - bronze, manifest, contract, and gold all cover 2018-2024 with no gaps.
- Row preservation: PASS - all raw rows either appear in gold or have a documented disposition; no unexplained row loss or row multiplication was found.
- Column coverage: PASS - `LONG_SCHOOL_YEAR`, raw names, `LABEL_LVL_3_DESC`, `LABEL_LVL_2_DESC`, `FTE`, `INEXPERIENCED_FTE`/`CATEGORY_FTE`, and `INEXPERIENCED_FTE_PCT`/`CATEGORY_FTE_PCT` all have direct lineage into gold keys, categoricals, or metrics; source names are validly excluded as dimension attributes.
- Recode accuracy: PASS - source role and poverty-subgroup values preserve their meanings; `Not Applicable` and `Unknown` are retained for Leaders and never appear for Teachers.
- Asian-family demographic recodes (section 5b): N/A - topic has no demographic or race column.
- Demographic mutual exclusivity (section 5a - no rollup row alongside split source rows in the same category): N/A - topic has no demographic column; `poverty_subgroup` is a school-poverty stratum, not a student demographic.
- Demographic collision aggregation before dedup (section 5): N/A - no demographic normalization or demographic collision path.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - actual parquet order is `year`, `district_code`, `school_code`, then categoricals, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, sections 11/12): PASS - no forbidden fact-table columns are present in parquet or contract properties.
- Canonical column vocabulary (section 16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - no forbidden vocabulary variants; `inexperienced_fte_rate` uses the canonical rate suffix rather than `_pct`.
- Shared categorical utilities applied (section 10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no `grade_level` or `subject` column.
- Tidy long format (section 9 - no demographics/years/components as column names): PASS - role and poverty subgroup are row values, years are partitions/row keys, and no wide category columns remain.
- FK keys present in dimension tables (section 13 - `district_code`, `school_code`, `demographic`): PASS - all 241 populated district keys and all 2,396 populated composite school keys resolve; no demographic FK applies.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - contract exposes the correct natural grain, independent filters for `role` and `poverty_subgroup`, and dimension joins for district and school labels.
- Standards compliance (catch-all for sections 1-16 items not enumerated above): PASS - suppression markers are NULLed, IDs remain strings, aggregate geography keys are nulled, no empty parquet files exist, and manifest categorical/metric sections are complete.

## Spot Checks

### Check 1

- Bronze: `data/bronze/education/gosa/educator_qualifications_inexperienced_teachers_leaders/educator_qualifications_inexperienced_teachers_leaders_2024.csv`, `Gwinnett County / Mason Elementary School / Teachers / Low Poverty`, source values `FTE=65.5`, `CATEGORY_FTE=33`, `CATEGORY_FTE_PCT=50`.
- Transform path: `_transform_era()` in `src/etl/education/gosa/educator_qualifications_inexperienced_teachers_leaders/transform.py:423` casts FTE metrics and divides the percent by 100; `_attach_codes()` at `transform.py:515` resolves district/school codes.
- Gold: `year=2024/schools.parquet`, `district_code=667`, `school_code=0298`, `role=teachers`, `poverty_subgroup=low_poverty`, `total_fte=65.5`, `inexperienced_fte=33.0`, `inexperienced_fte_rate=0.5`.
- Result: MATCH

### Check 2

- Bronze: `data/bronze/education/gosa/educator_qualifications_inexperienced_teachers_leaders/educator_qualifications_inexperienced_teachers_leaders_2022.csv`, `Paulding County / Paulding County High School / Leaders / Not Applicable`, source values `FTE=TFS`, `INEXPERIENCED_FTE=TFS`, `INEXPERIENCED_FTE_PCT=17`.
- Transform path: `read_bronze_file(..., infer_schema_length=0)` in `transform.py:712` converts `TFS` to NULL; `_transform_era()` in `transform.py:497` casts metrics and divides the percent by 100.
- Gold: `year=2022/schools.parquet`, `district_code=710`, `school_code=2552`, `role=leaders`, `poverty_subgroup=not_applicable`, `total_fte=NULL`, `inexperienced_fte=NULL`, `inexperienced_fte_rate=0.17`.
- Result: MATCH

### Check 3

- Bronze: `data/bronze/education/gosa/educator_qualifications_inexperienced_teachers_leaders/educator_qualifications_inexperienced_teachers_leaders_2018.csv`, `State of Georgia / All Georgia Schools / Teachers / Total`, source values `FTE=118009.1`, `INEXPERIENCED_FTE=33781.4`, `INEXPERIENCED_FTE_PCT=29`.
- Transform path: `_transform_era()` in `transform.py:460` classifies the state row; `null_aggregate_geography()` in `transform.py:821` enforces NULL geography keys.
- Gold: `year=2018/states.parquet`, `district_code=NULL`, `school_code=NULL`, `role=teachers`, `poverty_subgroup=total`, `total_fte=118009.1`, `inexperienced_fte=33781.4`, `inexperienced_fte_rate=0.29`.
- Result: MATCH

### Check 4

- Bronze: `data/bronze/education/gosa/educator_qualifications_inexperienced_teachers_leaders/educator_qualifications_inexperienced_teachers_leaders_2024.csv`, two `State Charter Schools- Utopian Academy for the Arts` district aggregate rows for `Leaders / Total`, both with `FTE=TFS`, `CATEGORY_FTE=TFS`, `CATEGORY_FTE_PCT=100`; plus the `Leaders / Low Poverty` row with the same metric tuple.
- Transform path: `_repair_truncated_placeholder_aggregates()` in `transform.py:336` reclassifies the truncated district aggregate; the collision guard and `deduplicate_by_detail_level()` at `transform.py:781` allow only identical duplicate metrics and collapse the repeated `leaders/total` row.
- Gold: `year=2024/districts.parquet`, `district_code=7820121`, `role=leaders`, rows `poverty_subgroup=total` and `low_poverty`, both `total_fte=NULL`, `inexperienced_fte=NULL`, `inexperienced_fte_rate=1.0`; one duplicate `total` row removed.
- Result: MATCH

### Check 5

- Bronze: `data/bronze/education/gosa/educator_qualifications_inexperienced_teachers_leaders/educator_qualifications_inexperienced_teachers_leaders_2024.csv`, ambiguous truncated `State Charter Schools II- Genesis Innovation Academy` district aggregate rows whose Boys/Girls distinguisher is erased.
- Transform path: `_drop_documented_gaps()` in `transform.py:591` drops resolved-but-arbitrary Genesis district aggregates with reason `force_drop_ambiguous_truncated_district_aggregate`.
- Gold: no 2024 district-level Genesis row under `district_code=7830615`; corresponding school-level rows remain for `7830615/0615` Boys (`leaders/high_poverty`, rate 1.0) and `7830616/0616` Girls (`leaders/not_applicable`, rate NULL).
- Result: MATCH

## Notes

- No existing `data-review-claude.md` or previous `data-review-codex.md` content was read before completing the independent findings.
- The review was read-only except for writing this report.
