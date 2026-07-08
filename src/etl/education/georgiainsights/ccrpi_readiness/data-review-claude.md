# Data Review: ccrpi_readiness

**Date**: 2026-06-12
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Gold is byte-identical with the v1 baseline (`MATCH — byte-identical with v1 gold`, sha `984ecd37…`), re-verified independently in this review. Every bronze→gold pathway checked out against raw cells: all 1,611,990 bronze rows land in gold (0 filtered), every numeric bronze value survives the cast exactly (per-year gold non-null counts equal raw numeric counts in all 7 files), all 4 categorical maps are semantically correct with 0 unmapped, and all 8 value-level traces MATCH. The only finding is a LOW documentation inaccuracy: the transform/contract claim that the `Beyond The Core` capital-T casing is "2018 only" is wrong — raw 2019 also uses capital T (lowercase starts 2021). Zero data impact (the map is uppercase-canonicalized).

## Manifest Verification

Artifacts FRESH (transform mtime 13:57:38 < manifest 14:00:05 ≤ validation 14:00:06); validation `passed: true`, 21 pass / 0 fail / 0 warning; `read_loss` 0 events; no `masked_values` / `reclassified` sections (absent = zero events).

### Categorical map table

| Column | Map entries | Bronze values seen | Unmapped | Status |
|---|---|---|---|---|
| demographic | 11 (effective alias slice) | 11 | 0 | PASS |
| grade_cluster | 3 | 3 | 0 | PASS |
| indicator | 8 | 8 | 0 | PASS |
| sub_indicator | 23 | 23 | 0 | PASS |

### Full map review (every entry verified semantically)

**demographic** — all 11 correct. `ALL STUDENTS→all`; `ASIAN/PACIFIC ISLANDER→asian_pacific_islander` (combined bucket, see 2e below); `BLACK→black`; `HISPANIC→hispanic`; `WHITE→white`; `MULTI-RACIAL→multiracial`; `AMERICAN INDIAN/ALASKAN→native_american` and `AMERICAN INDIAN/ALASKAN NATIVE→native_american` (label rename verified in raw: no "Native" through 2021, "Native" from 2022); `ECONOMICALLY DISADVANTAGED→economically_disadvantaged`; `STUDENTS WITH DISABILITY→students_with_disabilities`; `ENGLISH LEARNERS→english_learners`. Exactly 10 distinct labels per year in raw — no collisions, 1:1 onto 10 canonical keys.

**grade_cluster** — `E→elementary`, `M→middle`, `H→high`. Correct; raw shows only E/M/H in every year.

**indicator** — all 8 correct. `BEYOND THE CORE→beyond_the_core` (collapses both casings via uppercase canon — but see Fix 1 on the prose claim); `LITERACY→literacy` and `STUDENT ATTENDANCE→student_attendance` kept DISTINCT from `AT OR ABOVE GRADE-LEVEL READING→at_or_above_grade_level_reading` / `ATTENDANCE→attendance` — correct per the 2023 GaDOE methodology revision the structure doc flags ("reviewers may prefer to keep them as separate indicators"); the rename boundary is contract-enforced (`indicator_rename_era_boundary`, passing). `ACCELERATED ENROLLMENT`, `PATHWAY COMPLETION`, `COLLEGE AND CAREER READINESS` straightforward.

**sub_indicator** — all 23 entries correct. `ALL→all` and `NA→all` per the structure doc ("Treat `NA` as semantically equivalent to `All`"); raw confirms `NA` appears only 2021–2022 and only on the no-breakdown indicators. Casing variants (`Fine arts`, `World language`, `Advanced academic`, `Work-based learning`) collapse via uppercase canon. `PHYSICAL EDUCATION OR HEALTH` (2021) / `PHYSICAL EDUCATION/HEALTH` (2022+) → `physical_education_health` ✓. 2021 verbose CCR labels (`READINESS SCORE ON THE ACT, SAT, AP OR IB`, `END OF PATHWAY ASSESSMENT (EOPA)`, `ENTERING TCSG/USG WITHOUT NEEDING REMEDIATION`) → short canonical tokens ✓. The `ACT/SAT/AP/IB[/CAMBRIDGE]` evolution unifies on `act_sat_ap_ib_cambridge` — see Judgment Call 1. The raw distinct-value union across 2021–2025 (uppercased) is exactly the 23 seen values; nothing documented in the structure doc went unencountered.

**2c contract cross-check** — `gold_values_produced` equals the contract `enum` for all four columns (demographic 10, grade_cluster 3, indicator 8, sub_indicator 17). PASS.

**2d unmapped** — 0 across all columns. PASS.

**2e Asian/Pacific Islander (Risk 1)** — PASS, positive case. Raw sweep of all 7 files: exactly 10 Reporting Labels per year, always the explicit combined `Asian/Pacific Islander`, never a separate `Asian`, `Pacific Islander`, or NHPI label. Gold emits `asian_pacific_islander`; the split keys are never produced. Math test N/A — no summable count metric (both metrics are scores/rates); the structural test is the evidence.

**2f Mutual exclusivity (Risk 6)** — PASS — single convention (combined bucket only; no rollup-plus-split coexistence).

### Row-count reconciliation

| Year | Bronze | Gold | Filtered | Expansion | Raw rows re-counted |
|---|---|---|---|---|---|
| 2018 | 105,450 | 105,450 | 0 | 1.0 | 105,450 ✓ |
| 2019 | 105,640 | 105,640 | 0 | 1.0 | 105,640 ✓ |
| 2021 | 269,420 | 269,420 | 0 | 1.0 | 269,420 ✓ |
| 2022 | 213,650 | 213,650 | 0 | 1.0 | 213,650 ✓ (header row 1) |
| 2023 | 309,250 | 309,250 | 0 | 1.0 | 309,250 ✓ |
| 2024 | 304,670 | 304,670 | 0 | 1.0 | 304,670 ✓ |
| 2025 | 303,910 | 303,910 | 0 | 1.0 | 303,910 ✓ (renamed sheet) |

Total 1,611,990 bronze = 1,611,990 gold; actual parquet row sum re-counted = 1,611,990 = manifest `total_gold`. PASS. Stronger still: per-year gold `non_null_count` for both metrics equals the raw numeric-token count in each bronze file exactly (e.g. 2018 score 68,493; 2021 rate 14,172; 2024 both 196,375; 2025 both 197,733) — no value was silently lost to the `strict=False` cast.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| School Year | year | MAPPED (cross-checked vs filename year per file) |
| System ID | district_code | MAPPED (`ALL`→NULL, zfill(3), 7-digit charters untouched) |
| System Name | — | CORRECTLY EXCLUDED (dimension attribute; drives detail_level) |
| School ID | school_code | MAPPED (`ALL`→NULL, zfill(4)) |
| School Name | — | CORRECTLY EXCLUDED (dimension attribute; drives detail_level) |
| Grade Configuration | — | CORRECTLY EXCLUDED (dimension-style descriptor; verified present then dropped) |
| Grade Cluster | grade_cluster | MAPPED |
| Reporting Label | demographic | MAPPED |
| Indicator | indicator | MAPPED |
| Sub-Indicator (Era 2) | sub_indicator | MAPPED (Era 1 = typed NULL, "not collected") |
| Unbenchmarked Rate (Accelerated Enrollment) (Era 2) | unbenchmarked_rate | MAPPED (÷100 → proportion; Era 1 = typed NULL) |
| Indicator Score | indicator_score | MAPPED (0–100 score scale preserved) |

No gold column lacks a bronze source (no fabrication). Era rename maps re-checked against raw headers of all 7 files — exact matches, no typos; `_require_columns` guards every expected column per era.

## Value-Level Spot Checks

Extreme rows first; all verdicts rest on quoted raw cells (pandas `dtype=str`, `keep_default_na=False`).

| # | Trace | Bronze (file, row, raw values) | Expected | Gold | Verdict |
|---|---|---|---|---|---|
| 1 | Global max, indicator_score | 2024 row: `601/103, H, ALL Students, Accelerated Enrollment, All, rate=56.22, score=100` | 100.0, rate 0.5622 | `100.0` / `0.5622` | MATCH |
| 2 | Global min, indicator_score | 2024 row: `601/103, H, ALL Students, Accelerated Enrollment, Cambridge, rate=0, score=0` | 0.0, rate 0.0 | `0.0` / `0.0` | MATCH |
| 3 | Global max, unbenchmarked_rate | 2021 row 29990: `625/0513, H, ALL Students, Accelerated Enrollment, All, rate=100.00, score=100.00` | rate 1.0, score 100.0 | `1.0` / `100.0` | MATCH |
| 4 | Ordinary Era 1 + Corrections §4 check | 2019 row 28683: `644/309, M, Black, Student Attendance, score=96.15` (the structure doc's sample-data slip showed 100; raw is 96.15) | 96.15, sub_ind NULL, rate NULL | `96.15` / NULL / NULL | MATCH |
| 5 | Era 1 state row + ALL sentinel | 2019 row 105540: `System ID=ALL, School ID=ALL, All Systems/All Schools, Literacy, E, score=53.24` | NULL geo, 53.24 | NULL/NULL, `53.24`, in `states.parquet` | MATCH |
| 6 | Era 2 `NA` sub-indicator restoration | 2021 row 269160: state, `Literacy, E, Sub-Indicator=NA, rate=NA, score=46.74` | sub_indicator `all`, score 46.74, rate NULL | `all` / `46.74` / NULL | MATCH |
| 7 | Suppression, spelled-out marker | 2021 row 2: `601/0103, H, Asian/Pacific Islander, Accelerated Enrollment, All, score=Too Few Students` | NULL score, NULL rate | NULL / NULL | MATCH |
| 8 | Suppression `TFS` + `NA` + 7-digit charter | 2024 rows 304040–42: `7830647 RISE Prep / 647, E, At or Above Grade-Level Reading`: all=`54.35/54.35`, Am. Indian=`TFS/TFS`, Asian/PI=`NA/NA` | district_code `7830647` intact, school `0647`; 54.35 + 0.5435; NULLs | `7830647`/`0647`; `54.35`/`0.5435`; NULL/NULL ×2 | MATCH |
| 9 | 2024 AE rows where rate ≠ score (independent signal) | 2024 state rows 304410–304450: All=`49.63/90.68`, AP=`38.32/70.02`, Cambridge=`0.08/0.15`, DE=`25.35/46.32`, IB=`2.45/4.48` | rate/100 vs score verbatim, 5 rows | `0.4963/90.68`, `0.3832/70.02`, `0.0008/0.15`, `0.2535/46.32`, `0.0245/4.48` | MATCH (all 5) |

- **4c sentinel year-attribution (Risk 3)**: N/A-PASS — every file's `School Year` column holds exactly one distinct value equal to the filename year (verified all 7); no year-bearing strings inside data rows. The transform's year literals are config keys (sheet/header lookup) and quality-check boundaries only.
- **4d aggregate feasibility screen (aggregates COME FROM BRONZE)**: state-vs-district envelope: **0 of 153** state rows outside the district min/max. District-vs-school envelope (demographic=`all`): 846 / 30,982 (2.73%) outside, only 8 rows >10 pts, max excursion 28.12 — every worst case is district `799` ("State Schools", 3 schools). Verified the worst directly in bronze 2024: `Atlanta Area School for the Deaf=TFS`, `Georgia Academy for the Blind=56.25`, `Georgia School for the Deaf=TFS`, district `All Schools=28.13` — the district aggregate includes the two suppressed schools' students, so the excursion is bronze-published and suppression-explained, not a transform defect. PASS.
- **4e dedup tie-break (Risk 5)**: N/A — each year ships in exactly one file (no overlap years); natural key unique per file (collision guard + grain uniqueness both pass). `sort_col="indicator_score"` is defensive only.
- **4f suppression semantics**: all three marker forms traced to NULL (`TFS` trace 8, `Too Few Students` trace 7, `NA` traces 6/8); all three confirmed in shared `SUPPRESSION_VALUES`. Raw token census across all 7 files × both metric columns found **no other non-numeric token** (no `100.00+`-style sentinels in this topic) — so the suppression-aware read plus `strict=False` cast cannot have silently nulled anything else.

## Validation Cross-Read

- `_validation.json`: **21 pass / 0 fail / 0 warning**, `passed: true`, timestamp 2026-06-12T14:00:06Z. `contract_parquet_schema` (21 files), `contract_quality_sql` (all 18), `grain_uniqueness` (7-key grain), `foreign_keys` (243 districts / 2,407 schools / 10 demographics all resolve), geography nulling ×3 — all pass.
- Contract `schema_hash`: `2341973aebcc7a2615c1f0438e40a389301d20edc5271389cbb0d093e7503d6d`.
- **§4b masking audit**: no `_null_*` helpers in transform.py; no `masked_values` manifest section; raw min/max are exactly 0/100 for both metrics in every file — nothing to mask. Range guards present (`score` [0,100]; `proportion` [0,1]). PASS.
- **§15b coverage judgment**: strong — 11 authored quality checks cover both era boundaries (sub_indicator and rate structurally NULL in Era 1; never NULL in Era 2), the 2021–2023 AE-only rate population, the 2024–2025 rate≡score/100 mirror (with co-nullness), AE co-null, cluster-bound indicators (HS-only ×3; Beyond the Core E/M-only), the 2023 rename boundary, the partial-2022 release, and full sub-indicator→parent nesting. Each was independently re-verified against raw bronze in this review (see Cross-Era Consistency). No missing obvious invariant.
- **v1 parity (5d)** — executed output, verbatim:

```
MATCH — byte-identical with v1 gold
```

(current = v1 = `984ecd3785dc4c28101d9e9e0efa41ab8f209c5b69d1096526de030503a6c708`)

## Cross-Era Consistency

- **Era routing**: raw headers re-read for all 7 files — 2018/2019 are exactly the 10-column Era 1 signature; 2021–2025 exactly the 12-column Era 2 signature (incl. 2022 read at header row 1 under the DOE disclaimer, and the renamed 2025 sheet `Readiness - Student Group`). Routing is by column signature, never year. PASS.
- **Cross-year NULL sweep (Risk 2)**: only two flags — `sub_indicator` and `unbenchmarked_rate` ~100% NULL in 2018–2019 — both are the documented Era 1 structural gaps (columns absent from bronze), contract-enforced. No era-localized rename bug signature.
- **Rate population shift, re-verified in raw**: 2021/2022/2023 have **0** numeric rate values on non-AE rows (non-AE cells are `NA`); 2024/2025 populate every row, with non-AE rate raw-string-equal to Indicator Score on **100.0000%** of rows (max |diff| = 0.0, both files). AE one-sided (rate xor score numeric) = 0 in every Era 2 file.
- **Indicator availability per gold year** matches raw exactly: 2018–2021 six indicators (old names), 2022 only four (no Student Attendance / CCR — pandemic disclaimer), 2023–2025 six (new names). Old/new label boundary at 2023 holds in raw and gold.
- **Year-over-year continuity (3d)**: at comparable grain (state, demographic=`all`, rolled-up sub-indicator), per-indicator series are smooth — e.g. accelerated_enrollment 85.7→86.6→86.6→85.4→87.2→90.7→94.1; pathway_completion 79.1→79.7→78.3→77.5→76.8→78.0→79.9. The 2021 dips (literacy 60.5→47.9, student_attendance 87.8→79.6) are pandemic-consistent and bronze-published. No 10x jumps, no scale shifts. The big drop in the *overall* per-year mean (75.7→47.8 at the 2019→2021 boundary, visible in the manifest) is purely compositional — Era 2 adds many near-zero sub-component rows (e.g. Cambridge 0.15) — not a unit error.

## Transform Logic Risks

| Risk | Severity | Verdict / details |
|---|---|---|
| Silent column drops | — | PASS — `_require_columns` per era; all 12 bronze columns accounted for |
| Era routing correctness | — | PASS — signature-based; unknown schema raises; verified vs raw headers ×7 |
| Filter logic | — | PASS — zero rows filtered; bronze = gold = 1,611,990 |
| Normalization map completeness | — | PASS — 23/23 sub-indicator, 8/8 indicator, 11/11 demographic, 3/3 cluster vs raw unions |
| `strict=False` casts | — | PASS — raw token census: only TFS / Too Few Students / NA; gold non-null = raw numeric count per year, both metrics |
| Dedup keys + tie-break | — | PASS — collision guard before dedup; no overlap years; defensive only |
| Year extraction | — | PASS — filename year cross-checked against in-sheet `School Year` (uniform, all 7 files) |
| §4b/5b masking | — | PASS — no masks; nothing to mask (raw range exactly [0,100]) |
| Docstring/contract casing claim | LOW | FLAG — "Beyond The Core (2018)" prose wrong for 2019; see Fix 1 |

## Required Fixes

### Fix 1: Correct the "Beyond The Core 2018-only casing" claim in docstring/comment/contract description
- **Severity**: LOW
- **Issue**: Documentation inaccuracy (no data impact). Three places state the capital-T `Beyond The Core` casing is 2018-only and that `Beyond the Core` starts in 2019: the module docstring ("``Beyond The Core`` (2018, capital T) unifies with ``Beyond the Core`` (2019+)"), the `INDICATOR_MAP` comment, and the contract `indicator` description ("`Beyond The Core` (2018 casing) unifies with `Beyond the Core` (2019+)").
- **Evidence**: Raw distinct Indicator values — 2018: `'Beyond The Core'`; **2019: `'Beyond The Core'`** (capital T); 2021: `'Beyond the Core'` (lowercase t). The structure doc's recoding table has it right (`Beyond The Core` | 2018, 2019). Gold data is unaffected: the map applies on uppercased labels, so both casings land on `beyond_the_core` either way (v1 parity MATCH confirms byte-identical output).
- **Location**: module docstring (~line 49), `INDICATOR_MAP` comment (~line 198), and the `indicator` column description inside `_emit_contract_and_readme()` in `src/etl/education/georgiainsights/ccrpi_readiness/transform.py`.
- **Suggested fix**: Change the prose to "`Beyond The Core` (2018–2019, capital T) unifies with `Beyond the Core` (2021+)" in all three places and re-run the transform to re-emit the contract (data bytes unchanged; schema_hash unchanged; parity stays MATCH).

## NEEDS_JUDGMENT

### Judgment Call 1: `act_sat_ap_ib_cambridge` splices three label generations, while the indicator-level rename was kept separate
- **Severity if confirmed**: LOW
- **Suspicion**: Internal-consistency tension. The transform keeps `literacy`/`student_attendance` (2018–2022) separate from `at_or_above_grade_level_reading`/`attendance` (2023+) because the methodology changed — but unifies the CCR sub-indicator labels `Readiness score on the ACT, SAT, AP or IB` (2021), `ACT/SAT/AP/IB` (2023–2024), and `ACT/SAT/AP/IB/Cambridge` (2025) onto the single token `act_sat_ap_ib_cambridge`, even though 2025 widens the evidence list to include Cambridge.
- **Evidence available**: Raw sub-indicator sets per year confirm the three label generations and their years. The 2024 state-level Cambridge AE participation rate is 0.0008 (0.08%) — the Cambridge program is negligible in Georgia, so the 2025 definitional widening is immaterial in magnitude, unlike the 2023 Literacy methodology revision. The contract `sub_indicator` description documents the unification explicitly. v1 made the identical call (parity MATCH on approved gold).
- **Why uncertain**: Whether a definitional widening of the evidence list constitutes a "methodology change" warranting separate tokens is a semantics judgment, not something bronze can prove either way.
- **Location**: `SUB_INDICATOR_MAP` in `src/etl/education/georgiainsights/ccrpi_readiness/transform.py` (the three `act_sat_ap_ib_cambridge` entries).
- **If confirmed, suggested fix**: Split into era-specific tokens (e.g. `act_sat_ap_ib` for 2021–2024 and `act_sat_ap_ib_cambridge` for 2025+) and bump the contract version. **Recommendation: keep as-is** — the construct (test-score readiness evidence) is continuous, the widening is ~0.1%-of-students scale, the contract documents it, and splitting would fragment the series and break v1 parity for negligible semantic gain.

## Notes

- Contract `schema_hash`: `2341973aebcc7a2615c1f0438e40a389301d20edc5271389cbb0d093e7503d6d`; validation 21 pass / 0 fail / 0 warning; 18/18 contract quality SQL checks pass (11 authored + 7 auto-derived).
- v1 parity: **MATCH** (sha `984ecd3785dc4c28101d9e9e0efa41ab8f209c5b69d1096526de030503a6c708`), re-computed independently in this review.
- The literacy/attendance 2023 rename kept-separate decision is the conservative option the structure doc explicitly offers to reviewers; it is well-reasoned (GaDOE methodology revision), contract-documented, and enforced by the `indicator_rename_era_boundary` quality check. Verified, not a judgment item.
- Structure-doc Corrections section (ALL-sentinel IDs, spelled-out `Too Few Students` in 2021–2022, sub-indicator year corrections, the 2019 Wadsworth sample slip) — all four independently re-verified in raw during this review; all hold (0 empty ID cells / 0 sentinel-vs-name mismatches in any file; trace 4 confirms 96.15).
- Gold layout: `year=YYYY/{schools,districts,states}.parquet` for all 7 years; no empty files (validator-checked).
- KNOWN ISSUE honored: no S3 access attempted (broken `georgia-data-admin` profile); parity used the local `docs/rebuild/v1-baseline.yaml`.
