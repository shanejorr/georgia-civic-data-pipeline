# nibrs_offenses — Bronze Data Structure

## Overview

- Topic: nibrs_offenses
- Source: fbi_cde (FBI Crime Data Explorer, NIBRS master state extracts)
- Files: 7 zip archives (`GA-2018.zip` … `GA-2024.zip`) + 1 sidecar CSV (`srs_estimates/estimated_crimes_1979_2024.csv`, 1979–2024)
- Unreadable files: none (all zips pass `python -m zipfile -t`; all member CSVs parse with polars)
- Year representation: `data_year` column inside every relational segment **and** in the zip filename (`GA-{YEAR}.zip`); values verified identical (e.g., every `NIBRS_incident` row in `GA-2024.zip` has `data_year = 2024`). Calendar year, not school/fiscal year.
- Filename-to-data year offset: **same** — filename year = data year exactly, all 7 zips.
- Detail levels: **agency (ORI)** grain only. Incidents link to agencies; no county/state rollup rows exist in bronze. County aggregation requires the `ori_to_county` crosswalk; state = sum of agencies.
- Percentage scale: n/a — all metrics are raw counts (offense/incident rows to be counted). The SRS sidecar is also raw counts + population.
- Checksums generated: 2026-07-02

**Bronze is zips of relational CSVs, not flat tables.** Each `GA-{YEAR}.zip` is the FBI's NIBRS master extract for Georgia for one data year: ~46–48 member files forming a star of segment tables (`NIBRS_incident`, `NIBRS_OFFENSE`, `NIBRS_VICTIM`, `NIBRS_OFFENDER`, `NIBRS_ARRESTEE`, property/weapon/bias segments) plus small code-lookup tables and docs (`README.md`, `nibrs_diagram.pdf`, postgres DDL). Zips are kept unextracted. This report covers the **offense-side tables** used by this topic: `agencies.csv`, `NIBRS_incident.csv`, `NIBRS_OFFENSE.csv`, `NIBRS_OFFENSE_TYPE.csv`, `NIBRS_month.csv` (+ small lookups `NIBRS_CLEARED_EXCEPT`, `NIBRS_LOCATION_TYPE`). The arrestee segments in these same zips are the bronze for the sibling `nibrs_arrests` topic (shared bronze — see `../nibrs_arrests/_provenance.md`).

## Source Provenance

Full details in [`_provenance.md`](./_provenance.md) (same directory).

- **Source URL**: FBI Crime Data Explorer, <https://cde.ucr.cjis.gov> — Documents & Downloads page. Files served from a private S3 bucket via signed URLs that expire in ~15 minutes; keys follow `nibrs/incident/{YEAR}/GA-{YEAR}.zip`.
- **Retrieved**: 2026-07-02
- **Method**: scripted fetch — `uv run python -m src.etl.criminal_justice.fbi_cde.download --roster` (re-discovers signed URLs each run; never hardcode URLs)
- **License**: US federal government work — public domain
- **Coverage**: no GA zips exist before 2018 or after 2024 (probed 1991–2026 on 2026-07-02). 2025 should appear after the FBI's annual release — re-run the downloader.

## File Checksums

Generated: 2026-07-02

| File | SHA-256 |
|------|---------|
| GA-2018.zip | d5ba63dcbb98b793077b9cac9cd2f226c1c7b9d2f4249372214558b22adb08eb |
| GA-2019.zip | a73c8d56dd7bfbd211f598831d19874768251283d066b424e17fd5515203d86d |
| GA-2020.zip | d983e86165989e906f92edcc3992187229e780bbbb8cd8148eb5399934040fdc |
| GA-2021.zip | 5622a12699271e4fb9b887a9ada2044a4dc1a41324145d3ec7e9d1b96b0795e8 |
| GA-2022.zip | d1b14af4328416a7e46c78403307960dd4d1a311cdb4f272d6f2d29b95c641fc |
| GA-2023.zip | d3af5298547ad40c0ec65dc566cd93b3a95692db2ab6bcf4ff44ddb5366b2962 |
| GA-2024.zip | 500467d4892572d619bd3b65c679c9a21db864100eba98e57f1cada27446c991 |
| srs_estimates/estimated_crimes_1979_2024.csv | 8dfaa630331d771da0ffe2597ce85ac2c31b10155ef8d4a8ae5a0572cda1421c |

## Zip Archive Structure

(Analog of the Excel-sheet section — members within each zip.)

| File(s) | Internal layout | Members | Notes |
|---------|----------------|---------|-------|
| GA-2018, GA-2019, GA-2020, **GA-2023** | nested under a `GA/` folder | 46–48 | strip the folder prefix when opening members |
| GA-2021, GA-2022, GA-2024 | flat (no folder) | 47–48 | 2021 additionally contains `database_dump.sql` |

Member-name deltas vs 2024: `NIBRS_ARRESTEE_GROUPB.csv` + `NIBRS_ARRESTEE_GROUPB_WEAPON.csv` exist only 2022+ (arrests topic, not this one). Non-data members in every zip: `README.md`, `nibrs_diagram.pdf`, `postgres_setup.sql`, `postgres_load.sql` — skip. **Do not assume folder layout from year** (2023 reverted to nested `GA/`); resolve members by basename.

## Summary

Incident-level NIBRS crime data for Georgia: every offense reported by every participating Georgia law-enforcement agency, 2018–2024. The measures a user wants are **offense counts** — by offense type (52 distinct NIBRS offense codes observed in 2024, e.g., Simple Assault `13B`, All Other Larceny `23H`, Destruction/Vandalism `290`), by the FBI's offense category (35) and crime-against class (Person / Property / Society), by agency → county, and by year — plus attempted-vs-completed splits and exceptional-clearance status. The `srs_estimates` sidecar CSV provides state-level estimated index-crime counts and rates context back to 1979 (violent crime, homicide, rape, robbery, aggravated assault, property crime, burglary, larceny, motor-vehicle theft).

**Coverage grows sharply across years** — Georgia transitioned from SRS to NIBRS around Oct 2019, so early years cover only early-adopter agencies:

| Data year | Agencies | Incidents | Offense rows |
|-----------|----------|-----------|--------------|
| 2018 | 49 | 816 | 879 |
| 2019 | 276 | 79,125 | 84,895 |
| 2020 | 401 | 306,000 | 332,191 |
| 2021 | 447 | 369,225 | 402,368 |
| 2022 | 455 | 397,697 | 434,291 |
| 2023 | 447 | 406,331 | 442,508 |
| 2024 | 434 | 397,862 | 432,444 |

2018–2019 (and to a lesser degree 2020) are **not comparable** to later years as a state series — year-over-year change is dominated by adoption, not crime.

## Eras

Era boundary is between the 2020 and 2021 zips. Same underlying tables; headers change from quoted-UPPERCASE to lowercase, plus a handful of real column renames.

### Era 2: 2021–2024 (representative: GA-2024.zip)

Lowercase headers. Core offense-side tables:

**`NIBRS_OFFENSE.csv`** (432,444 rows in 2024) — one row per offense within an incident (an incident can carry multiple offenses):

| Column | Description |
|--------|-------------|
| data_year | Data year (matches filename) |
| offense_id | Surrogate PK for the offense row |
| incident_id | FK → NIBRS_incident |
| offense_code | NIBRS offense code, e.g. `13B`, `23H`, `090` — **join key to NIBRS_OFFENSE_TYPE** |
| attempt_complete_flag | `C` completed / `A` attempted |
| location_id | FK → NIBRS_LOCATION_TYPE (47 location types) |
| num_premises_entered | Burglary only; null otherwise (99.7% null) |
| method_entry_code | Burglary only: `F` force / `N` no force; null otherwise (95.7% null) |

**`NIBRS_incident.csv`** (397,862 rows in 2024) — one row per incident:

| Column | Description |
|--------|-------------|
| data_year | Data year |
| agency_id | FK → agencies.csv (surrogate id; ORI lives in agencies) |
| incident_id | Surrogate PK |
| nibrs_month_id | FK → NIBRS_month (agency-month submission) |
| cargo_theft_flag | `t`/`f` (2024: 1,452 `t`) |
| submission_date / incident_date | Timestamps/dates; incident_date is the event date |
| report_date_flag | `t` = incident_date is actually the report date (2024: 4,798) |
| incident_hour | 0–23, null when unknown (2024: 8,556 null) |
| cleared_except_id | FK → NIBRS_CLEARED_EXCEPT: 1 Death of Offender, 2 Prosecution Declined, 3 In Custody of Other Jurisdiction, 4 Victim Refused to Cooperate, 5 Juvenile/No Custody, 6 **Not Applicable** (= not exceptionally cleared; 97.3% of 2024) |
| cleared_except_date | Null unless exceptionally cleared |
| incident_status | `ACCEPTED` (371,047) / `WARNINGS` (26,815) in era 2 |
| data_home / orig_format / did | FBI internal; data_home all-null in era 2 |

**`NIBRS_OFFENSE_TYPE.csv`** (86 rows, both eras) — offense-code lookup:

| Column | Description |
|--------|-------------|
| offense_code | PK, e.g. `13B` |
| offense_name | e.g. Simple Assault |
| crime_against | Person (17) / Property (27) / Society (41) / **Not a Crime** (1 — `90I` Runaway) |
| ct_flag / hc_flag / hc_code | Cargo-theft-eligible, hate-crime-eligible flags; hc_code is whitespace-padded (`'  '`) |
| offense_category_name | 35 categories (e.g. Assault Offenses, Larceny/Theft Offenses) |
| offense_group | `A` (72) / `B` (13) / `' '` (one space — the `90I` row). Only Group A offenses appear in NIBRS_OFFENSE; Group B are arrest-only |

**`agencies.csv`** (434 rows in 2024) — one row per agency-year, 59 columns. Key ones: `agency_id` (PK, joins incidents), `ori` (9-char, e.g. `GA0010100`), `pub_agency_name`, `agency_type_name` (City 228 / County 133 / University or College 43 / Other 24 / Other State Agency 6), `county_name` (UPPERCASE; never null; **27 rows are comma-separated multi-county**, e.g. `BARROW, GWINNETT`), `population`, `nibrs_start_date`, participation flags (`nibrs_participated`/`participated`/`publishable_flag` all `Y`, `covered_flag` all `N`, `agency_status` all `A` in 2024). Also officer/civilian employee counts and `officer_rate`/`employee_rate` (era 2 only — era 1 has junk headers here, see ETL Considerations).

**`NIBRS_month.csv`** — **grain changed between eras** (see ETL Considerations). Era 2: one row per *incident submission document* (397,862 rows in 2024 = incident count), with only 4,200 distinct `nibrs_month_id` (agency×month). `reported_status` is always `I`; second year column renamed `inc_data_year`.

#### Sample Data (NIBRS_OFFENSE 2024)

```text
data_year  offense_id  incident_id  offense_code  attempt_complete_flag  location_id  num_premises_entered  method_entry_code
2024       233157056   196405688    23F           C                      35           null                  null
2024       243588662   205521218    250           C                      98           null                  null
2024       243594734   205526739    240           C                      35           null                  null
2024       240471035   202788513    23H           C                      35           null                  null
2024       240532055   202844683    13B           C                      35           null                  null
```

#### Null Counts (2024)

- `NIBRS_OFFENSE`: num_premises_entered 430,996/432,444; method_entry_code 413,749; all other columns 0.
- `NIBRS_incident`: incident_hour 8,556; cleared_except_date 387,200; data_home 397,862 (all); others 0.

#### Categorical Columns (2024)

| Column | Distinct Values |
|--------|----------------|
| offense_code (OFFENSE) | 52 observed; top: 13B 67,378 · 23H 53,112 · 290 41,359 · 23F 35,097 · 35A 34,255 · 23C 28,514 · 26A 22,691 · 240 21,526 · 13C 20,261 · 220 18,695 |
| attempt_complete_flag | C 416,887 · A 15,557 |
| method_entry_code | F 11,117 · N 7,578 (else null) |
| cargo_theft_flag (incident) | f 396,410 · t 1,452 |
| report_date_flag | f 393,064 · t 4,798 |
| incident_status | ACCEPTED 371,047 · WARNINGS 26,815 |
| cleared_except_id | 6 (N/A) 387,200 · 2 6,598 · 4 2,110 · 3 948 · 5 936 · 1 70 |

#### Suppression Markers

None — NIBRS master files are unsuppressed raw agency reports. No `*`/`N/A`-style markers in any offense-side column. (The SRS sidecar embeds thousands separators, not suppression — see below.)

### Era 1: 2018–2020 (representative: GA-2020.zip)

Same tables, quoted-UPPERCASE headers, plus real differences:

| Era 1 (2018–2020) | Era 2 (2021–2024) | Impact |
|-------------------|--------------------|--------|
| `NIBRS_OFFENSE.OFFENSE_TYPE_ID` (int) | `offense_code` (string) | **Join-key change**: era 1 joins OFFENSE→OFFENSE_TYPE on the surrogate `OFFENSE_TYPE_ID`; era 2 joins on `offense_code`. Era 1's `NIBRS_OFFENSE_TYPE` has both `OFFENSE_TYPE_ID` and `OFFENSE_CODE` (9 cols); era 2 drops the id (8 cols) |
| `NIBRS_month` has `DATA_YEAR` **twice** | second occurrence renamed `inc_data_year` | polars auto-renames to `DATA_YEAR_duplicated_0` in era 1 |
| `NIBRS_month` grain: agency×month (2020: 4,662 rows) with `REPORTED_STATUS` I 3,901 / U 236 / Z 525 | grain: one row per incident document; `reported_status` all `I` | Era 2 cannot distinguish un-reported (U) / zero-report (Z) months |
| `INCIDENT_STATUS` = int `0` | `ACCEPTED` / `WARNINGS` strings | normalize or drop |
| `METHOD_ENTRY_CODE` uses `''` empty string (0 nulls) | proper nulls | treat `''` as null in era 1 |
| `DATA_HOME` = `'C'` populated | all null | FBI-internal either way |
| agencies cols 42/46/47: `ped.male_officer+ped.male_civilian`, `0`, `0` (duplicate literal `0` headers) | `male_officer+male_civilian`, `officer_rate`, `employee_rate` | era 1 rate columns are junk; polars dedup-renames the second `0` |
| `NIBRS_VICTIM.AGE_RANGE_HIGH_NUM` | `age_code_range_high` | victim-side only |
| `NIBRS_RELATIONSHIP` has extra `RELATIONSHIP_TYPE_ID` | dropped | lookup-only |
| `NIBRS_JUSTIFIABLE_FORCE` | era 2 header typo `justifiable_fore_id` | lookup-only |

2020 sample (NIBRS_OFFENSE): identical shape to era 2 apart from `OFFENSE_TYPE_ID` in place of `offense_code` — e.g. `(2020, 159177792, 132032554, 14, 'C', 20, null, '')`. Null counts mirror era 2 (`NUM_PREMISES_ENTERED` 331,211/332,191 null; `METHOD_ENTRY_CODE` empty-string instead of null). 2020 incident nulls: `INCIDENT_HOUR` 501, `CLEARED_EXCEPT_DATE` 296,670.

Offense vocabulary is stable across eras: identical 86 `offense_code` sets, one cosmetic rename (`11D` "Fondling" → "Criminal Sexual Contact" in 2024's lookup; same code/category).

## SRS estimates sidecar (`srs_estimates/estimated_crimes_1979_2024.csv`)

2,388 rows × 15 cols: `year`, `state_abbr`, `state_name`, `population`, `violent_crime`, `homicide`, `rape_legacy`, `rape_revised`, `robbery`, `aggravated_assault`, `property_crime`, `burglary`, `larceny`, `motor_vehicle_theft`, `caveats`. State-level estimated counts, GA 1979–2024 (46 rows); rows with null `state_abbr` are **national** totals (42 rows).

**Dirty formatting**: numeric columns contain thousands separators and stray spaces (`'10,912,876'`, `' 40,607'`) so most parse as strings; `state_name` is space-padded (`'     Georgia'`). `rape_legacy` (definition through ~2016) vs `rape_revised` (2013+) overlap and are never both populated in recent years. This is the pre-2019 GA history stopgap; it is **estimated** SRS data and will not match NIBRS raw counts even in overlapping years.

## ETL Considerations

1. **Agency (ORI) grain + county rollup.** No geography below agency. County aggregation requires `data/bronze/_crosswalks/ori_to_county/` (`cde_agency_by_state_abbr_ga.json` — dict keyed by UPPERCASE county name → list of `{ori, counties, agency_name, agency_type_name, nibrs_start_date, lat/lon, …}`). 27 of 434 agencies (2024) span multiple counties (`county_name` = `"BARROW, GWINNETT"`); decide and document an allocation rule (assign-to-first, split, or drop-from-county-rollup) — do not silently double-count.
2. **Methodology break / coverage ramp.** 2018–2019 are early-adopter-only (49 / 276 agencies); never present a state total time series across 2018–2024 without a coverage caveat or an agency-count/`agencies_reporting` companion column. Never splice `srs_estimates` (estimated SRS) with NIBRS raw counts into one unlabeled series.
3. **Era join-key change.** Era 1 OFFENSE→OFFENSE_TYPE joins on `OFFENSE_TYPE_ID`; era 2 on `offense_code`. Normalize era 1 by joining through its own zip's lookup to obtain `offense_code`, then use `offense_code` as the canonical categorical everywhere. Always read the lookup from the *same zip* as the data year.
4. **Zip member paths vary non-monotonically**: 2018/2019/2020/2023 nest under `GA/`; 2021/2022/2024 are flat. Resolve members by basename, never by literal path.
5. **Duplicate headers**: era-1 `NIBRS_month` has `DATA_YEAR` twice; era-1 `agencies.csv` has two literal `0` column names. Polars auto-renames (`_duplicated_0`) — don't rely on positional access; era-1 agency `officer_rate`/`employee_rate` positions are junk (`0`) — take employee rates from era 2 only, or skip.
6. **`NIBRS_month` grain flip** (agency-month in era 1 → incident-document in era 2, `reported_status` all `I`, dedupe on `nibrs_month_id` to recover 4,200 agency-months). Era-2 zips cannot tell unreported (`U`) from zero-crime (`Z`) months. If gold needs reporting-coverage flags, they are only trustworthy for 2018–2020.
7. **Value normalization**: era-1 `METHOD_ENTRY_CODE` uses `''` for missing (era 2 uses null); era-1 `INCIDENT_STATUS` is int `0` vs era-2 strings; booleans are `t`/`f` lowercase (era 2) vs mixed; `hc_code`/`offense_group` in the lookup carry literal whitespace values (`'  '`, `' '`) — strip and null.
8. **Multi-offense incidents**: offense rows exceed incidents by ~9% (an incident can have several offenses). Decide the gold measure explicitly — offense counts (count of NIBRS_OFFENSE rows) vs incident counts (distinct `incident_id`) — and name columns accordingly; the FBI publishes both conventions.
9. **`90I` Runaway is "Not a Crime"** (`crime_against = 'Not a Crime'`, blank offense_group) — decide whether to exclude it from offense counts; it does not appear in the 2024 offense data but guard anyway.
10. **`cleared_except_id = 6` means "Not Applicable"** — i.e. *not* exceptionally cleared, not a null. Exceptional clearance ≠ cleared by arrest; NIBRS master zips don't directly flag arrest clearances at the offense level (the `CLEARANCE_IND` lives on arrestee rows).
11. **11D rename**: 2024 lookup says "Criminal Sexual Contact"; 2020 says "Fondling". Pin one canonical offense-name vocabulary (recommend the latest year's lookup) so labels don't flap by data year.
12. **SRS sidecar needs scrubbing**: strip commas/whitespace before casting counts; trim `state_name`; national rows have null `state_abbr`; `rape_legacy`/`rape_revised` are definitionally different — never sum or coalesce without labeling.
13. **Dates**: `incident_date` is `YYYY-MM-DD`; `submission_date` is a timestamp; `report_date_flag = 't'` means `incident_date` is actually the report date (4,798 rows in 2024) — relevant if gold ever derives month-of-incident.
14. **Shared bronze**: `nibrs_arrests` reads the `NIBRS_ARRESTEE*` members of these same zips. Changes to these zips invalidate both topics' freshness checks.

## Gold Schema Classification

Offense-side columns only (arrestee/victim/offender segments belong to sibling topics). Likely gold grain: `year × county_fips × offense_code` (+ derived category rollups), with offense and incident counts.

| Bronze Column (canonical era-2 name) | Gold Role | Gold Name | Notes |
|--------------------------------------|-----------|-----------|-------|
| data_year | fact_key | year | int, calendar year |
| agencies.ori → crosswalk | fact_key | county_fips | via ori_to_county crosswalk; multi-county rule required |
| OFFENSE.offense_code (era 1 via OFFENSE_TYPE_ID join) | fact_categorical | offense_code | canonical NIBRS code; 52 observed values |
| OFFENSE_TYPE.offense_name / offense_category_name / crime_against / offense_group | fact_categorical or dimension_attribute | offense_category, crime_against | best modeled as a small offense dimension or denormalized categoricals; pin latest-year vocabulary |
| OFFENSE rows (counted) | fact_metric | offense_count | count, ≥0, unestimated raw reports |
| incident_id (distinct, counted) | fact_metric | incident_count | count; document multi-offense semantics |
| attempt_complete_flag | fact_categorical | attempt_status | attempted/completed (or a completed-only count column) |
| cleared_except_id | fact_categorical or fact_metric | exceptional_clearance | id 6 = not cleared exceptionally; consider a cleared_exceptionally_count |
| agencies (count of reporting agencies) | fact_metric | agencies_reporting | coverage companion — essential given the adoption ramp |
| location_id / NIBRS_LOCATION_TYPE | fact_categorical (optional) | location_type | 47 types; include only if gold keeps location breakdown |
| agencies.pub_agency_name, agency_type_name, population, county_name, ori | dimension_attribute | — | agency dimension / crosswalk inputs; names never in fact |
| incident_hour, incident_date, submission_date, cargo_theft_flag, report_date_flag | not_in_gold | — | below gold grain; document only |
| num_premises_entered, method_entry_code | not_in_gold | — | burglary-only detail, 95%+ null |
| incident_status, data_home, orig_format, did, ddocname | not_in_gold | — | FBI-internal QC/plumbing |
| NIBRS_month.* | not_in_gold | — | reporting coverage only trustworthy 2018–2020 (grain flip) |
| srs_estimates columns | separate concern | — | state-grain estimated SRS series 1979–2024; if published, keep as its own topic/series flagged `estimated`, never spliced with NIBRS counts |
| victim/offender/arrestee/property/drug/bias/weapon segments | not_in_gold (this topic) | — | other CJ topics (nibrs_arrests uses ARRESTEE segments from these zips) |
