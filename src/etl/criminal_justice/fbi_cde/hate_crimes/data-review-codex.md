# Data Review: hate_crimes

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze-to-gold aggregation, recodes, county attribution, contract, validator, and current parquet output reconcile with no must-fix issues.

## Summary

- Review date: 2026-07-02
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze checksum gate passed; transform mtime 2026-07-02T22:50:40Z is before manifest 2026-07-02T22:50:41Z, and validation timestamp 2026-07-02T22:51:13Z is after the manifest.

## Files Reviewed

- Transform: `src/etl/criminal_justice/fbi_cde/hate_crimes/transform.py`
- Contract: `contracts/criminal_justice/hate_crimes.odcs.yaml`
- Bronze files: `data/bronze/criminal_justice/fbi_cde/hate_crimes/hate_crime.zip` (`hate_crime/hate_crime.csv`, 265,834 national rows, 1,983 Georgia rows) plus `_provenance.md`
- Gold files: 68 parquet files, `year=1991` through `year=2024`, with `counties.parquet` and `states.parquet` in every year
- Manifest: `data/gold/criminal_justice/hate_crimes/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/hate_crimes/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/CLAUDE.md`, `src/etl/criminal_justice/CLAUDE.md`, relevant `src/utils/` helpers, and `src/etl/criminal_justice/fbi_cde/_nibrs_shared.py`

## Contract Verification

- Schema/parquet column match: PASS - validation confirms all 68 parquet files match the contract column names and order: `year`, `county_fips`, `bias_motivation`, `bias_category`, `incident_count`, `victim_count`, `known_offender_count`, `agencies_reporting`.
- Column roles and grain: PASS - contract grain is `year`, `county_fips`, `bias_motivation`, `bias_category`; `county_fips` is nullable for state rows; both categoricals are part of the key metric grain.
- Metric units and derived quality checks: PASS - all four metrics are `unit: count`; derived non-negative checks are present, with additional authored checks for minimum incident count, state coverage, bias-category dependency, and agency-reporting consistency.
- Categorical enums: PASS - `bias_category` contract enum matches the six values currently produced in gold; `bias_motivation` is enforced by the pinned transform vocabulary and manifest mapping, with 32 observed Georgia values and no unmapped values.
- Detail levels and layout metadata: PASS - contract declares `counties` and `states`, default `counties`, `path_template` `criminal_justice/hate_crimes/year={year}/{detail}.parquet`, and `year_range` 1991-2024, matching the current layout.
- Foreign-key descriptors: PASS - `county_fips` targets the global counties dimension; validator reports all 108 populated county keys resolve.
- Schema hash/version consistency: PASS - contract is `version: 1.0.0`, `status: active`, with schema hash `e296e679430a7aa5e2d66cead62d4c863e487bdecd4316a0acef08ed693c1a5a`; current parquet matches that schema.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp `2026-07-02T22:51:13.446844+00:00` is newer than manifest `generated_at` `2026-07-02T22:50:41.326032+00:00`; `passed` is true.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 19 pass, 0 fail, 1 warning; schema, grain uniqueness, all 13 contract quality SQL checks, county FK integrity, and canonical vocabulary passed.
- Validator warnings explained: PASS - the only warning is `victim_count year=2017: null_rate=41.7%`; bronze has 5 Georgia incidents with `total_individual_victims` NULL in 2017, and the transform intentionally nulls any aggregate cell containing an unreported victim count.
- section 15b quality-check coverage (cross-column invariants authored): PASS - checks cover non-empty output, count bounds, nonzero incident rows, state incident and known-offender coverage over county sums, bias motivation determining category, and agency-reporting consistency. Victim totals were spot-checked separately because source NULL propagation intentionally makes some state/county victim sums non-comparable.

## Manifest Verification

- Files processed coverage: PASS - current bronze inventory is one analyzed zip; manifest records `hate_crime.zip` with 265,834 rows and the expected 28-column master-file schema. Row-count accounting covers all years 1991-2024.
- Categorical and recode coverage: PASS - `bias_category`, `bias_motivation`, and `county_fips` all have `unmapped_count: 0`. The manifest records 32 observed Georgia atomic bias labels, six produced bias categories, and 224 ORI-to-county mappings.
- Row-count reconciliation: PASS - manifest total is 265,834 national bronze rows, 263,851 explicitly filtered non-Georgia rows, and 1,299 final gold rows. Independent reconstruction from the 1,983 Georgia rows produced 1,999 incident-bias pairs and exactly the same 1,299 gold rows.
- Metric stats sanity: PASS - count metrics are non-negative; `incident_count` min is 1, `known_offender_count` min is 0, `agencies_reporting` min is 1, and `victim_count` NULLs are limited to the documented 2017-2019 unreported victim-count source rows.

## Row and Join Accounting

- Bronze file/year disposition: PASS - the national master file spans 1991-2024; all rows are either filtered as non-Georgia or included in Georgia aggregation.
- Filter accounting: PASS - 263,851 national non-Georgia rows are explicitly recorded as `non_georgia_state_row`; no Georgia rows are filtered out.
- Join accounting: PASS - ORI crosswalk has 0 duplicate ORIs; all 224 Georgia hate-crime ORIs match; 16 multi-county ORIs covering 600 incidents are attributed to the documented primary county; 0 current incidents have NULL county from statewide agencies.
- Deduplication accounting: PASS - Georgia `incident_id` is unique 1,983/1,983; exploded incident-bias pairs have 0 duplicate `(incident_id, bias_desc)` pairs; final natural grain has 0 duplicate rows.
- Aggregation/unpivot accounting: PASS - 15 multi-bias incidents expand Georgia incident rows from 1,983 to 1,999 incident-bias pairs. A null-safe independent aggregation by year, county/state, bias motivation, and category matched gold exactly: 1,299 rows, 0 missing rows, 0 extra rows, 0 metric mismatches.

## Reconciliation Checks

- Artifact freshness: PASS - bronze checksum gate passed; manifest and validation are current relative to `transform.py`.
- Contract freshness: PASS - contract was emitted from the current transform/gold run; no `_metadata.json` dependency was used.
- Year coverage: PASS - gold contains every year 1991-2024 and no unexpected years.
- Row preservation: PASS - all 1,983 Georgia incidents are represented in county and state aggregates; multi-bias rows are intentionally represented once per atomic bias.
- Column coverage: PASS - gold columns trace to `data_year`, ORI crosswalk `county_fips`, `bias_desc`, `incident_id`, `total_individual_victims`, `total_offender_count`, and distinct ORI counts. Excluded bronze fields are dimension attributes, redundant flags, misleading entity-count fields, NIBRS-only sparse splits, or intentionally out-of-scope offender demographics.
- Recode accuracy: PASS - reviewed all 35 map entries in `BIAS_VOCAB`; 32 are observed in Georgia, and their gold labels/categories match FBI hate-crime semantics.
- Asian-family demographic recodes (section 5b): N/A - there is no `demographic` column. The source separates `Anti-Asian` and `Anti-Native Hawaiian or Other Pacific Islander` as distinct bias motivations, and offender race is not served.
- Demographic mutual exclusivity (section 5a - no rollup row alongside split source rows in the same category): N/A - no demographics are emitted.
- Demographic collision aggregation before dedup (section 5): N/A - no demographic normalization is performed.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - actual parquet order is `year`, `county_fips`, `bias_motivation`, `bias_category`, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, section 11/12): PASS - no forbidden fact columns appear in parquet; `detail_level` is encoded by filename.
- Canonical column vocabulary (section 16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): N/A - topic uses criminal-justice count metrics and no education-specific vocabulary.
- Shared categorical utilities applied (section 10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no grade or academic subject columns.
- Tidy long format (section 9 - no demographics/years/components as column names): PASS - bias motivation/category are row values, years are partitions, and metrics are long-form aggregate counts.
- FK keys present in dimension tables (section 13 - `district_code`, `school_code`, `demographic`): PASS - `county_fips` resolves in the counties dimension for all 108 populated keys.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - row grain is stable, `bias_motivation` and `bias_category` are filterable categoricals, and county joins derive from the contract FK.
- Standards compliance (catch-all for section 1-16 items not enumerated above): PASS - source suppression semantics, null victim-count handling, primary county attribution, voluntary-reporting limitations, and absent county-year interpretation are documented in the contract and reflected in gold.

## Spot Checks

### Check 1

- Bronze: `hate_crime.zip:hate_crime/hate_crime.csv`, incident `1547665`, year 2024, ORI `GA0110000`, Bibb, `bias_desc=Anti-White`, `total_individual_victims=1`, `total_offender_count=2`.
- Transform path: `_attach_county` lines 376-435 maps ORI to `county_fips=13021`; `_explode_bias` lines 438-494 maps `Anti-White` to `anti_white`; `_aggregate` lines 527-568 groups to county/state rows.
- Gold: `year=2024/counties.parquet`, `county_fips=13021`, `bias_motivation=anti_white`, `incident_count=1`, `victim_count=1`, `known_offender_count=2`, `agencies_reporting=1`.
- Result: MATCH

### Check 2

- Bronze: incident `190211`, year 2017, ORI `GA0670200`, Gwinnett County Police Department, `bias_desc=Anti-Islamic (Muslim);Anti-Multiple Races, Group`, `total_individual_victims=100`, `total_offender_count=0`.
- Transform path: `_explode_bias` lines 446-494 splits the semicolon-delimited bias field and maps both atomic labels; `_aggregate` lines 536-543 counts the incident once under each bias and preserves the conceivable 100-victim value.
- Gold: `year=2017/counties.parquet`, `county_fips=13135`, rows `anti_islamic` and `anti_multiple_races_group` both have `incident_count=1`, `victim_count=100`, `known_offender_count=0`, `agencies_reporting=1`.
- Result: MATCH

### Check 3

- Bronze: incidents `190212` and `190581` have `total_individual_victims=NULL` in 2017, with `bias_desc=Anti-Asian` and `Anti-Protestant`.
- Transform path: `_load_georgia_incidents` lines 340-365 casts `total_individual_victims` with `strict=False`; `_aggregate` lines 538-541 sets aggregate `victim_count` to NULL when any contributing incident victim count is NULL.
- Gold: `year=2017/states.parquet` has `anti_asian` with `incident_count=2`, `victim_count=NULL`, `known_offender_count=2`, and `anti_protestant` with `incident_count=1`, `victim_count=NULL`, `known_offender_count=0`.
- Result: MATCH

### Check 4

- Bronze: incident `144691`, year 2010, ORI `GAAPD0000`, Atlanta, `bias_desc=Anti-Gay (Male)`, `total_individual_victims=2`, `total_offender_count=1`.
- Transform path: `_attach_county` lines 405-435 applies primary-county attribution for multi-county agencies, including Atlanta PD to Fulton; `_explode_bias` lines 478-483 maps to `anti_gay_male` and `sexual_orientation`.
- Gold: `year=2010/counties.parquet`, `county_fips=13121`, `bias_motivation=anti_gay_male`, `incident_count=1`, `victim_count=2`, `known_offender_count=1`, `agencies_reporting=1`.
- Result: MATCH

## Notes

- I did not read any prior `data-review-claude.md` or `data-review-codex.md` before completing the findings.
- One exploratory state-row comparison initially used a normal join and did not match NULL `county_fips` keys; rerunning with a null-safe state key showed 0 missing rows, 0 extra rows, and 0 metric mismatches.
- No required fixes were found.
