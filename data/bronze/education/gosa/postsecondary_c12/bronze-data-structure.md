# postsecondary_c12_report — Bronze Data Structure

## Overview

- Topic: postsecondary_c12_report
- Source: gosa
- Files: 13 files spanning 2012-2024 (publication years); covers HS graduate cohorts 2008-2020
- Unreadable files: none
- Year representation: All files carry a `School Year` / `SCHOOL_YEAR` column that holds a **single** integer (e.g., `2008`, `2016`, `2019`) representing the high school graduating-class year the metrics describe. Filenames use the **publication year**, which is consistently `data year + 4` (the C12 report tracks postsecondary outcomes 4 years after HS graduation — enrollment into college and completion of 24 credit hours within 2 years of enrollment). Era 3 (2023-2024) CSVs add a separate `#REPORTING_YEAR` header column that matches the filename year. `SCHOOL_YEAR` in Era 3 is stored as a float (`2019.00000`, `2020.00000`) — it must be cast to int.
- Filename-to-data year offset: filename year = `School Year` + 4 (consistent across every file)
- Detail levels: state (`All Systems` / `ALL`), district (`School Code` = `ALL`), and school (every other row). No grade-level detail.
- Percentage scale: not applicable. Every metric is a **count** of students (HS graduates, graduates enrolled in college, graduates who earned ≥24 credits within 2 years of enrollment).
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| postsecondary_c_12_report_2012.xlsx | d2cb16bdc81ea5148214178e2df1d16ed07c5d53d3d96081c75a2ae3a8d3935b |
| postsecondary_c_12_report_2013.xlsx | 6ffe32ac49d60be965d9e23833ee8cef166b8ee46dba603cbb37f8b0ec3ccdcd |
| postsecondary_c_12_report_2014.xlsx | 8d70100fe851be888660361123212802c2d6dea9fdff42fd7ff9e58678b1a2f7 |
| postsecondary_c_12_report_2015.xlsx | ff6cf6afa6628ae0c543454a08a3f10799a638c626a829b3ed61ea2bc3de591a |
| postsecondary_c_12_report_2016.xlsx | 4fe38ac5dd9f5076dd3dc4b55ca303b9b70747d9e28e825b0c9ced401124e821 |
| postsecondary_c_12_report_2017.xlsx | ff0bdebac4ab99573ec7508aea9b72e9a7b58e7b4476eee731c731af2dde4e4e |
| postsecondary_c_12_report_2018.xlsx | 9c6aeff71b203a7ebe2a882b63fd8d62686d212e815d94510a97735e149fd2d1 |
| postsecondary_c_12_report_2019.xlsx | 70c16773426170b6cde2f156783de7582fdd07aa7c4a5258c947e0f4275dd070 |
| postsecondary_c_12_report_2020.xlsx | 9d201ed4f40c202c776556b6c470a9e504c2cfb3b5a25e4b37aca5d6d7cf6e7c |
| postsecondary_c_12_report_2021.xlsx | 70e6bdd5171142bf5fbb491a6e142d3917e2a47cca430d54fdf20806d7b249b1 |
| postsecondary_c_12_report_2022.xlsx | 2c369fa3aca4e7fa83f03bf140ddea85668902b47896dc8cee0283c821912b14 |
| postsecondary_c_12_report_2023.csv | 06793637a54ff6b12c4236958b401abe5fa8ba4cfd7e645b8c94dca222327aa6 |
| postsecondary_c_12_report_2024.csv | 64860b580cf4be34823ad3da61f1cd36f5b49d4b5833bb5c28ecf9b85ee342d5 |

## Excel Sheet Structure

| File(s) | Sheets | Notes |
|---------|--------|-------|
| 2012.xlsx | `C12 Report for 2007-08 HS Grads` (Data), `Sheet1` (Metadata) | `Sheet1` lists column labels only (no data rows); ignore during transform. |
| 2013.xlsx, 2014.xlsx, 2021.xlsx, 2022.xlsx | `Export Worksheet` (Data) | Single data sheet. |
| 2015.xlsx, 2016.xlsx, 2017.xlsx, 2018.xlsx, 2019.xlsx | `C12_FY{YYYY}_HS Graduates {YYYY}_En` (Data) | Single data sheet; sheet name encodes fiscal/publication year and graduating-class year (e.g., 2015 file sheet is `C12_FY2015_HS Graduates 2011_En`). |
| 2020.xlsx | `Export Worksheet` (Data), `SQL` (Metadata) | `SQL` sheet contains the generating Oracle SQL query that defines how suppression is applied (`CASE WHEN {metric} < 10 THEN 'TFS' ELSE TO_CHAR({metric}) END`) and how demographic counts are computed; useful reference but not for the transform. |

All Excel files share the same **three-row header structure** on the data sheet:

- Row 0: Free-text note — `"TFS stands for Too Few Students"` in cell A1.
- Row 1: Demographic group headers (sparse / merged) — labels appear only above the first of three metric columns per group: `Total All`, `Male`, `Female`, `Free Reduced Lunch`, `Migrant`, `LEP`, `Disability`, `Hispanic`, `Two or More Race(s)`, `American Indian or Alaskan Native`, `Asian`, `Black`, `White`, `Pacific Islander` (Pacific Islander absent in 2012).
- Row 2: Metric column headers (repeated per demographic group) — the five identifier columns (`School Year`, `School District Code`, `School District Name`, `School Code`, `School Name`) followed by 13 or 14 demographic groups × 3 metrics (`Total High School Graduates`, `Number of High School Graduates Enrolled in Postsecondary Institution`, `Number that Completed 1yr of Credit within 2 Years of Enrollment`).
- Row 3+: Data rows.

The transform must **skip rows 0-1** and treat **row 2 as the header**; because row 2 contains duplicate metric names across the 13/14 demographic groups, the transform also needs to **forward-fill the row-1 demographic labels across the metric columns** and synthesize combined column names (e.g., `male__in_college`) before reading rows, otherwise polars `read_excel` will auto-suffix duplicates with `_1`, `_2`, etc.

## Summary

This dataset reports the **Career and College (C12) Ready / Postsecondary Report** for Georgia public high schools — three raw student counts per demographic subgroup, measured at three points along the high-school-graduate-to-postsecondary pipeline:

1. **Total High School Graduates** (`TOTAL_HS_GRADS`) — number of students who graduated high school in a given cohort year.
2. **Number of High School Graduates Enrolled in Postsecondary Institution** (`TOTAL_ENROLLED_IN_COLLEGE`) — of those graduates, how many enrolled in a **Georgia** postsecondary institution (2-year or 4-year). Unlike the sibling C11 report, C12 enrollment counts cover **Georgia institutions only**, not out-of-state enrollment: for the 2016 HS cohort the C11 state row reports 71,095 enrolled vs. C12's 57,468, while the two reports' graduate counts agree (103,947 vs. 103,950) — the gap is out-of-state enrollment that C11 captures and C12 does not.
3. **Number that Completed 1yr of Credit within 2 Years of Enrollment** (`TOTAL_EARNED_24CREDITS`) — of those graduates, how many accumulated at least 24 credit hours of postsecondary coursework within two years of initial enrollment (a rough "persistence / college-readiness" signal).

Each metric is reported separately for 14 demographic subgroups (13 in 2012): Total All, Male, Female, Free Reduced Lunch, Migrant, LEP (Limited English Proficiency), Disability / SWD (Students with Disabilities), Hispanic, Two or More Races, American Indian / Alaskan Native, Asian, Black, White, and Pacific Islander. The bronze layout is **wide** (one row per school-year-entity, 39 or 42 metric columns); the gold transform should **unpivot** it into a tidy `(year, district_code, school_code, demographic) × 3-metric` fact layout. No percentages or derived rates are computed in the bronze data — consumers can derive college-going rate or credit-earning rate by dividing the enrolled/earned counts by the HS graduate count.

## Eras

### Era 1: 2012 (HS grads 2008)

Single file at the start of the series; missing the `Pacific Islander` demographic group that every later file carries. 39 metric columns = 13 subgroups × 3 metrics.

| Column | Description |
|--------|-------------|
| School Year | HS graduating class year (integer, e.g., `2008`). Single value per file. |
| School District Code | 3-digit Georgia school-system code as **string** (e.g., `601`). State-total row uses literal `ALL`. |
| School District Name | District proper-name (e.g., `Appling County`). State-total row is `All Systems`. |
| School Code | 4-character school code as **string** with leading zeros preserved (e.g., `0103`). District-total rows use literal `ALL`. |
| School Name | School proper-name. District-total rows use `All Schools`. |
| `{demographic}__hs_grads` | Count of HS graduates in the subgroup. Stored as string because cells with fewer than 10 students are replaced with `TFS` (Too Few Students). |
| `{demographic}__in_college` | Count of graduates who enrolled in a postsecondary institution. Same storage / suppression pattern. |
| `{demographic}__earned_24credits` | Count of graduates who earned ≥24 credit hours within 2 years of initial postsecondary enrollment. Same storage / suppression pattern. |

Demographics present in Era 1 (13): `total_all`, `male`, `female`, `frl`, `migrant`, `lep`, `swd` (Disability), `hispanic`, `twoormore` (Two or More Race(s)), `native` (American Indian or Alaskan Native), `asian`, `black`, `white`. (Pacific Islander is **missing**.)

#### Sample Data

Selected columns from 5 random rows of `postsecondary_c_12_report_2012.xlsx`:

```
shape: (5, 12)
┌────────────┬─────────────┬─────────────┬────────────┬─────────────────────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐
│ School Yr  │ Dist Code   │ Dist Name   │ School Cd  │ School Name             │ totall  │ totall  │ totall  │ male    │ female  │ black   │ white   │
│                                                                                │ _grads  │ _coll   │ _cred   │ _grads  │ _grads  │ _grads  │ _grads  │
╞════════════╪═════════════╪═════════════╪════════════╪═════════════════════════╪═════════╪═════════╪═════════╪═════════╪═════════╪═════════╪═════════╡
│ 2008       │ 740         │ Treutlen    │ 3050       │ Treutlen Middle/High    │ 67      │ 36      │ 28      │ 31      │ 36      │ 31      │ 34      │
│ 2008       │ 648         │ Douglas     │ ALL        │ All Schools             │ 1562    │ 761     │ 459     │ 772     │ 790     │ 685     │ 745     │
│ 2008       │ 791         │ Trion City  │ ALL        │ All Schools             │ 87      │ 50      │ 31      │ 44      │ 43      │ TFS     │ 82      │
│ 2008       │ 715         │ Polk County │ 0102       │ Rockmart High School    │ 158     │ 76      │ 41      │ 81      │ 77      │ 22      │ 129     │
│ 2008       │ 736         │ Thomas Cty  │ 0100       │ Bishop Hall Charter Sch │ 33      │ 14      │ TFS     │ TFS     │ 25      │ 14      │ 15      │
└────────────┴─────────────┴─────────────┴────────────┴─────────────────────────┴─────────┴─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘
```

#### Statistics

- Rows: 574
- Columns: 44 (5 identifiers + 39 metrics; 13 demographics × 3 metrics)
- Single `School Year` value: 2008
- Distinct districts: 181 (plus 1 All Systems row)
- State-total row: `School District Code='ALL'`, `School District Name='All Systems'`, `School Code='ALL'`
- District-total rows: `School Code='ALL'` (181 rows — one per district)
- School rows: 393 (non-`ALL` School Code)

#### Null Counts

All 44 columns have **0** null values. Missing/suppressed data is encoded as the literal string `TFS`, not as null.

#### Categorical Columns

| Column | Distinct Values / Pattern |
|--------|---------------------------|
| School Year | `[2008]` — constant per file. |
| School District Code | 181 distinct district codes (3-digit, zero-padded strings in `601`–`793` range) + literal `ALL` for the state total row. |
| School District Name | 181 district names + `All Systems`. |
| School Code | 4-character school codes (`0100` to `5566`) + `ALL` (district totals). |
| School Name | 388 distinct school/aggregate names. |

#### Suppression Markers

Every metric column (all 39) uses **`TFS`** as the sole non-numeric value. `TFS` stands for **Too Few Students** (confirmed by the A1 note cell and the SQL generator seen in the 2020 file's `SQL` sheet: `CASE WHEN {metric} < 10 THEN 'TFS' ELSE TO_CHAR({metric}) END`). Total `TFS` occurrences across all metric columns: **12,357**.

| Column | Non-Numeric Values |
|--------|-------------------|
| All 39 metric columns (`total_all__hs_grads` through `white__earned_24credits`) | `['TFS']` |

---

### Era 2: 2013-2022 (HS grads 2009-2018)

Ten files with the **same logical column set** (5 IDs + 14 demographics × 3 metrics = 47 columns). Adds Pacific Islander relative to Era 1. The only per-file differences are:

- Sheet name (`Export Worksheet` for 2013, 2014, 2020, 2021, 2022; `C12_FY{YYYY}_HS Graduates {YYYY}_En` for 2015-2019)
- 2015-2019 files store `School District Code` as **integer** (no leading-zero padding) and `School Code` as a string but **without leading zeros** (e.g., `103` rather than `0103`); the state-total row's District Code cell holds the literal `ALL` in the source (confirmed via string-typed reads, `dtype=str`, across all five files) — it only appears as **null** when the column is read with integer coercion (e.g., polars type inference), which is a read artifact, not a blank source cell. All other files store both codes as zero-padded strings and likewise use `ALL` for aggregate rows.

| Column | Description |
|--------|-------------|
| School Year | HS graduating class year (integer). Single value per file (2009 → 2018 across the 10 files). |
| School District Code | 3-digit Georgia school-system code. String with leading zeros in 2013-2014 and 2020-2022; **integer** in 2015-2019. State-total row: literal `ALL` in every file (in 2015-2019 it surfaces as null only under integer-coerced reads). |
| School District Name | District proper-name. State-total row is `All Systems`. |
| School Code | 4-character school code as string. 2013-2014 and 2020-2022 preserve leading zeros (`0103`); 2015-2019 strip them (`103`). District-total rows: literal `ALL`. |
| School Name | School proper-name. District-total rows: `All Schools`. |
| `{demographic}__hs_grads` | HS graduate count per subgroup. String with `TFS` for <10. |
| `{demographic}__in_college` | Enrolled-in-college count per subgroup. Same encoding. |
| `{demographic}__earned_24credits` | Earned-24-credits count per subgroup. Same encoding. |

Demographics present in Era 2 (14): `total_all`, `male`, `female`, `frl`, `migrant`, `lep`, `swd`, `hispanic`, `twoormore`, `native`, `asian`, `black`, `white`, `pacific` (Pacific Islander, added starting 2013).

#### Sample Data

Selected columns from 5 random rows of `postsecondary_c_12_report_2020.xlsx` (HS grads 2016):

```
shape: (5, 12)
┌─────────┬──────────┬──────────────────┬────────┬─────────────────────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐
│ Sch Yr  │ Dist Cd  │ Dist Name        │ Sch Cd │ School Name             │ totall  │ totall  │ totall  │ male    │ female  │ pacific │ native  │
│                                                                          │ _grads  │ _coll   │ _cred   │ _grads  │ _grads  │ _grads  │ _grads  │
╞═════════╪══════════╪══════════════════╪════════╪═════════════════════════╪═════════╪═════════╪═════════╪═════════╪═════════╪═════════╪═════════╡
│ 2016    │ 742      │ Turner County    │ ALL    │ All Schools             │ 96      │ 47      │ 27      │ 39      │ 57      │ TFS     │ TFS     │
│ 2016    │ 650      │ Echols County    │ 1050   │ Echols County High Sch  │ 56      │ 24      │ 21      │ 30      │ 26      │ TFS     │ TFS     │
│ 2016    │ 786      │ Social Circle    │ ALL    │ All Schools             │ 109     │ 53      │ 30      │ 63      │ 46      │ TFS     │ TFS     │
│ 2016    │ 719      │ Rabun County     │ 0177   │ Rabun County High Sch   │ 147     │ 88      │ 58      │ 73      │ 74      │ TFS     │ TFS     │
│ 2016    │ 739      │ Towns County     │ 0204   │ Towns County High Sch   │ 68      │ 39      │ 23      │ 37      │ 31      │ TFS     │ TFS     │
└─────────┴──────────┴──────────────────┴────────┴─────────────────────────┴─────────┴─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘
```

#### Statistics

- Row count ranges from 577 (2013) to 647 (2022) — slight growth as new charter/state schools are added.
- Columns: 47 (5 identifiers + 42 metrics; 14 demographics × 3 metrics).
- Single `School Year` value per file: 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018 for 2013→2022 files respectively.
- Representative 2020 file: 626 rows, 187 districts, 1 All Systems row, 187 district-total rows (`School Code = ALL`), 439 school-level rows.
- Representative 2020 file metric ranges (after numeric cast, ignoring `TFS`): `total_all__hs_grads` min=10, max=103,950 (state total); `total_all__earned_24credits` min=10, max=40,318.

#### Null Counts

- 2013-2014, 2020-2022 Excel files: all columns have **0** nulls (suppression uses `TFS`; cells are string).
- 2015-2019 Excel files: `School District Code` shows **1 null** under polars integer coercion (the All Systems row, whose source cell holds the literal `ALL` that cannot be cast to int); under a string-typed read (`dtype=str`) the cell is `ALL` and the column has **0** nulls. All other columns 0 null.

#### Categorical Columns

| Column | Distinct Values / Pattern |
|--------|---------------------------|
| School Year | Single integer per file (`2009`-`2018`); use year from the data (not the filename). |
| School District Code | 181-188 distinct codes per file. Encoding differs by year: string `601`/`ALL` (2013-2014, 2020-2022) vs. integer-typed `601` (2015-2019 — the state row's literal `ALL` coerces to null under integer reads but is `ALL` in the source). |
| School District Name | 181-188 distinct district names + `All Systems`. |
| School Code | 4-character codes, zero-padded in 2013-2014/2020-2022, **unpadded** in 2015-2019. District-total rows: `ALL`. |
| School Name | 400-445 distinct school/aggregate names. |

#### Suppression Markers

Every metric column (42) uses **`TFS`** as the sole non-numeric value. Representative 2020 file TFS occurrences across metric columns: **14,439**.

| Column | Non-Numeric Values |
|--------|-------------------|
| All 42 metric columns (`total_all__hs_grads` through `pacific__earned_24credits`) | `['TFS']` |

---

### Era 3: 2023-2024 (HS grads 2019-2020)

Two CSV files with a flattened, snake-case column schema (no multi-row header). Adds an explicit `#REPORTING_YEAR` column that matches the filename year. 48 columns total (6 identifiers + 14 demographics × 3 metrics).

| Column | Description |
|--------|-------------|
| `#REPORTING_YEAR` | Publication year (equals filename year: `2023` or `2024`). First character `#` is a CSV comment-style marker from the exporter; transform should strip it when building the column list. |
| SCHOOL_YEAR | HS graduating class year, stored as **float** with decimals (`2019.00000`, `2020.00000`). Cast to int in transform. |
| SCHOOL_DISTRCT_CD | 3-digit system code as zero-padded string (e.g., `601`). State-total row: literal `ALL`. |
| SCHOOL_DSTRCT_NM | District name. State-total row: `All Systems`. |
| INSTN_NUMBER | 4-character school code as zero-padded string (e.g., `0103`). District-total rows: literal `ALL`. |
| INSTN_NAME | School name. District-total rows: `All Schools`. |
| TOTAL_HS_GRADS / TOTAL_ENROLLED_IN_COLLEGE / TOTAL_EARNED_24CREDITS | Counts for the "Total All" subgroup. |
| MALE_* / FEMALE_* | Gender counts (3 metrics each). |
| FRL_* / MIGRANT_* / LEP_* / SWD_* | Program counts (3 metrics each). |
| HISPANIC_* / TWOORMORE_* / NATIVE_* / ASIAN_* / BLACK_* / WHITE_* / PACIFIC_* | Race/ethnicity counts (3 metrics each). |

All 42 metric columns are quoted strings in the CSV, using `TFS` for suppression.

#### Sample Data

Selected columns from 5 random rows of `postsecondary_c_12_report_2023.csv`:

```
shape: (5, 12)
┌──────────┬──────────┬──────────┬──────────────────┬──────────┬──────────────────────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐
│ REPORT_Y │ SCHOOL_Y │ DIST_CD  │ DIST_NM          │ INSTN_NUM│ INSTN_NAME               │ TOTAL   │ TOTAL   │ TOTAL   │ MALE    │ BLACK   │ PACIFIC │
│                                                                                         │ HS_GRADS│ IN_COLL │ 24CREDS │ HS_GRADS│ HS_GRADS│ HS_GRADS│
╞══════════╪══════════╪══════════╪══════════════════╪══════════╪══════════════════════════╪═════════╪═════════╪═════════╪═════════╪═════════╪═════════╡
│ 2023     │ 2019.0   │ 625      │ Savannah-Chatham │ 3056     │ Groves High School       │ 165     │ 49      │ 15      │ 74      │ 128     │ TFS     │
│ 2023     │ 2019.0   │ 644      │ DeKalb County    │ 4069     │ Towers High School       │ 156     │ 46      │ 21      │ 68      │ 144     │ TFS     │
│ 2023     │ 2019.0   │ 755      │ Whitfield County │ 0112     │ Coahulla Creek HS        │ 195     │ 114     │ 67      │ 104     │ TFS     │ TFS     │
│ 2023     │ 2019.0   │ 706      │ Muscogee County  │ 5052     │ Carver High School       │ 238     │ 81      │ 41      │ 105     │ 226     │ TFS     │
│ 2023     │ 2019.0   │ 721      │ Richmond County  │ 0213     │ Richmond Co Tech Career  │ 73      │ 46      │ 25      │ 38      │ 54      │ TFS     │
└──────────┴──────────┴──────────┴──────────────────┴──────────┴──────────────────────────┴─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘
```

#### Statistics

- 2023 file: 646 rows; 2024 file: 649 rows.
- Columns: 48 (6 identifiers + 42 metrics).
- Each file holds exactly **one** `SCHOOL_YEAR` value: `2019.0` in 2023 file, `2020.0` in 2024 file.
- Representative 2023 file: 191 districts, 1 All Systems row, 191 district-total rows, 455 school-level rows.

#### Null Counts

All 48 columns have **0** nulls in both files. Missing/suppressed values are encoded as `TFS`.

#### Categorical Columns

| Column | Distinct Values / Pattern |
|--------|---------------------------|
| #REPORTING_YEAR | `[2023]` (2023 file), `[2024]` (2024 file). |
| SCHOOL_YEAR | `[2019.0]` (2023 file), `[2020.0]` (2024 file). |
| SCHOOL_DISTRCT_CD | 3-digit zero-padded strings; 190-191 distinct codes + `ALL`. |
| SCHOOL_DSTRCT_NM | 190-191 distinct names + `All Systems`. |
| INSTN_NUMBER | 4-character zero-padded strings; 199-207 distinct + `ALL`. |
| INSTN_NAME | ~450 distinct names (including aggregates). |

#### Suppression Markers

Every one of the 42 metric columns uses **`TFS`** as the sole non-numeric value. Representative 2023 file TFS occurrences: **15,060**; 2024 file: **15,437**.

| Column | Non-Numeric Values |
|--------|-------------------|
| All 42 metric columns (`TOTAL_HS_GRADS` through `PACIFIC_EARNED_24CREDITS`) | `['TFS']` |

## ETL Considerations

1. **Wide-to-long unpivot is required.** The bronze layout is wide: one row per `(school_year, district, school)` with 39 or 42 metric columns encoding 13 or 14 demographic subgroups × 3 metrics. The gold fact table should unpivot this into `(year, district_code, school_code, demographic)` rows with three metric columns (`hs_grads`, `enrolled_in_college`, `earned_24_credits`) — or similar. Demographic names must be normalized to the global demographics dimension (`All Students`, `Male`, `Female`, `Free Reduced Lunch`, `Migrant`, `LEP`, `SWD`, `Hispanic`, `Two or More Races`, `American Indian or Alaskan Native`, `Asian`, `Black`, `White`, `Pacific Islander`).

2. **Three-row Excel header (Eras 1-2).** `pl.read_excel(...)` with defaults produces garbled column names because row 0 is a free-text note and row 1 carries merged-cell demographic labels. The transform must read the first 3 rows via `openpyxl`, forward-fill the row-1 demographic labels across metric columns, concatenate with row-2 metric names to produce 39/42 unique combined column names, then re-read the sheet with `has_header=False, read_options={"skip_rows": 3, "column_names": <synthesized_list>}`. The combined-name synthesis itself must also hard-code the correct demographic list (Era 1 lacks Pacific Islander).

3. **Era 1 (2012) lacks Pacific Islander.** The transform must tolerate the missing subgroup and leave its metrics unobserved for that year (or equivalently, produce only 13 subgroup rows × 3 metrics when unpivoting that year). Do **not** pad Era 1 with empty "Pacific Islander" rows — it will mislead consumers into thinking Pacific Islander counts of 0 were observed when they were simply not collected.

4. **Filename year ≠ data year.** Always use `School Year` / `SCHOOL_YEAR` from the data (which represents the HS graduating-class year) as the partition key for gold, **not** the filename year. The filename year is the publication year (HS grad year + 4). For CSVs, `SCHOOL_YEAR` is a float — cast to int (or i16) before emitting.

5. **District / school code encoding shifts across years.** Eras 1, late-Era-2 (2013-2014, 2020-2022), and Era 3 store both `School District Code` and `School Code` as zero-padded strings (`601`, `0103`). Mid-Era-2 files (2015-2019) store District Code as **integer** (`601`) and School Code as **unpadded string** (`103`). The transform must (a) cast District Code to string and zero-pad (Georgia district codes are 3 digits; the standard in other gosa topics is 3-digit `str`), and (b) zero-pad School Code to 4 digits. Verify that a 4-digit padded school code from 2015-2019 matches the zero-padded code seen in the same school's row in earlier/later files.

6. **Aggregate-row encoding is uniform in the source — but watch integer coercion.** All eras (including 2015-2019) use `School Code = 'ALL'` for district totals and `District Code = 'ALL'` / `District Name = 'All Systems'` for the state total — verified via string-typed reads (`dtype=str`) of all five 2015-2019 files. However, if the transform lets polars infer the 2015-2019 `School District Code` column as integer, the state row's `ALL` coerces to **null** (a read artifact). Read the code columns as strings so `District Code == 'ALL'` works everywhere; as a safety net, detail-level detection may also accept `District Code is null and District Name == 'All Systems'` as the state-total condition. `School Code == 'ALL'` identifies district-level aggregate rows.

7. **`TFS` suppression marker on every metric column.** Across all eras every metric is stored as a string and uses the literal `TFS` ("Too Few Students" — cell count <10) as the sole non-numeric value. The transform must cast every metric to numeric with `strict=False` (mapping `TFS` → null) and preserve the suppression signal separately if the gold schema needs to distinguish suppressed-vs-absent (e.g., via an `is_suppressed` boolean).

8. **No implicit zero-filling.** `TFS` means "between 1 and 9 students" — not zero. Treat `TFS` cells as **null** in gold (not zero), and do not impute.

9. **Row-count integrity.** Both district-total rows (`School Code='ALL'`) and per-school rows coexist in the same bronze file. When unpivoting, preserve both — but flag them with a `detail_level` column (`state`, `district`, `school`) so consumers can filter. A district-total row is **not** the sum of its school rows (counts <10 are aggregated into the district total without suppression, but the same cells are suppressed on per-school rows).

10. **Sheet / CSV quirks:**
    - 2012 file's secondary `Sheet1` is a column-label dump — ignore it.
    - 2020 file's `SQL` sheet contains the generating Oracle query; useful as documentation (confirms `TFS` threshold is `<10`) but not as data.
    - Era 3 CSVs begin with `#REPORTING_YEAR` — the `#` is part of the raw CSV header; strip it before using the column.

11. **Total All vs. subgroup sums.** `Total All` is not always equal to `Male + Female` or to the sum of race/ethnicity categories — due to suppression and to students whose subgroup was unknown. Do not derive `Total All` from summing subgroups; always use the source `Total All` column.

## Gold Schema Classification

The gold fact table should be one row per `(year, district_code, school_code, demographic)` with three metric columns, sourced from an unpivot of the 39/42 metric columns in bronze.

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| School Year / SCHOOL_YEAR | fact_key | year | Cast to int16. Partition key. |
| School District Code / SCHOOL_DISTRCT_CD | fact_key | district_code | Zero-padded string (3 digits). FK to districts dimension. Map `'ALL'` → state-total row (null appears only under integer-coerced reads of 2015-2019 files). Cast 2015-2019 integer codes to zero-padded strings. |
| School District Name / SCHOOL_DSTRCT_NM | dimension_attribute | — | `district_name` lives in districts dimension. |
| School Code / INSTN_NUMBER | fact_key | school_code | Zero-padded 4-digit string. FK to schools dimension. `'ALL'` → district-total row. Zero-pad the 2015-2019 unpadded values. |
| School Name / INSTN_NAME | dimension_attribute | — | `school_name` lives in schools dimension. |
| (demographic-group component of each metric column, e.g. `Male`, `Hispanic`) | fact_key | demographic | FK to demographics dimension. Emitted via unpivot; normalize labels to global demographics catalog. |
| (derived from School Code / School District Code) | fact_categorical | detail_level | Enum: `state` (District Code == 'ALL' or null), `district` (School Code == 'ALL' and District is set), `school` (both are real codes). |
| `{demo}__hs_grads` / `{DEMO}_HS_GRADS` | fact_metric | hs_grads | Int count. Cast with strict=False; `TFS` → null. |
| `{demo}__in_college` / `{DEMO}_IN_COLLEGE` / `TOTAL_ENROLLED_IN_COLLEGE` | fact_metric | enrolled_in_college | Int count. `TFS` → null. |
| `{demo}__earned_24credits` / `{DEMO}_EARNED_24CREDITS` / `TOTAL_EARNED_24CREDITS` | fact_metric | earned_24_credits | Int count. `TFS` → null. |
| (implicit, from `TFS` presence) | fact_categorical | is_suppressed | Optional. Bool / int derived column flagging cells whose original value was `TFS`. Consumers may prefer to read this alongside the null metric. |
| #REPORTING_YEAR (Era 3 only) | not_in_gold | — | Publication year — redundant with `year + 4`. Not needed in gold. |
| Row 0 TFS note cell (Eras 1-2) | not_in_gold | — | Metadata header only. |
| Sheet1 metadata (2012), SQL sheet (2020) | not_in_gold | — | Not data — skip entirely. |

**Gold roles:**
- `fact_key` — Foreign key column retained in the fact table
- `fact_metric` — Numeric measurement (count, score, rate) in the fact table
- `fact_categorical` — Topic-specific categorical column in the fact table (e.g., detail_level)
- `dimension_attribute` — Descriptive attribute stored in a dimension table, NOT in the fact table
- `not_in_gold` — Column excluded from gold entirely
