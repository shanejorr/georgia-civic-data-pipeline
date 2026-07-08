# Data Review: georgia_milestones_end_of_course_eoc_assessment_by_grade

**Date**: 2026-06-11
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Gold data is **byte-identical with v1** (`compute_gold_sha256` MATCH against `docs/rebuild/v1-baseline.yaml`) and every value-level trace, categorical mapping, aggregate feasibility screen, and suppression-semantics check passed. One MEDIUM fix is required: the served contract/README description for `num_developing_learner` claims the 2017 literal zeros are unique ("no other year has any") — bronze measurement falsifies this (2015 `DISTINGUISHED_CNT` has 4,940 literal zeros; 2017 `PROFICIENT_CNT` has 824), and the analogous 2015/2017 anomalies are undocumented on their own columns. This is a metadata-prose defect only — the gold values themselves are bronze-faithful and parity is unaffected by a description-only re-emit (schema_hash excludes descriptions).

## Manifest Verification

Preconditions: artifacts FRESH (transform mtime 23:34:17 < manifest 23:34:43 ≤ validation 23:34:43); `passed: true` (20 pass / 0 fail / 1 warning); `read_loss` absent (zero events); no `masked_values` / `reclassified` sections.

| Column | Map entries | Bronze values seen | Unmapped | Status |
|---|---|---|---|---|
| `demographic` | 22 (effective slice of `DEMOGRAPHIC_ALIASES`) | 22 | 0 | PASS |
| `grade_level` | 9 (effective slice of `GRADE_LEVEL_MAP`) | 9 | 0 | PASS |
| `subject` | 11 (topic-local `SUBJECT_MAP`) | 11 | 0 | PASS |

**Demographic map — all 22 entries reviewed, all semantically correct**: `ALL STUDENTS→all`, `ASIAN→asian` (correct here — split convention, see 2e), `BLACK OR AFRICAN AMERICAN→black`, `HISPANIC→hispanic`, `WHITE→white`, `TWO OR MORE RACES→multiracial`, `AMERICAN INDIAN OR ALASKAN NATIVE→native_american`, `NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER→pacific_islander`, `MALE→male`, `FEMALE→female`, `ECONOMICALLY DISADVANTAGED→economically_disadvantaged`, `NOT ECONOMICALLY DISADVANTAGED→not_economically_disadvantaged`, `STUDENTS WITH DISABILITIES→students_with_disabilities`, `STUDENTS WITHOUT DISABILITIES→students_without_disabilities`, `LIMITED ENGLISH PROFICIENT→english_learners`, `NOT LIMITED ENGLISH PROFICIENT→not_english_learners` (canonical `not_` prefix per §5a), `MIGRANT→migrant`, `NON-MIGRANT→not_migrant`, `HOMELESS→homeless`, `ACTIVE DUTY→active_duty`, `MILITARY CONNECTED→military_connected`, `FOSTER CARE→foster_care`. The two military keys are correctly kept distinct (non-additive; subset relationship documented in the contract) — verified they never co-occur: gold has `active_duty` only in 2021 (242 rows) and `military_connected` only 2022+ (302/312/2,605 rows).

**Grade map — all 9 entries correct**: unpadded Era-1 spellings `7/8/9 → 07/08/09` and pass-throughs `10/11/12`, padded `07/08/09 → 07/08/09`. Produces exactly the 6 canonical values `07`–`12` in every year.

**Subject map — all 11 entries correct**: each bronze course name snake_cased to its §16 canonical (`US History→us_history`, `9th Grade Literature and Composition→9th_grade_literature_and_composition`, `Economics/Business/Free Enterprise→economics_business_free_enterprise`, `Algebra: Concepts and Connections→algebra_concepts_and_connections`, etc.). Curriculum-era identities (`algebra_i`/`coordinate_algebra`/`algebra_concepts_and_connections`; `geometry`/`analytic_geometry`) correctly kept distinct. `apply_subject_normalization` backstop is a no-op on this set (already canonical).

**Contract enum cross-check (2c)**: `gold_values_produced` equals the contract `enum` for all three columns (22 / 6 / 11 values). PASS.

**Row-count reconciliation (3a/3b)**:

| Year | Bronze | Gold | Expansion |
|---|---|---|---|
| 2015 | 107,393 | 107,393 | 1.0 |
| 2016 | 117,307 | 117,307 | 1.0 |
| 2017 | 118,950 | 118,950 | 1.0 |
| 2018 | 119,650 | 119,650 | 1.0 |
| 2019 | 119,611 | 119,611 | 1.0 |
| 2021 | 53,855 | 53,855 | 1.0 |
| 2022 | 64,443 | 64,443 | 1.0 |
| 2023 | 66,273 | 66,273 | 1.0 |
| 2024 | 138,747 | 138,747 | 1.0 |
| **Total** | **906,229** | **906,229** | |

Per-year bronze counts equal the structure doc's table exactly; actual parquet row count = 906,229 = manifest `total_gold`. Zero filtered, zero read loss, zero masks. The 2021 dip (53,855) and 2022 course retirement are documented real-world events. All expected years present; 2020 genuinely absent (COVID). PASS.

### 2e: Asian / Pacific Islander conflation (Risk 1) — PASS, split convention positively confirmed

Bronze publishes a separate `Native Hawaiian or Other Pacific Islander` label (structure doc + `bronze_values_seen`), and the math test confirms the 7-bucket split partition is complete and exclusive:

```
Race buckets present: ['asian', 'black', 'hispanic', 'multiracial', 'native_american', 'pacific_islander', 'white']
2024 state grade=09 biology: all=68397 race_sum=68397 ratio=1.0000
2019 state grade=09 biology: all=76743 race_sum=76743 ratio=1.0000
```

2019 state grade-09 biology race rows: asian=4,513, black=26,064, hispanic=11,205, multiracial=2,808, native_american=153, **pacific_islander=95**, white=31,905 — sums exactly to the `all` row's 76,743. Bare "Asian" is genuinely Asian-only; mapping to `asian` is correct. No §5b remap needed.

### 2f: Demographic mutual exclusivity (Risk 6) — PASS, single convention

`gold_values_produced` contains `asian` and `pacific_islander` but no `asian_pacific_islander` rollup (and no other category rollups). No synthesized rows. PASS — single convention.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| `#ASSMT_CD` (Era 2 only) | — | CORRECTLY EXCLUDED (constant `EOC_by_GRADE`; hard-guarded before drop — transform raises on any other value) |
| `LONG_SCHOOL_YEAR` | `year` | MAPPED (filename year hard cross-checked against parsed ending year) |
| `SCHOOL_DISTRCT_CD` | `district_code` | MAPPED (zfill(3), `ALL`→NULL before padding; 7-digit charters pass through) |
| `SCHOOL_DSTRCT_NM` | — | CORRECTLY EXCLUDED (districts dimension attribute) |
| `INSTN_NUMBER` | `school_code` | MAPPED (zfill(4) fixes the 2015-2019 3/4-char mix; `ALL`→NULL) |
| `INSTN_NAME` | — | CORRECTLY EXCLUDED (schools dimension attribute) |
| `ACDMC_LVL` | `grade_level` | MAPPED (shared normalizer) |
| `SUBGROUP_NAME` | `demographic` | MAPPED (`normalize_demographic_column`) |
| `TEST_CMPNT_TYP_NM` | `subject` | MAPPED (§16: academic content → `subject`, not `test_component`) |
| `NUM_TESTED_CNT` | `num_tested` | MAPPED (Int64, strict=False) |
| `BEGIN_CNT` / `DEVELOPING_CNT` / `PROFICIENT_CNT` / `DISTINGUISHED_CNT` | `num_{beginning,developing,proficient,distinguished}_learner` | MAPPED |
| `BEGIN_PCT` / `DEVELOPING_PCT` / `PROFICIENT_PCT` / `DISTINGUISHED_PCT` | `pct_{beginning,developing,proficient,distinguished}_learner` | MAPPED (÷100, 0-1 scale) |
| (derived) | `pct_developing_learner_or_above`, `pct_proficient_learner_or_above` | DERIVED per §16 (NULL-propagating `+`, rounding cap — verified below) |

Every gold column traces to bronze or a documented derivation; no fabrication. `_require_columns` guards all 16 expected bronze columns per file (rename-coverage hard stop). Matches the structure doc's Gold Schema Classification exactly.

## Value-Level Spot Checks

All traces MATCH. Bronze quoted verbatim.

**T1 — global `num_tested` max (extreme)**: 2016 bronze state row `ALL/ALL, ACDMC_LVL=9, All Students, 9th Grade Literature and Composition: NUM_TESTED_CNT=127704, BEGIN=27654, DEV=47767, PROF=43913, DIST=8370, PCTs 21.7/37.4/34.4/6.6` → gold `year=2016, NULL/NULL, all, 09, 9th_grade_literature_and_composition: 127704, 27654, 47767, 43913, 8370, 0.217/0.374/0.344/0.066, or_above 0.784/0.41`. MATCH (incl. cumulative sums 0.374+0.344+0.066=0.784; 0.344+0.066=0.410).

**T2 — global `num_developing_learner` max**: 2015 state grade-9 9th-lit row `126260/28937/48450/41096/7777, 22.9/38.4/32.5/6.2` → gold `126260/28937/48450/41096/7777, 0.229/0.384/0.325/0.062, or_above 0.771/0.387`. MATCH.

**T3 — global `num_proficient_learner` + `num_distinguished_learner` max**: 2019 state grade-9 9th-lit `120112/15175/32534/53289/19114, 12.6/27.1/44.4/15.9` → gold identical, or_above `0.874/0.603`. MATCH.

**T4 — global count min / 2015 zero anomaly (extreme)**: 2015 bronze `601/103/9, Economically Disadvantaged, 9th Grade Lit: NUM_TESTED=163, BEGIN=58, DEV=80, PROF=25, DISTINGUISHED_CNT=0, PCTs 35.6/49.1/15.3/0` → gold `601/0103/economically_disadvantaged/09: 163/58/80/25/0, 0.356/0.491/0.153/0.0, or_above 0.644/0.153`. MATCH — bronze-faithful zero (one of 4,940 such 2015 `DISTINGUISHED_CNT` zeros; see Fix 1). `num_tested` global min = 10 (e.g., 2015 district 601 grade-09 physical_science `all` row) consistent with GOSA's ≥10 reporting floor everywhere except the zero-anomaly cells.

**T5 — ordinary Era-1 entity**: 2023 bronze `611 Bibb County / 0386 Southwest High / 10 / Non-Migrant / Algebra I: 33, 30, TFS, TFS, TFS, 90.9/9.1/0/0` → gold `611/0386/not_migrant/10/algebra_i: 33, 30, NULL, NULL, NULL, 0.909/0.091/0.0/0.0, or_above 0.091/0.0`. MATCH (TFS→NULL; reported pcts preserved).

**T6 — ordinary Era-2 entity**: 2024 bronze `7830642 State Charter Schools II / 0642 Destinations Career Academy / 09 / Students without Disabilities / Algebra: Concepts and Connections: 107, 49, 34, 20, TFS, 45.8/31.8/18.7/3.7` → gold `7830642/0642/students_without_disabilities/09/algebra_concepts_and_connections: 107, 49, 34, 20, NULL, 0.458/0.318/0.187/0.037, or_above 0.542/0.224`. MATCH (7-digit charter code untruncated; 0.318+0.187+0.037=0.542 ✓).

**T7 — 2017 `DEVELOPING_CNT` zero-anomaly trace**: 2017 bronze `602/103/11, Students with Disabilities, American Literature: NUM_TESTED=12, BEGIN=12, DEVELOPING_CNT=0, PROF=TFS, DIST=TFS, DEVELOPING_PCT=0` → gold `602/0103/students_with_disabilities/11/american_literature_and_composition: 12, 12, 0, NULL, NULL, 1.0/0.0/0.0/0.0`. MATCH — literal zero passed through bronze-faithfully per the documented decision.

**T8 — 2024 fully-suppressed-counts cell with published pct distribution**: 2024 bronze `636 Columbia / 0193 Riverside Middle / 07 / White / Algebra: CC: NUM_TESTED=TFS, all four counts TFS, PCTs 0/0/0/100` → gold `num_tested=NULL, all counts NULL, pcts 0.0/0.0/0.0/1.0, or_above 1.0/1.0`. MATCH — 2024 pcts are real signal on suppressed cells, correctly preserved.

**T9 — 2024 extreme-low pct partition sum (0.068)**: 2024 bronze `618/0190/09, Students with Disabilities, Algebra: CC: NUM_TESTED=29 (numeric), counts all TFS, PCTs 3.4/3.4/0/0 (sum 6.8)` → gold `29, NULLs, 0.034/0.034/0.0/0.0, or_above 0.034/0.0`. MATCH — the documented valid-score undershoot case, preserved not "repaired".

**T10 — 2015 empty-CSV-field suppression**: 2015 bronze `601/103/9, All Students, Analytic Geometry: NUM_TESTED_CNT=TFS, all 8 count/pct fields genuinely empty (parsed NULL)` → gold row exists with all 11 metrics NULL. MATCH.

**T11 — `_or_above` rounding-cap behavior (parity-load-bearing)**: 6,970 gold rows have component sum dev+prof+dist > 1.0 (max raw sum 1.001) and 516 rows prof+dist > 1.0 (max 1.001); in every case the gold cumulative is exactly 1.0, and the global max of both cumulatives is 1.0. Example: 2015 district 603 grade-09 physical_science `not_economically_disadvantaged`: components 0.455+0.455+0.091=1.001 → gold 1.0. Bronze-wide max 4-pct sum is 100.2 in every file (≤ the 0.005 cap tolerance after ÷100), so the cap never clips a genuine anomaly. MATCH.

**4c sentinel year-attribution (Risk 3)**: year comes from the filename and is hard-checked against the file's single `LONG_SCHOOL_YEAR` (`_assert_school_year_matches` raises on mismatch); no other year-bearing strings exist in bronze. Gold years 2015-2024 (no 2020) match the file set. N/A beyond this — no sentinel rows.

**4d aggregate feasibility screen (Risk 4)**: aggregates COME FROM BRONZE (none derived). Screen over all years: 230,026 district rows joined to their school aggregates — **0 violations** of `district >= max(school)` and **0** of `district >= sum(visible schools)`; 5,363 state rows joined to district aggregates — **0 violations** both directions. Visible-district-sum coverage of state rows: median 0.899, max 1.0 (never exceeds — suppression-only undershoot, as expected). PASS.

**4e dedup tie-break (Risk 5)**: N/A — each bronze file is a distinct year (manifest `files_processed`), eras do not overlap, and grain uniqueness passed on the full 906,229-row gold, so dedup was a no-op safety net as documented.

**4f suppression semantics**: covered by T5 (TFS string→NULL), T8 (2024 TFS counts with live pcts), T10 (2015 empty fields→NULL). Per-year bronze TFS counts in `NUM_TESTED_CNT` measured directly: 2015: 7,335 / 2016: 8,436 / 2017: 8,329 / 2018: 7,812 / 2019: 7,631 / **2021: 4,352 / 2022: 3,472 / 2023: 3,588** / 2024: 76,074 — confirming the transform's correction of the structure doc's earlier "never TFS in 2021-2023" claim, and exactly matching the manifest's gold null counts per year (TFS + empty fields = gold NULLs, reconciled to the row).

## Validation Cross-Read

`_validation.json`: **20 pass / 0 fail / 1 warning**; `contract_parquet_schema` (27 files), `contract_quality_sql` (all 23 checks), `grain_uniqueness` (PK = year, district_code, school_code, demographic, grade_level, subject), `foreign_keys` (218 district keys, 1,064 school keys, 22 demographics — all resolve) all pass. The single warning is `null_rate_spikes` on 2024 count columns (num_tested 54.8% vs 6.8% median, plus the three band counts) — fully explained: GOSA broadened TFS suppression in 2024 (76,074/138,747 = 54.83% bronze TFS, exact match), documented in the contract's `null_meaning`/notes. Explained, not escalated.

**schema_hash**: `742035feecb442bade1cc132f06e55618033e24126147e6eb327bcaeb8f666e1`.

**§4b masking audit (5b)**: no `_null_*` helpers in transform.py, no `masked_values` in the manifest, and the "No §4b mask" docstring claim holds — bronze contains no impossible values (counts non-negative; all bronze pcts within 0-100; cumulatives capped within rounding tolerance only). Consistent. PASS.

**§15b coverage judgment (5c)**: 8 authored cross-column checks (pcts-present-when-tested, pre-2024 co-null, level-sum ≤ num_tested, single-count ≤ num_tested, 4-pct sum ≤ 1.0025, both cumulative component-sum reconciliations, curriculum year ranges) — a strong set covering the topic's real invariants. One served claim is unenforced: the four `pct_*` `null_meaning` fields state "never NULL in 2024" but no quality check asserts it (see Judgment Call 1).

**v1 parity (5d)** — verbatim output:

```
MATCH — byte-identical with v1 gold
```

## Cross-Era Consistency

- **Overlap years**: none (one file per year). Era boundary is 2023→2024 (`#ASSMT_CD` prepended); column names otherwise identical, one shared transform route — correct per the structure doc.
- **Cross-year NULL sweep (3c)**: `CLEAN — no era-localized ~100% NULL columns`; no column is ~100% NULL in any year while populated in others, and no all-NULL columns.
- **YoY level continuity (3d)**: state-level means per metric across all adjacent year pairs show no >10x jumps and no revert-style level shifts. `num_tested` mean dips 8,199→4,444 in 2021 (COVID, documented) and recovers to 7,823 in 2022; pct means stable (0.32-0.45 band). The 2024 dip in cumulative-pct means (0.639→0.566) is the documented partition-undershoot effect on suppressed cells, not a scale problem.
- **Categorical evolution matches the structure doc exactly per year**: demographics 18/18/18/18/18/20/21/21/21 (active_duty+homeless added 2021; military_connected+foster_care from 2022, active_duty gone); subjects 8 (2015) → 10 (2016-2021) → 5 (2022-2023) → 6 (2024, adds algebra_concepts_and_connections); grades constant `07`-`12`. The curriculum quality check enforces this shape.
- **Level-count reconciliation**: undershoot rows confirmed at exactly 2023: 1 row (−3) and 2024: 249 rows (worst −70); **zero** overshoot rows in any year — the ≤-only contract form is correct.

## Transform Logic Risks

| Risk | Severity | Verdict / details |
|---|---|---|
| Silent column drops | — | PASS — only `#ASSMT_CD`, constant-verified with hard raise; `_require_columns` guards the rest |
| Era routing correctness | — | PASS — `detect_era_by_columns` on `#ASSMT_CD` signature; never year-based |
| Filter logic | — | PASS — no filters; bronze rows = gold rows exactly (906,229) |
| Normalization map completeness | — | PASS — 22/9/11 bronze values all mapped, unmapped_count 0 everywhere |
| `strict=False` casts | — | PASS — applied after reader nulls TFS; 2015-2019 empty fields parse NULL; verified counts reconcile per year |
| Dedup keys + tie-break | — | PASS — collision guard before dedup; `sort_col="num_tested"` documented; dedup provably a no-op (grain unique) |
| Year extraction | — | PASS — filename year + `LONG_SCHOOL_YEAR` cross-check, hard stop on mismatch |
| §4b masking (5b) | — | PASS — no masks, none needed, manifest agrees |
| Served-metadata accuracy | MEDIUM | FLAG — false "(no other year has any)" zero-uniqueness claim; see Fix 1 |

## Required Fixes

### Fix 1: Contract/README falsely claim the 2017 literal zeros are unique; 2015 and 2017 sibling zero-anomalies undocumented
- **Severity**: MEDIUM
- **Issue**: The served `num_developing_learner` description (contract line 289, README line 28) states the 2017 file "is the only year/column where suppression was not applied — it carries ~3,001 literal 0 values **(no other year has any)**". Direct bronze measurement falsifies the parenthetical: 2015 `DISTINGUISHED_CNT` contains **4,940** literal `"0"` values and 2017 `PROFICIENT_CNT` contains **824** (all other year×column pairs: 0). The same irregular-suppression character (published zeros where every other year uses TFS, visibly depressing the suppression rate) affects `num_distinguished_learner` in 2015 (null_pct 0.518 vs 0.754-0.793 in 2016-2019; manifest min_val 0 in 2015 vs 10 elsewhere) and mildly `num_proficient_learner` in 2017 (824 zeros; min_val 0), yet neither column's description carries a cross-year-comparison caveat — analysts reading the contract are affirmatively told no such zeros exist. The gold values themselves are correct (bronze-faithful pass-through, verified by trace T4).
- **Evidence**: Bronze zero counts per count column (literal `"0"`, measured with `pl.read_csv(..., infer_schema_length=0)`): `2015 DISTINGUISHED_CNT: TFS=48267 zero=4940` · `2017 DEVELOPING_CNT: TFS=0 zero=3001` · `2017 PROFICIENT_CNT: TFS=47937 zero=824` · every other year×column `zero=0`. Manifest corroborates: `num_distinguished_learner` 2015 `min_val: 0.0` / `null_pct: 0.5177` (vs 0.793 in 2016); `num_proficient_learner` 2017 `min_val: 0.0`. Traced example row (2015, district 601, school 0103, grade 09, economically_disadvantaged, 9th-grade lit): bronze `DISTINGUISHED_CNT=0, DISTINGUISHED_PCT=0` → gold `num_distinguished_learner=0` — a 2015 zero the served metadata says cannot exist.
- **Location**: `_emit_contract_and_readme()` in transform.py — the `num_developing_learner` description string ("(no other year has any)" and "the only year/column"), the `num_distinguished_learner` and `num_proficient_learner` descriptions, and the corresponding `notes=` entry ("3,001 literal zeros... no other year has any" framing).
- **Suggested fix**: Reword `num_developing_learner`'s description to scope its uniqueness correctly (2017 is the only year/column with suppression *fully* absent — TFS count literally 0); add caveats documenting the 2015 `num_distinguished_learner` zeros (4,940, with TFS still applied to small nonzero counts; do not compare 2015 against 2016+ for this column) and the 2017 `num_proficient_learner` zeros (824). Update the matching note. Apply the same correction to `bronze-data-structure.md`'s anomaly section (which also claims "vs 0 such literal zeros in any other year for any count column") and its "2015 is the only file that carries genuine CSV nulls" quirk (2016-2019 band-count and pct columns also use empty CSV fields on their fully-suppressed rows — measured nulls 8,436/8,329/7,812/7,631 — with TFS in pct columns only from 2021+; gold outcome identical either way). Re-run the transform: descriptions don't enter `schema_hash` and gold bytes are untouched, so v1 parity is preserved.

## NEEDS_JUDGMENT

### Judgment Call 1: Author a quality check enforcing "pct columns never NULL in 2024"
- **Severity if confirmed**: LOW
- **Suspicion**: The four `pct_*_learner` columns' `null_meaning` and descriptions assert they are "never NULL in 2024" (the load-bearing fact that makes 2024's suppressed-cell distributions usable signal), but no contract quality check enforces it. `pcts_present_when_num_tested_reported` covers only rows with non-NULL `num_tested` — the ~55% of 2024 rows with suppressed `num_tested` (where this property matters most) are unguarded. A future re-publish of the 2024 file or a transform regression could silently break the served claim.
- **Evidence available**: Manifest 2024 `null_count: 0` for all four pct columns (138,747/138,747 non-null) — the invariant currently holds. §15b's authoring rule: "every invariant a careful reviewer would verify by hand must be authored as a quality check" — I verified this one by hand.
- **Why uncertain**: It is a year-scoped completeness fact about one source file rather than a structural invariant of the schema; the team may prefer not to pin single-year source behavior into contract SQL (a 2024 data revision would then require a contract edit). No current data defect either way.
- **Location**: `quality_checks=` list in `_emit_contract_and_readme()`, transform.py.
- **If confirmed, suggested fix**: Add `pct_levels_never_null_in_2024`: `SELECT COUNT(*) FROM {object} WHERE year = 2024 AND (pct_beginning_learner IS NULL OR pct_developing_learner IS NULL OR pct_proficient_learner IS NULL OR pct_distinguished_learner IS NULL)` with `mustBe: 0`. Contract-only change; gold bytes and parity unaffected.

## Notes

- schema_hash: `742035feecb442bade1cc132f06e55618033e24126147e6eb327bcaeb8f666e1`; validation 20 pass / 0 fail / 1 warning (2024 null-rate spikes, explained by the documented TFS broadening — bronze TFS 76,074 = 54.83% exact).
- v1 parity: **MATCH — byte-identical with v1 gold**. Both findings are description/contract-prose changes that do not alter gold parquet bytes, so fixing them preserves parity.
- Transform-agent claims audit: bronze=gold 906,229 ✓; categorical 22→22 / 9→6 / 11→11 unmapped 0 ✓; split race convention ✓ (math test ratio 1.0000 with separate pacific_islander rows); `_or_above` NULL-propagating + cap in (1.0, 1.005] ✓ (max raw component sum 1.001, all capped rows exactly 1.0); 2017 developing 3,001 zeros ✓ (but uniqueness claim falsified — Fix 1); 2024 suppressed-cell pcts preserved ✓ (T8/T9); level-sum undershoot 2023 ×1 (−3) / 2024 ×249 (−70 worst), zero overshoot ✓; curriculum year-ranges hold in gold ✓; NUM_TESTED_CNT TFS in every year incl. 2021-2023 (4,352/3,472/3,588) ✓ — the structure-doc correction is real and accurate.
- Sister-topic reconciliation (`georgia_milestones_end_of_course_eoc_assessment`, structure-doc item #22) skipped: sister gold not present locally in this rebuild phase.
- Structure-doc imprecisions found (cannot edit from this review; bundled into Fix 1's suggested fix): the zeros-uniqueness claim and the "2015 is the only file with genuine CSV nulls" quirk (2016-2019 also carry empty fields on fully-suppressed rows; pct-column suppression uses empty fields 2015-2019 and TFS strings 2021-2023). Neither affects gold values.
