# Data Review: overdose_deaths

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Current gold faithfully represents the served OASIS county, race, and sex extracts; no bronze-to-gold accuracy fixes are required.

## Summary

- Review date: 2026-07-02
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze checksum gate passed for all 30 CSV files; transform mtime `2026-07-02T23:24:08.690187+00:00`, manifest `2026-07-02T23:24:09.406185+00:00`, validation `2026-07-02T23:25:30.777122+00:00`.

## Files Reviewed

- Transform: `src/etl/criminal_justice/dph_oasis/overdose_deaths/transform.py`
- Shared helpers: `src/etl/criminal_justice/dph_oasis/_oasis_shared.py`
- Contract: `contracts/criminal_justice/overdose_deaths.odcs.yaml`
- Bronze files: 30 CSV files in `data/bronze/criminal_justice/dph_oasis/overdose_deaths/`; 18 county/race/sex files ingested, 12 age/ethnicity files intentionally deferred by transform policy.
- Gold files: 52 parquet files under `data/gold/criminal_justice/overdose_deaths/year=*/` (`counties.parquet` and `states.parquet`, 1999-2024).
- Manifest: `data/gold/criminal_justice/overdose_deaths/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/overdose_deaths/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `data/bronze/criminal_justice/dph_oasis/overdose_deaths/bronze-data-structure.md`, `data/bronze/criminal_justice/dph_oasis/overdose_deaths/_provenance.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `src/etl/CLAUDE.md`, `src/etl/criminal_justice/CLAUDE.md`.

## Contract Verification

- Schema/parquet column match: PASS - contract and parquet columns both equal `year, county_fips, demographic, drug_category, deaths, death_rate_per_100k, age_adjusted_death_rate_per_100k`.
- Column roles and grain: PASS - grain is `year, county_fips, demographic, drug_category`; roles are year, `fk_county`, `fk_demographic`, categorical, and metrics.
- Metric units and derived quality checks: PASS - `deaths` is `unit: count`; per-100k rates intentionally omit a repo unit marker and have authored non-negative and suppression/null quality SQL.
- Categorical enums: PASS - `demographic` and `drug_category` enums match actual gold distinct values and manifest `gold_values_produced`.
- Detail levels and layout metadata: PASS - contract lists `counties` and `states`, default `counties`, year partitioning, and `criminal_justice/overdose_deaths/year={year}/{detail}.parquet`.
- Foreign-key descriptors: PASS - `county_fips -> counties` and `demographic -> demographics`; validator resolved all 159 county keys and all 10 demographic keys.
- Schema hash/version consistency: PASS - version `1.0.0`, schema hash `3f7052554c1a444e5950eb97b79d73cf6d0128b2c5daee29e47647327233d0f1`, year range `1999-2024`.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp is after manifest generation and reports `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 20 pass, 0 fail, 0 warning; all 15 contract quality SQL checks pass.
- Validator warnings explained: N/A - no warnings.
- §15b quality-check coverage (cross-column invariants authored): PASS - quality SQL covers non-negative rates, suppression/null semantics, zero-death rates, county/state reconciliation, race and sex partitions, opioid hierarchy, complete county grid, and complete state demographic grid.

## Manifest Verification

- Files processed coverage: PASS - manifest records the 18 served county/race/sex files; the 12 age/ethnicity files are present in bronze and intentionally skipped by `DEFERRED_LAYOUTS` with contract limitations explaining v2 scope.
- Categorical and recode coverage: PASS - `demographic` map has 11 observed bronze labels, `drug_category` has 6 filename-derived values, and both have `unmapped_count: 0`.
- Row-count reconciliation: PASS - each normal year has 1,044 ingested bronze rows and 1,014 gold rows. The 30 removed rows are 6 county summaries, 6 selected-race totals, 6 selected-sex totals, and 12 duplicate statewide all-demographic rows. In 2024, 1,044 additional `selected_years_total` rows are recorded and filtered as derived all-years totals.
- Metric stats sanity: PASS - deaths are non-negative with no nulls; per-100k rates are non-negative after sentinel nulling, with expected sparse nulls for suppressed rows.

## Row and Join Accounting

- Bronze file/year disposition: PASS - all 30 current CSV checksums match the bronze structure report; 18 served files are processed, and 12 age/ethnicity files are explicitly deferred by transform lines 154-157 and 363-371.
- Filter accounting: PASS - transform records 1,512 explicit derived-row filters: 1,044 selected-years-total rows, 156 county-summary rows, 156 selected-race-total rows, and 156 selected-sex-total rows.
- Join accounting: N/A - the transform performs no data joins; FK integrity is validated against dimensions after export.
- Deduplication accounting: PASS - statewide `all` rows are published identically in county, race, and sex layouts; the collision guard checks metrics before dedup and dedup removes the expected 312 duplicate all rows.
- Aggregation/unpivot accounting: PASS - no derived aggregation is used for served rows; county/race/sex partitions are source-published and contract quality SQL verifies their deaths totals.

## Reconciliation Checks

- Artifact freshness: PASS - freshness script passed; validation is newer than manifest; transform is not newer than manifest.
- Contract freshness: PASS - contract mtime is from the same run as manifest/gold and there is no `_metadata.json` dependency.
- Year coverage: PASS - gold covers 1999-2024, 26 years, 1,014 rows per year.
- Row preservation: PASS - gold has 26,364 rows: 24,804 county rows (159 counties x 6 categories x 26 years) and 1,560 state rows (10 demographics x 6 categories x 26 years).
- Column coverage: PASS - served keys and metrics map from `year`, `county_fips`, race/sex labels, filename cause slug, `deaths`, `death_rate`, and `age_adjusted_death_rate`; geography names remain dimension attributes.
- Recode accuracy: PASS - race and sex labels map correctly; `Selected ... Total` rows are dropped as duplicates after equality checks; filename slugs map one-to-one to gold `drug_category`.
- Asian-family demographic recodes (§5b): PASS - bronze has separate `Asian` and `Native Hawaiian or Other Pacific Islander` rows; gold emits `asian` and `pacific_islander`, not a combined bucket.
- Demographic mutual exclusivity (§5a - no rollup row alongside split source rows in the same category): PASS - gold has split race rows plus `all`; no `asian_pacific_islander` rollup exists.
- Demographic collision aggregation before dedup (§5): N/A - observed race/sex labels are one-to-one after normalization.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS - actual parquet order is `year, county_fips, demographic, drug_category, deaths, death_rate_per_100k, age_adjusted_death_rate_per_100k`.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS - actual parquet contains only keys, categorical, and metrics.
- Canonical column vocabulary (§16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - no education-specific canonical vocabulary applies; per-100k rates are explicitly named with `_per_100k`.
- Shared categorical utilities applied (§10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no grade or subject columns; demographics use the shared normalizer.
- Tidy long format (§9 - no demographics/years/components as column names): PASS - demographic and drug category are row values, not wide columns.
- FK keys present in dimension tables (§13 - `district_code`, `school_code`, `demographic`): PASS - validator confirms county and demographic FKs resolve.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - `drug_category` is a required grain categorical with no total value; contract warns categories overlap and must be filtered to one value.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS - suppression sentinels become null, zero-death rows become zero rates, state rows have null `county_fips`, and gold is year-partitioned by detail-level files.

## Spot Checks

### Check 1

- Bronze: `all_drug_overdoses__county_year.csv`, Fulton 2023 has `county_fips=13121`, `deaths=308`, `death_rate=28.43894214521958`, `age_adjusted_death_rate=27.0719002`.
- Transform path: `_tidy_county_layout()` lines 246-289, `RATE_RENAMES` lines 161-164.
- Gold: `year=2023`, `county_fips=13121`, `demographic=all`, `drug_category=all_drug_overdoses`, `deaths=308`, `death_rate_per_100k=28.43894214521958`, `age_adjusted_death_rate_per_100k=27.0719002`.
- Result: MATCH

### Check 2

- Bronze: `all_drug_overdoses__county_year.csv`, Effingham 2006 has `deaths=4`, `death_rate=-5`, `age_adjusted_death_rate=-5`.
- Transform path: `null_sentinel_rates()` in `_oasis_shared.py` lines 236-258, called from transform lines 452-465.
- Gold: `year=2006`, `county_fips=13103`, `deaths=4`, both rate columns NULL.
- Result: MATCH

### Check 3

- Bronze: `all_drug_overdoses__state_race_year.csv`, 2023 has `All Races=2521`, `Asian=21`, `Native Hawaiian or Other Pacific Islander=5`.
- Transform path: `_tidy_breakdown_layout()` lines 292-343 and `normalize_demographic_column()`.
- Gold: `all=2521`, `asian=21`, `pacific_islander=5` for `year=2023`, `drug_category=all_drug_overdoses`, `county_fips=NULL`.
- Result: MATCH

### Check 4

- Bronze: `all_opioids__state_sex_year.csv`, 2024 has `All Sexes=1250`, `Female=419`, `Male=831`, and `Selected Sexes Total=1250`.
- Transform path: `drop_selected_total_rows()` in `_oasis_shared.py` lines 158-196, then `_tidy_breakdown_layout()` lines 292-343.
- Gold: `all=1250`, `female=419`, `male=831`; no selected-total row is served.
- Result: MATCH

### Check 5

- Bronze: `all_drug_overdoses__state_race_year.csv`, `race=Unknown`, 2023 has empty deaths and `death_rate=0`, `age_adjusted_death_rate=0`.
- Transform path: `cast_oasis_metrics()` fills null deaths to 0; `normalize_zero_death_rates()` preserves zero rates.
- Gold: `demographic=race_unknown`, `deaths=0`, `death_rate_per_100k=0.0`, `age_adjusted_death_rate_per_100k=0.0`.
- Result: MATCH

### Check 6

- Bronze: 2023 statewide all-drug all row is identical across county, race, and sex files: `deaths=2521`, `death_rate=22.786292684641957`, `age_adjusted_death_rate=23.209015800000003`.
- Transform path: collision guard lines 467-472, dedup lines 473-496.
- Gold: exactly one `year=2023`, `county_fips=NULL`, `demographic=all`, `drug_category=all_drug_overdoses` row with the same metrics.
- Result: MATCH

## Notes

- The 12 deferred age/ethnicity files are not treated as stale or missing: the transform, contract, and limitations consistently state they are out of v1 scope because age buckets need demographic-dimension expansion and OASIS ethnicity overlaps the existing race-axis semantics.
- No prior `data-review-claude.md` content was read before this independent review.
