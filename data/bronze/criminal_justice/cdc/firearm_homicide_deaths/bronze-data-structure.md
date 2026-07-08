# firearm_homicide_deaths — Bronze Data Structure

## Overview

- Topic: firearm_homicide_deaths
- Source: cdc (CDC WONDER, Multiple Cause of Death)
- Files: 8 files — 4 measures × 2 dataset vintages, spanning 1999–2024
- Unreadable files: none
- Year representation: `Year` / `Year Code` columns (4-digit calendar year). Calendar year of death, not school year.
- Filename-to-data year offset: filename carries the year *range* (e.g., `_1999_2020`), which matches the data years exactly
- Detail levels: county only (all 159 GA counties, decedent's county of **residence**). No state-total rows — WONDER omitted totals due to suppression constraints ("Totals are not available for these results").
- Percentage scale: no percentages. Rates are **per 100,000 population** (crude and age-adjusted).
- Checksums generated: 2026-07-02

## Source Provenance

- **Source URL**: <https://wonder.cdc.gov/mcd.html> — D77 (MCD 1999–2020, bridged race) via <https://wonder.cdc.gov/mcd-icd10.html>; D157 (MCD 2018–2024, single race) via <https://wonder.cdc.gov/mcd-icd10-expanded.html>
- **Retrieved**: 2026-07-02 (see `_provenance.md`)
- **Method**: scripted web-app form POST via `src/etl/criminal_justice/cdc/download.py` (the official WONDER XML API blocks county-level grouping). Grouped by County × Year, filtered to Georgia (FIPS 13), show-suppressed + show-zeros on, TSV export.

## File Checksums

Generated: 2026-07-02

| File | SHA-256 |
|------|---------|
| firearm_deaths_by_county_year_1999_2020.txt | 69f02f28a426ed1d69e83adcb0ae4decad0368c0874da6d098af4ff088e5d72d |
| firearm_deaths_by_county_year_2018_2024.txt | 30988e4f8e59e552c3ce78503e690c27ab31075931ec1474cbd5303d7a318a6b |
| firearm_homicide_by_county_year_1999_2020.txt | 70b31b19126af2a5b5b890ad3ade16e32ba3dc394c62029e38974dadacf62c3b |
| firearm_homicide_by_county_year_2018_2024.txt | 72a61635ea26c1f338637e159b416404a56b4f3a31e83da4c4fbcc1ad4046709 |
| homicide_by_county_year_1999_2020.txt | 76d2f1d1771c069f62006534bda5f29c262faf250b14afd5d0eaf336cd84c9ea |
| homicide_by_county_year_2018_2024.txt | 5a37aa80175c00cb36cd2562b453349072a16f2f73d5b51f0bf76b3ebb5b68b2 |
| legal_intervention_by_county_year_1999_2020.txt | 7227e81fa8c5a7bbe53a1983d7c762f8ba9229be914e1ccf01d3db169a59427d |
| legal_intervention_by_county_year_2018_2024.txt | 0f9978f0d17d2be03ab5f14771d7798d33cbc3e4e27ded0dc46ade9f11673be1 |

## Summary

County × year death counts and rates for four violent-death measures from NCHS/NVSS
death certificates (CDC WONDER Multiple Cause of Death):

| Measure (from filename) | Underlying-cause definition (verified from each file's Query Parameters footer) |
|--------------------------|--------------------------------------------------------------------------------|
| `firearm_deaths` | UCD Injury Mechanism = Firearm (all intents: homicide + suicide + unintentional + legal + undetermined) |
| `homicide` | UCD Injury Intent = Homicide (all mechanisms) |
| `firearm_homicide` | UCD Injury Intent = Homicide **and** Mechanism = Firearm |
| `legal_intervention` | UCD Injury Intent = Legal Intervention / Operations of War (all mechanisms) |

Metrics per row: `Deaths` (count), `Population` (denominator), `Crude Rate` (per
100,000), and either `Age Adjusted Rate` (D77 era; 2000 US std population) or crude-rate
95% CI bounds (D157 era). The **measure is encoded in the filename only** — the transform
must add a measure/cause categorical (or pivot wide) when concatenating files.

## Eras

Era = dataset vintage (column sets differ), not a plain year split. Within each era all
4 measure files have identical columns. The eras **overlap 2018–2020**.

### Era 1: D157 — 2018–2024 (Single Race vintage), 4 files

1,113 data rows per file = 159 counties × 7 years. Each file also has ~61 footer rows
(see ETL Considerations).

| Column | Description |
|--------|-------------|
| Notes | Always null on data rows; non-null only on footer rows (use as a data/footer discriminator) |
| County | County name, e.g. `Fulton County, GA` |
| County Code | 5-digit county FIPS as quoted string, zero-padded (e.g. `13001`) |
| Year | Calendar year of death (string). **`2024 ` carries a trailing space** in all 4 files; `Year Code` does not |
| Year Code | Calendar year, clean 4-digit string |
| Deaths | Death count (string; `Suppressed` when count is 1–9) |
| Population | County resident population (always numeric, never suppressed) |
| Crude Rate | Deaths per 100,000 (string; `Suppressed` mirrors Deaths; `0.0` for zero-death rows) |
| Crude Rate Lower 95% Confidence Interval | Lower bound of crude rate 95% CI |
| Crude Rate Upper 95% Confidence Interval | Upper bound of crude rate 95% CI |

#### Sample Data (firearm_deaths, seed=1)

```text
┌───────┬────────────────────┬─────────────┬───────┬───────────┬────────────┬────────────┬────────────┬─────────────┬─────────────┐
│ Notes ┆ County             ┆ County Code ┆ Year  ┆ Year Code ┆ Deaths     ┆ Population ┆ Crude Rate ┆ CR Lower CI ┆ CR Upper CI │
╞═══════╪════════════════════╪═════════════╪═══════╪═══════════╪════════════╪════════════╪════════════╪═════════════╪═════════════╡
│ null  ┆ Sumter County, GA  ┆ 13261       ┆ 2022  ┆ 2022      ┆ Suppressed ┆ 28877      ┆ Suppressed ┆ Suppressed  ┆ Suppressed  │
│ null  ┆ Worth County, GA   ┆ 13321       ┆ 2023  ┆ 2023      ┆ Suppressed ┆ 20273      ┆ Suppressed ┆ Suppressed  ┆ Suppressed  │
│ null  ┆ Bulloch County, GA ┆ 13031       ┆ 2024  ┆ 2024      ┆ 15         ┆ 85454      ┆ 17.6       ┆ 9.8         ┆ 29.0        │
│ null  ┆ Rabun County, GA   ┆ 13241       ┆ 2021  ┆ 2021      ┆ Suppressed ┆ 17119      ┆ Suppressed ┆ Suppressed  ┆ Suppressed  │
│ null  ┆ Clay County, GA    ┆ 13061       ┆ 2020  ┆ 2020      ┆ Suppressed ┆ 2866       ┆ Suppressed ┆ Suppressed  ┆ Suppressed  │
└───────┴────────────────────┴─────────────┴───────┴───────────┴────────────┴────────────┴────────────┴─────────────┴─────────────┘
```

#### Statistics (firearm_deaths, after `strict=False` cast to Float64, data rows only)

```text
┌────────────┬───────────┬───────────────┬────────────┬─────────────┬─────────────┐
│ statistic  ┆ Deaths    ┆ Population    ┆ Crude Rate ┆ CR Lower CI ┆ CR Upper CI │
╞════════════╪═══════════╪═══════════════╪════════════╪═════════════╪═════════════╡
│ count      ┆ 415.0     ┆ 1113.0        ┆ 415.0      ┆ 415.0       ┆ 415.0       │
│ null_count ┆ 698.0     ┆ 0.0           ┆ 698.0      ┆ 698.0       ┆ 698.0       │
│ mean       ┆ 26.55     ┆ 68076.8       ┆ 15.85      ┆ 9.83        ┆ 24.51       │
│ min        ┆ 0.0       ┆ 1537.0        ┆ 0.0        ┆ 0.0         ┆ 0.0         │
│ max        ┆ 258.0     ┆ 1090354.0     ┆ 65.3       ┆ 36.1        ┆ 120.1       │
└────────────┴───────────┴───────────────┴────────────┴─────────────┴─────────────┘
```

#### Null Counts

Zero nulls in every column on data rows (all masking is via marker strings, not blanks).
`Notes` is 100% null on data rows.

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| County | 159 values — every GA county, format `<Name> County, GA` |
| County Code | 159 values — `13001` … `13321` (odd-numbered FIPS) |
| Year / Year Code | `2018`–`2024` (Year has `2024 ` with trailing space) |

#### Suppression Markers (exact counts per file, era D157)

| File | Deaths `Suppressed` | Rate cols `Suppressed` | `Unreliable` |
|------|--------------------:|-----------------------:|-------------:|
| firearm_deaths_2018_2024 | 698 / 1113 | 698 in each of 3 rate cols | 0 |
| homicide_2018_2024 | 699 / 1113 | 699 | 0 |
| firearm_homicide_2018_2024 | 653 / 1113 | 653 | 0 |
| legal_intervention_2018_2024 | 158 / 1113 | 158 | 0 |

No `Unreliable` markers in this era — small-count rates are published with wide CIs
instead. Zero-death rows show `0.0` rates.

### Era 2: D77 — 1999–2020 (bridged-race vintage), 4 files

3,498 data rows per file = 159 counties × 22 years. Columns identical to Era 1 **except**:
no CI columns; instead a single `Age Adjusted Rate` column (per 100,000, 2000 US standard
population).

| Column | Description |
|--------|-------------|
| Notes, County, County Code, Year, Year Code, Deaths, Population, Crude Rate | Same as Era 1 (no trailing-space year values in this era) |
| Age Adjusted Rate | Age-adjusted deaths per 100,000 (string; `Suppressed` / `Unreliable` markers) |

#### Sample Data (firearm_deaths, seed=1)

```text
┌───────┬────────────────────┬─────────────┬──────┬───────────┬────────────┬────────────┬────────────┬───────────────────┐
│ Notes ┆ County             ┆ County Code ┆ Year ┆ Year Code ┆ Deaths     ┆ Population ┆ Crude Rate ┆ Age Adjusted Rate │
╞═══════╪════════════════════╪═════════════╪══════╪═══════════╪════════════╪════════════╪════════════╪═══════════════════╡
│ null  ┆ Sumter County, GA  ┆ 13261       ┆ 2018 ┆ 2018      ┆ Suppressed ┆ 29733      ┆ Suppressed ┆ Suppressed        │
│ null  ┆ Rabun County, GA   ┆ 13241       ┆ 2014 ┆ 2014      ┆ Suppressed ┆ 16243      ┆ Suppressed ┆ Suppressed        │
│ null  ┆ Bulloch County, GA ┆ 13031       ┆ 2019 ┆ 2019      ┆ Suppressed ┆ 79608      ┆ Suppressed ┆ Suppressed        │
│ null  ┆ Rabun County, GA   ┆ 13241       ┆ 2012 ┆ 2012      ┆ Suppressed ┆ 16297      ┆ Suppressed ┆ Suppressed        │
│ null  ┆ Clay County, GA    ┆ 13061       ┆ 2007 ┆ 2007      ┆ 0          ┆ 3262       ┆ Unreliable ┆ Unreliable        │
└───────┴────────────────────┴─────────────┴──────┴───────────┴────────────┴────────────┴────────────┴───────────────────┘
```

#### Statistics (firearm_deaths, after `strict=False` cast, data rows only)

```text
┌────────────┬───────────┬───────────────┬────────────┬───────────────────┐
│ statistic  ┆ Deaths    ┆ Population    ┆ Crude Rate ┆ Age Adjusted Rate │
╞════════════╪═══════════╪═══════════════╪════════════╪═══════════════════╡
│ count      ┆ 1114.0    ┆ 3498.0        ┆ 274.0      ┆ 274.0             │
│ null_count ┆ 2384.0    ┆ 0.0           ┆ 3224.0     ┆ 3224.0            │
│ mean       ┆ 18.36     ┆ 59857.4       ┆ 15.94      ┆ 15.84             │
│ min        ┆ 0.0       ┆ 1537.0        ┆ 6.2        ┆ 6.9               │
│ max        ┆ 231.0     ┆ 1077402.0     ┆ 38.6       ┆ 38.2              │
└────────────┴───────────┴───────────────┴────────────┴───────────────────┘
```

#### Null Counts

Zero nulls in every column on data rows; `Notes` 100% null on data rows (same as Era 1).

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| County | 159 values, same set/format as Era 1 |
| County Code | 159 values, `13001` … `13321` |
| Year / Year Code | `1999`–`2020`, clean 4-digit strings |

#### Suppression Markers (exact counts per file, era D77)

| File | Deaths `Suppressed` | Crude Rate S / U | Age Adjusted Rate S / U |
|------|--------------------:|-----------------:|------------------------:|
| firearm_deaths_1999_2020 | 2384 / 3498 | 2384 / 840 | 2384 / 840 |
| homicide_1999_2020 | 2168 / 3498 | 2168 / 1153 | 2168 / 1153 |
| firearm_homicide_1999_2020 | 1824 / 3498 | 1824 / 1538 | 1824 / 1538 |
| legal_intervention_1999_2020 | 270 / 3498 | 270 / 3228 | 270 / 3228 |

In this era rates from **< 20 deaths** are `Unreliable` (including all zero-death rows —
unlike Era 1, a 0-death row shows `Unreliable`, not `0.0`). For legal_intervention,
Suppressed + Unreliable = 3,498 → **not a single numeric rate exists in the entire D77
legal-intervention file**; only the Deaths counts (3,228 numeric, mostly 0) are usable.

## ETL Considerations

- **WONDER TSV layout**: tab-delimited, quoted strings, a header row, N data rows, then a
  `"---"` line followed by ~60 footer rows (Dataset, Query Parameters, Messages, Caveats).
  Robust parse: read with `separator='\t'`, `infer_schema_length=0` (all Utf8), then keep
  rows where `County Code` is not null (footer rows have all-null non-Notes columns).
  Do **not** parse by line count.
- **Measure is filename-encoded only.** Nothing inside a file identifies the measure
  (except the footer Query Parameters). The transform must attach the measure name
  (`firearm_deaths` / `homicide` / `firearm_homicide` / `legal_intervention`) from the
  filename when reading.
- **Era overlap 2018–2020 verified byte-identical.** For all 4 measures, every 2018–2020
  county-year has identical `Deaths` (including `Suppressed` markers) and `Population`
  across D77 and D157. Recommended stitch: D77 for 1999–2017, D157 for 2018–2024 (no
  discontinuity; keeps CI columns for recent years). Whatever the choice, dedupe the
  overlap — naive concat doubles 2018–2020.
- **Rate-column schema differs by era**: D77 has `Age Adjusted Rate` (no CIs); D157 has
  crude-rate 95% CI bounds (no age-adjusted rate — WONDER forbids AAR at county grain
  for D157). If gold keeps age-adjusted rate, it will be NULL for 2021–2024; if gold
  keeps CI columns, they'll be NULL for 1999–2017.
- **Suppression / reliability markers** (keep semantics straight):
  - `Suppressed` — death count 1–9 (privacy). NULL it — **never substitute 0**; real
    zeros are published as `0`.
  - `Unreliable` (D77 rates only) — rate computed from < 20 deaths. The Deaths count on
    such rows is still valid; only the rate is masked. NULL the rate, keep the count.
  - D157 has no `Unreliable`; zero-death rows carry `0.0` rates there, while D77
    zero-death rows carry `Unreliable` rates. A crude-rate column stitched across eras
    therefore has era-dependent null patterns for small counties.
  - `strict=False` Float64 cast converts both markers to null; log the per-column counts
    (expected totals are in the marker tables above).
- **Suppression volume is high**: 61–68% of county-year Deaths are suppressed for the
  three homicide/firearm measures in both eras. This is expected for county-grain rare
  events, but the gold data will be sparse for small counties; only ~30–40% of
  county-years have numeric counts (legal_intervention is the exception: ~95% numeric,
  because most values are 0).
- **`Year` = `'2024 '` trailing space** in all four D157 files (the `Year Code` column is
  clean). Use `Year Code`, or strip whitespace before casting. A strict cast on `Year`
  without stripping silently nulls all 159 rows of 2024.
- **County FIPS are quoted, zero-padded 5-char strings** (`13001`) — already in the
  project's canonical county FIPS format; keep as string, do not cast to int.
- **No state-total rows** despite show-totals being on ("Totals are not available for
  these results due to suppression constraints"). A state rollup cannot be recomputed
  from county rows either, because suppressed counts are missing — don't sum counties
  and present it as a state total.
- **Population is never suppressed** and identical across measure files for the same
  county-year — a useful cross-file consistency check in the transform.
- **Residence, not occurrence**: deaths are attributed to the decedent's county of
  residence.
- **No demographic columns** — no race/sex/age breakdowns were requested, so no
  Asian/Pacific Islander bucket concern applies. Grain is purely county × year × measure.
- **2024 caveat** (from file footers): 2024 populations are Vintage 2024 postcensal
  estimates; footers also carry an NC drug-overdose data-correction caveat that does not
  affect Georgia rows.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| County Code | fact_key | county_fips | FK to counties dimension; keep as 5-char string |
| Year Code | fact_key | year | Cast to int; prefer over `Year` (trailing-space issue) |
| *(filename)* | fact_categorical | measure (or cause) | `firearm_deaths` / `homicide` / `firearm_homicide` / `legal_intervention` — alternatively pivot to wide metric columns |
| Deaths | fact_metric | deaths | count; `Suppressed` → NULL (never 0) |
| Population | fact_metric | population | count (denominator); never suppressed |
| Crude Rate | fact_metric | crude_rate_per_100k | ratio, per 100,000; `Suppressed`/`Unreliable` → NULL. Candidate key metric — but consider deriving vs. keeping published value |
| Age Adjusted Rate | fact_metric | age_adjusted_rate_per_100k | D77 era only (1999–2017 after stitch); NULL for 2021–2024 |
| Crude Rate Lower 95% Confidence Interval | fact_metric | crude_rate_ci_lower | D157 era only; NULL pre-2018 |
| Crude Rate Upper 95% Confidence Interval | fact_metric | crude_rate_ci_upper | D157 era only; NULL pre-2018 |
| County | dimension_attribute | — | county_name lives in the counties dimension |
| Notes | not_in_gold | — | Null on all data rows; footer discriminator only |
| Year | not_in_gold | — | Duplicate of Year Code, with the `'2024 '` trailing-space defect |
