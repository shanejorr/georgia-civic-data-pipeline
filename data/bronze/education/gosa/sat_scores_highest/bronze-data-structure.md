# sat_scores_highest — Bronze Data Structure

## Overview

- Topic: sat_scores_highest
- Source: gosa
- Files: 22 files spanning 2004–2024 (21 publication years; 2016 published in two complementary files covering the old-SAT and redesigned-SAT test components side-by-side during the redesign year)
- Unreadable files: none (2005 and 2006 are `.csv`-extension wrappers that are actually XLS binary workbooks — readable with `xlrd`)
- Year representation: filename year is the publication year; from 2011 onward, an in-file `LONG_SCHOOL_YEAR` column holds the school-year string (e.g., `2023-24`). 2004–2010 files have no year column — only the filename conveys the year.
- Filename-to-data year offset: **filename year = spring of the school year's ending year**. For 2011+ files, `LONG_SCHOOL_YEAR` like `2010-11` accompanies `sat_scores_highest_2011.csv`, and `2023-24` accompanies `sat_scores_highest_2024.csv`. No offset — filename year always equals the ending calendar year of the school year.
- Detail levels: state (via `STATE_*` columns), district (via `DSTRCT_*` columns or `:ALL` sentinels), school (via `INSTN_*` columns or explicit school rows). Eras 1–3 encode detail levels via the `SysSchoolID` pattern (`district:ALL` vs `district:school`); Eras 4–5 encode them via separate fact-table columns, one row per (district, school, test) and report district/state context on every row via `DSTRCT_*` and `STATE_*` columns. Era 5 adds NATIONAL context via `NATIONAL_*` columns.
- Percentage scale: n/a — all metrics are raw SAT score points (old-SAT 200–800 per section / 600–2400 V+M+W composite; redesigned-SAT 200–800 per section / 400–1600 Combined; Essay sub-scores 2–8, Essay Total 6–24) or counts of tested students. No percent columns in any era.
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| sat_scores_highest_2004.csv | 2576f477ef0c786ab1f39ad2577e9ae46bc6c758125066e532e7b38a2f95808f |
| sat_scores_highest_2005.csv | 20a9a519652d1996d199568134af7b355a788a30fb435f9ef83ca56a2fdc958c |
| sat_scores_highest_2006.csv | 8c53e6e372c0b3b3a2b9ffdf355ad180d6d5cbeb1b9ce302ffcf23d930ff4563 |
| sat_scores_highest_2007.xls | a31f304cc641a5cc45fb0d4eb8ac9ff9ac8bb0108af2f1113ae5bce72766bc3f |
| sat_scores_highest_2008.xls | 680d70575e8eeebb1128d84ea87cd406c51a069a266be868ebf8f5947fb8781f |
| sat_scores_highest_2009.xls | 44a42fe11530a24659590d1481150a291b772ea58116b052313dd35cbae535c2 |
| sat_scores_highest_2010.xls | 82817c89f1cd9d4de3123eee0d01399ea24cee8f435a622c801a2e3903c5807c |
| sat_scores_highest_2011.csv | de1e625594866b725ff30428c870ddacf22763c9d927c6a2ac89788bc461de25 |
| sat_scores_highest_2012.csv | abfd620b15957c6130d563b0ae7a69eb5ffe990218518e87040671add25a3b92 |
| sat_scores_highest_2013.csv | c272be62c81f9bf38d6e2f41f2a91087a8d22a642390418bdcd2af3574875150 |
| sat_scores_highest_2014.csv | 1fec12bcf90711ed7bed76cbf3596f2f1553e8b4b89554ad4283b46adb270ec2 |
| sat_scores_highest_2015.csv | 0f42204f3367199149952c962e47a6da19f30b10f12b5133de41780ed291dc22 |
| sat_scores_highest_2016_new_format.csv | 050a7a1dc758a85d5160b71387dd1a1e78e7158341519c0e33aa5b28034c11bd |
| sat_scores_highest_2016_old_format.csv | c1472e50248895614527f21d5e1cf1d60bd5d2c4cac7d9a180ea6c68ef5658cd |
| sat_scores_highest_2017.csv | 7e2f64ab508b19c39de98b3f51eb91aaac58d2a10379856681694d13af760573 |
| sat_scores_highest_2018.csv | b437029364066f9d7a60154156af30d59a058b4448c56b360ac6f459f182ad05 |
| sat_scores_highest_2019.csv | e8f73e306d0913cc19e1ca0afafe2fba1278f4b734634a04e1dfc3f433af8337 |
| sat_scores_highest_2020.csv | b617758759e015f0f5efc9222b2d924b0bc23c2a353cec84d4f20c7b9d93bd29 |
| sat_scores_highest_2021.csv | 1aaae3ea362afda04a9b3b1126c37f6c5704c03485fc798c3fe02951f5fd2077 |
| sat_scores_highest_2022.csv | 36c7e5705fcc1e8c8c0b821e4ffce0d1798599c8b01cbcebfccb8103ef32b94a |
| sat_scores_highest_2023.csv | 98dbb0bdf9dffe06186635fe57d6cca2e4c2c90e374cf3aa358e3c415ea10605 |
| sat_scores_highest_2024.csv | 40b7eef93ef37cd2496f23abf1ffe52c43764d589a1ad76c7b73e9e1a57c60e1 |

## Excel Sheet Structure

| File(s) | Sheets | Notes |
|---------|--------|-------|
| sat_scores_highest_2005.csv | `SAT` (Data) | File has `.csv` extension but is actually an XLS binary workbook. Must be read with `xlrd` (not `polars.read_csv`, which fails with "invalid utf-8 sequence"). Single populated sheet. |
| sat_scores_highest_2006.csv | `Sheet1` (Data), `Sheet2` (empty), `Sheet3` (empty) | Same wrapper issue as 2005 — XLS disguised as `.csv`. Only `Sheet1` has rows. |
| sat_scores_highest_2007.xls | `Sheet1` (Data), `Sheet2` (empty), `Sheet3` (empty) | Only `Sheet1` has rows. Header is a single row (no sub-header). |
| sat_scores_highest_2008.xls | `Sheet1` (Data), `Sheet2` (empty), `Sheet3` (empty) | `Sheet1` has rows; row 0 is the column header, **row 1 is a secondary label row** (values like `"(Verbal+Math+Writing)"` and `"Verbal and Math"` that qualify columns 2–3). Data starts at row 2. |
| sat_scores_highest_2009.xls | `SAT` (Data), `Sheet2` (empty), `Sheet3` (empty) | Same header/sub-header pattern as 2008; data sheet is named `SAT`. |
| sat_scores_highest_2010.xls | `Sheet1` (Data), `Sheet2` (empty), `Sheet3` (empty) | Same header/sub-header pattern as 2008. |

No data is split across multiple sheets — every workbook has a single populated sheet. The transform must use `xlrd` to read all six Excel files (including the two `.csv`-extension binaries for 2005 and 2006) and must **skip the sub-header row** for 2008–2010.

## Summary

Per-school and per-district SAT score averages and test-taker counts for Georgia public high schools, reporting the highest recent score achieved by each student. Metrics across eras include old-SAT score averages (Total V+M / Verbal / Math / Writing V+M+W / Critical Reading, pre-2016) and redesigned-SAT metrics (2016+): Combined Test Score, Math Section Score, Reading Test Score, Writing-Language Test Score, Evidence-Based Reading and Writing, and four Essay sub-scores (Reading, Analysis, Writing, Total). Counts of students tested are reported at national, state, district, and school detail levels.

## Eras

### Era 1: 2004–2006 (wide format, verbose headers)

Files: `sat_scores_highest_2004.csv` (true CSV, latin-1 encoded, has quoted fields with embedded newlines), `sat_scores_highest_2005.csv` and `sat_scores_highest_2006.csv` (XLS binaries with `.csv` extension).

All three files share the same 72-column schema. Columns encode a measure-by-demographic matrix: measures = {Recent Total, Recent Verbal, Recent Math, High Total, High Verbal, High Math}, each × 10 demographics, plus Number Taken × 10 demographics = 72 columns total (plus `SysSchoolID` and `School Name`). Demographics = {All Students, Asian, Black, Female, Hispanic, Male, American Indian, O (Other), R (No Response), White}.

| Column | Description |
|--------|-------------|
| SysSchoolID | Composite `{district_code}:{school_code}` string; school-code is `ALL` for district-aggregated rows |
| School Name | District or school name |
| Recent Total All Students | Average SAT Total score (V+M) for most-recent attempt, all students |
| Recent Total {Asian,Black,Female,Hispanic,Male,American Indian,O,R,White} | Recent SAT Total average by demographic (O = Other, R = No Response) |
| Recent Verbal {...} | Recent SAT Verbal average, 10 demographics |
| Recent Math {...} | Recent SAT Math average, 10 demographics |
| High Total {...} | Highest-score SAT Total average, 10 demographics |
| High Verbal {...} | Highest-score SAT Verbal average, 10 demographics |
| High Verbal  Asian | **Header typo — two spaces between "Verbal" and "Asian"** (present in 2004, 2005, 2006) |
| High Math {...} | Highest-score SAT Math average, 10 demographics |
| Number Taken {All Students,Asian,Black,Female,Hispanic,Male,American Indian,O,R,White} | Count of students tested, by demographic |

#### Sample Data (2004)

```
shape: (5, 5)
┌─────────────┬───────────────────────────┬───────────────────────────┬────────────────────┬────────────────────┐
│ SysSchoolID │ School Name               │ Recent Total All Students │ Recent Total Asian │ Recent Total Black │
╞═════════════╪═══════════════════════════╪═══════════════════════════╪════════════════════╪════════════════════╡
│ 616:399     │ Portal Elementary School  │ (empty)                   │ (empty)            │ (empty)            │
│ 633:192     │ Harrison High School      │ 1054                      │ (empty)            │ 947                │
│ 793:173     │ J. R. Trippe Middle School│ (empty)                   │ (empty)            │ (empty)            │
│ 676:3056    │ Tucker Elementary School  │ (empty)                   │ (empty)            │ (empty)            │
│ 687:ALL     │ Laurens County            │ 884                       │ (empty)            │ 773                │
└─────────────┴───────────────────────────┴───────────────────────────┴────────────────────┴────────────────────┘
```

#### Statistics

- 2004: 2247 data rows (185 district-level `:ALL`, 2062 school-level). Many elementary/middle rows are blank across all metrics — only high schools have non-null scores.
- 2005: 536 data rows (178 district-level, 358 school-level).
- 2006: 542 data rows (178 district-level, 364 school-level).

Score metrics in 2004 range roughly 200–800 per section; V+M Totals range ~600–1600+.

#### Null Counts

All three years have 0 literal nulls in string identifier columns. Metric columns are mostly blank (empty string) rather than null — the transform should convert empty strings to null before casting. Populated rates vary by demographic: All Students ~519/2247 in 2004; rare demographics (American Indian, Asian in small districts) populated for only 5–80 rows.

#### Categorical Columns

None — there is no `SUBGRP_DESC` or `TEST_CMPNT_TYP_CD` column. Demographics and test components are encoded as separate columns in the wide layout.

#### Suppression Markers

2004, 2005, 2006: **no explicit suppression marker strings** in numeric columns — suppressed cells are simply left blank. Some demographic cells contain `0.0` which may represent "zero students tested in this demographic" rather than a real score; treat ambiguous `0.0` as null unless the paired `Number Taken{demographic}` is also 0 (legitimate zero).

### Era 2: 2007 (wide format, coded demographic suffixes)

File: `sat_scores_highest_2007.xls` (single file).

72 columns. Demographics are encoded as single-letter suffixes on measure names (e.g., `Recent Total0` = All Students, `Recent TotalA` = Asian). Adds subgroup `N` (American Indian / Native) that did not exist in Era 1. High Verbal and High Math retain the full demographic matrix (unlike Era 3 which drops it).

Column suffix decoding (consistent across Eras 2 and 3):
- `0` → All Students
- `A` → Asian
- `B` → Black
- `F` → Female
- `H` → Hispanic
- `M` → Male
- `N` → American Indian / Native
- `O` → Other
- `R` → No Response (2007 only; dropped in Era 3)
- `W` → White

| Column | Description |
|--------|-------------|
| SysSchoolID | Composite `{district_code}:{school_code}`; `:ALL` = district rollup |
| SchoolNme | School or district name (misspelling — missing `a`) |
| Recent Total{0,A,B,F,H,M,N,O,R,W} | Most-recent SAT Total average by demographic |
| Recent Verbal{0,A,B,F,H,M,N,O,R,W} | Most-recent SAT Verbal average by demographic |
| Recent Math{0,A,B,F,H,M,N,O,R,W} | Most-recent SAT Math average by demographic |
| High Total{0,A,B,F,H,M,N,O,R,W} | Highest-score SAT Total average by demographic |
| High Verbal{0,A,B,F,H,M,N,O,R,W} | Highest-score SAT Verbal average by demographic |
| High Math{0,A,B,F,H,M,N,O,R,W} | Highest-score SAT Math average by demographic |
| Number Taken{0,A,B,F,H,M,N,O,R,W} | Count of students tested by demographic |

#### Sample Data (2007)

```
shape: (5, 6)
┌─────────────┬─────────────────────────────┬───────────────┬───────────────┬───────────────┬───────────────┐
│ SysSchoolID │ SchoolNme                   │ Recent Total0 │ Recent TotalA │ Recent TotalB │ Recent TotalF │
╞═════════════╪═════════════════════════════╪═══════════════╪═══════════════╪═══════════════╪═══════════════╡
│ 740:3050    │ Treutlen Middle/High School │ 991.0         │ 0.0           │ 822.0         │ 962.0         │
│ 648:4050    │ Douglas County High School  │ 907.0         │ 942.0         │ 857.0         │ 886.0         │
│ 792:273     │ Valdosta High School        │ 969.0         │ 919.0         │ 878.0         │ 956.0         │
│ 716:2050    │ Hawkinsville High School    │ 924.0         │ 833.0         │ 846.0         │ 934.0         │
│ 736:ALL     │ Thomas County               │ 954.0         │ 1053.0        │ 845.0         │ 968.0         │
└─────────────┴─────────────────────────────┴───────────────┴───────────────┴───────────────┴───────────────┘
```

#### Statistics

- 2007: 543 data rows (177 district-level, 366 school-level).
- Scores roughly 400–1600 (old-SAT V+M Total scale).

#### Null Counts

All columns have 0 literal nulls, but many columns contain the literal string `"NULL"` as a value (see Categorical Columns / Suppression Markers). The transform must map `"NULL"` → null.

#### Categorical Columns

32 columns in 2007 are 100% populated with the literal string `"NULL"` — indicating no data collected at that detail level:
- `Recent TotalR`, `Recent VerbalR`, `Recent MathR` (R = No Response — not reported this year)
- `High TotalA`, `High TotalB`, `High TotalF`, `High TotalH`, `High TotalM`, `High TotalN`, `High TotalO`, `High TotalR`, `High TotalW`
- `High VerbalA`, `High VerbalB`, `High VerbalF`, `High VerbalH`, `High VerbalM`, `High VerbalN`, `High VerbalO`, `High VerbalR`, `High VerbalW`
- `High MathA`, `High MathB`, `High MathF`, `High MathH`, `High MathM`, `High MathN`, `High MathO`, `High MathR`, `High MathW`
- `Number TakenR`

Effectively, "High" metrics in 2007 are only reported for All Students (`0` suffix), and the "R" demographic is never reported.

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| (32 columns listed above) | `NULL` (literal string, 543 of 543 rows) |
| Demographic columns generally | `0.0` sometimes means "zero tested" — disambiguate using paired `Number Taken{demographic}` |

### Era 3: 2008–2010 (wide format, adds Writing, drops most High-score breakdowns)

Files: `sat_scores_highest_2008.xls`, `sat_scores_highest_2009.xls`, `sat_scores_highest_2010.xls`.

52 columns. Adds the `Writing` measure (SAT Writing section was active this era). Drops demographic breakdowns for High-score measures (keeps only `High Total0`, `High Verbal0`, `High Math0`, `High Writing0` — All Students only). Drops the `R` (No Response) demographic entirely. Adds a secondary header row at index 1 containing descriptive sub-labels like `"(Verbal+Math+Writing)"` for column `Recent Total` and `"Verbal and Math"` for column `Recent Total0` — **data starts at row index 2**.

Note: column `Recent Total` (without a demographic suffix) is the V+M+W composite score for All Students (max ~2400), while `Recent Total0` is the V+M score for All Students (max ~1600). These two columns are not redundant — they track different score totals on the old-SAT composite scales.

| Column | Description |
|--------|-------------|
| SysSchoolId | Composite `{district_code}:{school_code}`; `:ALL` = district rollup (note lowercase `d` vs Era 2's `D`) |
| School Name | School or district name |
| Recent Total | V+M+W composite average (max ~2400), All Students — sub-header row labels this "(Verbal+Math+Writing)" |
| Recent Total0 | V+M composite average (max ~1600), All Students — sub-header labels this "Verbal and Math" |
| Recent Total{A,B,F,H,M,N,O,W} | V+M+W composite, by demographic |
| Recent Verbal{0,A,B,F,H,M,N,O,W} | Verbal average by demographic |
| Recent Math{0,A,B,F,H,M,N,O,W} | Math average by demographic |
| Recent Writing{0,A,B,F,H,M,N,O,W} | Writing average by demographic |
| High Total0 | Highest V+M+W for All Students only |
| High Verbal0 | Highest Verbal for All Students only |
| High Math0 | Highest Math for All Students only |
| High Writing0 | Highest Writing for All Students only |
| Number Taken{0,A,B,F,H,M,N,O,W} | Count tested by demographic |

#### Sample Data (2009)

```
shape: (5, 8) — abridged to left columns
┌────────────┬─────────────────────────┬─────────────┬──────────────┬──────────────────┬──────────────────┬──────────────┬──────────────────┐
│ SysSchoolId│ School Name             │ Recent Total│ Recent Total0│ Recent TotalA    │ Recent TotalB    │ Recent TotalF│ Recent TotalH    │
╞════════════╪═════════════════════════╪═════════════╪══════════════╪══════════════════╪══════════════════╪══════════════╪══════════════════╡
│ 739:204    │ Towns County High School│ 1425.0      │ 951.0        │ Too Few Students │ Too Few Students │ 902.0        │ Too Few Students │
│ 648:4050   │ Douglas County HS       │ 1310.0      │ 881.0        │ Too Few Students │ 845.0            │ 875.0        │ Too Few Students │
│ 789:ALL    │ Thomasville City        │ 1317.0      │ 884.0        │ Too Few Students │ 805.0            │ 887.0        │ Too Few Students │
│ 715:5050   │ Cedartown High School   │ 1503.0      │ 1015.0       │ Too Few Students │ Too Few Students │ 1040.0       │ Too Few Students │
│ 735:ALL    │ Terrell County          │ 1111.0      │ 734.0        │ Too Few Students │ 741.0            │ 768.0        │ Too Few Students │
└────────────┴─────────────────────────┴─────────────┴──────────────┴──────────────────┴──────────────────┴──────────────┴──────────────────┘
```

#### Statistics

- 2008: 561 data rows (180 district-level, 381 school-level) — header row 0, sub-header row 1, data rows 2–562.
- 2009: 566 data rows (180 district-level, 386 school-level) — sheet named `SAT`, same header/sub-header layout.
- 2010: 581 data rows — same layout as 2008/2009.

#### Null Counts

All literal-null counts are 0 once the header and sub-header rows are skipped. The `"Too Few Students"` string marker below carries the null meaning.

#### Categorical Columns

None — same wide structure as Eras 1–2, no `SUBGRP_DESC` or test-component column.

#### Suppression Markers (2009 representative)

| Column | Non-Numeric Values |
|--------|-------------------|
| Recent Total0 / Verbal0 / Math0 / Writing0 | `Too Few Students` (19 rows each; numeric_pct ~0.97) |
| Recent Total{B,F,M,W} / Verbal{B,F,M,W} / Math{B,F,M,W} / Writing{B,F,M,W} | `Too Few Students` (50–161 rows; numeric_pct 0.72–0.91) |
| Recent TotalN / VerbalN / MathN / WritingN | `Too Few Students` (561 of 566 rows — Native demographic almost never reported) |
| High Total0 / Verbal0 / Math0 / Writing0 | `Too Few Students` (19 rows each) |
| Number Taken{0,A,…,W} | Often contains `Too Few Students` as suppression |

### Era 4: 2011–2022 (tidy format, old + new SAT test codes)

Files: `sat_scores_highest_2011.csv` through `sat_scores_highest_2022.csv`, plus both `sat_scores_highest_2016_old_format.csv` and `sat_scores_highest_2016_new_format.csv`. All share the same 14 columns.

This era is a complete redesign to **tidy format**: one row per (school, test-component) — district and state context are repeated on every row via dedicated columns rather than separate aggregate rows. `SUBGRP_DESC` is present but always `"All Students"` — **no demographic breakdown in this era**. Within the era, **2016 is the SAT redesign boundary**: the `_old_format.csv` file for 2015-16 carries old-SAT test codes (Reading / Mathematics / Writing / Combined), and `_new_format.csv` for 2015-16 plus every file 2017–2022 carries the redesigned-SAT test codes (Combined Test Score / Math Section Score / Reading Test Score / WritLang Test Score / Evidence Based Reading and Writing / four Essay sub-scores).

| Column | Description |
|--------|-------------|
| LONG_SCHOOL_YEAR | School year as `YYYY-YY` (e.g., `2014-15`); one value per file |
| SCHOOL_DISTRCT_CD | District code (note spelling: `DISTRCT`, not `DSTRCT`); 3-digit for normal districts, 7-digit for State Charter / State Schools |
| SCHOOL_DSTRCT_NM | District name |
| INSTN_NUMBER | School code (3–4 chars; zero-padded to 4 in 2020+) |
| INSTN_NAME | School name |
| SUBGRP_DESC | Always `"All Students"` — no demographics |
| TEST_CMPNT_TYP_CD | Test component (values differ between old/new SAT — see below) |
| NATIONAL_NUM_TESTED_CNT | Count of students tested nationally (same value across all rows in a file) |
| STATE_NUM_TESTED_CNT | Count of students tested in Georgia |
| DSTRCT_NUM_TESTED_CNT | Count of students tested in the district |
| INSTN_NUM_TESTED_CNT | Count of students tested at the school |
| STATE_AVG_SCORE_VAL | Georgia average score for the test component |
| DSTRCT_AVG_SCORE_VAL | District average score |
| INSTN_AVG_SCORE_VAL | School average score |

#### Sample Data (2015)

```
shape: (5, 10) — abridged to key columns
┌──────────────────┬───────────────────┬───────────────────┬──────────────┬───────────────────────────────┬──────────────┬───────────────────┬──────────────────────┬──────────────────────┬─────────────────────┐
│ LONG_SCHOOL_YEAR │ SCHOOL_DISTRCT_CD │ SCHOOL_DSTRCT_NM  │ INSTN_NUMBER │ INSTN_NAME                    │ SUBGRP_DESC  │ TEST_CMPNT_TYP_CD │ INSTN_NUM_TESTED_CNT │ STATE_AVG_SCORE_VAL  │ INSTN_AVG_SCORE_VAL │
╞══════════════════╪═══════════════════╪═══════════════════╪══════════════╪═══════════════════════════════╪══════════════╪═══════════════════╪══════════════════════╪══════════════════════╪═════════════════════╡
│ 2014-15          │ 738               │ Toombs County     │ 192          │ Toombs County High School     │ All Students │ Reading           │ 97                   │ 490                  │ 469                 │
│ 2014-15          │ 645               │ Dodge County      │ 103          │ Dodge County High School      │ All Students │ Reading           │ 148                  │ 490                  │ 460                 │
│ 2014-15          │ 784               │ Pelham City       │ 111          │ Pelham High School            │ All Students │ Mathematics       │ 30                   │ 489                  │ 452                 │
│ 2014-15          │ 709               │ Oglethorpe County │ 2050         │ Oglethorpe County High School │ All Students │ Reading           │ 115                  │ 490                  │ 501                 │
│ 2014-15          │ 731               │ Taliaferro County │ 102          │ Taliaferro County School      │ All Students │ Mathematics       │ 15                   │ 489                  │ 377                 │
└──────────────────┴───────────────────┴───────────────────┴──────────────┴───────────────────────────────┴──────────────┴───────────────────┴──────────────────────┴──────────────────────┴─────────────────────┘
```

#### Statistics

Row counts per file:
- 2011: 1724 | 2012: 1740 | 2013: 1716 | 2014: 1724 | 2015: 1756
- 2016_old_format: 1728 | 2016_new_format: 3611
- 2017: 3820 | 2018: 3816 | 2019: 3740 | 2020: 3276 | 2021: 3144 | 2022: 2980

Row-count doubling between 2015 (1756) and 2016_new_format (3611) reflects that the redesigned SAT has 8–9 test components vs the old SAT's 4. Score range from 2015 `STATE_AVG_SCORE_VAL`: min 373, max 1352, mean 676 (Combined Test Score pulls the mean up).

#### Null Counts

2015 representative:
- `LONG_SCHOOL_YEAR`, `SCHOOL_DISTRCT_CD`, `SCHOOL_DSTRCT_NM`, `INSTN_NUMBER`, `INSTN_NAME`, `SUBGRP_DESC`, `TEST_CMPNT_TYP_CD`, `NATIONAL_NUM_TESTED_CNT`, `STATE_NUM_TESTED_CNT`, `DSTRCT_NUM_TESTED_CNT`, `INSTN_NUM_TESTED_CNT`, `STATE_AVG_SCORE_VAL` — 0 literal nulls.
- `DSTRCT_AVG_SCORE_VAL` — 8 literal nulls.
- `INSTN_AVG_SCORE_VAL` — 131 literal nulls.

Along with `TFS` suppression markers (see below), null counts represent schools / districts with no reported average.

#### Categorical Columns

| Column | Distinct Values (old-SAT years 2011–2016_old) |
|--------|------------------------------------------------|
| LONG_SCHOOL_YEAR | Single value per file (e.g., `2014-15`) |
| SUBGRP_DESC | `All Students` (only value) |
| TEST_CMPNT_TYP_CD | `Combined`, `Reading`, `Mathematics`, `Writing` (4 values) |

| Column | Distinct Values (new-SAT years 2016_new–2022) |
|--------|------------------------------------------------|
| LONG_SCHOOL_YEAR | Single value per file |
| SUBGRP_DESC | `All Students` (only value) |
| TEST_CMPNT_TYP_CD | `Combined Test Score`, `Math Section Score - New`, `Reading Test  Score - New` (double space), `WritLang Test  Score - New` (double space), `Essay Analysis Score - New`, `Essay Reading Score - New`, `Essay Writing Score - New`, `Essay Total`, and (2016–2019 only) `Evidence Based Reading and Writing - New` (9 values; 2020–2022 drop the EBRW row → 8 values) |

Two `TEST_CMPNT_TYP_CD` values have **double spaces** between "Test" and "Score": `Reading Test  Score - New` and `WritLang Test  Score - New`. Preserve on lookup and normalize to single-space when recoding to tidy gold names.

#### Suppression Markers (2015 representative)

| Column | Non-Numeric Values |
|--------|-------------------|
| DSTRCT_NUM_TESTED_CNT | `TFS` (8 rows) |
| INSTN_NUM_TESTED_CNT | `TFS` (131 rows) |
| DSTRCT_AVG_SCORE_VAL | none in 2015 |
| INSTN_AVG_SCORE_VAL | none in 2015 (suppressed rows are literal null) |

The 2011 and 2018 files also contain `TFS` in numeric count columns (a polars parse failure occurs on default-typed read of 2011 and 2018 because of the `TFS` strings — must use `infer_schema_length=0` or explicit string schema, then cast with `strict=False`). Treat `TFS` (abbreviation of "Too Few Students") as the universal suppression marker across Era 4 — convert to null in numeric metric and count columns.

### Era 5: 2023–2024 (tidy format, adds assessment / indicator / national-avg columns)

Files: `sat_scores_highest_2023.csv`, `sat_scores_highest_2024.csv`.

17 columns — adds three new columns over Era 4 and **renames** `SCHOOL_DISTRCT_CD` (Era 4 spelling with `I`) to `SCHOOL_DSTRCT_CD` (Era 5 spelling, matches the abbreviation used in `SCHOOL_DSTRCT_NM`). This is a **breaking column rename** between Era 4 and Era 5.

| Column | Description |
|--------|-------------|
| #ASSMT_CD | Assessment code — always `SAT` (new; the leading `#` is a literal header character, probably indicating a legacy comment marker that leaked into the real header) |
| HIGHEST_RECENT_IND | Highest-vs-recent indicator — always `Highest` (new; redundant with the topic name) |
| LONG_SCHOOL_YEAR | School year as `YYYY-YY` |
| SCHOOL_DSTRCT_CD | District code — **renamed from `SCHOOL_DISTRCT_CD` in Era 4** |
| SCHOOL_DSTRCT_NM | District name |
| INSTN_NUMBER | School code (4 chars, zero-padded) |
| INSTN_NAME | School name |
| SUBGRP_DESC | Always `All Students` |
| TEST_CMPNT_TYP_CD | Test component (same 8-value new-SAT vocabulary as Era 4 2020–2022) |
| NATIONAL_NUM_TESTED_CNT | Nationwide tested count (in 2024 recorded as `"1973891."` with trailing period) |
| STATE_NUM_TESTED_CNT | Georgia tested count |
| DSTRCT_NUM_TESTED_CNT | District tested count |
| INSTN_NUM_TESTED_CNT | School tested count |
| NATIONAL_AVG_SCORE_VAL | **NEW** — national average for the test component; `"N/A"` for Reading Test Score and WritLang Test Score (College Board does not publish a national average for these sub-components) |
| STATE_AVG_SCORE_VAL | Georgia average score |
| DSTRCT_AVG_SCORE_VAL | District average score |
| INSTN_AVG_SCORE_VAL | School average score |

#### Sample Data (2024)

```
shape: (5, 10) — abridged to left columns
┌───────────┬────────────────────┬──────────────────┬──────────────────┬─────────────────────────────────┬──────────────┬───────────────────────────────────────┬──────────────┬────────────────────────────┬─────────────────────────┐
│ #ASSMT_CD │ HIGHEST_RECENT_IND │ LONG_SCHOOL_YEAR │ SCHOOL_DSTRCT_CD │ SCHOOL_DSTRCT_NM                │ INSTN_NUMBER │ INSTN_NAME                            │ SUBGRP_DESC  │ TEST_CMPNT_TYP_CD          │ NATIONAL_NUM_TESTED_CNT │
╞═══════════╪════════════════════╪══════════════════╪══════════════════╪═════════════════════════════════╪══════════════╪═══════════════════════════════════════╪══════════════╪════════════════════════════╪═════════════════════════╡
│ SAT       │ Highest            │ 2023-24          │ 729              │ Sumter County                   │ 0397         │ Sumter County High School             │ All Students │ Combined Test Score        │ 1973891.                │
│ SAT       │ Highest            │ 2023-24          │ 645              │ Dodge County                    │ 0103         │ Dodge County High School              │ All Students │ Math Section Score - New   │ 1973891.                │
│ SAT       │ Highest            │ 2023-24          │ 7830634          │ State Charter Schools II- Fug…  │ 0634         │ Georgia Fugees Academy Charter School │ All Students │ WritLang Test  Score - New │ 1973891.                │
│ SAT       │ Highest            │ 2023-24          │ 706              │ Muscogee County                 │ 0278         │ Shaw High School                      │ All Students │ WritLang Test  Score - New │ 1973891.                │
│ SAT       │ Highest            │ 2023-24          │ 722              │ Rockdale County                 │ 3052         │ Rockdale County High School           │ All Students │ Combined Test Score        │ 1973891.                │
└───────────┴────────────────────┴──────────────────┴──────────────────┴─────────────────────────────────┴──────────────┴───────────────────────────────────────┴──────────────┴────────────────────────────┴─────────────────────────┘
```

#### Statistics

- 2023: 2204 rows.
- 2024: 1866 rows.

Score ranges in 2024:
- Combined Test Score: state avg 505.4; district avg 192–1162; school avg 782–1347.
- Math Section Score: state avg 505.4; school avg 383–681.
- WritLang Test Score / Reading Test Score: state avg 266 / 272; school avg ~192–335 / ~208–331.
- Essay sub-scores (Reading / Analysis / Writing): state avg 4.5 / 3.5 / 5.4 (2–8 scale).
- Essay Total: state avg 13.3 (6–24 scale).

#### Null Counts

2024: 0 literal nulls across all 17 columns — suppression is via the string markers below (`TFS`, `N/A`).

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| #ASSMT_CD | `SAT` (only value) |
| HIGHEST_RECENT_IND | `Highest` (only value) |
| LONG_SCHOOL_YEAR | Single value per file (`2022-23`, `2023-24`) |
| SUBGRP_DESC | `All Students` (only value) |
| TEST_CMPNT_TYP_CD | 8 values (same new-SAT vocabulary as Era 4 2020–2022): `Combined Test Score`, `Math Section Score - New`, `Reading Test  Score - New` (double space), `WritLang Test  Score - New` (double space), `Essay Analysis Score - New`, `Essay Reading Score - New`, `Essay Writing Score - New`, `Essay Total` |

#### Suppression Markers (2024)

| Column | Non-Numeric Values |
|--------|-------------------|
| DSTRCT_NUM_TESTED_CNT | `TFS` (201 rows; ~11% suppressed) |
| INSTN_NUM_TESTED_CNT | `TFS` (350 rows; ~19% suppressed) |
| DSTRCT_AVG_SCORE_VAL | `TFS` (201 rows) |
| INSTN_AVG_SCORE_VAL | `TFS` (350 rows) |
| NATIONAL_AVG_SCORE_VAL | `N/A` (870 rows — specifically all `Reading Test Score - New` and `WritLang Test Score - New` rows, for which College Board does not publish a national average) |
| NATIONAL_NUM_TESTED_CNT | All rows in 2024 contain `"1973891."` with trailing period — strip before casting |

## ETL Considerations

1. **Four distinct file readers needed.**
   - CSV: 2004, 2011–2024 (including both 2016 files). 2004 needs `encoding='latin-1'` and quote / embedded-newline handling (the polars CSV parser chokes on the embedded newlines; use Python `csv` module or pass `infer_schema_length=0` with careful quote handling).
   - XLS via `xlrd`: 2007 (`Sheet1`), 2008 (`Sheet1`, skip row 1 sub-header), 2009 (`SAT`, skip row 1), 2010 (`Sheet1`, skip row 1).
   - XLS via `xlrd` but with `.csv` extension: **2005 (`SAT` sheet) and 2006 (`Sheet1`)** — the files are binary Excel workbooks mis-named with `.csv`. `polars.read_csv` fails with "invalid utf-8 sequence". Detect by file magic (`D0 CF 11 E0`) or special-case these two filenames.

2. **Breaking column rename in Era 5.** `SCHOOL_DISTRCT_CD` (Era 4, with `I`) becomes `SCHOOL_DSTRCT_CD` (Era 5, without `I`) in 2023. The district-name column is `SCHOOL_DSTRCT_NM` in both eras. Transform must standardize to a single canonical gold column name (e.g., `district_code`) and select from whichever bronze column is present.

3. **Year representation inconsistency.** Eras 1–3 have **no in-file year column** — the year must be inferred from the filename. Eras 4–5 have `LONG_SCHOOL_YEAR` in `YYYY-YY` format; extract the ending year (e.g., `2023-24` → data year `2024`).

4. **Suppression markers differ across eras.**
   - Era 1 (2004–2006): blank cells only (implicit null).
   - Era 2 (2007): literal string `"NULL"` plus `0.0` (which may be ambiguous).
   - Era 3 (2008–2010): literal string `"Too Few Students"` (spelled out in full).
   - Era 4–5: `"TFS"` abbreviation in count / avg columns; `"N/A"` in `NATIONAL_AVG_SCORE_VAL` for Reading and WritLang sub-scores in Era 5.
   - Use `strict=False` when casting via polars, and normalize all four forms to null in a single pre-processing step.

5. **Wide-to-long transformation required for Eras 1–3.** The gold target is tidy (one row per (year, district, school, test_component, demographic)). The 52–72 wide columns in Eras 1–3 encode two orthogonal axes (measure × demographic) that must be unpivoted. The measure axis for Eras 1–3 is {Total, Verbal, Math, Writing (Era 3 only), Number Taken}, further split by "Recent" vs "High".

6. **Demographic encoding in Eras 1–3 is lost in Eras 4–5.** Eras 1–3 include demographic breakdowns (All, Asian, Black, Female, Hispanic, Male, Native/American Indian, Other, No Response, White); Eras 4–5 do **not** (only `All Students`). Gold must decide whether to keep only `All Students` (consistent across all years) or include demographic rows where available. Recommended: include demographic breakdown where available — downstream queries for `demographic = 'all_students'` will still work across all years.

7. **Detail-level encoding varies.**
   - Eras 1–3: single `SysSchoolID` / `SysSchoolId` column like `"601:103"` (school row) or `"601:ALL"` (district-rollup row). Split on `:` → district_code + school_code; if school_code == `"ALL"`, it's a district rollup with null school_code.
   - Eras 4–5: separate `SCHOOL_DSTRCT_CD` + `INSTN_NUMBER` columns. Each row is a school-level record that additionally reports its parent district's, state's, and (Era 5) nation's averages in `DSTRCT_*`, `STATE_*`, and `NATIONAL_*` columns. To build a tidy fact table, either (a) emit three or four rows per input row — one at each detail level — or (b) only emit the school-level row and let downstream aggregates re-derive district/state totals. Recommendation: emit multiple rows at different detail levels to preserve the source's pre-computed aggregates.

8. **District-code format.** Most districts are 3-digit codes (`601`–`793`). State Charter Schools / State Schools are encoded as 7-digit composite codes (e.g., `7991894` = State Schools: Georgia Academy for the Blind; `7820108` = State Charter Schools: Mountain Education Center). Preserve as strings to avoid losing leading zeros or truncating the 7-digit codes.

9. **School-code format changes in 2020.** 2011–2019 files sometimes have 3-char school codes (`100`, `102`), sometimes 4-char (`1050`, `2050`). Starting 2020, the school code is consistently zero-padded to 4 chars (`0100`, `0497`). Pad to 4 chars in gold for consistency.

10. **Header typos to preserve-and-normalize.**
    - `High Verbal  Asian` (double space) in 2004, 2005, 2006.
    - `Reading Test  Score - New` (double space) and `WritLang Test  Score - New` (double space) in 2016_new_format and 2017–2024.
    - `SchoolNme` (missing `a`) in 2007 vs `School Name` in 2004–2006 / 2008–2010.
    - `SysSchoolID` (Eras 1–2, capital `D`) vs `SysSchoolId` (Era 3, lowercase `d`).
    - Match on exact strings when filtering/joining bronze; normalize to a single canonical tidy name in gold (e.g., `reading_score`, `writing_language_score`).

11. **Secondary-header row skip (Era 3).** 2008, 2009, and 2010 have a second non-data row at index 1 with annotations like `"(Verbal+Math+Writing)"` and `"Verbal and Math"`. When reading with `xlrd`, read data starting at `row_index=2`. Polars' `read_excel` (calamine engine) does not support `.xls`, so `xlrd` is required.

12. **Old-SAT vs redesigned-SAT test codes.** 2016 is a transition year with two files: `sat_scores_highest_2016_old_format.csv` (old codes: Reading / Mathematics / Writing / Combined) and `sat_scores_highest_2016_new_format.csv` (new codes). Both are valid data and both should be included in gold for 2015-16. After 2016, only new-SAT codes are used. The gold schema should reconcile both vocabularies into a canonical `test_component` value (e.g., `reading`, `math`, `writing_language`, `essay_reading`, `essay_analysis`, `essay_writing`, `essay_total`, `evidence_based_reading_writing`, `math_section`, `reading_test`, `combined`).

13. **`NATIONAL_*` columns are not available pre-2023 for averages.** Eras 1–3 have no national-level context; Era 4 has `NATIONAL_NUM_TESTED_CNT` (a single national count per file) but not `NATIONAL_AVG_SCORE_VAL`; Era 5 has both. The gold schema should permit nulls for national metrics in earlier years.

14. **`NATIONAL_NUM_TESTED_CNT` formatting in Era 5.** Values in 2024 include a trailing period (`"1973891."`). Strip the period before numeric cast, or verify that `cast(pl.Float64, strict=False)` handles this correctly on the installed polars version.

15. **Essay score scale vs section score scale.** Essay sub-scores (Reading, Analysis, Writing) use a 2–8 scale; Essay Total uses a 6–24 scale; Math Section / Reading Test / WritLang Test use a 200–800 scale; Combined Test Score uses 400–1600. These are not mutually comparable — the gold fact table should keep the per-component scale as-is, and downstream consumers should be aware.

16. **"Recent" vs "Highest" distinction in Eras 1–3.** The columns `Recent Total/Verbal/Math/Writing` report the most-recent test attempt's average; `High Total/Verbal/Math/Writing` reports the highest single attempt. The topic is `sat_scores_highest`, so the gold metric should be the `High` variant. However, Era 3 `High {Total,Verbal,Math,Writing}0` is the only highest-score column with any data (the demographic-split `High` columns exist only in Eras 1–2). Gold should filter to `High` columns for this topic and drop or ignore `Recent*`.

17. **Suppressed `0.0` values in Eras 1–2.** Some demographic cells in 2004–2007 contain the literal `0.0` — these may represent "zero students in this demographic" rather than a real zero score. Only treat `0.0` as a real score if the paired `Number Taken{demographic}` is non-zero; otherwise convert to null during transform.

## Gold Schema Classification

For each bronze column (across all eras), classify its role in the gold star schema:

| Bronze Column | Era(s) | Gold Role | Gold Name | Notes |
|---------------|--------|-----------|-----------|-------|
| SysSchoolID / SysSchoolId | 1, 2, 3 | fact_key (split) | district_code + school_code | Split on `:`; `ALL` → school_code is null (district rollup) |
| SCHOOL_DISTRCT_CD / SCHOOL_DSTRCT_CD | 4, 5 | fact_key | district_code | FK to districts dimension; preserve as string (3 or 7 chars) |
| INSTN_NUMBER | 4, 5 | fact_key | school_code | FK to schools dimension; zero-pad to 4 chars |
| SCHOOL_DSTRCT_NM | 4, 5 | dimension_attribute | — | `district_name` in districts dimension (latest-value policy) |
| INSTN_NAME | 4, 5 | dimension_attribute | — | `school_name` in schools dimension |
| School Name / SchoolNme | 1, 2, 3 | dimension_attribute | — | `school_name` when row is school-level; `district_name` when `SysSchoolID` ends in `:ALL` |
| LONG_SCHOOL_YEAR | 4, 5 | fact_key | year | Extract ending year (e.g., `2023-24` → 2024); gold year = calendar year of spring term |
| (filename year) | 1, 2, 3 | fact_key | year | Parse from filename `sat_scores_highest_{YYYY}.{ext}` |
| SUBGRP_DESC | 4, 5 | fact_key | demographic | Always `All Students` in these eras — still include as FK to demographics dimension for uniformity |
| (demographic suffix `0/A/B/F/H/M/N/O/R/W` in wide columns) | 1, 2, 3 | fact_key | demographic | Derive from the column name during unpivot; map `0→all_students`, `A→asian`, `B→black`, `F→female`, `H→hispanic`, `M→male`, `N→american_indian`, `O→other`, `R→no_response`, `W→white` |
| TEST_CMPNT_TYP_CD | 4, 5 | fact_categorical | test_component | Normalize old-SAT and new-SAT codes to canonical tidy names (e.g., `reading`, `mathematics`, `writing_language`, `combined`, `math_section`, `reading_test`, `evidence_based_reading_writing`, `essay_reading`, `essay_analysis`, `essay_writing`, `essay_total`); collapse the double-space typos to single space |
| (measure prefix `Recent / High` + `Total / Verbal / Math / Writing` from wide columns) | 1, 2, 3 | fact_categorical | test_component | Derive during unpivot; gold should use `High*` columns as the primary metric for this topic |
| INSTN_AVG_SCORE_VAL | 4, 5 | fact_metric | avg_score (school detail level) | Numeric; preserve decimal places; suppress `TFS` → null |
| DSTRCT_AVG_SCORE_VAL | 4, 5 | fact_metric | avg_score (district detail level) | Either emit as a separate row at district detail level or keep as a secondary column; `TFS` → null |
| STATE_AVG_SCORE_VAL | 4, 5 | fact_metric | avg_score (state detail level) | Single value per file/test_component; emit as state-detail row |
| NATIONAL_AVG_SCORE_VAL | 5 | fact_metric | avg_score (national detail level) | `N/A` → null for Reading/WritLang sub-scores; only available from 2023 onward |
| INSTN_NUM_TESTED_CNT | 4, 5 | fact_metric | num_tested (school) | Integer count; `TFS` → null |
| DSTRCT_NUM_TESTED_CNT | 4, 5 | fact_metric | num_tested (district) | Integer count; `TFS` → null |
| STATE_NUM_TESTED_CNT | 4, 5 | fact_metric | num_tested (state) | Integer count |
| NATIONAL_NUM_TESTED_CNT | 4, 5 | fact_metric | num_tested (national) | Strip trailing `.` in 2024 before cast |
| `Recent Total{0,A,B,F,H,M,N,O,R,W}` | 1, 2, 3 | fact_metric | avg_score (test_component=recent_total, demographic derived from suffix) | After unpivot; for Era 3, `Recent Total` (no suffix) is V+M+W composite max~2400 and `Recent Total0` is V+M only max~1600 — two distinct measures |
| `Recent Verbal{...}` | 1, 2, 3 | fact_metric | avg_score (test_component=recent_verbal) | After unpivot |
| `Recent Math{...}` | 1, 2, 3 | fact_metric | avg_score (test_component=recent_math) | After unpivot |
| `Recent Writing{...}` | 3 | fact_metric | avg_score (test_component=recent_writing) | After unpivot (Era 3 only) |
| `High Total{...}` / `High Total0` | 1, 2, 3 | fact_metric | avg_score (test_component=highest_total) | **Primary metric for this topic** |
| `High Verbal{...}` / `High Verbal0` | 1, 2, 3 | fact_metric | avg_score (test_component=highest_verbal) | Era 3 is All Students only |
| `High Math{...}` / `High Math0` | 1, 2, 3 | fact_metric | avg_score (test_component=highest_math) | Era 3 is All Students only |
| `High Writing0` | 3 | fact_metric | avg_score (test_component=highest_writing) | Era 3 only, All Students only |
| `Number Taken{0,A,B,F,H,M,N,O,R,W}` | 1, 2, 3 | fact_metric | num_tested | After unpivot; paired with the corresponding demographic |
| HIGHEST_RECENT_IND | 5 | not_in_gold | — | Constant `"Highest"` — redundant with topic name |
| #ASSMT_CD | 5 | not_in_gold | — | Constant `"SAT"` — redundant with topic name |
| (row-1 sub-header `"(Verbal+Math+Writing)"`, `"Verbal and Math"`) | 3 | not_in_gold | — | Header annotation, not data — skip when reading |
