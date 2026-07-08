# enrollment_by_grade_level — Bronze Data Structure

## Overview

- Topic: enrollment_by_grade_level
- Source: gosa
- Files: 14 files spanning 2011–2024 (school years 2010-11 through 2023-24)
- Unreadable files: none
- Year representation: present in both the filename (`enrollment_by_grade_level_YYYY.csv`) and a `LONG_SCHOOL_YEAR` column (`YYYY-YY` format, e.g. `2023-24`). One school year per file.
- Filename-to-data year offset: same — filename year always equals the ending calendar year of the school year in `LONG_SCHOOL_YEAR` (e.g., `_2024.csv` contains `2023-24` rows)
- Detail levels: state, district, school
- Percentage scale: not applicable — the only metric (`ENROLLMENT_COUNT`) is an integer count, not a percentage
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| enrollment_by_grade_level_2011.csv | db7478f2f419e8ac8943303ee1ed06eb58be14a2e0d9e20f0c97820b14af8659 |
| enrollment_by_grade_level_2012.csv | 915654c3006d8ddfacc57fc56ceb013fa918b90b57bd97656308d2aac26cb170 |
| enrollment_by_grade_level_2013.csv | 17f83c410c22123b930053ec749af6ec8a016c830a430b2fb11a4cceed73c34c |
| enrollment_by_grade_level_2014.csv | 376f00c37ad0cb924854592af6ac5a78870f307720119e027aaeff787b3aa840 |
| enrollment_by_grade_level_2015.csv | 08a586acdcd91f6ca709469498924fd4c8102a544846de97baee6582610cef1a |
| enrollment_by_grade_level_2016.csv | 26eddfef8a7d0285c9ea2504ec148914ce90e545910fcb0bc15a552bd9353996 |
| enrollment_by_grade_level_2017.csv | a0682d6ad18e09b24ef5d02f4ab9db1295517b64e085cf7fc61c5cbe57cf2520 |
| enrollment_by_grade_level_2018.csv | 5e2f664af7e1e6793d6588b3f49ab60306b1289789b34bc2d7f3e604e3824c0e |
| enrollment_by_grade_level_2019.csv | f56b6c1652fb832ef4296c2ff03b819e9631703df8eba079913e72d7ec728d4d |
| enrollment_by_grade_level_2020.csv | 1ed73b61e2b6d9cdaec5614305b5d53892c8284e62fb94ac60d040551ae5d8ae |
| enrollment_by_grade_level_2021.csv | eb001966241a7e8aa2b3f85f6aa12791f97ef9f7e2d0d4a0f2a7d8b908d4ffcd |
| enrollment_by_grade_level_2022.csv | 0b3a54f4f7f4b295ffbe89747d48fe2abd3e6e00626ca5fcc4284f0a97bc4bfd |
| enrollment_by_grade_level_2023.csv | 15dd217ac543285276b43749b01f9aa3aeb87308fd0d543e42a5b873f16cd72d |
| enrollment_by_grade_level_2024.csv | 5c7f9040dc1284bd617d8ee6f5c5ccc77c5d95ab2384b7aef4ab369cec55150e |

## Summary

This dataset reports the number of students enrolled (`ENROLLMENT_COUNT`) at each Georgia public school, district, and the state, broken out by **grade level** (13 values: `K`, `1st` through `12th`) and **enrollment period** (`Fall` and `Spring` snapshots within the same school year). Each file represents a single school year. There is no demographic breakdown — every row is the total student count for a given (geography × grade × period) cell. Suppression behavior changes sharply over time: 2011–2020 report all values exactly (including zeros and 1–9), 2021–2022 redact cells <10 as the literal `TFS`, and 2023–2024 both redact <10 cells as `TFS` and stop emitting rows for grade × school combinations that aren't applicable (the row count drops from ~65,000/year to ~28,000/year).

## Eras

### Era 1: 2023–2024 (with `#RPT_NAME` header; sparse rows)

11 columns. Adds a leading `#RPT_NAME` column whose only value is `Enrollment_by_Grade`. Most importantly, the file no longer emits a row for every (school × grade × period) combination — only combinations that have a valid count or that are explicitly suppressed below the threshold are present. This roughly halves the file size compared with Era 2.

| Column | Description |
|--------|-------------|
| #RPT_NAME | Report name; constant `"Enrollment_by_Grade"`. Era 1 only. |
| LONG_SCHOOL_YEAR | School year as `YYYY-YY` (e.g., `2023-24`). One value per file. |
| DETAIL_LVL_DESC | Detail level: `State`, `District`, or `School` |
| SCHOOL_DSTRCT_CD | GOSA district code (3-digit standard or 7-digit charter); the literal `ALL` for state-level rows |
| SCHOOL_DSTRCT_NM | District name; the literal `All Column Values` for state-level rows |
| INSTN_NUMBER | GOSA school code (4-digit, zero-padded); the literal `ALL` for state and district rows |
| INSTN_NAME | School name; the literal `All Column Values` for state and district rows |
| GRADES_SERVED_DESC | Comma-separated grade levels served by the institution (e.g., `06,07,08`); for district rows it is the broadest span of any school in the district |
| ENROLLMENT_PERIOD | `Fall` or `Spring` — the count snapshot date within the school year |
| GRADE_LEVEL | Grade label: `K`, `1st`, `2nd`, …, `12th` (13 values) |
| ENROLLMENT_COUNT | Number of enrolled students (integer ≥10) or the suppression marker `TFS` |

#### Sample Data (2024)

| #RPT_NAME | LONG_SCHOOL_YEAR | DETAIL_LVL_DESC | SCHOOL_DSTRCT_CD | SCHOOL_DSTRCT_NM | INSTN_NUMBER | INSTN_NAME | GRADES_SERVED_DESC | ENROLLMENT_PERIOD | GRADE_LEVEL | ENROLLMENT_COUNT |
|---|---|---|---|---|---|---|---|---|---|---|
| Enrollment_by_Grade | 2023-24 | School | 748 | Ware County | 3052 | Waresboro Elementary School | KK,01,02,03,04,05 | Fall | 2nd | 80 |
| Enrollment_by_Grade | 2023-24 | School | 647 | Dougherty County | 3058 | Northside Elementary School | PK,KK,01,02,03,04,05 | Fall | 4th | 55 |
| Enrollment_by_Grade | 2023-24 | District | 786 | Social Circle City | ALL | All Column Values | PK,KK,01,02,…,12 | Fall | 4th | 149 |
| Enrollment_by_Grade | 2023-24 | School | 715 | Polk County | 0310 | Youngs Grove Elementary School | PK,KK,01,02,03,04,05 | Spring | 3rd | 71 |
| Enrollment_by_Grade | 2023-24 | School | 743 | Twiggs County | 0207 | Twiggs Middle School | 06,07,08 | Spring | 6th | 53 |

#### Statistics (2024)

- Row count: 28,501
- All columns are stored as `Utf8` (string) on read
- 0 nulls in any column
- `ENROLLMENT_COUNT` after `TFS → null` then cast to `Int64`: count=27,323; min=10; median=112; max=154,395 (Georgia state aggregate); 1,178 TFS suppressions

#### Null Counts (2024)

All 11 columns: 0 nulls. Suppressed metric values use the literal `TFS` string rather than null.

#### Categorical Columns (2024)

| Column | Distinct Count | Distinct Values (with row counts where useful) |
|--------|---------------|------------------------------------------------|
| #RPT_NAME | 1 | `Enrollment_by_Grade` (28,501) |
| LONG_SCHOOL_YEAR | 1 | `2023-24` (28,501) |
| DETAIL_LVL_DESC | 3 | `School` (22,807), `District` (5,668), `State` (26) |
| SCHOOL_DSTRCT_NM | 235 | District names. Includes the sentinel `All Column Values` for state aggregate rows. |
| INSTN_NAME | 2,200 | School names. Includes the sentinel `All Column Values` for state and district aggregate rows. |
| GRADES_SERVED_DESC | 70 | Comma-separated grade strings. Common values include `KK,01,02,03,04,05` (elementary), `06,07,08` (middle), `09,10,11,12` (high), and `PK,KK,01,02,…,12` (full-K-12 districts and the state aggregate). |
| ENROLLMENT_PERIOD | 2 | `Fall` (14,250), `Spring` (14,251) |
| GRADE_LEVEL | 13 | `K`, `1st`, `2nd`, `3rd`, `4th`, `5th`, `6th`, `7th`, `8th`, `9th`, `10th`, `11th`, `12th` (1,415–2,960 rows each in 2024) |

#### Suppression Markers (2024)

| Column | Marker | Count | Meaning |
|--------|--------|-------|---------|
| SCHOOL_DSTRCT_CD | `ALL` | 26 | State-level rows (one per period × grade) |
| INSTN_NUMBER | `ALL` | 5,694 | State and district aggregate rows |
| ENROLLMENT_COUNT | `TFS` | 1,178 | "Too few students" — cell suppressed for privacy (count <10) |

`ENROLLMENT_COUNT` is stored as a string because of the `TFS` marker; the underlying numeric values are integers ≥10 (the cell-size threshold).

### Era 2: 2011–2022 (no `#RPT_NAME` header; dense rows)

10 columns. Every (geography × grade) combination is emitted for each period in which the entity appears, even when the count is zero (2011–2020) or suppressed (2021–2022). For schools, this means each school × period contributes a full set of 13 grade rows regardless of which grades the school actually serves — for grades the school does not serve, the value is `0` in 2011–2020 or `TFS` in 2021–2022. The rectangle is per (entity, period), not per entity: a handful of entities appear in only one period in some years (verified — 2011 has 2,475 fall vs 2,481 spring entity-periods; small fall/spring imbalances also exist in 2014, 2016, 2017, and 2019; 2012, 2013, 2015, 2018, 2020, 2021, and 2022 are exactly balanced).

**2022 `School`+`ALL` sentinel twins (52 rows).** The 2022 file alone emits rows with `DETAIL_LVL_DESC = 'School'` but `INSTN_NUMBER = 'ALL'` for two single-school charter districts (7830627 Atlanta SMART Academy and 7830636 Northwest Classical Academy; 26 rows each = 2 periods × 13 grades). Verified against the file: every such row exactly duplicates the matching school-coded row's `ENROLLMENT_COUNT` for the same (district, period, grade), and neither district has any `District`-level rows in 2022 — the `ALL` row is a redundant copy of the lone school, not a district aggregate. No other year contains `School`+`ALL` rows. The transform drops these 52 rows (guarded by an exact-duplicate assertion) rather than reclassifying them, which would fabricate district facts with no bronze counterpart.

| Column | Description |
|--------|-------------|
| LONG_SCHOOL_YEAR | School year as `YYYY-YY`. One value per file. |
| DETAIL_LVL_DESC | Detail level: `State`, `District`, or `School` |
| SCHOOL_DSTRCT_CD | GOSA district code; the literal `ALL` for state-level rows |
| SCHOOL_DSTRCT_NM | District name; the literal `All Column Values` for state-level rows |
| INSTN_NUMBER | GOSA school code; the literal `ALL` for state and district rows |
| INSTN_NAME | School name; the literal `All Column Values` for state and district rows |
| GRADES_SERVED_DESC | Comma-separated grade levels served (variable) |
| ENROLLMENT_PERIOD | `Fall` or `Spring` |
| GRADE_LEVEL | Grade label: `K`, `1st`–`12th` |
| ENROLLMENT_COUNT | Enrollment count: integer (including 0), or `TFS` (in 2021–2022 only) |

**Casing quirk in 2012.** The 2012 file alone uses the column name `Enrollment_Count` (initial capital + capitalized 'C') instead of `ENROLLMENT_COUNT`. Every other Era 2 file uses upper case. The transform must handle this case mismatch (e.g., normalize column names to upper case after read).

#### Sample Data (2022 — TFS-era)

| LONG_SCHOOL_YEAR | DETAIL_LVL_DESC | SCHOOL_DSTRCT_CD | SCHOOL_DSTRCT_NM | INSTN_NUMBER | INSTN_NAME | GRADES_SERVED_DESC | ENROLLMENT_PERIOD | GRADE_LEVEL | ENROLLMENT_COUNT |
|---|---|---|---|---|---|---|---|---|---|
| 2021-22 | School | 758 | Wilkinson County | 0175 | Wilkinson County Elementary School | 03,04,05 | Spring | 8th | TFS |
| 2021-22 | School | 676 | Houston County | 0401 | Bonaire Primary School | PK,KK,01,02 | Fall | 8th | TFS |
| 2021-22 | School | 667 | Gwinnett County | 0395 | Jackson Elementary School | PK,KK,01,02,03,04,05 | Spring | 12th | TFS |
| 2021-22 | School | 891 | Department of Juvenile Justice | 4199 | Millegeville ITU | 08,09,10,11,12 | Spring | 5th | TFS |
| 2021-22 | School | 631 | Clayton County | 0307 | Unidos Dual Language School | PK,KK,01,02,03,04,05,06,07,08 | Spring | 7th | TFS |

#### Sample Data (2011 — pre-suppression)

| LONG_SCHOOL_YEAR | DETAIL_LVL_DESC | SCHOOL_DSTRCT_CD | SCHOOL_DSTRCT_NM | INSTN_NUMBER | INSTN_NAME | GRADES_SERVED_DESC | ENROLLMENT_PERIOD | GRADE_LEVEL | ENROLLMENT_COUNT |
|---|---|---|---|---|---|---|---|---|---|
| 2010-11 | District | 601 | Appling County | ALL | All Column Values | PK,KK,01,02,…,12 | Fall | K | 313 |
| 2010-11 | School | 743 | Twiggs County | 0207 | Twiggs Middle School | 06,07,08 | Fall | 1st | 0 |

#### Statistics (Era 2 row counts and suppression representation)

| Year | Rows | District rows | School rows | State rows | TFS count | Null count | Zero count | 1–9 count |
|------|------|---------------|-------------|------------|-----------|------------|------------|-----------|
| 2011 | 64,428 | 5,005 | 59,397 | 26 | 0 | 0 | 37,413 | 487 |
| 2012 | 64,610 | 5,096 | 59,488 | 26 | 0 | 0 | 37,415 | 540 |
| 2013 | 64,194 | 5,148 | 59,020 | 26 | 0 | 0 | 37,100 | 505 |
| 2014 | 63,947 | 5,148 | 58,773 | 26 | 0 | 0 | 36,866 | 483 |
| 2015 | 64,038 | 5,148 | 58,864 | 26 | 0 | 0 | 36,817 | 537 |
| 2016 | 64,311 | 5,304 | 58,981 | 26 | 0 | 0 | 36,942 | 573 |
| 2017 | 64,441 | 5,382 | 59,033 | 26 | 0 | 0 | 37,014 | 596 |
| 2018 | 64,636 | 5,382 | 59,228 | 26 | 0 | 0 | 37,088 | 636 |
| 2019 | 64,753 | 5,486 | 59,241 | 26 | 0 | 0 | 37,075 | 681 |
| 2020 | 64,818 | 5,590 | 59,202 | 26 | 0 | 0 | 37,098 | 600 |
| 2021 | 65,130 | 5,746 | 59,358 | 26 | 37,904 | 0 | 0 | 0 |
| 2022 | 65,312 | 5,720 | 59,566 | 26 | 37,917 | 0 | 0 | 0 |

For comparison (Era 1):

| Year | Rows | District rows | School rows | State rows | TFS count |
|------|------|---------------|-------------|------------|-----------|
| 2023 | 28,250 | 5,460 | 22,764 | 26 | 1,040 |
| 2024 | 28,501 | 5,668 | 22,807 | 26 | 1,178 |

#### Null Counts (Era 2)

Every column is always 0 nulls in every year. Era 2 never uses null; the absence of an enrollment value is represented as either `0` (2011–2020) or `TFS` (2021–2022).

#### Categorical Columns (2022)

| Column | Distinct Count | Notes |
|--------|---------------|-------|
| LONG_SCHOOL_YEAR | 1 | `2021-22` |
| DETAIL_LVL_DESC | 3 | `School` (59,566), `District` (5,720), `State` (26) |
| SCHOOL_DSTRCT_NM | 223 | Includes `All Column Values` sentinel |
| INSTN_NAME | 2,191 | Includes `All Column Values` sentinel |
| GRADES_SERVED_DESC | 82 | Same kinds of comma-separated grade strings as Era 1; richer set because more schools are present |
| ENROLLMENT_PERIOD | 2 | `Fall` (32,656), `Spring` (32,656) — exactly even |
| GRADE_LEVEL | 13 | Same set as Era 1; in 2022 every grade has exactly 5,024 rows (= 2,300+ school rows + 220 district rows + 2 state rows × 2 periods) |

#### Categorical Columns (2011)

| Column | Distinct Count | Notes |
|--------|---------------|-------|
| LONG_SCHOOL_YEAR | 1 | `2010-11` |
| DETAIL_LVL_DESC | 3 | `School` (59,397), `District` (5,005), `State` (26) |
| GRADE_LEVEL | 13 | Same set as Era 1; each grade has exactly 4,956 rows (13-grade rectangle per (entity, period); note Fall and Spring entity sets differ slightly — 2,475 fall vs 2,481 spring entity-periods) |
| ENROLLMENT_PERIOD | 2 | `Fall` (32,175), `Spring` (32,253) |

#### Suppression Markers (Era 2)

| Column | Marker | Years | Notes |
|--------|--------|-------|-------|
| SCHOOL_DSTRCT_CD | `ALL` | all | State-level rows |
| INSTN_NUMBER | `ALL` | all | State and district rows |
| ENROLLMENT_COUNT | `0` (real value) | 2011–2020 | Indicates "no students enrolled"; this is a true zero, not a suppression marker. Cells <10 are reported as their actual value (1–9). |
| ENROLLMENT_COUNT | `TFS` | 2021–2022 | Privacy suppression (count <10). Replaces both true zeros and small counts that were previously reported. |

## ETL Considerations

- **Three suppression regimes across years.** The transform must handle three distinct cases for `ENROLLMENT_COUNT`: (a) 2011–2020 — every value is numeric, including legitimate `0` values for grades a school doesn't serve; (b) 2021–2022 — same row layout as 2011–2020 but `0` and any value <10 are now `TFS`; (c) 2023–2024 — `TFS` only appears for cells that exist (the file no longer emits rows for irrelevant school × grade combinations). Replace `TFS` with null before casting to `Int64`. **Do not** convert literal `0` to null in 2011–2020 — those are real zeros that should remain in gold.
- **Row sparsity changed.** 2011–2022 emit a 13-grade rectangle for every (entity, period) present — about 65,000 rows/year (a few entities appear in only one period in some years, so the rectangle is per entity-period, not per entity). 2023–2024 emit only the cells that have data — about 28,000 rows/year. Anyone comparing year-over-year row counts must understand this. The grain is unchanged; only the number of "no-enrollment" rows differs.
- **2022 `School`+`ALL` twin rows must be handled.** See the Era 2 section: 52 rows in 2022 with `DETAIL_LVL_DESC='School'` and `INSTN_NUMBER='ALL'` exactly duplicate the school-coded rows of two single-school charter districts and must not survive as school rows with a NULL school code (they would violate geography-nulling rules) nor be reclassified as district aggregates (no bronze counterpart).
- **`#RPT_NAME` is Era-1-only and constant.** Drop it during read for Era 1 files (or read both eras with `infer_schema_length=0` and select the common 10 columns) so the column-set is uniform before transforming.
- **2012 column-name casing quirk.** The 2012 file alone has the metric column named `Enrollment_Count`; every other Era 2 file uses `ENROLLMENT_COUNT`. Normalize column names with `df.rename({c: c.upper() for c in df.columns})` (or similar) immediately after read so downstream code can reference one name.
- **Numeric column is stored as a string.** `ENROLLMENT_COUNT` needs an explicit cast to `Int64` after replacing `TFS` with null. Underlying values are integers; in Era 1 minimum is 10, in 2011–2020 minimum is 0.
- **Geography sentinels.** `SCHOOL_DSTRCT_CD = "ALL"`, `INSTN_NUMBER = "ALL"`, `SCHOOL_DSTRCT_NM = "All Column Values"`, and `INSTN_NAME = "All Column Values"` mark aggregate rows. Per the education domain conventions, derive `detail_level` from `DETAIL_LVL_DESC` (lower-case it: `State`/`District`/`School` → `state`/`district`/`school`) and null out `district_code` for state rows and `school_code` for state and district rows. The sentinel strings must NOT be carried into the gold fact table.
- **District code formatting.** District codes are 3-digit standard (e.g., `601`) or 7-digit strings — state-charter (`782…`), commission-charter (`783…`), and state-school (`799…`, e.g. `7991893`) codes. 7-digit codes appear in **every** year 2011–2024 (verified), not only recent files. Apply `.str.zfill(3)` (per `src/etl/education/CLAUDE.md`) — never truncate. School codes are 4 digits and need `.str.zfill(4)`. Both columns must be read as `Utf8` (avoid Polars' integer inference dropping leading zeros).
- **No demographic dimension.** This dataset has no demographic breakdown — every row is a total enrollment. The fact table will have one row per (year × geography × enrollment_period × grade_level), with no `demographic` column.
- **`ENROLLMENT_PERIOD` is a fact-level categorical.** Each school year has both a `Fall` and `Spring` snapshot of enrollment. These must be preserved as distinct rows in gold (do NOT average or sum across periods). Map `Fall`/`Spring` to a snake_case column value such as `fall`/`spring`.
- **`GRADE_LEVEL` needs normalization.** Bronze values mix a single-letter `K` (kindergarten) with ordinal-suffix strings (`1st`, `2nd`, …, `12th`). For analytical use, normalize to a sortable representation. Two reasonable options: a) store as a 2-char string (`K`, `01`, `02`, …, `12`) so alphabetical sort matches grade order with `K` first, or b) store as `Int8` with `K` mapped to `0` and `1st`–`12th` to `1`–`12`. The `data-cleaning-standards` skill should be consulted to pick a convention and apply it consistently with any other grade-keyed topics. Preserve the bronze label in `_transform_manifest.json` so reviewers can verify the mapping.
- **`GRADES_SERVED_DESC` is metadata, not a metric.** It describes which grades the institution serves and varies even within a single school across years (because of grade configuration changes). It is NOT needed in the gold fact table — `GRADE_LEVEL` already pins the row to a single grade.
- **`LONG_SCHOOL_YEAR` derivation.** Convert `YYYY-YY` to a 4-digit ending year for the gold `year` column. The filename year matches the ending year, so either source produces the same value.
- **`SCHOOL_DSTRCT_NM` and `INSTN_NAME` belong in dimension tables, not the fact table.** Per the education domain conventions, names live in `data/gold/education/_dimensions/districts.parquet` and `schools.parquet` and should be excluded from the gold fact rows (only `district_code` and `school_code` survive into the fact table).
- **State row count is constant at 26.** This equals 2 periods × 13 grades. Use this as a sanity check when validating gold output — every year should produce exactly 26 state-level fact rows.

## Gold Schema Classification

For each bronze column (across all eras), classify its role in the gold star schema:

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| #RPT_NAME | not_in_gold | — | Era 1 only; constant `"Enrollment_by_Grade"` (no information) |
| LONG_SCHOOL_YEAR | fact_key | year | Convert `YYYY-YY` → ending 4-digit year as `pl.Int32` |
| DETAIL_LVL_DESC | not_in_gold | — | Used to drive geography nulling; implicit in output filename (`states.parquet` / `districts.parquet` / `schools.parquet`) |
| SCHOOL_DSTRCT_CD | fact_key | district_code | Cast to `pl.Utf8`, `.str.zfill(3)`; null out for state rows; sentinel `ALL` → null |
| SCHOOL_DSTRCT_NM | dimension_attribute | — | `district_name` in `districts.parquet` (title case); sentinel `All Column Values` excluded |
| INSTN_NUMBER | fact_key | school_code | Cast to `pl.Utf8`, `.str.zfill(4)`; null out for state/district rows; sentinel `ALL` → null |
| INSTN_NAME | dimension_attribute | — | `school_name` in `schools.parquet` (title case); sentinel `All Column Values` excluded |
| GRADES_SERVED_DESC | not_in_gold | — | Institution-level metadata; the row's own `GRADE_LEVEL` already pins the grade |
| ENROLLMENT_PERIOD | fact_categorical | enrollment_period | Lower-case to `fall`/`spring` |
| GRADE_LEVEL | fact_categorical | grade_level | Normalize bronze labels (`K`, `1st`, …, `12th`) to a sortable representation per the data-cleaning-standards convention; record the bronze→gold mapping in `_transform_manifest.json` |
| ENROLLMENT_COUNT | fact_metric | student_count | `pl.Int64`. Replace `TFS` with null, then cast. Preserve true `0` values from 2011–2020 (do NOT convert them to null). Gold name is `student_count` per data-cleaning-standards §16 (canonical name for an enrollment-slice count; this doc originally suggested `enrollment_count`, which the vocabulary registry forbids). |