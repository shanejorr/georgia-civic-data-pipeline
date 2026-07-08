# enrollment_october_disability - Bronze Data Structure

## Overview

- Topic: enrollment_october_disability
- Source: georgiainsights
- Files: 13 files spanning fiscal years 2014-2026 (one .csv per FTE October count)
- Unreadable files: none
- Year representation: encoded only in the filename pattern `FTE Enrollment by Grade Disability Fiscal Year{YYYY}-1 District.csv` and in the report subject line on row 2 (e.g., "FTE Enrollment by Disability - Fiscal Year 2026-1 Data Report"). There is **no year column inside the data**. The collection date on row 3 (e.g., "October 7, 2025 (FTE 2026-1)") confirms the FTE-1 cycle is the October count for the school year ending in the FTE year.
- Filename-to-data year offset: same — Fiscal Year `YYYY` in the filename is the school year ending in calendar year `YYYY` (e.g., `Year2026-1` = school year 2025-2026, October 2025 count). Use the FTE year directly as the gold `year`.
- Detail levels: **district only** — every file contains district-level rows (3-digit standard district codes plus 7-digit charter / state-specialty-school codes). There are no state-aggregate rows and no per-school rows.
- Percentage scale: not applicable — every metric in this dataset is an FTE student count (integer), not a rate.
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: Georgia Insights (GaDOE) public data downloads — exact page URL not recorded at acquisition time
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| FTE Enrollment by Grade Disability Fiscal Year2014-1 District.csv | 8d042777afb523d2a9b8f1c4e73bee53fe4851114212c113896762b71391ff08 |
| FTE Enrollment by Grade Disability Fiscal Year2015-1 District.csv | def879bcfa630c591cbbabc55fbda53eb9015815dc662220656fb64fb3419db1 |
| FTE Enrollment by Grade Disability Fiscal Year2016-1 District.csv | 7c4f2f0c4a722aafb196a53a5c919d27f66af83901154c6e89cf143f9e9f3ec7 |
| FTE Enrollment by Grade Disability Fiscal Year2017-1 District.csv | d1b3fa3f89d5d1167ddca176e7e9a55751c5f5704161b7c92089824feb4c4f1a |
| FTE Enrollment by Grade Disability Fiscal Year2018-1 District.csv | 36adb8f8b2d9c7f1129c54cb4627046138f96a278b162b690e0f5cf1341074f0 |
| FTE Enrollment by Grade Disability Fiscal Year2019-1 District.csv | a3d86f54aaf80942c8335cda826d2d2eb1811ce81571e817762a4b76802cf106 |
| FTE Enrollment by Grade Disability Fiscal Year2020-1 District.csv | abbf65cd17db824ea11d6d516fef40c6b3acd2c93730b4d0de48a33da9d8c352 |
| FTE Enrollment by Grade Disability Fiscal Year2021-1 District.csv | ea139434f8806fdce8f518d06366d3ee852c912110725296b56ce7df4373187f |
| FTE Enrollment by Grade Disability Fiscal Year2022-1 District.csv | 69bd2b90e68c5610b7dde964b02a0cf64df714a7a7a130113edf49852647e49e |
| FTE Enrollment by Grade Disability Fiscal Year2023-1 District.csv | 6a79e7cffeae6f107a57582b69fa0c91d26ce24d650d48046394a94283d21f8c |
| FTE Enrollment by Grade Disability Fiscal Year2024-1 District.csv | b4983155f8deed8608da888f9d1ce9daaa7e710340814298d5802c8fbdba2d80 |
| FTE Enrollment by Grade Disability Fiscal Year2025-1 District.csv | 1f224db289564ff6d0ca742a005338a948c1adeba344b5ee171877b26b758eb3 |
| FTE Enrollment by Grade Disability Fiscal Year2026-1 District.csv | 4f16d3fc0e6ac125ac0d5f639e7c4ad52e0b27e969408ca38a403c0603f60ae5 |

## Summary

GaDOE October FTE-1 enrollment counts of students receiving special-education services, broken out by IDEA/Georgia disability category at the school-district level. Each row reports, for one district, the count of FTE students in each of 17 disability categories (e.g., Autism, Specific Learning Disability, Speech-Language Impairment). The metrics are head-counts, suppressed with `*` whenever the count would otherwise be below 10. Despite the filename including "by Grade Disability", there is no per-grade breakdown in the file — only by district and by disability category.

The 17 disability categories are GaDOE/IDEA standard codes:

| Code | Disability Category |
|------|---------------------|
| AUT | Autism |
| BL | Blind / Low Vision |
| D | Deaf |
| DB | Deaf-Blind |
| EBD | Emotional and Behavioral Disorder |
| HH | Hospital / Homebound |
| MID | Mild Intellectual Disability |
| MoID | Moderate Intellectual Disability |
| OHI | Other Health Impairment |
| OI | Orthopedic Impairment |
| PID | Profound Intellectual Disability |
| SDD | Significant Developmental Delay |
| SI | Speech-Language Impairment |
| SID | Severe Intellectual Disability |
| SLD | Specific Learning Disability |
| TBI | Traumatic Brain Injury |
| VI | Visual Impairment |

## Eras

### Era 1: 2014-2026 (single era — no schema changes)

All 13 files share byte-identical column headers (verified on row 5 of each CSV). The 17 disability columns and their order are unchanged across the entire 2014-2026 span.

| Column | Description |
|--------|-------------|
| `System ID` | Int64. GOSA district code. 3 digits for standard public-school districts (e.g., `601` = Appling County) and 7 digits for state charters / state specialty schools (e.g., `7820212`, `7830634`). Stored unpadded by the source — must be cast to Utf8 and zero-padded for downstream joins. |
| `System Name` (raw header is ` System Name` with a leading space) | String. District name in title case (e.g., "Appling County", "Atlanta Public Schools"). Three IDs (7991893, 7991894, 7991895) appear in 2014-2019 with **blank** names — they are state-specialty / charter entities the source did not label. They drop out of the data starting in 2020. |
| `AUT`, `BL`, `D`, `DB`, `EBD`, `HH`, `MID`, `MoID`, `OHI`, `OI`, `PID`, `SDD`, `SI`, `SID`, `SLD`, `TBI`, `VI` (each header has 1-2 leading spaces and `VI` has a trailing space) | String stored as digits or `*`. FTE student count for that district in that disability category. `*` is the small-cell suppression marker (used whenever the true count is below 10 — verified: minimum non-suppressed value is 10 in every column in every year). Cast to `pl.Int64` with `strict=False` (or first replace `"*"` with null) to coerce the suppression marker to null. |

#### Sample Data (2026-1 file, 5 random rows)

```text
System ID  System Name                                                    AUT  BL  D  DB  EBD  HH  MID  MoID  OHI  OI  PID  SDD  SI  SID  SLD  TBI  VI
7830649    State Specialty Schools II- Rocky Creek Charter Academy       *    *   *  *   *    *   *    *     *    *   *    *    *   *    *    *    *
662        Glascock County                                                *    *   *  *   *    *   *    *     25   *   *    12   13  *    21   *    *
754        White County                                                   81   *   *  *   32   *   11   *     121  *   *    114  64  *    211  *    *
7830630    State Specialty Schools II- Baconton Community Charter School  17   *   *  *   *    *   *    *     20   *   *    *    *   11   48   *    *
7830641    State Specialty Schools II- Resurgence Hall Middle Academy     *    *   *  *   *    *   *    *     *    *   *    *    *   *    *    12   *
```

#### Sample Data (2014-1 file, last 5 rows — illustrates the blank-name state-school IDs)

```text
System ID  System Name        AUT  BL  D    DB  EBD  HH  MID  MoID  OHI  OI  PID  SDD  SI  SID  SLD  TBI  VI
758        Wilkinson County   *    *   *    *   20   *   36   *     18   *   *    12   21  *    39   *    *
759        Worth County       10   *   *    *   30   *   26   13    21   *   *    35   61  *    34   *    *
7991893    (blank)            *    *   155  *   *    *   13   *     *    *   *    *    *   *    *    *    *
7991895    (blank)            *    *   88   *   *    *   *    *     *    *   *    *    *   *    *    *    *
7991894    (blank)            *    *   *    *   *    *   13   11    *    *   *    *    12  *    *    *    55
```

#### Statistics — disability counts in the most recent (2026-1) file

| Column | Total rows | Suppressed (`*`) | Suppressed % | Min non-suppressed | Max non-suppressed | Sum of non-suppressed |
|--------|-----------:|-----------------:|-------------:|-------------------:|-------------------:|----------------------:|
| AUT  | 237 | 51  | 21.5%  | 10 | 5,384  | 39,917 |
| BL   | 237 | 234 | 98.7%  | 12 | 21     | 49     |
| D    | 237 | 228 | 96.2%  | 10 | 58     | 229    |
| DB   | 237 | 237 | 100.0% | -  | -      | 0      |
| EBD  | 237 | 116 | 48.9%  | 10 | 607    | 7,156  |
| HH   | 237 | 199 | 84.0%  | 10 | 119    | 1,003  |
| MID  | 237 | 84  | 35.4%  | 10 | 614    | 9,478  |
| MoID | 237 | 133 | 56.1%  | 10 | 405    | 4,423  |
| OHI  | 237 | 43  | 18.1%  | 10 | 2,287  | 36,778 |
| OI   | 237 | 221 | 93.2%  | 10 | 79     | 387    |
| PID  | 237 | 232 | 97.9%  | 10 | 36     | 108    |
| SDD  | 237 | 57  | 24.1%  | 10 | 3,725  | 30,909 |
| SI   | 237 | 50  | 21.1%  | 10 | 2,667  | 28,998 |
| SID  | 237 | 212 | 89.5%  | 10 | 182    | 788    |
| SLD  | 237 | 24  | 10.1%  | 10 | 10,040 | 80,154 |
| TBI  | 237 | 227 | 95.8%  | 10 | 33     | 162    |
| VI   | 237 | 219 | 92.4%  | 10 | 47     | 319    |

The minimum non-suppressed value is exactly `10` in every numeric column in every year, confirming the GaDOE small-cell rule (counts <10 → `*`).

#### Row Counts Per File

| Fiscal Year | Rows | Of which 3-digit `System ID` (standard districts) | Of which 7-digit `System ID` (charter / specialty) |
|------------:|-----:|--------------------------------------------------:|---------------------------------------------------:|
| 2014 | 201 | 183 | 18 |
| 2015 | 201 | 183 | 18 |
| 2016 | 206 | 183 | 23 |
| 2017 | 209 | 183 | 26 |
| 2018 | 213 | 181 | 32 |
| 2019 | 213 | 182 | 31 |
| 2020 | 216 | 183 | 33 |
| 2021 | 222 | 183 | 39 |
| 2022 | 223 | 183 | 40 |
| 2023 | 227 | 183 | 44 |
| 2024 | 235 | 183 | 52 |
| 2025 | 235 | 183 | 52 |
| 2026 | 237 | 183 | 54 |

The standard-district population is essentially constant (181-183 districts); charter / state specialty schools roughly triple over the period as more open.

#### Null Counts (2026-1 file)

Zero `null` values in any column in any year. All "missingness" is encoded as the literal `*` suppression marker, not as null. (In the 2014-2019 files, the `System Name` field for IDs 7991893/4/5 is the empty string `""`, not null — but it still parses as a non-null string.)

#### Categorical Columns

Only `System Name` is truly categorical, holding district / specialty-school names. For every fiscal year it has a 1-to-1 correspondence with `System ID` (with the 7991893/4/5 exception in 2014-2019 mentioned above). It does **not** need to be transformed into a fact-table column — names belong in the `districts.parquet` dimension. There are no other categorical columns: every disability column is a numeric count with `*` as the suppression marker.

#### Suppression Markers

| Column | Marker(s) | Meaning |
|--------|-----------|---------|
| `AUT`, `BL`, `D`, `DB`, `EBD`, `HH`, `MID`, `MoID`, `OHI`, `OI`, `PID`, `SDD`, `SI`, `SID`, `SLD`, `TBI`, `VI` | `*` (the only non-numeric value found in any disability column in any year) | True FTE count is non-zero but below 10 (GaDOE small-cell rule). |

Confirmed by exhaustive scan of all 13 files: `*` is the only suppression marker, and the minimum non-suppressed value is always 10.

## ETL Considerations

### Year is filename-only

There is no `year` column inside the CSVs. The transform must extract the FTE year from the filename via a regex such as `r"Year(\d{4})-1"`. The collection-date line on row 3 (e.g., `October 7, 2025 (FTE 2026-1)`) is consistent with the filename year and confirms FTE-1 = October count for the school year ending in the FTE year — use the FTE year directly as gold `year` (Int32).

### CSV header lives on row 5

Each file has 4 header / metadata rows before the column header:

1. `Georgia Department of Education`
2. `FTE Enrollment by Disability - Fiscal Year YYYY-1 Data Report`
3. `"October DD, YYYY (FTE YYYY-1)"`
4. (single blank row containing one space)
5. `System ID, System Name, AUT,  BL, ...` ← actual column header

Read with `pl.read_csv(path, skip_rows=4)`. Polars will pick up the header on the next non-skipped line. Without `truncate_ragged_lines=True` the read still works (every data row has 19 fields), but use it defensively.

### Column-header whitespace

The raw column headers contain leading and trailing spaces (`' System Name'`, `'  BL'`, `'  VI '`, etc.). Strip whitespace from every column name immediately after read:

```python
df = df.rename({c: c.strip() for c in df.columns})
```

Otherwise downstream selectors and renames will silently miss these columns.

### `*` suppression marker

Replace `"*"` with null before casting to `Int64`, **or** rely on `cast(pl.Int64, strict=False)` which converts the asterisk to null automatically. Either approach is safe. Suppression is per-cell — a single row can have any combination of the 17 disability columns suppressed and the others numeric.

### `System ID` arrives as Int64 — must be padded to a string

Polars infers `System ID` as `Int64` because every value is digits. Cast to `Utf8` then `str.zfill(3)`:

```python
pl.col("System ID").cast(pl.Utf8).str.zfill(3)
```

`zfill(3)` correctly pads 3-digit standard codes while leaving 7-digit charter / state-specialty codes unchanged. **Never** truncate with `.str.slice(0, 3)`.

### Blank `System Name` for IDs 7991893 / 7991894 / 7991895 (2014-2019 only)

These three 7-digit System IDs appear in 2014-2019 with empty-string names, then disappear from the data in 2020-2026. They are real records (each has non-suppressed counts in 1-3 disability columns), but the source omitted their human-readable names. The transform should:

- keep the records (do not drop based on blank name),
- emit them with `district_code` = `"7991893"` etc.,
- expect `districts.parquet` to either resolve or omit these legacy IDs (current `build_dimensions.py` keeps the latest name per code, so these may surface as nameless dimension rows unless explicitly mapped).

Flag during dimension build whether to add manual name overrides for these three IDs.

### No state-aggregate rows

There is no row representing the Georgia state total in any year. The transform must **not** attempt to produce a `states.parquet` per-year file for this topic — only `districts.parquet` will be populated. This is in contrast to most other education topics (e.g., `attendance_dashboard`, CCRPI), which include state rows.

### No school-level data

GaDOE only publishes this disability breakdown at the district / system level. There is no companion `... School.csv` file (compare with sibling topics `enrollment_october_grade` and `enrollment_october_gender_race_ethnicity`, which do publish both District and School files). The transform must **not** produce a `schools.parquet` for this topic.

### Tidy-format reshape required

Bronze is in **wide format** with one column per disability category. Gold should be tidy: one row per `(year, district_code, disability_category)` with a single `student_count` metric. Use `pl.DataFrame.unpivot` (formerly `melt`):

```python
df_long = df.unpivot(
    index=["year", "district_code"],
    on=["AUT", "BL", "D", "DB", "EBD", "HH", "MID", "MoID",
        "OHI", "OI", "PID", "SDD", "SI", "SID", "SLD", "TBI", "VI"],
    variable_name="disability_category",
    value_name="student_count",
)
```

This makes the disability category a `fact_categorical` column rather than producing 17 metric columns in the fact table.

### Disability category is a fact-categorical, not a demographic

The 17 IDEA category codes (AUT, EBD, SLD, etc.) are **not** in the global `data/gold/_dimensions/demographics.parquet`. They are a topic-specific dimension of disability *type*, not a demographic breakdown of the population. Every row in this fact already implicitly answers "students with disabilities" — the categorical splits that population by category. Treat as a `fact_categorical` column (`disability_category`) following the snake_case convention, e.g.:

| Bronze code | Gold `disability_category` |
|-------------|----------------------------|
| AUT  | autism |
| BL   | blind_low_vision |
| D    | deaf |
| DB   | deaf_blind |
| EBD  | emotional_behavioral_disorder |
| HH   | hospital_homebound |
| MID  | mild_intellectual_disability |
| MoID | moderate_intellectual_disability |
| OHI  | other_health_impairment |
| OI   | orthopedic_impairment |
| PID  | profound_intellectual_disability |
| SDD  | significant_developmental_delay |
| SI   | speech_language_impairment |
| SID  | severe_intellectual_disability |
| SLD  | specific_learning_disability |
| TBI  | traumatic_brain_injury |
| VI   | visual_impairment |

This is the inverse of the demographics pattern used by other education topics — there is no `demographic` column at all in this fact table because the population is fixed (students receiving special-education services).

### Coverage / missing years

All 13 fiscal years 2014-2026 are present, no gaps. Row counts grow monotonically as new charter / specialty schools open over the period.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| (filename `Year{YYYY}-1`) | fact_key | `year` | `pl.Int32`. Extracted from filename; same as the FTE fiscal year. |
| `System ID` | fact_key | `district_code` | Cast `pl.Int64` -> `pl.Utf8` -> `str.zfill(3)`. Preserves both 3-digit standard codes and 7-digit charter / specialty codes. |
| `System Name` | dimension_attribute | — | Goes to `data/gold/education/_dimensions/districts.parquet` (latest name per district). Drop from fact. Preserve as-is (already title case); blank-string entries for IDs 7991893/4/5 in 2014-2019 may need manual override. |
| `AUT` ... `VI` (17 disability columns) | fact_categorical (after unpivot) | `disability_category` | `pl.Utf8`. After `unpivot`, the column header (AUT, BL, ...) becomes the value of `disability_category`; map each code to its snake_case label per the table above. |
| `AUT` ... `VI` (17 disability columns) | fact_metric (after unpivot) | `student_count` | `pl.Int64`. The non-suppressed cell value becomes the metric; `*` -> null via `cast(pl.Int64, strict=False)`. Counts <10 are suppressed and remain null in gold. |

Final fact table grain: one row per `(year, district_code, disability_category)`. Output partitioning per the education domain convention: `data/gold/education/enrollment_october_disability/year=YYYY/districts.parquet`. **Do not emit** `states.parquet` or `schools.parquet` — neither detail level exists in this bronze.

## Corrections

Amendments from transform authoring (2026-06-12), each re-measured against all 13 bronze CSVs:

- **"Minimum non-suppressed value is 10 in every column in every year" (Era 1 column table and the sentence below the 2026 statistics table) is overstated.** The verified invariants are: (a) every non-suppressed value is `>= 10`, and (b) each file's **overall** minimum is exactly 10. Per-**column** minimums range 10-15 (e.g., `BL` 2026 min = 12 — consistent with this doc's own 2026 statistics table — `TBI` 2014 min = 15, `BL` 2017 min = 15), so "exactly 10 in every column" does not hold column-by-column.
- **`DB` (Deaf-Blind) has zero non-suppressed values in every year, not just 2026.** The 2026 statistics table shows `DB` 100%% suppressed; re-measurement confirms this holds for all 13 files (2014-2026): no Georgia district ever publishes a `DB` count. Gold therefore carries `deaf_blind` rows with `student_count` always NULL.

All other claims re-verified as written: per-file row counts and 3-digit/7-digit splits match exactly; the post-strip header set is byte-identical across all 13 files; `*` is the only non-numeric cell value (no empty or whitespace-padded cells); no duplicate `System ID` within any file; no blank/state-sentinel IDs; blank `System Name` only for 7991893/7991894/7991895 in 2014-2019; preamble year always equals filename year; raw data-line counts equal parsed row counts (no read loss).
