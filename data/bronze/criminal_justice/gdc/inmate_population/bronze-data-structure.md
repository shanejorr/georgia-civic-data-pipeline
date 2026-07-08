# inmate_population — Bronze Data Structure

## Overview

- Topic: inmate_population
- Source: gdc (Georgia Dept. of Corrections, Office of Data Management & Research — Statistical Trends standing reports)
- Files: 1 PDF file — "Year-End Population since 1925"
- Unreadable files: none (text-extractable; `pdftotext -layout` recovers the full year/count matrix. The lower half of the page is a bar chart — a picture of the same series, not a separate data table.)
- Year representation: **`Year` label columns inside a data matrix**, one row per year, `1925`–`2024` (100 values). The table is printed as **five side-by-side `Year | Count` column-blocks** for compactness (1925–1944, 1945–1964, 1965–1984, 1985–2004, 2005–2024) — a layout artifact, not five different series.
- Filename-to-data year offset: n/a — the file covers the full 1925–present span; no year in the filename.
- Detail levels: **statewide only** — a single year-end count for the whole Georgia Prison System. No county, facility, or demographic grain.
- Percentage scale: no percentages. The single metric is a **count** of inmates (integer; thousands separators, e.g. `3,007` … `50,107`).
- Checksums generated: 2026-07-04

## Source Provenance

Full detail in `_provenance.md` (same directory), summarized here:

- **Source URL**: GDC Statistical Trends page <https://gdc.georgia.gov/organization/about-gdc/agency-activity/research-and-reports/standing-reports/statistical-trends>. The `/media/{id}/download` anchor 301-redirects to the stable slug `https://gdc.georgia.gov/document/statistical-trend-reports/year-end-pop-1925/download`.
- **Retrieved**: 2026-07-04 (UTC)
- **Method**: scripted fetch — `src/etl/criminal_justice/gdc/download.py` (scrapes the page by link text, follows the redirect, stores the PDF verbatim).

## File Checksums

Generated: 2026-07-04

| File | SHA-256 |
|------|---------|
| year_end_population_since_1925.pdf | 817ede7ca7e9e0b4db75f2fc62e8ac1d4c841e25fc7cba8f856b1b229f444de8 |

Note: `_provenance.md` and this file are documentation artifacts, excluded from ingestion.

## Summary

The **longest-run statewide series** in the GDC suite: **year-end inmate counts of the Georgia Prison System, 1925 to present** (currently through 2024). Scope: state prisoners held in state prisons, inmate boot camps, county prisons, transition centers, and private prisons — **excluding** probationers in detention/diversion/probation boot camps and **excluding** inmates held in county jails. The century-long trend (from ~3,000 in 1925, through the truth-in-sentencing ramp of the mid-1990s, to ~50,000 today) is the headline stock/point-in-time prison-population measure.

## Report / Table Structure

> **PDF, not CSV.** The standard bronze "Eras / categorical / suppression" subsections **do not apply** — see the table description below. PDF table extraction (`camelot`/`pdfplumber`/`tabula-py`) is required at transform time; **`tabula-py` needs a Java runtime** (not installed as of 2026-07-04) — use `camelot`/`pdfplumber` (pure-Python) or `pdftotext -layout` + parsing. **Extract from the data table only, never from the bar chart** (the chart is a rendered picture of the same numbers).

Single **US-letter page**. Top: a title/scope/sources block. Middle: the data matrix. Bottom: a bar chart (ignore for extraction).

**Scope / sources block (printed on the page, verbatim):**

- "Year-end counts of inmates of the Georgia Prison System, 1925 to present."
- "Includes state prisoners in state prisons, inmate boot camps, county prisons, transition centers, & private prisons."
- "Does not include probationers in detention centers, diversion centers, or probation boot camps, nor inmates in county jails."
- **Sources / methodology by era** (this is a *methodological break*, document it):
  - **1925–1979**: National Corrections Reporting Program (NCRP).
  - **1980–1999**: December **average daily populations** (ADP).
  - **2000 forward**: Population (Head Count) report for **December 31**.
- "Updated annually, in first week of January."

**Data matrix** — effective columns after un-pivoting the five printed blocks:

| Column | Description |
|--------|-------------|
| Year | Calendar year, `1925`–`2024` (100 rows) |
| Count | Year-end statewide inmate count (integer; thousands comma). Note the definition changes by era per the sources block above. |

Sanity anchors from the extract: 1925 = `3,007`; 1994 = `33,175` (truth-in-sentencing era begins); 2019 = `53,943`; 2020 = `46,132` (COVID drop); 2024 = `50,107`. No missing years, no suppression markers.

## ETL Considerations

1. **PDF extraction — un-pivot the 5 print blocks.** The 100 years are laid out as five side-by-side `Year | Count` blocks to fit one page; the transform must stack them into a single tidy `year, count` series (100 rows), **not** read them as five columns. Reconcile a handful of known anchors (e.g. 2024 = 50,107) as QA. Ignore the bar chart entirely.
2. **Methodological break — version, do not smooth.** The series is **not** a single consistent measure: 1925–1979 = NCRP; 1980–1999 = December **ADP** (an average, not a point-in-time count); 2000+ = **Dec 31 head count**. Carry a `count_method` categorical (or at minimum document the break in `limitations`) so users don't treat the ADP era as directly comparable to the head-count era. Per criminal_justice domain conventions, "version methodological breaks, never pool across them."
3. **Scope exclusions matter for cross-source joins.** Excludes county-jail inmates and probation-supervised populations — do **not** reconcile against `jails/jail_population` (county jails) or parole/probation supervision counts as if they were the same denominator.
4. **Statewide grain only** — no `county_fips`; every row is a state detail-level row.
5. **Count only.** No demographics, offense, sentence-length, or facility breakdown in this report (those live in other GDC statistical reports, out of scope here).
6. **Annual cadence, first week of January.** A refresh adds one new year (`present` = latest complete calendar year-end); the download replaces the PDF and the checksum changes.

## Gold Schema Classification

Best-effort, from the observed matrix (fact grain: statewide × year).

| Bronze element | Gold Role | Gold Name | Notes |
|----------------|-----------|-----------|-------|
| `Year` | fact_key | year | int, 1925–present |
| `Count` | fact_metric | year_end_inmate_population | `unit: count`; **key_metric**; year-end statewide prison population |
| sources-block era | fact_categorical (recommended) | count_method | `ncrp` (1925–1979) / `december_adp` (1980–1999) / `dec31_headcount` (2000+) — encodes the methodological break |
| geography | fact_key | county_fips = NULL | statewide only — state detail level |
| bar chart | not_in_gold | — | rendered picture of the same series; never extracted |
