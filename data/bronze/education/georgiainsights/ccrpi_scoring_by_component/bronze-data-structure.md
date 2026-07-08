# ccrpi_scoring_by_component - Bronze Data Structure

## Overview

- Topic: ccrpi_scoring_by_component
- Source: georgiainsights
- Files: 12 files spanning 2012-2019 + 2022-2025 (no 2020/2021 files - COVID closure of CCRPI calculation)
- Unreadable files: none
- Year representation: `SCHOOL YEAR` / `School Year` column in every file (single integer per file, e.g., `2013`, `2024`). Each file contains exactly one school year. Stored as String in 2012-2013 and as Int64 from 2014 onward.
- Filename-to-data year offset: same (filename year = data year). Some filenames embed the publication date in MM.DD.YY form (e.g., `2014 CCRPI Scoring by Component.03.10.2016.xls`), but the in-file `School Year` column is the authoritative year.
- Detail levels: state, district, school (all 12 years have all three levels)
- Percentage scale: not a percentage. Component metrics are CCRPI point allocations (Era 1-2) or component scores on a 0-100 scale (Era 3-4). The aggregate CCRPI Score and Single Score (when present) are also 0-100 (can briefly exceed 100 in early years due to bonus points). Per the education domain CLAUDE.md "Percentage Scale Exceptions," these are NOT scaled to 0-1.
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: Georgia Insights (GaDOE) public data downloads — exact page URL not recorded at acquisition time
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| 2012 Scoring By Component for Public Release.xls | 09a2013327f7422b4df0b006d635352f9ac67eb25e8a784e05ad02473801407b |
| 2013 Scoring By Component for Public Release v2.xls | 1815b4318875646be2635075bf8cb1d3b8435488989a78e5d3dd5dd3f798b4e9 |
| 2014 CCRPI Scoring by Component.03.10.2016.xls | f808c46c1107aeafae714d353ade0193dd854c2f5510cd97554689ac54f042a8 |
| 2015 CCRPI Scoring By Component 07.14.16.xlsx | 5d638e12595fe3187114a1ebdc5a79f463eeb77e6ca6db25eb9d5216829f34e8 |
| 2016 Scoring by Component_12.08.16.xlsx | fb3fff57087a4597df5ff61fee7e15ca8ef2d67d0940e97f57da7a6cf048043d |
| 2017 CCRPI Scoring by Component 11.2.17.xlsx | 818659dfcb1dda6811b2ff88b39a861dabd68077e9bcc356af1f13eb9f19f24c |
| 2018 CCRPI Scoring by Component_12_14_18.xlsx | f780d379c681cecefba7899b29b38be64bb840255cd28e7960333616e04f9892 |
| 2019 CCRPI Scoring by Component_04_01_20.xls | b72fad53b134943fe44561598efa44a521d43b048cc88a20c7bcb44825fc21db |
| 2022 CCRPI Scoring by Component 11.16.22.xlsx | 0f088dc25c0c1098715e9aef91b486a24316ed79755d5ec59c687235a0afe267 |
| 2023 CCRPI Scoring by Component_12_14_23.xlsx | b1b43ff0faffa9bb1831e8c28fee491c6e06e7ad396e3fc35aa9d7ab42dc4845 |
| 2024 CCRPI Scoring by Component.xlsx | 080756150c2ae569abfc52187a015b868a61d56f14ee5f8415f4a1d2db3906a4 |
| 2025 CCRPI Scoring by Component.xlsx | 8ec7c68b39df3994fdb169d279c52a1fdfbe5db109052ed8866ed87798d4f758 |

## Excel Sheet Structure

| File(s) | Sheets | Notes |
|---------|--------|-------|
| 2012 | Sheet1 (Data), Sheet2 (empty), Sheet3 (empty) | All data is in Sheet1; Sheet2 and Sheet3 raise polars `empty Excel sheet` errors and must be skipped. |
| 2013 | Sheet1 (Data), Sheet2 (empty), Sheet3 (empty) | Same as 2012 — only Sheet1 has data. |
| 2014, 2015, 2016 | Sheet 1 (Data) | Single data sheet. Note the space — `Sheet 1`, not `Sheet1`. |
| 2017 | 2017_CCRPI Scoring by Component (Data) | Single data sheet, custom name. |
| 2018, 2019 | CCRPI Scoring by Component (Data) | Single data sheet, consistent name. |
| 2022 | CCRPI Scoring by Component (Data), FAQs (Metadata) | **Disclaimer in row 0 above headers** — must use `read_options={'header_row': 1}` in `pl.read_excel()`. The FAQs sheet should be skipped. The disclaimer text explains the COVID-related modification (no CCRPI Score, Single Score, Progress, or Closing Gaps reported). |
| 2023 | CCRPI by Component (Data) | Single data sheet (note: sheet name omits "Scoring", unlike all surrounding years). |
| 2024, 2025 | CCRPI Scoring by Component (Data) | Single data sheet. |

No multi-sheet concatenation is required — every file's data lives on a single populated sheet. The 2012/2013 empty-sheet error and the 2022 disclaimer-row offset are the only sheet-level quirks.

## Summary

This dataset reports the components of the College and Career Ready Performance Index (CCRPI) — Georgia's public school accountability score — broken out by `Grade Cluster` (Elementary, Middle, High) at the state, district, and school levels. The exact metric set evolves substantially:

- **2012-2017** report **CCRPI component points** that sum into the overall score: `Achievement Points` (max ~60), `Progress Points` (max ~22), `Achievement Gap Points` (max 15), `ED/EL/SWD Performance` (max 10), `ETB Points` (max 2-3, then 2.5), `Challenge Points` (max 10), plus the aggregated `CCRPI Score` and `Single Score` (both ~0-110 on a 0-100 scale with bonus points).
- **2018-2019, 2022** report **CCRPI component scores** on a 0-100 scale: `Content Mastery`, `Progress`, `Closing Gaps`, `Readiness`, `Graduation Rate`, plus the aggregated `CCRPI Score` and `Single Score`. The 2022 file has Progress, Closing Gaps, CCRPI Score, and Single Score uniformly suppressed to `NA` per a federally-approved one-year COVID modification.
- **2023-2025** report the same five component scores (Content Mastery / Progress / Closing Gaps / Readiness / Graduation Rate) but **drop the aggregated CCRPI Score and Single Score columns entirely**.

The grain is one row per (school or district or state aggregate) × `Grade Cluster`; there is no demographic subgroup breakdown in this dataset.

## Eras

### Era 1: 2012-2013

**Files**: `2012 Scoring By Component for Public Release.xls` (Sheet1), `2013 Scoring By Component for Public Release v2.xls` (Sheet1)

**Columns** (UPPERCASE; **2013 has a trailing space on `SCHOOL ID `**):
`SCHOOL YEAR`, `SYSTEM ID`, `SYSTEM NAME`, `SCHOOL ID` (or `SCHOOL ID ` in 2013), `SCHOOL NAME`, `GRADE CLUSTER`, `ACHIEVEMENT POINTS`, `PROGRESS POINTS`, `ACHIEVEMENT GAP POINTS`, `ED/EL/SWD PERFORMANCE`, `ETB POINTS`, `CHALLENGE POINTS`, `CCRPI SCORE`, `SINGLE SCORE`

| Column | Description |
|--------|-------------|
| SCHOOL YEAR | Single integer year as String (e.g., `"2012"`, `"2013"`). |
| SYSTEM ID | District code as String. `"ALL"` indicates the state aggregate (3 rows per file, one per Grade Cluster). 7-digit codes (e.g., `"7820108"`, `"7991895"`) are charter / state-school operators. |
| SYSTEM NAME | District name (e.g., `"Appling County"`, `"DeKalb County"`, `"State Charter Schools- ..."`); `"All Systems"` for state rows. |
| SCHOOL ID | School code as String (4-digit zero-padded, e.g., `"0103"`); `"ALL"` for district aggregate rows (570 in 2012, 574 in 2013). |
| SCHOOL NAME | School name; `"All Schools"` for district aggregate and state aggregate rows. |
| GRADE CLUSTER | `E`, `M`, `H` (Elementary / Middle / High). |
| ACHIEVEMENT POINTS | CCRPI Achievement points (max ~60). String with `NA` for suppressed rows. |
| PROGRESS POINTS | CCRPI Progress points (max ~22). String with `NA` for suppressed rows. |
| ACHIEVEMENT GAP POINTS | CCRPI Achievement Gap points (max 15). String with `NA` for suppressed rows. |
| ED/EL/SWD PERFORMANCE | Subgroup performance points (max 10). String with `NA` for suppressed rows; column itself can also be null (82 nulls in 2013 — a true null, not the `NA` sentinel). |
| ETB POINTS | Exceeding the Bar bonus points (max 2.0 in 2012-2013). String with `NA` for suppressed rows. |
| CHALLENGE POINTS | Challenge bonus points (max 10). String with `NA` for suppressed rows. |
| CCRPI SCORE | Aggregated CCRPI score on 0-100 scale (max 99.4 in 2012, 103.6 in 2013). String with `NA` for suppressed rows. |
| SINGLE SCORE | Single (overall) school score on 0-100 scale (always populated; max 99.4 / 103.6). String. |

#### Sample Data (2013)

```
shape: (5, 14)
| SCHOOL YEAR | SYSTEM ID | SYSTEM NAME     | SCHOOL ID  | SCHOOL NAME                                 | GRADE CLUSTER | ACHIEVEMENT POINTS | PROGRESS POINTS | ACHIEVEMENT GAP POINTS | ED/EL/SWD PERFORMANCE | ETB POINTS | CHALLENGE POINTS | CCRPI SCORE | SINGLE SCORE |
| 2013        | 766       | Carrollton City | 0193       | Carrollton Elementary School                | E             | 49.5               | NA              | 6                      | 4                     | 1          | 5                | 79          | 79           |
| 2013        | 625       | Chatham County  | 0115       | Woodville-Tompkins Tech & Career High Schl. | H             | 46.7               | 20              | 15                     | 6.9                   | .5         | 7.4              | 89.1        | 89.1         |
| 2013        | 663       | Glynn County    | 4752       | Glynn Academy                               | H             | 47.2               | 16.1            | 13.8                   | 3.4                   | 0          | 3.4              | 80.5        | 80.5         |
| 2013        | 628       | Cherokee County | ALL        | All Schools                                 | H             | 48.8               | 17.3            | 11.3                   | 2.9                   | 0          | 2.9              | 80.3        | 79.7         |
| 2013        | 625       | Chatham County  | ALL        | All Schools                                 | M             | 43.2               | 15.3            | 7                      | .9                    | 0          | .9               | 66.4        | 71.3         |
```

#### Statistics (2013)

Row count: 2,968. All columns are String. ED/EL/SWD PERFORMANCE has 82 true nulls; all other suppressed values are stored as the literal `"NA"` string. SCHOOL YEAR is constant `"2013"`. SYSTEM ID `min` is `"601"`, `max` is `"ALL"` (alphabetic order).

#### Null Counts (2013)

| SCHOOL YEAR | SYSTEM ID | SYSTEM NAME | SCHOOL ID | SCHOOL NAME | GRADE CLUSTER | ACHIEVEMENT POINTS | PROGRESS POINTS | ACHIEVEMENT GAP POINTS | ED/EL/SWD PERFORMANCE | ETB POINTS | CHALLENGE POINTS | CCRPI SCORE | SINGLE SCORE |
|-------------|-----------|-------------|-----------|-------------|---------------|--------------------|-----------------|------------------------|-----------------------|------------|------------------|-------------|--------------|
| 0           | 0         | 0           | 0         | 0           | 0             | 0                  | 0               | 0                      | 82                    | 0          | 0                | 0           | 0            |

#### Categorical Columns (2013)

| Column | Distinct Values |
|--------|----------------|
| GRADE CLUSTER | E (1,540), M (792), H (636) |
| SYSTEM NAME | 199 distinct district names (top: DeKalb County 143, Gwinnett County 135, Cobb County 116, Atlanta Public Schools 109, Fulton County 107). Includes 7-digit charter / state-school operators. |
| SCHOOL NAME | 2,141 distinct school names; `All Schools` (577 rows) for district + state aggregates. |

#### Suppression Markers (2013)

| Column | Non-Numeric Values |
|--------|-------------------|
| SYSTEM ID | `ALL` (3 rows = state aggregate) |
| SCHOOL ID | `ALL` (577 rows = district + state aggregates) |
| ACHIEVEMENT POINTS | `NA` (22 rows) |
| PROGRESS POINTS | `NA` (120 rows) |
| ACHIEVEMENT GAP POINTS | `NA` (148 rows) |
| ED/EL/SWD PERFORMANCE | `NA` (22 rows; plus 82 true nulls noted above) |
| ETB POINTS | `NA` (22 rows) |
| CHALLENGE POINTS | `NA` (22 rows) |
| CCRPI SCORE | `NA` (22 rows) |
| SINGLE SCORE | none (always numeric) |

#### Era 1 cross-file notes

- 2012 file: 2,991 rows (3 state, 570 district, 2,418 school). The Grade Cluster split is E (1,554), M (797), H (640).
- 2013 file: 2,968 rows (3 state, 574 district, 2,391 school).
- **Trailing-space header in 2013**: `SCHOOL ID ` has an extra space after `ID`. Strip column whitespace before any per-column logic.
- All ID columns (`SYSTEM ID`, `SCHOOL ID`) are stored as String in this era. School IDs are already 4-digit zero-padded (e.g., `"0103"`).

### Era 2: 2014-2017

**Files**: `2014 CCRPI Scoring by Component.03.10.2016.xls` (Sheet 1), `2015 CCRPI Scoring By Component 07.14.16.xlsx` (Sheet 1), `2016 Scoring by Component_12.08.16.xlsx` (Sheet 1), `2017 CCRPI Scoring by Component 11.2.17.xlsx` (`2017_CCRPI Scoring by Component`)

**Columns** (Title Case; same set as Era 1 but adds **`Grade Configuration`**, and casing varies year to year):
`School Year`, `System ID` / `System Id`, `System Name`, `School ID` / `School Id`, `School Name`, `Grade Configuration`, `Grade Cluster`, `Achievement Points`, `Progress Points`, `Achievement Gap Points`, `ED/EL/SWD Performance`, `ETB Points`, `Challenge Points`, `CCRPI Score`, `Single Score`

| Column | Description |
|--------|-------------|
| School Year | Integer year, e.g., 2017. |
| System Id / System ID | District code. **2014-2016 store as String** (with `"ALL"` for state aggregate); **2017 stores as Int64** (with null for state aggregate). 7-digit codes are charters / state-school operators. |
| System Name | District name; `"All Systems"` for state aggregates; `"Residential Treatment Center"` appears as a state-level operator name in 2017 (3 rows, with `All RTC Schools` as School Name). |
| School Id / School ID | School code. Stored as String in all four years (`"ALL"` indicates district + state aggregates). |
| School Name | School name; `"All Schools"` for district / state aggregates; `"All RTC Schools"` for the 2017 RTC operator rows. |
| Grade Configuration | New in Era 2. Comma-separated list of grade levels offered (e.g., `"PK, KK, 01, 02, 03, 04, 05"`). 2014-2016 use no spaces (`"PK,KK,01,02,03,04,05,06,07,08,09,10,11,12"`); 2017 uses spaces after commas. |
| Grade Cluster | `E`, `M`, `H`. |
| Achievement Points | CCRPI Achievement points (max ~60). Stored as String in 2014-2016 (with `NA` suppression marker), Float64 in 2017. |
| Progress Points | CCRPI Progress points (max ~40 in 2017 due to the redesigned Progress component). String in 2014-2016, Float64 in 2017. |
| Achievement Gap Points | CCRPI Achievement Gap points (max 15 in 2014-2016, 10 in 2017). String in 2014-2016, Float64 in 2017. |
| ED/EL/SWD Performance | Subgroup performance points (max 10). String in 2014-2016, Float64 in 2017. |
| ETB Points | Exceeding the Bar bonus points (max 3.0 in 2014, 2.5 in 2017). String in 2014-2016, Float64 in 2017. |
| Challenge Points | Challenge bonus points (max 10). String in 2014-2016, Float64 in 2017. |
| CCRPI Score | Aggregated CCRPI score on 0-100 scale (max 102.1 in 2014, 108.7 in 2017). String in 2014-2016, Float64 in 2017. |
| Single Score | Single (overall) score on 0-100 scale (max 101.2 in 2014, 108.2 in 2017). String in 2014-2016, Float64 in 2017. |

#### Sample Data (2017)

```
shape: (5, 15)
| School Year | System ID | System Name     | School ID | School Name                          | Grade Configuration                                  | Grade Cluster | Achievement Points | Progress Points | Achievement Gap Points | ED/EL/SWD Performance | ETB Points | Challenge Points | CCRPI Score | Single Score |
| 2017        | 721       | Richmond County | 4762      | Terrace Manor Elementary School      | PK, KK, 01, 02, 03, 04, 05                           | E             | 16.0               | 32.0            | 6.7                    | 0.0                   | 0.0        | 0.0              | 54.7        | 54.7         |
| 2017        | 611       | Bibb County     | 298       | Miller Magnet Middle School          | 06, 07, 08                                           | M             | 23.3               | 31.0            | 5.0                    | 0.0                   | 1.0        | 1.0              | 60.3        | 60.3         |
| 2017        | 657       | Floyd County    | 4054      | Pepperell Primary                    | PK, KK, 01, 02                                       | E             | 37.9               | null            | null                   | null                  | 1.0        | 1.0              | null        | null         |
| 2017        | 636       | Columbia County | 103       | Grovetown Middle School              | 06, 07, 08                                           | M             | 29.8               | 31.4            | 5.0                    | 0.5                   | 1.0        | 1.5              | 67.7        | 67.7         |
| 2017        | 644       | DeKalb County   | 503       | East DeKalb Special Education Center | PK, KK, 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11   | E             | null               | null            | null                   | null                  | null       | null             | null        | null         |
```

#### Statistics (2017)

```
| statistic  | School Year | System ID | School ID | Achievement Points | Progress Points | Achievement Gap Points | ED/EL/SWD Performance | ETB Points | Challenge Points | CCRPI Score | Single Score |
| count      | 3069        | 3063      | 3069      | 2969               | 2862            | 2793                   | 2877                  | 2969       | 2969             | 2880        | 2909         |
| null_count | 0           | 6         | 0         | 100                | 207             | 276                    | 192                   | 100        | 100              | 189         | 160          |
| mean       | 2017.0      | 252002    | n/a       | 30.71              | 34.22           | 6.35                   | 2.11                  | 0.70       | 2.72             | 73.74       | 73.57        |
| std        | 0.0         | 1.38e6    | n/a       | 7.25               | 4.00            | 1.68                   | 2.24                  | 0.62       | 2.29             | 12.45       | 12.54        |
| min        | 2017        | 601       | 100       | 4.4                | 18.1            | 1.7                    | 0.0                   | 0.0        | 0.0              | 16.4        | 16.4         |
| 50%        | 2017        | 667       | n/a       | 30.6               | 34.6            | 6.7                    | 1.7                   | 0.5        | 2.2              | 73.9        | 73.8         |
| max        | 2017        | 7,991,895 | ALL       | 56.2               | 40.0            | 10.0                   | 10.0                  | 2.5        | 10.0             | 108.7       | 108.2        |
```

#### Null Counts (2017)

| School Year | System ID | System Name | School ID | School Name | Grade Configuration | Grade Cluster | Achievement Points | Progress Points | Achievement Gap Points | ED/EL/SWD Performance | ETB Points | Challenge Points | CCRPI Score | Single Score |
|-------------|-----------|-------------|-----------|-------------|---------------------|---------------|--------------------|-----------------|------------------------|-----------------------|------------|------------------|-------------|--------------|
| 0           | 6         | 0           | 0         | 0           | 0                   | 0             | 100                | 207             | 276                    | 192                   | 100        | 100              | 189         | 160          |

#### Categorical Columns (2017)

| Column | Distinct Values |
|--------|----------------|
| Grade Cluster | E (1,561), M (830), H (678) |
| System Name | 209 distinct district names. Includes `All Systems` (3 rows = state) and `Residential Treatment Center` (3 rows = RTC operator aggregate). |
| School Name | 2,176 distinct school names; `All Schools` (594 rows) for district + state aggregates; `All RTC Schools` for the 3 RTC operator rows. |
| Grade Configuration | 69 distinct grade-level combinations. Top values: `PK, KK, 01, 02, 03, 04, 05` (963), `PK, KK, 01..12` (576), `06, 07, 08` (437), `09, 10, 11, 12` (391). |

#### Suppression Markers (2017)

| Column | Non-Numeric Values |
|--------|-------------------|
| School ID | `ALL` (597 rows = district + state aggregates) |
| All metric columns | None (numeric Float64 with true nulls for suppressed rows) |

For 2014-2016 the suppression marker on every metric column is the literal string `"NA"` (same as Era 1), since those years store metrics as String. 2017 differs only because polars reads its metric columns as Float64 already.

#### Era 2 cross-file notes

- **Casing drift across years**:
  - 2014, 2015: `System Id` / `School Id` (lowercase `d`).
  - 2016: `System ID` / `School ID` (uppercase `ID`).
  - 2017: `System ID` / `School ID` (uppercase `ID`).
- **Grade Configuration spacing**: 2014-2016 use comma-only delimiters (`PK,KK,01,02,...`); 2017 inserts a space after each comma (`PK, KK, 01, 02, ...`). Era 3 and 4 follow the 2017 format.
- **Detail-level encoding**:
  - 2014-2016: state row has `System Id == "ALL"` (3 rows per year), district rows have `School Id == "ALL"`.
  - 2017: state rows have `System ID == null` (6 rows: 3 `All Systems` + 3 `Residential Treatment Center` operator aggregates with `All RTC Schools`); district rows still have `School ID == "ALL"`.
- Row counts: 2014 (2,978; 3 state / 579 district / 2,396 school), 2015 (3,060; 3/586/2,471), 2016 (3,079; 3/592/2,484), 2017 (3,069; 6/591/2,472).
- 2017 RTC operator rows are unusual — they have `System ID == null`, `School ID == "ALL"`, `System Name == "Residential Treatment Center"`, and `School Name == "All RTC Schools"`. They are not state-of-Georgia aggregates; they are aggregates over a class of facilities. The transform should decide whether to preserve them (and how to map them to the gold detail level) or drop them.

### Era 3: 2018-2019, 2022

**Files**: `2018 CCRPI Scoring by Component_12_14_18.xlsx` (CCRPI Scoring by Component), `2019 CCRPI Scoring by Component_04_01_20.xls` (CCRPI Scoring by Component), `2022 CCRPI Scoring by Component 11.16.22.xlsx` (CCRPI Scoring by Component, with `read_options={'header_row': 1}`)

**Columns** (Title Case; same column set across all three years, but **2018 embeds line breaks in 4 column names**):
`School Year`, `System ID`, `System Name`, `School ID`, `School Name`, `Grade Configuration`, `Grade Cluster`, `Content Mastery` (or `Content \nMastery` in 2018), `Progress`, `Closing Gaps` (or `Closing\nGaps` in 2018), `Readiness`, `Graduation Rate`, `CCRPI Score` (or `CCRPI\nScore` in 2018), `Single Score` (or `Single \nScore` in 2018)

| Column | Description |
|--------|-------------|
| School Year | Int64. |
| System ID | District code. **2018, 2022 store as Int64 (null for state aggregate); 2019 stores as String (`"ALL"` for state aggregate)**. |
| System Name | District name; `"All Systems"` for state. |
| School ID | School code as String (`"ALL"` for district + state aggregates). |
| School Name | School name; `"All Schools"` for district + state aggregates. |
| Grade Configuration | Comma+space-delimited grade list (`PK, KK, 01, 02, ...`). |
| Grade Cluster | `E`, `M`, `H`. |
| Content Mastery | 0-100 component score. **2018, 2022: stored as String/Float**; **2019, 2022: String with `NA` and `TFS` suppression markers** (2018 is mostly Float64 with a few nulls, no string sentinels). |
| Progress | 0-100 component score. **2022 is uniformly `"NA"` for every row** (federal COVID modification). Otherwise String/Float with `NA`, `TFS` suppression markers. |
| Closing Gaps | 0-100 component score. **2022 is uniformly `"NA"` for every row.** Otherwise String/Float with `NA`, `TFS` suppression markers. |
| Readiness | 0-100 component score. String/Float with `NA`, `TFS` (2019, 2022) or `Too Few Students`, `NA` (2018) suppression markers. |
| Graduation Rate | 0-100 component score; only populated for High-school rows (and a small number of K-12 / mixed configurations). **Most rows are `NA`** because elementary and middle schools have no graduation rate. String. |
| CCRPI Score | 0-100 aggregated score. **2022 is uniformly `"NA"`.** Otherwise String/Float with `NA` suppression marker. |
| Single Score | 0-100 single score (school-wide aggregate). **2022 is uniformly `"NA"`.** Otherwise String/Float with `NA` suppression marker. |

#### Sample Data (2019)

```
shape: (5, 14)
| School Year | System ID | System Name     | School ID | School Name                   | Grade Configuration                                    | Grade Cluster | Content Mastery | Progress | Closing Gaps | Readiness | Graduation Rate | CCRPI Score | Single Score |
| 2019        | 706       | Muscogee County | 0401      | Double Churches Middle School | 06, 07, 08                                             | M             | 47.7            | 71.9     | 37.5         | 74.6      | NA              | 60.0        | 60.0         |
| 2019        | 714       | Pike County     | ALL       | All Schools                   | PK, KK, 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12 | M             | 63.8            | 73.9     | 38.6         | 82.4      | NA              | 67.3        | 74.5         |
| 2019        | 644       | DeKalb County   | 0190      | Pine Ridge Elementary School  | PK, KK, 01, 02, 03, 04, 05                             | E             | 48.4            | 97.3     | 94.4         | 75.1      | NA              | 77.8        | 77.8         |
| 2019        | 628       | Cherokee County | 5050      | Cherokee High School          | 09, 10, 11, 12                                         | H             | 73.2            | 80.3     | 68.8         | 72.5      | 81.3            | 76.0        | 76.0         |
| 2019        | 746       | Walker County   | 0199      | Cherokee Ridge Elementary     | PK, KK, 01, 02, 03, 04, 05                             | E             | 70.3            | 98.3     | 100.0        | 79.3      | NA              | 86.4        | 86.4         |
```

#### Statistics (2019)

Row count: 3,138. All metric columns are String. No true nulls anywhere — every suppressed value is encoded as `NA` or `TFS`.

#### Null Counts (2019)

All columns: 0. All suppression is via text markers (`NA`, `TFS`) rather than blank cells.

#### Categorical Columns (2019)

| Column | Distinct Values |
|--------|----------------|
| Grade Cluster | E (1,577), M (854), H (707) |
| System Name | 212 distinct district names. |
| School Name | 2,184 distinct school names; `All Schools` (642) for district + state aggregates. |
| Grade Configuration | 74 distinct grade-level combinations (top: `PK, KK, 01, 02, 03, 04, 05` 965, `PK, KK, 01..12` 672, `06, 07, 08` 432, `09, 10, 11, 12` 387). |
| Graduation Rate | 256 "distinct values" — 254 numeric strings plus the suppression markers `NA` (2,475) and `TFS` (25). Treated as numeric-with-suppression below. |

#### Suppression Markers (2019)

| Column | Non-Numeric Values |
|--------|-------------------|
| System ID | `ALL` (3 rows = state aggregate) |
| School ID | `ALL` (642 rows = district + state aggregates) |
| Content Mastery | `TFS` (77), `NA` (60) |
| Progress | `TFS` (120), `NA` (83) |
| Closing Gaps | `NA` (171) |
| Readiness | `NA` (38), `TFS` (24) |
| Graduation Rate | `NA` (2,475), `TFS` (25) |
| CCRPI Score | `NA` (137) |
| Single Score | `NA` (69) |

#### Era 3 cross-file notes

- **2018 line breaks in column names**: `Content \nMastery`, `Closing\nGaps`, `CCRPI\nScore`, `Single \nScore` (note the inconsistent space-before-newline). Strip / normalize whitespace before name-based mapping. Also note 2018 metric columns are mostly Float64 (only `Readiness` is String, with `Too Few Students` (21) and `NA` (1) markers).
- **2018 suppression marker variant**: 2018 uses `"Too Few Students"` (full text) on `Readiness`, while 2019 and 2022 use the shortened `"TFS"`. Both years also use `"NA"`. The transform must accept both spellings.
- **2022 disclaimer row**: The first row of the data sheet is the long disclaimer text starting with `"Given the impact of pandemic-related data limitations..."`. Reading without `read_options={'header_row': 1}` causes polars to use the disclaimer as the header. **Always pass `read_options={'header_row': 1}` for the 2022 file.**
- **2022 has no usable Progress / Closing Gaps / CCRPI Score / Single Score**: every row in those four columns is the literal string `"NA"`. The federally-approved modification described in the disclaimer suspended the calculation of these components for the 2021-2022 school year. The transform should null these out (don't drop the rows — `Content Mastery`, `Readiness`, and `Graduation Rate` remain reportable).
- **System ID type drift inside the era**: 2018 and 2022 store `System ID` as Int64 (null = state); 2019 stores it as String (`"ALL"` = state). 2018/2022 Year is also Int64; 2019 Year is Int64. Always cast to String + zfill(3) per the education domain CLAUDE.md.
- Row counts: 2018 (3,099; 3 state / 604 district / 2,492 school), 2019 (3,138; 3/639/2,496), 2022 (3,200; 3/666/2,531).

### Era 4: 2023-2025

**Files**: `2023 CCRPI Scoring by Component_12_14_23.xlsx` (`CCRPI by Component`), `2024 CCRPI Scoring by Component.xlsx` (`CCRPI Scoring by Component`), `2025 CCRPI Scoring by Component.xlsx` (`CCRPI Scoring by Component`)

**Columns** (Title Case; same set as Era 3 minus `CCRPI Score` and `Single Score`):
`School Year`, `System ID`, `System Name`, `School ID`, `School Name`, `Grade Configuration`, `Grade Cluster`, `Content Mastery`, `Progress`, `Closing Gaps`, `Readiness`, `Graduation Rate`

| Column | Description |
|--------|-------------|
| School Year | Int64. |
| System ID | District code as Int64 (null for state aggregate). 7-digit codes (e.g., `7820108`, `7830647`) are charters. |
| System Name | District name; `"All Systems"` for state. |
| School ID | String (`"ALL"` for district + state aggregates). |
| School Name | School name; `"All Schools"` for district + state aggregates. |
| Grade Configuration | Comma+space-delimited grade list. |
| Grade Cluster | `E`, `M`, `H`. |
| Content Mastery | 0-100 component score. String with `NA`, `TFS` suppression markers. |
| Progress | 0-100 component score. String with `NA`, `TFS` suppression markers. |
| Closing Gaps | 0-100 component score. **Stored as Float64** in all three Era 4 files (true nulls, no string sentinels). |
| Readiness | 0-100 component score. String with `NA`, `TFS` suppression markers. |
| Graduation Rate | 0-100 component score; mostly `NA` (only High-cluster rows). String. |

**No CCRPI Score or Single Score columns.** The aggregated CCRPI / Single Score columns were dropped starting in 2023.

#### Sample Data (2024)

```
shape: (5, 12)
| School Year | System ID | System Name       | School ID | School Name                     | Grade Configuration             | Grade Cluster | Content Mastery | Progress | Closing Gaps | Readiness | Graduation Rate |
| 2024        | 738       | Toombs County     | 4050      | Toombs Central Elementary Schl. | PK, KK, 01, 02, 03, 04, 05      | E             | 87.9            | 100      | 81.3         | 90        | NA              |
| 2024        | 630       | Clay County       | ALL       | All Schools                     | PK, KK, 01..12                  | M             | 50              | 100      | 100.0        | 83.4      | NA              |
| 2024        | 743       | Twiggs County     | ALL       | All Schools                     | PK, KK, 01..12                  | M             | 40.4            | 70       | 100.0        | 73.8      | NA              |
| 2024        | 699       | Meriwether County | 300       | Greenville High School          | 09, 10, 11, 12                  | H             | 36.1            | 39.1     | 100.0        | 70.1      | 85              |
| 2024        | 647       | Dougherty County  | 3062      | Turner Elementary School        | PK, KK, 01, 02, 03, 04, 05      | E             | 41.9            | 80.8     | 100.0        | 71        | NA              |
```

#### Statistics (2024)

```
| statistic  | School Year | System ID  | School ID | Closing Gaps |
| count      | 3247        | 3244       | 3247      | 3019         |
| null_count | 0           | 3          | 0         | 228          |
| mean       | 2024.0      | 615947     | n/a       | 67.63        |
| std        | 0.0         | 2.11e6     | n/a       | 28.60        |
| min        | 2024        | 601        | 100       | 0.0          |
| 50%        | 2024        | 671        | n/a       | 71.4         |
| max        | 2024        | 7,830,647  | ALL       | 100.0        |
```

(Other metrics are String columns; their numeric ranges, ignoring suppression markers, are: Content Mastery 1.8-100.0, Progress 13.2-100.0, Readiness 10.8-100.0, Graduation Rate 0-100.)

#### Null Counts (2024)

| School Year | System ID | System Name | School ID | School Name | Grade Configuration | Grade Cluster | Content Mastery | Progress | Closing Gaps | Readiness | Graduation Rate |
|-------------|-----------|-------------|-----------|-------------|---------------------|---------------|-----------------|----------|--------------|-----------|-----------------|
| 0           | 3         | 0           | 0         | 0           | 0                   | 0             | 0               | 0        | 228          | 0         | 0               |

System ID nulls = 3 (state-aggregate rows). Closing Gaps nulls = 228 (suppression encoded as true null, since it is the only Era 4 metric stored as Float64).

#### Categorical Columns (2024)

| Column | Distinct Values |
|--------|----------------|
| Grade Cluster | E (1,613), M (892), H (742) |
| System Name | 235 distinct district names (top: Gwinnett County 153, DeKalb County 151, Fulton County 117). Includes more 7-digit charter operators than earlier eras. |
| School Name | 2,201 distinct school names; `All Schools` (705) for district + state aggregates. |
| Grade Configuration | 66 distinct grade-level combinations. |
| Graduation Rate | 228 "distinct values" — numeric strings plus `NA` (2,559) and `TFS` (33). Treated as numeric-with-suppression below. |

#### Suppression Markers (2024)

| Column | Non-Numeric Values |
|--------|-------------------|
| School ID | `ALL` (705 rows = district + state aggregates) |
| Content Mastery | `NA` (87), `TFS` (86) |
| Progress | `TFS` (134), `NA` (111) |
| Readiness | `NA` (60), `TFS` (33) |
| Graduation Rate | `NA` (2,559), `TFS` (33) |
| Closing Gaps | none (Float64 with 228 true nulls) |

#### Era 4 cross-file notes

- All three years (2023, 2024, 2025) share an identical column set (12 columns) and identical typing pattern: `System ID` Int64 (null = state), all metric columns String EXCEPT `Closing Gaps` which is Float64.
- Row counts: 2023 (3,212; 3 state / 678 district / 2,531 school), 2024 (3,247; 3/702/2,542), 2025 (3,238; 3/702/2,533).
- Suppression markers (`NA`, `TFS`) match Era 3 (2019, 2022) exactly.
- `Closing Gaps` being Float64 is purely a polars inference outcome — the underlying suppression semantics are the same as the other components; just no `NA`/`TFS` strings appear in the actual cells, so polars infers Float64 with true nulls.
- 2023 sheet name omits the word "Scoring" — `CCRPI by Component` instead of `CCRPI Scoring by Component`. Match by file year, not by hard-coded sheet name.

## ETL Considerations

### Sheet structure

- **2012, 2013** files have 3 sheets (`Sheet1`, `Sheet2`, `Sheet3`). Only `Sheet1` has data; reading `Sheet2` or `Sheet3` raises `empty Excel sheet` from polars. Hard-code `sheet_name='Sheet1'` for these years.
- **2014, 2015, 2016** use `'Sheet 1'` (with space).
- **2017** uses `'2017_CCRPI Scoring by Component'`.
- **2018, 2019, 2022, 2024, 2025** use `'CCRPI Scoring by Component'`.
- **2023** uses `'CCRPI by Component'` (no `Scoring`).
- **2022** has a disclaimer in row 0; pass `read_options={'header_row': 1}` to `pl.read_excel()` for that file only.

### Column-name normalization

Header drift is significant across eras and within Era 2 / Era 3:

- **Casing**: Era 1 ALL CAPS, Era 2-4 Title Case. 2014-2015 use `System Id` / `School Id` (lowercase `d`); other Era 2 years use `System ID` / `School ID`.
- **Trailing whitespace**: 2013 has `SCHOOL ID ` (trailing space).
- **Embedded newlines**: 2018 has `Content \nMastery`, `Closing\nGaps`, `CCRPI\nScore`, `Single \nScore`.

The transform should normalize headers (lowercase, strip, collapse whitespace, replace newlines with a space) before mapping to gold column names, OR explicitly handle every variant in a per-era column-rename dict.

### Era boundaries on metrics

- **Era 1-2 (2012-2017)** report **CCRPI component points** with different scales per component (Achievement Points max ~60, Achievement Gap Points max 15, ED/EL/SWD Performance max 10, ETB Points max 2-3, Challenge Points max 10, Progress Points max ~22 in 2012-2014 then ~40 in 2017).
- **Era 3 (2018-2019, 2022)** swap to **CCRPI component scores** on a 0-100 scale (Content Mastery, Progress, Closing Gaps, Readiness, Graduation Rate) plus the aggregates CCRPI Score and Single Score.
- **Era 4 (2023-2025)** keep the Era 3 component scores but **drop CCRPI Score and Single Score**.

The Era 1-2 metric set and Era 3-4 metric set are **not directly comparable** — they measure different things on different scales (raw points vs. component scores). The gold schema must keep them as separate columns; do **not** try to map `Achievement Points` to `Content Mastery`. Each row will only populate the metrics that exist in its source era; other metrics will be null.

### Suppression markers

- **2012-2016 (string metrics)**: `"NA"` only.
- **2017 (Float64 metrics)**: no string markers; suppression appears as true nulls.
- **2018**: `"NA"`, `"Too Few Students"` (full text) on `Readiness`; other metrics are Float64 with true nulls.
- **2019, 2022, 2023-2025**: `"NA"`, `"TFS"`.

The transform must accept all four spellings (`NA`, `TFS`, `Too Few Students`, blank/null) and convert them to a true null. `Closing Gaps` in Era 4 is the only metric column stored as Float64 directly; everything else needs explicit string-to-numeric handling.

### 2022 metric blackout

The 2022 file has every row's `Progress`, `Closing Gaps`, `CCRPI Score`, and `Single Score` set to the literal `"NA"` because of the federally-approved one-year COVID modification (described in the disclaimer header row). The rows are still valid data — `Content Mastery`, `Readiness`, and `Graduation Rate` (for high schools) carry real numbers. Don't drop the rows; just null out the four affected columns.

### Detail levels

| Era | State row signal | District row signal |
|-----|------------------|---------------------|
| 2012-2013 | `SYSTEM ID == "ALL"` (3 rows; `SCHOOL ID == "ALL"` too) | `SCHOOL ID == "ALL"` (with `SYSTEM ID != "ALL"`) |
| 2014-2016 | `System Id == "ALL"` (3 rows) | `School Id == "ALL"` (with `System Id != "ALL"`) |
| 2017 | `System ID == null` (6 rows: 3 `All Systems` + 3 `Residential Treatment Center` operator aggregates) | `School ID == "ALL"` (with `System ID != null`) |
| 2018, 2022 | `System ID == null` (3 rows) | `School ID == "ALL"` (with `System ID != null`) |
| 2019 | `System ID == "ALL"` (3 rows) | `School ID == "ALL"` (with `System ID != "ALL"`) |
| 2023-2025 | `System ID == null` (3 rows) | `School ID == "ALL"` (with `System ID != null`) |

The transform should convert both `"ALL"` strings and string `"All Systems"` / `"All Schools"` and Int64 nulls into a unified `detail_level` field (`state`, `district`, `school`) before applying the geography-nulling rule from the education domain CLAUDE.md.

**2017 RTC operator rows** (`System Name == "Residential Treatment Center"`, 3 rows) are special — they aren't true Georgia state aggregates, they're aggregates over a class of facilities (Residential Treatment Centers). Recommend dropping them in the transform (they are not a state aggregate, they don't have a single `district_code`, and they only appear in 2017). If kept, they'd need a custom detail level outside the standard `state`/`district`/`school` taxonomy.

### ID column type drift

Across the 12 files, `System ID` is stored as String (Era 1, all of Era 2 except 2017, plus 2019) or Int64 (2017, 2018, 2022, 2023-2025). `School ID` is consistently a String column whose value can be `"ALL"`, but the underlying school-code values are sometimes already 4-digit zero-padded (Era 1, Era 2, Era 3, Era 4 — confirmed via repr inspection — School ID min is `"0100"` in 2019 and `"100"` (3-digit, unpadded) in 2017 and 2024). **Always cast to String + `zfill(4)`** for school codes per the education domain CLAUDE.md, and **`zfill(3)`** for district codes (preserving the 7-digit charter codes — never truncate). 2017 and 2024 in particular have un-zero-padded school codes (e.g., `"100"` instead of `"0100"`); zfilling fixes them.

### Charter / state-school district codes (7-digit)

These appear in every era (e.g., `7820108` State Charter Schools, `7820112`, `7820619`, `7991893` State Schools, `7830103`, `7830647`, etc.). Preserve as-is per the education domain rule "**Never truncate with `.str.slice(0, 3)`**" — `zfill(3)` is a no-op on a 7-character string.

### Year column

The `School Year` / `SCHOOL YEAR` column is a single integer year per file (the **ending** calendar year of the school year, e.g., `2024` for the 2023-2024 academic year). This matches the education domain CLAUDE.md `year` convention exactly — no offset, no school-year-string parsing. Stored as String in 2012-2013, Int64 elsewhere.

### Filename year vs data year

The filename year always matches the in-file `School Year`. (Some filenames embed the publication date — e.g., `2014 CCRPI Scoring by Component.03.10.2016.xls` was published March 10, 2016 — but the data year is `2014`.) Always trust the in-file column.

### Year coverage

Bronze covers 2012-2019 and 2022-2025 only. **2020 and 2021 are absent** because Georgia paused CCRPI calculation due to the COVID-19 pandemic. The 2022 file is present but has Progress / Closing Gaps / CCRPI Score / Single Score uniformly suppressed (see "2022 metric blackout" above). Gold should reflect actual coverage; do not synthesize 2020-2021 rows.

### Grade Configuration formatting

- Era 1 (2012-2013): no `Grade Configuration` column at all.
- Era 2 (2014-2016): comma-only delimiters (`PK,KK,01,02,03,04,05`).
- Era 2 (2017), Era 3, Era 4: comma+space delimiters (`PK, KK, 01, 02, 03, 04, 05`).

If preserved in gold, normalize to a single delimiter format. `Grade Configuration` describes the school's grade offering, not a test attribute, so it likely belongs in the schools dimension (or `not_in_gold`) rather than the fact table.

### Percentage scale

Per the education domain CLAUDE.md "Percentage Scale Exceptions," **CCRPI scores are not converted to a 0-1 scale** — preserve their natural 0-100 (or 0-N for component points) scale. Component point columns (Era 1-2) use their own ranges (max 60, 22, 15, 10, 3, 10) — these are points, not percentages, and should not be rescaled.

### Bonus-score over-100 values

`CCRPI Score` and `Single Score` can briefly exceed 100 in the early eras due to ETB / Challenge bonus points (max 102.1 in 2014, 103.6 in 2013, 108.7 in 2017). This is by design. Do not cap at 100.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| SCHOOL YEAR / School Year | not_in_gold | — | Used to derive `year` (Int32) per education domain conventions. Cast String → Int. |
| SYSTEM ID / System ID / System Id | fact_key | district_code | Cast Utf8 + `zfill(3)` to preserve 3-digit standard codes and 7-digit charter codes. `"ALL"` and Int64-null both become NULL for state rows. |
| SYSTEM NAME / System Name | dimension_attribute | — | `district_name` lives in `data/gold/education/_dimensions/districts.parquet`. Drop `"All Systems"` and the Era-2-2017-only `"Residential Treatment Center"` from the dimension build (they are aggregate sentinels, not real districts). |
| SCHOOL ID / School ID / School Id | fact_key | school_code | Cast Utf8 + `zfill(4)`. `"ALL"` becomes NULL for district + state rows. 2017 and 2024 have un-zero-padded values that zfill normalizes. |
| SCHOOL NAME / School Name | dimension_attribute | — | `school_name` lives in `data/gold/education/_dimensions/schools.parquet`. Drop `"All Schools"` and `"All RTC Schools"` aggregate sentinels. |
| Grade Configuration | not_in_gold (or schools dimension attribute) | — | Era 2-4 only. Describes the school's grade offering, not a test attribute. Either drop or move to the schools dimension. Normalize comma-only / comma+space delimiters. |
| GRADE CLUSTER / Grade Cluster | fact_categorical | grade_cluster | `E`, `M`, `H`. Always populated. |
| ACHIEVEMENT POINTS / Achievement Points | fact_metric | achievement_points | Era 1-2 only. Float (max ~60). NULL for Era 3-4 rows. |
| PROGRESS POINTS / Progress Points | fact_metric | progress_points | Era 1-2 only. Float. Note: max ~22 in 2012-2014 (old scoring), max ~40 in 2015-2017 (new scoring) — same column, different underlying scale. NULL for Era 3-4 rows. |
| ACHIEVEMENT GAP POINTS / Achievement Gap Points | fact_metric | achievement_gap_points | Era 1-2 only. Float (max 15 in 2012-2016, 10 in 2017). NULL for Era 3-4 rows. |
| ED/EL/SWD PERFORMANCE / ED/EL/SWD Performance | fact_metric | ed_el_swd_performance | Era 1-2 only. Float (max 10). NULL for Era 3-4 rows. |
| ETB POINTS / ETB Points | fact_metric | etb_points | Era 1-2 only. Float (max 2 in 2012-2013, 3 in 2014, 2.5 in 2017). NULL for Era 3-4 rows. |
| CHALLENGE POINTS / Challenge Points | fact_metric | challenge_points | Era 1-2 only. Float (max 10). NULL for Era 3-4 rows. |
| Content Mastery / Content \nMastery | fact_metric | content_mastery | Era 3-4 only. Float, 0-100 scale. NULL for Era 1-2 rows. |
| Progress | fact_metric | progress | Era 3-4 only. Float, 0-100 scale. **All 2022 values are `NA` → null** (federal COVID modification). NULL for Era 1-2 rows. |
| Closing Gaps / Closing\nGaps | fact_metric | closing_gaps | Era 3-4 only. Float, 0-100 scale. **All 2022 values are `NA` → null**. NULL for Era 1-2 rows. |
| Readiness | fact_metric | readiness | Era 3-4 only. Float, 0-100 scale. NULL for Era 1-2 rows. |
| Graduation Rate | fact_metric | graduation_rate | Era 3-4 only. Float, 0-100 scale. Always-`NA` for non-High-cluster rows (elementary / middle have no graduation rate). NULL for Era 1-2 rows. |
| CCRPI SCORE / CCRPI Score / CCRPI\nScore | fact_metric | ccrpi_score | Era 1-3 only (Era 4 dropped this column). Float, 0-100 scale (can exceed 100 due to bonus points; max 108.7 in 2017). **All 2022 values are `NA` → null.** NULL for Era 4 rows. |
| SINGLE SCORE / Single Score / Single \nScore | fact_metric | single_score | Era 1-3 only (Era 4 dropped this column). Float, 0-100 scale (can exceed 100; max 108.2 in 2017). **All 2022 values are `NA` → null.** NULL for Era 4 rows. |

The fact table has no demographic dimension (this dataset is not broken out by subgroup). It does have one fact-categorical (`grade_cluster`), so each row is uniquely keyed by (`year`, `district_code`, `school_code`, `grade_cluster`). The output should follow the education domain pattern with year-partitioned `schools.parquet` / `districts.parquet` / `states.parquet` files.

## Corrections (transform authoring, 2026-06-12)

Re-verification against bronze during the v2 transform authoring (pandas `dtype=str` reads of every file, which preserve the literal cell contents that polars type inference destroys) found the following claims above to be wrong. Each correction lists its evidence.

1. **RTC rows exist in 2015, 2016, AND 2017 — and carry the literal `SYSTEM ID == "RTC"`, not null.** Each of the three years ships exactly 3 rows with `SYSTEM ID = "RTC"`, `SYSTEM NAME = "Residential Treatment Center"`, `SCHOOL ID = "ALL"`, `SCHOOL NAME = "All RTC Schools"` (one per grade cluster, 9 rows total). The claims that these rows appear only in 2017 and have `System ID == null` (Era 2 cross-file notes, "Detail levels" section) are polars Int64-inference artifacts — a numeric-inferred `System ID` column silently nulls the non-numeric `RTC` and `ALL` strings. Because they carry a system code plus the `SCHOOL ID = "ALL"` district sentinel, they pattern as **district-level** rows, not state rows: the doc's "2017: 6 state rows" and the 2015/2016 district counts (586/592, which silently include the RTC rows) follow from the same misreading. Correct per-level counts: 2015 = 3 state / 583 district + 3 RTC / 2,471 school; 2016 = 3 / 589 + 3 / 2,484; 2017 = 3 / 591 + 3 / 2,472. The "Recommend dropping them" guidance is superseded: `RTC` is an allowlisted pseudo-district code in the districts dimension (education CLAUDE.md, `district_type = state_special`), already published by `ccrpi_content_mastery` (2015-2017) and `ccrpi_graduation_rate` (2015-2018), so the transform keeps the 9 rows as district-level facts with `district_code = "RTC"`.
2. **State aggregate rows carry the literal string `ALL` in `SYSTEM ID` in EVERY year — there are no null IDs anywhere in bronze.** The claims that 2017/2018/2022/2023-2025 store `System ID` as Int64 with null for state rows ("ID column type drift", per-era null-count tables showing 3-6 `System ID` nulls) are the same type-inference artifact. Under string-typed reads: every year has exactly 3 state rows with `SYSTEM ID = "ALL"` + `SCHOOL ID = "ALL"`, district rows have `SCHOOL ID = "ALL"` only, and neither ID column has a single true null in any of the 12 files. Detail-level detection can therefore use the `ALL` sentinels uniformly across all years.
3. **2018 ships the `Too Few Students` sentinel in THREE metric columns, not one**: `Content Mastery` (68 cells), `Readiness` (21), and `Graduation Rate` (28). The claim that 2018 metric columns are "mostly Float64 (only `Readiness` is String...)" reflects polars nulling the sentinel strings during Float64 inference in the other two columns. The transform's suppression handling (`SUPPRESSION_VALUES` at read + `strict=False` casts) covers all three.
4. **The Achievement Gap Points cap dropped from 15 to 10 in 2015, not 2017.** Observed per-year maxima: 15.0 in 2012, 2013, 2014; 10.0 in 2015 ([1.7, 10]), 2016 ([0, 10]), and 2017. The Era 2 table's "max 15 in 2014-2016, 10 in 2017" is wrong for 2015-2016.
5. **Confirmations** (re-verified, no change): in-file `SCHOOL YEAR` equals the filename year in all 12 files; the natural key (`SYSTEM ID`, `SCHOOL ID`, `GRADE CLUSTER`) is unique within every file (0 duplicates); Era 3-4 component scores all lie within [0, 100]; `Graduation Rate` is non-`NA` exclusively on `H`-cluster rows in every Era 3-4 year; the 2022 Progress / Closing Gaps / CCRPI Score / Single Score blackout is total (0 numeric cells); and **no `100.00+` top-cap sentinel exists anywhere in this topic's bronze** (unlike the ccrpi_content_mastery sibling). Additionally, the points-era identity `ACHIEVEMENT + PROGRESS + ACHIEVEMENT GAP + CHALLENGE = CCRPI SCORE` holds exactly (max |diff| = 0.0) on every 2012-2017 row where all five values are published, and `ACHIEVEMENT POINTS` / `ETB POINTS` / `CHALLENGE POINTS` are row-level co-null throughout 2012-2017.
