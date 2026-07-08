"""Download ICE detention bronze data: ice.gov workbooks + Deportation Data Project.

Three feeds:

1. **ICE official detention statistics workbooks** — scraped from
   https://www.ice.gov/detain/detention-management (Akamai-fronted; needs a
   real browser User-Agent). One XLSX per fiscal year, refreshed ~biweekly,
   with layout drift across fiscal years. FY2020 onward is downloaded.
   Saved as ``ice_detention_stats_fy{YYYY}_{snapshot-date}.xlsx`` where the
   snapshot date is the date embedded in the file URL when present (ICE dates
   some workbook filenames, e.g. ``FY26_detentionStats_04092026.xlsx``),
   otherwise the UTC download date. Workbook URLs are unstable — always
   re-scraped from the page, never hardcoded.

2. **Deportation Data Project (DDP) processed ICE detention data** — scraped
   from https://deportationdata.org/data/processed/ice.html. FOIA-obtained
   record-level data hosted as GitHub raw files (Parquet chosen; DDP also
   offers XLSX/DTA/SAV). Detention-focused files only (stays, stints,
   facility daily population, plus DDP's collated detention-management
   workbook) — the arrests/detainers/removals suite is intentionally *not*
   downloaded. Codebook HTML pages are archived alongside. Individual-level
   records contain PII — keep in bronze only; aggregate to facility-month
   before gold. Files larger than ``MAX_FILE_BYTES`` (~8 GB) are skipped and
   logged instead of downloaded.

3. **Facility-to-county crosswalk source snapshots** →
   ``data/bronze/_crosswalks/facility_to_county/``:
   - ICE ``Over72HourFacilities.xlsx`` (facility name/address/city/state) from
     the same ice.gov page.
   - DDP compiled detention-facilities dataset (geocoded, with lat/lon).
   - Archived HIFLD Open "Prison Boundaries" layer (covers prisons, local
     jails, and ICE detention centers; HIFLD Open was discontinued Sept 2025)
     from the SeerAI archive on Source Cooperative. There is no separate
     archived HIFLD "Local Jails" layer — local jails are included in
     Prison Boundaries.

Bronze outputs:
- ``data/bronze/criminal_justice/ice_detention/detention_population/`` —
  ICE workbooks at top level, DDP files under ``ddp/``.
- ``data/bronze/_crosswalks/facility_to_county/`` — crosswalk source snapshots.

Existing files are never re-downloaded (size-stable names; dated snapshots).

Usage (append ``--skip-crosswalk`` to skip the crosswalk snapshots)::

    uv run python -m \
        src.etl.criminal_justice.ice_detention.detention_population.download
"""

from __future__ import annotations

import argparse
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)

BRONZE_DIR = Path("data/bronze/criminal_justice/ice_detention/detention_population")
DDP_DIR = BRONZE_DIR / "ddp"
CROSSWALK_DIR = Path("data/bronze/_crosswalks/facility_to_county")

ICE_PAGE_URL = "https://www.ice.gov/detain/detention-management"
DDP_PAGE_URL = "https://deportationdata.org/data/processed/ice.html"
# SeerAI archive of the discontinued HIFLD Open portal (public S3-compatible
# listing; the parquet part filename is content-addressed, so list it live).
HIFLD_ARCHIVE_LIST_URL = (
    "https://data.source.coop/seerai/hifld/?prefix=prison-boundaries/"
)
HIFLD_ARCHIVE_BASE = "https://data.source.coop/seerai/hifld/"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126 Safari/537.36"
)
REQUEST_DELAY = 0.5  # politeness delay between downloads (seconds)
MAX_FILE_BYTES = 8 * 1024**3  # ~8 GB — skip anything larger, document instead
EARLIEST_FISCAL_YEAR = 2020

# DDP detention-focused files to fetch (filename allowlist — the page also
# links arrests/detainers/removals/offices files we deliberately skip).
DDP_FILE_ALLOWLIST = (
    "detention-stays-latest.parquet",
    "detention-stints-latest.parquet",
    "facilities-daily-population-latest.parquet",
    "detention-management.xlsx",
)
# DDP codebook pages (archived as HTML alongside the data).
DDP_CODEBOOK_RE = re.compile(
    r'href="([^"#]*docs/ice/codebook(?:-facilities(?:-daily-population)?)?\.html)'
)
# DDP compiled facilities dataset → crosswalk area (attribute + geo flavors).
DDP_CROSSWALK_ALLOWLIST = (
    "facilities-latest.parquet",
    "facilities-latest-sf.parquet",
)


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


def _content_length(session: requests.Session, url: str) -> int | None:
    """HEAD a URL (following redirects) and return Content-Length, if any."""
    try:
        resp = session.head(url, allow_redirects=True, timeout=60)
        resp.raise_for_status()
        length = resp.headers.get("Content-Length")
        return int(length) if length is not None else None
    except requests.RequestException as exc:
        logger.warning("HEAD failed for %s: %s", url, exc)
        return None


def _download(session: requests.Session, url: str, dest: Path) -> bool:
    """Stream a URL to ``dest`` unless it already exists. Returns True on success."""
    if dest.exists() and dest.stat().st_size > 0:
        logger.info("exists, skipping: %s", dest.name)
        return True
    size = _content_length(session, url)
    if size is not None and size > MAX_FILE_BYTES:
        logger.warning("SKIPPED (too large: %.1f GB > 8 GB): %s", size / 1024**3, url)
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with session.get(url, stream=True, timeout=300) as resp:
            resp.raise_for_status()
            with tmp.open("wb") as fh:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    fh.write(chunk)
        tmp.rename(dest)
    except requests.RequestException as exc:
        logger.error("download failed for %s: %s", url, exc)
        tmp.unlink(missing_ok=True)
        return False
    logger.info("downloaded %s (%.1f MB)", dest.name, dest.stat().st_size / 1024**2)
    time.sleep(REQUEST_DELAY)
    return True


# --- feed 1: ice.gov workbooks -------------------------------------------------

ICE_WORKBOOK_RE = re.compile(
    r'href="(?P<url>[^"]*FY(?P<fy>\d{2})[-_]?detention[sS]tats'
    r"(?:[-_]?(?P<mmddyyyy>\d{8}))?\.xlsx)\"",
)


def scrape_ice_workbook_urls(
    session: requests.Session,
) -> list[tuple[int, str | None, str]]:
    """Return [(fiscal_year, embedded MMDDYYYY date or None, absolute URL)]."""
    resp = session.get(ICE_PAGE_URL, timeout=120)
    resp.raise_for_status()
    out = []
    for m in ICE_WORKBOOK_RE.finditer(resp.text):
        fy = 2000 + int(m.group("fy"))
        if fy < EARLIEST_FISCAL_YEAR:
            continue
        out.append((fy, m.group("mmddyyyy"), urljoin(ICE_PAGE_URL, m.group("url"))))
    if not out:
        raise RuntimeError(
            f"No FY detention-stats workbook links found on {ICE_PAGE_URL} — "
            "page layout may have changed."
        )
    return sorted(set(out), key=lambda t: (t[0], t[1] or "", t[2]))


def download_ice_workbooks(session: requests.Session) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for fy, mmddyyyy, url in scrape_ice_workbook_urls(session):
        if mmddyyyy:
            snap = f"{mmddyyyy[4:8]}-{mmddyyyy[0:2]}-{mmddyyyy[2:4]}"
        else:
            snap = today
        dest = BRONZE_DIR / f"ice_detention_stats_fy{fy}_{snap}.xlsx"
        # A given FY workbook without an embedded date is a rolling snapshot:
        # if we already hold *any* snapshot of that undated URL, keep it and
        # only add today's copy when re-run on a later date (intended).
        _download(session, url, dest)


# --- feed 2: Deportation Data Project ------------------------------------------

DDP_GITHUB_RE = re.compile(r'https://github\.com/deportationdata/[\w-]+/raw/[^"\s<>]+')


def scrape_ddp_links(
    session: requests.Session,
) -> tuple[dict[str, str], dict[str, str], list[str]]:
    """Scrape the DDP ICE page.

    Returns (detention_files, crosswalk_files, codebook_urls) where the dicts
    map filename -> absolute URL.
    """
    resp = session.get(DDP_PAGE_URL, timeout=120)
    resp.raise_for_status()
    html = resp.text

    detention: dict[str, str] = {}
    crosswalk: dict[str, str] = {}
    for url in sorted(set(DDP_GITHUB_RE.findall(html))):
        name = url.rsplit("/", 1)[-1]
        if name in DDP_FILE_ALLOWLIST:
            detention[name] = url
        elif name in DDP_CROSSWALK_ALLOWLIST:
            crosswalk[name] = url

    codebooks = sorted(
        {urljoin(DDP_PAGE_URL, m.group(1)) for m in DDP_CODEBOOK_RE.finditer(html)}
    )
    missing = set(DDP_FILE_ALLOWLIST) - set(detention)
    if missing:
        logger.warning("DDP page missing expected files: %s", sorted(missing))
    if not detention:
        raise RuntimeError(
            f"No DDP detention file links found on {DDP_PAGE_URL} — "
            "page layout may have changed."
        )
    return detention, crosswalk, codebooks


def download_ddp(
    session: requests.Session, detention: dict[str, str], codebooks: list[str]
) -> None:
    for name, url in detention.items():
        _download(session, url, DDP_DIR / name)
    for url in codebooks:
        name = "ddp_" + url.rsplit("/", 1)[-1]
        dest = DDP_DIR / name
        # Codebooks are living pages — refresh on every run.
        dest.unlink(missing_ok=True)
        _download(session, url, dest)


# --- feed 3: facility -> county crosswalk snapshots ------------------------------

ICE_FACILITY_LIST_RE = re.compile(r'href="([^"]*Over72HourFacilities[^"]*\.xlsx)"')


def download_crosswalk_snapshots(
    session: requests.Session, ddp_crosswalk: dict[str, str]
) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 1. ICE over-72-hour facility list (name/city/state) from ice.gov.
    resp = session.get(ICE_PAGE_URL, timeout=120)
    resp.raise_for_status()
    m = ICE_FACILITY_LIST_RE.search(resp.text)
    if m:
        url = urljoin(ICE_PAGE_URL, m.group(1))
        _download(
            session, url, CROSSWALK_DIR / f"ice_over72hour_facilities_{today}.xlsx"
        )
    else:
        logger.warning("Over72HourFacilities.xlsx link not found on %s", ICE_PAGE_URL)

    # 2. DDP compiled detention-facilities dataset (geocoded).
    for name, url in ddp_crosswalk.items():
        _download(session, url, CROSSWALK_DIR / f"ddp_{name}")

    # 3. Archived HIFLD Open "Prison Boundaries" (SeerAI archive, geoparquet).
    resp = session.get(HIFLD_ARCHIVE_LIST_URL, timeout=120)
    resp.raise_for_status()
    keys = re.findall(r"<Key>([^<]+)</Key>", resp.text)
    got_parquet = False
    for key in keys:
        if key.endswith(".zstd.parquet"):
            _download(
                session,
                HIFLD_ARCHIVE_BASE + key.removeprefix("hifld/"),
                CROSSWALK_DIR / "hifld_prison_boundaries.zstd.parquet",
            )
            got_parquet = True
        elif key.endswith("prisonbndrys/README.md"):
            _download(
                session,
                HIFLD_ARCHIVE_BASE + key.removeprefix("hifld/"),
                CROSSWALK_DIR / "hifld_prison_boundaries_README.md",
            )
    if not got_parquet:
        logger.warning(
            "HIFLD prison-boundaries parquet not found in SeerAI archive listing"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-crosswalk",
        action="store_true",
        help="skip the facility-to-county crosswalk source snapshots",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    session = _session()
    download_ice_workbooks(session)
    detention, ddp_crosswalk, codebooks = scrape_ddp_links(session)
    download_ddp(session, detention, codebooks)
    if not args.skip_crosswalk:
        download_crosswalk_snapshots(session, ddp_crosswalk)


if __name__ == "__main__":
    main()
