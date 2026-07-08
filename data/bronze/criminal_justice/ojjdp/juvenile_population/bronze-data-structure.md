# juvenile_population — Bronze Data Structure

## Overview

- Topic: juvenile_population
- Source: ojjdp (OJJDP Statistical Briefing Book — *Easy Access to Juvenile Populations*, EZAPOP; NCJJ from Census Bureau / NCHS bridged-race county population estimates)
- Files: 28 CSV files, each covering **1990–2024** (one file per population slice, not per year)
- Unreadable files: none
- Year representation: years are **columns** (`"1990"` … `"2024"`) in a wide county × year matrix; no year in the filename
- Filename-to-data year offset: n/a — filenames encode the population slice (age/sex/race/ethnicity), not a year
- Detail levels: county (159 GA counties) + a statewide `All Counties` row per file
- Percentage scale: n/a — every value column is a raw population **count** (integer)
- Checksums generated: 2026-07-02

## Source Provenance

Full detail in `_provenance.md` (kept alongside the bronze files).

- **Source URL**: <https://www.ojjdp.gov/ojstatbb/ezapop> — export endpoint
  `https://www.ojjdp.gov/ojstatbb/ezapop/asp/comparison_display.asp` with `export_file=yes`,
  `selState=13` (Georgia), `col_var=v01` (years in columns)
- **Retrieved**: 2026-07-02T12:33Z (UTC)
- **Method**: scripted fetch — `uv run python -m src.etl.criminal_justice.ojjdp.download`
  (re-runnable; never overwrites unless `--refresh`)
- **Archival note**: the Statistical Briefing Book's federal funding is at risk; these files
  are the archival snapshot from first ingest. Do not delete even if the tool goes away.
- **Citation (verbatim in each file's footer)**: Puzzanchera, C., Sladky, A. and Kang, W. (2026).
  *Easy Access to Juvenile Populations: 1990–2024.*

## File Checksums

Generated: 2026-07-02

| File | SHA-256 |
|------|---------|
| ezapop_ga_county_year_age_00.csv | 53174f649ec13b999dc2122c82dc0dba9573afdea8cf2bf6b7f92108d4121231 |
| ezapop_ga_county_year_age_01.csv | a64083e0cf013943ad62db7b623bc8a4ae8bd3478a35b910045f3a784ce254ab |
| ezapop_ga_county_year_age_02.csv | f5da9e2ac423431d082e6d4b233a22d1fc093bd79e7a8b276bbb20e9d362a040 |
| ezapop_ga_county_year_age_03.csv | 1ced85101949323668c5f6b73b86cc76998c41df08d77c400da5b6171812cc68 |
| ezapop_ga_county_year_age_04.csv | dd529de40206f92d626377ad00b2348340d376e6e50e17879fbdc476705796b8 |
| ezapop_ga_county_year_age_05.csv | f889c68433e26dcbdf9d970278191e17560a249cdacfb5ab39582fc59e22ad52 |
| ezapop_ga_county_year_age_06.csv | 9a96748eb3a65f848386d0761b965d370fa95a93545c1507022e8bf3701d3a95 |
| ezapop_ga_county_year_age_07.csv | 178c6022385d892fd916e8a44015da204eb14580eb69c506b5e384fc2d821cab |
| ezapop_ga_county_year_age_08.csv | 57867d2d79382ed061ea71cc00856af6237dc56cfc1f4674cab8f6813142489b |
| ezapop_ga_county_year_age_09.csv | 8370b7cd0df2f872fd26cc191c1a5656779561609967be72cddf8d9791852b3a |
| ezapop_ga_county_year_age_10.csv | e4e2583a5280fd8837604c51535eba57daf23b9eac91937912f45dd9d7fa5caa |
| ezapop_ga_county_year_age_11.csv | d53907a1ff12cba49a9f11c0345afc9710f81717b6dc100bad41cee43ed0cbf6 |
| ezapop_ga_county_year_age_12.csv | d9d249763bdd3ca44d8fcf0162c2c50c3b4682d8cb6d901617871e4d34d8567e |
| ezapop_ga_county_year_age_13.csv | d7487c925ebc63a20259442e9b462791e17e63b49c4ee5cccf943a09bdf4d137 |
| ezapop_ga_county_year_age_14.csv | ee6c215b41f3ae435fd9be52899894e641e242acb0cf17876e191fbe96372b0d |
| ezapop_ga_county_year_age_15.csv | 3856d893828608ce5d9629ade542b887229158857cae23e1504e20ee32f321bd |
| ezapop_ga_county_year_age_16.csv | 4d8311d9a3045f30b6275e3c1221833105384ff1de38ee872d816ac30c4f868e |
| ezapop_ga_county_year_age_17.csv | 81f3774bae360e2f3cabc680e8bf7cd147af1c5980f80d48d325f6c25b16b55e |
| ezapop_ga_county_year_all_ages.csv | 3d073064745e638273438cc1f64266f6a5f833860cce62bac05adf6df3dd23fa |
| ezapop_ga_county_year_juveniles_age00_17.csv | a31a2e58e6dd6356304517e01f35817ad689f36b01a3115240b61a7d88ac50f2 |
| ezapop_ga_county_year_juveniles_ethnicity_hispanic.csv | 6ac7f22767c541788aefd6977ea8e01513d75a7934ac24dcb90e541f51ae538d |
| ezapop_ga_county_year_juveniles_ethnicity_non_hispanic.csv | a04d3230233b63a6676443ea4568d6fba7729142a7934f5d4bee68c6dd514399 |
| ezapop_ga_county_year_juveniles_race_american_indian.csv | 8395695260d7bca33e48d2c24f1ea9802c30cad495f051b8403109cfddcc08fc |
| ezapop_ga_county_year_juveniles_race_asian.csv | 0a8266cf647b6b8fdadbbcc0557da12e2ea1402d4ca6b7a9de8f59a099f9751e |
| ezapop_ga_county_year_juveniles_race_black.csv | dc0d190c17450d12b40be30152d441186b60ea2ba84fec616193a970a94ee3dd |
| ezapop_ga_county_year_juveniles_race_white.csv | f8f4afd6ac0bc6211b2b13b4a932fd881a7acc61bcadb2f3038d692deabc2f62 |
| ezapop_ga_county_year_juveniles_sex_female.csv | 7ca63038ddfade3b28b42eefd88cbcd5d42a89ac53407dcfeec45d24c5aba082 |
| ezapop_ga_county_year_juveniles_sex_male.csv | 61186d3e08593b29ec0f024318156a64d70f1cf8eac5e7d8c45f1f06f4b7ca3e |

(`_provenance.md` is documentation, not data — excluded from checksums.)

## Summary

County-level **juvenile population denominators** for Georgia, 1990–2024 — the base counts
needed to turn the other `criminal_justice` topics' raw counts into rates. The 28 files are
one-way marginal slices of the same underlying estimate set:

- `juveniles_age00_17` — **headline denominator**: juveniles (ages 0–17) per county per year
- `all_ages` — total resident population (all ages, adults included), context only
- `sex_{male,female}` — juveniles 0–17 by sex
- `race_{white,black,american_indian,asian}` — juveniles 0–17 by bridged race
  (**"Asian" includes Pacific Islander**; race buckets include both ethnicities)
- `ethnicity_{hispanic,non_hispanic}` — juveniles 0–17 by ethnicity (any race)
- `age_{00..17}` — single year of age, so **any age band can be rebuilt** (e.g., ages 10–16
  for the GA delinquency-jurisdiction denominator matching EZACO's `popten`; GA upper age = 16)

Census estimates — full coverage of all 159 counties, every year, **no suppression, no nulls**.

## File Layout (CSV preamble/footer)

Every file has the same shape; only the `Selecting:` preamble length varies:

| Section | Content |
|---------|---------|
| Lines 1–2 | Title (`"Easy Access to Juvenile Populations: County Comparisons"`) + table description |
| `Selecting:` block | 1–3 quoted filter lines (`Year = …`, then `Age = …` / `Sex = …` / `Race = …` / `Ethnicity = …` as applicable) — the file's slice, verbatim from the export |
| Header row | `counts, 1990, …, 2024, Total` — at line 7 (`all_ages`), 8 (`age_*`, `juveniles_age00_17`), or 9 (sex/race/ethnicity files), 1-based |
| Data | 160 rows: `All Counties` + 159 county rows (alphabetical) |
| Footer | blank line + 3-line suggested-citation block |

Every data row has a **trailing comma** (parses as a 38th empty column). The transform must
locate the header row dynamically (first row whose first cell is `counts`) rather than
hard-coding a skip count.

## Eras

### Era 1: 1990–2024 (single era — all 28 files share identical layout)

Files differ only in which population slice they contain (encoded in the filename and the
`Selecting:` preamble), never in column names.

| Column | Description |
|--------|-------------|
| counts | County name (`"Appling County"` … `"Worth County"`) or `"All Counties"` (statewide) |
| 1990 … 2024 | Population count (integer) for that calendar year — 35 year columns |
| Total | Row sum across all 35 years (derived; verified exact) |
| *(trailing empty)* | Artifact of the trailing comma on every row — drop |

Representative file: `ezapop_ga_county_year_juveniles_age00_17.csv`.

#### Sample Data

```text
┌─────────────────┬───────┬───────┬───────┬───────┬───────┬────────┐
│ counts          ┆ 1990  ┆ 2000  ┆ 2010  ┆ 2020  ┆ 2024  ┆ Total  │
╞═════════════════╪═══════╪═══════╪═══════╪═══════╪═══════╪════════╡
│ Spalding County ┆ 15510 ┆ 15926 ┆ 16165 ┆ 16156 ┆ 16130 ┆ 558070 │
│ Putnam County   ┆ 3693  ┆ 4362  ┆ 4580  ┆ 4413  ┆ 4387  ┆ 151808 │
│ Bryan County    ┆ 5088  ┆ 7294  ┆ 8874  ┆ 13366 ┆ 14526 ┆ 312951 │
│ Quitman County  ┆ 572   ┆ 621   ┆ 517   ┆ 408   ┆ 436   ┆ 18607  │
│ Clarke County   ┆ 17718 ┆ 18329 ┆ 20460 ┆ 22180 ┆ 21155 ┆ 694898 │
└─────────────────┴───────┴───────┴───────┴───────┴───────┴────────┘
```

(Year columns 1991–2023 omitted for width; all 35 are present in every file.)

#### Statistics (headline file, selected year columns; 160 rows incl. `All Counties`)

```text
┌────────────┬───────────────┬───────────────┬───────────────┬─────────────┐
│ statistic  ┆ 1990          ┆ 2007          ┆ 2024          ┆ Total       │
╞════════════╪═══════════════╪═══════════════╪═══════════════╪═════════════╡
│ count      ┆ 160.0         ┆ 160.0         ┆ 160.0         ┆ 160.0       │
│ null_count ┆ 0.0           ┆ 0.0           ┆ 0.0           ┆ 0.0         │
│ mean       ┆ 21842.0375    ┆ 30703.1125    ┆ 31759.3875    ┆ 1.0050e6    │
│ std        ┆ 138891.94     ┆ 195613.97     ┆ 202507.60     ┆ 6.4032e6    │
│ min        ┆ 536.0         ┆ 367.0         ┆ 298.0         ┆ 13546.0     │
│ 25%        ┆ 2679.0        ┆ 3029.0        ┆ 2251.0        ┆ 97515.0     │
│ 50%        ┆ 4686.0        ┆ 5574.0        ┆ 5526.0        ┆ 187968.0    │
│ 75%        ┆ 9961.0        ┆ 13637.0       ┆ 14314.0       ┆ 458221.0    │
│ max        ┆ 1.747363e6    ┆ 2.456249e6    ┆ 2.540751e6    ┆ 8.0401519e7 │
└────────────┴───────────────┴───────────────┴───────────────┴─────────────┘
```

The large max/std come from the `All Counties` statewide row (e.g., 2,540,751 GA juveniles
in 2024); county-only max is Gwinnett/Fulton scale (~250k).

#### Null Counts

Zero nulls in every column of every file (verified across all 28 files).

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| counts | 160 values: `All Counties` + 159 county names (`Appling County` … `Worth County`), identical set in every file |

#### Suppression Markers

**None.** Every value in every year/`Total` column across all 28 files casts cleanly to an
integer — no `*`, `N/A`, or other markers. Census estimates have no suppression.

#### Verified internal consistency (exact, max abs diff = 0 across all 160 rows × 35 years)

- `male + female` = juveniles 0–17 total
- `hispanic + non_hispanic` = juveniles 0–17 total
- `white + black + american_indian + asian` = juveniles 0–17 total
- `sum(age_00 … age_17)` = juveniles 0–17 total
- `All Counties` row = sum of the 159 county rows (every file)
- `Total` column = horizontal sum of the 35 year columns (every file)

## Asian / Pacific Islander check

Bronze has only **4 bridged-race buckets** (White, Black, American Indian, Asian) — no
separate Pacific Islander bucket. The math test confirms the combined bucket: the 4 race
buckets sum **exactly** to the juveniles total at every county × year, so "Asian" here is
the pre-1997-OMB **combined Asian + Pacific Islander** bucket. The transform must map it to
`asian_pacific_islander`, **not** `asian`. There is no combined-plus-split double publication
risk (no separate PI or API rows exist).

Note there is also **no Multiracial bucket** — bridged-race estimates allocate multiracial
persons into the 4 single-race buckets, which is why they sum exactly to the total.

## ETL Considerations

- **Wide → long unpivot.** Each file is a county × year matrix; unpivot the 35 year columns
  to a `year` column. The measured value dimension (age slice / sex / race / ethnicity /
  total) comes from the **filename**, not any in-file column — build it from a
  filename→slice mapping in the transform.
- **Dynamic header detection.** The `Selecting:` preamble is 1–3 lines depending on the
  filters applied, so the header row lands at 1-based line 7, 8, or 9. Find the row whose
  first cell is `counts`; don't hard-code `skip_rows`. Also stop before the blank line +
  3-line citation footer, and drop the empty 38th column created by the trailing comma on
  every row.
- **`Total` column and `All Counties` row.** `Total` is a row sum across 35 years — exclude
  from gold. `All Counties` is the statewide aggregate; keep it as a state-level row with
  `county_fips` NULL (matches the `decision_points` convention), or derive it — it equals the
  county sum exactly either way.
- **County name → FIPS.** No FIPS codes in bronze — join county names (strip the
  `" County"` suffix) to the counties dimension (`data/gold/_dimensions/counties.parquet`).
  **One known mismatch: bronze `De Kalb` vs dimension `DeKalb`** — needs a name override.
  All other 158 names match the dimension exactly.
- **Bridged race ≠ education race conventions.** EZAPOP race buckets **include Hispanic
  persons of both ethnicities** (bridged race), and ethnicity is a separate marginal. So
  `hispanic` (any race) **overlaps** the four race buckets — publishing `hispanic` alongside
  `white`/`black`/`native_american`/`asian_pacific_islander` under the shared `race`
  demographic category violates mutual exclusivity (data-cleaning-standards §5). This
  differs from `decision_points`, where DJJ's race/ethnicity buckets are mutually exclusive.
  **Recommendation:** publish sex + bridged-race marginals via the `demographic` FK, and
  handle ethnicity as a design decision at transform time — either (a) add an `ethnicity`
  demographic category (`hispanic`/`non_hispanic` pair) to the demographics dimension so the
  overlap is structural, not within-category, or (b) omit the two ethnicity files from gold.
  Option (a) is preferred because Hispanic rate denominators are needed against
  `decision_points` (which publishes `hispanic` rows); document that EZAPOP race and
  ethnicity are different classification systems.
- **Single-year-of-age files** (`age_00 … age_17`) have no counterpart in the demographics
  dimension (no `age` category). Model age as a **fact categorical** (e.g., `age` = `0`–`17`
  plus an all-juveniles level), not a demographic — this preserves the ability to build any
  age band (notably ages 10–16 for the GA delinquency-jurisdiction denominator matching
  EZACO's `popten`).
- **Marginals, not cross-tabs.** Sex/race/ethnicity/age slices are one-way marginals (each ×
  county × year). The grain must prevent double counting: a demographic marginal row is for
  ages 0–17 as a whole, and an age row is for all demographics — never both at once.
- **`all_ages` file includes adults** — it is total resident population, context only. If
  kept, it must not be confusable with the juvenile counts (separate metric or explicit age
  level, e.g., `age = all_ages` vs `age = 0_17`).
- **No suppression, no nulls, full coverage** — all 159 counties × 35 years in every file.
  Any null after transform indicates a parsing bug, not source suppression.
- **Estimates are revised.** The tool serves the current vintage only (1990–2024, published
  2026); re-downloading may change historical values. Checksums above pin the archival
  snapshot.

## Gold Schema Classification

Bronze "columns" here means the post-unpivot logical columns (the wide year columns become
`year`; the filename-encoded slice becomes categorical/demographic columns).

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| counts (county name) | fact_key | county_fips | Map name → 5-digit FIPS via counties dimension; `All Counties` → NULL (statewide); `De Kalb` → `DeKalb` override |
| counts (county name) | dimension_attribute | — | county_name lives in the counties dimension |
| 1990 … 2024 (column names) | fact_key | year | Unpivot to a calendar-year column (Int, 1990–2024) |
| *(filename: sex/race/ethnicity slice)* | fact_key | demographic | FK to demographics dimension: `all`, `male`, `female`, `white`, `black`, `native_american` (from American Indian), `asian_pacific_islander` (from Asian — combined bucket, see A/PI check), `hispanic`/`non_hispanic` (pending ethnicity-category decision) |
| *(filename: age slice)* | fact_categorical | age | `0` … `17` single year of age + an all-juveniles level (e.g., `0_17`); `all_ages` level only if the total-population file is kept |
| cell values | fact_metric | juvenile_population (working name) | Integer count, ≥ 0; unit `count`; the topic's key metric |
| Total | not_in_gold | — | Row sum across years — derivable, not a served metric |
| *(trailing empty column)* | not_in_gold | — | CSV trailing-comma artifact |
| *(preamble/footer rows)* | not_in_gold | — | Title, `Selecting:` block, citation — provenance only |
