# hope_eligible_graduates — Bronze Data Structure

## Overview

- Topic: hope_eligible_graduates
- Source: gosa
- Files: 21 files spanning 2004–2024
- Unreadable files: none (2005 file is delivered with a `.csv` extension but is actually a legacy Excel `.xls` binary; it is readable via `xlrd`)
- Year representation:
  - 2004–2008: Year is only in the filename (no `LONG_SCHOOL_YEAR` column). The 2008 Excel additionally carries integer `Data Year` / `Report Card Year` columns equal to 2008.
  - 2009–2024: Year is in a `LONG_SCHOOL_YEAR` column formatted as `YYYY-YY` (e.g., `2023-24`).
- Filename-to-data year offset:
  - 2004, 2006–2008: Filename year equals the spring graduation year represented in the data.
  - 2005: Filename is `2005` but the data column header is stale (`Number of 2004 Graduates`); numeric values differ from the 2004 file, so the data represents spring 2005 graduates — the header label is a leftover from the prior file.
  - 2009–2024: Filename year equals the end year of the `YYYY-YY` school year in the file (e.g., `2024.csv` carries `2023-24`, i.e., spring-2024 graduates).
- Detail levels: state, district, school (varies by era — see notes below).
- Percentage scale: 0–100 throughout (e.g., `50.75`, `42.758621`). Older eras generally report one decimal place; 2008–2024 report two to six decimal places depending on whether the source formatted or raw-divided the value.
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| hope_eligible_graduates_2004.csv | feaace1c5863e44b41dc494771dc82903da15390b50c41652f9d261904737fb9 |
| hope_eligible_graduates_2005.csv | 7858bffa2aef21ce761af1b20c333180ebd2d0ed98f617bf5d0a2fa353b90f86 |
| hope_eligible_graduates_2006.xls | 7b01b170e274c87dd7a8ab3b44a6e83faa267ee81cca6c45a6b0640acf505f0c |
| hope_eligible_graduates_2007.xls | 14ff8a4f99f9c04d2a50b56ed6cd26fb66453098f4c03248fb455f39f9fbd1a5 |
| hope_eligible_graduates_2008.xls | 4b307dacdffba3786c5d717243b5a007b2b25576f41ed3ee79e867a7bbec51d6 |
| hope_eligible_graduates_2009.xls | 1ecd9df3a775a571ba1174eac89d524e01ed7506fa36b4e3c1f9e45127ec6ecc |
| hope_eligible_graduates_2010.xls | 38c814dc020ce84a876d512b4ecbc2acdefee7ef2b175e816ab8835e64df8fe2 |
| hope_eligible_graduates_2011.csv | b0a028822a91495e483781becac39a7006a2492fd301154ed8851e5277db1ccf |
| hope_eligible_graduates_2012.csv | b5d41d0d5bdf2930aeec2ed5cc72f382d0ac1445cca0274c52079e97cecc0951 |
| hope_eligible_graduates_2013.csv | f51953e7689c6e9f16fc6442e3591d1390c990bd683bc95a654b02003ede2b50 |
| hope_eligible_graduates_2014.csv | 53ccc41e9501de742ad04af85acf1c038b899fde8e86b6a7995c1f1cf48009de |
| hope_eligible_graduates_2015.csv | 642f9d0b1ea715f30d273782222466e6559679220ee396b1b47d936bbc7c7877 |
| hope_eligible_graduates_2016.csv | fee8acb6d607b0064ac60a30682093f2386da67f0b4e7e8a07b2042db0260cb8 |
| hope_eligible_graduates_2017.csv | c92713b3dcdf0a0b185609b1b9b0e5a6499a369f685db5a76a74a6fad66ddec6 |
| hope_eligible_graduates_2018.csv | 035f6f00e36234b3ce745d392315d42dad8eaff48f11b2d48e02ad28e01280d7 |
| hope_eligible_graduates_2019.csv | ecbce10f6c385cc8f61a0cf5fe955cd4250150abb38622333e3feda69ea9e105 |
| hope_eligible_graduates_2020.csv | 701c0635ca99fe420997742c195bd2ceca33355ca9577704759d1701c92a1157 |
| hope_eligible_graduates_2021.csv | de80221f77fbf483e8077baadbb2fdc1232bab372b060ef42e3dfda0f55b37b5 |
| hope_eligible_graduates_2022.csv | e8c57c9400a4cb13cf658a2842334dd4d667cf27137076107940a1e4fb07046c |
| hope_eligible_graduates_2023.csv | 8c33838e5de64700d887a0575ee6fbc83b0f6b582526581c73897b5ed798d962 |
| hope_eligible_graduates_2024.csv | 4df19cc23f5d401952fe29a054190e0de45344da20050147a6b2a26856b49194 |

## Excel Sheet Structure

| File(s) | Sheets | Notes |
|---------|--------|-------|
| 2005 (`.csv` extension, but real format is legacy Excel `.xls` binary) | `Sheet1` (Data), `Sheet2` (empty), `Sheet3` (empty) | Use `Sheet1`; Sheet2/Sheet3 are empty placeholders. Must be read with `xlrd` — `pl.read_csv` fails on the OLE binary and `pl.read_excel` requires an `.xls` extension, so the cleanest path is `xlrd.open_workbook(path)`. |
| 2006 | `Hope` (Data) | Single data sheet. |
| 2007 | `Sheet1` (Data), `Sheet2` (empty), `Sheet3` (empty) | Use `Sheet1`; other two sheets are empty placeholders. |
| 2008 | `School Level` (Data), `System Level` (Summary/Pivot), `State Level` (Summary/Pivot) | School Level is the atomic grain (382 rows, one per school). System Level and State Level are pre-aggregated views that recompute as `GROUP BY system` and the single state total — transform should derive these itself from the school-level rows and ignore the other two sheets. |
| 2009 | `Export Worksheet` (Data), `SQL` (Metadata) | Use `Export Worksheet`. The `SQL` sheet contains the Oracle SQL that produced the export — useful context for understanding the data definition (confirms suppression rule: "when `Number_Of_Graduates <= 9` → null", output as `'TFS'`) but has no data rows. |
| 2010 | `Sheet1` (Data), `Sheet2` (empty), `Sheet3` (empty) | Use `Sheet1`. |

No file requires concatenating multiple data sheets — each era has exactly one data sheet (or one data sheet plus legend/empty sheets to skip).

## Summary

Dataset reports, per high school, the count of graduating seniors who met academic eligibility criteria for Georgia's HOPE scholarship program. The three metrics in every era are: (1) **number of graduates**, (2) **number HOPE-eligible**, and (3) **percent HOPE-eligible**. There are no demographic breakdowns, test scores, or subject-level splits — the grain is purely institution × year. A notable substantive break occurs at 2006 → 2007: 2004–2006 files report "Percent Eligible" of ~62% (state-level), while 2007 and later report ~38%. This is consistent with the HOPE eligibility methodology tightening in the late-2000s (Zell Miller-era reforms) rather than a data-processing artifact, and should be treated as a real definitional change, not a bug.

## Eras

### Era 1: 2023-2024 (CSV, schema with `#RPT_NAME` + `DETAIL_LVL_DESC`)

| Column | Description |
|--------|-------------|
| `#RPT_NAME` | Constant "HOPE Eligible" — report identifier (likely the GOSA DownloadableData report name). |
| `LONG_SCHOOL_YEAR` | School year in `YYYY-YY` format (e.g., `2023-24`). Single value per file. |
| `DETAIL_LVL_DESC` | Aggregation level: `STATE`, `DISTRICT`, or `SCHOOL`. |
| `SCHOOL_DISTRCT_CD` | GOSA district code (3-digit), zero-padded. `ALL` for state-level rows. |
| `SCHOOL_DSTRCT_NM` | District name (title case). `All Systems` for state-level rows. |
| `INSTN_NUMBER` | School institution number, usually 4 digits with leading zeros (e.g., `0103`). `ALL` for district- and state-level rows. |
| `INSTN_NAME` | School name (mixed case). `All Schools` for district- and state-level rows. |
| `NUMBER_OF_GRADUATES` | Count of regular high-school graduates. Stored as string because the column can carry the suppression marker `TFS`. |
| `HOPE_ELIGIBLE` | Count of those graduates who met HOPE academic eligibility. Stored as string due to `TFS` suppression. |
| `HOPE_ELIGIBLE_PCT` | Percent HOPE-eligible (0–100 scale, two decimals). Stored as string due to `TFS` suppression. |

#### Sample Data (2024 representative)

```
shape: (5, 10)
#RPT_NAME     LONG_SCHOOL_YEAR DETAIL_LVL_DESC SCHOOL_DISTRCT_CD SCHOOL_DSTRCT_NM INSTN_NUMBER INSTN_NAME               NUMBER_OF_GRADUATES HOPE_ELIGIBLE HOPE_ELIGIBLE_PCT
HOPE Eligible 2023-24          SCHOOL          748               Ware County      0195         Ware County High School  335                 170           50.75
HOPE Eligible 2023-24          DISTRICT        651               Effingham County ALL          All Schools              877                 373           42.53
HOPE Eligible 2023-24          DISTRICT        793               Vidalia City     ALL          All Schools              169                 95            56.21
HOPE Eligible 2023-24          SCHOOL          721               Richmond County  2056         Hephzibah High School    243                 68            27.98
HOPE Eligible 2023-24          DISTRICT        744               Union County     ALL          All Schools              229                 151           65.94
```

#### Statistics (2024)

All columns are stored as strings in Era 1; `describe()` therefore shows count/null_count only plus lexicographic min/max. Row count is 667 with 0 nulls across every column.

- `NUMBER_OF_GRADUATES`: 667 non-null values, lexicographic min = `10`, max = `TFS`.
- `HOPE_ELIGIBLE`: 667 non-null values, lexicographic min = `1004`, max = `TFS`.
- `HOPE_ELIGIBLE_PCT`: 667 non-null values, lexicographic min = `11.35`, max = `TFS`.
- `DETAIL_LVL_DESC` breakdown: 1 STATE + 196 DISTRICT + 470 SCHOOL (2024); 1 + 196 + 468 (2023).

#### Null Counts (2024)

All 10 columns have 0 nulls.

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| `#RPT_NAME` | Constant `HOPE Eligible` (1 distinct). |
| `LONG_SCHOOL_YEAR` | Single value per file (`2022-23` in 2023.csv, `2023-24` in 2024.csv). |
| `DETAIL_LVL_DESC` | `DISTRICT`, `SCHOOL`, `STATE` (3 distinct). |
| `SCHOOL_DSTRCT_NM` | 197 distinct (2024) — 196 districts plus the sentinel `All Systems`. |
| `INSTN_NAME` | 462 distinct (2024); includes the sentinel `All Schools` used on district and state rollup rows. |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| `SCHOOL_DISTRCT_CD` | `ALL` (on state rows; functions as a level marker, not suppression). |
| `INSTN_NUMBER` | `ALL` (on district/state rows; level marker, not suppression). |
| `NUMBER_OF_GRADUATES` | `TFS` (= "Too Few to Score/Student"; suppression when graduates ≤ 9). |
| `HOPE_ELIGIBLE` | `TFS`. |
| `HOPE_ELIGIBLE_PCT` | `TFS`. |

### Era 2: 2009, 2011–2022 (long-school-year schema, no `DETAIL_LVL_DESC` column)

This is a single schema shared by the 2009 Excel and every CSV from 2011 through 2022 inclusive. The year 2010 breaks contiguity with a different schema (see Era 3), so the era is listed as two ranges with identical columns rather than split into two eras.

| Column | Description |
|--------|-------------|
| `LONG_SCHOOL_YEAR` | School year `YYYY-YY`. Single value per file. |
| `SCHOOL_DISTRCT_CD` | GOSA district code (3 digits). `ALL` flags state rollup rows. |
| `SCHOOL_DSTRCT_NM` | District name. `All Systems` on state rollup rows. |
| `INSTN_NUMBER` | Institution number. Mostly 4-digit zero-padded in 2009, 2014, 2020–2022; unpadded 3–4 digit in 2011–2013, 2015–2019 (see ETL notes). `ALL` flags district / state rollup rows. |
| `INSTN_NAME` | School name. `All Schools` flags district / state rollup rows. |
| `NUMBER_OF_GRADUATES` | Count of regular graduates. Integer in most years; string-with-`TFS` in 2009, 2021, 2022. |
| `HOPE_ELIGIBLE` | Count HOPE-eligible. Integer in 2014, 2020; string-with-`TFS` in 2009, 2011–2013, 2015–2019, 2021, 2022. |
| `HOPE_ELIGIBLE_PCT` | Percent HOPE-eligible (0–100, two decimals). Float in most years; string-with-`TFS` in 2009, 2021, 2022. |

#### Sample Data (2022 representative)

```
shape: (5, 8)
LONG_SCHOOL_YEAR SCHOOL_DISTRCT_CD SCHOOL_DSTRCT_NM INSTN_NUMBER INSTN_NAME                    NUMBER_OF_GRADUATES HOPE_ELIGIBLE HOPE_ELIGIBLE_PCT
2021-22          747               Walton County    ALL          All Schools                   984                 514           52.24
2021-22          651               Effingham County 0390         Effingham County High School  393                 172           43.77
2021-22          799               State Schools    1894         Georgia Academy for the Blind TFS                 TFS           TFS
2021-22          721               Richmond County  2574         Westside High School          183                 46            25.14
2021-22          744               Union County     0101         Union County High School      212                 132           62.26
```

The 2009 representative (from the `Export Worksheet` sheet of the 2009 `.xls`) has 580 rows with `LONG_SCHOOL_YEAR = 2008-09` and an identical 8-column schema. The state rollup row is the single `ALL / All Systems / ALL / All Schools` row reporting 85,751 total graduates and 32,059 HOPE-eligible (37.39%).

#### Statistics

Row counts per year (all 8 columns present each year):

| Year | Rows | Year | Rows |
|------|------|------|------|
| 2009 | 580 | 2017 | 636 |
| 2011 | 602 | 2018 | 648 |
| 2012 | 610 | 2019 | 648 |
| 2013 | 616 | 2020 | 654 |
| 2014 | 618 | 2021 | 658 |
| 2015 | 630 | 2022 | 664 |
| 2016 | 630 | | |

State-level rollup is the row with `SCHOOL_DISTRCT_CD = 'ALL'`, `INSTN_NUMBER = 'ALL'`, `SCHOOL_DSTRCT_NM = 'All Systems'`, `INSTN_NAME = 'All Schools'`. Each district has one `INSTN_NUMBER = 'ALL'` row (district rollup). All remaining rows are school-level (one row per school).

In 2022, numeric summary over rows where all metrics parse as numbers:

- `NUMBER_OF_GRADUATES`: ranges from low tens for small schools to 119,530 for the state rollup.
- `HOPE_ELIGIBLE`: lexicographic min `1` because the column is stored as string; numeric min after casting is `0`.
- `HOPE_ELIGIBLE_PCT`: lexicographic min `.9` (leading dot, no leading zero — note the minor formatting quirk).

#### Null Counts

2009 and 2011–2022 all report 0 nulls across all 8 columns. No header-row or partial rows found in any file.

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| `LONG_SCHOOL_YEAR` | 1 value per file (format `YYYY-YY`). |
| `SCHOOL_DSTRCT_NM` | 180–196 distinct across years, always including the sentinel `All Systems`. District count grows over time as new charter systems are added. |
| `INSTN_NAME` | 390–462 distinct across years, always including the sentinel `All Schools`. |

#### Suppression Markers

| Column | Non-Numeric Values (years affected) |
|--------|-------------------------------------|
| `SCHOOL_DISTRCT_CD` | `ALL` (all years — level marker for state row, not suppression). |
| `INSTN_NUMBER` | `ALL` (all years — level marker for district/state rows, not suppression). |
| `NUMBER_OF_GRADUATES` | `TFS` in 2009, 2021, 2022 (not present in 2011–2020). |
| `HOPE_ELIGIBLE` | `TFS` in 2009, 2011–2013, 2015–2019, 2021, 2022 (not present in 2014, 2020). |
| `HOPE_ELIGIBLE_PCT` | `TFS` in 2009, 2021, 2022 (not present in 2011–2020). |

`TFS` means "Too Few to Score / Student count" — the 2009 Oracle SQL (visible on the SQL sheet of the 2009 `.xls`) confirms it is applied when `NUMBER_OF_GRADUATES <= 9`, nulling all three metrics and replacing them with the literal string `'TFS'` on export.

### Era 3: 2010 (`Sysschoolid` single-column-key schema)

| Column | Description |
|--------|-------------|
| `Sysschoolid` | Composite key `{district_code}:{school_code}`, e.g., `601:103`. Both halves become `ALL` at higher aggregation levels (district rollups are `{code}:ALL`; state rollup is `ALL:ALL`). |
| `System/School Name` | District name when `...:ALL`, school name otherwise. |
| `Number of Graduates` | Integer count of graduates. |
| `Number Eligible` | Integer count HOPE-eligible. |
| `Percent Eligible` | Float percent (0–100, one decimal). |

#### Sample Data (2010)

```
shape: (5, 5)
Sysschoolid System/School Name         Number of Graduates Number Eligible Percent Eligible
739:ALL     Towns County               305                 82              26.9
648:4050    Douglas County High School 402                 96              23.9
785:ALL     Rome City                  278                 134             48.2
715:102     Rockmart High School       130                 41              31.5
736:100     Bishop Hall Charter School 42                  12              28.6
```

State row (sole `ALL:ALL`): `State of Georgia, 89851, 34285, 38.2`.

#### Statistics

576 rows: 1 state + 180 district rollups + 395 school rows. All metrics native-numeric (no suppression markers applied in 2010); `describe()` reports max = 89,851 for `Number of Graduates` (the `ALL:ALL` row), mean ≈ 467 (inflated by inclusion of the state total), state percent eligible = 38.2.

#### Null Counts

0 nulls across all 5 columns.

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| `Sysschoolid` | 576 distinct (unique per row: 395 school IDs + 180 `{code}:ALL` district rollups + 1 `ALL:ALL` state). |
| `System/School Name` | 569 distinct (some schools share names across districts). |

#### Suppression Markers

None — 2010 reports raw integers and floats with no `TFS` or other suppression sentinel.

### Era 4: 2008 (Report Card multi-sheet format)

2008 uniquely uses the GOSA Report Card export schema, with three pre-aggregated sheets. Only the `School Level` sheet is atomic.

| Column (School Level sheet) | Description |
|-----------------------------|-------------|
| `Data Year` | Integer 2008. |
| `Report Card Year` | Integer 2008. |
| `Data Type` | Constant `HOPE`. |
| `Report Card Section` | Constant `Indicators`. |
| `System ID` | Integer district code (not zero-padded). |
| `School ID` | School code; MIXED numeric/text cells (corrected 2026-06-11) — numeric cells surface unpadded (`103`) via an all-string read, text cells keep padding (`0105`). Normalize with `zfill(4)`. |
| `System Name` | District name. |
| `School Name` | School name (ALL CAPS). |
| `# Eligible for HOPE 2008` | Integer count HOPE-eligible. |
| `Number of Regular Graduates - Report Card` | Integer count of graduates. |
| `Percent Eligible` | Float percent (0–100, six decimals). |

`System Level` sheet adds `Total Graduates` and `% Eligible` (district rollup, 179 rows). `State Level` sheet has the single state row. Because the School Level rows sum exactly to the higher aggregates, the transform should derive the district and state rollups itself and ignore the other two sheets.

#### Sample Data (2008 School Level)

```
Data Year Report Card Year Data Type Report Card Section System ID School ID System Name     School Name                   # Eligible for HOPE 2008 Number of Regular Graduates - Report Card Percent Eligible
2008      2008             HOPE      Indicators          601       103       Appling County  APPLING COUNTY HIGH SCHOOL    62                       145                                       42.758621
2008      2008             HOPE      Indicators          602       103       Atkinson County ATKINSON COUNTY HIGH SCHOOL   24                       65                                        36.923077
2008      2008             HOPE      Indicators          603       302       Bacon County    BACON COUNTY HIGH SCHOOL      29                       85                                        34.117647
```

State rollup (from `State Level` sheet): 31,443 HOPE-eligible / 81,569 graduates = 38.547733%.

#### Statistics

`School Level` sheet: 382 rows. `# Eligible for HOPE 2008` mean ≈ 82, max 443; `Number of Regular Graduates` mean ≈ 214, max 735; `Percent Eligible` mean ≈ 35.6, max 100.0.

#### Null Counts (School Level)

5 rows total have null `School ID` (corrected 2026-06-11 — measured, not 5+1): 4 are alternative campuses / evening schools with a valid `System ID` (Carver Comprehensive and D M Therrell in 761, Fayette County Evening High in 656, Houston Co Crossroads Center in 676; together 226 graduates / 42 eligible), and 1 (`RENAISSANCE ACADEMY`) has nulls across `System ID`, `School ID`, and `System Name` — its `Percent Eligible` is a real `0` (28 graduates / 0 eligible), not null. Separately, exactly one row has a null `Percent Eligible`: `REGIONAL EVENING SCHOOL` (678/0193), which has 0 graduates (division-by-zero cell left blank) and a valid `School ID`. The transform must decide whether to drop the null-id rows, map them to an "unknown school" placeholder, or attach them to the parent district.

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| `Data Type` | `HOPE` (1). |
| `Report Card Section` | `Indicators` (1). |
| `System Name` (School Level) | 179 distinct + 1 null. |
| `School Name` (School Level) | 382 distinct (ALL CAPS). |

#### Suppression Markers

None — metrics are native Int64/Float64. A `Percent Eligible = 0.0` appears in genuine zero-count rows (e.g., `RENAISSANCE ACADEMY` with 28 graduates and 0 eligible). These are real zeros, not suppression.

### Era 5: 2007 (`SYSSCHOOLID` + `SchoolNme` schema)

| Column | Description |
|--------|-------------|
| `SYSSCHOOLID` | Composite `{district_code}:{school_code}`. `{code}:ALL` = district rollup. `ALL:ALL` = state rollup. |
| `SchoolNme` | District name at rollup; school name otherwise. |
| `Number of Graduates` | Integer. |
| `Number Eligible` | Integer. |
| `Percent Eligible` | Float (0–100, one decimal). |

#### Sample Data (2007)

```
shape: (5, 5)
SYSSCHOOLID SchoolNme                   Number of Graduates Number Eligible Percent Eligible
738:ALL     Toombs County               144                 35              24.3
649:2050    Early County High School    148                 48              32.4
791:301     Trion High School           87                  37              42.5
715:102     Rockmart High School        154                 47              30.5
735:105     Terrell Middle High School  54                  12              22.2
```

State row: `ALL:ALL, State of Georgia, 77737, 29617, 38.1`.

#### Statistics

544 rows. Metrics native-numeric.

#### Null Counts

0 across all 5 columns.

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| `SYSSCHOOLID` | 544 (unique). |
| `SchoolNme` | 537. |

#### Suppression Markers

None.

### Era 6: 2006 (`SysSchoolID` + `School Name` schema)

Same shape as Era 5, but the column names are `SysSchoolID` (different casing) and `School Name` (with a space).

| Column | Description |
|--------|-------------|
| `SysSchoolID` | Composite `{district_code}:{school_code}`; `{code}:ALL` and `ALL:ALL` mark rollups. |
| `School Name` | District name at rollup, school name otherwise. |
| `Number of Graduates` | Integer. |
| `Number Eligible` | Integer. |
| `Percent Eligible` | Float (0–100, one decimal). |

#### Sample Data (2006)

```
shape: (5, 5)
SysSchoolID School Name                 Number of Graduates Number Eligible Percent Eligible
739:204     Towns County High School    60                  43              71.7
648:4050    Douglas County High School  202                 97              48.0
789:4052    Thomasville High School     115                 64              55.7
715:ALL     Polk County                 355                 172             48.5
735:105     Terrell Middle High School  61                  35              57.4
```

State row: `ALL:ALL, State of Georgia, 74059, 45731, 61.7`. The **state percent eligible ≈ 62%** is much higher than later years — see Summary / ETL Considerations; this reflects the pre-2008 HOPE eligibility definition.

#### Statistics

528 rows. Metrics native-numeric. State mean percent eligible ≈ 58%.

#### Null Counts

0 across all 5 columns.

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| `SysSchoolID` | 528 (unique). |
| `School Name` | 522. |

#### Suppression Markers

None.

### Era 7: 2004–2005 (`SYSSCHOOLID` + `SchoolNme` + stale "Number of 2004 Graduates" column)

2004 and 2005 share an identical set of column names (including the 2004-specific header `Number of 2004 Graduates`, which is not updated in the 2005 file). 2004 is delivered as a regular CSV; 2005 is delivered with a `.csv` extension but is actually a legacy Excel `.xls` binary and must be opened via `xlrd`.

| Column | Description |
|--------|-------------|
| `SYSSCHOOLID` | Composite `{district_code}:{school_code}`. 2004 has only school + state (`ALL:ALL`), no district rollup rows. 2005 has school + district (`{code}:ALL`) + state. |
| `SchoolNme` | District name at rollup, school name otherwise. 2004 has one row where `SchoolNme` (and all metrics) are null and `SYSSCHOOLID` is a long null-byte-padded string — a trailing blank/footer row. |
| `Number of 2004 Graduates` | Integer count of graduates. The header label is literally `Number of 2004 Graduates` in BOTH files; in the 2005 file this is a stale label — the actual values differ from the 2004 file and represent the 2005 graduating cohort. |
| `Number Eligible` | Integer count HOPE-eligible. |
| `Percent Eligible` | Float percent (0–100, one decimal). |

#### Sample Data

2004:

```
SYSSCHOOLID SchoolNme                    Number of 2004 Graduates Number Eligible Percent Eligible
736:100     The School at Bishop Hall    23                       3               13.0
644:775     Open Campus High School      535                      129             24.1
786:300     Social Circle High School    72                       36              50.0
712:198     Pickens County High School   184                      122             66.3
732:194     Tattnall County High School  107                      28              26.2
```

State row (2004): `ALL:ALL, State of Georgia, 68163, 42233, 62.0`.

2005:

```
SYSSCHOOLID SchoolNme                          Number of 2004 Graduates Number Eligible Percent Eligible
739:204     Towns County High School           70                       53              75.7
648:187     Alexander High School              267                      185             69.3
789:4052    Thomasville High School            145                      78              53.8
715:102     Rockmart High School               125                      60              48.0
735:4050    Terrell County Middle/High School  51                       34              66.7
```

State row (2005): `ALL:ALL, State Of Georgia, 70504, 43080, 61.1`. Note `State Of Georgia` uses title-case `Of` in 2005 vs. `State of Georgia` in 2004.

#### Statistics

| Year | Rows | Shape notes |
|------|------|-------------|
| 2004 | 348 | 1 state + 346 school rows + 1 junk/footer row (all fields null except `SYSSCHOOLID` which is a null-byte-padded empty string). No district rollup rows. |
| 2005 | 528 | 1 state + 175 district rollups (`{code}:ALL`) + 352 school rows. (Corrected 2026-06-11: previously listed as 181 + 346; measured split is 175 rollups / 352 schools — every school's district has a rollup row.) |

#### Null Counts

- 2004: 1 row with nulls in `SchoolNme`, `Number of 2004 Graduates`, `Number Eligible`, `Percent Eligible` (the junk/footer row).
- 2005: 0 nulls.

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| `SYSSCHOOLID` | 2004: 348 (includes the junk row); 2005: 528 (unique). |
| `SchoolNme` | 2004: 346 + 1 null + state row; 2005: 519 distinct. |

#### Suppression Markers

None — metrics are native-numeric in both years.

## ETL Considerations

1. **2005 file encoding.** `hope_eligible_graduates_2005.csv` is misnamed: it is a legacy Excel `.xls` binary (OLE compound file, magic bytes `D0 CF 11 E0`), not CSV. `pl.read_csv` fails with a UTF-8 error and `pl.read_excel` rejects the `.csv` extension. Read it with `xlrd.open_workbook(...)` and treat `Sheet1` as the data sheet. Build the Polars DataFrame from the `xlrd` cell values and explicitly cast numeric columns (`Number of 2004 Graduates`, `Number Eligible` to Int64; `Percent Eligible` to Float64).
2. **Stale `Number of 2004 Graduates` header in 2005.** The 2005 file reuses the 2004 column header. Year assignment must come from the filename, not the column name. When renaming to the standard metric column, drop the `2004` — the 2005 data represents the 2005 spring graduating class (confirmed by differing per-school values between the 2004 and 2005 files).
3. **2004 footer/junk row.** `hope_eligible_graduates_2004.csv` contains one trailing row where `SYSSCHOOLID` is a very long null-byte-padded empty string and every other column is null. Drop rows where `SchoolNme` (and the three metrics) are all null, or equivalently where `SYSSCHOOLID` contains the NUL character.
4. **Filename year = spring graduation year (all eras).** Use the filename year as the canonical `year` assignment for the fact table. For Era 2 files (2009, 2011–2022) the `LONG_SCHOOL_YEAR` column records the school year as `YYYY-YY` — assert that its end year equals the filename year as a sanity check, then drop the column in gold.
5. **Composite `SYSSCHOOLID` / `Sysschoolid` / `SysSchoolID` key in Eras 3, 5, 6, 7.** The pre-2008 and 2010 files use a single string `{district_code}:{school_code}` for the key. Split on `:` into `district_code` and `instn_number`. The sentinel `ALL` on either side marks a rollup row. Transform should produce `{district_code, instn_number}` columns that match Era 2 / Era 1 naming, preserving `ALL` as a signal for district/state rollups during cleaning and then explicitly classifying each row as state / district / school based on where `ALL` appears.
6. **District code zero-padding.** GOSA district codes are 3-digit integers (601, 602, ...). They appear:
    - Zero-padded strings (`601`) in Eras 1, 2, 3, 5, 6, 7.
    - Integer (`601`) in Era 4 (2008 `System ID` is Int64).
    Normalize to zero-padded 3-digit strings in gold.
7. **`INSTN_NUMBER` zero-padding (Era 2).** 2009, 2014, 2020, 2021, 2022 deliver `INSTN_NUMBER` with 4-digit zero-padding (`0103`), but 2011, 2012, 2013, 2015, 2016, 2017, 2018, 2019 deliver it without padding (`103`, `2050`, etc.). Normalize all years to consistent padding (likely 4-digit zero-padded strings) to allow joins across years to the schools dimension.
8. **`School ID` zero-padding (Era 4).** (Corrected 2026-06-11.) The 2008 `School ID` cells are MIXED types in the raw workbook: most are numeric cells (xlrd ctype 2, e.g. `103.0`) that surface as unpadded strings (`103`) through the all-string reader, while a minority are text cells that preserve zero-padding (`0105`, `0193`). Apply `zfill(4)` after the all-string read — do not assume the column arrives uniformly padded.
9. **Detail level derivation.**
   - Era 1 (2023–2024): use `DETAIL_LVL_DESC` directly (values `STATE`, `DISTRICT`, `SCHOOL`).
   - Era 2 (2009, 2011–2022), Era 4 (2008), and Era 3 (2010): derive level from sentinels. In Era 2/3, row is STATE iff `district_code == 'ALL'`, DISTRICT iff `district_code != 'ALL'` and `instn_number == 'ALL'`, SCHOOL otherwise. In Era 4 it is atomic school-level only; district and state must be derived by aggregation.
   - Eras 5, 6, 7: same sentinel logic against the split composite key.
   - Era 8 (2004): no district rollups exist in the source — if gold expects district aggregates for 2004, derive them via SUM.
10. **`TFS` suppression marker (Era 2 and Era 1).** Convert `TFS` → null when parsing `NUMBER_OF_GRADUATES`, `HOPE_ELIGIBLE`, `HOPE_ELIGIBLE_PCT` for 2009, 2011–2013, 2015–2019, 2021, 2022, 2023, 2024. The 2009 source SQL confirms `TFS` is applied when `NUMBER_OF_GRADUATES <= 9`. The pre-2008 eras and 2010 have no suppression markers at all.
11. **Real-zero rows in 2008.** `Percent Eligible = 0.0` is legitimate in 2008 (e.g., `RENAISSANCE ACADEMY` with 28 graduates and 0 eligible). Do not mistake these for missing data.
12. **2008 null-id rows.** (Corrected 2026-06-11.) Five rows in the 2008 School Level sheet have null `School ID`, four of which still have a valid `System ID` / `System Name` / `School Name`. One row (`RENAISSANCE ACADEMY`) has nulls in System ID, School ID, and System Name. Decide per-row whether to attach to a district via name match or drop. The four valid-district rows contribute 22+19+0+1 = 42 eligible and 93+123+3+7 = 226 graduates; Renaissance adds 28 graduates / 0 eligible but is excluded from the bronze State Level total (81,569 / 31,443), so folding the four into district/state aggregates and dropping Renaissance reproduces the official totals exactly.
13. **Pre-2007 definition change.** Percent eligible ≈ 62% in 2004–2006 but drops to ≈ 38% in 2007 and stays in the 37–50% range through 2024. This is a substantive definitional change in the HOPE program (tightening of GPA / course requirements), not a data-processing artifact. Do not correct it; note it in gold metadata so downstream users are aware of the series break.
14. **Skip pre-aggregated sheets in the 2008 file.** The `System Level` and `State Level` sheets are exact aggregations of the `School Level` sheet (verified by matching the state rollup total 31,443 / 81,569 / 38.55%). Reading only `School Level` and computing aggregates keeps the transform era-uniform.
15. **Skip the `SQL` sheet in the 2009 file.** It is Oracle SQL source, not data. Keep as documentation only.
16. **Percent scale is uniform (0–100).** Every era reports percent as 0–100, with one-decimal rounding in older years and two-to-six decimal precision in 2008+. Preserve the value as-is if the gold schema expects 0–100; divide by 100 if the gold schema expects 0–1.
17. **District-name drift / casing.** `State of Georgia` (2004, 2006, 2010) vs `State Of Georgia` (2005) vs `All Systems` (2008+). The sentinel text differs; do not rely on it for level classification — use the code/number sentinels instead.
18. **Row-count sanity check.** Expected state-level graduate counts: ~68K (2004), ~71K (2005), ~74K (2006), ~78K (2007), ~82K (2008), ~86K (2009), ~90K (2010), ~120K (2024). Numbers should grow gradually with population; a jump or drop >10% year-over-year (outside 2004→2008) likely indicates a data issue.
19. **`#RPT_NAME` and `DETAIL_LVL_DESC` (Era 1) should not leak into gold.** `#RPT_NAME` is a constant report label; `DETAIL_LVL_DESC` should be folded into the gold `detail_level` enum (after normalizing the sentinel derivation logic from other eras to match). Neither column needs to land in gold as-is.

## Gold Schema Classification

Applied across all eras; columns that only exist in certain eras are aligned to the standard names.

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| `#RPT_NAME` (Era 1) | not_in_gold | — | Constant `HOPE Eligible` — report label only. |
| `LONG_SCHOOL_YEAR` (Eras 1, 2) | not_in_gold | — | Redundant once filename year is assigned to `year`. Use for sanity-check only. |
| `Data Year`, `Report Card Year` (Era 4) | not_in_gold | — | Constant 2008; filename year wins. |
| `Data Type`, `Report Card Section` (Era 4) | not_in_gold | — | Constants (`HOPE`, `Indicators`). |
| `DETAIL_LVL_DESC` (Era 1) | fact_categorical | `detail_level` | Values STATE / DISTRICT / SCHOOL. For other eras, derive from `ALL` sentinels on district/institution keys (or, in Era 4, from the School-Level-only grain + aggregation). |
| `SCHOOL_DISTRCT_CD` / `System ID` / first half of `SYSSCHOOLID` / first half of `Sysschoolid` / first half of `SysSchoolID` | fact_key | `district_code` | Zero-padded 3-digit string; `ALL` is replaced with the state-rollup handling done in the `detail_level` classification. FK to the districts dimension. |
| `SCHOOL_DSTRCT_NM` / `System Name` / `SchoolNme` when row is a district rollup | dimension_attribute | — | `district_name` lives in the districts dimension only. |
| `INSTN_NUMBER` / `School ID` / second half of `SYSSCHOOLID` / second half of `Sysschoolid` / second half of `SysSchoolID` | fact_key | `instn_number` | Zero-padded 4-digit string; `ALL` removed after detail-level classification. FK to the schools dimension. |
| `INSTN_NAME` / `School Name` / `SchoolNme` when row is a school | dimension_attribute | — | `school_name` lives in the schools dimension only. |
| `NUMBER_OF_GRADUATES` / `Number of Graduates` / `Number of 2004 Graduates` / `Total Graduates` / `Number of Regular Graduates - Report Card` | fact_metric | `graduate_count` | Int64 after `TFS` → null. |
| `HOPE_ELIGIBLE` / `Number Eligible` / `# Eligible for HOPE 2008` | fact_metric | `hope_eligible_count` | Int64 after `TFS` → null. |
| `HOPE_ELIGIBLE_PCT` / `Percent Eligible` / `% Eligible` | fact_metric | `hope_eligible_pct` | Float64 after `TFS` → null; scale 0–100 preserved. |
| `SYSSCHOOLID` / `Sysschoolid` / `SysSchoolID` (as a whole) | not_in_gold | — | Composite key is split into `district_code` + `instn_number` (see above); the composite itself is not retained. |
