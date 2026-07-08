# placements — Bronze Data Structure

## Overview

- Topic: placements
- Source: juvenile_clearinghouse (Georgia Juvenile Justice Data Clearinghouse)
- Files: 1 file spanning 2010–2025 (433,844 rows, 20 columns, ~72 MB CSV)
- Unreadable files: none (requires `encoding="utf8-lossy"` — see ETL Considerations)
- Year representation: `Year` column, single calendar year (2010–2025). Semantics are
  **"placement active during year"**, not admission year: 433,825 / 433,844 rows satisfy
  `admitted_year ≤ Year ≤ terminated_year` (or termination NULL). A placement spanning
  multiple years appears once per year it was active; only ~64% of rows were admitted in
  their `Year`.
- Filename-to-data year offset: filename carries the WordPress upload month (`2026-06`),
  not a data year; data years come from the `Year` column only.
- Detail levels: **individual placement/offense-level rows only** — one row per juvenile
  per placement per offense record. No aggregate/summary rows. Geography is county
  **names** (4 different county concepts) plus facility (site).
- Percentage scale: N/A — no percentage or rate columns; all numerics are counts/codes.
- Checksums generated: 2026-07-02

## Source Provenance

- **Source URL**: <https://juveniledata.georgiacourts.gov/wp-content/uploads/2026/06/Juvenile-Justice-Decision-Point-Placements-Raw-Data.csv>
  (resolved from the "Raw Data" section of <https://juveniledata.georgiacourts.gov/dashboards-reports/>;
  the upload-month path segment changes — the downloader re-scrapes the landing page every run)
- **Data dictionary**: <https://juveniledata.georgiacourts.gov/definitions/> (no co-located dictionary ships with the CSV)
- **Retrieved**: 2026-07-02T03:25:38Z (UTC)
- **Method**: scripted download — `uv run python -m src.etl.criminal_justice.juvenile_clearinghouse.download`
- Full details: `_provenance.md` in this directory.

## File Checksums

Generated: 2026-07-02

| File | SHA-256 |
|------|---------|
| decision_point_placements_raw_data_2026-06.csv | 9f8641398d3400cf22d7c27ffc1f891b0d0a9907eea10e7e82aa86fd499ed589 |

## Summary

Row-level records of Georgia juveniles held in **secure DJJ facilities** — RYDCs
(Regional Youth Detention Centers, pre-adjudication detention; 96% of rows) and YDCs
(Youth Development Campuses, post-commitment confinement; 4%) — 2010–2025. Each row is a
juvenile × placement × offense-record combination, carrying admission/termination dates,
facility (site) and its type, four county concepts (arrest, residence, facility, offense),
offense description, gender, and race. The measures a gold table can derive are **counts**:
new secure-detention/confinement admissions per year, distinct youth in custody, placements
by facility type, plus length-of-stay statistics from the date pair. Per the clearinghouse
definitions page, the official measures are "new instances" of secure detention (RYDC) and
secure confinement (YDC) — contiguous stays starting in the reporting period, with
transfers between same-type facilities not counted as new.

## Eras

Single era — one cumulative file covering all years with one schema. (Within-file label
drift exists in the duplicate-flag columns from 2023 on; see ETL Considerations #4.)

### Era 1: 2010–2025 (single file)

| Column | Description |
|--------|-------------|
| Year | Calendar year the placement was active (Int64, 2010–2025) |
| newjuvenileid | Anonymized juvenile identifier (Int64) — PII-adjacent, aggregate before gold |
| Placement Count | Small integer 1–15; semantics unresolved/noisy — see ETL Considerations #6 |
| Gender | `MALE` / `FEMALE` |
| Gender Code | 1 = MALE, 2 = FEMALE (fully redundant with Gender) |
| Race Value | `White`, `Black`, `AmInd`, `Asian`, `Other`, `Hispanic` |
| Race Code | 1=White, 2=Black, 3=AmInd, 4=Asian, 6=Other, 7=Hispanic (no code 5; redundant with Race Value) |
| Site Name | Facility name, 34 distinct (e.g. `METRO`, `GAINESVILLE`, `MACON (GIRLS)`) |
| Site Type | `RYDC` / `YDC` — **right-padded with trailing spaces to 10 chars on every row** |
| Arrest County | County of arrest, uppercase name (159 distinct incl. `OUT OF STATE`) |
| County of Residence | Juvenile's county of residence, uppercase name (160 distinct incl. `OUT OF STATE`) |
| Facility County | County where the facility sits (30 distinct — facility locations only) |
| Admitted Date | Placement start, string `DD-MM-YYYY` (day-first) |
| Date Terminated | Placement end, string `DD-MM-YYYY`; NULL = still in custody at extract (57,036 nulls) |
| Offense Date | Date of the associated offense, `DD-MM-YYYY` |
| Offense County | County of the offense, uppercase name (160 distinct incl. `OUT OF STATE`) |
| Offense Description | Free-text offense charge (443 distinct, uppercase) |
| DBL Placements | Duplicate-placement flag: NULL = first row of a placement; flagged = extra offense row for the same placement |
| Duplicate Offense Record | Flag: the same offense re-listed under a different placement in the same year |
| Other offenses | `Offense from Year YYYY` marker when the offense-date year ≠ `Year` (fully derivable from Offense Date) |

#### Sample Data

```text
shape: (5, 20)  (seed=42)
Year  newjuvenileid  Placement Count  Gender  Gender Code  Race Value  Race Code  Site Name  Site Type   Arrest County  County of Residence  Facility County  Admitted Date  Date Terminated  Offense Date  Offense County  Offense Description                                        DBL Placements              Duplicate Offense Record   Other offenses
2022  1619932        1                MALE    1            Black       2          ROCKDALE   "RYDC     " WALTON         WALTON               ROCKDALE         11-01-2022     null             23-09-2022    WALTON          ENTERING MOTOR VEHICLE WITH INTENT TO COMMIT THEFT/FELONY  Duplicate Placement Record  null                       null
2013  1000358        1                MALE    1            Black       2          PAULDING   "RYDC     " PAULDING       DEKALB               PAULDING         17-07-2013     30-09-2013       18-05-2013    DEKALB          CRIMINAL TRESPASS                                          null                        Duplicate Offense Record   null
2025  1972926        1                MALE    1            Black       2          SAVANNAH   "RYDC     " GLYNN          GLYNN                CHATHAM          26-03-2025     10-04-2025       27-02-2025    GLYNN           CRIMINAL TRESPASS                                          null                        Duplicate Offense Records  null
2019  1350232        2                MALE    1            Black       2          AUGUSTA    "RYDC     " RICHMOND       RICHMOND             RICHMOND         03-08-2018     09-11-2022       30-03-2019    RICHMOND        CRIMINAL ATTEMPT/ENTER AUTO                                Duplicate Placement Record  null                       null
2021  1853386        1                MALE    1            Black       2          METRO      "RYDC     " FULTON         FULTON               DEKALB           11-02-2021     05-04-2021       11-02-2021    FULTON          ENTERING MOTOR VEHICLE WITH INTENT TO COMMIT THEFT/FELONY  Duplicate Placement Record  null                       null
```

#### Statistics

```text
Year:            min 2010, max 2025, mean 2016.40
newjuvenileid:   min 6,418, max 1,990,260
Placement Count: min 1, max 15, mean 1.40 (323,119 rows = 1; 70,542 = 2; tail to 15)
Gender Code:     1 or 2 (mean 1.19 — 81% male)
Race Code:       1–7 (no 5), mean 2.25 (69% Black)
Admitted Date:   strings; date range 01-01-1900 (sentinel, 7 rows) then 2001 → 31-12-2025
Date Terminated: strings; 01-01-2011 → 31-12-2025
Offense Date:    strings; 01-01-2009 → 31-12-2025 (plus pre-2009 carried offenses)
```

Rows and distinct juveniles per year:

| Year | rows | distinct juveniles | distinct placements¹ |
|------|------|-------------------|---------------------|
| 2010 | 37,679 | 11,901 | 16,299 |
| 2011 | 33,721 | 10,429 | 14,613 |
| 2012 | 37,998 | 10,197 | 14,366 |
| 2013 | 35,238 | 9,427 | 12,865 |
| 2014 | 35,310 | 7,596 | 10,343 |
| 2015 | 29,890 | 7,200 | 9,831 |
| 2016 | 29,162 | 6,641 | 9,482 |
| 2017 | 27,413 | 6,288 | 8,925 |
| 2018 | 27,528 | 6,083 | 8,423 |
| 2019 | 24,792 | 5,769 | 7,851 |
| 2020 | 15,199 | 3,939 | 4,819 |
| 2021 | 16,816 | 3,923 | 4,942 |
| 2022 | 19,952 | 4,693 | 5,952 |
| 2023 | 21,839 | 5,045 | 6,399 |
| 2024 | 20,794 | 5,164 | 6,292 |
| 2025 | 20,513 | 4,854 | 6,081 |

¹ distinct (`newjuvenileid`, `Admitted Date`, `Site Name`) tuples within the year —
the robust placement count (see ETL Considerations #4/#5). The 2020–21 dip is the COVID
era, consistent with national juvenile-detention trends.

#### Null Counts

| Column | Nulls | Notes |
|--------|-------|-------|
| Year, newjuvenileid, Placement Count, Gender, Gender Code, Race Value, Race Code, Site Name, Site Type, Arrest County, County of Residence, Facility County | 0 | fully populated |
| Admitted Date | 3 | |
| Date Terminated | 57,036 | = still in custody at extract time (not missing data) |
| Offense Date / Offense County / Offense Description | 869 each | the **same** 869 rows have all three offense fields null (placement with no linked offense record; spread thinly across all years, 32–117/yr) |
| DBL Placements | 154,834 | NULL means "not a duplicate" — the flag's normal state |
| Duplicate Offense Record | 390,231 | ditto |
| Other offenses | 414,370 | NULL means offense year == placement year |

#### Categorical Columns

| Column | Distinct Values (count) |
|--------|------------------------|
| Gender | MALE (350,922), FEMALE (82,922) |
| Gender Code | 1 (350,922), 2 (82,922) — exact 1:1 with Gender |
| Race Value | Black (299,224), White (92,094), Hispanic (30,627), Other (10,855), Asian (835), AmInd (209) |
| Race Code | 2, 1, 7, 6, 4, 3 respectively — exact 1:1 with Race Value; code 5 never appears |
| Site Type | `RYDC␣␣␣␣␣␣` (418,168), `YDC␣␣␣␣␣␣␣` (15,676) — always right-padded |
| Site Name | 34 facilities; top: METRO (57,362), GAINESVILLE (35,364), MARIETTA (32,874), MACON (26,649), SAVANNAH (25,832), ROME (25,743), COLUMBUS (23,393), CLAYTON (20,043), AUGUSTA (18,293), CRISP (18,033) … CLAYTON TRANSITION DORM (22). Two sites span both types: MACON and AUGUSTA and EASTMAN have both RYDC and YDC rows |
| Arrest County | 159 distinct: 158 GA county names + OUT OF STATE (261). TALIAFERRO never appears |
| County of Residence | 160 distinct: 159 GA counties + OUT OF STATE (10,660) |
| Facility County | 30 distinct GA counties (facility locations only; no OUT OF STATE) |
| Offense County | 160 distinct: 159 GA counties + OUT OF STATE (1,086) |
| Offense Description | 443 distinct free-text charges (e.g. BURGLARY 1st OFFENSE, VIOLATION OF PROBATION, AFFRAY) |
| DBL Placements | `Duplicate Placement Record` (234,703 — years ≤2022), `DBL Pleacements Record` [sic] (44,307 — years 2023–25), NULL (154,834) |
| Duplicate Offense Record | `Duplicate Offense Record` (39,762 — ≤2022), `Duplicate Offense Records` (3,851 — 2023–25), NULL (390,231) |
| Other offenses | 31 distinct `Offense from Year YYYY` strings (1994–2026) |

**Asian / Pacific Islander check.** Race has 6 buckets with **no separate Pacific
Islander bucket** and no combined `Asian/Pacific Islander` label; `Hispanic` is coded *as
a race* (mutually-exclusive single-bucket coding, not a separate ethnicity flag). Because
this is individual-level data (one bucket per row), the buckets are exhaustive and
mutually exclusive by construction — the state-level math test does not apply. Where
Pacific Islander youth land is undocumented (plausibly `Other`, given unused code 5).
The transform must make an explicit demographics-dimension mapping decision for `Asian`
(map to `asian` vs `asian_pacific_islander`), `AmInd`, `Other`, and race-coded `Hispanic`
— document the choice in the transform, per data-cleaning-standards §5b.

#### Suppression Markers

None. No suppressed values — all numeric columns parsed cleanly as Int64. (This is
row-level data; suppression appears at the aggregation step, not in bronze. **Gold-side
note:** small county×year×demographic cells will be tiny — apply the project's small-cell
suppression policy when aggregating.)

## ETL Considerations

1. **Read with `encoding="utf8-lossy"`.** The file has invalid UTF-8 (Windows-1252
   bytes). 4,618 `Offense Description` values contain U+FFFD after lossy decode, always
   where an en-dash was (e.g. `BATTERY�- FAMILY VIOLENCE`, `AGGRAVATED BATTERY � PEACE
   OFFICER`). Normalize U+FFFD to `-` (or strip) when standardizing offense text. No BOM.

2. **Dates are day-first `DD-MM-YYYY`.** Parse explicitly with `%d-%m-%Y` — never
   auto-infer. All non-null values in all three date columns parse cleanly under this
   format (0 failures; max first token = 31, and >60% of values have day > 12, so the
   format is proven, not assumed). Seven `Admitted Date` values are the sentinel
   `01-01-1900` → NULL them (known-bad, log counts). 3 rows have NULL `Admitted Date`.

3. **Strip whitespace on all string columns.** `Site Type` is right-padded to 10 chars on
   **every** row (`"RYDC      "`); 9,606 `Offense Description` values have stray padding.

4. **Duplicate-flag label drift (2023–2025).** `DBL Placements` switches from `Duplicate
   Placement Record` (2010–2022) to the misspelled `DBL Pleacements Record` (2023–2025);
   `Duplicate Offense Record` similarly gains an `…Records` plural variant in 2023–2025.
   Treat flag columns as boolean **non-null = flagged**; never match on exact label.

5. **The 2014 duplicate flags are broken — do not count placements from `DBL Placements`.**
   In every year except 2014, unflagged-row count ≈ distinct (`newjuvenileid`,
   `Admitted Date`, `Site Name`) tuples (within ~3%). In 2014, unflagged = 19,186 vs
   10,343 actual distinct placements — the flag under-marks duplicates that year.
   **Count placements as distinct (`newjuvenileid`, `Admitted Date`, `Site Name`) tuples
   within a `Year`**, which is robust across all years, rather than counting unflagged rows.
   Use `Duplicate Offense Record` (non-null) only if counting distinct offenses.

6. **`Placement Count` is unreliable — recommend excluding it.** It is not constant
   within (`Year`, `newjuvenileid`) for 11% of juvenile-years, and matches neither
   distinct admissions, distinct admission×site tuples, nor unflagged-row counts under
   any tested definition. Derive all counts from the rows themselves.

7. **`Year` = active-during-year, so naive per-year placement counts double-count
   multi-year stays.** A stay spanning years appears in each year's block. Decide the
   gold measure deliberately, aligned with the clearinghouse definitions page: the
   official measures are **new instances** (stay *started* in the reporting period —
   filter `admitted_year == Year`), while all rows in a year block give
   **served-during-year**. New-admission placements per year: 2010: 9,955 … 2025: 3,706
   (roughly 60% of distinct placements per year block). Also note the official definition
   excludes transfers between same-type facilities from "new instances" — a transfer
   shows up here as a new (site, admitted-date) tuple and is not directly detectable, so
   gold counts will slightly overstate the official measure; document this limitation.
   16 rows (5 juveniles) violate the year window entirely (`Year` outside
   [admitted, terminated]) — known-bad; drop or NULL with logging.

8. **PII gate: aggregate before gold.** `newjuvenileid` is youth-level and PII-adjacent.
   Gold must be county/year (× demographic × facility-type) aggregates. Never publish
   row-level data; apply small-cell suppression at aggregation.

9. **Four county concepts — choose deliberately.** Arrest / Residence / Facility /
   Offense. `County of Residence` is the natural primary geography for county rates
   (where youth are from); `Facility County` only reflects the 30 facility locations and
   would misattribute. Whatever is chosen, county values are **uppercase names, no
   FIPS** — map through the counties dimension (`contracts/_dimensions/counties.odcs.yaml`)
   to 5-digit FIPS. Handle `OUT OF STATE` explicitly (residence: 10,660 rows ≈ 2.5%;
   arrest: 261; offense: 1,086) — NULL the FIPS or bucket separately, don't silently drop.
   TALIAFERRO (GA's smallest county) never appears as Arrest County — real sparsity, not
   an error.

10. **869 rows (~0.2%) have no offense record** (all three offense fields null together).
    They are still valid placement rows — keep for placement counts; they simply have no
    offense attribution.

11. **True duplicate rows exist** even on the full natural key (Year, juvenile, site,
    admitted date, offense date, offense description, offense county) — 28,378 key groups
    have >1 row. This is why aggregation must use distinct-tuple counts, not row counts.

12. **`Other offenses` is derivable** — it exactly equals "offense-date year ≠ `Year`"
    (19,474/19,474 match the offense-date year). Drop it; recompute if needed.

13. **Redundant code/label pairs.** `Gender Code` and `Race Code` are exact 1:1 with
    their labels — verify the 1:1 holds on refresh (cheap invariant), then drop the codes.

14. **Offense descriptions are free text (443 distinct).** If offense breakdown is wanted
    in gold, it needs a curated category mapping (violent/property/drug/status/VOP…) —
    a substantial judgment task; reasonable v1 is to omit offense detail entirely.

15. **Refresh behavior:** one cumulative file re-published ~annually (June); a refresh
    replaces the whole history — expect the checksum to change and all years to need
    re-validation, not just the newest year.

## Gold Schema Classification

Bronze is individual-level; gold must be an **aggregate** (county × year × demographic ×
facility type). Classification below is each bronze column's role in producing that gold.

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| Year | fact_key | year | Calendar year; choose new-admissions vs served-during-year semantics (ETL #7) |
| County of Residence | fact_key | county_fips | Recommended primary geography; name → FIPS via counties dimension; OUT OF STATE → NULL FIPS (documented) |
| Gender | fact_key | demographic | → demographics dimension (`male`/`female`) |
| Race Value | fact_key | demographic | → demographics dimension; explicit mapping decision for Asian/AmInd/Other/Hispanic (see A/PI check) |
| Site Type | fact_categorical | facility_type | `rydc` (detention) / `ydc` (confinement) after stripping padding; drives the two official measures |
| newjuvenileid | not_in_gold | — | PII-adjacent; used only to compute distinct-youth and distinct-placement counts |
| Admitted Date | not_in_gold | — | Used to derive new-admission filter and length-of-stay metrics; NULL the 01-01-1900 sentinels |
| Date Terminated | not_in_gold | — | With Admitted Date → optional length-of-stay metric; NULL = still in custody |
| Site Name | not_in_gold | — | Facility-level detail below gold grain; revisit if a facility dimension is ever wanted |
| Facility County | not_in_gold | — | Facility location, not youth geography (30 counties only) |
| Arrest County | not_in_gold | — | Alternate geography; not the chosen concept |
| Offense County | not_in_gold | — | Alternate geography; not the chosen concept |
| Offense Date | not_in_gold | — | Offense-level detail below gold grain |
| Offense Description | not_in_gold | — | Free text; needs curated category mapping before it could serve as a categorical (ETL #14) |
| Placement Count | not_in_gold | — | Unreliable/ambiguous (ETL #6); derive counts from rows |
| Gender Code | not_in_gold | — | Redundant 1:1 with Gender |
| Race Code | not_in_gold | — | Redundant 1:1 with Race Value |
| DBL Placements | not_in_gold | — | Dedup logic only; broken for 2014 (ETL #5) |
| Duplicate Offense Record | not_in_gold | — | Dedup logic only |
| Other offenses | not_in_gold | — | Fully derivable from Offense Date (ETL #12) |

Derived gold metrics (computed, not bronze columns): `placement_count`
(distinct juvenile × admitted-date × site tuples — the **key metric** candidate),
`youth_count` (distinct juveniles), optionally median/mean length-of-stay.
