# Provenance — fbi_cde / law_enforcement_employees

**Source**: FBI Crime Data Explorer (CDE), <https://cde.ucr.cjis.gov> — "Documents & Downloads"
page (`https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/downloads`), "Law Enforcement Employees
Data" (LEE / PE) additional dataset (national).
**Retrieved**: 2026-07-02T12:23Z, via
`uv run python -m src.etl.criminal_justice.fbi_cde.download`.
**License**: US federal government work — public domain.

## Retrieval method (unstable URLs — re-discover, never hardcode)

The CDE SPA serves bulk files from a private S3 bucket via **signed URLs expiring in ~15 min**.
The downloader reads the S3 key from the SPA metadata file
`https://cde.ucr.cjis.gov/LATEST/webapp/assets/JSON/downloads/downloads.json` (entry id `pe`,
`awsFile: additional-datasets/law-enforcement/lee_1960_2025.csv` — filename embeds the year
range, so it changes with each release), exchanges it at
`GET https://cde.ucr.cjis.gov/LATEST/s3/signedurl?key={key}`, and downloads immediately.

## Files

| File | Size | sha256 |
|------|------|--------|
| `lee_1960_2025.csv` | 106,754,028 B | `36603e78db8926033f85c8727492f4913e0744ab33722307619dfcd4e098533c` |

- **Grain**: agency (ORI) × data_year, national, **1960–2025** (last modified 2026-05-11 per
  `downloads.json`).
- **Header**: `data_year, ori, pub_agency_name, pub_agency_unit, state_abbr, division_name,
  region_name, county_name, agency_type_name, population_group_desc, population,
  male_officer_ct, male_cilvilian_ct, male_total_ct, female_officer_ct, female_cilvilian_ct,
  female_total_ct, officer_ct, civilian_ct, total_pe_ct, pe_ct_per_1000` (note the source's
  `cilvilian` typo — preserve at bronze, fix at transform).
- **Filter to `state_abbr == "GA"` in the transform.** Serves as the staffing denominator
  for agency-level rates. Carries `county_name` per ORI — a secondary ORI→county signal
  alongside `data/bronze/_crosswalks/ori_to_county/`.

## Caveats

- Employee counts are as-reported snapshots (typically Oct 31 head counts); not every agency
  reports every year — missing agency-years are absent rows, not zeros.
- The fixed-width `master_files/pe/pe-{year}.zip` family (1991–2024) also exists; this CSV
  is the preferred, self-describing form and reaches back to 1960.
- SPA URLs are unstable and signed — always re-run the downloader rather than reusing URLs.
