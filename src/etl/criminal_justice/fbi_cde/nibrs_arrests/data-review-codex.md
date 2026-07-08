# Data Review: nibrs_arrests

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze-to-gold row ledgers, recodes, joins, contract checks, validator output, and spot traces all support the current transform.

## Summary

- Review date: 2026-07-02
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - `scripts/check_bronze_freshness.py criminal_justice fbi_cde nibrs_arrests` passed; validation timestamp `2026-07-02T22:07:28.996114+00:00` is newer than manifest `2026-07-02T22:04:50.106083+00:00`; transform mtime precedes the manifest.

## Files Reviewed

- Transform: `src/etl/criminal_justice/fbi_cde/nibrs_arrests/transform.py`
- Contract: `contracts/criminal_justice/nibrs_arrests.odcs.yaml`
- Bronze files: shared zips in `data/bronze/criminal_justice/fbi_cde/nibrs_offenses/GA-2018.zip` through `GA-2024.zip`; this topic directory intentionally contains only docs/provenance.
- Gold files: `data/gold/criminal_justice/nibrs_arrests/year=2018..2024/{counties,states}.parquet`
- Manifest: `data/gold/criminal_justice/nibrs_arrests/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/nibrs_arrests/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `CLAUDE.md`, `src/etl/CLAUDE.md`, `src/etl/criminal_justice/CLAUDE.md`, data-cleaning standards, transform-topic, data-review, fix-from-reviews, full-pipeline, and bronze-data-structure skills.

## Contract Verification

- Schema/parquet column match: PASS - actual gold columns exactly match contract properties: `year`, `county_fips`, `demographic`, `coverage`, `reporting_segment`, `offense_type`, `offense_category`, `crime_against`, `offense_group`, `arrest_type`, and eight count metrics.
- Column roles and grain: PASS - contract grain is `year, county_fips, demographic, coverage, reporting_segment, offense_type, offense_category, crime_against, offense_group, arrest_type`; transform natural keys use the non-dependent subset and authored quality SQL enforces dependent attributes.
- Metric units and derived quality checks: PASS - every metric is `unit: count`; contract quality includes non-negative checks and `arrest_count >= 1`.
- Categorical enums: PASS - gold distincts match manifest/contract for demographic, coverage, reporting segment, offense category, crime-against, offense group, and arrest type.
- Detail levels and layout metadata: PASS - contract declares `counties` and `states`; every year 2018-2024 has both files and no unexpected detail file.
- Foreign-key descriptors: PASS - `county_fips -> counties` and `demographic -> demographics` are declared; validator reports 153 county keys and 9 demographic keys resolve.
- Schema hash/version consistency: PASS - version is `1.0.0`; schema hash is `0d53e28110e59527884506812de6de7288f4098f0a064b63e361b60bc54b5c58`; year range is `2018-2024`.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation passed with 19 pass, 0 fail, 1 warning.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - schema, grain uniqueness, 28 contract SQL checks, FKs, canonical vocabulary, and geography nulling all pass.
- Validator warnings explained: PASS - tidy warning flags `hispanic_count` as a demographic-looking wide column; transform and contract intentionally serve NIBRS ethnicity as count partitions because race and ethnicity are separate NIBRS fields.
- Section 15b quality-check coverage (cross-column invariants authored): PASS - authored checks cover age partition, ethnicity partition, race and sex partition sums, state >= county totals, Group B state-only/start-year constraints, coverage year mapping, offense dependent attributes, and agencies_reporting consistency.

## Manifest Verification

- Files processed coverage: PASS - manifest covers Group A `NIBRS_ARRESTEE.csv` for 2018-2024 and Group B `NIBRS_ARRESTEE_GROUPB.csv` for 2022-2024, matching the bronze structure report.
- Categorical and recode coverage: PASS - all recorded categoricals have `unmapped_count: 0`; observed gold values match actual gold distincts.
- Row-count reconciliation: PASS - raw bronze arrestee records collapse by aggregation into gold cells. Direct annual ledger matched state `demographic=all` sums exactly: 2018 290, 2019 20,226, 2020 63,873, 2021 86,668, 2022 179,757, 2023 183,273, 2024 189,351.
- Metric stats sanity: PASS - all count metrics are non-null and non-negative; `arrest_count` min 1, max 30,039.

## Row and Join Accounting

- Bronze file/year disposition: PASS - seven shared zips checksum-match the bronze structure report; arrestee Group A rows are processed for all years; Group B report rows are processed only for 2022-2024 as documented.
- Filter accounting: PASS - 10,874 `multiple_indicator = M` duplicate arrestee segments are explicitly excluded, and 12 exact duplicate 2018 agency roster rows are dropped before joins.
- Join accounting: PASS - direct checks found zero unmatched incident/agency/ORI joins for all years; agency roster keys and crosswalk ORIs are unique after the documented 2018 exact-duplicate roster removal.
- Deduplication accounting: PASS - natural-key collision guard runs before `deduplicate_by_levels`; actual gold duplicate grain count is 0.
- Aggregation/unpivot accounting: PASS - each arrestee expands to `all`, one race, and one sex demographic slice, then aggregates to county/state cells. Recomputed sample cells matched gold exactly.

## Reconciliation Checks

- Artifact freshness: PASS - freshness gate passed; manifest, contract, and validation are current.
- Contract freshness: PASS - contract was emitted after export from the current transform; no `_metadata.json` dependency.
- Year coverage: PASS - gold years are 2018-2024, matching all shared zips.
- Row preservation: PASS - state `all` sums equal counted bronze arrestee records after `M` filtering plus Group B report rows where present.
- Column coverage: PASS - served columns have lineage from bronze fields, filename year, shared offense vocabulary, ORI county crosswalk, or documented constants.
- Recode accuracy: PASS - era-scoped race, ethnicity, offense, arrest type, age bucket, and coverage recodes match bronze values and documented source lookups.
- Asian-family demographic recodes (Section 5b): PASS - bronze publishes split Asian and Pacific Islander race codes in both eras; gold contains `asian` and `pacific_islander` and no `asian_pacific_islander`.
- Demographic mutual exclusivity (Section 5a): PASS - sample 2024 state drug/narcotic on-view race rows sum exactly to `all` (14,710), and no combined Asian/Pacific Islander rollup is present.
- Demographic collision aggregation before dedup (Section 5): N/A - each raw race/sex label maps to one distinct canonical key; no colliding demographic aliases are observed.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, Section 1): PASS - actual parquet order follows `STANDARD_COLUMNS` minus `detail_level`.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, Sections 11/12): PASS - no forbidden columns are present in exported parquet.
- Canonical column vocabulary (Section 16): PASS - validator canonical vocabulary passes; criminal-justice-specific columns use county FIPS and count metrics.
- Shared categorical utilities applied (Section 10a): PASS - demographic normalization uses `normalize_demographic_column`; education grade/subject utilities are N/A.
- Tidy long format (Section 9): PASS - offense type, arrest type, race/sex demographic, coverage, and segment are categorical rows/columns; ethnicity and age are intentionally metric partitions with authored sum checks.
- FK keys present in dimension tables (Section 13): PASS - validator confirms county and demographic FKs resolve.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - contract exposes independent categoricals and FK descriptors, with `arrest_count` as key metric.
- Standards compliance (catch-all for Sections 1-16): PASS - no suppression is present, counts are derived not masked, geography nulling is domain-driven, and validation is last in `main()`.

## Spot Checks

### Check 1

- Bronze: `GA-2020.zip:NIBRS_ARRESTEE.csv`, Fulton `county_fips=13121`, `offense_type_id=51 -> 13B`, `arrest_type_id=1`, after excluding `M` rows. Sample arrestees include `41993806`, `41993723`, `38720400`, `38726300`, `38726299`.
- Transform path: `_load_linked_arrestees()` lines 385-478, `_attach_county()` lines 535-632, `_recode()` lines 640-729, `_expand_demographics()` lines 732-761, `_aggregate()` lines 769-844.
- Gold: 2020 county row `demographic=all`, `reporting_segment=group_a_incident_linked`, `offense_type=simple_assault`, `arrest_type=on_view` has `arrest_count=350`, `juvenile_count=13`, `adult_count=337`, `age_unknown_count=0`, `hispanic_count=7`, `not_hispanic_count=290`, `ethnicity_unknown_count=53`.
- Result: MATCH

### Check 2

- Bronze: `GA-2024.zip:NIBRS_ARRESTEE_GROUPB.csv`, Group B DUI `offense_code=90D`, `arrest_type_id=2`, `sex_code=F`; sample arrestees include `52872352`, `52875440`, `53706357`, `54257095`, `55586414`.
- Transform path: `_load_groupb_arrestees()` lines 481-532, `_recode()` lines 640-729, `_expand_demographics()` lines 732-761, `_aggregate()` lines 769-844.
- Gold: 2024 state row `county_fips=NULL`, `demographic=female`, `reporting_segment=group_b_arrest_report`, `offense_type=driving_under_the_influence`, `arrest_type=summoned_cited` has `arrest_count=359`, `juvenile_count=3`, `adult_count=356`, `age_unknown_count=0`, `hispanic_count=39`, `not_hispanic_count=257`, `ethnicity_unknown_count=63`.
- Result: MATCH

### Check 3

- Bronze: `GA-2024.zip:NIBRS_ARRESTEE.csv` rows with `multiple_indicator=M`, e.g. arrestees `56545346`, `56545347`, `58400745`, `58400750`, `59176488`, are duplicate segments for one physical arrest clearing multiple incidents.
- Transform path: `_load_linked_arrestees()` lines 432-446 records and excludes `M` rows before aggregation.
- Gold: 2024 direct ledger has `raw_group_a=96,433`, `m_filtered=1,522`, `group_a_counted=94,911`; 2024 state `demographic=all` Group A sum is exactly 94,911.
- Result: MATCH

### Check 4

- Bronze: `GA-2024.zip:NIBRS_ARRESTEE.csv`, state Group A `offense_code=35A`, `arrest_type_id=1` uses split race codes including Asian `40` and Pacific Islander `50`.
- Transform path: era-2 race map lines 248-255, demographic expansion lines 732-761, race partition quality SQL in the contract.
- Gold: 2024 state `drug_narcotic_violations`, `on_view`, Group A rows include `asian=76`, `pacific_islander=7`, `black=8,159`, `native_american=15`, `race_unknown=185`, `white=6,268`; race sum is 14,710 and equals `all=14,710`.
- Result: MATCH

## Notes

- The topic uses shared bronze zips from `data/bronze/criminal_justice/fbi_cde/nibrs_offenses/`; the absence of data files directly under `nibrs_arrests/` is intentional and documented by the bronze structure report and transform.
- I did not read prior `data-review-claude.md` or any existing Codex review before completing this report.
