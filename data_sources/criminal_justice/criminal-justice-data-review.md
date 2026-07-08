# Georgia Criminal Justice — Bronze Data Blueprint

The actionable ingestion plan for the **`criminal_justice`** main topic. Every source below is
**recommended for bronze ingestion**, with the retrieval details Claude Code needs to pull it. 

> **Provenance.** Compiled 2026-07-01 from two verified research passes (2026-06-29 catalog + 2026-07-01
> re-verification and wide-net sweep; three parallel research agents; every load-bearing URL below was
> HTTP-tested live on 2026-07-01 unless marked otherwise).
>
> **Selection criteria** (platform mission): statewide Georgia coverage · **county-level or
> county-mappable grain** · aggregated, non-PII · recurring where possible · **bulk machine-readable
> retrieval preferred** (CSV/XLSX/API over PDF/dashboards).
>
> **Bronze layout:** `data/bronze/criminal_justice/{sub_topic}/{topic}/` — suggested `sub_topic/topic`
> given per source. Capture per ingest: source URL, download date, schema version, license, checksums
> (standard `bronze-data-structure.md` requirements).
>
> **Revision (2026-07-01, later same day).** Vera Institute's Incarceration Trends dataset — originally
> Tier 1 source #1 — was **rejected on license grounds** (non-commercial/no-redistribution terms
> incompatible with serving derived data through this platform's public API) and replaced with two
> first-party sources built from what Vera's own methodology paper disclosed as its inputs: **#1**
> `bjs/county_jail_population` (BJS Census/Annual Survey of Jails, free NACJD public-use) for the jail
> side, and **#25** `bjs/county_prison_population` (BJS NCRP restricted-use microdata, DUA required, plus
> a GDC records request for GA's pre-1983 series) for the county-level prison side.

---

## Tier 1 — build first (bulk machine-readable, county grain)

### 1. BJS Census/Annual Survey of Jails — county jail population (self-built, replaces Vera)

> **Decision (2026-07-01): Vera Institute's Incarceration Trends dataset will not be used.** Its
> `License.pdf` restricts use to non-commercial academic/nonprofit/research purposes and prohibits
> redistribution — incompatible with serving derived data through a public API. Vera's own methodology
> paper (`Workingpaper_Reconstructing-How-Counties-Contribute-to-State-Prisons.pdf`, in-repo) discloses
> exactly where its numbers come from, which lets us rebuild the same shape from primary sources instead:
> jail counts from BJS's own facility surveys (below), county prison counts from BJS's NCRP restricted-use
> microdata (**#25**), and Georgia's pre-1983 prison series directly from GDC. See full research trail in
> the session referenced in project memory.

- **Sub-topic / topic**: `bjs/county_jail_population`
- **Overall description**: County-level jail population/ADP built in-house from BJS's own local-jail
  surveys instead of consuming Vera's derivative CSV. **Census of Jails (COJ)** years give full
  county-level enumeration of all ~2,900 US local jails; **Annual Survey of Jails (ASJ)** years
  (discontinued after 2023, replaced by annual COJ) sample only ~1/3 of jails (skewed toward the largest),
  so non-sampled GA counties have no direct observation in those years — document as missing or backfill
  from GSA/GDC current-year reports (#4, #11) rather than inventing an imputation model.
- **Key metric fields**: Facility-level rated capacity, ADP, admissions/releases, demographics (race/sex,
  adult/juvenile, conviction status) — aggregate facility rows to county via the GA agency roster in each
  release.
- **Geographic granularity**: Facility → **county**. COJ full-county years: 1970, 1978, 1983, 1988, 1993,
  1999, 2006, 2013, 2019, then annual from 2024. ASJ (partial county coverage): 1982–2023 minus COJ years.
- **Format for retrieval**: Facility-level microdata via **ICPSR/NACJD — free public-use files, account
  registration only, no DUA required** (this tier of NCJD data is not restricted-access).
- **Link**: COJ overview <https://bjs.ojp.gov/data-collection/census-jails-coj>; ASJ overview
  <https://bjs.ojp.gov/data-collection/annual-survey-jails-asj>; search individual year studies at
  <https://www.icpsr.umich.edu/web/NACJD/series> (search "Census of Jails" / "Annual Survey of Jails").
- **Challenges**: One ICPSR study per year/collection wave — no single bulk file, so the ETL needs a
  per-year layout-aware loader (schema drift across ~55 years). ASJ sample years require explicit
  per-county coverage flags rather than silently blending sampled and unsampled counties. Small-county
  suppression/missingness in early years. Replaces Vera's AAPI-combined race scheme with GA's own reported
  categories — reconcile per `data-cleaning-standards` §5a–§5b (`asian`/`pacific_islander` vs
  `asian_pacific_islander`) using whatever the source actually reports, not Vera's recode.

### 2. FBI Crime Data Explorer — NIBRS/UCR (Georgia)

- **Sub-topic / topic**: `fbi_cde/nibrs_offenses`, `fbi_cde/nibrs_arrests`, `fbi_cde/hate_crimes`,
  `fbi_cde/law_enforcement_employees`
- **Overall description**: The canonical crime/arrest source. Georgia agencies report NIBRS to GBI/GCIC,
  which feeds the FBI. Bulk master files + a working REST API. Cornerstone of the crime side of the
  warehouse; requires the `ori_to_county` crosswalk (below) for county rollups.
- **Key metric fields**: NIBRS offenses (71 Group A across 28 categories + 10 Group B arrest-only),
  victims/offenders/arrestees (age/sex/race), weapon, location type, clearances, bias motivation (hate
  crimes), agency employee counts (staffing denominator); SRS offenses-known + arrests for pre-2019
  history.
- **Geographic granularity**: **Agency (ORI)** → county via crosswalk; state rollups native. GA full
  NIBRS since Oct 2019; SRS history to 1985. Monthly refresh cadence (since 2025-08).
- **Format for retrieval**: **Bulk CSV/ZIP** from the Documents & Downloads page (lead with these), plus a
  **REST API (JSON)** — verified working: base `https://api.usa.gov/crime/fbi/cde/`, free data.gov key
  (`API_KEY=`; `DEMO_KEY` works for testing), **dates must be `MM-YYYY`**. Example:
  `https://api.usa.gov/crime/fbi/cde/summarized/state/GA/homicide?from=01-2022&to=12-2022&API_KEY=DEMO_KEY`
  Agency-level: `…/summarized/agency/{ORI}/{offense}?from=MM-YYYY&to=MM-YYYY`.
- **Link**: <https://cde.ucr.cjis.gov> (downloads:
  `https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/downloads`); API docs: <https://www.justice.gov/developer>.
- **Challenges**: No stable direct file URLs (SPA — navigate/scrape the downloads page); large multi-table
  joins; older files fixed-width ASCII needing codebooks; SRS→NIBRS break (GA Oct 2019) must be versioned;
  NIBRS counts are unestimated (differ from CIUS estimates); API rate limits; **ORI→county crosswalk is a
  hard prerequisite**. For incident-level depth, prefer ICPSR/NACJD "NIBRS Extract Files" (series 128,
  free login) over raw master files.

### 3. Juvenile Justice Data Clearinghouse — decision points & placements

- **Sub-topic / topic**: `juvenile_clearinghouse/decision_points`, `juvenile_clearinghouse/out_of_home_placement`,
  `juvenile_clearinghouse/placements`
- **Overall description**: Multi-agency clearinghouse (Juvenile Data Exchange Committee / CJCC / courts)
  publishing **four downloadable raw CSVs** of county-level juvenile decision-point data — referrals,
  petitions, adjudications, diversions, commitments, detention, placements. The strongest juvenile ingest
  path in Georgia.
- **Key metric fields**: By county/year (and month in file 2): referrals, petitions, delinquent
  adjudications, diversions, probation/commitment orders, superior-court transfers, secure detention
  (RYDC) / confinement (YDC), OHP/STP commitments — with race and gender splits; placements file adds
  site name/type and offense description.
- **Geographic granularity**: **County throughout**; the OHP-STP file carries explicit 5-digit
  **`CountyFips`**. Coverage ~2005/2010 → ~2024; refreshed annually (June).
- **Format for retrieval**: Direct CSV downloads (four files; one ~19 MB). All four verified HTTP 200
  on 2026-07-01.
- **Link**: <https://juveniledata.georgiacourts.gov/dashboards-reports/> — current files (pattern:
  `…/wp-content/uploads/2026/06/Juvenile-Justice-Decision-Points-Raw-Data-1.csv`, `…-Raw-Data-2.csv`,
  `…Decision-Point-Raw-Data-OHP-STP.csv`, `…Decision-Point-Placements-Raw-Data.csv`). **URLs embed the
  upload month — re-scrape the page's "Raw Data" section rather than hardcoding.**
- **Challenges**: Inconsistent schemas across the four files (youth-level vs county aggregate); race/gender
  carry label + numeric code; `DD-MM-YYYY` dates in the placements file; youth-level IDs are PII-adjacent —
  **aggregate to county/year before gold**; no co-located data dictionary (use the site's Definitions page).

### 4. Georgia Sheriffs' Association — monthly county jail report

- **Sub-topic / topic**: `jails/jail_population`
- **Overall description**: Monthly voluntary survey of all county jails — the only near-statewide,
  current-month jail census Georgia has. Statewide summary + per-county table (all 159 counties).
  Pairs with the GDC County Jail Report (#11) for official backfill.
- **Key metric fields**: Per county: total jail inmates, jail capacity, % capacity, inmates awaiting
  trial, state-sentenced inmates held in county jail (jail backlog), county-sentenced, other; statewide
  monthly summary + annual totals (2016–2025).
- **Geographic granularity**: **County (159) + statewide**, monthly.
- **Format for retrieval**: **HTML table on the page** (cleanly extractable; PDF also posted). Latest
  month verified: May 2026.
- **Link**: <https://georgiasheriffs.org/jail-report>
- **Challenges**: Voluntary/self-reported — not all counties report every month (coverage fluctuates;
  note "NO JAIL" rows, e.g. Baker); counts + capacity only (no race/sex/charge detail — `bjs/county_jail_population`
  (#1) covers that); jurisdiction names need the `county_name_to_fips` crosswalk; no official archive on the page
  beyond the annual-totals table (archive each month at ingest time).

### 5. GA DPH OASIS — overdose & violent-death mortality

- **Sub-topic / topic**: `dph_oasis/overdose_deaths`, `dph_oasis/violent_deaths`
- **Overall description**: Georgia's official public-health data warehouse (vital statistics). The GA
  route to **drug-overdose deaths** (by drug type) and homicide/firearm mortality at county level; also
  underlies GA-VDRS violent-death reporting. Official, suppression-aware, FIPS-exportable.
- **Key metric fields**: Death counts + crude/age-adjusted rates by cause (any opioid, fentanyl/synthetic,
  heroin; homicide, firearm), year, age, race/ethnicity, sex; nonfatal overdose ED/inpatient counts.
- **Geographic granularity**: State / public-health district / **county** (some measures sub-county).
  Mortality ~1999–present, annual.
- **Format for retrieval**: **Web query tool → spreadsheet export with county FIPS codes** (FIPS in
  saved-data exports confirmed via the official changelog). **No bulk download or public API** — script
  or manually run per-measure queries and save the exports.
- **Link**: <https://oasis.state.ga.us> (GA-VDRS: <https://dph.georgia.gov/GVDRS>)
- **Challenges**: Query-driven (one export per measure/year-range — plan a repeatable manual/automated
  export procedure and snapshot to bronze); small-count suppression (rates not calculated <4 deaths →
  **NULL, never 0**); overdose drug categories are **not mutually exclusive** (any-opioid overlaps
  fentanyl/heroin — violates naive demographic-exclusivity assumptions; model as separate metrics);
  overlaps CDC WONDER (same NCHS source) — pick one as canonical per measure and cross-check.

### 6. CDC WONDER — firearm & homicide mortality (GA counties)

- **Sub-topic / topic**: `cdc/firearm_homicide_deaths`
- **Overall description**: National death-certificate mortality; firearm deaths, homicides, and
  legal-intervention deaths isolable via ICD-10 codes. The scriptable national complement to OASIS —
  use for the measures OASIS doesn't expose cleanly, or as the canonical firearm/homicide series.
- **Key metric fields**: Death counts, crude + age-adjusted rates, by injury intent (firearm homicide,
  assault, legal intervention), age, race, ethnicity, sex, year/month.
- **Geographic granularity**: National / state / **county (residence)**. 1999–2020 (bridged race) +
  2018–2024 (single race); annual.
- **Format for retrieval**: **Interactive query → tab-delimited TXT/CSV export.** ⚠️ The XML-POST API
  **cannot return county-level data** (sub-national grouping variables are API-blocked — verified against
  the API docs) — county extracts are **web-app export only**.
- **Link**: <https://wonder.cdc.gov/mcd.html> (API docs, for state-level only:
  <https://wonder.cdc.gov/wonder/help/WONDER-API.html>)
- **Challenges**: No API path at county grain (session-driven exports — automate carefully or refresh
  manually per annual release); suppression (counts <10 suppressed, rates unreliable <20 — many small GA
  counties blank for firearm deaths; pool years or NULL); data-use agreement consent; residence vs
  occurrence county.

### 7. OJJDP "Easy Access" — county juvenile court cases + population denominators

- **Sub-topic / topic**: `ojjdp/juvenile_court_cases` (EZACO), `ojjdp/juvenile_population` (EZAPOP)
- **Overall description**: NCJJ-built federal query tools. EZACO gives **county-level juvenile court case
  counts** (delinquency, status offense, dependency) for reporting GA counties; EZAPOP gives county
  juvenile population by age/sex/race/ethnicity (full GA coverage) — the rate denominators. Cross-validates
  the Clearinghouse (#3).
- **Key metric fields**: Juvenile court case counts + rates per 1,000 juveniles by county/year/case type;
  juvenile population by county/year/age/sex/race/ethnicity.
- **Geographic granularity**: **County-year.**
- **Format for retrieval**: Web query tool with **CSV/Excel export** (no bulk endpoint/API — drive the
  tool per query and save exports to bronze).
- **Link**: EZACO
  <https://ojjdp.ojp.gov/statistical-briefing-book/data-analysis-tools/ezaco/access-case-counts>;
  EZAPOP <https://www.ojjdp.gov/ojstatbb/ezapop>
- **Challenges**: ~3-year data lag; county reporting-coverage gaps (not all GA juvenile courts report);
  small-count suppression; per-query exports (no bulk); the Statistical Briefing Book's federal funding is
  at-risk — **snapshot everything at first ingest**.

### 8. ICE detention — ice.gov statistics + Deportation Data Project

- **Sub-topic / topic**: `ice_detention/detention_population`
- **Overall description**: Immigration detention in Georgia — **Stewart Detention Center** (Lumpkin, among
  the largest in the US) and **Folkston ICE Processing Center**. Two complementary feeds: ICE's official
  detention-statistics workbook (facility-level, ~biweekly) and the Deportation Data Project's
  FOIA-obtained record-level files (bulk CSV, ~monthly). No other recommended source covers this system.
- **Key metric fields**: Facility average daily population, book-ins, average length of stay, criminality
  mix, removals, detainers — aggregate to facility/county × month.
- **Geographic granularity**: **Facility → county-mappable** (via the facility crosswalk). ICE XLSX =
  facility-semimonthly; DDP = individual-level records with facility identifiers.
- **Format for retrieval**: **XLSX** direct from ice.gov (FY detention-statistics workbook, ~biweekly
  refresh); **bulk CSV + codebooks** from DDP (no gate).
- **Link**: <https://www.ice.gov/detain/detention-management> ·
  <https://deportationdata.org/data/processed/ice.html>
- **Challenges**: ICE workbook layout shifts across fiscal years (version the parser); DDP files are large
  and individual-level (**PII — aggregate to facility-month before gold**); DDP release cadence tracks FOIA
  productions (irregular); requires `facility_to_county` crosswalk; cite DDP as requested ("government
  data provided by ICE…, processed by the Deportation Data Project").

### 10. NHTSA FARS — fatal crashes / impaired driving

- **Sub-topic / topic**: `traffic_safety/fatal_crashes`
- **Overall description**: NHTSA's annual census of fatal motor-vehicle traffic crashes since 1975, coded
  from police reports/death certificates/toxicology. The fully open, machine-readable path for GA fatal
  crash and alcohol-involved (DUI-adjacent) data — GDOT's own crash warehouse is login-gated (see Tier 3).
- **Key metric fields**: Crashes/vehicles/persons (join on `ST_CASE`/`VEH_NO`/`PER_NO`): fatalities,
  injury severity, **driver BAC / alcohol involvement** (multiply-imputed BAC variables), drugs, speeding,
  restraint use, time/roadway, age/sex.
- **Geographic granularity**: **County** (`COUNTY` element on the crash file; GA = state FIPS 13) + crash
  lat/long. 1975–present, annual. No PII (Privacy Act-stripped).
- **Format for retrieval**: **Bulk CSV (zipped) + SAS** annual files.
- **Link**: <https://www.nhtsa.gov/research-data/fatality-analysis-reporting-system-fars> — file listing:
  <https://www.nhtsa.gov/file-downloads?p=nhtsa/downloads/FARS/>
- **Challenges**: Multi-file joins; BAC not measured for all fatalities (document which imputed variable is
  used); fatal-only (no injury/enforcement counts); annual schema tweaks; county code is the NHTSA GSA
  code — map to FIPS carefully.

---

## Tier 2 — high value, moderate friction

### 11. GDC — statistical trends + county jail report (PDF suite)

- **Sub-topic / topic**: `gdc/inmate_releases_county`, `gdc/inmate_population`, `gdc/recidivism_reconviction`,
  `jails/county_jail_report` (official monthly series)
- **Overall description**: Georgia Dept. of Corrections' statistical library — all **PDF**. The
  county-mappable/long-run subset is worth the extraction cost: **Inmate Release by County** (all 159
  counties, 5-year window, CY + FY editions), year-end prison population (since 1925), 3-year reconviction
  rates (the canonical GA recidivism metric), facility ADP — plus the **monthly County Jail Inmate
  Population Report** (all 159 counties: population, capacity, state-sentenced backlog, awaiting trial),
  whose historical issues (2000s–2021+) sit in the **Digital Library of Georgia** for backfill.
- **Key metric fields**: Releases by county of release; year-end inmate population; 3-yr reconviction rate
  by release type; facility ADP/capacity; county jail population/capacity/% capacity/backlog/awaiting-trial.
- **Geographic granularity**: County (releases; jail report), facility (ADP), statewide (population,
  recidivism). Annual (weekly Friday Report; monthly jail report).
- **Format for retrieval**: **PDF only** (confirmed — no CSV/XLSX/API). Current direct PDFs (verified
  2026-07-01; media IDs change on re-upload — re-scrape the Statistical Trends page): Inmate Release by
  County CY `https://gdc.georgia.gov/media/19926/download`, FY `https://gdc.georgia.gov/media/20906/download`.
- **Link**: <https://gdc.georgia.gov/organization/about-gdc/agency-activity/research-and-reports/standing-reports/statistical-trends>
  · Friday Report:
  <https://gdc.georgia.gov/organization/about-gdc/agency-activity/research-and-reports/standing-reports/friday-report>
  · DLG archive: <https://dlg.usg.edu>
- **Challenges**: PDF table extraction with per-table QA (`camelot`/`tabula-py`); layout drift across
  years; media-ID URLs are unstable; GDC offense taxonomy ≠ NIBRS; recidivism is *reconviction* (don't
  pool with re-arrest measures); skip the 90-page monthly inmate profiles in the first pass (statewide
  grain, heavy extraction).

### 14. Stanford Open Policing Project — GA State Patrol stops

- **Sub-topic / topic**: `open_policing/gsp_traffic_stops`
- **Overall description**: Standardized traffic-stop microdata; for Georgia, **Georgia State Patrol only**
  — 1,906,772 stops, 2012-01-01 → 2016-12-31 (static; project effectively frozen). High civic value for
  racial-disparity analysis; ingest once, aggregate to county/year/race.
- **Key metric fields**: Stop date/time, location, driver race/sex/age, search conducted, contraband
  found, outcome (citation/warning/arrest), violation.
- **Geographic granularity**: Statewide (single agency); location/county fields where available.
- **Format for retrieval**: **Bulk CSV (zip) / RDS** — direct (verified 200):
  `https://stacks.stanford.edu/file/druid:yg821jf8611/yg821jf8611_ga_statewide_2020_04_01.csv.zip`
- **Link**: <https://openpolicing.stanford.edu/data/>
- **Challenges**: Frozen 2012–2016; GSP only (no municipal agencies); stop-level records with driver
  demographics — **aggregate before serving**; license ODC-BY (attribution).

### 16. State Board of Pardons and Paroles — parole decisions

- **Sub-topic / topic**: `pardons_paroles/parole_decisions`
- **Overall description**: Georgia's constitutional clemency authority. Fiscal-year annual reports
  (FY2001–FY2025, continuous) with the parole decision-metric time series: grants, denials, completion
  rates, revocations, life-sentence reviews.
- **Key metric fields**: Parole population (FY start/end), certificates granted, releases, guideline
  decisions, life-sentence cases granted/denied, successful-completion %, revocations (technical vs
  new-crime), cost avoidance.
- **Geographic granularity**: **Statewide only**, annual.
- **Format for retrieval**: **PDF annual reports** (FY25 ~13 MB).
- **Link**: <https://pap.georgia.gov>
- **Challenges**: PDF extraction (key numbers often embedded in figure labels); statewide grain limits
  cross-dataset linking; 2015 HB 310 break (parole *supervision* moved to DCS — pre-2015 reports cover a
  richer series).

### 17. Federal justice in Georgia — FJC IDB + USSC datafiles

- **Sub-topic / topic**: `federal_justice/district_filings`, `federal_justice/district_sentences`
- **Overall description**: (a) FJC Integrated Database — every federal criminal defendant
  filing/termination in NDGa/MDGa/SDGa since 1979; (b) US Sentencing Commission annual datafiles — every
  federally sentenced individual FY1987–present (`DISTRICT` isolates the three GA districts). Free, bulk,
  public-domain, recurring.
- **Key metric fields**: Criminal filings/terminations, offense mix, disposition type, sentence imposed
  (IDB); sentence length, guideline position, departures/variances, demographics, drug type (USSC).
- **Geographic granularity**: **Federal district** (3 GA districts — sub-state but not county; criminal
  IDB has no county code). Serve as a district-grain topic.
- **Format for retrieval**: **Free bulk CSV/SAS/delimited** (IDB quarterly; USSC annual, CSV from ~FY2017).
- **Link**: <https://www.fjc.gov/research/idb> ·
  <https://www.ussc.gov/research/datafiles/commission-datafiles>
- **Challenges**: Defendant-level microdata → aggregate to district-year; USSC FY2018 methodology break;
  large files with year-specific layouts; district ≠ county (decide whether district grain fits the
  serving model before building).

---

## Tier 3 — contingent on access, manual steps, or a request

### 19. Dept. of Community Supervision — felony probation/parole supervision

- **Sub-topic / topic**: `dcs/supervision_population`
- **Overall description**: The authoritative post-2015 source for **all adult felony supervision**
  (~200k people — Georgia's largest correctional population). Population dashboard + PDF reports.
- **Key metric fields**: Supervised population (probation/parole), entries/exits, caseloads,
  demographics, outcomes.
- **Geographic granularity**: **10 judicial districts / 49 circuits — not county** (needs the
  `judicial_circuit_to_county` crosswalk). Data starts 2015-07-01.
- **Format for retrieval**: **Tableau Public** — a hidden "shared" workbook
  (`https://public.tableau.com/app/profile/georgiadcs/viz/shared/3CXMQWC3W`, embedded at
  `dcs.georgia.gov/dcspopulation` with `toolbar=no`); the `georgiadcs` profile also shows
  `EntriesandExits` / `AnnualPopulationDashboardfinal` workbooks. + PDF reports.
- **Link**: <https://dcs.georgia.gov/strategic-planning-research>
- **Challenges**: **Blocked on a manual browser check** — whether Download → Crosstab (CSV) is enabled
  could not be verified headlessly. If no export, fall back to PDF reports or a data request. 2015 HB 310
  break (pre-2015 probation in GDC reports, parole supervision in SBPP reports); circuit grain.

### 20. Judicial Council / AOC — court caseloads

- **Sub-topic / topic**: `courts/court_caseloads`, `courts/workload_assessments`
- **Overall description**: Caseload statistics for all GA trial-court classes since 1976 — but delivered
  as **view-only Power BI dashboards** (US-Gov cloud, no export). Two pragmatic paths while a bulk
  request is pending: the **Superior Court Workload Assessment PDFs** (2018–2024; the only circuit-level
  criminal-filings series in a file) and the **CDX dashboard** (criminal disposition transmissions to
  GCIC by court + county, 60-day refresh, extracts by email).
- **Key metric fields**: Filings, dispositions, manner of disposition, pending/cleared by court class;
  circuit workload values; CDX disposition-transmission + unfixed-error counts by county.
- **Geographic granularity**: County/circuit/municipality by court class (Superior = circuit).
- **Format for retrieval**: **Research Request to ORDA for CSV/XLSX** (the upgrade path — submit early);
  Workload Assessment **PDFs** at <https://research.georgiacourts.gov/data-and-statistics/>; CDX at
  <https://jcaoc.georgiacourts.gov/cdx-dashboard> (email kate.heidenreich@georgiacourts.gov for extracts).
- **Challenges**: Power BI view-only (no scraping path); PDF extraction for workload tables;
  circuit→county crosswalk; reporting completeness varies by court class; **submit the ORDA Research
  Request first — if CSV arrives, this becomes Tier 1 material** (`casecount.georgiacourts.gov` is a
  clerk login portal, not a public download).

### 21. DDS — DUI & distracted-driving convictions; GOHS crash facts

- **Sub-topic / topic**: `traffic_safety/dui_convictions`, `traffic_safety/crash_facts`
- **Overall description**: Dept. of Driver Services license-action data — DUI/alcohol-drug convictions
  (~16k/year), suspensions, distracted-driving convictions, itemized **by county**; GOHS "Georgia Traffic
  Safety Facts" annual reports for packaged statewide+county crash/DUI context.
- **Key metric fields**: DUI convictions by county/conviction code/violation date; administrative license
  suspensions; distracted-driver convictions by county; GOHS crashes by severity, BAC≥.08 fatalities.
- **Geographic granularity**: **County** (DDS convictions), statewide+county (GOHS). DDS DUI series
  ~2007–present.
- **Format for retrieval**: DDS **on-demand reports via the DRIVES e-services app**
  (`https://dds.drives.ga.gov/?link=DriverReports` — "DUI Report"; not login-gated but generated
  per-request, **not curl-able**); the **Distracted Driver** county reports are posted downloadable files
  at <https://dds.georgia.gov/distracted-driver-data-reports>. GOHS = **PDF** at
  <https://www.gahighwaysafety.org>.
- **Challenges**: DRIVES request flow needs browser automation or a manual quarterly pull; GOHS locked in
  PDFs; overlap with FARS (#10 — fatal only) — define metric boundaries per topic.

### 22. GBI — Summary Report tables, SAK backlog, sex-offender aggregate

- **Sub-topic / topic**: `gbi/family_violence`, `gbi/sak_backlog`, `gbi/sex_offender_counts`
- **Overall description**: GBI's residual value beyond FBI CDE: the annual Summary Report's GA-only tables
  (**family-violence incidents**, juvenile arrest dispositions), the statutory annual **sexual-assault-kit
  (SAK) backlog** series, and a **county-aggregated** derivative of the sex-offender registry. (Index
  crime/arrest counts themselves: use FBI CDE — the GBI interactive database has been down for months,
  re-confirmed 2026-07-01.)
- **Key metric fields**: Family-violence incidents by county; juvenile arrests & dispositions; SAK kits
  tested/awaiting/backlogged by year; registrant counts per county by risk level.
- **Geographic granularity**: County + MSA (Summary Report tables), statewide (SAK), county (SOR
  aggregate). Summary Reports archived to ~2009.
- **Format for retrieval**: **PDF** Summary Report (2024:
  `https://gbi.georgia.gov/document/document/2024-crime-statistics-summary/download`); SAK annual PDFs at
  <https://dofs-gbi.georgia.gov/dofs-sexual-assault-kits-report>; SOR **bulk CSV**
  `https://state.sor.gbi.ga.gov/SORT_PUBLIC/sor.csv` (verified 200; refreshed daily).
- **Challenges**: PDF table extraction (Summary Report); SOR CSV is **heavy individual PII** — ingest to
  bronze but **only county aggregates ever reach gold**; SOR is a current-state snapshot (archive
  snapshots to build a time series); SAK series is small statewide tables.

### 23. Census — justice expenditures & public-safety employment

- **Sub-topic / topic**: `justice_finance/justice_expenditures`, `justice_finance/public_safety_employment`
- **Overall description**: Annual Survey of State & Local Government Finances + Annual Survey of Public
  Employment & Payroll (APES) — *Police Protection*, *Corrections*, *Judicial & Legal* function codes.
  The only clean fiscal/workforce lens on GA's justice system; machine-readable.
- **Key metric fields**: Expenditures and FTE/payroll by government function, by government unit, by year.
- **Geographic granularity**: State + **local government unit** (→ county/place via government IDs).
- **Format for retrieval**: **CSV / data.census.gov API.**
- **Link**: <https://www.census.gov/programs-surveys/gov-finances.html> ·
  <https://www.census.gov/programs-surveys/apes.html>
- **Challenges**: Government-unit geography ≠ service geography (a city PD's spend isn't the county's);
  function-code mapping; survey (sample) years vs census years differ in coverage. Second-wave context
  topic.

### 24. National Registry of Exonerations — GA exonerations

- **Sub-topic / topic**: `exonerations/county_exonerations`
- **Overall description**: All GA exonerations since 1989, coded with county of conviction, crime, and
  contributing factors. Small, clean, high-interest niche topic — pending a republication OK.
- **Key metric fields**: Exoneration counts by county/year, crime type, official-misconduct/DNA flags,
  years lost.
- **Geographic granularity**: Case → **county of conviction** (sparse — serve cumulative counts).
- **Format for retrieval**: **XLSX via request form** (the old direct download is gone):
  <https://exonerationregistry.org/form/spreadsheet>
- **Challenges**: Manual request step; source file contains names (aggregate to county counts); tiny N;
  confirm republication rights with the Registry before serving.

### 25. BJS NCRP (restricted-use) + GDC historical request — county-level prison population/admissions

- **Sub-topic / topic**: `bjs/county_prison_population`
- **Overall description**: The prison-side replacement for Vera's county reconstruction. Vera's own
  methodology paper (`Workingpaper_Reconstructing-How-Counties-Contribute-to-State-Prisons.pdf`) confirms
  the **county of commitment** field that makes county rollups possible lives only in BJS's **National
  Corrections Reporting Program (NCRP) restricted-use person-level microdata** (admission/release/term
  records, 1983–present) — not in the freely downloadable NCRP "Selected Variables" public-use files,
  which drop the county field. The same paper discloses that **Georgia's prison series in Vera's dataset
  runs 1970–2016** (vs. 1983+ everywhere else) because GDC supplied Vera complete historical data directly
  — i.e., the pre-1983 stretch isn't in NCRP at all and requires going straight to GDC.
- **Key metric fields**: Admission/release/term records — offense, sentence length, demographics, **county
  of commitment**, admission/release type — aggregable to county-year population and admissions counts.
- **Geographic granularity**: **County**, via county-of-commitment. NCRP restricted-use covers 1983–present;
  1970–1982 requires the GDC request below.
- **Format for retrieval**: **ICPSR/NACJD restricted-use data — requires a Data Use Agreement (DUA)**, free
  but with an approval process (weeks, not instant); submitted via the ResearchDataGov Standard Application
  Process. For 1970–1982, a direct **GDC Open Records Act request** for historical county-of-commitment
  admission records (or whatever internal series fed Vera's extended GA numbers).
- **Link**: NCRP overview <https://bjs.ojp.gov/data-collection/national-corrections-reporting-program-ncrp>;
  restricted-data application requirements
  <https://www.icpsr.umich.edu/sites/nacjd/resources/restricted-data-at-nacjd/application-requirements>;
  GDC Open Records Request portal <https://gdc.georgia.gov/open-records-request>.
- **Challenges**: DUA approval timeline gates this off the critical path — file early, in parallel with
  Tier 1/2 builds. Several states (need to confirm GA's own participation completeness) don't report to
  NCRP every year; county-of-commitment has known data-entry errors requiring the same
  validation-against-state-totals approach Vera describes (cross-check county sums against BJS's National
  Prisoner Statistics state totals). Pre-1983 GDC records are of unknown format/completeness — confirm
  with GDC's open-records office before assuming parity with the 1983+ NCRP series. Until this lands,
  GDC's own PDF releases (#11: year-end population since 1925, Inmate Release by County) remain the only
  county-mappable prison signal in gold.

---

## Crosswalks to build (shared dependencies)

| Crosswalk | Feeds | Build from | Notes |
|-----------|-------|-----------|-------|
| `ori_to_county` | FBI CDE (#2), WaPo agencies (#13) | FBI/GCIC ORI lists + LEAIC (ICPSR) | **Hard prerequisite for all agency-grain FBI data** |
| `county_name_to_fips` | GSA jail report (#4), GDC PDFs (#11), MPV (#12), DDS (#21) | Census county list | Normalize "Athens-Clarke"→Clarke, "Columbus"→Muscogee; handle "NO JAIL"/non-reporting rows |
| `judicial_circuit_to_county` | DCS (#19), AOC (#20), GPDC | Statute/AOC circuit definitions | Static (changes need legislation); 49 circuits, many-to-one with counties |
| `facility_to_county` | GDC ADP (#11), ICE (#8), UCLA (#15) | **HIFLD snapshots + UCLA `facility_data`** | ⚠️ HIFLD Open discontinued Sept 2025 — grab archived Prison Boundaries / Local Jails / LE Locations from data.gov/DataLumos/ArcGIS mirrors **now** |
| Point → county FIPS | WaPo (#13), MPV (#12) | Census county geometry spatial join | For incident-level sources |

---

## Build order (dependency-aware)

1. `bjs/county_jail_population` (COJ/ASJ via NACJD, free public-use) — per-year study pulls, no DUA.
2. `fbi_cde/*` + **`ori_to_county`** — bulk CSVs, then API for refreshes.
3. `juvenile_clearinghouse/*` — re-scrape the Raw Data links, download 4 CSVs.
4. `jails/jail_population` (GSA HTML) — start the monthly archive immediately (no historical archive on-page).
5. `dph_oasis/*` + `cdc/firearm_homicide_deaths` — scripted/manual query exports (suppression → NULL).
6. `ojjdp/*` — snapshot EZACO/EZAPOP exports (funding-at-risk source).
7. `death_penalty/executions` + `police_use_of_force/*` — trivial CSV/XLSX pulls.
8. `ice_detention/detention_population` + **`facility_to_county`** (snapshot HIFLD while archives last).
9. `traffic_safety/fatal_crashes` (FARS bulk).
10. PDF wave: `gdc/*`, `jails/county_jail_report`, `pardons_paroles/*`, `gbi/*`.
11. In parallel, fire the access requests that gate Tier 3: **NCRP restricted-use DUA + GDC Open Records
    request** (`bjs/county_prison_population`, #25 — file first, longest lead time), **ORDA Research
    Request** (court caseloads), DCS crosstab browser check, GDOT Numetric Crash Query account, CDX
    extract email, Exonerations spreadsheet form.

## Cross-cutting rules for the pulls

- **Snapshot at-risk sources at first ingest** (OJJDP tools, HIFLD archives, Fulton Socrata, any
  federal dashboard) — bronze is the archive.
- **Suppression → NULL, never 0** (CDC <10, OASIS <4, OJJDP small counts), with the threshold documented
  per topic.
- **Version methodological breaks**: SRS→NIBRS (GA Oct 2019); 2015 HB 310 (GDC→DCS/SBPP);
  reconviction (GDC) vs re-arrest (NIJ/BJS) — never pool; COJ (full-county) vs ASJ (sample) coverage in
  `bjs/county_jail_population` — never blend without a coverage flag.
- **Licenses to read before anything ships**: WaPo **CC BY-NC-SA**, MPV terms, Stanford ODC-BY, DPIC/DDP
  attribution, NCRP restricted-use DUA terms (`bjs/county_prison_population`, #25).
- **PII stays in bronze**: SOR rows, Clearinghouse youth-level IDs, DDP records, stop-level Stanford data,
  MPV/WaPo victim names — gold serves aggregates only.
- **Unstable URLs** (GDC media IDs, Clearinghouse upload paths, FBI SPA downloads): scrape the parent page
  per refresh; never hardcode.

---

## Reviewed and NOT recommended (summary — details in the catalog)

**No usable GA data / redundant:** Measures for Justice (no GA), Justice Counts (GA participation thin,
dashboard-only), LEMAS (sample survey), NCSC CSP (state benchmark), BOP statistics (HTML-only, 2–3 GA
facilities), Fatal Encounters (merged into MPV), Police Scorecard (derived composite), Police Data
Initiative (stale directory), DBHDD GASPS (PDF re-publication of ingested sources), GBI Medical Examiner
(no public dataset).

**Rejected on license grounds (2026-07-01):** **Vera Institute Incarceration Trends** — the single best
county-FIPS jail+prison panel by convenience, but its `License.pdf` limits use to non-commercial
academic/nonprofit/research purposes and bars redistribution, which conflicts with serving derived data
through this platform's public API. Its own methodology paper discloses its primary sources cleanly
enough to rebuild the same shape directly — see **#1** (`bjs/county_jail_population`) and **#25**
(`bjs/county_prison_population`) above. BJS NCRP is no longer "consume via Vera" — it is a first-party
Tier 3 source (#25) requiring its own restricted-use DUA.

**Blocked/gated:** PeachCourt / re:SearchGA (ToU prohibits bulk), PAC TRACKER (no export, PII), TRAC
(paywalled), Jail Data Initiative (DUA-gated — one email worth sending), POST Data Gateway (login/ORR
only — decertification counts remain a worthwhile ORR ask), CJARS (restricted-use), GDOT Numetric
(request account; FARS is the open fallback).

**PII / mission conflicts:** county jail booking feeds, offender/parolee search tools, raw SOR rows.

**Downgraded 2026-07-01:** Atlanta PD Open Data (bulk raw downloads removed — UI-driven Excel export
apps only, underlying layer private); Fulton "Total Daily Jail Population" (Socrata `hf8e-sig8`, SODA API
works, but **stale — last record 2023-08-11**; frozen 2018–2023 series at best).

**Context-only:** Prison Policy Initiative, Sentencing Project, CSG/JRI, Marshall Project COVID data,
GCFV fatality reviews, GRACE Commission, OPB/DOAA budget PDFs, Open Georgia salary .txt (agency staffing
context — Maybe later), Gun Violence Archive (caps + ToS + geocoding friction), historical Kaplan/NaNDA
county panels (frozen backfill only), UGA Carl Vinson landscape report (request a copy as a reference).

---

_Blueprint compiled 2026-07-01 (Claude, Fable 5). Re-verify URLs at ingest time — several sources use
unstable/rotating file paths (flagged per-entry). Companion catalog:_
[`claude-criminal-justice-data-review.md`](claude-criminal-justice-data-review.md)_._
