# Provenance — Georgia Sheriffs' Association monthly county jail report

## Source

- **Publisher**: Georgia Sheriffs' Association (GSA)
- **URL**: <https://georgiasheriffs.org/jail-report/>
- **What it is**: Monthly voluntary survey of Georgia's county jails — statewide
  monthly summary, per-county table (all 159 counties: total inmates, capacity,
  % capacity, awaiting trial, state-sentenced held in county jail,
  county-sentenced, other), a 12-month statewide trend, and an annual-totals
  series (2016 onward).

## Retrieval

- **First retrieved**: 2026-07-02 (UTC), current report month **June 2026**.
- **Method**: `uv run python -m src.etl.criminal_justice.jails.jail_population.download`
  (plain HTTPS GET via `requests`; no auth, no JS rendering needed — the
  per-county table is server-rendered HTML).
- **Re-runnable**: yes. Each run archives the current report month (parsed from
  the on-page heading) and skips months already on disk. Existing files are
  never overwritten.

## Historical archive — past months ARE retrievable

The blueprint expected no on-page history beyond annual totals, but the page
carries a POST form (`report_year` 2007–present, `report_month`) that serves
any past month's full report page. `download.py --backfill` sweeps this
archive from 2007-01 forward:

- Months whose page contains a populated per-county table are saved as
  `jail_report_{YYYY-MM}.html`.
- Early months (e.g. 2007) return all-zero pages with **no county rows** —
  these are logged and **not** saved. The saved files therefore start at the
  first month the archive actually has data for.
- Verified spot-checks: March 2019 returns a fully populated 159-county page;
  January 2007 returns an empty all-zero page.

## Files

| Pattern | Contents |
| ------- | -------- |
| `jail_report_{YYYY-MM}.html` | Raw report page for that report month, verbatim — **canonical bronze artifact**. Contains the statewide summary table, the 159-row per-county table, the 12-month statewide trend (Google Charts JS array), and the annual-totals series (Google Charts JS array). |
| `jail_report_{YYYY-MM}.pdf` | Posted PDF for the month, if the page links one. **No PDF was linked as of 2026-07** — the downloader checks every run. |
| `annual_totals_{YYYY-MM-DD}.csv` | Convenience extract (snapshot-dated) of the annual-totals series (`year,total_inmates`, currently 2016–2025). The page has **no annual-totals HTML table** — the series exists only inside a Google Charts `arrayToDataTable` JS call, so the raw HTML remains the canonical bronze and this CSV is a verbatim convenience copy. |

## License / terms

No explicit license or data-use terms are posted on the jail-report page or in
the site footer (checked 2026-07-02). The report is published openly by a
nonprofit association of public officials for public consumption. Treat as
publicly available factual data; attribute the Georgia Sheriffs' Association
as the source. No redistribution restriction was found, but no affirmative
open license exists either.

## Caveats (for transform authors)

- **Voluntary, self-reported survey.** Sheriffs' offices report at their own
  discretion; not every county reports every month. Coverage fluctuates —
  e.g. in the June 2026 report only a subset of counties reported (statewide
  capacity 15,985 vs ~52,000 in fully reported months). Non-reporting counties
  appear as rows with **empty cells** (e.g. Fulton in June 2026).
- **"NO JAIL" rows.** Counties without a jail are listed as e.g.
  "Baker - NO JAIL" with zeros — distinguish "no jail" from "did not report".
- **Statewide summary reflects reporters only.** The monthly statewide totals
  are sums over reporting counties, so month-to-month statewide comparisons
  conflate population change with coverage change.
- **County names, not FIPS.** The per-county table uses county names — map via
  the county name→FIPS crosswalk at transform time.
- **Monthly page is overwritten by the source**, but the POST archive
  (2007-present) makes past months recoverable; ongoing monthly archiving here
  starts 2026-07 regardless, so bronze does not depend on the archive form
  staying up.
- **No cleaning at bronze** — all values are saved verbatim as served.
