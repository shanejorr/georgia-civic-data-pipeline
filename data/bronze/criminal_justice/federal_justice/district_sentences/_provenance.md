# Provenance — USSC individual-offender datafiles (federal district sentences)

## Source

- **Publisher**: United States Sentencing Commission (USSC) — Commission
  Datafiles, "Standardized Research Data" / Individual Offender Public Release
  files.
- **Program / listing page**: <https://www.ussc.gov/research/datafiles/commission-datafiles>
- **File patterns** (under `https://www.ussc.gov/sites/default/files/zip/`):
  - CSV (FY2012–present): `opafy{YY}nid_csv.zip`
  - SAS/SPSS (all years; only format FY2002–FY2011): `opafy{YY}nid.zip`
    (dash variant `opafy16-nid.zip` / `opafy17-nid.zip` for FY2016/FY2017)
- **Codebook**: `https://www.ussc.gov/sites/default/files/pdf/research-and-publications/datafiles/USSC_Public_Release_Codebook_FY99_FY25.pdf`
  (Public Release codebook, documents variables + district/circuit code lists FY1999–FY2025).

## Retrieval

- **Retrieved (UTC)**: 2026-07-04
- **Method**: `uv run python -m src.etl.criminal_justice.federal_justice.district_sentences.download`
  (`src/etl/criminal_justice/federal_justice/district_sentences/download.py`).
  The script scrapes the datafiles listing page for the real per-year
  `opafy{YY}nid*.zip` links (falling back to the confirmed URL pattern),
  prefers the CSV zip and falls back to the SAS/SPSS zip when CSV is absent,
  downloads each with atomic `.part`→`.replace` writes and a 1 s politeness
  delay, verifies the byte size against the remote `Content-Length`, and skips
  files already present with a matching size (idempotent re-runs). It also
  fetches the Public Release codebook PDF. Zips are kept as-is — **never
  extracted**; the transform reads directly from the zips.
  - Exact invocation (idempotency verified): run 1 downloaded 23 datafiles +
    codebook (FY2010 initially failed a transient HTTP 500 on the CSV probe and
    was recovered on run 2 via the SAS fallback after the downloader was made
    retry-/candidate-resilient); run 2 downloaded FY2010 and skipped the other
    23; run 3 skipped all 24 (0 downloaded).
- **Years downloaded**: FY2002–FY2025 inclusive (24 annual zips).
  - **CSV** (`opafy{YY}nid_csv.zip`): FY2012, FY2013, FY2014, FY2015, FY2016,
    FY2017, FY2018, FY2019, FY2020, FY2021, FY2022, FY2023, FY2024, FY2025.
  - **SAS/SPSS** (`opafy{YY}nid.zip`): FY2002, FY2003, FY2004, FY2005, FY2006,
    FY2007, FY2008, FY2009, FY2010, FY2011 (no CSV variant published for these
    years).
- **Total size**: 604,819,548 bytes datafile zips (576.8 MB) + 768,374 bytes
  codebook (0.75 MB). Per-zip sizes range ~17.9 MB (FY2002) to ~36.9 MB
  (FY2010).
- **Integrity**: all 24 zips pass a CRC listing (`unzip -l`); FY2025 CSV member
  `opafy25nid.csv` parses (22,149 columns); FY2024 CSV has 61,678 offender rows.

## Format notes per era

- **FY2002–FY2011** zips contain three members: `opafy{YY}nid.dat` (fixed-width
  ASCII, ~1.2–4.1 GB uncompressed), `opafy{YY}nid.sas` (SAS `INPUT` layout), and
  `opafy{YY}nid.sps` (SPSS syntax). There is **no header row** — the `.sas`/`.sps`
  layout defines column names and byte positions.
- **FY2012–FY2025** zips contain a single comma-delimited `opafy{YY}nid.csv`
  (~1.5–1.6 GB uncompressed) **with a header row**; the column set is very wide
  (22,149 columns in FY2025) and changes year to year.
- The **Public Release codebook** (`USSC_Public_Release_Codebook_FY99_FY25.pdf`)
  is the authoritative variable dictionary and value-label source (district
  codes, race/sex/drug-type recodes, sentence-length sentinels).

## License

US federal government work — **public domain** (17 U.S.C. §105). No use
restrictions; cite the United States Sentencing Commission. These are the
public-release individual-offender research files; offender `NAME` appears in
the raw layout but is aggregated away and not carried to gold.

## Caveats

- **Aggregate to district-year.** The files are individual-offender microdata
  (one row per sentenced offender), national coverage; gold serves
  `federal_district × fiscal_year` aggregates filtered to Georgia
  (`DISTRICT` ∈ {32 = GA-N, 33 = GA-M, 34 = GA-S}).
- **District ≠ county.** This is a **sub-state, non-county** grain — Georgia's
  three federal judicial districts, not the 159-county FIPS grain used by most
  criminal_justice topics. Decide the district-grain serving model before
  building (blueprint source #17).
- **FY2018 methodology break.** The Commission revised several derived variables
  (post-Booker sentencing position `BOOKERCD`, departure/variance derivations)
  "from FY2018-present." Do not pool a departure/variance series across the
  FY2017→FY2018 boundary without documenting the break.
- **Year-specific layouts.** The parser must branch on format (fixed-width
  FY2002–FY2011 vs CSV FY2012–FY2025) and select only the needed columns from
  the ~22k-column CSV files. Core variable names are stable; the wide tail is
  not.
- **Sentence-length sentinels.** `SENTTOT`/`SENSPLT0`/`TOTPRISN` are in months
  with high sentinel values (9997/9998) for life/indeterminate sentences —
  NULL these before computing mean/median sentence, or a life sentence will
  distort the average.
- **This is sentencing, not filings.** USSC counts individuals *sentenced*;
  federal criminal *filings/terminations* are the FJC IDB `district_filings`
  topic. The two are complementary, not interchangeable.
