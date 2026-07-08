# district_sentences — Bronze Data Structure

## Overview

- Topic: district_sentences
- Source: federal_justice (US Sentencing Commission — individual-offender annual datafiles, "Standardized Research Data" / Public Release)
- Files: 24 annual zip files spanning FY2002–FY2025 (one national zip per federal fiscal year) + 1 codebook PDF
- Unreadable files: none (all 24 zips pass CRC; a recent CSV member parses; SAS-era members are fixed-width `.dat` + `.sas`/`.sps` layout scripts)
- Year representation: **federal fiscal year in the filename** (`opafy{YY}nid…`, YY = 02…25 → FY2002…FY2025). A sentencing fiscal-year variable is also carried inside each file; the individual datafile for FY`YY` contains offenders sentenced in that fiscal year (Oct 1 – Sep 30).
- Filename-to-data year offset: **same** (the `opafy{YY}` fiscal year is the sentencing fiscal year of the records).
- Detail levels: **individual-offender microdata** (one row per federally sentenced offender), **national coverage**; a federal **judicial-district** variable (`DISTRICT`) isolates Georgia's three districts. Gold target is `federal_district × fiscal_year` aggregation, filtered to GA.
- Percentage scale: N/A — no percentage columns; values are counts, codes, sentence lengths (months), and numeric guideline levels.
- Checksums generated: 2026-07-04

## Source Provenance

- **Source URL**: datafiles listing page <https://www.ussc.gov/research/datafiles/commission-datafiles>;
  per-year files resolve under `https://www.ussc.gov/sites/default/files/zip/opafy{YY}nid_csv.zip` (CSV, FY2012+) and `…/opafy{YY}nid.zip` (SAS/SPSS, all years); codebook under `…/pdf/research-and-publications/datafiles/USSC_Public_Release_Codebook_FY99_FY25.pdf`
- **Retrieved**: 2026-07-04 (UTC)
- **Method**: scripted fetch — `uv run python -m src.etl.criminal_justice.federal_justice.district_sentences.download` (scrapes the datafiles page for the real per-year `opafy{YY}nid*.zip` links, prefers CSV and falls back to SAS/SPSS, verifies byte size against `Content-Length`, idempotent skip-if-present). Full details in [`_provenance.md`](_provenance.md). **Zips are never extracted** — the transform must read members directly from the zips.
- **License**: US federal government work — public domain (17 U.S.C. §105). Cite US Sentencing Commission. Records are PII-limited public-release microdata (offender `NAME` is present in the raw layout but is not carried to gold).

## File Checksums

Generated: 2026-07-04

| File | SHA-256 |
|------|---------|
| USSC_Public_Release_Codebook_FY99_FY25.pdf | 467f73e956a15a1427dce4ab9efb7659f3fe4ba5c1da573ac12fc777e55c2499 |
| opafy02nid.zip | 576a36f712d4e51cde3ef66e4c7800204d858e69012d8263960f46592fee5f76 |
| opafy03nid.zip | 3067be6e8ef1eeb73d93bc1af81bc4248e0163b78bbd046ac4a5afbdbbbefde4 |
| opafy04nid.zip | 68578a24d843166e39402e9d026f2733831efc68fbff6a4dd3ca08c87d4ce89e |
| opafy05nid.zip | c92163f25ba4914cb34c3d89ac46bf4aa769bdf3e0bf63f8c555af112a9f2651 |
| opafy06nid.zip | 3b185b67ae67f602fb1165f481e9827852409a39d86b69b0311f249ab384129f |
| opafy07nid.zip | d3acb754630bedd2a0da234ae91822fa3b901ab702aa5a252a82fed2ea585aae |
| opafy08nid.zip | e8456bbe11ad535d11418e51f9309d49647775bdf2d96a11c423fc2819ef1dbc |
| opafy09nid.zip | b8f27b77ea0f931a852bb2ce57eb5ad9d1400170690b817a5333fc9df8fa7c3a |
| opafy10nid.zip | ab5d65e78b8c89f2f447fd1890bd47357d1be10559da1e439a51b79bd7c4aa77 |
| opafy11nid.zip | 5e221227f7f5331b0b6cc79169383957b5b6699d13c5ac66c850c846081a520b |
| opafy12nid_csv.zip | c1feb05e63881e75249005f6c0e964dc85c7e81eb29e4b4dc37bae5155b7828c |
| opafy13nid_csv.zip | 094624f1c414b9b4f53e9fe1d0d8ea44151bae6e6faab45506ac0024c18b3534 |
| opafy14nid_csv.zip | 0898153084b8ac1bd3a0589db15b3807f343afa24ab0acbcb3e06f81937e1bca |
| opafy15nid_csv.zip | ec540dfc0da193fbaeb74b27776bd7cffe4225dcf98e3bd78788d40e41108bab |
| opafy16nid_csv.zip | b046f4d1fc1feeeb7b1be344ac48080cc29756d7856abee11c20877805c9938f |
| opafy17nid_csv.zip | 21b33869f8ed688060033337970079b52ebd22cf32e62cc37239a9e9b815030e |
| opafy18nid_csv.zip | 9efc867dbbd06f086e466d9578bd810eddc04fad78e91ca128fc83bc536cbaab |
| opafy19nid_csv.zip | b98dbea2e6e9a552f9809019656fdc6a067cddde100c71fdae0f0584e91e3b3c |
| opafy20nid_csv.zip | 45f27c28677211c52e782a2faf57f28a189cab072007aac27f23a8f9c0a5e566 |
| opafy21nid_csv.zip | 60b3c3fa6e63459927c119c91afa9bb89923c77a9b660fb468ea05bf2ec98cb0 |
| opafy22nid_csv.zip | 56e4305b0460f523bb8721b8f89a4499fee8a2c076e47e6a5871509c79436ba6 |
| opafy23nid_csv.zip | 3c32fa89fd7240886a5f377b8d2f813744b7282434baecaf6d7df0e42b4d8d32 |
| opafy24nid_csv.zip | 1a54f4fec666508e3d9a3df9513fd6dbc8a4c38bd24c778e466eadc31df43568 |
| opafy25nid_csv.zip | 1b1000f2bb162053c70c9ae207e20a845aede922c2b37d6a3ceb9351e7e19d7b |

## Zip / Table Structure

Not Excel — each annual zip bundles the single national individual-offender file in one of two formats. **The layout differs by fiscal year:**

| Year range | Zip name | Members | Format |
|------------|----------|---------|--------|
| FY2002–FY2011 | `opafy{YY}nid.zip` | `opafy{YY}nid.dat`, `opafy{YY}nid.sas`, `opafy{YY}nid.sps` | **Fixed-width ASCII** (`.dat`, ~1.2–4.1 GB uncompressed) + a **SAS `INPUT` statement** (`.sas`) and **SPSS syntax** (`.sps`) that define the column names, byte positions, and value labels. There is no header row — the `.sas`/`.sps` layout script is required to parse the `.dat`. |
| FY2012–FY2025 | `opafy{YY}nid_csv.zip` | `opafy{YY}nid.csv` | **Single comma-delimited CSV** with a header row (~1.5–1.6 GB uncompressed). FY2025 has **22,149 columns**; the column set is enormous (thousands of guideline / offense-detail variables) and grows/changes across years. |

(The SAS/SPSS zip `opafy{YY}nid.zip` also exists for FY2012–FY2025 but the CSV variant is preferred and downloaded for those years. The FY2016/FY2017 SAS zips are named with a dash, `opafy16-nid.zip`/`opafy17-nid.zip`, on the source page — not downloaded since CSV is present.)

**The transform must branch on format by year**: fixed-width parse via the `.sas` layout for FY2002–FY2011; CSV read with a header for FY2012–FY2025. Only a small subset of columns is needed for gold (district, fiscal year, sentence length, guideline position, departure, demographics, drug type) — select those explicitly rather than materializing all ~22k columns.

## Summary

The USSC individual-offender datafile is the authoritative record of **every individual sentenced under the federal system in a fiscal year** (one row per offender), FY2002–FY2025 here (the series runs FY1987–present; the codebook documents FY1999–FY2025). The headline user metrics are **sentence length imposed** (`SENTTOT` / `SENSPLT0` / `TOTPRISN`, total prison months), **guideline position** (`GLMIN`/`GLMAX` trumped guideline min/max, `XFOLSOR` final offense level, `XCRHISSR` criminal-history category), **departures/variances** (`DEPART`, `BOOKERCD` post-Booker sentencing position, `SAFETY` safety-valve), **primary offense / drug type** (`DRUGTYP1`–`DRUGTYPX`, `DRUGMIN` mandatory minimum), and offender **demographics** (`MONRACE`/`NEWRACE`, `MONSEX`, `AGE`/`YEARS`, `NEWCIT` citizenship). A federal **judicial-district** variable (`DISTRICT`) makes Georgia's three districts filterable. FY2024 has **61,678** sentenced-offender rows nationally.

## Eras

The meaningful partitions are **file format** and a **FY2018 methodology break**, not annual column churn (the column set drifts every year).

### Era 1: FY2002–FY2011 — fixed-width SAS/SPSS

Fixed-width `.dat` + `.sas`/`.sps` layout scripts (see Zip/Table Structure). Column names and byte positions come from the `.sas` `INPUT` statement; there is no CSV header. Uncompressed `.dat` sizes range ~1.17 GB (FY02) to ~4.07 GB (FY10).

### Era 2: FY2012–FY2025 — CSV

Single comma-delimited `.csv` member with a header row. Very wide (22,149 columns in FY2025). Same conceptual variables as Era 1 plus a large and growing set of guideline/offense-detail columns.

**Key columns (both eras; exact names from `USSC_Public_Release_Codebook_FY99_FY25.pdf`):**

| Column | Description |
|--------|-------------|
| `DISTRICT` | Judicial district where sentenced. **Georgia: 32 = Northern, 33 = Middle, 34 = Southern** (NUM, range 00–96). |
| `CIRCDIST` | Circuit-ordered district code (Sourcebook order). **Georgia: 92 = Middle, 93 = Northern, 94 = Southern.** |
| `SENTTOT` | Total prison sentence in months (excluding alternatives), 0.01–9997. Headline sentence-length metric. |
| `SENSPLT0` | Total prison sentence in months, 0–9997 (0 = probation/time-served variant). |
| `TOTPRISN` | Months of imprisonment (PSR/SOR source), 0–9998. |
| `GLMIN` / `GLMAX` | Trumped guideline minimum / maximum (months). |
| `XFOLSOR` | Final offense level (1–99). `XCRHISSR` = final criminal-history category (1–6). |
| `DEPART` | Departure status (0 = no departure, …). `BOOKERCD` = post-Booker sentencing position (12 categories; recoded FY2018+). |
| `SAFETY` | Safety-valve indicator (0/1). `DRUGMIN` = drug mandatory minimum (0–9990). |
| `DRUGTYP1`–`DRUGTYPX` | Drug types involved (1–161; multiple counts per case). |
| `MONRACE` / `NEWRACE` | Race (self-reported / recoded). `MONSEX` = sex (0 = male, 1 = female). |
| `AGE` / `YEARS` | Age at sentencing (15–105) / age category. `NEWCIT` = citizenship (0 = US). |
| `DISPOSIT` | Case disposition (0 = no imprisonment, …). |
| `NAME` | Offender name (**not carried to gold — aggregate away**). |

**FY2018 methodology break:** the USSC revised several derived variables (notably the post-Booker sentencing-position recode `BOOKERCD` and departure/variance derivations) "from FY2018-present." Do **not** pool a departure/variance series across the FY2017→FY2018 boundary without documenting the break; treat pre-FY2018 and FY2018+ as separate methodology regimes for those variables.

## ETL Considerations

1. **Read directly from zips; never extract.** For FY2012–FY2025 read the single `.csv` member; for FY2002–FY2011 parse the fixed-width `.dat` using the byte positions in the accompanying `.sas`/`.sps` layout script. (Provenance contract: no extraction to disk.)
2. **Select columns explicitly.** The CSV-era files have up to ~22,149 columns; never materialize all of them. Read only the gold-relevant variables listed above. Column *names* are stable for the core variables even as the wide tail changes year to year.
3. **Filter to Georgia by `DISTRICT` ∈ {32, 33, 34}** (Northern/Middle/Southern). `CIRCDIST` {93, 92, 94} is the equivalent circuit-ordered filter — pick one variable and document it; do not mix the two code schemes.
4. **Sentence-length units are months.** `SENTTOT`/`SENSPLT0`/`TOTPRISN` are in months with **sentinel high values** (9997/9998 = life/indeterminate placeholders; `.`/missing markers exist). NULL sentinels rather than averaging them into a mean sentence (a life sentence coded 9997 would blow up an average). Document which sentence variable the gold metric uses (Commission analyses typically use `SENTTOT` with capped variants for life).
5. **FY2018 methodology break** (see Eras) — version any departure/variance/`BOOKERCD`-derived metric across FY2017→FY2018.
6. **Year comes from the filename** (`opafy{YY}`) and is echoed by an in-file fiscal-year variable; verify they agree. FY2002–FY2025 map to YY 02–25.
7. **Codes are numeric with value labels in the codebook** — race/sex/citizenship/drug-type/disposition are integer codes; a per-variable recode map (from the codebook's value labels) is required if any reach gold as categoricals. Value labels are stable for the core demographic variables across FY2002–FY2025.
8. **Grain is one offender.** Aggregating to `federal_district × fiscal_year` yields counts (sentenced offenders) and distributional metrics (mean/median sentence months, share with departures, share by primary offense/drug type). District ≠ county — this is a **sub-state, non-county** grain (see Gold Schema Classification).
9. **Coverage is national and complete** for sentenced offenders; there is no suppression. Georgia rows are a filtered subset (~3 districts). USSC counts sentenced individuals, **not** filings/terminations (that is the FJC IDB `district_filings` topic).

## Gold Schema Classification

Proposed gold grain: **federal_district × fiscal_year** (aggregated from national individual-offender microdata, filtered to GA districts 32/33/34). This is a **federal-district grain**, distinct from the county-FIPS grain used by most criminal_justice topics — decide the serving model for district-grain topics before building (see blueprint source #17).

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| `DISTRICT` | fact_key | federal_district | filter/keep {32,33,34}; map to a GA-district identifier (GA-N/GA-M/GA-S) |
| filename `opafy{YY}` (+ in-file FY) | fact_key | fiscal_year | FY2002–FY2025 |
| (row count) | fact_metric | offenders_sentenced | count of offender rows; unit: count; **key_metric candidate** |
| `SENTTOT` | fact_metric | mean/median_sentence_months | central tendency of prison months; NULL life/indeterminate sentinels first |
| `DEPART` / `BOOKERCD` | fact_metric | share_with_departure | proportion; version at FY2018 break |
| `GLMIN` / `GLMAX` / `XFOLSOR` / `XCRHISSR` | fact_metric (optional) | guideline_min/max, offense_level, criminal_history | distributional summaries |
| `DRUGTYP1` / primary offense | fact_categorical (optional) | primary_offense / drug_type | recode from codebook value labels |
| `MONRACE`/`NEWRACE`, `MONSEX`, `AGE`/`YEARS`, `NEWCIT` | fact_categorical → demographic | demographic | map to the demographics dimension if a demographic breakdown is published |
| `CIRCDIST` | not_in_gold | — | redundant with `DISTRICT` (alternate code scheme) |
| `NAME` | not_in_gold | — | PII; aggregated away |
| ~22,000 other guideline/offense-detail columns | not_in_gold | — | below gold grain; not aggregated |
