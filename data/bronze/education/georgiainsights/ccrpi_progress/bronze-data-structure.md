# ccrpi_progress - Bronze Data Structure

## Overview

- Topic: ccrpi_progress
- Source: georgiainsights
- Files: 8 files spanning 2018-2025
- Unreadable files: none
- Year representation: `School Year` column in each file (single calendar year integer, e.g., 2024). Stored as Int64 in 2018-2020 and 2022-2025, and as String in 2021.
- Filename-to-data year offset: same (filename year = data year, confirmed via `School Year` column)
- Detail levels: state, district, school (all three present in every year, including 2021 — see Detail Level Detection)
- Percentage scale: All score / target / band-movement metrics are on a 0-100 scale (with an overage marker `100.00+` in some years)
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: Georgia Insights (GaDOE) public data downloads — exact page URL not recorded at acquisition time
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| 2018 CCRPI Progress Scores, Targets, Flags by Subgroup 12_14_18.xlsx | f8322e2c071957a579036e05fc7126c5e1df8aaab68eb0b3257cf7b0095994b3 |
| 2019 CCRPI Progress Scores, Targets, Flags by Subgroup_10_25_19.xlsx | 74a5950635c80090fd5c0c36aa5275a5b2a3492e0b59cf4402069091fbca3cae |
| 2020 Progress Scores, Targets, and Flags by Subgroup (Progress Towards Language Proficiency only).xlsx | 64199c54b2a4480e455f794c6a3cf4e7848399b325b8d03aac6c9cb079e56fba |
| 2021 Progress Towards English Language Proficiency by Subgroup 12.08.21.xlsx | e7c84b2c3b3fc5ca29bdfaec3b08ed9bee50bcf6b424f1652841f028b317ee93 |
| 2022 Progress Towards English Language Proficiency 11.16.22.xlsx | 4440677d584dee3c64581198f8c110e9b1827a62bfd85a2ff76e047fa06189c7 |
| 2023 CCRPI Progress Scores, Targets, and Flags by Subgroup_12_14_23.xlsx | 5ca8d235a7ae077bb4c209086f3e02a612f0a8882c3a85eb73f5378002fbdde1 |
| 2024 CCRPI Progress Scores, Targets, and Flags by Subgroup.xlsx | 01ead2115f3d2b31c55434742ae69ccd6b87cd28826acc3ae0295c60624ccbe2 |
| 2025 CCRPI Progress Scores, Targets, and Flags by Student Group.xlsx | 9e02ec499295851f7ada643c4c7172272c7fbf77e5d453458922ecea84c6df9c |

(All bytes unchanged from the prior generation; the only update vs the previous report is the date.)

## Excel Sheet Structure

| File(s) | Sheets | Notes |
|---------|--------|-------|
| 2018, 2019, 2020, 2023, 2024 | Progress by Subgroup (Data) | Single data sheet |
| 2021 | ELP by Subgroup (Data), FAQs (Metadata) | FAQs sheet is empty (polars raises NoDataError). ELP-only Era B schema. |
| 2022 | ELP (Data), FAQs (Metadata) | FAQs sheet is empty. ELP-only Era B schema. Primary sheet was renamed from "ELP by Subgroup" to "ELP". |
| 2025 | Progress - Student Group (Data) | Single data sheet, but the sheet name differs from earlier years ("Progress - Student Group" vs "Progress by Subgroup"). |

The transform must look up the correct primary sheet name per file rather than assuming a constant.

## Summary

CCRPI Progress measures the rate at which students improve year-over-year on Georgia Milestones assessments and the rate at which English Learners progress toward English Language Proficiency (ELP). The dataset reports an `Indicator Score` (a 0-100 progress score) along with an improvement `Target` and a performance `Flag` (G / Y / R) for each combination of school, demographic subgroup, and indicator (English Language Arts growth, Mathematics growth, and Progress Towards English Language Proficiency). For 2021 and 2022, GADOE published only the ELP component using a different schema that breaks the ELP rate into the four band-movement percentages (No Positive Movement, Moved Less Than One Band, Moved One Band, Moved More Than One Band) plus a single `Progress Towards ELP Rate`. The 2020 file is also ELP-only (Progress Towards Language Proficiency was the only component released that year), but uses the same column layout as the surrounding score/target/flag-style files.

## Eras

### Era A: 2018, 2019, 2020, 2023, 2024, 2025 — Score / Target / Flag schema

**Columns** (12, identical names across all six files):

`School Year`, `System ID`, `System Name`, `School ID`, `School Name`, `Grade Configuration`, `Grade Cluster`, `Reporting Label`, `Indicator`, `Indicator Score`, `Target`, `Flag`

| Column | Description |
|--------|-------------|
| School Year | Calendar year integer (e.g., 2024). Int64 in all Era A files. |
| System ID | District code (Int64). Null for state-level rows in 2019, 2023-2025. In 2018 and 2020, state-level rows also have null System ID. |
| System Name | District name, or `All Systems` for state-level rows. |
| School ID | School code. Stored as Int64 in 2019 / 2023-2025 (district / state aggregate rows are null); stored as String in 2018 / 2020 with the literal `ALL` marking district + state aggregate rows. |
| School Name | School name, or `All Schools` for district / state aggregate rows. |
| Grade Configuration | Comma-separated grade levels offered at the school (e.g., `09, 10, 11, 12`, `PK, KK, 01, 02, 03, 04, 05`). School attribute, not a measurement. 60+ distinct values per year. |
| Grade Cluster | Single-letter grade band: `E` (Elementary), `M` (Middle), `H` (High). |
| Reporting Label | Demographic subgroup name (10 distinct values per year except 2020). Spelling and punctuation drift between years (see ETL Considerations). |
| Indicator | The progress indicator measured. Labels drift across years (see Indicator labels table below). 2020 has only `Progress Towards Language Proficiency`. |
| Indicator Score | 0-100 progress score. Polars infers Float64 in 2018 (most cells numeric, suppression markers `NA`/`TFS` coerce to null on read) and String in 2019-2025 (suppression markers stay as strings); 2023 also contains the overage marker `100.00+`. |
| Target | Improvement target on the same 0-100 scale. Polars infers Float64 in 2019 (suppression markers coerce to null on read) and String in 2018 + 2020-2025 with `NA` (no target applies) and `TFS` (target suppressed for small N). |
| Flag | Performance flag: `G` (green / met target), `Y` (yellow), `R` (red), `NA` (no flag). |

**Indicator labels by year (Era A):**

| Year | Indicator label A | Indicator label B | Indicator label C |
|------|-------------------|-------------------|-------------------|
| 2018 | `ELA Growth` | `Mathematics Growth` | `ELP Progress` |
| 2019 | `English Language Arts` | `Mathematics` | `Progress Towards Language Proficiency` |
| 2020 | — | — | `Progress Towards Language Proficiency` (only indicator that year) |
| 2023, 2024, 2025 | `English Language Arts` | `Mathematics` | `Progress Towards English Language Proficiency` |

#### Sample Data (representative file: 2024)

```
shape: (5, 12)
School Year  System ID  System Name                                            School ID  School Name                       Grade Configuration                                       Grade Cluster  Reporting Label                  Indicator              Indicator Score  Target  Flag
2024         756        Wilcox County                                          195        Wilcox County Elementary School   PK, KK, 01, 02, 03, 04, 05                                E              Students With Disability         Mathematics            78.96            NA      NA
2024         648        Douglas County                                         507        Youth Villages at Inner Harbour   02, 03, 04, 06, 07, 08, 09, 10, 11, 12                    H              Black                            English Language Arts  NA               NA      NA
2024         7830636    State Charter Schools II- Northwest Classical Academy  null       All Schools                       PK, KK, 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12   H              Asian/Pacific Islander           Mathematics            TFS              NA      NA
2024         721        Richmond County                                        2058       Merry Elementary School           PK, KK, 01, 02, 03, 04, 05                                E              American Indian/Alaskan Native   Mathematics            NA               NA      NA
2024         749        Warren County                                          null       All Schools                       PK, KK, 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12   H              ALL Students                     Mathematics            61               NA      NA
```

#### Statistics (representative file: 2024)

Row count: **68,187**. Indicator Score is stored as String; the numeric portion has 34,090 non-null values (mean 82.72, std 14.07, min 5.56, max 100). Target numeric portion has 1,677 non-null values (mean 75.00, max 90).

Per-year row counts: 2018 = 87,480; 2019 = 65,898; 2020 = 3,148 (ELP only); 2023 = 67,452; 2024 = 68,187; 2025 = 67,998.

#### Null Counts

**2024** (representative — String dtype for score/target so markers stay visible):

| Column | Null Count |
|--------|-----------|
| System ID | 63 (state-level rows) |
| School ID | 14,805 (district + state aggregate rows) |
| All others | 0 |

**2018** (Indicator Score read as Float64 — suppression markers coerced to null at read time):

| Column | Null Count |
|--------|-----------|
| System ID | 90 (state-level rows) |
| Indicator Score | 46,579 (`NA` + `TFS` cells coerced to Float64 null) |
| All others | 0 (School ID uses literal `ALL` so it is never null) |

**2019** (Target read as Float64 — same effect):

| Column | Null Count |
|--------|-----------|
| System ID | 63 (state-level rows) |
| School ID | 13,482 (district + state aggregate rows) |
| Target | non-null only where a numeric target was published; `NA`/`TFS` cells become null |

#### Categorical Columns (2024)

| Column | Distinct Values |
|--------|----------------|
| Grade Cluster | E (33,873), M (18,732), H (15,582) |
| Reporting Label | English Learners (9,741), ALL Students (6,494), American Indian/Alaskan Native (6,494), Asian/Pacific Islander (6,494), Black (6,494), Economically Disadvantaged (6,494), Hispanic (6,494), Multi-Racial (6,494), Students With Disability (6,494), White (6,494) |
| Indicator | Mathematics (32,470), English Language Arts (32,470), Progress Towards English Language Proficiency (3,247) |
| Flag | NA (66,588), G (1,136), R (422), Y (41) |

**Reporting Label drift across Era A:**

| Year | American Indian label | Asian / Pacific label | Disability label |
|------|-----------------------|------------------------|------------------|
| 2018 | `American Indian/Alaskan` (no "Native") | `Asian/Pacific Islander` | `Students With Disability` |
| 2019 | `American Indian / Alaskan Native` (spaces around slash) | `Asian / Pacific Islander` (spaces) | `Students with Disability` (lowercase "w") |
| 2023, 2024, 2025 | `American Indian/Alaskan Native` | `Asian/Pacific Islander` | `Students With Disability` |

The 2020 file only contains the demographic `English Learners` (ELP-only release).

**Asian / Pacific Islander structure.** Every Era A and Era B file publishes a single combined `Asian/Pacific Islander` (or `Asian / Pacific Islander`) bucket — there is no separate `Asian` row and no separate `Pacific Islander` row anywhere in the bronze. Per `data-cleaning-standards` §5b, when the bronze only ships the combined bucket the transform must map it to the canonical `asian_pacific_islander` demographic key (not `asian`). No bare `Asian` row exists that could be misclassified, so the §5b math test ("if race sum equals total exactly, the lone Asian row is actually the combined bucket") does not apply here.

#### Suppression Markers (2024)

| Column | Non-Numeric Values |
|--------|-------------------|
| Indicator Score | NA (17,984), TFS (16,113) |
| Target | NA (65,488), TFS (1,022) |

In **2023 only**, Indicator Score also contains `100.00+` (4,131 occurrences) — an overage marker meaning the school exceeded 100% progress; treat as 100.

In **2018**, the raw Excel cells DO contain `NA` and `TFS` strings in `Indicator Score`, but polars coerces the whole column to Float64 (because most cells are numeric) and the markers become Polars nulls. Target in 2018 still surfaces as String with `NA`/`TFS` markers.

In **2019**, the same pattern applies to Target: raw cells contain `NA`/`TFS`, but polars coerces to Float64 and the markers become null. Indicator Score in 2019 stays String with `NA`/`TFS` markers visible.

This polars-coercion-to-null behavior is data-loss-free for the gold layer (a null and a suppression marker both become null in the metric column), but it is important to know when reading the bronze — `df.null_count()` for those Float64 columns reflects suppressed-or-missing rows, not "no data quality issues".

---

### Era B: 2021, 2022 — ELP-only band-movement schema

**Columns** (13, identical names across both files):

`School Year`, `System ID`, `System Name`, `School ID`, `School Name`, `Grade Configuration`, `Grade Cluster`, `Reporting Label`, `No Positive Movement`, `Moved Less Than One Band`, `Moved One Band`, `Moved More Than One Band`, `Progress Towards ELP Rate`

| Column | Description |
|--------|-------------|
| School Year | Year (String in 2021, Int64 in 2022). Same calendar-year semantic as Era A. |
| System ID | District code (String in 2021, Int64 in 2022). In 2021, state-level rows store the literal string `ALL` here (3 such rows). In 2022, state-level rows have null System ID (3 such rows). |
| System Name | District name, or `All Systems` for state-level rows. |
| School ID | School code. **String in both years**, with the literal `ALL` for district / state aggregate rows. Zero-padded in 2021 (e.g., `0194`) but not in 2022 (e.g., `194`). |
| School Name | School name, or `All Schools` for aggregate rows. |
| Grade Configuration | Same comma-separated grade-list semantics as Era A. |
| Grade Cluster | `E`, `M`, `H`. |
| Reporting Label | Always `English Learners` (no other demographic groups in Era B). |
| No Positive Movement | Percentage of EL students with no positive band movement, 0-100. String with `TFS` suppression marker. |
| Moved Less Than One Band | Percentage moving less than one band, 0-100. String with `TFS`. |
| Moved One Band | Percentage moving exactly one band, 0-100. String with `TFS`. |
| Moved More Than One Band | Percentage moving more than one band, 0-100. String with `TFS`. |
| Progress Towards ELP Rate | Composite ELP progress rate, 0-100 (the same metric reported as `Indicator Score` for the ELP indicator in Era A). String with `TFS` (suppressed) and `100.00+` (overage marker meaning exceeded 100%). |

#### Sample Data (representative file: 2022)

```
shape: (5, 13)
School Year  System ID  System Name                                              School ID  School Name                      Grade Configuration                                       Grade Cluster  Reporting Label   No Positive Movement  Moved Less Than One Band  Moved One Band  Moved More Than One Band  Progress Towards ELP Rate
2022         741        Troup County                                             194        Hollis Hand Elementary School    PK, KK, 01, 02, 03, 04, 05                                E              English Learners  16.67                 10                        20              53.33                     100.00+
2022         644        DeKalb County                                            ALL        All Schools                      PK, KK, 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12   E              English Learners  19.63                 15.86                     24.87           39.64                     92.26
2022         7830613    State Charter Schools II- Brookhaven Innovation Academy  ALL        All Schools                      PK, KK, 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12   M              English Learners  TFS                   TFS                       TFS             TFS                       TFS
2022         709        Oglethorpe County                                        112        Oglethorpe County Middle School  06, 07, 08                                                M              English Learners  63.16                 10.53                     15.79           10.53                     36.86
2022         734        Telfair County                                           ALL        All Schools                      PK, KK, 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12   E              English Learners  22.22                 5.56                      22.22           50                        100.00+
```

#### Statistics

Row count: 2022 = **2,721**; 2021 = 2,674. Both are ELP-only (one row per school × grade-cluster × English Learners).

#### Null Counts (2022)

| Column | Null Count |
|--------|-----------|
| System ID | 3 (state-level rows) |
| All others | 0 |

For 2021, all columns have 0 nulls because every column was loaded as String and state-level rows store the literal `ALL` in `System ID` and `School ID` rather than a Polars null.

#### Categorical Columns (2022)

| Column | Distinct Values |
|--------|----------------|
| Grade Cluster | E (1,438), M (708), H (575) |
| Reporting Label | English Learners (2,721) — only value |

#### Suppression Markers

**2022:**

| Column | Non-Numeric Values |
|--------|-------------------|
| School ID | ALL (533) — district / state aggregate marker, not suppression |
| No Positive Movement | TFS (1,148) |
| Moved Less Than One Band | TFS (1,148) |
| Moved One Band | TFS (1,148) |
| Moved More Than One Band | TFS (1,148) |
| Progress Towards ELP Rate | TFS (1,148), 100.00+ (466) |

**2021:**

| Column | Non-Numeric Values |
|--------|-------------------|
| School Year | `2021` (all values — column is String) |
| System ID | `ALL` (3 — state rows), plus zero-padded numeric district codes as strings |
| School ID | `ALL` (528) — district / state aggregate marker |
| No Positive Movement | TFS (1,136) |
| Moved Less Than One Band | TFS (1,136) |
| Moved One Band | TFS (1,136) |
| Moved More Than One Band | TFS (1,136) |
| Progress Towards ELP Rate | TFS (1,136), 100.00+ (202) |

---

## ETL Considerations

### Two distinct schemas (Eras) require separate code paths

- **Era A** (2018, 2019, 2020, 2023, 2024, 2025) uses the `Indicator` / `Indicator Score` / `Target` / `Flag` shape with one row per school × demographic × indicator (3 indicators when ELA / Math / ELP are all reported, 1 when only ELP).
- **Era B** (2021, 2022) uses the band-movement shape with one row per school × `English Learners` and 4 band-movement metrics plus a composite `Progress Towards ELP Rate`. Other demographics (ALL Students, Hispanic, etc.) are not present in Era B and the ELA / Math indicators are absent entirely.

The eras are **non-contiguous** — Era A applies to 2018-2020 *and* 2023-2025, while Era B sits between them (2021-2022).

### Sheet name varies per file

- 2018-2020, 2023, 2024 use `Progress by Subgroup`
- 2021 uses `ELP by Subgroup`
- 2022 uses `ELP`
- 2025 uses `Progress - Student Group`

The transform must build a per-file sheet-name lookup rather than assuming a constant.

### Indicator labels drift across years (Era A)

| Year(s) | ELA indicator | Math indicator | ELP indicator |
|---------|---------------|----------------|----------------|
| 2018 | `ELA Growth` | `Mathematics Growth` | `ELP Progress` |
| 2019 | `English Language Arts` | `Mathematics` | `Progress Towards Language Proficiency` |
| 2020 | — | — | `Progress Towards Language Proficiency` (only indicator) |
| 2023, 2024, 2025 | `English Language Arts` | `Mathematics` | `Progress Towards English Language Proficiency` |

Normalize to canonical values: `english_language_arts_growth`, `mathematics_growth`, `progress_towards_elp` (or similar) so that pre-2019 metrics align with later years for time-series analysis. **The 2018 indicators cleanly correspond to the 2019+ indicators**: ELA Growth = English Language Arts (growth in ELA proficiency on Milestones year-over-year), Mathematics Growth = Mathematics, ELP Progress = Progress Towards (English) Language Proficiency.

### Demographic label drift across Era A

| Concept | 2018 | 2019 | 2023-2025 |
|---------|------|------|-----------|
| American Indian | `American Indian/Alaskan` | `American Indian / Alaskan Native` | `American Indian/Alaskan Native` |
| Asian / Pacific | `Asian/Pacific Islander` | `Asian / Pacific Islander` | `Asian/Pacific Islander` |
| Disability | `Students With Disability` | `Students with Disability` (lowercase "w") | `Students With Disability` |

Map to the standard demographics dimension keys; the existing `ccrpi_content_mastery` transform faces the identical problem and provides a working pattern.

Per `data-cleaning-standards` §5b, the lone `Asian/Pacific Islander` row (no separate Asian or Pacific Islander values anywhere) must be mapped to the canonical `asian_pacific_islander` demographic key.

### School ID / System ID type and aggregate-marker inconsistencies

| Year | System ID dtype | System ID for state rows | School ID dtype | School ID for aggregate rows | Zero-padding |
|------|-----------------|--------------------------|------------------|-------------------------------|--------------|
| 2018 | Int64 | null | String | literal `ALL` | yes (e.g., `0103`) |
| 2019 | Int64 | null | Int64 | null | n/a (Int) |
| 2020 | Int64 | null | String | literal `ALL` | no (e.g., `103`) |
| 2021 | String | literal `ALL` | String | literal `ALL` | yes (e.g., `0194`) |
| 2022 | Int64 | null | String | literal `ALL` | no (e.g., `194`) |
| 2023 | Int64 | null | Int64 | null | n/a (Int) |
| 2024 | Int64 | null | Int64 | null | n/a (Int) |
| 2025 | Int64 | null | Int64 | null | n/a (Int) |

The transform must normalize both columns to consistent string FKs (e.g., `School ID` cast to Utf8 with `zfill(4)`, `System ID` cast to Utf8 with `zfill(3)`) and convert `ALL` and any pre-existing nulls to NULL. Verify zero-padding policy against the schools / districts dimensions to avoid join misses.

### Target column read dtype

- **2018, 2020-2025**: Target is read by polars as String with `NA` / `TFS` markers (and bare numerics).
- **2019**: Target is read as Float64 because the column has enough numeric values to outweigh string markers; the raw cells still contain `NA` / `TFS`, which polars silently coerces to null.

Treat `NA` as "target does not apply" (effectively null in gold), `TFS` as "target suppressed" (also null). Cast all to Float64 after stripping markers — for 2019 the cast is a no-op because polars already did the coercion.

### Indicator Score column read dtype

- **2018**: Indicator Score is read as Float64 (raw cells have `NA`/`TFS`, but polars coerces them to null on read).
- **2019-2025**: Indicator Score is read as String with `NA` / `TFS` (and `100.00+` in 2023 only).

Use `cast(pl.Float64, strict=False)` after explicitly mapping `100.00+` to `100`.

### `100.00+` overage marker

Appears in:
- 2023 `Indicator Score` (4,131 rows)
- 2021 `Progress Towards ELP Rate` (202 rows)
- 2022 `Progress Towards ELP Rate` (466 rows)

Map to `100.0` before numeric casting (matches the pattern used in `ccrpi_content_mastery` for the same marker).

### Detail level detection

State / district / school rows are encoded slightly differently across years, but the cross-era name-based test is identical everywhere:

- `state_row` = `System Name == 'All Systems'`
- `district_row` = `System Name != 'All Systems' AND School Name == 'All Schools'`
- `school_row` = `School Name != 'All Schools'`

Using the **name** columns avoids the per-year ID encoding differences entirely. Confirmed working against every year (2018-2025). Per-year state-row counts using this test: 2018 = 90, 2019 = 63, 2020 = 3, 2021 = 3, 2022 = 3, 2023 = 63, 2024 = 63, 2025 = 63. The 90 in 2018 reflects the fact that 2018 publishes 3 indicators × 10 demographics × 3 grade clusters = 90 state-level rows; ELP-only years collapse to 1 indicator × 1 demographic × 3 grade clusters = 3.

### 2021 stores all columns as String

In 2021 every column (including `School Year`, `System ID`, and `School ID`) is loaded as String by polars because the file mixes string aggregate markers (`ALL`) and zero-padded IDs (`0194`) with numeric-looking strings. Cast each column explicitly during the transform.

### Reporting Label scope differs by era

Era A files have the full 10 demographic groups for ELA / Math indicators **and** for the ELP indicator (which is non-null only for the `English Learners` row in practice). Era B files only contain the `English Learners` demographic. When unioning eras, the absence of other demographics in Era B is structural, not a data quality issue.

### Era B band-movement metrics do not exist in Era A

Era A reports a single composite `Indicator Score` for the ELP indicator. Era B replaces that with five separate columns (the four band-movement percentages plus the composite `Progress Towards ELP Rate`). The composite in Era B equals the same metric reported as `Indicator Score` for the ELP indicator in Era A — preserve it under the unified `indicator_score` metric. The four band-movement columns have no Era A equivalent; either drop them or surface them as Era-B-only metric columns with explicit nulls in Era A rows.

### Empty FAQs sheets

Both 2021 and 2022 contain an empty `FAQs` sheet (polars `read_excel` raises `NoDataError` if you read it directly). Skip during transform.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| School Year | not_in_gold | — | Year is captured by the partition (Hive `year=YYYY`); column itself is redundant |
| System ID | fact_key | district_code | FK to districts dimension. Cast to Utf8, `zfill(3)`. Map `ALL` and bronze-null to NULL for state rows. |
| System Name | dimension_attribute | — | `district_name` in districts dimension (and "All Systems" identifies the state-level row, used only for detail-level detection) |
| School ID | fact_key | school_code | FK to schools dimension. Cast to Utf8, `zfill(4)`. Map `ALL` and bronze-null to NULL for district / state rows. |
| School Name | dimension_attribute | — | `school_name` in schools dimension (and "All Schools" identifies aggregate rows, used only for detail-level detection) |
| Grade Configuration | dimension_attribute | — | Belongs in school dimension as the school's grade range; not a measurement |
| Grade Cluster | fact_categorical | grade_cluster | E / M / H |
| Reporting Label | fact_key | demographic | FK to demographics dimension. Normalize spelling drift (American Indian, Asian/Pacific, Disability casing) to canonical demographic keys. The lone `Asian/Pacific Islander` bucket maps to `asian_pacific_islander` (per data-cleaning-standards §5b). |
| Indicator (Era A) | fact_categorical | indicator | Normalize the 2018 labels (`ELA Growth`, `Mathematics Growth`, `ELP Progress`) and the 2019/2020 labels (`Progress Towards Language Proficiency`) to the canonical labels (`english_language_arts_growth`, `mathematics_growth`, `progress_towards_elp`). Era B implicitly equals `progress_towards_elp` for every row. |
| Indicator Score (Era A) / Progress Towards ELP Rate (Era B) | fact_metric | indicator_score | Primary 0-100 progress score. Cast suppression markers `NA` and `TFS` to null. Map `100.00+` to 100 before numeric cast. |
| Target | fact_metric | target | 0-100 improvement target. Cast `NA` (no target applies) and `TFS` (suppressed) to null. |
| Flag | fact_categorical | flag | Performance flag G / Y / R. Map `NA` (no flag) to null. |
| No Positive Movement (Era B) | fact_metric | no_positive_movement_pct | 0-100. Era B only — Era A rows null. Cast `TFS` to null. |
| Moved Less Than One Band (Era B) | fact_metric | moved_less_than_one_band_pct | 0-100. Era B only. Cast `TFS` to null. |
| Moved One Band (Era B) | fact_metric | moved_one_band_pct | 0-100. Era B only. Cast `TFS` to null. |
| Moved More Than One Band (Era B) | fact_metric | moved_more_than_one_band_pct | 0-100. Era B only. Cast `TFS` to null. |

## Corrections

Added 2026-06-12 during the clean-start transform rewrite, after re-verifying every claim against the 8 bronze files.

### "Reporting Label scope differs by era" overstates ELP-indicator demographic coverage

The ETL Considerations section claims Era A files have "the full 10 demographic groups for ELA / Math indicators **and** for the ELP indicator (which is non-null only for the `English Learners` row in practice)". Two parts of this are wrong:

1. **Only 2018 publishes ELP-indicator rows for all 10 demographic groups** (25,620 `ELP Progress` rows = 10 groups × 2,562). In **2019, 2023, 2024, and 2025 the ELP indicator rows exist ONLY for `English Learners`** (2019: 3,138 rows; 2023: 3,212; 2024: 3,247; 2025: 3,238 — each with a single Reporting Label value). The 10-group coverage applies to the ELA / Math indicators in every multi-indicator year, but to the ELP indicator only in 2018. This is also visible in the doc's own 2024 categorical counts: English Learners 9,741 (= 3,247 × 3 indicators) vs 6,494 (= 3,247 × 2) for every other group.
2. **The 2018 ELP `Indicator Score` is NOT non-null only for English Learners.** Non-null ELP scores by 2018 Reporting Label: ALL Students 1,357, English Learners 1,357, Economically Disadvantaged 1,215, Hispanic 1,142, Students With Disability 393, Asian/Pacific Islander 202, Black 72, White 58, American Indian/Alaskan 7, Multi-Racial 5. What IS English-Learners-only in 2018 is `Target` (1,234 non-null, 0 for all other groups) and `Flag` (1,201 non-null, 0 for all other groups).

### Target / Flag population scope (verified facts the doc omits)

The Summary's "an improvement `Target` and a performance `Flag` ... for each combination of school, demographic subgroup, and indicator" reads as if targets/flags accompany every row. Verified across all six Era A files:

- `Target` and `Flag` are non-null **only on the ELP indicator** — the ELA and Mathematics indicators carry 0 non-null targets and 0 non-null flags in every year, including 2018.
- Within the ELP indicator they are non-null **only for `English Learners`** rows.
- **2020 publishes neither** (0 non-null targets, 0 non-null flags in the whole file), even though it uses the Era A layout. Era B (2021-2022) has no target/flag columns at all.
- Observed flag vocabulary is exactly `G` / `Y` / `R` (plus `NA` = no flag); `G*` never appears in this topic.
