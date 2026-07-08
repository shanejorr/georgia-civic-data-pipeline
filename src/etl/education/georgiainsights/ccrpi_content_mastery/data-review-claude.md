# Data Review: ccrpi_content_mastery

**Date**: 2026-06-12
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Value-level accuracy is excellent: all 15 bronze→gold spot checks across all five eras MATCH exactly, every categorical map entry is semantically correct, row parity is 1.00x bronze in all 13 years (1,707,230 rows), and **v1 parity is MATCH (byte-identical, sha `a14eac09…`)** — independently recomputed. Both `100.00+` sentinel repairs verified against bronze: 2021's 1,772 reconstructions (recon range [100.005, 150.0] recomputed from bronze bands; exactly 1,772 gold 2021 scores >100) and 2023's 2,683 caps (0 gold 2023 scores >100). The single Required Fix is a §15b guard-authoring item (year-scoped upper bound on `indicator_score`), not a data defect — it changes only the contract's quality list, so parity is preserved.

## Manifest Verification

### Categorical maps

| Column | Map entries | Bronze values seen | Unmapped | Status |
|---|---|---|---|---|
| demographic | 11 (uppercased; covers 12 case-variant bronze labels) | 12 | 0 | PASS |
| grade_cluster | 3 | 3 | 0 | PASS |
| assessment_type | 4 | 4 | 0 | PASS |
| subject | 16 (→15 gold values) | 16 | 0 | PASS |
| ccrpi_flag | 4 | 4 | 0 | PASS |

### Full map review

**demographic** — all entries verified against `src/utils/demographics.py` (`DEMOGRAPHIC_ALIASES` printed and checked):
`ALL STUDENTS→all` ✓; `ASIAN/PACIFIC ISLANDER→asian_pacific_islander` ✓ (combined bucket, §5b — see 2e below); `BLACK→black` ✓; `HISPANIC→hispanic` ✓; `WHITE→white` ✓; `MULTI-RACIAL→multiracial` ✓; `AMERICAN INDIAN/ALASKAN→native_american` and `AMERICAN INDIAN/ALASKAN NATIVE→native_american` ✓ (same concept, 2019/2022+ spelling drift per structure doc); `ECONOMICALLY DISADVANTAGED→economically_disadvantaged` ✓; `STUDENTS WITH DISABILITY→students_with_disabilities` ✓ (covers both `With`/`with` bronze case variants after uppercase). 12 bronze labels → 10 canonical keys via spelling drift only; no two distinct concepts collapse to one key.

**subject** — `READING→reading` kept DISTINCT from `ENGLISH LANGUAGE ARTS→english_language_arts` ✓ (2013 ships both at 19,783 rows each — CRCT Reading is a separate test, not an ELA alias); `ENGLISH→english_language_arts` ✓ (2021-2022 Content Area relabel of the same indicator); `MATHEMATICS-1/-2→mathematics_1/_2` ✓ kept distinct from `ALGEBRA I/COORDINATE ALGEBRA→algebra_i_coordinate_algebra` / `GEOMETRY/ANALYTIC GEOMETRY→geometry_analytic_geometry` ✓ (curriculum-era distinction preserved per education CLAUDE.md); `9TH GRADE LITERATURE AND COMPOSITION`, `AMERICAN LITERATURE AND COMPOSITION`, `BIOLOGY`, `PHYSICAL SCIENCE`, `US HISTORY`, `ECONOMICS/BUSINESS/FREE ENTERPRISE`, `SCIENCE`, `SOCIAL STUDIES` → snake_case equivalents, all semantically exact ✓.

**assessment_type** — `CRCT→crct`, `EOCT→eoct`, `EOG→eog`, `EOC→eoc` ✓ (acronyms are the canonical program names per education CLAUDE.md vocabulary).

**grade_cluster** — `E→elementary`, `M→middle`, `H→high` ✓.

**ccrpi_flag** — `G→green`, `G*→green_star`, `Y→yellow`, `R→red` ✓ per §16 convention; bronze `NA` (not rated) → NULL at read via `SUPPRESSION_VALUES` ✓.

- **2a Completeness**: every distinct bronze value documented in the structure doc appears in `bronze_values_seen` (12 demographic labels, 16 subjects across eras, E/M/H, CRCT/EOCT/EOG/EOC, G/G*/Y/R). No documented value missing → no skipped era/file-routing gap.
- **2c Contract cross-check**: `gold_values_produced` equals the contract `enum` exactly for all five columns (10/3/4/15/4 values).
- **2d Unmapped**: 0 in every column.

### 2e: Asian / Pacific Islander (Risk 1) — PASS

Gold emits `asian_pacific_islander` from the explicit combined bronze label `Asian/Pacific Islander` (present in every era; 11 grep hits in the structure doc, zero separate Asian or Pacific Islander labels — `grep -icE 'pacific[ _-]?islander|…'` → 11, all the combined label). The skill's math test printed `indicator_score: year=2025 total=736.96 race_sum=4728.86 ratio=6.4167 -> OK` — no summable count metric exists (scores are averages; ratio ≈ 6 race buckets is the expected non-additive result), so the structural test governs: bronze never publishes a split pair, the combined key is the only correct §5b convention. The split keys are never emitted.

### 2f: Mutual exclusivity (Risk 6) — PASS — single convention

`gold_values_produced` contains `asian_pacific_islander` and no `asian` / `pacific_islander`; no rollup-plus-split conflict possible.

### Row-count reconciliation

| Year | Bronze | Gold | Factor | Detail split (state/district/school) |
|---|---|---|---|---|
| 2012 | 138,000 | 138,000 | 1.00 | —/—/138,000 (school-only, per doc) |
| 2013 | 136,595 | 136,595 | 1.00 | —/—/136,595 |
| 2014 | 171,495 | 171,495 | 1.00 | 180/34,710/136,605 = doc exactly |
| 2015 | 148,606 | 148,606 | 1.00 | 160/31,400/117,046 = doc (Correction 6) |
| 2016 | 149,312 | 149,312 | 1.00 | 160/31,520/117,632 = doc |
| 2017 | 150,402 | 150,402 | 1.00 | 160/33,240/117,002 = doc Correction 6 |
| 2018 | 125,160 | 125,160 | 1.00 | 120/25,520/99,520 = **bronze recount** (doc's 25,560/99,480 is wrong — see Notes) |
| 2019 | 125,520 | 125,520 | 1.00 | 120/25,560/99,840 = doc |
| 2021 | 110,900 | 110,900 | 1.00 | 110/24,310/86,480 = doc |
| 2022 | 111,590 | 111,590 | 1.00 | 110/24,420/87,060 = doc |
| 2023 | 112,430 | 112,430 | 1.00 | 110/24,860/87,460 = doc ALL-counts |
| 2024 | 113,750 | 113,750 | 1.00 | 110/25,740/87,900 |
| 2025 | 113,470 | 113,470 | 1.00 | 110/25,740/87,620 = doc ALL-counts |

Bronze totals match the structure doc for every file; `total_filtered = 0` everywhere; expansion factor 1.00 in all years; gold parquet actual count 1,707,230 = manifest `total_gold` (3b PASS). All 12 expected years present, 2020 correctly absent. RTC: exactly 480 gold rows (160 × 2015-2017), all `district_code='RTC'` with NULL `school_code` — matches Correction 4 (no individual RTC school rows; verified in 2017 bronze: 160 RTC rows, all `School ID='ALL'`).

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| SCHOOL YEAR / School Year | `year` | MAPPED (cross-checked vs filename; mismatch raises) |
| SYSTEM ID / System ID / System Id | `district_code` | MAPPED (zfill(3); ALL→NULL; RTC kept) |
| SYSTEM NAME / System Name | — | CORRECTLY EXCLUDED (districts dimension) |
| SCHOOL ID / School ID / School Id | `school_code` | MAPPED (zfill(4); ALL→NULL; bronze '288'→'0288' verified) |
| SCHOOL NAME / School Name | — | CORRECTLY EXCLUDED (schools dimension) |
| GRADE CLUSTER / Grade Cluster | `grade_cluster` | MAPPED |
| Grade Configuration (2018+) | — | CORRECTLY EXCLUDED (school attribute, not a test attribute) |
| REPORTING CATEGORY / Reporting Label | `demographic` | MAPPED |
| ASSESSMENT TYPE / Assessment Type (2012-2017) | `assessment_type` | MAPPED (NULL-filled 2018+) |
| ASSESSMENT SUBJECT / Indicator / Content Area | `subject` | MAPPED |
| PARTICIPATION RATE / Participation Rate | `participation_rate` | MAPPED (per-era /100 vs pass-through) |
| MEETS & EXCEEDS RATE / Meets Exceeds Rate / Weighted Proficiency Rate / Achievement Rate / Indicator Score | `indicator_score` | MAPPED (4 labels → 1 column; sentinel policies per era) |
| Beginning/Developing/Proficient/Distinguished Learner [or Level N] (2021-2022) | `pct_*_learner` | MAPPED (/100; `_or_above` derived) |
| Target (2018-2019, 2023-2025) | `target` | MAPPED |
| Flag (2018-2019, 2023-2025) | `ccrpi_flag` | MAPPED |

Every gold column traces to bronze (the two `_or_above` columns are documented derivations); no fabrication. Era rename maps cover every bronze column of their signature; `_require_columns` raises on any absence.

## Value-Level Spot Checks

All 15 traces MATCH. Extreme rows first.

| # | Trace | Bronze (file, row, value) | Expected | Gold | Verdict |
|---|---|---|---|---|---|
| 1 | participation global max | 2013: 667/1112/M/White/CRCT, `PARTICIPATION RATE='108.4'` ×3 subjects (ELA 95.6, `'Science       '` 82.5, Soc St 88.6) | /100 → 1.084; trailing-space Science → `science` | 1.084 on all 3; scores 95.6/82.5/88.6 | MATCH |
| 2 | indicator_score era-2 global max | 2017: 644/'288'/E/Asian-PI/EOG/Social Studies, `WPR='146.154'`, part `'100'` | preserve >100; zfill '288'→'0288' | 146.154, part 1.0 at school_code '0288' | MATCH |
| 3 | 2021 reconstruction max | 2021: 629/0102/H/White/English, bands `0.00/0.00/0.00/100.00`, `ACHIEVEMENT RATE='100.00+'` | 0.5·0+0+1.5·100=150.0; bands→0/0/0/1.0; or_above 1.0/1.0 | 150.0; 0.0/0.0/0.0/1.0; 1.0/1.0 | MATCH |
| 4 | 2021 sentinel population | 1,772 bronze `'100.00+'` rows, 0 with null bands, recon range [100.005, 150.0] (recomputed from bronze) | only sentinel rows exceed 100 | exactly 1,772 gold 2021 rows >100 | MATCH |
| 5 | 2023 cap | 2023: 603/3050/E/Multi-Racial/Mathematics `INDICATOR SCORE='100.00+'`, Target '90', Flag 'G' (2,683 sentinels recounted in bronze) | →100.0; target 90.0; green | 100.0 / 90.0 / green; 0 gold 2023 rows >100 | MATCH |
| 6 | target max | 2019: 625/ALL(district)/E/Asian-PI/Math, `TARGET='95'`, score '94.4', part '0.9949', Flag 'G' | district row, school_code NULL | 95.0 / 94.4 / 0.9949 / green | MATCH |
| 7 | target min | 2025: 667/1114/H/Econ Disadv/ELA, `TARGET='1.7'`, score '9.82', part '0.9333', Flag 'G*' | pass-through; green_star | 1.7 / 9.82 / 0.9333 / green_star | MATCH |
| 8 | suppression (era 1) | 2013: 734/0101/M/Asian-PI/CRCT/Math, both metrics `'Too Few Students'` | NULL/NULL | NULL/NULL | MATCH |
| 9 | suppression (`No Data`) + part min | 2013: 647/0114/H/Econ Disadv/EOCT/US History, part `'0'`, M&E `'No Data'` | 0.0 / NULL (strict=False cast) | 0.0 / NULL | MATCH |
| 10 | ordinary era 1 | 2013: 706/5060/E/White/CRCT/ELA, `'98.7'`/`'86.7'` | 0.987 / 86.7 | 0.987 / 86.7 | MATCH |
| 11 | RTC pseudo-district | 2017: RTC/ALL/H/ALL Students/EOC/American Lit, `'80'`/`'44.737'` | district row, district_code 'RTC', school NULL | 0.8 / 44.737, school_code NULL | MATCH |
| 12 | state row (era 1 boundary, 2014) | 2014: ALL/ALL/E/ALL Students/CRCT/Math, `'99.9'`/`'85.4'` | state row, both geo NULL | 0.999 / 85.4, both NULL | MATCH |
| 13 | ordinary 2021 bands | 2021: 661/0103/E/ALL Students/Math, part '99.36', bands 20.13/32.55/33.22/14.09, AR '70.63' | /100; dev_or_above .7986; prof_or_above .4731 | 0.9936; .2013/.3255/.3322/.1409; 70.63; .7986/.4731 | MATCH |
| 14 | 2021 state row | ALL/ALL/M/English Learners/English, part '72.85', bands 47.96/32.16/17.83/2.05, AR '36.99' | geo NULL; or_above .5204/.1988 | all values exact | MATCH |
| 15 | ordinary 2022 + 2024 | 2022: 601/'103'/H/Black/Science bands 40/35.71/24.29/0, IS '42.15' → gold .4/.3571/.2429/0.0, or_above .6/.2429, score 42.15, part '100'→1.0. 2024: science row (601/'177'/E/White) 0.9878/88.52/87.71/green; math row (601/'103'/H/All) 68.98 with Target/Flag NULL (bronze NA on all 32,470 math rows, recounted) | per-era scaling + 2024 math NULL | all exact | MATCH |

- **4c Sentinel year-attribution (Risk 3)**: N/A — no year-bearing bronze strings; `_derive_keys` raises if the in-sheet `School Year` disagrees with the filename year (cross-check ran clean on all 13 files).
- **4d Aggregate feasibility screen (Risk 4)**: aggregates COME FROM BRONZE (2014+). Screen over all years: 32,143 district cells with ≥2 visible school rows — 33 (0.10%) fall >10 pts outside the visible-school score envelope, all in 2014-2017 small subgroups with exactly 2 visible schools; the worst (2017 dist 706, multiracial/high/geometry: district 63.107 vs visible schools 90.476/106.818) was traced to bronze: district value is `'63.107'` verbatim and a third school is `'Too Few Students'` — suppressed-school composition drift, source-faithful. State-vs-district: 13/651 outside range, same mechanism. No swaps or garbling; no fix.
- **4e Dedup tie-break (Risk 5)**: N/A — one file per year, natural key unique within every file (collision guard ran before dedup); no overlap years exist.
- **4f Suppression semantics**: traces 8 (`Too Few Students`), 9 (`No Data`), 15-2024 (`NA` target/flag) each land as NULL; the doc's full marker catalog (`TFS`, `Too Few Students`, `No Data`, `NA`) is covered by `SUPPRESSION_VALUES` + the strict=False cast.

## Validation Cross-Read

- `_validation.json`: **21 pass / 0 fail / 0 warning**, `passed: true`, timestamp 2026-06-12T13:16:52Z (fresh vs manifest 13:16:52, transform mtime 13:14:23). `contract_parquet_schema` (35 files), `contract_quality_sql` (23 checks), `grain_uniqueness` (7-column grain), `foreign_keys` (247 districts incl. RTC, 2,584 schools, 10 demographics) all pass.
- **schema_hash**: `ff9e66fdba8686e544dc0ec4ac57143bdd8d6312c03dcf714365a7f49605a851`
- **§4b masking audit**: no `_null_*` helpers in transform.py, no `masked_values` manifest section — consistent with the docstring's "No §4b NULL masks" claim (all extremes preserved + documented: participation ≤1.084, WPR ≤146.154, recon ≤150.0). The two `reclassified` events (2021: 1,772 reconstruct; 2023: 2,683 cap) are recorded in the manifest with reasons and documented in the contract's `indicator_score` description and notes. PASS.
- **§15b coverage judgment**: the 9 authored checks (band partition exact-2022 + budget-2021, or_above identity, co-suppression, bands-only-2021-2022, score/band co-null, assessment_type era coverage, target/flag era coverage, 2024-math-NULL) cover the partition, co-null, and era-structure invariants well. **One gap**: `indicator_score` has no upper bound anywhere (only `value_min: 0`), yet bronze is structurally ≤100 in 9 of 13 years and ≤150 even in the >100-legitimate years → Required Fix 1.
- **v1 parity** (verbatim):

```
MATCH — byte-identical with v1 gold
v1 : a14eac092eb92c4bb95129d294f4cc53008d699cf0ba8b91d71ac30b47d74740
now: a14eac092eb92c4bb95129d294f4cc53008d699cf0ba8b91d71ac30b47d74740
```

## Cross-Era Consistency

- **Cross-year NULL sweep (Risk 2)**: 9 FLAGs, all expected bronze publication gaps enforced by authored quality checks — `assessment_type` NULL 2018+ (`assessment_type_era_coverage`), six band columns NULL outside 2021-2022 (`learner_bands_only_2021_2022`), `target`/`ccrpi_flag` NULL outside 2018-2019/2023-2025 (`target_flag_era_coverage`). No column is ~100% NULL in a year its era should populate; no rename-typo signature.
- **3d level continuity** (state-level means): indicator_score 77.2 (2014) → 54.5 (2015) is the documented metric change (Meets & Exceeds → Weighted Proficiency) coinciding with the CRCT→Milestones regime change; within-era drift is smooth (54.5→57.4→59.4; 61.4→63.7; 55.8→58.9; 59.3→62.0→63.5). participation_rate state mean 0.65 in 2021 vs ~0.98-0.99 every other year — the COVID-year participation collapse, verified faithful to bronze (state EL row '72.85' → 0.7285). No >10x jumps, no cumulative-publication signature.
- **Era boundaries**: 2014→2015 (era 1→2), 2017→2018 (era 2→3), 2019→2021 (era 3→4, with the 2020 gap), 2021→2022 (era 4→5), 2022→2023 (era 5→3) all traced with at least one entity on each side; per-era scaling flips (participation 0-100 vs 0-1) land correctly on both sides of every boundary (traces 1, 2, 6, 13, 15).

## Transform Logic Risks

| Risk | Severity | Details |
|---|---|---|
| Silent column drops | PASS | `_require_columns` raises on any missing renamed column; non-renamed bronze columns (names, Grade Configuration) are documented exclusions |
| Era routing | PASS | Column-signature routing; manifest `files_processed` assigns every file its documented era; 2024 header-row retry verified by exact row count (113,750) |
| Filter logic | PASS | No row filters; `total_filtered=0`; gold = bronze 1.00x in all years |
| Normalization map completeness | PASS | All maps total-coverage vs structure doc; unmapped 0 everywhere |
| `strict=False` casts | LOW (note) | Intentional: nulls era-1/2 `No Data` (traced). Residual risk: a future non-`100.00+` sentinel (e.g. `'95.00+'`) would silently null rather than raise; mitigated by per-era sentinel policy raising on `100.00+` in un-policied eras and by bronze freshness gating new files |
| Dedup keys + tie-break | PASS | Defensive only (key unique in every file, collision guard precedes dedup); `sort_col='indicator_score'` |
| Year extraction | PASS | Filename year cross-checked against in-sheet `School Year`; mismatch raises |
| §4b masking (5b) | PASS | No masks; both sentinel repairs recorded via `record_reclassified` + contract-documented |

## Required Fixes

### Fix 1: Author year-scoped upper-bound quality checks for indicator_score
- **Severity**: MEDIUM
- **Issue**: §15b coverage gap, not a present data inaccuracy. `indicator_score` declares `value_min: 0` and intentionally no `value_max` (>100 legitimate in 2015-2017 by design and in 2021 via reconstruction) — but this leaves the topic's headline metric with NO upper guard in any year. Bronze is structurally ≤100 in 2012-2014, 2018-2019, and 2022-2025 (2023 enforced by the cap repair), and even the >100 years have a hard structural ceiling of 150 (max weight 1.5 × 100). A future transform- or source-introduced scale error (e.g., a 0-1-scale year passed through ×100, or a 0-100 column read as basis points) in the bounded years would currently pass all 23 contract checks silently.
- **Evidence**: Manifest per-year `max_val` for `indicator_score`: exactly 100.0 in 2012, 2013, 2014, 2018, 2019, 2022, 2023, 2024, 2025; 140.0/142.308/146.154 in 2015-2017; 150.0 in 2021 (= the 1.5×100 formula ceiling, trace 3). Both proposed checks pass on current gold with zero violations.
- **Location**: `_emit_contract_and_readme()` → `quality_checks=` list in `src/etl/education/georgiainsights/ccrpi_content_mastery/transform.py`
- **Suggested fix**: Author two quality checks: (1) `indicator_score_bounded_years`: `SELECT COUNT(*) FROM {object} WHERE year IN (2012,2013,2014,2018,2019,2022,2023,2024,2025) AND indicator_score > 100` `mustBe: 0`; (2) `indicator_score_structural_ceiling`: `SELECT COUNT(*) FROM {object} WHERE indicator_score > 150` `mustBe: 0`. Optionally add a third pinning the participation quirk: `participation_rate > 1` only in 2012-2013 (94 rows; `WHERE year >= 2014 AND participation_rate > 1` `mustBe: 0`). Re-running the transform re-emits the contract only — parquet bytes are unchanged, so v1 parity (MATCH) is preserved.

## Notes

- schema_hash `ff9e66fdba8686e544dc0ec4ac57143bdd8d6312c03dcf714365a7f49605a851`; validation 21 pass / 0 fail / 0 warning; 23 contract quality checks (14 auto-derived + 9 authored).
- v1 parity MATCH (`a14eac09…`), independently recomputed against `docs/rebuild/v1-baseline.yaml`. S3 was not touched (known AWS credential issue); the local baseline hash was used per instruction.
- **Structure-doc nit (no gold impact)**: the Era 5 statistics give 2018 district/school as 25,560/99,480; a direct bronze recount shows 120 state / 25,520 district / 99,520 school (the 25,560 figure is 2019's, ambiguously labeled "per year" in the doc). Gold matches bronze exactly. Worth folding into the doc's Corrections section on its next edit; not a transform issue.
- 2021 participation collapse (state mean 0.65 vs ~0.99 all other years) is a real COVID artifact, verified faithful to bronze. The contract documents the 2020 gap but not this; a one-line note in the contract description would help API consumers, at the author's discretion (cosmetic — bundled here rather than as a judgment item because the data is verified correct).
- Aggregate feasibility screen: 33/32,143 district cells (0.10%, all 2014-2017 two-visible-school subgroup cells) and 13/651 state cells sit outside their visible-children envelope — verified suppression-driven composition drift, bronze pass-through (worst case traced verbatim). No action.
- The reclassified counts (1,772 + 2,683 = 4,455 repaired sentinel cells) are the only value-altering operations in the pipeline; both verified against bronze recounts in this review.
