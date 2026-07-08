# ccrpi_readiness — Bronze Data Structure

## Overview

- Topic: ccrpi_readiness
- Source: georgiainsights
- Files: 7 Excel files spanning 2018-2025 (2020 is missing — no CCRPI was reported that year due to COVID-related federal waivers)
- Unreadable files: none
- Year representation: `School Year` column present in every file; values are 4-digit calendar years (e.g., `2024`) representing the spring of the school year (i.e., `2024` = 2023-24 school year). Stored as `Int64` in 2018, 2019, 2022, 2023, 2024, 2025 and as `String` ("2021") in the 2021 file.
- Filename-to-data year offset: same — the year prefix in the filename matches the `School Year` value inside the file (e.g., `2024 CCRPI Readiness Indicator by Subgroups.xlsx` contains `School Year = 2024`).
- Detail levels: state (single `All Systems` / `All Schools` row with null `System ID` and null `School ID`), district (`All Schools` rows with non-null `System ID` but null `School ID`), and school (non-null `System ID` and non-null `School ID`).
- Percentage scale: 0-100. Both `Indicator Score` and `Unbenchmarked Rate (Accelerated Enrollment)` are stored as percentage points (range 0-100, mean ~48 in 2024). They are stored as strings because suppression markers (`TFS`, `NA`) are mixed with numeric values.
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: Georgia Insights (GaDOE) public data downloads — exact page URL not recorded at acquisition time
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| 2018 CCRPI Readiness Indicators by Subgroup 12_14_18.xlsx | 50033af8696910482fc85ae44c31c070c1af3d5c8ba3cc53d7b9b3f4f70e4564 |
| 2019 CCRPI Readiness Indicators Data by Subgroup_10_25_19.xlsx | 0c40a2f1a9d3230cb9a43a909baec173d3a8b8021e5dfa544beeaa8a5f7540ff |
| 2021 Readiness Indictors by Subgroup 12.08.21.xlsx | 34bdcdec2175b2a5b9a603ca748af92736f2edf8f49e88780d5c93a48ec2ace3 |
| 2022 CCRPI Readiness Indicators by Subgroup 11.16.22.xlsx | 8e271352475ed02289a21fba1fcae0368fb89c9a22fc5918e42db10352b80ec8 |
| 2023 CCRPI Readiness Indicator by Subgroup_12_14_23.xlsx | 97d5a3c1be28d4442e703536f52ea5e3eb669fa75a8d48bce8689bbfa4780002 |
| 2024 CCRPI Readiness Indicator by Subgroups.xlsx | f00270bedaec3fd95518e06c0a62f5becebb294275f3c18942926347d754e36e |
| 2025 CCRPI Readiness Indicators by Student Group.xlsx | 41e11c3fadf397c1cac89ae9868ae1d22e3deb8655838f4d4745b8e54c28ed37 |

## Excel Sheet Structure

| File(s) | Sheets | Notes |
|---------|--------|-------|
| 2018, 2019, 2023, 2024 | `Readiness by Subgroup` (Data) | Single data sheet |
| 2021, 2022 | `Readiness by Subgroup` (Data), `FAQs` (Metadata) | FAQs sheet contains explanatory notes; not usable as tabular data (polars reports the sheet as empty after dropping non-data rows) — skip during transform |
| 2025 | `Readiness - Student Group` (Data) | Sheet was renamed from "Readiness by Subgroup" to "Readiness - Student Group" — transform must select the data sheet by position or by handling both names |

The 2022 data sheet has a DOE explanatory disclaimer in row 1 (a single merged cell about pandemic-related accountability modifications). Polars treats that disclaimer as the header row by default, producing junk column names like `__UNNAMED__1`. The transform must skip the first row when reading 2022 (e.g., `read_options={"header_row": 1}`).

All other files have headers in row 1.

## Summary

CCRPI Readiness Indicator scores published annually by the Georgia Department of Education / Georgia Insights. The dataset reports each school's (and aggregated district/state) score on the **CCRPI Readiness component** broken down by demographic subgroup. The Readiness component aggregates several sub-metrics that vary by grade cluster:

- **Literacy** (primarily E/M, 2018-2022) — percent of students reading at or above grade level on Georgia Milestones, renamed to **At or Above Grade-Level Reading** starting in 2023. Also reported at H (~6,500 rows/year) in every bronze year.
- **Student Attendance** (primarily E/M, 2018-2022) — percent of students attending ≥90% of enrolled days, renamed to **Attendance** starting in 2023. Also reported at H in every bronze year that includes the indicator.
- **Beyond the Core** (E/M) — percent of students enrolled in enrichment courses (Fine Arts, World Language, Computer Science, Career Exploratory, Physical Education/Health). Sub-Indicator splits this into the individual enrichment categories.
- **Accelerated Enrollment** (H) — high school students earning college-level credit (Advanced Placement, Dual Enrollment, International Baccalaureate, Advanced Academic, Cambridge). Reported with both an "Unbenchmarked Rate" and a benchmarked "Indicator Score".
- **Pathway Completion** (H) — percent of high school graduates completing a CTAE / Fine Arts / World Language / Advanced Academic pathway.
- **College and Career Readiness** (H) — percent of high school graduates demonstrating readiness via ACT/SAT/AP/IB/Cambridge, ASVAB, EOPA, TCSG/USG entry, or Work-Based Learning.

All metric values are percentages on a 0-100 scale. CCRPI was not calculated for 2020 (pandemic waiver), and the 2022 file is partial (no Attendance/Literacy at HS, no College and Career Readiness — see disclaimer note in the file).

## Eras

Eras are defined by exact column-name match. There are two eras.

### Era 1: 2018-2019

| Column | Description |
|--------|-------------|
| School Year | 4-digit spring year of the school year (Int64). |
| System ID | Numeric district/system code (Int64). Null on the single state-level summary row. |
| System Name | District name; `All Systems` indicates the state-level aggregate. |
| School ID | Numeric school code (Int64). Null on district-level and state-level summary rows. |
| School Name | School name; `All Schools` indicates a district-level or state-level aggregate row. |
| Grade Configuration | Comma-separated list of grade levels served by the school (e.g., `PK, KK, 01, 02, 03, 04, 05`). |
| Grade Cluster | One of `E` (elementary), `M` (middle), `H` (high). A school can appear under multiple clusters if its grades span clusters. |
| Reporting Label | Demographic subgroup (e.g., `ALL Students`, `Black`, `English Learners`). |
| Indicator | One of six readiness sub-metrics (see Categorical Columns). |
| Indicator Score | Percent score on the indicator (0-100), stored as String due to suppression markers (`TFS`, `NA`). |

#### Sample Data

```
shape: (5, 10)
School Year | System ID | System Name             | School ID | School Name                                | Grade Configuration    | Grade Cluster | Reporting Label         | Indicator          | Indicator Score
2019        | 773       | City Schools of Decatur | 505       | Clairemont Elementary School               | PK, KK, 01, 02, 03     | E             | White                   | Beyond The Core    | 100
2019        | 741       | Troup County            | 207       | Bradfield Center - Ault Academy            | 05, 07, 08, 09, 10, 11 | M             | ALL Students            | Beyond The Core    | 21.05
2019        | 659       | Franklin County         | 2050      | Carnesville Elementary Primary School      | PK, KK, 01, 02         | E             | American Indian/Alaskan | Student Attendance | NA
2019        | 644       | DeKalb County           | 309       | Wadsworth Magnet School for High Achievers | 04, 05, 06             | M             | Black                   | Student Attendance | 100
2019        | 658       | Forsyth County          | 199       | Vickery Creek Middle School                | 06, 07, 08             | M             | English Learners        | Literacy           | 57.78
```

#### Statistics (2019 representative, 105,640 rows)

```
School Year: count=105640, all=2019
System ID  : count=105530, null=110, min=601, max=7991895
School ID  : count=83640,  null=22000, min=100, max=5567 (the 7-digit System ID values are state-charter / virtual operators)
Indicator Score (parsed as float, ignoring TFS/NA): full 0-100 range
```

#### Null Counts (2019)

| Column | Nulls |
|--------|-------|
| School Year | 0 |
| System ID | 110 (state-level rows where `System Name = All Systems`) |
| System Name | 0 |
| School ID | 22,000 (district-level and state-level summary rows where `School Name = All Schools`) |
| School Name | 0 |
| Grade Configuration | 0 |
| Grade Cluster | 0 |
| Reporting Label | 0 |
| Indicator | 0 |
| Indicator Score | 0 (suppression markers `TFS`/`NA` are stored as strings, not nulls) |

#### Categorical Columns (2019)

| Column | Distinct Values |
|--------|----------------|
| Grade Cluster (3) | `E` (47,000), `M` (25,290), `H` (33,350) |
| Reporting Label (10) | `ALL Students`, `American Indian/Alaskan`, `Asian/Pacific Islander`, `Black`, `Economically Disadvantaged`, `English Learners`, `Hispanic`, `Multi-Racial`, `Students With Disability`, `White` (each ~10,564 rows) |
| Indicator (6) | `Accelerated Enrollment`, `Beyond The Core`, `College and Career Readiness`, `Literacy`, `Pathway Completion`, `Student Attendance` |
| System Name (212) | District names; `All Systems` is the state aggregate |
| School Name (2,184) | School names; `All Schools` is a district or state aggregate (22,000 rows) |
| Grade Configuration (74) | Comma-separated grade lists (e.g., `PK, KK, 01, 02, 03, 04, 05` — 28,950 rows; `09, 10, 11, 12` — 19,330 rows) |

#### Suppression Markers (2019)

| Column | Non-Numeric Values | Counts |
|--------|-------------------|--------|
| Indicator Score | `TFS`, `NA` | 25,733 / 10,865 |

`TFS` = Too Few Students (suppression for small subgroup counts). `NA` = Not Applicable / not reported (e.g., a high-school-only indicator on an elementary row).

### Era 2: 2021-2025

This era adds two columns relative to Era 1: `Sub-Indicator` and `Unbenchmarked Rate (Accelerated Enrollment)`. Column NAMES are identical across all five files in this era; column VALUES (especially indicator and sub-indicator labels) shift several times — see ETL Considerations.

| Column | Description |
|--------|-------------|
| School Year | 4-digit spring year (Int64 in 2022-2025; String in 2021). |
| System ID | District code (Int64). Null on state-level summary rows. |
| System Name | District name; `All Systems` is the state aggregate. |
| School ID | School code (Int64). Null on district/state aggregate rows. |
| School Name | `All Schools` indicates an aggregate row. |
| Grade Configuration | Comma-separated grade list. |
| Grade Cluster | `E`, `M`, or `H`. |
| Reporting Label | Demographic subgroup. |
| Indicator | One of six readiness sub-metrics (see Categorical Columns). |
| Sub-Indicator | Component within the parent indicator (e.g., `Fine Arts` within `Beyond the Core`). The literal value `All` and the literal value `NA` both appear and signify "no further breakdown" (NOT a missing value). |
| Unbenchmarked Rate (Accelerated Enrollment) | Raw participation rate (0-100) for the Accelerated Enrollment sub-indicators before benchmark scaling. Equals `Indicator Score` for non-Accelerated-Enrollment rows. Stored as String due to `TFS`/`NA` markers. |
| Indicator Score | Percent score on the indicator (0-100), String. |

#### Sample Data (2024)

```
shape: (5, 12)
School Year | System ID | System Name     | School ID | School Name                    | Grade Configuration                                    | Grade Cluster | Reporting Label          | Indicator                       | Sub-Indicator      | Unbenchmarked Rate (Accelerated Enrollment) | Indicator Score
2024        | 710       | Paulding County | 109       | North Paulding High School     | 09, 10, 11, 12                                         | H             | English Learners         | College and Career Readiness    | ASVAB              | 0     | 0
2024        | 748       | Ware County     | null      | All Schools                    | PK, KK, 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12 | H             | Asian/Pacific Islander   | At or Above Grade-Level Reading | All                | TFS   | TFS
2024        | 741       | Troup County    | 204       | Callaway Middle School         | 06, 07, 08                                             | M             | Students With Disability | Beyond the Core                 | Computer Science   | 13.64 | 13.64
2024        | 658       | Forsyth County  | 704       | East Forsyth High School       | 09, 10, 11, 12                                         | H             | Black                    | Accelerated Enrollment          | Cambridge          | TFS   | TFS
2024        | 708       | Oconee County   | 103       | Rocky Branch Elementary School | PK, KK, 01, 02, 03, 04, 05                             | E             | Hispanic                 | Beyond the Core                 | Career Exploratory | 0     | 0
```

#### Statistics (2024 representative, 304,670 rows)

```
School Year: 2024
System ID  : count=304340, null=330, min=601, max=7830647
School ID  : count=235990, null=68680
Indicator Score (parsed as float): min=0, max=100, mean=47.82
Unbenchmarked Rate (parsed as float): min=0, max=100, mean=46.56
```

#### Null Counts (2024)

| Column | Nulls |
|--------|-------|
| School Year | 0 |
| System ID | 330 (state-level rows) |
| System Name | 0 |
| School ID | 68,680 (district + state aggregate rows) |
| School Name | 0 |
| Grade Configuration | 0 |
| Grade Cluster | 0 |
| Reporting Label | 0 |
| Indicator | 0 |
| Sub-Indicator | 0 (the literal strings `All` and `NA` are used to mean "not applicable") |
| Unbenchmarked Rate (Accelerated Enrollment) | 0 (suppression markers stored as strings) |
| Indicator Score | 0 |

#### Categorical Columns (Era 2 — combined across 2021-2025; counts shown for 2024)

| Column | Distinct Values |
|--------|----------------|
| Grade Cluster (3) | `E` (112,000), `M` (70,120), `H` (122,550) |
| Reporting Label (10) | 2021: `American Indian/Alaskan` (no "Native"). 2022-2025: `American Indian/Alaskan Native`. Other nine labels are stable: `ALL Students`, `Asian/Pacific Islander`, `Black`, `Economically Disadvantaged`, `English Learners`, `Hispanic`, `Multi-Racial`, `Students With Disability`, `White`. |
| Indicator | 2021: `Accelerated Enrollment`, `Beyond the Core`, `College and Career Readiness`, `Literacy`, `Pathway Completion`, `Student Attendance`. 2022: only `Accelerated Enrollment`, `Beyond the Core`, `Literacy`, `Pathway Completion` (Student Attendance, College and Career Readiness omitted per pandemic disclaimer). 2023-2025: `Accelerated Enrollment`, `At or Above Grade-Level Reading` (renamed from Literacy), `Attendance` (renamed from Student Attendance), `Beyond the Core`, `College and Career Readiness`, `Pathway Completion`. |
| Sub-Indicator | Heavy churn — see "Sub-Indicator Recoding" table in ETL Considerations. |

#### Suppression Markers (Era 2, 2024)

| Column | Non-Numeric Values | Counts |
|--------|-------------------|--------|
| Unbenchmarked Rate (Accelerated Enrollment) | `TFS`, `NA` | 75,797 / 32,498 |
| Indicator Score | `TFS`, `NA` | 75,797 / 32,498 |

## ETL Considerations

### Indicator label recoding (cross-era)

| Bronze value | Years observed | Canonical (gold) value |
|---|---|---|
| `Beyond The Core` | 2018, 2019 | `Beyond the Core` |
| `Beyond the Core` | 2021-2025 | `Beyond the Core` |
| `Literacy` | 2018, 2019, 2021, 2022 | `At or Above Grade-Level Reading` |
| `At or Above Grade-Level Reading` | 2023-2025 | `At or Above Grade-Level Reading` |
| `Student Attendance` | 2018, 2019, 2021 | `Attendance` |
| `Attendance` | 2023-2025 | `Attendance` |
| `Accelerated Enrollment` | all | `Accelerated Enrollment` |
| `College and Career Readiness` | all except 2022 | `College and Career Readiness` |
| `Pathway Completion` | all | `Pathway Completion` |

Decide explicitly whether to roll Literacy → At or Above Grade-Level Reading and Student Attendance → Attendance in gold; the underlying methodology was revised in 2023, so reviewers may prefer to keep them as separate indicators rather than concatenating the time series.

### Sub-Indicator label recoding (Era 2)

Sub-Indicator only exists in Era 2. The label set evolved:

| Bronze value(s) | Years | Likely canonical |
|---|---|---|
| `All` | 2021-2025 | `All` (means "no breakdown — overall indicator score") |
| `NA` | 2021, 2022 | `NA` literal — appears on rows for indicators that have no sub-breakdown (e.g., Literacy, Student Attendance). Treat as `All` in gold or carry through. |
| `Fine Arts` / `Fine arts` | mixed casing 2021-2022; `Fine Arts` 2023+ | `Fine Arts` |
| `World Language` / `World language` | mixed casing 2021-2022; `World Language` 2023+ | `World Language` |
| `Career Exploratory` | 2021+ | `Career Exploratory` |
| `Computer Science` | 2021+ | `Computer Science` |
| `Physical Education or Health` (2021), `Physical Education/Health` (2022-2025) | | `Physical Education/Health` |
| `Advanced Placement` | 2021-2024 | `Advanced Placement` |
| `Dual Enrollment` | 2021-2024 | `Dual Enrollment` |
| `International Baccalaureate` | 2021-2024 | `International Baccalaureate` |
| `Advanced academic` (2021-2022) / `Advanced Academic` (2023-2025) | | `Advanced Academic` |
| `Cambridge` | 2023-2025 | `Cambridge` |
| `CTAE` | 2021-2025 | `CTAE` |
| `Readiness score on the ACT, SAT, AP or IB` (2021), `ACT/SAT/AP/IB` (2023-2024), `ACT/SAT/AP/IB/Cambridge` (2025) | | normalize to one canonical token (e.g., `ACT/SAT/AP/IB/Cambridge`) |
| `End of pathway assessment (EOPA)` (2021), `EOPA` (2023+) | | `EOPA` |
| `Entering TCSG/USG without needing remediation` (2021), `TCSG/USG` (2023+) | | `TCSG/USG` |
| `Work-based learning` (2021), `Work-Based Learning` (2023+) | | `Work-Based Learning` |
| `ASVAB` | 2023-2025 | `ASVAB` |

The transform should build an explicit recode map and fail loudly on any unseen sub-indicator value (use `MissingMappingError` from `src/utils/transformers.py`).

### Reporting Label (demographic) recoding

`American Indian/Alaskan` (2018-2021) → `American Indian/Alaskan Native` (2022+). Standardize before joining the global demographics dimension.

### Suppression markers

`TFS` (Too Few Students) and `NA` (Not Applicable) appear in `Indicator Score` and `Unbenchmarked Rate (Accelerated Enrollment)`. Both should map to null when casting to numeric. Distinguish them in a separate `suppression_reason` column if downstream consumers need to know why a value is missing.

### Score type / scale

Both numeric columns are percentages on a 0-100 scale. Cast with `strict=False` after replacing suppression markers; do not divide by 100 (the metric is reported as percentage points, consistent with other CCRPI gold tables).

### Missing year

There is no 2020 file. Document this in the gold metadata so consumers don't assume a data gap is a pipeline bug.

### 2022 partial reporting

The 2022 file omits `Student Attendance`, `College and Career Readiness`, and the Elementary/Middle Literacy reporting at high school. The DOE disclaimer in row 1 of the 2022 sheet explains this. The transform should not attempt to fabricate missing 2022 values.

### Sheet name change in 2025

The data sheet was renamed from `Readiness by Subgroup` to `Readiness - Student Group`. Either select the sheet by index (first sheet) or branch on filename when reading.

### 2022 header offset

The 2022 file has a single-cell DOE disclaimer in row 1; the actual header is in row 2. Use `pl.read_excel(..., read_options={"header_row": 1})` (zero-indexed) or otherwise skip the disclaimer row when reading 2022.

### System ID size / format

`System ID` and `School ID` are bare integers (not zero-padded strings). State-charter / virtual operators have 7-digit System IDs (e.g., 7,991,895 in 2019; 7,830,647 in 2024) — these are valid, not data errors. Cast to string with no zero-padding when joining to the districts/schools dimensions.

### Aggregate rows (state and district)

- State row: `System Name = All Systems`, `System ID = null`, `School Name = All Schools`, `School ID = null`.
- District-aggregate row: `System Name = <District>`, `System ID = <code>`, `School Name = All Schools`, `School ID = null`.
- School-level row: both IDs populated.

The transform should classify each row by detail level using these patterns and route to the appropriate gold partition (state / district / school).

### "All" vs "NA" sub-indicator

In Era 2, `Sub-Indicator = "All"` denotes the parent-indicator overall score for indicators that DO have sub-breakdowns (e.g., `Beyond the Core / All` is the rolled-up Beyond the Core score). `Sub-Indicator = "NA"` (2021, 2022 only) denotes indicators that have no sub-breakdown at all (Literacy, Student Attendance). Treat `NA` as semantically equivalent to `All` when computing the overall indicator score in gold.

## Corrections (2026-06-12, verified during transform authoring)

Raw-cell re-verification of all 7 files (pandas `dtype=str`, `keep_default_na=False`, `na_values=[]`) found the following claims in this document to be artifacts of a typed read or otherwise inaccurate:

1. **Aggregate-row IDs are literal `ALL` sentinels, not nulls.** The Overview ("null `System ID` and null `School ID`"), the Era column tables ("Null on the single state-level summary row"), the Null Counts tables (2019: 110 / 22,000; 2024: 330 / 68,680), the Statistics blocks, and the "Aggregate rows (state and district)" section all describe the ID columns as null on aggregate rows. In the raw cells, **no ID cell is empty in any year**: every state row carries `System ID = "ALL"` and `School ID = "ALL"`, and every district-aggregate row carries `School ID = "ALL"`. Verified per file: the `ALL` sentinel appears on exactly the aggregate rows (0 mismatches against the name-based detail-level rule in all 7 files). The "nulls" reported here came from an Int64-inferring read coercing the non-numeric `ALL` token to null. The transform nulls `ALL` before zero-padding.
2. **2021 and 2022 spell out `Too Few Students`, not `TFS`.** The Overview, Era tables, and "Suppression markers" section list the markers as `TFS` / `NA` generically. Verified: 2018, 2019, 2023, 2024, 2025 use `TFS`; **2021 and 2022 use the spelled-out `Too Few Students`** (plus `NA`). Both forms are in the shared `SUPPRESSION_VALUES`, so suppression-aware reads null them either way.
3. **Sub-Indicator "years observed" inaccuracies.** The recoding table lists `Advanced Placement`, `Dual Enrollment`, and `International Baccalaureate` as "2021-2024"; all three appear in **every Era 2 year including 2025**. Additionally, the table omits parent-indicator nesting: `International Baccalaureate` also appears under **Pathway Completion** in 2022-2023 (not only Accelerated Enrollment), and `Fine Arts` / `World Language` appear under both **Beyond the Core** and **Pathway Completion**.
4. **2019 sample-data transcription slip.** The sample row for Wadsworth Magnet (644/309, `M`, Black, Student Attendance) shows `Indicator Score = 100`; the bronze file has `E = 100` and `M = 96.15` — the sample paired the M-cluster row with the E-cluster score. Cosmetic only.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| School Year | fact_key | year | Cast to Int64. Spring year of school year. |
| System ID | fact_key | district_code | Cast to string (no zero-padding). FK to districts dimension. Null on state-level rows. |
| System Name | dimension_attribute | — | district_name lives in districts dimension. `All Systems` row should be excluded from district dim insert and used to set state-level fact rows. |
| School ID | fact_key | school_code | Cast to string. FK to schools dimension. Null on district/state aggregate rows. |
| School Name | dimension_attribute | — | school_name lives in schools dimension. `All Schools` is an aggregate marker, not a real school. |
| Grade Configuration | dimension_attribute | — | Belongs in schools dimension (current grade range served). Not in fact table. |
| Grade Cluster | fact_categorical | grade_cluster | Recode `E`/`M`/`H` to `elementary`/`middle`/`high`. Required because a school can produce one row per cluster it serves. |
| Reporting Label | fact_key | demographic | FK to demographics dimension. Recode `American Indian/Alaskan` → `American Indian/Alaskan Native`; map all to canonical demographics dim values (e.g., `ALL Students` → `all_students`). |
| Indicator | fact_categorical | indicator | Snake-case the canonical names (e.g., `beyond_the_core`, `at_or_above_grade_level_reading`, `attendance`, `accelerated_enrollment`, `pathway_completion`, `college_and_career_readiness`). Apply the recoding table above. |
| Sub-Indicator | fact_categorical | sub_indicator | Era 2 only; nullable in Era 1 gold rows. Apply the sub-indicator recoding table; treat literal `NA` and `All` as `all` in gold. |
| Unbenchmarked Rate (Accelerated Enrollment) | fact_metric | unbenchmarked_rate | Float64, 0-100. Replace `TFS`/`NA` with null before casting. Only meaningful for `accelerated_enrollment` rows; equals `indicator_score` for other rows in source — decide whether to keep it null for non-Accelerated-Enrollment rows in gold. |
| Indicator Score | fact_metric | indicator_score | Float64, 0-100. Replace `TFS`/`NA` with null before casting. |

Detail-level routing: emit separate fact files for state, district, and school detail under `data/gold/education/ccrpi_readiness/year=YYYY/` per the Georgia gold output conventions. Do not write empty parquet files for detail levels with no rows in a given year.
