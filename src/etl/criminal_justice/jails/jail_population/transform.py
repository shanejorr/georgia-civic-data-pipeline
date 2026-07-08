"""Transform bronze GSA monthly jail-report HTML pages into a gold fact table.

Source: Georgia Sheriffs' Association monthly county jail report
(georgiasheriffs.org/jail-report) — a voluntary self-reported survey of all
159 Georgia county jails: total inmates, capacity, and a four-way custody
breakdown (state-sentenced, awaiting trial, county-sentenced, other), per
county per month, 2007-11 onward.

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **Grain: county x year x month (+ a statewide rollup).** ``month`` is a
  string categorical ("01"-"12") per the criminal_justice domain convention,
  so it joins the grain instead of being read as a metric.
- **Coverage flag, never imputation (domain rule).** The survey is voluntary
  and coverage collapses in recent months (159 counties reporting in 2019-03
  vs 59 in 2026-06). Every county appears in every month's table; a
  ``reporting_status`` categorical records how: ``reported`` (submitted
  values), ``no_jail`` (county submitted "no jail", literal zeros at source),
  ``not_reported`` (row published blank -> all metrics NULL).
- **Status is derived from the six COUNT cells only.** The structure doc's
  "all 11 value cells empty" rule undercounts: in many months the percent
  cells of blank rows render as literal "0%" while every count cell is empty
  (e.g. Baker 2021-07). Verified against all 222 files: a row with all six
  count cells blank is a non-reporting county; rows with some-but-not-all
  blank count cells (14 rows, e.g. Macon 2018-07, Dougherty 2022) are
  reported rows with individually missing cells -> those cells stay NULL.
- **Percent columns are dropped, never parsed (structure doc ETL #4).** All
  six bronze percent columns are corrupted at source (x100 rendering in 38
  months, inconsistent rounding elsewhere) and are pure derivations of the
  count columns. Consumers can recompute e.g. capacity utilization as
  total_inmates / jail_capacity.
- **Isolated single-month NO JAIL flags are reclassified to not_reported
  (structure doc ETL #2).** The " - NO JAIL" suffix legitimately toggles over
  the years (jails open/close: Stewart, Talbot, Clinch, Treutlen...), but the
  source also publishes one-off erroneous flags (Richmond 2024-06, Fayette
  2024-07, Burke 2024-10, ... each a single zero-inmate month for a county
  that plainly has a jail). Rule, applied uniformly to the whole archive: a
  no_jail month whose immediately adjacent archive months for the same county
  are both ``reported`` is treated as non-reporting — status becomes
  ``not_reported`` and the false zeros become NULL. 58 county-months match
  (all of the structure doc's listed erroneous flags, plus analogous cases —
  concentrated 2023-05 onward). Recorded via ``record_reclassified``.
  Multi-month NO JAIL runs (real closures) are untouched.
- **2018-09 Mac*/Mc* component misalignment is repaired (structure doc ETL
  #5).** In 2018-09 the four component columns of Macon / Madison / Marion /
  McDuffie / McIntosh are shifted by a source-side sort mismatch (components
  generated under Mc-before-Mac ordering, totals/capacity under the table's
  Mac-before-Mc ordering). Evidence is exact: each published component set
  sums precisely to the OTHER county's published total (Macon's components
  sum to 107 = McDuffie's total; Madison's to 79 = McIntosh's; Marion's to
  25 = Macon's; McDuffie's to 110 = Madison's; McIntosh's to 21 = Marion's).
  The transform verifies all five identities exactly and reassigns the
  component values to their owning counties (totals and capacity are aligned
  and untouched); it hard-fails if the bronze ever stops matching. Recorded
  via ``record_reclassified``.
- **S4b masks: impossible inmate counts -> NULL.** Two shapes exist in the
  archive, both NULLed via ``_null_impossible_counts`` + ``record_masked``
  (row and every other cell preserved; the contract's auto-derived
  non-negative range checks stay the enforceable guard):
  (1) the single non-integer count — Madison 2019-05 state-sentenced = 0.01,
  which the source's own TOTALS row excludes (sums to the integer 2451); and
  (2) four negative counts — Pulaski 2024-03 state-sentenced = -3, Long
  2025-07 county-sentenced = -1, Long 2025-08 other = -2, Charlton 2026-02
  other = -2 (verified verbatim in bronze). A headcount cannot be fractional
  or negative.
- **Additivity is documented, not enforced (structure doc ETL #5).** Through
  2023-05, total = state_sentenced + awaiting_trial + county_sentenced +
  other holds for effectively all rows (~14 sporadic violations in 16
  years); from 2023-06 onward the identity fails for ~70%% of reporting
  counties every month (median gap 13). All five counts are kept exactly as
  reported; no component is ever derived from the identity and no quality
  check asserts it.
- **TOTALS row = parse check + the state row's bronze source.** The county
  table's TOTALS row is verified against the parsed column sums for every
  file and every count column (tolerance 0.5, absorbing the 2019-05
  0.01 artifact) — a parse-drift tripwire. State rows are then rebuilt by
  summing the county rows (identical by the verified identity, and kept
  consistent by an authored quality check). The statewide summary table is
  NOT used: it can disagree with the county table (2026-06: summary 12,750
  vs county-table 12,664) and the county table is internally consistent.
- **Statewide numbers reflect reporters only (structure doc ETL #8).** State
  rows carry ``counties_reporting`` (count of counties that submitted that
  month, including no-jail counties — the source's "Number of Jails
  Reporting" concept) so consumers can separate population change from
  coverage change. NULL on county rows.
- **No suppression.** Blank cells mean "county did not report", not
  suppression; ``suppressed_to_null=False`` and per-column ``null_meaning``
  document the voluntary-coverage semantics.
- **Excluded bronze files.** ``annual_totals_*.csv`` (and the chart JS it
  snapshots) is retrieval-date page chrome identical in every archived file,
  never month-specific data — recorded on the manifest as excluded. The
  statewide summary table and all chart arrays are redundant with (or
  inferior to) the county table and are not parsed.
- **Dedup tie-break.** One bronze file per month and one row per county per
  file, so duplicate natural keys are impossible by construction;
  ``deduplicate_by_levels(sort_col="total_inmates")`` remains as the
  documented safety net (prefer the fuller row) should a future refresh add
  an overlapping file. The collision guard runs first and would surface any
  divergent duplicate as a hard error rather than letting dedup pick a
  winner.
"""

import logging
import re
from pathlib import Path

import polars as pl

from src.utils.crosswalks import add_county_fips
from src.utils.metadata import write_data_dictionary
from src.utils.readers import list_bronze_files
from src.utils.transformers import (
    COUNTY_DETAIL_LEVEL_FILES,
    TransformManifest,
    assert_no_natural_key_collisions,
    deduplicate_by_levels,
    detect_era_by_columns,
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

TOPIC = "jail_population"
BRONZE_DIR = Path("data/bronze/criminal_justice/jails/jail_population")
GOLD_DIR = Path("data/gold/criminal_justice/jail_population")
SOURCE_URL = "https://georgiasheriffs.org/jail-report/"

FILENAME_RE = re.compile(r"jail_report_(\d{4})-(\d{2})\.html$")

# The per-county table header — byte-identical across all 222 archive files
# (verified). Any deviation is a source format change and must hard-stop.
EXPECTED_HEADER: list[str] = [
    "Jurisdiction",
    "Number of Inmates in Jail",
    "Jail Capacity",
    "Inmates as % of Capacity",
    "Number of Inmates Sentenced to State",
    "% of Inmates Sentenced to State",
    "Number of Inmates Awaiting Trial in Jail",
    "% of Inmates Awaiting Trial in Jail",
    "Number of Inmates Serving County Sentence",
    "% of Inmates Serving County Sentence",
    "Number of Other Inmates",
    "% of Other Inmates",
]

# Bronze count column -> gold column, in gold output order. Keys are the raw
# header names; data-row cell positions are key positions + 1 (data rows carry
# a leading unnamed row-number cell the header lacks — structure doc ETL #11).
COUNT_COLUMNS: dict[str, str] = {
    "Number of Inmates in Jail": "total_inmates",
    "Jail Capacity": "jail_capacity",
    "Number of Inmates Sentenced to State": "state_sentenced_inmates",
    "Number of Inmates Awaiting Trial in Jail": "awaiting_trial_inmates",
    "Number of Inmates Serving County Sentence": "county_sentenced_inmates",
    "Number of Other Inmates": "other_inmates",
}

# Era detection by column signature. A single era spans the whole archive
# (header byte-identical 2007-11 -> 2026-06); the signature guards against a
# silent future format change rather than distinguishing eras.
ERA_SIGNATURES: dict[str, list[str]] = {
    "gsa_jail_report_v1": [
        "Jurisdiction",
        "Number of Inmates in Jail",
        "Jail Capacity",
    ],
}

# Row-shape markers (bronze side of the reporting_status recode).
MARKER_TO_STATUS: dict[str, str] = {
    "all_count_cells_blank": "not_reported",
    "no_jail_suffix": "no_jail",
    "count_data_present": "reported",
}

COUNTY_METRIC_COLUMNS: list[str] = list(COUNT_COLUMNS.values())

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "county_fips",
    "month",
    "reporting_status",
    *COUNTY_METRIC_COLUMNS,
    "counties_reporting",
    "detail_level",
]

METRIC_COLUMNS: list[str] = [*COUNTY_METRIC_COLUMNS, "counties_reporting"]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "county_fips": pl.Utf8,
    "month": pl.Utf8,
    "reporting_status": pl.Utf8,
    **{c: pl.Int64 for c in METRIC_COLUMNS},
    "detail_level": pl.Utf8,
}

NATURAL_KEYS: list[str] = ["year", "month", "county_fips", "detail_level"]

MONTH_VALUES: list[str] = [f"{m:02d}" for m in range(1, 13)]
REPORTING_STATUS_VALUES: list[str] = ["no_jail", "not_reported", "reported"]

# Tolerance for the per-file TOTALS-row parse check. The county-table TOTALS
# equal the column sums exactly in every file except 2019-05, where the
# source's own total excludes Madison's impossible 0.01 (diff = 0.01).
TOTALS_TOLERANCE = 0.5

# 2018-09 component misalignment: published components on the LEFT county's
# row belong to the RIGHT county (a source-side Mac*/Mc* sort mismatch; see
# module docstring). Keys/values are lowercase base county names.
MISALIGNED_2018_09_SOURCE_TO_OWNER: dict[str, str] = {
    "macon": "mcduffie",
    "madison": "mcintosh",
    "marion": "macon",
    "mcduffie": "madison",
    "mcintosh": "marion",
}
COMPONENT_COLUMNS: list[str] = [
    "state_sentenced_inmates",
    "awaiting_trial_inmates",
    "county_sentenced_inmates",
    "other_inmates",
]

# HTML parsing (server-rendered static tables; regex is sufficient and keeps
# the pipeline dependency-free — the downloader uses the same approach).
_TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_NO_JAIL_SUFFIX_RE = re.compile(r"\s*-\s*NO JAIL\s*$")


# =============================================================================
# HTML parsing
# =============================================================================


def _clean_cell(cell: str) -> str:
    """Strip tags (<strong> on the TOTALS row) and entity spaces from a cell."""
    return _TAG_RE.sub("", cell).replace("&nbsp;", " ").strip()


def _parse_count(cell: str) -> float | None:
    """Parse a count cell: strip thousands commas; blank -> None.

    Returns float (not int) so the single non-integer artifact in the archive
    (Madison 2019-05, 0.01) survives to the explicit S4b mask instead of being
    silently truncated by an integer cast.
    """
    text = cell.replace(",", "").strip()
    return None if text == "" else float(text)


def _parse_county_table(html: str, label: str) -> tuple[list[str], list[list[str]]]:
    """Extract the per-county table (table 1) header + cleaned data rows.

    Table 0 is the statewide summary (not parsed — see module docstring);
    table 1 is the per-county table: a 12-cell header row + 160 data rows
    (159 counties + TOTALS), each with 13 cells (leading row-number cell).
    """
    first = html.find("<table")
    second = html.find("<table", first + 1)
    if second == -1:
        raise ValueError(f"{label}: per-county table not found")
    segment = html[second : html.find("</table>", second)]
    rows = _TR_RE.findall(segment)
    header = [_clean_cell(c) for c in _CELL_RE.findall(rows[0])]
    data_rows = []
    for row in rows[1:]:
        cells = [_clean_cell(c) for c in _CELL_RE.findall(row)]
        if len(cells) != 13:
            raise ValueError(
                f"{label}: expected 13 cells per data row, got {len(cells)}: "
                f"{cells[:3]}"
            )
        data_rows.append(cells)
    return header, data_rows


# =============================================================================
# Per-file transform
# =============================================================================


def _check_totals_row(
    totals_cells: list[str], county_df: pl.DataFrame, label: str
) -> None:
    """Verify the TOTALS row equals the parsed county column sums (parse check).

    The TOTALS row is derived at source and exactly equals the column sums in
    every archive file (structure doc ETL #7) — a mismatch beyond tolerance
    means the parser mis-read the table, which must hard-stop, not pass on.
    """
    for pos, raw_name in enumerate(EXPECTED_HEADER, start=1):
        if raw_name not in COUNT_COLUMNS:
            continue
        published = _parse_count(totals_cells[pos])
        if published is None:
            continue
        parsed_sum = county_df[COUNT_COLUMNS[raw_name]].sum() or 0.0
        if abs(published - parsed_sum) > TOTALS_TOLERANCE:
            raise ValueError(
                f"{label}: TOTALS mismatch for '{raw_name}': published "
                f"{published} vs parsed column sum {parsed_sum}"
            )


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame:
    """Parse one monthly report page into county-grain rows.

    Emits one row per county (159 per file) with float count columns, the raw
    row-shape marker, and the derived reporting_status. The TOTALS row is
    consumed as a parse check (its content re-emerges as the state row built
    in main(), so bronze row accounting counts it: 160 bronze rows/file ->
    159 county + 1 state gold rows/month).
    """
    match = FILENAME_RE.search(path.name)
    if not match:
        raise ValueError(f"Unexpected bronze filename: {path.name}")
    year, month = int(match.group(1)), match.group(2)

    header, data_rows = _parse_county_table(path.read_text(), path.name)
    if header != EXPECTED_HEADER:
        raise ValueError(
            f"{path.name}: county-table header changed — new era? Got: {header}"
        )

    records: list[dict] = []
    totals_cells: list[list[str]] = []
    for cells in data_rows:
        name = cells[1]
        if name == "TOTALS":
            totals_cells.append(cells)
            continue
        record: dict = {"Jurisdiction": name}
        for pos, raw_name in enumerate(EXPECTED_HEADER, start=1):
            if raw_name in COUNT_COLUMNS:
                record[raw_name] = _parse_count(cells[pos])
        records.append(record)
    if len(records) != 159 or len(totals_cells) != 1:
        raise ValueError(
            f"{path.name}: expected 159 county rows + 1 TOTALS row, got "
            f"{len(records)} + {len(totals_cells)}"
        )

    schema = {"Jurisdiction": pl.Utf8, **{c: pl.Float64 for c in COUNT_COLUMNS}}
    df = pl.DataFrame(records, schema=schema)

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{path.name}: no era signature matched {df.columns}")

    # All 161 <tr> of the county table parsed (raw = parsed -> no-op record);
    # any row the regex failed to yield 13 cells for already raised above.
    manifest.record_read_loss(year, path.name, len(data_rows), len(records) + 1)
    manifest.record_file(path, year, era, len(data_rows), header)
    manifest.record_bronze(year, len(data_rows))

    # Row-shape marker from the six COUNT cells only — percent cells of blank
    # rows render "0%" in many months, so they cannot signal non-reporting.
    count_exprs = [pl.col(gold) for gold in COUNT_COLUMNS.values()]
    df = df.rename(COUNT_COLUMNS).with_columns(
        pl.lit(year, dtype=pl.Int32).alias("year"),
        pl.lit(month).alias("month"),
        pl.col("Jurisdiction")
        .str.replace(_NO_JAIL_SUFFIX_RE.pattern, "")
        .str.strip_chars()
        .alias("_county_name"),
        pl.when(pl.all_horizontal([c.is_null() for c in count_exprs]))
        .then(pl.lit("all_count_cells_blank"))
        .when(pl.col("Jurisdiction").str.contains(_NO_JAIL_SUFFIX_RE.pattern))
        .then(pl.lit("no_jail_suffix"))
        .otherwise(pl.lit("count_data_present"))
        .alias("_marker"),
        pl.lit("county").alias("detail_level"),
    )
    df = df.with_columns(
        pl.col("_marker")
        .replace_strict(MARKER_TO_STATUS, default=None)
        .alias("reporting_status"),
        pl.col("_county_name").str.to_lowercase().alias("_county_key"),
    ).drop("Jurisdiction")

    _check_totals_row(totals_cells[0], df, path.name)
    return df


# =============================================================================
# Cross-file repairs and masks
# =============================================================================


def _repair_2018_09_component_misalignment(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Reassign the 2018-09 Mac*/Mc* component values to their owning counties.

    Evidence (verified here before applying, exact to the integer): each of
    the five published component sets sums precisely to the OTHER county's
    published total under the source's sort mismatch. Totals and capacity are
    correctly aligned and untouched. Hard-fails if bronze stops matching.
    """
    block_filter = (
        (pl.col("year") == 2018)
        & (pl.col("month") == "09")
        & pl.col("_county_key").is_in(list(MISALIGNED_2018_09_SOURCE_TO_OWNER))
    )
    block = df.filter(block_filter)
    if block.height != len(MISALIGNED_2018_09_SOURCE_TO_OWNER):
        raise ValueError(
            f"2018-09 misalignment block: expected "
            f"{len(MISALIGNED_2018_09_SOURCE_TO_OWNER)} rows, got {block.height}"
        )

    rows = {r["_county_key"]: r for r in block.to_dicts()}
    for source, owner in MISALIGNED_2018_09_SOURCE_TO_OWNER.items():
        component_sum = sum(rows[source][c] for c in COMPONENT_COLUMNS)
        owner_total = rows[owner]["total_inmates"]
        if component_sum != owner_total:
            raise ValueError(
                "2018-09 misalignment evidence failed: components on "
                f"'{source}' sum to {component_sum}, expected to equal "
                f"'{owner}' total {owner_total} — bronze changed; re-verify"
            )

    repaired = [
        {
            **rows[owner],
            **{c: rows[source][c] for c in COMPONENT_COLUMNS},
        }
        for source, owner in MISALIGNED_2018_09_SOURCE_TO_OWNER.items()
    ]
    manifest.record_reclassified(
        2018,
        len(repaired),
        "2018-09 Mac*/Mc* sort mismatch: component columns reassigned to "
        "owning counties (component sums equal owner totals exactly)",
    )
    logger.warning(
        "Repaired 2018-09 component misalignment for %s",
        sorted(MISALIGNED_2018_09_SOURCE_TO_OWNER),
    )
    return pl.concat(
        [df.filter(~block_filter), pl.DataFrame(repaired, schema=block.schema)]
    )


def _resolve_county_fips(df: pl.DataFrame, manifest: TransformManifest) -> pl.DataFrame:
    """Join county FIPS by name; hard-stop on any unmatched name.

    All 159 base names (after NO JAIL suffix strip; casing variants like
    Mcduffie/McDuffie normalize inside add_county_fips) resolve against the
    global counties dimension — an unmatched name means the source or the
    crosswalk changed and must be fixed via COUNTY_NAME_OVERRIDES, never
    silently NULLed.
    """
    df = add_county_fips(df, "_county_name")
    unmatched = df.filter(pl.col("county_fips").is_null())
    if unmatched.height:
        raise ValueError(
            "Unmatched county name(s) — add to COUNTY_NAME_OVERRIDES: "
            f"{unmatched['_county_name'].unique().sort().to_list()}"
        )
    county_map = {
        row["_county_name"]: row["county_fips"]
        for row in df.select("_county_name", "county_fips").unique().to_dicts()
    }
    manifest.record_categorical(
        column="county_fips",
        map_dict=county_map,
        bronze_series=df["_county_name"],
        gold_series=df["county_fips"],
    )
    return df


def _reclassify_isolated_no_jail(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Treat single-month NO JAIL flags surrounded by reported months as
    non-reporting (structure doc ETL #2).

    A jail does not close for one month and reopen the next; an isolated
    no_jail month between two reported months is an erroneous flag (the
    source publishes several from 2023 on, e.g. Richmond 2024-06). Status
    becomes not_reported and the false zeros become NULL. Adjacency is over
    archive months per county (every county has a row in every file, so
    within-county row order is the archive order; the 2008-01/02 gap makes
    2007-12 and 2008-03 adjacent). Multi-month runs — real closures — never
    match.
    """
    df = df.sort(["_county_key", "year", "month"]).with_columns(
        pl.col("reporting_status").shift(1).over("_county_key").alias("_prev"),
        pl.col("reporting_status").shift(-1).over("_county_key").alias("_next"),
    )
    flag = (
        (pl.col("reporting_status") == "no_jail")
        & (pl.col("_prev") == "reported")
        & (pl.col("_next") == "reported")
    )
    flagged = df.filter(flag)
    if flagged.height:
        for row in flagged.group_by("year").len().sort("year").to_dicts():
            manifest.record_reclassified(
                row["year"],
                row["len"],
                "isolated_single_month_no_jail_flag_treated_as_not_reported",
            )
        sample = (
            flagged.select("_county_name", "year", "month")
            .sort(["year", "month", "_county_name"])
            .to_dicts()
        )
        logger.warning(
            "Reclassified %d isolated single-month NO JAIL flag(s) to "
            "not_reported (false zeros -> NULL): %s",
            flagged.height,
            [f"{r['_county_name']} {r['year']}-{r['month']}" for r in sample],
        )
    df = df.with_columns(
        pl.when(flag)
        .then(pl.lit("not_reported"))
        .otherwise(pl.col("reporting_status"))
        .alias("reporting_status"),
        *[
            pl.when(flag).then(None).otherwise(pl.col(c)).alias(c)
            for c in COUNTY_METRIC_COLUMNS
        ],
    )
    return df.drop("_prev", "_next")


def _null_impossible_counts(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """S4b mask: NULL impossible inmate counts (non-integer or negative).

    A headcount cannot be fractional or negative. The archive carries exactly
    one non-integer (Madison 2019-05, state-sentenced = 0.01, excluded from
    the source's own TOTALS row) and four negatives (Pulaski 2024-03, Long
    2025-07/08, Charlton 2026-02). Masked (not truncated/zeroed) so the
    impossible values never reach gold; the rest of each row is preserved.
    Recorded on the manifest per column and reason.
    """
    for col in COUNTY_METRIC_COLUMNS:
        for reason, bad in [
            (
                "non_integer_inmate_count_published_by_source",
                pl.col(col).is_not_null() & (pl.col(col) != pl.col(col).floor()),
            ),
            (
                "negative_inmate_count_published_by_source",
                pl.col(col).is_not_null() & (pl.col(col) < 0),
            ),
        ]:
            bad_rows = df.filter(bad)
            if bad_rows.height:
                manifest.record_masked(
                    col,
                    bad_rows.height,
                    reason,
                    years=bad_rows["year"].unique().to_list(),
                )
                df = df.with_columns(
                    pl.when(bad).then(None).otherwise(pl.col(col)).alias(col)
                )
    return df


def _record_status_and_month(df: pl.DataFrame, manifest: TransformManifest) -> None:
    """Record the reporting_status and month recodes on the manifest.

    reporting_status: row-shape marker -> status (recorded after the isolated
    NO JAIL reclassification, so gold_values_produced reflect final gold).
    month: filename-derived, identity-mapped — recorded so the review has
    100%% categorical coverage.
    """
    manifest.record_categorical(
        column="reporting_status",
        map_dict=MARKER_TO_STATUS,
        bronze_series=df["_marker"],
        gold_series=df["reporting_status"],
    )
    months_seen = df["month"]
    manifest.record_categorical(
        column="month",
        map_dict={m: m for m in MONTH_VALUES},
        bronze_series=months_seen,
        gold_series=months_seen,
    )


def _build_state_rows(county_df: pl.DataFrame) -> pl.DataFrame:
    """Build one statewide row per month by summing the county rows.

    Equals the source's county-table TOTALS row (verified per file by the
    parse check; the S4b mask and the 2018-09 repair are sum-preserving to
    within the check tolerance). Sums cover reporting counties only —
    counties_reporting (submitters, including no-jail counties) is carried
    so consumers can separate population change from coverage change.
    """
    sum_exprs = [
        pl.when(pl.col(c).count() > 0).then(pl.col(c).sum()).otherwise(None).alias(c)
        for c in COUNTY_METRIC_COLUMNS
    ]
    return (
        county_df.group_by("year", "month")
        .agg(
            *sum_exprs,
            (pl.col("reporting_status") != "not_reported")
            .sum()
            .cast(pl.Int64)
            .alias("counties_reporting"),
        )
        .with_columns(
            pl.lit(None).cast(pl.Utf8).alias("county_fips"),
            pl.lit(None).cast(pl.Utf8).alias("reporting_status"),
            pl.lit("state").alias("detail_level"),
        )
    )


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for jail_population."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every monthly HTML page; record the convenience CSV
    # as deliberately excluded (retrieval-date chrome, not month data).
    frames: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR, extensions=[".html", ".csv"]):
        if path.suffix == ".csv":
            manifest.record_file(path, 2026, "annual_totals_csv_EXCLUDED", 0, [])
            logger.warning(
                "EXCLUDED %s: verbatim snapshot of the annual-totals chart "
                "array — retrieval-date page chrome identical in every "
                "archived page, redundant with the monthly county tables "
                "(structure doc ETL #10)",
                path.name,
            )
            continue
        frames.append(transform_file(path, manifest))
    if not frames:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    county = pl.concat(frames)
    logger.info("Parsed %d county-month rows from %d files", county.height, len(frames))

    # 2. Cross-file repairs, FIPS resolution, reclassification, S4b mask.
    county = _repair_2018_09_component_misalignment(county, manifest)
    county = _resolve_county_fips(county, manifest)
    county = _reclassify_isolated_no_jail(county, manifest)
    county = _null_impossible_counts(county, manifest)
    _record_status_and_month(county, manifest)

    # 3. State rollup from the final county rows, then harmonize + concat.
    states = _build_state_rows(county)
    county = county.drop("_county_name", "_county_key", "_marker")
    combined = pl.concat(
        harmonize_columns([county, states], STANDARD_COLUMNS, TARGET_TYPES)
    )
    logger.info("Combined %d gold-shaped rows", combined.height)

    # 4. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean a parse/aggregation bug and must raise, not be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: one bronze file per month and one row per county per file, so
    # duplicates are impossible by construction; sort_col "total_inmates" is
    # the documented safety net (prefer the fuller row) should a future
    # refresh introduce an overlapping file.
    combined = deduplicate_by_levels(
        combined,
        {
            "county": ["year", "month", "county_fips"],
            "state": ["year", "month"],
        },
        sort_col="total_inmates",
    )

    # 5. Geography nulling (shared domain rules; state rows already NULL).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=CRIMINAL_JUSTICE_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. NULL-rate spikes in recent years are EXPECTED and
    # documented: voluntary-survey coverage collapses from 2019-11 onward
    # (2026-06: 100 of 159 counties not reporting -> NULL metrics).
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning(
            "NULL-rate spikes (documented cause: voluntary-survey coverage "
            "collapse in recent months): %s",
            spike_result.details,
        )
    validate_output(combined, required_non_null=["year", "month", "detail_level"])

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
    ``detail_level`` — the contract's properties (and the validator's schema
    check) follow it.
    """
    not_reported_null = (
        "NULL when the county did not report to the voluntary survey that "
        "month (reporting_status = 'not_reported'), or on the rare reported "
        "row whose individual cell is blank at source. Zeros are real "
        "(no-jail counties report literal zeros)."
    )
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Monthly county jail population survey for all 159 Georgia "
            "counties from the Georgia Sheriffs' Association jail report, "
            "November 2007 onward: total inmates, jail capacity (permanent "
            "beds), and a four-way custody breakdown (state-sentenced "
            "inmates held in county jail, inmates awaiting trial, "
            "county-sentenced inmates, other inmates), plus a statewide "
            "rollup per month with the number of counties reporting. The "
            "survey is voluntary and self-reported: each county-month "
            "carries a reporting_status (reported / no_jail / not_reported), "
            "non-reporting county-months have NULL metrics, and statewide "
            "rows reflect reporting counties only. This is the only "
            "monthly-grain, county-level jail population series available "
            "for Georgia."
        ),
        title="Monthly County Jail Population",
        summary=(
            "Monthly inmate population, capacity, and custody breakdown for "
            "each Georgia county jail, from the Georgia Sheriffs' "
            "Association's voluntary survey (2007 onward)."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": "Calendar year of the report month.",
            },
            {
                "name": "county_fips",
                "type": "string",
                "example": "13121",
                "null_meaning": "NULL on statewide rollup rows.",
                "description": (
                    "5-digit county FIPS code (state prefix 13) of the "
                    "county jail; FK to the counties dimension. NULL on "
                    "statewide rollup rows. Consolidated city-county "
                    "governments appear under their county FIPS."
                ),
            },
            {
                "name": "month",
                "type": "string",
                "nullable": False,
                "example": "06",
                "validValues": MONTH_VALUES,
                "short_description": "Report month (01-12).",
                "description": (
                    "Calendar report month as a zero-padded string ('01'-"
                    "'12'). The survey snapshot for that month; months "
                    "2008-01 and 2008-02 are absent (empty pages in the "
                    "source archive)."
                ),
            },
            {
                "name": "reporting_status",
                "type": "string",
                "validValues": REPORTING_STATUS_VALUES,
                "example": "reported",
                "null_meaning": (
                    "NULL on statewide rollup rows (a statewide aggregate "
                    "has no single reporting status)."
                ),
                "short_description": (
                    "Whether the county submitted data that month: reported, "
                    "no_jail (county operates no jail), or not_reported."
                ),
                "description": (
                    "Coverage flag for the voluntary survey. 'reported': the "
                    "county submitted inmate counts. 'no_jail': the county "
                    "submitted that it operates no jail (metrics are real "
                    "zeros). 'not_reported': the county did not submit that "
                    "month (metrics are NULL; never imputed). Isolated "
                    "single-month no-jail flags surrounded by reporting "
                    "months (58 county-months, concentrated 2023 onward, "
                    "e.g. Richmond 2024-06) are source errors reclassified "
                    "to not_reported. Coverage varies by month — 159 "
                    "counties reporting in 2019-03 vs 59 in 2026-06; use "
                    "counties_reporting on statewide rows."
                ),
            },
            {
                "name": "total_inmates",
                "type": "int64",
                "unit": "count",
                "key_metric": True,
                "example": 2624,
                "null_meaning": not_reported_null,
                "short_description": (
                    "Total inmates held in the county jail during the report month."
                ),
                "description": (
                    "Total inmates in the county jail (statewide rows: sum "
                    "over reporting counties). Through 2023-05 this equals "
                    "the sum of the four custody-breakdown columns for "
                    "effectively all rows; from 2023-06 onward the source's "
                    "breakdown no longer closes the identity for most "
                    "counties (median gap 13 inmates), so the total and the "
                    "components are each served exactly as reported and the "
                    "identity must not be assumed."
                ),
            },
            {
                "name": "jail_capacity",
                "type": "int64",
                "unit": "count",
                "example": 3636,
                "null_meaning": not_reported_null,
                "short_description": "Jail capacity in permanent beds.",
                "description": (
                    "Jail capacity (permanent beds). Statewide rows sum the "
                    "capacity of jails reporting that month. Occupancy can "
                    "exceed capacity — compute utilization as total_inmates "
                    "/ jail_capacity (the source's percent-of-capacity "
                    "column is corrupted at source and is not served)."
                ),
            },
            {
                "name": "state_sentenced_inmates",
                "type": "int64",
                "unit": "count",
                "example": 200,
                "null_meaning": not_reported_null,
                "description": (
                    "Inmates sentenced to state institutions but held in the "
                    "county jail (e.g. awaiting transfer to state prison). "
                    "Two impossible source values are NULLed: Madison "
                    "2019-05 published 0.01 (a fractional headcount, "
                    "excluded from the source's own totals row) and Pulaski "
                    "2024-03 published -3. In 2018-09 the four "
                    "custody-breakdown columns "
                    "for Macon, Madison, Marion, McDuffie, and McIntosh were "
                    "misaligned by a source-side sort mismatch; they are "
                    "reassigned to the correct counties here (each component "
                    "set sums exactly to its owner's published total)."
                ),
            },
            {
                "name": "awaiting_trial_inmates",
                "type": "int64",
                "unit": "count",
                "example": 2042,
                "null_meaning": not_reported_null,
                "short_description": (
                    "Inmates held awaiting trial (pretrial detainees)."
                ),
                "description": (
                    "Inmates awaiting trial in the county jail (pretrial "
                    "detention). Subject to the same 2018-09 five-county "
                    "realignment documented on state_sentenced_inmates."
                ),
            },
            {
                "name": "county_sentenced_inmates",
                "type": "int64",
                "unit": "count",
                "example": 820,
                "null_meaning": not_reported_null,
                "description": (
                    "Inmates serving a county sentence in the county jail. "
                    "One impossible source value is NULLed (Long 2025-07 "
                    "published -1). Subject to the same 2018-09 five-county "
                    "realignment documented on state_sentenced_inmates."
                ),
            },
            {
                "name": "other_inmates",
                "type": "int64",
                "unit": "count",
                "example": 987,
                "null_meaning": not_reported_null,
                "description": (
                    "Inmates in the residual 'other' category (not "
                    "state-sentenced, awaiting trial, or county-sentenced — "
                    "e.g. holds for other jurisdictions). Two impossible "
                    "source values are NULLed (Long 2025-08 and Charlton "
                    "2026-02, each published -2). Subject to the same "
                    "2018-09 five-county realignment documented on "
                    "state_sentenced_inmates."
                ),
            },
            {
                "name": "counties_reporting",
                "type": "int64",
                "unit": "count",
                "example": 143,
                "null_meaning": (
                    "NULL on county rows; populated on statewide rows only."
                ),
                "short_description": (
                    "Number of counties that submitted to the survey that "
                    "month (statewide rows only)."
                ),
                "description": (
                    "Statewide rows only: number of counties that submitted "
                    "to the survey that month (reporting_status 'reported' "
                    "or 'no_jail'; the source's 'Number of Jails Reporting' "
                    "concept). Derived by counting submitting county rows; "
                    "it can differ from the source's published summary item "
                    "13 ('Number of Jails Reporting'), which is unreliable "
                    "(it counts blank rows as reporting and exceeds "
                    "Georgia's 159 counties in three months of 2022). "
                    "Always read alongside statewide totals — "
                    "month-over-month statewide change conflates population "
                    "change with coverage change."
                ),
            },
        ],
        source="Georgia Sheriffs' Association monthly county jail report",
        source_url=SOURCE_URL,
        update_frequency="monthly",
        year_range=year_range,
        suppressed_to_null=False,
        usage=(
            "Attribute the Georgia Sheriffs' Association "
            "(georgiasheriffs.org/jail-report). The survey is voluntary: "
            "filter or group by reporting_status, and interpret statewide "
            "rows together with counties_reporting — a statewide drop can "
            "reflect fewer counties reporting, not fewer inmates. Compute "
            "capacity utilization as total_inmates / jail_capacity. Do not "
            "assume total_inmates equals the sum of the four breakdown "
            "columns after 2023-05."
        ),
        limitations=(
            "State rows have NULL county_fips. Voluntary self-reported "
            "survey: non-reporting county-months carry NULL metrics (never "
            "imputed, never zero-filled), and coverage collapses in recent "
            "months (159 counties reporting in 2019-03 vs 59 in 2026-06) — "
            "statewide rows reflect reporting counties only. The source has "
            "no suppression: NULL means not reported, and zeros are real "
            "(no-jail counties). The source's six percent columns are "
            "corrupted at source (x100 rendering in 38 months) and are "
            "dropped — recompute rates from the count columns. The custody "
            "breakdown stops closing to total_inmates from 2023-06 onward "
            "and the identity is intentionally not enforced. Months 2008-01 "
            "and 2008-02 are missing from the source archive."
        ),
        quality_checks=[
            {
                "name": "not_reported_implies_null_metrics",
                "description": (
                    "A county-month the county did not report can carry no "
                    "inmate counts — all six metrics must be NULL (coverage "
                    "is flagged, never imputed)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE reporting_status = "
                    "'not_reported' AND ("
                    + " OR ".join(f"{c} IS NOT NULL" for c in COUNTY_METRIC_COLUMNS)
                    + ")"
                ),
                "mustBe": 0,
            },
            {
                "name": "no_jail_implies_zero_counts",
                "description": (
                    "A county that submitted 'no jail' holds no inmates and "
                    "has no beds — every non-NULL metric on a no_jail row "
                    "must be 0 (verified across the full archive)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE reporting_status = "
                    "'no_jail' AND ("
                    + " OR ".join(
                        f"COALESCE({c}, 0) != 0" for c in COUNTY_METRIC_COLUMNS
                    )
                    + ")"
                ),
                "mustBe": 0,
            },
            *[
                {
                    "name": f"state_{col}_equals_sum_of_counties",
                    "description": (
                        "The statewide row is built by summing the reporting "
                        "county rows, matching the source county-table "
                        "TOTALS row (verified per file at parse time) — the "
                        f"state {col} must equal the county sum exactly for "
                        "every month. Authored for all six metrics: the "
                        "identity is structural, and a future §4b mask "
                        "applied after the state build would otherwise ship "
                        "a silent divergence."
                    ),
                    "dimension": "consistency",
                    "query": (
                        "SELECT COUNT(*) FROM ("
                        "SELECT year, month, "
                        f"MAX(CASE WHEN county_fips IS NULL THEN {col} "
                        "END) AS state_total, "
                        "SUM(CASE WHEN county_fips IS NOT NULL THEN "
                        f"{col} END) AS county_sum "
                        "FROM {object} GROUP BY year, month"
                        ") WHERE state_total IS NOT NULL AND county_sum IS "
                        "NOT NULL AND state_total != county_sum"
                    ),
                    "mustBe": 0,
                }
                for col in COUNTY_METRIC_COLUMNS
            ],
            {
                "name": "counties_reporting_matches_submitting_rows",
                "description": (
                    "Each month's statewide counties_reporting must equal "
                    "the number of county rows with reporting_status "
                    "'reported' or 'no_jail' (submitters) that month."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, month, "
                    "MAX(CASE WHEN county_fips IS NULL THEN "
                    "counties_reporting END) AS cr, "
                    "SUM(CASE WHEN county_fips IS NOT NULL AND "
                    "reporting_status != 'not_reported' THEN 1 ELSE 0 END) "
                    "AS submitted "
                    "FROM {object} GROUP BY year, month"
                    ") WHERE cr IS NOT NULL AND cr != submitted"
                ),
                "mustBe": 0,
            },
            {
                "name": "counties_reporting_on_state_rows_only",
                "description": (
                    "counties_reporting is a statewide coverage measure — it "
                    "must be NULL on every county row and populated on every "
                    "statewide row."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(county_fips IS NOT NULL AND counties_reporting IS NOT "
                    "NULL) OR (county_fips IS NULL AND counties_reporting "
                    "IS NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "reporting_status_null_iff_state_row",
                "description": (
                    "reporting_status applies to county rows only: NULL on "
                    "every statewide row, non-NULL on every county row."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(county_fips IS NULL AND reporting_status IS NOT NULL) "
                    "OR (county_fips IS NOT NULL AND reporting_status IS "
                    "NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "all_159_counties_every_month",
                "description": (
                    "Every monthly report lists all 159 Georgia counties "
                    "(non-reporters as blank rows), so every (year, month) "
                    "must carry exactly 159 county rows."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, month, "
                    "COUNT(CASE WHEN county_fips IS NOT NULL THEN 1 END) "
                    "AS n_counties "
                    "FROM {object} GROUP BY year, month"
                    ") WHERE n_counties != 159"
                ),
                "mustBe": 0,
            },
            {
                "name": "counties_reporting_within_159",
                "description": (
                    "No month can have more submitters than Georgia has counties."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE counties_reporting > 159"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
