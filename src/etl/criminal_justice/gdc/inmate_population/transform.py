"""Transform the GDC year-end population PDF into a statewide gold fact table.

Source: Georgia Dept. of Corrections "Year-End Population since 1925" — a
single one-page PDF from the Statistical Trends standing reports. The data
table prints the 1925-2024 series as FIVE side-by-side ``Year | Count``
column-blocks (a layout artifact); the lower half of the page is a bar chart
that renders the same series and is never extracted.

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Grain: year, statewide only — 2000 forward.** The printed series is NOT
  one consistent measure: 1925-1979 is NCRP data, 1980-1999 is December
  AVERAGE daily population (a flow-averaged figure), and 2000+ is a December
  31 point-in-time head count. Per the domain rule ("version methodological
  breaks, never pool across them") and the orchestrator's year floor, gold
  serves ONLY the uniform Dec-31 head-count era (year >= 2000). The full
  1925+ series is still extracted and anchor-checked for QA; pre-2000 rows
  are dropped with per-year ``record_filtered`` events (reason
  ``pre_2000_methodology_break_year_floor``) so the manifest records the
  floor explicitly.
- **No ``count_method`` categorical.** After the year-2000 floor every row is
  the same Dec-31 head count, so the categorical would be a constant — it is
  dropped and the single method (plus the floor) is documented in the
  contract description/limitations instead.
- **No geography column.** The report is statewide only — there is no county,
  facility, or demographic grain anywhere in it. ``county_fips`` is omitted
  entirely (the validator supports this: its geography-nulling and
  column-order checks skip absent columns), rather than carried as a
  100%%-NULL FK that would surface a dead county filter in the API. Rows are
  tagged ``detail_level='state'`` so export writes ``states.parquet``, and
  ``null_aggregate_geography`` is not called because there is no geography
  column to null.
- **PDF extraction un-pivots the five print blocks implicitly.** Words are
  grouped into visual lines; a line qualifies as data only when its tokens
  alternate year (``19xx``/``20xx``) and comma-formatted count — the bar
  chart's axis labels (bare years with no comma-counts, lone ``60,000``-style
  ticks) can never qualify. Each qualifying line yields one (year, count)
  pair per block, and hard assertions then require a contiguous, duplicate-
  free 1925..max_year series with pinned anchor values (1925=3,007 and
  1994=33,175 pre-filter; 2019=53,943, 2020=46,132, 2024=50,107 in gold), so
  any layout drift in a future refresh fails loudly instead of shipping a
  silently truncated series. Extraction was cross-verified against
  ``pdftotext -layout`` at authoring time (all 100 values identical).
- **No suppression, no NULLs** (``suppressed_to_null=False``): GDC publishes
  the complete series unsuppressed, and the transform hard-fails if any year
  in the span is missing. No demographic column exists, so demographic
  normalization does not apply.
- **No §4b masks.** The metric is a positive head count; every extracted
  value is regex-validated, anchor-checked, and within the plausible
  statewide range (43,875-54,463 in the served era) — nothing is impossible,
  so nothing is NULLed.
- **Quality checks (§15b).** No partition/co-null/component shapes exist
  (single metric, single grain column), so the authored checks are the
  topic's structural facts: the year-2000 floor (``no_pre_2000_years``), the
  never-NULL metric (``population_never_null``), and gap-free annual
  coverage (``year_series_contiguous``).
- **Dedup tie-break.** A single bronze PDF whose extraction is asserted
  duplicate-free makes natural-key collisions impossible by construction;
  the collision guard runs first, and ``deduplicate_by_levels(
  sort_col="year_end_inmate_population")`` remains as the documented safety
  net (prefer the row with the larger non-null count) should a future
  refresh ever add an overlapping file.
- **Scope (verbatim from the page, carried into the contract):** includes
  state prisoners in state prisons, inmate boot camps, county prisons,
  transition centers, and private prisons; EXCLUDES probationers in
  detention centers, diversion centers, or probation boot camps, and
  inmates in county jails — so this series must never be reconciled against
  the county-jail ``jail_population`` topic or supervision counts.
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

TOPIC = "inmate_population"
BRONZE_DIR = Path("data/bronze/criminal_justice/gdc/inmate_population")
GOLD_DIR = Path("data/gold/criminal_justice/inmate_population")
PDF_PATH = BRONZE_DIR / "year_end_population_since_1925.pdf"
SOURCE_URL = (
    "https://gdc.georgia.gov/organization/about-gdc/agency-activity/"
    "research-and-reports/standing-reports/statistical-trends"
)

# The printed series starts in 1925; gold serves only the Dec-31 head-count
# era (2000 forward) — see the module docstring's methodology-break note.
SERIES_START_YEAR = 1925
YEAR_FLOOR = 2000

# Pinned QA anchors. Full-series anchors guard the extraction BEFORE the year
# floor; gold anchors guard the served frame. A refresh that shifts any of
# these values (or drops a year) hard-fails instead of shipping bad data.
FULL_SERIES_ANCHORS: dict[int, int] = {1925: 3_007, 1994: 33_175}
GOLD_ANCHORS: dict[int, int] = {2019: 53_943, 2020: 46_132, 2024: 50_107}

METRIC_COLUMNS: list[str] = ["year_end_inmate_population"]

# Gold fact column order. `detail_level` is carried through dedup and export
# splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = ["year", *METRIC_COLUMNS, "detail_level"]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "year_end_inmate_population": pl.Int64,
    "detail_level": pl.Utf8,
}

NATURAL_KEYS: list[str] = ["year", "detail_level"]

# Data-line token shapes. Years are bare 4-digit tokens; counts are always
# comma-formatted thousands in this report (min printed value 2,945), which
# is exactly what disambiguates data lines from the bar chart's x-axis (bare
# years, no comma tokens). A future sub-1,000 count would fail COUNT_TOKEN_RE
# and then the contiguity assertion — a loud failure, never a silent drop.
YEAR_TOKEN_RE = re.compile(r"^(19|20)\d{2}$")
COUNT_TOKEN_RE = re.compile(r"^\d{1,3}(,\d{3})+$")


# =============================================================================
# PDF extraction
# =============================================================================


def _extract_year_count_pairs(path: Path) -> pl.DataFrame:
    """Extract the full (year, count) series from the one-page PDF.

    Words are grouped into visual lines by their rounded top coordinate and
    ordered left-to-right. A line is a data line only when its tokens
    alternate year / comma-formatted count (2+ tokens, even count) — this
    un-pivots the five side-by-side Year|Count print blocks into one tidy
    series and structurally excludes the title block, the header row, and
    every bar-chart label (axis years carry no comma-counts).
    """
    if not path.exists():
        raise FileNotFoundError(f"Bronze PDF missing: {path}")

    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) != 1:
            raise ValueError(f"{path.name}: expected 1 page, got {len(pdf.pages)}")
        words = pdf.pages[0].extract_words()

    lines: dict[int, list[dict]] = defaultdict(list)
    for word in words:
        lines[round(word["top"])].append(word)

    years: list[int] = []
    counts: list[int] = []
    data_lines = 0
    for top in sorted(lines):
        tokens = [w["text"] for w in sorted(lines[top], key=lambda w: w["x0"])]
        is_data_line = (
            len(tokens) >= 2
            and len(tokens) % 2 == 0
            and all(YEAR_TOKEN_RE.match(t) for t in tokens[0::2])
            and all(COUNT_TOKEN_RE.match(t) for t in tokens[1::2])
        )
        if not is_data_line:
            continue
        data_lines += 1
        years.extend(int(t) for t in tokens[0::2])
        counts.extend(int(t.replace(",", "")) for t in tokens[1::2])

    logger.info(
        "Extracted %d (year, count) pairs from %d data lines in %s",
        len(years),
        data_lines,
        path.name,
    )
    return pl.DataFrame(
        {"year": years, "year_end_inmate_population": counts},
        schema={"year": pl.Int32, "year_end_inmate_population": pl.Int64},
    )


def _assert_full_series(df: pl.DataFrame) -> int:
    """Hard-fail unless the extract is the complete, anchored 1925+ series.

    Returns the series' max year. Refresh-proof by design: the span end is
    not hardcoded (an annual refresh appends one year), but the series must
    start in 1925, be contiguous and duplicate-free, extend at least through
    2024, and reproduce the pinned anchor values exactly.
    """
    year_list = df["year"].to_list()
    max_year = max(year_list)
    expected = list(range(SERIES_START_YEAR, max_year + 1))
    if sorted(year_list) != expected:
        missing = sorted(set(expected) - set(year_list))
        dupes = sorted({y for y in year_list if year_list.count(y) > 1})
        raise ValueError(
            f"{PDF_PATH.name}: extracted years are not the contiguous "
            f"{SERIES_START_YEAR}-{max_year} series "
            f"(missing={missing[:10]}, duplicated={dupes[:10]})"
        )
    if max_year < 2024:
        raise ValueError(
            f"{PDF_PATH.name}: series ends at {max_year}, before the known "
            "2024 publication — extraction lost the trailing block"
        )
    values = dict(df.iter_rows())
    for year, anchor in FULL_SERIES_ANCHORS.items():
        if values[year] != anchor:
            raise ValueError(
                f"{PDF_PATH.name}: anchor mismatch — {year} extracted as "
                f"{values[year]:,}, expected {anchor:,}"
            )
    logger.info(
        "Full-series QA passed: contiguous %d-%d, anchors %s verified",
        SERIES_START_YEAR,
        max_year,
        FULL_SERIES_ANCHORS,
    )
    return max_year


def transform_pdf(manifest: TransformManifest) -> pl.DataFrame:
    """Extract, QA, and floor-filter the PDF into gold-shaped state rows."""
    df = _extract_year_count_pairs(PDF_PATH)
    max_year = _assert_full_series(df)

    # Manifest accounting: one bronze "row" per published year. The read-loss
    # record is parity by construction (the contiguity assertion above already
    # hard-failed any lost pair), kept for the standard accounting trail.
    manifest.record_file(
        PDF_PATH,
        max_year,
        "five_block_year_count_matrix",
        df.height,
        ["Year", "Count"],
    )
    manifest.record_read_loss(
        max_year, PDF_PATH.name, max_year - SERIES_START_YEAR + 1, df.height
    )
    for year in df["year"].to_list():
        manifest.record_bronze(year, 1)

    # Year floor: drop the 1925-1999 rows (NCRP era + December-ADP era) so
    # gold serves only the uniform Dec-31 head-count method. Recorded per
    # year so the manifest carries the floor explicitly.
    dropped = df.filter(pl.col("year") < YEAR_FLOOR)
    for year in dropped["year"].to_list():
        manifest.record_filtered(year, 1, "pre_2000_methodology_break_year_floor")
    logger.info(
        "Year floor %d: dropped %d pre-floor rows (%d-%d: NCRP era 1925-1979 "
        "+ December-ADP era 1980-1999), kept %d Dec-31 head-count rows",
        YEAR_FLOOR,
        dropped.height,
        int(dropped["year"].min()),
        int(dropped["year"].max()),
        df.height - dropped.height,
    )
    df = df.filter(pl.col("year") >= YEAR_FLOOR)

    # Statewide-only topic: every row is a state detail-level row (no
    # geography columns exist — see the module docstring).
    return df.with_columns(pl.lit("state").alias("detail_level"))


def _assert_gold_series(df: pl.DataFrame) -> None:
    """Hard-fail unless the served frame is the complete, anchored 2000+ era."""
    max_year = int(df["year"].max())
    expected_rows = max_year - YEAR_FLOOR + 1
    if df.height != expected_rows:
        raise ValueError(
            f"Gold frame has {df.height} rows; expected {expected_rows} "
            f"(one per year {YEAR_FLOOR}-{max_year})"
        )
    if df["year_end_inmate_population"].null_count():
        raise ValueError("Gold frame has NULL year_end_inmate_population values")
    values = dict(df.select("year", "year_end_inmate_population").iter_rows())
    for year, anchor in GOLD_ANCHORS.items():
        if values.get(year) != anchor:
            raise ValueError(
                f"Gold anchor mismatch — {year} is {values.get(year)}, "
                f"expected {anchor:,}"
            )
    logger.info(
        "Gold QA passed: %d rows (%d-%d), anchors %s verified, no NULLs",
        df.height,
        YEAR_FLOOR,
        max_year,
        GOLD_ANCHORS,
    )


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for inmate_population."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Extract the full series (QA-anchored), apply the year floor.
    result = transform_pdf(manifest)

    # 2. Harmonize to the gold schema (single source, so a one-frame pass).
    combined = pl.concat(harmonize_columns([result], STANDARD_COLUMNS, TARGET_TYPES))

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # would mean an extraction bug and must raise, not be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: one bronze PDF with an asserted duplicate-free extraction
    # makes collisions impossible by construction; sort_col is the documented
    # safety net (prefer the larger non-null head count) should a future
    # refresh ever add an overlapping file.
    combined = deduplicate_by_levels(
        combined,
        {"state": ["year"]},
        sort_col="year_end_inmate_population",
    )

    # 4. No geography nulling and no §4b masks: the topic has no geography
    # columns at all (statewide-only, county_fips omitted), and every value
    # is regex-validated + anchor-checked (see module docstring).
    _assert_gold_series(combined)

    # Pre-export sanity: the series is complete and never-NULL, so any
    # null-rate spike would be a regression worth failing loudly on later.
    spike = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike.details)
    validate_output(combined, required_non_null=["year", "detail_level"])

    # 5. Manifest stats on the FINAL DataFrame, then export.
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(
        combined,
        GOLD_DIR,
        STANDARD_COLUMNS,
        detail_level_files=COUNTY_DETAIL_LEVEL_FILES,
    )
    manifest.write(GOLD_DIR)

    # 6. Contract from the in-code column declaration.
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

    # 7. ALWAYS LAST: validate the gold just written against the contract
    # just emitted. Raises GoldValidationError -> non-zero exit.
    run_topic_validation(GOLD_DIR)


def _emit_contract(year_range: tuple[int, int]) -> None:
    """Emit the ODCS contract via ``write_data_dictionary``.

    The column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level`` — the contract's properties (and the validator's schema
    check) follow it.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Year-end head count of inmates of the Georgia Prison System, "
            "statewide, 2000 forward: the number of state prisoners in "
            "custody on December 31 of each year, as published by the "
            "Georgia Department of Corrections' standing 'Year-End "
            "Population since 1925' statistical report. Includes state "
            "prisoners held in state prisons, inmate boot camps, county "
            "prisons, transition centers, and private prisons; excludes "
            "probationers in detention centers, diversion centers, or "
            "probation boot camps, and inmates held in county jails. The "
            "source report reaches back to 1925, but its pre-2000 figures "
            "use different counting methods (1925-1979 National Corrections "
            "Reporting Program data; 1980-1999 December average daily "
            "population), so this dataset serves only the methodologically "
            "uniform December-31 head-count era (2000 forward) rather than "
            "pooling across the break."
        ),
        title="State Prison Year-End Population",
        summary=(
            "Year-end (December 31) head count of Georgia state prisoners, "
            "statewide, 2000 onward, from the Georgia Department of "
            "Corrections."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Calendar year; the head count is taken on December 31 "
                    "of this year. Serving starts at 2000, the first year of "
                    "the source's December-31 head-count methodology (the "
                    "report's 1925-1999 figures use different counting "
                    "methods and are not served)."
                ),
            },
            {
                "name": "year_end_inmate_population",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "key_metric": True,
                "example": 50107,
                "short_description": (
                    "State prisoners in custody on December 31 — statewide "
                    "head count of the Georgia Prison System."
                ),
                "description": (
                    "Number of inmates of the Georgia Prison System in "
                    "custody on December 31 (point-in-time head count, not "
                    "an average): state prisoners in state prisons, inmate "
                    "boot camps, county prisons, transition centers, and "
                    "private prisons. Excludes probationers in detention "
                    "centers, diversion centers, or probation boot camps, "
                    "and inmates held in county jails — do not reconcile "
                    "against county-jail population data. The served era "
                    "spans roughly 43,900 (2000) to 54,500 (2007), with the "
                    "COVID-19 drop to 46,132 in 2020."
                ),
            },
        ],
        source=(
            "Georgia Department of Corrections, Statistical Trends standing "
            "reports — Year-End Population since 1925"
        ),
        source_url=SOURCE_URL,
        update_frequency="annual (first week of January)",
        year_range=year_range,
        suppressed_to_null=False,
        usage=(
            "Cite the Georgia Department of Corrections' 'Year-End "
            "Population since 1925' statistical trends report. The metric is "
            "a statewide point-in-time stock (December 31 head count) of "
            "STATE prisoners: it excludes county-jail inmates and "
            "probation/parole supervision populations, so never reconcile it "
            "against the jail_population topic (county jails) or community-"
            "supervision counts as if they shared a denominator. Rates per "
            "resident require an external population denominator (not "
            "served here)."
        ),
        limitations=(
            "This source has no suppression; every served year has a real "
            "published value. Statewide only — no county, facility, or "
            "demographic breakdown exists in this report. Years before 2000 "
            "are deliberately not served: the source's 1925-1979 figures "
            "come from the National Corrections Reporting Program and its "
            "1980-1999 figures are December AVERAGE daily populations, "
            "neither directly comparable to the December-31 head count used "
            "from 2000 forward, so the series is floored at 2000 instead of "
            "pooling across the methodology break. The count covers state "
            "prisoners in state prisons, inmate boot camps, county prisons, "
            "transition centers, and private prisons, and excludes "
            "probationers in detention, diversion, or probation boot camps "
            "and inmates in county jails."
        ),
        quality_checks=[
            {
                "name": "no_pre_2000_years",
                "description": (
                    "Gold serves only the December-31 head-count era — the "
                    "source's pre-2000 NCRP and December-ADP figures are "
                    "methodologically different and must never appear."
                ),
                "dimension": "consistency",
                "query": "SELECT COUNT(*) FROM {object} WHERE year < 2000",
                "mustBe": 0,
            },
            {
                "name": "population_never_null",
                "description": (
                    "The source publishes a complete unsuppressed series — a "
                    "NULL head count would mean an extraction regression, "
                    "never real missingness."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE year_end_inmate_population IS NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "year_series_contiguous",
                "description": (
                    "The report is updated annually with no gaps — every "
                    "year between the earliest and latest served year must "
                    "be present (a gap means the PDF extraction lost a "
                    "print-block row)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, LEAD(year) OVER (ORDER BY year) AS next_year "
                    "FROM {object}"
                    ") WHERE next_year IS NOT NULL AND next_year != year + 1"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
