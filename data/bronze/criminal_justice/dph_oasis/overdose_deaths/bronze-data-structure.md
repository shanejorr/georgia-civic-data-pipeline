# overdose_deaths — Bronze Data Structure

## Overview

- Topic: overdose_deaths
- Source: dph_oasis (GA Dept. of Public Health, OASIS Data Table Tool — death-certificate data from the Georgia Office of Vital Records)
- Files: 30 CSV files (6 drug-cause categories × 5 layouts), all covering 1999–2024
- Unreadable files: none
- Year representation: `year` column, 4-digit calendar year (`1999`…`2024`), plus a derived `selected_years_total` row per group (drop in transform). Year of death, not publication year.
- Filename-to-data year offset: n/a — filenames carry no year; all files span all years
- Detail levels: state (Georgia) and county (159 counties, 5-digit FIPS). Demographic breakdowns (age/race/ethnicity/sex) exist **only at state level**; county files are all-demographics-combined.
- Percentage scale: no percentages. `death_rate` and `age_adjusted_death_rate` are per-100,000-population rates (unit: `ratio`), `deaths` is a count.
- Checksums generated: 2026-07-02

## Source Provenance

Full detail in `_provenance.md` (same directory), summarized here:

- **Source URL**: https://oasis.state.ga.us/dtt/mortalitydrugoverdoses (data endpoint `POST https://oasis.state.ga.us/dtt/MortalityDrugOverdoses/GetData`; county FIPS from `https://oasis.state.ga.us/dtt/data/geographies.json`)
- **Retrieved**: 2026-07-02 (12:34 UTC)
- **Method**: scripted fetch — `src/etl/criminal_justice/dph_oasis/download.py` (re-runnable; picks up new data years automatically). Verbatim request/response JSON kept in `_raw_responses/` (subdirectory — not scanned by the freshness gate, not ingested by the transform).

## File Checksums

Generated: 2026-07-02

| File | SHA-256 |
|------|---------|
| all_drug_overdoses__county_year.csv | 4d5cb85ab2fd8df92273cbdf7b5030f5c17b7cff5a4c0d438b73ed4179b2eb83 |
| all_drug_overdoses__state_age_year.csv | 7cdc2802239430afc0fe5048c75a6bcdbe758562fa6f438ee149e6535a941de6 |
| all_drug_overdoses__state_ethnicity_year.csv | 028d517ac3feb1215a30daa2cc79fcd93eba030e91c583a5875bf7f92ce906bf |
| all_drug_overdoses__state_race_year.csv | df2c018fa663d0e00029f546febc6bd9da37b36e604f9d31734088c23ed36d7b |
| all_drug_overdoses__state_sex_year.csv | 33902783cfb31eb1fd0747eb9233bb26ce82ff0dcb20f187c917a1f07aea2ab6 |
| all_opioids__county_year.csv | 1af34ee13b4f07d8104df7918823bfaad26ed211cff07771f4a06444801ff9e4 |
| all_opioids__state_age_year.csv | 14899abbdd38f3e1da7e123f9a4e392ee201986e9c123a3897848e3cc7a8322c |
| all_opioids__state_ethnicity_year.csv | 66f601aacee56b04900f72645a85d2e1adc40baee24e4f80032b122a52e5e913 |
| all_opioids__state_race_year.csv | e0ea779f77c1870a82f5f1f2786a61381858911720bc081794a3b3a106b1a58e |
| all_opioids__state_sex_year.csv | b20bd7935c0e3f1f8513e4d4e657476f73dfc0bb0e95b2e28041026f180b9121 |
| heroin__county_year.csv | a8876ec1f58a00a61034f5351690018a3408e7f5100b521477b3867fcef176db |
| heroin__state_age_year.csv | aef67748710155926a6d2d92c5c526ce66e0610a7a7fc4ec754aed0bcb9be2d4 |
| heroin__state_ethnicity_year.csv | 9cdd9066f92668342c716ed32040f8ac0b941c6354aeb7f38fc50e900045b5e0 |
| heroin__state_race_year.csv | d28c41171d4228ed36a443dcffe045c80c31751f19d01d44505a0a060b5eea58 |
| heroin__state_sex_year.csv | 171b778a4c42f93678a165df1896fc718abe0658f2a04f4776583d174f819a95 |
| methadone__county_year.csv | 24a4f32ad341118f6661db3a8d86c05079a292f2875458aebd1502b7054d4475 |
| methadone__state_age_year.csv | 01d3c6b1101b09f1f4a1be4d85bae581ffa144846d4bcd38198583a50f934020 |
| methadone__state_ethnicity_year.csv | 0f006c9b60d3a115ed5d7de30f016f5d212f20a7d0ea7eeffb7527c54974b5d3 |
| methadone__state_race_year.csv | 1f345b10a57f5439e446ec4c07819924c19ca6a04ddb07e45e125f6b804735d4 |
| methadone__state_sex_year.csv | 01ebe8c3497b4d0a69d5db8cca99d306603684b659429d1847e37e0b2c0711a9 |
| natural_semisynthetic_synthetic_opioids__county_year.csv | 92abe10827949bbfdfcc101aa60d64fc8b1faa1d7946f1838be37b51e61f7c65 |
| natural_semisynthetic_synthetic_opioids__state_age_year.csv | 8e550a815766d93a142f6db2135dbf779c35f28a5c581979e087ee82ee342068 |
| natural_semisynthetic_synthetic_opioids__state_ethnicity_year.csv | 50342841e178f30014be14a38ef781b16d3d0e1806d67fdb3cbcd1d75e0e5a19 |
| natural_semisynthetic_synthetic_opioids__state_race_year.csv | 5ccc6f1a7de5ea02461b8743ae5c9e574b06bdc4ebdca983c0e1e5cd6652ae8d |
| natural_semisynthetic_synthetic_opioids__state_sex_year.csv | e37da8231a38322c5f19207ac825984eb4b2d54da2d47864343ee51c57ccb6b8 |
| synthetic_opioids_excl_methadone__county_year.csv | 7c0329b30bc553afe3605658b73fd505488bb0ae4fc01a39aadd2dd75c3fd2d7 |
| synthetic_opioids_excl_methadone__state_age_year.csv | c64777a91bb570309b1f1494a6d6e0a0d15290c76c541ffa2c37f0d7c1bfed74 |
| synthetic_opioids_excl_methadone__state_ethnicity_year.csv | 382e1972f4232a82b13d260115316d8fdd2e76412b49e3f41e16850cbcff4a4e |
| synthetic_opioids_excl_methadone__state_race_year.csv | cac7cb39218bedf34ca21bf7e7d04e41a443ff9e0dad12df4e67f4f46395cea3 |
| synthetic_opioids_excl_methadone__state_sex_year.csv | a639d2b968ea0577c133f8b8bd7fb2d74f0b6e3ae7675402148c81be1362c519 |

Note: `_raw_responses/*.json` (verbatim API request/response pairs, one per CSV) and `_provenance.md` are documentation artifacts, intentionally excluded from checksums and from ingestion.

## Summary

Drug-overdose **deaths**, **crude death rates**, and **age-adjusted death rates** (both per 100,000) for Georgia, 1999–2024, from official death-certificate data. Six overlapping cause categories per the OASIS tool: all drug overdoses, all opioids, natural/semi-synthetic/synthetic opioids, synthetic opioids other than methadone (≈ fentanyl), heroin, and methadone — all "Without F-Codes" (excludes ICD-10 mental/behavioral underlying causes). County × year for all demographics combined; state × year broken down by age (20 buckets), race (7 buckets), ethnicity, and sex.

## Eras

Single era: all 30 files were exported in one scripted download on 2026-07-02 and are internally uniform — same years (1999–2024 + `selected_years_total`), same value vocabularies, and identical column sets *per layout*. The 5 layouts (not eras) differ by breakdown column:

| Layout (6 files each, one per cause) | Columns |
|---|---|
| `{cause}__county_year.csv` | geography, county_fips, year, deaths, death_rate, age_adjusted_death_rate |
| `{cause}__state_age_year.csv` | geography, age, year, deaths, death_rate — **no age-adjusted rate** (tool disallows age stratification with age-adjusted measures) |
| `{cause}__state_race_year.csv` | geography, race, year, deaths, death_rate, age_adjusted_death_rate |
| `{cause}__state_ethnicity_year.csv` | geography, ethnicity, year, deaths, death_rate, age_adjusted_death_rate |
| `{cause}__state_sex_year.csv` | geography, sex, year, deaths, death_rate, age_adjusted_death_rate |

Row counts are identical across causes: county 4,347 (161 geographies × 27 year-values), age 594 (22 × 27), race 243 (9 × 27), ethnicity 135 (5 × 27), sex 108 (4 × 27).

### Columns

| Column | Description |
|--------|-------------|
| geography | `Georgia`, one of 159 county names, or the derived `County Summary` row (county files); always `Georgia` in state files |
| county_fips | County FIPS as bare integer (`13001`–`13321`); `13` (state FIPS) on Georgia rows; null on `County Summary` rows. County files only. |
| age | 20 age buckets (`<1 year`, `1-4 years`, `5-9 years`, … `85+ years`) + `All Detailed Ages` + `Selected Ages Total` |
| race | 7 buckets + `All Races` + `Selected Races Total` (see Categorical Columns) |
| ethnicity | `Hispanic`, `Not Hispanic`, `Unknown` + `All Ethnicities` + `Selected Ethnicities Total` |
| sex | `Female`, `Male` + `All Sexes` + `Selected Sexes Total` |
| year | Calendar year of death as string (`1999`…`2024`) + derived `selected_years_total` row |
| deaths | Count of resident deaths (Int64). Empty = **true zero** per OASIS; never suppressed, never negative. |
| death_rate | Crude rate per 100,000 (Float64). Negative sentinel values = suppressed/NA (see Suppression Markers). `0.0` on zero-death rows. |
| age_adjusted_death_rate | Age-adjusted rate per 100,000 (Float64). Same sentinels. Absent from age-layout files; null on some zero-death rows. |

#### Sample Data (representative: `all_drug_overdoses__county_year.csv`, seed 42)

```
┌───────────┬─────────────┬──────────────────────┬────────┬────────────┬─────────────────────────┐
│ geography ┆ county_fips ┆ year                 ┆ deaths ┆ death_rate ┆ age_adjusted_death_rate │
╞═══════════╪═════════════╪══════════════════════╪════════╪════════════╪═════════════════════════╡
│ Talbot    ┆ 13263       ┆ selected_years_total ┆ 17     ┆ 10.21739   ┆ 11.033854               │
│ Effingham ┆ 13103       ┆ 2006                 ┆ 4      ┆ -5.0       ┆ -5.0                    │
│ Wilkinson ┆ 13319       ┆ 2008                 ┆ 1      ┆ -5.0       ┆ -5.0                    │
│ Pickens   ┆ 13227       ┆ 2022                 ┆ 18     ┆ 51.719679  ┆ 61.314129               │
│ Stephens  ┆ 13257       ┆ 2019                 ┆ 2      ┆ -5.0       ┆ -5.0                    │
└───────────┴─────────────┴──────────────────────┴────────┴────────────┴─────────────────────────┘
```

#### Statistics (`all_drug_overdoses__county_year.csv`; sentinels −5 pollute rate minima)

```
count 4347; county_fips null=27 (County Summary rows); deaths null=982 (true zeros)
deaths:    min 1, max 30634 (statewide selected_years_total), mean 54.6
death_rate:              min -5.0 (sentinel), max 76.43, median 0.0
age_adjusted_death_rate: min -5.0 (sentinel), max 86.23, null=982 (accompanies zero-death rows)
```

State-layout null counts (all_drug_overdoses): age deaths null=30; race deaths null=67, aadr null=38; ethnicity deaths null=9; sex — no nulls. All nulls in `deaths` are true zeros; `age_adjusted_death_rate` nulls co-occur with zero-death rows (sometimes `0.0` instead — inconsistent zero-rendering, same meaning).

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| geography (county files) | `Georgia`, 159 county names (`Appling` … `Worth`), `County Summary` — 161 values × 27 year-rows each |
| geography (state files) | `Georgia` only |
| age | `<1 year`, `1-4 years`, `5-9 years`, `10-14 years`, `15-17 years`, `18-19 years`, `20-24 years`, `25-29 years`, `30-34 years`, `35-39 years`, `40-44 years`, `45-49 years`, `50-54 years`, `55-59 years`, `60-64 years`, `65-69 years`, `70-74 years`, `75-79 years`, `80-84 years`, `85+ years`, `All Detailed Ages`, `Selected Ages Total` (27 rows each) |
| race | `All Races`, `American Indian or Alaska Native`, `Asian`, `Black or African-American`, `Multiracial`, `Native Hawaiian or Other Pacific Islander`, `Selected Races Total`, `Unknown`, `White` (27 rows each) |
| ethnicity | `All Ethnicities`, `Hispanic`, `Not Hispanic`, `Selected Ethnicities Total`, `Unknown` (27 rows each) |
| sex | `All Sexes`, `Female`, `Male`, `Selected Sexes Total` (27 rows each) |
| year | `1999`–`2024` + `selected_years_total` (uniform across all files) |

**Asian / Pacific Islander check**: race publishes the **split pair** — separate `Asian` and `Native Hawaiian or Other Pacific Islander` buckets — and **no** combined Asian/Pacific-Islander bucket. Map to `asian` and `pacific_islander` respectively; no §5b remap needed, and no split-vs-rollup duplication to resolve. Math test passes: at state level 2023 (all_drug_overdoses), the 7 race buckets (incl. `Unknown`, whose deaths are null=0) sum to exactly 2,521 = `All Races` — race buckets are mutually exclusive and exhaustive.

#### Suppression Markers

Values are **numeric sentinels**, not string markers (columns parse as Float64 — a plain `cast(strict=False)` will NOT catch them; they must be filtered by value):

| Column | Sentinel | Meaning (per OASIS UI / `_provenance.md`) | Where observed |
|--------|----------|-------------------------------------------|----------------|
| death_rate, age_adjusted_death_rate | `-5` | Rate suppressed — based on fewer than 5 deaths | all layouts (except some sex files with no small cells) |
| death_rate, age_adjusted_death_rate | `-2` | Not applicable — no population denominator | only `ethnicity = Unknown` rows |
| death_rate, age_adjusted_death_rate | `-1`, `-3`, `-6`, `-7`, `-99` | Other N/A codes documented by the tool | **not present** in current files, but the downloader may surface them on refresh — treat any negative rate as a sentinel |
| deaths | — | never suppressed (empty = true zero) | — |

## ETL Considerations

1. **Negative rate sentinels, not string markers.** `death_rate`/`age_adjusted_death_rate` parse as valid floats; sentinels (`-5`, `-2`, and defensively any negative value) must be nulled by value comparison. Null them — never zero (data-cleaning-standards §4b). Counts are never suppressed.
2. **Null `deaths` = true zero.** Per OASIS, empty means 0 events (the UI renders `0`). Convert null → 0 for `deaths`; this is confirmed by exact reconciliation (race buckets, age buckets, and the 159 counties each sum to the state total, e.g. 2,521 in 2023, treating nulls as 0). Zero-death rows carry `death_rate` `0.0` and `age_adjusted_death_rate` `0.0` **or** null inconsistently — normalize (a true-zero-deaths row has a true rate of 0).
3. **Drop three kinds of derived/duplicate rows**: (a) `year = 'selected_years_total'` (1999–2024 sum), (b) `geography = 'County Summary'` (duplicates the Georgia total; `county_fips` null), (c) `Selected {Races|Ethnicities|Sexes|Ages} Total` rows (verified equal to the corresponding `All …` row — assert equality, keep only `All …` as the `all` demographic).
4. **Cause categories overlap — never model as an exclusive categorical you can sum.** `all_drug_overdoses` ⊃ `all_opioids` ⊃ {natural/semi-synthetic/synthetic, synthetic-excl-methadone, heroin, methadone}, and the opioid sub-types overlap each other (poly-drug deaths count in every matching category: sub-type 2023 deaths sum to 3,609 vs 1,838 for all opioids). If kept as a `drug_category` fact categorical (recommended — 6 file-derived values), it must be a grain key with **no** implied additivity; document prominently in `limitations` and rely on the dashboard's required-single-select behavior. The alternative (6 × 3 wide metric columns) avoids mis-summing entirely but explodes the schema. `_provenance.md` carries the same warning.
5. **Cause labels**: OASIS definitions are "Without F-Codes" (exclude ICD-10 F-code underlying causes). Use the UI's plain labels (`all_drug_overdoses`, `heroin`, …) for values but state the F-code exclusion in the contract description/limitations.
6. **Demographic breakdowns exist only at state grain.** County rows are all-demographics only (county-level splits are nearly fully suppressed upstream, so they were not exported). The fact table will have demographic ≠ `all` only where geography = state. Age/race/ethnicity/sex are four separate breakdown axes from four separate files — concatenate into the single `demographic` FK column; each axis independently reconciles to the same total.
7. **`Unknown` race/ethnicity rows**: race `Unknown` is all-null (0 deaths, all years); ethnicity `Unknown` has real counts (e.g. 128 total) but no rates (`-2`). Decide mapping to the demographics dimension (`unknown` code) or drop; if dropped, ethnicity buckets no longer sum to the total — prefer keeping.
8. **`county_fips` is a bare integer**: cast to 5-digit zero-padded string for counties (values 13001–13321 need no padding but cast defensively). Georgia state rows carry `13` — do not treat as a county; route to the platform's state-level representation. `County Summary` rows have null fips (dropped anyway, see #3).
9. **`year` is a string column** (because of `selected_years_total`); cast to int after dropping derived rows.
10. **Age-layout files lack `age_adjusted_death_rate`** — the tool disallows age-adjusted measures with age stratification. Rows from age files will have that metric null (correctly, not as missing data). Crude `death_rate` for age buckets is age-specific (denominator = that age group's population).
11. **Rate suppression is deaths < 5**: every `-5` co-occurs with `deaths` in 1–4 (or a small cell). After nulling, small-count rows keep their exact `deaths` but no rate — expect heavy rate nullity in county × year for rare causes (heroin/methadone).
12. **Full-grid data**: every geography × year (and demo-bucket × year) combination is present — no missing-row imputation needed.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| geography | dimension_attribute | — | County name lives in the counties dimension; used in transform only to identify state rows and drop `County Summary` |
| county_fips | fact_key | county_fips | 5-digit string FK to counties dimension; state rows per platform state-grain convention (bronze value `13`) |
| age / race / ethnicity / sex | fact_key | demographic | Four breakdown axes (state grain only) → single `demographic` FK to demographics dimension; `All …` → `all`; split `asian` / `pacific_islander` preserved |
| year | fact_key | year | Cast to int after dropping `selected_years_total` rows |
| *(from filename)* cause slug | fact_categorical | drug_category | 6 values; **non-additive/overlapping** — grain key, no `all`-rollup semantics beyond `all_drug_overdoses` itself; see ETL #4 |
| deaths | fact_metric | deaths | `unit: count`; null → 0 (true zero); `metric_component: numerator` if rate is key metric |
| death_rate | fact_metric | death_rate | `unit: ratio` (per 100,000); negative sentinels → NULL; key-metric candidate (crude rate present at every grain, unlike age-adjusted) |
| age_adjusted_death_rate | fact_metric | age_adjusted_death_rate | `unit: ratio` (per 100,000); sentinels → NULL; structurally null for age-breakdown rows |
| *(none)* | not_in_gold | — | `County Summary` / `Selected … Total` / `selected_years_total` rows dropped as derived duplicates |
