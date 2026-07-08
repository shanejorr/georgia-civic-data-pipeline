"""Download the GA State Board of Pardons and Paroles annual reports to bronze.

Source: the Board's annual-reports listing page
(https://pap.georgia.gov/office-communications-news-publications-and-events/publications/annual-reports),
which links one PDF per fiscal year. The listing has **no stable URL
template** — links are a mix of ``/document/document/<slug>/download`` (newer)
and ``/media/<id>/download`` (some years), and the slugs are irregular (one
2023 slug literally embeds "UNPUBLISHED-DO-NOT-SHARE-this-URL"). So we scrape
the page, take every anchor whose href contains ``/download``, and map it to a
fiscal year from the link text ("Annual Report YYYY").

Bronze outputs (``data/bronze/criminal_justice/pardons_paroles/parole_decisions/``):

- ``annual_report_fy{YYYY}.pdf`` — one statewide fiscal-year annual report,
  verbatim. Coverage FY2001–FY2025 with **FY2015 missing** from the source.
- ``annual_report_fy2016_spread.pdf`` — the source lists FY2016 twice, once as
  a standard report and once as a "2-page spread" variant; both are kept, the
  spread under this distinct name.

Existing files are never overwritten — each run only fetches missing PDFs.
Pass ``--refresh`` to re-download every PDF even if present.

Usage:
    uv run python -m src.etl.criminal_justice.pardons_paroles.parole_decisions.download
    uv run python -m src.etl.criminal_justice.pardons_paroles.parole_decisions.download --refresh
"""

from __future__ import annotations

import argparse
import logging
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[5]
BRONZE_DIR = (
    REPO_ROOT
    / "data"
    / "bronze"
    / "criminal_justice"
    / "pardons_paroles"
    / "parole_decisions"
)

LISTING_URL = (
    "https://pap.georgia.gov/office-communications-news-publications-and-events"
    "/publications/annual-reports"
)
USER_AGENT = (
    "georgia-civic-data-bronze-etl/1.0 "
    "(+https://georgiacivicdata.org; shane.j.orr@gmail.com)"
)
# Politeness delay between PDF downloads (seconds).
REQUEST_DELAY = 1.0
CHUNK_SIZE = 1 << 20

# Anchor tags on the listing page: capture href + inner text.
ANCHOR_RE = re.compile(
    r'<a\b[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL
)
# Fiscal year embedded in the link text, e.g. "Annual Report 2025".
YEAR_IN_TEXT_RE = re.compile(r"Annual Report\s+(\d{4})", re.IGNORECASE)


def _session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session


def _strip_tags(html_fragment: str) -> str:
    """Collapse an anchor's inner HTML to plain whitespace-normalized text."""
    text = re.sub(r"<[^>]+>", " ", html_fragment)
    return re.sub(r"\s+", " ", text).strip()


def parse_report_links(html: str) -> list[tuple[int, bool, str]]:
    """Return ``(fiscal_year, is_spread, absolute_url)`` for each annual report.

    Every anchor whose href contains ``/download`` and whose text carries an
    "Annual Report YYYY" label is a fiscal-year report. The FY2016 "2-page
    spread" variant is flagged via ``is_spread`` so callers can name it
    distinctly and keep both.
    """
    links: list[tuple[int, bool, str]] = []
    for href, inner in ANCHOR_RE.findall(html):
        if "/download" not in href.lower():
            continue
        text = _strip_tags(inner)
        match = YEAR_IN_TEXT_RE.search(text)
        if not match:
            logger.warning(
                "Download anchor with no parseable year: %r (%s)", text, href
            )
            continue
        year = int(match.group(1))
        is_spread = "spread" in text.lower()
        url = urljoin(LISTING_URL, href)
        links.append((year, is_spread, url))
    return links


def target_name(year: int, is_spread: bool) -> str:
    """Bronze filename for a fiscal-year report."""
    suffix = "_spread" if is_spread else ""
    return f"annual_report_fy{year:04d}{suffix}.pdf"


def download_pdf(session: requests.Session, url: str, dest: Path) -> None:
    """Stream a PDF to ``dest`` atomically (``.part`` then ``replace``)."""
    tmp = dest.with_suffix(dest.suffix + ".part")
    with session.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with tmp.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    fh.write(chunk)
    tmp.replace(dest)


def fetch_listing(session: requests.Session) -> str:
    resp = session.get(LISTING_URL, timeout=60)
    resp.raise_for_status()
    return resp.text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="re-download every report even if the PDF is already on disk",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    session = _session()

    html = fetch_listing(session)
    links = parse_report_links(html)
    if not links:
        raise RuntimeError(
            f"No annual-report download links found on {LISTING_URL} — "
            "the page layout may have changed"
        )
    logger.info("Found %d annual-report links on the listing page", len(links))

    saved = 0
    skipped = 0
    for year, is_spread, url in sorted(links, reverse=True):
        dest = BRONZE_DIR / target_name(year, is_spread)
        if dest.exists() and not args.refresh:
            logger.info("Already archived, skipping: %s", dest.name)
            skipped += 1
            continue
        time.sleep(REQUEST_DELAY)
        download_pdf(session, url, dest)
        logger.info("Saved %s (%d bytes) from %s", dest.name, dest.stat().st_size, url)
        saved += 1

    logger.info(
        "Done: %d downloaded, %d skipped (%d links total)", saved, skipped, len(links)
    )


if __name__ == "__main__":
    main()
