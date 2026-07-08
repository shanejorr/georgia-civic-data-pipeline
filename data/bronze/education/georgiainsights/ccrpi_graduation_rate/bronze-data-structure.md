# ccrpi_graduation_rate - Bronze Data Structure

## Overview

- Topic: ccrpi_graduation_rate
- Source: georgiainsights
- Files: 27 files spanning 2012-2025 (one of which is a 125-page PDF and is unreadable for this analysis; one is a CSV — the rest are Excel)
- Unreadable files: `4-Year Cohort Graduation Rate State District School by Subgroups_12.14.23.pdf` (PDF version of the 2023 standalone 4-Year Cohort release; the GOSA CSV `GOSA_4-Year_Cohort_Graduation_Rate_2022-23_12.15.23.csv` carries the same 2023 4-year cohort data plus counts and is used instead)
- Year representation: Mixed. CCRPI files have a `School Year` integer column. Standalone "4-Year Cohort", "5-Year Graduation Rate", and "On Time Graduation Rate" files generally encode the data year only in the filename (publication date or year prefix). The GOSA CSV has a `LONG_SCHOOL_YEAR` column (e.g., `2022-23`)
- Filename-to-data year offset: see "ETL Considerations" — CCRPI files have a year column (use that), but legacy and standalone files require parsing the filename. One file (`...02.19.18.xlsx`) has filename year = data year + 1 (early 2018 release of the 2017 cohort)
- Detail levels: state, district (system), school (state and district aggregates not present in the 2012-2013 legacy files)
- Percentage scale: 0-100 throughout (with suppression markers as text)
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: Georgia Insights (GaDOE) public data downloads — exact page URL not recorded at acquisition time
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| 2012 Graduation Rate By Subgroups for Public Release.xls | a7c97e498d9fa6781ed7c251ef4a32abd0c8d59867fee7a5294083a1efcce7fa |
| 2013 Graduation Rate By Subgroups for Public Release.xls | 8cfa3157dd46c5a50eda20a3edfb0481726b3c0911f2b62ff8c529055ecde7f1 |
| 2014 Cohort Grad Rate by Subgroups Ammended (2) for Web Page.xlsx | b34fb06e38d7912486d580763faf1fcdaf4126fcfed5874f4a72f6c69d3c87d1 |
| 2015 4-Year Cohort Graduation Rate State District School  by Subgroup 05.03.16.xlsx | ac9409281858d6721283e739aa1789e0e9fb90162cbb422d99d20357fc95d464 |
| 2016 4-Year Cohort Graduation Rate State District School by Subgroups_11.29.16.xlsx | 39650c31b55d096c49de5f42b4300177274d284c9d9282ae12c62a78acf0cd78 |
| 2018 CCRPI Graduation Rates, Targets, Flags by Subgroup 11_1_18.xlsx | 61a6c0909657b7604f6c55be6c70ada1e25a6c116506eec5a86513f4b7314f39 |
| 2019 CCRPI Graduation Rate, Scores, Targets and Flags_12_06_19.xls | 356eea8e51023651e45d93718b567939a54840a82b15f523db16bf1a1eaa6a5b |
| 2020 Graduation Rate Scores, Targets, and Flags by Subgroup.xlsx | 0ae7b883d860a9bc91f9ff75c5d2d33fde42402303546fc37fc2f30032b24023 |
| 2021 On Time Graduation Rate 02.28.22.xlsx | ee626c7522625845d1caffd36b640bc1d5bd8cbac22f666c5d188d9a2f38a3cd |
| 2022 CCRPI Graduation Rates by Subgroup 11.16.22.xlsx | 345996e676fda49feeb054c438eca68349eab12d1e4df42ec077893574995c56 |
| 2022 On Time Graduation Rate.xlsx | 86fbde070d453f9a0bd0373339c11471b4a10f1b85c96241f54f8170dc9d1d3f |
| 2023 CCRPI Graduation Rates, Targets, and Flags by Subgroup_12_14_23.xlsx | 5d21d2c02e4519aeba38bb419fbb0995a328e09b82563831866260293de21f51 |
| 2023 On Time Graduation Rate.xlsx | 770e5cafcbb16205ac98194db13defc5dee0e9f997137b8c1c196a5f883a8c65 |
| 2024 4-Year Cohort Graduation Rate State District School by Subgroups.xlsx | c6425592441daea4325cb151ca1333e3a2be9e211ed4f0011a1b16072af324dd |
| 2024 CCRPI Graduation Rates, Targets, and Flags by Subgroup.xlsx | c812fd38c85e2206f00a5a5fcffc11171ae3f1a799d0325b3d8fe86e8128fc81 |
| 2024 On Time Graduation Rate.xlsx | ca0ad1727bd538723da59a1e62b6c716c7b52a903f6aad3b60cd8977a5346e6a |
| 2025 4-Year Cohort Graduation Rate State District School by Student Group.xlsx | e6a3600d05f88917dcaebf9d0d5f87f43f9b7f131b1dd84c6c8a5c42bec92054 |
| 2025 CCRPI Graduation Rates, Targets, and Flags by Student Group.xlsx | ec29b23461813f427b4e04a48c013302a87bf094f45723d7746fc62a3189c2ec |
| 4-Year Cohort Graduation Rate State District School by Subgroup 02.19.18.xlsx | 9b51f129007617e6d7c6a43ebb623350e2b2c2462f088d64693430de827a6866 |
| 4-Year Cohort Graduation Rate State District School by Subgroup 10_06_22.xlsx | 14ec22d9242822df7298d5c3e45b41e95e7b561b9ad215e7f10ce2e01e820b7d |
| 4-Year Cohort Graduation Rate State District School by Subgroup 12.08.21.xlsx | 05718f1823ea6e5a46f843e8ba150c998b035f023fbbf7b59aaaf189b5209e14 |
| 4-Year Cohort Graduation Rate State District School by Subgroups 11_20_20.xlsx | d971cea31a2936fa4c6c4abac7c0393c2294dda358b3cc00d531886c0ae47c67 |
| 4-Year Cohort Graduation Rate State District School by Subgroups_09_19_18.xlsx | 751277d2e9edb243ea55ef14535f6d105d5bc52ab75cf5f5ab3ddfeb6078d3ad |
| 4-Year Cohort Graduation Rate State District School by Subgroups_11_26_19.xlsx | 4a6a3763bfe9d622826bc2135d4332fab0adf280c01e353db63456a578838d3c |
| 4-Year Cohort Graduation Rate State District School by Subgroups_12.14.23.pdf | b3cc77cf4cafe46acb445bfd123393b7847ea097455e5701fe060517e719dab8 |
| 5-Year Graduation Rate by Subgroup 12.08.21.xlsx | adf0447d049481ef257dcb7fe778f455329c7f4f4902c87ad2afc154bf58b605 |
| GOSA_4-Year_Cohort_Graduation_Rate_2022-23_12.15.23.csv | 708331bc1cb251af84ebed3971ae537da527921fc79c998578bf45f8ff205422 |

## Excel Sheet Structure

The bronze directory contains six distinct file families. Each family has its own sheet structure.

| File family | Files | Sheets | Notes |
|-------------|-------|--------|-------|
| Family A: CCRPI Graduation Rates | 2018, 2019, 2020, 2022, 2023, 2024, 2025 (one file per year) | Single data sheet (named varies: `Graduation Rates by Subgroup`, `Graduation Rate by Subgroup`, `Graduation Rate - Student Group`); 2022 also has a blank `FAQs` metadata sheet | These are the CCRPI accountability releases. Both 4-year and 5-year graduation rates are stored together as long-format rows distinguished by `Graduation Rate Type` |
| Family B: Legacy Graduation Rate | 2012, 2013, 2014 | Single data sheet (default name) | Pre-CCRPI legacy releases. Only the 4-year cohort rate is reported. 2012-2013 lack district/state aggregates (school-level only) |
| Family C: Standalone 4-Year Cohort Graduation Rate | 2015 (05.03.16), 2016 (11.29.16), 2017 (02.19.18), 2018 (09_19_18), 2019 (11_26_19), 2020 (11_20_20), 2021 (12.08.21), 2022 (10_06_22), 2024 (year-prefixed), 2025 (year-prefixed) | Two data sheets per file: `All Students` (or `ALL Student` / `All Student`, depending on year) — has `Graduation Class Size` and `Total Graduated`, only `ALL Students` demographic, includes state/district/school rows; and `Subgroup` (or `Subgroups` / `Student Group`) — only `Graduation Rate`, all 10 demographic groups, school/district/state rows | Standalone 4-year cohort releases. The two sheets must be combined to get class-size-by-demographic data (subgroup sheet lacks counts; All Students sheet only has counts for ALL Students). 12.08.21 and 10_06_22 files have a disclaimer row before the column headers (need `header_row=1`). Some files (12.08.21) also contain a `FAQs` metadata sheet |
| Family D: 5-Year Graduation Rate | 2021 (12.08.21) — single file | Two data sheets: `ALL Student` (only ALL Students demographic), `Subgroup` (all demographics), plus `FAQs` metadata sheet | One-off standalone 5-year release. Only 7 columns (no class-size info) |
| Family E: On-Time Graduation Rate | 2021, 2022, 2023, 2024 | Two sheets: `On-Time Graduation by Subgroup` (data), `Details` (metadata describing methodology under SB 431) | School-level only — no district or state aggregate rows. Has a Senate Bill 431 disclaimer in row 0 of the data sheet (needs `header_row=1`). Includes `Total Enrolled`, `Total Graduated`, and `On-Time Graduation Rate` |
| Family F: GOSA 4-Year Cohort CSV (count-gap fill) | 2023 only (`GOSA_4-Year_Cohort_Graduation_Rate_2022-23_12.15.23.csv`) | Flat CSV (not Excel) — no sheets | Pulled from the GOSA Downloadable Data Portal. Carries the 2023 4-year cohort numerator (`PROGRAM_TOTAL`), denominator (`TOTAL_COUNT`), and rate (`PROGRAM_PERCENT`) at state/district/school × 18 demographic groups. Used to fill the 2023 4-year count gap left by the unreadable `12.14.23.pdf`. Long-format with one row per (entity, demographic) combo |

The 125-page PDF (`...12.14.23.pdf`) is the typeset version of the standalone 4-Year Cohort data dated 12.14.23 and is not used for transformation. For 2023 CCRPI graduation rates the canonical source is the matching XLSX (`2023 CCRPI Graduation Rates, Targets, and Flags by Subgroup_12_14_23.xlsx`); for 2023 4-year cohort counts (numerator and denominator) the canonical source is the Family F GOSA CSV (`GOSA_4-Year_Cohort_Graduation_Rate_2022-23_12.15.23.csv`).

## Summary

This topic captures Georgia's high school graduation rate measures across multiple reporting frameworks. The headline measures are:

- **4-year adjusted cohort graduation rate** — percentage of first-time 9th graders who graduated with a regular diploma within four years (the federal accountability metric, present in nearly every file)
- **5-year adjusted cohort graduation rate** — same cohort, allowing one extra year to graduate (CCRPI files plus the standalone 5-Year file)
- **On-time graduation rate** — Senate Bill 431 (2020) measure for students who attended continuously from October 1 of the cohort entry year and graduated by the regular date (On-Time files)
- **Graduation class size** — denominator (cohort size) for the 4-year rate (standalone 4-Year and On-Time files)
- **Total graduated** — numerator (graduates) for the rate (standalone 4-Year and On-Time files)
- **CCRPI target** and **flag** — accountability target rate and color-coded performance flag (G/Y/R) for each subgroup (CCRPI files, except 2020 which had targets suspended for COVID and the 2022 release which omitted them)

All measures are reported by demographic subgroup (10 standard subgroups: All Students, race/ethnicity categories, English Learners, Economically Disadvantaged, Students With Disability) at the school, district, and state levels (with the exception that the 2012-2013 legacy releases and the On-Time releases lack some aggregate levels).

## Eras

> Because this directory contains five distinct file families, eras are organized first by **family** (A-E) then by year sub-grouping within the family. Each era is a contiguous group of files that share the same column names.

### Era A1 (2018-2020, 2023-2025): CCRPI Graduation Rates with Target/Flag

**Files**: 2018, 2019, 2020, 2023, 2024, 2025 CCRPI Graduation Rate releases.

**Columns**: School Year, System ID, System Name, School ID, School Name, Grade Configuration, Grade Cluster, Reporting Label, Graduation Rate Type, Graduation Rate, Target, Flag

| Column | Description |
|--------|-------------|
| School Year | Integer year (the year the cohort graduated). 2018-2020 files contain a single year; 2023-2025 files contain TWO years (current year's 4-yr rate + prior year's 5-yr rate) |
| System ID | District (system) code, integer; null for state-level rows |
| System Name | District name, "All Systems" for state-level rows, "State Charter Schools" / "State Schools" for non-traditional districts |
| School ID | School code, string. "ALL" for district-level and state-level aggregate rows. School ID is stored as string with leading-zero handling that varies (e.g., `0103` in 2018, `103` in 2024) |
| School Name | School name, "All Schools" for district/state-level aggregate rows |
| Grade Configuration | Comma-separated list of grade levels offered by the school (e.g., `09, 10, 11, 12`, `PK, KK, 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12`) |
| Grade Cluster | Always "H" (this dataset is high-school-only) |
| Reporting Label | Demographic subgroup. "American Indian/Alaskan" in 2018-2020, "American Indian/Alaskan Native" in 2023-2025 |
| Graduation Rate Type | "4-year graduation rate" or "5-year graduation rate" |
| Graduation Rate | Percentage on 0-100 scale (string with suppression markers `TFS`, `No Data`) |
| Target | CCRPI target percentage. String type in most years (`NA`, `TFS`, or numeric); float type in 2023 and 2024 (numeric or null). 2020 has Target=`NA` for every row (COVID suspension of CCRPI scoring) |
| Flag | Performance flag: `G` (green), `Y` (yellow), `R` (red), or `NA` when no target. 2020 has Flag=`NA` for every row |

#### Sample Data (2018)

```
shape: (5, 12)
School Year | System ID | System Name     | School ID | School Name            | Grade Configuration                                | Grade Cluster | Reporting Label            | Graduation Rate Type   | Graduation Rate | Target | Flag
2018        | 751       | Wayne County    | ALL       | All Schools            | PK, KK, 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11 | H             | Multi-Racial               | 4-year graduation rate | TFS             | TFS    | NA
2018        | 653       | Emanuel County  | 0189      | Swainsboro High School | 09, 10, 11, 12                                     | H             | Multi-Racial               | 5-year graduation rate | TFS             | TFS    | NA
2018        | 7991894   | State Schools   | ALL       | All Schools            | PK, KK, 01, 02, ..., 11                            | H             | Economically Disadvantaged | 5-year graduation rate | TFS             | 59.16  | NA
2018        | 722       | Rockdale County | 0192      | Salem High School      | 09, 10, 11, 12                                     | H             | Students With Disability   | 5-year graduation rate | 71.05           | 62.69  | G
2018        | 746       | Walker County   | 0190      | Ridgeland High School  | 09, 10, 11, 12                                     | H             | American Indian/Alaskan    | 4-year graduation rate | TFS             | NA     | NA
```

#### Statistics

| File (year) | Row count | School Year values | Notes |
|-------------|-----------|--------------------|-------|
| 2018 | 13,890 | 2018 only | All metrics present |
| 2019 | 13,360 | 2019 only | All metrics present |
| 2020 | 13,460 | 2020 only | Target/Flag are all `NA` (COVID) |
| 2023 | 13,140 | 2022 (5-yr) + 2023 (4-yr) | Target is `f64`, not string |
| 2024 | 13,780 | 2023 (5-yr) + 2024 (4-yr) | Target is `f64`, not string |
| 2025 | 13,780 | 2024 (5-yr) + 2025 (4-yr) | Target reverts to string type |

#### Null Counts

In every file: only `System ID` has nulls (= 20 rows in 2018-2024, 110 rows in 2025), corresponding to state-level aggregate rows. All other columns have no nulls (suppression is via text markers).

#### Categorical Columns

| Column | Distinct Values |
|--------|-----------------|
| Grade Cluster | `H` (only) |
| Reporting Label (2018-2020) | `ALL Students`, `American Indian/Alaskan`, `Asian/Pacific Islander`, `Black`, `Economically Disadvantaged`, `English Learners`, `Hispanic`, `Multi-Racial`, `Students With Disability`, `White` |
| Reporting Label (2023-2025) | Same 10 groups, but `American Indian/Alaskan Native` instead of `American Indian/Alaskan` |
| Graduation Rate Type | `4-year graduation rate`, `5-year graduation rate` |
| Flag | `G`, `Y`, `R`, `NA` (counts vary; `NA` is the most common when target is suppressed) |
| Grade Configuration | 24-37 distinct values per file (varies by year as new schools open with new grade spans) |

#### Suppression Markers

| Column | Non-Numeric Values | 2018 counts |
|--------|--------------------|-------------|
| School ID | `ALL` (district/state aggregate) | 4,110 |
| Graduation Rate | `TFS`, `No Data` | TFS=4,243, No Data=2,622 |
| Target (2018, 2019, 2025) | `TFS`, `NA` | 2018: TFS=3,688, NA=3,335 |
| Target (2020) | `NA` only (across every row) | 13,460 |
| Target (2023, 2024) | numeric or null (column type is f64) | n/a |
| Flag | `NA` (no target) | 2018: 7,262 |

---

### Era A2 (2022): CCRPI Graduation Rates without Target/Flag

**Files**: 2022 CCRPI Graduation Rates by Subgroup release.

**Columns**: School Year, System ID, System Name, School ID, School Name, Grade Configuration, Grade Cluster, Reporting Label, Graduation Rate Type, Graduation Rate

Same as Era A1 but the `Target` and `Flag` columns are dropped.

| Column | Description |
|--------|-------------|
| (same first 9 columns as Era A1) |  |
| Graduation Rate | Percentage on 0-100 scale (string with suppression markers) |

#### Sample Data

```
shape: (5, 10)
School Year | System ID | System Name                         | School ID | School Name              | Grade Configuration | Grade Cluster | Reporting Label | Graduation Rate Type   | Graduation Rate
2021        | 746       | Walker County                       | 190       | Ridgeland High School    | 09, 10, 11, 12      | H             | ALL Students    | 5-year graduation rate | 92.11
2022        | 650       | Echols County                       | 1050      | Echols County High School| 09, 10, 11, 12      | H             | ALL Students    | 4-year graduation rate | 96
2022        | 7830103   | State Charter Schools II- Statesboro | 103     | Statesboro STEAM Academy | 06, 07, 08, ...     | H             | White           | 4-year graduation rate | TFS
2021        | 718       | Quitman County                      | 110       | Quitman County High Sch  | 09, 10, 11, 12      | H             | Hispanic        | 5-year graduation rate | No Data
2022        | 741       | Troup County                        | 201       | Callaway High School     | 09, 10, 11, 12      | H             | Black           | 4-year graduation rate | 90.24
```

#### Statistics

Row count: 12,960. School Year values: 2021 (5-yr) + 2022 (4-yr).

#### Null Counts

Only `System ID` = 20 nulls (state-level rows). All other columns: 0.

#### Categorical Columns

Same as Era A1 (uses `American Indian/Alaskan Native` like later years).

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|--------------------|
| School ID | `ALL` |
| Graduation Rate | `TFS`, `No Data` |

---

### Era B1 (2012): Legacy Graduation Rate, all-caps `REPORTING CATEGORY`

**File**: `2012 Graduation Rate By Subgroups for Public Release.xls`

**Columns**: COHORT YEAR, REPORTING LEVEL, SYSTEM ID, SCHOOL ID, SYSTEM NAME, SCHOOL NAME, REPORTING CATEGORY, GRADUATION RATE

| Column | Description |
|--------|-------------|
| COHORT YEAR | String year ("2012") |
| REPORTING LEVEL | `School` or `System` (no `State` rows) |
| SYSTEM ID | District code as string (e.g., `601`) |
| SCHOOL ID | School code as string (e.g., `0103`); `ALL` for district-level aggregate rows |
| SYSTEM NAME | District name |
| SCHOOL NAME | School name; `All Schools` for district aggregates |
| REPORTING CATEGORY | Demographic subgroup |
| GRADUATION RATE | Percentage on 0-100 scale (string with suppression markers `Too Few Students`, `No Data Found`) |

Sheet column ordering: SYSTEM ID and SCHOOL ID come BEFORE the system/school names (different from 2013+).

#### Statistics

Row count: 6,070. All columns are strings. No nulls. School-level rows: 4,280. District (System) rows: 1,790. No state-level rows.

#### Null Counts

All columns: 0.

#### Categorical Columns

| Column | Distinct Values |
|--------|-----------------|
| REPORTING LEVEL | `School` (4,280), `System` (1,790) |
| REPORTING CATEGORY | `ALL Students`, `American Indian/Alaskan`, `Asian/Pacific Islander`, `Black`, `Economically Disadvantaged`, `English Learners`, `Hispanic`, `Multi-Racial`, `Students With Disability`, `White` (607 rows each) |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|--------------------|
| SCHOOL ID | `ALL` (1,790) |
| GRADUATION RATE | `Too Few Students` (1,958), `No Data Found` (857) |

---

### Era B2 (2013): Legacy Graduation Rate, all-caps `REPORTING LABEL`

**File**: `2013 Graduation Rate By Subgroups for Public Release.xls`

**Columns**: COHORT YEAR, REPORTING LEVEL, SYSTEM ID, SYSTEM NAME, SCHOOL ID, SCHOOL NAME, REPORTING LABEL, GRADUATION RATE

Schema is identical to Era B1 except:
- The demographic column is renamed `REPORTING LABEL` (vs `REPORTING CATEGORY` in 2012)
- `SYSTEM NAME` now appears between `SYSTEM ID` and `SCHOOL ID` (column reordering)

Row count: 6,090. School-level rows: 4,270. System (district) rows: 1,820. No state-level rows.

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|--------------------|
| SCHOOL ID | `ALL` (1,820) |
| GRADUATION RATE | `Too Few Students` (1,945), `No Data Found` (881) |

---

### Era B3 (2014): Legacy Graduation Rate, title case + `Reporting Category Code`

**File**: `2014 Cohort Grad Rate by Subgroups Ammended (2) for Web Page.xlsx`

**Columns**: Cohort Year, System ID, System Name, School ID, School Name, Reporting Category Code, Graduation Rate

| Column | Description |
|--------|-------------|
| Cohort Year | String year ("2014") |
| System ID | District code as string; `ALL` for state-level aggregate (only 10 such rows) |
| System Name | District name; `All Systems` for state-level rows |
| School ID | School code as string; `ALL` for district aggregates |
| School Name | School name; `All Schools` for district/state aggregates |
| Reporting Category Code | Demographic subgroup |
| Graduation Rate | Percentage on 0-100 scale (string with suppression markers `Too Few Students`, `No Data Found`) |

No `Reporting Level` column — detail levels are inferred from `System ID == 'ALL'` (state) and `School ID == 'ALL'` (district).

Row count: 6,160.

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|--------------------|
| System ID | `ALL` (10) — state-level rows |
| School ID | `ALL` (1,850) |
| Graduation Rate | `Too Few Students` (1,948), `No Data Found` (893) |

---

### Era C1 (2015): Standalone 4-Year Cohort, all-caps with stray space

**File**: `2015 4-Year Cohort Graduation Rate State District School  by Subgroup 05.03.16.xlsx`

Two sheets:
- `All Students` (note plural): `REPORTING LEVEL, SYSTEM ID, SCHOOL ID , SYSTEM NAME, SCHOOL NAME, REPORTING LABEL, GRADUATION CLASS SIZE, TOTAL GRADUATED, GRADUATION RATE` — 625 rows, only `ALL Students` demographic, includes state/district/school
- `Subgroups` (note plural): `REPORTING LEVEL, SYSTEM ID, SCHOOL ID, SYSTEM NAME, SCHOOL NAME, REPORTING LABEL, GRADUATION RATE` — 6,250 rows, all 10 demographic groups but no class size or total graduated

**Notable**: `SCHOOL ID ` in the `All Students` sheet has a trailing space in the column name. The `Subgroups` sheet has clean `SCHOOL ID`. Must normalize before concatenating.

| Column (All Students sheet) | Description |
|-----------------------------|-------------|
| REPORTING LEVEL | `School`, `System`, or `State` |
| SYSTEM ID | District code (string); `ALL` for state |
| SCHOOL ID&nbsp; (trailing space) | School code; `ALL` for district/state aggregates |
| SYSTEM NAME | District name; `All Systems` for state |
| SCHOOL NAME | School name; `All Schools` for district/state |
| REPORTING LABEL | Always `ALL Students` in this sheet |
| GRADUATION CLASS SIZE | Cohort size (i64; never suppressed in this sheet but treat as int with potential text fallback) |
| TOTAL GRADUATED | Number of graduates (string with suppression marker `Too Few Students`) |
| GRADUATION RATE | Percentage on 0-100 scale (string with suppression markers) |

State value (ALL Students, 4-year): 78.953%

Row counts: All Students sheet = 625 (438 schools, 186 systems, 1 state). Subgroups sheet = 6,250.

#### Suppression Markers (2015 All Students sheet)

| Column | Non-Numeric Values |
|--------|--------------------|
| TOTAL GRADUATED | `Too Few Students` (37) |
| GRADUATION RATE | `Too Few Students` (37) |

---

### Era C2 (2016): Standalone 4-Year Cohort, title case `Reporting Level`

**File**: `2016 4-Year Cohort Graduation Rate State District School by Subgroups_11.29.16.xlsx`

Two sheets:
- `All Students`: `Reporting Level, System ID, School ID, System Name, School Name, Reporting Label, Graduation Class Size, Total Graduated, Graduation Rate` — 631 rows
- `Subgroup` (note singular): same 7 columns as the 2015 Subgroups sheet but title case — 6,310 rows

State value (ALL Students, 4-year): 79.4%

#### Suppression Markers (2016 All Students sheet)

| Column | Non-Numeric Values |
|--------|--------------------|
| Total Graduated | `Too Few Students` |
| Graduation Rate | `Too Few Students` |

---

### Era C3 (2017-2025): Standalone 4-Year Cohort, title case `Reporting Level` (stable schema)

**Files** (each represents a different data year despite some sharing publication years):
| Filename | Inferred data year | State ALL Students 4-year value |
|----------|--------------------|---------------------------------|
| `4-Year Cohort Graduation Rate State District School by Subgroup 02.19.18.xlsx` | 2017 (early-2018 release) | 80.556 |
| `4-Year Cohort Graduation Rate State District School by Subgroups_09_19_18.xlsx` | 2018 | 81.56 |
| `4-Year Cohort Graduation Rate State District School by Subgroups_11_26_19.xlsx` | 2019 | 82.02 |
| `4-Year Cohort Graduation Rate State District School by Subgroups 11_20_20.xlsx` | 2020 | 83.82 |
| `4-Year Cohort Graduation Rate State District School by Subgroup 12.08.21.xlsx` | 2021 | 83.69 |
| `4-Year Cohort Graduation Rate State District School by Subgroup 10_06_22.xlsx` | 2022 | 84.06 |
| `2024 4-Year Cohort Graduation Rate State District School by Subgroups.xlsx` | 2024 | 85.44 |
| `2025 4-Year Cohort Graduation Rate State District School by Student Group.xlsx` | 2025 | 87.22 |

Inferred years are derived by cross-referencing the state ALL Students 4-year value to the equivalent value in the matching CCRPI release. No file with data year 2023 exists in this family (the 12.14.23 PDF presumably contains it but is unreadable; no XLSX equivalent in this family for 2023).

**Common columns** (both sheets):

`Reporting Level, System ID, School ID, System Name, School Name, Reporting Label, [Graduation Class Size, Total Graduated,] Graduation Rate`

- `All Students` (or `ALL Student` / `All Student`) sheet: 9 columns including counts
- `Subgroup` (or `Student Group`) sheet: 7 columns (no counts, all 10 demographics)

**Type variation**: 02.19.18 and 11_26_19 files have `Graduation Class Size`, `Total Graduated`, and `Graduation Rate` parsed as i64/f64 (cleaner data). The other years have these as strings due to suppression markers (`Too Few Students`, `No Data`).

**Disclaimer rows**: 12.08.21 and 10_06_22 files have a USDA School Food Authorities disclaimer about Free and Reduced Meal Application waivers as the first row (need `header_row=1`). The 2024-2025 year-prefixed files do NOT have this disclaimer.

**Demographic naming**: Files through 12.08.21 use `American Indian/Alaskan`. Files from 10_06_22 onward use `American Indian/Alaskan Native`.

| Column | Description |
|--------|-------------|
| Reporting Level | `School`, `System`, or `State` |
| System ID | District code; `ALL` (or null int) for state-level |
| School ID | School code; `ALL` for district/state aggregates |
| System Name | District name; `All Systems` for state |
| School Name | School name; `All Schools` for district/state aggregates |
| Reporting Label | Demographic subgroup |
| Graduation Class Size | Cohort size (string in most files, i64 in 02.19.18 and 11_26_19 files) |
| Total Graduated | Number of graduates (string with `Too Few Students` marker in most files) |
| Graduation Rate | Percentage on 0-100 scale (string with suppression markers) |

#### Suppression Markers (representative 2024 file)

| Column | Sheet | Non-Numeric Values |
|--------|-------|--------------------|
| School ID | both | `ALL` (district/state) |
| Graduation Class Size | All Students | `Too Few Students` (37) |
| Total Graduated | All Students | `Too Few Students` (37) |
| Graduation Rate | All Students | `Too Few Students` (37) |
| Graduation Rate | Subgroup | `Too Few Students` (2,076), `No Data` (992) |

---

### Era D1 (2021): Standalone 5-Year Graduation Rate

**File**: `5-Year Graduation Rate by Subgroup 12.08.21.xlsx`

Two data sheets (`ALL Student`, `Subgroup`) plus `FAQs` metadata sheet.

**Columns**: Reporting Level, System ID, School ID, System Name, School Name, Reporting Label, Graduation Rate

7 columns (no class size or total graduated). All 10 demographics in `Subgroup` sheet, only `ALL Students` in `ALL Student` sheet.

Inferred data year: **2021** (state ALL Students 5-year value = 85.63%, which corresponds to the 2021 5-year cohort that started 9th grade in 2017).

**Demographic naming**: `American Indian/Alaskan` (older convention).

| Column | Description |
|--------|-------------|
| Reporting Level | `School`, `System`, or `State` |
| System ID | District code (string); `ALL` for state |
| School ID | School code (string); `ALL` for district/state |
| System Name | District name; `All Systems` for state |
| School Name | School name; `All Schools` for district/state |
| Reporting Label | Demographic subgroup |
| Graduation Rate | Percentage on 0-100 scale (string with suppression markers) |

Row counts: ALL Student sheet = 669 (476 schools, 192 systems, 1 state). Subgroup sheet = 6,683.

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|--------------------|
| School ID | `ALL` |
| Graduation Rate | `Too Few Students`, `No Data` |

---

### Era E1 (2021-2024): On-Time Graduation Rate

**Files**: 2021 (02.28.22), 2022, 2023, 2024 On Time Graduation Rate releases.

**Columns**: Year, Reporting Level, System ID, School ID, System Name, School Name, Reporting Label, Total Enrolled, Total Graduated, On-Time Graduation Rate

Single data sheet (named `On-Time Graduation by Subgroup`) plus `Details` metadata sheet that quotes Senate Bill 431 (2020) and explains the methodology.

**Disclaimer row**: Every On-Time file has the SB 431 statutory definition as row 0 (need `header_row=1`).

| Column | Description |
|--------|-------------|
| Year | Integer year (the cohort graduation year). 2021 file uses ` Year` with a leading space; 2022+ use `Year` |
| Reporting Level | Always `School` (no district or state aggregates) |
| System ID | District code (i64) |
| School ID | School code (i64) |
| System Name | District name |
| School Name | School name |
| Reporting Label | Demographic subgroup. 2021 file uses `American Indian/Alaskan`; 2022+ use `American Indian/Alaskan Native` |
| Total Enrolled | First-time 9th grade cohort count (string with suppression markers) |
| Total Graduated | Number who graduated by the regular date (string with suppression markers) |
| On-Time Graduation Rate | Percentage on 0-100 scale (string with suppression markers) |

#### Statistics

| File | Year | Row count |
|------|------|-----------|
| 2021 (02.28.22) | 2021 | 4,380 |
| 2022 | 2022 | 4,380 |
| 2023 | 2023 | 4,320 |
| 2024 | 2024 | 5,100 |

#### Categorical Columns (2024 example)

| Column | Distinct Values |
|--------|-----------------|
| Reporting Level | `School` (only) |
| Reporting Label | 10 standard groups (`American Indian/Alaskan Native` since 2022) |

#### Suppression Markers (2024 example)

| Column | Non-Numeric Values |
|--------|--------------------|
| Total Enrolled | `Too Few Students` (1,492), `No Data` (1,413) |
| Total Graduated | `Too Few Students` (1,492), `No Data` (1,413) |
| On-Time Graduation Rate | `Too Few Students` (1,492), `No Data` (1,413) |

The same row tends to have all three values suppressed together (TFS or No Data).

---

### Era F1 (2023): GOSA 4-Year Cohort CSV — count-gap fill

**File**: `GOSA_4-Year_Cohort_Graduation_Rate_2022-23_12.15.23.csv` (one file, CSV, not Excel).

**Source**: Georgia Insights / GOSA Downloadable Data Portal. The same underlying 4-year cohort data that the unreadable `4-Year Cohort Graduation Rate State District School by Subgroups_12.14.23.pdf` typesets, but published as a flat CSV with numerator and denominator counts.

**Columns**: LONG_SCHOOL_YEAR, DETAIL_LVL_DESC, SCHOOL_DSTRCT_CD, SCHOOL_DSTRCT_NM, INSTN_NUMBER, INSTN_NAME, GRADES_SERVED_DESC, LABEL_LVL_1_DESC, PROGRAM_TOTAL, PROGRAM_PERCENT, TOTAL_COUNT

| Column | Description |
|--------|-------------|
| LONG_SCHOOL_YEAR | School year string in `YYYY-YY` form. Only value present: `2022-23` (data year 2023 — the 4-year cohort that graduated in the 2022-23 school year) |
| DETAIL_LVL_DESC | `State`, `District`, or `School` — the aggregation level |
| SCHOOL_DSTRCT_CD | District code, string. `ALL` for state-level rows. Includes 3-digit traditional district codes (e.g., `601`) and 7-digit state-charter / state-school operator codes |
| SCHOOL_DSTRCT_NM | District name. `All Column Values` for state-level rows |
| INSTN_NUMBER | School code, string. `ALL` for state-level and district-level rows |
| INSTN_NAME | School name. `All Column Values` for state- and district-level rows |
| GRADES_SERVED_DESC | Comma-separated grade configuration (e.g., `09,10,11,12`, `PK,KK,01,02,...,12`). Same role as `Grade Configuration` in CCRPI files |
| LABEL_LVL_1_DESC | Demographic subgroup, prefixed with `Grad Rate -`. 18 distinct values: `Grad Rate -ALL Students`, `Grad Rate -Active Duty`, `Grad Rate -American Indian/Alaskan`, `Grad Rate -Asian/Pacific Islander`, `Grad Rate -Black`, `Grad Rate -Economically Disadvantaged`, `Grad Rate -Female`, `Grad Rate -Foster`, `Grad Rate -Hispanic`, `Grad Rate -Homeless`, `Grad Rate -Limited English Proficient`, `Grad Rate -Male`, `Grad Rate -Migrant`, `Grad Rate -Multi-Racial`, `Grad Rate -Not Economically Disadvantaged`, `Grad Rate -Students With Disability`, `Grad Rate -Students Without Disability`, `Grad Rate -White`. Wider than the 10-demographic standard the other families use (adds Active Duty, Female/Male, Foster, Homeless, Migrant, Not Economically Disadvantaged, Students Without Disability, and uses `Limited English Proficient` in place of `English Learners`) |
| PROGRAM_TOTAL | Numerator — number of cohort members who graduated (string; suppression marker `TFS`). Equivalent to `Total Graduated` in Family C |
| PROGRAM_PERCENT | Graduation rate, 0-100 scale (string; suppression marker `TFS`) |
| TOTAL_COUNT | Denominator — adjusted cohort size (string; suppression marker `TFS`). Equivalent to `Graduation Class Size` in Family C |

#### Sample Data

```
shape: (3, 11)
LONG_SCHOOL_YEAR | DETAIL_LVL_DESC | SCHOOL_DSTRCT_CD | SCHOOL_DSTRCT_NM  | INSTN_NUMBER | INSTN_NAME        | GRADES_SERVED_DESC          | LABEL_LVL_1_DESC          | PROGRAM_TOTAL | PROGRAM_PERCENT | TOTAL_COUNT
2022-23          | State           | ALL              | All Column Values | ALL          | All Column Values | PK,KK,01,...,12             | Grad Rate -ALL Students   | 113735        | 84.36           | 134822
2022-23          | District        | 601              | Appling County    | ALL          | All Column Values | PK,KK,01,02,...,12          | Grad Rate -ALL Students   | 236           | 93.65           | 252
2022-23          | District        | 601              | Appling County    | ALL          | All Column Values | PK,KK,01,02,...,12          | Grad Rate -Active Duty    | TFS           | TFS             | TFS
```

#### Statistics

Row count: 13,075. Detail-level breakdown: State = 18 rows (one per demographic), District = 3,807 rows, School = 9,250 rows. Single `LONG_SCHOOL_YEAR` value: `2022-23`.

#### Null Counts

All 11 columns: 0 nulls (suppression is via the text marker `TFS`).

#### Categorical Columns

| Column | Distinct Values |
|--------|-----------------|
| LONG_SCHOOL_YEAR | `2022-23` (only) |
| DETAIL_LVL_DESC | `State`, `District`, `School` |
| LABEL_LVL_1_DESC | 18 `Grad Rate -…`-prefixed demographic strings (see column table above) |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|--------------------|
| SCHOOL_DSTRCT_CD | `ALL` (18 — state rows) |
| INSTN_NUMBER | `ALL` (state + district rows) |
| PROGRAM_TOTAL | `TFS` (6,707) |
| PROGRAM_PERCENT | `TFS` (6,707) |
| TOTAL_COUNT | `TFS` (6,707) |

All three numeric columns are suppressed in lockstep — the same 6,707 rows carry `TFS` across `PROGRAM_TOTAL`, `PROGRAM_PERCENT`, and `TOTAL_COUNT`.

---

## ETL Considerations

### Multiple file families covering the same conceptual measure

The bronze directory mixes **six distinct file families** that all pertain to graduation rates. The transform must decide which file(s) to use as the authoritative source for each year and metric:

- **CCRPI Graduation Rate (Family A)** is the most complete: state/district/school detail, both 4-year and 5-year, with targets and flags. Years available: 2018, 2019, 2020, 2022 (no targets), 2023, 2024, 2025. **Notably no 2021** CCRPI release (COVID year — federal accountability suspended).
- **Standalone 4-Year Cohort (Family C)** provides 4-year rates for 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2024, 2025 — fills the 2015-2017 gap (no CCRPI yet) and the 2021 gap (no CCRPI release that year). Adds `Graduation Class Size` and `Total Graduated` (counts) which CCRPI files lack.
- **Standalone 5-Year Graduation Rate (Family D)** provides only 2021 5-year data (fills the 2021 CCRPI gap for 5-year).
- **Legacy Graduation Rate (Family B)** provides 4-year rates for 2012, 2013, 2014 (pre-CCRPI baseline).
- **On-Time Graduation Rate (Family E)** is a different statutory measure (SB 431) — a stricter definition than the federal 4-year cohort rate. Only school-level; only 2021-2024.
- **GOSA 4-Year Cohort CSV (Family F)** is a single 2023 CSV that fills the 2023 4-year count gap. The Family C standalone release for 2023 is only published as the 125-page PDF (unreadable), so the GOSA CSV is the canonical source for 2023 4-year `total_graduated` and `graduation_class_size` (numerator + denominator). The 2023 CCRPI XLSX still supplies the rate, target, and flag.

If the gold output is meant to consolidate "the" graduation rate per year, the CCRPI value should be preferred when available, then the standalone 4-Year/5-Year file, then the legacy file. Class-size data should be sourced from the standalone 4-Year files (Family C) for years 2015-2022, 2024-2025 and from the GOSA CSV (Family F) for 2023. The On-Time rate should be treated as a separate metric (different definition), not folded into the headline graduation rate.

### Year representation varies by family

- Family A (CCRPI): integer `School Year` column. 2018-2020 contain a single year. 2022-2025 contain TWO years (current year's 4-year rate + prior year's 5-year rate, because 5-year cohorts need an extra year of follow-up).
- Family B (legacy): string `COHORT YEAR` / `Cohort Year` column matches the filename year.
- Family C (standalone 4-Year): NO year column — must be parsed from the filename. Files dated `02.19.18` actually contain 2017 data (filename year = data year + 1). Other dated files have filename year = data year. The year-prefixed 2024 and 2025 files have year = data year.
- Family D (standalone 5-Year): NO year column — `12.08.21` file contains 2021 data.
- Family E (On-Time): integer `Year` column (with a leading space in 2021 only) matches filename year.
- Family F (GOSA CSV): string `LONG_SCHOOL_YEAR` column in `YYYY-YY` form (e.g., `2022-23`). The graduation year is the second part — `2022-23` → data year 2023.

### Sheet structure varies — multi-sheet concatenation needed for Family C and D

- Family C and D files have an `All Students` (or `ALL Student` / `All Student`) sheet containing only the `ALL Students` demographic but with `Graduation Class Size` and `Total Graduated`, AND a `Subgroup` (or `Subgroups` / `Student Group`) sheet containing all 10 demographics but only the rate. To get class size by demographic, the two sheets must be combined; the subgroup sheet has no count info.
- Sheet names are inconsistent across years: `All Students` / `ALL Student` / `All Student` / `ALL Students` (with trailing 's' or not, with varying capitalization). Must use a flexible matcher.
- Family E has a `Details` metadata sheet that should be skipped during transform.

### Disclaimer rows requiring `header_row=1`

- Standalone 4-Year files dated `12.08.21` and `10_06_22` have a USDA School Food Authorities waiver disclaimer in row 0.
- All On-Time Graduation Rate files have the SB 431 statutory definition as row 0.
- 5-Year Graduation Rate file (12.08.21) does NOT have a disclaimer (default `header_row=0`).

### Column name inconsistencies across eras

| Concept | Legacy 2012 | Legacy 2013 | Legacy 2014 | Standalone 2015 | Standalone 2016+ | CCRPI all years | On-Time | GOSA CSV |
|---------|-------------|-------------|-------------|-----------------|-------------------|------------------|---------|----------|
| Year | COHORT YEAR | COHORT YEAR | Cohort Year | (none) | (none) | School Year | Year | LONG_SCHOOL_YEAR |
| Detail level | REPORTING LEVEL | REPORTING LEVEL | (none) | REPORTING LEVEL | Reporting Level | (derived) | Reporting Level | DETAIL_LVL_DESC |
| District code | SYSTEM ID | SYSTEM ID | System ID | SYSTEM ID | System ID | System ID | System ID | SCHOOL_DSTRCT_CD |
| School code | SCHOOL ID | SCHOOL ID | School ID | SCHOOL ID&nbsp; (trailing space in `All Students` sheet) / SCHOOL ID | School ID | School ID | School ID | INSTN_NUMBER |
| Demographic | REPORTING CATEGORY | REPORTING LABEL | Reporting Category Code | REPORTING LABEL | Reporting Label | Reporting Label | Reporting Label | LABEL_LVL_1_DESC (prefixed `Grad Rate -…`) |
| Rate metric | GRADUATION RATE | GRADUATION RATE | Graduation Rate | GRADUATION RATE | Graduation Rate | Graduation Rate | On-Time Graduation Rate | PROGRAM_PERCENT |

Note the trailing space in `SCHOOL ID ` in the 2015 file's `All Students` sheet — this differs from the `SCHOOL ID` in the same file's `Subgroups` sheet.

### Demographic naming inconsistencies

- `American Indian/Alaskan` is used in: legacy 2012-2014, CCRPI 2018-2020, standalone 4-Year 2015-12.08.21, 5-Year 2021, On-Time 2021, and Family F GOSA CSV (under the `Grad Rate -American Indian/Alaskan` label).
- `American Indian/Alaskan Native` is used in: CCRPI 2022-2025, standalone 4-Year 10_06_22 onwards, On-Time 2022 onwards.
- Family F also uses `Limited English Proficient` in place of `English Learners` — semantically equivalent and folded together in gold.
- Family F adds eight demographics not present in the other families: `Active Duty`, `Female`, `Foster`, `Homeless`, `Male`, `Migrant`, `Not Economically Disadvantaged`, and `Students Without Disability`. All Family F demographic labels carry a `Grad Rate -` prefix that must be stripped before normalization.
- All other 9 demographic labels are stable across all files (`ALL Students`, `Asian/Pacific Islander`, `Black`, `Economically Disadvantaged`, `English Learners`, `Hispanic`, `Multi-Racial`, `Students With Disability`, `White`). Note `Students With Disability` is consistently capital-W (no `with` lowercase variant in this topic).

### Suppression marker variations

| Family | Markers |
|--------|---------|
| Family A (CCRPI) | `TFS`, `No Data` (rate); `TFS`, `NA` (target); `NA` (flag) |
| Family B (legacy) | `Too Few Students`, `No Data Found` |
| Family C (standalone 4-Year) | `Too Few Students`, `No Data` |
| Family D (5-Year 2021) | `Too Few Students`, `No Data` |
| Family E (On-Time) | `Too Few Students`, `No Data` |
| Family F (GOSA CSV) | `TFS` (across PROGRAM_TOTAL, PROGRAM_PERCENT, and TOTAL_COUNT — same rows in all three columns) |

The legacy files use `No Data Found` (3-word marker) while the others use `No Data`. Normalize to a single null representation.

### ID column type and zero-padding inconsistencies

- Earlier years (2012-2017): System ID and School ID are strings, often zero-padded (`0103`, `0212`).
- Later years (2018+): System ID and School ID are typically integers in CCRPI files (with null for state aggregates), losing leading zeros. School ID stays as string in some files.
- The standalone 4-Year files vary year-by-year: some files have `System ID` as string (`601`), some as i64 (`601`).
- For consistent gold output, cast all to string and zero-pad School ID to 4 characters and System ID to 3 characters. Treat `ALL` (string) and null (int) both as the aggregate marker.

### Dual-year CCRPI files (2022-2025)

Starting with the 2022 release, CCRPI files contain TWO `School Year` values:

| File | School Year values |
|------|--------------------|
| 2022 | 2021 (5-year cohort) + 2022 (4-year cohort) |
| 2023 | 2022 (5-year) + 2023 (4-year) |
| 2024 | 2023 (5-year) + 2024 (4-year) |
| 2025 | 2024 (5-year) + 2025 (4-year) |

The earlier 2018-2020 CCRPI files contain only one `School Year` value (with both 4-year and 5-year measured for that same graduation year). The transform should not assume one year per file.

### State-level aggregate detection

| Family | State row identifier |
|--------|----------------------|
| Family A (CCRPI) | `System ID` is null AND `System Name` is `All Systems` |
| Family B 2012-2013 | NO state rows present (only system + school) |
| Family B 2014 | `System ID` is `ALL` AND `System Name` is `All Systems` |
| Family C/D | `Reporting Level` is `State` (or `System ID` is `ALL` / null) |
| Family E (On-Time) | NO aggregate rows — school-level only |
| Family F (GOSA CSV) | `DETAIL_LVL_DESC` is `State` (also `SCHOOL_DSTRCT_CD` and `INSTN_NUMBER` are `ALL`) |

### District (system) aggregate detection

| Family | District row identifier |
|--------|-------------------------|
| Family A (CCRPI) | `School ID` is `ALL` AND `School Name` is `All Schools` |
| Family B (legacy) | `REPORTING LEVEL` is `System` (2012-2013) or `School ID` is `ALL` (2014) |
| Family C/D | `Reporting Level` is `System` (or `School ID` is `ALL`) |
| Family E (On-Time) | NO district rows present |
| Family F (GOSA CSV) | `DETAIL_LVL_DESC` is `District` (with `INSTN_NUMBER` = `ALL`) |

### CCRPI Target/Flag are unavailable in 2020 and 2022

- **2020 CCRPI**: All `Target` values are `NA` and all `Flag` values are `NA` because CCRPI scoring was suspended for COVID-19. The graduation rate values themselves are still valid.
- **2022 CCRPI**: The `Target` and `Flag` columns are not present in the file at all. The graduation rate values are still reported.

### Unreadable PDF (superseded by the GOSA CSV)

`4-Year Cohort Graduation Rate State District School by Subgroups_12.14.23.pdf` is a 125-page PDF. Its contents correspond to the 2023 standalone 4-Year cohort data (file is dated 12.14.23, matching a December 2023 release). The transform skips this PDF and instead pulls 2023 4-year cohort data from two sources:

1. The 2023 CCRPI XLSX (`2023 CCRPI Graduation Rates, Targets, and Flags by Subgroup_12_14_23.xlsx`) supplies the graduation rate, target, flag, and 5-year rate.
2. The Family F GOSA CSV (`GOSA_4-Year_Cohort_Graduation_Rate_2022-23_12.15.23.csv`) supplies the 2023 4-year numerator (`PROGRAM_TOTAL` → `total_graduated`) and denominator (`TOTAL_COUNT` → `graduation_class_size`) that the CCRPI XLSX omits.

The PDF itself remains in bronze but is in the transform's `SKIP_FILES` list.

### Graduation Rate values can equal 0 or 100

Several files contain `Graduation Rate` values of `0` (worst case) and `100` (best case). The describe min for 2018 CCRPI shows 0; max non-suppression value approaches 100. No special handling needed for these — they are valid numeric values.

### Grade Cluster is always `H`

In every CCRPI file, `Grade Cluster` is `H` (high school) for every row. This column carries no information for this dataset and can be dropped from gold.

### Grade Configuration is a school attribute

`Grade Configuration` (e.g., `09, 10, 11, 12` or `PK, KK, 01, ..., 12`) describes which grades the school serves, not which grade was tested. It belongs in the school dimension if needed; it is not a fact metric or fact categorical.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| COHORT YEAR / Cohort Year (legacy) | not_in_gold | — | Year is captured as `year`; this column is redundant |
| School Year (CCRPI) | not_in_gold | — | Used to populate `year`; no direct mapping (each row's `School Year` becomes the row's `year`) |
| Year /  Year (On-Time) | not_in_gold | — | Used to populate `year` |
| LONG_SCHOOL_YEAR (GOSA CSV) | not_in_gold | — | Used to populate `year`. The graduation year is the trailing 2-digit portion (`2022-23` → 2023). In practice the GOSA CSV is hard-mapped to year 2023 in the transform's `FILE_YEAR_OVERRIDES` |
| (filename year, standalone) | not_in_gold | — | Parsed to populate `year` (with offset for `02.19.18` file) |
| REPORTING LEVEL / Reporting Level / DETAIL_LVL_DESC | not_in_gold | — | Used to derive detail level / discriminate state/district/school rows; the actual detail level is encoded by which of `district_code` / `school_code` is null in gold |
| SYSTEM ID / System ID / SCHOOL_DSTRCT_CD | fact_key | district_code | Cast to Utf8, zfill(3) for traditional districts; 7-digit charter/state-school operator codes preserved as-is. `ALL` (string) and null (int) both become NULL for state-level rows |
| SYSTEM NAME / System Name / SCHOOL_DSTRCT_NM | dimension_attribute | — | district_name in districts dimension; `All Systems` / `All Column Values` becomes NULL/state marker |
| SCHOOL ID / School ID / SCHOOL ID&nbsp; (with trailing space) / INSTN_NUMBER | fact_key | school_code | Cast to Utf8, zfill(4). `ALL` becomes NULL for district/state-level rows |
| SCHOOL NAME / School Name / INSTN_NAME | dimension_attribute | — | school_name in schools dimension; `All Schools` / `All Column Values` becomes NULL |
| Grade Configuration / GRADES_SERVED_DESC | not_in_gold | — | School attribute (which grades the school serves); belongs in school dimension if needed at all |
| Grade Cluster | not_in_gold | — | Always `H`; carries no information |
| REPORTING CATEGORY / REPORTING LABEL / Reporting Category Code / Reporting Label / LABEL_LVL_1_DESC | fact_key | demographic | FK to demographics dimension. For Family F, strip the `Grad Rate -` prefix first; map `Limited English Proficient` → `english_learners` (folds with `English Learners`). Normalize `American Indian/Alaskan` → `American Indian/Alaskan Native` (or pick one canonical form per project standard). Family F also contributes extra demographics (`active_duty`, `female`, `male`, `foster_care`, `homeless`, `migrant`, `not_economically_disadvantaged`, `students_without_disabilities`) for 2023 only |
| Graduation Rate Type | fact_categorical | rate_type | `4-year` vs `5-year`. Values `4-year graduation rate` / `5-year graduation rate` should be normalized (e.g., `4_year`, `5_year`). For Family F, every row is `4_year` (the GOSA CSV is a 4-year cohort file) |
| GRADUATION RATE / Graduation Rate (all families) / PROGRAM_PERCENT (GOSA CSV) | fact_metric | graduation_rate | 0-100 scale. Cast suppression markers (`TFS`, `Too Few Students`, `No Data`, `No Data Found`) to null. (In practice, for 2023 the rate is sourced from the CCRPI XLSX, not Family F — Family F supplies counts only.) |
| On-Time Graduation Rate | fact_metric | on_time_graduation_rate | 0-100 scale. Separate metric from `graduation_rate`. Cast suppression markers to null. Only available 2021-2024, school-level only |
| GRADUATION CLASS SIZE / Graduation Class Size / TOTAL_COUNT (GOSA CSV) | fact_metric | graduation_class_size | Integer count. Cast suppression markers (`TFS`, `Too Few Students`) to null. Available in standalone 4-Year files (`All Students` sheet), on-time files (`Total Enrolled`), and Family F GOSA CSV (2023 4-year, all demographics) |
| TOTAL GRADUATED / Total Graduated / PROGRAM_TOTAL (GOSA CSV) | fact_metric | total_graduated | Integer count. Cast suppression markers to null. Same availability as class size; Family F supplies the 2023 4-year values |
| Total Enrolled (On-Time only) | fact_metric | total_enrolled | Integer count specific to the On-Time methodology (cohort starting October 1 of 9th grade year). Distinct from `graduation_class_size` |
| Target | fact_metric | ccrpi_target | CCRPI target rate, 0-100 scale. Cast `TFS` and `NA` to null. Only meaningful in CCRPI 2018, 2019, 2023, 2024, 2025; suppressed (all `NA`) in 2020; absent from 2022 file. Type varies (string vs f64) — always cast to f64 |
| Flag | fact_categorical | ccrpi_flag | `G`, `Y`, `R` (with `NA` cast to null). Only in CCRPI 2018, 2019, 2023, 2024, 2025; all `NA` in 2020; absent from 2022 file |

## Corrections (2026-06-12 rebuild verification)

Stale or missing claims found while re-verifying every invariant against the
bronze files during the clean-room transform rewrite. Each item states the
evidence; the body of this document above is preserved as originally written.

1. **Family A `System ID` "nulls" are a type-inference artifact — the bronze
   cells are the literal string `ALL`.** Era A1's Null Counts section claims
   "only `System ID` has nulls (= 20 rows in 2018-2024, 110 rows in 2025)" and
   the column table says `System ID` is "null for state-level rows". Re-read
   with string-typed reads (`pandas read_excel(dtype=str)`): every Family A
   file 2018-2025 has **zero** nulls in `System ID` and exactly **20 rows with
   the literal string `ALL`** (10 demographics × 2 rate types), which are the
   state-level rows (`System Name = "All Systems"`, `School ID = "ALL"`).
   Verified directly on the 2018 and 2025 files; the 2025 "110 nulls" figure
   is not reproducible under either string-typed or type-inferred pandas
   reads. The "State-level aggregate detection" table's Family A rule should
   read `System ID == 'ALL' AND System Name == 'All Systems'`.

2. **The `RTC` pseudo-district is missing from this document.** Family C
   standalone 4-year files for data years 2015-2018 (the 05.03.16, 11.29.16,
   02.19.18, and 09_19_18 files) each carry `System ID = "RTC"` rows — the
   Residential Treatment Center state-managed aggregate: 1 row in the
   All-Students sheet and 10 rows (one per demographic) in the Subgroup
   sheet, all with `Reporting Level = "System"` and `School ID = "ALL"`
   (district-level). `RTC` is an allowlisted pseudo-district code in the
   districts dimension (`district_type = state_special`; see education
   CLAUDE.md). No Family C file after 09_19_18 carries RTC rows, and no
   other family ever does.

3. **The 09_19_18 file's two sheets do not cover the same entities — the 30
   extra All-Students-sheet entities are fully suppressed.** The `All
   Student` sheet has 668 rows but the `Subgroup` sheet covers only 638
   entities (6,380 rows). The 30 All-Students-only entities (29 small
   special-purpose schools + 1 district, e.g. treatment centers, DJJ
   facilities, state schools) carry `Too Few Students` in ALL THREE metric
   columns (class size, total graduated, rate), so a transform that uses the
   Subgroup sheet as its row base loses no data. Every other Family C file
   has exactly matching entity sets across its two sheets.

4. **Family D's `ALL Student` sheet is a strict subset of its `Subgroup`
   sheet.** The 669 `ALL Student`-sheet keys all appear among the Subgroup
   sheet's 671 `ALL Students` rows with byte-identical `Graduation Rate`
   values (and the Subgroup sheet has 2 additional ALL-row keys). Reading
   only the Subgroup sheet loses nothing.

5. **On-Time co-suppression is exact, not approximate.** The Era E1 note
   "the same row *tends to* have all three values suppressed together" is
   stronger in reality: in all four On-Time files (2021-2024), `Total
   Enrolled`, `Total Graduated`, and `On-Time Graduation Rate` are suppressed
   in exact lockstep — zero partially-suppressed rows. Where all three are
   published, the rate reconciles with `100 × graduated / enrolled` to a max
   deviation of 0.005 (half the last published decimal, i.e. pure rounding).

6. **No `100.00+` top-cap sentinel in this topic.** Sibling CCRPI topics
   (content mastery) carry a literal `"100.00+"` score sentinel; a full scan
   of every sheet of every file in this directory finds none — graduation
   rates are plain numerics within [0, 100] plus the text suppression
   markers documented above.
