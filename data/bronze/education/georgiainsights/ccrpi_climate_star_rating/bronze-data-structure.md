# ccrpi_climate_star_rating - Bronze Data Structure

## Overview

- Topic: ccrpi_climate_star_rating
- Source: georgiainsights
- Files: 7 files spanning 2014-2019 + 2024 (large gap: no 2020-2023 files)
- Unreadable files: none
- Year representation: `Year` column (2014-2018) or `School Year` column (2019, 2024). Each file contains a single year. Stored as Int64 in most files; stored as String in the 2014 and 2017 files.
- Filename-to-data year offset: usually same. Exception: `CCRPI Score and School Climate Star Rating 04.14.15.xlsx` has a 2015 publication date in its filename but contains 2014 data (per its in-file `Year` column).
- Detail levels: school only (no state or district aggregate rows present)
- Percentage scale: not applicable. Metrics are CCRPI Single Score (nominally 0-100; the 2014-2017 bonus-point methodology produced values up to ~110, with the cap tightened in 2018+ — not a percentage) and School Climate Star Rating (1-5 ordinal star rating).
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: Georgia Insights (GaDOE) public data downloads — exact page URL not recorded at acquisition time
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| 2015 School Climate Star Ratings and CCRPI scores.xlsx | 15527764851e191cf42c91e2b5fe9819de23ff6cff9947283570c337472e7b96 |
| 2016 Star Rating_CCRP 1.26.17I.xlsx | 5407066d8038ff2d2285b9f7760dbdf78aa8c985f512aaa8c07eb40b0c7091e2 |
| 2017 CCRPI School Climate Star Rating 11.2.17.xlsx | c68054ed49a5967917ba30f8dc4d4af60f96f9e5905d533faaa307968c8958a7 |
| 2018 CCRPI School Climate Star Rating_10_29_18.xlsx | 25f7d49f3623312f102d65d37036d9ed698013f778a6d6f136cd6f23c6385071 |
| 2019 School Climate Star Rating_11_26_19.xls | b59d7668da4cdbf9963804222bae0522d861657b2bec0d9d92ec515bdd7b7421 |
| 2024 School Climate Star Rating.xlsx | 49b6f65a99f5a36fcb77783337261ce3e4c9b654259064a3cee96740065feefa |
| CCRPI Score and School Climate Star Rating 04.14.15.xlsx | fa2d244b71b016cc33a70af14a988b27038ae79130d61c0822a582becfa5c413 |

## Excel Sheet Structure

| File(s) | Sheets | Notes |
|---------|--------|-------|
| 2014 (`...04.14.15.xlsx`), 2015, 2016 | Sheet1 (Data) | Single data sheet with default name |
| 2017 | 2017_StarRatings (Data) | Single data sheet, custom name |
| 2018, 2019, 2024 | Star_Rating_Data_File (Data) | Single data sheet, consistent name |

All files have a single sheet — no metadata or summary sheets to skip, and no need to concatenate multiple sheets per file.

## Summary

This dataset reports two CCRPI (College and Career Ready Performance Index) metrics at the Georgia public school level: the **CCRPI Single Score** (a nominally 0-100 composite school accountability score combining content mastery, progress, closing gaps, readiness, and graduation rate components; the 2014-2017 bonus-point methodology produced values up to ~110, with the cap tightened in 2018+) and the **School Climate Star Rating** (a 1-5 ordinal rating reflecting school climate based on student/teacher/parent surveys, attendance, and discipline data). The 2024 file drops the CCRPI Single Score column (climate star rating only), so post-2019 data is single-metric.

## Eras

### Era 1: 2014-2018

**Files**: `CCRPI Score and School Climate Star Rating 04.14.15.xlsx` (2014 data), `2015 School Climate Star Ratings and CCRPI scores.xlsx`, `2016 Star Rating_CCRP 1.26.17I.xlsx`, `2017 CCRPI School Climate Star Rating 11.2.17.xlsx`, `2018 CCRPI School Climate Star Rating_10_29_18.xlsx`

**Columns**: `Year`, `System ID`, `System Name`, `School ID`, `School Name`, `CCRPI Single Score`, `School Climate Star Rating`

| Column | Description |
|--------|-------------|
| Year | Single integer year (e.g., 2018). Stored as Int64 in 2015, 2016, 2018 files; stored as String in 2014 and 2017 files. |
| System ID | District code (e.g., "601" for Appling County, "7820108" for State Charter Schools). 7-digit codes are charter/state-school operators. Stored as Int64 in some files (2015, 2016, 2018) and String in others (2014, 2017). |
| System Name | District name (e.g., "Appling County", "DeKalb County", "State Charter Schools- ..."). |
| School ID | School code (e.g., "0103"). Always 4-digit zero-padded String in this era. |
| School Name | School name (e.g., "Appling County High School"). |
| CCRPI Single Score | Composite CCRPI score, nominally 0-100 but with 2014-2017 bonus-point methodology pushing some values up to ~110 (cap tightened in 2018+). Float64 in all Era 1 files. May contain true nulls (e.g., 89 nulls in 2017, 33 in 2018). |
| School Climate Star Rating | Star rating, integer 1-5. May contain nulls (e.g., 42 nulls in 2018) for schools that did not receive a rating. |

#### Sample Data (2018)

```
shape: (5, 7)
| Year | System ID | System Name                    | School ID | School Name                     | CCRPI Single Score | School Climate Star Rating |
| 2018 | 729       | Sumter County                  | 0190      | Sumter County Middle School     | 68.4               | 1                          |
| 2018 | 644       | DeKalb County                  | 2061      | McLendon Elementary School      | 80.9               | 3                          |
| 2018 | 891       | Department of Juvenile Justice | 0104      | Atlanta Youth Detention Center  | 28.4               | null                       |
| 2018 | 706       | Muscogee County                | 2064      | Key Elementary School           | 63.4               | 4                          |
| 2018 | 722       | Rockdale County                | 0378      | Edwards Middle School           | 64.9               | 5                          |
```

#### Statistics (2018)

```
| statistic  | Year   | System ID | CCRPI Single Score | School Climate Star Rating |
| count      | 2278   | 2278      | 2245               | 2236                       |
| null_count | 0      | 0         | 33                 | 42                         |
| mean       | 2018.0 | 110816    | 71.94              | 3.87                       |
| std        | 0.0    | 922944    | 12.38              | 0.93                       |
| min        | 2018   | 601       | 17.8               | 1                          |
| 25%        | 2018   | 636       | 64.3               | 3                          |
| 50%        | 2018   | 667       | 72.2               | 4                          |
| 75%        | 2018   | 714       | 80.5               | 5                          |
| max        | 2018   | 7,991,895 | 98.7               | 5                          |
```

#### Null Counts (2018)

| Year | System ID | System Name | School ID | School Name | CCRPI Single Score | School Climate Star Rating |
|------|-----------|-------------|-----------|-------------|--------------------|----------------------------|
| 0    | 0         | 0           | 0         | 0           | 33                 | 42                         |

#### Categorical Columns (2018)

| Column | Distinct Values |
|--------|----------------|
| System Name | 211 distinct district names (e.g., "Appling County", "Atkinson County", "Atlanta Public Schools", ...). Includes regular districts (3-digit codes) and state-charter operators with prefixes like `State Charter Schools- ...` and `State Schools` (7-digit codes). |
| School Name | 2,182 distinct school names. |
| School Climate Star Rating | 1 (45), 2 (127), 3 (474), 4 (1,013), 5 (577), null (42). |

#### Suppression Markers (2018)

None. CCRPI Single Score and School Climate Star Rating both use true nulls (blank cells) rather than text suppression markers in this era.

#### Era 1 cross-file notes

- 2014 file (`CCRPI Score and School Climate Star Rating 04.14.15.xlsx`) and 2017 file have all ID columns (`Year`, `System ID`, `School ID`) stored as String rather than Int64. Other Era 1 files have `Year` and `System ID` as Int64.
- `School ID` is consistently a 4-digit zero-padded String across all Era 1 files (e.g., "0103", "2065").
- Row counts per file: 2014 (2,261), 2015 (2,271), 2016 (2,269), 2017 (2,235), 2018 (2,278).

### Era 2: 2019

**File**: `2019 School Climate Star Rating_11_26_19.xls`

**Columns**: `School Year`, `System ID`, `System Name`, `School ID`, `School Name`, `CCRPI Single Score`, `School Climate Star Rating`

Same columns as Era 1 except `Year` is renamed to `School Year`. All ID columns are stored as String. CCRPI Single Score is also stored as String to accommodate the `NA` suppression marker.

| Column | Description |
|--------|-------------|
| School Year | Integer year (2019). |
| System ID | District code, String (e.g., "601", "891"). |
| System Name | District name. |
| School ID | School code, 4-digit zero-padded String (e.g., "0100"). |
| School Name | School name. |
| CCRPI Single Score | CCRPI composite score 0-100, **stored as String** with `NA` suppression marker for 35 rows. |
| School Climate Star Rating | Integer 1-5, with 42 nulls. |

#### Sample Data (2019)

```
shape: (5, 7)
| School Year | System ID | System Name     | School ID | School Name                     | CCRPI Single Score | School Climate Star Rating |
| 2019        | 729       | Sumter County   | 0100      | Sumter County Primary School    | 57.3               | 4                          |
| 2019        | 644       | DeKalb County   | 2065      | Cary Reynolds Elementary School | 69.9               | 3                          |
| 2019        | 785       | Rome City       | 0275      | East Central Elementary School  | 77.7               | 5                          |
| 2019        | 706       | Muscogee County | 1066      | Reese Road Leadership Academy   | 67.3               | 4                          |
| 2019        | 722       | Rockdale County | 0194      | Shoal Creek Elementary School   | 67.3               | 5                          |
```

#### Statistics (2019)

```
| statistic  | School Year | School Climate Star Rating |
| count      | 2279        | 2237                       |
| null_count | 0           | 42                         |
| mean       | 2019.0      | 3.93                       |
| std        | 0.0         | 0.92                       |
| min        | 2019        | 1                          |
| 25%        | 2019        | 3                          |
| 50%        | 2019        | 4                          |
| 75%        | 2019        | 5                          |
| max        | 2019        | 5                          |
```

CCRPI Single Score is stored as String, so `describe()` reports min "18.6" and max "NA" (alphabetical, not numeric).

#### Null Counts (2019)

| School Year | System ID | System Name | School ID | School Name | CCRPI Single Score | School Climate Star Rating |
|-------------|-----------|-------------|-----------|-------------|--------------------|----------------------------|
| 0           | 0         | 0           | 0         | 0           | 0 (35 are `NA`)    | 42                         |

#### Categorical Columns (2019)

| Column | Distinct Values |
|--------|----------------|
| System Name | 211 distinct district names. |
| School Name | 2,183 distinct school names. |
| School Climate Star Rating | 1 (32), 2 (137), 3 (423), 4 (1,019), 5 (626), null (42). |

#### Suppression Markers (2019)

| Column | Non-Numeric Values |
|--------|-------------------|
| CCRPI Single Score | `NA` (35 rows) |

### Era 3: 2024

**File**: `2024 School Climate Star Rating.xlsx`

**Columns**: `School Year`, `System ID`, `System Name`, `School ID`, `School Name`, `School Climate Star Rating`

CCRPI Single Score column is **dropped** in this era — only the School Climate Star Rating is reported. ID columns are stored as Int64 (not zero-padded strings).

| Column | Description |
|--------|-------------|
| School Year | Integer year (2024). |
| System ID | District code as Int64 (e.g., 601, 7820618). 7-digit codes are charter operators. |
| System Name | District name. |
| School ID | School code as Int64 (e.g., 201, 100, 5567). **Not zero-padded** in this file — must be padded to 4 digits during transform to align with Era 1/2 data. |
| School Name | School name. |
| School Climate Star Rating | Integer 1-5, with 60 nulls. |

#### Sample Data (2024)

```
shape: (5, 6)
| School Year | System ID | System Name                                       | School ID | School Name                   | School Climate Star Rating |
| 2024        | 734       | Telfair County                                    | 201       | Telfair County High School    | 4                          |
| 2024        | 644       | DeKalb County                                     | 3051      | Briarlake Elementary School   | 4                          |
| 2024        | 7820618   | State Charter Schools- Coastal Plains High School | 618       | Coastal Plains High School    | 1                          |
| 2024        | 706       | Muscogee County                                   | 3066      | Rigdon Road Elementary School | 3                          |
| 2024        | 726       | Griffin-Spalding County                           | 103       | Moreland Road Elementary      | null                       |
```

#### Statistics (2024)

```
| statistic  | School Year | System ID | School ID | School Climate Star Rating |
| count      | 2300        | 2300      | 2300      | 2240                       |
| null_count | 0           | 0         | 0         | 60                         |
| mean       | 2024.0      | 177639    | 1011.6    | 3.66                       |
| std        | 0.0         | 1,163,800 | 1,412.4   | 1.04                       |
| min        | 2024        | 601       | 100       | 1                          |
| 25%        | 2024        | 636       | 188       | 3                          |
| 50%        | 2024        | 667       | 294       | 4                          |
| 75%        | 2024        | 715       | 1,062     | 4                          |
| max        | 2024        | 7,830,647 | 5,567     | 5                          |
```

#### Null Counts (2024)

| School Year | System ID | System Name | School ID | School Name | School Climate Star Rating |
|-------------|-----------|-------------|-----------|-------------|----------------------------|
| 0           | 0         | 0           | 0         | 0           | 60                         |

#### Categorical Columns (2024)

| Column | Distinct Values |
|--------|----------------|
| System Name | 234 distinct district names (more than Era 1/2 due to charter expansion). |
| School Name | 2,200 distinct school names. |
| School Climate Star Rating | 1 (86), 2 (214), 3 (576), 4 (872), 5 (492), null (60). |

#### Suppression Markers (2024)

None. School Climate Star Rating uses true nulls (blank cells).

## ETL Considerations

- **Year column rename across eras**: `Year` (Era 1) vs `School Year` (Era 2-3). Standardize to a single `school_year` source column before extracting `year`.
- **ID column dtype variations**: `System ID` and `School ID` are stored as different dtypes across files (Int64 vs String). 2014 and 2017 store both as String; 2015/2016/2018 store `System ID` as Int64 and `School ID` as String; 2019 stores both as String; 2024 stores both as Int64. Always cast to String and apply `zfill(3)` to district codes and `zfill(4)` to school codes per the education domain CLAUDE.md. **2024 school IDs in particular are bare integers and must be padded** (e.g., `100` → `"0100"`).
- **Charter and state-school district codes**: 7-digit `System ID` values (e.g., `7820108`, `7991895`) belong to State Charter Schools and State Schools. Do **not** truncate — preserve as-is per the education domain rule "Never truncate with `.str.slice(0, 3)`".
- **2019 CCRPI Single Score is a String column with `NA` markers**: Must cast with `strict=False` (or replace `NA` with null first) to convert to Float. 35 rows in 2019 use `NA` to indicate suppressed/missing CCRPI scores.
- **2024 has no CCRPI Single Score column**: This metric must be nullable in the gold schema. Rows from 2024 will have null `ccrpi_single_score` (or whatever the gold column is named).
- **Star Rating nulls are real data**: Schools without a star rating (42-60 per year, including new schools, special-purpose facilities like detention centers, and very small enrollments) have blank star ratings. Preserve as null — do not impute.
- **Year coverage gaps**: Bronze covers 2014-2019 and 2024 only. Years 2020-2023 are absent (likely due to COVID disruption — Georgia paused CCRPI calculation in 2020 and 2021). Gold should reflect the actual year coverage; do not synthesize missing years.
- **Filename year vs data year**: The 2014 data is in a file named `CCRPI Score and School Climate Star Rating 04.14.15.xlsx` (April 14, 2015 publication). All other files have the data year in the filename. Always trust the in-file `Year`/`School Year` column over the filename.
- **Detail level**: All rows are school-level. There are no state/district aggregation rows in any file. The transform should set `detail_level = "school"` for every row, which means `district_code` and `school_code` are both populated (no nulling needed).
- **Star Rating type**: The gold schema should keep `school_climate_star_rating` as `pl.Int8` (or similar) — values are always 1-5 and never decimal. Do **not** scale to 0-1; this is an ordinal star rating, not a percentage (per "Percentage Scale Exceptions" in education CLAUDE.md).
- **CCRPI Single Score type**: The gold schema should keep `ccrpi_single_score` as `pl.Float64` (or `Float32`) on a 0-100 scale. Do **not** scale to 0-1; this is a composite score, not a percentage (per "Percentage Scale Exceptions" in education CLAUDE.md).

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| Year / School Year | not_in_gold | — | Used to derive `year` (Int32) per education domain conventions |
| System ID | fact_key | district_code | Cast Utf8 + zfill(3); preserves 7-digit charter codes; FK to districts dimension |
| System Name | dimension_attribute | — | district_name lives in `data/gold/education/_dimensions/districts.parquet` |
| School ID | fact_key | school_code | Cast Utf8 + zfill(4); FK (composite with district_code) to schools dimension |
| School Name | dimension_attribute | — | school_name lives in `data/gold/education/_dimensions/schools.parquet` |
| CCRPI Single Score | fact_metric | ccrpi_single_score | Float, 0-100 scale (NOT a percentage). Null for all 2024 rows; null/`NA` for suppressed rows in earlier years. |
| School Climate Star Rating | fact_metric | school_climate_star_rating | Int8, ordinal 1-5 (NOT scaled). Null for schools without a rating. |

The fact table has no demographic dimension (the source is not broken out by subgroup) and no topic-specific categorical columns. Output: `data/gold/education/ccrpi_climate_star_rating/year=YYYY/schools.parquet` only — no `districts.parquet` or `states.parquet` since the source data has no aggregate rows.

## Corrections

Found during transform authoring (2026-06-12), each re-verified directly against the bronze files:

1. **The 2015 file contains one byte-identical duplicate row** — Murray County (`System ID` 705) / Spring Place Elementary School (`School ID` 1052) appears twice with identical values (CCRPI Single Score 68.6, Star Rating 5). This doc's per-file row count of 2,271 for 2015 is correct, but the duplicate is not mentioned anywhere. It is the only duplicate `(System ID, School ID)` key in any of the 7 files. Evidence: group-by count on zfilled IDs yields exactly one key with 2 rows, both rows identical on every column. Gold therefore has 2,270 rows for 2015 (one copy dropped by dedup).
2. **Star-rating null range is 11-60 per year, not "42-60 per year"** (ETL Considerations, "Star Rating nulls are real data" bullet). Actual per-year `School Climate Star Rating` null counts: 2014 = 17, 2015 = 28, 2016 = 35, 2017 = 11, 2018 = 42, 2019 = 42, 2024 = 60. The "42-60" claim only describes 2018-2024. The substance of the bullet (nulls are real, preserve them) is unchanged.
3. **All metric "nulls" are literal `NA` text markers — no file contains a blank metric cell** (found by the data review, 2026-06-12). The per-era "Suppression Markers" sections claim Era 1 and Era 3 use "true nulls (blank cells) rather than text suppression markers". Raw-cell inspection (pandas `dtype=str, keep_default_na=False`, confirmed at cell level with openpyxl) shows zero blank cells in either metric column in any of the 7 files: every missing value is the literal string `NA`. Per-file `NA` counts — CCRPI Single Score: 2014 = 25, 2015 = 123, 2016 = 127, 2017 = 89, 2018 = 33, 2019 = 35; School Climate Star Rating: 2014 = 17, 2015 = 28, 2016 = 35, 2017 = 11, 2018 = 42, 2019 = 42, 2024 = 60 — each exactly equals the null counts reported elsewhere in this doc. Earlier profiling read the numeric-typed columns through schema inference, which converted the `NA` strings to nulls silently, making them look like blank cells; only 2019's string-typed CCRPI column surfaced them as markers. There is no evidence the 2019 `NA`s differ in meaning from any other year's: `NA` marks "no score/rating published" (e.g., the 2018 DJJ Atlanta Youth Detention Center's star `NA` is a not-rated facility), not specifically privacy suppression. ETL impact: none — the shared reader nulls `NA` in all columns at read, so gold values are identical either way.

Supplemental observed CCRPI score min/max per year: 2014 21.3-101.2, 2015 23.2-108.4, 2016 22.9-110.3, 2017 16.4-108.2, 2018 17.8-98.7, 2019 18.6-99.3 — consistent with the doc's bonus-point-era description (values above 100 through 2017, capped below 100 from 2018).
