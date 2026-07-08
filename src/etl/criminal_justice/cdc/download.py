"""Download CDC WONDER Multiple Cause of Death exports (GA firearm/homicide/legal-intervention).

CDC WONDER's official XML-POST API **cannot return county-level data** (sub-national
grouping variables are API-blocked). But the interactive web app at
https://wonder.cdc.gov/mcd.html is an ordinary HTML form-POST workflow that **is**
scriptable, and it *will* return county grain. This module drives it end to end.

The mechanics (verified 2026-07):

1. GET the dataset entry page (e.g. ``mcd-icd10.html``) to open a session.
2. POST the **data-use-agreement** acceptance to ``/controller/datarequest/{DID}``
   with ``stage=about`` + ``action-I Agree=I Agree``. The response is the Request
   Form and carries a URL-rewritten ``;jsessionid=...`` in its ``<form action>`` —
   the session is tracked by that path token, **not** a cookie, so every
   subsequent POST must target ``/controller/datarequest/{DID};jsessionid=...``.
3. Parse **every** field of the Request Form (inputs, selects, *and* textareas —
   the ICD-code finders are ``<textarea>`` and must be submitted, even if empty,
   or WONDER raises a spurious "AND combination" error). Keep all defaults, then
   override only:
     - ``B_1`` = County group-by, ``B_2`` = Year group-by, ``B_3..B_5`` = ``*None*``
     - ``F_D{n}.V9`` = ``13`` (Georgia; the location finder uses state FIPS)
     - ``O_ucd`` = the Injury-Intent cause mode, plus the intent (``V_*.V22``) and
       mechanism (``V_*.V23``) selections per measure group
     - ``O_show_suppressed`` / ``O_show_zeros`` / ``O_show_totals`` = ``true`` so
       suppressed and zero rows are emitted with their markers **verbatim**
     - ``O_aar`` = ``aar_std`` + ``O_aar_pop`` = ``2000`` + ``O_aar_enable`` =
       ``true`` → adds the age-adjusted rate column (2000 US std population)
     - ``O_export-format`` = ``tsv`` and ``O_change_action-Send-Export Results`` =
       ``Export Results`` → tab-delimited export instead of the HTML results page
4. POST with ``action-Send=Send``. The response body is the tab-delimited export
   (header row, data rows, then a ``---`` block of "Dataset"/"Query Parameters"/
   "Caveats"/"Notes"). Suppression markers ("Suppressed", counts <10) and
   unreliable-rate markers ("Unreliable", rates from <20 deaths) are preserved.

Two vintages are pulled, because NCHS split the race coding scheme:
  - **D77**  Multiple Cause of Death, 1999-2020 (**bridged-race** populations)
  - **D157** Multiple Cause of Death, 2018-2024, **Single Race**

Four cause "measure groups" per vintage (county x year):
  - ``firearm_deaths``      all intents, Firearm mechanism
  - ``homicide``            Homicide intent, all mechanisms
  - ``firearm_homicide``    Homicide intent + Firearm mechanism
  - ``legal_intervention``  Legal Intervention / Operations of War intent

Outputs (verbatim TSV, one per vintage x measure group):
  data/bronze/criminal_justice/cdc/firearm_homicide_deaths/
    {measure}_by_county_year_{ystart}_{yend}.txt
    _provenance.md

Field/variable numbers and cause codes are resolved **by label** from each
dataset's own form, so a new WONDER data vintage (or renumbered variables) is
handled without editing this file.

Usage:
    uv run python -m src.etl.criminal_justice.cdc.download
    uv run python -m src.etl.criminal_justice.cdc.download --dataset D77   # one vintage
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import re
import time
from html.parser import HTMLParser
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE = "https://wonder.cdc.gov"
# Honest, identifiable User-Agent (per WONDER etiquette + repo global instructions).
USER_AGENT = "georgia-civic-data-bronze-etl/1.0 (+https://georgiacivicdata.org; shane.j.orr@gmail.com)"
REQUEST_DELAY_S = 4.0  # polite gap between sequential requests to wonder.cdc.gov
TIMEOUT_S = 600
GEORGIA_STATE_FIPS = "13"

REPO_ROOT = Path(__file__).resolve().parents[4]
BRONZE_DIR = (
    REPO_ROOT
    / "data"
    / "bronze"
    / "criminal_justice"
    / "cdc"
    / "firearm_homicide_deaths"
)

# Each vintage: WONDER dataset id + the HTML entry page that opens its session.
DATASETS = [
    {
        "id": "D77",
        "entry": "mcd-icd10.html",
        "label": "Multiple Cause of Death, 1999-2020 (bridged race)",
    },
    {
        "id": "D157",
        "entry": "mcd-icd10-expanded.html",
        "label": "Multiple Cause of Death, 2018-2024, Single Race",
    },
]

# Cause filters, resolved to codes by label at run time.
#   intent  -> a V_*.V22 (UCD - Injury Intent) option label, or "*All*"
#   mech    -> a V_*.V23 (UCD - Injury Mechanism) option label, or "*All*"
MEASURE_GROUPS = {
    "firearm_deaths": {"intent": "*All*", "mech": "Firearm"},
    "homicide": {"intent": "Homicide", "mech": "*All*"},
    "firearm_homicide": {"intent": "Homicide", "mech": "Firearm"},
    "legal_intervention": {"intent": "Legal Intervention", "mech": "*All*"},
}


class _FormParser(HTMLParser):
    """Collect every submittable field of a WONDER request form.

    Emits ``(name, value)`` pairs exactly as a browser would submit them:
    text/hidden inputs (current value), checked checkboxes/radios only, each
    <select>'s selected option (or first option if none marked selected), and
    every <textarea> (with its current text, usually empty). Also captures each
    <select>'s full ``(value, label)`` option list for label-based resolution.
    """

    def __init__(self) -> None:
        super().__init__()
        self.fields: list[tuple[str, str]] = []
        self.selects: dict[str, list[tuple[str, str]]] = {}
        self._sel_name: str | None = None
        self._sel_first: str | None = None
        self._sel_opts: list[tuple[str, bool]] = []
        self._sel_optlabels: list[tuple[str, str]] = []
        self._in_opt = False
        self._opt_val = ""
        self._opt_sel = False
        self._opt_text = ""
        self._ta_name: str | None = None
        self._ta_buf = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = {k: (v or "") for k, v in attrs}
        has = {k for k, _ in attrs}
        if tag == "input":
            name = d.get("name")
            typ = d.get("type", "text").lower()
            if not name or typ in ("submit", "button", "image", "reset"):
                return
            if typ in ("checkbox", "radio"):
                if "checked" in has:
                    self.fields.append((name, d.get("value", "")))
            else:
                self.fields.append((name, d.get("value", "")))
        elif tag == "select":
            self._sel_name = d.get("name")
            self._sel_first = None
            self._sel_opts = []
            self._sel_optlabels = []
        elif tag == "option" and self._sel_name is not None:
            self._in_opt = True
            self._opt_val = d.get("value", "")
            self._opt_sel = "selected" in has
            self._opt_text = ""
            if self._sel_first is None:
                self._sel_first = self._opt_val
        elif tag == "textarea":
            self._ta_name = d.get("name")
            self._ta_buf = ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "option" and self._in_opt:
            self._in_opt = False
            self._sel_opts.append((self._opt_val, self._opt_sel))
            self._sel_optlabels.append((self._opt_val, self._opt_text.strip()))
        elif tag == "select" and self._sel_name is not None:
            chosen = [o for o, sel in self._sel_opts if sel]
            if chosen:
                for c in chosen:
                    self.fields.append((self._sel_name, c))
            elif self._sel_first is not None:
                self.fields.append((self._sel_name, self._sel_first))
            self.selects[self._sel_name] = list(self._sel_optlabels)
            self._sel_name = None
        elif tag == "textarea" and self._ta_name is not None:
            self.fields.append((self._ta_name, self._ta_buf.strip()))
            self._ta_name = None

    def handle_data(self, data: str) -> None:
        if self._in_opt:
            self._opt_text += data
        if self._ta_name is not None:
            self._ta_buf += data


def _clean(label: str) -> str:
    """Strip the &nbsp; padding WONDER wraps option labels in."""
    return re.sub(r"\s+", " ", label.replace("\xa0", " ")).strip()


def _jsessionid(html: str, dataset_id: str) -> str:
    m = re.search(
        rf'action="/controller/datarequest/{dataset_id}(;jsessionid=[0-9A-Fa-f]+)?"',
        html,
    )
    return (m.group(1) or "") if m else ""


def _set(fields: list[tuple[str, str]], name: str, values) -> list[tuple[str, str]]:
    """Replace all occurrences of ``name`` with the given value(s)."""
    if not isinstance(values, list):
        values = [values]
    out = [(n, v) for n, v in fields if n != name]
    out.extend((name, v) for v in values)
    return out


def _resolve_var(select_opts: list[tuple[str, str]], want_label: str) -> str:
    """Return the base variable code (e.g. ``D77.V22``) for a B_1 group-by label."""
    for val, label in select_opts:
        if _clean(label).lower() == want_label.lower():
            # e.g. "D77.V9-level2" -> "D77.V9", "D77.V1-level1" -> "D77.V1"
            return re.sub(r"-level\d+$", "", val)
    raise ValueError(f"group-by label {want_label!r} not found in B_1 options")


def _resolve_option(select_opts: list[tuple[str, str]], want_label: str) -> str:
    """Return the option value whose (cleaned) label matches / starts with want_label."""
    if want_label == "*All*":
        return "*All*"
    for val, label in select_opts:
        cl = _clean(label)
        if cl.lower() == want_label.lower() or cl.lower().startswith(
            want_label.lower()
        ):
            return val
    raise ValueError(
        f"cause label {want_label!r} not found; "
        f"options={[_clean(lbl) for _, lbl in select_opts]}"
    )


def _extract_years(
    selects: dict[str, list[tuple[str, str]]], dataset_id: str
) -> tuple[str, str]:
    opts = selects.get(f"F_{dataset_id}.V1", [])
    yrs = sorted(int(v) for v, _ in opts if re.fullmatch(r"\d{4}", v))
    if not yrs:
        raise ValueError(f"could not determine year range for {dataset_id}")
    return str(yrs[0]), str(yrs[-1])


def _open_request_form(
    session: requests.Session, dataset_id: str, entry: str
) -> tuple[str, str]:
    """GET entry page, accept the DUA, return (request_form_html, jsessionid_token)."""
    entry_url = f"{BASE}/{entry}"
    logger.info("[%s] opening %s", dataset_id, entry_url)
    r = session.get(entry_url, timeout=TIMEOUT_S)
    r.raise_for_status()
    time.sleep(REQUEST_DELAY_S)

    sid = _jsessionid(r.text, dataset_id)
    agree_url = f"{BASE}/controller/datarequest/{dataset_id}{sid}"
    logger.info("[%s] accepting data-use agreement", dataset_id)
    r = session.post(
        agree_url,
        data={"stage": "about", "saved_id": "", "action-I Agree": "I Agree"},
        headers={"Referer": entry_url},
        timeout=TIMEOUT_S,
    )
    r.raise_for_status()
    if "Request Form" not in r.text:
        raise RuntimeError(
            f"[{dataset_id}] DUA acceptance did not return the Request Form"
        )
    time.sleep(REQUEST_DELAY_S)
    return r.text, _jsessionid(r.text, dataset_id)


def _build_export_fields(
    form_html: str,
    dataset_id: str,
    intent_label: str,
    mech_label: str,
    with_aar: bool = True,
) -> list[tuple[str, str]]:
    p = _FormParser()
    p.feed(form_html)
    fields = list(p.fields)
    b1 = p.selects.get("B_1", [])

    county_gb = f"{_resolve_var(b1, 'County')}-level2"
    year_gb = f"{_resolve_var(b1, 'Year')}-level1"
    loc_var = _resolve_var(b1, "State")  # e.g. D77.V9
    intent_var = _resolve_var(b1, "UCD - Injury Intent")  # e.g. D77.V22
    # Mechanism label carries an &-suffix; match by prefix.
    mech_var = None
    for val, label in b1:
        if _clean(label).lower().startswith("ucd - injury mechanism"):
            mech_var = re.sub(r"-level\d+$", "", val)
            break
    if mech_var is None:
        raise ValueError("could not locate UCD - Injury Mechanism group-by")

    intent_code = _resolve_option(p.selects.get(f"V_{intent_var}", []), intent_label)
    mech_code = _resolve_option(p.selects.get(f"V_{mech_var}", []), mech_label)

    # --- group-by: County x Year ---
    fields = _set(fields, "B_1", county_gb)
    fields = _set(fields, "B_2", year_gb)
    fields = _set(fields, "B_3", "*None*")
    fields = _set(fields, "B_4", "*None*")
    fields = _set(fields, "B_5", "*None*")
    # --- location: Georgia (state FIPS 13) ---
    fields = _set(fields, "O_location", loc_var)
    fields = _set(fields, f"F_{loc_var}", GEORGIA_STATE_FIPS)
    # --- cause: Injury Intent mode + intent/mechanism selections, all years ---
    fields = _set(fields, "O_ucd", intent_var)
    fields = _set(fields, f"V_{intent_var}", intent_code)
    fields = _set(fields, f"V_{mech_var}", mech_code)
    fields = _set(fields, f"F_{dataset_id}.V1", "*All*")
    # --- keep suppressed / zero / total rows so markers survive verbatim ---
    fields = _set(fields, "O_show_suppressed", "true")
    fields = _set(fields, "O_show_zeros", "true")
    fields = _set(fields, "O_show_totals", "true")
    # --- add age-adjusted rate (2000 US standard population) ---
    # WONDER forbids AAR when County is in the group-by for some vintages
    # (e.g. the single-race D157); download_dataset retries with_aar=False then.
    if with_aar:
        fields = _set(fields, "O_aar", "aar_std")
        fields = _set(fields, "O_aar_pop", "2000")
        fields.append(("O_aar_enable", "true"))
    # --- export as tab-delimited ---
    fields = _set(fields, "O_export-format", "tsv")
    fields = _set(fields, "O_javascript", "off")
    fields.append(("O_change_action-Send-Export Results", "Export Results"))
    fields.append(("action-Send", "Send"))
    return fields


def _export(
    session: requests.Session,
    dataset_id: str,
    sid: str,
    fields: list[tuple[str, str]],
    entry: str,
) -> str:
    url = f"{BASE}/controller/datarequest/{dataset_id}{sid}"
    r = session.post(
        url,
        data=fields,
        headers={"Referer": f"{BASE}/{entry}"},
        timeout=TIMEOUT_S,
    )
    text = r.text
    # A successful TSV export starts with the tab-delimited header row. WONDER
    # returns validation errors as HTTP 500 with the form + a "Messages" block,
    # so read the body regardless of status rather than raising on 500.
    first_line = text.split("\n", 1)[0]
    if "County Code" in first_line and "\t" in first_line:
        return text
    i = text.find("Messages")
    if i > 0:
        msg = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text[i : i + 1200]))
        raise RuntimeError(f"[{dataset_id}] export rejected; server said: {msg[:800]}")
    r.raise_for_status()  # genuine transport error with no message block
    raise RuntimeError(
        f"[{dataset_id}] export did not return TSV (status {r.status_code})"
    )


def download_dataset(
    session: requests.Session, dataset: dict, only_measures=None
) -> list[dict]:
    dataset_id = dataset["id"]
    form_html, sid = _open_request_form(session, dataset_id, dataset["entry"])

    # Determine the vintage's year span from its own year finder.
    yp = _FormParser()
    yp.feed(form_html)
    ystart, yend = _extract_years(yp.selects, dataset_id)

    results = []
    measures = only_measures or list(MEASURE_GROUPS)
    for measure in measures:
        cfg = MEASURE_GROUPS[measure]
        logger.info(
            "[%s] exporting %s (intent=%s, mech=%s)",
            dataset_id,
            measure,
            cfg["intent"],
            cfg["mech"],
        )
        fields = _build_export_fields(
            form_html, dataset_id, cfg["intent"], cfg["mech"], with_aar=True
        )
        try:
            tsv = _export(session, dataset_id, sid, fields, dataset["entry"])
            has_aar = True
        except RuntimeError as exc:
            if "Age Adjusted Rate" not in str(exc):
                raise
            logger.info(
                "[%s]   age-adjusted rate unavailable at county grain; retrying without it",
                dataset_id,
            )
            time.sleep(REQUEST_DELAY_S)
            fields = _build_export_fields(
                form_html, dataset_id, cfg["intent"], cfg["mech"], with_aar=False
            )
            tsv = _export(session, dataset_id, sid, fields, dataset["entry"])
            has_aar = False
        out = BRONZE_DIR / f"{measure}_by_county_year_{ystart}_{yend}.txt"
        out.write_text(tsv, encoding="utf-8")
        # Count data rows (before the "---" caveats/notes block).
        data_rows = 0
        for line in tsv.splitlines()[1:]:
            if line.startswith('"---"') or line.strip() == "---":
                break
            if line.strip():
                data_rows += 1
        logger.info(
            "[%s]   wrote %s (%d bytes, ~%d data rows)",
            dataset_id,
            out.name,
            len(tsv),
            data_rows,
        )
        results.append(
            {
                "dataset_id": dataset_id,
                "dataset_label": dataset["label"],
                "measure": measure,
                "intent": cfg["intent"],
                "mech": cfg["mech"],
                "file": out.name,
                "bytes": len(tsv),
                "data_rows": data_rows,
                "year_start": ystart,
                "year_end": yend,
                "age_adjusted_rate": has_aar,
            }
        )
        time.sleep(REQUEST_DELAY_S)
    return results


def write_provenance(results: list[dict]) -> None:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Provenance — CDC WONDER firearm / homicide / legal-intervention deaths (GA counties)",
        "",
        f"_Retrieved: {now}_",
        "",
        "## Source",
        "",
        "- **Tool**: CDC WONDER, Multiple Cause of Death (MCD) online query system.",
        "- **Landing page**: <https://wonder.cdc.gov/mcd.html>",
        "- **Datasets** (two race-coding vintages, NCHS/NVSS death certificates):",
        "  - **D77** — Multiple Cause of Death, 1999-2020 (**bridged-race** populations); "
        "entry <https://wonder.cdc.gov/mcd-icd10.html>",
        "  - **D157** — Multiple Cause of Death, 2018-2024, **Single Race**; "
        "entry <https://wonder.cdc.gov/mcd-icd10-expanded.html>",
        "",
        "## Method (scripted web-app form POST)",
        "",
        "The official WONDER **XML API cannot return county-level data** (sub-national grouping",
        "is API-blocked). County extracts are therefore pulled by replicating the web app's HTML",
        "form POST, via `src/etl/criminal_justice/cdc/download.py`:",
        "",
        "1. GET the dataset entry page to open a session.",
        "2. POST the **data-use-agreement** acceptance (`stage=about`, `action-I Agree=I Agree`).",
        "   The session is tracked by a URL-rewritten `;jsessionid=...` token in the returned",
        "   form's action (not a cookie); every subsequent POST reuses that token.",
        "3. Submit the full Request Form (all inputs, selects, and the ICD-code `<textarea>`",
        "   finders) with overrides: group by **County x Year**, filter **State = Georgia**",
        "   (FIPS 13), Injury-Intent cause mode, per-measure intent/mechanism selections, all",
        "   years, show-suppressed + show-zeros + show-totals, age-adjusted rate (2000 US std",
        "   population), and `O_export-format=tsv` + `action-Send=Send` for a tab-delimited export.",
        "",
        "Requests are sequential with a polite delay and an identifying User-Agent.",
        "",
        "## Measures / columns",
        "",
        "Grain: **residence county x year**. Columns: Deaths, Population, Crude Rate, and",
        "(where available) Age Adjusted Rate (per 100,000; 2000 US standard population).",
        "WONDER forbids age-adjusted rates at county grain for the single-race **D157**",
        "vintage, so those exports carry Deaths / Population / Crude Rate only (see table).",
        "",
        "## Cause definitions (ICD-10 injury intent + mechanism recodes)",
        "",
        "- `firearm_deaths` — all intents, **Firearm** mechanism (all firearm deaths).",
        "- `homicide` — **Homicide** intent, all mechanisms.",
        "- `firearm_homicide` — **Homicide** intent + **Firearm** mechanism.",
        "- `legal_intervention` — **Legal Intervention / Operations of War** intent, all mechanisms.",
        "",
        "## Suppression / reliability (markers kept VERBATIM in bronze)",
        "",
        "- **Suppressed** — sub-national death counts **< 10** are suppressed (privacy).",
        "- **Unreliable** — rates computed from **< 20** deaths are flagged unreliable.",
        "- Zero-death county-years are included (show-zeros on).",
        "- Residence county (decedent's county of residence), not occurrence county.",
        "- Do **not** substitute 0 for suppressed cells — the transform NULLs them (never 0).",
        "",
        "## Files",
        "",
        "| File | Dataset | Measure | Years | Bytes | ~Data rows | AAR col |",
        "| ---- | ------- | ------- | ----- | ----- | ---------- | ------- |",
    ]
    for r in results:
        lines.append(
            f"| `{r['file']}` | {r['dataset_id']} | {r['measure']} | "
            f"{r['year_start']}-{r['year_end']} | {r['bytes']:,} | {r['data_rows']:,} | "
            f"{'yes' if r['age_adjusted_rate'] else 'no'} |"
        )
    lines.append("")
    lines.append("## Citation")
    lines.append("")
    lines.append(
        "Centers for Disease Control and Prevention, National Center for Health Statistics. "
        "Multiple Cause of Death data on CDC WONDER Online Database. Data are from the Multiple "
        "Cause of Death Files, as compiled from data provided by the 57 vital statistics "
        "jurisdictions through the Vital Statistics Cooperative Program. Accessed at "
        "<https://wonder.cdc.gov/mcd.html>."
    )
    lines.append("")
    (BRONZE_DIR / "_provenance.md").write_text("\n".join(lines), encoding="utf-8")
    logger.info("wrote %s", (BRONZE_DIR / "_provenance.md"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--dataset", choices=[d["id"] for d in DATASETS], help="only this vintage"
    )
    ap.add_argument(
        "--measure",
        choices=list(MEASURE_GROUPS),
        action="append",
        help="only these measure groups",
    )
    args = ap.parse_args()

    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    datasets = [d for d in DATASETS if not args.dataset or d["id"] == args.dataset]
    all_results: list[dict] = []
    for ds in datasets:
        all_results.extend(download_dataset(session, ds, only_measures=args.measure))

    write_provenance(all_results)
    logger.info("done: %d export(s) into %s", len(all_results), BRONZE_DIR)


if __name__ == "__main__":
    main()
