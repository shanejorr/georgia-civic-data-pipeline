# Provenance — GDC `inmate_population`

## Source

- **Agency**: Georgia Department of Corrections (GDC), **Office of Data Management & Research**.
- **Publication**: the GDC **Statistical Trends** standing-reports library. This topic ingests one report:
  - **Year-End Population since 1925** → `year_end_population_since_1925.pdf` (PDF `Title`: *Inmate Population Yearly Counts (1925 - present)*; produced by Adobe Acrobat Paper Capture).
- **Landing page**: <https://gdc.georgia.gov/organization/about-gdc/agency-activity/research-and-reports/standing-reports/statistical-trends>
- **Format**: PDF only — no CSV/XLSX/API.
- **Measure**: year-end count of inmates of the Georgia Prison System, 1925 to present (statewide). Scope and per-era methodology are printed on the page (see Caveats).

## Retrieval

- **Retrieved**: 2026-07-04 (UTC).
- **Method**: `uv run python -m src.etl.criminal_justice.gdc.download` — `src/etl/criminal_justice/gdc/download.py`. The scraper matches the report by its link text on the Statistical Trends page, downloads the `/media/{id}/download` anchor following its 301 redirect, and stores the PDF verbatim. Media IDs are never hardcoded; the resolved stable slug is logged.
- **Anchor resolved on this run** (media ID → stable slug):
  - Year-End Population since 1925: `/media/20966/download` → `https://gdc.georgia.gov/document/statistical-trend-reports/year-end-pop-1925/download`
- **Idempotency**: existing non-empty PDF is skipped; `--refresh` forces re-download. Verified a second run skipped the file.

## Files

| File | Bytes | Pages | Span | Cadence |
|------|-------|-------|------|---------|
| `year_end_population_since_1925.pdf` | 305,696 | 1 | 1925–2024 (100 annual rows) | annual, first week of January |

Grain: statewide × year. Metric: integer year-end inmate count. Printed as five side-by-side `Year | Count` blocks plus a bar chart (a picture of the same series — not extracted). No suppression, no missing years.

## License

- **No explicit data license or open-data terms** are posted on the GDC Statistical Trends page. This is a **public statistical report published by a Georgia state agency**, a public record under the Georgia Open Records Act (O.C.G.A. § 50-18-70 *et seq.*).
- Treat as public-domain government work for redistribution, but **attribute**: "Georgia Department of Corrections, Office of Data Management & Research — Statistical Trends." The pre-1980 values additionally derive from the federal **National Corrections Reporting Program (NCRP)**.

## Caveats (carry into the transform / contract)

- **Methodological break — do not pool eras.** The page's own sources block: **1925–1979** from the National Corrections Reporting Program (NCRP); **1980–1999** = December **average daily population** (an average, not a point-in-time count); **2000 forward** = the **December 31 head-count** report. Carry a `count_method` categorical (or at minimum document in `limitations`) — the ADP era is not directly comparable to the head-count era.
- **Scope inclusions/exclusions.** Includes state prisoners in state prisons, inmate boot camps, county prisons, transition centers, and private prisons. **Excludes** probationers in detention/diversion/probation boot camps and **excludes** county-jail inmates — so this must **not** be reconciled against `jails/jail_population` (county jails) or probation/parole supervision counts.
- **Un-pivot the five print blocks.** The 100 years are printed as five side-by-side `Year | Count` blocks to fit one page; stack them into a single tidy series (never read as five columns). **Ignore the bottom bar chart** (rendered picture of the same numbers).
- **Statewide grain only** — no `county_fips`.
- **PDF extraction friction.** Acrobat Paper-Capture (OCR-derived) PDF — spot-check digit extraction; extract with `camelot`/`pdfplumber` (`tabula-py` would need a Java runtime, not installed as of 2026-07-04) or `pdftotext -layout` + parsing. Reconcile anchors (2024 = 50,107).
- **Media-ID URL instability.** `/media/{id}/download` IDs change on re-upload; the scraper matches by link text and retains the stable slug as fallback.

## Related source not ingested — jails/county_jail_report

Blueprint source #11 lists a fourth topic under the GDC entry: the monthly **County Jail Inmate Population Report** (all 159 counties: population, capacity, state-sentenced backlog, awaiting-trial). **It is intentionally NOT built here**, for these reasons:

- **It was never actually a GDC product.** The monthly County Jail Inmate Population Report was produced by the Georgia **Department of Community Affairs (DCA)**, not GDC, and that DCA series has been **discontinued**.
- **Live county-jail data already ingested elsewhere.** Current county-jail population/capacity data now comes from the **Georgia Sheriffs' Association** monthly jail report and is already ingested as the Tier 1 topic **`jails/jail_population`** (`data/bronze/criminal_justice/jails/jail_population/`) — which covers the same measures (per-county population, capacity, % capacity, state-sentenced backlog, awaiting-trial) with a re-runnable downloader and a POST archive back to 2007.
- **Historical backfill option exists but is deferred.** Historical monthly issues of the old DCA report (2000s–2021+) survive in the **Digital Library of Georgia** (<https://dlg.usg.edu>) and could be a future backfill for the pre-GSA era, but that is a separate, non-trivial ingestion (scanned PDFs) and is **out of scope** for this GDC bronze work.

Net: the county-jail measure is covered by `jails/jail_population`; this GDC `gdc/` sub-topic covers only the three statewide/county **prison** trends (releases-by-county, reconviction, year-end population).
