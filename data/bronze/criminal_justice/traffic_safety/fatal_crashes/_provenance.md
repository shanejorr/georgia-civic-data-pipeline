# Provenance — NHTSA FARS national annual files (fatal crashes)

## Source

- **Publisher**: National Highway Traffic Safety Administration (NHTSA), US DOT —
  Fatality Analysis Reporting System (FARS).
- **Program page**: <https://www.nhtsa.gov/research-data/fatality-analysis-reporting-system-fars>
- **File listing (human UI)**: <https://www.nhtsa.gov/file-downloads?p=nhtsa/downloads/FARS/>
- **Underlying static server**: `https://static.nhtsa.gov/` (S3-backed; anonymous
  `ListObjectsV2` is enabled, which is how years/files are discovered).
- **File pattern**: `https://static.nhtsa.gov/nhtsa/downloads/FARS/{year}/National/FARS{year}NationalCSV.zip`

## Retrieval

- **Retrieved (UTC)**: 2026-07-02 (downloads completed ~03:30Z; verified 12:15Z)
- **Method**: `uv run python -m src.etl.criminal_justice.traffic_safety.fatal_crashes.download`
  (`src/etl/criminal_justice/traffic_safety/fatal_crashes/download.py`). The script
  discovers available years via anonymous S3 listing of `nhtsa/downloads/FARS/`,
  picks each year's national zip preferring CSV → DBF → SAS, downloads sequentially
  with a 1s delay, verifies the byte size against the listed object size, and skips
  files already present with a matching size (idempotent re-runs). Zips are kept
  as-is — **never extracted**; the transform reads directly from the zips.
- **Years downloaded**: 1975–2024 inclusive (50 annual zips — every year the server
  offers as of retrieval; 2024 is the latest published year).
- **Total size**: 647,400,837 bytes (~618 MiB). Per-file sizes range ~4.7 MB (1975)
  to ~35.2 MB (2021).
- **Integrity**: all 50 zips pass `python -m zipfile -t` (CRC test of every member).

## Format notes per era

- **All 50 years (1975–2024) were available as `FARS{year}NationalCSV.zip`** — the
  historically SAS-only early years have since been republished as CSV, so no
  SAS/DBF fallback was needed. (SAS versions also exist server-side for every year;
  Auxiliary zips — derived convenience files — were intentionally skipped.)
- **1975 era**: 3 tables per zip (`ACCIDENT.CSV`, `VEHICLE.CSV`, `PERSON.CSV`),
  UPPERCASE filenames at the zip root.
- **2024 (latest)**: 33 tables nested under a `FARS2024NationalCSV/` folder,
  lowercase filenames (accident/vehicle/person plus cevent, drugs, drimpair,
  pbtype, race, weather, vpicdecode, the multiply-imputed BAC files
  `MIACC.CSV`/`MIDRVACC.CSV`/`MIPER.CSV`, etc.). The table roster and the
  in-zip layout (root vs. subfolder, filename case) vary by year — the transform
  must match member names case-insensitively and by basename.
- **2024 accident file check**: 80 columns; `STATE`, `COUNTY`, and `ST_CASE`
  columns confirmed present; 1,312 Georgia crash rows (`STATE = 13`).

## License

US federal government work — **public domain** (17 U.S.C. §105). No use
restrictions; cite NHTSA FARS as the source. Records are Privacy Act-stripped
(no PII).

## Caveats (from the criminal-justice blueprint, Tier 1 #10)

- **Multi-file joins**: tables join on `ST_CASE` (crash), `+ VEH_NO` (vehicle),
  `+ PER_NO` (person). `ST_CASE` is unique only within a year.
- **BAC is multiply imputed**: driver BAC is not measured for all fatalities; use
  the multiply-imputed BAC variables (`MIACC`/`MIDRVACC`/`MIPER` files) and
  document which imputed variable is used. See `README-BAC.pdf` on the server.
- **County code is NOT FIPS**: FARS `COUNTY` is the NHTSA/GSA geographic code —
  map to county FIPS carefully (GA = state FIPS 13 on `STATE`; in practice GSA
  county codes largely track FIPS county codes but must be verified per the FARS
  Analytical User's Manual before treating them as FIPS).
- **Annual schema tweaks**: variable names, code lists, and the table roster
  change across years (e.g., pre-2010 vs. post-2010 element redesigns; new tables
  added over time). Version the parser per era.
- **Fatal-only census**: FARS covers crashes with ≥1 death within 30 days — no
  injury-only crashes and no enforcement counts. Do not treat as total crash
  volume.
