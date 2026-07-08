# hate_crimes — Bronze Data Structure

## Overview

- Topic: hate_crimes
- Source: fbi_cde
- Files: 1 file — `hate_crime.zip`, the FBI CDE national hate-crime master CSV (kept unextracted; contains `hate_crime/hate_crime.csv`, ~68 MB, plus a methodology PDF). 265,834 incident rows nationally, **1,983 Georgia rows**, 1991–2024.
- Unreadable files: none (zip passes `python -m zipfile -t`; CSV parses cleanly with `null_values=["NULL"]`)
- Year representation: `data_year` column (integer calendar year, 1991–2024). `incident_date` is ISO `YYYY-MM-DD`; `year(incident_date) == data_year` on all 1,983 GA rows.
- Filename-to-data year offset: n/a — single national file with no year in the filename
- Detail levels: **incident** (one row per `incident_id`, globally unique) reported by **agency** (ORI). No aggregate/summary rows of any kind.
- Percentage scale: n/a — all metrics are integer counts
- Checksums generated: 2026-07-02

## Source Provenance

Full provenance (signed-URL mechanics, license) in [`_provenance.md`](_provenance.md), maintained by the scripted downloader.

- **Source URL**: FBI Crime Data Explorer "Documents & Downloads" (<https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/downloads>), "Hate Crime" additional dataset (national master file). Bulk-file URLs are signed and expire in ~15 min — always re-run the downloader, never reuse URLs.
- **Retrieved**: 2026-07-02, via `uv run python -m src.etl.criminal_justice.fbi_cde.download`
- **Method**: scripted fetch. License: US federal government work — public domain.

## File Checksums

Generated: 2026-07-02

| File | SHA-256 |
|------|---------|
| hate_crime.zip | 6d24e053b340e74e62d0fcf8b237ac470f5ccafc908ba661581f99c2daa9d189 |

Zip contents: `hate_crime/hate_crime.csv` (68,327,846 B, source-dated 2025-07-09) and `Hate_Crime_2024_Methodology.pdf` (453,465 B). Matches the hash recorded in `_provenance.md`.

## Summary

Incident-level FBI hate-crime records: each row is one bias-motivated criminal incident reported by a law-enforcement agency, with the **bias motivation** (`bias_desc` — Anti-Black, Anti-Jewish, Anti-Gay (Male), …), the **offense(s)** committed (Intimidation, Simple Assault, Vandalism, …), the **location type**, **victim counts** (total individuals, adult/juvenile splits where NIBRS-reported), **offender counts**, offender race/ethnicity, and victim entity types (Individual, Business, Government, …). The natural gold metric is **incident counts** (and victim/offender counts) aggregated to county × year × bias motivation.

## Eras

### Era 1: 1991–2024 (single era)

One national CSV with a uniform 28-column schema across all years. No column-name drift — era variation shows up as **column population** instead: the adult/juvenile victim/offender splits are only filled for NIBRS-submitted incidents (see ETL Considerations #5).

| Column | Type | Description |
|--------|------|-------------|
| incident_id | i64 | Unique incident identifier (globally unique — 265,834/265,834 nationally, 1,983/1,983 GA) |
| data_year | i64 | Calendar year of the incident, 1991–2024 |
| ori | str | Reporting agency ORI code (`GA…`, 9 chars); 224 distinct GA agencies |
| pug_agency_name | str | Agency name (sic — source misspelling of "pub"), e.g. `Atlanta`, `Cobb County Police Department`; 222 distinct GA values |
| pub_agency_unit | str | Agency sub-unit — **all null in GA** |
| agency_type_name | str | Agency type: City / County / Other / Other State Agency / University or College |
| state_abbr | str | State postal code — filter to `GA` |
| state_name | str | State name (constant `Georgia` after filter) |
| division_name | str | Census division (constant `South Atlantic` after filter) |
| region_name | str | Census region (constant `South` after filter) |
| population_group_code | str | UCR population-group code (`1B`–`9D`, 15 GA values) |
| population_group_description | str | Population-group label (e.g. `MSA counties 100,000 or over`) |
| incident_date | str | Incident date, ISO `YYYY-MM-DD`, never null, always consistent with `data_year` |
| adult_victim_count | i64 | Adult victims — NIBRS-only field, null on SRS-era rows (787/1,983 GA nulls) |
| juvenile_victim_count | i64 | Juvenile victims — NIBRS-only, same null pattern (787 nulls) |
| total_offender_count | i64 | Known offenders; **0 = offender unknown** (655 GA rows, all with offender_race Unknown/Not Specified) |
| adult_offender_count | i64 | Adult offenders — NIBRS-only (1,094 GA nulls; also null when offender count unknown) |
| juvenile_offender_count | i64 | Juvenile offenders — NIBRS-only (1,094 nulls) |
| offender_race | str | Offender race (single bucket, or `Multiple`/`Unknown`/`Not Specified`); never null |
| offender_ethnicity | str | Offender Hispanic/Latino ethnicity (or `Multiple`/`Unknown`/`Not Specified`); never null |
| victim_count | i64 | Count of victim *entities* by type — matches `len(victim_types.split(';'))` on 1,926/1,983 GA rows; **not** the individual-victim count |
| offense_name | str | Offense(s) — **semicolon-delimited multi-value** (47 GA rows multi) |
| total_individual_victims | i64 | Individual (human) victims; 0 when victims are only entities (Business/Government, 253 rows); 15 GA nulls |
| location_name | str | Location type(s) — semicolon-delimited multi-value (7 GA rows multi) |
| bias_desc | str | Bias motivation(s) — **semicolon-delimited multi-value** (15 GA rows multi) |
| victim_types | str | Victim entity type(s) — semicolon-delimited multi-value (21 GA rows multi) |
| multiple_offense | str | `M`/`S` flag — exactly tracks whether `offense_name` contains `;` (redundant) |
| multiple_bias | str | `M`/`S` flag — exactly tracks whether `bias_desc` contains `;` (redundant) |

#### Sample Data (GA rows)

| incident_id | data_year | ori | pug_agency_name | agency_type_name | incident_date | total_offender_count | offender_race | victim_count | offense_name | total_individual_victims | location_name | bias_desc | victim_types |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1467690 | 2022 | GA0200000 | Camden | County | 2022-05-07 | 1 | Black or African American | 1 | Simple Assault | 1 | Highway/Road/Alley/Street/Sidewalk | Anti-White | Law Enforcement Officer |
| 144691 | 2010 | GAAPD0000 | Atlanta | City | 2010-11-07 | 1 | Black or African American | 1 | Aggravated Assault | 2 | Restaurant | Anti-Gay (Male) | Individual |
| 1547665 | 2024 | GA0110000 | Bibb | County | 2024-07-03 | 2 | Multiple | 1 | Intimidation | 1 | Jail/Prison/Penitentiary/Corrections Facility | Anti-White | Individual |
| 1458630 | 2021 | GA0330200 | Cobb County Police Department | County | 2021-03-27 | 1 | White | 1 | Intimidation | 1 | Other/Unknown | Anti-Black or African American | Individual |
| 1511259 | 2021 | GA0190100 | Arlington | City | 2021-06-10 | 1 | Black or African American | 1 | Burglary/Breaking & Entering | 0 | Residence/Home | Anti-Black or African American | Other |

(Adult/juvenile split columns omitted above for width; see Statistics.)

#### Statistics (GA, n = 1,983)

| Column | non-null | mean | min | max |
|--------|---------:|-----:|----:|----:|
| data_year | 1,983 | 2012.7 | 1991 | 2024 |
| adult_victim_count | 1,196 | 0.82 | 0 | 10 |
| juvenile_victim_count | 1,196 | 0.12 | 0 | 6 |
| total_offender_count | 1,983 | 0.97 | 0 | 30 |
| adult_offender_count | 889 | 0.76 | 0 | 4 |
| juvenile_offender_count | 889 | 0.15 | 0 | 5 |
| victim_count | 1,983 | 1.02 | 0 | 3 |
| total_individual_victims | 1,968 | 1.10 | 0 | 100 |

The max `total_individual_victims` = 100 is a single 2017 Gwinnett County PD incident (Intimidation;Simple Assault, Anti-Islamic;Anti-Multiple Races) — extreme but conceivable (mass-victim intimidation incident); preserve and document, don't null.

#### Null Counts (GA)

| Column | Nulls |
|--------|------:|
| pub_agency_unit | 1,983 (all) |
| adult_victim_count / juvenile_victim_count | 787 |
| adult_offender_count / juvenile_offender_count | 1,094 |
| total_individual_victims | 15 |
| all other columns | 0 |

#### GA rows per year

| Years | Rows/yr | Reporting agencies/yr |
|-------|---------|----------------------|
| 1991–1997 | 23–75 | 2–4 |
| 1998–2012 | 11–39 | 4–11 |
| 2013–2018 | 27–57 | 4–11 |
| 2019 | 158 | 71 |
| 2020 | 231 | 82 |
| 2021 | 261 | 81 |
| 2022 | 191 | 63 |
| 2023 | 126 | 52 |
| 2024 | 85 | 45 |

The 2019 jump (11 → 71 agencies) and the 2022–2024 decline track **reporting participation**, not underlying incidence — see ETL Considerations #4.

#### Categorical Columns (GA distinct values)

| Column | Distinct Values |
|--------|----------------|
| agency_type_name | City, County, Other, Other State Agency, University or College |
| offender_race | American Indian or Alaska Native, Asian, Black or African American, Multiple, Not Specified, Unknown, White (7 values; **national file also has Native Hawaiian or Other Pacific Islander** — 8 values; GA simply has no NHPI-offender rows yet) |
| offender_ethnicity | Hispanic or Latino, Multiple, Not Hispanic or Latino, Not Specified, Unknown |
| multiple_offense / multiple_bias | M, S |
| population_group_code | 1B, 1C, 2, 3, 4, 5, 6, 7, 8B, 8C, 8D, 9A, 9B, 9C, 9D (15; descriptions map 1:1) |
| victim_types (atomic, split on `;`) | Business, Government, Individual, Law Enforcement Officer, Other, Religious Organization, Society/Public, Unknown |
| location_name | 42 raw distinct (incl. semicolon combos); atomic values are the standard NIBRS location vocabulary (Residence/Home, Highway/Road/…, Church/Synagogue/Temple/Mosque, School/College, …) |

**bias_desc — atomic values (split on `;`), GA counts:**

| Bias | n | | Bias | n |
|------|--:|-|------|--:|
| Anti-Black or African American | 713 | | Anti-Physical Disability | 10 |
| Anti-Gay (Male) | 314 | | Anti-Catholic | 10 |
| Anti-White | 305 | | Anti-Church of Jesus Christ | 9 |
| Anti-Hispanic or Latino | 107 | | Anti-Atheism/Agnosticism | 9 |
| Anti-Jewish | 89 | | Anti-Female | 9 |
| Anti-LGBT (Mixed Group) | 59 | | Anti-American Indian or Alaska Native | 8 |
| Anti-Other Race/Ethnicity/Ancestry | 52 | | Anti-Heterosexual | 5 |
| Anti-Lesbian (Female) | 48 | | Anti-Other Christian | 5 |
| Anti-Multiple Races, Group | 48 | | Anti-Male | 4 |
| Anti-Asian | 41 | | Anti-Arab | 3 |
| Anti-Gender Non-Conforming | 24 | | Anti-Bisexual | 3 |
| Anti-Sikh | 24 | | Anti-Buddhist | 3 |
| Anti-Other Religion | 21 | | Anti-Native Hawaiian or Other Pacific Islander | 1 |
| Anti-Islamic (Muslim) | 19 | | Anti-Eastern Orthodox (Russian, Greek, Other) | 1 |
| Anti-Mental Disability | 16 | | Anti-Protestant | 15 |
| Anti-Transgender | 14 | | Anti-Multiple Religions, Group | 10 |

GA has 32 atomic bias values; the national file has 35 (Anti-Hindu, Anti-Jehovah's Witness, Anti-Mormon-adjacent values appear elsewhere) — recode maps must cover the **national** vocabulary or fail loudly on unmapped values, since new GA values can appear on refresh.

**offense_name — atomic values (GA, top):** Intimidation (640), Simple Assault (498), Destruction/Damage/Vandalism of Property (425), Aggravated Assault (208), All Other Larceny (41), Burglary/Breaking & Entering (36), Robbery (33), plus a long tail of 27 more NIBRS offenses (Arson 14, Rape 3, Murder and Nonnegligent Manslaughter 2, …) and `Not Specified` (5). GA has 34 atomic offenses; national 51.

#### Suppression Markers

None. The CSV uses the literal string `NULL` for missing values (parse with `null_values=["NULL"]`); every numeric column is otherwise purely numeric. No FBI suppression — hate-crime counts are published unsuppressed.

## Asian / Pacific Islander check

`offender_race` uses post-1997 OMB buckets: `Asian` and `Native Hawaiian or Other Pacific Islander` are **separate** buckets nationally (GA has 0 NHPI rows, so only 7 of the 8 values appear in-state). There is no combined `Asian/Pacific Islander` bucket, so no split-vs-rollup conflict. Likewise `bias_desc` keeps `Anti-Asian` and `Anti-Native Hawaiian or Other Pacific Islander` separate. The math test doesn't apply (incident-level data, no cohort totals). If offender race is mapped to the demographics dimension, map `Asian` → `asian` (not the combined bucket) and NHPI → `pacific_islander`.

## ETL Considerations

1. **Read from the zip — do not extract into bronze.** `zipfile.ZipFile(...).open('hate_crime/hate_crime.csv')` + `pl.read_csv(..., infer_schema_length=None, null_values=["NULL"])`. Default schema inference fails at row ~10k (`NULL` in `total_individual_victims`).
2. **Filter to `state_abbr == "GA"`** (1,983 of 265,834 rows). After the filter, `state_abbr`, `state_name`, `division_name`, `region_name` are constants.
3. **ORI → county mapping (hard prerequisite, with judgment items).** The `ori_to_county` crosswalk (`data/bronze/_crosswalks/ori_to_county/cde_agency_by_state_abbr_ga.json`, 664 GA ORIs) covers 222 of the 224 GA hate-crime ORIs. Two gaps, 1 row each: `GA1080100` (Watkinsville PD → Oconee County) and `GA0331100` (Southern Polytechnic State University → Cobb County) — handle via explicit override, not silent drop. **16 ORIs carry comma-separated multi-county assignments covering 600 rows (30%)** — dominated by Atlanta PD `GAAPD0000` (`DEKALB, FULTON`, 541 rows). A county-attribution rule is required (e.g., primary/seat county: Atlanta PD → Fulton); whatever rule is chosen must be documented in the contract's limitations. This is a judgment item for review, not a silent default.
4. **Reporting coverage confounds trends.** Hate-crime reporting is voluntary; zero-report agencies are absent, not true zeros. GA participation exploded in 2019 (11 → 71 agencies, NIBRS transition) and has declined since 2021 (81 → 45 agencies in 2024). Year-over-year incident counts largely reflect reporting coverage. Pre-2019 county-level data is dominated by a handful of large agencies (often just Atlanta PD). This belongs in the contract `limitations` and should temper any per-county trend interpretation.
5. **NIBRS-only columns.** `adult_/juvenile_victim_count` and `adult_/juvenile_offender_count` are null for SRS-submitted incidents: all null 1991–2010, spotty 2011–2018 (whole years null or filled depending on submission format), mostly filled 2019+. `adult_offender_count` is additionally null when the offender is unknown. If kept as metrics, expect era-driven null patterns; consider dropping the splits and keeping only `total_individual_victims` + `total_offender_count`.
6. **`total_offender_count == 0` means unknown offenders** (655 rows; offender_race is Unknown/Not Specified on every one). Do not treat as "zero offenders" — either null it or document the semantics.
7. **`victim_count` is NOT individual victims** — it counts victim *entity types* (equals `len(victim_types)` split on 1,926/1,983 rows). The human-victim metric is `total_individual_victims` (0 = entity-only victims, e.g. vandalism of a business; 15 nulls). Recommend excluding `victim_count` from gold.
8. **Semicolon multi-value fields.** `offense_name` (47 GA rows), `bias_desc` (15), `location_name` (7), `victim_types` (21). Exploding on `;` double-counts incidents at an incident/county grain — either (a) keep the incident count grain and explode only into a separate bias grain where a row is an incident-bias pair (documenting that sums exceed incident totals), or (b) attribute each incident once (first-listed value). `multiple_offense`/`multiple_bias` flags are fully redundant with the semicolons (verified exact match) — drop them.
9. **Bias rollup recommended.** 32+ atomic bias values are too sparse for county-year serving (many n<10). The FBI's standard rollup — Race/Ethnicity/Ancestry, Religion, Sexual Orientation, Disability, Gender, Gender Identity — is the natural `fact_categorical`; keep the detailed bias as a second column or defer it.
10. **Extreme value to preserve:** the 2017 Gwinnett incident with `total_individual_victims = 100` (see Statistics) — conceivable, keep + document.
11. **`incident_date` is clean** (ISO, never null, always agrees with `data_year`) — month/date could support finer grains, but year is the standard serving grain.
12. **`pug_agency_name`** is the source's own misspelling ("pub") — keep the mapping explicit in code comments to avoid a "typo fix" breaking the read.
13. **2024 is likely still filling in** (85 rows, 45 agencies vs 261/81 in 2021); the CDE re-publishes the master file with late submissions. Re-download refreshes all years — checksums will change wholesale.

## Gold Schema Classification

Bronze is incident-level; the expected gold shape is an aggregate (county × year × bias category) fact, so most bronze columns feed aggregation rather than landing in gold directly.

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| data_year | fact_key | year | Calendar year |
| ori | fact_key | county_fips | Via `ori_to_county` crosswalk (+ 2 overrides, multi-county rule — ETL #3); ORI itself not served |
| bias_desc | fact_categorical | bias_category (+ optionally bias_motivation) | Roll up to the 6 FBI bias categories (ETL #9); multi-value handling per ETL #8 |
| offense_name | fact_categorical | offense_category (optional) | Consider crime-against rollup (person/property/society) or top-N; multi-value per ETL #8 |
| incident_id | fact_metric (via count) | incident_count | `count(distinct incident_id)` is the natural key metric |
| total_individual_victims | fact_metric | victim_count | Sum; unit: count; 15 nulls pass through |
| total_offender_count | fact_metric | offender_count | Sum of **known** offenders; 0 = unknown (ETL #6) — document or null-before-sum |
| adult/juvenile_victim_count | not_in_gold | — | NIBRS-era-only nulls make aggregates misleading (ETL #5) |
| adult/juvenile_offender_count | not_in_gold | — | Same |
| victim_count | not_in_gold | — | Entity-type count, misleading semantics (ETL #7) |
| victim_types | not_in_gold | — | Optional future categorical; sparse multi-value |
| location_name | not_in_gold | — | Optional future categorical (42 values); defer |
| offender_race / offender_ethnicity | not_in_gold | — | Offender demographic ≠ demographics-dimension semantics (victim/target datasets use it); revisit only with a clear use case |
| pug_agency_name | dimension_attribute | — | Agency name lives with the crosswalk, not the fact |
| agency_type_name | not_in_gold | — | Lost at county grain |
| pub_agency_unit | not_in_gold | — | All null in GA |
| state_abbr / state_name / division_name / region_name | not_in_gold | — | Filter + constants after GA filter |
| population_group_code / _description | not_in_gold | — | Agency-size UCR classification; irrelevant at county grain |
| incident_date | not_in_gold | — | Year retained via data_year (ETL #11) |
| multiple_offense / multiple_bias | not_in_gold | — | Redundant with semicolons (verified) |
