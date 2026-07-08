# detention_population — Bronze Data Structure

## Overview

- Topic: detention_population
- Source: ice_detention
- Files: 15 files across two feeds — 8 ICE fiscal-year workbooks (FY2020–FY2026; the two FY2025 files are byte-identical) + 7 Deportation Data Project (DDP) files under `ddp/` (3 Parquet, 1 XLSX collation, 3 HTML codebooks)
- Unreadable files: none
- Year representation: **fiscal year** (Oct 1 – Sep 30). Feed 1: FY is in the filename and embedded in column names (`FY26 ALOS`) / sheet names (`Facilities FY26`); no year column in the data. Feed 2: real date columns (`date`, `file_date`, `fiscal_year`, book-in/out timestamps).
- Filename-to-data year offset: same — filename FY = data FY. Caveat: the current-FY workbook is a fiscal-**YTD** snapshot overwritten ~biweekly at the source; the snapshot date is the second token of our filename.
- Detail levels: facility (Feed 1 `Facilities` sheets; DDP daily population / stints / stays), national and AOR (all other Feed 1 sheets — not GA-filterable)
- Percentage scale: n/a — no percentage columns. All population metrics are ADP (average daily population, fractional floats) or integer headcounts; ALOS is days.
- Checksums generated: 2026-07-02

## Source Provenance

Full provenance (URLs, download method, license, citation requirements) in
[`_provenance.md`](_provenance.md), maintained by the scripted downloader.

- **Feed 1 — ICE detention statistics workbooks**: <https://www.ice.gov/detain/detention-management>, retrieved 2026-07-02 via `src/etl/criminal_justice/ice_detention/detention_population/download.py` (scripted fetch; file URLs scraped per run — they rotate). Public domain (US federal work).
- **Feed 2 — Deportation Data Project (`ddp/`)**: <https://deportationdata.org/data/processed/ice.html>, retrieved 2026-07-02, same script. CC-0, but DDP **requires a specific citation** — exact wording in `_provenance.md` (differs between the FOIA record-level files and the detention-management collation).

## File Checksums

Generated: 2026-07-02

| File | SHA-256 |
|------|---------|
| ice_detention_stats_fy2020_2026-07-02.xlsx | 2c30cee5f1cd4b26ab1aa8c9ddf3e23b7e12929a201e0d1841f755c078d26067 |
| ice_detention_stats_fy2021_2026-07-02.xlsx | 66ce2cc482f72082c626eab08f45b8686c5ab3d7c6b8d758cc2bd6b3fcecc697 |
| ice_detention_stats_fy2022_2026-07-02.xlsx | b29a5d4a48221c839c18370baece46cf4b89a3c3dd84c173f7f145f627cf9e82 |
| ice_detention_stats_fy2023_2026-07-02.xlsx | 12185efdb1215b9e3242c9f4f4eda5b856ce3fd4978917d105e1a4edf4226129 |
| ice_detention_stats_fy2024_2026-07-02.xlsx | a177b8bdfe5eb391ed458ed84de810146a019cb25898387c27178357e20b7e30 |
| ice_detention_stats_fy2025_2025-09-24.xlsx | 3b9e2d626b1e249b2c87539554758333b27bc0da64a37e5dac99944a210c0782 |
| ice_detention_stats_fy2025_2026-07-02.xlsx | 3b9e2d626b1e249b2c87539554758333b27bc0da64a37e5dac99944a210c0782 |
| ice_detention_stats_fy2026_2026-04-09.xlsx | bbf3a29014d686f7eccce397804c9fdba7d2bf9b5fcea0180bc98443ffd4fbed |
| ddp/detention-stays-latest.parquet | dbe81de61de8cfb4d0e6ec4c1c6eb182c2c6b211206611b3702efe5b02215bb0 |
| ddp/detention-stints-latest.parquet | 252c211590b9192356ccc6a2f497e1ddbae70e291f50efddec5ea8ad34d73dff |
| ddp/facilities-daily-population-latest.parquet | 649722ae79088a91aab26b8f4f7889a71e12e56a36ee102213ba632293312017 |
| ddp/detention-management.xlsx | 514225d3fe80b3ebed9bcc8d7ab23cb0a26e0768169bbc1602dfc3e7d103f43c |
| ddp/ddp_codebook.html | d5ce7d0f9d2d5ed81db3b1152795d1c331ed590fb6712093139b7dcab0d4fed0 |
| ddp/ddp_codebook-facilities.html | 1736a27db1c549a520d6439d9961d77cc23bd8235655095a65deeed933813825 |
| ddp/ddp_codebook-facilities-daily-population.html | 32ab5c3e3982fde0cff354f531683843db596d78c998575e1e084ca22d83519b |

Note: the two FY2025 workbooks are byte-identical (same hash) — the undated FY25
URL now serves the final end-of-FY snapshot. **Process only one.**

## Excel Sheet Structure

### Feed 1 — ICE workbooks (sheet set grows over the years)

| File(s) | Sheets | Notes |
|---------|--------|-------|
| FY2020 | Header, ATD EOFY20, Detention EOFY2020, **Facilities EOYFY20␠** (Data), Footnotes | Facilities sheet name has a **trailing space** |
| FY2021 | Header, ATD FY21 YTD, Detention FY21 YTD, **Facilities FY21 YTD** (Data), Trans. Detainee Pop. FY21 YTD␠, Footnotes | |
| FY2022 | + ␠ICLOS and Detainees (leading space), Monthly Bond Statistics, Semiannual, Vulnerable & Special Population; **Facilities FY22** (Data) | |
| FY2023 | Same as FY22 plus a second ATD sheet (`ATD FY24 YTD` — mislabeled leftover); **Facilities EOFY23** (Data) | |
| FY2024 | + Monthly Segregation; **Facilities EOFY24** (Data) | |
| FY2025 (×2) | Same set as FY24; **Facilities FY25** (Data) | |
| FY2026 | Segregation sheet renamed `FY26 Monthly Segregation`; **Facilities FY26** (Data) | |

Sheet classification:
- **Data (use): `Facilities …`** — one row per detention facility nationwide, GA-filterable via `State`. The only facility-level population sheet.
- **Skip (national/AOR aggregates, no GA breakdown)**: ATD (Alternatives to Detention), Detention FYxx (multi-block national summary tables), ICLOS and Detainees, Monthly Bond Statistics, Semiannual, Trans. Detainee Pop. (national totals + AOR counts), Vulnerable & Special Population.
- **Skip (facility-level but out of scope for this topic)**: Monthly Segregation — stacked month-blocks of facility segregation placement counts; messy multi-block layout; candidate for a separate future topic.
- **Metadata**: Header (methodology prose), Footnotes (definitions: ADP, ALOS, criminality, threat levels, facility types, guaranteed minimums).

Sheet names must be resolved per-file by fuzzy match (`'Facilities' in name`), not hardcoded — they carry FY suffixes, trailing/leading spaces, and EOFY/YTD variants.

### Feed 2 — `ddp/detention-management.xlsx` (DDP collation)

23 sheets, one per ICE detention-management dataset, each stacking **every
historical biweekly snapshot** with `fiscal_year`, `file_date`, `pull_date`
columns and snake_case headers. Relevant here:

| Sheet | Shape | Notes |
|-------|-------|-------|
| Facilities | 20,222 × 45 | All 146 snapshots FY2019–FY2026 (file_date 2019-10-07 → 2026-04-09) of the Feed-1 Facilities sheet, columns unioned across eras. **Supersedes per-FY workbook parsing** — includes FY2019 (not in Feed 1) and full intra-year snapshot history. |
| Facility ALOS | 2,038 × 6 | `name`, `alos_fiscal_year`, `alos`, `fiscal_year`, `file_date`, `pull_date` |
| Others (ADP by agency, book-ins, bond, segregation, …) | — | National/AOR aggregates — skip |

## Summary

ICE immigration-detention population at the **facility level**, filterable to the
14–18 Georgia facilities (Stewart Detention Center, the three Folkston IPCs,
Irwin, Robert A. Deyton, Folkston/Atlanta holds, county jails). Metrics:

- **Average daily population (ADP)**, fiscal-YTD, broken down three independent ways: security classification (Level A–D), criminality × gender (Male/Female × Criminal/Non-Criminal), and ICE threat level (1/2/3/none), plus ADP subject to mandatory detention (Feed 1 / DDP Facilities collation).
- **Average length of stay (ALOS)** in days, per facility per FY.
- **Guaranteed-minimum beds** (contractual bed floor) per facility.
- **Daily headcounts** per facility (DDP `facilities-daily-population`): n_detained (distinct individuals at any point in the day), at midnight, by gender, convicted-criminal count, possibly-under-18 count — daily panel 2022-10-01 → 2026-03-10.
- **Individual-level detention stints/stays** (DDP FOIA records, 2.6M / 1.1M rows) — PII-bearing; bronze-only aggregation source.

## Eras

Era detection applies to the Feed-1 **Facilities** sheets. The first 23 columns
(`Name` … `Guaranteed Minimum`) are **identical in every year** except the ALOS
column carries the FY prefix (`FY20 ALOS` … `FY26 ALOS`). Only the trailing
inspection-column block drifts, giving 5 eras:

| Era | Years | Cols | Inspection tail |
|-----|-------|------|-----------------|
| 1 | FY2020–FY2021 | 31 | `Last Inspection Type/Standard/Rating - Final/Date` + `Second to Last Inspection Type/Standard/Rating/Date` |
| 2 | FY2022 | 30 | Era-1 tail minus `Second to Last Inspection Rating` |
| 3 | FY2023 | 33 (+2 unnamed all-null) | ODO/Nakamoto split: `ODO Inspection End Date`, `ODO Last Inspection Standard`, `ODO Final Rating`, `Last Nakamoto …` (×3), `Second to Last Nakamoto …` (×3) |
| 4 | FY2024–FY2025 | 28 | `Last Inspection Type`, `Last Inspection End Date`, `Pending FY25 Inspection`, `Last Inspection Standard`, `Last Final Rating` |
| 5 | FY2026 | 27 | Era-4 tail minus `Pending FY25 Inspection` |

Header row position also drifts: the column-name row (first cell `Name`) is
sheet row index 6 (FY20–22, FY24–25), 5 (FY23), or 9 (FY26) — detect by scanning
for the `Name` cell, don't hardcode.

### Shared core columns (all eras)

| Column | Description |
|--------|-------------|
| Name | Facility name (uppercase; spelling/format drifts across years — see ETL Considerations) |
| Address, City, State, Zip | Facility location. `State` is 2-letter postal (46 values incl. PR/MP/GU). `Zip` parses as **Int64 in FY20–style files, String in FY26** — zero-pad to 5 |
| AOR | ICE Area of Responsibility (3-letter code; all GA facilities = `ATL`) |
| Type Detailed | Facility contract type — 11 values in FY26: USMS IGA (99), IGSA (37), DIGSA (25), CDF (19), BOP (7), SPC (5), STAGING (4), USMS CDF (3), STATE (2), FAMILY (1), DOD (1); older files also JUVENILE, Other |
| Male/Female | Sex housed: Female/Male (142), Male (58), Female (1), null (2) in FY26 |
| FY{yy} ALOS | Average length of stay, days (float; FY-to-date) |
| Level A–D | ADP by security classification level (float) |
| Male Crim / Male Non-Crim / Female Crim / Female Non-Crim | ADP by gender × criminality (float) |
| ICE Threat Level 1 / 2 / 3 / No ICE Threat Level | ADP by ICE threat level (float) |
| Mandatory | ADP subject to mandatory detention (float) |
| Guaranteed Minimum | Contractual guaranteed-minimum beds (int; null when no guarantee — 139/203 null in FY26) |

The three ADP breakdowns (Level, gender×criminality, threat) are each intended
to sum to total facility ADP — usable as a cross-column quality check.

### Era 5 representative: FY2026 (`Facilities FY26`, 203 rows)

#### Sample Data (selected columns)

```
Name                              City       State AOR  Type Detailed  Male/Female  FY26 ALOS  Level A  Male Crim  Male Non-Crim  Mandatory  Guaranteed Minimum
RIO GRANDE DETENTION CENTER       LAREDO     TX    HLG  USMS CDF       Male         57.83      573.45   41.73      582.51         374.66     275
PHELPS COUNTY JAIL (MO)           ROLLA      MO    CHI  USMS IGA       Female/Male  37.62      7.90     2.31       9.58           8.20       null
CAMBRIA COUNTY PRISON             EBENSBURG  PA    PHI  USMS IGA       Male         8.12       28.43    5.96       19.20          18.63      null
COASTAL BEND DETENTION FACILITY   ROBSTOWN   TX    HLG  USMS IGA       Female/Male  6.17       37.14    7.04       35.84          41.40      null
STEWART DETENTION CENTER          LUMPKIN    GA    ATL  DIGSA          Female/Male  47.21      —        539.42     1161.27        1345.72    1600
```

#### Statistics (FY26, ADP/metric columns)

| Metric | mean | min | max |
|---|---|---|---|
| FY26 ALOS | 28.29 | 0.58 | 90.71 |
| Level A | 199.51 | 0.08 | 1709.33 |
| Level B / C / D | 47.75 / 43.32 / 35.34 | 0 | 427 / 418 / 493 |
| Male Crim / Male Non-Crim | 65.83 / 219.84 | 0 | 665.18 / 1944.10 |
| Female Crim / Female Non-Crim | 4.62 / 35.62 | 0 | 143.09 / 821.11 |
| ICE Threat Level 1 / 2 / 3 / none | 39.55 / 19.48 / 28.59 / 238.30 | 0 | 522.92 / 192.85 / 332.24 / 1909.77 |
| Mandatory | 181.59 | 0.17 | 1483.94 |
| Guaranteed Minimum (n=64) | 712.83 | 70 | 5000 |

#### Null Counts (FY26)

`Guaranteed Minimum` 139/203; inspection tail 21–61; `State` 1 (Imperial
Regional, CA — geocodable from city/zip); `Male/Female` 2. All ADP/ALOS
columns: 0 nulls.

#### Categorical Columns (FY26)

| Column | Distinct values |
|--------|----------------|
| State | 46 — TX (25), FL (19), LA (12), … **GA (8)** |
| AOR | 24 — SPM, CHI, NOL, MIA, …, ATL (10) |
| Type Detailed | USMS IGA, IGSA, DIGSA, CDF, BOP, SPC, STAGING, USMS CDF, STATE, FAMILY, DOD |
| Male/Female | Female/Male, Male, Female |
| Last Inspection Type | ODO, ORSA, Preoccupancy, ODO OASIP |
| Last Inspection Standard | NDS 2019, PBNDS 2011 - 2016 Revisions, ORSA NDS 2019, NDS 2025, FPBDS, NDS, USMS IGA, FRS |
| Last Final Rating | Pass (135), Fail (5), Final Rating Pending (2) |

#### Suppression Markers (Feed 1)

None in the Facilities sheets — all metric columns parse cleanly as
Float64/Int64 in every era. But `Last Inspection End Date` (era 4–5) mixes
dates with the strings `Scheduled FY26` / `Scheduled FY27`.

### Era 1 representative: FY2020 (`Facilities EOYFY20 `, 170 rows)

Same 23-column core (metrics verified: ADP floats, ALOS float, Guaranteed
Minimum Int64 with 113/170 null). Differences: `Zip` parses as **Int64**
(leading-zero loss for MA/RI/etc.); inspection tail uses the pre-2023 scheme
with `Last Inspection Rating - Final` values like Meets Standard / Acceptable /
Pending and `Last Inspection Date` as string `M/D/YYYY`. Six GA facilities
(Stewart, Irwin, Folkston Main+Annex, Deyton, Cobb County Jail).

### Era 3 note: FY2023

The sheet carries 2 unnamed all-null trailing columns **and 2 footnote prose
rows inside the data area** (bottom of sheet, only `Name` populated with
"ODO inspections are conducted…" text) — the transform must drop both.

## Feed 2 — DDP files

### `ddp/facilities-daily-population-latest.parquet` — 888,699 × 9

Daily panel: 707 facilities × 1,257 days (**2022-10-01 → 2026-03-10**, no gaps,
zero nulls). All 14 GA facility codes present with full 1,257-day coverage.

| Column | Description |
|--------|-------------|
| detention_facility_code | ICE DETLOC code (e.g. `STWRTGA`) — **the natural facility key**, matches stints/stays |
| date | Calendar date |
| n_detained | Distinct individuals detained at any point during the day |
| n_detained_at_midnight | Headcount at midnight |
| n_detained_male / n_detained_female | By ICE-reported gender |
| n_detained_convicted_criminal | Convicted-criminal subset |
| n_detained_possibly_under_18 | Possibly-minor subset |
| detention_facility | Facility name |

GA facilities by mean daily population: Stewart (`STWRTGA`, 1610.4), Folkston
Main (`FIPCMGA`, 586.4), Folkston Annex (`FIPCAGA`, 229.2), Folkston D Ray
(`FIPCDGA`, 152.7), Atlanta US Pen (`BOPATL`, 40.9), … down to Chatham/Hall/
Atlanta Pretrial (≈0). **No state column** — GA membership must come from a
code→state map derived from the stints file (or a maintained GA code list).

### `ddp/detention-management.xlsx`, sheet `Facilities` — 20,222 × 45

Union of all Feed-1 Facilities columns (snake_case) + `fiscal_year`,
`file_date`, `pull_date`. 146 snapshots, FY2019 (213 rows) → FY2026 (1,516
rows). GA: 715 rows. Read with `infer_schema_length=0` (dtype fallback) and
cast: suppression markers `*`, `N/A`, `\xa0` in `guaranteed_minimum`
(3,001 rows) and one misaligned row with `Scheduled` in `ice_threat_level_1`.
Facility names here also carry **case variants** (`COBB COUNTY JAIL` vs
`Cobb County Jail`) and truncation variants (`FOLKSTON D RAY ICE PROCES`).

### `ddp/detention-stints-latest.parquet` — 2,617,844 × 61 / `detention-stays-latest.parquet` — 1,087,417 × 70

Individual-level FOIA records (one row per facility stint / per detention
stay), book-ins 2004-12 → 2026-03-11. Rich attributes: facility code + city/
state/county, book-in/out timestamps, gender, birth_year, citizenship, criminality,
threat level, release reason, bond, `likely_duplicate` flag (11,671 in stints),
`stay_ID`/`stint_ID`/`unique_identifier`. GA stints: 18 facility codes
(Stewart 40,756; Folkston Main 20,343; Atlanta Hold 20,094; …). **PII — bronze
only; aggregate to facility-month or coarser before gold** (per `_provenance.md`).

## ETL Considerations

1. **Recommended primary sources.** (a) Facility-FY ADP/ALOS metrics: the DDP `Facilities` collation sheet (one parse, FY2019–FY2026, all snapshots) — take the **latest `file_date` per fiscal year** to get EOY (closed FYs) / newest-YTD (current FY) values; the per-FY ICE workbooks then serve as verification. (b) Facility-month population: aggregate the DDP daily-population parquet (means of daily headcounts). The stints/stays files are optional aggregation sources only.
2. **No facility code in Feed 1.** ICE workbooks identify facilities by name only, and names drift across years (`MAIN - FOLKSTON IPC (D RAY JAMES)` → `FOLKSTON MAIN IPC`; `ROBERT A. DEYTON` vs `ROBERT A DEYTON`; case and truncation variants in the DDP collation). Build a name→DETLOC crosswalk from the stints file's (code, name, city, state) pairs; `detention_facility_code` should be the facility natural key in gold. Scope is GA-only (~14–18 facilities), so the crosswalk is small and auditable.
3. **ADP values are fractional fiscal-YTD averages**, not headcounts — keep as Float64, never round to int. FY totals from the current FY are year-to-date through the snapshot date; label the year column as fiscal year (Oct–Sep).
4. **Header/sheet drift (Feed 1)**: header row index 5/6/9 (locate the `Name` cell); sheet names carry trailing/leading spaces and FY/EOFY/YTD suffixes (match on substring). FY23 has 2 unnamed null columns + 2 footnote rows inside the data area — drop rows where `State` is null AND all ADP columns are null (but keep the legitimate null-State Imperial Regional row in FY26 — safer filter: drop rows whose `Name` length > ~60 or where all numeric columns are null).
5. **Zip dtype drift**: Int64 in some files, String in others — cast to string and zero-pad to 5 (dimension attribute only; GA zips unaffected).
6. **Duplicate FY2025 file**: byte-identical snapshots; process exactly one.
7. **DDP collation dtypes**: read with `infer_schema_length=0`; null out `*`, `N/A`, `\xa0` in `guaranteed_minimum`; guard against the one misaligned `Scheduled` value in `ice_threat_level_1`; normalize name casing before crosswalk matching.
8. **DDP daily population has no state column** — filter GA via the code→state map from stints. Zero-population rows (e.g., hold rooms, county jails with ADP≈0) are real panel rows, not missing data.
9. **Quality checks available**: Level A+B+C+D ≈ Male Crim+Male Non-Crim+Female Crim+Female Non-Crim ≈ sum of threat levels (each ≈ total ADP); daily `n_detained_male + n_detained_female ≈ n_detained`; DDP-vs-workbook agreement per FY.
10. **PII gate**: stints/stays are individual-level FOIA records — never emit row-level data to gold; facility-month or coarser only.
11. **Licensing/citation**: Feed 1 public domain; Feed 2 CC-0 **with required DDP citation** (exact wording per file type in `_provenance.md`) — must flow into the contract's attribution/usage text.
12. **Demographics**: only gender (Male/Female/Unknown) exists; no race buckets → the Asian/Pacific-Islander combined-bucket check is **not applicable**. If gender is published as a demographic, use the shared demographics dimension codes and keep `all` vs male/female mutual exclusivity in mind (n_detained = all; male/female are the split).
13. **Source volatility**: ICE overwrites the current-FY workbook ~biweekly and can silently revise closed FYs; DDP releases are irregular and flag reliability caveats (hospital stints omitted, some values redacted). Re-runs of the downloader will change checksums for the current FY — re-run this report's checksum step after any refresh.

## Gold Schema Classification

Assuming two gold candidates: **(A) facility × fiscal-year** metrics (from the
DDP Facilities collation / ICE workbooks) and **(B) facility × month** population
(from DDP daily population). A GA detention-facilities dimension (keyed on
DETLOC code) is required either way.

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| detention_facility_code (DDP) | fact_key | facility_code | Natural key (DETLOC); FK to a new detention-facilities dimension |
| Name / name / detention_facility | dimension_attribute | — | facility_name in dimension; name variants resolved via crosswalk |
| Address, City, State, Zip | dimension_attribute | — | Location in dimension; map city/county → county FIPS for county linking |
| AOR | dimension_attribute | — | Constant `ATL` for GA — dimension only |
| Type Detailed / type_detailed | dimension_attribute | — | facility_type in dimension (11 codes; spell out in dimension) |
| Male/Female / male_female | dimension_attribute | — | sex_housed in dimension |
| FY{yy} ALOS / alos | fact_metric | avg_length_of_stay_days | Float days, ≥ 0 (unit: ratio); topic-A **key-metric candidate is ADP, not ALOS** |
| Level A–D | fact_metric | adp_security_level_a … _d | Float ADP (unit: ratio, ≥0); wide — the 3 breakdowns overlap, long format would double-count |
| Male/Female Crim/Non-Crim | fact_metric | adp_male_criminal, adp_male_noncriminal, adp_female_criminal, adp_female_noncriminal | Float ADP; sum = total ADP (candidate key metric `adp_total` derived as this sum) |
| ICE Threat Level 1/2/3/None | fact_metric | adp_threat_level_1 … adp_no_threat_level | Float ADP |
| Mandatory | fact_metric | adp_mandatory_detention | Float ADP |
| Guaranteed Minimum / guaranteed_minimum | fact_metric | guaranteed_minimum_beds | Int count, ≥0; null = no contractual floor (also `*`/`N/A` → null in DDP collation) |
| Inspection tail columns (all eras) | not_in_gold | — | Facility-compliance data, era-inconsistent; candidate for a future facility_inspections topic |
| fiscal_year / file_date / pull_date (DDP collation) | fact_key / not_in_gold | year | fiscal_year → `year`; keep only latest file_date per FY; file_date/pull_date dropped |
| date (daily pop) | fact_key | year + month | Aggregate daily → facility-month (means); calendar month |
| n_detained, n_detained_at_midnight | fact_metric | avg_daily_detained, avg_midnight_detained | Monthly mean of daily counts (unit: ratio, ≥0); n_detained is topic-B key-metric candidate |
| n_detained_male / _female | fact_metric or demographic split | avg_daily_detained_{male,female} | Or long `demographic` (all/male/female) if joined to demographics dim |
| n_detained_convicted_criminal | fact_metric | avg_daily_convicted_criminal | Monthly mean |
| n_detained_possibly_under_18 | fact_metric | avg_daily_possibly_under_18 | Monthly mean; near-zero in GA |
| All stints/stays columns | not_in_gold | — | PII; bronze-only aggregation source (facility code→state map, name crosswalk) |
| All other workbook sheets (ATD, Detention, ICLOS, Bond, Semiannual, Segregation, Trans., Vulnerable) | not_in_gold | — | National/AOR aggregates, or out-of-scope facility data (segregation) |
