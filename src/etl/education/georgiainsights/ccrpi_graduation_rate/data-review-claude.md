# Data Review: ccrpi_graduation_rate

**Date**: 2026-06-12
**Reviewer**: Claude (automated data review)
**Status**: NEEDS_JUDGMENT

## Summary

Value-level review of the six-family merge (CCRPI workbooks, legacy 2012-2014, standalone 4-year/5-year cohort releases, SB 431 on-time, GOSA 2023 CSV) found **zero required fixes**: every spot check — extremes, one entity per family, both directions of the cross-family precedence merge, suppression, and year attribution — matched raw bronze exactly. **v1 parity: MATCH — byte-identical with v1 gold (sha256 `c4ce73c682927a8b4fbecd342109ff59020404cc2a726427be6e70a3e43f0992`)**, independently recomputed. Two judgment items are deferred: the documented 2021 5-year A/D district/state asymmetry (recommend keep), and an optional 4-year count-coverage quality check (verified to hold; recommend adding at next contract regeneration).

## Manifest Verification

Preconditions: artifacts FRESH (transform mtime 14:03:35Z < manifest 14:05:03Z ≤ validation 14:05:03Z), `_validation.json` `passed: true` (21 pass / 0 fail / 0 warning), `read_loss` 0 events, no `masked_values` / `reclassified` sections.

### Categorical maps

| Column | Map entries | Bronze values seen | Unmapped | Status |
|---|---|---|---|---|
| `ccrpi_flag` | 3 | G, R, Y | 0 | PASS |
| `demographic` | 20 (effective slice of shared aliases) | 20 labels | 0 | PASS |
| `rate_type` | 5 (2 bronze + 3 synthetic literals) | 5 | 0 | PASS |

**Full map review (every entry):**

- `ccrpi_flag`: `G → green`, `Y → yellow`, `R → red` — correct per §16; bronze `NA` (no target) becomes NULL at read via SUPPRESSION_VALUES, matching the contract's `null_meaning`. CORRECT ×3.
- `demographic`: `ALL STUDENTS → all`, `ASIAN/PACIFIC ISLANDER → asian_pacific_islander` (explicit combined bronze bucket — see conflation test below), `BLACK → black`, `HISPANIC → hispanic`, `WHITE → white`, `MULTI-RACIAL → multiracial`, `AMERICAN INDIAN/ALASKAN → native_american` and `AMERICAN INDIAN/ALASKAN NATIVE → native_american` (label drift across 2022, same population), `ECONOMICALLY DISADVANTAGED → economically_disadvantaged`, `STUDENTS WITH DISABILITY → students_with_disabilities`, `ENGLISH LEARNERS → english_learners`, `LIMITED ENGLISH PROFICIENT → english_learners` (GOSA CSV synonym — semantically the same EL subgroup), `MALE → male`, `FEMALE → female`, `MIGRANT → migrant`, `HOMELESS → homeless`, `FOSTER → foster_care`, `ACTIVE DUTY → active_duty`, `STUDENTS WITHOUT DISABILITY → students_without_disabilities`, `NOT ECONOMICALLY DISADVANTAGED → not_economically_disadvantaged`. CORRECT ×20. The 20 `bronze_values_seen` exactly cover the structure doc's label inventory (10 standard subgroups + the Native-suffix drift + Family F's 18-label set after `Grad Rate -` prefix strip). No two labels within one file fold to the same canonical key.
- `rate_type`: `4-YEAR GRADUATION RATE → 4_year`, `5-YEAR GRADUATION RATE → 5_year` (Family A's bronze column) plus synthetic literals `4_year`/`5_year`/`on_time` recorded for families B/C/D/E/F that hardcode the type — correct: B/C/F are 4-year cohort releases, D is the 5-year release, E is the SB 431 on-time release. CORRECT ×5.

**Contract cross-check (2c):** `gold_values_produced` = contract `enum` for all three columns (demographic 18 = 18, rate_type 3 = 3, ccrpi_flag 3 = 3). PASS. **Unmapped (2d):** 0 everywhere. PASS.

### Asian/Pacific Islander conflation (2e)

Combined-convention topic: every family publishes the explicit `Asian/Pacific Islander` label; no NHPI/separate-Asian label exists anywhere in the structure doc. Positive math test at the only year with state-level counts across all demographics (2023, GOSA):

```
cohort_size: year=2023 total=134822 race_sum=134822 ratio=1.0000
graduate_count: year=2023 total=113735 race_sum=113735 ratio=1.0000
```

Exact race partition under the combined bucket — PASS (positive evidence for `asian_pacific_islander`; split keys never emitted).

### Mutual exclusivity (2f)

No rollup+split coexistence: gold has `asian_pacific_islander` and neither `asian` nor `pacific_islander`. `male`/`female`, `economically_disadvantaged`/`not_economically_disadvantaged`, `students_with(out)_disabilities` are complement pairs within their categories, not rollup/split conflicts. PASS — single convention.

### Row-count reconciliation (3a/3b)

Parquet total **163,568 rows = manifest `total_gold`**; per-year parquet counts equal manifest `by_year` gold exactly. All 14 expected years (2012-2025) present. Expansion factors < 1 are the cross-family merge collapsing deliberate overlaps, verified to the row for the most complex year:

| Year | Bronze | Gold | Explanation |
|---|---|---|---|
| 2012-2014 | 6,070 / 6,090 / 6,160 | same | Family B only, 1:1 |
| 2015-2017 | 6,875 / 6,941 / 6,952 | 6,250 / 6,310 / 6,320 | Family C All-Students sheet rows (625/631/632) merge into the Subgroup base |
| 2018 | 20,938 | 13,900 | A (13,890) + C (6,380+668); gold = A's 13,890 keys + 10 RTC district rows only C publishes |
| 2021 | 24,930 | 17,863 | verified: A 2021-5yr slice 6,420 + C 7,447 + D 6,683 + E 4,380 = 24,930 exactly; `filtered_explicit` 4,490 = A∩D school keys (see Cross-Era) |
| 2023 | 30,875 | 24,275 | A (13,140) + E (4,320) + F (13,075... counted under its rows); F fills counts on A keys + ~200 small-cell keys |
| 2025 | 14,458 | 6,890 | A's 2025 4-yr slice 6,890 (its 2024 5-yr slice lands in 2024) + C 7,568 merged in; zero C-only keys |

## Column Coverage

| Bronze column | Gold column | Verdict |
|---|---|---|
| COHORT YEAR / School Year / Year / LONG_SCHOOL_YEAR / filename year | `year` | MAPPED (consumed per family; cross-checks raise on mismatch) |
| SYSTEM ID / System ID / SCHOOL_DSTRCT_CD | `district_code` | MAPPED (zfill(3); `ALL` → NULL; `RTC` passes through) |
| SCHOOL ID (incl. trailing-space variant) / INSTN_NUMBER | `school_code` | MAPPED (zfill(4); `ALL` → NULL) |
| REPORTING CATEGORY / REPORTING LABEL / Reporting Category Code / Reporting Label / LABEL_LVL_1_DESC | `demographic` | MAPPED (shared aliases; F prefix-stripped) |
| Graduation Rate Type | `rate_type` | MAPPED |
| GRADUATION RATE / Graduation Rate / On-Time Graduation Rate / PROGRAM_PERCENT | `graduation_rate` | MAPPED (unified, discriminated by `rate_type`) |
| GRADUATION CLASS SIZE / Graduation Class Size / Total Enrolled / TOTAL_COUNT | `cohort_size` | MAPPED (unified denominator) |
| TOTAL GRADUATED / Total Graduated / PROGRAM_TOTAL | `graduate_count` | MAPPED |
| Target | `target` | MAPPED (0-1 scale) |
| Flag | `ccrpi_flag` | MAPPED |
| REPORTING LEVEL / Reporting Level / DETAIL_LVL_DESC | — | CORRECTLY EXCLUDED (consumed; cross-checked against sentinel-derived level, raises on disagreement) |
| SYSTEM NAME / School Name / SCHOOL_DSTRCT_NM / INSTN_NAME | — | CORRECTLY EXCLUDED (dimension attributes) |
| Grade Configuration / GRADES_SERVED_DESC | — | CORRECTLY EXCLUDED (school attribute) |
| Grade Cluster | — | CORRECTLY EXCLUDED (constant `H`) |

No fabricated gold columns. Note: the structure doc's Gold Schema Classification *proposed* separate `on_time_graduation_rate` / `total_enrolled` / `graduation_class_size` / `total_graduated` / `ccrpi_target` columns; the transform instead unified them under `graduation_rate`+`rate_type` / `cohort_size` / `graduate_count` / `target`. This is a deliberate, docstring-documented design (and §16-conformant: `target` without prefix, `…_rate` suffix), and the byte-identical v1 parity confirms it is the approved shape — not a coverage gap.

## Value-Level Spot Checks

All verdicts quote bronze read directly with string-typed pandas/polars.

**Extremes first:**

| Trace | Bronze (file, row, value) | Gold | Verdict |
|---|---|---|---|
| Global max `cohort_size`/`graduate_count` | 2025 4-Year C file, ALL Student sheet, state row: `142094` / `123910` / rate `87.2` | 2025 state all 4_year: 142094 / 123910 | MATCH |
| Same key, rate (A-over-C precedence) | 2025 CCRPI workbook state 4-yr: `87.22`, Target `85.62`, Flag `G` (C published 87.2) | `0.8722` / `0.8562` / `green` — A's value won | MATCH |
| Global min `cohort_size` = 10 | GOSA CSV, district 613 Hispanic: `PROGRAM_TOTAL=10, PROGRAM_PERCENT=100, TOTAL_COUNT=10`; 2023 CCRPI workbook same key: `Graduation Rate = TFS` | 2023 613/NULL hispanic 4_year: rate 1.0, 10/10, target/flag NULL — GOSA fills the CCRPI-suppressed cell | MATCH |
| `graduate_count` min = 0 | 2016 C file All Students, 733/0107: class size `21`, graduated `0` | school sum for 733 carries 21 (district row = bronze `108`) | MATCH |
| `target` global min = 0.022 | 2025 CCRPI workbook, 891 (Dept. of Juvenile Justice) district SWD 4-yr: Target `2.2`, rate `2.78`, Flag `G` | manifest 2025 target min 0.022 | MATCH (real bronze value) |
| `target` max = 0.9 | 2023 CCRPI workbook 601 district all 4-yr: Target `90` | gold target 0.9 | MATCH |

**Ordinary traces, one per family:**

| Family | Bronze | Gold | Verdict |
|---|---|---|---|
| A (2018) | 722/0192 Salem High SWD: 4-yr `63.33`/`63.05`/`G`; 5-yr `71.05`/`62.69`/`G` | 0.6333/0.6305/green (4_year) and 0.7105/0.6269/green (5_year), counts NULL | MATCH |
| B (2012) | 601/0103 ALL Students `72.2`; Black `66.1`; district 601 all `72.2` | 0.722 / 0.661 / district 0.722 | MATCH |
| C (2016) | 601/0103: Subgroup all `86`, White `87.5`; All-Students counts `265`/`228` | all: 0.86 + 265/228; white: 0.875 + NULL counts (counts attach to `all` only) | MATCH |
| D (2021 5-yr) | 601/0103 all `93.18`, black `84.21` | 0.9318 / 0.8421 | MATCH |
| E (2022 on-time) | 601/0103: Enrolled `204`, Graduated `195`, Rate `95.59` | 0.9559 / 204 / 195 | MATCH |
| F (2023) | 601 district all: `236`/`93.65`/`252` + A-2023 `93.65`/`90`/`G` | 0.9365 / 252 / 236 / 0.9 / green (A's rate + F's counts on one row) | MATCH |
| RTC pseudo-district (2016) | C file `System ID="RTC"`, School ID ALL: all row `122`/`3`/`2.5`; 10 Subgroup rows | district_code `RTC`, school NULL: 0.025 + 122/3; subgroup rates (black 0.039, econ. dis. 0.022, white 0.015...) | MATCH |

**4c Year attribution:** `FILENAME_DATA_YEARS` pins 7 files. The offset file `...02.19.18.xlsx` → gold 2017: state all 4_year = `0.80556` + 129176/104059, matching the structure doc's cross-referenced 2017 value (80.556). Family A dual-year slices: the 2025 workbook's 2024 5-yr slice (`87.16`/`86.39`/`G`) lands at gold year=2024 5_year state = 0.8716/0.8639/green; the 2022 workbook's 2021 5-yr slice lands at year=2021. MATCH.

**4d Aggregate feasibility screen** (aggregates come from bronze, never derived): 2023 — state cohort 134822 ≥ district sum 133178 ≥ visible school sum 132287 (suppression-consistent); **0** districts with impossibly-low counts. 2016 — 3 districts where district cohort < visible school sum (708: 519 vs 520; 733: 108 vs 129; 755: 956 vs 979); all three verified **source-published** in the bronze All-Students sheet (e.g. 733 publishes school 0107 = 21/0 and 0201 = 108/81 but district = `108`/`81` — the source excludes the alternative school from the district cohort). Gold is faithful to bronze; no fix.

**4e Merge/dedup tie-break** (cross-family overlaps; no within-family overlap years): verified in both directions —
- A over C: 2025 state rate = A's 87.22, not C's 87.2 (above).
- D over A (2021 5-yr school): 601/0103 all D=`93.18` vs A=`87.9` → gold 0.9318 (D); black D=`84.21` vs A=`86.57` → gold 0.8421 (D).
- A over D (2021 5-yr district/state): 601 district all D=`93.18` vs A=`87.9` → gold **0.879** (A); state D=`85.63` vs A=`85.85` → gold 0.8585 (A). The documented asymmetry, exactly as the docstring/contract describe (see Judgment Call 1).
- F fills only A-gaps: 613 hispanic (A=TFS) carries F's rate; 601 all (A published) carries A's.
- Set algebra: D school keys 4,753 ∩ A school keys 4,510 = **4,490** = manifest `filtered_explicit`; union = **4,773** = gold 2021 5_year school rows. Exact.

**4f Suppression semantics:** `No Data Found` (B-2012, 602/0103 Asian/Pacific Islander) → NULL; `Too Few Students` lockstep (E-2022 601/0103 Native American: all three metrics) → all three NULL; `TFS` (A-2023 613 hispanic) → NULL rate (then F backfill). All MATCH; no suppression markers survive in gold (validator check passes).

## Validation Cross-Read

- `_validation.json`: 21 pass / 0 fail / 0 warning; `contract_parquet_schema` (40 files), `contract_quality_sql` (all 14), `grain_uniqueness` (year, district_code, school_code, demographic, rate_type), `foreign_keys` (230 districts, 589 schools, 18 demographics — all resolve) all pass.
- `schema_hash`: `4ea3f58b930d23d5845b0d0314f21f38199d15cfaeaf20c00f1ff310b1d6ab89`.
- **§4b masking audit:** no `_null_*` §4b mask helpers in transform.py (`_null_fill` only NULL-fills columns a family never publishes — not value masking); manifest has no `masked_values` section; docstring documents domain verification (rates in [0,100] bronze, targets [2.2,90], counts ≥ 0, graduate ≤ cohort, 0 violations source-wide). Consistent — PASS.
- **§15b coverage judgment:** 6 authored checks (graduate ≤ cohort; on_time rate↔counts identity; on_time co-null; on_time school-only; 5_year never carries counts; target/flag publication coverage incl. the 2020 COVID pin) + 8 derived = 14. Coverage is strong; one candidate addition deferred to Judgment Call 2.
- **v1 parity (verbatim):**

```
MATCH — byte-identical with v1 gold
hash: c4ce73c682927a8b4fbecd342109ff59020404cc2a726427be6e70a3e43f0992
```

## Cross-Era Consistency

- **Overlap resolution** verified at value level in all four directions (A/C, D/A, A/D, A/F — see 4e).
- **Era-boundary continuity:** state all 4_year rate is smooth across every boundary — 0.726 (2014, B) → 0.78953 (2015, C) → 0.80556 (2017, pinned offset file) → 0.8156 (2018, A-era starts) → 0.8369 (2021, C-only COVID year) → 0.8436 (2023, A+F) → 0.8722 (2025). State cohort 124,703 → 142,094 monotone. No >10x jumps, no cumulative-publication signature anywhere.
- **Cross-year NULL sweep:** flags are all documented bronze gaps, not rename bugs: `cohort_size`/`graduate_count` 100% NULL 2012-2014 (legacy publishes no counts) and ≥95% NULL 2018-2020 (counts exist only on ALL-Students rows: 638/13,900 etc.); `target`/`ccrpi_flag` 100% NULL 2012-2017 (pre-CCRPI), 2020 (COVID all-`NA` at source), 2021 (no CCRPI release). No column is ~100% NULL in a year its sources cover. PASS.

## Transform Logic Risks

| Risk | Severity | Verdict / details |
|---|---|---|
| Silent column drops | none | PASS — `_require_columns` guards every family's rename map; missing columns raise |
| Era/family routing | none | PASS — filename-based (C/D share schemas; only the filename prefix discriminates); unclassifiable names raise; 2020's CCRPI-prefix-less file explicitly handled |
| Filter logic logged + justified | none | PASS — only explicit filter is the A-2021-5yr school drop (4,490 rows, `record_filtered` with reason); PDF excluded by extension with documented supersession (CCRPI rate + GOSA counts) |
| Normalization map completeness | none | PASS — manifest `bronze_values_seen` covers the structure doc's full label inventory; unmapped 0 |
| `strict=False` casts | LOW | PASS-with-note — used to NULL `No Data`/`No Data Found` text not in SUPPRESSION_VALUES; the structure doc's marker inventory is complete and all suppression traces verified, but any *novel* future marker would NULL silently |
| Dedup keys + tie-break | none | PASS — precedence merge (rank-sort then first non-null per metric) verified both directions; collision guard runs scoped within source family; validator grain check re-proves per-key uniqueness |
| Year extraction | none | PASS — pinned `FILENAME_DATA_YEARS` + per-family year cross-checks that raise on mismatch; offset file and dual-year slices traced |
| §5b masking | none | PASS — no §4b masks; see Validation Cross-Read |

## NEEDS_JUDGMENT

### Judgment Call 1: 2021 5-year district/state rows keep Family A while school rows keep Family D

- **Severity if confirmed**: MEDIUM
- **Suspicion**: Within year=2021 `5_year`, school rows carry the standalone December-2021 release (D) while their parent district/state rows carry the 2022 CCRPI workbook's prior-year slice (A) — two publication vintages that disagree materially (district 601: D=`93.18` vs A=`87.9`; state: D=`85.63` vs A=`85.85`). School rows therefore do not aggregate consistently to their own district rows for this slice.
- **Evidence available**: Bronze quotes above; gold district 601 all = 0.879 (A), gold school 601/0103 all = 0.9318 (D). `_drop_superseded_a_2021_5yr` only key-matches fully-populated school keys by construction (no `nulls_equal`), and the docstring + contract note both state the asymmetry is "preserved from the approved v1 baseline".
- **Why uncertain**: Both choices are defensible — D is the primary publication for the 2021 5-year measure (argues for D everywhere), but A is the later-published accountability-grade snapshot (argues for A at aggregate level). Switching district/state to D would break byte-parity with the approved v1 gold and change published aggregate values.
- **Location**: `_drop_superseded_a_2021_5yr` (transform.py)
- **If confirmed, suggested fix**: Extend the D-supersession join with `nulls_equal=True` so district/state 2021 5-year keys also take D — and bump the contract minor version. **Recommendation: keep as-is.** The asymmetry is deliberate, documented in the contract notes and column descriptions, and parity-preserving; revisit only if a consumer needs school-to-district additivity for that one slice.

### Judgment Call 2: Optional quality check — 4_year counts exist only on `all` rows outside 2023

- **Severity if confirmed**: MEDIUM
- **Suspicion**: None — the invariant holds today (verified: **0** `4_year` non-`all` rows with counts outside 2023; **0** 2012-2014 rows with counts). The question is whether it should be *enforced* as a contract quality check, like its siblings `five_year_rows_never_carry_counts` and `on_time_rows_are_school_level`.
- **Evidence available**: `SELECT COUNT(*) WHERE rate_type='4_year' AND year<>2023 AND demographic<>'all' AND (cohort_size IS NOT NULL OR graduate_count IS NOT NULL)` returns 0 on current gold. It would guard the Family C two-sheet join's `pl.when(demographic == 'all')` clause — the one merge step with a real regression mode the current checks do not pin.
- **Why uncertain**: The check encodes publication trivia (the 2023 GOSA exemption) that already appears in `null_meaning` and the contract notes; a future standalone release that starts publishing subgroup counts would require a contract edit. Reasonable to deem current coverage sufficient.
- **Location**: `_emit_contract_and_readme` `quality_checks=` (transform.py)
- **If confirmed, suggested fix**: Author the check as above (`mustBe: 0`). Additive contract change only — gold parquet unchanged, v1 parity preserved. **Recommendation: add it at the next contract regeneration; not blocking.**

## Notes

- `schema_hash`: `4ea3f58b930d23d5845b0d0314f21f38199d15cfaeaf20c00f1ff310b1d6ab89`; validation 21/21 pass, 0 warnings; 14/14 contract quality checks pass; FKs resolve (230 districts incl. `RTC`, 589 schools, 18 demographics).
- v1 parity MATCH (`c4ce73c6…`) independently recomputed against `docs/rebuild/v1-baseline.yaml` (S3 not touched — AWS profile known-broken).
- 2016 feasibility-screen flags (districts 708, 733, 755: district cohort below visible school sum) are source-published values, reproduced faithfully — a GaDOE cohort-assignment quirk, not a transform defect; the contract's cutoff caveats already warn against cross-level arithmetic assumptions.
- The structure doc's proposed gold column names (`on_time_graduation_rate`, `total_enrolled`, `ccrpi_target`, …) were superseded by the unified `rate_type`-discriminated design; the doc's Corrections section (RTC, Family A "ALL" sentinels, 09_19_18 sheet asymmetry, D-sheet subset, exact on-time co-suppression) was re-verified during this review where load-bearing.
- 27 bronze files: 26 ingested + 1 superseded PDF (its content arrives via the 2023 CCRPI workbook + GOSA CSV).
