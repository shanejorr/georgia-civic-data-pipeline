# gsp_traffic_stops — Bronze Data Structure

## Overview

- Topic: gsp_traffic_stops
- Source: open_policing (Stanford Open Policing Project — Georgia statewide, standardized traffic-stop microdata)
- Files: **1 zip** (`yg821jf8611_ga_statewide_2020_04_01.csv.zip`, 84.7 MiB) containing **one CSV** (`ga_statewide_2020_04_01.csv`, 408.7 MiB / 428,505,528 bytes uncompressed) — **1,906,772 stop-level rows**, 19 columns
- Unreadable files: none (zip CRC-clean; the CSV parses cleanly with polars, all columns read as Utf8)
- Year representation: **`date` column, ISO `YYYY-MM-DD`** (one row per traffic stop; no year column). The `2020_04_01` in the filename is the SOPP **release/standardization date**, not a data year.
- Filename-to-data year offset: **N/A** — filename date (2020-04-01) is the publication date; data years derive from the `date` column (2012–2016).
- Detail levels: **stop-level microdata** (one row per traffic stop) with `county_name` + `lat`/`lng`; gold target is **county × year × demographic** aggregation
- Percentage scale: N/A — no percentage columns; all fields are dates/times, coordinates, codes, or free-text
- Checksums generated: 2026-07-04

## Source Provenance

- **Source URL**: `https://stacks.stanford.edu/file/druid:yg821jf8611/yg821jf8611_ga_statewide_2020_04_01.csv.zip`
  (catalog page: <https://openpolicing.stanford.edu/data/>)
- **Retrieved**: 2026-07-04 (UTC)
- **Method**: scripted fetch — `uv run python -m src.etl.criminal_justice.open_policing.gsp_traffic_stops.download`
  (stable direct URL; verifies fetched byte size, idempotent, `--refresh` to force). Full details in
  [`_provenance.md`](_provenance.md). **The zip is never extracted** — any transform must read the CSV member
  directly from the zip and **aggregate to county/year/demographic** before anything reaches gold (stop-level
  driver demographics are PII).
- **License**: **ODC-BY 1.0** (Open Data Commons Attribution). Attribution required — see `_provenance.md`.

## File Checksums

Generated: 2026-07-04

| File | SHA-256 |
|------|---------|
| yg821jf8611_ga_statewide_2020_04_01.csv.zip | 2b15dea842c7d74e66a19871e11ead45b796a95774c334ae233f18d4f4a221ce |

## Zip / Member Structure

Single-member zip (not Excel, not a multi-table bundle):

| Member | Uncompressed | Notes |
|--------|--------------|-------|
| `ga_statewide_2020_04_01.csv` | 428,505,528 bytes | The only member; one flat CSV of stop-level records. Header + 1,906,772 data rows, 19 columns. |

Read directly from the zip (`zipfile.ZipFile(...).open("ga_statewide_2020_04_01.csv")`) — **never extract to disk**
(provenance contract; PII). Literal string **`NA`** is the file's null sentinel (there are no true CSV nulls).

## Summary

Stanford Open Policing Project (SOPP) **standardized traffic-stop microdata** for Georgia — one row per
traffic stop, **2012-01-01 → 2016-12-31**. For Georgia the reporting agency is effectively a single agency
(`department_name` = "GEORGIA DEPARTMENT OF PUBLIC SAFETY", the parent of the Georgia State Patrol, for
99.98% of rows). Each row carries the **stop date/time, county + lat/long location, driver race and sex,
a hashed officer id, the violation text, the stop outcome, and vehicle descriptors** (color/make/model/year).
The civic value is **racial-disparity analysis of who gets stopped** (stop counts by driver race per county
per year). **Two headline SOPP fields are effectively absent for Georgia:** the data contains **no search /
contraband / arrest columns at all**, and the `outcome` column is a **constant `warning`** — see ETL
Considerations #1–#2. This makes GA suitable for stop-volume and stop-composition disparity metrics, but
**not** for search-rate, hit-rate, citation, or arrest disparity metrics.

## Eras

Single file, single schema — **one era** (2012–2016). The 19 columns below are stable across all rows.

### Era 1: 2012–2016 (the one CSV member; 1,906,772 stop rows)

| Column | Description |
|--------|-------------|
| raw_row_number | SOPP within-file row id (unique across all 1,906,772 rows; a join key back to the raw source, not a stable stop id) |
| date | Stop date, ISO `YYYY-MM-DD` (2012-01-01 → 2016-12-31) — the year source for gold |
| time | Stop time, `HH:MM:SS` (24h; present for every row) |
| location | Free-text location description (e.g. "SR31 MM32, DUBLIN"); **65.1% `NA`** |
| lat | Latitude, decimal degrees (mostly valid GA ~30–35°; some out-of-range garbage — see ETL #5); 0.9% `NA` |
| lng | Longitude, decimal degrees (mostly ~−80 to −85°; some out-of-range garbage); 0.9% `NA` |
| county_name | Georgia county name, "<County> County" (e.g. "Fulton County"). 159 real GA counties + 7 `G### County` placeholder codes (9 rows) + 1 `NA`. **County rollup key.** |
| subject_race | SOPP-standardized driver race: `white`, `black`, `hispanic`, `asian/pacific islander`, `other`; **47.1% `NA`** |
| subject_sex | SOPP-standardized driver sex: `male`, `female`; 3.9% `NA` |
| officer_id_hash | Anonymized officer identifier (10-char hash); 18 `NA` |
| department_name | Reporting agency (see categoricals) — 99.98% "GEORGIA DEPARTMENT OF PUBLIC SAFETY" |
| type | Stop type — **constant `vehicular`** for every row |
| violation | Raw violation text; **30,255 distinct** values, mixed-case duplicates and pipe-delimited multi-violations (see ETL #4); 210 `NA` |
| outcome | Stop outcome — **constant `warning`** for every row (GA supplies warnings only; ETL #2) |
| vehicle_color | Vehicle color code (e.g. `BLK`, `GRY`); 1.9% `NA` |
| vehicle_make | Vehicle make (e.g. `PONTIAC`); 1.0% `NA` |
| vehicle_model | Vehicle model; 4.0% `NA` |
| vehicle_year | Vehicle model year (1901–2018 observed); 4.8% `NA` |
| raw_race | The pre-standardization race string from the source: `White`, `Black`, `Hispanic`, `Asian`, `Native American`, `Other`; 47.1% `NA` |

#### Sample Data (3 rows, key columns)

```text
raw_row_number  date        time      county_name       subject_race  subject_sex  department_name                       type       violation                       outcome  raw_race
216687          2012-01-01  00:01:37  Long County       NA            female       GEORGIA DEPARTMENT OF PUBLIC SAFETY   vehicular  FaultyHeadlights                warning  NA
231398          2012-01-01  00:02:11  Laurens County    white         female       GEORGIA DEPARTMENT OF PUBLIC SAFETY   vehicular  WarningNoTagLight               warning  White
220253          2012-01-01  00:02:19  Rockdale County   NA            female       GEORGIA DEPARTMENT OF PUBLIC SAFETY   vehicular  WarningDisobeyedTrafficSignal   warning  NA
```

#### Statistics

- Total rows: **1,906,772**. Rows per year: 2012 = 372,285; 2013 = 415,242; 2014 = 411,036; 2015 = 369,441; 2016 = 338,768.
- `raw_row_number` is unique across the whole file (1,906,772 distinct). `time` is `HH:MM:SS` for every row.
- `vehicle_year` numeric range 1901–2018; `lat`/`lng` mostly valid GA coordinates with a small tail of out-of-range sentinel/garbage values (lat up to ~85, lng up to ~85 — swapped/bad coords, see ETL #5).

#### Null Counts (`NA` sentinel; there are no true CSV nulls)

| Column | `NA` count | % of rows |
|--------|-----------:|----------:|
| location | 1,241,211 | 65.1% |
| subject_race | 898,309 | 47.1% |
| raw_race | 898,309 | 47.1% |
| vehicle_year | 91,743 | 4.8% |
| vehicle_model | 75,888 | 4.0% |
| subject_sex | 74,233 | 3.9% |
| vehicle_color | 36,853 | 1.9% |
| vehicle_make | 18,972 | 1.0% |
| lat | 16,365 | 0.9% |
| lng | 16,316 | 0.9% |
| violation | 210 | 0.0% |
| officer_id_hash | 18 | 0.0% |
| county_name | 1 | 0.0% |
| raw_row_number, date, time, department_name, type, outcome | 0 | 0.0% |

#### Categorical Columns

| Column | Distinct Values (with counts) |
|--------|-------------------------------|
| subject_race | `white` 660,855 · `black` 297,156 · `hispanic` 33,715 · `asian/pacific islander` 8,753 · `other` 7,984 · `NA` 898,309 |
| subject_sex | `male` 1,099,993 · `female` 732,546 · `NA` 74,233 |
| type | `vehicular` 1,906,772 (**constant**) |
| outcome | `warning` 1,906,772 (**constant** — GA has warnings only) |
| department_name | `GEORGIA DEPARTMENT OF PUBLIC SAFETY` 1,906,470 · `GEORGIA DEPARTMENT OF NATURAL RESOURCES` 298 · `GEORGIA STATE PATROL` 4 |
| raw_race | `White` 660,855 · `Black` 297,156 · `Hispanic` 33,715 · `Asian` 8,753 · `Native American` 4,339 · `Other` 3,645 · `NA` 898,309 |
| county_name | 159 real Georgia counties (all suffixed " County"; top: Fulton 108,085 · Cobb 71,779 · Gwinnett 70,789) + 7 `G### County` placeholders (9 rows total: G047/G059/G115/G139/G143/G213/G223) + 1 `NA` |
| violation | **30,255 distinct** — not a clean categorical (mixed case: `WarningExceededSpeedLimit` 484,834 vs `WARNINGEXCEEDEDSPEEDLIMIT` 199,318; pipe-joined multi-violations: `WarningExceededSpeedLimit\|WarningOtherViolations`). Treat as free text; needs heavy normalization if ever surfaced. |

**Asian / Pacific Islander check:** `subject_race` publishes a **combined `asian/pacific islander`** bucket
(8,753) with **no separate Pacific Islander** value → maps to `asian_pacific_islander`, never bare `asian`.
Note the SOPP standardization folds the raw `Native American` (4,339) into `other`: standardized `other`
(7,984) = raw `Native American` (4,339) + raw `Other` (3,645). No split-vs-combined mutual-exclusivity
conflict — only the combined AAPI bucket is published.

#### Suppression Markers

None. SOPP microdata is **unsuppressed** — every stop is an individual record. The only "missing" marker is
the literal string `NA` (unknown/not recorded), documented in the null-counts table above. There are no
small-count suppression codes.

## ETL Considerations

1. **No search / contraband / arrest / citation columns exist for Georgia.** The GA SOPP file has only 19
   columns (`raw_row_number, date, time, location, lat, lng, county_name, subject_race, subject_sex,
   officer_id_hash, department_name, type, violation, outcome, vehicle_color, vehicle_make, vehicle_model,
   vehicle_year, raw_race`). Fields many other SOPP states carry — `search_conducted`, `contraband_found`,
   `arrest_made`, `citation_issued`, `warning_issued`, `subject_age`, `reason_for_stop` — are **absent**.
   Do not assume them. This deviates from the source-blueprint field list (which listed search/contraband/
   citation as expected); GA does not provide them.
2. **`outcome` is a constant `warning`; `type` is a constant `vehicular`.** Georgia (GSP) supplied **warning
   data only** — there are no citations or arrests in this dataset. Both columns are single-valued, so they
   carry zero information and should be **dropped in gold** (or noted as a fixed scope, not a categorical).
   Consequence: GA is usable for **stop-count / stop-composition** disparity metrics (who is stopped/warned),
   **not** for search-rate, hit-rate, citation, or arrest-disparity metrics.
3. **County rollup is clean.** 159 distinct real GA county names (all " County"-suffixed, covering 1,906,762
   of 1,906,772 rows) map 1:1 to the counties dimension via `add_county_fips()` after stripping " County".
   The 7 `G### County` placeholder codes (9 rows) + 1 `NA` (1 row) = **10 unmappable rows** → NULL county
   (never drop; record as an unmapped categorical on the manifest, per domain rules). No consolidated-government
   name issues appear (no Athens-Clarke/Columbus/Macon-Bibb style names in the data).
4. **`violation` is dirty free text, not a categorical.** 30,255 distinct values with (a) case-duplication
   (`WarningExceededSpeedLimit` vs `WARNINGEXCEEDEDSPEEDLIMIT`) and (b) pipe-delimited multi-violations. If a
   violation breakdown is ever wanted, it needs case-folding + splitting on `|` + a substantial normalization
   map. For a county × year × race gold table, exclude it.
5. **`lat`/`lng` have out-of-range garbage.** ~99% are valid GA coordinates, but a tail carries impossible
   values (observed lat up to ~85, lng up to ~85 — swapped or corrupt). Coordinates are **not needed** for the
   county-year gold (county comes from `county_name`); if ever used, filter to GA's bounding box and NULL the
   rest (§4b known-bad handling).
6. **Race is 47.1% `NA`.** Nearly half the stops have unknown driver race. Any racial-disparity metric must
   surface the unknown-race share prominently (and the denominator caveat) — do **not** silently drop unknowns
   or treat them as a race. `subject_sex` is 3.9% `NA`.
7. **`subject_race` vs `raw_race`.** `subject_race` is the SOPP-standardized value (use it); `raw_race` is the
   source's original string (kept for audit only — folds `Native American` into `other`). Map
   `asian/pacific islander` → `asian_pacific_islander` (combined bucket; no separate PI).
8. **PII → aggregate before gold.** Stop-level rows carry driver demographics, precise time, precise location,
   and a hashed officer id. Gold must serve **county × year × demographic aggregates only** — none of
   `raw_row_number`, `time`, `location`, `lat`, `lng`, `officer_id_hash`, or vehicle descriptors reach gold.
9. **Frozen source.** The project is effectively frozen; 2012–2016 is complete and will not gain new years.
   Re-running `download.py` fetches the same static file (idempotent).
10. **Agency label caveat.** The standardized `department_name` is "GEORGIA DEPARTMENT OF PUBLIC SAFETY"
    (GSP's parent), plus 298 "GEORGIA DEPARTMENT OF NATURAL RESOURCES" and 4 "GEORGIA STATE PATROL" rows.
    This is single-agency state-patrol data, as the blueprint states — do not present it as all Georgia law
    enforcement (no municipal/sheriff stops are included).

## Gold Schema Classification

Proposed gold grain: **county_fips × year × demographic** (aggregated from stop-level bronze; count of stops).

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| county_name | fact_key | county_fips | strip " County" → `add_county_fips()`; 159 map cleanly; 10 placeholder/NA rows → NULL (ETL #3) |
| date | fact_key | year | `date[:4]`; 2012–2016 |
| subject_race | fact_key | demographic | map to demographics dim (`asian/pacific islander` → `asian_pacific_islander`); 47.1% NA → an `unknown`/`all` handling decision (ETL #6/#7) |
| subject_sex | fact_key (optional) | demographic (sex) | second demographic axis if a sex breakdown is wanted; else roll into `all` |
| (row count) | fact_metric | traffic_stops | count of stop rows per county × year × demographic; unit: count; **key_metric** |
| raw_race | not_in_gold | — | audit-only pre-standardization string (use `subject_race`) |
| outcome | not_in_gold | — | constant `warning` (ETL #2) — no information |
| type | not_in_gold | — | constant `vehicular` (ETL #2) — no information |
| violation | not_in_gold | — | 30,255-value dirty free text (ETL #4) |
| location, lat, lng | not_in_gold | — | sub-county PII location; county comes from `county_name` |
| time | not_in_gold | — | sub-annual PII detail |
| officer_id_hash | not_in_gold | — | PII (anonymized officer id) |
| department_name | not_in_gold | — | effectively constant (single agency, ETL #10) |
| vehicle_color / make / model / year | not_in_gold | — | vehicle descriptors; not part of county-year disparity grain |
| raw_row_number | not_in_gold | — | within-file source row id |
