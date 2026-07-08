# law_enforcement_employees — Bronze Data Structure

## Overview

- Topic: law_enforcement_employees
- Source: fbi_cde
- Files: 1 file (national CSV) spanning 1960–2025
- Unreadable files: none
- Year representation: `data_year` column, single calendar year integer (e.g., `2025`). Counts are as-reported snapshots (typically October 31 head counts).
- Filename-to-data year offset: filename encodes the full range (`lee_1960_2025.csv`); `data_year` is authoritative
- Detail levels: agency (ORI) only — national file, **filter to `state_abbr == "GA"`** (26,180 rows, 817 distinct ORIs). No state/county rollup rows; every row is one agency-year.
- Percentage scale: n/a — one rate column `pe_ct_per_1000` (employees per 1,000 population, not a percentage); all other metrics are raw counts
- Checksums generated: 2026-07-02

## Source Provenance

- **Source URL**: FBI Crime Data Explorer "Documents & Downloads" (`https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/downloads`), "Law Enforcement Employees Data" (LEE / PE) additional dataset. Bulk file served from a private S3 bucket via signed URLs expiring in ~15 min — re-run the downloader (`uv run python -m src.etl.criminal_justice.fbi_cde.download`), never reuse URLs. See `_provenance.md` for the signed-URL discovery mechanics.
- **Retrieved**: 2026-07-02
- **Method**: scripted fetch (`src/etl/criminal_justice/fbi_cde/download.py`)
- **License**: US federal government work — public domain

## File Checksums

Generated: 2026-07-02

| File | SHA-256 |
|------|---------|
| lee_1960_2025.csv | 36603e78db8926033f85c8727492f4913e0744ab33722307619dfcd4e098533c |

## Summary

Police-employment staffing counts per law-enforcement agency per year: sworn **officer** and **civilian** employee counts, each split by sex (male/female), plus the combined `total_pe_ct` and a derived staffing rate `pe_ct_per_1000` (total employees per 1,000 residents of the agency's service population). This is the canonical staffing denominator for agency-level rate calculations across the criminal-justice domain. 66 unbroken years of Georgia coverage (1960–2025), though early years are sparse (44–76 agencies/year in the 1960s vs ~350–530 from the 2010s onward — coverage growth, not real growth).

## Eras

Single era — one file, one header, all years. Column names are identical across the full 1960–2025 range.

### Era 1: 1960–2025 (`lee_1960_2025.csv`)

| Column | Description |
|--------|-------------|
| data_year | Calendar year of the head count (Int64) |
| ori | 9-char FBI Originating Agency Identifier, all start `GA` after the state filter |
| pub_agency_name | Agency display name (e.g., `Covington`, `State Patrol:`) |
| pub_agency_unit | Sub-unit qualifier; literal string `"NULL"` for 25,750 of 26,180 GA rows — only populated for state-agency posts/offices (e.g., State Patrol post cities, GBI field offices) |
| state_abbr | 2-letter state (constant `GA` after filter) |
| division_name | Census division (constant `South Atlantic` for GA) |
| region_name | Census region (constant `South` for GA) |
| county_name | UPPERCASE county name(s); comma-joined for multi-county agencies |
| agency_type_name | Agency category (6 values, see categoricals) |
| population_group_desc | UCR population-group bucket (16 values) |
| population | Agency service population (Int64; 0 for non-territorial agencies) |
| male_officer_ct | Male sworn officers (Int64) |
| male_cilvilian_ct | Male civilian employees (Int64) — **source typo `cilvilian`, preserve at bronze, rename at transform** |
| male_total_ct | Male total employees (Int64) |
| female_officer_ct | Female sworn officers (Int64) |
| female_cilvilian_ct | Female civilian employees (Int64) — same typo |
| female_total_ct | Female total employees (Int64) |
| officer_ct | Total sworn officers (Int64) |
| civilian_ct | Total civilian employees (Int64) |
| total_pe_ct | Total police employees (Int64) |
| pe_ct_per_1000 | Employees per 1,000 population (String — contains literal `"NULL"`) |

#### Sample Data (GA subset)

```text
┌───────────┬───────────┬─────────────────┬─────────────────┬────────────┬──────────────────┬──────────────────────────────────────────┬────────────┬─────────────────┬───────────────────┬───────────────┬───────────────────┬─────────────────────┬─────────────────┬────────────┬─────────────┬─────────────┬────────────────┐
│ data_year ┆ ori       ┆ pub_agency_name ┆ pub_agency_unit ┆ county_name┆ agency_type_name ┆ population_group_desc                    ┆ population ┆ male_officer_ct ┆ male_cilvilian_ct ┆ male_total_ct ┆ female_officer_ct ┆ female_cilvilian_ct ┆ female_total_ct ┆ officer_ct ┆ civilian_ct ┆ total_pe_ct ┆ pe_ct_per_1000 │
╞═══════════╪═══════════╪═════════════════╪═════════════════╪════════════╪══════════════════╪══════════════════════════════════════════╪════════════╪═════════════════╪═══════════════════╪═══════════════╪═══════════════════╪═════════════════════╪═════════════════╪════════════╪═════════════╪═════════════╪════════════════╡
│ 1983      ┆ GA0920000 ┆ Lowndes         ┆ NULL            ┆ LOWNDES    ┆ County           ┆ Non-MSA counties from 25,000 thru 99,999 ┆ 29927      ┆ 52              ┆ 2                 ┆ 54            ┆ 9                 ┆ 9                   ┆ 18              ┆ 61         ┆ 11          ┆ 72          ┆ 2.41           │
│ 1986      ┆ GA0220500 ┆ Whitesburg      ┆ NULL            ┆ CARROLL    ┆ City             ┆ Cities under 2,500                       ┆ 857        ┆ 4               ┆ 0                 ┆ 4             ┆ 0                 ┆ 0                   ┆ 0               ┆ 4          ┆ 0           ┆ 4           ┆ 4.67           │
│ 2020      ┆ GA0780200 ┆ Jefferson       ┆ NULL            ┆ JACKSON    ┆ City             ┆ Cities from 10,000 thru 24,999           ┆ 12349      ┆ 20              ┆ 0                 ┆ 20            ┆ 4                 ┆ 2                   ┆ 6               ┆ 24         ┆ 2           ┆ 26          ┆ 2.11           │
│ 1986      ┆ GA0170000 ┆ Burke           ┆ NULL            ┆ BURKE      ┆ County           ┆ Non-MSA counties from 10,000 thru 24,999 ┆ 12942      ┆ 30              ┆ 5                 ┆ 35            ┆ 1                 ┆ 7                   ┆ 8               ┆ 31         ┆ 12          ┆ 43          ┆ 3.32           │
│ 2015      ┆ GA1070100 ┆ Covington       ┆ NULL            ┆ NEWTON     ┆ City             ┆ Cities from 10,000 thru 24,999           ┆ 13803      ┆ 48              ┆ 3                 ┆ 51            ┆ 5                 ┆ 8                   ┆ 13              ┆ 53         ┆ 11          ┆ 64          ┆ 4.64           │
└───────────┴───────────┴─────────────────┴─────────────────┴────────────┴──────────────────┴──────────────────────────────────────────┴────────────┴─────────────────┴───────────────────┴───────────────┴───────────────────┴─────────────────────┴─────────────────┴────────────┴─────────────┴─────────────┴────────────────┘
(state_abbr / division_name / region_name omitted — constant GA / South Atlantic / South)
```

#### Statistics (GA subset, 26,180 rows)

| Column | mean | std | min | 25% | 50% | 75% | max |
|--------|------|-----|-----|-----|-----|-----|-----|
| data_year | 1998.0 | 15.4 | 1960 | 1986 | 1997 | 2011 | 2025 |
| population | 16,097 | 50,338 | 0 | 1,081 | 4,317 | 12,880 | 858,237 |
| male_officer_ct | 34.7 | 121.2 | 0 | 5 | 11 | 27 | 7,374 |
| male_cilvilian_ct | 5.0 | 28.9 | 0 | 0 | 0 | 3 | 2,113 |
| male_total_ct | 39.7 | 145.1 | 0 | 5 | 12 | 32 | 9,487 |
| female_officer_ct | 5.4 | 28.6 | 0 | 0 | 1 | 3 | 1,960 |
| female_cilvilian_ct | 9.3 | 44.2 | 0 | 0 | 2 | 6 | 2,739 |
| female_total_ct | 14.7 | 69.4 | 0 | 1 | 3 | 10 | 4,699 |
| officer_ct | 40.1 | 146.6 | 0 | 5 | 12 | 31 | 9,334 |
| civilian_ct | 14.3 | 71.3 | 0 | 0 | 3 | 9 | 4,852 |
| total_pe_ct | 54.4 | 211.4 | 0 | 6 | 16 | 42 | 14,186 |

Maxima are Atlanta PD / Fulton-area agencies in recent years — plausible.

#### Null Counts

Zero true nulls in every column (GA subset). Nulls are encoded as the literal string `"NULL"` instead — see Suppression Markers.

#### Categorical Columns

| Column | Distinct Values (GA) |
|--------|----------------------|
| ori | 817 distinct, all 9 chars starting `GA`. 734 follow `GA` + 7 digits; 83 are state-agency/campus patterns (`GAGSPxx00` State Patrol posts, `GAGBIxx00` GBI offices, `GA060309E` Clark Atlanta University) |
| pub_agency_name | 719 distinct agency names |
| pub_agency_unit | 60 distinct; `"NULL"` for 25,750/26,180 rows. Non-NULL only for state-agency sub-units (State Patrol post cities, GBI field offices, DNR districts, Ports Authority) |
| state_abbr | `GA` only (after filter) |
| division_name | `South Atlantic` only |
| region_name | `South` only |
| agency_type_name | `City` (15,153), `County` (8,260), `University or College` (1,392), `Other` (705), `Other State Agency` (444), `State Police` (226) |
| county_name | 201 distinct UPPERCASE values: 158 plain county names + 42 comma-joined multi-county values (e.g., `BARROW, GWINNETT, HALL, JACKSON`) + `NOT SPECIFIED` |
| population_group_desc | 16 UCR buckets: `Cities under 2,500` … `Cities from 500,000 thru 999,999`; `MSA counties …` / `Non-MSA counties …` size bands |

#### Suppression Markers

| Column | Non-Numeric Values (GA) |
|--------|------------------------|
| pe_ct_per_1000 | `NULL` (3,389 rows — exactly the rows where `population == 0`; division-by-zero placeholder, not suppression) |

No suppression of employee counts — all count columns are clean Int64. (Demographic race buckets: n/a — the only demographic split is male/female, so the Asian/Pacific-Islander check does not apply.)

## Detail Levels

Agency (ORI) × year only. There are no state-total or county-total rows — every row is a single reporting agency. County and state aggregates must be derived at transform time (with care: `county_name` is a display attribute, and multi-county agencies cannot be cleanly allocated — see ETL Considerations).

## Year Representation

- `data_year` column, plain calendar-year integer, 1960–2025 with **no missing years** in GA.
- Values are as-reported snapshots (typically Oct 31). Missing agency-years are absent rows, not zeros.
- Rows per GA year: 44–76 (1960s) growing to ~350–530 (2014–2025). The growth reflects reporting coverage, not agency creation.

## ETL Considerations

- **Filter first**: national file — `filter(state_abbr == "GA")` immediately (26,180 of 785,127 rows). `state_abbr`, `division_name`, `region_name` become constants → drop.
- **Source typo**: `male_cilvilian_ct` / `female_cilvilian_ct` — rename to `civilian` spelling at transform. If a future release fixes the typo, the rename will silently stop matching; select columns defensively.
- **Literal `"NULL"` strings, no true nulls**: `pub_agency_unit` and `pe_ct_per_1000` use the string `NULL`. `pl.read_csv(..., null_values=["NULL"])` handles both (safe: no legitimate value collides).
- **`pe_ct_per_1000` is derivable**: equals `total_pe_ct / population × 1000` rounded to 2 decimals (verified: max deviation 0.01, 2 rows off by rounding). Recommend **recomputing** in the transform (or dropping and letting consumers derive it) rather than parsing the string column; it is `NULL` exactly where `population == 0`.
- **`population == 0` rows (3,389)**: non-territorial agencies (state agencies, campus police, county agencies whose population is attributed to another ORI). Zero is "no service population," not missing — keep the rows, null the rate.
- **`total_pe_ct == 0` rows (238)**: agency reported zero employees (some recent years included). Conceivable (defunct/merged agencies filing zero reports) — preserve; flag in review rather than nulling.
- **Internal consistency is exact** (GA subset): `male + female = total` for officers, civilians, and each sex's total; `officer + civilian = total_pe`. Good candidates for contract `quality_checks`. Publishing all 9 counts violates no rule, but consider whether the sex-split belongs in tidy form (a `sex` categorical: `male`/`female`/`all`) vs wide columns — the totals row (`officer_ct` etc.) is the `all` bucket and must remain mutually exclusive with the sex splits if tidied.
- **County mapping is non-trivial**: `county_name` is UPPERCASE, comma-joins multi-county agencies (42 combos, 1,176 rows), and has `NOT SPECIFIED` (116 rows — GBI/State Patrol HQ, Ports Authority, one city). Do **not** naively map `county_name` → FIPS. Prefer `data/bronze/_crosswalks/ori_to_county/` as the primary ORI→county signal, keeping `county_name` as a secondary/validation signal. Multi-county agencies need an allocation policy (or county rollups exclude them with documentation).
- **Grain is clean**: `ori × data_year` unique (0 duplicates GA). Natural key for the fact table.
- **Sparse early years**: 1960s cover only ~45–76 agencies. Consider documenting a coverage caveat (or a floor year for served data) so per-county aggregates aren't mistaken for real time trends.
- **Bronze filename changes each release** (`lee_1960_{latest}.csv`) — refresh logic must glob, not hardcode.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| data_year | fact_key | year | Calendar year Int |
| ori | fact_key | ori | Natural key; FK to a (future) law-enforcement-agencies dimension |
| pub_agency_name | dimension_attribute | — | agency_name in agencies dimension |
| pub_agency_unit | dimension_attribute | — | agency_unit in agencies dimension (`"NULL"` → null) |
| state_abbr | not_in_gold | — | Constant `GA` after filter |
| division_name | not_in_gold | — | Constant |
| region_name | not_in_gold | — | Constant |
| county_name | dimension_attribute | — | Secondary county signal; resolve to `county_fips` via ori_to_county crosswalk in the agencies dimension, not the fact |
| agency_type_name | dimension_attribute | — | agency_type in agencies dimension (could be fact_categorical if no agencies dimension is built) |
| population_group_desc | dimension_attribute | — | UCR size bucket; descriptive, year-varying — consider fact_categorical if wanted for filtering |
| population | fact_metric | population | count, ≥0; service population (0 = non-territorial) |
| male_officer_ct | fact_metric | male_officer_count | count; or tidy to `sex` categorical |
| male_cilvilian_ct | fact_metric | male_civilian_count | count; **fix typo** |
| male_total_ct | fact_metric | male_total_count | count; redundant with officer+civilian — consider dropping |
| female_officer_ct | fact_metric | female_officer_count | count |
| female_cilvilian_ct | fact_metric | female_civilian_count | count; **fix typo** |
| female_total_ct | fact_metric | female_total_count | count; redundant — consider dropping |
| officer_ct | fact_metric | officer_count | count; likely **key_metric** candidate (or a derived officers-per-1,000 rate) |
| civilian_ct | fact_metric | civilian_count | count |
| total_pe_ct | fact_metric | total_employee_count | count |
| pe_ct_per_1000 | fact_metric | employees_per_1000 | ratio; **recompute** from total/population, null when population = 0 |
