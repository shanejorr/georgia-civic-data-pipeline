"""Download FBI Crime Data Explorer (CDE) bulk files into bronze.

The CDE site (https://cde.ucr.cjis.gov) is an SPA with **no stable file URLs**:
every bulk download is served from a private S3 bucket
(``cde-prd-data.s3.us-gov-east-1.amazonaws.com``) via short-lived signed URLs
(~15 min expiry). This downloader therefore re-discovers everything at run
time and never hardcodes an S3 URL:

1. **Additional datasets** (SRS estimates, Law Enforcement Employees, Hate
   Crime): S3 keys are read from the SPA's own metadata file
   ``LATEST/webapp/assets/JSON/downloads/downloads.json`` (entry ids ``srs``,
   ``pe``, ``hc``), so filename year-ranges (e.g. ``lee_1960_2025.csv``)
   track new releases automatically.
2. **NIBRS state-year master zips**: keys follow
   ``nibrs/incident/{YEAR}/{STATE}-{YEAR}.zip`` (pattern extracted from the
   SPA download component). Years are probed from ``NIBRS_PROBE_MIN_YEAR`` to
   the current year; a year exists iff the signed-URL endpoint returns a URL.
3. Each key is exchanged for a signed URL via
   ``GET https://cde.ucr.cjis.gov/LATEST/s3/signedurl?key={key}`` and
   downloaded immediately (before expiry).
4. **GA agency/ORI roster** (``--roster``): one call to the public CDE REST
   API ``https://api.usa.gov/crime/fbi/cde/agency/byStateAbbr/GA`` — this is
   the ``ori_to_county`` crosswalk source. Off by default because the shared
   ``DEMO_KEY`` allows only ~25-50 requests/day; set ``CDE_API_KEY`` (a free
   data.gov key) for routine refreshes.

File routing (bronze; raw files saved verbatim, zips left unextracted):

- ``nibrs_offenses/``                 <- ``GA-{YEAR}.zip`` NIBRS master zips
- ``nibrs_offenses/srs_estimates/``   <- ``estimated_crimes_1979_*.csv``
- ``hate_crimes/``                    <- ``hate_crime.zip``
- ``law_enforcement_employees/``      <- ``lee_*.csv``
- ``data/bronze/_crosswalks/ori_to_county/`` <- GA agency roster JSON

``nibrs_arrests/`` intentionally receives **no files**: its bronze is the
same NIBRS master zips (arrestee segments), shared from ``nibrs_offenses/``
— see that topic's ``_provenance.md``.

Usage:
    uv run python -m src.etl.criminal_justice.fbi_cde.download           # bulk files
    # add --roster for the agency roster too (1 CDE API call)
    uv run python -m src.etl.criminal_justice.fbi_cde.download --roster
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import sys
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CDE_BASE = "https://cde.ucr.cjis.gov"
DOWNLOADS_JSON_URL = f"{CDE_BASE}/LATEST/webapp/assets/JSON/downloads/downloads.json"
SIGNED_URL_ENDPOINT = f"{CDE_BASE}/LATEST/s3/signedurl"
API_BASE = "https://api.usa.gov/crime/fbi/cde"

STATE = "GA"
# Earliest year probed for GA NIBRS state zips. GA-2018 is the earliest that
# exists (early-adopter agencies); probing a little earlier is cheap and
# future-proofs against backfills.
NIBRS_PROBE_MIN_YEAR = 2016

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126 Safari/537.36"
)
TIMEOUT = 300

REPO_ROOT = Path(__file__).resolve().parents[4]
BRONZE_ROOT = REPO_ROOT / "data" / "bronze" / "criminal_justice" / "fbi_cde"
CROSSWALK_DIR = REPO_ROOT / "data" / "bronze" / "_crosswalks" / "ori_to_county"

# downloads.json entry id -> bronze destination directory.
ADDITIONAL_DATASET_ROUTING: dict[str, Path] = {
    "srs": BRONZE_ROOT / "nibrs_offenses" / "srs_estimates",
    "pe": BRONZE_ROOT / "law_enforcement_employees",
    "hc": BRONZE_ROOT / "hate_crimes",
}


def get_signed_url(session: requests.Session, key: str) -> str | None:
    """Exchange an S3 object key for a short-lived signed URL (None if absent)."""
    resp = session.get(SIGNED_URL_ENDPOINT, params={"key": key}, timeout=60)
    if not resp.ok:
        return None
    try:
        payload = resp.json()
    except ValueError:
        return None
    url = payload.get(key)
    return url if isinstance(url, str) and url.startswith("https://") else None


def download_file(session: requests.Session, url: str, dest: Path) -> int:
    """Stream a file to dest (atomic: temp file then rename). Returns byte count."""
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
    logger.info("Saved %s (%.1f MB)", dest.relative_to(REPO_ROOT), size / 1e6)
    return size


def download_key(session: requests.Session, key: str, dest_dir: Path) -> bool:
    """Resolve a signed URL for key and download it; False if the key is absent."""
    url = get_signed_url(session, key)
    if url is None:
        return False
    download_file(session, url, dest_dir / Path(key).name)
    return True


def download_nibrs_state_zips(session: requests.Session) -> list[int]:
    """Download every available {STATE}-{year} NIBRS master zip. Returns years found."""
    years_found: list[int] = []
    for year in range(NIBRS_PROBE_MIN_YEAR, dt.date.today().year + 1):
        key = f"nibrs/incident/{year}/{STATE}-{year}.zip"
        if download_key(session, key, BRONZE_ROOT / "nibrs_offenses"):
            years_found.append(year)
        else:
            logger.info("No NIBRS zip published for %s-%s", STATE, year)
    return years_found


def download_additional_datasets(session: requests.Session) -> None:
    """Download the SRS-estimates, LEE, and hate-crime files from downloads.json."""
    resp = session.get(DOWNLOADS_JSON_URL, timeout=60)
    resp.raise_for_status()
    entries = {e.get("id"): e for e in resp.json()}
    for entry_id, dest_dir in ADDITIONAL_DATASET_ROUTING.items():
        entry = entries.get(entry_id)
        if not entry or not entry.get("awsFile"):
            raise RuntimeError(
                f"downloads.json entry {entry_id!r} missing/changed — "
                f"re-inspect {DOWNLOADS_JSON_URL}"
            )
        key = entry["awsFile"]
        logger.info(
            "Additional dataset %s: %s (last modified %s)",
            entry_id,
            key,
            entry.get("last_modified", "?"),
        )
        if not download_key(session, key, dest_dir):
            raise RuntimeError(f"Signed URL refused for key {key!r}")


def download_agency_roster(session: requests.Session) -> None:
    """Fetch the GA agency/ORI roster (the ori_to_county crosswalk source)."""
    api_key = os.environ.get("CDE_API_KEY", "DEMO_KEY")
    url = f"{API_BASE}/agency/byStateAbbr/{STATE}"
    resp = session.get(url, params={"API_KEY": api_key}, timeout=120)
    resp.raise_for_status()
    data = resp.json()  # dict keyed by county name -> list of agency dicts
    if not isinstance(data, dict) or not data:
        raise RuntimeError(f"Unexpected roster payload from {url}")
    dest = CROSSWALK_DIR / f"cde_agency_by_state_abbr_{STATE.lower()}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".json.part")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    tmp.replace(dest)
    n_agencies = sum(len(v) for v in data.values())
    logger.info(
        "Saved %s (%d counties, %d agencies)",
        dest.relative_to(REPO_ROOT),
        len(data),
        n_agencies,
    )


def main(argv: list[str]) -> int:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    years = download_nibrs_state_zips(session)
    logger.info("NIBRS %s zips downloaded for years: %s", STATE, years)
    download_additional_datasets(session)

    if "--roster" in argv:
        download_agency_roster(session)
    else:
        logger.info("Skipping agency roster (pass --roster; uses 1 CDE API call)")

    logger.info("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
