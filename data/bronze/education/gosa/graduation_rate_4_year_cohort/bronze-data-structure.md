# graduation_rate_4_year_cohort — Bronze Data Structure

## Overview

- Topic: graduation_rate_4_year_cohort
- Source: gosa
- Files: 21 files spanning 2004–2024
- Unreadable files: none (but `2004.csv` is malformed — requires `pl.read_csv(..., ignore_errors=True)`; `2005.csv` and `2006.csv` are XLS binary files mislabeled with the `.csv` extension — require `pl.read_excel(..., engine='calamine')`)
- Year representation: Eras 1–2 (2004–2010) have **no** year column (year from filename only); Eras 3–6 (2011–2024) have `LONG_SCHOOL_YEAR` column formatted as `"YYYY-YY"` (e.g., `"2023-24"`)
- Filename-to-data year offset: filename year = ending calendar year of the school year (e.g., `graduation_rate_4_year_cohort_2024.csv` contains `LONG_SCHOOL_YEAR = "2023-24"`; the file's year value matches the filename year in every tidy-era file checked)
- Detail levels: state, district, school (all eras include all three levels)
- Percentage scale: 0–100 for graduation rate (`Graduation Rate {demographic}` in Era 1, `GradRate_P{code}` in Era 2, `PROGRAM_PERCENT` in Eras 3–6)
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| graduation_rate_4_year_cohort_2004.csv | 76f29977d09fe345ec6b11d4b2ff6192512c36f6013cdd41e2e43e7e3081f5ac |
| graduation_rate_4_year_cohort_2005.csv | e9d961aeed210dd2820ba3dbb09338171df431ede814825e0eead4aefba80871 |
| graduation_rate_4_year_cohort_2006.csv | fda5c44b22d3c5ce29a1f7abcf1764ba34bd716c9c9f94ac033d19ac981a8ec5 |
| graduation_rate_4_year_cohort_2007.xls | 661865cefd84b5a3add6e0f7907f3ee050756deb39a7a0697ba2a817e4d3f06c |
| graduation_rate_4_year_cohort_2008.xls | d00107baff7a48a0d7ff07e1ee7decd754c458f3b0a1483a73c2f4533f7e910a |
| graduation_rate_4_year_cohort_2009.xls | 3a6ea1aa18ffa3ed1d103291e406186602954e9621e245b3e4cbe8273f55187e |
| graduation_rate_4_year_cohort_2010.xls | ea4becbec3c2e3f850dd5109db1380aef2fcb0506f5f7aca9abef81c9275c350 |
| graduation_rate_4_year_cohort_2011.csv | dd800ce655fee4ed2f222b5977a39c039d1851bbab620cb548c3cb0b3d9be730 |
| graduation_rate_4_year_cohort_2012.csv | 20218d37f2dcdfae789ec126d3ccb44bf4cf5587ea1a2bdc0b71d7516049755a |
| graduation_rate_4_year_cohort_2013.csv | e8f6e0d16fa2063f38856075c8c5d1383963cd4ae022c2e4977578634e0c1872 |
| graduation_rate_4_year_cohort_2014.csv | c82fd2484e5f8c3481c9b84e5f7c977640770f6f98992e59ef7a4ec7ef2860a4 |
| graduation_rate_4_year_cohort_2015.csv | 5a2b786e91607abb4dd251eb3629db7a295e06216c9a9132656e1a49f5fb3497 |
| graduation_rate_4_year_cohort_2016.csv | 095d818c2cd1c34bf6752a4630c8f40c414f52f586f6244b3caebb1b75a628a8 |
| graduation_rate_4_year_cohort_2017.csv | 1efe61030ff8c13b3642e5f07fdbca8092f09727751203436cc334e34ef98a51 |
| graduation_rate_4_year_cohort_2018.csv | 774307610672af844b2f96babb61b4755319bf75765f9085082cf612c1cc5ea7 |
| graduation_rate_4_year_cohort_2019.csv | 9ce9346c9f2c34bc3ad318124d0a685b5f1a6d20a93261df78749cac681a73a1 |
| graduation_rate_4_year_cohort_2020.csv | 6641e069f2fddfffbcff7f1f146ead41c92e59dba3bd61ef1546e072667e2f10 |
| graduation_rate_4_year_cohort_2021.csv | 5712a9e02f6a7f7e0186ee4cb54ac3680548226593da6a0437170698ac4476ae |
| graduation_rate_4_year_cohort_2022.csv | e70aec77563c9d879203c5705d96e01716490218b11c14e44a08761a8b58276f |
| graduation_rate_4_year_cohort_2023.csv | d370015308b086c47d7959784c3e1179fa6016ecb061c08bd4920152821aca8a |
| graduation_rate_4_year_cohort_2024.csv | b77c26d923421c15a302009b0033520b82599aa147ed13cf927c5360131eafec |

## Excel Sheet Structure

Only Era 2 (and the mislabeled 2005/2006 XLS files) are Excel-format. Five of the six XLS files share the standard Excel "Sheet1 + two empty sheets" layout; 2009.xls is the only outlier (single `GradRate` sheet, no empty extras). All data is in a single sheet per file — the transform never needs to concatenate sheets.

| File(s) | Sheets | Notes |
|---------|--------|-------|
| 2005.csv, 2006.csv | Sheet1 (Data, 522–530 rows × 47 cols), Sheet2 (empty), Sheet3 (empty) | XLS binary files mislabeled with `.csv` extension; magic bytes `d0cf11e0a1b11ae1` confirm OLE compound format. Must be read with `pl.read_excel(engine='calamine')` |
| 2007.xls, 2008.xls, 2010.xls | Sheet1 (Data, 535–576 rows × 47 cols), Sheet2 (empty), Sheet3 (empty) | Standard Excel default sheet layout; data sheet is named `Sheet1` |
| 2009.xls | GradRate (Data, 561 rows × 47 cols) | Only XLS file with a named data sheet; no empty sibling sheets |

CSV files (2004, 2011–2024) have no sheet structure.

## Summary

Annual high school four-year adjusted cohort graduation rate for Georgia public schools, districts, and the state. Each row reports the graduation rate (`PROGRAM_PERCENT` / `GradRate_P*` / `Graduation Rate ...`) with paired denominators: number of graduates (`PROGRAM_TOTAL` / `GradRate_N*` / `Number Taken`) and cohort size (`TOTAL_COUNT` / `GradRate_S*` / `Approximate Class Size`). Metrics are broken out by demographic subgroup — race/ethnicity (Black, White, Hispanic, Asian/Pacific Islander, American Indian/Alaskan, Multi-Racial), gender (Male, Female), and special populations (Students With/Without Disability, Limited English Proficient, Economically Disadvantaged, Not Economically Disadvantaged, Migrant; plus Active Duty, Foster, Homeless added in **2018** onward — measured per file; an earlier revision of this doc claimed 2020).

## Eras

### Era 1: 2004–2006 (wide-format, human-readable headers)

| Column | Description |
|--------|-------------|
| SysSchoolID | Compound ID `{district}:{school}` — state=`ALL:ALL`, district=`NNN:ALL`, school=`NNN:MMMM` |
| SchoolName | Entity name (school, district, or "State Of Georgia" / "State Schools") |
| Graduation Rate All Students | Grad rate percent (0–100) for all students |
| Number Taken All Students | Count of graduates in cohort |
| Approximate Class Size All Students | Cohort size (denominator) |
| Graduation Rate Asian | Grad rate percent for Asian students |
| Number Taken Asian | Count of Asian graduates |
| Approximate Class Size Asian | Asian cohort size |
| Graduation Rate Black | Grad rate percent for Black students |
| Number Taken Black | Count of Black graduates |
| Approximate Class Size Black | Black cohort size |
| Graduation Rate Hispanic | Grad rate percent for Hispanic students |
| Number Taken Hispanic | Count of Hispanic graduates |
| Approximate Class Size Hispanic | Hispanic cohort size |
| Graduation Rate Native Amer/Alaskan Native | Grad rate percent for American Indian / Alaskan Native students |
| Number Taken Native Amer/Alaskan Native | Count of American Indian / Alaskan Native graduates |
| Approximate Class Size Amer/Alaskan Native | American Indian / Alaskan Native cohort size (note: column name drops "Native" prefix vs. rate/count columns) |
| Graduation Rate White | Grad rate percent for White students |
| Number Taken White | Count of White graduates |
| Approximate Class Size White | White cohort size |
| Graduation Rate Multiracial | Grad rate percent for Multiracial students |
| Number Taken Multiracial | Count of Multiracial graduates |
| Approximate Class Size Multiracial | Multiracial cohort size |
| Graduation Rate Male | Grad rate percent for Male students |
| Number Taken Male | Count of Male graduates |
| Approximate Class Size Male | Male cohort size |
| Graduation Rate Female | Grad rate percent for Female students |
| Number Taken Female | Count of Female graduates |
| Approximate Class Size Female | Female cohort size |
| Graduation Rate Students with Disabilities | Grad rate percent — SWD |
| Number Taken Students with Disabilities | SWD graduates |
| Approximate Class Size Students with Disabilities | SWD cohort size |
| Graduation Rate Students without Disabilities | Grad rate percent — non-SWD |
| Number Taken Students without Disabilities | Non-SWD graduates |
| Approximate Class Size Students without Disabilities | Non-SWD cohort size |
| Graduation Rate Limited English Proficient | Grad rate percent for LEP students |
| Number Taken Limited English Proficient | LEP graduates |
| Approximate Class Size Limited English Proficient | LEP cohort size |
| Graduation Rate Economically Disadvantaged | Grad rate percent for economically disadvantaged students |
| Number Taken Economically Disadvantaged | Economically disadvantaged graduates |
| Approximate Class Size Economically Disadvantaged | Economically disadvantaged cohort size |
| Graduation Rate Not Economically Disadv | Grad rate percent for not-economically-disadvantaged students |
| Number Taken Not Economically Disadv | Not-economically-disadvantaged graduates |
| Approximate Class Size Not Economically Disadv | Not-economically-disadvantaged cohort size |
| Graduation Rate Migrant | Grad rate percent for migrant students |
| Number Taken Migrant | Migrant graduates |
| Approximate Class Size Migrant | Migrant cohort size |

#### Sample Data (2005.csv, first 10 columns)

```
shape: (5, 10)
SysSchoolID  SchoolName                Grad Rate All  Num Taken All  Class Size All  Grad Rate Asian  Num Taken Asian  Class Size Asian  Grad Rate Black  Num Taken Black
741:201      Callaway High School      63.5           108            170             0.0              0                1                 65.8             50
649:2050     Early County High School  68.0           140            206             0.0              0                0                 60.9             84
792:273      Valdosta High School      65.0           360            554             84.6             11               13                59.4             212
719:ALL      Rabun County              72.1           106            147             0.0              0                0                 0.0              0
738:192      Toombs County High School 68.1           128            188             100.0            1                1                 48.6             18
```

#### Statistics

| Metric | 2005 `Graduation Rate All Students` (n=522) |
|--------|----------------------------------------------|
| mean | 67.55 |
| std | 14.59 |
| min | 0.0 |
| p25 | 60.6 |
| p50 | 67.3 |
| p75 | 75.6 |
| max | 100.0 |

Row counts by file and detail level:

| File | Total | State | District | School |
|------|-------|-------|----------|--------|
| 2004.csv (malformed) | 2271 | 1 | 187 | 2082 + 1 bad row (`SysSchoolID="0\""`, `SchoolName="10"`) |
| 2005.csv | 522 | 1 | 178 | 343 |
| 2006.csv | 530 | 1 | 178 | 351 |

#### Null Counts

All 47 columns have `null_count = 0` in 2005 and 2006 (zeros are encoded as literal `0` for suppressed cells, not null). 2004.csv has extensive nulls because of the malformed structure.

#### Categorical Columns

| Column | Distinct Values |
|--------|-----------------|
| SysSchoolID | 522 distinct in 2005 (178 districts × mix of schools + 1 state row) |

#### Suppression Markers

No string-typed suppression markers in Era 1 — suppressed cells appear as the literal numeric `0` for both rate and count. For example, `Callaway High School` shows `Number Taken Asian = 0`, `Class Size Asian = 1` (meaning 0 of 1 Asian students in the cohort — could be either a real zero-graduation-rate or a privacy-suppressed value). The reader cannot distinguish suppressed cells from real zeros in Era 1; transforms must treat very small cohorts (denominator < threshold) as suppression-equivalent.

### Era 2: 2007–2010 (wide-format, cryptic column codes)

| Column | Description |
|--------|-------------|
| SysSchoolID | Compound ID `{district}:{school}` (same format as Era 1) |
| SchoolNme | Entity name (note typo — missing 'a') |
| GradRate_P0 / GradRate_N0 / GradRate_S0 | Percent / Numerator / Denominator for **All Students** (0 = overall) |
| GradRate_Pa / GradRate_Na / GradRate_Sa | Percent / N / S for **Asian** |
| GradRate_Pb / GradRate_Nb / GradRate_Sb | Percent / N / S for **Black** |
| GradRate_Ph / GradRate_Nh / GradRate_Sh | Percent / N / S for **Hispanic** |
| GradRate_Pn / GradRate_Nn / GradRate_Sn | Percent / N / S for **Native American / Alaskan Native** |
| GradRate_Pw / GradRate_Nw / GradRate_Sw | Percent / N / S for **White** |
| GradRate_Pu / GradRate_Nu / GradRate_Su | Percent / N / S for **M(u)lti-racial** (suffix `u`) |
| GradRate_Pm / GradRate_Nm / GradRate_Sm | Percent / N / S for **Male** |
| GradRate_Pf / GradRate_Nf / GradRate_Sf | Percent / N / S for **Female** |
| GradRate_PS / GradRate_NS / GradRate_SS | Percent / N / S for **Students with Disabilities (SWD)** |
| GradRate_PRL / GradRate_NRL / GradRate_SRL | Percent / N / S for **"Regular-Learners" — Students without Disabilities** |
| GradRate_PL / GradRate_NL / GradRate_SL | Percent / N / S for **Limited English Proficient (LEP)** |
| GradRate_P_ed / GradRate_N_ed / GradRate_S_ed | Percent / N / S for **Economically Disadvantaged** |
| GradRate_P_ned / GradRate_N_ned / GradRate_S_ned | Percent / N / S for **Not Economically Disadvantaged** |
| GradRate_P_mig / GradRate_N_mig / GradRate_S_mig | Percent / N / S for **Migrant** |

Demographic suffix legend (derived from value comparison with Era 1):
- `0` = All Students
- `a` = Asian
- `b` = Black
- `h` = Hispanic
- `n` = Native American / Alaskan Native
- `w` = White
- `u` = Multiracial (probably "unknown"/"multi" — not standard)
- `m` = Male
- `f` = Female
- `S` = SWD (Students with Disabilities)
- `RL` = Non-SWD (Regular Learners)
- `L` = Limited English Proficient
- `_ed` = Economically Disadvantaged
- `_ned` = Not Economically Disadvantaged
- `_mig` = Migrant

#### Sample Data (2010.xls, first 12 columns)

```
shape: (5, 12)
SysSchoolID  SchoolNme                 GradRate_P0  GradRate_N0  GradRate_S0  GradRate_Pa       GradRate_Na       GradRate_Sa       GradRate_Pb  GradRate_Nb  GradRate_Sb  GradRate_Ph
601:103      Appling County High Schl  80.2         202          252          Too few Students  Too few Students  Too few Students  80.3         49           61           100
601:ALL      Appling County            80.2         202          252          Too few Students  Too few Students  Too few Students  80.3         49           61           100
602:103      Atkinson County High Schl 81.8         72           88           Too few Students  Too few Students  Too few Students  63.6         14           22           100
602:ALL      Atkinson County           81.8         72           88           Too few Students  Too few Students  Too few Students  63.6         14           22           100
603:302      Bacon County High School  82.6         95           115          Too few Students  Too few Students  Too few Students  87           20           23           Too few Students
```

#### Statistics

| Metric | 2010 `GradRate_P0` cast to float (n=568) |
|--------|-------------------------------------------|
| mean | 79.51 |
| std | 12.14 |
| min | 0.0 |
| p25 | 74.7 |
| p50 | 80.9 |
| p75 | 86.9 |
| max | 100.0 |
| null_count | 8 (all "Too few Students") |

Row counts by file and detail level:

| File | Total | State | District | School |
|------|-------|-------|----------|--------|
| 2007.xls | 535 | 1 | 177 | 357 |
| 2008.xls | 550 | 1 | 185 | 364 |
| 2009.xls | 561 | 1 | 189 | 371 |
| 2010.xls | 576 | 1 | 186 | 389 |

#### Null Counts

**2010 only** is typed `String`-with-markers: the `Too few Students` suppression marker is interleaved with numeric values (9,573 marker cells = 3,191 suppressed triplets; zero blank cells). **2007–2009 contain ZERO `Too few Students` cells, zero blank cells, and zero nulls** — they use Era-1-style literal-zero suppression instead (measured zero-rate cells: 2007: 1,818; 2008: 1,805; 2009: 1,774; vs only 15 in 2010). An earlier revision of this doc attributed the marker to all of 2007–2010.

#### Categorical Columns

In 2010, numeric metric columns render as [CATEGORICAL] because of the mixed numeric + `"Too few Students"` content; after casting with `strict=False`, only the suppression marker remains non-numeric. 2007–2009 metric columns are purely numeric strings.

#### Suppression Markers

| File(s) | Marker |
|---------|--------|
| 2007.xls, 2008.xls, 2009.xls | none — literal zeros stand in for suppressed cells (indistinguishable from real zeros, same as Era 1) |
| 2010.xls | `Too few Students` in all 45 `GradRate_*` columns (case-sensitive, literal) |

### Era 3: 2011 (tidy format with TOTAL_COUNT denominator — 1 year only)

| Column | Description |
|--------|-------------|
| LONG_SCHOOL_YEAR | School year as `"2010-11"` (single value per file) |
| DETAIL_LVL_DESC | Detail level: `State`, `District`, or `School` |
| SCHOOL_DSTRCT_CD | 3-digit zero-padded district code (`601`, `602`, ...) or `ALL` for state rows |
| SCHOOL_DSTRCT_NM | District name, or `All Column Values` for state rows |
| INSTN_NUMBER | 4-digit zero-padded school institution number (`0100`, `1050`, ...) or `ALL` for district and state rows |
| INSTN_NAME | School name, or `All Column Values` for district/state rows |
| GRADES_SERVED_DESC | Comma-joined list of grade codes served (e.g., `"PK,KK,01,02,...,11,12"`) — describes which grades the entity serves |
| LABEL_LVL_1_DESC | Demographic label: `Grad Rate -ALL Students`, `Grad Rate -Black`, `Grad Rate -Female`, etc. (15 distinct values) |
| PROGRAM_TOTAL | Numerator — count of graduates for that subgroup |
| PROGRAM_PERCENT | Graduation rate percent (0–100) |
| TOTAL_COUNT | Denominator — cohort size |

Era 3 has `TOTAL_COUNT`, which Era 4 (2012–2016) drops and Era 5 (2017–2022) reintroduces.

#### Sample Data (2011.csv, first 5 rows)

```
shape: (5, 11)
LONG_SCHOOL_YEAR  DETAIL_LVL_DESC  SCHOOL_DSTRCT_CD  SCHOOL_DSTRCT_NM  INSTN_NUMBER  INSTN_NAME         GRADES_SERVED_DESC                          LABEL_LVL_1_DESC                       PROGRAM_TOTAL  PROGRAM_PERCENT  TOTAL_COUNT
2010-11           District         601               Appling County    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Grad Rate -ALL Students                161            60.98            264
2010-11           District         601               Appling County    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Grad Rate -American Indian/Alaskan     null           null             null
2010-11           District         601               Appling County    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Grad Rate -Asian/Pacific Islander      null           null             null
2010-11           District         601               Appling County    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Grad Rate -Black                       37             50.0             74
2010-11           District         601               Appling County    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Grad Rate -Economically Disadvantaged  93             62.84            148
```

#### Statistics

| Metric | 2011.csv (n=9675 rows) |
|--------|-------------------------|
| PROGRAM_TOTAL — mean | 254.46 |
| PROGRAM_TOTAL — min | 10 (low end of reported counts; < 10 is suppressed to null) |
| PROGRAM_TOTAL — max | 88,391 (state-level row) |
| PROGRAM_PERCENT — mean | 69.08 |
| PROGRAM_PERCENT — min | 5.85 |
| PROGRAM_PERCENT — max | 100.0 |
| TOTAL_COUNT — mean | 372.23 |
| TOTAL_COUNT — min | 10 |
| TOTAL_COUNT — max | 131,012 (state) |

Row counts by detail level: School=6900, District=2760, State=15.

#### Null Counts

| Column | Null Count |
|--------|-----------|
| LONG_SCHOOL_YEAR | 0 |
| DETAIL_LVL_DESC | 0 |
| SCHOOL_DSTRCT_CD | 0 |
| SCHOOL_DSTRCT_NM | 0 |
| INSTN_NUMBER | 0 |
| INSTN_NAME | 0 |
| GRADES_SERVED_DESC | 0 |
| LABEL_LVL_1_DESC | 0 |
| PROGRAM_TOTAL | 4481 (46.3%) — suppressed cohorts |
| PROGRAM_PERCENT | 4481 (46.3%) |
| TOTAL_COUNT | 4481 (46.3%) |

#### Categorical Columns

| Column | Distinct Values |
|--------|-----------------|
| LONG_SCHOOL_YEAR | 1: `2010-11` |
| DETAIL_LVL_DESC | 3: `District`, `School`, `State` |
| SCHOOL_DSTRCT_NM | 185 (includes `All Column Values` used for state rows) |
| INSTN_NAME | 454 |
| GRADES_SERVED_DESC | 35 unique grade-span strings |
| LABEL_LVL_1_DESC | 15: `Grad Rate -ALL Students`, `Grad Rate -American Indian/Alaskan`, `Grad Rate -Asian/Pacific Islander`, `Grad Rate -Black`, `Grad Rate -Economically Disadvantaged`, `Grad Rate -Female`, `Grad Rate -Hispanic`, `Grad Rate -Limited English Proficient`, `Grad Rate -Male`, `Grad Rate -Migrant`, `Grad Rate -Multi-Racial`, `Grad Rate -Not Economically Disadvantaged`, `Grad Rate -Students With Disability`, `Grad Rate -Students Without Disability`, `Grad Rate -White` |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|--------------------|
| SCHOOL_DSTRCT_CD | `ALL` (used on state-level rows — not a real suppression but a literal aggregate marker) |
| INSTN_NUMBER | `ALL` (used on district- and state-level rows) |

Numeric suppression in Era 3 is encoded as **`null`** (blank cell) — no string markers like `TFS` or `Too few Students` in the three numeric columns.

### Era 4: 2012–2016 (tidy format, no TOTAL_COUNT)

Same schema as Era 3 but `TOTAL_COUNT` is **absent** — only `PROGRAM_TOTAL` (numerator) and `PROGRAM_PERCENT` (rate) are present, so the cohort size (denominator) cannot be recovered without computing `PROGRAM_TOTAL / (PROGRAM_PERCENT / 100)`.

| Column | Description |
|--------|-------------|
| LONG_SCHOOL_YEAR | `2011-12`, `2012-13`, ..., `2015-16` (one value per file) |
| DETAIL_LVL_DESC | `State`, `District`, `School` |
| SCHOOL_DSTRCT_CD | 3-digit district code or `ALL` |
| SCHOOL_DSTRCT_NM | District name or `All Column Values` |
| INSTN_NUMBER | 4-digit school number or `ALL` |
| INSTN_NAME | School name or `All Column Values` |
| GRADES_SERVED_DESC | Comma-joined grade list |
| LABEL_LVL_1_DESC | Demographic label (15 values, same as Era 3) |
| PROGRAM_TOTAL | Integer — number of graduates |
| PROGRAM_PERCENT | Float — graduation rate percent (0–100) |

#### Sample Data (2014.csv, first 5 rows)

```
shape: (5, 10)
LONG_SCHOOL_YEAR  DETAIL_LVL_DESC  SCHOOL_DSTRCT_CD  SCHOOL_DSTRCT_NM  INSTN_NUMBER  INSTN_NAME         GRADES_SERVED_DESC                          LABEL_LVL_1_DESC                       PROGRAM_TOTAL  PROGRAM_PERCENT
2013-14           District         601               Appling County    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Grad Rate -ALL Students                206            82.4
2013-14           District         601               Appling County    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Grad Rate -American Indian/Alaskan     null           null
2013-14           District         601               Appling County    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Grad Rate -Asian/Pacific Islander      null           null
2013-14           District         601               Appling County    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Grad Rate -Black                       39             79.6
2013-14           District         601               Appling County    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Grad Rate -Economically Disadvantaged  97             80.2
```

#### Statistics

| Metric | 2014.csv |
|--------|----------|
| Rows | 9836 |
| PROGRAM_PERCENT mean | 74.10 |
| PROGRAM_PERCENT min | 5.1 |
| PROGRAM_PERCENT max | 100.0 |
| PROGRAM_TOTAL mean | 250.29 |
| PROGRAM_TOTAL max | 89,498 (state row) |

Row counts per file (all have `DETAIL_LVL_DESC` values of `State`, `District`, `School`):

| File | Total rows | State | District | School |
|------|------------|-------|----------|--------|
| 2012.csv | 9900 | 15 | 2775 | 7110 |
| 2013.csv | 9873 | 15 | 2805 | 7053 |
| 2014.csv | 9836 | 15 | ~2835 | ~6986 |
| 2015.csv | 9960 | 15 | 2835 | 7110 |
| 2016.csv | 10155 | 15 | 2910 | 7230 |

#### Null Counts

Same pattern as Era 3 — `PROGRAM_TOTAL` and `PROGRAM_PERCENT` are null on ~45% of rows (suppressed small subgroups).

#### Categorical Columns

Same as Era 3 — same 15 `LABEL_LVL_1_DESC` values, same 3 `DETAIL_LVL_DESC` values.

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|--------------------|
| SCHOOL_DSTRCT_CD | `ALL` (state-level rows) |
| INSTN_NUMBER | `ALL` (district- and state-level rows) |

Numeric suppression = null (no `TFS` or similar string in this era).

### Era 5: 2017–2022 (tidy format, TOTAL_COUNT reintroduced)

Schema identical to Era 3 (11 columns including `TOTAL_COUNT`), but:
- `LABEL_LVL_1_DESC` grows from 15 to **18 values** in **2018** onwards (adds `Grad Rate -Active Duty`, `Grad Rate -Foster`, `Grad Rate -Homeless`). Measured per file: 2017 has 15 distinct labels; 2018, 2019, 2020, and 2022 have 18; **2021 has 17** — `Grad Rate -Limited English Proficient` is absent from the 2021 file only (it returns in 2022). (An earlier revision of this doc claimed the 18-label expansion started in 2020.)
- Starting in **2021**, `PROGRAM_TOTAL`, `PROGRAM_PERCENT`, and `TOTAL_COUNT` become string-typed due to the introduction of the **`TFS`** suppression marker (Too Few Students) interspersed with numeric values. 2017–2020 are still integer/float because they use blank cells for suppression.
- 2017 is a transition year — it has the same column set as Era 3/Era 5 (TOTAL_COUNT is back) but the 15-demographic list (before the 2018 expansion).

| Column | Description |
|--------|-------------|
| LONG_SCHOOL_YEAR | `2016-17`, ..., `2021-22` |
| DETAIL_LVL_DESC | `State`, `District`, `School` |
| SCHOOL_DSTRCT_CD | 3-digit district code or `ALL` |
| SCHOOL_DSTRCT_NM | District name or `All Column Values` |
| INSTN_NUMBER | 4-digit school number or `ALL` |
| INSTN_NAME | School name or `All Column Values` |
| GRADES_SERVED_DESC | Comma-joined grade list |
| LABEL_LVL_1_DESC | Demographic label (15 values in 2017; **18 values** in 2018–2020 and 2022 after adding Active Duty / Foster / Homeless; **17 values in 2021** — Limited English Proficient absent that year only) |
| PROGRAM_TOTAL | 2017–2020: Int64; **2021–2022: String (contains `TFS`)** |
| PROGRAM_PERCENT | 2017–2020: Float64; **2021–2022: String (contains `TFS`)** |
| TOTAL_COUNT | 2017–2020: Int64; **2021–2022: String (contains `TFS`)** |

Note on era boundaries (measured per file; an earlier revision of this doc misstated them): the demographic expansion to 18 labels starts in **2018**, while the `TFS` string suppression marker starts in **2021** — the two changes do NOT coincide. 2017 uses blank-cell suppression and the 15-demographic set; 2018–2020 use blank-cell suppression with the 18-demographic set; 2021–2022 use `TFS` markers (2021 with 17 labels, 2022 back to 18). Grouping 2017–2022 together is driven by the column-name match (the core header is identical) — downstream transforms must branch on year-level behavior for types and label counts.

#### Sample Data (2020.csv, first 5 rows)

```
shape: (5, 11)
LONG_SCHOOL_YEAR  DETAIL_LVL_DESC  SCHOOL_DSTRCT_CD  SCHOOL_DSTRCT_NM  INSTN_NUMBER  INSTN_NAME         GRADES_SERVED_DESC                          LABEL_LVL_1_DESC                    PROGRAM_TOTAL  PROGRAM_PERCENT  TOTAL_COUNT
2019-20           District         601               Appling County    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Grad Rate -ALL Students             205            92.76            221
2019-20           District         601               Appling County    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Grad Rate -Active Duty              null           null             null
2019-20           District         601               Appling County    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Grad Rate -American Indian/Alaskan  null           null             null
2019-20           District         601               Appling County    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Grad Rate -Asian/Pacific Islander   null           null             null
2019-20           District         601               Appling County    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Grad Rate -Black                    32             84.21            38
```

#### Statistics

| File | Rows | PROGRAM_PERCENT mean | min | max | dtype |
|------|------|---------------------|-----|-----|-------|
| 2017.csv | 10190 | - | - | - | numeric (Int64 / Float64) |
| 2018.csv | 12508 | - | - | - | numeric |
| 2019.csv | 12963 | - | - | - | numeric |
| 2020.csv | 13001 | 86.37 | 5.3 | 100.0 | numeric (blank = suppressed) |
| 2021.csv | 12176 | - | - | - | **String** (`TFS` marker) |
| 2022.csv | 13091 | - | - | - | **String** (`TFS` marker) |

#### Null Counts

For 2020.csv (13001 rows × 11 cols): `PROGRAM_TOTAL`, `PROGRAM_PERCENT`, `TOTAL_COUNT` = 6834 nulls (≈52.6%). Other columns = 0.

#### Categorical Columns

| Column | Distinct Values (2020) |
|--------|------------------------|
| LONG_SCHOOL_YEAR | 1 per file |
| DETAIL_LVL_DESC | 3: `District`, `School`, `State` |
| SCHOOL_DSTRCT_NM | 217 |
| INSTN_NAME | 519 |
| GRADES_SERVED_DESC | 42 |
| LABEL_LVL_1_DESC | **18**: 15 from Era 3/4 + `Grad Rate -Active Duty`, `Grad Rate -Foster`, `Grad Rate -Homeless` |

#### Suppression Markers

| Column | Non-Numeric Values (2017–2019) | Non-Numeric Values (2020–2022) |
|--------|--------------------------------|--------------------------------|
| SCHOOL_DSTRCT_CD | `ALL` | `ALL` |
| INSTN_NUMBER | `ALL` | `ALL` |
| PROGRAM_TOTAL | — (null only) | — (null only in 2020); **`TFS`** in 2021–2022 |
| PROGRAM_PERCENT | — (null only) | — (null only in 2020); **`TFS`** in 2021–2022 |
| TOTAL_COUNT | — (null only) | — (null only in 2020); **`TFS`** in 2021–2022 |

2020.csv, despite using the expanded 18-demographic label set, still encodes suppression as blank cells (null). The switch to `TFS` string marker happens in the 2021 file.

### Era 6: 2023–2024 (tidy format with leading #RPT_NAME column)

Same 11 data columns as Era 5, plus a new leading **`#RPT_NAME`** column whose sole value is `"Graduation Rate"` (constant — effectively a report-type label). All three numeric columns are string-typed with `TFS` suppression markers.

| Column | Description |
|--------|-------------|
| #RPT_NAME | Report name — constant string `"Graduation Rate"` in every row (no information content) |
| LONG_SCHOOL_YEAR | `2022-23`, `2023-24` |
| DETAIL_LVL_DESC | `State`, `District`, `School` |
| SCHOOL_DSTRCT_CD | 3-digit district code or `ALL` |
| SCHOOL_DSTRCT_NM | District name or `All Column Values` |
| INSTN_NUMBER | 4-digit school number or `ALL` |
| INSTN_NAME | School name or `All Column Values` |
| GRADES_SERVED_DESC | Comma-joined grade list |
| LABEL_LVL_1_DESC | 18 demographic labels (same 18-label set as 2018–2020 and 2022) |
| PROGRAM_TOTAL | String — integer graduate count or `TFS` |
| PROGRAM_PERCENT | String — graduation-rate percent (0–100) or `TFS` |
| TOTAL_COUNT | String — cohort size or `TFS` |

#### Sample Data (2024.csv, first 5 rows)

```
shape: (5, 12)
#RPT_NAME        LONG_SCHOOL_YEAR  DETAIL_LVL_DESC  SCHOOL_DSTRCT_CD  SCHOOL_DSTRCT_NM  INSTN_NUMBER  INSTN_NAME         GRADES_SERVED_DESC                          LABEL_LVL_1_DESC                   PROGRAM_TOTAL  PROGRAM_PERCENT  TOTAL_COUNT
Graduation Rate  2023-24           District         601               Appling County    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Grad Rate -ALL Students            225            93.75            240
Graduation Rate  2023-24           District         601               Appling County    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Grad Rate -Active Duty             TFS            TFS              TFS
Graduation Rate  2023-24           District         601               Appling County    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Grad Rate -American Indian/Alaskan TFS            TFS              TFS
Graduation Rate  2023-24           District         601               Appling County    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Grad Rate -Asian/Pacific Islander  TFS            TFS              TFS
Graduation Rate  2023-24           District         601               Appling County    ALL           All Column Values  PK,KK,01,02,03,04,05,06,07,08,09,10,11,12   Grad Rate -Black                   57             91.94            62
```

#### Statistics

| File | Rows | PROGRAM_PERCENT (cast) mean | min | max | non-numeric values |
|------|------|------------------------------|-----|-----|--------------------|
| 2023.csv | 13075 | — | — | — | `TFS` |
| 2024.csv | 13256 | 88.31 | 7.13 | 100.0 (n=6526 numeric) | `TFS` (n=6730) |

Row counts (2023): School=9250, District=3807, State=18. Row counts (2024): School=9285, District=3953, State=18 (18 = one row per demographic in `LABEL_LVL_1_DESC` at state level; an earlier revision of this doc mislabeled the 2023 counts as 2024's).

#### Null Counts

All columns have `null_count = 0` in 2024.csv — suppression is encoded with the literal string `"TFS"` rather than null.

#### Categorical Columns

| Column | Distinct Values (2024) |
|--------|------------------------|
| #RPT_NAME | 1: `Graduation Rate` |
| LONG_SCHOOL_YEAR | 1 per file |
| DETAIL_LVL_DESC | 3: `District`, `School`, `State` |
| SCHOOL_DSTRCT_NM | 235 |
| INSTN_NAME | 515 |
| GRADES_SERVED_DESC | 33 |
| LABEL_LVL_1_DESC | 18: same set as 2020–2022 |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|--------------------|
| SCHOOL_DSTRCT_CD | `ALL` |
| INSTN_NUMBER | `ALL` |
| PROGRAM_TOTAL | `TFS` |
| PROGRAM_PERCENT | `TFS` |
| TOTAL_COUNT | `TFS` |

## ETL Considerations

1. **File-format traps.** 2005 and 2006 carry `.csv` extensions but are binary XLS files (magic bytes `d0cf11e0a1b11ae1`). Reading them as CSV silently returns garbage or errors. Use `pl.read_excel(path, engine='calamine')` — the loader must inspect magic bytes (or sniff by year) rather than relying on extension. 2009.xls's sole sheet is named `GradRate` instead of `Sheet1` — Polars auto-detects the first non-empty sheet, so this works with default `sheet_id=1`.

2. **Malformed 2004.csv.** Has a single corrupt row with `SysSchoolID="0\""` / `SchoolName="10"` that injects 50 spurious rows when parsed strictly. Use `pl.read_csv(..., ignore_errors=True)` and drop rows where `SysSchoolID` lacks a colon before downstream processing. Warning: the `ignore_errors` path still yields 2271 rows, of which only 2270 are valid — the 1 corrupt row must be filtered explicitly, not relied on to be dropped by polars.

3. **Year representation.** Eras 1–2 (2004–2010) have **no year column**. The transform must inject the year from the filename. Eras 3+ have `LONG_SCHOOL_YEAR` in `"YYYY-YY"` format — parse the ending year (`"2023-24"` → 2024) as the canonical `year` to align with filename convention.

4. **Wide-to-long reshape for Eras 1 and 2.** Both wide eras store one row per school/district with 15 (Era 1) or 15 (Era 2) demographic subgroups × 3 metrics per row (rate, numerator, denominator). The transform must melt these into tidy format matching Era 3+ (`demographic` column + `value_type` column or separate rate/numerator/denominator columns).

5. **Demographic label mapping.** Five distinct naming conventions exist for the same demographic breakdown:
   - Era 1: `"Graduation Rate Asian"`, `"Graduation Rate Native Amer/Alaskan Native"`, `"Graduation Rate Students with Disabilities"`, ...
   - Era 2: cryptic `GradRate_Pa`, `GradRate_Pn`, `GradRate_PS`, `GradRate_PRL` (regular learners = non-SWD), `GradRate_P_ed`, `GradRate_P_ned`, `GradRate_P_mig`
   - Eras 3–4: `"Grad Rate -ALL Students"`, `"Grad Rate -Asian/Pacific Islander"`, `"Grad Rate -Multi-Racial"`, `"Grad Rate -Students With Disability"`, ... (15 values)
   - Eras 5+: adds `"Grad Rate -Active Duty"`, `"Grad Rate -Foster"`, `"Grad Rate -Homeless"` starting 2018 (18 values; 17 in 2021 where Limited English Proficient is absent)
   - Build an explicit bronze→canonical demographic mapping per era; manually verify against the demographics dimension (`data/gold/_dimensions/demographics.parquet`).
   - Note: Era 1 combines `"Native Amer/Alaskan Native"` (with "Native" in name) vs. Era 2 uses code `n`; Eras 3+ use `"American Indian/Alaskan"` — semantics are the same.
   - Era 1 `"Multiracial"` = Era 2 suffix `u` = Eras 3+ `"Multi-Racial"`.
   - Era 1 `"Approximate Class Size Amer/Alaskan Native"` drops the `"Native"` word — this is a column-name inconsistency in Era 1 itself (not an error to correct, but loaders must use exact literal column names).

6. **Zero-padding of geography codes.** Eras 3+ preserve `"601"` as 3-digit string when read with `schema_overrides={'SCHOOL_DSTRCT_CD': pl.Utf8, 'INSTN_NUMBER': pl.Utf8}`. **Without `schema_overrides`**, Polars infers `SCHOOL_DSTRCT_CD` as Int64 and fails on rows where the value is `"ALL"` (state-level rows). Always supply these overrides. `INSTN_NUMBER` is 4-digit zero-padded in CSV (`"0100"`); Int cast would strip leading zeros.

7. **`ALL` values in key columns.** Eras 3+ use the literal string `"ALL"` in `SCHOOL_DSTRCT_CD` (state rows) and `INSTN_NUMBER` (district + state rows) to mean "aggregated". The transform must map these to null (or a dedicated state/district marker) before joining to dimension tables. Era 1–2 use `SysSchoolID` with `":ALL"` suffix — parse the colon-delimited string to decompose into `district_code` and `school_code`, then convert `"ALL"` segments to null.

8. **Suppression markers.** Four distinct encodings across eras:
   - 2004–2009 (Era 1 AND the first three Era-2 files): **zero values** — `Number Taken Asian = 0`, `Graduation Rate Asian = 0`. Indistinguishable from real zeros. (Measured: 2007–2009 contain zero `Too few Students` cells and zero blanks; an earlier revision of this doc attributed the marker to all of 2007–2010.)
   - 2010 only: string **`"Too few Students"`** in every metric cell of the suppressed subgroup.
   - Eras 3–4 (2011–2016) and 2017–2020: **blank cells / null** on suppressed subgroups.
   - Eras 2021–2024: literal string **`"TFS"`** (Too Few Students — abbreviation of Era 2's text) in `PROGRAM_TOTAL`, `PROGRAM_PERCENT`, `TOTAL_COUNT`.
   - All string markers must be normalized to null via `pl.col(...).cast(pl.Float64, strict=False)`.

9. **Missing `TOTAL_COUNT` in Era 4 (2012–2016).** The cohort denominator (`TOTAL_COUNT`) is not in the source for these years. Either compute as `round(PROGRAM_TOTAL / (PROGRAM_PERCENT / 100.0))` when both are non-null, or leave null — document which choice is made.

10. **Double-aggregation rows (`DETAIL_LVL_DESC = State`).** State rows have `SCHOOL_DSTRCT_CD = "ALL"`, `SCHOOL_DSTRCT_NM = "All Column Values"`, `INSTN_NUMBER = "ALL"`, `INSTN_NAME = "All Column Values"` in Eras 3+, and `SysSchoolID = "ALL:ALL"`, `SchoolName = "State Of Georgia"` (or `"State Schools"` for the special statewide-charter aggregate) in Eras 1–2. Note: **every wide-era file (2004–2010)** has both `ALL:ALL → State Of Georgia` AND `799:ALL → State Schools` as separate aggregates (an earlier revision of this doc said only 2005) — the latter represents the state-school virtual district (district code 799 is genuine), not a full state aggregate; it is a district-level row. Keep only the true `ALL:ALL` row as the state-level total.

11. **Name drift for schools / districts.** `INSTN_NAME` for the same school changes across years (e.g., `"APS-Forrest Hills Academy"` vs `"APS-Forrest Hills Academey"` with typo in 2014). Fact tables should join on `INSTN_NUMBER`, not `INSTN_NAME` — put the canonical name in the schools dimension (latest-name-wins). Same for `SCHOOL_DSTRCT_NM` — district code `SCHOOL_DSTRCT_CD` is the stable key.

12. **`GRADES_SERVED_DESC` has ≤42 distinct values per file.** Useful for schools-dimension metadata (grade span served), but not a fact-table column. Candidate for school dimension attribute (latest year wins), not retained in the fact table.

13. **`#RPT_NAME` column (Eras 6).** Constant value `"Graduation Rate"` in every row — a report-type label with no information. Drop entirely in the transform.

14. **Percentage scale is 0–100 across all eras.** Confirmed by max values (100.0) and mean values (70–90%) in every era sampled. Store as 0–100 percent (per project standards).

15. **Demographic set changes over time.** 2004–2017 have 15 demographic labels; `Active Duty`, `Foster`, `Homeless` are added starting with the **2018** file (not 2020 as an earlier revision claimed), giving 18 labels in 2018–2020 and 2022–2024; **2021 has 17** (`Limited English Proficient` absent that year only, returning in 2022). Any backfill into earlier years must be coded as null (subgroup did not exist in published data), not as zero.

16. **2010 migrant internal inconsistency (3 rows).** The only rate-vs-counts mismatches in any year (max deviation elsewhere: 0.0005, i.e. 1-decimal percent rounding) are the three non-suppressed migrant rows of 2010.xls: the state row `ALL:ALL` (`GradRate_P_mig=65.5`, `N_mig=110`, `S_mig=110`) and Colquitt County `635:ALL` / `635:1554` (`P=69.6`, `N=23`, `S=23`). N equals S yet the rate is not 100%% — the published numerator/denominator do not reconcile with the published rate. Each value is individually possible; preserve as published and document (data-cleaning-standards §4b extreme-but-conceivable).

17. **Wide-era duplicate `SysSchoolID` rows.** 2004.csv carries 50 duplicated SysSchoolIDs (artifact of the same malformed export as the corrupt row) and 2009.xls carries 2 (`768:ALL` Ivy Prep, `770:ALL` Scholars Academy — one twin missing the name). Verified: every twin pair is value-identical on all 45 metric columns after suppression-aware casting (the one pre-cast difference, `751:194`, is empty-string vs null cells only), so dedup can keep either twin without a value judgment.

18. **2023–2024 partial suppression.** 369 rows (2023: 295 School + 74 District) and 339 rows (2024: 271 School + 68 District) publish `TOTAL_COUNT` while `PROGRAM_TOTAL` and `PROGRAM_PERCENT` are `TFS`-suppressed. In every other year the three metrics are suppressed together. `PROGRAM_TOTAL` and `PROGRAM_PERCENT` are always co-suppressed in every year (zero rows anywhere with exactly one of the two missing).

19. **2004 covers every school, mostly empty.** 2004.csv enumerates 2,270 valid entities (2,082 school rows) — every Georgia public school including elementary/middle schools with no graduating cohort — but only ~510 entities carry metric values; the rest are blank (≈77%% of rows). 2005 onward enumerate only entities with cohorts (522–576 rows). The blank cells are in-band empties, not read loss (raw line count = parsed rows = 2271). From 2011 onward, every published `PROGRAM_TOTAL`/`TOTAL_COUNT` value is ≥ 10 (GOSA's n=10 reporting threshold, verified per file).

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| SysSchoolID (Eras 1–2) | fact_key (derived) | `district_code`, `school_code` | Split on `:` — left half → district_code (strip `"ALL"` → null), right half → school_code (strip `"ALL"` → null). `"ALL:ALL"` → both null, detail level = state. |
| SchoolName / SchoolNme (Eras 1–2) | dimension_attribute | — | School / district / state entity name — goes into the schools or districts dimension table; not retained in fact table. |
| SCHOOL_DSTRCT_CD (Eras 3+) | fact_key | `district_code` | FK to districts dimension. `"ALL"` → null. Preserve as 3-digit zero-padded string. |
| SCHOOL_DSTRCT_NM (Eras 3+) | dimension_attribute | — | `district_name` in districts dimension. `"All Column Values"` → null. |
| INSTN_NUMBER (Eras 3+) | fact_key | `school_code` | FK to schools dimension. `"ALL"` → null. Preserve as 4-digit zero-padded string. |
| INSTN_NAME (Eras 3+) | dimension_attribute | — | `school_name` in schools dimension. `"All Column Values"` → null. |
| DETAIL_LVL_DESC (Eras 3+) | fact_categorical | `detail_level` | Values `State`, `District`, `School` normalized to `state`, `district`, `school` (snake_case). Can alternatively be derived from presence of non-null keys. |
| LONG_SCHOOL_YEAR (Eras 3+) | fact_key (derived) | `year` | Parse `"YYYY-YY"` → ending calendar year (integer). Eras 1–2: derive from filename. |
| (filename) (Eras 1–2) | fact_key (derived) | `year` | Extract from filename (e.g., `graduation_rate_4_year_cohort_2010.xls` → 2010). |
| LABEL_LVL_1_DESC (Eras 3+) | fact_key | `demographic` | Strip `"Grad Rate -"` prefix and map to canonical demographic name per demographics dimension. |
| Graduation Rate {demo} (Era 1) | fact_metric | `graduation_rate_pct` | Float, 0–100. Era 1 zero values indistinguishable from suppression — flag or leave as-is. |
| Number Taken {demo} (Era 1) | fact_metric | `graduates` | Integer count of graduating cohort members. |
| Approximate Class Size {demo} (Era 1) | fact_metric | `cohort_size` | Integer cohort size (denominator). |
| GradRate_P* (Era 2) | fact_metric | `graduation_rate_pct` | Cast from String (handle `"Too few Students"` → null). |
| GradRate_N* (Era 2) | fact_metric | `graduates` | Cast from String (handle `"Too few Students"` → null). |
| GradRate_S* (Era 2) | fact_metric | `cohort_size` | Cast from String (handle `"Too few Students"` → null). |
| PROGRAM_PERCENT (Eras 3+) | fact_metric | `graduation_rate_pct` | Float 0–100. Cast from String (handle `"TFS"` → null) in 2021+. |
| PROGRAM_TOTAL (Eras 3+) | fact_metric | `graduates` | Integer. Cast from String (`"TFS"` → null) in 2021+. |
| TOTAL_COUNT (Era 3, Era 5, Era 6) | fact_metric | `cohort_size` | Integer. Cast from String (`"TFS"` → null) in 2021+. **Absent in Era 4 (2012–2016)** — compute as `round(graduates / (rate/100))` or leave null. |
| GRADES_SERVED_DESC (Eras 3+) | dimension_attribute | — | `grades_served` in schools dimension (latest year wins). Not retained in fact table. |
| #RPT_NAME (Era 6) | not_in_gold | — | Constant `"Graduation Rate"` — no information content. |
