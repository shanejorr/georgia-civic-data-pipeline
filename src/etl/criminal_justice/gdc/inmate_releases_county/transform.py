"""Transform GDC inmate-release-by-county PDFs into a county x year gold fact table.

Source: Georgia Department of Corrections, Office of Data Management &
Research — Statistical Trends standing reports. Two born-digital 4-page PDFs,
one per edition: ``inmate_release_by_county_cy.pdf`` (calendar years
2021-2025) and ``inmate_release_by_county_fy.pdf`` (Georgia state fiscal
years 2022-2026). Each is ONE wide table continued across the four pages —
159 county rows plus three special rows — with five year columns covering a
rolling window of the five most recent complete years.

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Grain: county_fips x year x reporting_period (+ a statewide rollup).**
  "Home county" is the released inmate's county of RECORD at release — not
  the county of the offense and not the county of the releasing facility
  (stated in the contract; it is what makes the counts county-mappable).
- **County resolution is by NAME, never by the printed prefix.** The
  ``001``-``159`` row prefix is GDC's own alphabetical index (Appling=001 …
  Worth=159), NOT a FIPS code. The name part resolves through
  ``add_county_fips`` against the global counties dimension; any unmatched
  name HARD-STOPS (and is recorded on the manifest), never silently NULLed.
  No topic-local pre-mapping is needed: GDC prints plain county names
  (``094 - Macon County`` is the real Macon County, FIPS 13193 — no
  consolidated-government labels appear).
- **CY and FY are different 12-month windows, never pooled.** The
  ``reporting_period`` categorical (``calendar_year`` | ``fiscal_year``,
  values prescribed for sibling consistency with recidivism_reconviction)
  keeps the two editions separate; fiscal years run July 1 - June 30 and are
  labeled by their ending year (FY2026 = Jul 2025 - Jun 2026). Edition
  detection is CONTENT-based (the printed subtitle "the past five complete
  calendar|fiscal years"), never the filename.
- **The printed ``Total`` row becomes the state-detail rollup row**
  (detail_level='state', NULL county_fips), following the domain's
  county+state convention (jail_population precedent). Before anything is
  dropped, the transform asserts EXACT integer reconciliation per
  year-edition: sum of the 159 county values + the two residual rows equals
  the printed Total (verified: all 10 year-editions reconcile exactly).
- **Residual rows are excluded from gold (judgment call, documented).**
  ``999 - Other Custody/Out Of State`` (1-9 releases/yr) and ``Unknown, not
  reported`` (~880-1,270 releases/yr) are not Georgia counties. Serving them
  as extra NULL-geography state rows would break the state grain (three NULL
  county_fips rows per year-edition) or force an artificial categorical onto
  a simple count table, so they are excluded AFTER the reconciliation check
  and recorded via ``record_filtered``. Their releases remain inside the
  state Total row, so county rows sum to LESS than the state row by the
  residual amount (~7-10%% of releases, mostly unknown home county) — stated
  in the contract description, limitations, and the state-vs-county quality
  check (>=, not ==).
- **Rolling five-year window.** Each future refresh drops the oldest year
  and adds the newest; the transform keys on the year value in the column
  header (never the filename) and the natural keys
  (year, county_fips/detail_level, reporting_period) tolerate window shifts.
  Editions overlap on 2022-2025 but never collide (disjoint
  reporting_period).
- **YEAR >= 2000 floor (hard rule for this batch).** The working frame is
  defensively filtered to ``year >= YEAR_FLOOR`` before export (all
  published years are 2021-2026, so zero rows drop today); any drop would be
  recorded via ``record_filtered``. The floor is documented in the contract
  limitations and enforced by the ``year_at_or_after_2000`` quality check.
- **No suppression, no §4b masks.** Every cell in both tables is a populated
  integer (genuine zeros exist, e.g. Chattahoochee CY2025 = 0);
  ``suppressed_to_null=False``. Instead of defensive masks the parser
  HARD-FAILS on any layout deviation (unknown line, non-consecutive or
  non-5-year header, wrong label set, failed reconciliation) — on a
  fixed-layout PDF an anomaly far more likely signals a parse bug than a GDC
  publication error, so the conservative action is to stop, never NULL or
  guess. The row-shape regex cannot produce a negative or fractional count.
- **Read-loss accounting.** ``read_bronze_file`` cannot read PDFs; the
  tables are parsed with pdfplumber and the exact-shape guards (identical
  repeated page headers, 159+3 label set, 5 values per row, exact
  reconciliation) are the read-loss protection. A raw==parsed parity no-op
  is recorded per file (recidivism_reconviction precedent).
- **Repeating page header is de-duplicated structurally.** The column-header
  line repeats on each of the 4 pages; each occurrence is parsed, asserted
  identical, and counted once — data rows are never confused with it because
  the header regex is tried first.
- **Dedup tie-break.** Duplicate natural keys are impossible by construction
  (each edition contributes a disjoint reporting_period; each county label
  appears exactly once per file, enforced by the label-set guard).
  ``deduplicate_by_levels(sort_col="inmate_releases")`` remains as the
  documented safety net — prefer the row with the larger non-null count —
  should a future refresh add an overlapping file. The collision guard runs
  first and hard-fails on divergent duplicates.
"""

import logging
import re
from pathlib import Path

import pdfplumber
import polars as pl

from src.utils.crosswalks import add_county_fips
from src.utils.metadata import write_data_dictionary
from src.utils.transformers import (
    COUNTY_DETAIL_LEVEL_FILES,
    TransformManifest,
    assert_no_natural_key_collisions,
    deduplicate_by_levels,
    export_to_parquet,
    harmonize_columns,
    null_aggregate_geography,
    validate_output,
)
from src.utils.validators import (
    CRIMINAL_JUSTICE_DOMAIN_CONFIG,
    check_null_rate_spikes,
    run_topic_validation,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

TOPIC = "inmate_releases_county"
BRONZE_DIR = Path("data/bronze/criminal_justice/gdc/inmate_releases_county")
GOLD_DIR = Path("data/gold/criminal_justice/inmate_releases_county")
SOURCE_URL = (
    "https://gdc.georgia.gov/organization/about-gdc/agency-activity/"
    "research-and-reports/standing-reports/statistical-trends"
)

# HARD RULE for this ingestion batch: gold serves years from 2000 onward only.
# Applied defensively before export (all published years are 2021-2026) and
# enforced by the year_at_or_after_2000 contract quality check.
YEAR_FLOOR = 2000

# Printed report subtitle -> reporting_period. Edition detection is
# CONTENT-based (this subtitle line, repeated on every page), never
# filename-based; calendar_year / fiscal_year are prescribed for sibling
# consistency with recidivism_reconviction.
SUBTITLE_TO_PERIOD: dict[str, str] = {
    "the past five complete calendar years": "calendar_year",
    "the past five complete fiscal years": "fiscal_year",
}
REPORTING_PERIOD_VALUES: list[str] = sorted(SUBTITLE_TO_PERIOD.values())

# Special (non-county) row labels, exactly as printed after the wrapped
# '999 - Other Custody/Out Of' + 'State' continuation line is rejoined.
RESIDUAL_LABELS: tuple[str, ...] = (
    "999 - Other Custody/Out Of State",
    "Unknown, not reported",
)
TOTAL_LABEL = "Total"
RESIDUAL_FILTER_REASON = (
    "residual_non_county_rows_excluded_after_total_reconciliation"
    "(999_other_custody_out_of_state,unknown_not_reported)"
)

EXPECTED_COUNTY_ROWS = 159
EXPECTED_YEAR_COLUMNS = 5
# Bronze data rows per edition table: 159 counties + 2 residuals + Total.
EXPECTED_TABLE_ROWS = EXPECTED_COUNTY_ROWS + len(RESIDUAL_LABELS) + 1

METRIC_COLUMNS: list[str] = ["inmate_releases"]

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "county_fips",
    "reporting_period",
    "inmate_releases",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "county_fips": pl.Utf8,
    "reporting_period": pl.Utf8,
    "inmate_releases": pl.Int64,
    "detail_level": pl.Utf8,
}

NATURAL_KEYS: list[str] = [
    "year",
    "county_fips",
    "reporting_period",
    "detail_level",
]

# Page furniture (repeated header block on each of the 4 pages) — recognized
# and skipped explicitly so any UNRECOGNIZED line hard-fails the parse.
_FURNITURE_RES: list[re.Pattern[str]] = [
    re.compile(r"^Georgia Dept of Corrections\b"),
    re.compile(r"^Total prison releases by home county for$"),
    re.compile(r"^Run on \d{2}-[A-Z]{3}-\d{2}$"),
    re.compile(r"^Produced for General Production$"),
    re.compile(r"^Page \d+ of \d+$"),
]
# Table column header, repeated on every page: 'Home County' + the 5 year
# columns. Parsed (not just skipped) so the years come from the CONTENT.
_YEAR_HEADER_RE = re.compile(r"^Home County((?:\s+\d{4})+)$")
# Data row: a label followed by exactly 5 integer values (thousands commas on
# large residual/total values). The pattern cannot produce a negative or
# fractional count, so no §4b range mask is needed downstream.
_DATA_ROW_RE = re.compile(
    r"^(?P<label>\S.*?)\s+"
    r"(?P<values>\d{1,3}(?:,\d{3})*(?:\s+\d{1,3}(?:,\d{3})*){4})$"
)
# Wrapped-label continuation: the '999 - Other Custody/Out Of State' label
# breaks across two lines; the pure-alphabetic remainder ('State') is
# rejoined to the previous data row's label.
_LABEL_CONTINUATION_RE = re.compile(r"^[A-Za-z ]+$")
# County labels: GDC's 3-digit ALPHABETICAL index (001-159, NOT FIPS — the
# index is dropped) + ' - ' + the county name used for FIPS resolution.
_COUNTY_LABEL_RE = re.compile(r"^(?P<index>\d{3}) - (?P<name>.+)$")


# =============================================================================
# PDF parsing
# =============================================================================


def _parse_edition(path: Path) -> tuple[str, list[int], dict[str, list[int]]]:
    """Parse one edition PDF into (period, years, {row label: 5 counts}).

    Hard-fails on ANY deviation from the known fixed layout (unknown line,
    inconsistent repeated headers, non-5/non-consecutive year columns, wrong
    label set) — these exact-shape guards are this topic's read-loss
    protection, and a deviation means the publication changed and needs
    re-analysis through /bronze-data-structure, never a best-effort parse.
    """
    year_headers: list[list[int]] = []
    subtitles: set[str] = set()
    rows: list[tuple[str, list[int]]] = []

    with pdfplumber.open(path) as pdf:
        pages = pdf.pages
        for page in pages:
            for raw_line in (page.extract_text() or "").splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                # 1. The repeated table column header (parsed, checked below).
                if m := _YEAR_HEADER_RE.match(line):
                    year_headers.append([int(y) for y in m.group(1).split()])
                    continue
                # 2. The edition subtitle — the content-based period signal.
                if line in SUBTITLE_TO_PERIOD:
                    subtitles.add(line)
                    continue
                # 3. Remaining page furniture, skipped explicitly.
                if any(f.match(line) for f in _FURNITURE_RES):
                    continue
                # 4. A data row: label + exactly 5 integer counts.
                if m := _DATA_ROW_RE.match(line):
                    values = [
                        int(v.replace(",", "")) for v in m.group("values").split()
                    ]
                    rows.append((m.group("label"), values))
                    continue
                # 5. Wrapped-label continuation ('State' under the 999 row).
                if _LABEL_CONTINUATION_RE.match(line) and rows:
                    label, values = rows[-1]
                    rows[-1] = (f"{label} {line}", values)
                    continue
                raise ValueError(f"{path.name}: unrecognized line {line!r}")

    # Edition: exactly one subtitle variant across all pages.
    if len(subtitles) != 1:
        raise ValueError(
            f"{path.name}: expected exactly one edition subtitle, got {subtitles}"
        )
    period = SUBTITLE_TO_PERIOD[next(iter(subtitles))]

    # Repeating page header: one identical year header per page, exactly 5
    # consecutive years (the rolling five-year window).
    if len(year_headers) != len(pages) or any(
        h != year_headers[0] for h in year_headers
    ):
        raise ValueError(
            f"{path.name}: expected {len(pages)} identical repeated year "
            f"headers, got {year_headers}"
        )
    years = year_headers[0]
    if len(years) != EXPECTED_YEAR_COLUMNS or years != list(
        range(years[0], years[0] + EXPECTED_YEAR_COLUMNS)
    ):
        raise ValueError(
            f"{path.name}: expected {EXPECTED_YEAR_COLUMNS} consecutive year "
            f"columns, got {years}"
        )

    # Exact label set: 159 county rows carrying GDC's alphabetical index
    # 001-159 in printed order, the two residual rows, and the Total row —
    # each exactly once. Catches dropped, duplicated, or regex-missed rows.
    labels = [label for label, _ in rows]
    county_indexes = [
        m.group("index")
        for label in labels
        if (m := _COUNTY_LABEL_RE.match(label)) and m.group("index") != "999"
    ]
    if county_indexes != [f"{i:03d}" for i in range(1, EXPECTED_COUNTY_ROWS + 1)]:
        raise ValueError(
            f"{path.name}: county index sequence broken — got "
            f"{len(county_indexes)} county rows"
        )
    specials = [label for label in labels if not _COUNTY_LABEL_RE.match(label)] + [
        label for label in labels if label.startswith("999")
    ]
    if sorted(specials) != sorted([*RESIDUAL_LABELS, TOTAL_LABEL]):
        raise ValueError(
            f"{path.name}: special rows {sorted(specials)} != expected "
            f"{sorted([*RESIDUAL_LABELS, TOTAL_LABEL])}"
        )
    if len(rows) != EXPECTED_TABLE_ROWS:
        raise ValueError(
            f"{path.name}: expected {EXPECTED_TABLE_ROWS} table rows, got {len(rows)}"
        )

    table = dict(rows)
    _reconcile_totals(path.name, years, table)
    logger.info(
        "%s: parsed %s edition — %d rows x %d years (%d-%d), totals reconciled",
        path.name,
        period,
        len(rows),
        len(years),
        years[0],
        years[-1],
    )
    return period, years, table


def _reconcile_totals(
    label: str, years: list[int], table: dict[str, list[int]]
) -> None:
    """Assert the printed Total row reconciles EXACTLY, per year column.

    The printed statewide Total must equal the sum of the 159 county values
    plus the two residual rows for every year (verified exact in all 10
    year-editions of the current bronze). A mismatch means the parser
    mis-read the table (or GDC broke its own arithmetic) and must hard-stop
    BEFORE the residual rows are dropped — this is the check that licenses
    both the residual exclusion and serving Total as the state row.
    """
    county_rows = [
        values
        for row_label, values in table.items()
        if _COUNTY_LABEL_RE.match(row_label) and not row_label.startswith("999")
    ]
    for i, year in enumerate(years):
        component_sum = sum(values[i] for values in county_rows) + sum(
            table[res][i] for res in RESIDUAL_LABELS
        )
        if component_sum != table[TOTAL_LABEL][i]:
            raise ValueError(
                f"{label}: {year} reconciliation failed — county+residual sum "
                f"{component_sum} != printed Total {table[TOTAL_LABEL][i]}"
            )


# =============================================================================
# Per-file transform
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame:
    """Transform one edition PDF into gold-shaped long rows.

    Emits 159 county rows + 1 state row per year column. The residual
    non-county rows are excluded AFTER the exact Total reconciliation (their
    releases remain inside the state row) and recorded as filtered.
    """
    period, years, table = _parse_edition(path)

    manifest.record_file(
        path,
        max(years),
        f"{period}_wide_v1",
        EXPECTED_TABLE_ROWS,
        ["Home County", *[str(y) for y in years]],
    )
    # PDF text extraction has no raw-vs-parsed row distinction; the exact-
    # shape guards + reconciliation in _parse_edition are the read-loss
    # protection (parity no-op record, recidivism_reconviction precedent).
    manifest.record_read_loss(
        max(years), path.name, EXPECTED_TABLE_ROWS, EXPECTED_TABLE_ROWS
    )
    for i, year in enumerate(years):
        # Each year column contributes one bronze cell per table row.
        manifest.record_bronze(year, EXPECTED_TABLE_ROWS)
        # Residual exclusion (module docstring): 2 non-county rows per year.
        manifest.record_filtered(year, len(RESIDUAL_LABELS), RESIDUAL_FILTER_REASON)
        logger.info(
            "%s %s %d: residuals excluded but retained in state Total — "
            "other_custody_out_of_state=%d, unknown_not_reported=%d",
            path.name,
            period,
            year,
            table[RESIDUAL_LABELS[0]][i],
            table[RESIDUAL_LABELS[1]][i],
        )

    # reporting_period recode: the bronze value is the printed subtitle.
    subtitle = next(s for s, p in SUBTITLE_TO_PERIOD.items() if p == period)
    n_gold = (EXPECTED_COUNTY_ROWS + 1) * len(years)
    manifest.record_categorical(
        column="reporting_period",
        map_dict={subtitle: period},
        bronze_series=pl.Series("subtitle", [subtitle] * n_gold),
        gold_series=pl.Series("reporting_period", [period] * n_gold),
    )

    # Unpivot the wide table to long: county rows keep the raw label + name
    # (FIPS resolved by name in main; the 001-159 prefix is GDC's own index,
    # dropped); the printed Total row becomes the state-detail rollup.
    records: list[dict] = []
    for row_label, values in table.items():
        if row_label in RESIDUAL_LABELS:
            continue
        if row_label == TOTAL_LABEL:
            detail_level, name = "state", None
        else:
            detail_level = "county"
            name = _COUNTY_LABEL_RE.match(row_label).group("name")
        records.extend(
            {
                "year": year,
                "_raw_label": row_label,
                "_county_name": name,
                "reporting_period": period,
                "inmate_releases": value,
                "detail_level": detail_level,
            }
            for year, value in zip(years, values)
        )
    return pl.DataFrame(
        records,
        schema={
            "year": pl.Int32,
            "_raw_label": pl.Utf8,
            "_county_name": pl.Utf8,
            "reporting_period": pl.Utf8,
            "inmate_releases": pl.Int64,
            "detail_level": pl.Utf8,
        },
    )


def _resolve_county_fips(df: pl.DataFrame, manifest: TransformManifest) -> pl.DataFrame:
    """Join county FIPS by NAME; hard-stop on any unmatched county row.

    The GDC 001-159 prefix is an alphabetical index, not FIPS, so resolution
    goes through the county NAME against the global counties dimension. An
    unmatched name means the source or the crosswalk changed and must be
    fixed (topic-local pre-map or COUNTY_NAME_OVERRIDES), never silently
    NULLed — bare 'Macon County' here is the real Macon County (13193), so
    no consolidated-government pre-mapping applies. State rows (NULL name)
    keep NULL county_fips. The full raw bronze labels (prefix included) are
    recorded on the manifest for 100%% recode reviewability.
    """
    df = add_county_fips(df, "_county_name")
    unmatched = df.filter(
        (pl.col("detail_level") == "county") & pl.col("county_fips").is_null()
    )
    if unmatched.height:
        raise ValueError(
            "Unmatched county name(s) — resolve via a topic-local pre-map "
            "(never a bare global 'macon' override): "
            f"{unmatched['_county_name'].unique().sort().to_list()}"
        )
    county_rows = df.filter(pl.col("detail_level") == "county")
    manifest.record_categorical(
        column="county_fips",
        map_dict=dict(
            county_rows.select("_raw_label", "county_fips").unique().iter_rows()
        ),
        bronze_series=county_rows["_raw_label"],
        gold_series=county_rows["county_fips"],
    )
    return df


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for inmate_releases_county."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Parse + transform each edition PDF.
    pdf_paths = sorted(BRONZE_DIR.glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"No bronze PDFs found in {BRONZE_DIR}")
    frames: list[pl.DataFrame] = []
    for path in pdf_paths:
        frames.append(transform_file(path, manifest))
    # Exactly one edition per reporting basis — a missing or duplicated
    # edition means the bronze snapshot is incomplete or was re-fetched.
    periods_seen = sorted(frame["reporting_period"][0] for frame in frames)
    if periods_seen != REPORTING_PERIOD_VALUES:
        raise ValueError(
            f"Expected exactly one calendar_year and one fiscal_year edition, "
            f"got {periods_seen}"
        )

    combined = pl.concat(frames)
    logger.info("Combined %d gold-shaped rows across both editions", combined.height)

    # 2. County name -> FIPS on the combined frame (hard-stop on unmatched).
    combined = _resolve_county_fips(combined, manifest)
    combined = combined.drop("_raw_label", "_county_name")

    # 3. YEAR >= 2000 floor (hard rule): defensive — all published years are
    # 2021-2026 — with any dropped rows recorded on the manifest.
    pre_floor = combined.filter(pl.col("year") < YEAR_FLOOR)
    if pre_floor.height:
        for row in pre_floor.group_by("year").len().sort("year").to_dicts():
            manifest.record_filtered(
                int(row["year"]), int(row["len"]), f"year_floor_{YEAR_FLOOR}"
            )
        logger.warning(
            "Year floor %d dropped %d row(s) (years %s)",
            YEAR_FLOOR,
            pre_floor.height,
            sorted(pre_floor["year"].unique().to_list()),
        )
        combined = combined.filter(pl.col("year") >= YEAR_FLOOR)
    else:
        logger.info(
            "Year floor %d: all %d rows at or after the floor (0 dropped)",
            YEAR_FLOOR,
            combined.height,
        )

    # 4. Harmonize to the gold column order/types.
    combined = pl.concat(harmonize_columns([combined], STANDARD_COLUMNS, TARGET_TYPES))

    # 5. Collision guard BEFORE dedup: duplicate keys with divergent counts
    # mean a parse bug and must raise, never be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: duplicates are impossible by construction (disjoint
    # reporting_period per edition; each county label appears exactly once
    # per file, enforced by the label-set guard). sort_col inmate_releases is
    # the documented safety net — prefer the row with the larger non-null
    # count — should a future rolling-window refresh add an overlapping file.
    combined = deduplicate_by_levels(
        combined,
        {
            "county": ["year", "county_fips", "reporting_period"],
            "state": ["year", "reporting_period"],
        },
        sort_col="inmate_releases",
    )

    # 6. Geography nulling (shared domain rules; state rows already NULL).
    # No §4b masks apply: every cell is a populated non-negative integer and
    # the parser hard-fails on any deviation (see module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=CRIMINAL_JUSTICE_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity: every cell is published, so any NULL-rate spike is a
    # parse regression, not suppression.
    spike = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike.details)
    validate_output(
        combined,
        required_non_null=["year", "reporting_period", "detail_level"],
    )

    # 7. Manifest stats on the FINAL DataFrame, then export.
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(
        combined,
        GOLD_DIR,
        STANDARD_COLUMNS,
        detail_level_files=COUNTY_DETAIL_LEVEL_FILES,
    )
    manifest.write(GOLD_DIR)

    # 8. Contract from the in-code column declaration.
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

    # 9. ALWAYS LAST: validate the gold just written against the contract
    # just emitted. Raises GoldValidationError -> non-zero exit.
    run_topic_validation(GOLD_DIR)


def _emit_contract(year_range: tuple[int, int]) -> None:
    """Emit the ODCS contract via ``write_data_dictionary``.

    The column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level``.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Annual counts of Georgia prison releases by the released "
            "inmate's HOME COUNTY — the county of record GDC attributes the "
            "inmate to at release (their county of residence/record), NOT "
            "the county of the offense and NOT the county of the releasing "
            "facility. Covers all 159 Georgia counties plus a statewide "
            "rollup row, in two parallel editions of the GDC Statistical "
            "Trends standing report: calendar-year counts and Georgia state "
            "fiscal-year counts (July 1 - June 30, labeled by ending year), "
            "each a rolling window of the five most recent complete years. "
            "This measures release THROUGHPUT (people released back to each "
            "county per year), not a point-in-time population. The statewide "
            "row is the source's printed Total and also includes releases "
            "not attributable to any Georgia county (out-of-state/other "
            "custody, roughly 1-9 per year, and unknown home county, "
            "roughly 880-1,270 per year), so county rows sum to about "
            "7-10%% less than the statewide row."
        ),
        title="Prison Releases by Home County",
        summary=(
            "Annual Georgia prison releases attributed to each released "
            "inmate's home county of record, from GDC's calendar-year and "
            "fiscal-year Statistical Trends reports (rolling five-year "
            "windows)."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "short_description": (
                    "Release year (calendar year on calendar_year rows; "
                    "Georgia state fiscal year on fiscal_year rows)."
                ),
                "description": (
                    "Year of release. On reporting_period = 'calendar_year' "
                    "rows this is the calendar year of release; on "
                    "'fiscal_year' rows it is the Georgia state fiscal year "
                    "(July 1 - June 30, labeled by its ending year — fiscal "
                    "year 2026 spans July 2025 - June 2026). Each edition "
                    "covers a rolling window of the five most recent "
                    "complete years, so coverage shifts forward with every "
                    "source refresh. Years before 2000 are not served (year "
                    "floor enforced at transform time; the source publishes "
                    "none)."
                ),
            },
            {
                "name": "county_fips",
                "type": "string",
                "example": "13121",
                "null_meaning": "NULL on the statewide rollup rows.",
                "short_description": (
                    "5-digit FIPS of the released inmate's home county of "
                    "record; NULL on statewide rows."
                ),
                "description": (
                    "5-digit county FIPS code (state prefix 13) of the "
                    "released inmate's home county of record; FK to the "
                    "counties dimension. NULL on statewide rollup rows. "
                    "Resolved from the county NAME printed by GDC — the "
                    "source's own 001-159 row prefix is its internal "
                    "alphabetical index, not a FIPS code, and is not "
                    "served. Home county is the inmate's county of "
                    "record/residence at release, not the county of the "
                    "offense or of the releasing facility."
                ),
            },
            {
                "name": "reporting_period",
                "type": "string",
                "nullable": False,
                "validValues": REPORTING_PERIOD_VALUES,
                "example": "calendar_year",
                "short_description": (
                    "Release-count basis: calendar_year or fiscal_year "
                    "edition. Different 12-month windows — never pool."
                ),
                "description": (
                    "Which edition of the GDC report the row comes from: "
                    "'calendar_year' (releases counted by calendar year) or "
                    "'fiscal_year' (releases counted by Georgia state "
                    "fiscal year, July 1 - June 30). The two editions are "
                    "different 12-month windows over the same release "
                    "activity and overlap in year coverage — filter to ONE "
                    "reporting_period per analysis and never pool, sum, or "
                    "average across them."
                ),
            },
            {
                "name": "inmate_releases",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "key_metric": True,
                "label": "Inmate Releases",
                "example": 188,
                "short_description": (
                    "Count of prison releases attributed to the row's home "
                    "county in the year (statewide rows: the source's "
                    "printed Total)."
                ),
                "description": (
                    "Number of GDC prison releases in the year whose "
                    "released inmate's home county of record is the row's "
                    "county. Statewide rows carry the source's printed "
                    "Total, which additionally includes releases with an "
                    "out-of-state/other-custody home county (roughly 1-9 "
                    "per year) and releases with no home county recorded "
                    "(roughly 880-1,270 per year, about 7-10%% of all "
                    "releases) — so summing the 159 county rows yields LESS "
                    "than the statewide row by design. Zeros are real (e.g. "
                    "Chattahoochee County, calendar year 2025 = 0); the "
                    "source has no suppression, and the transform verifies "
                    "that county rows plus the excluded residual buckets "
                    "reconcile exactly to the printed Total before serving."
                ),
            },
        ],
        source=(
            "Georgia Department of Corrections, Office of Data Management & "
            "Research — Statistical Trends standing reports"
        ),
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        suppressed_to_null=False,
        usage=(
            "Cite the Georgia Department of Corrections, Office of Data "
            "Management & Research (Statistical Trends standing reports). "
            "Always filter to a single reporting_period — the calendar-year "
            "and fiscal-year editions are different 12-month windows over "
            "the same release activity and must never be pooled or summed. "
            "Use the statewide row (county_fips IS NULL) for the true "
            "statewide total: it includes releases not attributable to any "
            "Georgia county, so the 159 county rows intentionally sum to "
            "less than it. Home county is the inmate's county of record at "
            "release — do not interpret counts as offense-county or "
            "facility-county measures."
        ),
        limitations=(
            "Statewide rollup rows have NULL county_fips. Home county is "
            "the released inmate's county of record at release, not the "
            "offense or facility county. County rows do NOT sum to the "
            "statewide row: releases with an out-of-state/other-custody "
            "home county (~1-9/yr) or no recorded home county "
            "(~880-1,270/yr, about 7-10%% of releases) are included in the "
            "statewide Total but excluded as rows (they are not Georgia "
            "counties); the transform verifies the exact reconciliation "
            "before excluding them. Each edition is a rolling window of "
            "the five most recent complete years — coverage shifts forward "
            "with every source refresh, and older years drop out of the "
            "source. The calendar_year and fiscal_year editions are "
            "separate 12-month bases; never pool across reporting_period. "
            "A YEAR >= 2000 floor is enforced at transform time (all "
            "published years, 2021-2026, clear it). The source has no "
            "suppression: every cell is a published integer and zeros are "
            "real."
        ),
        quality_checks=[
            {
                "name": "year_at_or_after_2000",
                "description": (
                    "Hard ingestion rule for this topic: only years from "
                    "2000 onward are served (the source publishes "
                    "2021-2026). Enforces the transform-time year floor as "
                    "a contract invariant."
                ),
                "dimension": "consistency",
                "query": "SELECT COUNT(*) FROM {object} WHERE year < 2000",
                "mustBe": 0,
            },
            {
                "name": "inmate_releases_present",
                "description": (
                    "Every cell in both source tables is a published "
                    "integer (no suppression) — a NULL count means a parse "
                    "regression, not source suppression."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE inmate_releases IS NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "exactly_159_counties_per_year_edition",
                "description": (
                    "Each edition publishes all 159 Georgia counties for "
                    "every year column, so every (year, reporting_period) "
                    "must carry exactly 159 county rows."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, reporting_period, "
                    "COUNT(CASE WHEN county_fips IS NOT NULL THEN 1 END) "
                    "AS n_counties "
                    "FROM {object} GROUP BY year, reporting_period"
                    ") WHERE n_counties != 159"
                ),
                "mustBe": 0,
            },
            {
                "name": "one_state_row_per_year_edition",
                "description": (
                    "The source's printed Total row is served as exactly "
                    "one statewide rollup row per (year, reporting_period)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, reporting_period, "
                    "COUNT(CASE WHEN county_fips IS NULL THEN 1 END) "
                    "AS n_state "
                    "FROM {object} GROUP BY year, reporting_period"
                    ") WHERE n_state != 1"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_total_at_least_county_sum",
                "description": (
                    "The statewide row is the source's printed Total, which "
                    "includes the excluded non-county residual buckets "
                    "(out-of-state/other custody and unknown home county) — "
                    "so it must be at least the sum of the 159 county rows "
                    "for every (year, reporting_period). Exact "
                    "reconciliation including the residuals is asserted at "
                    "transform time."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, reporting_period, "
                    "MAX(CASE WHEN county_fips IS NULL THEN inmate_releases "
                    "END) AS state_total, "
                    "SUM(CASE WHEN county_fips IS NOT NULL THEN "
                    "inmate_releases END) AS county_sum "
                    "FROM {object} GROUP BY year, reporting_period"
                    ") WHERE state_total IS NOT NULL AND county_sum IS NOT "
                    "NULL AND state_total < county_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "five_years_per_reporting_period",
                "description": (
                    "Each edition is a rolling window of exactly the five "
                    "most recent complete years — fewer or more distinct "
                    "years in an edition means partitions were lost or a "
                    "stale window survived a refresh."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT reporting_period, COUNT(DISTINCT year) AS n_years "
                    "FROM {object} GROUP BY reporting_period"
                    ") WHERE n_years != 5"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
