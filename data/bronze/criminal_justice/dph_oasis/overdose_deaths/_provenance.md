# Provenance — GA DPH OASIS `overdose_deaths`

- **Source**: Georgia Dept. of Public Health, OASIS Data Table Tool
  (Office of Health Indicators for Planning). Death-certificate data from the
  Georgia Office of Vital Records — official Georgia mortality statistics
  (residents, wherever the death occurred; underlying cause assigned by NCHS).
- **Tool page**: https://oasis.state.ga.us/dtt/mortalitydrugoverdoses
- **Data endpoint**: `POST https://oasis.state.ga.us/dtt/MortalityDrugOverdoses/GetData` (JSON body; requires the
  ASP.NET antiforgery cookie + `RequestVerificationToken` header scraped from
  the tool page's `<meta id="wq-meta" data-anti>` attribute).
- **Select-list catalogs**: `https://oasis.state.ga.us/dtt/data/*.json` (times from
  `timesDrugODMortality.json`, geographies with county FIPS from
  `geographies.json`).
- **Downloaded**: 2026-07-02 12:34:12 UTC by `src/etl/criminal_justice/dph_oasis/download.py`
  (re-runnable; picks up new data years automatically).
- **Years**: 1999–2024 (all years the tool serves).
- **Measures per file**: Deaths, Death Rate (crude, per 100,000),
  Age-Adjusted Death Rate (per 100,000; omitted in the age-breakdown files —
  the tool disallows age stratification with age-adjusted measures).

## Files

- `{cause}__county_year.csv` — Georgia + 159 counties (5-digit FIPS) +
  the tool's "County Summary" row, by year, all demographics combined.
- `{cause}__state_{race|sex|ethnicity|age}_year.csv` — state-level ("Georgia")
  demographic breakdowns (county-level demographic splits are almost entirely
  suppressed, so only state grain is exported).
- `_raw_responses/*.json` — verbatim request payload + server JSON response
  for every CSV.

## Causes

| file slug | OASIS `CauseTypes` value | cause category |
|---|---|---|
| `all_drug_overdoses` | `Drug Overdoses Without F-Codes` | parent `Drug Overdoses Without F-Codes` |
| `all_opioids` | `All Opioids Without F-Codes` | parent `All Opioids Without F-Codes` |
| `natural_semisynthetic_synthetic_opioids` | `Natural, Semi-synthetic, Synthetic Opioids Without F-Codes` | parent `All Opioids Without F-Codes` |
| `synthetic_opioids_excl_methadone` | `Synthetic Opioids other than Methadone Without F-Codes` | parent `All Opioids Without F-Codes` |
| `heroin` | `Heroin Without F-Codes` | parent `All Opioids Without F-Codes` |
| `methadone` | `Methadone Without F-Codes` | parent `All Opioids Without F-Codes` |

Cause source: `Drug Overdoses`.

## Suppression / sentinel values (kept verbatim — do NOT treat as counts)

The tool's UI renders the raw JSON values in these files as:

| raw value | UI rendering | meaning |
|---|---|---|
| empty (JSON `null`) | `0` / `0.0` | no events (true zero per OASIS) |
| `-5` | `*` | **rate suppressed** — rate based on fewer than 5 events |
| `-1`, `-2`, `-3`, `-6`, `-7`, `-99` | `N/A…` | not applicable (e.g. no population for the selection) |

Transform policy: suppressed/N-A sentinels → NULL, never 0 (see
data-cleaning-standards §4b / review-doc suppression note).

## Notes

- Drug-overdose cause categories are **not mutually exclusive** (any-opioid overlaps fentanyl/heroin/methadone; all-drug-overdoses contains them all). Model as separate metrics, never as an exclusive categorical.
- Cause values carry the "Without F-Codes" qualifier: OASIS drug-overdose definitions exclude ICD-10 mental/behavioral (F-code) underlying causes; the UI labels these simply 'All Drug Overdoses', 'Heroin', etc.
- The `year` column includes the tool's derived `selected_years_total`
  column and the `County Summary` row verbatim; drop both in transform.
- Rows/columns mirror the tool's own XLSX export (which is generated
  client-side from the same JSON; FIPS codes come from `geographies.json`,
  exactly as the export's "include FIPS" option does).
