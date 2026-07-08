# Data Review: inmate_population

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: The transform accurately extracts the GDC PDF matrix, intentionally filters the pre-2000 methodology-break era, and the served 2000-2024 gold rows match the bronze values exactly.

## Summary

- Review date: 2026-07-07
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze checksum matches `bronze-data-structure.md`; `transform.py` mtime `2026-07-07T04:06:26Z` is before manifest `2026-07-07T04:09:27Z`; `_validation.json` timestamp `2026-07-07T04:09:27Z` is after the manifest and reports `passed: true`.

## Files Reviewed

- Transform: `src/etl/criminal_justice/gdc/inmate_population/transform.py`
- Contract: `contracts/criminal_justice/inmate_population.odcs.yaml`
- Bronze files: `year_end_population_since_1925.pdf` plus `_provenance.md` and `bronze-data-structure.md`; current PDF SHA-256 is `817ede7ca7e9e0b4db75f2fc62e8ac1d4c841e25fc7cba8f856b1b229f444de8`.
- Gold files: 25 `year=2000` through `year=2024` `states.parquet` files, one row each, plus `_transform_manifest.json` and `_validation.json`.
- Manifest: `data/gold/criminal_justice/inmate_population/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/inmate_population/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/CLAUDE.md`, `src/etl/criminal_justice/CLAUDE.md`, relevant `src/utils/` contract/validation/transformer code, and sibling GDC transforms for PDF-source conventions.

## Contract Verification

- Schema/parquet column match: PASS - contract and all 25 parquet files have exactly `year`, `year_end_inmate_population` in that order.
- Column roles and grain: PASS - `year` is the sole primary key and `year_end_inmate_population` is the sole metric; one row per year is the real served grain after the 2000 floor.
- Metric units and derived quality checks: PASS - metric is `unit: count`, required, non-negative, and declared as the single `key_metric`.
- Categorical enums: N/A - the served frame has no categorical columns; `count_method` is not needed after the transform filters to the uniform `dec31_headcount` era.
- Detail levels and layout metadata: PASS - contract declares `detail_levels: [states]`, `default_detail: states`, `partition_columns: [year]`, and `path_template: criminal_justice/inmate_population/year={year}/{detail}.parquet`.
- Foreign-key descriptors: N/A - statewide-only report has no county, facility, or demographic key; contract `foreign_keys` is `[]`.
- Schema hash/version consistency: PASS - contract version is `1.0.0`; schema hash is `b4b589e9e20867a515acb0c9eefb94fb6cb1dadae82043f3484cc3f00110ee22`, matching the emitted two-column grain.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp is after manifest generation and reports 19 pass, 0 fail, 0 warning.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - `contract_parquet_schema`, `grain_uniqueness`, `contract_quality_sql`, `foreign_keys`, `canonical_vocabulary`, and `geography_nulling` all passed.
- Validator warnings explained: N/A - no warnings were emitted.
- Section 15b quality-check coverage (cross-column invariants authored): PASS - no partition/co-null/component invariant exists for a one-metric, one-row-per-year table; transform authors structural checks for no pre-2000 years, never-null population, and contiguous years. Contract SQL returned `non_empty=25`, `year_end_inmate_population_non_negative=0`, `no_pre_2000_years=0`, `population_never_null=0`, and `year_series_contiguous=0`.

## Manifest Verification

- Files processed coverage: PASS - manifest records the single PDF as `five_block_year_count_matrix`, 100 bronze rows, `Year` and `Count` columns; bronze inventory has no unanalyzed source file.
- Categorical and recode coverage: N/A - no categorical recodes are performed and `categorical_mappings` is empty.
- Row-count reconciliation: PASS - manifest totals are 100 bronze, 75 filtered, 25 gold; every 1925-1999 row is explicitly filtered as `pre_2000_methodology_break_year_floor`, and every 2000-2024 row has expansion factor 1.0.
- Metric stats sanity: PASS - metric is non-null for every served year, min 43,875 in 2000, max 54,463 in 2007, no negative counts, no scale issue.

## Row and Join Accounting

- Bronze file/year disposition: PASS - all 100 extracted PDF years 1925-2024 have a disposition: 1925-1999 intentionally filtered for the documented methodology break, 2000-2024 preserved in gold.
- Filter accounting: PASS - 75 pre-2000 rows are dropped in `transform_pdf()` lines 262-278 and recorded per year in the manifest.
- Join accounting: N/A - no joins or lookups occur.
- Deduplication accounting: PASS - source extraction is duplicate-free; collision guard runs on `["year", "detail_level"]`, then `deduplicate_by_levels({"state": ["year"]}, sort_col="year_end_inmate_population")` removes no rows.
- Aggregation/unpivot accounting: PASS - the PDF's five print blocks are unpivoted into 100 `(year, count)` pairs by visual line parsing; no numeric aggregation or formula collapse is performed.

## Reconciliation Checks

- Artifact freshness: PASS - `scripts/check_bronze_freshness.py criminal_justice gdc inmate_population` reports all one bronze file checksum matches and no unanalyzed files.
- Contract freshness: PASS - contract was emitted after the manifest run and before validation; no `_metadata.json` dependency exists.
- Year coverage: PASS - independent PDF extraction found a contiguous duplicate-free 1925-2024 series; gold has contiguous 2000-2024 only, as intended.
- Row preservation: PASS - independent join of served PDF rows to gold found 0 PDF-minus-gold rows and 0 gold-minus-PDF rows.
- Column coverage: PASS - bronze `Year` maps to gold `year`; bronze `Count` maps to `year_end_inmate_population`; the source methodology block is captured in contract prose and implemented by the year floor rather than a constant categorical.
- Recode accuracy: N/A - no recodes.
- Asian-family demographic recodes (Section 5b): N/A - no demographic column or race labels exist.
- Demographic mutual exclusivity (Section 5a - no rollup row alongside split source rows in the same category): N/A - no demographic column exists.
- Demographic collision aggregation before dedup (Section 5): N/A - no demographics.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, Section 1): PASS - state-only table has no geography, demographic, or categorical columns, so order is `year`, then metric.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, Section 11/12): PASS - parquet files contain only `year` and `year_end_inmate_population`; `detail_level` is encoded by `states.parquet`.
- Canonical column vocabulary (Section 16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - no forbidden vocabulary variants appear.
- Shared categorical utilities applied (Section 10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no shared categorical columns.
- Tidy long format (Section 9 - no demographics/years/components as column names): PASS - five side-by-side PDF blocks are stacked into year rows; no year or category remains as a column.
- FK keys present in dimension tables (Section 13 - `district_code`, `school_code`, `demographic`): N/A - no FK columns are present or declared.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - API surface is one row per year, no filterable categoricals, no FK joins, key metric `year_end_inmate_population`.
- Standards compliance (catch-all for Sections 1-16 items not enumerated above): PASS - count is `Int64`, year is `Int32`, no suppression markers survive, no nulls exist, no impossible values were preserved, and no direct gold edits were detected.

## Spot Checks

### Check 1

- Bronze: PDF matrix row includes `2004 48,009` and `2024 50,107`; independent pdfplumber extraction parsed `2024 -> 50107`.
- Transform path: `_extract_year_count_pairs()` lines 150-198 parses year/count token pairs; `transform_pdf()` lines 277-281 keeps year >= 2000 and tags state detail.
- Gold: `data/gold/criminal_justice/inmate_population/year=2024/states.parquet` has `{'year': 2024, 'year_end_inmate_population': 50107}`.
- Result: MATCH

### Check 2

- Bronze: PDF matrix row includes `1980 12,177`, `2000 43,875`, and `2020 46,132`; independent extraction parsed `2000 -> 43875`.
- Transform path: same parser path, with 2000 retained because it is the first served Dec-31 head-count year.
- Gold: `data/gold/criminal_justice/inmate_population/year=2000/states.parquet` has `{'year': 2000, 'year_end_inmate_population': 43875}`.
- Result: MATCH

### Check 3

- Bronze: PDF matrix row includes `2000 43,875` and `2020 46,132`; independent extraction parsed `2020 -> 46132`.
- Transform path: `_assert_gold_series()` lines 284-308 includes 2020 as a pinned gold anchor before export.
- Gold: `data/gold/criminal_justice/inmate_population/year=2020/states.parquet` has `{'year': 2020, 'year_end_inmate_population': 46132}`.
- Result: MATCH

### Check 4

- Bronze: PDF matrix row includes `1987 18,575` and `2007 54,463`; independent extraction parsed `2007 -> 54463`, the served-era maximum.
- Transform path: `_assert_gold_series()` lines 284-308 checks served anchors and never-null metric values; export writes one state row per year.
- Gold: `data/gold/criminal_justice/inmate_population/year=2007/states.parquet` has `{'year': 2007, 'year_end_inmate_population': 54463}`.
- Result: MATCH

### Check 5

- Bronze: PDF matrix row includes `1979 12,119`, `1999 41,557`, and `2019 53,943`; independent extraction parsed `1999 -> 41557`.
- Transform path: `transform_pdf()` lines 262-278 filters all years below `YEAR_FLOOR = 2000` and records the reason `pre_2000_methodology_break_year_floor`.
- Gold: no `year=1999` partition exists; manifest row count for 1999 is bronze 1, gold 0, filtered 1, filtered_explicit 1.
- Result: MATCH

## Notes

- No prior `data-review-claude.md` or existing `data-review-codex.md` content was read before reaching these findings.
- The bronze source's full 1925-2024 series is intentionally not fully served because the source itself documents incompatible pre-2000 methods. This is an intentional transform rule, not unexplained data loss.
- No required fixes were identified.
