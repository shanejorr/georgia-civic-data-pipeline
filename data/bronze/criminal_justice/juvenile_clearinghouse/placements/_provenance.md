# Provenance — juvenile_clearinghouse / placements

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
| `decision_point_placements_raw_data_2026-06.csv` | <https://juveniledata.georgiacourts.gov/wp-content/uploads/2026/06/Juvenile-Justice-Decision-Point-Placements-Raw-Data.csv> | 71,777,331 B | 433,844 | 2010–2025 |

The `2026-06` filename suffix is the WordPress upload month parsed from the source URL
(`/wp-content/uploads/2026/06/`). Source URLs embed this upload month — **never hardcode
them**; the downloader re-scrapes the landing page on every run.

## Retrieval

- **Retrieved (UTC)**: 2026-07-02T03:25:38Z
- **Method**: scripted download —
  `uv run python -m src.etl.criminal_justice.juvenile_clearinghouse.download`
  (`src/etl/criminal_justice/juvenile_clearinghouse/download.py`); file saved verbatim,
  no cleaning at bronze.
- **Refresh cadence**: source is refreshed annually (approximately June).

## License / attribution

- Public data published for download by a Georgia state judicial-branch body; no explicit
  license text on the page. Treat as public-sector data; attribute the Georgia Juvenile
  Justice Data Clearinghouse (juveniledata.georgiacourts.gov).

## Coverage & grain

- **Grain**: placement/offense-level rows — one row per juvenile (`newjuvenileid`) per
  placement per offense record. Years 2010–2025.
- **Columns**: `Year`, `newjuvenileid`, `Placement Count`, gender + race (label **and**
  numeric code), `Site Name`, `Site Type` (e.g. `RYDC`, right-padded with spaces),
  `Arrest County`, `County of Residence`, `Facility County`, `Admitted Date`,
  `Date Terminated`, `Offense Date`, `Offense County`, `Offense Description`,
  `DBL Placements`, `Duplicate Offense Record`, `Other offenses`.

## Caveats (bronze — keep verbatim; see criminal-justice-data-review.md Tier 1 #3)

- **Dates are `DD-MM-YYYY`** (e.g. `19-02-2010`) — day-first; must be parsed explicitly
  downstream, never auto-inferred.
- **Youth-level IDs (`newjuvenileid`) are PII-adjacent — must be aggregated to county/year
  before gold.** Never publish youth/placement-level rows.
- **Duplicate rows are flagged, not removed**: `DBL Placements` = "Duplicate Placement
  Record" and `Duplicate Offense Record` markers appear; a juvenile with multiple offenses
  on one placement repeats the placement row. Kept verbatim at bronze; dedupe/aggregate in
  the transform.
- **Race and gender carry both a label and a numeric code** (`Race Value`/`Race Code`,
  `Gender`/`Gender Code`).
- **Multiple county columns** (arrest / residence / facility / offense) — the county
  concept must be chosen deliberately in the transform. County names only, no FIPS.
- **Not fully valid UTF-8**: the file contains some invalid UTF-8 byte sequences (likely
  Windows-1252 characters in free-text offense descriptions/site names) — read with a
  lossy/explicit encoding (e.g. polars `encoding="utf8-lossy"`). No BOM on this file
  (unlike the other three).
- `Site Type` values are right-padded with trailing spaces.
- **Inconsistent schemas across the four clearinghouse files** (this file is
  placement-level; others are youth-level or county aggregates).
