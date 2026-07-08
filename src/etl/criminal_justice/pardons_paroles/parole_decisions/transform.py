"""Transform GA Board of Pardons & Paroles annual-report PDFs into gold.

Source: 25 narrative annual-report PDFs (FY2001-FY2025) of the State Board of
Pardons and Paroles. Grain: **statewide x fiscal year** (GA FY = Jul 1-Jun 30;
the headline year is the END year), one row per fiscal year. FY2015 is missing
at the source (the agency never published it) — the gap is left as a missing
year partition, never interpolated. FY2016 exists twice in bronze; only
``annual_report_fy2016.pdf`` (standard layout) is ingested and the 2-up
``annual_report_fy2016_spread.pdf`` duplicate is skipped (kept for provenance
only, per bronze-data-structure.md).

Design decisions (from bronze-data-structure.md, data-cleaning-standards, and
the criminal_justice domain conventions):

- **Three layout eras, one label crosswalk.** Era 1 "classic" (FY2001-FY2009):
  clean back-of-book text tables; Era 2 "magazine" (FY2010-FY2014): the same
  tables in sidebar callouts; Era 3 post-HB310 "infographic" (FY2016-FY2025):
  a right-column stats table plus big-number tiles and prose. Metric labels
  drift across eras ("TOTAL DECISIONS UNDER GUIDELINES" / "Total Guidelines
  Decisions", "Parole" / "Parole Certificates", ...). Extraction is a single
  label->canonical crosswalk (``TABLE_LABELS``) applied to pdfplumber word
  geometry — stats pages are detected by content (>=3 crosswalk hits), never
  by hardcoded page numbers — plus era-scoped prose regexes for values that
  are only published in sentences (revocations FY2014+, completion rate,
  clemency votes, DCS-era population, expenditures). The crosswalk hits are
  recorded on the manifest as the ``metric_source_label`` recode map so the
  data review can verify every label->metric assignment.
- **"Total Prison Releases by Parole" (Era 3) is the release-actions TOTAL,
  not the parole line.** Component sums prove it (FY2016: 7,233+426+904+183+
  1,517+21+2,850+25+215 = 13,374; FY2025: 4,037+294+710+128+409+0+0+10+0 =
  5,588), so it maps to ``total_releases`` together with Era 1/2 "TOTAL
  RELEASES" and the FY2009 prose figure — the one series present in every
  report year, and therefore the key metric. The Era 1/2 "Parole" line
  (``parole_releases``) and the FY2014+ "Parole Certificates" line
  (``parole_certificates``) are kept as separate, era-scoped metrics — they
  are related but not provably the same concept, so they are never pooled.
- **HB310 (2015) methodological break.** Effective FY2016, parole field
  supervision moved from the Board to the Dept. of Community Supervision.
  Every row carries a ``supervision_era`` categorical (``board`` FY2001-2014,
  ``dcs`` FY2016-2025) — the same coverage-flag pattern jail_population uses —
  so the supervision-series metrics (population, completion rate, revocations)
  are never pooled across the boundary unflagged. The clemency-decision series
  (releases, guidelines, life, pardons) is the continuous one.
- **Statewide grain, no geography column.** Mirrors gdc/inmate_population:
  ``county_fips`` is omitted entirely (a 100%%-NULL FK would surface a dead
  county filter in the API); rows are tagged ``detail_level='state'`` so
  export writes ``states.parquet``.
- **Hand-transcribed years (sanctioned constants).** FY2002 is a scanned
  image-only PDF, and FY2007/FY2008 embed the clemency table as a page image —
  no text layer exists to parse. Their values live in ``TRANSCRIBED_VALUES``,
  each year annotated with its PDF page provenance, transcribed from 200-dpi
  page renders at authoring time. The same internal-sum verifications run on
  transcribed years as on parsed years.
- **Verification net.** Every year passes: (a) internal component-sum
  identities (release actions == total; life granted+denied == total;
  discharge components == total; population components == total; guidelines
  initial+other == total; pardons+restorations == combined total); (b) a
  pinned ``ANCHORS`` table of values re-verified during authoring via a
  second extraction path (pdftotext -layout) and adjacent-report
  restatements (e.g. the FY2025 report's FY21-FY24 revocations chart, the
  FY2014 report restating FY2013 revocations); (c) a DCS-era population
  chain check (each year's July-1 start == prior year's June-30 end, which
  holds for all of FY2017-FY2025); (d) an ``EXPECTED_COVERAGE`` matrix that
  asserts the exact per-metric NULL pattern, so a silently-failed parse can
  never ship as an unexplained NULL.
- **No suppression, no §4b masks.** The Board publishes unsuppressed
  statewide aggregates; NULL means "not published in that year's report"
  (``suppressed_to_null=False``, per-column ``null_meaning``). No value is
  impossible on its scale — nothing is masked; every extracted value is
  anchor- or sum-verified instead.
- **Percent -> proportion.** The successful-completion rate is quoted as a
  whole-number percent and is scaled to [0,1] (§4). FY2001-FY2004 rates are
  NOT served: those years published only an "RDS successful outcome rate" on
  a different formula (national avg quoted ~42%%) that is not comparable to
  the BJS-methodology completion series the Board reports from FY2005 on.
- **Currency as published.** ``total_expenditures`` is the report's own
  agency-expenditures total, kept verbatim (never recomputed, summed, or
  inflation-adjusted). Years that publish only line items without a total
  (FY2009) or only fund-source budgets (FY2012, FY2013) or nothing (FY2014)
  are NULL.
- **Cost-avoidance / cost-per-day figures are intentionally not served.**
  The reports publish cost metrics — per-day parole-vs-prison cost
  comparisons in the early eras, an aggregate annual "cost avoidance" dollar
  figure (e.g. FY2025's "$380 MILLION") in Era 3 — but their stated basis
  changes across eras and the values live in chart labels and prose that do
  not survive text extraction reliably (bronze-data-structure.md ETL #2/#11:
  "document, don't recompute"). The exclusion is documented in the contract
  limitations; ``total_expenditures`` is the only served cost metric. Serving
  them later as era-scoped metrics would be an additive schema change.
- **Dedup tie-break.** One report per fiscal year makes natural-key
  collisions impossible by construction; the collision guard runs first and
  ``deduplicate_by_levels(sort_col="total_releases")`` remains the documented
  safety net (prefer the row with the larger non-null release total) should a
  future refresh ever add an overlapping file.
- **Year floor.** All fiscal years are 2001-2025, but the ``year >= 2000``
  floor is applied defensively and recorded in the contract limitations.
"""

import logging
import re
from collections import defaultdict
from pathlib import Path

import pdfplumber
import polars as pl

from src.utils.metadata import write_data_dictionary
from src.utils.transformers import (
    COUNTY_DETAIL_LEVEL_FILES,
    TransformManifest,
    assert_no_natural_key_collisions,
    deduplicate_by_levels,
    export_to_parquet,
    harmonize_columns,
    validate_output,
)
from src.utils.validators import check_null_rate_spikes, run_topic_validation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

TOPIC = "parole_decisions"
BRONZE_DIR = Path("data/bronze/criminal_justice/pardons_paroles/parole_decisions")
GOLD_DIR = Path("data/gold/criminal_justice/parole_decisions")
SOURCE_URL = (
    "https://pap.georgia.gov/office-communications-news-publications-and-events/"
    "publications/annual-reports"
)

YEAR_FLOOR = 2000  # defensive floor (orchestrated rebuild rule); data is 2001+
MISSING_YEARS = {2015}  # never published by the agency — leave the gap
# 2-up duplicate of the FY2016 report kept for provenance only — never ingested.
SKIP_FILES = {"annual_report_fy2016_spread.pdf"}

ALL_YEARS: list[int] = [y for y in range(2001, 2026) if y not in MISSING_YEARS]

# HB310 (eff. 2015-07-01 = start of FY2016) moved parole field supervision from
# the Board (SBPP) to the Dept. of Community Supervision. The flag versions the
# supervision-series metrics so they are never pooled across the break.
HB310_LAST_BOARD_YEAR = 2014


def _supervision_era(year: int) -> str:
    return "board" if year <= HB310_LAST_BOARD_YEAR else "dcs"


METRIC_COLUMNS: list[str] = [
    "total_releases",
    "parole_releases",
    "parole_certificates",
    "supervised_reprieves",
    "conditional_transfers",
    "commutations",
    "guidelines_decisions_total",
    "guidelines_decisions_initial",
    "life_cases_granted",
    "life_cases_denied",
    "life_decisions_total",
    "parole_revocations",
    "total_discharges",
    "pardons_granted",
    "rights_restorations",
    "clemency_votes",
    "parole_population_start",
    "parole_population_end",
    "parole_completion_rate",
    "total_expenditures",
]

STANDARD_COLUMNS: list[str] = [
    "year",
    "supervision_era",
    *METRIC_COLUMNS,
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "supervision_era": pl.Utf8,
    **{c: pl.Int64 for c in METRIC_COLUMNS},
    "parole_completion_rate": pl.Float64,
    "total_expenditures": pl.Float64,
    "detail_level": pl.Utf8,
}

NATURAL_KEYS: list[str] = ["year", "detail_level"]

SUPERVISION_ERA_MAP: dict[str, str] = {"board": "board", "dcs": "dcs"}

# =============================================================================
# Label -> canonical metric crosswalk (all eras, one table)
# =============================================================================
# Keys are normalized token tuples (lowercased, dashes unified, edge
# punctuation stripped, dot-leaders split off). Values starting with "_" are
# internal verification-only series (release/discharge/population components,
# rollups) used by the sum checks but not served in gold. Matching is
# longest-label-first with word-span consumption, so "Out-of-State Conditional
# Transfers" can never be double-counted as "Conditional Transfers".

TABLE_LABELS: dict[tuple[str, ...], str] = {
    # --- Era 1/2 clemency-action table (FY2001-FY2013) ---
    ("parole",): "parole_releases",
    ("supervised", "reprieve"): "supervised_reprieves",
    ("conditional", "transfer"): "conditional_transfers",
    ("commutation",): "commutations",
    ("remission",): "_remission",
    ("other", "release", "action"): "_other_releases",
    ("other", "release", "actions"): "_other_releases",
    ("total", "releases"): "total_releases",
    ("total", "parole", "revocations"): "parole_revocations",
    ("discharge", "from", "parole"): "_discharge_from_parole",
    ("discharge", "parole"): "_discharge_from_parole",  # FY2006 "Discharge / Parole"
    ("discharge", "from", "supervised", "reprieve"): "_discharge_from_reprieve",
    ("discharge", "from", "reprieve"): "_discharge_from_reprieve",
    (
        "discharge",
        "reprieve",
    ): "_discharge_from_reprieve",  # FY2006 "Discharge / Reprieve"
    ("commutation", "to", "discharge", "parole"): "_commutation_to_discharge",
    ("total", "discharges"): "total_discharges",
    ("total", "decisions", "under", "guidelines"): "guidelines_decisions_total",
    (
        "total",
        "decision",
        "under",
        "guidelines",
    ): "guidelines_decisions_total",  # FY2006
    ("initial", "decisions", "under", "guidelines"): "guidelines_decisions_initial",
    ("deny", "parole", "to", "life", "cases"): "life_cases_denied",
    ("grant", "parole", "to", "life", "cases"): "life_cases_granted",
    ("total", "life", "decisions"): "life_decisions_total",
    ("pardon",): "pardons_granted",
    ("restoration", "of", "rights"): "rights_restorations",
    ("georgia", "releases", "in", "georgia"): "_pop_ga_in_ga",
    ("out-of-state", "releases", "in", "georgia"): "_pop_oos_in_ga",
    ("georgia", "releases", "out", "of", "state"): "_pop_ga_oos",
    ("georgia", "releases", "out-of-state"): "_pop_ga_oos",
    ("total", "parolee", "population"): "parole_population_end",
    ("total", "parole", "population"): "parole_population_end",  # FY2013/FY2014
    # --- FY2014 + Era 3 stats table ---
    ("parole", "certificates"): "parole_certificates",
    ("out-of-state", "parole", "orders"): "_oos_parole_orders",
    ("conditional", "transfers"): "conditional_transfers",
    ("out-of-state", "conditional", "transfers"): "_oos_conditional_transfers",
    ("supervised", "reprieves"): "supervised_reprieves",
    ("out-of-state", "supervised", "reprieves"): "_oos_supervised_reprieves",
    ("commutations",): "commutations",
    ("medical", "reprieves"): "_medical_reprieves",
    ("out-of-state", "ice", "orders"): "_oos_ice_orders",
    ("total", "prison", "releases", "by", "parole"): "total_releases",
    ("total", "discharges", "from", "parole"): "total_discharges",
    ("initial", "guidelines", "decisions"): "guidelines_decisions_initial",  # FY2017
    ("other", "guidelines", "decisions"): "_other_guidelines_decisions",
    ("total", "guidelines", "decisions"): "guidelines_decisions_total",
    ("life", "sentenced", "cases", "denied", "parole"): "life_cases_denied",  # FY2016
    ("life", "sentence", "cases", "denied", "parole"): "life_cases_denied",
    ("life", "sentence", "cases", "denied"): "life_cases_denied",
    ("life", "sentenced", "cases", "granted", "parole"): "life_cases_granted",
    ("life", "sentence", "cases", "granted", "parole"): "life_cases_granted",
    ("life", "sentence", "cases", "granted"): "life_cases_granted",
    ("life", "sentence", "cases", "granted/released"): "life_cases_granted",  # FY24/25
    ("total", "life", "sentenced", "case", "decisions"): "life_decisions_total",
    ("total", "life", "sentence", "case", "decisions"): "life_decisions_total",
    ("restoration", "of", "rights", "granted"): "rights_restorations",
    # FY2020-FY2022 spell the full label on one line:
    (
        "restoration",
        "of",
        "civil",
        "and",
        "political",
        "rights",
        "granted",
    ): "rights_restorations",
    ("pardon", "grants"): "pardons_granted",
    ("pardons", "granted", "all", "types"): "pardons_granted",  # FY2014
    ("total", "pardons", "&", "restorations", "granted"): "_total_pardons_restorations",
    ("total", "pardons", "restorations", "granted"): "_total_pardons_restorations",
}

# Some years wrap the restoration label across two physical lines: match the
# second-line tokens + value only when the first-line tokens sit just above.
# FY2018/FY2019 wrap "Restoration of Civil and Political" / "Rights Granted
# ....N"; FY2023/FY2024 wrap one word earlier — "Restoration of Civil and" /
# "Political Rights Granted ....N" (95 and 100, both corroborated by the
# published Pardon Grants + restorations = Total Pardons & Restorations
# Granted identity: 469+95=564 FY2023, 346+100=446 FY2024).
WRAPPED_LABELS: list[tuple[tuple[str, ...], tuple[str, ...], str]] = [
    (
        ("restoration", "of", "civil", "and", "political"),
        ("rights", "granted"),
        "rights_restorations",
    ),
    (
        ("restoration", "of", "civil", "and"),
        ("political", "rights", "granted"),
        "rights_restorations",
    ),
]

# Bare one-token labels only match on pages that already carry >=2 multi-token
# crosswalk hits (they are far too generic for prose pages).
BARE_LABELS = {
    ("parole",),
    ("commutation",),
    ("remission",),
    ("pardon",),
    ("commutations",),
}
# The only bare label eligible for the offset-baseline band fallback:
# "Commutations" in the FY2025 big-number stats table. The Era 1/2 bare labels
# ("Parole", "Pardon", ...) always print value-on-line and would false-match
# prose lines ending in those words if band-eligible.
BAND_BARE_LABELS = {("commutations",)}

# Internal series: extracted for verification, never served.
INTERNAL_METRICS = {
    "_remission",
    "_other_releases",
    "_discharge_from_parole",
    "_discharge_from_reprieve",
    "_commutation_to_discharge",
    "_pop_ga_in_ga",
    "_pop_oos_in_ga",
    "_pop_ga_oos",
    "_oos_parole_orders",
    "_oos_conditional_transfers",
    "_oos_supervised_reprieves",
    "_medical_reprieves",
    "_oos_ice_orders",
    "_other_guidelines_decisions",
    "_total_pardons_restorations",
}

# The manifest crosswalk map (bronze label string -> canonical metric) that
# record_categorical() verifies coverage against.
LABEL_CROSSWALK_MAP: dict[str, str] = {
    " ".join(tokens): canonical for tokens, canonical in TABLE_LABELS.items()
} | {" ".join(first + second): canonical for first, second, canonical in WRAPPED_LABELS}

# =============================================================================
# Prose patterns (era/year-scoped; values published only in sentences/tiles)
# =============================================================================
# Each entry: (metric, years the pattern applies to, list of regexes tried in
# order — first regex with matches wins; divergent multi-matches raise).
# Regexes run over column-threaded, dehyphenated page text (see
# _threaded_text), so sentences wrapped across lines inside one column match.

_ERA3_YEARS = set(range(2016, 2026))

PROSE_PATTERNS: list[tuple[str, set[int], list[str]]] = [
    # FY2009's 18-page mini-report publishes the release total only in prose.
    (
        "total_releases",
        {2009},
        [r"By Board action ([\d,]+) offenders were released"],
    ),
    # Era 3 (and FY2014) publish revocations only in prose; the FY2025 report's
    # FY21-FY25 bar chart restates them, anchoring the whole recent series.
    (
        "parole_revocations",
        {2014},
        [r"([\d,]+) offenders had their paroles revoked"],
    ),
    (
        "parole_revocations",
        _ERA3_YEARS,
        [
            r"Board revoked ([\d,]+) parole vio",
            r"\(revoked\) ([\d,]+) parole violators",  # FY2016 wording
        ],
    ),
    # Successful parole completion rate (whole-number percent -> proportion).
    # P4 (Era 3) -> P3 (FY2014) -> P2 (Era 2) -> P1 (FY2005-FY2009); the P1
    # window rejects the national-average comparison sentences.
    (
        "parole_completion_rate",
        set(range(2005, 2015)) | _ERA3_YEARS,
        [
            r"successful parole completions? was (\d{2})%",
            # FY2023 wraps the sentence mid-phrase across an interleaved
            # column boundary; the tail clause is still unambiguous.
            r"completions? was (\d{2})% for the fiscal year",
            r"parole completion success rate was (\d{2})%",
            r"successfully completing (?:their )?parole supervision"
            r" (?:rose to|was) (\d{2})%",
            r"(\d{2})%(?:(?![.]|national|average)[\s\S]){0,90}?successfully complet",
        ],
    ),
    # Clemency votes: prose in FY2009-FY2014 and FY2019-FY2024, tile in FY2025.
    (
        "clemency_votes",
        set(range(2009, 2015)) | set(range(2019, 2026)),
        [
            r"(?:completed|made) a total of ([\d,]+) (?:individual |clemency )?votes",
            r"made ([\d,]+) clemency votes",
            r"cast ([\d,]+) individual votes",
            r"([\d,]+) [Cc]lemency votes",
            r"CLEMENCY VOTES ([\d,]+)",
        ],
    ),
    # DCS-era parole population: "...from N on July 1, YYYY, to M on June 30,
    # YYYY" (the Era 2 narrative publishes an in-state-basis pair that is NOT
    # comparable to the Era 1/2 table series, so it is deliberately not
    # captured — see the module docstring).
    (
        "_population_pair",
        _ERA3_YEARS,
        [
            # Tight form: "...from 15,105 on July 1, 2024, to 14,568 (on June
            # 30 ...)". Comma-grouped thousands required so chart axis labels
            # ("80%") can never be captured.
            r"from (\d{1,3}(?:,\d{3})+) on July 1,? \d{4},? to (\d{1,3}(?:,\d{3})+)",
            # Windowed form for FY2022, whose sentence wraps across a line
            # that column-threading interleaves with a chart: the June-30
            # value is the first comma-grouped number followed by "on June 30"
            # after the July-1 clause.
            r"from (\d{1,3}(?:,\d{3})+) on July 1[\s\S]{0,800}?"
            r"(\d{1,3}(?:,\d{3})+) on June 30",
        ],
    ),
    # FY2025 dropped the discharges line from the stats table; prose only.
    # For FY2017-FY2024 the same sentence exists and must equal the table
    # value (cross-verified in _merge_value).
    (
        "total_discharges",
        _ERA3_YEARS - {2016},
        [r"discharg(?:ed|ing) from parole was ([\d,]+)"],
    ),
]

# Agency expenditures total. Matched against visual-line text (the era-1
# table's wide label-value gutter breaks threaded prose), requiring a
# millions-format value (two comma groups) so stray small numbers like the
# "2018" in "FOR FY 2018" can never be captured; FY2018 renders the value in a
# larger font on an offset baseline, handled by a vertical-band fallback. The
# label wording drifts wildly across eras and a pinned anchor verifies every
# captured value.
EXPENDITURE_YEARS: set[int] = set(range(2001, 2009)) | {2010, 2011} | _ERA3_YEARS
_MILLIONS = r"\$?(\d{1,3}(?:,\d{3}){2,}(?:\.\d{2})?)"
EXPENDITURE_LINE_PATTERNS: list[str] = [
    # "TOTAL EXPENDITURES $50,837,957" / "... FOR FY 2019 $..." / "... 2023 $..."
    rf"(?i)total expenditures(?: for)?(?: fy ?\d{{2,4}}| \d{{4}})?\s*{_MILLIONS}",
    # "Total FY25 Expenditures $21,634,700.96"
    rf"(?i)total fy ?\d{{2,4}} expenditures\s*{_MILLIONS}",
    # "FY 2017 Expenditures | Total: $16,846,903" / "FY24 Expenditures $20,240,569.85"
    rf"(?i)fy ?\d{{2,4}} expenditures(?: \| total:)?\s*{_MILLIONS}",
    # FY2016: a bare "Total: $45,782,940" line on the EXPENDITURES page (the
    # page-scope guard is applied in _extract_expenditures).
    rf"(?i)^total: {_MILLIONS}$",
]
# Band fallback (FY2018/FY2019): the value renders in a larger font on an
# offset baseline, splitting it out of the label's visual line — anchor on the
# "TOTAL EXPENDITURES" token pair and take the nearest millions-format token
# to the right with vertical overlap.
_MILLIONS_TOKEN_RE = re.compile(r"^\$?\d{1,3}(?:,\d{3}){2,}(?:\.\d{2})?$")

# =============================================================================
# Hand-transcribed years (image-only tables; sanctioned constants)
# =============================================================================
# FY2002 is a fully scanned PDF (no text layer at all); FY2007 and FY2008
# embed the clemency table as a single page image. Values below were
# transcribed at authoring time from 200-dpi renders (pdftoppm) of the cited
# pages, and every component-sum identity is re-verified at runtime by the
# same checks that guard parsed years.
TRANSCRIBED_VALUES: dict[int, dict[str, int | float]] = {
    # annual_report_fy2002.pdf — "FY2002 Activities" table, PDF page 38
    # (printed p.37); "FY2002 Expenditures" table, PDF page 37 (printed p.36).
    2002: {
        "parole_releases": 7804,
        "supervised_reprieves": 1817,
        "conditional_transfers": 638,
        "commutations": 12,
        "_remission": 0,
        "_other_releases": 0,
        "total_releases": 10271,
        "parole_revocations": 2685,
        "_discharge_from_parole": 5603,
        "_discharge_from_reprieve": 1316,
        "_commutation_to_discharge": 141,
        "total_discharges": 7060,
        "guidelines_decisions_total": 12864,
        "life_cases_denied": 458,
        "life_cases_granted": 173,
        "life_decisions_total": 631,
        "pardons_granted": 506,
        "rights_restorations": 244,
        "_pop_ga_in_ga": 19799,
        "_pop_oos_in_ga": 548,
        "_pop_ga_oos": 1213,
        "parole_population_end": 21560,
        "total_expenditures": 51448774.0,
    },
    # annual_report_fy2007.pdf — "Clemency Action in FY 07" table image,
    # PDF page 26 (printed p.26). Completion rate (61%) and expenditures
    # ($51,403,882) are text-extractable elsewhere in the report and are
    # parsed, not transcribed.
    2007: {
        "parole_releases": 8476,
        "supervised_reprieves": 2013,
        "conditional_transfers": 957,
        "commutations": 0,
        "_remission": 0,
        "_other_releases": 0,
        "total_releases": 11446,
        "parole_revocations": 3560,
        "_discharge_from_parole": 5793,
        "_discharge_from_reprieve": 2043,
        "_commutation_to_discharge": 261,
        "total_discharges": 8097,
        "guidelines_decisions_total": 11536,  # label "TOTAL DECISION UNDER GUIDELINES"
        "life_cases_denied": 595,
        "life_cases_granted": 154,
        "life_decisions_total": 749,
        "pardons_granted": 372,
        "rights_restorations": 211,
        "_pop_ga_in_ga": 20105,
        "_pop_oos_in_ga": 779,
        "_pop_ga_oos": 2457,
        "parole_population_end": 23341,
    },
    # annual_report_fy2008.pdf — "CLEMENCY ACTIONS IN FY 08" table image,
    # PDF page 22 (printed p.22). FY2008 is the first year the guidelines line
    # reads "INITIAL DECISIONS UNDER GUIDELINES". Completion (64%) and
    # expenditures ($55,980,192) are text-extractable and parsed.
    2008: {
        "parole_releases": 9502,
        "supervised_reprieves": 1850,
        "conditional_transfers": 931,
        "commutations": 0,
        "_remission": 0,
        "_other_releases": 0,
        "total_releases": 12283,
        "parole_revocations": 3125,
        "_discharge_from_parole": 5899,
        "_discharge_from_reprieve": 2033,
        "_commutation_to_discharge": 381,
        "total_discharges": 8313,
        "guidelines_decisions_initial": 10865,
        "life_cases_denied": 468,
        "life_cases_granted": 200,
        "life_decisions_total": 668,
        "pardons_granted": 560,
        "rights_restorations": 152,
        "_pop_ga_in_ga": 20701,
        "_pop_oos_in_ga": 856,
        "_pop_ga_oos": 2577,
        "parole_population_end": 24134,
    },
}

# =============================================================================
# Expected coverage matrix (the exact per-metric NULL pattern)
# =============================================================================
# Asserted after extraction: a served metric must be non-NULL in exactly these
# years. Any deviation — a silently-failed parse OR an unexpected new match —
# fails the run loudly. This doubles as the documentation of which report
# years publish which figure.
_Y = set(ALL_YEARS)
EXPECTED_COVERAGE: dict[str, set[int]] = {
    "total_releases": set(_Y),
    "parole_releases": set(range(2001, 2009)) | set(range(2010, 2014)),
    "parole_certificates": {2014} | _ERA3_YEARS,
    "supervised_reprieves": _Y - {2009},
    "conditional_transfers": _Y - {2009},
    "commutations": _Y - {2009},
    "guidelines_decisions_total": set(range(2001, 2008)) | _ERA3_YEARS,
    "guidelines_decisions_initial": {2008} | set(range(2010, 2015)) | {2016, 2017},
    "life_cases_granted": _Y - {2009},
    "life_cases_denied": _Y - {2009},
    "life_decisions_total": _Y - {2009},
    "parole_revocations": _Y - {2009},
    "total_discharges": _Y - {2009},
    "pardons_granted": _Y - {2009, 2025},
    "rights_restorations": _Y - {2009, 2025},
    "clemency_votes": set(range(2009, 2015)) | set(range(2019, 2026)),
    "parole_population_start": set(_ERA3_YEARS),
    "parole_population_end": _Y - {2009},
    "parole_completion_rate": set(range(2005, 2015)) | _ERA3_YEARS,
    "total_expenditures": set(range(2001, 2009)) | {2010, 2011} | _ERA3_YEARS,
}

# =============================================================================
# Anchors (authoring-time verified values; loud failure on any drift)
# =============================================================================
# Every anchored value was verified during authoring via a second extraction
# path (pdftotext -layout or a 200-dpi page render) and, where available,
# adjacent-report restatements: the FY2014 report restates FY2013 revocations
# (2,199) and the FY2025 report's bar chart restates FY2021-FY2024 revocations
# (2,373 / 1,825 / 1,552 / 1,437). All currency totals and a per-era spread of
# every other metric are pinned.
ANCHORS: dict[int, dict[str, int | float]] = {
    2001: {
        "total_releases": 10164,
        "parole_releases": 7305,
        "parole_revocations": 3383,
        "guidelines_decisions_total": 13630,
        "pardons_granted": 533,
        "rights_restorations": 332,
        "parole_population_end": 21431,
        "total_expenditures": 50837957.0,
    },
    2003: {
        "life_cases_granted": 167,
        "life_cases_denied": 387,
        "life_decisions_total": 554,
        "total_discharges": 7150,
        "total_expenditures": 49027202.0,
    },
    2004: {"total_expenditures": 47434074.69},
    2005: {
        "total_releases": 12708,
        "parole_population_end": 24276,
        "parole_completion_rate": 0.60,
        "total_expenditures": 45135674.89,
    },
    2006: {
        "guidelines_decisions_total": 14776,
        "parole_completion_rate": 0.60,
        "total_expenditures": 49581000.94,
    },
    2007: {"parole_completion_rate": 0.61, "total_expenditures": 51403882.0},
    2008: {"parole_completion_rate": 0.64, "total_expenditures": 55980192.0},
    2009: {
        "total_releases": 12938,
        "clemency_votes": 75245,
        "parole_completion_rate": 0.66,
    },
    2010: {
        "total_releases": 13926,
        "clemency_votes": 79922,
        "parole_completion_rate": 0.69,
        "total_expenditures": 51383648.0,
    },
    2011: {"guidelines_decisions_initial": 8585, "total_expenditures": 54849088.0},
    2012: {"commutations": 19, "clemency_votes": 63667},
    2013: {
        "total_releases": 15634,
        "parole_releases": 10828,
        "parole_revocations": 2199,  # restated by the FY2014 report
        "total_discharges": 11846,
        "pardons_granted": 1349,
        "rights_restorations": 232,
        "clemency_votes": 88302,
        "parole_population_end": 27285,
    },
    2014: {
        "total_releases": 16212,
        "parole_certificates": 8934,
        "parole_revocations": 2380,
        "pardons_granted": 1151,
        "rights_restorations": 170,
        "parole_population_end": 27170,
        "parole_completion_rate": 0.72,
    },
    2016: {
        "total_releases": 13374,
        "parole_certificates": 7233,
        "guidelines_decisions_total": 8439,
        "guidelines_decisions_initial": 6888,
        "parole_revocations": 2505,
        "total_discharges": 9159,
        "pardons_granted": 587,
        "rights_restorations": 100,
        "parole_population_start": 23859,
        "parole_population_end": 22901,
        "parole_completion_rate": 0.72,
        "total_expenditures": 45782940.0,
    },
    2017: {"parole_certificates": 6577, "total_expenditures": 16846903.0},
    2018: {
        "parole_certificates": 7703,
        "commutations": 1,
        "total_expenditures": 17512005.0,
    },
    2019: {
        "guidelines_decisions_total": 15535,
        "parole_completion_rate": 0.70,
        "total_expenditures": 17677229.0,
    },
    2020: {
        "commutations": 918,
        "parole_revocations": 2199,
        "parole_population_start": 20719,
        "parole_population_end": 21069,
        "total_expenditures": 16954797.0,
    },
    2021: {"parole_revocations": 2373, "total_expenditures": 17203983.0},  # FY25 chart
    2022: {
        "total_releases": 6245,
        "parole_revocations": 1825,  # restated by the FY2025 chart
        "pardons_granted": 412,
        "rights_restorations": 133,
        "clemency_votes": 51243,
        "total_expenditures": 17713201.0,
    },
    2023: {
        "parole_certificates": 3897,
        "parole_revocations": 1552,  # restated by the FY2025 chart
        "rights_restorations": 95,  # 469 (Pardon Grants) + 95 = published 564
        "parole_completion_rate": 0.70,
        "total_expenditures": 19049254.35,
    },
    2024: {
        "life_cases_granted": 93,
        "life_cases_denied": 1953,
        "life_decisions_total": 2046,
        "parole_revocations": 1437,  # restated by the FY2025 chart
        "pardons_granted": 346,
        "rights_restorations": 100,  # 346 (Pardon Grants) + 100 = published 446
        "total_expenditures": 20240569.85,
    },
    2025: {
        "total_releases": 5588,
        "parole_certificates": 4037,
        "guidelines_decisions_total": 13743,
        "parole_revocations": 1273,
        "total_discharges": 4729,
        "clemency_votes": 76261,
        "parole_population_start": 15105,
        "parole_population_end": 14568,
        "parole_completion_rate": 0.73,
        "total_expenditures": 21634700.96,
    },
}


# =============================================================================
# PDF extraction primitives
# =============================================================================

_NUM_RE = re.compile(r"^\$?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?$|^\$?\d+(?:\.\d{1,2})?$")
_DOT_RUN_RE = re.compile(r"\.{2,}")
# Note: "/" is edge punctuation (FY2006 prints "Discharge / Parole") but is
# preserved word-internally ("Granted/released" is a real FY2024+ label token).
_EDGE_PUNCT = ".,:;()\"'|•/"


def _norm_token(text: str) -> str:
    """Normalize a word token: unify dashes, lowercase, strip edge punctuation."""
    t = text.replace("–", "-").replace("—", "-").lower()
    return t.strip(_EDGE_PUNCT)


def _split_word(word: dict) -> list[dict]:
    """Split a pdfplumber word on dot-leader runs, keeping the parent bbox.

    Dot leaders glue label and value into one token in several years
    ("Commutations....0"); splitting restores separate tokens in x order.
    """
    parts = [p for p in _DOT_RUN_RE.split(word["text"]) if p not in ("", ".")]
    if not parts:
        return []
    return [
        {
            "text": p,
            "norm": _norm_token(p),
            # A trailing sentence mark means prose ("...seeking a pardon. 38,256
            # investigations..."), so the token can't be a bare one-word label.
            "bare_ok": not p.endswith((".", ",", ":", ";", "!", "?")),
            "x0": word["x0"],
            "x1": word["x1"],
            "top": word["top"],
            "bottom": word["bottom"],
        }
        for p in parts
    ]


def _page_tokens(page) -> list[dict]:
    """All normalized sub-tokens on a page, in pdfplumber's extraction order."""
    tokens: list[dict] = []
    for word in page.extract_words():
        tokens.extend(_split_word(word))
    return tokens


def _visual_lines(tokens: list[dict], tol: float = 3.0) -> list[list[dict]]:
    """Group tokens into visual lines by their top coordinate, left-to-right."""
    buckets: dict[int, list[dict]] = defaultdict(list)
    for t in tokens:
        buckets[round(t["top"] / tol)].append(t)
    return [sorted(buckets[k], key=lambda t: t["x0"]) for k in sorted(buckets)]


def _parse_number(text: str) -> float:
    return float(text.lstrip("$").replace(",", ""))


def _is_number(token: dict) -> bool:
    return bool(_NUM_RE.match(token["text"].lstrip("$")))


def _threaded_text(tokens: list[dict]) -> str:
    """Column-threaded page text for prose regexes.

    Visual lines are split into segments at horizontal gaps > 25pt (column
    gutters); segments are threaded into columns by clustering their left
    edges (15pt tolerance) and each thread's segments are joined top-to-
    bottom, so a sentence wrapped inside one column stays contiguous instead
    of interleaving with neighboring columns. Line-break hyphenation is
    repaired after joining.
    """
    segments: list[dict] = []
    for line in _visual_lines(tokens, tol=3.0):
        current: list[dict] = []
        for word in line:
            if current and word["x0"] - current[-1]["x1"] > 25:
                segments.append(
                    {"x0": current[0]["x0"], "top": current[0]["top"], "words": current}
                )
                current = []
            current.append(word)
        if current:
            segments.append(
                {"x0": current[0]["x0"], "top": current[0]["top"], "words": current}
            )

    # Cluster segment left edges into column threads (15pt tolerance).
    xs = sorted({round(s["x0"]) for s in segments})
    cluster_of: dict[int, int] = {}
    cluster_id = -1
    prev = None
    for x in xs:
        if prev is None or x - prev > 15:
            cluster_id += 1
        cluster_of[x] = cluster_id
        prev = x

    threads: dict[int, list[dict]] = defaultdict(list)
    for s in segments:
        threads[cluster_of[round(s["x0"])]].append(s)

    parts = []
    for cid in sorted(threads):
        rows = sorted(threads[cid], key=lambda s: s["top"])
        parts.append(" ".join(w["text"] for s in rows for w in s["words"]))
    text = "\n".join(parts)
    # Repair line-break hyphenation ("vio- lators" -> "violators") without
    # touching real hyphenated tokens ("Out-of-State" has no space).
    text = re.sub(r"(\w)- (?=[a-z])", r"\1", text)
    return re.sub(r"[ \t]+", " ", text)


# =============================================================================
# Stats-table extraction (label crosswalk over word geometry)
# =============================================================================

_LABELS_BY_LENGTH = sorted(TABLE_LABELS, key=len, reverse=True)


def _content_tokens(line: list[dict]) -> list[dict]:
    """Drop pure-punctuation tokens (norm == '') so labels match through
    separators like the '/' in FY2006's 'Discharge / Parole' rows."""
    return [t for t in line if t["norm"]]


def _match_line_labels(line: list[dict]) -> list[tuple[str, str, float]]:
    """Crosswalk hits on one visual line: (canonical, label, value or NaN).

    Longest label first with token-span consumption; the value must be the
    immediately-following numeric token (prose mentions of a label are
    followed by words, not numbers, so they never match). A multi-token label
    with no following token at all is reported with value NaN so the caller
    can attempt the vertical-band fallback (FY2025 offsets its big-number
    values ~5pt above the label line).
    """
    line = _content_tokens(line)
    norms = [t["norm"] for t in line]
    used = [False] * len(line)
    hits: list[tuple[str, str, float]] = []
    for label in _LABELS_BY_LENGTH:
        n = len(label)
        for i in range(0, len(norms) - n + 1):
            if any(used[i : i + n]) or tuple(norms[i : i + n]) != label:
                continue
            if label in BARE_LABELS and not line[i]["bare_ok"]:
                continue
            j = i + n
            if j < len(line) and _is_number(line[j]):
                for k in range(i, i + n):
                    used[k] = True
                used[j] = True
                hits.append(
                    (
                        TABLE_LABELS[label],
                        " ".join(label),
                        _parse_number(line[j]["text"]),
                    )
                )
            elif j >= len(line) and len(label) > 1:
                # Line-final multi-token label: candidate for band fallback.
                for k in range(i, i + n):
                    used[k] = True
                hits.append((TABLE_LABELS[label], " ".join(label), float("nan")))
    return hits


def _band_value(
    tokens: list[dict], line: list[dict], label: tuple[str, ...]
) -> float | None:
    """Find a numeric token right of a line-final label with vertical overlap.

    FY2025 renders stats values in a larger font whose baseline sits above
    the label's line cluster; the nearest number to the right that vertically
    overlaps the label band is its value.
    """
    line = _content_tokens(line)
    n = len(label)
    norms = [t["norm"] for t in line]
    for i in range(len(norms) - n, -1, -1):
        if tuple(norms[i : i + n]) == label:
            end = line[i + n - 1]
            top, bottom, x1 = end["top"], end["bottom"], end["x1"]
            candidates = [
                t
                for t in tokens
                if _is_number(t)
                and t["x0"] > x1 - 2
                and t["x0"] - x1 < 300
                and min(bottom, t["bottom"]) - max(top, t["top"]) > 2
            ]
            if candidates:
                best = min(candidates, key=lambda t: t["x0"])
                return _parse_number(best["text"])
    return None


def _extract_table_metrics(
    pages_tokens: list[list[dict]],
) -> tuple[dict[str, float], list[tuple[str, str]]]:
    """Extract every crosswalk metric from a report's stats pages.

    A page qualifies as a stats page when it yields >=3 distinct canonical
    hits; bare one-token labels only count on pages that already carry >=2
    multi-token hits. Duplicate hits for one canonical must agree (equal
    values are merged; divergent values raise).
    """
    values: dict[str, float] = {}
    provenance: dict[str, tuple[str, int]] = {}
    labels_seen: list[tuple[str, str]] = []

    for pno, tokens in enumerate(pages_tokens, 1):
        lines = _visual_lines(tokens)
        page_hits: list[tuple[str, str, float]] = []
        for line in lines:
            for canonical, label, value in _match_line_labels(line):
                if value != value:  # NaN -> band fallback
                    band = _band_value(tokens, line, tuple(label.split(" ")))
                    if band is None:
                        continue
                    value = band
                page_hits.append((canonical, label, value))

        multi = {c for c, lab, _ in page_hits if len(lab.split(" ")) > 1}
        if len(multi) < 2:
            page_hits = [h for h in page_hits if len(h[1].split(" ")) > 1]
        if len({c for c, _, _ in page_hits}) < 3:
            continue

        # On a qualified stats page, bare labels whose value sits on an offset
        # baseline (FY2025 big-number stats) get the band fallback too — a
        # clean line-final bare token ("Commutations") with the nearest
        # number to its right; the release-sum identity verifies the pairing.
        if len(multi) >= 3:
            hit_canonicals = {c for c, _, _ in page_hits}
            for label in BAND_BARE_LABELS:
                canonical = TABLE_LABELS[label]
                if canonical in hit_canonicals or canonical in values:
                    continue
                for line in (_content_tokens(li) for li in lines):
                    if line and line[-1]["norm"] == label[0] and line[-1]["bare_ok"]:
                        band = _band_value(tokens, line, label)
                        if band is not None:
                            page_hits.append((canonical, " ".join(label), band))
                            break

        for canonical, label, value in page_hits:
            if canonical in values and values[canonical] != value:
                raise ValueError(
                    f"p{pno}: divergent duplicate for {canonical}: "
                    f"{values[canonical]} (from {provenance[canonical]}) vs "
                    f"{value} (label {label!r})"
                )
            values[canonical] = value
            provenance[canonical] = (label, pno)
            labels_seen.append((label, canonical))

    # Wrapped two-line labels (FY2018/19 + FY2023/24 restoration-of-rights).
    for first, second, canonical in WRAPPED_LABELS:
        if canonical not in values:
            _extract_wrapped_label(
                pages_tokens, first, second, canonical, values, provenance, labels_seen
            )

    for canonical, (label, pno) in sorted(provenance.items()):
        logger.info(
            "    table: %-32s = %12g  (%r, p%d)",
            canonical,
            values[canonical],
            label,
            pno,
        )
    return values, labels_seen


def _extract_wrapped_label(
    pages_tokens: list[list[dict]],
    first: tuple[str, ...],
    second: tuple[str, ...],
    canonical: str,
    values: dict[str, float],
    provenance: dict[str, tuple[str, int]],
    labels_seen: list[tuple[str, str]],
) -> None:
    """Match a label wrapped across two physical lines (+ its value).

    The second-line tokens must be immediately followed by a number, with the
    first-line tokens sitting just above and left-aligned (FY2018/FY2019 wrap
    "Restoration of Civil and Political" / "Rights Granted ....N").
    """
    for pno, tokens in enumerate(pages_tokens, 1):
        lines = [_content_tokens(li) for li in _visual_lines(tokens)]
        firsts = []
        for line in lines:
            norms = [t["norm"] for t in line]
            for i in range(len(norms) - len(first) + 1):
                if tuple(norms[i : i + len(first)]) == first:
                    firsts.append(line[i])
        if not firsts:
            continue
        for line in lines:
            norms = [t["norm"] for t in line]
            for i in range(len(norms) - len(second) + 1):
                if tuple(norms[i : i + len(second)]) != second:
                    continue
                j = i + len(second)
                if j >= len(line) or not _is_number(line[j]):
                    continue
                anchor = line[i]
                if any(
                    0 < anchor["top"] - f["top"] < 30
                    and abs(anchor["x0"] - f["x0"]) < 60
                    for f in firsts
                ):
                    values[canonical] = _parse_number(line[j]["text"])
                    provenance[canonical] = (" ".join(first + second), pno)
                    labels_seen.append((" ".join(first + second), canonical))
                    return


# =============================================================================
# Prose extraction
# =============================================================================


def _extract_prose_metrics(
    year: int, texts: list[str]
) -> tuple[dict[str, float], list[tuple[str, str]]]:
    """Run the year-scoped prose regexes; divergent multi-matches raise.

    ``texts`` are alternative text surfaces tried in order per pattern —
    column-threaded text first (wrapped sentences stay contiguous), then
    plain visual-line text (big-number tiles like FY2025's "CLEMENCY VOTES
    76,261" span a column gutter that threading severs).
    """
    values: dict[str, float] = {}
    labels_seen: list[tuple[str, str]] = []
    for metric, years, patterns in PROSE_PATTERNS:
        if year not in years:
            continue
        for pattern in patterns:
            matches = next(
                (m for text in texts if (m := re.findall(pattern, text))), []
            )
            if not matches:
                continue
            if metric == "_population_pair":
                pairs = {(m[0], m[1]) for m in matches}
                if len(pairs) > 1:
                    raise ValueError(f"FY{year}: divergent population pairs {pairs}")
                start, end = pairs.pop()
                values["parole_population_start"] = _parse_number(start)
                values["parole_population_end"] = _parse_number(end)
                labels_seen.append((f"PROSE:{pattern}", "parole_population_start"))
                labels_seen.append((f"PROSE:{pattern}", "parole_population_end"))
                logger.info("    prose: population %s -> %s", start, end)
                break
            found = {m if isinstance(m, str) else m[0] for m in matches}
            if len(found) > 1:
                raise ValueError(
                    f"FY{year}: divergent prose matches for {metric}: {found} "
                    f"(pattern {pattern!r})"
                )
            raw = found.pop()
            value = _parse_number(raw)
            if metric == "parole_completion_rate":
                value = value / 100.0  # whole-number percent -> [0,1] proportion
            values[metric] = value
            labels_seen.append((f"PROSE:{pattern}", metric))
            logger.info("    prose: %-32s = %12g  (%r)", metric, value, pattern)
            break
    return values, labels_seen


def _extract_expenditures(pages_tokens: list[list[dict]]) -> float | None:
    """Extract the agency-expenditures total from visual-line text.

    Patterns are tried in order; the first pattern with any match wins, and
    divergent multi-matches raise. The bare "Total:" fallback (FY2016) only
    applies on pages that carry an EXPENDITURES heading; the vertical-band
    fallback handles FY2018's offset-baseline value.
    """
    pages_lines = [
        [(line, " ".join(t["text"] for t in line)) for line in _visual_lines(tokens)]
        for tokens in pages_tokens
    ]
    for pattern in EXPENDITURE_LINE_PATTERNS:
        found: set[str] = set()
        for lines in pages_lines:
            page_text = " ".join(text for _, text in lines)
            if "^total:" in pattern and "EXPENDITURES" not in page_text.upper():
                continue
            for _, text in lines:
                m = re.search(pattern, text)
                if m:
                    found.add(m.group(1))
        if not found:
            continue
        if len(found) > 1:
            raise ValueError(f"Divergent expenditure totals matched: {found}")
        value = _parse_number(found.pop())
        logger.info(
            "    line:  %-32s = %12.2f  (%r)", "total_expenditures", value, pattern
        )
        return value

    return _band_after_token_pair(
        pages_tokens,
        ("total", "expenditures"),
        _MILLIONS_TOKEN_RE,
        "total_expenditures",
    )


def _band_after_token_pair(
    pages_tokens: list[list[dict]],
    pair: tuple[str, str],
    value_re: re.Pattern,
    metric: str,
) -> float | None:
    # Band fallback: anchor on a consecutive token pair and take the nearest
    # matching numeric token to the right with vertical overlap — several
    # reports render a big-number value on an offset baseline that falls
    # outside the label's visual line (FY2018/FY2019 expenditures, the
    # FY2025 "CLEMENCY VOTES 76,261" tile).
    for tokens in pages_tokens:
        anchors = [
            t
            for prev, t in zip(tokens, tokens[1:])
            if t["norm"] == pair[1] and prev["norm"] == pair[0]
        ]
        for anchor in anchors:
            candidates = [
                t
                for t in tokens
                if value_re.match(t["text"])
                and t["x0"] > anchor["x1"] - 2
                and t["x0"] - anchor["x1"] < 300
                and min(anchor["bottom"], t["bottom"]) - max(anchor["top"], t["top"])
                > 2
            ]
            if candidates:
                best = min(candidates, key=lambda t: t["x0"])
                value = _parse_number(best["text"])
                logger.info(
                    "    band:  %-32s = %12.2f  (anchor %r)", metric, value, pair
                )
                return value
    return None


# =============================================================================
# Per-year verification
# =============================================================================


def _check_sum(
    year: int, values: dict, parts: list[str], total_key: str, note: str
) -> None:
    """Assert a component-sum identity when every part and the total exist."""
    if total_key not in values or any(p not in values for p in parts):
        return
    total = values[total_key]
    s = sum(values[p] for p in parts)
    if s != total:
        raise ValueError(
            f"FY{year}: {note} components sum to {s:,.0f} but "
            f"{total_key} = {total:,.0f}"
        )


def _verify_year(year: int, values: dict[str, float]) -> None:
    """Internal-sum identities + pinned anchors for one report year."""
    # Release actions == published total (era-specific component sets).
    if year <= 2013:
        _check_sum(
            year,
            values,
            [
                "parole_releases",
                "supervised_reprieves",
                "conditional_transfers",
                "commutations",
                "_remission",
                "_other_releases",
            ],
            "total_releases",
            "Era 1/2 release-action",
        )
    else:
        _check_sum(
            year,
            values,
            [
                "parole_certificates",
                "_oos_parole_orders",
                "conditional_transfers",
                "_oos_conditional_transfers",
                "supervised_reprieves",
                "_oos_supervised_reprieves",
                "commutations",
                "_medical_reprieves",
                "_oos_ice_orders",
            ],
            "total_releases",
            "FY2014+/Era 3 release-action",
        )
    # Mandatory presence of the release-sum inputs where the table publishes
    # the full component set (all parsed/transcribed table years).
    if year not in (2009,):
        if "total_releases" not in values:
            raise ValueError(f"FY{year}: total_releases not extracted")

    _check_sum(
        year,
        values,
        ["life_cases_granted", "life_cases_denied"],
        "life_decisions_total",
        "life-decision",
    )
    # Era 1/2 discharge components (FY2013 replaces the commutation line with
    # a bare "Other" row that is not crosswalked; its total is anchor-checked).
    if year <= 2012:
        _check_sum(
            year,
            values,
            [
                "_discharge_from_parole",
                "_discharge_from_reprieve",
                "_commutation_to_discharge",
            ],
            "total_discharges",
            "discharge",
        )
    _check_sum(
        year,
        values,
        ["_pop_ga_in_ga", "_pop_oos_in_ga", "_pop_ga_oos"],
        "parole_population_end",
        "supervision-population",
    )
    _check_sum(
        year,
        values,
        ["guidelines_decisions_initial", "_other_guidelines_decisions"],
        "guidelines_decisions_total",
        "guidelines-decision",
    )
    _check_sum(
        year,
        values,
        ["pardons_granted", "rights_restorations"],
        "_total_pardons_restorations",
        "pardons+restorations",
    )

    for metric, expected in ANCHORS.get(year, {}).items():
        got = values.get(metric)
        if got is None or abs(got - expected) > 1e-9:
            raise ValueError(
                f"FY{year}: anchor mismatch for {metric}: extracted "
                f"{got!r}, expected {expected!r}"
            )


# =============================================================================
# Per-file pipeline
# =============================================================================


def _era_label(year: int) -> str:
    if year in TRANSCRIBED_VALUES:
        return (
            "era1_image_table_transcribed"
            if year != 2002
            else "era1_scanned_transcribed"
        )
    if year <= 2009:
        return "era1_classic_table" if year != 2009 else "era1_prose_only"
    if year <= 2014:
        return "era2_magazine_table"
    return "era3_infographic"


def parse_report(
    path: Path, year: int, manifest: TransformManifest
) -> dict[str, float]:
    """Extract, cross-verify, and return all metric values for one report."""
    logger.info("FY%d — %s", year, path.name)
    values: dict[str, float] = {}
    labels_seen: list[tuple[str, str]] = []

    if year in TRANSCRIBED_VALUES:
        values.update(TRANSCRIBED_VALUES[year])
        labels_seen.extend(
            (f"TRANSCRIBED:{metric}", metric) for metric in TRANSCRIBED_VALUES[year]
        )
        logger.info(
            "    %d values from the authoring-time transcription table "
            "(image-only source pages; see TRANSCRIBED_VALUES provenance)",
            len(TRANSCRIBED_VALUES[year]),
        )

    with pdfplumber.open(path) as pdf:
        # One geometry pass per page; every extraction surface (stats-table
        # matching, threaded prose, visual-line text, band fallbacks) reuses
        # these token lists instead of re-reading the PDF.
        pages_tokens = [_page_tokens(page) for page in pdf.pages]

    if year not in TRANSCRIBED_VALUES:
        table_values, table_labels = _extract_table_metrics(pages_tokens)
        for metric, value in table_values.items():
            _merge_value(year, values, metric, value, "table")
        labels_seen.extend(table_labels)
    # FY2002/FY2007/FY2008 have image tables, but FY2007/FY2008 keep
    # text-extractable prose and expenditure pages, so the prose and
    # expenditure passes still run for every year.
    threaded_text = "\n".join(_threaded_text(tokens) for tokens in pages_tokens)
    lines_text = "\n".join(
        " ".join(t["text"] for t in line)
        for tokens in pages_tokens
        for line in _visual_lines(tokens)
    )

    prose_values, prose_labels = _extract_prose_metrics(
        year, [threaded_text, lines_text]
    )
    for metric, value in prose_values.items():
        _merge_value(year, values, metric, value, "prose")
    labels_seen.extend(prose_labels)

    if year in EXPENDITURE_YEARS:
        expenditures = _extract_expenditures(pages_tokens)
        if expenditures is not None:
            _merge_value(year, values, "total_expenditures", expenditures, "line")
            labels_seen.append(
                ("LINE:total_expenditures_pattern", "total_expenditures")
            )

    # FY2025 publishes clemency votes only as a big-number tile whose value
    # sits on an offset baseline — band-match it when prose found nothing.
    if year in EXPECTED_COVERAGE["clemency_votes"] and "clemency_votes" not in values:
        votes = _band_after_token_pair(
            pages_tokens,
            ("clemency", "votes"),
            re.compile(r"^\d{1,3}(?:,\d{3})+$"),
            "clemency_votes",
        )
        if votes is not None:
            _merge_value(year, values, "clemency_votes", votes, "band")
            labels_seen.append(("BAND:clemency votes tile", "clemency_votes"))

    _verify_year(year, values)

    # Manifest accounting: one statewide observation row per fiscal year; the
    # "columns" are the canonical metrics this report published.
    manifest.record_file(
        path,
        year,
        _era_label(year),
        1,
        sorted(m for m in values if not m.startswith("_")),
    )
    manifest.record_bronze(year, 1)
    if labels_seen:
        manifest.record_categorical(
            column="metric_source_label",
            map_dict=LABEL_CROSSWALK_MAP
            | {lab: met for lab, met in labels_seen if lab not in LABEL_CROSSWALK_MAP},
            bronze_series=pl.Series([lab for lab, _ in labels_seen]),
            gold_series=pl.Series([met for _, met in labels_seen]),
        )
    return values


def _merge_value(
    year: int, values: dict[str, float], metric: str, value: float, source: str
) -> None:
    """Merge one extracted value; a conflicting duplicate raises.

    Equal duplicates are expected — Era 3 prose restates several table values
    (e.g. discharges) and acts as a free cross-check.
    """
    if metric in values and values[metric] != value:
        raise ValueError(
            f"FY{year}: {source} value for {metric} ({value}) conflicts with "
            f"previously extracted {values[metric]}"
        )
    values[metric] = value


# =============================================================================
# Cross-year verification
# =============================================================================


def _verify_cross_year(rows: dict[int, dict[str, float]]) -> None:
    """DCS-era population chain: each July-1 start == prior June-30 end."""
    for year in sorted(_ERA3_YEARS - {2016}):
        prev = rows.get(year - 1)
        cur = rows.get(year)
        if not prev or not cur:
            continue
        start, prev_end = (
            cur.get("parole_population_start"),
            prev.get("parole_population_end"),
        )
        if start is not None and prev_end is not None and start != prev_end:
            raise ValueError(
                f"FY{year}: population chain broken — July-1 start {start:,.0f} "
                f"!= FY{year - 1} June-30 end {prev_end:,.0f}"
            )
    logger.info("Cross-year QA passed: DCS-era population chain FY2017-FY2025 intact")


def _verify_coverage(rows: dict[int, dict[str, float]]) -> None:
    """Assert the exact expected non-NULL pattern for every served metric."""
    problems = []
    for metric, expected_years in EXPECTED_COVERAGE.items():
        got_years = {y for y, vals in rows.items() if vals.get(metric) is not None}
        missing = expected_years - got_years
        extra = got_years - expected_years
        if missing:
            problems.append(
                f"{metric}: expected but not extracted for {sorted(missing)}"
            )
        if extra:
            problems.append(f"{metric}: unexpectedly extracted for {sorted(extra)}")
    if problems:
        raise ValueError("Coverage matrix violated:\n  " + "\n  ".join(problems))
    logger.info(
        "Coverage matrix verified: %d metrics x %d years match the expected"
        " NULL pattern",
        len(EXPECTED_COVERAGE),
        len(rows),
    )


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for parole_decisions."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    rows: dict[int, dict[str, float]] = {}
    for path in sorted(BRONZE_DIR.glob("annual_report_fy*.pdf")):
        if path.name in SKIP_FILES:
            # FY2016's 2-up spread duplicate — provenance only, never ingested
            # (identical content to annual_report_fy2016.pdf).
            logger.info(
                "Skipping %s (2-up duplicate kept for provenance only)", path.name
            )
            continue
        year = int(re.search(r"fy(\d{4})", path.name).group(1))
        rows[year] = parse_report(path, year, manifest)

    if sorted(rows) != ALL_YEARS:
        raise ValueError(
            f"Expected report years {ALL_YEARS}, got {sorted(rows)} — bronze "
            "inventory changed; re-run /bronze-data-structure first"
        )
    _verify_cross_year(rows)
    _verify_coverage(rows)

    # Build the one-row-per-fiscal-year statewide frame.
    frame_rows = []
    for year in ALL_YEARS:
        row: dict = {"year": year, "supervision_era": _supervision_era(year)}
        for metric in METRIC_COLUMNS:
            value = rows[year].get(metric)
            if metric in ("parole_completion_rate", "total_expenditures"):
                row[metric] = float(value) if value is not None else None
            else:
                row[metric] = int(value) if value is not None else None
        row["detail_level"] = "state"
        frame_rows.append(row)
    result = pl.DataFrame(frame_rows)

    manifest.record_categorical(
        column="supervision_era",
        map_dict=SUPERVISION_ERA_MAP,
        bronze_series=result["supervision_era"],
        gold_series=result["supervision_era"],
    )

    # Defensive year floor (all fiscal years here are 2001-2025 already).
    pre_floor = result.filter(pl.col("year") < YEAR_FLOOR)
    if pre_floor.height:
        for y in pre_floor["year"].to_list():
            manifest.record_filtered(y, 1, "pre_2000_year_floor")
        logger.info("Year floor %d: dropped %d rows", YEAR_FLOOR, pre_floor.height)
        result = result.filter(pl.col("year") >= YEAR_FLOOR)

    # Harmonize to the gold schema (single source, one-frame pass).
    combined = pl.concat(harmonize_columns([result], STANDARD_COLUMNS, TARGET_TYPES))

    # Collision guard BEFORE dedup: duplicate years would mean a bronze
    # inventory bug and must raise, never be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: one report per fiscal year makes collisions impossible by
    # construction; sort_col documents the safety net (prefer the row with the
    # larger non-null release total) should a refresh add an overlapping file.
    combined = deduplicate_by_levels(
        combined, {"state": ["year"]}, sort_col="total_releases"
    )

    # No geography nulling (no geography columns exist on this statewide-only
    # topic) and no §4b masks (no impossible values — every figure is
    # sum-verified and/or anchor-verified; see the module docstring).
    spike = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike.status == "warning":
        # Expected: metric availability is era-scoped by design (documented
        # per column in the contract), so per-year NULL patterns differ.
        logger.warning(
            "NULL-rate spikes (expected, era-scoped coverage): %s", spike.details
        )
    validate_output(
        combined, required_non_null=["year", "supervision_era", "detail_level"]
    )

    # Manifest stats on the FINAL frame, then export.
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(
        combined,
        GOLD_DIR,
        STANDARD_COLUMNS,
        detail_level_files=COUNTY_DETAIL_LEVEL_FILES,
    )
    manifest.write(GOLD_DIR)

    _emit_contract(
        year_range=(int(combined["year"].min()), int(combined["year"].max()))
    )

    summary = manifest.tracker.summary()
    logger.info(
        "Done. Bronze rows: %s; gold rows: %s; years: %s",
        f"{summary['total_bronze']:,}",
        f"{summary['total_gold']:,}",
        summary["years_processed"],
    )

    # ALWAYS LAST: validate the gold just written against the contract just
    # emitted. Raises GoldValidationError -> non-zero exit.
    run_topic_validation(GOLD_DIR)


# =============================================================================
# Contract
# =============================================================================


def _emit_contract(year_range: tuple[int, int]) -> None:
    """Emit the ODCS contract via ``write_data_dictionary``.

    Column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level``.
    """
    not_published = (
        "NULL means the figure was not published in that fiscal year's annual report."
    )
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        title="Parole Board Decisions and Clemency Actions",
        summary=(
            "Statewide fiscal-year totals of Georgia Parole Board decisions — "
            "prison releases by parole, guidelines and life-sentence decisions, "
            "revocations, pardons, and parole outcomes — FY2001 onward."
        ),
        description=(
            "Executive-clemency and parole decision metrics of the Georgia State "
            "Board of Pardons and Paroles, statewide by state fiscal year (July 1 "
            "- June 30; the year value is the fiscal year's END year), extracted "
            "from the Board's narrative annual-report PDFs for FY2001-FY2025. "
            "Covers prison releases by Board action (total and by release type), "
            "parole-guidelines and life-sentence case decisions, parole "
            "revocations, discharges, pardons and restorations of civil and "
            "political rights, clemency votes, the parole-supervision population "
            "and successful-completion rate, and agency expenditures. Metric "
            "availability varies with the reports' changing designs — a metric "
            "is NULL in years whose report did not publish it (this source has "
            "no suppression). House Bill 310 moved parole field supervision from "
            "the Board to the Department of Community Supervision effective "
            "FY2016; the supervision_era column flags the break so supervision-"
            "series metrics are never pooled across it. FY2015 was never "
            "published by the agency and is a true gap in the series."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2025,
                "description": (
                    "State fiscal year END year (Georgia FY runs July 1 - June "
                    "30, so 2025 = 2024-07-01 through 2025-06-30). FY2015 is "
                    "absent because the agency never published an FY2015 annual "
                    "report — the gap is real, not a processing artifact."
                ),
            },
            {
                "name": "supervision_era",
                "type": "string",
                "nullable": False,
                "validValues": ["board", "dcs"],
                "example": "dcs",
                "short_description": (
                    "Who supervised parolees: the Parole Board itself (through "
                    "FY2014) or the Dept. of Community Supervision (FY2016+)."
                ),
                "description": (
                    "Methodological-era flag for the 2015 House Bill 310 break: "
                    "'board' (FY2001-FY2014) years, when the Board's own Field "
                    "Operations division supervised parolees; 'dcs' (FY2016-"
                    "FY2025) years, after supervision moved to the Department of "
                    "Community Supervision. Supervision-series metrics "
                    "(parole_population_start/_end, parole_completion_rate, "
                    "parole_revocations, total_expenditures) are not comparable "
                    "across the two eras and must never be pooled or charted as "
                    "one continuous series across FY2015. The clemency-decision "
                    "series (releases, guidelines and life decisions, pardons) "
                    "is the continuous one."
                ),
            },
            {
                "name": "total_releases",
                "type": "int64",
                "unit": "count",
                "key_metric": True,
                "example": 5588,
                "null_meaning": not_published,
                "short_description": (
                    "Offenders released from prison by Parole Board action "
                    "during the fiscal year (all release types combined)."
                ),
                "description": (
                    "Total offenders released from prison to parole-system "
                    "supervision by Board clemency action during the fiscal "
                    "year, summing all release types (parole certificates, "
                    "out-of-state parole orders, supervised reprieves, "
                    "conditional transfers, commutations, medical reprieves, "
                    "ICE orders). Published as 'TOTAL RELEASES' (FY2001-FY2013), "
                    "in prose as offenders 'released to parole supervision by "
                    "Board action' (FY2009), and as 'Total Prison Releases by "
                    "Parole' (FY2014-FY2025) — the published component "
                    "breakdowns sum exactly to this total in every year that "
                    "prints them, confirming the labels describe the same "
                    "measure. Present in all 24 published years; the only "
                    "metric with full coverage."
                ),
            },
            {
                "name": "parole_releases",
                "type": "int64",
                "unit": "count",
                "example": 10828,
                "null_meaning": not_published,
                "description": (
                    "Offenders released via the 'Parole' release action — the "
                    "largest release type in the FY2001-FY2013 clemency-action "
                    "tables. NULL from FY2014 onward, when the reports replaced "
                    "this line with separate 'Parole Certificates' and "
                    "'Out-of-State Parole Orders' lines (see "
                    "parole_certificates); the two generations are related but "
                    "not provably identical, so they are kept as separate "
                    "columns rather than pooled. Also NULL for FY2009 (that "
                    "year's slim report published no release-type breakdown)."
                ),
            },
            {
                "name": "parole_certificates",
                "type": "int64",
                "unit": "count",
                "example": 4037,
                "null_meaning": not_published,
                "description": (
                    "Parole certificates issued ('Parole Certificates' line, "
                    "FY2014-FY2025) — in-state parole releases; out-of-state "
                    "parole orders are published separately and are not "
                    "included. NULL before FY2014, when the tables printed a "
                    "single 'Parole' line instead (see parole_releases)."
                ),
            },
            {
                "name": "supervised_reprieves",
                "type": "int64",
                "unit": "count",
                "example": 409,
                "null_meaning": not_published,
                "description": (
                    "Offenders released on supervised reprieve during the "
                    "fiscal year. FY2001-FY2013: the single 'Supervised "
                    "Reprieve' release-action line; FY2014-FY2025: the "
                    "'Supervised Reprieves' line, which excludes the separately "
                    "published out-of-state supervised reprieves. NULL FY2009."
                ),
            },
            {
                "name": "conditional_transfers",
                "type": "int64",
                "unit": "count",
                "example": 710,
                "null_meaning": not_published,
                "description": (
                    "Offenders released by conditional transfer during the "
                    "fiscal year. FY2001-FY2013: the single 'Conditional "
                    "Transfer' line; FY2014-FY2025: the 'Conditional Transfers' "
                    "line, which excludes the separately published out-of-state "
                    "conditional transfers. NULL FY2009."
                ),
            },
            {
                "name": "commutations",
                "type": "int64",
                "unit": "count",
                "example": 0,
                "null_meaning": not_published,
                "description": (
                    "Offenders RELEASED from prison by commutation during the "
                    "fiscal year (the commutation release action — distinct "
                    "from the 'Commutation Reducing Sentence' board action, "
                    "which is not served). Genuinely volatile: near zero in "
                    "most early years, then e.g. 1,357 (FY2013), 3,119 "
                    "(FY2014), 2,850 (FY2016), 918 (FY2020) as published — "
                    "reflecting real policy waves, not extraction error (values "
                    "are verified against the published release-total sum). "
                    "NULL FY2009."
                ),
            },
            {
                "name": "guidelines_decisions_total",
                "type": "int64",
                "unit": "count",
                "example": 13743,
                "null_meaning": not_published,
                "description": (
                    "Total parole-guidelines decisions rendered during the "
                    "fiscal year: 'TOTAL DECISIONS UNDER GUIDELINES' "
                    "(FY2001-FY2007) and 'Total Guidelines Decisions' "
                    "(FY2016-FY2025, which the FY2016-FY2017 reports break "
                    "into initial + other decisions). NULL FY2008-FY2014, when "
                    "the reports published only INITIAL guidelines decisions "
                    "(see guidelines_decisions_initial) — the two definitions "
                    "are kept in separate columns, never pooled."
                ),
            },
            {
                "name": "guidelines_decisions_initial",
                "type": "int64",
                "unit": "count",
                "example": 6888,
                "null_meaning": not_published,
                "description": (
                    "INITIAL parole-guidelines decisions ('INITIAL DECISIONS "
                    "UNDER GUIDELINES', FY2008 and FY2010-FY2014; 'Initial "
                    "(Decisions Under )Guidelines (Decisions)', FY2016-FY2017) "
                    "— first-time guideline decisions, excluding "
                    "reconsiderations and other subsequent decisions. In "
                    "FY2016-FY2017 initial + other guidelines decisions sum "
                    "exactly to guidelines_decisions_total. NULL elsewhere."
                ),
            },
            {
                "name": "life_cases_granted",
                "type": "int64",
                "unit": "count",
                "example": 123,
                "null_meaning": not_published,
                "description": (
                    "Life-sentence parole cases GRANTED during the fiscal year "
                    "('Grant Parole to Life Cases' FY2001-FY2013; 'Life "
                    "Sentence(d) Cases Granted (Parole)' FY2014-FY2023; 'Life "
                    "Sentence Cases Granted/released' FY2024-FY2025, which "
                    "counts grants including those released). Granted + denied "
                    "equals life_decisions_total in every published year. "
                    "NULL FY2009."
                ),
            },
            {
                "name": "life_cases_denied",
                "type": "int64",
                "unit": "count",
                "example": 2154,
                "null_meaning": not_published,
                "description": (
                    "Life-sentence parole cases DENIED during the fiscal year "
                    "('Deny Parole to Life Cases' / 'Life Sentence(d) Cases "
                    "Denied (Parole)'). NULL FY2009."
                ),
            },
            {
                "name": "life_decisions_total",
                "type": "int64",
                "unit": "count",
                "example": 2277,
                "null_meaning": not_published,
                "description": (
                    "Total life-sentence parole case decisions (grants + "
                    "denials) during the fiscal year. Equals "
                    "life_cases_granted + life_cases_denied in every published "
                    "year (enforced as a quality check). NULL FY2009."
                ),
            },
            {
                "name": "parole_revocations",
                "type": "int64",
                "unit": "count",
                "example": 1273,
                "null_meaning": not_published,
                "description": (
                    "Parole violators whose parole the Board revoked during "
                    "the fiscal year, returning them to prison. 'TOTAL PAROLE "
                    "REVOCATIONS' table line FY2001-FY2013; prose 'the Board "
                    "revoked N parole violators' FY2014-FY2025 (the FY2025 "
                    "report's FY21-FY25 bar chart restates the recent series, "
                    "verifying the prose values). A supervision-series metric: "
                    "before FY2016 violations were detected by the Board's own "
                    "field officers, from FY2016 by DCS officers reporting to "
                    "the Board — compare across supervision_era with caution. "
                    "The technical-vs-new-offense split is not consistently "
                    "published and is not served. NULL FY2009."
                ),
            },
            {
                "name": "total_discharges",
                "type": "int64",
                "unit": "count",
                "example": 4729,
                "null_meaning": not_published,
                "description": (
                    "Offenders discharged from parole-system supervision during "
                    "the fiscal year. FY2001-FY2013 'TOTAL DISCHARGES' includes "
                    "discharges from parole, from supervised reprieve, and "
                    "commutation-to-discharge; FY2014-FY2025 'Total Discharges "
                    "from Parole' is the parole-discharge count as published — "
                    "the pre/post-2014 definitions differ slightly, and the "
                    "FY2016+ years sit in the DCS supervision era. NULL FY2009."
                ),
            },
            {
                "name": "pardons_granted",
                "type": "int64",
                "unit": "count",
                "example": 346,
                "null_meaning": not_published,
                "description": (
                    "Pardons granted by the Board during the fiscal year "
                    "('Pardon' board-action line FY2001-FY2013; 'Pardons "
                    "Granted (all types)' FY2014; 'Pardon Grants' FY2016-"
                    "FY2024). Includes pardons granted both with and without "
                    "firearm-rights restoration. NULL FY2009 and FY2025 (the "
                    "FY2025 report publishes only the with/without-firearms "
                    "split as separate figures, never a single total, and "
                    "components are not summed at transform time)."
                ),
            },
            {
                "name": "rights_restorations",
                "type": "int64",
                "unit": "count",
                "example": 133,
                "null_meaning": not_published,
                "description": (
                    "Restorations of civil and political rights granted during "
                    "the fiscal year ('Restoration of Rights' FY2001-FY2014; "
                    "'Restoration of (Civil and Political )Rights Granted' "
                    "FY2016-FY2024, wrapped across two lines in some years). "
                    "NULL FY2009 and FY2025 — the FY2025 report publishes only "
                    "a with/without-firearms split of restorations rather than "
                    "a single total, and components are not summed at "
                    "transform time."
                ),
            },
            {
                "name": "clemency_votes",
                "type": "int64",
                "unit": "count",
                "example": 76261,
                "null_meaning": not_published,
                "description": (
                    "Individual clemency votes cast by the five Board members "
                    "during the fiscal year (every Board decision is a "
                    "majority of individual member votes). Published "
                    "FY2009-FY2014 and FY2019-FY2025; NULL FY2001-FY2008 and "
                    "FY2016-FY2018."
                ),
            },
            {
                "name": "parole_population_start",
                "type": "int64",
                "unit": "count",
                "example": 15105,
                "null_meaning": (
                    "NULL for all fiscal years before 2016: the pre-HB310 "
                    "reports never published a July-1 figure on the same basis "
                    "as their June-30 population table."
                ),
                "description": (
                    "Offenders on parole under community supervision at the "
                    "START of the fiscal year (July 1), as published in the "
                    "DCS-era reports (FY2016-FY2025 only; supervision_era = "
                    "'dcs'). Each year's July-1 figure equals the prior year's "
                    "June-30 figure throughout FY2017-FY2025 (verified at "
                    "transform time). Not comparable to the pre-FY2016 "
                    "parole_population_end series, which counts the Board-"
                    "supervised population on a different basis."
                ),
            },
            {
                "name": "parole_population_end",
                "type": "int64",
                "unit": "count",
                "example": 14568,
                "null_meaning": not_published,
                "description": (
                    "Offenders under parole-system supervision at the END of "
                    "the fiscal year (June 30) — a point-in-time stock, not a "
                    "flow. TWO bases, flagged by supervision_era: FY2001-FY2014 "
                    "('board') is the 'TOTAL PAROLEE POPULATION' from the "
                    "releases-under-supervision table (Georgia releases "
                    "supervised in Georgia + out-of-state releases supervised "
                    "in Georgia + Georgia releases supervised out-of-state; "
                    "components sum exactly to the total in every published "
                    "year); FY2016-FY2025 ('dcs') is the population on parole "
                    "under Department of Community Supervision community "
                    "supervision, as published in the reports' narrative. "
                    "Never chart as one continuous series across FY2015. "
                    "NULL FY2009."
                ),
            },
            {
                "name": "parole_completion_rate",
                "type": "float64",
                "unit": "proportion",
                "example": 0.73,
                "null_meaning": (
                    "NULL FY2001-FY2004: those reports quoted only an 'RDS "
                    "successful outcome rate' computed on a different formula, "
                    "which is not comparable and is not served."
                ),
                "short_description": (
                    "Share of parolees leaving supervision who successfully "
                    "completed parole (BJS methodology), as a 0-1 proportion."
                ),
                "description": (
                    "Successful parole completion rate — the share of parolees "
                    "leaving supervision during the fiscal year who completed "
                    "parole successfully, per the Bureau of Justice Statistics "
                    "methodology the Board cites, scaled from the published "
                    "whole-number percent to a 0-1 proportion (73%% -> 0.73). "
                    "Published FY2005-FY2014 and FY2016-FY2025. A supervision-"
                    "series metric: FY2016+ parolees are supervised by DCS "
                    "(supervision_era = 'dcs'), so treat the series as broken "
                    "at FY2015. NULL FY2001-FY2004 (pre-BJS-formula years)."
                ),
            },
            {
                "name": "total_expenditures",
                "type": "float64",
                "unit": "currency",
                "example": 21634700.96,
                "null_meaning": (
                    "NULL when the report published no agency-expenditures "
                    "total: FY2009 (line items only), FY2012-FY2013 (fund-"
                    "source budgets only), FY2014 (none)."
                ),
                "description": (
                    "Total agency expenditures for the fiscal year in nominal "
                    "dollars, exactly as published in the report's agency-"
                    "expenditures table (never recomputed from line items, "
                    "never inflation-adjusted). The series has a massive but "
                    "REAL discontinuity at the HB310 break: through FY2016 the "
                    "agency budget included field supervision (~$45-56M); from "
                    "FY2017 supervision costs belong to DCS and the Board's "
                    "expenditures drop to ~$17-22M. Never compare across "
                    "supervision_era. NULL FY2009, FY2012-FY2014."
                ),
            },
        ],
        source=(
            "Georgia State Board of Pardons and Paroles — Annual Reports, "
            "FY2001-FY2025 (PDF suite)"
        ),
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        suppressed_to_null=False,
        usage=(
            "Cite the Georgia State Board of Pardons and Paroles annual "
            "reports. Statewide only — this topic has no county breakdown and "
            "does not join the counties dimension. The fiscal-year value is "
            "the END year of the July-June state fiscal year. Filter or group "
            "by supervision_era before comparing supervision-series metrics "
            "(population, completion rate, revocations, expenditures) across "
            "years: House Bill 310 moved parole supervision to the Department "
            "of Community Supervision effective FY2016 and the two eras are "
            "not comparable. The clemency-decision series (total_releases, "
            "guidelines and life-sentence decisions, pardons) is continuous "
            "across the break. NULL always means 'not published that year', "
            "never zero and never suppression."
        ),
        limitations=(
            "Values are extracted from narrative annual-report PDFs whose "
            "designs change across three layout eras; every value is verified "
            "at transform time against published component-sum identities, "
            "pinned authoring-time anchors from a second extraction path, and "
            "adjacent-report restatements. FY2015 was never published by the "
            "agency and is a true gap — never interpolate across it. FY2016 "
            "exists in bronze twice; only the standard-layout report is "
            "ingested (the 2-up spread duplicate is provenance only). The "
            "FY2002 report is a scan and the FY2007/FY2008 clemency tables "
            "are page images; their values were hand-transcribed from 200-dpi "
            "renders with page-level provenance recorded in the transform, "
            "and pass the same sum checks as parsed years. Metric coverage is "
            "era-scoped: a NULL means that year's report did not publish the "
            "figure (this source has no suppression). Only fiscal years 2000 "
            "onward are served (the series starts at FY2001). Supervision-"
            "series metrics break at FY2016 (House Bill 310; see "
            "supervision_era) and expenditure totals are as published in "
            "nominal dollars with era-specific scope. The reports' cost-"
            "avoidance and cost-per-day figures are intentionally not served: "
            "their published basis changes across eras (per-day parole-vs-"
            "prison comparisons early on, an aggregate annual cost-avoidance "
            "dollar figure later) and the values appear only in chart labels "
            "and prose that text extraction cannot capture reliably — "
            "total_expenditures is the only cost metric served. Statewide "
            "grain only — no county, demographic, or offense-level detail "
            "exists in the source."
        ),
        quality_checks=[
            {
                "name": "year_floor_2000",
                "description": (
                    "Only fiscal years 2000 onward are served (the published "
                    "series starts at FY2001)."
                ),
                "dimension": "consistency",
                "query": "SELECT COUNT(*) FROM {object} WHERE year < 2000",
                "mustBe": 0,
            },
            {
                "name": "fy2015_never_present",
                "description": (
                    "The agency never published an FY2015 report; the year "
                    "must remain a gap, never interpolated."
                ),
                "dimension": "consistency",
                "query": "SELECT COUNT(*) FROM {object} WHERE year = 2015",
                "mustBe": 0,
            },
            {
                "name": "supervision_era_matches_hb310_boundary",
                "description": (
                    "The HB310 era flag is a pure function of the fiscal year: "
                    "'board' through FY2014, 'dcs' from FY2016."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(year <= 2014 AND supervision_era != 'board') OR "
                    "(year >= 2016 AND supervision_era != 'dcs')"
                ),
                "mustBe": 0,
            },
            {
                "name": "key_metric_never_null",
                "description": (
                    "total_releases is published in every report year — a NULL "
                    "would mean an extraction regression, never real "
                    "missingness."
                ),
                "dimension": "completeness",
                "query": "SELECT COUNT(*) FROM {object} WHERE total_releases IS NULL",
                "mustBe": 0,
            },
            {
                "name": "life_decision_components_sum",
                "description": (
                    "Life-sentence grants + denials must equal the published "
                    "total in every year all three are present."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE life_cases_granted IS "
                    "NOT NULL AND life_cases_denied IS NOT NULL AND "
                    "life_decisions_total IS NOT NULL AND life_cases_granted + "
                    "life_cases_denied != life_decisions_total"
                ),
                "mustBe": 0,
            },
            {
                "name": "release_components_within_total",
                "description": (
                    "Served release-type components can never exceed the "
                    "release-actions total they belong to."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE total_releases IS NOT "
                    "NULL AND COALESCE(parole_releases, 0) + "
                    "COALESCE(parole_certificates, 0) + "
                    "COALESCE(supervised_reprieves, 0) + "
                    "COALESCE(conditional_transfers, 0) + "
                    "COALESCE(commutations, 0) > total_releases"
                ),
                "mustBe": 0,
            },
            {
                "name": "board_era_release_components_reconcile",
                "description": (
                    "FY2001-FY2013 release components (parole + supervised "
                    "reprieve + conditional transfer + commutation) reconcile "
                    "to the published total within the tiny remission/other "
                    "remainder (max observed 23, FY2011)."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year <= 2013 AND "
                    "total_releases IS NOT NULL AND parole_releases IS NOT NULL "
                    "AND supervised_reprieves IS NOT NULL AND "
                    "conditional_transfers IS NOT NULL AND commutations IS NOT "
                    "NULL AND total_releases - (parole_releases + "
                    "supervised_reprieves + conditional_transfers + "
                    "commutations) NOT BETWEEN 0 AND 25"
                ),
                "mustBe": 0,
            },
            {
                "name": "parole_releases_certificates_mutually_exclusive",
                "description": (
                    "The pre-FY2014 'Parole' line and the FY2014+ 'Parole "
                    "Certificates' line never coexist in one year — they are "
                    "era-scoped generations of the release-type breakdown."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE parole_releases IS "
                    "NOT NULL AND parole_certificates IS NOT NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "guidelines_initial_within_total",
                "description": (
                    "Initial guidelines decisions can never exceed total "
                    "guidelines decisions in years publishing both (initial + "
                    "other = total is a published identity, e.g. FY2017 "
                    "8,581 + 2,143 = 10,724)."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "guidelines_decisions_initial IS NOT NULL AND "
                    "guidelines_decisions_total IS NOT NULL AND "
                    "guidelines_decisions_initial > guidelines_decisions_total"
                ),
                "mustBe": 0,
            },
            {
                "name": "population_start_dcs_era_only",
                "description": (
                    "The July-1 population start figure exists only in the "
                    "DCS-era reports (FY2016+)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "parole_population_start IS NOT NULL AND "
                    "supervision_era != 'dcs'"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
