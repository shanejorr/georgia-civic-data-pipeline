# parole_decisions — Bronze Data Structure

## Overview

- Topic: parole_decisions
- Source: pardons_paroles (Georgia State Board of Pardons and Paroles — annual reports, PDF suite)
- Files: 25 PDF annual reports covering **FY2001–FY2025** (24 distinct fiscal years; **FY2015 is missing from the source**, and **FY2016 is published twice** — a standard single-page-per-sheet report plus a "2-page spread" 2-up variant with identical content)
- Unreadable files: none (all 25 are valid PDFs; page-text extractable via `pdftotext -layout`)
- Year representation: **fiscal year, from the report title and filename** (`annual_report_fy{YYYY}.pdf`). No tabular year column — each PDF is one fiscal year. Georgia fiscal years run **July 1 → June 30** (e.g. FY2013 = 2012-07-01 … 2013-06-30). Figures are labeled `FY05`, `FY 2013`, `FY25`, etc. inside the reports.
- Filename-to-data year offset: none — filename fiscal year = the report's fiscal year.
- Detail levels: **statewide only** (single "Georgia" grain). No county or sub-state breakdown — this dataset does not join the counties dimension.
- Percentage scale: reports quote whole-number percents (e.g. "successful completion 73%"); the transform must scale to `[0,1]` proportions per data-cleaning standards.
- Checksums generated: 2026-07-04

## Source Provenance

Full detail in `_provenance.md` (same directory), summarized here:

- **Source URL**: https://pap.georgia.gov/office-communications-news-publications-and-events/publications/annual-reports (listing page scraped; each fiscal year links one PDF via irregular `/document/document/<slug>/download` or `/media/<id>/download` paths — no stable template)
- **Retrieved**: 2026-07-04 (UTC)
- **Method**: scripted scrape + download — `src/etl/criminal_justice/pardons_paroles/parole_decisions/download.py` (re-runnable; re-scrapes the listing page and fetches any missing fiscal-year PDF; `--refresh` re-fetches all). PDFs are kept **verbatim**.

## File Checksums

Generated: 2026-07-04

| File | SHA-256 |
|------|---------|
| annual_report_fy2001.pdf | a1091f027f8cdea8c15ba5df3153671a065fa1e5febed595013237a2a45d4eb6 |
| annual_report_fy2002.pdf | 4c3c69f782c14771079143d7ffdbff68406a49dc0f812bd39c73e745372f0993 |
| annual_report_fy2003.pdf | 47ded77989085ee36073121fccdaf4c7be36a1818940259b65399dc04a637aca |
| annual_report_fy2004.pdf | 6ceec547c325536c80d1ef137a7ff156765314e283e636259cce0cdf63470d6b |
| annual_report_fy2005.pdf | 3c1794a2673bb9f241eec6f650bb0c98153dfe0d36415e4bab5ed254cfa34869 |
| annual_report_fy2006.pdf | bea42b3a0184f8012b7eb2db4db5c2d42b782529b1ab767f566b160a2ba7e53f |
| annual_report_fy2007.pdf | cbfc5c2d1c690e77a0b893285464cfc8353935d2dd4c617d53045c27aa9920e9 |
| annual_report_fy2008.pdf | 4970e396f12446f500ffbade435231a3dc6ebadc7921db04b4acd8a48d4507bc |
| annual_report_fy2009.pdf | 0e2bb0da5a3c6194726189a0311001fef733d30ed974bf082f01088c91da456d |
| annual_report_fy2010.pdf | abcc7d1224ffb1fd382b535761ad6ca0058e800be8ad3b094567ab59ce02f766 |
| annual_report_fy2011.pdf | bc4c6b1a7473d27293be38a795458fab9b1f521ce1f16920ce0e1def9717f020 |
| annual_report_fy2012.pdf | c5f134c9a40d3bffecbea046ddc5c1c7d7074823494293cffee12d4f7603fc97 |
| annual_report_fy2013.pdf | 572da091cf2f18522c8852313ba66130d8321e052fff5215b7b6ebbf9f70aca5 |
| annual_report_fy2014.pdf | 9d9c6f95b71e438c21d1a1525d23b8d788b012cc4f30fbd7083cfeb7669b11da |
| annual_report_fy2016.pdf | be8e46aa5f34a398396ff73207ef60022037d8a8f309cd5439fe16a8fadf3f10 |
| annual_report_fy2016_spread.pdf | e998de79631d03483784431e2c3dfdf11193f4e76b863ba48562e235a77e7bd2 |
| annual_report_fy2017.pdf | c82e2ecd0aa32a16fffcb913b258727c114461a88dd41f61d06937a01b26b042 |
| annual_report_fy2018.pdf | 0bf41df9625ec6613d4ea1b966f2b216ecb37a9c59fc587e528ebb63f315cfcf |
| annual_report_fy2019.pdf | 348e6b6590644d2375251ab6b35be8e382ef39776ce92f36a1f72c21f1b2b2cb |
| annual_report_fy2020.pdf | 9eabde9cf9f4d29f672c83ac042e6d007b16fcddaaa2184aa013dd1603e28682 |
| annual_report_fy2021.pdf | f7ed52a052c1d21147c9606ddec2d31882062addf3d8697183f0eeb2e8042651 |
| annual_report_fy2022.pdf | b1e99884f920fd8f58a712aa042f4dee18d526913412c1abdfa7bf0535db4caf |
| annual_report_fy2023.pdf | dc54445f2acc0ff21fbda8976a770ec8b25b9f383eb3fe90850cee92e4031415 |
| annual_report_fy2024.pdf | 9c514640fe5a29cb28fb45022e5c131d1ed44048ecd0ad7507eb9b3cfc393870 |
| annual_report_fy2025.pdf | 631ae8554ec5cc38484881f4c9d732f91a1c55596da82054da893ec797021c57 |

Page counts (via `pdfinfo`): FY2001 42, FY2002 45, FY2003 40, FY2004 41, FY2005 34, FY2006 50, FY2007 42, FY2008 32, FY2009 18, FY2010 24, FY2011 30, FY2012 37, FY2013 37, FY2014 38, FY2016 44 (spread 23), FY2017 36, FY2018 36, FY2019 36, FY2020 36, FY2021 36, FY2022 36, FY2023 36, FY2024 36, FY2025 40.

## Summary

Statewide, fiscal-year time series of **executive-clemency and parole decision metrics** for Georgia's constitutional paroling authority: parole grants/releases by type (parole, supervised reprieve, conditional transfer, commutation), parole revocations, discharges, decisions rendered under the Parole Decision Guidelines, **life-sentence case decisions (granted vs denied)**, pardons and restorations of civil/political rights, parole-supervision population (FY start/end) with successful-completion rate, revocations, agency expenditures, and parole-vs-prison **cost avoidance / cost-per-day**. Grain is **statewide × fiscal year** — one narrative-plus-statistics PDF per year, not a machine-readable table.

## Report / Table Structure

**The Excel-sheet / CSV-column / categorical / suppression-marker subsections of the standard bronze template do not apply** — these are narrative PDF reports, not tabular files. This section replaces the CSV "Eras" grouping: the reports fall into three **layout eras** whose design (and therefore where each metric lives) drifts over time. Boundaries below are approximate and were confirmed by inspecting FY2005, FY2009, FY2013, FY2016, and FY2025; the exact transition years for the in-between reports must be verified page-by-page at transform time.

### Layout Era 1 — "Classic" text report (≈ FY2001–FY2009)

- **Design**: plain narrative pages (Chairman's message, board bios, division writeups) with a small number of **clean, labeled statistics tables** near the back.
- **Key tables (extractable as text; example page pointers from FY2005, 34 pp)**:
  - **`CLEMENCY ACTION IN FY{YY}`** (FY2005 ~p.21): `RELEASE ACTIONS` (Parole, Supervised Reprieve, Conditional Transfer, Commutation, Remission, Other → **TOTAL RELEASES**); **TOTAL PAROLE REVOCATIONS**; `DISCHARGES` (Discharge from Parole, Discharge from Supervised Reprieve, Commutation to Discharge → **TOTAL DISCHARGES**); **TOTAL DECISIONS UNDER GUIDELINES**; `LIFE DECISIONS` (**Deny Parole to Life Cases**, **Grant Parole to Life Cases** → TOTAL LIFE DECISIONS); `OTHER BOARD ACTIONS` (Pardon, Commutation Reducing Sentence, Medical/Compassionate Reprieve, Restoration of Rights, Visitor Interview).
  - **`Agency Expenditures`** (FY2005 ~p.13): line-item dollars by object class (Personal Services, Regular Operating, Other) → **TOTAL EXPENDITURES**.
- **In figure labels (chart values, NOT text tables — `pdftotext -layout` mangles the axis labels)**: parole-supervision population ("stood at 24,276"), **"Georgia's Adult Offender Population"** bar chart, **parole-vs-prison cost-per-day** line chart ($/day), life-sentence review counts, parole-revocations trend charts.

### Layout Era 2 — Magazine / "Nationally Recognized" layout (≈ FY2010–FY2014)

- **Design**: multi-column magazine styling (running footer "GEORGIA PAROLE: Nationally Recognized as a Leading Paroling Authority"); statistics live in **sidebar callout boxes** interleaved with prose.
- **Key callout tables (example page pointers from FY2013, 37 pp)**:
  - **`CLEMENCY ACTIONS IN FY{YY}`** (FY2013 ~p.19): same structure as Era 1 (RELEASE ACTION totals, TOTAL PAROLE REVOCATIONS, DISCHARGES, INITIAL DECISIONS UNDER GUIDELINES, LIFE SENTENCE DECISIONS grant/deny, OTHER BOARD ACTIONS incl. Pardon / Restoration of Rights / Revocation Hearings / Preliminary Hearings).
  - **`RELEASES UNDER SUPERVISION (June 30, FY)`** (FY2013 ~p.19): Georgia Releases in Georgia, Out-of-State Releases in Georgia, Georgia Releases Out-of-State → **TOTAL PAROLE POPULATION**.
  - **`Pardon Administration Unit FY{YY}`** (FY2013 ~p.17): Applications Received, Investigations Processed, Pardons Granted, Pardons Granted with Firearms, Restorations of Civil & Political Rights → Total applications granted.
- **In narrative + charts**: parole population **FY start vs end** ("increased from 22,480 on July 1, 2012 to 25,020 on June 30, 2013"), **successful-completion rate** ("rose to 74%"), average caseload, total offenders supervised at some point during the year, cost avoidance.

### Layout Era 3 — Post-HB310 modern infographic (FY2016–FY2025; **FY2015 missing**)

- **Design**: full graphic-design layout with large-number infographic callouts, icons, and multi-column pages; fewer clean back-of-book tables, more numbers embedded in **infographic callouts** and prose.
- **Key numbers (example page pointers from FY2025, 40 pp)**:
  - **Infographic callouts**: `CLEMENCY VOTES 76,261`, `COMPLETED PAROLE 73%` (big-number tiles — text-extractable but not in a labeled table).
  - **Stats table (FY2025 ~p.mid)**: `Parole Certificates 4,037`, `Total Prison Releases by Parole 5,588`, `Total Guidelines Decisions 13,743`, `Life Sentence Cases Denied 2,154`, `Total Life Sentence Case Decisions 2,277`, `Inmates Serving Life … Granted/Released 87`.
  - **Narrative**: parole-eligible cases considered (20,364), PIC points granted (30,710), preconditions to parole (4,781), revocations ("the Board revoked 1,273 parole violators"), parole-supervision population start/end + completion %, **cost avoidance** ("parole is calculated at more than $380 million"; cost-per-day parole $3.13 vs incarceration), agency-budget line items (e.g. "Clemency Decisions 18,390,468.00").
- **HB310 break (2015)**: House Bill 310 (effective 2015-07-01, i.e. the start of FY2016) moved day-to-day **parole supervision** to the new **Department of Community Supervision (DCS)**. FY2016+ reports explicitly reference DCS and "changes implemented late in FY15." Consequences for this series: **parole-supervision/field-operations metrics (population, caseloads, revocations-in-the-field) change hands and definitional basis at FY2016** — the pre-2015 reports cover a **richer, self-contained supervision series** that is not directly comparable to the post-2015 clemency-decision-focused reports. **Do not pool the supervision series across the FY2015 boundary** without a coverage/definition flag (see criminal_justice domain "version methodological breaks").

## ETL Considerations

1. **PDF table extraction is required at transform time.** These are narrative PDFs, not CSV/XLSX. `pdftotext -layout` (poppler) reliably extracts the back-of-book **text tables** (Era 1/2 clemency-action + expenditure tables). Extraction of grid tables and figure values is friction-heavy: **Java is not installed**, so `tabula`/`camelot` (JVM-backed) cannot run in this environment — install a JRE, or use a Python-native table extractor (e.g. `pdfplumber`) at transform time. Budget substantial per-year hand-verification.
2. **Many headline numbers are embedded in figure/chart labels**, not tables — parole population, cost-per-day, adult-offender-population breakdown, and (Era 3) the big infographic tiles. `pdftotext -layout` mangles chart axis/label geometry (see FY2005 "Georgia's Adult Offender Population" and cost-comparison charts). These must be read from the rendered figures (image/label OCR or manual transcription), not from linear text extraction.
3. **Metric labels drift across eras.** "TOTAL DECISIONS UNDER GUIDELINES" (Era 1) ≈ "INITIAL DECISIONS UNDER GUIDELINES" (Era 2) ≈ "Total Guidelines Decisions" (Era 3); "Discharge from Supervised Reprieve" (Era 1) ≈ "Discharge from Reprieve" (Era 2). Build an explicit label→canonical-metric crosswalk per era; do not assume a fixed row set.
4. **Fiscal-year semantics.** Georgia FY = July 1 → June 30; a report's headline year is its **end** year (FY2013 ends 2013-06-30). Population figures are point-in-time ("July 1" open vs "June 30" close); decision/release/revocation counts are **flow over the fiscal year**. Keep start-of-year and end-of-year population as distinct metrics.
5. **HB310 (2015) methodological break** — see Era 3 above. The parole *supervision* series (population, caseloads, field revocations) is not comparable pre/post FY2016; the *clemency-decision* series (grants, denials, guideline decisions, life decisions, pardons) is more continuous but still re-labeled. Version, don't pool.
6. **FY2015 is missing from the source** (not a download failure — the listing page omits it). Leave the gap; do not interpolate.
7. **FY2016 has two files with identical content** (`annual_report_fy2016.pdf` standard, 44 pp; `annual_report_fy2016_spread.pdf` 2-up, 23 pp). Ingest exactly one (prefer the standard single-page-per-sheet file for extraction); the spread is kept for provenance only.
8. **Percentages → proportions.** Completion rates, guideline-agreement rates, etc. are quoted as whole-number percents; scale to `[0,1]` per data-cleaning standards §4.
9. **Statewide grain only** — there is no county detail, so this topic carries a single "Georgia"/state row per fiscal year (NULL `county_fips` per the criminal_justice state-detail-level convention) and **does not participate in county-level cross-dataset linking** (documented limitation).
10. **Revocations technical vs new-crime**: the split is not consistently tabulated across all years (some reports give only a total revocation count, or split by hearing type rather than technical/new-crime). Verify per year before publishing a technical-vs-new-crime breakdown; fall back to a single revocations metric where the split is absent.
11. **Cost avoidance / cost-per-day** appears as chart labels and prose in different units across eras ($/day parole vs prison in Era 1; aggregate "$380 million cost avoidance" in Era 3). Keep the raw published figure + its stated basis; do not recompute across eras.

## Gold Schema Classification

Grain: **statewide × fiscal_year** (one row per fiscal year; state-level, NULL `county_fips`). All values are hand/tool-extracted from the PDFs at transform time — the table below classifies the *conceptual* fields, not literal source columns (there are none).

| Source field (PDF) | Gold Role | Gold Name (proposed) | Notes |
|---------------------|-----------|----------------------|-------|
| fiscal year (title/filename) | fact_key | `fiscal_year` | Int; FY end year (July–June). Sole time key. |
| statewide (implicit) | fact_key | `county_fips` | NULL (state grain) per criminal_justice state detail-level convention; no county breakdown exists. |
| Total Prison Releases by Parole / Parole (release action) | fact_metric | `parole_releases` | `unit: count`. Era-labeled: "Parole" (Era 1/2 release table) / "Total Prison Releases by Parole" (Era 3). Key-metric candidate. |
| Parole Certificates | fact_metric | `parole_certificates` | `unit: count` (Era 3 explicit; ≈ certificates granted). |
| TOTAL RELEASES | fact_metric | `total_releases` | `unit: count` (Era 1/2 rollup of release actions). |
| Supervised Reprieve / Conditional Transfer / Commutation | fact_metric | `supervised_reprieves` / `conditional_transfers` / `commutations` | `unit: count`; components of TOTAL RELEASES. |
| TOTAL / Initial DECISIONS UNDER GUIDELINES | fact_metric | `guidelines_decisions` | `unit: count`. Label drifts across eras (see ETL #3). |
| Grant Parole to Life Cases | fact_metric | `life_cases_granted` | `unit: count`. |
| Deny Parole to Life Cases | fact_metric | `life_cases_denied` | `unit: count`. |
| TOTAL LIFE (SENTENCE) DECISIONS | fact_metric | `life_decisions_total` | `unit: count`. |
| TOTAL PAROLE REVOCATIONS / "revoked N violators" | fact_metric | `parole_revocations` | `unit: count`. Technical-vs-new-crime split inconsistent (ETL #10). |
| DISCHARGES (Discharge from Parole, …) | fact_metric | `total_discharges` | `unit: count`. |
| Pardons Granted / Pardon | fact_metric | `pardons_granted` | `unit: count`. |
| Restorations of Civil & Political Rights | fact_metric | `rights_restorations` | `unit: count`. |
| Parole population July 1 (start) | fact_metric | `parole_population_start` | `unit: count`, point-in-time. Pre-HB310 basis differs (ETL #5); often a chart label (ETL #2). |
| Parole population June 30 (end) / TOTAL PAROLE POPULATION | fact_metric | `parole_population_end` | `unit: count`, point-in-time. |
| Successful parole completion rate | fact_metric | `parole_completion_rate` | `unit: proportion` (scale %→[0,1]). |
| Clemency votes | fact_metric | `clemency_votes` | `unit: count` (Era 3 prominent). |
| Cost avoidance / cost-per-day | fact_metric | `cost_avoidance` (and/or `parole_cost_per_day` / `prison_cost_per_day`) | `unit: currency`; basis varies by era (ETL #11) — document, don't recompute. |
| TOTAL EXPENDITURES / budget line items | fact_metric | `total_expenditures` | `unit: currency` (agency expenditure table). |
| board bios, mission/process narrative, org charts | not_in_gold | — | Non-numeric narrative content. |

Exactly one metric should carry `key_metric: True` at transform time (recommended: `parole_releases` — the headline decision output present in every era). Counts composing a rate (e.g. completions vs population) set `metric_component` as appropriate. Metric availability is uneven across the three eras; expect NULLs where a given report does not publish a field.
