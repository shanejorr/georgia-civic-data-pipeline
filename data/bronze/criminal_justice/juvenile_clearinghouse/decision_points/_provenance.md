# Provenance — juvenile_clearinghouse / decision_points

## Source

- **Publisher**: Georgia Juvenile Justice Data Clearinghouse (Juvenile Data Exchange
  Committee — Council of Juvenile Court Judges / CJCC / Georgia courts), hosted by the
  Judicial Council / Administrative Office of the Courts of Georgia.
- **Landing page**: <https://juveniledata.georgiacourts.gov/dashboards-reports/> ("Raw Data" section)
- **Data dictionary / definitions page**: <https://juveniledata.georgiacourts.gov/definitions/>
  (no co-located data dictionary is shipped with the CSVs — use this page)

## Files

| Local file | Resolved source URL | Size | Rows (excl. header) | Years |
|---|---|---|---|---|
| `decision_points_raw_data_1_2026-06.csv` | <https://juveniledata.georgiacourts.gov/wp-content/uploads/2026/06/Juvenile-Justice-Decision-Points-Raw-Data-1.csv> | 18,974,773 B | 309,637 | 2010–2025 |
| `decision_points_raw_data_2_2026-06.csv` | <https://juveniledata.georgiacourts.gov/wp-content/uploads/2026/06/Juvenile-Justice-Decision-Points-Raw-Data-2.csv> | 4,645,803 B | 92,656 | 2005–2025 |

The `2026-06` filename suffix is the WordPress upload month parsed from the source URL
(`/wp-content/uploads/2026/06/`). Source URLs embed this upload month — **never hardcode
them**; the downloader re-scrapes the landing page on every run.

## Retrieval

- **Retrieved (UTC)**: 2026-07-02T03:25:38Z
- **Method**: scripted download —
  `uv run python -m src.etl.criminal_justice.juvenile_clearinghouse.download`
  (`src/etl/criminal_justice/juvenile_clearinghouse/download.py`); files saved verbatim,
  no cleaning at bronze.
- **Refresh cadence**: source is refreshed annually (approximately June).

## License / attribution

- Public data published for download by a Georgia state judicial-branch body; no explicit
  license text on the page. Treat as public-sector data; attribute the Georgia Juvenile
  Justice Data Clearinghouse (juveniledata.georgiacourts.gov).

## Coverage & grain

- **Raw Data 1**: youth-level rows — one row per juvenile (`NEWJUVID`) per period year per
  county/court type/race/gender, with decision-point counts (offenses, diversions,
  delinquent adjudications, probation orders, commitment orders, petitions, superior-court
  sentenced, secure detention RYDC, secure confinement YDC) plus an active/terminated flag.
  Years 2010–2025, county throughout.
- **Raw Data 2**: county/year/**month**/case-type/race/gender aggregate rows — referred,
  petitioned, adjudicated, diverted, commitment, superior-court transfer. Years 2005–2025.

## Caveats (bronze — keep verbatim; see criminal-justice-data-review.md Tier 1 #3)

- **Inconsistent schemas across the four clearinghouse files** (youth-level vs county
  aggregate; different column naming conventions per file).
- **Race and gender carry both a label and a numeric code** in Raw Data 1
  (`Race Value`/`Race Code`, `Gender`/`Gender Code`); Raw Data 2 carries labels only and
  uses different race labels (e.g. `WHITE`, `OTHER`, `UNKNOWN`, `HISPANIC`).
- **Youth-level IDs (`NEWJUVID`) are PII-adjacent — must be aggregated to county/year
  before gold.** Never publish youth-level rows.
- RYDC/YDC columns in Raw Data 1 are blank (not zero) in early years — preserve the
  distinction; no cleaning at bronze.
- Both files begin with a UTF-8 BOM (`﻿`) before the header row.
- County identified by name only (no FIPS in these two files) — needs the
  county-name-to-FIPS crosswalk downstream.
