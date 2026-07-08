# Data Review: educator_qualifications_out_of_field_teachers

**Date**: 2026-06-11
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Gold is **byte-identical with the approved v1 baseline (parity MATCH)** and every value-level trace, the full 73-row drop-ledger replay, the tiny-FTE rate-deviation claims, and the suppression-era boundary all verify exactly against bronze. The single finding is a **documentation inaccuracy** (LOW): the transform docstring and `bronze-data-structure.md` claim the 2023 Genesis Innovation Academy per-campus values "are not separately published in this topic's 2023 file" — bronze in fact publishes both campuses under bare school names with the exact same metrics, and both rows are present in gold (7830615/0615 and 7830616/0616). The drop decision itself is correct (the truncated twins are redundant); only the stated rationale is factually wrong.

## Manifest Verification

### Categorical mappings (100% coverage)

| Column | Entries | Bronze seen | Unmapped | Status |
|---|---|---|---|---|
| `poverty_subgroup` | 3 | 3 (`High Poverty`, `Low Poverty`, `Total`) | 0 | PASS |

Full map review (every entry):

| Bronze → Gold | Correct? |
|---|---|
| `Total` → `total` | YES — the all-schools stratum (bronze `LABEL_LVL_2_DESC`) |
| `High Poverty` → `high_poverty` | YES — highest-poverty-quartile school stratum |
| `Low Poverty` → `low_poverty` | YES — lowest-poverty-quartile school stratum |

- **2a Completeness**: `bronze_values_seen` exactly matches the structure doc's documented distinct values for `LABEL_LVL_2_DESC` (Total/High Poverty/Low Poverty in both eras). No documented value is missing — no skipped era/routing bug.
- **2b Correctness**: all three recodings are semantically right; the stratum is correctly kept as a topic categorical, NOT mapped into `demographic` (it describes school poverty-quartile membership, not student subpopulations) — consistent with the structure doc and the education domain conventions.
- **2c Contract cross-check**: `gold_values_produced` = `{high_poverty, low_poverty, total}` = the contract `enum` for `poverty_subgroup`. PASS.
- **2d Unmapped**: `unmapped_count = 0`. PASS. (The transform routes unmapped strata to the `99999999` sentinel, which would fail `manifest.write()`.)
- **2e Asian/PI conflation**: **N/A** — the topic has no `demographic` column and no `pct_asian`-style column (verified: gold columns are `year, district_code, school_code, poverty_subgroup, total_fte, out_of_field_fte, out_of_field_fte_rate`). Poverty strata are school strata, not race/demographic buckets.
- **2f Mutual exclusivity**: **N/A** — no demographic column; the analogous stratum invariants (a school never carries both `high_poverty` and `low_poverty`; HP+LP ≤ total at district/state) are authored as contract quality checks and pass.

### Row-count reconciliation

| Year | Bronze | Filtered | Gold | Parquet actual | Status |
|---|---|---|---|---|---|
| 2018 | 3,757 | 0 | 3,757 | 3,757 | PASS |
| 2019 | 3,759 | 0 | 3,759 | 3,759 | PASS |
| 2020 | 3,779 | 0 | 3,779 | 3,779 | PASS |
| 2021 | 3,790 | 0 | 3,790 | 3,790 | PASS |
| 2022 | 3,789 | 0 | 3,789 | 3,789 | PASS |
| 2023 | 3,800 | 73 | 3,727 | 3,727 | PASS (expansion 0.981 explained below) |
| 2024 | 3,708 | 0 | 3,708 | 3,708 | PASS |
| **Total** | **26,382** | **73** | **26,309** | **26,309** | PASS |

**Drop-ledger replay (executed, not trusted).** I re-ran the 2023 file through `_transform_era` → `_attach_codes` → the documented-gap predicates → dedup, independently of the transform run:

- Unresolved-district rows: **37**, all matching `is_state_charter_placeholder_district` (0 source_gap_district, 0 unclassified) — manifest says `state_charter_placeholder_district: 37`. MATCH.
- School-level unresolved after district drops: **4 rows** across 3 name pairs (Lumpkin County Elementary School, Barrow Arts and Sciences Academy, Lindley 6th Grade Academy), every pair returning `is_source_gap_school(...) = True` — manifest says `source_gap_school: 4`. MATCH.
- Duplicate natural keys after drops: **32 keys / 64 rows**, with **0 keys carrying divergent metrics** (all three metrics identical within every pair) → dedup removes exactly **32** rows — manifest says `duplicate_rows_deduped: 32`. MATCH. The pairs are bare-school-name rows + 52-char-truncated `State Charter Schools II- …` republications of the same single-school charter (e.g. `Atlanta Heights Charter School` 31.3/18.2/0.58 twice at key 7830410/0410), so the collision guard's identical-metrics precondition genuinely held.
- Total replayed drops: 37 + 4 + 32 = **73**. MATCH.

**Redundancy of the 37 placeholder drops verified entity-by-entity**: every dropped truncated container row (Atlanta SMART, Atlanta Unbound, Cirrus, Coweta, D.E.L.T.A., DeKalb Brilliance, Fulton Leadership, Furlow, Genesis ×2, Pataula, SLAM, Southwest Georgia S.T.E.M., Statesboro STEAM, Cherokee, Coastal Plains, Dubois Integrity, Foothills, Georgia Connections, Georgia Cyber, Ivy Prep, Mountain Education, Odyssey, Scintilla, Utopian) has a corresponding bare-name school row **in gold 2023 with identical metrics** (e.g. dropped `State Charter Schools- Ivy Prep Academy at Kirkwood ` (29, TFS, 18) vs gold `Ivy Preparatory Academy, Inc` 7820121-era row 29.0/NULL/0.18; dropped `State Charter Schools- Georgia Cyber Academy- All Sc` (599.0, 46.8, TFS) vs gold `Georgia Cyber Academy (Virtual)` 599.0/46.8/NULL). No data loss; double-counting prevented.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| `#CATEGORY_DESC` (Era 1 only) | — | CORRECTLY EXCLUDED — verified-constant `Out_of_Field`; transform raises on any other value |
| `LONG_SCHOOL_YEAR` | `year` | MAPPED — `parse_school_year` ending year; filename cross-checked |
| `SCHOOL_DSTRCT_NM` | `district_code` | MAPPED — name-resolved via shared `_educator_lookups` resolver |
| `INSTN_NAME` | `school_code` | MAPPED — name-resolved; sentinels → detail_level/NULL |
| `LABEL_LVL_3_DESC` | — | CORRECTLY EXCLUDED — verified-constant `Teachers`; transform raises otherwise |
| `LABEL_LVL_2_DESC` | `poverty_subgroup` | MAPPED |
| `FTE` | `total_fte` | MAPPED (both eras) |
| `OUTOFFIELD_FTE` / `CATEGORY_FTE` | `out_of_field_fte` | MAPPED (era-routed) |
| `OUTOFFIELD_FTE_PCT` / `CATEGORY_FTE_PCT` | `out_of_field_fte_rate` | MAPPED (÷100 to 0-1 scale) |

Matches the structure doc's Gold Schema Classification exactly (including its corrected gold names `poverty_subgroup`/`total_fte`/`out_of_field_fte_rate`). No gold column lacks a bronze source; no fact_metric/fact_key is missing. The missing-metric-column guard in `_transform_era` fails loudly if an era's metric pair is absent.

## Value-Level Spot Checks

Extreme rows first (global max/min of every metric), then one ordinary entity per era. All bronze lines quoted verbatim.

| Trace | Bronze (file, quoted) | Expected | Gold | Verdict |
|---|---|---|---|---|
| `total_fte` global max | 2019: `"2018-19","State of Georgia","All Georgia Schools","Teachers","Total",162256.2,18058.9,11` | state row, 162256.2 / 18058.9 / 0.11 | year=2019, district_code NULL, school_code NULL, `total`: 162256.2 / 18058.9 / 0.11 | MATCH (also `out_of_field_fte` global max) |
| `total_fte` + `out_of_field_fte` global min (0.0) | 2020: `"2019-20","DeKalb County","East DeKalb Special Education Center","Teachers","Total",0,0,0` | 0.0 / 0.0 / 0.0 | 644/0503 2020 `total` (+ `high_poverty` mirror): 0.0 / 0.0 / 0.0 | MATCH |
| `out_of_field_fte_rate` global max (1.0) | 2018: `"2017-18","Baker County","Baker County Learning Center","Teachers","Total",1,1,100` and `"…","Richmond County","Lighthouse Care Center of Augusta","Teachers","Total",4,4,100` | 100 → 1.0 | 604/0183 (dim latest name "Baker County Learning Academy") 1.0/1.0/1.0; 721/0107 4.0/4.0/1.0 — the 4 rows at rate=1.0 | MATCH (dim stores latest school name; the code-level bind is correct) |
| `out_of_field_fte_rate` global min (0.0) | covered by East DeKalb 2020 row above (`…,0,0,0`) | 0 → 0.0 | 0.0 | MATCH |
| Era 2 ordinary (2022, Josey High School) | `"2021-22","Richmond County","Josey High School","Teachers","Total",34.8,12.3,35` (+ identical High Poverty row) | 34.8 / 12.3 / 0.35 | 721/3756: 34.8 / 12.3 / 0.35 (both strata mirror) | MATCH |
| Era 1 ordinary + suppression (2024, Hunt Elementary) | `"Out_of_Field","2023-24","Peach County","Hunt Elementary School","Teachers","Total","42.5","TFS","11"` | 42.5 / NULL / 0.11 | 711/0210: 42.5 / NULL / 0.11 | MATCH (TFS → NULL; 4f) |
| Independent cell suppression (2022 state Total) | `"2021-22","State of Georgia","All Georgia Schools","Teachers","Total","104530.4","6509.1","TFS"` | count kept, rate NULL | 104530.4 / 6509.1 / NULL | MATCH — confirms the contract's "GOSA suppresses each cell independently" |
| Genesis twins (2023, dropped) | `"…","State Charter Schools ","State Charter Schools II- Genesis Innovation Academy","Teachers","Total","31.1","20.3","65"` and `…"29.6","23.3","79"` — PLUS bare rows `"Genesis Innovation Academy for Boys"` (31.1/20.3/65) and `"…for Girls"` (29.6/23.3/79) | twins dropped; campuses in gold from bare rows | gold 2023: 7830615/0615 = 31.1/20.3/0.65 (Boys), 7830616/0616 = 29.6/23.3/0.79 (Girls); twins absent | MATCH on data — but see Fix 1: the docstring's "not separately published" rationale is contradicted by the bare rows |

Other executed verifications:

- **Bronze percent is a genuine integer 0–100 in every year** (per-file scan: min 0, max 100, zero non-integer values, zero out-of-range values across all 7 files) — the ÷100 to a bounded `proportion` is correct, and no §4b mask is needed (claim "no impossible values exist in any year" verified).
- **Tiny-FTE deviation claim verified exactly**: 26 rows with `total_fte < 3` deviate from `out_of_field_fte/total_fte` by > 0.015 (worst 0.57); worst deviation at `total_fte >= 3` is **0.012353** across all years — the quality check's `>= 3` scope and 0.015 tolerance are sharp, not decorative.
- **4c sentinel year-attribution**: `year` derives from `LONG_SCHOOL_YEAR` (e.g. the 2023 file's rows carry `"2022-23"` → year 2023), with a filename cross-check that logs on mismatch (none observed: manifest file→year mapping is 1:1 with filenames). PASS.
- **4d aggregate feasibility screen** (aggregates come from bronze; suppression-heavy → impossibly-LOW direction): district `total` row < max school row in only **4 district-years, all 2018**, all single-school charter/state-school districts with sub-1.3% deltas (e.g. Mountain Education 2018: district row 83.6 vs school row 83.8 — bronze quoted: `…,"Mountain Education Center School","Teachers","Total",83.8,20,24` vs `…- All Schools","Teachers","Total",83.6,20.5,25`). These are the **documented 2018 mixed-scope anomaly** straight from bronze, not a transform defect. Same result on `out_of_field_fte` (4 hits, all 2018). PASS.
- **4e dedup tie-break**: no year is covered by two eras (7 files, 7 distinct years) → cross-era N/A. Within-2023 dedup replayed above: all 32 collapsed pairs carry identical metrics, so no tie-break inversion is possible; `sort_col="out_of_field_fte"` is documented and v1-consistent.

## Validation Cross-Read

- `_validation.json`: **20 pass / 0 fail / 1 warning**; `contract_parquet_schema` (21 files), `contract_quality_sql` (all 11 checks), `grain_uniqueness` (year, district_code, school_code, poverty_subgroup), and `foreign_keys` (232 district keys, 2,386 school keys) all pass.
- The single warning is `null_rate_spikes` (6 spikes: `out_of_field_fte` 88.2/78.4/77.5% and `out_of_field_fte_rate` 74.0/55.3/56.1% in 2022/2023/2024 vs 0% median) — **explained**: TFS suppression begins in the 2022 file. Verified by direct bronze count: TFS occurrences per file = 2018: 0, 2019: 0, 2020: 0, 2021: 0, 2022: 6,267, 2023: 5,152, 2024: 5,048. The "suppression starts 2022, NOT 2021" correction is right. Gold null counts tie out to the structure doc's per-column TFS counts exactly (2022: 3,343/2,805/119; 2024: 2,872/2,081/95). Documented in the contract `null_meaning`/`limitations`. Not an issue.
- **schema_hash**: `35a0950217777a14172f8158bc092343fe305e6e0558fd83a6ce487a3203db8f`.
- **§4b masking audit**: no `_null_*` helpers in transform.py; manifest has no `masked_values`/`reclassified` sections (absent = zero events); read_loss: zero events. Consistent — and correct, since the bronze percent range scan found no impossible values to mask.
- **§15b coverage judgment**: 6 authored checks (numerator ≤ denominator; rate reconciliation scoped `total_fte >= 3` @ 0.015; school stratum mirrors total on all 3 metrics; school never in both strata; district/state HP+LP ≤ total + 0.25; exactly 3 state rows/year) + 5 auto-derived = the 11 passing contract checks. This covers every cross-column invariant I could verify by hand — including the ones I independently re-derived from bronze (worst in-scope rate deviation 0.0124 < 0.015; strata-excess 0.1 < 0.25). A full school→district sum reconciliation is **not authorable** for this topic (documented 2018/2019 denominator scope shifts + heavy 2022+ suppression), and the feasibility screen above confirms no impossibly-low aggregates beyond the documented 2018 cases. Coverage adequate.
- **v1 parity** (executed):

```
MATCH — byte-identical with v1 gold
```

## Cross-Era Consistency

- **Era routing**: manifest `files_processed` shows 2018–2022 → `era_2_2018_2022_outoffield_named`, 2023–2024 → `era_1_2023_2024_category_desc`, matching the structure doc. Signature detection is column-based; the Era 1 constant `#CATEGORY_DESC` is asserted before being dropped.
- **Cross-year NULL sweep (Risk 2)**: zero flags — no column is ~100% NULL in any year subset; no column is NULL in every year.
- **State-level YoY continuity (total stratum)**: 118,009.1 → 162,256.2 → 110,800.8 → 112,352.4 → 104,530.4 → 113,416.6 → 113,554.9. The 2019 +37% level is the **documented broad-scope year** (verified at the state row from bronze, quoted above); 2018 school rows sum to 157,557.3 (broad) against the narrow 118,009.1 state row — the documented mixed-scope year. `out_of_field_fte` dips in 2020 (3,180.1) and 2021 (6,281.9) consistent with the documented 2018–2021 zero-spike anomaly (2020: 48% of school rows are literal 0 per the structure doc; gold min stats confirm zeros pass through). No >10x jumps; no unexplained cumulative-publication signature. All anomalies preserved per §4b and documented in contract limitations + column descriptions.
- **Cross-topic trap verified from bronze**: this topic's 2021 state Total `OUTOFFIELD_FTE` = **6,281.9** (`"2020-21","State of Georgia","All Georgia Schools","Teachers","Total",112352.4,6281.9,6`), while the emergency sibling's 2021 bronze publishes **9,796.9** under the same header names — the contract's lineage caveat is accurate and necessary.

## Transform Logic Risks

| Risk | Severity | Verdict / details |
|---|---|---|
| Silent column drops | — | PASS — both dropped constants are asserted constant first (raise on new values) |
| Era routing correctness | — | PASS — signature-based `detect_era_by_columns`; manifest confirms expected file→era map |
| Filter logic logged + justified | — | PASS — every drop class logged + `record_filtered`; replay reproduces 37/4/32 exactly; residual unresolved rows RAISE (`_assert_fully_resolved`) |
| Normalization map completeness | — | PASS — 3/3 strata; sentinel default would fail `manifest.write()` on a new stratum |
| `strict=False` casts | — | PASS — justified (TFS coexists with numerics on all-string read); no stray non-numeric beyond TFS (gold null counts == bronze TFS counts) |
| Dedup keys + tie-break | — | PASS — collision guard before dedup; 0 divergent-metric pairs; documented `sort_col` |
| Year extraction | — | PASS — authoritative `LONG_SCHOOL_YEAR` with filename cross-check |
| §5b masking (unrecorded masks) | — | PASS — no masks exist, none needed (bronze percent verified within [0,100] in all years) |
| Docstring accuracy of the Genesis drop rationale | LOW | FLAG — see Fix 1 (data correct; prose wrong) |

## Required Fixes

### Fix 1: Correct the false "per-campus values are not separately published" claim in the Genesis-twins drop rationale
- **Severity**: LOW
- **Issue**: The transform module docstring (state_charter_placeholder_district bullet: "…the per-campus values are not separately published in this topic's 2023 file") and `bronze-data-structure.md` (Known Anomalies: "…the per-campus values are not separately published elsewhere in the 2023 file") assert a bronze fact that is false. This is documentation-only — gold data is correct and v1-parity MATCH — but the wrong rationale could mislead a future rebuild into believing the Genesis 2023 campus values are unrecoverable.
- **Evidence**: Bronze 2023 publishes the per-campus rows under bare names: `"Out_of_Field","2022-23","State Charter Schools ","Genesis Innovation Academy for Boys","Teachers","Total","31.1","20.3","65"` and `"…","Genesis Innovation Academy for Girls","Teachers","Total","29.6","23.3","79"` — identical metrics to the two dropped truncated twins. Both campuses are in gold 2023: 7830615/0615 = 31.1/20.3/0.65 and 7830616/0616 = 29.6/23.3/0.79. The values therefore ARE separately published and ARE served.
- **Location**: `transform.py` module docstring (the `state_charter_placeholder_district` bullet covering the Genesis twins); same clause in `data/bronze/education/gosa/educator_qualifications_out_of_field_teachers/bronze-data-structure.md` "2023 duplicate bronze name key" anomaly.
- **Suggested fix**: Replace the clause with the accurate rationale: the per-campus values ARE separately published under bare school names and reach gold through those rows; the truncated twins are exact republications whose campus distinguisher was erased, so attributing either twin to a single dimension target is unnecessary (and ambiguous) — dropping both loses nothing. Prose-only change; re-running the transform must leave gold byte-identical (same schema_hash).

## Notes

- schema_hash: `35a0950217777a14172f8158bc092343fe305e6e0558fd83a6ce487a3203db8f`; contract `version: 1.0.0`.
- Validation: 20 pass / 0 fail / 1 warning (null_rate_spikes — the documented 2022 TFS suppression boundary, explained above).
- Preconditions: artifacts FRESH (transform mtime 18:41:20 < manifest 18:41:58 ≤ validation 18:41:58); zero read-loss events; no masked/reclassified sections.
- v1 parity: MATCH (byte-identical), so this review's findings cannot indicate a regression vs the approved baseline.
- The 4 source_gap_school drops span 3 name pairs (one pair contributes two strata rows); all three return `is_source_gap_school = True` from the shared, parity-verified resolver module, which this review treated as read-only.
- Dim names are latest-name-only, so two traced entities surface under newer names than bronze (Baker County Learning Center → "Baker County Learning Academy"; Foothills Charter High School (Central Office…) → "Foothills Regional High School"); the code-level binds verify correct via matching metrics.
