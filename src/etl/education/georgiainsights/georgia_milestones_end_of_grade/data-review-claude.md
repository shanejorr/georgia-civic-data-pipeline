# Data Review: georgia_milestones_end_of_grade

**Date**: 2026-06-12
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Value-level accuracy is excellent: every one of 16 bronze-to-gold traces (extreme rows, one entity per era, all repair/fold/remap paths) matched exactly, the rollup feasibility screen is perfect (district sums = state values, school sums = district values, ratio 1.0 across all 222 state cells and 45,267 district cells), and the documented ULP fix (`df.rechunk()` after footnote filtering) is present, correctly commented, and its mechanism was reproduced empirically. **v1 parity: MATCH — byte-identical with v1 gold** (`51aebad2c9820edc7b9435ecfcf90a32f07384acc3165aee3d05f3b941a3b680`, recomputed independently). The single Required Fix is contract hardening, not a data inaccuracy: three era-availability structural facts (Lexile ≥2018, std-dev ≥2022, SGP ≥2024) and one block-structure fact (scale scores never published for EOC/Combined rows) are documented in notes but unenforced by quality checks, while two sibling era facts (pct_enrolled 2021-only, EOC 2016-2021) are enforced — an authoring asymmetry. All four proposed checks pass with 0 violations on current gold, so fixing them cannot change gold bytes or parity.

## Manifest Verification

| Column | Map entries | Bronze values seen | Unmapped | Status |
|---|---|---|---|---|
| subject | 19 | 19 (all in map) | 0 | PASS |
| assessment_type | 19 | 19 (all in map) | 0 | PASS |
| grade_level | 6 | 6 | 0 | PASS |

**Subject map (all 19 entries reviewed):**

| Bronze super-header | Gold subject | Correct? |
|---|---|---|
| English Language Arts / `- EOG` / `- EOC` / `- EOG and EOC Combined` | english_language_arts | YES (4 entries; variant carried in assessment_type) |
| Mathematics / `- EOG` / `- EOC` / `- EOG and EOC Combined` | mathematics | YES (4 entries) |
| Science / `- EOG` / `- EOC` / `- EOG and EOC Combined` | science | YES (4 entries) |
| Social Studies / `- EOG` | social_studies | YES (2 entries; no EOC variants exist in bronze — verified, see Corrections) |
| HS Physical Science | physical_science | YES — aligns with the EOC sibling's canonical label; grade-8 scope carried by grade_level |
| Reading Status* / Reading Status^ | english_language_arts | YES — metric family folded onto parent ELA row (§16 "Assessment subject"); interim label never reaches gold |
| SGP English Language Arts | english_language_arts | YES — fold parent |
| SGP Mathematics | mathematics | YES — fold parent |

**assessment_type map:** every bare block and `- EOG` variant → `eog`; `- EOC` → `eoc`; `- EOG and EOC Combined` → `eog_and_eoc_combined`. All 19 entries correct. `Reading Status*/^` and `SGP *` → `eog` is correct: the fold join carries assessment_type, and the global scan below proves the RS population equals the ELA-**EOG** population (so eog is the right parent). `HS Physical Science` → `eog` follows bronze (no EOC suffix in the EOG release) and matches v1.

**grade_level map:** `3`→`03` … `8`→`08` — all correct, matches contract enum.

**2c contract cross-check:** gold distincts == contract enums exactly — subject {english_language_arts, mathematics, physical_science, science, social_studies}; assessment_type {eoc, eog, eog_and_eoc_combined}; grade_level {03..08}. PASS.

**2d:** unmapped_count = 0 on all three columns. PASS.

**2e Asian/PI conflation:** N/A — bronze publishes no demographic breakdowns anywhere (verified: no SUBGROUP/Reporting Category columns; gold has no `demographic` column, per §5).

**2f mutual exclusivity:** N/A — no demographic axis.

**Row-count reconciliation** (manifest `row_counts`, arithmetic verified):

| Drop reason | Rows | Where |
|---|---|---|
| footnote_or_legend_row | 183 | dropped in readers, **before** the bronze count |
| state_non_administered_placeholder_row | 106 | dropped in readers, before the bronze count |
| non_administered_placeholder_block | 2,434 | post-concat |
| reading_status folds → ELA | 48,278 | post-concat |
| SGP-ELA folds → ELA | 10,992 | post-concat |
| SGP-Math folds → Math | 10,992 | post-concat |

307,944 bronze long rows − (2,434 + 48,278 + 10,992 + 10,992) = **235,248 = total_gold = actual parquet rows** (verified). `total_filtered_explicit` 72,985 = 72,696 + 289, where 289 = 183 + 106 (ledgered but excluded from the bronze count by construction). Per-year `filtered_explicit − filtered` deltas (1/24/51/51/90/18/18/18/18) sum to exactly 289. Fully reconciled. Reclassified ledger: 144 state-school 799 remaps (12 events × 12 rows: 3 entities × 4 subjects × {6 district + 6 school members}) + 256 charter promotions, 2015 only; **0 fold orphans** (no orphan-relabel events). Expansion factors per year are consistent with era content (1.0 in 2015 — no RS/SGP/placeholders; ~0.79 in 2018-19 — RS folds; ~0.50 in 2024-25 — RS + 2 SGP folds).

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| (filename year) | year | MAPPED (verified: Spring_2018 file → year 2018 rows) |
| (file detail level) | states/districts/schools.parquet split | MAPPED (detail_level implicit per domain convention) |
| System Code | district_code | MAPPED (zfill 3; hyphen-strip 2015; 799/782/783 repairs) |
| School Code | school_code | MAPPED (zfill 4) |
| Grade column / sheet grade | grade_level | MAPPED ('03'..'08') |
| System Name | — | CORRECTLY EXCLUDED (dimension; kept transiently only for the 2015 799 remap dispatch) |
| School Name, RESA, RESAName_RPT | — | CORRECTLY EXCLUDED (dimension attributes) |
| 17 metric sub-headers | 17 gold metric columns | MAPPED (full METRIC_NAME_MAP review — incl. the `% SGPTypical Growth` bronze typo alias) |
| Title banner / Lexile legend / footnotes / blank rows | — | CORRECTLY EXCLUDED (ledgered) |

Note: the structure doc's Gold Schema Classification proposed a fully melted `metric_name`/`value` shape; the transform emits wide metric columns instead. This is the correct deviation — it matches the project star-schema standard and the EOC sibling; no bronze metric is lost (all 17 land as columns).

## Value-Level Spot Checks

All traces quote bronze values read with the transform's own header convention (`header=[1,2], dtype=str`). **16/16 MATCH.**

Extreme rows first:

1. **num_tested global MAX** — `Spring_2018_EOG-State_Level.xlsx`, Grade 5 row, `('English Language Arts - EOG','Number Tested')` = `'137152'` → gold (2018, state, 05, ELA, eog) `num_tested=137152`. MATCH. Same row's ELA-EOC/Combined blocks are all `'--'` → correctly dropped as state placeholders (no gold eoc row exists).
2. **num_tested global MIN + 799 remap + suppression (4f)** — `Spring 2015 EOG System.zip:Gr6_System.xls`, row `System Code='799'`, name `GA ACADEMY FOR BLIND`: ELA `Number Tested='1'`, every other ELA cell `'--'` → gold (2015, **7991894**, 06, ELA) `num_tested=1`, all other metrics NULL. MATCH (remap + `'--'`→NULL both verified; 0 residual bare-799 rows in 2015).
3. **avg_scale_score global MAX** — `Spring-2024-EOG-School-Level-All-Grades.xlsx:School - Grade 8`, 660/0591, `('HS Physical Science','Mean Scale Score')` = `'654.7795275590552'` → gold 654.7795275590552, with `% Distinguished '85.03937007874016'` → 0.8503937007874016. MATCH to full float precision.
4. **avg_scale_score global MIN** — `Spring_2016_EOG-School_Level.zip:Gr7_School.xlsx`, 644/1100 ELA: `'372.2578125'`, `% Beginning '100'` → gold 372.2578125, pct_beginning_learner=1.0. MATCH.
5. **scale_score_std_dev global MIN** — `Spring_2022_EOG-System_Level-All Grades.xlsx:System - Grade 6`, system 799 (`STATE SCHOOLS`), Math: `Number Tested='24'`, `Mean='445.25'`, `Standard Deviation='14.010089532035547'` → gold (2022, 799, 06, math) all three exact. MATCH.
6. **num_received_sgp global MAX** — `Spring-2025-EOG-State-Level-All-Grades.xlsx:State - Grade 8`, `('SGP English Language Arts','Number Received SGP')='121298'`, `% SGP Low '34.500156639021256'` → gold 2025 state gr8 **ELA row** carries num_received_sgp=121298, pct_sgp_low_growth=0.34500156639021257. MATCH (SGP fold verified end-to-end).

Ordinary traces, one per era:

7. **2015 (Era 1, doc sample)** — Gr3_System.xls Appling 601 ELA: `'271'`, `'497.95571955719555'`, `'33.579335793357934'` … `'30.99630996309963'` → gold 271, 497.95571955719555, 0.33579335793357934 … 0.30996309963099633. MATCH (8/8 columns).
8. **2016 (Era 2)** — covered by trace 4 (school-level, title-case-name year). MATCH.
9. **2017 (Era 3, corrected doc)** — `Spring_2017_EOG-State_Level-All_Grades.xlsx` grade-8: supers include `Science - EOC/EOG/Combined` (doc correction confirmed); `('Science - EOC','Number Tested')='31935'`, `('Science - EOG','Number Tested')='96514'` → gold rows (2017, state, 08, science, eoc/eog) 31935 / 96514. MATCH. The Science-EOC block has **no Mean Scale Score column at all** (7 cols: Number Tested + 6 pcts) → gold avg_scale_score NULL is structurally correct.
10. **2018 (Era 4, RS fold)** — state grade-5 `('Reading Status*','% Below Grade Level')='30.37724568362109'` / `'% Grade Level or Above'='69.6227543163789'` → folded onto the gold ELA-eog row as 0.3037724568362109 / 0.696227543163789. MATCH. (The same masked read also surfaced the legend row `Grade='5'`, `'Lexile < 830L'` — confirming the legend filter is load-bearing: the grade-3-8 integer guard alone would NOT have caught it.)
11. **2021 (Era 5, merged-cell repair)** — `Spring 2021 EOG - System Level - Grade 8.xlsx` ELA block sub-headers are `['Number Tested', 'Number Tested.1', 'Mean Scale Score', …]`; `Number Tested.1` values `'91.570881'`, `'89.915966'`, `'100'` for systems 601/602/603 → gold pct_enrolled_tested 0.91570881 (601) and 1.0 (603), with num_tested 239/150 intact. MATCH — the repair preserved 206 districts' participation rates that the old doc advice would have dropped.
12. **2022 (Era 6, std dev + RS)** — `School - Grade 4` first row 601/0177: ELA `188 / 501.3670212765957 / 44.285152539703255 / 28.19148936170213…`; RS `% Below (Lexile < 740L) = 44.680851063829785` → gold all exact incl. lexile pair 0.44680851063829785 / 0.5531914893617021. MATCH.
13. **2023 (Era 7)** — `System - Grade 8` first row 601 Social Studies `254 / 513.5354330708661 / 50.68749411534486 / … / 41.732283464566926` → gold exact. MATCH.
14. **2024 (Era 8, bronze typo header)** — `State - Grade 5`, `('SGP Mathematics','% SGPTypical Growth')='30.842788778598848'` (missing-space variant confirmed in situ) → gold 2024 state gr5 mathematics pct_sgp_typical_growth=0.3084278877859885. MATCH — the typo alias works.
15. **Charter promotion (shared module)** — `Spring 2015 EOG School.zip:Gr3_School.xls` rows (782, 0110), (782, 0120)… ELA Number Tested `'44'`, `'698'`… → gold (2015, **7820110**, 0110, 03, ELA) num_tested=44. MATCH; 0 residual school-level rows under bare 782/783.
16. **RS fold-drop justification (global scan)** — across **all 111 sheets** carrying a Reading Status block, all **48,278** comparable rows (exactly the manifest's RS fold count): RS `Number Tested` vs parent ELA(-EOG) `Number Tested` → **0 mismatches**; 2021 RS vs ELA `Percent of Enrolled Students Tested` → **0 mismatches**. The docstring's "equal in current bronze" claim is fully verified — dropping the RS block's own counts loses zero information, and the eog fold parent is provably the right population.

## Validation Cross-Read

- `_validation.json`: **passed=true**, 20 pass / 0 fail / 1 warning (`null_rate_spikes`, 8 detail lines). `contract_parquet_schema`, `contract_quality_sql` (30 checks), `grain_uniqueness`, `foreign_keys` (240 district keys, 2,098 school keys all resolve), `geography_nulling` (×3 detail levels) all pass.
- Warning fully explained with bronze evidence: `avg_scale_score` 2018/2019 (39.5%/39.7% vs 15.2% median) — eoc/combined rows are 37% of those years and bronze EOC blocks ship **no Mean Scale Score column** (verified in trace 9; globally, all 38,317 non-eog gold rows across 2016-2021 have NULL avg_scale_score). Lexile 2015-2017 at 100% NULL — Reading Status first published 2018. Both legitimate.
- **schema_hash**: `a0a3f13273ab49ff497eff9e1c3b7fa5993ee879e21517306070f02a049263db` (briefed as identical to v1).
- **§4b masking audit**: N/A-clean — no `_null_*` helpers in transform.py, no `masked_values` manifest section, 0 masks. Consistent.
- **§15b coverage judgment**: 10 authored checks cover the partition sums (achievement levels, SGP bands), both cumulative-component identities, the Lexile complement, two co-null scopes (Lexile→ELA-only, SGP→ELA/Math gr4-8), two era pins (pct_enrolled=2021, EOC∈2016-2021) and std-dev sign. **Gap → Required Fix 1**: no era floors for Lexile (≥2018) / std-dev (≥2022) / SGP (≥2024) and no "EOC rows never carry scale scores" structural check, despite the contract notes documenting all four facts. All four verified 0-violation on current gold.
- **v1 parity** (recomputed independently):

```
MATCH — byte-identical with v1 gold
hash: 51aebad2c9820edc7b9435ecfcf90a32f07384acc3165aee3d05f3b941a3b680
```

- **ULP fix verification** (briefing item): the `df.rechunk()` after `_filter_footnote_rows` in `_unpivot_blocks` is present with a full explanatory comment. The claimed mechanism was reproduced empirically on polars 1.36.1: dividing a multi-row-chunk column by `100.0` equals reciprocal-multiply (`x * (1/100)`) on **100,000/100,000** values while true IEEE division differs on 14,023 of them; 1-row-chunk frames instead produce true IEEE division (274/2000 ULP diffs vs the multi-chunk result). The explanation is sound, and the byte-identical parity hash is the end-to-end proof that the rechunk pins the v1 float behavior.

## Cross-Era Consistency

- **Overlap years**: none — `files_processed` shows exactly one file per (year, detail_level) across all 30 files; dedup is defensive only (4e N/A). Era routing is structural (zip / 1-sheet / multi-sheet) and the manifest's shape-per-file table matches the doc's era layout exactly.
- **Continuity (3d)**: state EOG num_tested sums — 3.10M/3.08M (2015-16) → ~2.06M (2017-19, Science/SS narrowed to grades 5+8 per the doc Corrections) → 1.35M (2021, COVID participation; corroborated by pct_enrolled_tested) → ~1.91M (2022-25). avg_scale_score means 507-515 throughout; no >10x jumps, no revert-pattern level shifts.
- **NULL sweep (3c)**: 9 columns flagged; every one matches documented era availability exactly (std-dev pre-2022, Lexile pre-2018, pct_enrolled non-2021, SGP pre-2024 — all metric_stats non_null_count = 0 in the gated years, not merely ≥95% NULL). No column is NULL in every year. No rename-typo signature.
- **799 family**: 2015 (remapped) through 2019 itemize 7991893/94/95; 2021+ bronze itself switches to a single aggregated district `799` ("STATE SCHOOLS"). Gold is faithful to bronze in both eras; FK passes both ways. Analysts should note the 2021 discontinuity for state-school time series (see Notes).
- **Rollup feasibility (4d, aggregates COME FROM BRONZE)**: per (year, grade, subject, assessment_type) — district num_tested sums equal state values at ratio 1.00 in all 222 state cells (0 impossible, 0 below 0.95); school sums equal district values in all 45,267 district cells (0 cases of district < max school or district < visible school sum). 2024 state means lie within 0.022 scale-score points of the district-weighted means. This simultaneously proves the footnote/legend filter dropped no real entities (any lost school would break the exact sums).

## Transform Logic Risks

| Risk (Step 7 / 5b) | Severity | Verdict / details |
|---|---|---|
| Silent column drops | none | PASS — `_classify_columns` raises on unknown super-headers/metrics; only all-NaN columns and declared `_drop` identifiers are dropped |
| Era routing correctness | none | PASS — structural shape detection; 30/30 files routed as documented |
| Filter logic logged + justified | none | PASS — footnote/legend prefixes ledgered (183); placeholder drops ledgered (2,434 + 106); rollup sums prove zero real-entity loss |
| Normalization map completeness | none | PASS — 19/19 supers, 17/17 metrics incl. the `% SGPTYPICAL GROWTH` typo alias; raises on unmapped |
| `strict=False` casts | none | PASS — deliberate `'--'`→NULL after the NaN-block-absence drop; `no_suppression_markers` passes; trace 2 verifies semantics |
| Dedup keys + tie-break | none | N/A/PASS — collision guard (`assert_no_natural_key_collisions`) runs before defensive dedup; no overlap files |
| Year extraction | none | PASS — `Spring YYYY` filename = data year (doc §1); no row-level year strings (4c N/A); traces confirm |
| §4b masks | none | N/A — no masks |
| Sentinel year-attribution (Risk 3) | none | N/A — no year-bearing bronze strings |
| Asian/PI (Risk 1), mutual exclusivity (Risk 6) | none | N/A — no demographic axis |
| Rename typo (Risk 2), aggregation (Risk 4), dedup inversion (Risk 5), wrong mapping (Risk 7) | none | PASS — see Cross-Era Consistency / Manifest Verification |

## Required Fixes

### Fix 1: Author the four missing structural-fact quality checks (era floors + EOC-scale-score absence)
- **Severity**: MEDIUM
- **Issue**: Not a data inaccuracy — an enforcement gap (§15b: un-authored invariants are unenforced forever). The contract pins two era facts (`pct_enrolled_tested_only_in_2021`, `eoc_variants_only_2016_to_2021`) but leaves the three analogous era-availability facts and one block-structure fact unenforced, even though the contract notes document all of them: (a) Lexile metrics exist only from 2018; (b) `scale_score_std_dev` only from 2022; (c) SGP metrics only from 2024; (d) `avg_scale_score`/`scale_score_std_dev` are never published for `eoc` / `eog_and_eoc_combined` rows (bronze EOC blocks ship no Mean Scale Score / Standard Deviation columns). A future header-mapping regression that leaked values into these zones would today pass validation (the null-spike check only warns).
- **Evidence**: Executed on current gold — `lexile pre-2018 violations: 0`, `std_dev pre-2022 violations: 0`, `sgp pre-2024 violations: 0`, `non-eog rows with avg_scale_score non-null: 0` (of 38,317). All four checks pass now, so authoring them cannot change gold bytes — v1 parity stays MATCH.
- **Location**: `quality_checks=` list in `write_data_dictionary()` call, `main()` in transform.py (alongside `pct_enrolled_tested_only_in_2021`).
- **Suggested fix**: Add four consistency checks mirroring the existing era-pin pattern, e.g. `lexile_metrics_only_2018_onward` (`WHERE (pct_below_grade_level_lexile IS NOT NULL OR pct_grade_level_or_above_lexile IS NOT NULL) AND year < 2018`), `scale_score_std_dev_only_2022_onward`, `sgp_metrics_only_2024_onward`, and `no_scale_scores_on_eoc_rows` (`WHERE (avg_scale_score IS NOT NULL OR scale_score_std_dev IS NOT NULL) AND assessment_type <> 'eog'`), all `mustBe: 0`; optionally extend the avg_scale_score description with one clause noting EOC/Combined rows never carry scale scores. Re-run the transform to re-emit the contract and re-validate.

## NEEDS_JUDGMENT

(none — every suspicion raised during review was resolved with bronze evidence)

## Notes

- schema_hash `a0a3f13273ab49ff497eff9e1c3b7fa5993ee879e21517306070f02a049263db`; validation 20 pass / 0 fail / 1 warning (fully explained); 30 contract quality checks (20 derived + 10 authored); v1 parity MATCH `51aebad2…` recomputed independently in this review.
- Manifest "bronze" counts are post-read long rows; the 183 footnote/legend and 106 state-placeholder wide-row drops occur inside the readers before the count — the 289-row explicit-vs-implicit ledger delta reconciles exactly per year.
- State-school time-series caveat (data is bronze-faithful, no action required): districts 7991893/94/95 exist 2015-2019; from 2021 bronze publishes only the aggregated district `799` ("STATE SCHOOLS"). Cross-era state-school analysis must bridge that convention change.
- `assessment_type='eog'` for `physical_science` follows bronze labeling (no EOC suffix in the EOG release) and matches v1; the EOC-era quality check (`eoc_variants_only_2016_to_2021`) depends on this choice and passes.
- AWS profile broken per briefing — S3 conformance not attempted (local gold + contract only), as instructed.
