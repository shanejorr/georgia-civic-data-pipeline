"""Transform bronze free_reduced_lunch files into gold facts.

Source: Georgia Insights (GaDOE) "Free and Reduced Price Meal Eligibility"
— the share of K-12 enrolled students eligible for Free or Reduced-price
Lunch (FRL) under the USDA National School Lunch Program, for every Georgia
public school, district/system, and the state, fiscal years 2013-2026. The
single bronze metric ``KK-12 % FRL`` (0-100 scale) becomes the 0-1
``free_reduced_lunch_rate``; the bronze suppression markers become the
``reporting_status`` categorical.

Design decisions (every invariant re-verified against THIS topic's 28
bronze CSVs during authoring — see bronze-data-structure.md):

- **Single era, two files per year (District / School), FY2013-FY2026.**
  All 28 files share one layout: a 4-line preamble (agency, report title,
  "Fiscal Year YYYY Data Report", near-blank spacer), the header on line 5,
  data rows, then a 4-line footer (near-blank spacer + ``Notice:`` + two
  marker-definition lines starting ``-"``). The local reader verifies the
  preamble title, cross-checks the preamble fiscal year against the
  filename year (all 28 agree), verifies the exact 4-line footer shape, and
  parses ONLY the data segment — footer lines are never data rows. Year
  exists only in the filename/preamble; there is no year column.

- **Read loss is measured, not assumed.** Raw data lines = total lines
  minus 4 preamble minus 1 header minus 4 footer (no quoted multi-line
  fields exist in this source); verified raw == parsed for all 28 files.

- **Zero rows are dropped, masked, or reclassified.** Every footer-stripped
  bronze data row maps 1:1 to exactly one gold row (re-verified: no
  duplicate entity keys in any file, no state-row twins — the School files
  carry NO State-Wide Total row, so there is nothing to dedup). Bronze and
  gold manifest counts are equal every year.

- **``reporting_status`` preserves the suppression semantics.** Every rate
  cell in all 28 files is exactly one of: a numeric string, ``*``, ``#``,
  or ``NA`` (re-verified cell-by-cell; no empty cells exist, so
  ``reporting_status`` is never NULL — enforced by a quality check).
  Mapping: numeric → ``reported``; ``*`` → ``suppressed_privacy_band``
  (dual-ended privacy band: the true rate is >95%% or <5%%, so a suppressed
  entity cannot be inferred to sit at either end); ``#`` and ``NA`` →
  ``not_participating`` (entity is not in the FRL program — during the CEP
  era many high-poverty schools show this because meals are universal, so
  it does NOT imply low poverty). ``NA`` genuinely occurs, in FY2016 only
  (2 district + 4 school cells). An unknown future marker would surface as
  an unmapped categorical and fail the manifest write.

- **Publication band [5, 95] verified.** Every published (numeric) rate
  across all 28 files lies within [5.0, 95.0] (global min 5.0, max 95.0) —
  values outside the band are what ``*`` suppresses. After the /100 rescale
  the contract enforces the [0.05, 0.95] band with a float tolerance. No
  section 4b masks: no impossible values exist (nothing outside [0, 100]).

- **State rows come only from the District files.** Each District file
  carries exactly one ``State-Wide Total`` row (blank ``System ID``); the
  reader routes it to detail_level='state' and fails loudly if the count is
  not exactly 1 or if any other row has a blank System ID. Whitespace-only
  System ID maps to NULL BEFORE zfill so it cannot masquerade as district
  "000".

- **Geography**: district codes are 3-digit standard or 7-digit
  charter/state-specialty systems (verified: no other shapes anywhere) —
  zfill(3) pads without truncating. School codes come from the composite
  ``School ID - School Name`` column (`` NNNN - Name``; 100%% pattern
  conformance re-verified on every school row) — split on the first
  `` - ``; zfill(4) is defensive. School codes are NOT globally unique;
  identity is the (district_code, school_code) pair.

- **No demographic column**: the source reports a single overall K-12 rate
  per entity (every row would be 'all'), so per data-cleaning-standards §5
  the column is omitted.

- **Elevated FY2025-FY2026 suppression is real, not a transform artifact.**
  School-level ``*`` counts jump from ~450/year to 896 (FY2025) and 966
  (FY2026) — expanded Community Eligibility Provision coverage pushes more
  entities above the 95%% threshold. The per-year NULL-rate spike check may
  warn for these years; the cause is documented here and in the README.
"""

import logging
import re
from pathlib import Path

import polars as pl

from src.utils.metadata import write_data_dictionary
from src.utils.readers import list_bronze_files
from src.utils.transformers import (
    TransformManifest,
    assert_no_natural_key_collisions,
    deduplicate_by_detail_level,
    export_to_parquet,
    harmonize_columns,
    null_aggregate_geography,
    validate_output,
)
from src.utils.validators import (
    EDUCATION_DOMAIN_CONFIG,
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

TOPIC = "free_reduced_lunch"
BRONZE_DIR = Path("data/bronze/education/georgiainsights/free_reduced_lunch")
GOLD_DIR = Path("data/gold/education/free_reduced_lunch")
SOURCE_URL = "https://georgiainsights.gadoe.org/data-downloads/"

# Filename: "Free Reduced Lunch (FRL) Fiscal Year2013 District.csv" (no space
# before the year). The preamble's line 3 writes the year WITH a space
# ("... - Fiscal Year 2013 Data Report") — two distinct patterns.
FILENAME_PATTERN = re.compile(r"Fiscal Year(\d{4}) (District|School)\.csv$")
PREAMBLE_TITLE = "Free and Reduced Price Meal Eligibility"
PREAMBLE_YEAR_PATTERN = re.compile(r"Fiscal Year (\d{4}) Data Report")

# Lines before the header row (masthead, report title, fiscal-year title,
# near-blank spacer — header is line 5) and trailing footer lines (near-blank
# spacer, "Notice:", and two marker-definition lines starting '-"').
PREAMBLE_LINES = 4
FOOTER_LINES = 4

# Bronze column names AFTER header whitespace stripping (the source header
# writes " System Name" with a leading space).
BRONZE_SYSTEM_ID = "System ID"
BRONZE_SYSTEM_NAME = "System Name"
BRONZE_SCHOOL_COMPOSITE = "School ID - School Name"
BRONZE_RATE = "KK-12 % FRL"

# District-file marker for the one statewide aggregate row per file.
STATE_WIDE_SENTINEL = "State-Wide Total"

# Suppression-marker recoding for `reporting_status`. Numeric cells pass
# through as 'reported' (a derivation, not a lookup); this map covers the
# non-numeric marker space so record_categorical's unmapped guard fires only
# on a genuinely new marker, not on every numeric rate string.
#   `*`  → rate outside the 5%-95% publication band (privacy suppression)
#   `#`  → entity does not participate in the FRL program
#   `NA` → same non-participation semantics as `#` (FY2016 only: 6 cells)
FRL_STATUS_MAP: dict[str, str] = {
    "*": "suppressed_privacy_band",
    "#": "not_participating",
    "NA": "not_participating",
}

REPORTING_STATUS_VALUES: list[str] = sorted({*FRL_STATUS_MAP.values(), "reported"})

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "detail_level",
    "reporting_status",
    "free_reduced_lunch_rate",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "detail_level": pl.Utf8,
    "reporting_status": pl.Utf8,
    "free_reduced_lunch_rate": pl.Float64,
}

METRIC_COLUMNS: list[str] = ["free_reduced_lunch_rate"]

# Natural key for the collision guard: the entity key per detail level.
# reporting_status is intentionally NOT a key — it is derived 1:1 from the
# rate cell, so it is checked as a "metric" for divergence instead (two rows
# sharing an entity key but disagreeing on status must raise, not dedup).
NATURAL_KEYS: list[str] = ["year", "district_code", "school_code", "detail_level"]


# =============================================================================
# Bronze reading
# =============================================================================


def _read_bronze_csv(path: Path, year: int) -> tuple[pl.DataFrame, dict]:
    """Read one bronze CSV: verify preamble + footer, parse the data segment.

    The shared ``read_bronze_file`` cannot skip the 4-line GaDOE preamble or
    the 4-line footer, so this local reader handles both: it verifies the
    line-2 report title, cross-checks the line-3 fiscal year against the
    filename year (a mismatch means a misnamed or mis-filled file — fail
    loudly), verifies the exact footer shape (near-blank spacer, "Notice:",
    two marker-definition lines), and parses only the data segment as Utf8
    (``infer_schema_length=0`` — preserves the whitespace state sentinel,
    code strings, and the ``*``/``#``/``NA`` markers).

    Returns:
        ``(df, loss)`` — the all-Utf8 frame with stripped headers and a
        read-loss dict. Raw rows are counted from the file's data lines
        (total minus preamble minus header minus footer); this source has
        no quoted multi-line fields, so raw == parsed is expected (verified
        for all 28 files).
    """
    lines = path.read_bytes().decode("utf-8").splitlines()
    title_line = lines[1] if len(lines) > 1 else ""
    if PREAMBLE_TITLE not in title_line:
        raise ValueError(
            f"{path.name}: preamble line 2 does not contain the expected "
            f"title {PREAMBLE_TITLE!r}: {title_line[:100]!r}"
        )
    report_line = lines[2] if len(lines) > 2 else ""
    preamble_match = PREAMBLE_YEAR_PATTERN.search(report_line)
    if preamble_match is None or int(preamble_match.group(1)) != year:
        raise ValueError(
            f"{path.name}: preamble year disagrees with filename year "
            f"{year}: {report_line[:100]!r}"
        )

    # The footer must be exactly the 4 known lines — anything else means the
    # layout drifted and the slice below would eat data rows (or keep junk).
    footer = lines[-FOOTER_LINES:]
    footer_ok = (
        len(lines) > PREAMBLE_LINES + 1 + FOOTER_LINES
        and footer[0].strip() == ""
        and footer[1].strip() == "Notice:"
        and footer[2].startswith('-"*"')
        and footer[3].startswith('-"NA"')
    )
    if not footer_ok:
        raise ValueError(
            f"{path.name}: last {FOOTER_LINES} lines do not match the "
            f"expected footer shape: {footer!r}"
        )

    body = "\n".join(lines[PREAMBLE_LINES:-FOOTER_LINES]) + "\n"
    df = pl.read_csv(body.encode("utf-8"), infer_schema_length=0)
    # Strip the source's leading header whitespace (" System Name") so
    # downstream code uses clean names.
    df = df.rename({c: c.strip() for c in df.columns})

    raw_rows = len(lines) - PREAMBLE_LINES - 1 - FOOTER_LINES  # minus header
    loss = {"raw_rows": raw_rows, "parsed_rows": df.height, "format": "csv"}
    return df, loss


# =============================================================================
# Shared rate / reporting_status derivation
# =============================================================================


def _require_columns(df: pl.DataFrame, required: set[str], context: str) -> None:
    """Fail loudly when an expected bronze column is missing.

    An unmatched source column would silently become NULL in gold — the
    highest-frequency class of data-loss bug — so absence raises.
    """
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(
            f"{context}: expected bronze column(s) missing: {missing}. "
            f"Present: {sorted(df.columns)}"
        )


def _with_rate_and_status(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Derive ``free_reduced_lunch_rate`` and ``reporting_status``.

    The bronze cell is one of: numeric string, ``*``, ``#``, ``NA``
    (verified — no empty cells exist in any of the 28 files). The rate is
    rescaled 0-100 → 0-1 per data-cleaning-standards section 4; the three
    markers become NULL rate plus a distinguishing ``reporting_status``.
    An unknown marker falls through to NULL status AND shows up as an
    unmapped categorical, which fails the manifest write — new markers
    cannot slip through silently.
    """
    raw = pl.col(BRONZE_RATE)
    stripped = raw.str.strip_chars()
    numeric = stripped.cast(pl.Float64, strict=False)
    df = df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        (numeric / 100.0).alias("free_reduced_lunch_rate"),
        pl.when(raw.is_null())
        .then(None)
        .when(numeric.is_not_null())
        .then(pl.lit("reported"))
        .when(stripped == "*")
        .then(pl.lit("suppressed_privacy_band"))
        .when(stripped.is_in(["#", "NA"]))
        .then(pl.lit("not_participating"))
        .otherwise(None)
        .cast(pl.Utf8)
        .alias("reporting_status"),
    )

    # Record the recoding on the marker rows only: numeric cells pass
    # through as 'reported' (derivation, not recoding), so feeding them to
    # the unmapped guard would flag every distinct rate string. The guard
    # still fires on any genuinely new non-numeric marker.
    marker_series = df.select(
        pl.when(numeric.is_null() & raw.is_not_null())
        .then(stripped)
        .otherwise(None)
        .alias("status_bronze")
    )["status_bronze"]
    manifest.record_categorical(
        column="reporting_status",
        map_dict=FRL_STATUS_MAP,
        bronze_series=marker_series,
        gold_series=df["reporting_status"],
    )
    return df


# =============================================================================
# Per-file transforms (single era)
# =============================================================================


def _transform_district_frame(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Transform one District bronze file into district + state gold rows.

    Each District file carries exactly one ``State-Wide Total`` row (blank
    ``System ID``) — the ONLY source of the state-level rate in this topic
    — plus one row per district/system.
    """
    context = f"{TOPIC} {year} District"
    _require_columns(df, {BRONZE_SYSTEM_ID, BRONZE_SYSTEM_NAME, BRONZE_RATE}, context)

    is_state = pl.col(BRONZE_SYSTEM_NAME).str.strip_chars() == STATE_WIDE_SENTINEL
    blank_sid = pl.col(BRONZE_SYSTEM_ID).str.strip_chars().str.len_chars() == 0

    # Structural invariants (verified for all 14 District files): exactly one
    # statewide row per file, it is the only blank-System-ID row, and every
    # other System ID is a 3-digit standard or 7-digit charter/specialty
    # code. A violation means mis-routed detail levels — fail loudly.
    n_state = df.filter(is_state).height
    n_blank = df.filter(blank_sid).height
    if n_state != 1 or n_blank != 1 or df.filter(is_state & ~blank_sid).height:
        raise ValueError(
            f"{context}: expected exactly one State-Wide Total row with a "
            f"blank System ID; found {n_state} state row(s) and {n_blank} "
            f"blank-System-ID row(s)"
        )
    bad_codes = df.filter(
        ~blank_sid
        & ~pl.col(BRONZE_SYSTEM_ID).str.strip_chars().str.contains(r"^(\d{3}|\d{7})$")
    )
    if bad_codes.height:
        raise ValueError(
            f"{context}: {bad_codes.height} System ID value(s) that are "
            f"neither 3- nor 7-digit codes: "
            f"{bad_codes[BRONZE_SYSTEM_ID].head(5).to_list()}"
        )

    df = df.with_columns(
        # Whitespace state sentinel -> NULL BEFORE zfill (otherwise zfill
        # would mint a phantom district "000"); zfill(3) pads 3-digit
        # standard codes and passes 7-digit codes through untouched.
        pl.when(is_state)
        .then(None)
        .otherwise(pl.col(BRONZE_SYSTEM_ID).str.strip_chars())
        .str.zfill(3)
        .alias("district_code"),
        # District files carry no school rows; uniform NULL keeps the shared
        # education key-column shape.
        pl.lit(None).cast(pl.Utf8).alias("school_code"),
        pl.when(is_state)
        .then(pl.lit("state"))
        .otherwise(pl.lit("district"))
        .alias("detail_level"),
    )

    df = _with_rate_and_status(df, year, manifest)
    return df.select(STANDARD_COLUMNS)


def _transform_school_frame(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Transform one School bronze file into school gold rows.

    School files carry no statewide row (verified: zero blank-System-ID
    rows in all 14 files). The composite ``School ID - School Name`` packs
    `` NNNN - Name``; the leading 4-digit code is extracted (anchored on
    the first `` - `` separator, so hyphens inside school names are safe).
    """
    context = f"{TOPIC} {year} School"
    _require_columns(
        df,
        {BRONZE_SYSTEM_ID, BRONZE_SYSTEM_NAME, BRONZE_SCHOOL_COMPOSITE, BRONZE_RATE},
        context,
    )

    # No statewide row exists in School files; a blank System ID here would
    # mean a silent NULL district_code on a school row — fail loudly.
    blank_sid = df.filter(
        pl.col(BRONZE_SYSTEM_ID).str.strip_chars().str.len_chars() == 0
    )
    if blank_sid.height:
        raise ValueError(
            f"{context}: {blank_sid.height} unexpected blank-System-ID "
            f"row(s) (School files carry no statewide row)"
        )
    # Every row must carry the " NNNN - Name" composite prefix (verified
    # 100% conformance) — an unparseable value would silently produce a
    # NULL school_code, so it fails loudly instead.
    bad_names = df.filter(
        ~pl.col(BRONZE_SCHOOL_COMPOSITE).str.contains(r"^\s*\d{4} - ")
    )
    if bad_names.height:
        raise ValueError(
            f"{context}: {bad_names.height} row(s) whose composite school "
            f"column lacks the 'NNNN - ' prefix: "
            f"{bad_names[BRONZE_SCHOOL_COMPOSITE].head(5).to_list()}"
        )

    df = df.with_columns(
        pl.col(BRONZE_SYSTEM_ID).str.strip_chars().str.zfill(3).alias("district_code"),
        # Anchored extract of the 4-digit code before the first " - ";
        # zfill(4) is defensive (verified already 4 digits everywhere).
        pl.col(BRONZE_SCHOOL_COMPOSITE)
        .str.extract(r"^\s*(\d{4}) - ", 1)
        .str.zfill(4)
        .alias("school_code"),
        pl.lit("school").alias("detail_level"),
    )

    df = _with_rate_and_status(df, year, manifest)
    return df.select(STANDARD_COLUMNS)


# =============================================================================
# File dispatcher
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read and transform one bronze CSV (read-loss accounted)."""
    match = FILENAME_PATTERN.search(path.name)
    if match is None:
        raise ValueError(
            f"Unexpected bronze filename (no 'Fiscal YearYYYY "
            f"District|School.csv' suffix): {path.name}"
        )
    year = int(match.group(1))
    level_source = match.group(2)

    df, loss = _read_bronze_csv(path, year)
    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])
    # Single-era topic; the era name documents why there is no dispatch.
    manifest.record_file(
        path, year, "era_1_2013_2026_kk12_pct_frl", df.height, df.columns
    )
    manifest.record_bronze(year, df.height)

    if df.height == 0:
        logger.warning("Year %d: bronze file %s is empty, skipping", year, path.name)
        return None
    logger.info(
        "Processing %s (year %d, %s, %d rows)",
        path.name,
        year,
        level_source,
        df.height,
    )
    if level_source == "District":
        return _transform_district_frame(df, year, manifest)
    return _transform_school_frame(df, year, manifest)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for this topic."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file (two per year: District, School).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR, extensions=[".csv"]):
        result = transform_file(path, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize dtypes across files and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)
    logger.info("Combined %d rows across %d files", combined.height, len(all_dfs))

    # 3. Collision guard BEFORE dedup. No duplicate entity keys exist in any
    # bronze file and no entity appears in two files for one year (verified:
    # the statewide row lives only in the District file), so the guard is
    # expected to find nothing. reporting_status rides along as a "metric"
    # so same-key rows diverging only in status (both NULL rate) would also
    # raise rather than be silently deduped.
    assert_no_natural_key_collisions(
        combined,
        natural_keys=NATURAL_KEYS,
        metric_cols=[*METRIC_COLUMNS, "reporting_status"],
    )

    # Tie-break: a no-op by construction (zero duplicate keys, see guard
    # above); sort_col states the preference explicitly anyway — a row with
    # a reported (higher) rate would win over a NULL-rate twin.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code"],
        district_keys=["year", "district_code"],
        state_keys=["year"],
        sort_col="free_reduced_lunch_rate",
    )

    # 4. Geography nulling (shared domain rules — transform and validator
    # read the same dict, so they cannot disagree). No section 4b masks:
    # every published rate lies in [5.0, 95.0] bronze-scale (verified), so
    # nothing is impossible after the /100 rescale.
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. reporting_status is required non-null because every
    # bronze rate cell carries a value or a marker (verified) — a NULL means
    # a parse bug, not missing data. NULL-rate spikes in FY2025/FY2026 are
    # expected (expanded CEP coverage drives `*` suppression up).
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(
        combined,
        required_non_null=["year", "detail_level", "reporting_status"],
    )

    # 5. Manifest stats on the FINAL DataFrame, then export.
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(combined, GOLD_DIR, STANDARD_COLUMNS)
    manifest.write(GOLD_DIR)

    # 6. Contract + README from the in-code column declaration.
    _emit_contract_and_readme(
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


def _emit_contract_and_readme(year_range: tuple[int, int]) -> None:
    """Emit the ODCS contract and gold README via ``write_data_dictionary``.

    The column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level`` — the contract properties (and the validator's schema
    check) follow it.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Georgia Insights (GaDOE) Free and Reduced Price Meal "
            "Eligibility — the share of K-12 enrolled students eligible "
            "for Free or Reduced-price Lunch (FRL) under the USDA National "
            "School Lunch Program, for every Georgia public school, "
            "district/system, and the state, fiscal years 2013-2026. A "
            "widely used proxy for student economic disadvantage. "
            "Eligibility is income-based per the USDA Federal Income "
            "Eligibility Guidelines: free meals at or below 130%% of the "
            "federal poverty level, reduced-price between 130%% and 185%%; "
            "the combined FRL rate counts students up to the 185%% "
            "threshold. This is the broad income/application-based "
            "eligibility measure — the automatic categorical-eligibility "
            "SUBSET (students certified without an application via "
            "SNAP/TANF/foster/homeless/migrant/Medicaid) is the companion "
            "topic direct_certification."
        ),
        title="Free and Reduced-Price Lunch Eligibility",
        summary=(
            "Share of K-12 students eligible for free or reduced-price "
            "lunch, a proxy for economic disadvantage, per school, "
            "district, and state, 2013-2026."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Georgia fiscal year = ending calendar year of the "
                    "school year (2024 = the 2023-2024 school year; "
                    "Georgia FY ends June 30). Sourced from the bronze "
                    "filename, cross-checked against each file's preamble."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "GaDOE district/system code (FK to districts "
                    "dimension). Standard county/city systems are 3-digit "
                    "zero-padded codes; state-specialty and charter "
                    "systems use 7-digit codes. NULL for state-level rows."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "1050",
                "description": (
                    "4-digit GaDOE school code, extracted from the bronze "
                    "composite `School ID - School Name` column (FK to "
                    "schools dimension, composite with district_code — the "
                    "same school_code can appear in multiple districts). "
                    "NULL for district- and state-level rows."
                ),
            },
            {
                "name": "reporting_status",
                "type": "string",
                "example": "reported",
                "validValues": REPORTING_STATUS_VALUES,
                "short_description": (
                    "Why the rate is present or NULL: reported, privacy-"
                    "suppressed (rate >95% or <5%), or not participating."
                ),
                "description": (
                    "Why `free_reduced_lunch_rate` is present or NULL. "
                    "`reported` — bronze carried a numeric rate; "
                    "`suppressed_privacy_band` — bronze `*` (the true rate "
                    "is greater than 95%% or less than 5%%, hidden by the "
                    "source; dual-ended, so a suppressed entity cannot be "
                    "inferred to sit at either end); `not_participating` — "
                    "bronze `#` or `NA` (entity does not participate in "
                    "the FRL program; under the Community Eligibility "
                    "Provision many high-poverty schools fall here because "
                    "meals are universal rather than means-tested, so it "
                    "does NOT imply low poverty). Never NULL in FY2013-"
                    "FY2026 bronze (every rate cell carries a value or a "
                    "marker — enforced by a quality check); a NULL would "
                    "mean a genuinely missing bronze cell."
                ),
            },
            {
                "name": "free_reduced_lunch_rate",
                "type": "float64",
                "unit": "proportion",
                "key_metric": True,
                "example": 0.6889,
                "short_description": (
                    "Share of K-12 students eligible for free/reduced-price "
                    "lunch on a 0-1 scale; NULL means suppressed or not "
                    "participating (see reporting_status)."
                ),
                "description": (
                    "Share of K-12 enrolled students eligible for Free or "
                    "Reduced-price Lunch (0-1 decimal scale; bronze "
                    "`KK-12 %% FRL` divided by 100). NULL when the source "
                    "suppressed the rate (`*`) or the entity does not "
                    "participate (`#`/`NA`) — see `reporting_status` for "
                    "which. Every published rate lies within the source's "
                    "[0.05, 0.95] publication band."
                ),
            },
        ],
        source="Georgia Insights (GaDOE) — Free and Reduced Price Meal Eligibility",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        limitations=(
            "free_reduced_lunch_rate is NULL whenever the source did not "
            "publish a numeric rate; the reporting_status column records "
            "WHY. Bronze `*` (reporting_status='suppressed_privacy_band') "
            "is a dual-ended PRIVACY suppression — it means the rate was "
            "greater than 95% or less than 5%, so a suppressed entity "
            "cannot be inferred to be at either the high or the low end. "
            "Consequently, every published (non-null) rate falls within "
            "the [0.05, 0.95] band. Bronze `#` (and the rare `NA`, FY2016 "
            "only) (reporting_status='not_participating') means the entity "
            "does not participate in the FRL program at all — under the "
            "Community Eligibility Provision (CEP), many high-poverty "
            "schools show `#` because meals are universal rather than "
            "means-tested, so a `#` does NOT imply low poverty. State rows "
            "come exclusively from the District CSV's `State-Wide Total` "
            "row; School files carry no state aggregate. FY2025-FY2026 "
            "show substantially elevated `*` suppression (expanded CEP "
            "coverage). This is the broad income-based FRL eligibility "
            "measure (free <=130% FPL, reduced 130-185%); the automatic "
            "categorical subset is the companion direct_certification "
            "topic."
        ),
        notes=[
            (
                "Single-metric topic: one overall K-12 FRL rate per "
                "entity per year — no demographic breakdowns, so there is "
                "no demographic column."
            ),
            (
                "The `NA` non-participation marker occurs only in FY2016 "
                "(2 district + 4 school cells); all other years use `#`. "
                "Both map to reporting_status='not_participating'."
            ),
            (
                "School-level `*` suppression jumps from ~450/year to 896 "
                "(FY2025) and 966 (FY2026) as expanded Community "
                "Eligibility Provision coverage pushes more entities above "
                "the 95% publication threshold — expect elevated NULL "
                "rates in those years."
            ),
            (
                "Every footer-stripped bronze data row maps 1:1 to one "
                "gold row: no drops, no masks, no dedup losses "
                "(bronze carries no duplicate entity keys and no "
                "state-row twins)."
            ),
        ],
        quality_checks=[
            {
                "name": "reported_status_has_rate",
                "description": (
                    "Rows marked reporting_status='reported' must carry a "
                    "non-null free_reduced_lunch_rate."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE reporting_status "
                    "= 'reported' AND free_reduced_lunch_rate IS NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "suppressed_privacy_band_has_null_rate",
                "description": (
                    "Rows marked reporting_status='suppressed_privacy_band' "
                    "must have a NULL free_reduced_lunch_rate (the source "
                    "hid the rate)."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE reporting_status "
                    "= 'suppressed_privacy_band' AND "
                    "free_reduced_lunch_rate IS NOT NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "not_participating_has_null_rate",
                "description": (
                    "Rows marked reporting_status='not_participating' must "
                    "have a NULL free_reduced_lunch_rate (entity is not in "
                    "the FRL program)."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE reporting_status "
                    "= 'not_participating' AND free_reduced_lunch_rate IS "
                    "NOT NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "reporting_status_never_null",
                "description": (
                    "reporting_status is never NULL: every bronze rate "
                    "cell in FY2013-FY2026 carries a numeric value or one "
                    "of the `*`/`#`/`NA` markers (verified cell-by-cell "
                    "across all 28 files). A NULL would mean a genuinely "
                    "missing bronze cell — a new source behavior worth "
                    "investigating."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE reporting_status IS NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "free_reduced_lunch_rate_within_publication_band",
                "description": (
                    "Every published (non-null) rate falls within the "
                    "source publication band [0.05, 0.95]; values outside "
                    "the band are privacy-suppressed to NULL (verified: "
                    "bronze global min 5.0, max 95.0). A small float "
                    "tolerance absorbs the /100 rescale representation of "
                    "0.95."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "free_reduced_lunch_rate IS NOT NULL AND "
                    "(free_reduced_lunch_rate < 0.05 - 1e-6 OR "
                    "free_reduced_lunch_rate > 0.95 + 1e-6)"
                ),
                "mustBe": 0,
            },
            {
                "name": "one_state_row_per_year",
                "description": (
                    "Every year publishes exactly one state-level row — "
                    "each District bronze file carries exactly one "
                    "State-Wide Total row, and School files carry none "
                    "(verified for all 14 years)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT (SELECT COUNT(DISTINCT year) FROM {object}) - "
                    "(SELECT COUNT(*) FROM (SELECT year FROM {object} "
                    "WHERE district_code IS NULL AND school_code IS NULL "
                    "GROUP BY year HAVING COUNT(*) = 1) t)"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
