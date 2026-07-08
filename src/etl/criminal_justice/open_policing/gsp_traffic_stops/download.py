"""Download the Stanford Open Policing Project Georgia file into bronze.

The Stanford Open Policing Project (SOPP) publishes standardized traffic-stop
microdata by state. For Georgia the only reporting agency is the **Georgia
State Patrol** (GSP): ~1.9M stop-level records, 2012-01-01 -> 2016-12-31. The
project is frozen — there is a single, stable bulk file hosted on Stanford's
digital repository (stacks.stanford.edu), so no page scraping is needed.

The file is a zip containing one CSV of stop-level microdata (driver
demographics = PII). It is kept as-is — **never extracted**; any transform must
read the CSV member directly from the zip and aggregate to county/year/race
before anything reaches gold.

Idempotent: if the destination already exists with a size matching the remote
``Content-Length`` it is skipped, so re-runs do not re-fetch the ~85 MiB file.
Pass ``--refresh`` to force a re-download.

Usage:
    uv run python -m src.etl.criminal_justice.open_policing.gsp_traffic_stops.download
    uv run python -m src.etl.criminal_justice.open_policing.gsp_traffic_stops.download --refresh
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Stable direct download on Stanford's digital repository (druid yg821jf8611).
DOWNLOAD_URL = (
    "https://stacks.stanford.edu/file/druid:yg821jf8611/"
    "yg821jf8611_ga_statewide_2020_04_01.csv.zip"
)
FILENAME = "yg821jf8611_ga_statewide_2020_04_01.csv.zip"

# Verified 2026-07-04: server Content-Length for the file above.
EXPECTED_SIZE_BYTES = 88_842_478

BRONZE_DIR = (
    Path(__file__).resolve().parents[5]
    / "data"
    / "bronze"
    / "criminal_justice"
    / "open_policing"
    / "gsp_traffic_stops"
)

USER_AGENT = (
    "georgia-civic-data-bronze-etl/1.0 "
    "(+https://georgiacivicdata.org; shane.j.orr@gmail.com)"
)
REQUEST_DELAY_SECONDS = 1.0
CHUNK_BYTES = 1 << 20  # 1 MiB


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def _remote_size(session: requests.Session, url: str) -> int | None:
    """Return the server-reported Content-Length, or None if unavailable."""
    response = session.head(url, timeout=60, allow_redirects=True)
    response.raise_for_status()
    length = response.headers.get("Content-Length")
    return int(length) if length is not None else None


def download_file(
    session: requests.Session,
    url: str,
    destination: Path,
    *,
    refresh: bool = False,
) -> str:
    """Download ``url`` to ``destination``. Returns 'skipped' or 'downloaded'."""
    expected = _remote_size(session, url)
    if expected is None:
        expected = EXPECTED_SIZE_BYTES
        logger.warning(
            "server did not report Content-Length; falling back to expected %s bytes",
            f"{expected:,}",
        )
    elif expected != EXPECTED_SIZE_BYTES:
        logger.warning(
            "remote size %s bytes differs from the recorded expected %s bytes "
            "(source may have been republished)",
            f"{expected:,}",
            f"{EXPECTED_SIZE_BYTES:,}",
        )

    if not refresh and destination.exists() and destination.stat().st_size == expected:
        logger.info(
            "%s: skipped (already present, %s bytes)",
            destination.name,
            f"{expected:,}",
        )
        return "skipped"

    partial = destination.with_suffix(destination.suffix + ".part")
    logger.info("%s: downloading %s bytes ...", destination.name, f"{expected:,}")
    with session.get(url, stream=True, timeout=300) as response:
        response.raise_for_status()
        with open(partial, "wb") as out:
            for chunk in response.iter_content(chunk_size=CHUNK_BYTES):
                if chunk:
                    out.write(chunk)

    actual = partial.stat().st_size
    if actual != expected:
        partial.unlink(missing_ok=True)
        raise OSError(
            f"{destination.name}: size mismatch (got {actual:,}, expected {expected:,})"
        )
    partial.replace(destination)
    logger.info("%s: downloaded (%s bytes)", destination.name, f"{actual:,}")
    return "downloaded"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force re-download even if a size-matching file already exists.",
    )
    args = parser.parse_args()

    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    destination = BRONZE_DIR / FILENAME

    session = _session()
    try:
        status = download_file(session, DOWNLOAD_URL, destination, refresh=args.refresh)
    except Exception as exc:  # noqa: BLE001 — report and fail cleanly
        logger.error("download failed: %s", exc)
        return 1

    if status == "downloaded":
        time.sleep(REQUEST_DELAY_SECONDS)

    logger.info("Done: %s -> %s", status, destination)
    return 0


if __name__ == "__main__":
    sys.exit(main())
