# free_reduced_lunch — Bronze Data Structure

## Overview

- Topic: free_reduced_lunch
- Source: georgiainsights (Georgia Department of Education — Free and Reduced Price Meal Eligibility report)
- Files: 28 CSV files (14 fiscal years x 2 detail levels), FY2013 through FY2026
- Unreadable files: none
- Year representation: Filename only. Pattern: `Free Reduced Lunch (FRL) Fiscal Year{YYYY} {Level}.csv` where `{Level}` is `District` or `School`. The year embedded in the filename is the Georgia fiscal year (ends in June of that calendar year), e.g. `Fiscal Year2024` = 2023-2024 school year. Each file also carries the fiscal year in its 3rd preamble line (e.g. `Free and Reduced Lunch (FRL) - Fiscal Year 2026 Data Report`).
- Filename-to-data year offset: No year column in the data body, so no offset to compute; the filename year is the only year indicator and it matches the report title in the preamble.
- Detail levels: state (one `State-Wide Total` row in every District file), district/system (all files), school (School files only).
- Percentage scale: 0–100. `KK-12 % FRL` values range approximately 5.09–95.00 across years. Suppression markers (`*`, `#`) replace values outside 5–95.
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: Georgia Insights (GaDOE) public data downloads — exact page URL not recorded at acquisition time
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| Free Reduced Lunch (FRL) Fiscal Year2013 District.csv | bcdf7e74c7bece95ebce37c301b9b515812dd685a08914a4fc8fd62ee21d1a79 |
| Free Reduced Lunch (FRL) Fiscal Year2013 School.csv | 9d9d3681e04244feb83e52b1987ba5a774a655ccd6f230c8c71491f49133d9a2 |
| Free Reduced Lunch (FRL) Fiscal Year2014 District.csv | ef57b317de46d4440a65c13faa8dde0ccae9487918a9e9d71e7259aa3ae04181 |
| Free Reduced Lunch (FRL) Fiscal Year2014 School.csv | d2d68272805f83f48bffc3f02503f2dd76762d4dd25b01cb19f2f5fec7ab8de5 |
| Free Reduced Lunch (FRL) Fiscal Year2015 District.csv | 7deef1fa6e2cdb0cd095cb712466fa790a3122b3375c59d3bff8d5cbe9061581 |
| Free Reduced Lunch (FRL) Fiscal Year2015 School.csv | ec2e17991d4fdeaf99b61e0676e9c8919aae278c999f77a0c397d8189d016263 |
| Free Reduced Lunch (FRL) Fiscal Year2016 District.csv | ecaf2c3775e1df8f14ce12f227e31bb7f28986bc36363ae0072f9edf9f430628 |
| Free Reduced Lunch (FRL) Fiscal Year2016 School.csv | 7088b852d4c72ff8e61046bbd85acb192bb0238099da10d1fb7e7446c677e569 |
| Free Reduced Lunch (FRL) Fiscal Year2017 District.csv | 8b98bb6ee3c46a1b86b55292086d279b11743c5379607d807861324e1bf37b0d |
| Free Reduced Lunch (FRL) Fiscal Year2017 School.csv | aff81f9c443fdeeca640fdc580761ec1c0c1cb4992a0d1d0dc7a519606584bd2 |
| Free Reduced Lunch (FRL) Fiscal Year2018 District.csv | b77bd50c500b4cc5d531d8bf60055e4d19cfc3382a57d7e385383aa2d33565cd |
| Free Reduced Lunch (FRL) Fiscal Year2018 School.csv | 5e390a84586b36c83f6795e265ba6f0e3e0f1b9503e23b2a6aa69153b02aadb9 |
| Free Reduced Lunch (FRL) Fiscal Year2019 District.csv | 460a945923e2cd1f166ebc5f75831014e154e633908a8643ce40a0ff726fc05d |
| Free Reduced Lunch (FRL) Fiscal Year2019 School.csv | fa41a63716d1df2306c95d3664b34580574e5121a9778d7266cfd23e57efdd52 |
| Free Reduced Lunch (FRL) Fiscal Year2020 District.csv | 1cb349dbc0846ef6bc9ebc201e6d1671ffd7eb0049ea260781acece6ec459312 |
| Free Reduced Lunch (FRL) Fiscal Year2020 School.csv | 4b2046f243e58b130e526b0760757a2c511fb07be071340f26128c1eb68d9d4a |
| Free Reduced Lunch (FRL) Fiscal Year2021 District.csv | 882d371a3e6774f7bcc26a570fb13067c6ac2ed8f06a3f818769beb370de7c57 |
| Free Reduced Lunch (FRL) Fiscal Year2021 School.csv | d956f5631a3852d55c417d760d910efef2e51e0be1ce1937a0749f319a588411 |
| Free Reduced Lunch (FRL) Fiscal Year2022 District.csv | 66fb0c87d1996b7845ae52e1546c410ccc85284fe855ab3ee8c17f2767595981 |
| Free Reduced Lunch (FRL) Fiscal Year2022 School.csv | e61628ece7a69d702f2af94247d14e20ded9b45bfcf917c5bd600820650d31ab |
| Free Reduced Lunch (FRL) Fiscal Year2023 District.csv | f28bd230ed0a8584f36433cabd80942e12b9b8ecd803f1a4624d6c338f8f8dba |
| Free Reduced Lunch (FRL) Fiscal Year2023 School.csv | cdf81b98152d9b9f9f8ab431dcfb994e47fdaca845b05baefaddff14a8e48f2c |
| Free Reduced Lunch (FRL) Fiscal Year2024 District.csv | 84c0658dc380e64e646c944f76561ed08a6727f41be0c6fef62040b2dc4f4f6b |
| Free Reduced Lunch (FRL) Fiscal Year2024 School.csv | 8ba1c58583b4adf9176ebc373243e44e224e1e79039d26b834b325a89170e2da |
| Free Reduced Lunch (FRL) Fiscal Year2025 District.csv | feed3c9d1a29cf0fa1e7c8b3cd3d881d2f14ea86f40ab1348f9e50c0ebd14ad0 |
| Free Reduced Lunch (FRL) Fiscal Year2025 School.csv | 3577be81bb902f2ea6adc789fb97666f945428b413a4ef3ff8e3f08021ecbc81 |
| Free Reduced Lunch (FRL) Fiscal Year2026 District.csv | 25c538c8e3b865bc8da2e01839db855e505009a6d1205ca34d9a4089636c4757 |
| Free Reduced Lunch (FRL) Fiscal Year2026 School.csv | 124270d1e5ea815bc8ee50b9e5e56560ae5dc22179ecafdedab8d8835465db7a |

## Summary

This dataset reports the **percentage of students in grades K–12 eligible for Free or Reduced-price Lunch (FRL)** under the USDA National School Lunch Program. The single metric, `KK-12 % FRL`, is a point-in-time poverty/economic-disadvantage indicator commonly used as a proxy for student economic need across Georgia public schools and districts. Values are percentages on a 0–100 scale and are suppressed (`*`) when they fall outside the 5%–95% band, or marked not-applicable (`#` for district / `NA` referenced in notice) when the entity does not participate in FRL.

## Eras

There is effectively **one era**: every file (both detail levels) across FY2013 – FY2026 uses the same column set. The District and School files differ only because School files carry one extra column (`School ID - School Name`).

All CSV files share the same structural layout:

- Lines 1–3: Preamble ("Georgia Department Of Education" / "Free and Reduced Price Meal Eligibility" / "Free and Reduced Lunch (FRL) - Fiscal Year YYYY Data Report")
- Line 4: Blank separator (single space)
- Line 5: Header row
- Lines 6..N-4: Data rows
- Last 4 lines: Footer (blank row, then three `Notice:` lines explaining suppression codes)

Files must be read with `skip_rows=4` and a filter to drop the trailing footer rows.

Note: Column headers contain a leading space on ` System Name` (both file types) — treat exactly as `" System Name"` when referencing by name in Polars.

### Era 1 (District level): FY2013 – FY2026

| Column | Description |
|--------|-------------|
| `System ID` | Georgia district / school system identifier. Numeric string; blank (`" "`) on the one State-Wide Total row per file. Mix of 3-digit county / city system codes (e.g. `601` Appling County, `761` Atlanta Public Schools) and 7-digit state-specialty-school identifiers (e.g. `7830618`). |
| ` System Name` | District / system name (leading space in header). `"State-Wide Total"` denotes the statewide aggregate row. |
| `KK-12 % FRL` | Percent of K–12 enrolled students eligible for Free or Reduced-price Lunch. Numeric string on a 0–100 scale. Suppression markers: `*` (rate outside 5%–95% band) and `#` (district does not participate in FRL). |

#### Sample Data (FY2024 District)

```
shape: (5, 3)
┌───────────┬─────────────────────────────────────────────────────────────────────────────────────┬─────────────┐
│ System ID ┆  System Name                                                                        ┆ KK-12 % FRL │
╞═══════════╪═════════════════════════════════════════════════════════════════════════════════════╪═════════════╡
│ 7830618   ┆ State Specialty Schools II- SAIL Charter Academy - School for Arts-Infused Learning ┆ #           │
│ 7830615   ┆ State Specialty Schools II- Genesis Innovation Academy for Boys                     ┆ 81.79       │
│ 620       ┆ Camden County                                                                       ┆ 53.31       │
│ 7830616   ┆ State Specialty Schools II- Genesis Innovation Academy for Girls                    ┆ 72.7        │
│ 771       ┆ Commerce City                                                                       ┆ 60.89       │
└───────────┴─────────────────────────────────────────────────────────────────────────────────────┴─────────────┘
```

#### Statistics (FY2024 District, footer stripped)

- Row count: 236 (235 entities + 1 `State-Wide Total`)
- `KK-12 % FRL` numeric min / max / mean: 5.63 / 94.9 / 68.19
- Suppression: 19 `*`, 8 `#` (FY2024)

#### Null Counts (FY2024 District, footer stripped)

| Column | Nulls |
|--------|-------|
| System ID | 0 |
| System Name | 1 (trailing blank row after the State-Wide Total) |
| KK-12 % FRL | 1 (same trailing blank row) |

#### Categorical Columns (District)

| Column | Distinct Values |
|--------|----------------|
| ` System Name` | 197 (FY2013) to 237 (FY2026) distinct district / system / specialty-school names. Growth over time reflects new charter / state-specialty schools. `State-Wide Total` appears once per file. |

#### Suppression Markers (District)

| Column | Non-Numeric Values | Meaning |
|--------|-------------------|---------|
| `System ID` | `" "` (blank) | Marks the `State-Wide Total` row (occurs on the row whose name is `State-Wide Total`, plus one fully blank trailing row). |
| `KK-12 % FRL` | `*`, `#` | `*` = rate is > 95% or < 5% (suppressed for student privacy); `#` = entity does not participate in FRL program. |

#### Observed suppression counts by year (District)

| FY | `*` count | `#` count |
|----|-----------|-----------|
| 2013 | 5 | 1 |
| 2024 | 19 | 8 |
| 2025 | ~80 | ~8 (high; see ETL Considerations) |
| 2026 | 89 | 8 |

### Era 1 (School level): FY2013 – FY2026

| Column | Description |
|--------|-------------|
| `System ID` | District code the school belongs to (same format as District files). |
| ` System Name` | District / system name. |
| `School ID - School Name` | Composite "` {SchoolID} - {School Name}`" string — leading space, 4-digit zero-padded school id, " - " separator, then the school name. |
| `KK-12 % FRL` | Same semantics as the District file. |

#### Sample Data (FY2024 School)

```
shape: (5, 4)
┌───────────┬─────────────────┬────────────────────────────────────┬─────────────┐
│ System ID ┆  System Name    ┆ School ID - School Name            ┆ KK-12 % FRL │
╞═══════════╪═════════════════╪════════════════════════════════════╪═════════════╡
│ 715       ┆ Polk County     ┆  0102 - Rockmart High School       ┆ 61.01       │
│ 706       ┆ Muscogee County ┆  4070 - Wynnton Elementary School  ┆ *           │
│ 616       ┆ Bulloch County  ┆  4052 - Portal Middle/High School  ┆ 67.67       │
│ 706       ┆ Muscogee County ┆  0192 - Brewer Elementary School   ┆ *           │
│ 631       ┆ Clayton County  ┆  0277 - Pointe South Middle School ┆ *           │
└───────────┴─────────────────┴────────────────────────────────────┴─────────────┘
```

#### Statistics (FY2024 School, footer stripped)

- Row count: 2,319 (2,318 entities + 1 trailing blank row)
- `KK-12 % FRL` numeric min / max / mean: 5.29 / 94.99 / 62.65
- Suppression: 453 `*`, 14 `#` (FY2024)

#### Null Counts (FY2024 School, footer stripped)

| Column | Nulls |
|--------|-------|
| System ID | 0 |
| System Name | 1 (trailing blank row) |
| School ID - School Name | 1 (trailing blank row) |
| KK-12 % FRL | 1 (trailing blank row) |

#### Categorical Columns (School)

| Column | Distinct Values |
|--------|----------------|
| ` System Name` | ~196 (FY2013) to ~236 (FY2026) distinct district names. No `State-Wide Total` row in School files. |
| `School ID - School Name` | ~2,270 (FY2013) to ~2,316 (FY2026) distinct composite strings. Values carry a leading space and the School ID is not strictly unique across districts — always pair with `System ID` for identity. |

#### Suppression Markers (School)

| Column | Non-Numeric Values | Meaning |
|--------|-------------------|---------|
| `KK-12 % FRL` | `*`, `#` | `*` = >95% or <5% (suppressed); `#` = school does not participate in FRL. |
| `System ID` | `" "` (blank) | Only the trailing blank footer row (no State-Wide row in School files). |

#### Observed suppression counts by year (School)

| FY | `*` count | `#` count |
|----|-----------|-----------|
| 2013 | 194 | 21 |
| 2024 | 453 | 14 |
| 2026 | 966 | 10 |

Suppression rates rise sharply in FY2025 / FY2026 — presumably because Community Eligibility Provision (CEP) coverage pushes more entities above the 95% threshold.

## ETL Considerations

- **Preamble + footer stripping.** Every CSV has a 4-line preamble before the header and 4 trailing rows (1 blank + 3 `Notice:` lines). Read with `pl.read_csv(..., skip_rows=4, infer_schema_length=0)` and then drop rows where `System ID` is a `Notice:` / `-...` value or where the whole row is null. The three Notice lines document the suppression codes and match the markers observed in the data:
  - `-"*" indicates Free and Reduced Lunch (FRL) percentage is either greater than 95% or less than 5%.`
  - `-"NA" indicates school does not participate in the FRL program.` (In practice the data uses `#` for this, not `NA`. Treat both `#` and any stray `NA` as not-applicable.)
- **Header whitespace.** The second column header is `" System Name"` with a leading space. Also, `School ID - School Name` values carry a leading space (e.g. `" 0277 - ..."`). Strip whitespace during transform.
- **`State-Wide Total` row handling.** District files always contain one row with a blank `System ID` and ` System Name` = `State-Wide Total`. This is the only source of state-level FRL and should be routed to a state-level gold fact file (not dropped as noise). There is no analogous state-wide row in School files.
- **Mixed-level data in District files.** The District file contains entries whose `System ID` starts with `782xxxx` / `783xxxx` / `7991895` etc. — these are state-specialty-schools and charter schools that GaDOE treats as their own "system." They are not standard counties but they are still `district`-level rows in this dataset; preserve them in gold at the same detail level unless the downstream crosswalk dictates otherwise.
- **`System ID` format.** Mix of 3-digit (e.g. `601`) and 7-digit (e.g. `7830618`) integer codes. Bronze stores them as strings and they are NOT zero-padded to a common width. Keep as string `district_code` to preserve the GaDOE system identifier exactly.
- **`School ID - School Name` composite.** Split on the first ` - ` to recover the school ID (4-digit zero-padded string) and the school name. The 4-digit school ID is **not** globally unique — e.g. `0100` appears in multiple districts (`Bishop Hall`, `Buford Academy`, `C. W. Davis Middle School`, ...). Compose a unique `school_code` by concatenating `System ID` + School ID (or keep them as two columns with `System ID` in the primary key).
- **Suppression semantics (material to interpretation).** `*` does not mean "small cell"; it specifically means the rate fell outside the 5%–95% band. Downstream users who see `*` should know the value is either very low OR very high — not simply "near zero." Preserve this distinction by mapping `*` to a dedicated `suppressed_out_of_band` flag (or similar) rather than a generic `suppressed` flag if the gold model supports it; otherwise document in metadata.
- **`#` vs participation.** `#` means the entity is not in the FRL program at all. During the CEP era, some schools/districts that appear to "not participate" may actually be CEP-covered under a different mechanism; treat `#` as a non-applicability marker and leave the rate null rather than 0.
- **Year is filename-only.** No year column in any file body. Parse the FY from the filename (`Fiscal Year2024` → 2024) and inject it as `year` during transform. Use `Path.stem` regex like `Fiscal Year(\d{4})`.
- **Fiscal year convention.** `Fiscal Year 2024` is the 2023–2024 school year (Georgia FY ends June 30). Follow the domain-wide convention already used by other georgiainsights topics.
- **Numeric coercion.** `KK-12 % FRL` must be cast with `strict=False` (or via `str.replace` for `*` and `#` → null before cast). Values are floats; a few boundary values like `95` / `5` may appear without decimal places (e.g. `66` in FY2024 School sample).
- **Row count growth.** District file row count grows from 200 (FY2013) → 238 (FY2026) as new charter / state-specialty systems are added. School file row count grows from 2,274 (FY2013) → 2,313 (FY2026) and also churns substantially year-to-year (schools open / close / rename). Do not assume a stable key across years.
- **Duplicate schools.** Spot-check confirmed `School ID - School Name` can reuse names; always dedupe on `(System ID, school_id)` (with year).
- **Consistency check to run during transform.** For each year, the district-level `State-Wide Total` and the enrollment-weighted average of school-level rates should be close; this is a good sanity check but exact matches are not guaranteed (state-wide rate may be sourced from totals rather than averaging).

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| `System ID` | fact_key | `district_code` | GaDOE district / system code. FK to districts dimension. Blank → state-wide row (assign sentinel such as `STATE` or emit to state-level fact file). |
| ` System Name` | dimension_attribute | — | `district_name` in districts dimension (not in fact table). Value `State-Wide Total` flags the statewide row. |
| `School ID - School Name` | fact_key + dimension_attribute | `school_code` / — | Split on first ` - ` → `school_code` (4-digit zero-padded string, FK to schools dimension; combine with `district_code` for uniqueness) and `school_name` (belongs in the schools dimension, not in fact). Only present in School files. |
| `KK-12 % FRL` | fact_metric | `pct_frl` | Float on 0–100 scale. `*` and `#` map to null in fact; retain a companion suppression flag/code column per data-cleaning standards. |
| (filename year) | fact_key | `year` | Extracted from filename `Fiscal Year(\d{4})`. |
| (not present) | fact_key | `detail_level` | `state` / `district` / `school`, derived from file type and `State-Wide Total` row. |

**No demographic breakouts**: this dataset reports a single overall K–12 rate per entity — the gold fact table does not need a `demographic` column (or, equivalently, every row is `All Students`; per domain convention, omit the column rather than carry a constant).

## Corrections (2026-06-12, transform authoring)

Stale or imprecise claims found while re-verifying every invariant against the 28 bronze CSVs:

1. **`NA` does occur in the data.** The claim "In practice the data uses `#` for this, not `NA`. Treat both `#` and any stray `NA` as not-applicable" understates it: `NA` genuinely appears in **FY2016 only** — 2 District cells and 4 School cells (verified cell-by-cell; all other years use `#`). Both map to the same non-participation semantics.
2. **Footer composition.** "Last 4 lines: Footer (blank row, then three `Notice:` lines)" is imprecise: the footer is one near-blank spacer line (a single space), one line reading `Notice:`, and **two** marker-definition lines starting `-"*"` and `-"NA"` (verified identical shape in all 28 files).
3. **Row counts include the footer's blank spacer as a "row".** The doc's "footer stripped" frames kept the blank spacer line as a data row, inflating counts by one and misattributing the entity split:
   - FY2024 District: "236 (235 entities + 1 State-Wide Total)" → true data rows are **235 = 234 entities + 1 State-Wide Total** (the doc's own null-counts table flags the extra row as the "trailing blank row" — that line is the footer's first line, not data).
   - FY2024 School: "2,319 (2,318 entities + 1 trailing blank row)" → true data rows are **2,318**, all entities.
   - Growth figures "District 200 (FY2013) → 238 (FY2026)" and "School 2,274 (FY2013) → 2,313 (FY2026)" → true data rows are **199 → 237** (including the State-Wide Total row) and **2,273 → 2,312**.
4. **FY2025 District suppression counts.** "~80 `*`, ~8 `#`" → exactly **81 `*` and 8 `#`**. (FY2025 School, not tabulated in the doc: 896 `*`, 12 `#`.)
5. **Published value range.** "`KK-12 % FRL` values range approximately 5.09–95.00 across years" → the verified global published range is exactly **[5.00, 95.00]** (min 5.0 in FY2017 and FY2022 School files; max 95.0 in FY2015/2017/2018/2020/2021/2026 School files). All published values respect the 5–95 publication band, so a [0.05, 0.95] band check holds in gold after the /100 rescale.
6. **Rate-cell vocabulary is closed.** Every footer-stripped rate cell in all 28 files is exactly one of: numeric string, `*`, `#`, `NA` — there are **no empty/missing rate cells** in any data row, so a row-level reporting status derived from the cell is never NULL. Also verified: no duplicate (System ID[, school id]) keys within any file, every System ID is 3- or 7-digit (state row aside), and every School composite value matches `^\s*\d{4} - `.
