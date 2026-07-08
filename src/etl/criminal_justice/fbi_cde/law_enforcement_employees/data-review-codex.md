# Data Review: law_enforcement_employees

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze-to-gold row coverage, ORI county attribution, sex-split recodes, aggregate formulas, contract metadata, and validator output all reconcile; no must-fix transform defects found.

## Summary

- Review date: 2026-07-02
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH — bronze checksum matches `bronze-data-structure.md`; manifest generated `2026-07-02T23:18:37.259282+00:00`; `_validation.json` is fresh and passing at `2026-07-02T23:23:04.641696+00:00`.

## Files Reviewed

- Transform: `src/etl/criminal_justice/fbi_cde/law_enforcement_employees/transform.py`
- Contract: `contracts/criminal_justice/law_enforcement_employees.odcs.yaml`
- Bronze files: `data/bronze/criminal_justice/fbi_cde/law_enforcement_employees/lee_1960_2025.csv`, `_provenance.md`, `bronze-data-structure.md`
- Gold files: 132 parquet files, `year=1960` through `year=2025`, each with `counties.parquet` and `states.parquet`
- Manifest: `data/gold/criminal_justice/law_enforcement_employees/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/law_enforcement_employees/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/CLAUDE.md`, `src/etl/criminal_justice/CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS — validator reports all 132 parquet files match the contract; actual parquet order is `year`, `county_fips`, `demographic`, then the four metrics.
- Column roles and grain: PASS — contract grain is `year`, `county_fips`, `demographic`; roles are `year`, `fk_county`, `fk_demographic`, and metric roles.
- Metric units and derived quality checks: PASS — all four metrics are `unit: count`; non-negativity checks and the topic-authored component/partition checks are present.
- Categorical enums: PASS — `demographic` enum is `all`, `female`, `male`, matching manifest and gold distinct values.
- Detail levels and layout metadata: PASS — contract lists `counties` and `states`, default `counties`, partition `year`, and path template `criminal_justice/law_enforcement_employees/year={year}/{detail}.parquet`.
- Foreign-key descriptors: PASS — `county_fips -> counties` and `demographic -> demographics`; validator confirms all 159 county keys and all 3 demographic keys resolve.
- Schema hash/version consistency: PASS — contract is `version: 1.0.0`, `year_range: 1960-2025`, no year gaps, schema hash present.

## Validator Verification

- `_validation.json` fresh + passing: PASS — `passed: true`, 20 pass / 0 fail / 0 warning; validation timestamp is later than manifest generation.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS — schema, grain uniqueness, all 13 contract quality checks, foreign keys, geography nulling, and canonical vocabulary pass.
- Validator warnings explained: N/A — no validator warnings.
- §15b quality-check coverage (cross-column invariants authored): PASS — contract enforces officer+civilian totals, male+female partition to all, exactly three demographic rows per cell, state totals covering county sums, constant `agencies_reporting` across sex rows, and positive reporting rosters.

## Manifest Verification

- Files processed coverage: PASS — one current bronze CSV is processed; SHA-256 matches `36603e78db8926033f85c8727492f4913e0744ab33722307619dfcd4e098533c`.
- Categorical and recode coverage: PASS — `county_fips` records 817 ORIs with `unmapped_count: 0`; `demographic` maps `All`, `Male`, `Female` to `all`, `male`, `female` with `unmapped_count: 0`.
- Row-count reconciliation: PASS — 26,180 GA agency-years aggregate to 8,932 county-year cells plus 66 state-year cells, then unpivot to three demographic rows each: `3 * (8,932 + 66) = 26,994` gold rows.
- Metric stats sanity: PASS — all metrics are non-null counts; gold min values are non-negative and `agencies_reporting` minimum is 1.

## Row and Join Accounting

- Bronze file/year disposition: PASS — national file has 785,127 rows; Georgia scope is 26,180 rows across 66 unbroken years, 1960-2025.
- Filter accounting: PASS — `state_abbr == "GA"` is a scope filter for the national file; no in-scope Georgia rows are dropped as quality filters.
- Join accounting: PASS — `ori_to_county.parquet` has 820 unique ORIs and zero duplicate keys; all 817 Georgia ORIs match; join preserves 26,180 rows with no fanout. 113 agency-years from 12 no-county statewide ORIs roll to state only; 1,531 agency-years from 41 multi-county ORIs are attributed to primary county as documented.
- Deduplication accounting: PASS — bronze `(ori, data_year)` is unique; gold natural grain duplicates are zero after aggregation/dedup.
- Aggregation/unpivot accounting: PASS — county rows sum non-null county-attributed agencies, state rows sum all Georgia agencies, and each geography-year is unpivoted into `all`, `male`, `female`.

## Reconciliation Checks

- Artifact freshness: PASS — bronze freshness script reports all 1 bronze file checksum matches and no unanalyzed files.
- Contract freshness: PASS — contract/parquet schema check passes and there is no `_metadata.json` dependency.
- Year coverage: PASS — bronze and gold both cover every year 1960-2025.
- Row preservation: PASS — every Georgia agency-year contributes either to a county plus state row, or state-only for no-county statewide agencies; no zero-fill is fabricated for non-reporting county-years.
- Column coverage: PASS — source employee count fields map to the three served metrics across the three demographic rows; excluded `population`/`pe_ct_per_1000` and agency descriptors are documented as out of fact scope.
- Recode accuracy: PASS — source typo `cilvilian` is handled by the era mapping; demographic and ORI-to-county mappings match actual bronze and gold values.
- Asian-family demographic recodes (§5b): N/A — topic has no race demographics.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): PASS — `all` is the aggregate lane; `male` and `female` are mutually exclusive and partition all rows exactly.
- Demographic collision aggregation before dedup (§5): N/A — no multiple raw demographic labels collapse to the same canonical value.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS — actual parquet order follows the standard.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS — gold contains no agency names, county names, ORIs, `population`, `pe_ct_per_1000`, `topic`, or `detail_level`.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS — no forbidden canonical variants apply; count metric names are clear and contract-described.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A — no grade or subject columns; demographics use `normalize_demographic_column`.
- Tidy long format (§9 — no demographics/years/components as column names): PASS — sex splits are tidy rows in `demographic`; no year or demographic values appear as metric columns.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS — validator confirms `county_fips` and `demographic` foreign keys resolve.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS — API grain is natural key `year + county_fips + demographic`; county and demographic joins derive from contract FKs.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS — count types, nonnegative values, geography nulling, suppression semantics, and year partitioning are consistent with repo standards.

## Spot Checks

### Check 1

- Bronze: `lee_1960_2025.csv`, 1983 Georgia agency rows mapped to Lowndes County (`county_fips=13185`) sum to `officer_ct=149`, `civilian_ct=31`, `total_pe_ct=180`, across 4 agencies.
- Transform path: `_load_georgia_agency_years()` lines 199-267; `_attach_county()` lines 270-322; `_aggregate()` lines 363-391; `_tidy_demographics()` lines 325-360.
- Gold: `year=1983/counties.parquet`, `county_fips=13185`, `demographic=all` has `officer_count=149`, `civilian_count=31`, `total_employee_count=180`, `agencies_reporting=4`.
- Result: MATCH

### Check 2

- Bronze: `lee_1960_2025.csv`, 2020 Jackson County (`county_fips=13157`) sums to all officers/civilians of `148/75`; male/female officer counts are `133 + 15 = 148`, and civilian counts are `40 + 35 = 75`.
- Transform path: `_aggregate()` groups county agencies by `year`, `county_fips`; `_tidy_demographics()` emits `all`, `male`, and `female` demographic rows.
- Gold: `year=2020/counties.parquet`, `county_fips=13157` has `all=(148,75,223)`, `male=(133,40,173)`, `female=(15,35,50)`, all with `agencies_reporting=6`.
- Result: MATCH

### Check 3

- Bronze: `lee_1960_2025.csv`, all 455 Georgia agency rows in 2025 sum to `officer_ct=25,945`, `civilian_ct=11,678`, `total_pe_ct=37,623`.
- Transform path: `_aggregate()` state branch groups by `year` only and includes both county-attributed and no-county statewide agencies.
- Gold: `year=2025/states.parquet`, `county_fips=NULL`, `demographic=all` has `officer_count=25,945`, `civilian_count=11,678`, `total_employee_count=37,623`, `agencies_reporting=455`.
- Result: MATCH

### Check 4

- Bronze: non-Georgia rows in the national CSV are outside this topic's Georgia scope; Georgia rows are selected by `state_abbr == "GA"`.
- Transform path: `_load_georgia_agency_years()` lines 226-237 applies the scope filter before county joining or aggregation.
- Gold: no non-Georgia rows can appear because the only geography key is Georgia county FIPS, and all populated county FIPS values begin with `13`.
- Result: MATCH

## Notes

- No required fixes. The row-count shape is a deliberate many-agency-to-county/state aggregation followed by a three-row demographic unpivot; it is not evidence of data loss.
- `population` and `pe_ct_per_1000` are excluded by documented topic policy because agency service populations overlap across jurisdictions and would produce misleading county-level rates.
