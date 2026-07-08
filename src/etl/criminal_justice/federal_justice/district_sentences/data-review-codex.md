# Data Review: district_sentences

## Verdict

**Status**: NEEDS FIXES
**Must-fix count**: 1

Summary: bronze coverage, row accounting, validation, and representative aggregate recomputations are clean, but the transform caps determinate `SENTTOT > 470` values at 470.0 instead of the codebook/SENTTCAP 469.99 cap, changing served averages in at least two gold cells.

## Summary

- Review date: 2026-07-07
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - `scripts/check_bronze_freshness.py criminal_justice federal_justice district_sentences` passed for all 25 checksummed bronze files; transform mtime 2026-07-07T04:06:26Z precedes manifest generation 2026-07-07T04:11:16Z; validation timestamp 2026-07-07T04:11:16Z is fresh and passing.

## Files Reviewed

- Transform: `src/etl/criminal_justice/federal_justice/district_sentences/transform.py`
- Contract: `contracts/criminal_justice/district_sentences.odcs.yaml`
- Bronze files: 24 annual USSC zips (`opafy02nid.zip` through `opafy25nid_csv.zip`) plus `USSC_Public_Release_Codebook_FY99_FY25.pdf`, `_provenance.md`, and `bronze-data-structure.md`
- Gold files: 24 `year=YYYY/states.parquet` files, FY2002-FY2025
- Manifest: `data/gold/criminal_justice/district_sentences/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/district_sentences/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, data-cleaning standards, transform/review/fix/full-pipeline skills, `AGENTS.md`, `CLAUDE.md`, and `src/etl/criminal_justice/CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS - validator reports all 24 parquet files match the contract; actual columns are `year`, `federal_district`, `demographic`, `offenders_sentenced`, `num_with_prison_sentence`, `avg_sentence_months`, `median_sentence_months`.
- Column roles and grain: PASS - contract grain is `year`, `federal_district`, `demographic`; `year` is `column_role=year`, `federal_district` is a categorical grain key, `demographic` is `fk_demographic`, and all metric columns are metric roles.
- Metric units and derived quality checks: FAIL - count metrics have `unit=count` and range checks, and authored checks constrain sentence stats to `(0, 470]`, but the transform and emitted prose claim SENTTCAP-style capping while using 470.0 for determinate `SENTTOT > 470`; see Fix 1.
- Categorical enums: PASS - contract enums match manifest and gold values for `federal_district` (`georgia_middle`, `georgia_northern`, `georgia_southern`) and `demographic` (`all`, `female`, `male`).
- Detail levels and layout metadata: PASS - contract reports `detail_levels: [states]`, `default_detail: states`, partitioning by `year`, and path template `criminal_justice/district_sentences/year={year}/{detail}.parquet`; gold layout matches.
- Foreign-key descriptors: PASS - contract has only the global demographics FK; actual gold demographics all resolve in `data/gold/_dimensions/demographics.parquet`.
- Schema hash/version consistency: PASS - contract version is `1.0.0`, schema hash is `24fbba0810374a4bc42f3cd3f23cca0ef607d08d14188a2edac3bca6995caa2c`, and available years are FY2002-FY2025 with no gaps.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp 2026-07-07T04:11:16.939799Z is after manifest generation 2026-07-07T04:11:16.867202Z and `"passed": true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 19 pass, 0 fail, 0 warning; schema, grain uniqueness, all 14 contract SQL checks, demographics FK, vocabulary, and geography nulling pass.
- Validator warnings explained: N/A - no validator warnings.
- section 15b quality-check coverage (cross-column invariants authored): PASS - checks cover no pre-2000 years, all rows count at least one offender, male+female within all totals, all row per district-year, exactly three districts per year, prison-sentence denominator within offenders, sentence-stat co-null behavior, and average/median range. The exact 469.99 cap cannot be inferred from aggregate range checks and is addressed as transform logic in Fix 1.

## Manifest Verification

- Files processed coverage: PASS - manifest lists all 24 annual zips, FY2002-FY2025, with fixed-width SAS layout for FY2002-FY2011 and CSV-wide format for FY2012-FY2025; bronze freshness confirms no unanalyzed or changed files.
- Categorical and recode coverage: PASS - `federal_district`, `offender_sex`, and final `demographic` mappings have `unmapped_count: 0`; map entries are semantically correct for GA DISTRICT 32/33/34 and MONSEX 0/1.
- Row-count reconciliation: PASS - manifest total bronze rows = 1,720,684; explicit non-GA filter removes 1,683,826 rows; gold has 216 aggregate rows. For every year, `bronze - non_georgia_district_row` equals the sum of gold `demographic='all'` counts across the three federal districts.
- Metric stats sanity: FAIL - metric ranges are non-negative and within `(0, 470]`, but the sentence-month averages inherit the incorrect 470.0 cap for raw determinate values above 470; scan found 69 GA rows with raw `SENTTOT > 470`.

## Row and Join Accounting

- Bronze file/year disposition: PASS - every annual source zip is processed once; the codebook PDF and provenance/structure markdown are supporting metadata, not fact inputs.
- Filter accounting: PASS - only explicit substantive filter is `DISTRICT` not in GA codes 32/33/34; manifest records 1,683,826 `non_georgia_district_row` removals. Direct samples from FY2002/FY2012/FY2025 show non-GA districts such as 74, 42, 88, 61, 52, and 3 excluded.
- Join accounting: N/A - transform performs no data joins; demographic FK is validated after export against the global dimension.
- Deduplication accounting: PASS - each year has one source file; `assert_no_natural_key_collisions` runs before `deduplicate_by_levels`, and actual gold has zero duplicate `year/federal_district/demographic` groups.
- Aggregation/unpivot accounting: PASS - no unpivot; offender microdata collapses to 9 aggregate rows per fiscal year (3 districts x all/male/female). Direct recomputations for fixed-width and CSV eras match gold except for the cap issue in Fix 1.

## Reconciliation Checks

- Artifact freshness: PASS - bronze freshness, manifest, contract, and validation are current.
- Contract freshness: PASS - contract was emitted after export by the current transform run; no `_metadata.json` dependency.
- Year coverage: PASS - gold contains FY2002-FY2025, 24 years, no unexpected years.
- Row preservation: PASS - GA offender counts are preserved in the `all` rows: every year has zero difference between manifest GA rows and gold `all` row sums.
- Column coverage: PASS - gold columns trace to filename year, `DISTRICT`, `MONSEX`, row counts, and `SENTTOT`; excluded bronze fields are either non-GA rows, PII/detail columns below aggregate grain, redundant code schemes, or deferred unsupported breakdowns.
- Recode accuracy: PASS - `DISTRICT` 32/33/34 map to the three Georgia federal districts; `MONSEX` 0/1 map to male/female; missing sex is included only in `all`.
- Asian-family demographic recodes (section 5b): N/A - no race demographic is served; race is intentionally deferred because public `NEWRACE` conflates non-White/Black/Hispanic groups.
- Demographic mutual exclusivity (section 5a - no rollup row alongside split source rows in the same category): PASS - male/female are mutually exclusive and the overlapping `all` lane is the only aggregate; latest FY2025 gold differences between all and male+female match missing-sex counts by district.
- Demographic collision aggregation before dedup (section 5): N/A - no multiple raw labels collapse to the same served demographic beyond the all-row aggregation.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - actual parquet order is `year`, `federal_district`, `demographic`, then metrics. `federal_district` is a topic categorical grain key, not a county FK.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, section 11/12): PASS - actual parquet has no `topic`, `detail_level`, PII, names, county IDs, or source record IDs.
- Canonical column vocabulary (section 16): PASS - no forbidden education vocabulary variants; criminal justice metric names are descriptive and contract-backed.
- Shared categorical utilities applied (section 10a): PASS - demographic normalization uses `normalize_demographic_column`; no grade/subject columns apply.
- Tidy long format (section 9): PASS - demographic values are rows, years are partitions/column values, and no category is encoded as a metric column.
- FK keys present in dimension tables (section 13): PASS - `all`, `female`, and `male` all exist in the global demographics dimension.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - federal district is an enum-bearing categorical filter; demographic FK join is contract-described; no county join is advertised.
- Standards compliance (catch-all for sections 1-16 items not enumerated above): FAIL - the sentence-length capping rule does not faithfully implement the codebook/SENTTCAP convention for raw `SENTTOT > 470`; see Fix 1.

## Spot Checks

### Check 1

- Bronze: `opafy02nid.zip` fixed-width FY2002, GA Northern (`DISTRICT=32`) all offenders: 786 GA rows, 714 non-null capped sentence-month values, 2 raw values above 470, recomputed average 72.13 and median 48.0.
- Transform path: `_read_fixed_width_year` -> `transform_file` -> `_clean_offenders` -> `_aggregate` (`transform.py:256-304`, `385-460`, `468-573`, `576-614`).
- Gold: `data/gold/criminal_justice/district_sentences/year=2002/states.parquet`, `georgia_northern/all` has `offenders_sentenced=786`, `num_with_prison_sentence=714`, `avg_sentence_months=72.13`, `median_sentence_months=48.0`.
- Result: MATCH

### Check 2

- Bronze: `opafy12nid_csv.zip` CSV FY2012, GA Southern (`DISTRICT=34`) female (`MONSEX=1`): 101 offender rows, 39 non-null sentence-month values, recomputed average 33.22 and median 27.0.
- Transform path: `_read_csv_year` -> `transform_file` -> `_clean_offenders` -> `_aggregate` (`transform.py:307-377`, `385-460`, `468-573`, `576-614`).
- Gold: `year=2012/states.parquet`, `georgia_southern/female` has `offenders_sentenced=101`, `num_with_prison_sentence=39`, `avg_sentence_months=33.22`, `median_sentence_months=27.0`.
- Result: MATCH

### Check 3

- Bronze: `opafy25nid_csv.zip` CSV FY2025, GA Middle (`DISTRICT=33`) all offenders: 405 offender rows, 326 non-null sentence-month values, 10 missing-sex rows included only in all, recomputed current-transform average 84.42 and median 60.0.
- Transform path: `_read_csv_year` -> `transform_file` -> `_clean_offenders` -> `_aggregate` (`transform.py:307-377`, `385-460`, `468-573`, `576-614`).
- Gold: `year=2025/states.parquet`, `georgia_middle/all` has `offenders_sentenced=405`, `num_with_prison_sentence=326`, `avg_sentence_months=84.42`, `median_sentence_months=60.0`; male 333 + female 62 = 395, leaving 10 missing-sex offenders in all only.
- Result: MATCH

### Check 4

- Bronze: `USSC_Public_Release_Codebook_FY99_FY25.pdf` says SENTTCAP caps sentences greater than 470 months at 469.99 and gives life sentences 470. In `opafy05nid.zip`, GA Northern male rows include raw `SENTTOT` 480, 481, and 512 for `USSCIDN` 877047, 809847, and 858322.
- Transform path: `_clean_offenders` clips every raw `senttot > 470` to `SENTENCE_CAP_MONTHS = 470.0` (`transform.py:164-170`, `559-572`).
- Gold: current `year=2005/states.parquet`, `georgia_northern/male` has `avg_sentence_months=85.52`; recomputing with the codebook cap of 469.99 gives 85.51.
- Result: MISMATCH

## Needs Follow-up

- Federal-district grain (`federal_district` categorical with no `county_fips`) is explicitly documented in the transform and contract and is not a bronze-to-gold accuracy defect, but the broader serving/dimension design remains a deferred project decision before approval.

## Required Fixes

### Fix 1: Apply the SENTTCAP 469.99 cap for raw determinate sentences over 470 months

- **Severity**: MEDIUM
- **Issue**: The transform claims to follow the Commission's SENTTCAP length-of-imprisonment convention but clips every raw `SENTTOT > 470` to `470.0`. The codebook distinguishes determinate sentences over 470 months, which are capped at `469.99`, from life sentences, which are coded `470`. This produces incorrect served `avg_sentence_months` values after the transform's two-decimal rounding.
- **Evidence**: Bronze codebook `USSC_Public_Release_Codebook_FY99_FY25.pdf` states SENTTCAP uses range `0.01 thru 469.99` with `470 = Life`, and Appendix B says sentences longer than 470 months are capped at 469.99 while life is 470. A full GA scan found 69 raw `SENTTOT > 470` rows. In `opafy05nid.zip`, GA Northern male rows `USSCIDN` 877047/809847/858322 have raw `SENTTOT` 480/481/512; current gold `year=2005/states.parquet` has `avg_sentence_months=85.52`, but recomputing with 469.99 gives 85.51. In `opafy22nid_csv.zip`, GA Middle male rows `USSCIDN` 2746148/2749668/2780675 have raw `SENTTOT=720`; current gold has `avg_sentence_months=93.01`, but recomputing with 469.99 gives 93.00.
- **Location**: `src/etl/criminal_justice/federal_justice/district_sentences/transform.py:164-170` and `src/etl/criminal_justice/federal_justice/district_sentences/transform.py:559-572`
- **Suggested fix**: Replace the single `SENTENCE_CAP_MONTHS = 470.0` clip for values above 470 with SENTTCAP-compatible logic: preserve raw `470` as 470, but map raw values `> 470` and `< SENTINEL_FLOOR` to `469.99` after the existing sentinel/non-positive masks. Update the transform comments and emitted contract descriptions/quality checks to state that determinate values above 470 are capped at 469.99 while life remains 470, then re-run the transform and validation.

## Notes

- No prior `data-review-claude.md` or existing `data-review-codex.md` content was read before writing this independent report.
- Validator cannot catch Fix 1 because the current contract quality checks only enforce sentence statistics within `(0, 470]`; the defect is a formula-level convention mismatch below that range ceiling.
- The review used representative direct bronze inspections for FY2002 fixed-width, FY2012 CSV, and FY2025 CSV, plus manifest-led all-year row reconciliation and a full read-only scan for raw `SENTTOT > 470` rows.
