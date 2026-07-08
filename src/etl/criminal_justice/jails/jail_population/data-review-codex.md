# Data Review: jail_population

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: The current gold output is fresh, validator-passing, and reconciles to the bronze county-table data with no must-fix accuracy defects found.

## Summary

- Review date: 2026-07-02
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH — `scripts/check_bronze_freshness.py criminal_justice jails jail_population` passed for all 223 bronze files; transform mtime `2026-07-02T20:48:28.940771+00:00` precedes manifest `2026-07-02T20:48:30.723739+00:00`; validation timestamp `2026-07-02T20:49:43.442552+00:00` is newer than the manifest and reports `passed: true`.

## Files Reviewed

- Transform: `src/etl/criminal_justice/jails/jail_population/transform.py`
- Contract: `contracts/criminal_justice/jail_population.odcs.yaml`
- Bronze files: 222 `jail_report_YYYY-MM.html` files for 2007-11 through 2026-06, plus excluded `annual_totals_2026-07-02.csv`
- Gold files: 40 parquet files, `counties.parquet` and `states.parquet` for each year 2007-2026
- Manifest: `data/gold/criminal_justice/jail_population/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/jail_population/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/CLAUDE.md`, `src/etl/criminal_justice/CLAUDE.md`, and relevant `src/utils/` modules.

## Contract Verification

- Schema/parquet column match: PASS — contract properties exactly match the parquet column order: `year`, `county_fips`, `month`, `reporting_status`, six count metrics, and `counties_reporting`.
- Column roles and grain: PASS — contract grain is `year`, `county_fips`, `month`, `reporting_status`; `month` and `reporting_status` are categoricals; `county_fips` is the county FK.
- Metric units and derived quality checks: PASS — all metrics use `unit: count`; the contract includes non-negative checks for each count metric and topic-specific consistency checks.
- Categorical enums: PASS — `month` enum is `01`-`12`; `reporting_status` enum is `no_jail`, `not_reported`, `reported`; actual gold values match.
- Detail levels and layout metadata: PASS — detail levels are `counties` and `states`; path template is `criminal_justice/jail_population/year={year}/{detail}.parquet`.
- Foreign-key descriptors: PASS — `county_fips -> counties.county_fips`; validator and manual anti-join found 159 distinct county keys and 0 orphans.
- Schema hash/version consistency: PASS — version `1.0.0`; schema hash `34227ee0354cfbf2779d567025753aaaafce80b3e1f39276b3af1d30c5198e72`.

## Validator Verification

- `_validation.json` fresh + passing: PASS — `passed: true`, 18 pass / 0 fail / 2 warning.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS — `contract_parquet_schema`, `grain_uniqueness`, `contract_quality_sql`, `foreign_keys`, and `canonical_vocabulary` all passed.
- Validator warnings explained: PASS — tidy warning is a false positive on `other_inmates` matching the word "other"; 2026 null-rate spikes are explained by voluntary-survey coverage collapse (2026-06 has 100 non-reporting counties).
- §15b quality-check coverage (cross-column invariants authored): PASS — authored checks cover not-reported null metrics, no-jail zero counts, state total vs county sum, `counties_reporting`, state/county-only structural nulls, 159 county rows per month, and `counties_reporting <= 159`. The component-sum identity is intentionally not enforced after 2023-05 because the source stops closing.

## Manifest Verification

- Files processed coverage: PASS — current bronze inventory and manifest both contain 223 files; no missing or extra files. The convenience CSV is recorded as excluded.
- Categorical and recode coverage: PASS — `county_fips`, `month`, and `reporting_status` all have `unmapped_count: 0`; county-name variants (`DeKalb`/`Dekalb`, `McDuffie`/`Mcduffie`, `McIntosh`/`Mcintosh`) map to the same FIPS values.
- Row-count reconciliation: PASS — manifest bronze rows, manifest gold rows, and actual gold rows all equal 35,520. Every report month has 159 county rows and 1 state row.
- Metric stats sanity: PASS — count metrics are non-negative in gold; the five impossible source count cells are masked to NULL and recorded in `masked_values`.

## Row and Join Accounting

- Bronze file/year disposition: PASS — 222 monthly HTML files are processed; 2008-01 and 2008-02 are absent from source and absent from gold; 2007-11 through 2026-06 otherwise produce 222 months.
- Filter accounting: PASS — no data rows are filtered; the per-file `TOTALS` row is consumed as parse/state-rollup evidence, and `annual_totals_2026-07-02.csv` is excluded as retrieval-date chart chrome.
- Join accounting: PASS — county-name-to-FIPS resolution is one-to-one after suffix/casing normalization; all 159 FIPS keys resolve in `data/gold/_dimensions/counties.parquet`.
- Deduplication accounting: PASS — duplicate natural keys are 0 in actual gold; `assert_no_natural_key_collisions` runs before the documented safety-net dedup.
- Aggregation/unpivot accounting: PASS — no unpivot occurs. State rows are derived by summing final county rows; manual checks found 0 state-vs-county sum mismatches for all six count metrics.

## Reconciliation Checks

- Artifact freshness: PASS — bronze checksums match the profile and transform/manifest/validation timestamps are ordered correctly.
- Contract freshness: PASS — contract schema matches current parquet and has no `_metadata.json` dependency.
- Year coverage: PASS — gold covers years 2007-2026 and exactly the expected 222 months; missing months are only 2008-01 and 2008-02.
- Row preservation: PASS — 160 bronze rows per month (159 counties + `TOTALS`) correspond to 159 county rows + 1 state row per month.
- Column coverage: PASS — fact keys, categoricals, and count metrics from the bronze classification are represented or intentionally excluded; corrupted percent columns are dropped as documented derivations.
- Recode accuracy: PASS — `all_count_cells_blank -> not_reported`, `no_jail_suffix -> no_jail`, and `count_data_present -> reported` are semantically correct, with isolated `NO JAIL` reclassifications separately recorded.
- Asian-family demographic recodes (§5b): N/A — no demographic column or race buckets.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): N/A — no demographic column.
- Demographic collision aggregation before dedup (§5): N/A — no demographic column.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS — actual parquet order is `year`, `county_fips`, `month`, `reporting_status`, metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS — exported parquet has no forbidden columns or county names.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): N/A — education vocabulary patterns do not apply; criminal-justice names are descriptive and pass validator vocabulary.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A — no grade or subject columns.
- Tidy long format (§9 — no demographics/years/components as column names): PASS — `month` is a categorical in the row grain; custody components are separate same-row metrics, not categorical levels.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS — all 159 county FIPS keys resolve in the global counties dimension.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS — `month` and `reporting_status` are independent filterable categoricals; county FK joins are contract-described.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS — count types, NULL semantics, geography nulling, year partitioning, and manifest/validation outputs conform.

## Spot Checks

### Check 1

- Bronze: `jail_report_2019-03.html`, Fulton row has total `2624`, capacity `2688`, state `106`, awaiting `2042`, county sentence `149`, other `327`.
- Transform path: `transform_file()` lines 329-406 parses six count cells, maps county name to FIPS in `_resolve_county_fips()` lines 469-495, exports county row.
- Gold: `year=2019`, `month='03'`, `county_fips='13121'` has `reporting_status='reported'` and the same six counts.
- Result: MATCH

### Check 2

- Bronze: `jail_report_2019-03.html`, `Quitman - NO JAIL` row has all six count cells `0`.
- Transform path: marker/status logic lines 380-403 maps `no_jail_suffix` to `no_jail`; quality check `no_jail_implies_zero_counts` enforces zeros.
- Gold: `year=2019`, `month='03'`, `county_fips='13239'` has `reporting_status='no_jail'` and all six count metrics `0`.
- Result: MATCH

### Check 3

- Bronze: `jail_report_2021-07.html`, Baker row has all six count cells blank.
- Transform path: marker/status logic lines 380-403 maps all blank count cells to `not_reported`; quality check `not_reported_implies_null_metrics` enforces NULL metrics.
- Gold: `year=2021`, `month='07'`, `county_fips='13007'` has `reporting_status='not_reported'` and all six count metrics NULL.
- Result: MATCH

### Check 4

- Bronze: `jail_report_2018-09.html`, Macon/Madison/Marion/McDuffie/McIntosh component sums are shifted: Macon components sum to 107 (McDuffie total), Madison to 79 (McIntosh total), Marion to 25 (Macon total), McDuffie to 110 (Madison total), McIntosh to 21 (Marion total).
- Transform path: `_repair_2018_09_component_misalignment()` lines 414-466 verifies each shifted component sum against the owner total and reassigns components.
- Gold: the five county rows have component sums exactly equal to their own totals: Macon 25, Madison 110, Marion 21, McDuffie 107, McIntosh 79.
- Result: MATCH

### Check 5

- Bronze: `jail_report_2019-05.html`, Madison state-sentenced count is `0.01`; `jail_report_2024-03.html`, Pulaski state-sentenced count is `-3`; `jail_report_2025-07.html`, Long county-sentenced count is `-1`; `jail_report_2025-08.html`, Long other count is `-2`; `jail_report_2026-02.html`, Charlton other count is `-2`.
- Transform path: `_null_impossible_counts()` lines 554-588 masks non-integer and negative inmate counts and records them in the manifest.
- Gold: those five individual metric cells are NULL while the rest of each row is preserved; manifest `masked_values` records counts by column/year.
- Result: MATCH

### Check 6

- Bronze: Richmond has normal reported rows in 2024-05 (`total=1144`) and 2024-07 (`total=1172`) but `Richmond - NO JAIL` with zero counts in 2024-06; Fayette similarly has reported 2024-06/2024-08 rows around a `Fayette - NO JAIL` zero row in 2024-07.
- Transform path: `_reclassify_isolated_no_jail()` lines 498-551 identifies single-month `no_jail` flags surrounded by `reported` months and converts false zeros to `not_reported` NULLs.
- Gold: Richmond 2024-06 and Fayette 2024-07 are `reporting_status='not_reported'` with NULL count metrics, while adjacent months remain reported with their source counts.
- Result: MATCH

### Check 7

- Bronze: `jail_report_2026-06.html` county-table `TOTALS` row has total `12,664`, capacity `15,848`, state `1,190`, awaiting `8,558`, county sentence `1,424`, other `1,015`.
- Transform path: `_check_totals_row()` lines 306-327 verifies per-file county sums against the `TOTALS` row; `_build_state_rows()` lines 614-641 builds state rows from final county rows.
- Gold: 2026-06 state row has the same six counts and `counties_reporting=59`; county rows for that month are 56 `reported`, 3 `no_jail`, and 100 `not_reported`.
- Result: MATCH

## Notes

- The review did not read any prior `data-review-claude.md` or existing `data-review-codex.md` before forming findings.
- Validator warnings are review items, not blockers: the `other_inmates` tidy warning is semantic, not a wide-format defect; 2026 null-rate spikes are the expected coverage collapse documented in the transform and contract.
- No must-fix issues were found, so `## Required Fixes` is intentionally omitted.
