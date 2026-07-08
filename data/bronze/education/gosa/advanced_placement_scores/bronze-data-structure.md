# advanced_placement_ap_scores — Bronze Data Structure

## Overview

- Topic: advanced_placement_ap_scores
- Source: gosa
- Files: 21 files spanning 2004–2024
- Unreadable files: none (but `2005.csv` is an XLS binary file mislabeled with the `.csv` extension — must be read with an Excel reader, not `pl.read_csv`)
- Year representation: Eras A–C (2004–2010) have **no** year column (year derived from filename only); Eras D–E (2011–2024) have a `LONG_SCHOOL_YEAR` column formatted as `"YYYY-YY"` (e.g., `"2023-24"`)
- Filename-to-data year offset: filename year = ending calendar year of the school year (e.g., `advanced_placement_ap_scores_2024.csv` contains `LONG_SCHOOL_YEAR = "2023-24"`; in every tidy-era file checked, the year value matches the filename year)
- Detail levels: state, district, school (all eras include all three levels)
- Percentage scale: not applicable in bronze — no rate/percentage column is provided in the modern (Eras D–E) tidy data; the legacy wide eras (A–C) include `Percentage of Test Scores 3 or Higher` on a 0–100 scale, which the gold transform should recompute from counts to keep the metric available across all eras
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| advanced_placement_ap_scores_2004.csv | ca273ef759e72bc28b5b4b5222422fec7b23eff62707bf2c6fa0f2f0703d2e08 |
| advanced_placement_ap_scores_2005.csv | 70956eb009a5335cb4c762cd2fc42c82cb7082fd1142c6e7972150c925f556ea |
| advanced_placement_ap_scores_2006.xls | 9161ae0c21bc1e93989b0d5e0c24e2bc2ae1df1b5658860aa4e8acc416ab9402 |
| advanced_placement_ap_scores_2007.xls | e6d6e41d3722e8d0a7c454d533eb9c4c03c92891fa8e5bff32fa56c12432f049 |
| advanced_placement_ap_scores_2008.xls | 085051015aaafdbf1cb82c27d865567184d183659fd6fb9ec674bb2435e4008e |
| advanced_placement_ap_scores_2009.xls | 03cb3188b330bfc9760cd6dcc000c5fc469a7cdc1659761796cf431b080615a7 |
| advanced_placement_ap_scores_2010.xls | d8245f350f072d52c9a4449236fe63f8be28e5d5a635af368a0c0efce8bb7107 |
| advanced_placement_ap_scores_2011.csv | 4ee2b0d0b01b10854d2143e461a316f4ace6ba3490f82bb0de7261dbf556fc89 |
| advanced_placement_ap_scores_2012.csv | a1f0e6f5716dab6fde46efce904cfe4db97a86877e2deda3c13ee32208a406e4 |
| advanced_placement_ap_scores_2013.csv | 7b8a5ab7d810e8ca1cdc22d9a23a7767499a61f5420a9e49007cf107aac85987 |
| advanced_placement_ap_scores_2014.csv | 65a41b9b7f8bedc0a06753607e120c639f43dbc6c82ed7f5cdbe3adcba8db716 |
| advanced_placement_ap_scores_2015.csv | 816e85b10725400b316b3d36556748597a149b38eae8ef2a78831815ad404b52 |
| advanced_placement_ap_scores_2016.csv | 4ccd0914019fa791084ea278440b2c5d783cd279ba90b3bce7fe8e3ca8692635 |
| advanced_placement_ap_scores_2017.csv | 1a50148eeec06f6e8414be5b691319e1ddbb288b0f6f96fbfb295a059af361dc |
| advanced_placement_ap_scores_2018.csv | 461fce34671575af967d6ed52f45f00312bc637b1928da770ed5bf208dd5aff9 |
| advanced_placement_ap_scores_2019.csv | 61de12a44a9697de780e9d74d415e7c4e8bd8fc89f5f3b15328d61ceb46bba58 |
| advanced_placement_ap_scores_2020.csv | f2d7ede26291d8dff6bb75459be24265413e070dbc4e1b409cbdfcff680616f7 |
| advanced_placement_ap_scores_2021.csv | 95bb80cefb6f0e9143e28e4569fd257733f271ed996343910ee575e74590b647 |
| advanced_placement_ap_scores_2022.csv | e781209c6385bdeb1c877264e86a654794c1bb223d0e7ac45ccf728b6a701f16 |
| advanced_placement_ap_scores_2023.csv | 34552e4c6395675cc474bd0e95aac0631beb3ecdae8c261f285a930c4edb03ae |
| advanced_placement_ap_scores_2024.csv | 5a3e0508e66cbcaf653c6cd971f52c1a3bdee1907f20055cf7ed49fef6342af6 |

## Excel Sheet Structure

All five `.xls` files (and the mislabeled `2005.csv`) follow Excel's default workbook layout: one populated data sheet plus two empty placeholder sheets that should be ignored. The data sheet name varies — the transform must select by `sheet_id=0` (or by name with an explicit lookup) rather than hard-coding `"Sheet1"`.

| File(s) | Sheets | Notes |
|---------|--------|-------|
| 2005.csv, 2006.xls, 2007.xls, 2010.xls | Sheet1 (Data), Sheet2 (empty), Sheet3 (empty) | XLS binary files; `2005.csv` is mislabeled with `.csv` extension (magic bytes `d0cf11e0a1b11ae1` confirm OLE compound format). Read with `pl.read_excel(engine='calamine')` or `xlrd.open_workbook` |
| 2008.xls, 2009.xls | AP (Data), Sheet2 (empty), Sheet3 (empty) | The data sheet is renamed from `Sheet1` to `AP`. Same row layout as the Sheet1 files, but transforms that hard-code the sheet name will skip these years |

CSV files (2004, 2011–2024) are single-table and do not have the sheet concept.

## Summary

Number of Advanced Placement (AP) exams taken by Georgia high-school students and the number of those exams that scored 3 or higher (College Board's "qualifying" threshold). Each row reports three counts for a given entity (state, district, or school):

- **Number of students taking tests** — distinct students who sat for at least one AP exam in the school year
- **Number of tests taken** — total exams administered (a student can take multiple subjects)
- **Number of tests scored 3 or higher** — count of those exams that earned a qualifying score (3 / 4 / 5)

Eras D–E (2011–2024) additionally break the metrics down by **AP subject** (`TEST_CMPNT_TYP_NM`, e.g., `Calculus A`, `Eng. Language & Comp`, `Computer Science Principles`) with a special `ALL Subjects` row that aggregates across subjects. The legacy eras (2004–2010) report only the `ALL Subjects` totals — there is no per-subject breakdown for those years.

There is **no demographic breakdown** in any era. The dataset captures participation and qualifying-score counts only; no race, gender, economic-status, or other subgroup splits.

A pass-rate / percentage column is **not** present in the modern eras — it only appeared in Eras A–C (`Percentage of Test Scores 3 or Higher`, 0–100 scale). The transform should recompute the pass rate from `(num_tests_3_or_higher / num_tests_taken)` so the metric is consistent across all eras.

## Eras

### Era A: 2004–2007 (wide format, no per-subject breakdown)

Files: `advanced_placement_ap_scores_2004.csv`, `advanced_placement_ap_scores_2005.csv` (actually XLS), `advanced_placement_ap_scores_2006.xls`, `advanced_placement_ap_scores_2007.xls`

6 columns. One row per entity (school, district, or state) with the AP totals across all subjects.

| Column | Description |
|--------|-------------|
| SysSchoolID | Compound `"{district}:{school}"` key (e.g., `"601:2050"` for school, `"601:ALL"` for district aggregate, `"ALL:ALL"` for state). District is 3 digits; school is a 3- or 4-digit institution number; `"ALL"` is the aggregation sentinel for both positions. |
| SchoolNme | Entity name — school name for school rows, district name for `XXX:ALL` rows, `"State of Georgia"` (or `"State Of Georgia"` in 2004) for `ALL:ALL` |
| Number of Students Taking Tests | Distinct students who took at least one AP exam (Int) |
| Number of Tests Taken | Total exams administered (Int) |
| Number of Test Scores 3 or Higher | Exams scoring 3 or higher (Int; populated for most 2004 rows — 367 / 414 non-null with 47 nulls) |
| Percentage of Test Scores 3 or Higher | Pass rate as percentage 0–100 (Float; populated for most 2004 rows — 367 / 414 non-null with 47 nulls) |

#### Sample Data (2007, representative)

```
shape: (553, 6)
┌─────────────┬─────────────────────────┬──────────┬───────────┬───────────┬──────────────┐
│ SysSchoolID │ SchoolNme               │ #Students│ #Tests    │ #Tests 3+ │ Pct Tests 3+ │
╞═════════════╪═════════════════════════╪══════════╪═══════════╪═══════════╪══════════════╡
│ 601:103     │ Appling County HS       │ 17       │ 17        │ 12        │ 70.6         │
│ 601:ALL     │ Appling County          │ 17       │ 17        │ 12        │ 70.6         │
│ 799:1893    │ AAS for the Deaf        │ 0        │ 0         │ 0         │ ""           │
│ 799:ALL     │ State Schools           │ 0        │ 0         │ ""        │ ""           │
│ ALL:ALL     │ State of Georgia        │ 43027    │ 67705     │ 35676     │ 52.7         │
└─────────────┴─────────────────────────┴──────────┴───────────┴───────────┴──────────────┘
```

#### Statistics

Row counts and detail-level mix per file:

| File | Rows | State | District | School |
|------|------|-------|----------|--------|
| 2004.csv | 414 | 1 | 133 | 279 (plus a trailing junk row with empty SysSchoolID; only ~280 schools/districts have any AP students; the row count is much smaller than the modern era because most schools without AP participation are absent) |
| 2005.csv | 403 | 1 | 128 | 274 |
| 2006.xls | 543 | 1 | 177 | 365 |
| 2007.xls | 553 | 1 | 177 | 375 |

After casting `Percentage of Test Scores 3 or Higher` to Float64 (2007), values range 0.0 – 100.0 with the state row at 52.7. `Number of Tests Taken` for the state row ranges 39,549 (2004) → 67,705 (2007), reflecting growth in AP participation.

#### Null Counts (2007)

| Column | Nulls (out of 553) |
|--------|--------------------|
| SysSchoolID | 0 |
| SchoolNme | 5 |
| Number of Students Taking Tests | 0 |
| Number of Tests Taken | 0 |
| Number of Test Scores 3 or Higher | 38 (mostly state-school rows where the value is reported as blank) |
| Percentage of Test Scores 3 or Higher | 107 (rows where total tests = 0 leave the rate blank) |

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| SysSchoolID | 414 unique in 2004, 553 unique in 2007 — format `{3-digit district}:{school code}` or `XXX:ALL` for district aggregate or `ALL:ALL` for state |
| SchoolNme | School / district names; `"State of Georgia"` (2007), `"State Of Georgia"` (2004 — capital `O`), and `"State Schools"` for the GA-state-schools aggregate (Schools for the Deaf, Academy for the Blind) |

#### Suppression Markers

- **2004**: blanks (nulls) appear in `Number of Tests Taken`, `Number of Test Scores 3 or Higher`, and `Percentage of Test Scores 3 or Higher` for 47 of 414 rows (367 non-null in each column). The remaining ~88% of rows do carry numeric values — 2004 is **not** participation-only. As in 2005–2007, blanks coincide with entities where the test count would be zero or below the reporting threshold; no string suppression markers.
- **2005–2007**: blanks (nulls) appear in `Number of Test Scores 3 or Higher` and `Percentage of Test Scores 3 or Higher` for entities with `Number of Tests Taken == 0`. No string suppression markers — the source uses empty cells (which Polars reads as null).

---

### Era B: 2008–2009 (wide format with separate System Name column)

Files: `advanced_placement_ap_scores_2008.xls`, `advanced_placement_ap_scores_2009.xls`

7 columns — adds a separate `System Name` column between the ID and the school name. Suppression appears as the explicit string `"Too Few Students"`.

| Column | Description |
|--------|-------------|
| SysSchoolid | Same `"{district}:{school}"` key as Era A (note the lowercase `i` in `Sysschoolid`/`SysSchoolid` — case differs from Era A's `SysSchoolID`). 2009 zero-pads the school portion to 4 digits (`"601:0103"`); 2008 does not (`"601:103"`). |
| System Name | District name (e.g., `"Appling County"`); `"ALL Systems"` for the state row |
| School Name | School name; `"All Schools"` for the district aggregate (`XXX:ALL`) and state row; some 2009 names are upper-cased (e.g., `"APPLING COUNTY HIGH SCHOOL"`) |
| Number of Students Taking Tests | Int |
| Number of Tests Taken | Int or `"Too Few Students"` |
| Number of Test Scores 3 or Higher | Int or `"Too Few Students"` |
| Percentage of Test Scores 3 or Higher | Float (0–100) or `"Too Few Students"` |

#### Sample Data (2008, representative)

```
shape: (492, 7)
┌─────────────┬──────────────┬──────────────────────────┬──────────┬────────────────┬────────────────┬────────────────┐
│ SysSchoolid │ System Name  │ School Name              │ #Students│ #Tests         │ #Tests 3+      │ Pct Tests 3+   │
╞═════════════╪══════════════╪══════════════════════════╪══════════╪════════════════╪════════════════╪════════════════╡
│ 601:103     │ Appling Co.  │ Appling County HS        │ 27       │ 27             │ 15             │ 55.56          │
│ 603:302     │ Bacon Co.    │ Bacon County HS          │ 3        │ Too Few Students│ Too Few Students│ Too Few Students│
│ 795:103     │ CCAT         │ CCAT School              │ 1        │ Too Few Students│ Too Few Students│ Too Few Students│
│ ALL:ALL     │ ALL Systems  │ All Schools              │ 50073    │ 79781          │ 40420          │ 50.66          │
└─────────────┴──────────────┴──────────────────────────┴──────────┴────────────────┴────────────────┴────────────────┘
```

#### Statistics

| Year | Rows | State | District | School |
|------|------|-------|----------|--------|
| 2008 | 492 | 1 | 167 | 324 |
| 2009 | 516 | 1 | 175 | 340 |

State row in 2008: 50,073 students / 79,781 tests / 40,420 qualifying / 50.66 % pass rate.

#### Null Counts (2008)

All 7 columns: **0 nulls**. Suppression is fully encoded by `"Too Few Students"`.

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| SysSchoolid | 491 unique (2008); same format as Era A |
| System Name | 156 districts + `"ALL Systems"` (2008) |
| School Name | 331 unique (2008); `"All Schools"` is the aggregate sentinel |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| Number of Tests Taken | `Too Few Students` (37 occurrences in 2008; 32 in 2009) |
| Number of Test Scores 3 or Higher | `Too Few Students` |
| Percentage of Test Scores 3 or Higher | `Too Few Students` |

`Number of Students Taking Tests` is never suppressed (the count of test-takers itself is always reported, even when downstream metrics are masked).

---

### Era C: 2010 (wide format, no separate System Name)

Files: `advanced_placement_ap_scores_2010.xls`

6 columns — drops the `System Name` column reintroduced in Era B and combines school + district names into a single `School or Distict Name` column (note the misspelling `Distict`). Suppression continues with `"Too Few Students"`.

| Column | Description |
|--------|-------------|
| Sysschoolid | `"{district}:{school}"` key (lowercase `s` everywhere this time) |
| School or Distict  Name | Entity name — school for school rows, district for `XXX:ALL`, `"State of Georgia"` for `ALL:ALL` (column header literally has two spaces between `Distict` and `Name`) |
| Number of Students Taking Tests | Int |
| Number of Tests Taken | Int or `"Too Few Students"` |
| Number of Test Scores 3 or Higher | Int or `"Too Few Students"` |
| Percentage of Test Scores 3 or Higher | Float (0–100) or `"Too Few Students"` |

#### Sample Data (2010)

```
shape: (524, 6)
┌─────────────┬─────────────────────────────┬──────────┬────────────────┬────────────────┬────────────────┐
│ Sysschoolid │ School or Distict  Name     │ #Students│ #Tests         │ #Tests 3+      │ Pct Tests 3+   │
╞═════════════╪═════════════════════════════╪══════════╪════════════════╪════════════════╪════════════════╡
│ 601:103     │ Appling County HS           │ 28       │ 28             │ 17             │ 60.7           │
│ 603:302     │ Bacon County HS             │ 3        │ Too Few Students│ Too Few Students│ Too Few Students│
│ 793:273     │ Vidalia Comprehensive HS    │ 31       │ 55             │ 25             │ 45.5           │
│ ALL:ALL     │ State of Georgia            │ 63923    │ 104505         │ 52679          │ 50.4           │
└─────────────┴─────────────────────────────┴──────────┴────────────────┴────────────────┴────────────────┘
```

#### Statistics

- 2010: 524 rows (1 state + 173 district + 350 school)
- State row: 63,923 students / 104,505 tests / 52,679 qualifying / 50.4 % pass rate

#### Null Counts (2010)

All 6 columns: **0 nulls**. Suppression handled entirely by `"Too Few Students"`.

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| Sysschoolid | 524 unique; same format as Era A/B |
| School or Distict  Name | 518 unique entity names |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| Number of Tests Taken | `Too Few Students` (33 occurrences) |
| Number of Test Scores 3 or Higher | `Too Few Students` |
| Percentage of Test Scores 3 or Higher | `Too Few Students` |

---

### Era D: 2011–2022 (tidy format with per-subject breakdown)

Files: `advanced_placement_ap_scores_2011.csv` through `advanced_placement_ap_scores_2022.csv`

9 columns. Tidy / long format — each row is one entity × one subject. The `ALL Subjects` value of `TEST_CMPNT_TYP_NM` provides the cross-subject totals that match Eras A–C. **No `Percentage of Test Scores 3 or Higher` column** in this era.

| Column | Description |
|--------|-------------|
| LONG_SCHOOL_YEAR | School year string (e.g., `"2010-11"`, `"2021-22"`) — single value per file |
| SCHOOL_DISTRCT_CD | 3-digit district code (e.g., `"721"`) or 7-digit charter code (e.g., `"7820412"`); `"DISTRICT_ALL"` for state rows |
| SCHOOL_DSTRCT_NM | District name; `"DISTRICT_ALL"` (no separate name) for state rows |
| INSTN_NUMBER | 4-digit school code; `"SCHOOL_ALL"` for district rows; `"DISTRICT_ALL"` for state rows |
| INSTN_NAME | School name; `"SCHOOL_ALL"` for district rows; `"DISTRICT_ALL"` for state rows |
| TEST_CMPNT_TYP_NM | AP subject name (e.g., `"Calculus A"`, `"Eng. Language & Comp"`) — `"ALL Subjects"` is the cross-subject aggregate |
| NUMBER_OF_STUDENTS_TESTED | Number of distinct students who sat the subject exam — string with numeric value or `"TFS"` (2011–2015 and 2019–2022 only; 2016–2018 publish fully unsuppressed counts down to n=1) |
| NUMBER_TESTS_TAKEN | Number of exams administered — string with numeric value, `"TFS"` (2020–2022), or an **empty cell** (the only suppression form in this column 2011–2019, ~2,040–2,538 rows/yr) |
| NOTESTS_3ORHIGHER | Number of exams scoring 3+ — string with numeric value, `"TFS"` (2020–2022), or an **empty cell** (the only suppression form in this column 2011–2019, ~2,360–2,813 rows/yr; 2020–2022 additionally have 70/132/160 residual empty cells) |

All columns are read as `String` when using `infer_schema_length=0` (and naturally so when `"TFS"` is present); metric columns must be cast to `Float64`/`Int64` after suppression handling.

#### Sample Data (2022)

```
shape: (7317, 9)
┌──────────────────┬───────────────────┬─────────────────────────┬──────────────┬──────────────────────────┬─────────────────────────┬───────────────────────────┬────────────────────┬───────────────────┐
│ LONG_SCHOOL_YEAR │ SCHOOL_DISTRCT_CD │ SCHOOL_DSTRCT_NM        │ INSTN_NUMBER │ INSTN_NAME               │ TEST_CMPNT_TYP_NM       │ NUMBER_OF_STUDENTS_TESTED │ NUMBER_TESTS_TAKEN │ NOTESTS_3ORHIGHER │
╞══════════════════╪═══════════════════╪═════════════════════════╪══════════════╪══════════════════════════╪═════════════════════════╪═══════════════════════════╪════════════════════╪═══════════════════╡
│ 2021-22          │ 726               │ Griffin-Spalding County │ SCHOOL_ALL   │ SCHOOL_ALL               │ Computer Science Princ. │ 17                        │ 17                 │ 5                 │
│ 2021-22          │ 633               │ Cobb County             │ 0373         │ Sprayberry HS            │ World History           │ 60                        │ 60                 │ 49                │
│ 2021-22          │ 625               │ Savannah-Chatham County │ SCHOOL_ALL   │ SCHOOL_ALL               │ Japanese Lang. & Cult.  │ TFS                       │ TFS                │ TFS               │
│ 2021-22          │ 710               │ Paulding County         │ 0292         │ East Paulding HS         │ Calculus A              │ TFS                       │ TFS                │ TFS               │
│ 2021-22          │ 673               │ Hart County             │ 3050         │ Hart County HS           │ Biology                 │ 45                        │ 45                 │ 6                 │
└──────────────────┴───────────────────┴─────────────────────────┴──────────────┴──────────────────────────┴─────────────────────────┴───────────────────────────┴────────────────────┴───────────────────┘
```

#### Statistics

Per-year row counts (Era D):

| Year | Rows | LONG_SCHOOL_YEAR |
|------|------|------------------|
| 2011 | 6,262 | 2010-11 |
| 2012 | 6,719 | 2011-12 |
| 2013 | 7,015 | 2012-13 |
| 2014 | 7,232 | 2013-14 |
| 2015 | 7,366 | 2014-15 |
| 2016 | 7,504 | 2015-16 |
| 2017 | 7,457 | 2016-17 |
| 2018 | 7,415 | 2017-18 |
| 2019 | 7,240 | 2018-19 |
| 2020 | 7,054 | 2019-20 |
| 2021 | 7,312 | 2020-21 |
| 2022 | 7,317 | 2021-22 |

After casting metric columns to Float64 in 2022:

- `NUMBER_OF_STUDENTS_TESTED` range: 10 – 78,718 (mean 132); 4,960 numeric / 2,357 `"TFS"`
- `NUMBER_TESTS_TAKEN` range: 10 – 142,717 (mean 171); 4,960 numeric / 2,357 `"TFS"`
- `NOTESTS_3ORHIGHER` range: 1 – 88,345; 4,800 numeric / 2,357 `"TFS"` / 160 empty cells. (Correction 2026-06-11, measured by raw re-read of every Era D file: empty-cell suppression in this column is NOT 2020-only — it is the *dominant* form for 2011–2019, 2,360–2,813 rows/yr with zero `"TFS"` in those years, and persists residually alongside TFS in 2020/2021/2022 with 70/132/160 rows respectively.)

The minimum count of 10 (rather than 1) reflects the GOSA suppression policy: cells with fewer than 10 students/tests are masked as `"TFS"`. **Exception (measured 2026-06-11): 2016–2018 publish `NUMBER_OF_STUDENTS_TESTED` fully unsuppressed (zero TFS, zero empty cells; minimum value 1)** — the n<10 floor applies to the other Era D years only.

#### Null Counts (2022)

All 9 columns: **0 string-level nulls** (every cell has a value or `"TFS"`). After casting metric columns to numeric, ~2,357 rows return null due to `"TFS"`.

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| LONG_SCHOOL_YEAR | One value per file |
| SCHOOL_DSTRCT_NM | 142 districts in 2022 (top: Gwinnett 575, Cobb 443, Fulton 416, DeKalb 307); `"DISTRICT_ALL"` is the state-row sentinel |
| INSTN_NAME | 348 schools in 2022; `"SCHOOL_ALL"` is the district sentinel; `"DISTRICT_ALL"` is the state sentinel |
| TEST_CMPNT_TYP_NM | 38 subjects in 2022 (range across the era: 34 in 2011 → 36 in 2017–2020 → 38 in 2022). `"ALL Subjects"` is present every year and provides the cross-subject totals matching the legacy eras. |

The 38 subjects in 2022: `ALL Subjects`, `Eng. Language & Comp`, `U.S. History`, `Eng. Literature & Comp`, `World History`, `Calculus A`, `Biology`, `Environmental Science`, `Gov. & Pol. U.S.`, `Psychology`, `Statistics`, `Geography: Human`, `Chemistry`, `Physics 1`, `Economics: Micro`, `Computer Science Principles`, `Spanish Language`, `Art: Studio 2-D Design`, `Calculus BC`, `Computer Science A`, `Economics: Macro`, `Art: Studio Drawing`, `Music Theory`, `Capstone`, `Physics C: Mechanics`, `European History`, `Capstone Research`, `Art History`, `French Language`, `Art: Studio 3-D Design`, `Gov. & Pol. Comp`, `Physics C: Elec & Magnetism`, `Chinese Lang. & Culture`, `Physics 2`, `Latin: Vergil`, `Spanish Literature`, `German Language`, `Japanese Lang. & Culture`.

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| SCHOOL_DISTRCT_CD | `DISTRICT_ALL` (state-row sentinel) |
| INSTN_NUMBER | `SCHOOL_ALL` (district-row sentinel), `DISTRICT_ALL` (state-row sentinel) |
| NUMBER_OF_STUDENTS_TESTED | `TFS` (Too Few Students) — 2011–2015 and 2019–2022 (2,040–2,644/yr); **2016–2018 have no suppression at all in this column** (zero TFS, zero empty; min value 1) |
| NUMBER_TESTS_TAKEN | **Empty cells** are the only suppression 2011–2019 (2,040–2,538/yr; zero TFS in those years); `TFS` 2020–2022 (2,399/2,644/2,357) |
| NOTESTS_3ORHIGHER | **Empty cells** are the only suppression 2011–2019 (2,360–2,813/yr; zero TFS in those years); `TFS` 2020–2022 (2,399/2,644/2,357) plus residual empty cells of 70 (2020), 132 (2021), 160 (2022) |

*(Corrected 2026-06-11 by raw re-read of every Era D file with no null-value handling: the previous claims — "TFS appears 2011–2022", "TFS observed 2011–2014 (rare)", and "2020 also has empty-string for 160 rows (the only year where this happens)" — were wrong. The 160-empty-cell figure belongs to 2022; 2020 has 70.)*

---

### Era E: 2023–2024 (tidy format with #RPT_NAME and DETAIL_LVL_DESC)

Files: `advanced_placement_ap_scores_2023.csv`, `advanced_placement_ap_scores_2024.csv`

11 columns — adds two leading metadata columns (`#RPT_NAME` and `DETAIL_LVL_DESC`), simplifies the `"DISTRICT_ALL"` / `"SCHOOL_ALL"` sentinels to plain `"ALL"`, replaces the sentinel-name strings with descriptive English (`"All Systems"`, `"All Schools"`), and renames `NOTESTS_3ORHIGHER` → `NUMBER_TESTS_3_OR_HIGHER` for clarity.

| Column | Description |
|--------|-------------|
| #RPT_NAME | Always `"AP COUNTS"` — constant report identifier. The `#` prefix is part of the literal column name. |
| LONG_SCHOOL_YEAR | School year string (`"2022-23"` or `"2023-24"`) — single value per file |
| DETAIL_LVL_DESC | Detail-level identifier — six values: `"SCHOOL"`, `"DISTRICT"`, `"STATE"`, plus three `"…ALL SUBJECTS"` variants that mark per-entity subject totals |
| SCHOOL_DISTRCT_CD | 3-digit district code or 7-digit charter code; `"ALL"` for state rows |
| SCHOOL_DSTRCT_NM | District name; `"All Systems"` for state rows |
| INSTN_NUMBER | 4-digit school code; `"ALL"` for district and state rows |
| INSTN_NAME | School name; `"All Schools"` for district and state rows |
| TEST_CMPNT_TYP_NM | AP subject name; `"ALL Subjects"` is the cross-subject aggregate |
| NUMBER_OF_STUDENTS_TESTED | String numeric or `"TFS"` |
| NUMBER_TESTS_TAKEN | String numeric or `"TFS"` |
| NUMBER_TESTS_3_OR_HIGHER | String numeric or `"TFS"` (renamed from `NOTESTS_3ORHIGHER`) |

#### Sample Data (2024)

```
shape: (8553, 11)
┌───────────┬──────────────────┬─────────────────────┬───────────────────┬─────────────────────────┬──────────────┬──────────────────────────┬─────────────────────┬──────────┬──────────┬────────────┐
│ #RPT_NAME │ LONG_SCHOOL_YEAR │ DETAIL_LVL_DESC     │ SCHOOL_DISTRCT_CD │ SCHOOL_DSTRCT_NM        │ INSTN_NUMBER │ INSTN_NAME               │ TEST_CMPNT_TYP_NM   │ #Students│ #Tests   │ #Tests 3+  │
╞═══════════╪══════════════════╪═════════════════════╪═══════════════════╪═════════════════════════╪══════════════╪══════════════════════════╪═════════════════════╪══════════╪══════════╪════════════╡
│ AP COUNTS │ 2023-24          │ SCHOOL ALL SUBJECTS │ 722               │ Rockdale County         │ 0278         │ Conyers Middle School    │ ALL Subjects        │ TFS      │ TFS      │ TFS        │
│ AP COUNTS │ 2023-24          │ SCHOOL ALL SUBJECTS │ 708               │ Oconee County           │ 0293         │ Oconee County HS         │ ALL Subjects        │ 526      │ 1002     │ 887        │
│ AP COUNTS │ 2023-24          │ DISTRICT            │ 625               │ Savannah-Chatham County │ ALL          │ All Schools              │ Spanish Language    │ 27       │ 27       │ 18         │
│ AP COUNTS │ 2023-24          │ SCHOOL              │ 708               │ Oconee County           │ 0105         │ North Oconee HS          │ Precalculus         │ 109      │ 109      │ 108        │
│ AP COUNTS │ 2023-24          │ STATE ALL SUBJECTS  │ ALL               │ All Systems             │ ALL          │ All Schools              │ ALL Subjects        │ ...      │ ...      │ ...        │
└───────────┴──────────────────┴─────────────────────┴───────────────────┴─────────────────────────┴──────────────┴──────────────────────────┴─────────────────────┴──────────┴──────────┴────────────┘
```

#### Statistics

| Year | Rows | LONG_SCHOOL_YEAR |
|------|------|------------------|
| 2023 | 7,938 | 2022-23 |
| 2024 | 8,553 | 2023-24 |

DETAIL_LVL_DESC distribution (2024):

| DETAIL_LVL_DESC | Rows |
|-----------------|------|
| SCHOOL | 5,837 |
| DISTRICT | 2,052 |
| SCHOOL ALL SUBJECTS | 480 |
| DISTRICT ALL SUBJECTS | 143 |
| STATE | 40 |
| STATE ALL SUBJECTS | 1 |

After casting to Float64 (2024):

- `NUMBER_OF_STUDENTS_TESTED` range: 10 – 98,135 (mean 146); 5,867 numeric / 2,686 `"TFS"`
- `NUMBER_TESTS_TAKEN` range: 10 – 190,946 (mean 194); 5,867 numeric / 2,686 `"TFS"`
- `NUMBER_TESTS_3_OR_HIGHER` range: 10 – 131,555 (mean 175); 4,441 numeric / 4,112 `"TFS"`

Note that the qualifying-score column is suppressed almost twice as often as the test-count columns — this matches the GOSA convention of independently masking each metric below its 10-student/10-test threshold.

#### Null Counts (2024)

All 11 columns: **0 string-level nulls**. After casting, `"TFS"` becomes null in metric columns.

#### Categorical Columns

| Column | Distinct Values (2024) |
|--------|------------------------|
| #RPT_NAME | `AP COUNTS` (constant) |
| LONG_SCHOOL_YEAR | `2023-24` |
| DETAIL_LVL_DESC | `SCHOOL`, `DISTRICT`, `STATE`, `SCHOOL ALL SUBJECTS`, `DISTRICT ALL SUBJECTS`, `STATE ALL SUBJECTS` (6 values; the `… ALL SUBJECTS` variants are the per-entity cross-subject aggregates) |
| SCHOOL_DSTRCT_NM | 144 districts + `"All Systems"` |
| INSTN_NAME | 473 schools + `"All Schools"` |
| TEST_CMPNT_TYP_NM | 41 subjects in 2024 (38 from 2022 + `Precalculus` + `African American Studies` + `Italian Lang. & Culture`); `Italian Lang. & Culture` only has 3 rows in 2024 |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| SCHOOL_DISTRCT_CD | `ALL` (state-row sentinel) |
| INSTN_NUMBER | `ALL` (district and state sentinel) |
| NUMBER_OF_STUDENTS_TESTED | `TFS` |
| NUMBER_TESTS_TAKEN | `TFS` |
| NUMBER_TESTS_3_OR_HIGHER | `TFS` |

The empty-string-suppression edge case from 2020 (Era D) does **not** recur — every metric cell is either a numeric string or `"TFS"`.

---

## ETL Considerations

1. **File-format issue (2005)** — `advanced_placement_ap_scores_2005.csv` is an XLS binary file mislabeled with the `.csv` extension. `file` reports it as a Composite Document File V2 (OLE compound) document. Read it with `pl.read_excel(path, engine='calamine')` or `xlrd.open_workbook(path)`; `pl.read_csv` returns a malformed-CSV error.

2. **Excel sheet selection (Era A–C, plus 2005)** — the `.xls` (and 2005-XLS) files have three sheets but only one is populated. The data sheet is named `Sheet1` for 2006/2007/2010, `AP` for 2008/2009, and `Sheet1` for the 2005 mislabeled file. Select by `sheet_id=0` (or the first non-empty sheet) rather than hard-coding `"Sheet1"`.

3. **`SysSchoolID` parsing (Eras A–C)** — split on `:` to extract district and school codes. Format: `"{district}:{school}"` where district is a 3-digit code and school is a 3- or 4-digit institution number. `"ALL"` is the aggregation sentinel: `"601:ALL"` = district aggregate, `"ALL:ALL"` = state. Map `"ALL"` to `null` in `district_code` / `school_code` per the cleaning standards.

4. **Column-name drift across legacy eras** — header capitalization and naming changes between years. Era A uses `SysSchoolID` and `SchoolNme`; Era B (2008/2009) uses `SysSchoolid` (lowercase `id`), `System Name`, and `School Name`; Era C (2010) uses `Sysschoolid` and `School or Distict  Name` (note the misspelling and the **double space**). The transform must rename to a common schema before unioning.

5. **2004 has partial blanks in qualifying-score data** — `Number of Tests Taken`, `Number of Test Scores 3 or Higher`, and `Percentage of Test Scores 3 or Higher` are null for 47 of 414 rows in 2004 (367 non-null in each column); the remaining rows carry real numeric values. Treat 2004 like 2005–2007: rows with blank cells emit null metrics; rows with values pass through normally. No string suppression markers in this era.

6. **No demographic breakdown** — unlike most GOSA topics, AP scores has no race / gender / disability / economic status splits. The fact rows should not include a `demographic` column. (Per the data-cleaning-standards skill, omit `demographic` rather than emit a constant `"All Students"` value.)

7. **Suppression varies by era**:
   - **Era A (2004–2007)** — blanks (nulls). 2004 has ~11% blank rows in `Number of Tests Taken` / `Number of Test Scores 3 or Higher` / `Percentage of Test Scores 3 or Higher` (47 of 414 rows); 2005–2007 blanks appear only when total tests = 0.
   - **Eras B–C (2008–2010)** — explicit `"Too Few Students"` string in the three score-related metric columns; `Number of Students Taking Tests` is never suppressed.
   - **Era D (2011–2022)** — mixed forms (corrected 2026-06-11): 2011–2019 suppress `NUMBER_TESTS_TAKEN` / `NOTESTS_3ORHIGHER` via **empty cells** only (~2,000–2,800 rows/yr each; no TFS in those columns) while `NUMBER_OF_STUDENTS_TESTED` uses `"TFS"` in 2011–2015 and 2019 and is fully unsuppressed in 2016–2018; 2020–2022 use `"TFS"` in all three metric columns plus 70/132/160 residual empty cells in `NOTESTS_3ORHIGHER`. All forms become NULL on read/cast.
   - **Era E (2023–2024)** — `"TFS"` string only.

8. **Subject-level vs cross-subject rows (Eras D–E)** — each entity appears multiple times: once per subject plus once with `TEST_CMPNT_TYP_NM = "ALL Subjects"` for the cross-subject total. The legacy eras (A–C) only have the cross-subject totals. The transform should:
   - Either keep `subject` as a `fact_categorical` column (preserving the per-subject breakdown for Eras D–E with `subject = "All Subjects"` for legacy era rows), **or**
   - Filter to `TEST_CMPNT_TYP_NM = "ALL Subjects"` to align all eras and write a separate per-subject fact.
   The per-subject metric is high-value for analysts so retaining it as a `fact_categorical` column is recommended.

9. **`DETAIL_LVL_DESC` granularity (Era E)** — six values, not three. The `… ALL SUBJECTS` variants identify the per-entity cross-subject aggregate rows (e.g., a `SCHOOL ALL SUBJECTS` row is the school's total across all subjects). This is redundant with `(detail_level == "school" AND subject == "ALL Subjects")`. The transform can derive `detail_level` from `DETAIL_LVL_DESC.split(' ')[0]` (lowercased) and ignore the `ALL SUBJECTS` suffix.

10. **Detail-level inference for Era D** — Era D has no `DETAIL_LVL_DESC`; infer it from the sentinel pattern:
    - `SCHOOL_DISTRCT_CD == "DISTRICT_ALL"` AND `INSTN_NUMBER == "DISTRICT_ALL"` → state
    - `SCHOOL_DISTRCT_CD` is a numeric district code AND `INSTN_NUMBER == "SCHOOL_ALL"` → district
    - Both are numeric codes → school

11. **Sentinel string normalization** — across eras the aggregation sentinels are spelled differently and must all map to null:
    - **District code**: `"DISTRICT_ALL"` (Era D) and `"ALL"` (Era E) → null when row is state-level
    - **School code**: `"DISTRICT_ALL"`, `"SCHOOL_ALL"` (Era D) and `"ALL"` (Era E) → null when row is state- or district-level
    - **District name** (in dimension): `"DISTRICT_ALL"` (Era D), `"All Systems"` (Era E), `"ALL Systems"` (Era B 2008–2009), `"State of Georgia"` / `"State Of Georgia"` / `"State Schools"` (Eras A–C) → null in fact, drop from districts dimension
    - **School name** (in dimension): `"SCHOOL_ALL"` / `"DISTRICT_ALL"` (Era D), `"All Schools"` (Era E and Era B), `"State of Georgia"` (Eras A–C `ALL:ALL` rows) → null in fact, drop from schools dimension

12. **District code format** — 3-digit standard codes plus 7-digit charter codes (Era D from 2011 onward, Era E both years). Read with `infer_schema_length=0` to preserve leading zeros, then `.cast(pl.Utf8).str.zfill(3)` (per the education-domain CLAUDE.md). Charter 7-digit codes pass through `zfill(3)` unchanged. Examples observed: `7820119`, `7820412`, `7830103`, `7830310`, `7991893`.

13. **School code format** — `INSTN_NUMBER` is 3- or 4-digit (Era D early years) or always 4-digit (Era E). Cast to Utf8 and `.str.zfill(4)` per the education-domain CLAUDE.md. 2018 onwards is uniformly 4-digit; 2014 mixes 3-digit and 4-digit (3,374 vs 1,737 rows in 2014).

14. **Pass rate not stored in modern bronze** — Eras D–E do not include the `Percentage of Test Scores 3 or Higher` column. To keep the metric available across all eras, recompute `pct_tests_3_or_higher = num_tests_3_or_higher / num_tests_taken` in the transform. Per the data-cleaning-standards skill the resulting rate should be on the 0–1 scale.

15. **`ALL Subjects` row arithmetic does not equal the sum of subject rows** — `NUMBER_OF_STUDENTS_TESTED` for `ALL Subjects` counts distinct students (a student who took both Calculus and Biology counts once), while individual subject rows count subject-level participants. The cross-subject aggregate must be carried as the source provides it; do not derive it by summing subject rows.

16. **`#RPT_NAME` column (Era E)** — the `#` prefix is part of the literal column name. Polars `read_csv` reads it correctly without special handling. The value is always `"AP COUNTS"`; drop in gold.

17. **`LONG_SCHOOL_YEAR` parsing** — format `"YYYY-YY"` (e.g., `"2023-24"`). The canonical gold `year` is the ending calendar year. Parse via `.str.split('-').list.get(0).cast(Int32) + 1` or match the 4-digit prefix and add 1. In every tidy-era file checked, this equals the filename year. For Eras A–C, derive `year` from the filename only.

18. **Per-year row counts grow ~30 %** — bronze counts grow from 6,262 (2011) to 8,553 (2024), driven by both new subjects (Computer Science Principles 2017+, Capstone 2018+, Precalculus 2024+, African American Studies 2024+, Italian 2024+) and broader school participation. No data loss appears between 2022 (7,317) and 2023 (7,938) — the increase reflects the tracked `DETAIL_LVL_DESC` rows being more granular in Era E.

19. **2005 district rollups are misassigned for 8 districts** (discovered at data-review 2026-06-11). The 2005 file's `{d}:ALL` rows for districts 681, 717, 720, 721, 722, 724, 758, 779 publish totals that provably belong to other districts — an alphabetical-adjacency shift plus an exact Jefferson County (681) ↔ Jefferson City (779) swap in GOSA's rollup generation. Proof: 2005 has zero suppression and 120 of 128 district rollups equal their own school-row sums exactly; the 8 exceptions decode by exact three-metric donor matches (717←719 Rabun, 720←721 Richmond, 721←722 Rockdale, 722←785 Rome City — Rome's own rollup is also published correctly, i.e. its totals are served twice; 681↔779 exact swap; 724 Screven published 167/202/111 vs own sums 67/104/51 and 758 Wilkinson published 37/38/14 vs own sums 10/11/0 contradict their own sums with no in-file donor), and the 2004→2006 trend confirms every case (e.g. Rockdale tests 833 → published 97 / own-sums 842 → 950; Randolph students 3 → published 489 → 1). School-level 2005 rows are unaffected. The transform masks all four metrics on these 8 rows per data-cleaning-standards §4b.

## Gold Schema Classification

### Eras A–C (wide format — must be unpivoted to single-subject `ALL Subjects` rows)

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| SysSchoolID / SysSchoolid / Sysschoolid | fact_key | district_code, school_code | Split on `:`; map `"ALL"` to null; zfill 3 / 4 per education-domain CLAUDE.md |
| SchoolNme / SchoolName / School Name / School or Distict  Name | dimension_attribute | — | Goes to schools dimension (school rows) and districts dimension (`XXX:ALL` rows); `"State of Georgia"` rows produce no dimension entry |
| System Name (Era B only) | dimension_attribute | — | Redundant with `SchoolNme` after parsing `SysSchoolID`; goes to districts dimension |
| (year from filename) | fact_key | year | Int32; calendar year = filename year |
| (constant) | fact_categorical | subject | Always `"All Subjects"` for legacy eras |
| Number of Students Taking Tests | fact_metric | num_tested | Int count; populated in 2004 like every other year |
| Number of Tests Taken | fact_metric | num_tests_taken | Int count; 47 / 414 rows null in 2004; `"Too Few Students"` (Eras B/C) → null |
| Number of Test Scores 3 or Higher | fact_metric | num_tests_3_or_higher | Int count; 47 / 414 rows null in 2004; `"Too Few Students"` (Eras B/C) → null |
| Percentage of Test Scores 3 or Higher | not_in_gold | — | Recompute in gold from counts (`num_tests_3_or_higher / num_tests_taken`) so the metric is consistent across all eras |

### Eras D–E (tidy format)

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| #RPT_NAME | not_in_gold | — | Constant `"AP COUNTS"` (Era E only); drop |
| LONG_SCHOOL_YEAR | fact_key | year | Int32; parse `"YYYY-YY"` → ending calendar year |
| DETAIL_LVL_DESC | not_in_gold | — | Implicit in output partition (states / districts / schools parquet files); strip `" ALL SUBJECTS"` suffix to derive `detail_level` (Era E only) |
| SCHOOL_DISTRCT_CD | fact_key | district_code | Utf8; zfill 3 (preserves 7-digit charter codes); `"DISTRICT_ALL"` (D) and `"ALL"` (E) → null; FK to districts dimension |
| SCHOOL_DSTRCT_NM | dimension_attribute | — | `district_name` in districts dimension; `"DISTRICT_ALL"` / `"All Systems"` → null |
| INSTN_NUMBER | fact_key | school_code | Utf8; zfill 4; `"SCHOOL_ALL"` / `"DISTRICT_ALL"` (D) and `"ALL"` (E) → null; FK to schools dimension |
| INSTN_NAME | dimension_attribute | — | `school_name` in schools dimension; `"SCHOOL_ALL"` / `"DISTRICT_ALL"` / `"All Schools"` → null |
| TEST_CMPNT_TYP_NM | fact_categorical | subject | Snake-case-normalized AP subject (`all_subjects`, `calculus_a`, `eng_language_comp`, …). Carries the per-subject breakdown; `ALL Subjects` rows are the cross-subject aggregate |
| NUMBER_OF_STUDENTS_TESTED | fact_metric | num_tested | Int count; `"TFS"` → null |
| NUMBER_TESTS_TAKEN | fact_metric | num_tests_taken | Int count; `"TFS"` → null |
| NOTESTS_3ORHIGHER (D) / NUMBER_TESTS_3_OR_HIGHER (E) | fact_metric | num_tests_3_or_higher | Int count; `"TFS"` and empty cells (2011–2022, see Suppression Markers) → null |
| (derived) | fact_metric | pct_tests_3_or_higher | `num_tests_3_or_higher / num_tests_taken`, 0–1 scale; null when either count is null or `num_tests_taken == 0`. (Named per the §16 share-of-denominator `pct_*` convention; an earlier draft called it `pass_rate`.) |
