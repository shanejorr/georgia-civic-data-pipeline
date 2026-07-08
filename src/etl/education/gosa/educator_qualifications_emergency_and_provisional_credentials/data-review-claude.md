# Data Review: educator_qualifications_emergency_and_provisional_credentials

**Date**: 2026-06-11
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Gold is byte-identical with the approved v1 baseline (**v1 parity: MATCH**) and every value-level trace across all three eras matched bronze exactly, including the curated-pin bindings and the 73 documented 2023 drops (replayed independently: 44 placeholder + 4 source-gap + 25 identical-metric dedups, 0 residual unresolved). The Era 3 OUTOFFIELD→Emergency rename is proven from bronze (this topic's 2021 state total 9,796.9 vs the out-of-field topic's 6,281.9 over the same 112,352.4 denominator). One Required Fix (MEDIUM, documentation-only — gold values unchanged): the 2018 file publishes school-level rows on the broad teacher-population scope (statewide school sum 157,557.3 = 1.335× the state row 118,009.1; Gwinnett schools sum to 22,190.6 vs the district aggregate 11,170 — bronze-faithful) while district/state rows are on the narrow scope; only the 2019 statewide shift is documented in the contract.

## Manifest Verification

| Column | Map entries | Bronze values seen | Unmapped | Status |
|---|---|---|---|---|
| poverty_subgroup | 3 | 3 (`Total`, `High Poverty`, `Low Poverty`) | 0 | PASS |

Full map review (every entry):

| Bronze → Gold | Semantically correct? |
|---|---|
| `Total` → `total` | YES — all schools in the entity |
| `High Poverty` → `high_poverty` | YES — highest-poverty-quartile school stratum |
| `Low Poverty` → `low_poverty` | YES — lowest-poverty-quartile school stratum |

- **2a Completeness**: structure doc documents exactly these 3 values in every era; all 3 in `bronze_values_seen`. No documented value missing.
- **2c Contract cross-check**: `gold_values_produced` {high_poverty, low_poverty, total} == contract enum. PASS.
- **2d Unmapped**: 0 (sentinel default `"99999999"` would surface any new stratum). PASS.
- **2e Asian/PI conflation**: N/A — no `demographic` column, no `pct_asian`. `poverty_subgroup` is a school-poverty stratum, correctly NOT mapped to the demographics dimension (validator: "No demographic column (skipped)").
- **2f Mutual exclusivity**: N/A — no demographic column; strata disjointness enforced by `school_never_in_both_poverty_strata` (passing).

Row-count reconciliation (manifest vs structure doc vs parquet):

| Year | Bronze | Gold | Filtered | Notes |
|---|---|---|---|---|
| 2018 | 3,757 | 3,757 | 0 | == structure doc |
| 2019 | 3,759 | 3,759 | 0 | == structure doc |
| 2020 | 3,779 | 3,779 | 0 | == structure doc |
| 2021 | 3,790 | 3,790 | 0 | == structure doc |
| 2022 | 3,789 | 3,789 | 0 | == structure doc |
| 2023 | 3,800 | 3,727 | 73 | 44 state_charter_placeholder_district + 4 source_gap_school + 25 duplicate_rows_deduped |
| 2024 | 3,708 | 3,708 | 0 | == structure doc |

Parquet row count = **26,309** == manifest `total_gold`. Expansion factor 1.0 everywhere except 2023 (0.9808, fully explained). The 73 drops were **independently replayed** through `EducatorNameResolver` + the drop predicates: exactly 44/0/4/25 reproduced; the 4 source-gap rows are Barrow Arts and Sciences Academy ×2 (cert personnel 2023 publishes BOTH 0300 and 0309 under that name — genuinely ambiguous; resolves to 0300 in 2021/2022/2024), Lindley 6th Grade Academy ×1, Lumpkin County Elementary School ×1 (both lack 2023 cert-personnel evidence; resolved year-aware in 2018–2022 to 633/0309 and 693/2050). All 25 dedup groups had **identical metrics** (0 divergent groups — collision guard semantics verified empirically).

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| #CATEGORY_DESC (Era 1) | — | CORRECTLY EXCLUDED — constant `Emergency`, asserted before drop |
| LONG_SCHOOL_YEAR | year | MAPPED (ending year via `parse_school_year`) |
| SCHOOL_DSTRCT_NM | district_code (lookup source) | MAPPED; name itself is a dimension attribute, correctly excluded |
| INSTN_NAME | school_code (lookup source) | MAPPED; name correctly excluded |
| LABEL_LVL_3_DESC | — | CORRECTLY EXCLUDED — constant `Teachers`, asserted before drop |
| LABEL_LVL_2_DESC | poverty_subgroup | MAPPED |
| FTE | total_fte | MAPPED |
| OUTOFFIELD_FTE / Emergency_FTE / CATEGORY_FTE | emergency_fte | MAPPED (unified across eras) |
| OUTOFFIELD_FTE_PCT / Emergency_FTE_PCT / CATEGORY_FTE_PCT | emergency_fte_rate | MAPPED, ÷100. Structure doc suggested `emergency_fte_pct`; `_rate` is the §16-canonical name for a 0–1-scale column — correct deviation |

No gold column lacks a bronze source.

## Value-Level Spot Checks

Extreme rows first (global max/min of every metric), then one ordinary entity per era. All MATCH.

| # | Trace | Bronze (file, quoted) | Gold | Verdict |
|---|---|---|---|---|
| 1 | total_fte / emergency_fte global max | 2019 state Total: `FTE=162256.2, OUTOFFIELD_FTE=13743.3, PCT=8` (+ HP `37077.2/3531.8/10`, LP `58745.9/4368.3/7`) | (2019, NULL, NULL): 162256.2 / 13743.3 / 0.08; HP 0.1; LP 0.07 | MATCH |
| 2 | total_fte global min (0.0, 2020) | 5 schools publish `FTE=0, OUTOFFIELD_FTE=0, PCT=0`, e.g. Fulton "Georgia Baptist Children's Home and Family Ministries" | 10 gold rows incl. (660, **0307**) 0.0/0.0/0.0 — also proves the Baptist alias covers 2020, the one year cert personnel lacks the school | MATCH |
| 3 | emergency_fte_rate global max (1.0, 2018) | DJJ "Macon Youth Development Campus" `FTE=5, OUTOFFIELD_FTE=5, PCT=100` | (891, 0598) 5.0/5.0/1.0 ×2 strata | MATCH |
| 4 | total_fte min 2018 (1.0) | "Baker County Learning Center" `1/0/0` (alias → Learning Academy); "Habersham Success Academy" `1/0/0` | (604, 0183) ×2 + (668, 0114) ×1, all 1.0/0.0/0.0 | MATCH |
| 5 | Era 3 ordinary | 2018 Appling "Altamaha Elementary School" `29.2/1.5/5` | (601, 1050) 29.2/1.5/0.05 | MATCH |
| 6 | Era 2 ordinary | 2022 Richmond "Josey High School" `34.8/10/29` (Total + HP) | (721, 3756) 34.8/10.0/0.29 ×2 | MATCH |
| 7 | Era 1 district aggregate | 2024 "Dalton Public Schools- All Schools" HP `276.1/23/TFS`, Total `590.1/42/TFS` | (772, NULL) 276.1/23.0/NULL; 590.1/42.0/NULL | MATCH |
| 8 | 4f suppression | 2024 Peach "Hunt Elementary School" `42.5/TFS/TFS` | (711, 0210) 42.5/NULL/NULL. Peach's dim has TWO "Hunt Elementary School" rows (0210, 0391); cert personnel 2024 carries only 0210 — year-aware disambiguation correct | MATCH |
| 9 | Pin: Obama | 2023 DeKalb `Barack H. Obama Elementary Magnet School of Technolo` (52-char trunc) `46/TFS/TFS` | (644, 1103) = dim "Barack H Obama Elementary Magnet Sc", 46.0/NULL/NULL | MATCH |
| 10 | Pin: Usher | 2023 APS `Bazoline E. Usher/Collier Heights Elmentary School` (typo) `37.9` | (761, 0604) = dim "Bazoline E Usher Collier Heights El", 37.9 | MATCH |
| 11 | Pin: SAIL | 2023 placeholder district `State Charter Schools ` + `SAIL Charter Academy - School for Arts-Infused Learn` `37` | (7830618, 0618) = dim "Sail Charter Academy - School For A", 37.0 ×2 (LP + Total); absent 2024 = absent in bronze | MATCH |
| 12 | Pins: Coretta / Fitzgerald | bronze misspelled/truncated forms all years | (761, 1410) "Coretta Scott King Young Womens Lea"; (609, 0291) "Fitzgerald High School College And" — rows present every bronze year | MATCH |
| 13 | CCAT/Statesboro continuity | district label "Commission Charter Schools- CCAT School" (2018–20) → "State Charter Schools II- Statesboro STEAM Academy" (2021+); 2020 bronze publishes school "Statesboro STEAM Academy" UNDER the CCAT label | all bind to (7830103, 0103); district agg == school row (single-school district) | MATCH |

- **4c sentinel year-attribution**: year derives from `LONG_SCHOOL_YEAR` (the only year-bearing string), filename is cross-check only; traces 1/5/6/7 confirm `2017-18`→2018, `2018-19`→2019, `2021-22`→2022, `2023-24`→2024. PASS.
- **4d feasibility screen** (aggregates COME FROM BRONZE): state vs Σdistricts reconciles 0.98–1.00 for 2019–2024 (deficits consistent with TFS suppression and the 2023 placeholder-aggregate drops); district vs Σschools reconciles to ≤0.3% median in 2019–2024. **2018 does not reconcile** (see Fix 1) — verified bronze-faithful. Impossibly-low screen: 19 rows where a district stratum FTE < its max member-school FTE, mostly 0.1–0.5 rounding; largest (Griffin-Spalding 2019 LP: district `27` vs school Crescent Road `35.8`) quoted directly from bronze — source-side, preserved faithfully.
- **4e dedup tie-break**: no era-overlap years (one file per year) — N/A for era overlap; the 2023 republication dedup verified above (identical metrics in all 25 groups, e.g. (7820614, 0614) "International Charter School of Atlanta" bare + truncated container forms).

## Validation Cross-Read

- `_validation.json`: **21 pass / 0 fail / 0 warnings**, `passed: true` (2026-06-11T05:25:10Z, fresh vs manifest). `contract_parquet_schema`, `contract_quality_sql` (11 checks), `grain_uniqueness` (year, district_code, school_code, poverty_subgroup), `foreign_keys` (232 district + 2,386 school keys resolve) all pass.
- `schema_hash`: `2c38701537a70afc578be7768152b086b8ed0f90687c4d3ac63762856fac0ab8`.
- **§4b masking audit**: no `_null_*` helpers in transform.py; no `masked_values` section in the manifest; no `read_loss` events. Nothing masked — consistent with the docstring claim that no impossible values exist (rate verified within [0,1]; empirical worst rate deviation re-computed from gold = **0.012105** at (2020, 669 Hall, 0392 "The Foundry", 1.9 FTE) — exactly the documented 0.0121; worst strata excess re-computed = **0.1** at Greene (666) 2021/2022 and Richmond (721) 2021 — exactly as documented).
- **§15b coverage judgment**: 6 authored checks (numerator≤denominator, rate reconciliation ±0.015, school-stratum-mirrors-total, strata disjointness, HP+LP≤Total+0.25, exactly-3-state-rows) + 5 derived. Strong coverage; a district≈Σschools check is NOT authorable (suppression + the 2018 source-side scope split would fail it) — correctly absent.
- **v1 parity** (verbatim): `MATCH — byte-identical with v1 gold`.

## Cross-Era Consistency

- No overlap years between eras; era routing by exact column signature, manifest `files_processed` eras match the structure doc.
- Cross-year NULL sweep: no column ≥95% NULL in any year; no 100%-NULL columns. The 2021 suppression boundary (emergency_fte null 0% → 83%) is era-asymmetric TFS suppression, documented in contract `null_meaning`/limitations.
- State-level continuity: no >10x jumps. 2019 level shift (+37% total_fte, reverting 2020) matches the cumulative/scope-shift signature and is preserved + documented at the column and notes level. The related, *undocumented* 2018 school-level scope inconsistency is Fix 1.
- Era 3 mislabeling correction verified from bronze: emergency topic 2021 state `OUTOFFIELD_FTE=9796.9` vs out-of-field topic 2021 state `OUTOFFIELD_FTE=6281.9, PCT=6` (6,281.9/112,352.4 ≈ 6% — internally consistent with the genuine out-of-field metric). The rename is correct and must stand.

## Transform Logic Risks

| Risk | Severity | Details |
|---|---|---|
| Silent column drops | PASS | Constants asserted (`#CATEGORY_DESC`, `LABEL_LVL_3_DESC`) before drop; rename-coverage guard raises on missing metric columns |
| Era routing | PASS | Signature detection, most-specific first; unmatched columns raise |
| Filter logic logged + justified | PASS | All drops manifest-recorded per reason; independently replayed 44/0/4/25 |
| Normalization map completeness | PASS | 3/3 bronze values; sentinel default surfaces new strata |
| `strict=False` casts | PASS | All-string read; TFS is the only non-numeric per structure doc; metric ranges contract-enforced |
| Dedup keys + tie-break | PASS | Collision guard before dedup; 2023 dups verified identical-metric; tie-break documented as defensive |
| Year extraction | PASS | `LONG_SCHOOL_YEAR`-derived, filename cross-check warns on mismatch |
| §5b masking | PASS | No masks; none needed |

## Required Fixes

### Fix 1: Document the 2018 school-level vs district/state scope inconsistency
- **Severity**: MEDIUM
- **Issue**: In the 2018 file ONLY, school-level rows are published on the broad teacher-population scope while district and state rows are on the narrow scope, so school rows do not reconcile with their own district/state aggregates — and nothing in the contract warns consumers. Statewide: Σ(school Total rows) = 157,557.3 vs state row 118,009.1 (ratio 1.335); per-district median ratio 1.027, p90 1.216, max 1.99. Every other year (2019–2024) reconciles within ~0.3% (2019 is uniformly on the broad scope, which IS documented).
- **Evidence**: bronze 2018: `Gwinnett County- All Schools, Total, FTE=11170` while Gwinnett's 137 school rows sum to 22,190.6 (e.g. `Discovery High School, FTE=431.0`, `Norcross High School, FTE=425.5`); Σdistrict rows 122,988.0 also exceeds the state row 118,009.1 (1.042). Gold mirrors bronze exactly — the values are correct; the caveat is missing.
- **Location**: `_emit_contract_and_readme()` in transform.py (`limitations` and the 2019-anomaly `notes` entry, plus the `total_fte` column description).
- **Suggested fix**: Extend the existing 2019-anomaly documentation to state that in 2018 the broad scope applies to school-level rows only (school rows sum to ~1.34× the state row; district/state rows are narrow-scope), so school-to-aggregate reconciliation is not valid for 2018; optionally also note that district poverty-stratum aggregates can sit slightly below member-school FTE in a handful of rows (worst: Griffin-Spalding 2019 low_poverty district 27.0 vs school 35.8 — GOSA-published). Documentation-only; gold parquet bytes (and v1 parity) unchanged.

## NEEDS_JUDGMENT

### Judgment Call 1: 2023 Lindley 6th Grade Academy row is droppable but possibly rescuable
- **Severity if confirmed**: LOW (1 row, 2023, Total stratum only)
- **Suspicion**: The dropped 2023 row could bind to (633, 0309), whose dim latest name is "Betty Gray Middle School" — cert personnel maps "Lindley 6th Grade Academy" → 633/0309 in every year 2018–2022, and gold already carries (633, 0309) for 2018–2022 and 2024 via those year-aware/name bindings. An alias `lindley 6th grade academy` → `betty gray middle school` would rescue 2023 with no collision (the two bronze labels never co-occur).
- **Evidence available**: cert personnel 2018–2022 `SCHOOL_DSTRCT_CD=633, INSTN_NUMBER=0309, INSTN_NAME=Lindley 6th Grade Academy`; cert personnel 2023 carries only Lindley Middle (0202); gold (633, 0309) present 2018–2022 + 2024, absent 2023.
- **Why uncertain**: No 2023 evidence that code 0309 still represented that campus (the school was renamed/reconstituted as Betty Gray Middle around 2024); binding on dim-name continuity alone would be a guess. v1 (byte-matched) made the same drop; the row is documented in SOURCE_GAP_SCHOOLS. Lumpkin County Elementary 2023 (1 row) is the same pattern with weaker evidence (code 2050's latest dim name "Cottrell Elementary" is flagged as a distinct school) and should stay dropped.
- **Location**: `SOURCE_GAP_SCHOOLS` / `SCHOOL_NAME_ALIASES` in `src/etl/education/gosa/_educator_lookups.py`.
- **If confirmed, suggested fix**: add the alias and remove the gap entry — but note this changes gold bytes and breaks v1 parity for a 1-row coverage gain; the status quo is defensible (fidelity over coverage).

## Notes

- schema_hash `2c38701537a70afc578be7768152b086b8ed0f90687c4d3ac63762856fac0ab8`; validation 21 pass / 0 fail / 0 warning; manifest fresh (generated 2026-06-11T05:25:10Z); no read-loss events.
- v1 parity MATCH means every finding above also describes the approved v1 gold; Fix 1 is documentation-only and preserves parity (drift hashes only `.parquet`).
- The lookups module carries `TODO(verify-ccat-rename)` on the 7830103 pin; this topic's own bronze corroborates the CCAT→Statesboro STEAM continuity (2020 publishes the renamed school under the CCAT container label), so no action needed here.
- `emergency_fte_rate` may be non-NULL while `emergency_fte` is suppressed (e.g. 2021 Goshen Elementary `TFS`/`16`) — GOSA suppresses each cell independently; documented in `null_meaning`.
