# Data Review: attendance

**Date**: 2026-06-10
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Bronze-to-gold accuracy is verified end-to-end: every categorical mapping is semantically correct, all era traces match bronze byte-for-byte, both §4b masks and both source-defect repairs reproduce exactly from bronze, and the aggregate feasibility screen is clean. **v1 parity DIFFERS, fully accounted**: the only cell-level differences from the v1 baseline are the two new §4b masks (346,173 cells changed `0`→NULL: 320,742 tier-rate cells + 25,420 chronic cells + 11 student_count cells); row counts, keys, and all other values are provably identical. One LOW documentation fix: the impossible-zero-count helper docstring overclaims its sibling-count evidence ("ALL minus MALE > 0 on every affected row" is not computable for 4 of the 11 rows).

## Manifest Verification

### Categorical maps

| Column | Entries | Bronze seen | Unmapped | Status |
|--------|--------:|------------:|---------:|--------|
| demographic | 23 | 30 (15 wide labels + 15 tidy suffixes) | 0 | PASS |
| detail_level | 3 | 3 | 0 | PASS |

### demographic — full map review (every entry)

| Bronze (upper-normalized) | Gold | Correct? |
|---|---|---|
| ALL | all | ✓ unfiltered total |
| ASIAN | asian_pacific_islander | ✓ §5b combined bucket — see math test below |
| BLACK | black | ✓ |
| HISPANIC / HISPANI | hispanic | ✓ (HISPANI is the literal truncated tidy suffix, structure doc §20) |
| WHITE | white | ✓ |
| MULTIRACIAL / MULTI | multiracial | ✓ |
| NATIVE AMER/ALASKAN NATIVE / INDIAN | native_american | ✓ |
| MALE | male | ✓ |
| FEMALE | female | ✓ |
| ECONOMICALLY DISADVANTAGED / ED | economically_disadvantaged | ✓ |
| NOT ECONOMICALLY DISADVANTAGED / NOT_ED | not_economically_disadvantaged | ✓ complement category |
| STUDENTS WITH DISABILITIES / SWD | students_with_disabilities | ✓ |
| STUDENTS WITHOUT DISABILITIES / NOT_SWD | students_without_disabilities | ✓ complement category |
| LIMITED ENGLISH PROFICIENT / LEP | english_learners | ✓ legacy term → canonical key |
| MIGRANT | migrant | ✓ |

All 30 `bronze_values_seen` are exactly the 15 wide-era labels + 15 tidy-era suffixes documented in `bronze-data-structure.md`; no documented value is unseen, no seen value is undocumented. `gold_values_produced` (15 keys) equals the contract `validValues` enum exactly. `unmapped_count` = 0 for both columns.

### detail_level

`State`→state, `District`→district, `School`→school — all correct; gold values land in the partition file split (states/districts/schools.parquet), not a fact column.

### §5b Asian/Pacific Islander (Risk 1) — PASS, combined convention proven

- `grep -iE 'pacific[ _-]?islander|...' bronze-data-structure.md` → `NO_NHPI_LABEL_IN_BRONZE`.
- Math test (executed): `student_count: year=2024 total=1867876 race_sum=1867876 ratio=1.0000 -> CONFLATED` — exact partition, positive evidence for the explicit `asian_pacific_islander` remap.
- 2013 pinned exception verified in BRONZE: state `STUDENT_COUNT_ALL = 1837279`, race buckets {INDIAN 4161, ASIAN 64408, BLACK 704006, WHITE 775949, HISPANI 231807, MULTI 56940} sum to 1,837,271 — **gap exactly 8**; male+female = 1,837,279 (gap 0). The pinned `state_race_partition_2013_gap_is_8` check is faithful to the source.
- v1 made the identical remap (`_raw_demographic_label`), so this is not a v1 deviation.

### Mutual exclusivity (Risk 6) — PASS, single convention

Gold publishes `asian_pacific_islander` only; `asian` / `pacific_islander` never emitted. No rollup/split coexistence.

### Row-count reconciliation

| Year | Bronze | Filtered (explicit) | Gold | Check |
|------|-------:|--------------------:|-----:|-------|
| 2004 | 2,243 | 23 (corrupt block: 1 unkeyable + 22 re-pastes) | 33,300 | (2243−23)×15 ✓ |
| 2005–2008, 2010–2024 | n | 0 | n×15 | exact ×15 ✓ (all 17 years) |
| 2009 | 2,417 | 30 (2 republished charter keys × 15 demos) | 36,225 | 2417×15−30 ✓ |
| **Total** | **51,238** | **53** | **768,195** | parquet row count = 768,195 = manifest `total_gold` ✓ |

All 21 expected years (2004–2024) present. Expansion factor 15.0 everywhere except the two explained years.

## Column Coverage

| Bronze column | Gold | Status |
|---|---|---|
| SysSchoolID / sysschoolid / SchoolID (wide) | district_code + school_code + detail_level | MAPPED (split on `:`, ALL→NULL, zfill 3/4) |
| School Name / schoolname (wide) | — | CORRECTLY EXCLUDED (dimension attribute) |
| Number of Students {demo} ×15 (wide) | student_count | MAPPED (unpivot; `_require_columns` asserts all 60) |
| 5 or Fewer / 6 to 15 / More than 15 Days Absent {demo} ×45 (wide) | three `*_absent_rate` cols | MAPPED (÷100) |
| (chronic — wide era) | chronically_absent_rate | typed NULL — column does not exist in source ✓ |
| LONG_SCHOOL_YEAR (tidy) | year | MAPPED (ending year, hard-stop cross-check vs filename) |
| DETAIL_LVL_DESC (tidy) | detail_level → partition file | MAPPED |
| SCHOOL_DSTRCT_CD / INSTN_NUMBER (tidy) | district_code / school_code | MAPPED (ALL→NULL, zfill) |
| SCHOOL_DSTRCT_NM / INSTN_NAME (tidy) | — | CORRECTLY EXCLUDED (dimensions) |
| GRADES_SERVED_DESC (tidy) | — | CORRECTLY EXCLUDED (school metadata; contract notes it) |
| #RPT_NAME (era 8) | — | CORRECTLY EXCLUDED (constant; guarded by `_validate_era8_constants`) |
| STUDENT_COUNT_/FIVE_OR_FEWER_/SIX_TO_FIFTEEN_/OVER_15_/CHRONIC_ABSENT_PERC_{demo} (tidy) | 5 metric cols | MAPPED (`_require_columns` asserts all 60; chronic all-15 asserted when present) |

No gold column lacks a bronze source; no fact-relevant bronze column is dropped.

## Value-Level Spot Checks

All executed bronze→gold; every trace MATCH.

**Extreme rows**
- Global max `student_count`: gold 2017 state `all` = 1,898,534 ← bronze 2017 `STUDENT_COUNT_ALL` (State row) = `1898534`. MATCH.
- Global min `student_count`: gold 2004 district 603 `native_american` = 0 with all rates NULL ← 2004 zero-population convention (blank rates in source). MATCH.
- Rate extremes (0.0 / 1.0) are bronze-published 0/100 values (e.g. 2006 `601:103` Asian below); contract unit checks bound them.

**Era traces (one entity per era, all columns)**
- Era 1 (2006, XLS-mislabeled-.csv): bronze `601:103` All = `['954','45.2','38.1','16.8']` → gold 2006 601/0103 all = (954, 0.452, 0.381, 0.168, chronic NULL). Asian = `['5','100','0','0']` → a_pi (5, 1.0, 0.0, 0.0). MATCH.
- Era 2 (2008 xls): `601:1050` All `['425','39.3','49.9','10.8']` → (425, 0.393, 0.499, 0.108). MATCH.
- Era 3 (2009 xls): `ALL:ALL` Female `['902089','58','33.4','8.6']` → state female (902089, 0.58, 0.334, 0.086). MATCH.
- Era 4 (2010 xls): `601:ALL` Migrant `['99','53.5','36.4','10.1']` → district 601 migrant (99, 0.535, 0.364, 0.101). MATCH.
- Era 5 (2011): 601/0103 ALL `['991','27.5','46.3','26.1',None]` → (991, 0.275, 0.463, 0.261, NULL). MATCH.
- Era 6 (2015): district 644 SWD `['12047','46.6','35.1','18.3']` → (12047, 0.466, 0.351, 0.183, NULL). MATCH.
- Era 7 (2021): state ALL `['1818081','52.3','27.8','19.9','20.4']` → (1818081, 0.523, 0.278, 0.199, 0.204). MATCH.
- Era 8 (2024): 601/0103 ALL `['1112','39.8','33.5','26.6','28.1']` → (1112, 0.398, 0.335, 0.266, 0.281). MATCH.

**Suppression traces (4f)**
- 2021 TFS (raw read): 601/0103 INDIAN all five cells = `'TFS'` → gold native_american row all NULL. MATCH.
- 2024 per-cell TFS mix: 601/1050 MIGRANT = `['TFS','85.7','14.3','TFS','28.6']` → gold (NULL, 0.857, 0.143, NULL, 0.286) — per-cell suppression preserved, no co-nulling. MATCH.
- 2004 blank-cell (count>0): `755:2050` White raw line fields verified against header: `Number of Students White='313'`, rates `'47.6','41.2','11.2'` → gold (313, 0.476, 0.412, 0.112). MATCH (the identical-to-All rates are genuine in the byte line — 313 of 357 students; no column shift).

**§4b mask 1 — zero-population placeholders (2005–2020): VERIFIED EXACTLY + judged SOUND**
- Bronze recount using the transform's own predicate (count==0, all rates 0-or-null, ≥1 rate non-null), per year: 2004=0, 2005=3,569, 2006=3,702, 2007=3,773, 2008=3,831, 2009=3,804, 2010=3,549, 2011=8,351, 2012=8,405, 2013=8,274, 2014=8,491, 2015=8,531, 2016=8,625, 2017=8,589, 2018=8,516, 2019=8,421, 2020=8,483, 2021–2024=0. **Total 106,914 = manifest count exactly** (per tier column); chronic placeholders 8,351 (2011) + 8,516 + 8,421 + 8,483 (2018–2020) = **33,771 = manifest count exactly**.
- The three tier-mask counts are identical (106,914 each) → every masked row had a complete all-zero triple (no partial-null ambiguity ever fires in 2005–2020, which have no metric nulls outside 2011 chronic). A real population's tiers must sum to ~100, so an all-zero triple with count=0 is provably a placeholder, not a measurement; 2004 publishes NULL in the same situation (era consistency); the mask is recorded per column, documented in every rate column's contract description, and pinned by the `zero_population_rates_null` quality check. **Verdict: sound — keeping the 0.0s (v1 behavior) would poison rate averages with undefined values.**
- Spot trace: 2011 601/0109 MIGRANT bronze `['0','0','0','0','0']` → gold (0, NULL, NULL, NULL, NULL), count kept. MATCH.
- 2011 chronic claim verified: the file's 8,351 non-null chronic cells are exactly the count-0 placeholder rows, so 2011 publishes no real chronic data.

**§4b mask 2 — impossible zero counts (2023–2024): VERIFIED EXACTLY + judged SOUND**
- Full-corpus sweep (all 21 years, all 15 demographics) for count==0 with any rate > 0 finds **exactly 11 rows, all FEMALE: 2023 = 5, 2024 = 6** — matching the manifest. No other year/demographic is affected.
- Sibling proof where computable, e.g. 2023 East DeKalb Special Education Center: `STUDENT_COUNT_ALL='80'`, `MALE='71'`, `FEMALE='0'` with `FIVE_OR_FEWER_PERCENT_FEMALE='100'` → 9 female students exist; the count is the impossible value. 2024 rows include Price Academy (26/17/0 with 88.9) and East DeKalb (88/80/0 with 100).
- 4 of the 11 rows (2023 Baker County, 2024 Baker County, 2024 Dooly, 2024 Georgia Baptist) have ALL and/or MALE TFS-suppressed, so the documented "ALL minus MALE > 0 on every affected row" is not computable there — for those rows the proof is the published rates themselves (e.g. 100% over-15 cannot describe an empty population). **Verdict: mask sound (NULL the count, keep the rates); see Fix 1 for the docstring overclaim.**

**Source-defect repairs**
- 2004 corrupt trailing block (executed byte-level verification): unkeyable line at index 2221; its 20 fields are exactly the tail of the intact `754:197` line (`endswith` = True). 22 keyed lines follow: **21 byte-identical** to intact earlier rows; **1 (`756:101`) a strict prefix truncated at field 52 (`'42'` vs intact `'42.4'`)**, 52 of 62 fields. Zero novel keys → drop loses nothing. Gold 756/0101 rows match the INTACT copy. Manifest 1 + 22 ✓.
- 2009 republished charter aggregates: `768:ALL` (Ivy Prep) and `770:ALL` (Scholars Academy) each appear twice, metrics byte-identical, one copy NULL name → 30 gold-grain rows deduped ✓.
- 2022 reclassification: exactly 2 rows have `DETAIL_LVL_DESC='School'` + `INSTN_NUMBER='ALL'` — districts 7830627 (Atlanta SMART Academy, count 144) and 7830636 (Northwest Classical Academy, count 542); neither has a genuine District row (each district has exactly 1 school row + the mislabeled aggregate). Sweep of 2011–2024 finds the defect in no other year. Reclassify-to-district is correct ✓.

**4c sentinel year-attribution**: tidy years derive from `LONG_SCHOOL_YEAR` with a hard-stop if the ending year disagrees with the filename year; 2021/2024 traces above land in the right gold years. PASS.

**4d aggregate feasibility screen** (aggregates come from bronze): district `student_count` < max school count: **0 violations**; district/Σ(schools) ratio quantiles (p1/median/p99) = 1.0/1.0/1.0; state/Σ(districts) = 1.0 in 16 of 21 years, tiny positive drift in 2004 (1.00026), 2007 (1.0035), 2015, 2018, 2019 (state ≥ sum — students not attributed to a reporting district; composition drift, not garbling). PASS.

**4e dedup tie-break**: no overlap years across files (one school year per file, enforced by the LONG_SCHOOL_YEAR/filename hard-stop); within-file dups are byte-identical (2009 trace above). N/A / PASS.

## Validation Cross-Read

- `_validation.json`: **20 pass / 0 fail / 1 warning**; `contract_parquet_schema`, `contract_quality_sql` (all 13), `grain_uniqueness`, `foreign_keys` (252 districts, 2,911 schools, 15 demographics all resolve) pass.
- Warning: `null_rate_spikes` — `student_count` 2021–2024 null rate ~22–23% vs median 0%. Explained: TFS suppression begins 2021 (TFS-only 2021–2022, TFS+blank per-cell 2023–2024); documented in contract `limitations`. Not a transform defect.
- `schema_hash`: `16ed7214c48f5ee3b1234fce5087258ee2c3c19743a945fc7273a07afce22ab9`; contract `version` 1.0.0.
- **§4b masking audit**: both `_null_*` helpers recorded in `masked_values` (counts independently reproduced from bronze, above); handling documented in `student_count` and all four rate columns' contract descriptions + `null_meaning`; range guards present (`unit: proportion` → [0,1]; `count` → ≥0); masks enforced by `zero_population_rates_null`. PASS (one prose overclaim → Fix 1).
- **§15b coverage**: quality list covers the real invariants — tier partition sum (`absentee_tiers_partition_population`, domain-registered), race partition exact (year ≠ 2013), 2013 gap pinned at exactly 8, gender partition exact, zero-population co-null, chronic NULL through 2017, per-unit ranges, enum, non-empty. No obvious missing invariant (chronic vs over-15 has no strict relation — different cutoffs; per-cell 2023–2024 suppression precludes a tier co-null check, correctly noted in the contract).
- **v1 parity (5d)** — executed output verbatim:

```
DIFFERS from v1
  v1:  de95a2d8f09e8af21bb83566b464682b9f686bdf9a5eda236b9e8ba0664db981
  now: 346c44a349ee0d48b1c00320e4f7371c3d61d68e0508f712c63e8a2d7ff0b6bc
```

  **Exact delta accounting** (from v1 transform at `v1-pipeline` tag vs current):
  1. **Zero-population mask (new)**: v1 had no mask → kept bronze `0.0`. Delta: 106,914 cells × 3 tier columns = **320,742 cells** (2005–2020) + **25,420 chronic cells** (2018–2020: 8,516+8,421+8,483) now NULL. 2011 chronic is NOT a delta — v1 blanket-nulled all of 2011 chronic (`if year == 2011` override), v2's mask nulls the same 8,351 cells (the rest were bronze-NULL); identical end state.
  2. **Impossible-count mask (new)**: **11 `student_count` cells** (2023: 5, 2024: 6) `0` → NULL.
  3. **2004 corrupt block — NOT a delta**: v1 filtered the unkeyable orphan and deduped the 22 duplicate keys by per-file `unique(keep first after sort by _non_null_count desc)` — the truncated 756:101 copy (10 missing fields) loses to the intact copy, byte-identical pairs are value-equal either way → same 2,220 surviving entities as v2's block drop.
  4. **Asian/PI remap and 2022 reclassification — NOT deltas**: v1 contains both (its `_raw_demographic_label` maps Asian→Asian/Pacific Islander; its tidy path reclassifies `School`+`INSTN_NUMBER='ALL'` to district).
  5. Row counts identical (51,238 bronze → 768,195 gold, same per-year), keys identical, written column order identical (v1's `export_to_parquet` drops `detail_level` too).

  Total: **346,173 cells differ, all `0`→NULL from the two new §4b masks; nothing else.**

## Cross-Era Consistency

- Overlap years: none (each file one school year; hard-stop guard). N/A.
- Cross-year NULL sweep: single flag — `chronically_absent_rate` ~100% NULL 2004–2017. Expected and pinned: column absent in 2004–2010 and 2012–2017 sources; 2011 holds only placeholders. All other columns populated every year.
- Era-boundary continuity (state level): student_count 1.71M (2004) → 1.87M (2024), smooth across the 2010/2011 wide→tidy boundary (1,860,412 → 1,866,423) and the 2017/2018 chronic introduction. No >10x jumps; no revert-style level shifts. The 2021–2024 attendance deterioration (five_or_fewer mean 0.52 → 0.36; over_15 0.08 → 0.24) appears in the bronze state rows verbatim (2021 trace above) — a real post-COVID shift, not a scale artifact (tiers still partition to ~1.0).

## Transform Logic Risks

| Risk | Severity | Details |
|------|----------|---------|
| Silent column drops | PASS | `_require_columns` asserts all 60 wide / 60+15 tidy metric columns per file; era-8 `#RPT_NAME` constant guard |
| Era routing | PASS | Signature-based, most-specific first; manifest `files_processed` shows the expected era per file; year ranges never used for detection |
| Filter logic logged + justified | PASS | Corrupt block: evidence-based detection (unkeyable marker + hard-stop on novel keys), `record_filtered` 1+22; dedup removals recorded per year (30) |
| Normalization map completeness | PASS | 30/30 bronze labels mapped; matches structure-doc §5 table |
| `strict=False` casts | PASS | Confined to metric columns after `read_bronze_file` suppression handling; residue would surface in null-rate spikes / range checks |
| Dedup keys + tie-break | PASS | `assert_no_natural_key_collisions` BEFORE dedup guarantees only value-identical duplicates are deduped; `sort_col="student_count"` safety net |
| Year extraction | PASS | Filename year ⟷ LONG_SCHOOL_YEAR hard-stop; wide era filename-only per structure doc §18 |
| §4b masks (5b) | PASS | Recorded, documented, range-guarded, quality-pinned; counts reproduced from bronze exactly |

## Required Fixes

### Fix 1: Impossible-zero-count helper docstring overclaims its sibling-count evidence
- **Severity**: LOW
- **Issue**: `_null_impossible_zero_student_counts`'s docstring asserts "sibling counts prove the population is non-empty (ALL minus MALE > 0 on every affected row)". This is false for 4 of the 11 affected rows, where ALL and/or MALE are TFS-suppressed and the difference is not computable: 2023 Baker County Learning Academy (ALL='10', MALE=TFS), 2024 Baker County (ALL=TFS, MALE=TFS), 2024 Dooly County Prep (ALL='14', MALE=TFS), 2024 Georgia Baptist Children's Home (ALL=TFS, MALE=TFS). The mask itself is correct — for those rows the impossibility proof is the published rates (e.g. 2024 Baker County FEMALE count 0 with `OVER_15_PERCENT_FEMALE='100'`, `CHRONIC='100'`; a zero population cannot have 100% of itself absent).
- **Evidence**: Bronze 2024 row (`604`, `0183`, Baker County Learning Academy): `STUDENT_COUNT_FEMALE='0'`, `STUDENT_COUNT_ALL=NULL(TFS)`, `STUDENT_COUNT_MALE=NULL(TFS)`, `OVER_15_PERCENT_FEMALE='100'` — vs docstring claim "ALL minus MALE > 0 on every affected row". Gold data is unaffected (count NULL, rates kept — correct).
- **Location**: `_null_impossible_zero_student_counts` docstring in `src/etl/education/gosa/attendance/transform.py` (the module docstring and contract use a correctly hedged "e.g." example and need no change).
- **Suggested fix**: Reword to "sibling counts prove the population is non-empty on 7 of the 11 rows (ALL − MALE > 0); the remaining 4 rows have TFS-suppressed siblings and are proven impossible by their published non-zero rates alone". No transform-logic or gold-data change.

## Notes

- `schema_hash`: `16ed7214c48f5ee3b1234fce5087258ee2c3c19743a945fc7273a07afce22ab9`; validation 20 pass / 0 fail / 1 explained warning; 13/13 contract quality checks pass.
- Gold: 768,195 rows, 21 years, 63 parquet files; grain (`year`, `district_code`, `school_code`, `demographic`) unique.
- Structure-doc nit (no action for this topic): `bronze-data-structure.md` Era 5 prose says the 2011 chronic columns have "only 1–4 rows per column with any value", contradicted by its own null-count table (8,351 non-null cells total, e.g. INDIAN has 2,354). The transform and this review used the table (and verified all 8,351 are count-0 placeholder zeros), so the gold is unaffected.
- Both §4b deviations from v1 are judged **sound improvements**: the zero-population mask removes provable placeholders (undefined rates) that v1 shipped as real 0.0 measurements, and the impossible-count mask removes contradictory zeros v1 shipped as real counts. The 2004 corrupt-block handling and the 2022 reclassification are behaviorally identical to v1 despite different code paths.
