# attendance — Bronze Data Structure

## Overview

- Topic: attendance
- Source: gosa
- Files: 21 files spanning 2004–2024
- Unreadable files: none (but `attendance_2005.csv` and `attendance_2006.csv` are XLS binary files mislabeled with the `.csv` extension — magic bytes `d0cf11e0a1b1...` confirm OLE compound format. Must be read with `pl.read_excel(path, engine='calamine')` or `xlrd.open_workbook(path)`)
- Year representation: Eras 1–4 (2004–2010) have **no** year column (year derived from filename only); Eras 5–8 (2011–2024) have `LONG_SCHOOL_YEAR` column formatted as `"YYYY-YY"` (e.g., `"2023-24"`)
- Filename-to-data year offset: filename year = ending calendar year of the school year. For tidy-era files, `attendance_2024.csv` contains `LONG_SCHOOL_YEAR = "2023-24"`. The same convention applies to wide-era files (filename `attendance_2010.xls` covers school year 2009-10 ending spring 2010); confirmed by Appling County High School student counts changing year over year (972 in 2010 file → 991 in 2011 file).
- Detail levels: state, district, school
  - Eras 1–4 (2004–2010): encoded in `SysSchoolID` / `sysschoolid` / `SchoolID`. `"ALL:ALL"` = state, `"{district}:ALL"` = district, else school
  - Eras 5–8 (2011–2024): explicit `DETAIL_LVL_DESC` column with values `"State"`, `"District"`, `"School"`
- Percentage scale: 0–100 for all `5 or Fewer Days Absent ...`, `6 to 15 Days Absent ...`, `More than 15 Days Absent ...`, and `FIVE_OR_FEWER_PERCENT_*` / `SIX_TO_FIFTEEN_PERCENT_*` / `OVER_15_PERCENT_*` / `CHRONIC_ABSENT_PERC_*` columns. `Number of Students ...` and `STUDENT_COUNT_*` are integer counts, not percentages.
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| attendance_2004.csv | 98fc990b4fdfe1a7acbaada05baae755644b7cdf0754b9011caa3de62169a628 |
| attendance_2005.csv | fa4d02bf9242a18a3cf0647fe9b281e412f59584d0d736f65431eebeca16fe75 |
| attendance_2006.csv | af38cd812fe597176841f1c13b3754b46189c09d075cad83c2dfab92b771d9a7 |
| attendance_2007.xls | 3adbae27613f092471d1929cc683f413374fabb3664e295e339fe2f9a8d32798 |
| attendance_2008.xls | eb0fd35351211680fbfc56871e3304f1af3fc193f495fcd6acb49faf063877e4 |
| attendance_2009.xls | 3c23679e9af1419609826178cfcf779efed875e3c0a80321bb43f33398f0a7a6 |
| attendance_2010.xls | 47899227da85c27583e192165a8d8c3a573b66086772b5fb66e80d6f803c588e |
| attendance_2011.csv | fcbf905e444e152ac8b76480a70917649d1ef44c6baeda810cca0cf2791fa3b0 |
| attendance_2012.xlsx | 5f6f4490a978cc7379cf372e927145c686380bf62eb8631b2300ab4506f734d7 |
| attendance_2013.csv | e6c9f07367c073dd166f69b45017985680070b247f9befecfc86d9cbebe55044 |
| attendance_2014.csv | c32e730ac4963f0b1b8d2cdd6bd66bd6367fb5b0fb3b067fc35467f88412c514 |
| attendance_2015.csv | 5f7c67c8b3e1180a550dba57fe687ca72a651ed82a51c35d36f9107a70a9fa77 |
| attendance_2016.csv | fd272eb745d98e45d4fedbaf8febff17d62f3292480f6023ef9bbe3ce00f5988 |
| attendance_2017.csv | 1262faba1eafab97bc3da9aefb43bd57c8060780feb2cfd6eb533b949c50df30 |
| attendance_2018.csv | 78dec78df9b4813b04df1d864485b69aee3550de9c9661a576e7b95c065b13ce |
| attendance_2019.csv | 2ec64da558ae74dc4db166e30ee62ff153ea6a49a5a13d86204408812b93e748 |
| attendance_2020.csv | 5d19c0a4859e37fab611891e8a95199f9b6d87546dc989304cbf0ea23e061d37 |
| attendance_2021.csv | a4c2bc9fa940d5257010665e007dfc79d6a73ed4471c3b7d4e032e75b08f376b |
| attendance_2022.csv | 7a180754d9b2814962bfa522f8da4cc2959846aeebfd118269315aa285f1539a |
| attendance_2023.csv | 6ffcd3e0b224b1cf3b606d48cd3a20e6b017f4fb9219e38d7f89295e68ff672f |
| attendance_2024.csv | 9992b4188180343c80a4d04d84bc13c01951f4699cc5c911487f4b9ed359667e |

## Excel Sheet Structure

The Excel/XLS files (and the two XLS-mislabeled-as-CSV files) all carry data in a single sheet — the transform never needs to concatenate sheets. CSV files (2004, 2011, 2013–2024) are single-table and do not have the sheet concept.

| File(s) | Sheets | Notes |
|---------|--------|-------|
| `attendance_2005.csv`, `attendance_2006.csv` | Sheet1 (Data, 2,255–2,286 rows × 62 cols), Sheet2 (empty), Sheet3 (empty) | XLS binary files mislabeled with `.csv` extension. Read with `pl.read_excel(engine='calamine')` |
| `attendance_2007.xls`, `attendance_2008.xls`, `attendance_2010.xls` | Sheet1 (Data, 2,346–2,453 rows × 62 cols), Sheet2 (empty), Sheet3 (empty) | Standard Excel default sheet layout |
| `attendance_2009.xls` | Attendance (Data, 2,418 rows × 62 cols) | Only sheet present; data sheet renamed to `Attendance` |
| `attendance_2012.xlsx` | Export Worksheet (Data, 2,485 rows × 67 cols) | Single sheet with custom name |

## Summary

Georgia's attendance distribution data — counts and percentages of students by absentee category. Each row reports three percentage metrics for a given entity (state, district, or school) and demographic subgroup:

- **5 or Fewer Days Absent** — percentage of students absent five or fewer days during the school year (the most-attendant tier)
- **6 to 15 Days Absent** — percentage of students absent six to fifteen days during the school year (middle tier)
- **More than 15 Days Absent** — percentage of students absent more than fifteen days during the school year (often used as a chronic-absenteeism proxy)

Two additional measures are present in some eras:

- **Number of Students / STUDENT_COUNT** — integer count of students in the denominator (always present across all eras)
- **CHRONIC_ABSENT_PERC** — percentage of students chronically absent (10% or more of enrolled days). Present in Era 5 (2011, but mostly null), absent in Era 6 (2012–2017), present and populated in Eras 7–8 (2018–2024)

Demographic breakdowns include race/ethnicity (Asian, Black, Hispanic, White, Multiracial, Native American/Alaskan), gender (Male, Female), special populations (Students with Disabilities / without, Limited English Proficient, Migrant), and economic status (Economically Disadvantaged / Not).

## Eras

Eight eras emerge from strict column-name equality. Eras 1–4 share the same 60 metric columns and differ only in identifier-column casing (`SysSchoolID` vs `sysschoolid` vs `SchoolID`, `School Name` vs `schoolname`). Eras 5–8 share the tidy long-form structure but differ in metric coverage and a leading `#RPT_NAME` column added in Era 8.

### Era 1: 2004–2006 (wide format, `SysSchoolID` / `School Name`)

Files: `attendance_2004.csv`, `attendance_2005.csv` (actually XLS), `attendance_2006.csv` (actually XLS)

Wide format with 62 columns: 2 identifier columns and 60 metric columns (4 metrics × 15 demographic groups). Each row is one entity (state, district, or school); demographics and metrics are encoded in the column names.

| Column | Description |
|--------|-------------|
| SysSchoolID | Compound `district:school` key (e.g., `"601:103"` for school, `"601:ALL"` for district aggregate, `"ALL:ALL"` for state) |
| School Name | Entity name (school name, district name like `"Appling County"`, or `"State of Georgia"` for state row) |
| Number of Students {demographic} | Integer count of students in the denominator (15 columns) |
| 5 or Fewer Days Absent {demographic} | Percentage of students absent 5 or fewer days, 0–100 (15 columns) |
| 6 to 15 Days Absent {demographic} | Percentage of students absent 6 to 15 days, 0–100 (15 columns) |
| More than 15 Days Absent {demographic} | Percentage of students absent more than 15 days, 0–100 (15 columns) |

**Demographic labels in column names** (order as they appear in the file): `All`, `Economically Disadvantaged`, `Migrant`, `Not Economically Disadvantaged`, `Asian`, `Black`, `Female`, `Hispanic`, `Limited English Proficient`, `Male`, `Native Amer/Alaskan Native`, `Students without Disabilities`, `Students with Disabilities`, `Multiracial`, `White`.

#### Sample Data (2006)

```
shape: (2285, 62) — first 6 columns shown
┌─────────────┬──────────────────────────────────┬────────────────────────┬────────────────────────────┬─────────────────────────┬──────────────────────────────┐
│ SysSchoolID ┆ School Name                      ┆ Number of Students All ┆ 5 or Fewer Days Absent All ┆ 6 to 15 Days Absent All ┆ More than 15 Days Absent All │
╞═════════════╪══════════════════════════════════╪════════════════════════╪════════════════════════════╪═════════════════════════╪══════════════════════════════╡
│ 601:103     ┆ Appling County High School       ┆ 954                    ┆ 45.2                       ┆ 38.1                    ┆ 16.8                         │
│ 601:1050    ┆ Altamaha Elementary School       ┆ 431                    ┆ 45.5                       ┆ 45.5                    ┆ 9.0                          │
│ 601:177     ┆ Appling County Elementary School ┆ 540                    ┆ 57.6                       ┆ 35.7                    ┆ 6.7                          │
│ 601:195     ┆ Appling County Middle School     ┆ 805                    ┆ 53.2                       ┆ 39.5                    ┆ 7.3                          │
│ 601:277     ┆ Appling County Primary School    ┆ 756                    ┆ 47.1                       ┆ 42.9                    ┆ 10.1                         │
└─────────────┴──────────────────────────────────┴────────────────────────┴────────────────────────────┴─────────────────────────┴──────────────────────────────┘
```

#### Statistics (2006)

- 2,285 rows: 1 state + 185 district + 2,099 school (185 rows ending in `:ALL` = districts; 1 row `ALL:ALL` = state)
- All 62 columns are read as strings; metric columns cast cleanly to Float64
- `5 or Fewer Days Absent All` percentage range: 5.8 – 100.0 (mean 57.7, median 57.6)
- `Number of Students All` range: 26 – 1,794,430 (state row reaches max)

Row counts across the era:

| Year | Total rows | State | District | School |
|------|-----------:|------:|---------:|-------:|
| 2004 | 2,243 | 1 | 184 | 2,058 |
| 2005 | 2,254 | 1 | 184 | 2,069 |
| 2006 | 2,285 | 1 | 184 | 2,100 |

#### Null Counts (2006)

All 62 columns: **0 nulls**. (2004 has nulls — see Era 1 specifics in ETL Considerations.)

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| SysSchoolID | 2,285 unique entity keys (1 state, 185 district, 2,099 school) |
| School Name | 2,184 distinct school/district/state names; some duplicate names (e.g., generic `"9th Grade Academy"`) |

#### Suppression Markers

No string suppression markers in Eras 1–3. **Era 1 (2004 only)** — when a demographic subgroup has zero students, the percentage columns may be `null` (see ETL Considerations). 2005, 2006 have no nulls anywhere. The metric columns cast cleanly to Float64 in every Era 1 file.

---

### Era 2: 2007–2008 (wide format, `sysschoolid` / `schoolname` lowercased)

Files: `attendance_2007.xls`, `attendance_2008.xls`

Identical column set to Era 1 except the first two columns are lowercased: `sysschoolid` and `schoolname`. The remaining 60 metric columns are byte-for-byte identical to Era 1.

| Column | Description |
|--------|-------------|
| sysschoolid | Same compound `district:school` key as Era 1 |
| schoolname | Same entity name field as Era 1 |
| (60 metric columns) | Identical to Era 1 |

#### Sample Data (2008)

```
shape: (2392, 62) — first 6 columns shown
┌─────────────┬──────────────────────────────────┬────────────────────────┬────────────────────────────┬─────────────────────────┬──────────────────────────────┐
│ sysschoolid ┆ schoolname                       ┆ Number of Students All ┆ 5 or Fewer Days Absent All ┆ 6 to 15 Days Absent All ┆ More than 15 Days Absent All │
╞═════════════╪══════════════════════════════════╪════════════════════════╪════════════════════════════╪═════════════════════════╪══════════════════════════════╡
│ 601:103     ┆ Appling County High School       ┆ 990                    ┆ 39.2                       ┆ 38.7                    ┆ 22.1                         │
│ 601:1050    ┆ Altamaha Elementary School       ┆ 386                    ┆ 36.4                       ┆ 52.7                    ┆ 10.9                         │
└─────────────┴──────────────────────────────────┴────────────────────────┴────────────────────────────┴─────────────────────────┴──────────────────────────────┘
```

#### Statistics

| Year | Total rows | State | District | School |
|------|-----------:|------:|---------:|-------:|
| 2007 | 2,345 | 1 | 184 | 2,160 |
| 2008 | 2,392 | 1 | 185 | 2,206 |

#### Null Counts (2008)

All 62 columns: **0 nulls**.

#### Categorical & Suppression Columns

Same as Era 1 — `sysschoolid` and `schoolname` are high-cardinality identifiers. No string suppression markers; metric columns cast cleanly to Float64.

---

### Era 3: 2009 only (wide format, `SchoolID` / `School Name`)

Files: `attendance_2009.xls`

Single-year era. The first two columns differ from both Era 1 and Era 2: `SchoolID` (no "Sys" prefix) and `School Name` (Era 1 spelling, Era 2 case-collision-free). The remaining 60 metric columns match Eras 1–2.

| Column | Description |
|--------|-------------|
| SchoolID | Same compound `district:school` key as Eras 1–2 |
| School Name | Same entity name field as Era 1 |
| (60 metric columns) | Identical to Eras 1–2 |

#### Sample Data (2009)

```
shape: (2417, 62) — first 6 columns shown
┌──────────┬──────────────────────────────────┬────────────────────────┬────────────────────────────┬─────────────────────────┬──────────────────────────────┐
│ SchoolID ┆ School Name                      ┆ Number of Students All ┆ 5 or Fewer Days Absent All ┆ 6 to 15 Days Absent All ┆ More than 15 Days Absent All │
╞══════════╪══════════════════════════════════╪════════════════════════╪════════════════════════════╪═════════════════════════╪══════════════════════════════╡
│ 601:103  ┆ Appling County High School       ┆ 1059                   ┆ ...                        ┆ ...                     ┆ ...                          │
│ 601:1050 ┆ Altamaha Elementary School       ┆ 401                    ┆ ...                        ┆ ...                     ┆ ...                          │
│ 601:ALL  ┆ Appling County                   ┆ ...                    ┆ ...                        ┆ ...                     ┆ ...                          │
└──────────┴──────────────────────────────────┴────────────────────────┴────────────────────────────┴─────────────────────────┴──────────────────────────────┘
```

#### Statistics

| Year | Total rows | State | District | School |
|------|-----------:|------:|---------:|-------:|
| 2009 | 2,417 | 1 | 189 | 2,227 |

#### Null Counts (2009)

All 62 columns: **0 nulls**.

#### Categorical & Suppression Columns

Same as Eras 1–2.

---

### Era 4: 2010 only (wide format, lowercased identifiers — same as Era 2 but isolated year)

Files: `attendance_2010.xls`

Identifier columns revert to the Era 2 lowercased form (`sysschoolid`, `schoolname`). Metric columns identical to Eras 1–3.

#### Sample Data (2010)

Same shape as Era 2 sample.

#### Statistics

| Year | Total rows | State | District | School |
|------|-----------:|------:|---------:|-------:|
| 2010 | 2,452 | 1 | 186 | 2,265 |

#### Null Counts (2010)

All 62 columns: **0 nulls**.

#### Categorical & Suppression Columns

Same as Eras 1–3.

---

### Era 5: 2011 only (tidy long format, with `CHRONIC_ABSENT_PERC_*` columns mostly null)

Files: `attendance_2011.csv`

Format pivots completely. **82 columns** — 7 identifier columns + 60 absentee-tier columns (4 metrics × 15 demographic groups, but reorganized) + 15 chronic-absence-percentage columns. Each row is now one entity at one detail level (state, district, school) rather than a wide-format school row.

| Column | Description |
|--------|-------------|
| LONG_SCHOOL_YEAR | School year string (`"2010-11"`, single value) |
| DETAIL_LVL_DESC | `"State"`, `"District"`, or `"School"` |
| SCHOOL_DSTRCT_CD | 3-digit district code or `"ALL"` for state row |
| SCHOOL_DSTRCT_NM | District name (e.g., `"Appling County"`) or `"All Column Values"` for state |
| INSTN_NUMBER | 4-digit zero-padded school code or `"ALL"` for district/state aggregate |
| INSTN_NAME | School name or `"All Column Values"` for district/state aggregate |
| GRADES_SERVED_DESC | Comma-separated grade list (e.g., `"PK,KK,01,02,03,04,05"`) |
| STUDENT_COUNT_{DEMO} | Integer count of students in denominator (15 demographic suffixes) |
| FIVE_OR_FEWER_PERCENT_{DEMO} | Percentage absent 5 or fewer days, 0–100 (15 demographic suffixes) |
| SIX_TO_FIFTEEN_PERCENT_{DEMO} | Percentage absent 6–15 days, 0–100 (15 demographic suffixes) |
| OVER_15_PERCENT_{DEMO} | Percentage absent more than 15 days, 0–100 (15 demographic suffixes) |
| CHRONIC_ABSENT_PERC_{DEMO} | Percentage chronically absent, 0–100 (15 demographic suffixes) — **mostly null in 2011** |

**Demographic suffixes used in column names**: `ALL`, `INDIAN` (Native American/Alaskan), `ASIAN`, `BLACK`, `WHITE`, `HISPANI` (sic — truncated `HISPANIC`), `MULTI` (multiracial), `FEMALE`, `MALE`, `SWD` (Students with Disabilities), `NOT_SWD`, `ED` (Economically Disadvantaged), `NOT_ED`, `LEP` (Limited English Proficient), `MIGRANT`.

#### Sample Data (2011)

```
shape: (2481, 82) — first 8 columns shown
┌──────────────────┬─────────────────┬──────────────────┬──────────────────┬──────────────┬──────────────────────────────────┬────────────────────┬───────────────────┐
│ LONG_SCHOOL_YEAR ┆ DETAIL_LVL_DESC ┆ SCHOOL_DSTRCT_CD ┆ SCHOOL_DSTRCT_NM ┆ INSTN_NUMBER ┆ INSTN_NAME                       ┆ GRADES_SERVED_DESC ┆ STUDENT_COUNT_ALL │
╞══════════════════╪═════════════════╪══════════════════╪══════════════════╪══════════════╪══════════════════════════════════╪════════════════════╪═══════════════════╡
│ 2010-11          ┆ School          ┆ 601              ┆ Appling County   ┆ 0103         ┆ Appling County High School       ┆ 09,10,11,12        ┆ 991               │
│ 2010-11          ┆ School          ┆ 601              ┆ Appling County   ┆ 0177         ┆ Appling County Elementary School ┆ 01,03,04,05        ┆ 545               │
│ 2010-11          ┆ District        ┆ 601              ┆ Appling County   ┆ ALL          ┆ All Column Values                ┆ ...                ┆ ...               │
│ 2010-11          ┆ State           ┆ ALL              ┆ All Column Values┆ ALL          ┆ All Column Values                ┆ ...                ┆ ...               │
└──────────────────┴─────────────────┴──────────────────┴──────────────────┴──────────────┴──────────────────────────────────┴────────────────────┴───────────────────┘
```

#### Statistics

- 2,481 rows: 1 state + 194 district + 2,286 school
- `FIVE_OR_FEWER_PERCENT_ALL` range: 0 – 100 (mean 57.3, median 57.2)
- `STUDENT_COUNT_ALL` range: 11 – 1,675,123 (state)
- Chronic-absence columns: 15 columns × 2,481 rows × ~99% nulls. Only 1–4 rows per chronic-absence column have any value, and those are all `0`. Treat 2011 chronic-absence data as effectively absent.

#### Null Counts (2011)

| Column group | Nulls |
|--------------|------:|
| All 7 identifier columns | 0 |
| All 60 STUDENT_COUNT / FIVE_OR_FEWER / SIX_TO_FIFTEEN / OVER_15 columns | 0 |
| CHRONIC_ABSENT_PERC_ALL | 2,479 |
| CHRONIC_ABSENT_PERC_INDIAN | 127 |
| CHRONIC_ABSENT_PERC_ASIAN | 1,177 |
| CHRONIC_ABSENT_PERC_BLACK | 2,359 |
| CHRONIC_ABSENT_PERC_WHITE | 2,256 |
| CHRONIC_ABSENT_PERC_HISPANI | 2,139 |
| CHRONIC_ABSENT_PERC_MULTI | 1,919 |
| CHRONIC_ABSENT_PERC_FEMALE | 2,470 |
| CHRONIC_ABSENT_PERC_MALE | 2,475 |
| CHRONIC_ABSENT_PERC_SWD | 2,448 |
| CHRONIC_ABSENT_PERC_NOT_SWD | 2,468 |
| CHRONIC_ABSENT_PERC_ED | 2,460 |
| CHRONIC_ABSENT_PERC_NOT_ED | 2,316 |
| CHRONIC_ABSENT_PERC_LEP | 1,575 |
| CHRONIC_ABSENT_PERC_MIGRANT | 196 |

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| LONG_SCHOOL_YEAR | `2010-11` (1 value) |
| DETAIL_LVL_DESC | `School` (2,286), `District` (194), `State` (1) |
| SCHOOL_DSTRCT_NM | 195 distinct (194 county/district names + `"All Column Values"` for the state row) |
| INSTN_NAME | 2,181 distinct (school names + `"All Column Values"` for district/state aggregates) |
| GRADES_SERVED_DESC | 75 distinct grade combinations |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| SCHOOL_DSTRCT_CD | `ALL` (1 row — state) |
| INSTN_NUMBER | `ALL` (195 rows — districts + state) |
| All metric columns | None (only nulls — no string markers) |

---

### Era 6: 2012–2017 (tidy long format, **no chronic-absence columns**)

Files: `attendance_2012.xlsx` through `attendance_2017.csv`

**67 columns** — same 7 identifier columns and 60 absentee-tier columns as Era 5, but the 15 `CHRONIC_ABSENT_PERC_*` columns are entirely absent.

| Column | Description |
|--------|-------------|
| (Same 67 columns as Era 5 minus CHRONIC_ABSENT_PERC_*) | See Era 5 |

#### Sample Data (2017)

Same shape as Era 5 sample.

#### Statistics (per year)

| Year | Total rows | State | District | School |
|------|-----------:|------:|---------:|-------:|
| 2012 | 2,485 | 1 | 196 | 2,288 |
| 2013 | 2,469 | 1 | 198 | 2,270 |
| 2014 | 2,460 | 1 | 198 | 2,261 |
| 2015 | 2,462 | 1 | 198 | 2,263 |
| 2016 | 2,474 | 1 | 204 | 2,269 |
| 2017 | 2,479 | 1 | 207 | 2,271 |

#### Null Counts (2017)

All 67 columns: **0 nulls**.

#### Categorical Columns

| Column | Distinct Values (2017) |
|--------|------------------------|
| LONG_SCHOOL_YEAR | One value per file (`"2011-12"` through `"2016-17"`) |
| DETAIL_LVL_DESC | `District`, `School`, `State` |
| SCHOOL_DSTRCT_NM | 207 districts + `"All Column Values"` |
| INSTN_NAME | 2,172 schools + `"All Column Values"` |
| GRADES_SERVED_DESC | 75 distinct combinations |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| SCHOOL_DSTRCT_CD | `ALL` (1 row per file — state) |
| INSTN_NUMBER | `ALL` (`District` + `State` rows — 197 to 208 per file) |
| All metric columns | None (no string markers, no nulls) |

---

### Era 7: 2018–2022 (tidy long format, **chronic-absence columns return**, `TFS` introduced 2021)

Files: `attendance_2018.csv` through `attendance_2022.csv`

**82 columns** — same as Era 5 (the `CHRONIC_ABSENT_PERC_*` columns are now populated). Suppression behavior changes mid-era: 2018–2020 have no markers; 2021–2022 introduce `"TFS"` ("Too Few Students") as the suppression sentinel.

| Column | Description |
|--------|-------------|
| (82 columns same as Era 5) | See Era 5 — the `CHRONIC_ABSENT_PERC_*` columns are now broadly populated |

#### Sample Data (2022)

```
shape: (2512, 82) — last 5 columns shown
┌─────────────────────────────┬────────────────────────┬────────────────────────────┬─────────────────────────┬─────────────────────────────┐
│ CHRONIC_ABSENT_PERC_NOT_SWD ┆ CHRONIC_ABSENT_PERC_ED ┆ CHRONIC_ABSENT_PERC_NOT_ED ┆ CHRONIC_ABSENT_PERC_LEP ┆ CHRONIC_ABSENT_PERC_MIGRANT │
╞═════════════════════════════╪════════════════════════╪════════════════════════════╪═════════════════════════╪═════════════════════════════╡
│ 33.8                        ┆ 34.2                   ┆ TFS                        ┆ 30.4                    ┆ 27.9                        │
│ 15.6                        ┆ 17.1                   ┆ TFS                        ┆ 12.4                    ┆ 13                          │
│ 18.4                        ┆ 18.2                   ┆ TFS                        ┆ 11.8                    ┆ 8.5                         │
└─────────────────────────────┴────────────────────────┴────────────────────────────┴─────────────────────────┴─────────────────────────────┘
```

#### Statistics (per year)

| Year | Total rows | State | District | School | Suppression markers |
|------|-----------:|------:|---------:|-------:|---------------------|
| 2018 | 2,486 | 1 | 207 | 2,278 | None |
| 2019 | 2,491 | 1 | 211 | 2,279 | None |
| 2020 | 2,493 | 1 | 215 | 2,277 | None |
| 2021 | 2,505 | 1 | 221 | 2,283 | `TFS` |
| 2022 | 2,512 | 1 | 220 | 2,291 | `TFS` |

#### Null Counts (2022)

All 82 columns: **0 nulls**. All suppression handled by `"TFS"` strings.

#### Categorical Columns

| Column | Distinct Values (2022) |
|--------|------------------------|
| LONG_SCHOOL_YEAR | One value per file (`"2017-18"` through `"2021-22"`) |
| DETAIL_LVL_DESC | `District`, `School`, `State` |
| SCHOOL_DSTRCT_NM | 222 districts + `"All Column Values"` |
| INSTN_NAME | 2,191 schools + `"All Column Values"` |
| GRADES_SERVED_DESC | 82 distinct combinations |

#### Suppression Markers (2022 example)

| Column | Non-Numeric Values |
|--------|-------------------|
| SCHOOL_DSTRCT_CD | `ALL` (1 row — state) |
| INSTN_NUMBER | `ALL` (221 rows — districts + state) |
| STUDENT_COUNT_ALL through OVER_15_PERCENT_MIGRANT (60 cols) | `TFS` (varies by column; lowest groups have most TFS — 1,069 TFS in `STUDENT_COUNT_ASIAN` is typical pattern) |
| CHRONIC_ABSENT_PERC_* (15 cols) | `TFS` (same suppression rule as the absentee-tier metrics) |

In the 2018–2020 sub-era, every metric is numeric — no `TFS`, no nulls. The transition to `TFS` happens in 2021. Native American (`STUDENT_COUNT_INDIAN`, etc.) is the most-suppressed group: in 2022, ~2,400 of 2,512 rows are `TFS` for `INDIAN` columns. Row counts above are the file-level totals — `TFS` does not delete rows, it just marks individual cells.

---

### Era 8: 2023–2024 (tidy long format with `#RPT_NAME` prefix, `TFS` + `null` mixed)

Files: `attendance_2023.csv`, `attendance_2024.csv`

**83 columns** — same as Era 7 plus a leading `#RPT_NAME` column always equal to `"Attendance"`. Suppression uses both `"TFS"` (mostly count metrics) and `null` (mostly percentage metrics).

| Column | Description |
|--------|-------------|
| #RPT_NAME | Always `"Attendance"` — constant report identifier. The `#` prefix is part of the literal column name. |
| (82 columns same as Era 7) | See Era 7 |

#### Sample Data (2024)

```
shape: (2535, 83) — first 8 columns shown
┌────────────┬──────────────────┬─────────────────┬──────────────────┬──────────────────┬──────────────┬───────────────────┬───────────────────────────────────────────┐
│ #RPT_NAME  ┆ LONG_SCHOOL_YEAR ┆ DETAIL_LVL_DESC ┆ SCHOOL_DSTRCT_CD ┆ SCHOOL_DSTRCT_NM ┆ INSTN_NUMBER ┆ INSTN_NAME        ┆ GRADES_SERVED_DESC                        │
╞════════════╪══════════════════╪═════════════════╪══════════════════╪══════════════════╪══════════════╪═══════════════════╪═══════════════════════════════════════════╡
│ Attendance ┆ 2023-24          ┆ District        ┆ 601              ┆ Appling County   ┆ ALL          ┆ All Column Values ┆ PK,KK,01,02,03,04,05,06,07,08,09,10,11,12 │
│ Attendance ┆ 2023-24          ┆ District        ┆ 602              ┆ Atkinson County  ┆ ALL          ┆ All Column Values ┆ PK,KK,01,02,03,04,05,06,07,08,09,10,11,12 │
└────────────┴──────────────────┴─────────────────┴──────────────────┴──────────────────┴──────────────┴───────────────────┴───────────────────────────────────────────┘
```

#### Statistics

| Year | Total rows | State | District | School |
|------|-----------:|------:|---------:|-------:|
| 2023 | 2,518 | 1 | 226 | 2,291 |
| 2024 | 2,535 | 1 | 234 | 2,300 |

#### Null Counts (2024 — non-zero only, columns with the same null count are grouped)

| Column group | Nulls per column |
|--------------|-----------------:|
| Asian metric quartet (`STUDENT_COUNT_ASIAN`, `FIVE_OR_FEWER_PERCENT_ASIAN`, `SIX_TO_FIFTEEN_PERCENT_ASIAN`, `OVER_15_PERCENT_ASIAN`, `CHRONIC_ABSENT_PERC_ASIAN`) | 249 |
| Indian metric quartet (5 cols) | 818 |
| Black metric quartet | 4 |
| White metric quartet | 40 |
| Hispanic metric quartet | 19 |
| Multi metric quartet | 18 |
| Female metric quartet | 13 |
| Male metric quartet | 7 |
| SWD metric quartet | 1 |
| Not-SWD metric quartet | 6 |
| ED metric quartet | 20 |
| Not-ED metric quartet | 1,013 |
| LEP metric quartet | 95 |
| Migrant metric quartet | 1,744 |

(Quartet here means the 5 columns: STUDENT_COUNT, FIVE_OR_FEWER_PERCENT, SIX_TO_FIFTEEN_PERCENT, OVER_15_PERCENT, CHRONIC_ABSENT_PERC for that demographic.)

#### Categorical Columns

| Column | Distinct Values (2024) |
|--------|------------------------|
| #RPT_NAME | `Attendance` (constant) |
| LONG_SCHOOL_YEAR | `2023-24` (1 value) |
| DETAIL_LVL_DESC | `District` (234), `School` (2,300), `State` (1) |
| SCHOOL_DSTRCT_NM | 235 districts + `"All Column Values"` |
| INSTN_NAME | School names + `"All Column Values"` |
| GRADES_SERVED_DESC | Many distinct combinations |

#### Suppression Markers (2024)

| Column | Non-Numeric Values |
|--------|-------------------|
| SCHOOL_DSTRCT_CD | `ALL` (1 row — state) |
| INSTN_NUMBER | `ALL` (235 rows — districts + state) |
| STUDENT_COUNT_* (15 cols) | `TFS` mixed with `null`; small-population demographics dominated by `TFS` (e.g., Asian: 1,069 `TFS` + 249 null in `STUDENT_COUNT_ASIAN`) |
| FIVE_OR_FEWER_PERCENT_*, SIX_TO_FIFTEEN_PERCENT_*, OVER_15_PERCENT_*, CHRONIC_ABSENT_PERC_* | `TFS` mixed with `null` — both must be treated as suppressed |

Both 2023 and 2024 use this `TFS` + `null` hybrid pattern. 2023 has slightly different null counts but the same conceptual suppression scheme.

---

## ETL Considerations

1. **File format issues (2005–2006)** — `attendance_2005.csv` and `attendance_2006.csv` are XLS binary files mislabeled with `.csv` extension. Magic bytes `d0 cf 11 e0 a1 b1 1a e1` confirm OLE compound format. Polars `read_csv` fails ("invalid utf-8 sequence"). Use `pl.read_excel(path, engine='calamine')` or detect via magic bytes and route to the Excel reader. The data sheet is `Sheet1`; `Sheet2` and `Sheet3` are empty.

2. **Wide-to-tidy conversion (Eras 1–4)** — Eras 1–4 (2004–2010) use wide format with demographic and metric encoded in 60 column names (4 metrics × 15 demographics). Must be unpivoted to match Eras 5–8. Recommended approach: melt all 60 metric columns, parse the column name into `metric` (one of `Number of Students`, `5 or Fewer Days Absent`, `6 to 15 Days Absent`, `More than 15 Days Absent`) and `demographic_raw`, then pivot back to four metric columns keyed by demographic.

3. **Identifier column casing varies (Eras 1–4)** — the first two columns are:
   - Era 1 (2004–2006): `SysSchoolID`, `School Name`
   - Era 2 (2007–2008): `sysschoolid`, `schoolname`
   - Era 3 (2009): `SchoolID`, `School Name`
   - Era 4 (2010): `sysschoolid`, `schoolname`
   
   Normalize by reading the file then renaming the first two columns to a canonical pair (e.g., `entity_id`, `entity_name`).

4. **`SysSchoolID`/`SchoolID` parsing (Eras 1–4)** — Split on `:` to extract district and school codes. Format: `"{district}:{school}"`. District is always 3 digits in Eras 1–4 (no 7-digit charter codes yet). School is a 3- or 4-digit institution number, but **not zero-padded** in these eras (`601:103` rather than `601:0103`). `"ALL"` is the sentinel: `"601:ALL"` = district aggregate, `"ALL:ALL"` = state aggregate. To match Eras 5–8, zero-pad school codes to 4 chars after splitting (`.str.zfill(4)`) and keep district codes at 3 chars.

5. **Demographic label normalization** — bronze uses these raw labels (Eras 1–4 from column name segments, Eras 5–8 from column name suffixes):

   | Era 1–4 column suffix | Era 5–8 column suffix | Canonical demographic |
   |-----------------------|----------------------|----------------------|
   | `All` | `ALL` | `all` |
   | `Asian` | `ASIAN` | `asian` |
   | `Black` | `BLACK` | `black` |
   | `White` | `WHITE` | `white` |
   | `Hispanic` | `HISPANI` (sic) | `hispanic` |
   | `Multiracial` | `MULTI` | `multiracial` |
   | `Native Amer/Alaskan Native` | `INDIAN` | `native_american` |
   | `Male` | `MALE` | `male` |
   | `Female` | `FEMALE` | `female` |
   | `Students with Disabilities` | `SWD` | `students_with_disabilities` |
   | `Students without Disabilities` | `NOT_SWD` | (no canonical match — confirm with `normalize_demographic_column` and add alias if needed) |
   | `Limited English Proficient` | `LEP` | `english_learners` |
   | `Economically Disadvantaged` | `ED` | `economically_disadvantaged` |
   | `Not Economically Disadvantaged` | `NOT_ED` | (no canonical match — confirm with `normalize_demographic_column`) |
   | `Migrant` | `MIGRANT` | `migrant` |

   Use `normalize_demographic_column()` from `src/utils/demographics.py` — never hardcode mappings. Add aliases (`HISPANI`, `INDIAN`, `SWD`, `NOT_SWD`, `LEP`, `ED`, `NOT_ED`) to `DEMOGRAPHIC_ALIASES` if missing. The transform must halt with `unmapped_count > 0` per the manifest contract — fix aliases until all bronze labels map.

6. **Suppression convention varies dramatically by era**:
   - **Era 1 (2004 only)** — null cells when a demographic group has zero students (~28k null cells across all metric columns). The `Number of Students {demo}` column is 0 for those rows, with corresponding `_Days Absent` columns null. Treat as suppressed → null in gold.
   - **Era 1 (2005–2006), Era 2 (2007–2008), Era 3 (2009), Era 4 (2010)** — no nulls, no string markers. All metric columns cast cleanly to Float64.
   - **Era 5 (2011)** — no nulls in the absentee-tier columns; the 15 `CHRONIC_ABSENT_PERC_*` columns are ~99% null and the few non-null values are all `0`. **Treat 2011 chronic-absence as missing data** rather than as zeros.
   - **Era 6 (2012–2017)** — no nulls, no string markers. Chronic-absence columns are absent (not null — the columns themselves don't exist).
   - **Era 7 (2018–2020)** — no nulls, no string markers. All metrics populated.
   - **Era 7 (2021–2022)** — `"TFS"` introduced as suppression marker. Zero nulls; every suppressed cell carries the literal string `"TFS"`. `read_bronze_file()` from `src/utils/transformers.py` handles `TFS` as a known marker; Polars `cast(Float64, strict=False)` then converts to null.
   - **Era 8 (2023–2024)** — both `"TFS"` and `null` used. Both must be treated as suppressed.

7. **`STUDENT_COUNT_INDIAN` and `CHRONIC_ABSENT_PERC_INDIAN` quirks (Era 7)** — in 2022, only ~91 of 2,512 rows have a numeric value for `STUDENT_COUNT_INDIAN`; the rest are `TFS`. The `[CATEGORICAL]` classification in Step-4 output (44 distinct values) is misleading — these are tiny integer counts surfacing because `numeric_pct < 0.5`. They are still the same metric column; cast with `strict=False` and the `TFS` markers will become null.

8. **`Native Amer/Alaskan Native` literal contains a slash** — the demographic suffix in Eras 1–4 columns is literally `Native Amer/Alaskan Native` (note the `/` and the capitalized `Amer`). The string is identical across all 4 metric columns for this demographic. Map with care during the wide-to-tidy melt — splitting column names on space alone will not work.

9. **Detail level detection**:
   - Eras 1–4 — derive from `SysSchoolID` parsing: `ALL:ALL` = state, `XXX:ALL` = district, else school.
   - Eras 5–8 — explicit `DETAIL_LVL_DESC` column with `"State"`, `"District"`, `"School"`.

10. **State/district sentinel values (Eras 5–8)** — state rows carry `SCHOOL_DSTRCT_CD = "ALL"`, `INSTN_NUMBER = "ALL"`, `SCHOOL_DSTRCT_NM = "All Column Values"`, `INSTN_NAME = "All Column Values"`. District rows carry `INSTN_NUMBER = "ALL"`, `INSTN_NAME = "All Column Values"`. Use `null_aggregate_geography()` from `src/utils/transformers.py` with the education domain rules to null these out properly.

11. **District code format (Eras 5–8)** — primarily 3-digit codes (e.g., `601`); 7-digit charter codes appear in Era 8 (e.g., `7820108` for "State Charter Schools- Mountain Education High School"). Read with `infer_schema_length=0` to preserve leading zeros; only zero-pad codes that are <3 chars (none observed). Leave 7-digit charter codes unchanged.

12. **School code format (Eras 5–8)** — `INSTN_NUMBER` values are always 4 digits in 2024 (e.g., `0103`, `1050`, `5050`). Read with `infer_schema_length=0` to preserve leading zeros. In Eras 1–4 the school codes after the colon split are 3 or 4 chars without leading zeros (e.g., `103` not `0103`); apply `.str.zfill(4)` to align with Eras 5–8.

13. **Percentage scale** — all `5 or Fewer Days Absent ...`, `6 to 15 Days Absent ...`, `More than 15 Days Absent ...`, `FIVE_OR_FEWER_PERCENT_*`, `SIX_TO_FIFTEEN_PERCENT_*`, `OVER_15_PERCENT_*`, and `CHRONIC_ABSENT_PERC_*` columns are 0–100. Per `data-cleaning-standards`, divide by 100 to produce 0–1 scale in gold.

14. **`Number of Students` / `STUDENT_COUNT` are integer counts, not percentages** — keep at original scale and cast to int (or Int64 for the state row which can exceed 1.7M).

15. **`GRADES_SERVED_DESC` (Eras 5–8)** — comma-separated grade list (e.g., `"PK,KK,01,02,03,04,05"`) describing which grades the school serves. School metadata, not an attendance metric. Drop from gold fact table; optionally surface as a schools dimension attribute.

16. **`#RPT_NAME` column (Era 8)** — the `#` prefix is part of the literal column name. Polars `read_csv` reads it correctly without special handling. The value is constant `"Attendance"` and should be dropped from gold.

17. **`LONG_SCHOOL_YEAR` parsing (Eras 5–8)** — format `"YYYY-YY"` (e.g., `"2023-24"`). The canonical gold `year` is the **ending calendar year**. Parse via `.str.split('-').list.get(0).cast(Int32) + 1` or take the 4-digit prefix and add 1. In every Era 5–8 file, `LONG_SCHOOL_YEAR` end year equals the filename year exactly.

18. **Filename year for Eras 1–4 (no year column)** — the filename year is the school year ending year (same convention as Eras 5–8). `attendance_2010.xls` covers school year 2009-10. Confirmed by year-over-year change in school enrollment for the same INSTN_NUMBER.

19. **Three absentee tiers + chronic absence are not redundant** — `5 or Fewer + 6 to 15 + More than 15` should sum to ~100% per row (it's a partition of the student population by absence count). `CHRONIC_ABSENT_PERC` is a separate measure (the federal "10% or more of enrolled days" definition) and is **not** equal to `OVER_15_PERCENT` — they overlap but use different cutoffs. Keep all four metrics.

20. **`HISPANI` is a literal column-name suffix, not a typo** — Eras 5–8 use `STUDENT_COUNT_HISPANI`, `FIVE_OR_FEWER_PERCENT_HISPANI`, etc. The bronze files genuinely truncate `HISPANIC` to `HISPANI`. Treat this as a data quirk and add `HISPANI` to demographic aliases.

## Gold Schema Classification

### Eras 1–4 (wide format — must be unpivoted)

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| SysSchoolID / sysschoolid / SchoolID | fact_key | district_code, school_code | Split on `:` → `district_code` (3-digit), `school_code` (zfill 4); `"ALL"` → null |
| School Name / schoolname | dimension_attribute | — | Goes to districts/schools dimensions; `"State of Georgia"` for state row |
| Number of Students {demographic} | fact_metric | num_students | Int count; null in 2004 when demographic had zero students |
| 5 or Fewer Days Absent {demographic} | fact_metric | five_or_fewer_days_absent_pct | 0–100; convert to 0–1 in gold |
| 6 to 15 Days Absent {demographic} | fact_metric | six_to_fifteen_days_absent_pct | 0–100; convert to 0–1 in gold |
| More than 15 Days Absent {demographic} | fact_metric | over_15_days_absent_pct | 0–100; convert to 0–1 in gold |
| (demographic embedded in column name) | fact_key | demographic | Normalize via `normalize_demographic_column()` |
| (year from filename) | fact_key | year | Int32; calendar year = filename year |

CHRONIC_ABSENT_PERC is **not available** in Eras 1–4 — emit null in gold for these years.

### Eras 5–8 (tidy long format)

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| #RPT_NAME | not_in_gold | — | Constant `"Attendance"` (Era 8 only); drop |
| LONG_SCHOOL_YEAR | fact_key | year | Int32; parse `"YYYY-YY"` → ending calendar year |
| DETAIL_LVL_DESC | not_in_gold | — | Implicit in output partition (states / districts / schools parquet files) |
| SCHOOL_DSTRCT_CD | fact_key | district_code | Utf8; preserve leading zeros via `infer_schema_length=0`; `"ALL"` → null; FK to districts dimension |
| SCHOOL_DSTRCT_NM | dimension_attribute | — | `district_name` in districts dimension; `"All Column Values"` → null |
| INSTN_NUMBER | fact_key | school_code | Utf8; 4-digit zero-padded; `"ALL"` → null; FK to schools dimension |
| INSTN_NAME | dimension_attribute | — | `school_name` in schools dimension; `"All Column Values"` → null |
| GRADES_SERVED_DESC | not_in_gold | — | School metadata, not an attendance metric (alternatively: schools dimension attribute) |
| STUDENT_COUNT_{DEMO} | fact_metric | num_students | Int count; `"TFS"`/null → null |
| FIVE_OR_FEWER_PERCENT_{DEMO} | fact_metric | five_or_fewer_days_absent_pct | 0–100; `"TFS"`/null → null; convert to 0–1 in gold |
| SIX_TO_FIFTEEN_PERCENT_{DEMO} | fact_metric | six_to_fifteen_days_absent_pct | 0–100; `"TFS"`/null → null; convert to 0–1 in gold |
| OVER_15_PERCENT_{DEMO} | fact_metric | over_15_days_absent_pct | 0–100; `"TFS"`/null → null; convert to 0–1 in gold |
| CHRONIC_ABSENT_PERC_{DEMO} | fact_metric | chronic_absent_pct | 0–100; `"TFS"`/null → null; convert to 0–1 in gold; **absent in Era 6 (2012–2017)** — emit null. Era 5 (2011) has the column but it is ~99% null — emit null for 2011 too. |
| (DEMO suffix in metric column name) | fact_key | demographic | Normalize via `normalize_demographic_column()`; `HISPANI` → `hispanic`, `INDIAN` → `native_american`, etc. |
