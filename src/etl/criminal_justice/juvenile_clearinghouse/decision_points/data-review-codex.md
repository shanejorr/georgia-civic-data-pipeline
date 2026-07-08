# Data Review: decision_points

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Fresh artifacts, passing validator, complete Raw Data 1 recomputation, and targeted bronze-to-gold traces found no transform accuracy defects.

## Summary

- Review date: 2026-07-02
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze checksums match; transform mtime 2026-07-02T13:20:54Z is older than manifest 2026-07-02T13:22:21Z; validation 2026-07-02T13:23:15Z is newer than the manifest and passed.

## Files Reviewed

- Transform: `src/etl/criminal_justice/juvenile_clearinghouse/decision_points/transform.py`
- Contract: `contracts/criminal_justice/decision_points.odcs.yaml`
- Bronze files: `decision_points_raw_data_1_2026-06.csv` (309,637 rows, 2010-2025, ingested) and `decision_points_raw_data_2_2026-06.csv` (92,656 rows, 2005-2025, deliberately excluded as a separate county/month case-flow universe)
- Gold files: 32 parquet files under `data/gold/criminal_justice/decision_points/year=2010` through `year=2025`, with `counties.parquet` and `states.parquet` in each year
- Manifest: `data/gold/criminal_justice/decision_points/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/decision_points/_validation.json`
- Supporting docs: `data/bronze/criminal_justice/juvenile_clearinghouse/decision_points/bronze-data-structure.md`, `_provenance.md`, `docs/contract-creation.md`, `docs/codex-review-contract.md`, data-cleaning standards, and `src/etl/criminal_justice/CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS - `_validation.json` reports all 32 parquet files match the contract; actual columns are `year`, `county_fips`, `demographic`, and 11 `num_*` count metrics in contract order.
- Column roles and grain: PASS - roles are `year`, `fk_county`, `fk_demographic`, and metric counts; grain is `year`, `county_fips`, `demographic`, with NULL `county_fips` uniquely identifying state rows.
- Metric units and derived quality checks: PASS - all 11 metrics have `unit: count`; contract emits non-negative checks plus topic invariants for offense/youth, petitions/offenses, adjudications/offenses, secure placement subset, and race/gender event-count partitions.
- Categorical enums: PASS - `demographic` enum has 9 values matching gold: `all`, `asian`, `black`, `female`, `hispanic`, `male`, `native_american`, `other`, `white`.
- Detail levels and layout metadata: PASS - `detail_levels` are `counties` and `states`, `default_detail` is `counties`, partition is `year`, and path template is `criminal_justice/decision_points/year={year}/{detail}.parquet`.
- Foreign-key descriptors: PASS - contract declares `county_fips -> counties` and `demographic -> demographics`; validation reports all 159 county keys and all 9 demographic keys resolve.
- Schema hash/version consistency: PASS - version is `1.0.0`, schema hash is `09e4b9320e0df5a0e33d73774ae2acbab749fde198422379ed9071101a93d642`, year range is `2010-2025`, and available years have no gaps.

## Validator Verification

- `_validation.json` fresh + passing: PASS - timestamp `2026-07-02T13:23:15.042633+00:00`, generated after manifest `2026-07-02T13:22:21.235559+00:00`, with `"passed": true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 20 pass, 0 fail, 0 warning; `contract_quality_sql` says all 19 SQL checks pass.
- Validator warnings explained: N/A - no warnings were emitted.
- S15b quality-check coverage (cross-column invariants authored): PASS - authored checks cover the key count invariants and event-count partition checks. Distinct-youth counts are intentionally non-additive across county and demographic axes, documented in the contract, so no partition check is expected for `num_youth`.

## Manifest Verification

- Files processed coverage: PASS - manifest records both bronze CSVs. Raw Data 1 is processed as `raw_data_1_youth_level`; Raw Data 2 is recorded as `raw_data_2_case_flow_EXCLUDED` because it is a separate county/month aggregate universe.
- Categorical and recode coverage: PASS - `county_fips` saw 160 bronze county labels including `OUT OF STATE`; all Georgia counties mapped to FIPS and `OUT OF STATE` is explicitly marked state-rollup-only. `demographic` saw 8 raw race/gender labels and all mapped with `unmapped_count: 0`.
- Row-count reconciliation: PASS - manifest total bronze is 309,637 Raw Data 1 rows and total gold is 16,551 aggregate rows. Explicit filters are 38 byte-identical duplicate rows and 3,300 `OUT OF STATE` rows excluded only from county rows; the rest of the reduction is expected aggregation from youth-level microdata to county/state x demographic cells.
- Metric stats sanity: PASS - all gold metrics are non-null, non-negative Int64 counts; independent checks found zero negative metrics, zero `num_offenses < num_youth`, and zero secure-placement counts exceeding `num_youth`.

## Row and Join Accounting

- Bronze file/year disposition: PASS - Raw Data 1 covers 2010-2025 and feeds gold; Raw Data 2 covers 2005-2025 and is deliberately excluded with manifest coverage because it has different grain, coverage, and metrics.
- Filter accounting: PASS - recomputation found 38 exact duplicate Raw Data 1 rows removed in 2025 and 3,300 `OUT OF STATE` rows excluded from county-level rows while retained in the state rollup.
- Join accounting: PASS - county-name resolution produced zero unmatched non-`OUT OF STATE` county names; FK validation confirms the resulting 159 county FIPS values resolve in the counties dimension.
- Deduplication accounting: PASS - exact duplicates are removed before aggregation; post-aggregation duplicate natural-key count is 0, and the safety-net `deduplicate_by_levels(sort_col="num_youth")` has no divergent rows to resolve.
- Aggregation/unpivot accounting: PASS - no unpivot is used. An independent aggregation from post-dedup Raw Data 1 to county/state x demographic rows produced exactly 16,551 expected rows, zero missing/extra keys, and zero metric mismatches against gold.

## Reconciliation Checks

- Artifact freshness: PASS - bronze checksum gate passed for both files; manifest and validation are fresh relative to transform.py.
- Contract freshness: PASS - contract reflects current gold schema and has no `_metadata.json` dependency.
- Year coverage: PASS - gold years are 2010-2025, matching ingested Raw Data 1. There are no 2005-2009 gold rows because those years appear only in excluded Raw Data 2.
- Row preservation: PASS - Raw Data 1 rows are preserved by documented aggregation, exact duplicate removal, or `OUT OF STATE` county-level exclusion/state-level retention.
- Column coverage: PASS - Raw Data 1 fact keys and metrics are mapped; `NEWJUVID` is consumed only for distinct counts, county names become `county_fips`, race/gender become `demographic`, court type is summed over because source codes are undocumented, and the active/terminated flag is omitted as a publication-time status.
- Recode accuracy: PASS - county FIPS and demographic recodes match actual bronze values and manifest mappings.
- Asian-family demographic recodes (S5b): PASS - actual Raw Data 1 race values are `AmInd`, `Asian`, `Black`, `Hispanic`, `Other`, `White`; Raw Data 2 likewise has no Pacific Islander, Native Hawaiian, or NHPI label. The transform maps `Asian -> asian` with a documented caveat and emits no `asian_pacific_islander` rollup.
- Demographic mutual exclusivity (S5a - no rollup row alongside split source rows in the same category): PASS - gold contains `asian` only, not `asian_pacific_islander` or `pacific_islander`, and event counts partition exactly across race and gender. Source segment inconsistencies make `num_youth` non-additive for a small number of groups; the contract documents that limitation.
- Demographic collision aggregation before dedup (S5): PASS - grouping happens after normalization, so labels that normalize to the same value aggregate before dedup. No observed Raw Data 1 labels collide into the same canonical value.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, S1): PASS - parquet order is `year`, `county_fips`, `demographic`, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, S11/S12): PASS - gold parquet contains no topic/detail columns, county names, youth IDs, court-type codes, active flags, or crosswalk IDs.
- Canonical column vocabulary (S16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - topic has criminal-justice count metrics only; no forbidden vocabulary variants were detected by validation.
- Shared categorical utilities applied (S10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no grade or subject columns. Demographic normalization uses the shared demographic utility.
- Tidy long format (S9 - no demographics/years/components as column names): PASS - demographic groups are values, years are partitions/column values, and decision-point measures are metric columns.
- FK keys present in dimension tables (S13 - `district_code`, `school_code`, `demographic`): PASS - `county_fips` and `demographic` FKs resolve in global dimensions; no education FKs apply.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - contract exposes the natural grain, key metric `num_youth`, FK joins, and county/state detail levels needed by REST/MCP consumers.
- Standards compliance (catch-all for S1-S16 items not enumerated above): PASS - the table is county/state fact data, no PII or name columns are exported, no suppression markers survive, zero is real per contract, and all metrics are source-backed counts.

## Spot Checks

### Check 1

- Bronze: Raw Data 1 row for `NEWJUVID=H16752085`, `year=2020`, `County Name=FULTON`, `Race Value=Black`, `Gender=MALE`, `Number of offenses=23`, `Petitions=13`, `Delinquent Adjudications=23`, `Unique Adjudication Date Count=13`, `Commitments orders=13`.
- Transform path: `_transform_youth_level()` resolves Fulton to `13121`; `_aggregate_slices()` groups by `year`, `county_fips`, and normalized race demographic, summing event metrics and counting distinct `NEWJUVID`.
- Gold: `year=2020`, `county_fips=13121`, `demographic=black` has `num_youth=312`, `num_offenses=1288`, `num_petitions=404`, `num_delinquent_adjudications=869`, `num_adjudication_dates=492`, `num_commitment_orders=338`, exactly matching direct aggregation from all matching bronze rows.
- Result: MATCH

### Check 2

- Bronze: 2025 `OUT OF STATE` sample rows include `NEWJUVID=I19844585`, `I19844605`, and `I19844625`, all with `county_fips=NULL` after county resolution; 2025 `OUT OF STATE` rows sum to `125` offenses after exact duplicate removal.
- Transform path: `_resolve_county_fips()` marks `OUT OF STATE` as state-rollup-only; county aggregation filters NULL `county_fips`, while state aggregation uses the full youth-level file.
- Gold: 2025 `demographic=all` state `num_offenses=29008`; sum of 2025 county `demographic=all` `num_offenses=28883`; difference is `125`, matching the `OUT OF STATE` bronze offenses.
- Result: MATCH

### Check 3

- Bronze: Raw Data 1 row `NEWJUVID=D9172705`, `year=2010`, `County Name=BALDWIN`, `county_fips=13009`, `Race Value=Black`, `Gender=MALE`, `Secure Detention (RYDC)=1`, `Secure Confinement (YDC)=0`, `Number of offenses=2`.
- Transform path: `_aggregation_exprs()` counts distinct `NEWJUVID` where `_rydc == 1` and where `_ydc == 1` for each cell.
- Gold: `year=2010`, `county_fips=13009`, `demographic=all` has `num_youth=208`, `num_secure_detention_youth=1`, `num_secure_confinement_youth=0`, matching direct bronze flag aggregation.
- Result: MATCH

### Check 4

- Bronze: Raw Data 2 has 92,656 rows, years 2005-2025, 12 months, and case types `CHINS`/`DELINQUENCY`; sample rows include `County=Bartow`, `Year=2005`, `Month=1`, `Case Type=CHINS`, `Race=HISPANIC/OTHER/UNKNOWN`.
- Transform path: `transform_file()` records Raw Data 2 as `raw_data_2_case_flow_EXCLUDED` and returns `None` because it is a different county/month aggregate universe.
- Gold: no rows have `year < 2010`, and no Raw Data 2-only columns such as `month`, `case_type`, or referred/adjudicated case-flow metrics appear in the parquet schema.
- Result: MATCH

## Notes

- Full independent recomputation from Raw Data 1 after exact duplicate removal produced the same 16,551 gold rows and zero metric mismatches.
- Source segment inconsistencies were quantified post-dedup: 224 county youth-year groups have more than one race value for the same `NEWJUVID`, and 244 have more than one gender value. The transform preserves event-count partitioning and documents `num_youth` non-additivity rather than fabricating a single corrected attribute.
- No prior review report was used as evidence for these findings.
