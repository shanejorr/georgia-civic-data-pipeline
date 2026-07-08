# Data Review: hope_eligible_graduates

**Date**: 2026-06-11
**Reviewer**: Claude (automated data review)
**Status**: NEEDS_JUDGMENT

## Summary

Every value-level check passed: all extreme-row and per-era traces match bronze exactly, all 8
2004 trailing-x merges sum correctly, all 174 derived 2004 district rows and all 179 derived
2008 district rows reconcile (the 2008 set was verified against the bronze System Level sheet
the transform deliberately does not read — counts and rates match to 1e-9), and the derived
2008 state row equals the bronze State Level sheet to the float bit (0.3854773259449055).
**v1 parity: MATCH — byte-identical with v1 gold.** No Required Fixes. One LOW-severity
judgment item: the contract attributes all metric NULLs to TFS suppression, but 2011–2020
graduate_count NULLs (and all 2014/2020 NULLs) come from blank bronze cells, not the TFS
literal — a documentation-precision gap, not a data defect.

## Manifest Verification

Preconditions: artifacts FRESH (transform mtime 02:26:18 < manifest 02:26:29 ≤ validation
02:26:29), `_validation.json` `passed: true` (21 pass / 0 fail / 0 warning), `read_loss`
events: 0.

### Categorical mappings

| Column | Entries | Bronze seen | Unmapped | Status |
|---|---|---|---|---|
| `detail_level` (Era 1 only) | 3 | 3 (`DISTRICT`, `SCHOOL`, `STATE`) | 0 | PASS |

Full map review:

| Bronze | Gold | Correct? |
|---|---|---|
| `STATE` | `state` | Yes — statewide rollup (1 per year in 2023/2024 bronze) |
| `DISTRICT` | `district` | Yes — district rollup (196 per year) |
| `SCHOOL` | `school` | Yes — school rows |

`gold_values_produced` = {district, school, state} — matches the contract's `detail_levels`
custom property (schools/districts/states; `detail_level` itself is encoded in the per-year
file split, correctly not a contract column). All other eras derive level from the `ALL`
sentinels / NULL patterns (no recode map needed); Era 4 derives aggregates structurally.

- 2e Asian/PI conflation: **N/A** — no `demographic` column in gold (`SKIP: no demographic
  column`), and `grep -icE 'pacific[ _-]?islander|...|asian'` over the structure doc returns 0.
- 2f Mutual exclusivity: **N/A** — no demographic column.

### Row-count reconciliation

| Year(s) | Bronze | Gold | Explanation |
|---|---|---|---|
| 2004 | 348 | 513 | −1 junk footer, −8 x-rows merged into siblings (338 schools), +174 derived districts, 1 state. 338+174+1 = 513 ✓ |
| 2005–2007, 2009–2022 | n | n | 1:1 pass-through (bronze ships all three levels) |
| 2008 | 382 | 556 | −5 null-School-ID rows (4 folded into aggregates, 1 orphan dropped), −1 Westside row merged → 376 schools, +179 derived districts, +1 derived state. 376+179+1 = 556 ✓ |
| 2023–2024 | 665/667 | 665/667 | 1:1 |

Manifest `total_gold` 12,771 = actual parquet row sum 12,771 ✓. Filtered ledger (11):
1 footer junk + 8 x-subtally merged + 1 orphan (Renaissance) + 1 Westside merged; reclassified
4 (2008 fold rows). All accounted.

## Column Coverage

| Bronze column(s) | Gold column | Status |
|---|---|---|
| `SCHOOL_DISTRCT_CD` / `System ID` / first half of composite key | `district_code` | MAPPED (zfill 3; 7-digit codes pass through) |
| `INSTN_NUMBER` / `School ID` / second half of composite key | `school_code` | MAPPED — structure doc proposed `instn_number`; domain CLAUDE.md mandates `school_code`. Correct supersession. |
| `NUMBER_OF_GRADUATES` / `Number of Graduates` / `Number of 2004 Graduates` / `Number of Regular Graduates - Report Card` | `graduate_count` | MAPPED |
| `HOPE_ELIGIBLE` / `Number Eligible` / `# Eligible for HOPE 2008` | `hope_eligible_count` | MAPPED |
| `HOPE_ELIGIBLE_PCT` / `Percent Eligible` | `hope_eligible_rate` | MAPPED — structure doc proposed `hope_eligible_pct` at 0–100; §16 `…_rate` on 0–1 wins. Correct supersession. |
| `DETAIL_LVL_DESC` | `detail_level` → file split | MAPPED (dropped from columns per domain convention) |
| `#RPT_NAME`, `LONG_SCHOOL_YEAR`, `Data Year`, `Report Card Year`, `Data Type`, `Report Card Section` | — | CORRECTLY EXCLUDED (constants / asserted against filename year) |
| `SCHOOL_DSTRCT_NM`, `INSTN_NAME`, `System Name`, `School Name`, `SchoolNme`, `System/School Name` | — | CORRECTLY EXCLUDED (dimension attributes) |
| Composite `SYSSCHOOLID`/`Sysschoolid`/`SysSchoolID` | — | CORRECTLY EXCLUDED (split into the two key columns) |

No gold column lacks a bronze source (no fabrication). 2008 `System Level`/`State Level`
sheets correctly skipped (verified below as exact pre-aggregations).

## Value-Level Spot Checks

All verdicts below quote executed bronze reads. **Every trace: MATCH.**

Extreme rows first:

| Trace | Bronze | Gold | Verdict |
|---|---|---|---|
| graduate_count + hope_eligible_count global max — 2024 state | `ALL/All Systems/ALL/All Schools, 119530, 59349, 49.65` | `(2024, NULL, NULL) → 119530, 59349, 0.4965` | MATCH |
| graduate_count global min = 0 — 2008 Regional Evening School 678/0193 | `0 eligible, 0 graduates, Percent Eligible = None` (blank div-by-zero cell) | `0, 0, NULL` (rate NULL via `graduate_count > 0` guard; the single 2008 rate NULL in the manifest) | MATCH |
| hope_eligible_count min = 0 — 2007 `676:300` Houston Co Career & Tech | `56, 0, 0` | `(2007, 676, 0300) → 56, 0, 0.0` | MATCH (also `676:3050` 5/0/0 and `799:1893` 2/0/0) |
| hope_eligible_rate max = 1.0 — 2006 `625:499` Savannah Arts Academy | `113, 113, 100` | `(2006, 625, 0499) → 113, 113, 1.0` | MATCH |
| hope_eligible_rate max = 1.0 — 2008 799/1894 Georgia Academy for the Blind | `1 eligible, 1 graduate, 100` | rate 1.0 (recomputed 1/1) | MATCH |
| hope_eligible_rate min = 0.0 — 2007 `676:300` | `Percent Eligible = '0'` | `0.0` | MATCH |

Ordinary entity per era:

| Era | Bronze | Gold | Verdict |
|---|---|---|---|
| 1 (2024) Ware Co HS 748/0195 | `335, 170, 50.75` | `335, 170, 0.5075` | MATCH |
| 2 (2015) Gwinnett Sch of Math 667/1019 | `183, 112, 61.2` | `183, 112, 0.612` | MATCH |
| 2 (2015) district 601 `ALL` row | `239, 110, 46.03` | `(601, NULL) → 239, 110, 0.4603` | MATCH |
| 2 (2015) unpadded `103` → `0103` (Atkinson 602) | `83, 45, 54.22` | `(602, 0103) → 83, 45, 0.5422` | MATCH (zfill verified) |
| 3 (2010) Rockmart `715:102` | `130, 41, 31.5` | `(715, 0102) → 130, 41, 0.315` | MATCH |
| 4 (2008) Appling 601, `School ID` numeric cell `103` | `145, 62, 42.758620689655174` | `(601, 0103) → 145, 62, 0.42758620689655175` | MATCH (rate recompute is a no-op as claimed) |
| 5 (2007) Trion `791:301` | `87, 37, 42.5` | `(791, 0301) → 87, 37, 0.425` | MATCH |
| 6 (2006) Towns Co HS `739:204` | `60, 43, 71.7` | `(739, 0204) → 60, 43, 0.717` | MATCH |
| 7 (2004) Social Circle `786:300` | `72, 36, 50.0` | `(786, 0300) → 72, 36, 0.5` | MATCH |
| 7 (2005) Towns Co HS `739:204` | `70, 53, 75.7` (2004 file has `54, 45, 83.3` for the same school) | gold 2005 → `70, 53, 0.757`; gold 2004 → `54, 45, 0.833` | MATCH — stale-header year attribution correct (Risk 3) |

2004 trailing-x merge — **all 8 pairs verified arithmetically**, e.g.:

- `644:775x` Open Campus HS `17, 5, 29.4` + sibling `644:775` `535, 129, 24.1` → gold
  `(644, 0775) → 552, 134, 0.2427536…` = (17+535, 5+129, 134/552) ✓
- `622:2052x` Central HS `176, 113` + `622:2052` `181, 112` → gold `357, 225, 0.6302521…` ✓
- Remaining 6 pairs (631:290, 644:3060, 669:4752, 747:4050, 755:191, 761:3055) all sum
  correctly; every x-row has a same-named canonical sibling (verified in the executed output).

Aggregate reconciliation (Risk 4 — the topic's biggest risk):

- **2004 derived districts (FULL check)**: all 174 district rows equal their school sums for
  both counts; 0 rate mismatches at 1e-12 (rate = sum(e)/sum(g), graduate-weighted — no
  `.mean()` on percentages anywhere). Spot: district 644 (DeKalb, contains 2 merged x-pairs)
  → `4813, 3007` = school sum `4813, 3007` ✓.
- **2004 state preserved as published**: gold `68163, 42233, 0.62`; school sums `68029, 42146`
  → gap 134 graduates / 87 eligible (~0.2%), exactly the documented bronze artifact.
- **2008 derived state vs bronze State Level sheet** (sheet not read by the transform):
  bronze `31443, 81569, 38.547732594490554` → gold `81569, 31443, 0.3854773259449055`.
  Exact to the float bit.
- **2008 derived districts vs bronze System Level sheet (FULL independent check)**: all 179
  gold district rows match the 179 bronze System Level rows on both counts and rate
  (tolerance 1e-9, 0 mismatches). This is the strongest evidence available — GOSA's own
  pre-aggregation reproduced exactly, including the 4 folded null-School-ID rows.
- **2008 fold rows**: bronze null-School-ID rows quoted: Carver Comprehensive (761, 93/22),
  D M Therrell (761, 123/19), Fayette Evening (656, 3/0), Houston Crossroads (676, 7/1).
  District 761: school-row sum `1628, 508` + folds `216, 41` = gold `1844, 549, 0.29772234`
  = bronze System Level `1844, 549, 0.2977223427331887` ✓.
- **2008 Westside pair**: bronze `WESTSIDE HIGH SCHOOL 241/61` + `WESTSIDE COMPREHENSIVE HIGH
  SCHOOL 140/30` under shared key 721/2574 → gold `381, 91, 0.2388451…` = (241+140, 61+30,
  91/381) ✓.
- **Renaissance Academy**: fully orphaned bronze row (`System ID = None`, 28 graduates /
  0 eligible) absent from gold 2008 at every level (0 matching school rows); its exclusion is
  what makes the derived state equal the bronze State Level total. ✓
- **2005 bronze rollups pass through, not derived**: bronze `648:ALL` (Douglas County)
  `999, 630, 63.1` → gold `(2005, 648, NULL) → 999, 630, 0.631` ✓.

Suppression traces (4f):

- Full TFS, 2022 line 653 (quoted raw): `"2021-22","799","State Schools","1894","Georgia
  Academy for the Blind","TFS","TFS","TFS"` → gold `(2022, 799, 1894) → NULL, NULL, NULL` ✓.
- Partial TFS, 2015 line 563: `761,...,508,"Therrell School of Law...",48,TFS,16.67` → gold
  `(2015, 761, 0508) → 48, NULL, 0.1667` ✓ (graduates and published rate preserved, eligible
  censored — co-null quality check semantics confirmed in the data).
- 2004 junk footer: 1 bronze row with NUL-padded `SYSSCHOOLID` (`'\x00\x00…'`) and all-null
  fields — absent from gold; 2004 gold = 513 rows exactly as reconciled above. ✓

Dedup tie-break (4e): **N/A** — 21 files, 21 distinct years (manifest `files_processed`),
no overlap years; `sort_col="graduate_count"` is a defensive net only, and
`assert_no_natural_key_collisions` runs before it.

## Validation Cross-Read

- `_validation.json`: 21 pass / 0 fail / 0 warning; `contract_parquet_schema` (63 files),
  `contract_quality_sql` (all 8), `grain_uniqueness` (year, district_code, school_code),
  `foreign_keys` (district_code → districts: all 203 resolve; school_code → schools: all 623
  resolve), geography_nulling ×3 — all pass.
- `schema_hash`: `9e0a478cd9c2089ec4bd5fd9e951cbbc796901bda917559f97cae6f40e3e85ef`.
- §4b masking audit: transform contains no `_null_*` helpers; manifest has no `masked_values`
  section; docstring claims "No §4b masks" — consistent. All values physically possible
  (validator range checks pass; measured global max |rate − e/g| = 0.0005 over 11,977
  three-metric rows, exactly the contract's documented bound, occurring on 1-decimal-rounded
  2004/2007 rows).
- §15b coverage judgment: the 4 authored checks (eligible ≤ graduates; rate ≈ e/g within
  0.005; suppression co-null; exactly one state row per year) plus the 4 auto-derived
  unit/range checks cover the real cross-column invariants. A district-equals-school-sum check
  is intentionally not authorable as a hard invariant (the published 2004 state row breaks it
  by ~0.2%, and bronze-published rollups in other years are preserved as published). Adequate.
- v1 parity (verbatim): `MATCH — byte-identical with v1 gold`.

## Cross-Era Consistency

- Overlap years: none (each file = one year).
- Cross-year NULL sweep: clean — no column ~100% NULL in any year subset, none NULL in all
  years (Risk 2 ruled out).
- Era-boundary continuity: state graduate_count grows smoothly 68,163 (2004) → 119,530
  (2024) with no >10x jumps and no revert-style level shifts. The only level shifts are
  hope_eligible_count (ratio 0.648) and hope_eligible_rate (ratio 0.618) at 2006→2007 — the
  documented real GSFC methodology change (HOPE GPA from electronic transcripts), preserved
  as published and prominently caveated in the contract description and notes.
- Era 2 padding drift (unpadded `103` in 2011–2013/2015–2019 vs padded `0103` elsewhere)
  normalized via zfill(4) — verified by trace; FK check confirms all school keys resolve.

## Transform Logic Risks

| Risk | Severity | Details |
|---|---|---|
| Silent column drops | PASS | All drops enumerated per era; constants asserted (`LONG_SCHOOL_YEAR`, `Data Year`) before dropping |
| Era routing correctness | PASS | Manifest `files_processed` eras match design (Era 1 superset listed first; Eras 5/7 disambiguated by graduate-column name); detection raises on no-match |
| Filter logic logged + justified | PASS | 11 filtered + 4 reclassified rows, all manifest-recorded with reasons; junk-footer filter (`SchoolNme` null) verified to touch only the 1 junk row (2005 has zero null names) |
| Normalization map completeness | PASS | Single 3-entry detail_level map, complete vs structure doc |
| `strict=False` casts | PASS | Net behind read-time TFS nulling; residual nulls traced to genuine bronze blanks (see judgment item), not lost numerics |
| Dedup keys + tie-break | PASS | Collision guard before dedup; no overlap years; era-internal merges are sums, not dedups |
| Year extraction | PASS | Filename canonical; LONG_SCHOOL_YEAR / Data Year asserted equal (raises on drift); 2005 stale header traced correct |
| §4b/§5b masks | PASS | None used, none needed; manifest consistent |

## NEEDS_JUDGMENT

### Judgment Call 1: Contract attributes all metric NULLs to TFS suppression, but 2011–2020 NULLs are (partly or wholly) blank bronze cells

- **Severity if confirmed**: LOW
- **Suspicion**: The contract's `graduate_count` description says "NULL when suppressed in
  bronze (TFS = Too Few Students, … affects 2009 and 2011-2024)" and the suppression note
  says full three-metric suppression occurs in "2009, 2021-2024; only hope_eligible_count
  and/or the rate in 2011-2013 and 2015-2019". Both statements imply the TFS literal is the
  sole NULL mechanism. Measured bronze: 2014 has **0** TFS occurrences yet 12/21/21 blank
  cells (graduates/eligible/pct); 2020 has **0** TFS yet 24/37/37 blanks; 2015 mixes 34 TFS
  (eligible only) with 12/25/25 blanks — and every gold NULL count decomposes exactly into
  TFS + blanks (2015 eligible: 34 + 25 = 59 = manifest null_count). Blank rows are real
  schools with no published metrics (e.g., 2015 line 120: `2014-15,633,Cobb County,807,
  Devereux Ackerman Academy,,,`) — fully-null rows therefore DO exist in 2011–2020, and 2014/
  2020 NULLs are entirely blank-driven. The structure doc's "0 nulls across all 8 columns"
  claim for 2011–2022 is likewise imprecise.
- **Evidence available**: TFS counts per file (2011: 34, 2012: 42, 2013: 37, **2014: 0**,
  2015: 34, 2016: 34, 2017: 27, 2018: 31, 2019: 30, **2020: 0**); per-column TFS/blank split
  quoted above; gold NULLs faithfully mirror bronze in every traced case.
- **Why uncertain**: The gold **values** are correct (NULL faithfully represents missing
  bronze data either way), so this is purely a metadata-precision question: whether blank
  cells are unpublished/unreported programs (semantically different from "suppressed small
  cohort") matters to users predicting NULL patterns, but GOSA does not document the blanks'
  meaning. Fixing prose would not change gold bytes (v1 parity and approval hashes cover
  .parquet only).
- **Location**: `_emit_contract_and_readme()` in transform.py — `graduate_count` /
  `hope_eligible_count` / `hope_eligible_rate` descriptions and the "Suppression" note.
- **If confirmed, suggested fix**: Add one sentence to the suppression note (and soften
  "affects 2009 and 2011-2024" in the column descriptions): a small number of rows per year
  in 2011–2020 (9–24 graduate_count, up to 37 eligible/rate) carry blank metric cells in
  bronze — unreported special programs / treatment centers — which are also NULL in gold;
  2014 and 2020 contain no TFS literals at all.

## Notes

- `schema_hash`: `9e0a478cd9c2089ec4bd5fd9e951cbbc796901bda917559f97cae6f40e3e85ef`;
  validation 21 pass / 0 fail / 0 warning; manifest generated 2026-06-12T02:26:29Z.
- v1 parity MATCH (byte-identical) — every interpretive decision (2008 school-only read +
  derived aggregates, 2004 x-merges + derived districts, Renaissance exclusion, Westside sum,
  filename-year-wins) reproduces the approved v1 gold exactly.
- The transform's claim that the 2008 rate recompute is a semantic no-op held in the traced
  rows (bronze `42.758620689655174` ÷ 100 vs 62/145 — identical), and the full System Level
  reconciliation at 1e-9 bounds any residual ulp noise.
- The 2006→2007 series break (state rate 0.617 → 0.381) is real, externally documented
  (GSFC-calculated HOPE GPA), and prominently caveated — correctly preserved, not "fixed".
- Asian/PI and demographic mutual-exclusivity risks: N/A (no demographic axis in any era).
