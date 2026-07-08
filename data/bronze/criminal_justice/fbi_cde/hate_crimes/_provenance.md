# Provenance — fbi_cde / hate_crimes

**Source**: FBI Crime Data Explorer (CDE), <https://cde.ucr.cjis.gov> — "Documents & Downloads"
page (`https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/downloads`), "Hate Crime" additional
dataset (national master file).
**Retrieved**: 2026-07-02T12:23Z, via
`uv run python -m src.etl.criminal_justice.fbi_cde.download`.
**License**: US federal government work — public domain.

## Retrieval method (unstable URLs — re-discover, never hardcode)

The CDE SPA serves bulk files from a private S3 bucket via **signed URLs expiring in ~15 min**.
The downloader reads the S3 key from the SPA metadata file
`https://cde.ucr.cjis.gov/LATEST/webapp/assets/JSON/downloads/downloads.json` (entry id `hc`,
`awsFile: additional-datasets/hate-crime/hate_crime.zip`), exchanges it at
`GET https://cde.ucr.cjis.gov/LATEST/s3/signedurl?key={key}`, and downloads immediately.

## Files

| File | Size | sha256 |
|------|------|--------|
| `hate_crime.zip` | 5,351,152 B | `6d24e053b340e74e62d0fcf8b237ac470f5ccafc908ba661581f99c2daa9d189` |

Zip contents (kept unextracted; passes `python -m zipfile -t`, verified 2026-07-02):
`hate_crime/hate_crime.csv` (~68 MB uncompressed; incident-level, columns include
`incident_id, data_year, ori, agency names/types, state_abbr, incident_date,
victim/offender counts, offender_race, offender_ethnicity, offense_name, location_name,
bias_desc, …`) and `Hate_Crime_2024_Methodology.pdf`.

- **Coverage**: national, 1991–2024 (per `downloads.json`; last modified 2025-08-05).
- **National file — filter to `state_abbr == "GA"` in the transform.**

## Caveats

- Agency (ORI) grain — county rollups need the `ori_to_county` crosswalk
  (`data/bronze/_crosswalks/ori_to_county/`), a hard prerequisite.
- Hate-crime reporting is voluntary and notoriously under-reported; zero-report agencies
  are absent, not true zeros — treat coverage per year via the participation data if needed.
- The CDE also publishes a fixed-width `master_files/hate-crime/hate-crime-{year}.zip`
  family (1991–2025 per the SPA's `masters.json`); this CSV additional-dataset release is
  the preferred, self-describing form.
- SPA URLs are unstable and signed — always re-run the downloader rather than reusing URLs.
