# Provenance — juvenile_clearinghouse / out_of_home_placement

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
| `decision_point_raw_data_ohp_stp_2026-06.csv` | <https://juveniledata.georgiacourts.gov/wp-content/uploads/2026/06/Juvenile-Justice-Decision-Point-Raw-Data-OHP-STP.csv> | 137,836 B | 2,921 | 2005–2025 |

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

- **Grain**: one row per county per period year (county aggregate — no youth-level IDs in
  this file). Years 2005–2025, all counties.
- **Columns**: `CountyName`, `PeriodYear`, explicit 5-digit **`CountyFips`** (e.g. `13001`),
  then commitment/STP measures: `AllCommitments`, `FelonyCommitments`,
  `FelonyCommitmentsOhp`, `AllStpAdmissions`, `FelonyStpAdmissions`, plus race splits
  (Black/White/Hispanic/Other) for felony commitments and all STP admissions.
- OHP = out-of-home placement; STP = short-term program.

## Caveats (bronze — keep verbatim; see criminal-justice-data-review.md Tier 1 #3)

- **Inconsistent schemas across the four clearinghouse files** — this file is the only one
  with FIPS codes and CamelCase headers; race categories here (Black/White/Hispanic/Other)
  differ from the label+code scheme in the youth-level files.
- **No gender split** in this file (race splits only), unlike the other three files.
- File begins with a UTF-8 BOM (`﻿`) before the header row.
- Already county/year aggregate, so no PII concern here, but the sibling clearinghouse
  files are youth-level — do not join back to youth IDs.
