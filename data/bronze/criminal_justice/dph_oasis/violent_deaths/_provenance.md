# Provenance — GA DPH OASIS `violent_deaths`

- **Source**: Georgia Dept. of Public Health, OASIS Data Table Tool
  (Office of Health Indicators for Planning). Death-certificate data from the
  Georgia Office of Vital Records — official Georgia mortality statistics
  (residents, wherever the death occurred; underlying cause assigned by NCHS).
- **Tool page**: https://oasis.state.ga.us/dtt/mortality
- **Data endpoint**: `POST https://oasis.state.ga.us/dtt/Mortality/GetData` (JSON body; requires the
  ASP.NET antiforgery cookie + `RequestVerificationToken` header scraped from
  the tool page's `<meta id="wq-meta" data-anti>` attribute).
- **Select-list catalogs**: `https://oasis.state.ga.us/dtt/data/*.json` (times from
  `times.json`, geographies with county FIPS from
  `geographies.json`).
- **Downloaded**: 2026-07-02 12:35:03 UTC by `src/etl/criminal_justice/dph_oasis/download.py`
  (re-runnable; picks up new data years automatically).
- **Years**: 1994–2024 (all years the tool serves).
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
| `homicide` | `Assault (Homicide)` | parent `External Causes` |
| `suicide` | `Intentional Self-Harm (Suicide)` | parent `External Causes` |
| `legal_intervention` | `Legal Intervention` | parent `External Causes` |
| `accidental_shooting` | `Accidental Shooting` | parent `External Causes` |

Cause source: `OASIS Detailed Causes`.

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

- OASIS has **no all-intents firearm-mortality cause**; only `Accidental Shooting` is firearm-specific. CDC WONDER (source #6) is the canonical all-intents firearm/homicide series; these files are the official Georgia vital-statistics counterpart.
- The mortality tool serves 1994+; causes are ICD-9 based before 1999 and ICD-10 from 1999 on (NCHS comparability break at 1998/1999).
- The `year` column includes the tool's derived `selected_years_total`
  column and the `County Summary` row verbatim; drop both in transform.
- Rows/columns mirror the tool's own XLSX export (which is generated
  client-side from the same JSON; FIPS codes come from `geographies.json`,
  exactly as the export's "include FIPS" option does).
