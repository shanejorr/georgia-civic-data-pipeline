# Data Review: advanced_placement_ap_scores

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Contract, manifest, validator, bronze traces, row accounting, subject recodes, duplicate aggregation, and masked source-defect handling all support the current gold output.

## Summary

- Review date: 2026-06-12
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - `scripts/check_bronze_freshness.py education gosa advanced_placement_ap_scores` passed; transform mtime `2026-06-12T03:59:50.635821+00:00`, manifest `2026-06-12T03:59:51.791550+00:00`, validation `2026-06-12T03:59:51.873801+00:00`.

## Files Reviewed

- Transform: `src/etl/education/gosa/advanced_placement_ap_scores/transform.py`
- Contract: `contracts/education/advanced_placement_ap_scores.odcs.yaml`
- Bronze files: 21 source files, `advanced_placement_ap_scores_2004.csv` through `advanced_placement_ap_scores_2024.csv`; `.DS_Store` is ignored by the freshness gate.
- Gold files: 63 parquet files, one `schools.parquet`, `districts.parquet`, and `states.parquet` partition for each year 2004-2024.
- Manifest: `data/gold/education/advanced_placement_ap_scores/_transform_manifest.json`
- Validation report: `data/gold/education/advanced_placement_ap_scores/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, `.claude/skills/data-cleaning-standards/SKILL.md`, `.claude/skills/data-cleaning-standards/code-review-checklist.md`, `.claude/skills/bronze-data-structure/SKILL.md`, `.claude/skills/transform-topic/SKILL.md`, `.claude/skills/data-review-claude/SKILL.md`, `.claude/skills/fix-from-reviews/SKILL.md`, `.claude/skills/full-pipeline/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `src/etl/education/CLAUDE.md`.

## Contract Verification

- Schema/parquet column match: PASS - contract properties exactly match parquet columns: `year`, `district_code`, `school_code`, `subject`, `num_tested`, `num_tests_taken`, `num_tests_3_or_higher`, `pct_tests_3_or_higher`.
- Column roles and grain: PASS - contract roles are year, education FKs, `subject` categorical, and four metrics; grain is `year`, `district_code`, `school_code`, `subject`, matching actual uniqueness.
- Metric units and derived quality checks: PASS - count metrics use `unit: count`; `pct_tests_3_or_higher` uses `unit: proportion`; derived non-negative and [0, 1] checks are present.
- Categorical enums: PASS - 42 `subject` enum values match manifest `gold_values_produced` and actual gold distinct values.
- Detail levels and layout metadata: PASS - detail levels are `schools`, `districts`, `states`; path template and year partitioning match the 63 parquet files.
- Foreign-key descriptors: PASS - district and composite school FK descriptors match education dimension contracts; validator confirms all 189 district keys and 662 school keys resolve.
- Schema hash/version consistency: PASS - contract version is `1.0.0`, schema hash is present, and contract was emitted after current gold export.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation timestamp is newer than manifest and `"passed": true`.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 21 validator checks passed, 0 failed, 0 warnings.
- Validator warnings explained: N/A - validation reported no warnings.
- §15b quality-check coverage (cross-column invariants authored): PASS - contract includes checks for qualifying count <= tests taken, pinned exceptions for `num_tested > num_tests_taken`, derived-rate formula, derived-rate co-null behavior, district rollup not below own largest school, and legacy years all-subjects only.

## Manifest Verification

- Files processed coverage: PASS - manifest lists all 21 expected source files and the correct five eras; bronze freshness confirms checksums match the structure report.
- Categorical and recode coverage: PASS - `subject` has 42 bronze values, 42 mapped gold values, no unused map entries against current bronze, and `unmapped_count: 0`.
- Row-count reconciliation: PASS - total bronze rows 105,829, total gold rows 105,821, total filtered 8; the 8-row difference is fully accounted for by 3 dropped malformed/placeholder rows and 5 duplicate rows collapsed into summed entities.
- Metric stats sanity: PASS - counts are non-negative; `pct_tests_3_or_higher` ranges from 0.0 to 1.0; null profiles match documented suppression eras and the 2005 masked district rollups.

## Row and Join Accounting

- Bronze file/year disposition: PASS - every source year 2004-2024 appears once in manifest and gold.
- Filter accounting: PASS - manifest records one 2004 missing compound-ID delimiter row, one 2005 malformed `644:xxxx` row, one 2007 placeholder `678:9999` row, and five pinned duplicate rows collapsed by aggregation.
- Join accounting: N/A - transform does not join source lookups; FK joins are post-export API/dimension semantics and passed validator coverage.
- Deduplication accounting: PASS - pinned legacy duplicate groups are aggregated before collision checks; actual gold has zero duplicate natural-key groups.
- Aggregation/unpivot accounting: PASS - no wide demographic unpivot is needed; legacy eras emit `all_subjects`; 2011-2024 retain source per-subject rows plus source `ALL Subjects` rows. The 2009 `722:0176` duplicate rows `213/417/251` and `63/70/22` correctly aggregate to gold `276/487/273`.

## Reconciliation Checks

- Artifact freshness: PASS - all required artifacts exist and validation is newer than the manifest.
- Contract freshness: PASS - contract/parquet schema matches; no `_metadata.json` dependency is used.
- Year coverage: PASS - gold covers 2004-2024 with no gaps and no unexpected years.
- Row preservation: PASS - row counts are 1:1 except the explicitly documented filtered/collapsed rows.
- Column coverage: PASS - fact keys and metrics from bronze are represented; names, report labels, and detail labels are correctly excluded from fact output.
- Recode accuracy: PASS - AP subject labels map semantically to canonical snake_case values, including `Calculus A` -> `calculus_a`, `Eng. Language & Comp` -> `english_language_and_composition`, `Gov. & Pol. U.S.` -> `government_and_politics_us`, and 2024 additions.
- Asian-family demographic recodes (§5b): N/A - this topic has no demographic axis or race buckets.
- Demographic mutual exclusivity (§5a - no rollup row alongside split source rows in the same category): N/A - no demographic column.
- Demographic collision aggregation before dedup (§5): N/A - no demographic column.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, §1): PASS - actual parquet order is year, district_code, school_code, subject, then metrics.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, §11/§12): PASS - exported parquet omits `detail_level`, names, report labels, and crosswalk IDs.
- Canonical column vocabulary (§16 - `num_tested`, `grade_level`, `subject`, `indicator_score`, proficiency-band names, `_or_above`, rate columns without `_pct`, etc.): PASS - AP content uses `subject`, count metrics use canonical `num_*` names, and the share metric uses `pct_tests_3_or_higher`.
- Shared categorical utilities applied (§10a - `normalize_grade_column`, `apply_subject_normalization` when the gold output has those columns): PASS - transform applies `apply_subject_normalization`; no grade column exists.
- Tidy long format (§9 - no demographics/years/components as column names): PASS - subject is a categorical row axis; no year, subject, or demographic values are encoded as columns.
- FK keys present in dimension tables (§13 - `district_code`, `school_code`, `demographic`): PASS - validator confirmed district and composite school keys resolve; no demographic FK applies.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - `subject` is filterable through the contract; FK descriptors are present and composite-aware for schools.
- Standards compliance (catch-all for §1-§16 items not enumerated above): PASS - suppression markers become NULL, IDs are strings with leading zeros, aggregate geography is NULLed, and fact table contains only keys, categorical, and metrics.

## Spot Checks

### Check 1

- Bronze: `advanced_placement_ap_scores_2007.xls`, row `SysSchoolID=601:103`, Appling County High School, values `17` students, `17` tests, `12` scores 3+, bronze percent `70.6`.
- Transform path: `_transform_legacy()` splits `SysSchoolID`, zero-pads `school_code`, sets `subject = all_subjects`, casts counts, and recomputes `_pct_expr()`.
- Gold: year 2007, `district_code=601`, `school_code=0103`, `subject=all_subjects`, values `17`, `17`, `12`, `pct_tests_3_or_higher=0.7058823529411765`.
- Result: MATCH

### Check 2

- Bronze: `advanced_placement_ap_scores_2024.csv`, row `SCHOOL_DISTRCT_CD=708`, `INSTN_NUMBER=0105`, `TEST_CMPNT_TYP_NM=Precalculus`, values `109`, `109`, `108`.
- Transform path: `_transform_tidy()` validates Era E detail level, maps subject through `SUBJECT_MAP` and `apply_subject_normalization`, casts counts, and recomputes `_pct_expr()`.
- Gold: year 2024, `district_code=708`, `school_code=0105`, `subject=precalculus`, values `109`, `109`, `108`, `pct_tests_3_or_higher=0.9908256880733946`.
- Result: MATCH

### Check 3

- Bronze: `advanced_placement_ap_scores_2022.csv`, district `625`, `INSTN_NUMBER=SCHOOL_ALL`, `TEST_CMPNT_TYP_NM=Japanese Lang. & Culture`, all three metric cells read as suppression NULL.
- Transform path: `_transform_tidy()` casts metric columns with `strict=False`; `_pct_expr()` yields NULL when inputs are NULL.
- Gold: year 2022, `district_code=625`, `school_code=NULL`, `subject=japanese_language_and_culture`, all four metrics NULL.
- Result: MATCH

### Check 4

- Bronze: `advanced_placement_ap_scores_2009.xls`, duplicate key `722:0176` appears twice with values `213/417/251` and `63/70/22`.
- Transform path: `_aggregate_pinned_legacy_duplicates()` recognizes the pinned duplicate group and sums count components, then recomputes the rate.
- Gold: year 2009, `district_code=722`, `school_code=0176`, `subject=all_subjects`, values `276/487/273`, `pct_tests_3_or_higher=0.5605749486652978`.
- Result: MATCH

### Check 5

- Bronze: `advanced_placement_ap_scores_2005.csv`, district rollups for `681`, `717`, `720`, `721`, `722`, `724`, `758`, and `779` contradict their own school-row sums; examples include `722:ALL` published `70/97/72` while its own school rows sum to `482/842/457`, and `724:ALL` published `167/202/111` while own school rows sum to `67/104/51`.
- Transform path: `_null_2005_misassigned_district_rollups()` pins exactly these 8 district rollups and records masked values for all four metrics.
- Gold: the 8 2005 district `all_subjects` rows exist, with `district_code` preserved and all four metrics NULL.
- Result: MATCH

## Notes

- No prior `data-review-claude.md` or existing `data-review-codex.md` was read before forming this verdict.
- This audit did not edit transform, bronze, gold, contracts, utilities, or docs. Only this report file was written.
