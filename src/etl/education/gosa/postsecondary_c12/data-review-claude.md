# Data Review: postsecondary_c12_report

**Date**: 2026-06-10
**Reviewer**: Claude (automated data review)
**Status**: NEEDS_JUDGMENT

## Summary

Gold is accurate and **byte-identical with the approved v1 baseline** (`MATCH — byte-identical with v1 gold`). All 20 demographic map entries are semantically correct; the split Asian/PI convention is proven by an exact 7-bucket state race partition (2020: race_sum 113,189 = all 113,189, ratio 1.0000) with `pacific_islander` separately published; every value trace (extremes, one entity per era, suppression, year attribution, zfill restoration) matches bronze exactly; and the per-year gold NULL totals reconcile to the structure doc's TFS counts to the student (e.g., 2008: 12,357 = 12,357). The transform's two corrections of the structure doc — (1) C12 enrollment is Georgia-institutions-only, (2) the 2015-2019 state row carries the literal `ALL`, not NULL — are both empirically confirmed here. No data fixes required; one LOW judgment item on amending the now-known-stale structure-doc claims.

## Manifest Verification

### Categorical map: `demographic`

| Column | Entries | Bronze values seen | Unmapped | Status |
|--------|---------|--------------------|----------|--------|
| demographic | 20 | 27 (14 Era 1/2 labels + 14 Era 3 prefixes, LEP shared) | 0 | PASS |

Full map review (every entry; manifest `map_used` verified identical to `src/utils/demographics.py` `DEMOGRAPHIC_ALIASES`):

| Bronze (uppercased key) | Gold | Correct? |
|---|---|---|
| TOTAL ALL | all | YES — "Total All" is the unfiltered cohort total |
| MALE | male | YES |
| FEMALE | female | YES |
| FREE REDUCED LUNCH | economically_disadvantaged | YES — FRL is the canonical economic-status proxy |
| MIGRANT | migrant | YES |
| LEP | english_learners | YES — Limited English Proficiency = EL |
| DISABILITY | students_with_disabilities | YES — Era 1/2 label for SWD |
| HISPANIC | hispanic | YES |
| TWO OR MORE RACE(S) | multiracial | YES |
| AMERICAN INDIAN OR ALASKAN NATIVE | native_american | YES |
| ASIAN | asian | YES — split convention proven (§2e below) |
| BLACK | black | YES |
| WHITE | white | YES |
| PACIFIC ISLANDER | pacific_islander | YES |
| TOTAL (Era 3) | all | YES |
| TWOORMORE (Era 3) | multiracial | YES |
| NATIVE (Era 3) | native_american | YES |
| PACIFIC (Era 3) | pacific_islander | YES |
| FRL (Era 3) | economically_disadvantaged | YES |
| SWD (Era 3) | students_with_disabilities | YES |

- **2a Completeness**: all 27 `bronze_values_seen` are exactly the union of the structure doc's Era 1/2 label list (14) and Era 3 prefix list (14), minus the shared `LEP`. No documented label is unseen; no seen label is undocumented. PASS.
- **2c Contract cross-check**: `gold_values_produced` (14 values) equals the contract enum exactly. PASS.
- **2d Unmapped**: `unmapped_count: 0`. PASS.

### 2e Asian / Pacific Islander (Risk 1)

Executed math test (state level, latest year):

```
Race buckets present: ['asian', 'black', 'hispanic', 'multiracial', 'native_american', 'pacific_islander', 'white']
graduate_count: year=2020 total=113189 race_sum=113189 ratio=1.0000 -> COMPLETE-PARTITION
```

**PASS — split convention proven.** The source publishes a distinct Pacific Islander group (cohort 2009 onward) and the seven split buckets form an exact partition. Per-year diffs (all = `all` − race_sum, graduate_count): 2008: 1,433; 2009: 1,779; 2010-2016: 0; 2017: 8; 2018: 1; 2019-2020: 0. Gender (male+female) diff is 0 in all 13 years. The transform docstring's claims are verified verbatim.

The 2008/2009 shortfalls are **unclassified-race residue, not folded PI**: state PI counts run 68-141 when published (2010-2020), ~10-20x smaller than the 1,433/1,779 gaps; and the 2009 gap exists even though PI is separately published (suppressed: bronze 2013.xlsx state PI cells are `'TFS','TFS','TFS'` — quoted) and contributes 0 to the sum. Mapping Era-1 "Asian" → `asian` is consistent and correct.

### 2f Demographic mutual exclusivity (Risk 6)

PASS — single convention. `gold_values_produced` contains `asian` + `pacific_islander` and no `asian_pacific_islander` rollup. The contract quality check `state_race_sum_within_all_total` (race sums never exceed `all`) passes, ruling out any synthesized rollup or double-counted bucket.

### Row-count reconciliation (3a/3b)

| Year | Bronze | × demos | Gold | Match |
|------|--------|---------|------|-------|
| 2008 | 574 | 13 | 7,462 | YES (Era 1 lacks PI) |
| 2009 | 577 | 14 | 8,078 | YES |
| 2010 | 588 | 14 | 8,232 | YES |
| 2011 | 592 | 14 | 8,288 | YES |
| 2012 | 610 | 14 | 8,540 | YES |
| 2013 | 614 | 14 | 8,596 | YES |
| 2014 | 614 | 14 | 8,596 | YES |
| 2015 | 628 | 14 | 8,792 | YES |
| 2016 | 626 | 14 | 8,764 | YES |
| 2017 | 634 | 14 | 8,876 | YES |
| 2018 | 644 | 14 | 9,016 | YES |
| 2019 | 646 | 14 | 9,044 | YES |
| 2020 | 649 | 14 | 9,086 | YES |

Total gold 111,370 = manifest `total_gold` = actual parquet row count (verified). `total_filtered` 0 in every year; expansion factor exactly 13.0/14.0 — zero rows lost anywhere, including through dedup. All 13 expected cohort years present.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| School Year / SCHOOL_YEAR | year | MAPPED (Int32 per domain standard; doc suggested int16) |
| School District Code / SCHOOL_DISTRCT_CD | district_code | MAPPED (zfill(3), ALL→NULL) |
| School District Name / SCHOOL_DSTRCT_NM | — | CORRECTLY EXCLUDED (districts dimension) |
| School Code / INSTN_NUMBER | school_code | MAPPED (zfill(4), ALL→NULL) |
| School Name / INSTN_NAME | — | CORRECTLY EXCLUDED (schools dimension) |
| demographic-group label component | demographic | MAPPED (unpivot, 13/14 groups) |
| (derived) detail_level | — | CORRECTLY EXCLUDED from columns — implicit in schools/districts/states.parquet split per domain convention |
| `{demo}__hs_grads` / `{PREFIX}_HS_GRADS` | graduate_count | MAPPED (doc suggested `hs_grads`; canonical-vocabulary check passes; matches v1) |
| `{demo}__in_college` / `{PREFIX}_IN_COLLEGE` / `TOTAL_ENROLLED_IN_COLLEGE` | num_enrolled_in_college | MAPPED (TOTAL outlier handled in `_era3_blocks`) |
| `{demo}__earned_24credits` / `{PREFIX}_EARNED_24CREDITS` | num_earned_24_credits | MAPPED |
| is_suppressed (optional, doc-proposed) | — | CORRECTLY EXCLUDED — suppression encoded as NULL with contract `null_meaning` + `null_semantics.suppressed_to_null` |
| #REPORTING_YEAR (Era 3) | — | CORRECTLY EXCLUDED (= year + 4, redundant) |
| Row 0 TFS note / Sheet1 (2012) / SQL sheet (2020) | — | CORRECTLY EXCLUDED (metadata) |

No gold column lacks a bronze ancestor (no fabrication). Era rename maps reviewed: `_xlsx_blocks` derives blocks from the stitched column set and raises on partial groups; `_era3_blocks` hardcodes the 14 prefixes with the `TOTAL_ENROLLED_IN_COLLEGE` outlier; `_blocks_to_long` raises on any missing source column.

## Value-Level Spot Checks

All verdicts quote bronze read directly from the source files (independent re-stitch, not the transform's reader).

**Extreme traces (4a):**

| Trace | Bronze (file, row, value) | Gold | Verdict |
|---|---|---|---|
| Global max graduate_count | 2024.csv state row: `TOTAL_HS_GRADS='113189'` | 2020/NULL/NULL/all = 113,189 | MATCH |
| Global max num_enrolled_in_college | 2024.csv state row: `TOTAL_ENROLLED_IN_COLLEGE='60460'` | 2020 state all = 60,460 | MATCH |
| Global max num_earned_24_credits | 2020.xlsx state row (cohort 2016): `Total All/Completed 1yr = '40318'` | 2016 state all = 40,318 | MATCH |
| Global min (=10) all metrics | 2012.xlsx Berrien 610/0106: `Free Reduced Lunch grads='10', coll='TFS', cred='TFS'` | 2008/610/0106/economically_disadvantaged = 10/NULL/NULL | MATCH |
| 2016 state secondary cells | 2020.xlsx state: Asian 4287/3146/2774; PI 128/52/33 | 2016 state asian = 4287/3146/2774; pacific_islander = 128/52/33 | MATCH |
| 2020 state secondary cells | 2024.csv state: `ASIAN_HS_GRADS='5240'`, `PACIFIC_HS_GRADS='141'`, `MIGRANT_*='152'/'48'/'24'` | 2020 state asian grads 5240; PI grads 141; migrant 152/48/24 | MATCH |

**Ordinary traces (4b), one entity per era, all metric columns:**

- **Era 1** — 2012.xlsx, Treutlen County 740 / Treutlen Middle/High 3050 (cohort 2008). Bronze: Total All `67/36/28`; Male `31/12/TFS`; Female `36/24/19`; FRL `44/17/11`; Black `31/12/TFS`; White `34/22/20`. Gold (year=2008, 740/3050): all 67/36/28; male 31/12/NULL; female 36/24/19; economically_disadvantaged 44/17/11; black 31/12/NULL; white 34/22/20. **MATCH** (13 demographic rows present, no `pacific_islander` — Era 1 absence honored).
- **Era 2** — 2020.xlsx, Echols County 650 / Echols County High 1050 (cohort 2016). Bronze: Total All `56/24/21`; Male `30/11/11`; Female `26/13/10`; Pacific Islander `TFS/TFS/TFS`. Gold: all 56/24/21; male 30/11/11; female 26/13/10; pacific_islander NULL/NULL/NULL. **MATCH**.
- **Era 3** — 2023.csv, Savannah-Chatham 625 / Groves High 3056 (cohort 2019). Bronze: `TOTAL 165/49/15`; `MALE 74/15/TFS`; `BLACK 128/38/13`; `PACIFIC_HS_GRADS='TFS'`. Gold: all 165/49/15; male 74/15/NULL; black 128/38/13; pacific_islander NULL. **MATCH**.

**4c Sentinel year-attribution**: year comes from the in-file School Year cell, never the filename, with a hard-fail `filename == cohort + 4` guard. Traced: 2019.xlsx internal `School Year='2015'` → gold year=2015 (Appling row grads `'239'` lands at year=2015, gold 239). All 13 manifest file→year assignments follow the +4 offset. PASS.

**4d Aggregate feasibility screen** (aggregates come from bronze): zero cases of district < max(school) for any metric. 22 cases of district < sum(published school rows) — **every one off by exactly 1** — and 3 state < sum(district) cases (diffs 1, 2, 1 of ~90-104K). Traced to bronze: 2014.xlsx Gwinnett (667) district row `Total All grads='8516'` vs its 18 published school rows summing 8517 (quoted values, Grayson 595 … Duluth 421). The discrepancy is in the source itself (student-level dedup across schools in the district rollup); gold is faithful. No swaps or garbling; `all`-row district-sum coverage of the state total is 0.998-1.000 for all metrics. PASS — source-side artifact, no fix.

**4e Dedup tie-break**: N/A — 13 files map to 13 distinct cohort years (manifest `files_processed`); no overlap years exist. Row conservation (expansion factors exact) confirms dedup removed nothing.

**4f Suppression semantics**: single marker type (`TFS`). Era 1: 2012.xlsx Trion City 791/ALL Black `'TFS','TFS','TFS'` → gold 2008/791/NULL/black NULL/NULL/NULL. Era 2: Echols PI (above). Era 3: Groves `PACIFIC_HS_GRADS='TFS'` → NULL. **MATCH ×3 eras.** Reconciliation proof: gold per-year NULL totals equal the structure doc's bronze TFS counts exactly — 2008: 12,357; 2016: 14,439; 2019: 15,060; 2020: 15,437 (all four documented years MATCH to the cell), so `strict=False` nulled nothing besides TFS.

**ID formatting trace**: 2019.xlsx stores Appling County High as school code `'103'` (unpadded, quoted); gold carries `'0103'` continuously across 2008-2020 with plausible grad counts (163…239…204) — zfill restoration verified against the same school in padded years.

## Validation Cross-Read

- `_validation.json`: **21 pass / 0 fail / 0 warnings**, `passed: true`, fresh (manifest 2026-06-11T01:19:37Z, validation same second). `contract_parquet_schema` (39 files), `contract_quality_sql` (13 checks), `grain_uniqueness`, `foreign_keys` (199 district, 581 school, 14 demographic keys resolve), `geography_nulling` ×3 all pass.
- Contract `schema_hash`: `1f8ff43d66e0f1a904a64985876abc93264b61d63b967a7e12aa1e640496e858`; version 1.0.0.
- **§4b masking audit**: no `_null_*` helpers in transform.py (grep clean), no `masked_values` manifest section, docstring documents the full-scan finding (all published values in [10, 113,189], no impossible values). Consistent — nothing unrecorded. PASS.
- **§15b coverage judgment**: 8 authored quality checks cover the topic's real invariants — three pairwise ordering subsets (earned ≤ enrolled ≤ grads, including the grads-vs-earned pair that survives a suppressed middle), the ≥10 reporting threshold, state core-row completeness, the exact state gender partition, the directional race-bucket bound (doubles as the §5a no-rollup guard), and PI-absence-in-2008. No obvious invariant is missing; the partition checks are pivoted via conditional aggregation, not self-joins. PASS.
- **v1 parity (5d)**, executed output verbatim:

```
MATCH — byte-identical with v1 gold
```

## Cross-Era Consistency

- **Era routing**: 2012→era_1_xlsx (44 cols, no PI), 2013-2022→era_2_xlsx (47 cols), 2023-2024→era_3_csv (48 cols) — manifest `files_processed` matches the structure doc exactly.
- **Era-boundary continuity**: state `all` levels move smoothly across both boundaries (2008: 89,167 → 2009: 85,410 → 2010: 89,304; 2018: 111,296 → 2019: 112,919 → 2020: 113,189). No >10x jumps, no cumulative-publication signature, in any adjacent year pair for any metric.
- **Cross-year NULL sweep (Risk 2)**: zero flags — no column is ~100% NULL in any year-subset, none is all-NULL.
- **2015-2019 state-row literal**: all five files verified to carry literal `'ALL'` in the state row's district cell under dtype=str read (2015: `'ALL'`, 2016: `'ALL'`, 2017: `'ALL'`, 2018: `'ALL'`, 2019: `'ALL'`) — the structure doc's "null district code" was a polars integer-coercion artifact; the transform's correction and its `state_rows != blocks` hard guard are right.
- **Georgia-only scope correction verified against sibling gold**: C11 gold 2016 state all = graduates 103,947 / enrolled 71,095 vs C12 gold 103,950 / 57,468. Same cohort, graduate counts agree within 3, enrollment differs 19% — C12 is Georgia-institutions-only; the structure doc's "in-state or out-of-state" overview line is wrong (copied from C11). The contract/docstring carry the corrected scope.

## Transform Logic Risks

| Risk | Severity | Details |
|---|---|---|
| Silent column drops | PASS | `_blocks_to_long` raises on missing source columns; `_xlsx_blocks` raises on partial (≠3) groups; only name columns excluded (dimension attributes) |
| Era routing correctness | PASS | Signature-based, most-specific-first; manifest assignments all correct; stitcher hard-fails on layout drift (A1 note + ID-label guards) |
| Filter logic | PASS | No row filters (`total_filtered` 0 everywhere); structure guard raises instead of dropping |
| Normalization map completeness | PASS | 27/27 bronze labels mapped via shared aliases; unmapped 0 |
| `strict=False` casts | PASS | Float64 hop tolerates decimal counts; TFS-vs-NULL reconciliation proves zero non-TFS values were nulled (4 years checked exactly) |
| Dedup keys + tie-break | PASS | Safety net only; collision guard runs before dedup; row conservation exact |
| Year extraction | PASS | In-file School Year + hard-fail +4 filename cross-check; traced (4c) |
| §4b masks | PASS | None exist, none needed (full-scan documented); manifest consistent |

## NEEDS_JUDGMENT

### Judgment Call 1: Amend the two stale claims in bronze-data-structure.md

- **Severity if confirmed**: LOW (documentation only — gold data is unaffected and byte-identical with v1)
- **Suspicion**: `bronze-data-structure.md` retains two claims this review proved wrong: (1) the Overview/Summary "enrolled in any postsecondary institution (in-state or out-of-state…)" line — contradicted by the C11 cross-check (71,095 vs 57,468 for the same 2016 cohort, graduates agreeing); (2) the Era 2 / ETL-consideration-6 claim that the 2015-2019 state row's District Code is null — all five files carry the literal `'ALL'` under a string-typed read (the null was a polars integer-coercion artifact of the analysis tooling).
- **Evidence available**: quoted in this review — C11 gold 2016 state row; 2015-2019.xlsx state-row cells all `'ALL'`.
- **Why uncertain**: the structure doc is a generated artifact of `/bronze-data-structure`; whether to hand-amend it, regenerate it, or leave it (the transform docstring + contract already document both corrections prominently) is a process decision above this review's pay grade, and this review may only edit its own report.
- **Location**: `data/bronze/education/gosa/postsecondary_c12_report/bronze-data-structure.md` (Overview line ~64, Era 2 section lines ~145/150, Null Counts ~189, ETL consideration 6)
- **If confirmed, suggested fix**: amend the doc's two claims (with a one-line note that the transform verified the corrections empirically) so a future re-analysis or re-transform doesn't reintroduce the C11-copied scope wording or a null-state-row detection branch.

## Notes

- schema_hash: `1f8ff43d66e0f1a904a64985876abc93264b61d63b967a7e12aa1e640496e858`; validation 21 pass / 0 fail / 0 warnings; read_loss events 0.
- v1 parity: MATCH (byte-identical), so every finding above also held for the approved v1 gold.
- Source-side off-by-one aggregates (not a defect, documented for future reviewers): 22 district rows sit exactly 1 below their published school-row sum and 3 state `graduate_count` cells sit 1-2 below the district sum (e.g., bronze 2014.xlsx Gwinnett 667 district `8516` vs school sum `8517`). Faithful to bronze; consistent with student-level dedup in source rollups; the contract's limitations already direct consumers to official aggregate rows.
- 2009 state `pacific_islander` is NULL — bronze-faithful (2013.xlsx state PI cells are literal `TFS`), consistent with the new-in-2009 race scheme still leaving ~1,779 students race-unclassified.
- Gold layout: 13 year partitions × {schools, districts, states}.parquet = 39 files; detail_level dropped per domain convention.
