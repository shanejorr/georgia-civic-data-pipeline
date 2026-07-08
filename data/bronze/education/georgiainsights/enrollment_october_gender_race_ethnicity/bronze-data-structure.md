# enrollment_october_gender_race_ethnicity - Bronze Data Structure

## Overview

- Topic: enrollment_october_gender_race_ethnicity
- Source: georgiainsights
- Files: 34 files spanning 2010-2026 (one CSV per year per detail level: District + School, 17 years x 2 files)
- Unreadable files: none
- Year representation: Year is encoded ONLY in the filename (`Fiscal Year2010-1` ... `Fiscal Year2026-1`) and in the file's preamble (lines 2-3, e.g., line 2 = `"FTE Enrollment by Race/Ethnicity and Gender - Fiscal Year 2026-1 Data Report"`, line 3 = `" October 7, 2025 (FTE 2026-1)"`). There is no year column inside the data — every row in `Fiscal Year2026-1` is implicitly fiscal year 2026 / school year 2025-2026.
- Filename-to-data year offset: same (filename `YYYY-1` = GaDOE fiscal year `YYYY` = fall term of school year `(YYYY-1)-YYYY`, collected in early October of calendar year `YYYY-1`). Verified by the in-file preamble: the 2026-1 file was collected "October 7, 2025". The trailing `-1` denotes Cycle 1 (the October FTE student count, distinguishing this dataset from the March Cycle 3 enrollment).
- Detail levels: state (System ID = `""`, System Name = `"State-Wide"`), district (in District files), school (in School files). The District and School counts live in **separate CSV files per year**; there are no district-aggregate rows in the School files (see ETL Considerations).
- Percentage scale: N/A. All metric columns are integer student counts, not rates or percentages.
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: Georgia Insights (GaDOE) public data downloads — exact page URL not recorded at acquisition time
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2010-1 District.csv | 689ff8c0954ac582b773ade0c2a83f07137dffc2efb58d053b6cacbae6e57a8d |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2010-1 School.csv | ea6f4a9fa7a58cdb4063fec3b5655cb69c4d822be6440505594155aaafe10636 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2011-1 District.csv | b46aa2a04898fa22540c0e521bf499dfa9c2af9ecdadf6b5a028118b7896a884 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2011-1 School.csv | 320cacda212a3400eefbc580f5219a7a359246b8eb2cdd08eb2888e04dceab84 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2012-1 District.csv | 2084995ec910a518a4f8db2e41980de462af5a4e6db96829ff949d2eecf7df21 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2012-1 School.csv | 03f86303d085e460d067b151fa790621d721ef9f67ce020a1bd16a32cd3ee757 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2013-1 District.csv | 394feb9114d867728ae695ddf4e40040b7f8c3604e5f48c35a072ba7a940aa76 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2013-1 School.csv | 65d4b7d3f61d86f908e459a9777da7f33c337aec15fcdab2074764a497a3a720 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2014-1 District.csv | 95ba2ff0ecb4a2c0b7478c92e5bbf8264f7e75a55dd310d296fe6624ec8fc640 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2014-1 School.csv | bfce26800587a2abceb6d3d20b2d58ac975d5d598edae3d55e918c25817123e0 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2015-1 District.csv | 7911ab73c7931199a440ad7d9ab8922d297555264c4aa13419cc3e3d3acd37c9 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2015-1 School.csv | 85cc745c4706d3ccdaf982a51c1c5852953ab8eded83c8d4a57e5a89150ae1c1 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2016-1 District.csv | 41e05a8b635aa5e944eead18c049eeb4a9fef9836c24556a3a41569f3e0485b0 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2016-1 School.csv | e2d74c8c0d3c6d87c62800cbcc9c7c77bd7c4d4130e3be2d3de8a857e9ab3a26 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2017-1 District.csv | f28ca8eb1df8fe52fa7c502864a0fc139f64035b0b90e1045c301e0f57e1d7e3 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2017-1 School.csv | dd78198b3cb2f9fc5994fb9aa092535f5b7b313717c5812c58de099e2ec0997b |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2018-1 District.csv | 038a9ba8e24ea3c530a342e1bbd505ae2d562e8c6ab8a45f447d11007cd2d7c0 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2018-1 School.csv | 858b1828e493b2324c74c5df4d2a46c2731ee1c7c0dac3a1497979f0b46bf6a9 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2019-1 District.csv | a1341c248598e7fd7a419bbf9bc2a04647b5c48971da453e34829eb9a14c2078 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2019-1 School.csv | 8a70efb5c9edf3e392f57736e71e188acb5e9d1f69b19dbf861046ffe288f0c3 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2020-1 District.csv | 0c1bc91fd2cc5abe2cb8ddf793697d699301946e03520e8bf106c2b7307bd77a |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2020-1 School.csv | c69fdec0eb6af86e31186cbe18340ab2e190b39aff0d21c676c9708e2f700e07 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2021-1 District.csv | 93f00cacca7c29a2916b20ddd5a571b5aee7706396813b7f04f5ccb9c838fbe0 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2021-1 School.csv | 03b6028bb20f89e86c866cf8a3635150ea647dffea5423b8496701aef44cd2be |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2022-1 District.csv | 653050c6132f1865909c55a9f142977102fabb964e1f79913d69f9399f123eaf |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2022-1 School.csv | f089956635fb5169fc2bbd517f5c0126b1b0f9118c79299a8b35268ebd120050 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2023-1 District.csv | c5ab528831709675ef1be3c9b4eda14b1e97ae6dbfcfd584a9b0039217679076 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2023-1 School.csv | 08ad4c5d8a101673dd053846b123d5f0e60ba2227af74e3fd833403441b55bf8 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2024-1 District.csv | 148b3bd512dd0de4b5962bf8ce183abd0039e7604b1cc993f8ed2b60eac5c292 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2024-1 School.csv | b987a995eeee0cff376dd493c1b5436e895ddcc7fe27ea8b0a75b064b2973873 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2025-1 District.csv | def9d6ba28cf43342ae80793af130c27a87f3cbe93e28a0e3ae196b57afbf93d |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2025-1 School.csv | b38dc2a1958ac49a2c82610f02c32a822a6d06ea471c1d545df35ecb3bcc0a4d |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2026-1 District.csv | 279ee0066c1a935e64cfd3684c6fe268c9021cecc42ce65a0526c488b5e2aefa |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2026-1 School.csv | 66728a1bfe7e641f2ecc699ef11e64f69a4248cdc42914e243be3ef651149209 |

## Summary

GaDOE October (FTE Cycle 1) headcount of public school students broken out by gender and race/ethnicity. Each row reports a Female / Male / Total student count for one of seven mutually-exclusive race/ethnicity buckets:

- `Ethnic Hispanic` — students of Hispanic origin (treated as a separate ethnicity bucket, NOT overlapping with the six race buckets — see ETL Considerations).
- `Race AmericanIndian` — non-Hispanic American Indian / Alaska Native.
- `Race Asian` — non-Hispanic Asian.
- `Race Black` — non-Hispanic Black / African American.
- `Race Pacific Islander` — non-Hispanic Native Hawaiian / Pacific Islander.
- `Race White` — non-Hispanic White.
- `Two or more Races` — non-Hispanic students reporting two or more races.

The three `Gender` rows (`Female`, `Male`, `Total`) for any single (year, geography) are arithmetically related: `Total == Female + Male` for every race column where neither value is suppressed (verified cell-by-cell at the 2025 and 2026 state level, all seven race columns). The seven race/ethnicity columns also sum to total enrollment per gender (e.g., 2026 state Total: `4,294 + 92,062 + 616,403 + 1,694 + 576,765 + 87,879 (race) + 335,934 (Hispanic) = 1,715,031` students, matching Georgia's published FTE October 2025 total enrollment).

This is the **October / fall** snapshot (Cycle 1 = first semester count). The companion topic `enrollment_march_gender_race_ethnicity` reports the same breakdown from the March Cycle 3 spring count.

## Eras

### Era 1: 2010-2026 (single era)

Every file in the topic uses the **same column set across all 17 years** with no schema drift. The only structural difference is between detail levels: District files have 10 columns, School files have the same 10 plus a `School ID` column (11 total). Both detail levels share the identical 7 race/ethnicity metric columns for the entire range.

**Note on column header whitespace.** Bronze headers contain inconsistent leading whitespace introduced by the source export — every column name except `System ID` and `School ID` carries one or two leading spaces, and `Two or more Races` has a trailing space too. Notably, the `Gender` header has **1 leading space in District files but 2 leading spaces in School files**. Headers must be referenced by their exact bytes (or stripped) when reading; partial-substring matches are unreliable. The transform should `.strip()` all headers on load.

| Column | Description |
|--------|-------------|
| `System ID` | String. 3-digit GOSA district code (e.g., `"601"`) for standard districts, 7-digit charter-system code (e.g., `"7820108"`) for charter authorizers, or empty string `""` for the state-aggregate row. Verified across all 34 files: 185 distinct 3-digit codes and 71 distinct 7-digit codes. |
| ` System Name` | String. District/system name in title case (e.g., `"Appling County"`, `"Atlanta Public Schools"`, `"State Specialty Schools II- Cirrus Charter Academy"`), or `"State-Wide"` for the state row. Leading space in header. |
| `School ID` | **School files only.** String of the form `"NNNN-School Name"` where `NNNN` is the 4-digit GOSA school code (e.g., `"0103-Appling County High School"`), or `"State-Wide"` for the state-aggregate rows. The numeric prefix and the school name are jammed into a single column and must be split during transform. Verified: 100% of non-state school IDs match `^\d{4}-` across all 17 years. |
| `  Gender` (School) / ` Gender` (District) | String. One of `Female`, `Male`, `Total` (consistent across all 34 files). Each (year, geography) appears as exactly three rows. Note the asymmetric leading-space count between District (1 leading space) and School (2 leading spaces) files. |
| `  Ethnic Hispanic` | String holding integer counts; suppression marker `*` for small cells. Two leading spaces in header. |
| `  Race AmericanIndian` | Same dtype/suppression pattern. Heavily suppressed at the school level (~99.9% `*` in 2025 and 2026 school files). |
| `  Race Asian` | Same dtype/suppression pattern. |
| `  Race Black` | Same dtype/suppression pattern. Lowest suppression rate (~13.7% at 2026 school level). |
| `  Race Pacific Islander` | Same dtype/suppression pattern. Heavily suppressed (~99.9% `*` at school level). |
| `  Race White` | Same dtype/suppression pattern. |
| `  Two or more Races ` | Same dtype/suppression pattern. Trailing space in header. |

#### Sample Data (2026 School file)

```text
=== State rows (top 3 rows) ===
System ID="" System Name="State-Wide" School ID="State-Wide" Gender=Female Hispanic=164663 AI=2134  Asian=44632 Black=304856 PI=858  White=279142 Two=43468
System ID="" System Name="State-Wide" School ID="State-Wide" Gender=Male   Hispanic=171271 AI=2160  Asian=47430 Black=311547 PI=836  White=297623 Two=44411
System ID="" System Name="State-Wide" School ID="State-Wide" Gender=Total  Hispanic=335934 AI=4294  Asian=92062 Black=616403 PI=1694 White=576765 Two=87879

=== Random school rows (seed=42) ===
System ID="737" System Name="Tift County"             School ID="3052-Northeast Middle School"          Gender=Male   Hispanic=86 AI=* Asian=* Black=127 PI=* White=128 Two=*
System ID="644" System Name="DeKalb County"           School ID="3056-Flat Shoals Elementary School"    Gender=Male   Hispanic=* AI=* Asian=* Black=178 PI=* White=*   Two=*
System ID="792" System Name="Valdosta City"           School ID="0106-J. L. Lomax Elementary School"    Gender=Female Hispanic=51 AI=* Asian=* Black=214 PI=* White=*   Two=*
System ID="706" System Name="Muscogee County"         School ID="5069-Wesley Heights Elementary School" Gender=Female Hispanic=* AI=* Asian=* Black=140 PI=* White=*   Two=*
System ID="726" System Name="Griffin-Spalding County" School ID="4052-Orrs Elementary School"           Gender=Male   Hispanic=62 AI=* Asian=* Black=129 PI=* White=32  Two=*
```

#### Sample Data (2026 District file, selected rows)

```text
=== State rows (top 3 rows) ===
System ID="" System Name="State-Wide" Gender=Female Hispanic=164663 AI=2134 Asian=44632 Black=304856 PI=858  White=279142 Two=43468
System ID="" System Name="State-Wide" Gender=Male   Hispanic=171271 AI=2160 Asian=47430 Black=311547 PI=836  White=297623 Two=44411
System ID="" System Name="State-Wide" Gender=Total  Hispanic=335934 AI=4294 Asian=92062 Black=616403 PI=1694 White=576765 Two=87879

=== Random district/charter rows (seed=42) ===
System ID="7830611" System Name="State Specialty Schools II- Cirrus Charter Academy"   Gender=Total  Hispanic=* AI=* Asian=* Black=457   PI=* White=*   Two=*
System ID="675"     System Name="Henry County"                                          Gender=Male   Hispanic=2775 AI=61 Asian=622 Black=13817 PI=21 White=2774 Two=1184
System ID="792"     System Name="Valdosta City"                                         Gender=Male   Hispanic=397 AI=* Asian=62 Black=3111  PI=* White=339 Two=149
System ID="769"     System Name="Chickamauga City"                                      Gender=Male   Hispanic=19 AI=* Asian=* Black=*     PI=* White=591 Two=16
System ID="7830103" System Name="State Specialty Schools II- Statesboro STEAM Academy" Gender=Total  Hispanic=* AI=* Asian=* Black=100   PI=* White=81  Two=*
```

Note the 7-digit `System ID` values (e.g., `7820108`, `7830611`) represent state-specialty charter authorizers / charter-system aggregate codes that appear ONLY in District files. They are not individual schools — they are the district-level aggregate for a charter-system group. The regular 3-digit codes (e.g., `601` Appling County, `675` Henry County) are the conventional GOSA district codes.

#### Statistics — Row Counts Per File

| Year | District file rows | Districts (incl. charters) | School file rows | Schools |
|-----:|-------------------:|---------------------------:|-----------------:|--------:|
| 2010 |   561 | 186 | 6,816 | 2,268 |
| 2011 |   597 | 198 | 6,972 | 2,320 |
| 2012 |   603 | 200 | 6,969 | 2,319 |
| 2013 |   609 | 202 | 6,921 | 2,303 |
| 2014 |   606 | 201 | 6,882 | 2,290 |
| 2015 |   606 | 201 | 6,888 | 2,292 |
| 2016 |   621 | 206 | 6,879 | 2,289 |
| 2017 |   630 | 209 | 6,885 | 2,292 |
| 2018 |   642 | 213 | 6,903 | 2,298 |
| 2019 |   645 | 214 | 6,912 | 2,301 |
| 2020 |   651 | 216 | 6,906 | 2,299 |
| 2021 |   669 | 222 | 6,924 | 2,305 |
| 2022 |   672 | 223 | 6,942 | 2,311 |
| 2023 |   684 | 227 | 6,948 | 2,313 |
| 2024 |   708 | 235 | 6,972 | 2,321 |
| 2025 |   708 | 235 | 6,975 | 2,322 |
| 2026 |   714 | 237 | 6,951 | 2,315 |

District row counts are always exactly `3 + 3 × number_of_districts` (Female / Male / Total per district, plus 3 state-aggregate rows). School row counts are `3 + 3 × number_of_schools` (the same triple per school plus 3 state-aggregate rows). The school counts drift as schools close or open across years.

#### Describe (2026 District file, race columns cast to Int64 with `*` → null)

```text
┌────────────┬──────────────┬────────────┬───────────┬───────────┬────────────┬────────────┬────────────┬────────────┐
│ statistic  │ Hispanic     │ AI         │ Asian     │ Black     │ PI         │ White      │ Two        │            │
├────────────┼──────────────┼────────────┼───────────┼───────────┼────────────┼────────────┼────────────┼────────────┤
│ count      │ 578          │ 97         │ 274       │ 677       │ 54         │ 603        │ 541        │            │
│ null_count │ 136          │ 617        │ 440       │ 37        │ 660        │ 111        │ 173        │            │
│ mean       │ 2,322.6      │ 158.0      │ 1,334.0   │ 3,640.0   │ 102.6      │ 3,824.9    │ 647.3      │            │
│ std        │ 17,464       │ 524        │ 7,162     │ 29,324    │ 270        │ 28,785     │ 4,645      │            │
│ min        │ 15           │ 15         │ 15        │ 15        │ 15         │ 15         │ 15         │            │
│ max        │ 335,934      │ 4,294      │ 92,062    │ 616,403   │ 1,694      │ 576,765    │ 87,879     │            │
└────────────┴──────────────┴────────────┴───────────┴───────────┴────────────┴────────────┴────────────┴────────────┘
```

**Important**: the `min` of every race column is exactly **15** — verified across all 34 files. Any (race, geography, gender) cell with a true count below 16 is suppressed with `*`. This is a standard GaDOE small-cell privacy rule for FTE enrollment data.

#### Null Counts

Every column in every file has **0 nulls** when read with `infer_schema_length=0` (all-string mode). The "missing" semantics in this dataset are encoded as:

- `System ID == ""` (empty string) for the state-aggregate row.
- `*` for suppressed numeric cells (counts below 15).

There are no actual `None`/null values anywhere in any bronze file.

#### Categorical Columns

| Column | Distinct Values |
|--------|-----------------|
| `Gender` (after strip) | `Female`, `Male`, `Total` (3 values, identical across all 34 files) |
| `System Name` | District names in title case (e.g., `Appling County`, `Atlanta Public Schools`) plus the literal `State-Wide`. ~238 distinct district/system names appear in the most recent (2026) school file; the roster grows from 186 districts in 2010 to 237 in 2026 as new charter systems appear. |
| `System ID` | Either empty string `""` (state row), a 3-digit standard district code (`"601"`, `"644"`, ...), or a 7-digit charter/school-system code (`"7820108"`, `"7830649"`, ...). Across all 17 years: 185 distinct 3-digit codes + 71 distinct 7-digit codes = 256 total. |
| `School ID` (School files only) | Either `State-Wide` (state-aggregate row) or `NNNN-School Name` (4-digit code prefix). Verified 100% conformance to the `^\d{4}-` pattern across all 17 years of school files. 2,316 distinct school IDs in the 2026 file. |

#### Suppression Markers

| Column | Marker | Where it appears (2026 figures) |
|--------|--------|---------------------------------|
| `Ethnic Hispanic` | `*` (asterisk) | Both detail levels, every year. ~19% of rows at district level (2026), ~20% at school level (2026). Historical range: 17–20% district, 20–46% school (pre-2015 had substantially higher school-level suppression). |
| `Race AmericanIndian` | `*` | Both detail levels, every year. ~86% at district level, ~99.9% at school level. |
| `Race Asian` | `*` | Both detail levels, every year. ~62% at district level, ~78% at school level. |
| `Race Black` | `*` | Both detail levels, every year. ~5% at district level, ~14% at school level. |
| `Race Pacific Islander` | `*` | Both detail levels, every year. ~92% at district level, ~99.9% at school level. |
| `Race White` | `*` | Both detail levels, every year. ~16% at district level, ~25% at school level. |
| `Two or more Races ` | `*` | Both detail levels, every year. ~24% at district level, ~48% at school level. Suppression percentage has been decreasing over time as the multi-racial population grows. |

Verified across all 34 files: `*` is the **only** non-numeric value that appears in any of the 7 race/ethnicity columns. There are no `TFS`, `N/A`, or other markers — Georgia Insights uses a single `*` convention for this dataset.

Suppression is **column-by-column, not row-by-row** — a single row can have some race columns suppressed (`*`) and others numeric. This differs from the attendance_dashboard topic where suppression is all-or-nothing across the metric columns.

## ETL Considerations

### Multi-File-Per-Year Concatenation

For each year, the District counts and School counts live in **two separate CSV files**. The transform must read both files (e.g., `Year2026-1 District.csv` and `Year2026-1 School.csv`) and union them with a synthesized `detail_level` column:

- `District.csv` rows become `detail_level = "district"` (or `"state"` if `System ID == ""`).
- `School.csv` rows become `detail_level = "school"` (or `"state"` if `System ID == ""`).

Note that both the District file and the School file each contain their own copy of the 3 state-aggregate rows (Female/Male/Total). They report the same underlying state totals — verified for 2025 and 2026 that every (gender, race) cell of the state row in the District file equals the corresponding cell in the School file. The transform must **deduplicate** the state rows so the final state-level fact emits exactly 3 rows per year, not 6. (After the Total row is also dropped per §"Total Gender Row Is Redundant" below, each year contributes 2 state rows × 7 race buckets = 14 state fact rows.)

### CSV Preamble Must Be Skipped

Every CSV begins with a 4-line preamble:

```text
Georgia Department of Education
FTE Enrollment by Race/Ethnicity and Gender - Fiscal Year YYYY-1 Data Report
"October D, YYYY-1 (FTE YYYY-1)"          <-- note: early years use "Oct D" and some years have a leading space inside the quotes
{blank line}
```

Headers start on line 5. Use `pl.read_csv(path, skip_rows=4, ...)`. Do not parse the preamble date for the year (the filename is more reliable and matches exactly), but do verify line 2 starts with `"FTE Enrollment by Race/Ethnicity and Gender"` as a sanity check.

### Column Header Whitespace

Bronze headers carry stray leading and trailing spaces that vary by column **and by detail level**:

```text
District files (10 columns):
  'System ID'              (no whitespace)
  ' System Name'           (1 leading space)
  ' Gender'                (1 leading space — NOTE: different from School files)
  '  Ethnic Hispanic'      (2 leading spaces)
  '  Race AmericanIndian'  (2 leading spaces)
  '  Race Asian'           (2 leading spaces)
  '  Race Black'           (2 leading spaces)
  '  Race Pacific Islander' (2 leading spaces)
  '  Race White'           (2 leading spaces)
  '  Two or more Races '   (2 leading spaces, 1 trailing space)

School files (11 columns):
  'System ID'              (no whitespace)
  ' System Name'           (1 leading space)
  'School ID'              (no whitespace — School files only)
  '  Gender'               (2 leading spaces — NOTE: different from District files)
  '  Ethnic Hispanic'      (2 leading spaces)
  '  Race AmericanIndian'  (2 leading spaces)
  '  Race Asian'           (2 leading spaces)
  '  Race Black'           (2 leading spaces)
  '  Race Pacific Islander' (2 leading spaces)
  '  Race White'           (2 leading spaces)
  '  Two or more Races '   (2 leading spaces, 1 trailing space)
```

The transform must `.strip()` all column headers immediately after `read_csv()` so downstream code can reference them by clean names. Failing to strip will produce silent column-name mismatches — especially dangerous because the `Gender` header differs between the District and School files (1 vs 2 leading spaces).

### Year Is Not in the Data

There is no year column. The transform must derive `year` from the filename. Recommended pattern:

```python
import re
m = re.search(r"Fiscal Year(\d{4})-1", path.name)
year = int(m.group(1))
```

The `-1` suffix (Cycle 1 = October count) is implicit in the topic name. The companion topic `enrollment_march_gender_race_ethnicity` uses `-3` (Cycle 3 = March count).

**Fiscal-year semantics.** `Fiscal Year YYYY-1` = Cycle 1 (October) of GaDOE fiscal year `YYYY`, which is the **fall term of school year `(YYYY-1)-YYYY`**. For example, the `Year2026-1` file was collected October 7, 2025, and represents the fall 2025 enrollment count of the 2025-2026 school year. The gold `year` column should store the filename year `YYYY` (consistent with the rest of the education domain using GaDOE fiscal year as the year key).

### School ID Splitting

The `School ID` column packs both the school code and the school name into a single string of the form `NNNN-Name` (e.g., `"0103-Appling County High School"`). The transform must split on the first `-`:

```python
df = df.with_columns(
    pl.col("school_id_combined").str.extract(r"^(\d{4})-(.+)$", 1).alias("school_code"),
    pl.col("school_id_combined").str.extract(r"^(\d{4})-(.+)$", 2).alias("school_name_raw"),
)
```

The `school_code` portion goes into the fact table; the `school_name_raw` portion belongs only in the schools dimension and should be `title_case_name()`-ed there. Note that some school names may already contain hyphens (e.g., `"Griffin-Spalding"` appears as a *district* name so hyphens do appear in other name fields), so split on the **first** hyphen only.

State-aggregate rows have `School ID == "State-Wide"` (no leading 4-digit code) — the regex above will produce nulls for those rows, which is the correct behavior for state rows that get nulled out anyway (per the geography-nulling rules below).

### Geography Sentinels

State and aggregate rows use these patterns (verified across all 34 files):

| Detail Level | bronze pattern | district_code | school_code |
|-------------|----------------|---------------|-------------|
| state | `System ID == ""` AND `System Name == "State-Wide"` (and `School ID == "State-Wide"` in school files) | NULL | NULL |
| district (in District files) | `System ID == digits` | 3-digit `zfill(3)` or 7-digit as-is | NULL |
| school (in School files) | `System ID == digits` AND `School ID matches "^\d{4}-"` | 3-digit `zfill(3)` or 7-digit as-is | `zfill(4)` |

There are no `(System ID present, School ID == "State-Wide")` rows in any School file — verified across all 17 years. District aggregates only live in the District files.

Use `null_aggregate_geography()` from `src/utils/transformers.py` with the standard `EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"]`.

### Charter/Specialty System IDs (7-digit)

`System ID` comes in two valid lengths: 3-digit standard district codes (185 distinct) and 7-digit charter-system / state-specialty codes (71 distinct). Both appear in District files. 7-digit codes represent charter authorizers that report their schools as a group under a single "system". They are NOT individual schools — they are district-level aggregates for a charter-system.

When applying `zfill(3)` for padding, apply it only to codes that are already ≤ 3 characters. The safer pattern:

```python
pl.when(pl.col("district_code_raw").str.len_chars() <= 3)
  .then(pl.col("district_code_raw").str.zfill(3))
  .otherwise(pl.col("district_code_raw"))
```

Or equivalently, skip padding for 7-digit codes since they are already longer than 3 characters. (The existing `read_bronze_file()` / geography-normalization utilities in `src/utils/transformers.py` should be reviewed for handling this — the attendance_dashboard and enrollment_march_gender_race_ethnicity topics have already faced this same pattern.)

### ID Padding

`System ID` is already 3-digit zero-padded for standard districts (`"601"`) and 7-digit for charters (`"7820108"`). Apply `zfill(3)` per education domain conventions to be defensive (a no-op for 3-digit and 7-digit codes alike). Cast to `pl.Utf8` first.

`School ID` code portion (after splitting) is 4-digit (`"0103"`). Apply `zfill(4)` to be defensive. Cast to `pl.Utf8` first.

The empty string `""` for state rows must be mapped to NULL **before** zfill is applied (otherwise `"".zfill(3)` would produce `"000"` and silently masquerade as a district).

### Suppression Handling

The single suppression marker `*` appears in every race/ethnicity column. Use `cast(pl.Int64, strict=False)` after reading — `*` will coerce to null. Alternatively, register `*` as a null marker via `read_bronze_file()` from `src/utils/readers.py` (which already handles common suppression markers including `*`).

Per the data-cleaning standards, all suppressed values must become NULL in gold — do not impute, do not drop the row, do not retain the `*` literal. Analysts can detect suppressed cells downstream by checking for NULL in the student_count column.

The 15-student threshold is implicit in the data and worth documenting in the gold data dictionary: any NULL student_count in the fact table means the true count was < 15 (inclusive lower bound 15 verified).

### Hispanic Is a Separate (Non-Overlapping) Ethnicity

Critical interpretation: `Ethnic Hispanic` is a **non-overlapping** ethnicity bucket alongside the six race buckets, not an overlay. Verified by summing the 7 race/ethnicity columns for the 2026 state Total row: `4,294 + 92,062 + 616,403 + 1,694 + 576,765 + 87,879 (6 race columns) + 335,934 (Hispanic) = 1,715,031` — which matches Georgia's published FTE October 2025 total enrollment (~1.72M reported by GaDOE for the 2025-2026 school year).

This means the gold demographic mapping should treat Hispanic as one of seven mutually exclusive race/ethnicity values, NOT as a Hispanic-of-any-race overlay. Use the global demographic codes:

| Bronze column (stripped) | Gold `demographic` code |
|--------------------------|--------------------------|
| `Ethnic Hispanic` | `hispanic` |
| `Race AmericanIndian` | `native_american` |
| `Race Asian` | `asian` |
| `Race Black` | `black` |
| `Race Pacific Islander` | `pacific_islander` |
| `Race White` | `white` |
| `Two or more Races` | `multiracial` |

All seven codes already exist in `data/gold/_dimensions/demographics.parquet`. **No new demographic codes are required** for this topic — unlike the attendance_dashboard topic which combined Asian + Pacific Islander into a single bronze bucket, this topic keeps them separate, matching the global dimension exactly.

The `Gender` column maps to `female`, `male` (already in the dimension). The `Total` gender row should NOT be emitted to gold — it is redundant (always equals `Female + Male` for non-suppressed cells) and would create double-counting if any analyst aggregated the gold without filtering. **Drop all `Gender == "Total"` rows during transform.**

### Wide-by-Race Format Requires Unpivoting

The bronze data is wide-by-race-column (each row has one Gender and seven race-count columns). Per the data-cleaning standards (Tidy Data Format, §9), the transform must **unpivot** the seven race/ethnicity columns into rows so that each row in gold represents one (year, geography, gender, demographic) observation with a single `student_count` metric.

Recommended pattern using `df.unpivot()`:

```python
df = df.unpivot(
    index=["year", "district_code", "school_code", "detail_level", "gender"],
    on=[
        "ethnic_hispanic", "race_americanindian", "race_asian",
        "race_black", "race_pacific_islander", "race_white", "two_or_more_races",
    ],
    variable_name="race_ethnicity_raw",
    value_name="student_count",
)
```

After unpivoting, map `race_ethnicity_raw` to the `demographic` code via `replace_strict()` with the table above.

**Design decision**: Keep `gender` as a separate fact-table column (a topic-specific categorical alongside `demographic`). This produces a fact with two FK columns (`demographic` + `gender`), preserves the gender × race cross-tab fidelity, and avoids an explosion of demographic codes. The alternative (folding gender into demographic with codes like `female_hispanic`, `male_black`) would create 14 codes that are not useful anywhere else in the domain. The sister topic `enrollment_march_gender_race_ethnicity` has chosen this same pattern — keeping both topics consistent.

### Total Gender Row Is Redundant

The `Total` gender row equals `Female + Male` for every (year, geography, race) cell where neither component is suppressed. Verified at the 2025 and 2026 state level for all seven race columns (every cell matches exactly). The transform should drop `Gender == "Total"` rows because:

1. It is computable as `Female + Male` (modulo suppression).
2. Keeping it would require analysts to filter `gender != "Total"` on every aggregation to avoid double-counting.
3. When gender components are suppressed but the total is not (or vice versa), keeping `Total` adds no information that the per-gender rows do not already convey.

If the transform later needs the totals (e.g., for percentage calculations within validate.py), they can be reconstructed by summing the kept rows.

### State Row Deduplication

Both the District file and the School file for a given year each contain the 3 state-aggregate rows (Female/Male/Total). After concatenation, deduplicate state rows so the gold fact emits one set of state rows per year, not two. Use `deduplicate_by_detail_level()` from `src/utils/transformers.py` keyed on (year, gender, demographic) for state-level rows.

### No Year Coverage Gaps

All 17 years from 2010 through 2026 are present (no COVID gap — the FTE October count was published every year of the decade and is the most-used enrollment snapshot). Both detail levels are complete for every year.

### Column Renames

Recommended bronze → standardized column rename map (apply after `.strip()`):

```python
RENAME_MAP = {
    "System ID":              "district_code_raw",    # then map "" -> NULL, then zfill(3) for 3-digit codes
    "System Name":            "district_name_raw",    # dimension-only
    "School ID":              "school_id_combined",   # then split into school_code + school_name_raw
    "Gender":                 "gender_raw",           # then map to female/male and drop Total
    "Ethnic Hispanic":        "ethnic_hispanic",      # cast Int64 strict=False
    "Race AmericanIndian":    "race_americanindian",
    "Race Asian":             "race_asian",
    "Race Black":             "race_black",
    "Race Pacific Islander":  "race_pacific_islander",
    "Race White":             "race_white",
    "Two or more Races":      "two_or_more_races",    # note bronze had trailing space
}
```

After renaming, cast all 7 race/ethnicity columns to `pl.Int64` with `strict=False` (which converts `*` to null), then unpivot to long form, then map the variable name to `demographic`.

### Consistency With enrollment_march_gender_race_ethnicity

This dataset is structurally identical to the March/Cycle 3 companion topic except:

- Filename suffix `-1` (Cycle 1 / October) vs `-3` (Cycle 3 / March).
- The October dataset has 17 years (2010-2026) vs the March dataset's 16 years (2010-2025) — i.e., the October 2025 count for SY 2025-2026 has been published but the March 2026 count has not yet been collected.
- Preamble line 2 format slightly differs (October has a space before the year: `"Fiscal Year 2026-1"`; March has none: `"Fiscal Year2025-3"`) — but the transform should not rely on the preamble for the year anyway (use filename).
- District file `Gender` header has 1 leading space in October files vs 2 leading spaces in the March files. Both variants exist across the full 34-file October set consistently by detail level.

The gold fact table for this topic can (and should) follow the same schema as the March topic, enabling analysts to compute October→March transitions within the same school year by joining on (district_code, school_code, gender, demographic, year).

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| (filename year `YYYY` from `Fiscal YearYYYY-1`) | fact_key | `year` | Cast to `pl.Int32`. Derived from filename — no year column in bronze. `year` represents GaDOE fiscal year = school year ending (e.g., `year=2026` → SY 2025-2026, fall 2025 snapshot). |
| `System ID` | fact_key | `district_code` | Cast to `pl.Utf8`, then map `""` → NULL for state rows, then `zfill(3)` (no-op for existing 3-digit and 7-digit codes alike). 7-digit charter-system codes pass through unchanged. |
| `System Name` | dimension_attribute | — | Goes to `districts.parquet` dimension. Title case already; pass through `title_case_name`. Drop from fact. |
| `School ID` (NNNN-Name) — code part | fact_key | `school_code` | Extract via regex `^(\d{4})-`. Cast to `pl.Utf8`, map `"State-Wide"` → NULL, then `zfill(4)`. |
| `School ID` (NNNN-Name) — name part | dimension_attribute | — | Extract via regex `^\d{4}-(.+)$`. Goes to `schools.parquet` dimension. Pass through `title_case_name`. Drop from fact. |
| `Gender` (Female, Male) | fact_categorical | `gender` | Lowercase the bronze value. **Drop rows where `Gender == "Total"`** — redundant with Female + Male. |
| `Ethnic Hispanic` (count) | fact_metric (after unpivot) | `student_count` (with `demographic == "hispanic"`) | `pl.Int64`. Cast `*` → null via `strict=False`. Hispanic is a non-overlapping ethnicity bucket. |
| `Race AmericanIndian` (count) | fact_metric (after unpivot) | `student_count` (with `demographic == "native_american"`) | `pl.Int64`. Heavily suppressed — expect ~86-99.9% null at district/school level. |
| `Race Asian` (count) | fact_metric (after unpivot) | `student_count` (with `demographic == "asian"`) | `pl.Int64`. |
| `Race Black` (count) | fact_metric (after unpivot) | `student_count` (with `demographic == "black"`) | `pl.Int64`. Lowest suppression rate (~14% at school level). |
| `Race Pacific Islander` (count) | fact_metric (after unpivot) | `student_count` (with `demographic == "pacific_islander"`) | `pl.Int64`. Heavily suppressed (~99.9% at school level). |
| `Race White` (count) | fact_metric (after unpivot) | `student_count` (with `demographic == "white"`) | `pl.Int64`. |
| `Two or more Races` (count) | fact_metric (after unpivot) | `student_count` (with `demographic == "multiracial"`) | `pl.Int64`. Suppression decreasing over time as population grows. |

**Final fact-table column order** (per data-cleaning-standards §1):
`year`, `district_code`, `school_code`, `demographic`, `gender`, `student_count`.

The fact table will have one row per `(year, district_code, school_code, demographic, gender)` tuple, partitioned per `data/gold/education/enrollment_october_gender_race_ethnicity/year=YYYY/{schools,districts,states}.parquet` per the education gold output format.

**Expected expansion factor (bronze → gold):**

- Bronze rows: each (geography × gender) pair has 7 race/ethnicity columns wide → after unpivot each pair expands ×7.
- Bronze gender rows kept: 2 of 3 (drop `Total`) → ×(2/3).
- State rows deduplicated: District + School both contribute 3 state rows → keep 3, not 6.

For 2026: District file = 714 bronze rows = 237 districts × 3 genders + 3 state. After dropping Total: 237 × 2 + 2 = 476. After unpivot ×7: 3,332 district + state-from-district rows. School file = 6,951 bronze rows = 2,315 schools × 3 + 3 state. After dropping Total + dedup state: 2,315 × 2 = 4,630 school rows × 7 = 32,410 rows. Plus 2 × 7 = 14 state rows (after dedup and dropping Total) and 237 × 2 × 7 = 3,318 district rows. Approximate gold totals for 2026: ~14 state + ~3,318 district + ~32,410 school ≈ 35,742 rows. (Exact figures will be in the `_transform_manifest.json` after the transform runs.)

## Corrections

- **2026-06-12 (transform authoring)**: The Gold Schema Classification table, the demographic-mapping table header ("Gold `demographic` code"), and the final column-order line place the race axis in a `demographic` column. Stale: the education domain `CLAUDE.md` "Race × gender cross-classification" convention (added after this doc was written, and explicitly listing this topic) names that column **`race`** — each axis of a true cross-classification is its own fact column, and `demographic` is reserved for single-axis topics. Actual gold column order: `year`, `district_code`, `school_code`, `race`, `gender`, `student_count`. The seven canonical keys in the mapping table are unchanged; only the gold column name differs. State-level dedup keys are likewise `(year, race, gender)`.
- **2026-06-12 (transform authoring)**: The row-count table's claim "School row counts are `3 + 3 × number_of_schools`" is inconsistent with its own numbers (e.g., 2026: 3 + 3 × 2,315 = 6,948 ≠ 6,951). The table's *Schools* column counts **distinct `School ID` strings**, but a few School ID strings repeat under two different System IDs, and the row formula actually follows the **(System ID, School ID) pair** count: 2010 = 2,271 pairs (vs 2,268 strings), 2026 = 2,316 pairs (vs 2,315 strings), with file rows = `3 × (pairs + 1)` exactly. The gold school grain is `(district_code, school_code)`, i.e. the pair count. (Relatedly, the Categorical Columns section's "2,316 distinct school IDs in the 2026 file" includes the `State-Wide` sentinel: 2,315 school strings + 1.)
- **2026-06-12 (transform authoring)**: The 2026 expansion estimate (~35,742) undercounts for the same reason — school-level gold rows are 2,316 pairs × 14 = **32,424**, not 32,410. Actual 2026 gold = 14 state + 3,318 district + 32,424 school = **35,756** rows (verified against the actual gold output; per-year gold equals `14 × (1 + n_districts + n_school_pairs)` for all 17 years; total = 599,760).
- **2026-06-12 (transform authoring)**: The "Consistency With enrollment_march_gender_race_ethnicity" claim that the March preamble writes the year with no space (`"Fiscal Year2025-3"`) is wrong — that no-space form is the **filename** pattern (both cycles). Preamble line 2 writes the spaced form in **both** topics (verified: March 2025 line 2 = `"... - Fiscal Year 2025-3 Data Report"`; all 34 October files = `"... - Fiscal Year YYYY-1 Data Report"`). The two-pattern distinction is filename (`Fiscal YearYYYY-c`) vs preamble (`Fiscal Year YYYY-c`), not October vs March.
- **2026-06-12 (transform authoring)**: The Suppression Handling section's alternative — "register `*` as a null marker via `read_bronze_file()`" — is not viable: `read_bronze_file()` has no `skip_rows` parameter and cannot skip the 4-line GaDOE preamble. A topic-local reader (`pl.read_csv(skip_rows=4, infer_schema_length=0, null_values=["*"])` + header strip) is required, consistent with this doc's own "CSV Preamble Must Be Skipped" section.
- **2026-06-12 (transform authoring)**: Additional invariants verified during authoring across all 34 files: the minimum non-null count anywhere in bronze is exactly **15** (the suppression floor); state-aggregate cells are **never** suppressed; the 3 state rows in the District and School files of the same year are value-identical for all 17 years; `Total == Female + Male` holds on all 123,666 fully published (geography, race) triples with 0 violations; and physical data-line counts equal parsed row counts for every file (zero read loss).
