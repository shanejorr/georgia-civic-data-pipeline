# certified_personnel — Bronze Data Structure

## Overview

- Topic: certified_personnel
- Source: gosa
- Files: 14 CSV files spanning 2011–2024
- Unreadable files: none
- Year representation: `LONG_SCHOOL_YEAR` column in format `YYYY-YY` (e.g., `2023-24`); school year spanning two calendar years
- Filename-to-data year offset: filename year = ending year of school year (e.g., file `2024` → data year `2023-24`)
- Detail levels: state, district, school
- Percentage scale: N/A — no percentage columns; `MEASURE` contains headcounts, averages (salary, contract days, experience)
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| certified_personnel_2011.csv | 08750e6f0709ef7a81b533ba930417b38ebd5721d7e102f6ab6b6eb590760ca6 |
| certified_personnel_2012.csv | bab59fc04a6d69e53177e12d903d6d61c0315238060f31c2436a91e5e527097a |
| certified_personnel_2013.csv | 3443a0379060d17a6e8a9f5c28c07c1cd5eed3e972b432e999908d00777017b2 |
| certified_personnel_2014.csv | 490e03a82f01b947f7b6038734cc6267ce581d3d83c07ab97f8fcb58f22e1eec |
| certified_personnel_2015.csv | 7415d9029917bef4b64613932c29b836ce28f0f05469cad080470e6f5b1aec83 |
| certified_personnel_2016.csv | d22873d87e77ac2c61b72be46dfaf68cfd518dd036da7ef6f1a0b16fb792b094 |
| certified_personnel_2017.csv | dc848721042d6e37403fbe24da4adb432ec1171d8a1a391a37ce2ea02993e6e0 |
| certified_personnel_2018.csv | 0fffb03e697432280196fe49586d604b1a4be961ee866d16f93d830a059bf4e0 |
| certified_personnel_2019.csv | 53f42f4cb39b2852f2e7ecb3e23d578e26264145396bb8883c012f788d98cd06 |
| certified_personnel_2020.csv | 0d47d9fd0c1156d775f64ee87ba84f8c6dea602d485e5f4479e0d06397013347 |
| certified_personnel_2021.csv | fce67d620dffdbe9ba14a5c4aa1fdf4e42a839fff5620e6073efdf5bb2959f34 |
| certified_personnel_2022.csv | 74ae1c30cb900ae71a4183ad8d0a71fe63277dbb9b9252c6bc0b00af8a9a28a7 |
| certified_personnel_2023.csv | 810fce431d719265c083484e496a389327924fa1e400de7d3b3a6d1aa2050206 |
| certified_personnel_2024.csv | 59d367981bc927aebbf1c869d9cf228d2ad9c8a6f66a59c1236e32309dc6996c |

## Summary

Certified personnel data captures staffing metrics for Georgia public schools by employee type (Administrators, PK-12 Teachers, Support Personnel). The dataset is structured in a long/tidy key-value format: `DATA_CATEGORY` + `DATA_SUB_CATEGORY` define what is being measured, and the `MEASURE` column holds the numeric value. The measure families include:

- **Certificate Level** distribution (4 Yr Bachelor's, 5 Yr Master's, 6 Yr Specialist's, 7 Yr Doctoral, Other)
- **Certified Personnel** status (Professional, Provisional)
- **Gender** breakdown (Male, Female)
- **Personnel** employment status (Full-time, Part-time)
- **Positions** metrics (Number/headcount, Average Annual Salary, Average Daily Salary, Average Contract Days)
- **Race/Ethnicity** breakdown (Asian, Black, Hispanic, Multiracial, Native American, White)
- **Years Experience** distribution (<1, 1-10, 11-20, 21-30, >30, Average)

Each measure is reported per employee type per geographic level (state, district, school).

## Eras

### Era 1: 2023–2024

**Columns**: `#RPT_NAME`, `LONG_SCHOOL_YEAR`, `SCHOOL_DSTRCT_CD`, `SCHOOL_DSTRCT_NM`, `INSTN_NUMBER`, `INSTN_NAME`, `GRADES_SERVED_DESC`, `DATA_CATEGORY`, `DATA_SUB_CATEGORY`, `EMPLOYEE_TYPE`, `MEASURE`

| Column | Description |
|--------|-------------|
| #RPT_NAME | Report name identifier; constant value `CERTIFIED_PERSONNEL` |
| LONG_SCHOOL_YEAR | School year in format `YYYY-YY` (e.g., `2023-24`) |
| SCHOOL_DSTRCT_CD | District code as string — 3-digit standard or 7-digit charter (charters appear 2012+); literal `ALL` marks state-level aggregate rows |
| SCHOOL_DSTRCT_NM | District name; `All Column Values` for state-level rows |
| INSTN_NUMBER | 4-character zero-padded institution/school number as string (uniform; only the `ALL` sentinel, marking district-level aggregate rows, is 3-char) |
| INSTN_NAME | School/institution name; `All Column Values` for district-level aggregate rows |
| GRADES_SERVED_DESC | Comma-delimited list of grades served by the school (e.g., `KK,01,02,03,04,05`); null for district aggregates and some non-instructional facilities (central offices, nutrition facilities, career academies) |
| DATA_CATEGORY | Measure family (`Certificate Level`, `Certified Personnel`, `Gender`, `Personnel`, `Positions`, `Race/Ethnicity`, `Years Experience`) |
| DATA_SUB_CATEGORY | Specific measure label within the family (e.g., `Female`, `5 Yr Master's`, `Average Annual Salary`) |
| EMPLOYEE_TYPE | Employee group (`Administrators`, `PK-12 Teachers`, `Support Personnel`) |
| MEASURE | Numeric metric value (headcount, count, average salary, average contract days, average years of experience) |

#### Sample Data

Sample of 5 rows from `certified_personnel_2024.csv`:

```
| #RPT_NAME           | LONG_SCHOOL_YEAR | SCHOOL_DSTRCT_CD | SCHOOL_DSTRCT_NM | INSTN_NUMBER | INSTN_NAME                      | GRADES_SERVED_DESC                        | DATA_CATEGORY     | DATA_SUB_CATEGORY | EMPLOYEE_TYPE     | MEASURE |
|---------------------|------------------|------------------|------------------|--------------|---------------------------------|-------------------------------------------|-------------------|-------------------|-------------------|---------|
| CERTIFIED_PERSONNEL | 2023-24          | 741              | Troup County     | 0189         | Long Cane Elementary School     | PK,KK,01,02,03,04,05                      | Certificate Level | 5 Yr Master's     | Support Personnel | 3       |
| CERTIFIED_PERSONNEL | 2023-24          | 644              | DeKalb County    | 5067         | Southwest DeKalb High School    | 09,10,11,12                               | Years Experience  | < 1               | Administrators    | 0       |
| CERTIFIED_PERSONNEL | 2023-24          | 785              | Rome City        | 0275         | East Central Elementary School  | PK,KK,01,02,03,04,05,06                   | Gender            | Male              | Administrators    | 0       |
| CERTIFIED_PERSONNEL | 2023-24          | 708              | Oconee County    | 1050         | Oconee County Elementary School | 03,04,05                                  | Positions         | Number            | Administrators    | 2       |
| CERTIFIED_PERSONNEL | 2023-24          | 732              | Tattnall County  | ALL          | All Column Values               | PK,KK,01,02,03,04,05,06,07,08,09,10,11,12 | Certificate Level | 7 Yr Doctoral     | Support Personnel | 4       |
```

#### Statistics

Describe of `certified_personnel_2024.csv` (shape 229,797 × 11). All columns parsed as strings; `MEASURE` cast to float has min `0.0`, max `249,599.0`, mean `3,058.15`.

```
| statistic  | #RPT_NAME           | LONG_SCHOOL_YEAR | SCHOOL_DSTRCT_CD | SCHOOL_DSTRCT_NM  | INSTN_NUMBER | INSTN_NAME               | GRADES_SERVED_DESC                     | DATA_CATEGORY     | DATA_SUB_CATEGORY | EMPLOYEE_TYPE     | MEASURE |
|------------|---------------------|------------------|------------------|-------------------|--------------|--------------------------|----------------------------------------|-------------------|-------------------|-------------------|---------|
| count      | 229797              | 229797           | 229797           | 229797            | 229797       | 229797                   | 203796                                 | 229797            | 229797            | 229797            | 229797  |
| null_count | 0                   | 0                | 0                | 0                 | 0            | 0                        | 26001                                  | 0                 | 0                 | 0                 | 0       |
| min        | CERTIFIED_PERSONNEL | 2023-24          | 601              | All Column Values | 0100         | 7 Pillars Career Academy | 01,02                                  | Certificate Level | 1-10              | Administrators    | .01     |
| max        | CERTIFIED_PERSONNEL | 2023-24          | ALL              | Worth County      | ALL          | z_Alpha Academy          | PK,KK,01,03,04,05,06,07,08,09,10,11,12 | Years Experience  | White             | Support Personnel | 99985.5 |
```

#### Null Counts

Only `GRADES_SERVED_DESC` has nulls (26,001 of 229,797 rows ≈ 11.3%); all other columns are non-null.

| Column | Null Count |
|--------|-----------:|
| #RPT_NAME | 0 |
| LONG_SCHOOL_YEAR | 0 |
| SCHOOL_DSTRCT_CD | 0 |
| SCHOOL_DSTRCT_NM | 0 |
| INSTN_NUMBER | 0 |
| INSTN_NAME | 0 |
| GRADES_SERVED_DESC | 26001 |
| DATA_CATEGORY | 0 |
| DATA_SUB_CATEGORY | 0 |
| EMPLOYEE_TYPE | 0 |
| MEASURE | 0 |

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| #RPT_NAME | `CERTIFIED_PERSONNEL` (229,797 rows, constant) |
| LONG_SCHOOL_YEAR | `2023-24` (2024 file) or `2022-23` (2023 file) — single value per file |
| DATA_CATEGORY (7 values) | `Certificate Level` (42,555), `Certified Personnel` (17,022), `Gender` (17,022), `Personnel` (17,022), `Positions` (34,044), `Race/Ethnicity` (51,066), `Years Experience` (51,066) |
| DATA_SUB_CATEGORY (27 values) | `1-10` (8,511), `11-20` (8,511), `21-30` (8,511), `4 Yr Bachelor's` (8,511), `5 Yr Master's` (8,511), `6 Yr Specialist's` (8,511), `7 Yr Doctoral` (8,511), `< 1` (8,511), `> 30` (8,511), `Asian` (8,511), `Average` (8,511), `Average Annual Salary` (8,511), `Average Contract Days` (8,511), `Average Daily Salary` (8,511), `Black` (8,511), `Female` (8,511), `Full-time` (8,511), `Hispanic` (8,511), `Male` (8,511), `Multiracial` (8,511), `Native American` (8,511), `Number` (8,511), `Other *` (8,511), `Part-time` (8,511), `Professional` (8,511), `Provisional` (8,511), `White` (8,511) |
| EMPLOYEE_TYPE | `Administrators` (78,489), `PK-12 Teachers` (73,359), `Support Personnel` (77,949) |
| SCHOOL_DSTRCT_NM | 232 distinct values (231 districts + `All Column Values` for state-level rows) |
| INSTN_NAME | 2,404 distinct values (includes `All Column Values` for district aggregates) |
| GRADES_SERVED_DESC | 77 distinct comma-delimited grade combinations (e.g., `PK,KK,01,02,03,04,05`, `09,10,11,12`, `KK,01,02,03,04,05,06,07,08,09,10,11,12`); null for 26,001 rows (non-instructional facilities like central offices, nutrition facilities, transitional/gateway academies) |

**`DATA_CATEGORY` × `DATA_SUB_CATEGORY` combinations (27 pairs, each 8,511 rows):**

| DATA_CATEGORY | DATA_SUB_CATEGORY values |
|---------------|--------------------------|
| Certificate Level | `4 Yr Bachelor's`, `5 Yr Master's`, `6 Yr Specialist's`, `7 Yr Doctoral`, `Other *` |
| Certified Personnel | `Professional`, `Provisional` |
| Gender | `Female`, `Male` |
| Personnel | `Full-time`, `Part-time` |
| Positions | `Number`, `Average Annual Salary`, `Average Daily Salary`, `Average Contract Days` |
| Race/Ethnicity | `Asian`, `Black`, `Hispanic`, `Multiracial`, `Native American`, `White` |
| Years Experience | `< 1`, `1-10`, `11-20`, `21-30`, `> 30`, `Average` |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| SCHOOL_DSTRCT_CD | `ALL` (marks state-level aggregate rows — not a suppression marker) |
| INSTN_NUMBER | `ALL` (marks district-level aggregate rows — not a suppression marker) |
| MEASURE | (none observed in 2024 — all 229,797 rows parse to valid numbers; no `*`, `TFS`, or `N/A` markers) |

Note: GOSA does not appear to suppress small-cell counts in this dataset; zero counts are reported as `0` rather than suppressed.

---

### Era 2: 2011–2022

**Columns**: `LONG_SCHOOL_YEAR`, `SCHOOL_DSTRCT_CD`, `SCHOOL_DSTRCT_NM`, `INSTN_NUMBER`, `INSTN_NAME`, `DATA_CATEGORY`, `DATA_SUB_CATEGORY`, `EMPLOYEE_TYPE`, `MEASURE`

Era 2 differs from Era 1 only by the **absence** of `#RPT_NAME` and `GRADES_SERVED_DESC`. All other columns have identical names, semantics, and value domains.

| Column | Description |
|--------|-------------|
| LONG_SCHOOL_YEAR | School year in format `YYYY-YY` (e.g., `2021-22`) |
| SCHOOL_DSTRCT_CD | District code as string — 3-digit standard or 7-digit charter (charters appear 2012+); literal `ALL` marks state-level aggregate rows |
| SCHOOL_DSTRCT_NM | District name; `All Column Values` for state-level rows |
| INSTN_NUMBER | 4-character zero-padded institution/school number as string (uniform; only the `ALL` sentinel, marking district-level aggregate rows, is 3-char) |
| INSTN_NAME | School/institution name; `All Column Values` for district-level aggregate rows |
| DATA_CATEGORY | Measure family (same 7 categories as Era 1) |
| DATA_SUB_CATEGORY | Specific measure label (same 27 labels as Era 1) |
| EMPLOYEE_TYPE | Employee group (same 3 values as Era 1) |
| MEASURE | Numeric metric value |

#### Sample Data

Sample of 5 rows from `certified_personnel_2022.csv`:

```
| LONG_SCHOOL_YEAR | SCHOOL_DSTRCT_CD | SCHOOL_DSTRCT_NM | INSTN_NUMBER | INSTN_NAME                      | DATA_CATEGORY     | DATA_SUB_CATEGORY | EMPLOYEE_TYPE  | MEASURE |
|------------------|------------------|------------------|--------------|---------------------------------|-------------------|-------------------|----------------|---------|
| 2021-22          | 737              | Tift County      | 8014         | Other Auxillary Facility        | Race/Ethnicity    | Black             | Administrators | 0       |
| 2021-22          | 644              | DeKalb County    | 5058         | Huntley Hills Elementary School | Certificate Level | Other *           | Administrators | 0       |
| 2021-22          | 785              | Rome City        | 0275         | East Central Elementary School  | Years Experience  | > 30              | PK-12 Teachers | 0       |
| 2021-22          | 707              | Newton County    | 5050         | Porterdale Elementary School    | Certificate Level | 7 Yr Doctoral     | PK-12 Teachers | 0       |
| 2021-22          | 729              | Sumter County    | 0100         | Sumter County Primary School    | Years Experience  | < 1               | PK-12 Teachers | 0       |
```

#### Statistics

Describe of `certified_personnel_2022.csv` (shape 226,638 × 9). `MEASURE` cast to float has min `0`, max `99,996`.

```
| statistic  | LONG_SCHOOL_YEAR | SCHOOL_DSTRCT_CD | SCHOOL_DSTRCT_NM  | INSTN_NUMBER | INSTN_NAME               | DATA_CATEGORY     | DATA_SUB_CATEGORY | EMPLOYEE_TYPE     | MEASURE |
|------------|------------------|------------------|-------------------|--------------|--------------------------|-------------------|-------------------|-------------------|---------|
| count      | 226638           | 226638           | 226638            | 226638       | 226638                   | 226638            | 226638            | 226638            | 226638  |
| null_count | 0                | 0                | 0                 | 0            | 0                        | 0                 | 0                 | 0                 | 0       |
| min        | 2021-22          | 601              | All Column Values | 0100         | 7 Pillars Career Academy | Certificate Level | 1-10              | Administrators    | 0       |
| max        | 2021-22          | ALL              | Worth County      | ALL          | z_Alpha Academy          | Years Experience  | White             | Support Personnel | 99996   |
```

Row counts per file (Era 2):

| File | LONG_SCHOOL_YEAR | Rows |
|------|------------------|-----:|
| certified_personnel_2011.csv | 2010-11 | 220,347 |
| certified_personnel_2012.csv | 2011-12 | 220,725 |
| certified_personnel_2013.csv | 2012-13 | 217,566 |
| certified_personnel_2014.csv | 2013-14 | 218,160 |
| certified_personnel_2015.csv | 2014-15 | 220,833 |
| certified_personnel_2016.csv | 2015-16 | 221,130 |
| certified_personnel_2017.csv | 2016-17 | 222,021 |
| certified_personnel_2018.csv | 2017-18 | 222,966 |
| certified_personnel_2019.csv | 2018-19 | 223,425 |
| certified_personnel_2020.csv | 2019-20 | 224,127 |
| certified_personnel_2021.csv | 2020-21 | 225,315 |
| certified_personnel_2022.csv | 2021-22 | 226,638 |

#### Null Counts

All columns are fully populated (null count 0 for every column in every Era 2 file).

#### Categorical Columns

Same categorical domains as Era 1:

| Column | Distinct Values |
|--------|----------------|
| LONG_SCHOOL_YEAR | Single value per file (matches `YYYY-YY` matching filename minus 1 through filename) |
| DATA_CATEGORY (7 values) | `Certificate Level`, `Certified Personnel`, `Gender`, `Personnel`, `Positions`, `Race/Ethnicity`, `Years Experience` |
| DATA_SUB_CATEGORY (27 values) | Same 27 labels as Era 1 (Certificate Level, Gender, Personnel, Positions, Race/Ethnicity, Years Experience, Certified Personnel) |
| EMPLOYEE_TYPE | `Administrators`, `PK-12 Teachers`, `Support Personnel` |
| SCHOOL_DSTRCT_NM | ~222 distinct values (varies slightly by year as districts open/close) |
| INSTN_NAME | ~2,387 distinct values (varies by year) |

Note: counts of combinations (DATA_CATEGORY × DATA_SUB_CATEGORY) are the same 27 pairs as Era 1.

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| SCHOOL_DSTRCT_CD | `ALL` (state-level marker) |
| INSTN_NUMBER | `ALL` (district-level marker) |
| MEASURE | (none observed in any Era 2 file — all values parse to valid numbers) |

---

## ETL Considerations

- **Two near-identical eras**: Era 2 (2011–2022) lacks `#RPT_NAME` (constant, safe to drop anyway) and `GRADES_SERVED_DESC`. Era 1 (2023–2024) adds both. The transform can select the common 9-column schema and conditionally read the two extra columns — only `GRADES_SERVED_DESC` is semantically meaningful, but it's school-level metadata not a fact attribute; `#RPT_NAME` is constant and drops entirely.
- **Long/tidy value-key format**: The dataset is already in long form, keyed by (`DATA_CATEGORY`, `DATA_SUB_CATEGORY`, `EMPLOYEE_TYPE`). Gold representation can either keep the long shape (with `data_category`, `data_sub_category`, `employee_type`, `measure` columns) or pivot to a wider fact table where each (category, sub_category) pair becomes a metric column. The 27 combinations × 3 employee types = 81 potential metric columns — pivoting will produce very wide rows but may match downstream analytic needs better.
- **`ALL` sentinel, not null**: The source encodes state and district aggregates with the literal string `ALL` in `SCHOOL_DSTRCT_CD` / `INSTN_NUMBER`, paired with `All Column Values` in the name columns. The transform must translate these sentinels to the standard geography-key conventions (drop aggregate rows, or convert to explicit `total` geography markers per data-cleaning-standards). Every row has either school-level keys, district-level keys (INSTN_NUMBER=ALL), or state-level keys (both ALL) — no mixed/invalid combinations observed.
- **District code format**: `SCHOOL_DSTRCT_CD` is a 3-digit string (`601`–`795`) for standard districts, **plus 7-digit charter district codes from the 2012 file onward** (verified: distinct code lengths are {3} in 2011 and {3, 7} in 2012–2024). Keep as string to preserve leading zeros and avoid confusion with FIPS codes. These are Georgia DOE district codes, not county FIPS codes. *(Corrected 2026-06-11: previously claimed 3-digit only.)*
- **Institution number format**: `INSTN_NUMBER` is a **uniformly 4-character** zero-padded string (e.g., `0100`, `0189`, `5067`) in all 14 files — the only 3-character value is the `ALL` sentinel (re-verified 2026-06-11 excluding the sentinel: non-`ALL` code lengths are exactly {4} in every file). Must preserve as string — casting to int would lose the leading zeros and break joins to the schools dimension. A defensive `zfill(4)` is harmless but must be applied *after* the `ALL`→NULL sentinel translation, which would otherwise produce a bogus `0ALL`.
- **Mixed metric types in one column**: `MEASURE` carries heterogeneous units across rows — integer headcounts (e.g., Gender/Female = 4), currency averages (Positions/Average Annual Salary up to ~$250k), fractional averages (Years Experience/Average with `.01` precision), and integer counts up to ~249,599. Type casting must preserve float precision; do not down-cast to int.
- **`Other *` is a CERTIFICATE LEVEL label, not a race/ethnicity label**: the pair (`Certificate Level`, `Other *`) is the only occurrence of `Other *` in all 14 files (verified 2026-06-11; the Race/Ethnicity family carries exactly `Asian`, `Black`, `Hispanic`, `Multiracial`, `Native American`, `White`). It is the fifth certificate-type bucket alongside the Bachelor's/Master's/Specialist's/Doctoral levels; the trailing asterisk likely flags a footnote in the source documentation. Map to `other` within the certificate-level vocabulary. *(Corrected 2026-06-11: previously mis-described as a Race/Ethnicity category.)*
- **"Average" sub-category inside Years Experience**: The pair (`Years Experience`, `Average`) is a summary statistic (mean years of experience) rather than a band count. Handle carefully when aggregating — do not sum `Average` across districts to get a state average.
- **`GRADES_SERVED_DESC` is school metadata**: 77 distinct comma-delimited grade lists. Nulls occur only at school level for 26,001 rows (non-instructional facilities: central offices, nutrition consolidations, auxiliary facilities, GNETS programs, transitional/gateway academies). This column belongs in a schools dimension, not in the fact table. Do not attempt to parse into min/max grade fields without confirming downstream need.
- **School name stability**: Names like `All Column Values`, `z_Alpha Academy`, `z_Open Campus` are source artifacts — the `z_` prefix appears to flag placeholder/consolidated records. Do not filter them out without confirming with source docs; they may represent legitimate district-wide entries.
- **No suppression markers in MEASURE**: Unlike most GOSA datasets, certified_personnel does not use `*`/`TFS`/`N/A` markers — zeros are reported as `0`. This is unusual and reduces complexity, but the transform should still cast `MEASURE` with `strict=False` to catch any future introduction of markers.
- **Filename-vs-data year drift**: The filename year is always the ending calendar year of the school year in `LONG_SCHOOL_YEAR` (e.g., file `2024` = school year `2023-24`). The transform should derive `year` from `LONG_SCHOOL_YEAR` (ending year) rather than parsing the filename, since the source column is the authoritative record.
- **Row count grows mildly over time** (220k in 2010-11 → 230k in 2023-24), consistent with slow growth in the school count. Nothing here suggests a discontinuity that requires era-specific processing beyond the column-set difference.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| #RPT_NAME | not_in_gold | — | Constant value `CERTIFIED_PERSONNEL`; redundant |
| LONG_SCHOOL_YEAR | fact_key | year | Parse ending calendar year from `YYYY-YY` (e.g., `2023-24` → `2024`) |
| SCHOOL_DSTRCT_CD | fact_key | district_code | Georgia DOE district code as string (3-digit standard, 7-digit charter from 2012+); drop/flag rows where value = `ALL` per aggregate-row policy |
| SCHOOL_DSTRCT_NM | dimension_attribute | — | `district_name` in districts dimension; `All Column Values` rows should be filtered or treated as state aggregates |
| INSTN_NUMBER | fact_key | school_code | 4-character zero-padded school number as string (uniform in all files; only the `ALL` sentinel is 3-char); drop/flag rows where value = `ALL` per aggregate-row policy |
| INSTN_NAME | dimension_attribute | — | `school_name` in schools dimension |
| GRADES_SERVED_DESC | dimension_attribute | — | School-level metadata; store in schools dimension (comma-delimited grade list) or decompose into `min_grade`/`max_grade`/flag columns |
| DATA_CATEGORY | fact_categorical | measure_family | 7 values; snake_case recode (e.g., `Certificate Level` → `certificate_level`); forms a composite key with `measure_label` |
| DATA_SUB_CATEGORY | fact_categorical | measure_label | 27 values; snake_case recode (e.g., `5 Yr Master's` → `5_yr_masters`, `Other *` → `other`) |
| EMPLOYEE_TYPE | fact_categorical | employee_type | 3 values; recode `PK-12 Teachers` → `pk_12_teachers`, `Support Personnel` → `support_personnel`, `Administrators` → `administrators` |
| MEASURE | fact_metric | measure_value | Float; interpretation depends on (measure_family, measure_label) — may be a count, average salary (USD), average days, or average years of experience |

**Alternative gold layout**: Instead of keeping the long/tidy shape above, the transform may pivot the 27 (`DATA_CATEGORY`, `DATA_SUB_CATEGORY`) combinations into named metric columns keyed by (year, district_code, school_code, employee_type). Example metrics: `cert_4yr_bachelors_count`, `cert_5yr_masters_count`, `positions_number`, `positions_avg_annual_salary_usd`, `yrs_exp_under_1_count`, `yrs_exp_average`, `race_black_count`, `gender_female_count`, etc. This produces a wider fact table (~30+ metric columns) but matches the typical gold-star-schema pattern and is friendlier for downstream analytics. Pick the representation in `transform.py` consistent with `data-cleaning-standards`.
