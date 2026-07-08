# Data Review: retained_students

**Date**: 2026-06-11
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

PASS. v1 parity: **MATCH — byte-identical with v1 gold** (`compute_gold_sha256` vs `docs/rebuild/v1-baseline.yaml`). Every transform-agent claim was independently re-verified against bronze: the CENTRAL structure-doc correction (2004-2010 totals are TOTAL RETAINED, not enrollment) is proven by exact race-sum = gender-sum = total identities at the state row in all 21 years (ratio 1.0000 every year); the §5b combined Asian/Pacific Islander convention is proven by the same math test; the 2012 enrollment mask, the 2009 derived shares, the 2010 drops (1 malformed + 53 dups), and the 2022 reclassification all replay exactly from bronze. 458,559 gold rows = (51,005 bronze − 54 dropped) × 9, validation 21/21 with zero warnings, zero read loss. No required fixes; no judgment items.

## Manifest Verification

### Categorical maps

| Column | Entries | Bronze values seen | Unmapped | Status |
|---|---|---|---|---|
| `demographic` | 9 | 10 (incl. `MultiRacial`/`Multiracial` case variants) | 0 | PASS |
| `detail_level` | 3 | 3 | 0 | PASS |

**`demographic` — full map review (every entry):**

| Bronze (post-remap, uppercased) → gold | Correct? |
|---|---|
| `ALL` → `all` | YES — synthetic total-row literal emitted by `_melt_to_long`; carries the overall retained count, not a demographic |
| `ASIAN/PACIFIC ISLANDER` → `asian_pacific_islander` | YES — raw bronze label is bare `Asian`/`Asians`; the topic-local `_raw_demographic_label` remap to the combined bucket is proven by the §5b math test (race-sum/total ratio = 1.0000 at the state row in **all 21 years**; see Spot Checks) and by the structure doc: no era ever publishes a separate Pacific Islander row |
| `BLACK` → `black` | YES |
| `HISPANIC` → `hispanic` | YES |
| `WHITE` → `white` | YES |
| `MULTIRACIAL` → `multiracial` | YES — covers both tidy-era `MultiRacial` and wide-era `Multiracial` spellings; wide_v1 letter code `U` verified as Multiracial via state-row continuity (TU 1,325 in 2007 → 1,543 in 2008 → explicit `Retained Total Multiracial` 1,584 in 2009) |
| `AMERICAN INDIAN` → `native_american` | YES — the dimension's canonical key (no `american_indian_alaskan` key exists); wide_v1 code `N` verified by continuity (TN 67 in 2007 → 77 in 2009 explicit American Indian) |
| `MALE` → `male` | YES |
| `FEMALE` → `female` | YES |

**`detail_level`:** `State` → `state`, `District` → `district`, `School` → `school` — all correct. Wide eras derive detail level from `SysSchoolid` (`ALL:ALL`/`{d}:ALL`/`{d}:{s}`), verified in traces below.

- **2a Completeness**: all 8 demographic labels documented in the structure doc (per era) appear; the synthetic `all` is by design. No documented value missing. Note: `bronze_values_seen` records the **post-remap** label `Asian/Pacific Islander` (the `_raw_demographic_label` remap runs before normalization), so the raw `Asian`/`Asians` labels do not appear in the manifest — the remap itself was verified directly against bronze (math test + structure doc).
- **2c Contract cross-check**: `gold_values_produced` (9 values) == contract `enum` exactly. PASS.
- **2d Unmapped**: 0 for both columns. PASS.
- **2e Asian/PI conflation**: PASS (positive case) — gold emits `asian_pacific_islander` from an explicit combined remap; math test output: `retained_count: year=2024 total=44495 race_sum=44495 ratio=1.0000` and the per-year sweep shows ratio exactly 1.0 with n=6/6 race buckets published at the state row for every year 2004-2024.
- **2f Mutual exclusivity**: PASS — single convention; `asian` / `pacific_islander` split keys are never emitted alongside the rollup.

### Row-count reconciliation

| Year | Bronze | Dropped | Gold | Factor | | Year | Bronze | Dropped | Gold | Factor |
|---|---|---|---|---|---|---|---|---|---|---|
| 2004 | 1,996 | 0 | 17,964 | 9.0 | | 2015 | 2,463 | 0 | 22,167 | 9.0 |
| 2005 | 2,254 | 0 | 20,286 | 9.0 | | 2016 | 2,474 | 0 | 22,266 | 9.0 |
| 2006 | 2,285 | 0 | 20,565 | 9.0 | | 2017 | 2,479 | 0 | 22,311 | 9.0 |
| 2007 | 2,346 | 0 | 21,114 | 9.0 | | 2018 | 2,486 | 0 | 22,374 | 9.0 |
| 2008 | 2,392 | 0 | 21,528 | 9.0 | | 2019 | 2,491 | 0 | 22,419 | 9.0 |
| 2009 | 2,415 | 0 | 21,735 | 9.0 | | 2020 | 2,493 | 0 | 22,437 | 9.0 |
| 2010 | 2,506 | **54** | 22,068 | 8.81 | | 2021 | 2,505 | 0 | 22,545 | 9.0 |
| 2011 | 2,475 | 0 | 22,275 | 9.0 | | 2022 | 2,512 | 0 | 22,608 | 9.0 |
| 2012 | 2,485 | 0 | 22,365 | 9.0 | | 2023 | 2,502 | 0 | 22,518 | 9.0 |
| 2013 | 2,469 | 0 | 22,221 | 9.0 | | 2024 | 2,518 | 0 | 22,662 | 9.0 |
| 2014 | 2,459 | 0 | 22,131 | 9.0 | | | | | | |

Expansion factor exactly 9.0 (1 `all` + 8 demographics per bronze entity) in 20/21 years. 2010: 2,506 − 54 = 2,452 × 9 = 22,068 ✓; the 54 explicit drops (1 `malformed_sysschoolid` + 53 `duplicate_sysschoolid`) are manifest-recorded and verified in bronze (Spot Checks). Actual parquet rows **458,559** == manifest `total_gold` ✓ == (51,005 − 54) × 9 ✓. All 21 expected years present; no gaps (`year_gaps: []`). Read loss: zero events across 21 files.

## Column Coverage

| Bronze column(s) (era) | Gold column | Status |
|---|---|---|
| `School Year`/`School_Year` (tidy) | `year` | MAPPED (cross-checked vs filename; raises on disagreement) |
| filename year (wide eras — no year column) | `year` | MAPPED |
| `Data Reporting Level`/`Data_Reporting_Level` (tidy) | drives `detail_level` → file split | CORRECTLY EXCLUDED (implicit in filename) |
| `School District Code`/`School_District_Code` (tidy) | `district_code` | MAPPED (zfill(3); `ALL` → NULL) |
| `School Code`/`School_Code` (tidy) | `school_code` | MAPPED (zfill(4); `ALL` → NULL) |
| `SysSchoolid` (wide) | `district_code` + `school_code` + `detail_level` | MAPPED (split on `:`; `ALL` → NULL; zfill 3/4) |
| `School District Name`, `School Name`/`SchoolNme`, `School_*_Name` | — | CORRECTLY EXCLUDED (dimension attributes) |
| `Grades Served`/`Grades_Served` (tidy) | — | CORRECTLY EXCLUDED (institution metadata, not a fact) |
| `#RPT_NAME` (era 1) | — | CORRECTLY EXCLUDED (constant `Retained K-12`, guarded — raises on foreign values) |
| `Total Enrolled`/`Total_Enrolled` (tidy only) | `student_count` (`all` rows) | MAPPED (2012 §4b-masked) |
| `Total Retained`/`Total_Retained` (tidy), `Retained_NN` (wide_v1), `Retained Total Students` (wide_v2) | `retained_count` (`all` rows) | MAPPED — wide totals confirmed as TOTAL RETAINED (see Spot Checks), structure-doc correction verified |
| `Number of {d}`/`Number_of_{d}` (tidy), `Retained_T{x}` (wide_v1), `Retained Total {d}` (wide_v2) | `retained_count` (demo rows) | MAPPED (8 demographics × all eras; `_require_columns` guard fails loudly on absence) |
| `Percentage of {d}`/`Percentage_of_{d}` (tidy), `Retained_P{x}` (wide_v1), `Retained Percent {d}` (wide_v2) | `pct_of_retained_cohort` (÷100) | MAPPED (2009 White/Multiracial derived from counts — verified corrupt) |
| `Retained_N{A,B,F,H,M,U,W}` (wide_v1) | — | CORRECTLY EXCLUDED — re-verified: 0 mismatches vs `Retained_NN` in 2007 AND 2008 |
| `Retained {Demo}` ×7 (2004-2006, 2009) | — | CORRECTLY EXCLUDED — re-verified: 0 mismatches vs `Retained Total Students` in all 4 years |
| `Unnamed: 26`/`Unnamed: 27` (2009) | — | CORRECTLY EXCLUDED (Excel artifacts, never selected) |

No gold column lacks a bronze source (no fabrication): `year`, 2 geography keys, `demographic` (melt axis + synthetic `all`), 3 metrics — all traced.

## Value-Level Spot Checks

**Extreme rows first** (per-metric global max/min from manifest stats):

1. **`retained_count` global max** — 2007 state row. Bronze `retained_students_2007.xls` `ALL:ALL`: `Retained_NN='68423'`, `TM='42426'`, `TF='25997'`, `TW='22679'`, `PW='33.1'`. Gold (year=2007, both geo NULL): `all`=68423, `male`=42426, `female`=25997, `white`=22679 @ 0.331. **MATCH** — and 68,423 ≈ 3.5% of GA's ~1.6M K-12 enrollment, confirming the total-retained (not enrollment) reading; 42,426+25,997 = 68,423 exactly.
2. **`retained_count` global min** — 0 (wide eras only; tidy-era min is 10 because cells <10 are suppressed). Bronze 2004 `601:ALL` (Appling County): `Retained Total Asian='0'`, `Retained Percent Asian='0'` → gold `asian_pacific_islander` 0 @ 0.0. **MATCH** (zero_is_real).
3. **`student_count` global max** — 2018 state. Bronze 2018 State row: `Total Enrolled='1720916'`, `Total Retained='46156'` → gold 1,720,916 / 46,156. **MATCH**.
4. **`student_count` global min** — 2. Bronze 2018 `604`/`0183` Baker County Learning Center: `Total Enrolled='2'`, `Total Retained=None` (suppressed) → gold student_count=2, retained_count NULL. **MATCH** — extreme-but-conceivable (tiny alternative facility), preserved per §4b.
5. **`pct_of_retained_cohort` max** — 1.0 (3,862 rows). Bronze 2004 `604:ALL` Baker County: total='1', `Retained Total Black='1'`, `Retained Percent Black='100'`, Female='1'/'100' → gold black 1 @ 1.0, female 1 @ 1.0. **MATCH** (100 ÷ 100 = 1.0; a 1-student retained cohort is legitimately 100% one race/gender).
6. **`pct_of_retained_cohort` min** — 0.0 (published 0-of-N and 0-of-0 rows; see trace 12).

**§4b masked-cell trace (2012):**

7. Bronze `retained_students_2012.xlsx` State row: `Total Enrolled='27,864,309'` vs `Total Retained='56406'` — enrollment ~17x the real ~1.65M (2011: 1,633,596; 2013: 1,657,506) and >3x Georgia's population: impossible. District 601: `Total Enrolled='56627'` vs real ~3.2k (school 601/0103 published 16,303 vs ~1,000 in adjacent years — the same ~17x inflation at every level). Gold 2012: `student_count` NULL in **all** 22,365 rows (0 non-null); state/district `retained_count` 56,406 / 58 preserved. **MATCH** — manifest `masked_values` records column=student_count, count=2,485 (every `all` row in 2012), reason + years. Replayed and confirmed.

**2009 derived-share trace:**

8. Bronze `retained_students_2009.xls` state row: `Retained Percent White='61.1'`, `Retained Percent Multiracial='61.1'`, `Retained Percent Male='61.1'` — both corrupt columns repeat the Male share. Counts are internally consistent: total='61642', White='20064', Multiracial='1584'. File-wide replay: published-vs-derived off by >1pp in **656** White and **57** Multiracial rows; **0** for all six other demographics. Gold state 2009: white 20064 @ 0.3254923591058045 (= 20064/61642), multiracial 1584 @ 0.02569676519256351 (= 1584/61642); every non-corrupt demographic carries the published share (black 0.508, male 0.611). **MATCH** — the exact claimed defect, the exact claimed repair.

**Ordinary traces, one per era (all columns):**

9. **tidy_era1 (2024)** — district 601 Appling: bronze `Total_Enrolled='3237.00000'`, `Total_Retained='58'`, Black 13/22, Male 32/55 → gold all 58/3237, black 13 @ 0.22, male 32 @ 0.55 (float-string `3237.00000` → 3237 exact; 0 non-integer enrollment values exist anywhere in the tidy era, so the Float64→Int64 hop cannot truncate). **MATCH**.
10. **tidy_era2 (2016)** — district 601: bronze 3382/64, Black 10/16, White 35/55, Male 40/63, Asians suppressed (None) → gold matches every cell incl. `asian_pacific_islander` NULL. **MATCH**.
11. **wide_v1 (2007)** — school 601:103 Appling County High: bronze NN=42, TB 21/50, TW 19/45.2, TH 1/2.4, TU 1/2.4, TM 21/50, TF 21/50, TN 0/0, TA 0/0 → gold 601/0103 (zfill applied): all 42, black 21 @ 0.5, white 19 @ 0.452, hispanic 1 @ 0.024, multiracial 1 @ 0.024, male/female 21 @ 0.5, native_american 0 @ 0.0, asian_pacific_islander 0 @ 0.0. **MATCH** — all 17 metric cells.
12. **wide_v2 (2004)** — school 601:1050 Altamaha Elementary: bronze total 12, Black 2/16.7, White 9/75 → gold all 12, black 2 @ 0.167, white 9 @ 0.75. **MATCH**. Also 0-retained convention: 2010 `601:109` Baxley (total 0, all components 0) → gold publishes retained 0 @ 0.0 — bronze's published 0-of-0 zeros pass through as published.

**Suppression traces (4f), one per marker type:**

13. `TFS` (era 1): raw 2024 CSV 726/0201 Cowan Road Middle: `Total_Retained='TFS'`, `Number_of_Black='TFS'`, `Total_Enrolled='555.000000'` → gold retained_count NULL, black NULL, student_count 555. **MATCH**.
14. `Too Few Students` (era 2a): raw 2016 CSV 601/0103: `Number of Black='Too Few Students'`, `Total Retained='31'` → gold black NULL/NULL, all 31. **MATCH**.
15. Blank cells (2009): bronze `761:1008` Bakers Ferry-Residential Facility (all metrics blank) → gold: 9 rows, every metric NULL. **MATCH**. 2009 `Retained Total Students` has exactly **882** nulls — the structure doc's 882 suppressed rows confirmed.
16. Literal `NULL` strings (2005-2007): at the pandas dtype=str read the affected cells already arrive as NaN — 5 (2005), 5 (2006), 8 (2007) null totals, matching the doc's claimed row counts exactly; gold 2005/2006/2007 retained_count nulls = 45/45/72 = rows × 9. **MATCH** (representation detail noted in Notes).

**2010 drop/dedup traces:**

17. Malformed row: exactly 1 bronze row with `SysSchoolid=' Few Students'` (no colon), **all 17 metric cells NULL** — quoted from bronze. Dropped + manifest-recorded (`malformed_sysschoolid: 1`). **VERIFIED**.
18. Duplicates: exactly **53** duplicated `SysSchoolid` keys; **52** byte-identical pairs; the single divergent key is `746:4050` Chattanooga Valley Elementary — twin A: total 30, Male '19'/'63.3', Female '11'/'36.7'; twin B: same but Male NULL (extra suppressed cells). Gold kept twin A (male 19 @ 0.633 present; 9 rows exactly at that key). **MATCH — most-complete row won**. Counter-claim check: 2009 has **0** duplicated keys — v1's "2 duplicate pairs in 2009" claim is confirmed false.

**2022 reclassification trace:**

19. Bronze 2022: exactly 2 rows with `Data Reporting Level='School'` AND `School Code='ALL'` — districts 7830627 (Atlanta SMART Academy, enrolled 123) and 7830636 (Northwest Classical Academy, enrolled 505); **0** genuine District rows for those codes (no collision possible). Gold: both land in `year=2022/districts.parquet` with `school_code` NULL (student_count 123/505); their genuine school rows (0627/0636) remain in `schools.parquet`. **MATCH**.

**Aggregate feasibility screen (4d, aggregates come from bronze):** district `retained_count` < max school: **0** violations; district < visible school sum: **0**; same for `student_count` (0 and 0 at 2% tolerance). State vs sum-of-district `all` rows: ratio exactly 1.0 in 2004-2010 (no suppression of totals), drifting to 0.90-0.92 by 2023-24 — visible-sum ≤ total, the correct direction under growing TFS suppression. **PASS**.

## Validation Cross-Read

- `_validation.json`: **passed=true**, 21/21 checks pass, 0 warnings — including `contract_parquet_schema`, `contract_quality_sql`, `grain_uniqueness`, `foreign_keys` (district 252 keys, school 2,896 keys, demographic 9 keys — all resolve), `geography_nulling` ×3.
- Contract `schema_hash`: `f76fa41129994a745d50d5ed9e6535d2e92634cea9feab02b275ff33573de926`.
- **§4b masking audit**: one `_null_*` helper (`_null_corrupt_2012_student_count`). Manifest `masked_values`: recorded (column, count=2,485, reason, years=[2012]) ✓; documented in the contract `student_count` description AND `limitations` AND a note ✓; enforceable guard: the authored quality check `student_count_only_on_all_rows_in_published_years` explicitly includes `year = 2012` in its must-be-NULL predicate, so the masked values cannot silently return ✓. Fully compliant.
- **§15b coverage judgment**: 5 authored checks + 5 auto-derived (non_empty, enum, 2 count ≥0, proportion [0,1]). The two load-bearing invariants — race AND gender count partition-sums via NULL-guarded conditional aggregation — are authored and pass (and I independently confirmed 0 mismatches at the state level in all 21 years). `retained_count ≤ student_count`, pct-NULL-on-`all`, and the structural student_count rule cover the remaining cross-column facts. The deliberate omission of **percent** partition sums is justified by evidence: state race-share sums range 0.990-1.010 (whole-percent rounding) and 2023/2024 publish only 5/6 race shares (state American Indian share TFS-suppressed) — an exact-sum check would be unauthorable without tolerance hacks, and the count-based checks pin the same invariant exactly. No missing obvious invariant. **PASS**.
- **v1 parity** (verbatim): `MATCH — byte-identical with v1 gold`.

## Cross-Era Consistency

- **Overlap years**: none — 21 files, 21 distinct years (manifest `files_processed`); era routing per file verified (2004-06/09/10 → wide_v2, 2007-08 → wide_v1, 2011-22 → tidy_era2, 2023-24 → tidy_era1). Dedup tie-break across files: N/A (no overlap); the within-2010 bronze dedup is traced above.
- **Era-boundary continuity**: state retained_count 2004→2024: 58,302 … 68,423 (2007) … 59,999 (2010) | 59,444 (2011) … 47,406 (2020), 37,065 (2021 — COVID promotion policies), 55,213 (2022 rebound), 44,495 (2024). No discontinuity at either era boundary (2010→2011: 59,999→59,444); no >10x jump anywhere; state student_count 1.63M→1.72M smooth across 2011-2024. The per-row mean retained_count jump 2010→2011 (36.8→106.2) is the suppression-composition artifact (tidy era suppresses cells <10; wide eras publish 0s) — expected, not a scale issue.
- **Cross-year NULL sweep**: one flag — `student_count` ~100% NULL only in [2004-2010, 2012]: exactly the documented structural gap (wide eras publish no enrollment) plus the §4b mask. Not a rename bug: the wide-era bronze genuinely has no enrollment column (verified — the "total" columns are retained counts). No column is 100% NULL in every year.

## Transform Logic Risks

| Risk | Severity | Details |
|---|---|---|
| Silent column drops | PASS | `_require_columns` guard per era fails loudly; redundant copies verified equal before exclusion (0 mismatches, re-executed) |
| Era routing | PASS | Signature-based, most-specific first; all 21 files routed correctly per manifest |
| Filter logic | PASS | Only 2 filters (malformed + dup 2010), both manifest-recorded, both replayed from bronze |
| Normalization map completeness | PASS | 100% of map entries semantically reviewed; §5b remap proven by math test |
| `strict=False` casts | PASS | Float64→Int64 hop tolerates float-formatted counts; 0 non-integer enrollment values exist (no truncation possible); residual non-numerics are genuine suppression |
| Dedup keys + tie-break | PASS | Natural-key collision guard runs BEFORE dedup; no cross-file overlap; 2010 most-complete-wins traced |
| Year extraction | PASS | Tidy: School Year cross-checked against filename (raises on disagreement; verified `2015-16`→2016); wide: filename only, per GOSA convention (Risk 3 N/A — no other year-bearing strings) |
| §4b mask (5b) | PASS | Recorded, documented, guard-enforced (see Validation Cross-Read) |

Risk hypotheses 1-7: 1 PASS (combined bucket handled correctly), 2 PASS (sweep clean), 3 N/A→PASS, 4 PASS (0 feasibility violations), 5 PASS (no overlap; bronze dedup traced), 6 PASS (single convention), 7 PASS (100% map review).

## Notes

- `schema_hash`: `f76fa41129994a745d50d5ed9e6535d2e92634cea9feab02b275ff33573de926`; validation 21/21 pass, 0 warnings; read_loss events: 0; masked: 1 event (2,485 cells); reclassified: 1 event (2 rows); filtered: 54 rows (2010).
- **2009 repair footprint (quantified, correct as shipped)**: replacing the two corrupt percent columns wholesale means gold pct is NULL where the derivation has no denominator: White — 105 count-published rows with total=0 (bronze published '0' from the corrupt column) + 277 with total suppressed (bronze published a corrupt value); Multiracial — 105 + 742. All discarded values came from columns proven corrupt (both repeat the Male share at every verifiable row), so NULLing rather than trusting them is the right §4b call; the trustworthy counts on those rows are preserved. Side effect: on total=0 entities, 2009 White/Multiracial pct is NULL while sibling demographics carry the published 0.0 — acknowledged in the transform docstring ("a derived value must not fabricate one"), v1-identical (parity MATCH).
- **Structure-doc sample tables (Era 2) are garbled — doc hygiene only**: the "Sample Data (2016)" district-601 row (3187/65/18/28) and school rows (946/23, 531/10) match no year of bronze (2016 actual: 3382/64/10/16; 983/31; 546/suppressed — and 946/23 appears in no year 2011-2024); the 2022 sample rows are likewise inexact. The wide-era samples (2004, 2007, 2010) match bronze exactly. Gold is unaffected — every value in this review was traced against actual bronze, and the doc's Gold Schema Classification, era schemas, and 2026-06-11 Corrections are all accurate. Worth fixing the sample tables on the doc's next touch.
- **Suppression-marker representation nuance**: the structure doc describes 2005-2007's markers as literal `NULL` strings; at the pandas `dtype=str` read path the affected cells arrive as NaN (counts match the doc exactly: 5/5/8). Either way the same gold NULLs result; no action needed.
- **Manifest remap visibility**: `bronze_values_seen` for `demographic` records post-`_raw_demographic_label` labels, so the raw `Asian`/`Asians` → `Asian/Pacific Islander` remap is invisible in the manifest itself; this review verified it directly (math test, all 21 years, ratio exactly 1.0).
- Tidy-era `retained_count` minimum of 10 is the privacy-threshold floor (cells <10 suppressed), not a data defect; wide eras publish true 0s (56,103 zero rows, 2004-2010 only).
- Co-null structure: 0 rows publish a pct with a NULL count; 6 rows (2023-24, incl. the state American Indian rows) publish a count with a suppressed pct — faithful to bronze's asymmetric suppression.
