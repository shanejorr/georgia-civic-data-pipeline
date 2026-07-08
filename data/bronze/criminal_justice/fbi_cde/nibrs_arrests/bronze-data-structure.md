# nibrs_arrests — Bronze Data Structure

## Overview

- Topic: nibrs_arrests
- Source: fbi_cde
- Files: **shared bronze** — 7 zip files (`GA-2018.zip` … `GA-2024.zip`) stored once in
  `../nibrs_offenses/` (see `_provenance.md` here and there). This topic reads only the
  **arrestee segments** inside each zip:
  - `NIBRS_ARRESTEE.csv` — Group A arrests (incident-linked), all 7 years
  - `NIBRS_ARRESTEE_GROUPB.csv` — Group B arrests (arrest-only offenses), **2022–2024 only**
  - `NIBRS_ARRESTEE_WEAPON.csv` / `NIBRS_ARRESTEE_GROUPB_WEAPON.csv` — weapon child segments
  - Code lookups (`NIBRS_ARREST_TYPE.csv`, `REF_RACE.csv`, `NIBRS_ETHNICITY.csv`,
    `NIBRS_AGE.csv`, `NIBRS_OFFENSE_TYPE.csv`, `NIBRS_WEAPON_TYPE.csv`) and the join-path
    tables (`NIBRS_incident.csv`, `agencies.csv`)
- Unreadable files: none (all 7 zips pass `python -m zipfile -t`; every arrestee CSV parses)
- Year representation: `DATA_YEAR`/`data_year` column in every segment; equals the filename
  year. This is the **NIBRS data year** (incident year for Group A), not strictly the arrest
  calendar year — see "Year representation" below.
- Filename-to-data year offset: same (verified: each file's `data_year` is single-valued and
  equals the filename year)
- Detail levels: record-level (one row per arrestee per offense). Geography is **derived**:
  Group A rows join `incident_id → NIBRS_incident.agency_id → agencies.ori` → county FIPS via
  the `ori_to_county` crosswalk (join verified 100% for 2020 and 2024). **Group B rows have
  no agency or incident link at all** → state level only. Gold detail levels: `county`
  (Group A only) and `state`.
- Percentage scale: n/a — no percentage columns; all bronze values are codes, dates, or ages
- Checksums generated: 2026-07-02

## Source Provenance

- **Source URL**: FBI Crime Data Explorer "Documents & Downloads",
  <https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/downloads> (S3 keys
  `nibrs/incident/{YEAR}/GA-{YEAR}.zip` behind ~15-min signed URLs — re-discover, never
  hardcode)
- **Retrieved**: 2026-07-02T12:22–12:24Z
- **Method**: scripted fetch — `uv run python -m src.etl.criminal_justice.fbi_cde.download`
  (full retrieval mechanics + license (public domain) in `../nibrs_offenses/_provenance.md`)

## File Checksums

Generated: 2026-07-02. Paths are relative to this directory — the files live in the shared
`../nibrs_offenses/` bronze (do not duplicate them here).

| File | SHA-256 |
|------|---------|
| ../nibrs_offenses/GA-2018.zip | d5ba63dcbb98b793077b9cac9cd2f226c1c7b9d2f4249372214558b22adb08eb |
| ../nibrs_offenses/GA-2019.zip | a73c8d56dd7bfbd211f598831d19874768251283d066b424e17fd5515203d86d |
| ../nibrs_offenses/GA-2020.zip | d983e86165989e906f92edcc3992187229e780bbbb8cd8148eb5399934040fdc |
| ../nibrs_offenses/GA-2021.zip | 5622a12699271e4fb9b887a9ada2044a4dc1a41324145d3ec7e9d1b96b0795e8 |
| ../nibrs_offenses/GA-2022.zip | d1b14af4328416a7e46c78403307960dd4d1a311cdb4f272d6f2d29b95c641fc |
| ../nibrs_offenses/GA-2023.zip | d3af5298547ad40c0ec65dc566cd93b3a95692db2ab6bcf4ff44ddb5366b2962 |
| ../nibrs_offenses/GA-2024.zip | 500467d4892572d619bd3b65c679c9a21db864100eba98e57f1cada27446c991 |

## Zip Member Structure

Each zip holds one Georgia NIBRS data year as ~47–49 relational CSVs plus docs
(`README.md`, `nibrs_diagram.pdf`, `postgres_setup.sql`, `postgres_load.sql`).

| File(s) | Nesting | Arrestee members present |
|---------|---------|--------------------------|
| GA-2018 … GA-2020, GA-2023 | members under a `GA/` folder | see below |
| GA-2021, GA-2022, GA-2024 | flat (no folder) | see below |

**The `GA/` nesting is inconsistent across years** (2018–2020 and 2023 nested; 2021, 2022,
2024 flat) — the transform must resolve members by basename, never by literal path.

| Member | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|--------|------|------|------|------|------|------|------|
| NIBRS_ARRESTEE.csv | 315 | 20,909 | 66,107 | 89,021 | 95,901 | 92,942 | 96,433 |
| NIBRS_ARRESTEE_GROUPB.csv | — | — | — | — | 86,162 | 92,082 | 94,440 |
| NIBRS_ARRESTEE_WEAPON.csv | 317 | 20,930 | 66,247 | 89,212 | 96,126 | 93,157 | 96,649 |
| NIBRS_ARRESTEE_GROUPB_WEAPON.csv | — | — | — | — | 86,207 | 92,119 | 94,485 |

(row counts exclude the header)

## Summary

Record-level arrest data for Georgia from FBI NIBRS: one row per arrestee per offense, with
the arrest type (on-view / summoned-cited / taken into custody), the NIBRS offense code
(57 distinct Group A codes in 2024, led by drug/narcotic violations 35A, simple assault 13B,
shoplifting 23C; 7 Group B `90x` codes led by "all other offenses" 90Z), arrest date, and
arrestee age/sex/race/ethnicity. Group A arrests link to the reporting agency (→ county);
Group B arrests (drunkenness, DUI, disorderly conduct, etc.) exist only from 2022 and carry
no agency link. The natural gold product is **arrest counts by county × year × offense
(category) × demographic**, plus state-level totals.

## Eras

Era boundary is driven by the arrestee-segment column names (and the code-ID systems, which
change with them).

### Era 1: 2018–2020 — UPPERCASE columns, `OFFENSE_TYPE_ID`

`NIBRS_ARRESTEE.csv` columns:

| Column | Description |
|--------|-------------|
| DATA_YEAR | NIBRS data year (= filename year) |
| ARRESTEE_ID | Row ID, unique per arrestee segment |
| INCIDENT_ID | FK → `NIBRS_incident.csv` (INCIDENT_ID → AGENCY_ID → agencies) |
| ARRESTEE_SEQ_NUM | Arrestee sequence within the incident (1–14 in 2020) |
| ARREST_DATE | Arrest date, `DD-MON-YY` (e.g. `12-DEC-20`) |
| ARREST_TYPE_ID | 1 = On View, 2 = Summoned/Cited, 3 = Taken Into Custody |
| MULTIPLE_INDICATOR | C = Count / M = Multiple (duplicate segment) / N — see ETL notes |
| OFFENSE_TYPE_ID | Integer FK → `NIBRS_OFFENSE_TYPE.csv` (era-1 lookup has both `OFFENSE_TYPE_ID` and `OFFENSE_CODE`) |
| AGE_ID | 4 = Unknown, 5 = Age in Years (see AGE_NUM), 6 = Over 98 (era-1 7-row lookup) |
| AGE_NUM | Age in years (null when unknown; 37 nulls in 2020) |
| SEX_CODE | M / F |
| RACE_ID | Era-1 codes: 0 = Unknown, 1 = White, 2 = Black, 3 = American Indian, 4 = Asian, 8 = Pacific Islander |
| ETHNICITY_ID | Era-1 codes: 1 = Hispanic, 2 = Not Hispanic, 3 = Unknown (null when unreported) |
| RESIDENT_CODE | R = Resident, N = Nonresident, U = Unknown, `''` = missing |
| UNDER_18_DISPOSITION_CODE | H = Handled within department, R = Referred to other authorities, `''` = n/a (adults) |
| CLEARANCE_IND | **Empty string for all rows in all years** |
| AGE_RANGE_LOW_NUM | = AGE_NUM (0-filled semantics vary; not analytically useful) |
| AGE_RANGE_HIGH_NUM | Almost always 0 (only set for age ranges) |

`NIBRS_ARRESTEE_WEAPON.csv`: `DATA_YEAR, ARRESTEE_ID, WEAPON_ID, NIBRS_ARRESTEE_WEAPON_ID`.
No Group B files in this era.

#### Sample Data (GA-2020, NIBRS_ARRESTEE.csv, 66,107 rows)

| DATA_YEAR | ARRESTEE_ID | INCIDENT_ID | SEQ | ARREST_DATE | ARREST_TYPE_ID | MULT | OFFENSE_TYPE_ID | AGE_ID | AGE_NUM | SEX | RACE_ID | ETH_ID | RES | U18 | CLR |
|-----------|------------|-------------|-----|-------------|----------------|------|-----------------|--------|---------|-----|---------|--------|-----|-----|-----|
| 2020 | 41502023 | 134334740 | 1 | 12-DEC-20 | 1 | N | 23 | 5 | 39 | M | 1 | 2 | N | '' | '' |
| 2020 | 41492334 | 134286995 | 1 | 26-NOV-20 | 3 | C | 27 | 5 | 32 | M | 2 | 2 | R | '' | '' |
| 2020 | 38495428 | 124450256 | 1 | 08-MAR-20 | 3 | N | 23 | 5 | 63 | M | 2 | 2 | R | '' | '' |
| 2020 | 40809228 | 132034621 | 2 | 11-NOV-20 | 1 | N | 23 | 5 | 32 | M | 2 | 2 | N | '' | '' |
| 2020 | 40358186 | 130524447 | 1 | 09-AUG-20 | 1 | N | 51 | 5 | 43 | M | 2 | 3 | R | '' | '' |

#### Statistics (GA-2020)

- `AGE_NUM`: mean 32.4, std 12.4, min 5, max 93 (37 nulls)
- `ARRESTEE_SEQ_NUM`: 1–14, mean 1.19
- `OFFENSE_TYPE_ID`: 58 distinct; top: 16→35A Drug/Narcotic (19,960), 51→13B Simple Assault
  (12,112), 23→23C Shoplifting (7,042), 27→13A Aggravated Assault (5,672), 5→290 Vandalism (3,059)

#### Null Counts (GA-2020)

All columns 0 nulls except: `AGE_NUM` 37, `AGE_RANGE_LOW_NUM` 37, `AGE_RANGE_HIGH_NUM` 37,
`ETHNICITY_ID` 14,993. **Missing string values are empty strings, not nulls** (`RESIDENT_CODE`
17,278 × `''`; `UNDER_18_DISPOSITION_CODE` 60,846 × `''`; `CLEARANCE_IND` 66,107 × `''`).

#### Categorical Columns (GA-2020, with counts)

| Column | Distinct Values |
|--------|----------------|
| ARREST_TYPE_ID | 1 On View (33,526), 2 Summoned/Cited (6,868), 3 Taken Into Custody (25,713) |
| MULTIPLE_INDICATOR | C (5,720), M (2,234), N (58,153) |
| SEX_CODE | M (47,346), F (18,761) |
| RACE_ID | 0 Unknown (482), 1 White (30,095), 2 Black (35,080), 3 Am. Indian (75), 4 Asian (349), 8 Pacific Islander (26) |
| ETHNICITY_ID | 1 Hispanic (3,114), 2 Not Hispanic (46,098), 3 Unknown (1,902), null (14,993) |
| RESIDENT_CODE | R (30,645), N (14,597), U (3,587), '' (17,278) |
| UNDER_18_DISPOSITION_CODE | H (2,150), R (3,111), '' (60,846) |
| CLEARANCE_IND | '' only |

#### Suppression Markers

None — record-level data with no suppressed cells in any era. (Privacy is instead handled by
aggregation in the transform; see ETL Considerations.)

### Era 2: 2021–2024 — lowercase columns, `offense_code`; Group B from 2022

`NIBRS_ARRESTEE.csv` columns (same 18-column layout as era 1 except):

| Change vs era 1 | Detail |
|-----------------|--------|
| All column names lowercase | `data_year`, `arrestee_id`, … |
| `OFFENSE_TYPE_ID` → `offense_code` | NIBRS alphanumeric code directly (e.g. `35A`, `13B`) — no lookup join needed |
| `ARREST_DATE` format | ISO `YYYY-MM-DD` (e.g. `2024-01-01`) |
| Missing values | Proper nulls, not empty strings |
| Code-ID systems changed | race_id 10/20/30/40/50/70/98/99, ethnicity_id 10–50, age_id 1–104 (one ID per single year of age; 103 = Unknown) |
| `NIBRS_ARRESTEE_WEAPON.csv` | column order now `data_year, arrestee_id, nibrs_arrestee_weapon_id, weapon_id` (same names) |

`NIBRS_ARRESTEE_GROUPB.csv` (**2022–2024 only**, 15 columns): `data_year,
groupb_arrestee_id, arrestee_seq_num, arrest_date, arrest_type_id, offense_code, age_id,
age_num, sex_code, race_id, ethnicity_id, resident_code, under_18_disposition_code,
age_range_low_num, age_range_high_num`. **No `incident_id`, no agency column** (confirmed
against the zip's own `postgres_setup.sql`) — Group B arrests cannot be placed in a county.
`NIBRS_ARRESTEE_GROUPB_WEAPON.csv`: `data_year, groupb_arrestee_id, weapon_code, weapon_id`.

#### Sample Data (GA-2024, NIBRS_ARRESTEE_GROUPB.csv, 94,440 rows)

| data_year | groupb_arrestee_id | seq | arrest_date | arrest_type_id | offense_code | age_id | age_num | sex | race_id | eth_id | res | u18 |
|-----------|--------------------|-----|-------------|----------------|--------------|--------|---------|-----|---------|--------|-----|-----|
| 2024 | 52872477 | 1 | 2024-03-05 | 1 | 90Z | 22 | 19 | M | 10 | 10 | R | null |
| 2024 | 52883710 | 1 | 2024-02-19 | 1 | 90J | 53 | 50 | F | 10 | 20 | R | null |
| 2024 | 56115034 | 1 | 2024-11-29 | 1 | 90D | 55 | 52 | F | 98 | 50 | N | null |
| 2024 | 56636399 | 1 | 2024-01-02 | 1 | 90B | 34 | 31 | F | 10 | 20 | R | null |
| 2024 | 52008920 | 1 | 2024-01-16 | 3 | 90Z | 26 | 23 | F | 20 | 20 | N | null |

#### Statistics (GA-2024)

- `NIBRS_ARRESTEE.csv` (96,433 rows): `age_num` mean 33.4, min 0, max 99;
  `arrestee_seq_num` 1–36; `arrest_date` min 2024-01-01, **max 2025-03-31** (Group A arrests
  attach to the incident's data year and can occur the following calendar year)
- `NIBRS_ARRESTEE_GROUPB.csv` (94,440 rows): `age_num` mean 35.6, min 0, max 99;
  `arrestee_seq_num` 1–99; `arrest_date` min 2024-01-01, max 2024-12-31 (stays in-year)

#### Null Counts (GA-2024)

- Group A: 0 nulls everywhere except `resident_code` 18,170, `under_18_disposition_code`
  86,880, `clearance_ind` 96,433 (all rows — column is dead), `age_range_low_num` 28,
  `age_range_high_num` 96,175
- Group B: 0 nulls except `resident_code` 23,929, `under_18_disposition_code` 90,032,
  `age_range_low_num` 34,310, `age_range_high_num` 93,980

#### Categorical Columns (GA-2024, with counts)

| Column | Group A (NIBRS_ARRESTEE) | Group B |
|--------|--------------------------|---------|
| arrest_type_id | 1 (52,922), 2 (10,627), 3 (32,884) | 1 (47,188), 2 (9,034), 3 (38,218) |
| multiple_indicator | C (8,180), M (1,522), N (86,731) | — (column absent) |
| sex_code | M (68,539), F (27,894) | M (68,777), F (25,663) |
| race_id | 10 White (37,703), 20 Black (56,698), 30 Am. Indian (154), 40 Asian (854), 50 Pacific Islander (53), 98 Unknown (971) | 10 (44,874), 20 (45,762), 30 (196), 40 (797), 50 (72), 98 (2,739) |
| ethnicity_id | 10 Hispanic (7,623), 20 Not Hispanic (72,798), 40 Unknown (3,568), 50 Not Specified (12,444) | 10 (10,924), 20 (55,480), 40 (7,544), 50 (20,492) |
| resident_code | R (43,444), N (20,747), U (14,072), null (18,170) | R (37,108), N (22,629), U (10,774), null (23,929) |
| under_18_disposition_code | H (3,827), R (5,726), null (86,880) | H (2,115), R (2,293), null (90,032) |
| offense_code | 57 distinct; top: 35A (24,687), 13B (19,069), 23C (12,186), 13A (7,574), 26A (4,362), 290 (3,893) | 7 distinct: 90Z (56,868), 90D DUI (20,207), 90C Disorderly Conduct (7,838), 90J Trespass (5,233), 90B Curfew (1,778), 90G Liquor Law (1,506), 90F Family Offenses (1,010) |

#### Suppression Markers

None.

### Code lookups and the agency join path (both eras)

- **`NIBRS_ARREST_TYPE.csv`** (3 rows, stable across eras): 1 = On View,
  2 = Summoned / Cited, 3 = Taken Into Custody.
- **`REF_RACE.csv`** (12 rows): the ID column values differ by era (era 1: 0,1,2,3,4,8,…;
  era 2: 98,10,20,30,40,50,…) for the *same* codes W/B/I/A/P/U — always join on the same
  year's lookup. Legacy buckets (combined "AP" 1980–2012, Chinese/Japanese/Other 1960–1979)
  exist in the lookup but never appear in the data.
- **`NIBRS_ETHNICITY.csv`**: era 1 has 4 rows (1 H, 2 N, 3 U, 4 M); era 2 has 5
  (10 H, 20 N, 30 M, 40 U, 50 X Not Specified). Data uses H/N/U (+X in era 2); era-1 missing
  is a null ID instead of X.
- **`NIBRS_AGE.csv`**: era 1 = 7 rows (categories; the actual age is `AGE_NUM`); era 2 = 104
  rows (one ID per single year of age, 103 = Unknown, 104 = Not Specified). `age_num` is
  present and consistent in both eras — use it and ignore `age_id`.
- **`NIBRS_OFFENSE_TYPE.csv`**: era 1 has 9 columns *including* `OFFENSE_TYPE_ID` →
  `OFFENSE_CODE`; era 2 has 8 (keyed by `offense_code` directly). 86 offense types; carries
  `offense_category_name` and `offense_group` (A/B) — the natural rollup attributes.
  Spot-checked era-1 translation: 16→35A, 51→13B, 23→23C, 27→13A, 5→290.
- **`NIBRS_WEAPON_TYPE.csv`** (38 rows): armed-arrestee codes; Group B weapon rows are 98%
  `01 Unarmed` in 2024.
- **Agency join (Group A only)**: `NIBRS_incident.csv` (`incident_id`, `agency_id`, …) →
  `agencies.csv` (434 GA agencies in 2024; has `ori`, `pub_agency_name`, `agency_type_name`,
  `county_name`, `population`). Verified: 100% of Group A arrestee rows in both 2020 and 2024
  resolve to an agency with a non-null `county_name`.

## ETL Considerations

1. **Shared bronze** — read the zips from `data/bronze/criminal_justice/fbi_cde/nibrs_offenses/`;
   this directory intentionally holds no data files. Zips stay unextracted (read members via
   `zipfile` in memory).
2. **Resolve zip members by basename.** The `GA/` folder nesting is inconsistent
   (2018–2020 + 2023 nested, 2021/2022/2024 flat). Never hardcode member paths.
3. **Era handling.** Lowercase all column names on read, then eras align except for the
   offense column: era 1 needs `OFFENSE_TYPE_ID → OFFENSE_CODE` via **the same zip's**
   `NIBRS_OFFENSE_TYPE.csv`. Never reuse a lookup across eras — `race_id`, `ethnicity_id`,
   and `age_id` renumbered between era 1 and era 2 (e.g. Black = 2 in 2020 but 20 in 2024;
   joining the wrong year's lookup silently mislabels every demographic).
4. **Era-1 empty strings.** `RESIDENT_CODE`, `UNDER_18_DISPOSITION_CODE`, `CLEARANCE_IND`
   use `''` for missing in 2018–2020 (proper nulls from 2021). Normalize `'' → null` before
   recode maps, or the manifest will flag `''` as unmapped.
5. **Group B ≠ county data.** `NIBRS_ARRESTEE_GROUPB.csv` has no incident/agency link
   (confirmed in the zip's `postgres_setup.sql`), so Group B arrests can only feed
   state-level rows. They are also entirely **absent 2018–2021** — a state total that sums
   Group A + Group B is only possible 2022+; flag or version this coverage break, never
   splice. (Group B is ~half of all arrests: 94,440 of 190,873 in 2024.)
6. **SRS→NIBRS transition (GA Oct 2019).** 2018 has 315 arrestee rows and 2019 ~21k
   (early-adopter agencies only); 2020 is still partial coverage. Counts are unestimated raw
   agency reports. Consider dropping 2018 (and possibly 2019) or carrying an explicit
   coverage caveat — these years must never read as statewide totals.
7. **`multiple_indicator` (Group A only)** — NIBRS Data Element 44: when one arrest clears
   multiple incidents, one segment is marked C (Count) and the duplicates M (Multiple).
   **Exclude `M` rows when counting arrests** (2,234 in 2020; 1,522 in 2024) or the same
   physical arrest is double-counted. Verify against the NIBRS user manual during transform
   review.
8. **`data_year` is the grain year.** Group A `arrest_date` spills past the data year
   (2024 file: max 2025-03-31) because arrests attach to the incident's year. Use
   `data_year`, not the arrest date's calendar year, as the fact `year`; don't derive a
   `month` categorical from Group A dates without documenting this.
9. **ORI → county.** `agencies.csv` `county_name` is populated for 100% of matched rows but
   contains multi-county values (`"MERIWETHER, TALBOT"`, …). Roll up via the
   `ori_to_county` crosswalk (`data/gold/crosswalks/ori_to_county.parquet`,
   built by `src/etl/crosswalks/build_ori_to_county.py`) rather than parsing `county_name`.
   Per domain rules, agency identifiers stay out of gold.
10. **PII stays in bronze.** These are person-level records (age, sex, race, ethnicity,
    date). Gold must serve **aggregated counts only** (county/state × year × offense ×
    demographic), consistent with the CJ domain rule; small cells are acceptable to publish
    per FBI practice (the source is already public record-level data), but do not publish
    record-level rows.
11. **Race buckets (A/PI check).** Bronze carries **split** Asian (era-1 ID 4 / era-2 ID 40)
    and Pacific Islander (8 / 50) codes — no combined Asian/Pacific-Islander rows appear in
    any year. Map to the split `asian` / `pacific_islander` demographics. Race and ethnicity
    (Hispanic) are **separate NIBRS fields**: race values are not Hispanic-exclusive, so
    publish race and ethnicity as separate demographic categories (they don't sum with each
    other), the standard NIBRS presentation.
12. **Dead/near-dead columns.** `clearance_ind` is 100% blank in every year;
    `age_range_high_num` is ≥97% blank/0; `age_range_low_num` duplicates `age_num`. Exclude
    all three.
13. **`sex_code` has no U** in any year (M/F only, 0 nulls). `age_num` min is 0 in era 2
    (infants as arrestees are almost certainly data-entry artifacts — a handful of rows;
    consider the under-10 counts during review, but preserve unless provably impossible).
14. **Weapon segments** are child tables (1+ rows per arrestee; 2024 Group B is 98%
    "Unarmed") — recommend `not_in_gold` for the first gold version to keep the grain simple.

## Gold Schema Classification

Gold is an **aggregate** of the record-level bronze: proposed grain
`year × county_fips × offense_code (or offense category) × demographic`, metric
`arrest_count`, with `detail_level ∈ {county, state}` (Group B and unmatched-ORI rows are
state-only).

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| data_year / DATA_YEAR | fact_key | year | int16; = filename year |
| incident_id → agency_id → ori | fact_key (derived) | county_fips | via `NIBRS_incident` + `agencies` + `ori_to_county` crosswalk; Group A only; NULL for state rows |
| offense_code (era 2) / OFFENSE_TYPE_ID (era 1, via lookup) | fact_categorical | offense_code | plus/or `offense_category` from `NIBRS_OFFENSE_TYPE.offense_category_name`; keep `offense_group` (A/B) explicit if both groups ship |
| arrest_type_id | fact_categorical | arrest_type | on_view / summoned_cited / taken_into_custody |
| sex_code, race_id, ethnicity_id, age_num | fact_key | demographic | FK to demographics dimension; race → split asian / pacific_islander; age → adult/juvenile (under-18) buckets; race and ethnicity are separate categories |
| (aggregation of rows) | fact_metric | arrest_count | count of arrestee segments, excluding `multiple_indicator == 'M'` |
| arrestee_id / groupb_arrestee_id / arrestee_seq_num | not_in_gold | — | row identifiers; used only for counting/dedup |
| arrest_date | not_in_gold | — | spills across calendar years for Group A (consideration #8) |
| multiple_indicator | not_in_gold | — | dedup filter only (consideration #7) |
| resident_code | not_in_gold | — | optional future categorical; high missingness (26–34%) |
| under_18_disposition_code | not_in_gold | — | meaningful only for juvenile rows; candidate for a future juvenile-justice topic |
| clearance_ind | not_in_gold | — | 100% blank every year |
| age_id, age_range_low_num, age_range_high_num | not_in_gold | — | redundant with age_num / near-empty |
| NIBRS_ARRESTEE_WEAPON / GROUPB_WEAPON segments | not_in_gold | — | child grain; 98% unarmed (Group B 2024); revisit if a weapons cut is wanted |
| lookups (ARREST_TYPE, REF_RACE, ETHNICITY, AGE, OFFENSE_TYPE, WEAPON_TYPE) | not_in_gold | — | transform-time recode sources; era-local (consideration #3) |
| agencies.csv attributes (names, population, agency_type_name) | dimension_attribute | — | stay in the ori_to_county crosswalk / agency reference; agency identifiers do not enter gold |
