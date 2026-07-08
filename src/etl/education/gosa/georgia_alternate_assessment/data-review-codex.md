# Data Review: georgia_alternate_assessment_gaa

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Current bronze, manifest, contract, validation report, and gold parquet reconcile; no must-fix bronze-to-gold accuracy defects found.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH — `scripts/check_bronze_freshness.py education gosa georgia_alternate_assessment_gaa` passed; transform mtime `2026-06-12T03:37:55Z`, manifest `generated_at` `2026-06-12T03:38:12Z`, validation timestamp `2026-06-12T03:38:12Z`, and validation passed.

## Files Reviewed

- Transform: `src/etl/education/gosa/georgia_alternate_assessment_gaa/transform.py`
- Contract: `contracts/education/georgia_alternate_assessment_gaa.odcs.yaml`
- Bronze files: 16 files, `georgia_alternate_assessment_gaa_2004.csv` through `georgia_alternate_assessment_gaa_2024.csv` for years 2004-2007, 2011-2019, and 2022-2024
- Gold files: 48 parquet files, three detail files (`schools.parquet`, `districts.parquet`, `states.parquet`) for each of 16 years
- Manifest: `data/gold/education/georgia_alternate_assessment_gaa/_transform_manifest.json`
- Validation report: `data/gold/education/georgia_alternate_assessment_gaa/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`, and relevant shared utilities in `src/utils/`

## Contract Verification

- Schema/parquet column match: PASS — all 17 parquet columns match contract `schema[0].properties[]` in order.
- Column roles and grain: PASS — grain is `year`, `district_code`, `school_code`, `demographic`, `subject`; validator reports one row per grain tuple.
- Metric units and derived quality checks: PASS — count metrics carry `unit: count`, percentage metrics carry `unit: proportion`, and the object declares 29 SQL quality checks including non-negativity, unit interval, row-shape, and formula checks.
- Categorical enums: PASS — `demographic` enum has the 22 gold demographic values and `subject` enum has the four subject values observed in gold.
- Detail levels and layout metadata: PASS — detail levels are `schools`, `districts`, `states`; path template is `education/georgia_alternate_assessment_gaa/year={year}/{detail}.parquet`.
- Foreign-key descriptors: PASS — contract declares FKs for `district_code`, composite `school_code` via `(district_code, school_code)`, and `demographic`.
- Schema hash/version consistency: PASS — contract version is `1.0.0`; schema hash custom property is `7de73c05cdcc8a440c9ace026d54dec538a2c962e211f9425a616a7bc3205c9e`.

## Validator Verification

- `_validation.json` fresh + passing: PASS — validation timestamp is not older than the manifest and `passed` is `true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS — validation summary is 20 pass, 0 fail, 1 warning; schema, grain, 29 contract SQL checks, FKs, canonical vocabulary, and geography nulling passed.
- Validator warnings explained: PASS — null-rate spikes are expected from documented regime changes: 2004-2007 participation-only rows have null achievement metrics; 2011+ lacks `enrollment_ayp_grades`; 2011-2018 lacks distinguished tier; 2024 suppresses most count fields while retaining percentages.
- §15b quality-check coverage (cross-column invariants authored): PASS — authored checks cover participation-era row shape, achievement-era row shape, absent 3-tier distinguished metrics, count-vs-tested invariants, 2011-2019 partition sums, 2022+ upper-bound sums, cumulative formulas, and 2024 suppressed-count percentage behavior.

## Manifest Verification

- Files processed coverage: PASS — manifest lists all 16 current bronze data files; bronze freshness check confirms checksums match and no unanalyzed files exist.
- Categorical and recode coverage: PASS — `demographic` and `subject` each have `unmapped_count: 0`; manifest values match bronze distinct values and gold distinct values.
- Row-count reconciliation: PASS — manifest reports 248,479 bronze rows, 248,341 gold rows, and 138 explicitly filtered 2004 rows: 1 null trailing row, 136 exact duplicates, and 1 all-null placeholder twin.
- Metric stats sanity: PASS — percentage metrics are on 0-1 scale; count metrics are non-negative; expected null profiles match documented source eras.

## Row and Join Accounting

- Bronze file/year disposition: PASS — all current bronze files are processed. Expected gaps are 2008-2010 and 2020-2021, documented as source/COVID gaps.
- Filter accounting: PASS — the only filters are 2004-specific repairs: one fully null trailing row, 136 duplicate copies, and one all-null placeholder twin for `647:3058`.
- Join accounting: N/A — transform does not join external lookup tables; FK resolution is validated post-export against dimensions.
- Deduplication accounting: PASS — collision guard runs before dedup; actual duplicate grain count in gold is 0.
- Aggregation/unpivot accounting: PASS — no row-collapsing aggregation or wide unpivot is performed; row shape is one output row per source row except documented 2004 repairs.

## Reconciliation Checks

- Artifact freshness: PASS — bronze, manifest, validation, contract, and gold agree.
- Contract freshness: PASS — contract was emitted from the transform run and gold schema; no `_metadata.json` dependency.
- Year coverage: PASS — gold years are exactly 2004, 2005, 2006, 2007, 2011-2019, and 2022-2024.
- Row preservation: PASS — all non-filtered source rows are represented in gold with expected 1:1 row counts per year.
- Column coverage: PASS — gold columns trace to bronze columns, filename year, documented constants (`demographic='all'` for 2004-2007), or derived cumulative formulas.
- Recode accuracy: PASS — subject recodes and demographic aliases match actual bronze values.
- Asian-family demographic recodes (§5b): PASS — bronze publishes separate `Asian` and `Native Hawaiian or Other Pacific Islander` rows in later files; gold emits split `asian` and `pacific_islander`, with no `asian_pacific_islander`.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): PASS — no group contains `asian_pacific_islander` alongside `asian` or `pacific_islander`; source-published non-additive military keys are documented.
- Demographic collision aggregation before dedup (§5): N/A — every observed label maps to a distinct canonical key; collision guard protects future alias changes.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS — parquet order is `year`, `district_code`, `school_code`, `demographic`, `subject`, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS — no forbidden columns appear in parquet.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS — GAA uses canonical `subject`, `num_tested`, proficiency-band count/share names, and `_or_above` cumulative names.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): PASS — `apply_subject_normalization` and `normalize_demographic_column` are used; no `grade_level` column applies.
- Tidy long format (§9 — no demographics/years/components as column names): PASS — achievement rows are long by `(entity x demographic x subject)`.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS — direct anti-joins found 0 missing district keys, 0 missing composite school keys, and 0 missing demographic keys.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS — grain, `subject` filter enum, demographic FK, and geography FKs are contract-derived and validation-passing.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS — no accuracy-impacting standards defect found.

## Spot Checks

### Check 1

- Bronze: `georgia_alternate_assessment_gaa_2006.csv`, `SysSchoolID=601:103`, `School Name=Appling County High School`, enrollment `199`, tested `10`.
- Transform path: `_transform_era12()` parses `district:school`, zfills school code, assigns `demographic='all'`, `subject=NULL`, and casts the two participation metrics.
- Gold: `year=2006`, `district_code=601`, `school_code=0103`, `demographic=all`, `subject=NULL`, `enrollment_ayp_grades=199`, `num_tested=10`, achievement metrics NULL.
- Result: MATCH

### Check 2

- Bronze: `georgia_alternate_assessment_gaa_2015.csv`, `644/0897`, `Not Limited English Proficient`, `English Language Arts`, `NUM_TESTED_CNT=11`, `LIMITED_CNT=0`, `PARTIAL_CNT=4`, `ADEQUATE_CNT=7`, `LIMITED_PERCENT=0`, `PARTIAL_PERCENT=36.4`, `ADEQUATE_PERCENT=63.6`.
- Transform path: `_transform_era36()` maps subject and demographic, drops absent 3-tier distinguished signal to NULL, divides percentages by 100, and derives 3-tier cumulatives.
- Gold: `district_code=644`, `school_code=0897`, `demographic=not_english_learners`, `subject=english_language_arts`, `num_tested=11`, counts `0/4/7/NULL`, percentages `0.0/0.364/0.636/NULL`, `pct_developing_learner_or_above=1.0`, `pct_proficient_learner_or_above=0.636`.
- Result: MATCH

### Check 3

- Bronze: `georgia_alternate_assessment_gaa_2019.csv`, `601/177`, `All Students`, `English Language Arts`, `NUM_TESTED_CNT=16`, Level counts `2/4/9/1`, Level percents `12.5/25/56.3/6.3`.
- Transform path: `_transform_era36()` uses Era 4 maps, zfills `INSTN_NUMBER` to `0177`, divides percentages by 100, and derives 4-tier cumulatives.
- Gold: `district_code=601`, `school_code=0177`, `demographic=all`, `subject=english_language_arts`, counts `2/4/9/1`, percentages `0.125/0.25/0.563/0.063`, `pct_developing_learner_or_above=0.876`, `pct_proficient_learner_or_above=0.626`; formula diffs were 0.0.
- Result: MATCH

### Check 4

- Bronze: `georgia_alternate_assessment_gaa_2024.csv`, `601/0103`, `All Students`, `English Language Arts`, `NUM_TESTED_CNT=TFS/null`, level counts null, percents `0/0/100/0`.
- Transform path: shared reader maps `TFS` to NULL; `_transform_era36()` preserves published percentages, divides by 100, and derives cumulatives even when counts are suppressed.
- Gold: `num_tested=NULL`, level counts NULL, percentages `0.0/0.0/1.0/0.0`, `pct_developing_learner_or_above=1.0`, `pct_proficient_learner_or_above=1.0`.
- Result: MATCH

### Check 5

- Bronze: `georgia_alternate_assessment_gaa_2004.csv` has raw 2,358 rows, including 1 null-id trailing row, 136 duplicate copies, and two `647:3058` rows where one is all-null metrics and one has `enrollment=406`, `tested=10`.
- Transform path: `_transform_era12()` drops the null-id row, de-duplicates exact duplicate rows, and drops only the all-null placeholder twin before the collision guard.
- Gold: year 2004 has 2,220 rows, matching `2358 - 1 - 136 - 1`; the populated `647/3058` row is retained.
- Result: MATCH

## Notes

- No required fixes were identified.
- Validation warnings were reviewed and are source/era-shape artifacts rather than transform defects.
- The contract custom `schema_hash` is top-level `customProperties`, not a schema-object custom property.
