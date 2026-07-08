# Data Review: wida_access

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze, transform, contract, validator, manifest, and gold output reconcile; no required transform fixes identified.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze freshness gate passed for all 8 files, transform mtime `2026-06-12T20:06:24Z` precedes manifest `2026-06-12T20:06:40Z`, and validation `2026-06-12T20:06:40Z` is passing and newer than the manifest.
- v1 parity: PASS - current gold hash `5c9322f1a332f5fe5d47bb28d60fd3dc785bb79db16511c2e5d2e5bd4a72dc59` matches the v1 approved baseline.

## Files Reviewed

- Transform: `src/etl/education/georgiainsights/wida_access/transform.py`
- Contract: `contracts/education/wida_access.odcs.yaml`
- Bronze files: 8 Excel workbooks, `ACCESS_for_ELLs_2017_State_Results.xlsx` through `WIDA-ACCESS-2024-State-Results.xlsx`
- Gold files: 8 `states.parquet` files under `data/gold/education/wida_access/year=2017` through `year=2024`
- Manifest: `data/gold/education/wida_access/_transform_manifest.json`
- Validation report: `data/gold/education/wida_access/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `data/bronze/education/georgiainsights/wida_access/bronze-data-structure.md`, `src/etl/education/CLAUDE.md`, data-cleaning standards and checklist

## Contract Verification

- Schema/parquet column match: PASS - contract properties exactly match parquet column order: `year`, geography keys, `grade_level`, `domain`, `proficiency_level`, then six metrics.
- Column roles and grain: PASS - grain is `year`, `district_code`, `school_code`, `grade_level`, `domain`, `proficiency_level`; this matches the state-only long table and validator grain check.
- Metric units and derived quality checks: PASS - counts use `unit: count`; percentage metrics use bounded `unit: proportion`; range and non-negative SQL checks are present.
- Categorical enums: PASS - contract enums match manifest and gold distinct values for 13 grades, 8 domains, and 6 WIDA proficiency levels.
- Detail levels and layout metadata: PASS - `detail_levels: [states]`, `path_template: education/wida_access/year={year}/{detail}.parquet`, and available years 2017-2024 match gold.
- Foreign-key descriptors: PASS - district and school FK descriptors are present; all fact rows have NULL geography keys because the source is state-only.
- Schema hash/version consistency: PASS - `version: 1.0.0`, `schema_hash: 1942277f42b93ba7e255a2484148b54f5376553c1644ad09ba57f66b77f965c3`.

## Validator Verification

- `_validation.json` fresh + passing: PASS - `passed: true`, 19 pass, 0 fail, 0 warning.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - schema, grain uniqueness, 15 contract quality SQL checks, FK resolution, canonical vocabulary, and geography nulling all pass.
- Validator warnings explained: N/A - no warnings in `_validation.json`.
- §15b quality-check coverage (cross-column invariants authored): PASS - authored checks cover level counts summing to domain denominator, shares summing to one, count ordering, 2021-only participation rates, and state-only geography NULLs.

## Manifest Verification

- Files processed coverage: PASS - manifest processed all 8 current bronze files; `scripts/check_bronze_freshness.py education georgiainsights wida_access` passed with no unanalyzed files.
- Categorical and recode coverage: PASS - `domain`, `grade_level`, and `proficiency_level` all have `unmapped_count: 0`; all map entries are semantically correct.
- Row-count reconciliation: PASS - 7 standard files have 13 bronze grade rows -> 624 gold rows each; 2021 records 21 data-region rows with 8 explicit non-grade footnote/blank rows filtered, then 13 grade rows -> 624 gold rows.
- Metric stats sanity: PASS - counts are non-negative; proportions are within 0-1; participation metrics are populated only in 2021 and NULL elsewhere as documented.

## Row and Join Accounting

- Bronze file/year disposition: PASS - one processed workbook for each year 2017-2024; no ignored data files.
- Filter accounting: PASS - 2021 drops exactly 8 non-data rows: 2 blanks, 4 composite-footnote rows, 1 note row, and 1 URL row.
- Join accounting: PASS - joins are grade-key joins from unpivoted long rows to per-grade base/domain frames; expected row count is asserted as `df.height * 8 * 6`, and actual gold has 624 rows per year.
- Deduplication accounting: PASS - no duplicate natural-key rows found in gold; defensive dedup keeps unique state rows only.
- Aggregation/unpivot accounting: PASS - wide bronze pivots are unpivoted to 13 grades x 8 domains x 6 proficiency levels; per-domain denominator is published in 2021 and reconstructed as the six-level count sum in other years.

## Reconciliation Checks

- Artifact freshness: PASS - checksums match bronze structure report and validation is fresh relative to manifest.
- Contract freshness: PASS - contract schema matches current parquet; no `_metadata.json` dependency.
- Year coverage: PASS - expected years 2017-2024 all present, no unexpected year partitions.
- Row preservation: PASS - all grade rows are preserved and reshaped; only documented 2021 non-data rows are filtered.
- Column coverage: PASS - all fact keys, categoricals, and metrics from the structure doc are represented under current canonical names.
- Recode accuracy: PASS - grade `K`/`1`-`12` -> `k`/`01`-`12`; domain footnote labels such as `Oral Language CompositeA` -> `oral_language_composite`; WIDA levels normalize correctly.
- Asian-family demographic recodes (§5b): N/A - no race/ethnicity demographic column or Asian-family labels.
- Demographic mutual exclusivity (§5a): N/A - no `demographic` column; grade is stored as the primary `grade_level` axis.
- Demographic collision aggregation before dedup (§5): N/A - no demographic normalization/collision path.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS - parquet begins with `year`, `district_code`, `school_code`, then categoricals and metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS - exported parquet contains none of these columns.
- Canonical column vocabulary (§16): PASS - uses `grade_level`; proficiency-level count/share names use `num_at_proficiency_level` / `pct_at_proficiency_level`; rate columns end in `_rate`.
- Shared categorical utilities applied (§10a): PASS - `normalize_grade_column` is used for `grade_level`; no academic `subject` column exists.
- Tidy long format (§9): PASS - no domains, levels, or years are encoded as metric columns in gold.
- FK keys present in dimension tables (§13): PASS - validator FK check passes; all geography keys are NULL state-level values.
- Contract-driven API semantics: PASS - filterable categoricals and FK descriptors are contract-derived and coherent with state-only rows.
- Standards compliance: PASS - ID/null semantics, percentage scale, suppression handling, manifest, contract, validation, and state-only geography all follow the repo standards.

## Spot Checks

### Check 1

- Bronze: `ACCESS_for_ELLs_2017_State_Results.xlsx`, grade `12`, `Listening Domain | Level 1 Entering`: count `187`, percent `16.681534`, total tested `1121`; Era 1 domain denominator reconstructed as level-count sum `1121`.
- Transform path: `_transform_era()` lines 493-565 unpivots domain/level columns, divides percent by 100, and reconstructs `num_tested_in_domain`.
- Gold: `year=2017`, `grade_level='12'`, `domain='listening'`, `proficiency_level='level_1_entering'` has count `187`, pct `0.16681534`, `num_tested_in_domain=1121`, `num_tested=1121`.
- Result: MATCH

### Check 2

- Bronze: `ACCESS for ELLs 2021 State Results.xlsx`, grade `K`, `Listening Domain | Level 1 Entering`: count `4391`, percent `34.374511`, published domain denominator `12774`, overall tested `12779`, overall participation `95.45115`, domain participation `95.413803`.
- Transform path: `_transform_era()` lines 478-559 reads 2021 participation fields, published domain denominator, and scales percentages to 0-1.
- Gold: `year=2021`, `grade_level='k'`, `domain='listening'`, `proficiency_level='level_1_entering'` has count `4391`, pct `0.34374511`, `num_tested_in_domain=12774`, `num_tested=12779`, rates `0.9545115` and `0.95413803`.
- Result: MATCH

### Check 3

- Bronze: `WIDA-ACCESS-2024-State-Results.xlsx`, grade `K`, `Listening Domain | Level 1 Entering`: count `6475`, percent `45.766186033361606`, total tested `14148`; denominator reconstructed as `14148`.
- Transform path: `_transform_era()` lines 493-565 applies the Era 1 unpivot and denominator reconstruction.
- Gold: `year=2024`, `grade_level='k'`, `domain='listening'`, `proficiency_level='level_1_entering'` has count `6475`, pct `0.45766186033361606`, `num_tested_in_domain=14148`, `num_tested=14148`.
- Result: MATCH

### Check 4

- Bronze: `WIDA-ACCESS-2024-State-Results.xlsx`, grade `12`, `Overall Score Composite | Level 6 Reaching`: count `1`, percent `0.02543881963876876`, reconstructed denominator `3931`, total tested `4008`.
- Transform path: `DOMAIN_MAP` lines 145-158 maps `Overall Score Composite` to `overall_score_composite`; `_transform_era()` scales the percent and repeats the grade total.
- Gold: `year=2024`, `grade_level='12'`, `domain='overall_score_composite'`, `proficiency_level='level_6_reaching'` has count `1`, pct `0.0002543881963876876`, `num_tested_in_domain=3931`, `num_tested=4008`.
- Result: MATCH

## Notes

- Aggregate recomputation across all 8 bronze files found max six-level percentage-sum deviation `2.00000000916134e-06` on the 0-100 source scale and 0 mismatches between 2021 published `Total Tested in Domain` values and six-level count sums.
- Gold recomputation found 0 count-denominator ordering violations, 0 populated geography keys, 0 duplicate grain rows, and max gold share-sum deviation `2e-08`.
- No required fixes were identified, so this report intentionally omits `## Required Fixes`.
