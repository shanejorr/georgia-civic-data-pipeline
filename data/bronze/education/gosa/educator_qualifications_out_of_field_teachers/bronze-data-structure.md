# educator_qualifications_out_of_field_teachers — Bronze Data Structure

## Overview

- Topic: educator_qualifications_out_of_field_teachers
- Source: gosa
- Files: 7 CSV files spanning 2018–2024
- Unreadable files: none
- Year representation: `LONG_SCHOOL_YEAR` column in format `YYYY-YY` (e.g., `2023-24`); school year spanning two calendar years
- Filename-to-data year offset: filename year = ending calendar year of the school year (e.g., file `2024.csv` → school year `2023-24`, ending calendar year 2024)
- Detail levels: state, district, school
- Percentage scale: 0–100 (`OUTOFFIELD_FTE_PCT` / `CATEGORY_FTE_PCT`); values are stored as integers (rounded to whole percent)
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| educator_qualifications_out_of_field_teachers_2018.csv | 985661ade2a1a732a18c2fd34bca2591f27e3bf00489a7d8c6f12b88afe62f93 |
| educator_qualifications_out_of_field_teachers_2019.csv | b0c2b309f65b826eb2515caf80507bd2ce939406cdc9351605485295e5847d09 |
| educator_qualifications_out_of_field_teachers_2020.csv | 630ebd98fc064987361d70a6274fafd46976b3ed5c9c1f4bee23a1e2671de2b5 |
| educator_qualifications_out_of_field_teachers_2021.csv | f07a21ba04c35ee697ddc68bd6834ec106c9698720c379302f7bae78ab34fdb5 |
| educator_qualifications_out_of_field_teachers_2022.csv | 638e07ac9e204a12d882fbcd71852918436356f27772690b253a9e9147face44 |
| educator_qualifications_out_of_field_teachers_2023.csv | 51bbf9379f74a487037f2b84a64567525c7304ba37d3181527c59538a7114c28 |
| educator_qualifications_out_of_field_teachers_2024.csv | 7f7f914e47d3a49e1ac978ce286f10ee8994a2438175f6a1b70f872cc8ba55f0 |

## Summary

Tracks the count and percentage of teacher full-time equivalents (FTE) teaching **out of field** (i.e., assigned to a subject for which they are not certified) at each Georgia public school, district, and at the state level. Each row reports a total teacher FTE alongside an out-of-field FTE count and an integer 0–100 out-of-field percentage, broken down by school **poverty band** (Total, High Poverty, Low Poverty). The suppression marker `TFS` ("Too Few to Show") is used heavily — most school-level out-of-field counts and percentages are suppressed for privacy.

## Eras

### Era 1: 2023–2024

**Columns**: `#CATEGORY_DESC`, `LONG_SCHOOL_YEAR`, `SCHOOL_DSTRCT_NM`, `INSTN_NAME`, `LABEL_LVL_3_DESC`, `LABEL_LVL_2_DESC`, `FTE`, `CATEGORY_FTE`, `CATEGORY_FTE_PCT`

| Column | Description |
|--------|-------------|
| #CATEGORY_DESC | Category descriptor; constant value `Out_of_Field` for this topic. Leading `#` is part of the column name as published by GOSA. |
| LONG_SCHOOL_YEAR | School year in format `YYYY-YY` (e.g., `2023-24`) |
| SCHOOL_DSTRCT_NM | District name (e.g., `Fulton County`, `Atlanta Public Schools`); `State of Georgia` for state-level rows. The 2023 file (not 2024) also carries truncated placeholder labels `State Charter Schools ` / `State Charter Schools-`, and both 2023 and 2024 carry the 22-char truncation `Department of Juvenile` — see the year-over-year note below. |
| INSTN_NAME | Institution name; `All Georgia Schools` for state-level rows; `{District Name}- All Schools` for district-level aggregate rows |
| LABEL_LVL_3_DESC | Personnel level; constant value `Teachers` |
| LABEL_LVL_2_DESC | Poverty band: `Total`, `High Poverty`, `Low Poverty` |
| FTE | Total teacher FTE at the row's level/poverty band; numeric with `TFS` suppression |
| CATEGORY_FTE | Out-of-field teacher FTE (renamed from `OUTOFFIELD_FTE` in earlier eras); numeric with `TFS` suppression |
| CATEGORY_FTE_PCT | Out-of-field FTE as a percentage of total FTE (renamed from `OUTOFFIELD_FTE_PCT`); integer 0–100; numeric with `TFS` suppression |

#### Sample Data (2024 representative)

```
shape: (5, 9)
┌────────────────┬──────────────────┬───────────────────────┬──────────────────────────────────────────────────────┬──────────────────┬──────────────────┬───────┬──────────────┬──────────────────┐
│ #CATEGORY_DESC ┆ LONG_SCHOOL_YEAR ┆ SCHOOL_DSTRCT_NM      ┆ INSTN_NAME                                           ┆ LABEL_LVL_3_DESC ┆ LABEL_LVL_2_DESC ┆ FTE   ┆ CATEGORY_FTE ┆ CATEGORY_FTE_PCT │
╞════════════════╪══════════════════╪═══════════════════════╪══════════════════════════════════════════════════════╪══════════════════╪══════════════════╪═══════╪══════════════╪══════════════════╡
│ Out_of_Field   ┆ 2023-24          ┆ Peach County          ┆ Hunt Elementary School                               ┆ Teachers         ┆ Total            ┆ 42.5  ┆ TFS          ┆ 11               │
│ Out_of_Field   ┆ 2023-24          ┆ Dalton Public Schools ┆ Dalton Public Schools- All Schools                   ┆ Teachers         ┆ High Poverty     ┆ 276.1 ┆ TFS          ┆ TFS              │
│ Out_of_Field   ┆ 2023-24          ┆ White County          ┆ Tesnatee Gap Elementary (Old White Co. Intermediate) ┆ Teachers         ┆ Total            ┆ 34.3  ┆ TFS          ┆ TFS              │
│ Out_of_Field   ┆ 2023-24          ┆ Jones County          ┆ Gray Station Middle School                           ┆ Teachers         ┆ Total            ┆ 48.6  ┆ TFS          ┆ TFS              │
│ Out_of_Field   ┆ 2023-24          ┆ Oconee County         ┆ Malcom Bridge Elementary School                      ┆ Teachers         ┆ Low Poverty      ┆ 45    ┆ TFS          ┆ TFS              │
└────────────────┴──────────────────┴───────────────────────┴──────────────────────────────────────────────────────┴──────────────────┴──────────────────┴───────┴──────────────┴──────────────────┘
```

#### Statistics (2024 representative, numeric cast)

```
shape: (9, 10)
┌────────────┬────────────────┬──────────────────┬──────────────────┬──────────────────────────────┬──────────────────┬──────────────────┬─────────────┬──────────────┬──────────────────┐
│ statistic  ┆ #CATEGORY_DESC ┆ LONG_SCHOOL_YEAR ┆ SCHOOL_DSTRCT_NM ┆ INSTN_NAME                   ┆ LABEL_LVL_3_DESC ┆ LABEL_LVL_2_DESC ┆ FTE         ┆ CATEGORY_FTE ┆ CATEGORY_FTE_PCT │
╞════════════╪════════════════╪══════════════════╪══════════════════╪══════════════════════════════╪══════════════════╪══════════════════╪═════════════╪══════════════╪══════════════════╡
│ count      ┆ 3708           ┆ 3708             ┆ 3708             ┆ 3708                         ┆ 3708             ┆ 3708             ┆ 3613.0      ┆ 836.0        ┆ 1627.0           │
│ null_count ┆ 0              ┆ 0                ┆ 0                ┆ 0                            ┆ 0                ┆ 0                ┆ 95.0        ┆ 2872.0       ┆ 2081.0           │
│ mean       ┆ null           ┆ null             ┆ null             ┆ null                         ┆ null             ┆ null             ┆ 142.296928  ┆ 59.735167    ┆ 22.906577        │
│ std        ┆ null           ┆ null             ┆ null             ┆ null                         ┆ null             ┆ null             ┆ 2044.687724 ┆ 494.450383   ┆ 14.328508        │
│ min        ┆ Out_of_Field   ┆ 2023-24          ┆ Appling County   ┆ 7 Pillars Career Academy     ┆ Teachers         ┆ High Poverty     ┆ 10.0        ┆ 10.0         ┆ 10.0             │
│ 25%        ┆ null           ┆ null             ┆ null             ┆ null                         ┆ null             ┆ null             ┆ 35.3        ┆ 12.9         ┆ 13.0             │
│ 50%        ┆ null           ┆ null             ┆ null             ┆ null                         ┆ null             ┆ null             ┆ 47.8        ┆ 17.0         ┆ 19.0             │
│ 75%        ┆ null           ┆ null             ┆ null             ┆ null                         ┆ null             ┆ null             ┆ 68.0        ┆ 24.5         ┆ 27.0             │
│ max        ┆ Out_of_Field   ┆ 2023-24          ┆ Worth County     ┆ iGrad Virtual Academy School ┆ Teachers         ┆ Total            ┆ 113554.9    ┆ 13214.8      ┆ 98.0             │
└────────────┴────────────────┴──────────────────┴──────────────────┴──────────────────────────────┴──────────────────┴──────────────────┴─────────────┴──────────────┴──────────────────┘
```

(Source CSV columns are all read as strings to preserve `TFS` markers; the above table is produced after casting `FTE`, `CATEGORY_FTE`, `CATEGORY_FTE_PCT` to `Float64` with `strict=False` so that `TFS` becomes null. The raw string-typed `describe()` shows min/max as `10` and `TFS` respectively with mean/std/quartiles null.)

#### Null Counts (2024 representative)

```
shape: (1, 9)
┌────────────────┬──────────────────┬──────────────────┬────────────┬──────────────────┬──────────────────┬─────┬──────────────┬──────────────────┐
│ #CATEGORY_DESC ┆ LONG_SCHOOL_YEAR ┆ SCHOOL_DSTRCT_NM ┆ INSTN_NAME ┆ LABEL_LVL_3_DESC ┆ LABEL_LVL_2_DESC ┆ FTE ┆ CATEGORY_FTE ┆ CATEGORY_FTE_PCT │
╞════════════════╪══════════════════╪══════════════════╪════════════╪══════════════════╪══════════════════╪═════╪══════════════╪══════════════════╡
│ 0              ┆ 0                ┆ 0                ┆ 0          ┆ 0                ┆ 0                ┆ 0   ┆ 0            ┆ 0                │
└────────────────┴──────────────────┴──────────────────┴────────────┴──────────────────┴──────────────────┴─────┴──────────────┴──────────────────┘
```

No nulls in any column; all missing values are encoded as the string `TFS` in the three numeric columns.

#### Categorical Columns (2024 representative)

| Column | Distinct Values |
|--------|----------------|
| #CATEGORY_DESC | `Out_of_Field` (3,708) |
| LONG_SCHOOL_YEAR | `2023-24` (3,708) |
| SCHOOL_DSTRCT_NM | 182 values — county/city districts plus `State of Georgia` for the state aggregate |
| INSTN_NAME | 2,325 values — school names plus `All Georgia Schools` (state) and `{District}- All Schools` (district aggregates) |
| LABEL_LVL_3_DESC | `Teachers` (3,708) |
| LABEL_LVL_2_DESC | `Total` (2,426), `High Poverty` (660), `Low Poverty` (622) |

#### Suppression Markers (2024 representative)

| Column | Non-Numeric Values |
|--------|-------------------|
| FTE | `TFS` (95 occurrences, ~2.6% of rows) |
| CATEGORY_FTE | `TFS` (2,872 occurrences, ~77% of rows) |
| CATEGORY_FTE_PCT | `TFS` (2,081 occurrences, ~56% of rows) |

### Era 2: 2018–2022

**Columns**: `LONG_SCHOOL_YEAR`, `SCHOOL_DSTRCT_NM`, `INSTN_NAME`, `LABEL_LVL_3_DESC`, `LABEL_LVL_2_DESC`, `FTE`, `OUTOFFIELD_FTE`, `OUTOFFIELD_FTE_PCT`

Same semantic content as Era 1, but **without** the `#CATEGORY_DESC` column and with the metric columns named `OUTOFFIELD_FTE` / `OUTOFFIELD_FTE_PCT` (rather than `CATEGORY_FTE` / `CATEGORY_FTE_PCT`). Same measures — only the column names changed.

| Column | Description |
|--------|-------------|
| LONG_SCHOOL_YEAR | School year in format `YYYY-YY` (e.g., `2021-22`) |
| SCHOOL_DSTRCT_NM | District name; `State of Georgia` for state-level rows. 2018–2022 files also include special charter/state-school aggregator categories (e.g., `State Charter Schools- Georgia Connections Academy`, `State Charter Schools II- Academy For Classical Education`) that do NOT appear in 2023–2024. |
| INSTN_NAME | Institution name; `All Georgia Schools` for state-level rows; `{District Name}- All Schools` for district-level aggregate rows |
| LABEL_LVL_3_DESC | Personnel level; constant value `Teachers` |
| LABEL_LVL_2_DESC | Poverty band: `Total`, `High Poverty`, `Low Poverty` |
| FTE | Total teacher FTE; numeric with `TFS` suppression (2018–2021 files contain **zero** `TFS` markers in any column — verified by direct count; `TFS` first appears in the 2022 file: FTE 119, OUTOFFIELD_FTE 3,343, OUTOFFIELD_FTE_PCT 2,805 occurrences) |
| OUTOFFIELD_FTE | Out-of-field teacher FTE; numeric with `TFS` suppression |
| OUTOFFIELD_FTE_PCT | Out-of-field FTE as percentage of total FTE; integer 0–100; numeric with `TFS` suppression |

#### Sample Data (2022 representative)

```
shape: (5, 8)
┌──────────────────┬──────────────────┬──────────────────────────────┬──────────────────┬──────────────────┬───────┬────────────────┬────────────────────┐
│ LONG_SCHOOL_YEAR ┆ SCHOOL_DSTRCT_NM ┆ INSTN_NAME                   ┆ LABEL_LVL_3_DESC ┆ LABEL_LVL_2_DESC ┆ FTE   ┆ OUTOFFIELD_FTE ┆ OUTOFFIELD_FTE_PCT │
╞══════════════════╪══════════════════╪══════════════════════════════╪══════════════════╪══════════════════╪═══════╪════════════════╪════════════════════╡
│ 2021-22          ┆ Richmond County  ┆ Josey High School            ┆ Teachers         ┆ Total            ┆ 34.8  ┆ 12.3           ┆ 35                 │
│ 2021-22          ┆ Dawson County    ┆ Dawson County- All Schools   ┆ Teachers         ┆ Total            ┆ 231.4 ┆ TFS            ┆ TFS                │
│ 2021-22          ┆ Whitfield County ┆ Cedar Ridge Elementary       ┆ Teachers         ┆ Total            ┆ 26    ┆ TFS            ┆ TFS                │
│ 2021-22          ┆ Marion County    ┆ L. K. Moss Elementary School ┆ Teachers         ┆ Total            ┆ 36.4  ┆ TFS            ┆ TFS                │
│ 2021-22          ┆ Putnam County    ┆ Putnam County Middle School  ┆ Teachers         ┆ High Poverty     ┆ 54    ┆ TFS            ┆ 16                 │
└──────────────────┴──────────────────┴──────────────────────────────┴──────────────────┴──────────────────┴───────┴────────────────┴────────────────────┘
```

#### Statistics (2022 representative, numeric cast)

```
shape: (9, 9)
┌────────────┬──────────────────┬──────────────────┬──────────────────────────────┬──────────────────┬──────────────────┬────────────┬────────────────┬────────────────────┐
│ statistic  ┆ LONG_SCHOOL_YEAR ┆ SCHOOL_DSTRCT_NM ┆ INSTN_NAME                   ┆ LABEL_LVL_3_DESC ┆ LABEL_LVL_2_DESC ┆ FTE        ┆ OUTOFFIELD_FTE ┆ OUTOFFIELD_FTE_PCT │
╞════════════╪══════════════════╪══════════════════╪══════════════════════════════╪══════════════════╪══════════════════╪════════════╪════════════════╪════════════════════╡
│ count      ┆ 3789             ┆ 3789             ┆ 3789                         ┆ 3789             ┆ 3789             ┆ 3670.0     ┆ 446.0          ┆ 984.0              │
│ null_count ┆ 0                ┆ 0                ┆ 0                            ┆ 0                ┆ 0                ┆ 119.0      ┆ 3343.0         ┆ 2805.0             │
│ mean       ┆ null             ┆ null             ┆ null                         ┆ null             ┆ null             ┆ 127.192153 ┆ 53.854709      ┆ 22.197154          │
│ std        ┆ null             ┆ null             ┆ null                         ┆ null             ┆ null             ┆ 1856.69803 ┆ 339.801459     ┆ 14.005004          │
│ min        ┆ 2021-22          ┆ Appling County   ┆ 7 Pillars Career Academy     ┆ Teachers         ┆ High Poverty     ┆ 10.0       ┆ 10.0           ┆ 10.0               │
│ 25%        ┆ null             ┆ null             ┆ null                         ┆ null             ┆ null             ┆ 31.3       ┆ 12.1           ┆ 12.0               │
│ 50%        ┆ null             ┆ null             ┆ null                         ┆ null             ┆ null             ┆ 42.4       ┆ 15.1           ┆ 17.0               │
│ 75%        ┆ null             ┆ null             ┆ null                         ┆ null             ┆ null             ┆ 60.5       ┆ 20.6           ┆ 27.0               │
│ max        ┆ 2021-22          ┆ Worth County     ┆ iGrad Virtual Academy School ┆ Teachers         ┆ Total            ┆ 104530.4   ┆ 6509.1         ┆ 94.0               │
└────────────┴──────────────────┴──────────────────┴──────────────────────────────┴──────────────────┴──────────────────┴────────────┴────────────────┴────────────────────┘
```

#### Null Counts (2022 representative)

```
shape: (1, 8)
┌──────────────────┬──────────────────┬────────────┬──────────────────┬──────────────────┬─────┬────────────────┬────────────────────┐
│ LONG_SCHOOL_YEAR ┆ SCHOOL_DSTRCT_NM ┆ INSTN_NAME ┆ LABEL_LVL_3_DESC ┆ LABEL_LVL_2_DESC ┆ FTE ┆ OUTOFFIELD_FTE ┆ OUTOFFIELD_FTE_PCT │
╞══════════════════╪══════════════════╪════════════╪══════════════════╪══════════════════╪═════╪════════════════╪════════════════════╡
│ 0                ┆ 0                ┆ 0          ┆ 0                ┆ 0                ┆ 0   ┆ 0              ┆ 0                  │
└──────────────────┴──────────────────┴────────────┴──────────────────┴──────────────────┴─────┴────────────────┴────────────────────┘
```

No nulls in any column; all missing values are encoded as the string `TFS` in the three numeric columns.

#### Categorical Columns (2022 representative)

| Column | Distinct Values |
|--------|----------------|
| LONG_SCHOOL_YEAR | `2021-22` (3,789) |
| SCHOOL_DSTRCT_NM | 222 values — county/city districts plus `State of Georgia` and special aggregator categories such as `State Charter Schools- Georgia Connections Academy`, `State Charter Schools II- Academy For Classical Education`, `State Schools- Georgia School for the Deaf`, `Department of Juvenile Justice` |
| INSTN_NAME | 2,403 values — school names plus `All Georgia Schools` and `{District}- All Schools` |
| LABEL_LVL_3_DESC | `Teachers` (3,789) |
| LABEL_LVL_2_DESC | `Total` (2,502), `High Poverty` (656), `Low Poverty` (631) |

#### Suppression Markers (2022 representative)

| Column | Non-Numeric Values |
|--------|-------------------|
| FTE | `TFS` (119 occurrences, ~3% of rows) |
| OUTOFFIELD_FTE | `TFS` (3,343 occurrences, ~88% of rows) |
| OUTOFFIELD_FTE_PCT | `TFS` (2,805 occurrences, ~74% of rows) |

#### Year-over-year row counts and district counts

| File | Rows | Distinct districts |
|------|------|--------------------|
| 2018 | 3,757 | (same pattern — county/city + aggregators + state) |
| 2019 | 3,759 | (same pattern) |
| 2020 | 3,779 | (same pattern) |
| 2021 | 3,790 | 222 |
| 2022 | 3,789 | 222 |
| 2023 | 3,800 | 184 |
| 2024 | 3,708 | 182 |

Note the drop in distinct district count between 2022 and 2023: the **specific per-entity** charter/state-school aggregator labels (`State Charter Schools- {Entity}`, `State Charter Schools II- {Entity}`, `State Schools- Georgia School for the Deaf`) disappear from 2023 onward. They do **not** vanish entirely, however (correction 2026-06-11, verified by direct count): the 2023 file carries 152 charter/special rows under three **truncated** labels — `Department of Juvenile` (14 rows; 22-char truncation of `Department of Juvenile Justice`), `State Charter Schools ` (96 rows, trailing space), and `State Charter Schools-` (42 rows, trailing dash) — where the two generic `State Charter Schools` placeholders mix bare school names, container-prefixed 52-char-truncated school names, and truncated `...- All Sc` district-aggregate forms in `INSTN_NAME`. The 2024 file carries 12 rows under `Department of Juvenile` and no charter placeholders.

## ETL Considerations

- **NO DISTRICT OR SCHOOL ID COLUMNS IN BRONZE.** Unlike most GOSA files, this dataset has no `SCHOOL_DSTRCT_CD` or `INSTN_NUMBER` columns — only `SCHOOL_DSTRCT_NM` and `INSTN_NAME`. The transform must **join to the existing `data/gold/education/_dimensions/districts.parquet` and `schools.parquet` dimension tables by name** to recover the codes required for fact-table FK columns. Be aware that:
  - Some districts have name variants between bronze and the dimension table (e.g., punctuation, capitalization, or `City`/`County` suffixes). Build a normalized join key and/or maintain an override map.
  - The schools dimension is keyed by `(school_code, district_code)`; school names are not globally unique, so join on `(district_name → district_code)` first, then `(school_name + district_code → school_code)`.
  - Expect a small number of unmatched rows (especially special-program schools and charter aggregators in Era 2). Log unmatched names so they can be added to district/school name overrides.
- **Era column changes**:
  - Era 1 (2023–2024) adds a new constant `#CATEGORY_DESC` column (always `Out_of_Field`; safe to drop). The leading `#` is part of the column name — access it as `df["#CATEGORY_DESC"]`.
  - Era 1 renames `OUTOFFIELD_FTE` → `CATEGORY_FTE` and `OUTOFFIELD_FTE_PCT` → `CATEGORY_FTE_PCT`. **Same metric, just renamed.** The transform must standardize these to a single gold column name regardless of era.
- **Suppression handling**: All three numeric columns (`FTE`, `OUTOFFIELD_FTE`/`CATEGORY_FTE`, `OUTOFFIELD_FTE_PCT`/`CATEGORY_FTE_PCT`) use `TFS` ("Too Few to Show") as the only suppression marker. Cast with `pl.col(...).cast(pl.Float64, strict=False)` so `TFS` becomes null. The out-of-field metrics have very high suppression rates (60–90% of school-level rows) while `FTE` itself is rarely suppressed (~3%).
- **Detail-level detection**:
  - State rows: `SCHOOL_DSTRCT_NM == "State of Georgia"` AND `INSTN_NAME == "All Georgia Schools"`.
  - District rows: `INSTN_NAME` matches the pattern `"{district_name}- All Schools"` (note the `-` immediately followed by a space, no space before the `-`).
  - All other rows are school-level.
- **Charter / state-school aggregator rows in Era 2**: 2018–2022 files include synthetic district names like `State Charter Schools- Georgia Connections Academy`, `State Charter Schools II- Academy For Classical Education`, `State Schools- Georgia School for the Deaf`, and `Department of Juvenile Justice`. These act as "districts" for individual statewide charters or state schools. Decide whether to:
  1. Map them to their underlying district code in the dimension table (preferred for consistency), or
  2. Drop them (acceptable if the underlying schools also appear as standalone rows).
  The specific per-entity labels do NOT appear in 2023 or 2024 — but truncated successors DO (correction 2026-06-11): 2023 has `Department of Juvenile` (14 rows), `State Charter Schools ` (96 rows), and `State Charter Schools-` (42 rows); 2024 has `Department of Juvenile` (12 rows). `Department of Juvenile` expands to `Department of Juvenile Justice` (a real dimension district); the two generic `State Charter Schools` placeholders require per-school rescue by `INSTN_NAME` (bare school names resolve; truncated container-prefixed and `...- All Sc` aggregate forms that cannot be rescued are redundant republications of the bare school rows and are dropped).
- **Constant columns to drop**: `#CATEGORY_DESC` (always `Out_of_Field`) and `LABEL_LVL_3_DESC` (always `Teachers`) carry no information and should be dropped from gold.
- **`LABEL_LVL_2_DESC` is a poverty band, not a demographic**: This column splits data by school poverty level (`Total`, `High Poverty`, `Low Poverty`) — it is NOT a student demographic in the standard sense (race, gender, etc.). Map this to a topic-specific `poverty_band` fact categorical column rather than the global `demographic` FK. Note: school-level rows can appear with `High Poverty` and `Low Poverty`; district and state rows can also appear with all three bands (verify exact breakdowns per level during transform).
- **Year representation**: `LONG_SCHOOL_YEAR` is `YYYY-YY` (school year). Convert to `Int32` ending calendar year (e.g., `2023-24` → `2024`) per education domain conventions.
- **Percentage scale**: `OUTOFFIELD_FTE_PCT` / `CATEGORY_FTE_PCT` are integers on the 0–100 scale (rounded — e.g., an actual ratio of 11.3% is stored as `11`). Per data-cleaning standards, decide whether to convert to 0–1 scale during transform.
- **Header quoting and `#` prefix**: Era 2 files use double-quoted headers; Era 1 files use unquoted headers and the first column header literally starts with `#` (`#CATEGORY_DESC`). Polars reads both by default. When reading Era 1 files with `pl.read_csv`, pass `comment_prefix=None` (or any value other than `#`) so polars does not interpret the header row as a comment line. Use `infer_schema_length=0` (or explicit string overrides) to preserve the `TFS` markers.
- **No true nulls** — all "missing" values are the string `TFS` in numeric columns, never actual nulls.

## Known Anomalies

- **2018–2021 `OUTOFFIELD_FTE = "0"` zero-spike (out-of-field counts only):** Bronze files for 2018–2021 contain unusually high concentrations of literal `"0"` in `OUTOFFIELD_FTE` at the school level — a pattern that vanishes from 2022 onward when explicit `TFS` suppression begins appearing on roughly 88% of school-level rows. Year-by-year breakdown (school-level rows; `OUTOFFIELD_FTE` only):

  | Year | School-level rows | exact `0` | values in `(0, 1)` | `TFS` |
  |------|------------------:|----------:|-------------------:|------:|
  | 2018 | 3,399             | 98 (2.9%) | 206                | 0     |
  | 2019 | 3,396             | 111 (3.3%)| 221                | 0     |
  | 2020 | 3,404             | 1,645 (48%) | 86               | 0     |
  | 2021 | 3,413             | 616 (18%) | 704                | 0     |
  | 2022+| —                 | 0         | —                  | ~88%  |

  GOSA did not publish a suppression-policy change at this transition. We cannot mechanically distinguish "true zero out-of-field teachers" from "suppression encoded as `0`": the 2018–2019 zero rates around 3% are plausibly real, but the 2020 48% rate is implausibly high and almost certainly reflects an undocumented suppression encoding. We preserve bronze fidelity — every `0` in `OUTOFFIELD_FTE` passes through to gold as a literal `0.0` (no override). **Downstream analysts should handle 2018–2021 `out_of_field_fte = 0` rows explicitly** (e.g., exclude or treat as suppressed) when interpreting school-level out-of-field counts in those years; aggregates that include 2020 will be biased toward zero unless this is addressed.

- **2023 duplicate bronze name key with divergent metrics (added 2026-06-11):** the 2023 file publishes TWO rows with the identical key (`SCHOOL_DSTRCT_NM='State Charter Schools '`, `INSTN_NAME='State Charter Schools II- Genesis Innovation Academy'`, `LABEL_LVL_2_DESC='Total'`) carrying different values — (FTE 31.1, OUTOFFIELD 20.3, 65%) vs (29.6, 23.3, 79%). These are the Genesis Innovation Academy **for Boys** (7830615) and **for Girls** (7830616) campuses whose distinguisher was erased by GOSA's 52-char `INSTN_NAME` truncation. No single dimension target can faithfully receive either row; the 2023 file separately publishes both campuses under their bare school names with the same metrics (Boys 7830615/0615 = 31.1/20.3/65; Girls 7830616/0616 = 29.6/23.3/79), and both bare-name rows reach gold — so the transform drops the redundant truncated pair under the placeholder-container predicate (manifest-recorded, lossless).

- **Rate vs FTE inconsistency at tiny programs, 2018–2021 (added 2026-06-11):** 26 rows with `FTE < 3` publish an integer percent that deviates from `OUTOFFIELD_FTE / FTE` by up to 0.57 (e.g. Evans County "Second Chance" 2020: 1.0 / 1.0 published as 50%; Bleckley County Success Academy 2020: 0.8 / 0.8 published as 43%). GOSA evidently computes the percent from unrounded FTE values, and at this scale the 0.1-FTE rounding dominates. For rows with `FTE >= 3` the worst deviation across all years is 0.0124. All published values pass through to gold unchanged.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| #CATEGORY_DESC | not_in_gold | — | Constant `Out_of_Field`; carries no information |
| LONG_SCHOOL_YEAR | fact_key | year | Convert `YYYY-YY` → `Int32` ending calendar year (e.g., `2023-24` → `2024`) |
| SCHOOL_DSTRCT_NM | fact_key | district_code | Resolve via name-join to `data/gold/education/_dimensions/districts.parquet`; `State of Georgia` → NULL; zfill(3) on resolved code. In Era 2 also handle charter/state-school aggregator names. |
| INSTN_NAME | fact_key | school_code | Resolve via composite name-join to `data/gold/education/_dimensions/schools.parquet` (match on `(district_code, school_name)`); `All Georgia Schools` and `{District}- All Schools` indicate aggregate rows where `school_code` is NULL; zfill(4) on resolved code |
| LABEL_LVL_3_DESC | not_in_gold | — | Constant `Teachers`; carries no information |
| LABEL_LVL_2_DESC | fact_categorical | poverty_subgroup | Values: `Total`, `High Poverty`, `Low Poverty`; recode to `total`, `high_poverty`, `low_poverty` (snake_case) per data-cleaning standards. (Gold name corrected 2026-06-11 to match the published v1/v2 contract — was suggested as `poverty_band` here, never adopted.) |
| FTE | fact_metric | total_fte | Float64; total teacher FTE at the row's level/poverty subgroup; `TFS` → null. (Published gold name is `total_fte`, not `total_teacher_fte`.) |
| OUTOFFIELD_FTE / CATEGORY_FTE | fact_metric | out_of_field_fte | Float64; same metric across both eras (renamed in Era 1); `TFS` → null |
| OUTOFFIELD_FTE_PCT / CATEGORY_FTE_PCT | fact_metric | out_of_field_fte_rate | Float64; bronze 0–100 integer divided by 100 onto the 0–1 scale per §4. (Published gold name is `out_of_field_fte_rate`, not `out_of_field_pct`.) |

**Detail-level derivation** (no bronze column maps directly to detail level — derive in transform):

| Bronze pattern | detail_level |
|----------------|--------------|
| `SCHOOL_DSTRCT_NM == "State of Georgia"` AND `INSTN_NAME == "All Georgia Schools"` | `state` |
| `INSTN_NAME` ends with `"- All Schools"` (and not state-level) | `district` |
| Otherwise | `school` |
