# Data Review: revenues_and_expenditures

**Date**: 2026-06-12
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Gold is byte-identical with the approved v1 baseline (**v1 parity MATCH**, sha `b464f247…`) and every
value-level trace, categorical mapping, row-count reconciliation, and aggregate feasibility screen passes —
zero row loss across all 14 files (499,468 bronze = 499,468 gold), the DOE OTHER split arithmetic ties out
exactly, and the Era 3 FTE-division claim verifies independently. One MEDIUM fix is required, and it is
prose-only (no parquet change, parity preserved): the contract materially understates the per-FTE artifact in
the 2024 file, where `dollars_per_fte == rev_exp_value` verbatim on **100% of nonzero school-detail rows**
(15,678 School-label + 3,197 DOE OTHER) — not just on DOE OTHER rows as documented — so the contract's
guidance to "filter to school-detail rows and confirm the entity is a traditional school" yields wrong
per-pupil numbers for 2024.

## Manifest Verification

### Categorical maps

| Column | Map entries | Bronze values seen | Unmapped | Status |
| --- | --- | --- | --- | --- |
| `rev_exp_type` | 2 | 2 (matches structure doc) | 0 | PASS |
| `category` | 17 | 17 (matches structure doc, incl. `School food Services` typo) | 0 | PASS |
| `detail_level` | 5 (incl. synthetic rollup key) | 5 (Era 1 only — Era 2–4 detail is derived, no bronze label) | 0 | PASS |

### Full map review

**rev_exp_type** — both entries semantically correct:

| Bronze | Gold | Correct? |
| --- | --- | --- |
| `K-12 Revenues` | `k12_revenues` | YES |
| `K-12 Expenditures` | `k12_expenditures` | YES |

**category** — all 17 entries are mechanical snake_case of unambiguous functional-category labels; each verified:
`Debt Services→debt_services`, `Federal→federal`, `General Administration→general_administration`,
`Instruction→instruction`, `Instructional Support→instructional_support`, `Local→local`,
`Maintenance and Operations→maintenance_and_operations`, `Media→media`, `Other→other`,
`Pupil Services→pupil_services`, `Renovation and Capital Projects→renovation_and_capital_projects`,
`School Administration→school_administration`, `School food Services→school_food_services` (upstream
lowercase-`food` typo, correctly normalized), `State Lottery→state_lottery`, `State Other→state_other`,
`State QBE→state_qbe`, `Transportation→transportation`. All YES. The revenue/expenditure containment split
(6 revenue-source vs 11 expenditure-function categories) is semantically right and enforced by
`rev_exp_type_category_pairs_valid`.

**detail_level** (Era 1 explicit column; Era 2–4 derive from `ALL` sentinels):

| Bronze | Gold | Correct? |
| --- | --- | --- |
| `State` | `state` | YES |
| `District` | `district` | YES |
| `School` | `school` | YES |
| `DOE OTHER` | `school` | YES — option (a) from the bronze doc; the same entities (codes 6xxx/7xxx/8xxx central offices, GNETS, Pre-K) sat under `school` in Era 2–4 via the ALL-marker heuristic. Verified: 9,526 rows/year in both 2023 and 2024 bronze. |
| `DOE OTHER (INSTN_NUMBER=ALL)` (synthetic) | `district` | YES — bronze grep confirms exactly 272 such rows/year and their district codes are exactly the 16 RESA codes `850 852 854 856 858 860 862 864 866 868 872 876 880 884 886 888`. Gold carries exactly 272 RESA district rows (16 × 17 pairs) in **every** year 2011–2024, so the routing reproduces the pre-Era-1 convention precisely. |

Bronze evidence for the split (2024 file): `grep -c '"DOE OTHER"'` → 9798; of those,
`grep -c '"ALL","All Column Values"'` → 272 (identical in 2023). Manifest `reclassified` events
(9,526 → school, 272 → district, per year) match exactly.

- **2a completeness**: every distinct bronze value documented in the structure doc appears in
  `bronze_values_seen`; nothing documented was missed (no skipped era / routing gap). PASS.
- **2c contract cross-check**: `gold_values_produced` equals the contract `enum` for `rev_exp_type` (2)
  and `category` (17). `detail_level` is filename-encoded (no contract column); `detail_levels`
  custom property `[schools, districts, states]` matches the 3 produced values. PASS.
- **2d unmapped**: `unmapped_count` 0 on all three columns. PASS.
- **2e Asian/PI conflation**: **N/A** — no `demographic` column in gold (confirmed on parquet) and no
  demographic breakout in bronze; `grep -iE 'pacific|nhpi'` on the structure doc → no NHPI label.
- **2f mutual exclusivity**: **N/A** — no demographic column.

### Row-count reconciliation

| Year | Bronze | Gold | Filtered | Expansion | Detail split (state/district/school) |
| --- | --- | --- | --- | --- | --- |
| 2011 | 40,187 | 40,187 | 0 | 1.0 | 17 / 3,485 / 36,685 — matches doc spot count |
| 2012 | 38,973 | 38,973 | 0 | 1.0 | 17 / 3,536 / 35,420 |
| 2013 | 28,541 | 28,541 | 0 | 1.0 | 17 / 3,587 / 24,937 |
| 2014 | 28,375 | 28,375 | 0 | 1.0 | 17 / 3,553 / 24,805 |
| 2015 | 28,391 | 28,391 | 0 | 1.0 | 17 / 3,536 / 24,838 |
| 2016 | 28,538 | 28,538 | 0 | 1.0 | — |
| 2017 | 40,221 | 40,221 | 0 | 1.0 | — |
| 2018 | 28,605 | 28,605 | 0 | 1.0 | — |
| 2019 | 40,757 | 40,757 | 0 | 1.0 | — |
| 2020 | 39,143 | 39,143 | 0 | 1.0 | 17 / 3,893 / 35,233 |
| 2021 | 39,283 | 39,283 | 0 | 1.0 | 17 / 3,978 / 35,288 |
| 2022 | 39,350 | 39,350 | 0 | 1.0 | 17 / 4,012 / 35,321 — matches doc spot count |
| 2023 | 39,473 | 39,473 | 0 | 1.0 | 17 / 4,080 / 35,376 (3,808 District + 272 rollups; 25,850 School + 9,526 DOE OTHER) |
| 2024 | 39,631 | 39,631 | 0 | 1.0 | 17 / 4,216 / 35,398 (3,944+272; 25,872+9,526 — matches doc breakdown exactly) |
| **Total** | **499,468** | **499,468** | **0** | | actual parquet rows counted: **499,468** = manifest `total_gold` |

Zero loss, zero filtering, all 14 expected years present, era assignment in `files_processed` matches the
structure doc (2011→era_2_4, 2012–2014→era_3, 2015–2022→era_2_4, 2023–2024→era_1). The 28k-vs-40k row-count
fluctuation across years is a bronze composition characteristic (some years include ~3,000 extra
non-traditional entities), mirrored 1:1 into gold. PASS.

## Column Coverage

| Bronze column | Gold column | Status |
| --- | --- | --- |
| SCHOOL_YEAR / LONG_SCHOOL_YEAR | `year` | MAPPED (parsed spring year, cross-checked vs filename) |
| DISTRICT_CODE / SCHOOL_DSTRCT_CD | `district_code` | MAPPED (ALL→NULL, zfill(3), 7-char preserved) |
| SCHOOL_CODE / INSTN_NUMBER | `school_code` | MAPPED (ALL→NULL, zfill(4)) |
| Revenues/Expenditures / REVENUES/EXPENDITURES | `rev_exp_type` | MAPPED |
| Description / DESCRIPTION | `category` | MAPPED |
| REV_EXP_VALUE | `rev_exp_value` | MAPPED |
| Dollars per FTE / DOLLARS_PER_FTE | `dollars_per_fte` | MAPPED |
| DETAIL_LVL_DESC (Era 1) / derived (Era 2–4) | `detail_level` → file split | MAPPED (filename-encoded per domain convention) |
| DISTRICT_NAME / SCHOOL_DSTRCT_NM | — | CORRECTLY EXCLUDED (dimension attribute) |
| SCHOOL_NAME / INSTN_NAME | — | CORRECTLY EXCLUDED (dimension attribute) |
| GRADES_SERVED_DESC (Era 1) | — | CORRECTLY EXCLUDED (school metadata, dimension-bound) |
| FTE_COUNT (Era 3) | — | CORRECTLY EXCLUDED (3/14 years; per-FTE = value/FTE verified to 0.005 before drop — independently re-verified, see below) |
| #RPT_NAME (Era 1) | — | CORRECTLY EXCLUDED (constant; guarded with a hard-stop on unexpected values) |

No gold column lacks a bronze ancestor (no fabrication). The structure doc's Gold Schema Classification
lists `doe_other` as a possible fourth `detail_level` value; the transform instead implemented the doc's own
ETL-Considerations **option (a)** (DOE OTHER → school/district), which matches the domain's three-level
convention, `salaries_and_benefits`, and the v1 baseline. Consistent — no fix.

## Value-Level Spot Checks

All 13 traces MATCH. Extreme rows first (bronze lines quoted verbatim):

| Trace | Bronze (file, quoted) | Gold | Verdict |
| --- | --- | --- | --- |
| Global MAX `rev_exp_value` | 2024 line 4: `"Revenue_and_Expenditures","2023-24","State","ALL",…,"K-12 Expenditures","Instruction",14381049432.94,8249.37` | (2024, NULL, NULL, k12_expenditures, instruction) = 14381049432.94 / 8249.37 | MATCH |
| Global MIN `rev_exp_value` | 2013 line 9524: `"2012-13","644","DeKalb County","ALL",…,"K-12 Revenues","State Other",-48563362.27,-492.75,98555` | (2013, 644, NULL, k12_revenues, state_other) = −48563362.27 / −492.75 | MATCH (also −48,563,362.27 / 98,555 ≈ −492.75 ✓ FTE relationship) |
| Global MAX `dollars_per_fte` | 2012: `2011-12,633,Cobb County,8010,Central Office,K-12 Expenditures,Instruction,592534988.8,592534988.8,` (FTE empty) | (2012, 633, 8010) = 592534988.8 / 592534988.8 | MATCH — documented null-FTE artifact row, preserved |
| Global MIN `dollars_per_fte` | 2021: `"2020-21","675","Henry County","8014","Other Auxillary Facility","K-12 Expenditures","Instruction",-37959538.34,-37959538.34` | (2021, 675, 8014) = −37959538.34 / −37959538.34 | MATCH — negative adjustment on a non-school entity, preserved |

Ordinary traces, one per era plus decision-specific traces:

| Trace | Bronze (quoted) | Gold | Verdict |
| --- | --- | --- | --- |
| Era 4 school | 2011: `"2010-11","644","DeKalb County","0101","Avondale Middle School",…,"Instruction",3217934.46,6272.78` | 3217934.46 / 6272.78 | MATCH |
| Era 4 state (ALL→NULL) | 2011: `"2010-11","ALL",…,"ALL",…,"Debt Services",24540144.57,14.86` | (2011, NULL, NULL) = 24540144.57 / 14.86 | MATCH |
| Era 3 school | 2013: `"2012-13","712","Pickens County","0189",…,"Instructional Support",9897.31,20.53,482` | 9897.31 / 20.53 | MATCH (20.53 ≈ 9897.31/482 ✓) |
| Era 3 zfill | 2012: bronze school code `177` (Appling County Elementary, district 601), `…,"Instruction",2502181.26,4650.89` | (2012, 601, **0177**) = 2502181.26 / 4650.89 | MATCH — 17,655 short-code 2012 rows all padded; gold school_code lengths = {4}, zero codes <4 chars |
| Era 3 state | 2012: `2011-12,ALL,…,ALL,…,Debt Services,22441795.23,13.54,1656992` | (2012, NULL, NULL) = 22441795.23 / 13.54 | MATCH |
| Era 2 school | 2022: `"2021-22","704","Morgan County","0191",…,"School Administration",377969.47,550.98` | 377969.47 / 550.98 | MATCH |
| Era 1 school + year attribution | 2023: `"Revenue_and_Expenditures","2022-23","School","625",…,"2068","Andrea B Williams Elementary School",…,"Debt Services",0.00,0.00` | (year **2023**, 625, 2068) = 0.0 / 0.0 | MATCH — `2022-23` → 2023 ✓ |
| Era 1 DOE OTHER → district | 2024: `…,"DOE OTHER","850","Northwest Georgia RESA","ALL","All Column Values",…,"General Administration",482928.15,482928.15` | (2024, 850, **NULL**) districts slice = 482928.15 / 482928.15 | MATCH |
| Era 1 DOE OTHER → school | 2024: `…,"DOE OTHER","644","DeKalb County","6015","International Student Center",…,"Instruction",4191749.41,4191749.41` | (2024, 644, **6015**) schools slice = 4191749.41 / 4191749.41 | MATCH |

- **4c sentinel year-attribution**: each file carries exactly one embedded school year; the transform
  parses it and **hard-fails** if it disagrees with the filename year. Traced: 2023 file (`2022-23`) → gold
  year 2023; 2012 file (`2011-12`) → gold year 2012. PASS.
- **4d aggregate feasibility (aggregates come from bronze)**: (i) district vs school sums — for 2011/644,
  2022/644, 2024/644, 2024/625 the school sums equal the district row to ratio 1.000 in every expenditure
  category; for 2013/712, 2018/704 school sums ≤ district (composition drift: district-held funds, e.g.
  debt services). (ii) Impossibly-low screen: 6 rows had a single school exceeding its district row by >2%;
  in **all 6** the school *sum* equals the district row exactly (e.g. 2021/747 transportation: district
  5,770,303.82 = school sum 5,770,303.82, max school 6,769,379.06 — negative sibling rows explain it).
  No swaps, no garbling. (iii) State vs district sums — instruction-scale categories reconcile at ~1.00;
  small categories deviate (see NEEDS_JUDGMENT 2). PASS at the fact level.
- **4e dedup tie-break**: **N/A** — one file per year, no overlap years (`files_processed` confirms);
  collision guard ran before the safety-net dedup.
- **4f suppression semantics**: **N/A** — no suppression markers anywhere; independently confirmed:
  `rev_exp_value` has 0 NULLs in all years; `dollars_per_fte` NULLs are exactly the 667 bronze-empty cells
  (13/382/272 in 2012/2013/2014), not cast casualties.
- **Era 3 FTE-drop verification (independent)**: for all three files, max |`Dollars per FTE` −
  `REV_EXP_VALUE`/`FTE_COUNT`| = **0.005000** where FTE is non-null/non-zero (rounding). 2012: all
  **10,414/10,414** null-FTE rows carry per-FTE == value verbatim; the file's 13 per-FTE NULLs sit exactly
  on FTE=0 rows; the other 20 FTE=0 rows are 0/0. 2013: 382 per-FTE NULLs exactly where FTE NULL; 2014:
  272 likewise. The transform's documented claims all hold.

## Validation Cross-Read

- `_validation.json`: **21 pass / 0 fail / 0 warning** at 2026-06-12T12:16:41Z, `passed: true`.
  `contract_parquet_schema` (42 files), `contract_quality_sql` (all 8), `grain_uniqueness`
  (year, district_code, school_code, rev_exp_type, category), `foreign_keys` (254 district keys,
  3,880 school keys all resolve), and geography nulling ×3 all pass.
- Contract `schema_hash`: `5fb333f25290ab469febda5d0737236e962192710fccbd0763bf8ee25fd7bfc6`.
- **§4b masking audit**: no `_null_*` helpers in transform.py, no `masked_values` manifest section,
  `suppressed_to_null: false` in the contract — consistent; signed currency has no impossible values.
  PASS (nothing unrecorded).
- **§15b coverage judgment**: the 5 authored checks (type↔category containment, rev_exp_value never NULL,
  per-FTE NULLs confined to 2012–2014, exactly 17 state rows/year, every district entity carries all 17
  pairs) pin this topic's real invariants. The two candidate additions are *not* authorable: state ≠ sum of
  district rows in small categories (source netting, see NEEDS_JUDGMENT 2) and district ≠ school sum in all
  categories (district-held funds). Coverage adequate. PASS.
- **v1 parity** (re-run independently):

  ```
  MATCH — byte-identical with v1 gold
  v1 : b464f2470ab1964eb92ecd49e989cbadfb8c9858f26db015aaa741b5521ade0e
  now: b464f2470ab1964eb92ecd49e989cbadfb8c9858f26db015aaa741b5521ade0e
  ```

## Cross-Era Consistency

- **Overlap years**: none (14 files, 14 distinct years).
- **Era-boundary continuity (3d)**: state-level revenue and expenditure sums move smoothly across every
  adjacent pair, including both era boundaries (2011→2012 era_2_4→era_3: 0.95/1.01; 2014→2015
  era_3→era_2_4: 1.06/1.05; 2022→2023 era_2_4→era_1: 1.07/1.09). Max YoY ratio anywhere: 1.12. No >10x
  jumps, no cumulative-publication signature. State instruction per-FTE runs 5,232 → 8,249 monotonically-ish
  across 14 years — plausible.
- **Cross-year NULL sweep (3c)**: no column is ≥95% NULL in any year; no 100%-NULL columns. The only metric
  NULLs are the 667 documented Era 3 per-FTE rows.
- **RESA convention**: exactly 272 RESA-coded district rows (16 agencies × 17 pairs) in every year
  2011–2024 — the Era 1 DOE OTHER→district routing exactly reproduces the pre-2023 ALL-marker outcome.
- **Per-FTE artifact incidence by year** (nonzero school-detail rows where dpf==value): ~18–19% in the
  40k-row years (2011, 2012, 2017, 2019–2023 — the non-traditional entities), ~0% in the 28k-row years
  (2013–2016, 2018), and **100% in 2024** (see Required Fix 1).

## Transform Logic Risks

| Risk | Severity | Verdict / details |
| --- | --- | --- |
| Silent column drops | — | PASS — every drop documented and classified (names→dims, FTE_COUNT verified-then-dropped, #RPT_NAME constant-guarded, GRADES_SERVED_DESC dim-bound) |
| Era routing correctness | — | PASS — signature match most-specific-first (era_1, era_3 before era_2_4); `files_processed` confirms all 14 assignments; `_require_columns` hard-stops on missing columns |
| Filter logic | — | PASS — no filters; 0 filtered, 0 read loss |
| Normalization map completeness | — | PASS — 2+17(+5) entries exactly cover the structure doc's documented values |
| `strict=False` casts | — | PASS — defensive only; verified zero cast-induced NULLs (667 dpf NULLs are bronze-empty cells) |
| Dedup keys + tie-break | — | PASS — collision guard raises before dedup; dedup is a safety net (no duplicates exist); `sort_col="rev_exp_value"` documented |
| Year extraction | — | PASS — single embedded school year parsed, cross-checked against filename, hard-fail on disagreement |
| §4b masking (5b) | — | PASS — no masks; none needed (signed currency) |

## Required Fixes

### Fix 1: Contract understates the 2024 per-FTE artifact — all 2024 school-detail rows, not just DOE OTHER
- **Severity**: MEDIUM
- **Issue**: The contract's `dollars_per_fte` description and notes attribute the dpf==value artifact to
  "2023-2024 DOE OTHER specialty-program rows" and the 2012 null-FTE rows, and advise consumers to
  "Filter to school-detail rows and confirm the entity is a traditional school before treating it as
  per-pupil spending." In the **2024 file this guidance is wrong**: the source publishes
  `DOLLARS_PER_FTE == REV_EXP_VALUE` verbatim on **every** nonzero school-detail row — traditional schools
  included — so 2024 school-level `dollars_per_fte` carries no per-pupil information at all. A consumer
  following the contract would read, e.g., Bloomingdale Elementary's 2024 "per-FTE" Media spend as $96,247.94
  (it is the school's *total*). The data itself is bronze-faithful; this is a contract-prose accuracy defect.
- **Evidence**: Bronze 2024, dpf==value among nonzero-value rows by detail level: `School` **15,678 of
  15,678**, `DOE OTHER` 3,197 of 3,197, `District` 0 of 3,018, `State` 0 of 16. Contrast bronze 2023:
  `School` 151 of 14,624, `DOE OTHER` 3,098 of 3,098, `District`/`State` 0. Quoted bronze 2024 School row:
  `"Revenue_and_Expenditures","2023-24","School","625","Savannah-Chatham County","4052","Bloomingdale
  Elementary School","PK,KK,01,02,03,04,05","K-12 Expenditures","Media",96247.94,96247.94`. Gold mirrors
  bronze exactly (2024 schools slice: 18,747/18,747 nonzero rows artifact = 15,678 School + 3,197 DOE OTHER
  − 128 nonzero rollups routed to districts; the 128 reappear as the only 2024 district-slice artifacts).
  This also explains the manifest's 2024 dpf mean jump (578,754 vs 120,384 in 2023).
- **Location**: `_emit_contract_and_readme()` in
  `src/etl/education/gosa/revenues_and_expenditures/transform.py` — `dollars_per_fte` column `description`,
  the `notes` entry on the dpf==value artifact, and `limitations`.
- **Suggested fix**: Amend the prose to state that in the 2024 file (school year 2023-24) the source
  publishes `dollars_per_fte` equal to `rev_exp_value` on all school-detail rows, so per-FTE values at
  school detail are unusable for 2024 (only district- and state-level 2024 rows carry true per-FTE
  amounts); keep the existing DOE OTHER / 2012 caveats. Re-run the transform to re-emit the contract —
  prose-only, parquet bytes unchanged, v1 parity preserved. Also amend the bronze doc sentence "The
  anomalously large DOLLARS_PER_FTE values come from DOE OTHER rows" (Era 1 statistics section), which is
  incomplete for 2024.

## NEEDS_JUDGMENT

### Judgment Call 1: Preserve vs mask the dpf==value artifact rows (incl. the 2024 school-detail blanket)
- **Severity if confirmed**: LOW
- **Suspicion**: `dollars_per_fte` values that verbatim equal `rev_exp_value` (2024: all school-detail rows;
  2023: all DOE OTHER school rows; 2012: all 10,414 null-FTE rows; scattered non-school entities in other
  years) are provably not per-FTE amounts and could be argued to be §4b "known-bad" → NULL candidates.
- **Evidence available**: counts above; all values trace bronze-verbatim; v1 preserved them identically
  (parity MATCH).
- **Why uncertain**: §4b masks *impossible* values; these are published-as-is report artifacts on an
  unbounded currency scale — extreme-but-conceivable, the category §4b says to preserve + document. Masking
  ~19k 2024 rows would also break v1 parity and discard the (still meaningful) information that GOSA
  published the column un-normalized.
- **Location**: era transforms in `transform.py` (would be a conditional `_null_*` mask).
- **If confirmed, suggested fix**: NULL `dollars_per_fte` where it equals `rev_exp_value` on school-detail
  rows in affected years, with a manifest `masked_values` record. **Recommendation: do not mask — preserve +
  document (Fix 1), consistent with §4b, the prior deferred LOW item, and v1.**

### Judgment Call 2: State rows are not the sum of district rows in small categories — add a contract caveat?
- **Severity if confirmed**: LOW
- **Suspicion**: none of transform error — values are bronze-verbatim. The published state row sits far below
  the district sum for small categories, which could mislead consumers who try to reconcile levels.
- **Evidence available**: state vs district-sum ratios: instruction-scale categories ≈ 1.000 in every year,
  but 2014 renovation_and_capital_projects: state 2,223,918.32 vs district sum 11,815,000 (ratio 5.31);
  debt_services 2021–2024: ratios 2.2–3.7; k12_revenues `other` 2014/2021: 1.6–2.0. State row traced
  bronze-verbatim: `"2013-14","ALL",…,"K-12 Expenditures","Renovation and Capital Projects",2223918.32,1.31,1700688`.
- **Why uncertain**: GOSA's state-total methodology (netting of inter-district transfers / exclusion of
  certain funds) is not documented in bronze, so the relationship cannot be pinned as a quality check, and
  it is unclear whether a limitations sentence is warranted or noise.
- **Location**: `limitations` kwarg in `_emit_contract_and_readme()` (prose only).
- **If confirmed, suggested fix**: add one limitations sentence: "State-level rows are GOSA's published
  state totals and do not equal the sum of district rows in all categories (netting; deviations are largest
  in debt_services and renovation_and_capital_projects)." **Recommendation: add it if Fix 1 is being applied
  anyway (zero-cost prose); not worth a re-run on its own.**

## Notes

- Contract `schema_hash`: `5fb333f25290ab469febda5d0737236e962192710fccbd0763bf8ee25fd7bfc6`; validation
  21 pass / 0 fail / 0 warning; manifest and validation fresh relative to transform.py (12:16:41 vs 12:16:32).
- v1 parity MATCH (`b464f2470ab1964eb92ecd49e989cbadfb8c9858f26db015aaa741b5521ade0e`) — both proposed
  changes are contract-prose only and would not perturb parquet bytes.
- Minor bronze-doc nit (no data impact): the 2012 file's 13 per-FTE NULLs span **three** schools — the doc
  names Northwoods Academy (Bibb) and T. Carl Buice (Gwinnett) but omits Susie Dasher Elementary School
  (Dublin City).
- The 2012 short-school-code population is larger than the doc's "minority" phrasing suggests (17,655 of
  38,973 rows) — all correctly zero-padded; gold school_code lengths are uniformly 4.
- No demographic column (correct — source has no demographic breakout); risk hypotheses 1 and 6 N/A,
  2–5 and 7 ruled out with executed evidence above.
