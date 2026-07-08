# attendance_dashboard - Bronze Data Structure

## Overview

- Topic: attendance_dashboard
- Source: georgiainsights
- Files: 8 files spanning 2018-2025 (one .xlsx per school year)
- Unreadable files: none
- Year representation: `School \nYear` column in every sheet (Int64, single value per file, e.g., 2025). Filename also embeds the same year in `Attendance Dashboard Data - YYYY.xlsx`. The integer is the spring (ending) year of the school year (e.g., 2025 = SY 2024-2025).
- Filename-to-data year offset: same (filename year = data year)
- Detail levels: state (System ID = "All", School ID = "All"), district (System ID = code, School ID = "All"), school (System ID = code, School ID = code)
- Percentage scale: All three rate metrics (Chronically Absent, Average Daily Absenteeism Rate, Average Daily Attendance Rate) are stored on a 0-1 scale (verified min/max across every year and every sheet — max observed value is 1.0).
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: Georgia Insights (GaDOE) public data downloads — exact page URL not recorded at acquisition time
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| Attendance Dashboard Data - 2018.xlsx | 35bbe5a9484e4a526b76d7e2313693d01dd370fbdf7307fc62cff12e317f71f3 |
| Attendance Dashboard Data - 2019.xlsx | 06778ee4225dec8016e44fd2832e6c054189b48508f1d8ef222f279a8edb7812 |
| Attendance Dashboard Data - 2020.xlsx | 21bd27779bdf65ab518efccea33e6c6726f88876bc5aabf7a355add4a49bd446 |
| Attendance Dashboard Data - 2021.xlsx | 5341edb7c63dcfd27a6c7761a33b06e76f52e50f2cf93f65fb8e9d280ef5f4df |
| Attendance Dashboard Data - 2022.xlsx | 64acbb6736fad5295e9334656bb4f822d0ee707a36461071a2ba008ad56d74b3 |
| Attendance Dashboard Data - 2023.xlsx | d51bb0a1c8a52cc2be59d139197cfa39919542c0d75f7c4c963d2fb4476e5cbf |
| Attendance Dashboard Data - 2024.xlsx | 72280d2f9e67615dcb5b24774fde6adb9b434fddcf21b4fef49e5223f806ebbb |
| Attendance Dashboard Data - 2025.xlsx | 137ef04609312c3cde88f8e9537d0659f38f5218868143252d89f14bb197b6f8 |

## Excel Sheet Structure

| File(s) | Sheets | Notes |
|---------|--------|-------|
| 2018-2025 (all 8 files) | `Read Me` (Metadata), `All Students` (Data), `Grade Level` (Data), `Subgroups` (Data) | Same 4-sheet layout in every year. The `Read Me` sheet defines the three absenteeism metrics and lists the only suppression marker (`TFS - Too Few Students`). Data lives in three parallel sheets that must be concatenated during transform: `All Students` (no demographic breakdown), `Grade Level` (broken out by grade), `Subgroups` (broken out by gender, race/ethnicity, special populations). Each sheet has identical column headers; the `Group` and `Subgroup` columns disambiguate them after concatenation. |

The transform must read all three data sheets and union them — they share the same 11-column schema but cover different demographic dimensions of the same population. The `Read Me` sheet is documentation only and must not be ingested.

## Summary

GaDOE Attendance Dashboard reports three closely-related absenteeism metrics for every Georgia public school, district, and the state, broken down by grade level and by demographic subgroup:

- **Chronically Absent (10% or more)** — share of students absent ≥10% of their enrolled days (the federal chronic-absenteeism definition).
- **Average Daily Attendance Rate** — total present-days / total enrolled-days.
- **Average Daily Absenteeism Rate** — total absent-days / total enrolled-days. Mathematically the inverse of Average Daily Attendance Rate.

The dashboard also publishes the underlying `Total Students` enrollment used as the denominator. All three rates are emitted on a 0-1 scale (e.g., 0.935 = 93.5%).

## Eras

### Era 1: 2018-2025 (single era)

Every file in the topic uses the exact same 11 columns in the exact same order across all three data sheets:

| Column | Description |
|--------|-------------|
| `School \nYear` | Int64. Single calendar year matching the filename (e.g., 2025). Represents the spring year of the school year. |
| `System \nID` | String. GOSA district code — 3-digit for traditional school districts (e.g., `"601"`) or 7-digit for state-charter / state-specialty systems (e.g., `"7820618"`). Literal string `"All"` for state-aggregate rows. Only `"All"` and digit-only strings appear. |
| `System Name` | String. District name in title case (e.g., `"Appling County"`), or `"State of Georgia"` for the state row. |
| `School \nID` | String. GOSA school code — 3- or 4-digit (e.g., `"618"` or `"2055"`), or the literal string `"All"` for state- and district-aggregate rows. Only `"All"` and digit-only strings appear. |
| `School Name` | String. School name in title case (e.g., `"Altamaha Elementary School"`), or `"All Schools"` for state- and district-aggregate rows. |
| `Group` | String. Demographic dimension being broken out: `"All"` (in `All Students` sheet), `"Grade Level"` (in `Grade Level` sheet), or one of seven category names in `Subgroups` (`Race/Ethnicity`, `Gender`, `Students with Disabilities`, `Socioeconomic Status`, `English Learners`, `Homeless`, `Migrant`). |
| `Subgroup` | String. Specific value within `Group` (e.g., `"All"`, `"Kindergarten"`, `"Grade 9"`, `"Black"`, `"Female"`, `"Student with Disabilities"`). 28 distinct values across all sheets and years. |
| `Total \nStudents` | Int64. Enrollment denominator. Never null/suppressed in any row. |
| `Chronically Absent \n(10% or more)` | Float64 in some file/sheet combinations, String (Utf8) in others depending on whether `TFS` appears (see dtype-drift table in ETL Considerations). Values are on a 0-1 scale. |
| `Average Daily Absenteeism Rate` | Same dtype-by-sheet pattern as Chronically Absent. 0-1 scale. |
| `Average Daily Attendance Rate` | Same dtype-by-sheet pattern. 0-1 scale. Equal to `1 - Average Daily Absenteeism Rate` row-by-row (within ≤ 0.001 rounding tolerance). |

#### Sample Data (2025 file)

```text
=== All Students sheet (sample) ===
School Year=2025  System ID=721  System Name=Richmond County    School ID=399   School Name=Richmond Hill Elementary School  Group=All  Subgroup=All  Total Students=913    Chronically Absent=0.284  ADAR=0.081  ADAttR=0.919
School Year=2025  System ID=644  System Name=DeKalb County      School ID=2055  School Name=Druid Hills High School          Group=All  Subgroup=All  Total Students=1568   Chronically Absent=0.393  ADAR=0.108  ADAttR=0.892
School Year=2025  System ID=755  System Name=Whitfield County   School ID=All   School Name=All Schools                      Group=All  Subgroup=All  Total Students=12108  Chronically Absent=0.158  ADAR=0.057  ADAttR=0.943

=== Grade Level sheet (sample) ===
School Year=2025  System ID=625  System Name=Savannah-Chatham County  School ID=101   School Name=Johnson High School         Group=Grade Level  Subgroup=Grade 12      Total Students=153  Chronically Absent=0.333  ADAR=0.101  ADAttR=0.899
School Year=2025  System ID=755  System Name=Whitfield County         School ID=All   School Name=All Schools                 Group=Grade Level  Subgroup=Grade 3       Total Students=960  Chronically Absent=0.107  ADAR=0.048  ADAttR=0.952

=== Subgroups sheet (sample) ===
School Year=2025  System ID=721  System Name=Richmond County    School ID=5566  School Name=Laney High School                 Group=Race/Ethnicity  Subgroup=Black                  Total Students=774  Chronically Absent=0.602  ADAR=0.165  ADAttR=0.835
School Year=2025  System ID=755  System Name=Whitfield County   School ID=206   School Name=Beaverdale Elementary School      Group=Race/Ethnicity  Subgroup=Black                  Total Students=5    Chronically Absent=TFS    ADAR=TFS    ADAttR=TFS
School Year=2025  System ID=781  System Name=Marietta City      School ID=101   School Name=Marietta High School              Group=Gender          Subgroup=Female                 Total Students=1330 Chronically Absent=0.379  ADAR=0.110  ADAttR=0.890
```

#### Statistics (2025 file, by sheet)

| Sheet | Rows | State rows | District rows | School rows | Rows with TFS / null (any of 3 metrics) | Mean Chronically Absent | Mean ADAR | Mean ADAttR |
|-------|-----:|-----------:|--------------:|------------:|--------------------------------------:|------------------------:|----------:|------------:|
| All Students | 2,536 | 1 | 234 | 2,301 | 4 | 0.199 | 0.065 | 0.935 |
| Grade Level | 14,143 | 13 | 2,755 | 11,375 | 309 | 0.193 | 0.063 | 0.937 |
| Subgroups | 32,322 | 14 | 3,036 | 29,272 | 6,437 | (n/a — column read as string; recompute after TFS→null) | (n/a) | (n/a) |

(Mean values are computed across all non-suppressed rows including state, district, and school rows. Min/max for every year and sheet stay within the [0, 1] interval, confirming the 0-1 scale.)

#### Row Counts Per File and Sheet

| Year | All Students | Grade Level | Subgroups | Total |
|-----:|-------------:|------------:|----------:|------:|
| 2018 | 2,492 | 13,827 | 31,551 | 47,870 |
| 2019 | 2,493 | 13,866 | 31,594 | 47,953 |
| 2020 | 2,493 | 13,878 | 31,599 | 47,970 |
| 2021 | 2,505 | 13,943 | 31,625 | 48,073 |
| 2022 | 2,512 | 14,029 | 31,857 | 48,398 |
| 2023 | 2,518 | 14,082 | 32,023 | 48,623 |
| 2024 | 2,535 | 14,150 | 32,263 | 48,948 |
| 2025 | 2,536 | 14,143 | 32,322 | 49,001 |

#### Detail-Level Row Counts (per year, per sheet)

State / District / School row counts (no `(System ID = "All", School ID = digits)` rows appear in any year — that combination is structurally absent):

| Year | All Students (s/d/sch) | Grade Level (s/d/sch) | Subgroups (s/d/sch) |
|-----:|------------------------|-----------------------|---------------------|
| 2018 | 1 / 213 / 2,278  | 13 / 2,593 / 11,221 | 14 / 2,799 / 28,738 |
| 2019 | 1 / 213 / 2,279  | 13 / 2,598 / 11,255 | 14 / 2,799 / 28,781 |
| 2020 | 1 / 215 / 2,277  | 13 / 2,618 / 11,247 | 14 / 2,833 / 28,752 |
| 2021 | 1 / 221 / 2,283  | 13 / 2,657 / 11,273 | 14 / 2,881 / 28,730 |
| 2022 | 1 / 222 / 2,289  | 13 / 2,677 / 11,339 | 14 / 2,907 / 28,936 |
| 2023 | 1 / 226 / 2,291  | 13 / 2,701 / 11,368 | 14 / 2,963 / 29,046 |
| 2024 | 1 / 234 / 2,300  | 13 / 2,743 / 11,394 | 14 / 3,042 / 29,207 |
| 2025 | 1 / 234 / 2,301  | 13 / 2,755 / 11,375 | 14 / 3,036 / 29,272 |

Note: `All Students` has 1 state row per year; `Grade Level` has 13 state rows (one per grade K-12); `Subgroups` has 14 state rows (one per demographic value, summed across the seven `Group` categories).

#### Null Counts (2025 file)

| Sheet | Total \nStudents | Chronically Absent (numeric null) | Average Daily Absenteeism Rate (numeric null) | Average Daily Attendance Rate (numeric null) |
|-------|----:|----:|----:|----:|
| All Students | 0 | 4 | 4 | 4 |
| Grade Level | 0 | 309 | 309 | 309 |
| Subgroups | 0 | 0 (column stored as string; suppression marker `TFS` used instead) | 0 (string, `TFS`) | 0 (string, `TFS`) |

`Total \nStudents`, ID columns, name columns, `Group`, and `Subgroup` are never null in any file/sheet/year.

#### Categorical Columns

`Group` (across all three sheets, all years — 9 distinct values total):

| Sheet | Distinct values of `Group` |
|-------|----------------------------|
| All Students | `All` |
| Grade Level | `Grade Level` |
| Subgroups | `English Learners`, `Gender`, `Homeless`, `Migrant`, `Race/Ethnicity`, `Socioeconomic Status`, `Students with Disabilities` |

`Subgroup` (union across all three sheets, all years — 28 distinct values):

| Group (in `Subgroups` sheet) | Subgroup values |
|------------------------------|-----------------|
| (in `All Students`) | `All` |
| `Grade Level` (13 values) | `Kindergarten`, `Grade 1`, `Grade 2`, `Grade 3`, `Grade 4`, `Grade 5`, `Grade 6`, `Grade 7`, `Grade 8`, `Grade 9`, `Grade 10`, `Grade 11`, `Grade 12` |
| `Race/Ethnicity` (6) | `American Indian/Alaskan Native`, `Asian/Pacific Islander`, `Black`, `Hispanic`, `Multi-Racial`, `White` |
| `Gender` (2) | `Female`, `Male` |
| `Students with Disabilities` (2) | `Student with Disabilities`, `Student without Disabilities` |
| `Socioeconomic Status` (1) | `Economically Disadvantaged` |
| `English Learners` (1) | `English Learner` |
| `Homeless` (1) | `Homeless` |
| `Migrant` (1) | `Migrant` |

The `Group` and `Subgroup` lexicon is **identical across all 8 years** — no new or retired demographic categories appear over time.

**Asian / Pacific Islander check**: bronze publishes only a single combined `Asian/Pacific Islander` bucket for race (no separate `Asian` or `Pacific Islander` rows in any year). Five of the six race buckets are present (American Indian/Alaskan Native, Asian/Pacific Islander, Black, Hispanic, Multi-Racial, White) — this is the pre-1997 OMB 6-bucket convention rather than the post-1997 7-bucket split. The transform must map this bronze value to the `asian_pacific_islander` code (already present in `data/gold/_dimensions/demographics.parquet`), not to `asian`. There is no separate-vs-combined collision risk — bronze never publishes both the split pair and the combined bucket in the same file.

`System ID` and `School ID` are technically Utf8 columns but contain only digit-strings (3 or 7 digits for System ID; 3 or 4 digits for School ID) and the literal `"All"`. The presence of `"All"` is what marks aggregate rows, not nulls.

#### Suppression Markers

| Column | Marker | Where it appears |
|--------|--------|------------------|
| `Chronically Absent \n(10% or more)` | `TFS` (text) | `Subgroups` sheet (every year); `Grade Level` sheet (only in 2021, 2023, 2024) |
| `Chronically Absent \n(10% or more)` | numeric `null` | `All Students` sheet (every year); `Grade Level` sheet (2018, 2019, 2020, 2022, 2025) |
| `Average Daily Absenteeism Rate` | `TFS` (text) | same pattern as above |
| `Average Daily Absenteeism Rate` | numeric `null` | same pattern as above |
| `Average Daily Attendance Rate` | `TFS` (text) | same pattern as above |
| `Average Daily Attendance Rate` | numeric `null` | same pattern as above |

`TFS` = "Too Few Students" (per the `Read Me` sheet) — Georgia's standard small-cell suppression code. It is the **only** non-numeric value that appears in any of the three rate columns across all 24 file/sheet combinations.

**Important**: In every file/sheet/year, suppression is **always all-or-nothing across the three metric columns** — when one is suppressed, all three are. There is no row anywhere in the bronze data with partial suppression. (Verified across all 24 file/sheet combinations: `partial_suppression = 0` everywhere.) `Total \nStudents` is always populated even on suppressed rows.

## ETL Considerations

### Multi-Sheet Concatenation Required

Every file has three data sheets that must be concatenated. They share the exact same 11-column schema; the row-level disambiguation comes from the `Group` and `Subgroup` columns. Reading only one sheet would silently drop demographic breakdowns.

### Column Header Whitespace and Embedded Newlines

Five column headers contain literal `\n` line breaks in the source (`School \nYear`, `System \nID`, `School \nID`, `Total \nStudents`, `Chronically Absent \n(10% or more)`). The transform must rename these explicitly — partial substring matches will silently miss them. Recommended rename map:

```python
"School \nYear" -> "year"
"System \nID" -> "district_code"
"System Name" -> "district_name"
"School \nID" -> "school_code"
"School Name" -> "school_name"
"Total \nStudents" -> "student_count"
"Chronically Absent \n(10% or more)" -> "chronically_absent_rate"
"Average Daily Absenteeism Rate" -> "average_daily_absenteeism_rate"
"Average Daily Attendance Rate" -> "average_daily_attendance_rate"
```

### Suppression Marker Dtype Drift

`Chronically Absent`, `Average Daily Absenteeism Rate`, and `Average Daily Attendance Rate` are read by polars as `Float64` in some sheet/year combinations and as `String` (Utf8) in others, depending on whether `TFS` happens to appear in that file/sheet:

| Sheet | Year-by-year dtype pattern |
|-------|-----------------------------|
| `All Students` | Float64 in **every** year (suppression as numeric null). |
| `Grade Level` | Float64 in 2018, 2019, 2020, 2022, 2025; String (Utf8) with `TFS` markers in 2021, 2023, 2024. |
| `Subgroups` | String (Utf8) with `TFS` markers in **every** year. |

Use `cast(pl.Float64, strict=False)` after first reading — `strict=False` coerces `TFS` to null directly. Apply the cast unconditionally to all three rate columns regardless of which dtype polars infers for that file/sheet, so the transform stays robust if the dtype pattern shifts in a future year.

### Geography Sentinels

State and district aggregate rows use the literal string `"All"` in `System ID` / `School ID` (and the names `"State of Georgia"` / `"All Schools"`). Per `src/etl/education/CLAUDE.md`, these must become NULL in gold according to the detail-level rules:

| Detail Level | bronze pattern | district_code | school_code |
|-------------|----------------|---------------|-------------|
| state | System ID = "All" AND School ID = "All" | NULL | NULL |
| district | System ID = digits AND School ID = "All" | zfill(3) of bronze value | NULL |
| school | System ID = digits AND School ID = digits | zfill(3) of bronze value | zfill(4) of bronze value |

There are no `(System ID = "All", School ID != "All")` rows in any year — that "other" cell of the matrix is always 0.

### ID Width Variation

`System ID` is **not** uniformly 3 digits: 183 of the 244 distinct system codes are 3-digit traditional districts (601-799 etc.), but 61 are 7-digit state-charter / state-specialty system codes (e.g., `7820618` "State Specialty Schools I- Coastal Plains"). Per the education domain convention, apply `.str.zfill(3)` — this pads 1-3 digit values to 3 characters while leaving 7-digit codes untouched. **Do not truncate** with `.str.slice(0, 3)`.

`School ID` appears as either 3-digit (267 distinct codes) or 4-digit (219 distinct codes); GaDOE represents 4-digit codes with a stripped leading zero in some cases (e.g., `"618"` is stored, but the canonical form is `"0618"`). The education domain's `.str.zfill(4)` recommendation correctly handles this — 3-digit values pad to 4-digit, and existing 4-digit values are unchanged. There are no 1- or 2-digit school IDs.

Four school-name groups switched school codes across years (e.g., Armuchee Elementary in district `657` appears as both `"402"` and `"195"` in different years — these are real GaDOE renumbering events, not zfill collisions). The dimension build should accept either code as valid; downstream joins should use `(district_code, school_code)` composite keys.

### Demographic Mapping to Global Dimension

The bronze `Subgroup` strings need to be mapped onto the global demographic codes in `data/gold/_dimensions/demographics.parquet`. All required codes are already present in the current global dimension. Mapping required (no unmapped values should remain):

| Bronze Subgroup | Gold `demographic` code |
|-----------------|--------------------------|
| `All` | `all` |
| `Female` | `female` |
| `Male` | `male` |
| `Kindergarten` | `kindergarten` |
| `Grade 1` ... `Grade 12` | `grade_1` ... `grade_12` |
| `American Indian/Alaskan Native` | `native_american` |
| `Asian/Pacific Islander` | `asian_pacific_islander` (combined bucket — see Asian/PI note in Categorical Columns) |
| `Black` | `black` |
| `Hispanic` | `hispanic` |
| `Multi-Racial` | `multiracial` |
| `White` | `white` |
| `Economically Disadvantaged` | `economically_disadvantaged` |
| `English Learner` | `english_learners` (bronze is singular, dimension is plural) |
| `Homeless` | `homeless` |
| `Migrant` | `migrant` |
| `Student with Disabilities` | `students_with_disabilities` (bronze is singular, dimension is plural) |
| `Student without Disabilities` | `students_without_disabilities` (bronze is singular, dimension is plural) |

The global demographics dimension currently has 40 codes including `asian_pacific_islander`, `asian`, and `pacific_islander` separately — confirmed at report-generation time. For this topic, use only `asian_pacific_islander` (the combined bucket); never emit `asian` or `pacific_islander` separately because bronze does not provide that split.

### Year Representation

`School \nYear` is already an `Int64` matching the filename (e.g., 2025 in `Attendance Dashboard Data - 2025.xlsx`). It represents the spring (ending) year of the school year (school year 2024-2025 → 2025). Cast to `pl.Int32` for gold per education domain conventions.

### Percentage Scale

All three rate columns are already on the 0-1 scale across every file and every sheet — verified by min/max statistics on every year (max observed value is exactly 1.0 in `Chronically Absent`; max ADAR is 0.763; max ADAttR is 1.0). **No scaling transformation is needed.** Do NOT divide by 100; do NOT multiply by 100. Just preserve the float values as-is.

### Mathematical Redundancy of Attendance vs. Absenteeism

`Average Daily Attendance Rate ≡ 1 - Average Daily Absenteeism Rate` row-by-row in every file, within rounding tolerance: maximum observed deviation `|adar + adattr - 1|` is **0.001** across every year and sheet (caused by independent rounding of each rate to 3 decimal places at publication). Both columns are still useful in gold (they answer slightly different questions and avoid forcing analysts to recompute), but the transform should author a contract `quality_checks=` invariant confirming `attendance + absenteeism ≈ 1.0` (within 0.005 tolerance, generous enough to swallow rounding) for non-suppressed rows. (There are no per-topic `validate.py` files — cross-column invariants live in the ODCS contract's quality SQL, executed on every validation run.)

### No Missing Years / Coverage

All 8 calendar years from 2018 through 2025 are present (no COVID gap — unlike CCRPI, attendance reporting continued through the pandemic). Row counts grow modestly year-over-year as new schools open.

### Read Me Sheet — Skip

The `Read Me` sheet is documentation only (definitions, the `TFS` acronym). It must not be ingested into gold; the transform should explicitly target the three data sheets by name (`"All Students"`, `"Grade Level"`, `"Subgroups"`).

### `Group` Column Is Disposable After Demographic Mapping

The `Group` column is redundant once `Subgroup` has been mapped to a `demographic` code — every gold `demographic` value implies a unique category. Drop `Group` after the demographic mapping is applied (do not carry it into the fact table).

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| `School \nYear` | fact_key | `year` | Cast to `pl.Int32`. Already matches filename year. |
| `System \nID` | fact_key | `district_code` | Cast to `pl.Utf8`, then map `"All"` → NULL for state rows, then `.str.zfill(3)`. Pads 3-digit codes while preserving 7-digit charter/state-specialty codes. |
| `System Name` | dimension_attribute | — | Goes to `districts.parquet` dimension. Title case already. Drop from fact. |
| `School \nID` | fact_key | `school_code` | Cast to `pl.Utf8`, then map `"All"` → NULL for state/district rows, then `.str.zfill(4)`. Handles both 3-digit (leading-zero-stripped) and 4-digit codes. |
| `School Name` | dimension_attribute | — | Goes to `schools.parquet` dimension. Title case already. Drop from fact. |
| `Group` | not_in_gold | — | Used during transform to identify which sheet contributed the row, but redundant with `Subgroup` once `Subgroup` is mapped to a `demographic` code. Drop after the demographic mapping is applied. |
| `Subgroup` | fact_key | `demographic` | Map to global `demographics.parquet` codes per the table above. FK to demographics dimension. |
| `Total \nStudents` | fact_metric | `student_count` | `pl.Int64`. Enrollment denominator; never null. Canonical name per data-cleaning-standards §16 ("Count of students in an enrollment / cohort slice → `student_count`"; `total_students` is an explicitly forbidden variant) — matches the v1 contract and emitted gold. |
| `Chronically Absent \n(10% or more)` | fact_metric | `chronically_absent_rate` | `pl.Float64`, 0-1 scale (NOT a percentage). Cast `TFS` → null via `.cast(pl.Float64, strict=False)`. |
| `Average Daily Absenteeism Rate` | fact_metric | `average_daily_absenteeism_rate` | `pl.Float64`, 0-1 scale. Cast `TFS` → null. |
| `Average Daily Attendance Rate` | fact_metric | `average_daily_attendance_rate` | `pl.Float64`, 0-1 scale. Cast `TFS` → null. Equal to `1 - average_daily_absenteeism_rate` within ≤ 0.001 rounding tolerance for non-suppressed rows; preserve to avoid forcing analysts to recompute. |

The fact table will have one row per `(year, district_code, school_code, demographic)` tuple, partitioned per `data/gold/education/attendance_dashboard/year=YYYY/{schools,districts,states}.parquet` per the education gold output format.

## Corrections

- **2026-06-12 (transform authoring)**: The recommended gold name for `Total \nStudents` was originally `total_students`, which is an explicitly forbidden variant under data-cleaning-standards §16 — the canonical name for an enrollment/attendance denominator is **`student_count`** (also the name used by the v1 contract and gold). Corrected in the rename map and the Gold Schema Classification table. Also replaced the stale reference to a per-topic `validate.py` (no such files exist; the attendance/absenteeism complement invariant is authored as a contract `quality_checks=` entry, executed by the generic validator on every run).
