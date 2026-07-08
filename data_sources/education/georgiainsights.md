# Georgia Insights

Datasets to download from [Georgia Insights](https://georgiainsights.gadoe.org/data-downloads/)

The data downloads page in Georgia Insights is an embedded Microsoft PowerBI Table. We only need to download data from Page 1 ('State/School/System Files')

**Datasets**

## Accountability

### CCRPI

GOSA provides individual assessment results (Georgia Milestones, GAA) and standalone metrics (graduation rates, FESR), but does not include the CCRPI composite accountability system data. The following CCRPI subcategories are unique to Georgia Insights.

#### Climate Star Rating

- **Description**: School Climate Star Ratings paired with CCRPI scores. Rates school climate on a star scale alongside overall CCRPI performance.
- **Years**: 2014-2019, 2024
- **Files**: 7

#### Content Mastery

- **Description**: CCRPI Content Mastery scores, targets, and flags by subgroup. Measures student mastery of grade-level content standards.
- **Years**: 2012-2019, 2021-2025
- **Files**: 14

#### Graduation Rate

- **Description**: CCRPI-specific graduation rate data including scores, targets, and flags by subgroup. Also includes 5-year graduation rates and on-time graduation rates not available in GOSA.
- **Years**: 2012-2025
- **Overlap note**: GOSA provides basic 4-year cohort graduation rates. The Georgia Insights CCRPI data adds target/flag scoring, 5-year cohort rates, and on-time graduation rates.
- **Files**: 22
- **2023 4-year count gap**: the Georgia Insights standalone 4-year release for 2023 (`4-Year Cohort Graduation Rate State District School by Subgroups_12.14.23.pdf`) is a 125-page typeset PDF the pipeline cannot parse. The equivalent release is available as CSV from the GOSA download portal at `https://download.gosa.ga.gov/2023/Graduation_Rate_2022-23_2023-12-15_18_55_15.csv` and is ingested as Family F in `transform.py` to fill the `graduation_class_size` / `total_graduated` columns for 2023. The CCRPI xlsx remains the authoritative source for the 2023 rate, target, and flag; GOSA supplies only the counts. If bronze is wiped, re-download the GOSA CSV into `data/bronze/education/georgiainsights/ccrpi_graduation_rate/GOSA_4-Year_Cohort_Graduation_Rate_2022-23_12.15.23.csv` to preserve 2023 count coverage.

#### Progress

- **Description**: CCRPI Progress scores, targets, and flags by subgroup. Includes Progress Towards English Language Proficiency indicators.
- **Years**: 2018-2025 (no 2020 data for full progress; 2020-2021 include language proficiency only)
- **Files**: 8

#### Readiness

- **Description**: CCRPI Readiness indicators by subgroup. Measures college and career readiness preparation across grade bands.
- **Years**: 2018-2019, 2021-2025
- **Files**: 7

#### Scoring by Component

- **Description**: Overall CCRPI scores broken down by component (Content Mastery, Progress, Readiness, Graduation Rate, etc.) at the state, system, and school level.
- **Years**: 2012-2019, 2022-2025
- **Files**: 13

---

## CTAE

### Pathway Graduation Rate

- **Description**: Career, Technical, and Agricultural Education (CTAE) pathway-specific graduation rates at the state, system, and school level for high school students.
- **Years**: 2021-2025
- **Files**: 5

---

## Student Demographics

GOSA provides enrollment by grade level and by subgroup programs. The Georgia Insights enrollment data comes directly from DOE FTE counts and includes breakdowns not available in GOSA.

### Enrollment March

#### Gender, Race, Ethnicity

- **Description**: FTE enrollment counts broken down by race/ethnicity and gender at the school and system level from the March FTE count.
- **Years**: 2010-2025 (school level), 2010-2025 (system level)
- **Overlap note**: GOSA provides enrollment by subgroup programs which includes some demographic breakdowns, but the Georgia Insights data uses DOE FTE counts with a different structure and granularity.
- **Files**: Range of annual files at school and district level

> **Note**: The source dashboard lists files for each year from 2010 to 2025. Only the first and last year are shown above. The download URL pattern is consistent — substitute the fiscal year in the file name to access intermediate years.

#### Grade

- **Description**: FTE enrollment counts by grade level at the school and system level from the March FTE count.
- **Years**: 2010-2025 (school level), 2011-2025 (system level)
- **Overlap note**: GOSA provides enrollment by grade level (2011-2024), but the Georgia Insights data uses DOE FTE counts with a different structure and may include additional years.
- **Files**: Range of annual files at school and district level

> **Note**: The source dashboard lists files for each year within the ranges above. Only the first and last year are shown. The download URL pattern is consistent — substitute the fiscal year in the file name to access intermediate years.

### Enrollment October

#### Disability

- **Description**: FTE enrollment counts by grade and disability category at the system level from the October FTE count.
- **Years**: 2010-2025
- **Files**: Range of annual files at district level

> **Note**: The source dashboard lists files for each year from 2010 to 2025. Only the first and last year are shown. The download URL pattern is consistent — substitute the fiscal year in the file name to access intermediate years.

#### Gender, Race, Ethnicity

#### Grade

### Free Reduced Lunch

--

## Student Performance

### Georgia Milestones

#### End of Course

#### End of Grade

### Georgia Student Growth Model

#### End of Course

#### End of Grade

### WIDA Access

--

## Whole Child

### Attendance Dashboard
