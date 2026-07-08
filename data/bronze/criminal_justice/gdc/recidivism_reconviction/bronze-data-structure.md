# recidivism_reconviction — Bronze Data Structure

## Overview

- Topic: recidivism_reconviction
- Source: gdc (Georgia Dept. of Corrections, Office of Data Management & Research — Statistical Trends standing reports)
- Files: 2 PDF files — one Calendar-Year edition, one Fiscal-Year edition (both single-page)
- Unreadable files: none (both text-extractable; `pdftotext -layout` recovers the full matrix)
- Year representation: **column headers inside the table** — one column per release-cohort year. CY edition: calendar years `2011`–`2022` (12 columns). FY edition: fiscal years `2012`–`2023` (12 columns). The report date is printed in the header (`Date: 01/06/2026` CY / `Date: 07/01/2026` FY). Each year is a **release cohort**: the rate is the share of inmates released in that year who were reconvicted of a new felony within 3 years.
- Filename-to-data year offset: n/a — filenames (`_cy` / `_fy`) carry no year; years are the column headers.
- Detail levels: **statewide only**, disaggregated by **facility type** (of release) and **sex**. No county or facility-instance grain.
- Percentage scale: **rates are percentages on a 0–100 scale** (e.g. `26.90` = 26.90%), one decimal-to-two-decimal precision. In gold these should be stored as a proportion `[0,1]` (divide by 100) or kept as a `0–100` percent with an explicit `unit`/scale note — see ETL considerations.
- Checksums generated: 2026-07-04

## Source Provenance

Full detail in `_provenance.md` (same directory), summarized here:

- **Source URL**: GDC Statistical Trends page <https://gdc.georgia.gov/organization/about-gdc/agency-activity/research-and-reports/standing-reports/statistical-trends>. The `/media/{id}/download` anchors 301-redirect to stable slugs: `https://gdc.georgia.gov/document/statistical-trend-reports/3-year-reconviction-calendar-years/download` (CY) and `.../3-year-reconviction-fiscal-years/download` (FY).
- **Retrieved**: 2026-07-04 (UTC)
- **Method**: scripted fetch — `src/etl/criminal_justice/gdc/download.py` (scrapes the page by link text, follows the redirect, stores the PDF verbatim).

## File Checksums

Generated: 2026-07-04

| File | SHA-256 |
|------|---------|
| reconviction_3yr_cy.pdf | e0cd1509c09be2f5f2a65d464b268bdfb4ec5fd263f81baa0aba87cc7c690d36 |
| reconviction_3yr_fy.pdf | be4c32f477c35683237f525002482cf981064ff683338600c8766389607d527a |

Note: `_provenance.md` and this file are documentation artifacts, excluded from ingestion.

## Summary

Georgia's **canonical recidivism metric**: the **3-year felony reconviction rate** — the percentage of an inmate release cohort that is reconvicted of a new felony within three years of release. Published as a statewide time series broken down by **release facility type** (private prisons, state prison/IBCs, county CI, transition centers) and by **sex** (male-inclusive "all" rows plus a female block), in parallel Calendar-Year and Fiscal-Year editions spanning ~2011–2023 cohorts. This is **reconviction, not re-arrest** — do not pool with re-arrest or re-incarceration recidivism measures.

## Report / Table Structure

> **PDF, not CSV.** The standard bronze "Eras / categorical / suppression" subsections **do not apply** — see the table description below. PDF table extraction (`camelot`/`pdfplumber`/`tabula-py`) is required at transform time; **`tabula-py` needs a Java runtime** (not installed as of 2026-07-04) — use `camelot`/`pdfplumber` (pure-Python) or, for this simple single-page matrix, `pdftotext -layout` + column parsing. Both files are born-digital (OpenPDF), so extraction is clean.

Both PDFs share one layout: **1 A4 page, one matrix**: rows = facility type / sex breakdown, columns = 12 cohort years. Values are the 3-year reconviction rate (percent) for that breakdown × cohort.

| Report | File | Pages | Period | Cohort-year columns |
|--------|------|-------|--------|---------------------|
| 3-Year Reconviction — Calendar Years | `reconviction_3yr_cy.pdf` | 1 | Calendar Year | 2011, 2012, …, 2022 (12) |
| 3-Year Reconviction — Fiscal Years | `reconviction_3yr_fy.pdf` | 1 | Fiscal Year | 2012, 2013, …, 2023 (12) |

**Row labels (breakdown axis — the "Facility Type" stub column):**

| Row | Grouping | Notes |
|-----|----------|-------|
| `All inmate facilities **` | all-facilities rollup | `**` footnote marker (definition not printed on the page; denotes the aggregate/all-facility line). Headline statewide rate. |
| `Private prisons` | facility type | |
| `State prison, IBCs` | facility type | IBC = Inmate Boot Camp |
| `County CI` | facility type | CI = County Correctional Institution |
| `Transition centers` | facility type | |
| `All Female Facilities **` | female rollup | `**` marker; female-only aggregate |
| `Female State prison, IBCs` | facility type × female | |
| `Female Transition centers` | facility type × female | |

(The FY edition lower-cases some labels — `All female facilities`, `Female state prison, IBCs` — same meaning; normalize casing in transform.)

**Cell values**: reconviction rate as a percent, `0–100` scale, e.g. `26.90`, `31.10`, `9.70`. Every cell is populated in both files — **no suppression markers and no missing cells** observed.

## ETL Considerations

1. **PDF extraction.** Single-page 8-row × 12-year matrix; the simplest of the GDC suite. Reconcile a few cells against the `pdftotext -layout` dump as QA. No page continuation.
2. **Statewide grain, facility-type + sex breakdown.** No county/FIPS. The natural gold grain is `year × reporting_period × facility_type × sex` (or fold sex into the facility-type label if kept literal). Decide whether the two rollup rows (`All inmate facilities`, `All Female facilities`) become an `all`-style total or stay separate literal categories — they are aggregates, so treat as the "all facilities" roll-up, not as mutually-exclusive facility types you can sum.
3. **Percent scale.** Values are `0–100` percentages. Per data-cleaning-standards, either store as a proportion `[0,1]` (divide by 100, `unit: proportion`) or keep as percent with an explicit scale note. A reconviction *rate* is the key metric — there is no accompanying numerator/denominator count in these PDFs (cohort N is not published here).
4. **"3-Year" = fixed 3-year follow-up window on a release cohort.** The year column is the *release* year; the rate reflects reconvictions observed within the following 3 years. The most recent cohorts therefore require ~3 years of maturity — GDC only publishes cohorts with a complete 3-year window (latest CY cohort 2022, latest FY cohort 2023).
5. **Reconviction ≠ re-arrest / re-incarceration.** This is felony *reconviction*. Do not pool with any re-arrest, technical-revocation, or return-to-custody recidivism series. State this in the contract `limitations`.
6. **CY ≠ FY.** Calendar-year and fiscal-year cohorts are different definitions of the release window; keep a `reporting_period` categorical and never merge them.
7. **`**` footnote.** The `**` marker on the two rollup rows has no printed definition on the page. Preserve the fact that these are aggregate lines; if a definition is needed, cross-check GDC's annual statistical report or a fuller reconviction publication.
8. **Label casing/whitespace drift between editions** (`All Female Facilities` vs `All female facilities`; `County CI`) — normalize to a canonical facility-type vocabulary in transform; record the mapping on the manifest.

## Gold Schema Classification

Best-effort, from the observed matrix (fact grain: statewide × cohort-year × reporting-period × facility-type × sex).

| Bronze element | Gold Role | Gold Name | Notes |
|----------------|-----------|-----------|-------|
| column header year | fact_key | year | int cohort/release year |
| CY vs FY edition | fact_categorical | reporting_period | `calendar` / `fiscal` |
| row stub (facility part) | fact_categorical | facility_type | `all` / `private_prison` / `state_prison_ibc` / `county_ci` / `transition_center`; normalize casing |
| row stub (female block) | fact_key or categorical | sex / demographic | female rows → `female`; the non-female rows are all-sex → `all`; map to the demographics dimension if using `demographic` |
| cell value | fact_metric | reconviction_rate_3yr | `unit: proportion` (÷100) or percent w/ scale note; **key_metric**; no published numerator/denominator |
| geography | fact_key | county_fips = NULL | statewide only — all rows are state detail level |
