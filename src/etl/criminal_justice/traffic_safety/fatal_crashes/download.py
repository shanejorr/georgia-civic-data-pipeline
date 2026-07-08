"""Download NHTSA FARS national annual zip files into bronze.

FARS (Fatality Analysis Reporting System) is NHTSA's annual census of fatal
motor-vehicle traffic crashes, 1975-present. Files live on an S3-backed static
server (static.nhtsa.gov) that allows anonymous ListObjectsV2, so available
years are *discovered* by listing ``nhtsa/downloads/FARS/`` rather than
hardcoded.

For each year the script downloads the single national multi-table zip
(accident/vehicle/person/...), preferring formats in this order:

1. ``FARS{year}NationalCSV.zip`` (present for every year as of 2026)
2. ``FARS{year}NationalDBF.zip``
3. ``FARS{year}NationalSAS.zip``

Auxiliary zips (``...NationalAuxiliaryCSV.zip``) are derived convenience files
and are intentionally skipped. Zips are kept as-is (never extracted) — the
transform reads directly from the zips.

Idempotent: a file already present locally with a size matching the remote
object is skipped, so re-runs only fetch new/changed years.

Usage:
    uv run python -m src.etl.criminal_justice.traffic_safety.fatal_crashes.download
"""

from __future__ import annotations

import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_URL = "https://static.nhtsa.gov"
FARS_PREFIX = "nhtsa/downloads/FARS/"
LISTING_PAGE = "https://www.nhtsa.gov/file-downloads?p=nhtsa/downloads/FARS/"

BRONZE_DIR = (
    Path(__file__).resolve().parents[5]
    / "data"
    / "bronze"
    / "criminal_justice"
    / "traffic_safety"
    / "fatal_crashes"
)

# Preferred national-file formats, best first.
FORMAT_PREFERENCE = ("CSV", "DBF", "SAS")

USER_AGENT = "georgia-civic-data-bronze-downloader/1.0 (public-data aggregation)"
REQUEST_DELAY_SECONDS = 1.0
CHUNK_BYTES = 1 << 20  # 1 MiB


def _http_get(url: str, timeout: int = 120) -> urllib.request.addinfourl:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(request, timeout=timeout)


def _list_objects(prefix: str, delimiter: str | None = None) -> ET.Element:
    """One page of anonymous S3 ListObjectsV2 results (merged across pages)."""
    merged: ET.Element | None = None
    token: str | None = None
    while True:
        params = {"list-type": "2", "prefix": prefix}
        if delimiter:
            params["delimiter"] = delimiter
        if token:
            params["continuation-token"] = token
        url = f"{BASE_URL}/?{urllib.parse.urlencode(params)}"
        with _http_get(url, timeout=60) as response:
            page = ET.fromstring(response.read())
        if merged is None:
            merged = page
        else:
            merged.extend(page)
        truncated = page.findtext("{*}IsTruncated", default="false")
        token = page.findtext("{*}NextContinuationToken")
        if truncated != "true" or not token:
            return merged


def discover_years() -> list[int]:
    """Discover available FARS years from the server's directory prefixes."""
    result = _list_objects(FARS_PREFIX, delimiter="/")
    years: list[int] = []
    for node in result.iterfind(".//{*}CommonPrefixes/{*}Prefix"):
        match = re.fullmatch(rf"{re.escape(FARS_PREFIX)}(\d{{4}})/", node.text or "")
        if match:
            years.append(int(match.group(1)))
    return sorted(years)


def national_files(year: int) -> dict[str, int]:
    """Map of key -> size (bytes) for a year's National folder."""
    result = _list_objects(f"{FARS_PREFIX}{year}/National/")
    files: dict[str, int] = {}
    for contents in result.iterfind(".//{*}Contents"):
        key = contents.findtext("{*}Key")
        size = contents.findtext("{*}Size")
        if key and size is not None:
            files[key] = int(size)
    return files


def pick_national_zip(year: int, files: dict[str, int]) -> tuple[str, int, str] | None:
    """Pick the preferred national zip: (key, size, format_label) or None."""
    for fmt in FORMAT_PREFERENCE:
        key = f"{FARS_PREFIX}{year}/National/FARS{year}National{fmt}.zip"
        if key in files:
            return key, files[key], fmt
    # Last resort: any non-Auxiliary zip in the National folder.
    for key, size in sorted(files.items()):
        name = key.rsplit("/", 1)[-1]
        if name.lower().endswith(".zip") and "auxiliary" not in name.lower():
            return key, size, "OTHER"
    return None


def download_file(key: str, expected_size: int, destination: Path) -> str:
    """Download one object to destination. Returns 'skipped' or 'downloaded'."""
    if destination.exists() and destination.stat().st_size == expected_size:
        return "skipped"
    url = f"{BASE_URL}/{urllib.parse.quote(key)}"
    partial = destination.with_suffix(destination.suffix + ".part")
    with _http_get(url) as response, open(partial, "wb") as out:
        while chunk := response.read(CHUNK_BYTES):
            out.write(chunk)
    actual_size = partial.stat().st_size
    if actual_size != expected_size:
        partial.unlink(missing_ok=True)
        raise IOError(
            f"{destination.name}: size mismatch (got {actual_size:,}, "
            f"expected {expected_size:,})"
        )
    partial.replace(destination)
    return "downloaded"


def main() -> int:
    BRONZE_DIR.mkdir(parents=True, exist_ok=True)

    years = discover_years()
    if not years:
        print("ERROR: no FARS year directories discovered — server layout changed?")
        return 1
    print(f"Discovered {len(years)} FARS years: {years[0]}-{years[-1]}")

    failures: list[int] = []
    non_csv_years: list[tuple[int, str]] = []
    downloaded = skipped = 0

    for year in years:
        try:
            files = national_files(year)
            choice = pick_national_zip(year, files)
            if choice is None:
                print(f"{year}: NO national zip found (keys: {sorted(files)})")
                failures.append(year)
                continue
            key, size, fmt = choice
            if fmt != "CSV":
                non_csv_years.append((year, fmt))
            destination = BRONZE_DIR / key.rsplit("/", 1)[-1]
            status = download_file(key, size, destination)
            print(f"{year}: {status} {destination.name} ({size:,} bytes, {fmt})")
            if status == "downloaded":
                downloaded += 1
                time.sleep(REQUEST_DELAY_SECONDS)
            else:
                skipped += 1
        except Exception as exc:  # noqa: BLE001 — keep going, report at end
            print(f"{year}: FAILED — {exc}")
            failures.append(year)
            time.sleep(REQUEST_DELAY_SECONDS)

    print(
        f"\nDone: {downloaded} downloaded, {skipped} skipped (already present), "
        f"{len(failures)} failed."
    )
    if non_csv_years:
        print(f"Non-CSV fallback years: {non_csv_years}")
    if failures:
        print(f"FAILED years: {failures}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
