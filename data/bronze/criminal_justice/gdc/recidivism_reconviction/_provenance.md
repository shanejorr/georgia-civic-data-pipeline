# Provenance — GDC `recidivism_reconviction`

## Source

- **Agency**: Georgia Department of Corrections (GDC), **Office of Data Management & Research**.
- **Publication**: the GDC **Statistical Trends** standing-reports library. This topic ingests the two "3-Year Reconviction" editions — GDC's canonical recidivism series:
  - **3-Year Reconviction — Calendar Years** → `reconviction_3yr_cy.pdf` (PDF `Title`: *CY Felony Reconviction Rates*).
  - **3-Year Reconviction — Fiscal Years** → `reconviction_3yr_fy.pdf` (PDF `Title`: *FY2026 Felony Reconviction Rates*).
- **Landing page**: <https://gdc.georgia.gov/organization/about-gdc/agency-activity/research-and-reports/standing-reports/statistical-trends>
- **Format**: PDF only — no CSV/XLSX/API.
- **Metric definition**: the **3-year felony reconviction rate** — the percentage of an inmate release cohort reconvicted of a new felony within three years of release, broken down by release facility type and sex.

## Retrieval

- **Retrieved**: 2026-07-04 (UTC).
- **Method**: `uv run python -m src.etl.criminal_justice.gdc.download` — `src/etl/criminal_justice/gdc/download.py`. The scraper matches each report by its link text on the Statistical Trends page, downloads the `/media/{id}/download` anchor following its 301 redirect, and stores the PDF verbatim. Media IDs are never hardcoded; the resolved stable slug is logged.
- **Anchors resolved on this run** (media ID → stable slug):
  - 3-Year Reconviction — Calendar Years: `/media/21676/download` → `https://gdc.georgia.gov/document/statistical-trend-reports/3-year-reconviction-calendar-years/download`
  - 3-Year Reconviction — Fiscal Years: `/media/20901/download` → `https://gdc.georgia.gov/document/statistical-trend-reports/3-year-reconviction-fiscal-years/download`
- **Idempotency**: existing non-empty PDFs are skipped; `--refresh` forces re-download. Verified a second run skipped both files.

## Files

| File | Bytes | Pages | Edition | Cohort years | Report date |
|------|-------|-------|---------|--------------|-------------|
| `reconviction_3yr_cy.pdf` | 27,011 | 1 | Calendar Year | 2011–2022 | 01/06/2026 |
| `reconviction_3yr_fy.pdf` | 25,267 | 1 | Fiscal Year | 2012–2023 | 07/01/2026 |

Grain: statewide × cohort-year, broken down by 8 facility-type / sex rows (incl. two `**` aggregate rows). Metric: 3-year felony reconviction rate (percent, 0–100 scale). Every cell populated; no suppression.

## License

- **No explicit data license or open-data terms** are posted on the GDC Statistical Trends page. These are **public statistical reports published by a Georgia state agency**, public records under the Georgia Open Records Act (O.C.G.A. § 50-18-70 *et seq.*).
- Treat as public-domain government work for redistribution, but **attribute**: "Georgia Department of Corrections, Office of Data Management & Research — Statistical Trends."

## Caveats (carry into the transform / contract)

- **Recidivism = reconviction, NOT re-arrest.** GDC's canonical metric is felony *reconviction* within 3 years of release. Never pool with re-arrest, technical-revocation, or return-to-custody recidivism measures from other sources.
- **Fixed 3-year follow-up on a release cohort.** The year column is the release year; the rate reflects new felony convictions in the following 3 years, so only cohorts with a matured 3-year window are published (latest CY 2022, latest FY 2023).
- **Percent scale (0–100).** Values like `26.90` are percentages; store as a proportion `[0,1]` (÷100) or as percent with an explicit scale note. **No numerator/denominator (cohort N) is published** in these PDFs — the rate stands alone.
- **CY ≠ FY.** Calendar-year and fiscal-year cohorts are different release-window definitions; keep a `reporting_period` categorical and do not merge.
- **`**` footnote undefined on-page.** The `**` on `All inmate facilities` / `All Female Facilities` marks the aggregate rows; its footnote text is not printed on the PDF. Preserve these as roll-up ("all") lines, not summable facility types.
- **Label casing/whitespace drift** between the CY and FY editions (e.g. `All Female Facilities` vs `All female facilities`) — normalize to a canonical facility-type vocabulary in transform.
- **PDF extraction friction.** Single-page matrix; extract with `camelot`/`pdfplumber` (`tabula-py` would need a Java runtime — not installed as of 2026-07-04). Reconcile a sample of cells against `pdftotext -layout`.
- **Media-ID URL instability.** `/media/{id}/download` IDs change on re-upload; the scraper matches by link text and retains the stable slug as fallback.
- **Statewide grain only** — no county mapping; this series does not join to `county_fips`.
