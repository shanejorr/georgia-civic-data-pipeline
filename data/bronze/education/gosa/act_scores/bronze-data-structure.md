# act_scores — Bronze Data Structure

## Overview

- Topic: act_scores
- Source: gosa
- Files: 21 files spanning 2004-2024
- Unreadable files: none
- Year representation: Era 1 (2004-2007) and Era 2 (2008-2010) have no year column (year from filename only); Eras 3 (2011-2023) and 4 (2024) carry a `LONG_SCHOOL_YEAR` column in `YYYY-YY` school-year format (e.g., `2010-11`, `2023-24`).
- Filename-to-data year offset: filename year matches the ending (spring) year of the school year (e.g., `act_scores_2011.csv` has `LONG_SCHOOL_YEAR='2010-11'`). For Era 1 and Era 2, filename year is treated as the reporting/publication year.
- Detail levels: Eras 1-2 embed state, district, and school rows in a single `SysSchoolID` column (and 2004 adds a national benchmark row). Eras 3-4 carry school-level rows only — district, state, and national aggregates appear as side-by-side columns (`DSTRCT_*`, `STATE_*`, `NATIONAL_*`) on every school row.
- Percentage scale: not applicable. This dataset reports ACT scaled scores (1-36) and counts of test takers; no percentages.
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| act_scores_2004.csv | d6b6f2fe9aec1be737950643a83789a0788470cac5f10f460e57d93718c7c204 |
| act_scores_2005.csv | 2e23dd33353affb2026b3813a24228c9e1f65021b3f7d0816eebf7b6deb0f9fb |
| act_scores_2006.xls | ee06f98b499ff4cd0aaca3f36f5a03dd30780c344aa48ceb3e51cd74c6f0018f |
| act_scores_2007.xls | 34ba45d5381c2dd0b6e9dbe80a4dd7769f240160c58590715dd575bb023fc42b |
| act_scores_2008.xls | 01d589b4c99fb6fe2c970814399197ab66c1fef0e7e6f7a07708a3e5fc004788 |
| act_scores_2009.xls | 519ece8aaa281952f93560ae78138c691c6b4da9167c72f1981bc1743017c7a2 |
| act_scores_2010.xls | c0da11ff6b78c3e610e4a862523c1f5f345ccdd956d576862200a105efb09d83 |
| act_scores_2011.csv | 6b2aee41b7dfbe2facf5e1b0e8302ad3b14f71a24f14579763e0a0fab6c96ace |
| act_scores_2012.csv | 46ad56d2207de924c629806f8a7995f7733cbb68282327ee1569307da1ce658f |
| act_scores_2013.csv | 3161d588b3ac2f2aa726e43be5b3a95a762661826811b5f855927578aa73b4b2 |
| act_scores_2014.csv | 2ee5f636b50419efa49ea42b3b024c8c99069b531ceb93a30a77c95a89836b6c |
| act_scores_2015.csv | ae2d698d2ac9d9a13cc2f4132d4d22f70ab9178d17d0e0d1469e21794e885950 |
| act_scores_2016.csv | 87dfea5a4919adcc7a66b6201463aefabe205ea4f75549daab329fec1ac20714 |
| act_scores_2017.csv | afbde3a86701f381ca461bab92ec1102fbbf0d359c62304a62d3ff57fcad8f87 |
| act_scores_2018.csv | 27fff7d9678b2f0a57248e3a239b764eefd9167a194d9791143b2599f8ca1b4d |
| act_scores_2019.csv | 1ed7d2972aa4ed182a72be3d3d3016ede995716d292950a6cebbfd2f7ab18a81 |
| act_scores_2020.csv | 49e999ffdce4cafea5c2cc429ad0da38ee6a317568afac846f1b635de2296209 |
| act_scores_2021.csv | 52efe453401101359be291eb4d766d3744fddc896d894ae9bc820761f1545cc1 |
| act_scores_2022.csv | 0c25209aa3f7733cac4e70cf1e2a3126f159fcac8463f972177fb19963b1bfce |
| act_scores_2023.csv | 34333d9ef50d5ca7c7b6ccd4ec0400b30fc36b0e06d96959d49c88efdda9ea4e |
| act_scores_2024.csv | cb09591186c6fa5688d8d3d1b21547bcbd9fae6a3a8fdc6ff7c23969258bda9a |

## Excel Sheet Structure

| File(s) | Sheets | Notes |
|---------|--------|-------|
| 2006.xls, 2007.xls, 2008.xls, 2010.xls | `Sheet1` (Data), `Sheet2` (empty), `Sheet3` (empty) | Data is in `Sheet1`; `Sheet2`/`Sheet3` are empty placeholders that should be ignored. |
| 2009.xls | `ACT` (Data), `Sheet2` (empty), `Sheet3` (empty) | Data sheet is renamed from `Sheet1` to `ACT` but carries the same schema as 2008/2010. Empty sheets should be ignored. |

Reader note: 2006-2010 are legacy binary `.xls` files (BIFF). `openpyxl` cannot read them. `polars.read_excel()` with the default calamine backend reads them successfully. For explicit sheet-name inspection, use `xlrd.open_workbook()`.

## Summary

This dataset reports ACT exam results for Georgia public schools: the **average scaled score** (1-36) and **number of students tested** for each ACT section — Composite, English, Mathematics, Reading, Science (labelled "Science Reasoning" in Eras 1-2), and the Writing Subscore / Combined English-Writing where applicable. Era 3 and Era 4 also carry side-by-side **district, state, and national comparison averages** on every school row so consumers can contextualize a school's score without a follow-up query. Era 1 (2004-2007) additionally exposes demographic (race/ethnicity and sex) breakdowns of Composite/English/Math/Reading/Science Reasoning scores, but those breakdowns are populated only for the statewide and national rows; school and district rows leave those columns blank.

## Eras

### Era 1: 2004-2007

A wide, 56-column layout. Each row represents one state / district / school entity (encoded in `SysSchoolID`), with 45 score columns = 5 test components × 9 demographic subgroups, plus 9 Number-Tested columns (one per demographic subgroup). 2004-2005 are CSV; 2006-2007 are legacy binary `.xls` (BIFF).

| Column | Description |
|--------|-------------|
| SysSchoolID | Entity key in `{district_code}:{school_code}` form. Special tokens: `ALL:ALL`/`All:All` = state total; `{district_code}:ALL`/`{district_code}:All` = district total; `NATIONAL` (2004 only) = national benchmark. |
| School Name | Free-text name of the school (for school rows), district (for district rows), or `State of Georgia`/`State Of Georgia` for the state row. Empty string for the `NATIONAL` row. |
| Composite All Students | Average ACT Composite scaled score for all students. |
| Composite Asian-American/Pacific Islander | Composite score for Asian-American / Pacific Islander subgroup. |
| Composite African-American/Black | Composite score for African-American / Black subgroup. |
| Composite Female | Composite score for female students. |
| Composite Puerto Rican/Cuban/Other Hispanic | Composite score for Puerto Rican / Cuban / Other Hispanic subgroup. |
| Composite Male | Composite score for male students. |
| Composite American Indian/Alaskan Native | Composite score for American Indian / Alaskan Native subgroup. |
| Composite Caucasian-American/White | Composite score for Caucasian-American / White subgroup. |
| Composite Mexican-Amierican/Chicano/Latino | Composite score for Mexican-American / Chicano / Latino subgroup. Note the **misspelling** "Amierican" is preserved in the bronze header. |
| English All Students | Average ACT English section scaled score. |
| English {8 demographic subgroups} | English section score for each of the 8 demographic subgroups (same list as Composite). |
| Mathematics All Students | Average ACT Mathematics section scaled score. |
| Mathematics {8 demographic subgroups} | Mathematics section score for each of the 8 subgroups. The Mexican-American column name has **a double space**: `Mathematics  Mexican-Amierican/Chicano/Latino`. |
| Reading All Students | Average ACT Reading section scaled score. |
| Reading {8 demographic subgroups} | Reading section score for each of the 8 subgroups. The Mexican-American column has a **double space**: `Reading  Mexican-Amierican/Chicano/Latino`. |
| Science Reasoning All Students | Average ACT Science Reasoning section scaled score (renamed to just "Science" in Era 3/4). |
| Science Reasoning {8 demographic subgroups} | Science Reasoning score for each of the 8 subgroups. The Mexican-American column has a **double space**: `Science Reasoning  Mexican-Amierican/Chicano/Latino`. |
| All Students Number Tested | Count of students tested (all students). |
| {8 demographic subgroups} Number Tested | Number tested in each of the 8 subgroups (same subgroup list as scores). |

#### Sample Data

Representative rows from `act_scores_2004.csv` (non-null cells only):

```
Row 0 - 601:2050 / Appling County High School (school)
  Composite All Students: 18.1     English All Students: 16.9
  Mathematics All Students: 18.2   Reading All Students: 18.2
  Science Reasoning All Students: 18.4
  All Students Number Tested: 24
  (all 40 demographic score columns + 8 demographic Number Tested columns: null)

Row 1 - 601:ALL / Appling County (district)
  Same metric values as row 0; this district only has one reporting school.

Row 517 - ALL:ALL / State of Georgia (state)
  Composite All Students: 20
  Composite Asian-American/Pacific Islander: 21.8
  Composite African-American/Black: 17.2
  Composite Female: 20.1   Composite Male: 19.9
  Composite Caucasian-American/White: 21.5
  ... all 40 demographic score columns populated ...
  All Students Number Tested: 20510
  Asian-American/Pacific Islander Number Tested: 605
  African-American/Black Number Tested: 6447
  ... all 8 demographic Number Tested columns populated ...

Row 518 - NATIONAL / "" (national benchmark; 2004 only)
  Composite All Students: 20.9
  ... all demographic subgroups populated ...
  All Students Number Tested: 1171460
```

#### Statistics

2004 (representative) after casting to Float64, showing the two widely-populated columns (other columns are null on most rows):

```
shape: (9, 3)
statistic   | Composite All Students | All Students Number Tested
count       | 424                    | 519
null_count  | 95                     | 0
mean        | 19.00                  | 2360.15
std         | 1.86                   | 51424.89
min         | 14.3                   | 1
25%         | 17.8                   | 13
50%         | 18.9                   | 28
75%         | 20.2                   | 70
max         | 24.0                   | 1171460
```

Per-file row counts: 2004 = 519 × 56, 2005 = 523 × 56, 2006 = 526 × 56, 2007 = 540 × 56.

#### Null Counts

For 2004 (representative, 519 rows):

| Column group | Null count |
|--------------|------------|
| `SysSchoolID`, `School Name` | 0 |
| `{Component} All Students` (5 cols) | 95 each |
| `{Component} {each of 8 demographic subgroups}` (40 cols) | 517 each (only state+national rows populated) |
| `All Students Number Tested` | 0 |
| `{8 demographic-subgroup} Number Tested` | 517 each (only state+national rows populated) |

**2005 behavior deviation:** all 56 columns show zero true nulls, but the demographic-subgroup cells contain a single-space string (`' '`) instead of a blank. A naive `strict=False` float cast converts them to null, but a whitespace check may be needed if upstream readers trim strings.

**2006-2007:** Only the state row has any score columns populated. District and school rows have values in `{Component} All Students` (most rows), but the 40 demographic score columns and 8 demographic Number Tested columns are uniformly blank — including at the state row in 2006-2007.

#### Categorical Columns

Era 1 has no true categoricals; `SysSchoolID` and `School Name` each have 500+ distinct values. Only the **special `SysSchoolID` tokens** matter for classification:

| Column | Distinct Values (special tokens + counts) |
|--------|--------------------------------------------|
| `SysSchoolID` (2004) | `ALL:ALL` (state, 1), `NATIONAL` (national, 1), `{district}:ALL` (district totals, 173), `{district}:{school}` (schools, 344) |
| `SysSchoolID` (2005) | `All:All` (lowercase — state, 1), `{district}:All` (district totals, 175), `{district}:{school}` (schools, 347). No `NATIONAL` row. |
| `SysSchoolID` (2006) | `ALL:ALL` (state, 1), `{district}:ALL` (district totals, 174), `{district}:{school}` (schools, 351) |
| `SysSchoolID` (2007) | `ALL:ALL` (state, 1), `{district}:ALL` (district totals, 175), `{district}:{school}` (schools, 364) |
| `School Name` for the state row | `State of Georgia` (2004, 2006, 2007) or `State Of Georgia` (2005 — capitalization differs) |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| All score and count columns (2004, 2006, 2007) | (none — only nulls) |
| All 2005 score and count columns | `' '` (single space) — used in demographic-subgroup columns (which never contain actual values) and in the state row's demographic cells. |

**Implicit suppression convention for Era 1:** a row where `Composite All Students` is null but `All Students Number Tested` is small (1-15) represents a suppressed school — i.e., the school had too few test-takers to report a score. Example from 2004: `603:302 / Bacon County High School` has `null` for every score column but `All Students Number Tested = 2`. Transform should classify these as "suppressed" rather than "missing".

### Era 2: 2008-2010

A compact, 8-column layout in legacy binary `.xls` files. Demographic columns are dropped entirely, keeping only the five "All Students" scores and one count. Suppression is now marked with the literal text `Too Few Students`.

| Column | Description |
|--------|-------------|
| SysSchoolid | **Lowercase `d`** — same format as Era 1 `SysSchoolID`: `ALL:ALL` (state), `{district_code}:ALL` (district), `{district_code}:{school_code}` (school). No NATIONAL row. |
| School Name | Free-text name of school / district / state. |
| Composite All Students | Average ACT Composite scaled score. |
| English All Students | Average ACT English section scaled score. |
| Mathematics All Students | Average ACT Mathematics section scaled score. |
| Reading All Students | Average ACT Reading section scaled score. |
| Science Reasoning All Students | Average ACT Science Reasoning section scaled score. |
| All Students Number Tested | Count of students tested (already `Int64` in bronze — polars infers numeric). |

#### Sample Data

From `act_scores_2008.xls`:

```
Row 0 - 601:103 / Appling County High School (school)
  Composite: 20.8   English: 21.3   Math: 20.9   Reading: 21.3   Science Reasoning: 19.8
  Number Tested: 16

Row 1 - 601:ALL / Appling County (district)
  Same metrics as row 0 (Appling has a single reporting school)
  Number Tested: 16

Row 2 - 602:103 / Atkinson County High School (school, suppressed)
  Composite: 'Too Few Students'   English: 'Too Few Students'   ...
  Number Tested: 5

Final row - ALL:ALL / State of Georgia
  Composite: 20.6   English: 20.1   Math: 20.6   Reading: 20.9   Science Reasoning: 20.3
  Number Tested: 33238
```

#### Statistics

2008 (representative), scores cast to Float64:

```
shape: (9, 7)
statistic   | Composite  | English    | Math       | Reading    | Science    | Number Tested
count       | 479        | 479        | 479        | 479        | 479        | 543
null_count  | 64         | 64         | 64         | 64         | 64         | 0
mean        | 19.38      | 18.80      | 19.36      | 19.57      | 19.27      | 161.86
std         | 2.04       | 2.31       | 2.02       | 2.28       | 1.77       | 1441.70
min         | 14.6       | 12.4       | 15.2       | 13.4       | 15.1       | 1
max         | 25.0       | 25.1       | 25.7       | 25.2       | 24.1       | 33238
```

Per-file row counts: 2008 = 543, 2009 = 556, 2010 = 555.

#### Null Counts

All eight columns have zero true nulls in the bronze files. Missing score values are stored as the literal string `'Too Few Students'` in the five score columns (survives a `strict=False` float cast as null). `All Students Number Tested` is fully populated (including for suppressed schools).

#### Categorical Columns

No true categorical columns. The only classification-bearing tokens are the special `SysSchoolid` values: `ALL:ALL` = state, `{district}:ALL` = district, `{district}:{school}` = school. `State of Georgia` is the `School Name` for `ALL:ALL`.

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| `Composite All Students` | `Too Few Students` |
| `English All Students` | `Too Few Students` |
| `Mathematics All Students` | `Too Few Students` |
| `Reading All Students` | `Too Few Students` |
| `Science Reasoning All Students` | `Too Few Students` |
| `All Students Number Tested` | (none — `Int64`) |

Note: `All Students Number Tested` is populated even when scores are suppressed (e.g., `5`), so the marker signals "count is too low to report a reliable score", not "no students".

### Era 3: 2011-2023

A long-format, 15-column layout. Each row is a (school × test component) combination. Columns `NATIONAL_*`, `STATE_*`, `DSTRCT_*`, and `INSTN_*` appear side-by-side so every row carries the school's value plus its district, state, and national averages as context.

| Column | Description |
|--------|-------------|
| LONG_SCHOOL_YEAR | School year in `YYYY-YY` format (e.g., `2010-11`). Exactly one distinct value per file. |
| SCHOOL_DISTRCT_CD | District code. Mostly 3-digit strings (`601`-`793`). 2016+ also include 7-digit codes (`7820108`, `7820412`, `7820613`, `7830210`, `7830310`, `7991893`) for state-chartered and state-operated schools. Note the **misspelling** "DISTRCT" (missing `I`). |
| SCHOOL_DSTRCT_NM | District name (e.g., `Appling County`, `State Charter Schools- Foothills Regional`). Note the **misspelling** "DSTRCT" (missing `I`). |
| INSTN_NUMBER | School code. Mixed-length in early years (`100`, `103`, `1050`), zero-padded to 4 digits by 2023 (`0100`, `0103`, `1050`). **Not globally unique** — must combine with `SCHOOL_DISTRCT_CD` for a unique school key. |
| INSTN_NAME | School name (e.g., `Appling County High School`). |
| SUBGRP_DESC | Demographic subgroup. In every Era 3 file the only value is `All Students` — no race/ethnicity/sex breakdowns. |
| TEST_CMPNT_TYP_CD | ACT section. `Composite`, `English`, `Mathematics`, `Reading`, `Science`, `Writing Subscore`. 2011-2015 also include `Combined English Writing` (dropped starting 2016). |
| NATIONAL_NUM_TESTED_CNT | National total tested for this component (context column; constant across all rows in a file). |
| STATE_NUM_TESTED_CNT | Georgia statewide total tested. |
| DSTRCT_NUM_TESTED_CNT | District total tested for this component. `TFS` when suppressed. |
| INSTN_NUM_TESTED_CNT | School number tested for this component. `TFS` when suppressed. |
| NATIONAL_AVG_SCORE_VAL | National average scaled score. |
| STATE_AVG_SCORE_VAL | Georgia statewide average scaled score. |
| DSTRCT_AVG_SCORE_VAL | District average scaled score. Null when the district sample is too small (no text marker in Era 3). |
| INSTN_AVG_SCORE_VAL | School average scaled score. Null when the school sample is too small. |

#### Sample Data

From `act_scores_2011.csv` (one school's 5 rows, one per test component):

```
LONG_SCHOOL_YEAR | DIST | INSTN | COMPONENT                | NAT_NUM  | ST_NUM | DST_NUM | SCH_NUM | NAT_AVG | ST_AVG | DST_AVG | SCH_AVG
2010-11          | 601  | 103   | Combined English Writing | 905035   | 18162  | TFS     | TFS     | 20.8    | 19.5   | null    | null
2010-11          | 601  | 103   | Composite                | 1623112  | 28789  | 15      | 15      | 21.1    | 19.8   | 15.8    | 15.8
2010-11          | 601  | 103   | English                  | 1623112  | 28791  | 15      | 15      | 20.6    | 19.2   | 14.8    | 14.8
2010-11          | 601  | 103   | Mathematics              | 1623112  | 28791  | 15      | 15      | 21.1    | 19.9   | 16.4    | 16.4
2010-11          | 601  | 103   | Reading                  | 1623112  | 28790  | 15      | 15      | 21.3    | 20.1   | 15.5    | 15.5
```

`Combined English Writing` has a smaller `NATIONAL_NUM_TESTED_CNT` (905k vs 1.62M) because it is only reported for students who took both English and the optional Writing section.

#### Statistics

2011 (representative), numeric columns cast to Float64:

```
shape: (9, 8)
statistic   | NAT_NUM   | ST_NUM   | DST_NUM | SCH_NUM | NAT_AVG | ST_AVG | DST_AVG | SCH_AVG
count       | 2785      | 2785     | 2599    | 2431    | 2785    | 2785   | 2599    | 2431
null_count  | 0         | 0        | 186     | 354     | 0       | 0      | 186     | 354
mean        | 1.42M     | 25814    | 696     | ---     | 19.03   | 17.89  | 17.46   | 17.34
std         | 322498    | 4773     | 854     | ---     | 4.82    | 4.49   | 4.60    | 4.75
min         | 905035    | 18162    | 10      | ---     | 7.1     | 6.8    | 4.2     | 4.2
max         | 1.62M     | 28791    | 2913    | ---     | 21.3    | 20.1   | 24.5    | 28.7
```

Per-file row counts: 2011 = 2785, 2012 = 2659, 2013 = 2853, 2014 = 2957, 2015 = 3022, 2016 = 2597, 2017 = 2513, 2018 = 2495, 2019 = 2451, 2020 = 2417, 2021 = 2199, 2022 = 2413, 2023 = 2443.

#### Null Counts

For 2011:
- Identifier columns (`LONG_SCHOOL_YEAR`, `SCHOOL_DISTRCT_CD`, `SCHOOL_DSTRCT_NM`, `INSTN_NUMBER`, `INSTN_NAME`, `SUBGRP_DESC`, `TEST_CMPNT_TYP_CD`): 0 nulls
- `NATIONAL_NUM_TESTED_CNT`, `STATE_NUM_TESTED_CNT`: 0 nulls (always populated)
- `DSTRCT_NUM_TESTED_CNT`, `INSTN_NUM_TESTED_CNT`: 0 nulls (stored as `TFS` when suppressed)
- `NATIONAL_AVG_SCORE_VAL`, `STATE_AVG_SCORE_VAL`: 0 nulls
- `DSTRCT_AVG_SCORE_VAL`: 186 nulls; `INSTN_AVG_SCORE_VAL`: 354 nulls (no text marker — simply blank)

For 2023: only `DSTRCT_AVG_SCORE_VAL` (307) and `INSTN_AVG_SCORE_VAL` (621) carry nulls.

#### Categorical Columns

| Column | Distinct Values (2011 representative) |
|--------|--------------------------------------|
| `LONG_SCHOOL_YEAR` | single value per file: `2010-11` in 2011 through `2022-23` in 2023 |
| `SUBGRP_DESC` | `All Students` (only value, constant across every row in every Era 3 file) |
| `TEST_CMPNT_TYP_CD` (2011-2015) | `Combined English Writing`, `Composite`, `English`, `Mathematics`, `Reading`, `Science`, `Writing Subscore` |
| `TEST_CMPNT_TYP_CD` (2016-2023) | `Composite`, `English`, `Mathematics`, `Reading`, `Science`, `Writing Subscore` (no `Combined English Writing`) |
| `SCHOOL_DISTRCT_CD` | 175-181 distinct values per file |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| `DSTRCT_NUM_TESTED_CNT` | `TFS` |
| `INSTN_NUM_TESTED_CNT` | `TFS` |
| `NATIONAL_NUM_TESTED_CNT`, `STATE_NUM_TESTED_CNT`, `NATIONAL_AVG_SCORE_VAL`, `STATE_AVG_SCORE_VAL` | (none — always populated) |
| `DSTRCT_AVG_SCORE_VAL`, `INSTN_AVG_SCORE_VAL` | (none — suppressed values stored as null rather than a text marker) |

### Era 4: 2024

Identical to Era 3 in record grain plus two new leading columns. The score columns now also use `TFS` as a suppression marker (Era 3 used nulls for those).

| Column | Description |
|--------|-------------|
| #ASSMT_CD | Assessment code — constant `ACT` across every row. Note the **leading `#`** is a literal character in the header, not a comment marker. |
| HIGHEST_RECENT_IND | Reporting indicator — constant `Highest` across every row. Indicates scores reflect each student's highest recent ACT attempt. |
| LONG_SCHOOL_YEAR | School year (`2023-24`). |
| SCHOOL_DSTRCT_CD | **Column renamed** from Era 3's `SCHOOL_DISTRCT_CD` to `SCHOOL_DSTRCT_CD` (now matches the "DSTRCT" spelling of `SCHOOL_DSTRCT_NM`). Same content as Era 3 (3-digit and 7-digit codes). |
| SCHOOL_DSTRCT_NM | District name. |
| INSTN_NUMBER | School code, zero-padded to 4 digits. |
| INSTN_NAME | School name. |
| SUBGRP_DESC | `All Students` (only value — same as Era 3). |
| TEST_CMPNT_TYP_CD | `Composite`, `English`, `Mathematics`, `Reading`, `Science`, `Writing Subscore`. |
| NATIONAL_NUM_TESTED_CNT | National number tested. **Formatting quirk:** appears as `1374791.` (trailing period) in the raw CSV; casts cleanly to float but would fail a strict int cast. |
| STATE_NUM_TESTED_CNT | State number tested. |
| DSTRCT_NUM_TESTED_CNT | District number tested. `TFS` when suppressed. |
| INSTN_NUM_TESTED_CNT | School number tested. `TFS` when suppressed. |
| NATIONAL_AVG_SCORE_VAL | National average score. |
| STATE_AVG_SCORE_VAL | State average score. |
| DSTRCT_AVG_SCORE_VAL | District average score — **now also uses `TFS`** (Era 3 left these null). |
| INSTN_AVG_SCORE_VAL | School average score — **now also uses `TFS`**. |

#### Sample Data

From `act_scores_2024.csv`:

```
#ASSMT_CD | HIGHEST | LONG_SCHOOL_YEAR | DIST | INSTN | COMPONENT   | NAT_NUM   | ST_NUM | DST_NUM | SCH_NUM | NAT_AVG | ST_AVG | DST_AVG | SCH_AVG
ACT       | Highest | 2023-24          | 601  | 0103  | Composite   | 1374791.  | 14727  | TFS     | TFS     | 19.4    | 21     | TFS     | TFS
ACT       | Highest | 2023-24          | 601  | 0103  | English     | 1374791.  | 14727  | TFS     | TFS     | 18.6    | 20.2   | TFS     | TFS
ACT       | Highest | 2023-24          | 601  | 0103  | Mathematics | 1374791.  | 14727  | TFS     | TFS     | 19      | 20.1   | TFS     | TFS
```

#### Statistics

2024 after casting numeric columns to Float64:

```
shape: (9, 8)
statistic   | NAT_NUM   | ST_NUM   | DST_NUM | SCH_NUM | NAT_AVG | ST_AVG | DST_AVG | SCH_AVG
count       | 2402      | 2402     | 1945    | 1503    | 2402    | 2402   | 1945    | 1503
null_count  | 0         | 0        | 457     | 899     | 0       | 0      | 457     | 899
mean        | 1.23M     | 12937    | 404     | ---     | 17.48   | 18.90  | 18.66   | 19.46
std         | 349196    | 4433     | 482     | ---     | 4.62    | 5.06   | 4.97    | 4.05
min         | 369535    | 1966     | 10      | ---     | 6.1     | 6.5    | 5.4     | 5.5
max         | 1.37M     | 14727    | 1583    | ---     | 20.1    | 22.3   | 26.6    | 30.3
```

Row count: 2402.

#### Null Counts

After polars reads the CSV, `DSTRCT_NUM_TESTED_CNT`, `INSTN_NUM_TESTED_CNT`, `DSTRCT_AVG_SCORE_VAL`, and `INSTN_AVG_SCORE_VAL` all have **0 true nulls** — every suppressed value is stored as `TFS` rather than null. This is the key difference from Era 3.

#### Categorical Columns

| Column | Distinct Values |
|--------|-----------------|
| `#ASSMT_CD` | `ACT` |
| `HIGHEST_RECENT_IND` | `Highest` |
| `LONG_SCHOOL_YEAR` | `2023-24` |
| `SUBGRP_DESC` | `All Students` |
| `TEST_CMPNT_TYP_CD` | `Composite`, `English`, `Mathematics`, `Reading`, `Science`, `Writing Subscore` |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| `DSTRCT_NUM_TESTED_CNT` | `TFS` |
| `INSTN_NUM_TESTED_CNT` | `TFS` |
| `DSTRCT_AVG_SCORE_VAL` | `TFS` (new in 2024) |
| `INSTN_AVG_SCORE_VAL` | `TFS` (new in 2024) |
| `NATIONAL_*`, `STATE_*` columns | (none — always populated) |

## ETL Considerations

1. **Year column semantics.** Only Era 3 and Era 4 carry `LONG_SCHOOL_YEAR`. The ending (spring) year of the value matches the filename year (e.g., `act_scores_2011.csv` has `2010-11`). For Era 1 and Era 2, derive `year` from the filename. Normalize all eras to a single integer `year` equal to the spring/ending year.

2. **Four radically different schemas in one topic.** Era 1 (56 wide columns) must be unpivoted by test component and subgroup. Era 2 (8 columns) unpivots by test component only (no demographics). Era 3 (15 long columns) and Era 4 (17 long columns) are already long but need column-name harmonization — Era 4's `SCHOOL_DSTRCT_CD` must align with Era 3's `SCHOOL_DISTRCT_CD`, and Era 4's two extra leading columns (`#ASSMT_CD`, `HIGHEST_RECENT_IND`) must be dropped or captured as constants.

3. **Era 1 demographic data is effectively unusable at school/district level.** In 2004 only the state and national rows have demographic scores. In 2005 demographic cells are filled with `' '` (single space). In 2006-2007 demographic cells are blank everywhere, including the state row. Recommendation: drop all demographic score columns from Era 1 and retain only the "All Students" metrics; otherwise every school/district row will emit 40 null demographic facts that match nothing in the demographics dimension.

4. **`SysSchoolID` vs `SysSchoolid` capitalization.** Uppercase `D` in 2004-2007 CSV/xls, lowercase `d` in 2008-2010 xls. Transform must accept both.

5. **`ALL`/`All` capitalization in Era 1.** 2004, 2006, 2007 use `ALL:ALL` and `{district}:ALL`. 2005 uses `All:All` and `{district}:All`. Split-and-classify logic must be case-insensitive on the `ALL` token (or normalize via `.upper()`).

6. **`NATIONAL` row only exists in 2004.** 2005-2007 drop it; Era 2 has no national row; Era 3/4 encode national data as `NATIONAL_*` columns on every school row.

7. **Detail level encoding differs across eras.** Eras 1-2: encoded in `SysSchoolID` (split on `:`, classify `ALL:ALL` → state, `{d}:ALL` → district, `{d}:{s}` → school, `NATIONAL` → national). Eras 3-4: every row is a school, with district/state/national as side-by-side columns. The transform materializes three gold detail levels (`school`, `district`, `state`) using the official aggregate rows / columns — re-aggregating from school rows would undercount by ~4-18% because GOSA suppresses per-school metrics under `n<10` while the official totals are unsuppressed. National rows / `NATIONAL_*` columns are dropped (out of scope for Georgia detail levels).

8. **Score interpretation.** ACT scaled scores are 1-36. Treat out-of-range as a data quality flag. No percentage scaling applies.

9. **Suppression markers are inconsistent across eras.**
   - Era 1: null in score columns (+ positive `Number Tested`) = suppressed school. 2005 also uses `' '` (single space) in demographic cells.
   - Era 2: literal text `Too Few Students` in score columns; count remains numeric.
   - Era 3: `TFS` in `DSTRCT_NUM_TESTED_CNT` and `INSTN_NUM_TESTED_CNT`; `DSTRCT_AVG_SCORE_VAL` / `INSTN_AVG_SCORE_VAL` are null (no text marker).
   - Era 4: `TFS` in all four of `DSTRCT_NUM_TESTED_CNT`, `INSTN_NUM_TESTED_CNT`, `DSTRCT_AVG_SCORE_VAL`, `INSTN_AVG_SCORE_VAL`.
   - Transform should normalize all markers (`Too Few Students`, `TFS`, `' '`, trailing whitespace) to nulls before numeric casts.

10. **`INSTN_NUMBER` is not globally unique.** The same 4-digit code appears in multiple districts (e.g., `0101` appears in 14 different districts in 2023). The fact table school key must be composite: `(district_code, school_code)`.

11. **`INSTN_NUMBER` zero-padding is inconsistent across Era 3 years.** In 2011, codes appear as `100`, `1050` (3-4 chars). By 2023-2024 all codes are zero-padded to 4 characters. Zero-pad all Era 3/4 `INSTN_NUMBER` values to 4 chars so they compare across years, and left-pad Era 1/2 split-out school codes to 4 chars too.

12. **Column-name typos are load-bearing.** Era 3's `SCHOOL_DISTRCT_CD` (missing `I`) was renamed to Era 4's `SCHOOL_DSTRCT_CD` (now matching `SCHOOL_DSTRCT_NM`). Era 1 column names `Mathematics  Mexican-Amierican/Chicano/Latino`, `Reading  Mexican-Amierican/Chicano/Latino`, and `Science Reasoning  Mexican-Amierican/Chicano/Latino` contain **double spaces and the misspelling "Amierican"**. Unit-test the column harmonizer with these exact strings so an upstream typo "fix" doesn't silently drop data.

13. **Era 3/4 `LONG_SCHOOL_YEAR` has exactly one value per file** — derive `year` from `LONG_SCHOOL_YEAR` itself (not the filename) for these eras to catch any silent disagreement.

14. **`Combined English Writing` is a derived metric unique to 2011-2015.** Keep it as its own `test_component` value or drop it — but don't try to sum it with the other components. Its `NATIONAL_NUM_TESTED_CNT` is smaller than the other components in the same file (represents students who took both English and Writing).

15. **2024 trailing-dot number formatting.** `NATIONAL_NUM_TESTED_CNT` is `'1374791.'` (trailing period). `float(...)` works; a strict integer cast would fail. Pass through a float cast first.

16. **`School Name` for the state row differs across eras** (`State of Georgia` vs `State Of Georgia`). Classify using the ID column, never the name string.

17. **Legacy `.xls` reader choice.** 2006-2010 are BIFF `.xls`, not `.xlsx`. Polars' default calamine backend reads them. `openpyxl` does not. Use `xlrd` (or calamine) for explicit sheet-name inspection.

18. **Empty Excel sheets must be skipped.** 2006-2010 workbooks have empty `Sheet2` / `Sheet3` placeholders. Transform must explicitly select the data sheet by name (`Sheet1` for 2006-2008, 2010; `ACT` for 2009) or select by index 0.

19. **Non-school institutions exist in Era 3/4.** A handful of `INSTN_NAME`s are career centers, magnets, online campuses, alternative centers, or institutes (e.g., `William S. Hutchings Career Center`, `Gwinnett Online Campus`, `Colquitt County Achievement Center`, `Bradwell Institute`). Treat these as schools for reporting purposes — they carry their own `INSTN_NUMBER` — but flag them if the downstream consumer expects only traditional high schools.

20. **State-chartered and state-operated schools have 7-digit district codes** (`7820108`, `7820412`, `7820613`, `7830210`, `7830310`, `7991893`). These are not tied to a county district; the district "name" is the operator (e.g., `State Charter Schools- Foothills Regional`). Decide whether to: (a) exclude them from county-level rollups, (b) flag them with a `district_type` attribute in the districts dimension, or (c) keep them as-is in the fact table.

## Gold Schema Classification

Gold goal: a long-format fact table at `data/gold/education/act_scores/` partitioned by year and split by detail level into `schools.parquet` / `districts.parquet` / `states.parquet`. Keys are `year`, `district_code` (NULL for state rows), `school_code` (NULL for district and state rows), categorical `test_component`, and metric columns `avg_score`, `num_tested`. There is no `demographic` column (every row is effectively `All Students` — per data-cleaning-standards §5, omit when constant). Descriptive names move to dimension tables.

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| **Era 1 (2004-2007)** | | | |
| `SysSchoolID` / `SysSchoolid` | fact_key | `district_code` + `school_code` + `detail_level` | Split on `:`. `ALL:ALL` / `All:All` → `detail_level="state"`; `{d}:ALL` / `{d}:All` → `detail_level="district"`; `{d}:{s}` → `detail_level="school"`; `NATIONAL` (2004 only) is dropped (out of scope). Pad district to 3 chars and school to 4 chars; `null_aggregate_geography` nulls them per detail-level rules. |
| `School Name` | dimension_attribute | — | `school_name` in schools dimension (school rows) or `district_name` in districts dimension (district rows). State row name `State of Georgia` / `State Of Georgia` is not stored — it is implicit in `detail_level="state"`. |
| `Composite All Students` | fact_metric | `avg_score` (emitted with `test_component = "composite"`) | Cast via `strict=False`; treat null + positive `Number Tested` as suppressed. Applies at all three detail levels — state, district, and school rows all have populated `All Students` score columns when not suppressed. |
| `English All Students` | fact_metric | `avg_score` (`test_component = "english"`) | Same handling. |
| `Mathematics All Students` | fact_metric | `avg_score` (`test_component = "mathematics"`) | Same. |
| `Reading All Students` | fact_metric | `avg_score` (`test_component = "reading"`) | Same. |
| `Science Reasoning All Students` | fact_metric | `avg_score` (`test_component = "science"`) | Rename `Science Reasoning` → `science` to match Era 3/4. |
| `All Students Number Tested` | fact_metric | `num_tested` | Integer count. Same column feeds all three detail levels — bronze publishes one count per row regardless of detail level. |
| Composite/English/Math/Reading/Science Reasoning × 8 demographic subgroups (40 cols) | not_in_gold | — | 2004: only state+national rows populated (excluded). 2005-2007: effectively empty. Drop all 40 demographic score columns for Era 1. |
| {8 demographic-subgroup} Number Tested (8 cols) | not_in_gold | — | Same reasoning. Drop. |
| **Era 2 (2008-2010)** | | | |
| `SysSchoolid` | fact_key | `district_code` + `school_code` + `detail_level` | Same split logic as Era 1; no `NATIONAL` rows in Era 2. State / district / school rows all preserved. |
| `School Name` | dimension_attribute | — | `school_name` / `district_name` in dimensions. |
| `Composite All Students` | fact_metric | `avg_score` (`test_component = "composite"`) | `Too Few Students` → null. Populated for school, district, and state rows when not suppressed. |
| `English All Students` | fact_metric | `avg_score` (`test_component = "english"`) | Same. |
| `Mathematics All Students` | fact_metric | `avg_score` (`test_component = "mathematics"`) | Same. |
| `Reading All Students` | fact_metric | `avg_score` (`test_component = "reading"`) | Same. |
| `Science Reasoning All Students` | fact_metric | `avg_score` (`test_component = "science"`) | Same; rename component. |
| `All Students Number Tested` | fact_metric | `num_tested` | Already `Int64`. Same column populates all three detail levels. |
| **Era 3 (2011-2023)** | | | |
| `LONG_SCHOOL_YEAR` | fact_key | `year` | Parse `YYYY-YY` → ending-year integer (e.g., `2010-11` → 2011). |
| `SCHOOL_DISTRCT_CD` | fact_key | `district_code` | Keep as string; both 3-digit county and 7-digit state-chartered codes coexist. Populates the `school` and `district` detail-level rows; nulled for `state` rows. |
| `SCHOOL_DSTRCT_NM` | dimension_attribute | — | `district_name` in districts dimension. |
| `INSTN_NUMBER` | fact_key | `school_code` | Zero-pad to 4 characters. Composite key with `district_code`. Populates `school` rows only; nulled for `district` and `state` rows. |
| `INSTN_NAME` | dimension_attribute | — | `school_name` in schools dimension. |
| `SUBGRP_DESC` | not_in_gold | — | Always `All Students` in Era 2-4; no `demographic` column in gold (single-value categorical, omitted per data-cleaning-standards §5). |
| `TEST_CMPNT_TYP_CD` | fact_categorical | `test_component` | Normalize to snake_case: `Composite` → `composite`, `English` → `english`, `Mathematics` → `mathematics`, `Reading` → `reading`, `Science` → `science`, `Writing Subscore` → `writing_subscore`, `Combined English Writing` → `combined_english_writing`. |
| `INSTN_NUM_TESTED_CNT` | fact_metric | `num_tested` (school rows) | `TFS` → null; cast to nullable `Int64`. Populates `detail_level="school"` rows. |
| `INSTN_AVG_SCORE_VAL` | fact_metric | `avg_score` (school rows) | Null or `TFS` → null; cast to `Float64`. Populates `detail_level="school"` rows. |
| `DSTRCT_NUM_TESTED_CNT`, `DSTRCT_AVG_SCORE_VAL` | fact_metric | `num_tested` / `avg_score` (district rows) | Materialized as `detail_level="district"` rows via group_by + first per (year, district_code, test_component). Values are constant within their group by bronze contract; using the official aggregate avoids ~4-18% undercounts that re-aggregating from suppressed school rows would produce. |
| `STATE_NUM_TESTED_CNT`, `STATE_AVG_SCORE_VAL` | fact_metric | `num_tested` / `avg_score` (state rows) | Materialized as `detail_level="state"` rows via group_by + first per (year, test_component). Constant across every row in the file. |
| `NATIONAL_NUM_TESTED_CNT`, `NATIONAL_AVG_SCORE_VAL` | not_in_gold | — | National benchmark; out of scope for Georgia detail levels (school / district / state per `src/etl/education/CLAUDE.md`). |
| **Era 4 (2024) — all Era 3 columns plus:** | | | |
| `#ASSMT_CD` | not_in_gold | — | Constant `ACT`; embedded in the topic name. Capture in `_metadata.json` if needed. |
| `HIGHEST_RECENT_IND` | not_in_gold | — | Constant `Highest`; capture in `_metadata.json` as a methodology note if consumers care about score-reporting rules. |
| `SCHOOL_DSTRCT_CD` | fact_key | `district_code` | Same role as Era 3's `SCHOOL_DISTRCT_CD`; harmonize the column name (and recognize the spelling differs from Era 3). |
