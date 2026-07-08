# georgia_student_growth_model_end_of_grade - Bronze Data Structure

## Overview

- Topic: georgia_student_growth_model_end_of_grade
- Source: georgiainsights
- Files: 18 files covering 2015-2019 and 2023 (no 2020-2022 files). Three files per year (state / system / school); 2015-2019 use the `GSGM_EOG_YYYY_...` naming convention, 2023 uses the `SGP_EOG_Aggs_..._2023` naming convention.
- Unreadable files: none
- Year representation: Year appears only in the filename and in the sheet-title banner row (e.g., `GSGM Georgia Milestones EOG 2019, All Students by School, All Grades`, or for 2023 `Student Growth Percentile (SGP) Spring 2023 Georgia Milestones End-of-Grade Assessment ...`). There is no `year` column inside the data. "Spring YYYY" refers to the school year ending in that calendar year (e.g., `Spring 2023` = the 2022-2023 school year).
- Filename-to-data year offset: same (filename year = data year; no `year` column to compare against).
- Detail levels: state, district (system), school — each published in a separate file.
- Percentage scale: All `%` columns are 0-100. 2015-2018 percentages are integer-valued (`94`); 2019 and 2023 are decimal-valued (`94.003428`). Median SGP is on a 0-100 scale (it is a percentile rank).
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: Georgia Insights (GaDOE) public data downloads — exact page URL not recorded at acquisition time
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| GSGM_EOG_2015_School.xls | ea119646ce345c250e0cc3ee00ae241271c56a5f4d32d8fba403f4e5b7428f73 |
| GSGM_EOG_2015_State.xls | 7b50377ffd55e905a0f7c8df4c3b0813eb9feedf4805deb88f8ba82cf74e4597 |
| GSGM_EOG_2015_System.xls | 0d5bd572efa3114a2c977b9ba5de8aed6043e6a84b80446f06c9cf7664b754e6 |
| GSGM_EOG_2016_School_Level.xls | 48812be02eb3ec647aa5609015c54fcca6f6ebd78954e7b6b1df7efe464a3a33 |
| GSGM_EOG_2016_State_Level.xls | 5bf5cfd258d3764cd4b0b555992b72d6a2b61f5493da23dfc17af63b3f3af991 |
| GSGM_EOG_2016_System_Level.xls | db8089a5d8a96ca2f288c12a1ce94fea90cecd616b3f99910da2c26aea0f1538 |
| GSGM_EOG_2017_School_Level.xlsx | 24ea951ab94acc14a5e1c018fad7ad10dbcb1ff17d19e62b6efc9a6c66d38933 |
| GSGM_EOG_2017_State_Level.xlsx | 596beb4b9629d0333a1aa79eb1f259af2c735f5758d676c2b91c41b197bd8623 |
| GSGM_EOG_2017_System_Level.xlsx | 5b5b067c32b56264507cad7d21e78bbde05a47a49f5dc9f0f3140bcfbfd9cf1a |
| GSGM_EOG_2018_School_Level.xlsx | 06682b731a86c7e3dfb6947c7c00eefa6bcf953782cb635282d4941e98487a25 |
| GSGM_EOG_2018_State_Level.xlsx | 15b118b9297ebb1233b59ba15fa4dd548ed95727ebae956fd33090cc6e7507ea |
| GSGM_EOG_2018_System_Level.xlsx | 732e81b156db09a3474bb553f6d711b1791fb610b7da17620600e99a51df510f |
| GSGM_EOG_2019_School_Level.xlsx | a16f4952c53fd6be74cd689f523f5b793ea29addce0cd0c3c2f127341643201d |
| GSGM_EOG_2019_State_Level.xlsx | 8926a872be5e9433e76c7a40dc2dace4ec07c9e635390cb9f47b7772281fea74 |
| GSGM_EOG_2019_System_Level.xlsx | 5e49cc46280430005f8f85a6d84b4c4055cd869c2b756efdd0ac50f8360aba80 |
| SGP_EOG_Aggs_School_Level_2023.xlsx | 57de21abf78eeae687b45c789b4607da4045cc737fa6e2f2f57813ad6cf02223 |
| SGP_EOG_Aggs_State_Level_2023.xlsx | 12f64e9c5e9cf84cad0ee5d717984b3a8c75e7a11b2dfff6e5a731b518e54582 |
| SGP_EOG_Aggs_System_Level_2023.xlsx | 7ceae4275feaf2d6ae7d936be7274634655d3fbcb47a88bd8ea9459d9c16f09d |

## Excel Sheet Structure

Every Excel file contains one or more grade-level sheets. The transform must iterate sheets within each workbook, pick up a per-grade label where appropriate, and concatenate. Except for 2015, all files use a **two-row pivot header**: row 0 is a title banner (ignorable), row 1 is a super-header naming each subject (e.g., `English Language Arts`, `Mathematics`), and row 2 is the actual metric header (e.g., `Number Tested`, `Median SGP`). In 2015 only, row 0 is the title and row 1 is already the flat metric header (no super-header row).

| File(s) | Sheets | Notes |
|---------|--------|-------|
| 2015 State (`GSGM_EOG_2015_State.xls`) | `EOG_AllGrades_2015_State` (Data), `EOG_Grade4_2015_State` - `EOG_Grade8_2015_State` (Data) | Legacy `.xls`. `AllGrades` sheet contains a single "Georgia, all grades" row with no `GRADE` column; the per-grade sheets each contain a single Georgia row with a `Grade` column. Transform should concatenate the 6 per-grade sheets and optionally add a synthetic `ALL` row from the AllGrades sheet. |
| 2015 System (`GSGM_EOG_2015_System.xls`) | `EOG_AllGrades_2015_System`, `EOG_Grade{4..8}_2015_System` | Legacy `.xls`. AllGrades has no `Grade` column (one row per system); per-grade sheets add a `Grade` column. **First column is mis-labeled `State` but contains the system code (601, 602, ...).** |
| 2015 School (`GSGM_EOG_2015_School.xls`) | `EOG_AllGrades_2015_School`, `EOG_Grade{4..8}_2015_School` | Legacy `.xls`. AllGrades has no `Grade` column; per-grade sheets add `Grade`. Uses a single 7-digit `KEY` column that encodes `SYSTEM_CODE*10000 + SCHOOL_CODE`. |
| 2016 State (`GSGM_EOG_2016_State_Level.xls`) | Single sheet **mis-named** `EOG_AllGrades_2015_State` (sheet tab still says 2015 even though file is 2016) | 6 data rows: one `ALL` row + Grade 4-8 rows, all for state `Georgia`. Adds `GRADE` column. Two-row header starts here. |
| 2016 System (`GSGM_EOG_2016_System_Level.xls`) | `EOG_AllGrades_2016_System`, `EOG_Grade{4..8}_2016_System` | AllGrades = 1 row per system (no `Grade`); per-grade sheets add `Grade`. First column renamed to `System ID`. |
| 2016 School (`GSGM_EOG_2016_School_Level.xls`) | `EOG_AllGrades_2016_School`, `EOG_Grade{4..8}_2016_School` | Same layout as 2015 school. First column renamed `Key` (capitalization-only change). |
| 2017 State (`GSGM_EOG_2017_State_Level.xlsx`) | Single sheet `EOG_AllGrades_2017_State` | 6 data rows (ALL + Grade 4-8). **Science and Social Studies dropped** — only English Language Arts and Mathematics remain in this era. |
| 2017 System / School | `EOG_AllGrades_2017_{System,School}`, `EOG_Grade{4..8}_2017_{System,School}` | Same layout as 2016 but ELA/Math only. |
| 2018 State (`GSGM_EOG_2018_State_Level.xlsx`) | Single sheet `EOG_AllGrades_2018_State` | 6 data rows. Column names change from `ELA: N Tested` / `Math: N Tested` form to subject-stripped form `Number Tested`, with newline characters embedded (e.g., `Number\nTested`, `%\n Received SGP`, `% \nProficient Learner and Above`). Polars auto-appends `_1` to duplicate column names when subjects are stripped. |
| 2018 System / School | `EOG_AllGrades_2018_{System,School}`, `EOG_Grade{4..8}_2018_{System,School}` | **School-level splits the single `Key` column into two: `System Code` and `School Code`.** Per-grade sheets include a `Grade` column; AllGrades does not. |
| 2019 State / System / School | Same sheet layout as 2018, same two-row header pattern | Column names like 2018 but without the stray newlines inside `% Received SGP`, `% Proficient Learner and Above`, `% Typical or High Growth` (the newlines only remain inside `Number\nTested` and `Median\nSGP`). **Percentage values switch from integer to decimal** (e.g., `94.003428` instead of `94`). Per-grade sheets no longer carry a `Grade` column — grade must be inferred from sheet name. |
| 2023 State (`SGP_EOG_Aggs_State_Level_2023.xlsx`) | Single sheet `EOG_AllGrades_2023_State` | 5 data rows (Grade 4-8 only — **no `ALL` row at state level**). `GRADE` column is integer-typed (`4`, `5`, ...) whereas 2016-2019 used string `ALL`/`4`/... |
| 2023 System / School | **Per-grade sheets only** — `Grade{4..8}_{System,School}_2023`. **No `AllGrades` sheet at system or school level.** | Metric set changes completely (see Era 6 below). Adds `RESAName_RPT` column at both system and school level (the 16 Regional Education Service Agency districts). The school-level `School Code` is 4 digits — a `(System Code, School Code)` composite key is required because school codes repeat across systems. |

For every era, transform code should:

1. Open each file.
2. Enumerate the relevant grade-level sheet(s) inside. For state-level 2015, the per-grade breakdown lives in six separate sheets. For 2016-2019 state, it lives in a single `AllGrades` sheet with a `GRADE` column. For 2023 state/system/school, only per-grade sheets exist.
3. Skip the title banner row(s); read the header row (row 1 for 2015, row 2 for 2016+); read the data rows.
4. Tag every row with the `year` inferred from the filename, the `detail_level` (state / district / school), and (where needed) the `grade` inferred from the sheet name.
5. Normalize column names (strip the `Subject:` prefix in 2015-2017, strip newlines in 2018-2019, dedupe the repeated ELA/Math columns into long format) before unpivoting.
6. Unpivot so that `subject` and `metric_name` become key columns and the numeric measurement becomes a single `value` column.

## Summary

Georgia Student Growth Model (SGM) results at the End-of-Grade (EOG) level. Metrics capture how individual students' scaled-score gains compare to peers with similar prior performance. Core published metrics, 2015-2019:

- **Number Tested** — students who took the EOG in the given subject.
- **Number Received SGP** — students who had both a current-year and prior-year EOG score and therefore received an SGP.
- **% Received SGP** — `Number Received SGP / Number Tested` × 100.
- **Median SGP** — median Student Growth Percentile among those who received an SGP (50 = typical Georgia peer growth).
- **% Proficient Learner and above** — share of tested students scoring at or above the state's Proficient Learner achievement cut-score.
- **% Developing Learner and above** — share of tested students scoring at or above Developing Learner.
- **% Typical or High Growth** — share of SGP-eligible students whose SGP is in the Typical (35-65) or High (66-99) growth band.

Subjects covered:
- **2015-2016**: ELA, Math, Science, Social Studies.
- **2017-2019**: ELA and Math only (Science and Social Studies dropped; not reinstated).

For **2023**, Georgia replaces the proficiency- and achievement-level metrics with a pure growth-percentile summary (ELA and Math only):

- **Number Received SGP** — same meaning as 2015-2019.
- **Median SGP** — same.
- **% Low Growth** — SGP 1-34.
- **% Typical Growth** — SGP 35-65.
- **% High Growth** — SGP 66-99.

The 2023 files also add a **RESA** (Regional Education Service Agency) column to the system- and school-level files — a 16-value grouping of Georgia's 180+ districts.

## Eras

### Era 1: 2015 (`GSGM_EOG_2015_{State,System,School}.xls`)

Flat single-row header (row 1); ELA + Math + Science + Social Studies; each subject has 7 metrics; subject-prefixed column names (`ELA: N Tested`, `Math: % Typical or High Growth`, ...).

| Column | Description |
|--------|-------------|
| State / KEY | State name at state level (`Georgia`); system code (misleadingly named `State`, values like `601`) at system level; 7-digit `KEY` at school level (encodes system + school). |
| System Name | System (district) name (system and school levels only). |
| School Name | School name (school level only). |
| Grade | Grade 4-8 on the per-grade sheets; absent on the AllGrades sheets. |
| ELA: N Tested | Number of students tested in English Language Arts (integer). |
| ELA: N Received SGP | Number of students who received an SGP in ELA (integer). |
| ELA: % Received SGP | `N Received SGP / N Tested` × 100 (integer 0-100, `----` when suppressed). |
| ELA: Median SGP | Median SGP in ELA (0-100, `----` when suppressed). |
| ELA: % Proficient Learner and above | Percent scoring Proficient or higher (0-100, `----` when suppressed). |
| ELA: % Developing Learner and above | Percent scoring Developing or higher (0-100, `----` when suppressed). |
| ELA: % Typical or High Growth | Percent with SGP 35+ (0-100, `----` when suppressed). |
| Math / Science / Social Studies: ... | Same 7 metrics repeated for each of the other three subjects. |

#### Sample Data (2015 School, AllGrades)

```
shape: (5, 31)
KEY    System Name      School Name                          ELA:N Tested  ELA:Median SGP ...
6750407 Henry County    New Hope Elementary                  247           68             ...
6410295 Dade County     Dade Middle School                   455           58             ...
6690289 Hall County     East Hall Middle School              782           68             ...
7790107 Jefferson City  Jefferson Academy                    515           42             ...
7080198 Oconee County   Malcom Bridge Middle School          856           47             ...
```

#### Statistics (2015 School, AllGrades)

- 1762 rows.
- `KEY` range: 6,010,177 - 7,991,895 (encodes system × 10000 + school).
- `ELA: N Tested` mean 363, max 5196.
- Median SGP columns centered at 50 (as expected).
- `% Received SGP` typically 90-99.

#### Null Counts

0 across all columns (suppression is encoded as the string `----`, not null).

#### Categorical Columns

| Column | Distinct Values (sample) |
|--------|------------------------|
| System Name (2015 school) | 196 distinct — `Gwinnett County` (109), `DeKalb County` (108), `Cobb County` (92), `Fulton County` (84), ... down to `Quitman County`, `Echols County`, `State Charter Schools- *`. |
| School Name (2015 school) | 1671 distinct (many repeats across districts — `Eastside Elementary School` appears 6 times, `Northside Elementary School` 5 times). |

#### Suppression Markers

| Column | Non-Numeric Values (count) |
|--------|---------------------------|
| `{ELA,Math,Science,Social Studies}: % Received SGP` | `----` (10-13 per subject) |
| `{ELA,Math,Science,Social Studies}: Median SGP` | `----` (10-13 per subject) |
| `{ELA,Math,Science,Social Studies}: % Proficient Learner and above` | `----` (19-29 per subject; Social Studies: 29 is highest) |
| `{ELA,Math,Science,Social Studies}: % Developing Learner and above` | `----` (11-14 per subject) |
| `{ELA,Math,Science,Social Studies}: % Typical or High Growth` | `----` (10-13 per subject) |
| `N Tested`, `N Received SGP` | **No suppression in 2015** — these are stored as clean integers even when the `%` metrics are `----`. |

### Era 2: 2016 (`GSGM_EOG_2016_{State,System,School}_Level.xls`)

Two-row pivot header (row 1 = subject super-header, row 2 = metric). Same subjects (ELA + Math + Science + Social Studies) and same 7 metrics as Era 1. Same `----` suppression marker.

Key differences vs 2015:
- State file introduces a `GRADE` column with `ALL` + `4`-`8` rows (6 total at state level).
- System file renames the first column from mis-labeled `State` to `System ID`.
- School file renames `KEY` → `Key` (capitalization only).
- The 2016 State workbook sheet tab is mis-labeled `EOG_AllGrades_2015_State` even though the file is 2016 — transform code should not trust sheet name for year inference.

#### Sample Data (2016 School, AllGrades)

```
shape: (3, 31)
Key     System Name      School Name                     ELA:N Tested  ELA:Median SGP ...
6010177 Appling County   Appling County Elementary School 367           38             ...
6010195 Appling County   Appling County Middle School     756           44             ...
6011050 Appling County   Altamaha Elementary School       122           38             ...
```

#### Statistics (2016 School)

1769 rows. `Key` range identical to 2015 (6,010,177 - 7,991,895 approx).

#### Null Counts

0 across all columns (suppression is `----`, not null).

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| System Name (2016 school) | 201 distinct — top districts unchanged vs 2015. |
| School Name (2016 school) | 1681 distinct. |

#### Suppression Markers

Same pattern as Era 1. `----` for all percent and Median SGP columns, 16-17 instances per column. `N Tested` and `N Received SGP` never suppressed.

### Era 3: 2017 (`GSGM_EOG_2017_{State,System,School}_Level.xlsx`)

Same two-row header shape as 2016, but:
- **Science and Social Studies dropped** — only ELA and Math remain. Column count drops from ~30 → ~16.
- Mix of two suppression markers: `----` (majority) and `TFS` ("Too Few Students"). Only column with `TFS` in the AllGrades school sheet is `Math: % Proficient Learner and above` (34 non-numeric entries: 24 `TFS`, 10 `----`).

#### Sample Data (2017 School, AllGrades)

```
shape: (3, 17)
Key     System Name      School Name                     ELA:N Tested  ELA:Median SGP ... Math:% Typical or High Growth
6010177 Appling County   Appling County Elementary       367           51             ... 80
6010195 Appling County   Appling County Middle School    760           58             ... 74
6011050 Appling County   Altamaha Elementary School      129           56             ... 69
```

#### Statistics (2017 School)

1772 rows.

#### Null Counts

0 across all columns (suppression encoded as strings `----` or `TFS`).

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| System Name | 204 distinct. |
| School Name | 1686 distinct. |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| `Math: % Proficient Learner and above` | `TFS` (24), `----` (10) |
| (other `%` and `Median SGP` columns) | `----` only (~10-20 each) — not all listed in the summary because they fall below the hybrid threshold. |

### Era 4: 2018 (`GSGM_EOG_2018_{State,System,School}_Level.xlsx`)

Same two-row header shape; ELA + Math only. Big naming change: the subject prefix is gone and each metric appears twice (once under ELA, once under Math). Polars auto-disambiguates the duplicates by appending `_1` to the second occurrence. Column names also carry embedded `\n` characters from the underlying merged-cell formatting (e.g., `Number\nTested`, `%\n Received SGP`, `Median\nSGP`, `% \nProficient Learner and Above`, `% \nTypical or High Growth`).

- **School file splits the single `Key` column into two: `System Code` and `School Code`.** State file gains a `GRADE` column; system files lose the `State` column (now `System Code` + `System Name`).
- Suppression marker changes from `----` to `TFS` universally across all `%` and `Median SGP` columns (24 entries in school AllGrades). `Number Tested` and `Number Received SGP` remain clean integers.
- `% Proficient Learner and above` becomes `% Proficient Learner and Above` (capital A).

#### Sample Data (2018 School, AllGrades)

```
shape: (3, 18)
System Code  School Code  System Name      School Name                       Number Tested  Median SGP ... Median SGP_1 (Math)
601          177          Appling County   Appling County Elementary School  395            43         ... 58
601          195          Appling County   Appling County Middle School      760            58         ... 58
601          1050         Appling County   Altamaha Elementary School        128            63         ... 54
```

#### Statistics (2018 School)

1780 rows.

#### Null Counts

0 across all columns (suppression encoded as string `TFS`, not null).

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| System Name | 209 distinct. |
| School Name | 1694 distinct. |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| `%\n Received SGP`, `Median\nSGP`, `% \nProficient Learner and Above`, `% Developing Learner and Above`, `% \nTypical or High Growth` (ELA block) | `TFS` (24) |
| Same five columns, `_1` suffix (Math block) | `TFS` (23) |
| `Number\nTested`, `Number Received SGP` | None (clean integers). |

### Era 5: 2019 (`GSGM_EOG_2019_{State,System,School}_Level.xlsx`)

Like Era 4 but:
- Embedded newlines are removed from `% Received SGP`, `% Proficient Learner and Above`, `% Developing Learner and Above`, `% Typical or High Growth` (still present in `Number\nTested` and `Median\nSGP`).
- **Percentages switch from integer to decimal** (e.g., `94.003428` instead of `94`) — this is the most important substantive change. `Median SGP` also becomes float (e.g., `50.0`, `46.5`).
- **Suppression moves from the string `TFS` to true null.** 24-25 rows in the school file have null `Number Received SGP` / `% Received SGP` / `Median SGP` / `% Proficient Learner and Above` / `% Developing Learner and Above` / `% Typical or High Growth` in each subject block. `Number Tested` is never null.
- `System Code` at system level is a string (`'601'`) in 2019 only — cast to the same integer type used by other years inside transform code.
- Per-grade system / school sheets **no longer carry a `Grade` column** — transform code must infer grade from the sheet name.

#### Sample Data (2019 School, AllGrades)

```
shape: (3, 18)
System Code  School Code  System Name      School Name                       Number Tested  Median SGP  % Proficient ELA  ...
601          0177         Appling County   Appling County Elementary School  374            44.0        30.327869         ...
601          0195         Appling County   Appling County Middle School      789            57.0        40.442133         ...
601          1050         Appling County   Altamaha Elementary School        126            43.0        29.365079         ...
```

Note that `School Code` is a zero-padded 4-character string in 2019 (unlike 2018, where it is an integer).

#### Statistics (2019 School)

- 1787 rows, 24-25 nulls per percent column.
- `Number Tested` mean 372, max 3189, min 1.
- `% Received SGP` mean 94.15 (as expected); min 71.26 (some school has relatively low matched-student coverage).
- `Median SGP` mean 50.03; min 5.5, max 78.5 — the expected percentile range (50 = typical).
- `% Proficient Learner and Above` mean 41.8 (ELA); range 0.0 - 99.4.
- `% Typical or High Growth` mean 65.0 (ELA); range 13.3 - 87.9.

#### Null Counts

| Column | Nulls |
|--------|-------|
| `System Code`, `School Code`, `System Name`, `School Name`, `Number Tested`, `Number Tested_1` | 0 |
| ELA block (`Number Received SGP`, `% Received SGP`, `Median SGP`, 3 pct columns) | 24 each |
| Math block (`..._1`) | 25 each |

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| System Name | 209 distinct (same ballpark as 2018). |
| School Name | 1700 distinct. |

#### Suppression Markers

None in string form — suppression is pure null. Total suppressed rows: 24 (ELA) / 25 (Math) at school AllGrades level.

### Era 6: 2023 (`SGP_EOG_Aggs_{State,System,School}_Level_2023.xlsx`)

Substantially different file:
- **Metric set changes completely.** Achievement/proficiency metrics (`% Proficient Learner and Above`, `% Developing Learner and Above`, `% Typical or High Growth`) are all dropped. Only SGP-related metrics remain: `Number Received SGP`, `Median SGP`, `% Low Growth`, `% Typical Growth`, `% High Growth`. `Number Tested` and `% Received SGP` are also gone. Column count drops to 10-14.
- **No `AllGrades` sheet at system or school level.** Per-grade sheets only (Grade 4-8). The state-level file has a single sheet named `EOG_AllGrades_2023_State` but it contains only the 5 per-grade rows — **no `ALL` across grades row**, unlike 2016-2019.
- **`GRADE` column at state level is integer (`4`, `5`, `6`, `7`, `8`)** rather than the string `ALL`/`4`/... used in 2016-2019.
- **`System Name` and `School Name` are fully UPPER-CASED** (`APPLING COUNTY`, `APPLING COUNTY ELEMENTARY SCHOOL`) whereas 2015-2019 use Title Case. Transform code must normalize these (preferred target: Title Case, matching other topics).
- **Adds a `RESAName_RPT` column** at system and school level — one of 16 Regional Education Service Agency names (`METRO`, `FIRST DISTRICT`, `NORTHWEST GEORGIA`, ...). This is a new categorical column with no equivalent in 2015-2019 files. Also UPPER-CASE.
- Suppression marker: `--` (two hyphens), not `----`. 14 suppressed rows per Grade 4 school sheet.
- **The School-level file uses a 4-digit `School Code` (`0177`, `1050`, etc.) that is NOT globally unique across systems.** School codes repeat across systems — the composite key `(System Code, School Code)` is required.
- **`Number Received SGP` column name is duplicated inside the ELA and Math blocks and Polars appends `_1` to the Math one**, same pattern as 2018-2019.

#### Sample Data (2023 School, Grade 4)

```
shape: (3, 15)
System Code  School Code  System Name      School Name                       Number Received SGP  Median SGP  % Low Growth ... RESA
601          0177         APPLING COUNTY   APPLING COUNTY ELEMENTARY SCHOOL  164                  45.5        39.024390    ... FIRST DISTRICT
601          1050         APPLING COUNTY   ALTAMAHA ELEMENTARY SCHOOL        57                   55.0        21.052632    ... FIRST DISTRICT
602          0176         ATKINSON COUNTY  PEARMAN ELEMENTARY SCHOOL         54                   50.0        16.666667    ... OKEFENOKEE
```

#### Statistics (2023 School, Grade 4)

- 1258 rows (one grade). Similar counts for Grades 5-8.
- `Median SGP` clustered around 50 (as expected).
- `% Low / Typical / High Growth` should sum to ~100 within each (row, subject) pair.

#### Null Counts

- 0 nulls on `System Code`, `School Code`, names, `Number Received SGP`, `RESAName_RPT`.
- 14 nulls each on `Median SGP`, `% Low Growth`, `% Typical Growth`, `% High Growth` in each subject block (14 rows where suppression marker `--` converted to null when the transform casts to Float64 with `strict=False`).

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| System Name (2023 school Grade 4) | 211 distinct, all UPPER-CASE (`APPLING COUNTY`, `ATKINSON COUNTY`, ...). |
| School Name | 1184 distinct. |
| RESAName_RPT | 16 distinct: `METRO` (454), `FIRST DISTRICT` (93), `NORTHWEST GEORGIA` (91), `GRIFFIN` (72), `CENTRAL SAVANNAH RIV` (64), `PIONEER` (60), `NORTHEAST GEORGIA` (57), `MIDDLE GEORGIA` (56), `WEST GEORGIA` (52), `NORTH GEORGIA` (49), `CHATTAHOOCHEE-FLINT` (46), `COASTAL PLAINS` (39), `SOUTHWEST GEORGIA` (36), `OKEFENOKEE` (35), `HEART OF GEORGIA` (14), `OCONEE` (7). |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| `Median\nSGP`, `% Low Growth`, `% Typical Growth`, `% High Growth` (ELA block) | `--` (14 each) |
| Same four columns, `_1` suffix (Math block) | `--` (14 each) |
| `Number Received SGP`, `Number Received SGP_1` | None (clean integers). |

## ETL Considerations

- **Multi-year-gap dataset.** Only 2015-2019 and 2023 are available. No 2020 (COVID cancellation), 2021 (ramp-back-up), 2022, 2024, or 2025. Transform code must not assume contiguous years.
- **Major schema break at 2023.** The 2023 files are best treated as a separate dataset variant: the core Growth Model "achievement × growth" metric set from 2015-2019 is gone and is replaced by a pure SGP-distribution view (`% Low Growth`, `% Typical Growth`, `% High Growth`). Do not try to force-fit the 2023 columns into the 2015-2019 gold schema — they should live alongside as distinct `metric` values, with separate metrics-present flags per era.
- **Two header rows (2016+) vs one (2015).** Row 0 is always a title banner and must be skipped. In 2015 row 1 is the flat header. In 2016+ row 1 is the super-header (forward-fill candidate: `English Language Arts`, `Mathematics`, `Science`, `Social Studies`, and in 2023+ also `RESA`) and row 2 is the metric header. Transform code must concatenate row 1 forward-filled with row 2 (or strip the subject prefix and unpivot long).
- **Mid-file subject drop (2017).** Science and Social Studies disappear in 2017 and never come back. The 2017 state file has 16 columns (2 ID + 2 × 7 metrics); 2016 has 30 columns (2 ID + 4 × 7 metrics).
- **Percentage scale change at 2019.** 2015-2018 store integers (`94`); 2019+ store decimals (`94.003428`). Treat both as 0-100 scale; no normalization needed beyond the dtype cast.
- **Five distinct suppression conventions across eras.**
  - 2015-2016: `----` (4 hyphens) — in all `%` and `Median SGP` columns.
  - 2017: mixed `----` and `TFS` ("Too Few Students") in `%`/`Median` columns.
  - 2018: `TFS` exclusively.
  - 2019: true null (no string marker).
  - 2023: `--` (2 hyphens).
  - Transform code should treat all of `['----', '--', 'TFS', 'tfs']` (case-insensitive) as missing and cast to Float64 / Int64 with `strict=False`.
- **Geographic identifier evolution.**
  - 2015: system code is mislabeled `State` at system level; school file uses a single 7-digit `KEY` that encodes `system_code * 10000 + school_code`. Transform must split `KEY` into its two components for gold.
  - 2016-2017: system-level column renamed `System ID` (still integer). School column renamed `Key` (same 7-digit encoding).
  - 2018: `Key` finally split into separate `System Code` + `School Code` integer columns.
  - 2019: same split layout but `System Code` and `School Code` are strings (`'601'`, `'0177'`) — cast to canonical types.
  - 2023: back to integer `System Code` and string `School Code` (zero-padded 4-digit). **School Code is NOT unique across systems** — must use `(System Code, School Code)` as the composite key.
- **Name-case change at 2023.** 2015-2019 use Title Case (`Appling County`, `Appling County Elementary School`); 2023 uses UPPER-CASE. Normalize to Title Case in gold, consistent with the sibling `georgia_milestones_end_of_grade` topic.
- **Grade representation differences.**
  - 2015 State (AllGrades sheet) has no `GRADE` column (implicit ALL); per-grade state sheets add `Grade` as integer 4-8.
  - 2015 System / School AllGrades has no `Grade` column; per-grade sheets have `Grade`.
  - 2016-2019 state AllGrades has a `GRADE` column with string values `ALL`, `4`, `5`, `6`, `7`, `8`.
  - 2016-2018 system / school AllGrades has no `Grade` column; per-grade sheets have one (2018) or not (2019).
  - 2019 per-grade sheets drop the `Grade` column entirely — transform must infer grade from the sheet name (`EOG_Grade4_2019_System` → `4`).
  - 2023 state `GRADE` is an integer 4-8 (no `ALL` row). 2023 system / school files have per-grade sheets with no `Grade` column — grade must be inferred from sheet name (`Grade4_System_2023` → `4`).
- **Only Grades 4-8 are measured.** Grade 3 is never present because an SGP requires a prior-year score, and Grade 2 is not tested.
- **Sheet tab typo in 2016 State.** `GSGM_EOG_2016_State_Level.xls` has a single sheet labeled `EOG_AllGrades_2015_State` even though the file is 2016. Sheet-name parsing for year must defer to the filename, not the tab.
- **`% Received SGP` is derived.** Equal to `Number Received SGP / Number Tested` × 100. Useful for sanity checks (range 70-100 typical, never > 100). In 2023 this column is absent because `Number Tested` is no longer published.
- **Median SGP is centered on 50 by construction.** Statewide median is always exactly 50 (true for every year in the state file). Use this as a validation signal: the state-level `Median SGP` in each year × subject should equal 50; deviations indicate transform/suppression bugs.
- **Growth-band percentages should sum to ~100 within each (row, subject) in 2023.** `% Low Growth + % Typical Growth + % High Growth ≈ 100` for 2023. In 2015-2019 there is no equivalent closure relationship because only `% Typical or High Growth` is reported (not `% Low Growth`).
- **RESA is a new-in-2023 column** and appears only in 2023 system/school files (not state). It maps each district to one of Georgia's 16 Regional Education Service Agencies. If used, normalize the 16 values to Title Case (`Metro`, `First District`, `Northwest Georgia`, ...) and cross-reference against the Georgia DOE's official RESA list, noting that `CENTRAL SAVANNAH RIV` is a truncation of `Central Savannah River`.

## Gold Schema Classification

| Bronze Column(s) | Gold Role | Gold Name | Notes |
|---|---|---|---|
| `State` (2015 state only), `Georgia` literal | fact_key (constant) | — | Drop; every row is Georgia. Use `district_code = NULL` to mark state-level rows. |
| `State` / `System ID` / `System Code` | fact_key | district_code | Cast to 3-digit integer. Note 2015 system "State" column actually holds the system code. |
| `System Name` | dimension_attribute | — | Goes to `districts` dimension. Normalize: 2023 values are UPPER-CASE, others Title Case — standardize to Title Case. |
| `KEY` / `Key` (2015-2017, 7 digits) | fact_key (split) | district_code, school_code | Split into `district_code = KEY // 10000` and `school_code = KEY % 10000`. |
| `System Code` + `School Code` (2018-2019, 2023) | fact_key (pair) | district_code, school_code | Already separate. Cast both to integers (or use zero-padded 4-digit string for `school_code` to preserve leading zeros — see companion topic convention). |
| `School Name` | dimension_attribute | — | Goes to `schools` dimension. Normalize case. |
| `GRADE` / `Grade` | fact_categorical | grade_level | Bronze integer 4-8 → gold zero-padded 2-char string (`"04"`-`"08"`). At state level, `ALL` rows (2016-2019 only) collapse to gold `grade_level = "all"`; 2023 has no ALL row. |
| `ELA: N Tested`, `Math: N Tested`, ..., `Number Tested` | fact_metric | num_tested | Integer. Per-subject via unpivot. **Not present in 2023.** |
| `ELA: N Received SGP`, ..., `Number Received SGP` | fact_metric | number_received_sgp | Integer. Per-subject via unpivot. |
| `ELA: % Received SGP`, ..., `% Received SGP` | fact_metric | pct_received_sgp | 0-100 percent. Per-subject via unpivot. **Not present in 2023.** |
| `ELA: Median SGP`, ..., `Median SGP` | fact_metric | median_sgp | 0-100 percentile. Per-subject via unpivot. |
| `ELA: % Proficient Learner and above`, ..., `% Proficient Learner and Above` | fact_metric | pct_proficient_and_above | 0-100 percent. Per-subject via unpivot. **Not present in 2023.** |
| `ELA: % Developing Learner and above`, ..., `% Developing Learner and Above` | fact_metric | pct_developing_and_above | 0-100 percent. Per-subject via unpivot. **Not present in 2023.** |
| `ELA: % Typical or High Growth`, ..., `% Typical or High Growth` | fact_metric | pct_typical_or_high_growth | 0-100 percent. Per-subject via unpivot. **Not present in 2023.** |
| `% Low Growth` (2023 only) | fact_metric | pct_low_growth | 0-100 percent. Per-subject via unpivot. **Only present in 2023.** |
| `% Typical Growth` (2023 only) | fact_metric | pct_typical_growth | 0-100 percent. Per-subject via unpivot. **Only present in 2023.** |
| `% High Growth` (2023 only) | fact_metric | pct_high_growth | 0-100 percent. Per-subject via unpivot. **Only present in 2023.** |
| Super-header (`English Language Arts`, `Mathematics`, `Science`, `Social Studies`) | fact_categorical | subject | Unpivoted into a single `subject` column with values `ela`, `math`, `science`, `social_studies`. Filter to `{ela, math}` only for 2017+. |
| `RESAName_RPT` (2023 system/school only) | dimension_attribute | — | Goes to `districts` dimension as `resa_name` (Title Case). Not a fact-table column. |
| File-year (derived from filename) | fact_key | year | 2015-2019, 2023. Integer. |
| Detail level (derived from file) | fact_categorical | detail_level | `state`, `district`, `school`. |
| Title banner row 0 | not_in_gold | — | Skip. |
| Sheet tab string | not_in_gold | — | Only used to derive `year` and `grade` for eras where the `Grade` column is missing. |

## Corrections (verified against bronze during transform authoring, 2026-06-12)

1. **Median SGP domain is 1-99, not 0-100, and bronze publishes sentinel `0`
   blocks for empty cohorts.** The Overview ("Median SGP is on a 0-100 scale")
   overstates the domain: an SGP is an ordinal percentile rank with no 0 or 100
   value. Bronze publishes `Median SGP = 0` only on whole-row zero blocks for
   subject cohorts with no test takers (`N Tested = 0`, `N Received SGP = 0`,
   every `%` metric 0). Verified by a full 18-file scan: 34 such cells — 29 in
   the 2016 School file (e.g. 14 in `EOG_Grade8_2016_School` Science), 2 in the
   2016 System file (`EOG_Grade8_2016_System` Science), 3 in the 2018 School
   file (`EOG_Grade8_2018_School` Mathematics). The transform NULLs `sgp_median`
   on those rows (§4b mask, recorded in the manifest) and enforces a [1, 99]
   contract range.
2. **2015-2017 school files key State/Commission Charter campuses under the
   bare SYSTEM codes 782/783** (via the 7-digit `KEY` prefix: e.g. `7820110`
   splits to system `782` + school `0110`). The 2018-2019 and 2023 school files
   instead publish the 7-digit CAMPUS codes directly in `System Code`
   (`7820110`, `7830636`, ...; no bare 782/783 school rows). Not previously
   documented. The transform promotes the early school-level rows to the campus
   codes via the shared `_charter_district_promotion` module (790 rows:
   272/324/194 in 2015/2016/2017). No bare 782/783 rows exist at the DISTRICT
   level in any year — even the 2015-2017 system files already publish the
   7-digit campus codes as district rows (13/17/20 distinct campus codes
   respectively; verified per file) — so the promotion only ever applies to
   school rows.
3. **Era 4 "State file gains a `GRADE` column" is misleading** — the state
   files have carried a `GRADE` column (values `ALL`, `4`-`8`) since 2016
   (Era 2); 2018 changed nothing at state level in that respect.
4. **`799` ("State Schools") is a single umbrella district row in the
   2015-2017 system files** — exactly one row per sheet, named `State Schools`.
   Unlike the Milestones EOG bronze (where three distinct state schools share
   code 799), no per-school disambiguation is needed at the district level;
   school-level rows already carry distinct codes (`7991893`-`7991895`-style
   keys split to `799` + school code).
5. **Gold column names in the "Gold Schema Classification" table are
   superseded by the §16 canonical vocabulary**: `num_received_sgp` (not
   `number_received_sgp`), `sgp_median` (not `median_sgp`),
   `pct_proficient_learner_or_above` / `pct_developing_learner_or_above` (not
   `pct_proficient_and_above` / `pct_developing_and_above`), and
   `pct_sgp_low_growth` / `pct_sgp_typical_growth` / `pct_sgp_high_growth`
   (not `pct_low_growth` / `pct_typical_growth` / `pct_high_growth`).
