# georgia_student_growth_model_end_of_course — Bronze Data Structure

## Overview

- Topic: georgia_student_growth_model_end_of_course
- Source: georgiainsights
- Files: 18 Excel workbooks spanning school years 2014-2015 through 2022-2023 (data years 2015, 2016, 2017, 2018, 2019, 2023). Three detail levels (State, System, School) × six reporting years. No 2020, 2021, or 2022 files (the GSGM was not reported during those COVID-era years; a single Full-Year 2022-2023 bundle reappears in the 2023 filename).
- Unreadable files: none (all `.xls` open with `xlrd`; all `.xlsx` open with `openpyxl` / `polars.read_excel`).
- Year representation: The year is encoded **only in the filename and in a title row above the header** (row 0 of every sheet). There is no `year` column inside the data tables. Naming patterns:
  - `GSGM_EOC_YYYY_State|System|School[_Level].xls[x]` — the `YYYY` is the **spring year** of the school year (e.g., `GSGM_EOC_2015_State.xls` covers school year 2014-2015, title row reads `GSGM Georgia Milestones EOC 2015, All Students by State`). Data year = `YYYY`.
  - `SGP_EOC_Aggs_{School|State|System}_Level_2023.xlsx` — Full-Year 2022-2023 aggregate; title reads `Student Growth Percentile (SGP) Full Year 2022-2023 (Fall, Winter, Spring) Georgia Milestones End-of-Course Assessment - <subject> - <level> - November 2, 2023`. Data year = 2023.
- Filename-to-data year offset: **same** (filename year = data year = school-year end / spring year). No year column exists to double-check, but the title row in row 0 always matches the filename year.
- Detail levels: state (single row per subject), system/district (one row per district per subject, `System Code` + `System Name`), school (one row per school per subject, `Key` or `System Code` + `School Code`). Detail level is carried in the filename (`...State...`, `...System...`, `...School...`) and not in any column.
- Percentage scale: 0–100 across every era for every percentage column. In 2015-2018 the percentages are rounded integers (e.g., `87`, `50`). In 2019 and 2023 the percentages are floats with many decimal places (e.g., `91.558254` meaning 91.56%). `Median SGP` / `SGP Median` are 1–99 growth-percentile scores (integer or `.5` halves). `N Tested` / `Number Tested` / `N Received SGP` / `Number Received SGP` are raw integer student counts.
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: Georgia Insights (GaDOE) public data downloads — exact page URL not recorded at acquisition time
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| GSGM_EOC_2015_School.xls | 7d845e33d576adf367b50495340c325ecae9f3c6a0cbf6ce31badfc38a2bec2e |
| GSGM_EOC_2015_State.xls | 7da3f20308bc283e18d04b879b7b24d9fc2d26479a72847e46de00082f40a554 |
| GSGM_EOC_2015_System.xls | b40ae367c78e3f85fb73a4f3d0c36bfab29c5532ac7e3c1bc9a71c1628e08948 |
| GSGM_EOC_2016_School_Level.xls | 5b131e3affda6c0f891a7e4753cb1867aa44dcd21febbca1f12bd767b1324cf1 |
| GSGM_EOC_2016_State_Level.xls | 5f0ba911c22db335b482c84c8cb4b4493a1a7e4b598a06ca2f9f564363b7018c |
| GSGM_EOC_2016_System_Level.xls | 31cda80b75f795aaa1e3d103697cd7b15b385634d2355bae6e1a5c5dac76bfc8 |
| GSGM_EOC_2017_School_Level.xlsx | 102405050e5562f70e75c72bfbb6fff2b6c86638eeb6cfb070af0c7b8b6204ef |
| GSGM_EOC_2017_State_Level.xlsx | f5874d629c29e474ad57d21bb6036d2255cc9ab94fa7596d16bffc953d4199a3 |
| GSGM_EOC_2017_System_Level.xlsx | e95a90995a9e3aa0557cf3ddfca0f0d6f2146c3a9232a46fa2931a4a1c76a17a |
| GSGM_EOC_2018_School_Level.xlsx | 0d57ffdc059a60c0d04a8d7a27881dd566948e30a612ab5ae874ac52f3f39ef2 |
| GSGM_EOC_2018_State_Level.xlsx | 31347533647d926430b3c141f0e74b4a44b3be90195abb2ff3f5790c4a156e26 |
| GSGM_EOC_2018_System_Level.xlsx | 0204053d1aca91400036fa38ca8a98eaf6d9a8b5a6175b95ea5d3ce7ad32a942 |
| GSGM_EOC_2019_School_Level.xlsx | 5f7ec16ba45ec869be5e4118f16a37ee9312331817c45734fb6bd628f8bd4c22 |
| GSGM_EOC_2019_State_Level.xlsx | 24a455009fdc58338ef6b84b272baeb6a485a72b8ebd1b65f142860af5c2bb66 |
| GSGM_EOC_2019_System_Level.xlsx | fe99bc49179660eb0d65327066268912c27e1329fb54ad38696e33db3a98c12d |
| SGP_EOC_Aggs_School_Level_2023.xlsx | 29b98149747de32d4870b53835b7902ad83df3fe43366d0e102c6c9bec7e3375 |
| SGP_EOC_Aggs_State_Level_2023.xlsx | 2e13a832ab064d8f20eccf209771936a900a19e5aeca5d3a803acf9dad829608 |
| SGP_EOC_Aggs_System_Level_2023.xlsx | 163a891f59bf7fb68b0e8a66e10e03bd599d59ff2652368feeffdca0dd209581 |

## Excel Sheet Structure

All files store the dataset title in **row 0** and the column header in **row 1**; data starts at row 2. Read with `pl.read_excel(..., read_options={"header_row": 1})`. Subject/content-area assignment is driven either by the sheet name (most files) or by a dedicated column (combined state sheets). Every sheet across every file is a pure **Data** sheet — there are no Metadata, Legend, or Summary/Pivot sheets.

| File(s) | Sheets | Notes |
|---------|--------|-------|
| `GSGM_EOC_2015_State.xls` | 8 per-subject sheets: `EOC_9LIT_2015_State`, `EOC_AMLIT_2015_State`, `EOC_CAL_2015_State`, `EOC_AGE_2015_State`, `EOC_BIO_2015_State`, `EOC_PHY_2015_State`, `EOC_USH_2015_State`, `EOC_ECO_2015_State` | Each sheet has 1 data row. Subjects: Ninth Grade Literature & Composition, American Literature & Composition, Coordinate Algebra, Analytic Geometry, Biology, Physical Science, United States History, Economics. **Subject is both in the sheet name AND as a `Subject` value column**. |
| `GSGM_EOC_2015_System.xls` | Same 8 per-subject sheets (`EOC_{code}_2015_System`) | Each subject is in its own sheet; no `Subject` column (subject identified by sheet name). |
| `GSGM_EOC_2015_School.xls` | Same 8 per-subject sheets (`EOC_{code}_2015_School`) | Same pattern as System. |
| `GSGM_EOC_2016_State_Level.xls` | **Single combined sheet**: `EOC_2016_State` | 10 rows (one per subject). Adds Algebra I and Geometry to the 2015 subject list. Contains a `Subject` column. |
| `GSGM_EOC_2016_System_Level.xls` | 10 per-subject sheets (`EOC_{code}_2016_System`) | Subjects: 9LIT, AMLIT, CAL, AGE, ALG, GEO, BIO, PHY, USH, ECO. |
| `GSGM_EOC_2016_School_Level.xls` | 10 per-subject sheets (`EOC_{code}_2016_School`) | Same list as System. |
| `GSGM_EOC_2017_State_Level.xlsx` | Single combined sheet: `EOC_2017_State` | 6 rows. Subject list shrinks to core six (9LIT, AMLIT, CAL, AGE, ALG, GEO) — Biology, Physical Science, US History, Economics are no longer reported. |
| `GSGM_EOC_2017_System_Level.xlsx` | 6 per-subject sheets (`EOC_{code}_2017_System`) | Core six subjects only. |
| `GSGM_EOC_2017_School_Level.xlsx` | 6 per-subject sheets (`EOC_{code}_2017_School`) | Core six subjects only. |
| `GSGM_EOC_2018_State_Level.xlsx` | Single combined sheet: `EOC_2018_State` | 6 rows. Drops the `State` column (only `Subject` + metrics). Header contains embedded `\n` characters in several column names. |
| `GSGM_EOC_2018_System_Level.xlsx` | 6 per-subject sheets (`EOC_{code}_2018_System`) | Header contains embedded `\n` in several columns (`%\n Received SGP`, `Median \nSGP`, `%\n Proficient Learner and above`, `% \nTypical or High Growth`). |
| `GSGM_EOC_2018_School_Level.xlsx` | 6 per-subject sheets (`EOC_{code}_2018_School`) | **Splits `Key` into separate `System Code` + `School Code` columns** (and both come in as `i64`, unpadded — e.g., school code `103` for what 2015-2017 encoded as `0103`). |
| `GSGM_EOC_2019_State_Level.xlsx` | Single combined sheet: `EOC_2019_State` | 6 rows. `Median \nSGP` still has embedded newline, others are now clean. Metrics become **floats with many decimals** instead of rounded integers. |
| `GSGM_EOC_2019_System_Level.xlsx` | 6 per-subject sheets (`EOC_{code}_2019_System`) | `System Code` is now **string** (`'601'`) instead of int. `Above` capitalization changes (`% Proficient Learner and Above` vs previous `and above`). |
| `GSGM_EOC_2019_School_Level.xlsx` | 6 per-subject sheets (`EOC_{code}_2019_School`) | `System Code` and `School Code` are both **string** and **zero-padded** (`'601'`, `'0103'`). |
| `SGP_EOC_Aggs_State_Level_2023.xlsx` | 2 per-subject sheets: `State - Coordinate Algebra`, `State - Algebra I` | One data row per sheet. First column renamed to `Content Area`. Metric set replaced entirely (see Era 3). |
| `SGP_EOC_Aggs_System_Level_2023.xlsx` | 2 per-subject sheets: `System - Coordinate Algebra`, `System - Algebra I` | Adds `RESA` column (regional education service area). `System Code` is string. The Coordinate Algebra sheet names its RESA column with a trailing space (`'RESA '`); Algebra I uses `'RESA'`. |
| `SGP_EOC_Aggs_School_Level_2023.xlsx` | 2 per-subject sheets: `School - Coordinate Algebra`, `School - Algebra I` | Adds `RESA` column. Coordinate Algebra sheet has `Number\nReceived SGP` (embedded newline) and `'RESA '` (trailing space); Algebra I has clean `Number Received SGP` and `'RESA'`. Names are uppercased (`APPLING COUNTY HIGH SCHOOL`) unlike 2015-2019 which use title case. |

**Transform implication:** Every sheet per detail-level file must be concatenated during transform, with the subject recovered from either (a) a `Subject` / `Content Area` data column (state-level 2015-2019 + all 2023), or (b) the sheet name (every system/school file 2015-2019). Sheet-name → subject map (2015-2019):

| Sheet-name stem | Subject |
|-----------------|---------|
| `EOC_9LIT_*` | Ninth Grade Literature & Composition |
| `EOC_AMLIT_*` | American Literature & Composition |
| `EOC_CAL_*` | Coordinate Algebra |
| `EOC_AGE_*` | Analytic Geometry |
| `EOC_ALG_*` (2016+) | Algebra I |
| `EOC_GEO_*` (2016+) | Geometry |
| `EOC_BIO_*` (2015, 2016 only) | Biology |
| `EOC_PHY_*` (2015, 2016 only) | Physical Science |
| `EOC_USH_*` (2015, 2016 only) | United States History |
| `EOC_ECO_*` (2015, 2016 only) | Economics/Business/Free Enterprise (2015: `Economics`; 2016: `Economics/Business/Free Enterprise`) |

## Summary

This topic is the **Georgia Student Growth Model (GSGM / SGP)** on End-of-Course assessments. Every row provides growth-related measures for a single (state / district / school) × subject cohort:

- `Median SGP` (or `SGP Median`) — the cohort's median Student Growth Percentile on a 1–99 scale.
- `% Typical or High Growth` (2015-2019) — share of students scoring SGP ≥ 35.
- `% SGP Low Growth` / `% SGP Typical Growth` / `% SGP High Growth` (2023 only) — three-bucket split (SGP < 35, 35-65, > 65). The 2023 breakdown **replaces** the single "typical or high" percentage.
- `% Proficient Learner and above` / `% Developing Learner and above` (2015-2019 only) — achievement-level distributions on the EOC assessment itself, not growth. Dropped in 2023.
- `N Tested` / `Number Tested` — students who took the EOC assessment.
- `N Received SGP` / `Number Received SGP` — students with enough prior-year scores to receive an SGP (a subset of tested students).
- `% Received SGP` — Received SGP / Tested × 100 (not reported at all in 2023).
- `RESA` (2023 only) — regional education service area (12 values), a dimension attribute for districts/schools that is already captured elsewhere.

The 2023 report only covers **Coordinate Algebra** and **Algebra I**, while 2015-2019 reports cover six or more subjects.

## Eras

### Era 1: 2015-2017 — GSGM EOC with "typical-or-high" growth, integer percentages

**Files (9):** `GSGM_EOC_2015_{State,System,School}.xls`, `GSGM_EOC_2016_{State_Level,System_Level,School_Level}.xls`, `GSGM_EOC_2017_{State_Level,System_Level,School_Level}.xlsx`.

**Representative file for Era 1 analysis:** `GSGM_EOC_2017_School_Level.xlsx` (sheet `EOC_9LIT_2017_School`, 597 rows). School-level 2015-2016 is identical except for file format (`.xls` vs `.xlsx`) and an expanded subject list in 2015-2016 that contracts to six subjects in 2017.

#### Columns

**State-level (9 cols), 2015 only:**

| Column | Description |
|--------|-------------|
| State | Constant `Georgia`. |
| Subject | Full subject name (e.g., `Ninth Grade Literature & Composition`). Each 2015 state sheet has one row; subject also encoded in sheet name. |
| N Tested | Integer student count (students who took the EOC). |
| N Received SGP | Integer (subset of Tested that got an SGP). |
| % Received SGP | Integer 0-100 (Received SGP / Tested × 100). |
| Median SGP | Integer 1-99 (cohort median Student Growth Percentile). |
| % Proficient Learner and above | Integer 0-100 (achievement-level share on EOC). |
| % Developing Learner and above | Integer 0-100. |
| % Typical or High Growth | Integer 0-100 (share of SGP ≥ 35). |

**State-level (9 cols), 2016-2017:** same as 2015 but `N Tested` is renamed to `Number Tested`. Combined sheet with 10 rows (2016) or 6 rows (2017), one row per subject. 2015 uses 8 separate one-row sheets.

**System-level (9 cols), 2015-2017:** drops `State`, replaces `Subject` column with `System Code` (Int64, 3-digit GOSA district code) + `System Name` (title case). Retains `N Tested` through `% Typical or High Growth`. Subject identified by sheet name.

| Column | Description |
|--------|-------------|
| System Code | GOSA district code as Int64 (e.g., 601 = Appling County). |
| System Name | District display name in title case (e.g., `Appling County`). |
| N Tested | Integer. |
| N Received SGP | Integer. |
| % Received SGP | Integer 0-100 stored as string when suppressed, otherwise numeric. |
| Median SGP | Numeric (integer or `.5` halves); stored as string when suppressed. |
| % Proficient Learner and above | Numeric 0-100; string when suppressed. |
| % Developing Learner and above | Numeric 0-100; string when suppressed. |
| % Typical or High Growth | Numeric 0-100; string when suppressed. |

**School-level (10 cols), 2015-2017:** replaces `System Code` with a single combined **`Key`** column.

| Column | Description |
|--------|-------------|
| Key | Int64 composite code: `6` prefix + 3-digit system code + 4-digit school code (e.g., `6010103` = system 601, school 0103). Always 7 digits. The leading `6` is a constant prefix, not part of the district code. |
| System Name | District name (title case). |
| School Name | School display name (title case). |
| N Tested | Integer. |
| N Received SGP | Integer. |
| % Received SGP | Numeric; string when suppressed. |
| Median SGP | Numeric (integer or `.5`); string when suppressed. |
| % Proficient Learner and above | Numeric; string when suppressed. |
| % Developing Learner and above | Numeric; string when suppressed. |
| % Typical or High Growth | Numeric; string when suppressed. |

#### Sample Data

2017 School `EOC_9LIT_2017_School` sample (representative of the full Era 1 layout):

| Key | System Name | School Name | N Tested | N Received SGP | % Received SGP | Median SGP | % Proficient Learner and above | % Developing Learner and above | % Typical or High Growth |
|---|---|---|---|---|---|---|---|---|---|
| 6090291 | Ben Hill County | Fitzgerald High School | 244 | 232 | 95 | 36 | 33 | 69 | 52 |
| 6331064 | Cobb County | McEachern High School | 624 | 555 | 89 | 49 | 50 | 87 | 64 |
| 6353052 | Colquitt County | CA Gray Junior High School | 602 | 578 | 96 | 45 | 38 | 75 | 61 |
| 6690105 | Hall County | Lanier Career Academy | 19 | 9 | TFS | TFS | TFS | TFS | TFS |
| 6220198 | Carroll County | Bay Springs Middle School | 32 | 32 | 100 | 45 | 100 | 100 | 66 |

#### Statistics

Describe of `EOC_9LIT_2017_School` (597 rows) — numeric columns only; percentage columns are string-typed due to suppression markers so Polars reports counts, not quantiles:

| statistic | Key | N Tested | N Received SGP |
|---|---|---|---|
| count | 597 | 597 | 597 |
| null_count | 0 | 0 | 0 |
| mean | 6,835,700 | 239.77 | 217.66 |
| std | 551,584 | 219.88 | 197.89 |
| min | 6,010,103 | 1 | 1 |
| 25% | 6,420,109 | 50 | 43 |
| 50% | 6,671,814 | 189 | 176 |
| 75% | 7,211,052 | 387 | 351 |
| max | 8,915,001 | 1,411 | 1,192 |

2015 school `EOC_9LIT_2015_School` is similar (547 rows, `N Tested` mean ≈ 250, range 1–1,310).

#### Null Counts

Every sheet in Era 1 has **zero true nulls**. Suppressed metric values are stored as `----` (2015-2016) or `TFS` (2017), not as blanks.

#### Categorical Columns

`System Name` (distinct per sheet, e.g., 192-194 values) and `School Name` (distinct per sheet, 539-597 values) are identifier-ish categoricals but are dimension attributes — they should be resolved via the `districts` / `schools` dimension, not stored in the fact table. No fact-level categoricals beyond the subject (which is implicit in the sheet name).

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| % Received SGP | `----` (2015-2016), `TFS` (2017) |
| Median SGP | `----` (2015-2016), `TFS` (2017) |
| % Proficient Learner and above | `----` (2015-2016), `TFS` (2017), plus one literal `NULL` string in `GSGM_EOC_2017_School_Level.xlsx` |
| % Developing Learner and above | `----` (2015-2016), `TFS` (2017) |
| % Typical or High Growth | `----` (2015-2016), `TFS` (2017) |

Suppression does **not** appear in any 2015 state row (one Georgia-level row per subject, no suppressions). `N Tested` / `N Received SGP` are always numeric in Era 1 (no suppression markers).

### Era 2: 2018-2019 — GSGM EOC with "typical-or-high" growth, split System/School codes, float percentages

**Files (6):** `GSGM_EOC_2018_{State_Level,System_Level,School_Level}.xlsx`, `GSGM_EOC_2019_{State_Level,System_Level,School_Level}.xlsx`.

**Representative file for Era 2 analysis:** `GSGM_EOC_2019_School_Level.xlsx` (sheet `EOC_9LIT_2019_School`, 620 rows).

#### Columns

Same metric set as Era 1 (`% Typical or High Growth`, `% Proficient Learner and Above`, `% Developing Learner and Above`, `Median SGP`, `% Received SGP`, `N Received SGP` / `Number Received SGP`, `N Tested` / `Number Tested`). Differences from Era 1:

1. **State level drops the `State` column.** Columns become `Subject, Number Tested, Number Received SGP, % Received SGP, Median \nSGP, % ...`.
2. **System level renames counts** from `N Tested` / `N Received SGP` to `Number Tested` / `Number Received SGP`. School level keeps `N Tested` / `N Received SGP`.
3. **School level splits `Key` into separate `System Code` + `School Code`.**
   - 2018: both Int64, **NOT zero-padded** (`103` instead of `0103`).
   - 2019: both strings, **zero-padded** (`'601'`, `'0103'`).
4. **2018 headers contain embedded `\n` characters** in several column names: `%\n Received SGP`, `Median \nSGP`, `%\n Proficient Learner and above`, `% \nTypical or High Growth` (System); `% \nProficient Learner and above`, `%\n Typical or High Growth`, `Median \nSGP` (State). 2019 is mostly clean but keeps `Median \nSGP`.
5. **2019 capitalizes `Above`** in `% Proficient Learner and Above` and `% Developing Learner and Above` — 2018 keeps lowercase `above`.
6. **2019 percentage metrics are floats with many decimal places** (e.g., `91.558254` for 91.56%). 2018 still uses rounded integers (and Int64 in Polars when not suppressed).

#### Sample Data

2019 School `EOC_9LIT_2019_School` sample:

| System Code | School Code | System Name | School Name | N Tested | N Received SGP | % Received SGP | Median SGP | % Proficient Learner and Above | % Developing Learner and Above | % Typical or High Growth |
|---|---|---|---|---|---|---|---|---|---|---|
| 622 | 3050 | Carroll County | Bowdon High School | 92 | 86 | 93.478261 | 40.5 | 73.255814 | 93.023256 | 59.302326 |
| 635 | 3052 | Colquitt County | CA Gray Junior High School | 626 | 607 | 96.964856 | 67 | 55.189456 | 85.996705 | 77.594728 |
| 712 | 0189 | Pickens County | Pickens County Junior High School | 1 | TFS | TFS | TFS | TFS | TFS | TFS |
| 717 | 0114 | Putnam County | Putnam County High School | 123 | 109 | 88.617886 | 50 | 46.788991 | 89.908257 | 66.055046 |
| 622 | 0212 | Carroll County | Mt. Zion High School | 111 | 105 | 94.594595 | 71 | 76.190476 | 97.142857 | 73.333333 |

#### Statistics

Describe of `EOC_9LIT_2019_School` (620 rows) — only `N Tested` is non-string after suppression:

| statistic | N Tested |
|---|---|
| count | 620 |
| null_count | 0 |
| mean | 223.91 |
| std | 211.61 |
| min | 1 |
| 50% | 149 |
| max | 1,043 |

#### Null Counts

Zero true nulls across all Era 2 sheets (suppressions use `TFS`, not blanks). State-level files have no suppressions at all.

#### Categorical Columns

Same as Era 1 — only `System Name` / `School Name` (dimension attributes) are categorical; no fact-level categoricals beyond the implicit subject.

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| N Received SGP (2019 only) | `TFS` |
| Number Received SGP (2018) | (none — value is Int64) |
| % Received SGP | `TFS` |
| Median SGP | `TFS` |
| % Proficient Learner and Above | `TFS` |
| % Developing Learner and Above | `TFS` |
| % Typical or High Growth | `TFS` |

Suppression threshold appears to be the same as Era 1 (cohorts with < 15 students). `TFS` = "Too Few Students".

### Era 3: 2023 — Full-Year 2022-2023 SGP three-bucket growth, Math only

**Files (3):** `SGP_EOC_Aggs_{State,System,School}_Level_2023.xlsx`.

**Representative file for Era 3 analysis:** `SGP_EOC_Aggs_School_Level_2023.xlsx` (sheet `School - Algebra I`, 833 rows).

#### Columns

Complete redesign. The achievement-level percentages (`% Proficient…`, `% Developing…`) and the "typical or high" single-percent growth metric are **gone**. Replaced with a three-bucket split of SGP (`% SGP Low / Typical / High Growth`). `N Tested` and `% Received SGP` are not reported at all.

**State-level (6 cols):**

| Column | Description |
|--------|-------------|
| Content Area | Subject name: `Coordinate Algebra` or `Algebra I`. Replaces the 2015-2019 `Subject` column. |
| Number Received SGP | Integer (cohort size for growth). |
| SGP Median | Integer 1-99 (renamed from `Median SGP`). |
| % SGP Low Growth | Float 0-100 (SGP < 35). |
| % SGP Typical Growth | Float 0-100 (35 ≤ SGP ≤ 65). |
| % SGP High Growth | Float 0-100 (SGP > 65). Three percentages sum to ~100. |

**System-level (8 cols):** adds `System Code` (string), `System Name` (UPPERCASE) at the start and `RESA` (string, may be null for charter-like entities) at the end. Drops the `Content Area` column (subject identified by sheet name).

| Column | Description |
|--------|-------------|
| System Code | String, 3-digit GOSA district code (may be 7-digit for charters). |
| System Name | UPPERCASE (e.g., `APPLING COUNTY`). |
| Number Received SGP | Integer. |
| SGP Median | Numeric or `--` when suppressed. |
| % SGP Low / Typical / High Growth | Float 0-100 or `--` when suppressed. |
| RESA | One of 16 values: `CENTRAL SAVANNAH RIV`, `CHATTAHOOCHEE-FLINT`, `COASTAL PLAINS`, `FIRST DISTRICT`, `GRIFFIN`, `HEART OF GEORGIA`, `METRO`, `MIDDLE GEORGIA`, `NORTH GEORGIA`, `NORTHEAST GEORGIA`, `NORTHWEST GEORGIA`, `OCONEE`, `OKEFENOKEE`, `PIONEER`, `SOUTHWEST GEORGIA`, `WEST GEORGIA`. Null for some districts/schools (likely state charters / entities without a RESA assignment). |

**School-level (10 cols):** same as System plus `School Code` (string, zero-padded) and `School Name` (UPPERCASE).

**Header quirks unique to Era 3:**

- The Coordinate Algebra sheet names its growth-count column `Number\nReceived SGP` (embedded newline) and its RESA column `'RESA '` (trailing space). The Algebra I sheet uses clean `Number Received SGP` and `'RESA'`. Transform must normalize both.

#### Sample Data

2023 School `School - Algebra I` sample:

| System Code | School Code | System Name | School Name | Number Received SGP | SGP Median | % SGP Low Growth | % SGP Typical Growth | % SGP High Growth | RESA |
|---|---|---|---|---|---|---|---|---|---|
| 655 | 0193 | FANNIN COUNTY | FANNIN COUNTY MIDDLE SCHOOL | 27 | 28 | 51.851851852 | 33.333333333 | 14.814814815 | PIONEER |
| 761 | 4058 | ATLANTA PUBLIC SCHOOLS | FREDERICK DOUGLASS HIGH SCHOOL | 262 | 49.5 | 34.732824427 | 31.679389313 | 33.58778626 | METRO |
| 625 | 0125 | SAVANNAH-CHATHAM COUNTY | TYBEE ISLAND MARITIME ACADEMY SCHOO | 10 | -- | -- | -- | -- | FIRST DISTRICT |
| 761 | 0515 | ATLANTA PUBLIC SCHOOLS | CHARLES DREW CHARTER JA SR ACADEMY | 126 | 44.5 | 34.126984127 | 38.095238095 | 27.777777778 | METRO |
| 772 | 0378 | DALTON PUBLIC SCHOOLS | THE DALTON ACADEMY | 12 | -- | -- | -- | -- | NORTHWEST GEORGIA |

#### Statistics

Describe of `School - Algebra I` (833 rows) — only `Number Received SGP` is non-string:

| statistic | Number Received SGP | RESA (null_count) |
|---|---|---|
| count | 833 | 789 (44 nulls) |
| null_count | 0 | 44 |
| mean | 134.94 | — |
| std | 138.42 | — |
| min | 1 | — |
| 50% | 76 | — |
| max | 748 | — |

#### Null Counts

`RESA` is the only column with true nulls (44 of 833 rows in school Algebra I — state charters / similar entities outside RESA boundaries). All other columns are 0-null; suppressed rows store `--`, not null.

#### Categorical Columns

- `Content Area` (state level only): `['Algebra I', 'Coordinate Algebra']`.
- `RESA` (system / school levels): 16 distinct values listed above (truncated in one case: `CENTRAL SAVANNAH RIV` is clipped from `CENTRAL SAVANNAH RIVER`).
- Subject (implicit from sheet name for system/school): `Algebra I` or `Coordinate Algebra`.

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| SGP Median | `--` |
| % SGP Low Growth | `--` |
| % SGP Typical Growth | `--` |
| % SGP High Growth | `--` |

Note the marker changed from `TFS` to `--` between Era 2 and Era 3.

## ETL Considerations

1. **Year is filename-driven.** Parse the 4-digit year out of the filename with a regex. For `GSGM_EOC_(\d{4})_…`, year = match. For `SGP_EOC_Aggs_{level}_Level_(\d{4}).xlsx`, year = match (2023). Verify against the row-0 title string if you want belt-and-suspenders validation. There is **no** year column inside the data.

2. **Subject/content-area extraction.** For 2015 state, 2016-2019 system and school, and all 2023 system/school files, the subject is encoded in the **sheet name** and must be mapped via the stem table above. For 2016-2019 state, the subject is a `Subject` column value. For 2023 state, the column is renamed to `Content Area`. Normalize to a single `subject` column (e.g., `ninth_grade_literature`, `american_literature`, `coordinate_algebra`, `analytic_geometry`, `algebra_i`, `geometry`, `biology`, `physical_science`, `united_states_history`, `economics`). Use `Economics/Business/Free Enterprise` consistently — the 2015 `Economics` short form should be rewritten to the 2016 long form.

3. **Geography ID parsing is era-specific.**
   - 2015-2017 school uses a combined `Key` (int, 7 digits = `6` prefix + 3-digit district + 4-digit school). Split with `int_to_str(Key)[1:4]` → district, `int_to_str(Key)[4:]` → school; pad to `zfill(3)` and `zfill(4)` per the education CLAUDE. The leading `6` is a constant; do **not** keep it.
   - 2015-2017 system, 2018 system, 2018 school all have `System Code` (and `School Code`) as **Int64 without zero-padding**. Must `.cast(pl.Utf8).str.zfill(3)` / `.str.zfill(4)` or you will silently merge codes like `1` and `001` → `1` and lose joins to the districts dimension.
   - 2019 and 2023 already have `System Code` / `School Code` as zero-padded strings. Still run `.str.zfill(3)` / `.str.zfill(4)` defensively.

4. **Metric renames across eras.**
   - `N Tested` (2015-2017 all levels, 2018-2019 school) ≡ `Number Tested` (2016-2019 state, 2018-2019 system). Standardize to `num_tested`.
   - `N Received SGP` (2015-2017 all levels, 2018-2019 school) ≡ `Number Received SGP` (2018-2019 state/system, 2023 all levels). Standardize to `n_received_sgp`. Note 2023 drops `num_tested` entirely.
   - `Median SGP` (2015-2019) ≡ `SGP Median` (2023). Standardize to `sgp_median`.
   - `% Typical or High Growth` (2015-2019) **is not equivalent to** `% SGP Typical Growth` (2023). The 2015-2019 metric = % with SGP ≥ 35; 2023's `% SGP Typical Growth` = % with 35 ≤ SGP ≤ 65. Do **not** merge these into one column. Keep 2023's three-bucket split (`pct_sgp_low_growth`, `pct_sgp_typical_growth`, `pct_sgp_high_growth`) and 2015-2019's single `pct_typical_or_high_growth` as separate columns, leaving each null in the years where the other was reported.
   - `% Proficient Learner and above` / `% Developing Learner and above` (2015-2019 only) capitalize `A`bove in 2019 but not earlier. Normalize via a lowercased rename before mapping to `pct_proficient_learner_or_above` / `pct_developing_learner_or_above`.

5. **Suppression markers.**
   - Era 1 (2015-2016): `----` (four hyphens).
   - Era 1 end / Era 2 (2017-2019): `TFS` plus one stray `NULL` literal in 2017 school.
   - Era 3 (2023): `--` (two hyphens).
   - Cast percentage / Median columns with `.cast(pl.Float64, strict=False)` to convert all three markers (and the stray `NULL`) to null. Confirm via a post-cast count of null rows per column against pre-cast counts of non-numeric strings.
   - In Era 2 (2019 school only), `N Received SGP` itself can be `TFS` (suppressed), so the count column needs the same cast as the percentage columns, not a direct Int64 coercion.

6. **Embedded `\n` and trailing spaces in headers.** 2018 system / state and 2019 state have newline characters mid-column-name (`Median \nSGP`, `%\n Received SGP`, `% \nTypical or High Growth`, etc.). 2023 Coordinate Algebra sheets have `Number\nReceived SGP` and `'RESA '` (trailing space). Transform must normalize by running `.strip()` and `.replace('\n', ' ')` (and collapsing double spaces) on every column name before mapping to standard gold names.

7. **Percentage scale and precision.** Every percent column is 0-100. 2015-2018 report rounded integers (e.g., `91`); 2019 and 2023 report floats with 6+ decimal places (e.g., `91.558254`). Convert to the project standard (`0-1` float scale — see education CLAUDE, which lists scores/star ratings as exceptions but not these SGP percentages) by dividing by 100 after casting. The three 2023 bucket percentages (`% SGP Low/Typical/High Growth`) sum to ~100 but not exactly (rounding residuals), so do not force them to sum.

8. **RESA column (2023 only) is a dimension attribute, not a fact metric.** Drop from the fact table — the regional service area is a district attribute that belongs in the districts dimension (if kept at all). Also note one value is truncated to `CENTRAL SAVANNAH RIV` (bronze source error, actual region is `CENTRAL SAVANNAH RIVER`); normalize before using.

9. **System/School name casing.** 2015-2019 files use title case (`Appling County`, `Appling County High School`). 2023 files use UPPERCASE (`APPLING COUNTY`, `APPLING COUNTY HIGH SCHOOL`). Names are dimension attributes and will be resolved via `build_dimensions.py` against the authoritative title-case list; do not keep them in the fact table.

10. **Demographic dimension.** The dataset has **no demographic breakdowns** — every row is "All Students". Omit the `demographic` FK column entirely (per the global data-cleaning-standards rule: if the topic is always "All Students", leave demographic out of the fact).

11. **2023 subject coverage is a real data gap, not a transform bug.** Only Algebra I and Coordinate Algebra were reported Full-Year 2022-2023. No 2020-2022 reports exist at all (COVID). The gold fact table should reflect this: emit 2015, 2016, 2017, 2018, 2019, 2023 partitions — no empty 2020-2022 partitions.

12. **State rows already carry `State = 'Georgia'` in 2015-2017 only.** Drop that column; the state detail level is signalled by absence of `district_code` / `school_code` (per the education CLAUDE geography-nulling rule).

13. **Suppressed `% Received SGP` percentages and `Median SGP` in 2017 School:** one row has literal `NULL` string instead of `TFS` in `% Proficient Learner and above`. Treat as a suppression marker (null-out after cast).

14. **No demographic or grade split.** Unlike Georgia Milestones EOC, which breaks out by content area × learner subgroup, GSGM is only ever "All Students" at one of three detail levels × one subject. The fact grain is `(year, detail_level, district_code, school_code, subject)`.

15. **Sheet name subject mapping for the `EOC_XXXX_20YY_{Level}` pattern must be complete.** The stem codes change what they mean: `EOC_ECO_2015` was `Economics` (short) but `EOC_ECO_2016` was `Economics/Business/Free Enterprise` (long) — map both stems to the 2016 long form. `EOC_BIO`, `EOC_PHY`, `EOC_USH`, `EOC_ECO` only appear in 2015-2016.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| (filename year) | fact_key | `year` | Parsed from filename (`GSGM_EOC_(\d{4})_…` or `..._2023.xlsx`). Int32. |
| Key (2015-2017 school) | fact_key | `district_code` + `school_code` | Split `Key` into `district_code = str(Key)[1:4]` and `school_code = str(Key)[4:]`, then `.str.zfill(3)` / `.str.zfill(4)`. The leading `6` is a constant prefix; discard. |
| System Code (2015-2019, 2023, all non-state) | fact_key | `district_code` | Cast Int64 → Utf8, `.str.zfill(3)` (preserves 7-digit charter codes). |
| School Code (2018-2019, 2023 school) | fact_key | `school_code` | Cast Int64 → Utf8, `.str.zfill(4)`. |
| (sheet name stem) / Subject / Content Area | fact_categorical | `subject` | Normalize all three sources to snake_case values: `ninth_grade_literature`, `american_literature`, `coordinate_algebra`, `analytic_geometry`, `algebra_i`, `geometry`, `biology`, `physical_science`, `united_states_history`, `economics_business_free_enterprise`. |
| State (2015-2017 state) | not_in_gold | — | Constant `Georgia`. Detail level signalled by geography nulling. |
| System Name | dimension_attribute | — | `district_name` in districts dimension (already present via `build_dimensions.py`). Drop from fact. |
| School Name | dimension_attribute | — | `school_name` in schools dimension. Drop from fact. |
| N Tested / Number Tested | fact_metric | `num_tested` | Int32. Not reported in 2023 → null for 2023 rows. |
| N Received SGP / Number Received SGP | fact_metric | `n_received_sgp` | Int32. In 2019 school it can be suppressed (`TFS`); cast via Float64 then round to Int. |
| % Received SGP | fact_metric | `pct_received_sgp` | Float64, scaled 0-1. Not reported in 2023 → null for 2023 rows. |
| Median SGP / SGP Median | fact_metric | `sgp_median` | Float64, 1-99 natural scale (not a percentage — do not divide by 100). |
| % Proficient Learner and above / and Above | fact_metric | `pct_proficient_learner_or_above` | Float64, scaled 0-1. Not reported in 2023 → null. |
| % Developing Learner and above / and Above | fact_metric | `pct_developing_learner_or_above` | Float64, scaled 0-1. Not reported in 2023 → null. |
| % Typical or High Growth | fact_metric | `pct_typical_or_high_growth` | Float64, scaled 0-1. Two-bucket growth flag (SGP ≥ 35). Not reported in 2023 → null. |
| % SGP Low Growth | fact_metric | `pct_sgp_low_growth` | Float64, scaled 0-1. 2023 only → null for 2015-2019. |
| % SGP Typical Growth | fact_metric | `pct_sgp_typical_growth` | Float64, scaled 0-1. 2023 only → null. |
| % SGP High Growth | fact_metric | `pct_sgp_high_growth` | Float64, scaled 0-1. 2023 only → null. |
| RESA (2023 only) | not_in_gold | — | Dimension attribute for districts (regional service area). Also truncated / inconsistent (`CENTRAL SAVANNAH RIV`). Drop from fact; if needed elsewhere, add to the districts dimension in a cleanup pass. |
| (title row 0 in every sheet) | not_in_gold | — | Informational only. |

## Corrections

- **2026-06-12 (transform authoring)** — claims re-verified against all 18 bronze files during the clean-start rebuild; evidence is from raw `header=None` / `header=1, dtype=str` reads of the named files/sheets and a full-file scan of every non-name column.
  - **The school `Key` has NO constant leading-`6` prefix; the `[1:4]`/`[4:]` slicing in ETL consideration 3 and the Gold Schema Classification is wrong.** The 7-digit Key is simply `district(3) + school(4)`: observed Key prefixes span the full GOSA district-code range 601–799 plus 891 (e.g. `8915001` = district 891 Dept. of Juvenile Justice + school 5001; `7820108` = State Charter system 782 + school 0108; `7910201` = city district 791 + school 0201). Cross-era proof: the same school appears as Key `6010103` in 2015-2017 and as `System Code 601` / `School Code 0103` in 2018-2019. Correct parse: `zfill(7)` → `slice(0, 3)` district, `slice(3, 4)` school. (`6010103[1:4]` would yield district `010` — nonsense.)
  - **Charter campus codes: system-level files publish 7-digit campus codes in EVERY year, including 2015-2017.** Era 1's System column description ("Int64, 3-digit GOSA district code") is incomplete — all System files (2015-2023) carry 7-digit charter campus district codes (`7820108`, `7830103`, …) and the 799-prefix state-school codes (`7991893`-`7991895`) alongside the 3-digit districts; no bare `782`/`783` appears at system level. At SCHOOL level, the 2015-2017 Key rows for those campuses parse to bare `782`/`783` + school code (e.g. `7820108` → 782 + 0108) while 2018+ School files already publish the 7-digit campus code in `System Code` — so the 2015-2017 school rows require the shared charter SYSTEM→CAMPUS promotion (191 rows: 69 in 2015, 78 in 2016, 44 in 2017).
  - **Undocumented `9999` numeric suppression sentinel in `EOC_PHY_2016_System`** (`GSGM_EOC_2016_System_Level.xls`): 11 rows store `9999` in all five of `% Received SGP`, `Median SGP`, `% Proficient Learner and above`, `% Developing Learner and above`, `% Typical or High Growth` — impossible values on those 0-100 / 1-99 scales. No `9999` exists anywhere else in any column of any file (counts included). The transform NULLs these per §4b and ledgers them as manifest masked events (5 columns × 11).
  - **`----` persists into the 2017 files.** The Era 1 suppression table implies `----` is 2015-2016-only with `TFS` taking over in 2017; in fact `% Proficient Learner and above` still carries `----` in 2017 (5 cells in `GSGM_EOC_2017_School_Level.xlsx`, 10 in `GSGM_EOC_2017_System_Level.xlsx`) alongside the `TFS` marker used by every other suppressed column.
  - **2019 system-level `Number Received SGP` is also suppressed**, not just the school-level `N Received SGP` listed in the Era 2 suppression table: `GSGM_EOC_2019_System_Level.xlsx` has 112 `TFS` cells in `Number Received SGP`. Suppression is also not strictly row-uniform in 2019 (e.g. the system file has 114 `TFS` in `% Received SGP` vs 113 in `Median SGP`).
  - **2023 sheets have a blank spacer row between header and data** — data starts at row 3, not row 2 as the "Excel Sheet Structure" intro claims for all files (the 2015-2019 files do start at row 2). The doc's per-sheet row counts (e.g. `School - Algebra I` = 833) are data rows; a `header=1` read returns one extra all-blank row. Harmless — the transform filters fully-null rows layout-agnostically.
  - **`EOC_AGE_2019_System` carries 119 trailing blank rows plus one orphan stray-marker row** (previously undocumented): the data block ends after 63 district rows, followed by 119 fully-blank rows and, at the very bottom (raw row 184), a row whose ONLY content is a lone `TFS` in `% Received SGP` with no System Code/Name — an artifact, not a record (it explains the 114-vs-113 `TFS` count asymmetry in that file's `% Received SGP` column). Both are dropped by the fully-null-row filter after marker nulling.
  - **Gold naming guidance superseded by the canonical vocabulary (§16).** ETL consideration 4 / the classification table suggest `n_received_sgp` and short subject values (`ninth_grade_literature`, `american_literature`, `united_states_history`, `economics`); gold uses the canonical names `num_received_sgp` and `9th_grade_literature_and_composition`, `american_literature_and_composition`, `us_history`, `economics_business_free_enterprise` per data-cleaning-standards §16 / `src/utils/subjects.py`.
