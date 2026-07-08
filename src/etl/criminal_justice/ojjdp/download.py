"""Download OJJDP "Easy Access" juvenile-justice data for Georgia to bronze.

Covers two topics (both from NCJJ-built OJJDP Statistical Briefing Book tools;
the SBB's federal funding is at-risk, so bronze snapshots everything):

1. **EZACO** — Easy Access to State and County Juvenile Court Case Counts
   (https://ojjdp.ojp.gov/statistical-briefing-book/data-analysis-tools/ezaco/access-case-counts).
   The page is a thin JS client over a Socrata-style dataset API:
   ``https://api.ojp.gov/ojpdataset/v1/v7hy-xgyt.json`` with SoQL params
   (``$where=yr='YYYY' and state='Georgia'``). One raw JSON file per year is
   saved verbatim to ``data/bronze/criminal_justice/ojjdp/juvenile_court_cases/``.
   Each year returns ~160 rows: ``fct=0`` = the Georgia summary row, then one
   row per county (``court`` = county name, ``fct`` = 3-digit county FIPS
   suffix). Case-count fields: ``petdel``/``nonpetdel`` (delinquency),
   ``petsta``/``nonpetsta`` (status offense), ``petdep``/``nonpetdep``
   (dependency), plus populations, rates, reporting flags, and footnotes.

2. **EZAPOP** — Easy Access to Juvenile Populations
   (https://www.ojjdp.gov/ojstatbb/ezapop). Classic ASP GET form; setting
   ``export_file=yes`` on ``asp/comparison_display.asp`` returns a CSV
   attachment. County-comparison exports for Georgia (``selState=13``) are
   saved to ``data/bronze/criminal_justice/ojjdp/juvenile_population/``:
   county x year (columns = years) for total juveniles (ages 0-17), all ages,
   each sex, each race, each ethnicity, and each single year of age 0-17.
   Filter variables are checkbox params: ``v01N`` year (v011=1990 ...),
   ``v02N`` sex, ``v03N`` race, ``v04N`` ethnicity, ``v05N`` age
   (v051=age 0 ... v0518=age 17, v0519=18-20, v0520=21-24, v0521=25+).
   Every CSV embeds its own "Selecting:" filter block — kept verbatim.

Existing files are never overwritten — re-runs only add missing files
(``--refresh`` re-downloads everything). Year lists are discovered from the
live tools at run time, so re-runs pick up newly published years.

Usage:
    uv run python -m src.etl.criminal_justice.ojjdp.download
    uv run python -m src.etl.criminal_justice.ojjdp.download --refresh
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

BRONZE_ROOT = Path("data/bronze/criminal_justice/ojjdp")
EZACO_DIR = BRONZE_ROOT / "juvenile_court_cases"
EZAPOP_DIR = BRONZE_ROOT / "juvenile_population"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126 Safari/537.36"
)
REQUEST_DELAY = 0.5  # politeness delay between requests (seconds)

# ---------------------------------------------------------------- EZACO ----
EZACO_PAGE_URL = (
    "https://ojjdp.ojp.gov/statistical-briefing-book/"
    "data-analysis-tools/ezaco/access-case-counts"
)
EZACO_API_URL = "https://api.ojp.gov/ojpdataset/v1/v7hy-xgyt.json"
# Fallback year range if the page's <select id="year"> can't be parsed.
EZACO_FALLBACK_YEARS = range(1997, 2026)

# --------------------------------------------------------------- EZAPOP ----
EZAPOP_SELECTION_URL = (
    "https://www.ojjdp.gov/ojstatbb/ezapop/asp/comparison_selection.asp"
)
EZAPOP_DISPLAY_URL = "https://www.ojjdp.gov/ojstatbb/ezapop/asp/comparison_display.asp"
GEORGIA_STATE_FIPS = "13"

# Demographic filter checkboxes (variable id -> filename slug + expected
# "Selecting:" text in the exported CSV). Verified against the selection
# form's <label> text on 2026-07-02.
EZAPOP_SEX = {"v021": ("male", "Male"), "v022": ("female", "Female")}
EZAPOP_RACE = {
    "v031": ("white", "White"),
    "v032": ("black", "Black"),
    "v033": ("american_indian", "American Indian"),
    "v034": ("asian", "Asian"),
}
EZAPOP_ETHNICITY = {
    "v041": ("non_hispanic", "Non Hispanic"),
    "v042": ("hispanic", "Hispanic"),
}
JUVENILE_AGE_PARAMS = {f"v05{i}": f"v05{i}" for i in range(1, 19)}  # ages 0-17


def _session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session


# =========================================================== EZACO (API) ====


def discover_ezaco_years(session: requests.Session) -> list[int]:
    """Parse the year <select> from the EZACO page; fall back to a fixed range."""
    try:
        resp = session.get(EZACO_PAGE_URL, timeout=60)
        resp.raise_for_status()
        match = re.search(
            r'<select[^>]*id="year".*?</select>', resp.text, re.IGNORECASE | re.DOTALL
        )
        if match:
            found = re.findall(r'value="(\d{4})"', match.group(0))
            years = sorted({int(y) for y in found})
            if years:
                logger.info(
                    "EZACO years offered by the tool: %d-%d", years[0], years[-1]
                )
                return years
    except requests.RequestException as exc:  # page down != data API down
        logger.warning("Could not read the EZACO page (%s); using fallback years", exc)
    logger.warning("EZACO year <select> not found; probing fallback range")
    return list(EZACO_FALLBACK_YEARS)


def fetch_ezaco_year(session: requests.Session, year: int) -> list[dict] | None:
    """Fetch one Georgia year from the EZACO dataset API; None if no data."""
    params = {
        "$where": f"yr='{year}' and state='Georgia'",
        "$order": "fct ASC",
        "$limit": "1000",
    }
    resp = session.get(EZACO_API_URL, params=params, timeout=60)
    resp.raise_for_status()
    rows = resp.json()
    if not rows:
        return None
    if rows[0].get("fct") != "0":
        raise RuntimeError(f"EZACO {year}: first row is not the state summary (fct=0)")
    return rows


def download_ezaco(session: requests.Session, refresh: bool) -> list[Path]:
    """Save one raw JSON file per available Georgia year."""
    EZACO_DIR.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    empty_years: list[int] = []
    for year in discover_ezaco_years(session):
        path = EZACO_DIR / f"ezaco_ga_county_case_counts_{year}.json"
        if path.exists() and not refresh:
            logger.info("Already archived, skipping: %s", path.name)
            continue
        time.sleep(REQUEST_DELAY)
        rows = fetch_ezaco_year(session, year)
        if rows is None:
            empty_years.append(year)
            continue
        path.write_text(json.dumps(rows, indent=1), encoding="utf-8")
        n_counties = sum(1 for r in rows if r.get("fct") != "0")
        logger.info(
            "Saved %s (%d rows, %d county rows)", path.name, len(rows), n_counties
        )
        saved.append(path)
    if empty_years:
        logger.info("EZACO years with no Georgia data: %s", empty_years)
    return saved


# ========================================================= EZAPOP (CSV) =====


def discover_ezapop_years(session: requests.Session) -> dict[int, int]:
    """Map year -> checkbox index (v01<idx>) from the selection form labels."""
    resp = session.get(EZAPOP_SELECTION_URL, params={"selState": "1"}, timeout=60)
    resp.raise_for_status()
    pairs = re.findall(r'for="idv01(\d+)">(\d{4})<', resp.text)
    years = {int(year): int(idx) for idx, year in pairs}
    if not years:
        raise RuntimeError(
            "EZAPOP: could not parse year checkboxes from the selection form"
        )
    lo, hi = min(years), max(years)
    logger.info("EZAPOP years offered by the tool: %d-%d", lo, hi)
    return years


def fetch_ezapop_csv(
    session: requests.Session, extra_params: dict[str, str], year_params: dict[str, str]
) -> str:
    """GET a county-comparison CSV export for Georgia (columns = years)."""
    params: dict[str, str] = {
        "display_type": "counts",
        "export_file": "yes",
        "printer_friendly": "",
        "selState": GEORGIA_STATE_FIPS,
        "col_var": "v01",  # years as columns, counties as rows
        **year_params,
        **extra_params,
    }
    resp = session.get(EZAPOP_DISPLAY_URL, params=params, timeout=120)
    resp.raise_for_status()
    return resp.text


def validate_ezapop_csv(csv_text: str, expect_selecting: str | None) -> None:
    """Sanity-check an export: county rows present, expected filter applied."""
    if "County Comparisons" not in csv_text:
        raise RuntimeError("EZAPOP export missing the County Comparisons header")
    if '"All Counties"' not in csv_text or '"Appling County"' not in csv_text:
        raise RuntimeError("EZAPOP export missing county rows")
    n_counties = len(re.findall(r'^"[A-Z][^"]+ County"', csv_text, re.MULTILINE))
    if n_counties < 159:
        raise RuntimeError(
            f"EZAPOP export has only {n_counties} county rows (expected 159)"
        )
    if expect_selecting and expect_selecting not in csv_text:
        raise RuntimeError(
            "EZAPOP export 'Selecting:' block missing expected filter "
            f"{expect_selecting!r}"
        )


def download_ezapop(session: requests.Session, refresh: bool) -> list[Path]:
    """Save the suite of Georgia county x year population CSV exports."""
    EZAPOP_DIR.mkdir(parents=True, exist_ok=True)
    years = discover_ezapop_years(session)
    all_year_params = {f"v01{idx}": f"v01{idx}" for idx in years.values()}

    # (filename, demographic filter params, expected "Selecting:" text)
    jobs: list[tuple[str, dict[str, str], str | None]] = [
        # Headline denominator: total juveniles (ages 0-17) per county per year.
        (
            "ezapop_ga_county_year_juveniles_age00_17.csv",
            dict(JUVENILE_AGE_PARAMS),
            "Age = 0,",
        ),
        # Context: total resident population (all ages).
        ("ezapop_ga_county_year_all_ages.csv", {}, None),
    ]
    for var, (slug, label) in {**EZAPOP_SEX, **EZAPOP_RACE, **EZAPOP_ETHNICITY}.items():
        group = {"v02": "Sex", "v03": "Race", "v04": "Ethnicity"}[var[:3]]
        jobs.append(
            (
                f"ezapop_ga_county_year_juveniles_{group.lower()}_{slug}.csv",
                {var: var, **JUVENILE_AGE_PARAMS},
                f"{group} = {label}",
            )
        )
    for i in range(1, 19):  # single years of age 0..17 (any age band can be rebuilt)
        age = i - 1
        jobs.append(
            (
                f"ezapop_ga_county_year_age_{age:02d}.csv",
                {f"v05{i}": f"v05{i}"},
                f"Age = {age}",
            )
        )

    saved: list[Path] = []
    for filename, extra_params, expect in jobs:
        path = EZAPOP_DIR / filename
        if path.exists() and not refresh:
            logger.info("Already archived, skipping: %s", path.name)
            continue
        time.sleep(REQUEST_DELAY)
        csv_text = fetch_ezapop_csv(session, extra_params, all_year_params)
        validate_ezapop_csv(csv_text, expect)
        path.write_text(csv_text, encoding="utf-8")
        logger.info("Saved %s (%d bytes)", path.name, path.stat().st_size)
        saved.append(path)
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="re-download files that already exist in bronze",
    )
    parser.add_argument(
        "--only",
        choices=["ezaco", "ezapop"],
        help="download only one of the two tools",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    session = _session()

    if args.only in (None, "ezaco"):
        saved = download_ezaco(session, args.refresh)
        logger.info("EZACO: %d file(s) written", len(saved))
    if args.only in (None, "ezapop"):
        saved = download_ezapop(session, args.refresh)
        logger.info("EZAPOP: %d file(s) written", len(saved))


if __name__ == "__main__":
    main()
