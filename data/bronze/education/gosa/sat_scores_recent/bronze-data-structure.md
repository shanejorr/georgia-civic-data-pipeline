# sat_scores_recent — Bronze Data Structure

## Overview

- Topic: sat_scores_recent
- Source: gosa
- Files: 22 files spanning 2004–2024 (2016 ships in two formats: `_old_format` and `_new_format`)
- Unreadable files: none. **Beware file-extension mismatch**: `sat_scores_recent_2005.csv` and `sat_scores_recent_2006.csv` are actually Microsoft Excel `.xls` binaries (OLE Compound Document, magic `D0 CF 11 E0 A1 B1 1A E1`) with a `.csv` extension — they must be read with `pl.read_excel`, not a CSV reader. `sat_scores_recent_2004.csv` is a real CSV but contains at least one row whose unquoted comma inside `"Martin Luther King, Jr. Elementary School"` defeats Polars' CSV parser; fall back to Python's stdlib `csv.reader` (which handles the quoting correctly) and load the result into a Polars frame. Two rows at the end of the 2004 file have wrong field counts (48 and 11 fields instead of 72) and must be dropped.
- Year representation: Eras 1–3 (2004–2010) have **no** year column (year comes from the filename only). Eras 4–6 (2011–2024) have a `LONG_SCHOOL_YEAR` column formatted as `"YYYY-YY"` (e.g., `"2023-24"`).
- Filename-to-data year offset: filename year = **ending** calendar year of the school year (e.g., `sat_scores_recent_2024.csv` contains `LONG_SCHOOL_YEAR = "2023-24"`). Every row in every long-format file carries the same single school-year value, and that value always matches the filename year.
- Detail levels: Eras 1–3 (2004–2010) mix **state, district, and school** rows in one file (encoded in `SysSchoolID` / `SysSchoolId`). Eras 4–6 (2011–2024) contain **only school-level rows**; state/district/national values are carried as sibling columns on every school row (no separate aggregate rows).
- Percentage scale: not applicable — SAT section scores are reported on the 200–800 scale (pre-2016) or 200–800 per-section / 400–1600 combined (2016 onward), essay subscores on 2–8, and `*_NUM_TESTED_CNT` are counts. No percentage columns.
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| sat_scores_recent_2004.csv | 2576f477ef0c786ab1f39ad2577e9ae46bc6c758125066e532e7b38a2f95808f |
| sat_scores_recent_2005.csv | 20a9a519652d1996d199568134af7b355a788a30fb435f9ef83ca56a2fdc958c |
| sat_scores_recent_2006.csv | 8c53e6e372c0b3b3a2b9ffdf355ad180d6d5cbeb1b9ce302ffcf23d930ff4563 |
| sat_scores_recent_2007.xls | a31f304cc641a5cc45fb0d4eb8ac9ff9ac8bb0108af2f1113ae5bce72766bc3f |
| sat_scores_recent_2008.xls | 680d70575e8eeebb1128d84ea87cd406c51a069a266be868ebf8f5947fb8781f |
| sat_scores_recent_2009.xls | 44a42fe11530a24659590d1481150a291b772ea58116b052313dd35cbae535c2 |
| sat_scores_recent_2010.xls | 82817c89f1cd9d4de3123eee0d01399ea24cee8f435a622c801a2e3903c5807c |
| sat_scores_recent_2011.csv | 6b3ce4b20efc8b70d76d41be46827e055852e8600159415d827bcd7abfd20d55 |
| sat_scores_recent_2012.csv | 418cb2157d36902e1839f52922984a9be49cfee776e0ecaf1f2f6a4272d058d8 |
| sat_scores_recent_2013.csv | 650433e9cca2d10598a4fed263693caaeedc3f77fa3cfcf89ee6144a40ede559 |
| sat_scores_recent_2014.csv | 86cf945b7a5a1af0436b09652235901c7a1f55599f5697485585b024f5f6a27d |
| sat_scores_recent_2015.csv | c9114b976528c5dee99796d87ce37711a0eb581b97c8636c19366a71aafb9d76 |
| sat_scores_recent_2016_new_format.csv | 79fdd10cb401a6c10c778fa17c9876156529d62a548d0641e7ea445d923debeb |
| sat_scores_recent_2016_old_format.csv | 275818541fbb7126f42fc23282253afe9682e432daaf3b28a0e343d599c881a8 |
| sat_scores_recent_2017.csv | d264d0e1e090ae669a8759eb86a0a03538abb2f4ba567c6cd08d9280eb487067 |
| sat_scores_recent_2018.csv | 39ba0a16b1ec1c06037252d850ac809f67d0eb8bddc4ba9a28dfaded0f70fd45 |
| sat_scores_recent_2019.csv | fa335fbe805c1aeedc92f0dbb58d93d5f9f58e532ff217f48bf49b28f8bedd42 |
| sat_scores_recent_2020.csv | b617758759e015f0f5efc9222b2d924b0bc23c2a353cec84d4f20c7b9d93bd29 |
| sat_scores_recent_2021.csv | 1aaae3ea362afda04a9b3b1126c37f6c5704c03485fc798c3fe02951f5fd2077 |
| sat_scores_recent_2022.csv | 36c7e5705fcc1e8c8c0b821e4ffce0d1798599c8b01cbcebfccb8103ef32b94a |
| sat_scores_recent_2023.csv | cc33622066bcb6920e7c81463b3a966c0a5d7e8a6ff14acc052d949f501f46d8 |
| sat_scores_recent_2024.csv | f73e42cdbdf106b6b35557ec26f2ad658b7096917dea06fe28696867846fd138 |

## Excel Sheet Structure

Four files are true `.xls` (2007–2010); two more files (2005, 2006) are `.xls` binaries saved with a `.csv` extension. All six contain the data in a single sheet plus two empty sheets — the transform never needs to concatenate sheets. `pl.read_excel` with the default `calamine` engine reads all six.

| File(s) | Sheets | Notes |
|---------|--------|-------|
| sat_scores_recent_2005.csv | `SAT` (Data, 536 rows × 72 cols) | Actually `.xls`; data sheet is named `SAT`, not `Sheet1` |
| sat_scores_recent_2006.csv | `Sheet1` (Data, 542 rows × 72 cols), `Sheet2` (empty), `Sheet3` (empty) | Actually `.xls` despite the `.csv` extension |
| sat_scores_recent_2007.xls | `Sheet1` (Data, 543 rows × 72 cols), `Sheet2` (empty), `Sheet3` (empty) | |
| sat_scores_recent_2008.xls | `Sheet1` (Data, 562 rows × 52 cols), `Sheet2` (empty), `Sheet3` (empty) | |
| sat_scores_recent_2009.xls | `SAT` (Data, 567 rows × 52 cols), `Sheet2` (empty), `Sheet3` (empty) | Data sheet is named `SAT`, not `Sheet1` |
| sat_scores_recent_2010.xls | `Sheet1` (Data, 582 rows × 52 cols), `Sheet2` (empty), `Sheet3` (empty) | |

CSV files (2004, 2011–2024, excluding the misnamed 2005/2006) are single-table and do not have a sheet concept.

## Summary

SAT (Scholastic Assessment Test) college-admissions test results for Georgia public high schools. The dataset reports the test's section averages and an optional essay subscore, plus a count of students tested, for each entity. The exact measures vary by era because the SAT itself was redesigned in 2016:

- **Pre-2016 SAT** (Eras 1–4): three 200–800 section scores — **Verbal** (renamed **Reading** starting in 2012), **Math**, and **Writing** (introduced 2008) — plus a **Combined** total (Verbal+Math pre-2008; Verbal+Math+Writing 2008–2015).
- **Redesigned SAT (2016+)** (Eras 5–6): a 200–800 **Math Section Score**, a 200–800 **Evidence-Based Reading and Writing** score (present 2016–2019, dropped from 2020 onward), a **Reading Test Score** and **Writing and Language Test Score** published by GOSA on a 200–800 section-equivalent scale (College Board separately reports these as 10–40 cross-test scores, but the bronze files ship the section-equivalent values), a 400–1600 **Combined Test Score**, and a 2–8 essay triptych (**Reading**, **Analysis**, **Writing**) plus their **Essay Total**.

Eras 1–2 also report "**High**"-section averages (best-ever per student across test attempts) alongside "**Recent**" averages (most recent attempt). From 2011 onward the dataset additionally reports the **district**, **state**, and (sporadically) **national** averages alongside the school value on every row — useful for benchmarking, same pattern as `act_scores`. Eras 1–3 (2004–2010) carry demographic subgroup breakdowns as wide columns; from 2011 onward every row is restricted to `SUBGRP_DESC = "All Students"` (there are no demographic breakdowns in the long-format data).

## Eras

Six eras total. Note: `sat_scores_recent_2016_old_format.csv` duplicates 2016 in the Era 4 15-column shape, and `sat_scores_recent_2016_new_format.csv` gives 2016 in the Era 5 14-column shape. Both carry `LONG_SCHOOL_YEAR = "2015-16"`. The transform should pick one (likely the new-format file, which contains the redesigned-SAT metrics introduced that year) and skip the other to avoid double-counting.

### Era 1: 2004–2006 (wide 72-column, full-name demographics)

Files: `sat_scores_recent_2004.csv`, `sat_scores_recent_2005.csv` (actually `.xls`), `sat_scores_recent_2006.csv` (actually `.xls`)

72 columns: 2 identity columns + 7 metric groups × 10 demographics. Each row is one entity (state, district, or school). Metric groups: `Recent Total`, `Recent Verbal`, `Recent Math`, `High Total`, `High Verbal`, `High Math`, `Number Taken`.

| Column | Description |
|--------|-------------|
| SysSchoolID | Compound key — `"{district_code}:{school_code}"` for schools, `"{district_code}:ALL"` for district aggregates, `"ALL:ALL"` for the state row |
| School Name | Entity name. School name for school rows, district name for `:ALL` rows, `"State of Georgia"` for the `ALL:ALL` row |
| Recent Total {demographic} | Most-recent-attempt composite (Verbal+Math) — 10 columns, 200–1600 scale |
| Recent Verbal {demographic} | Most-recent Verbal section score — 10 columns, 200–800 |
| Recent Math {demographic} | Most-recent Math section score — 10 columns, 200–800 |
| High Total {demographic} | Best-attempt composite (Verbal+Math) — 10 columns, 200–1600 |
| High Verbal {demographic} | Best-attempt Verbal section score — 10 columns, 200–800 |
| High Math {demographic} | Best-attempt Math section score — 10 columns, 200–800 |
| Number Taken {demographic} | Count of students tested — 10 columns |

**Demographic suffixes** (verbatim from column names): `All Students`, `Asian`, `Black`, `Female`, `Hispanic`, `Male`, `American Indian`, `O` (Other), `R` (no long-form label, always blank/NULL), `White`. There is one stray double-space in `High Verbal  Asian` (two spaces before `Asian`) that is part of the literal column name in all three era-1 files.

#### Sample Data (2004, first 2 data rows, truncated)

```
SysSchoolID  School Name                 Recent Total All Students  Recent Verbal All Students  Recent Math All Students  Number Taken All Students
ALL:ALL      State of Georgia            981                        490                          491                       —
"601:103"    Appling County High School  985                        488                          497                       134
"601:ALL"    Appling County              985                        488                          497                       134
```

#### Statistics (2005 All Students numeric columns)

```
                    Recent Total  Recent Verbal  Recent Math   High Total    High Verbal   High Math     Number Taken
count               536           536            536            536           536           536           536
mean                944.6         473.7          470.9          961.5         482.3         479.2         270.3
std                 86.5          42.4           45.9           87.0          42.7          46.1          2119.9
min                 580           240            230            580           240           230           1
median              954           478            475            968           485           483           101
max                 1184          598            591            1208          612           604           48317
```

All 70 metric columns in Era 1 are clean numeric strings (no suppression markers). Where cells are empty, it means "no test takers" for that demographic at that entity. Most school rows have every demographic except `All Students` and the gender split blank, because the demographic breakouts are populated mostly at the district and state levels.

#### Null Counts (2004, sample columns)

Every column has a large number of empty strings (stored as `""`, not SQL null). Specific counts for 2004 (out of 2245 rows):

| Column | Empty cells |
|--------|-------------|
| SysSchoolID | 0 |
| School Name | 0 |
| Recent Total All Students | 1,727 |
| Recent Total Asian | 2,166 |
| Recent Total Black | 1,885 |
| Recent Total Female | 1,737 |
| Recent Total Hispanic | 2,175 |
| Recent Total Male | 1,745 |
| Recent Total American Indian | 2,241 |
| Recent TotalO (Other) | 2,197 |
| Recent TotalR | 1,931 (and non-empty cells are still blank-or-zero valued) |
| Recent Total White | 1,794 |

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| SysSchoolID | ~2,220 distinct compound keys in 2004 (free-form geography identifier) |
| School Name | entity name (free text) |

#### Suppression Markers

None in Era 1 — suppressed cells are simply blank (empty string), not encoded with a marker token. The `*R` demographic columns are uniformly blank across every row in 2004–2006.

### Era 2: 2007 (wide 72-column, single-letter demographic codes)

Files: `sat_scores_recent_2007.xls`

72 columns with the same 7 metric groups as Era 1, but the demographic suffix is now a **single letter** instead of a full name — a textual break from Era 1. The row structure (state / district / school all mixed) and `SysSchoolID` semantics are unchanged. The `School Name` column is renamed `SchoolNme` (no "a" between "Nme").

Demographic letter codes (in column order): `0` = All Students, `A` = Asian, `B` = Black, `F` = Female, `H` = Hispanic, `M` = Male, `N` = American Indian (Native), `O` = Other, `R` = (always `"NULL"`), `W` = White.

| Column | Description |
|--------|-------------|
| SysSchoolID | Same compound-key format as Era 1 |
| SchoolNme | Entity name (typo of `School Name`) |
| {metric} {code} | 70 metric columns: 7 metric groups × 10 demographic codes |

Every `{metric}R` column (Recent TotalR, Recent VerbalR, Recent MathR, High TotalR, High VerbalR, High MathR, Number TakenR) contains the literal string `"NULL"` in every row — that column is reserved but carries no data. Additionally, **every `High*` column except `High Total0`, `High Verbal0`, `High Math0`** (i.e., every "High" column for any non-`0` demographic) is `"NULL"` in every row, so the "High" break-out by demographic is unpopulated in 2007.

#### Sample Data (2007, first 2 data rows)

```
SysSchoolID  SchoolNme                  Recent Total0  Recent TotalA  Recent TotalB
704:1050     Morgan County High School  938            1200           752
608:105      Adairsville High School    1011           1180           943
755:ALL      Whitfield County           1017           1055           880
```

#### Statistics (Era 2, 2007)

The `Recent Total0`, `Recent TotalA`, `Recent TotalB` etc. columns load as int64 (Excel-native integer storage); no null cells. `Recent TotalR`, `High TotalA..W`, `High VerbalA..W`, `High MathA..W`, and `Number TakenR` load as string because of the literal `"NULL"` values.

#### Null Counts (Era 2)

No true SQL nulls — unpopulated cells use the literal string `"NULL"` as described above.

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| SysSchoolID | ~540 distinct (mix of school / district / state) |
| SchoolNme | entity name (free text) |

#### Suppression Markers (Era 2)

| Column | Non-Numeric Values |
|--------|-------------------|
| All `*R` columns (Recent TotalR, Recent VerbalR, Recent MathR, High TotalR, High VerbalR, High MathR, Number TakenR) | `"NULL"` (all 543 rows) — treat as null |
| All `High*` columns except `High {Total,Verbal,Math}0` (i.e., `High TotalA..W`, `High VerbalA..W`, `High MathA..W`) | `"NULL"` (all 543 rows) — treat as null |

### Era 3: 2008–2010 (wide 52-column, adds Writing, drops per-demographic High)

Files: `sat_scores_recent_2008.xls`, `sat_scores_recent_2009.xls`, `sat_scores_recent_2010.xls`

52 columns. Same single-letter demographic codes as Era 2 (`0, A, B, F, H, M, N, O, W` — the `R` slot is **dropped**, leaving 9 demographic codes). The **Writing section** is added (9 new `Recent Writing{code}` columns). The per-demographic `High` section is dropped — `High Total0`, `High Verbal0`, `High Math0`, `High Writing0` survive only for All Students. `School Name` returns (the 2007 typo `SchoolNme` is fixed). `SysSchoolID` is renamed `SysSchoolId` (lowercase `d`).

A single **legend row** sits at the top of the data sheet in every era-3 file: `SysSchoolId` and `School Name` are null; `Recent Total` contains the literal text `"(Verbal+Math+Writing)"` and `Recent Total0` contains `"Verbal and Math"` — this row explains what the two "total" columns mean and **must be dropped before transforming metrics**. The `Recent Total` column exists **only** in Era 3 (it is the new 3-part Verbal+Math+Writing composite, 600–2400 scale) — `Recent Total0 / Recent TotalA / etc.` are the 2-part (Verbal+Math, 200–1600 scale) composites carried over from Eras 1–2.

| Column | Description |
|--------|-------------|
| SysSchoolId | Compound key: `"{district}:{school}"`, `"{district}:ALL"`, `"ALL:ALL"` |
| School Name | Entity name |
| Recent Total | 3-section composite (Verbal+Math+Writing), 600–2400 scale, All Students only |
| Recent {Total,Verbal,Math,Writing}{code} | 4 metric groups × 9 demographic codes = 36 columns |
| High {Total,Verbal,Math,Writing}0 | 4 columns, All Students only, best-attempt values |
| Number Taken{code} | 9 columns |

Note: 2009's data sheet is named `SAT`, not `Sheet1` — pass the sheet name explicitly or let `read_excel` pick the first non-empty sheet.

#### Sample Data (2010, first 3 rows, shows legend row)

```
SysSchoolId  School Name                  Recent Total           Recent Total0     Recent TotalA     ...
null         null                         (Verbal+Math+Writing)  Verbal and Math   null              ← legend row (drop)
601:103      Appling County High School   1353                   916               Too Few Students
601:ALL      Appling County               1353                   916               Too Few Students
```

#### Statistics (2010, key metrics after legend drop, n=581 rows)

```
                     Recent Total  Recent Total0   Recent Verbal0  Recent Math0   Recent Writing0  Number Taken0
count                581           553             553             553            553              581
null_count           0             28              28              28             28               0
mean                 1381.8        934.7           467.4           467.3          454.9            271.4
std                  162.3         102.8           50.8            53.1           47.3             2220.1
min                  0             701             342             339            356              0
median               1375          929             465             464            450              94
max                  3114          2133            1039            1094           981              52632
```

Note: `Recent Total` max of `3114` and `Recent Total0` max of `2133` exceed the scale caps (2400 and 1600 respectively). These are genuine data-quality anomalies in the source — see row for `Rockdale County High School` (`722:3052`) which carries `Recent Total = 3114`. Also `Elberta Open Campus High School` (`676:3050`) is flagged with `Recent Total = 2287`. `Number Taken0` max of 52632 is the state-level aggregate row (`ALL:ALL`). These should be preserved as-is and flagged at validate time rather than silently corrected.

#### Null Counts (2010, after legend drop)

Non-All-Students demographic columns have 28–577 rows suppressed (as `Too Few Students`) or genuinely null. The high suppression counts for minority demographics are expected — very few high schools have enough test-takers in any single non-All-Students demographic for the score to be publishable.

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| SysSchoolId | ~580 distinct |
| School Name | entity name (free text) |

#### Suppression Markers (Era 3)

| Column | Non-Numeric Values | Count (2010) |
|--------|-------------------|--------------|
| `Recent Total` | `(Verbal+Math+Writing)` | 1 row (legend, drop) |
| `Recent Total0` | `Too Few Students`, `Verbal and Math` (legend) | 28 TFS + 1 legend |
| `Recent TotalB` (Black) | `Too Few Students` | 173 |
| `Recent TotalF` (Female) | `Too Few Students` | 41 |
| `Recent TotalM` (Male) | `Too Few Students` | 69 |
| `Recent TotalW` (White) | `Too Few Students` | 123 |
| `Recent Verbal0..W`, `Recent Math0..W`, `Recent Writing0..W` | `Too Few Students` | same per-demographic counts as `Recent Total*` |
| `High {Total,Verbal,Math,Writing}0` | `Too Few Students` | 28 each |
| `Number Taken*` | clean numeric — counts are not suppressed | 0 |

`Too Few Students` (full phrase with spaces) is the only suppression marker in Era 3. Treat it as null for metric columns.

### Era 4: 2011–2015, 2016_old_format (long 15-column, with NATIONAL averages)

Files: `sat_scores_recent_2011.csv`, `sat_scores_recent_2012.csv`, `sat_scores_recent_2013.csv`, `sat_scores_recent_2014.csv`, `sat_scores_recent_2015.csv`, `sat_scores_recent_2016_old_format.csv`

Era 4 is a long/tidy format: one row per (year, school, test-component), carrying national/state/district/school count and average on every row. All rows are `SUBGRP_DESC = "All Students"` (demographic breakouts disappear in this era). Every row is a school-level row — there are no state/district aggregate rows, because the state and district numbers are columns.

| Column | Description |
|--------|-------------|
| LONG_SCHOOL_YEAR | `"YYYY-YY"` format (e.g., `"2010-11"`) — same value in every row |
| SCHOOL_DISTRCT_CD | District code (integer as string) — note the misspelling DIST**R**CT here |
| SCHOOL_DSTRCT_NM | District name — note the different misspelling D**S**TRCT here |
| INSTN_NUMBER | School/institution code (integer as string, sometimes zero-padded) |
| INSTN_NAME | School name |
| SUBGRP_DESC | Always `"All Students"` |
| TEST_CMPNT_TYP_CD | Test-component code (categorical) — see values below |
| NATIONAL_NUM_TESTED_CNT | Count tested nationally (constant per year+component) |
| STATE_NUM_TESTED_CNT | Count tested statewide |
| DSTRCT_NUM_TESTED_CNT | Count tested in the district |
| INSTN_NUM_TESTED_CNT | Count tested at the school |
| NATIONAL_AVG_SCORE_VAL | National average score |
| STATE_AVG_SCORE_VAL | State average score |
| DSTRCT_AVG_SCORE_VAL | District average score |
| INSTN_AVG_SCORE_VAL | School average score |

#### Sample Data (2013)

```
LONG_SCHOOL_YEAR  SCHOOL_DISTRCT_CD  SCHOOL_DSTRCT_NM   INSTN_NUMBER  INSTN_NAME                           SUBGRP_DESC   TEST_CMPNT_TYP_CD  INSTN_NUM_TESTED_CNT  INSTN_AVG_SCORE_VAL
2012-13           611                Bibb County        303           William S. Hutchings Career Center   All Students  Reading            26                    429
2012-13           644                DeKalb County      5067          Southwest DeKalb High School         All Students  Reading            479                   423
2012-13           617                Burke County       288           Burke County High School             All Students  Mathematics        123                   428
```

#### Statistics (2013, numeric cols)

```
                          count  null  mean          std       min     median   max
NATIONAL_NUM_TESTED_CNT   1716   0     1,295,267     0         1.3M    1.3M     1.3M
STATE_NUM_TESTED_CNT      1716   0     84,853        0         84,853  84,853   84,853
DSTRCT_NUM_TESTED_CNT     1700   16    2,228         3,224     11      875      10,898
INSTN_NUM_TESTED_CNT      1612   104   210           185       10      161      1,008
NATIONAL_AVG_SCORE_VAL    1716   0     737           425       480     503      1,474
STATE_AVG_SCORE_VAL       1716   0     673           390       381     483      1,345
DSTRCT_AVG_SCORE_VAL      1700   16    659           386       187     466      1,476
INSTN_AVG_SCORE_VAL       1612   104   649           383       187     463      1,728
```

The `NATIONAL_AVG_SCORE_VAL` max of 1474 reflects the 400–1600 `Combined` component total; pre-2016 component rows (Math, Reading, Writing) range 200–800.

#### Null Counts (2013)

| Column | Null count |
|--------|-----------|
| All identity cols + NATIONAL/STATE cols | 0 |
| DSTRCT_NUM_TESTED_CNT | 16 (corresponding to `TFS` marker + null) |
| DSTRCT_AVG_SCORE_VAL | 16 |
| INSTN_NUM_TESTED_CNT | 104 |
| INSTN_AVG_SCORE_VAL | 104 |

#### Categorical Columns (Era 4)

| Column | Distinct Values |
|--------|----------------|
| LONG_SCHOOL_YEAR | single value per file, e.g., `2012-13` |
| SUBGRP_DESC | `All Students` (always) |
| TEST_CMPNT_TYP_CD | Varies by year. 2011: `Combined`, `Mathematics`, `Verbal`, `Writing` (4). 2012–2015 & 2016_old: `Combined`, `Mathematics`, `Reading`, `Writing` (4 — `Verbal` → `Reading` rename starting 2012) |
| SCHOOL_DSTRCT_NM | ~184 distinct district names (free text) |
| INSTN_NAME | ~420 distinct school names (free text) |

#### Suppression Markers (Era 4)

| Column | Non-Numeric Values |
|--------|-------------------|
| DSTRCT_NUM_TESTED_CNT | `TFS` (Too Few Students) — 16 rows in 2013 |
| INSTN_NUM_TESTED_CNT | `TFS` — 104 rows in 2013 |
| DSTRCT_AVG_SCORE_VAL, INSTN_AVG_SCORE_VAL | may carry nulls (empty), no text marker — 16 / 104 nulls in 2013 |

All "count" columns occasionally carry the marker `TFS`; the corresponding `_AVG_SCORE_VAL` columns are simply null (empty) in the same rows.

### Era 5: 2016_new_format, 2017–2022 (long 14-column, NATIONAL_AVG dropped, redesigned SAT)

Files: `sat_scores_recent_2016_new_format.csv`, `sat_scores_recent_2017.csv` through `sat_scores_recent_2022.csv`

Identical to Era 4 **except**: the `NATIONAL_AVG_SCORE_VAL` column is dropped. `NATIONAL_NUM_TESTED_CNT` is **kept** (but is empty in `2016_new_format.csv` — all 3,611 rows null — and populated from 2017 onward). Net one fewer column: 14 instead of 15.

The column order is: `LONG_SCHOOL_YEAR, SCHOOL_DISTRCT_CD, SCHOOL_DSTRCT_NM, INSTN_NUMBER, INSTN_NAME, SUBGRP_DESC, TEST_CMPNT_TYP_CD, NATIONAL_NUM_TESTED_CNT, STATE_NUM_TESTED_CNT, DSTRCT_NUM_TESTED_CNT, INSTN_NUM_TESTED_CNT, STATE_AVG_SCORE_VAL, DSTRCT_AVG_SCORE_VAL, INSTN_AVG_SCORE_VAL`.

Also in Era 5, `TEST_CMPNT_TYP_CD` expands to the redesigned-SAT components and carries **two literal double-spaces** inside some codes that must be preserved verbatim.

#### Categorical Columns (Era 5)

| Column | Distinct Values |
|--------|----------------|
| LONG_SCHOOL_YEAR | single value per file, e.g., `2019-20` |
| SUBGRP_DESC | `All Students` (always) |
| TEST_CMPNT_TYP_CD | 2016_new, 2017–2019: 9 values (includes `Evidence Based Reading and Writing - New`). 2020–2022: 8 values (EBRW removed). See full list below |

**Distinct `TEST_CMPNT_TYP_CD` values (Era 5):**

| Value | Notes |
|-------|-------|
| `Math Section Score - New` | 200–800 |
| `Evidence Based Reading and Writing - New` | 200–800. Present 2016–2019 only. **Dropped from 2020 onward** |
| `WritLang Test  Score - New` | 200–800 section-equivalent scale as published by GOSA (College Board's 10–40 cross-test score is a different reporting convention). **Double-space before `Score`** |
| `Reading Test  Score - New` | 200–800 section-equivalent scale as published by GOSA (College Board's 10–40 cross-test score is a different reporting convention). **Double-space before `Score`** |
| `Combined Test Score` | 400–1600 composite (Math + EBRW) |
| `Essay Writing Score - New` | 2–8 essay subscore |
| `Essay Reading Score - New` | 2–8 essay subscore |
| `Essay Analysis Score - New` | 2–8 essay subscore |
| `Essay Total` | 6–24 essay total |

#### Sample Data (2020)

```
LONG_SCHOOL_YEAR  SCHOOL_DISTRCT_CD  SCHOOL_DSTRCT_NM   INSTN_NUMBER  INSTN_NAME                           TEST_CMPNT_TYP_CD              INSTN_NUM_TESTED_CNT  INSTN_AVG_SCORE_VAL
2019-20           658                Forsyth County     0219          Forsyth Virtual Academy              WritLang Test  Score - New     TFS                    TFS
2019-20           658                Forsyth County     5050          Forsyth Central High School          Essay Writing Score - New      71                     6
2019-20           730                Talbot County      0190          Central Elementary/High School       Combined Test Score            TFS                    TFS
2019-20           602                Atkinson County    0103          Atkinson County High School          Reading Test  Score - New      39                     257
```

#### Suppression Markers (Era 5)

Same as Era 4, but Era 5 also sees `TFS` in the `_AVG_SCORE_VAL` columns (not just the `_NUM_TESTED_CNT` columns). 2020 counts:

| Column | Non-Numeric Values | Count (2020) |
|--------|-------------------|--------------|
| DSTRCT_NUM_TESTED_CNT | `TFS` | 268 |
| INSTN_NUM_TESTED_CNT | `TFS` | 544 |
| DSTRCT_AVG_SCORE_VAL | `TFS` | 268 |
| INSTN_AVG_SCORE_VAL | `TFS` | 544 |

`NATIONAL_NUM_TESTED_CNT` is null across every row in `2016_new_format.csv` (zero non-null values, 3,611 nulls) but populated in 2017–2022.

### Era 6: 2023–2024 (long 17-column, adds assessment flag and "highest recent" flag, restores NATIONAL_AVG)

Files: `sat_scores_recent_2023.csv`, `sat_scores_recent_2024.csv`

Adds two leading columns — `#ASSMT_CD` (always `"SAT"`) and `HIGHEST_RECENT_IND` (always `"Recent"`) — and **restores** `NATIONAL_AVG_SCORE_VAL` as a column (so Era 6 has the Era 4 set of score columns plus Era 5's additional per-row assessment flags). Also, the two district columns switch spellings back to the shorter variant: `SCHOOL_DSTRCT_CD` (no extra R) and `SCHOOL_DSTRCT_NM`. The first column name begins with a literal `#` character: `#ASSMT_CD`. `TEST_CMPNT_TYP_CD` matches Era 5 2020–2022 (8 values — EBRW remains dropped).

| Column | Description |
|--------|-------------|
| #ASSMT_CD | `"SAT"` in every row |
| HIGHEST_RECENT_IND | `"Recent"` in every row |
| LONG_SCHOOL_YEAR | same as Era 4/5 |
| SCHOOL_DSTRCT_CD | District code (note the spelling returns to `DSTRCT` — consistent with `SCHOOL_DSTRCT_NM`) |
| SCHOOL_DSTRCT_NM | District name |
| INSTN_NUMBER | School code (sometimes zero-padded e.g. `0105`) |
| INSTN_NAME | School name |
| SUBGRP_DESC | Always `"All Students"` |
| TEST_CMPNT_TYP_CD | 8 values — same redesigned-SAT vocabulary as Era 5 (2020–2022) |
| NATIONAL_NUM_TESTED_CNT | National count (note 2024 formats values with trailing `.` e.g. `"1973891."`) |
| STATE_NUM_TESTED_CNT | State count |
| DSTRCT_NUM_TESTED_CNT | District count (may be `TFS`, or a fractional number like `4159.3`) |
| INSTN_NUM_TESTED_CNT | School count (may be `TFS`) |
| NATIONAL_AVG_SCORE_VAL | National average (may be `N/A`, used for essay components) |
| STATE_AVG_SCORE_VAL | State average |
| DSTRCT_AVG_SCORE_VAL | District average (may be `TFS`) |
| INSTN_AVG_SCORE_VAL | School average (may be `TFS`) |

#### Sample Data (2024)

```
#ASSMT_CD  HIGHEST_RECENT_IND  LONG_SCHOOL_YEAR  SCHOOL_DSTRCT_CD  SCHOOL_DSTRCT_NM   INSTN_NUMBER  INSTN_NAME                           TEST_CMPNT_TYP_CD          NATIONAL_NUM_TESTED_CNT  NATIONAL_AVG_SCORE_VAL
SAT        Recent              2023-24           622               Carroll County     5054          Villa Rica High School               Reading Test  Score - New  1973891.                 N/A
SAT        Recent              2023-24           754               White County       0105          White County High School             Reading Test  Score - New  1973891.                 N/A
SAT        Recent              2023-24           648               Douglas County     0100          Chapel Hill High School              Essay Reading Score - New  250976.0                 4
```

#### Null Counts (2024)

All 17 columns have 0 SQL-null values — all suppressions are encoded as text markers (`TFS`, `N/A`).

#### Categorical Columns (Era 6)

| Column | Distinct Values (2024) |
|--------|-----------------------|
| #ASSMT_CD | `SAT` |
| HIGHEST_RECENT_IND | `Recent` |
| LONG_SCHOOL_YEAR | `2023-24` (2024 file); `2022-23` (2023 file) |
| SUBGRP_DESC | `All Students` |
| TEST_CMPNT_TYP_CD | `Combined Test Score`, `Essay Analysis Score - New`, `Essay Reading Score - New`, `Essay Total`, `Essay Writing Score - New`, `Math Section Score - New`, `Reading Test  Score - New`, `WritLang Test  Score - New` (8 values) |
| SCHOOL_DSTRCT_NM | ~186 distinct district names |
| INSTN_NAME | ~430 distinct school names |

#### Suppression Markers (Era 6)

| Column | Non-Numeric Values | Count (2024) |
|--------|-------------------|--------------|
| DSTRCT_NUM_TESTED_CNT | `TFS` | 201 |
| INSTN_NUM_TESTED_CNT | `TFS` | 350 |
| DSTRCT_AVG_SCORE_VAL | `TFS` | 201 |
| INSTN_AVG_SCORE_VAL | `TFS` | 350 |
| NATIONAL_AVG_SCORE_VAL | `N/A` | 870 (every Essay-component row — College Board does not publish national essay averages) |

2023 suppression counts are higher: 412 `TFS` in district counts/averages, 656 in school counts/averages, 874 `N/A` in national averages.

Numeric values in 2024 also carry a trailing dot (e.g., `1973891.`, `4159.3`) — Polars' strict cast to Float64 accepts both. 2024 values also display fractional district counts for `DSTRCT_NUM_TESTED_CNT` (92 distinct fractional values including `10.7`, `106.7`, `1111.3`, `1688.3`, etc.) — **this is in the source data**, likely an artifact of weighted rollup reporting, and should be carried through as-is.

## ETL Considerations

1. **File-extension lies.** `sat_scores_recent_2005.csv` and `sat_scores_recent_2006.csv` are `.xls` files with a `.csv` extension. Detect by reading the first 8 bytes — `D0 CF 11 E0 A1 B1 1A E1` is the OLE compound-document magic number — and route those files through the Excel reader. Don't rely on the extension. Sheet names: 2005 → `SAT`, 2006 → `Sheet1`.

2. **2004 CSV parse failures.** Polars' CSV parser throws on a row containing `"Martin Luther King, Jr. Elementary School"` — the comma inside a properly-quoted field trips Polars' quote handling in this specific file. Fall back to Python's stdlib `csv.reader` for 2004 only; it handles the quoting correctly. Drop rows whose length doesn't match the header (2 rows at the end of 2004 have 48 and 11 fields).

3. **2016 dual-format files — keep both.** `2016_old_format.csv` and `2016_new_format.csv` both carry `LONG_SCHOOL_YEAR = "2015-16"` in every row, but they use **disjoint** `TEST_CMPNT_TYP_CD` vocabularies: the old-format file carries pre-redesign components (`combined` / `mathematics` / `reading` / `writing` on the 600-2400 composite scale), and the new-format file carries the redesigned-SAT components (`combined_test_score` / `math_section_score` / `reading_test_score` / `writlang_test_score`, plus Essay components). The natural key `(district, school, demographic, test_component)` therefore does not collide between the two files. Keep both: old-format rows preserve the 2015-16 cohort's pre-redesign measures, and new-format rows carry the redesigned-SAT measures that become standard from 2017 onward. (Earlier guidance to drop the old-format file was incorrect — it would discard ~1,728 rows of legitimate pre-redesign 2015-16 cohort data.)

4. **Legend row in Era 3.** Every `.xls` file in 2008–2010 has a single legend row at the top of the data sheet where `SysSchoolId` and `School Name` are null and the `Recent Total` / `Recent Total0` cells contain explanatory text (`"(Verbal+Math+Writing)"` / `"Verbal and Math"`). Drop this row (filter out `SysSchoolId.is_null()`) before casting metric columns to numeric, or the string-to-float cast will fail / emit spurious `Too Few Students` entries in the suppression analysis.

5. **Aggregate rows in Eras 1–3.** The wide-format files mix **state**, **district**, and **school** rows in the same table (identified by the `:ALL` suffix in `SysSchoolID` / `SysSchoolId`, and the single `ALL:ALL` state row). Decide whether the gold topic keeps all three levels or filters to schools only:
   - The `act_scores` topic keeps only the school-level rows in gold and discards the `:ALL` aggregates, on the grounds that Eras 4–6 also carry only school rows (state/district values are redundant columns on each school row). Consider the same approach here for consistency: drop the `:ALL` rows in Eras 1–3 so the gold fact table is uniformly "one school-year-component per row", then reconstruct state/district averages at query time.
   - If the project wants the pre-2011 state/district totals preserved, write them into a separate fact table (or a `detail_level` dimension) instead of mixing them into the school table.

6. **Column-name drift across eras.** The district-code column name alternates between `SCHOOL_DISTRCT_CD` (Eras 4–5) and `SCHOOL_DSTRCT_CD` (Era 6 — plus matching `SCHOOL_DSTRCT_NM` in all long-format eras). Both spellings are misspellings of "district"; rename both to `district_code` / `district_name` in gold. Similarly, `SysSchoolID` (Eras 1–2, uppercase D) vs `SysSchoolId` (Era 3, lowercase d).

7. **Demographic column renaming.** Era 1 uses full-name demographic column suffixes (`"All Students"`, `"Asian"`, `"Black"`, `"White"`, `"Hispanic"`, `"American Indian"`, `"Female"`, `"Male"`, `"O"`, `"R"`). Era 2 collapses them to single-letter codes (`0, A, B, F, H, M, N, O, R, W`). Era 3 drops the `R` slot (9 demographics). Eras 4–6 eliminate demographic breakouts entirely. Build an explicit mapping dictionary for the letter codes before melting to tidy format: `0 → All Students`, `A → Asian`, `B → Black`, `W → White`, `H → Hispanic`, `N → American Indian`, `F → Female`, `M → Male`, `O → Other/Multiracial`, `R → (drop; always null/NULL)`.

8. **`"NULL"` as a suppression marker in Era 2.** The 2007 file uses the literal string `"NULL"` (uppercase, not an empty cell) for every `*R` column and for every demographic break-out of the `High*` section. Add `"NULL"` to the `null_values` list when reading, or filter it out before numeric casting.

9. **`Too Few Students` vs `TFS`.** Era 3 spells the suppression marker `Too Few Students` (with spaces). Eras 4–6 abbreviate it to `TFS`. Both should be mapped to null in gold metric columns. Era 6 also introduces `N/A` in `NATIONAL_AVG_SCORE_VAL` — treat as null as well.

10. **Verbal vs Reading rename in the SAT itself.** The 2011 file's `TEST_CMPNT_TYP_CD` still uses `Verbal`, but every later file uses `Reading`. These are the same SAT section (until 2016). If collapsing across eras, map both to the same canonical component name in gold (e.g., `reading`) — but note that the **redesigned SAT** in 2016+ introduces a distinct `Reading Test  Score - New` that is a subscore on a different (10–40) scale, not a section score comparable to the 200–800 pre-2016 Reading/Verbal. These should stay as separate components in gold.

11. **Literal double-spaces in Era 5/6 `TEST_CMPNT_TYP_CD`.** `Reading Test  Score - New` and `WritLang Test  Score - New` both contain two spaces before `Score`. These are part of the literal value as emitted by GOSA. Preserve verbatim during recoding (don't collapse whitespace) or the join to a component-code dimension will miss.

12. **Number formatting in 2024.** Some numeric cells in `sat_scores_recent_2024.csv` ship with a trailing dot (e.g., `1973891.`). Polars' `cast(Float64, strict=False)` handles this fine. `DSTRCT_NUM_TESTED_CNT` also contains fractional values in 2024 (92 distinct, e.g., `4159.3`, `10.7`) — surprising for a count, but it's in the source. Carry through as-is and cast as `Float64`, not `Int64`, for the tested-count columns.

13. **"Number Taken" is tested, not enrolled.** `Number Taken*` and `*_NUM_TESTED_CNT` both describe **students who took the SAT**, not total enrolled students. The column naming differs by era (wide `Number Taken{code}` in Eras 1–3, long `INSTN_NUM_TESTED_CNT` etc. in Eras 4–6); rename to a single canonical `num_tested` in gold.

14. **Geography ids are bare integer strings.** `SCHOOL_DISTRCT_CD`, `SCHOOL_DSTRCT_CD`, `INSTN_NUMBER` are zero- or non-zero-padded integer strings (e.g., `"611"`, `"0105"`, `"5067"`). Normalize padding per the gold standards before joining to dimensions (the project convention — see the `act_scores` `bronze-data-structure.md` and `data-cleaning-standards` skill — is to pad GOSA district codes to width 3 and school codes to width 4).

15. **Evidence Based Reading and Writing (EBRW) drops after 2019.** The `Evidence Based Reading and Writing - New` component appears in 2016_new_format and 2017–2019, then vanishes from 2020 onward. Treat this as a real schema change in the source, not a data error — EBRW is a 200–800 section score that's still being reported for the 2019–20 cohort.

16. **Out-of-range values in Era 3.** 2010's `Recent Total` max of 3114 and `Recent Total0` max of 2133 exceed the 2400 / 1600 scale caps respectively. Validate these at audit time but carry through as-is — they appear to be source-data quality issues at a small number of entities (e.g., Rockdale County High School = 3114 Recent Total).

17. **Blank cells vs NULL cells in Era 1.** Era 1 (2004–2006) represents suppressed/missing values as **empty strings** (`""`), not SQL nulls and not a text marker. Map both `""` and null to null before numeric casting. In 2004 more than 1,700 of 2,245 rows have blank `Recent Total All Students`.

## Gold Schema Classification

The same table applies across every era (column-name variants across eras are noted in the Notes column).

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| SysSchoolID / SysSchoolId | fact_key | (split) | Split on `:` into `district_code` + `school_code`; `:ALL` rows are district/state aggregates (drop if keeping schools only). Exists only in Eras 1–3 |
| School Name / SchoolNme | dimension_attribute | — | `school_name` / `district_name` in schools/districts dimension; Era-2 typo (`SchoolNme`) still resolves to the same attribute |
| SCHOOL_DISTRCT_CD / SCHOOL_DSTRCT_CD | fact_key | district_code | FK to districts dimension; normalize padding to width 3 |
| SCHOOL_DSTRCT_NM | dimension_attribute | — | `district_name` in districts dimension |
| INSTN_NUMBER | fact_key | school_code | FK to schools dimension; normalize padding to width 4 |
| INSTN_NAME | dimension_attribute | — | `school_name` in schools dimension |
| LONG_SCHOOL_YEAR | fact_key | year | Parse `"YYYY-YY"` → ending calendar year int. Absent in Eras 1–3 — derive from filename there |
| SUBGRP_DESC | fact_key | demographic | FK to demographics dimension. Always `"All Students"` in Eras 4–6. In Eras 1–3 the demographic is encoded in the column **suffix**, not in a column — melt wide → long first |
| TEST_CMPNT_TYP_CD | fact_categorical | test_component | Normalize to a small controlled vocabulary spanning eras (pre-2016 Verbal/Reading/Math/Writing/Combined vs redesigned SAT sections and essay subscores). Preserve literal double-spaces when matching |
| #ASSMT_CD | not_in_gold | — | Era 6 only; always `"SAT"` (no information) |
| HIGHEST_RECENT_IND | not_in_gold | — | Era 6 only; always `"Recent"` — Eras 1–2 distinguished Recent vs High but neither era emits this value explicitly. Drop as noise |
| Recent Total / Recent Total0 / Recent TotalA / ... | fact_metric | avg_score | Era 1–3 only: melt wide → long. Era 1's `Recent Total` is 200–1600 (V+M); Era 3's `Recent Total` is 600–2400 (V+M+W); Era 3's `Recent Total0` is the 200–1600 (V+M) value — use the test_component dimension to disambiguate |
| Recent Verbal / Recent Math / Recent Writing / ... | fact_metric | avg_score | Era 1–3 melt; each becomes a row with `test_component = "recent_verbal"` / `"recent_math"` / `"recent_writing"` |
| High Total / High Verbal / High Math / High Writing / ... | fact_metric | avg_score | Era 1–3 melt; `test_component` prefix `"high_"`. Sparsely populated in Eras 2–3 (All Students only) |
| Number Taken / Number Taken0 / ... | fact_metric | num_tested | Era 1–3 melt → count; same join key as the avg_score row |
| INSTN_NUM_TESTED_CNT | fact_metric | num_tested | Era 4–6 school-level count |
| INSTN_AVG_SCORE_VAL | fact_metric | avg_score | Era 4–6 school-level average |
| NATIONAL_NUM_TESTED_CNT, STATE_NUM_TESTED_CNT, DSTRCT_NUM_TESTED_CNT | not_in_gold | — | Era 4–6: these are benchmarks carried on every school row. State and district values can be rebuilt from the dimensional state/district fact rows (if the pipeline writes them) or computed at query time — don't copy redundantly onto every school fact row |
| NATIONAL_AVG_SCORE_VAL, STATE_AVG_SCORE_VAL, DSTRCT_AVG_SCORE_VAL | not_in_gold | — | Same as above — benchmark columns, not primary measurements |
