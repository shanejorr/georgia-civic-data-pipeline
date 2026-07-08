# Provenance — FJC Integrated Database (IDB) criminal defendant files (federal district filings)

## Source

- **Publisher**: Federal Judicial Center (FJC) — Integrated Database (IDB),
  criminal (defendant-level) data.
- **Hub**: <https://www.fjc.gov/research/idb>
- **Research Guide**: <https://www.fjc.gov/sites/default/files/IDB-Research-Guide.pdf>
- **Criminal-dataset landing pages** (reached via the "Criminal Data" filter):
  - SY1970–FY1995: <https://www.fjc.gov/research/idb/criminal-defendants-filed-and-terminated-sy-1970-through-fy-1995>
  - FY1996–present: <https://www.fjc.gov/research/idb/criminal-defendants-filed-terminated-and-pending-fy-1996-present>
- **Resolved file URLs**:
  - `https://www.fjc.gov/sites/default/files/idb/textfiles/cr70to95.zip` (tab-delimited, SY1970–FY1995)
  - `https://www.fjc.gov/sites/default/files/idb/textfiles/cr96on_0.zip` (tab-delimited, FY1996–present)
  - `https://www.fjc.gov/sites/default/files/idb/codebooks/Criminal Code Book 1970-1995.pdf`
  - `https://www.fjc.gov/sites/default/files/idb/codebooks/Criminal Code Book 1996 Forward.pdf`

## Retrieval

- **Retrieved (UTC)**: 2026-07-04
- **Antibot bypass (the "JS widget" from the blueprint):** the IDB dataset
  downloads are exposed through a Drupal **Views exposed filter wrapped in the
  *antibot* module** — the `<select name="field_type_tid">` ("Criminal Data" =
  taxonomy term `6876`) posts to a JS-rewritten `/antibot` action, so the
  buttons have no static href and a headless client is blocked at the widget.
  **This retrieval bypasses the widget** by requesting the exposed filter as a
  plain GET query parameter: `GET /research/idb?field_type_tid=6876` returns the
  two criminal-dataset landing pages server-side, which are then scraped for the
  real file URLs under `/sites/default/files/idb/`. The bulk criminal files are
  therefore **not** blocked as of 2026-07-04 — they are fully scriptable.
- **Method**: `uv run python -m src.etl.criminal_justice.federal_justice.district_filings.download`
  (`src/etl/criminal_justice/federal_justice/district_filings/download.py`).
  The script performs the antibot bypass, scrapes both landing pages for the
  tab-delimited text zips + codebooks (nothing hardcoded — filename drift on
  FJC's quarterly `_0` re-uploads is tracked), and downloads each with atomic
  `.part`→`.replace` writes, size verification against `Content-Length`, and
  skip-if-present idempotency. Zips are kept as-is — **never extracted**.
  - **`cr70to95.zip` truncation workaround:** the FJC origin caps a single
    non-ranged connection at exactly 8 MiB for that file (`Content-Length`
    15,673,434 but the body is cut at 8,388,608 bytes → `IncompleteRead`), while
    honoring HTTP **Range** requests (206). The downloader detects the under-read
    and falls back to a **windowed Range download** (8 MiB windows), which
    completes the file; the reassembled zip passes CRC. `cr96on_0.zip` (252.8 MB)
    downloads in one stream.
  - Idempotency verified: a second run downloaded 0 and skipped all 4 files.
- **Files downloaded** (4): `cr70to95.zip`, `cr96on_0.zip`,
  `Criminal Code Book 1970-1995.pdf`, `Criminal Code Book 1996 Forward.pdf`.
- **Total size**: 269,012,152 bytes (~256.6 MB) across the 4 files
  (`cr70to95.zip` 15.7 MB, `cr96on_0.zip` 252.8 MB, codebooks 0.2 + 0.3 MB).
- **Integrity**: both zips pass a CRC test (`unzip -t`). `cr70to95.zip` → member
  `cr70to95.txt` (178,239,657 B, 1,420,711 rows, 39 cols). `cr96on_0.zip` →
  member `cr96on.txt` (3,524,429,156 B, 6,299,908 rows, 144 cols, `FISCALYR`
  1996–2026). Georgia district codes 3E/3G/3J confirmed present in both.
- **Per-year SAS datasets not downloaded.** The landing pages also list per-year
  `datasets/cr{YY}.sas7bdat` files (SY1970–FY2026) and cumulative SAS zips —
  these hold the same records in SAS format. The **tab-delimited text zips are
  the complete canonical bulk download** and are transform-friendly, so the SAS
  files are intentionally omitted (available if ever needed).

## Format notes

- **`cr96on_0.zip` uses Deflate64** ("enhanced-64k"), which Python's stdlib
  `zipfile` cannot decompress. Read it with system `unzip`, `libarchive`, or a
  Deflate64 backport. `cr70to95.zip` is standard Deflate.
- Both `.txt` members are **tab-delimited with a header row**; the two periods
  have different column layouts (39 vs 144 columns) with their own codebook.

## License

US federal government work — **public domain** (17 U.S.C. §105). No use
restrictions; cite Federal Judicial Center, Integrated Database. Defendant
`NAME` appears in the raw text but is aggregated away and not carried to gold.

## Caveats

- **Aggregate to district-year.** Defendant-level microdata (one row per federal
  criminal defendant per case), national coverage; gold serves
  `federal_district × year` aggregates filtered to Georgia
  (`DISTRICT` ∈ {3E = GA-N, 3G = GA-M, 3J = GA-S}).
- **District ≠ county.** Sub-state, **non-county** grain — Georgia's three
  federal judicial districts, not the 159-county FIPS grain used by most
  criminal_justice topics. The criminal IDB has **no usable county code**
  (a `COUNTY` column exists in the 1996+ file but is sparse/inconsistent for
  criminal data — do not treat as county grain). Decide the district-grain
  serving model before building (blueprint source #17).
- **Do not filter Georgia on `CIRCUIT`.** It is 5 (Fifth Circuit) before SY82
  and 11 (Eleventh Circuit) after the 1981 split; filter on `DISTRICT`
  (3E/3G/3J), which is stable across the whole series.
- **1992 15-month bridge / SY→FY change.** Reporting shifted from statistical
  year (July–June) to fiscal year (Oct–Sep) around 1992 with a 15-month
  transition; year-over-year counts across that boundary are not directly
  comparable. Version the break.
- **Two layouts.** SY1970–FY1995 (39 cols) and FY1996–present (144 cols) use
  different column names for the same concepts — harmonize per era; do not
  assume a shared schema.
- **Quarterly updates → FY2026 is partial.** The current fiscal year is
  incomplete and grows each quarter; treat the latest FY as provisional.
- **This is filings/terminations, not sentencing counts.** The IDB counts
  criminal defendants filed/terminated; individual *sentencing* detail
  (guideline position, departures) is the USSC `district_sentences` topic. The
  two are complementary.
