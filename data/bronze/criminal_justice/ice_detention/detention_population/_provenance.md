# Provenance — criminal_justice / ice_detention / detention_population

**Retrieved**: 2026-07-02 (UTC), via
`uv run python -m src.etl.criminal_justice.ice_detention.detention_population.download`
(requests with a desktop-browser User-Agent; ice.gov is Akamai-fronted and rejects
default UAs). Workbook and DDP file URLs are **scraped from the source pages on every
run — never hardcoded** (both sites use unstable/rotating file URLs).

Source blueprint: `data_sources/criminal_justice/criminal-justice-data-review.md`,
Tier 1 #8 (ICE detention — ice.gov statistics + Deportation Data Project).

## Feed 1 — ICE official detention statistics workbooks

- **Source page**: <https://www.ice.gov/detain/detention-management>
- **Publisher**: U.S. Immigration and Customs Enforcement (federal government work —
  public domain, 17 U.S.C. § 105). Attribution: U.S. ICE, Detention Management statistics.
- One XLSX per fiscal year, refreshed ~biweekly during the active FY. Facility-level
  sheets include facility name / address / city / state / AOR, ADP, criminality mix,
  ALOS, etc. FY2020 onward downloaded (the page also links FY2019, out of scope).
- File naming: `ice_detention_stats_fy{YYYY}_{snapshot-date}.xlsx` — snapshot date is
  the date embedded in the ICE filename when present (e.g. `FY26_…_04092026.xlsx` →
  `2026-04-09`), otherwise the UTC download date.

| File | Size | SHA-256 |
|---|---|---|
| ice_detention_stats_fy2020_2026-07-02.xlsx | 135,598 | 2c30cee5f1cd4b26ab1aa8c9ddf3e23b7e12929a201e0d1841f755c078d26067 |
| ice_detention_stats_fy2021_2026-07-02.xlsx | 133,697 | 66ce2cc482f72082c626eab08f45b8686c5ab3d7c6b8d758cc2bd6b3fcecc697 |
| ice_detention_stats_fy2022_2026-07-02.xlsx | 195,925 | b29a5d4a48221c839c18370baece46cf4b89a3c3dd84c173f7f145f627cf9e82 |
| ice_detention_stats_fy2023_2026-07-02.xlsx | 234,070 | 12185efdb1215b9e3242c9f4f4eda5b856ce3fd4978917d105e1a4edf4226129 |
| ice_detention_stats_fy2024_2026-07-02.xlsx | 242,258 | a177b8bdfe5eb391ed458ed84de810146a019cb25898387c27178357e20b7e30 |
| ice_detention_stats_fy2025_2025-09-24.xlsx | 1,566,719 | 3b9e2d626b1e249b2c87539554758333b27bc0da64a37e5dac99944a210c0782 |
| ice_detention_stats_fy2025_2026-07-02.xlsx | 1,566,719 | 3b9e2d626b1e249b2c87539554758333b27bc0da64a37e5dac99944a210c0782 |
| ice_detention_stats_fy2026_2026-04-09.xlsx | 248,450 | bbf3a29014d686f7eccce397804c9fdba7d2bf9b5fcea0180bc98443ffd4fbed |

Source URLs at retrieval time (subject to change):
`https://www.ice.gov/doclib/detention/FY20-detentionstats.xlsx`,
`…/FY21-detentionstats.xlsx`, `…/FY22-detentionStats.xlsx`, `…/FY23_detentionStats.xlsx`,
`…/FY24_detentionStats.xlsx`, `…/FY25_detentionStats.xlsx`,
`…/FY25_detentionStats09242025.xlsx`, `…/FY26_detentionStats_04092026.xlsx`.

Note: the two FY2025 files are byte-identical — the undated FY25 URL now serves the
final end-of-FY (2025-09-24) snapshot. Both are kept to document both URLs.

## Feed 2 — Deportation Data Project (DDP) processed ICE detention data (`ddp/`)

- **Source page**: <https://deportationdata.org/data/processed/ice.html>
- **Method**: files are hosted as GitHub raw links under
  `github.com/deportationdata/{ice,ice-detention-management}`; Parquet flavor chosen
  (DDP also offers XLSX/DTA/SAV). No access gate. Sizes HEAD-checked before download;
  anything > ~8 GB would be skipped (largest actual file: 250 MB — nothing skipped).
- **Scope**: detention-focused files only. The arrests / detainers / removals /
  encounters suite on the same page was deliberately **not** downloaded.
- **License**: DDP publishes under **CC-0 (no rights reserved)** (footer of the source
  page). Underlying records are US government data obtained by FOIA.
- **Required citation (exact wording from the DDP page)** — record-level FOIA data
  (detention stays / stints / facility daily population):
  > "government data provided by ICE in response to a FOIA request, processed by the
  > Deportation Data Project, and analyzed by [your organization]."
  For the detention-management spreadsheet datasets (`detention-management.xlsx`):
  > "government statistics published by ICE, collated by the Deportation Data Project,
  > and analyzed by [your organization]."

| File | Size | SHA-256 |
|---|---|---|
| ddp/detention-stays-latest.parquet | 109,997,291 | dbe81de61de8cfb4d0e6ec4c1c6eb182c2c6b211206611b3702efe5b02215bb0 |
| ddp/detention-stints-latest.parquet | 250,462,537 | 252c211590b9192356ccc6a2f497e1ddbae70e291f50efddec5ea8ad34d73dff |
| ddp/facilities-daily-population-latest.parquet | 1,347,003 | 649722ae79088a91aab26b8f4f7889a71e12e56a36ee102213ba632293312017 |
| ddp/detention-management.xlsx | 5,425,585 | 514225d3fe80b3ebed9bcc8d7ab23cb0a26e0768169bbc1602dfc3e7d103f43c |
| ddp/ddp_codebook.html | 315,176 | d5ce7d0f9d2d5ed81db3b1152795d1c331ed590fb6712093139b7dcab0d4fed0 |
| ddp/ddp_codebook-facilities.html | 81,234 | 1736a27db1c549a520d6439d9961d77cc23bd8235655095a65deeed933813825 |
| ddp/ddp_codebook-facilities-daily-population.html | 67,819 | 32ab5c3e3982fde0cff354f531683843db596d78c998575e1e084ca22d83519b |

- `detention-stays-latest.parquet` — one row per detention *stay* (DDP-recommended for
  individual-level analysis); 70 columns; release covers ICE enforcement actions
  through early March 2026.
- `detention-stints-latest.parquet` — one row per facility *stint* (DDP-recommended for
  facility-level analysis; one person can have multiple stints per stay via transfers);
  61 columns.
- `facilities-daily-population-latest.parquet` — daily headcounts per facility
  (9 columns; dates through 2026-03-10 at retrieval).
- `detention-management.xlsx` — DDP's collation of all ICE detention-management
  spreadsheets into one workbook (one sheet per dataset, with `file_date`/`pull_date`
  columns), smoothing the cross-FY layout drift of Feed 1.
- Codebooks are the DDP documentation pages archived as HTML
  (`https://deportationdata.org/docs/ice/codebook*.html`).

## Georgia verification (2026-07-02)

- FY2026 workbook, "Facilities FY26" sheet: **STEWART DETENTION CENTER** (Lumpkin, GA)
  and **FOLKSTON MAIN IPC / FOLKSTON ANNEX IPC / FOLKSTON D RAY ICE PROCESSING CTR**
  (Folkston, GA) all present.
- DDP `detention-stints-latest.parquet`: Stewart 40,756 stints; Folkston Main 20,343;
  Folkston Annex 7,539; Folkston D Ray 5,310.
- DDP `facilities-daily-population-latest.parquet`: 1,257 daily rows for each of the
  4 GA facilities.

## Caveats

- **Workbook layout drift**: sheet names, sheet sets, and column layouts change across
  fiscal years (e.g. FY20 has 5 sheets, FY22+ add ICLOS/bond/segregation sheets) —
  version the parser per FY.
- **ICE workbook URLs and content are unstable**: the current-FY workbook is
  overwritten ~biweekly at the same URL; re-runs on later dates capture new dated
  snapshots. Prior-FY workbooks can also be silently revised.
- **DDP release cadence is irregular** (tracks FOIA productions), and DDP itself flags
  reliability concerns in recent releases: hospital/medical stints omitted, some
  `case_category` and release-reason values redacted, encounters/removals reliability
  questions (see the source page and archived codebooks).
- **PII**: DDP stays/stints are individual-level records — they stay in bronze only.
  **Aggregate to facility-month (or coarser) before gold.**
- FY totals in workbooks are fiscal-year (Oct–Sep) year-to-date snapshots, not calendar
  year.
