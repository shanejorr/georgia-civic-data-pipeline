# Data Review: sat_scores_recent

**Date**: 2026-06-10
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Gold is **byte-identical with the v1 approved baseline (v1 parity: MATCH)** and every value-level trace across all six eras matched bronze exactly, including all 16 §4b masks, the zero-sentinel repair, TFS/Too-Few-Students suppression, and the 2024 modal-pair vote (verified: the rejected state pair (37140, 505.4) is the math_section_score state aggregate pasted onto Combined rows). Two fixes are required: a MEDIUM contract-coverage gap (four composite-sum invariants hold with zero violations across 30,791 checked groups but are unenforced) and a LOW documentation inaccuracy (the 2004 duplicate block is 25 re-published rows, not just Wilkinson County). Three judgment items are escalated, led by a systematic ~95-point depression of the 2011–2016 `writing` column versus College Board GA means (internally consistent in bronze, so faithfully carried — but it deserves a contract caveat).

## Manifest Verification

| Column | Map entries | Bronze values seen | Unmapped | Status |
| --- | --- | --- | --- | --- |
| demographic | 10 | 10 (all in map) | 0 | PASS |
| test_component | 19 | 18 (`Verbal` never seen — see below) | 0 | PASS |

**demographic — full map review (every entry):**

| Bronze | Gold | Correct? |
| --- | --- | --- |
| All Students | all | YES |
| Asian | asian_pacific_islander | YES — §5b combined bucket (see 2e below) |
| Black | black | YES |
| Female | female | YES |
| Hispanic | hispanic | YES |
| Male | male | YES |
| American Indian | native_american | YES |
| O | other | YES — structure doc glosses `O` as "Other" |
| R | race_unknown | YES — no bronze long-form label exists; the race partition sums exactly to the all-students total in 2004 only when `race_unknown` is included (46,828 = race buckets incl. R), supporting the no-response reading. Carries real data only in 2004 (1,515 rows, 942 non-NULL scores, counts up to 7,483) — the structure doc's claim that R is "always blank/NULL" is wrong for 2004; the transform handled reality correctly |
| White | white | YES |

**test_component — full map review (every entry):**

| Bronze | Gold | Correct? |
| --- | --- | --- |
| Recent Total (V+M, suffixed) | verbal_math | YES — 200–1600 V+M composite, verified 2005 601:2050 475+458=933 |
| Recent Verbal | reading | YES — pre-2016 Critical Reading section, unified with 2012+ `Reading` |
| Recent Math | mathematics | YES |
| Recent Writing | writing | YES (Era 3 only) |
| Recent Total (V+M+W, standalone) | verbal_math_writing | YES — verified 2010 601:103: 916+437=1353 |
| Combined | combined | YES — Era 4 V+M+W on 600–2400 (state 2013: 483+482+381=1346≈1345; the bronze doc's "400–1600" claim is wrong; the contract's 600–2400 is correct) |
| Mathematics | mathematics | YES |
| Verbal | reading | YES but **never encountered**: bronze 2011 actually publishes `Reading` (verified directly), so the structure doc's "2011 uses Verbal" is a doc error, not a routing bug. Entry is harmless (same canonical) |
| Reading | reading | YES |
| Writing | writing | YES |
| Combined Test Score | combined_test_score | YES — 400–1600 Math+EBRW (state 2016: 530+550=1080 exact) |
| Math Section Score - New | math_section_score | YES |
| Evidence Based Reading and Writing - New | evidence_based_reading_and_writing | YES (2016–2019 only) |
| Reading Test  Score - New | reading_test_score | YES — double-space preserved |
| WritLang Test  Score - New | writlang_test_score | YES — double-space preserved |
| Essay Reading Score - New | essay_reading_score | YES |
| Essay Analysis Score - New | essay_analysis_score | YES |
| Essay Writing Score - New | essay_writing_score | YES |
| Essay Total | essay_total | YES |

- **2c contract cross-check**: contract `enum`s (10 demographic, 15 test_component) equal `gold_values_produced` exactly. PASS.
- **2d unmapped**: 0 for both columns. PASS.

### 2e Asian/Pacific Islander (Risk 1)

`grep -icE 'pacific[ _-]?islander|native[ _-]?hawaiian|nhpi' bronze-data-structure.md` → `NO_NHPI_LABEL_IN_BRONZE`. The transform already maps bare `Asian` → `asian_pacific_islander` via topic-local `ASIAN_PI_REMAP`. Positive math-test evidence (run on `num_tested`, which IS summable here):

```
2010 state mathematics: total=52632.0 race_sum=52632.0 ratio=1.0000
2004 state mathematics: total=46828.0 race_sum=46828.0 ratio=1.0000
```

The race partition is complete with the combined bucket and no separate Pacific Islander label exists in any era; sibling GOSA transforms (`act_scores`, `sat_scores_highest`, etc.) use the same combined-label convention. **PASS — convention correctly applied.**

### 2f Mutual exclusivity (Risk 6)

Gold publishes `asian_pacific_islander` only — no `asian`/`pacific_islander` split keys anywhere. **PASS — single convention.**

## Row Counts

| Year | Bronze | Gold | Reconciliation |
| --- | --- | --- | --- |
| 2004 | 2,245 | 13,089 | 2,245×30 cells − 54,189 empty − 72 deduped (25-row re-appended duplicate block, see Fix 2) = 13,089 ✓ |
| 2005 | 536 | 14,472 | exactly ×27 (9 demographics × 3 components; R blank → 536×3 filtered) ✓ |
| 2006 | 542 | 14,634 | exactly ×27 ✓ |
| 2007 | 543 | 14,661 | exactly ×27 (R columns literal "NULL" → 543×3 filtered) ✓ |
| 2008 | 562 | 20,757 | (562−1 legend)×37 cells exact ✓ |
| 2009 | 567 | 20,942 | (567−1)×37 exact ✓ |
| 2010 | 582 | 21,497 | (582−1)×37 exact ✓ |
| 2011 | 1,724 | 2,460 | 1,724 schools + 732 districts (183×4) + 4 states ✓ |
| 2012–2015 | 1,716–1,756 | 2,456–2,500 | same pattern, ~1.43x ✓ |
| 2016 | 5,339 (both files) | 7,690 | 5,339 schools + 2,338 districts + 13 states (4 old + 9 new components) ✓ |
| 2017–2024 | 1,866–3,820 | 2,702–5,491 | ~1.43–1.46x, schools 1:1 + materialized aggregates ✓ |

Actual parquet total = **175,971 = manifest `total_gold`** ✓. `total_filtered_explicit` 59,055 = 59,052 empty wide cells + 3 Era-3 legend rows, all recorded. All 21 expected years present (both 2016 files kept, disjoint vocabularies, no key collisions).

## Column Coverage

| Bronze column(s) | Gold | Status |
| --- | --- | --- |
| SysSchoolID / SysSchoolId | district_code + school_code + detail_level | MAPPED (split on `:`, `ALL` sentinels → NULL, case-insensitive for 2005's `All:All`) |
| School Name / SchoolNme | — | CORRECTLY EXCLUDED (dimension attribute) |
| Recent {Total,Verbal,Math,Writing}{suffix} | avg_score × test_component | MAPPED (melt) |
| Recent Total (Era 3 standalone) | avg_score @ verbal_math_writing | MAPPED |
| High * (all eras) | — | CORRECTLY EXCLUDED (sibling topic sat_scores_highest; 2004–2010 files byte-identical between the two topics) |
| Number Taken{suffix} | num_tested | MAPPED |
| LONG_SCHOOL_YEAR | year | MAPPED (ending year, filename cross-check) |
| SCHOOL_DISTRCT_CD / SCHOOL_DSTRCT_CD | district_code | MAPPED (both spellings, zfill(3)) |
| SCHOOL_DSTRCT_NM, INSTN_NAME | — | CORRECTLY EXCLUDED (dimensions) |
| SUBGRP_DESC | demographic | MAPPED (validated constant 'All Students') |
| TEST_CMPNT_TYP_CD | test_component | MAPPED |
| INSTN_NUM_TESTED_CNT / INSTN_AVG_SCORE_VAL | num_tested / avg_score (school rows) | MAPPED |
| DSTRCT_* / STATE_* | district/state fact rows | MAPPED — deliberate, documented deviation from the structure doc's `not_in_gold` suggestion: official aggregates are materialized as fact rows (modal-pair vote), keeping the 2004–2024 gold shape uniform and never re-aggregating suppressed school rows. Sound. |
| NATIONAL_NUM_TESTED_CNT / NATIONAL_AVG_SCORE_VAL | — | CORRECTLY EXCLUDED (out of scope; would collide with state rows) |
| #ASSMT_CD, HIGHEST_RECENT_IND | — | CORRECTLY EXCLUDED (validated constants `SAT`/`Recent`, hard-stop on deviation) |

No gold column lacks a bronze ancestor (no fabrication). `_require_columns` guards every era's expected set.

## Value-Level Spot Checks

Extreme rows first; all bronze values quoted from the files directly.

| # | Trace | Bronze (quoted) | Gold | Verdict |
| --- | --- | --- | --- | --- |
| 1 | num_tested global MAX: 2012 state | 2012 csv, Combined rows, single distinct pair `STATE_NUM_TESTED_CNT='85153'`, `STATE_AVG_SCORE_VAL='1352'` | (NULL,NULL geo, all, combined) = (85153.0, 1352.0) | MATCH |
| 2 | avg_score global MAX: 2009 761:308 | 2009 xls "South Atlanta Leadership and Economic Empowerment School": `Recent Total='2352'`, `Recent Total0='1561'`, `Verbal0='784'`, `Math0='777'`, `Writing0='791'`, `Number Taken0='115'` | all five components carried verbatim (2352/1561/784/777/791, n=115) | MATCH (mechanically; plausibility → Judgment 2) |
| 3 | avg_score global MIN: 2016 603:0302 essay_analysis | bronze 2016_new essay analysis rows, n=11 avg 2 | (11.0, 2.0) | MATCH |
| 4 | num_tested global MIN: zero-sentinel | 2005 xls 601:2050/601:ALL: `Recent Total Asian='0'`, `Number Taken Asian='0'` | (0.0, NULL) — count kept, impossible 0 score nulled | MATCH |
| 5 | §4b: 2009 Carroll Co district | 2009 xls `622:ALL`: `Recent Total='2751'` but `Total0='945'`,`Writing0='453'` (true V+M+W=1398 → 2751 corrupt) | verbal_math_writing (307.0, NULL); other 4 components preserved (945/472/473/453) | MATCH — masked exactly |
| 6 | §4b: 2010 Rockdale 722:3052 | `Recent Total='3114'`, `Total0='2133'`, `Verbal0='1039'`, `Math0='1094'`, `Writing0='981'`, n=219 | all 5 avg_score NULL, num_tested 219 preserved | MATCH |
| 7 | §4b: 2010 Elberta 676:3050 | `Verbal0='819'` (>800), `Math0='699'`, `Writing0='769'`, `Total0='1518'`, `Recent Total='2287'`, n=10 | reading NULL; mathematics 699, verbal_math 1518, verbal_math_writing 2287, writing 769 preserved | MATCH — documented policy applied precisely |
| 8 | §4b: nine sub-200 writing 2011–2015 | bronze quoted: 2011 648:212 `'118'`; 2012 625:117 `'92'`, 660:119 `'184'`; 2013 749:205 `'187'` (school+district); 2014 631:215 `'174'`; 2015 667:1814 `'144'`, 7991894:1894 `'189'` (school+district) = 9 values | all → avg_score NULL, counts preserved (spot-verified 5 of 9 incl. both district variants) | MATCH |
| 9 | Era 1 ordinary: 2005 601:2050 Appling Co High | `'933'/'475'/'458'`, n=`'79'`; White `'967'`, n=`'56'` | verbal_math 933, reading 475, mathematics 458 (n=79); white 967/494/473 (n=56) | MATCH |
| 10 | Era 1 state 2005 | `All:All`: `'989'/'494'/'495'`, n=`'48317'`; Asian `'1070'/'504'/'566'`, n=`'2325'` | state all (48317, 989/494/495); asian_pacific_islander (2325, 1070/504/566) | MATCH |
| 11 | Era 2 ordinary: 2007 704:1050 Morgan Co High | `Recent Total0='938'` n=`'115'`; `TotalA='1200'` n=`'2'`; `TotalB='752'` n=`'18'`; `TotalR='NULL'` | verbal_math: all (115, 938), asian_pacific_islander (2, 1200), black (18, 752); no race_unknown rows in 2007 | MATCH |
| 12 | Era 3 ordinary: 2010 601:103 Appling | `Recent Total='1353'`, `Total0='916'`, `Verbal0='459'`, `Math0='457'`, `Writing0='437'`, n=`'77'`; `Number TakenA='0'` | all five components exact; asian_pacific_islander (0, NULL) | MATCH |
| 13 | Era 4 ordinary: 2013 611:303 Hutchings | Reading row: INSTN `('26','429')`, DSTRCT `('1056','433')` (single distinct district pair), STATE `('84853','483')` | school 0303 (26, 429); district 611 (1056, 433); state (84853, 483) | MATCH |
| 14 | Era 5 TFS: 2020 658:0219 Forsyth Virtual | WritLang row: INSTN count+avg = TFS (reader → NULL) | (NULL, NULL) row preserved at school grain | MATCH |
| 15 | Era 5 ordinary: 2020 658:5050 Forsyth Central | Essay Writing `('71','6')` | (71.0, 6.0) | MATCH |
| 16 | Era 5 TFS: 2020 730:0190 Combined | TFS/TFS | (NULL, NULL) | MATCH |
| 17 | Era 6: 2024 648:0100 Chapel Hill essay_reading | INSTN TFS/TFS; `NATIONAL_AVG='4'` (dropped) | (NULL, NULL); no national row in gold | MATCH |
| 18 | Era 6 fractional count: 2024 Gwinnett 667 | Combined Test Score: `DSTRCT=('4159.3','1103.1')` | district 667 (4159.3, 1103.1) — Float64 §16 exception carried unrounded | MATCH |
| 19 | Era 6 state: 2023 Essay Total | single distinct STATE pair `('194','13.7')` | state (194.0, 13.7) | MATCH |
| 20 | Modal vote (2024 anomaly) | 3 bronze rows carried alternate state pair (37140, 505.4) on Combined rows | state combined_test_score = (32976.0, 1043.6) official; (37140, 505.4) is the legitimate **math_section_score** state row — the anomalous bronze rows pasted math aggregates onto Combined rows; vote rejected them | MATCH |
| 21 | Dedup winner (4e): 2004 758:ALL Wilkinson | duplicate identical rows: `'812'`(all), `'752'`(Black), `'789'`(Female), `'849'`(White) | single district row set: verbal_math 812/752/789/849... | MATCH |
| 22 | 4c year attribution | 2011 file `LONG_SCHOOL_YEAR='2010-11'` (single value) | year=2011; transform raises if ending year ≠ filename year | MATCH |

## Validation Cross-Read

- `_validation.json`: **20 pass / 0 fail / 1 warning** (2026-06-10T22:09:05Z, fresh). `contract_parquet_schema`, `contract_quality_sql` (11/11), `grain_uniqueness`, `foreign_keys` (193 districts, 578 school pairs, 10 demographics) all pass.
- **schema_hash**: `675005c92aa47a74bca9b4271362bb5d6105914ed5d308994fe51dd31d69efba`
- **Warning triage (null_rate_spikes, 6 spikes)** — all bronze-real, none a transform defect:
  - `num_tested` 2021 28.4% / 2022 32.0% / 2023 29.6% (median 4.9%): raw TFS tokens per bronze line rise from 0.18 (2019) to 0.83 / 0.95 / 0.97 (2021–2023), then fall to 0.59 (2024, gold 19.1%) — COVID/test-optional participation collapse pushing schools under GOSA's n<10 threshold. Era 5 2016–2018 instead published sub-10 counts (n=1–9) with blank scores (427 such rows in 2017), which is why num_tested nulls are 0 there.
  - `avg_score` 2008 43.5% / 2009 44.6% / 2010 44.5% (median 16.0%): Era 3 carries 9,136 / 9,420 / 9,664 raw "Too Few Students" score cells per year while counts stay numeric — suppressed-score rows survive the both-NULL drop (unlike Era 1 blanks), structurally raising the era's score null rate; plus zero-sentinel (count=0) rows.
- **§4b masking audit**: one mask family, `_null_invalid_sat_scores` → `masked_values` records (avg_score, 16, outside_sat_component_scale, years 2009–2015) — counts verified against bronze (7 over-ceiling + 9 sub-200 writing = 16). Documented in the contract `avg_score` description and `null_meaning`; range guard enforceable via `avg_score_within_component_scale`. The zero-sentinel (score NULLed when count=0) and TFS→NULL are suppression-decoding at read/melt time, not §4b masks — documented in contract notes and `null_meaning`; `avg_score==0` rows in gold: 0. PASS.
- **§15b coverage judgment**: the 7 authored checks are good (scale, score⇒count≥1, demographic window, two component-year windows, essay reconciliation, state-unsuppressed) — but four equally obvious composite-sum invariants are unenforced (→ Fix 1). The rewritten `essay_total_reconciles_with_dimensions` pivot is **sound**: grain uniqueness guarantees ≤1 row per (year, geo, demographic, component) so each `MAX(CASE…)` selects at most one value; `GROUP BY` treats NULL geography keys as equal (the intended IS-NOT-DISTINCT-FROM semantics, keeping state/district/school levels separate); the outer 4-way non-NULL filter restricts to complete groups. Semantically identical to the abandoned self-join, without the join explosion. Not a defect.
- **v1 parity (verbatim)**:

```
MATCH — byte-identical with v1 gold
```

## Cross-Era Consistency

- **Overlap years**: none across eras (the two 2016 files share the year but have disjoint component vocabularies — both kept by design; 2016 is the only year with both families: `combined` (50161, 1395) and `combined_test_score` (27919, 1080) coexist). 4e dedup is within-file only (2004 block, trace 21).
- **Era-boundary continuity (state all-students)**: `reading` 484→483 and `mathematics` 487→486 across 2010→2011 — clean. `num_tested` jumps 52,632→83,053 at 2010→2011 (×1.58, sustained through 2015, not the reverting cumulative signature): a bronze population-definition change (wide-era "Number Taken" vs long-era `STATE_NUM_TESTED_CNT`), carried as published. 2016 new-format counts are low (27,919) because the redesigned SAT debuted March 2016 mid-cohort; 2017 recovers to 61,246. Essay counts collapse 3,589→194→33 (2022→2023→2024): College Board discontinued the SAT essay in 2021 — bronze-real (state pair (194, 13.7) quoted in trace 19).
- **`writing` 471→378 at 2010→2011**: NOT continuous — see Judgment 1.
- **Cross-year NULL sweep (3c)**: no column ≥95% NULL in any year. Risk 2 ruled out.
- **Feasibility screens (4d)**: state vs district rollups — 0 count violations, 0 state-mean-bounds violations across all years/components. District vs school rows — 0 "district < max school" violations; 15 "district < visible school sum" rows, all (2004, district 739): bronze `739:ALL` Towns County is a verbatim copy of Towns County High (`'915'/'466'/'450'`, n=`'52'`), excluding Mountain Education Center (739:194, n=11) — bronze-published, gold faithful (→ Judgment 3).

## Transform Logic Risks

| Risk | Severity | Details |
| --- | --- | --- |
| Silent column drops | PASS | `_require_columns` hard-stops per era on any missing expected column |
| Era routing | PASS | Most-specific-first signatures; era_4 (superset) checked before era_5; manifest confirms 2016_old→era_4, 2016_new→era_5 |
| Filter logic | PASS | 59,055 explicit filters (empty cells, 3 legend rows) all recorded; malformed-ID guard never fired |
| Normalization completeness | PASS | All 18 observed bronze component values + 10 demographic labels mapped; the one unused entry (`Verbal`) traced to a structure-doc error (2011 publishes `Reading` — verified in bronze) and maps to the same canonical anyway |
| `strict=False` casts | PASS | String round-trip then non-strict Float64; suppression tokens pre-nulled by the shared reader; exact row reconciliation shows no silent numeric loss |
| Dedup keys + tie-break | PASS | Collision guard before dedup; only identical within-file twins deduped (2004 block); winner equals bronze |
| Year extraction | PASS | Eras 1–3 filename; Eras 4–6 `LONG_SCHOOL_YEAR` with filename cross-check that raises on disagreement |
| §4b mask hygiene (5b) | PASS | Recorded, documented, range-guarded (see Validation Cross-Read) |

## Required Fixes

### Fix 1: Author composite-sum reconciliation quality checks
- **Severity**: MEDIUM
- **Issue**: Four obvious cross-component invariants — directly analogous to the authored `essay_total_reconciles_with_dimensions` — are unenforced, leaving future regressions (bronze garbling, mask asymmetries, component swaps) invisible to CI.
- **Evidence**: Executed against current gold, all four hold with zero violations: `verbal_math = reading+mathematics` (23,442 groups, 0 violations @ tol 1.5); `verbal_math_writing = reading+mathematics+writing` (1,632, 0 @ 2.0); `combined = reading+mathematics+writing` (3,474, 0 @ 2.0); `combined_test_score = math_section_score+evidence_based_reading_and_writing` (2,243 groups 2016–2019, 0 @ 1.5).
- **Location**: `_emit_contract_and_readme()` `quality_checks=` list in `src/etl/education/gosa/sat_scores_recent/transform.py`
- **Suggested fix**: Add four `mustBe: 0` checks using the same conditional-aggregation pivot pattern as `essay_total_reconciles_with_dimensions` (GROUP BY year/district_code/school_code/demographic, `MAX(CASE WHEN test_component=… THEN avg_score END)`, outer non-NULL filter, tolerances as measured above). Re-run the transform to re-emit contract + re-validate.

### Fix 2: 2004 duplicate-block documentation understates the dedup
- **Severity**: LOW
- **Issue**: The transform docstring and the contract note claim only "the 758:ALL Wilkinson County district row" is re-published in the 2004 file. The file actually re-appends a 25-row block (districts 758/759/761 — including populated rows for Worth County High School `759:176` and Worth County district `759:ALL`), and dedup removed 72 melted rows (2,245×30 − 54,189 filtered = 13,161 → 13,089 gold), all verified identical twins.
- **Evidence**: `Counter(SysSchoolID)` on bronze 2004 → 25 ids ×2 (758:ALL, 759:176, 759:177, 759:193, 759:196, 759:3051, 759:ALL, 761:100…761:1664 etc.); duplicate rows byte-identical (e.g. `759:176 Worth County High School | 927 | 808 | 911 | 953` twice). Gold data itself is correct.
- **Location**: module docstring "Dedup tie-break" bullet and the 2004 `notes=` entry in `transform.py`
- **Suggested fix**: Reword both to describe the 25-row re-appended trailing block (72 melted rows removed as identical twins), keeping Wilkinson as the named example. Re-run the transform (contract note changes only; gold parquet bytes unchanged — but verify parity hash is preserved).

## NEEDS_JUDGMENT

### Judgment Call 1: 2011–2016 `writing` column is systematically depressed ~95 points
- **Severity if confirmed**: MEDIUM
- **Suspicion**: The Era 4 bronze "Writing" averages (and therefore the `combined` composite that sums them) are not clean 200–800 section means — they appear to include zero/missing essay scores in the averaging base, making 2011–2016 `writing` non-comparable with 2008–2010 `writing` despite sharing one `test_component` value.
- **Evidence available**: State writing falls 471 (2010) → 378 (2011), then 381/381/387/389/423 through 2016, while College Board GA writing means were ~473–488 those years; reading/mathematics are continuous across the same boundary (484→483, 487→486). The depression is internally consistent (2011 state 378.0 vs school-weighted mean 378.1 over 99.7% coverage — so NOT a transform artifact), and the same bronze column contains nine sub-200 values (min 92) that are impossible for a true section mean — already §4b-masked. `combined` inherits the depression exactly (2013: 483+482+381=1346≈1345 vs College Board GA V+M+W ≈1452).
- **Why uncertain**: Cannot prove the mechanism from within the dataset; in-range values (378–389) are not individually impossible, so §4b does not apply. GOSA published these numbers at every level.
- **Location**: bronze `*_AVG_SCORE_VAL` on Writing rows 2011–2016; contract `test_component` description currently implies one continuous 200–800 `writing` series 2008–2016.
- **If confirmed, suggested fix**: Add a contract caveat to the `test_component` description and `limitations` ("2011–2016 writing — and the combined composite — run systematically below College Board section means; treat the 2010→2011 writing series as discontinuous"). Do NOT mask in-range values. Splitting into a separate component value is the stronger option but breaks v1 parity and the published vocabulary — Shane's call.

### Judgment Call 2: 2009 South Atlanta (761:0308) row is implausible but in-range — and is the undocumented global maximum
- **Severity if confirmed**: LOW
- **Suspicion**: Sections 784/777/791 (V+M 1561, V+M+W 2352 — the gold-wide avg_score maximum) for n=115 at South Atlanta Leadership and Economic Empowerment School would be the highest school averages in US history; the row is almost certainly a GOSA publication error (e.g. +300 per section).
- **Evidence available**: Bronze 2009 xls quoted: `Recent Total='2352'`, `Total0='1561'`, `Verbal0='784'`, `Math0='777'`, `Writing0='791'`, `Number Taken0='115'`. Internally consistent (784+777=1561; 1561+791=2352), every value within its scale, so the §4b mask correctly does not fire. The school has no 2008 or 2010 SAT rows to compare against.
- **Why uncertain**: No provable scale violation and no neighboring-year baseline; masking would require a feasibility argument the standards don't currently codify.
- **Location**: gold 2009 school rows 761/0308 (all 5 components); contract `avg_score` description documents Elberta's 2287 but not this larger extreme.
- **If confirmed, suggested fix**: Minimum: document the row alongside Elberta in the contract `avg_score` description as a preserved suspect extreme (it, not 2287, is the global max). If Shane prefers accuracy over preservation: extend the §4b mask to this pinned row (all 5 components) with a feasibility rationale.

### Judgment Call 3: 2004 Towns County (739) district rollup excludes one school
- **Severity if confirmed**: LOW
- **Suspicion**: The bronze 2004 district rollup for 739 is a verbatim copy of Towns County High School and omits Mountain Education Center's 11 test-takers, so 15 (demographic × component) district aggregates are smaller than the visible school sums.
- **Evidence available**: Bronze quoted — `739:204 Towns County High School | 915 | 466 | 450 | n=52` and `739:ALL Towns County | 915 | 466 | 450 | n=52` identical, while `739:194 Mountain Education Center | 1020 | 525 | 495 | n=11`. Feasibility screen: this is the only district/year in 21 years where district count < school sum.
- **Why uncertain**: Possibly intentional — Mountain Education Center is a multi-district alternative program GOSA may exclude from county rollups; overwriting an official published aggregate would violate the never-re-aggregate principle.
- **Location**: gold 2004 district 739 rows; bronze sat_scores_recent_2004.csv.
- **If confirmed, suggested fix**: Recommend keep-as-published (no transform change); optionally add one limitations sentence ("district rollups are as published and may exclude shared alternative-education centers").

## Notes

- schema_hash: `675005c92aa47a74bca9b4271362bb5d6105914ed5d308994fe51dd31d69efba`; validation 20 pass / 0 fail / 1 warning (triaged above); v1 parity MATCH.
- Read loss: 1 acknowledged event (2004, 2 truncated trailing fragments, re-appends of intact rows — note verified against the file tail).
- `num_tested` Float64 is the documented §16 exception (fractional Era 5–6 combined counts, e.g. Gwinnett 2024 district 4159.3 traced verbatim) — do not "fix" to Int64.
- The bronze structure doc contains three errors the transform correctly did not inherit: (1) Era 4 `Combined` is V+M+W 600–2400, not "400–1600"; (2) 2011 `TEST_CMPNT_TYP_CD` uses `Reading`, not `Verbal`; (3) 2004 `*R` columns are not "always blank" — they carry real race-unknown data (1,515 gold rows).
- Both Required Fixes are contract/documentation artifacts; neither changes gold parquet values. Per the project's drift policy, metadata-note changes do not require re-approval, but Fix 1 adds quality checks (contract change → re-emit + re-validate).
