# Provenance — OJJDP EZACO: Georgia county juvenile court case counts

- **Source tool**: OJJDP Statistical Briefing Book — *Easy Access to State and
  County Juvenile Court Case Counts* (EZACO), built by the National Center for
  Juvenile Justice (NCJJ) from the National Juvenile Court Data Archive.
  <https://ojjdp.ojp.gov/statistical-briefing-book/data-analysis-tools/ezaco/access-case-counts>
- **Actual data endpoint**: the page is a thin JS client over a Socrata-style
  dataset API — `https://api.ojp.gov/ojpdataset/v1/v7hy-xgyt.json` with SoQL
  params (`$where=yr='YYYY' and state='Georgia'`, `$order=fct ASC`). No auth
  or app token required as of retrieval.
- **Retrieved**: 2026-07-02T12:32Z (UTC) via
  `uv run python -m src.etl.criminal_justice.ojjdp.download` (re-runnable;
  discovers offered years from the page's year dropdown; never overwrites
  existing files unless `--refresh`).
- **Files**: `ezaco_ga_county_case_counts_{YYYY}.json` — one verbatim API
  response per year, 1997–2023 (26 files; **2014 returns no Georgia rows from
  the API** — GA did not publish that year). Each file has 160 rows: `fct="0"`
  = Georgia summary row, then 159 county rows (`court` = county name, `fct` =
  county FIPS suffix within GA; full FIPS = `13` + zero-padded `fct`).
- **Fields**: petitioned/non-petitioned case counts for delinquency
  (`petdel`/`nonpetdel`), status offense (`petsta`/`nonpetsta`), dependency
  (`petdep`/`nonpetdep`); per-1,000 rates (`*rate`); population represented
  (`poptot`, `popten` = age 10 through upper age, `popzero` = 0 through upper
  age; GA upper age of juvenile-court jurisdiction = 16, see `age` field);
  `reportingflag_*` = number of counties reporting that measure that year;
  `footnotes` = embedded XML-ish source notes (GA source: Council of Juvenile
  Court Judges of Georgia; delinquency/status/dependency figures are cases
  disposed).

## Caveats (keep verbatim in bronze; handle in transform)

- **~3-year data lag** — most recent year is 2023 as of retrieval.
- **County reporting-coverage gaps**: not all GA juvenile courts report, and
  coverage varies sharply by year (e.g. `reportingflag_petdel` = 152 counties
  in 1997 but only **41 in 2023**). State-row totals are sums over *reporting*
  counties only — never treat them as statewide. Use `reportingflag_*` as the
  coverage flag; never impute non-reporting counties.
- **Small-count suppression kept verbatim**: `*` = primary suppression of cell
  values 1–4; `x` = secondary suppression of values 5–20; `z` = secondary
  suppression of a value >20 (per the tool's own note; the stricter <11 rule
  applies only to California 2021+). `--` = data not available or not reliable
  for publication. Suppressed/unavailable → NULL in transform, never 0.
- Counts contain thousands separators (`"11,708"`) — strings in bronze.
- **Funding-at-risk snapshot**: the Statistical Briefing Book's federal
  funding is at risk — these files are the archival snapshot taken at first
  ingest (2026-07-02). Do not delete even if the tool goes away.

## Citation

Hockenberry, S. and Puzzanchera, C. — *Easy Access to State and County
Juvenile Court Case Counts* (EZACO). Online: OJJDP Statistical Briefing Book.
Georgia data source: Council of Juvenile Court Judges of Georgia, via the
National Juvenile Court Data Archive (NCJJ).
