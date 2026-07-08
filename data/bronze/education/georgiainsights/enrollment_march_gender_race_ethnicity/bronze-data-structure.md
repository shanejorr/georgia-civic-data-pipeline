# enrollment_march_gender_race_ethnicity - Bronze Data Structure

## Overview

- Topic: enrollment_march_gender_race_ethnicity
- Source: georgiainsights
- Files: 32 files spanning 2010-2025 (one CSV per year per detail level: District + School)
- Unreadable files: none
- Year representation: Year is encoded ONLY in the filename (`Fiscal Year2010-3` ... `Fiscal Year2025-3`) and in the file's preamble (lines 2-3, e.g., `"March 4, 2010 (FTE 2010-3)"`). There is no year column inside the data — every row in `Fiscal Year2025-3` is implicitly fiscal year 2025 / school year 2024-2025.
- Filename-to-data year offset: same (filename year = data year — confirmed by the in-file preamble "Fiscal Year YYYY-3 Data Report"). The trailing `-3` denotes Cycle 3 (the March FTE student count, distinguishing this dataset from the October Cycle 1 enrollment).
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
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2010-3 District.csv | dbc823e145f6f46ceeefeef915b7c563798047e2c9c834ee98dcc4cbc9b4c1da |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2010-3 School.csv | 1b3b5305e080425a444ae344334da461e9af623a938fc30940d7c1f90722bad6 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2011-3 District.csv | 1aa38ad5228081440499c8f8d1613eaba61e91afd83b8ae71d9a8a5e7f2b4576 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2011-3 School.csv | 526f0f244a5724137c4360b3ac6332587a47db67469c0b316054b6c4ce0abce1 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2012-3 District.csv | 814e0f382a4378b28b8816675d7519fe1f75ab9a0f95eb062068bb846e0a37ca |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2012-3 School.csv | b94c75fd59e54615ab760b7279ac7d4e32cd52130bc7165cbb7b8cfe3c0d373f |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2013-3 District.csv | 9af69b2fa5d60b7cee98756dd3ab3f874aeca4328205dad40212f67477da540d |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2013-3 School.csv | 2472d1fa2ff56f8b050ece8be82cb20a237cb61797da594bb7a24607e33c9e51 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2014-3 District.csv | 769a7c6084b5f68c2cafcf8726b3644751c03c6e7a167966ee4c98079be5991c |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2014-3 School.csv | 6a3600fdaca3ecff48c1fa9ced1fa800256ce2f47cc1763a281c850ba5d9e656 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2015-3 District.csv | 0e1d5fbd4085a07e8ea5c8d2681b21807bf0143deb8cbf478f9abf49f04c044a |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2015-3 School.csv | c25dd07cca89895abd5611f2a079427ab4477b0523fafdf457275a9a9a62d35b |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2016-3 District.csv | a5d01cdc7a3fde4a6d1e58a1d8239d50376908edae3eedaa5208109fccc2b11d |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2016-3 School.csv | 6fb99956d713f95f1a923b4a25850a64114c9e593fff0e69a377480ecb38acec |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2017-3 District.csv | fb7219abf2c9c576fa30d6a08224a8ce89da6bd7916fee9c4384bd52f1d2c50b |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2017-3 School.csv | c7deeb8334f25f0ae078e29824941ffd18a7cb961f474534dd70452c34107232 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2018-3 District.csv | 3c5b50c4d4db16cf3e1a1ab4b1a44a951e5f184e464e956240fe55c417d7e1de |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2018-3 School.csv | bc716e641886ec8a28710d9c70df1fb4e7011ffc099ab47ebc797ff5c1abe687 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2019-3 District.csv | 86d51bdf5e0f4a544bcbd926e06912759231944c26d8c8a1daa063e8ed69f7e0 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2019-3 School.csv | e8bc07c54ad6e66bc9d4c8a524a8d3028329458214719373e64b4a5efbd5893f |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2020-3 District.csv | dc7b373ea3681c78e77e15b854053b9984682581adc6e4e4671f916be7e878cb |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2020-3 School.csv | 434d991508a5f17d3afde903bdded3b8d79aec1de9a6a738b7877401ffec075d |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2021-3 District.csv | 5819d8833024ad518377fd1760dc4b575b75950ad01b0c875444e8b6ab545896 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2021-3 School.csv | 9a2875b3eb1e0e8bd41ee24f46927a9d467ea98b7253d763fc14eb8793fd0e59 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2022-3 District.csv | 743a4a574de12164bd6b66197dba389206bd075d0bbe063553e8670a8649cde7 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2022-3 School.csv | a94ffaae6f3c86399a3c6918b8294d708edf74748d5415e84b2112a6e20f54ef |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2023-3 District.csv | efc4213dc9a33ad326a4da1e5c6acf1b1b90e37162887f2cb3c57d754026f35a |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2023-3 School.csv | 12408b710cd5ab13565d7ed8dddc39f8477b3568dd839a64d76efa021482549a |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2024-3 District.csv | a4bb5643ff232cb870034cd47dd168d95095beee9b6ef938b181c50603f6809e |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2024-3 School.csv | cf0d7d07599e48e19496b59828cfa9df124c0c4cbd1e5e5432ae6dd415f45514 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2025-3 District.csv | b7112824f7ea90a0efd5c91667336356c307101db3d84af48344f34330f609b9 |
| FTE Enrollment by Race_Ethnicity and Gender Fiscal Year2025-3 School.csv | d1fd19a89ffda1e0f4dc8bc3ee03a1179a24e0c6f55ab1654af6d9f4155de474 |

## Summary

GaDOE March (FTE Cycle 3) headcount of public school students broken out by gender and race/ethnicity. Each row reports a Female / Male / Total student count for one of seven mutually-exclusive race/ethnicity buckets:

- `Ethnic Hispanic` — students of Hispanic origin (treated as a separate ethnicity bucket, NOT overlapping with the six race buckets — see ETL Considerations).
- `Race AmericanIndian` — non-Hispanic American Indian / Alaska Native.
- `Race Asian` — non-Hispanic Asian.
- `Race Black` — non-Hispanic Black / African American.
- `Race Pacific Islander` — non-Hispanic Native Hawaiian / Pacific Islander.
- `Race White` — non-Hispanic White.
- `Two or more Races` — non-Hispanic students reporting two or more races.

The three `Gender` rows (`Female`, `Male`, `Total`) for any single (year, geography) are arithmetically related: `Total == Female + Male` for every race column where neither value is suppressed (verified row-by-row). The seven race/ethnicity columns also sum to total enrollment per gender (e.g., 2025 state Total: 1,396,583 race + 340,147 Hispanic = 1,736,730 students).

This is the **March / spring** snapshot. The companion topic `enrollment_october_gender_race_ethnicity` reports the same breakdown from the October Cycle 1 count.

## Eras

### Era 1: 2010-2025 (single era)

Every file in the topic uses the **same column set across all 16 years** with no schema drift. The only structural difference is between detail levels: District files have 10 columns, School files have the same 10 plus a `School ID` column (11 total). Both detail levels share the identical 7 race/ethnicity metric columns for the entire range.

**Note on column header whitespace.** Bronze headers contain inconsistent leading whitespace introduced by the source export — every column name except `System ID` and `School ID` carries one or two leading spaces, and `Two or more Races` has a trailing space too. Headers must be referenced by their exact bytes (or stripped) when reading; partial-substring matches are unreliable. The transform should `.strip()` all headers on load.

| Column | Description |
|--------|-------------|
| `System ID` | String. 3-digit GOSA district code (e.g., `"601"`) for districts, 7-digit charter code (e.g., `"7820108"`) for charters, or empty string `""` for the state-aggregate row. |
| ` System Name` | String. District name in title case (e.g., `"Appling County"`, `"Atlanta Public Schools"`), or `"State-Wide"` for the state row. Leading space in header. |
| `School ID` | **School files only.** String of the form `"NNNN-School Name"` where NNNN is the 4-digit GOSA school code (e.g., `"0103-Appling County High School"`), or `"State-Wide"` for the state-aggregate rows. The numeric prefix and the school name are jammed into a single column and must be split during transform. |
| `  Gender` | String. One of `Female`, `Male`, `Total` (consistent across all 32 files). Each (year, geography) appears as exactly three rows. Two leading spaces in header. |
| `  Ethnic Hispanic` | String holding integer counts; suppression marker `*` for small cells. Two leading spaces in header. |
| `  Race AmericanIndian` | Same dtype/suppression pattern. Heavily suppressed at the school level (~99.9% `*` in 2025 schools). |
| `  Race Asian` | Same dtype/suppression pattern. |
| `  Race Black` | Same dtype/suppression pattern. Lowest suppression rate (~13.6% at 2025 school level). |
| `  Race Pacific Islander` | Same dtype/suppression pattern. Heavily suppressed (~99.9% `*` at 2025 school level). |
| `  Race White` | Same dtype/suppression pattern. |
| `  Two or more Races ` | Same dtype/suppression pattern. Trailing space in header. |

#### Sample Data (2025 School file)

```text
=== State rows (top 3 rows) ===
System ID="" System Name="State-Wide" School ID="State-Wide" Gender=Female  Ethnic Hispanic=166312 RaceAI=1984 RaceAsian=44042 RaceBlack=309028 RacePI=852 RaceWhite=285306 TwoOrMore=42374
System ID="" System Name="State-Wide" School ID="State-Wide" Gender=Male    Ethnic Hispanic=173835 RaceAI=2068 RaceAsian=46832 RaceBlack=316031 RacePI=869 RaceWhite=303854 TwoOrMore=43343
System ID="" System Name="State-Wide" School ID="State-Wide" Gender=Total   Ethnic Hispanic=340147 RaceAI=4052 RaceAsian=90874 RaceBlack=625059 RacePI=1721 RaceWhite=589160 TwoOrMore=85717

=== Random school rows ===
System ID="737" System Name="Tift County"             School ID="3052-Northeast Middle School"          Gender=Male   Hispanic=89  AI=* Asian=*   Black=131 PI=* White=121  Two=*
System ID="644" System Name="DeKalb County"           School ID="3063-Oak Grove Elementary School"      Gender=Male   Hispanic=20  AI=* Asian=22  Black=32  PI=* White=154  Two=21
System ID="792" System Name="Valdosta City"           School ID="0103-Valdosta Middle School"           Gender=Total  Hispanic=104 AI=* Asian=*   Black=751 PI=* White=124  Two=35
System ID="706" System Name="Muscogee County"         School ID="5069-Wesley Heights Elementary School" Gender=Female Hispanic=*   AI=* Asian=*   Black=142 PI=* White=*    Two=19
System ID="726" System Name="Griffin-Spalding County" School ID="4052-Orrs Elementary School"           Gender=Female Hispanic=47  AI=* Asian=*   Black=125 PI=* White=43   Two=*
```

#### Sample Data (2025 District file, state rows)

```text
System ID="" System Name="State-Wide" Gender=Female  Hispanic=166312 AI=1984 Asian=44042 Black=309028 PI=852  White=285306 Two=42374
System ID="" System Name="State-Wide" Gender=Male    Hispanic=173835 AI=2068 Asian=46832 Black=316031 PI=869  White=303854 Two=43343
System ID="" System Name="State-Wide" Gender=Total   Hispanic=340147 AI=4052 Asian=90874 Black=625059 PI=1721 White=589160 Two=85717

=== A district row (Appling County) ===
System ID="601" System Name="Appling County" Gender=Female Hispanic=361 AI=* Asian=* Black=356 PI=* White=863  Two=78
System ID="601" System Name="Appling County" Gender=Male   Hispanic=332 AI=* Asian=* Black=323 PI=* White=989  Two=84
System ID="601" System Name="Appling County" Gender=Total  Hispanic=693 AI=* Asian=* Black=679 PI=* White=1852 Two=162
```

#### Statistics — Row Counts Per File

| Year | District file rows | School file rows |
|-----:|-------------------:|-----------------:|
| 2010 | 561   | 6,813 |
| 2011 | 585   | 6,873 |
| 2012 | 591   | 6,876 |
| 2013 | 597   | 6,822 |
| 2014 | 597   | 6,795 |
| 2015 | 597   | 6,804 |
| 2016 | 615   | 6,870 |
| 2017 | 624   | 6,876 |
| 2018 | 642   | 6,900 |
| 2019 | 642   | 6,909 |
| 2020 | 648   | 6,903 |
| 2021 | 666   | 6,921 |
| 2022 | 672   | 6,942 |
| 2023 | 684   | 6,948 |
| 2024 | 708   | 6,972 |
| 2025 | 708   | 6,975 |

District row counts are always exactly `3 × number_of_districts` (Female / Male / Total per district, plus 3 state-aggregate rows). School row counts are `3 × number_of_schools + 3` (the same triple per school plus 3 state-aggregate rows). Note: the school counts include schools that close or open across years, which is why the row count drifts.

#### Null Counts

Every column in every file has **0 nulls** when read with `infer_schema_length=0` (all-string mode). The "missing" semantics in this dataset are encoded as:

- `System ID == ""` (empty string) for the state-aggregate row.
- `*` for suppressed numeric cells.

There are no actual `None`/null values anywhere in any bronze file.

#### Categorical Columns

| Column | Distinct Values |
|--------|-----------------|
| `  Gender` | `Female`, `Male`, `Total` (3 values, identical across all 32 files) |
| ` System Name` | District names in title case (e.g., `Appling County`, `Atlanta Public Schools`) plus the literal `State-Wide`. Total of ~250 distinct district names across 16 years (district roster grows ~561→708 districts as new charters appear). |
| `System ID` | Either empty string `""` (state row), a 3-digit standard district code (`"601"`, `"644"`, ...), or a 7-digit charter/school-system code (`"7820108"`, `"7830649"`, ...). Across all 16 years: 183 distinct 3-digit codes + 67 distinct 7-digit codes = 250 total. |
| `School ID` (School files only) | Either `State-Wide` (state-aggregate row) or `NNNN-School Name` (4-digit code prefix). Verified 100% conformance to the `^\d{4}-` pattern across 2,322 distinct school IDs in the 2025 file. |

#### Suppression Markers

| Column | Marker | Where it appears |
|--------|--------|------------------|
| `  Ethnic Hispanic` | `*` (asterisk) | Both detail levels, every year. ~17–21% of rows at district level, ~21% at school level (2025 figures). |
| `  Race AmericanIndian` | `*` | Both detail levels, every year. ~80–87% of rows at district level, ~99.9% at school level. |
| `  Race Asian` | `*` | Both detail levels, every year. ~58–61% at district level, ~78% at school level. |
| `  Race Black` | `*` | Both detail levels, every year. ~5–7% at district level, ~14% at school level. |
| `  Race Pacific Islander` | `*` | Both detail levels, every year. ~92% at district level, ~99.9% at school level. |
| `  Race White` | `*` | Both detail levels, every year. ~5–24% at district level, ~24% at school level. |
| `  Two or more Races ` | `*` | Both detail levels, every year. ~25% at district level, ~50% at school level (and decreasing over time as the multi-racial population grows). |

Verified across all 32 files: `*` is the **only** non-numeric value that appears in any of the 7 race/ethnicity columns. There are no `TFS`, `N/A`, or other markers — Georgia Insights uses a single `*` convention for this dataset.

Suppression is **column-by-column, not row-by-row** — a single row can have some race columns suppressed (`*`) and others numeric. This differs from the attendance_dashboard topic where suppression is all-or-nothing across the metric columns.

## ETL Considerations

### Multi-File-Per-Year Concatenation

For each year, the District counts and School counts live in **two separate CSV files**. The transform must read both files (e.g., `Year2025-3 District.csv` and `Year2025-3 School.csv`) and union them with a synthesized `detail_level` column:

- `District.csv` rows become `detail_level = "district"` (or `"state"` if `System ID == ""`).
- `School.csv` rows become `detail_level = "school"` (or `"state"` if `System ID == ""`).

Note that both the District file and the School file each contain their own copy of the 3 state-aggregate rows (Female/Male/Total). They report the same underlying state totals — verified that `Female + Male = Total` and that the state values match across the two files. The transform must **deduplicate** the state rows so the final state-level fact emits exactly 3 rows per year (one per gender × per race), not 6.

### CSV Preamble Must Be Skipped

Every CSV begins with a 4-line preamble:

```text
Georgia Department of Education
FTE Enrollment by Race/Ethnicity and Gender - Fiscal Year YYYY-3 Data Report
"March D, YYYY (FTE YYYY-3)"
{blank line}
```

Headers start on line 5. Use `pl.read_csv(path, skip_rows=4, ...)`. Do not parse the preamble for the year (the filename is more reliable and matches exactly), but do verify line 2 starts with `"FTE Enrollment by Race/Ethnicity and Gender"` as a sanity check.

### Column Header Whitespace

Bronze headers carry stray leading and trailing spaces that vary by column:

```text
'System ID'              (no whitespace)
' System Name'           (1 leading space)
'School ID'              (no whitespace, school files only)
'  Gender'               (2 leading spaces)
'  Ethnic Hispanic'      (2 leading spaces)
'  Race AmericanIndian'  (2 leading spaces)
'  Race Asian'           (2 leading spaces)
'  Race Black'           (2 leading spaces)
'  Race Pacific Islander' (2 leading spaces)
'  Race White'           (2 leading spaces)
'  Two or more Races '   (2 leading spaces, 1 trailing space)
```

The transform must `.strip()` all column headers immediately after `read_csv()` so downstream code can reference them by clean names. Failing to strip will produce silent column-name mismatches in the rename map.

### Year Is Not in the Data

There is no year column. The transform must derive `year` from the filename. Recommended pattern:

```python
import re
m = re.search(r"Fiscal Year(\d{4})-3", path.name)
year = int(m.group(1))
```

The `-3` suffix (Cycle 3 = March count) is implicit in the topic name. The companion topic `enrollment_october_gender_race_ethnicity` uses `-1` (Cycle 1 = October count).

### School ID Splitting

The `School ID` column packs both the school code and the school name into a single string of the form `NNNN-Name` (e.g., `"0103-Appling County High School"`). The transform must split on the first `-`:

```python
df = df.with_columns(
    pl.col("school_id").str.extract(r"^(\d{4})-(.+)$", 1).alias("school_code"),
    pl.col("school_id").str.extract(r"^(\d{4})-(.+)$", 2).alias("school_name_raw"),
)
```

The `school_code` portion goes into the fact table; the `school_name_raw` portion belongs only in the schools dimension and should be `title_case_name()`-ed there. Note that some school names already contain hyphens (e.g., `"H. R. McCall–Smith Elementary"` if any exist), so split on the **first** hyphen only.

State-aggregate rows have `School ID == "State-Wide"` (no leading 4-digit code) — the regex above will fail and produce nulls, which is the correct behavior for state rows that get nulled out anyway (per the geography-nulling rules below).

### Geography Sentinels

State and aggregate rows use these patterns (verified across all 32 files):

| Detail Level | bronze pattern | district_code | school_code |
|-------------|----------------|---------------|-------------|
| state | `System ID == ""` AND `System Name == "State-Wide"` (and `School ID == "State-Wide"` in school files) | NULL | NULL |
| district (in District files) | `System ID == digits` | `zfill(3)` | NULL |
| school (in School files) | `System ID == digits` AND `School ID matches "^\d{4}-"` | `zfill(3)` | `zfill(4)` |

There are no `(System ID present, School ID == "State-Wide")` rows in any School file — i.e., the School files do not contain district-aggregate rows. District aggregates only live in the District files.

Use `null_aggregate_geography()` from `src/utils/transformers.py` with the standard `EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"]`.

### ID Padding

`System ID` is already 3-digit zero-padded for standard districts (`"601"`) and 7-digit for charters (`"7820108"`). Apply `zfill(3)` per education domain conventions to be defensive. Cast to `pl.Utf8` first.

`School ID` after splitting is 4-digit (`"0103"`). Apply `zfill(4)` to be defensive. Cast to `pl.Utf8` first.

The empty string `""` for state rows must be mapped to NULL **before** zfill is applied (otherwise `"".zfill(3)` would produce `"000"` and silently masquerade as a district).

### Suppression Handling

The single suppression marker `*` appears in every race/ethnicity column. Use `cast(pl.Int64, strict=False)` after reading — `*` will coerce to null. Alternatively, register `*` as a null marker via `read_bronze_file()` from `src/utils/readers.py` (which already handles common suppression markers including `*`).

Per the data-cleaning standards, all suppressed values must become NULL in gold — do not impute, do not drop the row, do not retain the `*` literal.

### Hispanic Is a Separate (Non-Overlapping) Ethnicity

Critical interpretation: `Ethnic Hispanic` is a **non-overlapping** ethnicity bucket alongside the six race buckets, not an overlay. Verified by summing the 7 race/ethnicity columns for the 2025 state Total row: 1,396,583 (race columns) + 340,147 (Hispanic) = 1,736,730 — which matches Georgia's published FTE March 2025 total enrollment (~1.74M).

This means the gold demographic mapping should treat Hispanic as one of seven mutually exclusive race/ethnicity values, NOT as a Hispanic-of-any-race overlay. Use the global demographic codes:

| Bronze column | Gold `demographic` code |
|---------------|--------------------------|
| `  Ethnic Hispanic` | `hispanic` |
| `  Race AmericanIndian` | `native_american` |
| `  Race Asian` | `asian` |
| `  Race Black` | `black` |
| `  Race Pacific Islander` | `pacific_islander` |
| `  Race White` | `white` |
| `  Two or more Races ` | `multiracial` |

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

**Open question for transform design**: Whether to keep `gender` as a separate fact-table column (a topic-specific categorical alongside `demographic`), or to fold gender into the `demographic` column (e.g., add new codes like `female_hispanic`, `male_black`, ...) keeping the topic single-demographic. The first approach is cleaner — it produces a fact with two FK columns (`demographic` + `gender`), preserves the gender × race cross-tab fidelity, and avoids an explosion of demographic codes. The transform should add a `gender` column with values `female` and `male` (drop `Total`) as a topic-specific categorical column distinct from the global `demographic` FK.

### Total Gender Row Is Redundant

The `Total` gender row equals `Female + Male` for every (year, geography, race) cell where neither component is suppressed. Verified at the 2025 state level for all seven race columns. The transform should drop `Gender == "Total"` rows because:

1. It is computable as `Female + Male` (modulo suppression).
2. Keeping it would require analysts to filter `gender != "Total"` on every aggregation to avoid double-counting.
3. When gender components are suppressed but the total is not (or vice versa), keeping `Total` adds no information that the per-gender rows do not already convey.

If the transform later needs the totals (e.g., for percentage calculations within validate.py), they can be reconstructed by summing the kept rows.

### State Row Deduplication

Both the District file and the School file for a given year each contain the 3 state-aggregate rows (Female/Male/Total). After concatenation, deduplicate state rows so the gold fact emits one set of state rows per year, not two. Use `deduplicate_by_detail_level()` from `src/utils/transformers.py` keyed on (year, gender, demographic) for state-level rows.

### No Year Coverage Gaps

All 16 years from 2010 through 2025 are present (no COVID gap — the FTE March count was published every year of the decade). Both detail levels are complete for every year.

### Column Renames

Recommended bronze → standardized column rename map (apply after `.strip()`):

```python
RENAME_MAP = {
    "System ID":              "district_code_raw",   # then map "" -> NULL, zfill(3)
    "System Name":            "district_name_raw",   # dimension-only
    "School ID":              "school_id_combined",  # then split into school_code + school_name_raw
    "Gender":                 "gender_raw",          # then map to female/male and drop Total
    "Ethnic Hispanic":        "ethnic_hispanic",     # cast Int64 strict=False
    "Race AmericanIndian":    "race_americanindian",
    "Race Asian":             "race_asian",
    "Race Black":             "race_black",
    "Race Pacific Islander":  "race_pacific_islander",
    "Race White":             "race_white",
    "Two or more Races":      "two_or_more_races",   # note bronze had trailing space
}
```

After renaming, cast all 7 race/ethnicity columns to `pl.Int64` with `strict=False` (which converts `*` to null), then unpivot to long form, then map the variable name to `demographic`.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| (filename year `YYYY` from `Fiscal YearYYYY-3`) | fact_key | `year` | Cast to `pl.Int32`. Derived from filename — no year column in bronze. |
| `System ID` | fact_key | `district_code` | Cast to `pl.Utf8`, then map `""` → NULL for state rows, then `zfill(3)`. |
| `System Name` | dimension_attribute | — | Goes to `districts.parquet` dimension. Title case already; pass through `title_case_name`. Drop from fact. |
| `School ID` (NNNN-Name) — code part | fact_key | `school_code` | Extract via regex `^(\d{4})-`. Cast to `pl.Utf8`, map `"State-Wide"` → NULL, then `zfill(4)`. |
| `School ID` (NNNN-Name) — name part | dimension_attribute | — | Extract via regex `^\d{4}-(.+)$`. Goes to `schools.parquet` dimension. Pass through `title_case_name`. Drop from fact. |
| `Gender` (Female, Male) | fact_categorical | `gender` | Lowercase the bronze value. **Drop rows where `Gender == "Total"`** — redundant with Female + Male. |
| `Ethnic Hispanic` (count) | fact_metric (after unpivot) | `student_count` (with `demographic == "hispanic"`) | `pl.Int64`. Cast `*` → null via `strict=False`. Hispanic is a non-overlapping ethnicity bucket. |
| `Race AmericanIndian` (count) | fact_metric (after unpivot) | `student_count` (with `demographic == "native_american"`) | `pl.Int64`. Heavily suppressed — expect ~80-99% null at school level. |
| `Race Asian` (count) | fact_metric (after unpivot) | `student_count` (with `demographic == "asian"`) | `pl.Int64`. |
| `Race Black` (count) | fact_metric (after unpivot) | `student_count` (with `demographic == "black"`) | `pl.Int64`. Lowest suppression rate. |
| `Race Pacific Islander` (count) | fact_metric (after unpivot) | `student_count` (with `demographic == "pacific_islander"`) | `pl.Int64`. Heavily suppressed. |
| `Race White` (count) | fact_metric (after unpivot) | `student_count` (with `demographic == "white"`) | `pl.Int64`. |
| `Two or more Races` (count) | fact_metric (after unpivot) | `student_count` (with `demographic == "multiracial"`) | `pl.Int64`. Suppression decreasing over time as population grows. |

**Final fact-table column order** (per data-cleaning-standards §1):
`year`, `district_code`, `school_code`, `demographic`, `gender`, `student_count`.

The fact table will have one row per `(year, district_code, school_code, demographic, gender)` tuple, partitioned per `data/gold/education/enrollment_march_gender_race_ethnicity/year=YYYY/{schools,districts,states}.parquet` per the education gold output format.

**Expected expansion factor (bronze → gold):**

- Bronze rows: each (geography × gender) pair has 7 race/ethnicity columns wide → after unpivot each pair expands ×7.
- Bronze gender rows kept: 2 of 3 (drop `Total`) → ×(2/3).
- State rows deduplicated: District + School both contribute 3 state rows → keep 3, not 6.

For 2025: District file = 708 bronze rows = 235 districts × 3 genders + 3 state. After dropping Total: 235 × 2 + 2 = 472. After unpivot ×7: 3,304 district + state-from-district rows. School file = 6,975 bronze rows = 2,324 schools × 3 + 3 state. After dropping Total + dedup state: 2,324 × 2 = 4,648 school rows × 7 = 32,536 rows. Plus 3 state × 7 = 21 state rows (after dedup) and 470 district rows × 7 = 3,290 district rows. Approximate gold totals for 2025: ~21 state + ~3,290 district + ~32,536 school ≈ 35,847 rows. (Exact figures will be in the `_transform_manifest.json` after the transform runs.)

## Corrections

- **2026-06-12 (transform authoring)**: The Gold Schema Classification table, the final column-order line, and the "Open question for transform design" paragraph place the race axis in a `demographic` column. Stale: the education domain `CLAUDE.md` "Race × gender cross-classification" convention (added after this doc was written, and explicitly listing this topic) names that column **`race`** — each axis of a true cross-classification is its own fact column, and `demographic` is reserved for single-axis topics. Actual gold column order: `year`, `district_code`, `school_code`, `race`, `gender`, `student_count`. The open question is resolved: two columns (`race` + `gender`), never folded codes like `female_hispanic`. Dedup keys are likewise `(year, race, gender)` at the state level, not `(year, gender, demographic)`.
- **2026-06-12 (transform authoring)**: The 2025 expansion arithmetic above is wrong in one term — "3 state × 7 = 21 state rows (after dedup)" counts the dropped `Total` gender row. After dropping `Total`, state rows per year are 2 genders × 7 races = **14**, so 2025 gold = 14 state + 3,290 district + 32,536 school = **35,840** rows (verified against the actual gold output; per-year gold equals `14 × (n_districts + n_schools + 1)` for all 16 years).
- **2026-06-12 (transform authoring)**: The Suppression Handling section's alternative — "register `*` as a null marker via `read_bronze_file()`" — is not viable: `read_bronze_file()` has no `skip_rows` parameter and cannot skip the 4-line GaDOE preamble. A topic-local reader (`pl.read_csv(skip_rows=4, infer_schema_length=0, null_values=["*"])` + header strip) is required, consistent with this doc's own "CSV Preamble Must Be Skipped" section.
- **2026-06-12 (transform authoring)**: Additional invariants verified during authoring across all 32 files: the minimum non-null count anywhere in bronze is exactly **15** (the suppression floor); state-aggregate cells are **never** suppressed; the 3 state rows in the District and School files of the same year are byte-identical for all 16 years; `Total == Female + Male` holds on all 115,889 fully published (geography, race) triples with 0 violations; and physical data-line counts equal parsed row counts for every file (zero read loss).
