"""Download GA DPH OASIS mortality exports into bronze (overdose + violent deaths).

OASIS (https://oasis.state.ga.us) has **no bulk download or public API**, but its
Data Table Tool (``/dtt/``) is an ASP.NET Core app whose "Get Data" button POSTs
JSON to per-page endpoints:

- ``POST /dtt/MortalityDrugOverdoses/GetData``  (drug-overdose mortality, 1999+)
- ``POST /dtt/Mortality/GetData``               (all-cause mortality, 1994+)

Each POST requires an anti-forgery pair scraped from the tool page itself: the
``.AspNetCore.Antiforgery.*`` cookie plus the token in
``<meta id="wq-meta" data-anti="...">``, sent as the
``RequestVerificationToken`` header. Select-list values (measures, times,
geographies with county FIPS, causes, demographics) are static JSON catalogs
under ``/dtt/data/*.json`` and are re-read at run time, so new data years are
picked up automatically.

The response is ``{"rowHeaders": [[geo, dim?], ...], "values": [flat...]}``
where ``values`` is row-major: for each row, for each year ascending (plus a
"Selected Years Total" column when >1 year requested), one value per requested
measure. The UI's XLSX export is client-side (exceljs over the rendered
table), so this JSON **is** the export.

Sentinel values are kept **verbatim** in bronze (the transform interprets
them). The UI renders them as:

- ``null``  -> "0"  (no events; for rate columns "0.0")
- ``-5``    -> "*"  (rate suppressed: fewer than 5 events)
- ``-1``/``-2``/``-3``/``-6``/``-7``/``-99`` -> "N/A" variants (no population, etc.)

Outputs (CSV per cause, long by geography x year, raw JSON alongside):

- ``data/bronze/criminal_justice/dph_oasis/overdose_deaths/``
    ``{cause}__county_year.csv`` for 6 drug-overdose causes (not mutually
    exclusive!), plus ``{cause}__state_{race,sex,ethnicity,age}_year.csv``
    state-level demographic breakdowns.
- ``data/bronze/criminal_justice/dph_oasis/violent_deaths/``
    same layout for homicide, suicide, legal intervention, accidental
    shooting. (OASIS has no all-intents firearm cause — CDC WONDER is the
    canonical firearm-mortality source.)
- ``_raw_responses/*.json`` — request payload + verbatim server response.
- ``_provenance.md`` per topic (regenerated each run).

Usage:
    uv run python -m src.etl.criminal_justice.dph_oasis.download
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import logging
import re
import time
from pathlib import Path
from typing import Any

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE = "https://oasis.state.ga.us"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) georgia-civic-data-bronze/1.0"
REQUEST_DELAY_S = 1.5
TIMEOUT_S = 300

REPO_ROOT = Path(__file__).resolve().parents[4]
BRONZE_ROOT = REPO_ROOT / "data" / "bronze" / "criminal_justice" / "dph_oasis"

MEASURES = ["Deaths", "Death Rate", "Age-Adjusted Death Rate"]
# Age-stratified requests cannot use the age-adjusted rate (the UI disables
# the Age list when an Age-Adjusted measure is selected).
MEASURES_NO_AADR = ["Deaths", "Death Rate"]

TOPICS: dict[str, dict[str, Any]] = {
    "overdose_deaths": {
        "page_path": "/dtt/mortalitydrugoverdoses",
        "getdata_path": "/dtt/MortalityDrugOverdoses/GetData",
        "times_catalog": "timesDrugODMortality.json",
        "cause_source": "Drug Overdoses",
        # slug -> (CauseTypes value, CauseParentFirstItem = first item of the
        # cause category list in the UI)
        "causes": {
            "all_drug_overdoses": (
                "Drug Overdoses Without F-Codes",
                "Drug Overdoses Without F-Codes",
            ),
            "all_opioids": (
                "All Opioids Without F-Codes",
                "All Opioids Without F-Codes",
            ),
            "natural_semisynthetic_synthetic_opioids": (
                "Natural, Semi-synthetic, Synthetic Opioids Without F-Codes",
                "All Opioids Without F-Codes",
            ),
            "synthetic_opioids_excl_methadone": (
                "Synthetic Opioids other than Methadone Without F-Codes",
                "All Opioids Without F-Codes",
            ),
            "heroin": ("Heroin Without F-Codes", "All Opioids Without F-Codes"),
            "methadone": ("Methadone Without F-Codes", "All Opioids Without F-Codes"),
        },
    },
    "violent_deaths": {
        "page_path": "/dtt/mortality",
        "getdata_path": "/dtt/Mortality/GetData",
        "times_catalog": "times.json",
        "cause_source": "OASIS Detailed Causes",
        "causes": {
            "homicide": ("Assault (Homicide)", "External Causes"),
            "suicide": ("Intentional Self-Harm (Suicide)", "External Causes"),
            "legal_intervention": ("Legal Intervention", "External Causes"),
            "accidental_shooting": ("Accidental Shooting", "External Causes"),
        },
    },
}

# Demographic state-level breakdowns: dim slug -> (payload key, stratify flag,
# catalog file, catalog accessor)
DEMOGRAPHIC_DIMS: dict[str, dict[str, Any]] = {
    "race": {
        "payload_key": "Race",
        "stratify": "stratifyRace",
        "catalog": "races.json",
    },
    "sex": {
        "payload_key": "Sex",
        "stratify": "stratifySex",
        "catalog": "sexes.json",
    },
    "ethnicity": {
        "payload_key": "Ethnicity",
        "stratify": "stratifyEthnicity",
        "catalog": "ethnicities.json",
    },
    "age": {"payload_key": "Ages", "stratify": "stratifyAge", "catalog": "ages.json"},
}


# ---------------------------------------------------------------- session ----


def bootstrap_session(page_path: str) -> tuple[requests.Session, str]:
    """GET the tool page; return a session (antiforgery cookie) + header token."""
    ses = requests.Session()
    ses.headers["User-Agent"] = USER_AGENT
    resp = ses.get(f"{BASE}{page_path}", timeout=60)
    resp.raise_for_status()
    m = re.search(r'data-anti="([^"]+)"', resp.text)
    if not m:
        raise RuntimeError(f"No data-anti antiforgery token on {page_path}")
    return ses, m.group(1)


def fetch_catalog(ses: requests.Session, name: str) -> Any:
    resp = ses.get(f"{BASE}/dtt/data/{name}", timeout=60)
    resp.raise_for_status()
    return resp.json()


def get_data(
    ses: requests.Session, anti: str, getdata_path: str, payload: dict, referer: str
) -> dict:
    for attempt in range(1, 4):
        try:
            resp = ses.post(
                f"{BASE}{getdata_path}",
                json=payload,
                headers={
                    "RequestVerificationToken": anti,
                    "Referer": f"{BASE}{referer}",
                },
                timeout=TIMEOUT_S,
            )
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            if attempt == 3:
                raise
            logger.warning("GetData attempt %d failed (%s); retrying", attempt, exc)
            time.sleep(5 * attempt)
    raise AssertionError("unreachable")


# ---------------------------------------------------------------- payloads ----


def base_payload(cause_source: str, cause_value: str, cause_parent: str) -> dict:
    """All-demographics-collapsed payload skeleton (sentinel 'All ...' values)."""
    return {
        "GeoType": "Counties",
        "Geographies": [],
        "Times": [],
        "Measure": [],
        "AgeType": "Detailed Age Groups",
        "Ages": ["All Detailed Ages"],
        "Race": ["All Races"],
        "Education": ["All Educations PPOR"],
        "Ethnicity": ["All Ethnicities"],
        "Sex": ["All Sexes"],
        "CauseTypes": [cause_value],
        "CauseParentFirstItem": cause_parent,
        "CauseSource": cause_source,
        "SES": ["All Social Vulnerability Indexes"],
        "stratifyCause": True,
        "stratifyAge": False,
        "stratifyRace": False,
        "stratifySex": False,
        "stratifyEducation": False,
        "stratifyEthnicity": False,
        "stratifySES": False,
    }


# ---------------------------------------------------------------- parsing ----


def year_columns(times: list[str]) -> list[str]:
    """Server column order: years ascending, plus a totals column when >1 year."""
    cols = sorted(times, key=int)
    if len(cols) > 1:
        cols.append("selected_years_total")
    return cols


def rows_from_response(
    res: dict,
    times: list[str],
    measures: list[str],
    extra_dim: str | None,
) -> list[dict]:
    """Flatten {rowHeaders, values} into long records; sentinels verbatim."""
    ycols = year_columns(times)
    n_cols = len(ycols) * len(measures)
    headers = res.get("rowHeaders") or []
    values = res.get("values") or []
    expected = len(headers) * n_cols
    if len(values) != expected:
        raise RuntimeError(
            f"Value-count mismatch: got {len(values)}, expected {expected} "
            f"({len(headers)} rows x {len(ycols)} year-cols x {len(measures)} measures)"
        )
    out: list[dict] = []
    for i, raw_hdr in enumerate(headers):
        hdr = raw_hdr if isinstance(raw_hdr, list) else [raw_hdr]
        rec_base: dict[str, Any] = {"geography": hdr[0]}
        if extra_dim is not None:
            rec_base[extra_dim] = hdr[1] if len(hdr) > 1 else ""
        base = i * n_cols
        for yi, ycol in enumerate(ycols):
            rec = dict(rec_base)
            rec["year"] = ycol
            for mi, measure in enumerate(measures):
                slug = measure.lower().replace("-", "_").replace(" ", "_")
                rec[slug] = values[base + yi * len(measures) + mi]
            out.append(rec)
    return out


def write_csv(path: Path, records: list[dict]) -> None:
    fields = list(records[0].keys())
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for rec in records:
            writer.writerow({k: ("" if v is None else v) for k, v in rec.items()})
    logger.info("wrote %s (%d rows)", path.relative_to(REPO_ROOT), len(records))


def save_raw(raw_dir: Path, name: str, payload: dict, response: dict) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"{name}.json").write_text(
        json.dumps(
            {
                "downloaded_at_utc": dt.datetime.now(dt.UTC).isoformat(),
                "request_payload": payload,
                "response": response,
            },
            indent=1,
        )
    )


# ---------------------------------------------------------------- download ----


def county_geographies(ses: requests.Session) -> tuple[list[str], dict[str, str]]:
    """('Georgia' + 159 counties) and value -> 5-digit FIPS map.

    'Rural'/'Nonrural' aggregates are excluded (their catalog FIPS is bogus).
    """
    cat = fetch_catalog(ses, "geographies.json")
    skip = ("Georgia", "Rural", "Nonrural")
    counties = [g for g in cat["Counties"] if g["value"] not in skip]
    if len(counties) != 159:
        raise RuntimeError(f"Expected 159 GA counties, got {len(counties)}")
    fips = {g["value"]: g["fips"] for g in counties}
    fips["Georgia"] = "13"
    return ["Georgia"] + [g["value"] for g in counties], fips


def demographic_values(ses: requests.Session, dim: str) -> list[str]:
    cat = fetch_catalog(ses, DEMOGRAPHIC_DIMS[dim]["catalog"])
    if dim == "sex":
        return [x["value"] for x in cat["Sex"]]
    if dim == "age":
        return [x["value"] for x in cat["Detailed Age Groups"]]
    return [x["value"] for x in cat]


def download_topic(topic: str, cfg: dict[str, Any]) -> None:
    out_dir = BRONZE_ROOT / topic
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = out_dir / "_raw_responses"

    ses, anti = bootstrap_session(cfg["page_path"])
    times = [t["value"] for t in fetch_catalog(ses, cfg["times_catalog"])]
    geos, fips_map = county_geographies(ses)
    demo_vals = {dim: demographic_values(ses, dim) for dim in DEMOGRAPHIC_DIMS}

    logger.info(
        "[%s] years %s..%s, %d geographies", topic, min(times), max(times), len(geos)
    )

    for slug, (cause_value, cause_parent) in cfg["causes"].items():
        # --- county x year, all demographics combined -----------------------
        payload = base_payload(cfg["cause_source"], cause_value, cause_parent)
        payload["Geographies"] = geos
        payload["Times"] = times
        payload["Measure"] = MEASURES
        res = get_data(ses, anti, cfg["getdata_path"], payload, cfg["page_path"])
        name = f"{slug}__county_year"
        save_raw(raw_dir, name, payload, res)
        records = rows_from_response(res, times, MEASURES, extra_dim=None)
        for rec in records:
            rec["county_fips"] = fips_map.get(rec["geography"], "")
        # put fips right after geography
        records = [
            {
                "geography": r["geography"],
                "county_fips": r["county_fips"],
                **{k: v for k, v in r.items() if k not in ("geography", "county_fips")},
            }
            for r in records
        ]
        write_csv(out_dir / f"{name}.csv", records)
        time.sleep(REQUEST_DELAY_S)

        # --- state-level demographic breakdowns -----------------------------
        for dim, dim_cfg in DEMOGRAPHIC_DIMS.items():
            measures = MEASURES_NO_AADR if dim == "age" else MEASURES
            payload = base_payload(cfg["cause_source"], cause_value, cause_parent)
            payload["Geographies"] = ["Georgia"]
            payload["Times"] = times
            payload["Measure"] = measures
            payload[dim_cfg["payload_key"]] = demo_vals[dim]
            payload[dim_cfg["stratify"]] = True
            res = get_data(ses, anti, cfg["getdata_path"], payload, cfg["page_path"])
            name = f"{slug}__state_{dim}_year"
            save_raw(raw_dir, name, payload, res)
            records = rows_from_response(res, times, measures, extra_dim=dim)
            write_csv(out_dir / f"{name}.csv", records)
            time.sleep(REQUEST_DELAY_S)

    write_provenance(topic, cfg, out_dir, times)


# ---------------------------------------------------------------- provenance ----


def write_provenance(
    topic: str, cfg: dict[str, Any], out_dir: Path, times: list[str]
) -> None:
    now = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    causes_md = "\n".join(
        f"| `{slug}` | `{val}` | parent `{parent}` |"
        for slug, (val, parent) in cfg["causes"].items()
    )
    extra = (
        (
            "- Drug-overdose cause categories are **not mutually exclusive** "
            "(any-opioid overlaps fentanyl/heroin/methadone; all-drug-overdoses "
            "contains them all). Model as separate metrics, never as an "
            "exclusive categorical.\n"
            '- Cause values carry the "Without F-Codes" qualifier: OASIS '
            "drug-overdose definitions exclude ICD-10 mental/behavioral (F-code) "
            "underlying causes; the UI labels these simply 'All Drug Overdoses', "
            "'Heroin', etc.\n"
        )
        if topic == "overdose_deaths"
        else (
            "- OASIS has **no all-intents firearm-mortality cause**; only "
            "`Accidental Shooting` is firearm-specific. CDC WONDER (source #6) "
            "is the canonical all-intents firearm/homicide series; these files "
            "are the official Georgia vital-statistics counterpart.\n"
            "- The mortality tool serves 1994+; causes are ICD-9 based before "
            "1999 and ICD-10 from 1999 on (NCHS comparability break at "
            "1998/1999).\n"
        )
    )
    md = f"""# Provenance — GA DPH OASIS `{topic}`

- **Source**: Georgia Dept. of Public Health, OASIS Data Table Tool
  (Office of Health Indicators for Planning). Death-certificate data from the
  Georgia Office of Vital Records — official Georgia mortality statistics
  (residents, wherever the death occurred; underlying cause assigned by NCHS).
- **Tool page**: {BASE}{cfg["page_path"]}
- **Data endpoint**: `POST {BASE}{cfg["getdata_path"]}` (JSON body; requires the
  ASP.NET antiforgery cookie + `RequestVerificationToken` header scraped from
  the tool page's `<meta id="wq-meta" data-anti>` attribute).
- **Select-list catalogs**: `{BASE}/dtt/data/*.json` (times from
  `{cfg["times_catalog"]}`, geographies with county FIPS from
  `geographies.json`).
- **Downloaded**: {now} by `src/etl/criminal_justice/dph_oasis/download.py`
  (re-runnable; picks up new data years automatically).
- **Years**: {min(times)}–{max(times)} (all years the tool serves).
- **Measures per file**: Deaths, Death Rate (crude, per 100,000),
  Age-Adjusted Death Rate (per 100,000; omitted in the age-breakdown files —
  the tool disallows age stratification with age-adjusted measures).

## Files

- `{{cause}}__county_year.csv` — Georgia + 159 counties (5-digit FIPS) +
  the tool's "County Summary" row, by year, all demographics combined.
- `{{cause}}__state_{{race|sex|ethnicity|age}}_year.csv` — state-level ("Georgia")
  demographic breakdowns (county-level demographic splits are almost entirely
  suppressed, so only state grain is exported).
- `_raw_responses/*.json` — verbatim request payload + server JSON response
  for every CSV.

## Causes

| file slug | OASIS `CauseTypes` value | cause category |
|---|---|---|
{causes_md}

Cause source: `{cfg["cause_source"]}`.

## Suppression / sentinel values (kept verbatim — do NOT treat as counts)

The tool's UI renders the raw JSON values in these files as:

| raw value | UI rendering | meaning |
|---|---|---|
| empty (JSON `null`) | `0` / `0.0` | no events (true zero per OASIS) |
| `-5` | `*` | **rate suppressed** — rate based on fewer than 5 events |
| `-1`/`-2`/`-3`/`-6`/`-7`/`-99` | `N/A…` | not applicable (e.g. no population) |

Transform policy: suppressed/N-A sentinels → NULL, never 0 (see
data-cleaning-standards §4b / review-doc suppression note).

## Notes

{extra}- The `year` column includes the tool's derived `selected_years_total`
  column and the `County Summary` row verbatim; drop both in transform.
- Rows/columns mirror the tool's own XLSX export (which is generated
  client-side from the same JSON; FIPS codes come from `geographies.json`,
  exactly as the export's "include FIPS" option does).
"""
    (out_dir / "_provenance.md").write_text(md)
    logger.info("wrote %s", (out_dir / "_provenance.md").relative_to(REPO_ROOT))


def main() -> None:
    for topic, cfg in TOPICS.items():
        download_topic(topic, cfg)
    logger.info("done")


if __name__ == "__main__":
    main()
