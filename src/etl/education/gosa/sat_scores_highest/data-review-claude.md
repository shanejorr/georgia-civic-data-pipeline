# Data Review: sat_scores_highest

**Date**: 2026-06-10
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

The transform is accurate: all 11 value-level spot checks (6 extreme-row + 5 ordinary per-era) MATCH bronze exactly, all 27 categorical map entries are semantically correct, the strict aggregate feasibility screen finds 0 violations across 18,069 full-coverage district groups, and the 2024 modal-pair vote provably repairs the three Math-Section-on-Combined mix-up rows. **v1 parity: MATCH — byte-identical with v1 gold.** Three fixes are required, none of which touch parquet data: a missing `combined = reading + mathematics + writing` quality check (empirically holds within 1 point on all 3,473 complete groups), a wrong contract claim that `race_unknown` spans 2004-2007 (gold rows exist in 2004 only), and an undocumented 2004 within-file duplicate block (25 entities × 2 identical rows; 72 gold-grain rows correctly but silently deduped).

## Manifest Verification

### Categorical maps

| Column | Entries | Bronze seen | Unmapped | Status |
|---|---|---|---|---|
| demographic | 10 | 10 | 0 | PASS — all semantically correct |
| test_component | 17 | 17 | 0 | PASS — all semantically correct |

**demographic — full map review (every entry):**

| Bronze | Gold | Correct? |
|---|---|---|
| All Students | all | YES |
| Asian | asian_pacific_islander | YES — §5b combined-bucket convention (see 2e below) |
| Black | black | YES |
| Female | female | YES |
| Hispanic | hispanic | YES |
| Male | male | YES |
| American Indian | native_american | YES |
| O | other | YES — bronze doc defines suffix O = "Other" |
| R | race_unknown | YES — bronze doc defines suffix R = "No Response" |
| White | white | YES |

**test_component — full map review (every entry):**

| Bronze | Gold | Correct? |
|---|---|---|
| High Total (Era 1-3 prefix) | verbal_math | YES — empirically verified: bronze `High Total0 == High Verbal0 + High Math0` (the contract quality check passes over all 2004-2010 gold; trace: 2004 644:5052 `1291 = 641 + 650`); old-SAT V+M scale 400-1600, distinct from the V+M+W `combined` |
| High Verbal (prefix) | reading | YES — old-SAT Verbal section == the section GOSA later labels "Reading"; state continuity across the fold is smooth (2010: 492 → 2011: 486) |
| High Math (prefix) | mathematics | YES — state continuity 2010: 495 → 2011: 490 |
| High Writing (prefix) | writing | YES — Era 3 only (2008-2010), matches bronze layout |
| Combined | combined | YES — V+M+W 600-2400 total (2011 state 1338 ≈ 486+490+361) |
| Mathematics | mathematics | YES |
| Reading | reading | YES |
| Writing | writing | YES |
| Combined Test Score | combined_test_score | YES — redesigned 400-1600 |
| Math Section Score - New | math_section_score | YES |
| Reading Test  Score - New | reading_test_score | YES — literal double-space bronze key preserved |
| WritLang Test  Score - New | writlang_test_score | YES — literal double-space bronze key preserved |
| Evidence Based Reading and Writing - New | evidence_based_reading_and_writing | YES — 2016-2019 only, enforced by quality check |
| Essay Reading Score - New | essay_reading_score | YES |
| Essay Analysis Score - New | essay_analysis_score | YES |
| Essay Writing Score - New | essay_writing_score | YES |
| Essay Total | essay_total | YES |

- **2c contract cross-check**: `gold_values_produced` == contract `enum` for both columns (10 and 14 values). PASS.
- **2d unmapped**: 0 for both. PASS.

### 2e Asian/Pacific Islander (Risk 1)

- `grep -iE 'pacific...' bronze-data-structure.md` → **NO_NHPI_LABEL_IN_BRONZE** (0 hits).
- Metrics are averages, so the structural test governs: no era of this source publishes a Pacific Islander bucket; sibling GOSA topic `act_scores` labels the same concept explicitly — verified in `data/bronze/education/gosa/act_scores/bronze-data-structure.md` line 73: `| Composite Asian-American/Pacific Islander | Composite score for Asian-American / Pacific Islander subgroup. |`
- Positive math evidence on `num_tested` (count metric), state level, single component, every demographic year:
  ```
  2004: total=46828.0 race_sum=46828.0 ratio=1.0000
  2005: total=48317.0 race_sum=48317.0 ratio=1.0000
  2006: total=47733.0 race_sum=47733.0 ratio=1.0000
  2007: total=50139.0 race_sum=50139.0 ratio=1.0000
  2008: total=51591.0 race_sum=51591.0 ratio=1.0000
  2009: total=47281.0 race_sum=47281.0 ratio=1.0000
  2010: total=52632.0 race_sum=52632.0 ratio=1.0000
  ```
  The 6-bucket race scheme (incl. the combined bucket) partitions the state total exactly — no separate PI population exists outside it. **PASS** — bare "Asian" correctly remapped to `asian_pacific_islander` via the topic-local `_raw_demographic_label` override.

### 2f Mutual exclusivity (Risk 6)

`gold_values_produced` contains `asian_pacific_islander` and neither `asian` nor `pacific_islander`. **PASS — single convention.**

### Row-count reconciliation

| Year(s) | Bronze | Gold | Reconciliation |
|---|---|---|---|
| 2004 | 2,247 | 13,089 | 2,245 good records (2 corrupted fragments dropped, recorded) × 30 cells = 67,350; − 54,189 empty cells (elided, recorded) = 13,161; − 72 within-file duplicate rows (deduped, see Fix 3) = **13,089 exact** |
| 2005 / 2006 | 536 / 542 | 14,472 / 14,634 | × 30 cells; exactly 3 R-demographic cells/row elided (R columns verified 100% blank in bronze) → 536×27 / 542×27 **exact** |
| 2007 | 543 | 14,661 | × 30 cells; 3 R cells/row elided (R columns are the literal string "NULL") → 543×27 **exact** |
| 2008-2010 | 562/567/582 | 20,196/20,376/20,916 | 1 sub-header row dropped each (recorded); (561/566/581) × 36 cells (9 demographics × 4 components) **exact, zero elisions** — verified bronze `Number Taken*` columns are 100% numeric (the structure doc's claim of TFS in Era 3 count columns is wrong) |
| 2011-2015 | 1,716-1,756 | 2,456-2,500 | schools 1:1 + districts + 4 state rows; expansion ~1.43 consistent |
| 2016 | 5,339 (2 files) | 7,690 | old+new vocabularies disjoint, no key collision |
| 2017-2024 | 1,866-3,820 | 2,702-5,491 | expansion 1.43-1.46 consistent |

- **3b**: gold parquet total = **174,263** == manifest `total_gold`. PASS.
- All 21 expected years present (2004-2024, no gaps).

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| SysSchoolID / SysSchoolId (Eras 1-3) | district_code + school_code (+ detail_level) | MAPPED — `ALL:ALL`→state, `{d}:ALL`→district; both header spellings handled |
| SCHOOL_DISTRCT_CD (Era 4) / SCHOOL_DSTRCT_CD (Era 5) | district_code | MAPPED — breaking rename handled per era |
| INSTN_NUMBER | school_code | MAPPED — zfill(4) verified ('386' → '0386') |
| LONG_SCHOOL_YEAR / filename year | year | MAPPED — ending year; filename cross-check raises on mismatch |
| SUBGRP_DESC / demographic suffixes & tokens | demographic | MAPPED |
| TEST_CMPNT_TYP_CD / High* prefixes | test_component | MAPPED |
| INSTN/DSTRCT/STATE_NUM_TESTED_CNT, Number Taken* | num_tested | MAPPED — per detail level |
| INSTN/DSTRCT/STATE_AVG_SCORE_VAL, High* | avg_score | MAPPED — per detail level |
| School Name / SchoolNme / *_NM / INSTN_NAME | — | CORRECTLY EXCLUDED (dimension attributes) |
| Recent * (Eras 1-3) | — | CORRECTLY EXCLUDED (sibling topic sat_scores_recent's measure) |
| NATIONAL_NUM_TESTED_CNT / NATIONAL_AVG_SCORE_VAL | — | CORRECTLY EXCLUDED (national out of scope; documented in notes) |
| #ASSMT_CD / HIGHEST_RECENT_IND | — | CORRECTLY EXCLUDED (constants, hard-stop validated — non-'Highest' rows would raise) |
| Era 3 row-1 sub-header | — | CORRECTLY EXCLUDED (dropped + recorded) |

No gold column lacks a bronze source (no fabrication).

## Value-Level Spot Checks

Extreme rows first (global max/min of each metric, plus per-year extremes), then one ordinary entity per era. **All 11 traces MATCH.**

| # | Trace | Bronze (file, row, value) | Gold | Verdict |
|---|---|---|---|---|
| 1 | avg_score global MAX | 2011.csv, 667/1019 Gwinnett School of Mathematics, Combined: `INSTN_AVG_SCORE_VAL=1795`, `CNT=194` | 2011, 667, 1019, combined = (194, 1795) | MATCH |
| 2 | avg_score global MIN | 2017.csv, 611/386 Southwest High, Essay Analysis: `2`, `138` | 2017, 611, 0386, essay_analysis_score = (138, 2.0) | MATCH (essay floor) |
| 3 | num_tested global MAX | 2012.csv state context Reading: `STATE_NUM_TESTED_CNT=86895`, `AVG=488` | 2012 state reading = (86895, 488) | MATCH |
| 4 | num_tested global MIN | 2005.csv(XLS), 601:ALL, `Number Taken Asian=0.0`, all High Asian cells blank | 2005, 601, district, asian_pacific_islander = (0.0, NULL) ×3 components | MATCH (real zero kept) |
| 5 | 2024 fractional min | 2024.csv, 703/0201 Montgomery County High, Combined: `9.3`/`955.3` (school and district) | (9.3, 955.3) at school and district | MATCH (Float64 §16 exception) |
| 6 | 2004 max / 2005 min | 2004.csv 644:5052 Chamblee `High Total Asian=1291`,`Number Taken Asian=14`; 2005 761:289 Crim Evening `High Math All Students=230.0`, count `1.0` | 2004 644/5052 apl verbal_math=(14,1291); 2005 761/0289 mathematics=(1,230) | MATCH |
| 7 | Era 1 ordinary: 2004 633:192 Harrison High | `High Total/Verbal/Math All Students = 1074/539/535`, `Number Taken=414`; Female `1060`/`190` | all=(414, 1074/539/535), female verbal_math=(190,1060) | MATCH |
| 8 | Era 2 ordinary: 2007 792:273 Valdosta | `High Total0/Verbal0/Math0 = 983/498/485`, `Number Taken0=137`; `High TotalA='NULL'`, `Number TakenA=17.0` | all=(137, 983/498/485); asian_pacific_islander = (17, NULL)×3 | MATCH — literal-'NULL' subgroup correctly count-only |
| 9 | Era 3 ordinary: 2009 739:204 Towns County | `High Total0/Verbal0/Math0/Writing0 = 965/486/479/484`, `Number Taken0=34.0`, `Number TakenB=0.0` | all=(34, 965/486/479/484); black=(0.0, NULL)×4 | MATCH |
| 10 | Era 4 ordinary: 2015 738:192 Toombs County, Reading | school `97`/`469`; district `97`/`469`; state `85353`/`490` | school (97,469); district (97,469); state (85353,490) | MATCH at all three detail levels |
| 11 | Era 5 ordinary: 2024 645:0103 Dodge County, Math Section | school `32`/`466.3`; district `32`/`466.3` | (32, 466.3) at school and district | MATCH |

- **4c sentinel year-attribution (Risk 3)**: Eras 4-5 derive `year` from `LONG_SCHOOL_YEAR` (ending year) and `transform_file` raises if it disagrees with the filename year. Verified: 2024 file carries `LONG_SCHOOL_YEAR='2023-24'` and every gold row from it is year=2024. PASS.
- **4d aggregate feasibility screen (Risk 4)** — aggregates COME FROM BRONZE (Era 1-3 published `:ALL`/`ALL:ALL` rows; Era 4-5 context columns), never re-derived:
  - district `num_tested` < max school `num_tested`: **0 violations**.
  - state count < max district count and state count < visible district sum: **0 violations**.
  - Strict full-coverage district avg bound (all school counts AND avgs non-null, district count == school sum, tolerance ±1): **0 violations of 18,069 groups**. (A looser screen flagged 166 rows, all explained by schools with suppressed scores but visible counts legitimately pulling the district average outside the visible-school range — e.g. 2004 607 black mathematics: district (17, 415) vs Apalachee (10, 419) + Winder-Barrow (7, score blank).)
  - Era 4/5 district count < visible school sum: 28 cases, every one off by exactly 1 student (e.g. 2011 616: 391 vs 392) or 0.1 (2024 657: 87.3 vs 87.4) — bronze rounding, immaterial.
  - 2004 district 739: district row (52, 931, …) is byte-identical to Towns County High School 739:204 and omits Mountain Education Center 739:194 (11 students) → visible school sum 63 > district count 52 across 15 demographic×component rows. Bronze-published (quoted above); see Judgment Call 2.
  - 2024 modal-pair repair verified against bronze: Combined Test Score state pair frequencies = `(32979, 1043.6) ×435` vs `(37143, 505.4) ×3`, and `(37143, 505.4)` is exactly the 2024 Math Section state pair — confirming the mix-up diagnosis. Gold state combined = (32979, 1043.6) ✓; districts 675/705/736 take the school-evidence-backed pairs (809.7, 987.8)/(41.7, 997.4)/(63.7, 1019.7), not the Math-scale 470.0/469.4/473.6 values ✓; the three mix-up school rows survive as (NULL, NULL) ✓; 3 out-voted rows recorded via `record_reclassified` would be expected — counts appear under the modal-pair logging (school metrics NULL so school rows unaffected).
- **4e dedup tie-break (Risk 5)**: No year is covered by two eras (the two 2016 files have disjoint component vocabularies) → cross-file N/A. Within-file: the 2004 CSV contains 25 entities each appearing exactly twice with **identical** values (758:ALL Wilkinson, 759:* Worth County block, 761:* Atlanta block — e.g. `759:176 Worth County High (937, 469, 468, 77)` twice). `assert_no_natural_key_collisions` passed (it raises on metric-divergent duplicates, tolerates true repeats), proving the 72 deduped gold-grain rows were exact copies; gold keeps exactly one row each with the right values (759/0176 = (77, 937/469/468); 758 district = (47, 824/407/418)). Data correct; documentation gap → Fix 3.
- **4f suppression semantics**: Era 2 literal `"NULL"` (792:273 `High TotalA`) → count-only row ✓; Era 3 `"Too Few Students"` (2009 622:190 `High Total0='Too Few Students'`, `Number Taken0=3.0`) → gold (3.0, NULL)×4 ✓; Era 4 `TFS` (2015 604/105 Combined, `INSTN_NUM_TESTED_CNT='TFS'`, score null) → gold row kept as (NULL, NULL) ✓; Era 5 `TFS` (2024 705/0108) → (NULL, NULL) ✓. Era 5 `N/A` in NATIONAL_AVG_SCORE_VAL is moot (national never emitted). All MATCH.

## Validation Cross-Read

- `_validation.json` (2026-06-10T22:09:08Z): **20 pass / 0 fail / 1 warning**; `contract_parquet_schema` (63 files), `contract_quality_sql` (12 checks), `grain_uniqueness`, `foreign_keys` (193 districts / 578 schools / 10 demographics all resolve), geography nulling ×3 — all pass.
- The single warning (`null_rate_spikes`, 9 spikes) is triaged below in Cross-Era Consistency — all 9 have verified bronze causes.
- Contract `schema_hash`: `54310a68e15a2192a2cc29d30867e593e87667bc641b53c7e54127633abfa3e7`.
- **§4b masking audit**: one mask helper (`_null_invalid_sat_scores`). Manifest `masked_values` records all 20: writing=13 (2009-2015), reading=3 (2009-2010), verbal_math=2, mathematics=2 — exactly matching the docstring inventory (2009 Heritage 4 + S. Atlanta 1; 2010 Rockdale 4 + Elberta 1; 2011-2015 writing 10). Bronze verified: 2009 722:176 published (2017, 1022, 995, 976) with `Number Taken0=190` → gold all four NULL, count 190 kept ✓; the 3 district writing rollups (2013 749=166, 2014 7991894=184, 2015 7991894=189) → gold NULL with counts kept ✓. Handling documented in the contract's avg_score description; the `avg_score_within_component_scale` quality check keeps the mask enforceable. PASS.
- **§15b coverage judgment**: 12 authored/derived checks cover component scales, the V+M identity, era-coverage, demographic-era constraints, count-implies-score, state completeness, and count integrality. The pivot rewrite of `verbal_math_equals_reading_plus_mathematics` (conditional aggregation, GROUP BY year/district_code/school_code/demographic with MAX(CASE…)) is **sound**: grain uniqueness guarantees at most one row per component within each group so MAX selects the single value; SQL GROUP BY treats NULL geography keys as equal, so district (school_code NULL) and state (both NULL) rows form their own groups exactly as IS NOT DISTINCT FROM joins would; the year ≤ 2010 + component filter restricts to the eras where the invariant holds; the NULL guard reproduces the 3-way inner-join complete-case semantics. One **gap**: no analogous check for `combined = reading + mathematics + writing` (2011-2016), which empirically holds within 1 point on all 3,473 complete groups → Fix 1.
- **v1 parity** (verbatim): `MATCH — byte-identical with v1 gold`

## Cross-Era Consistency

- **Overlap years**: none across files (2016's two files have disjoint vocabularies — verified no key collision; grain uniqueness passes).
- **Era-boundary score continuity** (state, all): reading 2010→2011 = 492→486; mathematics = 495→490; verbal_math ends 2010 (987), combined begins 2011 (1338, different 600-2400 scale, distinct name) — smooth, the High-Verbal→reading / High-Math→mathematics folds are confirmed at the level of state means.
- **writing 2010→2011** = 480→361: the documented HIGHEST-basis deflation, covered in contract limitations.
- **num_tested 2010→2011** = 52,632→84,799 (+61%, sustained through 2016): bronze-verified (2011 state pairs quoted above) — a count-basis change at the wide→tidy era boundary, currently undocumented → Judgment Call 1.
- **Null-rate spike triage (the validator's 9 warnings)**: `avg_score` 2005-2010 at 88.9-89.4% — structural: 2005/2006 carry scores only where data exists for 9-of-10 demographics in 3 components; 2007 demographic High columns are the literal "NULL" string (count-only rows); 2008-2010 publish subgroup counts with no subgroup High columns at all (36 cells/row, scores possible on only 4) — all verified in bronze headers/values. `num_tested` 2021-2023 at 28.4-32.0% vs median 5.8% — COVID-era test-optional collapse pushes more schools under GOSA's TFS threshold; bronze 2024 shows 201 district + 350 school TFS markers (~11%/~19%) vs 8/131 in 2015; suppression rows are kept as NULL-metric observations by design, so the gold null rate mirrors bronze suppression. All 9 spikes explained; no action.
- **Essay components 2023-2024**: state counts collapse 3,589 (2022) → 194 (2023) → 33 (2024) — bronze-verified (`2023: Essay Total (194, 13.7)`); College Board discontinued the SAT Essay in 2021, so the tail is real.
- **Cross-year NULL sweep (Risk 2)**: no column is ≥95% NULL in a subset of years (and none in all years). PASS.

## Transform Logic Risks

| Risk | Severity | Details |
|---|---|---|
| Silent column drops | PASS | `_require_columns` hard-stops on every expected era column incl. per-demographic count columns; Era 1 raises if any (prefix × token) score column is unresolved |
| Era routing | PASS | Structural signatures (not year-based); XLS magic bytes route the 2005/2006 `.csv`-named binaries; both 2016 files detect as era_4; unmatched era raises |
| Filter logic | PASS | All drops recorded: 2 corrupted fragments, 3 sub-header rows, 59,052 empty cells; nothing else filtered |
| Normalization map completeness | PASS | All 17 bronze test-component values + 10 demographic labels seen and mapped; `replace_strict(default=None)` with a coverage check via manifest unmapped=0 |
| `strict=False` casts | PASS | Confined to `_to_float_expr` (Utf8 → strip → strip trailing "." → Float64), which is also what nulls TFS/"NULL"/"Too Few Students"; trailing-dot 2024 national counts verified handled |
| Dedup keys + tie-break | PASS (doc gap) | Keys = full natural key per detail level; collision guard before dedup proves only identical duplicates were dropped (the 72-row 2004 block); docstring wrongly says none expected → Fix 3 |
| Year extraction | PASS | Filename year for Eras 1-3; LONG_SCHOOL_YEAR ending year with filename cross-check raise for Eras 4-5 |
| §4b masks (5b) | PASS | All 20 recorded, documented, range-guarded (see Validation Cross-Read) |

## Required Fixes

### Fix 1: Author the missing `combined = reading + mathematics + writing` quality check (2011-2016)
- **Severity**: MEDIUM
- **Issue**: §15b — the contract enforces the Era 1-3 identity (`verbal_math = reading + mathematics`) but not the exactly analogous Era 4 old-SAT identity for `combined`, leaving a real cross-column invariant unenforced forever.
- **Evidence**: Empirical test over gold 2011-2016, complete-case pivot on (year, district_code, school_code): n=3,473 groups, max |combined − reading − mathematics − writing| = 1.0, zero groups exceed 1.0. State 2011: 1338 vs 486+490+361=1337 (diff 1).
- **Location**: `_quality_checks()` in transform.py
- **Suggested fix**: Add a check mirroring `verbal_math_equals_reading_plus_mathematics` — same conditional-aggregation pivot (per §15b no-self-join), `WHERE year BETWEEN 2011 AND 2016 AND test_component IN ('combined','reading','mathematics','writing')`, NULL-guarded, `ABS(combined - reading - mathematics - writing) > 1.0`, mustBe 0. Re-run the transform to re-emit the contract (parquet unchanged; v1 parity preserved).

### Fix 2: Correct the contract claim that race_unknown exists 2004-2007
- **Severity**: LOW
- **Issue**: The contract's `demographic` description and the "No Response" note state `race_unknown ('No Response') exists 2004-2007 only`, but gold contains race_unknown rows **only in 2004** (1,515 rows; zero in 2005-2007).
- **Evidence**: Gold `filter(demographic=='race_unknown').group_by('year')` → `{2004: 1515}` only. Bronze: 2005/2006 `High TotalR`/`High VerbalR`/`High MathR`/`Number TakenR` are 100% empty-string (verified via xlrd; all values `''`); 2007's R columns including `Number TakenR` are 100% the literal string `"NULL"` (bronze-data-structure.md's 32-column list) — so every 2005-2007 R cell is elided (exactly 3 cells/row: 1608=536×3, 1626=542×3, 1629=543×3 recorded elisions).
- **Location**: `_emit_contract_and_readme()` in transform.py — the `demographic` column description and the demographics note.
- **Suggested fix**: Change the prose to "race_unknown ('No Response') carries data in 2004 only (the source's R columns exist through 2007 but are blank in 2005-2006 and literal-'NULL' in 2007)". Re-run the transform to re-emit (parquet unchanged).

### Fix 3: Document the 2004 within-file duplicate block (72 silently deduped rows)
- **Severity**: LOW
- **Issue**: The module docstring asserts duplicates are "none expected after the 2004 fragment drop", but the 2004 CSV contains 25 entities each published twice with byte-identical values; 72 gold-grain rows were deduplicated with no docstring mention and no manifest record (2004 `filtered: 0`), an audit-trail gap. The data itself is correct.
- **Evidence**: `csv.reader` over the 2004 file: duplicate SysSchoolIDs = 758:ALL, 759:{176,177,193,196,3051,ALL}, 761:{100,101,…,180} (25 keys, each ×2, values identical — e.g. `759:176 Worth County High School (937, 469, 468, 77)` twice). Cell math: 2,245 rows × 30 − 54,189 elided = 13,161 generated vs 13,089 gold = 72 deduped. `assert_no_natural_key_collisions` passed → duplicates provably metric-identical.
- **Location**: transform.py module docstring (dedup section); optionally `main()` to record the dedup delta in the manifest.
- **Suggested fix**: Update the docstring to document the 2004 duplicate block (Wilkinson/Worth/Atlanta rows each printed twice, proven identical, deduped). Optionally record the 72 dropped rows via `manifest.record_filtered(2004, 72, "identical_duplicate_rows")` or equivalent so the manifest reconciles exactly. Must not change parquet bytes (v1 parity is MATCH); recording-only changes are safe.

## NEEDS_JUDGMENT

### Judgment Call 1: num_tested count-basis discontinuity at the 2010→2011 era boundary
- **Severity if confirmed**: LOW (documentation only — values match bronze)
- **Suspicion**: State-level All-Students `num_tested` jumps 52,632 (2010) → 84,799 (2011), +61%, and stays at the new level through 2016. SAT participation did not rise 61% in one year; the wide-era "Number Taken" and the tidy-era "NUM_TESTED" count different populations (likely per-year administrations vs cohort-cumulative takers).
- **Evidence available**: Gold state series (mathematics): 2008-2010 = 51,591 / 47,281 / 52,632; 2011-2015 = 84,799 / 86,883 / 86,622 / 83,391 / 85,362. Bronze 2011 state pairs verified verbatim (Mathematics 84799/490). Score averages are continuous across the same boundary (495→490), so only the count basis shifts.
- **Why uncertain**: GOSA does not document either era's counting basis; the discontinuity is real but its cause is inferred, and whether it merits a contract caveat is an editorial call.
- **Location**: contract `limitations` / `notes` (emitted from `_emit_contract_and_readme()`).
- **If confirmed, suggested fix**: Add a limitations sentence: "num_tested is not comparable across the 2010/2011 boundary — the 2011+ source counts a substantially larger population (state count rises ~61%) under a different counting basis."

### Judgment Call 2: 2004 district 739 rollup excludes Mountain Education Center
- **Severity if confirmed**: LOW (bronze-published; single district-year)
- **Suspicion**: The 2004 published district rollup for Towns County (739:ALL = 52 tested, High Total 931) is byte-identical to Towns County High School (739:204) and excludes Mountain Education Center (739:194, 11 tested, High Total 1028), so the district count (52) is less than the visible school sum (63) across 15 demographic×component rows — the only such case in Eras 1-3.
- **Evidence available**: Bronze quoted: `739:194 Mountain Education Center (11, 1028, 495)`, `739:204 Towns County High (52, 931, 458)`, `739:ALL Towns County (52, 931, 458)`. Mountain Education Center is a multi-county alternative program (later re-coded as state charter 7820108), so GOSA may have intentionally excluded it from the county rollup.
- **Why uncertain**: Cannot prove whether GOSA's exclusion was intentional (multi-district program) or an aggregation error; either way the transform faithfully preserves the official published aggregate, and repairing it would violate the "never re-aggregate" rule.
- **Location**: n/a (data faithful to bronze).
- **If confirmed, suggested fix**: None to the data. At most, a notes sentence that pre-2011 district rollups occasionally exclude multi-district alternative programs.

## Notes

- schema_hash: `54310a68e15a2192a2cc29d30867e593e87667bc641b53c7e54127633abfa3e7`; validation 20 pass / 0 fail / 1 warning (all 9 spike details triaged above); v1 parity MATCH (no explanation needed).
- All three Required Fixes are contract-prose/docstring/manifest-recording changes — none alters gold parquet, so byte-parity with v1 survives the fix loop if applied as suggested.
- The structure doc's Era 3 suppression table ("Number Taken{0,A,…,W} often contains Too Few Students") is contradicted by bronze: all Era 3 Number Taken columns are 100% numeric (verified 2009 via xlrd) — gold's zero count-nulls in 2008-2010 are correct.
- `num_tested` Float64 §16 exception verified end-to-end: fractional counts only on `combined_test_score` (quality check passes; 2024 trace 9.3 preserved).
- The modal-pair vote (`_modal_pair_rollup`) and the quality-check pivot rewrite were both reviewed as sound; the rewrite is semantically identical to the prior self-join formulation and is not a defect.
