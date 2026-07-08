# Data Review: sat_scores_highest

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: contract, manifest, validation, bronze traces, and gold parquet all support the current transform; no bronze-to-gold accuracy fixes are required.

## Summary

- Review date: 2026-06-10
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze checksum gate passed for all 22 files; transform mtime 2026-06-10T22:07:52Z is older than manifest generated_at 2026-06-10T22:09:08Z; validation timestamp 2026-06-10T22:09:08Z is newer than the manifest and passed.

## Files Reviewed

- Transform: `src/etl/education/gosa/sat_scores_highest/transform.py`
- Contract: `contracts/education/sat_scores_highest.odcs.yaml`
- Bronze files: 22 files under `data/bronze/education/gosa/sat_scores_highest/`, spanning `sat_scores_highest_2004.csv` through `sat_scores_highest_2024.csv`, including both 2016 old/new format files
- Gold files: 63 parquet files under `data/gold/education/sat_scores_highest/year=*/` (schools, districts, states for each year 2004-2024)
- Manifest: `data/gold/education/sat_scores_highest/_transform_manifest.json`
- Validation report: `data/gold/education/sat_scores_highest/_validation.json`
- Supporting docs: `docs/codex-review-contract.md`, `docs/contract-creation.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`, and selected sibling context from `src/etl/education/gosa/sat_scores_recent/transform.py`

## Contract Verification

- Schema/parquet column match: PASS - contract properties and every sampled parquet use `year`, `district_code`, `school_code`, `demographic`, `test_component`, `num_tested`, `avg_score` in that order.
- Column roles and grain: PASS - roles are `year`, `fk_district`, `fk_school`, `fk_demographic`, `categorical`, `metric`, `metric`; primary key grain is year plus geography, demographic, and test_component.
- Metric units and derived quality checks: PASS - `num_tested` is `unit: count` with a non-negative check; `avg_score` is `unit: score` with component-specific quality SQL because SAT component scales differ.
- Categorical enums: PASS - contract enums match manifest and actual gold values for 10 demographics and 14 test components.
- Detail levels and layout metadata: PASS - contract lists `schools`, `districts`, `states`, path template `education/sat_scores_highest/year={year}/{detail}.parquet`, and available years 2004-2024.
- Foreign-key descriptors: PASS - district, composite school, and demographic FK descriptors match the dimension contracts; validator reports all populated FK keys resolve.
- Schema hash/version consistency: PASS - contract is `version: 1.0.0` with schema_hash `54310a68e15a2192a2cc29d30867e593e87667bc641b53c7e54127633abfa3e7`, coherent with the current schema and gold layout.

## Validator Verification

- `_validation.json` fresh + passing: PASS - `passed: true`; validation timestamp 2026-06-10T22:09:08.259696 is newer than manifest generated_at 2026-06-10T22:09:08.172049.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 20 checks passed, including `contract_parquet_schema`, `grain_uniqueness`, `contract_quality_sql`, `foreign_keys`, `canonical_vocabulary`, and geography nulling.
- Validator warnings explained: PASS - the single warning is null-rate spikes. Bronze TFS counts explain the 2021-2023 `num_tested`/`avg_score` spikes, and 2005-2010 `avg_score` nulls are structural count-only subgroup rows or blank wide cells.
- Quality-check coverage (cross-column invariants authored): PASS - contract quality SQL covers component score ranges, verbal_math equals reading plus mathematics, component year coverage, post-2010 demographic restriction, subgroup score years, avg_score requiring positive num_tested, state count completeness, and fractional counts only on `combined_test_score`.

## Manifest Verification

- Files processed coverage: PASS - manifest lists all 22 current bronze data files and no extras; bronze freshness reports all checksums match and no unanalyzed files.
- Categorical and recode coverage: PASS - `demographic` and `test_component` both have `unmapped_count: 0`; manifest records `Asian -> asian_pacific_islander`, `O -> other`, `R -> race_unknown`, old/new SAT components, and the double-space Reading/WritLang source labels.
- Row-count reconciliation: PASS - manifest totals are 44,424 bronze rows and 174,263 gold rows. Explicit filter accounting records 59,057 wide-era non-observations: 59,052 empty demographic/component cells, 3 Era 3 sub-header rows, and 2 corrupted partial duplicate fragments.
- Metric stats sanity: PASS - `num_tested` is non-negative; `avg_score` has no remaining values outside authored component ranges; manifest records 20 `avg_score` masks for impossible SAT values while preserving row and count metrics.

## Row and Join Accounting

- Bronze file/year disposition: PASS - every current bronze file is processed; filename years match `LONG_SCHOOL_YEAR` for 2011-2024; both 2016 files are retained because old-SAT and redesigned-SAT component vocabularies are disjoint.
- Filter accounting: PASS - wide blank cells are explicitly elided as non-observations; the three 2008-2010 sub-header rows and two corrupted 2004 fragments are recorded. National columns are intentionally out of scope under education detail-level rules.
- Join accounting: N/A - the transform does not join external lookup tables; FK integrity is checked post-export by the validator against dimension tables.
- Deduplication accounting: PASS - manual duplicate-key audit found 72 duplicate 2004 generated cell rows, all metric-identical and collapsing to 13,089 unique 2004 gold rows. No divergent duplicate key groups were found.
- Aggregation/unpivot accounting: PASS - 2004-2010 wide cells unpivot as expected; 2011-2024 school rows are 1:1 and district/state rows equal unique district-component and component counts. 2024 modal-pair rollups choose source-backed official context pairs and avoid the three mixed-up Combined rows.

## Reconciliation Checks

- Artifact freshness: PASS - bronze, manifest, validation, contract, and gold are current relative to each other.
- Contract freshness: PASS - contract is emitted from the transform and matches the current parquet; no `_metadata.json` dependency was used.
- Year coverage: PASS - gold has exactly years 2004-2024 with no gaps; 2016 contains both old and redesigned SAT components.
- Row preservation: PASS - wide-era expansions and tidy-era district/state materialization reconcile to gold counts; dedup only removes identical 2004 repeats.
- Column coverage: PASS - fact keys, `demographic`, `test_component`, `num_tested`, and `avg_score` have source-backed lineage; name, school-year, national, and constant assessment fields are validly excluded.
- Recode accuracy: PASS - old `High Total` maps to `verbal_math` based on the source identity `High Total = High Verbal + High Math`; 2011-2016 `Combined` remains the 600-2400 old-SAT total; redesigned components stay distinct.
- Asian-family demographic recodes: PASS - actual bronze/profile search found no Pacific Islander/NHPI label; sibling SAT source uses the same combined convention; gold emits `asian_pacific_islander` only.
- Demographic mutual exclusivity: PASS - representative groups contain one combined Asian/Pacific Islander bucket and never also contain `asian` or `pacific_islander`; 2011+ rows are `all` only.
- Demographic collision aggregation before dedup: N/A - each raw demographic token maps to a distinct canonical key; no alias collision was observed.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics): PASS - parquet order is `year`, `district_code`, `school_code`, `demographic`, `test_component`, `num_tested`, `avg_score`.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs): PASS - exported parquet contains no forbidden fact-table columns.
- Canonical column vocabulary: PASS - uses `test_component`, `num_tested`, and `avg_score`; `num_tested` is Float64 under the documented SAT exception.
- Shared categorical utilities applied: N/A - no `grade_level` or academic `subject` column exists; demographics use the canonical alias table with a topic-local Asian/Pacific Islander remap.
- Tidy long format: PASS - demographics and test components are rows, not metric column names; no year-keyed or component-wide columns remain in gold.
- FK keys present in dimension tables: PASS - validator reports all 193 district keys, all 578 composite school keys, and all 10 demographic keys resolve.
- Contract-driven API semantics: PASS - every categorical is filterable by contract; FK joins and row grain derive from the ODCS metadata.
- Standards compliance: PASS - suppression markers become NULL, aggregate geography is nulled, IDs preserve leading zeros, metric units are authored, range defects are NULLed rather than row-dropped, and manifest/validation outputs are present.

## Spot Checks

### Check 1

- Bronze: `data/bronze/education/gosa/sat_scores_highest/sat_scores_highest_2004.csv`, `ALL:ALL` has High Total All Students 999, High Verbal All Students 499, High Math All Students 500, Number Taken All Students 46828; Asian fields are 1068/503/565 with count 1926.
- Transform path: `_transform_era1()` and `_unpivot_era123()` in `src/etl/education/gosa/sat_scores_highest/transform.py:617` and `src/etl/education/gosa/sat_scores_highest/transform.py:532`, with `_raw_demographic_label()` at `src/etl/education/gosa/sat_scores_highest/transform.py:358`.
- Gold: 2004 state rows preserve all-student `verbal_math=999`, `reading=499`, `mathematics=500`, `num_tested=46828`; Asian maps to `asian_pacific_islander` with 1068/503/565 and count 1926.
- Result: MATCH

### Check 2

- Bronze: `data/bronze/education/gosa/sat_scores_highest/sat_scores_highest_2007.xls`, `601:103` has `High Total0=944`, `High Verbal0=474`, `High Math0=470`, `Number Taken0=58`, and Asian high-score cells are `NULL` with `Number TakenA=0`.
- Transform path: `_transform_era23()` in `src/etl/education/gosa/sat_scores_highest/transform.py:656`.
- Gold: 2007 `district_code=601`, `school_code=0103`, `demographic=all` has verbal_math/reading/mathematics scores 944/474/470 and count 58; `demographic=asian_pacific_islander` has three count rows with `num_tested=0` and `avg_score=NULL`.
- Result: MATCH

### Check 3

- Bronze: `data/bronze/education/gosa/sat_scores_highest/sat_scores_highest_2008.xls` first row is the secondary header/null-ID row; next `601:103` row has `High Total0=981`, `High Verbal0=484`, `High Math0=497`, `High Writing0=473`, `Number Taken0=60`.
- Transform path: `_split_compound_id()` records/drops null IDs at `src/etl/education/gosa/sat_scores_highest/transform.py:462`, then `_transform_era23()`.
- Gold: 2008 `601/0103/all` has verbal_math 981, reading 484, mathematics 497, writing 473, each with `num_tested=60`.
- Result: MATCH

### Check 4

- Bronze: `data/bronze/education/gosa/sat_scores_highest/sat_scores_highest_2011.csv`, `601/103` Combined row has school and district count/score 85/1268 and state count/score 84240/1338.
- Transform path: `_transform_era45()` and `_modal_pair_rollup()` in `src/etl/education/gosa/sat_scores_highest/transform.py:862` and `src/etl/education/gosa/sat_scores_highest/transform.py:726`.
- Gold: 2011 `combined` rows preserve school `601/0103` 85/1268, district `601` 85/1268, and state 84240/1338.
- Result: MATCH

### Check 5

- Bronze: `data/bronze/education/gosa/sat_scores_highest/sat_scores_highest_2016_new_format.csv`, `601/103` Combined Test Score has state `num_tested=28212.33333`, state `avg_score=1084`, and school/district 34/1055.
- Transform path: `TEST_COMPONENT_MAP` and `_transform_era45()` in `src/etl/education/gosa/sat_scores_highest/transform.py:191` and `src/etl/education/gosa/sat_scores_highest/transform.py:862`.
- Gold: 2016 `combined_test_score` preserves school and district 34/1055 and state 28212.33333/1084; `num_tested` remains Float64.
- Result: MATCH

### Check 6

- Bronze: `data/bronze/education/gosa/sat_scores_highest/sat_scores_highest_2024.csv`, three Combined Test Score rows without school metrics carry Math-scale context pairs: `675:4050` district 1011/470 and state 37143/505.4; `705:0108` district 63/469.4; `736:0100` district 83/473.6.
- Transform path: evidence-restricted modal pair vote in `_modal_pair_rollup()` at `src/etl/education/gosa/sat_scores_highest/transform.py:726`.
- Gold: 2024 `combined_test_score` state is 32979/1043.6, and affected district rows use the modal school-supported pairs: 675 -> 809.7/987.8, 705 -> 41.7/997.4, 736 -> 63.7/1019.7.
- Result: MATCH

### Check 7

- Bronze: 2009 Heritage High `722:176` publishes impossible SAT averages reading 1022, mathematics 995, writing 976, and verbal_math 2017; 2011-2015 old-SAT writing includes 10 values below the 200 floor.
- Transform path: `_null_invalid_sat_scores()` in `src/etl/education/gosa/sat_scores_highest/transform.py:1032`.
- Gold: affected rows keep `num_tested` but set `avg_score=NULL`; no gold row remains outside the authored component ranges.
- Result: MATCH

## Needs Follow-up

- Auditability only: the 2004 file has 72 non-empty duplicate generated cell rows from 25 repeated complete IDs; manual audit proved all duplicate metrics are identical and gold dedup is value-preserving, but the dedup count is not surfaced in `_transform_manifest.json`.
- Auditability only: the 2024 modal-pair repair is correct by manual vote checks, but the three excluded no-school-evidence Combined rows are not recorded in the manifest's `reclassified` section because the evidence restriction removes them before loser counting.

## Notes

- No required fixes were found. The two follow-up items above do not change served gold values under the inspected bronze inventory; they would make future manifest-based audits easier.
- I did not read any prior `data-review-claude.md` or existing `data-review-codex.md` before forming the findings.
