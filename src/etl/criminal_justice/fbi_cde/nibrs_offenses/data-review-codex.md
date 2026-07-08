# Data Review: nibrs_offenses

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Fresh contract, manifest, validation, bronze, and gold artifacts reconcile; no bronze-to-gold accuracy defects were found.

## Summary

- Review date: 2026-07-02
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH — transform mtime 2026-07-02T21:18:49Z, manifest generated_at 2026-07-02T21:19:06Z, contract mtime 2026-07-02T21:19:06Z, validation timestamp 2026-07-02T21:20:06Z with `"passed": true`; bronze checksum gate passed for all 8 profiled files.

## Files Reviewed

- Transform: `src/etl/criminal_justice/fbi_cde/nibrs_offenses/transform.py`
- Contract: `contracts/criminal_justice/nibrs_offenses.odcs.yaml`
- Bronze files: `GA-2018.zip` through `GA-2024.zip`, plus excluded sidecar `srs_estimates/estimated_crimes_1979_2024.csv`
- Gold files: 14 parquet files, `year=2018` through `year=2024`, each with `counties.parquet` and `states.parquet`
- Manifest: `data/gold/criminal_justice/nibrs_offenses/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/nibrs_offenses/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, data-cleaning standards/checklist, bronze/transform/review/fix/full-pipeline skills, `AGENTS.md`, `CLAUDE.md`, `src/etl/CLAUDE.md`, `src/etl/criminal_justice/CLAUDE.md`, `data/bronze/criminal_justice/fbi_cde/nibrs_offenses/bronze-data-structure.md`, and `src/etl/criminal_justice/fbi_cde/_nibrs_shared.py`

## Contract Verification

- Schema/parquet column match: PASS — `_validation.json` reports all 14 parquet files match contract order: `year`, `county_fips`, `coverage`, `offense_type`, `offense_category`, `crime_against`, and five count metrics.
- Column roles and grain: PASS — contract roles match transform declarations; grain is year + county_fips + coverage + offense_type + dependent category/class fields, with county FIPS nullable for state rows.
- Metric units and derived quality checks: PASS — all five metrics are `unit: count`; contract quality checks enforce non-negativity plus offense/component and incident-count invariants.
- Categorical enums: PASS — `coverage`, `offense_category`, and `crime_against` enums match gold and manifest values; `offense_type` has 52 observed snake_case values and no invalid fallback values.
- Detail levels and layout metadata: PASS — contract lists `counties` and `states`, default `counties`, partition by `year`, and path template `criminal_justice/nibrs_offenses/year={year}/{detail}.parquet`.
- Foreign-key descriptors: PASS — `county_fips` targets the global counties dimension; validator confirms all 154 populated county keys resolve.
- Schema hash/version consistency: PASS — contract version is `1.0.0`, year_range is `2018-2024`, available_years are 2018-2024, and schema_hash is present.

## Validator Verification

- `_validation.json` fresh + passing: PASS — validation timestamp is later than manifest generated_at and `"passed": true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS — 20 pass, 0 fail, 0 warning; 17 contract quality SQL checks pass.
- Validator warnings explained: N/A — no warnings.
- §15b quality-check coverage (cross-column invariants authored): PASS — checks cover completed + attempted = offense_count, incident_count bounds, state total >= county sum, agencies_reporting constancy, transition-year coverage labels, and offense_type functional dependency.

## Manifest Verification

- Files processed coverage: PASS — manifest covers all 7 NIBRS zips plus the SRS sidecar as `srs_estimates_EXCLUDED`; checksum freshness gate reports all 8 bronze files match with no unanalyzed files.
- Categorical and recode coverage: PASS — manifest records `attempt_status`, `county_fips`, `coverage`, `crime_against`, `offense_category`, and `offense_type`; all have `unmapped_count: 0`.
- Row-count reconciliation: PASS — 2,129,576 offense rows aggregate to 24,412 gold rows; per-year gold counts match parquet exactly. The large bronze-minus-gold delta is expected aggregation from offense rows to county/state/year/offense cells, not dropped source records.
- Metric stats sanity: PASS — count metrics are non-negative; no nulls; `incident_count` is between 1 and `offense_count`; no scale-sensitive rate/proportion metrics exist.

## Row and Join Accounting

- Bronze file/year disposition: PASS — `GA-2018.zip` through `GA-2024.zip` are processed as data years 2018-2024; the SRS estimated sidecar is deliberately excluded because it is state-grain estimated SRS data on an incompatible category vocabulary.
- Filter accounting: PASS — no offense rows are filtered; 12 exact duplicate 2018 agency roster rows are dropped before joins and recorded in the manifest.
- Join accounting: PASS — direct checks found no missing incident->agency ORI joins, no agency ORIs missing from `ori_to_county`, no unknown offense codes, and no invalid attempt flags in any year. The ORI crosswalk has 820 unique ORIs and no duplicate join keys.
- Deduplication accounting: PASS — natural-grain duplicate check found 0 duplicate gold rows; `deduplicate_by_levels` is a safety net only because there is one zip per data year.
- Aggregation/unpivot accounting: PASS — aggregation is from offense rows to county and state offense cells. State offense sums equal county sums in all observed years because no statewide no-county ORI reported offense rows.

## Reconciliation Checks

- Artifact freshness: PASS — transform, manifest, contract, validation, bronze checksums, and gold layout are mutually current.
- Contract freshness: PASS — contract was emitted from the current transform/gold and there is no `_metadata.json` dependency.
- Year coverage: PASS — expected 2018-2024 years are present; no extra gold years exist.
- Row preservation: PASS — raw offense row totals by year equal state-level `offense_count` sums: 879, 84,895, 332,191, 402,368, 434,291, 442,508, 432,444.
- Column coverage: PASS — fact columns are traceable to `data_year`, ORI crosswalk county, offense code lookup/vocabulary, attempt flag, distinct incident IDs, and agency roster counts.
- Recode accuracy: PASS — `C/A` become `completed/attempted`; years become `partial_adoption` for 2018-2019 and `full_participation` from 2020; observed offense codes map to the 2024 FBI lookup vocabulary.
- Asian-family demographic recodes (§5b): N/A — no demographic column or race fields are produced for this offense-segment topic.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): N/A — no demographic column.
- Demographic collision aggregation before dedup (§5): N/A — no demographic normalization.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS — parquet order is year, county FK, categoricals, then metrics; `detail_level` is not exported.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS — gold contains no forbidden fact-table columns.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): N/A — education assessment vocabulary does not apply; CJ names are descriptive and contract-consistent.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A — no grade or subject columns.
- Tidy long format (§9 — no demographics/years/components as column names): PASS — offense types/categories/classes are rows, not columns.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS — `county_fips` resolves in the counties dimension for all 154 populated county keys.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS — contract exposes county FK and categorical filters for coverage, offense_type, offense_category, and crime_against; dependent category/class fields are quality-checked as functions of offense_type.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS — suppression is correctly documented as absent, counts are integers, state geography is nulled, SRS/NIBRS methodology is not pooled, and PII/agency names stay out of gold.

## Spot Checks

### Check 1

- Bronze: `GA-2024.zip` `NIBRS_OFFENSE` rows with `offense_code=13B` and ORIs crosswalking to Fulton County `13121`: 3,884 rows, all `attempt_complete_flag=C`, 3,884 distinct incidents; statewide `13B` rows: 67,378.
- Transform path: `_load_offenses()` resolves code, `_attach_county()` joins incident -> agency -> ORI -> county, `_map_offense_vocabulary()` maps `13B` to `simple_assault` / `assault_offenses` / `person`, `_aggregate()` counts rows and distinct incidents.
- Gold: 2024 county `13121` / `simple_assault` has `offense_count=3884`, `completed_count=3884`, `attempted_count=0`, `incident_count=3884`, `agencies_reporting=24`; 2024 state row has `offense_count=67378`.
- Result: MATCH

### Check 2

- Bronze: `GA-2021.zip` DeKalb County `13089`, `offense_code=23H`: 9,194 offense rows, 9,097 completed, 97 attempted, 9,194 distinct incidents; statewide `23H`: 49,146 rows with 468 attempted.
- Transform path: era-2 native `offense_code` maps through the pinned vocabulary to `all_other_larceny` / `larceny_theft_offenses` / `property`; attempted/completed flags are counted into separate metric columns.
- Gold: 2021 county `13089` / `all_other_larceny` has `offense_count=9194`, `completed_count=9097`, `attempted_count=97`, `incident_count=9194`, `agencies_reporting=15`; state row has `offense_count=49146`, `attempted_count=468`.
- Result: MATCH

### Check 3

- Bronze: `GA-2020.zip` era-1 rows use `offense_type_id`; after same-zip `NIBRS_OFFENSE_TYPE` lookup, Fulton County `13121`, code `13B` has 2,376 rows, all completed, 2,376 distinct incidents; statewide code `13B` has 47,065 rows.
- Transform path: `_load_offenses()` joins `NIBRS_OFFENSE` to the same zip's `NIBRS_OFFENSE_TYPE` on `offense_type_id`, then uses the same aggregation path as era 2.
- Gold: 2020 county `13121` / `simple_assault` has `offense_count=2376`, `completed_count=2376`, `attempted_count=0`, `incident_count=2376`, `coverage=full_participation`; state row has `offense_count=47065`.
- Result: MATCH

### Check 4

- Bronze: `GA-2018.zip` Gwinnett County `13135`, code `35A`: 63 offense rows, all completed, 63 distinct incidents. The 2018 agency roster has 49 parsed rows but 37 unique `(agency_id, ori, data_year)` rows, with 12 exact duplicate groups.
- Transform path: `load_agencies()` drops exact duplicate roster rows before joins; `_aggregate()` counts unique reporting agencies and offense rows.
- Gold: 2018 county `13135` / `drug_narcotic_violations` has `offense_count=63`, `completed_count=63`, `attempted_count=0`, `incident_count=63`, `agencies_reporting=4`; 2018 state rows have `agencies_reporting=37`.
- Result: MATCH

## Notes

- The manifest's `total_filtered` is mechanically `total_bronze - total_gold`; for this topic it reflects aggregation collapse from offense rows to county/state cells. Direct row-ledger checks found no unexplained offense-row loss.
- The SRS estimates sidecar was inspected as a disposition item only. Its exclusion is code-backed and contract-documented; mixing estimated SRS index-crime history into raw NIBRS offense counts would violate the CJ domain methodology-break rule.
