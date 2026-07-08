# Data Review: georgia_milestones_end_of_course_eoc_assessment_by_grade

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: bronze-to-gold row coverage, categorical recodes, metric scaling, contract semantics, validator output, and spot checks all support a faithful transform.

## Summary

- Review date: 2026-06-11
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - `scripts/check_bronze_freshness.py` passes for all 9 bronze files; transform mtime `2026-06-11T23:34:17.130709+00:00` is older than manifest `2026-06-11T23:34:43.657942+00:00`; validation `2026-06-11T23:34:43.881134+00:00` is newer than the manifest and passing.

## Files Reviewed

- Transform: `src/etl/education/gosa/georgia_milestones_end_of_course_eoc_assessment_by_grade/transform.py`
- Contract: `contracts/education/georgia_milestones_end_of_course_eoc_assessment_by_grade.odcs.yaml`
- Bronze files: 9 CSV files for 2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024 under `data/bronze/education/gosa/georgia_milestones_end_of_course_eoc_assessment_by_grade/`
- Gold files: 27 parquet files, one `states.parquet`, `districts.parquet`, and `schools.parquet` for each of the 9 years under `data/gold/education/georgia_milestones_end_of_course_eoc_assessment_by_grade/`
- Manifest: `data/gold/education/georgia_milestones_end_of_course_eoc_assessment_by_grade/_transform_manifest.json`
- Validation report: `data/gold/education/georgia_milestones_end_of_course_eoc_assessment_by_grade/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS - validator reports all 27 parquet files match the contract, and direct comparison confirms contract properties equal the gold column order: `year`, `district_code`, `school_code`, `demographic`, `grade_level`, `subject`, then 11 metrics.
- Column roles and grain: PASS - contract grain is `year`, `district_code`, `school_code`, `demographic`, `grade_level`, `subject`, matching transform natural keys and the actual unique gold grain.
- Metric units and derived quality checks: PASS - count metrics use `unit: count`; six percentage/cumulative metrics use `unit: proportion`; contract includes non-negative and `[0, 1]` checks plus topic-specific co-null, upper-bound, and cumulative checks.
- Categorical enums: PASS - contract enums match manifest and gold distinct values: 22 demographics, 6 grade levels, and 11 subjects.
- Detail levels and layout metadata: PASS - contract custom properties list `schools`, `districts`, `states`; local/S3 path templates match the current partition layout.
- Foreign-key descriptors: PASS - contract declares district, composite school `(district_code, school_code)`, and demographic FKs; validator reports all keys resolve.
- Schema hash/version consistency: PASS - contract version is `1.0.0`, status `active`, and custom `schema_hash` is `742035feecb442bade1cc132f06e55618033e24126147e6eb327bcaeb8f666e1`; year metadata records available years 2015-2019 and 2021-2024 with 2020 as a gap.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp `2026-06-11T23:34:43.881134+00:00` is newer than manifest `2026-06-11T23:34:43.657942+00:00`; `passed` is `true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 20 pass, 0 fail, 1 warning; schema, grain uniqueness, contract quality SQL, foreign keys, geography nulling, and canonical vocabulary all pass.
- Validator warnings explained: PASS - the only warning is 4 null-rate spikes, all in 2024 count metrics (`num_tested`, `num_beginning_learner`, `num_developing_learner`, `num_proficient_learner`) caused by the documented 2024 source expansion of `TFS` count suppression.
- Section 15b quality-check coverage (cross-column invariants authored): PASS - contract includes checks for reported-count percentage presence, pre-2024 full-suppression co-nullity, level-count upper bounds, single-level count bounds, four-share upper bound, both cumulative formulas, and subject curriculum year ranges.

## Manifest Verification

- Files processed coverage: PASS - manifest lists all 9 current bronze CSV files, years, eras, row counts, and column sets; bronze checksum freshness also passes.
- Categorical and recode coverage: PASS - `demographic`, `grade_level`, and `subject` all have `unmapped_count: 0`; manifest values match actual bronze distinct values and gold distinct values.
- Row-count reconciliation: PASS - manifest total bronze rows `906,229` equals total gold rows `906,229`; every year has expansion factor `1.0`.
- Metric stats sanity: PASS - counts are non-negative; percentage metrics are on 0-1 scale with min/max inside `[0, 1]`; 2017 `num_developing_learner` zero/null anomaly and 2024 count null spikes match documented source behavior.

## Row and Join Accounting

- Bronze file/year disposition: PASS - each current bronze file maps to exactly one gold year; 2020 is absent from both bronze and gold by documented COVID testing suspension.
- Filter accounting: N/A - no source rows are filtered; Era 2's `#ASSMT_CD` is verified as the constant `EOC_by_GRADE` and dropped as non-gold metadata.
- Join accounting: N/A - the transform performs no joins or lookups; FK joins are downstream API semantics and validator coverage confirms dimension key resolution.
- Deduplication accounting: PASS - no bronze file has duplicate normalized natural keys, gold has 0 duplicate grain groups, and independent bronze-derived rows equal gold rows exactly.
- Aggregation/unpivot accounting: PASS - no row aggregation or unpivot changes the row count; only the two cumulative percentage metrics are derived from same-row percentage fields.

## Reconciliation Checks

- Artifact freshness: PASS - bronze freshness check passes; manifest and validation are current relative to the transform.
- Contract freshness: PASS - contract was emitted from the current transform/gold and validation consumed it directly; no `_metadata.json` dependency.
- Year coverage: PASS - gold years are `[2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024]`, matching the bronze inventory and documented 2020 gap.
- Row preservation: PASS - actual detail counts match bronze sentinels exactly, e.g. 2024 has 570 state, 40,651 district, and 97,526 school rows; all years sum to their manifest row counts.
- Column coverage: PASS - every `fact_key`, `fact_categorical`, and `fact_metric` in the bronze structure report has a gold disposition; name columns and `#ASSMT_CD` are valid exclusions.
- Recode accuracy: PASS - grades `7/8/9` normalize to `07/08/09`, already padded grades pass through, `SUBGROUP_NAME` maps to canonical demographics, and all 11 EOC course labels map to the intended subject values.
- Asian-family demographic recodes (section 5b): PASS - every bronze year publishes a separate `Native Hawaiian or Other Pacific Islander` row; gold has `asian` and `pacific_islander` rows and 0 `asian_pacific_islander` rows.
- Demographic mutual exclusivity (section 5a - no rollup row alongside split source rows in the same category): PASS - no `asian_pacific_islander` rollup is emitted with the split rows; `active_duty` appears only in 2021 and `military_connected` only in 2022-2024.
- Demographic collision aggregation before dedup (section 5): N/A - no same-year raw demographic labels collapse to one canonical key; collision guard remains in place.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - actual parquet order matches this order and the contract.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, sections 11/12): PASS - actual gold files contain none of those columns.
- Canonical column vocabulary (section 16 - `num_tested`, `grade_level`, `subject`, proficiency-band names, `_or_above`, etc.): PASS - output uses canonical vocabulary and validator confirms no forbidden variants.
- Shared categorical utilities applied (section 10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): PASS - transform uses `normalize_grade_column` for `grade_level` and `apply_subject_normalization` after the topic subject map.
- Tidy long format (section 9 - no demographics/years/components as column names): PASS - demographics, grade, and subject are row values, not wide columns.
- FK keys present in dimension tables (section 13 - `district_code`, `school_code`, `demographic`): PASS - direct anti-join checks found 0 district misses, 0 composite school misses, and 0 demographic misses; validator reports all 218 district keys, 1,064 school keys, and 22 demographic keys resolve.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - contract grain, enums, and FK descriptors reflect the actual gold shape.
- Standards compliance (catch-all for sections 1-16 items not enumerated above): PASS - suppression markers become NULL where appropriate, rates are 0-1, IDs preserve leading zeros, state/district geography keys are nulled per detail level, and no impossible metric values are served.

## Spot Checks

### Check 1

- Bronze: `georgia_milestones_end_of_course_eoc_assessment_by_grade_2015.csv`, state row `LONG_SCHOOL_YEAR=2014-15`, `ACDMC_LVL=7`, `SUBGROUP_NAME=All Students`, `TEST_CMPNT_TYP_NM=Biology`, `NUM_TESTED_CNT=37`, `BEGIN_CNT=TFS`, `DEVELOPING_CNT=11`, `PROFICIENT_CNT=22`, `DISTINGUISHED_CNT=3`, pcts `2.7/29.7/59.5/8.1`.
- Transform path: `transform.py:459-558` derives detail/geography, grade, subject, demographic, count casts, 0-1 percentage scaling, and cumulative percentages.
- Gold: `year=2015`, `district_code=NULL`, `school_code=NULL`, `demographic=all`, `grade_level=07`, `subject=biology`, `num_tested=37`, `num_beginning_learner=NULL`, counts `11/22/3`, pcts `0.027/0.297/0.595/0.081`, cumulatives `0.973` and `0.676`.
- Result: MATCH

### Check 2

- Bronze: `georgia_milestones_end_of_course_eoc_assessment_by_grade_2024.csv`, school row `#ASSMT_CD=EOC_by_GRADE`, `SCHOOL_DISTRCT_CD=601`, `INSTN_NUMBER=0103`, `ACDMC_LVL=09`, `SUBGROUP_NAME=All Students`, `TEST_CMPNT_TYP_NM=Algebra: Concepts and Connections`, counts `258/46/85/82/45`, pcts `17.8/32.9/31.8/17.4`.
- Transform path: `transform.py:592-599` verifies/drops `#ASSMT_CD`; `transform.py:459-558` maps the row to the gold schema.
- Gold: `year=2024`, `district_code=601`, `school_code=0103`, `demographic=all`, `grade_level=09`, `subject=algebra_concepts_and_connections`, counts `258/46/85/82/45`, pcts `0.178/0.329/0.318/0.174`, cumulatives `0.821` and `0.492`.
- Result: MATCH

### Check 3

- Bronze: `georgia_milestones_end_of_course_eoc_assessment_by_grade_2024.csv`, same school/grade, `TEST_CMPNT_TYP_NM=Biology`, all five count fields are `TFS`, but pcts are `40/60/0/0`.
- Transform path: `transform.py:528-556` casts `TFS` counts to NULL while preserving and scaling the published percentage fields.
- Gold: counts are all NULL; pcts are `0.4/0.6/0.0/0.0`; cumulatives are `0.6` and `0.0`.
- Result: MATCH

### Check 4

- Bronze: `georgia_milestones_end_of_course_eoc_assessment_by_grade_2024.csv`, state row `SUBGROUP_NAME=Native Hawaiian or Other Pacific Islander`, `ACDMC_LVL=09`, `TEST_CMPNT_TYP_NM=Algebra: Concepts and Connections`, `NUM_TESTED_CNT=111`, level counts `31/33/30/17`, pcts `27.9/29.7/27/15.3`.
- Transform path: `transform.py:517-526` uses `normalize_demographic_column`; split race convention maps this label to `pacific_islander`.
- Gold: `demographic=pacific_islander`, geography keys NULL, grade `09`, subject `algebra_concepts_and_connections`, counts `111/31/33/30/17`, pcts `0.279/0.297/0.27/0.153`.
- Result: MATCH

### Check 5

- Bronze: `georgia_milestones_end_of_course_eoc_assessment_by_grade_2015.csv`, school row `SCHOOL_DISTRCT_CD=603`, `INSTN_NUMBER=302`, `SUBGROUP_NAME=Not Economically Disadvantaged`, `ACDMC_LVL=9`, `TEST_CMPNT_TYP_NM=Physical Science`, pcts `0/45.5/45.5/9.1` on the 0-100 source scale.
- Transform path: `transform.py:346-358` and `transform.py:544-556` cap small cumulative rounding overshoot; `45.5 + 45.5 + 9.1 = 100.1%` becomes `pct_developing_learner_or_above=1.0`.
- Gold: `district_code=603`, `school_code=0302`, `demographic=not_economically_disadvantaged`, `grade_level=09`, `subject=physical_science`, pcts `0.0/0.455/0.455/0.091`, `pct_developing_learner_or_above=1.0`, `pct_proficient_learner_or_above=0.546`.
- Result: MATCH

## Notes

- I did not read any prior topic review report before completing these findings; no existing `data-review-codex.md` was present.
- Independent reconstruction of the gold schema from the current bronze files produced `906,229` rows and matched the current gold parquet frame exactly.
- No must-fix issues were found.
