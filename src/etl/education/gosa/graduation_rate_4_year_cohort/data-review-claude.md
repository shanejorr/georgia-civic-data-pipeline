# Data Review: graduation_rate_4_year_cohort

**Date**: 2026-06-11
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Gold data is value-accurate: **v1 parity MATCH (byte-identical)**, every bronze-to-gold trace matched (extremes, all six eras, all four suppression conventions, the 2010 migrant defect rows, the 2023/24 partial-suppression rows), the 781-row drop accounting replays exactly, and the §5b combined Asian/Pacific Islander convention is proven by an exact race-partition sum at the state row in all 21 years. Two **documentation** inaccuracies in the emitted contract require fixes (no parquet change, parity preserved): (1) 2007-2009 bronze uses Era-1-style literal-zero suppression — zero "Too few Students" cells and zero NULLs exist in those files — yet the contract claims "Suppressed cells are NULL (not zero) from 2007 onward"; (2) the 2023/24 partial-suppression rows are described as "district rows" but are mostly school rows (295/369 in 2023, 271/339 in 2024). Two judgment items: a probable pre-2011 methodology break (leaver-style rate vs federal ACGR) that the contract description papers over, and 49 district-years where the bronze-published district graduate_count is below its visible school sum.

## Manifest Verification

Preconditions: FRESH (transform mtime 01:35:12 < manifest 01:35:21 ≤ validation 01:35:21); `passed: true`; `read_loss`/`masked_values`/`reclassified` sections absent (zero events — 2004's malformed chunk is in-band: raw=parsed=2271).

### Categorical maps

| Column | Map entries | Bronze values seen | Unmapped | Status |
|---|---|---|---|---|
| demographic | 23 (effective `DEMOGRAPHIC_ALIASES` slice) | 26 raw labels | 0 | PASS |
| detail_level | 3 | 3 | 0 | PASS |

**demographic — all 23 entries verified semantically against `src/utils/demographics.py`** (each confirmed identical to the alias table; the 26 seen labels collapse to 23 keys after case-folding):

| Bronze (upper) | Gold | Correct? |
|---|---|---|
| ALL STUDENTS | all | YES (covers "ALL Students" + "All Students") |
| ASIAN/PACIFIC ISLANDER | asian_pacific_islander | YES — explicit combined label (tidy era) and the wide-era relabel target; see §2e below |
| BLACK / HISPANIC / WHITE | black / hispanic / white | YES |
| MULTIRACIAL, MULTI-RACIAL | multiracial | YES (Era-1 vs tidy spelling variants) |
| NATIVE AMER/ALASKAN NATIVE, AMERICAN INDIAN/ALASKAN | native_american | YES (Era-1/2 vs tidy labels, same population per structure doc §5) |
| MALE / FEMALE | male / female | YES |
| ECONOMICALLY DISADVANTAGED | economically_disadvantaged | YES (flag=Y semantics — it is the label of the subgroup itself) |
| NOT ECONOMICALLY DISADV, NOT ECONOMICALLY DISADVANTAGED | not_economically_disadvantaged | YES (canonical `not_` prefix) |
| STUDENTS WITH DISABILITIES, STUDENTS WITH DISABILITY | students_with_disabilities | YES (plural/singular era variants) |
| STUDENTS WITHOUT DISABILITIES, STUDENTS WITHOUT DISABILITY | students_without_disabilities | YES (Era-2 suffix `RL` "Regular Learners" mapped via label, matches structure-doc legend) |
| LIMITED ENGLISH PROFICIENT | english_learners | YES (canonical key for LEP) |
| MIGRANT | migrant | YES |
| HOMELESS / FOSTER / ACTIVE DUTY | homeless / foster_care / active_duty | YES (2018+ expansion labels) |

Completeness note: bare bronze "Asian" (wide eras 2004-2010) intentionally never reaches `_demographic_raw` — the triplet maps relabel it to "Asian/Pacific Islander" *before* normalization (topic-local §5b override; the global `ASIAN → asian` alias untouched). Every label documented in the structure doc appears in `bronze_values_seen`; no documented label is missing.

**detail_level**: State→state, District→district, School→school — trivially correct; `replace_strict(default=None)` + manifest unmapped guard.

**2c contract cross-check**: `gold_values_produced` (18 values) equals the contract `enum` exactly. **2d**: `unmapped_count` = 0 for both columns.

### §2e Asian/Pacific Islander conflation (Risk 1) — PASS (combined convention, positive evidence)

Gold emits `asian_pacific_islander` from the tidy era's explicit "Asian/Pacific Islander" label; the wide-era relabel of bare "Asian" is proven by the math test, run for **every** year at the state row (executed):

```
2005: all_N=67547 race_N=67547 ratio=1.000000 | all_S=97359 race_S=97359
2010: all_N=91561 race_N=91561 ratio=1.000000 | all_S=113364 race_S=113364
2024: all_N=117661 race_N=117661 ratio=1.000000 | all_S=137710 race_S=137710
```

All 21 years: ratio exactly 1.000000 for graduate_count, and cohort_size where published (2012-2016 publish no S). Pacific Islanders are folded in, not dropped — `asian_pacific_islander` is correct. Gender partition (male+female = all) also exact in all 21 years. Pinned as contract quality checks `state_race_partition_sums_to_all` / `state_gender_partition_sums_to_all`, both passing.

### §2f Mutual exclusivity (Risk 6) — PASS, single convention

Gold contains 0 `asian` and 0 `pacific_islander` rows (executed). Only the combined key exists; no synthesized rollups.

### Row-count reconciliation

| Year(s) | Bronze | Expansion | Drops | Expected gold | Manifest gold | Match |
|---|---|---|---|---|---|---|
| 2004 | 2,271 | ×15 after −1 malformed | 1 malformed + 750 twin rows | (2271−1)×15−750 = 33,300 | 33,300 | ✓ |
| 2005-2008, 2010 | 522/530/535/550/576 | ×15 | 0 | ×15 exact | ✓ all | ✓ |
| 2009 | 561 | ×15 | 30 twin rows (2 entities) | 561×15−30 = 8,385 | 8,385 | ✓ |
| 2011-2024 | various | ×1 | 0 | 1:1 | ✓ all | ✓ |

Total: bronze 165,204 → gold 242,039; `total_filtered_explicit` 781 = 1 `malformed_sysschoolid_row` + 780 `duplicate_bronze_twin_rows_deduplicated`. **Replayed independently** (executed): 2004 has exactly 1 row lacking ':' (`SysSchoolID='0"'`, `SchoolName='10'`), 50 duplicate SysSchoolIDs (100 rows → 50 removed), 2009 has 2 (`768:ALL` Ivy Prep, `770:ALL` Scholars Academy, one twin per pair NULL-named); **0 twin groups have divergent metrics after casting** in either year; 1 + 50×15 + 2×15 = 781. Actual parquet rows: 242,039 = manifest `total_gold`.

## Column Coverage

Per the structure doc's Gold Schema Classification:

| Bronze column | Gold column | Status |
|---|---|---|
| SysSchoolID (Eras 1-2) | district_code + school_code (split on ':', ALL→NULL, zfill 3/4) | MAPPED |
| SchoolName / SchoolNme (Eras 1-2) | — (dimension attribute) | CORRECTLY EXCLUDED |
| SCHOOL_DSTRCT_CD (Eras 3+) | district_code (ALL→NULL, zfill(3)) | MAPPED |
| SCHOOL_DSTRCT_NM / INSTN_NAME (Eras 3+) | — (dimension attributes) | CORRECTLY EXCLUDED |
| INSTN_NUMBER (Eras 3+) | school_code (ALL→NULL, zfill(4)) | MAPPED |
| DETAIL_LVL_DESC (Eras 3+) | detail_level (drives file split, dropped at export) | MAPPED |
| LONG_SCHOOL_YEAR (Eras 3+) / filename (Eras 1-2) | year | MAPPED |
| LABEL_LVL_1_DESC (Eras 3+) | demographic (prefix-stripped, normalized) | MAPPED |
| Graduation Rate {demo} / GradRate_P* / PROGRAM_PERCENT | graduation_rate (÷100, canonical `…_rate` name on 0-1 scale) | MAPPED |
| Number Taken {demo} / GradRate_N* / PROGRAM_TOTAL | graduate_count | MAPPED |
| Approximate Class Size {demo} / GradRate_S* / TOTAL_COUNT | cohort_size (NULL 2012-2016, absent in source) | MAPPED |
| GRADES_SERVED_DESC | — (dimension attribute) | CORRECTLY EXCLUDED |
| #RPT_NAME (Era 6) | — (constant; guarded by `_validate_era6_constants`) | CORRECTLY EXCLUDED |

No gold column lacks a bronze source (no fabrication). The Era-1 "Approximate Class Size Amer/Alaskan Native" name quirk (drops "Native") is handled by the literal triplet entry; `_require_columns` fails loudly on any missing triplet column.

## Value-Level Spot Checks

All MATCH; bronze quoted from executed reads.

**Extreme rows (per-metric global max/min):**

| Trace | Bronze | Gold | Verdict |
|---|---|---|---|
| graduate_count + cohort_size global max — 2024 state all | `('ALL','ALL','117661','85.44','137710')` | (117661, 137710, 0.8544) | MATCH |
| 2004 (Era-1 max) state all | `('ALL:ALL','65.4','65124','99535')` | (65124, 99535, 0.654) | MATCH |
| graduation_rate tidy min — 2012 school 761/2664 Black | `('16','3.98')`, no TOTAL_COUNT | (16, None, 0.0398) | MATCH |
| graduate_count threshold min — 2011 district 606 Asian/PI | `('10','100','10')` | (10, 10, 1.0) | MATCH |
| graduation_rate max 1.0 — 2005 792:273 Native Am. | `('100','2','2')` (via the "Class Size Amer/Alaskan Native" column) | (2, 2, 1.0) | MATCH |
| graduation_rate min 0.0 (wide eras) | 2007 zero-triplets, e.g. 601:103 `Pa=0, Na=0, Sa=0` | (0, 0, 0.0) pattern preserved | MATCH (see Fix 1: zeros are Era-1-style suppression) |

**Ordinary traces (one per era, all metric columns):**

| Era | Entity | Bronze | Gold | Verdict |
|---|---|---|---|---|
| 1 (2005) | Valdosta 792:273, all / asian | `65.0/360/554`; Asian `84.6/11/13` | (360,554,0.65); as_pi (11,13,0.846) | MATCH |
| 2 (2010) | Appling 601:103, all / black | `80.2/202/252`; `80.3/49/61` | (202,252,0.802); (49,61,0.803) | MATCH |
| 3 (2011) | District 601, all / black | `161/60.98/264`; `37/50/74` | (161,264,0.6098); (37,74,0.5) | MATCH |
| 4 (2014) | District 601, all | `206/82.4` (no TOTAL_COUNT) | (206, None, 0.824) | MATCH |
| 5 (2020) | District 601, all | `205/92.76/221` | (205, 221, 0.9276) | MATCH |
| 6 (2024) | District 601, all | `225/93.75/240` | (225, 240, 0.9375) | MATCH |

**Suppression traces (every marker type):** 2010 "Too few Students" (601:103 Asian, all three cells) → all-NULL gold row ✓; 2014 blank cells (district 601 Am. Indian) → all-NULL ✓; 2024 TFS (district 601 Active Duty: raw CSV `('TFS','TFS','TFS')`, nulled by `read_bronze_file`) → all-NULL ✓; Era-1/2007-2009 zeros pass through as published (0,0,0.0) ✓.

**2010 migrant defect rows (preserved per §4b):** bronze `ALL:ALL P_mig=65.5/N=110/S=110`, `635:ALL 69.6/23/23`, `635:1554 69.6/23/23` → gold (110,110,0.655), (23,23,0.696), (23,23,0.696). Exactly these 3 rows violate rate-reconciliation in all of gold (executed: 3 rows with |rate − N/S| > 0.001, all year=2010 demographic='migrant'; max deviation elsewhere **0.0005000**) — the transform's claims (tight exclusion, 0.0005 measured max, 0.001 tolerance) verified exactly.

**2023/24 partial suppression:** bronze rows with numeric TOTAL_COUNT + TFS PROGRAM_TOTAL: **369 (2023) and 339 (2024)** — equal to gold rows with cohort_size present and graduate_count NULL. Trace: 2023 district 604 Female `TFS/TFS/10` → gold (None, 10, None) ✓; 2024 district 602 SWD `TFS/TFS/12` → gold (None, 12, None) ✓. **However** bronze detail levels are 2023: School 295 + District 74; 2024: School 271 + District 68 — the contract's "district rows" wording is wrong (Fix 2).

**Cast-loss screens (executed):** 0 cells in any of the 21 files fail the Float64 cast outside suppression markers; 0 count cells are Float-castable-but-Int64-uncastable in surviving rows (4 such cells exist in 2004, all inside the single dropped corrupt row `SysSchoolID='0"'` — no data impact; docstring claim holds for surviving rows).

## Validation Cross-Read

`_validation.json`: **20 pass / 0 fail / 1 warning** — `contract_parquet_schema` (63 files), `contract_quality_sql` (all 14), `grain_uniqueness` (year, district_code, school_code, demographic), `foreign_keys` (248 district + 2,325 school + 18 demographic keys resolve) all pass. Warning: `null_rate_spikes` (8 details) — graduate_count/graduation_rate 2004 at 85.8% and cohort_size 2004 at 76.7% (2004 enumerates every Georgia school incl. non-graduating elementary/middle, blanks in-band — structure doc §19, documented in contract notes), and cohort_size 100% NULL 2012-2016 (source publishes no TOTAL_COUNT — pinned by the `cohort_size_unpublished_2012_2016` quality check). Both explained; no escalation.

`schema_hash`: `ab4fd4139e172bfa89f3b0877a4a57c821a7ab5bfeed23ba27b7cfe2e5ef426c`.

**§4b masking audit**: no `_null_*` helpers in transform.py, no `record_masked` calls, no `masked_values` manifest section — consistent with the "No §4b masks" claim; the only anomaly (2010 migrant) is extreme-but-conceivable, preserved, documented in the contract, and excluded precisely from the reconciliation check. PASS.

**§15b coverage judgment**: 9 authored checks (numerator≤denominator, rate↔counts reconciliation with the tight 2010-migrant exclusion, co-suppression, cohort-NULL 2012-2016, race partition, gender partition, n≥10 threshold 2011+, expanded subgroups <2018, EL absent 2021) + 5 derived. This covers the topic's real invariants comprehensively — partition sums, co-null structure, era-structural facts, and the threshold. No missing obvious invariant. PASS.

**v1 parity** (executed, verbatim):

```
MATCH — byte-identical with v1 gold
```

## Cross-Era Consistency

- **Overlap years**: none — 21 files, one year each, year sets disjoint (manifest `files_processed`). Dedup tie-break inversion (Risk 5): N/A; the only key duplicates were the 52 value-identical wide-era twin pairs (replayed above), guarded by `assert_no_natural_key_collisions` *before* dedup.
- **Era boundaries**: 2006→2007 (wide_v1→wide_v2) and 2010→2011 (wide→tidy) state all-students series: 0.654, 0.694, 0.708, 0.723, 0.754, 0.789, 0.808 | 0.6747, 0.6973, 0.718, ... 0.8544. Smooth within 2004-2010 and within 2011-2024; the **13.3-point drop at 2010→2011** coincides with Georgia's adoption of the federal adjusted-cohort rate — a source methodology break, not a transform bug (Judgment Call 1). No >10x jumps; no cumulative-publication signature.
- **Cross-year NULL sweep (Risk 2)**: one flag — `cohort_size` ~100% NULL only in [2012, 2013, 2014, 2015, 2016] — matches the bronze (TOTAL_COUNT column absent in those files per manifest `bronze_columns`), is logged by the transform, documented in the contract, and pinned by a quality check. Not a rename bug. No column is NULL in every year.
- **Demographic sets per year (gold, executed)**: 15 (2004-2017), 18 (2018-2020), 17 (2021, `english_learners` absent), 18 (2022-2024); 2018−2017 = {active_duty, foster_care, homeless}; 2022−2021 = {english_learners}. Confirms the structure-doc *corrections* (expansion starts 2018, not 2020; 2021 has 17 labels).
- **Detail-level counts vs structure doc**: 2011 = 6900/2760/15, 2023 = 9250/3807/18, 2024 = 9285/3953/18 — all match (confirming the doc's corrected Era-6 row-count attribution).
- **799:ALL** ("State Schools") present as a district-level row in every wide year 2004-2010 (and as district 799 in 2020-2024 tidy files); only ALL:ALL became the state row.
- **Aggregate feasibility screen (4d — aggregates come from bronze)**: district `all` graduate_count < max school: **0 violations** in 3,847 district-years. State vs district-sum: ratio 0.9988-1.0000 every year (districts slightly under state — suppressed/zero district rows; tolerated composition drift). District < *visible school sum* in 49 district-years — verified faithful bronze passthrough (Judgment Call 2).

## Transform Logic Risks

| Risk | Severity | Verdict / details |
|---|---|---|
| Silent column drops | — | PASS — `_require_columns` guards all 47 wide columns and 7 required tidy columns; exclusions are dimension attributes/constants |
| Era routing | — | PASS — ordered first-match signatures, most-specific (`tidy_2023_2024`) first; manifest confirms expected era per file |
| Filter logic logged + justified | — | PASS — malformed row + twin dedup recorded via `record_filtered`; replayed to 781 exactly |
| Normalization map completeness | — | PASS — all structure-doc labels covered; 0 unmapped |
| `strict=False` casts | — | PASS — cast-loss screens found 0 silent losses outside suppression markers (4 decimal count cells confined to the dropped corrupt row) |
| Dedup keys + tie-break | — | PASS — collision guard before dedup; twins value-identical; `sort_col="cohort_size"` safety net value-irrelevant here |
| Year extraction | — | PASS — wide: filename (no year column in bronze); tidy: `LONG_SCHOOL_YEAR` parsed (`parse_school_year('2023-24')=2024`) and cross-checked against filename, raising on mismatch (Risk 3 N/A — no other year-bearing strings) |
| §4b masking (5b) | — | PASS — no masks; 2010 migrant preserve+document decision conforms to §4b extreme-but-conceivable |
| Suppression-era documentation | MEDIUM | FLAG — 2007-2009 misdescribed as marker-suppressed/NULL (Fix 1) |
| Partial-suppression wording | LOW | FLAG — "district rows" wrong (Fix 2) |

## Required Fixes

### Fix 1: Contract and docstring misstate the 2007-2009 suppression convention (zeros, not "Too few Students"/NULL)
- **Severity**: MEDIUM
- **Issue**: The contract tells consumers "Suppressed cells are NULL (not zero) from 2007 onward, but 2004-2006 sources use literal ZEROS" and scopes the 'Too few Students' marker to "2007-2010". In reality the 2007, 2008, and 2009 bronze files contain **zero** "Too few Students" cells and **zero** blank cells — they use Era-1-style literal-zero suppression (rate=0, N=0, S=0-2 triplets) — and gold for those years has **zero NULLs** in all three metrics. Only 2010 uses the marker. Consumers following the contract will treat 2007-2009 zeros as real values when they are indistinguishable-from-suppressed, biasing any mean/min computed over those years.
- **Evidence**: Executed scan of bronze: `2007: too_few_students_cells=0 empty_or_null_cells=0 zero_rate_cells=1818`, `2008: 0/0/1805`, `2009: 0/0/1774`, `2010: too_few=9573 empty=0 zero_rate=15`. Zero-pattern sample (2007 `601:103` Appling Co HS): `GradRate_Pa='0', GradRate_Na='0', GradRate_Sa='0'` — identical to the documented Era-1 suppression signature. Manifest `metric_stats`: 2007-2009 `null_pct: 0.0` for graduation_rate/graduate_count/cohort_size; 2010 `null_pct: 0.3693` (3,191 = 9,573/3 marker triplets, exact). Contract limitations (contracts/education/graduation_rate_4_year_cohort.odcs.yaml): "Suppressed cells are NULL (not zero) from 2007 onward…"; `graduate_count` null_meaning: "…'Too few Students' 2007-2010"; notes[0]: "2007-2010 'Too few Students' literals".
- **Location**: `_emit_contract_and_readme()` in transform.py — `limitations=`, the `null_meaning`/`description` of `graduate_count`/`cohort_size`/`graduation_rate`, and `notes[0]`; also the module docstring "Suppression differs per era" bullet (lines ~40-48).
- **Suggested fix**: Re-scope the zero-suppression caveat to **2004-2009** ("a zero rate/count in 2004-2009 may be real or suppressed; treat very small cohorts with caution") and the 'Too few Students' marker to **2010 only**; null_meaning becomes "blank cells 2011-2020, TFS literals 2021-2024, 'Too few Students' 2010; 2004-2009 have no suppression NULLs (literal zeros instead)". Text-only change — re-running the transform re-emits the contract/README without touching parquet, so v1 parity is preserved.

### Fix 2: Partial-suppression rows misdescribed as "district rows"
- **Severity**: LOW
- **Issue**: The contract says cohort_size is published on partially suppressed "district rows" in 2023-2024 ("2023-2024 publish it on 369/339 district rows whose other metrics are TFS-suppressed"). The majority of those rows are **school**-level.
- **Evidence**: Executed bronze count of rows with numeric TOTAL_COUNT + TFS PROGRAM_TOTAL: 2023 → `[('School', 295), ('District', 74)]` (= 369); 2024 → `[('School', 271), ('District', 68)]` (= 339). (The structure doc's consideration 18 "all district-level" is wrong on the same point.) Totals and gold behavior are correct; only the level attribution is wrong.
- **Location**: `_emit_contract_and_readme()` in transform.py — `cohort_size` description ("In 2023-2024 some district rows publish cohort_size…") and `notes[1]` ("…on 369/339 district rows…").
- **Suggested fix**: Change to "district and school rows" (or "rows, mostly school-level"). Text-only; parquet unchanged.

## NEEDS_JUDGMENT

### Judgment Call 1: 2004-2010 rates predate the federal adjusted-cohort methodology — contract describes the whole series as federal ACGR
- **Severity if confirmed**: MEDIUM
- **Suspicion**: The contract's purpose statement and column descriptions present all of 2004-2024 as the "Federal four-year adjusted-cohort graduation rate" with cohort_size as "the adjusted four-year cohort… plus transfers in, minus transfers out". The 2004-2010 figures are very likely Georgia's earlier (leaver-style/NGA) graduation rate, not the federal ACGR, making the two halves of the series non-comparable without a caveat.
- **Evidence available**: State all-students rate drops from 0.808 (2010) to 0.6747 (2011) — a 13.3-point one-year break exactly at Georgia's first federal-ACGR reporting year, then resumes a smooth trend; the wide-era denominator column is literally named "Approximate Class Size" (an adjusted cohort would not be "approximate"); the metric-name/format reset (Eras 1-2 → 3) coincides.
- **Why uncertain**: The bronze files carry no methodology metadata, and GOSA ships all 21 years under one "graduation_rate_4_year_cohort" download — I cannot prove the pre-2011 formula from the artifacts alone. Preserving the published values is correct either way; only the description is at stake.
- **Location**: `_emit_contract_and_readme()` — `description`, `limitations`, and the `graduation_rate`/`cohort_size` column descriptions.
- **If confirmed, suggested fix**: Add a limitations sentence: "2004-2010 figures predate Georgia's adoption of the federal four-year adjusted-cohort methodology (first reported 2011); the 2010→2011 state rate drop (~81%→67%) is a methodology break, not a real decline — do not trend across it." Text-only; parity preserved.

### Judgment Call 2: 49 district-years where the published district graduate_count is below the visible school sum
- **Severity if confirmed**: LOW
- **Suspicion**: In 49 of 3,847 district-years (1.3%) the bronze-published district `all` graduate_count is smaller than the sum of its published school rows (it is never below the max single school). A handful of districts recur (e.g., 755 Whitfield in 2010-2016, 675/676 in 2005-2007), suggesting a systematic source-side cohort-assignment difference (students counted at a school but excluded/deduplicated at the district level).
- **Evidence available**: Executed screen: 0/3,847 district < max-school violations; 49 district < visible-school-sum cases, max gap 103. Faithful passthrough verified: 2016 bronze itself publishes Whitfield district `PROGRAM_TOTAL='709'` while its four school rows sum to 810 (`187+255+101+267`); gold matches bronze exactly.
- **Why uncertain**: This is the source's own internal inconsistency, not a transform defect; whether it merits a consumer-facing caveat (vs. accepting that school rows don't necessarily roll up) is a publication-policy call.
- **Location**: n/a (data correct as published); optional caveat in `_emit_contract_and_readme()` `limitations=` or notes.
- **If confirmed, suggested fix**: Add a note: "School rows do not always sum to the published district row (49 district-years have district < school sum, source-published); use the official district/state rows for rollups rather than summing school rows."

## Notes

- schema_hash `ab4fd4139e172bfa89f3b0877a4a57c821a7ab5bfeed23ba27b7cfe2e5ef426c`; validation 20 pass / 0 fail / 1 explained warning; 14/14 contract quality SQL checks pass.
- v1 parity: **MATCH — byte-identical with v1 gold** (`docs/rebuild/v1-baseline.yaml` key `education/gosa/graduation_rate_4_year_cohort`). Both Required Fixes and both judgment items are contract/README text changes only — re-emitting them does not alter parquet, so parity and any future approval hash are unaffected.
- Transform-agent claims all verified: 781 drops replayed exactly; §5b exact partition 21/21 years (N and S); 2010 migrant rows are the only 3 reconciliation violations with measured max legit deviation 0.0005; cohort_size genuinely absent from 2012-2016 bronze and not derived; the structure-doc corrections (2018 expansion start, 17 labels in 2021, Era-6 row-count attribution, 799:ALL in every wide year) all measured true in bronze/gold.
- Read-loss: no `read_loss` section in the manifest (zero events); the 2004 malformed chunk is in-band (raw=parsed=2271) with the 1 corrupt row dropped explicitly and recorded.
