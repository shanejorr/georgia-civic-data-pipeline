# Provenance — OJJDP EZAPOP: Georgia county juvenile population

- **Source tool**: OJJDP Statistical Briefing Book — *Easy Access to Juvenile
  Populations* (EZAPOP), built by NCJJ from U.S. Census Bureau / NCHS
  county-level bridged-race population estimates.
  <https://www.ojjdp.gov/ojstatbb/ezapop>
- **Actual data endpoint**: classic ASP GET form —
  `https://www.ojjdp.gov/ojstatbb/ezapop/asp/comparison_display.asp` with
  `export_file=yes` returns a CSV attachment. Georgia = `selState=13`;
  `col_var=v01` puts years in columns, counties in rows. Filter checkboxes:
  `v01N` year (v011=1990 … v0135=2024), `v02N` sex (1=Male, 2=Female), `v03N`
  race (1=White, 2=Black, 3=American Indian, 4=Asian), `v04N` ethnicity
  (1=Non-Hispanic, 2=Hispanic), `v05N` age (v051=age 0 … v0518=age 17,
  v0519=18–20, v0520=21–24, v0521=25+).
- **Retrieved**: 2026-07-02T12:33Z (UTC) via
  `uv run python -m src.etl.criminal_justice.ojjdp.download` (re-runnable;
  discovers offered years from the selection form; never overwrites existing
  files unless `--refresh`).
- **Coverage**: all 159 Georgia counties (full coverage — census estimates,
  no reporting gaps, no suppression), years **1990–2024**, plus an
  "All Counties" statewide row and a row/column "Total". Each CSV embeds its
  own `Selecting:` block stating exactly which filters were applied — kept
  verbatim.

## Files (28 CSVs, county × year counts)

- `ezapop_ga_county_year_juveniles_age00_17.csv` — **headline denominator**:
  juveniles (ages 0–17) per county per year.
- `ezapop_ga_county_year_all_ages.csv` — total resident population (all ages),
  context only.
- `ezapop_ga_county_year_juveniles_sex_{male,female}.csv` — juveniles 0–17 by
  sex (verified: male + female = total).
- `ezapop_ga_county_year_juveniles_race_{white,black,american_indian,asian}.csv`
  — juveniles 0–17 by race (bridged race; "Asian" includes Pacific Islander;
  race categories include both ethnicities).
- `ezapop_ga_county_year_juveniles_ethnicity_{hispanic,non_hispanic}.csv` —
  juveniles 0–17 by ethnicity.
- `ezapop_ga_county_year_age_{00..17}.csv` — single year of age, so any age
  band can be rebuilt (verified: ages 0–17 sum to the juveniles total). Use
  ages 10–16 to build the GA delinquency-jurisdiction denominator matching
  EZACO's `popten` (GA upper age = 16).

## Caveats

- Rate denominators for `ojjdp/juvenile_court_cases` (EZACO): compute rates
  only over *reporting* counties — EZAPOP covers all 159 counties but EZACO
  case counts do not.
- Sex/race/ethnicity/age files are one-way marginals (each × county × year),
  not cross-tabs.
- Estimates are periodically revised by the Census Bureau; the tool serves
  the current vintage only (citation vintage: 1990–2024, published 2026).
- **Funding-at-risk snapshot**: the Statistical Briefing Book's federal
  funding is at risk — these files are the archival snapshot taken at first
  ingest (2026-07-02). Do not delete even if the tool goes away.

## Citation (from the exports, verbatim)

Puzzanchera, C., Sladky, A. and Kang, W. (2026). *Easy Access to Juvenile
Populations: 1990–2024.* Online. Available:
<https://www.ojjdp.gov/ojstatbb/ezapop/>
