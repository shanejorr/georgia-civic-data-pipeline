# dropout_rate_7_12 — Bronze Data Structure

## Overview

- Topic: dropout_rate_7_12
- Source: gosa
- Files: 14 files spanning 2011–2024 (school years 2010-11 through 2023-24)
- Unreadable files: none
- Year representation: present in both the filename (`dropout_rate_7_12_YYYY.csv`) and a `LONG_SCHOOL_YEAR` column (`YYYY-YY` format, e.g., `2023-24`)
- Filename-to-data year offset: same — the filename year always equals the ending calendar year of the school year in `LONG_SCHOOL_YEAR` (e.g., `_2024.csv` contains `2023-24` rows)
- Detail levels: state, district, school
- Percentage scale: 0–100 (for `PROGRAM_PERCENT`)
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| dropout_rate_7_12_2011.csv | 6b2e4064dbc33b2a9840647d5cd66c98004a29f6e9e5607f89a2256e9076094b |
| dropout_rate_7_12_2012.csv | 9162e9e5773acb1b991050e55f67d2dfaa87c5f36037b2c2a91ada69fce0be05 |
| dropout_rate_7_12_2013.csv | 02a2a732d1e1cfc5925aae8746a00930ac0078888b85ec9b3be98d920010d59b |
| dropout_rate_7_12_2014.csv | 080b2fce836c5849526a5aa9538a765ecb432dcf4c1b2bab806e635de07d79d2 |
| dropout_rate_7_12_2015.csv | e4d98965e4da59d9a788982528dfea5208df633f226c51c3379c5d3c8ced4f92 |
| dropout_rate_7_12_2016.csv | 0ff0d2e143581df3b4d0237ad8f166a1a7107c67f717e9345356ba49f90b6edc |
| dropout_rate_7_12_2017.csv | ca4b55d9b55cfc1ba0e9e2b54bc2bc4310ee8672f153f4f7644100fff8965345 |
| dropout_rate_7_12_2018.csv | 083236585cb3eb9b3523b3c6234b4090e2c438a0f85b0c3715fc792372f0c903 |
| dropout_rate_7_12_2019.csv | 15a4be1440c43d27b22747a604c9eb08e33074aed0a3b4582bfba6eb248fc10e |
| dropout_rate_7_12_2020.csv | 555d3ecd5b4e1506c791ad51c1b7218767cd125b882d0d97db4ea28ca8c8af68 |
| dropout_rate_7_12_2021.csv | 3b4352641a9364a6ce2c39352ddb196f1293f5551930938056ff8d224afa43b9 |
| dropout_rate_7_12_2022.csv | 3bfb591df6db0c9946394382bcb805a558d31e6d64650bac7d792cf21964df86 |
| dropout_rate_7_12_2023.csv | 53fce29664aef226de78550ac14c0d862299bcc2178041229c64519140d98cbc |
| dropout_rate_7_12_2024.csv | 047265f514fcf03cd72e4d941b988473511c610fcb8cb4cb971b15d1df113762 |

## Summary

This dataset reports the number of grade 7–12 dropouts (`PROGRAM_TOTAL`) and the dropout rate as a percentage (`PROGRAM_PERCENT`) for each Georgia public school, district, and the state, broken out by demographic subgroups (race/ethnicity, gender, economic status, English proficiency, migrant status, disability status, plus an `ALL Students` total). The label set has 15 demographics most years, but 14 in 2020–2022 (the `Limited English Proficient` category is absent in those three files and returns starting with 2023). Suppressed values (cells where the cohort is below the reporting threshold of 10) are explicit in every era — represented as nulls in 2011–2020 and as the literal string `TFS` ("too few students") in 2021–2024. Each file contains exactly one school-year of data.

## Eras

### Era 1: 2023–2024 (with `#RPT_NAME` header)

The 2023 and 2024 files added a leading `#RPT_NAME` column whose only value is `7-12 Dropouts`. All other columns are identical to Era 2.

| Column | Description |
|--------|-------------|
| #RPT_NAME | Report name; constant `"7-12 Dropouts"`. Era 1 only. |
| LONG_SCHOOL_YEAR | School year as `YYYY-YY` (e.g., `2023-24`). One value per file. |
| DETAIL_LVL_DESC | Detail level: `State`, `District`, or `School` |
| SCHOOL_DSTRCT_CD | GOSA district code (3-digit standard or 7-digit charter); the literal `ALL` for state-level rows |
| SCHOOL_DSTRCT_NM | District name; the literal `All Column Values` for state-level rows |
| INSTN_NUMBER | GOSA school code (4-digit, zero-padded); the literal `ALL` for state and district rows |
| INSTN_NAME | School name; the literal `All Column Values` for state and district rows |
| GRADES_SERVED_DESC | Comma-separated grade levels served by the institution (e.g., `06,07,08`, `09,10,11,12`, or longer spans); the broadest grade span of the district for district rows |
| LABEL_LVL_1_DESC | Demographic subgroup label, prefixed with `7-12 Drop Outs -` (15 distinct values) |
| PROGRAM_TOTAL | Number of dropouts (integer ≥10) or the suppression marker `TFS` |
| PROGRAM_PERCENT | Dropout rate (0–100, one decimal place) or the suppression marker `TFS` |

#### Sample Data (2024)

| #RPT_NAME | LONG_SCHOOL_YEAR | DETAIL_LVL_DESC | SCHOOL_DSTRCT_CD | SCHOOL_DSTRCT_NM | INSTN_NUMBER | INSTN_NAME | GRADES_SERVED_DESC | LABEL_LVL_1_DESC | PROGRAM_TOTAL | PROGRAM_PERCENT |
|---|---|---|---|---|---|---|---|---|---|---|
| 7-12 Dropouts | 2023-24 | State | ALL | All Column Values | ALL | All Column Values | PK,KK,01,02,...,12 | 7-12 Drop Outs -ALL Students | 20203 | 2.3 |
| 7-12 Dropouts | 2023-24 | State | ALL | All Column Values | ALL | All Column Values | PK,KK,01,02,...,12 | 7-12 Drop Outs -Black | 9263 | 2.8 |
| 7-12 Dropouts | 2023-24 | District | 696 | Marion County | ALL | All Column Values | PK,KK,01,02,...,12 | 7-12 Drop Outs -Female | TFS | TFS |
| 7-12 Dropouts | 2023-24 | School | 747 | Walton County | 0111 | Walnut Grove High School | 09,10,11,12 | 7-12 Drop Outs -Black | TFS | TFS |
| 7-12 Dropouts | 2023-24 | School | 644 | DeKalb County | 0205 | Redan Middle School | 06,07,08 | 7-12 Drop Outs -Black | 20 | 4.7 |

#### Statistics (2024)

- Row count: 19,020
- All 11 columns are stored as `Utf8` (string) on read
- 0 nulls in any column (suppression is represented by the literal `TFS`, not null)

#### Null Counts (2024)

All 11 columns: 0 nulls. Suppressed metric values use the literal `TFS` string rather than null.

#### Categorical Columns (2024)

| Column | Distinct Count | Distinct Values (with row counts where useful) |
|--------|---------------|------------------------------------------------|
| #RPT_NAME | 1 | `7-12 Dropouts` (19,020) |
| LONG_SCHOOL_YEAR | 1 | `2023-24` (19,020) |
| DETAIL_LVL_DESC | 3 | `School` (15,495), `District` (3,510), `State` (15) |
| SCHOOL_DSTRCT_NM | 235 | District names (largest by row count: Gwinnett County 900, DeKalb County 810, Fulton County 705, Cobb County 660, Atlanta Public Schools 585). Includes the sentinel `All Column Values` for the 15 state rows. |
| INSTN_NAME | 1,010 | School names. Includes the sentinel `All Column Values` for state and district aggregate rows (3,525 rows = 234 districts × 15 demographics + 1 state × 15 demographics). |
| GRADES_SERVED_DESC | 44 | Comma-separated grade strings. Common patterns include `06,07,08` (middle schools), `09,10,11,12` (high schools), and `PK,KK,01,02,03,04,05,06,07,08,09,10,11,12` (full-K-12 districts and the state aggregate). |
| LABEL_LVL_1_DESC | 15 | `7-12 Drop Outs -ALL Students`, `7-12 Drop Outs -American Indian/Alaskan`, `7-12 Drop Outs -Asian/Pacific Islander`, `7-12 Drop Outs -Black`, `7-12 Drop Outs -Economically Disadvantaged`, `7-12 Drop Outs -Female`, `7-12 Drop Outs -Hispanic`, `7-12 Drop Outs -Limited English Proficient`, `7-12 Drop Outs -Male`, `7-12 Drop Outs -Migrant`, `7-12 Drop Outs -Multi-Racial`, `7-12 Drop Outs -Not Economically Disadvantaged`, `7-12 Drop Outs -Students With Disability`, `7-12 Drop Outs -Students Without Disability`, `7-12 Drop Outs -White` (each 1,268 rows in 2024) |

#### Suppression Markers (2024)

| Column | Marker | Count | Meaning |
|--------|--------|-------|---------|
| SCHOOL_DSTRCT_CD | `ALL` | 15 | State-level rows (one per demographic) |
| INSTN_NUMBER | `ALL` | 3,525 | State and district aggregate rows (15 state + 3,510 district) |
| PROGRAM_TOTAL | `TFS` | 15,627 | "Too few students" — cell suppressed for privacy (cohort <10) |
| PROGRAM_PERCENT | `TFS` | 15,627 | Same as `PROGRAM_TOTAL` (always co-suppressed) |

`PROGRAM_TOTAL` and `PROGRAM_PERCENT` are stored as strings because of the `TFS` marker; the underlying numeric values are integers (counts ≥10) and one-decimal-place floats (0.3–80.7) respectively.

### Era 2: 2011–2022 (no `#RPT_NAME` header)

10 columns, identical names and roles as Era 1 except for the missing `#RPT_NAME` column.

| Column | Description |
|--------|-------------|
| LONG_SCHOOL_YEAR | School year as `YYYY-YY` (e.g., `2021-22`). One value per file. |
| DETAIL_LVL_DESC | Detail level: `State`, `District`, or `School` |
| SCHOOL_DSTRCT_CD | GOSA district code; the literal `ALL` for state-level rows |
| SCHOOL_DSTRCT_NM | District name; the literal `All Column Values` for state-level rows |
| INSTN_NUMBER | GOSA school code; the literal `ALL` for state and district rows |
| INSTN_NAME | School name; the literal `All Column Values` for state and district rows |
| GRADES_SERVED_DESC | Comma-separated grade levels served (variable) |
| LABEL_LVL_1_DESC | Demographic subgroup label, prefixed with `7-12 Drop Outs -` (14–15 distinct values depending on year) |
| PROGRAM_TOTAL | Number of dropouts (integer ≥10), `TFS` (in 2021–2022), or null (in 2011–2020) |
| PROGRAM_PERCENT | Dropout rate (0–100), `TFS` (in 2021–2022), or null (in 2011–2020) |

#### Sample Data (2022)

| LONG_SCHOOL_YEAR | DETAIL_LVL_DESC | SCHOOL_DSTRCT_CD | SCHOOL_DSTRCT_NM | INSTN_NUMBER | INSTN_NAME | GRADES_SERVED_DESC | LABEL_LVL_1_DESC | PROGRAM_TOTAL | PROGRAM_PERCENT |
|---|---|---|---|---|---|---|---|---|---|
| 2021-22 | School | 636 | Columbia County | 0183 | Harlem High School | 09,10,11,12 | 7-12 Drop Outs -ALL Students | 27 | 2.2 |
| 2021-22 | District | 779 | Jefferson City | ALL | All Column Values | PK,KK,01,...,12 | 7-12 Drop Outs -Male | TFS | TFS |
| 2021-22 | School | 663 | Glynn County | 3552 | Brunswick High School | 09,10,11,12 | 7-12 Drop Outs -ALL Students | 21 | 1 |
| 2021-22 | School | 657 | Floyd County | 0103 | Coosa Middle School | 05,06,07,08 | 7-12 Drop Outs -Female | TFS | TFS |
| 2021-22 | School | 660 | Fulton County | 0204 | KIPP South Fulton Academy School | 05,06,07,08 | 7-12 Drop Outs -Not Economically Disadvantaged | TFS | TFS |

#### Sample Data (2011)

| LONG_SCHOOL_YEAR | DETAIL_LVL_DESC | SCHOOL_DSTRCT_CD | SCHOOL_DSTRCT_NM | INSTN_NUMBER | INSTN_NAME | GRADES_SERVED_DESC | LABEL_LVL_1_DESC | PROGRAM_TOTAL | PROGRAM_PERCENT |
|---|---|---|---|---|---|---|---|---|---|
| 2010-11 | School | 656 | Fayette County | 0192 | Sandy Creek High School | 09,10,11,12 | 7-12 Drop Outs -Migrant | null | null |
| 2010-11 | School | 741 | Troup County | 0201 | Callaway High School | 09,10,11,12 | 7-12 Drop Outs -Asian/Pacific Islander | null | null |
| 2010-11 | School | 694 | Macon County | 0199 | Macon County Middle School | 06,07,08 | 7-12 Drop Outs -Male | null | null |
| 2010-11 | School | 706 | Muscogee County | 0178 | Fort Middle School | 06,07,08 | 7-12 Drop Outs -Economically Disadvantaged | null | null |
| 2010-11 | School | 667 | Gwinnett County | 1019 | Gwinnett School of Mathematics, Science and Technology | 09,10,11,12 | 7-12 Drop Outs -Male | null | null |

#### Statistics (Era 2 row counts and suppression representation)

| Year | Rows | PROGRAM_TOTAL nulls | PROGRAM_TOTAL suppression marker | LABEL_LVL_1_DESC count |
|------|------|---------------------|----------------------------------|------------------------|
| 2011 | 17,310 | 13,400 | (none — uses null) | 15 |
| 2012 | 17,610 | 13,538 | (none — uses null) | 15 |
| 2013 | 17,670 | 13,851 | (none — uses null) | 15 |
| 2014 | 17,640 | 13,864 | (none — uses null) | 15 |
| 2015 | 17,880 | 14,012 | (none — uses null) | 15 |
| 2016 | 17,940 | 14,176 | (none — uses null) | 15 |
| 2017 | 18,015 | 14,297 | (none — uses null) | 15 |
| 2018 | 18,195 | 14,498 | (none — uses null) | 15 |
| 2019 | 18,330 | 14,865 | (none — uses null) | 15 |
| 2020 | 17,150 | 14,287 | (none — uses null) | 14 (no Limited English Proficient) |
| 2021 | 17,248 | 0 | `TFS` (14,147 rows) | 14 (no Limited English Proficient) |
| 2022 | 17,444 | 0 | `TFS` (13,900 rows) | 14 (no Limited English Proficient) |

#### Null Counts (Era 2)

`LONG_SCHOOL_YEAR`, `DETAIL_LVL_DESC`, `SCHOOL_DSTRCT_CD`, `SCHOOL_DSTRCT_NM`, `INSTN_NUMBER`, `INSTN_NAME`, `GRADES_SERVED_DESC`, `LABEL_LVL_1_DESC`: always 0 nulls.

`PROGRAM_TOTAL` and `PROGRAM_PERCENT`: nulls in 2011–2020 (representing suppression); 0 nulls in 2021–2022 (suppression switched to the `TFS` literal).

#### Categorical Columns (2022)

| Column | Distinct Count | Notes |
|--------|---------------|-------|
| LONG_SCHOOL_YEAR | 1 | `2021-22` |
| DETAIL_LVL_DESC | 3 | `School` (14,350), `District` (3,080), `State` (14) |
| SCHOOL_DSTRCT_NM | 223 | Includes `All Column Values` sentinel |
| INSTN_NAME | 1,000 | Includes `All Column Values` sentinel |
| GRADES_SERVED_DESC | 53 | Dominated by `09,10,11,12` (high schools), `06,07,08` (middle schools), and `PK,KK,01,02,03,04,05,06,07,08,09,10,11,12` (full-K-12 districts and state aggregate) |
| LABEL_LVL_1_DESC | 14 | Same set as Era 1 minus `Limited English Proficient`, which is absent in 2020–2022 |

#### Categorical Columns (2011)

| Column | Distinct Count | Notes |
|--------|---------------|-------|
| LONG_SCHOOL_YEAR | 1 | `2010-11` |
| DETAIL_LVL_DESC | 3 | `School` (14,490), `District` (2,805), `State` (15) |
| SCHOOL_DSTRCT_NM | 188 | Includes `All Column Values` sentinel |
| INSTN_NAME | 945 | Includes `All Column Values` sentinel |
| LABEL_LVL_1_DESC | 15 | Same set of 15 demographic labels as Era 1 (includes `Limited English Proficient`) |

#### Suppression Markers (Era 2)

| Column | Marker | Years | Notes |
|--------|--------|-------|-------|
| SCHOOL_DSTRCT_CD | `ALL` | all | State-level rows |
| INSTN_NUMBER | `ALL` | all | State and district rows |
| PROGRAM_TOTAL | empty/null | 2011–2020 | Privacy suppression |
| PROGRAM_TOTAL | `TFS` | 2021–2022 | Privacy suppression (cohort <10) |
| PROGRAM_PERCENT | empty/null | 2011–2020 | Privacy suppression (always co-suppressed with `PROGRAM_TOTAL`) |
| PROGRAM_PERCENT | `TFS` | 2021–2022 | Privacy suppression |

## ETL Considerations

- **`#RPT_NAME` is Era-1-only and constant.** Drop it during read for Era 1 files (or select the common 10 columns after concatenation) so the column set is uniform before transforming. Values are always `"7-12 Dropouts"`.
- **Two distinct suppression representations.** 2011–2020 use empty/null cells; 2021–2024 use the literal string `TFS`. The transform must convert `TFS` to null before casting `PROGRAM_TOTAL` to integer and `PROGRAM_PERCENT` to float (e.g., `pl.col("PROGRAM_TOTAL").replace("TFS", None).cast(pl.Int64, strict=False)`).
- **Numeric columns are stored as strings.** `PROGRAM_TOTAL` and `PROGRAM_PERCENT` need explicit casts and must be read with string-forced schema (`infer_schema=False` or `schema_overrides`) to avoid Polars failing on `ALL` and `TFS` tokens. `PROGRAM_TOTAL` is an integer (minimum is 10 because of the cell-size threshold). `PROGRAM_PERCENT` is a float on a 0–100 scale (observed range 0.2–93.6 across all years).
- **Demographic set varies by year.** Years 2020, 2021, and 2022 have 14 demographic labels (no `Limited English Proficient`); every other year has all 15. The transform should not hard-code a fixed count — just map whatever labels appear.
- **Geography sentinels.** `SCHOOL_DSTRCT_CD = "ALL"`, `INSTN_NUMBER = "ALL"`, `SCHOOL_DSTRCT_NM = "All Column Values"`, and `INSTN_NAME = "All Column Values"` mark aggregate rows. Per the education domain conventions, derive `detail_level` from `DETAIL_LVL_DESC` (lowercase: `State`/`District`/`School` → `state`/`district`/`school`) and null out `district_code` for state rows and `school_code` for state and district rows. The sentinel strings must NOT be carried into the gold fact table.
- **District code formatting.** District codes are 3-digit standard (e.g., `601`) or 7-digit charter/state-school codes (e.g., `7991894`) stored as strings. Apply `.cast(pl.Utf8).str.zfill(3)` per the education CLAUDE.md — never truncate. The 7-digit codes belong to state charter networks and state schools (e.g., `7991895 State Schools- Georgia School for the Deaf`, `7820108 State Charter Schools- Mountain Education Center School`, `7830110 Commission Charter Schools- Ivy Preparatory Academy School`).
- **School code formatting.** `INSTN_NUMBER` is 4 digits, zero-padded (e.g., `0100`, `3552`). Apply `.cast(pl.Utf8).str.zfill(4)`. Read as `Utf8` to preserve leading zeros; never treat as an integer.
- **Demographic mapping.** All `LABEL_LVL_1_DESC` values share the prefix `7-12 Drop Outs -` (note: prefix uses `Drop Outs` with a space, not `Dropouts`). Strip the prefix and map to the global demographics dimension. Labels with non-standard forms that may need explicit mapping include `Multi-Racial` (vs `Multiracial`), `American Indian/Alaskan` (vs `American Indian/Alaska Native`), and `Asian/Pacific Islander` (a combined category — confirm it maps to a single demographic key rather than being split). `ALL Students` is the total row.
- **`GRADES_SERVED_DESC` is metadata, not a metric.** It describes which grades the institution serves and varies even within a single school (district aggregate rows use the broadest span of any school in the district). The topic is already scoped to grades 7–12, so this column is not needed in the gold fact table. Note that many schools in this report serve only grades 5–8 or 6–8 (middle schools) — the `7-12 Drop Outs` metric is still reported for those institutions because grade 7 and 8 dropouts can occur there.
- **`LONG_SCHOOL_YEAR` derivation.** Convert `YYYY-YY` to a 4-digit ending year for the gold `year` column. The filename year matches the ending year, so either source produces the same value.
- **One row per (year × geography × demographic).** Each demographic label has identical row counts within a year (e.g., 1,268 rows per demographic in 2024 = 1 state + 234 districts + 1,033 schools). No multi-row aggregation is required during transform.
- **`SCHOOL_DSTRCT_NM` and `INSTN_NAME` belong in dimension tables, not the fact table.** Per the education domain conventions, names live in `data/gold/education/_dimensions/districts.parquet` and `schools.parquet` and should be excluded from the gold fact rows (only `district_code` and `school_code` survive into the fact table).

## Gold Schema Classification

For each bronze column (across all eras), classify its role in the gold star schema:

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| #RPT_NAME | not_in_gold | — | Era 1 only; constant `"7-12 Dropouts"` (no information) |
| LONG_SCHOOL_YEAR | fact_key | year | Convert `YYYY-YY` → ending 4-digit year as `pl.Int32` |
| DETAIL_LVL_DESC | not_in_gold | — | Used to drive geography nulling; implicit in output filename (`states.parquet` / `districts.parquet` / `schools.parquet`) |
| SCHOOL_DSTRCT_CD | fact_key | district_code | Cast to `pl.Utf8`, `.str.zfill(3)`; null out for state rows; sentinel `ALL` → null |
| SCHOOL_DSTRCT_NM | dimension_attribute | — | `district_name` in `districts.parquet` (title case); sentinel `All Column Values` excluded |
| INSTN_NUMBER | fact_key | school_code | Cast to `pl.Utf8`, `.str.zfill(4)`; null out for state/district rows; sentinel `ALL` → null |
| INSTN_NAME | dimension_attribute | — | `school_name` in `schools.parquet` (title case); sentinel `All Column Values` excluded |
| GRADES_SERVED_DESC | not_in_gold | — | Institution-level metadata; not relevant for a 7-12-scoped fact |
| LABEL_LVL_1_DESC | fact_key | demographic | FK to global demographics dimension. Strip the `"7-12 Drop Outs -"` prefix and map remaining label to the demographic key |
| PROGRAM_TOTAL | fact_metric | dropout_count | `pl.Int64`. Replace `TFS` with null, then cast (handles both Era 2 nulls and 2021–2024 `TFS`) |
| PROGRAM_PERCENT | fact_metric | dropout_rate | `pl.Float64` on 0–100 scale. Replace `TFS` with null, then cast |
