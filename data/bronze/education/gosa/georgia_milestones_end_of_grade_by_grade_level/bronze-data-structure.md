# georgia_milestones_end_of_grade_eog_assessment_by_grade — Bronze Data Structure

## Overview

- Topic: georgia_milestones_end_of_grade_eog_assessment_by_grade
- Source: gosa
- Files: 9 CSV files spanning school years 2014-15 through 2023-24 (filename years 2015–2024, with **2020 missing** — no EOG administration due to COVID-19 disruption)
- Unreadable files: none
- Year representation: `LONG_SCHOOL_YEAR` column in `"YYYY-YY"` format (e.g., `"2023-24"`) plus the filename year
- Filename-to-data year offset: filename year = **ending** calendar year of the school year (e.g., `georgia_milestones_end_of_grade_eog_assessment_by_grade_2024.csv` contains `LONG_SCHOOL_YEAR = "2023-24"`). The filename year always equals the ending calendar year of `LONG_SCHOOL_YEAR`
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
| georgia_milestones_end_of_grade_eog_assessment_by_grade_2015.csv | 0879b1b81777647cdb9ac9e1fa274c1a95eb9e6303fd93a72aa4134daea6bdd0 |
| georgia_milestones_end_of_grade_eog_assessment_by_grade_2016.csv | 378e06eee7ed85b77a58a288fca4fc873c8e2247a8ae413adb68344118201455 |
| georgia_milestones_end_of_grade_eog_assessment_by_grade_2017.csv | 3142bd3116b37d5ff6c64ff03c996537a94cfbdc97c02d6f9d47f16728bb758d |
| georgia_milestones_end_of_grade_eog_assessment_by_grade_2018.csv | 57fe6d4dc93960b04366f07fad42ffcfd5a1560c68ac156b8e86fa2fb06f31c5 |
| georgia_milestones_end_of_grade_eog_assessment_by_grade_2019.csv | 236ef06ba0c35e05ae434ac7eaeecb371d314a665dd91707e0ff0f796a14383f |
| georgia_milestones_end_of_grade_eog_assessment_by_grade_2021.csv | 1690cee4fa727af738b8f96b5ac756f62c7cb162bb32bec9d0e387c41dd813bb |
| georgia_milestones_end_of_grade_eog_assessment_by_grade_2022.csv | 8f8d3caa4454b896c9921ef0f8c9a80c21ee4bdc2ec1bd22154735ddbbe3f742 |
| georgia_milestones_end_of_grade_eog_assessment_by_grade_2023.csv | eb6fd7f16202d93d3b6df76283b508e14704994f47232a155827c667e6ce7468 |
| georgia_milestones_end_of_grade_eog_assessment_by_grade_2024.csv | 25eee2cdeb1cc1814c516a73c5913199e96d7cf91ce86a20d547420b136cf296 |

## Summary

Georgia Milestones End-of-Grade (EOG) assessment results for Georgia public elementary and middle schools (grades 3–8), **broken out by individual grade level**. For each `(entity × demographic subgroup × content area × grade)` combination, the dataset reports the **count** of students scoring at each of four achievement levels — **Beginning Learner**, **Developing Learner**, **Proficient Learner**, **Distinguished Learner** — along with the corresponding **percentage** of test-takers at each level and the overall **Number Tested** count. This is the per-grade companion to the sibling rollup topic `georgia_milestones_end_of_grade_eog_assessment` (which reports the same measurements with `ACDMC_LVL = "ALL GRADES"` instead of grades 3–8). The per-grade grain lets users evaluate mastery rates by content area, demographic subgroup, and **specific grade band** across the four (and later five) state-required EOG content areas: English Language Arts, Mathematics, Science, Social Studies, and (from 2022 onward) Physical Science (an 8th-grade option for accelerated middle-school students).

## Eras

Data splits into **two eras** based on column schema:

- **Era 1** (2015–2023, 8 files) — 17-column tidy format: `LONG_SCHOOL_YEAR`, 4 entity identifiers, `ACDMC_LVL` (grade 3–8), `SUBGROUP_NAME`, `TEST_CMPNT_TYP_NM`, `NUM_TESTED_CNT`, and 4 count + 4 percentage columns for each achievement level.
- **Era 2** (2024, 1 file) — Same 17 columns plus 1 new constant column prepended: `#ASSMT_CD` (always `"EOG_by_GRADE"`). Total = 18 columns.

Note: 2020 is absent from bronze — EOG administration was cancelled that school year (2019-20 → 2020-21) due to COVID-19 school closures.

---

### Era 1: 2015–2023 (tidy format, 17 columns)

Files: `georgia_milestones_end_of_grade_eog_assessment_by_grade_2015.csv` through `georgia_milestones_end_of_grade_eog_assessment_by_grade_2023.csv` (8 files, 2020 absent).

Each row is one `(entity × grade × demographic subgroup × content area)` combination. Entity is one of: state (`SCHOOL_DISTRCT_CD = "ALL"` AND `INSTN_NUMBER = "ALL"`), district (`SCHOOL_DISTRCT_CD = value` AND `INSTN_NUMBER = "ALL"`), or school (both set to real values).

| Column | Description |
|--------|-------------|
| LONG_SCHOOL_YEAR | School year — e.g., `"2022-23"` (one value per file) |
| SCHOOL_DISTRCT_CD | District code — string; 3-digit standard codes (e.g., `"601"` for Appling County) or 7-digit state-administered codes (e.g., `"7820120"` for State Charter Schools – Georgia Cyber Academy). Value `"ALL"` marks a state-level row. **Note the typo** — `DISTRCT` not `DSTRCT` (shared with the sibling EOG rollup, EOC, and ACT Era 3 datasets) |
| SCHOOL_DSTRCT_NM | District name — string (e.g., `"Appling County"`, `"State Charter Schools- Georgia Cyber Academy"`). Value `"ALL"` on state-level rows |
| INSTN_NUMBER | School institution number — string; 3- or 4-char (not consistently zero-padded in 2015 and 2019). Value `"ALL"` on district- and state-level rows |
| INSTN_NAME | School name — string (e.g., `"Appling County Elementary School"`). Value `"ALL"` on district- and state-level rows |
| ACDMC_LVL | Academic level / grade — one of grades 3–8. Format varies by year: `"3"` – `"8"` in 2015 and 2019, but `"03"` – `"08"` (zero-padded) in 2016–2018 and 2021–2024. **This is the column that makes this topic grain-different from the rollup sibling — each row is a single grade, not an all-grades total.** |
| SUBGROUP_NAME | Demographic subgroup name — e.g., `"All Students"`, `"White"`, `"Economically Disadvantaged"` (see categoricals below) |
| TEST_CMPNT_TYP_NM | Content area / subject — e.g., `"English Language Arts"`, `"Mathematics"`, `"Science"`, `"Social Studies"`, `"Physical Science"` (see categoricals below; set changes mid-era) |
| NUM_TESTED_CNT | Total students tested in the `(entity × grade × subgroup × subject)` cell — Int-ish string; `"TFS"` for suppressed rows in 2015, 2019, and 2021+, but empty string in 2016–2018 |
| BEGIN_CNT | Count of students scoring **Beginning Learner** (lowest tier) — string; `"TFS"` or empty when suppressed |
| DEVELOPING_CNT | Count scoring **Developing Learner** — string; `"TFS"` or empty when suppressed |
| PROFICIENT_CNT | Count scoring **Proficient Learner** — string; `"TFS"` or empty when suppressed |
| DISTINGUISHED_CNT | Count scoring **Distinguished Learner** (highest tier) — string; `"TFS"` or empty when suppressed (highest rate of suppression — ~70% of rows) |
| BEGIN_PCT | Percentage scoring Beginning Learner — 0–100 scale; `"TFS"` when entire cell is suppressed (2021–2023) or empty (2015–2019) |
| DEVELOPING_PCT | Percentage scoring Developing Learner — 0–100 scale |
| PROFICIENT_PCT | Percentage scoring Proficient Learner — 0–100 scale |
| DISTINGUISHED_PCT | Percentage scoring Distinguished Learner — 0–100 scale |

#### Sample Data (2015)

```
shape: (5, 17)
┌──────────────────┬───────────────────┬──────────────────┬──────────────┬─────────────────────────────┬───────────┬────────────────────────────────┬───────────────────┬────────────────┬───────────┬────────────────┬────────────────┬───────────────────┬───────────┬────────────────┬────────────────┬───────────────────┐
│ LONG_SCHOOL_YEAR │ SCHOOL_DISTRCT_CD │ SCHOOL_DSTRCT_NM │ INSTN_NUMBER │ INSTN_NAME                  │ ACDMC_LVL │ SUBGROUP_NAME                  │ TEST_CMPNT_TYP_NM │ NUM_TESTED_CNT │ BEGIN_CNT │ DEVELOPING_CNT │ PROFICIENT_CNT │ DISTINGUISHED_CNT │ BEGIN_PCT │ DEVELOPING_PCT │ PROFICIENT_PCT │ DISTINGUISHED_PCT │
╞══════════════════╪═══════════════════╪══════════════════╪══════════════╪═════════════════════════════╪═══════════╪════════════════════════════════╪═══════════════════╪════════════════╪═══════════╪════════════════╪════════════════╪═══════════════════╪═══════════╪════════════════╪════════════════╪═══════════════════╡
│ 2014-15          │ 732               │ Tattnall County  │ 101          │ Reidsville Middle School    │ 8         │ Economically Disadvantaged     │ Mathematics       │ 102            │ 16        │ 56             │ 26             │ TFS               │ 15.7      │ 54.9           │ 25.5           │ 3.9               │
│ 2014-15          │ 644               │ DeKalb County    │ 4058         │ Hightower Elementary School │ 4         │ All Students                   │ Science           │ 127            │ 61        │ 52             │ 14             │ TFS               │ 48        │ 40.9           │ 11             │ 0                 │
│ 2014-15          │ 785               │ Rome City        │ 3052         │ Main Elementary School      │ 3         │ All Students                   │ Science           │ 40             │ 27        │ 12             │ TFS            │ TFS               │ 67.5      │ 30             │ 2.5            │ 0                 │
│ 2014-15          │ 706               │ Muscogee County  │ 4056         │ Davis Elementary School     │ 3         │ Not Limited English Proficient │ Science           │ 48             │ 26        │ 16             │ TFS            │ TFS               │ 54.2      │ 33.3           │ 10.4           │ 2.1               │
│ 2014-15          │ 723               │ Schley County    │ ALL          │ ALL                         │ 5         │ Non-Migrant                    │ Science           │ 101            │ 13        │ 29             │ 46             │ 13                │ 12.9      │ 28.7           │ 45.5           │ 12.9              │
└──────────────────┴───────────────────┴──────────────────┴──────────────┴─────────────────────────────┴───────────┴────────────────────────────────┴───────────────────┴────────────────┴───────────┴────────────────┴────────────────┴───────────────────┴───────────┴────────────────┴────────────────┴───────────────────┘
```

#### Statistics

Row counts and breakdown per file (Era 1):

| Year file | LONG_SCHOOL_YEAR | Total rows | State rows | District rows | School rows | Districts | Schools | Subgroups | Subjects |
|-----------|------------------|-----------:|-----------:|--------------:|------------:|----------:|--------:|----------:|---------:|
| 2015 | 2014-15 | 288,475 | 432 | 54,502 | 233,541 | 197 | 1,697 | 18 | 4 |
| 2016 | 2015-16 | 290,060 | 432 | 54,872 | 234,756 | 201 | 1,703 | 18 | 4 |
| 2017 | 2016-17 | 194,195 | 294 | 36,936 | 156,965 | 204 | 1,708 | 18 | 4 |
| 2018 | 2017-18 | 194,378 | 292 | 37,380 | 156,706 | 209 | 1,721 | 18 | 4 |
| 2019 | 2018-19 | 195,503 | 292 | 37,508 | 157,703 | 210 | 1,719 | 18 | 4 |
| 2021 | 2020-21 | 170,679 | 304 | 36,045 | 134,330 | 218 | 1,714 | 20 | 4 |
| 2022 | 2021-22 | 190,320 | 343 | 39,163 | 150,814 | 219 | 1,723 | 21 | 5 |
| 2023 | 2022-23 | 192,568 | 348 | 39,890 | 152,330 | 222 | 1,725 | 21 | 5 |

**Grade x subject availability per year** — Unlike the rollup sibling, this topic only includes rows for `(grade, subject)` combinations that were actually tested. The 2017 row-count drop (~33% relative to 2015–2016) reflects Georgia's policy change to administer Science and Social Studies only in **grades 5 and 8** (plus a handful of administrative audit rows elsewhere). Full grid:

| Year | ELA (grades) | Mathematics (grades) | Science (grades) | Social Studies (grades) | Physical Science (grades) |
|------|--------------|----------------------|------------------|-------------------------|---------------------------|
| 2015 | 3–8 | 3–8 | 3–8 | 3–8 | — |
| 2016 | 3–8 | 3–8 | 3–8 | 3–8 | — |
| 2017 | 3–8 | 3–8 | **5, 8 only** | **5, 8 only** | — |
| 2018 | 3–8 | 3–8 | **5, 8 only** | **5, 8 only** | — |
| 2019 | 3–8 | 3–8 | **5, 8 only** | **5, 8 only** | — |
| 2021 | 3–8 | 3–8 | **5, 8 only** | **8 only** | — |
| 2022 | 3–8 | 3–8 | **5, 8 only** | **8 only** | **8 only** |
| 2023 | 3–8 | 3–8 | **5, 8 only** | **8 only** | **8 only** |
| 2024 | 3–8 | 3–8 | **5, 8 only** (plus small 3–7 audit cells) | **8 only** (plus small 3–7 audit cells) | **8 only** |

A small number (typically 3–13) of rows exist outside the main-administration grades (e.g., 3 Science rows at grade 4 in 2017). These are rare audit/retest cells — the row counts are two or more orders of magnitude below the main `(grade, subject)` cells and can be safely retained through the transform.

- State rows grow as new subgroups are added (18 x 4 x 6 = 432 in 2015–2016; smaller in 2017–2019 because Science/Social Studies drop to grades 5 and 8 only; 348 in 2023 = 21 subgroups x mix of subject-grade cells).
- Percentages across the four achievement levels sum to ~100 per row (mean 99.9 in 2023; subject to rounding) — **except `Foster Care` rows from 2022 onward**: every row in any year whose four percentages deviate from 100 by more than ±2 is a `Foster Care` row (206 rows in 2022, 282 in 2023, 4,738 in 2024; zero deviators in 2015–2021). See ETL consideration 23.
- `Active Duty` and `Homeless` added in 2021; `Active Duty` → `Military Connected` rename and `Foster Care` added in 2022+; `Physical Science` subject added in 2022.

#### Null Counts

Per the 2015 and 2023 files (representative of the two suppression patterns):

| Column | 2015 nulls | 2023 nulls |
|--------|-----------:|-----------:|
| LONG_SCHOOL_YEAR, SCHOOL_DISTRCT_CD, SCHOOL_DSTRCT_NM, INSTN_NUMBER, INSTN_NAME, ACDMC_LVL, SUBGROUP_NAME, TEST_CMPNT_TYP_NM | 0 | 0 |
| NUM_TESTED_CNT | 0 | 0 |
| BEGIN_CNT, DEVELOPING_CNT, PROFICIENT_CNT, DISTINGUISHED_CNT | 521 each (genuine empty; plus `"TFS"` also present — see note) | 0 (suppression uses only `"TFS"` string) |
| BEGIN_PCT, DEVELOPING_PCT, PROFICIENT_PCT, DISTINGUISHED_PCT | 521 each (genuine empty) | 0 |

**Important quirk — mixed suppression marking within Era 1**:

| Year | Suppression mechanism in count/pct columns |
|------|--------------------------------------------|
| 2015 | Both: `"TFS"` string (83,830 in BEGIN_CNT, 207,760 in DISTINGUISHED_CNT) AND **521 genuine CSV nulls** (rows with `NUM_TESTED_CNT = "TFS"` carry true empty fields for counts/pcts) |
| 2016 | **Genuine CSV nulls only** — 520 rows with empty BEGIN_CNT; no `"TFS"` anywhere |
| 2017 | **Genuine CSV nulls only** — 383 rows |
| 2018 | **Genuine CSV nulls only** — 403 rows |
| 2019 | Both: 73,445 `"TFS"` in BEGIN_CNT AND 437 genuine nulls |
| 2021 | `"TFS"` string only (54,557 in BEGIN_CNT; 683 in BEGIN_PCT) |
| 2022 | `"TFS"` string only (60,479 in BEGIN_CNT; 381 in BEGIN_PCT) |
| 2023 | `"TFS"` string only (63,119 in BEGIN_CNT; 357 in BEGIN_PCT) |

Cast with `.cast(pl.Float64, strict=False)` to convert **both** `"TFS"` and empty strings to null.

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| LONG_SCHOOL_YEAR | One value per file: `"2014-15"` through `"2022-23"` (no `"2019-20"` — 2020 file absent) |
| ACDMC_LVL | `"3"`–`"8"` in 2015 and 2019; `"03"`–`"08"` in 2016–2018 and 2021–2023 (zero-padded). Six distinct values per file |
| SUBGROUP_NAME | See **Demographic evolution** below — 18 → 20 → 21 values over the era |
| TEST_CMPNT_TYP_NM | See **Content area evolution** below — 4 → 5 subjects over the era |
| SCHOOL_DSTRCT_NM | 197–222 distinct district names per file (varies with which charter districts have data in a given year) |
| INSTN_NAME | ~1,700 distinct school names per file (plus sentinel `"ALL"`) |

**Demographic evolution (SUBGROUP_NAME)**:
- 2015–2019 (18 values): `All Students`, `American Indian or Alaskan Native`, `Asian`, `Black or African American`, `Economically Disadvantaged`, `Female`, `Hispanic`, `Limited English Proficient`, `Male`, `Migrant`, `Native Hawaiian or Other Pacific Islander`, `Non-Migrant`, `Not Economically Disadvantaged`, `Not Limited English Proficient`, `Students with Disabilities`, `Students without Disabilities`, `Two or More Races`, `White`
- 2021 (20 values): adds `Active Duty` and `Homeless`
- 2022–2024 (21 values): renames `Active Duty` → `Military Connected` and adds `Foster Care`; retains `Homeless`. Final set: the 18 core + `Foster Care`, `Homeless`, `Military Connected`

Note: unlike the sibling rollup topic, this `_by_grade` topic's 2019 file does **not** contain `Active Duty`/`Foster`/`Homeless` — the 2019 `_by_grade` file is still the 18-subgroup set. Those additions first appear in 2021.

**Content area evolution (TEST_CMPNT_TYP_NM)**:
- 2015–2021 (4 subjects): `English Language Arts`, `Mathematics`, `Science`, `Social Studies`
- 2022–2024 (5 subjects): adds `Physical Science` (an 8th-grade accelerated option for middle-school students who take the high-school Physical Science course in 8th grade)

**Academic-level format (ACDMC_LVL)**:
- 2015 and 2019 — bare single-digit strings: `"3"`, `"4"`, `"5"`, `"6"`, `"7"`, `"8"`
- 2016, 2017, 2018, 2021, 2022, 2023, 2024 — zero-padded two-char strings: `"03"`, `"04"`, `"05"`, `"06"`, `"07"`, `"08"`

#### Suppression Markers

Per-column breakdown from the 2023 representative file:

| Column | Non-Numeric Values | Count (2023) | Notes |
|--------|-------------------|-------------:|-------|
| SCHOOL_DISTRCT_CD | `ALL` | 348 | Marks state-level rows; not a suppression marker |
| INSTN_NUMBER | `ALL` | 40,238 | Marks state- and district-level rows; not a suppression marker |
| NUM_TESTED_CNT | `TFS` | 357 | Fully-suppressed cell (below threshold) |
| BEGIN_CNT | `TFS` | 63,119 | Suppressed cell count |
| DEVELOPING_CNT | `TFS` | 48,759 | |
| PROFICIENT_CNT | `TFS` | 69,546 | |
| DISTINGUISHED_CNT | `TFS` | 134,133 | Highest suppression rate — very few schools have students at distinguished level in every demographic x grade x subject cell |
| BEGIN_PCT | `TFS` | 357 | Rare — usually suppression is at the count level, not percentage |
| DEVELOPING_PCT | `TFS` | 357 | |
| PROFICIENT_PCT | `TFS` | 357 | |
| DISTINGUISHED_PCT | `TFS` | 357 | |

Treat `"TFS"` = "Too Few Students" (standard GOSA suppression marker). Cast with `strict=False` to convert to null.

---

### Era 2: 2024 (tidy format, 18 columns — adds `#ASSMT_CD` constant)

File: `georgia_milestones_end_of_grade_eog_assessment_by_grade_2024.csv` (1 file).

Same row grain as Era 1, with 1 new column prepended:

| Column | Description |
|--------|-------------|
| #ASSMT_CD | Assessment code — always `"EOG_by_GRADE"`. The literal column name **starts with `#`** (read via `pl.read_csv` keeping the `#` prefix). Distinct from the sibling rollup file's `"EOG"` code — useful if you ever concatenate bronze sources. |
| LONG_SCHOOL_YEAR | `"2023-24"` |
| SCHOOL_DISTRCT_CD | District code — string; both 3- and 7-char codes (identical format to Era 1) |
| SCHOOL_DSTRCT_NM | District name |
| INSTN_NUMBER | School institution number — string; **always 4-char zero-padded** (e.g., `"0177"`) |
| INSTN_NAME | School name |
| ACDMC_LVL | Academic level / grade — `"03"` through `"08"` (zero-padded; same format as 2016–2018 and 2021–2023) |
| SUBGROUP_NAME | Demographic subgroup |
| TEST_CMPNT_TYP_NM | Content area |
| NUM_TESTED_CNT | Total students tested — string; `"TFS"` when suppressed (**suppression applies broadly here** — 30% of rows have `NUM_TESTED_CNT = "TFS"` in 2024, vs. <1% in Era 1) |
| BEGIN_CNT / DEVELOPING_CNT / PROFICIENT_CNT / DISTINGUISHED_CNT | Counts at each achievement level — string with `"TFS"` |
| BEGIN_PCT / DEVELOPING_PCT / PROFICIENT_PCT / DISTINGUISHED_PCT | Percentages at each level — 0–100 scale (**never suppressed in 2024** — always numeric, because when counts are `"TFS"` the percentages still report the rounded share) |

#### Sample Data (2024)

```
shape: (5, 18)
┌──────────────┬──────────────────┬───────────────────┬────────────────────┬──────────────┬──────────────────────────────────┬───────────┬───────────────────────────────┬───────────────────────┬────────────────┬───────────┬────────────────┬────────────────┬───────────────────┬───────────┬────────────────┬────────────────┬───────────────────┐
│ #ASSMT_CD    │ LONG_SCHOOL_YEAR │ SCHOOL_DISTRCT_CD │ SCHOOL_DSTRCT_NM   │ INSTN_NUMBER │ INSTN_NAME                       │ ACDMC_LVL │ SUBGROUP_NAME                 │ TEST_CMPNT_TYP_NM     │ NUM_TESTED_CNT │ BEGIN_CNT │ DEVELOPING_CNT │ PROFICIENT_CNT │ DISTINGUISHED_CNT │ BEGIN_PCT │ DEVELOPING_PCT │ PROFICIENT_PCT │ DISTINGUISHED_PCT │
╞══════════════╪══════════════════╪═══════════════════╪════════════════════╪══════════════╪══════════════════════════════════╪═══════════╪═══════════════════════════════╪═══════════════════════╪════════════════╪═══════════╪════════════════╪════════════════╪═══════════════════╪═══════════╪════════════════╪════════════════╪═══════════════════╡
│ EOG_by_GRADE │ 2023-24          │ 746               │ Walker County      │ 0106         │ Chattanooga Valley Middle School │ 08        │ Economically Disadvantaged    │ Mathematics           │ 118            │ 51        │ 48             │ 13             │ TFS               │ 43.2      │ 40.7           │ 11             │ 5.1               │
│ EOG_by_GRADE │ 2023-24          │ 647               │ Dougherty County   │ 0103         │ Robert A. Cross Middle Magnet    │ 06        │ Students without Disabilities │ Mathematics           │ 162            │ TFS       │ 41             │ 88             │ 33                │ 0         │ 25.3           │ 54.3           │ 20.4              │
│ EOG_by_GRADE │ 2023-24          │ 786               │ Social Circle City │ 0103         │ Social Circle Middle School      │ 08        │ Students without Disabilities │ Science               │ 137            │ 49        │ 47             │ 36             │ TFS               │ 35.8      │ 34.3           │ 26.3           │ 3.6               │
│ EOG_by_GRADE │ 2023-24          │ 710               │ Paulding County    │ 0304         │ Connie Dugan Elementary School   │ 05        │ Non-Migrant                   │ English Language Arts │ 124            │ 42        │ 37             │ 37             │ TFS               │ 33.9      │ 29.8           │ 29.8           │ 6.5               │
│ EOG_by_GRADE │ 2023-24          │ 738               │ Toombs County      │ 0204         │ Lyons Upper Elementary           │ 04        │ All Students                  │ English Language Arts │ 155            │ 51        │ 56             │ 31             │ 17                │ 32.9      │ 36.1           │ 20             │ 11                │
└──────────────┴──────────────────┴───────────────────┴────────────────────┴──────────────┴──────────────────────────────────┴───────────┴───────────────────────────────┴───────────────────────┴────────────────┴───────────┴────────────────┴────────────────┴───────────────────┴───────────┴────────────────┴────────────────┴───────────────────┘
```

#### Statistics (2024)

- **279,084 rows**, 18 columns
- 363 state-level rows, 55,780 district-level rows, 222,941 school-level rows
- 230 distinct districts (including the 7-digit State Charter / Commission / State-administered codes — 14,586 rows carry 7-char codes)
- 1,727 distinct school names (plus the sentinel `"ALL"`)
- 21 demographic subgroups (same set as 2022–2023)
- 5 content areas (English Language Arts, Mathematics, Physical Science, Science, Social Studies)
- 6 grade levels (`"03"`–`"08"`)
- **Detail-level breakdown**: 0.13% state, 20.0% district, 79.9% school
- **Suppression is pervasive**: **55% of rows have `BEGIN_CNT = "TFS"`** (152,435 / 279,084), **30% have `NUM_TESTED_CNT = "TFS"`** (85,104 / 279,084), **76% have `DISTINGUISHED_CNT = "TFS"`** (212,861 / 279,084). Percentage columns never carry `"TFS"` in 2024 (they always report the rounded distribution even when the underlying counts are suppressed)
- **Large year-over-year row jump (+45% vs 2023)** — mostly driven by the new 7-digit state-administered charter entities (14,586 rows vs. 8,882 in 2023) and by more grade x subject x subgroup cells now reported

#### Null Counts (2024)

All 18 columns have **0 nulls** (all suppression uses the `"TFS"` string, not CSV nulls).

#### Categorical Columns (2024)

| Column | Distinct Values |
|--------|----------------|
| #ASSMT_CD | `EOG_by_GRADE` (constant) |
| LONG_SCHOOL_YEAR | `2023-24` |
| ACDMC_LVL | `03`, `04`, `05`, `06`, `07`, `08` |
| SUBGROUP_NAME | 21 values — same set as 2022–2023 |
| TEST_CMPNT_TYP_NM | 5 values — same as 2022–2023 |
| SCHOOL_DSTRCT_NM | 230 distinct |
| INSTN_NAME | 1,727 distinct (plus `"ALL"` sentinel) |

#### Suppression Markers (2024)

| Column | Non-Numeric Values | Count (2024) |
|--------|-------------------|-------------:|
| SCHOOL_DISTRCT_CD | `ALL` | 363 (state-level rows) |
| INSTN_NUMBER | `ALL` | 56,143 (district + state rows) |
| NUM_TESTED_CNT | `TFS` | 85,104 |
| BEGIN_CNT | `TFS` | 152,435 |
| DEVELOPING_CNT | `TFS` | 137,105 |
| PROFICIENT_CNT | `TFS` | 152,825 |
| DISTINGUISHED_CNT | `TFS` | 212,861 |
| BEGIN_PCT / DEVELOPING_PCT / PROFICIENT_PCT / DISTINGUISHED_PCT | (none — 0 `"TFS"`) | 0 |

---

## ETL Considerations

1. **Two-era schema** — Era 2 (2024) prepends `#ASSMT_CD` but otherwise shares column names with Era 1. The new column is a constant (`"EOG_by_GRADE"`) and can be dropped from gold. A single per-era read-function approach works well: Era 1 reads the 17 columns directly; Era 2 strips the 1 extra constant. Note: unlike the sibling rollup topic (which adds BOTH `#ASSMT_CD` and a constant `ACDMC_LVL` column in Era 2), this `_by_grade` topic already has `ACDMC_LVL` (with real grade values) in every era — only `#ASSMT_CD` is a new Era 2 addition.

2. **`#ASSMT_CD` column with `#` prefix (Era 2)** — The column name literally starts with `#`. Polars `pl.read_csv` reads this fine, but reference it as the literal string `"#ASSMT_CD"`. Always `"EOG_by_GRADE"`; drop from gold.

3. **`ACDMC_LVL` column (every era)** — This is the grade-level column that distinguishes this topic from the rollup sibling. It must be **kept** as a fact categorical (gold name `grade_level` or similar). Values are `"3"`–`"8"` in 2015 and 2019 but `"03"`–`"08"` in 2016–2018 and 2021–2024. **Normalize to integers 3–8** (or zero-padded strings `"03"`–`"08"`) during transform so grade-level filtering is consistent across years.

4. **Column-name typo `SCHOOL_DISTRCT_CD`** — Both eras use the typo spelling `DISTRCT` (missing `I`). Preserve the typo literally when reading bronze. The companion column `SCHOOL_DSTRCT_NM` uses a different abbreviation — they are NOT consistent with each other.

5. **ID column formatting varies across eras**:
   - **`INSTN_NUMBER`**:
     - 2015 — mix of 3-char and 4-char — not zero-padded (e.g., `"101"`, `"4050"`)
     - 2016–2018 — always 4-char zero-padded
     - **2019 — back to mix of 3-char and 4-char** — inconsistent again
     - 2021–2024 — always 4-char zero-padded (e.g., `"0177"`)
     - Standardize to 4-char with `.str.zfill(4)` per the education domain convention (FK to schools dimension). School codes are NOT globally unique — PK in the schools dimension is `(school_code, district_code)`.
   - **`SCHOOL_DISTRCT_CD`**:
     - All eras — 3-char standard codes (e.g., `"601"`) or 7-char state-administered codes (e.g., `"7820120"`, `"7991893"`); the sentinel `"ALL"` marks state-level rows.
     - Pad with `.str.zfill(3)` per education domain — **never truncate** the 7-char codes.

6. **Detail-level detection via `"ALL"` sentinels**:
   - State-level: `SCHOOL_DISTRCT_CD == "ALL"` AND `INSTN_NUMBER == "ALL"`
   - District-level: `SCHOOL_DISTRCT_CD != "ALL"` AND `INSTN_NUMBER == "ALL"`
   - School-level: both are non-`"ALL"` values
   - No `(SCHOOL_DISTRCT_CD == "ALL", INSTN_NUMBER != "ALL")` rows observed.
   After detail-level classification, NULL-out the geography keys per the education star-schema rule (state rows null both keys; district rows null `school_code`).

7. **State-level row marker**: When `SCHOOL_DISTRCT_CD == "ALL"`, the `SCHOOL_DSTRCT_NM` is also `"ALL"`. Similarly, district-level rows have `INSTN_NAME == "ALL"`. Treat these literal `"ALL"` strings as sentinels to replace with null in gold.

8. **7-digit state-administered districts** — Codes like `7820120` (State Charter Schools – Georgia Cyber Academy), `7820212` (State Charter Schools – Cherokee Charter Academy), `7820412` (State Charter Schools – Georgia Connections Academy), `7830110` (Commission Charter Schools – Ivy Preparatory Academy), `7830210` (Commission Charter Schools – Pataula Charter Academy), `7830610` (Commission Charter Schools – Coweta Charter Academy), `7991893` (State Schools – Atlanta Area School for the Deaf), `7991894` (State Schools – Georgia Academy for the Blind), `7991895` (State Schools – Georgia School for the Deaf) are real entities and must be preserved. They typically have null census IDs in the districts dimension. The 7-char row count grows from 5,078 in 2015 to 14,586 in 2024 as more state-administered entities participate.

9. **Two suppression mechanisms — `"TFS"` string AND genuine CSV nulls**:
   - 2015 uses BOTH — `"TFS"` for most suppressed cells (83,830 in BEGIN_CNT, 207,760 in DISTINGUISHED_CNT), plus 521 genuine null rows (true empty CSV fields) where `NUM_TESTED_CNT` is also `"TFS"`.
   - **2016, 2017, 2018 use ONLY genuine CSV nulls** (520, 383, 403 null rows respectively) — NO `"TFS"` string anywhere in these files.
   - 2019 uses BOTH — 73,445 `"TFS"` in BEGIN_CNT plus 437 genuine nulls.
   - 2021, 2022, 2023 use ONLY `"TFS"` string in count columns; BEGIN_PCT etc. also carry `"TFS"` when the cell's `NUM_TESTED_CNT` is itself `"TFS"`.
   - 2024 uses ONLY `"TFS"` string in count columns; percentages never carry `"TFS"`.
   - Casting all metric columns with `.cast(pl.Float64, strict=False)` converts both empty strings and `"TFS"` to null — this is the only safe read strategy.

10. **Demographic subgroup evolution** — Different from the rollup sibling in one important way:
    - 2015–2019 — 18 subgroups (no `Active Duty`/`Foster`/`Homeless` yet; this differs from the rollup where those first appeared in 2019)
    - 2021 — 20 subgroups (adds `Active Duty` and `Homeless`; never adds `Foster` as a standalone label here)
    - 2022+ — 21 subgroups (`Active Duty` → `Military Connected` rename; `Foster Care` added). Final set: 18 core + `Foster Care`, `Homeless`, `Military Connected`
    Per the `data-cleaning-standards` skill, route `SUBGROUP_NAME` through `normalize_demographic_column()` from `src/utils/demographics.py`. If any of these raw labels aren't in `DEMOGRAPHIC_ALIASES`, add them (map `Active Duty`/`Military Connected` → same canonical; `Foster Care` → same canonical) rather than silently emitting `"99999999"` (unmapped).

11. **Content area change 2022** — `Physical Science` is new in 2022 and persists through 2024. This is a real 8th-grade accelerated-testing addition (middle-school students taking the high-school Physical Science course sit the EOG version of the assessment), not a rename. Preserve `Physical Science` as its own `test_component` value; do not merge with `Science`. The four legacy subjects (`English Language Arts`, `Mathematics`, `Science`, `Social Studies`) keep identical labels across all 9 files.

12. **Grade x subject availability changes mid-era** — Starting in 2017, Science and Social Studies are only administered at grades 5 and 8 (plus rare single-digit audit rows at other grades). Starting in 2021, Social Studies is only grade 8. Physical Science (2022+) is only grade 8. **The transform must preserve the natural sparsity** — do not fabricate zero-row cells for grade x subject combinations that weren't tested. Document this in gold metadata so users understand the gaps.

13. **`ACDMC_LVL` format normalization** — Mix of bare-digit (`"3"`) and zero-padded (`"03"`) strings across years. Cast to `Int32` with values 3–8 (drops the padding ambiguity) OR normalize to two-char zero-padded string `"03"`–`"08"` consistently. Integer is simpler — grade level is a naturally ordered numeric.

14. **Count-metric scaling** — All count columns (`NUM_TESTED_CNT`, `BEGIN_CNT`, `DEVELOPING_CNT`, `PROFICIENT_CNT`, `DISTINGUISHED_CNT`) are raw integer counts. Cast to Int32 or Int64 after converting `"TFS"` / empty to null.

15. **Percentage scaling** — All `*_PCT` columns are 0–100 (e.g., `34.1` means 34.1%). Per `data-cleaning-standards`, divide by 100 at gold time so metrics land on the 0–1 scale (gold convention). Validate that `BEGIN_PCT + DEVELOPING_PCT + PROFICIENT_PCT + DISTINGUISHED_PCT ≈ 100` in bronze (should always round to 100; 99.9 mean across 2023 non-suppressed rows, with a small rounding slack).

16. **Percentages present even when counts are suppressed (Era 2 / 2024)** — When all 4 count columns are `"TFS"`, the 4 percentage columns still contain real numbers on a 0–100 scale (e.g., `0, 0, 0, 20`). This means in 2024 the percentages are usable even when individual counts are suppressed. In 2015–2023 the percentages are typically also `"TFS"` or null when counts are suppressed (with a minority of 2021–2023 rows carrying `"TFS"` percentages only — 357 rows in 2023). Don't inadvertently treat the 2024 percentages as artifacts of division-by-zero. **Caveat (verified 2026-06-11)**: on `Foster Care` rows the published percentages cover only the unsuppressed levels — including an all-four-zeros placeholder pattern on fully-suppressed cells (157 rows in 2022, 173 in 2023, 4,106 in 2024; in 2024 most of these also have `NUM_TESTED_CNT = "TFS"`). Those all-zero percentages are placeholders, not real shares. All such rows are `Foster Care`; no other subgroup is affected. See consideration 23.

17. **Year representation** — `LONG_SCHOOL_YEAR` uses `"YYYY-YY"` format. Parse via `.str.split("-").list.get(0).cast(pl.Int32) + 1` (ending-calendar-year convention from `src/etl/education/CLAUDE.md`). The filename year always equals the ending calendar year; use it as a sanity-check.

18. **Missing 2020 file** — No file for school year 2019-20. This is expected (EOG testing cancelled during initial COVID-19 closures). Do **not** attempt to interpolate or infer values; simply skip that year. `validate.py` should not error on the gap.

19. **Quoting changes mid-era** — 2015 and 2019 files are unquoted; 2016–2018 and 2021–2024 files quote every field. Polars `pl.read_csv` handles both transparently. No action needed.

20. **Row-grain PK** — The natural PK for a gold fact row is `(year, district_code, school_code, grade_level, demographic, test_component)`, with NULLs in `district_code`/`school_code` per detail level. Verify uniqueness when deduplicating (use `deduplicate_by_detail_level()` from `src/utils/transformers.py` if available). **Note the added `grade_level` field vs. the rollup sibling's PK** — this is the key grain difference.

21. **Disambiguation vs sibling topics** — This topic (`georgia_milestones_end_of_grade_eog_assessment_by_grade`) reports per-grade results. The rollup companion (`georgia_milestones_end_of_grade_eog_assessment`) reports all-grades-combined results with `ACDMC_LVL = "ALL GRADES"`. Do **NOT** merge the two sources in gold — they are different grains (grades 3–8 individually vs. a single rollup row per entity x subgroup x subject). Row counts per year are roughly 2–3x the rollup topic because each rollup row corresponds to ~2–6 grade-specific rows (plus some grades where the subject isn't tested). Lexile scores live in a separate third topic, `georgia_milestones_end_of_grade_eog_lexile_scores`.

22. **Audit/retest rows outside main grade x subject cells** — A small number of rows (3–13 in most years, up to ~500 per outlier cell in 2024) exist at grade x subject combinations outside the primary administration pattern (e.g., 3 Science rows at grade 4 in 2017; 515 Science rows at grade 3 in 2024). These are real records of students taking the test outside their primary grade (e.g., accelerated students, retests). Retain them — they're valid rows with suppressed or low counts.

23. **Foster Care reporting anomalies (2022–2024) — added 2026-06-11 from transform-time verification.** `Foster Care` (new in 2022) is the only subgroup whose rows violate the otherwise-universal cross-column invariants:
    - **Percentage-sum deviations are exclusively Foster Care.** Rows where all four `*_PCT` values are non-suppressed but sum to less than ~100: 206 (2022), 282 (2023), 4,738 (2024); zero in 2015–2021. Every one is a `Foster Care` row (verified by grouping deviators by `SUBGROUP_NAME` per file). Sub-patterns: (a) all-four-zeros placeholders on fully-suppressed cells (157 / 173 / 4,106 rows); (b) partial sums (e.g., `8.3, 0, 0, 0` with `NUM_TESTED_CNT = 12`) where percentages cover only unsuppressed levels.
    - **Level-count shortfall on fully-unsuppressed state rows.** 28 state-level Foster Care rows (7 in 2022, 11 in 2023, 10 in 2024) have `BEGIN_CNT + DEVELOPING_CNT + PROFICIENT_CNT + DISTINGUISHED_CNT < NUM_TESTED_CNT` (e.g., 2022 grade 03 Mathematics: 602 tested vs level sum 594) — students tested but not assigned a performance level at publication time. The shortfall is one-directional: the level sum **never exceeds** `NUM_TESTED_CNT` anywhere in any year, and no individual level count exceeds `NUM_TESTED_CNT`. All district- and school-level fully-unsuppressed rows reconcile exactly in every year.
    - **Percentages remain shares of `NUM_TESTED_CNT`**: max |`*_PCT`/100 − `*_CNT`/`NUM_TESTED_CNT`| = 0.0005 across all years wherever all parts are non-null, including the shortfall rows.
    Preserve these published values as-is; scope any percentage-partition validation to exclude `Foster Care`.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| #ASSMT_CD (Era 2 only) | not_in_gold | — | Constant `"EOG_by_GRADE"`; drop |
| LONG_SCHOOL_YEAR | fact_key | year | Int32; parse `"YYYY-YY"` → ending calendar year |
| SCHOOL_DISTRCT_CD | fact_key | district_code | Utf8; `.str.zfill(3)` to pad 3-digit standard codes; preserve 7-digit state-administered codes as-is; `"ALL"` → NULL (state-level) |
| SCHOOL_DSTRCT_NM | dimension_attribute | — | `district_name` in the districts dimension |
| INSTN_NUMBER | fact_key | school_code | Utf8; `.str.zfill(4)`; `"ALL"` → NULL (district- or state-level) |
| INSTN_NAME | dimension_attribute | — | `school_name` in the schools dimension |
| ACDMC_LVL | fact_categorical | grade_level | Int32 (3–8) — **the grain-distinguishing column vs. the rollup sibling**; normalize `"3"`/`"03"` format variation to a plain integer |
| SUBGROUP_NAME | fact_key | demographic | Normalize via `normalize_demographic_column()`; FK to global demographics dimension. Add `Active Duty`/`Military Connected`/`Foster Care` aliases to `DEMOGRAPHIC_ALIASES` if not already present |
| TEST_CMPNT_TYP_NM | fact_categorical | test_component | Keep bronze values verbatim: `English Language Arts`, `Mathematics`, `Physical Science`, `Science`, `Social Studies` |
| NUM_TESTED_CNT | fact_metric | num_tested | Int; cast `strict=False` to handle `"TFS"` and empty strings |
| BEGIN_CNT | fact_metric | beginning_count | Int |
| DEVELOPING_CNT | fact_metric | developing_count | Int |
| PROFICIENT_CNT | fact_metric | proficient_count | Int |
| DISTINGUISHED_CNT | fact_metric | distinguished_count | Int |
| BEGIN_PCT | fact_metric | beginning_pct | Float; **divide by 100** per `data-cleaning-standards` (0–1 scale in gold) |
| DEVELOPING_PCT | fact_metric | developing_pct | Float; divide by 100 |
| PROFICIENT_PCT | fact_metric | proficient_pct | Float; divide by 100 |
| DISTINGUISHED_PCT | fact_metric | distinguished_pct | Float; divide by 100 |

**Detail-level split**: After classification, split the fact table into `schools.parquet`, `districts.parquet`, and `states.parquet` per-year partitions (per the education domain output format). Approximate scale per year: state-level rows are 292–432 per year (except 2024 at 363); district-level rows are ~36,000–55,800 per year; school-level rows are the bulk (~134,000–234,000 per year, with the big 2024 jump reflecting more schools, subgroups, and 7-char-code state-administered entities).

**Column order in each fact file** (per `data-cleaning-standards`): `year`, `district_code` (NULL for states), `school_code` (NULL for states and districts), `grade_level`, `demographic`, `test_component`, then metric columns in this order: `num_tested`, `beginning_count`, `developing_count`, `proficient_count`, `distinguished_count`, `beginning_pct`, `developing_pct`, `proficient_pct`, `distinguished_pct`.
