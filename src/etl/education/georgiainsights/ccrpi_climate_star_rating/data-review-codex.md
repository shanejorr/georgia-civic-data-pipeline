# Data Review: ccrpi_climate_star_rating

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze, transform, contract, validator, manifest, and gold output reconcile; no required transform fixes were found.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - transform mtime `2026-06-12T15:45:29.694704+00:00`, manifest `generated_at` `2026-06-12T15:45:54.085388+00:00`, validation timestamp `2026-06-12T15:45:54.120619+00:00`, validation passed.

## Files Reviewed

- Transform: `src/etl/education/georgiainsights/ccrpi_climate_star_rating/transform.py`
- Contract: `contracts/education/ccrpi_climate_star_rating.odcs.yaml`
- Bronze files: 7 Excel files, 2014-2019 and 2024: `CCRPI Score and School Climate Star Rating 04.14.15.xlsx`, `2015 School Climate Star Ratings and CCRPI scores.xlsx`, `2016 Star Rating_CCRP 1.26.17I.xlsx`, `2017 CCRPI School Climate Star Rating 11.2.17.xlsx`, `2018 CCRPI School Climate Star Rating_10_29_18.xlsx`, `2019 School Climate Star Rating_11_26_19.xls`, `2024 School Climate Star Rating.xlsx`
- Gold files: 7 school-level parquet files under `data/gold/education/ccrpi_climate_star_rating/year={2014,2015,2016,2017,2018,2019,2024}/schools.parquet`
- Manifest: `data/gold/education/ccrpi_climate_star_rating/_transform_manifest.json`
- Validation report: `data/gold/education/ccrpi_climate_star_rating/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`, `data/bronze/education/georgiainsights/ccrpi_climate_star_rating/bronze-data-structure.md`

## Contract Verification

- Schema/parquet column match: PASS - contract properties and parquet columns are exactly `year`, `district_code`, `school_code`, `ccrpi_single_score`, `school_climate_star_rating`.
- Column roles and grain: PASS - roles are `year`, `fk_district`, `fk_school`, metric, metric; grain is one row per `year`, `district_code`, `school_code`.
- Metric units and derived quality checks: PASS - `ccrpi_single_score` is `unit: score` with no false 0-100 cap because bonus-point-era values exceed 100; `school_climate_star_rating` is `unit: rating` with `value_min: 1`, `value_max: 5`.
- Categorical enums: N/A - no demographic or topic-specific categorical columns.
- Detail levels and layout metadata: PASS - contract detail levels are `schools` only, matching all gold output; path template and partition columns are coherent.
- Foreign-key descriptors: PASS - `district_code` targets districts and `school_code` targets the composite schools key `(district_code, school_code)`.
- Schema hash/version consistency: PASS - contract `version: 1.0.0`, schema hash present, available years are 2014-2019 and 2024 with gaps 2020-2023.

## Validator Verification

- `_validation.json` fresh + passing: PASS - timestamp is later than the manifest and `"passed": true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 18 pass, 0 fail; schema, grain uniqueness, quality SQL, FKs, vocabulary, and geography nulling all pass.
- Validator warnings explained: PASS - one null-rate warning for `ccrpi_single_score` in 2024 is expected because the 2024 bronze release dropped that column.
- §15b quality-check coverage (cross-column invariants authored): PASS - authored checks cover whole-star ratings, 2024 CCRPI score absence, and the school-only structural fact.

## Manifest Verification

- Files processed coverage: PASS - all 7 current bronze files appear in `files_processed`; current SHA-256 checksums match `bronze-data-structure.md`.
- Categorical and recode coverage: N/A - `categorical_mappings` is empty because no categorical recodes exist.
- Row-count reconciliation: PASS - 15,893 bronze rows to 15,892 gold rows; the single filtered row is the documented byte-identical 2015 duplicate.
- Metric stats sanity: PASS - CCRPI score ranges match bronze, including preserved 2016 max 110.3; star ratings are whole values in 1-5 with expected null counts.

## Row and Join Accounting

- Bronze file/year disposition: PASS - 2014-2019 and 2024 processed; no 2020-2023 bronze files exist and no synthetic years were created.
- Filter accounting: PASS - one 2015 duplicate `(705, 1052)` filtered after collision guard; direct bronze check found two identical rows and one gold row.
- Join accounting: N/A - transform performs no joins. FK validation against dimensions passed with 0 unmatched districts and 0 unmatched schools.
- Deduplication accounting: PASS - direct per-year key counts show distinct bronze keys equal gold rows for every year after the one 2015 duplicate is accounted for.
- Aggregation/unpivot accounting: N/A - no aggregation or unpivot occurs; this is a one-source-row to one-gold-row transform except the duplicate removal.

## Reconciliation Checks

- Artifact freshness: PASS - required runtime artifacts exist, validation passed, and validation timestamp is not older than manifest generation.
- Contract freshness: PASS - contract was emitted from the current transform/gold path and there is no `_metadata.json` dependency.
- Year coverage: PASS - gold years are exactly 2014, 2015, 2016, 2017, 2018, 2019, and 2024.
- Row preservation: PASS - per-year gold rows equal distinct bronze `(System ID, School ID)` keys: 2014 2261, 2015 2270, 2016 2269, 2017 2235, 2018 2278, 2019 2279, 2024 2300.
- Column coverage: PASS - fact keys and metrics map from `Year`/`School Year`, `System ID`, `School ID`, `CCRPI Single Score`, and `School Climate Star Rating`; name columns are correctly excluded as dimension attributes.
- Recode accuracy: PASS - only deterministic casts/padding occur; sampled IDs preserve 3-digit district codes, 7-digit district codes, and 4-digit school codes.
- Asian-family demographic recodes (§5b): N/A - no demographic column or race buckets.
- Demographic mutual exclusivity (§5a - no rollup row alongside split source rows in the same category): N/A - no demographic axis.
- Demographic collision aggregation before dedup (§5): N/A - no demographic axis.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS - actual parquet order is `year`, `district_code`, `school_code`, `ccrpi_single_score`, `school_climate_star_rating`.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS - parquet contains no forbidden fact-table columns; `detail_level` is encoded by `schools.parquet`.
- Canonical column vocabulary (§16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - CCRPI/FESR-style names use canonical `ccrpi_single_score` and `school_climate_star_rating`.
- Shared categorical utilities applied (§10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A - no grade or subject columns.
- Tidy long format (§9 - no demographics/years/components as column names): PASS - no year-keyed, demographic-keyed, or component-keyed metric columns.
- FK keys present in dimension tables (§13 - `district_code`, `school_code`, `demographic`): PASS - direct anti-joins found 0 unmatched districts and 0 unmatched composite school keys.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - row grain and FK joins are derivable from the contract; no filterable categoricals exist.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS - IDs are strings, metrics are Float64, score/rating scales are not incorrectly converted to 0-1, suppression becomes NULL, and no gold files are empty.

## Spot Checks

### Check 1

- Bronze: `CCRPI Score and School Climate Star Rating 04.14.15.xlsx`, Appling County High School (`Year=2014`, `System ID=601`, `School ID=0103`) has `CCRPI Single Score=69.1`, `School Climate Star Rating=4`.
- Transform path: `transform_file()` resolves in-file year at `transform.py:287-296`; `_transform_one_file()` renames/casts metrics and formats IDs at `transform.py:200-246`.
- Gold: `year=2014`, `district_code=601`, `school_code=0103`, `ccrpi_single_score=69.1`, `school_climate_star_rating=4.0`.
- Result: MATCH

### Check 2

- Bronze: `2019 School Climate Star Rating_11_26_19.xls`, Appling County High School (`School Year=2019`, `System ID=601`, `School ID=0103`) has string `CCRPI Single Score=76.2`, `School Climate Star Rating=4`.
- Transform path: era 2 routes through `detect_era_by_columns()` at `transform.py:278`, then casts the string score with `strict=False` at `transform.py:226-246`.
- Gold: `year=2019`, `district_code=601`, `school_code=0103`, `ccrpi_single_score=76.2`, `school_climate_star_rating=4.0`.
- Result: MATCH

### Check 3

- Bronze: `2019 School Climate Star Rating_11_26_19.xls`, Price Academy (`School Year=2019`, `System ID=611`, `School ID=0307`) has suppressed/null `CCRPI Single Score` and null `School Climate Star Rating`.
- Transform path: `read_bronze_file()` handles suppression before `transform_file()` records the file; metric casts preserve nulls at `transform.py:226-246`.
- Gold: `year=2019`, `district_code=611`, `school_code=0307`, both metrics NULL.
- Result: MATCH

### Check 4

- Bronze: `2024 School Climate Star Rating.xlsx`, Telfair County High School (`School Year=2024`, `System ID=734`, bare `School ID=201`) has `School Climate Star Rating=4` and no CCRPI Single Score column.
- Transform path: school code padding at `transform.py:217-224`; missing 2024 CCRPI score is explicitly NULL-filled at `transform.py:236-245`.
- Gold: `year=2024`, `district_code=734`, `school_code=0201`, `ccrpi_single_score=NULL`, `school_climate_star_rating=4.0`.
- Result: MATCH

### Check 5

- Bronze: `2015 School Climate Star Ratings and CCRPI scores.xlsx`, Murray County / Spring Place Elementary School (`System ID=705`, `School ID=1052`) appears twice with identical metrics `68.6` and `5`.
- Transform path: collision guard and dedup at `transform.py:346-364`; filtered duplicate is recorded at `transform.py:365-378`.
- Gold: exactly one row for `year=2015`, `district_code=705`, `school_code=1052`, `ccrpi_single_score=68.6`, `school_climate_star_rating=5.0`.
- Result: MATCH

### Check 6

- Bronze: `2016 Star Rating_CCRP 1.26.17I.xlsx`, Gwinnett School of Mathematics, Science and Technology (`System ID=667`, `School ID=1019`) has `CCRPI Single Score=110.3`, `School Climate Star Rating=5`.
- Transform path: `ccrpi_single_score` is cast but not capped or scaled at `transform.py:226-246`; the contract description documents bonus-point-era values at `transform.py:496-510`.
- Gold: `year=2016`, `district_code=667`, `school_code=1019`, `ccrpi_single_score=110.3`, `school_climate_star_rating=5.0`.
- Result: MATCH

## Notes

- No must-fix findings were identified.
- No prior `data-review-claude.md` or existing `data-review-codex.md` was read before writing this report.
- The only validator warning is the expected 2024 `ccrpi_single_score` null-rate spike caused by the source dropping the column.
