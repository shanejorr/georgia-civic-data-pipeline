# Data Review: juvenile_population

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze, transform logic, contract, validator output, and gold parquet reconcile; no required transform fixes were found.

## Summary

- Review date: 2026-07-02
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH — transform mtime `2026-07-03T00:16:32.772995+00:00`, manifest `generated_at` `2026-07-03T00:16:33.710792+00:00`, validation timestamp `2026-07-03T00:17:51.552308+00:00`, validation `passed: true`.

## Files Reviewed

- Transform: `src/etl/criminal_justice/ojjdp/juvenile_population/transform.py`
- Contract: `contracts/criminal_justice/juvenile_population.odcs.yaml`
- Bronze files: 28 current EZAPOP CSV data files under `data/bronze/criminal_justice/ojjdp/juvenile_population/`; all 28 checksum entries in `bronze-data-structure.md` match current bytes.
- Gold files: 70 parquet files under `data/gold/criminal_justice/juvenile_population/year=1990` through `year=2024` (`counties.parquet` and `states.parquet` for each year).
- Manifest: `data/gold/criminal_justice/juvenile_population/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/juvenile_population/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/CLAUDE.md`, `src/etl/criminal_justice/CLAUDE.md`, and relevant shared utility files in `src/utils/`.

## Contract Verification

- Schema/parquet column match: PASS — contract and all parquet files expose exactly `year`, `county_fips`, `demographic`, `age_group`, `population`, `hispanic_population`, `not_hispanic_population` in that order.
- Column roles and grain: PASS — contract grain is `year`, `county_fips`, `demographic`, `age_group`; roles match the transform column declaration at `transform.py:691-826`.
- Metric units and derived quality checks: PASS — all three metrics are `unit: count`; contract includes non-negative checks, `population_never_null`, and topic-specific partition/structural SQL checks.
- Categorical enums: PASS — manifest and gold distinct values match contract enums for `demographic` and `age_group`; `county_fips` is an FK, not an enum.
- Detail levels and layout metadata: PASS — contract detail levels are `counties` and `states`; gold has one `counties.parquet` and one `states.parquet` for each year 1990-2024.
- Foreign-key descriptors: PASS — `county_fips -> counties` and `demographic -> demographics`; validation reports all 159 county keys and all 7 demographic keys resolve.
- Schema hash/version consistency: PASS — contract `version: 1.0.0`, `schema_hash: 629af9781d613887eda60bbcdb8475c5908de80f14f72718d304f03f73fef767`, and `year_range: 1990-2024` are coherent with the transform and gold layout.

## Validator Verification

- `_validation.json` fresh + passing: PASS — validation timestamp is newer than the manifest and reports `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS — 19 pass, 0 fail; schema, grain uniqueness, 15 contract quality SQL checks, FK integrity, vocabulary, ID formatting, and geography nulling all passed.
- Validator warnings explained: PASS — the only warning is tidy-format heuristic detection of `hispanic_population`; this is an intentional, documented metric-column representation because EZAPOP ethnicity is an overlapping any-race marginal and not mutually exclusive with bridged-race rows.
- §15b quality-check coverage (cross-column invariants authored): PASS — contract quality SQL covers non-null population, sex/race/ethnicity partitions, single-age rollup, state county-sum equality, juvenile <= total population, ethnicity structural nulls, and demographic splits limited to `age_group = '00_17'`.

## Manifest Verification

- Files processed coverage: PASS — all 28 current CSV data files appear in `files_processed`; no data CSV is unlisted or missing, and all carry the expected 160 parsed data rows.
- Categorical and recode coverage: PASS — `age_group`, `county_fips`, and `demographic` have `unmapped_count: 0`; demographic gold values are `all`, `asian_pacific_islander`, `black`, `female`, `male`, `native_american`, and `white`.
- Row-count reconciliation: PASS — manifest `total_bronze` is 156,800 source cells (28 files x 160 rows x 35 years), `total_gold` is 145,600 rows (26 base slices x 160 x 35), and 11,200 explicit filtered rows are the two ethnicity marginals pivoted into metric columns.
- Metric stats sanity: PASS — `population` is fully non-null and non-negative; `hispanic_population` and `not_hispanic_population` are non-null on exactly 5,600 juvenile-total rows and structurally null elsewhere.

## Row and Join Accounting

- Bronze file/year disposition: PASS — each file spans year columns 1990-2024; every file is read by `_read_ezapop_csv`, verified by `_verify_export`, and unpivoted by `_unpivot_years`.
- Filter accounting: PASS — the only row-count reduction is the documented pivot of two ethnicity files into `hispanic_population` and `not_hispanic_population`, recorded as 320 rows per year, 11,200 total.
- Join accounting: PASS — the two ethnicity frames have matching `(county_raw, year)` coverage and populate every `demographic = 'all', age_group = '00_17'` row; county name -> FIPS resolution has 0 unmatched county rows, including `De Kalb County -> 13089`.
- Deduplication accounting: PASS — pre-dedup natural keys are unique; gold duplicate check on `year`, `county_fips`, `demographic`, `age_group` returns 0 duplicate groups.
- Aggregation/unpivot accounting: PASS — no metric aggregation is performed by the transform; wide year columns are unpivoted one-to-one, and source partition sums are preserved exactly.

## Reconciliation Checks

- Artifact freshness: PASS — transform, manifest, validation, contract, bronze checksums, and gold partitions are mutually current.
- Contract freshness: PASS — contract is emitted from the transform's `write_data_dictionary()` call and has no `_metadata.json` dependency.
- Year coverage: PASS — gold covers exactly 1990-2024 with 4,160 rows per year.
- Row preservation: PASS — direct all-cell reconciliation checked 156,800 source cells against gold population/ethnicity outputs with 0 mismatches.
- Column coverage: PASS — gold columns trace to year headers, county names/FIPS, filename slice metadata, and source count cells; `Total`, trailing empty CSV column, preamble, footer, and county names are validly excluded.
- Recode accuracy: PASS — filename slices map to the expected `age_group`/`demographic`; `Asian` is remapped to `asian_pacific_islander`, `American Indian` to `native_american`, and `All Counties` to state rows with NULL `county_fips`.
- Asian-family demographic recodes (§5b): PASS — bronze has no separate Pacific Islander bucket; race buckets sum exactly to juvenile totals, and gold has `asian_pacific_islander` only, with no `asian` or `pacific_islander` rows.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): PASS — gold does not publish split Asian/Pacific Islander rows alongside the combined bucket; sex and bridged-race rows are documented one-way marginals, and ethnicity is not emitted as overlapping demographic rows.
- Demographic collision aggregation before dedup (§5): N/A — each source demographic slice maps to a distinct canonical key; no collision aggregation is needed.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS — parquet order is `year`, `county_fips`, `demographic`, `age_group`, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS — exported parquet excludes `detail_level`, `county_raw`, county names, and crosswalk IDs.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): N/A — this topic has CJ population denominator columns, not education assessment vocabulary.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A — no grade or subject columns; demographic normalization uses `normalize_demographic_column`.
- Tidy long format (§9 — no demographics/years/components as column names): PASS — years and age groups are long; ethnicity metric columns are a documented exception to avoid publishing overlapping ethnicity rows inside the shared demographic FK.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS — `county_fips` resolves to counties and `demographic` resolves to demographics per `_validation.json`.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS — API grain and joins derive from contract `grain` and `foreign_keys`; `age_group` is the only topic categorical filter.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS — counts are `Int64`, year is `Int32`, FIPS values are 5-character strings, no suppression markers survive, no impossible negative counts exist, and no gold rows are fabricated.

## Spot Checks

### Check 1

- Bronze: `ezapop_ga_county_year_juveniles_age00_17.csv`, Fulton County, 2024 = 222,302.
- Transform path: `_read_ezapop_csv` / `_unpivot_years` / `_resolve_geography`, `transform.py:254-382` and `transform.py:508-549`.
- Gold: `year=2024`, `county_fips = '13121'`, `demographic = 'all'`, `age_group = '00_17'`, `population = 222302`, `hispanic_population = 25179`, `not_hispanic_population = 197123`.
- Result: MATCH

### Check 2

- Bronze: `ezapop_ga_county_year_juveniles_race_asian.csv`, Fulton County, 2024 = 20,118; source has no separate Pacific Islander file and race sums equal juvenile totals.
- Transform path: `FILE_SLICES` remaps the Asian race file to `ASIAN_COMBINED_LABEL`, then `normalize_demographic_column`, `transform.py:183-188` and `transform.py:421-438`.
- Gold: `year=2024`, `county_fips = '13121'`, `demographic = 'asian_pacific_islander'`, `age_group = '00_17'`, `population = 20118`; no `asian` or `pacific_islander` demographic values exist.
- Result: MATCH

### Check 3

- Bronze: `ezapop_ga_county_year_age_10.csv`, Fulton County, 2024 = 12,381.
- Transform path: single-age filename mapping to `age_group = '10'`, `transform.py:197-205` and `transform.py:421-444`.
- Gold: `year=2024`, `county_fips = '13121'`, `demographic = 'all'`, `age_group = '10'`, `population = 12381`, ethnicity columns NULL structurally.
- Result: MATCH

### Check 4

- Bronze: `ezapop_ga_county_year_juveniles_age00_17.csv`, De Kalb County, 2024 = 171,001; Hispanic file = 29,617 and non-Hispanic file = 141,384.
- Transform path: ethnicity full join then left join to juvenile-total rows, plus county FIPS resolution, `transform.py:459-505` and `transform.py:508-549`.
- Gold: `year=2024`, `county_fips = '13089'`, `demographic = 'all'`, `age_group = '00_17'`, `population = 171001`, `hispanic_population = 29617`, `not_hispanic_population = 141384`.
- Result: MATCH

## Notes

- `bronze-data-structure.md` overview says "27 CSV files", but its checksum table, current bronze inventory, manifest, and transform all cover 28 CSV data files. This is a documentation typo in the bronze profile, not a transform accuracy defect.
- I did not read any prior `data-review-claude.md` or `data-review-codex.md` before completing this independent review.
