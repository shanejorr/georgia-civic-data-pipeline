# georgia_milestones_end_of_course_eoc_assessment_by_grade — Bronze Data Structure

## Overview

- Topic: georgia_milestones_end_of_course_eoc_assessment_by_grade
- Source: gosa
- Files: 9 files spanning school years 2014-15 through 2023-24 (filename years 2015–2024, with 2020 missing — no COVID-year EOC administration)
- Unreadable files: none
- Year representation: `LONG_SCHOOL_YEAR` column in `"YYYY-YY"` format (e.g., `"2023-24"`) plus the filename year
- Filename-to-data year offset: filename year = ending calendar year of the school year (e.g., `georgia_milestones_end_of_course_eoc_assessment_by_grade_2024.csv` contains `LONG_SCHOOL_YEAR = "2023-24"`). The filename year always equals the ending calendar year of `LONG_SCHOOL_YEAR`
- Detail levels: state, district, school (encoded in `SCHOOL_DISTRCT_CD` / `INSTN_NUMBER` via the sentinel `"ALL"`)
- Percentage scale: 0–100 (the `*_PCT` columns are reported on a 0–100 scale; must be divided by 100 at gold time per `data-cleaning-standards`)
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| georgia_milestones_end_of_course_eoc_assessment_by_grade_2015.csv | 63df16b7831a3b89dc06f4a2dc8c4553e7fc34be3433c235ccc9226007b37164 |
| georgia_milestones_end_of_course_eoc_assessment_by_grade_2016.csv | f6bca921fb6d70c814d378b804febb32926da2a24eaf662f6fe65c1bdc2c09f7 |
| georgia_milestones_end_of_course_eoc_assessment_by_grade_2017.csv | 046909b828cc61c84fce40be2afc9adf4c482fe9f17cd90720245ed89a2b0478 |
| georgia_milestones_end_of_course_eoc_assessment_by_grade_2018.csv | 14f888b2a336ff208fe44679f2a19d7cb8ac3c914a1eb0dc493b2be367174884 |
| georgia_milestones_end_of_course_eoc_assessment_by_grade_2019.csv | 10fbb321f0195a12401a9565e176d3222c5d4648e4486aef5caaa906dc4cc542 |
| georgia_milestones_end_of_course_eoc_assessment_by_grade_2021.csv | 09fe336f4388ff8ac0f7df850068946747d701e5cff18f79a835cc5e06af6a26 |
| georgia_milestones_end_of_course_eoc_assessment_by_grade_2022.csv | a9c84c1a54c47f7d5052771206aea11f00daf3be0e4a6bda32a5b55f9b603da3 |
| georgia_milestones_end_of_course_eoc_assessment_by_grade_2023.csv | 46b9dc5e4fe32ad209c91f1a7d0f7124f2f3b11d97efe7e3d8802cf348ac5239 |
| georgia_milestones_end_of_course_eoc_assessment_by_grade_2024.csv | c328a9151c4e849cc7ac66b122b1f5d8df28398e128946abc8c849a2f5b0ab0b |

## Summary

Georgia Milestones End-of-Course (EOC) assessment results **disaggregated by grade level**. For each `(entity x grade x demographic subgroup x course test component)` combination, the dataset reports the **count** of students scoring at each of four achievement levels — **Beginning Learner**, **Developing Learner**, **Proficient Learner**, **Distinguished Learner** — along with the corresponding **percentage** of test-takers at each level and the overall **Number Tested** count. This is the grade-disaggregated sibling of `georgia_milestones_end_of_course_eoc_assessment` and shares the same metrics and suppression scheme; the only substantive difference is that `ACDMC_LVL` here carries real grade values (`7`/`07` to `12`) rather than the constant `"ALL GRADES"`. These metrics let a user evaluate mastery rates and the distribution of student performance across grade x demographic subgroups for each EOC course.

## Eras

Data splits into **two eras** based on column schema:

- **Era 1** (2015–2023, 8 files) — 17-column tidy format: `LONG_SCHOOL_YEAR`, 4 entity identifiers, `ACDMC_LVL`, `SUBGROUP_NAME`, `TEST_CMPNT_TYP_NM`, `NUM_TESTED_CNT`, and 4 count + 4 percentage columns for each achievement level.
- **Era 2** (2024, 1 file) — Same 17 columns plus 1 new constant-valued column prepended: `#ASSMT_CD` (always `"EOC_by_GRADE"`).

Note: 2020 is missing from bronze — EOC testing was suspended that school year (2019-20 to 2020-21) due to COVID-19 disruption.

---

### Era 1: 2015–2023 (tidy format, 17 columns)

Files: `georgia_milestones_end_of_course_eoc_assessment_by_grade_2015.csv` through `georgia_milestones_end_of_course_eoc_assessment_by_grade_2023.csv` (8 files, 2020 absent).

Each row is one `(entity x grade x demographic subgroup x test component)` combination. Entity is one of: state (`SCHOOL_DISTRCT_CD = "ALL"` and `INSTN_NUMBER = "ALL"`), district (`SCHOOL_DISTRCT_CD = value` and `INSTN_NUMBER = "ALL"`), or school (both set).

| Column | Description |
|--------|-------------|
| LONG_SCHOOL_YEAR | School year — e.g., `"2022-23"` (one value per file) |
| SCHOOL_DISTRCT_CD | District code — string; 3-digit standard codes (e.g., `"601"` for Appling County) or 7-digit state-administered codes (e.g., `"7820108"`). Value `"ALL"` marks a state-level row. **Note the typo** — `DISTRCT` not `DSTRCT` (shared with the sister `_eoc_assessment` topic and the ACT dataset's Era 3) |
| SCHOOL_DSTRCT_NM | District name — string (e.g., `"Appling County"`). Value `"ALL"` on state-level rows |
| INSTN_NUMBER | School institution number — string; **3- or 4-char** in 2015–2019 (not consistently zero-padded), **4-char zero-padded** from 2021 onward. Value `"ALL"` on district- and state-level rows |
| INSTN_NAME | School name — string. Value `"ALL"` on district- and state-level rows |
| ACDMC_LVL | Academic/grade level — 6 distinct grade values. **Padding differs by era:** 2015–2019 uses bare integers (`"7"`, `"8"`, `"9"`, `"10"`, `"11"`, `"12"`); 2021–2023 uses zero-padded strings (`"07"`, `"08"`, `"09"`, `"10"`, `"11"`, `"12"`). Must normalize (e.g., `.str.zfill(2)`) before reduction |
| SUBGROUP_NAME | Demographic subgroup name — e.g., `"All Students"`, `"White"`, `"Economically Disadvantaged"` (see categoricals below; set changes across era) |
| TEST_CMPNT_TYP_NM | Test component / course — e.g., `"Algebra I"`, `"Biology"`, `"US History"` (see categoricals below; set changes mid-era) |
| NUM_TESTED_CNT | Total students tested in the `(entity x grade x subgroup x test)` cell — Int-ish string; `"TFS"` for suppressed rows in **every** year (verified per file: 2015: 7,335; 2016: 8,436; 2017: 8,329; 2018: 7,812; 2019: 7,631; 2021: 4,352; 2022: 3,472; 2023: 3,588 — consistent with the 2023 suppression-markers table below; an earlier revision of this doc wrongly claimed 2021–2023 were never suppressed) |
| BEGIN_CNT | Count of students scoring **Beginning Learner** (lowest tier) — string; `"TFS"` when suppressed |
| DEVELOPING_CNT | Count scoring **Developing Learner** — string; `"TFS"` when suppressed |
| PROFICIENT_CNT | Count scoring **Proficient Learner** — string; `"TFS"` when suppressed |
| DISTINGUISHED_CNT | Count scoring **Distinguished Learner** (highest tier) — string; `"TFS"` when suppressed |
| BEGIN_PCT | Percentage scoring Beginning Learner — 0–100 scale; `"TFS"` when entire cell is suppressed (common in 2023) |
| DEVELOPING_PCT | Percentage scoring Developing Learner — 0–100 scale |
| PROFICIENT_PCT | Percentage scoring Proficient Learner — 0–100 scale |
| DISTINGUISHED_PCT | Percentage scoring Distinguished Learner — 0–100 scale |

#### Sample Data (2023)

```
shape: (5, 17)
| LONG_SCHOOL_YEAR | SCHOOL_DISTRCT_CD | SCHOOL_DSTRCT_NM | INSTN_NUMBER | INSTN_NAME                       | ACDMC_LVL | SUBGROUP_NAME                  | TEST_CMPNT_TYP_NM | NUM_TESTED_CNT | BEGIN_CNT | DEVELOPING_CNT | PROFICIENT_CNT | DISTINGUISHED_CNT | BEGIN_PCT | DEVELOPING_PCT | PROFICIENT_PCT | DISTINGUISHED_PCT |
|------------------|-------------------|------------------|--------------|----------------------------------|-----------|--------------------------------|-------------------|----------------|-----------|----------------|----------------|-------------------|-----------|----------------|----------------|-------------------|
| 2022-23          | 611               | Bibb County      | 0386         | Southwest High School            | 10        | Non-Migrant                    | Algebra I         | 33             | 30        | TFS            | TFS            | TFS               | 90.9      | 9.1            | 0              | 0                 |
| 2022-23          | 662               | Glascock County  | ALL          | ALL                              | 11        | Non-Migrant                    | US History        | 23             | 10        | 10             | TFS            | TFS               | 43.5      | 43.5           | 13             | 0                 |
| 2022-23          | 667               | Gwinnett County  | 0189         | Phoenix High School              | 12        | Not Economically Disadvantaged | Biology           | 12             | TFS       | TFS            | TFS            | TFS               | 58.3      | 25             | 8.3            | 8.3               |
| 2022-23          | 734               | Telfair County   | ALL          | ALL                              | 11        | Female                         | US History        | 40             | 10        | 19             | 10             | TFS               | 25        | 47.5           | 25             | 2.5               |
| 2022-23          | 696               | Marion County    | 0275         | Marion County Middle/High School | 09        | Female                         | Biology           | 48             | 16        | 15             | 12             | TFS               | 33.3      | 31.3           | 25             | 10.4              |
```

#### Statistics

Row counts per file (Era 1):

| Year file | Rows    | Test components | Demographic subgroups | Districts | Schools |
|-----------|---------|-----------------|-----------------------|-----------|---------|
| 2015      | 107,393 | 8               | 18                    | 196       | 813     |
| 2016      | 117,307 | 10              | 18                    | 195       | 842     |
| 2017      | 118,950 | 10              | 18                    | 197       | 869     |
| 2018      | 119,650 | 10              | 18                    | 197       | 872     |
| 2019      | 119,611 | 10              | 18                    | 197       | 887     |
| 2021      | 53,855  | 10              | 20                    | 202       | 857     |
| 2022      | 64,443  | 5               | 21                    | 203       | 869     |
| 2023      | 66,273  | 5               | 21                    | 202       | 870     |

- Row counts drop sharply in 2021 because total EOC administration fell post-COVID (smaller schools had suppression across more cells). The 2022 drop reflects the retirement of 5 of the 10 EOC courses.
- Percentages across the four achievement levels sum to ~100 per row (subject to rounding).
- Each row is grade-specific — multiplying the row count of `_eoc_assessment` (non-by-grade) by ~2–3 roughly matches the by-grade row count, since each course x demographic combination fans out across the grades that test-takers were in.
- Grade 7 is rare (172–360 rows per year in Era 1) — it reflects the small number of 7th graders who take EOC courses early. Grade 12 counts rise over the era as more 12th graders take make-up / retake administrations.

#### Null Counts

Per the 2015 and 2023 files:

| Column                                                                                                                  | 2015 nulls                                                                                                                        | 2023 nulls                    |
|-------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|-------------------------------|
| LONG_SCHOOL_YEAR, SCHOOL_DISTRCT_CD, SCHOOL_DSTRCT_NM, INSTN_NUMBER, INSTN_NAME, ACDMC_LVL, SUBGROUP_NAME, TEST_CMPNT_TYP_NM | 0                                                                                                                                 | 0                             |
| NUM_TESTED_CNT                                                                                                          | 0                                                                                                                                 | 0                             |
| BEGIN_CNT, DEVELOPING_CNT, PROFICIENT_CNT, DISTINGUISHED_CNT                                                            | 7,335 each (true nulls — empty CSV fields; these rows are exactly the rows with `NUM_TESTED_CNT == "TFS"`. The same pattern holds in every 2015–2019 file: 8,436 / 8,329 / 7,812 / 7,631 empty-field rows in 2016–2019)            | 0 (suppression uses `"TFS"` string) |
| BEGIN_PCT, DEVELOPING_PCT, PROFICIENT_PCT, DISTINGUISHED_PCT                                                            | 7,335 each (true nulls in 2015 in the same rows)                                                                                  | 0                             |

**Important quirk**: every 2015–2019 file carries genuine CSV nulls (empty fields) for the count/percentage columns on exactly its fully-suppressed rows (`NUM_TESTED_CNT == "TFS"`): 7,335 / 8,436 / 8,329 / 7,812 / 7,631 rows per year (an earlier revision of this doc wrongly claimed only 2015 did). In those years the `*_PCT` columns never carry the `"TFS"` string — full-row suppression uses empty fields only. 2021–2023 use the explicit `"TFS"` string throughout, including the `*_PCT` columns. Cast via `strict=False` to handle both mechanisms.

#### Year-Specific Anomalies

**2017 `DEVELOPING_CNT` missing suppression** — In the 2017 bronze CSV, `DEVELOPING_CNT` is NOT suppressed with `"TFS"` like every other year and every other count column. Instead, it contains **3,001 literal `"0"` values** and zero TFS markers — the only year/column pair where suppression is entirely absent. Two sibling year/column pairs carry literal zeros ALONGSIDE normal TFS suppression (measured directly; an earlier revision of this doc wrongly claimed no other year/column had any): **2015 `DISTINGUISHED_CNT` has 4,940 literal zeros** (TFS still on 48,267 cells; its 2015 null rate is ~52% vs 75–79% in 2016–2019, and the 2015 min is 0 vs 10 elsewhere) and **2017 `PROFICIENT_CNT` has 824 literal zeros** (TFS still on 47,937 cells). Every other year×column pair has 0 literal zeros. All three conflate true zeros with should-have-been-suppressed small counts. Per-column TFS counts confirm the 2017 asymmetry:

| Year | BEGIN_CNT TFS | DEVELOPING_CNT TFS | PROFICIENT_CNT TFS | DISTINGUISHED_CNT TFS |
|------|---------------|--------------------|--------------------|------------------------|
| 2017 | 44,314        | **0**              | 47,937             | 84,426                 |
| 2018 | 45,560        | 49,828             | 53,978             | 83,920                 |

Consequence in gold: 2017 `developing_count` has `null_pct ≈ 0.07` (~8,329 nulls) and `min_val = 0`, whereas every other year shows `null_pct` between 43–75% and `min_val = 10`. The transform faithfully passes bronze through — this is an upstream GOSA-published-file anomaly, not a transform bug. **Downstream analysts should not compare 2017 `developing_count` directly against other years** (the 2017 column conflates true zeros, near-zero counts the publisher should have suppressed, and real low-count values).

#### Categorical Columns

| Column            | Distinct Values                                                                                                                                                                      |
|-------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| LONG_SCHOOL_YEAR  | One value per file: `"2014-15"` through `"2022-23"` (no `"2019-20"` — 2020 file absent)                                                                                              |
| ACDMC_LVL         | 6 grades: 2015–2019 use `"7"`, `"8"`, `"9"`, `"10"`, `"11"`, `"12"` (unpadded); 2021–2023 use `"07"`, `"08"`, `"09"`, `"10"`, `"11"`, `"12"` (zero-padded). Grade 7 is rare             |
| SUBGROUP_NAME     | See **Demographic evolution** below — 18 to 20 to 21 values over the era                                                                                                              |
| TEST_CMPNT_TYP_NM | See **Test component evolution** below — 8 to 10 to 5 courses over the era                                                                                                            |
| SCHOOL_DSTRCT_NM  | 195–203 distinct district names per file (varies with which charter districts have data in a given year); includes the sentinel `"ALL"` for state-level rows                         |
| INSTN_NAME        | ~810–890 distinct school names per file; includes the sentinel `"ALL"` for district/state rows                                                                                       |

**Demographic evolution (SUBGROUP_NAME)**:

- 2015–2019 (18 values): `All Students`, `American Indian or Alaskan Native`, `Asian`, `Black or African American`, `Economically Disadvantaged`, `Female`, `Hispanic`, `Limited English Proficient`, `Male`, `Migrant`, `Native Hawaiian or Other Pacific Islander`, `Non-Migrant`, `Not Economically Disadvantaged`, `Not Limited English Proficient`, `Students with Disabilities`, `Students without Disabilities`, `Two or More Races`, `White`
- 2021 (20 values): adds `Active Duty` and `Homeless`
- 2022–2024 (21 values): renames `Active Duty` to `Military Connected` and adds `Foster Care`. Final set: the 18 core + `Foster Care`, `Homeless`, `Military Connected`

(Unlike the non-by-grade `_eoc_assessment` topic, the 2019 by-grade file does **not** include `Active Duty`/`Foster`/`Homeless` — those demographic codes only begin appearing from 2021 onward in this topic.)

**Test component evolution (TEST_CMPNT_TYP_NM)**:

- 2015 (8 courses): `9th Grade Literature and Composition`, `American Literature and Composition`, `Analytic Geometry`, `Biology`, `Coordinate Algebra`, `Economics/Business/Free Enterprise`, `Physical Science`, `US History`
- 2016–2021 (10 courses): adds `Algebra I` and `Geometry`
- 2022–2023 (5 courses): drops `9th Grade Literature and Composition`, `Analytic Geometry`, `Economics/Business/Free Enterprise`, `Geometry`, `Physical Science`. Remaining: `Algebra I`, `American Literature and Composition`, `Biology`, `Coordinate Algebra`, `US History`

#### Suppression Markers

Per-column breakdown from the 2023 representative file (66,273 total rows):

| Column            | Non-Numeric Values | Count (2023) | Notes                                                                                                      |
|-------------------|-------------------|--------------|------------------------------------------------------------------------------------------------------------|
| SCHOOL_DISTRCT_CD | `ALL`             | 456          | Marks state-level rows; not a suppression marker                                                           |
| INSTN_NUMBER      | `ALL`             | 20,911       | Marks state- and district-level rows; not a suppression marker                                             |
| NUM_TESTED_CNT    | `TFS`             | 3,588        | Fully suppressed rows where no signal is available                                                         |
| BEGIN_CNT         | `TFS`             | 28,222       | Suppressed count cells                                                                                     |
| DEVELOPING_CNT    | `TFS`             | 30,905       |                                                                                                            |
| PROFICIENT_CNT    | `TFS`             | 34,661       |                                                                                                            |
| DISTINGUISHED_CNT | `TFS`             | 53,210       | Highest suppression rate — very few schools/grades/demographics have students at distinguished level       |
| BEGIN_PCT         | `TFS`             | 3,588        | Present when `NUM_TESTED_CNT == "TFS"` (entire row fully suppressed)                                       |
| DEVELOPING_PCT    | `TFS`             | 3,588        |                                                                                                            |
| PROFICIENT_PCT    | `TFS`             | 3,588        |                                                                                                            |
| DISTINGUISHED_PCT | `TFS`             | 3,588        |                                                                                                            |

Treat `"TFS"` = "Too Few Students" (standard GOSA suppression marker). Cast with `strict=False` to convert to null.

---

### Era 2: 2024 (tidy format, 18 columns — adds 1 constant column)

File: `georgia_milestones_end_of_course_eoc_assessment_by_grade_2024.csv` (1 file).

Same row grain as Era 1 (one row per `entity x grade x demographic x test component`), with 1 new column prepended:

| Column            | Description                                                                                                                        |
|-------------------|------------------------------------------------------------------------------------------------------------------------------------|
| #ASSMT_CD         | Assessment code — always `"EOC_by_GRADE"`. The literal column name **starts with `#`**.                                              |
| LONG_SCHOOL_YEAR  | `"2023-24"`                                                                                                                        |
| SCHOOL_DISTRCT_CD | District code — string; both 3-char and 7-char codes (identical format to Era 1)                                                    |
| SCHOOL_DSTRCT_NM  | District name                                                                                                                      |
| INSTN_NUMBER      | School institution number — string; **always 4-char zero-padded** (e.g., `"0103"`)                                                  |
| INSTN_NAME        | School name                                                                                                                        |
| ACDMC_LVL         | Academic/grade level — zero-padded strings (`"07"`, `"08"`, `"09"`, `"10"`, `"11"`, `"12"`)                                         |
| SUBGROUP_NAME     | Demographic subgroup                                                                                                               |
| TEST_CMPNT_TYP_NM | Test component                                                                                                                     |
| NUM_TESTED_CNT    | Total students tested — string; `"TFS"` when suppressed — far more common (76,074 rows, ~55%) than 2021–2023's ~3,500–4,400 rows     |
| BEGIN_CNT / DEVELOPING_CNT / PROFICIENT_CNT / DISTINGUISHED_CNT | Counts at each achievement level — string with `"TFS"`                                                |
| BEGIN_PCT / DEVELOPING_PCT / PROFICIENT_PCT / DISTINGUISHED_PCT | Percentages at each level — 0–100 scale; **never suppressed in 2024** — always numeric, because when counts are `"TFS"` the percentages still report the rounded share |

#### Sample Data (2024)

```
shape: (5, 18)
| #ASSMT_CD    | LONG_SCHOOL_YEAR | SCHOOL_DISTRCT_CD | SCHOOL_DSTRCT_NM                                         | INSTN_NUMBER | INSTN_NAME                             | ACDMC_LVL | SUBGROUP_NAME                  | TEST_CMPNT_TYP_NM                 | NUM_TESTED_CNT | BEGIN_CNT | DEVELOPING_CNT | PROFICIENT_CNT | DISTINGUISHED_CNT | BEGIN_PCT | DEVELOPING_PCT | PROFICIENT_PCT | DISTINGUISHED_PCT |
|--------------|------------------|-------------------|----------------------------------------------------------|--------------|----------------------------------------|-----------|--------------------------------|-----------------------------------|----------------|-----------|----------------|----------------|-------------------|-----------|----------------|----------------|-------------------|
| EOC_by_GRADE | 2023-24          | 7830642           | State Charter Schools II- Destinations Career Academy    | 0642         | Destinations Career Academy of Georgia | 09        | Students without Disabilities  | Algebra: Concepts and Connections | 107            | 49        | 34             | 20             | TFS               | 45.8      | 31.8           | 18.7           | 3.7               |
| EOC_by_GRADE | 2023-24          | 636               | Columbia County                                          | 0193         | Riverside Middle School                | 07        | White                          | Algebra: Concepts and Connections | TFS            | TFS       | TFS            | TFS            | TFS               | 0         | 0              | 0              | 100               |
| EOC_by_GRADE | 2023-24          | 761               | Atlanta Public Schools                                   | 0212         | Kipp Atlanta Collegiate Charter School | 09        | Two or More Races              | Algebra: Concepts and Connections | TFS            | TFS       | TFS            | TFS            | TFS               | 50        | 25             | 0              | 25                |
| EOC_by_GRADE | 2023-24          | 761               | Atlanta Public Schools                                   | 0315         | Booker T. Washington High School       | 12        | Not Limited English Proficient | Algebra I                         | TFS            | TFS       | TFS            | TFS            | TFS               | 75        | 25             | 0              | 0                 |
| EOC_by_GRADE | 2023-24          | 707               | Newton County                                            | ALL          | ALL                                    | 12        | Not Economically Disadvantaged | Algebra I                         | TFS            | TFS       | TFS            | TFS            | TFS               | 100       | 0              | 0              | 0                 |
```

#### Statistics (2024)

- **138,747 rows**, 18 columns
- 207 distinct districts
- 879 distinct school names (includes the sentinel `"ALL"` at 41,221 rows, which marks district- and state-level aggregates)
- 21 demographic subgroups
- 6 test components (Algebra I, Algebra: Concepts and Connections, American Literature and Composition, Biology, Coordinate Algebra, US History)
- 6 grade levels (`07`, `08`, `09`, `10`, `11`, `12`); grade 7 still rare (1,171 rows) but larger than prior years; grade 12 the second-largest at 28,668 rows
- **Detail-level breakdown**: 570 state-level rows (0.4%), 40,651 district-level rows (29.3%), 97,526 school-level rows (70.3%)
- Suppression is pervasive: **~55% of rows have `NUM_TESTED_CNT = "TFS"`**, and the percentage columns never carry `"TFS"` (they always report the rounded share of each level so the four PCT columns still sum to ~100)

#### Null Counts (2024)

All 18 columns have **0 nulls** (all suppression uses the `"TFS"` string, not CSV nulls).

#### Categorical Columns (2024)

| Column            | Distinct Values                                              |
|-------------------|--------------------------------------------------------------|
| #ASSMT_CD         | `EOC_by_GRADE` (constant)                                    |
| LONG_SCHOOL_YEAR  | `2023-24`                                                    |
| ACDMC_LVL         | `07`, `08`, `09`, `10`, `11`, `12`                           |
| SUBGROUP_NAME     | 21 values — same set as 2022–2023                            |
| TEST_CMPNT_TYP_NM | 6 values (adds `Algebra: Concepts and Connections`)          |
| SCHOOL_DSTRCT_NM  | 207 distinct (includes sentinel `ALL`)                       |
| INSTN_NAME        | 879 distinct (includes sentinel `ALL`)                       |

#### Suppression Markers (2024)

| Column                                                       | Non-Numeric Values | Count (2024)              |
|--------------------------------------------------------------|-------------------|---------------------------|
| SCHOOL_DISTRCT_CD                                            | `ALL`             | 570 (state-level rows)    |
| INSTN_NUMBER                                                 | `ALL`             | 41,221 (district + state) |
| NUM_TESTED_CNT                                               | `TFS`             | 76,074                    |
| BEGIN_CNT                                                    | `TFS`             | 101,465                   |
| DEVELOPING_CNT                                               | `TFS`             | 104,552                   |
| PROFICIENT_CNT                                               | `TFS`             | 106,804                   |
| DISTINGUISHED_CNT                                            | `TFS`             | 122,576                   |
| BEGIN_PCT / DEVELOPING_PCT / PROFICIENT_PCT / DISTINGUISHED_PCT | (none — 0 `"TFS"`) | 0                         |

---

## ETL Considerations

1. **Two-era schema** — Era 2 (2024) prepends `#ASSMT_CD` but otherwise shares column names with Era 1. The constant column (`"EOC_by_GRADE"`) can be dropped from gold. A single per-era read-function approach works well: Era 1 reads the 17 columns directly; Era 2 strips the extra `#ASSMT_CD` constant.

2. **`#ASSMT_CD` column with `#` prefix (Era 2)** — The column name literally starts with `#`. Polars `pl.read_csv` reads this fine, but reference it as the literal string `"#ASSMT_CD"`. Always `"EOC_by_GRADE"`; drop from gold. (Note: this value is different from the sister `_eoc_assessment` topic's `"EOC"` — do not hard-code `"EOC"` when checking `#ASSMT_CD` validity.)

3. **`ACDMC_LVL` is a real categorical here, NOT a constant** — Unlike the sister `_eoc_assessment` topic where `ACDMC_LVL == "ALL GRADES"`, this topic carries actual grade values and they are the point of the dataset. Preserve it as a `fact_categorical` in gold.

4. **Grade padding differs across eras** — 2015–2019 uses `"7"` .. `"12"` (unpadded); 2021–2024 uses `"07"` .. `"12"` (zero-padded). Normalize to a single format at the top of the transform (recommend `.str.zfill(2)` so all grades are 2-char). Otherwise downstream joins and filters will miss rows.

5. **Column-name typo `SCHOOL_DISTRCT_CD`** — Both eras use the typo spelling `DISTRCT` (missing `I`). Unlike the ACT dataset, this topic does **not** rename it to `SCHOOL_DSTRCT_CD` in 2024. Preserve the typo literally when reading bronze.

6. **ID column formatting varies across eras**:
   - **`INSTN_NUMBER`**:
     - 2015–2019 — mix of 3-char and 4-char (e.g., `"103"`, `"4050"`) — not consistently zero-padded
     - 2021–2024 — always 4-char zero-padded (e.g., `"0103"`)
     - Standardize to 4-char with `.str.zfill(4)` per the education domain convention (FK to schools dimension). School codes are NOT globally unique — PK in the dimension is `(school_code, district_code)`.
   - **`SCHOOL_DISTRCT_CD`**:
     - All eras — 3-char standard codes (e.g., `"601"`) or 7-char state-administered codes (e.g., `"7820108"`, `"7830642"`); the sentinel `"ALL"` marks state-level rows.
     - Pad with `.str.zfill(3)` per education domain — **never truncate** 7-char codes.

7. **Detail-level detection via `"ALL"` sentinels**:
   - State-level: `SCHOOL_DISTRCT_CD == "ALL"` AND `INSTN_NUMBER == "ALL"`
   - District-level: `SCHOOL_DISTRCT_CD != "ALL"` AND `INSTN_NUMBER == "ALL"`
   - School-level: both are non-`"ALL"` values
   - No `(SCHOOL_DISTRCT_CD == "ALL", INSTN_NUMBER != "ALL")` rows were observed.
   After detail-level classification, NULL-out the geography keys per the education star-schema rule (state rows null both keys; district rows null `school_code`).

8. **State-level row marker**: When `SCHOOL_DISTRCT_CD == "ALL"`, the `SCHOOL_DSTRCT_NM` is also `"ALL"`. Similarly, district-level rows have `INSTN_NAME == "ALL"`. Treat these literal `"ALL"` strings as sentinels to replace with null in gold.

9. **7-digit state-administered districts** — Codes like `7820614` (State Charter Schools-International Charter), `7830642` (State Charter Schools II-Destinations Career Academy), `7830624`, `7830634`, `7830647`, etc., are real entities and must be preserved. They typically have null census IDs in the districts dimension. See the `educator_qualifications_*`, `act_scores`, and `advanced_placement_ap_scores` bronze reports for the canonical list.

10. **Suppression marker `"TFS"`** — "Too Few Students" — appears in the count columns (`NUM_TESTED_CNT`, `BEGIN_CNT`, `DEVELOPING_CNT`, `PROFICIENT_CNT`, `DISTINGUISHED_CNT`) across all years, and in the percentage columns (`*_PCT`) in **2021–2023 only** (when `NUM_TESTED_CNT == "TFS"`); in 2015–2019 fully-suppressed rows blank the `*_PCT` (and count) columns with genuine empty CSV fields instead of the `"TFS"` string (see #11). In 2024, percentages are never suppressed — they report the rounded distribution even when the underlying counts are `"TFS"`. Cast all metric columns with `.cast(pl.Float64, strict=False)` to convert `"TFS"` and empty fields to null.

11. **2015–2019 genuine-null quirk** — Every 2015–2019 file contains rows with **genuine empty CSV values** (not `"TFS"`) in all 4 count and 4 percentage columns: 7,335 / 8,436 / 8,329 / 7,812 / 7,631 rows per year. Those are exactly the rows where `NUM_TESTED_CNT == "TFS"` (an earlier revision of this doc wrongly limited this to 2015). Handle them the same as `"TFS"` (cast to null); `strict=False` casting will convert both empty strings and `"TFS"` to null.

12. **Demographic subgroup renames**:
   - 2015–2019 — stable 18-value set (this topic does NOT contain `Active Duty`/`Foster`/`Homeless` in 2019, unlike the non-by-grade sister topic)
   - 2021 — adds `Active Duty` and `Homeless` (20 values)
   - 2022+ — renames `Active Duty` to `Military Connected`; adds `Foster Care` (21 values)
   Per the `data-cleaning-standards` skill, route `SUBGROUP_NAME` through `normalize_demographic_column()` from `src/utils/demographics.py`. If `Active Duty` / `Military Connected` / `Foster Care` aren't in `DEMOGRAPHIC_ALIASES`, add them (map `Active Duty`/`Military Connected` to the same canonical, both `Foster` variants to the same canonical) rather than silently emitting `"99999999"`.

13. **Test component renames**:
   - The big change is the 2022 retirement of 5 courses (`9th Grade Literature and Composition`, `Analytic Geometry`, `Economics/Business/Free Enterprise`, `Geometry`, `Physical Science`). This is a real-world curriculum change, not a column rename — preserve the historical course identities.
   - **2024 adds `Algebra: Concepts and Connections`** — a new integrated-math course (note the colon). Keep it distinct; do not attempt to merge with `Algebra I` or `Coordinate Algebra`.
   - `TEST_CMPNT_TYP_NM` is academic content, so the gold categorical is **`subject`** (NOT `test_component`, which is reserved for SAT/ACT-style non-academic sections) per `data-cleaning-standards` §16, snake_cased via a topic-local map and passed through `apply_subject_normalization` from `src/utils/subjects.py`. Curriculum-era distinctions (`algebra_i` / `coordinate_algebra` / `algebra_concepts_and_connections`; `geometry` / `analytic_geometry`) stay distinct.

14. **Count-metric scaling** — All count columns (`NUM_TESTED_CNT`, `BEGIN_CNT`, `DEVELOPING_CNT`, `PROFICIENT_CNT`, `DISTINGUISHED_CNT`) are raw integer counts. Cast to Int32 or Int64 after converting `"TFS"`.

15. **Percentage scaling** — All `*_PCT` columns are 0–100 (e.g., `34.1` means 34.1%). Per `data-cleaning-standards`, divide by 100 at gold time so metrics land on the 0–1 scale (gold convention). `BEGIN_PCT + DEVELOPING_PCT + PROFICIENT_PCT + DISTINGUISHED_PCT` never exceeds 100.2 (rounding slack), but it is NOT a partition that always sums to ~100: verified per file, sums sit in [99.9, 100.2] for 2015–2022 but undershoot in 2023 (4 rows, min 91.0) and 2024 (min 0.0; min 6.8 among rows with numeric `NUM_TESTED_CNT`). The percentages are computed against `NUM_TESTED_CNT`, which includes test-takers without a valid achievement-level score (see #23). Only the upper bound is an enforceable invariant.

16. **Percentages present even when counts are suppressed (Era 2 / 2024)** — When all 4 count columns are `"TFS"`, the 4 percentage columns still contain real numbers on a 0–100 scale. This means in 2024 the percentages are usable even when individual counts are suppressed. In 2015–2023, rows with `NUM_TESTED_CNT == "TFS"` have percentages as `"TFS"` as well (no signal), but rows with `NUM_TESTED_CNT` numeric always have numeric percentages. Don't inadvertently treat the 2024 percentages as artifacts of division-by-zero.

17. **Year representation** — `LONG_SCHOOL_YEAR` uses `"YYYY-YY"` format. Parse via `.str.split("-").list.get(0).cast(pl.Int32) + 1` (ending-calendar-year convention from `src/etl/education/CLAUDE.md`). The filename year always equals the ending calendar year; use it as a sanity-check.

18. **Missing 2020 file** — No file for school year 2019-20. This is expected (EOC testing suspended during initial COVID-19 closures). Do **not** attempt to interpolate or infer values; simply skip that year. `validate.py` should not error on the gap.

19. **Quoting changes mid-era** — 2015–2019 files are unquoted CSVs; 2021–2024 files quote every field. Polars `pl.read_csv` handles both transparently. No action needed.

20. **Row-grain PK** — The natural PK for a gold fact row is `(year, district_code, school_code, demographic, grade_level, subject)`, with NULLs in `district_code`/`school_code` per detail level. Verify uniqueness when deduplicating (use `deduplicate_by_detail_level()` from `src/utils/transformers.py`). Note that `grade_level` is a required part of the PK here, unlike the non-by-grade sister topic. (Verified: no duplicate natural keys exist within any bronze file, so dedup is a pure safety net.)

21. **Courses with very low row counts in later years** — `Coordinate Algebra` drops from ~15,000 rows per file (2015) to ~1,800 in 2023 and ~1,200 in 2024. This is a real curriculum change; do not filter these rows. The new `Algebra: Concepts and Connections` (2024, ~37,000 rows) appears to be replacing it over time.

22. **Relationship to sister topic `_eoc_assessment`** — The by-grade topic disaggregates each `(entity x demographic x course)` cell from `_eoc_assessment` into separate rows per grade (`ACDMC_LVL`). Summing the counts across grades should match the parent topic's numbers for each cell (subject to suppression differences). Both topics share the same suppression conventions, column typo, `#ASSMT_CD` prefix in 2024, and state/district/school detail pattern.

23. **Level counts reconcile to `NUM_TESTED_CNT` as an upper bound, not an equality** — Verified per file: where all five counts are numeric, `BEGIN_CNT + DEVELOPING_CNT + PROFICIENT_CNT + DISTINGUISHED_CNT` equals `NUM_TESTED_CNT` exactly in 2015–2022, but undershoots it on 1 row in 2023 (−3) and 249 rows in 2024 (down to −70) — test-takers without a valid achievement-level score count toward `NUM_TESTED_CNT` but appear in no band. The sum (and every single band count) never exceeds `NUM_TESTED_CNT` in any year, so only the ≤ relationship is an enforceable invariant.

## Gold Schema Classification

| Bronze Column              | Gold Role            | Gold Name          | Notes                                                                                                                                                                                                                                                                                    |
|----------------------------|----------------------|--------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| #ASSMT_CD (Era 2 only)     | not_in_gold          | —                  | Constant `"EOC_by_GRADE"`; drop                                                                                                                                                                                                                                                          |
| LONG_SCHOOL_YEAR           | fact_key             | year               | Int32; parse `"YYYY-YY"` to ending calendar year                                                                                                                                                                                                                                         |
| SCHOOL_DISTRCT_CD          | fact_key             | district_code      | Utf8; `.str.zfill(3)` to pad 3-digit standard codes; preserve 7-digit state-administered codes as-is; `"ALL"` to NULL (state-level)                                                                                                                                                       |
| SCHOOL_DSTRCT_NM           | dimension_attribute  | —                  | `district_name` in the districts dimension                                                                                                                                                                                                                                               |
| INSTN_NUMBER               | fact_key             | school_code        | Utf8; `.str.zfill(4)`; `"ALL"` to NULL (district- or state-level)                                                                                                                                                                                                                        |
| INSTN_NAME                 | dimension_attribute  | —                  | `school_name` in the schools dimension                                                                                                                                                                                                                                                   |
| ACDMC_LVL                  | fact_categorical     | grade_level        | Utf8; `.str.zfill(2)` to reconcile `"7"` vs `"07"` across eras. Values: `"07"`, `"08"`, `"09"`, `"10"`, `"11"`, `"12"`                                                                                                                                                                   |
| SUBGROUP_NAME              | fact_key             | demographic        | Normalize via `normalize_demographic_column()`; FK to global demographics dimension. Add `Active Duty`/`Military Connected`/`Foster Care` aliases to `DEMOGRAPHIC_ALIASES` if not already present                                                                                          |
| TEST_CMPNT_TYP_NM          | fact_categorical     | subject            | snake_case per §16 (`subject`, not `test_component` — academic content): `9th_grade_literature_and_composition`, `algebra_i`, `algebra_concepts_and_connections`, `american_literature_and_composition`, `analytic_geometry`, `biology`, `coordinate_algebra`, `economics_business_free_enterprise`, `geometry`, `physical_science`, `us_history` |
| NUM_TESTED_CNT             | fact_metric          | num_tested         | Int64; cast `strict=False` to handle `"TFS"` and empty strings                                                                                                                                                                                                                           |
| BEGIN_CNT                  | fact_metric          | num_beginning_learner | Int64; §16 canonical `num_<level>_learner`                                                                                                                                                                                                                                            |
| DEVELOPING_CNT             | fact_metric          | num_developing_learner | Int64                                                                                                                                                                                                                                                                                |
| PROFICIENT_CNT             | fact_metric          | num_proficient_learner | Int64                                                                                                                                                                                                                                                                                |
| DISTINGUISHED_CNT          | fact_metric          | num_distinguished_learner | Int64                                                                                                                                                                                                                                                                             |
| BEGIN_PCT                  | fact_metric          | pct_beginning_learner | Float64; **divide by 100** per `data-cleaning-standards` (0–1 scale in gold); §16 canonical `pct_<level>_learner`                                                                                                                                                                     |
| DEVELOPING_PCT             | fact_metric          | pct_developing_learner | Float64; divide by 100                                                                                                                                                                                                                                                               |
| PROFICIENT_PCT             | fact_metric          | pct_proficient_learner | Float64; divide by 100                                                                                                                                                                                                                                                               |
| DISTINGUISHED_PCT          | fact_metric          | pct_distinguished_learner | Float64; divide by 100                                                                                                                                                                                                                                                            |
| (derived)                  | fact_metric          | pct_developing_learner_or_above | Float64; transform-derived per §16 = developing + proficient + distinguished pcts (NULL-propagating)                                                                                                                                                                        |
| (derived)                  | fact_metric          | pct_proficient_learner_or_above | Float64; transform-derived per §16 = proficient + distinguished pcts (NULL-propagating)                                                                                                                                                                                     |

**Detail-level split**: After classification, split the fact table into `schools.parquet`, `districts.parquet`, and `states.parquet` per-year partitions (per the education domain output format). The state-level rows are ~450–600 rows per year (6 grades x ~21 demographics x 4–10 courses); district-level rows are ~20,000–40,000 per year; school-level rows are the bulk (~45,000–100,000 per year).

**Column order in each fact file** (per `data-cleaning-standards`): `year`, `district_code` (NULL for states), `school_code` (NULL for states and districts), `demographic`, `grade_level`, `subject`, then metric columns in this order: `num_tested`, `num_beginning_learner`, `num_developing_learner`, `num_proficient_learner`, `num_distinguished_learner`, `pct_beginning_learner`, `pct_developing_learner`, `pct_proficient_learner`, `pct_distinguished_learner`, `pct_developing_learner_or_above`, `pct_proficient_learner_or_above`.
