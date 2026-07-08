# educator_qualifications_inexperienced_teachers_leaders — Bronze Data Structure

## Overview

- Topic: educator_qualifications_inexperienced_teachers_leaders
- Source: gosa
- Files: 7 CSV files spanning 2018–2024
- Unreadable files: none
- Year representation: `LONG_SCHOOL_YEAR` column in format `YYYY-YY` (e.g., `2023-24`); school year spanning two calendar years
- Filename-to-data year offset: filename year = ending year of school year (e.g., file `2024` → data year `2023-24`)
- Detail levels: state, district, school
- Percentage scale: 0–100 (the `*_FTE_PCT` columns are integer percents; observed range 0 in 2018–2020 and 10–100 in 2021+ when not suppressed)
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| educator_qualifications_inexperienced_teachers_leaders_2018.csv | a747fd546acaa3942c9c4a692e5cd6da162554e8aa310581a9018a8eaeb02131 |
| educator_qualifications_inexperienced_teachers_leaders_2019.csv | f939905dcf355690874c374cda08b31b07746f27564dc4ad0754587088303029 |
| educator_qualifications_inexperienced_teachers_leaders_2020.csv | 2fb1dde66bc712311c72b3fd5f07faf65a76b50935f102e260441708bc8517f7 |
| educator_qualifications_inexperienced_teachers_leaders_2021.csv | 29b0ea7e26ec9853857ac3c5272c0d0226bfb7734a2f0db38143e0ee7669fe0c |
| educator_qualifications_inexperienced_teachers_leaders_2022.csv | d5470e5fe6aae84db3f5edad82fe44909ca025c1cd6ad07917c17a0cb68bb219 |
| educator_qualifications_inexperienced_teachers_leaders_2023.csv | 170a70b9efec3751bd700d100bc885a5e9fa008daa006175d410e46d347e703f |
| educator_qualifications_inexperienced_teachers_leaders_2024.csv | b2491c87bf522233c008ee3288c0a54658543d4b755098ef79e346069b21e463 |

## Summary

Reports the count and percentage of educator full-time equivalents (FTE) classified as **Inexperienced** at each Georgia public school, district, and state-wide. Inexperienced educators are those within the first few years of their career (the exact GOSA threshold is not documented in the CSV payload, but typically <3 years of experience). This dataset differs from the sibling `educator_qualifications_emergency_and_provisional_credentials` and `educator_qualifications_out_of_field_teachers` topics in two important ways: (1) it reports both **Teachers** and **Leaders** (principals/assistant principals), where the sibling topics only report Teachers, and (2) the Leaders workforce introduces two extra poverty-subgroup values (`Not Applicable` and `Unknown`) that never appear for Teachers. Each row provides the total FTE at the entity (or aggregate), the FTE of those educators who are Inexperienced, and that count expressed as an integer percentage of total FTE. The dataset is school-year-based (2017–18 through 2023–24).

## Eras

### Era 1: 2023–2024

**Columns**: `#CATEGORY_DESC`, `LONG_SCHOOL_YEAR`, `SCHOOL_DSTRCT_NM`, `INSTN_NAME`, `LABEL_LVL_3_DESC`, `LABEL_LVL_2_DESC`, `FTE`, `CATEGORY_FTE`, `CATEGORY_FTE_PCT`

| Column | Description |
|--------|-------------|
| #CATEGORY_DESC | Qualification category being measured; constant `Inexperienced` in this topic |
| LONG_SCHOOL_YEAR | School year in format `YYYY-YY` (e.g., `2023-24`) |
| SCHOOL_DSTRCT_NM | District name; `State of Georgia` for state-level rows |
| INSTN_NAME | Institution name; `<District>- All Schools` for district aggregates; `All Georgia Schools` for state aggregates |
| LABEL_LVL_3_DESC | Workforce role: `Teachers` or `Leaders` |
| LABEL_LVL_2_DESC | Poverty subgroup: `Total`, `High Poverty`, `Low Poverty`, plus `Not Applicable` and `Unknown` (Leaders only) |
| FTE | Total educator FTE in the entity for the given role and poverty subgroup (numeric, may be `TFS`) |
| CATEGORY_FTE | Educator FTE classified as Inexperienced (numeric, may be `TFS`) |
| CATEGORY_FTE_PCT | `CATEGORY_FTE` as a percentage of `FTE`, integer 10–100 (numeric, may be `TFS`) |

#### Sample Data (2024)

```
shape: (5, 9)
┌────────────────┬──────────────────┬──────────────────┬───────────────────────────────┬──────────────────┬──────────────────┬──────┬──────────────┬──────────────────┐
│ #CATEGORY_DESC ┆ LONG_SCHOOL_YEAR ┆ SCHOOL_DSTRCT_NM ┆ INSTN_NAME                    ┆ LABEL_LVL_3_DESC ┆ LABEL_LVL_2_DESC ┆ FTE  ┆ CATEGORY_FTE ┆ CATEGORY_FTE_PCT │
╞════════════════╪══════════════════╪══════════════════╪═══════════════════════════════╪══════════════════╪══════════════════╪══════╪══════════════╪══════════════════╡
│ Inexperienced  ┆ 2023-24          ┆ Gwinnett County  ┆ Mason Elementary School       ┆ Teachers         ┆ Low Poverty      ┆ 65.5 ┆ 33           ┆ 50               │
│ Inexperienced  ┆ 2023-24          ┆ Barrow County    ┆ Holsenbeck Elementary School  ┆ Teachers         ┆ Total            ┆ 58.2 ┆ 28.1         ┆ 48               │
│ Inexperienced  ┆ 2023-24          ┆ Houston County   ┆ Morningside Elementary School ┆ Teachers         ┆ Total            ┆ 34   ┆ 13           ┆ 38               │
│ Inexperienced  ┆ 2023-24          ┆ Gwinnett County  ┆ Chesney Elementary School     ┆ Teachers         ┆ Total            ┆ 73   ┆ 44.5         ┆ 61               │
│ Inexperienced  ┆ 2023-24          ┆ Coweta County    ┆ Arnall Middle School          ┆ Teachers         ┆ Total            ┆ 48   ┆ 19           ┆ 40               │
└────────────────┴──────────────────┴──────────────────┴───────────────────────────────┴──────────────────┴──────────────────┴──────┴──────────────┴──────────────────┘
```

#### Statistics (2024)

```
shape: (9, 10)
┌────────────┬────────────────┬──────────────────┬──────────────────┬──────────────────────────────┬──────────────────┬──────────────────┬──────┬──────────────┬──────────────────┐
│ statistic  ┆ #CATEGORY_DESC ┆ LONG_SCHOOL_YEAR ┆ SCHOOL_DSTRCT_NM ┆ INSTN_NAME                   ┆ LABEL_LVL_3_DESC ┆ LABEL_LVL_2_DESC ┆ FTE  ┆ CATEGORY_FTE ┆ CATEGORY_FTE_PCT │
╞════════════╪════════════════╪══════════════════╪══════════════════╪══════════════════════════════╪══════════════════╪══════════════════╪══════╪══════════════╪══════════════════╡
│ count      ┆ 6462           ┆ 6462             ┆ 6462             ┆ 6462                         ┆ 6462             ┆ 6462             ┆ 6462 ┆ 6462         ┆ 6462             │
│ null_count ┆ 0              ┆ 0                ┆ 0                ┆ 0                            ┆ 0                ┆ 0                ┆ 0    ┆ 0            ┆ 0                │
│ min        ┆ Inexperienced  ┆ 2023-24          ┆ Appling County   ┆ 7 Pillars Career Academy     ┆ Leaders          ┆ High Poverty     ┆ 10   ┆ 10           ┆ 10               │
│ max        ┆ Inexperienced  ┆ 2023-24          ┆ Worth County     ┆ iGrad Virtual Academy School ┆ Teachers         ┆ Unknown          ┆ TFS  ┆ TFS          ┆ TFS              │
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
| #CATEGORY_DESC | `Inexperienced` (6,462) — constant for this topic |
| LONG_SCHOOL_YEAR | `2023-24` (6,462) |
| SCHOOL_DSTRCT_NM | 184 values including `State of Georgia` (6 rows), `Department of Juvenile` (18 rows), and 182 actual districts |
| INSTN_NAME | 2,417 values: 2,236 individual schools plus aggregate names `<District>- All Schools` (one per district) and `All Georgia Schools` (6 state-level rows) |
| LABEL_LVL_3_DESC | `Teachers` (3,708), `Leaders` (2,754) |
| LABEL_LVL_2_DESC | `Total` (2,645), `High Poverty` (1,362), `Low Poverty` (1,303), `Not Applicable` (1,145, Leaders only), `Unknown` (7, Leaders at Department of Juvenile facilities) |

#### Suppression Markers (2024)

| Column | Non-Numeric Values |
|--------|-------------------|
| FTE | `TFS` (2,649 rows) |
| CATEGORY_FTE | `TFS` (3,096 rows) |
| CATEGORY_FTE_PCT | `TFS` (690 rows) |

`TFS` = "Too Few Students/Staff to report." Numeric values in all three columns are bounded below by 10 (the GOSA reporting floor); the `CATEGORY_FTE_PCT` column is an integer percent on a 0–100 scale.

### Era 2: 2018–2022

**Columns**: `LONG_SCHOOL_YEAR`, `SCHOOL_DSTRCT_NM`, `INSTN_NAME`, `LABEL_LVL_3_DESC`, `LABEL_LVL_2_DESC`, `FTE`, `INEXPERIENCED_FTE`, `INEXPERIENCED_FTE_PCT`

Same fact data as Era 1, but the qualification category is encoded directly in the **column name** (`INEXPERIENCED_FTE` / `INEXPERIENCED_FTE_PCT`) instead of a `#CATEGORY_DESC` row dimension. The leading `#CATEGORY_DESC` column does not exist in this era.

| Column | Description |
|--------|-------------|
| LONG_SCHOOL_YEAR | School year (`2017-18` through `2021-22`) |
| SCHOOL_DSTRCT_NM | District name; `State of Georgia` for state-level rows |
| INSTN_NAME | Institution name; `<District>- All Schools` for district aggregates; `All Georgia Schools` for state aggregates |
| LABEL_LVL_3_DESC | Workforce role: `Teachers` or `Leaders` |
| LABEL_LVL_2_DESC | Poverty subgroup: `Total`, `High Poverty`, `Low Poverty`, plus `Not Applicable` and `Unknown` (Leaders only) |
| FTE | Total educator FTE in the entity for the given role and poverty subgroup (numeric; `TFS` only in 2021–2022, true zeros in 2018–2020) |
| INEXPERIENCED_FTE | Educator FTE classified as Inexperienced (numeric; `TFS` only in 2021–2022, true zeros in 2018–2020) |
| INEXPERIENCED_FTE_PCT | `INEXPERIENCED_FTE` as a percentage of total `FTE`, integer 0–100 (numeric; `TFS` only in 2021–2022, true zeros in 2018–2020) |

#### Sample Data (2022 — representative)

```
shape: (5, 8)
┌──────────────────┬─────────────────────────┬──────────────────────────────────┬──────────────────┬──────────────────┬──────┬───────────────────┬───────────────────────┐
│ LONG_SCHOOL_YEAR ┆ SCHOOL_DSTRCT_NM        ┆ INSTN_NAME                       ┆ LABEL_LVL_3_DESC ┆ LABEL_LVL_2_DESC ┆ FTE  ┆ INEXPERIENCED_FTE ┆ INEXPERIENCED_FTE_PCT │
╞══════════════════╪═════════════════════════╪══════════════════════════════════╪══════════════════╪══════════════════╪══════╪═══════════════════╪═══════════════════════╡
│ 2021-22          ┆ Paulding County         ┆ Paulding County High School      ┆ Leaders          ┆ Not Applicable   ┆ TFS  ┆ TFS               ┆ 17                    │
│ 2021-22          ┆ Decatur County          ┆ Jones-Wheat Elementary School    ┆ Teachers         ┆ Total            ┆ 39.6 ┆ 15.6              ┆ 39                    │
│ 2021-22          ┆ Elbert County           ┆ Elbert County- All Schools       ┆ Leaders          ┆ Low Poverty      ┆ TFS  ┆ TFS               ┆ TFS                   │
│ 2021-22          ┆ Clarke County           ┆ Cleveland Road Elementary School ┆ Teachers         ┆ Total            ┆ 23.8 ┆ 10.8              ┆ 45                    │
│ 2021-22          ┆ Savannah-Chatham County ┆ Johnson High School              ┆ Leaders          ┆ Not Applicable   ┆ TFS  ┆ TFS               ┆ 57                    │
└──────────────────┴─────────────────────────┴──────────────────────────────────┴──────────────────┴──────────────────┴──────┴───────────────────┴───────────────────────┘
```

#### Statistics (2022 — representative)

```
shape: (9, 9)
┌────────────┬──────────────────┬──────────────────┬──────────────────────────────┬──────────────────┬──────────────────┬──────┬───────────────────┬───────────────────────┐
│ statistic  ┆ LONG_SCHOOL_YEAR ┆ SCHOOL_DSTRCT_NM ┆ INSTN_NAME                   ┆ LABEL_LVL_3_DESC ┆ LABEL_LVL_2_DESC ┆ FTE  ┆ INEXPERIENCED_FTE ┆ INEXPERIENCED_FTE_PCT │
╞════════════╪══════════════════╪══════════════════╪══════════════════════════════╪══════════════════╪══════════════════╪══════╪═══════════════════╪═══════════════════════╡
│ count      ┆ 6460             ┆ 6460             ┆ 6460                         ┆ 6460             ┆ 6460             ┆ 6460 ┆ 6460              ┆ 6460                  │
│ null_count ┆ 0                ┆ 0                ┆ 0                            ┆ 0                ┆ 0                ┆ 0    ┆ 0                 ┆ 0                     │
│ min        ┆ 2021-22          ┆ Appling County   ┆ 7 Pillars Career Academy     ┆ Leaders          ┆ High Poverty     ┆ 10   ┆ 10                ┆ 10                    │
│ max        ┆ 2021-22          ┆ Worth County     ┆ iGrad Virtual Academy School ┆ Teachers         ┆ Unknown          ┆ TFS  ┆ TFS               ┆ TFS                   │
└────────────┴──────────────────┴──────────────────┴──────────────────────────────┴──────────────────┴──────────────────┴──────┴───────────────────┴───────────────────────┘
```

(`mean`, `std`, and quartile rows are all `null` because every column is read as `Utf8` due to `TFS` suppression markers in 2021–2022. Even in 2018–2020 files where no suppression tokens are present, Polars can still infer `Utf8` for the FTE columns depending on the mixture of integer and decimal values.)

#### Null Counts (2022 — representative)

```
shape: (1, 8)
All columns: 0 nulls
```

#### Categorical Columns (2022 — representative)

| Column | Distinct Values |
|--------|----------------|
| LONG_SCHOOL_YEAR | `2021-22` (6,460) |
| SCHOOL_DSTRCT_NM | 222 values including `State of Georgia` (6 rows), `Department of Juvenile` (19 rows), and 220 actual districts |
| INSTN_NAME | 2,412 values: individual schools plus `<District>- All Schools` and `All Georgia Schools` aggregates |
| LABEL_LVL_3_DESC | `Teachers` (3,789), `Leaders` (2,671) |
| LABEL_LVL_2_DESC | `Total` (2,722), `High Poverty` (1,307), `Low Poverty` (1,284), `Not Applicable` (1,140, Leaders only), `Unknown` (7, Leaders only) |

#### Suppression Markers — `TFS` only in 2021–2022; 2018–2020 has true zeros instead

| Year | `FTE` non-numeric | `INEXPERIENCED_FTE` non-numeric | `INEXPERIENCED_FTE_PCT` non-numeric | `INEXPERIENCED_FTE` true zeros | `INEXPERIENCED_FTE_PCT` true zeros |
|------|-------------------|----------------------------------|--------------------------------------|--------------------------------|------------------------------------|
| 2018 | none | none | none | 723 rows | 723 rows |
| 2019 | none | none | none | 757 rows | 756 rows |
| 2020 | none | none | none | 765 rows | 765 rows |
| 2021 | `TFS` (2,585) | `TFS` (3,178) | `TFS` (884) | 0 rows | 0 rows |
| 2022 | `TFS` (2,597) | `TFS` (3,415) | `TFS` (957) | 0 rows | 0 rows |

In 2018–2020 the data appears to have been published **without small-cell suppression**: every numeric value is reported, with `0` used when no Inexperienced educators were present. Beginning with 2021, the GOSA reporting policy started masking values below 10 with the `TFS` token and the minimum reported numeric value jumps from `0` to `10`. This affects how `0` should be interpreted: in 2018–2020 it is a true zero; a 2021+ `TFS` cell could have been a true zero or any value 1–9 (information loss).

Note: `INEXPERIENCED_FTE` was reported as `CATEGORICAL` by the column-classification script for 2022 because >50% of rows carry the `TFS` marker (3,415 of 6,460 ≈ 53%). The sole non-numeric value across all years is still `TFS`, so treat it as a suppression marker in the transform regardless of how the heuristic classifies it.

#### Year-by-year row counts

| Year | School rows | District rows | State rows | Total | Distinct districts | Distinct schools |
|------|-------------|---------------|------------|-------|--------------------|------------------|
| 2018 | 5,678 | 711 | 6 | 6,395 | 207 | 2,184 |
| 2019 | 5,677 | 744 | 6 | 6,427 | 211 | 2,186 |
| 2020 | 5,683 | 746 | 6 | 6,435 | 215 | 2,184 |
| 2021 | 5,695 | 747 | 6 | 6,448 | 221 | 2,189 |
| 2022 | 5,703 | 751 | 6 | 6,460 | 219 | 2,192 |
| 2023 | 5,842 | 637 | 6 | 6,485 | 181 | 2,236 |
| 2024 | 5,712 | 744 | 6 | 6,462 | 180 | 2,236 |

State rows are always 6 per year (2 roles × 3 poverty subgroups: `Total`, `High Poverty`, `Low Poverty`). For Leaders, additional rows exist at the school/district level under `Not Applicable` and `Unknown` poverty values.

## ETL Considerations

- **Two column-name eras to harmonize.** Per era, the metric pair is:
  - Era 1 (2023–2024): `CATEGORY_FTE`, `CATEGORY_FTE_PCT` with `#CATEGORY_DESC = Inexperienced`
  - Era 2 (2018–2022): `INEXPERIENCED_FTE`, `INEXPERIENCED_FTE_PCT`

  Map both to a single gold metric pair (e.g., `inexperienced_fte` and `inexperienced_fte_pct`). Unlike the sibling `educator_qualifications_emergency_and_provisional_credentials` topic, there is **no mislabeled-column era** here — the Era 2 column names accurately describe the metric.

- **`#CATEGORY_DESC` is constant in this topic.** It always equals `Inexperienced` in the 2023–2024 files. Do not propagate it as a fact_categorical column — drop it after verifying the constant.

- **Two values in `LABEL_LVL_3_DESC` — keep as a fact_categorical.** Unlike the parallel emergency/out-of-field topics (which are Teachers-only), this topic reports both `Teachers` and `Leaders`. Retain the role as a fact_categorical column (e.g., `role`) with values `teachers` and `leaders` (snake_case). This is critical — the row count is ~6,400, which is ~70% larger than the ~3,800 in emergency/out-of-field topics precisely because Leaders rows are included.

- **`LABEL_LVL_2_DESC` has five values, not three — `Not Applicable` and `Unknown` apply to Leaders only.** Teachers rows carry only `Total`, `High Poverty`, or `Low Poverty`. Leaders rows additionally carry `Not Applicable` (the dominant value — 1,137–1,145 rows per year, roughly one per school/district with Leaders data) and `Unknown` (6–7 rows per year, always associated with the `Department of Juvenile` district's youth-development-campus schools). Do not filter these out — they represent real coverage, especially `Not Applicable` which is the most common poverty value for Leaders. Normalize to `total`, `high_poverty`, `low_poverty`, `not_applicable`, `unknown`.

- **`LABEL_LVL_2_DESC` is a poverty subgroup, not a demographic.** Values are about school-poverty strata, not student demographics. This is a fact_categorical column (e.g., `poverty_subgroup`) — it does **not** map to the global demographics dimension.

- **No district or school codes in source.** GOSA only provides district name (`SCHOOL_DSTRCT_NM`) and institution name (`INSTN_NAME`). The transform must look up `district_code` and `school_code` from the education dimensions (`data/gold/education/_dimensions/districts.parquet` and `schools.parquet`) by name. Plan for unmatched names — the dimension build script reads from other GOSA topics that include codes; expect occasional mismatches for renamed schools or for `Department of Juvenile` facilities.

- **District-aggregate detection: `INSTN_NAME` contains `- All Schools`.** When `INSTN_NAME == "<District>- All Schools"` the row is a district aggregate (set `school_code = NULL`). Beware: the suffix uses a regular hyphen with a space before it (`- All Schools`), not a long dash, and the prefix exactly matches `SCHOOL_DSTRCT_NM`. The `str.contains(r'- All Schools')` pattern is reliable **only through 2022**. *(Amended 2026-06-11 with run evidence:)* the 2023–2024 files truncate `INSTN_NAME` at exactly 52 characters and truncate the charter-container district label to a generic placeholder (`"State Charter Schools "` / `"State Charter Schools-"`). For state-charter district aggregates this cuts the `- All Schools` suffix partially (e.g. `"State Charter Schools II- Atlanta Unbound Academy- A"`; 38 rows in 2023, 20 in 2024) or entirely, mid-entity-name (e.g. `"State Charter Schools II- Atlanta Heights Charter Sc"`, exactly 52 chars; 100 rows in 2023, 40 in 2024). A transform must repair both truncation classes before suffix-based detail-level detection or those district aggregates are misclassified as school rows.

- **State-aggregate detection: `SCHOOL_DSTRCT_NM == "State of Georgia"` AND `INSTN_NAME == "All Georgia Schools"`.** Set both `district_code` and `school_code` to NULL. Always 6 state rows per year (2 roles × 3 poverty subgroups — no `Not Applicable` or `Unknown` at the state level).

- **`TFS` suppression marker (2021–2024 only).** Convert `TFS` → NULL via `pl.col(...).cast(pl.Float64, strict=False)`. The numeric reporting floor is 10 (any actual value <10 is masked). This affects all three metric columns (`FTE`, `INEXPERIENCED_FTE`/`CATEGORY_FTE`, `INEXPERIENCED_FTE_PCT`/`CATEGORY_FTE_PCT`).

- **2018–2020 has no suppression — true zeros are present.** In `2018.csv`–`2020.csv`, values of `0` (in `INEXPERIENCED_FTE`) and `0` (in `INEXPERIENCED_FTE_PCT`) are real measurements: 723–765 rows per year reported zero Inexperienced educators. Do not coerce these zeros to NULL.

- **Percentage scale is 0–100.** `*_FTE_PCT` columns are integer percents (observed range: 0–100 in 2018–2020, 10–100 in 2021+). Per `data-cleaning-standards`, convert to 0–1 in gold by dividing by 100.

- **`FTE` is the subgroup-specific denominator, not always total.** When `LABEL_LVL_2_DESC = Total`, `FTE` is the total role FTE at the entity; when it is `High Poverty` or `Low Poverty` (or `Not Applicable` / `Unknown` for Leaders), `FTE` is the FTE in just that subgroup of schools/positions. Carry `FTE` in gold so consumers can recompute weighted aggregates.

- **Duplicate rows exist in 2023 and 2024.** In each of those two years, multiple rows share the same `(LONG_SCHOOL_YEAR, SCHOOL_DSTRCT_NM, INSTN_NAME, LABEL_LVL_3_DESC, LABEL_LVL_2_DESC)` key (`State Charter Schools II- Genesis Innovation Academy` in both years, and `State Charter Schools- Utopian Academy for the Arts ` in 2024). *(Amended 2026-06-11 with run evidence:)* these are NOT same-entity republications — each is a 52-char `INSTN_NAME` truncation that erases the distinguisher between two sister charter campuses (Genesis Boys/Girls; Utopian main/Trilith), collapsing two physical entities onto one bronze key. The affected groups are: 2023 Genesis Leaders/Total (`TFS/TFS/100` vs `TFS/TFS/TFS`) **and** 2023 Genesis Teachers/Total (`31.1/23.1/74` vs `29.6/17.6/60` — non-TFS, contradicting the earlier claim that all affected rows are Leaders with `FTE = TFS`); 2024 Genesis Leaders/Total (`TFS/TFS/100` vs `TFS/TFS/TFS`); 2024 Utopian Leaders/Total (`TFS/TFS/100` vs `TFS/TFS/100`, identical). Because each colliding pair belongs to two different campuses whose bare school-name rows carry the faithful per-campus values, preserving both under one arbitrarily-bound district key would double-count — the transform drops the distinguisher-erased Genesis aggregates and lets the identical Utopian pair collapse via dedup.

- **`Department of Juvenile` is a district.** 18–19 rows per year come from the `Department of Juvenile` district (Georgia Department of Juvenile Justice schools at Youth Development Campuses). This district's Leaders rows are the sole source of `LABEL_LVL_2_DESC = Unknown`. Ensure the district lookup handles this non-county-named district.

- **No nulls in any source column.** All cells are populated; suppression is encoded with the `TFS` string (2021+), and absence of the metric in pre-2021 is encoded with `0`.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| #CATEGORY_DESC | not_in_gold | — | Era 1 only; constant `Inexperienced`; verify and drop |
| LONG_SCHOOL_YEAR | fact_key | year | Convert `YYYY-YY` → ending calendar year as `pl.Int32` (e.g., `2023-24` → `2024`) |
| SCHOOL_DSTRCT_NM | fact_key (lookup source) | district_code | Lookup `district_code` in `districts.parquet` by `district_name`; NULL for state-level rows where `SCHOOL_DSTRCT_NM = "State of Georgia"` |
| SCHOOL_DSTRCT_NM | dimension_attribute | — | Already represented in `districts.district_name` |
| INSTN_NAME | fact_key (lookup source) | school_code | Lookup `school_code` in `schools.parquet` by `(district_code, school_name)`; NULL for district-aggregate rows (`<District>- All Schools`) and state-level rows (`All Georgia Schools`) |
| INSTN_NAME | dimension_attribute | — | Already represented in `schools.school_name` |
| LABEL_LVL_3_DESC | fact_categorical | role | Values `teachers`, `leaders` (snake_case the source labels); critical for this topic — unlike sibling emergency/out-of-field topics, Leaders data is included |
| LABEL_LVL_2_DESC | fact_categorical | poverty_subgroup | Values `total`, `high_poverty`, `low_poverty`, `not_applicable` (Leaders only), `unknown` (Leaders only); not a global demographic |
| FTE | fact_metric | total_fte | Total role FTE in the entity/subgroup; `TFS` → NULL; cast to `pl.Float64` |
| INEXPERIENCED_FTE / CATEGORY_FTE | fact_metric | inexperienced_fte | Unified Inexperienced-educator FTE count across both eras; `TFS` → NULL; cast to `pl.Float64`; preserve true `0` values from 2018–2020 |
| INEXPERIENCED_FTE_PCT / CATEGORY_FTE_PCT | fact_metric | inexperienced_fte_pct | Unified Inexperienced-educator percentage across both eras; `TFS` → NULL; cast to `pl.Float64`; divide by 100 to put on 0–1 scale per `data-cleaning-standards` |
