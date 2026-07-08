# enrollment_by_subgroup_programs — Bronze Data Structure

## Overview

- Topic: enrollment_by_subgroup_programs
- Source: gosa
- Files: 21 files spanning 2004–2024 (school years FY2003-04 through 2023-24)
- Unreadable files: none. Note: `enrollment_by_subgroup_programs_2006.csv` is misnamed — it is actually an Excel (.xls) binary workbook (Composite Document File V2, header bytes `D0 CF 11 E0`) despite the `.csv` extension, and must be read as Excel.
- Year representation:
  - 2004–2010 — year is only in the filename (no year column in the data). Files contain cross-sectional enrollment/AYP snapshots for the year named.
  - 2011–2024 — year is in both the filename and a `LONG_SCHOOL_YEAR` column (`YYYY-YY` format, e.g., `2023-24`). One school year per file.
- Filename-to-data year offset: same — the filename year matches the ending calendar year of the school year in `LONG_SCHOOL_YEAR` (e.g., `_2024.csv` contains `2023-24` rows). For 2004–2010 files, filename is assumed to follow the same convention (end-of-school-year), but cannot be confirmed from the data itself.
- Detail levels: state, district, school
  - 2004 — all three levels present in a single CSV, distinguished by `ID` format (`ALL:ALL` = state, `NNN:ALL` = district, `NNN:SCHOOL` = school).
  - 2005, 2006, 2007, 2008 — three levels split across three Excel sheets (`School Level`, `System Level`, `State Level`).
  - 2009 — school + district rows combined in `Sheet1` (no state row).
  - 2010 — school + district rows combined in `Sheet3` (no state row).
  - 2011–2024 — three levels in a single CSV/XLSX, distinguished by a `DETAIL_LVL_DESC` column (`State`, `District`, `School`).
- Percentage scale: 0–100 for every `ENROLL_PERCENT_*`, `ENROLL_PCT_*`, and `*Percentage of Enrollment` column (including race/ethnicity, ED, SWD, LEP, MIGRANT, MALE, FEMALE, and program-specific percentages like `ENROLL_PCT_GIFTED`). Bronze counts (`ENROLL_COUNT_*`) are raw integers.
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)
- **Note**: this bronze directory feeds two derived gold topics: enrollment_demographic_shares and enrollment_program_participation

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| enrollment_by_subgroup_programs_2004.csv | 82b786ef6fe68819e606ebe1033064f5c360a216fdae8a8bec836f0eb0e29979 |
| enrollment_by_subgroup_programs_2005.xls | 88a2ce9b93e55bba5db9058b181d1e2e5c90a151f9139bbc77ca5b88989c1be2 |
| enrollment_by_subgroup_programs_2006.csv | 99f5e012f3c46646691f36e826cecb04beea6f71a14ec4eda1c3def66d9e33e6 |
| enrollment_by_subgroup_programs_2007.xls | b3e193ae608fadbc9e005d7eed58d45725246e40796239e77283ab744c6efcc8 |
| enrollment_by_subgroup_programs_2008.xls | 4dc42a8429b7372a4d1d2ebae6fa4790176c812031242f2d414de8126dde570b |
| enrollment_by_subgroup_programs_2009.xls | 2f6faae7c24bdb3e1405fb36ea773cf5d84305e8da3a0c0833f9c9c9600780b2 |
| enrollment_by_subgroup_programs_2010.xls | bc0f5373e7359d1a2494e2f883daa0ef6150a1acc33dc383f9ea89dd83ec953d |
| enrollment_by_subgroup_programs_2011.csv | 386d8e9339ab88cea243c37556de5c0a74c8190bb9cdb313a46c60a550da9c54 |
| enrollment_by_subgroup_programs_2012.xlsx | c31edd77594395b7699c6a3bc2a59897914f9da40d042302c9909fd12e5ac897 |
| enrollment_by_subgroup_programs_2013.csv | 642c18b208d6c8e59e5dff0c01fdbb0d6fd54d3b86875092b3e9fca9c2d19dd8 |
| enrollment_by_subgroup_programs_2014.csv | 528fe3b014d68040ae2b76e618828110bd88d1a82f0d9809db253df7af9bdc26 |
| enrollment_by_subgroup_programs_2015.csv | 77d0f6fceb4ed16e8e18fe7865ea55008c12f2798e36d15a0f97d53781e32173 |
| enrollment_by_subgroup_programs_2016.csv | 991d493c32ddfe6fba3f92acd56b447c5457a2f0199c8a234e364613dd7970ae |
| enrollment_by_subgroup_programs_2017.csv | 2960c5dbed8d19dfb9c44e4387d8682420741c14ddacddddb169bd421ae9b161 |
| enrollment_by_subgroup_programs_2018.csv | 322ba6144a041e8c7fc69aa291003d031701aa05e54765efe388c6f5d16be137 |
| enrollment_by_subgroup_programs_2019.csv | 728967fc84dbf20126448077a09fc1db871e417942cbafb4b6419990723b5e31 |
| enrollment_by_subgroup_programs_2020.csv | b3e9017eed767293820814b5863cd47cef495dfe676828a430249e1975638b80 |
| enrollment_by_subgroup_programs_2021.csv | 3b1db7da0f0db005403fa6b68df6589797d969409b31505d6e934b2507221ff8 |
| enrollment_by_subgroup_programs_2022.csv | 885f866dea6f50d5334ef7e2715fca7558d827e25ea6153eaa137e37526058e8 |
| enrollment_by_subgroup_programs_2023.csv | fb4d63e22c1f90d3a2df3af4daa3742ecba60849b47f652abd71ad66573b0de6 |
| enrollment_by_subgroup_programs_2024.csv | 33aa2da28a0d5f71320f8f6546a03b9f3a10c63d16dbc3c0f343efa98cd0404a |

## Excel Sheet Structure

| File(s) | Sheets | Notes |
|---------|--------|-------|
| 2005.xls, 2006.csv (Excel binary), 2008.xls | `School Level` (Data), `System Level` (Data), `State Level` (Data) | All three sheets share the **same 15-column schema**. Transform must **concatenate all three** to recover state + district + school rows; pick the sheet based on detail level. |
| 2007.xls | `School level` (Data) **[lowercase `l` in "level"]**, `System Level` (Data), `State Level` (Data) | Same structure as 2005/2006/2008 but the `School` sheet's name uses lowercase `level`. Sheet-name lookup must be case-insensitive. |
| 2009.xls | `Sheet1` (Data), `Sheet2` (empty), `Sheet3` (empty) | School + district rows combined in one sheet; **no state row** in the file at all. `Sheet2`/`Sheet3` are zero-row placeholders — ignore them. |
| 2010.xls | `Sheet3` (Data) | Only `Sheet3` contains data (also school + district, **no state row**). `Sheet1`/`Sheet2` do not exist in this workbook. |
| 2012.xlsx | `Export Worksheet` (Data) | Single data sheet. |
| 2004.csv, 2011.csv, 2013–2024.csv | — (CSV, no sheets) | Single flat file per year. |

**Net transform impact:**

- For 2005–2008 (three-sheet eras), the transform must read each sheet and union the rows to produce a single long frame. Sheet-to-detail-level mapping is implicit (not stored inside the sheet) — capture `detail_level` during concatenation.
- 2009 and 2010 are missing a state row — the state aggregate simply is not present. Do not synthesize one.
- Default `pl.read_excel` reads only the first sheet and will silently drop district + state rollups for 2005–2008. Read each sheet explicitly.

## Summary

This dataset reports the percentage of each Georgia public school and district whose enrollment falls into various demographic and program subgroups. The demographics covered are race/ethnicity (Asian, Native American, Black, Hispanic, Multiracial, White), socioeconomic status (Economically Disadvantaged `ED`), disability (`SWD`), limited English proficiency / English learners (`LEP`), migrant status, and sex (Male, Female — present only in 2011 and 2018-2024). Starting with the 2011 file the dataset expands to include program-participation percentages and counts: Remedial grades 6-8 and 9-12, Early Intervention Program (`EIP`) K-5, Special Ed K-12 and Pre-K, `ESOL`, Vocational grades 9-12, Alternative Programs, and Gifted. The 2004–2010 files additionally carry the NCLB-era school accountability indicators `Met AYP` and `Improvement Status`, which disappear after AYP was retired.

The grain is one row per (year × entity), with the entity being a state, a district, or a school depending on the detail level.

## Eras

### Era 1: 2004–2006 (`ID` column, 15 columns, AYP-era)

15 columns. First column is `ID` with format `<SystemID>:<SchoolID>` (3-digit system, 4-digit school, or `ALL:ALL`/`NNN:ALL`/`NNN:SCHOOL` sentinel patterns). 2004 is a single CSV; 2005 and 2006 are Excel binaries split across `School Level`, `System Level`, `State Level` sheets (2006 is mislabeled with a `.csv` extension).

Column schema (all 15 columns, identical across files):

| Column | Description |
|--------|-------------|
| ID | Entity identifier. Format `<SystemID>:<SchoolID>` where `SystemID` is a 3-digit GOSA district code (or `ALL` for state) and `SchoolID` is a 4-digit school code (or `ALL` for district/state rows). |
| System Name | District/system name (`State of Georgia` for the state row). |
| School Name | School name (`State of Georgia` for state, district name for district rows). |
| Grades | Grade range served. 2004: dash-separated range (e.g., `K-5`, `6-8`, `9-12`, `PK-8`). 2005: quote-prefixed dash range (e.g., `'02-03`, `'03-05`, `'06-08`). 2006: comma-separated zero-padded (e.g., `01, 02, 03, 04, 05`) — 2006 already uses the same format 2007+ adopts. Blank for state row. |
| Met AYP | `Yes` / `No` / `N/A` indicator of whether the entity made Adequate Yearly Progress (NCLB). |
| Improvement Status | NCLB school-status category (`ADEQ`, `ADEQ_DNM`, `DIST`, `NI`, `NI_AYP`, or blank). |
| Asian Percentage of Enrollment | % enrolled identified as Asian (0–100 integer). |
| Black Percentage of Enrollment | % Black (0–100 integer). |
| Hispanic Percentage of Enrollment | % Hispanic (0–100 integer). |
| Native American Percentage of Enrollment | % Native American / American Indian (0–100 integer). |
| MultiracialPercentage of Enrollment | % Multiracial (0–100 integer). **Column header is missing the space between "Multiracial" and "Percentage".** The typo is present in every file 2004–2009. |
| White Percentage of Enrollment | % White (0–100 integer). |
| Limited English Proficient Percentage of Enrollment | % LEP / English learners (0–100 integer). |
| Economically Disadvantaged Percentage of Enrollment | % ED (0–100 integer). |
| With Disabilities Percentage of Enrollment | % students with disabilities / SWD (0–100 integer). |

#### Sample Data (2004)

| ID | System Name | School Name | Grades | Met AYP | Improvement Status | Asian % | Black % | Hispanic % | Native % | Multi % | White % | LEP % | ED % | SWD % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 601:1050 | Appling County | Altamaha Elementary School | K-5 | Yes | ADEQ | 0 | 5 | 3 | 0 | 1 | 91 | 1 | 41 | 18 |
| 601:ALL | Appling County | Appling County | K-12 | No | ADEQ_DNM | 0 | 26 | 6 | 0 | 1 | 67 | 3 | 61 | 16 |
| 601:177 | Appling County | Appling County Elementary School | 3-5 | Yes | ADEQ | 1 | 32 | 8 | 0 | 2 | 56 | 5 | 78 | 19 |

#### Statistics (Era 1 row counts)

| Year | School rows | District rows | State rows | Total |
|------|------------|---------------|-----------|-------|
| 2004 | 2,119 | 199 | 1 | 2,319 |
| 2005 | 2,069 | 184 | 1 | 2,254 |
| 2006 | 2,100 | 184 | 1 | 2,285 |

**2004 data quality (verified 2026-06-11):** the 2004 CSV contains one malformed junk row with `ID = '2'` (no colon; every other cell null — counted in the school-row figure above), and **109 exact duplicate rows** (109 IDs appear twice with byte-identical values in all 15 columns; hence the 2,210 distinct IDs vs 2,319 rows in the categorical table below). Transforms must drop the junk row and dedup the repeats.

All 15 columns are read as `Utf8` (Polars infers string because `Grades`, `Met AYP`, `Improvement Status` and the blank state-row cells contain non-numeric values).

#### Null Counts (2004)

| Column | Nulls |
|--------|-------|
| ID | 0 |
| System Name / School Name / Grades / Met AYP / Improvement Status | 1 (state row has blank `Grades`) |
| Race/ethnicity percentages (Asian, Black, Hispanic, Native, Multi, White) | 4 |
| LEP % | 1 |
| ED % | 4 |
| SWD % | 17 |

2005 and 2006 sheets have zero nulls per cell — all rows fully populated after concatenation.

#### Categorical Columns (2004)

| Column | Distinct Count | Notes |
|--------|---------------|-------|
| ID | 2,210 | Entity identifiers |
| System Name | 182 | District names; includes `State of Georgia` |
| School Name | 2,107 | School names |
| Grades | 50 | Dash-range format (`K-5`, `6-8`, `9-12`, `PK-8`, `1-12`); a few values include stray whitespace |
| Met AYP | 4 | `Yes`, `No`, `N/A`, blank |
| Improvement Status | 6 | `ADEQ`, `ADEQ_DNM`, `DIST`, `NI`, `NI_AYP`, blank |

#### Suppression Markers (Era 1)

None — every non-null percentage value is numeric. Blank cells are plain `null`, not a suppression sentinel.

### Era 2: 2007–2009 (`SysSchoolID` column, 15 columns, AYP-era)

Identical 15-column schema to Era 1 **except the first column is renamed from `ID` to `SysSchoolID`**. Same `<SystemID>:<SchoolID>` value pattern. 2007 and 2008 are Excel binaries with three sheets; 2009 is an Excel binary with a single `Sheet1` that combines school + district rows (no state row).

The `Grades` column uses the comma-separated zero-padded format in all three files (e.g., `09, 10, 11, 12`, `PK, KK, 01, 02, ..., 12`) — same as 2006 and 2011+.

| Column | Description |
|--------|-------------|
| SysSchoolID | Entity identifier (same as `ID` in Era 1). |
| (remaining 14 columns) | Identical to Era 1. |

#### Sample Data (2007, School level sheet)

| SysSchoolID | System Name | School Name | Grades | Met AYP | Improvement Status | Asian | Black | Hispanic | Native | Multi | White | LEP | ED | SWD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 601:103 | Appling County | Appling County High School | 09, 10, 11, 12 | Yes | DIST | 0 | 27 | 6 | 0 | 0 | 67 | 1 | 58 | 14 |
| 601:1050 | Appling County | Altamaha Elementary School | PK, KK, 01, 02, 03, 04, 05 | Yes | DIST | 0 | 4 | 4 | 0 | 1 | 91 | 0 | 46 | 17 |
| 601:177 | Appling County | Appling County Elementary School | 03, 04, 05 | Yes | ADEQ | 1 | 32 | 11 | 0 | 1 | 55 | 4 | 70 | 17 |

#### Statistics (Era 2 row counts)

| Year | School rows | District rows | State rows | Total |
|------|------------|---------------|-----------|-------|
| 2007 | 2,160 | 184 | 1 | 2,345 |
| 2008 | 2,206 | 185 | 1 | 2,392 |
| 2009 | 2,228 | 190 (combined with school rows in one sheet; split derived from the `:ALL` SysSchoolID suffix) | 0 | 2,418 |

**2009 data quality (verified 2026-06-11):** 4 SysSchoolID values appear twice. `796:105` and `796:ALL` (Odyssey) are byte-identical repeats; `768:ALL` (Ivy Prep) and `770:ALL` (Scholars Academy) differ only in the `School Name` / `Grades` cells (one row carries the name, the other the grade range) while all 9 percentage columns and both AYP columns are identical. Transforms that drop the name/grade dimension attributes can treat all 4 as exact repeats.

2007 uses a lowercase `School level` sheet name while every other year in 2005–2008 uses `School Level` — sheet-name lookup must be case-insensitive.

#### Null Counts (Era 2)

Zero nulls per column in 2007. In 2005 Polars logs `Could not determine dtype for column 5, falling back to string` when reading with auto-inference — read with `infer_schema_length=0` to force Utf8.

#### Categorical Columns (2007, all sheets concatenated)

| Column | Distinct Count | Notes |
|--------|---------------|-------|
| SysSchoolID | ~2,345 | Unique across all 3 sheets |
| System Name | 184 | |
| Grades | 84 | Comma-separated zero-padded |
| Met AYP | 3 | `Yes`, `No`, blank |
| Improvement Status | 7 | `.`, `ADEQ`, `ADEQ_DNM`, `DIST`, `NI`, `NI_AYP`, blank |

#### Suppression Markers (Era 2)

None in percentage columns. The literal `.` in `Improvement Status` is a "not applicable" sentinel, not a numeric suppression marker.

### Era 3: 2010 (single-sheet Excel, abbreviated headers)

15 columns — same semantics as Era 1/2 but **every column name is abbreviated and lowercase**. Literal column-name crosswalk is required. Single sheet named `Sheet3` (the only sheet in the workbook). School + district rows combined; no state row.

| Bronze Column (2010) | Era 1/2 Equivalent | Description |
|---|---|---|
| SysSchoolID | ID / SysSchoolID | Entity identifier |
| systemname | System Name | District name |
| schoolname | School Name | School name |
| graderange | Grades | Grade range (`PK, KK, 01, 02, 03, 04, 05`, etc.) |
| ayp_status | Met AYP | `Yes`/`No` |
| ni_status | Improvement Status | `ADEQ`, `DIST`, `NI`, etc. |
| A | Asian Percentage of Enrollment | % Asian |
| B | Black Percentage of Enrollment | % Black |
| H | Hispanic Percentage of Enrollment | % Hispanic |
| N | Native American Percentage of Enrollment | % Native American |
| U | MultiracialPercentage of Enrollment | % Multiracial |
| W | White Percentage of Enrollment | % White |
| L | Limited English Proficient Percentage of Enrollment | % LEP |
| ED | Economically Disadvantaged Percentage of Enrollment | % ED |
| S | With Disabilities Percentage of Enrollment | % SWD |

#### Sample Data (2010)

| SysSchoolID | systemname | schoolname | graderange | ayp_status | ni_status | A | B | H | N | U | W | L | ED | S |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 601:103 | Appling County | Appling County High School | 09, 10, 11, 12 | No | ADEQ_DNM | 1 | 24 | 8 | 0 | 2 | 65 | 1 | 57 | 15 |
| 601:1050 | Appling County | Altamaha Elementary School | PK, KK, 01, 02, 03, 04, 05 | Yes | DIST | 1 | 4 | 5 | 0 | 1 | 90 | 2 | 53 | 15 |
| 601:109 | Appling County | Baxley Wilderness Institute | 07, 08, 09, 10, 11 | No | . | 0 | 59 | 7 | 0 | 0 | 33 | 0 | 100 | 15 |

#### Statistics (2010)

- Row count: **2,441** (2,260 school + 181 district + 0 state)
- All columns read as `Utf8` with `infer_schema_length=0`.
- Max values by column: A=58, B=100, H=94, N=5, U=21, W=99, L=100, **ED=102**, S=100. The `ED` max of 102 on one district row is a GOSA rounding artifact — do not hard-cap at 100.

#### Null Counts (2010)

Zero nulls across every column.

#### Categorical Columns (2010)

| Column | Distinct Count | Notes |
|--------|---------------|-------|
| SysSchoolID | 2,441 | |
| systemname | 181 | |
| graderange | 77 | Comma-separated zero-padded |
| ayp_status | 2 | `No`, `Yes` |
| ni_status | 6 | `.`, `ADEQ`, `ADEQ_DNM`, `DIST`, `NI`, `NI_AYP` |

#### Suppression Markers (2010)

None in percentage columns. `ni_status = '.'` is a "not applicable" sentinel.

### Era 4: 2011 (CSV, 37 columns, new program columns + MALE/FEMALE)

37 columns. Major schema expansion — the dataset switches from the AYP-era 15-column format to a much richer table that adds:

- A formal `DETAIL_LVL_DESC` column identifying state/district/school rows (replaces the embedded `ID`/`SysSchoolID` convention).
- A `LONG_SCHOOL_YEAR` column (`2010-11` format, one value per file).
- Separate `INSTN_NUMBER` (school code) and `SCHOOL_DSTRCT_CD` (district code) columns instead of the concatenated `ID`.
- An `INSTN_NAME` (school name) column distinct from `SCHOOL_DSTRCT_NM` (district name).
- A `GRADES_SERVED_DESC` column (comma-list, no whitespace; e.g., `01,02,03,04,05` instead of `01, 02, 03, 04, 05`).
- **9 program-enrollment (count, percent) pairs**: Remedial 6-8, EIP K-5, Remedial 9-12, Special Ed K-12, ESOL, Special Ed PK, Vocation 9-12, Alt Programs, Gifted. The EIP pair uses the synonym `ENROLL_PERCENT_EIP_K_5` — every other program percentage uses `ENROLL_PCT_*`.
- **Sex columns** `ENROLL_PERCENT_MALE`, `ENROLL_PERCENT_FEMALE` (present in 2011, then dropped for 2012–2017, restored in 2018).
- **`Met AYP` and `Improvement Status` are dropped** — the AYP program had ended.

Full column list (file order):

```
DETAIL_LVL_DESC, INSTN_NUMBER, SCHOOL_DSTRCT_CD, LONG_SCHOOL_YEAR, INSTN_NAME,
SCHOOL_DSTRCT_NM, GRADES_SERVED_DESC,
ENROLL_PERCENT_ASIAN, ENROLL_PERCENT_NATIVE, ENROLL_PERCENT_BLACK,
ENROLL_PERCENT_HISPANIC, ENROLL_PERCENT_MULTIRACIAL, ENROLL_PERCENT_WHITE,
ENROLL_PERCENT_MIGRANT, ENROLL_PERCENT_ED, ENROLL_PERCENT_SWD, ENROLL_PERCENT_LEP,
ENROLL_COUNT_REMEDIAL_GR_6_8, ENROLL_PCT_REMEDIAL_GR_6_8,
ENROLL_COUNT_EIP_K_5, ENROLL_PERCENT_EIP_K_5,
ENROLL_COUNT_REMEDIAL_GR_9_12, ENROLL_PCT_REMEDIAL_GR_9_12,
ENROLL_COUNT_SPECIAL_ED_K12, ENROLL_PCT_SPECIAL_ED_K12,
ENROLL_COUNT_ESOL, ENROLL_PCT_ESOL,
ENROLL_COUNT_SPECIAL_ED_PK, ENROLL_PCT_SPECIAL_ED_PK,
ENROLL_COUNT_VOCATION_9_12, ENROLL_PCT_VOCATION_9_12,
ENROLL_COUNT_ALT_PROGRAMS, ENROLL_PCT_ALT_PROGRAMS,
ENROLL_COUNT_GIFTED, ENROLL_PCT_GIFTED,
ENROLL_PERCENT_MALE, ENROLL_PERCENT_FEMALE
```

#### Statistics (2011)

- Row count: **2,536** (2,340 school + 195 district + 1 state)
- All columns read as `Utf8` when `infer_schema_length=0`.
- `INSTN_NUMBER` is 4-digit zero-padded (e.g., `0103`), **or the literal `ALL`** for state/district rows.
- `SCHOOL_DSTRCT_CD` is 3-digit (e.g., `601`) or 7-digit (charter), **or the literal `ALL`** for state rows.

#### Null Counts (2011)

Program-enrollment count/percent columns are null for schools that don't offer the relevant program (e.g., `ENROLL_COUNT_REMEDIAL_GR_6_8` is null for elementary schools). Demographic and sex percentages are dense. No `TFS` suppression.

**`ENROLL_PERCENT_LEP` school-level suppression (2011 only).** Unlike every adjacent year, the 2011 file suppresses `ENROLL_PERCENT_LEP` at the school grain: 2,033 of 2,340 school rows (86.9%) are null, while district (1/195 null) and state (0/1 null) levels are fully populated. The 2010 source carries no LEP column at all and 2012 onward publishes LEP at ≤0.2% null across all detail levels. Most likely cause: GOSA's pre-CCRPI school-level cell-suppression policy, lifted in the 2012 release coinciding with the May 2013 CCRPI overhaul. The transform preserves the values that are present and does not impute.

#### Categorical Columns (2011)

| Column | Distinct Count | Notes |
|--------|---------------|-------|
| DETAIL_LVL_DESC | 3 | `District`, `School`, `State` |
| LONG_SCHOOL_YEAR | 1 | `2010-11` |
| SCHOOL_DSTRCT_NM | 197 | Includes `All Column Values` sentinel |
| INSTN_NAME | 2,212 | Includes `All Column Values` sentinel |
| GRADES_SERVED_DESC | 81 | Comma-separated zero-padded (no spaces) |

#### Suppression Markers (2011)

| Column | Marker | Meaning |
|--------|--------|---------|
| INSTN_NUMBER | `ALL` | Aggregate row (district or state) — not a number |
| SCHOOL_DSTRCT_CD | `ALL` | State-level row — not a number |

No `TFS` yet; all numeric percentage/count columns contain only digits or null.

### Era 5: 2012–2017 (CSV/XLSX, 35 columns, MALE/FEMALE dropped)

35 columns. Identical to Era 4 **minus** `ENROLL_PERCENT_MALE` and `ENROLL_PERCENT_FEMALE`. All other 35 columns (including every program-enrollment pair and `ENROLL_PERCENT_EIP_K_5`) are in the same order as Era 4. 2012 is delivered as XLSX (`Export Worksheet` sheet), 2013–2017 as CSV.

Full column list:

```
DETAIL_LVL_DESC, INSTN_NUMBER, SCHOOL_DSTRCT_CD, LONG_SCHOOL_YEAR, INSTN_NAME,
SCHOOL_DSTRCT_NM, GRADES_SERVED_DESC,
ENROLL_PERCENT_ASIAN, ENROLL_PERCENT_NATIVE, ENROLL_PERCENT_BLACK,
ENROLL_PERCENT_HISPANIC, ENROLL_PERCENT_MULTIRACIAL, ENROLL_PERCENT_WHITE,
ENROLL_PERCENT_MIGRANT, ENROLL_PERCENT_ED, ENROLL_PERCENT_SWD, ENROLL_PERCENT_LEP,
ENROLL_COUNT_REMEDIAL_GR_6_8, ENROLL_PCT_REMEDIAL_GR_6_8,
ENROLL_COUNT_EIP_K_5, ENROLL_PERCENT_EIP_K_5,
ENROLL_COUNT_REMEDIAL_GR_9_12, ENROLL_PCT_REMEDIAL_GR_9_12,
ENROLL_COUNT_SPECIAL_ED_K12, ENROLL_PCT_SPECIAL_ED_K12,
ENROLL_COUNT_ESOL, ENROLL_PCT_ESOL,
ENROLL_COUNT_SPECIAL_ED_PK, ENROLL_PCT_SPECIAL_ED_PK,
ENROLL_COUNT_VOCATION_9_12, ENROLL_PCT_VOCATION_9_12,
ENROLL_COUNT_ALT_PROGRAMS, ENROLL_PCT_ALT_PROGRAMS,
ENROLL_COUNT_GIFTED, ENROLL_PCT_GIFTED
```

#### Statistics (Era 5 row counts)

| Year | School rows | District rows | State rows | Total | LONG_SCHOOL_YEAR |
|------|------------|---------------|-----------|-------|------------------|
| 2012 | 2,291 | 196 | 1 | 2,488 | 2011-12 |
| 2013 | 2,273 | 198 | 1 | 2,472 | 2012-13 |
| 2014 | 2,261 | 198 | 1 | 2,460 | 2013-14 |
| 2015 | 2,270 | 199 | 1 | 2,470 | 2014-15 |
| 2016 | 2,269 | 204 | 1 | 2,474 | 2015-16 |
| 2017 | 2,271 | 207 | 1 | 2,479 | 2016-17 |

#### Null Counts (Era 5)

Program-enrollment columns (`ENROLL_COUNT_REMEDIAL_GR_6_8`, `ENROLL_PCT_REMEDIAL_GR_6_8`, `ENROLL_COUNT_EIP_K_5`, `ENROLL_PERCENT_EIP_K_5`, `ENROLL_COUNT_REMEDIAL_GR_9_12`, `ENROLL_PCT_REMEDIAL_GR_9_12`, and the Special Ed / Vocation / Alt pairs) are **null for schools that do not offer the relevant program** (e.g., `REMEDIAL_GR_6_8` is null for elementary and high schools). Demographic percentage columns remain dense across all schools. No `TFS` suppression.

**`ENROLL_PCT_SPECIAL_ED_PK` denominator shift between 2012 and 2013.** Within Era 5, the `ENROLL_PCT_SPECIAL_ED_PK` column undergoes an undocumented methodology change between the 2012 file and the 2013 file: 2012 mean = ~1.0% with max = 759.4% (mechanically impossible as a percentage); 2013 mean = ~19% capped at 100%, even though companion `ENROLL_COUNT_SPECIAL_ED_PK` mean stays steady at ~11 students per row in both years. The most likely cause is a denominator switch from "total K-12 enrollment" (pre-2013) to "PK enrollment / grades served by the program" (2013+), the latter matching GOSA's current published methodology and coinciding with the May 2013 CCRPI launch. The transform NULLs pre-2013 `pct_special_ed_pk` values in gold (they cannot be re-normalized without GOSA's historical denominator definitions) while preserving `count_special_ed_pk`.

#### Categorical Columns (2013 representative)

| Column | Distinct Count | Notes |
|--------|---------------|-------|
| DETAIL_LVL_DESC | 3 | `District`, `School`, `State` |
| LONG_SCHOOL_YEAR | 1 | `2012-13` |
| SCHOOL_DSTRCT_NM | 199 | Includes `All Column Values` sentinel |
| INSTN_NAME | ~2,167 | Includes `All Column Values` sentinel |
| GRADES_SERVED_DESC | 72 | Comma-separated zero-padded |

#### Suppression Markers (Era 5)

| Column | Marker | Meaning |
|--------|--------|---------|
| INSTN_NUMBER | `ALL` | District or state row |
| SCHOOL_DSTRCT_CD | `ALL` | State row |

No `TFS` yet; no explicit percent-suppression marker.

### Era 6: 2018–2022 (CSV, 37 columns, MALE/FEMALE returns, TFS appears in 2021)

37 columns — Era 5 plus `ENROLL_PERCENT_MALE` and `ENROLL_PERCENT_FEMALE` (the same pair that was in 2011, then dropped, now restored at the end of the column list). Format is otherwise identical to Era 5.

**Critical change mid-era:** The suppression sentinel **`TFS`** ("Too Few Students" — cell suppressed for privacy because the underlying count is below threshold) first appears in **2021** for **all 9 program-enrollment count columns** (`ENROLL_COUNT_REMEDIAL_GR_6_8`, `ENROLL_COUNT_EIP_K_5`, `ENROLL_COUNT_REMEDIAL_GR_9_12`, `ENROLL_COUNT_SPECIAL_ED_K12`, `ENROLL_COUNT_ESOL`, `ENROLL_COUNT_SPECIAL_ED_PK`, `ENROLL_COUNT_VOCATION_9_12`, `ENROLL_COUNT_ALT_PROGRAMS`, `ENROLL_COUNT_GIFTED`). Percentage columns in 2021–2022 remain numeric (no `TFS` on percentages until Era 7).

Full column list:

```
DETAIL_LVL_DESC, INSTN_NUMBER, SCHOOL_DSTRCT_CD, LONG_SCHOOL_YEAR, INSTN_NAME,
SCHOOL_DSTRCT_NM, GRADES_SERVED_DESC,
ENROLL_PERCENT_ASIAN, ENROLL_PERCENT_NATIVE, ENROLL_PERCENT_BLACK,
ENROLL_PERCENT_HISPANIC, ENROLL_PERCENT_MULTIRACIAL, ENROLL_PERCENT_WHITE,
ENROLL_PERCENT_MIGRANT, ENROLL_PERCENT_ED, ENROLL_PERCENT_SWD, ENROLL_PERCENT_LEP,
ENROLL_COUNT_REMEDIAL_GR_6_8, ENROLL_PCT_REMEDIAL_GR_6_8,
ENROLL_COUNT_EIP_K_5, ENROLL_PERCENT_EIP_K_5,
ENROLL_COUNT_REMEDIAL_GR_9_12, ENROLL_PCT_REMEDIAL_GR_9_12,
ENROLL_COUNT_SPECIAL_ED_K12, ENROLL_PCT_SPECIAL_ED_K12,
ENROLL_COUNT_ESOL, ENROLL_PCT_ESOL,
ENROLL_COUNT_SPECIAL_ED_PK, ENROLL_PCT_SPECIAL_ED_PK,
ENROLL_COUNT_VOCATION_9_12, ENROLL_PCT_VOCATION_9_12,
ENROLL_COUNT_ALT_PROGRAMS, ENROLL_PCT_ALT_PROGRAMS,
ENROLL_COUNT_GIFTED, ENROLL_PCT_GIFTED,
ENROLL_PERCENT_MALE, ENROLL_PERCENT_FEMALE
```

#### Sample Data (2018)

| DETAIL_LVL_DESC | INSTN_NUMBER | SCHOOL_DSTRCT_CD | LONG_SCHOOL_YEAR | INSTN_NAME | ... | ENROLL_PERCENT_MALE | ENROLL_PERCENT_FEMALE |
|---|---|---|---|---|---|---|---|
| School | 0103 | 601 | 2017-18 | Appling County High School | ... | 53 | 47 |
| School | 0177 | 601 | 2017-18 | Appling County Elementary School | ... | 51 | 49 |

#### Sample Data (2021 — TFS appears)

| DETAIL_LVL_DESC | INSTN_NUMBER | SCHOOL_DSTRCT_CD | LONG_SCHOOL_YEAR | ... | ENROLL_COUNT_EIP_K_5 | ENROLL_COUNT_SPECIAL_ED_K12 | ENROLL_COUNT_ESOL | ENROLL_COUNT_GIFTED |
|---|---|---|---|---|---|---|---|---|
| School | 0177 | 601 | 2020-21 | ... | 91 | 86 | 64 | 29 |
| School | 0277 | 601 | 2020-21 | ... | 141 | 64 | 94 | TFS |

*(Sample corrected 2026-06-11: the earlier version of this table showed `TFS` in `ENROLL_COUNT_GIFTED` for school `0177`; the actual 2021 bronze value for 601/0177 is `29`. The genuine in-district TFS example is school `0277` — Appling County Primary — shown above; the 2021 file has 190 `TFS` cells in `ENROLL_COUNT_GIFTED` overall.)*

#### Statistics (Era 6 row counts)

| Year | School rows | District rows | State rows | Total | LONG_SCHOOL_YEAR |
|------|------------|---------------|-----------|-------|------------------|
| 2018 | 2,281 | 207 | 1 | 2,489 | 2017-18 |
| 2019 | 2,279 | 211 | 1 | 2,491 | 2018-19 |
| 2020 | 2,281 | 215 | 1 | 2,497 | 2019-20 |
| 2021 | 2,287 | 221 | 1 | 2,509 | 2020-21 |
| 2022 | 2,295 | 220 | 1 | 2,516 | 2021-22 |

#### Null Counts (Era 6)

Same program-not-offered null pattern as Era 5. Starting 2021, some of those former nulls are replaced with the literal `TFS` in the count columns (the `TFS` substitution is partial — some rows still have blank/null where the program truly does not apply).

#### Categorical Columns (2018)

| Column | Distinct Count | Notes |
|--------|---------------|-------|
| DETAIL_LVL_DESC | 3 | `District`, `School`, `State` |
| LONG_SCHOOL_YEAR | 1 | `2017-18` |
| SCHOOL_DSTRCT_NM | 214 | Includes `All Column Values` sentinel |
| INSTN_NAME | ~2,186 | Includes `All Column Values` sentinel |
| GRADES_SERVED_DESC | ~79 | |

#### Suppression Markers (Era 6)

| Column | Marker | Years | Meaning |
|--------|--------|-------|---------|
| INSTN_NUMBER | `ALL` | 2018–2022 | District or state row |
| SCHOOL_DSTRCT_CD | `ALL` | 2018–2022 | State row |
| ENROLL_COUNT_REMEDIAL_GR_6_8 | `TFS` | 2021, 2022 | Count suppressed (below threshold) |
| ENROLL_COUNT_EIP_K_5 | `TFS` | 2021, 2022 | Count suppressed |
| ENROLL_COUNT_REMEDIAL_GR_9_12 | `TFS` | 2021, 2022 | Count suppressed |
| ENROLL_COUNT_SPECIAL_ED_K12 | `TFS` | 2021, 2022 | Count suppressed |
| ENROLL_COUNT_ESOL | `TFS` | 2021, 2022 | Count suppressed |
| ENROLL_COUNT_SPECIAL_ED_PK | `TFS` | 2021, 2022 | Count suppressed |
| ENROLL_COUNT_VOCATION_9_12 | `TFS` | 2021, 2022 | Count suppressed |
| ENROLL_COUNT_ALT_PROGRAMS | `TFS` | 2021, 2022 | Count suppressed |
| ENROLL_COUNT_GIFTED | `TFS` | 2021, 2022 | Count suppressed |

For 2021 the `TFS` counts in `ENROLL_COUNT_ESOL` alone are **882 rows out of 2,509** — suppression is substantial. Matching percentage columns (e.g., `ENROLL_PCT_ESOL`) for those same rows remain numeric or blank (the value was not re-suppressed on the percentage side in Era 6).

### Era 7: 2023–2024 (CSV, 38 columns, `#RPT_NAME` header, `ENROLL_PERCENT_*` → `ENROLL_PCT_*`, TFS on percentages)

38 columns. Three major changes from Era 6:

1. **New leading column `#RPT_NAME`** with the constant value `Enrollment_by_Subgroup_Metrics`.
2. **Rename of 12 `ENROLL_PERCENT_*` columns to `ENROLL_PCT_*`** — Asian, Native, Black, Hispanic, Multiracial, White, Migrant, ED, SWD, LEP, Male, Female. **Program-enrollment `ENROLL_PERCENT_EIP_K_5` is NOT renamed** (it stays as `ENROLL_PERCENT_EIP_K_5` in Era 7 — the rename is inconsistent).
3. **Expanded `TFS` coverage.** In 2023–2024, `TFS` appears in **30 columns** — all 12 demographic/sex `ENROLL_PCT_*` columns (including `ENROLL_PCT_NATIVE`, `ENROLL_PCT_MULTIRACIAL`, and `ENROLL_PCT_MIGRANT`, which the prior report incorrectly marked as TFS-free in 2023), plus all 9 program `ENROLL_COUNT_*` columns and all 9 program `ENROLL_PCT_*`/`ENROLL_PERCENT_EIP_K_5` columns.

Also note: **column order changes** — the leading identifier group is reordered to `#RPT_NAME, LONG_SCHOOL_YEAR, DETAIL_LVL_DESC, SCHOOL_DSTRCT_CD, SCHOOL_DSTRCT_NM, INSTN_NUMBER, INSTN_NAME, GRADES_SERVED_DESC`. In earlier eras it was `DETAIL_LVL_DESC, INSTN_NUMBER, SCHOOL_DSTRCT_CD, LONG_SCHOOL_YEAR, INSTN_NAME, SCHOOL_DSTRCT_NM, GRADES_SERVED_DESC`. The transform must not rely on positional reads.

Full column list (2023–2024):

```
#RPT_NAME, LONG_SCHOOL_YEAR, DETAIL_LVL_DESC, SCHOOL_DSTRCT_CD, SCHOOL_DSTRCT_NM,
INSTN_NUMBER, INSTN_NAME, GRADES_SERVED_DESC,
ENROLL_PCT_ASIAN, ENROLL_PCT_NATIVE, ENROLL_PCT_BLACK, ENROLL_PCT_HISPANIC,
ENROLL_PCT_MULTIRACIAL, ENROLL_PCT_WHITE, ENROLL_PCT_MIGRANT, ENROLL_PCT_ED,
ENROLL_PCT_SWD, ENROLL_PCT_LEP,
ENROLL_COUNT_REMEDIAL_GR_6_8, ENROLL_PCT_REMEDIAL_GR_6_8,
ENROLL_COUNT_EIP_K_5, ENROLL_PERCENT_EIP_K_5,
ENROLL_COUNT_REMEDIAL_GR_9_12, ENROLL_PCT_REMEDIAL_GR_9_12,
ENROLL_COUNT_SPECIAL_ED_K12, ENROLL_PCT_SPECIAL_ED_K12,
ENROLL_COUNT_ESOL, ENROLL_PCT_ESOL,
ENROLL_COUNT_SPECIAL_ED_PK, ENROLL_PCT_SPECIAL_ED_PK,
ENROLL_COUNT_VOCATION_9_12, ENROLL_PCT_VOCATION_9_12,
ENROLL_COUNT_ALT_PROGRAMS, ENROLL_PCT_ALT_PROGRAMS,
ENROLL_COUNT_GIFTED, ENROLL_PCT_GIFTED,
ENROLL_PCT_MALE, ENROLL_PCT_FEMALE
```

#### Sample Data (2023)

| #RPT_NAME | LONG_SCHOOL_YEAR | DETAIL_LVL_DESC | SCHOOL_DSTRCT_CD | SCHOOL_DSTRCT_NM | INSTN_NUMBER | INSTN_NAME | GRADES_SERVED_DESC | ENROLL_PCT_ASIAN | ENROLL_PCT_NATIVE | ENROLL_PCT_MIGRANT | ENROLL_COUNT_GIFTED | ENROLL_PCT_GIFTED |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Enrollment_by_Subgroup_Metrics | 2022-23 | School | 652 | Elbert County | 0313 | Elbert County Elementary School | 02,03,04 | 1 | TFS | 1 | 57 | 8.7 |
| Enrollment_by_Subgroup_Metrics | 2022-23 | School | 741 | Troup County | 1052 | LaGrange High School | 09,10,11,12 | 2 | TFS | TFS | 194 | 14.9 |
| Enrollment_by_Subgroup_Metrics | 2022-23 | District | 601 | Appling County | ALL | All Column Values | PK,KK,01,02,03,04,05,06,07,08,09,10,11,12 | TFS | TFS | 7 | 196 | 6 |

#### Statistics (Era 7 row counts)

| Year | School rows | District rows | State rows | Total | LONG_SCHOOL_YEAR |
|------|------------|---------------|-----------|-------|------------------|
| 2023 | 2,295 | 210 | 1 | 2,506 | 2022-23 |
| 2024 | 2,304 | 218 | 1 | 2,523 | 2023-24 |

#### Null Counts (2023)

Nulls remain for program-not-offered rows (e.g., `ENROLL_COUNT_REMEDIAL_GR_6_8` has ~1,645 null rows — mostly elementary/high schools that do not run grade 6-8 remediation). Demographic percentage columns have 4 nulls each (corresponds to rows where the subgroup percentage was 0% and GOSA left blank rather than `0`).

#### Categorical Columns (2023)

| Column | Distinct Count | Notes |
|--------|---------------|-------|
| #RPT_NAME | 1 | `Enrollment_by_Subgroup_Metrics` |
| LONG_SCHOOL_YEAR | 1 | `2022-23` |
| DETAIL_LVL_DESC | 3 | `District`, `School`, `State` |
| SCHOOL_DSTRCT_NM | 227 | Includes `All Column Values` sentinel |
| INSTN_NAME | ~2,196 | Includes `All Column Values` sentinel |
| GRADES_SERVED_DESC | ~71 | |

#### Suppression Markers (Era 7)

2023 & 2024 — `TFS` appears in **all 30 metric columns**:

| Category | Columns | Years |
|----------|---------|-------|
| Geography sentinel | `SCHOOL_DSTRCT_CD`, `INSTN_NUMBER` (value `ALL`) | 2023, 2024 |
| Demographic % | `ENROLL_PCT_ASIAN`, `ENROLL_PCT_NATIVE`, `ENROLL_PCT_BLACK`, `ENROLL_PCT_HISPANIC`, `ENROLL_PCT_MULTIRACIAL`, `ENROLL_PCT_WHITE`, `ENROLL_PCT_MIGRANT`, `ENROLL_PCT_ED`, `ENROLL_PCT_SWD`, `ENROLL_PCT_LEP` | 2023, 2024 |
| Sex % | `ENROLL_PCT_MALE`, `ENROLL_PCT_FEMALE` | 2023, 2024 |
| Program counts | `ENROLL_COUNT_REMEDIAL_GR_6_8`, `ENROLL_COUNT_EIP_K_5`, `ENROLL_COUNT_REMEDIAL_GR_9_12`, `ENROLL_COUNT_SPECIAL_ED_K12`, `ENROLL_COUNT_ESOL`, `ENROLL_COUNT_SPECIAL_ED_PK`, `ENROLL_COUNT_VOCATION_9_12`, `ENROLL_COUNT_ALT_PROGRAMS`, `ENROLL_COUNT_GIFTED` | 2023, 2024 |
| Program % | `ENROLL_PCT_REMEDIAL_GR_6_8`, `ENROLL_PERCENT_EIP_K_5`, `ENROLL_PCT_REMEDIAL_GR_9_12`, `ENROLL_PCT_SPECIAL_ED_K12`, `ENROLL_PCT_ESOL`, `ENROLL_PCT_SPECIAL_ED_PK`, `ENROLL_PCT_VOCATION_9_12`, `ENROLL_PCT_ALT_PROGRAMS`, `ENROLL_PCT_GIFTED` | 2023, 2024 |

Counts of `TFS` rows in 2023 across selected columns: `ENROLL_PCT_ASIAN`=754, `ENROLL_PCT_NATIVE`=2,235, `ENROLL_PCT_MIGRANT`=2,183, `ENROLL_PCT_ED`=12, `ENROLL_PCT_MULTIRACIAL`=64. Suppression is massive for rare-group columns (`NATIVE`, `MIGRANT`).

## ETL Considerations

- **Severe column-name drift across 7 eras.** Any long-running union must go through a per-era column-mapping function. High-risk transitions:
  - 2004–2006 `ID` → 2007–2009 `SysSchoolID` → 2010 `SysSchoolID` (with abbreviated single-letter columns `A/B/H/N/U/W/L/ED/S` and lowercase friendly names) → 2011+ splits into separate `INSTN_NUMBER` and `SCHOOL_DSTRCT_CD`.
  - 2004–2009 `MultiracialPercentage of Enrollment` (no space after `Multiracial`) is a **real column name typo**. Normalize carefully — do not "clean" the header unless you do so identically in every era.
  - 2007 uses lowercase `level` in the Excel sheet name `School level`. Every other year of 2005–2008 uses `School Level`. Sheet-name lookup must be case-insensitive.
  - 2012–2017 drops sex columns (`ENROLL_PERCENT_MALE`/`_FEMALE`); 2011 and 2018+ have them. The gold fact table must allow these metrics to be null for missing years.
  - 2023–2024 rename the 12 demographic/sex percentage columns from `ENROLL_PERCENT_*` to `ENROLL_PCT_*`, but leave `ENROLL_PERCENT_EIP_K_5` **unchanged**. Do not apply a mechanical `_PERCENT_` → `_PCT_` substitution — that specific column is an exception in every era.
  - 2023–2024 reorder the leading identifier group and prepend `#RPT_NAME`. The leading `#` can confuse some CSV readers — use `infer_schema_length=0` and explicit column selection.
- **2006.csv is a mislabeled Excel file.** Detect via magic bytes (`D0 CF 11 E0` Composite Document header) and read with `xlrd`/`pl.read_excel` regardless of the `.csv` extension.
- **Detail level is derived, not uniform.**
  - 2004 CSV: parse `ID` — `ALL:ALL` → state, `*:ALL` → district, other → school.
  - 2005–2008: use the Excel sheet name (case-insensitive).
  - 2009, 2010: no state row. School vs district must be derived from `SysSchoolID` (`:ALL` suffix = district).
  - 2011–2024: use the `DETAIL_LVL_DESC` column directly (`State`/`District`/`School`); lower-case to `state`/`district`/`school`.
- **District/school codes must stay string, not integer.** District codes are 3 digits (`601`) or 7 digits (charter LEAs). School codes are 4 digits zero-padded (`0103`). Cast to `Utf8` on read (`infer_schema_length=0`) and `.str.zfill(3)` / `.str.zfill(4)` after stripping the `ALL` sentinel. Never let Polars infer them as integers.
- **`ALL` sentinels must be nulled before casting.**
  - `INSTN_NUMBER == 'ALL'` marks state and district rows — null out `school_code` for those rows.
  - `SCHOOL_DSTRCT_CD == 'ALL'` marks state rows — null out `district_code` for those rows.
  - `SCHOOL_DSTRCT_NM == 'All Column Values'` and `INSTN_NAME == 'All Column Values'` are the corresponding name sentinels; these names must NOT be carried into dimension tables (filter by `DETAIL_LVL_DESC` first).
- **Suppression sentinel rollout is time-dependent.** Replace `TFS` → null **before** casting numeric columns to `Float64`/`Int64`:
  - 2004–2020: no `TFS` — every numeric value is either a digit string or null.
  - 2021–2022: `TFS` appears in **all 9 program `ENROLL_COUNT_*` columns**. Percentages still numeric.
  - 2023–2024: `TFS` appears in all 30 metric columns (every demographic/sex percentage AND every program count AND every program percentage).
  The transform should apply `TFS → null` universally across all numeric columns regardless of year; the map is a no-op for years that don't contain `TFS`.
- **Percent values can exceed 100 — by far more than rounding in Era A (verified 2026-06-11).** 2010 has an `ED` max of 102 (district row, rounding artifact), but earlier Era A files go much higher: `ED` max is 121 in 2004 and **132 in 2008** (705:108 Mountain Creek Academy; also 101-102 at three other 2008 schools), and `SWD` max is **117 in 2004** (611:179 Butler Early Childhood Center). These occur at alternative/behavioral/early-childhood/state-special schools where the count of students served exceeds the October FTE snapshot denominator — real published GOSA values, not parse errors. Do not hard-cap at 100; treat the derived share as a ratio (may exceed 1.0 after /100), not a bounded proportion.
- **Duplicate rows exist in Era A (verified 2026-06-11).** 2004: one junk row (`ID='2'`, no colon, all other cells null) plus 109 byte-identical duplicate rows. 2009: 4 duplicate SysSchoolID groups (2 byte-identical; 2 differing only in the School Name/Grades dimension attributes). 2005-2008, 2010, and all of 2011-2024 have zero duplicate keys.
- **2022 mislabels two single-school charter district aggregates as School rows.** Districts `7830627` (State Charter Schools II - Atlanta SMART Academy) and `7830636` (Northwest Classical Academy) each have a row with `DETAIL_LVL_DESC='School'` but `INSTN_NUMBER='ALL'` / `INSTN_NAME='All Column Values'` — and no `District`-labeled row at all. These are the district aggregates (values duplicate the school row, as expected for a single-school district) and must be reclassified to district level. No other year 2011-2024 has this pattern.
- **`ENROLL_COUNT_ALT_PROGRAMS` is corrupted in 2011 and 2019 (verified 2026-06-11).** In exactly those two files GOSA published the alternative-programs count as the entity's TOTAL enrollment, not the alt-program subset, while `ENROLL_PCT_ALT_PROGRAMS` stayed correct. Evidence: the state row carries 1,533,435 (2011) and 1,602,163 (2019) versus 10k–33k in every other year 2012–2024; 61 district rows exceed 5,000 in each error year versus exactly 1 in every other year; school rows carry the school's own few-hundred enrollment with a tiny companion rate (e.g., 2011 601:0103 count=717, pct=2.9 — compare 2017's count=74, pct=7.5). The corruption reaches school level, so no absolute count threshold can isolate it; the companion rate separates the cases cleanly — bogus rows top out at pct 93.7 (2011) / 93.9 (2019), while genuine all-alternative entities (where count == enrollment is legitimately true) sit at pct >= 95. The `enrollment_program_participation` transform NULLs the 2011/2019 counts wherever the companion rate is < 95 or null and preserves the rate.
- **Era 5 null-vs-zero ambiguity for program columns.** In 2012–2017, `ENROLL_COUNT_REMEDIAL_GR_6_8` is null for schools that do not offer grade 6-8 remediation (elementary, high). This is "program not applicable," not a suppression. **Preserve null** — do not coerce to 0. Same pattern applies in Era 4 and Era 6.
- **Year derivation.**
  - 2011–2024: parse `LONG_SCHOOL_YEAR` `YYYY-YY` → 4-digit ending year (e.g., `2022-23` → `2023`). Matches filename year.
  - 2004–2010: no year column. Use the filename's year literal. Assume the filename represents the ending year of the school year (matching the 2011+ convention).
- **AYP columns are only meaningful for 2004–2010.** `Met AYP` and `Improvement Status` can be carried in gold as `fact_categorical` columns that are null for 2011+. Alternatively, restrict them to a companion fact table if the project prefers not to mix NCLB-era measures with the modern program-enrollment measures. Recommend the former (single fact with nulls) for simplicity.
- **Grades format drift.** `Grades` in 2004 is dash-range (`K-5`, `6-8`). 2005 uses quote-prefix ranges (`'PK-05`, `'01-05`). 2006, 2007, 2008 use comma-separated zero-padded with spaces (`09, 10, 11, 12`). 2010 keeps the spaces; 2011+ drops the spaces (`09,10,11,12`). This is **institutional metadata** about which grades the school offers — not a fact-level categorical. It belongs in the schools/districts dimension, not the fact table.
- **`#RPT_NAME` is Era-7 only and constant.** Drop immediately after reading so the common 37-column schema is preserved.
- **`ENROLL_PERCENT_EIP_K_5` never gets renamed to `ENROLL_PCT_EIP_K_5`.** When normalizing column names across eras, do not assume a mechanical `_PERCENT_` → `_PCT_` substitution — that specific one is an exception in Era 4 through Era 7.
- **Sex percentages (`MALE`, `FEMALE`) are partially available.** Present in 2011, absent 2012–2017, present 2018–2024 (renamed to `ENROLL_PCT_*` in 2023–2024). Null the columns for missing years rather than inventing values.
- **Percent scaling is consistently 0-100 across every era.** No era reports proportions as 0-1. This is important when joining with other GOSA topics that also use 0-100 scale.

## Gold Schema Classification

For each bronze column (unified across all eras), classify its role in the gold star schema:

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| #RPT_NAME | not_in_gold | — | 2023–2024 only; constant `Enrollment_by_Subgroup_Metrics` (no information) |
| LONG_SCHOOL_YEAR *(2011+)* / filename year *(2004-2010)* | fact_key | year | Convert `YYYY-YY` → ending 4-digit year as `pl.Int32`; for pre-2011 parse from filename |
| DETAIL_LVL_DESC *(2011+)* / sheet name *(2005-2008)* / `ID` or `SysSchoolID` pattern *(other pre-2011)* | not_in_gold | — | Implicit in the fact-table file name (`state.parquet` / `districts.parquet` / `schools.parquet`); used only to drive geography nulling |
| ID *(2004-2006)* / SysSchoolID *(2007-2010)* | not_in_gold | — | Superseded by separate `INSTN_NUMBER` and `SCHOOL_DSTRCT_CD` in Era 4+. The transform must split this concatenated identifier into its two parts for 2004-2010. |
| INSTN_NUMBER *(2011+)* | fact_key | school_code | Cast to `Utf8`, `.str.zfill(4)`; null when value is `ALL` or when row is state/district |
| SCHOOL_DSTRCT_CD *(2011+)* | fact_key | district_code | Cast to `Utf8`, `.str.zfill(3)`; null when value is `ALL` or when row is state |
| System Name *(2004-2010)* / SCHOOL_DSTRCT_NM *(2011+)* | dimension_attribute | — | `district_name` in `data/gold/education/_dimensions/districts.parquet` (title case); filter out `All Column Values` sentinel |
| School Name *(2004-2010)* / INSTN_NAME *(2011+)* | dimension_attribute | — | `school_name` in `data/gold/education/_dimensions/schools.parquet` (title case); filter out `All Column Values` sentinel |
| Grades *(2004-2010)* / GRADES_SERVED_DESC *(2011+)* | dimension_attribute | — | Grades served is institution metadata; lives in `schools.parquet` / `districts.parquet` (not the fact table). Not used to pin a fact row. |
| Met AYP *(2004-2010)* / ayp_status *(2010)* | fact_categorical | met_ayp | Lower-case `yes`/`no`/`n_a`; null for 2011+ |
| Improvement Status *(2004-2010)* / ni_status *(2010)* | fact_categorical | improvement_status | Preserve codes (`adeq`, `adeq_dnm`, `dist`, `ni`, `ni_ayp`) lower-cased; map the `.` sentinel and blanks to null; null for 2011+ |
| A *(2010)* / Asian Percentage of Enrollment *(2004-2009)* / ENROLL_PERCENT_ASIAN *(2011-2022)* / ENROLL_PCT_ASIAN *(2023-2024)* | fact_metric | pct_asian | `Float64`; replace `TFS` with null; 0-100 scale |
| B *(2010)* / Black Percentage of Enrollment *(2004-2009)* / ENROLL_PERCENT_BLACK *(2011-2022)* / ENROLL_PCT_BLACK *(2023-2024)* | fact_metric | pct_black | `Float64`; `TFS` → null; 0-100 |
| H *(2010)* / Hispanic Percentage of Enrollment *(2004-2009)* / ENROLL_PERCENT_HISPANIC / ENROLL_PCT_HISPANIC | fact_metric | pct_hispanic | `Float64`; `TFS` → null; 0-100 |
| N *(2010)* / Native American Percentage of Enrollment *(2004-2009)* / ENROLL_PERCENT_NATIVE / ENROLL_PCT_NATIVE | fact_metric | pct_native_american | `Float64`; `TFS` → null; 0-100 |
| U *(2010)* / MultiracialPercentage of Enrollment *(2004-2009, typo)* / ENROLL_PERCENT_MULTIRACIAL / ENROLL_PCT_MULTIRACIAL | fact_metric | pct_multiracial | `Float64`; `TFS` → null; 0-100 |
| W *(2010)* / White Percentage of Enrollment *(2004-2009)* / ENROLL_PERCENT_WHITE / ENROLL_PCT_WHITE | fact_metric | pct_white | `Float64`; `TFS` → null; 0-100 |
| ENROLL_PERCENT_MIGRANT *(2011-2022)* / ENROLL_PCT_MIGRANT *(2023-2024)* | fact_metric | pct_migrant | `Float64`; `TFS` → null; 0-100; null for 2004-2010 (no bronze source) |
| ED *(2010)* / Economically Disadvantaged Percentage of Enrollment *(2004-2009)* / ENROLL_PERCENT_ED / ENROLL_PCT_ED | fact_metric | pct_economically_disadvantaged | `Float64`; `TFS` → null; 0-100 (tolerate occasional >100 rounding) |
| S *(2010)* / With Disabilities Percentage of Enrollment *(2004-2009)* / ENROLL_PERCENT_SWD / ENROLL_PCT_SWD | fact_metric | pct_students_with_disabilities | `Float64`; `TFS` → null; 0-100 |
| L *(2010)* / Limited English Proficient Percentage of Enrollment *(2004-2009)* / ENROLL_PERCENT_LEP / ENROLL_PCT_LEP | fact_metric | pct_english_learners | `Float64`; `TFS` → null; 0-100. Use `english_learners` to match the newer "EL" nomenclature favored by other gosa topics. |
| ENROLL_PERCENT_MALE *(2011, 2018-2022)* / ENROLL_PCT_MALE *(2023-2024)* | fact_metric | pct_male | `Float64`; `TFS` → null; 0-100; null for 2004-2010 and 2012-2017 |
| ENROLL_PERCENT_FEMALE *(2011, 2018-2022)* / ENROLL_PCT_FEMALE *(2023-2024)* | fact_metric | pct_female | `Float64`; `TFS` → null; 0-100; null for 2004-2010 and 2012-2017 |
| ENROLL_COUNT_REMEDIAL_GR_6_8 *(2011+)* | fact_metric | count_remedial_gr_6_8 | `Int64` (or `Float64`); `TFS` → null; null for schools that do not offer grade 6-8 remediation (preserve null, do NOT coerce to 0); null for 2004-2010 |
| ENROLL_PCT_REMEDIAL_GR_6_8 *(2011+)* | fact_metric | pct_remedial_gr_6_8 | `Float64`; `TFS` → null; 0-100; null for 2004-2010 |
| ENROLL_COUNT_EIP_K_5 *(2011+)* | fact_metric | count_eip_k_5 | `Int64`; `TFS` → null; null for 2004-2010 |
| ENROLL_PERCENT_EIP_K_5 *(2011+)* **[note: never renamed to `PCT`]** | fact_metric | pct_eip_k_5 | `Float64`; `TFS` → null; 0-100 |
| ENROLL_COUNT_REMEDIAL_GR_9_12 *(2011+)* | fact_metric | count_remedial_gr_9_12 | `Int64`; `TFS` → null |
| ENROLL_PCT_REMEDIAL_GR_9_12 *(2011+)* | fact_metric | pct_remedial_gr_9_12 | `Float64`; `TFS` → null |
| ENROLL_COUNT_SPECIAL_ED_K12 *(2011+)* | fact_metric | count_special_ed_k_12 | `Int64`; `TFS` → null |
| ENROLL_PCT_SPECIAL_ED_K12 *(2011+)* | fact_metric | pct_special_ed_k_12 | `Float64`; `TFS` → null |
| ENROLL_COUNT_ESOL *(2011+)* | fact_metric | count_esol | `Int64`; `TFS` → null |
| ENROLL_PCT_ESOL *(2011+)* | fact_metric | pct_esol | `Float64`; `TFS` → null |
| ENROLL_COUNT_SPECIAL_ED_PK *(2011+)* | fact_metric | count_special_ed_pk | `Int64`; `TFS` → null |
| ENROLL_PCT_SPECIAL_ED_PK *(2011+)* | fact_metric | pct_special_ed_pk | `Float64`; `TFS` → null |
| ENROLL_COUNT_VOCATION_9_12 *(2011+)* | fact_metric | count_vocation_9_12 | `Int64`; `TFS` → null |
| ENROLL_PCT_VOCATION_9_12 *(2011+)* | fact_metric | pct_vocation_9_12 | `Float64`; `TFS` → null |
| ENROLL_COUNT_ALT_PROGRAMS *(2011+)* | fact_metric | count_alt_programs | `Int64`; `TFS` → null |
| ENROLL_PCT_ALT_PROGRAMS *(2011+)* | fact_metric | pct_alt_programs | `Float64`; `TFS` → null |
| ENROLL_COUNT_GIFTED *(2011+)* | fact_metric | count_gifted | `Int64`; `TFS` → null |
| ENROLL_PCT_GIFTED *(2011+)* | fact_metric | pct_gifted | `Float64`; `TFS` → null |

Note on fact structure: this topic has **no demographic breakdown** — every row is an "all students" aggregate, and the demographic information is expressed as separate percentage metrics (`pct_asian`, `pct_black`, etc.) within the same row. The gold fact table is one row per (year × geography), with no `demographic` column.
