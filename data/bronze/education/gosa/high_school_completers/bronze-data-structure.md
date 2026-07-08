# high_school_completers — Bronze Data Structure

## Overview

- Topic: high_school_completers
- Source: gosa
- Files: 14 CSV files spanning publication years 2011–2024 (data school years 2010-11 through 2023-24)
- Unreadable files: none
- Year representation: `LONG_SCHOOL_YEAR` column in the format `YYYY-YY` (e.g., `2023-24`), single value per file; also encoded in the filename
- Filename-to-data year offset: filename year equals the ending calendar year of the school year (e.g., `high_school_completers_2024.csv` contains school year `2023-24`; filename year = ending year of `LONG_SCHOOL_YEAR`)
- Detail levels: state (aggregate), district, school
- Percentage scale: 0–100 (`PROGRAM_PERCENT`)
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| high_school_completers_2011.csv | 2f3a87c1971f29ac7aef6c733767d5ebe7183e19916a3d5b0236932414dc7d2c |
| high_school_completers_2012.csv | ef84d9991abf58081d12bd9f5e18e2724a2b8b6503a2f0d1984ee2cacf23ee83 |
| high_school_completers_2013.csv | 08af1f2668ad5e6959153a4b96f8d383c5600c505ad366b0d201b0c89412142c |
| high_school_completers_2014.csv | 8f0861b4a25ef113070b18fdce5b82b02f27aa1301d9d2c4903ba06aedd551cf |
| high_school_completers_2015.csv | 2683733ef812abb986f1cbe29b7560147f16d34fbf17339263ebb930ed8191df |
| high_school_completers_2016.csv | 23db2aca07d42523238d270b1ebc48dac96bb276ae28cd198cc414f41799b4eb |
| high_school_completers_2017.csv | d5f81a58baf639b99549f7f7768b9dd2578c008a6dd8b8ef538778f4b224065c |
| high_school_completers_2018.csv | ba71a3555cb748eb2ae9b091e394eb19671caf588b3458d200b71411760bb3e1 |
| high_school_completers_2019.csv | 1904b974694b27d15c251992eadfabebc8e93353ea2d86d79fc443051a23a9a3 |
| high_school_completers_2020.csv | d74132641b27b56fabb3e1e3fb0777106b7181f1789edecd2f6a3e33211d15ec |
| high_school_completers_2021.csv | 6d5166f8d787788468d2d2a799b4d6e28408e5edbe115db5b26c3334245add4f |
| high_school_completers_2022.csv | ddc80fea06380bc2b331ab079d77bc622b63610eb760779bdbe5aa5dec6c0a12 |
| high_school_completers_2023.csv | f0eff08667f92222cd54c3a9e032fd9c283675b5d5379dcc09197e72dfd13d12 |
| high_school_completers_2024.csv | 020870f420006353da7778850b36b64b36d2b79473d7678cac13a378461e359f |

## Summary

Counts and percentages of high-school completers broken out by credential type (General Education Diplomas, Diplomas with College Prep Endorsements, Diplomas with Vocational Endorsements, Diplomas with Both College Prep & Vocational Endorsements, Special Education Diplomas, and Certificates of Attendance) and by `Graduates` vs. `Other Completers` category. Each row reports a completer count (`PROGRAM_TOTAL`) and the demographic's share of that credential's completers (`PROGRAM_PERCENT` — the row's count over the credential's `Total`-demographic count; see ETL note 11), cross-tabulated by gender and race/ethnicity at state, district, and school levels.

## Eras

### Era 1: 2010-11 through 2021-22 (files 2011–2022)

11 columns. Same column set across all 12 files in this era.

| Column | Description |
|--------|-------------|
| LONG_SCHOOL_YEAR | School year label in `YYYY-YY` format, e.g. `2021-22`. Single value per file. |
| SCHOOL_DSTRCT_CD | District code: 3-digit traditional district code (e.g., `601`) or 7-digit state-charter code (e.g., `7830210`). Literal `ALL` for state-aggregate rows. |
| SCHOOL_DSTRCT_NM | District name (title case). Literal `All Column Values` for state-aggregate rows. |
| INSTN_NUMBER | School code, typically 4-character zero-padded (`0100`), but **padding is inconsistent** across years — see ETL Considerations. Literal `ALL` for district/state aggregate rows. |
| INSTN_NAME | School name (title case). Literal `All Column Values` for district/state aggregate rows. |
| LABEL_SORT_ORDER | Integer 1–5 (2011 file) or 0–5 (2012–2022 files). Sort order for `LABEL_LVL_1_DESC`; redundant with that column. |
| COMPLETER_TYPE | `Graduates` or `Other Completers`. |
| LABEL_LVL_1_DESC | Credential type. 5 values in 2011 (no "General Education Diplomas") and 6 values from 2012 onward (adds `General Education Diplomas`). |
| LABEL_LVL_5_CD | Gender or race/ethnicity subgroup. 9 values: `Male`, `Female`, `Total`, `Asian`, `Black`, `Hispanic`, `Multi`, `Native American/ Alaskan Native`, `White`. |
| PROGRAM_TOTAL | Count of completers (numeric string). Suppressed rows use `TFS`. |
| PROGRAM_PERCENT | Percent share of the `COMPLETER_TYPE` total at that geography/subgroup. 0–100 scale. Suppressed rows use `TFS` (except in 2011, where no `TFS` occurs in this column). |

#### Sample Data (2022)

```
shape: (5, 11)
LONG_SCHOOL_YEAR  SCHOOL_DSTRCT_CD  SCHOOL_DSTRCT_NM  INSTN_NUMBER  INSTN_NAME                      LABEL_SORT_ORDER  COMPLETER_TYPE    LABEL_LVL_1_DESC                          LABEL_LVL_5_CD  PROGRAM_TOTAL  PROGRAM_PERCENT
2021-22           748               Ware County       ALL           All Column Values               3                 Graduates         Diplomas with Vocational Endorsements     Multi           TFS            TFS
2021-22           651               Effingham County  0390          Effingham County High School    4                 Other Completers  Special Education Diplomas                Male            4              50
2021-22           799               State Schools     1894          Georgia Academy for the Blind   1                 Graduates         Diplomas with Both College Prep. & Voc.   Hispanic        TFS            TFS
2021-22           721               Richmond County   2574          Westside High School            3                 Graduates         Diplomas with Vocational Endorsements     Total           TFS            TFS
2021-22           743               Twiggs County     ALL           All Column Values               5                 Other Completers  Certificates Of Attendance                Total           TFS            TFS
```

#### Statistics (2022)

```
shape: (9, 12)
statistic   LONG_SCHOOL_YEAR  SCHOOL_DSTRCT_CD  SCHOOL_DSTRCT_NM   INSTN_NUMBER  INSTN_NAME                    LABEL_SORT_ORDER  COMPLETER_TYPE    LABEL_LVL_1_DESC            LABEL_LVL_5_CD  PROGRAM_TOTAL  PROGRAM_PERCENT
count       35856             35856             35856              35856         35856                         35856.0           35856             35856                       35856           35856          35856
null_count  0                 0                 0                  0             0                             0.0               0                 0                           0               0              0
mean        null              null              null               null          null                          2.5               null              null                        null            null           null
std         null              null              null               null          null                          1.707849          null              null                        null            null           null
min         2021-22           601               All Column Values  0100          AZ Kelsey Academy             0.0               Graduates         Certificates Of Attendance  Asian           0              .1
max         2021-22           ALL               Worth County       ALL           iGrad Virtual Academy School  5.0               Other Completers  Special Education Diplomas  White           TFS            TFS
```

Row counts per file in Era 1: 2011=27,540; 2012=33,318; 2013=33,372; 2014=33,534; 2015=34,236; 2016=34,398; 2017=34,722; 2018=34,992; 2019=35,046; 2020=35,316; 2021=35,478; 2022=35,856.

Numeric range (2022): `PROGRAM_TOTAL` 0–114,359; `PROGRAM_PERCENT` 0.1–100.

#### Null Counts

```
shape: (1, 11)
LONG_SCHOOL_YEAR  SCHOOL_DSTRCT_CD  SCHOOL_DSTRCT_NM  INSTN_NUMBER  INSTN_NAME  LABEL_SORT_ORDER  COMPLETER_TYPE  LABEL_LVL_1_DESC  LABEL_LVL_5_CD  PROGRAM_TOTAL  PROGRAM_PERCENT
0                 0                 0                 0             0           0                 0               0                 0               0              0
```

Zero explicit nulls in every column **of the 2022 representative file**. This does NOT hold across the era: most Era 1 files suppress with *empty cells*, not `TFS`. Per-file verification (2026-06-11, polars raw-null + TFS counts):

| File | PROGRAM_TOTAL blank | PROGRAM_TOTAL `TFS` | PROGRAM_PERCENT blank | PROGRAM_PERCENT `TFS` |
|------|--------------------:|--------------------:|----------------------:|----------------------:|
| 2011 | 9,073 | 10,339 | 9,073 | 0 |
| 2012 | 21,646 | 0 | 21,646 | 0 |
| 2013 | 23,714 | 0 | 23,714 | 0 |
| 2014 | 24,121 | 0 | 24,121 | 0 |
| 2015 | 27,920 | 0 | 27,920 | 0 |
| 2016 | 28,233 | 0 | 28,233 | 0 |
| 2017 | 28,716 | 0 | 28,716 | 0 |
| 2018 | 28,968 | 2,319 | 28,968 | 0 |
| 2019 | 29,079 | 2,230 | 29,079 | 0 |
| 2020 | 29,464 | 2,130 | 29,464 | 0 |
| 2021 | 29,670 | 0 | 29,670 | 0 |
| 2022 | 0 | 30,026 | 0 | 30,026 |

Blank cells are co-located across both metric columns in every file. `TFS` counts (2011, 2018-2020) come with a *published* `PROGRAM_PERCENT`. In every file: a non-suppressed `PROGRAM_TOTAL` always has a non-suppressed `PROGRAM_PERCENT` (0 violations).

#### Categorical Columns (counts from 2022 representative file)

| Column | Distinct Values |
|--------|----------------|
| LONG_SCHOOL_YEAR | `2021-22` (35,856 rows — single value per file; varies file-to-file) |
| COMPLETER_TYPE | `Graduates` (23,904), `Other Completers` (11,952) |
| LABEL_LVL_1_DESC | `Certificates Of Attendance` (5,976), `Diplomas with Both College Prep. & Voc.` (5,976), `Diplomas with College Prep Endorsements` (5,976), `Diplomas with Vocational Endorsements` (5,976), `General Education Diplomas` (5,976), `Special Education Diplomas` (5,976). Note: 2011 file has only 5 values (no `General Education Diplomas`). |
| LABEL_LVL_5_CD | `Asian` (3,984), `Black` (3,984), `Female` (3,984), `Hispanic` (3,984), `Male` (3,984), `Multi` (3,984), `Native American/ Alaskan Native` (3,984), `Total` (3,984), `White` (3,984) |
| LABEL_SORT_ORDER | `0`–`5` in 2012–2022 (one-to-one with `LABEL_LVL_1_DESC`); `1`–`5` in 2011 |
| SCHOOL_DSTRCT_NM | 195 distinct district names plus `All Column Values` for the state aggregate row |
| INSTN_NAME | 461 distinct school names plus `All Column Values` for district/state aggregate rows |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| SCHOOL_DSTRCT_CD | `ALL` (aggregate-row marker, NOT suppression) — 54 rows in 2022 |
| INSTN_NUMBER | `ALL` (aggregate-row marker, NOT suppression) — 10,530 rows in 2022 |
| PROGRAM_TOTAL | `TFS` ("Too Few Students") — 30,026 rows in 2022. **2022 is the only Era 1 file where `TFS` is the dominant marker**: 2012-2017 and 2021 use blank cells exclusively; 2011 and 2018-2020 mix blanks with a smaller `TFS` population (see the per-file table above). |
| PROGRAM_PERCENT | `TFS` — 30,026 rows in 2022; **zero `TFS` in every other Era 1 file** (2011-2021 suppress percent with blank cells; additionally, `TFS`-count rows in 2011/2018-2020 keep a published percent). |

### Era 2: 2022-23 through 2023-24 (files 2023–2024)

12 columns. Identical to Era 1 plus a leading `#RPT_NAME` column.

| Column | Description |
|--------|-------------|
| #RPT_NAME | Report label. Constant value `HS Completer Credentials`. Not useful for gold; drop. |
| LONG_SCHOOL_YEAR | School year label (e.g., `2023-24`). Same format as Era 1. |
| SCHOOL_DSTRCT_CD | District code (3- or 7-digit string) or `ALL`. Same semantics as Era 1. |
| SCHOOL_DSTRCT_NM | District name or `All Column Values`. Same as Era 1. |
| INSTN_NUMBER | School code (4-char zero-padded, e.g., `0100`) or `ALL`. Padding is consistent within this era. |
| INSTN_NAME | School name or `All Column Values`. Same as Era 1. |
| LABEL_SORT_ORDER | Integer 0–5; redundant with `LABEL_LVL_1_DESC`. |
| COMPLETER_TYPE | `Graduates` / `Other Completers`. Same as Era 1. |
| LABEL_LVL_1_DESC | Same 6 credential types as 2012+ Era 1 files. |
| LABEL_LVL_5_CD | Same 9 gender/race subgroups. |
| PROGRAM_TOTAL | Count; `TFS` when suppressed. Numeric minimum in 2024 is 10 (values < 10 appear suppressed). |
| PROGRAM_PERCENT | Percent (0–100); `TFS` when suppressed. |

#### Sample Data (2024)

```
shape: (5, 12)
#RPT_NAME                 LONG_SCHOOL_YEAR  SCHOOL_DSTRCT_CD  SCHOOL_DSTRCT_NM                                    INSTN_NUMBER  INSTN_NAME                LABEL_SORT_ORDER  COMPLETER_TYPE    LABEL_LVL_1_DESC                          LABEL_LVL_5_CD  PROGRAM_TOTAL  PROGRAM_PERCENT
HS Completer Credentials  2023-24           7830210           State Charter Schools II- Pataula Charter Academy   0210          Pataula Charter Academy   0                 Graduates         General Education Diplomas                Hispanic        TFS            2.6
HS Completer Credentials  2023-24           756               Wilcox County                                       ALL           All Column Values         1                 Graduates         Diplomas with Both College Prep. & Voc.   Hispanic        TFS            TFS
HS Completer Credentials  2023-24           7830210           State Charter Schools II- Pataula Charter Academy   0210          Pataula Charter Academy   3                 Graduates         Diplomas with Vocational Endorsements     Hispanic        TFS            TFS
HS Completer Credentials  2023-24           715               Polk County                                         ALL           All Column Values         5                 Other Completers  Certificates Of Attendance                Asian           TFS            TFS
HS Completer Credentials  2023-24           661               Gilmer County                                       0196          Gilmer High School        2                 Graduates         Diplomas with College Prep Endorsements   Male            TFS            TFS
```

#### Statistics (2024)

```
shape: (9, 13)
statistic   #RPT_NAME                 LONG_SCHOOL_YEAR  SCHOOL_DSTRCT_CD  SCHOOL_DSTRCT_NM   INSTN_NUMBER  INSTN_NAME                    LABEL_SORT_ORDER  COMPLETER_TYPE    LABEL_LVL_1_DESC            LABEL_LVL_5_CD  PROGRAM_TOTAL  PROGRAM_PERCENT
count       35694                     35694             35694             35694              35694         35694                         35694.0           35694             35694                       35694           35694          35694
null_count  0                         0                 0                 0                  0             0                             0.0               0                 0                           0               0              0
mean        null                      null              null              null               null          null                          2.5               null              null                        null            null           null
std         null                      null              null              null               null          null                          1.707849          null              null                        null            null           null
min         HS Completer Credentials  2023-24           601               All Column Values  0100          AZ Kelsey Academy             0.0               Graduates         Certificates Of Attendance  Asian           10             .1
max         HS Completer Credentials  2023-24           ALL               Worth County       ALL           iGrad Virtual Academy School  5.0               Other Completers  Special Education Diplomas  White           TFS            TFS
```

2023 row count: 35,478. 2024 row count: 35,694. Numeric range (2024): `PROGRAM_TOTAL` 10–119,764; `PROGRAM_PERCENT` 0.1–100.

#### Null Counts

```
shape: (1, 12)
#RPT_NAME  LONG_SCHOOL_YEAR  SCHOOL_DSTRCT_CD  SCHOOL_DSTRCT_NM  INSTN_NUMBER  INSTN_NAME  LABEL_SORT_ORDER  COMPLETER_TYPE  LABEL_LVL_1_DESC  LABEL_LVL_5_CD  PROGRAM_TOTAL  PROGRAM_PERCENT
0          0                 0                 0                 0             0           0                 0               0                 0               0              0
```

Zero explicit nulls in every column.

#### Categorical Columns (counts from 2024 representative file)

| Column | Distinct Values |
|--------|----------------|
| #RPT_NAME | `HS Completer Credentials` (35,694 — constant) |
| LONG_SCHOOL_YEAR | `2023-24` (single value per file) |
| COMPLETER_TYPE | `Graduates` (23,796), `Other Completers` (11,898) |
| LABEL_LVL_1_DESC | `Certificates Of Attendance` (5,949), `Diplomas with Both College Prep. & Voc.` (5,949), `Diplomas with College Prep Endorsements` (5,949), `Diplomas with Vocational Endorsements` (5,949), `General Education Diplomas` (5,949), `Special Education Diplomas` (5,949) |
| LABEL_LVL_5_CD | `Asian` (3,966), `Black` (3,966), `Female` (3,966), `Hispanic` (3,966), `Male` (3,966), `Multi` (3,966), `Native American/ Alaskan Native` (3,966), `Total` (3,966), `White` (3,966) |
| LABEL_SORT_ORDER | `0`–`5` (one-to-one with `LABEL_LVL_1_DESC`) |
| SCHOOL_DSTRCT_NM | 196 distinct district names plus `All Column Values` for state aggregate |
| INSTN_NAME | 466 distinct school names plus `All Column Values` for district/state aggregates |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| SCHOOL_DSTRCT_CD | `ALL` (aggregate marker, not suppression) — 54 rows in 2024 |
| INSTN_NUMBER | `ALL` (aggregate marker, not suppression) — 10,098 rows in 2024 |
| PROGRAM_TOTAL | `TFS` — 31,852 rows in 2024 |
| PROGRAM_PERCENT | `TFS` — 29,992 rows in 2024 |

## ETL Considerations

1. **Suppression has TWO representations, varying by year** *(amended 2026-06-11 — the original claim that `TFS` is the only suppression marker was true only of the 2022/2023/2024 files)*: blank (empty) cells and the literal `TFS`. `TFS` is the only non-numeric *string* in the metric columns, but blank cells are the dominant suppression form in 2011-2021. Per-file: 2012-2017 and 2021 use blanks exclusively (both metrics co-suppressed row-for-row); 2018-2020 use co-located blanks plus ~2.1-2.3k `TFS` counts whose percent IS published; 2011 has 9,073 fully-blank rows plus 10,339 `TFS` counts with a published percent; 2022-2024 use `TFS` only (2023-2024 keep ~1.9k published percents on `TFS`-count rows). All forms → NULL (blank via the CSV reader, `TFS` via the suppression null-list / `strict=False` casts). Invariant verified across all 14 files: a published `PROGRAM_TOTAL` always has a published `PROGRAM_PERCENT`; the reverse fails in 2011, 2018-2020, 2023-2024.
2. **`ALL` is an aggregate-row marker, NOT a suppression marker** in `SCHOOL_DSTRCT_CD` and `INSTN_NUMBER`. Detail-level semantics:
   - `SCHOOL_DSTRCT_CD='ALL'` and `INSTN_NUMBER='ALL'` → **state-level** row (54 rows per file)
   - `SCHOOL_DSTRCT_CD=<code>` and `INSTN_NUMBER='ALL'` → **district-level** row (≈10k rows per file)
   - `SCHOOL_DSTRCT_CD=<code>` and `INSTN_NUMBER=<code>` → **school-level** row (≈25k rows per file)
   The combination `SCHOOL_DSTRCT_CD='ALL'` with a non-`ALL` `INSTN_NUMBER` does not occur.
3. **`INSTN_NUMBER` zero-padding is inconsistent across years.** Files 2012–2017 and 2021–2024 use 4-char zero-padded strings (`0100`). Files 2011, 2018, 2019, 2020 mix 3-char unpadded codes (`100`, `506`) with 4-char padded codes (`2664`, `5055`). Transform must normalize to a single canonical form (recommend 4-character zero-padded string) before joining to the schools dimension, else joins will fragment.
4. **`SCHOOL_DSTRCT_CD` is a mix of 3-digit traditional district codes and 7-digit state-charter codes.** Both are valid; preserve as strings. Do not cast to integer.
5. **`#RPT_NAME` appears only in Era 2 (2023–2024)** with the single constant value `HS Completer Credentials`. Drop it in transform.
6. **`LABEL_SORT_ORDER` is redundant** with `LABEL_LVL_1_DESC` (one-to-one mapping, and the order differs between 2011 and 2012+). Drop it from gold.
7. **`LABEL_LVL_1_DESC` evolves across eras.** 2011 has 5 credential types (no `General Education Diplomas`). 2012 onward has 6 credential types. Expect missing `General Education Diplomas` rows for 2011 in the gold output.
8. **`LABEL_LVL_1_DESC` has punctuation quirks:** `Diplomas with Both College Prep. & Voc.` contains periods and an ampersand; `Certificates Of Attendance` uses title-case "Of". Normalize to canonical snake_case (e.g., `diplomas_college_prep_vocational`, `certificates_of_attendance`) for the fact_categorical column.
9. **`LABEL_LVL_5_CD` mixes gender and race/ethnicity** into a single demographic dimension, alongside the `Total` aggregate. Map values to the global demographics dimension: `Total`→`all`; `Female`/`Male`→gender values; race values (`Asian`, `Black`, `Hispanic`, `Multi`, `Native American/ Alaskan Native`, `White`) → race/ethnicity values. Note the irregular whitespace in `Native American/ Alaskan Native` (space after the slash) — preserve exactly when matching, or normalize. **The bare `Asian` label is the combined pre-1997 OMB Asian + Pacific Islander bucket** (data-cleaning-standards §5b): bronze has only 6 race buckets, never a separate Pacific Islander row, and the math test is exact — race-bucket counts sum EXACTLY to the `Total` count in every fully-published (geography × completer type × credential) group (6,369 such groups across all 14 files, 0 deviations; gender sums are likewise exact in all 11,214 complete groups). Map `Asian` → `asian_pacific_islander` via a topic-local remap before shared normalization.
10. **`COMPLETER_TYPE` is a fact_categorical** with two values: `Graduates` covers the four graduate credential types (General Ed, College Prep, Vocational, Both Prep & Voc); `Other Completers` covers `Special Education Diplomas` and `Certificates Of Attendance`. Each credential is tied to exactly one completer type; consider whether to keep both or drop `COMPLETER_TYPE` since it is functionally determined by `LABEL_LVL_1_DESC`.
11. **Percent is the demographic's share of the single credential's total** *(amended 2026-06-11 — the original claim that credentials sum to ~100% within a `COMPLETER_TYPE` is wrong)*. `PROGRAM_PERCENT` = row's `PROGRAM_TOTAL` ÷ the same credential's `LABEL_LVL_5_CD='Total'` `PROGRAM_TOTAL` at the same geography, ×100 — verified to match exactly (1-decimal rounding) on every checkable row in 2011/2022/2024. Disproof of the original claim: 2022 state `Other Completers` rows carry `PROGRAM_PERCENT=100` for BOTH credentials (Certificates Of Attendance = 18, Special Education Diplomas = 189); under the old reading they would be 8.7/91.3. Consequences: `Total` rows are always exactly 100 where published (0 violations in 14 files); Male+Female percents sum to ~100 within a credential (max rounding deviation 0.1); the six race-bucket percents sum to ~100 within a credential (max deviation 0.2). Document as a demographic-composition share — do NOT sum it across credentials.
12. **`LONG_SCHOOL_YEAR` format is stable** (`YYYY-YY`) across all files. Parse the leading 4-digit year + trailing 2-digit year to derive the gold `year` (recommend using the ending calendar year, e.g., `2023-24` → 2024, which matches the filename).
13. **District name `DeKalb County`** uses mixed case (capital K) — preserve as-is; dimension join should be by district_code anyway.
14. **File publication year = ending calendar year of the school year** (`high_school_completers_2024.csv` → `2023-24`). Partition gold by ending calendar year for consistency with filename.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| LONG_SCHOOL_YEAR | fact_key | year | Parse to integer (ending calendar year, e.g., `2023-24` → 2024); used as partition key |
| SCHOOL_DSTRCT_CD | fact_key | district_code | Preserve as string (3- or 7-digit); `ALL` rows represent state-level aggregates (handle via detail-level column, not stored as a district_code value) |
| SCHOOL_DSTRCT_NM | dimension_attribute | — | `district_name` in the districts dimension, not in the fact table |
| INSTN_NUMBER | fact_key | school_code | Zero-pad to 4 characters; `ALL` rows represent district-level aggregates (handle via detail-level column, not stored as a school_code value) |
| INSTN_NAME | dimension_attribute | — | `school_name` in the schools dimension |
| LABEL_SORT_ORDER | not_in_gold | — | Redundant with `LABEL_LVL_1_DESC` |
| COMPLETER_TYPE | fact_categorical | completer_type | Normalize to snake_case (`graduates`, `other_completers`); functionally determined by credential type so may be dropped if `LABEL_LVL_1_DESC` is kept |
| LABEL_LVL_1_DESC | fact_categorical | credential_type | 6 credential categories (5 in 2011); normalize to snake_case |
| LABEL_LVL_5_CD | fact_key | demographic | FK to global demographics dimension; map `Total`→`all`; bare `Asian`→`asian_pacific_islander` (combined bucket, see ETL note 9); map gender and remaining race values to dimension; normalize whitespace in `Native American/ Alaskan Native` |
| PROGRAM_TOTAL | fact_metric | completer_count | Integer count; blank/`TFS`→null via reader null-list + `strict=False` cast |
| PROGRAM_PERCENT | fact_metric | pct_of_credential_type | 0–100 scale ÷100 → 0–1; the demographic's share of the credential's total (see ETL note 11, amended); blank/`TFS`→null |
| #RPT_NAME | not_in_gold | — | Constant label, Era 2 (2023–2024) only |
