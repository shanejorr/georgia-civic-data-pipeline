# inmate_releases_county — Bronze Data Structure

## Overview

- Topic: inmate_releases_county
- Source: gdc (Georgia Dept. of Corrections, Office of Data Management & Research — Statistical Trends standing reports)
- Files: 2 PDF files — one Calendar-Year edition, one Fiscal-Year edition
- Unreadable files: none (both are text-extractable PDFs; a `pdftotext -layout` pass recovers the full table)
- Year representation: **column headers inside the table**, not the filename. Each edition is a wide table with **five year columns** covering a rolling window of the last five complete years. CY edition: `2021 2022 2023 2024 2025`. FY edition: `2022 2023 2024 2025 2026` (state fiscal year runs Jul 1 – Jun 30; "FY2026" = Jul 2025 – Jun 2026). The run date is printed in the header (`Run on 05-JAN-26` CY / `Run on 01-JUL-26` FY) and the PDF `Title` names the newest year (`Inmate Releases by County - CY2025` / `- FY2026`).
- Filename-to-data year offset: n/a — the descriptive filenames (`_cy` / `_fy`) carry no year; the years live in the table's column headers.
- Detail levels: **county of release ("home county")** — all 159 Georgia counties — plus three statewide roll-up / residual rows (see Report / Table Structure). No sub-county or facility grain.
- Percentage scale: no percentages. The single metric is a **count** of prison releases (integer; thousands separators on the large residual/total rows, e.g. `1,022` / `13,460`).
- Checksums generated: 2026-07-04

## Source Provenance

Full detail in `_provenance.md` (same directory), summarized here:

- **Source URL**: GDC Statistical Trends page <https://gdc.georgia.gov/organization/about-gdc/agency-activity/research-and-reports/standing-reports/statistical-trends>. The page's `/media/{id}/download` anchors 301-redirect to stable per-report slugs: `https://gdc.georgia.gov/document/statistical-trend-reports/inmate-release-county-calendar-year/download` (CY) and `.../inmate-release-county-fiscal-year/download` (FY).
- **Retrieved**: 2026-07-04 (UTC)
- **Method**: scripted fetch — `src/etl/criminal_justice/gdc/download.py` (re-runnable; scrapes the Statistical Trends page for the anchors by link text, never hardcodes media IDs, follows the redirect, and stores the PDF verbatim).

## File Checksums

Generated: 2026-07-04

| File | SHA-256 |
|------|---------|
| inmate_release_by_county_cy.pdf | 2f4769d4669c12fd080c44dfc6f16ad3ed8e406230f53e64e5cdf6531e1cd5d2 |
| inmate_release_by_county_fy.pdf | c36c65f7c3fb383e9e57342035ec2fae5b2e19fb71966aa9bbba458e2bad0fb7 |

Note: `_provenance.md` and this file are documentation artifacts, excluded from ingestion.

## Summary

Counts of **prison releases by the inmate's home county of record**, published by GDC as two parallel trend reports: a **Calendar-Year** edition and a **Fiscal-Year** edition, each showing the five most recent complete years side by side across all 159 counties. The measure is "how many people GDC released back to each Georgia county" in each year — the county-mappable complement to the statewide population and recidivism trends. This is *release* counts (throughput), not a stock/point-in-time population.

## Report / Table Structure

> **PDF, not CSV.** The standard bronze "Eras / categorical / suppression" subsections **do not apply** — see the table descriptions below. PDF table extraction (`camelot` lattice/stream or `tabula-py`) is required at transform time; **`tabula-py` needs a Java runtime installed** (not present in this environment as of 2026-07-04), or use `camelot`/`pdfplumber` (pure-Python) instead. `pdftotext -layout` cleanly recovers the columns for QA.

Both PDFs share one layout: **4 A4 pages, one wide table continued across pages**, page header repeated on each page.

| Report | File | Pages | Header line | Year columns | County rows |
|--------|------|-------|-------------|--------------|-------------|
| Inmate Release by County — Calendar Year | `inmate_release_by_county_cy.pdf` | 4 | "Total prison releases by home county for the past five complete calendar years" | 2021, 2022, 2023, 2024, 2025 | 159 + 3 residual |
| Inmate Release by County — Fiscal Year | `inmate_release_by_county_fy.pdf` | 4 | "Total prison releases by home county for the past five complete fiscal years" | 2022, 2023, 2024, 2025, 2026 | 159 + 3 residual |

**Effective columns** (identical in both editions):

| Column | Description |
|--------|-------------|
| Home County | County-of-release label, prefixed with GDC's own 3-digit sequential county code, e.g. `001 - Appling County` … `159 - Worth County`. The code is GDC's alphabetical index (Appling=001 … Worth=159), **not** a FIPS code — map the county *name* to FIPS via `add_county_fips`. |
| {year} ×5 | Integer count of prison releases whose home county = that row, in that calendar/fiscal year. Large values carry a thousands comma (`13,460`). |

**Special / non-county rows** (appear once, after county 159, on the last page):

| Row label | Meaning | Gold handling |
|-----------|---------|---------------|
| `999 - Other Custody/Out Of State` | Releases whose home county is out-of-state or another custody category | not a Georgia county — map to a residual bucket (NULL `county_fips`) or drop; do **not** force to a FIPS |
| `Unknown, not reported` | Releases with no home county recorded (large: ~900–1,300/yr) | residual / NULL `county_fips`; keep the count for reconciliation |
| `Total` | Statewide total releases for the year (~12,900–13,700/yr) | state-detail-level row (NULL `county_fips`); equals sum of the 159 counties + the two residual rows |

No missing/suppressed cells were observed — every county has an integer in every year column (small counties show single digits, e.g. Webster `1`–`3`; genuine zeros appear, e.g. Chattahoochee `0` in 2025). There are **no suppression markers**.

## ETL Considerations

1. **PDF extraction with per-page QA.** Four-page continued table; the header row repeats on each page and must be de-duplicated. Reconcile the extracted 159 county values + 2 residual rows against the printed `Total` for each year as a validation check (they sum exactly).
2. **County code is GDC's, not FIPS.** The `001`–`159` prefix is GDC's alphabetical index. Resolve to 5-digit FIPS from the **county name** via `src/utils/crosswalks.add_county_fips` + `COUNTY_NAME_OVERRIDES`; do not assume the GDC index maps to FIPS ordering. Record any unmatched names as unmapped categoricals on the manifest (blocking), never silently NULL.
3. **Rolling five-year window — do not treat editions as an append-only archive.** Each new run *drops the oldest year and adds the newest*; re-downloading later replaces the file with a shifted window. Overlapping years (e.g. CY2022 appears in both this edition and future editions) should reconcile, but the transform must key on the *year value in the column header*, not the file, and de-dup on `(county, year, cy_or_fy)`.
4. **CY vs FY are different reporting periods, not the same series.** Keep a `reporting_period` categorical (`calendar` / `fiscal`) in the grain — a CY2025 count and an FY2025 count are different 12-month windows and must not be pooled or summed.
5. **Home county = county of release/record, not county of the offense or the releasing facility.** Document this in the contract; it is the decedent's/inmate's county of residence attribution, which is what makes it county-mappable.
6. **Residual rows are not counties.** `Other Custody/Out Of State` and `Unknown, not reported` carry real, sizeable counts — preserve them for statewide reconciliation but route them to a NULL-`county_fips` residual, never to a FIPS.
7. **Counts only.** No rates, no demographics, no offense breakdown in these PDFs (those live in other GDC "Profiles of Inmate Releases" reports, out of scope here).

## Gold Schema Classification

Best-effort, from the observed table columns (fact grain: county-of-release × year × reporting-period).

| Bronze element | Gold Role | Gold Name | Notes |
|----------------|-----------|-----------|-------|
| `Home County` (name part) | fact_key | county_fips | 5-digit string FK to counties dimension, resolved from the county name; residual rows → NULL |
| `Home County` (`001`–`159` code) | not_in_gold | — | GDC alphabetical index; superseded by FIPS |
| {year} column header | fact_key | year | int; taken from the column header, not the filename |
| CY vs FY edition | fact_categorical | reporting_period | `calendar` / `fiscal` — distinguishes the two 12-month windows; part of the grain |
| cell value | fact_metric | releases | `unit: count`; integer prison releases; **key_metric** |
| `Total` row | not_in_gold (state row) | — | statewide detail-level row (NULL county_fips) — derivable; keep only for validation reconciliation |
| `999 - Other Custody/Out Of State`, `Unknown, not reported` | fact_key (residual) | county_fips = NULL | non-county residual buckets; counts preserved, geography NULL |
