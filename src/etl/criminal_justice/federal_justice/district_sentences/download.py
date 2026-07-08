"""Download US Sentencing Commission (USSC) individual-offender datafiles into bronze.

The USSC publishes one **individual-offender annual datafile** ("Standardized
Research Data" / Public Release) per federal fiscal year — one row per federally
sentenced offender, national coverage. Each file carries a federal
**judicial-district** variable (``DISTRICT``), so Georgia's three districts
(GA-N Northern, GA-M Middle, GA-S Southern) are filterable in transform.

Files live under stable paths on ``www.ussc.gov/sites/default/files/zip/``. The
naming is not perfectly uniform, so this downloader **scrapes the datafiles
listing page** for the real per-year ``opafy{YY}nid*.zip`` links and falls back
to the confirmed URL pattern when a year is not found on the page:

- CSV:  ``opafy{YY}nid_csv.zip``  (present FY2012-FY2025)
- SAS/SPSS: ``opafy{YY}nid.zip`` (or ``opafy{YY}-nid.zip`` for FY16/FY17;
  the only format for FY2002-FY2011)

For each fiscal year FY2002-FY2025 the CSV zip is preferred; if it is absent
(404) the SAS/SPSS zip is downloaded instead. The main **Public Release
codebook** (``USSC_Public_Release_Codebook_FY99_FY25.pdf`` — documents FY99-FY25
variables including the district/circuit code lists) is also fetched.

Zips are kept as-is (**never extracted**). Files are saved under their native
names. Idempotent: a file already present with a byte size matching the remote
``Content-Length`` is skipped, so re-runs do not re-download ~600 MB. Pass
``--refresh`` to force re-download of every file.

Usage:
    uv run python -m src.etl.criminal_justice.federal_justice.district_sentences.download
    uv run python -m src.etl.criminal_justice.federal_justice.district_sentences.download --refresh
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE = "https://www.ussc.gov"
DATAFILES_PAGE = f"{BASE}/research/datafiles/commission-datafiles"

# Individual-offender ("Standardized Research Data" / Public Release) codebook,
# covering FY1999-FY2025 (variable definitions + district/circuit code lists).
CODEBOOK_URL = (
    f"{BASE}/sites/default/files/pdf/research-and-publications/datafiles/"
    "USSC_Public_Release_Codebook_FY99_FY25.pdf"
)

# Federal fiscal years to acquire (FY2002-FY2025 inclusive).
FISCAL_YEARS = range(2002, 2026)

USER_AGENT = (
    "georgia-civic-data-bronze-etl/1.0 "
    "(+https://georgiacivicdata.org; shane.j.orr@gmail.com)"
)
REQUEST_DELAY_SECONDS = 1.0
CHUNK_BYTES = 1 << 20  # 1 MiB
TIMEOUT = 300
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 3.0

REPO_ROOT = Path(__file__).resolve().parents[5]
BRONZE_DIR = (
    REPO_ROOT
    / "data"
    / "bronze"
    / "criminal_justice"
    / "federal_justice"
    / "district_sentences"
)

# Matches an individual-offender datafile basename and classifies its format.
# Group 1 = 2-digit fiscal year; group 2 present iff the CSV variant.
_OPAFY_RE = re.compile(r"opafy(\d{2})-?nid(_csv)?\.zip$", re.IGNORECASE)


def _fiscal_year(two_digit: int) -> int:
    """Expand a 2-digit fiscal year (standard windowing: >=50 -> 19xx)."""
    return 1900 + two_digit if two_digit >= 50 else 2000 + two_digit


def discover_links(session: requests.Session) -> dict[int, dict[str, str]]:
    """Scrape the datafiles page -> {fiscal_year: {"csv": url, "sas": url}}."""
    resp = session.get(DATAFILES_PAGE, timeout=120)
    resp.raise_for_status()
    found: dict[int, dict[str, str]] = {}
    for match in re.finditer(
        r'href="([^"]*opafy[^"]*\.zip)"', resp.text, re.IGNORECASE
    ):
        href = match.group(1)
        name = href.rsplit("/", 1)[-1]
        fmt_match = _OPAFY_RE.search(name)
        if not fmt_match:
            continue
        year = _fiscal_year(int(fmt_match.group(1)))
        fmt = "csv" if fmt_match.group(2) else "sas"
        found.setdefault(year, {})[fmt] = urljoin(BASE, href)
    return found


def _pattern_fallback(year: int) -> dict[str, str]:
    """Confirmed URL pattern used when a year is missing from the scrape."""
    yy = f"{year % 100:02d}"
    return {
        "csv": f"{BASE}/sites/default/files/zip/opafy{yy}nid_csv.zip",
        "sas": f"{BASE}/sites/default/files/zip/opafy{yy}nid.zip",
    }


def _remote_size(session: requests.Session, url: str) -> int:
    """HEAD a URL for its Content-Length, retrying transient (5xx) errors.

    Returns the size in bytes, ``-1`` if the object is absent (404), or ``0``
    if present but of unknown length (no/blank Content-Length header). Raises
    ``requests.RequestException`` only after exhausting retries on a persistent
    non-404 failure — the caller treats that as "try the next candidate".
    """
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.head(url, timeout=60, allow_redirects=True)
            if resp.status_code == 404:
                return -1  # definitively absent
            if resp.status_code >= 500:
                raise requests.HTTPError(f"{resp.status_code} for {url}")
            resp.raise_for_status()
            length = resp.headers.get("Content-Length", "")
            return int(length) if length.isdigit() else 0
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                "HEAD %s failed (attempt %d/%d): %s", url, attempt, MAX_RETRIES, exc
            )
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    raise requests.HTTPError(
        f"HEAD {url} failed after {MAX_RETRIES} attempts"
    ) from last_exc


def download_url(
    session: requests.Session, url: str, dest: Path, refresh: bool
) -> tuple[str, int] | None:
    """Download url -> dest atomically. Returns (status, size) or None if absent.

    status is 'skipped' (already present, size matches) or 'downloaded'. Returns
    None on a 404; raises on a persistent non-404 failure.
    """
    expected = _remote_size(session, url)
    if expected == -1:
        return None  # remote object does not exist; caller tries next candidate

    if dest.exists() and not refresh:
        current = dest.stat().st_size
        if expected == 0 or current == expected:
            return "skipped", current

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with session.get(url, timeout=TIMEOUT, stream=True) as resp:
                resp.raise_for_status()
                with tmp.open("wb") as fh:
                    for chunk in resp.iter_content(chunk_size=CHUNK_BYTES):
                        fh.write(chunk)
            break
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                "GET %s failed (attempt %d/%d): %s", url, attempt, MAX_RETRIES, exc
            )
            tmp.unlink(missing_ok=True)
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    else:
        raise requests.HTTPError(
            f"GET {url} failed after {MAX_RETRIES} attempts"
        ) from last_exc

    size = tmp.stat().st_size
    if size == 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded zero bytes from {url}")
    if expected not in (0,) and size != expected:
        tmp.unlink(missing_ok=True)
        raise OSError(
            f"{dest.name}: size mismatch (got {size:,}, expected {expected:,})"
        )
    tmp.replace(dest)
    return "downloaded", size


def fetch_year(
    session: requests.Session,
    year: int,
    discovered: dict[int, dict[str, str]],
    refresh: bool,
) -> tuple[str, str, str, int] | None:
    """Acquire one fiscal year: prefer CSV, fall back to SAS/SPSS.

    A candidate that is absent (404) or persistently failing falls through to
    the next candidate — the USSC edge occasionally returns 500 (not 404) for a
    non-existent CSV path, which must not abort a year that has a SAS file.
    Returns (format, filename, status, size) or None if neither format exists.
    """
    entry = discovered.get(year, {})
    fallback = _pattern_fallback(year)
    candidates = (
        ("csv", entry.get("csv", fallback["csv"])),
        ("sas", entry.get("sas", fallback["sas"])),
    )
    for fmt, url in candidates:
        dest = BRONZE_DIR / url.rsplit("/", 1)[-1]
        try:
            result = download_url(session, url, dest, refresh)
        except (requests.RequestException, OSError, RuntimeError) as exc:
            logger.warning("FY%02d %s candidate failed: %s", year % 100, fmt, exc)
            continue
        if result is not None:
            status, size = result
            if status == "downloaded":
                time.sleep(REQUEST_DELAY_SECONDS)
            return fmt, dest.name, status, size
    return None


def fetch_codebook(session: requests.Session, refresh: bool) -> None:
    """Download the Public Release codebook PDF (FY99-FY25)."""
    dest = BRONZE_DIR / CODEBOOK_URL.rsplit("/", 1)[-1]
    result = download_url(session, CODEBOOK_URL, dest, refresh)
    if result is None:
        logger.warning("Codebook not found at %s", CODEBOOK_URL)
        return
    status, size = result
    logger.info("codebook: %s %s (%.1f MB)", status, dest.name, size / 1e6)
    if status == "downloaded":
        time.sleep(REQUEST_DELAY_SECONDS)


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

    try:
        discovered = discover_links(session)
        logger.info(
            "Discovered %d fiscal years on the datafiles page: %s",
            len(discovered),
            ", ".join(f"FY{y % 100:02d}" for y in sorted(discovered)),
        )
    except requests.RequestException as exc:
        logger.warning("Datafiles page scrape failed (%s) — using URL pattern.", exc)
        discovered = {}

    downloaded = skipped = 0
    total_bytes = 0
    csv_years: list[int] = []
    sas_years: list[int] = []
    failures: list[int] = []

    for year in FISCAL_YEARS:
        try:
            result = fetch_year(session, year, discovered, args.refresh)
        except requests.RequestException as exc:
            logger.error("FY%02d FAILED — %s", year % 100, exc)
            failures.append(year)
            continue
        if result is None:
            logger.error("FY%02d: no CSV or SAS datafile found", year % 100)
            failures.append(year)
            continue
        fmt, name, status, size = result
        (csv_years if fmt == "csv" else sas_years).append(year)
        total_bytes += size
        if status == "downloaded":
            downloaded += 1
        else:
            skipped += 1
        logger.info(
            "FY%02d: %s %s (%.1f MB, %s)",
            year % 100,
            status,
            name,
            size / 1e6,
            fmt.upper(),
        )

    fetch_codebook(session, args.refresh)

    logger.info(
        "Done: %d downloaded, %d skipped, %d failed. Datafile bytes: %.1f MB.",
        downloaded,
        skipped,
        len(failures),
        total_bytes / 1e6,
    )
    logger.info(
        "CSV years: %s",
        ", ".join(f"FY{y % 100:02d}" for y in csv_years) or "none",
    )
    logger.info(
        "SAS/SPSS years: %s",
        ", ".join(f"FY{y % 100:02d}" for y in sas_years) or "none",
    )
    if failures:
        logger.error("FAILED years: %s", [f"FY{y % 100:02d}" for y in failures])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
