# Provenance — GA State Board of Pardons and Paroles `parole_decisions`

## Source

- **Agency**: Georgia State Board of Pardons and Paroles (SBPP) — Georgia's
  constitutional executive-clemency and paroling authority.
- **Publication**: the Board's **annual reports** (one PDF per fiscal year),
  each a narrative-plus-statistics report of clemency/parole decision activity.
- **Listing page (scraped)**:
  <https://pap.georgia.gov/office-communications-news-publications-and-events/publications/annual-reports>
- **Grain**: statewide (Georgia), annual (fiscal year, July 1 → June 30).
- The listing page has **no stable URL template** — links are a mix of
  `/document/document/<slug>/download` (newer) and `/media/<id>/download` (some
  years), and the slugs are irregular (the FY2023 slug literally embeds
  `UNPUBLISHED-document--DO-NOT-SHARE-this-URL`). The downloader therefore
  **scrapes the listing HTML**, takes every anchor whose href contains
  `/download`, and maps each to a fiscal year from its "Annual Report YYYY"
  link text.

## Retrieval

- **Downloaded**: 2026-07-04 (UTC) by
  `src/etl/criminal_justice/pardons_paroles/parole_decisions/download.py`.
- **Invocation**:
  `uv run python -m src.etl.criminal_justice.pardons_paroles.parole_decisions.download`
  (re-runnable; skip-if-present idempotency; `--refresh` re-fetches all).
- **Method**: `requests.Session` (User-Agent
  `georgia-civic-data-bronze-etl/1.0 (+https://georgiacivicdata.org; shane.j.orr@gmail.com)`),
  atomic streamed writes (`.part` → `replace`), 1 s politeness delay between
  downloads. PDFs stored **verbatim** — no re-encoding.
- **Coverage**: FY2001–FY2025, **24 distinct fiscal years** (25 files).
  - **FY2015 is missing from the source** (the listing page omits it — not a
    download failure).
  - **FY2016 is listed twice**: a standard report (`annual_report_fy2016.pdf`,
    44 pp) and a "2-page spread" 2-up variant
    (`annual_report_fy2016_spread.pdf`, 23 pp) with identical content. Both are
    kept; the spread is provenance-only.

### Resolved per-fiscal-year download URLs (as scraped 2026-07-04)

| Fiscal year | Bronze file | Source URL |
|---|---|---|
| FY2025 | annual_report_fy2025.pdf | https://pap.georgia.gov/document/document/pardons-paroles-ar-2025-d12-1pdf/download |
| FY2024 | annual_report_fy2024.pdf | https://pap.georgia.gov/document/document/pardons-paroles-ar-2024i3-dec-30pdf/download |
| FY2023 | annual_report_fy2023.pdf | https://pap.georgia.gov/document/document/pardons-paroles-ar-2023-finalpdf--UNPUBLISHED-document--DO-NOT-SHARE-this-URL--/download |
| FY2022 | annual_report_fy2022.pdf | https://pap.georgia.gov/media/13351/download |
| FY2021 | annual_report_fy2021.pdf | https://pap.georgia.gov/document/document/state-board-pardons-and-paroles-fy21-annual-report/download |
| FY2020 | annual_report_fy2020.pdf | https://pap.georgia.gov/media/13366/download |
| FY2019 | annual_report_fy2019.pdf | https://pap.georgia.gov/document/document/fy19-annual-report/download |
| FY2018 | annual_report_fy2018.pdf | https://pap.georgia.gov/media/12566/download |
| FY2017 | annual_report_fy2017.pdf | https://pap.georgia.gov/document/document/annual-report-2017/download |
| FY2016 | annual_report_fy2016.pdf | https://pap.georgia.gov/document/document/annual-report-2016/download |
| FY2016 (spread) | annual_report_fy2016_spread.pdf | https://pap.georgia.gov/document/document/annual-report-2016-2-page-spread/download |
| FY2015 | — **missing from source** — | (no link on the listing page) |
| FY2014 | annual_report_fy2014.pdf | https://pap.georgia.gov/document/document/annual-report-2014/download |
| FY2013 | annual_report_fy2013.pdf | https://pap.georgia.gov/document/document/annual-report-2013/download |
| FY2012 | annual_report_fy2012.pdf | https://pap.georgia.gov/document/document/annual-report-2012/download |
| FY2011 | annual_report_fy2011.pdf | https://pap.georgia.gov/document/document/annual-report-2011/download |
| FY2010 | annual_report_fy2010.pdf | https://pap.georgia.gov/document/document/annual-report-2010/download |
| FY2009 | annual_report_fy2009.pdf | https://pap.georgia.gov/document/document/annual-report-2009/download |
| FY2008 | annual_report_fy2008.pdf | https://pap.georgia.gov/document/document/annual-report-2008/download |
| FY2007 | annual_report_fy2007.pdf | https://pap.georgia.gov/document/document/annual-report-2007/download |
| FY2006 | annual_report_fy2006.pdf | https://pap.georgia.gov/document/document/annual-report-2006/download |
| FY2005 | annual_report_fy2005.pdf | https://pap.georgia.gov/document/document/annual-report-2005/download |
| FY2004 | annual_report_fy2004.pdf | https://pap.georgia.gov/document/document/annual-report-2004/download |
| FY2003 | annual_report_fy2003.pdf | https://pap.georgia.gov/document/document/annual-report-2003/download |
| FY2002 | annual_report_fy2002.pdf | https://pap.georgia.gov/document/document/annual-report-2002/download |
| FY2001 | annual_report_fy2001.pdf | https://pap.georgia.gov/document/document/annual-report-2001/download |

> These per-year URLs are **not stable** (Drupal media/document IDs and slugs
> change when the agency re-uploads). Re-acquisition should always re-scrape the
> listing page rather than reuse these URLs — that is exactly what `download.py`
> does.

## Files

- `annual_report_fy{YYYY}.pdf` — one statewide fiscal-year annual report,
  verbatim (canonical bronze artifact).
- `annual_report_fy2016_spread.pdf` — the FY2016 2-up "spread" variant
  (identical content to `annual_report_fy2016.pdf`; kept for provenance).
- `bronze-data-structure.md`, `_provenance.md` — documentation (excluded from
  checksums/ingestion).

## License / Attribution

- **No license, copyright notice, or terms of use is posted** for these reports
  on the SBPP publications page (the only "license"/"copyright" strings in the
  page HTML belong to the Font Awesome icon library, not the content).
- As **publications of a Georgia state agency**, the annual reports are public
  records under the Georgia Open Records Act (O.C.G.A. § 50-18-70 et seq.) and
  are distributed by the agency for public use.
- **Attribute to**: *Georgia State Board of Pardons and Paroles, Annual Report
  FY{YYYY}* (pap.georgia.gov). Carry this attribution into the topic contract's
  `usage` when the topic ships.

## Caveats

- **PDF extraction friction.** These are narrative/design PDFs, not tabular
  data. Back-of-book text tables extract with `pdftotext -layout` (poppler),
  but grid tables and figure values need a Python-native extractor
  (`pdfplumber`) — **`tabula`/`camelot` cannot run here: Java/JRE is not
  installed**. Many headline numbers (parole population, cost-per-day, the
  Era-3 infographic tiles) live **inside figure/chart labels**, which linear
  text extraction mangles; expect substantial manual verification at transform
  time. See `bronze-data-structure.md` → "Report / Table Structure" and "ETL
  Considerations".
- **Layout drift across three eras** (classic text ≈ FY2001–FY2009, magazine
  ≈ FY2010–FY2014, post-HB310 infographic FY2016–FY2025). Metric row labels
  change across eras — build a per-era label→canonical-metric crosswalk.
- **2015 HB 310 break.** House Bill 310 (effective 2015-07-01, start of FY2016)
  moved day-to-day **parole supervision** to the new **Department of Community
  Supervision (DCS)**. Pre-2015 reports carry a richer, self-contained
  supervision series (population, caseloads, field revocations) that is **not
  directly comparable** to the post-2015 clemency-decision-focused reports. Do
  not pool the supervision series across the FY2015 boundary without a
  coverage/definition flag.
- **FY2015 missing** and **FY2016 duplicated** (standard + spread) — see
  Retrieval above.
- **Statewide grain only** — no county detail, so this topic does not
  participate in county-level cross-dataset linking (it publishes a single
  state row per fiscal year).
