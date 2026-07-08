# Data Review: fatal_crashes

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: bronze FARS accident-table rows reconcile to gold county/state totals, the contract and validator are fresh and passing, and no must-fix data accuracy defects were found.

## Summary

- Review date: 2026-07-02
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH — transform mtime `2026-07-02T22:51:24.904463+00:00`; manifest generated `2026-07-02T22:51:42.723834+00:00`; validation timestamp `2026-07-02T22:52:39.356851+00:00`; validation passed.

## Files Reviewed

- Transform: `src/etl/criminal_justice/traffic_safety/fatal_crashes/transform.py`
- Contract: `contracts/criminal_justice/fatal_crashes.odcs.yaml`
- Bronze files: 50 annual FARS national zip files, `FARS1975NationalCSV.zip` through `FARS2024NationalCSV.zip`
- Gold files: 100 parquet files, `year=1975` through `year=2024`, with `counties.parquet` and `states.parquet` in each year
- Manifest: `data/gold/criminal_justice/fatal_crashes/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/fatal_crashes/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/CLAUDE.md`, `src/etl/criminal_justice/CLAUDE.md`, and relevant `src/utils/` contract/transform/validation modules.

## Contract Verification

- Schema/parquet column match: PASS — contract properties and all parquet files use `year`, `county_fips`, `fatal_crashes`, `traffic_fatalities`, `crashes_with_drunk_driver` in that order.
- Column roles and grain: PASS — `year` and nullable `county_fips` define the contract grain; metrics are correctly marked as metrics; state rows are represented by NULL `county_fips`.
- Metric units and derived quality checks: PASS — all metrics are `unit: count`; contract includes non-negative checks plus topic-specific consistency checks.
- Categorical enums: N/A — there are no served categorical columns; `county_fips` is an FK identifier, not an enum-bearing categorical.
- Detail levels and layout metadata: PASS — contract advertises `counties` and `states`, default `counties`, and `criminal_justice/fatal_crashes/year={year}/{detail}.parquet`; gold layout matches.
- Foreign-key descriptors: PASS — `county_fips -> counties.county_fips`; validator confirms all 159 county keys resolve.
- Schema hash/version consistency: PASS — contract version is `1.0.0`, `schema_hash` is `ff74843cd70be4c3f61b4b8dbf5691ef2520065098bd90c74d018353d232942e`, and available years are 1975-2024 with no gaps.

## Validator Verification

- `_validation.json` fresh + passing: PASS — validation timestamp is after manifest generation and `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS — 19 pass, 0 fail; all 13 contract quality SQL checks pass.
- Validator warnings explained: PASS — the only warning is 100% NULL `crashes_with_drunk_driver` in 2021-2024, matching the documented removal of `DRUNK_DR` after 2020.
- §15b quality-check coverage (cross-column invariants authored): PASS — contract checks cover fatality count >= crash count, zero crash/fatality co-null behavior, drinking-driver subset, 1975-2020 vs 2021+ alcohol coverage, 159 counties per year, one state row per year, and state totals >= county sums.

## Manifest Verification

- Files processed coverage: PASS — manifest lists all 50 bronze zip files, one per year, matching the current bronze inventory and checksum gate.
- Categorical and recode coverage: PASS — `county_fips` mapping has `unmapped_count: 0`; invalid/sentinel county codes intentionally map to NULL and are preserved in state totals only.
- Row-count reconciliation: PASS — manifest `total_gold` is 8,000, matching actual parquet rows (50 years * 160 rows); manifest `total_bronze` is 66,916 Georgia crash rows. The apparent shrink is explained by county/state aggregation plus densification, not row loss.
- Metric stats sanity: PASS — counts are non-negative; `traffic_fatalities >= fatal_crashes`; `crashes_with_drunk_driver` is populated through 2020 and NULL after 2020.

## Row and Join Accounting

- Bronze file/year disposition: PASS — every annual zip from 1975-2024 is processed; the accident table is read directly from each zip and scoped to Georgia rows (`STATE = 13`).
- Filter accounting: PASS — non-Georgia national rows are explicitly recorded as out of scope (`1,805,548` rows across all files); no Georgia crash rows are dropped.
- Join accounting: PASS — county FIPS resolution validates candidate `13` + zero-padded FARS county code against the 159-row counties dimension; 2016, 2018, and 2024 `COUNTYNAME` label checks showed 0 normalized name mismatches and 0 missing dimension keys.
- Deduplication accounting: PASS — aggregation produces unique county/year and state/year rows; validator grain check finds no duplicate grain tuples.
- Aggregation/unpivot accounting: PASS — crash-level bronze rows collapse to county-year rows and one statewide row per year. Direct recomputation from bronze matched every statewide `fatal_crashes`, `traffic_fatalities`, and 1975-2020 `crashes_with_drunk_driver` value.

## Reconciliation Checks

- Artifact freshness: PASS — bronze freshness gate reports all 50 checksums match and no unanalyzed files.
- Contract freshness: PASS — contract is emitted from the current transform/gold path and there is no `_metadata.json` dependency.
- Year coverage: PASS — 1975-2024 present in bronze, manifest, contract, and gold.
- Row preservation: PASS — all Georgia fatal-crash rows contribute to statewide totals; valid county-coded rows contribute to county totals; 126 invalid/unknown county-coded rows across 21 years remain in state totals only.
- Column coverage: PASS — served metrics trace to row count (`fatal_crashes`), `FATALS` sum (`traffic_fatalities`), and `DRUNK_DR >= 1` count through 2020; optional future metrics (`PEDS`, vehicles, person demographics) are documented as out of v1 scope.
- Recode accuracy: PASS — FARS county codes resolve to Georgia county FIPS when dimension-valid; invalid codes become NULL rather than fabricated county keys.
- Asian-family demographic recodes (§5b): N/A — no demographic column or race buckets are served.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): N/A — no demographic column.
- Demographic collision aggregation before dedup (§5): N/A — no demographic column.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS — actual parquet order is `year`, `county_fips`, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS — parquet contains only fact keys and metrics; `detail_level` is encoded in filenames and absent from parquet.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS — no forbidden canonical variants are present.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A — no grade, subject, or demographic categorical output.
- Tidy long format (§9 — no demographics/years/components as column names): PASS — no wide year/component/category columns are served.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS — `county_fips` keys in county rows all resolve to the global counties dimension.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS — contract grain and FK descriptor match the served county/state layout; no extra categoricals are exposed.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS — FIPS IDs are strings, zero rows are real census zeros, post-2020 alcohol NULLs are documented, and no suppression markers are present in gold.

## Spot Checks

### Check 1

- Bronze: `FARS1975NationalCSV.zip` accident table, Georgia rows with `COUNTY = 45` (candidate `13045`): 14 crash rows, `sum(FATALS) = 15`, `count(DRUNK_DR >= 1) = 6`.
- Transform path: `transform_file()` lines 214-273 reads GA crash rows; `_resolve_county_fips()` lines 281-331 maps county codes; `_build_county_rows()` lines 351-394 aggregates.
- Gold: `year=1975/counties.parquet`, `county_fips = 13045`: `fatal_crashes = 14`, `traffic_fatalities = 15`, `crashes_with_drunk_driver = 6`.
- Result: MATCH

### Check 2

- Bronze: `FARS2024NationalCSV.zip` accident table, Georgia rows with `COUNTY = 121` (Fulton, `13121`): 91 crash rows, `sum(FATALS) = 95`; `DRUNK_DR` absent from the source era.
- Transform path: post-2020 era detection at lines 216-266 emits typed NULL `drunk_dr`; aggregation at lines 340-347 preserves NULL when no `DRUNK_DR` values exist.
- Gold: `year=2024/counties.parquet`, `county_fips = 13121`: `fatal_crashes = 91`, `traffic_fatalities = 95`, `crashes_with_drunk_driver = NULL`.
- Result: MATCH

### Check 3

- Bronze: `FARS1980NationalCSV.zip` contains 27 Georgia crash rows with invalid county codes (`124`, `262`, `507`, `510`), totaling 29 fatalities.
- Transform path: `_resolve_county_fips()` lines 281-331 maps invalid dimension-missing candidates to NULL; `_build_state_rows()` lines 397-411 includes all Georgia crashes in state totals while county rows exclude NULL `county_fips`.
- Gold: 1980 statewide row exceeds summed county rows by 27 `fatal_crashes` and 29 `traffic_fatalities`, exactly matching the invalid-county bronze rows.
- Result: MATCH

### Check 4

- Bronze: `FARS2024NationalCSV.zip` has zero Georgia crash rows resolving to `county_fips = 13037`.
- Transform path: `_build_county_rows()` lines 351-394 left-joins aggregate county rows to the full 159-county grid and fills missing crash/fatality counts with 0.
- Gold: `year=2024/counties.parquet`, `county_fips = 13037`: `fatal_crashes = 0`, `traffic_fatalities = 0`, `crashes_with_drunk_driver = NULL`.
- Result: MATCH

## Notes

- The manifest's derived `total_filtered` is not interpreted as data loss for this topic because the transform deliberately collapses crash-level bronze rows into aggregate county/state rows. The authoritative preservation checks are the direct aggregate recomputations and the contract quality checks.
- No required fixes were identified.
