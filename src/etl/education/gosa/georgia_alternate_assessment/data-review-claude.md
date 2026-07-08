# Data Review: georgia_alternate_assessment_gaa

**Date**: 2026-06-11
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Gold data is accurate: **v1 parity MATCH (byte-identical)**, all 16 value-level
traces (extremes, one ordinary entity per era, suppression, Homeless ~0.5-sum,
2004 dropped twin) reproduce bronze exactly, the 138 2004 drops replay
precisely (1 + 136 + 1), the Era 3 `THUROUGH_*` drop is verified per file, and
the aggregate feasibility screen is perfectly consistent (district and school
sums equal the state total to the row, 0 impossibly-low districts in 29,194
cells). One LOW documentation fix: the Homeless percentage-sum-~50% source
quirk is scoped in the contract notes to "a few 2022–2023 district/state rows,"
but 2024 is affected wholesale — all 1,135 Homeless rows, including 831
school-level rows. No gold-value change is needed.

## Manifest Verification

| Column | Map entries | Bronze values seen | Unmapped | Status |
| --- | --- | --- | --- | --- |
| `demographic` | 22 | 22 (= structure-doc union across Eras 3–6) | 0 | PASS |
| `subject` | 4 | 4 | 0 | PASS |

**`demographic` — all 22 entries reviewed semantically (2b), all correct:**

| Bronze | Gold | Correct? |
| --- | --- | --- |
| All Students | `all` | Yes |
| American Indian or Alaskan Native | `native_american` | Yes |
| Asian | `asian` | Yes — split convention proven (see 2e below) |
| Black or African American | `black` | Yes |
| Economically Disadvantaged | `economically_disadvantaged` | Yes |
| Not Economically Disadvantaged | `not_economically_disadvantaged` | Yes |
| Female / Male | `female` / `male` | Yes |
| Foster Care | `foster_care` | Yes |
| Hispanic | `hispanic` | Yes |
| Homeless | `homeless` | Yes |
| Limited English Proficient | `english_learners` | Yes — LEP is the legacy federal term for EL |
| Not Limited English Proficient | `not_english_learners` | Yes — canonical `not_` prefix |
| Migrant / Non-Migrant | `migrant` / `not_migrant` | Yes |
| Military Connected | `military_connected` | Yes — distinct from `active_duty` (nested, non-additive; documented) |
| Active Duty | `active_duty` | Yes — subset key; verified `active_duty ≤ military_connected` num_tested in all 37 comparable cells (0 violations) |
| Native Hawaiian or Other Pacific Islander | `pacific_islander` | Yes |
| Students with/without Disabilities | `students_with_disabilities` / `students_without_disabilities` | Yes |
| Two or More Races | `multiracial` | Yes |
| White | `white` | Yes |

**`subject` — all 4 entries correct:** English Language Arts →
`english_language_arts`, Mathematics → `mathematics`, Science → `science`,
Social Studies → `social_studies`. Routing `TEST_CMPNT_TYP_NM` to `subject`
(not `test_component`) is correct per §16 — these are academic content areas.
The structure doc's original `test_component` recommendation predates the
canonical-vocabulary decision; its addendum acknowledges the override.

- **2a Completeness**: every `SUBGROUP_NAME` documented in the structure doc
  (16 in Era 3, +NHPI in Era 4, +Active Duty/Foster Care/Homeless/Military
  Connected in Era 5, +Students without Disabilities in Era 6 = 22) appears in
  `bronze_values_seen`. No documented value missing. Eras 1–2 have no
  categorical bronze columns — the literal `demographic = "all"` is correct
  (full-population rows) and needs no recording.
- **2c Contract cross-check**: `gold_values_produced` for both columns equals
  the contract `enum` exactly (22 and 4 values).
- **2d Unmapped**: 0 for both.

### 2e Asian / Pacific Islander (Risk 1) — PASS, split convention

Bronze publishes an explicit separate `"Native Hawaiian or Other Pacific
Islander"` row (5 mentions in the structure doc; e.g., 3 rows in 2023, 64 in
2024), so bare `"Asian"` is genuinely Asian-only. Math-test output:

```
num_tested: year=2023 total=34552 race_sum=34534 ratio=0.9995
num_tested: year=2019 total=35361 race_sum=35347 ratio=0.9996
```

With 7 split race buckets present (`asian`, `pacific_islander`, `black`,
`hispanic`, `multiracial`, `native_american`, `white`), race_sum ≈ total is the
expected complete-partition result — NOT conflation. If "Asian" were the
combined bucket while separate PI rows also existed, the race sum would
*exceed* the total. §5b's known-list also names this topic split-convention.

### 2f Mutual exclusivity (Risk 6) — PASS, single convention

`asian_pacific_islander` rows in gold: **0**. Gold carries only the split pair,
matching bronze. The nested military keys are in `special_population` (a
multi-axis category by design); their non-additivity is documented in the
contract `demographic` description and verified numerically above.

### Row-count reconciliation (3a/3b)

| Year | Bronze | Gold | Filtered | Notes |
| --- | --- | --- | --- | --- |
| 2004 | 2,358 | 2,220 | 138 | 1 all-null trailing + 136 exact duplicates + 1 placeholder twin — replayed exactly (below) |
| 2005–2023 (14 files) | 1:1 | 1:1 | 0 | expansion factor 1.0 every year |
| 2024 | 63,689 | 63,689 | 0 | suppressed rows now emitted by source (~4x row jump, documented) |
| **Total** | **248,479** | **248,341** | **138** | parquet row count = 248,341 = manifest `total_gold` ✓ |

**2004 repair replay (executed against bronze):** 1 row with null
`SysSchoolID` (all four columns null); 272 rows flagged `is_duplicated()` =
136 exact-duplicate pairs, district prefixes exactly `['644','645','646','647']`;
`647:3058` appears twice — `"Northside Elementary School" / 406 / 10` and
`"Northside Elementary" / null / null` — gold keeps exactly one row with
`enrollment_ayp_grades=406, num_tested=10`. 2005 has 0 duplicate ids.
138 = 1 + 136 + 1 matches `filtered_explicit_by_reason` exactly.

## Column Coverage

| Bronze column (era) | Gold column | Status |
| --- | --- | --- |
| `SysSchoolID` / `sysschoolid` (E1–2) | `district_code`, `school_code`, detail level (split on `:`, `ALL`→NULL) | MAPPED |
| `School Name` / `schoolname` (E1–2) | — (dimension attribute) | CORRECTLY EXCLUDED |
| `Enrollment in Grades…` / `Enroll` (E1–2) | `enrollment_ayp_grades` | MAPPED |
| `Number of Students Taking the GAA` / `Number` (E1–2) | `num_tested` | MAPPED |
| `LONG_SCHOOL_YEAR` (E3–6) | — (year from filename; asserted equal per file) | CORRECTLY EXCLUDED |
| `SCHOOL_DISTRCT_CD` (E3–6) | `district_code` | MAPPED |
| `SCHOOL_DSTRCT_NM` / `INSTN_NAME` (E3–6) | — (dimension attributes) | CORRECTLY EXCLUDED |
| `INSTN_NUMBER` (E3–6) | `school_code` (zfill(4); fixes 2019 unpadded) | MAPPED |
| `SUBGROUP_NAME` (E3–6) | `demographic` | MAPPED |
| `TEST_CMPNT_TYP_NM` (E3–6) | `subject` | MAPPED |
| `NUM_TESTED_CNT` (E3–6) | `num_tested` | MAPPED |
| Level counts/pcts (E3: LIMITED/PARTIAL/ADEQUATE; E4: Level1–4; E5: +THOROUGH; E6: BEGIN/DEVELOPING/PROFICIENT/DISTINGUISHED) | `num_/pct_{beginning,developing,proficient,distinguished}_learner` | MAPPED (era maps reviewed entry-by-entry; tier order correct in all four eras) |
| `THUROUGH_CNT` / `THUROUGH_PERCENT` (E3) | — | CORRECTLY EXCLUDED — **verified per file**: distinct non-null values are `['0']` and `[]` respectively in all 8 files 2011–2018 |
| `#ASSMT_CD`, `ACDMC_LVL` (E6) | — (constants `GAA` / `ALL GRADES`, asserted before drop) | CORRECTLY EXCLUDED |
| *(derived)* | `pct_developing_learner_or_above`, `pct_proficient_learner_or_above` | Derived, era-aware — verified below |

No gold column lacks a bronze (or documented derived) origin.

## Value-Level Spot Checks

All MATCH. Bronze values quoted from executed reads.

**Extreme rows (4a):**

| Trace | Bronze | Gold | Verdict |
| --- | --- | --- | --- |
| `enrollment_ayp_grades` global max | 2007 `ALL:ALL` "State of Georgia" `Enroll=1238970` | 2007 state row 1238970 | MATCH |
| `num_tested` global max | 2023 state ELA `NUM_TESTED_CNT=12765` | 12765 | MATCH |
| `num_beginning_learner` global max | 2014 state ELA `LIMITED_CNT=2066` | 2066 | MATCH |
| `num_developing_learner` global max | 2018 state Math `PARTIAL_CNT=6533` | 6533 | MATCH |
| `num_proficient_learner` global max | 2024 state Math `PROFICIENT_CNT=5927` | 5927 | MATCH |
| `num_distinguished_learner` global max | 2023 state ELA `THOROUGH_CNT=3349` | 3349 | MATCH |
| `enrollment_ayp_grades` global min | 2005 `729:205` "Americus Sumter County High North" `Enrollment=1.0`, `Number=0` | 1 / 0 | MATCH (extreme-but-conceivable: AYP grades at a high school ≈ grade 11 only) |
| 2024 count mins = 10 everywhere | bronze min 10 on every `*_CNT` (suppression threshold <10) | gold min 10 | MATCH |

**Ordinary traces, one per era (4b):**

| Era | Entity | Bronze | Gold | Verdict |
| --- | --- | --- | --- | --- |
| 1 (2004) | 644:3058 Heritage Educational Center | `44 / 51` (also the preserved num_tested>enrollment quirk; 2005: `50 / 52`) | 44/51 and 50/52 | MATCH |
| 2 (2007) | 733:105 Taylor County Upper Elementary | `530 / 6` | 0105 (padded), 530/6, demographic=`all`, subject NULL | MATCH |
| 3 (2015) | 644:0897, Not LEP, ELA | `11; 0/4/7; 0/36.4/63.6` | 11; 0/4/7; 0/.364/.636; distinguished NULL; dev_or_above=1.0; prof_or_above=.636 | MATCH |
| 4 (2019) | 792:**273** (unpadded), Male, Math | `10; 0/3/6/1; 0/30/60/10` | school_code `0273`; 0/.3/.6/.1; dev_or_above≈1.0; prof_or_above=.7 | MATCH (zfill repair confirmed) |
| 5 (2023) | 645:0180, Econ. Disadv., ELA | `21; 2/0/8/11; 9.5/0/38.1/52.4` | .095/0/.381/.524; dev_or_above=.905; prof_or_above=.905 | MATCH |
| 6 (2024) | 645:0293, Non-Migrant, Science | raw CSV `TFS` counts; `0/33.3/66.7/0` pcts | all counts NULL; pcts 0/.333/.667/0; dev_or_above=1.0 | MATCH (percent-only row preserved) |

**Era-aware `_or_above` (3-tier vs 4-tier):** 2014 state ELA (3-tier) bronze
`19.8/50.7/29.5` → gold dev_or_above = .507+.295 = **.802** and prof_or_above
= **.295** (absent tier omitted, not NULL-propagated); 2023 state ELA (4-tier)
`24.5/46.3/26.2` → dev_or_above **.97**, prof_or_above **.725**. Both MATCH.

**Sentinel year-attribution (4c):** 2022 file `LONG_SCHOOL_YEAR='2021-22'` →
`parse_school_year` = 2022 = filename year; the transform *asserts* this
equality per Era 3–6 file (`_assert_school_year_matches`). PASS.

**Aggregate reconciliation / feasibility screen (4d)** — aggregates come from
bronze, so the feasibility screen applies: for `demographic='all'`,
district sums and school sums equal the state total **exactly** (ratio 1.000)
in 2011, 2015, 2019, 2023; impossibly-low check across all years ≤2023:
**0 of 29,194** district cells have `num_tested` below the max (or visible
sum) of their school rows. PASS.

**Dedup tie-break (4e):** N/A — one bronze file per year, no overlap years;
dedup is a documented safety net (`sort_col="num_tested"`), and the collision
guard runs first.

**Suppression semantics (4f):**

| Marker | Bronze | Gold | Verdict |
| --- | --- | --- | --- |
| Null-cell (E3) | 2015 732:0201 All Students ELA: `NUM_TESTED_CNT='3'`, all level cells null | num_tested=3, all level metrics + cumulatives NULL | MATCH |
| `TFS` (E5) | 2023 735:1051 All Students Math raw CSV: `'7','TFS','TFS','TFS','TFS','TFS',…` | num_tested=7, all level metrics + cumulatives NULL | MATCH |
| `TFS` on num_tested (E6) | 2024 645:0293: counts `TFS`, pcts published | counts NULL, pcts populated | MATCH |

**Homeless ~0.5-sum rows:** 2023 bronze district 618 Homeless ELA:
`NUM_TESTED_CNT='14', counts 0/0/3/4, pcts 0/0/21.4/28.6` (sum 50.0) → gold
`.0/.0/.214/.286`, psum 0.5 — preserved as published. Gold rows with all four
shares non-null summing <0.9: 2022=**50**, 2023=**77** (all `homeless`,
matching the documented counts) — plus 2024=**1,135** (see Required Fix 1).

## Validation Cross-Read

- `_validation.json`: **20 pass / 0 fail / 1 warning**; `passed: true`;
  timestamp fresh vs manifest. `contract_parquet_schema` (48 files),
  `contract_quality_sql` (all 29), `grain_uniqueness`
  (year, district_code, school_code, demographic, subject), and
  `foreign_keys` (217 districts, 2,691 schools, 22 demographics) all pass.
- The single warning (36 null-rate spikes) is fully explained by era
  structure: 2004–2007 participation-only (achievement metrics 100% NULL),
  2011–2018 3-tier (distinguished 100% NULL), 2024 suppression-policy change
  (num_tested 84.5% NULL, counts ~95–99.6% NULL). All documented in the
  contract column descriptions and asserted by authored quality checks.
- **schema_hash**: `7de73c05cdcc8a440c9ace026d54dec538a2c962e211f9425a616a7bc3205c9e`
- **§4b masking audit (5b)**: no `_null_*` metric mask exists and none is
  needed — manifest has no `masked_values` section (correct: absent = zero
  events). `_null_if_all` nulls the geography `ALL` *sentinel* (§6 detail-level
  handling, validator-checked by `geography_nulling`), not a metric mask, so
  `record_masked` does not apply. Verified claim "no impossible values":
  all gold proportions ≤ 1.0 (unit-interval checks pass), counts ≥ 0.
- **§15b coverage (5c)**: strong. 15 derived + 14 authored = 29 checks. The
  authored set covers all four required shapes: partition-sums (scoped
  2011–2019 with a 2022+ upper bound — correctly scoped given the Homeless
  quirk), co-null (scoped 2011–2019; 2022+ provably breaks it at source),
  component reconciliation (level counts ≤/= num_tested, era-scoped), and
  structural era facts (participation-era shape, era-3 distinguished absent,
  2024 pcts always published, num_tested never suppressed 2011–2023).
- **v1 parity (5d)**, verbatim:

```
MATCH — byte-identical with v1 gold
```

## Cross-Era Consistency

- **No overlap years** — 16 files, one per year; dedup tie-break N/A.
- **Era-boundary continuity (3d)**: state-level `all` num_tested totals are
  smooth within regimes (2004–2007: 8,982→9,861; 2011–2024: 33,560–43,349).
  The Era 2→3 jump (9,861→34,631) is the measure-regime change (one
  participation row vs per-subject sums ×4 subjects) — expected. The
  2016→2017 dip (43,349→33,560, ~1.29x) is present in bronze (2016 file has
  18,477 rows vs 2017's 14,617) — source-driven, below the 1.5x flag
  threshold. No 10x scale jumps anywhere.
- **Cross-year NULL sweep (3c)**: every flag maps to a documented era fact —
  `subject`/achievement metrics NULL 2004–2007; `enrollment_ayp_grades` NULL
  2011+; distinguished pair NULL 2011–2018; counts ~95–99.6% NULL 2024. No
  era-localized rename-bug signature (no unexplained NULL year inside an era).
- **State-row counts** match the corrected structure doc exactly: 64 standard,
  2012=65, 2016=68, 2022=79, 2023=81, 2024=86 — the transform-agent's
  structure-doc corrections check out.

## Transform Logic Risks

| Risk | Severity | Verdict / details |
| --- | --- | --- |
| Silent column drops | — | PASS — THUROUGH drop verified 0/null per file; E6 constants asserted before drop; name columns dimension-routed |
| Era routing correctness | — | PASS — signatures mutually exclusive (`THUROUGH` vs `THOROUGH` vs `Level1` vs `BEGIN`; `SysSchoolID` vs `sysschoolid` casing); `detect_era_by_columns` = first era with all signature columns present |
| Filter logic logged + justified | — | PASS — 138 drops logged + manifest-recorded with three distinct reasons; replayed exactly |
| Normalization map completeness | — | PASS — 22/22 demographics, 4/4 subjects vs structure doc |
| `strict=False` casts | — | PASS — all-Utf8 read (`infer_schema_length=0`); TFS pre-nulled by shared reader (raw-CSV trace confirms); casts null residue only |
| Dedup keys + tie-break | — | PASS — explicit `sort_col="num_tested"`, documented as safety net; `assert_no_natural_key_collisions` runs first on full natural key incl. `detail_level` |
| Year extraction | — | PASS — filename year, asserted equal to `LONG_SCHOOL_YEAR` per Era 3–6 file; traced 2022 |
| §4b masking (5b) | — | PASS — no metric mask needed; none silently applied |

## Required Fixes

### Fix 1: Homeless percentage-sum quirk documentation omits 2024 (affected wholesale, including school level)
- **Severity**: LOW
- **Issue**: The contract note, README note, and transform docstring scope the
  Homeless shares-sum-to-~50% source quirk to "a few **2022-2023**
  district/state 'Homeless' rows" (50+77 rows). In 2024 the same quirk affects
  **every Homeless row — 1,135 rows (4 state, 300 district, 831 school)** —
  with share sums tightly clustered at 0.499–0.501. Gold values are correct
  (preserved as published, and the 2022+ quality check only asserts the upper
  bound, so validation is unaffected), but the prose tells analysts 2024 is
  clean and the quirk never reaches school level.
- **Evidence**: Bronze 2024 (executed): `Homeless rows with pct sum < 90: 1135
  of 1135; state 4 | district 300 | school 831`; sample row `605:0189 ELA:
  NUM_TESTED_CNT=TFS, BEGIN/DEVELOPING/PROFICIENT/DISTINGUISHED_PCT =
  0/0/50.0/0` → gold psum 0.5. Gold low-sum (<0.9) rows by year: 2022=50,
  2023=77, 2024=1,135 — all `demographic='homeless'`. Contract note (emitted
  from transform.py `notes=[...]`): "A few 2022-2023 district/state 'Homeless'
  rows publish level percentages that sum to ~50%…".
- **Location**: `_emit_contract_and_readme()` `notes` list (4th item) and the
  module docstring "Known source quirks preserved" bullet in
  `src/etl/education/gosa/georgia_alternate_assessment_gaa/transform.py`.
- **Suggested fix**: Extend the note/docstring to state that in 2024 the quirk
  is systematic — all 1,135 Homeless rows at every detail level publish four
  shares summing to ~0.5 — and keep "preserved as published". Re-run the
  transform to re-emit the contract/README. Prose-only change: parquet bytes
  are untouched, so v1 parity is preserved.

## Notes

- schema_hash `7de73c05cdcc8a440c9ace026d54dec538a2c962e211f9425a616a7bc3205c9e`;
  validation 20 pass / 0 fail / 1 explained warning; read_loss events: 0.
- v1 parity: MATCH (byte-identical). The Required Fix above changes only
  contract/README prose, not gold parquet.
- The `_cap_or_above` snap is real and bounded: 8,751 gold rows have four-share
  sums >1.0 with max 1.002 (bronze max 100.2 on the 0-100 scale), consistent
  with the partition-check tolerance (0.0025) and cap tolerance (0.005). Minor
  cosmetic inconsistency: the module docstring says "bronze max 100.1" while
  the quality-check description and observed gold say 100.2 — the 100.1 figure
  applies to the 3-summand `_or_above` inputs; no behavioral impact (could be
  folded into the Fix 1 prose pass).
- Optional enhancement (not required): an `active_duty ≤ military_connected`
  num_tested quality check (pivot-style per §15b) would mechanize the nested-
  key invariant verified manually here (0 violations / 37 comparable cells).
- 2024 `num_tested` mean jump (55.9 vs ~39 in prior years) is censoring, not
  scale drift: only cells with ≥10 students survive suppression.
- Skill math-test caveat: its CONFLATED heuristic fires on race_sum ≈ total,
  which for this 7-bucket *split* source is the expected complete partition —
  the structural evidence (explicit separate NHPI bronze rows; sum does not
  exceed total) rules conflation out. Recorded as PASS in §2e.
