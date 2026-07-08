# georgia_milestones_end_of_grade_eog_lexile_scores — Bronze Data Structure

## Overview

- Topic: georgia_milestones_end_of_grade_eog_lexile_scores
- Source: gosa
- Files: 9 files spanning 2015-2024 (2020 is missing — no testing due to COVID-19)
- Unreadable files: none
- Year representation: `SCHOOL_YEAR` column (integer, 4-digit, spring-year convention — e.g., `2024` means school year 2023-2024). Filename year (`..._YYYY.csv`) matches the `SCHOOL_YEAR` column value exactly.
- Filename-to-data year offset: same (filename year = data year)
- Detail levels: state, district, school (identified via `DETAIL_LEVEL` column)
- Percentage scale: not applicable — all metrics are counts (integers) or raw Lexile scores (floats). No percentage columns in bronze.
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| georgia_milestones_end_of_grade_eog_lexile_scores_2015.csv | dcab62fcfe16d591d25a50799ebcb5b6678d35f8b9dc98b438a7c64e0d6b6783 |
| georgia_milestones_end_of_grade_eog_lexile_scores_2016.csv | 0d94267df59f9d07e662d936094abf7f9f04be4abdadc43473a0942153ebe876 |
| georgia_milestones_end_of_grade_eog_lexile_scores_2017.csv | db072200ab32f031f4e0043605cb83a29fea2645c1c875147638743ee40a5cd7 |
| georgia_milestones_end_of_grade_eog_lexile_scores_2018.csv | 14caa6626a282d7a313a211cd9fab322f5eb56924fc42c8e2f51f70bb8b1cfc8 |
| georgia_milestones_end_of_grade_eog_lexile_scores_2019.csv | 5c8bcfbcde94fe10532e8accfcfda852c920013f85a302c7d57da60c17b5b5d3 |
| georgia_milestones_end_of_grade_eog_lexile_scores_2021.csv | 1b357ba87314f1153360aa4444443dd52f4f3b34667276c2f2d3a412ee13e306 |
| georgia_milestones_end_of_grade_eog_lexile_scores_2022.csv | 499d34b960a15782126dfefce033feaeada948015516907da8fc841bda9435fc |
| georgia_milestones_end_of_grade_eog_lexile_scores_2023.csv | b7062c0e7dbce77f09cbfcb264ce97e35f91aef25c8b578804cf0a3ffe4f336a |
| georgia_milestones_end_of_grade_eog_lexile_scores_2024.csv | 973e77461f2f07e660e253f58868df078e073807be09c032d05113fa9f4bb68d |

## Summary

This dataset reports **Lexile reading score outcomes** for students taking the Georgia Milestones End-of-Grade (EOG) English Language Arts assessment in grades 3-8. Each row represents a single grade level at a specific geography (state / district / school). Metrics include:

- `TOTAL_STUDENTS_TESTED` — students who took the EOG ELA assessment
- `STUDENTS_WITH_LEXILE` — students who received a Lexile score
- `LEXILE_ON_OR_ABOVE_MIDPOINT` — students whose Lexile score met or exceeded the grade-band "stretch midpoint" (a national reading-level benchmark)
- `NO_LEXILE_SCORE` — students tested but who did not receive a Lexile score (e.g., because they did not meet the minimum scale-score threshold)
- `AVG_LEXILE_SCORE` — mean Lexile score for the grade/geography (typical range ~400-1400L)

No demographic breakouts are provided — this dataset is strictly grade-by-geography aggregates.

## Eras

### Era 1: 2015-2024 (all years share identical column names)

| Column | Description |
|--------|-------------|
| SCHOOL_YEAR | Reporting school year (spring-year convention, e.g., `2024` = 2023-2024). Integer. |
| DETAIL_LEVEL | Geographic aggregation level: `State Level`, `District Level`, or `School Level`. |
| SCHOOL_DSTRCT_CD | District/LEA code. 3-digit for traditional systems (e.g., `601` = Appling County); 7-digit for state charter schools (e.g., `7830643`). Literal string `"All"` at state-level rollup rows. Stored as string. |
| SCHOOL_DSTRCT_NM | District/LEA name. Literal string `"All"` at state-level rollup rows. |
| INSTN_NUMBER | Institution number (4-digit zero-padded string, e.g., `0200`). Literal string `"All"` at district-level and state-level rollup rows. |
| INSTN_NAME | School name. Literal string `"All"` at district-level and state-level rollup rows. |
| ACDMC_LVL_CD | Academic level code = grade level. Stored in the raw CSV as a quoted, zero-padded 2-char string (`"03"`–`"08"`) in every year; schema inference parses it as integer 3–8. Read as string to preserve the padding. |
| TOTAL_STUDENTS_TESTED | Count of students who took the EOG ELA assessment. Integer in 2015-2019; string (with `TFS` suppression) in 2021-2024. |
| STUDENTS_WITH_LEXILE | Count of tested students who received a Lexile score. Integer in 2015-2019; string (with `TFS` suppression) in 2021-2024. |
| LEXILE_ON_OR_ABOVE_MIDPOINT | Count of students whose Lexile score met or exceeded the grade-band stretch midpoint. Integer in 2015-2019; string (with `TFS` suppression) in 2021-2024. |
| NO_LEXILE_SCORE | Count of tested students who did not receive a Lexile score. Integer in 2015-2019; string (with `TFS` suppression) in 2021-2024. |
| AVG_LEXILE_SCORE | Mean Lexile score for the grade/geography. Float in 2015-2019; string (with `TFS` suppression) in 2021-2024. |

> Column *names* are identical across all nine files, so this is a single era. However, the **dtype and null/suppression semantics change in 2021** (pre-COVID vs post-COVID suppression regime) — see ETL Considerations below.

#### Sample Data (representative file: 2024)

```
shape: (5, 12)
SCHOOL_YEAR  DETAIL_LEVEL   SCHOOL_DSTRCT_CD  SCHOOL_DSTRCT_NM                                      INSTN_NUMBER  INSTN_NAME                          ACDMC_LVL_CD  TOTAL_STUDENTS_TESTED  STUDENTS_WITH_LEXILE  LEXILE_ON_OR_ABOVE_MIDPOINT  NO_LEXILE_SCORE  AVG_LEXILE_SCORE
2024         School Level   721               Richmond County                                       3050          Bayvale Elementary School           4             57                     57                    TFS                          TFS              611.3
2024         School Level   631               Clayton County                                        0200          Roberta T. Smith Elementary School  4             132                    132                   19                           TFS              607
2024         School Level   7830643           State Charter Schools II- Amana Academy West Atlanta  0643          Amana Academy West Atlanta          4             32                     32                    14                           TFS              844.8
2024         School Level   684               Jones County                                          0106          Gray Station Middle School          7             201                    201                   139                          TFS              1174.6
2024         School Level   715               Polk County                                           0274          Eastside Elementary School          5             109                    109                   50                           TFS              928.3
```

#### Statistics

**2024 file (6,917 rows — suppression era):** All measurement columns are stored as strings because of `TFS`. After `cast(Float64, strict=False)`, describe yields numeric statistics equivalent to the 2019 pattern but with more nulls (from `TFS` conversions).

**2019 file (6,758 rows — pre-suppression era):**

```
statistic    SCHOOL_YEAR  ACDMC_LVL_CD  TOTAL_STUDENTS_TESTED  STUDENTS_WITH_LEXILE  LEXILE_ON_OR_ABOVE_MIDPOINT  NO_LEXILE_SCORE  AVG_LEXILE_SCORE
count        6758         6758          6617                   6615                  6615                         6617             6615
null_count   0            0             141                    143                   143                          141              143
mean         2019         5.06          361.87                 358.57                199.21                       3.45             901.48
std          0            1.65          4053.93                4017.71               2252.32                      85.96            189.79
min          2019         3             10                     10                    0                            0                446.7
50%          2019         5             117                    117                   61                           0                909.5
max          2019         8             136443                 136209                82633                        6697             1430.2
```

(Max values reflect state-level rollup rows.)

**Row counts by year:**

| Year | Rows |
|-----:|-----:|
| 2015 | 6,641 |
| 2016 | 6,664 |
| 2017 | 6,692 |
| 2018 | 6,741 |
| 2019 | 6,758 |
| 2021 | 6,768 |
| 2022 | 6,846 |
| 2023 | 6,881 |
| 2024 | 6,917 |

#### Null Counts

> Correction (2026-06-11, rebuild review): the 2015-2018 metric-column null counts below were originally recorded as 0 — raw-bronze grep counts (empty CSV fields) match the transform manifest exactly and are now shown. Empty metric fields exist in EVERY 2015-2019 file, not just 2019.

| Year | SCHOOL_YEAR | DETAIL_LEVEL | SCHOOL_DSTRCT_CD | SCHOOL_DSTRCT_NM | INSTN_NUMBER | INSTN_NAME | ACDMC_LVL_CD | TOTAL_STUDENTS_TESTED | STUDENTS_WITH_LEXILE | LEXILE_ON_OR_ABOVE_MIDPOINT | NO_LEXILE_SCORE | AVG_LEXILE_SCORE |
|------|------------:|-------------:|-----------------:|-----------------:|-------------:|-----------:|-------------:|----------------------:|---------------------:|----------------------------:|----------------:|-----------------:|
| 2015 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 129 | 131 | 131 | 129 | 131 |
| 2016 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 126 | 127 | 127 | 126 | 127 |
| 2017 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 128 | 128 | 128 | 128 | 128 |
| 2018 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 136 | 137 | 137 | 136 | 137 |
| 2019 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 141 | 143 | 143 | 141 | 143 |
| 2021 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2022 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2023 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2024 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

In 2021-2024, zero true nulls because suppressed values are encoded as the literal string `"TFS"` instead of null. In 2019, genuine nulls appear where values are missing (141-143 rows). 2015-2018 have no nulls at all.

#### Categorical Columns

**`DETAIL_LEVEL`**

| Value | 2024 rows | 2015 rows |
|-------|----------:|----------:|
| School Level | 5,613 | 5,471 |
| District Level | 1,298 | 1,164 |
| State Level | 6 | 6 |

The 6 state-level rows each correspond to one grade (3-8).

**`ACDMC_LVL_CD`** (integer grade level)

| ACDMC_LVL_CD | 2024 rows | 2015 rows |
|-------------:|----------:|----------:|
| 3 | 1,480 | 1,440 |
| 4 | 1,477 | 1,442 |
| 5 | 1,471 | 1,438 |
| 6 | 839 | 788 |
| 7 | 822 | 769 |
| 8 | 828 | 764 |

Grades 3-5 are typically elementary; grades 6-8 are middle school. Middle-school row counts are lower because fewer institutions serve those grades.

Other columns that appear "categorical" to the naive classifier (`SCHOOL_DSTRCT_CD`, `SCHOOL_DSTRCT_NM`, `INSTN_NUMBER`, `INSTN_NAME`) are really identifiers with the literal `"All"` inserted for rollup rows — see the Suppression Markers / aggregation value table below.

#### Suppression Markers

Two distinct kinds of non-numeric tokens appear in this dataset:

**(a) Small-cell suppression in measurement columns (2021-2024 only):**

| Column | Non-Numeric Values (2015-2019) | Non-Numeric Values (2021-2024) |
|--------|--------------------------------|--------------------------------|
| TOTAL_STUDENTS_TESTED | none (pure integer) | `TFS` |
| STUDENTS_WITH_LEXILE | none (pure integer) | `TFS` |
| LEXILE_ON_OR_ABOVE_MIDPOINT | none (pure integer) | `TFS` |
| NO_LEXILE_SCORE | none (pure integer) | `TFS` |
| AVG_LEXILE_SCORE | none (pure float) | `TFS` |

`TFS` = "too few students" — GOSA's small-cell suppression marker, introduced in 2021. Cast with `strict=False` to convert `TFS` to null.

**2024 suppression snapshot** — rows where the column value is `TFS`:

| Column | TFS rows | % of 6,917 |
|--------|---------:|-----------:|
| NO_LEXILE_SCORE | 6,870 | 99.3% |
| AVG_LEXILE_SCORE | ~few hundred | ~few % |
| TOTAL_STUDENTS_TESTED | minor | <5% |
| STUDENTS_WITH_LEXILE | minor | <5% |
| LEXILE_ON_OR_ABOVE_MIDPOINT | moderate | partial |

Nearly all `NO_LEXILE_SCORE` values are suppressed from 2021 onward — this column contributes minimal signal in the suppression era.

**(b) Aggregation placeholders in identifier columns (all years):**

| Column | Aggregation Value | Where it appears |
|--------|-------------------|------------------|
| SCHOOL_DSTRCT_CD | `"All"` | `State Level` rows only |
| SCHOOL_DSTRCT_NM | `"All"` | `State Level` rows only |
| INSTN_NUMBER | `"All"` | `State Level` and `District Level` rows |
| INSTN_NAME | `"All"` | `State Level` and `District Level` rows |

These are not true suppression markers — they indicate "this row is a rollup at a higher level than this identifier".

## ETL Considerations

1. **Dtype inconsistency across years (critical).** Even though column *names* are identical across 2015-2024, the *dtypes* differ:
   - 2015-2019: `TOTAL_STUDENTS_TESTED`, `STUDENTS_WITH_LEXILE`, `LEXILE_ON_OR_ABOVE_MIDPOINT`, `NO_LEXILE_SCORE` are pure `Int64`; `AVG_LEXILE_SCORE` is pure `Float64`.
   - 2021-2024: All five measurement columns are `Utf8` (String) because of `TFS` suppression markers.
   - Always read CSVs with `infer_schema_length=0` (or explicit schema=string for these columns) and cast with `pl.col(...).cast(Float64, strict=False)` so `TFS` becomes null without raising. This handles both eras uniformly.

2. **Missing 2020.** The 2020 file is absent because Georgia waived EOG testing that year due to COVID-19 (federal waiver from U.S. Department of Education). Do not interpolate. Downstream validation should accept a gap.

3. **`NO_LEXILE_SCORE` is nearly fully suppressed in 2021+.** 99.3% of 2024 rows are `TFS`, so the column contributes minimal signal post-2020. Consider whether to include it in gold at all or only preserve it for the earlier era.

4. **Aggregation rows use the literal string `"All"`, not null.** Rows where `DETAIL_LEVEL = "State Level"` have `SCHOOL_DSTRCT_CD = "All"`, `SCHOOL_DSTRCT_NM = "All"`, `INSTN_NUMBER = "All"`, `INSTN_NAME = "All"`. Rows where `DETAIL_LEVEL = "District Level"` have `INSTN_NUMBER = "All"` and `INSTN_NAME = "All"`. Per data-cleaning-standards, split the bronze rows by `DETAIL_LEVEL` into separate gold files (state / district / school) — the `"All"` placeholders should not leak into FK columns.

5. **District code format is variable-length.** `SCHOOL_DSTRCT_CD` is 3-digit for traditional LEAs (e.g., `601`) and 7-digit for state charter schools (e.g., `7830643`). Store as string — never cast to integer — to preserve the full code and any leading zeros. The distinct-code count (231 in 2024) also includes the `"All"` placeholder.

6. **School institution number is 4-digit zero-padded in every year (no exceptions).** `INSTN_NUMBER` is a 4-character zero-padded string (e.g., `0200`, `0391`) on every school-level row in all 9 files — verified 2026-06-11 via raw field-length counts (`awk -F',' '{print length($5)}'`: only 4-char codes and the 3-char `"All"` placeholder appear). An earlier claim of "one 3-digit code in 2024" was the `"All"` placeholder itself, not a real code. Read as string — CSV parsing may otherwise strip leading zeros.

7. **`SCHOOL_YEAR` uses the spring-year convention.** `SCHOOL_YEAR = 2024` means the 2023-2024 academic year (administered spring 2024). This matches other GaDOE / GOSA datasets.

8. **Grade level lives in `ACDMC_LVL_CD`, not a name column.** Values 3-8 correspond directly to grades 3-8. There is no grade-label string; the transform may simply rename this to `grade_level`.

9. **No demographic dimension.** Unlike most Georgia Milestones outputs, this dataset is grade-by-geography only. Do not include a `demographic` FK; all rows are implicitly "All Students". This simplifies the gold schema.

10. **Arithmetic identity is only approximate — and badly violated on some aggregate rows.** In theory `STUDENTS_WITH_LEXILE + NO_LEXILE_SCORE = TOTAL_STUDENTS_TESTED`, but every year has violations (verified 2026-06-11 across all 9 files; counts where all three values are non-null: 403 in 2015 down to 20 in 2023). Defining diff = `(WITH + NO) - TESTED`: most deviations are small (±15), but a 2015 state-level row overshoots by +326, and 2023/2024 state- and district-level rows fall SHORT by up to 15,807 (e.g., 2023 state grade rows: TESTED=142,160, WITH=126,259, NO=94 — the published `NO_LEXILE_SCORE` aggregate does not reconcile, likely because it sums only unsuppressed cells). Do not enforce as a validation rule in any form; treat as an FYI diagnostic. The pairwise subset inequalities DO hold with zero violations in every year: `LEXILE_ON_OR_ABOVE_MIDPOINT <= STUDENTS_WITH_LEXILE <= TOTAL_STUDENTS_TESTED` and `NO_LEXILE_SCORE <= TOTAL_STUDENTS_TESTED` — those are safe to enforce.

11. **No percentage columns in bronze.** If a gold metric like `pct_on_or_above_midpoint` is desired, compute it in the transform as `LEXILE_ON_OR_ABOVE_MIDPOINT / STUDENTS_WITH_LEXILE * 100` (or `/ TOTAL_STUDENTS_TESTED`). Verify the denominator choice against a GaDOE publication before deriving.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| SCHOOL_YEAR | fact_key | year | Integer (spring-year). Partition column for gold parquet. |
| DETAIL_LEVEL | not_in_gold | — | Used only to split bronze rows into state/district/school gold files. Discarded after the split. |
| SCHOOL_DSTRCT_CD | fact_key | district_code | FK to districts dimension. Keep as string; drop rows where value is `"All"` (handled via DETAIL_LEVEL split). |
| SCHOOL_DSTRCT_NM | dimension_attribute | — | `district_name` in districts dimension; not in fact table. |
| INSTN_NUMBER | fact_key | school_code | FK to schools dimension. 4-digit zero-padded string. Only present in school-level gold file. |
| INSTN_NAME | dimension_attribute | — | `school_name` in schools dimension; not in fact table. |
| ACDMC_LVL_CD | fact_categorical | grade_level | Integer 3-8. Represents the grade the assessment was administered to. |
| TOTAL_STUDENTS_TESTED | fact_metric | students_tested | Integer count. Cast with `strict=False` to handle `TFS`. |
| STUDENTS_WITH_LEXILE | fact_metric | students_with_lexile | Integer count. Cast with `strict=False`. |
| LEXILE_ON_OR_ABOVE_MIDPOINT | fact_metric | students_on_or_above_midpoint | Integer count. Cast with `strict=False`. |
| NO_LEXILE_SCORE | fact_metric | students_without_lexile | Integer count. Cast with `strict=False`. Nearly fully suppressed 2021+; retain for pre-2020 comparability. |
| AVG_LEXILE_SCORE | fact_metric | avg_lexile_score | Float. Cast with `strict=False`. Typical range ~400-1400L. |

**Notes on gold structure:**
- No `demographic` column — all rows are implicitly "All Students" (no subgroup breakouts in bronze).
- Geography identifiers: `district_code` (and `school_code` for school-level files) are the only FKs; no FIPS/GEOID in bronze, so county linkage happens via the districts dimension.
- Optional derived percentage metrics (e.g., `pct_on_or_above_midpoint`) can be computed in the transform; document the denominator.
