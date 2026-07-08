# Data Review: enrollment_demographic_shares

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: bronze-to-gold reconciliation, contract conformance, validator output, categorical recodes, row ledger, and targeted value traces all match the current GOSA shared-source transform.

## Summary

- Review date: 2026-06-11
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - `_transform_manifest.json` was generated at `2026-06-11T19:46:00.339427+00:00`; `_validation.json` was generated at `2026-06-11T19:46:00.449356+00:00` and passed. Topic transform and shared bronze reader mtimes are older than the manifest.

## Files Reviewed

- Transform: `src/etl/education/gosa/enrollment_demographic_shares/transform.py`
- Shared bronze reader: `src/etl/education/gosa/_enrollment_subgroup_programs_shared.py`
- Contract: `contracts/education/enrollment_demographic_shares.odcs.yaml`
- Bronze files: 21 shared-source files in `data/bronze/education/gosa/enrollment_by_subgroup_programs/`, 2004-2024; all checksums match `bronze-data-structure.md`
- Gold files: 61 parquet files under `data/gold/education/enrollment_demographic_shares/` (school/district/state for all years except no state files in 2009 and 2010, matching bronze)
- Manifest: `data/gold/education/enrollment_demographic_shares/_transform_manifest.json`
- Validation report: `data/gold/education/enrollment_demographic_shares/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `CLAUDE.md`, `AGENTS.md`, `src/etl/education/CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS - contract properties exactly match parquet order: `year`, `district_code`, `school_code`, `demographic`, `met_ayp`, `improvement_status`, `pct_of_enrollment`.
- Column roles and grain: PASS - roles are `year`, `fk_district`, `fk_school`, `fk_demographic`, `categorical`, `categorical`, `metric`; grain is year plus geography plus the three categoricals.
- Metric units and derived quality checks: PASS - `pct_of_enrollment` is `unit: ratio`; contract quality enforces non-negative values and authored upper sanity bound `<= 1.5`. Actual range is `0.0` to `1.32`.
- Categorical enums: PASS - contract enums match manifest and gold distinct values for all three categorical fields.
- Detail levels and layout metadata: PASS - `detail_levels` are `schools`, `districts`, `states`; `path_template` and `partition_columns` match the year-partitioned layout.
- Foreign-key descriptors: PASS - contract declares district, composite school, and demographic joins; validator and manual checks resolve all 252 district keys, 2,913 school keys, and 12 demographic keys.
- Schema hash/version consistency: PASS - version is `1.0.0`, schema hash is `3f46dac823df881689ce386110481107ce96ffbe0e36ab759c3b7f8429fa810c`, and year range is `2004-2024`.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp is seconds after manifest generation and `"passed": true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 21 checks passed, 0 failed, 0 warnings.
- Validator warnings explained: N/A - validator reported no warnings.
- Section 15b quality-check coverage (cross-column invariants authored): PASS - contract quality includes non-empty, categorical enums, non-negative ratio, sane upper bound, post-2010 AYP nulling, era-gap demographic nulling, and exactly 12 demographic rows per entity-year.

## Manifest Verification

- Files processed coverage: PASS - manifest lists the same 21 bronze data files currently present in the shared bronze directory, with years 2004-2024 and no extras or omissions.
- Categorical and recode coverage: PASS - `demographic`, `met_ayp`, and `improvement_status` all have `unmapped_count: 0`; `gold_values_produced` matches actual gold values.
- Row-count reconciliation: PASS - 51,364 bronze rows would produce 616,368 long rows at 12 demographics each; subtract 12 rows for the one malformed 2004 raw row and 1,356 duplicate long rows, yielding the actual 615,000 gold rows.
- Metric stats sanity: PASS - `pct_of_enrollment` is on 0-1 scale, has no negatives, max is the documented 1.32 ratio, and null spikes align with era-gap demographics plus 2011 and 2023-2024 suppression.

## Row and Join Accounting

- Bronze file/year disposition: PASS - all 21 shared bronze files are processed. The literal topic-named bronze directory is absent, but `BRONZE_DIR` points to the shared `enrollment_by_subgroup_programs` source and both derived topics intentionally consume it.
- Filter accounting: PASS - 2004 drops one malformed `ID='2'` raw row; no valid observation data is present in that row. No other filters remove valid rows.
- Join accounting: N/A - the transform performs no enrichment joins. FK joins are contract/validator semantics only and all keys resolve against dimension tables.
- Deduplication accounting: PASS - 2004 has 109 exact duplicate rows and 2009 has 4 duplicate key groups; inspected 2009 duplicate groups agree on every fact metric and AYP categorical, differing only in dimension-only name/grade cells for two district aggregates.
- Aggregation/unpivot accounting: PASS - each retained wide entity-year row emits exactly 12 demographic rows; no source rows are aggregated except duplicate removal after `assert_no_natural_key_collisions`.

## Reconciliation Checks

- Artifact freshness: PASS - manifest, contract, validation report, and parquet outputs were emitted by the current transform/shared reader state.
- Contract freshness: PASS - contract was emitted after parquet and has no `_metadata.json` dependency.
- Year coverage: PASS - gold covers 2004-2024. State files are absent only for 2009 and 2010, when bronze publishes no state row.
- Row preservation: PASS - ledger reconciles from bronze to gold exactly: `51,364 * 12 - 12 - 1,356 = 615,000`.
- Column coverage: PASS - all fact keys, categoricals, and the demographic share metric are present; dimension-only names/grades are excluded.
- Recode accuracy: PASS - `Yes`/`No` -> `yes`/`no`, improvement statuses -> lowercase canonical codes, and all demographic source columns map to the intended canonical demographics.
- Asian-family demographic recodes (section 5b): PASS - bronze headers contain only `Asian Percentage of Enrollment`, `ENROLL_PERCENT_ASIAN`, and `ENROLL_PCT_ASIAN`; no Pacific Islander, Native Hawaiian, or NHPI split exists. State race-share sums are 101.0 in 2004, 99.0 in 2011, and 100.0 in 2022, consistent with the documented rounded combined-bucket convention. Gold emits `asian_pacific_islander` and emits no `asian` or `pacific_islander` rows.
- Demographic mutual exclusivity (section 5a - no rollup row alongside split source rows in the same category): PASS - race values are the six source buckets with `asian_pacific_islander` only; there is no split-plus-rollup collision.
- Demographic collision aggregation before dedup (section 5): N/A - each source demographic column maps to a distinct canonical value, so there are no demographic collisions to aggregate.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - parquet and contract order are `year`, geography keys, `demographic`, `met_ayp`, `improvement_status`, `pct_of_enrollment`.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, sections 11/12): PASS - parquet contains no forbidden columns; `detail_level` is implicit in file names.
- Canonical column vocabulary (section 16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - applicable columns use canonical names; no grade, subject, proficiency, or assessment columns apply.
- Shared categorical utilities applied (section 10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - this topic has no `grade_level` or `subject` column; demographics use `normalize_demographic_column`.
- Tidy long format (section 9 - no demographics/years/components as column names): PASS - 12 wide demographic columns are unpivoted into `demographic` plus `pct_of_enrollment`.
- FK keys present in dimension tables (section 13 - `district_code`, `school_code`, `demographic`): PASS - manual FK checks found 0 unmatched keys and no duplicate dimension PKs.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - contract exposes independent categorical filters for `demographic`, `met_ayp`, and `improvement_status`, and FK descriptors match dimensions.
- Standards compliance (catch-all for sections 1-16 items not enumerated above): PASS - IDs are strings with leading zeros preserved, geography aggregate sentinels are nulled, suppression markers do not survive, and no empty parquet files exist.

## Spot Checks

### Check 1

- Bronze: `enrollment_by_subgroup_programs_2004.csv`, `ID=601:1050`, `Met AYP=Yes`, `Improvement Status=ADEQ`, `Black Percentage of Enrollment=5`
- Transform path: shared Era A scaling/ID parsing in `src/etl/education/gosa/_enrollment_subgroup_programs_shared.py:551` and unpivot in `src/etl/education/gosa/enrollment_demographic_shares/transform.py:205`
- Gold: `year=2004`, `district_code=601`, `school_code=1050`, `demographic=black`, `met_ayp=yes`, `improvement_status=adeq`, `pct_of_enrollment=0.05`
- Result: MATCH

### Check 2

- Bronze: `enrollment_by_subgroup_programs_2004.csv`, same entity has no male/female/migrant columns in the AYP era.
- Transform path: missing wide columns padded as typed NULLs in `src/etl/education/gosa/_enrollment_subgroup_programs_shared.py:418`; uniform-grid unpivot in `transform.py:205`
- Gold: `year=2004`, `district_code=601`, `school_code=1050`, `demographic=male`, `pct_of_enrollment=NULL`
- Result: MATCH

### Check 3

- Bronze: `enrollment_by_subgroup_programs_2005.xls`, `State Level` sheet, `ID=ALL:ALL`, `Met AYP=No`, `White Percentage of Enrollment=49`
- Transform path: multi-sheet read/tag in `src/etl/education/gosa/_enrollment_subgroup_programs_shared.py:445`, state geography nulling in `transform.py:316`
- Gold: `year=2005`, `district_code=NULL`, `school_code=NULL`, `demographic=white`, `met_ayp=no`, `pct_of_enrollment=0.49`
- Result: MATCH

### Check 4

- Bronze: `enrollment_by_subgroup_programs_2011.csv`, `SCHOOL_DSTRCT_CD=601`, `INSTN_NUMBER=0103`, `LONG_SCHOOL_YEAR=2010-11`, `ENROLL_PERCENT_ASIAN=1`, `ENROLL_PERCENT_MALE=55`, `ENROLL_PERCENT_LEP=NULL`
- Transform path: modern-year validation and scaling in `src/etl/education/gosa/_enrollment_subgroup_programs_shared.py:642` and `:712`; Asian combined-bucket label in `transform.py:135`
- Gold: `year=2011`, `district_code=601`, `school_code=0103`; `asian_pacific_islander=0.01`, `male=0.55`, `english_learners=NULL`, AYP categoricals NULL
- Result: MATCH

### Check 5

- Bronze: `enrollment_by_subgroup_programs_2024.csv`, district row `SCHOOL_DSTRCT_CD=601`, `INSTN_NUMBER=ALL`, `ENROLL_PCT_NATIVE=TFS`
- Transform path: read-time suppression/null casting plus modern scaling in `src/etl/education/gosa/_enrollment_subgroup_programs_shared.py:712`; district geography nulling in `transform.py:316`
- Gold: `year=2024`, `district_code=601`, `school_code=NULL`, `demographic=native_american`, `pct_of_enrollment=NULL`
- Result: MATCH

### Check 6

- Bronze: `enrollment_by_subgroup_programs_2022.csv`, rows labeled `DETAIL_LVL_DESC=School` with `INSTN_NUMBER=ALL` for districts `7830627` and `7830636`; `ENROLL_PERCENT_BLACK=88/19`, `ENROLL_PERCENT_ED=23/7`
- Transform path: charter aggregate reclassification in `src/etl/education/gosa/_enrollment_subgroup_programs_shared.py:676`
- Gold: district-level rows with `school_code=NULL`; district `7830627` has `black=0.88`, `economically_disadvantaged=0.23`, and district `7830636` has `black=0.19`, `economically_disadvantaged=0.07`
- Result: MATCH

### Check 7

- Bronze: `enrollment_by_subgroup_programs_2008.xls`, School Level `SysSchoolID=705:108`, Mountain Creek Academy, `Economically Disadvantaged Percentage of Enrollment=132`
- Transform path: Era A percentage division by 100 in `src/etl/education/gosa/_enrollment_subgroup_programs_shared.py:551`; ratio contract policy in `transform.py:474`
- Gold: `year=2008`, `district_code=705`, `school_code=0108`, `demographic=economically_disadvantaged`, `pct_of_enrollment=1.32`
- Result: MATCH

## Notes

- This is a derived topic. The expected local topic-shaped bronze directory `data/bronze/education/gosa/enrollment_demographic_shares/` is not present, but the transform's actual `BRONZE_DIR` is the shared `data/bronze/education/gosa/enrollment_by_subgroup_programs/` source. That shared source is profiled, checksummed, present, and fully covered by the manifest.
- Manifest `filtered_explicit` mixes one pre-unpivot malformed raw row with post-unpivot duplicate long-row removals. The manual row ledger accounts for units explicitly and reconciles to parquet exactly; this is not a data accuracy defect.
