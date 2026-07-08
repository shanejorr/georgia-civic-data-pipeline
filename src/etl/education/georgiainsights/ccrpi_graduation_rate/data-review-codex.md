# Data Review: ccrpi_graduation_rate

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze inventory, transform logic, contract, validator, manifest, and gold parquet reconcile; no must-fix transformation defects found.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH — manifest generated 2026-06-12T14:05:03.548467+00:00; validation timestamp 2026-06-12T14:05:03.629157+00:00 and passed; transform mtime 2026-06-12T14:03:35.268909+00:00.

## Files Reviewed

- Transform: `src/etl/education/georgiainsights/ccrpi_graduation_rate/transform.py`
- Contract: `contracts/education/ccrpi_graduation_rate.odcs.yaml`
- Bronze files: 27 current files under `data/bronze/education/georgiainsights/ccrpi_graduation_rate/`; all 27 SHA-256 checksums match `bronze-data-structure.md`. The 26 `.xls`/`.xlsx`/`.csv` data files are processed; the 2023 PDF is intentionally superseded by the CCRPI workbook plus GOSA CSV.
- Gold files: 40 parquet files under `data/gold/education/ccrpi_graduation_rate/year=*/`, covering 2012-2025.
- Manifest: `data/gold/education/ccrpi_graduation_rate/_transform_manifest.json`
- Validation report: `data/gold/education/ccrpi_graduation_rate/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `data/bronze/education/georgiainsights/ccrpi_graduation_rate/bronze-data-structure.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `src/etl/education/CLAUDE.md`, `CLAUDE.md`.

## Contract Verification

- Schema/parquet column match: PASS — validator reports all 40 parquet files match contract columns: `year`, `district_code`, `school_code`, `demographic`, `rate_type`, `graduation_rate`, `cohort_size`, `graduate_count`, `target`, `ccrpi_flag`.
- Column roles and grain: PASS — roles are year, district FK, school FK, demographic FK, `rate_type` categorical, four numeric metrics, and `ccrpi_flag` categorical; contract grain is `year`, `district_code`, `school_code`, `demographic`, `rate_type`, matching the transform's exported grain after `detail_level` is encoded by filename.
- Metric units and derived quality checks: PASS — `graduation_rate` and `target` are `proportion`; `cohort_size` and `graduate_count` are `count`; derived and authored checks include interval bounds, non-negativity, numerator <= denominator, on-time reconciliation, on-time co-null, on-time school-level-only, five-year counts always null, and target/flag publication coverage.
- Categorical enums: PASS — contract enums match manifest and actual gold values for `demographic`, `rate_type`, and `ccrpi_flag`.
- Detail levels and layout metadata: PASS — contract lists `schools`, `districts`, `states`; gold layout is year-partitioned with those detail files where present.
- Foreign-key descriptors: PASS — validator and direct anti-joins found 0 unmatched district, school, and demographic keys; school FK is composite on `district_code`, `school_code`.
- Schema hash/version consistency: PASS — contract version is `1.0.0`; schema hash is `4ea3f58b930d23d5845b0d0314f21f38199d15cfaeaf20c00f1ff310b1d6ab89`.

## Validator Verification

- `_validation.json` fresh + passing: PASS — validation is newer than the manifest and reports `passed: true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS — 21 pass, 0 fail, 0 warning; `contract_quality_sql` reports all 14 quality checks pass.
- Validator warnings explained: N/A — validation emitted no warnings.
- §15b quality-check coverage (cross-column invariants authored): PASS — the transform authors the material cross-column invariants for this topic: count numerator bounds, on-time rate/count reconciliation and co-nullity, on-time school-only structure, null 5-year counts, and target/flag publication coverage. The documented non-invariant `graduate_count / cohort_size == graduation_rate` for 4-year rows is correctly not enforced because rates and counts can come from different release cutoffs.

## Manifest Verification

- Files processed coverage: PASS — manifest records 26 processed data files; the only unprocessed bronze file is the documented superseded 125-page 2023 PDF.
- Categorical and recode coverage: PASS — `unmapped_count` is 0 for `demographic`, `rate_type`, and `ccrpi_flag`; actual gold distinct values match manifest `gold_values_produced`.
- Row-count reconciliation: PASS — manifest total gold is 163,568, matching actual parquet. In-memory accounting found 216,628 transformed rows before cross-family merge, 4,490 explicitly filtered superseded 2021 school 5-year rows, and 163,568 rows after precedence merge.
- Metric stats sanity: PASS — gold ranges are valid: `graduation_rate` 0.0-1.0, `target` 0.022-0.9, `cohort_size` 10-142094, `graduate_count` 0-123910, and 0 rows where `graduate_count > cohort_size`.

## Row and Join Accounting

- Bronze file/year disposition: PASS — all 2012-2025 source years are represented; dual-year CCRPI files are booked by row year; Family C/D/F filename years and the Family F `2022-23` school year are pinned by transform logic.
- Filter accounting: PASS — Family C All-Students sheets contribute counts to `all` rows and are otherwise not fact rows; the Family D All Student sheet is skipped as a verified subset; 4,490 Family A 2021 school-level 5-year rows are explicitly filtered because Family D is the primary 2021 5-year publication; the PDF is intentionally superseded.
- Join accounting: PASS — Family C count joins use `nulls_equal=True` for aggregate geography keys and attach counts only to `demographic == 'all'`; no row multiplication remains after the final grain check.
- Deduplication accounting: PASS — no within-family duplicate natural-key groups were found in the in-memory transformed data; cross-family duplicates are resolved by documented source precedence and the final validator grain check passes.
- Aggregation/unpivot accounting: PASS — no derived district/state aggregation is performed; wide source sheets are normalized to one row per geography, demographic, and `rate_type`. Family C's sheet combine is a lookup-style count attachment, not a rate recomputation.

## Reconciliation Checks

- Artifact freshness: PASS — current bronze checksums match the structure doc, and gold/manifest/validation are from the current transform.
- Contract freshness: PASS — contract matches current parquet and has no `_metadata.json` dependency.
- Year coverage: PASS — gold covers all years 2012-2025 with no gaps; 2012-2013 correctly lack state rows and 2025 is thinner because no 2025 on-time release exists and the 2025 CCRPI 5-year slice lands in 2024.
- Row preservation: PASS — row count changes are explained by non-fact count sheets, superseded rows, and cross-family overlap collapse; no unexplained loss found.
- Column coverage: PASS — fact keys, `rate_type`, metrics, and `ccrpi_flag` trace to bronze columns or documented constants; names, grade configuration, detail-level labels, and source-only year fields are correctly excluded from fact parquet.
- Recode accuracy: PASS — `G/Y/R` map to `green/yellow/red`; 4-year/5-year literals and CCRPI labels map to `4_year`/`5_year`; on-time is a documented transform constant; demographic labels map to canonical values.
- Asian-family demographic recodes (§5b): PASS — every inspected source label is `Asian/Pacific Islander`; no separate Pacific Islander, Native Hawaiian, or NHPI label appears. Gold emits `asian_pacific_islander` and never emits `asian` or `pacific_islander`.
- Demographic mutual exclusivity (§5a — no rollup row alongside split source rows in the same category): PASS — race values present are `asian_pacific_islander`, `black`, `hispanic`, `multiracial`, `native_american`, and `white`; 0 groups contain combined Asian/Pacific Islander alongside split Asian or Pacific Islander rows.
- Demographic collision aggregation before dedup (§5): N/A — actual source labels do not create same-file canonical collisions; the transform's within-family collision guard would fail on future divergent duplicates.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS — actual parquet order is `year`, `district_code`, `school_code`, `demographic`, `rate_type`, metrics, then `ccrpi_flag`.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS — actual parquet has no `topic`, `detail_level`, name, grade-configuration, or census/crosswalk columns.
- Canonical column vocabulary (§16 — `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS — graduation-specific canonical names `cohort_size`, `graduate_count`, `graduation_rate`, `target`, and `ccrpi_flag` are used.
- Shared categorical utilities applied (§10a — `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): N/A — no `grade_level` or `subject` column; demographics use `normalize_demographic_column`.
- Tidy long format (§9 — no demographics/years/components as column names): PASS — demographic and rate methodology are row values, not columns.
- FK keys present in dimension tables (§13 — `district_code`, `school_code`, `demographic`): PASS — direct anti-joins and validator FK checks found 0 unmatched keys.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS — contract roles expose `rate_type` and `ccrpi_flag` as categoricals and derive FK joins from dimensions; `ccrpi_flag` is excluded from grain as a performance attribute.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS — rates are on 0-1 scale, counts are Int64, IDs are strings with zero padding, aggregate geography keys are nulled, and suppression markers become NULL.

## Spot Checks

### Check 1

- Bronze: `2023 CCRPI Graduation Rates, Targets, and Flags by Subgroup_12_14_23.xlsx`, state `ALL Students` 4-year row has `Graduation Rate=84.36`, `Target=84.24`, `Flag=G`; `GOSA_4-Year_Cohort_Graduation_Rate_2022-23_12.15.23.csv`, state `Grad Rate -ALL Students` has `PROGRAM_TOTAL=113735`, `PROGRAM_PERCENT=84.36`, `TOTAL_COUNT=134822`.
- Transform path: Family A rate/target/flag scaling in `_transform_family_a` lines 616-680; Family F count scaling in `_transform_family_f` lines 986-1041; precedence merge in `_merge_cross_family` lines 1170-1239.
- Gold: `year=2023`, state, `demographic=all`, `rate_type=4_year` has `graduation_rate=0.8436`, `cohort_size=134822`, `graduate_count=113735`, `target=0.8424`, `ccrpi_flag=green`.
- Result: MATCH

### Check 2

- Bronze: `2024 On Time Graduation Rate.xlsx`, row `Year=2024`, `System ID=601`, `School ID=103`, `Reporting Label=ALL Students` has `Total Enrolled=209`, `Total Graduated=200`, `On-Time Graduation Rate=95.69`.
- Transform path: `_transform_family_e` lines 924-978 reads header row 1, pads IDs, scales rate to 0-1, casts counts, and sets `rate_type=on_time`.
- Gold: `year=2024`, `district_code=601`, `school_code=0103`, `demographic=all`, `rate_type=on_time` has `graduation_rate=0.9569`, `cohort_size=209`, `graduate_count=200`, `target=NULL`, `ccrpi_flag=NULL`.
- Result: MATCH

### Check 3

- Bronze: `2025 CCRPI Graduation Rates, Targets, and Flags by Student Group.xlsx`, state `ALL Students` 4-year row has `Graduation Rate=87.22`, `Target=85.62`, `Flag=G`; `2025 4-Year Cohort Graduation Rate State District School by Student Group.xlsx`, state `ALL Students` row has `Graduation Class Size=142094`, `Total Graduated=123910`, `Graduation Rate=87.2`.
- Transform path: Family A wins rate/target/flag and Family C contributes counts through `_merge_cross_family` lines 1170-1239.
- Gold: `year=2025`, state, `demographic=all`, `rate_type=4_year` has `graduation_rate=0.8722`, `cohort_size=142094`, `graduate_count=123910`, `target=0.8562`, `ccrpi_flag=green`.
- Result: MATCH

### Check 4

- Bronze: `2012 Graduation Rate By Subgroups for Public Release.xls`, `System ID=601`, `School ID=0103`, `REPORTING CATEGORY=ALL Students` has `GRADUATION RATE=72.2`.
- Transform path: `_transform_family_b` lines 688-753 maps legacy columns, derives detail level, normalizes demographic, scales rate, and null-fills unpublished counts/target/flag.
- Gold: `year=2012`, `district_code=601`, `school_code=0103`, `demographic=all`, `rate_type=4_year` has `graduation_rate=0.722`, `cohort_size=NULL`, `graduate_count=NULL`, `target=NULL`, `ccrpi_flag=NULL`.
- Result: MATCH

### Check 5

- Bronze: `2018 CCRPI Graduation Rates, Targets, Flags by Subgroup 11_1_18.xlsx`, `System ID=601`, `School ID=0103`, `Reporting Label=Asian/Pacific Islander`, `Graduation Rate Type=4-year graduation rate` has `Graduation Rate=TFS`, `Target=TFS`, `Flag=NA`.
- Transform path: `_read_sheet` lines 364-380 treats suppression markers as NULL; `_transform_family_a` lines 616-680 scales metrics and normalizes `Asian/Pacific Islander` to `asian_pacific_islander`.
- Gold: `year=2018`, `district_code=601`, `school_code=0103`, `demographic=asian_pacific_islander`, `rate_type=4_year` has `graduation_rate=NULL`, `target=NULL`, `ccrpi_flag=NULL`.
- Result: MATCH

## Notes

- The structure doc's older Gold Schema Classification table contains pre-rebuild candidate names such as `on_time_graduation_rate`, `graduation_class_size`, `total_graduated`, and `ccrpi_target`; the current transform and contract intentionally consolidate those into `graduation_rate`, `cohort_size`, `graduate_count`, and `target` with `rate_type` as the methodology discriminator.
- Target and flag are not required to be co-null: 1,211 gold rows have a published target but NULL flag because the source flag is `NA` when the rate is suppressed or not comparable. This matches bronze semantics and is not a defect.
