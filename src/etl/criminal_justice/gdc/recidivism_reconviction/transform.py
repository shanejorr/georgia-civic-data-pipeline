"""Transform GDC 3-year felony reconviction PDFs into a statewide gold fact table.

Source: Georgia Department of Corrections, Office of Data Management &
Research — Statistical Trends standing reports. Two born-digital single-page
PDFs, one per edition: ``reconviction_3yr_cy.pdf`` (Calendar-Year release
cohorts 2011-2022) and ``reconviction_3yr_fy.pdf`` (Fiscal-Year release
cohorts 2012-2023). Each is one 8-row x 12-column matrix: rows are the
facility-type / sex breakdown, columns are release-cohort years, and every
cell is the share of inmates released that year who were reconvicted of a
NEW FELONY within three years of release, as a 0-100 percent.

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Grain: year x demographic x reporting_period x facility_type, statewide
  only.** The source has no county or facility-instance grain, so gold
  carries no ``county_fips`` column at all (both the column-order and
  geography-nulling validators skip absent columns) and every row exports to
  ``states.parquet``.
- **The sex axis is served as the canonical ``demographic`` column** (values
  ``all`` / ``female``), not a topic-local ``sex`` column: the female block
  is a demographic breakdown, and ``demographic`` gives the FK to the global
  demographics dimension plus the platform-wide ``demographic_category``
  filter for free. The raw sex labels derived from the row stubs go through
  ``normalize_demographic_column()`` (never a hardcoded map, per §5).
  ``demographic='all'`` rows cover the FULL cohort of the row's facility type
  (both sexes); ``female`` is the only published subset (GDC prints no
  male-only rows — not synthesized). Only ``all`` overlaps ``female`` (§5a).
- **Rollup rows are the ``facility_type='all'`` aggregation lane.** The two
  ``**``-marked stubs (``All inmate facilities``, ``All Female Facilities``)
  are aggregates of the member facility types, not summable members — they
  map to ``facility_type='all'`` (the standard ``demographic='all'``-style
  lane) so consumers can never sum them with member rows. The ``**`` footnote
  has NO printed definition anywhere on the page (documented in the
  contract). Rates are never additive across facility types anyway — GDC
  publishes no cohort sizes, so no re-weighting is possible.
- **Row-label casing/whitespace drift is normalized before recoding.** The FY
  edition lower-cases parts of the female stubs (``All female facilities``
  vs the CY ``All Female Facilities``); labels are stripped of the trailing
  ``**``, whitespace-collapsed, and lower-cased into one canonical set BEFORE
  the ``ROW_LABEL_MAP`` recode. The manifest records the RAW labels seen so
  the drift stays reviewable.
- **CY and FY are a methodological-basis split — never pooled.** The
  ``reporting_period`` categorical (``calendar_year`` | ``fiscal_year``,
  values prescribed for sibling consistency) keeps the two release-window
  definitions separate; fiscal-year rows use the Georgia state fiscal year
  (July 1 - June 30, labeled by its ending year). Edition detection is
  content-based (the printed report title + the axis caption), never the
  filename.
- **Percent -> proportion.** Published 0-100 percents are divided by 100 and
  served as ``reconviction_rate_3yr`` (``unit: proportion``, key metric).
  The source publishes NO numerator or denominator for any cell, so no
  ``metric_component`` columns exist.
- **YEAR >= 2000 floor (hard rule for this batch).** The working frame is
  defensively filtered to ``year >= YEAR_FLOOR`` before export; any dropped
  rows would be recorded on the manifest via ``record_filtered`` (all
  published cohorts are 2011-2023, so zero rows drop today). The floor is
  documented in the contract limitations and ENFORCED by the authored
  ``year_at_or_after_2000`` quality check on every validation run.
- **No suppression, no §4b masks.** Every cell in both matrices is populated
  (``suppressed_to_null=False``) and every value is a plausible in-range
  rate. Instead of a defensive mask, the parser HARD-FAILS if any parsed
  value falls outside [0, 100] or if the matrix shape / label set / year
  header deviates — for a fixed-layout PDF, an out-of-range value far more
  likely signals column misalignment (a parse bug) than a GDC publication
  error, so the conservative action is to stop, not to NULL.
- **The female member rows do NOT exhaust the female rollup (source
  evidence).** CY 2012: ``All Female Facilities`` = 20.80%% while both
  published female member rows are lower (state prison/IBCs 20.60%%,
  transition centers 19.80%%) — a weighted average cannot exceed every
  member, so the female rollup must include women released from facility
  types that get no published female row (e.g. private prisons; Emanuel
  Women's Facility, a private women's prison, opened in 2012). The
  rollup-within-member-range quality check is therefore authored for the
  full-cohort (``demographic='all'``) groups only, where the four member
  types are the source's complete facility taxonomy and the bracket holds in
  all 24 cohort-edition groups; the female non-exhaustiveness is documented
  in the contract instead.
- **Reconviction is NOT re-arrest and NOT re-incarceration.** This is
  Georgia's canonical felony-reconviction recidivism measure; it is lower
  than re-arrest-based measures by construction and must never be pooled
  with re-arrest / return-to-custody series (stated in the contract
  description and limitations).
- **Read-loss accounting.** ``read_bronze_file`` cannot read PDFs; the
  matrices are parsed with pdfplumber (already a project dependency) and the
  exact-shape guards (1 page, one title, 12 consecutive year columns, the
  exact 8-label set, 12 values per row) are the read-loss protection. A
  raw==parsed parity no-op is recorded per file (the detention_population
  Excel precedent).
- **Dedup tie-break.** Duplicate natural keys are impossible by construction
  (each edition contributes a disjoint ``reporting_period`` and each matrix
  cell appears exactly once, enforced by the label-set and year-header
  guards). ``deduplicate_by_levels(sort_col="reconviction_rate_3yr")``
  remains as the documented safety net — prefer the row with the larger
  non-null rate — should a future refresh add an overlapping file. The
  collision guard runs first and hard-fails on divergent duplicates.
"""

import logging
import re
from pathlib import Path

import pdfplumber
import polars as pl

from src.utils.demographics import (
    DEMOGRAPHIC_ALIASES,
    SENTINEL_UNMATCHED_DEMOGRAPHIC,
    normalize_demographic_column,
)
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

TOPIC = "recidivism_reconviction"
BRONZE_DIR = Path("data/bronze/criminal_justice/gdc/recidivism_reconviction")
GOLD_DIR = Path("data/gold/criminal_justice/recidivism_reconviction")
SOURCE_URL = (
    "https://gdc.georgia.gov/organization/about-gdc/agency-activity/"
    "research-and-reports/standing-reports/statistical-trends"
)

# HARD RULE for this ingestion batch: gold serves release cohorts from 2000
# onward only. Applied defensively before export (all published cohorts are
# 2011-2023) and enforced by the year_at_or_after_2000 contract quality check.
YEAR_FLOOR = 2000

# Printed report title -> reporting_period. Edition detection is CONTENT-based
# (title + axis caption below), never filename-based; the values
# calendar_year / fiscal_year are prescribed for sibling consistency.
TITLE_TO_PERIOD: dict[str, str] = {
    "CY Recidivism Rates (Felony Reconviction)": "calendar_year",
    "FY Recidivism Rates (Felony Reconviction)": "fiscal_year",
}
# Axis caption printed above the year header, used to cross-check the title.
PERIOD_AXIS_CAPTION: dict[str, str] = {
    "calendar_year": "Calendar Year",
    "fiscal_year": "Fiscal Year",
}

# Canonical (normalized) row stub -> (facility_type, raw sex label). Labels
# are normalized (trailing '**' stripped, whitespace collapsed, lower-cased)
# BEFORE this map so the CY/FY casing drift ('All Female Facilities' vs 'All
# female facilities') collapses to one key. The two '**' rows are ROLLUPS ->
# facility_type='all' (the aggregation lane), never summable members. The raw
# sex label goes through normalize_demographic_column(), per §5.
ROW_LABEL_MAP: dict[str, tuple[str, str]] = {
    "all inmate facilities": ("all", "All"),
    "private prisons": ("private_prison", "All"),
    "state prison, ibcs": ("state_prison_ibc", "All"),
    "county ci": ("county_ci", "All"),
    "transition centers": ("transition_center", "All"),
    "all female facilities": ("all", "Female"),
    "female state prison, ibcs": ("state_prison_ibc", "Female"),
    "female transition centers": ("transition_center", "Female"),
}
FACILITY_TYPE_MAP: dict[str, str] = {k: v[0] for k, v in ROW_LABEL_MAP.items()}
SEX_LABEL_MAP: dict[str, str] = {k: v[1] for k, v in ROW_LABEL_MAP.items()}

EXPECTED_MATRIX_ROWS = len(ROW_LABEL_MAP)  # 8
EXPECTED_YEAR_COLUMNS = 12

FACILITY_TYPE_VALUES: list[str] = sorted(set(FACILITY_TYPE_MAP.values()))
REPORTING_PERIOD_VALUES: list[str] = sorted(TITLE_TO_PERIOD.values())
# GDC publishes female rows only for these facility types (no female
# private-prison or county-CI rows exist in either edition).
FEMALE_PUBLISHED_FACILITY_TYPES: list[str] = sorted(
    {ft for ft, sex in ROW_LABEL_MAP.values() if sex == "Female"}
)

METRIC_COLUMNS: list[str] = ["reconviction_rate_3yr"]

# Gold fact column order. `detail_level` is carried through dedup / export
# splitting, then dropped by export_to_parquet(). No geography column: the
# source is statewide only (see module docstring).
STANDARD_COLUMNS: list[str] = [
    "year",
    "demographic",
    "reporting_period",
    "facility_type",
    "reconviction_rate_3yr",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "demographic": pl.Utf8,
    "reporting_period": pl.Utf8,
    "facility_type": pl.Utf8,
    "reconviction_rate_3yr": pl.Float64,
    "detail_level": pl.Utf8,
}

NATURAL_KEYS: list[str] = [
    "year",
    "demographic",
    "reporting_period",
    "facility_type",
    "detail_level",
]

# Year header line: 'Facility Type' followed by the 12 cohort-year columns.
_HEADER_RE = re.compile(r"^Facility Type((?:\s+(?:19|20)\d{2})+)$")
# Data row: a non-numeric label (letters, spaces, commas, the '**' marker)
# followed by one 0-100 rate per year column (1-2 decimals).
_DATA_ROW_RE = re.compile(
    r"^(?P<label>[A-Za-z][A-Za-z ,*]*?)\s+"
    r"(?P<values>\d{1,3}\.\d{1,2}(?:\s+\d{1,3}\.\d{1,2})*)$"
)


def _normalize_label(raw: str) -> str:
    """Collapse a raw row stub to its canonical ROW_LABEL_MAP key.

    Strips the trailing '**' rollup marker, collapses whitespace, and
    lower-cases so the CY/FY casing drift maps to one key.
    """
    return re.sub(r"\s+", " ", re.sub(r"\s*\*+\s*$", "", raw.strip())).lower()


# =============================================================================
# PDF parsing
# =============================================================================


def _parse_matrix(path: Path) -> tuple[str, str, list[int], pl.DataFrame]:
    """Parse one edition PDF into (title, period, years, long DataFrame).

    Hard-fails on ANY deviation from the known fixed layout (page count,
    title, axis caption, year-header shape, label set, values per row, value
    range) — these exact-shape guards are this topic's read-loss protection,
    and a deviation means the publication changed and needs re-analysis
    through /bronze-data-structure, never a silent best-effort parse.
    """
    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) != 1:
            raise ValueError(f"{path.name}: expected 1 page, got {len(pdf.pages)}")
        text = pdf.pages[0].extract_text() or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # Edition detection from the printed report title (content-based).
    titles = [line for line in lines if line in TITLE_TO_PERIOD]
    if len(titles) != 1:
        raise ValueError(
            f"{path.name}: expected exactly one known report title, got {titles}"
        )
    title = titles[0]
    period = TITLE_TO_PERIOD[title]
    # Cross-check: the axis caption above the year header must agree.
    if PERIOD_AXIS_CAPTION[period] not in lines:
        raise ValueError(
            f"{path.name}: title says {period!r} but axis caption "
            f"{PERIOD_AXIS_CAPTION[period]!r} is missing"
        )

    header_matches = [m for line in lines if (m := _HEADER_RE.match(line))]
    if len(header_matches) != 1:
        raise ValueError(
            f"{path.name}: expected exactly one 'Facility Type <years>' header, "
            f"got {len(header_matches)}"
        )
    years = [int(y) for y in header_matches[0].group(1).split()]
    if len(years) != EXPECTED_YEAR_COLUMNS or years != list(
        range(years[0], years[0] + len(years))
    ):
        raise ValueError(
            f"{path.name}: expected {EXPECTED_YEAR_COLUMNS} consecutive "
            f"cohort-year columns, got {years}"
        )

    # Data rows: label + one rate per year column. Non-matching lines (date
    # stamp, titles, captions) are skipped; the exact-label-set assertion
    # below catches any data row that failed to match.
    records: list[dict] = []
    raw_labels: list[str] = []
    for line in lines:
        if _HEADER_RE.match(line):
            continue
        m = _DATA_ROW_RE.match(line)
        if m is None:
            continue
        raw_label = m.group("label").strip()
        values = [float(v) for v in m.group("values").split()]
        if len(values) != len(years):
            raise ValueError(
                f"{path.name}: row {raw_label!r} has {len(values)} values for "
                f"{len(years)} year columns"
            )
        # Parse-integrity guard (not a §4b mask): a rate outside 0-100 on this
        # fixed layout means column misalignment — stop, never NULL or guess.
        bad = [v for v in values if not 0.0 <= v <= 100.0]
        if bad:
            raise ValueError(
                f"{path.name}: row {raw_label!r} has out-of-range percent "
                f"values {bad} — likely a parse misalignment"
            )
        raw_labels.append(raw_label)
        records.extend(
            {"raw_label": raw_label, "year": year, "rate_percent": value}
            for year, value in zip(years, values)
        )

    # The 8 canonical stubs must each appear exactly once — catches dropped,
    # duplicated, renamed, or regex-missed rows in one assertion.
    norm_labels = sorted(_normalize_label(raw) for raw in raw_labels)
    if norm_labels != sorted(ROW_LABEL_MAP):
        raise ValueError(
            f"{path.name}: row stubs {norm_labels} != expected "
            f"{sorted(ROW_LABEL_MAP)} — the layout changed; re-run "
            "/bronze-data-structure"
        )

    long_df = pl.DataFrame(
        records,
        schema={"raw_label": pl.Utf8, "year": pl.Int32, "rate_percent": pl.Float64},
    )
    logger.info(
        "%s: parsed %s edition — %d rows x %d cohort years (%d-%d)",
        path.name,
        period,
        EXPECTED_MATRIX_ROWS,
        len(years),
        years[0],
        years[-1],
    )
    return title, period, years, long_df


# =============================================================================
# Per-file transform
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame:
    """Transform one edition PDF into gold-shaped rows."""
    title, period, years, df = _parse_matrix(path)

    manifest.record_file(
        path,
        max(years),
        f"{period}_matrix_v1",
        EXPECTED_MATRIX_ROWS,
        ["facility_type", *[str(y) for y in years]],
    )
    # PDF text extraction has no raw-vs-parsed row distinction; the exact-
    # shape guards in _parse_matrix are the read-loss protection (parity
    # no-op record, mirroring the Excel-read precedent).
    manifest.record_read_loss(
        max(years), path.name, EXPECTED_MATRIX_ROWS, EXPECTED_MATRIX_ROWS
    )
    # Each cohort-year column contributes one bronze cell per matrix row.
    for year in years:
        manifest.record_bronze(year, EXPECTED_MATRIX_ROWS)

    # Normalize the row stub (strip '**', collapse whitespace, lower-case) so
    # CY/FY casing drift recodes through one canonical map, then split the
    # compound stub into facility_type + raw sex label.
    df = df.with_columns(
        pl.col("raw_label")
        .str.replace(r"\s*\*+\s*$", "")
        .str.strip_chars()
        .str.replace_all(r"\s+", " ")
        .str.to_lowercase()
        .alias("_label_norm")
    )
    df = df.with_columns(
        pl.col("_label_norm").replace_strict(FACILITY_TYPE_MAP).alias("facility_type"),
        pl.col("_label_norm").replace_strict(SEX_LABEL_MAP).alias("sex_raw"),
    )

    # Demographic normalization via the shared canonical path (§5) — the raw
    # sex labels ('All' / 'Female') map through DEMOGRAPHIC_ALIASES.
    df = df.with_columns(normalize_demographic_column("sex_raw").alias("demographic"))
    unmatched = df.filter(pl.col("demographic") == SENTINEL_UNMATCHED_DEMOGRAPHIC)
    if unmatched.height:
        raise ValueError(
            f"{path.name}: unmatched demographic labels "
            f"{unmatched['sex_raw'].unique().to_list()} — add aliases to "
            "src/utils/demographics.py, never drop rows"
        )

    # Manifest recodes keyed by the RAW stubs so the CY/FY casing drift stays
    # reviewable (raw label -> gold value, one entry per observed variant).
    raw_to_norm = dict(df.select("raw_label", "_label_norm").unique().iter_rows())
    manifest.record_categorical(
        column="facility_type",
        map_dict={raw: FACILITY_TYPE_MAP[norm] for raw, norm in raw_to_norm.items()},
        bronze_series=df["raw_label"],
        gold_series=df["facility_type"],
    )
    # Effective alias slice (§4.3a): only the aliases actually hit.
    observed_sex = df["sex_raw"].unique().to_list()
    manifest.record_categorical(
        column="demographic",
        map_dict={
            label: DEMOGRAPHIC_ALIASES[label.upper()]
            for label in observed_sex
            if label.upper() in DEMOGRAPHIC_ALIASES
        },
        bronze_series=df["sex_raw"],
        gold_series=df["demographic"],
    )
    # reporting_period's bronze value is the printed report title.
    manifest.record_categorical(
        column="reporting_period",
        map_dict={title: period},
        bronze_series=pl.Series("title", [title] * df.height),
        gold_series=pl.Series("reporting_period", [period] * df.height),
    )

    # Published 0-100 percent -> 0-1 proportion (§4); statewide detail level.
    df = df.with_columns(
        (pl.col("rate_percent") / 100.0).alias("reconviction_rate_3yr"),
        pl.lit(period).alias("reporting_period"),
        pl.lit("state").alias("detail_level"),
    )
    return df.select(STANDARD_COLUMNS)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for recidivism_reconviction."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Parse + transform each edition PDF.
    pdf_paths = sorted(BRONZE_DIR.glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"No bronze PDFs found in {BRONZE_DIR}")
    frames: list[pl.DataFrame] = []
    periods_seen: list[str] = []
    for path in pdf_paths:
        df = transform_file(path, manifest)
        periods_seen.append(df["reporting_period"][0])
        frames.append(df)
    # Exactly one edition per reporting basis — a missing or duplicated
    # edition means the bronze snapshot is incomplete or was re-fetched.
    if sorted(periods_seen) != REPORTING_PERIOD_VALUES:
        raise ValueError(
            f"Expected exactly one calendar_year and one fiscal_year edition, "
            f"got {periods_seen}"
        )

    # 2. Harmonize + concat across the two editions.
    combined = pl.concat(harmonize_columns(frames, STANDARD_COLUMNS, TARGET_TYPES))
    logger.info("Combined %d gold-shaped rows across both editions", combined.height)

    # 3. YEAR >= 2000 floor (hard rule): defensive — all published cohorts are
    # 2011-2023 — with any dropped rows recorded on the manifest.
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

    # 4. Collision guard BEFORE dedup: duplicate keys with divergent rates
    # mean a label-normalization bug and must raise, never be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: duplicates are impossible by construction (disjoint
    # reporting_period per edition; each matrix cell parsed exactly once);
    # sort_col reconviction_rate_3yr is the documented safety net — prefer
    # the row with the larger non-null rate should a refresh add overlap.
    combined = deduplicate_by_levels(
        combined,
        {"state": [k for k in NATURAL_KEYS if k != "detail_level"]},
        sort_col="reconviction_rate_3yr",
    )

    # 5. Geography nulling (shared domain rules). No geography column exists
    # on this statewide-only topic, so this is a structural no-op kept for
    # domain convention. No §4b masks apply: every cell is populated and
    # in-range (the parser hard-fails otherwise — see module docstring).
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
        required_non_null=[
            "year",
            "demographic",
            "reporting_period",
            "facility_type",
            "detail_level",
        ],
    )

    # 6. Manifest stats on the FINAL DataFrame, then export.
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(
        combined,
        GOLD_DIR,
        STANDARD_COLUMNS,
        detail_level_files=COUNTY_DETAIL_LEVEL_FILES,
    )
    manifest.write(GOLD_DIR)

    # 7. Contract from the in-code column declaration.
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

    # 8. ALWAYS LAST: validate the gold just written against the contract
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
            "Georgia's canonical prison-recidivism measure: the share of "
            "inmates released from Georgia Department of Corrections "
            "facilities in a given cohort year who were RECONVICTED of a new "
            "felony within three years of release. Statewide only, broken "
            "down by release facility type (private prisons, state prisons "
            "and inmate boot camps, county correctional institutions, "
            "transition centers, plus an all-facilities rollup) and by sex "
            "(full-cohort rows plus a female-only block), in two parallel "
            "editions: calendar-year release cohorts (2011-2022) and Georgia "
            "state fiscal-year release cohorts (2012-2023). This measures "
            "felony reconviction, NOT re-arrest and NOT re-incarceration or "
            "return to custody — it is lower than re-arrest-based recidivism "
            "measures by construction and must never be pooled with them. "
            "GDC publishes only rates: no cohort sizes or reconviction "
            "counts exist in this report."
        ),
        title="3-Year Felony Reconviction Rates",
        summary=(
            "Share of Georgia inmates reconvicted of a new felony within "
            "three years of release, statewide by facility type and sex, "
            "for calendar- and fiscal-year release cohorts."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2022,
                "short_description": (
                    "Release-cohort year (calendar year on calendar_year "
                    "rows; Georgia state fiscal year on fiscal_year rows)."
                ),
                "description": (
                    "Release-cohort year — the year the cohort was RELEASED, "
                    "not the year of reconviction. On reporting_period = "
                    "'calendar_year' rows this is the calendar year of "
                    "release (2011-2022); on 'fiscal_year' rows it is the "
                    "Georgia state fiscal year of release (July 1 - June 30, "
                    "labeled by its ending year; 2012-2023). Every published "
                    "cohort has a fully matured 3-year follow-up window — "
                    "GDC only publishes cohorts whose window is complete. "
                    "Cohorts before 2000 are not served (year floor enforced "
                    "at transform time; the source publishes none)."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "all",
                "short_description": (
                    "Sex slice: 'all' (full cohort, both sexes) or 'female' "
                    "(female-only block). No male-only rows are published."
                ),
                "description": (
                    "Sex slice of the release cohort; FK to the demographics "
                    "dimension. 'all' rows cover the FULL cohort of the "
                    "row's facility type (both sexes); 'female' rows are the "
                    "female-only subset GDC publishes for all facilities, "
                    "state prisons/IBCs, and transition centers (no female "
                    "private-prison or county-CI rows exist in the source, "
                    "and no male-only rows are published or synthesized). "
                    "Note the female all-facilities rollup covers ALL women "
                    "released — including from facility types with no "
                    "published female row (in calendar year 2012 it exceeds "
                    "both published female member rows, 20.8%% vs 20.6%% and "
                    "19.8%%, as published). Only 'all' overlaps 'female' — "
                    "never sum across demographic values."
                ),
            },
            {
                "name": "reporting_period",
                "type": "string",
                "nullable": False,
                "validValues": REPORTING_PERIOD_VALUES,
                "example": "calendar_year",
                "short_description": (
                    "Release-cohort basis: calendar_year or fiscal_year "
                    "edition. Methodologically distinct — never pool."
                ),
                "description": (
                    "Which edition of the GDC report the row comes from: "
                    "'calendar_year' (release cohorts defined by calendar "
                    "year, 2011-2022) or 'fiscal_year' (release cohorts "
                    "defined by Georgia state fiscal year, July 1 - June 30, "
                    "2012-2023). The two editions are different definitions "
                    "of the release window over overlapping populations — "
                    "filter to ONE reporting_period per analysis and never "
                    "pool or average across them."
                ),
            },
            {
                "name": "facility_type",
                "type": "string",
                "nullable": False,
                "validValues": FACILITY_TYPE_VALUES,
                "example": "state_prison_ibc",
                "short_description": (
                    "Facility type the cohort was released from; 'all' is "
                    "the rollup row, not a summable member."
                ),
                "description": (
                    "Type of GDC facility the cohort was released from: "
                    "'private_prison', 'state_prison_ibc' (state prisons "
                    "plus inmate boot camps), 'county_ci' (county "
                    "correctional institutions), 'transition_center', or "
                    "'all' — the source's rollup rows ('All inmate "
                    "facilities', 'All Female Facilities', both marked '**' "
                    "in the source with no printed footnote definition). "
                    "'all' is an aggregate lane, not a member: rates are "
                    "NEVER additive or averageable across facility types "
                    "(no cohort sizes are published to weight them) — use "
                    "the 'all' row for the overall rate."
                ),
            },
            {
                "name": "reconviction_rate_3yr",
                "type": "float64",
                "unit": "proportion",
                "nullable": False,
                "key_metric": True,
                "label": "3-Year Reconviction Rate",
                "example": 0.311,
                "short_description": (
                    "Share of the release cohort reconvicted of a new felony "
                    "within 3 years of release (0-1 proportion)."
                ),
                "description": (
                    "Share of inmates released in the cohort year (from the "
                    "row's facility-type and sex slice) who were reconvicted "
                    "of a NEW FELONY within three years of release. "
                    "Published by GDC as a one-decimal percent (e.g. 26.9) "
                    "and served here as a 0-1 proportion (0.269). Felony "
                    "reconviction only: excludes re-arrests without "
                    "conviction, misdemeanor convictions, and technical "
                    "revocations/returns to custody, so it is lower than "
                    "re-arrest-based recidivism measures by construction. "
                    "The underlying cohort size and reconviction count are "
                    "not published, so rates cannot be re-weighted or "
                    "combined across rows. Every published cell is populated "
                    "(no suppression)."
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
            "and fiscal-year editions are methodologically distinct release-"
            "window definitions and must never be pooled or averaged. Use "
            "facility_type = 'all' with demographic = 'all' for the "
            "headline statewide rate; never sum or average rates across "
            "facility types or demographic values (no cohort sizes are "
            "published to weight them). Do not compare against re-arrest- "
            "or re-incarceration-based recidivism measures — this is felony "
            "reconviction only."
        ),
        limitations=(
            "Statewide only: the source publishes no county or facility-"
            "level grain, so this dataset has no county_fips column. Rates "
            "only: GDC publishes no cohort sizes or reconviction counts, so "
            "rates cannot be re-weighted, combined across facility types, "
            "or converted to counts. This measures felony RECONVICTION "
            "within 3 years of release — not re-arrest, not misdemeanor "
            "reconviction, and not re-incarceration/return to custody — and "
            "must not be pooled with recidivism series built on those "
            "definitions. The calendar_year and fiscal_year editions are "
            "separate methodological bases; never pool across "
            "reporting_period. Sex breakdowns cover only the female block "
            "GDC publishes (no male-only rows; female rows exist only for "
            "the all-facilities rollup, state prisons/IBCs, and transition "
            "centers). The female facility-type rows do not exhaust the "
            "female rollup: 'All Female Facilities' includes women released "
            "from facility types with no published female row, and in "
            "calendar year 2012 it exceeds both published female member "
            "rows as published by the source. The '**' marker on the "
            "source's two rollup rows has "
            "no printed definition on the page. A YEAR >= 2000 floor is "
            "enforced at transform time (all published cohorts, 2011-2023, "
            "clear it). Rates are as published, rounded to one decimal on "
            "the percent scale (0.001 on the served proportion scale)."
        ),
        quality_checks=[
            {
                "name": "year_at_or_after_2000",
                "description": (
                    "Hard ingestion rule for this topic: only release "
                    "cohorts from 2000 onward are served (the source "
                    "publishes 2011-2023). Enforces the transform-time year "
                    "floor as a contract invariant."
                ),
                "dimension": "consistency",
                "query": "SELECT COUNT(*) FROM {object} WHERE year < 2000",
                "mustBe": 0,
            },
            {
                "name": "reconviction_rate_present",
                "description": (
                    "Every cell in both source matrices is populated (no "
                    "suppression, no missing cells) — a NULL rate means a "
                    "parse regression, not source suppression."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE reconviction_rate_3yr IS NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "eight_rows_per_cohort_edition",
                "description": (
                    "Each edition publishes exactly 8 breakdown rows per "
                    "cohort year (5 facility types x full cohort + 3 female "
                    "rows) — any other count means rows were dropped or "
                    "duplicated in parsing."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, reporting_period, COUNT(*) AS n "
                    "FROM {object} GROUP BY year, reporting_period"
                    ") WHERE n != 8"
                ),
                "mustBe": 0,
            },
            {
                "name": "full_cohort_rollup_within_member_range",
                "description": (
                    "On full-cohort rows (demographic='all') the four member "
                    "facility types are the source's complete taxonomy, so "
                    "the facility_type='all' rollup — a cohort-weighted "
                    "average — must lie between the member minimum and "
                    "maximum (tolerance 0.001 = 0.1 percentage point, the "
                    "source's published precision). Deliberately NOT applied "
                    "to female groups: the female block is a partial breakout "
                    "and its rollup provably exceeds both published female "
                    "members in CY 2012 (20.8 vs 20.6/19.8), so no bracket "
                    "invariant exists there."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, reporting_period, "
                    "MAX(CASE WHEN facility_type = 'all' THEN "
                    "reconviction_rate_3yr END) AS rollup_rate, "
                    "MIN(CASE WHEN facility_type != 'all' THEN "
                    "reconviction_rate_3yr END) AS member_min, "
                    "MAX(CASE WHEN facility_type != 'all' THEN "
                    "reconviction_rate_3yr END) AS member_max "
                    "FROM {object} WHERE demographic = 'all' "
                    "GROUP BY year, reporting_period"
                    ") WHERE rollup_rate IS NOT NULL "
                    "AND member_min IS NOT NULL "
                    "AND (rollup_rate < member_min - 0.001 "
                    "OR rollup_rate > member_max + 0.001)"
                ),
                "mustBe": 0,
            },
            {
                "name": "female_rows_only_for_published_facility_types",
                "description": (
                    "GDC publishes female rows only for the all-facilities "
                    "rollup, state prisons/IBCs, and transition centers — a "
                    "female row under any other facility type means the "
                    "row-label recode broke."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE demographic = 'female' AND facility_type NOT IN ("
                    + ", ".join(f"'{ft}'" for ft in FEMALE_PUBLISHED_FACILITY_TYPES)
                    + ")"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
