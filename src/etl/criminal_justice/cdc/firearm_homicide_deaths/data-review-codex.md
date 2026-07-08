# Data Review: firearm_homicide_deaths

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: bronze TSV rows reconcile exactly to gold after the documented D77/D157 stitch, suppression handling, and county-year cause categorization.

## Summary

- Review date: 2026-07-02
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze checksum gate passed for all 8 data files; manifest generated at `2026-07-02T23:50:29.598077+00:00`; validation timestamp `2026-07-02T23:51:53.774473+00:00`; transform mtime precedes manifest generation.

## Files Reviewed

- Transform: `src/etl/criminal_justice/cdc/firearm_homicide_deaths/transform.py`
- Contract: `contracts/criminal_justice/firearm_homicide_deaths.odcs.yaml`
- Bronze files: 8 CDC WONDER TSV exports: four cause categories (`firearm_deaths`, `firearm_homicide`, `homicide`, `legal_intervention`) x two vintages (`1999_2020`, `2018_2024`)
- Gold files: 26 county parquet files, `year=1999/counties.parquet` through `year=2024/counties.parquet`
- Manifest: `data/gold/criminal_justice/firearm_homicide_deaths/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/firearm_homicide_deaths/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `src/etl/CLAUDE.md`, `src/etl/criminal_justice/CLAUDE.md`, `data/bronze/criminal_justice/cdc/firearm_homicide_deaths/bronze-data-structure.md`

## Contract Verification

- Schema/parquet column match: PASS - contract properties and parquet columns match exactly: `year`, `county_fips`, `cause_category`, `dataset_vintage`, `deaths`, `population`, `crude_rate_per_100k`, `age_adjusted_rate_per_100k`.
- Column roles and grain: PASS - grain is year + county + `cause_category` + `dataset_vintage`; `county_fips` is the only geography FK and is never NULL for this county-only topic.
- Metric units and derived quality checks: PASS - count metrics carry `unit: count`; per-100k rate metrics intentionally omit a platform `unit` and have authored nonnegative and reconciliation SQL checks.
- Categorical enums: PASS - `cause_category` enum has 4 values and `dataset_vintage` enum has 2 values; both match manifest and gold distinct values.
- Detail levels and layout metadata: PASS - contract declares `counties` only, path template `criminal_justice/firearm_homicide_deaths/year={year}/{detail}.parquet`, and year range `1999-2024`.
- Foreign-key descriptors: PASS - `county_fips -> counties.county_fips`; all 159 gold county keys resolve in `data/gold/_dimensions/counties.parquet`.
- Schema hash/version consistency: PASS - contract version is `1.0.0`; schema hash is `239bee9385ad012f1e3d883f5760f71aabb3154cbb9f0429eed65d2a01b89f7c`; current gold layout matches the emitted schema.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation passed, timestamp is newer than manifest generation.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - all 19 checks passed, including `contract_parquet_schema`, `grain_uniqueness`, `contract_quality_sql`, `foreign_keys`, `canonical_vocabulary`, and `geography_nulling`.
- Validator warnings explained: N/A - validation reports 0 warnings.
- §15b quality-check coverage (cross-column invariants authored): PASS - contract has 17 quality checks covering suppression co-null rules, D77 unreliable-rate rules, D157 crude-rate coverage, age-adjusted-rate vintage scope, crude-rate formula tolerance, vintage/year split, cause containment, population consistency, and full county/cause grids.

## Manifest Verification

- Files processed coverage: PASS - manifest records all 8 current bronze TSVs; checksum gate confirmed all 8 match `bronze-data-structure.md` and no unanalyzed files exist.
- Categorical and recode coverage: PASS - `cause_category` and `dataset_vintage` mappings have `unmapped_count: 0`; manifest values match contract enums and actual gold values.
- Row-count reconciliation: PASS - manifest reports 18,444 bronze rows, 1,908 explicitly filtered D77 overlap rows, and 16,536 gold rows. For 2018-2020, each year has 1,272 bronze rows, 636 filtered rows, and 636 gold rows; all other years have 636 bronze and 636 gold rows.
- Metric stats sanity: PASS - deaths and population are nonnegative, crude rates range `0.0` to `65.3`, age-adjusted rates range `2.5` to `29.6`, and expected null patterns align with CDC suppression and D77 unreliable-rate markers.

## Row and Join Accounting

- Bronze file/year disposition: PASS - D77 files contribute 1999-2017; D157 files contribute 2018-2024; all four causes are present for every served year.
- Filter accounting: PASS - the only filter is the documented D77 2018-2020 overlap drop: 159 counties x 3 years x 4 causes = 1,908 rows.
- Join accounting: N/A - transform does not join source data; county FIPS are source keys and FK integrity is validated against the counties dimension after export.
- Deduplication accounting: PASS - dedup is a no-op guard; actual gold has one row per `year`, `county_fips`, `cause_category`, `dataset_vintage`, and also one row per `year`, `county_fips`, `cause_category`.
- Aggregation/unpivot accounting: N/A - no aggregation or unpivot occurs; each retained bronze county-year-cause row becomes one gold row.

## Reconciliation Checks

- Artifact freshness: PASS - bronze checksums, manifest, validation, contract, and parquet are mutually current.
- Contract freshness: PASS - contract matches current parquet and has no `_metadata.json` dependency.
- Year coverage: PASS - gold covers exactly 1999-2024, 26 years.
- Row preservation: PASS - independently rebuilt expected rows from the 8 TSVs using documented stitch and marker rules: 16,536 expected rows vs 16,536 gold rows; zero value mismatches.
- Column coverage: PASS - fact keys (`Year Code`, `County Code`, filename cause), categoricals (`cause_category`, `dataset_vintage`), and served metrics (`Deaths`, `Population`, `Crude Rate`, D77 `Age Adjusted Rate`) are carried correctly. D157 CI columns are intentionally excluded and documented in transform and contract limitations.
- Recode accuracy: PASS - filename cause slugs map one-to-one to canonical cause categories; era signatures map to `bridged_race` and `single_race` correctly.
- Asian-family demographic recodes (§5b): N/A - source has no demographic fields.
- Demographic mutual exclusivity (§5a - no rollup row alongside split source rows in the same category): N/A - source has no demographic fields.
- Demographic collision aggregation before dedup (§5): N/A - source has no demographic fields.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS - actual parquet order is year, `county_fips`, categoricals, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS - parquet contains no `topic`, `detail_level`, `County`, county name, or crosswalk attributes.
- Canonical column vocabulary (§16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - criminal-justice rate names use explicit `_per_100k`, matching the documented per-100k exception.
- Shared categorical utilities applied (§10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no grade or academic subject columns.
- Tidy long format (§9 - no demographics/years/components as column names): PASS - cause is a row categorical, years are partition values plus `year`, and metrics are tidy columns.
- FK keys present in dimension tables (§13 - `district_code`, `school_code`, `demographic`): PASS - all 159 `county_fips` values resolve to the global counties dimension.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - `cause_category` and `dataset_vintage` are filterable categoricals; `county_fips` join derives from the contract FK descriptor.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS - suppression markers become NULL, zeros remain real zeros, FIPS strings preserve leading zeros, no state rows are fabricated, and validation confirms ID formatting/geography rules.

## Spot Checks

### Check 1

- Bronze: `firearm_deaths_by_county_year_2018_2024.txt`, Bulloch County `13031`, 2024: `Deaths=15`, `Population=85454`, `Crude Rate=17.6`, CI bounds present.
- Transform path: `transform_file` uses `Year Code`, `County Code`, filename cause, D157 `dataset_vintage`, and `_cast_and_mask_metrics`; D157 age-adjusted rate is emitted NULL because the column is absent.
- Gold: `year=2024`, `county_fips=13031`, `cause_category=firearm_deaths`, `dataset_vintage=single_race`, `deaths=15`, `population=85454`, `crude_rate_per_100k=17.6`, `age_adjusted_rate_per_100k=NULL`.
- Result: MATCH

### Check 2

- Bronze: `firearm_deaths_by_county_year_2018_2024.txt`, Sumter County `13261`, 2022: `Deaths=Suppressed`, `Population=28877`, `Crude Rate=Suppressed`.
- Transform path: `_cast_and_mask_metrics` strict casts legal `Suppressed` markers to NULL and records masked deaths/rate events.
- Gold: `year=2022`, `county_fips=13261`, `cause_category=firearm_deaths`, `dataset_vintage=single_race`, `deaths=NULL`, `population=28877`, `crude_rate_per_100k=NULL`, `age_adjusted_rate_per_100k=NULL`.
- Result: MATCH

### Check 3

- Bronze: `firearm_deaths_by_county_year_1999_2020.txt`, Clay County `13061`, 2007: `Deaths=0`, `Population=3262`, `Crude Rate=Unreliable`, `Age Adjusted Rate=Unreliable`.
- Transform path: `_cast_and_mask_metrics` keeps numeric death count 0 and NULLs only D77 `Unreliable` rate cells.
- Gold: `year=2007`, `county_fips=13061`, `cause_category=firearm_deaths`, `dataset_vintage=bridged_race`, `deaths=0`, `population=3262`, `crude_rate_per_100k=NULL`, `age_adjusted_rate_per_100k=NULL`.
- Result: MATCH

### Check 4

- Bronze: `homicide_by_county_year_1999_2020.txt`, Fulton County `13121`, 2017: `Deaths=122`, `Population=1041423`, `Crude Rate=11.7`, `Age Adjusted Rate=11.2`.
- Transform path: D77 row is retained because year is before 2018; metric strings cast directly to numeric gold columns.
- Gold: `year=2017`, `county_fips=13121`, `cause_category=homicide`, `dataset_vintage=bridged_race`, `deaths=122`, `population=1041423`, `crude_rate_per_100k=11.7`, `age_adjusted_rate_per_100k=11.2`.
- Result: MATCH

### Check 5

- Bronze: `legal_intervention_by_county_year_2018_2024.txt`, Appling County `13001`, 2024: `Deaths=0`, `Population=18669`, `Crude Rate=0.0`.
- Transform path: D157 zero-death rows publish real crude rates; `_cast_and_mask_metrics` casts `0.0` to float, not NULL.
- Gold: `year=2024`, `county_fips=13001`, `cause_category=legal_intervention`, `dataset_vintage=single_race`, `deaths=0`, `population=18669`, `crude_rate_per_100k=0.0`, `age_adjusted_rate_per_100k=NULL`.
- Result: MATCH

### Check 6

- Bronze: 2018-2020 overlap rows across D77 and D157 have zero death/population mismatches for all four cause categories. D157 adds 122 + 177 + 149 + 405 crude-rate cells where D77 has `Unreliable`; D77 has 114 numeric age-adjusted-rate overlap cells that are intentionally forgone by the stitch.
- Transform path: `_verify_overlap_identity` asserts death/population identity and numeric crude-rate agreement where both vintages publish; `transform_file` drops D77 rows with `year >= 2018`.
- Gold: 2018, 2019, and 2020 each have exactly 636 rows, all `dataset_vintage=single_race`, with no D77 duplicate rows.
- Result: MATCH

### Check 7

- Bronze: all retained rows with published crude rates.
- Transform path: `_cast_and_mask_metrics` preserves the source-published crude rate; contract SQL verifies it against `deaths / population * 100000`.
- Gold: 2,717 rows have non-null crude rates; independent recomputation found maximum rounding delta below 0.051 and zero containment or population-consistency failures.
- Result: MATCH

## Notes

- No required fixes were identified.
- This review did not read any prior `data-review-claude.md` or `data-review-codex.md` report before writing findings.
