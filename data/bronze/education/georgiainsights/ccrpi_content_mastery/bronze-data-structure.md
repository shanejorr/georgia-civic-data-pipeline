# ccrpi_content_mastery — Bronze Data Structure

## Overview

- Topic: ccrpi_content_mastery
- Source: georgiainsights
- Files: 13 files spanning 2012-2025 (no 2020 file — COVID year, no CCRPI release)
- Unreadable files: none
- Year representation: `School Year` column in every file (matches filename year exactly; single-calendar-year integer such as `2013`, `2024`). 2024 file has a disclaimer row above the header.
- Filename-to-data year offset: same (filename year = `School Year` value)
- Detail levels: state, district, school (presence varies by era — see ETL Considerations)
- Percentage scale: `Participation Rate` is 0-100 for 2012-2017 and 2021-2022; 0-1 for 2018-2019 and 2023-2025. All content mastery metrics (`Meets & Exceeds Rate`, `Weighted Proficiency Rate`, `Indicator Score`, `Achievement Rate`, learner-level columns) are 0-100. `Target` is 0-100.
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: Georgia Insights (GaDOE) public data downloads — exact page URL not recorded at acquisition time
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| 2012 Content Mastery By Subgroups for Public Release.xls | 58d9e7a0b2602ef41cb1b257ecfaf1efd3a9fb962be1ee2af3bc97d2bb5ba916 |
| 2013 Content Mastery By Subgroups for Public Release.xls | 9b39e0da2ba71c587892c4a946e04d02c87c2a9bf5a8db56524a7a5e52b2576c |
| 2014 Content Mastery By Subgroup Ammended (2) for Web Page.xlsx | 9d4d8a57e1388983e9d1725fecf4b7f3b72cb18321c0a2b0c253da2e5250e68c |
| 2015 Content Mastery By Subgroup.xlsx | 3f28b6f79e93f684301bf514c44b557a904ef9ebdd1f2de7c098580a62d9ab00 |
| 2016 Content Mastery By Subgroup.xlsx | b4b7fabbbdaf153c14ee1f0f8dbe3e78938d621575b8f4c37400f91566fc8a75 |
| 2017 Content Mastery by Subgroup 11.2.17.xlsx | 86b99a222245dd9403e888852d3ef62201109fee2894d243bc8b43d196b228e6 |
| 2018 CCRPI Content Mastery Scores, Targets, Flags by Subgroup 12_14_18.xlsx | a40bc6bd923a0d92dbfc6d723731c9b81d76929f23027e710df367aa9f6264bd |
| 2019 CCRPI Content Mastery Scores, Targets, and Flags_04_01_20.xlsx | 0fc7ce315b310efd73dc8946457c8657700ee4d903cbc641dbb3f5f4cfe6b052 |
| 2021 Content Mastery by Subgroup 12.08.21.xlsx | f345d08981b64afe50794dbaa1dc0b37e04e717ac7884a240265386a8cd478c5 |
| 2022 CCRPI Content Mastery Scores by Subgroup 11.16.22.xlsx | 3a98c39c355f1ea7345f9f32ce863730fe8e1defb9e58622a53cd132341c4f61 |
| 2023 CCRPI Content Mastery Scores, Targets, and Flags by Subgroup_12_14_23.xlsx | 92dd8e113f41657314d501400fd8f8fa31a2d33c60be3cfd4cbc423030c41084 |
| 2024 CCRPI Content Mastery Scores, Targets, and Flags.xlsx | 4ce5db8581cb76ff72e5ebacb81d6a410e5411dca909d54b7b2cd7308b78a531 |
| 2025 CCRPI Content Mastery Scores, Targets, and Flags by Student Group.xlsx | d23040a16c298992ba66210ce32893d4b9c9e5d2982eafb92c52e50db458a03e |

## Excel Sheet Structure

| File(s) | Sheets | Notes |
|---------|--------|-------|
| 2012 | `Appling - Glynn` (Data), `Glynn - Carrollton City` (Data), `Carrollton City - State Schools` (Data) | .xls format. Data split alphabetically by district across 3 sheets, all with identical all-caps column names. School-level only — no district/state aggregate rows. Concatenate all sheets. |
| 2013 | `Appling to Gordon` (Data), `Gordon - Decatur City` (Data), `Decatur City - State Schools` (Data) | .xls format. Data split alphabetically across 3 sheets. **Third sheet uses title-case headers** (`Participation Rate`, `Meets Exceeds Rate`) while the first two use all-caps (`PARTICIPATION RATE`, `MEETS & EXCEEDS RATE`). Must normalize column names before concatenation. School-level only. |
| 2014 | `Sheet 1` (Data) | Single data sheet. State (`System ID="ALL"`) + district (`School ID="ALL"`) + school rows present. |
| 2015 | `Appling - Gordon` (Data), `Gordon - Atlanta` (Data), `Atlanta - RTC` (Data) | Data split alphabetically across 3 sheets, all with identical columns. State (`System Id="ALL"`), district (`School Id="ALL"`), school, and a pseudo-district `RTC` (Residential Treatment Center) aggregate present. Concatenate all sheets. |
| 2016 | `App-Gor` (Data), `Gor-Atl` (Data), `Atl-RTC` (Data) | Same shape as 2015 but `System ID`/`School ID` (uppercase). State (`System ID="ALL"`), district (`School ID="ALL"`), school, and `RTC` rows present. |
| 2017 | `Appling-Gordon` (Data), `Grady-Worth` (Data), `Atlanta-RTC` (Data) | Same shape as 2016. Polars auto-detects `System ID` / `School ID` as Int64 because numeric district codes dominate — must override schema to Utf8 so `"ALL"` / `"RTC"` aggregate markers are preserved instead of becoming nulls. |
| 2018-2019 | `Content Mastery by Subgroup` (Data) | Single data sheet. State + district + school rows present. 2018 uses `"ALL"` string markers (`School ID`/`System ID` are Utf8); 2019 uses null Int64 IDs paired with `System Name="All Systems"` / `School Name="All Schools"`. |
| 2021 | `Content Mastery by Subgroup` (Data), `FAQs` (Metadata) | `FAQs` sheet is empty. Single data sheet. `System ID="ALL"` / `School ID="ALL"` mark aggregates (Utf8). |
| 2022 | `Content Mastery by Subgroup` (Data), `FAQs` (Metadata) | `FAQs` sheet is empty. Single data sheet. `System ID`/`School ID` are Int64 with nulls for aggregates. |
| 2023 | `Content Mastery by Subgroup` (Data) | Single data sheet. `System ID`/`School ID` Int64 with nulls for aggregates. |
| 2024 | `Content Mastery by Subgroup` (Data) | Single data sheet. **Row 0 contains a disclaimer** ("Targets and flags for mathematics are not available due to the implementation of new mathematics standards and assessments in the 2023-2024 school year.") — read with `read_options={"header_row": 1}` so the real headers are on row 1. All math-subject `Target`/`Flag` values are `NA` in this file. |
| 2025 | `Content Mastery - Student Group` (Data) | Single data sheet with a different sheet name from prior years. Same column structure as 2023-2024. |

## Summary

CCRPI Content Mastery measures student proficiency on Georgia state assessments in core academic subjects (English/ELA, Mathematics, Science, Social Studies) reported by demographic subgroup at school, district, and (most years) state levels. The headline metric evolves across eras: **Meets & Exceeds Rate** (2012-2014, CRCT/EOCT era), **Weighted Proficiency Rate** (2015-2017, EOG/EOC transition), **Indicator Score** (2018-2019, 2022-2025), and **Achievement Rate** with learner-level breakdowns (2021). Eras 5 and 8 (2018-2019, 2023-2025) add improvement `Target` scores and performance `Flag` ratings (G / G* / Y / R / NA). Eras 6 and 7 (2021-2022) publish the four learner-level percentages (Beginning, Developing, Proficient, Distinguished) that compose the score. Early eras (2012-2017) carry a separate `Assessment Type` column (CRCT/EOCT or EOG/EOC) and 12-13 granular subjects (Biology, US History, Algebra I/Coordinate Algebra, etc.); later eras consolidate to the four broad indicators.

## Eras

### Era 1: 2012-2013

**Columns (2012, and 2013 sheets 1-2)**: `SCHOOL YEAR`, `SYSTEM ID`, `SYSTEM NAME`, `SCHOOL ID`, `SCHOOL NAME`, `GRADE CLUSTER`, `REPORTING CATEGORY`, `ASSESSMENT TYPE`, `ASSESSMENT SUBJECT`, `PARTICIPATION RATE`, `MEETS & EXCEEDS RATE`.

**2013 third sheet (`Decatur City - State Schools`)** uses the same logical columns but with title-case metric headers: `Participation Rate`, `Meets Exceeds Rate`. All other columns remain all-caps in that sheet too — only the two metric headers change.

All values stored as strings. No state-level or district-level aggregate rows — school-level only. Data is split across 3 sheets per file.

| Column | Description |
|--------|-------------|
| SCHOOL YEAR | Year (`"2012"` or `"2013"`) |
| SYSTEM ID | District code (3-digit string, e.g. `"656"`); 7-digit codes for state charter schools |
| SYSTEM NAME | District name |
| SCHOOL ID | School code (zero-padded 4-digit string, e.g. `"0182"`) |
| SCHOOL NAME | School name |
| GRADE CLUSTER | `E` (Elementary), `M` (Middle), `H` (High) |
| REPORTING CATEGORY | Demographic subgroup (see categorical table) |
| ASSESSMENT TYPE | `CRCT` (Criterion-Referenced Competency Tests) or `EOCT` (End-of-Course Tests) |
| ASSESSMENT SUBJECT | One of 13 subjects (CRCT subjects + 8 EOCT courses) |
| PARTICIPATION RATE | Percentage on 0-100 scale (string with suppression markers) |
| MEETS & EXCEEDS RATE | Percentage of students meeting or exceeding standards, 0-100 (string with suppression markers) |

#### Sample Data (2013, concatenated)

| SCHOOL YEAR | SYSTEM ID | SYSTEM NAME | SCHOOL ID | SCHOOL NAME | GRADE CLUSTER | REPORTING CATEGORY | ASSESSMENT TYPE | ASSESSMENT SUBJECT | PARTICIPATION RATE | MEETS & EXCEEDS RATE |
|---|---|---|---|---|---|---|---|---|---|---|
| 2013 | 734 | Telfair County | 0101 | Telfair County Middle School | M | Asian/Pacific Islander | CRCT | Mathematics | Too Few Students | Too Few Students |
| 2013 | 644 | DeKalb County | 2068 | Stone Mountain Elementary School | E | English Learners | CRCT | English Language Arts | 95 | 52.6 |
| 2013 | 706 | Muscogee County | 5060 | Gentian Elementary School | E | White | CRCT | English Language Arts | 98.7 | 86.7 |
| 2013 | 726 | Spalding County | 0187 | Griffin High School | H | Hispanic | EOCT | Mathematics-2 | 100 | 70 |

#### Statistics

- 2012 row count: 138,000 (across 3 sheets)
- 2013 row count: 136,595 (across 3 sheets, after column-name normalization)
- All columns are strings; no nulls (suppression is via text markers)

#### Null Counts

All columns: 0

#### Categorical Columns (2013, concatenated)

| Column | Distinct Values (with counts) |
|--------|------------------------------|
| GRADE CLUSTER | E (68,065), H (37,680), M (30,850) |
| REPORTING CATEGORY | ALL Students (13,673), American Indian/Alaskan (13,658), Asian/Pacific Islander (13,658), Black (13,658), Economically Disadvantaged (13,658), English Learners (13,658), Hispanic (13,658), Multi-Racial (13,658), Students With Disability (13,658), White (13,658) |
| ASSESSMENT TYPE | CRCT (98,915), EOCT (37,680) |
| ASSESSMENT SUBJECT | Reading (19,783), Science (19,783), Mathematics (19,783), Social Studies (19,783), English Language Arts (19,783), 9th Grade Literature and Composition (4,710), American Literature and Composition (4,710), Biology (4,710), Economics/Business/Free Enterprise (4,710), Mathematics-1 (4,710), Mathematics-2 (4,710), Physical Science (4,710), US History (4,710) |

#### Suppression Markers (2013, concatenated)

| Column | Non-Numeric Values (with counts) |
|--------|----------------------------------|
| PARTICIPATION RATE | Too Few Students (39,461), No Data (21,314) |
| MEETS & EXCEEDS RATE | Too Few Students (39,721), No Data (22,506) |

---

### Era 2: 2014

**Columns**: `School Year`, `System ID`, `System Name`, `School ID`, `School Name`, `Grade Cluster`, `Reporting Category`, `Assessment Type`, `Assessment Subject`, `Participation Rate`, `Meets Exceeds Rate`.

Same content scope as Era 1 but title-case headers; ampersand dropped from `Meets Exceeds Rate`. Single data sheet. **First year with state-level and district-level aggregate rows**: state rows use `System ID="ALL"` / `System Name="All Systems"` / `School ID="ALL"` / `School Name="All Schools"`; district rows use a real `System ID` plus `School ID="ALL"` / `School Name="All Schools"`.

#### Statistics

- Row count: 171,495
  - State-level rows (`System ID="ALL"`): 180
  - District-level rows (`System ID != "ALL"` AND `School ID="ALL"`): 34,710
  - School-level rows: 136,605
- All columns are strings; no nulls

#### Null Counts

All columns: 0

#### Categorical Columns

| Column | Distinct Values (with counts) |
|--------|------------------------------|
| Grade Cluster | E (77,565), H (53,280), M (40,650) |
| Reporting Category | ALL Students (17,163); Hispanic, English Learners, Black, Asian/Pacific Islander, White, Multi-Racial, Economically Disadvantaged, Students With Disability, American Indian/Alaskan (17,148 each) |
| Assessment Type | CRCT (118,215), EOCT (53,280) |
| Assessment Subject | Same 13 subjects as Era 1 (Science / Reading / Social Studies / English Language Arts / Mathematics each 23,643; the eight EOCT subjects 6,660 each) |

#### Suppression Markers

| Column | Non-Numeric Values (with counts) |
|--------|----------------------------------|
| System ID | ALL (180) — state marker, NOT suppression |
| School ID | ALL (34,890) — district/state marker, NOT suppression |
| Participation Rate | Too Few Students (47,991), No Data (25,210) |
| Meets Exceeds Rate | Too Few Students (48,602), No Data (26,441) |

---

### Era 3: 2015

**Columns**: `School Year`, `System Id`, `System Name`, `School Id`, `School Name`, `Grade Cluster`, `Reporting Category`, `Assessment Type`, `Assessment Subject`, `Participation Rate`, `Weighted Proficiency Rate`.

Differs from Era 4 only by ID-column casing: `System Id` / `School Id` (lowercase `d`) here vs `System ID` / `School ID` in 2016-2017. Switches the primary metric to `Weighted Proficiency Rate` (replaces `Meets Exceeds Rate`) and the assessment regime to `EOG` (End-of-Grade) / `EOC` (End-of-Course). Data split across 3 sheets. Aggregate markers present: `System Id="ALL"` (state), `System Id="RTC"` (Residential Treatment Center pseudo-district), `School Id="ALL"` (district aggregate).

#### Statistics

- Row count: 148,606 (across 3 sheets)
  - State-level rows (`System Id="ALL"`): 160
  - RTC pseudo-district rows (`System Id="RTC"`): 160
  - District-level rows: 31,400
  - School-level rows: 117,046 (includes individual RTC schools and standard schools)
- All columns are strings; no nulls

#### Categorical Columns

| Column | Distinct Values (with counts) |
|--------|------------------------------|
| Grade Cluster | E (60,886), H (54,720), M (33,000) |
| Reporting Category | ALL Students (14,992); other nine subgroups 14,846 each |
| Assessment Type | EOG (93,886), EOC (54,720) |
| Assessment Subject | 12 subjects — Mathematics (23,773), English Language Arts (23,773), `Science       ` *(note trailing spaces)* (23,170), Social Studies (23,170), Biology (6,840), Algebra I/Coordinate Algebra (6,840), 9th Grade Literature and Composition (6,840), Geometry/Analytic Geometry (6,840), Physical Science (6,840), American Literature and Composition (6,840), US History (6,840), Economics/Business/Free Enterprise (6,840) |

#### Suppression Markers

| Column | Non-Numeric Values (with counts) |
|--------|----------------------------------|
| System Id | ALL (160), RTC (160) — aggregate markers |
| School Id | ALL (31,560) — district/state marker |
| Participation Rate | Too Few Students (42,160), No Data (21,376) |
| Weighted Proficiency Rate | Too Few Students (42,641), No Data (22,752) |

---

### Era 4: 2016-2017

**Columns**: `School Year`, `System ID`, `System Name`, `School ID`, `School Name`, `Grade Cluster`, `Reporting Category`, `Assessment Type`, `Assessment Subject`, `Participation Rate`, `Weighted Proficiency Rate`.

Same shape as Era 3 but with uppercase `System ID` / `School ID`. Polars auto-detects 2017's `System ID` and `School ID` as Int64 (because numeric codes dominate); must read with `schema_overrides={'System ID': pl.Utf8, 'School ID': pl.Utf8}` to preserve `"ALL"`/`"RTC"` markers. Same EOG/EOC assessment regime, same `Weighted Proficiency Rate` metric.

| Column | Description |
|--------|-------------|
| School Year | Year (`"2016"` or `"2017"`) |
| System ID | District code or `"ALL"` (state) / `"RTC"` (Residential Treatment Center) |
| System Name | District name or `"All Systems"` / `"Residential Treatment Center"` |
| School ID | School code or `"ALL"` for district/state aggregates |
| School Name | School name or `"All Schools"` / `"All RTC Schools"` |
| Grade Cluster | E, M, H |
| Reporting Category | Demographic subgroup |
| Assessment Type | EOG or EOC |
| Assessment Subject | 12 subjects (replaces Mathematics-1/-2 with Algebra I/Coordinate Algebra and Geometry/Analytic Geometry) |
| Participation Rate | 0-100 scale (string with suppression) |
| Weighted Proficiency Rate | 0-100 scale; **can exceed 100** (e.g., 102.332) by design |

#### Statistics

- 2016 row count: 149,312 — state 160, district 31,520, school 117,632
- 2017 row count: 150,402 — state 160, district 33,400 (includes the RTC aggregate), school 116,842
- All columns are strings (when forced); no nulls

#### Categorical Columns (2016, concatenated)

| Column | Distinct Values (with counts) |
|--------|------------------------------|
| Grade Cluster | E (62,712), H (55,200), M (31,400) approx |
| Reporting Category | ALL Students + the 9 standard subgroups, all spelled the same as Era 3 |
| Assessment Type | EOC, EOG |
| Assessment Subject | Same 12 subjects as Era 3. **`Science       ` retains trailing whitespace** in both 2016 and 2017. |

#### Suppression Markers (2017)

| Column | Non-Numeric Values (with counts) |
|--------|----------------------------------|
| System ID | ALL (160), RTC (160) |
| School ID | ALL (33,400) |
| Participation Rate | Too Few Students (45,171), No Data (26,176) |
| Weighted Proficiency Rate | Too Few Students (45,336), No Data (27,464) |

---

### Era 5: 2018-2019

**Columns**: `School Year`, `System ID`, `System Name`, `School ID`, `School Name`, `Grade Configuration`, `Grade Cluster`, `Reporting Label`, `Indicator`, `Participation Rate`, `Indicator Score`, `Target`, `Flag`.

Major structural reset. Adds `Grade Configuration` (comma-separated list of grade levels offered at the school), `Target` (improvement target on 0-100), and `Flag` (G / G* / Y / R / NA performance rating). Replaces `Assessment Type` and `Assessment Subject` with `Indicator` (the four broad subjects). Renames `Reporting Category` to `Reporting Label`. **`Participation Rate` switches to 0-1 scale.**

Dtype quirks per year:
- **2018**: `System ID`/`School ID`/`Target` are strings; aggregates use literal `"ALL"` markers; `Target` carries `"NA"` / `"TFS"` suppression strings.
- **2019**: `System ID`/`School ID` are Int64 with nulls for state/district aggregates; `Target` is Float64 (suppressed values come through as nulls, not strings); `Indicator Score` and `Participation Rate` remain Utf8 with `"NA"`/`"TFS"` markers.

| Column | Description |
|--------|-------------|
| School Year | Year (integer, 2018 or 2019) |
| System ID | District code (integer in 2019 / string in 2018; null or `"ALL"` for state rows) |
| System Name | District name or `"All Systems"` |
| School ID | School code (null/`"ALL"` for district/state aggregates) |
| School Name | School name or `"All Schools"` |
| Grade Configuration | Comma-separated grade list (e.g. `"09, 10, 11, 12"`) — describes grades offered at the school, not the grade being tested |
| Grade Cluster | E, M, H |
| Reporting Label | Demographic subgroup |
| Indicator | English Language Arts, Mathematics, Science, Social Studies |
| Participation Rate | **0-1 scale** (string with `NA`/`TFS` markers) |
| Indicator Score | 0-100 scale (string with `NA`/`TFS` markers) |
| Target | Improvement target, 0-100 (string `NA`/`TFS` in 2018; Float64 with nulls in 2019) |
| Flag | G (green / met target), G* (green with caveat), Y (yellow), R (red / missed target), NA |

#### Statistics

- 2018 row count: 125,160
- 2019 row count: 125,520
  - State-level rows (System ID null/`"ALL"`): 120 per year
  - District-level rows: 25,560
  - School-level rows: 99,480 (2018) / 99,840 (2019)

#### Null Counts (2019)

| Column | Null Count |
|--------|-----------|
| System ID | 120 |
| School ID | 25,680 |
| Target | 57,686 |
| All others | 0 |

#### Categorical Columns (2019)

| Column | Distinct Values (with counts) |
|--------|------------------------------|
| Grade Cluster | E (63,080), M (34,160), H (28,280) |
| Reporting Label | ALL Students; American Indian/Alaskan Native, Asian/Pacific Islander, Black, Economically Disadvantaged, English Learners, Hispanic, Multi-Racial, Students with Disability, White — 12,552 each |
| Indicator | English Language Arts (31,380), Mathematics (31,380), Science (31,380), Social Studies (31,380) |
| Flag | NA (59,970), G (28,032), R (22,152), G* (10,660), Y (4,706) |

#### Suppression Markers (2019)

| Column | Non-Numeric Values (with counts) |
|--------|----------------------------------|
| Participation Rate | TFS (34,926), NA (20,759) |
| Indicator Score | TFS (35,141), NA (21,732) |
| Target | _Float64 column — suppressed values are null_ |

Note: 2018 uses `"ALL"` string markers in the ID columns; Reporting Label values match earlier eras (`American Indian/Alaskan`, `Students With Disability`). 2019 uses null Int64 IDs and renames two demographic labels to `American Indian/Alaskan Native` and `Students with Disability` (lowercase `w`). Same column structure, different value spellings.

---

### Era 6: 2021

**Columns**: `School Year`, `System ID`, `System Name`, `School ID`, `School Name`, `Grade Configuration`, `Grade Cluster`, `Reporting Label`, `Content Area`, `Participation Rate`, `Beginning Learner`, `Developing Learner`, `Proficient Learner`, `Distinguished Learner`, `Achievement Rate`.

No `Target` or `Flag` columns. Adds four learner-level percentage breakdowns (Beginning / Developing / Proficient / Distinguished, all 0-100) and replaces `Indicator Score` with `Achievement Rate`. Uses `Content Area` instead of `Indicator`, and the value `English` (not `English Language Arts`). All columns read as strings; aggregates use `"ALL"` markers. **`Participation Rate` returns to 0-100 scale** for this year only (2021-2022).

| Column | Description |
|--------|-------------|
| Content Area | `English`, `Mathematics`, `Science`, `Social Studies` |
| Participation Rate | 0-100 (string, NA / Too Few Students markers) |
| Beginning Learner | % of students at the lowest proficiency band, 0-100 |
| Developing Learner | % of students at the second proficiency band, 0-100 |
| Proficient Learner | % at third band, 0-100 |
| Distinguished Learner | % at highest band, 0-100 |
| Achievement Rate | Composite content-mastery metric, 0-100 (sentinel `"100.00+"` appears 1,772 times when capped) |

#### Statistics

- Row count: 110,900
  - State-level (`System ID="ALL"`): 110
  - District-level (`System ID != "ALL"` AND `School ID="ALL"`): 24,310
  - School-level: 86,480
- All columns are strings; no nulls

#### Categorical Columns

| Column | Distinct Values (with counts) |
|--------|------------------------------|
| Grade Cluster | E (47,580), M (34,600), H (28,720) |
| Reporting Label | ALL Students; American Indian/Alaskan, Asian/Pacific Islander, Black, Economically Disadvantaged, English Learners, Hispanic, Multi-Racial, Students With Disability, White — 11,090 each |
| Content Area | English (31,690), Mathematics (31,690), Science (31,690), Social Studies (15,830) |

#### Suppression Markers

| Column | Non-Numeric Values (with counts) |
|--------|----------------------------------|
| System ID | ALL (110) — state marker |
| School ID | ALL (24,420) — district/state marker |
| Participation Rate | Too Few Students (30,885), NA (18,792) |
| Beginning Learner | Too Few Students (33,563), NA (22,866) |
| Developing Learner | Too Few Students (33,563), NA (22,866) |
| Proficient Learner | Too Few Students (33,563), NA (22,866) |
| Distinguished Learner | Too Few Students (33,563), NA (22,866) |
| Achievement Rate | Too Few Students (33,563), NA (22,866), **100.00+ (1,772)** — non-suppression cap marker |

---

### Era 7: 2022

**Columns**: `School Year`, `System ID`, `System Name`, `School ID`, `School Name`, `Grade Configuration`, `Grade Cluster`, `Reporting Label`, `Content Area`, `Participation Rate`, `Beginning Learner or Level 1`, `Developing Learner or Level 2`, `Proficient Learner or Level 3`, `Distinguished Learner or Level 4`, `Indicator Score`.

Same shape as Era 6 but the four learner columns have `" or Level N"` appended (to accommodate the rebranding to numeric proficiency levels), and the composite metric is renamed back to `Indicator Score` (replacing `Achievement Rate`). `System ID`/`School ID` are Int64 with nulls for aggregates. `Participation Rate` remains 0-100 (max observed 100.0). The `Achievement Rate "100.00+"` sentinel from 2021 does **not** appear in 2022.

#### Statistics

- Row count: 111,590
  - State-level rows (`System ID is null`): 110
  - District-level rows: 24,420
  - School-level rows: 87,060

#### Null Counts

| Column | Null Count |
|--------|-----------|
| System ID | 110 |
| School ID | 24,530 |
| All others | 0 |

#### Categorical Columns

| Column | Distinct Values (with counts) |
|--------|------------------------------|
| Grade Cluster | E (47,790), M (34,880), H (28,920) |
| Reporting Label | ALL Students; American Indian/Alaskan Native, Asian/Pacific Islander, Black, Economically Disadvantaged, English Learners, Hispanic, Multi-Racial, Students With Disability, White — 11,159 each |
| Content Area | Science (31,880), Mathematics (31,880), English (31,880), Social Studies (15,950) |

#### Suppression Markers

| Column | Non-Numeric Values (with counts) |
|--------|----------------------------------|
| Participation Rate | Too Few Students (30,864), NA (18,381) |
| Beginning Learner or Level 1 | Too Few Students (31,145), NA (19,287) |
| Developing Learner or Level 2 | Too Few Students (31,145), NA (19,287) |
| Proficient Learner or Level 3 | Too Few Students (31,145), NA (19,287) |
| Distinguished Learner or Level 4 | Too Few Students (31,145), NA (19,287) |
| Indicator Score | Too Few Students (31,145), NA (19,287) |

---

### Era 8: 2023-2025

**Columns**: `School Year`, `System ID`, `System Name`, `School ID`, `School Name`, `Grade Configuration`, `Grade Cluster`, `Reporting Label`, `Indicator`, `Participation Rate`, `Indicator Score`, `Target`, `Flag`.

Same columns as Era 5 (2018-2019), but `Target` is read as **string** here (with `NA` / `TFS` markers) instead of Float64 like 2019. `System ID`/`School ID` are Int64 with nulls for aggregates. `Participation Rate` is 0-1.

**2024 caveat**: file has a disclaimer row at row 0 ("Targets and flags for mathematics are not available due to the implementation of new mathematics standards and assessments in the 2023-2024 school year.") — must read with `read_options={"header_row": 1}`. In the 2024 file, `Target` and `Flag` are `NA` for every Mathematics row.

**2025 caveat**: sheet name is `Content Mastery - Student Group` (different from 2023-2024's `Content Mastery by Subgroup`).

#### Statistics

- 2023 row count: 112,430
- 2024 row count: 113,750
- 2025 row count: 113,470
  - State-level rows (System ID null): 110 per year
  - District-level rows: ~25,720
  - School-level rows: ~87,600

#### Null Counts (2025)

| Column | Null Count |
|--------|-----------|
| System ID | 110 |
| School ID | 25,850 |
| All others | 0 |

#### Categorical Columns (2025)

| Column | Distinct Values (with counts) |
|--------|------------------------------|
| Grade Cluster | E (48,150), M (35,720), H (29,600) |
| Reporting Label | ALL Students; American Indian/Alaskan Native, Asian/Pacific Islander, Black, Economically Disadvantaged, English Learners, Hispanic, Multi-Racial, Students With Disability, White — 11,347 each |
| Indicator | English Language Arts (32,380), Science (32,380), Mathematics (32,380), Social Studies (16,330) |
| Flag | NA (53,172), R (25,327), G (20,762), G* (10,876), Y (3,333) |

#### Suppression Markers (2025)

| Column | Non-Numeric Values (with counts) |
|--------|----------------------------------|
| Participation Rate | TFS (30,201), NA (18,596) |
| Indicator Score | TFS (30,630), NA (19,610) |
| Target | TFS (30,453), NA (20,755) |

2024 `Target` distribution differs because of the math suppression: TFS (22,762), NA (48,628).

---

## ETL Considerations

### Multi-Sheet Concatenation

- **2012-2013** (.xls files): 3 data sheets per file, split alphabetically by district. Read with `xlrd` (via pandas), then concatenate. The 2013 third sheet (`Decatur City - State Schools`) uses **mixed-case metric headers** (`Participation Rate`, `Meets Exceeds Rate`) while the first two sheets are all-caps (`PARTICIPATION RATE`, `MEETS & EXCEEDS RATE`); normalize column names before concatenation.
- **2015-2017**: 3 data sheets per file, identical columns within each year. Concatenate. Casing of ID columns differs between 2015 (`System Id`/`School Id`) and 2016-2017 (`System ID`/`School ID`).
- **2018+**: single data sheet; in 2021-2022 the workbook also has an empty `FAQs` sheet which should be skipped.

### 2024 Disclaimer Row

The 2024 file has a disclaimer paragraph at row 0 above the real header row. Use `pl.read_excel(..., read_options={"header_row": 1})`. In the resulting frame, every Mathematics row has `Target="NA"` and `Flag="NA"` because Georgia rolled out new math standards/assessments that year and did not compute targets.

### ID Column Type Quirks (Critical)

| Year | `System ID` dtype (default polars read) | Aggregate marker for state row | Aggregate marker for district row |
|------|----------------------------------------|--------------------------------|-----------------------------------|
| 2012-2013 | Utf8 | (none — school-level only) | (none) |
| 2014 | Utf8 | `"ALL"` | `School ID="ALL"` |
| 2015 | Utf8 | `"ALL"` (+ `"RTC"` pseudo-district) | `School ID="ALL"` |
| 2016 | Utf8 | `"ALL"` / `"RTC"` | `School ID="ALL"` |
| 2017 | **Int64** (auto-detected) | `"ALL"` / `"RTC"` — **lost to null unless schema_overrides=Utf8** | `School ID="ALL"` — also lost |
| 2018 | Utf8 | `"ALL"` | `School ID="ALL"` |
| 2019 | Int64 | `null` | `School ID is null` |
| 2021 | Utf8 | `"ALL"` | `School ID="ALL"` |
| 2022+ | Int64 | `null` | `School ID is null` (plus `School Name="All Schools"`) |

**Recommended approach**: force `System ID`, `School ID` (and 2018's `Target`) to `pl.Utf8` via `schema_overrides` for every year, then derive the detail level from the marker — `"ALL"`, `null`, and `"RTC"` are all aggregate signals. After detail-level routing, cast `System ID` to a zero-padded 3-digit string (district code) and `School ID` to a zero-padded 4-digit string (school code) where the row is school-level. School IDs like `"0182"` lose their leading zeros when polars reads them as Int64, so `str.zfill(4)` is required.

### Column Name Changes Across Eras

| Concept | 2012-2013 | 2014 | 2015 | 2016-2017 | 2018-2019 | 2021 | 2022 | 2023-2025 |
|---------|-----------|------|------|-----------|-----------|------|------|-----------|
| District code | SYSTEM ID | System ID | System Id | System ID | System ID | System ID | System ID | System ID |
| School code | SCHOOL ID | School ID | School Id | School ID | School ID | School ID | School ID | School ID |
| Demographic | REPORTING CATEGORY | Reporting Category | Reporting Category | Reporting Category | Reporting Label | Reporting Label | Reporting Label | Reporting Label |
| Subject | ASSESSMENT SUBJECT | Assessment Subject | Assessment Subject | Assessment Subject | Indicator | Content Area | Content Area | Indicator |
| Primary metric | MEETS & EXCEEDS RATE | Meets Exceeds Rate | Weighted Proficiency Rate | Weighted Proficiency Rate | Indicator Score | Achievement Rate | Indicator Score | Indicator Score |

### Demographic Value Spelling Inconsistencies

Within `Reporting Category` / `Reporting Label`, value spellings drift between years and must be normalized to a single set of demographic codes:

- `American Indian/Alaskan` (2012-2018, 2021) ↔ `American Indian/Alaskan Native` (2019, 2022-2025)
- `Students With Disability` (most eras) ↔ `Students with Disability` (lowercase `w` in 2019 only)

`Asian/Pacific Islander` and `Multi-Racial` appear consistently across all eras.

### Asian / Pacific Islander Bucketing

Bronze uses **one combined `Asian/Pacific Islander` race bucket** in every era — there is no separate `Asian` value and no separate `Pacific Islander` value. Per `data-cleaning-standards` §5b, when the transform maps this bronze label to a gold demographic, the gold value must be `asian_pacific_islander` (NOT `asian`). The bronze never publishes both the combined bucket and a split pair in the same row set, so there is no mutual-exclusivity conflict to resolve.

### Subject / Indicator / Content Area Reconciliation

- **2012-2014**: 13 granular subjects spanning CRCT (Reading, Math, ELA, Science, Social Studies) and EOCT (9th Grade Literature and Composition, American Literature and Composition, Biology, Physical Science, Economics/Business/Free Enterprise, US History, Mathematics-1, Mathematics-2).
- **2015-2017**: 12 subjects — replaces Mathematics-1/-2 with Algebra I/Coordinate Algebra and Geometry/Analytic Geometry. **`Science       ` has trailing whitespace** in all three years and must be `str.strip()`-ed.
- **2018-2019, 2023-2025**: 4 indicators — `English Language Arts`, `Mathematics`, `Science`, `Social Studies`.
- **2021-2022**: 4 content areas — `English` (not `English Language Arts`), `Mathematics`, `Science`, `Social Studies`. Normalize `English` → `English Language Arts` for cross-era consistency.
- **Social Studies row count is roughly half** of the other three subjects in eras 6-8 because Social Studies is only assessed at the H grade cluster (and a subset of M); ELA/Math/Science are assessed at all three clusters.

### Assessment Type Column (2012-2017 only)

`Assessment Type` exists only in Eras 1-4 (CRCT/EOCT 2012-2014, EOG/EOC 2015-2017). It disappears starting in 2018. To preserve granularity across eras, treat it as a nullable fact categorical (`null` for 2018+).

### Grade Configuration (2018+ only)

The `Grade Configuration` column is a comma-separated list of grade levels offered at the school (e.g. `"PK, KK, 01, 02, 03, 04, 05"`) — it describes the school's grade span, not the grade being tested. It is a **school attribute**, not a test attribute, and is constant within a school across rows. Best modeled in the schools dimension rather than the fact table.

### Suppression Marker Catalog

| Era | Markers |
|-----|---------|
| 2012-2017 | `No Data`, `Too Few Students` |
| 2018-2019, 2023-2025 | `NA`, `TFS` |
| 2021-2022 | `NA`, `Too Few Students` |

Cast all suppression strings to `null` before numeric coercion. Polars' `cast(pl.Float64, strict=False)` will do this implicitly, but explicit replacement (with logging of counts replaced) is preferred.

### Participation Rate Scale

- **2012-2017**: 0-100
- **2018-2019, 2023-2025**: 0-1 (multiply by 100 in transform to match the gold convention)
- **2021-2022**: 0-100

Transform must rescale per-era so the gold value is consistently 0-100.

### Weighted Proficiency Rate Can Exceed 100

In 2015-2017, `Weighted Proficiency Rate` is by design allowed to exceed 100 (e.g., 102.332) because CCRPI weighted credit for students who exceeded the standard. Treat as a real value; do **not** cap.

### Achievement Rate "100.00+" Sentinel (2021 only)

`Achievement Rate` in 2021 contains 1,772 rows with the literal string `"100.00+"`. This is not a suppression marker — it is a top-cap sentinel where the underlying value exceeds 100. Recommended handling: treat as `100.0`. Document the count of rows affected in the transform manifest so reviewers know the data was clipped.

### Detail Level Detection (Summary)

| Era | State | District | School | Notes |
|-----|-------|----------|--------|-------|
| 2012-2013 | No | No | Yes | School-level only — no aggregate rows |
| 2014 | Yes | Yes | Yes | Aggregates via `System ID="ALL"` / `School ID="ALL"` |
| 2015-2017 | Yes (`"ALL"` only; in 2015-2016 there is also an `"RTC"` pseudo-district) | Yes | Yes | After forcing IDs to Utf8 |
| 2018, 2021 | Yes | Yes | Yes | Aggregates via `"ALL"` markers |
| 2019, 2022-2025 | Yes | Yes | Yes | Aggregates via null `System ID` / `School ID` (paired with `"All Systems"` / `"All Schools"` names) |

The RTC ("Residential Treatment Center") pseudo-district appears in 2015-2016 (and 2017 once IDs are read as Utf8). It aggregates state RTC facilities and behaves like a non-FIPS district. If gold restricts `district_code` to real FIPS / GA district codes, RTC rows must be filtered out or routed to a special bucket — document the choice in the transform.

### No 2020 Data

There is no 2020 file. Georgia did not release CCRPI for the 2019-2020 school year due to COVID-19 disruptions. Expect the year gap in gold output.

---

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| `SCHOOL YEAR` / `School Year` | fact_key | `year` | Year partition; cast to Int64. |
| `SYSTEM ID` / `System ID` / `System Id` | fact_key | `district_code` | FK to districts dimension. Cast Utf8, `zfill(3)`. `"ALL"` / `null` / `"RTC"` markers route to state-level fact / drop respectively. |
| `SYSTEM NAME` / `System Name` | dimension_attribute | — | `district_name` lives in the districts dimension; do not carry into fact. |
| `SCHOOL ID` / `School ID` / `School Id` | fact_key | `school_code` | FK to schools dimension. Cast Utf8, `zfill(4)`. `"ALL"` / `null` markers indicate district- or state-level rows. |
| `SCHOOL NAME` / `School Name` | dimension_attribute | — | `school_name` lives in the schools dimension. |
| `GRADE CLUSTER` / `Grade Cluster` | fact_categorical | `grade_cluster` | Values `E`, `M`, `H`. |
| `Grade Configuration` | not_in_gold | — | School attribute (grades offered at school), not a test metric. Optional addition to schools dimension. |
| `REPORTING CATEGORY` / `Reporting Label` | fact_key | `demographic` | FK to demographics dimension. Normalize `American Indian/Alaskan` ↔ `American Indian/Alaskan Native`; normalize `Students With Disability` ↔ `Students with Disability`. Map `Asian/Pacific Islander` → `asian_pacific_islander` per `data-cleaning-standards` §5b. `ALL Students` → `all`. |
| `ASSESSMENT TYPE` / `Assessment Type` | fact_categorical | `assessment_type` | Only populated for 2012-2017 (`CRCT`/`EOCT` or `EOG`/`EOC`). Null for 2018+. |
| `ASSESSMENT SUBJECT` / `Assessment Subject` / `Indicator` / `Content Area` | fact_categorical | `content_area` | Normalize `English` → `English Language Arts`. Trim trailing whitespace (`"Science       "` in 2015-2017). Early eras have 12-13 granular subjects; later eras have 4 broad subjects. |
| `PARTICIPATION RATE` / `Participation Rate` | fact_metric | `participation_rate` | Rescale per-era to 0-100 (multiply 2018-2019 and 2023-2025 by 100). Cast suppression markers to null. |
| `MEETS & EXCEEDS RATE` / `Meets Exceeds Rate` / `Weighted Proficiency Rate` / `Achievement Rate` / `Indicator Score` | fact_metric | `indicator_score` | Primary CCRPI content-mastery metric, 0-100. Cast suppression markers (`No Data`, `Too Few Students`, `NA`, `TFS`) to null. Cast `"100.00+"` to 100.0 (2021 Achievement Rate only). `Weighted Proficiency Rate` may legitimately exceed 100 — do not cap. |
| `Beginning Learner` / `Beginning Learner or Level 1` | fact_metric | `beginning_learner_pct` | 0-100. Only in 2021-2022. |
| `Developing Learner` / `Developing Learner or Level 2` | fact_metric | `developing_learner_pct` | 0-100. Only in 2021-2022. |
| `Proficient Learner` / `Proficient Learner or Level 3` | fact_metric | `proficient_learner_pct` | 0-100. Only in 2021-2022. |
| `Distinguished Learner` / `Distinguished Learner or Level 4` | fact_metric | `distinguished_learner_pct` | 0-100. Only in 2021-2022. |
| `Target` | fact_metric | `target` | Improvement target, 0-100. Only in 2018-2019, 2023-2025. Cast suppression markers (`NA`/`TFS`) and Float64 nulls to null. 2024 math rows are all null by design. |
| `Flag` | fact_categorical | `flag` | Performance rating: `G`, `G*`, `Y`, `R`. Map `NA` → null. Only in 2018-2019, 2023-2025. |

---

## Corrections

Re-verified against all 13 bronze files during the clean-start transform rewrite (2026-06-12), using string-typed reads (`pandas read_excel(dtype=str, na_values=SUPPRESSION_VALUES)`) so type inference cannot mask stored values.

1. **The `"100.00+"` sentinel also appears in 2023 — not only 2021.** The Era 8 section and the "Achievement Rate \"100.00+\" Sentinel (2021 only)" heading claim the sentinel is unique to 2021. In fact the 2023 `Indicator Score` column ships **2,683** literal `"100.00+"` values (2021 `Achievement Rate`: 1,772 as documented). No other year has any: 2012-2019, 2022, 2024, 2025 all have zero occurrences. Unlike 2021, the 2023 file has no learner-level columns from which to reconstruct the capped value.

2. **The stored aggregate marker is the literal string `"ALL"` in every year 2014-2025 — the "null Int64 IDs" for 2019/2022+ are a read artifact.** Era 5/7/8 descriptions ("2019 uses null Int64 IDs", "System ID/School ID are Int64 with nulls for aggregates") and the ID Column Type Quirks table describe what a *default polars read* produces: polars infers Int64 (numeric codes dominate) and coerces `"ALL"` to null. With a string-preserving read, `System ID`/`School ID` have **zero nulls in every file**, and the `"ALL"` counts match the documented aggregate-row counts exactly (2019: 120 / 25,680; 2022: 110 / 24,530; 2023: 110 / 24,970; 2025: 110 / 25,850). Detail-level detection only ever needs the `"ALL"` (and 2015-2017 `"RTC"`) string markers when the read preserves strings.

3. **Trailing-whitespace subject labels also affect 2012-2013, and also the `Reading` label.** The doc flags only `Science       ` in 2015-2017. Verified: 2012 and 2013 ship both `'Science       '` and `'Reading       '` (trailing spaces) alongside other clean labels; 2015-2017 ship `'Science       '`. Strip subject values before mapping in every era.

4. **2015-2017 contain no individual RTC school rows.** The Era 3 statistics line "School-level rows: 117,046 (includes individual RTC schools and standard schools)" is wrong about RTC: all 160 `System Id="RTC"` rows per year (2015, 2016, 2017) carry `School Id="ALL"` — the RTC pseudo-district publishes only its aggregate. There are zero school-level rows under the RTC system code and zero school names matching RTC/Residential in any of the three years.

5. **2021 learner-level percentages do not always sum to 100.** Undocumented source defect: 146 rows in 2021 (concentrated in `Grade Cluster=H`, `Content Area=English`; e.g. system 781 school 0101, system 633 multiple schools) have all four learner percentages populated but summing materially below 100 — worst case 76.46. 2022's worst deviation is 2.18. Partition-sum validation must be scoped/budgeted accordingly. Related: on numeric 2021 rows, `Achievement Rate = 0.5*Developing + 1.0*Proficient + 1.5*Distinguished` holds to within 0.005 (half the last published decimal) on all 52,699 numeric rows, which licenses reconstructing the 1,772 `"100.00+"` rows from the bands.

6. **2015, 2017, and 2018 detail-level statistics are internally inconsistent.** The Era 3 (2015) breakdown (state 160 + RTC 160 + district 31,400 + school 117,046 = 148,766) exceeds the file's 148,606 rows because the 160 RTC rows are already inside the 31,400 district figure. The Era 4 2017 line (district 33,400, school 116,842) mislabels the `School ID="ALL"` total (33,400) as "district": it includes the 160 state rows, so the correct split is state 160 / district 33,240 (incl. the 160 RTC rows) / school 117,002. Verified: 160 + 33,240 + 117,002 = 150,402 = the 2017 file total, and the doc's own suppression-marker table (`School ID` "ALL (33,400)") confirms the inclusive count. The Era 5 statistics give "District-level rows: 25,560" per year and "School-level rows: 99,480 (2018)"; a direct bronze recount shows 2018 = 120 state / 25,520 district / 99,520 school (the 25,560 district figure is 2019's; 120 + 25,520 + 99,520 = 125,160 = the 2018 file total).

7. **Gold Schema Classification table: three proposed names superseded by canonical vocabulary.** `content_area` → gold `subject`, `beginning_learner_pct` (etc.) → `pct_beginning_learner` (plus derived `pct_developing_learner_or_above` / `pct_proficient_learner_or_above`), and `flag` → `ccrpi_flag` with descriptive values (`green`/`green_star`/`yellow`/`red`), per data-cleaning-standards §16. The table's role/handling guidance is otherwise accurate.
