"""Download the GA Dept. of Corrections (GDC) statistical-trend PDFs to bronze.

Source: the GDC **Statistical Trends** standing-reports page
<https://gdc.georgia.gov/organization/about-gdc/agency-activity/research-and-reports/standing-reports/statistical-trends>,
which links a small suite of trend PDFs via ``/media/{id}/download`` anchors.
Those media-ID URLs **301-redirect to stable per-report slug URLs** and the
media IDs themselves change whenever GDC re-uploads a report, so this module
never hardcodes media IDs: it **scrapes the page**, maps each anchor to a
report by its (normalized) link text, downloads it following the redirect, and
logs the resolved slug URL for provenance. The expected stable slug is kept per
report as a verification target and a fallback if the page markup changes.

Five PDFs are pulled into three topic bronze dirs
(``data/bronze/criminal_justice/gdc/{topic}/``):

- ``inmate_releases_county``
  - ``inmate_release_by_county_cy.pdf`` — Inmate Release by County, Calendar Year
  - ``inmate_release_by_county_fy.pdf`` — Inmate Release by County, Fiscal Year
- ``recidivism_reconviction``
  - ``reconviction_3yr_cy.pdf`` — 3-Year Reconviction, Calendar Years
  - ``reconviction_3yr_fy.pdf`` — 3-Year Reconviction, Fiscal Years
- ``inmate_population``
  - ``year_end_population_since_1925.pdf`` — Year-End Population since 1925

PDFs are stored verbatim. Existing non-empty files are skipped unless
``--refresh`` is passed. There is no R2/upload step here — this is bronze
acquisition only.

Usage:
    uv run python -m src.etl.criminal_justice.gdc.download
    uv run python -m src.etl.criminal_justice.gdc.download --refresh
"""

from __future__ import annotations

import argparse
import logging
import re
import time
from html.parser import HTMLParser
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

USER_AGENT = "georgia-civic-data-bronze-etl/1.0 (+https://georgiacivicdata.org; shane.j.orr@gmail.com)"
REQUEST_DELAY = 0.75  # polite gap between requests (seconds)
TIMEOUT_S = 120
CHUNK = 1 << 20  # 1 MiB streaming chunks

TRENDS_URL = (
    "https://gdc.georgia.gov/organization/about-gdc/agency-activity/"
    "research-and-reports/standing-reports/statistical-trends"
)

REPO_ROOT = Path(__file__).resolve().parents[4]
BRONZE_BASE = REPO_ROOT / "data" / "bronze" / "criminal_justice" / "gdc"

# Each report: which topic bronze dir it lands in, its verbatim filename, a
# case-insensitive regex matched against the (whitespace-normalized) link text
# on the Statistical Trends page, and the stable slug URL we expect the anchor's
# /media/{id}/download to redirect to (verification + fallback; NOT hardcoded as
# the primary source — the scraped anchor is preferred).
REPORTS = [
    {
        "topic": "inmate_releases_county",
        "filename": "inmate_release_by_county_cy.pdf",
        "text_re": re.compile(r"inmate release by county.*calendar", re.IGNORECASE),
        "expected_slug": "https://gdc.georgia.gov/document/statistical-trend-reports/inmate-release-county-calendar-year/download",
    },
    {
        "topic": "inmate_releases_county",
        "filename": "inmate_release_by_county_fy.pdf",
        "text_re": re.compile(r"inmate release by county.*fiscal", re.IGNORECASE),
        "expected_slug": "https://gdc.georgia.gov/document/statistical-trend-reports/inmate-release-county-fiscal-year/download",
    },
    {
        "topic": "recidivism_reconviction",
        "filename": "reconviction_3yr_cy.pdf",
        "text_re": re.compile(r"3[-\s]?year reconviction.*calendar", re.IGNORECASE),
        "expected_slug": "https://gdc.georgia.gov/document/statistical-trend-reports/3-year-reconviction-calendar-years/download",
    },
    {
        "topic": "recidivism_reconviction",
        "filename": "reconviction_3yr_fy.pdf",
        "text_re": re.compile(r"3[-\s]?year reconviction.*fiscal", re.IGNORECASE),
        "expected_slug": "https://gdc.georgia.gov/document/statistical-trend-reports/3-year-reconviction-fiscal-years/download",
    },
    {
        "topic": "inmate_population",
        "filename": "year_end_population_since_1925.pdf",
        "text_re": re.compile(r"year[-\s]?end\s+pop.*1925", re.IGNORECASE),
        "expected_slug": "https://gdc.georgia.gov/document/statistical-trend-reports/year-end-pop-1925/download",
    },
]


class _AnchorParser(HTMLParser):
    """Collect every ``(href, normalized_text)`` pair on the page."""

    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[tuple[str, str]] = []
        self._href: str | None = None
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            d = {k: (v or "") for k, v in attrs}
            self._href = d.get("href")
            self._buf = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            text = re.sub(r"\s+", " ", "".join(self._buf).replace("\xa0", " ")).strip()
            self.anchors.append((self._href, text))
            self._href = None
            self._buf = []


def _session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session


def scrape_anchors(session: requests.Session) -> list[tuple[str, str]]:
    """GET the Statistical Trends page and return all (href, text) anchors."""
    logger.info("Fetching Statistical Trends page: %s", TRENDS_URL)
    resp = session.get(TRENDS_URL, timeout=TIMEOUT_S)
    resp.raise_for_status()
    parser = _AnchorParser()
    parser.feed(resp.text)
    logger.info("Scraped %d anchors", len(parser.anchors))
    return parser.anchors


def resolve_report_url(
    report: dict, anchors: list[tuple[str, str]]
) -> tuple[str, bool]:
    """Return (url, from_page) for a report by matching link text on the page.

    Prefers the scraped anchor whose normalized text matches the report's
    ``text_re``. Falls back to the report's expected stable slug URL (with a
    warning) if no anchor matches — so a markup change degrades gracefully
    instead of failing the whole run.
    """
    matches = [href for href, text in anchors if report["text_re"].search(text)]
    if matches:
        if len(matches) > 1:
            logger.warning(
                "%s: %d anchors matched, using the first: %s",
                report["filename"],
                len(matches),
                matches,
            )
        return matches[0], True
    logger.warning(
        "%s: no anchor matched on the page; falling back to expected slug %s",
        report["filename"],
        report["expected_slug"],
    )
    return report["expected_slug"], False


def download_pdf(
    session: requests.Session, url: str, dest: Path, refresh: bool
) -> dict:
    """Stream a PDF to ``dest`` atomically; skip if present unless ``refresh``.

    Returns a result dict with the resolved (post-redirect) slug URL, byte size,
    and whether it was skipped.
    """
    if dest.exists() and dest.stat().st_size > 0 and not refresh:
        logger.info(
            "Already downloaded, skipping: %s (%d bytes)",
            dest.name,
            dest.stat().st_size,
        )
        return {
            "file": dest.name,
            "bytes": dest.stat().st_size,
            "resolved_url": None,
            "skipped": True,
        }

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    logger.info("Downloading %s -> %s", url, dest.name)
    with session.get(url, timeout=TIMEOUT_S, stream=True) as resp:
        resp.raise_for_status()
        ctype = resp.headers.get("Content-Type", "")
        if "pdf" not in ctype.lower():
            raise RuntimeError(
                f"{dest.name}: expected a PDF but server returned Content-Type {ctype!r} "
                f"from {resp.url}"
            )
        resolved_url = resp.url  # final URL after redirects (the stable slug)
        with tmp.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=CHUNK):
                if chunk:
                    fh.write(chunk)
    tmp.replace(dest)
    size = dest.stat().st_size
    logger.info("Saved %s (%d bytes) from %s", dest.name, size, resolved_url)
    return {
        "file": dest.name,
        "bytes": size,
        "resolved_url": resolved_url,
        "skipped": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="re-download even if the target PDF already exists on disk",
    )
    args = parser.parse_args()

    session = _session()
    anchors = scrape_anchors(session)
    time.sleep(REQUEST_DELAY)

    results: list[dict] = []
    for report in REPORTS:
        url, from_page = resolve_report_url(report, anchors)
        dest = BRONZE_BASE / report["topic"] / report["filename"]
        result = download_pdf(session, url, dest, args.refresh)
        result["topic"] = report["topic"]
        result["from_page"] = from_page
        result["expected_slug"] = report["expected_slug"]
        results.append(result)
        if not result["skipped"]:
            time.sleep(REQUEST_DELAY)

    downloaded = sum(1 for r in results if not r["skipped"])
    skipped = sum(1 for r in results if r["skipped"])
    logger.info(
        "Done: %d downloaded, %d skipped, into %s",
        downloaded,
        skipped,
        BRONZE_BASE,
    )
    for r in results:
        if r["resolved_url"] and r["resolved_url"] != r["expected_slug"]:
            logger.warning(
                "%s: resolved URL %s differs from expected slug %s",
                r["file"],
                r["resolved_url"],
                r["expected_slug"],
            )


if __name__ == "__main__":
    main()
