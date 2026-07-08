"""Download raw CSVs from the Georgia Juvenile Justice Data Clearinghouse.

Scrapes the "Raw Data" links on the dashboards-reports page (the file URLs
embed the WordPress upload month, so they must never be hardcoded) and saves
the four county-level raw CSVs into three topic bronze directories:

- decision_points/        <- Raw-Data-1 and Raw-Data-2
- out_of_home_placement/  <- the OHP-STP file
- placements/             <- the Placements file

Files are saved verbatim (no cleaning at bronze) with a descriptive
snake_case name suffixed by the upload month parsed from the URL
(e.g. ``decision_points_raw_data_1_2026-06.csv``). Re-runnable: each run
re-downloads and overwrites atomically (temp file + rename).

Usage:
    uv run python -m src.etl.criminal_justice.juvenile_clearinghouse.download
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PAGE_URL = "https://juveniledata.georgiacourts.gov/dashboards-reports/"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126 Safari/537.36"
)
TIMEOUT = 120

REPO_ROOT = Path(__file__).resolve().parents[4]
BRONZE_ROOT = (
    REPO_ROOT / "data" / "bronze" / "criminal_justice" / "juvenile_clearinghouse"
)

# Map a distinctive substring of the source filename -> (topic dir, local basename).
# The upload month (from the URL path) is appended before the .csv extension.
FILE_ROUTING: list[tuple[str, str, str]] = [
    ("Raw-Data-1", "decision_points", "decision_points_raw_data_1"),
    ("Raw-Data-2", "decision_points", "decision_points_raw_data_2"),
    ("OHP-STP", "out_of_home_placement", "decision_point_raw_data_ohp_stp"),
    ("Placements-Raw-Data", "placements", "decision_point_placements_raw_data"),
]

UPLOAD_MONTH_RE = re.compile(r"/wp-content/uploads/(\d{4})/(\d{2})/")
CSV_HREF_RE = re.compile(r'href="(https?://[^"]+\.csv)"', re.IGNORECASE)


def find_csv_links(session: requests.Session) -> list[str]:
    """Fetch the dashboards-reports page and return the raw-data CSV URLs."""
    logger.info("Fetching %s", PAGE_URL)
    resp = session.get(PAGE_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    links = sorted(set(CSV_HREF_RE.findall(resp.text)))
    logger.info("Found %d CSV link(s) on page", len(links))
    return links


def route_link(url: str) -> tuple[Path, str] | None:
    """Return (topic dir, local filename) for a CSV URL, or None if unrecognized."""
    month_match = UPLOAD_MONTH_RE.search(url)
    suffix = f"_{month_match.group(1)}-{month_match.group(2)}" if month_match else ""
    for marker, topic, basename in FILE_ROUTING:
        if marker in url:
            return BRONZE_ROOT / topic, f"{basename}{suffix}.csv"
    return None


def download_file(session: requests.Session, url: str, dest: Path) -> int:
    """Stream a CSV to dest (atomic: temp file then rename). Returns byte count."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with session.get(url, timeout=TIMEOUT, stream=True) as resp:
        resp.raise_for_status()
        with tmp.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
    size = tmp.stat().st_size
    if size == 0:
        tmp.unlink()
        raise RuntimeError(f"Downloaded zero bytes from {url}")
    tmp.replace(dest)
    rel = dest.relative_to(REPO_ROOT)
    logger.info("Saved %s (%.1f MB) <- %s", rel, size / 1e6, url)
    return size


def main() -> int:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    links = find_csv_links(session)
    if not links:
        logger.error(
            "No CSV links found on %s — page layout may have changed", PAGE_URL
        )
        return 1

    routed: list[tuple[str, Path, str]] = []
    for url in links:
        route = route_link(url)
        if route is None:
            logger.warning("Skipping unrecognized CSV link: %s", url)
            continue
        routed.append((url, *route))

    expected = len(FILE_ROUTING)
    if len(routed) != expected:
        logger.error(
            "Expected %d raw-data CSVs, matched %d — check FILE_ROUTING vs links: %s",
            expected,
            len(routed),
            links,
        )
        return 1

    for url, topic_dir, filename in routed:
        download_file(session, url, topic_dir / filename)

    logger.info("Done: %d files downloaded.", len(routed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
