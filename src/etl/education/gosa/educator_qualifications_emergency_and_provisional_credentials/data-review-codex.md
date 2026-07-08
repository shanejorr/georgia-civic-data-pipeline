# Data Review: educator_qualifications_emergency_and_provisional_credentials

## Verdict

**Status**: NEEDS FIXES
**Must-fix count**: 1

Summary: bronze-to-gold values, rows, recodes, schema, and FKs reconcile, but one documented poverty-stratum invariant is only partially enforced by contract quality SQL.

## Summary

- Review date: 2026-06-11
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - `scripts/check_bronze_freshness.py` passed for all 7 bronze CSV checksums with no unanalyzed files; transform mtime is before manifest generation, and `_validation.json` is newer than the manifest.

## Files Reviewed

- Transform: `src/etl/education/gosa/educator_qualifications_emergency_and_provisional_credentials/transform.py`
- Shared resolver: `src/etl/education/gosa/_educator_lookups.py`
- Contract: `contracts/education/educator_qualifications_emergency_and_provisional_credentials.odcs.yaml`
- Bronze files: 7 CSV files, `educator_qualifications_emergency_and_provisional_credentials_2018.csv` through `educator_qualifications_emergency_and_provisional_credentials_2024.csv`
- Gold files: 21 parquet files, `year=2018` through `year=2024`, each with `schools.parquet`, `districts.parquet`, and `states.parquet`
- Manifest: `data/gold/education/educator_qualifications_emergency_and_provisional_credentials/_transform_manifest.json`
- Validation report: `data/gold/education/educator_qualifications_emergency_and_provisional_credentials/_validation.json`
- Supporting docs: `data/bronze/education/gosa/educator_qualifications_emergency_and_provisional_credentials/bronze-data-structure.md`, `docs/codex-review-contract.md`, `docs/contract-creation.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `CLAUDE.md`, `AGENTS.md`, and `src/etl/education/CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS - contract properties are `year`, `district_code`, `school_code`, `poverty_subgroup`, `total_fte`, `emergency_fte`, `emergency_fte_rate`, matching all 21 parquet files in name and order.
- Column roles and grain: PASS - roles are `year`, `fk_district`, `fk_school`, `categorical`, and metrics; grain is year plus geography keys plus `poverty_subgroup`, with nullable geography keys correctly representing state and district rows.
- Metric units and derived quality checks: PASS - `total_fte` and `emergency_fte` are `unit: count`; `emergency_fte_rate` is `unit: proportion` with an emitted [0, 1] check.
- Categorical enums: PASS - `poverty_subgroup` enum is exactly `high_poverty`, `low_poverty`, `total`, matching the manifest and gold distinct values.
- Detail levels and layout metadata: PASS - contract lists `schools`, `districts`, and `states`; year partitions cover 2018-2024 with no gaps.
- Foreign-key descriptors: PASS - `district_code` targets districts and `school_code` targets the composite schools key; validator confirms all 232 district keys and 2386 school keys resolve.
- Schema hash/version consistency: PASS - version is `1.0.0`, `year_range` is `2018-2024`, and `schema_hash` is present.

## Validator Verification

- `_validation.json` fresh + passing: PASS - manifest `generated_at` is `2026-06-11T16:58:04.392808+00:00`; validation timestamp is `2026-06-11T16:58:04.448246+00:00`; `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 21 pass, 0 fail, 0 warning; `contract_parquet_schema`, `grain_uniqueness`, `contract_quality_sql`, `foreign_keys`, and `canonical_vocabulary` all pass.
- Validator warnings explained: N/A - validation report has no warnings.
- Section 15b quality-check coverage (cross-column invariants authored): FAIL - the transform documents school poverty-stratum mirror behavior on all three metrics and aggregate high/low subsets, but the authored SQL checks only enforce `total_fte` for those two invariants. See Required Fix 1.

## Manifest Verification

- Files processed coverage: PASS - manifest processes all 7 current bronze files and all expected years 2018-2024.
- Categorical and recode coverage: PASS - `poverty_subgroup` maps `Total`, `High Poverty`, and `Low Poverty` to canonical values with `unmapped_count: 0`.
- Row-count reconciliation: PASS - manifest `total_bronze=26382`, `total_gold=26309`, `total_filtered=73`; the 73 filtered 2023 rows are fully explicit: 37 placeholder charter rows, 4 source-gap school rows, and 32 duplicate republications deduplicated.
- Metric stats sanity: PASS - raw percent columns are 0-100 and gold `emergency_fte_rate` is 0-1; count metrics are non-negative; `emergency_fte <= total_fte` has zero violations.

## Row and Join Accounting

- Bronze file/year disposition: PASS - all bronze CSVs are processed; 2018-2021 use the documented mislabeled `OUTOFFIELD_*` emergency metric columns, 2022 uses `Emergency_*`, and 2023-2024 use `CATEGORY_*` with constant `#CATEGORY_DESC = Emergency`.
- Filter accounting: PASS - only 2023 rows are removed, all through documented predicates: unresolved generic state-charter placeholder rows or cataloged source-gap school rows.
- Join accounting: PASS - name resolution runs once per distinct name/detail combination and joins back left; residual unresolved guards would raise. After documented drops, unresolved district and school counts are both zero.
- Deduplication accounting: PASS - 2023 has 32 duplicate natural-key groups after documented drops; every duplicate group has identical metric triples, and dedup removes exactly 32 rows.
- Aggregation/unpivot accounting: PASS - no unpivot or aggregate recomputation is performed; metrics are row-preserving casts/scaling except for dedup of identical republications. Rate formula reconciliation max observed difference is 0.012105, within the authored 0.015 tolerance.

## Reconciliation Checks

- Artifact freshness: PASS - bronze checksums match the structure report; manifest and validation are current.
- Contract freshness: PASS - contract schema and parquet schema agree; no `_metadata.json` dependency.
- Year coverage: PASS - bronze, manifest, contract, and gold all cover 2018-2024.
- Row preservation: PASS - six years are one-to-one; 2023 row reduction is fully explained by 41 documented drops plus 32 identical duplicate republications.
- Column coverage: PASS - each fact key, fact categorical, and fact metric from the bronze structure report is represented or intentionally excluded as a constant/dimension attribute.
- Recode accuracy: PASS - `LABEL_LVL_2_DESC` recodes are semantically correct; no fallback values appear in gold.
- Asian-family demographic recodes (section 5b): N/A - topic has no demographic column and no race/Asian-family fields.
- Demographic mutual exclusivity (section 5a): N/A - no demographic column.
- Demographic collision aggregation before dedup (section 5): N/A - no demographic normalization.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - parquet order is `year`, `district_code`, `school_code`, `poverty_subgroup`, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, sections 11/12): PASS - exported parquet contains none of these columns.
- Canonical column vocabulary (section 16): PASS - no forbidden variants found; rate column uses `emergency_fte_rate`, not a redundant `_pct` suffix.
- Shared categorical utilities applied (section 10a): N/A - no grade, subject, or demographic column.
- Tidy long format (section 9): PASS - poverty subgroup is a row categorical, years are partitions/column values, and there are no wide category columns.
- FK keys present in dimension tables (section 13): PASS - validator confirms all district and composite school keys resolve.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - `poverty_subgroup` is a categorical filter, and FK joins derive from contract descriptors.
- Standards compliance (catch-all for sections 1-16): FAIL - current values comply, but section 15b quality SQL under-enforces documented poverty-stratum invariants.

## Spot Checks

### Check 1

- Bronze: `educator_qualifications_emergency_and_provisional_credentials_2018.csv`, state Total row: `FTE=118009.1`, `OUTOFFIELD_FTE=9507.3`, `OUTOFFIELD_FTE_PCT=8`.
- Transform path: Era 3 metric selection via `ERA_METRIC_COLUMNS` and scaling in `_transform_era` (`transform.py:212` and `transform.py:345`).
- Gold: 2018 state total row has `district_code=NULL`, `school_code=NULL`, `poverty_subgroup=total`, `total_fte=118009.1`, `emergency_fte=9507.3`, `emergency_fte_rate=0.08`.
- Result: MATCH

### Check 2

- Bronze: `educator_qualifications_emergency_and_provisional_credentials_2022.csv`, Richmond County / Josey High School / Total: `FTE=34.8`, `Emergency_FTE=10`, `Emergency_FTE_PCT=29`.
- Transform path: Era 2 metric selection plus resolver code attachment (`transform.py:212`, `transform.py:360`).
- Gold: 2022 row resolves to `district_code=721`, `school_code=3756`, `poverty_subgroup=total`, `total_fte=34.8`, `emergency_fte=10.0`, `emergency_fte_rate=0.29`.
- Result: MATCH

### Check 3

- Bronze: `educator_qualifications_emergency_and_provisional_credentials_2024.csv`, Peach County / Hunt Elementary School / Total: `FTE=42.5`, `CATEGORY_FTE=TFS`, `CATEGORY_FTE_PCT=TFS`.
- Transform path: all-string read with suppression handling and `strict=False` metric casts (`transform.py:523`, `transform.py:345`).
- Gold: 2024 row resolves to `district_code=711`, `school_code=0210`, `poverty_subgroup=total`, `total_fte=42.5`, `emergency_fte=NULL`, `emergency_fte_rate=NULL`.
- Result: MATCH

### Check 4

- Bronze: `educator_qualifications_emergency_and_provisional_credentials_2023.csv` publishes Odyssey Charter School Total twice: the bare school row and the truncated `...- All S` republication both have `FTE=28.5`, `CATEGORY_FTE=TFS`, `CATEGORY_FTE_PCT=21`.
- Transform path: resolver binds both to `(7820110, 0110)`, collision guard verifies identical metrics, and `deduplicate_by_detail_level` removes one duplicate (`transform.py:592`, `transform.py:606`).
- Gold: exactly one 2023 `total` row for Odyssey Charter School has `total_fte=28.5`, `emergency_fte=NULL`, `emergency_fte_rate=0.21`; the low-poverty duplicate also deduplicates to one row.
- Result: MATCH

### Check 5

- Bronze: `educator_qualifications_emergency_and_provisional_credentials_2023.csv` has Barrow County / Barrow Arts and Sciences Academy rows for `total` and `low_poverty`, both `FTE=61.8`.
- Transform path: `_drop_documented_gaps` drops unresolved source-gap school pairs after resolver failure (`transform.py:433`); `_educator_lookups.py` documents this name as ambiguous because the schools dimension carries two Barrow Arts and Sciences Academy rows.
- Gold: no 2023 fact row is emitted for Barrow Arts and Sciences Academy.
- Result: MATCH - intentionally filtered, not silently lost.

## Required Fixes

### Fix 1: Complete poverty-stratum quality SQL coverage

- **Severity**: MEDIUM
- **Issue**: The transform documents two poverty-stratum invariants but the emitted contract quality SQL only enforces them for `total_fte`. For school rows, `high_poverty` or `low_poverty` should mirror the same school's `total` row on `total_fte`, `emergency_fte`, and `emergency_fte_rate`. For district/state rows, `high_poverty + low_poverty <= total + 0.25` should apply to count metrics, including `emergency_fte` when all three cells are reported. The current gold values satisfy these invariants, but the validator does not enforce the documented emergency-metric cases.
- **Evidence**: Bronze and gold spot checks confirm school stratum rows duplicate all three metrics, and aggregate checks found zero `emergency_fte` high+low > total+0.25 violations. Transform logic at `transform.py:1004` defines `school_poverty_stratum_mirrors_total` but its SQL only selects `total_fte`; transform logic at `transform.py:1053` defines `aggregate_poverty_strata_within_total` but its SQL only selects `total_fte`. `_validation.json` passes 11 quality checks, so the missing emergency-metric cases are currently unenforced rather than failing.
- **Location**: `src/etl/education/gosa/educator_qualifications_emergency_and_provisional_credentials/transform.py:1004` and `src/etl/education/gosa/educator_qualifications_emergency_and_provisional_credentials/transform.py:1053`
- **Suggested fix**: Expand the existing `quality_checks` SQL in `_emit_contract_and_readme()` so `school_poverty_stratum_mirrors_total` also compares `emergency_fte` and `emergency_fte_rate` with null-safe row-existence guards, and so `aggregate_poverty_strata_within_total` also checks `emergency_fte` high+low against total when all three values are non-null. Re-run the transform so the contract and `_validation.json` are regenerated.

## Notes

- No current bronze-to-gold value mismatch was found.
- No prior `data-review-claude.md` or existing `data-review-codex.md` was read before writing this independent report.
- The only required fix is validation coverage for documented invariants; the current served parquet values reconciled against bronze in the checks above.
