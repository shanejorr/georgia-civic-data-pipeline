# violent_deaths — Bronze Data Structure

## Overview

- Topic: violent_deaths
- Source: dph_oasis (GA Dept. of Public Health, OASIS Data Table Tool — death-certificate data from the Georgia Office of Vital Records)
- Files: 20 CSV files (4 violent/external-cause categories × 5 layouts), all covering 1994–2024
- Unreadable files: none
- Year representation: `year` column, 4-digit calendar year (`1994`…`2024`), plus a derived `selected_years_total` row per group (drop in transform). Year of death, not publication year.
- Filename-to-data year offset: n/a — filenames carry no year; all files span all years
- Detail levels: state (Georgia) and county (159 counties, 5-digit FIPS). Demographic breakdowns (age/race/ethnicity/sex) exist **only at state level**; county files are all-demographics-combined.
- Percentage scale: no percentages. `death_rate` and `age_adjusted_death_rate` are per-100,000-population rates (unit: `ratio`), `deaths` is a count.
- Checksums generated: 2026-07-02

## Source Provenance

Full detail in `_provenance.md` (same directory), summarized here:

- **Source URL**: https://oasis.state.ga.us/dtt/mortality (data endpoint `POST https://oasis.state.ga.us/dtt/Mortality/GetData`; county FIPS from `https://oasis.state.ga.us/dtt/data/geographies.json`)
- **Retrieved**: 2026-07-02 (12:35 UTC)
- **Method**: scripted fetch — `src/etl/criminal_justice/dph_oasis/download.py` (re-runnable; picks up new data years automatically). Verbatim request/response JSON kept in `_raw_responses/` (subdirectory — not scanned by the freshness gate, not ingested by the transform).

## File Checksums

Generated: 2026-07-02

| File | SHA-256 |
|------|---------|
| accidental_shooting__county_year.csv | a341a0a5ab9498cc3a98c738ea533726c6854a9c46ad4b58a3feb36f5e73cf0a |
| accidental_shooting__state_age_year.csv | ef276ebffe56f5731750cf16a43b1eaf99266b46bcf92d470c105896cd6db179 |
| accidental_shooting__state_ethnicity_year.csv | 3b99a8bb718baa5c2108caaa97e84150ab3d2a87096dc67d4e9e6760c6755712 |
| accidental_shooting__state_race_year.csv | 0697edcfeb9816cf3c404c0bb7d4f1ba757124fe5df85f8a4a3600fd835b0d0d |
| accidental_shooting__state_sex_year.csv | 3130b3f3d6727d14bb67bfa4d8967ca519f36bcc183b699d2bd06fec7ee3876e |
| homicide__county_year.csv | 06ab1cd0ebc2f321ec5e8a312f0f84d642392b41f0cb40a054870636420929f4 |
| homicide__state_age_year.csv | f5f815a9539eb423882937613fb7b034328fcaf33bae5d93e72d18f5369c714c |
| homicide__state_ethnicity_year.csv | b149958819ced13498371f1607c86de6b344cccc08b93b071aa866cb4b9659a9 |
| homicide__state_race_year.csv | a6d69cdf936acd52e302bea0e9a1c210cc27409d869e9c49d96861a37cebb5f6 |
| homicide__state_sex_year.csv | fb7e87eb03a66496d89b8ec15cf4fa4dec939c7447e43af7d2eb9b5a8454c31a |
| legal_intervention__county_year.csv | f98c380e7a5afc0062c67c6ba5a22d95e2f208b812b72f8183c7fffb50b0c513 |
| legal_intervention__state_age_year.csv | 04f004d4f6291dece49ac67372e5cfb1e6b428479de4a335dc03502247b526e9 |
| legal_intervention__state_ethnicity_year.csv | a0aff3deb70d61b16ff533861b89a94e77d330ef07390095220600515f48aa0f |
| legal_intervention__state_race_year.csv | 67c35c0214996e45a6a953fbf0f3be6082601a72990f573beb410399a582ef9d |
| legal_intervention__state_sex_year.csv | 7d068c0842ece0bf84f9534e5775113b0806b47e50f8c538a61f87df311422a7 |
| suicide__county_year.csv | 92b84486402c66d136605854c3e6eb2b85fb6526bfcf6408bea87a7b2c9b0c25 |
| suicide__state_age_year.csv | d35cc8440f96356410ade467051e3408b8e9c8d5e2bd22aceeceabda7f815b13 |
| suicide__state_ethnicity_year.csv | 389ef3ec6ee1cd79af620f5bf3604a7c7b9a5dd1829f334f60eecdfee6f84c26 |
| suicide__state_race_year.csv | 9780e81d035c14b817d2dae924eef4765be63a88008b1ff7efbb9b41a8b4f269 |
| suicide__state_sex_year.csv | e79bc940418cc45cdfcb8d9c6783b3489cc6c103a0b9feb41d99e46747269e0b |

Note: `_raw_responses/*.json` (verbatim API request/response pairs, one per CSV) and `_provenance.md` are documentation artifacts, intentionally excluded from checksums and from ingestion.

## Summary

Violent/external-cause **deaths**, **crude death rates**, and **age-adjusted death rates** (both per 100,000) for Georgia, 1994–2024, from official death-certificate data. Four OASIS detailed-cause categories: **homicide** (Assault), **suicide** (Intentional Self-Harm), **legal intervention** (deaths caused by law enforcement), and **accidental shooting** (the tool's only firearm-specific cause — OASIS has no all-intents firearm category; CDC WONDER is the canonical all-intents firearm series). County × year for all demographics combined; state × year broken down by age (20 buckets), race (7 buckets), ethnicity, and sex. Structurally identical to the sibling `overdose_deaths` topic (same downloader, same layouts, same sentinel scheme) but starting in 1994 rather than 1999.

## Eras

Single era: all 20 files were exported in one scripted download on 2026-07-02 and are internally uniform — same years (1994–2024 + `selected_years_total`), same value vocabularies, and identical column sets *per layout*. The 5 layouts (not eras) differ by breakdown column:

| Layout (4 files each, one per cause) | Columns |
|---|---|
| `{cause}__county_year.csv` | geography, county_fips, year, deaths, death_rate, age_adjusted_death_rate |
| `{cause}__state_age_year.csv` | geography, age, year, deaths, death_rate — **no age-adjusted rate** (tool disallows age stratification with age-adjusted measures) |
| `{cause}__state_race_year.csv` | geography, race, year, deaths, death_rate, age_adjusted_death_rate |
| `{cause}__state_ethnicity_year.csv` | geography, ethnicity, year, deaths, death_rate, age_adjusted_death_rate |
| `{cause}__state_sex_year.csv` | geography, sex, year, deaths, death_rate, age_adjusted_death_rate |

Row counts are identical across causes: county 5,152 (161 geographies × 32 year-values), age 704 (22 × 32), race 288 (9 × 32), ethnicity 160 (5 × 32), sex 128 (4 × 32).

### Columns

| Column | Description |
|--------|-------------|
| geography | `Georgia`, one of 159 county names, or the derived `County Summary` row (county files); always `Georgia` in state files |
| county_fips | County FIPS as bare integer (`13001`–`13321`); `13` (state FIPS) on Georgia rows; null on `County Summary` rows. County files only. |
| age | 20 age buckets (`<1 year`, `1-4 years`, `5-9 years`, … `85+ years`) + `All Detailed Ages` + `Selected Ages Total` |
| race | 7 buckets + `All Races` + `Selected Races Total` (see Categorical Columns) |
| ethnicity | `Hispanic`, `Not Hispanic`, `Unknown` + `All Ethnicities` + `Selected Ethnicities Total` |
| sex | `Female`, `Male` + `All Sexes` + `Selected Sexes Total` |
| year | Calendar year of death as string (`1994`…`2024`) + derived `selected_years_total` row |
| deaths | Count of resident deaths (Int64). Empty = **true zero** per OASIS; never suppressed, never negative. |
| death_rate | Crude rate per 100,000 (Float64). Negative sentinel values = suppressed/NA (see Suppression Markers). `0.0` on zero-death rows. |
| age_adjusted_death_rate | Age-adjusted rate per 100,000 (Float64). Same sentinels. Absent from age-layout files; null on zero-death rows (county files) or inconsistently null/`0.0` (state files). |

#### Sample Data (representative: `homicide__county_year.csv`, seed 42)

```
┌────────────┬─────────────┬──────┬────────┬────────────┬─────────────────────────┐
│ geography  ┆ county_fips ┆ year ┆ deaths ┆ death_rate ┆ age_adjusted_death_rate │
╞════════════╪═════════════╪══════╪════════╪════════════╪═════════════════════════╡
│ Taliaferro ┆ 13265       ┆ 1994 ┆ null   ┆ 0.0        ┆ null                    │
│ Effingham  ┆ 13103       ┆ 2003 ┆ null   ┆ 0.0        ┆ null                    │
│ Wilkinson  ┆ 13319       ┆ 2005 ┆ null   ┆ 0.0        ┆ null                    │
│ Pickens    ┆ 13227       ┆ 2021 ┆ null   ┆ 0.0        ┆ null                    │
│ Stephens   ┆ 13257       ┆ 2018 ┆ 1      ┆ -5.0       ┆ -5.0                    │
└────────────┴─────────────┴──────┴────────┴────────────┴─────────────────────────┘
```

#### Statistics (`homicide__county_year.csv`; sentinels −5 pollute rate minima)

```
count 5152; county_fips null=32 (County Summary rows); deaths null=1458 (true zeros)
deaths:    min 1, max 23580 (statewide selected_years_total), mean 38.3
death_rate:              min -5.0 (sentinel), max 89.37, median -5.0
age_adjusted_death_rate: min -5.0 (sentinel), max 88.61, null=1458 (accompanies zero-death rows)
```

County-layout null counts by cause (`deaths` = `age_adjusted_death_rate` nulls, all true zeros; `county_fips` null=32 = County Summary rows): homicide 1,458; suicide 714; accidental_shooting 4,280; legal_intervention 4,608 — the two rare causes are zero in most county-years. State-layout null counts (homicide): age deaths null=1; race deaths null=81, aadr null=37; ethnicity deaths null=10; sex — no nulls. All `deaths` nulls are true zeros; state-file `age_adjusted_death_rate` on zero-death rows is sometimes `0.0` instead of null (inconsistent zero-rendering, same meaning).

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| geography (county files) | `Georgia`, 159 county names (`Appling` … `Worth`), `County Summary` — 161 values × 32 year-rows each |
| geography (state files) | `Georgia` only |
| age | `<1 year`, `1-4 years`, `5-9 years`, `10-14 years`, `15-17 years`, `18-19 years`, `20-24 years`, `25-29 years`, `30-34 years`, `35-39 years`, `40-44 years`, `45-49 years`, `50-54 years`, `55-59 years`, `60-64 years`, `65-69 years`, `70-74 years`, `75-79 years`, `80-84 years`, `85+ years`, `All Detailed Ages`, `Selected Ages Total` (32 rows each) |
| race | `All Races`, `American Indian or Alaska Native`, `Asian`, `Black or African-American`, `Multiracial`, `Native Hawaiian or Other Pacific Islander`, `Selected Races Total`, `Unknown`, `White` (32 rows each) |
| ethnicity | `All Ethnicities`, `Hispanic`, `Not Hispanic`, `Selected Ethnicities Total`, `Unknown` (32 rows each) |
| sex | `All Sexes`, `Female`, `Male`, `Selected Sexes Total` (32 rows each) |
| year | `1994`–`2024` + `selected_years_total` (uniform across all files) |

**Asian / Pacific Islander check**: race publishes the **split pair** — separate `Asian` and `Native Hawaiian or Other Pacific Islander` buckets — and **no** combined Asian/Pacific-Islander bucket. Map to `asian` and `pacific_islander` respectively; no §5b remap needed, and no split-vs-rollup duplication to resolve. Math test passes for all 4 causes: at state level 2023 (deaths null→0), the 7 race buckets (incl. `Unknown`, whose deaths are always null) sum exactly to `All Races` (homicide 1,058; suicide 1,658; legal_intervention 27; accidental_shooting 18) — race buckets are mutually exclusive and exhaustive.

#### Suppression Markers

Values are **numeric sentinels**, not string markers (columns parse as Float64 — a plain `cast(strict=False)` will NOT catch them; they must be filtered by value):

| Column | Sentinel | Meaning (per OASIS UI / `_provenance.md`) | Where observed |
|--------|----------|-------------------------------------------|----------------|
| death_rate, age_adjusted_death_rate | `-5` | Rate suppressed — based on fewer than 5 deaths | all layouts (6,982 / 6,307 occurrences respectively) |
| death_rate, age_adjusted_death_rate | `-2` | Not applicable — no population denominator | `ethnicity = Unknown` rows (all 4 causes) **and one `race = Native Hawaiian or Other Pacific Islander` row** (suicide) |
| death_rate, age_adjusted_death_rate | `-1`, `-3`, `-6`, `-7`, `-99` | Other N/A codes documented by the tool | **not present** in current files, but the downloader may surface them on refresh — treat any negative rate as a sentinel |
| deaths | — | never suppressed (empty = true zero) | — |

## ETL Considerations

1. **Negative rate sentinels, not string markers.** `death_rate`/`age_adjusted_death_rate` parse as valid floats; sentinels (`-5`, `-2`, and defensively any negative value) must be nulled by value comparison. Null them — never zero (data-cleaning-standards §4b). Counts are never suppressed.
2. **Null `deaths` = true zero.** Per OASIS, empty means 0 events (the UI renders `0`). Convert null → 0 for `deaths`; confirmed by exact reconciliation: race/age/ethnicity/sex buckets and the 159 counties each sum to the state total treating nulls as 0 (homicide 2023: Georgia = county sum = County Summary = 1,058). Zero-death rows carry `death_rate` `0.0` and `age_adjusted_death_rate` null (county files) or `0.0`/null inconsistently (state files) — normalize (a true-zero-deaths row has a true rate of 0).
3. **Drop three kinds of derived/duplicate rows**: (a) `year = 'selected_years_total'` (1994–2024 sum), (b) `geography = 'County Summary'` (duplicates the Georgia total; `county_fips` null), (c) `Selected {Races|Ethnicities|Sexes|Ages} Total` rows (verified equal to the corresponding `All …` row across all 16 breakdown files, all years — assert equality, keep only `All …` as the `all` demographic).
4. **Cause categories are mutually exclusive here** — unlike `overdose_deaths` (whose drug categories overlap), OASIS detailed causes assign each death exactly one underlying cause, so homicide / suicide / legal_intervention / accidental_shooting rows never double-count each other. A `cause_of_death` (or similar) fact categorical is safe as a grain key, but note there is **no all-causes rollup row** — the four causes do not sum to anything meaningful (they are 4 of many external causes), so no `all` value should be fabricated. The dashboard's required-single-select behavior applies.
5. **ICD comparability break at 1998/1999.** Causes are ICD-9-coded for 1994–1998 deaths and ICD-10-coded from 1999 on (NCHS comparability break). Document in `limitations` — trend comparisons across the break are approximate. (This is why the sibling `overdose_deaths` starts at 1999; the mortality tool serves 1994+.)
6. **Demographic breakdowns exist only at state grain.** County rows are all-demographics only (county-level splits are almost entirely suppressed upstream, so they were not exported). The fact table will have demographic ≠ `all` only where geography = state. Age/race/ethnicity/sex are four separate breakdown axes from four separate files — concatenate into the single `demographic` FK column; each axis independently reconciles to the same total.
7. **`Unknown` race/ethnicity rows**: race `Unknown` is all-null (0 deaths, all years, all causes); ethnicity `Unknown` has real counts (e.g. homicide 660 total) but no rates (`-2`). Decide mapping to the demographics dimension (`unknown` code) or drop; if dropped, ethnicity buckets no longer sum to the total — prefer keeping.
8. **`county_fips` is a bare integer**: cast to 5-digit zero-padded string for counties (values 13001–13321 need no padding but cast defensively). Georgia state rows carry `13` — do not treat as a county; route to the platform's state-level representation. `County Summary` rows have null fips (dropped anyway, see #3).
9. **`year` is a string column** (because of `selected_years_total`); cast to int after dropping derived rows.
10. **Age-layout files lack `age_adjusted_death_rate`** — the tool disallows age-adjusted measures with age stratification. Rows from age files will have that metric null (correctly, not as missing data). Crude `death_rate` for age buckets is age-specific (denominator = that age group's population).
11. **Rate suppression is deaths < 5**: every `-5` co-occurs with `deaths` in 1–4 (or a small cell). After nulling, small-count rows keep their exact `deaths` but no rate — expect heavy rate nullity at county grain, especially for the rare causes (legal_intervention: statewide 5–47 deaths/year; accidental_shooting: 13–51/year — most county-years are zero or suppressed).
12. **Full-grid data**: every geography × year (and demo-bucket × year) combination is present — no missing-row imputation needed.
13. **Shared transform potential with `overdose_deaths`**: same downloader, identical layouts, vocabularies, and sentinel scheme. Consider sharing parsing/reshaping helpers, but keep the topics separate — different year spans (1994 vs 1999 start), different categorical semantics (exclusive causes vs overlapping drug categories).

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| geography | dimension_attribute | — | County name lives in the counties dimension; used in transform only to identify state rows and drop `County Summary` |
| county_fips | fact_key | county_fips | 5-digit string FK to counties dimension; state rows per platform state-grain convention (bronze value `13`) |
| age / race / ethnicity / sex | fact_key | demographic | Four breakdown axes (state grain only) → single `demographic` FK to demographics dimension; `All …` → `all`; split `asian` / `pacific_islander` preserved |
| year | fact_key | year | Cast to int after dropping `selected_years_total` rows |
| *(from filename)* cause slug | fact_categorical | cause_of_death | 4 values (`homicide`, `suicide`, `legal_intervention`, `accidental_shooting`); mutually exclusive but **no all-causes rollup** — see ETL #4 |
| deaths | fact_metric | deaths | `unit: count`; null → 0 (true zero); `metric_component: numerator` if rate is key metric |
| death_rate | fact_metric | death_rate | `unit: ratio` (per 100,000); negative sentinels → NULL; key-metric candidate (crude rate present at every grain, unlike age-adjusted) |
| age_adjusted_death_rate | fact_metric | age_adjusted_death_rate | `unit: ratio` (per 100,000); sentinels → NULL; structurally null for age-breakdown rows |
| *(none)* | not_in_gold | — | `County Summary` / `Selected … Total` / `selected_years_total` rows dropped as derived duplicates |
