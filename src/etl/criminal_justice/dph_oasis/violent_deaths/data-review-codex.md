# Data Review: violent_deaths

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Contract, manifest, validation, bronze inventory, and gold values reconcile; no must-fix transform defects found.

## Summary

- Review date: 2026-07-03
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze checksum gate passed for all 20 profiled CSVs; transform mtime `2026-07-03T00:35:48.469512+00:00`, manifest `generated_at` `2026-07-03T00:35:49.142044+00:00`, validation timestamp `2026-07-03T00:36:26.434030+00:00`, validation passed.

## Files Reviewed

- Transform: `src/etl/criminal_justice/dph_oasis/violent_deaths/transform.py`
- Shared helpers: `src/etl/criminal_justice/dph_oasis/_oasis_shared.py`
- Contract: `contracts/criminal_justice/violent_deaths.odcs.yaml`
- Bronze files: 20 CSVs under `data/bronze/criminal_justice/dph_oasis/violent_deaths/`; 12 ingested county/race/sex files and 8 documented deferred age/ethnicity files.
- Gold files: 62 parquet files under `data/gold/criminal_justice/violent_deaths/year=1994` through `year=2024`, each with `counties.parquet` and `states.parquet`.
- Manifest: `data/gold/criminal_justice/violent_deaths/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/violent_deaths/_validation.json`
- Supporting docs: `STATUS.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/CLAUDE.md`, `src/etl/criminal_justice/CLAUDE.md`, `docs/contract-creation.md`, `docs/codex-review-contract.md`, data-cleaning standards and review workflow skills, and `data/bronze/criminal_justice/dph_oasis/violent_deaths/bronze-data-structure.md`.

## Contract Verification

- Schema/parquet column match: PASS - contract properties exactly match gold parquet order: `year`, `county_fips`, `demographic`, `cause_of_death`, `icd_revision`, `deaths`, `death_rate_per_100k`, `age_adjusted_death_rate_per_100k`.
- Column roles and grain: PASS - grain is `year`, `county_fips`, `demographic`, `cause_of_death`, `icd_revision`; state rows use NULL `county_fips`.
- Metric units and derived quality checks: PASS - `deaths` is `unit: count`; per-100k rate metrics intentionally omit `unit` and are guarded by authored non-negative and null-semantics quality SQL.
- Categorical enums: PASS - contract enums match manifest and gold for `demographic`, `cause_of_death`, and `icd_revision`.
- Detail levels and layout metadata: PASS - contract declares `counties` and `states`, default `counties`, partition column `year`, and path template `criminal_justice/violent_deaths/year={year}/{detail}.parquet`.
- Foreign-key descriptors: PASS - `county_fips -> counties` and `demographic -> demographics` are present; validation confirms all 159 counties and all 10 demographic keys resolve.
- Schema hash/version consistency: PASS - contract version is `1.0.0`; schema hash is `5f4f9f11a6d02a12b211f3e02b0a72ae9f0880b2cd0c1f12e9b72a03ab2b63a0`; year range is `1994-2024`.

## Validator Verification

- `_validation.json` fresh + passing: PASS - timestamp `2026-07-03T00:36:26.434030+00:00` is after manifest generation and `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 20 pass, 0 fail, 0 warning; `contract_parquet_schema`, `grain_uniqueness`, `contract_quality_sql`, `foreign_keys`, and `canonical_vocabulary` all passed.
- Validator warnings explained: N/A - validation reported no warnings.
- section 15b quality-check coverage (cross-column invariants authored): PASS - contract includes 16 checks covering non-empty data, enum vocabularies, non-negative metrics, suppression null semantics, zero-death rate semantics, state-only demographics, ICD revision/year partition, county death sums, race and sex partitions, full 159-county grid, and 10-row state demographic grid.

## Manifest Verification

- Files processed coverage: PASS - 12 ingested files in `files_processed` match the county, state-race, and state-sex layouts for four causes. The 8 state-age/state-ethnicity CSVs are present in bronze but intentionally deferred by transform lines 366-374 and documented in the contract limitations.
- Categorical and recode coverage: PASS - `cause_of_death`, `demographic`, and `icd_revision` all have `unmapped_count: 0`; race uses split `asian` and `pacific_islander` values from separate bronze labels.
- Row-count reconciliation: PASS - manifest `total_bronze` 22,272, `total_filtered` 1,316, `total_gold` 20,956. Explicit filters account for 1,068 derived rows; the remaining 248 are the expected duplicate statewide `all` rows from county/race/sex layouts, asserted by the transform before dedup.
- Metric stats sanity: PASS - final gold has `deaths` range 0-1,659 and per-100k rate ranges 0-89.365505 crude and 0-88.605439 age-adjusted after sentinel nulling; no negative rates survive.

## Row and Join Accounting

- Bronze file/year disposition: PASS - all 20 profiled CSV checksums match. County/race/sex files are processed for 1994-2024; age and ethnicity files are intentionally read out of scope for v1 because age needs demographic dimension expansion and ethnicity overlaps the race axis.
- Filter accounting: PASS - per year, 12 `selected_years_total` rows are filtered; one `County Summary` row per cause-year, one `Selected Races Total` row per cause-year, and one `Selected Sexes Total` row per cause-year are filtered after equality assertions. In 2024 the manifest also records the all-years total rows under the max year, explaining the larger filtered count.
- Join accounting: N/A - this transform performs no merge/join enrichment; county FIPS and demographics are source-derived and validated as FKs after export.
- Deduplication accounting: PASS - duplicate statewide `all` rows are reconciled by `assert_no_natural_key_collisions()` and deduped via `deduplicate_by_levels`; expected removed count is 248 and actual gold has 0 duplicate natural keys.
- Aggregation/unpivot accounting: PASS - no derived aggregation is used for served rows. Duplicate total rows are dropped only after equality checks; published county/race/sex totals reconcile directly to state totals.

## Reconciliation Checks

- Artifact freshness: PASS - bronze checksums match and manifest/validation are fresh relative to transform.py.
- Contract freshness: PASS - contract mtime is immediately after manifest generation and before validation; no `_metadata.json` dependency.
- Year coverage: PASS - bronze and gold cover 1994-2024 with no gaps; gold has 31 partitions and contract `available_years` lists 1994-2024.
- Row preservation: PASS - actual gold has 636 county rows and 40 state rows per year: 159 counties x 4 causes plus 10 state demographics x 4 causes.
- Column coverage: PASS - all served fact keys, categoricals, and metrics trace to bronze columns or filename/year constants; deferred age/ethnicity columns are documented as not served in v1.
- Recode accuracy: PASS - `homicide`, `suicide`, `legal_intervention`, and `accidental_shooting` derive from filename slugs; `icd9` applies to 1994-1998 and `icd10` to 1999-2024; demographic labels map through the shared aliases.
- Asian-family demographic recodes (section 5b): PASS - bronze publishes separate `Asian` and `Native Hawaiian or Other Pacific Islander` rows and no combined Asian/Pacific Islander row; gold preserves `asian` and `pacific_islander`. Homicide 2023 race bucket deaths sum to `All Races` exactly, 1,058 vs 1,058.
- Demographic mutual exclusivity (section 5a - no rollup row alongside split source rows in the same category): PASS - gold has split race buckets and no `asian_pacific_islander`; race and sex partition checks have 0 violations.
- Demographic collision aggregation before dedup (section 5): N/A - no multiple bronze labels collapse to the same canonical demographic except `All Races`/`All Sexes` -> `all`, and duplicate statewide `all` rows are equality-checked before dedup.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - actual parquet order is `year`, `county_fips`, `demographic`, `cause_of_death`, `icd_revision`, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, sections 11/12): PASS - exported parquet contains no forbidden columns; `detail_level` is encoded by file name.
- Canonical column vocabulary (section 16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - no education-specific vocabulary applies; per-100k rates use explicit `_per_100k` names to avoid platform 0-1 rate semantics.
- Shared categorical utilities applied (section 10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): PASS - demographic values use `normalize_demographic_column`; no grade or subject columns exist.
- Tidy long format (section 9 - no demographics/years/components as column names): PASS - cause, ICD revision, and demographic are row values, not wide columns.
- FK keys present in dimension tables (section 13 - `district_code`, `school_code`, `demographic`): PASS - validator reports `county_fips -> counties: all 159 keys resolve` and `demographic -> demographics: all 10 keys resolve`.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - `cause_of_death` and `icd_revision` are independent categoricals, and `county_fips`/`demographic` joins derive from contract FKs.
- Standards compliance (catch-all for sections 1-16 items not enumerated above): PASS - suppression sentinels are nulled, zero deaths are normalized to true 0 rates, state geography is nulled, all county FIPS values are 5-digit strings, and gold is year-partitioned.

## Spot Checks

### Check 1

- Bronze: `homicide__county_year.csv`, Fulton 2023: `county_fips=13121`, `deaths=165`, `death_rate=15.235147577796203`, `age_adjusted_death_rate=14.381648`.
- Transform path: `_tidy_county_layout()` lines 249-292, filename cause derivation lines 397-408, ICD flag lines 400-405.
- Gold: `year=2023/counties.parquet`, `county_fips=13121`, `demographic=all`, `cause_of_death=homicide`, `icd_revision=icd10`, `deaths=165`, `death_rate_per_100k=15.235148`, `age_adjusted_death_rate_per_100k=14.381648`.
- Result: MATCH

### Check 2

- Bronze: `homicide__state_race_year.csv`, 2023 `Asian` row has `deaths=14`, rate `2.5049562348360683`; `Native Hawaiian or Other Pacific Islander` has null deaths and `death_rate=0`; `All Races` and `Selected Races Total` both have `deaths=1058`.
- Transform path: `_tidy_breakdown_layout()` lines 295-346, selected-total drop lines 304-311, demographic normalization lines 320-341.
- Gold: state 2023 homicide rows include `asian deaths=14`, `pacific_islander deaths=0`, and `all deaths=1058`; seven race buckets sum to 1,058.
- Result: MATCH

### Check 3

- Bronze: `homicide__county_year.csv`, Stephens 2018 has `deaths=1`, `death_rate=-5`, `age_adjusted_death_rate=-5`.
- Transform path: `null_sentinel_rates()` in `_oasis_shared.py` and manifest mask recording in `transform.py` lines 470-483.
- Gold: `year=2018/counties.parquet`, `county_fips=13257`, `cause_of_death=homicide`, `deaths=1`, both rate metrics NULL.
- Result: MATCH

### Check 4

- Bronze: `homicide__county_year.csv`, Taliaferro 1994 has blank deaths, `death_rate=0`, blank age-adjusted rate.
- Transform path: `cast_oasis_metrics()` fills death nulls with 0; `normalize_zero_death_rates()` lines 457-469 normalizes zero-death rates to 0.
- Gold: `year=1994/counties.parquet`, `county_fips=13265`, `cause_of_death=homicide`, `icd_revision=icd9`, `deaths=0`, both rate metrics `0.0`.
- Result: MATCH

### Check 5

- Bronze: `homicide__county_year.csv`, 2023 `Georgia` and `County Summary` both have `deaths=1058`, `death_rate=9.56283128137691`, `age_adjusted_death_rate=9.775186599999998`; `homicide__state_race_year.csv`, 2023 `All Races` and `Selected Races Total` also match exactly.
- Transform path: `drop_county_summary_rows()` and `drop_selected_total_rows()` in `_oasis_shared.py`; manifest filter recording in `transform.py` lines 258-267 and 304-311.
- Gold: one statewide `all` homicide row remains for 2023 after duplicate reconciliation.
- Result: MATCH

## Notes

- The 8 age/ethnicity CSVs contain real source rows, for example `accidental_shooting__state_age_year.csv` and `accidental_shooting__state_ethnicity_year.csv`, but are explicitly out of the v1 served scope. This is documented in transform.py, the bronze structure report, and contract limitations, so I did not classify it as unexplained row loss.
- Manifest `masked_values` records 6,104 masked cells for each per-100k rate column, all from OASIS negative sentinels `-5.0` or `-2.0`; gold confirms every NULL rate sits on `deaths` 1-4 and no NULL rate sits outside that range.
