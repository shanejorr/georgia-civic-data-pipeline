# Provenance — Stanford Open Policing Project, Georgia State Patrol traffic stops (`gsp_traffic_stops`)

## Source

- **Publisher**: **Stanford Open Policing Project (SOPP)** — a Stanford Computational Policy Lab research
  project that collects and standardizes US traffic-stop records. For Georgia the underlying agency is the
  **Georgia State Patrol / Georgia Department of Public Safety** (a single state agency; no municipal or
  sheriff stops).
- **Catalog page**: <https://openpolicing.stanford.edu/data/>
- **Direct file URL (stable)**: `https://stacks.stanford.edu/file/druid:yg821jf8611/yg821jf8611_ga_statewide_2020_04_01.csv.zip`
  (hosted on Stanford's digital repository `stacks.stanford.edu`; druid `yg821jf8611`, standardized release
  dated 2020-04-01).
- **Coverage**: Georgia, **single agency (state patrol)**, stops **2012-01-01 → 2016-12-31**. The project is
  effectively **frozen** — this is the final GA release and will not gain new years.

## Retrieval

- **Retrieved (UTC)**: 2026-07-04
- **Method**: `uv run python -m src.etl.criminal_justice.open_policing.gsp_traffic_stops.download`
  (`src/etl/criminal_justice/open_policing/gsp_traffic_stops/download.py`). Stable direct download — no page
  scraping. The script fetches the single zip, streams it to a `.part` file and atomically `.replace()`s it,
  **verifies the fetched byte size** (against the server `Content-Length` when present, else the recorded
  expected size), and **skips** on re-run when a size-matching file already exists (idempotent; `--refresh`
  forces a re-download). Politeness delay + `logging`. **The zip is never extracted.**
- **Size verification note**: the server's HEAD response did **not** return a `Content-Length` header (chunked
  transfer), so the download fell back to the recorded expected size of **88,842,478 bytes**; the streamed
  file matched that exactly. (Recon on 2026-07-04 observed `Content-Length: 88,842,478` on a GET, matching.)
- **Idempotency**: verified — a second run skipped without re-downloading the ~85 MiB file.

## Files

| File | Bytes | SHA-256 | Contents |
|------|------:|---------|----------|
| `yg821jf8611_ga_statewide_2020_04_01.csv.zip` | 88,842,478 | `2b15dea842c7d74e66a19871e11ead45b796a95774c334ae233f18d4f4a221ce` | One member: `ga_statewide_2020_04_01.csv` (428,505,528 bytes uncompressed) — **1,906,772** stop-level rows, 19 columns, driver demographics (PII). |

Structure, columns, categoricals, and null patterns: [`bronze-data-structure.md`](bronze-data-structure.md).
**The zip is kept verbatim and never extracted** — the transform must read the CSV member directly from the
zip and aggregate to county/year/demographic before anything reaches gold.

## License

- **ODC-BY 1.0** — Open Data Commons Attribution License (<https://opendatacommons.org/licenses/by/1-0/>).
  Free to share, use, and adapt **with attribution**.
- **Required attribution** (carry into the gold contract `usage`/`limitations` when this ships): credit the
  **Stanford Open Policing Project** and cite the accompanying paper —
  > Pierson, E., Simoiu, C., Overgoor, J., Corbett-Davies, S., Jenson, D., Shoemaker, A., Ramachandran, V.,
  > Barghouty, P., Phillips, C., Shroff, R., & Goel, S. (2020). *A large-scale analysis of racial disparities
  > in police stops across the United States.* **Nature Human Behaviour** 4, 736–745.
  Data source line: "Data: Stanford Open Policing Project (openpolicing.stanford.edu), Georgia statewide
  release `yg821jf8611`, 2020-04-01; licensed ODC-BY 1.0."

## Caveats

- **PII → aggregate before serving.** Stop-level records carry driver race/sex, precise date/time, precise
  location (lat/lng + free-text), and a hashed officer id. Gold serves **county × year × demographic
  aggregates only**; none of the row-level identifiers reach gold. (Domain rule: "PII stays in bronze.")
- **Warnings only — no citations, arrests, searches, or contraband.** The GA data's `outcome` column is a
  **constant `warning`**, and the file has **no search/contraband/arrest columns at all**. GA is usable for
  stop-volume and stop-composition (racial) disparity, **not** for search-rate, hit-rate, citation, or
  arrest-disparity analysis. (Deviates from the source-blueprint field list, which anticipated
  search/contraband/citation fields — GA does not provide them.)
- **Single agency.** Georgia State Patrol / Dept. of Public Safety only — **no** municipal police or sheriff
  stops. Never present as all-Georgia traffic enforcement.
- **Frozen 2012–2016.** No new years; the release is final. All five years are complete
  (2012: 372,285 · 2013: 415,242 · 2014: 411,036 · 2015: 369,441 · 2016: 338,768 stops).
- **Race is 47.1% unknown (`NA`).** Nearly half of stops lack driver race; any disparity metric must expose
  the unknown-race share and denominator caveat rather than dropping unknowns.
- **County field is present and clean** (`county_name`): 159 real GA counties cover all but 10 rows (7
  `G### County` placeholder codes = 9 rows, plus 1 `NA`), which map to NULL county. `violation` is dirty
  30,255-value free text (case-duplicated, pipe-delimited) — not a usable categorical without heavy cleaning.
