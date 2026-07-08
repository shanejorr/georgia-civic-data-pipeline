# Data Review: dropout_rate_7_12

**Date**: 2026-06-10
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

The rebuild is value-accurate end to end: **v1 parity is MATCH (byte-identical with v1 gold)**, all 250,292 bronze rows reach gold with zero filtering, every categorical map entry is semantically correct, all 9 bronze→gold spot traces match exactly (including the 2022 reclassified aggregates and both suppression-marker eras), and the aggregate-row feasibility screen found zero impossible district/state values across 14,137 district groups. One MEDIUM contract-coverage fix: the state-level economic and disability partition sums hold exactly in every year (verified) but are not pinned as contract quality checks, while the equivalent race and gender partitions are.

## Manifest Verification

| Column | Map entries | Bronze values seen | Unmapped | Status |
|--------|-------------|--------------------|----------|--------|
| `demographic` | 15 | 15 | 0 | PASS |
| `detail_level` | 3 | 3 | 0 | PASS |

### Full map review — `demographic` (after stripping the constant `"7-12 Drop Outs -"` prefix)

| Bronze (uppercased) | Gold | Correct? |
|---|---|---|
| ALL STUDENTS | `all` | Yes — unfiltered total row |
| ASIAN/PACIFIC ISLANDER | `asian_pacific_islander` | Yes — bronze publishes the explicitly combined label; §2e math test confirms (see Spot Checks) |
| BLACK | `black` | Yes |
| HISPANIC | `hispanic` | Yes |
| WHITE | `white` | Yes |
| MULTI-RACIAL | `multiracial` | Yes |
| AMERICAN INDIAN/ALASKAN | `native_american` | Yes — canonical key for American Indian/Alaska Native |
| MALE | `male` | Yes |
| FEMALE | `female` | Yes |
| ECONOMICALLY DISADVANTAGED | `economically_disadvantaged` | Yes |
| NOT ECONOMICALLY DISADVANTAGED | `not_economically_disadvantaged` | Yes — distinct complement key, not conflated |
| STUDENTS WITH DISABILITY | `students_with_disabilities` | Yes |
| STUDENTS WITHOUT DISABILITY | `students_without_disabilities` | Yes — distinct complement key |
| LIMITED ENGLISH PROFICIENT | `english_learners` | Yes — canonical key for LEP/EL |
| MIGRANT | `migrant` | Yes |

### Full map review — `detail_level`

| Bronze | Gold | Correct? |
|---|---|---|
| State | `state` | Yes |
| District | `district` | Yes |
| School | `school` | Yes |

- **2a Completeness**: the 15 `bronze_values_seen` exactly match the 15 prefix-stripped labels documented in `bronze-data-structure.md` (Era 1 categorical table); no documented value is unseen, none seen that is undocumented. The 2020–2022 14-label gap (no `Limited English Proficient`) is reflected and pinned by a quality check.
- **2c Contract cross-check**: `gold_values_produced` (15 keys) equals the contract `enum` for `demographic` exactly. `detail_level` is correctly not a gold column (implicit in filename).
- **2d Unmapped**: 0 in both columns.
- **2e Asian/PI**: gold has no `asian` key (triage N/A for the remap direction), and the math test run as positive evidence shows the six race buckets sum EXACTLY to `all` (ratio 1.0000) in all 14 years — the combined `asian_pacific_islander` key is the proven-correct convention. Executed output (excerpt):
  `2024: all=20203 race_sum=20203 ratio=1.0000 gender_sum=20203 buckets=['asian_pacific_islander', 'black', 'hispanic', 'multiracial', 'native_american', 'white']` (identical ratio for 2011–2023).
- **2f Mutual exclusivity**: PASS — single convention; `asian` / `pacific_islander` split keys never emitted alongside the rollup.

### Row-count reconciliation

| Year | Bronze | Gold | Filtered | Expansion |
|------|--------|------|----------|-----------|
| 2011 | 17,310 | 17,310 | 0 | 1.0 |
| 2012 | 17,610 | 17,610 | 0 | 1.0 |
| 2013 | 17,670 | 17,670 | 0 | 1.0 |
| 2014 | 17,640 | 17,640 | 0 | 1.0 |
| 2015 | 17,880 | 17,880 | 0 | 1.0 |
| 2016 | 17,940 | 17,940 | 0 | 1.0 |
| 2017 | 18,015 | 18,015 | 0 | 1.0 |
| 2018 | 18,195 | 18,195 | 0 | 1.0 |
| 2019 | 18,330 | 18,330 | 0 | 1.0 |
| 2020 | 17,150 | 17,150 | 0 | 1.0 |
| 2021 | 17,248 | 17,248 | 0 | 1.0 |
| 2022 | 17,444 | 17,444 | 0 | 1.0 |
| 2023 | 18,840 | 18,840 | 0 | 1.0 |
| 2024 | 19,020 | 19,020 | 0 | 1.0 |
| **Total** | **250,292** | **250,292** | **0** | |

Assessment: perfect 1:1 row preservation; per-year bronze counts match the structure doc's Era 2 table and the Era 1 statistics exactly. Actual parquet row count = **250,292** = manifest `total_gold`. All 14 expected years present. Manifest non-null counts tie exactly to the structure doc's suppression counts (e.g., 2011: 17,310 − 13,400 nulls = 3,910 non-null; 2021: 17,248 − 14,147 TFS = 3,101; 2024: 19,020 − 15,627 TFS = 3,393).

## Column Coverage

| Bronze Column | Gold Column | Status |
|---------------|------------|--------|
| #RPT_NAME (Era 1 only) | — | CORRECTLY EXCLUDED — constant `"7-12 Dropouts"`, hard-guarded by `_validate_era1_constants` |
| LONG_SCHOOL_YEAR | `year` | MAPPED — ending year parsed, cross-checked against filename |
| DETAIL_LVL_DESC | — (`detail_level`, dropped at export) | CORRECTLY EXCLUDED — drives file split + geography nulling, implicit in filename |
| SCHOOL_DSTRCT_CD | `district_code` | MAPPED — zfill(3), `ALL` sentinel → NULL |
| SCHOOL_DSTRCT_NM | — | CORRECTLY EXCLUDED — dimension attribute (districts dim) |
| INSTN_NUMBER | `school_code` | MAPPED — zfill(4), `ALL` sentinel → NULL |
| INSTN_NAME | — | CORRECTLY EXCLUDED — dimension attribute (schools dim) |
| GRADES_SERVED_DESC | — | CORRECTLY EXCLUDED — institution metadata, topic already 7–12-scoped |
| LABEL_LVL_1_DESC | `demographic` | MAPPED — prefix-stripped, shared alias normalization |
| PROGRAM_TOTAL | `dropout_count` | MAPPED — Int64 via exact Float64 hop |
| PROGRAM_PERCENT | `dropout_rate` | MAPPED — Float64 ÷ 100 → 0–1 proportion |

No gold column lacks a bronze source (no fabrication). Rename coverage enforced by `_require_columns` against `REQUIRED_BRONZE_COLUMNS`.

## Value-Level Spot Checks

All traces MATCH. Bronze quoted verbatim from the named file.

**Extreme rows (4a):**

1. **Global max `dropout_count`** — `dropout_rate_7_12_2017.csv`: `('2016-17', 'State', 'ALL', 'ALL', …, '7-12 Drop Outs -ALL Students', '24061', '2.8')` → gold `{year: 2017, district_code: None, school_code: None, demographic: 'all', dropout_count: 24061, dropout_rate: 0.028}`. **MATCH**.
2. **Global max `dropout_rate`** — `dropout_rate_7_12_2012.csv`: `('2011-12', 'School', '625', '0209', 'Savannah Gateway to College', '7-12 Drop Outs -Black', '44', '93.6')` → gold `{2012, '625', '0209', 'black', 44, 0.936}`. **MATCH** — extreme-but-conceivable (alternative/Gateway-to-College program in Savannah-Chatham), preserved per §4b and covered by the contract's documented observed range 0.2–93.6.
3. **Global min `dropout_rate`** — `dropout_rate_7_12_2011.csv`: `('2010-11', 'District', '633' [Cobb County], …, 'ALL', '7-12 Drop Outs -Economically Disadvantaged', '39', '0.2')` → gold `{2011, '633', school_code: None, 'economically_disadvantaged', 39, 0.002}` (the only 0.002 row in 2011). **MATCH** — implies ~19.5k ED 7–12 enrollment, plausible for Cobb (Georgia's 2nd-largest district).
4. **Min `dropout_count` (=10, threshold)** — `dropout_rate_7_12_2015.csv`: `('2014-15', 'School', '657', '0111', 'Model High', '7-12 Drop Outs -Economically Disadvantaged', '10', '3.2')` → gold `{2015, '657', '0111', 'economically_disadvantaged', 10, 0.032}`. **MATCH**.

**Ordinary traces (4b), one per era:**

5. **Era 2 (2022)** — Harlem High School: bronze `{'636', '0183', '7-12 Drop Outs -ALL Students', '27', '2.2'}` → gold `{2022, '636', '0183', 'all', 27, 0.022}`. **MATCH**.
6. **Era 1 (2024)** — Redan Middle School: bronze `{'644', '0205', '7-12 Drop Outs -Black', '20', '4.7'}` → gold `{2024, '644', '0205', 'black', 20, 0.047}`. **MATCH**.
7. **Era 2 early (2011), district level** — Clayton County: bronze `{'District', '631', INSTN_NUMBER='ALL', '7-12 Drop Outs -Male', '562', '4.4'}` → gold `{2011, '631', school_code: None, 'male', 562, 0.044}`. **MATCH** (sentinel → NULL confirmed).

**Suppression traces (4f), one per marker type:**

8. **Blank-cell era (2011)** — Sandy Creek High `656/0192` Migrant: bronze `PROGRAM_TOTAL=None, PROGRAM_PERCENT=None` → gold `dropout_count=None, dropout_rate=None`. **MATCH**.
9. **TFS era (2024)** — Walnut Grove High `747/0111` Black: bronze `PROGRAM_TOTAL='TFS', PROGRAM_PERCENT='TFS'` → gold both NULL. **MATCH**.

**2022 reclassification trace (manifest `reclassified`: 28 rows):** bronze 2022 has exactly 28 rows with `DETAIL_LVL_DESC='School'` AND `INSTN_NUMBER='ALL'` — 14 for `7830627` (Atlanta SMART Academy) + 14 for `7830636` (Northwest Classical Academy), all TFS-suppressed, e.g. `('School', '7830636', 'ALL', '7-12 Drop Outs -ALL Students', 'TFS', 'TFS')`. Bronze has **zero** genuine District rows for those codes in 2022 (no collision possible) and 2023 publishes 30 District rows for the same codes (convention restored, 15 demographics × 2). Gold 2022 `districts.parquet` carries all 28 as district rows with `school_code` NULL and both metrics NULL; the 14 genuine school rows (Atlanta SMART Academy school `0627`) remain in `schools.parquet`. **MATCH — repair verified end to end.**

**Year attribution (4c):** the only year-bearing parsing is `parse_school_year(LONG_SCHOOL_YEAR)` hard-cross-checked against `extract_year_from_filename` (raises on disagreement). `_2011.csv` carries the single value `'2010-11'` → gold `year=2011` partition has exactly 17,310 rows. **PASS** — no sentinel-year risk.

**Aggregate-row feasibility screen (4d 

— aggregates COME FROM BRONZE):** executed over all years:
- 14,137 (year, district, demographic) groups with a published district count and school rows: **0** violations of `district_count < max(school_count)`; **0** violations of `district_count < sum(visible school counts)`.
- **0** suppressed district cells coexisting with a published school row ≥ 10 (would be impossible, since a district cell ≥ any of its school cells).
- State level: **0** violations of `state_count < sum(visible district counts)` or `< max(district)`.
- Coverage sanity: visible school sums reach at most 100.0% of the district count (median 89.2%) and visible district sums at most 99.5% of state — undershoot only, exactly the signature expected from ~78–83% school-row suppression. No impossibly-low aggregates anywhere.

**Dedup tie-break (4e):** N/A — `files_processed` shows 14 files mapping to 14 distinct years (no overlap), per-file grain unique, and bronze=gold row counts prove dedup removed zero rows.

## Validation Cross-Read

- `_validation.json`: **passed=true, 21 pass / 0 fail / 0 warning**, including `contract_parquet_schema` (42 files), `contract_quality_sql` (all 10 checks), `grain_uniqueness` (year, district_code, school_code, demographic), and `foreign_keys` (242 district keys, 1,191 school keys, 15 demographic keys all resolve).
- `schema_hash`: `3fc2466c7ccb0dbe743f50879e78d5cf39c1f6c2494810b608855754f0551466`.
- **§4b masking audit**: PASS — no `_null_*` helpers in transform.py, no `masked_values` section in the manifest, and the docstring's full-bronze-scan claim is consistent with observed bounds (`PROGRAM_TOTAL` ∈ [10, 24061]; `PROGRAM_PERCENT` ∈ [0.2, 93.6]); manifest metric mins/maxes confirm (min count 10 every year; max rate 0.936).
- **§15b coverage judgment**: six authored cross-column checks (co-suppression, state-never-suppressed, count ≥ 10 threshold, race partition, gender partition, english_learners 2020–2022 absence) plus auto-derived range/enum checks. **Gap**: the economic and disability partitions also hold exactly in all 14 years but are unpinned — see Fix 1.
- **v1 parity (5d)**, output verbatim:

  ```
  MATCH — byte-identical with v1 gold
  ```

## Cross-Era Consistency

- **Overlap years**: none — every year comes from exactly one file (manifest `files_processed`); era split is 2011–2022 = era_2, 2023–2024 = era_1.
- **Era-boundary continuity**: state-level `dropout_count` mean moves 8,223 (2022) → 7,678 (2023) and `dropout_rate` mean 0.0275 → 0.0259 across the era_2/era_1 boundary — smooth, no scale jump anywhere (count means range 6,175–8,223; rate means 0.0205–0.0297 across all 14 years).
- **Cross-year NULL sweep**: clean — no column ~100% NULL in any subset of years; metric NULL rates 76.9–83.3% are uniform and tie exactly to bronze suppression counts.

## Transform Logic Risks

| Risk | Severity | Details |
|------|----------|---------|
| Silent column drops | PASS | `_require_columns` guards all 7 required bronze columns per file; excluded columns each justified (constant / dimension / metadata) |
| Era routing correctness | PASS | Most-specific-first signatures (`era_1` carries `#RPT_NAME`); manifest confirms 2023–2024 = era_1, 2011–2022 = era_2; Era 1 constant guard active |
| Filter logic | PASS | No row filters; `filtered=0` every year, bronze=gold totals |
| Normalization map completeness | PASS | 15/15 documented labels mapped via shared `DEMOGRAPHIC_ALIASES`; `unmapped_count=0`; manifest records the effective alias slice |
| `strict=False` casts | PASS | Used only after read-time suppression nulling (TFS/blank → NULL in `read_bronze_file`); non-null counts tie exactly to bronze suppression counts in every year, so nothing real was silently nulled; the ≥10 threshold + co-suppression checks would catch residue |
| Dedup keys + tie-break | PASS | Natural-key collision guard (with `detail_level`) runs BEFORE dedup; no overlap years; zero rows removed (250,292 in = 250,292 out) |
| Year extraction | PASS | `LONG_SCHOOL_YEAR` (single value per file, enforced) cross-checked against filename year; mismatch raises |
| §4b masking (5b) | PASS | No masks exist; none needed (no impossible values in any bronze file) |

## Required Fixes

### Fix 1: Author quality checks for the economic and disability state partition sums
- **Severity**: MEDIUM
- **Issue**: The contract pins the race and gender partition sums (`state_race_partition_sums_to_all`, `state_gender_partition_sums_to_all`) but not the two other exactly-holding demographic partitions. Verified against gold: at the state level, `economically_disadvantaged + not_economically_disadvantaged = all` and `students_with_disabilities + students_without_disabilities = all` hold **exactly in all 14 years** (2011–2024). Per §15b, an un-authored invariant is unenforced forever — a future re-publish that breaks either partition (e.g., an "unknown status" bucket appearing) would ship silently.
- **Evidence**: Executed partition test on gold state rows: `economic partition: exact in all years`; `disability partition: exact in all years` (e.g., 2024: ED+notED = 20,203 = `all`; SWD+SWOD = 20,203 = `all`). Contract `quality` list contains only the race and gender variants.
- **Location**: `_emit_contract_and_readme()` in `src/etl/education/gosa/dropout_rate_7_12/transform.py` (the `quality_checks` list).
- **Suggested fix**: Add two checks mirroring `state_gender_partition_sums_to_all` — `state_economic_partition_sums_to_all` over `('economically_disadvantaged', 'not_economically_disadvantaged')` and `state_disability_partition_sums_to_all` over `('students_with_disabilities', 'students_without_disabilities')` — and re-run the transform. Contract-only change: gold parquet bytes are untouched, so v1 parity remains MATCH.

## Notes

- `schema_hash`: `3fc2466c7ccb0dbe743f50879e78d5cf39c1f6c2494810b608855754f0551466`; contract `version` 1.0.0 (no schema change vs v1).
- Validation: 21 pass / 0 fail / 0 warning; 10/10 contract quality SQL checks pass.
- v1 parity: **MATCH — byte-identical with v1 gold** (v1 also produced 250,292 rows; identical hashes mean every value, NULL, and row order reproduced exactly).
- Read loss: 0 events across 14 files.
- The two extreme rates (Savannah Gateway to College 93.6% Black in 2012; Cobb ED 0.2% in 2011) are bronze-real, conceivable, and inside the contract's documented observed range — preserved per §4b, no action.
- Caveat for consumers (already in contract limitations): with ~78–83% school-row suppression, school-level subgroup sums legitimately undershoot district/state aggregates; use the published district/state rows for official totals.
