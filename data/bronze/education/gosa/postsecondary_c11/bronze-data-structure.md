# postsecondary_c11_report — Bronze Data Structure

## Overview

- Topic: postsecondary_c11_report
- Source: gosa
- Files: 13 files spanning publication years 2012-2024; covers HS graduating cohorts 2010-2022
- Unreadable files: none
- Year representation: Every file carries a `School Year` / `SCHOOL_YEAR` column that holds a **single** integer per file (e.g., `2010`, `2017`, `2021`) representing the high school graduating-class year the metrics describe. Filenames use the **publication year** (fiscal year of the report). Era 4 (2023-2024) CSVs add a separate `REPORTING_YEAR` header column that matches the filename year. In every era `SCHOOL_YEAR` is a single calendar year (not a spanning range like `2010-2011`).
- Filename-to-data year offset: **filename year = `School Year` + 2** consistently across every file (the C11 report tracks postsecondary enrollment approximately 1 year after HS graduation; publication adds another year of lag).
- Detail levels: state (1 row per file), district (one row per district), school (one row per school). All three levels present in every file.
- Percentage scale: not applicable. Every metric is a raw **count** of students (HS graduates, HS graduates enrolled in any postsecondary institution). No rates or percentages are published in bronze.
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| postsecondary_c_11_report_2012.xlsx | 584cd001c77cd8cab354f7007dcaa094cc88cdf7ad3281ccb4f4bd6f49698b86 |
| postsecondary_c_11_report_2013.xlsx | 3907d25a2ec106651c3c2e9782f2082649f68f8a150751ce4f44c53cc38e0d01 |
| postsecondary_c_11_report_2014.xlsx | 426ea03c1bf6b89a8a80b5ff349966ed9eb36c4153425c580a8861d5e4ac8994 |
| postsecondary_c_11_report_2015.xlsx | ba44843cb3c9abd3572e95e2dbca0d986284c998bfd709ff616e29de8a26f366 |
| postsecondary_c_11_report_2016.xlsx | 45e4912bae280d290f9f1c3354340bb6d97c623a1855977c46a6436f3afe8715 |
| postsecondary_c_11_report_2017.xlsx | 0cf45b90b3b120f992c4b9e41888870fa7816c9c8163e352a1fb7112b8886950 |
| postsecondary_c_11_report_2018.xlsx | 7628133ed905b418178b68f598ba205ae68736c385b1fb1f371bb2fb9b5eac0b |
| postsecondary_c_11_report_2019.xlsx | 072bd30b25aa8851c334caecf16247e33ac38cd2183f63d62954bb4674def307 |
| postsecondary_c_11_report_2020.xlsx | 0b36bc20b9dfa0fdd86d7bdbb5b13e659ef937b4bf033f535a0b7bd11c6c1ebc |
| postsecondary_c_11_report_2021.xlsx | b433e45e831a8ce1e87608f32105935009ab91310a2bc1efafc476394d24c605 |
| postsecondary_c_11_report_2022.xlsx | ef1d0ae19d4fcdfc9a7de5974a98416aff41b889599080978289a46308fc2f70 |
| postsecondary_c_11_report_2023.csv | b777ea2a9e3a877fd45794589b030bca60fa09f0e04afb39052e8b475c18cf1e |
| postsecondary_c_11_report_2024.csv | b73cc10a1604f23c1f8eb0859833fcae1074a0b572d3af0a7a3cc74d2d4cd4af |

## Excel Sheet Structure

Sheet names are inconsistent across the 11 Excel files — the transform must pick the data sheet by **index (first sheet)** rather than by hard-coded name. Two files (2014, 2022) contain an extra `SQL` sheet that holds a reference Oracle SQL query showing how the publisher encodes suppression (`CASE WHEN {metric} < 10 THEN 'TFS' ELSE TO_CHAR({metric}) END`) — skip this sheet during transform.

| File(s) | Sheets | Notes |
|---------|--------|-------|
| 2012.xlsx | `C11_Data_HS Graduate 2010` (Data) | Single data sheet; sheet name encodes the HS graduation cohort year. |
| 2013.xlsx | `Export Worksheet` (Data) | Single data sheet. |
| 2014.xlsx | `Export Worksheet` (Data), `SQL` (Metadata) | `SQL` holds the SELECT query used to generate the export. Skip during transform. |
| 2015.xlsx - 2019.xlsx | `C11_FY{YYYY}_HS Graduates {YYYY}_En` (Data) | Single data sheet; name encodes fiscal year and graduating-class year (e.g., `C11_FY2019_HS Graduates 2017_En`). |
| 2020.xlsx, 2021.xlsx | `Export Worksheet` (Data) | Single data sheet. |
| 2022.xlsx | `Export Worksheet` (Data), `SQL` (Metadata) | Same `SQL` reference sheet as 2014. Skip during transform. |

All data is on a single sheet per file — the transform never needs to concatenate multiple sheets.

**Three-row header layout on the data sheet (Eras 1 and 3).** The header occupies three rows and the actual data starts on row 3 (zero-indexed):

- Row 0: Free-text note — literal cell `"TFS stands for Too Few Students"` in column A, rest of the row is null.
- Row 1: Demographic-group labels (sparse / merged). Labels appear only above the *first* of the two metric columns for each group: `Total All`, `Male`, `Female`, `Free Reduced Lunch`, `Migrant`, `LEP`, `Disability`, `Hispanic`, `Two or More Race(s)`, `American Indian or Alaskan Native`, `Asian`, `Black`, `White`, and `Pacific Islander` (absent in 2012).
- Row 2: Metric column headers — five identifier columns (`School Year`, `School District Code`, `School District Name`, `School Code`, `School Name`) followed by 13 or 14 demographic groups × 2 metrics (`Total High School Graduates`, `Number of High School Graduates Enrolled in Postsecondary Institution`), repeated across all demographic blocks.
- Row 3+: Data rows.

**Two-row header layout (Era 2).** The 2013 and 2014 files **omit Row 0** (no TFS note cell); the header is only two rows: Row 0 holds the demographic-group labels, Row 1 holds the metric headers, and data starts on row 2.

The transform must **forward-fill the demographic-group row across merged cells** and synthesize combined column names (e.g., `male__hs_grads`, `male__in_college`) before reading row-oriented data, otherwise polars' `read_excel` will auto-suffix the duplicate `Total High School Graduates` / `Number of High School Graduates Enrolled in Postsecondary Institution` labels with `_1`, `_2`, etc., and the demographic association is lost.

## Summary

This dataset reports the **C11 Postsecondary Enrollment Report** for Georgia public high schools — two raw student counts per demographic subgroup:

1. **Total High School Graduates** — number of students who graduated high school in a given cohort year. Column names vary by era: `{group} Total High School Graduates` (Excel, 2012-2022) and `{GROUP}_HS_GRADS` (CSV, 2023-2024).
2. **Number of High School Graduates Enrolled in Postsecondary Institution** — of those graduates, how many enrolled in any postsecondary institution (in-state or out-of-state, 2-year or 4-year). Column names: `{group} Number of High School Graduates Enrolled in Postsecondary Institution` (Excel) and `{GROUP}_IN_COLLEGE` / `TOTAL_ENROLLED_IN_COLLEGE` (CSV).

Each metric is reported separately for 14 demographic subgroups (13 in 2012 — Pacific Islander was added beginning with the 2013 report): Total All, Male, Female, Free / Reduced Lunch, Migrant, LEP (Limited English Proficiency), Disability / SWD (Students with Disabilities), Hispanic, Two or More Races, American Indian / Alaskan Native, Asian, Black, White, and Pacific Islander.

The bronze layout is **wide** (one row per school-year-entity, with 26 or 28 metric columns). The gold transform should **unpivot** it into a tidy `(year, district_code, school_code, demographic) × 2-metric` fact layout. No percentages or derived rates are computed in the bronze data — downstream consumers can derive the postsecondary enrollment rate by dividing `in_college` by `hs_grads`.

This is the sibling of `postsecondary_c12_report`, which carries the same demographic structure but adds a third metric (students earning ≥24 credits within 2 years of enrollment) and uses a 4-year filename-to-data offset instead of 2.

## Eras

### Era 1: 2012 (HS grads 2010)

Single file at the start of the series; **missing the `Pacific Islander` demographic group** that every later file carries. 26 metric columns = 13 demographic subgroups × 2 metrics.

| Column | Description |
|--------|-------------|
| School Year | HS graduating class year (integer). Single value per file: `2010`. |
| School District Code | 3-digit GOSA school-system code. Stored as **integer** in 2012 (e.g., `601`, not `0601`). State-total row uses literal `ALL`. |
| School District Name | District proper-name (e.g., `Appling County`). State-total row is `All Systems`. |
| School Code | 3/4-character GOSA school code, stored as **integer** in 2012 (e.g., `103`, not `0103`). District-total rows use literal `ALL`. |
| School Name | School proper-name. District-total rows use `All Schools`. |
| `{demographic}` Total High School Graduates | Count of HS graduates in the subgroup. Stored as string because cells with fewer than 10 students are replaced with `TFS` (Too Few Students). |
| `{demographic}` Number of High School Graduates Enrolled in Postsecondary Institution | Count of graduates who enrolled in a postsecondary institution. Same storage / suppression pattern. |

Demographics present in Era 1 (13): `Total All`, `Male`, `Female`, `Free Reduced Lunch`, `Migrant`, `LEP`, `Disability`, `Hispanic`, `Two or More Race(s)`, `American Indian or Alaskan Native`, `Asian`, `Black`, `White`. **Pacific Islander is missing.**

#### Sample Data

Selected columns from 5 rows of `postsecondary_c_11_report_2012.xlsx`:

```
shape: (5, 11)
┌─────────┬─────────┬─────────────────────┬─────────┬──────────────────────┬────────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│ SY      │ DstCode │ DstName             │ SchCode │ SchName              │ TotAll_HS  │ TotAll_C │ Black_HS │ Black_C  │ White_HS │ White_C  │
╞═════════╪═════════╪═════════════════════╪═════════╪══════════════════════╪════════════╪══════════╪══════════╪══════════╪══════════╪══════════╡
│ 2010    │ 739     │ Towns County        │ 204     │ Towns County HS      │ 55         │ 43       │ TFS      │ TFS      │ 55       │ 43       │
│ 2010    │ 648     │ Douglas County      │ 187     │ Alexander HS         │ 430        │ 299      │ 74       │ 53       │ 310      │ 217      │
│ 2010    │ 786     │ Social Circle City  │ 300     │ Social Circle HS     │ 97         │ 61       │ 27       │ 13       │ 65       │ 45       │
│ 2010    │ 714     │ Pike County         │ ALL     │ All Schools          │ 207        │ 154      │ 28       │ 20       │ 175      │ 131      │
│ 2010    │ 735     │ Terrell County      │ 105     │ Terrell HS           │ 73         │ 53       │ 72       │ 53       │ TFS      │ TFS      │
└─────────┴─────────┴─────────────────────┴─────────┴──────────────────────┴────────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
```

#### Statistics

- Rows: 588 (1 state + 180 districts + 407 schools)
- Columns: 31 (5 identifiers + 13 demographics × 2 metrics = 26 metric columns)
- Single `School Year` value: `2010`
- Distinct school districts: 180 (plus 1 `All Systems` state-total row)
- State-total row: `School District Code='ALL'`, `School District Name='All Systems'`, `School Code='ALL'`, `School Name='All Schools'`
- District-total rows: one per district — `School Code='ALL'`, `School Name='All Schools'`
- School rows: 407 (non-`ALL` School Code)
- Total `TFS` occurrences across all metric cells: **8,174** (of 15,288 metric cells = 53.5%)

#### Null Counts

All 31 columns have **0** null values. Missing / suppressed data is encoded as the literal string `TFS`, not as null.

#### Categorical Columns

| Column | Distinct Values / Pattern |
|--------|---------------------------|
| School Year | `[2010]` — constant per file. |
| School District Code | 180 distinct district codes (3-digit integers in the `601`-`793` range, plus 7-digit charter/state-school codes) + literal `ALL` for the state-total row. |
| School District Name | 180 district names + `All Systems`. |
| School Code | 168 distinct school codes (integers, no leading-zero padding) + `ALL` (state + 180 district-total rows = 181 `ALL` values total). |
| School Name | 402 distinct school / aggregate names. |

#### Suppression Markers

Every one of the 26 metric columns uses **`TFS`** as the sole non-numeric value. `TFS` stands for **Too Few Students** (confirmed by the A1 note cell in Row 0, and by the SQL generator visible in the 2022 file's `SQL` sheet: `CASE WHEN {metric} < 10 THEN 'TFS' ELSE TO_CHAR({metric}) END` — i.e., any count below 10 is suppressed).

| Column | Non-Numeric Values |
|--------|-------------------|
| School District Code (aggregate-level marker) | `['ALL']` (1 occurrence — the state-total row) |
| School Code (aggregate-level marker) | `['ALL']` (181 occurrences — 1 state + 180 district totals) |
| All 26 metric columns (`Total All Total High School Graduates` through `White Number of High School Graduates Enrolled in Postsecondary Institution`) | `['TFS']` |

Representative counts: `Total All HS Grads` 10 TFS / 588 rows; `Male In College` 35 TFS; `Free Reduced Lunch In College` 117 TFS; `Black HS Grads` 76 TFS; `White In College` 114 TFS; `LEP HS Grads` 10 TFS (of 11 non-null observations — LEP is nearly always suppressed).

---

### Era 2: 2013-2014 (HS grads 2011-2012)

Two files with the **14-demographic-group** structure — adds `Pacific Islander` relative to Era 1, otherwise same metric definitions. **Distinct two-row header layout**: these two files omit the Row 0 TFS note, so the demographic-group row is Row 0 and the metric row is Row 1 (data starts on Row 2 — one row earlier than Eras 1 and 3).

| Column | Description |
|--------|-------------|
| School Year | HS graduating class year (integer). Single value per file (`2011` or `2012`). |
| School District Code | 3-digit GOSA school-system code. Stored as **string** in these two files (leading zeros preserved where applicable, e.g., `601`). State-total row: literal `ALL`. |
| School District Name | District proper-name. State-total row is `All Systems`. |
| School Code | 4-character school code stored as **string** with leading zeros preserved (e.g., `0103` rather than `103`). District-total rows: literal `ALL`. |
| School Name | School proper-name. District-total rows: `All Schools`. |
| `{demographic}` Total High School Graduates | HS graduate count per subgroup. String with `TFS` for <10. |
| `{demographic}` Number of High School Graduates Enrolled in Postsecondary Institution | Enrolled-in-college count per subgroup. Same encoding. |

Demographics present in Era 2 (14): adds `Pacific Islander` to the 13 from Era 1.

#### Sample Data

Selected columns from 5 rows of `postsecondary_c_11_report_2013.xlsx`:

```
shape: (5, 9)
┌────────┬─────────┬───────────────────┬─────────┬────────────────────┬───────────┬───────────┬───────────┬───────────┐
│ SY     │ DstCode │ DstName           │ SchCode │ SchName            │ TotAll_HS │ TotAll_C  │ Pacific_HS│ Pacific_C │
╞════════╪═════════╪═══════════════════╪═════════╪════════════════════╪═══════════╪═══════════╪═══════════╪═══════════╡
│ 2011   │ 601     │ Appling County    │ 0103    │ Appling County HS  │ 162       │ 100       │ TFS       │ TFS       │
│ 2011   │ 601     │ Appling County    │ ALL     │ All Schools        │ 162       │ 100       │ TFS       │ TFS       │
│ 2011   │ 602     │ Atkinson County   │ 0103    │ Atkinson County HS │ 83        │ 48        │ TFS       │ TFS       │
│ 2011   │ ALL     │ All Systems       │ ALL     │ All Schools        │ 88017     │ 64893     │ 67        │ 44        │
│ 2011   │ 660     │ Fulton County     │ 0392    │ Chattahoochee HS   │ 414       │ 371       │ TFS       │ TFS       │
└────────┴─────────┴───────────────────┴─────────┴────────────────────┴───────────┴───────────┴───────────┴───────────┘
```

#### Statistics

- 2013 file: 592 rows (1 state + 178 districts + 413 schools)
- 2014 file: 608 rows (1 state + 182 districts + 425 schools)
- Combined Era 2: 1,200 rows across 2 files
- Columns per file: 33 (5 identifiers + 14 demographics × 2 metrics = 28 metric columns)
- `School Year` values: `2011` (2013 file) and `2012` (2014 file)
- Total `TFS` occurrences across all metric cells in Era 2: **17,908** (of 33,600 metric cells ≈ 53.3%)

#### Null Counts

All 33 columns have **0** null values across both files. Missing / suppressed data is encoded as the literal string `TFS`.

#### Categorical Columns

| Column | Distinct Values / Pattern |
|--------|---------------------------|
| School Year | `[2011]` (2013 file) or `[2012]` (2014 file) — single value per file. |
| School District Code | ~180 distinct district codes per file (zero-padded 3-digit strings) + literal `ALL` for the state-total row. |
| School District Name | ~180 district names per file + `All Systems`. |
| School Code | ~175-185 distinct school codes (zero-padded 4-digit strings) + `ALL` (state + per-district aggregates). |
| School Name | ~400-430 distinct school / aggregate names per file. |

#### Suppression Markers

Same `TFS` convention as Era 1. Sparse demographic groups such as `American Indian or Alaskan Native`, `Pacific Islander`, `Migrant`, and `LEP` are almost always suppressed at the school level (see the 2013 file where `Pacific Islander Total High School Graduates` has only 2 distinct values: `67` (the state total) and `TFS` (everything else)).

| Column | Non-Numeric Values |
|--------|-------------------|
| School District Code (aggregate-level marker) | `['ALL']` (1 per file) |
| School Code (aggregate-level marker) | `['ALL']` (179-183 per file) |
| All 28 metric columns | `['TFS']` |

---

### Era 3: 2015-2022 (HS grads 2013-2020)

Eight files with the **same 14-demographic, 28-metric-column structure** as Era 2. Restores the Row 0 TFS note (three-row header, identical layout to Era 1). 33 columns total per file.

| Column | Description |
|--------|-------------|
| School Year | HS graduating class year (integer). Single value per file (`2013` through `2020` across the 8 files). |
| School District Code | 3-digit GOSA school-system code. **Format varies by year** — stored as `int` in 2015-2019 (e.g., `601`) and as `str` with leading zeros in 2020-2022 (e.g., `601`). State-total row: literal `ALL`. |
| School District Name | District proper-name. State-total row is `All Systems`. |
| School Code | 4-character school code. **Format varies by year** — stored as `int` (no leading-zero padding: `103`, `113`) in 2015-2019, and as `str` with leading-zero padding (`0103`, `0114`) in 2020-2022. District-total rows: literal `ALL`. |
| School Name | School proper-name. District-total rows: `All Schools`. |
| `{demographic}` Total High School Graduates | HS graduate count per subgroup. String with `TFS` for <10. |
| `{demographic}` Number of High School Graduates Enrolled in Postsecondary Institution | Enrolled-in-college count per subgroup. Same encoding. |

Demographics present in Era 3 (14): identical to Era 2.

#### Sample Data

Selected columns from 5 rows of `postsecondary_c_11_report_2019.xlsx`:

```
shape: (5, 11)
┌───────┬─────────┬──────────────────┬─────────┬─────────────────────┬────────────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ SY    │ DstCode │ DstName          │ SchCode │ SchName             │ TotAll_HS  │ TotAll_C  │ Black_HS │ Black_C  │ White_HS │ White_C  │
╞═══════╪═════════╪══════════════════╪═════════╪═════════════════════╪════════════╪═══════════╪══════════╪══════════╪══════════╪══════════╡
│ 2017  │ ALL     │ All Systems      │ ALL     │ All Schools         │ 106934     │ 72472     │ 39070    │ 25398    │ 47731    │ 34072    │
│ 2017  │ 601     │ Appling County   │ 103     │ Appling County HS   │ 198        │ 118       │ 45       │ 30       │ 116      │ 68       │
│ 2017  │ 601     │ Appling County   │ ALL     │ All Schools         │ 198        │ 118       │ 45       │ 30       │ 116      │ 68       │
│ 2017  │ 602     │ Atkinson County  │ 103     │ Atkinson County HS  │ 97         │ 60        │ 18       │ 10       │ 53       │ 37       │
│ 2017  │ 602     │ Atkinson County  │ ALL     │ All Schools         │ 97         │ 60        │ 18       │ 10       │ 53       │ 37       │
└───────┴─────────┴──────────────────┴─────────┴─────────────────────┴────────────┴───────────┴──────────┴──────────┴──────────┴──────────┘
```

#### Statistics

| File | Rows | State | Districts | Schools | School Year |
|------|------|-------|-----------|---------|-------------|
| 2015.xlsx | 612 | 1 | 183 | 428 | 2013 |
| 2016.xlsx | 618 | 1 | 187 | 430 | 2014 |
| 2017.xlsx | 628 | 1 | 187 | 440 | 2015 |
| 2018.xlsx | 626 | 1 | 186 | 439 | 2016 |
| 2019.xlsx | 634 | 1 | 190 | 443 | 2017 |
| 2020.xlsx | 644 | 1 | 190 | 453 | 2018 |
| 2021.xlsx | 646 | 1 | 190 | 455 | 2019 |
| 2022.xlsx | 649 | 1 | 190 | 458 | 2020 |

- Combined Era 3: 5,057 rows across 8 files
- Columns per file: 33 (5 identifiers + 28 metric columns)
- Total `TFS` occurrences across all metric cells in Era 3: **72,857** (of 141,596 metric cells ≈ 51.5%)

#### Null Counts

All 33 columns have **0** null values across all 8 files. Missing / suppressed data is encoded as the literal string `TFS`.

#### Categorical Columns

| Column | Distinct Values / Pattern |
|--------|---------------------------|
| School Year | Single value per file — `2013`, `2014`, `2015`, `2016`, `2017`, `2018`, `2019`, `2020` respectively. |
| School District Code | 183-190 distinct district codes per file + literal `ALL` for state-total row. **Integer type in 2015-2019, string type in 2020-2022.** |
| School District Name | 183-190 district names + `All Systems`. |
| School Code | ~170-195 distinct school codes + `ALL`. **Integer type in 2015-2019 (no leading zero), string type in 2020-2022 (4-digit with leading zero).** |
| School Name | ~420-460 distinct school / aggregate names per file. |

#### Suppression Markers

Same `TFS` convention as Eras 1 and 2. Sparse demographics (Migrant, Pacific Islander, American Indian or Alaskan Native) are almost entirely suppressed; the Disability group becomes overwhelmingly suppressed starting in 2019 (`Disability Total High School Graduates` has 168/634 TFS in 2019 — about 26% of rows).

| Column | Non-Numeric Values |
|--------|-------------------|
| School District Code (aggregate-level marker) | `['ALL']` (1 per file) |
| School Code (aggregate-level marker) | `['ALL']` (184-191 per file) |
| All 28 metric columns | `['TFS']` |

---

### Era 4: 2023-2024 (HS grads 2021-2022) — CSV Format

Two **CSV** files with a flat, single-row header and two extra identifier columns (`#RPT_NAME`, `REPORTING_YEAR`) that are not present in the Excel eras. 35 columns total per file. Demographic group names are embedded directly into column names (e.g., `MALE_HS_GRADS`, `HISPANIC_IN_COLLEGE`) rather than derived from a merged-cell header.

| Column | Description |
|--------|-------------|
| `#RPT_NAME` | Constant string `C11 Report Metrics`. Appears to be a report-identifier header emitted by the GOSA CSV export. |
| `REPORTING_YEAR` | Publication / fiscal year. Single value per file: `2023` or `2024`. Matches the filename year. |
| `SCHOOL_YEAR` | HS graduating class year. Single value per file: `2021` (2023 file) or `2022` (2024 file). |
| `SCHOOL_DISTRCT_CD` | 3-digit GOSA school-system code (string, leading zeros preserved). Note the misspelling `DISTRCT` (no second `I`). State-total row: literal `ALL`. |
| `SCHOOL_DSTRCT_NM` | District proper-name. Misspelling `DSTRCT` (no `I`). State-total row: `All Systems`. |
| `INSTN_NUMBER` | 4-character school code (zero-padded string, e.g., `0103`). District-total rows: literal `ALL`. |
| `INSTN_NAME` | School proper-name. District-total rows: `All Schools`. |
| `TOTAL_HS_GRADS`, `TOTAL_ENROLLED_IN_COLLEGE` | Total-all HS graduates and postsecondary-enrolled counts. |
| `MALE_HS_GRADS`, `MALE_IN_COLLEGE` | Male subgroup. |
| `FEMALE_HS_GRADS`, `FEMALE_IN_COLLEGE` | Female subgroup. |
| `FRL_HS_GRADS`, `FRL_IN_COLLEGE` | Free / Reduced Lunch. |
| `MIGRANT_HS_GRADS`, `MIGRANT_IN_COLLEGE` | Migrant. |
| `LEP_HS_GRADS`, `LEP_IN_COLLEGE` | Limited English Proficiency. |
| `SWD_HS_GRADS`, `SWD_IN_COLLEGE` | Students with Disabilities. |
| `HISPANIC_HS_GRADS`, `HISPANIC_IN_COLLEGE` | Hispanic. |
| `TWOORMORE_HS_GRADS`, `TWOORMORE_IN_COLLEGE` | Two or More Races. |
| `NATIVE_HS_GRADS`, `NATIVE_IN_COLLEGE` | American Indian / Alaskan Native. |
| `ASIAN_HS_GRADS`, `ASIAN_IN_COLLEGE` | Asian. |
| `BLACK_HS_GRADS`, `BLACK_IN_COLLEGE` | Black. |
| `WHITE_HS_GRADS`, `WHITE_IN_COLLEGE` | White. |
| `PACIFIC_HS_GRADS`, `PACIFIC_IN_COLLEGE` | Pacific Islander. |

Demographics present in Era 4 (14): identical demographic coverage to Eras 2-3, but column names are flat and capitalized (e.g., `FRL` maps to `Free Reduced Lunch`, `SWD` maps to `Disability`, `NATIVE` maps to `American Indian or Alaskan Native`, `TWOORMORE` maps to `Two or More Race(s)`).

#### Sample Data

First 5 rows of `postsecondary_c_11_report_2023.csv` (selected columns):

```
shape: (5, 10)
┌──────────────────┬─────────┬────────┬─────────────────┬─────────────┬───────────────────┬─────────┬─────────┬─────────┬────────┐
│ #RPT_NAME        │ RPT_YR  │ SY     │ DistCd          │ InstNum     │ InstName          │ TotHS   │ TotColl │ BlackHS │ BlackC │
╞══════════════════╪═════════╪════════╪═════════════════╪═════════════╪═══════════════════╪═════════╪═════════╪═════════╪════════╡
│ C11 Report Metr. │ 2023    │ 2021   │ ALL             │ ALL         │ All Schools       │ 110804  │ 71791   │ 38924   │ 24132  │
│ C11 Report Metr. │ 2023    │ 2021   │ 601             │ ALL         │ All Schools       │ 215     │ 113     │ 57      │ 21     │
│ C11 Report Metr. │ 2023    │ 2021   │ 601             │ 0103        │ Appling County HS │ 215     │ 113     │ 57      │ 21     │
│ C11 Report Metr. │ 2023    │ 2021   │ 602             │ ALL         │ All Schools       │ 116     │ 50      │ 17      │ 10     │
│ C11 Report Metr. │ 2023    │ 2021   │ 602             │ 0103        │ Atkinson County HS│ 116     │ 50      │ 17      │ 10     │
└──────────────────┴─────────┴────────┴─────────────────┴─────────────┴───────────────────┴─────────┴─────────┴─────────┴────────┘
```

#### Statistics

| File | Rows | State | Districts | Schools | SCHOOL_YEAR |
|------|------|-------|-----------|---------|-------------|
| 2023.csv | 652 | 1 | 192 | 459 | 2021 |
| 2024.csv | 659 | 1 | 194 | 464 | 2022 |

- Combined Era 4: 1,311 rows across 2 files
- Columns per file: 35 (7 identifiers + 28 metric columns)
- Total `TFS` occurrences across all metric cells: 9,317 (2023 file, of 18,256 ≈ 51.0%) and 9,482 (2024 file, of 18,452 ≈ 51.4%)

#### Null Counts

All 35 columns have **0** null values across both files. Missing / suppressed data is encoded as the literal string `TFS`.

#### Categorical Columns

| Column | Distinct Values / Pattern |
|--------|---------------------------|
| `#RPT_NAME` | `['C11 Report Metrics']` — constant. |
| `REPORTING_YEAR` | Single value per file — `2023` or `2024`. |
| `SCHOOL_YEAR` | Single value per file — `2021` or `2022`. |
| `SCHOOL_DISTRCT_CD` | ~193 distinct zero-padded district codes per file + literal `ALL`. |
| `SCHOOL_DSTRCT_NM` | ~193 district names + `All Systems`. |
| `INSTN_NUMBER` | ~206 distinct 4-digit zero-padded school codes + `ALL`. |
| `INSTN_NAME` | ~451-460 distinct school / aggregate names. |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| `SCHOOL_DISTRCT_CD` (aggregate-level marker) | `['ALL']` (1 per file) |
| `INSTN_NUMBER` (aggregate-level marker) | `['ALL']` (193-195 per file) |
| All 28 metric columns (`TOTAL_HS_GRADS` through `PACIFIC_IN_COLLEGE`) | `['TFS']` |

---

## ETL Considerations

1. **Three distinct header patterns across Excel files (plus flat CSV in Era 4).** The transform must branch by file/era:
   - Era 1 (2012) and Era 3 (2015-2022): three-row header — skip row 0 (TFS note), forward-fill row 1 (demographic groups across merged cells), combine row 1 + row 2 into flat column names, then read from row 3.
   - Era 2 (2013-2014): two-row header — **no row 0 TFS note** — forward-fill row 0 (demographic groups), combine with row 1 (metric labels), read from row 2.
   - Era 4 (2023-2024): single-row CSV header; already flat.

2. **Never rely on hard-coded Excel sheet names** — they vary per year (`C11_Data_HS Graduate 2010`, `Export Worksheet`, `C11_FY{YYYY}_HS Graduates {YYYY}_En`). Always read the first sheet by index. The `SQL` sheets in 2014 and 2022 contain only a reference Oracle SQL string and must be skipped.

3. **Era 1 (2012) has only 13 demographic groups — no Pacific Islander column.** When unpivoting, the transform must allow the Pacific Islander group to be absent in 2012 and emit rows with `pacific_hs_grads` / `pacific_in_college` as null, not error out on missing columns.

4. **District and school code formatting is inconsistent across years.** Coerce both to `pl.Utf8` and zero-pad per `education/CLAUDE.md` conventions: `district_code` → `zfill(3)`, `school_code` → `zfill(4)`. Never use `.str.slice(0, 3)` to truncate because charter-school district codes are 7 digits.
   - 2012: integer codes (district `601`, school `103`) — cast to string then pad.
   - 2013, 2014, 2020-2022: string codes already zero-padded (`0103`).
   - 2015-2019: integer codes in Excel (`103`) — zero-pad to `0103`.
   - 2023-2024: already zero-padded strings in CSV.

5. **Filename year ≠ data year.** Use the `School Year` / `SCHOOL_YEAR` column value for the fact-table `year` (HS graduating class year), not the filename year. The publication year (`REPORTING_YEAR` in Era 4) is incidental; filename year = data year + 2 is a consistent mapping but the CSV value is authoritative. Per the education domain convention, `year` should represent the HS graduating cohort year (e.g., `year=2020` means the 2019-2020 school year's graduates).

6. **Demographic-group name inconsistencies across eras.** The same demographic group uses three different tokens across bronze:
   - `Disability` (Excel) ↔ `SWD_*` (CSV) → gold `swd`
   - `American Indian or Alaskan Native` (Excel) ↔ `NATIVE_*` (CSV) → gold `native` / `aian`
   - `Two or More Race(s)` (Excel) ↔ `TWOORMORE_*` (CSV) → gold `twoormore`
   - `Free Reduced Lunch` (Excel) ↔ `FRL_*` (CSV) → gold `frl`
   - `Pacific Islander` (Excel) ↔ `PACIFIC_*` (CSV) → gold `pacific` / `nhpi`
   - `Total All` (Excel) ↔ `TOTAL_*` (CSV) → gold `all_students`
   The transform needs a single canonical mapping dictionary to normalize across eras; the canonical names should match the global demographics dimension at `data/gold/_dimensions/demographics.parquet`.

7. **Suppression marker is `TFS` (Too Few Students, <10).** The A1 cell text and the 2022 SQL-sheet query both confirm: `CASE WHEN {metric} < 10 THEN 'TFS' ELSE TO_CHAR({metric}) END`. Cast metric columns to `Int64` with `strict=False`; `TFS` becomes null. Do **not** coerce `TFS` to `0` — that would fabricate enrollment numbers.

8. **Aggregate-row sentinels (`ALL`, `All Systems`, `All Schools`) must become NULL per `education/CLAUDE.md`.** Use a derived `detail_level` column (`state` / `district` / `school`) during transform to drive geography-nulling; then drop `detail_level` before writing, because gold splits fact tables into `states.parquet`, `districts.parquet`, `schools.parquet` per the domain convention.

9. **Wide-to-tidy unpivot.** The bronze layout is (one row per school-year-entity) × (14 demographics × 2 metrics). The gold layout should be one row per `(year, district_code, school_code, demographic)` with two metric columns (`hs_grads`, `in_college`). Suggested unpivot path: build a multi-index of `(demographic, metric)` from flattened column headers, then melt once per metric family, then pivot the `metric` dimension back to wide (two metric columns per row).

10. **Pacific Islander, American Indian/Alaskan Native, Migrant, LEP are heavily suppressed.** Nearly every row at school-level has `TFS` for these groups; only state-total and a handful of large districts have real values. This is not a data bug — it is a consequence of the <10 threshold combined with small subgroup sizes. Gold should still emit rows for these groups (with null metrics) rather than silently dropping them, so downstream consumers know suppression is distinguishable from missing coverage.

11. **Row-0 TFS note cell can leak into column names.** In Eras 1 and 3 the first column of Row 0 literally reads `"TFS stands for Too Few Students"`; if the transform calls `pl.read_excel(... has_header=True)` naively, polars will use Row 0 as the header and produce garbled column names (e.g., `'"TFS stands for Too Few Students"'` for column A plus `__UNNAMED__N` for every other column). Always read with `header_row=None` or set `skip_rows` / manual header stitching.

12. **No per-grade-level breakdown.** Unlike some other GOSA topics (e.g., `enrollment_by_grade_level`), this topic reports only the total graduating class — there are no grade-level rows, no gender-by-race crosstabs, and no age-based splits. The single categorical dimension beyond geography is `demographic`.

13. **No year column drift.** The `School Year` / `SCHOOL_YEAR` column always holds a **single** integer (never a range like `2019-2020`) and the value is consistent across all rows of a given file. The transform can safely read it from the first row and propagate.

## Gold Schema Classification

Across all four eras the bronze columns fall into these gold roles. Column names below use the Era 4 CSV form (flat `UPPER_SNAKE_CASE`) as the canonical bronze name; Era 1-3 Excel forms with embedded demographic labels should be normalized to the same names during transform.

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| `#RPT_NAME` (Era 4) | not_in_gold | - | Constant `C11 Report Metrics`; redundant with the topic identity. |
| `REPORTING_YEAR` (Era 4) | not_in_gold | - | Publication / fiscal year; redundant with filename year. The gold fact uses `year` (HS grad cohort) not the publication year. |
| `School Year` (Eras 1-3) / `SCHOOL_YEAR` (Era 4) | fact_key | `year` | HS graduating-class year; cast `pl.Int32`. Per `education/CLAUDE.md`, `year` = HS graduating class year (ending calendar year of the school year). |
| `School District Code` (Eras 1-3) / `SCHOOL_DISTRCT_CD` (Era 4) | fact_key | `district_code` | FK to districts dimension. Coerce to `pl.Utf8`, zfill(3). Aggregate sentinel `ALL` → NULL in gold (detail_level = state). |
| `School District Name` (Eras 1-3) / `SCHOOL_DSTRCT_NM` (Era 4) | dimension_attribute | - | `district_name` lives in the districts dimension table; not stored in the fact table. |
| `School Code` (Eras 1-3) / `INSTN_NUMBER` (Era 4) | fact_key | `school_code` | FK to schools dimension. Coerce to `pl.Utf8`, zfill(4). Aggregate sentinel `ALL` → NULL in gold (detail_level in {state, district}). |
| `School Name` (Eras 1-3) / `INSTN_NAME` (Era 4) | dimension_attribute | - | `school_name` lives in the schools dimension table; not stored in the fact table. |
| `{Group} Total High School Graduates` (Eras 1-3) / `{GROUP}_HS_GRADS` / `TOTAL_HS_GRADS` (Era 4) | fact_metric | `hs_grads` | Count of HS graduates in the demographic subgroup. `pl.Int64` after cast with strict=False. `TFS` → NULL. |
| `{Group} Number of High School Graduates Enrolled in Postsecondary Institution` (Eras 1-3) / `{GROUP}_IN_COLLEGE` / `TOTAL_ENROLLED_IN_COLLEGE` (Era 4) | fact_metric | `in_college` | Count of HS graduates enrolled in any postsecondary institution. `pl.Int64`. `TFS` → NULL. |
| Demographic-group label (from merged Row 1 in Excel; embedded in column prefix in CSV) | fact_key | `demographic` | Unpivoted from the wide bronze layout. FK to global demographics dimension (`data/gold/_dimensions/demographics.parquet`). Canonical values: `all_students`, `male`, `female`, `frl`, `migrant`, `lep`, `swd`, `hispanic`, `twoormore`, `native` (or `aian`), `asian`, `black`, `white`, `pacific` (or `nhpi`). |

**Implicit gold columns not present in bronze but required by downstream conventions:**

- `detail_level` — derived during transform from the `(district_code, school_code)` sentinel pattern; used to split fact rows into `states.parquet`, `districts.parquet`, `schools.parquet` per the education domain convention (not stored in fact tables).
- `school_year` — derivable from `year` (e.g., `year=2020` → `school_year='2019-2020'`); per `education/CLAUDE.md`, **not stored** in the fact table.

**Gold directory layout (per `education/CLAUDE.md`):**

```
data/gold/education/postsecondary_c11_report/
├── year=2010/
│   ├── states.parquet       # 1 row × 13 demographics = 13 rows
│   ├── districts.parquet    # ~180 districts × 13 demographics
│   └── schools.parquet      # ~400 schools × 13 demographics  (no pacific islander in 2010)
├── year=2011/
│   ├── states.parquet
│   ├── districts.parquet
│   └── schools.parquet
├── ... (2012 through 2022) ...
├── _metadata.json
└── README.md
```
