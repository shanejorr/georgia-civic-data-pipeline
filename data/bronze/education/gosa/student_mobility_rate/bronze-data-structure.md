# student_mobility_rate — Bronze Data Structure

## Overview

- Topic: student_mobility_rate
- Source: gosa
- Files: 26 files spanning 2012–2024 — **two download families** in one bronze directory:
  - `student_mobility_rates_district_YYYY.xls` (13 files, 2012–2024) — the GOSA district-level mobility download.
  - `student_mobility_rates_school_YYYY.xls` (13 files, 2012–2024) — the GOSA school-level mobility download.
  The two families are distinct GOSA downloads with **identical metric semantics** (the same churn rate, percent scale 0–100); the only difference is detail level (one row per district vs one row per school). The transform routes each file by the `_district_` / `_school_` infix in its filename.
- Unreadable files: none.
- Year representation: Year is encoded in the filename only (`student_mobility_rates_{district,school}_YYYY.xls`). There is **no year column inside any file** in either family.
- Filename-to-data year offset: No in-file year column to compare; the filename year is the **ending calendar year** of the school year (e.g., `..._2024.xls` = school year 2023–24), per GOSA convention shared with the `attendance` topic.
- Detail levels: **school** (school family — one row per school) and **district** (district family — one row per district). In the merged gold fact table school rows carry both geography keys and district rows have a NULL `school_code` (detail level implicit in the parquet filename, dropped on export). No statewide rollup rows exist in either family.
- Percentage scale: 0–100 for the single metric column (`mobility_rate` / `mobility`). The transform divides by 100 onto the 0–1 scale (`unit: ratio` — values may legitimately exceed 1.0 at high-churn schools).
- Checksums generated: 2026-05-22

> **Note on the 2014 anomaly.** The `student_mobility_rates_district_2014.xls` file is byte-identical to `student_mobility_rates_school_2014.xls` (same SHA-256, `785e7ac…`): the district family's 2014 file is actually a **school-level** export (2,261 rows keyed by `sys_sch`/`school_name`), not a district export. It carries no enrollment counts, so GOSA's official district-level 2014 rate cannot be reconstructed from it. The merged transform detects this file as the school-level anomaly era and **drops the district-family 2014 file** (the school family's identical 2014 file supplies 2014's school-level rows). The merged fact table therefore has a 2014 district gap but full 2014 school coverage.

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

### District family (`student_mobility_rates_district_YYYY.xls`)

| File | SHA-256 |
|------|---------|
| student_mobility_rates_district_2012.xls | 17df70b7fb048cdd195f0c327363aac4f0ec5ae31aa2d8ee385a676bbec56901 |
| student_mobility_rates_district_2013.xls | bf588d6a72503caac1c9b3004737c6bfcce2af46b4ecb0bcbc01edcefb9682e7 |
| student_mobility_rates_district_2014.xls | 785e7ac52f25d54732e1671f99c25d61e33311a51a9d8aba406756d8bd8b5eb6 |
| student_mobility_rates_district_2015.xls | d2d278c510b29112a5a1c6e6dc31193d377564819b7ede8135062af74c3d358b |
| student_mobility_rates_district_2016.xls | 44f4b0905f13c001bdd82c480a29610f562b658fa46fb92e938628ea9fd7aca9 |
| student_mobility_rates_district_2017.xls | e92f1801d6ec22faa5953a0a7a12f561ff11f6b2e14e8d156e48dd23d6e54d42 |
| student_mobility_rates_district_2018.xls | 88fe35315dc55885815270825b9de122cbf82c3045c23ed7b8084b698b439506 |
| student_mobility_rates_district_2019.xls | 0c48422acb79f9ed24904ce9d7b08f1e09644bb4592095230dfd1024e663511e |
| student_mobility_rates_district_2020.xls | d1b9a08cfeb124a795e6d5955b0c33bd60bd397ebf18dd8fce3cca82f4d224d1 |
| student_mobility_rates_district_2021.xls | 8ca1142afeeca5c937f85447ffe7831e5b0a4218a72815e1baef9bc68e9ac514 |
| student_mobility_rates_district_2022.xls | a650fc51e6d22ea45d00e04f23de347600a80972c39f0904d92f1063a3fa9e8f |
| student_mobility_rates_district_2023.xls | efd57a21b5218ca0a4e97c471bb04249bb544ecc96f280ee44e36df4c6c11be7 |
| student_mobility_rates_district_2024.xls | 5e7764bdd2122b6670a44fdc9a2bc011fc2971265ecc6ac87e0e61796bfc3fa2 |

### School family (`student_mobility_rates_school_YYYY.xls`)

| File | SHA-256 |
|------|---------|
| student_mobility_rates_school_2012.xls | 9f9e09e293f560ac2d6e53b4598ee6927908e9d4ababf337ac9294e4e6ed2e70 |
| student_mobility_rates_school_2013.xls | 0fe058624cabecd4ac895c95b73489a300789eb12333adfc7b946b6c815d6da2 |
| student_mobility_rates_school_2014.xls | 785e7ac52f25d54732e1671f99c25d61e33311a51a9d8aba406756d8bd8b5eb6 |
| student_mobility_rates_school_2015.xls | 6fbb906bcc0131ec15f7231df02238740e91cbdb18bc10e0fddb429ba931a796 |
| student_mobility_rates_school_2016.xls | 087a96fe2c60b47eb11e58fafba549c5569802da5ad56461465d90a4f2140386 |
| student_mobility_rates_school_2017.xls | b3cfa41395e39f7cb4df8f42e51b126faf757fcd6efb854d32d487058f694bdb |
| student_mobility_rates_school_2018.xls | 075bbe1f28a8b1d7dd398a20f828da9f313fd0861dd93364d5f6d4d9ee7efe29 |
| student_mobility_rates_school_2019.xls | 6f1f043e9f6018fbd6a66568a9e6f1e38f6efdf8f51f4d438887aba7069984d7 |
| student_mobility_rates_school_2020.xls | 61c641ed4add4b2cb04916c06ab47441756bf91e2fd2198ffdccd007096f0409 |
| student_mobility_rates_school_2021.xls | a33e7396797f16c2c33fed8ffff5a67b2320df5ac6a31aef16f3f81edaaef030 |
| student_mobility_rates_school_2022.xls | ff4e5fb782e9b610c52835ee77d35892e449f82dd138f0c060903b6b75562bbd |
| student_mobility_rates_school_2023.xls | baef799b6960bfdc84111bc7238d77d1bbf9dac9ea0349f7655f08afb51b3df1 |
| student_mobility_rates_school_2024.xls | 975df48a61bb4e1df86411b40d1367e5a78b8c53c8dfc7dce42fda3c7a8733c8 |

## Excel Sheet Structure

| File(s) | Sheets | Notes |
|---------|--------|-------|
| both families, 2012–2024 | `Sheet1` (Data) | Every `.xls` file contains a single data sheet named `Sheet1`. No metadata/legend or pivot sheets. The transform reads the only sheet uniformly. |

## Summary

Annual **student mobility rate** (churn rate) for Georgia public schools and districts, published by GOSA for school years 2011-12 through 2023-24. GOSA computes mobility as a churn rate — student entries plus withdrawals between the fall count date and May 1, divided by fall-count enrollment — so it counts moves rather than movers and can legitimately exceed 100% at high-churn facilities (alternative schools, DJJ sites, residential treatment centers). No demographic breakdowns at either level. The two families are merged into one fact table at two detail levels: **school** (one row per school) and **district** (one row per district).

## District family eras

The district family carries one metric column on a 0–100 scale; only column names change across eras (the metric is renamed `mobility` from 2021).

### District Era 1: 2012–2013, 2015–2018 — standard district columns

Columns: `school_district_cd`, `school_district_nm`, `mobility_rate`.

| Column | Description |
|--------|-------------|
| school_district_cd | Three-digit GOSA district code (Int64 in the file; e.g., `601` = Appling County). Stringify + zero-pad to 3 chars. |
| school_district_nm | District name (dimension attribute — not in the fact table). |
| mobility_rate | District-level mobility rate, percent scale 0–100 (Float64). |

Every district-level file carries exactly **180 rows** (the identical 3-digit code set 601–793, zero nulls, no 7-digit charter codes). No `ALL`/`Total` summary rows.

### District Era 2: 2014 — school-level anomaly (dropped)

Columns: `sys_sch`, `school_district_nm`, `school_name`, `mobility_rate`. This file is school-level, not district-level (see the 2014 note above); the transform detects it by signature and drops it. It is byte-identical to the school family's 2014 file.

### District Era 3: 2019–2020 — renamed district-name column

Columns: `school_district_cd`, `school_district_nm_hs`, `mobility_rate`. The `_hs` suffix is a GOSA labeling artifact carrying the same semantics as `school_district_nm`. 180 rows/year, 0 nulls.

### District Era 4: 2021–2024 — renamed metric column

Columns: `school_district_cd`, `school_district_nm`, `mobility`. `mobility` is the renamed `mobility_rate` (semantically identical). 180 rows/year, 0 nulls.

#### District suppression markers

None in any year. `mobility_rate`/`mobility` is pure Float64 with 0 nulls; no `*`/`TFS`/N-A markers. District-level values span 0.039–0.59 after the ÷100 scaling (bronze max 59.0 in 2016); no district value exceeds 1.0.

## School family eras

The school family carries a compound `sys_sch` system-school code split into `district_code` + `school_code`, plus the same 0–100 metric. ~2,261–2,301 rows/year.

### School Era A: 2012–2018 — original column names

Columns: `sys_sch`, `school_district_nm`, `school_name`, `mobility_rate`. `sys_sch` parses as Int64 for 2012–2015 and String for 2016–2018 — always cast to String.

### School Era B: 2019–2020 — `_hs`-suffixed name columns

Columns: `sys_sch`, `school_district_nm_hs`, `school_name_hs`, `mobility_rate`. The `_hs` suffix is cosmetic; the files still cover all grade bands.

### School Era C: 2021–2024 — metric renamed to `mobility`

Columns: `sys_sch`, `school_district_nm`, `school_name`, `mobility`.

#### `sys_sch` shape and split rules

The first 3 characters are always the GOSA district code. Observed lengths:

- **6/7 chars** — regular district schools: district = first 3 chars, school = remainder zero-padded to 4 (`601103` → `601`/`0103`; `6011050` → `601`/`1050`).
- **10 chars**, prefix `782`/`783` — state/commission-charter schools: district = first 7 chars, school = last 3 zero-padded to 4 (`7820108108` → `7820108`/`0108`). The 3-char tail repeats the district tail (a GOSA publishing quirk).
- **7 or 11 chars**, prefix `799` — state schools (deaf/blind): district = first 3 chars, school = chars 4–7 zero-padded. The 11-char form with a duplicated school tail (`79918931893` → `799`/`1893`) runs 2012–2019; 2020–2024 publish the same schools as plain 7-char codes (`7991893` → `799`/`1893`). Both forms split to identical keys.

A shape guard hard-stops on any `sys_sch` that fits none of these patterns. All 29,625 school rows join the schools and districts dimensions with zero anti-join misses.

#### School suppression markers and NULLs

No suppression markers (`*`/`TFS`/`N/A`) in any file. Exactly **four** genuinely blank mobility cells become true NULL — one each in 2019, 2020, 2021, and 2024.

#### Legitimate >100 values and the 2020 outlier

Mobility above 100 (raw) is real at high-churn facilities (e.g., Lighthouse Care Center of Augusta 533.3 raw in 2024). Preserve — do not clip or drop. One suspected source defect is preserved per data-cleaning-standards §4b (extreme-but-conceivable): 2020 `701298` (Eagle's Landing Academy, Mitchell County) publishes raw 11500.0 (gold 115.0), ~17× the next 2020 extreme (657.9); the same school is NULL in 2019/2021 and absent from 2022+ bronze. It is retained, not capped, and flagged by the transform's sanity-threshold warning on every run.

#### Anomalous district code 890

`890198` (Department of Corrections) appears 2022–2024 with intermittently blank name fields. The fact rows are preserved (district_code `890`, school_code `0198`) — names are dimension attributes, not fact columns.

## ETL Considerations

- **Per-family dispatch by filename infix.** `_district_` → district reader/eras; `_school_` → school reader/eras. Any other filename must stop the pipeline.
- **2014 district file dropped.** Detected as the school-level anomaly era; recorded via `manifest.record_filtered` and omitted from the district detail (the school family supplies 2014 school rows). Documented year gap, not a silent absence.
- **Year derived from filename** (no in-file year column in either family); interpreted as the school-year ending calendar year. The district family cross-check uses the filename only; the school family the same.
- **Column renames normalized.** District: `school_district_nm_hs` (2019–2020) and `mobility` (2021–2024); School: `school_district_nm_hs`/`school_name_hs` (2019–2020) and `mobility` (2021–2024). Name columns are dimension attributes and are not carried into the fact table.
- **Percentage scale.** Both families publish 0–100; divide by 100 onto the 0–1 scale per data-cleaning-standards §4. Keep `unit: ratio` (values may exceed 1.0 at high-churn schools).
- **No demographics.** Every row is an implicit all-students aggregate in both families; the `demographic` column is omitted per §5.
- **No suppression.** No string markers anywhere; the only NULLs are the four blank school cells.

## Gold Schema Classification

One merged fact table at two detail levels (`detail_level` is implicit in the parquet filename and dropped on export):

| Detail level | district_code | school_code | Source family |
|--------------|---------------|-------------|---------------|
| school | value | value | `_school_` files (2012–2024) |
| district | value | NULL | `_district_` files (2012–2024, **no 2014**) |

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| (filename year) | fact_key | year | Ending calendar year of the school year. |
| school_district_cd (district family) | fact_key | district_code | Cast → zero-pad 3-char string; FK to districts dimension. |
| sys_sch[:3] / [:7] (school family) | fact_key | district_code | First 3 chars (or 7 for 782/783 charters); FK to districts dimension. |
| sys_sch tail (school family) | fact_key | school_code | Extracted + zero-padded to 4; composite FK to schools dimension. NULL on district rows. |
| school_district_nm / _hs | dimension_attribute | — | District name; lives in the districts dimension. |
| school_name / _hs | dimension_attribute | — | School name; lives in the schools dimension. |
| mobility_rate / mobility | fact_metric | mobility_rate | Float, ÷100 onto 0–1 ratio scale; the single fact-table metric (`key_metric`). |

Expected gold fact columns: `year`, `district_code`, `school_code`, `mobility_rate`. No demographic or categorical column beyond geography; no additional metrics.
