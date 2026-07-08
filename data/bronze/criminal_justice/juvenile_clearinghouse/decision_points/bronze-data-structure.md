# decision_points — Bronze Data Structure

## Overview

- Topic: decision_points
- Source: juvenile_clearinghouse (Georgia Juvenile Justice Data Clearinghouse)
- Files: 2 CSV files. Raw Data 1: 2010–2025 (309,637 rows); Raw Data 2: 2005–2025 (92,656 rows)
- Unreadable files: none
- Year representation: integer year column in both files (`Period Year` in Raw Data 1, `Year` in Raw Data 2). Calendar year, not school/fiscal year (Raw Data 2 also has a 1–12 `Month` column).
- Filename-to-data year offset: filename carries only the WordPress upload month (`2026-06`), not a data year; each file spans many years internally.
- Detail levels: county only (no state rollup rows; no sub-county geography). Raw Data 1 is **youth-level** (one row per juvenile per year per county per court type); Raw Data 2 is county/year/month aggregate.
- Percentage scale: n/a — all metrics are non-negative integer counts (plus 0/1 indicator flags in Raw Data 1).
- Checksums generated: 2026-07-02

## Source Provenance

Full provenance in the co-located `_provenance.md` (canonical). Summary:

- **Source URL**: <https://juveniledata.georgiacourts.gov/dashboards-reports/> ("Raw Data" section). Resolved file URLs embed the WordPress upload month and change on each refresh — never hardcode; the downloader re-scrapes the landing page.
- **Data dictionary**: <https://juveniledata.georgiacourts.gov/definitions/> (no dictionary ships with the CSVs)
- **Retrieved**: 2026-07-02 (UTC), scripted — `uv run python -m src.etl.criminal_justice.juvenile_clearinghouse.download`
- **Method**: scripted download, files saved verbatim
- **Refresh cadence**: annual (~June)
- Two sibling files exist at the source (`OHP-STP`, `Placements`) — out of scope for this topic; candidate separate topics.

## File Checksums

Generated: 2026-07-02

| File | SHA-256 |
|------|---------|
| decision_points_raw_data_1_2026-06.csv | 1b68c6f0f710529f8bcfd2374b80b6050c0c9da4dbc5767b30dd7d2807e60aa9 |
| decision_points_raw_data_2_2026-06.csv | 206925162f84b0b46f46b8339ef2ac1c84481e9940735be10b09242ef223383d |

## Summary

Juvenile-justice **decision-point counts** for Georgia counties, defined with the US DOJ under the JJDP Act. The two files measure different things at different grains:

- **Raw Data 1 (youth-level, 2010–2025, statewide)**: per-juvenile annual counts of offenses, diversions, delinquent adjudications (misdemeanor + felony), unique adjudication dates, probation orders, commitment orders, petitions, superior-court sentences — plus 0/1 flags for new secure detention (RYDC) / secure confinement (YDC) and an active/terminated status flag. Aggregating these rows to county/year yields both **event counts** (sum) and **unique-youth counts** (row/juvenile counts).
- **Raw Data 2 (county/month aggregate, 2005–2025, partial coverage)**: monthly counts of cases referred, petitioned, adjudicated, diverted, committed, and transferred to superior court, by case type (CHINS vs DELINQUENCY), race, and gender. **Only 65 counties ever appear (44–62 per year, growing over time)** — this is a reporting-counties subset, not statewide.

## Eras

Era structure is per-file, not per-year: each CSV has one stable schema across all its years. Both files start with a UTF-8 BOM (polars `read_csv` handles it transparently; the first header name is clean).

### Era 1: Raw Data 1 — youth-level (2010–2025)

`decision_points_raw_data_1_2026-06.csv` — 309,637 rows × 19 columns.

| Column | Type | Description |
|--------|------|-------------|
| NEWJUVID | str | Pseudonymized juvenile ID (e.g. `C7701105`). **PII-adjacent — never publish; aggregate away.** |
| Period Year | i64 | Calendar year, 2010–2025 |
| County Name | str | UPPERCASE county name; 160 values = 159 GA counties + `OUT OF STATE` |
| Court Type | str | Single-letter code `D` / `I` / `S` — **undocumented at source** (see ETL Considerations) |
| Gender | str | `MALE` / `FEMALE` |
| Gender Code | i64 | 1=MALE, 2=FEMALE (redundant with Gender) |
| Race Value | str | `White`, `Black`, `AmInd`, `Asian`, `Hispanic`, `Other` |
| Race Code | i64 | 1=White, 2=Black, 3=AmInd, 4=Asian, 6=Other, 7=Hispanic (5 never appears; redundant with Race Value) |
| Number of offenses | i64 | Offense count for this youth/year/county/court type (min 1 — rows exist only where a youth had contact) |
| Diversions (all types) | i64 | Count of diversions (informal adjustment, abeyance, diverted complaint withheld, mediation, nolle prosequi) |
| Delinquent Adjudications (Misd. And Felony) | i64 | Count of delinquent adjudications |
| Unique Adjudication Date Count | i64 | Distinct adjudication dates |
| Probation orders | i64 | Count of probation orders |
| Commitments orders | i64 | Count of commitment orders |
| Petitions | i64 | Count of petitioned cases |
| Superior Court Sentenced | i64 | Count sentenced in superior court |
| Secure Detention (RYDC) | i64 | **0/1 indicator, not a count** — 1 if the youth's secure placement was RYDC detention; null when no secure placement (98.6% null) |
| Secure Confinement (YDC) | i64 | **0/1 indicator, not a count** — 1 if YDC confinement; mutually exclusive with the RYDC flag (never both 1, never both 0 when non-null) |
| (1)ACTIVE JUVENILE - (0)TERMINATED JUVENILE | i64 | 1=active, 0=terminated (as of the reporting period); part of the row grain |

#### Sample Data

```text
┌───────────┬─────────────┬─────────────┬────────────┬────────┬─────────────┬────────────┬───────────┬────────────────────┬────────────────────────┬──────────────────────┬────────────────────────────────┬──────────────────┬────────────────────┬───────────┬──────────────────────────┬────────────────┬────────────────┬──────────────────┐
│ NEWJUVID  ┆ Period Year ┆ County Name ┆ Court Type ┆ Gender ┆ Gender Code ┆ Race Value ┆ Race Code ┆ Number of offenses ┆ Diversions (all types) ┆ Delinquent Adjudic.  ┆ Unique Adjudication Date Count ┆ Probation orders ┆ Commitments orders ┆ Petitions ┆ Superior Court Sentenced ┆ RYDC           ┆ YDC            ┆ ACTIVE/TERM      │
╞═══════════╪═════════════╪═════════════╪════════════╪════════╪═════════════╪════════════╪═══════════╪════════════════════╪════════════════════════╪══════════════════════╪════════════════════════════════╪══════════════════╪════════════════════╪═══════════╪══════════════════════════╪════════════════╪════════════════╪══════════════════╡
│ I18711865 ┆ 2021        ┆ STEPHENS    ┆ D          ┆ MALE   ┆ 1           ┆ White      ┆ 1         ┆ 1                  ┆ 0                      ┆ 0                    ┆ 0                              ┆ 0                ┆ 0                  ┆ 0         ┆ 0                        ┆ null           ┆ null           ┆ 0                │
│ H16752085 ┆ 2020        ┆ FULTON      ┆ I          ┆ MALE   ┆ 1           ┆ Black      ┆ 2         ┆ 23                 ┆ 0                      ┆ 23                   ┆ 13                             ┆ 0                ┆ 13                 ┆ 13        ┆ 0                        ┆ null           ┆ null           ┆ 0                │
│ D9580645  ┆ 2011        ┆ CHATHAM     ┆ I          ┆ MALE   ┆ 1           ┆ Black      ┆ 2         ┆ 3                  ┆ 0                      ┆ 3                    ┆ 1                              ┆ 0                ┆ 1                  ┆ 1         ┆ 0                        ┆ null           ┆ null           ┆ 0                │
│ I18510065 ┆ 2020        ┆ FORSYTH     ┆ D          ┆ MALE   ┆ 1           ┆ White      ┆ 1         ┆ 1                  ┆ 1                      ┆ 0                    ┆ 0                              ┆ 0                ┆ 0                  ┆ 0         ┆ 0                        ┆ null           ┆ null           ┆ 0                │
│ D8158485  ┆ 2012        ┆ CHATHAM     ┆ I          ┆ MALE   ┆ 1           ┆ Black      ┆ 2         ┆ 1                  ┆ 0                      ┆ 1                    ┆ 1                              ┆ 1                ┆ 0                  ┆ 1         ┆ 0                        ┆ null           ┆ null           ┆ 0                │
└───────────┴─────────────┴─────────────┴────────────┴────────┴─────────────┴────────────┴───────────┴────────────────────┴────────────────────────┴──────────────────────┴────────────────────────────────┴──────────────────┴────────────────────┴───────────┴──────────────────────────┴────────────────┴────────────────┴──────────────────┘
```

#### Statistics (metric columns)

| Column | mean | std | min | max |
|--------|------|-----|-----|-----|
| Number of offenses | 2.41 | 2.84 | 1 | 179 |
| Diversions (all types) | 0.37 | 0.79 | 0 | 47 |
| Delinquent Adjudications | 1.79 | 2.61 | 0 | 179 |
| Unique Adjudication Date Count | 0.98 | 2.07 | 0 | 156 |
| Probation orders | 0.61 | 1.53 | 0 | 91 |
| Commitments orders | 0.22 | 1.20 | 0 | 155 |
| Petitions | 0.76 | 1.87 | 0 | 156 |
| Superior Court Sentenced | 0.03 | 0.42 | 0 | 39 |
| Secure Detention (RYDC) | 0.80 | — | 0 | 1 |
| Secure Confinement (YDC) | 0.20 | — | 0 | 1 |
| ACTIVE/TERMINATED flag | 0.07 | — | 0 | 1 |

Rows per year decline from ~26,800 (2010) to ~13,000 (2025) — consistent with the statewide decline in juvenile-court contact, with a visible 2020 COVID dip (12,435 rows).

#### Null Counts

All columns 0 nulls except `Secure Detention (RYDC)` and `Secure Confinement (YDC)`: 305,367 null each (non-null only for the 4,270 youth-years with a new secure placement — 3,413 RYDC, 857 YDC). Non-null share holds ~1.3–1.7% of rows through 2022 then drops sharply in 2023–2025 (62/81/72 rows) — treat recent-year secure-placement flags as possibly incomplete.

#### Categorical Columns

| Column | Distinct Values (count) |
|--------|------------------------|
| Court Type | D (222,484), I (63,629), S (23,524) |
| Gender | MALE (210,814), FEMALE (98,823) |
| Race Value | Black (168,546), White (113,077), Hispanic (20,003), Other (7,156), Asian (748), AmInd (107) |
| County Name | 160 values: all 159 GA counties (UPPERCASE) + `OUT OF STATE` |

#### Suppression Markers

None — every metric column parses as clean Int64; no `*`/`N/A`-style markers in either file.

### Era 2: Raw Data 2 — county/month aggregate (2005–2025)

`decision_points_raw_data_2_2026-06.csv` — 92,656 rows × 12 columns.

| Column | Type | Description |
|--------|------|-------------|
| County | str | Title-case county name (e.g. `DeKalb`); 65 distinct counties ever, 44–62 per year |
| Year | i64 | Calendar year, 2005–2025 |
| Month | i64 | 1–12 |
| Case Type | str | `CHINS` (child in need of services) / `DELINQUENCY` |
| Race | str | `WHITE`, `BLACK`, `HISPANIC`, `ASIAN`, `NATAMER`, `OTHER`, `UNKNOWN` + stray `Unknown` (case variant, all years) |
| Gender | str | `Male` / `Female` / `Unknown` |
| Referred | i64 | Cases referred (min 1 — rows exist only where activity occurred) |
| Petitioned | i64 | Cases petitioned |
| Adjudicated | i64 | Cases adjudicated |
| Diverted | i64 | Cases diverted |
| Commitment | i64 | Commitments |
| Superior Court Transfer | i64 | Transfers to superior court |

#### Sample Data

```text
┌──────────┬──────┬───────┬─────────────┬─────────┬────────┬──────────┬────────────┬─────────────┬──────────┬────────────┬─────────────────────────┐
│ County   ┆ Year ┆ Month ┆ Case Type   ┆ Race    ┆ Gender ┆ Referred ┆ Petitioned ┆ Adjudicated ┆ Diverted ┆ Commitment ┆ Superior Court Transfer │
╞══════════╪══════╪═══════╪═════════════╪═════════╪════════╪══════════╪════════════╪═════════════╪══════════╪════════════╪═════════════════════════╡
│ Rockdale ┆ 2023 ┆ 6     ┆ DELINQUENCY ┆ BLACK   ┆ Male   ┆ 7        ┆ 6          ┆ 5           ┆ 1        ┆ 2          ┆ 0                       │
│ Paulding ┆ 2008 ┆ 12    ┆ DELINQUENCY ┆ OTHER   ┆ Female ┆ 1        ┆ 0          ┆ 0           ┆ 0        ┆ 0          ┆ 0                       │
│ Chatham  ┆ 2016 ┆ 9     ┆ DELINQUENCY ┆ OTHER   ┆ Male   ┆ 1        ┆ 1          ┆ 1           ┆ 0        ┆ 0          ┆ 0                       │
│ Paulding ┆ 2008 ┆ 5     ┆ CHINS       ┆ Unknown ┆ Male   ┆ 1        ┆ 0          ┆ 0           ┆ 0        ┆ 0          ┆ 0                       │
│ Clayton  ┆ 2006 ┆ 11    ┆ CHINS       ┆ WHITE   ┆ Female ┆ 3        ┆ 0          ┆ 0           ┆ 0        ┆ 0          ┆ 0                       │
└──────────┴──────┴───────┴─────────────┴─────────┴────────┴──────────┴────────────┴─────────────┴──────────┴────────────┴─────────────────────────┘
```

#### Statistics (metric columns)

| Column | mean | std | min | max |
|--------|------|-----|-----|-----|
| Referred | 8.83 | 21.66 | 1 | 726 |
| Petitioned | 4.12 | 11.60 | 0 | 269 |
| Adjudicated | 2.30 | 7.08 | 0 | 138 |
| Diverted | 1.06 | 3.39 | 0 | 87 |
| Commitment | 0.42 | 1.84 | 0 | 45 |
| Superior Court Transfer | 0.008 | 0.18 | 0 | 25 |

Funnel sanity holds everywhere: no row has Petitioned > Referred or Adjudicated > Petitioned.

#### Null Counts

Zero nulls in every column.

#### Categorical Columns

| Column | Distinct Values (count) |
|--------|------------------------|
| Case Type | DELINQUENCY (55,305), CHINS (37,351) |
| Race | WHITE (31,202), BLACK (31,180), HISPANIC (14,273), OTHER (6,575), UNKNOWN (5,214), ASIAN (2,472), Unknown (1,343), NATAMER (397) |
| Gender | Male (49,359), Female (41,344), Unknown (1,953) |
| County | 65 distinct Title-case names (subset of GA counties; no OUT OF STATE) |

#### Suppression Markers

None.

## Row Grain

- **Raw Data 1**: nominal grain `NEWJUVID × Period Year × County Name × Court Type × active/terminated flag` (gender/race are attributes of the youth, not grain). Even with the flag, **381 duplicate-key rows remain** (of which 38 are byte-identical duplicate rows); the rest are same-key pairs with different metric values — the same youth apparently reported in segments within a year. **Aggregation by SUM (not row-dedup) is the safe reduction**; dropping only the 38 exact duplicates is defensible but the transform should decide and log it.
- **Raw Data 2**: `County × Year × Month × Case Type × Race × Gender` is exactly unique (92,656 rows = 92,656 keys) **before** the `UNKNOWN`/`Unknown` race-case merge; after normalizing case, re-aggregate with SUM to restore uniqueness.

## ETL Considerations

1. **Two incompatible schemas → likely two gold fact tables** (or two topics). Raw Data 1 aggregates to a youth-based county/year table (event counts + unique-youth counts); Raw Data 2 is a county/year(/month) case-flow table. They measure different universes (statewide youth-level vs 65 self-reporting counties' case counts) and different periods (2010–2025 vs 2005–2025). Do not union them.
2. **PII: `NEWJUVID` must never reach gold.** Aggregate to county/year (× demographic/categorical) during transform. Note that county × year × court type × race × gender cells are often tiny (1–2 youths) — consider whether a small-cell suppression policy is needed before serving, per project privacy standards for juvenile data.
3. **`Court Type` codes `D`/`I`/`S` are undocumented.** Neither the definitions page nor the raw-data landing page defines them (verified 2026-07-02). Plausible reading — D = DJJ-served court, I = independent juvenile court, S = superior-court-judge-served — matches Georgia's juvenile-court administration models but is **unverified; do not bake labels into gold without confirmation** (contact the Clearinghouse or find the JDEX codebook). Safe options: keep the raw letter as a categorical with documented unknown semantics, or sum over it.
4. **RYDC/YDC columns are 0/1 indicator flags, not counts** (mutually exclusive: 3,413 RYDC vs 857 YDC among 4,270 non-null rows; null = no new secure placement). At county/year aggregation they become "youths with a new secure detention/confinement" counts (sum of flags). Blank ≠ zero at bronze, but for aggregation null→0 is the correct reading. Their non-null share collapses in 2023–2025 — flag recent secure-placement counts as possibly incomplete in the contract limitations.
5. **Race schemes differ between files and from the project demographic vocabulary.** Raw Data 1: `White/Black/AmInd/Asian/Hispanic/Other` (codes 1,2,3,4,6,7; code 5 never appears). Raw Data 2 adds `UNKNOWN` (+ case-variant `Unknown`) and uses `NATAMER`. **No Pacific Islander bucket exists in either file** and the §5b math test is inapplicable (no total rows; youth-level/aggregate counts only). Because both files carry an explicit `Other` catch-all and the data is modern (2005+), PI most plausibly lands in `Other`; recommended mapping is `Asian → asian` with a documented caveat, but flag this for the data review rather than silently deciding. Hispanic is a mutually-exclusive race bucket here (per the source: "All races except Hispanic are populations not considered Hispanic").
6. **Race case-folding in Raw Data 2**: `UNKNOWN` (5,214) and `Unknown` (1,343) are the same category split by casing across all years — normalize case **then re-aggregate with SUM**, or the county/year/month grain breaks.
7. **County names, not FIPS.** Raw Data 1 is UPPERCASE, Raw Data 2 Title case. `src/utils/crosswalks.add_county_fips` resolves all names in both files except `OUT OF STATE` (Raw Data 1 only) — decide whether to keep out-of-state youths as a NULL-FIPS row set or drop with logging.
8. **Raw Data 2 coverage is a growing 65-county subset (44 in 2005 → ~60 in 2025).** Year-over-year statewide sums are NOT comparable — the panel is unbalanced. This must be prominent in the contract `limitations`, and argues for the county (not state) level being the only honest serving grain for this file.
9. **Duplicate keys in Raw Data 1** (see Row Grain): 38 exact duplicate rows + 343 same-key/different-values pairs. SUM-aggregation absorbs the latter; decide and log handling of the exact duplicates.
10. **Raw Data 1 metric semantics**: `Number of offenses` has min 1 (a row exists only if the youth had ≥1 offense); other metrics are 0-heavy. `Delinquent Adjudications` counts charge-level adjudications while `Unique Adjudication Date Count` counts distinct dates — keep names that preserve the distinction.
11. **UTF-8 BOM** at the start of both files — harmless with polars `read_csv` (header parses clean), but don't read headers with naive `open()` string-matching.
12. **Never hardcode source URLs** — the WordPress upload path changes each refresh; the downloader re-scrapes the landing page (see `_provenance.md`).

## Gold Schema Classification

Assuming two fact tables (working names: `juvenile_decision_points_youth` from Raw Data 1, aggregated to county/year; `juvenile_case_flow` from Raw Data 2):

### Raw Data 1 (youth-level → county/year aggregate)

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| NEWJUVID | not_in_gold | — | PII-adjacent; consumed by aggregation (drives unique-youth counts) |
| Period Year | fact_key | year | Calendar year |
| County Name | fact_key | county_fips | Via `add_county_fips`; decide `OUT OF STATE` handling |
| Court Type | fact_categorical | court_type | Raw `D`/`I`/`S` codes undocumented — verify labels or aggregate over it (ETL #3) |
| Gender | fact_key | demographic | → demographics dimension (`male`/`female`); race+gender likely serve as two demographic breakdowns per project standards |
| Gender Code | not_in_gold | — | Redundant with Gender |
| Race Value | fact_key | demographic | → demographics dimension; `Asian` mapping caveat (ETL #5); `AmInd` → `american_indian_alaska_native`; `Other` → project `other` bucket |
| Race Code | not_in_gold | — | Redundant with Race Value |
| Number of offenses | fact_metric | offense_count | Sum; unit: count |
| Diversions (all types) | fact_metric | diversion_count | Sum; unit: count |
| Delinquent Adjudications (Misd. And Felony) | fact_metric | delinquent_adjudication_count | Sum; unit: count |
| Unique Adjudication Date Count | fact_metric | adjudication_date_count | Sum; unit: count |
| Probation orders | fact_metric | probation_order_count | Sum; unit: count |
| Commitments orders | fact_metric | commitment_order_count | Sum; unit: count |
| Petitions | fact_metric | petition_count | Sum; unit: count — candidate key metric alongside a derived `youth_count` |
| Superior Court Sentenced | fact_metric | superior_court_sentenced_count | Sum; unit: count |
| Secure Detention (RYDC) | fact_metric | secure_detention_youth_count | Sum of 0/1 flag (null→0) = youths with new RYDC detention; incomplete 2023–2025 (ETL #4) |
| Secure Confinement (YDC) | fact_metric | secure_confinement_youth_count | Sum of 0/1 flag (null→0); same caveat |
| (1)ACTIVE JUVENILE - (0)TERMINATED JUVENILE | not_in_gold (or fact_metric) | active_youth_count | Either sum-aggregate as a metric or drop; not a serving-grain categorical |
| *(derived)* | fact_metric | youth_count | `n_unique(NEWJUVID)` per cell — the natural headline metric |

### Raw Data 2 (county/year/month case flow)

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| County | fact_key | county_fips | Via `add_county_fips`; all 65 names resolve |
| Year | fact_key | year | |
| Month | fact_categorical (or not_in_gold) | month | Keep for monthly grain, or sum to annual — decide at transform; annual is likelier the serving grain |
| Case Type | fact_categorical | case_type | `chins` / `delinquency` |
| Race | fact_key | demographic | Case-fold `UNKNOWN`/`Unknown` then re-aggregate (ETL #6); `NATAMER` → `american_indian_alaska_native`; same Asian caveat |
| Gender | fact_key | demographic | `male`/`female`/`unknown` |
| Referred | fact_metric | referred_count | Sum; unit: count — natural key-metric candidate (top of funnel) |
| Petitioned | fact_metric | petitioned_count | Sum; unit: count |
| Adjudicated | fact_metric | adjudicated_count | Sum; unit: count |
| Diverted | fact_metric | diverted_count | Sum; unit: count |
| Commitment | fact_metric | commitment_count | Sum; unit: count |
| Superior Court Transfer | fact_metric | superior_court_transfer_count | Sum; unit: count |
