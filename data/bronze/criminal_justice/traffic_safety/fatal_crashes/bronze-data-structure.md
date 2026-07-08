# fatal_crashes — Bronze Data Structure

## Overview

- Topic: fatal_crashes
- Source: traffic_safety (NHTSA FARS — Fatality Analysis Reporting System)
- Files: 50 zip files spanning 1975–2024 (one national zip per year; each zip contains 3–33 CSV tables)
- Unreadable files: none (all 50 zips pass CRC; every `accident.csv` parses with polars)
- Year representation: `YEAR` column in the accident table — **2-digit (75–97) for 1975–1997, 4-digit for 1998–2024**; also encoded in the filename (`FARS{year}NationalCSV.zip`)
- Filename-to-data year offset: **same** (verified for all 50 files: the `YEAR` column matches the filename year)
- Detail levels: **crash-level records** (one row per fatal crash) with state/county/city codes + lat/long (1999+); gold target is county-year aggregation
- Percentage scale: N/A — no percentage columns; all values are counts, codes, or coordinates
- Checksums generated: 2026-07-02

## Source Provenance

- **Source URL**: `https://static.nhtsa.gov/nhtsa/downloads/FARS/{year}/National/FARS{year}NationalCSV.zip`
  (program page: <https://www.nhtsa.gov/research-data/fatality-analysis-reporting-system-fars>)
- **Retrieved**: 2026-07-02 (UTC)
- **Method**: scripted fetch — `uv run python -m src.etl.criminal_justice.traffic_safety.fatal_crashes.download`
  (discovers years via anonymous S3 listing, verifies byte sizes, idempotent). Full details in
  [`_provenance.md`](_provenance.md). **Zips are never extracted** — the transform must read members
  directly from the zips.
- **License**: US federal government work — public domain (17 U.S.C. §105). Cite NHTSA FARS.

## File Checksums

Generated: 2026-07-02

| File | SHA-256 |
|------|---------|
| FARS1975NationalCSV.zip | a3bce899281a87dc628cd7cc8c43477f2d450a1864f1a69145120a609cb67970 |
| FARS1976NationalCSV.zip | 13ef599abf741f23a2df5568aea0a5643f8af9ed3a9bea37fbf90bb37edf2b68 |
| FARS1977NationalCSV.zip | cc8a4b9841a8d082c9fef0b0ae5e8cb08cb583495d600055de5f11c3dc4d85a0 |
| FARS1978NationalCSV.zip | 00f70b64dfda5b9d7d4c9bb238d9daa1798bdb8fb04c4fa5c9b6f6a8b54e6b89 |
| FARS1979NationalCSV.zip | 29343ba286e45fad053d78d29449b62a2beb0926d01e676669dfa1a427009842 |
| FARS1980NationalCSV.zip | 39f9906b4b317e79e17380d1a0ace6f2901e636c3ee7374246c7553304466c59 |
| FARS1981NationalCSV.zip | a2067410ef1707226aae4c52c89b194809ff5971b4ca0808f8382405cfa6d3e5 |
| FARS1982NationalCSV.zip | 4352379bf6af52f710ba53a5af440eff1d09d079e39499da4e6bcec917e103f3 |
| FARS1983NationalCSV.zip | c8ad18fe6351aa5f25c25c70964c4aaaea0e3352d0f0e4ef56ed886045f11532 |
| FARS1984NationalCSV.zip | b1ac5f6f64e614e231c87f4ceeaaba9c8ac845a8d75dd91a1f29dad31238c149 |
| FARS1985NationalCSV.zip | 72d369219717b1a784bc2d98f4b1bd6d6d19e33c48342766d99d7ac5c0f0bf33 |
| FARS1986NationalCSV.zip | d8dfb4f7e13d4f1b2e797914630672d7356a3d995261160b9171f99aafca3355 |
| FARS1987NationalCSV.zip | ec0fe50ad613c45a3667ceca907cb62a5abad29de310571c09d0e3598b2aa5f3 |
| FARS1988NationalCSV.zip | eba5d32af2e42fc74251900092e65f55b192a6eb115dabd2983630106f23568c |
| FARS1989NationalCSV.zip | 1cc82582c6c767d9b629f951432d57d189d60e5ec58852e2d66a446ef2f2093f |
| FARS1990NationalCSV.zip | 6de62eeb303f4dca1c2c9f3f7e5132b4bd93df7b7e6678f499c8a32cc15c4d2e |
| FARS1991NationalCSV.zip | 6be22cf2b3703c8d6fe50d57a77598173d3ff0fff1038ada9d56e6dc227c37f2 |
| FARS1992NationalCSV.zip | 4f4c5df90618ead0bbb8cc3810d008de2f9db50e481d421d285426bdee8bb13c |
| FARS1993NationalCSV.zip | eec8a1a3cd57464afd9178df22c3f2d23d89e6bddf06c8c5c61c78f8e435c7b2 |
| FARS1994NationalCSV.zip | 5838143735aeee3bf621c80ce74d4bf892259a9cb9678b40f91711af885f1b1b |
| FARS1995NationalCSV.zip | 1cc4559cfef24bbb97eecaeb5efa5bc6e500c158888482fc9da2cef106556f41 |
| FARS1996NationalCSV.zip | 9a89ff803f8d0f38427e8621db507f8e455e98dc6b3472fd3fbbb1307ae3843e |
| FARS1997NationalCSV.zip | 7d68eb7effe7f63155db1554aa52f1610f29278d64ef235b25f680054c03b452 |
| FARS1998NationalCSV.zip | 605c495dc16fe5fbb9d928dcb5b0c02d11d5ef8688d259befc601c73e17a2d82 |
| FARS1999NationalCSV.zip | 879c5966da662ee99a236d6a00b0b2e6657d52ed09a7f87e75fbc90af4499cf1 |
| FARS2000NationalCSV.zip | daf5cd5a883118c44a0b197ea706f8381c67e6286a35d644476fa428346d67f3 |
| FARS2001NationalCSV.zip | c9941820b5badf68ef70bc84e33d4ab810ac21f705b34ec599b88286d648dd61 |
| FARS2002NationalCSV.zip | 93ff09c7c36d703b39bd76c1cabe4a2b3afaa56e0d964ce4fdbb25362b388b16 |
| FARS2003NationalCSV.zip | 8938be605548310a0acc6362feb4a1d7f4a00434e2812bdeae788b9b55be8836 |
| FARS2004NationalCSV.zip | 04ac171a224b246de273f985827342ea4d3f56caffcaf66d3e0dcc0166f33b5b |
| FARS2005NationalCSV.zip | 3eba25e830d0a522faf6a334a43e9eb2c4822e8a54670d92e8fa729b5ecdfb71 |
| FARS2006NationalCSV.zip | b11b5347c3a19abbc48ae205da252c14b0e56c21360c22fbd8eeb8bc0f670be3 |
| FARS2007NationalCSV.zip | 22bdfc00dd6720b01aaa976d60ceb2372c4af62b49860bbc6fd95341585dc020 |
| FARS2008NationalCSV.zip | 4106f0cd8f5fdaf20e8063263e50b7f5f4373ede1ba3962ae22b4f92e7812fcc |
| FARS2009NationalCSV.zip | eaa349e8107f79856340c65036b3ef665f5aa01faa18b6b429a7953a245a58cf |
| FARS2010NationalCSV.zip | 4f86c198d48c4cc26e836b63fa9029b74980a5a436d85c5e26474ff51c613312 |
| FARS2011NationalCSV.zip | 7c73e6e20e1ff3f174362688a7255ead541f315066c85c0bea6d4549d5d0befb |
| FARS2012NationalCSV.zip | ff6f575de1a6157b1911188e1346f899f000860e4449b64fa3e81d44da11a702 |
| FARS2013NationalCSV.zip | 9c34182ff203b2dfc09afd1c8a54133ddac000ec16eee70cd7b810aa5e998b65 |
| FARS2014NationalCSV.zip | 9789f29ee8d23b1d3a1f474d54f76fee51a9238fd90e19c71beb82636b472380 |
| FARS2015NationalCSV.zip | 45f3aa0f03723c4d74c5f4b084530dd458c50354bcc5f9a8d165d36e24b12209 |
| FARS2016NationalCSV.zip | 44a452a25cb064bf680d4851ff3ad63d7e2d13704a58a1b287b4e02a7cebff0f |
| FARS2017NationalCSV.zip | 1a886757b7bf611c883cc9039e0f3cf1915142dcb0e31fcbaa14c96aab2385c4 |
| FARS2018NationalCSV.zip | bd0c5473e3f0eaf44c3236000225e5ca90070884684d1b69036062b2ddbdaf2e |
| FARS2019NationalCSV.zip | 0974abb92cfb04fa022631a838a3f46555025f2b011ee78ecad15bcf86c60f31 |
| FARS2020NationalCSV.zip | b2806902b3da9b45c632499f82e1c74fd108238ae7f67e108ebf40360ee4c9c3 |
| FARS2021NationalCSV.zip | 743c19a13884614430d295289e655c5ad32b0a025a11e5b2149dfb57acae389b |
| FARS2022NationalCSV.zip | 989448d7a2f3964264c96a3cdb220f6c413c782a33eb759781f520c5acb5f744 |
| FARS2023NationalCSV.zip | edde841eb493e55751961b36bac2d1ce8750f601cb8e6e183a525723bb62bab0 |
| FARS2024NationalCSV.zip | 5112727a8c0dc91ffee27ca05bddb073934f2d192ce4fae997da767dccdbe04f |

## Zip / Table Structure

Not Excel — each annual zip bundles multiple CSV tables. The roster and in-zip layout vary by year:

| Year range | Layout | Tables |
|------------|--------|--------|
| 1975–1981 | UPPERCASE at zip root | `ACCIDENT.CSV`, `VEHICLE.CSV`, `PERSON.CSV` (3 tables; **no MI-BAC files**) |
| 1982–2005 | UPPERCASE at zip root | + `MIACC.CSV`, `MIDRVACC.CSV`, `MIPER.CSV` (multiply-imputed BAC); 2005 adds `VEHNIT.CSV` |
| 2006–2014 | Mixed case, root or `FARS{year}NationalCSV/` subfolder | ~20+ tables (adds Damage, Distract, DrImpair, Factor, Maneuver, NMCrash, PBType, SafetyEq, VEvent, Violatn, Vision, VSOE, VINDecode…) |
| 2015–2024 | `FARS{year}NationalCSV/` subfolder, mostly lowercase (MI files stay UPPERCASE) | 24–33 tables (adds race, weather, drugs, crashrf/driverrf/personrf, vpicdecode…) |

**The transform must match members case-insensitively by basename** (e.g. `accident.csv` matches
`ACCIDENT.CSV`, `FARS2024NationalCSV/accident.csv`). Only the **accident table** is needed for the
county-year gold; person/vehicle/MI tables join on `ST_CASE` (+ `VEH_NO`, `PER_NO`) if ever needed.

## Summary

FARS is NHTSA's **census of fatal motor-vehicle traffic crashes** (every crash with ≥1 death within
30 days), 1975–2024. Each accident-table row is one fatal crash with: **`FATALS`** (deaths in the
crash), vehicle/person involvement counts (`VE_FORMS`/`VE_TOTAL`, `PERSONS`/`PERMVIT`, `PEDS`),
**`DRUNK_DR`** (number of drinking drivers, 1975–2020 only), county/city location, date/time, and
crash-characteristic codes (light condition, weather, manner of collision, first harmful event,
rural/urban). The headline user metrics are **traffic fatalities and fatal-crash counts per county
per year**, with derivable sub-metrics (crashes involving a drinking driver, crashes involving
pedestrians/non-motorists, vehicles involved). Georgia has ~1,100–1,700 fatal crashes and
~1,200–1,800 deaths per year (2024: 1,312 crashes / 1,403 deaths — cross-checked against the person
file's fatal-injury rows, exact match).

## Eras

Grouping by **exact** accident-table column sets yields 17 raw eras; they collapse into 5 analytic
eras. Raw era boundaries (column count in parentheses):

| Exact era | Cols | Changes vs previous |
|-----------|------|---------------------|
| 1975–1981 | 45 | baseline (incl. `VEHICLES`, `CL_TWAY`, `TA_1_CL`, `LAND_USE`; `ROAD_FNC` present but **all NULL in 1975**) |
| 1982–1986 | 47 | −`VEHICLES`,`TA_1_CL`,`ROAD_FLO`; +`FED_AID`,`T_CONT_F`,`TWAY_FLO`,`MILEPT`,`TWAY_ID` |
| 1987–1990 | 48 | −`LAND_USE`,`CL_TWAY`,`TWAY_FLO`; +`ROUTE`,`TRAF_FLO`,`HOSP_HR`,`HOSP_MN` |
| 1991–1993 | 49 | +`PEDS` |
| 1994–1998 | 49 | `FED_AID`→`NHS` |
| 1999–2003 | 51 | +`LATITUDE`,`LONGITUD` (mostly 8888…-filled until ~2001) |
| 2004 | 52 | +`TWAY_ID2` |
| 2005–2006 | 53 | +`VE_TOTAL` (`VE_FORMS` redefined to in-transport vehicles only) |
| 2007–2008 | 55 | +`WEATHER1`,`WEATHER2` (alongside `WEATHER`) |
| 2009 | 54 | `HIT_RUN` dropped (moves to vehicle file); +`WRK_ZONE` |
| 2010 | 47 | element redesign: −`NO_LANES`,`SP_LIMIT`,`ALIGNMNT`,`PROFILE`,`PAVE_TYP`,`SUR_COND`,`TRA_CONT`,`T_CONT_F`,`REL_JUNC`; +`RELJCT1`,`RELJCT2`,`TYP_INT` |
| 2011–2014 | 50 | +`PVH_INVL`,`PERNOTMVIT`,`PERMVIT` |
| 2015 | 89 | −`ROAD_FNC`, +`RUR_URB`,`FUNC_SYS`,`RD_OWNER`; adds a `…NAME` label twin for most code columns |
| 2016–2019 | 91 | +`COUNTYNAME`,`CITYNAME` |
| 2020 | 81 | −`CF1–CF3`(+NAMEs), −`WEATHER1/2`(+NAMEs) — back to single `WEATHER` |
| 2021–2022 | 80 | **−`DRUNK_DR`** (dropped permanently); files carry a **UTF-8 BOM** on the header |
| 2023–2024 | 80 | same columns as 2021–2022, no BOM |

The columns needed for county-year gold are stable across all 50 years: `STATE`, `COUNTY`, `YEAR`,
`MONTH`, `ST_CASE`, `FATALS` (all years); `DRUNK_DR` (1975–2020); `PEDS` (1991+);
`VE_FORMS`/`VE_TOTAL` (see ETL notes).

Detailed analysis below uses Georgia rows only (`STATE = 13`), representative year per analytic era.

### Era A: 1975–1981 (representative: 1975 — 1,170 GA rows, 1,360 GA fatalities)

| Column | Description |
|--------|-------------|
| STATE | State FIPS (13 = Georgia) |
| ST_CASE | Case number, unique **within year only** (GA range ~130001–13xxxx) |
| COUNTY | GSA county code — for GA equals the 3-digit county FIPS suffix (see ETL) |
| CITY | GSA city code (0 = not in a city) |
| YEAR / MONTH / DAY / DAY_WEEK / HOUR / MINUTE | Crash date/time; YEAR is 2-digit (75); HOUR 99 = unknown (also 24 = midnight in early years) |
| VE_FORMS | Vehicles involved (all vehicles in this era) |
| PERSONS | Persons involved (person forms submitted) |
| FATALS | **Deaths in the crash (1–7 observed)** |
| DRUNK_DR | Number of drinking drivers (0–2 observed) |
| LGT_COND / WEATHER / MAN_COLL / HARM_EV / LAND_USE / SP_LIMIT etc. | Crash-attribute codes (code lists change across eras) |
| CF1–CF3, NOT_/ARR_ hours, SCH_BUS, RAIL, HIT_RUN … | Contributing factors / timeline / flags — not needed for gold |

Sample (5 GA rows, core columns):

```text
│ ST_CASE ┆ COUNTY ┆ CITY ┆ MONTH ┆ DAY ┆ DAY_WEEK ┆ HOUR ┆ VE_FORMS ┆ PERSONS ┆ FATALS ┆ DRUNK_DR ┆ LGT_COND ┆ WEATHER ┆ MAN_COLL ┆ HARM_EV ┆ LAND_USE ┆ SP_LIMIT │
│ 130950  ┆ 45     ┆ 0    ┆ 10    ┆ 29  ┆ 4        ┆ 17   ┆ 1        ┆ 2       ┆ 1      ┆ 0        ┆ 1        ┆ 1       ┆ 0        ┆ 8       ┆ 2        ┆ 55       │
│ 130373  ┆ 25     ┆ 2750 ┆ 5     ┆ 3   ┆ 7        ┆ 21   ┆ 1        ┆ 1       ┆ 1      ┆ 0        ┆ 2        ┆ 1       ┆ 0        ┆ 27      ┆ 2        ┆ 45       │
│ 131150  ┆ 5      ┆ 0    ┆ 12    ┆ 29  ┆ 2        ┆ 17   ┆ 2        ┆ 2       ┆ 1      ┆ 0        ┆ 6        ┆ 2       ┆ 4        ┆ 12      ┆ 2        ┆ 55       │
│ 130820  ┆ 21     ┆ 0    ┆ 9     ┆ 12  ┆ 6        ┆ 7    ┆ 1        ┆ 2       ┆ 1      ┆ 0        ┆ 1        ┆ 1       ┆ 0        ┆ 8       ┆ 2        ┆ 55       │
│ 130929  ┆ 193    ┆ 0    ┆ 10    ┆ 17  ┆ 6        ┆ 22   ┆ 1        ┆ 1       ┆ 1      ┆ 0        ┆ 2        ┆ 1       ┆ 0        ┆ 1       ┆ 2        ┆ 55       │
```

Key statistics (GA, 1975): FATALS mean 1.16, max 7; PERSONS max 37; VE_FORMS max 4; DRUNK_DR values
{0,1,2}. Nulls: **zero in every core column** except `ROAD_FNC` (100% null in 1975 only — reads as
a string column of empty values). COUNTY: 150 distinct codes, all odd 1–321 except one `999`
(unknown) row.

### Era B: 1982–1998 (representatives: 1985 — 1,223 rows / 1,361 fatalities; 1994 — 1,281 rows / 1,425 fatalities)

Same core columns; adds MI-BAC companion files (1982+), `PEDS` (1991+), `ROAD_FNC` now populated.
Nulls: zero in all core columns. Distinct codes (1994): DAY_WEEK 1–7, LGT_COND 1–5+9, WEATHER
1–6+9, DRUNK_DR {0,1,2}, FATALS 1–6, HOUR 0–24+99, ROAD_FNC {1–6, 11–16, 99}.

Sample (5 GA rows, 1994):

```text
│ ST_CASE ┆ COUNTY ┆ CITY ┆ MONTH ┆ DAY ┆ DAY_WEEK ┆ HOUR ┆ VE_FORMS ┆ PERSONS ┆ PEDS ┆ FATALS ┆ DRUNK_DR ┆ LGT_COND ┆ WEATHER ┆ MAN_COLL ┆ HARM_EV ┆ ROAD_FNC ┆ SP_LIMIT │
│ 131050  ┆ 141    ┆ 0    ┆ 7     ┆ 14  ┆ 5        ┆ 16   ┆ 1        ┆ 1       ┆ 0    ┆ 1      ┆ 0        ┆ 1        ┆ 9       ┆ 0        ┆ 99      ┆ 99       ┆ 99       │
│ 130413  ┆ 135    ┆ 0    ┆ 5     ┆ 22  ┆ 1        ┆ 2    ┆ 1        ┆ 3       ┆ 0    ┆ 1      ┆ 1        ┆ 2        ┆ 5       ┆ 0        ┆ 1       ┆ 16       ┆ 35       │
│ 131271  ┆ 121    ┆ 280  ┆ 5     ┆ 31  ┆ 3        ┆ 5    ┆ 1        ┆ 2       ┆ 1    ┆ 1      ┆ 0        ┆ 3        ┆ 9       ┆ 0        ┆ 8       ┆ 11       ┆ 50       │
│ 130908  ┆ 59     ┆ 270  ┆ 8     ┆ 11  ┆ 5        ┆ 18   ┆ 1        ┆ 2       ┆ 1    ┆ 1      ┆ 0        ┆ 1        ┆ 1       ┆ 0        ┆ 8       ┆ 16       ┆ 30       │
│ 131027  ┆ 55     ┆ 0    ┆ 11    ┆ 14  ┆ 2        ┆ 19   ┆ 1        ┆ 2       ┆ 1    ┆ 1      ┆ 0        ┆ 2        ┆ 1       ┆ 0        ┆ 8       ┆ 12       ┆ 35       │
```

**County-code anomalies cluster here**: scattered invalid GSA codes (even numbers, 0, >321) appear
1986–1994, 1–10 rows/year (peak: 1991 with 10 rows incl. codes 20, 28, 80, 90, 130, 190, 296, 471,
950). 1976–1981 also have code 510/520/507 rows (2–27/year). See ETL Considerations.

### Era C: 1999–2009 (representatives: 2000 — 1,380 rows / 1,541 fatalities; 2007 — 1,492 rows / 1,641 fatalities)

Adds `LATITUDE`/`LONGITUD`. In 2000 these are integer sentinel-heavy (88888888/888888888 = not
reported); by 2007 they are proper decimal degrees with **98 nulls of 1,492 GA rows** (only null
core columns in the whole dataset besides 1975 ROAD_FNC). 2005+ adds `VE_TOTAL` (all vehicles;
`VE_FORMS` becomes in-transport only). 2007–2009 have `WEATHER1`/`WEATHER2` alongside `WEATHER`.
`YEAR` is 4-digit from 1998 on. DRUNK_DR shows values {0–4} in 2000. FATALS 1–7.

Sample (5 GA rows, 2007):

```text
│ ST_CASE ┆ COUNTY ┆ CITY ┆ MONTH ┆ DAY ┆ DAY_WEEK ┆ HOUR ┆ VE_FORMS ┆ VE_TOTAL ┆ PERSONS ┆ PEDS ┆ FATALS ┆ DRUNK_DR ┆ LGT_COND ┆ WEATHER ┆ MAN_COLL ┆ HARM_EV ┆ ROAD_FNC ┆ LATITUDE  ┆ LONGITUD   ┆ SP_LIMIT │
│ 131214  ┆ 137    ┆ 0    ┆ 9     ┆ 27  ┆ 5        ┆ 10   ┆ 2        ┆ 2        ┆ 2       ┆ 0    ┆ 1      ┆ 0        ┆ 1        ┆ 1       ┆ 5        ┆ 12      ┆ 4        ┆ 34.583325 ┆ -83.548219 ┆ 35       │
│ 130475  ┆ 15     ┆ 0    ┆ 5     ┆ 20  ┆ 1        ┆ 3    ┆ 1        ┆ 1        ┆ 1       ┆ 0    ┆ 1      ┆ 0        ┆ 2        ┆ 1       ┆ 0        ┆ 53      ┆ 14       ┆ 34.144333 ┆ -84.879306 ┆ 45       │
│ 131470  ┆ 231    ┆ 0    ┆ 3     ┆ 16  ┆ 6        ┆ 5    ┆ 1        ┆ 1        ┆ 2       ┆ 0    ┆ 1      ┆ 1        ┆ 2        ┆ 1       ┆ 0        ┆ 32      ┆ 3        ┆ 32.994817 ┆ -84.50615  ┆ 55       │
│ 131047  ┆ 143    ┆ 0    ┆ 9     ┆ 30  ┆ 1        ┆ 10   ┆ 2        ┆ 3        ┆ 3       ┆ 0    ┆ 1      ┆ 0        ┆ 1        ┆ 1       ┆ 5        ┆ 12      ┆ 4        ┆ 33.671858 ┆ -85.263419 ┆ 55       │
│ 131186  ┆ 137    ┆ 0    ┆ 11    ┆ 10  ┆ 7        ┆ 10   ┆ 2        ┆ 2        ┆ 3       ┆ 0    ┆ 1      ┆ 0        ┆ 1        ┆ 1       ┆ 3        ┆ 12      ┆ 3        ┆ 34.5521   ┆ -83.571456 ┆ 55       │
```

### Era D: 2010–2014 (representative: 2012 — 1,126 rows / 1,192 fatalities)

FARS element redesign: roadway-detail columns (SP_LIMIT, SUR_COND, ALIGNMNT…) move to the vehicle
file; adds `PERMVIT`/`PERNOTMVIT`/`PVH_INVL`. Core metrics unchanged. Nulls: zero across core
columns. Distinct codes (2012): WEATHER now {1,2,3,5,8,10,98} (code list revised — 10 = cloudy,
98 = not reported), DRUNK_DR {0,1,2}, FATALS 1–3. Lat/long fully populated (sentinel 99.9999 /
999.9999 for unknown, 22 such rows).

Sample (5 GA rows, 2012):

```text
│ ST_CASE ┆ COUNTY ┆ CITY ┆ MONTH ┆ DAY ┆ DAY_WEEK ┆ HOUR ┆ VE_FORMS ┆ VE_TOTAL ┆ PERSONS ┆ PERMVIT ┆ PEDS ┆ FATALS ┆ DRUNK_DR ┆ LGT_COND ┆ WEATHER ┆ MAN_COLL ┆ HARM_EV ┆ ROAD_FNC ┆ LATITUDE  ┆ LONGITUD   │
│ 130919  ┆ 33     ┆ 0    ┆ 10    ┆ 31  ┆ 4        ┆ 4    ┆ 1        ┆ 1        ┆ 1       ┆ 1       ┆ 0    ┆ 1      ┆ 0        ┆ 2        ┆ 1       ┆ 0        ┆ 42      ┆ 4        ┆ 33.063419 ┆ -82.088375 │
│ 130360  ┆ 217    ┆ 0    ┆ 4     ┆ 28  ┆ 7        ┆ 0    ┆ 1        ┆ 1        ┆ 2       ┆ 2       ┆ 0    ┆ 1      ┆ 1        ┆ 2        ┆ 1       ┆ 0        ┆ 31      ┆ 6        ┆ 33.481597 ┆ -83.915186 │
│ 131112  ┆ 77     ┆ 3950 ┆ 12    ┆ 22  ┆ 7        ┆ 20   ┆ 2        ┆ 2        ┆ 7       ┆ 7       ┆ 0    ┆ 1      ┆ 0        ┆ 2        ┆ 1       ┆ 6        ┆ 12      ┆ 14       ┆ 33.373533 ┆ -84.763    │
│ 130794  ┆ 133    ┆ 0    ┆ 9     ┆ 21  ┆ 6        ┆ 15   ┆ 3        ┆ 3        ┆ 5       ┆ 5       ┆ 0    ┆ 1      ┆ 0        ┆ 1        ┆ 1       ┆ 2        ┆ 12      ┆ 3        ┆ 33.522056 ┆ -83.222314 │
│ 130899  ┆ 77     ┆ 0    ┆ 10    ┆ 24  ┆ 4        ┆ 20   ┆ 1        ┆ 1        ┆ 1       ┆ 1       ┆ 0    ┆ 1      ┆ 1        ┆ 2        ┆ 1       ┆ 0        ┆ 42      ┆ 6        ┆ 33.307883 ┆ -84.712683 │
```

### Era E: 2015–2024 (representatives: 2018 — 1,408 rows / 1,505 fatalities; 2021 — 1,681 / 1,809; 2024 — 1,312 / 1,403)

Adds a human-readable `…NAME` twin for most code columns (incl. `COUNTYNAME` from 2016 — used to
verify the county-code→FIPS mapping, see ETL), replaces `ROAD_FNC` with **`RUR_URB`** (1 = rural,
2 = urban; 6 = unknown appears in 2024) + `FUNC_SYS`. **`DRUNK_DR` exists through 2020 and is gone
from 2021 onward.** Nulls: zero across core columns (unknown lat/long uses sentinels 99.9999 /
999.9999). GA county codes: 146–155 distinct per year, all odd 1–321, no invalid codes 1995+
(except isolated 0/999 rows in 2001–2006, 1 row/year).

Sample (5 GA rows, 2024):

```text
│ ST_CASE ┆ COUNTY ┆ CITY ┆ MONTH ┆ DAY ┆ DAY_WEEK ┆ HOUR ┆ VE_FORMS ┆ VE_TOTAL ┆ PERSONS ┆ PERMVIT ┆ PEDS ┆ FATALS ┆ LGT_COND ┆ WEATHER ┆ MAN_COLL ┆ HARM_EV ┆ RUR_URB ┆ FUNC_SYS ┆ LATITUDE  ┆ LONGITUD   │
│ 131105  ┆ 121    ┆ 280  ┆ 3     ┆ 8   ┆ 6        ┆ 2    ┆ 1        ┆ 1        ┆ 1       ┆ 1       ┆ 0    ┆ 1      ┆ 3        ┆ 1       ┆ 0        ┆ 31      ┆ 2       ┆ 3        ┆ 33.840197 ┆ -84.378389 │
│ 130428  ┆ 95     ┆ 90   ┆ 5     ┆ 9   ┆ 5        ┆ 3    ┆ 1        ┆ 1        ┆ 1       ┆ 1       ┆ 0    ┆ 1      ┆ 3        ┆ 10      ┆ 0        ┆ 59      ┆ 2       ┆ 5        ┆ 31.603339 ┆ -84.119047 │
│ 131351  ┆ 81     ┆ 1340 ┆ 12    ┆ 18  ┆ 4        ┆ 5    ┆ 2        ┆ 2        ┆ 2       ┆ 2       ┆ 0    ┆ 1      ┆ 2        ┆ 5       ┆ 1        ┆ 12      ┆ 1       ┆ 1        ┆ 31.909672 ┆ -83.738919 │
│ 130957  ┆ 33     ┆ 5860 ┆ 9     ┆ 28  ┆ 7        ┆ 19   ┆ 2        ┆ 2        ┆ 3       ┆ 3       ┆ 0    ┆ 1      ┆ 5        ┆ 1       ┆ 6        ┆ 12      ┆ 2       ┆ 3        ┆ 33.100578 ┆ -81.997961 │
│ 131081  ┆ 39     ┆ 4850 ┆ 10    ┆ 30  ┆ 4        ┆ 19   ┆ 2        ┆ 2        ┆ 2       ┆ 2       ┆ 0    ┆ 1      ┆ 2        ┆ 1       ┆ 0        ┆ 33      ┆ 2       ┆ 4        ┆ 30.769653 ┆ -81.579489 │
```

### GA rows and fatalities per year (full sweep, accident table)

| Year | Crashes | Fatalities | | Year | Crashes | Fatalities | | Year | Crashes | Fatalities |
|------|---------|-----------|-|------|---------|-----------|-|------|---------|-----------|
| 1975 | 1170 | 1360 | | 1992 | 1184 | 1315 | | 2009 | 1180 | 1292 |
| 1976 | 1119 | 1264 | | 1993 | 1247 | 1394 | | 2010 | 1150 | 1247 |
| 1977 | 1188 | 1372 | | 1994 | 1281 | 1425 | | 2011 | 1119 | 1226 |
| 1978 | 1290 | 1472 | | 1995 | 1333 | 1488 | | 2012 | 1126 | 1192 |
| 1979 | 1331 | 1524 | | 1996 | 1402 | 1573 | | 2013 | 1085 | 1180 |
| 1980 | 1348 | 1508 | | 1997 | 1405 | 1577 | | 2014 | 1080 | 1164 |
| 1981 | 1256 | 1418 | | 1998 | 1414 | 1568 | | 2015 | 1329 | 1432 |
| 1982 | 1097 | 1229 | | 1999 | 1314 | 1508 | | 2016 | 1424 | 1556 |
| 1983 | 1157 | 1296 | | 2000 | 1380 | 1541 | | 2017 | 1440 | 1540 |
| 1984 | 1260 | 1410 | | 2001 | 1471 | 1647 | | 2018 | 1408 | 1505 |
| 1985 | 1223 | 1361 | | 2002 | 1362 | 1524 | | 2019 | 1378 | 1492 |
| 1986 | 1378 | 1530 | | 2003 | 1463 | 1603 | | 2020 | 1517 | 1658 |
| 1987 | 1441 | 1599 | | 2004 | 1463 | 1634 | | 2021 | 1681 | 1809 |
| 1988 | 1488 | 1654 | | 2005 | 1582 | 1729 | | 2022 | 1677 | 1796 |
| 1989 | 1422 | 1632 | | 2006 | 1557 | 1693 | | 2023 | 1486 | 1610 |
| 1990 | 1410 | 1562 | | 2007 | 1492 | 1641 | | 2024 | 1312 | 1403 |
| 1991 | 1226 | 1389 | | 2008 | 1370 | 1495 | | | | |

#### Categorical columns / suppression markers

FARS categoricals are **numeric codes, not strings** — the string-based categorical/suppression
classification does not apply. There are no suppression markers anywhere (FARS is unsuppressed
public-domain microdata); unknowns are **in-band numeric sentinel codes** instead (see ETL). The
only string-typed columns are `TWAY_ID`(2), the 2015+ `…NAME` label twins, and 1975's all-null
`ROAD_FNC`.

## ETL Considerations

1. **Read directly from zips; match members case-insensitively by basename.** Layout varies
   (root vs `FARS{year}NationalCSV/` subfolder; `ACCIDENT.CSV` vs `accident.csv`). Never extract to
   disk (provenance contract).
2. **County code → FIPS (verified safe for GA).** FARS `COUNTY` is the GSA geographic code.
   **Verified against 2016, 2018, and 2024 `COUNTYNAME`: all GA codes map to the counties dimension
   with 0 name mismatches** — for Georgia, GSA code = 3-digit county FIPS suffix. Build
   `county_fips = "13" + COUNTY zero-padded to 3`, then **validate membership against the counties
   dimension** (159 counties, all-odd codes 001–321). Invalid codes to NULL (never drop the row —
   fatalities still count at state level; log counts): `999`/`0` (unknown/not applicable),
   `510`/`520`/`507` (1976–1981, 2–27 rows/yr), scattered even/one->321 codes 1986–1994 (1–10
   rows/yr, worst 1991). 1995+ is clean apart from single 0/999 rows in 2001–2006.
3. **`DRUNK_DR` ends in 2020.** The column is dropped from 2021 on. A drinking-driver-crashes
   metric from the accident file alone covers 1975–2020 only — the gold column must be NULL (not 0)
   for 2021+, or the metric must be rebuilt from person-level `DRINKING`/`ALC_RES` or the
   multiply-imputed BAC files (`MIPER` P1–P10; **absent 1975–1981**). NHTSA's published
   "alcohol-impaired-driving fatalities" series uses imputed driver BAC ≥ .08 — if we ever publish
   an alcohol metric, document which variable it is and that it is NOT comparable to `DRUNK_DR`.
   Simplest defensible v1: `crashes_with_drunk_driver = count(DRUNK_DR ≥ 1)` for 1975–2020, NULL after.
4. **Vehicle-count semantics change in 2005.** 1975–2004 `VE_FORMS` = all vehicles; 2005+
   `VE_TOTAL` = all vehicles (incl. parked/working) while `VE_FORMS` = in-transport only. For a
   continuous vehicles-involved metric use `VE_FORMS` (in-transport is the consistent concept), and
   note the pre-2005 definition includes the rare parked vehicle. Similarly `PERSONS` changes
   flavor post-2011 (`PERMVIT`/`PERNOTMVIT` split) — prefer FATALS/PEDS/crash counts as served
   metrics; treat PERSONS with care or leave it out.
5. **`PEDS` starts in 1991** (count of non-motorist person forms). A pedestrian/non-motorist
   involvement metric is NULL before 1991.
6. **In-band sentinel codes, not nulls.** Unknown values are numeric codes: HOUR 99 (and 24 =
   midnight in pre-~1998 years — remap, don't treat as unknown), WEATHER 9/98/99, MAN_COLL 9/98/99,
   LGT_COND 9 (8/9 in later years), lat/long 88888888/888888888 (integer era) and 99.9999/999.9999
   (decimal era). If any of these columns reach gold as categoricals, code lists ALSO shift meaning
   across eras (e.g. WEATHER 2 = rain pre-2010; 10 = cloudy 2015+) — a per-era recode map is
   required. For a pure county-year count table none of these matter.
7. **CSV parsing quirks**: 2021–2022 headers carry a UTF-8 BOM (strip from first column name);
   2006+ `MILEPT` contains floats that break naive int inference — use `infer_schema_length=None`
   (or explicit dtypes) and `encoding="utf8-lossy"`; polars parses every year cleanly with that.
8. **`YEAR` is 2-digit 1975–1997** (75–97) — derive gold `year` from the filename or normalize
   (1900 + YY); verified filename year always equals data year.
9. **Census ⇒ real zeros.** FARS covers *every* qualifying fatal crash. Only ~146–158 of 159 GA
   counties appear per year; missing county-years are **true zeros, not missing data**. The
   transform should densify to the full 159-county × 50-year grid with 0 counts (drunk-driver
   column still NULL where the era lacks it, per #3).
10. **Fatal-only scope.** No injury-only crashes, no enforcement counts — never present as total
    crash volume. Also GA's NHTSA-published fatality counts are by *state of crash*, matching this
    STATE=13 filter.
11. **`ST_CASE` is unique within a year only** — never use it as a cross-year key. Bronze grain =
    crash (one row per fatal crash); GA rows/year ≈ 1,080–1,681.
12. **Cross-file consistency check available**: sum(`FATALS`) in the accident table should equal
    person-table rows with `INJ_SEV = 4` (verified exact for 2024: 1,403). Useful as a transform
    sanity check if person data is ever read.
13. **Person-level detail (age/sex/race) is out of scope for v1** but present: `person.csv` all
    years (AGE, SEX, PER_TYP, INJ_SEV, DRINKING); race moves between the person file and a separate
    `race.csv` (2019+), Hispanic origin in the person file. A demographic breakdown would be a
    separate, larger effort with its own era mapping.

## Gold Schema Classification

Proposed gold grain: **county_fips × year** (aggregated from crash-level bronze; densified to all
159 counties, see ETL #9).

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| STATE | not_in_gold | — | filter `== 13` only |
| COUNTY | fact_key | county_fips | `"13" + zfill(3)`; validate against counties dimension; invalid → NULL (ETL #2) |
| YEAR (+ filename) | fact_key | year | normalize 2-digit years (ETL #8) |
| (row count) | fact_metric | fatal_crashes | count of crash rows; unit: count; **key_metric candidate** |
| FATALS | fact_metric | traffic_fatalities | sum; unit: count (likely the key metric users want) |
| DRUNK_DR | fact_metric | crashes_with_drunk_driver | count of rows with ≥1; 1975–2020 only, NULL after (ETL #3) |
| PEDS | fact_metric | crashes_with_nonmotorist (optional) | count of rows with ≥1; 1991+ only, NULL before |
| VE_FORMS | fact_metric | vehicles_involved (optional) | sum; semantics note ETL #4 |
| RUR_URB / LAND_USE / ROAD_FNC | fact_categorical (optional) | rural_urban | only if worth the 3-era recode (semantics differ — see ETL #6); otherwise not_in_gold |
| MONTH, DAY, DAY_WEEK, HOUR, MINUTE | not_in_gold | — | sub-annual detail below gold grain |
| CITY, TWAY_ID*, MILEPT, LATITUDE, LONGITUD | not_in_gold | — | sub-county location detail |
| LGT_COND, WEATHER*, MAN_COLL, HARM_EV, RELJCT*, TYP_INT, FUNC_SYS, SP_JUR, … | not_in_gold | — | crash-attribute codes; era-shifting code lists; not aggregated |
| ST_CASE | not_in_gold | — | within-year case id (join key for other bronze tables only) |
| COUNTYNAME / …NAME twins (2015+) | dimension_attribute | — | used only to verify county mapping; names come from the counties dimension |
| PERSON/VEHICLE/MI tables | not_in_gold | — | reserve for future person-level topics (ETL #13) |
| all other accident columns (NOT_/ARR_/HOSP_ times, CF1–3, SCH_BUS, RAIL, NHS, ROUTE, …) | not_in_gold | — | operational/roadway detail irrelevant to county-year counts |
