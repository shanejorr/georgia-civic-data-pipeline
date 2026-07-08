# educator_qualifications_emergency_and_provisional_credentials — Bronze Data Structure

## Overview

- Topic: educator_qualifications_emergency_and_provisional_credentials
- Source: gosa
- Files: 7 CSV files spanning 2018–2024
- Unreadable files: none
- Year representation: `LONG_SCHOOL_YEAR` column in format `YYYY-YY` (e.g., `2023-24`); school year spanning two calendar years
- Filename-to-data year offset: filename year = ending year of school year (e.g., file `2024` → data year `2023-24`)
- Detail levels: state, district, school
- Percentage scale: 0–100 (the `*_FTE_PCT` columns are integer percents; observed range 0 in 2018–2020 and 10–71 in 2021+ when not suppressed)
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| educator_qualifications_emergency_and_provisional_credentials_2018.csv | 20533211bb9b5c516c5bcaa473b590abd74a251be6befac8130ea3cd572d95eb |
| educator_qualifications_emergency_and_provisional_credentials_2019.csv | ea0bd1910eaa8e6e3540620c6aa1a7e317f64318e3d6cb252121ba909933200b |
| educator_qualifications_emergency_and_provisional_credentials_2020.csv | ba4e0fcfe3542973e981d18f0b37b875bdb74478b9ab751697d502cc0cc6ea25 |
| educator_qualifications_emergency_and_provisional_credentials_2021.csv | e6b90f5bf8de7ce2e50dff0d5f96033937f192555994901d7d292a39ee08214d |
| educator_qualifications_emergency_and_provisional_credentials_2022.csv | d8982d67826debf5af4725bdf1df3b23fb74e01c06edc8cc957fb5e8c0241774 |
| educator_qualifications_emergency_and_provisional_credentials_2023.csv | 572f7be002d3a15d620b5bdf1ff674e9d754d5d2a8f819db4211bf595448a47d |
| educator_qualifications_emergency_and_provisional_credentials_2024.csv | cf1f16468f19b9f5eb838f15e527ee8220873f76c6a36e32a396163f4f1e785b |

## Summary

Reports the count and percentage of teacher full-time equivalents (FTE) holding **Emergency** teaching credentials at each Georgia public school, district, and state-wide. Teachers with emergency credentials have been hired without holding a fully-approved standard teaching certificate. Each row provides the total teacher FTE at the entity (or aggregate), the FTE of those teachers holding an Emergency credential, and that count expressed as a percentage of total FTE. Within each entity, three sub-rows are reported: `Total`, `High Poverty` (schools in the highest-poverty quartile), and `Low Poverty` (schools in the lowest-poverty quartile). The dataset is school-year-based (2017–18 through 2023–24). Despite the topic name referencing both "Emergency and Provisional" credentials, the 2023–2024 files' `#CATEGORY_DESC` column only surfaces the value `Emergency`; no `Provisional` rows appear in any of the seven source files.

## Eras

### Era 1: 2023–2024

**Columns**: `#CATEGORY_DESC`, `LONG_SCHOOL_YEAR`, `SCHOOL_DSTRCT_NM`, `INSTN_NAME`, `LABEL_LVL_3_DESC`, `LABEL_LVL_2_DESC`, `FTE`, `CATEGORY_FTE`, `CATEGORY_FTE_PCT`

| Column | Description |
|--------|-------------|
| #CATEGORY_DESC | Credential category being measured; constant `Emergency` in this topic |
| LONG_SCHOOL_YEAR | School year in format `YYYY-YY` (e.g., `2023-24`) |
| SCHOOL_DSTRCT_NM | District name; `State of Georgia` for state-level rows |
| INSTN_NAME | Institution name; `<District>- All Schools` for district aggregates; `All Georgia Schools` for state aggregates |
| LABEL_LVL_3_DESC | Workforce role; constant `Teachers` |
| LABEL_LVL_2_DESC | Poverty subgroup: `Total`, `High Poverty`, or `Low Poverty` |
| FTE | Total teacher FTE in the entity (numeric, may be `TFS`) |
| CATEGORY_FTE | Teacher FTE holding the credential category in `#CATEGORY_DESC` (numeric, may be `TFS`) |
| CATEGORY_FTE_PCT | `CATEGORY_FTE` as a percentage of `FTE`, integer 10–100 (numeric, may be `TFS`) |

#### Sample Data (2024)

```
shape: (5, 9)
┌────────────────┬──────────────────┬───────────────────────┬──────────────────────────────────────────────────────┬──────────────────┬──────────────────┬───────┬──────────────┬──────────────────┐
│ #CATEGORY_DESC ┆ LONG_SCHOOL_YEAR ┆ SCHOOL_DSTRCT_NM      ┆ INSTN_NAME                                           ┆ LABEL_LVL_3_DESC ┆ LABEL_LVL_2_DESC ┆ FTE   ┆ CATEGORY_FTE ┆ CATEGORY_FTE_PCT │
╞════════════════╪══════════════════╪═══════════════════════╪══════════════════════════════════════════════════════╪══════════════════╪══════════════════╪═══════╪══════════════╪══════════════════╡
│ Emergency      ┆ 2023-24          ┆ Peach County          ┆ Hunt Elementary School                               ┆ Teachers         ┆ Total            ┆ 42.5  ┆ TFS          ┆ TFS              │
│ Emergency      ┆ 2023-24          ┆ Dalton Public Schools ┆ Dalton Public Schools- All Schools                   ┆ Teachers         ┆ High Poverty     ┆ 276.1 ┆ 23           ┆ TFS              │
│ Emergency      ┆ 2023-24          ┆ White County          ┆ Tesnatee Gap Elementary (Old White Co. Intermediate) ┆ Teachers         ┆ Total            ┆ 34.3  ┆ TFS          ┆ TFS              │
│ Emergency      ┆ 2023-24          ┆ Jones County          ┆ Gray Station Middle School                           ┆ Teachers         ┆ Total            ┆ 48.6  ┆ TFS          ┆ TFS              │
│ Emergency      ┆ 2023-24          ┆ Oconee County         ┆ Malcom Bridge Elementary School                      ┆ Teachers         ┆ Low Poverty     ┆ 45    ┆ TFS          ┆ TFS              │
└────────────────┴──────────────────┴───────────────────────┴──────────────────────────────────────────────────────┴──────────────────┴──────────────────┴───────┴──────────────┴──────────────────┘
```

#### Statistics (2024)

```
shape: (9, 10)
┌────────────┬────────────────┬──────────────────┬──────────────────┬──────────────────────────────┬──────────────────┬──────────────────┬──────┬──────────────┬──────────────────┐
│ statistic  ┆ #CATEGORY_DESC ┆ LONG_SCHOOL_YEAR ┆ SCHOOL_DSTRCT_NM ┆ INSTN_NAME                   ┆ LABEL_LVL_3_DESC ┆ LABEL_LVL_2_DESC ┆ FTE  ┆ CATEGORY_FTE ┆ CATEGORY_FTE_PCT │
╞════════════╪════════════════╪══════════════════╪══════════════════╪══════════════════════════════╪══════════════════╪══════════════════╪══════╪══════════════╪══════════════════╡
│ count      ┆ 3708           ┆ 3708             ┆ 3708             ┆ 3708                         ┆ 3708             ┆ 3708             ┆ 3708 ┆ 3708         ┆ 3708             │
│ null_count ┆ 0              ┆ 0                ┆ 0                ┆ 0                            ┆ 0                ┆ 0                ┆ 0    ┆ 0            ┆ 0                │
│ min        ┆ Emergency      ┆ 2023-24          ┆ Appling County   ┆ 7 Pillars Career Academy     ┆ Teachers         ┆ High Poverty     ┆ 10   ┆ 10           ┆ 10               │
│ max        ┆ Emergency      ┆ 2023-24          ┆ Worth County     ┆ iGrad Virtual Academy School ┆ Teachers         ┆ Total            ┆ TFS  ┆ TFS          ┆ TFS              │
└────────────┴────────────────┴──────────────────┴──────────────────┴──────────────────────────────┴──────────────────┴──────────────────┴──────┴──────────────┴──────────────────┘
```

(`mean`, `std`, and quartile rows are all `null` because every column is read as `Utf8` due to `TFS` suppression markers.)

#### Null Counts (2024)

```
shape: (1, 9)
All columns: 0 nulls
```

#### Categorical Columns (2024)

| Column | Distinct Values |
|--------|----------------|
| #CATEGORY_DESC | `Emergency` (3,708) — constant for this topic |
| LONG_SCHOOL_YEAR | `2023-24` (3,708) |
| SCHOOL_DSTRCT_NM | 182 values including `State of Georgia` (3 rows) and 181 actual districts |
| INSTN_NAME | 2,325 values: 2,322 individual schools plus aggregate names `<District>- All Schools` (one per district) and `All Georgia Schools` (3 state-level rows) |
| LABEL_LVL_3_DESC | `Teachers` (3,708) — constant |
| LABEL_LVL_2_DESC | `Total` (2,426), `High Poverty` (660), `Low Poverty` (622) |

#### Suppression Markers (2024)

| Column | Non-Numeric Values |
|--------|-------------------|
| FTE | `TFS` (95 rows) |
| CATEGORY_FTE | `TFS` (3,062 rows — most schools have <10 emergency FTE) |
| CATEGORY_FTE_PCT | `TFS` (2,378 rows) |

`TFS` = "Too Few Students/Staff to report." Numeric values in all three columns are bounded below by 10 (the GOSA reporting floor); the `*_FTE_PCT` columns are integer percents on a 0–100 scale.

### Era 2: 2022

**Columns**: `LONG_SCHOOL_YEAR`, `SCHOOL_DSTRCT_NM`, `INSTN_NAME`, `LABEL_LVL_3_DESC`, `LABEL_LVL_2_DESC`, `FTE`, `Emergency_FTE`, `Emergency_FTE_PCT`

Same data as Era 1, but the credential category is encoded in the **column name** (`Emergency_FTE` / `Emergency_FTE_PCT`) instead of a `#CATEGORY_DESC` row dimension. The leading `#CATEGORY_DESC` column does not exist in this era.

| Column | Description |
|--------|-------------|
| LONG_SCHOOL_YEAR | School year `2021-22` |
| SCHOOL_DSTRCT_NM | District name; `State of Georgia` for state-level rows |
| INSTN_NAME | Institution name; `<District>- All Schools` for district aggregates; `All Georgia Schools` for state aggregates |
| LABEL_LVL_3_DESC | Workforce role; constant `Teachers` |
| LABEL_LVL_2_DESC | Poverty subgroup: `Total`, `High Poverty`, or `Low Poverty` |
| FTE | Total teacher FTE in the entity (numeric, may be `TFS`) |
| Emergency_FTE | Teacher FTE holding an Emergency credential (numeric, may be `TFS`) |
| Emergency_FTE_PCT | `Emergency_FTE` as a percentage of `FTE`, integer 10–100 (numeric, may be `TFS`) |

#### Sample Data (2022)

```
shape: (5, 8)
┌──────────────────┬──────────────────┬──────────────────────────────┬──────────────────┬──────────────────┬───────┬───────────────┬───────────────────┐
│ LONG_SCHOOL_YEAR ┆ SCHOOL_DSTRCT_NM ┆ INSTN_NAME                   ┆ LABEL_LVL_3_DESC ┆ LABEL_LVL_2_DESC ┆ FTE   ┆ Emergency_FTE ┆ Emergency_FTE_PCT │
╞══════════════════╪══════════════════╪══════════════════════════════╪══════════════════╪══════════════════╪═══════╪═══════════════╪═══════════════════╡
│ 2021-22          ┆ Richmond County  ┆ Josey High School            ┆ Teachers         ┆ Total            ┆ 34.8  ┆ 10            ┆ 29                │
│ 2021-22          ┆ Dawson County    ┆ Dawson County- All Schools   ┆ Teachers         ┆ Total            ┆ 231.4 ┆ 14.3          ┆ TFS               │
│ 2021-22          ┆ Whitfield County ┆ Cedar Ridge Elementary       ┆ Teachers         ┆ Total            ┆ 26    ┆ TFS           ┆ TFS               │
│ 2021-22          ┆ Marion County    ┆ L. K. Moss Elementary School ┆ Teachers         ┆ Total            ┆ 36.4  ┆ TFS           ┆ TFS               │
│ 2021-22          ┆ Putnam County    ┆ Putnam County Middle School  ┆ Teachers         ┆ High Poverty     ┆ 54    ┆ TFS           ┆ TFS               │
└──────────────────┴──────────────────┴──────────────────────────────┴──────────────────┴──────────────────┴───────┴───────────────┴───────────────────┘
```

#### Statistics (2022)

```
shape: (9, 9)
┌────────────┬──────────────────┬──────────────────┬──────────────────────────────┬──────────────────┬──────────────────┬──────┬───────────────┬───────────────────┐
│ statistic  ┆ LONG_SCHOOL_YEAR ┆ SCHOOL_DSTRCT_NM ┆ INSTN_NAME                   ┆ LABEL_LVL_3_DESC ┆ LABEL_LVL_2_DESC ┆ FTE  ┆ Emergency_FTE ┆ Emergency_FTE_PCT │
╞════════════╪══════════════════╪══════════════════╪══════════════════════════════╪══════════════════╪══════════════════╪══════╪═══════════════╪═══════════════════╡
│ count      ┆ 3789             ┆ 3789             ┆ 3789                         ┆ 3789             ┆ 3789             ┆ 3789 ┆ 3789          ┆ 3789              │
│ null_count ┆ 0                ┆ 0                ┆ 0                            ┆ 0                ┆ 0                ┆ 0    ┆ 0             ┆ 0                 │
│ min        ┆ 2021-22          ┆ Appling County   ┆ 7 Pillars Career Academy     ┆ Teachers         ┆ High Poverty     ┆ 10   ┆ 10            ┆ 10                │
│ max        ┆ 2021-22          ┆ Worth County     ┆ iGrad Virtual Academy School ┆ Teachers         ┆ Total            ┆ TFS  ┆ TFS           ┆ TFS               │
└────────────┴──────────────────┴──────────────────┴──────────────────────────────┴──────────────────┴──────────────────┴──────┴───────────────┴───────────────────┘
```

#### Null Counts (2022)

```
shape: (1, 8)
All columns: 0 nulls
```

#### Categorical Columns (2022)

| Column | Distinct Values |
|--------|----------------|
| LONG_SCHOOL_YEAR | `2021-22` (3,789) |
| SCHOOL_DSTRCT_NM | 222 values including `State of Georgia` (3 rows) and 221 actual districts |
| INSTN_NAME | 2,403 values |
| LABEL_LVL_3_DESC | `Teachers` (3,789) |
| LABEL_LVL_2_DESC | `Total` (2,502), `High Poverty` (656), `Low Poverty` (631) |

#### Suppression Markers (2022)

| Column | Non-Numeric Values |
|--------|-------------------|
| FTE | `TFS` (119 rows) |
| Emergency_FTE | `TFS` (3,385 rows) |
| Emergency_FTE_PCT | `TFS` (2,883 rows) |

### Era 3: 2018–2021

**Columns**: `LONG_SCHOOL_YEAR`, `SCHOOL_DSTRCT_NM`, `INSTN_NAME`, `LABEL_LVL_3_DESC`, `LABEL_LVL_2_DESC`, `FTE`, `OUTOFFIELD_FTE`, `OUTOFFIELD_FTE_PCT`

> **CRITICAL — column-name vs. data mismatch.** In this era the metric columns are named `OUTOFFIELD_FTE` and `OUTOFFIELD_FTE_PCT`, but the **values they contain are Emergency-credential FTE counts** (the same metric reported in Era 2 as `Emergency_FTE` and in Era 1 as `CATEGORY_FTE` with `#CATEGORY_DESC = Emergency`). The mismatch was confirmed by comparing 2021 state-level totals: this directory's `OUTOFFIELD_FTE` = 9,796.9, while the parallel `educator_qualifications_out_of_field_teachers/` directory's 2021 file shows `OUTOFFIELD_FTE` = 6,281.9 (the genuine out-of-field metric). GOSA appears to have re-used the legacy `OUTOFFIELD_FTE` column header for the Emergency report when it was first published. The transform must rename these columns to the Emergency metric and not interpret them as out-of-field counts.

| Column | Description |
|--------|-------------|
| LONG_SCHOOL_YEAR | School year (`2017-18` through `2020-21`) |
| SCHOOL_DSTRCT_NM | District name; `State of Georgia` for state-level rows |
| INSTN_NAME | Institution name; `<District>- All Schools` for district aggregates; `All Georgia Schools` for state aggregates |
| LABEL_LVL_3_DESC | Workforce role; constant `Teachers` |
| LABEL_LVL_2_DESC | Poverty subgroup: `Total`, `High Poverty`, or `Low Poverty` |
| FTE | Total teacher FTE in the entity (numeric; `TFS` only in 2021) |
| OUTOFFIELD_FTE | **Actually:** Teacher FTE holding an Emergency credential (numeric; `TFS` only in 2021; true `0` values present in 2018–2020) |
| OUTOFFIELD_FTE_PCT | **Actually:** Emergency-credentialed FTE as a percentage of total FTE, integer 0–100 (numeric; `TFS` only in 2021; true `0` values present in 2018–2020) |

#### Sample Data (representative — 2021)

```
shape: (5, 8)
┌──────────────────┬──────────────────┬────────────────────────────────────┬──────────────────┬──────────────────┬──────┬────────────────┬────────────────────┐
│ LONG_SCHOOL_YEAR ┆ SCHOOL_DSTRCT_NM ┆ INSTN_NAME                         ┆ LABEL_LVL_3_DESC ┆ LABEL_LVL_2_DESC ┆ FTE  ┆ OUTOFFIELD_FTE ┆ OUTOFFIELD_FTE_PCT │
╞══════════════════╪══════════════════╪════════════════════════════════════╪══════════════════╪══════════════════╪══════╪════════════════╪════════════════════╡
│ 2020-21          ┆ Richmond County  ┆ Goshen Elementary School           ┆ Teachers         ┆ High Poverty     ┆ 32.8 ┆ TFS            ┆ 16                 │
│ 2020-21          ┆ DeKalb County    ┆ Doraville United Elementary School ┆ Teachers         ┆ Total            ┆ 65   ┆ TFS            ┆ 12                 │
│ 2020-21          ┆ Wheeler County   ┆ Wheeler County- All Schools        ┆ Teachers         ┆ Total            ┆ 69.7 ┆ TFS            ┆ 11                 │
│ 2020-21          ┆ Marietta City    ┆ Marietta City- All Schools         ┆ Teachers         ┆ Low Poverty      ┆ 58.6 ┆ TFS            ┆ TFS                │
│ 2020-21          ┆ Polk County      ┆ Rockmart Middle School             ┆ Teachers         ┆ Total            ┆ 47.4 ┆ TFS            ┆ TFS                │
└──────────────────┴──────────────────┴────────────────────────────────────┴──────────────────┴──────────────────┴──────┴────────────────┴────────────────────┘
```

#### Statistics (representative — 2021)

```
shape: (9, 9)
┌────────────┬──────────────────┬──────────────────┬──────────────────────────┬──────────────────┬──────────────────┬──────┬────────────────┬────────────────────┐
│ statistic  ┆ LONG_SCHOOL_YEAR ┆ SCHOOL_DSTRCT_NM ┆ INSTN_NAME               ┆ LABEL_LVL_3_DESC ┆ LABEL_LVL_2_DESC ┆ FTE  ┆ OUTOFFIELD_FTE ┆ OUTOFFIELD_FTE_PCT │
╞════════════╪══════════════════╪══════════════════╪══════════════════════════╪══════════════════╪══════════════════╪══════╪════════════════╪════════════════════╡
│ count      ┆ 3790             ┆ 3790             ┆ 3790                     ┆ 3790             ┆ 3790             ┆ 3790 ┆ 3790           ┆ 3790               │
│ null_count ┆ 0                ┆ 0                ┆ 0                        ┆ 0                ┆ 0                ┆ 0    ┆ 0              ┆ 0                  │
│ min        ┆ 2020-21          ┆ Appling County   ┆ 7 Pillars Career Academy ┆ Teachers         ┆ High Poverty     ┆ 10   ┆ 10             ┆ 10                 │
│ max        ┆ 2020-21          ┆ Worth County     ┆ Zebulon High School      ┆ Teachers         ┆ Total            ┆ TFS  ┆ TFS            ┆ TFS                │
└────────────┴──────────────────┴──────────────────┴──────────────────────────┴──────────────────┴──────────────────┴──────┴────────────────┴────────────────────┘
```

#### Null Counts (representative — 2021)

```
shape: (1, 8)
All columns: 0 nulls
```

#### Categorical Columns (representative — 2021)

| Column | Distinct Values |
|--------|----------------|
| LONG_SCHOOL_YEAR | `2020-21` (3,790) |
| SCHOOL_DSTRCT_NM | 222 values including `State of Georgia` (3 rows) and 221 actual districts |
| INSTN_NAME | 2,408 values |
| LABEL_LVL_3_DESC | `Teachers` (3,790) |
| LABEL_LVL_2_DESC | `Total` (2,506), `Low Poverty` (656), `High Poverty` (628) |

#### Suppression Markers — `TFS` only in 2021; pre-2021 has true zeros instead

| Year | `FTE` non-numeric | `OUTOFFIELD_FTE` non-numeric | `OUTOFFIELD_FTE_PCT` non-numeric | `OUTOFFIELD_FTE` true zeros |
|------|------|------|------|------|
| 2018 | none | none | none | 491 rows |
| 2019 | none | none | none | 418 rows |
| 2020 | none | none | none | 547 rows |
| 2021 | `TFS` (116) | `TFS` (3,158) | `TFS` (2,510) | 0 rows |

In 2018–2020 the data appears to have been published **without small-cell suppression**: every numeric value is reported, with `0` used when no emergency-credentialed teachers were present. Beginning with 2021, the GOSA reporting policy started masking values below 10 with the `TFS` token and the minimum reported numeric value jumps from `0` to `10`. This affects how `0` should be interpreted: in 2018–2020 it is a true zero, in 2021+ a `TFS` cell may also have been a true zero (information loss).

#### Year-by-year row counts

| Year | School rows | District rows | State rows | Total |
|------|-------------|---------------|-----------|-------|
| 2018 | 3,399 | 355 | 3 | 3,757 |
| 2019 | 3,396 | 360 | 3 | 3,759 |
| 2020 | 3,404 | 372 | 3 | 3,779 |
| 2021 | 3,413 | 374 | 3 | 3,790 |
| 2022 | 3,414 | 372 | 3 | 3,789 |
| 2023 | 3,483 | 314 | 3 | 3,800 |
| 2024 | 3,353 | 352 | 3 | 3,708 |

State rows are always 3 per year (one each for `Total`, `High Poverty`, `Low Poverty`). District rows = districts × poverty subgroups present.

## ETL Considerations

- **Era 3 column names are misleading.** In `2018.csv`–`2021.csv` the Emergency-credential metric is stored under columns named `OUTOFFIELD_FTE` and `OUTOFFIELD_FTE_PCT`. The transform must rename these to the unified Emergency metric and **not** treat them as out-of-field counts. Cross-checking against `educator_qualifications_out_of_field_teachers/` confirms the values differ; the column headers were re-used erroneously when GOSA first published the Emergency report.
- **Three column-name eras to harmonize.** Per era, the metric pair is:
  - Era 1 (2023–2024): `CATEGORY_FTE`, `CATEGORY_FTE_PCT` with `#CATEGORY_DESC = Emergency`
  - Era 2 (2022): `Emergency_FTE`, `Emergency_FTE_PCT`
  - Era 3 (2018–2021): `OUTOFFIELD_FTE`, `OUTOFFIELD_FTE_PCT` (mislabeled — see above)
  Map all three to a single gold metric pair (e.g., `emergency_fte` and `emergency_fte_pct`).
- **`#CATEGORY_DESC` is constant in this topic.** It always equals `Emergency` in the 2023–2024 files. Despite the topic name referencing "Provisional" credentials, no provisional rows exist in bronze. Do not propagate `#CATEGORY_DESC` as a fact_categorical column — drop it after verifying the constant.
- **`LABEL_LVL_3_DESC` is constant.** Always `Teachers`. Drop after verification.
- **`LABEL_LVL_2_DESC` is the poverty subgroup, not a demographic dimension.** Values are `Total`, `High Poverty`, `Low Poverty`. This is a fact_categorical column (e.g., `poverty_subgroup`) — it does **not** map to the global demographics dimension because the two non-`Total` values describe a school-poverty stratum, not a student demographic.
- **No district or school codes in source.** GOSA only provides district name (`SCHOOL_DSTRCT_NM`) and institution name (`INSTN_NAME`). The transform must look up `district_code` and `school_code` from the education dimensions (`data/gold/education/_dimensions/districts.parquet` and `schools.parquet`) by name. Plan for unmatched names — the dimension build script reads from other GOSA topics that include codes; expect occasional mismatches for renamed schools.
- **District-aggregate detection: `INSTN_NAME` ends with `- All Schools`.** When `INSTN_NAME == "<District>- All Schools"` the row is a district aggregate (set `school_code = NULL`). Beware: the suffix uses a regular hyphen with spaces (`- All Schools`), not a long dash, and the prefix exactly matches `SCHOOL_DSTRCT_NM`.
- **State-aggregate detection: `SCHOOL_DSTRCT_NM == "State of Georgia"` AND `INSTN_NAME == "All Georgia Schools"`.** Set both `district_code` and `school_code` to NULL. Always 3 state rows per year.
- **`TFS` suppression marker (Era 1, Era 2, and 2021).** Convert `TFS` → NULL via `pl.col(...).cast(pl.Float64, strict=False)`. The numeric reporting floor is 10 (any actual value <10 is masked).
- **Pre-2021 has no suppression — true zeros are present.** In `2018.csv`–`2020.csv`, values of `0` (in `OUTOFFIELD_FTE`) and `0` (in `OUTOFFIELD_FTE_PCT`) are real measurements, not suppressed. Hundreds of schools per year reported zero emergency-credentialed teachers. Do not coerce these zeros to NULL.
- **Percentage scale is 0–100.** `*_FTE_PCT` columns are integer percents (observed range when not suppressed: 0 in 2018–2020, 10–71 in 2021+). Per `data-cleaning-standards`, convert to 0–1 in gold by dividing by 100.
- **`FTE` is total teachers, including the High Poverty / Low Poverty subgroup denominator.** When `LABEL_LVL_2_DESC = Total`, `FTE` is total school FTE; when it is `High Poverty` or `Low Poverty`, `FTE` is the FTE in just that subgroup of schools. Carry `FTE` in gold so consumers can recompute weighted aggregates.
- **No duplicates.** Confirmed `(LONG_SCHOOL_YEAR, SCHOOL_DSTRCT_NM, INSTN_NAME, LABEL_LVL_3_DESC, LABEL_LVL_2_DESC)` is unique within each year file.
- **No nulls in any source column.** All cells are populated; suppression is encoded with the `TFS` string (Era 1/2 and 2021), and absence of the metric in pre-2021 is encoded with `0`.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| #CATEGORY_DESC | not_in_gold | — | Era 1 only; constant `Emergency`; verify and drop |
| LONG_SCHOOL_YEAR | fact_key | year | Convert `YYYY-YY` → ending calendar year as `pl.Int32` (e.g., `2023-24` → `2024`) |
| SCHOOL_DSTRCT_NM | fact_key (lookup source) | district_code | Lookup `district_code` in `districts.parquet` by `district_name`; NULL for state-level rows where `SCHOOL_DSTRCT_NM = "State of Georgia"` |
| SCHOOL_DSTRCT_NM | dimension_attribute | — | Already represented in `districts.district_name` |
| INSTN_NAME | fact_key (lookup source) | school_code | Lookup `school_code` in `schools.parquet` by `(district_code, school_name)`; NULL for district-aggregate rows (`<District>- All Schools`) and state-level rows (`All Georgia Schools`) |
| INSTN_NAME | dimension_attribute | — | Already represented in `schools.school_name` |
| LABEL_LVL_3_DESC | not_in_gold | — | Constant `Teachers`; verify and drop |
| LABEL_LVL_2_DESC | fact_categorical | poverty_subgroup | Values `total`, `high_poverty`, `low_poverty` (snake_case the source labels); not a global demographic |
| FTE | fact_metric | total_fte | Total teacher FTE in the entity/subgroup; `TFS` → NULL; cast to `pl.Float64` |
| OUTOFFIELD_FTE / Emergency_FTE / CATEGORY_FTE | fact_metric | emergency_fte | Unified emergency-credential FTE count across all 3 eras; `TFS` → NULL; cast to `pl.Float64`; preserve true `0` values from 2018–2020 |
| OUTOFFIELD_FTE_PCT / Emergency_FTE_PCT / CATEGORY_FTE_PCT | fact_metric | emergency_fte_pct | Unified emergency-credential percentage across all 3 eras; `TFS` → NULL; cast to `pl.Float64`; divide by 100 to put on 0–1 scale per `data-cleaning-standards` |
