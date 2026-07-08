# retained_students — Bronze Data Structure

## Overview

- Topic: retained_students
- Source: gosa
- Files: 21 files spanning 2004–2024 (school years 2003-04 through 2023-24)
- Unreadable files: none. `retained_students_2005.csv` and `retained_students_2006.csv` are actually legacy Excel binary (.xls / OLE2 BIFF8) files saved with a `.csv` extension — they must be read with `pl.read_excel()`, not `pl.read_csv()`. They contain the same single data sheet (`Sheet1`) as the surrounding Excel files.
- Year representation:
  - **Era 1–2 (2011–2024)**: present in both the filename (`retained_students_YYYY.csv|xlsx`) and a `School Year` / `School_Year` column (`YYYY-YY` format, e.g., `2023-24`). Filename year = ending calendar year of the school year (e.g., `_2024.csv` contains `2023-24` rows).
  - **Era 3–4 (2004–2010)**: no `School Year` column exists. Year is identified only by the filename. Following the GOSA convention (confirmed in Era 2), the filename year is the *ending* school year — so `retained_students_2004.csv` represents school year `2003-04`, and `retained_students_2010.csv` represents school year `2009-10`.
- Filename-to-data year offset: same — filename year always equals the ending calendar year of the school year.
- Detail levels: state, district, school
- Percentage scale: 0–100 (for all `Percent*` / `Percentage*` columns)
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| retained_students_2004.csv | fc1bda34ba918a49b33ee9dd929c52041786b5f95bba827f3438e95ebbfa4a61 |
| retained_students_2005.csv | aa103f57f34c280f7fcb157841793e0a5c03559466f9bb4fd130319edbf7d107 |
| retained_students_2006.csv | 3e74f7c526e1dad90dabc78559f092f8ee37f46c1348ed2f03b030b2fd34832c |
| retained_students_2007.xls | ec0fd06a3ecf95b25d3ac4580a08a86647b6c77fc9fc5e756ed5e0ff4064dfa7 |
| retained_students_2008.xls | c5e4a42579722485e46cc28e4e3187e0584404397ec27ba5ae7dc1eacfe60797 |
| retained_students_2009.xls | 88b8b5008076f28ac56a16ec7caa835244919cd2936719cdbac1d33c0169d8cb |
| retained_students_2010.csv | e358d4ca28ee2cad0a79fbe8fc532a5847149811d7efcec4556cb8f24535c119 |
| retained_students_2011.csv | 02c2ed280b7e6b6a6da4255acd3d0179e09937da6317ea375c8c76d1b4413ebd |
| retained_students_2012.xlsx | 0033c793bfaa590a4925edc26beff6d9e7efad5eaa6de720658a34be4470abee |
| retained_students_2013.csv | 4ab96b8a42894978abcfe21c172a14578372c27de9a1c0ae0a4551c9c3491cf8 |
| retained_students_2014.csv | 3cecf226b1818846aaf24c63c27558874f8569384063d186911c46e98b4df4ea |
| retained_students_2015.csv | 4f28b05c1b2ce0086acd866370e6adf803c392278d4e962b3a3889e45d649004 |
| retained_students_2016.csv | e128547307e37abd5dc905af85f42c7d750422067b9348087a6185a085b140b3 |
| retained_students_2017.csv | bba8ed10b7854d19feb3de5a70fe0a6822902ec78580a90a36c9ba2347421378 |
| retained_students_2018.csv | 68b09a5e303df68f4d9282f8f6b8fa294af5b4333ad9ee3473ca1ad3e743b866 |
| retained_students_2019.csv | a281aef46823c2af58a5003b7011a3504e4bff9f35bb70685d08185c742accd8 |
| retained_students_2020.csv | 7f76080d68694337429b42bc22d42b307b3ad03c427830939f4d7e4cd1832e99 |
| retained_students_2021.csv | b00123a17029514febd069b14c498dd825881f0f6e32dbb6fe680359a77b2482 |
| retained_students_2022.csv | 84fe0006d89649ed0d040e9afdb75b4aca8919d95590eba3782195b0d9a97add |
| retained_students_2023.csv | c18e60a5e74c48ecd69cc70a73b11ed020e0926f1f8b29685cd44b2dbd78c4f2 |
| retained_students_2024.csv | bd92fa46d97988e0ff1119f349253496bddb22bec29411fb4381ec5c62e82cc5 |

## Excel Sheet Structure

| File(s) | Sheets | Notes |
|---------|--------|-------|
| 2005.csv (actually .xls), 2006.csv (actually .xls), 2007.xls, 2008.xls | `Sheet1` (Data), `Sheet2` (empty), `Sheet3` (empty) | Use `Sheet1`. `Sheet2`/`Sheet3` are empty placeholders created by Excel — Polars raises `NoDataError` on them if read directly. |
| 2009.xls | `Retained` (Data) | Single sheet, renamed from the `Sheet1` default. |
| 2012.xlsx | `Export Worksheet` (Data), `SQL` (empty) | Use `Export Worksheet`. `SQL` contains 1 column, 0 rows (likely an empty template). |

All other files (2004 and 2010–2024) are CSVs.

The 2005 and 2006 files carry a `.csv` extension but are in fact OLE2-format Excel files (BIFF8). Detect this at runtime by sniffing the first 4 bytes for the `\xd0\xcf\x11\xe0` magic, or simply hard-code those two years to use `pl.read_excel()`.

## Summary

This dataset reports grade-level retention (students held back). Each row contains an overall retention count and rate (`Total Retained`, `Total Retained / Total Enrolled` × 100) plus the count and percentage of retained students broken out by 7 demographics: **American Indian, Asian, Black, Hispanic, Multiracial, White, Female, Male**. There is NO `All Students` subgroup column — the overall total is the `Total Retained` metric itself. Percentages are out of each demographic's retained subset (i.e., "What percent of the retained students are Black?"), not retention rates *within* each demographic — the report is a demographic breakdown of who is being retained, not a per-demographic retention rate.

Key distinguishing metrics:
- `Total Retained` — number of students retained (held back) at the geography level
- `Number of {demographic}` — count of retained students in that demographic
- `Percentage of {demographic}` — share of retained students who are in that demographic (sums to ~100% across race columns and to ~100% across gender columns)

**CORRECTED (2026-06-11, transform authoring):** Only the tidy era (2011–2024) includes `Total Enrolled`. The wide-era columns `Retained_NN` (2007–2008) and `Retained Total Students` (2004–2006, 2009–2010) — originally read as "Total Enrolled" — are in fact the **TOTAL RETAINED count**. Evidence: at every state row 2004–2010 the value (58,302 / 66,805 / 66,367 / 68,423 / 65,776 / 61,642 / 59,999) equals BOTH the male+female sum AND the 6-race-bucket sum of the per-demographic retained counts, and is ~3.5% of Georgia's ~1.6M K-12 enrollment (the tidy-era `Total Enrolled` at the state row is 1.63–1.72M). The same identity holds at every non-state row where all components are published (0 mismatches across all 21 files). No overall retention rate is derivable for 2004–2010.

## Eras

The dataset has **four structurally distinct eras**, but Era 2 additionally splits into two sub-eras by suppression-marker convention.

### Era 1: 2023–2024 (modern naming with `#RPT_NAME`, underscore separators)

26 columns. Column names use `Snake_Case_With_Underscores` and a leading `#RPT_NAME` column was added (constant `Retained K-12`).

| Column | Description |
|--------|-------------|
| #RPT_NAME | Report name; constant `"Retained K-12"`. Era 1 only. |
| School_Year | School year as `YYYY-YY` (e.g., `2023-24`). One value per file. |
| Data_Reporting_Level | Detail level: `State`, `District`, or `School`. |
| School_District_Code | GOSA district code (3-digit standard or 7-digit charter); literal `ALL` for state-level rows. |
| School_District_Name | District name; literal `All Column Values` for state-level rows. |
| School_Code | GOSA school code (4-digit, zero-padded); literal `ALL` for state and district rows. |
| School_Name | School name; literal `All Column Values` for state and district rows. |
| Grades_Served | Comma-separated grade levels served by the institution (e.g., `09,10,11,12`). |
| Total_Enrolled | Total enrolled students in K-12 (float, even though count-like). |
| Total_Retained | Number of retained students (integer ≥10) or the suppression marker `TFS`. |
| Number_of_Asians | Count of retained students who are Asian (integer ≥10) or `TFS`. |
| Percentage_of_Asians | % of retained who are Asian (integer 0–100) or `TFS`. |
| Number_of_American_Indian | Retained American Indian count or `TFS`. |
| Percentage_of_American_Indian | % of retained who are American Indian or `TFS`. |
| Number_of_Black | Retained Black count or `TFS`. |
| Percentage_of_Black | % of retained who are Black or `TFS`. |
| Number_of_Hispanic | Retained Hispanic count or `TFS`. |
| Percentage_of_Hispanic | % of retained who are Hispanic or `TFS`. |
| Number_of_MultiRacial | Retained Multiracial count or `TFS`. |
| Percentage_of_MultiRacial | % of retained who are Multiracial or `TFS`. |
| Number_of_White | Retained White count or `TFS`. |
| Percentage_of_White | % of retained who are White or `TFS`. |
| Number_of_Male | Retained Male count or `TFS`. |
| Percentage_of_Male | % of retained who are Male or `TFS`. |
| Number_of_Female | Retained Female count or `TFS`. |
| Percentage_of_Female | % of retained who are Female or `TFS`. |

#### Sample Data (2024)

| #RPT_NAME | School_Year | Data_Reporting_Level | School_District_Code | School_District_Name | School_Code | School_Name | Grades_Served | Total_Enrolled | Total_Retained | Number_of_Black | Percentage_of_Black | Number_of_Male | Percentage_of_Male |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Retained K-12 | 2023-24 | District | 601 | Appling County | ALL | All Column Values | PK,KK,01,02,03,04,05,06,07,08,09,10,11,12 | 3237.00000 | 58 | 13 | 22 | 32 | 55 |
| Retained K-12 | 2023-24 | District | 602 | Atkinson County | ALL | All Column Values | PK,KK,01,02,03,04,05,06,07,08,09,10,11,12 | 1491.00000 | 48 | 25 | 52 | 28 | 58 |
| Retained K-12 | 2023-24 | School | 726 | Griffin-Spalding County | 0201 | Cowan Road Middle School | 06,07,08 | 555.00000 | TFS | TFS | TFS | TFS | TFS |
| Retained K-12 | 2023-24 | School | 637 | Cook County | 0104 | Cook Elementary School | 03,04,05 | 640.00000 | 19 | 11 | 58 | 10 | 53 |

#### Statistics (2024)

- Row count: 2,518
- All columns are stored as `Utf8` (string) on read
- 0 nulls in any column (suppression is encoded as the `TFS` literal, not null)
- `Total_Enrolled` is a float-formatted string (e.g., `3237.00000`, `640.00000`) — must be cast to `Float64` then to `Int64` after stripping.

#### Null Counts (2024)

All 26 columns: 0 nulls.

#### Categorical Columns (2024)

| Column | Distinct Count | Distinct Values (with row counts where useful) |
|--------|---------------|------------------------------------------------|
| #RPT_NAME | 1 | `Retained K-12` (2,518) |
| School_Year | 1 | `2023-24` (2,518) |
| Data_Reporting_Level | 3 | `School` (2,299), `District` (218), `State` (1) |
| School_District_Name | 233 | District names; includes `All Column Values` sentinel for the single state row. |
| School_Name | 2,199 | School names; includes `All Column Values` for state + district aggregate rows. |
| Grades_Served | 69 | Comma-separated grade strings; common values include `09,10,11,12`, `06,07,08`, `PK,KK,01,02,03,04,05`, and `PK,KK,01,02,03,04,05,06,07,08,09,10,11,12` (K-12 full span used for state and most districts). |

#### Suppression Markers (2024)

| Column | Marker | Count | Meaning |
|--------|--------|-------|---------|
| School_District_Code | `ALL` | 1 | State-level row only. |
| School_Code | `ALL` | 219 | State + district aggregate rows (1 state + 218 districts). |
| Total_Retained | `TFS` | 1,602 | "Too few students" — cell suppressed for privacy (cohort <10). |
| Number_of_Asians | `TFS` | 2,491 | Privacy suppression. |
| Percentage_of_Asians | `TFS` | 2,491 | Privacy suppression (always co-suppressed with its `Number_of_*` sibling). |
| Number_of_American_Indian | `TFS` | 2,514 | Privacy suppression. |
| Percentage_of_American_Indian | `TFS` | 2,518 | Fully suppressed for 2024 (no geography met the threshold). |
| Number_of_Black | `TFS` | 2,029 | Privacy suppression. |
| Percentage_of_Black | `TFS` | 2,029 | Privacy suppression. |
| Number_of_Hispanic | `TFS` | 2,255 | Privacy suppression. |
| Percentage_of_Hispanic | `TFS` | 2,255 | Privacy suppression. |
| Number_of_MultiRacial | `TFS` | 2,455 | Privacy suppression. |
| Percentage_of_MultiRacial | `TFS` | 2,455 | Privacy suppression. |
| Number_of_White | `TFS` | 2,082 | Privacy suppression. |
| Percentage_of_White | `TFS` | 2,082 | Privacy suppression. |
| Number_of_Male | `TFS` | 1,870 | Privacy suppression. |
| Percentage_of_Male | `TFS` | 1,870 | Privacy suppression. |
| Number_of_Female | `TFS` | 1,994 | Privacy suppression. |
| Percentage_of_Female | `TFS` | 1,994 | Privacy suppression. |

All metric columns are stored as strings because of the `TFS` marker. Underlying numeric types: `Total_Enrolled` is float (one-decimal representation of integer counts), `Total_Retained` and `Number_of_*` are integers (≥10 because of the cell-size threshold), `Percentage_of_*` are integers 0–100.

### Era 2: 2011–2022 (modern naming with spaces; no `#RPT_NAME`)

25 columns. Identical in content to Era 1 except:
- No `#RPT_NAME` column.
- Column names use `Title Case With Spaces` rather than `Snake_Case_With_Underscores` (e.g., `School Year`, `Data Reporting Level`, `Number of Asians`, `Percentage of Asians`).

| Column | Description |
|--------|-------------|
| School Year | School year as `YYYY-YY` (e.g., `2021-22`). One value per file. |
| Data Reporting Level | Detail level: `State`, `District`, or `School`. |
| School District Code | GOSA district code; literal `ALL` for state-level rows. |
| School District Name | District name; literal `All Column Values` for state-level rows. |
| School Code | GOSA school code; literal `ALL` for state and district rows. |
| School Name | School name; literal `All Column Values` for state and district rows. |
| Grades Served | Comma-separated grade levels served. |
| Total Enrolled | Total enrolled students. |
| Total Retained | Number of retained students or the suppression marker. |
| Number of Asians | Retained Asian count or suppression marker. |
| Percentage of Asians | % of retained who are Asian, or suppression marker. |
| Number of American Indian | Retained American Indian count or suppression marker. |
| Percentage of American Indian | % of retained who are American Indian, or suppression marker. |
| Number of Black | Retained Black count or suppression marker. |
| Percentage of Black | % of retained who are Black, or suppression marker. |
| Number of Hispanic | Retained Hispanic count or suppression marker. |
| Percentage of Hispanic | % of retained who are Hispanic, or suppression marker. |
| Number of MultiRacial | Retained Multiracial count or suppression marker. |
| Percentage of MultiRacial | % of retained who are Multiracial, or suppression marker. |
| Number of White | Retained White count or suppression marker. |
| Percentage of White | % of retained who are White, or suppression marker. |
| Number of Male | Retained Male count or suppression marker. |
| Percentage of Male | % of retained who are Male, or suppression marker. |
| Number of Female | Retained Female count or suppression marker. |
| Percentage of Female | % of retained who are Female, or suppression marker. |

**Era 2 sub-eras by suppression marker:**
- **Era 2a: 2011–2020** → marker is the literal string `Too Few Students`
- **Era 2b: 2021–2022** → marker is the abbreviated literal string `TFS` (same as Era 1)

#### Sample Data (2016, Era 2a)

| School Year | Data Reporting Level | School District Code | School District Name | School Code | School Name | Grades Served | Total Enrolled | Total Retained | Number of Black | Percentage of Black |
|---|---|---|---|---|---|---|---|---|---|---|
| 2015-16 | School | 601 | Appling County | 0103 | Appling County High School | 09,10,11,12 | 946 | 23 | Too Few Students | Too Few Students |
| 2015-16 | School | 601 | Appling County | 0177 | Appling County Elementary School | 02,03,04,05 | 531 | 10 | Too Few Students | Too Few Students |
| 2015-16 | District | 601 | Appling County | ALL | All Column Values | PK,KK,01,02,03,04,05,06,07,08,09,10,11,12 | 3187 | 65 | 18 | 28 |

#### Sample Data (2022, Era 2b)

| School Year | Data Reporting Level | School District Code | School District Name | School Code | School Name | Grades Served | Total Enrolled | Total Retained | Number of Black | Percentage of Black |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021-22 | School | 601 | Appling County | 0103 | Appling County High School | 09,10,11,12 | 970 | 31 | TFS | TFS |
| 2021-22 | District | 601 | Appling County | ALL | All Column Values | PK,KK,01,02,03,04,05,06,07,08,09,10,11,12 | 3253 | 76 | 17 | 22 |

#### Statistics (Era 2 row counts and suppression representation)

| Year | Rows | Total Retained suppression marker | Total Retained marker count |
|------|------|-----------------------------------|-----------------------------|
| 2011 | 2,475 | `Too Few Students` | 1,097 |
| 2012 | 2,485 | `Too Few Students` | 1,124 |
| 2013 | 2,469 | `Too Few Students` | 1,129 |
| 2014 | 2,459 | `Too Few Students` | 1,179 |
| 2015 | 2,463 | `Too Few Students` | 1,149 |
| 2016 | 2,474 | `Too Few Students` | 1,229 |
| 2017 | 2,479 | `Too Few Students` | 1,311 |
| 2018 | 2,486 | `Too Few Students` | 1,314 |
| 2019 | 2,491 | `Too Few Students` | 1,298 |
| 2020 | 2,493 | `Too Few Students` | 1,383 |
| 2021 | 2,505 | `TFS` | 1,661 |
| 2022 | 2,512 | `TFS` | 1,411 |

#### Null Counts (Era 2)

All ID and geography columns: 0 nulls in every year.

Metric columns: 0 nulls in every year except **2016**, which has **8 rows with null `Total Enrolled`** (see ETL Considerations). Every other metric for those 8 rows is either a number or the suppression marker — they are not empty rows, just a specific gap in the enrollment column that year.

Suppression is encoded via the literal marker string (`Too Few Students` or `TFS`), never via null.

#### Categorical Columns (Era 2)

| Column | Distinct Count (2022) | Notes |
|--------|---------------------|-------|
| School Year | 1 | One per file (e.g., `2021-22`). |
| Data Reporting Level | 3 | `School`, `District`, `State` (always exactly 1 `State` row). |
| School District Name | ~220 | Includes `All Column Values` sentinel for state row. |
| School Name | ~2,200 | Includes `All Column Values` for non-school rows. |
| Grades Served | ~70 | Same comma-separated pattern as Era 1. |

#### Suppression Markers (Era 2)

| Column | Marker | Years | Notes |
|--------|--------|-------|-------|
| School District Code | `ALL` | all | State-level row only (1 per year). |
| School Code | `ALL` | all | State + district aggregate rows (~200 per year). |
| Total Enrolled | (none — `null` in 8 rows in 2016) | 2016 only | Data gap, not suppression. |
| Total Retained, Number of *, Percentage of * | `Too Few Students` | 2011–2020 | Privacy suppression (cohort <10). |
| Total Retained, Number of *, Percentage of * | `TFS` | 2021–2022 | Privacy suppression (same rule, abbreviated marker). |

### Era 3: 2007–2009 (pre-reformat, abbreviated / inconsistent layout)

26 columns in 2007–2008, 28 columns in 2009 (2 extra stray columns). No `School Year`, no `Data Reporting Level`, no `District Code / Name`, no `Grades Served`, no `Total Enrolled`. Geography and detail level must be **derived from the `SysSchoolid` column** (see below).

**Sub-era 3a: 2007–2008** — cryptic short column names.

| Column | Description |
|--------|-------------|
| SysSchoolid | `districtcode:schoolcode`, or `districtcode:ALL` for district aggregates, or `ALL:ALL` for the state row. |
| SchoolNme | School/district name, or `State of Georgia` for the state row. (Note the typo — `SchoolNme`, not `SchoolName`.) |
| Retained_NN | **Total Retained** (CORRECTED — not Total Enrolled; see Summary). Repeated 8× as `Retained_NN`, `_NA`, `_NB`, `_NF`, `_NH`, `_NM`, `_NU`, `_NW`. All 8 `N*` columns are **always equal** (verified on 2007 AND 2008: all 8 equal `Retained_NN` for every row). The 7 non-NN copies are redundant. |
| Retained_TN | Total Retained for American Indian ("Native"). |
| Retained_PN | Percent Retained for American Indian. |
| Retained_TA | Total Retained for Asian. |
| Retained_PA | Percent Retained for Asian. |
| Retained_TB | Total Retained for Black. |
| Retained_PB | Percent Retained for Black. |
| Retained_TF | Total Retained for Female. |
| Retained_PF | Percent Retained for Female. |
| Retained_TH | Total Retained for Hispanic. |
| Retained_PH | Percent Retained for Hispanic. |
| Retained_TM | Total Retained for Male. |
| Retained_PM | Percent Retained for Male. |
| Retained_TU | Total Retained for Multiracial ("Unclassified"?). |
| Retained_PU | Percent Retained for Multiracial. |
| Retained_TW | Total Retained for White. |
| Retained_PW | Percent Retained for White. |

**IMPORTANT semantic interpretation check for 2007–2008 (CORRECTED):** The `_T*` values are the **per-demographic retained counts** and `_P*` values are the **share-of-retained percentages** — exactly analogous to Era 1–2 `Number of Black` / `Percentage of Black`. There IS a top-level total: `Retained_NN` is the **total retained count** (verified: `Retained_NN = TM + TF = TN + TA + TB + TH + TU + TW` on every row of 2007 and 2008 — 0 mismatches — and `P{x} = T{x} / NN × 100` holds within 1pp everywhere except 0/0 rows). No derivation is needed. The original cross-check note for `601:103` ("`_NN=42` which is enrolled, not retained") was wrong — 42 is that school's retained total. The note's race sum of 41 was an arithmetic slip that omitted `_TU=1` (Multiracial): the actual row is TB=21 + TH=1 + TU=1 + TW=19 = 42 = NN = TM+TF.

**Sub-era 3b: 2009** — returned to the long-name layout used in Eras 3c/4 below, plus two stray empty columns.

| Column | Description |
|--------|-------------|
| SysSchoolid | Same `districtcode:schoolcode` format as Era 3a. |
| School Name | School/district name (now spelled correctly, with a space). |
| Retained Total Students | **Total Retained** (CORRECTED — not total enrolled; see Summary). |
| Retained Total American Indian | Retained American Indian count (numerator). |
| Retained Percent American Indian | Percent of retained who are American Indian. |
| Retained Asian, Retained Black, Retained Female, Retained Hispanic, Retained Male, Retained Multiracial, Retained White | All 7 are duplicates of `Retained Total Students` (verified: every non-null row has these equal to `Retained Total Students`). These are redundant denominator copies and should be dropped. |
| Retained Total Asian, Retained Total Black, Retained Total Female, Retained Total Hispanic, Retained Total Male, Retained Total Multiracial, Retained Total White | Per-demographic retained counts (numerators). |
| Retained Percent Asian, Retained Percent Black, Retained Percent Female, Retained Percent Hispanic, Retained Percent Male, Retained Percent Multiracial, Retained Percent White | Share-of-retained percentages. |
| __UNNAMED__26 | Stray spillover column — 15 rows non-null with small decimal values; 2,400 null. Almost certainly an Excel workbook artifact. **Drop.** |
| __UNNAMED__27 | Stray spillover column — 1 row non-null, 2,414 null. **Drop.** |

#### Sample Data (2007, Era 3a)

| SysSchoolid | SchoolNme | Retained_NN | Retained_TN | Retained_PN | Retained_TA | Retained_PA | Retained_TB | Retained_PB | Retained_TW | Retained_PW |
|---|---|---|---|---|---|---|---|---|---|---|
| 601:103 | Appling County High School | 42 | 0 | 0 | 0 | 0 | 21 | 50 | 19 | 45.2 |
| 601:1050 | Altamaha Elementary School | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 14 | 100 |
| 601:177 | Appling County Elementary School | 21 | 0 | 0 | 0 | 0 | 7 | 33.3 | 9 | 42.9 |

#### Sample Data (2009, Era 3b)

Columns are identical to Era 4 (see below); the only differences are the two stray `__UNNAMED__*` columns (drop) and the lack of a `Total Retained` top-level column (derive by summing race columns).

#### Statistics and Detail Level Counts (Era 3)

| Year | Rows | Schools | Districts (`*:ALL`) | State (`ALL:ALL`) | Suppression marker |
|------|------|---------|---------------------|-------------------|-------------------|
| 2007 | 2,346 | 2,161 | 184 | 1 | `NULL` (literal string, 8 rows) |
| 2008 | 2,392 | 2,206 | 185 | 1 | (no marker observed — 0 non-numeric values in metrics) |
| 2009 | 2,415 | 2,227 | 187 | 1 | (suppression encoded as **null** — 882 rows with null metrics across the board) |

#### Suppression Markers (Era 3)

| Year | How suppression is encoded |
|------|---------------------------|
| 2007 | The literal string `NULL` appears in metric columns (8 rows across all columns). Separately there is no `Total Retained` column, so overall suppression doesn't directly apply — suppression is at the per-demographic cell level. |
| 2008 | **No suppression marker observed.** All metric cells parse as numbers. Either suppression did not occur this year or it's encoded in a way Polars doesn't detect (unlikely). |
| 2009 | Suppression encoded as **Polars null** (empty cells). Every suppressed row has all 26 metric columns null simultaneously (882 rows). |

### Era 4: 2004–2006, 2010 (long-name layout, pre-School-Year)

Same broad column layout as Era 3b (2009), minus the two stray `__UNNAMED__*` columns, and with a varying number of race denominator copies.

**Sub-era 4a: 2004–2006** — 26 columns (identical column names across the three years). Same shape as 2009 minus the two stray columns.

| Column | Description |
|--------|-------------|
| SysSchoolid | `districtcode:schoolcode`, or `districtcode:ALL` for district aggregate, or `ALL:ALL` for state. |
| School Name | School/district name (or `State of Georgia` for state row). |
| Retained Total Students | **Total Retained** (CORRECTED — not total enrolled; see Summary). |
| Retained Total American Indian | Retained American Indian count. |
| Retained Percent American Indian | Share of retained who are American Indian. |
| Retained Asian, Retained Black, Retained Female, Retained Hispanic, Retained Male, Retained Multiracial, Retained White | All 7 equal `Retained Total Students` (verified: 100% match in 2004, 2005, 2006). Redundant denominators; **drop**. |
| Retained Total Asian, Retained Total Black, Retained Total Female, Retained Total Hispanic, Retained Total Male, Retained Total Multiracial, Retained Total White | Retained counts by demographic. |
| Retained Percent Asian, Retained Percent Black, Retained Percent Female, Retained Percent Hispanic, Retained Percent Male, Retained Percent Multiracial, Retained Percent White | Share-of-retained percentages by demographic. |

**Sub-era 4b: 2010** — 19 columns. This year collapsed Era 4a's structure by removing the redundant `Retained {Demographic}` denominator columns (which always duplicated `Retained Total Students`). The remaining columns match 4a exactly except the 7 redundant ones are gone. Note: the `Retained Total American Indian` and `Retained Percent American Indian` pair stays, but the `Retained Asian`/`Retained Black`/etc. columns are dropped.

| Column | Description |
|--------|-------------|
| SysSchoolid | As above. |
| School Name | As above. |
| Retained Total Students | **Total Retained** (CORRECTED — not total enrolled), or the literal string `Too Few Students`. |
| Retained Total American Indian | Retained count or `Too Few Students`. |
| Retained Percent American Indian | Percent or `Too Few Students`. |
| Retained Total Asian | Retained count or `Too Few Students`. |
| Retained Percent Asian | Percent or `Too Few Students`. |
| Retained Total Black | Retained count or `Too Few Students`. |
| Retained Percent Black | Percent or `Too Few Students`. |
| Retained Total Female | Retained count or `Too Few Students`. |
| Retained Percent Female | Percent or `Too Few Students`. |
| Retained Total Hispanic | Retained count or `Too Few Students`. |
| Retained Percent Hispanic | Percent or `Too Few Students`. |
| Retained Total Male | Retained count or `Too Few Students`. |
| Retained Percent Male | Percent or `Too Few Students`. |
| Retained Total Multiracial | Retained count or `Too Few Students`. |
| Retained Percent Multiracial | Percent or `Too Few Students`. |
| Retained Total White | Retained count or `Too Few Students`. |
| Retained Percent White | Percent or `Too Few Students`. |

#### Sample Data (2004, Era 4a)

| SysSchoolid | School Name | Retained Total Students | Retained Total Asian | Retained Percent Asian | Retained Total Black | Retained Percent Black | Retained Total White | Retained Percent White |
|---|---|---|---|---|---|---|---|---|
| 601:1050 | Altamaha Elementary School | 12 | 0 | 0 | 2 | 16.7 | 9 | 75 |
| 601:277 | Appling County Primary School | 9 | 0 | 0 | 0 | 0 | 9 | 100 |
| 602:ALL | Atkinson County | 100 | 0 | 0 | 14 | 14 | 48 | 48 |
| ALL:ALL | State of Georgia | 58302 | … | … | … | … | 21974 | 37.7 |

#### Sample Data (2010, Era 4b)

| SysSchoolid | School Name | Retained Total Students | Retained Total Black | Retained Percent Black | Retained Total Male | Retained Percent Male |
|---|---|---|---|---|---|---|
| 601:103 | Appling County High School | 49 | 13 | 26.5 | 30 | 61.2 |
| 601:1050 | Altamaha Elementary School | 10 | 0 | 0 | Too Few Students | Too Few Students |
| 601:109 | Baxley Wilderness Institute | 0 | 0 | 0 | 0 | 0 |
| ALL:ALL | State of Georgia | 59999 | 29629 | 49.4 | 36874 | 61.5 |

#### Statistics and Detail Level Counts (Era 4)

| Year | Rows | Schools | Districts (`*:ALL`) | State (`ALL:ALL`) | Suppression marker |
|------|------|---------|---------------------|-------------------|-------------------|
| 2004 | 1,996 | 1,817 | 178 | 1 | (none observed) |
| 2005 | 2,254 | 2,069 | 184 | 1 | `NULL` (literal string, 5 rows) |
| 2006 | 2,285 | 2,100 | 184 | 1 | `NULL` (literal string, 5 rows) |
| 2010 | 2,506 | 2,314 | 191 | 1 | `Too Few Students` (widespread — 1,469 rows in `Retained Total Female`, etc.) |

Note: 2010 also has a handful of **actual null cells** (1–2 per column) in addition to the `Too Few Students` markers — these are rare data gaps, not suppression.

#### Suppression Markers (Era 4)

| Year | How suppression is encoded |
|------|---------------------------|
| 2004 | No marker observed — 0 non-numeric values in metric columns. |
| 2005–2006 | The literal string `NULL` (5 rows each). |
| 2010 | The literal string `Too Few Students` (same as Era 2a). Additionally, 1–2 nulls per column. |

## ETL Considerations

### Era boundaries and column renaming

- **Four distinct eras** × two sub-eras = six schemas in total across 21 years. Every era except Era 1→Era 2 changes the column naming convention. A tidy transform should build a per-era reader that emits a unified canonical schema (`year`, `detail_level`, `district_code`, `school_code`, `total_enrolled`, `total_retained`, then one `Number_of_{demographic}` and one `Percentage_of_{demographic}` pair per demographic).
- Recommended canonical demographic keys (matching the global demographics dimension): `american_indian`, `asian`, `black`, `hispanic`, `multiracial`, `white`, `female`, `male`. **There is NO `all_students` breakdown** — the overall total is a single metric pair (`total_retained`, derived retention rate), not a demographic.

### Two file-extension traps

- **2005 and 2006 have a `.csv` extension but are OLE2 Excel files.** Detect at runtime by sniffing the first 4 bytes (`\xd0\xcf\x11\xe0`), or hard-code to use `pl.read_excel()` for those two years. Reading with `pl.read_csv` raises `ComputeError: CSV malformed`.
- **2007.xls, 2008.xls, 2009.xls are legacy .xls (BIFF8).** Polars 1.x handles these via its built-in xlsx/xls readers, but if Polars ever drops `.xls` support, fall back to `pandas.read_excel(..., engine="xlrd")` (xlrd is already in the lock file via a transitive dependency).

### Excel sheet selection

- 2005.csv, 2006.csv, 2007.xls, 2008.xls each have `Sheet1, Sheet2, Sheet3` where only `Sheet1` has data. Sheets 2 and 3 are empty — raising `NoDataError` on read. Use `sheet_name="Sheet1"` or `sheet_id=1` explicitly.
- 2009.xls has a single sheet `Retained`.
- 2012.xlsx has `Export Worksheet` (data) and `SQL` (empty placeholder). Use `sheet_name="Export Worksheet"` or `sheet_id=1`.

### Year column derivation

- **Eras 1–2 (2011–2024):** derive `year` from the `School Year` / `School_Year` column by taking the last two digits and adding `2000` (e.g., `2023-24` → `2024`), or simply from the filename.
- **Eras 3–4 (2004–2010):** no `School Year` column. Derive `year` from the filename only. The filename year is the ending calendar year of the school year (e.g., `retained_students_2004.csv` → `2003-04` school year → `year = 2004`).

### Detail level and geography derivation

- **Eras 1–2 (2011–2024):** Use the explicit `Data Reporting Level` / `Data_Reporting_Level` column (values `State`, `District`, `School`) and the separate `School District Code` and `School Code` columns. Apply the standard education nulling rule from `src/etl/education/CLAUDE.md`: state rows → null both geography keys, district rows → null `school_code`, school rows → keep both.
- **Eras 3–4 (2004–2010):** Geography is packed into the single `SysSchoolid` column using a `districtcode:schoolcode` format. Derivation:
  - `SysSchoolid == "ALL:ALL"` → `detail_level = "state"`, `district_code = null`, `school_code = null`
  - `SysSchoolid` ends with `":ALL"` (but isn't `ALL:ALL`) → `detail_level = "district"`, `district_code = left side, zfill(3)`, `school_code = null`
  - Otherwise → `detail_level = "school"`, `district_code = left side zfill(3)`, `school_code = right side zfill(4)`
- The state row's `School Name` (Eras 3b/4) is `State of Georgia`; keep the sentinel detection on `SysSchoolid`, not on the name string.

### Four distinct suppression representations

The transform must normalize these to Polars null **before** casting to numeric:

| Era | Marker | Replace-with-null before cast |
|-----|--------|-------------------------------|
| Era 1 (2023–2024) | `TFS` | `.str.replace("TFS", "", literal=True)` then cast, or `pl.when(col == "TFS").then(None).otherwise(col)` |
| Era 2a (2011–2020) | `Too Few Students` | same, replace `Too Few Students` |
| Era 2b (2021–2022) | `TFS` | same, replace `TFS` |
| Era 3a (2007–2008) | (rare) literal `NULL` string (8 rows/yr in 2007; 0 in 2008) | replace `NULL` |
| Era 3b (2009) | Polars null (empty cell) | no-op (already null) |
| Era 4a (2004–2006) | (rare) literal `NULL` string (5 rows in 2005/2006) | replace `NULL` |
| Era 4b (2010) | `Too Few Students`; occasional true nulls | replace `Too Few Students` |

A single safe replace-list covering all eras: `["TFS", "Too Few Students", "NULL"]`. Empty-string and existing Polars nulls pass through as null.

### Redundant denominator columns — DROP

Eras 3a, 3b, and 4a all include per-demographic **copies of `Retained Total Students`**:

- Era 3a (2007–2008): `Retained_NN, _NA, _NB, _NF, _NH, _NM, _NU, _NW` — all eight always equal. Keep one as `total_enrolled`, drop the other seven.
- Era 3b (2009) and Era 4a (2004–2006): `Retained Asian`, `Retained Black`, `Retained Female`, `Retained Hispanic`, `Retained Male`, `Retained Multiracial`, `Retained White` — all seven always equal `Retained Total Students` (verified 100% match on the 2004/2005/2006 files, and on the non-null rows of 2009). Drop all seven.

### Total Retained across eras (CORRECTED 2026-06-11)

This section originally claimed Era 3a's total retained must be derived from gender sums and that `Retained_NN` / `Retained Total Students` were enrollment. Both claims were wrong (see Summary for the full evidence):

- Era 1–2 (2011–2024) has both `Total Enrolled` and `Total Retained` → an overall retention rate is computable (`Total Retained / Total Enrolled`) — except 2012, whose `Total Enrolled` is corrupt (below).
- Era 3a (2007–2008): `Retained_NN` **is** the published total retained (verified: equals `TM + TF` and the 6-race-bucket sum on every row of both files). No derivation needed. There is NO enrollment column.
- Era 3b/4 (2004–2006, 2009, 2010): `Retained Total Students` **is** the published total retained (verified: equals the gender sum and the race sum at every row where all components are published — 0 mismatches). There is NO enrollment column.
- Consequence for gold: `student_count` (enrollment) can only be populated for 2011 and 2013–2024.

### 2012 `Total Enrolled` is corrupt — inflated ~17x (added 2026-06-11)

The 2012 file's `Total Enrolled` is impossible at every detail level: the state row publishes 27,864,309 vs 1,633,596 (2011) and 1,657,506 (2013); districts and schools show the same ~17x inflation (e.g., large districts in the millions). `Total Retained` for 2012 (56,406 state) is internally consistent (race and gender sums match). The transform NULLs `student_count` for all 2012 rows per data-cleaning-standards §4b and preserves `retained_count`.

### 2009 `Retained Percent White` / `Retained Percent Multiracial` are corrupt (added 2026-06-11)

In the 2009 file only, these two percent columns are wrong: at the state row both publish 61.1 — the Male share — vs derived values of 32.5 (White) and 2.6 (Multiracial); file-wide, 656 White and 57 Multiracial rows are off by >1pp from `count / Retained Total Students`. Every other demographic and every other year matches the count-derived share within 1pp (apparent mismatches elsewhere are all `total = 0` rows where 0/0 is undefined and bronze publishes 0). The counts themselves are internally consistent in 2009, so the transform derives those two shares from `count / total` instead of passing the published percents through.

### 2010 duplicate and malformed rows (added 2026-06-11)

- One malformed row with `SysSchoolid = " Few Students"` (no colon, all metrics NULL) — an export artifact of a misparsed `Too Few Students` cell. Dropped by the transform.
- 53 `SysSchoolid` keys appear exactly twice (106 rows): 52 pairs are byte-identical; one key (`746:4050`, Chattanooga Valley Elementary) has a second row with extra suppressed (NULL) cells. The transform dedups at the bronze stage keeping the most complete row per key. No other year has duplicate keys (2004–2009 verified: 0).

### 2022 mislabeled school-level aggregate rows (added 2026-06-11)

The 2022 file labels 2 rows `Data Reporting Level = School` while carrying `School Code = ALL` — the district-aggregate rows of state-charter districts `7830627` and `7830636` (the same defect appears in the 2022 files of other GOSA topics, e.g. dropout_rate_9_12). 2022 has no genuine District rows for those codes. The transform reclassifies them to district detail. No other year has School+`ALL` rows.

### District code / school code formatting from `SysSchoolid`

The left side of `SysSchoolid` is the 3-digit GOSA district code (or 7-digit charter code for a handful of charter LEAs — verify). The right side is the 4-digit school code (or `ALL`). Both must be cast to `pl.Utf8` and zero-padded via `.str.zfill(3)` / `.str.zfill(4)` per `src/etl/education/CLAUDE.md`. Never truncate or slice.

Example rows observed: `601:103`, `601:1050`, `644:293`, `718:ALL`, `ALL:ALL`. The `:` split is reliable because neither half contains a colon.

### 2016 has 8 rows with null `Total Enrolled`

A minor data gap. Those rows still carry a `Total Retained` value. Decide whether to keep, null the rate, or drop — preferred is to keep the row and compute `retention_rate_overall = null` for that geography in that year.

### 2009 stray `__UNNAMED__26` / `__UNNAMED__27` columns

Both are almost entirely null (2,400+ nulls out of 2,415 rows). They are Excel-range artifacts from the original workbook (likely a stray chart or formula cell). **Drop** them.

### Demographic mapping

The 8 demographic breakdowns in this dataset map to the global demographics dimension as follows:

| Bronze label (Era 1–2) | Bronze label (Era 3a 2007–2008) | Demographic key |
|------------------------|--------------------------------|-----------------|
| `American Indian` | `N` (e.g., `Retained_TN`, `_PN`) | `native_american` (global dim key; corrected 2026-06-11 — the dim has no `american_indian_alaskan` key) |
| `Asians` | `A` | `asian_pacific_islander` — CONFIRMED 2026-06-11 via the §5b math test: the 6 race-bucket retained counts sum exactly to the total retained at the state row in every year 2004–2024 (0 row-level mismatches where all components are published), so Pacific Islanders are folded into the "Asian" bucket (pre-1997 OMB combined convention), not dropped |
| `Black` | `B` | `black` |
| `Hispanic` | `H` | `hispanic` |
| `MultiRacial` | `U` (Unclassified?) | `multiracial` |
| `White` | `W` | `white` |
| `Male` | `M` | `male` |
| `Female` | `F` | `female` |

The Era 3a letter-code `U` is inferred to mean "Multiracial" from column position (after `M`, before `W`) and from the fact that Era 3b (2009) uses the same column order as Era 4a and places `Multiracial` in that slot. Verify by comparing 2007→2008→2009 counts at the state row.

NO era contains `Pacific Islander` as a separate category (that split appeared in other GOSA datasets in 2018+, never in this one). RESOLVED 2026-06-11: the global dimension has both `asian` and `asian_pacific_islander`; this topic maps the bare `Asian`/`Asians` label to **`asian_pacific_islander`** (combined bucket), proven by the §5b math test above.

### Percentage scale — keep 0–100

The percentages in every era are 0–100 integers or one-decimal-place floats. Per `data-cleaning-standards`, standard percentages should be converted to 0-1 — confirm with the skill, but the raw scale is 0–100 consistently across all 21 files.

### Row-count sanity check

Rows per file are remarkably stable at ~2,400–2,520 (mostly schools plus ~180–220 district aggregates and 1 state row). A dramatic deviation in a future refresh would indicate a schema change.

## Gold Schema Classification

For each bronze column (across all eras), classify its role in the gold star schema:

| Bronze Column(s) | Gold Role | Gold Name | Notes |
|------------------|-----------|-----------|-------|
| `#RPT_NAME` (Era 1 only) | not_in_gold | — | Constant `"Retained K-12"` — no information. |
| `School Year` / `School_Year` (Era 1–2) | fact_key | `year` | Convert `YYYY-YY` → ending 4-digit year as `pl.Int32`. Eras 3–4: derive from filename. |
| `Data Reporting Level` / `Data_Reporting_Level` (Era 1–2) | not_in_gold | — | Drives output file split (`states.parquet`/`districts.parquet`/`schools.parquet`) and geography nulling. Not in fact rows. |
| `School District Code` / `School_District_Code` (Era 1–2) | fact_key | `district_code` | `pl.Utf8`, `.str.zfill(3)`. Null for state rows. `ALL` sentinel → null. |
| `School District Name` / `School_District_Name` (Era 1–2) | dimension_attribute | — | `district_name` in `districts.parquet`. Sentinel `All Column Values` excluded. |
| `School Code` / `School_Code` (Era 1–2) | fact_key | `school_code` | `pl.Utf8`, `.str.zfill(4)`. Null for state and district rows. `ALL` sentinel → null. |
| `School Name` / `School_Name` (Era 1–2) | dimension_attribute | — | `school_name` in `schools.parquet`. Sentinel excluded. |
| `SysSchoolid` (Era 3–4) | fact_key (derived) | `district_code` + `school_code` | Split on `:`. See ETL Considerations for nulling rules. |
| `School Name` / `SchoolNme` (Era 3–4) | dimension_attribute | — | Same dimension destination. (Typo `SchoolNme` in 2007–2008 must be renamed.) State row value `State of Georgia` is a sentinel — exclude. |
| `Grades Served` / `Grades_Served` (Era 1–2 only) | not_in_gold | — | Institution metadata (same across demographics within a row). Not a fact metric. Could optionally land on the schools dimension, but not required. |
| `Total Enrolled` / `Total_Enrolled` (Era 1–2 ONLY) | fact_metric | `student_count` | `pl.Int64`, on the `demographic = all` row only. Drop `TFS`/`Too Few Students` → null, then cast. The float formatting (`3237.00000`) in Era 1 must be handled by casting via `Float64` first. NULL for every 2004–2010 row (no enrollment in the wide eras — CORRECTED) and all of 2012 (corrupt source, §4b mask). |
| `Total Retained` / `Total_Retained` (Era 1–2) / `Retained_NN` (Era 3a) / `Retained Total Students` (Era 3b–4) | fact_metric | `retained_count` (on `demographic = all` row) | `pl.Int64`. Drop suppression markers → null, then cast. CORRECTED: the wide-era columns ARE the total retained; no gender-sum derivation is needed in any era. |
| (derived retention rate) | not_in_gold | — | CORRECTED: gold does not emit a retention-rate column; consumers compute `retained_count / student_count` on `demographic = all` rows (2011, 2013–2024 only). |
| `Number of {demo}` / `Number_of_{demo}` (Era 1–2) / `Retained Total {demo}` (Era 3b–4) / `Retained_T{x}` (Era 3a) | fact_metric | `retained_count` (on the demographic's row, long format) | `pl.Int64`. Drop suppression markers → null, then cast. |
| `Percentage of {demo}` / `Percentage_of_{demo}` (Era 1–2) / `Retained Percent {demo}` (Era 3b–4) / `Retained_P{x}` (Era 3a) | fact_metric | `pct_of_retained_cohort` (on the demographic's row, long format) | `pl.Float64`, converted to 0–1 scale (share of total retained who belong to this demographic; §16 canonical name). Drop suppression markers → null, then cast. 2009 White/Multiracial derived from counts (corrupt percents — see ETL Considerations). |
| `Retained Asian` / `Retained Black` / `Retained Female` / `Retained Hispanic` / `Retained Male` / `Retained Multiracial` / `Retained White` (Era 3b, 4a) | not_in_gold | — | Redundant duplicates of `Retained Total Students`. Verified 100% equal in 2004/2005/2006/2009 non-null rows. |
| `Retained_NA` / `_NB` / `_NF` / `_NH` / `_NM` / `_NU` / `_NW` (Era 3a) | not_in_gold | — | Redundant duplicates of `Retained_NN`. Verified 100% equal in 2007. |
| `__UNNAMED__26` / `__UNNAMED__27` (Era 3b / 2009 only) | not_in_gold | — | Stray Excel artifact cells. Drop. |

**Considerations for tidy output.** The wide-format demographic metrics (`Number_of_Asians`, `Percentage_of_Asians`, `Number_of_Black`, …, 16 columns) may optionally be melted into a long-format demographic dimension per `data-cleaning-standards`, producing two metrics (`retained_count`, `retained_pct_of_retained`) per `(year, geography, demographic)` row. Decide at transform time whether to keep the wide layout (faster analytical queries, but many columns) or go long (consistent with other GOSA topics like `dropout_rate_9_12`). The long format is consistent with the global `demographic` dimension and is the recommended shape for this topic. There is **no `all_students` total** in this dataset — the `demographic` column omits `all_students`, and `total_retained` / `retention_rate_pct` / `total_enrolled` live at the row-level (not keyed by demographic), so the long fact table has **(geography) × (demographic)** granularity for the demographic-breakdown metrics and **(geography)** granularity for the overall metrics. This means the long-format fact will need either (a) a separate `all_students` demographic pseudo-key to hold the overall metrics, or (b) the overall metrics to be duplicated across every demographic row. Approach (a) is cleaner and matches the pattern used in `dropout_rate_9_12`.

**RESOLVED 2026-06-11 (transform implemented):** long format with approach (a) — the overall metrics live on a synthetic `demographic = 'all'` row (`retained_count` + `student_count`; `pct_of_retained_cohort` NULL there, 100% by definition). Gold columns: `year`, `district_code`, `school_code`, `demographic`, `retained_count`, `student_count`, `pct_of_retained_cohort`. No retention-rate column is emitted.
