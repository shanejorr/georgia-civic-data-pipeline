# Provenance — _crosswalks / facility_to_county (source snapshots)

Source snapshots for building a detention-facility → county crosswalk (used by
`criminal_justice/ice_detention/*`). **Retrieved 2026-07-02 (UTC)** via
`uv run python -m src.etl.criminal_justice.ice_detention.detention_population.download`
(the crosswalk snapshot step; skip with `--skip-crosswalk`). Desktop-browser
User-Agent required for ice.gov (Akamai).

| File | Size | SHA-256 |
|---|---|---|
| ice_over72hour_facilities_2026-07-02.xlsx | 47,718 | 6438a5ca5c1fa0795905e48d252a7de880aa12b836907b00f9c9885ba48e2652 |
| ddp_facilities-latest.parquet | 125,189 | 073d60987f481812d82f6679c5710182c63485081636702834a153bc6fe5198b |
| ddp_facilities-latest-sf.parquet | 146,948 | a9189906cf7964fb3a587cc6a07d737a290329ed2390f2c234b7fb76eb0374cb |
| hifld_prison_boundaries.zstd.parquet | 2,105,048 | 9b650ad68c6d9be913792cf661051da55e0d665b9b37140a6bea057105304eb5 |
| hifld_prison_boundaries_README.md | 5,114 | 50aee674e07610c9d94d6a7bd37735edbae224cd458ec0ba66396e8f949e271e |

## 1. ICE Over-72-Hour Facilities list

- **Source**: `https://www.ice.gov/doclib/detention/Over72HourFacilities.xlsx`, linked
  from <https://www.ice.gov/detain/detention-management> (URL scraped each run).
- Facility name / address / city / state / AOR for facilities holding detainees longer
  than 72 hours. US government work — public domain. Note the ICE FY detention-stats
  workbooks (see the ice_detention bronze dir) also carry facility name/city/state in
  their Facilities sheets, so the workbook alone can seed a GA crosswalk.

## 2. Deportation Data Project — compiled detention facilities

- **Source**: <https://deportationdata.org/data/processed/ice.html> →
  `github.com/deportationdata/ice-detention-facilities` (`facilities-latest.parquet`
  attribute table; `facilities-latest-sf.parquet` adds point geometry).
- **This is the strongest crosswalk source**: it already includes `county` and
  `county_fips_code` per facility (verified: Stewart Detention Center → Stewart County
  13259; the three Folkston facilities → Charlton County 13049), keyed by
  `detention_facility_code` — the same code used in DDP detention records.
- License CC-0 (no rights reserved). Citation per DDP:
  > "government data published by ICE, collated by the Deportation Data Project, and
  > analyzed by [your organization]."

## 3. Archived HIFLD Open "Prison Boundaries"

- **Background**: DHS discontinued the public HIFLD Open portal in Aug–Sep 2025; layers
  moved to access-gated HIFLD Secure. Community archives preserve the last public
  snapshots.
- **Source used**: SeerAI's HIFLD archive on Source Cooperative (public S3-compatible
  bucket) — <https://source.coop/seerai/hifld>, key
  `prison-boundaries/prisonbndrys/prisonbndrys.parquet/part-….zstd.parquet`
  (content-addressed part filename; the downloader lists the prefix live). Archived
  layer README saved alongside (`hifld_prison_boundaries_README.md`).
- 6,468 national facilities with NAME / ADDRESS / CITY / COUNTY / COUNTYFIPS / TYPE /
  SECURELVL / CAPACITY / POPULATION + geometry; 306 GA rows; Stewart and both Folkston
  centers present (TYPE = FEDERAL).
- **There is no separate archived HIFLD "Local Jails" layer** — per the layer
  description, Prison Boundaries covers secure detention facilities "from federal
  (excluding military) to local governments," i.e. local jails and ICE detention
  centers are included in this layer. The Data Rescue Project portal
  (<https://portal.datarescueproject.org/datasets/hifld-open-prison-boundaries/>,
  snapshot downloaded 2025-08-26, mirrored on DataLumos project 240534) likewise lists
  only Prison Boundaries.
- Underlying data: US government (DHS HIFLD) — public domain; archive access courtesy
  of SeerAI / Source Cooperative (and Data Rescue Project / DataLumos mirrors).
- **Access notes**: DataLumos (<https://www.datalumos.org/datalumos/project/240534/version/V1/view>)
  returns 403 to non-browser clients — not retrievable headlessly; the SeerAI bucket
  was used instead. HIFLD data is a **static 2025 snapshot** and will not be updated —
  facility openings/closures after mid-2025 must come from the ICE/DDP feeds.

## Caveats

- Facility names differ across sources (e.g. "FOLKSTON D RAY ICE PROCESSING CTR" vs
  "Folkston D Ray ICE Processing Center" vs HIFLD naming) — match on normalized
  name + city/state, or prefer DDP's `detention_facility_code` join where available.
- The ICE Over72Hour list and workbook Facilities sheets are point-in-time and only
  cover facilities with current ICE detainees.
