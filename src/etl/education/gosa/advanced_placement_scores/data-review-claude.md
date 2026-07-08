# Data Review: advanced_placement_ap_scores

**Date**: 2026-06-11
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

The transform is mechanically excellent — v1 parity **MATCH** (byte-identical gold), all 21/21 validation checks pass with 0 warnings, every transform-agent claim replayed exactly (the 644:xxxx exclusion proof, the five pinned summed pairs, the 0.0005 pct-recompute agreement, the suppression-by-era profile). However, the §4d feasibility screen uncovered a **provable source defect that gold currently serves**: the 2005 file's district rollups are misassigned for 8 districts (an alphabetical-adjacency shift plus a Jefferson County↔Jefferson City swap in GOSA's publication process), proven by exact three-metric donor matches against other districts' school sums and by 2004/2006 trend evidence. v1 shipped the same defective values; this review flags them for §4b masking, which will intentionally break parity.

## Manifest Verification

### Categorical mappings

| Column | Entries | Bronze seen | Unmapped | Status |
|---|---|---|---|---|
| subject | 42 | 42 | 0 | PASS |

Full map review — every entry verified semantically (bronze → gold | correct?):

| Bronze | Gold | Correct? |
|---|---|---|
| ALL Subjects | all_subjects | yes — cross-subject aggregate, also the constant for Eras A-C |
| African American Studies | african_american_studies | yes (new 2024) |
| Art History | art_history | yes |
| Art: Studio 2-D Design | art_studio_2d_design | yes |
| Art: Studio 3-D Design | art_studio_3d_design | yes |
| Art: Studio Drawing | art_studio_drawing | yes |
| Biology | biology | yes |
| Calculus A | calculus_a | yes — GOSA's literal label for AP Calculus AB; faithful recode, documented in contract |
| Calculus BC | calculus_bc | yes |
| Capstone | capstone | yes — GOSA label (AP Capstone/Seminar), faithful |
| Capstone Research | capstone_research | yes |
| Chemistry | chemistry | yes |
| Chinese Lang. & Culture | chinese_language_and_culture | yes |
| Computer Science A | computer_science_a | yes |
| Computer Science Principles | computer_science_principles | yes |
| Economics: Macro | economics_macro | yes |
| Economics: Micro | economics_micro | yes |
| Eng. Language & Comp | english_language_and_composition | yes |
| Eng. Literature & Comp | english_literature_and_composition | yes |
| Environmental Science | environmental_science | yes |
| European History | european_history | yes |
| French Language | french_language | yes |
| Geography: Human | human_geography | yes — reordered to the College Board course name |
| German Language | german_language | yes |
| Gov. & Pol. Comp | government_and_politics_comparative | yes |
| Gov. & Pol. U.S. | government_and_politics_us | yes |
| Italian Lang. & Culture | italian_language_and_culture | yes (new 2024, 3 rows) |
| Japanese Lang. & Culture | japanese_language_and_culture | yes |
| Latin: Vergil | latin_vergil | yes — discontinued legacy exam, faithful |
| Music Theory | music_theory | yes |
| Physics 1 | physics_1 | yes |
| Physics 2 | physics_2 | yes |
| Physics B | physics_b | yes — discontinued (2011-2014 era), explains 42 map entries vs 41 subjects in 2024 |
| Physics C: Elec & Magnetism | physics_c_electricity_and_magnetism | yes |
| Physics C: Mechanics | physics_c_mechanics | yes |
| Precalculus | precalculus | yes (new 2024) |
| Psychology | psychology | yes |
| Spanish Language | spanish_language | yes |
| Spanish Literature | spanish_literature | yes |
| Statistics | statistics | yes |
| U.S. History | us_history | yes — §16 canonical spelling |
| World History | world_history | yes |

- **2a Completeness**: bronze_values_seen (42) = the structure doc's 38 (2022) + 3 new 2024 subjects + Physics B (2011-2014). No documented value unencountered. PASS.
- **2b Correctness**: 100% of entries reviewed above — all semantically correct. The shared `apply_subject_normalization` backstop is a verified structural no-op: `SUBJECT_NORMALIZATION_MAP` keys (`united_states_history`, `economics`, 9th-grade-literature variants, `american_literature`) do not intersect the 42 gold values, and `us_history` is already canonical. PASS.
- **2c Contract cross-check**: contract `enum` (42 values) = `gold_values_produced` exactly. PASS.
- **2d Unmapped**: 0. PASS.
- **2e Asian/PI conflation**: **N/A** — no `demographic` column in any era and no wide race columns; structure doc Summary states "no demographic breakdown in any era".
- **2f Mutual exclusivity**: **N/A** — no demographic column.

### Row-count reconciliation

| Year | Bronze | Gold | Filtered | Reason |
|---|---|---|---|---|
| 2004 | 414 | 413 | 1 | missing_compound_id_delimiter (NUL-byte junk row, all metrics null — verified in bronze) |
| 2005 | 403 | 402 | 1 | malformed_compound_id (644:xxxx — verified excluded from GOSA's own 644:ALL rollup, see spot checks) |
| 2006 | 543 | 543 | 0 | |
| 2007 | 553 | 552 | 1 | placeholder_school_code (678:9999, all metrics 0; genuine 678:ALL preserved — verified) |
| 2008 | 492 | 491 | 1 | pinned_partial_count_rows_summed (761:0195 pair) |
| 2009 | 516 | 512 | 4 | pinned_partial_count_rows_summed (611, 667, 710 district pairs + 722:0176 pair) |
| 2010 | 524 | 524 | 0 | |
| 2011-2024 | 100,384 | 100,384 | 0 | tidy eras pass through 1:1 |

Totals: bronze 105,829 → gold 105,821, filtered 8 — matches `filtered_explicit_by_reason` exactly. Actual parquet rows = **105,821 = manifest `total_gold`**; per-year parquet counts match the manifest with zero mismatches. All 21 expected years present; per-year bronze counts match the structure doc tables exactly. PASS.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| SysSchoolID / SysSchoolid / Sysschoolid (A/B/C) | district_code + school_code (split on `:`) | MAPPED — sentinels→NULL, zfill(3)/zfill(4) verified (2008 `761:195`→`0195`) |
| SchoolNme / School Name / School or Distict  Name | — | CORRECTLY EXCLUDED (dimension attribute) |
| System Name (Era B) | — | CORRECTLY EXCLUDED (dimension attribute) |
| Number of Students Taking Tests (A-C) | num_tested | MAPPED |
| Number of Tests Taken (A-C) | num_tests_taken | MAPPED |
| Number of Test Scores 3 or Higher (A-C) | num_tests_3_or_higher | MAPPED |
| Percentage of Test Scores 3 or Higher (A-C) | — | CORRECTLY EXCLUDED — recomputed from counts; agreement ≤ 0.0005 verified in all 7 legacy files (see spot checks) |
| #RPT_NAME (E) | — | CORRECTLY EXCLUDED (constant `AP COUNTS`, asserted at read) |
| LONG_SCHOOL_YEAR (D-E) | year | MAPPED — ending year, cross-checked vs filename (raises on disagreement) |
| DETAIL_LVL_DESC (E) | detail_level → filename | CORRECTLY EXCLUDED from columns — drives Era E detail level with two raise-on-mismatch cross-checks |
| SCHOOL_DISTRCT_CD / INSTN_NUMBER (D-E) | district_code / school_code | MAPPED — DISTRICT_ALL / SCHOOL_ALL / ALL sentinels→NULL |
| SCHOOL_DSTRCT_NM / INSTN_NAME (D-E) | — | CORRECTLY EXCLUDED (dimension attributes) |
| TEST_CMPNT_TYP_NM (D-E) | subject | MAPPED (42-entry map above) |
| NUMBER_OF_STUDENTS_TESTED / NUMBER_TESTS_TAKEN / NOTESTS_3ORHIGHER (D) / NUMBER_TESTS_3_OR_HIGHER (E) | num_tested / num_tests_taken / num_tests_3_or_higher | MAPPED — era-conditional t3 column name handled |
| (derived) | pct_tests_3_or_higher | Traces to bronze counts; no fabrication |

No gold column lacks a bronze ancestry; no fact_key/fact_metric/fact_categorical column from the structure doc is missing.

## Value-Level Spot Checks

All verdicts below are MATCH unless stated. Bronze quoted first.

**Extreme rows (per-metric global max/min):**
- Global max, all three counts — 2024 state row, bronze line 8514: `"AP COUNTS","2023-24","STATE ALL SUBJECTS","ALL","All Systems","ALL","All Schools","ALL Subjects","98135","190946","131555"` → gold 2024 state all_subjects = 98135 / 190946 / 131555, pct 0.688964 = 131555/190946. MATCH.
- Global min, all three counts (0) — 2007 bronze `799:1893 | Atlanta Area School for the Deaf | 0 | 0 | 0 | (blank pct)` → gold 0/0/0 with pct NULL (denominator 0 → NULL rule). MATCH.
- 2008 per-year min num_tests_taken = 9 — bronze `652:176 | Elbert County High School | 10 | 9 | 2 | 22.22` and `652:ALL | 10 | 9 | 2` → gold carries 10/9/2 on both rows (the pinned num_tested>num_tests_taken preservation; single-school district so the defect appears at both levels). MATCH.
- pct max = 1.0 — 2005 bronze `729:205 | Americus Sumter County High North | 1 | 2 | 2 | 100` → gold 1/2/2/1.0; also 739 Towns County 2/2/2 at school and district. MATCH (verbatim source values; 1 student sitting 2 exams, both qualifying).
- pct min = 0.0 — 2005 bronze `644:1051 | Avondale High School | 101 | 144 | 0 | 0` → gold pct 0.0. MATCH.
- 2005 num_tested > num_tests_taken — bronze `611:204 | Rutland High School | 33 | 23 | 2 | 8.7` → gold 33/23/2/0.086957, preserved per §4b extreme-vs-impossible with pinned quality-check exclusion. MATCH.

**Ordinary entity traces (one per era, all columns):**
- Era A, 2007: bronze `601:103 | Appling County High School | 17 | 17 | 12 | 70.6` → gold (2007, 601, 0103, all_subjects) = 17/17/12/0.705882. MATCH.
- Era B, 2008: bronze `601:103 | 27 | 27 | 15 | 55.56` → gold 27/27/15/0.555556. MATCH.
- Era C, 2010: bronze `601:103 | 28 | 28 | 17 | 60.7` → gold 28/28/17/0.607143; also `793:273 Vidalia | 31 | 55 | 25 | 45.5` → 31/55/25/0.454545. MATCH.
- Era D, 2022: bronze line 1352 `"2021-22","633","Cobb County","0373","Sprayberry High School","World History","60","60","49"` → gold world_history 60/60/49/0.816667. MATCH.
- Era E, 2024: bronze line 6381 `"SCHOOL","708","Oconee County","0105","North Oconee High School","Precalculus","109","109","108"` → gold precalculus 109/109/108/0.990826. MATCH.
- Era D, 2011 state: bronze line 6230 `2010-11,DISTRICT_ALL,...,ALL Subjects,65506,108443,56691` → gold 2011 state = 65506/108443/56691, year correctly 2011 (= LONG_SCHOOL_YEAR ending year = filename year). MATCH.

**Summed-pair replays (all five pinned groups verified in bronze):**
- 2009 district 710 (Paulding): bronze pair `710:ALL | Paulding | 559/712/206` + `710:ALL | Paulding County | 80/80/39`; pair sums 639/792/245 equal the district's school-row sums **exactly on all three metrics** (zero suppressed school cells) → gold district 710 = 639/792/245. MATCH — summing, not dedup, is provably correct.
- 2009 district 611 (Bibb): pair 809+158 / 1168+216 / 117+32 = 967/1384/149; school sums 967 exact on num_tested, 1381/146 visible with 1 suppressed cell each on the other two → gold 967/1384/149. MATCH.
- 2009 district 667 (Gwinnett): pair = 8687/15981/9886; school sums 8687 exact, 15979/9885 + 1 suppressed cell → gold 8687/15981/9886. MATCH.
- 2009 school 722:0176 (Heritage): bronze rows 213/417/251 + 63/70/22 → gold 276/487/273; district 722's published 738/1231/543 equals its school sums **only** with both rows included. MATCH.
- 2008 school 761:0195: bronze rows 41/60/1 + 5/None/None → gold num_tested 46 (non-null sum), num_tests_taken/num_tests_3_or_higher **NULL** (null-poisoning: any suppressed component), pct NULL. District 761's 606 student total reconciles only when both rows' students are counted. MATCH — null-poisoning semantics verified.

**Suppression traces (one per marker type):**
- Era B `Too Few Students`: 2008 bronze 603:302 Bacon (3 / TFS / TFS / TFS) → gold 3/NULL/NULL/NULL. MATCH.
- Era D empty cells + TFS: 2011 bronze line 7 `2010-11,605,Baldwin County,189,Baldwin High School,Biology,TFS,,` (TFS in students, empty cells in tests/score) → gold (2011, 605, 0189, biology) all four metrics NULL. MATCH.
- Era D TFS (2020-2022): 2022 line 5459 East Paulding `Calculus A,TFS,TFS,TFS` → gold all NULL. MATCH.
- Era E TFS: 2024 line 6938 Conyers Middle `ALL Subjects,TFS,TFS,TFS` → gold all NULL. MATCH.

**Dropped-row verification:**
- 2004 junk: 1 row with NUL-byte `SysSchoolID` (`'\x00\x00…'`), all metrics null. Legitimate drop. MATCH.
- 2005 644:xxxx (2/2/2, no name): school-row sums excluding it = 2577/4076/1760 = the `644:ALL` rollup **exactly**; including it would not match. The drop loses nothing GOSA itself counted — the transform's corrected rationale (v1's was backwards) is verified. MATCH.
- 2007 678:9999 (no name, all metrics 0): dropped; genuine 678:0191 school row and 678 district row (112/147/80) both preserved in gold. MATCH.

**pct recompute agreement (legacy 0-100 column vs recomputed):** max |bronze_pct/100 − t3/tt| per year: 2004 0.000500, 2005 0.000500, 2006 0.000496, 2007 0.000500, 2008 0.000050, 2009 0.000050, 2010 0.000500 — the "within 0.0005" claim verified for every legacy file (source rounding only).

**§4d feasibility screen (aggregates come from bronze):** Across all 21 years and all three count metrics, district rows vs their school rows: **zero** impossibly-low violations anywhere except 2005 — where districts 681 and 722 publish rollups below their own max single school. The full 2005 audit (below, Required Fix 1) shows 8 of 128 district rollup rows are misassigned; the other 120 reconcile with their school sums **exactly** (2005 has zero suppression). State rows: never below any single district; small `num_tested` state-below-district-sum and district-below-school-sum gaps (median delta 2) are the expected distinct-count semantics (a student attributed to two schools/districts counts once at the higher level) — see NEEDS_JUDGMENT 1. The 2005 state-vs-district t3 drift (25267 vs 25288) is a symptom of the same 8-row misassignment (Rome City's 72 double-counted via 722's defective row, etc.), not an independent defect.

## Validation Cross-Read

- `_validation.json`: **passed = true, 21 pass / 0 fail / 0 warning** (fresh: validation ts 2026-06-12T03:36:54Z ≥ manifest 03:36:54Z ≥ transform mtime 03:36:45Z). `contract_parquet_schema` (63 files), `contract_quality_sql` (11 checks), `grain_uniqueness`, `foreign_keys` (189 district keys, 662 school keys all resolve) all pass.
- Contract `schema_hash`: `69683c25823daf09c26a7653cb94668725a9120a50d7cabf02ece667525d72eb`.
- **§4b masking audit**: no `_null_*` helpers in transform.py and no `masked_values` manifest section — consistent. The three num_tested>num_tests_taken rows are correctly handled as preserve+document (each value individually plausible, wrong side unknowable) with pinned quality-check exclusions. Note: Required Fix 1 will introduce the topic's first §4b mask.
- **§15b coverage judgment**: the five authored checks (t3 ≤ tt; num_tested ≤ tt with 3 pinned exclusions; pct reconciliation at 1e-9; pct co-null iff inputs; legacy years all_subjects-only) cover the topic's cross-column invariants well. One missing cross-ROW invariant surfaced by this review: *a district rollup can never be below its own largest school row* — true for all three metrics in all 21 years except the 8 defective 2005 rows. Folding this into Fix 1 as the enforcement guard.
- **v1 parity** (verbatim output): `MATCH — byte-identical with v1 gold`. Strong evidence the rebuild reproduces v1; note Fix 1, if applied, will intentionally diverge from v1 (v1 shipped the same 2005 defect).

## Cross-Era Consistency

- **Overlap years**: none — 21 files map 1:1 to 21 distinct years (manifest `files_processed`); dedup tie-break is a documented safety net only. Risk 5 N/A.
- **Era boundaries**: state-row continuity is smooth across all four boundaries (2007→2008: 43027→50073 students; 2010→2011: 63923→65506; 2022→2023: 78718→88656); no >1.5x level shift on any adjacent-year pair for any metric.
- **Cross-year NULL sweep**: no column ~100% NULL in any year; none 100% NULL everywhere. NULL-rate profile follows the documented suppression eras exactly (0-11% legacy; ~32-38% Era D except 0% for num_tested 2016-2018; ~48-51% for t3 in Era E, matching GOSA's independent-masking convention). Manifest null counts reproduce the structure doc's corrected suppression census (e.g., t3 2020/2021/2022 nulls = 2469/2776/2517 = TFS + 70/132/160 residual empties).
- **Scale consistency**: pct_tests_3_or_higher on 0-1 scale in all eras (recomputed everywhere — no era carries the legacy 0-100 column).

## Transform Logic Risks

| Risk | Severity | Verdict / details |
|---|---|---|
| Silent column drops | — | PASS — `_require_columns` hard-stops on any missing expected bronze column; all drops are dimension attributes or the recomputed pct |
| Era routing | — | PASS — five signatures keyed on distinct ID-column spellings / t3 column name; manifest era assignments match the structure doc file-for-file |
| Filter logic logged + justified | — | PASS — 3 drop classes + pinned summing, all `record_filtered`, all replayed in bronze (above) |
| Normalization map completeness | — | PASS — 42/42; shared backstop verified no-op |
| `strict=False` casts | — | PASS — metric casts only, on all-string reads; nulls suppression residue by design |
| Dedup keys + tie-break | — | PASS — pinned 5-group aggregation (raises on any other duplicate) → collision guard → dedup safety net (`sort_col="num_tests_taken"`); no overlap years exist |
| Year extraction | — | PASS — legacy from filename (no year column in bronze); tidy `LONG_SCHOOL_YEAR` ending year cross-checked vs filename, raises on disagreement; 2011 trace confirms |
| §5b masking audit | — | PASS — no masks, none recorded; consistent |
| 2005 district rollup misassignment | HIGH | FLAG — see Required Fix 1; carried verbatim from bronze, invisible to row counts/ranges/grain checks |

## Required Fixes

### Fix 1: 2005 district rollups misassigned for 8 districts — mask per §4b
- **Severity**: HIGH
- **Issue**: The 2005 bronze file publishes district `:ALL` rollup rows whose values provably belong to *other* districts, and gold serves them verbatim. Mechanism: GOSA's 2005 rollup generation shifted values onto the alphabetically-adjacent district (and swapped the two "Jefferson"-named districts). Gold's 2005 district rows for codes 681, 717, 720, 721, 722, 724, 758, 779 carry another district's (or an unknown donor's) AP totals — e.g., Richmond County (721) is served Rockdale's totals (482/842/457), and Randolph County (720), whose true AP program had ~1-3 students (2004: 3; 2006: 1), is served Richmond's 489/772/318.
- **Evidence**: 2005 has zero suppression and 120 of 128 district rollups equal their school-row sums **exactly**; the 8 exceptions decode as: `681 Jefferson County: published (16,21,13), own school sums (28,43,19), donor = 779`; `779 Jefferson City: published (28,43,19), own sums (16,21,13), donor = 681` (exact swap); `717 Putnam: published (11,12,5) = 719 Rabun's school sums` (Rabun's only row `719:177 | Rabun County High School | 11 | 12 | 5`); `720 Randolph: published (489,772,318) = 721 Richmond's school sums`; `721 Richmond: published (482,842,457) = 722 Rockdale's school sums`; `722 Rockdale: published (70,97,72) = 785 Rome City's school sums` (and `785:ALL` itself correctly publishes 70/97/72 — Rome's totals are served twice); `724 Screven: published (167,202,111) vs own sums (67,104,51)`; `758 Wilkinson: published (37,38,14) vs own sums (10,11,0)`. Trend confirmation for every affected district — published 2005 values break the 2004→2006 series while own school sums fit it: Rockdale 833 (2004) → 97 published / 842 own (2005) → 950 (2006); Screven 80 → 202 published / 104 own → 127; Wilkinson 10 students → 37 published / 10 own → 9; Jefferson County 45 tests → 21 published / 43 own → 62. Gold 2005 district rows verified to carry all 8 defective triples verbatim (e.g., gold `(2005, '721', NULL)` = 482/842/457).
- **Location**: `main()` in `src/etl/education/gosa/advanced_placement_ap_scores/transform.py` (new `_null_*` helper at the §4b seam — after geography nulling, before validate/manifest/export); `_emit_contract_and_readme()` for documentation + the new quality check.
- **Suggested fix**: Per §4b (impossible → NULL + document; these rows publish values that cannot be the named district's totals): add a pinned `_null_2005_misassigned_district_rollups()` helper that NULLs all four metrics on the 8 `(year=2005, detail_level='district')` rows for district_codes {681, 717, 720, 721, 722, 724, 758, 779} (rows preserved; pct goes NULL with its inputs, keeping the co-null check green); record via `manifest.record_masked(column, count=8, reason, years=[2005])` per metric; document the misassignment in the contract column descriptions/notes (including the donor mapping so analysts can recover e.g. Richmond's true 2005 totals from its school rows); add an authored quality check `district_not_below_own_max_school` (district row ≥ max same-year/subject school row per count metric, with no exclusions once the mask lands — currently violated only by the masked rows) so the defect class is enforced forever. School-level 2005 rows are unaffected and stay. Alternative for the proven 681↔779 swap only: a pinned repair re-crossing the two published triples — defensible since both true values are published in the file, but masking all 8 uniformly is the established §4b convention; recommend masking. Re-run transform + validation; expect intentional v1 parity break and drift-detection trip.

## NEEDS_JUDGMENT

### Judgment Call 1: document distinct-count semantics of `num_tested` across geography levels
- **Severity if confirmed**: LOW
- **Suspicion**: Analysts summing school rows to rebuild district/state `num_tested` will get slightly *higher* numbers than the published rollups (945 district cases, median delta 2, p95 36; 88 state cases; e.g., Gwinnett 2015 all_subjects: district 14,942 vs school sum 15,259). The contract warns that summing per-subject `num_tested` double-counts students, but not that summing per-school rows can too.
- **Evidence available**: Gold screen across all years: the gaps are one-directional (rollup ≤ visible school sum), small, concentrated in large districts, and present for per-subject rows as well — consistent with students attributed to multiple schools (mid-year movers) being deduplicated in GOSA/College Board's higher-level distinct counts. Test-count metrics (`num_tests_taken`, `num_tests_3_or_higher`) show zero such gaps outside the 2005 defect, confirming this is distinct-count semantics, not data loss.
- **Why uncertain**: The attribution mechanism is GOSA/College Board internal; cannot be proven from bronze. No values are wrong — both levels are served verbatim as published.
- **Location**: `num_tested` column description in `_emit_contract_and_readme()`.
- **If confirmed, suggested fix**: extend the `num_tested` contract description by one sentence: school-row sums may slightly exceed district/state rollups because the rollup counts each student once even when school-level attribution counts them at more than one school. No data change.

## Notes

- schema_hash: `69683c25823daf09c26a7653cb94668725a9120a50d7cabf02ece667525d72eb`; validation 21 pass / 0 fail / 0 warning; read_loss events: 0; masked_values: none (would change under Fix 1).
- v1 parity: `MATCH — byte-identical with v1 gold` — the 2005 defect therefore also shipped in v1 and was not caught by the v1 review cycle.
- Minor composition drift, tolerated per §4d (no action): 2004 DeKalb 644 district tt = 3,984 vs school sums 3,977 (delta 7); 2006 644 delta 1 and 660 delta 3. Orders of magnitude below the 2005 misassignments and consistent with a school absent from the file.
- The 2005 state row (29,114 / 45,937 / 25,267) is verbatim bronze; the 21-test excess of district t3 sums over the state is explained by the Fix 1 misassignment (Rome City double-counted) and resolves once the defective rows are masked.
- All transform-agent claims scrutinized and confirmed: 8 ledgered drops (incl. the corrected 644:xxxx EXCLUDED-from-rollup rationale), 5 summed pairs (710's 639/792/245 exact), pct recomputed ≤0.0005 agreement, 3 preserved num_tested>num_tests_taken rows with pinned exclusions, era-by-era suppression census, 42-label subject map, no demographic column in any era.
