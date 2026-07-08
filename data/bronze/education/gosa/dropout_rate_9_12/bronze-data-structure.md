# dropout_rate_9_12 — Bronze Data Structure

## Overview

- Topic: dropout_rate_9_12
- Source: gosa
- Files: 14 files spanning 2011–2024 (school years 2010-11 through 2023-24)
- Unreadable files: none
- Year representation: present in both the filename (`dropout_rate_9_12_YYYY.csv`) and a `LONG_SCHOOL_YEAR` column (`YYYY-YY` format, e.g. `2023-24`)
- Filename-to-data year offset: same — filename year always equals the ending calendar year of the school year in `LONG_SCHOOL_YEAR` (e.g., `_2024.csv` contains `2023-24` rows)
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
| dropout_rate_9_12_2011.csv | 2d12c62577e747bb690891d4d78430058405d225901955c68987d3422a860375 |
| dropout_rate_9_12_2012.csv | 39f061e90b4702fbc28aa00f44c2201f4f9200efa43382d17c4369b03de87744 |
| dropout_rate_9_12_2013.csv | 3f42f2ce5e76201e9566d60c4bbe4fa2f2ff2e37ffb55e371aa5ffa950489be0 |
| dropout_rate_9_12_2014.csv | 63ef3ebf8abb81a90a8bb9d26c5425ebfe211f4d514649af611b7851818b8841 |
| dropout_rate_9_12_2015.csv | 3cbc3b7fa66cd4ac840eadb3d9857345ddeb000d0b968e7c50bb2e186a172633 |
| dropout_rate_9_12_2016.csv | c8bda1283059ab726e9feb83e432cc6f2e72cb109860e1f58f0eec388dbef208 |
| dropout_rate_9_12_2017.csv | 87b255e4a42d7dafce2aea7ea76c7b93ebf4069808d3ffee19911f8b02d5803a |
| dropout_rate_9_12_2018.csv | 95193f21c90a6ec900ebd2f38f66ab8b5c5d13dcdea7013b2b525f82f55c6084 |
| dropout_rate_9_12_2019.csv | d7b3ab53a1282e7135fd122e26f729e71f0472be6b84fd73dce99e6560814a2c |
| dropout_rate_9_12_2020.csv | 477b1f26def07ae6e1e14025fe7b6ac1c12c0363377c5f0f4e5c5796ef686630 |
| dropout_rate_9_12_2021.csv | f4aa0f251a69c1267ef03508ecc4402cc83f07039b033f1a803c12c3d5ec5606 |
| dropout_rate_9_12_2022.csv | 82f98b9ebdefe9208bbc375bb444fa6cd32b334ed0d9de1232a308f77726db4d |
| dropout_rate_9_12_2023.csv | 811a932cda822ff2e094c7b2d295bbc8fd0e95d9c0c33e75d9057f8b19e8c4b1 |
| dropout_rate_9_12_2024.csv | 1b9c103d4b8534b93ebeee4ba295bd8d4fe734ac7e0c0cb81c9d025f2c291e7f |

## Summary

This dataset reports the number of grade 9–12 dropouts (`PROGRAM_TOTAL`) and the dropout rate as a percentage (`PROGRAM_PERCENT`) for each Georgia public school, district, and the state, broken out by 15 demographic subgroups (race/ethnicity, gender, economic status, English proficiency, migrant status, disability status, plus an `ALL Students` total). Suppressed values (cells where the cohort is below the reporting threshold of 10) are explicit in every era — represented as nulls in 2011–2020 and as the literal string `TFS` ("too few students") in 2021–2024. Each file contains exactly one school-year of data.

## Eras

### Era 1: 2023–2024 (with `#RPT_NAME` header)

The 2023 and 2024 files added a leading `#RPT_NAME` column whose only value is `9-12 Dropouts`. All other columns are identical to Era 2.

| Column | Description |
|--------|-------------|
| #RPT_NAME | Report name; constant `"9-12 Dropouts"`. Era 1 only. |
| LONG_SCHOOL_YEAR | School year as `YYYY-YY` (e.g., `2023-24`). One value per file. |
| DETAIL_LVL_DESC | Detail level: `State`, `District`, or `School` |
| SCHOOL_DSTRCT_CD | GOSA district code (3-digit standard or 7-digit charter); the literal `ALL` for state-level rows |
| SCHOOL_DSTRCT_NM | District name; the literal `All Column Values` for state-level rows |
| INSTN_NUMBER | GOSA school code (4-digit, zero-padded); the literal `ALL` for state and district rows |
| INSTN_NAME | School name; the literal `All Column Values` for state and district rows |
| GRADES_SERVED_DESC | Comma-separated grade levels served by the school (e.g., `09,10,11,12`); the broadest grade span of the district for district rows |
| LABEL_LVL_1_DESC | Demographic subgroup label, prefixed with `9-12 Drop Outs -` (15 distinct values) |
| PROGRAM_TOTAL | Number of dropouts (integer ≥10) or the suppression marker `TFS` |
| PROGRAM_PERCENT | Dropout rate (0–100, one decimal place) or the suppression marker `TFS` |

#### Sample Data (2024)

| #RPT_NAME | LONG_SCHOOL_YEAR | DETAIL_LVL_DESC | SCHOOL_DSTRCT_CD | SCHOOL_DSTRCT_NM | INSTN_NUMBER | INSTN_NAME | GRADES_SERVED_DESC | LABEL_LVL_1_DESC | PROGRAM_TOTAL | PROGRAM_PERCENT |
|---|---|---|---|---|---|---|---|---|---|---|
| 9-12 Dropouts | 2023-24 | State | ALL | All Column Values | ALL | All Column Values | PK,KK,01,02,...,12 | 9-12 Drop Outs -ALL Students | 16616 | 2.8 |
| 9-12 Dropouts | 2023-24 | State | ALL | All Column Values | ALL | All Column Values | PK,KK,01,02,...,12 | 9-12 Drop Outs -American Indian/Alaskan | 51 | 4.1 |
| 9-12 Dropouts | 2023-24 | District | 601 | Appling County | ALL | All Column Values | PK,KK,01,02,...,12 | 9-12 Drop Outs -ALL Students | TFS | TFS |
| 9-12 Dropouts | 2023-24 | District | 793 | Vidalia City | ALL | All Column Values | PK,KK,01,02,...,12 | 9-12 Drop Outs -Students Without Disability | 11 | 1.6 |
| 9-12 Dropouts | 2023-24 | School | 761 | Atlanta Public Schools | 0212 | Kipp Atlanta Collegiate Charter School | 09,10,11,12 | 9-12 Drop Outs -White | TFS | TFS |

#### Statistics (2024)

- Row count: 11,130
- All columns are stored as `Utf8` (string) on read
- 0 nulls in any column

#### Null Counts (2024)

All 11 columns: 0 nulls. Suppressed metric values use the literal `TFS` string rather than null.

#### Categorical Columns (2024)

| Column | Distinct Count | Distinct Values (with row counts where useful) |
|--------|---------------|------------------------------------------------|
| #RPT_NAME | 1 | `9-12 Dropouts` (11,130) |
| LONG_SCHOOL_YEAR | 1 | `2023-24` (11,130) |
| DETAIL_LVL_DESC | 3 | `School` (7,605), `District` (3,510), `State` (15) |
| SCHOOL_DSTRCT_NM | 235 | District names (largest: Gwinnett County 465, DeKalb 420, Fulton 360, Cobb 285, APS 270). Includes the sentinel `All Column Values` for the 15 state rows. |
| INSTN_NAME | 499 | School names. Includes the sentinel `All Column Values` (3,525 rows = 234 districts × 15 demographics + 15 state). |
| GRADES_SERVED_DESC | 31 | Comma-separated grade strings; dominated by `09,10,11,12` (5,790) for high schools and `PK,KK,01,02,03,04,05,06,07,08,09,10,11,12` (3,510) for full-K-12 districts and the state aggregate. |
| LABEL_LVL_1_DESC | 15 | `9-12 Drop Outs -ALL Students`, `9-12 Drop Outs -American Indian/Alaskan`, `9-12 Drop Outs -Asian/Pacific Islander`, `9-12 Drop Outs -Black`, `9-12 Drop Outs -Economically Disadvantaged`, `9-12 Drop Outs -Female`, `9-12 Drop Outs -Hispanic`, `9-12 Drop Outs -Limited English Proficient`, `9-12 Drop Outs -Male`, `9-12 Drop Outs -Migrant`, `9-12 Drop Outs -Multi-Racial`, `9-12 Drop Outs -Not Economically Disadvantaged`, `9-12 Drop Outs -Students With Disability`, `9-12 Drop Outs -Students Without Disability`, `9-12 Drop Outs -White` (each 742 rows in 2024) |

#### Suppression Markers (2024)

| Column | Marker | Count | Meaning |
|--------|--------|-------|---------|
| SCHOOL_DSTRCT_CD | `ALL` | 15 | State-level rows (one per demographic) |
| INSTN_NUMBER | `ALL` | 3,525 | State and district aggregate rows |
| PROGRAM_TOTAL | `TFS` | 8,322 | "Too few students" — cell suppressed for privacy (cohort <10) |
| PROGRAM_PERCENT | `TFS` | 8,322 | Same as `PROGRAM_TOTAL` (always co-suppressed) |

`PROGRAM_TOTAL` and `PROGRAM_PERCENT` are stored as strings because of the `TFS` marker; the underlying numeric values are integers (counts ≥10) and one-decimal-place floats (0.4–81.1) respectively.

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
| LABEL_LVL_1_DESC | Demographic subgroup label, prefixed with `9-12 Drop Outs -` (15 distinct values, identical set to Era 1) |
| PROGRAM_TOTAL | Number of dropouts (integer ≥10), `TFS` (in 2021–2022), or null (in 2011–2020) |
| PROGRAM_PERCENT | Dropout rate (0–100), `TFS` (in 2021–2022), or null (in 2011–2020) |

#### Sample Data (2022)

| LONG_SCHOOL_YEAR | DETAIL_LVL_DESC | SCHOOL_DSTRCT_CD | SCHOOL_DSTRCT_NM | INSTN_NUMBER | INSTN_NAME | GRADES_SERVED_DESC | LABEL_LVL_1_DESC | PROGRAM_TOTAL | PROGRAM_PERCENT |
|---|---|---|---|---|---|---|---|---|---|
| 2021-22 | School | 721 | Richmond County | 0213 | Richmond County Technical Career Magnet School | 06,07,08,09,10,11,12 | 9-12 Drop Outs -Not Economically Disadvantaged | TFS | TFS |
| 2021-22 | School | 608 | Bartow County | 0105 | Adairsville High School | 09,10,11,12 | 9-12 Drop Outs -Not Economically Disadvantaged | TFS | TFS |
| 2021-22 | School | 791 | Trion City | 0301 | Trion High School | 09,10,11,12 | 9-12 Drop Outs -Black | TFS | TFS |
| 2021-22 | School | 711 | Peach County | 2052 | Peach County High School | 09,10,11,12 | 9-12 Drop Outs -Economically Disadvantaged | 16 | 1.4 |

#### Sample Data (2011)

| LONG_SCHOOL_YEAR | DETAIL_LVL_DESC | SCHOOL_DSTRCT_CD | SCHOOL_DSTRCT_NM | INSTN_NUMBER | INSTN_NAME | GRADES_SERVED_DESC | LABEL_LVL_1_DESC | PROGRAM_TOTAL | PROGRAM_PERCENT |
|---|---|---|---|---|---|---|---|---|---|
| 2010-11 | School | 667 | Gwinnett County | 0189 | Phoenix High School | 09,10,11,12 | 9-12 Drop Outs -Economically Disadvantaged | 152 | 33 |
| 2010-11 | School | 613 | Brantley County | 1050 | Brantley County High School | 09,10,11,12 | 9-12 Drop Outs -Multi-Racial | null | null |
| 2010-11 | District | 668 | Habersham County | ALL | All Column Values | PK,KK,01,02,...,12 | 9-12 Drop Outs -Asian/Pacific Islander | null | null |

#### Statistics (Era 2 row counts and suppression representation)

| Year | Rows | PROGRAM_TOTAL nulls | PROGRAM_TOTAL suppression marker |
|------|------|---------------------|----------------------------------|
| 2011 | 9,885 | 6,270 | (none — uses null) |
| 2012 | 9,960 | 6,264 | (none — uses null) |
| 2013 | 9,900 | 6,390 | (none — uses null) |
| 2014 | 9,990 | 6,530 | (none — uses null) |
| 2015 | 10,230 | 6,703 | (none — uses null) |
| 2016 | 10,275 | 6,836 | (none — uses null) |
| 2017 | 10,155 | 6,759 | (none — uses null) |
| 2018 | 10,500 | 7,170 | (none — uses null) |
| 2019 | 10,575 | 7,554 | (none — uses null) |
| 2020 | 9,940 | 7,459 | (none — uses null) |
| 2021 | 10,052 | 0 | `TFS` (7,247 rows) |
| 2022 | 10,122 | 0 | `TFS` (7,089 rows) |

#### Null Counts (Era 2)

`LONG_SCHOOL_YEAR`, `DETAIL_LVL_DESC`, `SCHOOL_DSTRCT_CD`, `SCHOOL_DSTRCT_NM`, `INSTN_NUMBER`, `INSTN_NAME`, `GRADES_SERVED_DESC`, `LABEL_LVL_1_DESC`: always 0 nulls.

`PROGRAM_TOTAL` and `PROGRAM_PERCENT`: nulls in 2011–2020 (representing suppression); 0 nulls in 2021–2022 (suppression switched to the `TFS` literal).

#### Categorical Columns (2022)

| Column | Distinct Count | Notes |
|--------|---------------|-------|
| LONG_SCHOOL_YEAR | 1 | `2021-22` |
| DETAIL_LVL_DESC | 3 | `School` (7,028), `District` (3,080), `State` (14) |
| SCHOOL_DSTRCT_NM | 223 | Includes `All Column Values` sentinel |
| INSTN_NAME | 492 | Includes `All Column Values` sentinel (3,122 rows) |
| GRADES_SERVED_DESC | 40 | Dominated by `09,10,11,12` (5,292) and `PK,KK,01,02,03,04,05,06,07,08,09,10,11,12` (3,066) |
| LABEL_LVL_1_DESC | 14 in 2022 (15 in most years; identical set to Era 1, but a single demographic may have zero rows in a given year) |

#### Categorical Columns (2011)

| Column | Distinct Count | Notes |
|--------|---------------|-------|
| LONG_SCHOOL_YEAR | 1 | `2010-11` |
| DETAIL_LVL_DESC | 3 | `School` (7,095), `District` (2,775), `State` (15) |
| GRADES_SERVED_DESC | 39 | Same dominant patterns as 2022 |
| LABEL_LVL_1_DESC | 15 | Same set of 15 demographic labels as Era 1 |

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

- **`#RPT_NAME` is Era-1-only and constant.** Drop it during read for Era 1 files (or read both eras with `infer_schema_length=0` and select the common 10 columns) so the column-set is uniform before transforming.
- **Two distinct suppression representations.** 2011–2020 use empty/null cells; 2021–2024 use the literal string `TFS`. The transform must convert `TFS` to null before casting `PROGRAM_TOTAL` to integer and `PROGRAM_PERCENT` to float (e.g., `pl.col("PROGRAM_TOTAL").replace("TFS", None).cast(pl.Int64, strict=False)`).
- **Numeric columns are stored as strings.** `PROGRAM_TOTAL` and `PROGRAM_PERCENT` need explicit casts. `PROGRAM_TOTAL` is an integer (minimum is 10 because of the cell-size threshold). `PROGRAM_PERCENT` is a float on a 0–100 scale; per `src/etl/education/CLAUDE.md`, scoring/score-style metrics keep their natural scale, but a percentage like dropout rate is a standard percentage and should follow the project rule for percentages — confirm with `data-cleaning-standards` whether to keep 0–100 or rescale to 0–1.
- **Geography sentinels.** `SCHOOL_DSTRCT_CD = "ALL"`, `INSTN_NUMBER = "ALL"`, `SCHOOL_DSTRCT_NM = "All Column Values"`, and `INSTN_NAME = "All Column Values"` mark aggregate rows. Per the education domain conventions, derive `detail_level` from `DETAIL_LVL_DESC` (lower-case it: `State`/`District`/`School` → `state`/`district`/`school`) and null out `district_code` for state rows and `school_code` for state and district rows. The sentinel strings must NOT be carried into the gold fact table.
- **District code formatting.** District codes are 3-digit standard or 7-digit charter codes stored as strings (e.g., `601`, `7991894`). Apply `.str.zfill(3)` (per education CLAUDE.md) — never truncate. School codes are 4 digits and need `.str.zfill(4)`. Both columns must be read as `Utf8` (avoid Polars' integer inference dropping leading zeros).
- **Demographic mapping.** All 15 `LABEL_LVL_1_DESC` values share the prefix `9-12 Drop Outs -`. Strip the prefix and map to the global demographics dimension. Note `Multi-Racial` (vs `Multiracial`), `American Indian/Alaskan` (vs `American Indian/Alaska Native`), and `Asian/Pacific Islander` (which is a combined category — confirm it maps to a single demographic key, not split). `ALL Students` is the total row.
- **`GRADES_SERVED_DESC` is metadata, not a metric.** It describes which grades the institution serves and varies even within a single school (district aggregate rows use the broadest span of any school in the district). It is not needed in the gold fact table because the topic is already scoped to grades 9–12.
- **`LONG_SCHOOL_YEAR` derivation.** Convert `YYYY-YY` to a 4-digit ending year for the gold `year` column. The filename year matches the ending year, so either source produces the same value.
- **One row per (year × geography × demographic).** Confirmed that 2024 has 11,130 = 234 districts × 15 demographics + 1 state × 15 demographics + ~7,605 schools, etc. (counts vary year to year as schools open/close). No multi-row aggregation is required during transform.
- **`SCHOOL_DSTRCT_NM` and `INSTN_NAME` belong in dimension tables, not the fact table.** Per the education domain conventions, names live in `data/gold/education/_dimensions/districts.parquet` and `schools.parquet` and should be excluded from the gold fact rows (only `district_code` and `school_code` survive into the fact table).

## Gold Schema Classification

For each bronze column (across all eras), classify its role in the gold star schema:

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| #RPT_NAME | not_in_gold | — | Era 1 only; constant `"9-12 Dropouts"` (no information) |
| LONG_SCHOOL_YEAR | fact_key | year | Convert `YYYY-YY` → ending 4-digit year as `pl.Int32` |
| DETAIL_LVL_DESC | not_in_gold | — | Used to drive geography nulling; implicit in output filename (`states.parquet` / `districts.parquet` / `schools.parquet`) |
| SCHOOL_DSTRCT_CD | fact_key | district_code | Cast to `pl.Utf8`, `.str.zfill(3)`; null out for state rows; sentinel `ALL` → null |
| SCHOOL_DSTRCT_NM | dimension_attribute | — | `district_name` in `districts.parquet` (title case); sentinel `All Column Values` excluded |
| INSTN_NUMBER | fact_key | school_code | Cast to `pl.Utf8`, `.str.zfill(4)`; null out for state/district rows; sentinel `ALL` → null |
| INSTN_NAME | dimension_attribute | — | `school_name` in `schools.parquet` (title case); sentinel `All Column Values` excluded |
| GRADES_SERVED_DESC | not_in_gold | — | Institution-level metadata; not relevant for a 9-12-scoped fact |
| LABEL_LVL_1_DESC | fact_key | demographic | FK to global demographics dimension. Strip the `"9-12 Drop Outs -"` prefix and map remaining label to the demographic key |
| PROGRAM_TOTAL | fact_metric | dropout_count | `pl.Int64`. Replace `TFS` with null, then cast (handles both Era 2 nulls and Era 1/late-Era-2 `TFS`) |
| PROGRAM_PERCENT | fact_metric | dropout_rate | `pl.Float64` on 0–100 scale. Replace `TFS` with null, then cast |
