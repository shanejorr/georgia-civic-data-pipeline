"""Shared parsing helpers for GA DPH OASIS Data Table Tool exports.

The OASIS mortality topics (``overdose_deaths``, ``violent_deaths``) download
the same export format from ``https://oasis.state.ga.us/dtt``: per-cause CSVs
in five layouts (county x year, plus state-grain age / race / ethnicity / sex
breakdowns), all with the metric triplet ``deaths`` / ``death_rate`` /
``age_adjusted_death_rate`` (rates per 100,000 population; the age layout
omits the age-adjusted rate because the tool disallows age-adjusted measures
with age stratification).

Format quirks handled here (see each topic's ``bronze-data-structure.md``):

- ``year`` is a string column because every geography/bucket group carries a
  derived ``selected_years_total`` row (the 1999-2024 sum) — dropped.
- County files carry a derived ``County Summary`` row duplicating the Georgia
  total — dropped after asserting it matches the Georgia row's deaths.
- Breakdown files carry a derived ``Selected {Races|Sexes|...} Total`` row
  duplicating the ``All {Races|Sexes|...}`` row — dropped after asserting
  equality on deaths.
- ``deaths`` empty cells are TRUE ZEROS per OASIS (never suppressed) —
  filled with 0.
- Rates are numeric with NEGATIVE SENTINELS (``-5`` = suppressed, fewer than
  5 events; ``-2`` = not applicable, no population denominator; other codes
  documented by the tool) — any negative rate is nulled by value, never by
  string marker.
- Zero-death rows render their rates inconsistently (``0.0`` or empty); a
  true-zero-deaths row has a true rate of 0, normalized here.
"""

import logging
from pathlib import Path

import polars as pl

from src.utils.readers import read_bronze_file
from src.utils.transformers import detect_era_by_columns

logger = logging.getLogger(__name__)

# The derived all-years-sum value in the `year` column.
OASIS_TOTAL_YEAR = "selected_years_total"

# The derived duplicate-of-Georgia geography row in county-layout files.
OASIS_COUNTY_SUMMARY = "County Summary"

# Bronze rate columns (per 100,000 population). The age layout lacks
# age_adjusted_death_rate; helpers skip columns absent from the frame.
OASIS_RATE_COLUMNS = ["death_rate", "age_adjusted_death_rate"]

# Layout detection by column signature (never by filename or year range).
# Most-specific first: every layout shares geography/year/deaths and differs
# only by its breakdown column.
OASIS_LAYOUT_SIGNATURES: dict[str, list[str]] = {
    "county": ["geography", "county_fips", "year", "deaths"],
    "age": ["geography", "age", "year", "deaths"],
    "race": ["geography", "race", "year", "deaths"],
    "ethnicity": ["geography", "ethnicity", "year", "deaths"],
    "sex": ["geography", "sex", "year", "deaths"],
}

# Per-breakdown (all-rows label, derived selected-total label) pairs.
OASIS_BREAKDOWN_LABELS: dict[str, tuple[str, str]] = {
    "age": ("All Detailed Ages", "Selected Ages Total"),
    "race": ("All Races", "Selected Races Total"),
    "ethnicity": ("All Ethnicities", "Selected Ethnicities Total"),
    "sex": ("All Sexes", "Selected Sexes Total"),
}


def read_oasis_csv(path: Path) -> tuple[pl.DataFrame, dict]:
    """Read an OASIS export all-string, with read-loss accounting.

    All-string (``infer_schema_length=0``) because ``year`` mixes 4-digit
    years with the ``selected_years_total`` string and ``county_fips`` is a
    bare integer code — schema inference would mis-type both. Numeric columns
    are cast explicitly by :func:`cast_oasis_metrics`.
    """
    return read_bronze_file(path, infer_schema_length=0, return_loss=True)


def detect_oasis_layout(df: pl.DataFrame, filename: str) -> str:
    """Return the layout key for an export frame; raise if none matches."""
    layout = detect_era_by_columns(df, OASIS_LAYOUT_SIGNATURES)
    if layout is None:
        raise ValueError(f"{filename}: no OASIS layout signature matched {df.columns}")
    return layout


def cast_oasis_metrics(df: pl.DataFrame, filename: str) -> pl.DataFrame:
    """Cast deaths/rates off the all-string read.

    ``deaths`` empty = true zero per OASIS (never suppressed), so nulls are
    filled with 0. Rates cast STRICTLY: sentinels are numeric (``-5``/``-2``),
    and any non-numeric residue (a new suppression marker the reader did not
    null) must fail loudly rather than silently null (rename-bug guard).
    """
    df = df.with_columns(pl.col("deaths").cast(pl.Int64).fill_null(0))
    rate_cols = [c for c in OASIS_RATE_COLUMNS if c in df.columns]
    try:
        df = df.with_columns(pl.col(c).cast(pl.Float64) for c in rate_cols)
    except pl.exceptions.InvalidOperationError as exc:  # pragma: no cover
        raise ValueError(
            f"{filename}: non-numeric rate values survived the bronze read — "
            f"a new suppression marker needs handling: {exc}"
        ) from exc
    return df


def drop_total_year_rows(df: pl.DataFrame, filename: str) -> tuple[pl.DataFrame, int]:
    """Drop the derived ``selected_years_total`` rows and cast year to Int32."""
    kept = df.filter(pl.col("year") != OASIS_TOTAL_YEAR)
    dropped = df.height - kept.height
    logger.info(
        "%s: dropped %d derived '%s' row(s)", filename, dropped, OASIS_TOTAL_YEAR
    )
    return kept.with_columns(pl.col("year").cast(pl.Int32)), dropped


def drop_county_summary_rows(
    df: pl.DataFrame, filename: str
) -> tuple[pl.DataFrame, int]:
    """Drop derived ``County Summary`` rows, asserting they mirror Georgia.

    The County Summary row duplicates the statewide (Georgia) total; keeping
    both would double the state series. Equality is asserted on deaths (the
    unsuppressed metric) per year before dropping.
    """
    check = (
        df.group_by("year")
        .agg(
            pl.col("deaths")
            .filter(pl.col("geography") == OASIS_COUNTY_SUMMARY)
            .sum()
            .alias("summary_deaths"),
            pl.col("deaths")
            .filter(pl.col("geography") == "Georgia")
            .sum()
            .alias("georgia_deaths"),
        )
        .filter(pl.col("summary_deaths") != pl.col("georgia_deaths"))
    )
    if check.height:
        raise ValueError(
            f"{filename}: 'County Summary' rows diverge from the Georgia row "
            f"on deaths — not a pure duplicate:\n{check}"
        )
    kept = df.filter(pl.col("geography") != OASIS_COUNTY_SUMMARY)
    dropped = df.height - kept.height
    logger.info(
        "%s: dropped %d derived '%s' row(s) (verified equal to Georgia rows)",
        filename,
        dropped,
        OASIS_COUNTY_SUMMARY,
    )
    return kept, dropped


def drop_selected_total_rows(
    df: pl.DataFrame, breakdown_col: str, filename: str
) -> tuple[pl.DataFrame, int]:
    """Drop the derived ``Selected ... Total`` rows in a breakdown file.

    The tool emits a ``Selected {X}s Total`` row summing the selected buckets;
    with every bucket selected it duplicates the ``All {X}s`` row. Equality is
    asserted on deaths per year before dropping.
    """
    all_label, total_label = OASIS_BREAKDOWN_LABELS[breakdown_col]
    check = (
        df.group_by("year")
        .agg(
            pl.col("deaths")
            .filter(pl.col(breakdown_col) == total_label)
            .sum()
            .alias("selected_total_deaths"),
            pl.col("deaths")
            .filter(pl.col(breakdown_col) == all_label)
            .sum()
            .alias("all_deaths"),
        )
        .filter(pl.col("selected_total_deaths") != pl.col("all_deaths"))
    )
    if check.height:
        raise ValueError(
            f"{filename}: '{total_label}' rows diverge from '{all_label}' "
            f"rows on deaths — not a pure duplicate:\n{check}"
        )
    kept = df.filter(pl.col(breakdown_col) != total_label)
    dropped = df.height - kept.height
    logger.info(
        "%s: dropped %d derived '%s' row(s) (verified equal to '%s' rows)",
        filename,
        dropped,
        total_label,
        all_label,
    )
    return kept, dropped


def normalize_zero_death_rates(
    df: pl.DataFrame, rate_cols: list[str]
) -> tuple[pl.DataFrame, dict[str, int]]:
    """Set rates to 0.0 on zero-death rows (OASIS renders them inconsistently).

    A row with 0 events has a true rate of 0 regardless of denominator; OASIS
    renders such cells as ``0.0``, empty, or occasionally a sentinel. Rows
    with a POSITIVE rate but zero deaths would be a real contradiction and
    raise. Run BEFORE :func:`null_sentinel_rates` so suppression masking only
    counts rows with actual (1+) events.
    """
    counts: dict[str, int] = {}
    present = [c for c in rate_cols if c in df.columns]
    contradictions = df.filter(
        pl.col("deaths") == 0,
        pl.any_horizontal(pl.col(c) > 0 for c in present),
    )
    if contradictions.height:
        raise ValueError(
            f"{contradictions.height} zero-death row(s) carry a positive rate "
            f"— bronze contradiction, investigate:\n{contradictions.head(10)}"
        )
    for col in present:
        changed = df.filter(
            pl.col("deaths") == 0,
            pl.col(col).is_null() | (pl.col(col) != 0.0),
        ).height
        counts[col] = changed
        df = df.with_columns(
            pl.when(pl.col("deaths") == 0)
            .then(pl.lit(0.0))
            .otherwise(pl.col(col))
            .alias(col)
        )
    return df, counts


def null_sentinel_rates(
    df: pl.DataFrame, rate_cols: list[str]
) -> tuple[pl.DataFrame, dict[str, dict[str, object]]]:
    """NULL every negative rate value (OASIS suppression/N-A sentinels).

    ``-5`` = rate suppressed (fewer than 5 events); ``-2`` = not applicable
    (no population denominator); other negative codes are documented by the
    tool and may appear on refresh — ANY negative rate is a sentinel, never a
    real rate. Returns per-column mask stats (count, distinct sentinel
    values, affected years) for manifest recording.
    """
    stats: dict[str, dict[str, object]] = {}
    for col in (c for c in rate_cols if c in df.columns):
        masked = df.filter(pl.col(col) < 0)
        if masked.height:
            stats[col] = {
                "count": masked.height,
                "sentinels": sorted(masked[col].unique().to_list()),
                "years": sorted(masked["year"].unique().to_list()),
            }
        df = df.with_columns(
            pl.when(pl.col(col) < 0).then(None).otherwise(pl.col(col)).alias(col)
        )
    return df, stats
