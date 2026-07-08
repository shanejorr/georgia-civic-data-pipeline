# Data Review: act_scores

**Date**: 2026-06-10
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

The rebuild is faithful to bronze and the v1 parity delta is **fully explained**: gold is +5 rows vs v1 (70,927 vs 70,922), all in 2004, exactly the repaired `69::ALL9` → `699:ALL` Meriwether district row × 5 unpivoted test components; every other year's row count is identical to v1, and the 2022 placeholder-twin drop is row-and-value equivalent to v1's implicit dedup. All three repair proofs and the 20-twin claim verified directly in bronze. However, value-level spot checks surfaced two provable bronze defects the transform currently serves as real data — the 2007 county/city district-row swaps (3 pairs) and the 2009 Atlanta district row (scores ~17 points above the feasible bound) — plus a documentation regression: the 2016 writing_subscore scale anomaly (values 11.8–23.1 vs 4.6–8.5 in every other year) was documented in v1's README but is absent from the rebuilt contract.

## Manifest Verification

### Categorical maps

| Column | Entries | Bronze seen | Unmapped | Status |
|---|---|---|---|---|
| `test_component` | 12 | 12 (all map keys encountered) | 0 | PASS |

Full map review (every entry):

| Bronze value | Gold value | Correct? |
|---|---|---|
| `Composite` | `composite` | YES |
| `English` | `english` | YES |
| `Mathematics` | `mathematics` | YES |
| `Reading` | `reading` | YES |
| `Science` | `science` | YES |
| `Writing Subscore` | `writing_subscore` | YES |
| `Combined English Writing` | `combined_english_writing` | YES — distinct measure, correctly kept separate from `writing_subscore` |
| `Composite All Students` | `composite` | YES (Era 1/2 wide header) |
| `English All Students` | `english` | YES |
| `Mathematics All Students` | `mathematics` | YES |
| `Reading All Students` | `reading` | YES |
| `Science Reasoning All Students` | `science` | YES — "Science Reasoning" is ACT's pre-2011 label for the same Science section; merging is semantically right |

- 2a Completeness: every bronze value documented in `bronze-data-structure.md` appears in `bronze_values_seen`; no documented value was never encountered. PASS.
- 2c Contract cross-check: `gold_values_produced` (7 values) == contract `enum` (7 values). PASS.
- 2d Unmapped: `unmapped_count = 0`. PASS.
- 2e Asian/PI conflation: **N/A** — executed triage printed `SKIP: no demographic column`; gold has no `pct_asian` column. Era 1 demographic columns are dropped (unusable per structure doc §ETL-3), so no conflation surface exists.
- 2f Mutual exclusivity: **N/A — single convention** (no demographic column).

### Row-count reconciliation

| Year(s) | Bronze | Explicit filtered | Gold | Rule | OK? |
|---|---|---|---|---|---|
| 2004 | 519 | 1 (national row) | 2,590 | (519−1)×5 | YES |
| 2005–2007 | 523/526/540 | 0 | ×5 exactly | wide→long unpivot | YES |
| 2008–2010 | 543/556/555 | 0 | ×5 exactly | same | YES |
| 2011 | 2,785 | 0 | 4,037 | 2,785 school + 1,245 district + 7 state | YES |
| 2022 | 2,413 | 20 (all-null twins) | 3,481 | 2,393 school + 1,082 district + 6 state | YES |
| 2012–2021, 2023–2024 | — | 0 | ≈1.42–1.45× | school rows + materialized district/state | YES |

- 3b Actual parquet rows: **70,927** == manifest `total_gold`. PASS.
- Filter accounting: `national_benchmark_row: 1`, `all_null_duplicate_school_row: 20` — both logged and justified. PASS.
- Read loss: 0 events. PASS.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| `SysSchoolID` / `SysSchoolid` (Era 1/2) | `district_code` + `school_code` + detail level | MAPPED (split on first `:`, case-insensitive ALL, zfill 3/4) |
| `School Name` | — | CORRECTLY EXCLUDED (dimension attribute) |
| 5 × `{Component} All Students` (Era 1/2) | `avg_score` × `test_component` | MAPPED (unpivot) |
| `All Students Number Tested` (Era 1/2) | `num_tested` | MAPPED (repeated across the 5 component rows — documented) |
| 40 demographic score cols + 8 demographic count cols (Era 1) | — | CORRECTLY EXCLUDED (2004: populated only at state/national rows — verified 517/519 null; 2005: `' '` placeholders; 2006–07 blank) |
| `LONG_SCHOOL_YEAR` (Era 3/4) | `year` | MAPPED (ending year, cross-checked vs filename) |
| `SCHOOL_DISTRCT_CD` / `SCHOOL_DSTRCT_CD` | `district_code` | MAPPED (both spellings routed by era signature) |
| `SCHOOL_DSTRCT_NM`, `INSTN_NAME` | — | CORRECTLY EXCLUDED (dimensions) |
| `INSTN_NUMBER` | `school_code` | MAPPED (zfill 4) |
| `SUBGRP_DESC` | — | CORRECTLY EXCLUDED (guarded constant: transform raises if any value ≠ 'All Students') |
| `TEST_CMPNT_TYP_CD` | `test_component` | MAPPED |
| `INSTN_NUM_TESTED_CNT` / `INSTN_AVG_SCORE_VAL` | `num_tested` / `avg_score` (school rows) | MAPPED |
| `DSTRCT_*` / `STATE_*` | district / state rows | MAPPED (materialized via `unique()`, never re-aggregated) |
| `NATIONAL_*` | — | CORRECTLY EXCLUDED (out of scope) |
| `#ASSMT_CD`, `HIGHEST_RECENT_IND` (Era 4) | — | CORRECTLY EXCLUDED (`#ASSMT_CD` guarded == 'ACT') |

No gold column lacks a bronze ancestor (no fabrication).

## Value-Level Spot Checks

Extreme rows first:

1. **Global max `avg_score` = 35.5 (2009, district 761 Atlanta, reading, n=949) — MISMATCH WITH REALITY (bronze defect, see Fix 2).** Bronze `act_scores_2009.xls` row `761:ALL | Atlanta City | Composite 35.1 | English 34.2 | Math 35.1 | Reading 35.5 | Science 34.4 | 949`. Its own 14 school rows cover 945 of the 949 students with composites 15.4–20.2 (e.g. `761:182 Mays High School 17.8 | 204`, `761:4560 Grady High School 20.2 | 115`). Feasibility bound: even if all unattributed students scored 36, the district composite could not exceed 17.48. The transform copies bronze faithfully (gold == bronze), but the value is provably impossible.
2. **Global min `avg_score` = 4.2 (2011, district 730 / school 0190, writing_subscore, n=13) — MATCH.** Bronze 2011: `730 | 190 | Central Elementary/High School | Writing Subscore | DSTRCT 13/4.2 | INSTN 13/4.2`. Legitimate low writing-domain score.
3. **Global max `num_tested` = 62,743 (2013, state, composite) — MATCH.** Bronze 2013 `STATE_NUM_TESTED_CNT` is the constant `'62743'` with `STATE_AVG_SCORE_VAL '20.9'` on every Composite row.
4. **Global min `num_tested` = 1 (2004, district 732 Tattnall) — MATCH.** Bronze 2004: `732:ALL | Tattnall County | Composite None | 1` (and `732:194` school identical) — Era-1 implicit suppression (null score + tiny count) lands as NULL `avg_score` with `num_tested = 1`.

Ordinary traces (one per era, all columns):

- **Era 1, 2005, school `601:2050`** — bronze `17.4 / 16.3 / 17.6 / 17.3 / 17.7 | 23`; gold has exactly those five component rows with `num_tested = 23` each. MATCH. 2005 state row `All:All | State Of Georgia | Composite '20' | 23324` → gold state composite 20.0/23,324 and english 19.4/23,324 — the lowercase `All:All` sentinel classified correctly. MATCH.
- **Era 2, 2008, `601:103` (Appling)** — bronze `20.8 / 21.3 / 20.9 / 21.3 / 19.8 | 16`; gold school rows `0103` and district rows both match exactly (single-school district mirrors bronze). MATCH.
- **Era 3, 2011, `601:103`** — bronze 7 component rows; gold school `0103` composite 15.8/15, district composite 15.8/15 (from `DSTRCT_*`), state composite 19.8/28,789 (from `STATE_*`). `Combined English Writing` and `Writing Subscore` rows carry `TFS`/null at school+district → gold NULL/NULL, while state writing 6.8/18,162 survives. MATCH.
- **Era 4, 2024, `601:0103`** — bronze all four metric columns `TFS` at school and district; gold school and district rows all NULL/NULL; state composite 21.0/14,727 matches bronze `STATE_*`. MATCH (Era-4 `TFS`-in-score-columns handled).

Targeted verifications:

- **2004 `69::ALL9` repair (intentional change a)** — all three proofs verified in bronze: (a) `699` is the only district with school rows but no `:ALL` row in 2004, and `69::ALL9` is the only malformed ID in the file; (b) its count 35 = 14 (`699:300` Greenville) + 21 (`699:4050` Manchester); (c) composite 15.7 vs count-weighted blend (14.6×14 + 16.5×21)/35 = 15.74 (english 14.92, math 16.60, science 15.76 all blend within rounding). Gold 2004 now has district `699` rows: composite 15.7/35 etc., schools unchanged. 2005 bronze has a normal `699:All` row. VERIFIED.
- **2022 placeholder twins (intentional change b)** — bronze 2022 has exactly 40 duplicate-key rows over 20 distinct `(district, school, component)` keys: each pair is one data-carrying row + one `TFS`/null row under a renamed school (e.g. `608|0114` "Cass High School" `32|19.8` vs "New Cass High School" `TFS|None`; `675|3050` "McDonough High School" `66|16.6` vs "Henry County High School" `TFS|None`). Note the twins are `TFS`-marked in raw bronze and all-null only after the cast — consistent with the transform, which drops them post-cast. Gold keeps exactly the data-carrying values (Cass 32/19.8; McDonough 66/15.3–18.0), one row per key; the lone suppressed `writing_subscore` row for 675/3050 is correctly preserved as NULL/NULL. VERIFIED.
- **2006 §4b mask** — bronze has exactly 10 out-of-range values, precisely the documented two schools: `633:1054 Campbell HS 38.4/36.9/38.6/39.0/37.7 | 225` and `644:172 Cedar Grove HS 40.9/40.7/40.7/41.5/39.5 | 183`. Gold: all 10 `avg_score` NULL, `num_tested` 225/183 preserved on every row. VERIFIED.
- **2007 district-row swaps — NEW FINDING (Fix 1).** Bronze 2007: `643:ALL Decatur County = 22.6/22.5/22.5/23.3/21.7 | 61` is byte-for-byte Decatur High School (`773:3050`), while `773:ALL Decatur City = 18.3/18.1/17.7/18.8/18.6 | 72` is byte-for-byte Bainbridge High School (`643:3050`). Identical mirrored swaps for `619:ALL`↔`765:ALL` (Calhoun County ↔ Calhoun City: 62/20.9 vs 5/18.2) and `681:ALL`↔`779:ALL` (Jefferson County ↔ Jefferson City: 33/20.6 vs 5/15.4). In 2004, 2005, 2006, and 2008 each of these six single-school districts' `:ALL` row equals its own school's row exactly (e.g. 2006 `765:ALL Calhoun City 20.8|73` == `765:3050 Calhoun High School 20.8|73`); only 2007 mirrors the name-twin. The school rows carry the correct school names in 2007, so the `{district}:ALL` rows were swapped between county/city name twins at the source. Gold currently serves all six districts' 2007 aggregates swapped.

Suppression semantics (4f): all four marker regimes traced — Era 1 blank+count (2004 `732:ALL`), Era 2 `Too Few Students` (2008 `602:103 Atkinson` n=5 → gold NULL scores, count 5 preserved at school and district), Era 3 `TFS` counts + null scores (2011 `601:103` writing rows), Era 4 `TFS` in all four metric columns (2024 `601:0103`). PASS.

Sentinel year-attribution (4c): Era 3/4 derive `year` from `LONG_SCHOOL_YEAR` (`parse_school_year('2010-11') → 2011`, verified) with a hard cross-check against the filename; Era 1/2 use the filename (bronze carries no year column). PASS.

Derived-row reconciliation (4d): **N/A — aggregates come from bronze** (Era 1/2: published rollup rows; Era 3/4: `DSTRCT_*`/`STATE_*` context columns via `unique()`; divergence would create duplicate keys and trip the collision guard). Traced 2011 district 601 and state rows against bronze context columns — exact. The no-re-aggregation decision is right: GOSA suppresses school rows under n<10 while publishing unsuppressed aggregates.

Dedup tie-break (4e): **N/A** — each bronze file is one distinct year; eras do not overlap. The collision guard runs before dedup; manifest shows zero implicit dedup drops.

## Validation Cross-Read

- `_validation.json`: **20 pass / 0 fail / 1 warning** (precondition: `passed: true`, FRESH). `contract_parquet_schema` (63 files), `contract_quality_sql` (8 checks), `grain_uniqueness`, `foreign_keys` (190 district keys, 546 school keys resolve) all pass.
- The single warning (`null_rate_spikes`: num_tested/avg_score 2021/2022/2024 at 29–39% vs ~9–12% median) is explained and bronze-real: GOSA's n<10 suppression bites far more schools after ACT participation collapsed from 2021 (COVID + test-optional). Documented in the transform docstring, contract notes, and verified against bronze suppression rates. EXPLAINED.
- Contract `schema_hash`: `066aaae84c463e97cd65c1d94af2de8c7731ddbca060c1fd1c52acae38431bd1`.
- §4b masking audit: one mask, `_null_invalid_act_scores` — count + sample logged at runtime; handling documented in the `avg_score` contract description; `value_min: 1` / `value_max: 36` pinned so the derived range check stays enforceable. PASS (masked count is log-only, not persisted in the manifest — minor, see Notes).
- §15b coverage judgment: the four authored checks (`avg_score_requires_positive_num_tested`, `state_rows_never_suppressed`, `combined_english_writing_year_range`, `writing_subscore_year_range`) plus four derived checks cover the topic's main invariants. One real invariant is un-authored: writing_subscore's scale (≤ 8.5 in every year except 2016) — see Fix 3. A district-vs-school feasibility check is *not* authorable until the 2010 judgment item is resolved (it would fail on known bronze inconsistencies).
- v1 parity output (verbatim):

```
DIFFERS from v1
  v1:  97f26e7fb0402e6786484b0b8b4569fa02bbcb46890fd81a5aee0ddb4a5c5bb4
  now: 1a64a33e569a266e1961e7cd1f1078a1ed5a5a3ea45515e784a3aca68bf7faa0
```

**DIFFERS is fully explained.** Against `git show v1-pipeline:` artifacts: v1 total 70,922 vs current 70,927 (**+5**); v1 2004 = 2,585 (860 district / 1,720 school / 5 state) vs current 2,590 (865 / 1,720 / 5) — the +5 is exactly the repaired `699:ALL` district row unpivoted to 5 component rows, at district detail only. **All 20 other years match v1's per-year totals exactly.** The 2022 twin handling is row-equivalent (both 3,481: v1's dedup with `sort_col="num_tested"` kept the same data-carrying rows the rebuild now keeps via the explicit pre-guard drop) and the 2006 §4b mask exists in both v1 and the rebuild (v1's tagged `gold-data-structure.md` claiming "preserve bronze fidelity", max 41.5, is stale — generated 2026-05-25 before v1's own fix; the v1 transform and README confirm the mask). No other delta source found.

## Cross-Era Consistency

- Overlap years: none (one file per year). N/A.
- Era-boundary continuity: state composite series is smooth across all four era boundaries (2007→2008: 20.3→20.6; 2010→2011: 20.7→19.8; 2023→2024: 20.7→21.0). The overall `avg_score` mean dip from 2011 (19.1→17.3) is compositional — `writing_subscore` (2–12 scale) and `combined_english_writing` enter the mix — not a scale bug. No >10x jumps. PASS.
- Cross-year NULL sweep: executed; **no FLAG and no INVESTIGATE lines** — no era-localized rename bug signature (Risk 2 ruled out).
- State `num_tested` basis shifts in bronze (39,436 in 2010 → 28,789 in 2011 → 58,112 in 2012) are bronze-real (traced) — see Notes.

## Transform Logic Risks

| Risk | Severity | Details |
|---|---|---|
| Silent column drops | PASS | `_require_columns` hard-stops on missing expected columns; Era-1 demographic drop is logged with rationale |
| Era routing | PASS | Signatures most-specific-first; manifest confirms 2004–07→era_1, 2008–10→era_2, 2011–23→era_3, 2024→era_4 |
| Filter logic logged + justified | PASS | 1 national row + 20 twins via `record_filtered`; malformed-ID guard fired 0 times beyond the pinned repair |
| Normalization map completeness | PASS | 12/12 bronze values seen, `replace_strict(default=None)` + manifest unmapped guard would surface unknowns |
| `strict=False` casts | PASS | String round-trip handles `' '`, `'Too Few Students'`, `TFS`, trailing-dot `'1374791.'`; per-year null counts match bronze suppression exactly (e.g. 2008: 64 suppressed entities × 5 = 320 nulls) |
| Dedup keys + tie-break | PASS | Collision guard *before* dedup; tie-break only a documented safety net (no within-file dups remain post twin-drop) |
| Year extraction | PASS | Filename (Era 1/2); `LONG_SCHOOL_YEAR` ending year with filename cross-check (Era 3/4) |
| §4b mask (5b) | PASS | Logged, contract-documented, range-pinned |

## Required Fixes

### Fix 1: Repair the three swapped 2007 county/city district rows
- **Severity**: HIGH
- **Issue**: In the 2007 bronze, the `{district}:ALL` rows for three county/city name-twin pairs are swapped — Calhoun County (619) ↔ Calhoun City (765), Decatur County (643) ↔ City Schools of Decatur (773), Jefferson County (681) ↔ Jefferson City (779). Gold serves all six districts' 2007 aggregates (5 components × num_tested + avg_score = 60 values) attributed to the wrong district.
- **Evidence**: Bronze 2007: `643:ALL Decatur County | 22.6/22.5/22.5/23.3/21.7 | 61` equals `773:3050 Decatur High School` exactly, while `773:ALL Decatur City | 18.3/18.1/17.7/18.8/18.6 | 72` equals `643:3050 Bainbridge High School` exactly; same exact mirroring for 619↔765 (`62|20.9` vs `5|18.2`) and 681↔779 (`33|20.6` vs `5|15.4`). In 2004, 2005, 2006, and 2008 each of these single-school districts' `:ALL` row equals its own school's row exactly (e.g. 2006: `765:ALL Calhoun City 20.8|73` == `765:3050 Calhoun High School 20.8|73`). The school rows carry correct school names/IDs in 2007 — only the district rows are crossed.
- **Location**: `_transform_era12` / a new pinned-repair structure alongside `SYS_ID_REPAIRS` in `src/etl/education/gosa/act_scores/transform.py`
- **Suggested fix**: Pin a 2007-only district-row swap repair (e.g. `DISTRICT_ROW_SWAPS_2007 = {"619": "765", "643": "773", "681": "779"}` applied symmetrically to `{d}:ALL` rows in the 2007 file only), logged like the `69::ALL9` repair, with the four-year mirror proof in the docstring and a contract note. Equivalently acceptable: since all six are single-school districts in 2007, set each district row equal to its own school row. (Conservative alternative — NULL all six districts' 2007 metrics — discards data that has a provable repair; the pinned swap is recommended and consistent with the `SYS_ID_REPAIRS` philosophy.)

### Fix 2: NULL the five infeasible 2009 Atlanta (761) district scores per §4b
- **Severity**: HIGH
- **Issue**: The 2009 bronze district row for Atlanta City (`761:ALL`) publishes avg scores of 34.2–35.5, roughly double the district's true level; gold serves them as real, making Atlanta the top ACT district statewide in 2009 by ~14 points.
- **Evidence**: Bronze `act_scores_2009.xls`: `761:ALL | Atlanta City | 35.1/34.2/35.1/35.5/34.4 | 949`. Its own 14 school rows cover 945 of 949 students with composites 15.4–20.2 (count-weighted composite ≈ 17.4). Feasibility: even if the 4 unattributed students scored a perfect 36, the district composite is bounded at 17.48 (executed bound per component: composite ≤ 17.48, english ≤ 16.71, math ≤ 17.52, reading ≤ 17.70, science ≤ 17.59) — published values exceed the bound by ~17 points. The row's `num_tested` (949 ≈ 945 school sum) is plausible and internally consistent.
- **Location**: extend the §4b handling near `_null_invalid_act_scores` in `src/etl/education/gosa/act_scores/transform.py`
- **Suggested fix**: Pin a §4b mask for `(year=2009, district_code='761', school_code IS NULL)`: NULL the five `avg_score` values, preserve `num_tested` and the rows, log the count, and document the defect in the `avg_score` contract description (same pattern as the 2006 Campbell/Cedar Grove mask). No arithmetic repair exists (the true values are unrecoverable from this file), so NULL is correct here.

### Fix 3: Document the 2016 writing_subscore scale anomaly in the contract
- **Severity**: MEDIUM
- **Issue**: Gold 2016 `writing_subscore` values run 11.8–23.1 (mean 17.2) while every other year runs 4.2–8.5 (mean ≈ 6.6) — ACT's September 2015–June 2016 "enhanced writing" window reported writing on a 1–36 scale. The current contract description states writing_subscore is "on the ACT writing domain 2-12 scale (typical statewide averages 6-7)" with no 2016 exception, so consumers doing time series will read 2016 as a doubling. v1's README documented this exception explicitly ("except for 2016, the experimental window in which ACT reported Writing on a 1-36 scale"); the rebuild dropped it — a documentation regression.
- **Evidence**: Executed per-year range: 2015 min/max = 5.1/7.9; **2016 = 11.8/23.1 (mean 17.22)**; 2017 = 5.0/8.2. Data is bronze-faithful (no data change needed).
- **Location**: `_emit_contract_and_readme` (`avg_score` column description and/or `notes`) in `src/etl/education/gosa/act_scores/transform.py`
- **Suggested fix**: Add the 2016 scale exception to the `avg_score` description and a `notes` entry. Optionally author a quality check making the writing scale enforceable: `SELECT COUNT(*) FROM {object} WHERE test_component = 'writing_subscore' AND year != 2016 AND avg_score > 12` must be 0 (passes today; would catch future scale/column-swap errors).

## NEEDS_JUDGMENT

### Judgment Call 1: 2010 district rows are systematically inconsistent with their school rows in bronze
- **Severity if confirmed**: MEDIUM
- **Suspicion**: The 2010 bronze file's `{d}:ALL` district rows were computed on a different student basis than its school rows (or are partially erroneous). ~30 districts' published district means fall outside the mathematically feasible range implied by their own school rows, in both directions — unlike 2008 and 2009, which are clean (Atlanta 761 aside).
- **Evidence available**: All verified in bronze, not just gold. `615:ALL Bryan County | Composite 19.6 | 89` vs schools Richmond Hill `22|77` + Bryan County HS `17.3|12` → weighted 21.37 with zero unattributed students (district 1.8 below the floor). `792:ALL Valdosta City | Science 14.6 | 111` vs its only school Valdosta HS `18.2|110` → the one extra student would need an impossible score of −214. `623:ALL Catoosa County | 263` vs its three schools summing 340 testers (district count 77 below its own schools). The 2010 state count (39,436) is also an outlier vs 2009 (30,548) and 2011 (28,789). Ruled out: stale-copy from 2009 (0% of 2010 rows match 2009) and 2011-vintage data (no match).
- **Why uncertain**: Both row sets come from the same bronze file and neither is provably the wrong one; the pattern (both directions, ~30 districts, plus a state-count outlier) suggests a cohort/basis difference (e.g. graduating-class vs all-examinees) rather than row-level typos. Unlike Fixes 1–2 there is no provable repair, and NULLing 30 districts' aggregates on an unconfirmed theory would destroy plausibly-official data.
- **Location**: bronze `act_scores_2010.xls`; would touch `_transform_era12` and contract notes if acted on
- **If confirmed, suggested fix**: Minimum — add a contract `notes` caveat that 2010 district aggregates are internally inconsistent with 2010 school rows and the basis is unknown. Aggressive option — NULL only the provably infeasible district values (the feasibility-bound violators), logged as §4b. Recommend the documentation note unless GOSA provenance can settle the basis question.

## Notes

- Contract `schema_hash`: `066aaae84c463e97cd65c1d94af2de8c7731ddbca060c1fd1c52acae38431bd1`; validation 20 pass / 0 fail / 1 warning (explained); 63 parquet files (21 years × 3 detail levels), 70,927 rows.
- v1 parity: DIFFERS, fully accounted — +5 rows, all 2004 district-level (`699:ALL` repair × 5 components); all other years' counts identical to v1. Byte-level identity of non-2004 years cannot be verified (v1 parquet isn't retained; only the aggregate hash), but per-year counts, identical mask/dedup semantics, and value spot checks support no other delta.
- `bronze-data-structure.md` miscounts 2005's row classification (says 175 district / 347 school; bronze actually has 173 / 349 — recounted with the same case-insensitive `:ALL` rule). The transform matches bronze; the doc is wrong. Cosmetic.
- The §4b masked count (10) is visible in the run log but not persisted in `_transform_manifest.json`; a `masked` section in `TransformManifest` would make the §4b audit artifact-driven. Enhancement, not a defect.
- State `num_tested` swings in Era 3 bronze (28,789 in 2011 → 58,112 in 2012 → 62,743 in 2013 → 44,185 in 2014) are bronze-real reporting-basis changes at the source; consider a contract note if consumers use state counts as a participation series.
- Era 1/2 `num_tested` is per-entity (repeated across the 5 component rows) — correctly documented in the contract with the double-counting warning.
