# juvenile_court_cases — Bronze Data Structure

## Overview

- Topic: juvenile_court_cases
- Source: ojjdp (EZACO — Easy Access to State and County Juvenile Court Case Counts, NCJJ/National Juvenile Court Data Archive)
- Files: 26 JSON files spanning 1997–2023 (**2014 missing** — the API returns no Georgia rows for that year; GA did not publish)
- Unreadable files: none
- Year representation: `yr` column in the data (4-digit calendar year, e.g. `"2023"`); filename also carries the year
- Filename-to-data year offset: same — filename year matches `yr` in every file
- Detail levels: state (single `fct = "0"` row per file) and county (159 rows, `fct` = GA county FIPS suffix)
- Percentage scale: no percentages; `*rate` columns are **cases per 1,000 juveniles** (not 0–1 or 0–100)
- Checksums generated: 2026-07-02

## Source Provenance

- **Source URL**: <https://ojjdp.ojp.gov/statistical-briefing-book/data-analysis-tools/ezaco/access-case-counts> — actual data endpoint is the Socrata-style API `https://api.ojp.gov/ojpdataset/v1/v7hy-xgyt.json` with SoQL params (`$where=yr='YYYY' and state='Georgia'`, `$order=fct ASC`)
- **Retrieved**: 2026-07-02 (UTC) — archival snapshot; the Statistical Briefing Book's federal funding is at risk, do not delete these files even if the tool goes away
- **Method**: scripted fetch — `uv run python -m src.etl.criminal_justice.ojjdp.download` (re-runnable; never overwrites unless `--refresh`). Full details in `_provenance.md` alongside this report.

## File Checksums

Generated: 2026-07-02

| File | SHA-256 |
|------|---------|
| ezaco_ga_county_case_counts_1997.json | c20599355fcb4f3f0e719fdd51e6506fa2477fec087671f802bccfceef13c010 |
| ezaco_ga_county_case_counts_1998.json | a7e96f04796c4e8ea42a8b8af2c17dcb6f3083d7d2fef021df6cacb1a9dd2d3d |
| ezaco_ga_county_case_counts_1999.json | a6dcc5f0c5544c26e2e05e9248c0e3530139762fe03fcc5f63f1f406133cb984 |
| ezaco_ga_county_case_counts_2000.json | ba96e05781323a55784ecb0ad8d86d16af731ee8b84cd45cc65f64dbb44e3ca3 |
| ezaco_ga_county_case_counts_2001.json | 3a953f4cf7ca539d7df3057f79f58bb7394987e2d1c87f5949cbb6a9257fab6d |
| ezaco_ga_county_case_counts_2002.json | 0826ae303b8c81bdbe69a49f8168173f336522f2521b4e6acf763fe5d078415c |
| ezaco_ga_county_case_counts_2003.json | 6226dab2e2e7a0b6d34277e676087b5ce641f15c816adc1da2fd1d5584aaaddd |
| ezaco_ga_county_case_counts_2004.json | 4bef697b378c7ea60963f558f1234ef5403de35901de9676c842a54b059fec7b |
| ezaco_ga_county_case_counts_2005.json | ccc1340ff0edfb05fa786de82a55f9f0ddcf1cbdcd732d49aaf6c31f810c6288 |
| ezaco_ga_county_case_counts_2006.json | f073ea18c8a02f46b1883d13947e4c3e65925e3a1466fa5328107c2d6519a442 |
| ezaco_ga_county_case_counts_2007.json | dde56588d5863ac70237c752032f9233013775973e18bea6a5e68547a9b4d44a |
| ezaco_ga_county_case_counts_2008.json | ad391fccf9953314a892e1f0fbf42f93a754ae9c91a0ce66350030c2c09daa7c |
| ezaco_ga_county_case_counts_2009.json | 225e459773318067b6b5d5058896b70f089b1e7300efa40ff4d7d2ee06b6c380 |
| ezaco_ga_county_case_counts_2010.json | e45ee986e4b651a1c37608cbc36d464c6fa01c5040c76aa6c886813a47d6539c |
| ezaco_ga_county_case_counts_2011.json | 1f4591fbd745898f00a47d6369effaf500406d29bbe55a549a9c77ce882dea74 |
| ezaco_ga_county_case_counts_2012.json | d2390a7abe536453a5e73a3ccaa3bbdacca91f43f9c25ace6dfb297b01625574 |
| ezaco_ga_county_case_counts_2013.json | 469485ea352b3f512ec9444f5ab0ecdc8528d337bf5d7ee3b8b2c9a7c15a6bd1 |
| ezaco_ga_county_case_counts_2015.json | 24c1863982386c9ada3cb775254328eacb5d06be7535c59a9ee08ddcacf8d279 |
| ezaco_ga_county_case_counts_2016.json | 7c223e28d3172e1a8a515329c8881e6ee65f193b450e6595f64a741382d85f05 |
| ezaco_ga_county_case_counts_2017.json | 7824ebfc72557e66567bd7a4af2809ede0e0a83d971dae10978ddc427108a20b |
| ezaco_ga_county_case_counts_2018.json | deeb1d85046a931fabff0d9b9058cb03392b5d6cfed50c876e4df323c2f5e813 |
| ezaco_ga_county_case_counts_2019.json | 50977a683aa37ba00b0f0fa30ce1106b97fb47734495f902e7d6f9fab8fa55e1 |
| ezaco_ga_county_case_counts_2020.json | bcc5906c943c6a6cfa88a4b27e8568b32f8ed1ade131ea6f61038ef20a7cba18 |
| ezaco_ga_county_case_counts_2021.json | eeef62d09ce10219d471884acffd281534787d45da1742bc142fd028bd81e179 |
| ezaco_ga_county_case_counts_2022.json | 67230ff087ea4a6a2a6683417c51918717804566026034b09f3576386ee4dfb3 |
| ezaco_ga_county_case_counts_2023.json | a76d8e7fddef4b6e0366dadbc993dc9e94d884587ba40447e1f9eae376394af9 |

## Summary

Juvenile court **cases disposed** per Georgia county per calendar year, split by
case type — **delinquency**, **status offense**, **dependency** — and by whether
the case was **petitioned** (formally handled) or **non-petitioned** (informally
handled): six count metrics (`petdel`, `nonpetdel`, `petsta`, `nonpetsta`,
`petdep`, `nonpetdep`). The state row also carries per-1,000-juvenile **rates**
for each measure (county rows never do) plus juvenile population denominators
(`poptot`, `popten`, `popzero`). GA's upper age of juvenile-court jurisdiction
is 16 (`age` column, constant). Source: Council of Juvenile Court Judges of
Georgia via the National Juvenile Court Data Archive.

The dataset's defining hazard is **reporting coverage**: only a subset of GA's
159 county juvenile courts report each year, swinging from 152 counties (1997)
to 25 (2009) to 41 (2023). The `reportingflag_*` fields carry the coverage
signal.

## Eras

### Era 1: 1997–2023 (single era — identical 38-key schema in all 26 files)

Each file is a JSON array of 160 objects: 1 state summary row (`fct = "0"`,
no `court` key) + 159 county rows. **All values are strings**, including counts
(with thousands separators, e.g. `"11,708"`).

| Column | Description |
|--------|-------------|
| `yr` | Calendar year of the data (`"1997"`–`"2023"`) |
| `state` | Constant `"Georgia"` |
| `st` | Constant `"GA"` |
| `fst` | State FIPS, constant `"13"` |
| `fct` | County FIPS suffix within GA (`"0"` = state row; `"1"`–`"321"`, not zero-padded, all odd). Full county FIPS = `"13"` + `fct` zero-padded to 3 |
| `court` | County name (e.g. `"Appling"`); **absent** on the state row |
| `age` | Upper age of juvenile-court jurisdiction, constant `"16"` |
| `unit`, `unit_2` | Constant `"Counties"` |
| `print_state` | Constant `"1"` (display flag) |
| `poptot` | Total resident population |
| `popten` | Juvenile population age 10 through upper age (delinquency/status denominator) |
| `popzero` | Juvenile population age 0 through upper age (dependency denominator) |
| `poptenpetdel`, `poptennonpetdel`, `poptenpetsta`, `poptennonpetsta` | Age-10+ juvenile population **represented by reporting counties** for that measure (state row); `--` on county rows |
| `popzeropetdep`, `popzerononpetdep` | Age-0+ juvenile population represented by reporting counties (dependency) |
| `petdel` / `nonpetdel` | Petitioned / non-petitioned **delinquency** cases disposed |
| `petsta` / `nonpetsta` | Petitioned / non-petitioned **status offense** cases disposed |
| `petdep` / `nonpetdep` | Petitioned / non-petitioned **dependency** cases disposed |
| `petdelrate`, `nonpetdelrate`, `petstarate`, `nonpetstarate`, `petdeprate`, `nonpetdeprate` | Cases per 1,000 juveniles; **numeric only on the state row**, always `--` on county rows |
| `reportingflag_petdel` … `reportingflag_nonpetdep` | State row: **count** of counties reporting that measure; county rows: **0/1 indicator** of whether that county reported |
| `footnotes` | Embedded XML-ish source notes (source attribution + "cases disposed" definitions); identical semantics across rows |

#### Sample Data (2023, `footnotes` dropped)

```text
┌──────┬─────────┬─────┬──────────┬─────┬─────┬─────┬─────────┬────────┬─────────┬────────┬───────────┬────────┬───────────┬────────┬───────────┬──────────────────────┬────────────┬──────────┐
│ yr   ┆ state   ┆ age ┆ unit     ┆ fst ┆ fct ┆ st  ┆ poptot  ┆ popten ┆ popzero ┆ petdel ┆ nonpetdel ┆ petsta ┆ nonpetsta ┆ petdep ┆ nonpetdep ┆ reportingflag_petdel ┆ petdelrate ┆ court    │
╞══════╪═════════╪═════╪══════════╪═════╪═════╪═════╪═════════╪════════╪═════════╪════════╪═══════════╪════════╪═══════════╪════════╪═══════════╪══════════════════════╪════════════╪══════════╡
│ 2023 ┆ Georgia ┆ 16  ┆ Counties ┆ 13  ┆ 255 ┆ GA  ┆ 69,900  ┆ 6,500  ┆ 15,300  ┆ 94     ┆ 21        ┆ *      ┆ 7         ┆ --     ┆ --        ┆ 1                    ┆ --         ┆ Spalding │
│ 2023 ┆ Georgia ┆ 16  ┆ Counties ┆ 13  ┆ 237 ┆ GA  ┆ 23,100  ┆ 1,900  ┆ 4,100   ┆ --     ┆ --        ┆ --     ┆ --        ┆ --     ┆ --        ┆ 0                    ┆ --         ┆ Putnam   │
│ 2023 ┆ Georgia ┆ 16  ┆ Counties ┆ 13  ┆ 29  ┆ GA  ┆ 49,700  ┆ 5,900  ┆ 13,300  ┆ --     ┆ --        ┆ --     ┆ --        ┆ --     ┆ --        ┆ 0                    ┆ --         ┆ Bryan    │
│ 2023 ┆ Georgia ┆ 16  ┆ Counties ┆ 13  ┆ 239 ┆ GA  ┆ 2,300   ┆ 200    ┆ 400     ┆ --     ┆ --        ┆ --     ┆ --        ┆ --     ┆ --        ┆ 0                    ┆ --         ┆ Quitman  │
│ 2023 ┆ Georgia ┆ 16  ┆ Counties ┆ 13  ┆ 59  ┆ GA  ┆ 129,900 ┆ 8,400  ┆ 20,400  ┆ 212    ┆ 100       ┆ 29     ┆ 51        ┆ --     ┆ --        ┆ 1                    ┆ --         ┆ Clarke   │
└──────┴─────────┴─────┴──────────┴─────┴─────┴─────┴─────────┴────────┴─────────┴────────┴───────────┴────────┴───────────┴────────┴───────────┴──────────────────────┴────────────┴──────────┘
```

(Wide-table columns elided for readability; every row carries all 6 count
metrics, 6 rate columns, 6 reporting flags, and the 6 reporting-population
columns shown in the column table above.)

#### Statistics (2023, counts cleaned of commas and cast, all 160 rows)

```text
┌────────────┬───────────────┬──────────────┬──────────────┬─────────────┬────────────┬────────────┬────────────┬────────┬───────────┐
│ statistic  ┆ poptot        ┆ popten       ┆ popzero      ┆ petdel      ┆ nonpetdel  ┆ petsta     ┆ nonpetsta  ┆ petdep ┆ nonpetdep │
╞════════════╪═══════════════╪══════════════╪══════════════╪═════════════╪════════════╪════════════╪════════════╪════════╪═══════════╡
│ count      ┆ 160.0         ┆ 160.0        ┆ 160.0        ┆ 42.0        ┆ 38.0       ┆ 36.0       ┆ 35.0       ┆ 0.0    ┆ 0.0       │
│ null_count ┆ 0.0           ┆ 0.0          ┆ 0.0          ┆ 118.0       ┆ 122.0      ┆ 124.0      ┆ 125.0      ┆ 160.0  ┆ 160.0     │
│ mean       ┆ 137866.25     ┆ 13136.25     ┆ 29778.125    ┆ 557.5       ┆ 187.2      ┆ 126.3      ┆ 117.8      ┆ null   ┆ null      │
│ min        ┆ 1600.0        ┆ 100.0        ┆ 300.0        ┆ 0.0         ┆ 0.0        ┆ 0.0        ┆ 0.0        ┆ null   ┆ null      │
│ max        ┆ 1.10292e7     ┆ 1.0507e6     ┆ 2.3821e6     ┆ 11708.0     ┆ 3558.0     ┆ 2282.0     ┆ 2069.0     ┆ null   ┆ null      │
└────────────┴───────────────┴──────────────┴──────────────┴─────────────┴────────────┴────────────┴────────────┴────────┴───────────┘
```

(Max values are the state summary row. Non-null counts track reporting coverage
— 41 reporting counties + state row in 2023, minus suppressed cells.)

#### Null Counts

Raw JSON has no nulls except `court`, which is absent on the state row (1 per
file). All other missingness is encoded as string markers (`--`, `*`, `x`, `z`)
inside otherwise-numeric columns.

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| `yr` | 1997–2023 excluding 2014 (26 values, one per file, matches filename) |
| `court` | 159 GA county names (state row omits the key) |
| `fct` | `0` (state) + 159 odd values `1`–`321` (county FIPS suffixes) |
| `fst` | `13` (constant) |
| `state` / `st` | `Georgia` / `GA` (constant) |
| `age` | `16` (constant) |
| `unit` / `unit_2` | `Counties` (constant) |
| `print_state` | `1` (constant) |
| `reportingflag_*` (county rows) | `0`, `1` |

#### Suppression Markers

Union over all 26 files:

| Column(s) | Non-Numeric Values |
|-----------|-------------------|
| `petdel`, `nonpetdel`, `petsta`, `nonpetsta`, `nonpetdep` | `*`, `--`, `x` |
| `petdep` | `*`, `--`, `x`, `z` |
| all 6 `*rate` columns | `--` |
| `poptenpetdel`, `poptennonpetdel`, `poptenpetsta`, `poptennonpetsta`, `popzeropetdep`, `popzerononpetdep` | `--` |

Marker meanings (from the tool's own legend, recorded in `_provenance.md`):
`*` = primary suppression of cell values 1–4; `x` = secondary suppression of
values 5–20; `z` = secondary suppression of a value >20; `--` = data not
available / not reliable for publication (also used for every non-reporting
county). All → NULL in transform, **never 0**.

## Detail Levels

- **State** — one row per file, `fct = "0"`, no `court` key. Its counts are
  sums over **reporting counties only**, not statewide totals. Verified:
  state `petdel` ≥ sum of visible county `petdel`, with the gap explained by
  suppressed county cells (e.g. 1997: 61,619 vs 61,612 visible + 3 suppressed
  cells; 2023: exact match, 0 suppressed).
- **County** — 159 rows per file (every GA county appears every year, even
  non-reporting ones, whose measures are all `--`).

## Year Representation

- `yr` column, 4-digit calendar year string; matches the filename year exactly.
- Calendar year, not school/fiscal year. Figures are **cases disposed** during
  that year.
- 2014 absent (API returns no GA rows; GA did not publish that year).

## Asian / Pacific Islander Check

Not applicable — this dataset has no demographic breakdowns at all (no race,
sex, or age subgroups). Grain is year × county × (case type × petition status
as wide columns).

## ETL Considerations

1. **Every value is a string.** Counts and populations carry thousands
   separators (`"11,708"`) — strip commas before casting. Cast with
   `strict=False` after mapping the four suppression markers to NULL, and log
   NULLed counts per marker.
2. **Suppression markers `*`, `x`, `z`, `--` → NULL, never 0.** `--` doubles
   as "county did not report" — the `reportingflag_*` columns distinguish
   non-reporting (`0`) from reporting-but-suppressed (`1` with a `*`/`x`/`z`
   value). Genuine zeros do occur (e.g. `petdel = "0"`), so 0 vs NULL is
   meaningful.
3. **Reporting coverage is the headline caveat.** Reporting counties range
   from 152 (1997) to 25 (2009) to 41 (2023); dependency measures drop to 0
   reporting counties in 2015 and 2019, and 2021–2023. Non-petitioned measures have 0
   reporting counties for 1997–2000 and 2010–2013. State-row totals are sums
   over reporting counties only — **never present them as statewide totals**,
   and never impute non-reporting counties. Consider carrying the county-row
   0/1 `reportingflag_*` (or a derived `reported` categorical) into gold so
   API users can distinguish "didn't report" from "reported zero" — at minimum
   the per-county flags must inform NULL handling.
4. **Rates are state-row only.** All 6 `*rate` columns are `--` on all county
   rows in all 26 years — verified programmatically. Rates cannot be a
   county-grain key metric; either recompute county rates from counts +
   `popten`/`popzero` (only for reporting counties) or keep counts as the
   metrics. Note state-row rates are per 1,000 juveniles of the relevant
   population *represented by reporting counties* (`popten<measure>` /
   `popzero<measure>` denominators), not the full state juvenile population.
5. **County FIPS assembly**: `fct` is a bare, non-zero-padded integer string
   (`"1"`–`"321"`, all odd = valid GA county suffixes). Full 5-digit FIPS =
   `"13" + fct.zfill(3)`. `fct = "0"` is the state row (state FIPS `13`).
6. **`reportingflag_*` semantics differ by row level**: count of reporting
   counties on the state row; 0/1 indicator on county rows. Don't sum or mix
   them.
7. **State row lacks the `court` key** — when reading JSON into polars,
   ensure schema inference doesn't fail on the missing key (read the full
   array; the missing key becomes NULL).
8. **2014 gap**: no file exists. The gold year sequence will have a hole —
   this is source truth, not a pipeline bug. Don't interpolate.
9. **Constants to drop**: `state`, `st`, `fst`, `age`, `unit`, `unit_2`,
   `print_state`, `footnotes` are constant or metadata-only. The `age = 16`
   jurisdiction bound and "cases disposed" definition belong in contract
   prose/limitations, not in fact columns.
10. **Wide → tidy**: the 6 count columns encode two categoricals — case type
    (`delinquency` / `status_offense` / `dependency`) and petition status
    (`petitioned` / `non_petitioned`). Unpivoting to
    `year × county × case_type × petition_status` grain with a single count
    metric fits the star schema better than 6 metric columns; the matching
    reporting flags and reporting-population columns unpivot along the same
    keys.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| `yr` | fact_key | `year` | Int, calendar year |
| `fct` (+ `fst`) | fact_key | `county_fips` | `"13" + fct.zfill(3)`; FK to counties dimension; `fct="0"` state row → state-level handling per CJ county-grain conventions |
| `court` | dimension_attribute | — | County name lives in the counties dimension |
| `petdel`, `nonpetdel`, `petsta`, `nonpetsta`, `petdep`, `nonpetdep` | fact_metric | `case_count` (tidy) | Unpivot to case_type × petition_status; unit: count; suppressed → NULL |
| (derived from column name) | fact_categorical | `case_type` | `delinquency` / `status_offense` / `dependency` |
| (derived from column name) | fact_categorical | `petition_status` | `petitioned` / `non_petitioned` |
| `reportingflag_*` (county rows) | fact_categorical or fact_metric | `reported` (0/1) | Distinguishes non-reporting from reported-zero/suppressed; unpivots with the same keys |
| `reportingflag_*` (state row) | not_in_gold (or limitations metadata) | — | Count of reporting counties; derivable by summing county flags |
| `*rate` columns | not_in_gold | — | State-row only, denominator is reporting-coverage-dependent; recompute if needed |
| `poptot`, `popten`, `popzero` | not_in_gold (candidate fact_metric) | — | Census-derived denominators; keep only if county rates are computed in gold |
| `poptenpetdel` … `popzerononpetdep` | not_in_gold | — | State-row reporting-coverage denominators; coverage documented in limitations |
| `state`, `st`, `fst`, `age`, `unit`, `unit_2`, `print_state` | not_in_gold | — | Constants |
| `footnotes` | not_in_gold | — | Source attribution + "cases disposed" notes → contract prose |
