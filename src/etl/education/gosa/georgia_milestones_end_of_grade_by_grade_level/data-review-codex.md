# Data Review: georgia_milestones_end_of_grade_eog_assessment_by_grade

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: bronze, transform, contract, validator, manifest, and gold parquet reconcile; no must-fix bronze-to-gold accuracy defects found.

## Summary

- Review date: 2026-06-11
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH — `scripts/check_bronze_freshness.py` passed for all 9 bronze CSV checksums with no unanalyzed files; transform mtime `2026-06-11T23:30:55Z` precedes manifest `2026-06-11T23:31:14Z`; validation timestamp `2026-06-11T23:31:14Z` is later than the manifest and reports `passed: true`.

## Files Reviewed

- Transform: `src/etl/education/gosa/georgia_milestones_end_of_grade_eog_assessment_by_grade/transform.py`
- Contract: `contracts/education/georgia_milestones_end_of_grade_eog_assessment_by_grade.odcs.yaml`
- Bronze files: 9 CSVs for 2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024 under `data/bronze/education/gosa/georgia_milestones_end_of_grade_eog_assessment_by_grade/`
- Gold files: 27 parquet files, `states.parquet`, `districts.parquet`, and `schools.parquet` for each processed year under `data/gold/education/georgia_milestones_end_of_grade_eog_assessment_by_grade/`
- Manifest: `data/gold/education/georgia_milestones_end_of_grade_eog_assessment_by_grade/_transform_manifest.json`
- Validation report: `data/gold/education/georgia_milestones_end_of_grade_eog_assessment_by_grade/_validation.json`
- Supporting docs: `docs/codex-review-contract.md`, `docs/contract-creation.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`, and relevant utilities in `src/utils/`.

## Contract Verification

- Schema/parquet column match: PASS — all 27 parquet files have exactly the contract property order: `year`, `district_code`, `school_code`, `demographic`, `grade_level`, `subject`, count metrics, percentage metrics, and derived cumulative percentage metrics.
- Column roles and grain: PASS — contract grain is `year`, `district_code`, `school_code`, `demographic`, `grade_level`, `subject`; roles match the transform's output design and validation reports one row per grain tuple.
- Metric units and derived quality checks: PASS — count metrics use `unit: count`; percentage metrics use `unit: proportion`; the contract carries derived non-negative and [0,1] checks plus authored cross-column invariants.
- Categorical enums: PASS — manifest-produced values exactly match contract enums for `demographic`, `grade_level`, and `subject`; every categorical has `unmapped_count: 0`.
- Detail levels and layout metadata: PASS — contract declares `schools`, `districts`, `states`, `partition_columns: [year]`, and path template `education/georgia_milestones_end_of_grade_eog_assessment_by_grade/year={year}/{detail}.parquet`; current layout matches.
- Foreign-key descriptors: PASS — contract describes `district_code -> districts`, composite `district_code + school_code -> schools`, and `demographic -> demographics`; validator and manual anti-joins found zero unmatched keys.
- Schema hash/version consistency: PASS — contract version is `1.0.0`, schema hash is `692af1c294d3905d0aeceba72f51ac9e4ab6c34b14fd9c9eb4fff20a69a28c7f`, available years are 2015-2019 and 2021-2024, with 2020 correctly recorded as a year gap.

## Validator Verification

- `_validation.json` fresh + passing: PASS — validation timestamp `2026-06-11T23:31:14.442727+00:00` is after manifest generation and `passed` is `true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS — schema, dtypes, percentage scale, grain uniqueness, 23 contract quality SQL checks, canonical vocabulary, FK integrity, and geography nulling all passed.
- Validator warnings explained: PASS — the only warning is 2024 null-rate spikes for `num_tested`, `num_beginning_learner`, `num_developing_learner`, and `num_proficient_learner`; bronze 2024 uses `TFS` heavily in those count fields, including 85,104 `NUM_TESTED_CNT` suppressions.
- §15b quality-check coverage (cross-column invariants authored): PASS — the contract includes partition-sum, cumulative-share, nested-threshold, level-count, count-sum, and count/share reconciliation checks. They are scoped for the documented Foster Care source exception.

## Manifest Verification

- Files processed coverage: PASS — all 9 current bronze CSVs appear in `files_processed` with the expected eras: 2015-2023 as `era_1_2015_2023` and 2024 as `era_2_2024`.
- Categorical and recode coverage: PASS — `demographic`, `grade_level`, and `subject` mappings cover every observed bronze value with zero unmapped values.
- Row-count reconciliation: PASS — manifest records 1,995,262 bronze rows and 1,995,262 gold rows; each year has expansion factor `1.0` and `filtered: 0`.
- Metric stats sanity: PASS — manifest metric stats match actual gold after rounding to the manifest's serialized precision; metric ranges are valid (`num_* >= 0`, `pct_*` in `[0,1]`).

## Row and Join Accounting

- Bronze file/year disposition: PASS — every current bronze CSV is processed; no 2020 file exists and no 2020 gold partition exists, matching the documented COVID cancellation gap.
- Filter accounting: N/A — transform applies no row filters; row counts are one-to-one from bronze to gold.
- Join accounting: N/A — transform performs no joins. Dimension joins are contract/API semantics and were verified by the validator plus manual anti-joins.
- Deduplication accounting: PASS — `assert_no_natural_key_collisions` precedes `deduplicate_by_detail_level`; actual independent reconstruction and gold both have zero duplicate natural keys, and row counts prove dedup removed no rows.
- Aggregation/unpivot accounting: PASS — no row-collapsing aggregation or unpivot occurs. The only derived values are `pct_developing_learner_or_above` and `pct_proficient_learner_or_above`, both verified from source percentage columns.

## Reconciliation Checks

- Artifact freshness: PASS — bronze checksums match the bronze structure report, manifest and validation are current, and gold partitions match manifest years.
- Contract freshness: PASS — contract schema matches current parquet and no `_metadata.json` dependency is used.
- Year coverage: PASS — gold covers 2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, and 2024 only.
- Row preservation: PASS — an independent reconstruction from the 9 bronze CSVs matched all 1,995,262 gold rows exactly, including keys, metrics, nulls, detail levels, and derived cumulative metrics.
- Column coverage: PASS — fact keys, categoricals, and metrics from bronze are represented; source-only `#ASSMT_CD`, `LONG_SCHOOL_YEAR`, district/school names, and sentinel labels are excluded from gold as dimension/source metadata.
- Recode accuracy: PASS — grade values `3`/`03` through `8`/`08` normalize to `03`-`08`; subjects normalize to the five canonical subject values; demographic labels normalize to canonical demographics.
- Asian-family demographic recodes (§5b): PASS — every bronze year has both `Asian` and `Native Hawaiian or Other Pacific Islander`, no bronze year has `Asian/Pacific Islander`, gold has zero `asian_pacific_islander` rows, and no race group mixes combined and split conventions.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): PASS — no group contains `asian_pacific_islander` with `asian` or `pacific_islander`; `active_duty` appears only in 2021 and `military_connected` only in 2022-2024.
- Demographic collision aggregation before dedup (§5): N/A — no two observed bronze labels normalize to the same canonical key within a year; collision guard would fail if that changes.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS — parquet column order matches the standard order and contract order.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS — exported parquet omits `detail_level`, `#ASSMT_CD`, `LONG_SCHOOL_YEAR`, names, and crosswalk IDs.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS — validator reports no canonical vocabulary violations.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): PASS — transform uses `normalize_grade_column` for `grade_level` and applies `apply_subject_normalization` after the topic-local subject map.
- Tidy long format (§9 — no demographics/years/components as column names): PASS — each row is one entity x demographic x grade x subject observation; achievement levels are metric columns by design, not categorical rows.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS — manual anti-joins found 0 unmatched district keys, 0 unmatched composite school keys, and 0 unmatched demographic keys.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS — grain, categorical filters, and FK descriptors are coherent with the gold schema.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS — IDs preserve leading zeros, percentages are 0-1, suppression markers become NULL, aggregate geography keys are nulled, and no empty parquet files exist.

## Spot Checks

### Check 1

- Bronze: `georgia_milestones_end_of_grade_eog_assessment_by_grade_2015.csv`, district `732`, school `101`, grade `8`, `Economically Disadvantaged`, `Mathematics`: `NUM_TESTED_CNT=102`, `BEGIN_CNT=16`, `DEVELOPING_CNT=56`, `PROFICIENT_CNT=26`, `DISTINGUISHED_CNT=TFS/null`, pcts `15.7, 54.9, 25.5, 3.9`.
- Transform path: `_transform_era()` lines 400-509 derives school detail, zfills school to `0101`, normalizes grade to `08`, maps demographic/subject, casts counts, divides percentages by 100, and derives cumulatives.
- Gold: `year=2015/schools.parquet` row has `district_code=732`, `school_code=0101`, `grade_level=08`, `demographic=economically_disadvantaged`, `subject=mathematics`, `num_tested=102`, `num_distinguished_learner=NULL`, pcts `0.157, 0.549, 0.255, 0.039`, `pct_developing_learner_or_above=0.843`, `pct_proficient_learner_or_above=0.294`.
- Result: MATCH

### Check 2

- Bronze: `georgia_milestones_end_of_grade_eog_assessment_by_grade_2024.csv`, district `647`, school `0103`, grade `06`, `Students without Disabilities`, `Mathematics`: `NUM_TESTED_CNT=162`, `BEGIN_CNT=TFS/null`, `DEVELOPING_CNT=41`, `PROFICIENT_CNT=88`, `DISTINGUISHED_CNT=33`, pcts `0, 25.3, 54.3, 20.4`.
- Transform path: `transform_file()` lines 538-547 validates and drops `#ASSMT_CD`; `_transform_era()` lines 478-506 casts suppressed counts to NULL, scales percentages, and derives cumulative shares.
- Gold: `year=2024/schools.parquet` row has `num_tested=162`, `num_beginning_learner=NULL`, `num_developing_learner=41`, `num_proficient_learner=88`, `num_distinguished_learner=33`, pcts `0.0, 0.253, 0.543, 0.204`, `pct_developing_learner_or_above=1.0`, `pct_proficient_learner_or_above=0.747`.
- Result: MATCH

### Check 3

- Bronze: `georgia_milestones_end_of_grade_eog_assessment_by_grade_2022.csv`, state row, grade `03`, `Foster Care`, `Mathematics`: `NUM_TESTED_CNT=602`, level counts `200, 247, 130, 17`, pcts `33.2, 41.0, 21.6, 2.8`.
- Transform path: `_transform_era()` lines 400-426 nulls aggregate geography; lines 478-506 preserve published counts and percentages and derive cumulative percentages. Contract quality checks intentionally preserve state-level Foster Care shortfalls.
- Gold: `year=2022/states.parquet` row has null geography keys, `num_tested=602`, level-count sum `594`, pcts `0.332, 0.410, 0.216, 0.028`, `pct_developing_learner_or_above=0.654`, `pct_proficient_learner_or_above=0.244`.
- Result: MATCH

### Check 4

- Bronze: `georgia_milestones_end_of_grade_eog_assessment_by_grade_2024.csv`, state row, `#ASSMT_CD=EOG_by_GRADE`, grade `08`, `All Students`, `Physical Science`: `NUM_TESTED_CNT=40865`, counts `10462, 9607, 14188, 6608`, pcts `25.6, 23.5, 34.7, 16.2`.
- Transform path: `transform_file()` lines 538-547 validates/drops the Era 2 constant; `SUBJECT_MAP` lines 175-180 maps `Physical Science` to `physical_science`; geography nulling preserves the state aggregate as null district/school.
- Gold: `year=2024/states.parquet` row has no `#ASSMT_CD` column, `demographic=all`, `grade_level=08`, `subject=physical_science`, `num_tested=40865`, counts `10462, 9607, 14188, 6608`, pcts `0.256, 0.235, 0.347, 0.162`, cumulatives `0.744` and `0.509`.
- Result: MATCH

## Notes

- I did not read any existing `data-review-claude.md` or prior `data-review-codex.md`; no prior Codex review file existed at preflight.
- This review did not edit transform, bronze, contract, validator, manifest, or gold data.
- Foster Care share-sum deviations are confined to `foster_care` rows. A strict binary-float `abs(delta) > 0.02` query counts 283 rows in 2023 because one displayed sum is exactly `0.98`; using `> 0.0200000001` gives the documented 282. This does not affect served values or validation because the authored invariant excludes `foster_care`.
