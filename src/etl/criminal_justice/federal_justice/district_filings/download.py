"""Download FJC Integrated Database (IDB) criminal defendant files into bronze.

The Federal Judicial Center's Integrated Database (IDB) is the authoritative
record of every federal **criminal defendant** filing/termination in the U.S.
district courts, back to statistical year 1970 and updated quarterly. Each
record carries **circuit + district** fields, so Georgia's three federal
districts (GA-N Northern = 11-3, GA-M Middle = 11-4, GA-S Southern = 11-5) are
filterable in transform.

**Retrieval note.** The IDB dataset-download links on ``/research/idb`` sit
behind a Drupal *antibot* JavaScript widget (a Views exposed filter whose form
``action`` is JS-rewritten from ``/antibot``), so the buttons yield no static
href. This downloader bypasses the widget by requesting the exposed filter as a
plain **GET query parameter** (``?field_type_tid=6876`` = "Criminal Data"),
which returns the two criminal-dataset landing pages server-side. Each landing
page is then scraped for the real file URLs under
``www.fjc.gov/sites/default/files/idb/`` — nothing is hardcoded, so filename
drift on FJC's quarterly re-uploads (the ``_0`` suffixes) is tracked
automatically.

Criminal data is partitioned into two period files, each published as a single
**tab-delimited text** zip (the canonical bulk download — self-describing and
transform-friendly; polars reads the members directly):

- SY1970-FY1995: ``textfiles/cr70to95.zip``
- FY1996-present: ``textfiles/cr96on_0.zip`` (1992 is a 15-month bridge year)

Both period **codebooks** (PDF) are fetched too. Per-year SAS datasets
(``datasets/cr{YY}.sas7bdat``) hold the same records in an alternate format and
are intentionally **not** downloaded — the tab-delimited zips are complete.

Zips are kept as-is (**never extracted**). Idempotent: a file already present
with a byte size matching the remote ``Content-Length`` is skipped. Pass
``--refresh`` to force re-download.

Usage:
    uv run python -m src.etl.criminal_justice.federal_justice.district_filings.download
    uv run python -m src.etl.criminal_justice.federal_justice.district_filings.download --refresh
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urljoin

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE = "https://www.fjc.gov"
# Criminal Data taxonomy term = 6876; passing it as a GET filter bypasses the
# antibot JS widget and returns the criminal-dataset landing pages server-side.
LISTING_URL = f"{BASE}/research/idb?field_type_tid=6876"

USER_AGENT = (
    "georgia-civic-data-bronze-etl/1.0 "
    "(+https://georgiacivicdata.org; shane.j.orr@gmail.com)"
)
REQUEST_DELAY_SECONDS = 1.0
CHUNK_BYTES = 1 << 20  # 1 MiB
TIMEOUT = 600  # cr96on_0.zip is ~250 MB
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 3.0

REPO_ROOT = Path(__file__).resolve().parents[5]
BRONZE_DIR = (
    REPO_ROOT
    / "data"
    / "bronze"
    / "criminal_justice"
    / "federal_justice"
    / "district_filings"
)

# Criminal-dataset landing pages (exclude the /interactive/ query tools).
_LANDING_RE = re.compile(r'href="(/research/idb/criminal-[^"?#]*)"', re.IGNORECASE)
# The bulk tab-delimited text zips and the period codebooks on a landing page.
_TEXTZIP_RE = re.compile(r'href="([^"]*/idb/textfiles/[^"]*\.zip)"', re.IGNORECASE)
_CODEBOOK_RE = re.compile(r'href="([^"]*/idb/codebooks/[^"]*\.pdf)"', re.IGNORECASE)


def _get_text(session: requests.Session, url: str) -> str:
    """GET a URL with retries on transient (5xx / connection) errors."""
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=TIMEOUT)
            if resp.status_code >= 500:
                raise requests.HTTPError(f"{resp.status_code} for {url}")
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                "GET %s failed (attempt %d/%d): %s", url, attempt, MAX_RETRIES, exc
            )
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    raise RuntimeError(f"GET {url} failed after {MAX_RETRIES} attempts") from last_exc


def discover_files(session: requests.Session) -> list[str]:
    """Scrape the Criminal-Data listing -> landing pages -> real file URLs."""
    listing = _get_text(session, LISTING_URL)
    landing_paths = sorted(
        {
            path
            for path in _LANDING_RE.findall(listing)
            if "/interactive/" not in path.lower()
        }
    )
    if not landing_paths:
        raise RuntimeError(
            f"No criminal-dataset landing pages found at {LISTING_URL} — "
            "the IDB page layout or the antibot bypass may have changed."
        )
    logger.info(
        "Found %d criminal landing page(s): %s", len(landing_paths), landing_paths
    )

    urls: list[str] = []
    for path in landing_paths:
        page = _get_text(session, urljoin(BASE, path))
        found = _TEXTZIP_RE.findall(page) + _CODEBOOK_RE.findall(page)
        if not found:
            logger.warning("No text-zip or codebook links on %s", path)
        for href in found:
            full = urljoin(BASE, href)
            if full not in urls:
                urls.append(full)
    return urls


# The FJC origin caps a single non-ranged connection at 8 MiB for some files
# (e.g. cr70to95.zip truncates at exactly 8 MiB), but honors HTTP Range requests
# (206). Window must stay <= that cap so each ranged response is served whole.
RANGE_WINDOW_BYTES = 8 * (1 << 20)


def _windowed_download(
    session: requests.Session, url: str, tmp: Path, total: int
) -> int:
    """Fetch [0, total) via sequential HTTP Range windows. Returns bytes written.

    Fallback for files the origin truncates on a single connection but serves
    correctly in ranges. Each window is retried independently; a partial/failed
    window is discarded (seek+truncate) before retrying so bytes never double.
    """
    with tmp.open("wb") as fh:
        pos = 0
        while pos < total:
            end = min(pos + RANGE_WINDOW_BYTES, total) - 1
            last_exc: Exception | None = None
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    fh.seek(pos)
                    fh.truncate()
                    got = 0
                    with session.get(
                        url,
                        headers={"Range": f"bytes={pos}-{end}"},
                        timeout=TIMEOUT,
                        stream=True,
                    ) as resp:
                        if resp.status_code != 206:
                            raise requests.HTTPError(
                                f"expected 206 for Range request, got {resp.status_code}"
                            )
                        for chunk in resp.iter_content(chunk_size=CHUNK_BYTES):
                            fh.write(chunk)
                            got += len(chunk)
                    if got == 0:
                        raise RuntimeError(f"empty Range window at byte {pos}")
                    pos += got
                    break
                except (requests.RequestException, RuntimeError) as exc:
                    last_exc = exc
                    logger.warning(
                        "Range window %d-%d failed (attempt %d/%d): %s",
                        pos,
                        end,
                        attempt,
                        MAX_RETRIES,
                        exc,
                    )
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)
            else:
                raise RuntimeError(
                    f"Range window at byte {pos} failed after {MAX_RETRIES} attempts"
                ) from last_exc
    return tmp.stat().st_size


def download_file(
    session: requests.Session, url: str, refresh: bool
) -> tuple[str, int]:
    """Download url -> BRONZE_DIR atomically. Returns (status, size).

    Fast path is a single streaming GET; if the origin under-reads (truncates)
    and advertises byte ranges, it falls back to a windowed Range download.
    """
    dest = BRONZE_DIR / unquote(url.rsplit("/", 1)[-1])

    expected: int | None = None
    head = session.head(url, timeout=120, allow_redirects=True)
    head.raise_for_status()
    length = head.headers.get("Content-Length", "")
    if length.isdigit():
        expected = int(length)
    accept_ranges = "bytes" in head.headers.get("Accept-Ranges", "").lower()

    if dest.exists() and not refresh:
        current = dest.stat().st_size
        if expected is None or current == expected:
            return "skipped", current

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    can_range = accept_ranges and expected is not None
    last_exc: Exception | None = None
    size = 0
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with session.get(url, timeout=TIMEOUT, stream=True) as resp:
                resp.raise_for_status()
                with tmp.open("wb") as fh:
                    for chunk in resp.iter_content(chunk_size=CHUNK_BYTES):
                        fh.write(chunk)
            size = tmp.stat().st_size
            if expected is not None and size != expected and can_range:
                logger.warning(
                    "%s under-read (%d/%d bytes) — retrying via Range windows",
                    dest.name,
                    size,
                    expected,
                )
                size = _windowed_download(session, url, tmp, expected)
            break
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                "Download %s failed (attempt %d/%d): %s",
                dest.name,
                attempt,
                MAX_RETRIES,
                exc,
            )
            if can_range:
                try:
                    size = _windowed_download(session, url, tmp, expected)
                    last_exc = None
                    break
                except (requests.RequestException, RuntimeError) as range_exc:
                    last_exc = range_exc
                    logger.warning("Range fallback also failed: %s", range_exc)
            tmp.unlink(missing_ok=True)
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    else:
        raise RuntimeError(
            f"Download {url} failed after {MAX_RETRIES} attempts"
        ) from last_exc

    if size == 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded zero bytes from {url}")
    if expected is not None and size != expected:
        tmp.unlink(missing_ok=True)
        raise OSError(
            f"{dest.name}: size mismatch (got {size:,}, expected {expected:,})"
        )
    tmp.replace(dest)
    return "downloaded", size


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force re-download of every file (ignore skip-if-present).",
    )
    args = parser.parse_args(argv)

    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    urls = discover_files(session)
    logger.info("Discovered %d file(s) to acquire:\n  %s", len(urls), "\n  ".join(urls))

    downloaded = skipped = 0
    total_bytes = 0
    failures: list[str] = []
    for url in urls:
        try:
            status, size = download_file(session, url, args.refresh)
        except (requests.RequestException, OSError, RuntimeError) as exc:
            logger.error("FAILED %s — %s", url, exc)
            failures.append(url)
            continue
        total_bytes += size
        if status == "downloaded":
            downloaded += 1
            time.sleep(REQUEST_DELAY_SECONDS)
        else:
            skipped += 1
        logger.info(
            "%s %s (%.1f MB)", status, unquote(url.rsplit("/", 1)[-1]), size / 1e6
        )

    logger.info(
        "Done: %d downloaded, %d skipped, %d failed. Total bytes: %.1f MB.",
        downloaded,
        skipped,
        len(failures),
        total_bytes / 1e6,
    )
    if failures:
        logger.error("FAILED: %s", failures)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
