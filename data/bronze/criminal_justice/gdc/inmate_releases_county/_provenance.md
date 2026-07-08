# Provenance — GDC `inmate_releases_county`

## Source

- **Agency**: Georgia Department of Corrections (GDC), **Office of Data Management & Research** ("Data Management & Research" / "General Production" appear in the page footers).
- **Publication**: the GDC **Statistical Trends** standing-reports library — a small suite of statistical-trend PDFs. This topic ingests the two "Inmate Release by County" editions:
  - **Inmate Release by County — Calendar Year** → `inmate_release_by_county_cy.pdf` (PDF `Title`: *Inmate Releases by County - CY2025*; produced by Adobe Acrobat Paper Capture, i.e. a scanned/OCR'd layout).
  - **Inmate Release by County — Fiscal Year** → `inmate_release_by_county_fy.pdf` (PDF `Title`: *Inmate Releases by County - FY2026*; produced by OpenPDF, a born-digital export).
- **Landing page**: <https://gdc.georgia.gov/organization/about-gdc/agency-activity/research-and-reports/standing-reports/statistical-trends>
- **Format**: PDF only — GDC publishes no CSV/XLSX/API for these trends.

## Retrieval

- **Retrieved**: 2026-07-04 (UTC).
- **Method**: `uv run python -m src.etl.criminal_justice.gdc.download` — `src/etl/criminal_justice/gdc/download.py`. The scraper GETs the Statistical Trends page, matches each report by its (whitespace-normalized) link text, downloads the linked `/media/{id}/download` anchor following its 301 redirect, and writes the PDF verbatim (atomic `.part` → rename). Media IDs are **never hardcoded** — they change whenever GDC re-uploads a report — and the resolved stable slug is logged for provenance.
- **Anchors resolved on this run** (media ID → stable slug the download followed):
  - Inmate Release by County — Calendar Year: `/media/19926/download` → `https://gdc.georgia.gov/document/statistical-trend-reports/inmate-release-county-calendar-year/download`
  - Inmate Release by County — Fiscal Year: `/media/20906/download` → `https://gdc.georgia.gov/document/statistical-trend-reports/inmate-release-county-fiscal-year/download`
- **Idempotency**: existing non-empty PDFs are skipped; `--refresh` forces re-download. A second run in this session skipped all files (verified).

## Files

| File | Bytes | Pages | Edition | Year columns | Run date (header) |
|------|-------|-------|---------|--------------|-------------------|
| `inmate_release_by_county_cy.pdf` | 205,103 | 4 | Calendar Year | 2021–2025 | 05-JAN-26 |
| `inmate_release_by_county_fy.pdf` | 198,503 | 4 | Fiscal Year | 2022–2026 | 01-JUL-26 |

Grain: prison releases counted by the inmate's **home county of record** (all 159 counties, GDC codes `001`–`159`), plus `999 - Other Custody/Out Of State`, `Unknown, not reported`, and a statewide `Total` row. Metric: integer count of releases per county per year.

## License

- **No explicit data license or open-data terms** are posted on the GDC Statistical Trends page. These are **public statistical reports published by a Georgia state agency** and are public records under the Georgia Open Records Act (O.C.G.A. § 50-18-70 *et seq.*).
- Treat as public-domain government work for redistribution purposes, but **attribute to the source**: "Georgia Department of Corrections, Office of Data Management & Research — Statistical Trends." If GDC posts formal terms later, revisit.

## Caveats (carry into the transform / contract)

- **PDF extraction friction.** Tables must be extracted with `camelot`/`pdfplumber` or `tabula-py` at transform time; **`tabula-py` requires a Java runtime** (not installed as of 2026-07-04). Four-page continued table with a repeated header — de-dup the header and reconcile the 159 county values + 2 residual rows to the printed `Total` per year. The CY PDF is OCR-derived (Acrobat Paper Capture) — spot-check digit extraction; the FY PDF is born-digital.
- **Rolling five-year window.** Each edition shows only the five most recent complete years and *shifts* on every re-run (drops oldest, adds newest). Key on the column-header year, de-dup overlaps on `(county, year, reporting_period)`, and never assume the file is an append-only archive.
- **CY ≠ FY.** Calendar-year and fiscal-year editions are different 12-month windows; keep a `reporting_period` categorical and never pool or sum across them.
- **GDC county code ≠ FIPS.** The `001`–`159` prefix is GDC's alphabetical index; resolve to FIPS from the county *name* via `add_county_fips` + `COUNTY_NAME_OVERRIDES`.
- **Home county attribution.** "Home county" is the inmate's county of record, not the county of offense or of the releasing facility.
- **Not comparable to jail data.** These are *prison* releases (GDC state custody), unrelated to county-jail populations (`jails/jail_population`).
- **Media-ID URL instability.** The `/media/{id}/download` IDs change on re-upload; the scraper handles this by matching link text, but a page-markup change could require updating `REPORTS[*]["text_re"]` in `download.py` (the expected stable slug is retained as a fallback).
- **Offense taxonomy.** GDC's offense/facility taxonomy is GDC-specific and **≠ NIBRS** — relevant for cross-source joins (not exposed in this particular report, which is county counts only).
