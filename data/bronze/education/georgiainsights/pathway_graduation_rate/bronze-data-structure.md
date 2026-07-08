# pathway_graduation_rate - Bronze Data Structure

## Overview

- Topic: pathway_graduation_rate
- Source: georgiainsights
- Files: 4 files spanning 2021-2024 (one `.xlsx` per cohort graduation year)
- Unreadable files: none
- Year representation: `COHORT YEAR` column in every file (single value per file matching the filename year, e.g., 2024). Dtype drifts across files — `Int64` in 2021/2022 and `String` in 2023/2024. Filename also embeds the same year as the leading token in `YYYY Pathways Graduation Rates.xlsx`.
- Filename-to-data year offset: same (filename year = COHORT YEAR = data year)
- Detail levels: state (`SYSTEM ID = "ALL"`, `SCHOOL ID = "ALL"`), district (`SYSTEM ID = digits`, `SCHOOL ID = "ALL"`), school (`SYSTEM ID = digits`, `SCHOOL ID = digits`). Every file has exactly one state row.
- Percentage scale: 0-100 (all four pathway metrics are percentages of graduates completing each pathway type)
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: Georgia Insights (GaDOE) public data downloads — exact page URL not recorded at acquisition time
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| 2021 Pathways Graduation Rates.xlsx | 94461ebf5e9794076da5d48760ca80062634014507a532debdec33b1fb15114a |
| 2022 Pathways Graduation Rates.xlsx | 732e6748e9987ef011090bfab97f2237e227a10278331108c28a2f5a688b6eb9 |
| 2023 Pathways Graduation Rates.xlsx | 07cce0e718ac936994ab386b89e28ce61285e1dbf5c10ea61ab3aa231e83352b |
| 2024 Pathways Graduation Rates.xlsx | e4afeb6c86a8b5e9fd6485dfaf0dff0296abdd93799780994dd35be261c24c72 |

## Excel Sheet Structure

| File(s) | Sheets | Notes |
|---------|--------|-------|
| 2021, 2022, 2024 | `Sheet1` (Data) | Default workbook sheet name. |
| 2023 | `2023` (Data) | Sheet was renamed to the year for this one release. |

All four files have a single data sheet with no separate legend/metadata sheet. Column headers are always on row 0 — no disclaimer banner row to skip. The transform should open the first (and only) sheet in each workbook rather than hard-coding a sheet name.

## Summary

Georgia's CCRPI "Pathways" indicator measures the share of each graduating cohort that completed a coherent three-course sequence ("pathway") in one of four elective areas. Each metric is reported on a 0-100 percentage scale:

- **Advanced Academic pathway completion rate** — % of graduates who finished an Advanced Placement, International Baccalaureate, or dual enrollment pathway.
- **World Language pathway completion rate** — % of graduates who completed three or more courses in a single world language.
- **Fine Arts pathway completion rate** — % of graduates who completed a three-course Fine Arts sequence (visual arts, music, theater, dance).
- **CTAE pathway completion rate** — % of graduates who completed a Career, Technical, and Agricultural Education pathway (three sequenced CTAE courses in a single program area).

The metrics are published annually at the state, district, and school levels with no demographic breakdown (one row per geography per year). Pathway completion is a CCRPI Readiness indicator component and feeds into each school's CCRPI Readiness score.

## Eras

### Era 1: 2021-2024 (single era)

All four files share the same 9 columns in the same order:

| Column | Description |
|--------|-------------|
| `COHORT YEAR` | Cohort graduation year (e.g., 2024). **Dtype drift**: `Int64` in 2021 and 2022; `String` in 2023 and 2024. Single value per file, always equal to the filename year. |
| `SYSTEM ID` | GOSA district code. **Dtype drift**: `Int64` in 2021/2022 (so state rows have `SYSTEM ID = null` because `"ALL"` cannot be cast); `String` in 2023/2024 (state rows have `SYSTEM ID = "ALL"`). Standard districts have 3-digit codes (e.g., `625`); state charter networks have 7-digit codes (e.g., `7830634`). |
| `SYSTEM NAME` | District name, title case (e.g., `Savannah-Chatham County`). State-level row value is `All Systems`. State charter networks use names like `State Charter Schools- Georgia Cyber Academy`. |
| `SCHOOL ID` | GOSA school code. String in every file. Standard schools have 3-digit codes in 2021-2023 (e.g., `195`); 2024 zero-pads them to 4 digits (e.g., `0195`). State- and district-level aggregate rows use the literal string `"ALL"`. |
| `SCHOOL NAME` | School name, title case (e.g., `Islands High School`). District aggregate rows use `All Schools`; state aggregate row also uses `All Schools`. |
| `ADVANCED ACADEMIC` | Advanced Academic pathway completion rate (%). 0-100 scale. **Dtype drift**: `Float64` in 2021 (no suppression markers; see ETL Considerations); `String` in 2022-2024 because of the suppression markers `NA` and `TFS`. |
| `WORLD LANGUAGE` | World Language pathway completion rate (%). Same dtype-by-year pattern. |
| `FINE ARTS` | Fine Arts pathway completion rate (%). Same dtype-by-year pattern. |
| `CTAE` | CTAE (Career, Technical, and Agricultural Education) pathway completion rate (%). Same dtype-by-year pattern. |

#### Sample Data (2024 file)

```text
COHORT YEAR | SYSTEM ID | SYSTEM NAME              | SCHOOL ID | SCHOOL NAME                    | ADVANCED ACADEMIC | WORLD LANGUAGE | FINE ARTS | CTAE
2024        | ALL       | All Systems              | ALL       | All Schools                    | 99.50             | 99.26          | 97.89     | 98.24
2024        | 625       | Savannah-Chatham County  | 0411      | Islands High School            | 100.00            | 100.00         | 100.00    | 98.92
2024        | 748       | Ware County              | 0195      | Ware County High School        | 99.29             | 98.08          | 97.78     | 94.42
2024        | 733       | Taylor County            | ALL       | All Schools                    | 100.00            | TFS            | 100.00    | 100.00
2024        | 622       | Carroll County           | 0112      | KidsPeace                      | NA                | NA             | NA        | NA
```

#### Statistics

| File | Rows | State rows | District rows | School rows |
|------|-----:|-----------:|--------------:|------------:|
| 2021 | 688 | 1 | 195 | 492 |
| 2022 | 690 | 1 | 194 | 495 |
| 2023 | 694 | 1 | 195 | 498 |
| 2024 | 701 | 1 | 197 | 503 |

Numeric summary of pathway metrics (non-null values only):

| Year | Column | n | min | max | mean |
|------|--------|--:|----:|----:|-----:|
| 2021 | Advanced Academic | 688 | 0.0 | 100.0 | 88.67 |
| 2021 | World Language | 688 | 0.0 | 100.0 | 76.37 |
| 2021 | Fine Arts | 688 | 0.0 | 100.0 | 84.17 |
| 2021 | CTAE | 688 | 0.0 | 100.0 | 87.43 |
| 2022 | Advanced Academic | 550 | 30.43 | 100.0 | 99.05 |
| 2022 | World Language | 388 | 41.3 | 100.0 | 98.65 |
| 2022 | Fine Arts | 495 | 18.18 | 100.0 | 96.55 |
| 2022 | CTAE | 596 | 15.79 | 100.0 | 96.96 |
| 2023 | Advanced Academic | 564 | 58.82 | 100.0 | 99.24 |
| 2023 | World Language | 407 | 35.0 | 100.0 | 98.66 |
| 2023 | Fine Arts | 507 | 22.0 | 100.0 | 97.04 |
| 2023 | CTAE | 597 | 24.75 | 100.0 | 97.48 |
| 2024 | Advanced Academic | 579 | 38.71 | 100.0 | 99.16 |
| 2024 | World Language | 394 | 36.0 | 100.0 | 99.12 |
| 2024 | Fine Arts | 522 | 21.43 | 100.0 | 97.29 |
| 2024 | CTAE | 600 | 24.29 | 100.0 | 97.90 |

Note the stark year-over-year shift: 2021 reports many low (and zero) values, while 2022-2024 consistently show means near 99%. This is because 2021 encoded "no applicable students" as `0` (non-suppressive zeros), whereas 2022+ encodes that as `NA`/`TFS` suppression markers — see "ETL Considerations: 2021 zero-encoding" below.

#### Null Counts

In every file, all 9 columns have zero true nulls. Suppression (for 2022-2024) is always via text markers, not null. The only exception is the state-level row in the 2021 and 2022 files where `SYSTEM ID` is `null` because the column was parsed as `Int64` and `"ALL"` could not be cast — reading those files with `schema_overrides={"SYSTEM ID": pl.String}` recovers `"ALL"`.

#### Categorical Columns

`SYSTEM ID` and `SCHOOL ID` are identifier columns with categorical behavior only via their sentinel value `"ALL"`. Everything else in those columns is numeric-looking strings.

| Column | Distinct "category" values | Notes |
|--------|----------------------------|-------|
| `SYSTEM ID` | `"ALL"` (1 row per file, state aggregate) | Numeric values otherwise |
| `SCHOOL ID` | `"ALL"` (1 per district row + 1 state row per file) | Numeric values otherwise |

There are no true categorical columns (no demographic breakdown, no subject/pathway type column — each pathway is a separate metric column).

#### Suppression Markers

| Column | Year | Non-numeric values (counts) |
|--------|------|-----------------------------|
| `SYSTEM ID` (via `pl.String` override) | 2021-2024 | `ALL` (1) — state aggregate row |
| `SCHOOL ID` | 2021 | `ALL` (196) |
| `SCHOOL ID` | 2022 | `ALL` (195) |
| `SCHOOL ID` | 2023 | `ALL` (196) |
| `SCHOOL ID` | 2024 | `ALL` (198) |
| `ADVANCED ACADEMIC` | 2021 | (none — column is Float64 with real zeros; see ETL Considerations) |
| `ADVANCED ACADEMIC` | 2022 | `NA` (64), `TFS` (76) |
| `ADVANCED ACADEMIC` | 2023 | `NA` (58), `TFS` (72) |
| `ADVANCED ACADEMIC` | 2024 | `NA` (59), `TFS` (63) |
| `WORLD LANGUAGE` | 2021 | (none) |
| `WORLD LANGUAGE` | 2022 | `NA` (136), `TFS` (166) |
| `WORLD LANGUAGE` | 2023 | `NA` (168), `TFS` (119) |
| `WORLD LANGUAGE` | 2024 | `NA` (171), `TFS` (136) |
| `FINE ARTS` | 2021 | (none) |
| `FINE ARTS` | 2022 | `NA` (77), `TFS` (118) |
| `FINE ARTS` | 2023 | `NA` (66), `TFS` (121) |
| `FINE ARTS` | 2024 | `NA` (70), `TFS` (109) |
| `CTAE` | 2021 | (none) |
| `CTAE` | 2022 | `NA` (50), `TFS` (44) |
| `CTAE` | 2023 | `NA` (45), `TFS` (52) |
| `CTAE` | 2024 | `NA` (49), `TFS` (52) |

Per GaDOE conventions used across GeorgiaInsights releases:
- `TFS` = "Too Few Students" — small-cell suppression (denominator below reporting threshold).
- `NA` = "Not Applicable" — no applicable students in that pathway at that geography (e.g., an alternative school with no regular graduates; a K-8 academy that appears only because it has a district enrollment roll-up).

Both markers map to NULL in gold. Downstream users should treat them identically unless the distinction is called out.

## ETL Considerations

### 2021 zero-encoding (most important)

The 2021 file has **zero suppression markers** across all four pathway columns (columns read as `Float64` rather than `String`). Instead, there are 368 numeric `0.0` values concentrated at specialty schools (KidsPeace psychiatric facility, alternative schools, junior highs, E-Learning academies, detention facilities) and at small rural districts for less-common pathways — the same row identities that appear as `NA`/`TFS` in 2022-2024. Examples:

- `622 / 112 / KidsPeace`: 2021 = `(0, 0, 0, 0)`; 2024 = `(NA, NA, NA, NA)`.
- `625 / 107 / UHS of Savannah Coastal Harbor`: 2021 = `(0, 0, 0, 0)`; 2024 = `(NA, NA, TFS, NA)`.
- `602 / ALL / Atkinson County` (district row): 2021 = `(100, 0, 100, 97.65)`; the `0` for World Language at a small rural district mirrors the `TFS` pattern in later years for the same geography.

**The transform must distinguish legitimate zeros from zero-encoded suppression in the 2021 file, and there is no clean signal to do it with.** Without a denominator column (cohort size) in this topic, the best we can do is one of:

1. **Preserve the 2021 zeros as-is** and document this in `gold-data-structure.md` / `_metadata.json` so downstream users know 2021 rates near 0 may mean "0%" or "suppressed" ambiguously.
2. **Heuristic null-out** for 2021 rows where all four pathway values are 0 (47 such rows — almost certainly all suppression, since it is extremely unlikely a graduating cohort completed no pathway in any of the four areas) and leave partial-zero rows intact. This is safer than blanket-nulling.
3. **Blanket null-out** every 2021 zero, risking false nullification of a few legitimate district-level zeros.

Recommendation: adopt option 2 (null-out rows where all four pathway values = 0 in 2021 only) and document the remaining 2021 zeros as genuine rates. Flag the decision in `transform.py` with a comment and confirm the row count (47) in the transform manifest.

### Column and sheet dtype drift across years

Polars infers different dtypes for the same logical column depending on whether the workbook cells are all numeric (2021) or contain text markers (2022-2024):

| Column | 2021 | 2022 | 2023 | 2024 |
|--------|------|------|------|------|
| COHORT YEAR | Int64 | Int64 | String | String |
| SYSTEM ID | Int64 | Int64 | String | String |
| SCHOOL ID | String | String | String | String |
| ADVANCED ACADEMIC | Float64 | String | String | String |
| WORLD LANGUAGE | Float64 | String | String | String |
| FINE ARTS | Float64 | String | String | String |
| CTAE | Float64 | String | String | String |

To avoid losing the state-row `SYSTEM ID = "ALL"` in 2021/2022, read every file with `schema_overrides={"COHORT YEAR": pl.String, "SYSTEM ID": pl.String, "SCHOOL ID": pl.String, "ADVANCED ACADEMIC": pl.String, "WORLD LANGUAGE": pl.String, "FINE ARTS": pl.String, "CTAE": pl.String}`, then cast numerics with `cast(pl.Float64, strict=False)` after suppression handling.

### Suppression marker vocabulary

Two markers — `NA` and `TFS` — both map to NULL. Use `strict=False` casting or replace explicitly. No other markers appear (no `No Data`, no `*`, no blank strings).

### Geography sentinels and ID padding

State-level row: `SYSTEM ID == "ALL"` AND `SCHOOL ID == "ALL"`. District-level: `SYSTEM ID == "<digits>"` AND `SCHOOL ID == "ALL"`. School-level: both are digits. No `(SYSTEM ID = "ALL", SCHOOL ID != "ALL")` rows exist in any file (verified).

Per `src/etl/education/CLAUDE.md`:
- Map `"ALL"` sentinels to NULL before zfill.
- `district_code`: `.cast(pl.Utf8).str.zfill(3)` — preserves 7-digit charter codes (e.g., `7830634`) while padding standard 3-digit codes.
- `school_code`: `.cast(pl.Utf8).str.zfill(4)` — 2021-2023 files store school IDs as 3 chars (e.g., `195`), while 2024 stores them as 4 chars (`0195`). After zfill, both become `0195`.

### Sheet name for 2023

The 2023 workbook has one sheet named `2023` rather than `Sheet1`. The transform should open the first sheet of each workbook (e.g., via openpyxl's default worksheet or `pl.read_excel(..., sheet_id=1)`) rather than hard-coding a sheet name.

### No demographic breakdown

This topic has no subgroup/demographic column — each row is (year, district, school) only. The `demographic` gold key is therefore N/A and should be omitted from the fact table entirely (per root `CLAUDE.md`, demographic is included only when the topic breaks out subgroups).

### State charter networks use 7-digit SYSTEM IDs

State charter school networks (e.g., `7820120 / State Charter Schools- Georgia Cyber Academy`, `7830634 / State Charter Schools II- Georgia School for Innovation`) use 7-digit `SYSTEM ID` codes. These must be preserved through the zfill step (zfill(3) leaves them untouched because they are already longer than 3). Their `district_code` values should match the `district_type = state_charter` or `commission_charter` entries in `districts.parquet` — verify the dimension covers them before transforming; a few may need to be added.

### Year column handling

`COHORT YEAR` is guaranteed to match the filename year in every file (verified). The transform can safely parse the year from the filename as a sanity check but should use the column value as the source of truth (cast from string to `pl.Int32`).

### Percentage scale: no conversion needed

All four pathway metrics are already on the 0-100 scale. Per `src/etl/education/CLAUDE.md` "Percentage Scale Exceptions" (which lists score columns and star ratings), pathway completion rates are standard percentages — but by the root `CLAUDE.md` default, percentages should go to 0-1. Check the universal `data-cleaning-standards` skill before deciding; if 0-100 is required for alignment with other CCRPI "percent meeting" metrics, keep as-is. Otherwise divide by 100. **This is the one remaining decision for the transform.**

### No 2020 or earlier data

The pathway graduation rate is a relatively new CCRPI indicator, reported in this dataset starting with the 2021 cohort. No 2020 file exists (cohort 2020 was the COVID graduation class; CCRPI scoring was suspended). No pre-2021 historical file exists in this topic.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| `COHORT YEAR` | fact_key | `year` | Cast to `pl.Int32` via `cast(pl.Utf8).cast(pl.Int32)`. Matches filename year. |
| `SYSTEM ID` | fact_key | `district_code` | Cast to `pl.Utf8`, map `"ALL"` → NULL for state row, then `zfill(3)`. Preserve 7-digit charter codes. |
| `SYSTEM NAME` | dimension_attribute | — | Goes to `districts.parquet` dimension; `All Systems` maps to NULL/state. Drop from fact. |
| `SCHOOL ID` | fact_key | `school_code` | Cast to `pl.Utf8`, map `"ALL"` → NULL for state/district rows, then `zfill(4)`. |
| `SCHOOL NAME` | dimension_attribute | — | Goes to `schools.parquet` dimension; `All Schools` maps to NULL. Drop from fact. |
| `ADVANCED ACADEMIC` | fact_metric | `advanced_academic_pathway_rate` | `pl.Float64`, 0-100 scale (subject to final percentage-scale decision; see ETL Considerations). Cast `NA`/`TFS` → null. Apply 2021 all-zero-row null-out. |
| `WORLD LANGUAGE` | fact_metric | `world_language_pathway_rate` | Same handling as above. |
| `FINE ARTS` | fact_metric | `fine_arts_pathway_rate` | Same handling as above. |
| `CTAE` | fact_metric | `ctae_pathway_rate` | Same handling as above. |

The gold fact table will have one row per `(year, district_code, school_code)` tuple with no demographic breakdown. Output per `src/etl/education/CLAUDE.md` convention:

```
data/gold/education/pathway_graduation_rate/
├── year=2021/{states,districts,schools}.parquet
├── year=2022/{states,districts,schools}.parquet
├── year=2023/{states,districts,schools}.parquet
├── year=2024/{states,districts,schools}.parquet
├── _metadata.json
└── README.md
```

## Corrections (2026-06-12 rebuild verification)

Stale or imprecise claims found while re-verifying every invariant against the
bronze files during the clean-room transform rewrite. Each item states the
evidence; the body of this document above is preserved as originally written.

1. **2021-2023 `SCHOOL ID` values are NOT uniformly 3-char.** The column table
   and the "Geography sentinels and ID padding" section claim "Standard schools
   have 3-digit codes in 2021-2023 (e.g., `195`)" with 2024 zero-padding to 4.
   Re-verified with string-typed reads: 2021-2023 each mix unpadded 3-char codes
   with naturally-4-digit codes (2021: 142 distinct 3-char + 80 distinct 4-char,
   e.g. `1018`, `1052`; 2022: 146 + 83; 2023: 147 + 85; none of the 4-char codes
   are zero-padded). Only 2024 ships uniformly 4-char, zero-padded codes
   (`0100`, ...). The prescribed remedy is unchanged — `zfill(4)` pads the
   3-char codes and passes naturally-4-digit codes through — but the width-drift
   description above is an overgeneralization.

2. **The "SYSTEM ID = null" state rows in 2021/2022 are a polars
   type-inference artifact, not bronze nulls.** The Null Counts section already
   frames this conditionally; confirming for the record: the shared
   `read_bronze_file()` Excel path (pandas `read_excel(dtype=str)`) yields
   **zero** `SYSTEM ID` nulls in every file — the state row carries the literal
   string `ALL` in all four years. No `schema_overrides` workaround is needed
   under the shared reader.

3. **The projected gold layout's `_metadata.json` is process-stale.** Under the
   contract-emitting pipeline there is no `_metadata.json` (and no
   `gold-data-structure.md` as referenced in the "2021 zero-encoding" section);
   the transform emits `contracts/education/pathway_graduation_rate.odcs.yaml`,
   `README.md`, `_transform_manifest.json`, and `_validation.json` instead.

4. **Resolved decisions.** The percentage-scale question ("the one remaining
   decision for the transform") is resolved: all four rates are standard
   percentages, divided by 100 to the canonical 0-1 scale (`unit: proportion`).
   The 2021 zero-encoding handling adopts option 2 (null-out the 47 rows where
   all four pathway values are 0; re-verified count 47, with 368 total zero
   cells in 2021 and zero `0` cells in 2022-2024), recorded per column via
   `manifest.record_masked` and guarded by the `no_all_zero_pathway_rows`
   contract quality check.
