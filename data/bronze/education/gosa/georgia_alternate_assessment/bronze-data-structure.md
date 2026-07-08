# georgia_alternate_assessment_gaa — Bronze Data Structure

## Overview

- Topic: georgia_alternate_assessment_gaa
- Source: gosa
- Files: 16 files spanning school years 2003-04 through 2023-24 (filename years 2004–2007 and 2011–2024; 2008–2010, 2020, 2021 missing from bronze)
- Unreadable files: none (2005.csv, 2006.csv, 2007.xls are **Excel binary `.xls` files** — the 2005 and 2006 files have a `.csv` extension but are actually OLE2 `Composite Document` Excel workbooks; all three must be read with `xlrd`, not `pl.read_csv`)
- Year representation:
  - **Eras 1 & 2 (2004–2007)**: year is **only in the filename** — there is no year column. The four columns are `SysSchoolID`/`sysschoolid`, `School Name`/`schoolname`, an enrollment column, and a tested-count column
  - **Eras 3–6 (2011–2024)**: year is both in the filename and in a `LONG_SCHOOL_YEAR` column in `"YYYY-YY"` format (e.g., `"2023-24"`)
- Filename-to-data year offset: filename year = **ending calendar year** of the school year (e.g., `georgia_alternate_assessment_gaa_2024.csv` contains `LONG_SCHOOL_YEAR = "2023-24"`). No offset — filename year always equals the spring/ending calendar year
- Detail levels: state, district, school (encoded differently across eras — see below)
  - **Eras 1 & 2 (2004–2007)**: encoded in `SysSchoolID`/`sysschoolid` via `"district:school"` pattern — `"ALL:ALL"` = state, `"<dist>:ALL"` = district, `"<dist>:<school>"` = school
  - **Eras 3–6 (2011–2024)**: encoded in `SCHOOL_DISTRCT_CD` / `INSTN_NUMBER` via the sentinel `"ALL"` — both `"ALL"` = state, only `INSTN_NUMBER = "ALL"` = district, both set = school
- Percentage scale: 0–100 (the `*_PERCENT` / `*_PCT` columns in Eras 3–6 are reported on a 0–100 scale; must be divided by 100 at gold time per `data-cleaning-standards`)
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| georgia_alternate_assessment_gaa_2004.csv | 49546b06e2a19e16cef9f4a59949b4a78a4ad235496cfd44eb7a66d909fb73f6 |
| georgia_alternate_assessment_gaa_2005.csv | 73bb38c3c3d8296a3897833d9cb92aa999ffc29686fdcccd8524f80a1b24ad77 |
| georgia_alternate_assessment_gaa_2006.csv | fd91711fa01ffadee265ce7e75e530b792879fae370c4bdd2b28f91c2cbfb543 |
| georgia_alternate_assessment_gaa_2007.xls | 9e919f98eaa4d0859314d3d431bb04632769c5d33d8522a5d2b864b614411d27 |
| georgia_alternate_assessment_gaa_2011.csv | fdfdc2683a10362b661abebe77af7bf0b19f0463b2673e2129c2b033e8ca7c60 |
| georgia_alternate_assessment_gaa_2012.csv | df3102709e0cc154862ac625676632ffcd002b2d5c5c3c17bb08704b48570b01 |
| georgia_alternate_assessment_gaa_2013.csv | 423443cc5ceec14966a7a45a1962f4c972944d250f16ad6f925152020b196472 |
| georgia_alternate_assessment_gaa_2014.csv | e1ad3059deac22433f322175dd57f0d2e1c0dff2be0436eaf0c21a1799530325 |
| georgia_alternate_assessment_gaa_2015.csv | ba5d3427f4e1e8f15635749bf34e78631228bfc318b0401482e80348df308e25 |
| georgia_alternate_assessment_gaa_2016.csv | 40e4413b786cfd70ac8a9b0c4186f9cd3d5dff0187f68766e2d451f2f6d4a8b8 |
| georgia_alternate_assessment_gaa_2017.csv | 47e6934ff9b8e231e30db65f0005e59007bfaaa8edc8eaefb0db855672d7ef6f |
| georgia_alternate_assessment_gaa_2018.csv | e5eecdd4b3e9f0707a171a0e140cea1a338266608127c0048c0ec6a4258ba4cf |
| georgia_alternate_assessment_gaa_2019.csv | eae4566041f2b4c4b58042fd793160f29755a45aec69a51653d8f570c0962893 |
| georgia_alternate_assessment_gaa_2022.csv | 83f41bd1feecdf1cc0e8bc0b2287ae7d19948d6205b1fc87c6c50da51f876c34 |
| georgia_alternate_assessment_gaa_2023.csv | d073e02408fd0d928da182e0562408e55bc2d8194014ea16ce3c7db231b5eaf4 |
| georgia_alternate_assessment_gaa_2024.csv | 06d2838c5868ee56c16be8f5e0ff8fbcc10dd73e98f8fa1c031409f9a94d8489 |

## Excel Sheet Structure

2005.csv, 2006.csv, and 2007.xls are OLE2 Excel binary files (despite the `.csv` extension on 2005/2006). Every other file is a real CSV.

| File(s) | Sheets | Notes |
|---------|--------|-------|
| 2005.csv | `Sheet1` (Data), `Sheet2` (empty), `Sheet3` (empty) | Read with `xlrd` — file is actually Excel `.xls` despite `.csv` extension |
| 2006.csv | `Sheet1` (Data), `Sheet2` (empty), `Sheet3` (empty) | Same — actually Excel `.xls` despite `.csv` extension |
| 2007.xls | `Sheet1` (Data), `Sheet2` (empty), `Sheet3` (empty) | Legitimate `.xls` — read with `xlrd` |
| All others (`.csv`) | N/A | Plain CSV |

No legend / metadata sheets. The empty `Sheet2` and `Sheet3` in the Excel files should be skipped — `Sheet1` is the only data sheet.

## Summary

Georgia Alternate Assessment (GAA) participation and achievement-level results for Georgia public school students with significant cognitive disabilities. The dataset has **two fundamentally different measures** across its history:

- **2004–2007 (Eras 1 & 2)**: a **participation summary** — rows contain only two metrics per entity: (1) total enrollment in AYP-applicable grades (grades 1–8 and 11), and (2) the count of students taking the GAA at that school/district/state. There are no achievement-level breakdowns, no demographics, and no test-component detail. This matches the "Number of Students Taking the GAA" report referenced in the column name
- **2011–2024 (Eras 3–6)**: a **tidy achievement-level breakdown** — for each `(entity × demographic subgroup × test component)` combination, the data reports the count of students tested plus the count and percentage of students scoring at each of four achievement levels. The achievement level labels (and the set of 3 vs 4 levels in use) change across the three "Era 3+" sub-eras, reflecting curriculum and standards changes. Test components are the four Georgia Milestones subjects: English Language Arts, Mathematics, Science, Social Studies

Users care about GAA participation rates (students tested / enrolled) for the early years and achievement-level mastery percentages for the later years.

## Eras

Data splits into **six eras** based on column schema. Row counts per file are in the statistics tables.

- **Era 1** (2004–2006, 3 files) — 4 columns: `SysSchoolID`, `School Name`, `Enrollment in Grades Applicable to AYP Grades 1 through 8 and 11`, `Number of Students Taking the GAA`
- **Era 2** (2007, 1 file) — Same 4 semantic columns but renamed: `sysschoolid`, `schoolname`, `Enroll`, `Number` (lowercase short labels)
- **Era 3** (2011–2018, 8 files) — 16 cols with `LIMITED_CNT`/`PARTIAL_CNT`/`ADEQUATE_CNT`/`THUROUGH_CNT` (**note the typo — `THUROUGH`, not `THOROUGH`**). `THUROUGH_CNT` and `THUROUGH_PERCENT` are **always `0` or null** in this era (the GAA used a 3-tier scoring system: Limited, Partial, Adequate — the `THUROUGH` column was reserved but never populated)
- **Era 4** (2019, 1 file) — Same 16 columns but with generic proficiency-level names: `Level1_CNT` through `Level4_CNT` and `Level1_PERCENT` through `Level4_PERCENT`. All four levels are populated with real data (GAA moved to a 4-tier scoring system this year)
- **Era 5** (2022–2023, 2 files) — 16 columns with achievement names `LIMITED_CNT`/`PARTIAL_CNT`/`ADEQUATE_CNT`/`THOROUGH_CNT` (**typo corrected** to `THOROUGH`) and matching `*_PERCENT` columns. `"TFS"` is introduced as the suppression marker in these files (in place of the null-valued-cells convention of Eras 3–4)
- **Era 6** (2024, 1 file) — 18 columns: adds two new constant-valued columns (`#ASSMT_CD = "GAA"`, `ACDMC_LVL = "ALL GRADES"`) and renames the achievement levels to match Georgia Milestones: `BEGIN_CNT`/`DEVELOPING_CNT`/`PROFICIENT_CNT`/`DISTINGUISHED_CNT` plus matching `*_PCT` columns (now `_PCT` instead of `_PERCENT`). Also the 4x row count explosion reflects a change in suppression *output* — suppressed rows are now emitted with `"TFS"` counts rather than omitted entirely (63,437 of 63,689 rows are fully suppressed)

Missing years: **2008–2010, 2020, 2021** are absent from bronze. 2020 and 2021 are COVID-era suspensions of state testing; 2008–2010 are gaps in the GOSA Data Dashboard historical coverage.

---

### Era 1: 2004–2006 (3 files)

Files: `georgia_alternate_assessment_gaa_2004.csv`, `georgia_alternate_assessment_gaa_2005.csv` (actually `.xls`), `georgia_alternate_assessment_gaa_2006.csv` (actually `.xls`).

Each row is one entity (state, district, or school). There are **no demographic or test-component breakdowns** in this era — only aggregate counts.

| Column | Description |
|--------|-------------|
| `SysSchoolID` | Entity identifier — `"<district_code>:<school_code>"` pattern. `"ALL:ALL"` = state (1 row), `"<dist>:ALL"` = district (~185 rows), `"<dist>:<school>"` = school (~2,000 rows). District codes are 3-digit strings (e.g., `"601"` for Appling County); school codes are 3- or 4-digit strings |
| `School Name` | Entity name — district name (e.g., `"Appling County"`) on `:ALL` rows, school name (e.g., `"Appling County High School"`) on school rows, and `"State of Georgia"` on the single `ALL:ALL` row |
| `Enrollment in Grades Applicable to AYP Grades 1 through 8 and 11` | Total enrollment in AYP-applicable grades — Int. Float64 dtype in Excel files, Int in the 2004 CSV |
| `Number of Students Taking the GAA` | Count of students who took the GAA at this entity — Int. Float64 dtype in Excel files, Int in the 2004 CSV |

#### Sample Data (2006 representative)

```
shape: (5, 4)
┌─────────────┬──────────────────────────────────┬──────────────────────┬───────────────────────────┐
│ SysSchoolID ┆ School Name                      ┆ Enrollment in Grades ┆ Number of Students Taking │
│             ┆                                  ┆ Applicable...        ┆ the GAA                   │
╞═════════════╪══════════════════════════════════╪══════════════════════╪═══════════════════════════╡
│ 601:1050    ┆ Altamaha Elementary School       ┆ 306.0                ┆ 0.0                       │
│ 601:ALL     ┆ Appling County                   ┆ 2371.0               ┆ 22.0                      │
│ 601:177     ┆ Appling County Elementary School ┆ 540.0                ┆ 5.0                       │
│ 601:103     ┆ Appling County High School       ┆ 199.0                ┆ 10.0                      │
│ 601:195     ┆ Appling County Middle School     ┆ 803.0                ┆ 4.0                       │
└─────────────┴──────────────────────────────────┴──────────────────────┴───────────────────────────┘
```

#### Statistics

| Year file | Rows | State | District | School |
|-----------|------|-------|----------|--------|
| 2004 | 2,358 | 1 | 185 | 2,171 (+1 fully-null row; also contains 136 exact-duplicate rows and 1 all-null placeholder twin — see Addendum) |
| 2005 | 2,239 | 1 | 184 | 2,054 (binary `.xls` despite `.csv` extension) |
| 2006 | 2,266 | 1 | 184 | 2,081 (binary `.xls` despite `.csv` extension) |

> Split counts corrected 2026-06-11: recomputed directly from the `SysSchoolID` `ALL` sentinels (rule in ETL consideration 8). The original table over-counted districts by one for each year (and bucketed 2004's fully-null row); the original 2005/2006 splits did not even sum to their own row totals (1+185+2,054 = 2,240 ≠ 2,239).

Describe (2006 representative):

```
shape: (9, 5)
┌────────────┬─────────────┬──────────────────────────────┬──────────────────────┬──────────────────────┐
│ statistic  ┆ SysSchoolID ┆ School Name                  ┆ Enrollment in Grades ┆ Number of Students   │
│            ┆             ┆                              ┆ Applicable...        ┆ Taking the GAA       │
╞════════════╪═════════════╪══════════════════════════════╪══════════════════════╪══════════════════════╡
│ count      ┆ 2266        ┆ 2266                         ┆ 2266.0               ┆ 2266.0               │
│ null_count ┆ 0           ┆ 0                            ┆ 0.0                  ┆ 0.0                  │
│ mean       ┆ null        ┆ null                         ┆ 1619.0               ┆ 13.9                 │
│ std        ┆ null        ┆ null                         ┆ 26012.4              ┆ 223.5                │
│ min        ┆ 601:103     ┆  Banks County Primary School ┆ 14.0                 ┆ 0.0                  │
│ 50%        ┆ null        ┆ null                         ┆ 542.0                ┆ 3.0                  │
│ max        ┆ ALL:ALL     ┆ Youth Middle School          ┆ 1222922.0            ┆ 10529.0              │
└────────────┴─────────────┴──────────────────────────────┴──────────────────────┴──────────────────────┘
```

The `max` enrollment of ~1.22M and `max` tested-count of ~10,529 come from the `ALL:ALL` state row.

#### Null Counts

- 2004: `SysSchoolID` 1, `School Name` 1, `Enrollment...` 12, `Number of Students...` 12 — a scattering of schools with null metrics, and **one entirely-null trailing row** at the end of the file (all four columns null)
- 2005, 2006: 0 nulls in any column

#### Categorical Columns

None. No demographics, no test-component breakdowns — only entity-level aggregates.

#### Suppression Markers

**None** — no suppression in Era 1 files. Small counts (including `0`) are reported as literal numbers, not masked.

---

### Era 2: 2007 (1 file)

File: `georgia_alternate_assessment_gaa_2007.xls`.

Same semantic columns as Era 1 but renamed to a shorter, lowercase schema. Otherwise identical structure and detail levels.

| Column | Description |
|--------|-------------|
| `sysschoolid` | Entity identifier — same `"<district>:<school>"` pattern as Era 1 (`"ALL:ALL"`, `"<dist>:ALL"`, `"<dist>:<school>"`) |
| `schoolname` | Entity name |
| `Enroll` | Enrollment in AYP-applicable grades — Float64 |
| `Number` | Count of students taking the GAA — Float64 |

#### Sample Data (2007)

```
shape: (5, 4)
┌─────────────┬────────────────────────────────┬─────────┬────────┐
│ sysschoolid ┆ schoolname                     ┆ Enroll  ┆ Number │
╞═════════════╪════════════════════════════════╪═════════╪════════╡
│ 733:105     ┆ Taylor County Upper Elementary ┆ 530.0   ┆ 6.0    │
│ 644:400     ┆ DeKalb School of the Arts      ┆ 113.0   ┆ 0.0    │
│ 786:103     ┆ Social Circle Middle School    ┆ 429.0   ┆ 8.0    │
│ 706:ALL     ┆ Muscogee County                ┆ 25369.0 ┆ 196.0  │
│ 726:107     ┆ Kennedy Road Middle School     ┆ 665.0   ┆ 16.0   │
└─────────────┴────────────────────────────────┴─────────┴────────┘
```

#### Statistics

| Year file | Rows | State | District | School |
|-----------|------|-------|----------|--------|
| 2007 | 2,323 | 1 | 184 | 2,138 (`.xls`, `xlrd` required) |

> District count corrected 2026-06-11 (was 185; 1+185+2,138 = 2,324 ≠ 2,323 — did not sum to the file's own row total).

Describe (2007):

```
shape: (9, 5)
┌────────────┬─────────────┬──────────────────────────────┬──────────────┬────────────┐
│ statistic  ┆ sysschoolid ┆ schoolname                   ┆ Enroll       ┆ Number     │
╞════════════╪═════════════╪══════════════════════════════╪══════════════╪════════════╡
│ count      ┆ 2323        ┆ 2323                         ┆ 2323.0       ┆ 2323.0     │
│ null_count ┆ 0           ┆ 0                            ┆ 0.0          ┆ 0.0        │
│ mean       ┆ null        ┆ null                         ┆ 1600.0       ┆ 12.7       │
│ std        ┆ null        ┆ null                         ┆ 26039.8      ┆ 206.9      │
│ min        ┆ 601:103     ┆  Banks County Primary School ┆ 2.0          ┆ 0.0        │
│ 50%        ┆ null        ┆ null                         ┆ 531.0        ┆ 3.0        │
│ max        ┆ ALL:ALL     ┆ Youth Middle School          ┆ 1238970.0    ┆ 9861.0     │
└────────────┴─────────────┴──────────────────────────────┴──────────────┴────────────┘
```

#### Null Counts

0 nulls in any column.

#### Categorical Columns

None.

#### Suppression Markers

None.

---

### Era 3: 2011–2018 (8 files)

Files: `georgia_alternate_assessment_gaa_2011.csv` through `georgia_alternate_assessment_gaa_2018.csv`.

16-column tidy format. Each row is one `(entity × demographic subgroup × test component)` combination. Entity is encoded via `SCHOOL_DISTRCT_CD` / `INSTN_NUMBER` = `"ALL"` sentinel.

| Column | Description |
|--------|-------------|
| `LONG_SCHOOL_YEAR` | School year — e.g., `"2014-15"` (one value per file) |
| `SCHOOL_DISTRCT_CD` | District code — 3-digit string (e.g., `"601"`), or 7-digit state-administered codes (e.g., `"7820108"` for State Charter Schools). Value `"ALL"` marks a state-level row. **Note the typo — `DISTRCT` not `DSTRCT`** (same typo as the ACT Scores topic) |
| `SCHOOL_DSTRCT_NM` | District name — string (`"ALL"` on the state row). **Spelled correctly as `DSTRCT`**, unlike `SCHOOL_DISTRCT_CD` |
| `INSTN_NUMBER` | School institution number — **4-char zero-padded** string in this era (e.g., `"0201"`, `"0100"`). Value `"ALL"` on district- and state-level rows |
| `INSTN_NAME` | School name — string (`"ALL"` on district- and state-level rows) |
| `SUBGROUP_NAME` | Demographic subgroup — e.g., `"All Students"`, `"White"`, `"Economically Disadvantaged"`, `"Students with Disabilities"` (see categoricals below; set expands mid-era) |
| `TEST_CMPNT_TYP_NM` | Test component — one of `"English Language Arts"`, `"Mathematics"`, `"Science"`, `"Social Studies"` |
| `NUM_TESTED_CNT` | Total students tested in the `(entity × subgroup × test)` cell — Int. **Always populated** (even for suppressed rows) |
| `LIMITED_CNT` | Count scoring **Limited** (lowest tier) — Int, **null when suppressed** |
| `PARTIAL_CNT` | Count scoring **Partial** (middle-low tier) — Int, null when suppressed |
| `ADEQUATE_CNT` | Count scoring **Adequate** (middle-high tier) — Int, null when suppressed |
| `THUROUGH_CNT` | Count scoring **Thorough** — **typo: `THUROUGH` not `THOROUGH`.** Always `0` or `null` in this era (unused column reserved for a future 4th tier that never materialized under the 3-tier GAA scoring) |
| `LIMITED_PERCENT` | Percentage scoring Limited — 0–100 scale; null when suppressed |
| `PARTIAL_PERCENT` | Percentage scoring Partial — 0–100 scale; null when suppressed |
| `ADEQUATE_PERCENT` | Percentage scoring Adequate — 0–100 scale; null when suppressed |
| `THUROUGH_PERCENT` | Percentage scoring Thorough — always `0` or `null` |

#### Sample Data (2015 representative)

```
shape: (5, 16) (columns abbreviated)
LONG_SCHOOL_YEAR | SCHOOL_DISTRCT_CD | SCHOOL_DSTRCT_NM | INSTN_NUMBER | INSTN_NAME                       | SUBGROUP_NAME                  | TEST_CMPNT_TYP_NM     | NUM_TESTED_CNT | LIMITED_CNT | PARTIAL_CNT | ADEQUATE_CNT | THUROUGH_CNT | LIMITED_PERCENT | PARTIAL_PERCENT | ADEQUATE_PERCENT | THUROUGH_PERCENT
2014-15          | 732               | Tattnall County  | 0201         | Glennville Middle School         | All Students                   | English Language Arts | 3              | null        | null        | null         | null         | null            | null            | null             | null
2014-15          | 644               | DeKalb County    | 0897         | Druid Hills Middle School        | Not Limited English Proficient | English Language Arts | 11             | 0           | 4           | 7            | 0            | 0               | 36.4            | 63.6             | null
2014-15          | 792               | Valdosta City    | 1052         | W.G. Nunn Elementary             | Economically Disadvantaged     | Social Studies        | 10             | 0           | 0           | 10           | 0            | 0               | 0               | 100              | null
2014-15          | 706               | Muscogee County  | ALL          | ALL                              | Black or African American      | Science               | 132            | 5           | 89          | 38           | 0            | 3.8             | 67.4            | 28.8             | null
2014-15          | 724               | Screven County   | 0191         | Screven County Elementary School | Not Limited English Proficient | Social Studies        | 10             | 1           | 5           | 4            | 0            | 10              | 50              | 40               | null
```

#### Statistics

Row counts per file (Era 3):

| Year file | Rows | State rows | District rows | School rows | Suppressed (null CNT) |
|-----------|------|------------|---------------|-------------|-----------------------|
| 2011 | 15,175 | 64 | 4,574 | 10,537 | 5,113 |
| 2012 | 15,700 | 65 | 4,727 | 10,908 | 5,060 |
| 2013 | 16,479 | 64 | 4,857 | 11,558 | 4,962 |
| 2014 | 16,981 | 64 | 4,827 | 12,090 | 4,844 |
| 2015 | 17,869 | 64 | 4,850 | 12,955 | 4,815 |
| 2016 | 18,477 | 68 | 5,127 | 13,282 | 4,794 |
| 2017 | 14,617 | 64 | 4,300 | 10,253 | 4,987 |
| 2018 | 15,239 | 64 | 4,502 | 10,673 | 4,989 |

> Split counts corrected 2026-06-11: recomputed directly from the `SCHOOL_DISTRCT_CD` / `INSTN_NUMBER` `ALL` sentinels (ETL consideration 8; cross-checked against the `INSTN_NAME` / `SCHOOL_DSTRCT_NM` sentinels with zero mismatches). The original 2011-2014 and 2016-2018 splits were materially off (e.g., 2011 had 4,574 district rows, not 4,159), and the state-row count is not always 64 — 2012 has 65 and 2016 has 68 (extra subgroup × subject combinations at the state level in those years). Row totals and suppressed counts were already correct.

Describe (2015 representative, numeric columns cast to Float64):

```
shape: (9, 10)
statistic  | NUM_TESTED_CNT | LIMITED_CNT | PARTIAL_CNT | ADEQUATE_CNT | THUROUGH_CNT | LIMITED_PERCENT | PARTIAL_PERCENT | ADEQUATE_PERCENT | THUROUGH_PERCENT
count      | 17869.0        | 13054.0     | 13054.0     | 13054.0      | 13054.0      | 13054.0         | 13054.0         | 13054.0          | 0.0
null_count | 0.0            | 4815.0      | 4815.0      | 4815.0       | 4815.0       | 4815.0          | 4815.0          | 4815.0           | 17869.0
mean       | 40.1           | 5.5         | 26.2        | 21.6         | 0.0          | 10.0            | 49.8            | 40.2             | null
min        | 1.0            | 0.0         | 0.0         | 0.0          | 0.0          | 0.0             | 0.0             | 0.0              | null
50%        | 12.0           | 1.0         | 8.0         | 7.0          | 0.0          | 1.6             | 50.0            | 37.3             | null
max        | 11016.0        | 1885.0      | 5650.0      | 5591.0       | 0.0          | 100.0           | 100.0           | 100.0            | null
```

#### Null Counts (2015 representative)

- All identifier and categorical columns: **0 nulls**
- `NUM_TESTED_CNT`: 0 nulls
- `LIMITED_CNT`, `PARTIAL_CNT`, `ADEQUATE_CNT`, `THUROUGH_CNT`: 4,815 nulls each (rows where individual level breakdowns are suppressed for confidentiality; `NUM_TESTED_CNT` is still populated on these rows)
- `LIMITED_PERCENT`, `PARTIAL_PERCENT`, `ADEQUATE_PERCENT`: 4,815 nulls (same rows)
- `THUROUGH_PERCENT`: **17,869 nulls (100% — column is entirely empty)**

#### Categorical Columns

2015 representative values; the `SUBGROUP_NAME` set is essentially stable across 2011–2018, expanding slightly year-over-year. Value frequencies are from 2015 (17,869 rows).

| Column | Distinct Values (with counts from 2015) |
|--------|-----------------------------------------|
| `LONG_SCHOOL_YEAR` | `"2014-15"` (17,869) — one value per file |
| `SUBGROUP_NAME` (16 values in 2015) | `"All Students"` (6,866), `"American Indian or Alaskan Native"` (4), `"Asian"` (28), `"Black or African American"` (721), `"Economically Disadvantaged"` (1,488), `"Female"` (405), `"Hispanic"` (129), `"Limited English Proficient"` (44), `"Male"` (1,182), `"Migrant"` (4), `"Non-Migrant"` (2,050), `"Not Economically Disadvantaged"` (299), `"Not Limited English Proficient"` (1,976), `"Students with Disabilities"` (2,051), `"Two or More Races"` (14), `"White"` (608). Earlier years (2011–2014) omit some of the smaller subgroups; `"Native Hawaiian or Other Pacific Islander"` appears in a few years with very small counts |
| `TEST_CMPNT_TYP_NM` | `"English Language Arts"` (4,664), `"Mathematics"` (4,604), `"Science"` (4,144), `"Social Studies"` (4,457) |

#### Suppression Markers

**No string markers** in this era (no `*`, `TFS`, `N/A`, etc. in any numeric column). Suppression is indicated by **null / empty cells** in the `*_CNT` and `*_PERCENT` columns.

---

### Era 4: 2019 (1 file)

File: `georgia_alternate_assessment_gaa_2019.csv`.

Same 16-column layout as Era 3, but the four achievement-level labels are replaced with generic `Level1`–`Level4` names, and — critically — **all four levels are populated** (GAA moved from a 3-tier to a 4-tier scoring system for 2018-19).

| Column | Description |
|--------|-------------|
| `LONG_SCHOOL_YEAR` | `"2018-19"` |
| `SCHOOL_DISTRCT_CD`, `SCHOOL_DSTRCT_NM`, `INSTN_NUMBER`, `INSTN_NAME`, `SUBGROUP_NAME`, `TEST_CMPNT_TYP_NM`, `NUM_TESTED_CNT` | Same as Era 3, **except `INSTN_NUMBER` is NOT zero-padded in this file** (e.g., `"100"`, `"101"` instead of `"0100"`, `"0101"`). This is a one-year quirk — the padding returns in Era 5 |
| `Level1_CNT` | Count scoring lowest tier (Level 1) — Int, null when suppressed. The label `"Level 1"` is GOSA's generic equivalent of the "Beginning Learner" tier used in Era 6 |
| `Level2_CNT` | Count scoring Level 2 — Int, null when suppressed |
| `Level3_CNT` | Count scoring Level 3 — Int, null when suppressed |
| `Level4_CNT` | Count scoring Level 4 (highest tier) — Int, null when suppressed |
| `Level1_PERCENT` | Percentage scoring Level 1 — 0–100 scale, null when suppressed |
| `Level2_PERCENT` | Percentage scoring Level 2 — 0–100 scale, null when suppressed |
| `Level3_PERCENT` | Percentage scoring Level 3 — 0–100 scale, null when suppressed |
| `Level4_PERCENT` | Percentage scoring Level 4 — 0–100 scale, null when suppressed |

#### Sample Data (2019)

```
shape: (5, 16) (columns abbreviated)
LONG_SCHOOL_YEAR | SCHOOL_DISTRCT_CD | SCHOOL_DSTRCT_NM | INSTN_NUMBER | INSTN_NAME            | SUBGROUP_NAME              | TEST_CMPNT_TYP_NM     | NUM_TESTED_CNT | Level1_CNT | Level2_CNT | Level3_CNT | Level4_CNT | Level1_PERCENT | Level2_PERCENT | Level3_PERCENT | Level4_PERCENT
2018-19          | 733               | Taylor County    | ALL          | ALL                   | Male                       | Mathematics           | 11             | 0          | 6          | 4          | 1          | 0              | 54.5           | 36.4           | 9.1
2018-19          | 645               | Dodge County     | ALL          | ALL                   | All Students               | Science               | 12             | 0          | 2          | 6          | 4          | 0              | 16.7           | 50             | 33.3
2018-19          | 792               | Valdosta City    | 273          | Valdosta High School  | Male                       | Mathematics           | 10             | 0          | 3          | 6          | 1          | 0              | 30             | 60             | 10
2018-19          | 706               | Muscogee County  | ALL          | ALL                   | Economically Disadvantaged | Social Studies        | 113            | 3          | 30         | 57         | 23         | 2.7            | 26.5           | 50.4           | 20.4
2018-19          | 725               | Seminole County  | ALL          | ALL                   | All Students               | English Language Arts | 9              | null       | null       | null       | null       | null           | null           | null           | null
```

#### Statistics

| Year file | Rows | State | District | School | Suppressed |
|-----------|------|-------|----------|--------|------------|
| 2019 | 15,200 | 64 | 4,454 | 10,682 | 5,224 |

```
shape: (9, 10)
statistic  | NUM_TESTED_CNT | Level1_CNT | Level2_CNT | Level3_CNT | Level4_CNT | Level1_PERCENT | Level2_PERCENT | Level3_PERCENT | Level4_PERCENT
count      | 15200.0        | 9976.0     | 9976.0     | 9976.0     | 9976.0     | 9976.0         | 9976.0         | 9976.0         | 9976.0
null_count | 0.0            | 5224.0     | 5224.0     | 5224.0     | 5224.0     | 5224.0         | 5224.0         | 5224.0         | 5224.0
mean       | 38.4           | 3.3        | 15.8       | 25.2       | 12.1       | 5.5            | 26.6           | 45.4           | 22.4
min        | 1.0            | 0.0        | 0.0        | 0.0        | 0.0        | 0.0            | 0.0            | 0.0            | 0.0
50%        | 12.0           | 1.0        | 4.0        | 7.0        | 4.0        | 2.4            | 25.0           | 45.5           | 20.0
max        | 12400.0        | 792.0      | 3938.0     | 5724.0     | 2897.0     | 81.8           | 100.0          | 100.0          | 92.9
```

#### Null Counts

- All identifier / categorical columns: 0
- `NUM_TESTED_CNT`: 0
- Each of `Level1_CNT`..`Level4_CNT` and `Level1_PERCENT`..`Level4_PERCENT`: 5,224 nulls (suppressed rows)

#### Categorical Columns

| Column | Distinct Values (with counts) |
|--------|-------------------------------|
| `LONG_SCHOOL_YEAR` | `"2018-19"` (15,200) |
| `SUBGROUP_NAME` (17 values) | Same as Era 3 plus `"Native Hawaiian or Other Pacific Islander"` (2). Top values: `"All Students"` (6,779), `"Non-Migrant"` (1,551), `"Students with Disabilities"` (1,555), `"Not Limited English Proficient"` (1,427), `"Economically Disadvantaged"` (1,148), `"Male"` (867), `"Black or African American"` (586), `"White"` (453), `"Female"` (335), `"Not Economically Disadvantaged"` (250), `"Hispanic"` (123), `"Limited English Proficient"` (62), `"Asian"` (30), `"Two or More Races"` (26), `"American Indian or Alaskan Native"` (4), `"Migrant"` (2), `"Native Hawaiian or Other Pacific Islander"` (2) |
| `TEST_CMPNT_TYP_NM` | `"English Language Arts"` (5,087), `"Mathematics"` (5,077), `"Science"` (2,516), `"Social Studies"` (2,520) |

#### Suppression Markers

No string markers. Suppression = null.

---

### Era 5: 2022–2023 (2 files)

Files: `georgia_alternate_assessment_gaa_2022.csv`, `georgia_alternate_assessment_gaa_2023.csv`.

16-column tidy format matching Era 3 but with:
- **Typo corrected**: `THUROUGH_CNT` / `THUROUGH_PERCENT` are now spelled `THOROUGH_CNT` / `THOROUGH_PERCENT`
- **`THOROUGH` is fully populated** (4-tier scoring like Era 4)
- **String suppression marker introduced**: `"TFS"` (Too Few Students) now appears in all numeric columns when a row is suppressed (was null in earlier eras)
- Expanded `SUBGROUP_NAME` set with post-pandemic additions (`"Active Duty"`, `"Foster Care"`, `"Homeless"`, `"Military Connected"`)

| Column | Description |
|--------|-------------|
| `LONG_SCHOOL_YEAR` | `"2021-22"` or `"2022-23"` |
| `SCHOOL_DISTRCT_CD` | Same as Era 3 — `"601"`-style codes, `"ALL"` sentinel, typo `DISTRCT` |
| `SCHOOL_DSTRCT_NM` | Same as Era 3 — `"ALL"` on state row |
| `INSTN_NUMBER` | **Back to 4-char zero-padded** (e.g., `"0100"`) |
| `INSTN_NAME` | Same as Era 3 |
| `SUBGROUP_NAME` | Expanded set — see categoricals |
| `TEST_CMPNT_TYP_NM` | Same four values as prior eras |
| `NUM_TESTED_CNT` | Always a real integer (no `"TFS"` in this column) |
| `LIMITED_CNT` | Count scoring Limited — Int string; `"TFS"` when suppressed |
| `PARTIAL_CNT` | Count scoring Partial — Int string; `"TFS"` when suppressed |
| `ADEQUATE_CNT` | Count scoring Adequate — Int string; `"TFS"` when suppressed |
| `THOROUGH_CNT` | Count scoring Thorough (now the actual 4th tier, not a placeholder); `"TFS"` when suppressed |
| `LIMITED_PERCENT`, `PARTIAL_PERCENT`, `ADEQUATE_PERCENT`, `THOROUGH_PERCENT` | 0–100 scale; `"TFS"` when suppressed |

#### Sample Data (2023 representative)

```
shape: (5, 16) (columns abbreviated)
LONG_SCHOOL_YEAR | SCHOOL_DISTRCT_CD | SCHOOL_DSTRCT_NM        | INSTN_NUMBER | INSTN_NAME                      | SUBGROUP_NAME              | TEST_CMPNT_TYP_NM     | NUM_TESTED_CNT | LIMITED_CNT | PARTIAL_CNT | ADEQUATE_CNT | THOROUGH_CNT | LIMITED_PERCENT | PARTIAL_PERCENT | ADEQUATE_PERCENT | THOROUGH_PERCENT
2022-23          | 735               | Terrell County          | 1051         | Cooper-Carver Elementary School | All Students               | Mathematics           | 7              | TFS         | TFS         | TFS          | TFS          | TFS             | TFS             | TFS              | TFS
2022-23          | 645               | Dodge County            | 0180         | Dodge County Middle School      | Economically Disadvantaged | English Language Arts | 21             | 2           | 0           | 8            | 11           | 9.5             | 0               | 38.1             | 52.4
2022-23          | 792               | Valdosta City           | 0117         | Pinevale Elementary School      | All Students               | Mathematics           | 14             | 0           | 0           | 1            | 13           | 0               | 0               | 7.1              | 92.9
2022-23          | 706               | Muscogee County         | 5060         | Gentian Elementary School       | Non-Migrant                | English Language Arts | 13             | 0           | 5           | 4            | 4            | 0               | 38.5            | 30.8             | 30.8
2022-23          | 726               | Griffin-Spalding County | 0201         | Cowan Road Middle School        | Economically Disadvantaged | English Language Arts | 11             | 0           | 1           | 2            | 8            | 0               | 9.1             | 18.2             | 72.7
```

#### Statistics

| Year file | Rows | State | District | School | Rows with `TFS` in `LIMITED_CNT` |
|-----------|------|-------|----------|--------|----------------------------------|
| 2022 | 15,018 | 79 | 4,392 | 10,547 | 4,649 |
| 2023 | 14,849 | 81 | 4,316 | 10,452 | 4,625 |

> 2022 split corrected 2026-06-11 (was 81 / 4,349 / 10,588; recomputed from the `ALL` sentinels per ETL consideration 8 — 2023 was already correct).

```
(2023, numeric columns cast to Float64 after stripping TFS)
shape: (9, 10)
statistic  | NUM_TESTED_CNT | LIMITED_CNT | PARTIAL_CNT | ADEQUATE_CNT | THOROUGH_CNT | LIMITED_PERCENT | PARTIAL_PERCENT | ADEQUATE_PERCENT | THOROUGH_PERCENT
count      | 14849.0        | 10224.0     | 10224.0     | 10224.0      | 10224.0      | 10224.0         | 10224.0         | 10224.0          | 10212.0
null_count | 0.0            | 4625.0      | 4625.0      | 4625.0       | 4625.0       | 4625.0          | 4625.0          | 4625.0           | 4637.0
mean       | 39.2           | 1.8         | 15.6        | 25.1         | 12.5         | 2.7             | 26.8            | 45.9             | 24.1
min        | 1.0            | 0.0         | 0.0         | 0.0          | 0.0          | 0.0             | 0.0             | 0.0              | 0.0
50%        | 12.0           | 0.0         | 4.0         | 7.0          | 4.0          | 0.0             | 25.0            | 45.7             | 20.0
max        | 12765.0        | 430.0       | 4035.0      | 5912.0       | 3349.0       | 50.0            | 100.0           | 100.0            | 100.0
```

#### Null Counts

- **Every column has 0 literal nulls** in the CSV (suppressed values are filled with the `"TFS"` string instead of left blank)

#### Categorical Columns

| Column | Distinct Values (with counts from 2023, 14,849 rows) |
|--------|------------------------------------------------------|
| `LONG_SCHOOL_YEAR` | `"2022-23"` (14,849) — one value per file |
| `SUBGROUP_NAME` (21 values) | `"Active Duty"` (12), `"All Students"` (6,210), `"American Indian or Alaskan Native"` (3), `"Asian"` (30), `"Black or African American"` (591), `"Economically Disadvantaged"` (1,156), `"Female"` (321), `"Foster Care"` (8), `"Hispanic"` (137), `"Homeless"` (77), `"Limited English Proficient"` (52), `"Male"` (929), `"Migrant"` (3), `"Military Connected"` (14), `"Native Hawaiian or Other Pacific Islander"` (3), `"Non-Migrant"` (1,583), `"Not Economically Disadvantaged"` (255), `"Not Limited English Proficient"` (1,468), `"Students with Disabilities"` (1,585), `"Two or More Races"` (40), `"White"` (372) |
| `TEST_CMPNT_TYP_NM` | `"English Language Arts"` (5,279), `"Mathematics"` (5,254), `"Science"` (2,598), `"Social Studies"` (1,718) |

Note: `"Students without Disabilities"` is NOT present in 2022/2023 (only in 2024).

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| `LIMITED_CNT`, `PARTIAL_CNT`, `ADEQUATE_CNT`, `THOROUGH_CNT` | `"TFS"` (4,625 rows in 2023) |
| `LIMITED_PERCENT`, `PARTIAL_PERCENT`, `ADEQUATE_PERCENT`, `THOROUGH_PERCENT` | `"TFS"` (4,625–4,637 rows in 2023) |
| `NUM_TESTED_CNT` | None — always numeric |

---

### Era 6: 2024 (1 file)

File: `georgia_alternate_assessment_gaa_2024.csv`.

18-column schema adds two new constant-valued header columns and renames the achievement level columns to match Georgia Milestones naming (`BEGIN`/`DEVELOPING`/`PROFICIENT`/`DISTINGUISHED`). Percent columns are now `*_PCT` instead of `*_PERCENT`.

| Column | Description |
|--------|-------------|
| `#ASSMT_CD` | Assessment code — always `"GAA"` (63,689 rows). Leading `#` makes this column name awkward for downstream tools — strip/rename during transform |
| `LONG_SCHOOL_YEAR` | `"2023-24"` (one value) |
| `SCHOOL_DISTRCT_CD` | Same format as Era 5 — `"601"`-style, `"ALL"` sentinel |
| `SCHOOL_DSTRCT_NM` | Same as Era 5 |
| `INSTN_NUMBER` | 4-char zero-padded (back to Era 5's format) |
| `INSTN_NAME` | Same as Era 5 |
| `ACDMC_LVL` | Academic level — always `"ALL GRADES"` (constant; not useful for partitioning). Introduced so GOSA can use a unified schema across assessments with grade-level breakdowns |
| `SUBGROUP_NAME` | Expanded again — 22 values, adds `"Students without Disabilities"` |
| `TEST_CMPNT_TYP_NM` | Same four values |
| `NUM_TESTED_CNT` | Int string; `"TFS"` when suppressed. **Now suppressed on most rows** — 53,791 `"TFS"` out of 63,689 (suppression policy tightened in 2024) |
| `BEGIN_CNT` | Count scoring **Beginning Learner** (lowest tier — replaces `LIMITED`). Int string; `"TFS"` when suppressed (63,437 of 63,689 rows) |
| `DEVELOPING_CNT` | Count scoring **Developing Learner** — `"TFS"` when suppressed (61,629 rows) |
| `PROFICIENT_CNT` | Count scoring **Proficient Learner** — `"TFS"` when suppressed (60,263 rows) |
| `DISTINGUISHED_CNT` | Count scoring **Distinguished Learner** (highest tier) — `"TFS"` when suppressed (62,140 rows) |
| `BEGIN_PCT` | Percentage scoring Beginning — 0–100 scale. **Never suppressed** (percentages are released even when counts are `"TFS"` — unusual inversion!) |
| `DEVELOPING_PCT` | Percentage scoring Developing — 0–100 scale; never `"TFS"` |
| `PROFICIENT_PCT` | Percentage scoring Proficient — 0–100 scale; never `"TFS"` |
| `DISTINGUISHED_PCT` | Percentage scoring Distinguished — 0–100 scale; sometimes `"TFS"` (430 rows), sometimes blank |

**Key 2024 quirk**: the row count jumps from ~15K (2022/2023) to ~64K because suppressed rows are no longer omitted — GOSA now emits a row for every `(entity × subgroup × test)` combination whether or not the cell passes the suppression threshold, and marks the counts as `"TFS"` when suppressed. Percentages continue to be published even for suppressed rows (`BEGIN_PCT`, `DEVELOPING_PCT`, `PROFICIENT_PCT` have no `"TFS"` at all; only `DISTINGUISHED_PCT` has a handful).

#### Sample Data (2024)

```
shape: (5, 18) (columns abbreviated)
#ASSMT_CD | LONG_SCHOOL_YEAR | SCHOOL_DISTRCT_CD | SCHOOL_DSTRCT_NM   | INSTN_NUMBER | INSTN_NAME                     | ACDMC_LVL  | SUBGROUP_NAME                  | TEST_CMPNT_TYP_NM | NUM_TESTED_CNT | BEGIN_CNT | DEVELOPING_CNT | PROFICIENT_CNT | DISTINGUISHED_CNT | BEGIN_PCT | DEVELOPING_PCT | PROFICIENT_PCT | DISTINGUISHED_PCT
GAA       | 2023-24          | 732               | Tattnall County    | 0201         | South Tattnall Middle School   | ALL GRADES | Two or More Races              | Mathematics       | TFS            | TFS       | TFS            | TFS            | TFS               | 0         | 0              | 100            | 0
GAA       | 2023-24          | 645               | Dodge County       | 0293         | Dodge County Elementary School | ALL GRADES | Non-Migrant                    | Science           | TFS            | TFS       | TFS            | TFS            | TFS               | 0         | 33.3           | 66.7           | 0
GAA       | 2023-24          | 786               | Social Circle City | 0300         | Social Circle High School      | ALL GRADES | Not Limited English Proficient | Science           | TFS            | TFS       | TFS            | TFS            | TFS               | 0         | 0              | 50             | 50
GAA       | 2023-24          | 706               | Muscogee County    | 1064         | Kendrick High School           | ALL GRADES | White                          | Social Studies    | TFS            | TFS       | TFS            | TFS            | TFS               | 0         | 0              | 100            | 0
GAA       | 2023-24          | 723               | Schley County      | 0101         | Schley Middle High School      | ALL GRADES | White                          | Science           | TFS            | TFS       | TFS            | TFS            | TFS               | 0         | 0              | 50             | 50
```

#### Statistics

| Year file | Rows | State | District | School | `TFS` in `NUM_TESTED_CNT` |
|-----------|------|-------|----------|--------|---------------------------|
| 2024 | 63,689 | 86 | 9,212 | 54,391 | 53,791 (84%) |

```
(2024, numeric columns cast to Float64 after stripping TFS)
shape: (9, 10)
statistic  | NUM_TESTED_CNT | BEGIN_CNT | DEVELOPING_CNT | PROFICIENT_CNT | DISTINGUISHED_CNT | BEGIN_PCT | DEVELOPING_PCT | PROFICIENT_PCT | DISTINGUISHED_PCT
count      | 9898.0         | 252.0     | 2060.0         | 3426.0         | 1549.0            | 63689.0   | 63689.0        | 63689.0        | 63259.0
null_count | 53791.0        | 63437.0   | 61629.0        | 60263.0        | 62140.0           | 0.0       | 0.0            | 0.0            | 430.0
mean       | 55.9           | 45.8      | 65.7           | 63.4           | 57.0              | 3.6       | 29.9           | 45.1           | 20.0
min        | 10.0           | 10.0      | 10.0           | 10.0           | 10.0              | 0.0       | 0.0            | 0.0            | 0.0
50%        | 15.0           | 18.0      | 17.0           | 15.0           | 16.0              | 0.0       | 25.0           | 50.0           | 0.0
max        | 12589.0        | 426.0     | 4131.0         | 5927.0         | 2981.0            | 100.0     | 100.0          | 100.0          | 100.0
```

Note the `min` of 10 on every `*_CNT` column — consistent with a suppression threshold of "fewer than 10".

#### Null Counts

- **All columns have 0 literal nulls in the CSV** (suppressed counts = `"TFS"` string; suppressed `DISTINGUISHED_PCT` is an empty string that polars treats as null → 430 "nulls" shown in `describe`)

#### Categorical Columns

| Column | Distinct Values (with counts) |
|--------|-------------------------------|
| `#ASSMT_CD` | `"GAA"` (63,689) — constant |
| `LONG_SCHOOL_YEAR` | `"2023-24"` (63,689) |
| `ACDMC_LVL` | `"ALL GRADES"` (63,689) — constant |
| `SUBGROUP_NAME` (22 values) | `"Active Duty"` (430), `"All Students"` (6,309), `"American Indian or Alaskan Native"` (121), `"Asian"` (1,037), `"Black or African American"` (4,796), `"Economically Disadvantaged"` (6,138), `"Female"` (4,857), `"Foster Care"` (670), `"Hispanic"` (2,985), `"Homeless"` (1,135), `"Limited English Proficient"` (1,593), `"Male"` (5,951), `"Migrant"` (113), `"Military Connected"` (457), `"Native Hawaiian or Other Pacific Islander"` (64), `"Non-Migrant"` (6,308), `"Not Economically Disadvantaged"` (2,399), `"Not Limited English Proficient"` (6,283), `"Students with Disabilities"` (6,309), `"Students without Disabilities"` (6), `"Two or More Races"` (1,428), `"White"` (4,300) |
| `TEST_CMPNT_TYP_NM` | `"English Language Arts"` (19,650), `"Mathematics"` (19,634), `"Science"` (15,107), `"Social Studies"` (9,298) |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| `NUM_TESTED_CNT` | `"TFS"` (53,791) |
| `BEGIN_CNT` | `"TFS"` (63,437) |
| `DEVELOPING_CNT` | `"TFS"` (61,629) |
| `PROFICIENT_CNT` | `"TFS"` (60,263) |
| `DISTINGUISHED_CNT` | `"TFS"` (62,140) |
| `BEGIN_PCT`, `DEVELOPING_PCT`, `PROFICIENT_PCT` | None — always numeric |
| `DISTINGUISHED_PCT` | `"TFS"` (430 rows, plus 430 empty/null) |

---

## ETL Considerations

1. **File-extension mismatch for 2005 and 2006.** `.csv` files are actually Excel binary (`.xls`) OLE2 documents (confirmed via `file` command showing `Composite Document File V2 Document, ... Name of Creating Application: Microsoft Excel`). Reading with `pl.read_csv` produces garbage and UTF-8 errors. Both must be read via `xlrd` (polars' `read_excel` with calamine/openpyxl does **not** support `.xls`; only `xlrd` does). Read only `Sheet1` — `Sheet2` and `Sheet3` are empty. Suggested reader:
    ```python
    import xlrd
    wb = xlrd.open_workbook(path)
    s = wb.sheet_by_name("Sheet1")
    header = [s.cell_value(0, c) for c in range(s.ncols)]
    rows = [[s.cell_value(r, c) for c in range(s.ncols)] for r in range(1, s.nrows)]
    df = pl.DataFrame(rows, schema=header, orient="row")
    ```

2. **Two semantically different datasets share the topic.** Eras 1–2 (2004–2007) are a **participation-only summary** (no demographics, no test components); Eras 3–6 (2011–2024) are a **tidy achievement-level breakdown**. These cannot share a single gold fact table — the earlier era can only populate an enrollment + tested-count row at each entity with `demographic = "All Students"` and no `test_component`, while the later era has full `(subgroup × test × achievement level)` detail. Options:
   - Emit Eras 1–2 only as two metric columns (`enrollment_ayp_grades`, `num_tested`) on a pared-down row with `test_component = null`/sentinel, and leave the achievement-level columns null; **or**
   - Drop Eras 1–2 from gold entirely and document the gap. Given the historical value and small row count (~9K rows), keeping them is feasible.
   - Recommended: keep them but clearly annotate — the `num_tested` metric is still a valid count in either era.

3. **`THUROUGH` typo in Era 3.** `THUROUGH_CNT` / `THUROUGH_PERCENT` (2011–2018) contains **only zeros and nulls** — the column was reserved for a 4th tier that did not exist until Era 4 adopted 4-tier scoring. The transform should **drop `THUROUGH_CNT` and `THUROUGH_PERCENT` from gold for Era 3** (they contribute no information) rather than emit an always-zero metric. Separately, do not confuse `THUROUGH` (Era 3 misspelling) with `THOROUGH` (Era 5 correct spelling) when mapping.

4. **Achievement-level naming changes across Eras 3→4→5→6.** A common gold naming must be chosen. Suggested mapping of bronze → gold achievement levels:

    | Era 3 (3 active tiers) | Era 4 | Era 5 | Era 6 | Gold name (recommended) |
    |------------------------|-------|-------|-------|--------------------------|
    | LIMITED | Level1 | LIMITED | BEGIN | `level_1_beginning` |
    | PARTIAL | Level2 | PARTIAL | DEVELOPING | `level_2_developing` |
    | ADEQUATE | Level3 | ADEQUATE | PROFICIENT | `level_3_proficient` |
    | (THUROUGH = always 0, drop) | Level4 | THOROUGH | DISTINGUISHED | `level_4_distinguished` |

    Before Era 4 (2019), Level 4 did not exist for GAA — the metric should be emitted as null for 2011–2018 rows, not `0`. This avoids misleading averages.

5. **Suppression markers differ across eras.** Handling:
   - Eras 3 & 4 (2011–2019): suppression = null cell → `pl.col(c).cast(pl.Float64, strict=False)` handles this automatically
   - Eras 5 & 6 (2022–2024): suppression = `"TFS"` string → must replace `"TFS"` with null before casting (e.g., `pl.col(c).replace({"TFS": None}).cast(pl.Float64)`)
   - In 2024, `NUM_TESTED_CNT` is also suppressed (`"TFS"`) for ~84% of rows — a significant change from prior years where `NUM_TESTED_CNT` was always populated. Suppressed `NUM_TESTED_CNT` rows still carry percentages — decide whether to keep them as "percent-only" rows or drop them
   - Eras 1 & 2 (2004–2007) have no suppression

6. **Column-name typo: `SCHOOL_DISTRCT_CD` vs `SCHOOL_DSTRCT_NM`.** The code column is misspelled (`DISTRCT`) while the name column is spelled correctly (`DSTRCT`). Both appear in every Era 3–6 file. Rename both to `district_code` / `district_name` in gold to avoid propagating either spelling.

7. **`INSTN_NUMBER` padding inconsistency in Era 4 (2019).** 2019 is the only file that does **not** zero-pad `INSTN_NUMBER` to 4 characters (values like `"100"`, `"101"` instead of `"0100"`, `"0101"`). Must left-pad with `str.zfill(4)` during transform for 2019 to preserve joinability with the schools dimension (which uses 4-char padded codes). **Note**: `SCHOOL_DISTRCT_CD` is consistent 3-char (or 7-char for state charter agencies) across all Era 3–6 files and does not need padding normalization.

8. **`INSTN_NUMBER` / `SCHOOL_DISTRCT_CD` = `"ALL"` sentinel.** Both ID columns use the literal string `"ALL"` to indicate aggregation level. The transform must:
    - Map `(SCHOOL_DISTRCT_CD = "ALL", INSTN_NUMBER = "ALL")` → state-level row (`detail_level = "state"`, geography keys set to state FIPS)
    - Map `(SCHOOL_DISTRCT_CD = value, INSTN_NUMBER = "ALL")` → district-level row (school key = null)
    - Map `(SCHOOL_DISTRCT_CD = value, INSTN_NUMBER = value)` → school-level row
    - Emit three separate fact files per gold pattern: `state.parquet`, `district.parquet`, `school.parquet` (plus `year=YYYY` partitioning)
    - The `SysSchoolID` in Eras 1 & 2 follows the **same logical pattern** but uses `":"` as the delimiter (e.g., `"601:ALL"` for district, `"ALL:ALL"` for state) — split on `":"` and apply the same rule

9. **State-administered district codes.** Districts such as State Charter Schools use 7-digit district codes like `"7820108"` (observed in the EOC sibling topic; likely appears here too). These should pass through as-is — do NOT pad or truncate — and the districts dimension has to accommodate both 3-digit and 7-digit codes.

10. **One fully-null trailing row in 2004.** The 2004 CSV has a single row where all four columns are null (end-of-file artifact). Filter rows where `SysSchoolID.is_null()` before processing.

11. **State-level `max` in `NUM_TESTED_CNT` in Era 3.** Values over ~10,000 come from state-level `ALL` rows (e.g., 11,016 total students tested in ELA statewide). These are legitimate and reflect the aggregation level. The summary row for the `"All Students"` × `"ALL:ALL"` combination should be the largest.

12. **`SUBGROUP_NAME` set expansion over time.** The demographic categories expand substantially between eras:
    - Era 3 (2011–2018): 16 subgroups (standard race/ethnicity, EL status, disability, migrant, ED)
    - Era 4 (2019): adds `"Native Hawaiian or Other Pacific Islander"` (17 total)
    - Eras 5 & 6 (2022–2024): adds `"Active Duty"`, `"Foster Care"`, `"Homeless"`, `"Military Connected"` (21–22 total; 22 includes `"Students without Disabilities"` only in 2024). All new subgroups should map through the standard `demographics` dimension — see shared demographic mapping utilities in `src/etl/education/`.

13. **`#ASSMT_CD` column name.** The leading `#` in 2024 will break several libraries (treated as comment character by some CSV readers, sort keys weirdly). When reading with polars, the default behavior preserves the `#` (polars does not treat `#` as a comment by default). Strip or rename to `assessment_code` in the transform. Value is constant `"GAA"` → candidate for `not_in_gold`.

14. **`ACDMC_LVL = "ALL GRADES"` constant in 2024.** Not useful for partitioning in this topic (the GAA has no grade-level breakdown in the file). Drop from gold.

15. **Percentage scaling.** All `*_PERCENT` and `*_PCT` columns are 0–100 scaled — must divide by 100 at gold per `data-cleaning-standards`. Suppressed `"TFS"` → null before scaling.

16. **No filename-to-data-year offset** — the filename year is the ending calendar year of the school year (matches `LONG_SCHOOL_YEAR` in Eras 3–6). Derive `year` from the filename for Eras 1 & 2 (no year column available).

17. **Dataset gaps.** 2008–2010 and 2020–2021 files are absent. 2020 and 2021 are COVID test-suspension years; 2008–2010 are GOSA historical archive gaps. Document both in the gold contract/README (there is no `_metadata.json` — the ODCS contract is the metadata) — the fact table will simply have no rows for those years.

## Gold Schema Classification

| Bronze Column (era) | Gold Role | Gold Name | Notes |
|---------------------|-----------|-----------|-------|
| `SysSchoolID` (Eras 1–2) | **derived** | `district_code`, `school_code`, `detail_level` | Split on `:`; `"ALL:ALL"` → state, `"<d>:ALL"` → district, `"<d>:<s>"` → school |
| `School Name` / `schoolname` (Eras 1–2) | dimension_attribute | — | District name for `:ALL` rows, school name otherwise — belongs in districts/schools dimensions |
| `Enrollment in Grades Applicable to AYP Grades 1 through 8 and 11` / `Enroll` (Eras 1–2) | fact_metric | `enrollment_ayp_grades` | Int (Eras 1–2 only; null for Eras 3–6). Used only for participation-rate calc |
| `Number of Students Taking the GAA` / `Number` (Eras 1–2) | fact_metric | `num_tested` | Int (carries over into Eras 3–6 as a direct mapping from `NUM_TESTED_CNT`) |
| `LONG_SCHOOL_YEAR` (Eras 3–6) | not_in_gold | — | Use `year` derived from filename; redundant |
| `SCHOOL_DISTRCT_CD` (Eras 3–6) | fact_key | `district_code` | String, `"ALL"` → state FIPS. FK to districts dimension (note DISTRCT typo in source) |
| `SCHOOL_DSTRCT_NM` (Eras 3–6) | dimension_attribute | — | `district_name` in districts dimension |
| `INSTN_NUMBER` (Eras 3–6) | fact_key | `school_code` | String, zero-pad to 4 chars (2019 requires fixing). `"ALL"` → null (district/state row). FK to schools dimension |
| `INSTN_NAME` (Eras 3–6) | dimension_attribute | — | `school_name` in schools dimension |
| `SUBGROUP_NAME` (Eras 3–6) | fact_key | `demographic` | Standard demographic dimension FK. 22+ distinct values post-2022 |
| `TEST_CMPNT_TYP_NM` (Eras 3–6) | fact_categorical | `test_component` | `english_language_arts`, `mathematics`, `science`, `social_studies` (snake_case). Null for Eras 1–2 |
| `NUM_TESTED_CNT` (Eras 3–6) | fact_metric | `num_tested` | Int; shares gold name with Eras 1–2 `Number`. In 2024, 84% of rows are `"TFS"` → null |
| `LIMITED_CNT` (Era 3) / `Level1_CNT` (Era 4) / `LIMITED_CNT` (Era 5) / `BEGIN_CNT` (Era 6) | fact_metric | `level_1_beginning_count` | Int; union across eras with common gold name |
| `PARTIAL_CNT` / `Level2_CNT` / `PARTIAL_CNT` / `DEVELOPING_CNT` | fact_metric | `level_2_developing_count` | Int |
| `ADEQUATE_CNT` / `Level3_CNT` / `ADEQUATE_CNT` / `PROFICIENT_CNT` | fact_metric | `level_3_proficient_count` | Int |
| `THUROUGH_CNT` (Era 3) | not_in_gold | — | Always 0 or null — do not emit an always-zero metric |
| `Level4_CNT` (Era 4) / `THOROUGH_CNT` (Era 5) / `DISTINGUISHED_CNT` (Era 6) | fact_metric | `level_4_distinguished_count` | Int; null for Era 3 rows |
| `LIMITED_PERCENT` / `Level1_PERCENT` / `LIMITED_PERCENT` / `BEGIN_PCT` | fact_metric | `level_1_beginning_pct` | Float, 0–1 scale after /100 |
| `PARTIAL_PERCENT` / `Level2_PERCENT` / `PARTIAL_PERCENT` / `DEVELOPING_PCT` | fact_metric | `level_2_developing_pct` | Float, 0–1 scale |
| `ADEQUATE_PERCENT` / `Level3_PERCENT` / `ADEQUATE_PERCENT` / `PROFICIENT_PCT` | fact_metric | `level_3_proficient_pct` | Float, 0–1 scale |
| `THUROUGH_PERCENT` (Era 3) | not_in_gold | — | Always null — do not emit |
| `Level4_PERCENT` (Era 4) / `THOROUGH_PERCENT` (Era 5) / `DISTINGUISHED_PCT` (Era 6) | fact_metric | `level_4_distinguished_pct` | Float, 0–1 scale; null for Era 3 |
| `#ASSMT_CD` (Era 6) | not_in_gold | — | Constant `"GAA"` — topic identity, not data |
| `ACDMC_LVL` (Era 6) | not_in_gold | — | Constant `"ALL GRADES"` — no info |

> Note (2026-06-11): the gold names in this table were a pre-build recommendation. The shipped gold schema follows the data-cleaning-standards §16 canonical vocabulary instead: the test-component column is `subject` (academic content), and the achievement-level metrics are `num_beginning_learner` / `num_developing_learner` / `num_proficient_learner` / `num_distinguished_learner` and `pct_<level>_learner`, plus derived `pct_developing_learner_or_above` / `pct_proficient_learner_or_above`. See `contracts/education/georgia_alternate_assessment_gaa.odcs.yaml`.

## Addendum — transform-time findings (2026-06-11)

Verified directly against the bronze files while authoring `transform.py`; these facts were missing from (or contradicted by) the original report:

1. **2004 duplicate rows.** Besides the one fully-null trailing row already documented, the 2004 CSV republishes **137 `SysSchoolID`s with two rows each** (districts 644–647): **136 are exact duplicates** (byte-identical rows — lossless to drop one copy), and **one is an all-null placeholder twin** — `647:3058` appears once as "Northside Elementary" with both metrics null and once as "Northside Elementary School" with `Enrollment = 406`, `Number tested = 10`. The 2005–2007 files have no duplicate ids.
2. **`num_tested` can exceed `enrollment_ayp_grades`.** `644:3058` (DeKalb) reports 51 tested vs 44 enrolled in 2004 and 52 vs 50 in 2005. Conceivable, not impossible: the enrollment column counts only AYP grades (1–8, 11) while the GAA is also administered in other grades — preserved in gold, so do NOT author a `num_tested <= enrollment` invariant.
3. **Counts reconcile exactly to `NUM_TESTED_CNT` in 2011–2019 only.** Where all active-tier counts are reported, their sum equals `NUM_TESTED_CNT` with zero exceptions in 2011–2019. From 2022 on the sum can undershoot (max observed shortfall 401 in 2023; some tested students receive no band), though it never exceeds `NUM_TESTED_CNT` in any year.
4. **`Homeless` percentage-sum anomaly (2022–2024).** The `Homeless` subgroup's four level percentages sum to ~50 instead of ~100 — a source denominator inconsistency vs the published counts. In 2022–2023 it affects a small set of district/state rows (50 rows in 2022, 77 in 2023); in **2024 it is systematic** — all 1,135 Homeless rows at every detail level (4 state, 300 district, 831 school) publish shares summing to ~49.9–50.1. Partition-sums-to-100 holds only for 2011–2019 (observed range 99.9–100.2); from 2022 only the upper bound (≤ 100.2) holds.
5. **Per-tier count/percent co-nullity holds 2011–2019 with zero row-level mismatches.** Era 5 has 11 (2022) / 12 (2023) rows where `THOROUGH_PERCENT` is suppressed while `THOROUGH_CNT` is not, and 2024 breaks co-nullity wholesale (percentages published while counts are TFS) — so the invariant is only assertable for 2011–2019.
6. **State-row counts vary.** 64 state rows is the norm (16 subgroups × 4 subjects), but 2012 has 65 and 2016 has 68 (extra subgroup × subject combinations published at the state level); 2022 has 79, 2023 has 81, 2024 has 86. The original per-level split tables were wrong for 2011–2014, 2016–2018, and 2022 and have been corrected in place (see the per-era notes above).
