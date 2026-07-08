# english_learners_el_exit_rate — Bronze Data Structure

## Overview

- Topic: english_learners_el_exit_rate
- Source: gosa
- Files: 12 files spanning FY2019–FY2024 — one district-level CSV and one
  state-level CSV per fiscal year (filenames prefixed `district_` and `state_`
  to make the source detail level traceable after the merge of the legacy
  `_district_level` and `_state_level` topics).
- Unreadable files: none
- Year representation: present in both the filename (`{detail_level}_FY{YYYY}.csv`)
  and a `FISCAL_YEAR` column (4-digit ending year, e.g. `2024`). One year per
  file.
- Filename-to-data year offset: same — filename year always equals the
  `FISCAL_YEAR` value. GOSA fiscal year equals the ending calendar year of
  the school year (FY2024 = school year 2023-24).
- Detail levels: `district` (regular districts, charter LEAs, and the
  `State Schools` aggregate LEA) and `state` (one statewide aggregate row
  per FY). No school-level detail.
- Percentage scale: 0–100 (for `EL_EXIT_RATE` and `STATE_EL_EXIT_RATE`).
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| district_FY2019.csv | 51a975e40649f8c2bb4114cf51f4b32cd0f24dd875fe6388b83981bc318eba28 |
| district_FY2020.csv | ccd7219a23de7b5343718d9ef10c536c4c4d423a6802d5c74b3cf47a3b9f2060 |
| district_FY2021.csv | 5250ade7f6203f63a719bfa9978f23f59689a720a0e7c02119eb9d6a126067ac |
| district_FY2022.csv | 068c02cb2e528f0304b4864e8b561cf44986f441b51e5820ca2d7e04e7ff1711 |
| district_FY2023.csv | da44f080f2187928bfa0168da0a23054d3919a9aa4ac364ae5420834b164e861 |
| district_FY2024.csv | 3b71e93a631aa9804883623c573d4c9c94349860a0322928082428ff9b341d72 |
| state_FY2019.csv | 7e17d774d17bfaef358172203091deb74f7cacba8994af063cab45bd4dffe843 |
| state_FY2020.csv | 0ee75cecab875cbbcabb5604fa085506907fbd517b052602b1230e0534032ec5 |
| state_FY2021.csv | 3e7981d42733e7d8efc69a12af898e2ba11ba35f4bf48dafccc684688c180f02 |
| state_FY2022.csv | d11096890f936a7cc3316277e247e49c170e67191f0ed0d3b5b42b6430a86238 |
| state_FY2023.csv | df9fbb527d14328fac2f2df442d3e96e5a0975eef19db669a80619abdd6f4237 |
| state_FY2024.csv | 3be843c5989c1dd7f09a5f98fe317fa210ca555c8f6fbac6e8e5dd816f5f272a |

## Provenance

This bronze directory is the merged product of two legacy GOSA topics that
were consolidated into one to reduce cross-topic union queries at the API
layer. A third legacy topic, `english_learners_el_exit_rate_3yr_for_report_card`,
covered FY2021–FY2024 only and republished the same metric values for the
same `(year, district_code)` cells. A row-by-row diff against the
`_district_level` and `_state_level` gold parquet for FY2021–FY2024
returned **zero mismatches**, so the report-card bronze was dropped during
the merge — the `_district_level` + `_state_level` files cover the full
FY2019–FY2024 range and contain the same metric values.

| Source CSV (legacy) | Renamed in this bronze | FY |
|---|---|---|
| `english_learners_el_exit_rate_district_level_2019.csv` | `district_FY2019.csv` | 2019 |
| `english_learners_el_exit_rate_district_level_2020.csv` | `district_FY2020.csv` | 2020 |
| `english_learners_el_exit_rate_district_level_2021.csv` | `district_FY2021.csv` | 2021 |
| `english_learners_el_exit_rate_district_level_2022.csv` | `district_FY2022.csv` | 2022 |
| `english_learners_el_exit_rate_district_level_2023.csv` | `district_FY2023.csv` | 2023 |
| `english_learners_el_exit_rate_district_level_2024.csv` | `district_FY2024.csv` | 2024 |
| `english_learners_el_exit_rate_state_level_2019.csv` | `state_FY2019.csv` | 2019 |
| `english_learners_el_exit_rate_state_level_2020.csv` | `state_FY2020.csv` | 2020 |
| `english_learners_el_exit_rate_state_level_2021.csv` | `state_FY2021.csv` | 2021 |
| `english_learners_el_exit_rate_state_level_2022.csv` | `state_FY2022.csv` | 2022 |
| `english_learners_el_exit_rate_state_level_2023.csv` | `state_FY2023.csv` | 2023 |
| `english_learners_el_exit_rate_state_level_2024.csv` | `state_FY2024.csv` | 2024 |

## Summary

This dataset reports each Georgia LEA's annual English Learner (EL) program
exit activity, plus a single statewide aggregate per fiscal year. For every
LEA and the statewide row, three metrics are reported per fiscal year:

- `el_exit_count` — number of EL students who exited the EL program.
- `el_student_count` — total EL student enrollment for the fiscal year.
- `el_exit_rate` — exit rate as a proportion (gold 0–1 scale; bronze 0–100).

There is no demographic breakdown, no grade breakdown, and no school-level
detail. Suppressed cells use the literal string `TFS` ("too few students")
in the district-level files (district aggregates can be small). State-level
files are never suppressed (statewide totals are always >100k students).

## Eras

Two distinct file groups (`district_*` and `state_*`) carry their own
schema histories. The transform routes each file by its filename prefix to
the appropriate handler and then applies era-detection within each group.

### District files (district_FY2019 – district_FY2024)

#### District Era 1: 2019, 2020, 2021, 2022, 2024 (no `#RPT_NAME` header)

5 files share an identical 6-column header. 2023 is the lone exception
(District Era 2) — 2024 reverted to District Era 1, so the column drift is a
single-year anomaly bracketed by Era 1 on both sides.

| Column | Description |
|--------|-------------|
| FISCAL_YEAR | GOSA fiscal year as a 4-digit integer. One value per file. |
| SYSTEM_ID | GOSA district / LEA code (3-digit standard or 7-digit charter). |
| SYSTEM_NAME | District / LEA name (e.g. `Appling County`, `State Schools`). |
| EL_EXIT_COUNT | Number of EL students who exited services. Integer ≥10 or `TFS`. |
| EL_STUDENT_COUNT | Total EL student count for the LEA. Integer ≥10 or `TFS`. |
| EL_EXIT_RATE | Exit rate, 0–100 percent. `TFS` in 2019–2022. **2024 quirk**: numeric for every row, including suppressed-count rows (see ETL Considerations). |

#### District Era 2: 2023 only (with `#RPT_NAME` header)

The 2023 file added a leading `#RPT_NAME` column whose only value is
`EL_EXIT_RATES_DISTRICT_LEVEL`. All other columns are identical to District
Era 1.

| Column | Description |
|--------|-------------|
| #RPT_NAME | Report name; constant `EL_EXIT_RATES_DISTRICT_LEVEL`. Drop during transform. |
| FISCAL_YEAR | 2023 only. |
| SYSTEM_ID | Same as District Era 1. |
| SYSTEM_NAME | Same as District Era 1. **One row has `null` for `SYSTEM_NAME`** (SYSTEM_ID `890`) — all metrics for this row are `TFS`. |
| EL_EXIT_COUNT | Same as District Era 1, with `TFS` suppression. |
| EL_STUDENT_COUNT | Same as District Era 1, with `TFS` suppression. |
| EL_EXIT_RATE | Same as District Era 1; uses `TFS` for every suppressed row (the 2024 quirk does NOT apply in 2023). |

#### District-file row counts

| Year | Era | Rows | EL_EXIT_COUNT non-null n | EL_STUDENT_COUNT non-null n | EL_EXIT_RATE non-null n | Notes |
|------|-----|------|--------------------------|-----------------------------|-------------------------|-------|
| 2019 | Era 1 | 213 | 92  | 166 | 92  | Three individual `State Schools-…` rows (`7991893` Atlanta Area School for the Deaf, `7991894` Georgia Academy for the Blind, `7991895` Georgia School for the Deaf — all metrics `TFS`); no `799` aggregate. |
| 2020 | Era 1 | 210 | 88  | 167 | 88  | No State Schools rows at all — neither individual `State Schools-…` rows nor a `799` aggregate (verified: zero rows matching `(?i)state school` or a 799-prefix code). |
| 2021 | Era 1 | 222 | 84  | 174 | 84  | First year `State Schools` (SYSTEM_ID 799) appears as a single aggregate row. |
| 2022 | Era 1 | 223 | 96  | 175 | 96  | |
| 2023 | Era 2 | 227 | 105 | 179 | 105 | One null `SYSTEM_NAME` for SYSTEM_ID `890` (all metrics suppressed). |
| 2024 | Era 1 | 235 | 105 | 178 | **235** | EL_EXIT_RATE quirk — see ETL Considerations. |

#### District-file suppression

The only suppression marker across all district files is the literal string
`TFS`. All bronze cells with no published value contain this marker, never
empty / null (except the one 2023 SYSTEM_NAME case noted above).

| Column | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|--------|------|------|------|------|------|------|
| EL_EXIT_COUNT  | 121 | 122 | 138 | 127 | 122 | 130 |
| EL_STUDENT_COUNT | 47 | 43 | 48 | 48 | 48 | 57 |
| EL_EXIT_RATE  | 121 | 122 | 138 | 127 | 122 | **0** (Float64; numeric values published for every row) |

### State files (state_FY2019 – state_FY2024)

Each state file contains exactly **one row** — the statewide aggregate for
that fiscal year. Three schema eras detected by column signature:

#### State Era 1: 2019, 2020, 2021 (`STATE_`-prefixed metric columns)

| Column | Description |
|--------|-------------|
| FISCAL_YEAR | 4-digit fiscal year. |
| STATE_EL_EXIT_COUNT | Statewide count of EL students who exited services. |
| STATE_EL_STUDENT_COUNT | Statewide total EL student population. |
| STATE_EL_EXIT_RATE | Statewide exit rate, 0–100 percent. |

#### State Era 2: 2022, 2024 (no prefix)

The `STATE_` prefix is dropped — otherwise identical to State Era 1. Note:
State Era 2 is non-contiguous (2023 sits between the two State Era 2 files
and uses State Era 3).

| Column | Description |
|--------|-------------|
| FISCAL_YEAR | 4-digit fiscal year. |
| EL_EXIT_COUNT | Same as State Era 1's `STATE_EL_EXIT_COUNT`. |
| EL_STUDENT_COUNT | Same as State Era 1's `STATE_EL_STUDENT_COUNT`. |
| EL_EXIT_RATE | Same as State Era 1's `STATE_EL_EXIT_RATE`. |

#### State Era 3: 2023 (extra constant descriptor columns)

Same metric columns as State Era 2, plus three constant identifier columns
that all carry `"State of Georgia"` or the report-name string. The header
also begins with a literal `#` on `#RPT_NAME` (Polars reads it as a regular
column name).

| Column | Description |
|--------|-------------|
| #RPT_NAME | Constant `EL_EXIT_RATES_STATE_LEVEL`. Drop during transform. |
| FISCAL_YEAR | 2023 only. |
| SYSTEM_ID | Constant `State of Georgia`. Drop. |
| SYSTEM_NAME | Constant `State of Georgia`. Drop. |
| EL_EXIT_COUNT | Same as State Era 2. |
| EL_STUDENT_COUNT | Same as State Era 2. |
| EL_EXIT_RATE | Same as State Era 2. |

#### State-file values (one row per file)

| Year | EL_EXIT_COUNT | EL_STUDENT_COUNT | EL_EXIT_RATE |
|------|---------------|------------------|--------------|
| 2019 | 12,125 | 121,921 | 9.94 |
| 2020 | 11,841 | 127,512 | 9.29 |
| 2021 | 9,627  | 124,925 | 7.71 |
| 2022 | 14,348 | 136,295 | 10.53 |
| 2023 | 14,215 | 143,070 | 9.94 |
| 2024 | 15,519 | 155,372 | 9.99 |

#### State-file suppression

No suppression markers appear in any state file. State totals are large
enough (>100k students) that no privacy threshold is triggered. All four
columns in all six files load as pure numeric types (or as Utf8 with no
`TFS` markers when read with `infer_schema_length=0`).

## ETL Considerations

- **Two file groups, six era combinations.** The transform routes each
  file by the filename prefix (`district_` or `state_`) to a group-specific
  handler, then within each group detects the era by column presence
  (resilient to a future republication that reintroduces `#RPT_NAME` for a
  different year).
- **Single suppression marker (`TFS`) — but inconsistent application.**
  All three district metric columns use the literal `TFS`. The transform
  must convert `TFS` → null before casting (handled by
  `read_bronze_file`'s built-in SUPPRESSION_VALUES). 2019–2023 district
  files use `TFS` for every metric column when a row is suppressed.
  **2024 is the exception**: `EL_EXIT_COUNT` and `EL_STUDENT_COUNT` use
  `TFS` (130 and 57 rows respectively), but `EL_EXIT_RATE` was published
  as a numeric value for every row. Across the 130 exit-suppressed rows
  the published rates span 0–100 (65 read `0`); 57 of the 130 also have
  `EL_STUDENT_COUNT` = `TFS` (46 of those read `0`; Ivy Preparatory
  Academy, SYSTEM_ID `7820612`, reads `100`). These rates are not derivable from
  suppressed counts and should be treated as suppressed too — null
  `el_exit_rate` whenever either `el_exit_count` or `el_student_count`
  is suppressed (which nulls 130 of 235 rows in 2024).
- **`#RPT_NAME` is constant and informational only.** Drop it whenever
  it appears (district 2023, state 2023).
- **Era 3 state-row constants.** In the 2023 state file, `SYSTEM_ID` and
  `SYSTEM_NAME` both equal `"State of Georgia"`. These are encoded in
  gold via `detail_level = "state"` and NULL geography keys; drop both
  bronze columns.
- **State-name-prefix column rename.** State Era 1 uses `STATE_EL_EXIT_COUNT`,
  `STATE_EL_STUDENT_COUNT`, `STATE_EL_EXIT_RATE`. The transform renames
  them to the canonical `EL_EXIT_COUNT` / `EL_STUDENT_COUNT` /
  `EL_EXIT_RATE` (which then become `el_exit_count` / `el_student_count`
  / `el_exit_rate` in gold).
- **Numeric columns are stored as quoted strings (district files).** All
  three district metric columns need explicit casts after the `TFS`
  replacement. `EL_EXIT_COUNT` and `EL_STUDENT_COUNT` are integers ≥ 10.
  `EL_EXIT_RATE` is a one-decimal-place float on a 0–100 scale (district
  files); state files publish the rate with two decimal places.
- **`SYSTEM_ID` district code formatting.** Codes are 3-digit standard
  (`601`–`899`) or 7-digit charter (`7820120`, `7830210`, `7991893`,
  etc.). Apply `.cast(pl.Utf8).str.zfill(3)` per
  `src/etl/education/CLAUDE.md` — never truncate. 7-digit codes are
  preserved as-is by `str.zfill(3)` because they already exceed the
  3-digit minimum.
- **Detail-level routing.** Every district-file row is `detail_level =
  "district"`. Every state-file row is `detail_level = "state"`. Per the
  education domain conventions, state rows have `district_code = NULL`
  and `school_code = NULL`. District rows have `district_code = SYSTEM_ID`
  and `school_code = NULL`.
- **Charter and state-school LEAs included.** Rows like `State Charter
  Schools-Georgia Cyber Academy` (`7820120`), `Commission Charter
  Schools-Pataula Charter Academy` (`7830210`), and `State Schools-Atlanta
  Area School for the Deaf` (`7991893`) are first-class district rows,
  not aggregates. Their 7-digit `district_code` will get a null
  `district_census_id` from `add_census_district_code()`, which is
  expected behavior.
- **Charter LEA composition changes year over year.** 2019 has 213 rows,
  2024 has 235 rows. The growth is driven primarily by new charter LEAs
  being added (e.g. `7820619` State Charter Schools- Utopian Academy for
  the Arts Trilith first appears in 2024) and by the State Schools
  representation changing: three individual `State Schools-…` rows
  (`7991893`–`7991895`) in 2019 only, none at all in 2020, then a single
  consolidated `799` row from 2021 onward. No `(year,
  district_code)` duplicates are present in any single bronze file.
- **District 890 in 2023 has a null SYSTEM_NAME.** All metrics are
  suppressed. The row is still emitted to gold; the districts dimension
  resolves the name via DISTRICT_NAME_OVERRIDES.
- **Filename year = `FISCAL_YEAR`.** Confirmed across all 12 files. Use
  `FISCAL_YEAR.cast(pl.Int32)` for the gold `year` column.
- **No demographic breakdown.** Every row is "All EL students" — there is
  no demographic dimension in this topic. Per data-cleaning-standards §5,
  omit the `demographic` column entirely.
- **Natural primary keys.** The natural key for the gold fact is
  `(year, district_code)` for district rows and `(year,)` for state rows.
  No `(year, district_code)` duplicates exist within the source bronze.

## Gold Schema Classification

| Bronze Column | Source File Group | Gold Role | Gold Name | Notes |
|---------------|-------------------|-----------|-----------|-------|
| #RPT_NAME | district 2023, state 2023 | not_in_gold | — | Constant report-name string; drop. |
| FISCAL_YEAR | both | fact_key | year | Cast to `pl.Int32`. |
| SYSTEM_ID | district (all years), state 2023 | fact_key (district only) | district_code | Cast to `pl.Utf8`, `.str.zfill(3)`. State-row value (`State of Georgia`) is replaced by NULL via `null_aggregate_geography`. |
| SYSTEM_NAME | district (all years), state 2023 | dimension_attribute / drop | — | District: stored in districts dimension table. State 2023: constant `"State of Georgia"`, drop. |
| EL_EXIT_COUNT | district (all years), state 2022 + 2024 + 2023 | fact_metric | el_exit_count | `pl.Int64`. `TFS` → NULL. |
| EL_STUDENT_COUNT | same as above | fact_metric | el_student_count | `pl.Int64`. `TFS` → NULL. |
| EL_EXIT_RATE | same as above | fact_metric | el_exit_rate | `pl.Float64` on 0–1 scale (bronze 0–100 ÷ 100). District 2024 quirk: null whenever either count column is null. |
| STATE_EL_EXIT_COUNT | state 2019–2021 | fact_metric | el_exit_count | Same as `EL_EXIT_COUNT`; renamed during transform. |
| STATE_EL_STUDENT_COUNT | state 2019–2021 | fact_metric | el_student_count | Same as `EL_STUDENT_COUNT`; renamed during transform. |
| STATE_EL_EXIT_RATE | state 2019–2021 | fact_metric | el_exit_rate | Same as `EL_EXIT_RATE`; renamed during transform. |
| — (synthesized) | both | fact_key | school_code | Always NULL — no school-level detail in this topic. |
| — (synthesized) | both | transient pipeline column | detail_level | `"district"` for district-file rows, `"state"` for state-file rows. **Not persisted in gold parquet** — `export_to_parquet` drops it and encodes the detail level in the output filename (`districts.parquet` / `states.parquet`), per `src/etl/education/CLAUDE.md` ("Columns NOT Stored in Fact Tables") and validator check 5 (star-schema compliance forbids a `detail_level` column). The approved v1 gold and its ODCS contract carry no `detail_level` property; the REST API surfaces detail-level selection via its own `detail` parameter. (An earlier revision of this doc claimed the column was persisted — that was never true of the emitted gold.) |
