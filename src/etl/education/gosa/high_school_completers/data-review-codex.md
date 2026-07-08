# Data Review: high_school_completers

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: contract, manifest, validator, bronze files, and gold parquet reconcile; no must-fix bronze-to-gold accuracy defects found.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH — transform mtime 2026-06-12T01:30:56Z, manifest generated 2026-06-12T01:31:09Z, validation timestamp 2026-06-12T01:31:09Z, validation passed.

## Files Reviewed

- Transform: `src/etl/education/gosa/high_school_completers/transform.py`
- Contract: `contracts/education/high_school_completers.odcs.yaml`
- Bronze files: 14 CSV files, `high_school_completers_2011.csv` through `high_school_completers_2024.csv`
- Gold files: 42 parquet files, `year=2011` through `year=2024`, with `states.parquet`, `districts.parquet`, and `schools.parquet` for each year
- Manifest: `data/gold/education/high_school_completers/_transform_manifest.json`
- Validation report: `data/gold/education/high_school_completers/_validation.json`
- Supporting docs: `data/bronze/education/gosa/high_school_completers/bronze-data-structure.md`, `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`

## Contract Verification

- Schema/parquet column match: PASS — parquet columns are exactly `year`, `district_code`, `school_code`, `demographic`, `completer_type`, `credential_type`, `completer_count`, `pct_of_credential_type`, matching contract order.
- Column roles and grain: PASS — grain is year + geography + demographic + completer_type + credential_type; actual duplicate grain groups = 0.
- Metric units and derived quality checks: PASS — `completer_count` is `unit: count`; `pct_of_credential_type` is `unit: proportion`; validator executed all 13 contract quality SQL checks successfully.
- Categorical enums: PASS — contract enums match manifest and gold distinct values for demographic, completer_type, and credential_type.
- Detail levels and layout metadata: PASS — contract detail levels are schools, districts, states; gold has all three files for each year 2011-2024.
- Foreign-key descriptors: PASS — validator and independent checks found 0 unmatched district, school, or demographic keys.
- Schema hash/version consistency: PASS — contract is active version 1.0.0 with schema hash `e03ad04843c6291927e3edf4b7d40cfb933203a5f5af7423d8dd41e8ba466a8e`; contract layout and year range match gold.

## Validator Verification

- `_validation.json` fresh + passing: PASS — validation timestamp is after manifest generation and `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS — 21 pass, 0 fail, 0 warning.
- Validator warnings explained: N/A — validation reported no warnings.
- §15b quality-check coverage (cross-column invariants authored): PASS — transform authors checks for credential/completer dependency, count/pct co-null direction, all-demographic pct = 1, gender/race count partitions, and gender/race pct partition sums.

## Manifest Verification

- Files processed coverage: PASS — manifest records all 14 current bronze CSVs, with years 2011-2024 and row counts matching direct bronze reads.
- Categorical and recode coverage: PASS — `unmapped_count` is 0 for demographic, completer_type, and credential_type; every actual bronze distinct categorical value appears in the manifest.
- Row-count reconciliation: PASS — total bronze rows 478,980; total gold rows 478,980; every year has expansion factor 1.0 and no filtered rows.
- Metric stats sanity: PASS — `completer_count` range is 0 to 119,764; `pct_of_credential_type` range is 0.0 to 1.0; null counts align with documented blank/TFS suppression patterns.

## Row and Join Accounting

- Bronze file/year disposition: PASS — all 14 bronze CSVs are processed, one school year per file, and filename year agrees with `LONG_SCHOOL_YEAR`.
- Filter accounting: N/A — no source rows are filtered; manifest and gold row counts equal bronze row counts by year.
- Join accounting: N/A — transform does not join external lookups; FK resolution to dimensions is validator-checked after export.
- Deduplication accounting: PASS — representative direct checks for 2011, 2022, and 2024 show 0 bronze duplicate natural-key groups; gold duplicate grain groups = 0.
- Aggregation/unpivot accounting: N/A — no aggregation or unpivot occurs; bronze rows are reshaped one-to-one into gold fact rows.

## Reconciliation Checks

- Artifact freshness: PASS — bronze freshness gate reports all 14 checksums match and no unanalyzed files.
- Contract freshness: PASS — contract, parquet schema, and validation are from the current transform output; no `_metadata.json` dependency.
- Year coverage: PASS — bronze, manifest, contract, and gold all cover 2011-2024 with no gaps.
- Row preservation: PASS — direct gold count is 478,980, equal to manifest and bronze total.
- Column coverage: PASS — fact keys, categoricals, and metrics from the bronze classification are present; name columns, sort order, and Era 2 report label are validly excluded.
- Recode accuracy: PASS — `Graduates` -> `graduates`, `Other Completers` -> `other_completers`; all six credential labels map to documented credential keys; `Total` -> `all`; `Multi` -> `multiracial`; `Native American/ Alaskan Native` -> `native_american`.
- Asian-family demographic recodes (§5b): PASS — bronze has no Pacific Islander/NHPI header or value; 2024 state race counts for graduates/general education diplomas sum to 119,764, exactly matching the all row, so bare `Asian` is correctly emitted as `asian_pacific_islander`.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): PASS — gold emits `asian_pacific_islander` and emits 0 `asian` or `pacific_islander` rows.
- Demographic collision aggregation before dedup (§5): N/A — the nine source demographic labels map to nine distinct canonical values.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS — actual parquet order follows the standard.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS — no forbidden columns appear in parquet.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS — topic uses canonical `completer_count` and `pct_of_credential_type`; no irrelevant assessment vocabulary appears.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A — no grade_level or subject column; demographics use `normalize_demographic_column`.
- Tidy long format (§9 — no demographics/years/components as column names): PASS — demographic and credential values are rows, not columns.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS — independent anti-joins found 0 unmatched districts, 0 unmatched composite schools, and 0 unmatched demographics.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS — contract exposes categorical filters for completer_type and credential_type and FK joins for district, school, and demographic.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS — IDs remain strings with zero padding, `ALL` sentinels are nulled, suppression markers become null metrics, and percentage scale is 0-1.

## Spot Checks

### Check 1

- Bronze: `high_school_completers_2022.csv`, state row `Graduates` / `General Education Diplomas` / `Male`: `PROGRAM_TOTAL=55853`, `PROGRAM_PERCENT=48.8`; matching total row count is 114,359.
- Transform path: `transform_file()` lines 404-495 parse year/geography, normalize categoricals, cast count, and divide percent by 100.
- Gold: `year=2022/states.parquet` row has `district_code=NULL`, `school_code=NULL`, `demographic=male`, `credential_type=general_education_diplomas`, `completer_count=55853`, `pct_of_credential_type=0.488`; recomputation `55853 / 114359 = 0.488`.
- Result: MATCH

### Check 2

- Bronze: `high_school_completers_2024.csv`, school row district `7830210`, school `0210`, `Graduates` / `General Education Diplomas` / `Hispanic`: `PROGRAM_TOTAL=TFS` parsed as null, `PROGRAM_PERCENT=2.6`.
- Transform path: `read_bronze_file()` suppression nulling plus `transform_file()` lines 484-495 cast count and divide percent.
- Gold: `year=2024/schools.parquet` row has `district_code=7830210`, `school_code=0210`, `demographic=hispanic`, `completer_count=NULL`, `pct_of_credential_type=0.026`.
- Result: MATCH

### Check 3

- Bronze: `high_school_completers_2011.csv`, school row district `601`, unpadded school `103`, `Graduates` / `Diplomas with College Prep Endorsements` / `Male`: `PROGRAM_TOTAL=39`, `PROGRAM_PERCENT=38.2`.
- Transform path: `transform_file()` lines 479-495 zero-pad `INSTN_NUMBER` to four characters, map credential/demographic, cast count, and divide percent by 100.
- Gold: `year=2011/schools.parquet` row has `district_code=601`, `school_code=0103`, `demographic=male`, `credential_type=diplomas_college_prep`, `completer_count=39`, `pct_of_credential_type=0.382`.
- Result: MATCH

## Notes

- I did not read any prior `data-review-claude.md` or existing `data-review-codex.md` before writing this report.
- No collapsed-row formula trace is required for this topic because the transform does not aggregate, unpivot, or collapse rows; the formula-level check performed was the source percentage interpretation for a real state-level row.
