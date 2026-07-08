# salaries_and_benefits — Bronze Data Structure

## Overview

- Topic: salaries_and_benefits
- Source: gosa
- Files: 14 CSV files spanning school years 2010-11 through 2023-24 (filenames 2011–2024)
- Unreadable files: none
- Year representation: Present both in the filename (`salaries_and_benefits_YYYY.csv`, publication/ending calendar year) and in the `LONG_SCHOOL_YEAR` column as a two-year school-year string (e.g., `2021-22`, `2023-24`). Each file contains exactly one school year.
- Filename-to-data year offset: Filename year equals the *ending* calendar year of the school year (e.g., `salaries_and_benefits_2024.csv` contains `2023-24` data). Recommended gold `year` = filename year = trailing year of the school year.
- Detail levels: State (3 rows per year, `SCHOOL_DSTRCT_CD = 'ALL'`) and District (one row per district × CATEGORY). Both eras include RESA (Regional Education Service Agency) aggregate rows with numeric district codes in the 8xx range (850, 852, 854, 856, ...): Era 1 (2011–2022) carries them as bare codes alongside traditional districts with no detail-level flag (e.g., `salaries_and_benefits_2011.csv` contains 48 RESA rows like `850 Pioneer RESA`, `854 Metro RESA`, `860 Coastal Plains RESA`), and Era 2 (2023–2024) adds an explicit `DETAIL_LVL_DESC = 'DOE OTHER'` flag for the same kind of rows.
- Percentage scale: 0–100 (percent values). All four percentage columns are already expressed as percentages (e.g., 54.21 means 54.21%, as seen in the state-level row in 2011).
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| salaries_and_benefits_2011.csv | bb901a6a689b4162d901787d6c0b78609e6dcdb2a79f70d40c53dca186c01b67 |
| salaries_and_benefits_2012.csv | 43abb931dbacb27d9ea8c6dfd39cb67ff051abc853856b192a5cc97b35a13f4d |
| salaries_and_benefits_2013.csv | 14201dbe9662aee57420b3235526395d841c5d3da3d008b558c66b8980dde9ed |
| salaries_and_benefits_2014.csv | 13d87d9dba8684f2eb8ebd5501b2db6b9a699448328915d2b4f77a9be21640a5 |
| salaries_and_benefits_2015.csv | a74a6fa2f34f967088bf930fa1e76cb280c590f507ba93dcdaf867947ce0ff42 |
| salaries_and_benefits_2016.csv | 083157babcee4f9655b10341cc036ba16a1e10d4f9154c2f3a28f8c74198d2f4 |
| salaries_and_benefits_2017.csv | 3061b3193d880b69362d10a9ebc1615092739db27a606897f046e16f2843539d |
| salaries_and_benefits_2018.csv | f29b1c09d75bf507b1b20bec00443379f50076d1d6fcd8f1f18ac62461e40b60 |
| salaries_and_benefits_2019.csv | fbf96c8affa2f3381136a0b70f6a384c614ebec4837eb422336882a0d6729749 |
| salaries_and_benefits_2020.csv | 2bd9efd46538569ed4ae44e4b1dec86d3459a9f6152da12ef366b28b939ebab7 |
| salaries_and_benefits_2021.csv | 65bd242399adad61378894891c70899abbfe45dc747b160c22d73d70dd24e044 |
| salaries_and_benefits_2022.csv | 86bfaaaab585aa5a3fcd17babf1cbbf34d54b7f99cba7c78a1b4a768f3c698b4 |
| salaries_and_benefits_2023.csv | 9ec8e3013f3694137d4db6b74219d2d94270320ff0673fe24222b65920991bc2 |
| salaries_and_benefits_2024.csv | b56cb6b3a36d8669851b09c2cdd3915b3f3055843ded602fa14e41567bd244e9 |

## Summary

This topic reports **district-level salary and benefit expenditures** for three staff CATEGORY groups — `Teachers and Paraprofessionals`, `General Administration`, and `School Administration` — along with how those salary+benefit totals compare against district revenue and expenditure bases. Each district × category row contains:

- `SALARIES` (dollars) — total salary dollars for that category
- `BENEFITS` (dollars) — total benefits dollars for that category
- `SALARIES_AND_BENEFITS` (dollars) — `SALARIES + BENEFITS`
- Percent of district revenue from GF / Title / Lottery funds spent on the category
- Percent of district total K-12 revenue spent on the category
- Percent of district expenditures from GF / Title / Lottery funds spent on the category
- Percent of district total K-12 expenditures spent on the category

## Eras

### Era 1: 2011–2022 (school years 2010-11 through 2021-22)

13 columns; no explicit detail-level column (state rows flagged only by `SCHOOL_DSTRCT_CD = 'ALL'`). RESA aggregate rows are present in this era too — they appear as bare numeric codes in the 850–888 range (e.g., 48 RESA rows in `salaries_and_benefits_2011.csv` like `850 Pioneer RESA`, `854 Metro RESA`, `860 Coastal Plains RESA`) and are not distinguished from regular districts by any column. Era 2 later adds an explicit `DOE OTHER` flag for the same kind of rows.

| Column | Description |
|--------|-------------|
| LONG_SCHOOL_YEAR | School year as `YYYY-YY` (e.g., `2021-22`). Single value per file. |
| SCHOOL_DSTRCT_CD | District code as string; numeric for districts (including 8xx RESA codes), literal `'ALL'` for state-level rollup rows. |
| SCHOOL_DSTRCT_NM | District name (title case). For state rollup rows, value is `'All Column Values'`. |
| INSTN_NUMBER | Always `'ALL'` in this dataset (no school-level detail). |
| INSTN_NAME | Always `'All Column Values'` in this dataset. |
| CATEGORY | Staff category: `General Administration`, `School Administration`, `Teachers and Paraprofessionals`. |
| SALARIES | Total salary dollars for the district × category (float, dollars). |
| BENEFITS | Total benefit dollars for the district × category (float, dollars; can be slightly negative in rare refund cases). |
| SALARIES_AND_BENEFITS | Sum of SALARIES + BENEFITS (float, dollars). |
| % Rev- GF/Title/Lottery | Salaries+benefits as % of district revenue from General Fund / Title / Lottery sources (0–100). |
| % Rev- Total K-12 | Salaries+benefits as % of district total K-12 revenue (0–100). |
| % Exp- GF/Title/Lottery | Salaries+benefits as % of district expenditures from GF / Title / Lottery (0–100). |
| % Exp-Total K-12 | Salaries+benefits as % of district total K-12 expenditures (0–100). |

#### Sample Data (2021-22)

```
shape: (5, 13)
LONG_SCHOOL_YEAR  SCHOOL_DSTRCT_CD  SCHOOL_DSTRCT_NM                                        INSTN_NUMBER  INSTN_NAME         CATEGORY                         SALARIES     BENEFITS     SALARIES_AND_BENEFITS  % Rev- GF/Title/Lottery  % Rev- Total K-12  % Exp- GF/Title/Lottery  % Exp-Total K-12
2021-22           7830611           State Charter Schools II- Cirrus Charter Academy        ALL           All Column Values  General Administration           8000.00      50783.26     58783.26               0.66                     0.62               0.80                     0.75
2021-22           7820121           State Charter Schools- Utopian Academy for the Arts...  ALL           All Column Values  General Administration           0.00         114234.60    114234.60              1.90                     1.76               2.30                     2.15
2021-22           624               Charlton County                                         ALL           All Column Values  Teachers and Paraprofessionals   6,204,400    3,059,444    9,263,900              41.83                    37.27              45.58                    40.58
2021-22           7820121           State Charter Schools- Utopian Academy for the Arts...  ALL           All Column Values  School Administration            865728.35    12145.52     877873.87              14.60                    13.49              17.71                    16.53
2021-22           644               DeKalb County                                           ALL           All Column Values  Teachers and Paraprofessionals   448,150,000  193,100,000  641,250,000            41.08                    35.98              44.16                    40.15
```

#### Statistics (2021-22)

```
count        711 rows
SALARIES                     mean 2.33e7   min 0.00         max 7.37e9
BENEFITS                     mean 1.13e7   min -191,629.60  max 3.52e9   (rare negative values observed)
SALARIES_AND_BENEFITS        mean 3.46e7   min 0.00         max 1.09e10
% Rev- GF/Title/Lottery      mean 16.27    min 0.00         max 60.47
% Rev- Total K-12            mean 13.70    min 0.00         max 60.47
% Exp- GF/Title/Lottery      mean 17.55    min 0.00         max 62.44
% Exp-Total K-12             mean 14.95    min 0.00         max 59.74
```

#### Null Counts (2021-22)

All 13 columns: 0 nulls.

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| LONG_SCHOOL_YEAR | `2021-22` (single value per file; varies by file) |
| INSTN_NUMBER | `ALL` (711) — always constant |
| INSTN_NAME | `All Column Values` (711) — always constant |
| CATEGORY | `General Administration` (237), `School Administration` (237), `Teachers and Paraprofessionals` (237) |
| SCHOOL_DSTRCT_NM | 237 distinct district names (+ `All Column Values` for state rows) |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| SCHOOL_DSTRCT_CD | `ALL` (3 rows — state rollup; all other rows are numeric district codes) |

No true suppression markers (no `*`, `TFS`, etc.) in any numeric column. All dollar and percent columns are fully numeric. BENEFITS occasionally has small negative values (refunds/adjustments) rather than suppression.

---

### Era 2: 2023–2024 (school years 2022-23 through 2023-24)

16 columns. Adds `#RPT_NAME`, `DETAIL_LVL_DESC`, and `GRADES_SERVED_DESC`; renames the four percent columns to underscore-based identifiers.

| Column | Description |
|--------|-------------|
| #RPT_NAME | Literal `Salary_and_Benefits`. Constant across all rows. |
| LONG_SCHOOL_YEAR | School year as `YYYY-YY` (single value per file). |
| DETAIL_LVL_DESC | Detail level: `District`, `State`, or `DOE OTHER` (RESA aggregates). Explicitly flags row granularity — replaces the implicit `'ALL'` convention from Era 1, and gives RESA rows (which already existed in Era 1 as bare 8xx codes) their own distinguishing label. |
| SCHOOL_DSTRCT_CD | District code as string; numeric for districts (including 8xx RESA codes), literal `'ALL'` for state rollup. |
| SCHOOL_DSTRCT_NM | District / entity name. `'All Column Values'` for state rows; RESA names (e.g., `Metro RESA`, `Coastal Plains RESA`) for `DOE OTHER` rows. |
| INSTN_NUMBER | Always `'ALL'`. |
| INSTN_NAME | Always `'All Column Values'`. |
| GRADES_SERVED_DESC | Comma-separated grade list, e.g., `PK,KK,01,02,...,12`. Null for all `DOE OTHER` rows. |
| CATEGORY | Staff category (same 3 values as Era 1). |
| SALARIES | Dollars. |
| BENEFITS | Dollars. |
| SALARIES_AND_BENEFITS | Dollars. |
| REV__GF/TITLE/LOTTERY | Renamed from Era 1 `% Rev- GF/Title/Lottery`. Same meaning, 0–100 scale. |
| REV__TOTAL_K_12 | Renamed from Era 1 `% Rev- Total K-12`. |
| EXP__GF/TITLE/LOTTERY | Renamed from Era 1 `% Exp- GF/Title/Lottery`. |
| EXP_TOTAL_K_12 | Renamed from Era 1 `% Exp-Total K-12`. |

#### Sample Data (2023-24)

```
shape: (5, 16)
#RPT_NAME            LONG_SCHOOL_YEAR  DETAIL_LVL_DESC  SCHOOL_DSTRCT_CD  SCHOOL_DSTRCT_NM                                     INSTN_NUMBER  INSTN_NAME         GRADES_SERVED_DESC                          CATEGORY                          SALARIES      BENEFITS      SALARIES_AND_BENEFITS  REV__GF/TITLE/LOTTERY  REV__TOTAL_K_12  EXP__GF/TITLE/LOTTERY  EXP_TOTAL_K_12
Salary_and_Benefits  2023-24           District         7830620           State Charter Schools II- International Charter ...  ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   General Administration            189644.19     55719.32      245363.51              6.95                   6.95             8.02                   8.00
Salary_and_Benefits  2023-24           District         7820618           State Charter Schools- Coastal Plains High School    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   General Administration            1513902.30    218792.24     1732694.54             8.99                   8.99             11.39                  11.39
Salary_and_Benefits  2023-24           District         625               Savannah-Chatham County                              ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Teachers and Paraprofessionals    187,070,000   100,870,000   287,940,000            41.26                  33.00            46.77                  35.90
Salary_and_Benefits  2023-24           District         7820618           State Charter Schools- Coastal Plains High School    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   School Administration             1,507,300     250,875       1,758,200              9.13                   9.13             11.56                  11.56
Salary_and_Benefits  2023-24           District         646               Dooly County                                         ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Teachers and Paraprofessionals    4,576,700     2,529,200     7,105,900              33.68                  28.74            34.54                  27.10
```

#### Statistics (2023-24)

```
count        747 rows
SALARIES                 mean 2.50e7   min -2,000.00   max 8.30e9
BENEFITS                 mean 1.41e7   min 0.00        max 4.64e9
SALARIES_AND_BENEFITS    mean 3.91e7   min 0.00        max 1.29e10
REV__GF/TITLE/LOTTERY    mean 16.91    min 0.00        max 62.99
REV__TOTAL_K_12          mean 14.55    min 0.00        max 59.73
EXP__GF/TITLE/LOTTERY    mean 17.58    min 0.00        max 66.06
EXP_TOTAL_K_12           mean 14.76    min 0.00        max 66.06
```

#### Null Counts (2023-24)

All columns 0 nulls **except** `GRADES_SERVED_DESC` which has 48 nulls — corresponding exactly to the 48 `DOE OTHER` (RESA) rows.

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| #RPT_NAME | `Salary_and_Benefits` (747) — always constant |
| LONG_SCHOOL_YEAR | Single value per file |
| DETAIL_LVL_DESC | `District` (696), `DOE OTHER` (48), `State` (3) |
| INSTN_NUMBER | `ALL` (747) — always constant |
| INSTN_NAME | `All Column Values` (747) — always constant |
| GRADES_SERVED_DESC | `PK,KK,01,02,03,04,05,06,07,08,09,10,11,12` (681), null (48, all `DOE OTHER`), `KK,01,02,03,04,05,06,07,08,09,10,11,12` (18) |
| CATEGORY | `General Administration` (249), `School Administration` (249), `Teachers and Paraprofessionals` (249) |
| SCHOOL_DSTRCT_NM | 247 distinct names (districts + RESAs + `All Column Values`) |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| SCHOOL_DSTRCT_CD | `ALL` (3 rows — state rollup) |

No suppression markers (no `*`, `TFS`, `N/A`). SALARIES has one small negative (-2000.00) in 2023-24 — a data quality oddity, not a suppression marker.

## ETL Considerations

- **Column renames across eras.** The four percent columns are the main schema change between eras:
  | Era 1 (2011–2022) | Era 2 (2023–2024) |
  | --- | --- |
  | `% Rev- GF/Title/Lottery` | `REV__GF/TITLE/LOTTERY` |
  | `% Rev- Total K-12` | `REV__TOTAL_K_12` |
  | `% Exp- GF/Title/Lottery` | `EXP__GF/TITLE/LOTTERY` |
  | `% Exp-Total K-12` | `EXP_TOTAL_K_12` |
  Map both to a single set of snake_case gold column names (e.g., `pct_revenue_gf_title_lottery`, `pct_revenue_total_k12`, `pct_expense_gf_title_lottery`, `pct_expense_total_k12`).
- **Percentages are already 0–100.** Do not multiply by 100; the state-level 2010-11 row showing 54.21 for Teachers & Paraprofessionals confirms the scale.
- **Year.** Use the trailing year of `LONG_SCHOOL_YEAR` as the gold `year` (e.g., `2023-24` → `2024`). This matches the filename year.
- **Detail levels.** In Era 1 the detail level is implicit (state rows have `SCHOOL_DSTRCT_CD = 'ALL'`; everything else — including RESA rows with 8xx codes — is district). Era 2 adds explicit `DETAIL_LVL_DESC` with a `DOE OTHER` level that distinguishes RESAs from traditional districts. Decide whether gold keeps RESA rows (the current transform routes them to `detail_level = 'district'` in both eras to keep their natural codes queryable) and state rows (either drop or encode with a `district_code` sentinel/`NULL`). Both eras contain RESA rows; Era 1 just doesn't flag them separately.
- **District code is string, not zero-padded.** Values are bare integers like `624`, `644`, `7830611`. Treat as string to preserve leading characters where present and to avoid losing the `ALL` sentinel. Note: codes in the 7xxx–8xxx range are charter/state special entities, not traditional county districts.
- **District name drift.** District / charter names change spelling and suffix across years (e.g., `State Charter Schools- Coastal Plains High School` appears in Era 2 but not Era 1). Store name in the districts dimension, not the fact table, and key joins on `district_code`.
- **Constant columns to drop.** `#RPT_NAME`, `INSTN_NUMBER`, `INSTN_NAME` are constant in every row and add no information to the fact table.
- **GRADES_SERVED_DESC** exists only in Era 2 and is null for all RESA rows. Not a useful fact; either drop entirely or move to a districts-dimension attribute if it turns out to vary meaningfully across districts.
- **BENEFITS can be slightly negative** (2021-22 min = -191,629.60). Treat as valid data (likely refunds/adjustments), not as errors to null out.
- **SALARIES has one small negative** (-2,000.00) in 2023-24 — same treatment.
- **Tidy format.** CATEGORY is already a long-format row grain (3 rows per district). Keep it as a `fact_categorical` (staff category) rather than pivoting wide.
- **Row count per year.** Era 1 files have 618–711 rows (~205–237 districts × 3 categories + 3 state rows). Era 2 adds ~48 RESA rows per year (16 RESAs × 3 categories).
- **No suppression.** Unlike most GOSA topics, this dataset has no `*` / `TFS` / `N/A` suppression markers, so numeric casting is lossless.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| LONG_SCHOOL_YEAR | fact_key | year | Parse trailing two-digit year to 4-digit int (e.g., `2023-24` → `2024`). |
| SCHOOL_DSTRCT_CD | fact_key | district_code | String. Drop rows where value is `'ALL'` (state rollups) unless gold explicitly supports a state grain; drop RESA rows (Era 2 `DOE OTHER`) from the district fact. |
| SCHOOL_DSTRCT_NM | dimension_attribute | — | `district_name` in districts dimension. |
| INSTN_NUMBER | not_in_gold | — | Constant `'ALL'`; no school-level data in this topic. |
| INSTN_NAME | not_in_gold | — | Constant `'All Column Values'`. |
| #RPT_NAME | not_in_gold | — | Constant `'Salary_and_Benefits'` (Era 2 only). |
| DETAIL_LVL_DESC | not_in_gold | — | Era 2 only; used during transform to filter/partition rows, not retained in fact table (detail level is implicit from which rows survive filtering). |
| GRADES_SERVED_DESC | not_in_gold | — | Era 2 only; null for RESAs, near-constant for districts. Not a metric. |
| CATEGORY | fact_categorical | staff_category | Values: `general_administration`, `school_administration`, `teachers_and_paraprofessionals` (snake_case). |
| SALARIES | fact_metric | salaries_dollars | Float (dollars). Negatives preserved as-is. |
| BENEFITS | fact_metric | benefits_dollars | Float (dollars). Negatives preserved as-is. |
| SALARIES_AND_BENEFITS | fact_metric | salaries_and_benefits_dollars | Float (dollars). Equal to SALARIES + BENEFITS. |
| `% Rev- GF/Title/Lottery` / REV__GF/TITLE/LOTTERY | fact_metric | pct_revenue_gf_title_lottery | Float, 0–100. Salaries+benefits as % of district GF/Title/Lottery revenue. |
| `% Rev- Total K-12` / REV__TOTAL_K_12 | fact_metric | pct_revenue_total_k12 | Float, 0–100. % of total K-12 revenue. |
| `% Exp- GF/Title/Lottery` / EXP__GF/TITLE/LOTTERY | fact_metric | pct_expense_gf_title_lottery | Float, 0–100. % of GF/Title/Lottery expenditures. |
| `% Exp-Total K-12` / EXP_TOTAL_K_12 | fact_metric | pct_expense_total_k12 | Float, 0–100. % of total K-12 expenditures. |
