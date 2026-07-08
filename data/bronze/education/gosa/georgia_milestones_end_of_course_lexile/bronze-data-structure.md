# georgia_milestones_end_of_course_eoc_lexile_scores — Bronze Data Structure

## Overview

- Topic: georgia_milestones_end_of_course_eoc_lexile_scores
- Source: gosa
- Files: 9 files spanning 2015–2024 (2020 is missing — EOC testing was cancelled due to COVID-19)
- Unreadable files: none
- Year representation: present in both the filename (`georgia_milestones_end_of_course_eoc_lexile_scores_YYYY.csv`) and a `SCHOOL_YEAR` column (4-digit integer, e.g. `2024`)
- Filename-to-data year offset: same — filename year always equals the `SCHOOL_YEAR` value (e.g., `_2024.csv` contains `SCHOOL_YEAR = 2024` on every row). `SCHOOL_YEAR` is the ending calendar year of the school year (e.g., `2024` = school year 2023–24).
- Detail levels: state, district, school — explicit `DETAIL_LEVEL` column with values `"State Level"`, `"District Level"`, `"School Level"`
- Percentage scale: not applicable — the dataset reports integer counts (`TOTAL_STUDENTS_TESTED`, `STUDENTS_WITH_LEXILE`, `LEXILE_ON_OR_ABOVE_MIDPOINT`, `NO_LEXILE_SCORE`) and the Lexile measure itself (`AVG_LEXILE_SCORE`, observed range 707–1679 across all years). There is no percentage metric to rescale.
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| georgia_milestones_end_of_course_eoc_lexile_scores_2015.csv | dc965599be4f52d26a85520346143c56d99e4adf1490bee952414f89a438fb1a |
| georgia_milestones_end_of_course_eoc_lexile_scores_2016.csv | 0b55299670b83d9354c5e74078ee7a85a18b06eec1418d2b7521102b30981c47 |
| georgia_milestones_end_of_course_eoc_lexile_scores_2017.csv | 0f46fb0d0f973f2110a2f5b785a4364f6d5f34714fb5b5befe7cb60d1be9313b |
| georgia_milestones_end_of_course_eoc_lexile_scores_2018.csv | fedba67a7955869c01b4fe364bcadf7911aed40048aa7bef9fd84a2effc232b2 |
| georgia_milestones_end_of_course_eoc_lexile_scores_2019.csv | e3a1afc55669126f068ce2cf8f6ca1e47fbb18f8b45fb6a4479e00a801007756 |
| georgia_milestones_end_of_course_eoc_lexile_scores_2021.csv | b14b26817b55e8ae5cfe2e4f01bfad23dff0e0b5d699c247a1388b98961f1c98 |
| georgia_milestones_end_of_course_eoc_lexile_scores_2022.csv | eb7c79c757695bd3c75fb98aa9e1ade9240133b21c0e80ceb2e26ba1ca987ecb |
| georgia_milestones_end_of_course_eoc_lexile_scores_2023.csv | beb6bf47d40f36f2f7aa37a91e7b1951202d8d16c6100d9e7a623e3851ce6d10 |
| georgia_milestones_end_of_course_eoc_lexile_scores_2024.csv | 0a10f4ac8d2f40d759016dd07ff7865ace5e656271b0d70994887d68dfb29348 |

## Summary

Georgia Milestones End-of-Course (EOC) Lexile assessment results for the state's English Language Arts EOC tests — **9th Grade Literature and Composition** and **American Literature and Composition**. Rather than scoring the EOC overall, this dataset reports the Lexile reading-measure distribution derived from each test. Each row reports, for one entity (state / district / school) and one subject, five measures:

- **TOTAL_STUDENTS_TESTED** — count of students who took the subject's EOC.
- **STUDENTS_WITH_LEXILE** — count of those students whose EOC produced a usable Lexile measure (typically equal to, or slightly less than, `TOTAL_STUDENTS_TESTED`).
- **LEXILE_ON_OR_ABOVE_MIDPOINT** — count of students whose Lexile measure was at or above the grade-level midpoint (GOSA's "on-track reader" threshold). Confirmed to be a raw count, not a percentage (at the state level in 2024: 69,660 out of 132,835 students with a Lexile, or 52.4%).
- **NO_LEXILE_SCORE** — count of students who did not receive a Lexile measure. In practice this column is dominated by the `TFS` suppression marker ("Too Few Students"); only 1–37 rows per year ever contain a numeric value (range 10–488).
- **AVG_LEXILE_SCORE** — average Lexile measure among students who received one, reported to one decimal place (observed range 707.0–1679.3 across all years and detail levels).

**Subject coverage changes mid-range.** 2015–2019 and 2021 contain both subjects; 2022–2024 contain **only** `American Literature and Composition`. 2021 has only 84 `9th Grade Literature and Composition` rows (vs. 663 `American Literature` rows) — this is partial / COVID-impacted coverage. 2020 is absent entirely.

Only the "All Students" population is reported — there are **no demographic subgroup breakdowns** in this dataset.

## Eras

### Era 1: 2015–2024 (single era — identical 12-column tidy long format)

Every file has the same 12-column header, in the same order. This is a single-era dataset; the only cross-year differences are (a) subject coverage, (b) `INSTN_NUMBER` zero-padding, and (c) suppression behavior — all described in ETL Considerations.

| Column | Description |
|--------|-------------|
| SCHOOL_YEAR | Ending calendar year of the school year (e.g., `2024` = school year 2023–24). Stored as a 4-digit string; always equals the year in the filename. |
| DETAIL_LEVEL | Geographic/organizational aggregation level. Exactly three values: `State Level`, `District Level`, `School Level`. |
| SCHOOL_DSTRCT_CD | District code. 3-digit local districts (`601`–`793`) or 7-digit state-chartered entity codes (`7820xxx`, `7830xxx`). Set to the literal string `"All"` on State Level rows. |
| SCHOOL_DSTRCT_NM | District name in title case (e.g., `Fulton County`). Set to `"All"` on State Level rows. |
| INSTN_NUMBER | Institution (school) number. Zero-padded to 4 characters in 2021–2024 (e.g. `0100`); not zero-padded in 2015–2019 (3–4 characters, e.g. `100` or `4060`). Set to `"All"` on District and State Level rows. |
| INSTN_NAME | School name in title case. Set to `"All"` on District and State Level rows. |
| SUBJECT_CODE | EOC subject. `9th Grade Literature and Composition` or `American Literature and Composition` (the 9th-grade subject is absent after 2021). |
| TOTAL_STUDENTS_TESTED | Integer count of students tested. Can be suppressed with `TFS`. |
| STUDENTS_WITH_LEXILE | Integer count of tested students who received a Lexile measure. Can be suppressed with `TFS`. |
| LEXILE_ON_OR_ABOVE_MIDPOINT | Integer count of students whose Lexile met or exceeded the grade-level midpoint. Can be suppressed with `TFS`. This is a **count**, not a percentage. |
| NO_LEXILE_SCORE | Integer count of tested students who did not receive a Lexile. Overwhelmingly reported as `TFS` (677–1386 of ~679–1489 rows per year); only 1–37 rows per year hold a numeric value. |
| AVG_LEXILE_SCORE | Average Lexile reading measure (one decimal, observed 707.0–1679.3). Can be suppressed with `TFS`. |

#### Sample Data

Representative file: `georgia_milestones_end_of_course_eoc_lexile_scores_2024.csv` (681 rows × 12 columns).

```
shape: (5, 12)
┌─────────────┬──────────────┬──────────────────┬────────────────────┬──────────────┬───────────────────────────┬─────────────────────────────────────┬───────────────────────┬──────────────────────┬─────────────────────────────┬─────────────────┬──────────────────┐
│ SCHOOL_YEAR ┆ DETAIL_LEVEL ┆ SCHOOL_DSTRCT_CD ┆ SCHOOL_DSTRCT_NM   ┆ INSTN_NUMBER ┆ INSTN_NAME                ┆ SUBJECT_CODE                        ┆ TOTAL_STUDENTS_TESTED ┆ STUDENTS_WITH_LEXILE ┆ LEXILE_ON_OR_ABOVE_MIDPOINT ┆ NO_LEXILE_SCORE ┆ AVG_LEXILE_SCORE │
│ str         ┆ str          ┆ str              ┆ str                ┆ str          ┆ str                       ┆ str                                 ┆ str                   ┆ str                  ┆ str                         ┆ str             ┆ str              │
╞═════════════╪══════════════╪══════════════════╪════════════════════╪══════════════╪═══════════════════════════╪═════════════════════════════════════╪═══════════════════════╪══════════════════════╪═════════════════════════════╪═════════════════╪══════════════════╡
│ 2024        ┆ School Level ┆ 721              ┆ Richmond County    ┆ 0100         ┆ Cross Creek High School   ┆ American Literature and Composition ┆ 287                   ┆ 287                  ┆ 65                          ┆ TFS             ┆ 1119.9           │
│ 2024        ┆ School Level ┆ 611              ┆ Bibb County        ┆ 0204         ┆ Rutland High School       ┆ American Literature and Composition ┆ 214                   ┆ 214                  ┆ 88                          ┆ TFS             ┆ 1212.8           │
│ 2024        ┆ School Level ┆ 786              ┆ Social Circle City ┆ 0300         ┆ Social Circle High School ┆ American Literature and Composition ┆ 119                   ┆ 119                  ┆ 67                          ┆ TFS             ┆ 1320.2           │
│ 2024        ┆ School Level ┆ 675              ┆ Henry County       ┆ 3050         ┆ McDonough High School     ┆ American Literature and Composition ┆ 375                   ┆ 375                  ┆ 128                         ┆ TFS             ┆ 1178.2           │
│ 2024        ┆ School Level ┆ 713              ┆ Pierce County      ┆ 0182         ┆ Pierce County High School ┆ American Literature and Composition ┆ 213                   ┆ 213                  ┆ 150                         ┆ TFS             ┆ 1402.8           │
└─────────────┴──────────────┴──────────────────┴────────────────────┴──────────────┴───────────────────────────┴─────────────────────────────────────┴───────────────────────┴──────────────────────┴─────────────────────────────┴─────────────────┴──────────────────┘
```

#### Statistics

`describe()` on the representative 2024 file (all columns read as `str`, so only `count`, `null_count`, `min`, `max` are meaningful):

```
shape: (9, 13)
┌────────────┬─────────────┬────────────────┬──────────────────┬──────────────────┬──────────────┬──────────────────────────────┬─────────────────────────────────────┬───────────────────────┬──────────────────────┬─────────────────────────────┬─────────────────┬──────────────────┐
│ statistic  ┆ SCHOOL_YEAR ┆ DETAIL_LEVEL   ┆ SCHOOL_DSTRCT_CD ┆ SCHOOL_DSTRCT_NM ┆ INSTN_NUMBER ┆ INSTN_NAME                   ┆ SUBJECT_CODE                        ┆ TOTAL_STUDENTS_TESTED ┆ STUDENTS_WITH_LEXILE ┆ LEXILE_ON_OR_ABOVE_MIDPOINT ┆ NO_LEXILE_SCORE ┆ AVG_LEXILE_SCORE │
│ str        ┆ str         ┆ str            ┆ str              ┆ str              ┆ str          ┆ str                          ┆ str                                 ┆ str                   ┆ str                  ┆ str                         ┆ str             ┆ str              │
╞════════════╪═════════════╪════════════════╪══════════════════╪══════════════════╪══════════════╪══════════════════════════════╪═════════════════════════════════════╪═══════════════════════╪══════════════════════╪═════════════════════════════╪═════════════════╪══════════════════╡
│ count      ┆ 681         ┆ 681            ┆ 681              ┆ 681              ┆ 681          ┆ 681                          ┆ 681                                 ┆ 681                   ┆ 681                  ┆ 681                         ┆ 681             ┆ 681              │
│ null_count ┆ 0           ┆ 0              ┆ 0                ┆ 0                ┆ 0            ┆ 0                            ┆ 0                                   ┆ 0                     ┆ 0                    ┆ 0                           ┆ 0               ┆ 0                │
│ min        ┆ 2024        ┆ District Level ┆ 601              ┆ All              ┆ 0100         ┆ AZ Kelsey Academy            ┆ American Literature and Composition ┆ 10                    ┆ 10                   ┆ 10                          ┆ 10              ┆ 1001.3           │
│ max        ┆ 2024        ┆ State Level    ┆ All              ┆ Worth County     ┆ All          ┆ iGrad Virtual Academy School ┆ American Literature and Composition ┆ TFS                   ┆ TFS                  ┆ TFS                         ┆ TFS             ┆ TFS              │
└────────────┴─────────────┴────────────────┴──────────────────┴──────────────────┴──────────────┴──────────────────────────────┴─────────────────────────────────────┴───────────────────────┴──────────────────────┴─────────────────────────────┴─────────────────┴──────────────────┘
```

Numeric coverage (after `cast(Float64, strict=False)` on the 2024 file):

| Column | Non-null numeric rows | Min | Max | Mean |
|--------|-----------------------|-----|-----|------|
| TOTAL_STUDENTS_TESTED | 650 of 681 | 10 | 132,865 | 612.98 |
| STUDENTS_WITH_LEXILE | 650 of 681 | 10 | 132,835 | 612.84 |
| LEXILE_ON_OR_ABOVE_MIDPOINT | 611 of 681 | 10 | 69,660 | 341.71 |
| NO_LEXILE_SCORE | 5 of 681 | 10 | 87 | 27.20 |
| AVG_LEXILE_SCORE | 650 of 681 | 873.3 | 1,645.7 | 1254.82 |

Row counts per file: 2015=1422, 2016=1442, 2017=1467, 2018=1477, 2019=1489, 2021=747, 2022=678, 2023=679, 2024=681. The drop in 2021+ reflects the near-elimination of 9th-grade coverage.

#### Null Counts

No literal null values appear in any column of any file — every cell contains either a numeric string or the literal `"All"` / `"TFS"` sentinel. Example (2024):

```
shape: (1, 12)
┌─────────────┬──────────────┬──────────────────┬──────────────────┬──────────────┬────────────┬──────────────┬───────────────────────┬──────────────────────┬─────────────────────────────┬─────────────────┬──────────────────┐
│ SCHOOL_YEAR ┆ DETAIL_LEVEL ┆ SCHOOL_DSTRCT_CD ┆ SCHOOL_DSTRCT_NM ┆ INSTN_NUMBER ┆ INSTN_NAME ┆ SUBJECT_CODE ┆ TOTAL_STUDENTS_TESTED ┆ STUDENTS_WITH_LEXILE ┆ LEXILE_ON_OR_ABOVE_MIDPOINT ┆ NO_LEXILE_SCORE ┆ AVG_LEXILE_SCORE │
╞═════════════╪══════════════╪══════════════════╪══════════════════╪══════════════╪════════════╪══════════════╪═══════════════════════╪══════════════════════╪═════════════════════════════╪═════════════════╪══════════════════╡
│ 0           ┆ 0            ┆ 0                ┆ 0                ┆ 0            ┆ 0          ┆ 0            ┆ 0                     ┆ 0                    ┆ 0                           ┆ 0               ┆ 0                │
└─────────────┴──────────────┴──────────────────┴──────────────────┴──────────────┴────────────┴──────────────┴───────────────────────┴──────────────────────┴─────────────────────────────┴─────────────────┴──────────────────┘
```

"Missing" data is encoded by `"TFS"` (for suppressed metrics) or `"All"` (for aggregated / non-applicable geography), not by `null`.

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| DETAIL_LEVEL | `District Level`, `School Level`, `State Level` — per-year 2024 counts: School Level=485, District Level=195, State Level=1. 2015–2021 have 2 State Level rows (one per subject); 2022–2024 have 1 (only `American Literature` remains). |
| SUBJECT_CODE | `9th Grade Literature and Composition` (present 2015–2021; 2021 has only 84 rows), `American Literature and Composition` (present every year, dominant volume). |
| SCHOOL_DSTRCT_NM | ~196 distinct district / state-charter names per year (e.g., `Gwinnett County`, `DeKalb County`, `Fulton County`, `Cobb County`, `Atlanta Public Schools`, ..., plus the literal `All` for State Level rows). |
| INSTN_NAME | 477 distinct values in 2024 (476 school names plus the literal `All` for aggregated rows). The string `All` appears 196 times — once per district-level row. |

#### Suppression Markers

| Column | Non-Numeric Values (counts shown for 2024 representative file) |
|--------|------|
| SCHOOL_YEAR | none (4-digit year string only). |
| SCHOOL_DSTRCT_CD | `All` — 1 row (State Level). |
| INSTN_NUMBER | `All` — 196 rows (District + State Level aggregates). |
| TOTAL_STUDENTS_TESTED | `TFS` — 31 rows. |
| STUDENTS_WITH_LEXILE | `TFS` — 31 rows. |
| LEXILE_ON_OR_ABOVE_MIDPOINT | `TFS` — 70 rows. |
| NO_LEXILE_SCORE | `TFS` — 676 of 681 rows (the column is numeric only in rare cases). |
| AVG_LEXILE_SCORE | `TFS` — 31 rows. |

`"All"` is an aggregation sentinel (not suppression); `"TFS"` ("Too Few Students") is the single suppression marker used throughout. The 2024 behaviour shown above is typical: `TFS` counts on metric columns stay in a narrow band (typically 31–70 rows), while `NO_LEXILE_SCORE` is almost always `TFS` because very few students at any given school fail to receive a Lexile measure.

## ETL Considerations

Points to watch when transforming bronze to gold:

1. **Three-level tidy long format — filter by `DETAIL_LEVEL`.** Each file mixes state / district / school rows in one table, distinguished only by the `DETAIL_LEVEL` column. The transform should split into separate gold files (state, district, school) using `DETAIL_LEVEL` **and** verify that sentinel values are consistent: `SCHOOL_DSTRCT_CD = "All"` and `INSTN_NUMBER = "All"` at State Level; `INSTN_NUMBER = "All"` at District Level; neither equal to `"All"` at School Level. Do not try to identify aggregation rows by looking for missing values — the file uses the literal string `"All"`.
2. **`INSTN_NUMBER` zero-padding changes in 2021.** 2015–2019 files report institution numbers as 3- or 4-character strings with leading zeros stripped (e.g., `100`, `101`, `301`, `4060`). 2021–2024 files are zero-padded to 4 characters (`0100`, `0101`, `0300`). The transform must normalize this — preferably by left-padding all values to 4 characters (`str.zfill(4)`), matching Georgia's canonical school-code format. Without normalization, the same physical school will appear as two different keys across eras (`101` vs `0101`).
3. **`SCHOOL_DSTRCT_CD` has two distinct formats.** Local school districts are 3-digit numeric strings (`601`–`793`). State Charter Schools I & II entities are 7-digit numeric strings (`7820xxx`, `7830xxx`). Keep them as strings; do not cast to int (you would lose the 7-digit category's leading 7 and collapse `0100` school codes too). Zero-padding district codes to a fixed width would corrupt the 7-digit charter codes, so leave district codes as-is.
4. **`SUBJECT_CODE` is a fact_categorical, not a metric.** Every row already represents a single subject. The 9th-Grade subject phases out after 2021 (and has only 84 rows in 2021 itself). Do not try to reshape subjects into columns — keep one row per subject.
5. **All metrics are stored as strings with `"TFS"` suppression.** Cast with `strict=False` so `TFS` becomes `null`. Do not interpret `TFS` as zero. In 2024 this affects 31–70 rows per metric column out of 681 (4.5%–10.3%). Suppression rates vary year-to-year but are generally low.
6. **`LEXILE_ON_OR_ABOVE_MIDPOINT` is a count, not a percentage.** Confirmed at the state level (2024: 69,660 / 132,835 = 52.4%). If a derived "percent on or above midpoint" is desired in gold, compute it as `LEXILE_ON_OR_ABOVE_MIDPOINT / STUDENTS_WITH_LEXILE` (not over `TOTAL_STUDENTS_TESTED`, since the denominator is the population with a valid Lexile).
7. **`NO_LEXILE_SCORE` is nearly always `TFS`.** Only 1–37 rows per year hold a numeric value (smallest = 10, largest = 488). **It is NOT derivable from the other counts** (corrected 2026-06-11; the earlier claim that the complement "typically recovers the same number" was wrong): of the 140 rows across all 9 files where `TOTAL_STUDENTS_TESTED`, `STUDENTS_WITH_LEXILE`, and `NO_LEXILE_SCORE` are all numeric, 45 disagree with `TOTAL_STUDENTS_TESTED − STUDENTS_WITH_LEXILE` (per-year disagreements 1–7; largest gap 99 students, in 2021). It is GOSA's independently published count and must be retained in gold as-is; do not author a with+without=tested reconciliation check.
8. **`AVG_LEXILE_SCORE` is already decimal.** It is reported to one decimal place (e.g., `1119.9`). Parse as `Float64`; do not multiply by 100 or treat as a percentage. Observed range 707.0–1679.3, consistent with the Lexile scale.
9. **2020 is absent and not a data error.** EOC testing was cancelled statewide. The transform should simply not produce a 2020 partition (do not pad with null rows).
10. **2021 is a COVID-impacted year.** Only ~50% of the usual row count (747 vs. ~1,480) and the 9th-grade subject has just 84 rows (mostly district- and state-level, with sparse school coverage). Keep the data but flag downstream consumers via documentation.
11. **No demographic breakdown.** Every row is implicitly "All Students." In the gold fact table this means the `demographic` column will be constant — consider whether to omit it (per the gold-schema classification guidance: "omit if always 'All Students'") or include it for consistency with other EOC fact tables.
12. **`SCHOOL_YEAR` is already an integer-like string.** Cast to `Int32` or `UInt16`. It always matches the filename year; no cross-era year-offset correction is needed.
13. **Entity name fields duplicate information in dimensions.** `SCHOOL_DSTRCT_NM` and `INSTN_NAME` should not land in the fact table — they belong in the `districts` and `schools` dimension tables. Use `SCHOOL_DSTRCT_CD` and the normalized `INSTN_NUMBER` as the FKs.
14. **Checksum the bronze inputs with the numbers in "File Checksums" before every transform run** (the pipeline already enforces this via `--allow-stale-bronze` gating). The 2020 gap means the file set is complete at 9 files, not 10.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| SCHOOL_YEAR | fact_key | year | Integer (4-digit ending calendar year). Partition column. |
| DETAIL_LEVEL | not_in_gold | — | Used to split rows into state/district/school gold outputs; not retained as a column (the output file choice encodes it). |
| SCHOOL_DSTRCT_CD | fact_key | district_code | String; 3-digit for local districts, 7-digit for state charter entities. FK to the education districts dimension. Excluded from the state-level fact output. |
| SCHOOL_DSTRCT_NM | dimension_attribute | — | `district_name` in districts dimension. Do not retain in the fact table. |
| INSTN_NUMBER | fact_key | school_code | String; zero-pad to 4 characters during transform to reconcile 2015–2019 (`100`) with 2021–2024 (`0100`). FK to the education schools dimension. Included only in the school-level fact output. |
| INSTN_NAME | dimension_attribute | — | `school_name` in schools dimension. Do not retain in the fact table. |
| SUBJECT_CODE | fact_categorical | subject | Two values: `9th Grade Literature and Composition`, `American Literature and Composition`. Normalize to the §16 canonical snake_case forms `9th_grade_literature_and_composition` and `american_literature_and_composition` (per `src/utils/subjects.py`, which resolves `ninth_grade_…` spellings to the `9th_grade_…` canonical; gold names corrected 2026-06-11). |
| TOTAL_STUDENTS_TESTED | fact_metric | num_tested | Integer count. `TFS` → null. |
| STUDENTS_WITH_LEXILE | fact_metric | num_with_lexile | Integer count. `TFS` → null. (Gold name corrected 2026-06-11 to the §16 canonical `num_with_lexile` — data-cleaning-standards §16 cites this exact name as the condition-count convention.) |
| LEXILE_ON_OR_ABOVE_MIDPOINT | fact_metric | num_at_or_above_lexile_midpoint | Integer **count** (not a percentage). `TFS` → null. (Gold name corrected 2026-06-11 to match the v1 contract / §16 `num_*` + `_or_above` conventions.) |
| NO_LEXILE_SCORE | fact_metric | num_without_lexile | Integer count; ~94–99% suppressed to `TFS` → null. NOT derivable from the other counts (see ETL consideration 7) — retained as GOSA's independently published value. (Gold name corrected 2026-06-11 to the §16 canonical `num_without_lexile`.) |
| AVG_LEXILE_SCORE | fact_metric | avg_lexile_score | Float (one decimal). `TFS` → null. Observed range 707.0–1679.3. Lexile scale — not percentage-like; do not rescale. |
| (implicit demographic) | fact_key (optional) | demographic | Always `All Students`. Per gold-schema guidance, omit from the fact table since it is constant. |
