# Data Review: enrollment_demographic_shares

**Date**: 2026-06-11
**Reviewer**: Claude (automated data review)
**Status**: NEEDS_JUDGMENT

## Summary

Value-level review of the demographic-share side of the shared GOSA
`enrollment_by_subgroup_programs` bronze (21 files, 2004–2024) found **no
required fixes**. **v1 parity: MATCH — byte-identical with v1 gold**
(`compute_gold_sha256` vs `docs/rebuild/v1-baseline.yaml`), which also
confirms the parity-load-bearing chunk-preserving Era-A scaling kernel did
its job. All 14 extreme/ordinary/suppression traces matched bronze exactly
(including the 1.32 ED and 1.17 SWD ratios, the `.2` → 0.002 leading-dot
parse, and the 2023–24 state-level TFS on native_american/migrant); the
two-hop demographic map, both AYP maps, the drop ledger (1 junk + 1,356
dedup rows), and the 2-row 2022 reclassification all verified. Two judgment
items: a possibly-authorable male+female partition-sum quality check, and an
optional caveat for the bronze-published 2022 statewide ED dip.

## Manifest Verification

Preconditions: artifacts FRESH (transform mtime 19:34:52 < shared-module
mtime 19:45:45 < manifest 19:46:00.339 ≤ validation 19:46:00.449);
`_validation.json` `passed: true` (21 pass / 0 fail / 0 warning);
`read_loss` absent (zero events); `masked_values` absent (zero);
`reclassified` = 1 event (2022, count 2).

### Categorical map table

| Column | Entries | Bronze seen | Unmapped | Status |
| --- | --- | --- | --- | --- |
| `demographic` | 24 (two-hop: 12 wide-column→key + 12 label→key) | 12 (the 12 wide columns) | 0 | PASS |
| `met_ayp` | 2 | 2 (`Yes`, `No`) | 0 | PASS |
| `improvement_status` | 5 | 5 (`ADEQ`, `ADEQ_DNM`, `DIST`, `NI`, `NI_AYP`) | 0 | PASS |

### Full map review — `demographic` (every entry)

Column hop (mechanical, from `DEMOGRAPHIC_PCT_COLUMNS`) and label hop (the
effective `DEMOGRAPHIC_ALIASES` slice) recorded together; both verified:

| Bronze side | Gold | Correct? |
| --- | --- | --- |
| `pct_asian_pacific_islander` / "Asian/Pacific Islander" | `asian_pacific_islander` | YES — §5b topic-local remap of GOSA's bare "Asian"; see 2e below |
| `pct_black` / "Black" | `black` | YES |
| `pct_hispanic` / "Hispanic" | `hispanic` | YES |
| `pct_native_american` / "Native American" | `native_american` | YES (bronze "Native American Percentage of Enrollment" / `ENROLL_PCT_NATIVE`) |
| `pct_multiracial` / "Multiracial" | `multiracial` | YES (incl. the 2004–09 "MultiracialPercentage" header typo and 2010 `U`) |
| `pct_white` / "White" | `white` | YES |
| `pct_migrant` / "Migrant" | `migrant` | YES (2011+ only; pre-2011 NULL-metric grid rows) |
| `pct_economically_disadvantaged` / "Economically Disadvantaged" | `economically_disadvantaged` | YES |
| `pct_students_with_disabilities` / "Students With Disabilities" | `students_with_disabilities` | YES (bronze "With Disabilities …" / `SWD` / 2010 `S`) |
| `pct_english_learners` / "Limited English Proficient" | `english_learners` | YES — LEP → EL is the project-canonical nomenclature; the label hop documents the rename |
| `pct_male` / "Male" | `male` | YES (2011, 2018+ only) |
| `pct_female` / "Female" | `female` | YES |

`met_ayp`: `Yes → yes`, `No → no` — correct. Bronze also documents `N/A`
and blank (2004 categorical table in the structure doc); these never reach
the map because `N/A` is nulled at read time (`SUPPRESSION_VALUES`,
`src/utils/readers.py` line 22) and `''`/`' '`/`'.'` via
`_clean_ayp_sentinels` — verified by trace (2004 `761:102` Met AYP `'N/A'`
→ gold NULL), and the NULL semantics are documented in the contract's
`null_meaning`. Not a completeness gap.

`improvement_status`: `ADEQ → adeq`, `ADEQ_DNM → adeq_dnm`, `DIST → dist`,
`NI → ni`, `NI_AYP → ni_ayp` — codes preserved lowercase exactly as the
structure doc prescribes; `'.'` sentinel → NULL verified by trace (2008
`705:108` below).

2c contract cross-check: `gold_values_produced` for all three columns equal
the contract `enum`s exactly (12 / 2 / 5 values). 2d: `unmapped_count` = 0
for all three.

### 2e Asian/Pacific Islander (Risk 1)

- `grep -icE 'pacific[ _-]?islander|native[ _-]?hawaiian|nhpi'` on the
  structure doc → `NO_NHPI_LABEL_IN_BRONZE` (bronze publishes exactly 6 race
  buckets in all 21 years, no separate PI column anywhere).
- Math test (share variant, executed): state-row race-share sums per year
  run 0.99–1.01 in every year (e.g. 2004 = 1.01, 2005 = 1.00, 2006 = 0.99,
  2020 = 0.99, 2022 = 1.00) — integer-rounded to 1pp, so the ~0.1–0.2% NHPI
  share is below resolution: **inconclusive**, exactly as the transform
  docstring claims. The structural argument governs, and standards §5b
  explicitly lists `enrollment_by_subgroup_programs` in the known
  combined-bucket set.
- Verdict: **PASS** — bronze "Asian" correctly remapped to the combined
  `asian_pacific_islander` BEFORE `normalize_demographic_column` (the
  `DEMOGRAPHIC_SOURCE_LABELS` map), and the contract `demographic`
  description documents the §5b decision.

### 2f Mutual exclusivity (Risk 6)

`gold_values_produced` contains `asian_pacific_islander` and neither
`asian` nor `pacific_islander` — **PASS, single convention**. Sex
(`male`/`female`) and each special population are single-key axes; no
rollup/split coexistence anywhere.

### Row-count reconciliation

| Year | Bronze | Filtered (explicit) | Gold | Factor | Check |
| --- | --- | --- | --- | --- | --- |
| 2004 | 2,319 | 1,309 (1 junk wide row + 109 dup wide rows ×12) | 26,508 | 11.43 | (2,319−1−109)×12 = 26,508 ✓ |
| 2005–2008, 2010–2024 | 2,254–2,523 | 0 | bronze×12 | 12.00 | exact ×12 every year ✓ |
| 2009 | 2,418 | 48 (4 dup wide rows ×12) | 28,968 | 11.98 | (2,418−4)×12 = 28,968 ✓ |
| **Total** | **51,364** | **1,357** | **615,000** | | (51,364−1−113)×12 = 615,000 ✓ |

Actual parquet row count = **615,000** = manifest `total_gold`. All 21
expected years present; per-year bronze counts equal the structure doc's
row-count tables exactly (2,319 / 2,254 / 2,285 / 2,345 / 2,392 / 2,418 /
2,441 / 2,536 / 2,488 / … / 2,523). Drop ledger replayed against bronze:
2004 junk row `ID='2'` (no colon, all other cells NULL) confirmed — exactly
1 row; 2004 has 2,210 distinct IDs over 2,319 rows with exactly 109
duplicated IDs; 2009's 4 duplicate `SysSchoolID` groups confirmed (see 4e).
`filtered_explicit_by_reason`: 1 `malformed_identifier_junk_row` + 1,356
`duplicate_long_rows_removed_by_dedup…` = 1,357 ✓.

## Column Coverage

Versus the structure doc's Gold Schema Classification (which was written
for the combined bronze before the two-topic split; the doc's provenance
section names both derived topics):

| Bronze column | Gold disposition | Status |
| --- | --- | --- |
| `#RPT_NAME` (Era 7) | dropped (constant) | CORRECTLY EXCLUDED |
| `LONG_SCHOOL_YEAR` / filename year | `year` (Int32, ending year; cross-checked, raises on drift) | MAPPED |
| `DETAIL_LVL_DESC` / sheet name / ID pattern | drives detail-level split + geography nulling; not in gold | CORRECTLY EXCLUDED |
| `ID` / `SysSchoolID` | split into `district_code` (zfill 3) + `school_code` (zfill 4), `ALL` → NULL | MAPPED |
| `INSTN_NUMBER` / `SCHOOL_DSTRCT_CD` | `school_code` / `district_code` | MAPPED |
| `System Name` / `SCHOOL_DSTRCT_NM`, `School Name` / `INSTN_NAME`, `Grades` / `GRADES_SERVED_DESC` | dimension attributes, dropped | CORRECTLY EXCLUDED |
| `Met AYP` / `ayp_status` | `met_ayp` | MAPPED (deviation: doc proposed an `n_a` value; transform NULLs `N/A` — defensible, matches the `'.'` handling, documented in `null_meaning`) |
| `Improvement Status` / `ni_status` | `improvement_status` | MAPPED |
| 12 demographic % columns (all era spellings, incl. 2010's `A/B/H/N/U/W/L/ED/S` and Era C's `ENROLL_PCT_*`) | unpivoted to `demographic` + `pct_of_enrollment` (÷100) | MAPPED (deviation from the doc's proposed wide `pct_asian`-style layout: tidy long per standards §9, and `asian` → `asian_pacific_islander` per §5b — both deviations are standards-mandated improvements over the doc's sketch) |
| 9 program (count, pct) pairs (2011+) | sibling topic `enrollment_program_participation` | CORRECTLY EXCLUDED here |

Every gold column traces to bronze (no fabrication): `year`,
`district_code`, `school_code`, `demographic` (from column identity),
`met_ayp`, `improvement_status`, `pct_of_enrollment`. Era rename maps read
clean: `_ERA_A_RENAME_2004_2009` carries the "MultiracialPercentage" typo
verbatim; `_ERA_A_RENAME_2010` matches the doc's 15-column crosswalk
letter-for-letter; `_ERA_BC_RENAME` lists both PERCENT/PCT spellings
literally (no mechanical substitution, EIP quirk isolated to the sibling's
columns) with leftover-`ENROLL_*` and required-demographic-set guards that
raise.

## Value-Level Spot Checks

Extreme rows first. Every verdict quotes the bronze cell it rests on.

| # | Trace | Bronze (quoted) | Expected | Gold | Verdict |
| --- | --- | --- | --- | --- | --- |
| 1 | Global max — 2008 `705:108` Mountain Creek Academy (Murray Co; now "Pleasant Valley Innovative School" in the dim), ED | `'132'`, Met AYP `'No'`, Improvement `'.'` | 1.32, `no`, NULL | 1.32, `no`, NULL | MATCH |
| 2 | SWD max — 2004 `611:179` Butler Early Childhood Center (Bibb Co) | SWD `'117'`, Met AYP `'No'`, `'ADEQ_DNM'` | 1.17, `no`, `adeq_dnm` | 1.17, `no`, `adeq_dnm` | MATCH |
| 3 | 2004 max — `721:301` Jenkins-White Elementary (Richmond Co), ED | `'121'`, Met AYP `'Yes'`, `'NI_AYP'` | 1.21 at `721`/`0301`, `yes`, `ni_ayp` | 1.21, `yes`, `ni_ayp` | MATCH |
| 4 | Global min / leading-dot — 2023 `647:0103` Robert A. Cross Middle Magnet, SWD | `'.2'` | 0.002 | 0.002 | MATCH (Era-C leading-dot decimal parses correctly) |
| 5 | State-level TFS — 2023 & 2024 State rows | `ENROLL_PCT_NATIVE='TFS'`, `ENROLL_PCT_MIGRANT='TFS'` (both years) | NULL native_american + migrant at state level | NULL both, both years | MATCH (explains the 5-of-6 non-null state race buckets in 2023–24) |
| 6 | Ordinary, era_a_2004_2006 — 2004 `601:1050` Altamaha Elementary | Asian 0, Black 5, Hisp 3, Native 0, Multi 1, White 91, LEP 1, ED 41, SWD 18; `'Yes'`/`'ADEQ'` | ÷100; migrant/male/female NULL grid rows | all 9 shares + `yes`/`adeq` + 3 NULL grid rows | MATCH (12/12 rows) |
| 7 | Ordinary + dedup, era_a_2007_2009 — 2009 `768:ALL` Ivy Prep (district) | 15/57/11/1/9/8, LEP 11, ED 36, SWD 7; `'Yes'`/`'ADEQ'` | one gold district row-set | exactly 12 rows, all values match | MATCH |
| 8 | Ordinary, era_a_2010 — 2010 `601:103` Appling County High | A 1, B 24, H 8, N 0, U 2, W 65, L 1, ED 57, S 15; ayp `'No'`, ni `'ADEQ_DNM'` | school_code zfill → `0103` | all match, `no`/`adeq_dnm` | MATCH |
| 9 | Ordinary, era_b — 2015 `601:0103` | ASIAN 1, NATIVE 0, BLACK 22, HISP 11, MULTI 2, WHITE 64, MIGRANT 4, ED 59, SWD `12.7`, LEP 2 | ÷100 incl. 0.127; male/female NULL (2012–17 gap) | all match | MATCH |
| 10 | Ordinary, era_c — 2023 `647:0103` | ASIAN 2, NATIVE `TFS`, BLACK 89, HISP 4, MULTI 1, WHITE 4, MIGRANT `TFS`, ED 100, SWD `.2`, LEP 2, MALE 40, FEMALE 60 | TFS→NULL, ED→1.0, sex populated | all 12 match | MATCH |
| 11 | Era-C state row — 2024 State | ASIAN 5, BLACK 36, HISP 19, MULTI 5, WHITE 35, ED 64, SWD `13.3`, LEP 12, MALE 51, FEMALE 49, NATIVE/MIGRANT `TFS` | NULL geography keys, ÷100 | all match (0.133 SWD etc.) | MATCH |
| 12 | met_ayp `N/A` sentinel — 2004 `761:102` and `644:199` | Met AYP `'N/A'`, Improvement `'ADEQ'` | NULL met_ayp, `adeq` | NULL, `adeq` (both) | MATCH |
| 13 | 2011 LEP suppression — state row | `ENROLL_PERCENT_LEP='6'`, `MIGRANT='0'`, `MALE='51'`, `FEMALE='49'` | 0.06 / 0.0 / 0.51 / 0.49 | all match; school-level EL null rate 2,034/2,536 = 80.2% (doc: 2,033 school + 1 district) | MATCH |
| 14 | 2022 reclassification — `7830627`/`7830636` | `DETAIL_LVL_DESC='School'` + `INSTN_NUMBER='ALL'`, no District row (per structure doc, verified count=2 in manifest) | district-level rows (school_code NULL) | each charter has 12 school rows (`0627`/`0636`) + 12 district rows (NULL school_code) | MATCH |

- **4c sentinel year-attribution**: every Era B/C file's
  `LONG_SCHOOL_YEAR` is parsed to its ending year and the transform
  **raises** on filename drift (`_transform_era_bc`); trace #10/11 confirm
  `2022-23` → 2023, `2023-24` → 2024. Era A has no embedded year. PASS.
- **4d aggregate feasibility screen** (aggregates COME FROM BRONZE; no
  derivation): district share must lie within [min, max] of its school
  shares ±0.015 → 36 violations out of 42,864 joined cells (0.084%).
  29 are 2011 `english_learners` — the visible (non-suppressed) school rows
  are all 0.0 while the district published a real share (e.g. `781`
  district 0.17 vs 3 visible schools at 0.0): an artifact of the 2011
  school-level LEP suppression, not garbling. 5 are district `891`
  (Dept. of Juvenile Justice, a `state_agency` pseudo-district whose
  students sit partly in non-school facilities) SWD shares above the school
  max. Remaining 2 are ≤0.04 excess. No column-swap signature anywhere.
  PASS.
- **4e dedup tie-break**: one file per year — no era-overlap years (N/A for
  the classic inversion). In-file duplicates: 2009 `796:105` and `796:ALL`
  byte-identical pairs; `768:ALL` / `770:ALL` pairs differ ONLY in
  School Name/Grades (one row carries the name, the other the grades — both
  quoted above), with all 9 shares + both AYP values identical.
  `assert_no_natural_key_collisions` (metrics + both AYP categoricals) ran
  before dedup, so the winner is provably immaterial; `sort_col=
  "pct_of_enrollment"` documented as safety net. PASS.
- **4f suppression semantics**: TFS→NULL (traces 5, 10, 11), `'.'`→NULL
  (trace 1), `'N/A'`→NULL (trace 12), blank→NULL (strict casts). PASS.

## Validation Cross-Read

- `_validation.json`: 21 pass / 0 fail / 0 warning, `passed: true`,
  timestamp 2026-06-11T19:46:00Z. `contract_parquet_schema` (61/61 files),
  `contract_quality_sql` (9/9), `grain_uniqueness`, and `foreign_keys`
  (252 district keys, 2,913 school keys, 12 demographics — all resolve)
  all pass. I additionally verified zero duplicates on the *tighter*
  natural key (year, district_code, school_code, demographic) — the
  contract grain auto-includes the two AYP categoricals, which is weaker;
  both hold.
- **schema_hash**:
  `3f46dac823df881689ce386110481107ce96ffbe0e36ab759c3b7f8429fa810c`.
- **§4b masking audit**: the transform declares "No §4b masks" — confirmed:
  no `_null_*` metric-mask helper exists in `transform.py`; the shared
  module's `_null_if_all` is geography-sentinel nulling (domain rule §6),
  not a value mask; manifest has no `masked_values` section (zero events);
  the >1.0 ratios are preserved-and-documented per §4b
  extreme-but-conceivable, with the contract's `pct_of_enrollment`
  description carrying the full rationale and the verified maxima.
- **§15b coverage**: 4 authored checks — `pct_of_enrollment_sane_upper_bound`
  (≤1.5 unscaled-regression guard; correct given `unit: ratio` only derives
  ≥0), `ayp_columns_null_post_2010`, `era_gap_demographics_null`,
  `twelve_demographic_rows_per_entity` (correctly written as one
  GROUP BY scan, no self-join) — plus 5 auto-derived. The 12-row grid,
  the era gaps, and the AYP retirement are all pinned. The documented
  opt-out of race/sex partition-sum checks: the **race** opt-out is
  *provably correct* — bronze publishes real all-zero race rows (2005–07
  `667:299` T. Carl Buice School, a PK-only school, quoted: all six race
  cells `'0'`; 18 such entity-years with race-sum 0.0), so any mustBe-0
  sum-to-one check would fail on genuine bronze. The **sex** opt-out is
  weaker — see Judgment Call 1.
- **v1 parity (verbatim)**: `MATCH — byte-identical with v1 gold`.
  The parity-load-bearing comment exists in
  `_enrollment_subgroup_programs_shared.py` (Era-A scaling loop): "One
  single-expression with_columns per column, applied BEFORE any
  multi-expression with_columns: polars preserves the per-sheet chunk
  layout … A multi-expression call rechunks the frame first, and the SIMD
  kernel multiplies by the reciprocal instead, flipping e.g. 47/100 by
  1 ulp (0x1.e147ae147ae15p-2 vs ...14p-2)". The rationale (scalar
  true-division vs rechunked SIMD reciprocal-multiply kernels) is
  plausible polars behavior, and the byte-identical hash is the proof it
  reproduces v1's floats.

## Cross-Era Consistency

- **Era boundaries**: state-level per-demographic series are smooth across
  both boundaries (2010→2011 and 2022→2023): e.g. white 0.51 (2004) → 0.44
  (2011/2012) → 0.35 (2024); hispanic 0.07 → 0.12 → 0.19; SWD 0.12 → 0.103
  → 0.133. No 10x jumps anywhere; no scale break (all eras ÷100 once, in
  the shared module).
- **Cross-year NULL sweep (Risk 2)**: ≥95%-NULL cells are exactly the
  documented era gaps — male/female in 2004–2010 + 2012–2017, migrant in
  2004–2010 — and nothing else. Partial-NULL cells: 2011 english_learners
  (80.2%, the documented pre-CCRPI school-level suppression) and 2023–24
  native_american/migrant (86–89%, the documented Era-7 TFS expansion;
  bronze TFS counts 2,235/2,183 in 2023 match the structure doc). No
  unexplained era-localized NULL column → rename-typo hypothesis ruled out.
- **AYP columns**: 0–2.6% NULL in 2004–2010 (sentinels), 100% NULL from
  2011 — pinned by quality check.
- **Known bronze anomalies preserved faithfully**: the 2022 statewide ED
  share dips to 0.45 (bronze `ENROLL_PERCENT_ED='45'` quoted from the 2022
  State row; 2021='56', 2023='59') — see Judgment Call 2. Migrant state
  share prints 0.0 in 2011–2022 (bronze `'0'` — integer rounding of a
  <0.5% population), then TFS-NULL in 2023–24.

## Transform Logic Risks

| Risk | Severity | Verdict / details |
| --- | --- | --- |
| Silent column drops | none | PASS — only name/grades dimension attrs + constant `#RPT_NAME` dropped; rename-coverage guards raise on any leftover `ENROLL_*` or missing Era-A/required-demo column |
| Era routing | none | PASS — `detect_era_by_columns` with 5 most-specific-first signatures; unmatched raises; manifest `files_processed` routes all 21 files to the expected eras |
| Filter logic logged + justified | none | PASS — junk row logged + `record_filtered`; per-year dedup removals recorded; 2022 reclassification via `record_reclassified` |
| Normalization map completeness | none | PASS — both PERCENT/PCT spellings literal; EIP-K-5 rename trap documented and irrelevant to this topic's columns; 2010 single-letter crosswalk matches the doc |
| `strict=False` casts | none | PASS — used only after read-time TFS/N-A nulling, on `infer_schema_length=0` string reads; leading-dot decimals verified parsing correctly (trace 4) |
| Dedup keys + tie-break | none | PASS — collision guard on metrics **and** both AYP categoricals before dedup; explicit `sort_col`; duplicates proven identical (Step 4e) |
| Year extraction | none | PASS — strict filename parse (raises); Era B/C LONG_SCHOOL_YEAR cross-check (raises on drift) |
| §4b/§5b masking (Step 5b) | none | PASS — zero masks, none needed; >1.0 ratios preserved + documented + guarded at ≤1.5 |

## NEEDS_JUDGMENT

### Judgment Call 1: male+female partition-sum quality check is authorable
- **Severity if confirmed**: MEDIUM
- **Suspicion**: The transform docstring opts out of BOTH race and sex
  partition-sum checks on the grounds that "no tolerance is provable from
  bronze without also masking real data errors." For race that is proven
  correct (real all-zero race rows, e.g. 2005–07 `667:299`). For the sex
  pair the claim looks too conservative: a NULL-guarded
  `male_female_shares_sum_to_one` check (both non-null, |sum − 1| ≤ 0.03)
  passes on 100% of current gold.
- **Evidence available**: executed sweep — 19,921 (year, entity) pairs with
  both sex shares non-null; 0 pairs outside [0.97, 1.03]; state-level
  male+female sums are exactly 1.0 in all 8 published years. 1pp integer
  rounding bounds the pair sum to ~1±0.02 when the true values sum to 1.
- **Why uncertain**: the opt-out is a deliberate, documented §15b decision,
  and a future GOSA file could legitimately break the ±0.03 envelope
  (decimal-precision changes, partial suppression of one sex but not the
  other would be caught by the NULL guard, but a publication quirk like the
  all-zero race rows could recur on the sex pair). Reasonable reviewers can
  accept the documented opt-out as-is.
- **Location**: `quality_checks=` in `_emit_contract_and_readme()`
  (`src/etl/education/gosa/enrollment_demographic_shares/transform.py`);
  docstring "No race/sex partition-sum quality check" bullet.
- **If confirmed, suggested fix**: author a NULL-guarded pivoted check
  (one GROUP BY scan per §15b, no self-join): both sex shares non-null ⇒
  `ABS(male + female − 1.0) <= 0.03`, `mustBe: 0`; update the docstring
  bullet to scope the opt-out to race only. Note this re-emits the contract
  (quality-check count 9 → 10) but cannot change gold bytes — v1 parity is
  unaffected.

### Judgment Call 2: 2022 statewide ED dip deserves a one-line caveat
- **Severity if confirmed**: LOW
- **Suspicion**: the state economically_disadvantaged share drops from 0.56
  (2021) to 0.45 (2022) and reverts to 0.59 (2023) — a one-year level shift
  that propagates through district/school rows (2022 gold mean 0.229 vs
  0.238/0.298 neighbors). Analysts trending ED will hit it.
- **Evidence available**: bronze-confirmed — 2022 State row
  `ENROLL_PERCENT_ED='45'`, 2021 `'56'`, 2023 `'59'` (quoted). The
  transform is a faithful passthrough; nothing to fix in code. The dip
  coincides with pandemic-era direct-certification/P-EBT changes to ED
  identification, but that cause is not provable from bronze.
- **Why uncertain**: it is real published GOSA data, already served
  correctly; whether it merits contract/README prose (vs. being ordinary
  source-data history that documentation should not editorialize) is a
  policy call.
- **Location**: `notes=[...]` and/or the `pct_of_enrollment` description in
  `_emit_contract_and_readme()`.
- **If confirmed, suggested fix**: add one sentence to the topic notes:
  "The 2022 statewide economically_disadvantaged share (0.45) is a
  bronze-published one-year dip (0.56 in 2021, 0.59 in 2023), likely from
  pandemic-era changes to ED identification; values are GOSA's as
  published." Doc-only; no gold change.

## Notes

- schema_hash
  `3f46dac823df881689ce386110481107ce96ffbe0e36ab759c3b7f8429fa810c`;
  validation 21 pass / 0 fail / 0 warning; 61 parquet files (21 years × 3
  detail levels − 2: no states.parquet in 2009/2010, matching the bronze's
  missing state rows — correctly not synthesized).
- v1 parity MATCH means every numeric, dedup, and convention decision is
  byte-identical with the approved v1 gold; both judgment items are
  contract/doc-layer only and would not perturb parity of the fact data.
- The contract grain auto-includes `met_ayp`/`improvement_status`
  (emitter derives the key from all categoricals). Harmless — uniqueness
  also holds on the true (year, geography, demographic) key (verified,
  0 duplicate groups) — but consumers should treat the AYP columns as
  denormalized attributes, not key parts; the contract's
  `dataGranularityDescription` makes this readable.
- Bronze quirks verified and handled: 2006 XLS-with-.csv-extension read by
  magic bytes; 2007 lowercase "School level" sheet; 2005–2008 three-sheet
  workbooks read sheet-by-sheet (default first-sheet reads would have
  dropped district+state rows — manifest per-year counts prove all sheets
  landed); 2010 single `Sheet3`.
- All-zero race rows (18 entity-years, Era A, e.g. T. Carl Buice PK school)
  are bronze-published zeros, preserved per `zero_is_real` — they are why a
  race partition-sum quality check is correctly absent.
