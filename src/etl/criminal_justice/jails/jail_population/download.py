"""Download the Georgia Sheriffs' Association monthly county jail report to bronze.

Source: https://georgiasheriffs.org/jail-report — an HTML page showing the
current month's statewide summary, a per-county table (all 159 counties), a
12-month statewide trend, and an annual-totals chart (2016 onward). The page
is overwritten by the source each month, but a POST form (``report_year`` /
``report_month``) serves any past month back to 2007 (months before 2010-08
come back as empty all-zero pages with no county rows).

Bronze outputs (``data/bronze/criminal_justice/jails/jail_population/``):

- ``jail_report_{YYYY-MM}.html`` — the raw page for that report month
  (canonical bronze artifact; values verbatim). Default run archives the
  current month; ``--backfill`` sweeps the POST archive for all past months.
- ``jail_report_{YYYY-MM}.pdf`` — the posted PDF for the month, if the page
  links one (none as of 2026-07).
- ``annual_totals_{YYYY-MM-DD}.csv`` — convenience extract of the
  annual-totals series embedded in the page's Google Charts JS (the page has
  no annual-totals HTML table). The HTML remains canonical.

Existing files are never overwritten — each run only adds missing months.

Usage:
    uv run python -m src.etl.criminal_justice.jails.jail_population.download
    uv run python -m src.etl.criminal_justice.jails.jail_population.download --backfill
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)

SOURCE_URL = "https://georgiasheriffs.org/jail-report/"
BRONZE_DIR = Path("data/bronze/criminal_justice/jails/jail_population")
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126 Safari/537.36"
)
# Earliest year offered by the page's archive form.
ARCHIVE_START_YEAR = 2007
# Politeness delay between archive requests (seconds).
REQUEST_DELAY = 0.5

MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
MONTH_TO_NUM = {name: i + 1 for i, name in enumerate(MONTH_NAMES)}

# Heading on every report page, e.g. "... For Their Inmate Population for June, 2026"
REPORT_MONTH_RE = re.compile(
    r"For Their Inmate Population for\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r",?\s+(\d{4})"
)
# County-name cells in the per-county table are styled width:200px.
COUNTY_CELL_RE = re.compile(r'width:200px;?">\s*([^<]+?)\s*<')
# Annual-totals Google Charts data array: ['Year','Total Inmates'],['2016',428203],...
ANNUAL_ARRAY_RE = re.compile(
    r"\[\s*'Year'\s*,\s*'Total Inmates'\s*\](?P<rows>(?:\s*,\s*\[\s*'\d{4}'\s*,\s*[\d,]+\s*\])+)"
)
ANNUAL_ROW_RE = re.compile(r"\[\s*'(\d{4})'\s*,\s*([\d]+)\s*\]")
PDF_HREF_RE = re.compile(r'href="([^"]+\.pdf[^"]*)"', re.IGNORECASE)


def _session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session


def parse_report_month(html: str) -> tuple[int, int] | None:
    """Return (year, month) parsed from the report heading, or None."""
    match = REPORT_MONTH_RE.search(html)
    if not match:
        return None
    return int(match.group(2)), MONTH_TO_NUM[match.group(1)]


def count_county_rows(html: str) -> int:
    """Number of county-name cells in the per-county table (159 when populated)."""
    return len(COUNTY_CELL_RE.findall(html))


def save_report_html(html: str, year: int, month: int) -> Path | None:
    """Save a report page verbatim as jail_report_{YYYY-MM}.html; skip if present."""
    path = BRONZE_DIR / f"jail_report_{year:04d}-{month:02d}.html"
    if path.exists():
        logger.info("Already archived, skipping: %s", path.name)
        return None
    path.write_text(html, encoding="utf-8")
    logger.info(
        "Saved %s (%d bytes, %d county rows)",
        path.name,
        path.stat().st_size,
        count_county_rows(html),
    )
    return path


def download_pdf_if_linked(
    session: requests.Session, html: str, year: int, month: int
) -> Path | None:
    """Download a posted PDF for the report month, if the page links one."""
    hrefs = sorted(set(PDF_HREF_RE.findall(html)))
    if not hrefs:
        logger.info("No PDF linked on the page for %04d-%02d", year, month)
        return None
    if len(hrefs) > 1:
        logger.warning("Multiple PDF links found, taking the first: %s", hrefs)
    url = urljoin(SOURCE_URL, hrefs[0])
    path = BRONZE_DIR / f"jail_report_{year:04d}-{month:02d}.pdf"
    if path.exists():
        logger.info("PDF already archived, skipping: %s", path.name)
        return None
    resp = session.get(url, timeout=60)
    resp.raise_for_status()
    path.write_bytes(resp.content)
    logger.info("Saved %s (%d bytes) from %s", path.name, path.stat().st_size, url)
    return path


def extract_annual_totals(html: str, snapshot_date: str) -> Path | None:
    """Extract the annual-totals JS chart series verbatim to a convenience CSV.

    The page has no annual-totals HTML table — the series lives only in a
    Google Charts ``arrayToDataTable`` call. The saved HTML stays canonical.
    """
    match = ANNUAL_ARRAY_RE.search(html)
    if not match:
        logger.warning("Annual-totals chart array not found in page")
        return None
    rows = ANNUAL_ROW_RE.findall(match.group("rows"))
    path = BRONZE_DIR / f"annual_totals_{snapshot_date}.csv"
    if path.exists():
        logger.info("Annual totals already captured today, skipping: %s", path.name)
        return None
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["year", "total_inmates"])
        writer.writerows(rows)
    logger.info(
        "Saved %s (%d years: %s–%s)", path.name, len(rows), rows[0][0], rows[-1][0]
    )
    return path


def fetch_current(session: requests.Session) -> tuple[str, int, int]:
    """Fetch the live page and return (html, report_year, report_month)."""
    resp = session.get(SOURCE_URL, timeout=60)
    resp.raise_for_status()
    html = resp.text
    parsed = parse_report_month(html)
    if parsed is None:
        raise RuntimeError("Could not parse report month from the live page")
    return html, parsed[0], parsed[1]


def fetch_archive_month(session: requests.Session, year: int, month: int) -> str:
    """POST the archive form for a specific past month and return the HTML."""
    resp = session.post(
        SOURCE_URL,
        # The form's year <option> values carry a trailing space — mirror it.
        data={
            "report_year": f"{year} ",
            "report_month": MONTH_NAMES[month - 1],
            "submit": "",
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.text


def backfill(session: requests.Session, current: tuple[int, int]) -> None:
    """Sweep the POST archive from ARCHIVE_START_YEAR up to the current month.

    Months already on disk are skipped without a request. Months whose page
    contains no county rows (pre-coverage all-zero pages) are logged and not
    saved.
    """
    cur_year, cur_month = current
    empty: list[str] = []
    for year in range(ARCHIVE_START_YEAR, cur_year + 1):
        for month in range(1, 13):
            if (year, month) >= (cur_year, cur_month):
                break
            path = BRONZE_DIR / f"jail_report_{year:04d}-{month:02d}.html"
            if path.exists():
                continue
            time.sleep(REQUEST_DELAY)
            html = fetch_archive_month(session, year, month)
            parsed = parse_report_month(html)
            if parsed != (year, month):
                logger.warning(
                    "Archive returned %s for requested %04d-%02d — not saving",
                    parsed,
                    year,
                    month,
                )
                continue
            if count_county_rows(html) == 0:
                empty.append(f"{year:04d}-{month:02d}")
                continue
            save_report_html(html, year, month)
    if empty:
        logger.info(
            "Skipped %d empty archive months (no county rows): %s … %s",
            len(empty),
            empty[0],
            empty[-1],
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="also sweep the site's POST archive for all past months (2007→present)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    session = _session()

    html, year, month = fetch_current(session)
    n_rows = count_county_rows(html)
    logger.info(
        "Live page report month: %04d-%02d (%d county rows)", year, month, n_rows
    )
    if n_rows == 0:
        raise RuntimeError(
            "Live page has no per-county table rows — refusing to archive"
        )

    save_report_html(html, year, month)
    download_pdf_if_linked(session, html, year, month)
    snapshot_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    extract_annual_totals(html, snapshot_date)

    if args.backfill:
        backfill(session, (year, month))


if __name__ == "__main__":
    main()
