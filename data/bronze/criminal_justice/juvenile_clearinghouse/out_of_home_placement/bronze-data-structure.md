# out_of_home_placement — Bronze Data Structure

## Overview

- Topic: out_of_home_placement
- Source: juvenile_clearinghouse
- Files: 1 file spanning 2005–2025 (all years in a single CSV)
- Unreadable files: none
- Year representation: `PeriodYear` column, plain 4-digit integer (2005–2025). Filename suffix (`2026-06`) is the WordPress upload month, not a data year.
- Filename-to-data year offset: n/a — filename carries the publication/upload month only; data years come from the `PeriodYear` column.
- Detail levels: county only (159 Georgia counties + an `OUT OF STATE` pseudo-county). No state-level rollup rows — state totals must be derived by summing.
- Percentage scale: n/a — all metrics are raw counts; no percentage columns.
- Checksums generated: 2026-07-02

## Source Provenance

- **Source URL**: <https://juveniledata.georgiacourts.gov/wp-content/uploads/2026/06/Juvenile-Justice-Decision-Point-Raw-Data-OHP-STP.csv> (linked from the "Raw Data" section of <https://juveniledata.georgiacourts.gov/dashboards-reports/>). Definitions: <https://juveniledata.georgiacourts.gov/definitions/>.
- **Retrieved**: 2026-07-02 (UTC 2026-07-02T03:25:38Z)
- **Method**: scripted download — `uv run python -m src.etl.criminal_justice.juvenile_clearinghouse.download`. Source URLs embed the upload month (`/wp-content/uploads/2026/06/`) — never hardcode; the downloader re-scrapes the landing page every run. Full details: `_provenance.md` in this directory.

## File Checksums

Generated: 2026-07-02

| File | SHA-256 |
|------|---------|
| decision_point_raw_data_ohp_stp_2026-06.csv | 80d144c382cbfe291f4c1ae3eee399c25ab3c3b4e9faa9e6f4eb114515690c9c |

## Summary

County-by-year counts of juvenile-court commitments and short-term program (STP) admissions from the Georgia Juvenile Justice Data Clearinghouse, 2005–2025. Five measures per county-year: all commitments, felony commitments, felony commitments resulting in out-of-home placement (OHP), all STP admissions, and felony STP admissions. Two of those measures — felony commitments and all STP admissions — also carry four-way race splits (Black / White / Hispanic / Other). No rates or percentages; everything is a raw count. Counts are unsuppressed (values of 1 and 2 appear throughout).

## Eras

Single era — one CSV covers all years with one fixed header.

### Era 1: 2005–2025

2,921 rows × 16 columns. Grain: one row per (CountyName, PeriodYear) — verified unique, no duplicates.

| Column | Description |
|--------|-------------|
| CountyName | County name, UPPERCASE (e.g. `APPLING`, `BEN HILL`); includes `OUT OF STATE` |
| PeriodYear | 4-digit year, 2005–2025 |
| CountyFips | 5-digit county FIPS (e.g. `13001`); parses as integer — no leading-zero risk for GA (`13xxx`) |
| AllCommitments | All juvenile-court commitments (count) |
| FelonyCommitments | Felony commitments (count) |
| FelonyCommitmentsOhp | Felony commitments resulting in out-of-home placement (count) |
| AllStpAdmissions | All short-term program admissions (count) |
| FelonyStpAdmissions | Felony STP admissions (count) |
| FelonyCommitBlack | Felony commitments — Black youth (count) |
| FelonyCommitWhite | Felony commitments — White youth (count) |
| FelonyCommitHispanic | Felony commitments — Hispanic youth (count) |
| FelonyCommitOther | Felony commitments — Other race (count) |
| AllStpAdmissionBlack | All STP admissions — Black youth (count) |
| AllStpAdmissionWhite | All STP admissions — White youth (count) |
| AllStpAdmissionHispanic | All STP admissions — Hispanic youth (count) |
| AllStpAdmissionOther | All STP admissions — Other race (count) |

#### Sample Data

```
┌────────────┬────────────┬────────────┬────────────────┬───────────────────┬──────────────────────┬──────────────────┬─────────────────────┬───────────────────┬───────────────────┬──────────────────────┬───────────────────┬──────────────────────┬──────────────────────┬─────────────────────────┬──────────────────────┐
│ CountyName ┆ PeriodYear ┆ CountyFips ┆ AllCommitments ┆ FelonyCommitments ┆ FelonyCommitmentsOhp ┆ AllStpAdmissions ┆ FelonyStpAdmissions ┆ FelonyCommitBlack ┆ FelonyCommitWhite ┆ FelonyCommitHispanic ┆ FelonyCommitOther ┆ AllStpAdmissionBlack ┆ AllStpAdmissionWhite ┆ AllStpAdmissionHispanic ┆ AllStpAdmissionOther │
╞════════════╪════════════╪════════════╪════════════════╪═══════════════════╪══════════════════════╪══════════════════╪═════════════════════╪═══════════════════╪═══════════════════╪══════════════════════╪═══════════════════╪══════════════════════╪══════════════════════╪═════════════════════════╪══════════════════════╡
│ LAURENS    ┆ 2021       ┆ 13175      ┆ 11             ┆ 10                ┆ 8                    ┆ 9                ┆ 4                   ┆ 7                 ┆ 3                 ┆ 0                    ┆ 0                 ┆ 6                    ┆ 3                    ┆ 0                       ┆ 0                    │
│ BULLOCH    ┆ 2011       ┆ 13031      ┆ 6              ┆ 6                 ┆ 5                    ┆ 26               ┆ 16                  ┆ 5                 ┆ 1                 ┆ 0                    ┆ 0                 ┆ 20                   ┆ 4                    ┆ 0                       ┆ 2                    │
│ MADISON    ┆ 2025       ┆ 13195      ┆ 3              ┆ 3                 ┆ 2                    ┆ 3                ┆ 2                   ┆ 1                 ┆ 2                 ┆ 0                    ┆ 0                 ┆ 1                    ┆ 2                    ┆ 0                       ┆ 0                    │
│ TWIGGS     ┆ 2018       ┆ 13289      ┆ 4              ┆ 4                 ┆ 4                    ┆ 0                ┆ 0                   ┆ 4                 ┆ 0                 ┆ 0                    ┆ 0                 ┆ 0                    ┆ 0                    ┆ 0                       ┆ 0                    │
│ CAMDEN     ┆ 2021       ┆ 13039      ┆ 6              ┆ 4                 ┆ 4                    ┆ 2                ┆ 1                   ┆ 2                 ┆ 1                 ┆ 1                    ┆ 0                 ┆ 2                    ┆ 0                    ┆ 0                       ┆ 0                    │
└────────────┴────────────┴────────────┴────────────────┴───────────────────┴──────────────────────┴──────────────────┴─────────────────────┴───────────────────┴───────────────────┴──────────────────────┴───────────────────┴──────────────────────┴──────────────────────┴─────────────────────────┴──────────────────────┘
```

#### Statistics

(read with `null_values=['NULL']` — see ETL Considerations)

```
┌────────────┬────────────┬────────────┬──────────────┬────────────────┬───────────────────┬──────────────────────┬──────────────────┬─────────────────────┬───────────────────┬───────────────────┬──────────────────────┬───────────────────┬──────────────────────┬──────────────────────┬─────────────────────────┬──────────────────────┐
│ statistic  ┆ CountyName ┆ PeriodYear ┆ CountyFips   ┆ AllCommitments ┆ FelonyCommitments ┆ FelonyCommitmentsOhp ┆ AllStpAdmissions ┆ FelonyStpAdmissions ┆ FelonyCommitBlack ┆ FelonyCommitWhite ┆ FelonyCommitHispanic ┆ FelonyCommitOther ┆ AllStpAdmissionBlack ┆ AllStpAdmissionWhite ┆ AllStpAdmissionHispanic ┆ AllStpAdmissionOther │
╞════════════╪════════════╪════════════╪══════════════╪════════════════╪═══════════════════╪══════════════════════╪══════════════════╪═════════════════════╪═══════════════════╪═══════════════════╪══════════════════════╪═══════════════════╪══════════════════════╪══════════════════════╪═════════════════════════╪══════════════════════╡
│ count      ┆ 2921       ┆ 2921.0     ┆ 2918.0       ┆ 2921.0         ┆ 2921.0            ┆ 2921.0               ┆ 2921.0           ┆ 2921.0              ┆ 2921.0            ┆ 2921.0            ┆ 2921.0               ┆ 2921.0            ┆ 2921.0               ┆ 2921.0               ┆ 2921.0                  ┆ 2921.0               │
│ null_count ┆ 0          ┆ 0.0        ┆ 3.0          ┆ 0.0            ┆ 0.0               ┆ 0.0                  ┆ 0.0              ┆ 0.0                 ┆ 0.0               ┆ 0.0               ┆ 0.0                  ┆ 0.0               ┆ 0.0                  ┆ 0.0                  ┆ 0.0                     ┆ 0.0                  │
│ mean       ┆ null       ┆ 2014.481   ┆ 13159.995888 ┆ 12.376583      ┆ 7.298186          ┆ 4.863403             ┆ 13.671345        ┆ 5.84834             ┆ 5.232455          ┆ 1.397124          ┆ 0.490585             ┆ 0.178021          ┆ 8.988702             ┆ 3.545361             ┆ 0.841835                ┆ 0.295447             │
│ std        ┆ null       ┆ 5.983631   ┆ 91.639087    ┆ 33.365462      ┆ 16.845829         ┆ 10.419497            ┆ 27.813312        ┆ 13.846638           ┆ 14.355052         ┆ 2.386846          ┆ 2.260742             ┆ 0.650982          ┆ 23.292134            ┆ 5.982974             ┆ 3.656526                ┆ 0.952651             │
│ min        ┆ APPLING    ┆ 2005.0     ┆ 13001.0      ┆ 0.0            ┆ 0.0               ┆ 0.0                  ┆ 0.0              ┆ 0.0                 ┆ 0.0               ┆ 0.0               ┆ 0.0                  ┆ 0.0               ┆ 0.0                  ┆ 0.0                  ┆ 0.0                     ┆ 0.0                  │
│ 25%        ┆ null       ┆ 2009.0     ┆ 13081.0      ┆ 1.0            ┆ 1.0               ┆ 0.0                  ┆ 2.0              ┆ 0.0                 ┆ 0.0               ┆ 0.0               ┆ 0.0                  ┆ 0.0               ┆ 0.0                  ┆ 0.0                  ┆ 0.0                     ┆ 0.0                  │
│ 50%        ┆ null       ┆ 2014.0     ┆ 13159.0      ┆ 3.0            ┆ 2.0               ┆ 1.0                  ┆ 5.0              ┆ 2.0                 ┆ 1.0               ┆ 1.0               ┆ 0.0                  ┆ 0.0               ┆ 2.0                  ┆ 1.0                  ┆ 0.0                     ┆ 0.0                  │
│ 75%        ┆ null       ┆ 2019.0     ┆ 13237.0      ┆ 8.0            ┆ 6.0               ┆ 4.0                  ┆ 13.0             ┆ 5.0                 ┆ 3.0               ┆ 2.0               ┆ 0.0                  ┆ 0.0               ┆ 7.0                  ┆ 4.0                  ┆ 0.0                     ┆ 0.0                  │
│ max        ┆ WORTH      ┆ 2025.0     ┆ 13321.0      ┆ 417.0          ┆ 179.0             ┆ 102.0                ┆ 277.0            ┆ 187.0               ┆ 167.0             ┆ 30.0              ┆ 43.0                 ┆ 9.0               ┆ 247.0                ┆ 60.0                 ┆ 71.0                    ┆ 20.0                 │
└────────────┴────────────┴────────────┴──────────────┴────────────────┴───────────────────┴──────────────────────┴──────────────────┴─────────────────────┴───────────────────┴───────────────────┴──────────────────────┴───────────────────┴──────────────────────┴──────────────────────┴─────────────────────────┴──────────────────────┘
```

#### Null Counts

All columns 0 nulls except `CountyFips`: 3 (2 empty cells + 1 literal `"NULL"` string — all three are `OUT OF STATE` rows, years 2023–2025).

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| CountyName | 160 values: all 159 Georgia counties (UPPERCASE) + `OUT OF STATE`. 1:1 with CountyFips (no name↔FIPS conflicts). |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| CountyFips | `NULL` (literal string, 1 row: OUT OF STATE 2025) |
| all metric columns | none — no suppression; small cells (1, 2) published as-is |

#### Row counts per year

| Year | Rows | | Year | Rows | | Year | Rows |
|------|------|-|------|------|-|------|------|
| 2005 | 147 | | 2012 | 152 | | 2019 | 138 |
| 2006 | 150 | | 2013 | 149 | | 2020 | 107 |
| 2007 | 153 | | 2014 | 147 | | 2021 | 127 |
| 2008 | 153 | | 2015 | 137 | | 2022 | 130 |
| 2009 | 156 | | 2016 | 132 | | 2023 | 116 |
| 2010 | 156 | | 2017 | 140 | | 2024 | 127 |
| 2011 | 151 | | 2018 | 136 | | 2025 | 117 |

2,921 rows vs a full panel of 160 × 21 = 3,360 — the panel is sparse. No row in the file has all metrics zero (0 such rows), so a county-year is simply **absent** when it had no recorded activity; absence ≈ zero, not missing data. The 2020 dip (107 counties) is consistent with the COVID-19 court slowdown.

## Race bucket check (Asian / Pacific Islander)

The race splits have only **four buckets: Black, White, Hispanic, Other** — no Asian, Pacific Islander, Native American, or Multiracial buckets at all. Math test across **all 2,921 rows**:

- `FelonyCommitBlack + White + Hispanic + Other == FelonyCommitments` — **0 mismatches**
- `AllStpAdmissionBlack + White + Hispanic + Other == AllStpAdmissions` — **0 mismatches**

So the four buckets are mutually exclusive and exhaustive; `Other` absorbs Asian, Pacific Islander, Native American, multiracial, and unknown. Hispanic is treated as a race-level bucket (not a separate ethnicity overlay). Map to existing demographics-dimension codes `black` / `white` / `hispanic` / `other` — no Asian/Pacific-Islander remapping applies to this topic, and there is no split-vs-combined duplication risk.

## ETL Considerations

- **UTF-8 BOM**: file begins with `\xef\xbb\xbf` before the header. Polars handles it, but any raw header comparison must strip it.
- **Literal `"NULL"` string in `CountyFips`**: `pl.read_csv` fails with default settings (`could not parse 'NULL' as dtype i64`). Read with `null_values=["NULL"]` (or `infer_schema_length=0` + explicit casts).
- **`OUT OF STATE` pseudo-county (21 rows)**: carries **bogus FIPS `13222` for 2005–2022** — not a valid Georgia county FIPS (GA county codes are odd numbers; 13222 doesn't exist in the counties dimension) — then empty/`"NULL"` for 2023–2025. These rows hold real commitments (4–68/yr, race splits populated for felony commitments; STP columns always 0). The counties dimension (`data/gold/_dimensions/counties.parquet`, PK `county_fips`, 159 rows) cannot absorb it. Recommendation: **drop the OUT OF STATE rows** from gold (log the drop) — a county-grain fact table with an FK to the counties dimension can't carry a null-geography row, and the counts are small. If they're kept, `13222` must be nulled, never passed through as a FIPS.
- **FIPS format**: parses as bare integer (`13001`). The counties dimension PK is a **5-char string** — cast to `Utf8` (GA codes all start with `13`, so no zero-padding is needed, but cast explicitly).
- **Sparse panel — do not zero-fill blindly**: absent county-years mean no recorded activity (verified: no all-zero rows exist). Recommend leaving absent rows absent, documenting the semantics in the contract, rather than manufacturing 439 zero rows.
- **Race splits cover only 2 of 5 measures**: `FelonyCommitments` and `AllStpAdmissions` have the four-way race splits; `AllCommitments`, `FelonyCommitmentsOhp`, and `FelonyStpAdmissions` do not. After unpivoting to a `demographic` column, race rows will have NULLs for the three unsplit metrics — expected, not a data problem.
- **Internal consistency (verified, 0 violations — good candidates for contract `quality_checks`)**: `FelonyCommitments ≤ AllCommitments`; `FelonyCommitmentsOhp ≤ FelonyCommitments`; `FelonyStpAdmissions ≤ AllStpAdmissions`; race sums exactly equal their parent totals.
- **No suppression** anywhere — counts of 1 and 2 published as-is. No markers to convert.
- **`PeriodYear` basis undocumented in-file**: whether it is calendar year or state fiscal year is not stated in the CSV; consult the definitions page (<https://juveniledata.georgiacourts.gov/definitions/>) before writing contract prose. 2025 being present in a June-2026 upload suggests a completed reporting period, but verify.
- **County names are UPPERCASE** (`BEN HILL`, `MCDUFFIE`) — dimension attribute only; title-casing/joining happens against the counties dimension via FIPS, so no name normalization is needed in the fact table.
- **Schema differs from sibling clearinghouse files** — this is the only clearinghouse file with FIPS codes and CamelCase headers; do not reuse its column mapping for the other juvenile_clearinghouse topics.

## Gold Schema Classification

Recommended gold grain: **county × year × demographic** (unpivot race splits into a `demographic` FK; `all` rows carry all five metrics, race rows carry the two split metrics).

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| CountyFips | fact_key | county_fips | Cast Int64 → Utf8 (5-char); FK to counties dimension. `13222` / null → see OUT OF STATE handling |
| PeriodYear | fact_key | year | Int; partition column |
| CountyName | dimension_attribute | — | `county_name` lives in the counties dimension; drop from fact |
| AllCommitments | fact_metric | all_commitments | count, ≥0; `all` demographic rows only |
| FelonyCommitments | fact_metric | felony_commitments | count, ≥0; populated for `all` + race rows |
| FelonyCommitmentsOhp | fact_metric | felony_commitments_ohp | count, ≥0; `all` rows only. Headline candidate — this is the topic's namesake out-of-home-placement measure |
| AllStpAdmissions | fact_metric | all_stp_admissions | count, ≥0; populated for `all` + race rows |
| FelonyStpAdmissions | fact_metric | felony_stp_admissions | count, ≥0; `all` rows only |
| FelonyCommitBlack/White/Hispanic/Other | fact_key + fact_metric | demographic + felony_commitments | Unpivot → demographic ∈ {black, white, hispanic, other} (codes already in demographics dim); values feed `felony_commitments` |
| AllStpAdmissionBlack/White/Hispanic/Other | fact_key + fact_metric | demographic + all_stp_admissions | Unpivot → same demographic codes; values feed `all_stp_admissions` |
