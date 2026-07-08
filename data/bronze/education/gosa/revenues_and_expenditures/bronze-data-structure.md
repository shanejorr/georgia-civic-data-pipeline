# revenues_and_expenditures — Bronze Data Structure

## Overview

- Topic: revenues_and_expenditures
- Source: gosa
- Files: 14 CSV files spanning filename years 2011–2024 (school years 2010-11 through 2023-24)
- Unreadable files: none
- Year representation: Each file contains a year column with the school year in `YYYY-YY` format (`SCHOOL_YEAR` in Era 2–4, `LONG_SCHOOL_YEAR` in Era 1). The filename also encodes the year as the spring (end) year of the school year. One year per file.
- Filename-to-data year offset: Filename year = spring year of the school year (e.g., `revenues_and_expenditures_2024.csv` contains `2023-24`). The data-year convention we use is the spring year (same as filename), so filename year = gold `year`.
- Detail levels: State, District, School, and (Era 1 only) `DOE OTHER` — specialty programs / centers / administrative units that are neither a traditional district nor a traditional school. In Era 2–4 detail level must be derived from the `ALL` markers in `DISTRICT_CODE` / `SCHOOL_CODE`; in Era 1 it is an explicit `DETAIL_LVL_DESC` column.
- Percentage scale: N/A — all metrics are monetary (dollars) or counts (FTE), not percentages.
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| revenues_and_expenditures_2011.csv | 3dfda763e3e9a31a853b8d8e4bed156db50490a0c6ae812830d805a9480ca235 |
| revenues_and_expenditures_2012.csv | fbe07d2c154176aec5a9e3d97fece5cc90db1dc67ee209f926a9ade642f51b93 |
| revenues_and_expenditures_2013.csv | 3905231df4d692ae29f69e961fb307be5d37b7946e0a56b2b3196f240fb45af8 |
| revenues_and_expenditures_2014.csv | a62ce51a3a2d0c347e08e6eeded449f098967299b5efb440518bbf565eb184b0 |
| revenues_and_expenditures_2015.csv | 3f96007fca1b5fa52493774b839cc077c2e319629709c76bbef8140a9d9fd543 |
| revenues_and_expenditures_2016.csv | b26c9898387f652773fed3f62835ba3ea379d908bcab14e18586a6e2bf29548b |
| revenues_and_expenditures_2017.csv | 4ec2a3b000781c7ac78901e0bacfae8d0976517e73bac5f9608af78f23ac4cb9 |
| revenues_and_expenditures_2018.csv | 1b1ee3113f50245e06a27d9096502c97f6f61cc74bbb59bbe4067f668af9573a |
| revenues_and_expenditures_2019.csv | 075e8314fcdbdc74b06401b6331960fb54905bed171e37f704101b38bee93101 |
| revenues_and_expenditures_2020.csv | ea9180fd11e5fe3b70668f2a37ac7d7673ff0845cc6c93a770ff643daad5a27a |
| revenues_and_expenditures_2021.csv | 448172b6a3424e4519d53091d6250473bd198b60c174f8dcff05c5249dbc4d66 |
| revenues_and_expenditures_2022.csv | 8720615e0ca9f8590a88e5d11d8c65a3c0398e06d5292f146d3fb7400f60969d |
| revenues_and_expenditures_2023.csv | fd86e06b0d74f6a7810c87d38ac448c91c12aeb62a29149341469a44f13f2bd2 |
| revenues_and_expenditures_2024.csv | dd720d9da37f2ac2a670b164e2904d7a6a83c2fcc066786f0752cd35da0fcd82 |

## Summary

Georgia Department of Education financial reporting, split into **K-12 Revenues** and **K-12 Expenditures** rows, broken out by 17 functional categories (Instruction, Debt Services, General Administration, Transportation, Federal, Local, State QBE, State Lottery, Media, Pupil Services, School Administration, School food Services, Instructional Support, Renovation and Capital Projects, Maintenance and Operations, State Other, Other). Each row reports two metrics for a given functional category: `REV_EXP_VALUE` (total dollars) and `Dollars per FTE` (per-student amount). In Era 3 (filename years 2012–2014) a per-row `FTE_COUNT` column was additionally reported. Values are reported at state, district, and school detail levels, plus a `DOE OTHER` detail level (Era 1 only, 2023–2024) for specialty programs / centers / RESA administrative units.

## Eras

Four contiguous eras by column-name identity (newest first). Era 2 and Era 4 share the same 9-column schema; Era 3 inserts an `FTE_COUNT` column for three years, and Era 1 is a wholesale rename with two additional columns (`DETAIL_LVL_DESC`, `GRADES_SERVED_DESC`) plus a constant `#RPT_NAME` report-name column.

### Era 1: Filename years 2023–2024 (school years 2022-23 and 2023-24)

12-column schema. Columns renamed (`SCHOOL_YEAR` → `LONG_SCHOOL_YEAR`, `DISTRICT_CODE` → `SCHOOL_DSTRCT_CD`, `DISTRICT_NAME` → `SCHOOL_DSTRCT_NM`, `SCHOOL_CODE` → `INSTN_NUMBER`, `SCHOOL_NAME` → `INSTN_NAME`, `Description` → `DESCRIPTION`, `Revenues/Expenditures` → `REVENUES/EXPENDITURES`, `Dollars per FTE` → `DOLLARS_PER_FTE`). New columns: `#RPT_NAME` (constant), `DETAIL_LVL_DESC` (explicit detail-level), `GRADES_SERVED_DESC` (school-level only). `FTE_COUNT` from Era 3 is not present.

| Column | Description |
|--------|-------------|
| #RPT_NAME | Report-name constant — always `Revenue_and_Expenditures`. The leading `#` comes from the upstream report format. |
| LONG_SCHOOL_YEAR | School year in `YYYY-YY` format (e.g., `2023-24`). Constant within file. |
| DETAIL_LVL_DESC | Detail level of the row — one of `State`, `District`, `School`, `DOE OTHER`. |
| SCHOOL_DSTRCT_CD | 3-digit Georgia district code, zero-padded (stored as string). `ALL` on state-level rows. |
| SCHOOL_DSTRCT_NM | District name (title case). `All Column Values` on state-level rows. |
| INSTN_NUMBER | 4-digit institution number, zero-padded (stored as string). `ALL` on state-level and district-level rows. |
| INSTN_NAME | Institution name (title case). `All Column Values` on aggregate rows. |
| GRADES_SERVED_DESC | Comma-delimited list of grades served by the school (e.g., `09,10,11,12`, `PK,KK,01,02,03,04,05`). Describes the school, not the row. Null on State, District, and most DOE OTHER rows (9,798 nulls out of 39,631 in 2023-24). |
| REVENUES/EXPENDITURES | Top-level bucket — either `K-12 Revenues` or `K-12 Expenditures`. |
| DESCRIPTION | Functional category within the bucket (17 distinct values — same set as all other eras). |
| REV_EXP_VALUE | Dollar amount (Float64). Can be negative (adjustments). |
| DOLLARS_PER_FTE | Per-FTE dollar amount (Float64). Can be negative. See ETL Considerations about DOE OTHER rows where this metric equals `REV_EXP_VALUE`. |

#### Sample Data (2023-24 representative file, 5 random rows)

```
| #RPT_NAME                | LONG_SCHOOL_YEAR | DETAIL_LVL_DESC | SCHOOL_DSTRCT_CD | SCHOOL_DSTRCT_NM        | INSTN_NUMBER | INSTN_NAME                     | GRADES_SERVED_DESC      | REVENUES/EXPENDITURES | DESCRIPTION    | REV_EXP_VALUE | DOLLARS_PER_FTE |
| Revenue_and_Expenditures | 2023-24          | School          | 625              | Savannah-Chatham County | 4052         | Bloomingdale Elementary School | PK,KK,01,02,03,04,05    | K-12 Expenditures     | Media          | 96247.94      | 96247.94        |
| Revenue_and_Expenditures | 2023-24          | DOE OTHER       | 644              | DeKalb County           | 6015         | International Student Center   | null                    | K-12 Expenditures     | Debt Services  | 0.0           | 0.0             |
| Revenue_and_Expenditures | 2023-24          | School          | 755              | Whitfield County        | 3050         | Dawnville Elementary School    | PK,KK,01,02,03,04,05    | K-12 Expenditures     | Transportation | 0.0           | 0.0             |
| Revenue_and_Expenditures | 2023-24          | School          | 705              | Murray County           | 0104         | Woodlawn Elementary School     | PK,KK,01,02,03,04,05,06 | K-12 Expenditures     | Instruction    | 3.96e6        | 3.96e6          |
| Revenue_and_Expenditures | 2023-24          | School          | 721              | Richmond County         | 0177         | Meadowbrook Elementary School  | PK,KK,01,02,03,04,05    | K-12 Expenditures     | Media          | 133149.89     | 133149.89       |
```

#### Statistics (2023-24)

```
shape: (39631, 12)

REV_EXP_VALUE
  count: 39,631    null_count: 0
  mean:  2.90e6    std: 1.11e8
  min:  -1.20e6    max: 1.44e10    (max is state-total Instruction)

DOLLARS_PER_FTE
  count: 39,631    null_count: 0
  mean:  578,753.76    std: 2.54e6
  min:  -1.20e6    max: 1.46e8
```

The anomalously large `DOLLARS_PER_FTE` values come from rows where the metric equals `REV_EXP_VALUE` verbatim. In the 2023-24 file this artifact covers the **entire school detail level** — every nonzero `School` row (15,678 of 15,678) **and** every `DOE OTHER` row — not just DOE OTHER; `District` and `State` rows carry true per-FTE values. In the 2022-23 file it covers all DOE OTHER rows plus 151 nonzero School rows (verified 2026-06-12; see ETL Considerations).

#### Null Counts (2023-24)

| Column | Nulls |
|--------|-------|
| GRADES_SERVED_DESC | 9,798 |
| All others | 0 |

Detail-level breakdown of nulls: 17 State, 3,944 District, 25,872 School, 9,798 DOE OTHER rows. `GRADES_SERVED_DESC` is populated only on school rows (and even then may be missing for some DOE OTHER rows that carry a grades-served value).

#### Categorical Columns (2023-24)

| Column | Distinct Values |
|--------|----------------|
| #RPT_NAME | 1: `Revenue_and_Expenditures` |
| LONG_SCHOOL_YEAR | 1: `2023-24` (single year per file) |
| DETAIL_LVL_DESC | 4: `DOE OTHER` (9,798), `District` (3,944), `School` (25,872), `State` (17) |
| REVENUES/EXPENDITURES | 2: `K-12 Expenditures`, `K-12 Revenues` |
| DESCRIPTION | 17: `Debt Services`, `Federal`, `General Administration`, `Instruction`, `Instructional Support`, `Local`, `Maintenance and Operations`, `Media`, `Other`, `Pupil Services`, `Renovation and Capital Projects`, `School Administration`, `School food Services`, `State Lottery`, `State Other`, `State QBE`, `Transportation` (same set across every era) |
| GRADES_SERVED_DESC | 78 distinct grade-span combinations, comma-delimited |
| SCHOOL_DSTRCT_NM | 247 distinct (includes `All Column Values` for state-level rows) |
| INSTN_NAME | 2,453 distinct (includes `All Column Values` for aggregate rows) |

#### Suppression Markers (2023-24)

| Column | Non-Numeric Values |
|--------|-------------------|
| SCHOOL_DSTRCT_CD | `ALL` (state-level aggregate marker, not a suppression marker) |
| INSTN_NUMBER | `ALL` (state-level and district-level aggregate marker, not a suppression marker) |

No numeric suppression markers (`*`, `TFS`, `N/A`, etc.) appear in `REV_EXP_VALUE` or `DOLLARS_PER_FTE` — both parse cleanly as Float64.

### Era 2: Filename years 2015–2022 (school years 2014-15 through 2021-22)

9-column schema. Identical columns to Era 4 (2011 file) — the `FTE_COUNT` column that appeared in Era 3 was removed starting 2014-15.

| Column | Description |
|--------|-------------|
| SCHOOL_YEAR | School year in `YYYY-YY` format (e.g., `2021-22`). Constant within file. |
| DISTRICT_CODE | 3-digit Georgia district code, zero-padded (stored as string). `ALL` on state-level rows. |
| DISTRICT_NAME | District name (title case). `All Column Values` on state-level rows. |
| SCHOOL_CODE | 4-digit school/institution code, zero-padded (stored as string). `ALL` on state-level and district-level rows. |
| SCHOOL_NAME | School name (title case). `All Column Values` on aggregate rows. |
| Revenues/Expenditures | Top-level bucket — `K-12 Revenues` or `K-12 Expenditures`. |
| Description | Functional category (same 17 values as every era). |
| REV_EXP_VALUE | Dollar amount (Float64). |
| Dollars per FTE | Per-FTE dollar amount (Float64). No nulls in this era. |

#### Sample Data (2021-22 representative file, 5 random rows)

```
| SCHOOL_YEAR | DISTRICT_CODE | DISTRICT_NAME    | SCHOOL_CODE | SCHOOL_NAME                     | Revenues/Expenditures | Description                | REV_EXP_VALUE | Dollars per FTE |
| 2021-22     | 785           | Rome City        | ALL         | All Column Values               | K-12 Expenditures     | School Administration      | 4.78e6        | 721.62          |
| 2021-22     | 644           | DeKalb County    | 1059        | Idlewood Elementary School      | K-12 Expenditures     | School food Services       | 0.0           | 0.0             |
| 2021-22     | 755           | Whitfield County | 4050        | Dug Gap Elementary School       | K-12 Expenditures     | Maintenance and Operations | 103374.77     | 279.39          |
| 2021-22     | 704           | Morgan County    | 0191        | Morgan County Elementary School | K-12 Expenditures     | School Administration      | 377969.47     | 550.98          |
| 2021-22     | 721           | Richmond County  | 0103        | Freedom Park Elementary         | K-12 Expenditures     | Instruction                | 4.08e6        | 6696.37         |
```

#### Statistics (2021-22)

```
shape: (39350, 9)

REV_EXP_VALUE
  count: 39,350    null_count: 0
  mean:  2.42e6    std: 9.42e7
  min:  -1.48e6    max: 1.20e10    (max is state-total Instruction)

Dollars per FTE
  count: 39,350    null_count: 0
  mean:  107,736.78    std: 1.50e6
  min:  -1.48e6    max: 1.22e8
```

Row counts across the era range from 28,391 (2014-15) to 40,757 (2018-19). The large `Dollars per FTE` maxima come from aggregate / non-school rows where the metric tends to equal `REV_EXP_VALUE`.

#### Null Counts (2021-22)

All 9 columns: 0 nulls in 39,350 rows. The null-free pattern holds across every year in this era (confirmed for 2015, 2019, 2021, 2022).

#### Categorical Columns (2021-22)

| Column | Distinct Values |
|--------|----------------|
| SCHOOL_YEAR | 1: `2021-22` (single year per file; each year of the era has the appropriate `YYYY-YY` value) |
| Revenues/Expenditures | 2: `K-12 Expenditures`, `K-12 Revenues` |
| Description | 17: same set as Era 1 |
| DISTRICT_NAME | 237 distinct (includes `All Column Values`) — count varies slightly year to year |
| SCHOOL_NAME | 2,440 distinct (includes `All Column Values`) — count varies year to year |

#### Suppression Markers (2021-22)

| Column | Non-Numeric Values |
|--------|-------------------|
| DISTRICT_CODE | `ALL` (aggregate marker only) |
| SCHOOL_CODE | `ALL` (aggregate marker only) |

No numeric suppression markers.

### Era 3: Filename years 2012–2014 (school years 2011-12 through 2013-14)

10-column schema. Same as Era 2 / Era 4 **plus** an `FTE_COUNT` column (Int64). This is the only era in which per-row FTE counts are reported.

| Column | Description |
|--------|-------------|
| SCHOOL_YEAR | School year in `YYYY-YY` format. |
| DISTRICT_CODE | Same as Era 2. 3-digit, zero-padded. `ALL` on state-level rows. |
| DISTRICT_NAME | Same as Era 2. `All Column Values` on state-level rows. |
| SCHOOL_CODE | Same as Era 2. 4-digit, zero-padded. `ALL` on state-level and district-level rows. (In 2011-12 a minority of SCHOOL_CODE values are upstream-published as 3-digit such as `110`, `106` without a leading zero — these are the same schools that appear as `0110`, `0106` in Era 2–4 and in the schools dimension, so the transform zero-pads them to 4 digits via `.str.zfill(4)` to keep the FK consistent across eras.) |
| SCHOOL_NAME | Same as Era 2. |
| Revenues/Expenditures | Top-level bucket (`K-12 Revenues` or `K-12 Expenditures`). |
| Description | Same 17 functional categories as every era. |
| REV_EXP_VALUE | Dollar amount (Float64). |
| Dollars per FTE | Per-FTE dollar amount (Float64). May be null — but the null relationship to FTE_COUNT differs by year (verified 2026-06-12): in 2012-13 (382 nulls) and 2013-14 (272 nulls) it is null exactly when FTE_COUNT is null; in 2011-12 the 10,414 null-FTE_COUNT rows instead carry a *populated* `Dollars per FTE` equal to `REV_EXP_VALUE` verbatim (the same un-normalized artifact as Era 1 DOE OTHER rows), and the file's only 13 nulls occur on rows with `FTE_COUNT = 0` (Northwoods Academy School / Bibb County, T. Carl Buice School / Gwinnett County; the other 20 zero-FTE rows have value 0 and per-FTE 0). Total per-FTE nulls across the era: 667. |
| FTE_COUNT | Full-time-equivalent student count at the row's detail level (Int64). Typically the same value repeats across the ~34 rev/exp rows for a given entity. Null for non-school / central-office entities where FTE is not defined. In 2011-12, 10,414 rows have null FTE_COUNT (out of 38,973); in 2012-13, 382 rows (out of 28,541); in 2013-14, 272 rows (out of 28,375). |

Verified relationship: for rows with non-null, non-zero `FTE_COUNT`, `Dollars per FTE ≈ REV_EXP_VALUE / FTE_COUNT` (max observed |diff| = 0.005 on 2012-13, consistent with round-to-two-decimals in the upstream report).

#### Sample Data (2012-13 representative file, 5 random rows)

```
| SCHOOL_YEAR | DISTRICT_CODE | DISTRICT_NAME   | SCHOOL_CODE | SCHOOL_NAME                                    | Revenues/Expenditures | Description                     | REV_EXP_VALUE | Dollars per FTE | FTE_COUNT |
| 2012-13     | 712           | Pickens County  | 0189        | Pickens County Middle School                   | K-12 Expenditures     | Instructional Support           | 9897.31       | 20.53           | 482       |
| 2012-13     | 638           | Coweta County   | 0103        | Willis Road Elementary                         | K-12 Expenditures     | Pupil Services                  | 261915.95     | 358.79          | 730       |
| 2012-13     | 755           | Whitfield County| 0206        | Beaverdale Elementary School                   | K-12 Expenditures     | Instruction                     | 2.39e6        | 5441.24         | 440       |
| 2012-13     | 689           | Liberty County  | 0189        | Joseph Martin Elementary School                | K-12 Expenditures     | Maintenance and Operations      | 249670.85     | 423.17          | 590       |
| 2012-13     | 888           | Okefenokee RESA | ALL         | All Column Values                              | K-12 Revenues         | State Other                     | 510618.0      | null            | null      |
```

#### Statistics (2012-13)

```
shape: (28541, 10)

REV_EXP_VALUE
  count: 28,541    null_count: 0
  mean:  2.15e6    std: 7.63e7
  min:  -4.86e7    max: 8.68e9

Dollars per FTE
  count: 28,159    null_count: 382
  mean:  613.69    std: 1,842.19
  min:  -2,743.80    max: 147,834.75

FTE_COUNT
  count: 28,159    null_count: 382
  mean:  2,673.06    std: 41,785.10
  min:  3    max: 1,679,589    (max is state-level FTE)
```

#### Null Counts (2012-13)

| Column | Nulls |
|--------|-------|
| Dollars per FTE | 382 |
| FTE_COUNT | 382 |
| All others | 0 |

The same 382 rows have both `Dollars per FTE` and `FTE_COUNT` null simultaneously — entities whose FTE count is zero or undefined (typically district central offices / non-school entities).

#### Categorical Columns (2012-13)

| Column | Distinct Values |
|--------|----------------|
| SCHOOL_YEAR | 1: `2012-13` (one `YYYY-YY` per file across the era) |
| Revenues/Expenditures | 2: `K-12 Expenditures`, `K-12 Revenues` |
| Description | 17: same set as every era |
| DISTRICT_NAME | 212 distinct (includes `All Column Values`) |
| SCHOOL_NAME | 2,161 distinct (includes `All Column Values`) |

#### Suppression Markers (2012-13)

| Column | Non-Numeric Values |
|--------|-------------------|
| DISTRICT_CODE | `ALL` (aggregate marker only) |
| SCHOOL_CODE | `ALL` (aggregate marker only) |

No numeric suppression markers.

### Era 4: Filename year 2011 (school year 2010-11)

9-column schema — identical column names to Era 2 (no `FTE_COUNT`). Listed separately because it is non-contiguous with Era 2: the 2012–2014 files inserted `FTE_COUNT`, breaking contiguity.

| Column | Description |
|--------|-------------|
| SCHOOL_YEAR | `2010-11`. |
| DISTRICT_CODE | Same as Era 2. |
| DISTRICT_NAME | Same as Era 2. |
| SCHOOL_CODE | Same as Era 2. |
| SCHOOL_NAME | Same as Era 2. |
| Revenues/Expenditures | Same as Era 2. |
| Description | Same 17 categories. |
| REV_EXP_VALUE | Same as Era 2. |
| Dollars per FTE | Same as Era 2 — notably, no nulls in this year's file. |

#### Sample Data (2010-11, 5 random rows)

```
| SCHOOL_YEAR | DISTRICT_CODE | DISTRICT_NAME    | SCHOOL_CODE | SCHOOL_NAME                    | Revenues/Expenditures | Description                     | REV_EXP_VALUE | Dollars per FTE |
| 2010-11     | 721           | Richmond County  | 4562        | Davidson Magnet School         | K-12 Expenditures     | Debt Services                   | 0.0           | 0.0             |
| 2010-11     | 644           | DeKalb County    | 8015        | Consolidated School Nutrition  | K-12 Expenditures     | Maintenance and Operations      | 0.0           | 0.0             |
| 2010-11     | 755           | Whitfield County | 8013        | Maintenance Facility           | K-12 Expenditures     | General Administration          | 0.0           | 0.0             |
| 2010-11     | 699           | Meriwether County| 0207        | Good Sheperd Therapeutic Center| K-12 Expenditures     | Renovation and Capital Projects | 0.0           | 0.0             |
| 2010-11     | 715           | Polk County      | 1054        | Goodyear Elementary School     | K-12 Expenditures     | Pupil Services                  | 0.0           | 0.0             |
```

#### Statistics (2010-11)

```
shape: (40187, 9)

REV_EXP_VALUE
  count: 40,187    null_count: 0
  mean:  1.63e6    std: 6.44e7
  min:  -3.87e6    max: 8.64e9

Dollars per FTE
  count: 40,187    null_count: 0
  mean:  81,842.98    std: 3.10e6
  min:  -3.87e6    max: 5.87e8
```

#### Null Counts (2010-11)

All 9 columns: 0 nulls in 40,187 rows.

#### Categorical Columns (2010-11)

| Column | Distinct Values |
|--------|----------------|
| SCHOOL_YEAR | 1: `2010-11` |
| Revenues/Expenditures | 2: `K-12 Expenditures`, `K-12 Revenues` |
| Description | 17: same set as every era |
| DISTRICT_NAME | 206 distinct (includes `All Column Values`) |
| SCHOOL_NAME | 2,524 distinct (includes `All Column Values`) |

#### Suppression Markers (2010-11)

| Column | Non-Numeric Values |
|--------|-------------------|
| DISTRICT_CODE | `ALL` (aggregate marker only) |
| SCHOOL_CODE | `ALL` (aggregate marker only) |

No numeric suppression markers.

## ETL Considerations

**Sheet layout.** All files are plain CSV — no Excel sheet parsing required.

**Wide schema rename in Era 1.** Era 1 (2023–2024) renamed every column and added three. The transform must map both naming conventions onto a common set of gold columns:

| Gold name | Era 2–4 bronze | Era 1 bronze |
|-----------|----------------|--------------|
| year (spring, integer) | parse from `SCHOOL_YEAR` (`YYYY-YY`) | parse from `LONG_SCHOOL_YEAR` (`YYYY-YY`) |
| district_code | `DISTRICT_CODE` | `SCHOOL_DSTRCT_CD` |
| district_name (for dims) | `DISTRICT_NAME` | `SCHOOL_DSTRCT_NM` |
| school_code | `SCHOOL_CODE` | `INSTN_NUMBER` |
| school_name (for dims) | `SCHOOL_NAME` | `INSTN_NAME` |
| rev_exp_type | `Revenues/Expenditures` | `REVENUES/EXPENDITURES` |
| category | `Description` | `DESCRIPTION` |
| rev_exp_value | `REV_EXP_VALUE` | `REV_EXP_VALUE` |
| dollars_per_fte | `Dollars per FTE` | `DOLLARS_PER_FTE` |

**Detail-level derivation (Era 2, 3, 4).** There is no `DETAIL_LVL_DESC` column before Era 1. Derive it from the `ALL` markers in the code columns:

- `district_code == 'ALL'` AND `school_code == 'ALL'` → **state**
- `district_code != 'ALL'` AND `school_code == 'ALL'` → **district**
- `district_code != 'ALL'` AND `school_code != 'ALL'` → **school**

Spot checks: 2010-11 has 17 state rows, ~3,485 district rows, ~36,685 school rows; 2021-22 has 17 state rows, 4,012 district rows, 35,321 school rows. The 17-row state count is stable across every era (one row per functional category: 17).

**`DOE OTHER` rows (Era 1 only).** In 2022-23 and 2023-24 there are ~9,800 rows per year with `DETAIL_LVL_DESC = 'DOE OTHER'`. These are special programs and centers — GNETS programs, alternative schools, virtual academies, central offices, maintenance facilities, Pre-K programs, RESA administrative units. They carry a real district code and a non-traditional institution number (`INSTN_NUMBER` frequently starts with `6`, `7`, or `8`, though some `0xxx` codes also appear). Some DOE OTHER rows are themselves district-level rollups: rows with `INSTN_NUMBER = 'ALL'` and `INSTN_NAME = 'All Column Values'` (272 rows in 2023-24) — these are RESA-style aggregates and should be excluded from the school-level fact table. Pre-Era-1 eras would have placed these same entities under the `school` detail level via the ALL-marker heuristic (the institution codes for "Central Office", "Maintenance Facility", etc. already existed in Era 2–4 data with non-ALL SCHOOL_CODE values). For apples-to-apples historical totals, be aware that the **school** slice in Era 2–4 includes these non-traditional programs while Era 1 separates them into `DOE OTHER`. The transform should either:
  - (a) map Era 1's `DOE OTHER` to `school` so that the school-level detail matches Era 2–4 conventions (simplest, keeps history comparable), OR
  - (b) add a post-hoc `doe_other` flag in Era 2–4 by matching the Era 1 DOE OTHER institution numbers (more accurate but reverse-engineered).

The `DOLLARS_PER_FTE == REV_EXP_VALUE` pattern in Era 1 is anomalous — the per-FTE metric is not truly normalized for these rows. Verified extent (2026-06-12): in the 2023-24 file the artifact covers the **entire school detail level** — every nonzero `School` row (15,678/15,678, traditional schools included) and every `DOE OTHER` row — so 2023-24 school-level per-FTE values carry no per-pupil information at all; in the 2022-23 file it covers all `DOE OTHER` rows plus 151 nonzero `School` rows. `District` and `State` rows in both Era 1 files carry true per-FTE values. Downstream consumers must be cautioned that `dollars_per_fte` is not meaningful for DOE OTHER rows in either Era 1 year, nor for ANY school-level row in 2023-24.

**Year column.** `SCHOOL_YEAR` / `LONG_SCHOOL_YEAR` is already in `YYYY-YY` form. For gold `year` (integer), take the spring year, which matches both our convention and the filename year (e.g., `2023-24` → `2024`, and the file is named `revenues_and_expenditures_2024.csv`). Cross-verified for all 14 files.

**District / school codes are zero-padded string identifiers.** They must be read as strings to preserve leading zeros (especially `INSTN_NUMBER` / `SCHOOL_CODE`, where values like `0100`, `0108`, `0111` would otherwise lose their leading zero). Polars infers them as strings in default settings because of the `ALL` values mixed in, but the transform should explicitly cast them to Utf8 to be safe. Note: in 2011-12 a minority of `SCHOOL_CODE` values are upstream-published as 3-digit (`110`, `106`, etc.) rather than 4-digit. These are the same schools that appear as `0110`, `0106` in Era 2–4 and in the schools dimension (e.g., Howard High School is `(district=611, school_code=0105)` in the dim and in 2013–2024 bronze, but appears as `105` in 2011-12 bronze), so the transform zero-pads Era 3 `SCHOOL_CODE` to 4 digits via `.str.zfill(4)` to keep the FK consistent across eras.

**District codes `ALL` vs 7-char values.** A small number of rows (~250–1,500 per year) have `DISTRICT_CODE` values that are 7 characters long. These correspond to state charter / commission schools with compound codes (e.g., "Commission Charter Schools- Atlanta Heights Charter School" in 2010-11 appears with a 7-char district code). Preserve the width as-is; do not truncate.

**`All Column Values` sentinel.** On aggregate rows the name columns hold the literal string `All Column Values`. These should not be carried into the districts / schools dimensions (the dimensions hold only real entity names). In the fact table, these rows must be identifiable by their `ALL` district_code / school_code.

**`FTE_COUNT` is partial — drop for gold.** Only Era 3 (3 of 14 years, 2012–2014) provides FTE_COUNT. Because the analytical metric we want (`dollars_per_fte`) exists in every era as its own column, dropping `FTE_COUNT` from gold is appropriate. Do not attempt to reconstruct FTE for Era 1, 2, or 4.

**`Dollars per FTE` nulls in Era 3.** The era's per-FTE nulls total 667 (13 in 2011-12, 382 in 2012-13, 272 in 2013-14), but the FTE_COUNT relationship differs by year (verified 2026-06-12): in 2012-13 and 2013-14, `Dollars per FTE` is null exactly when `FTE_COUNT` is null (district central offices / auxiliary facilities). In 2011-12, however, the 10,414 null-FTE_COUNT rows carry a *populated* `Dollars per FTE` equal to `REV_EXP_VALUE` verbatim — the same un-normalized report artifact as Era 1 DOE OTHER rows — and the file's 13 nulls instead occur where `FTE_COUNT = 0` (Northwoods Academy School / Bibb County, T. Carl Buice School / Gwinnett County; the other 20 zero-FTE rows have `REV_EXP_VALUE = 0` and per-FTE `0`). All of these are legitimate missing/undefined denominators, not suppression markers — carry nulls through as null in gold. Era 1, 2, and 4 have no nulls in the per-FTE column, but `dollars_per_fte` frequently equals `REV_EXP_VALUE` on aggregate / non-school rows, which is a report-format artifact (not a true per-pupil amount) and callers must know this when consuming the fact table.

**Negative values are real.** Both `REV_EXP_VALUE` and `Dollars per FTE` / `DOLLARS_PER_FTE` legitimately go negative (budget adjustments, corrections). Do not clamp to zero.

**No numeric suppression markers.** Unusually for GOSA data, no `*`, `TFS`, or similar string markers appear in the numeric columns. The only string sentinel is `ALL` in the code columns, which is an aggregation marker (handled above).

**No demographic breakout.** This dataset does not have a SUBGRP / demographic column. The gold fact table does not need a `demographic` FK.

**`GRADES_SERVED_DESC` (Era 1 only).** Comma-delimited grade list such as `09,10,11,12` or `PK,KK,01,02,03,04,05`. It describes the *school*, not the *row*, so it belongs in the schools dimension (or be dropped from the fact table). Null on State, District, and many DOE OTHER rows. Only Era 1 provides this, so the attribute will be null in the dimension for schools that have not yet appeared in Era 1 bronze — accept this partial coverage.

**`#RPT_NAME` (Era 1).** Constant value `Revenue_and_Expenditures` — drop from gold entirely.

**Category normalization.** The `Description` / `DESCRIPTION` column has 17 literal values that must be snake_cased carefully. Notably, `School food Services` is stored with lowercase `food` (a typo in the upstream report); normalize to `school_food_services` but flag this in the manifest since it looks like inconsistent casing. `Revenues/Expenditures` / `REVENUES/EXPENDITURES` normalizes to `k12_revenues` / `k12_expenditures`.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| SCHOOL_YEAR / LONG_SCHOOL_YEAR | fact_key | year | Parse `YYYY-YY` → integer spring year (matches filename). |
| DISTRICT_CODE / SCHOOL_DSTRCT_CD | fact_key | district_code | 3-digit zero-padded string (some 7-char compound values for commission/state charters). FK to districts dimension. Drop the `ALL` aggregate rows from the fact table (they are pre-aggregates the API can recompute). |
| DISTRICT_NAME / SCHOOL_DSTRCT_NM | dimension_attribute | — | `district_name` in districts dimension. Drop the `All Column Values` sentinel from the dimension. |
| SCHOOL_CODE / INSTN_NUMBER | fact_key | school_code | 4-digit (mostly) zero-padded string. FK to schools dimension. On district-level / state-level rows this is `ALL` — drop those rows from the school-level fact slice (gold fact rows hold only leaf-level observations). |
| SCHOOL_NAME / INSTN_NAME | dimension_attribute | — | `school_name` in schools dimension. Drop the `All Column Values` sentinel. |
| (derived) | fact_categorical | detail_level | `state` / `district` / `school` / `doe_other`. In Era 2–4 derive from `ALL` markers; in Era 1 map from `DETAIL_LVL_DESC` (`State` → `state`, `District` → `district`, `School` → `school`, `DOE OTHER` → `doe_other`). See ETL Considerations for comparability caveat between eras. |
| Revenues/Expenditures / REVENUES/EXPENDITURES | fact_categorical | rev_exp_type | Normalize to snake_case — `k12_revenues` or `k12_expenditures`. |
| Description / DESCRIPTION | fact_categorical | category | 17 functional categories. Normalize to snake_case (e.g., `school_food_services` from the literal `School food Services`). |
| REV_EXP_VALUE | fact_metric | rev_exp_value | Dollar amount, Float64. Can be negative. No scaling. |
| Dollars per FTE / DOLLARS_PER_FTE | fact_metric | dollars_per_fte | Per-FTE dollar amount, Float64. Can be negative. May be null in Era 3 (when FTE_COUNT is null). In Era 1 this equals `REV_EXP_VALUE` for DOE OTHER rows — carry through but flag in ETL docs. |
| FTE_COUNT | not_in_gold | — | Only present in Era 3 (2012–2014). Partial coverage; drop for gold. |
| GRADES_SERVED_DESC | dimension_attribute | — | Belongs in schools dimension (describes the school, not the row). Only available from Era 1, so null for schools never appearing in Era 1 bronze. |
| #RPT_NAME | not_in_gold | — | Constant `Revenue_and_Expenditures`; carries no information. |
| DETAIL_LVL_DESC | not_in_gold (direct) | — | Used to populate the derived `detail_level` gold column; the bronze column itself is not retained. |
