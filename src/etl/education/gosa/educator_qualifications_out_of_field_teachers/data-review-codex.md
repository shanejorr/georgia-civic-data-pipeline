# Data Review: educator_qualifications_out_of_field_teachers

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze, transform logic, contract, manifest, validator output, and gold Parquet reconcile; no must-fix accuracy issues were found.

## Summary

- Review date: 2026-06-11
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - all 7 bronze checksums match the structure report, all bronze files are represented in the manifest, the contract/parquet schema matches, and `_validation.json` is fresh relative to `_transform_manifest.json` and passing. The bronze structure report was amended after the transform run, but the bronze file checksums did not change and direct inspection verified the amended facts.

## Files Reviewed

- Transform: `src/etl/education/gosa/educator_qualifications_out_of_field_teachers/transform.py`
- Shared lookup logic: `src/etl/education/gosa/_educator_lookups.py`
- Contract: `contracts/education/educator_qualifications_out_of_field_teachers.odcs.yaml`
- Bronze files: 7 CSVs, `educator_qualifications_out_of_field_teachers_2018.csv` through `educator_qualifications_out_of_field_teachers_2024.csv`
- Gold files: 21 Parquet files, `year=2018` through `year=2024`, each with `schools.parquet`, `districts.parquet`, and `states.parquet`
- Manifest: `data/gold/education/educator_qualifications_out_of_field_teachers/_transform_manifest.json`
- Validation report: `data/gold/education/educator_qualifications_out_of_field_teachers/_validation.json`
- Supporting docs: `docs/codex-review-contract.md`, `docs/contract-creation.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS - contract properties are `year`, `district_code`, `school_code`, `poverty_subgroup`, `total_fte`, `out_of_field_fte`, `out_of_field_fte_rate`; every Parquet file has that exact order.
- Column roles and grain: PASS - roles are year, district FK, school FK, categorical, and three metrics; grain is `year`, `district_code`, `school_code`, `poverty_subgroup`, with geography NULLs at aggregate levels.
- Metric units and derived quality checks: PASS - `total_fte` and `out_of_field_fte` are `count`; `out_of_field_fte_rate` is `proportion`; derived non-negative and [0,1] checks are present.
- Categorical enums: PASS - contract enum `high_poverty`, `low_poverty`, `total` matches the transform map, manifest output, and actual gold distinct values.
- Detail levels and layout metadata: PASS - `schools`, `districts`, `states`, default `schools`, partition by `year`, and the path template match current gold layout.
- Foreign-key descriptors: PASS - `district_code` targets districts; `school_code` targets schools with composite `(district_code, school_code)`.
- Schema hash/version consistency: PASS - version is `1.0.0`, schema hash is present, available years are 2018-2024 with no gaps.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation reports `passed: true`; timestamp is after manifest `generated_at`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 20 pass, 0 fail, 1 warning.
- Validator warnings explained: PASS - warning is six null-rate spikes for `out_of_field_fte` and `out_of_field_fte_rate` in 2022-2024, matching the source's switch to explicit `TFS` suppression.
- Section 15b quality-check coverage (cross-column invariants authored): PASS - contract includes checks for numerator within denominator, rate reconciliation for `total_fte >= 3`, school poverty stratum mirroring, high/low school exclusivity, aggregate stratum totals within total, and exactly three state rows per year.

## Manifest Verification

- Files processed coverage: PASS - all 7 current bronze CSVs appear in `files_processed`; eras and row counts match direct bronze inspection.
- Categorical and recode coverage: PASS - `poverty_subgroup` maps `Total`, `High Poverty`, and `Low Poverty` to `total`, `high_poverty`, and `low_poverty`; `unmapped_count` is 0.
- Row-count reconciliation: PASS - 26,382 bronze rows -> 26,309 gold rows; all 73 removals are explicit 2023 events.
- Metric stats sanity: PASS - percentages are on the 0-1 scale, counts are non-negative, suppression NULLs begin in 2022 as documented, and the 2018-2021 zero spike is preserved and documented.

## Row and Join Accounting

- Bronze file/year disposition: PASS - 2018-2022 use the `OUTOFFIELD_FTE` era; 2023-2024 use the `CATEGORY_FTE` era; all years 2018-2024 are present in gold.
- Filter accounting: PASS - 2023 has 37 `state_charter_placeholder_district` rows and 4 `source_gap_school` rows dropped; direct replay showed no residual unresolved names after those filters.
- Join accounting: PASS - the resolver uses year-aware certified-personnel lookups, curated pins/aliases, dimension lookups, and guarded fallbacks; current gold has 232 district keys and 2,386 school key pairs, all resolving in dimensions.
- Deduplication accounting: PASS - after documented 2023 drops, 32 duplicate natural-key groups remain; each duplicate group has identical metrics before dedup, and dedup removes exactly 32 rows.
- Aggregation/unpivot accounting: N/A - the transform is one-row-in to one-row-out except documented filters and identical-row dedup; no unpivot, rollup, or weighted aggregation is performed.

## Reconciliation Checks

- Artifact freshness: PASS - bronze checksums match, no unanalyzed bronze files, and a null-safe in-memory shadow transform matched the gold row set exactly: 26,309 shadow rows, 26,309 gold rows, 0 rows only in either side.
- Contract freshness: PASS - contract was emitted from the current topic shape and has no `_metadata.json` dependency.
- Year coverage: PASS - bronze and gold cover 2018, 2019, 2020, 2021, 2022, 2023, and 2024.
- Row preservation: PASS - all row loss is accounted for by documented 2023 drops or identical duplicate republications.
- Column coverage: PASS - `LONG_SCHOOL_YEAR`, `SCHOOL_DSTRCT_NM`, `INSTN_NAME`, `LABEL_LVL_2_DESC`, `FTE`, and out-of-field metrics have clear lineage; constants `#CATEGORY_DESC` and `LABEL_LVL_3_DESC` are verified and dropped.
- Recode accuracy: PASS - poverty subgroup recodes are semantically correct and exhaustive.
- Asian-family demographic recodes (section 5b): N/A - topic has no demographic or race field.
- Demographic mutual exclusivity (section 5a): N/A - topic has no demographic field; `poverty_subgroup` is a school-poverty stratum, not a student demographic.
- Demographic collision aggregation before dedup (section 5): N/A - no demographic normalization is performed.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - actual Parquet order is `year`, `district_code`, `school_code`, `poverty_subgroup`, metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, sections 11/12): PASS - no forbidden columns appear in gold; `detail_level` is encoded by file name.
- Canonical column vocabulary (section 16): PASS - names follow the education vocabulary; no forbidden variants are present.
- Shared categorical utilities applied (section 10a): N/A - no `grade_level`, `subject`, or `demographic` column is emitted.
- Tidy long format (section 9): PASS - poverty strata are rows, not columns; years are partitions, not columns.
- FK keys present in dimension tables (section 13): PASS - direct join checks found 0 unmatched district keys and 0 unmatched school composite keys.
- Contract-driven API semantics: PASS - row grain, categorical filter, and FK joins are coherent with contract metadata.
- Standards compliance (catch-all for sections 1-16): PASS - suppression, null geography, ID formatting, units, manifest, validator, and star-schema checks passed.

## Spot Checks

### Check 1

- Bronze: `educator_qualifications_out_of_field_teachers_2021.csv`, `State of Georgia` / `All Georgia Schools` / `Total`: `FTE=112352.4`, `OUTOFFIELD_FTE=6281.9`, `OUTOFFIELD_FTE_PCT=6`
- Transform path: `transform.py:301` derives state detail, casts metrics, divides percent by 100; `transform.py:647` applies aggregate geography nulling
- Gold: `year=2021/states.parquet`, `district_code=NULL`, `school_code=NULL`, `poverty_subgroup=total`, `total_fte=112352.4`, `out_of_field_fte=6281.9`, `out_of_field_fte_rate=0.06`
- Result: MATCH

### Check 2

- Bronze: `educator_qualifications_out_of_field_teachers_2024.csv`, `Peach County` / `Hunt Elementary School` / `Total`: `FTE=42.5`, `CATEGORY_FTE=TFS`, `CATEGORY_FTE_PCT=11`
- Transform path: `transform.py:366` casts `FTE`, `transform.py:367` converts `TFS` to NULL via reader/cast, `transform.py:370` scales percent to 0.11, resolver attaches `district_code=711`, `school_code=0210`
- Gold: `year=2024/schools.parquet`, `district_code=711`, `school_code=0210`, `poverty_subgroup=total`, `total_fte=42.5`, `out_of_field_fte=NULL`, `out_of_field_fte_rate=0.11`
- Result: MATCH

### Check 3

- Bronze: `educator_qualifications_out_of_field_teachers_2022.csv`, `Richmond County` / `Josey High School` / `Total`: `FTE=34.8`, `OUTOFFIELD_FTE=12.3`, `OUTOFFIELD_FTE_PCT=35`
- Transform path: `transform.py:230` selects era 2 metrics; `transform.py:366`-`transform.py:370` casts and scales; resolver attaches `district_code=721`, `school_code=3756`
- Gold: `year=2022/schools.parquet`, `district_code=721`, `school_code=3756`, `poverty_subgroup=total`, `total_fte=34.8`, `out_of_field_fte=12.3`, `out_of_field_fte_rate=0.35`
- Result: MATCH

### Check 4

- Bronze: `educator_qualifications_out_of_field_teachers_2018.csv`, `Atlanta Public Schools` / `Grady High School` / `Total`: `FTE=128.7`, `OUTOFFIELD_FTE=24.5`, `OUTOFFIELD_FTE_PCT=19`
- Transform path: shared resolver in `_educator_lookups.py` handles historical naming; topic transform preserves metrics and scales the percent
- Gold: `year=2018/schools.parquet`, `district_code=761`, `school_code=4560`, `poverty_subgroup=total`, `total_fte=128.7`, `out_of_field_fte=24.5`, `out_of_field_fte_rate=0.19`
- Result: MATCH

### Check 5

- Bronze: `educator_qualifications_out_of_field_teachers_2023.csv`, two placeholder rows under `State Charter Schools ` / `State Charter Schools II- Genesis Innovation Academy` / `Total` with divergent metrics: `31.1/20.3/65` and `29.6/23.3/79`
- Transform path: `transform.py:406`-`transform.py:489` drops unresolved generic placeholder-charter rows under the documented predicate; this avoids arbitrary attribution after GOSA truncation erased the Boys/Girls distinguisher
- Gold: no row is emitted from those ambiguous placeholder rows; residual unresolved count after documented drops is 0
- Result: MATCH

## Notes

- No must-fix items were found.
- The standalone validator was also run during review and passed; it reports the same 20 pass / 0 fail / 1 warning result, with the null-rate warning explained by 2022+ suppression.
