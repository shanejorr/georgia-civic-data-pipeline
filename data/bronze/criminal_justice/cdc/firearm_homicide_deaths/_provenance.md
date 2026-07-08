# Provenance — CDC WONDER firearm / homicide / legal-intervention deaths (GA counties)

_Retrieved: 2026-07-02 12:40:27 UTC_

## Source

- **Tool**: CDC WONDER, Multiple Cause of Death (MCD) online query system.
- **Landing page**: <https://wonder.cdc.gov/mcd.html>
- **Datasets** (two race-coding vintages, NCHS/NVSS death certificates):
  - **D77** — Multiple Cause of Death, 1999-2020 (**bridged-race** populations); entry <https://wonder.cdc.gov/mcd-icd10.html>
  - **D157** — Multiple Cause of Death, 2018-2024, **Single Race**; entry <https://wonder.cdc.gov/mcd-icd10-expanded.html>

## Method (scripted web-app form POST)

The official WONDER **XML API cannot return county-level data** (sub-national grouping
is API-blocked). County extracts are therefore pulled by replicating the web app's HTML
form POST, via `src/etl/criminal_justice/cdc/download.py`:

1. GET the dataset entry page to open a session.
2. POST the **data-use-agreement** acceptance (`stage=about`, `action-I Agree=I Agree`).
   The session is tracked by a URL-rewritten `;jsessionid=...` token in the returned
   form's action (not a cookie); every subsequent POST reuses that token.
3. Submit the full Request Form (all inputs, selects, and the ICD-code `<textarea>`
   finders) with overrides: group by **County x Year**, filter **State = Georgia**
   (FIPS 13), Injury-Intent cause mode, per-measure intent/mechanism selections, all
   years, show-suppressed + show-zeros + show-totals, age-adjusted rate (2000 US std
   population), and `O_export-format=tsv` + `action-Send=Send` for a tab-delimited export.

Requests are sequential with a polite delay and an identifying User-Agent.

## Measures / columns

Grain: **residence county x year**. Columns: Deaths, Population, Crude Rate, and
(where available) Age Adjusted Rate (per 100,000; 2000 US standard population).
WONDER forbids age-adjusted rates at county grain for the single-race **D157**
vintage, so those exports carry Deaths / Population / Crude Rate only (see table).

## Cause definitions (ICD-10 injury intent + mechanism recodes)

- `firearm_deaths` — all intents, **Firearm** mechanism (all firearm deaths).
- `homicide` — **Homicide** intent, all mechanisms.
- `firearm_homicide` — **Homicide** intent + **Firearm** mechanism.
- `legal_intervention` — **Legal Intervention / Operations of War** intent, all mechanisms.

## Suppression / reliability (markers kept VERBATIM in bronze)

- **Suppressed** — sub-national death counts **< 10** are suppressed (privacy).
- **Unreliable** — rates computed from **< 20** deaths are flagged unreliable.
- Zero-death county-years are included (show-zeros on).
- Residence county (decedent's county of residence), not occurrence county.
- Do **not** substitute 0 for suppressed cells — the transform NULLs them (never 0).

## Files

| File | Dataset | Measure | Years | Bytes | ~Data rows | AAR col |
| ---- | ------- | ------- | ----- | ----- | ---------- | ------- |
| `firearm_deaths_by_county_year_1999_2020.txt` | D77 | firearm_deaths | 1999-2020 | 281,154 | 3,498 | yes |
| `homicide_by_county_year_1999_2020.txt` | D77 | homicide | 1999-2020 | 279,865 | 3,498 | yes |
| `firearm_homicide_by_county_year_1999_2020.txt` | D77 | firearm_homicide | 1999-2020 | 277,241 | 3,498 | yes |
| `legal_intervention_by_county_year_1999_2020.txt` | D77 | legal_intervention | 1999-2020 | 264,765 | 3,498 | yes |
| `firearm_deaths_by_county_year_2018_2024.txt` | D157 | firearm_deaths | 2018-2024 | 98,323 | 1,113 | no |
| `homicide_by_county_year_2018_2024.txt` | D157 | homicide | 2018-2024 | 97,566 | 1,113 | no |
| `firearm_homicide_by_county_year_2018_2024.txt` | D157 | firearm_homicide | 2018-2024 | 96,171 | 1,113 | no |
| `legal_intervention_by_county_year_2018_2024.txt` | D157 | legal_intervention | 2018-2024 | 80,973 | 1,113 | no |

## Citation

Centers for Disease Control and Prevention, National Center for Health Statistics. Multiple Cause of Death data on CDC WONDER Online Database. Data are from the Multiple Cause of Death Files, as compiled from data provided by the 57 vital statistics jurisdictions through the Vital Statistics Cooperative Program. Accessed at <https://wonder.cdc.gov/mcd.html>.
