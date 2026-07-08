# Data Review: ccrpi_content_mastery

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: contract, manifest, validator, bronze files, transform logic, and current gold parquet reconcile with no required transform fixes.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - transform mtime `2026-06-12T13:14:23.081572+00:00`, manifest `2026-06-12T13:16:52.624180+00:00`, validation `2026-06-12T13:16:52.923900+00:00`; bronze freshness gate passed with all 13 checksums matching and no unanalyzed files.

## Files Reviewed

- Transform: `src/etl/education/georgiainsights/ccrpi_content_mastery/transform.py`
- Contract: `contracts/education/ccrpi_content_mastery.odcs.yaml`
- Bronze files: 13 Excel files, 2012-2019 and 2021-2025; 2020 absent by source/COVID pause.
- Gold files: 35 parquet files under `data/gold/education/ccrpi_content_mastery/year=*/`, plus `README.md`, `_transform_manifest.json`, and `_validation.json`.
- Manifest: `data/gold/education/ccrpi_content_mastery/_transform_manifest.json`
- Validation report: `data/gold/education/ccrpi_content_mastery/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`.

## Contract Verification

- Schema/parquet column match: PASS - contract properties exactly match actual parquet columns: `year`, geography keys, `demographic`, `grade_cluster`, `assessment_type`, `subject`, metrics, and `ccrpi_flag`.
- Column roles and grain: PASS - grain is `year, district_code, school_code, demographic, grade_cluster, assessment_type, subject`; `ccrpi_flag` is correctly excluded as a derived attribute.
- Metric units and derived quality checks: PASS - `participation_rate` is `ratio`; learner bands are `proportion`; `indicator_score` and `target` are `score`, with `target` bounded 0-100 and `indicator_score` intentionally unbounded above because 2015-2017 and 2021 can exceed 100.
- Categorical enums: PASS - contract enums match manifest and actual gold values for `demographic`, `grade_cluster`, `assessment_type`, `subject`, and `ccrpi_flag`.
- Detail levels and layout metadata: PASS - contract lists `schools`, `districts`, `states`; actual gold has school files for all 13 years and district/state files for 2014-2019 and 2021-2025.
- Foreign-key descriptors: PASS - validator and direct anti-joins found 0 unmatched district, school, or demographic keys; `RTC` resolves to the districts dimension as `state_special`.
- Schema hash/version consistency: PASS - version is `1.0.0`; schema hash is `ff9e66fdba8686e544dc0ec4ac57143bdd8d6312c03dcf714365a7f49605a851`; available years are 2012-2019 and 2021-2025 with gap 2020.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp is later than manifest generation and `"passed": true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 21 checks passed, 0 failed, 0 warnings; all 23 contract quality SQL checks passed.
- Validator warnings explained: N/A - no validation warnings were emitted.
- §15b quality-check coverage (cross-column invariants authored): PASS - contract enforces learner-band partition checks, cumulative consistency, co-suppression, score-band co-null behavior, era coverage for `assessment_type`, target/flag era coverage, and 2024 mathematics target/flag nulling.

## Manifest Verification

- Files processed coverage: PASS - all 13 current bronze Excel files appear in `files_processed`; bronze checksum verification also passed.
- Categorical and recode coverage: PASS - all recorded categoricals have `unmapped_count: 0`; map entries are semantically correct, including `Asian/Pacific Islander -> asian_pacific_islander`, `English -> english_language_arts`, `G* -> green_star`, and era spelling drift for Native American and disability labels.
- Row-count reconciliation: PASS - manifest total bronze rows and total gold rows both equal 1,707,230; every year has expansion factor 1.0 and zero filtered rows.
- Metric stats sanity: PASS - actual metric ranges match contract semantics: no negative metrics, no learner-band proportion above 1, `target` within 1.7-95.0, and documented `participation_rate > 1` only in 2012 (21 rows) and 2013 (73 rows).

## Row and Join Accounting

- Bronze file/year disposition: PASS - every bronze file is processed once; no 2020 file exists and no gold 2020 partition exists.
- Filter accounting: N/A - transform reports and manifest records zero filtered rows.
- Join accounting: N/A - transform performs no row-affecting joins; FK joins are consumer-side and validator-checked against dimensions.
- Deduplication accounting: PASS - actual gold has 0 duplicate natural-key groups; manifest row counts remain 1:1 after defensive deduplication.
- Aggregation/unpivot accounting: PASS - transform preserves source rows without unpivot expansion or aggregate derivation; source aggregate rows are routed by `ALL` sentinels into state/district files.

## Reconciliation Checks

- Artifact freshness: PASS - transform predates manifest; validation postdates manifest; bronze checksums match the structure report.
- Contract freshness: PASS - contract and parquet column order match; no `_metadata.json` dependency exists.
- Year coverage: PASS - gold years are 2012-2019 and 2021-2025; 2020 is absent as documented.
- Row preservation: PASS - all 1,707,230 bronze rows land in gold; no unexplained loss or multiplication.
- Column coverage: PASS - fact keys, categoricals, and metrics from the structure report are either mapped to gold or validly excluded as dimension attributes/non-fact fields (`System Name`, `School Name`, `Grade Configuration`).
- Recode accuracy: PASS - direct bronze distinct-value inspection across all files matches manifest values and contract enums.
- Asian-family demographic recodes (§5b): PASS - every era publishes explicit `Asian/Pacific Islander`; no `asian` or `pacific_islander` gold rows exist.
- Demographic mutual exclusivity (§5a - no rollup row alongside split source rows in the same category): PASS - gold emits the combined `asian_pacific_islander` convention only, with 0 split Asian/Pacific Islander rows.
- Demographic collision aggregation before dedup (§5): PASS - source label drift collapses only equivalent labels across years; actual gold has no duplicate grain groups.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS - actual parquet order matches the standard and contract.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS - actual parquet has none of the forbidden columns.
- Canonical column vocabulary (§16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - uses `subject`, `indicator_score`, `target`, `ccrpi_flag`, and `pct_<level>_learner` / `_or_above` names.
- Shared categorical utilities applied (§10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): PASS - no `grade_level` column; `subject` passes through topic-local map and `apply_subject_normalization`.
- Tidy long format (§9 - no demographics/years/components as column names): PASS - demographic and subject are row values, not wide columns; learner bands are metric columns for a four-band metric family.
- FK keys present in dimension tables (§13 - `district_code`, `school_code`, `demographic`): PASS - direct anti-joins found 0 unmatched district, school, or demographic keys; school checks use the composite `(district_code, school_code)`.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - contract exposes independent categorical filters and FK descriptors consistent with the actual table.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS - suppression markers become NULL, geography sentinels become NULL at aggregate levels, IDs stay zero-padded strings, and percentages/rates use the documented scale.

## Spot Checks

### Check 1

- Bronze: `2021 Content Mastery by Subgroup 12.08.21.xlsx`, district aggregate row `System ID=605`, `School ID=ALL`, `Reporting Label=Asian/Pacific Islander`, `Content Area=Mathematics`, `Participation Rate=93.75`, learner bands `20.00/6.67/26.67/46.67`, `Achievement Rate=100.00+`.
- Transform path: `_transform_scores` lines 731-752 reconstructs `100.00+` as `0.5*developing + proficient + 1.5*distinguished`; `_transform_bands_target_flag` lines 787-805 scales bands to 0-1 and derives cumulatives.
- Gold: `year=2021/districts.parquet` has `district_code=605`, `school_code=NULL`, `demographic=asian_pacific_islander`, `subject=mathematics`, `participation_rate=0.9375`, `indicator_score=100.01`, bands `0.2/0.0667/0.2667/0.4667`, cumulatives `0.8001/0.7334`.
- Result: MATCH

### Check 2

- Bronze: `2023 CCRPI Content Mastery Scores, Targets, and Flags by Subgroup_12_14_23.xlsx`, school row `System ID=603`, `School ID=3050`, `Reporting Label=Multi-Racial`, `Indicator=Mathematics`, `Participation Rate=1`, `Indicator Score=100.00+`, `Target=90`, `Flag=G`.
- Transform path: `_transform_scores` lines 753-767 caps 2023 `100.00+` at 100.0; `_transform_bands_target_flag` lines 817-823 casts target and maps flag.
- Gold: `year=2023/schools.parquet` has `district_code=603`, `school_code=3050`, `demographic=multiracial`, `subject=mathematics`, `participation_rate=1.0`, `indicator_score=100.0`, `target=90.0`, `ccrpi_flag=green`.
- Result: MATCH

### Check 3

- Bronze: `2015 Content Mastery By Subgroup.xlsx`, RTC aggregate row `System ID=RTC`, `School ID=ALL`, `Grade Cluster=H`, `Reporting Category=ALL Students`, `Assessment Type=EOC`, `Assessment Subject=9th Grade Literature and Composition`, `Participation Rate=66.867`, `Weighted Proficiency Rate=20.139`.
- Transform path: `_derive_keys` lines 624-642 routes `School ID=ALL` to district detail and preserves `RTC`; `_transform_scores` lines 712-770 divides participation by 100 and preserves score scale.
- Gold: `year=2015/districts.parquet` has `district_code=RTC`, `school_code=NULL`, `demographic=all`, `grade_cluster=high`, `assessment_type=eoc`, `subject=9th_grade_literature_and_composition`, `participation_rate=0.66867`, `indicator_score=20.139`.
- Result: MATCH

### Check 4

- Bronze: `2013 Content Mastery By Subgroups for Public Release.xls`, school row `System ID=601`, `School ID=0103`, `Reporting Category=Asian/Pacific Islander`, `Assessment Type=EOCT`, `Assessment Subject=9th Grade Literature and Composition`, suppressed `Participation Rate=NULL`, `Meets Exceeds Rate=NULL`.
- Transform path: `_read_data_sheets` lines 524-529 applies suppression-aware reads; `_transform_scores` lines 710-725 uses `strict=False` numeric casts.
- Gold: `year=2013/schools.parquet` has the matching key with `demographic=asian_pacific_islander`, `participation_rate=NULL`, `indicator_score=NULL`.
- Result: MATCH

### Check 5

- Bronze: `2024 CCRPI Content Mastery Scores, Targets, and Flags.xlsx`, school row `System ID=601`, `School ID=103`, `Indicator=Mathematics`, `Participation Rate=0.9935`, `Indicator Score=68.98`, `Target=NULL`, `Flag=NULL`.
- Transform path: `transform_file` lines 870-879 retries the disclaimer header row; `_transform_bands_target_flag` lines 817-823 preserves NULL target/flag.
- Gold: `year=2024/schools.parquet` has `district_code=601`, `school_code=0103`, `subject=mathematics`, `participation_rate=0.9935`, `indicator_score=68.98`, `target=NULL`, `ccrpi_flag=NULL`.
- Result: MATCH

## Notes

- No Required Fixes were identified.
- The 2021 formula audit over all numeric bronze rows found maximum absolute deviation `0.005000000000023874`, matching the documented rounding tolerance; 1,772 `100.00+` rows were reconstructed.
- Gold cumulative learner-band checks found 0 mismatches; 2021 has 26 band-partition deviations over 0.025 as documented source defects, and 2022 has 0.
- The review did not read prior `data-review-claude.md` or any existing Codex report before completing findings.
