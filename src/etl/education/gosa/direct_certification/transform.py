"""Transform bronze direct_certification files into one multi-level gold table.

Source: Governor's Office of Student Achievement (GOSA) — annual direct
certification rate for Georgia public schools and districts, fiscal years
2014-2024. Direct certification identifies K-12 students automatically eligible
for free school meals through enrollment in means-tested programs (SNAP, TANF,
FDPIR, Medicaid), or because the student is in foster care (from FY2018),
homeless, migrant, runaway, or a Head Start enrollee — without a household
application. The headline metric is the share of K-12 students directly
certified; from FY2020 the source also publishes the underlying numerator
(directly certified student count) and denominator (K-12 enrollment).

**This topic merges two formerly separate GOSA download families** —
``direct_certification_school`` (one row per school) and
``direct_certification_district`` (one row per district/system, plus a
statewide aggregate) — into a single star-schema fact table with three detail
levels (``schools`` / ``districts`` / ``states``). The two families are
distinct downloads with identical metric semantics; the only structural
differences are the per-school columns (school family) and the statewide
``SYSTEM_ID=999`` row (district family). Both families share the same
four-era column evolution and the same metric vocabulary, so a single
transform body handles both behind a per-family dispatch keyed on the
``_school_`` / ``_district_`` infix in each filename.

Detail levels in the merged fact table (``detail_level`` is implicit in the
parquet filename per ``src/etl/education/CLAUDE.md`` and is dropped on export):

- ``school``  — both geography keys populated (school family rows).
- ``district`` — ``district_code`` populated, ``school_code`` NULL (district
  family standard/charter/state-agency/State-Schools rows).
- ``state``   — both geography keys NULL (district family ``SYSTEM_ID=999``
  "State of Georgia" row; published 2022-2024 only).

Because ``detail_level`` is not a stored column, the merged quality checks
discriminate detail by the geography-key NULL pattern in the unioned table
(school ⟺ ``school_code IS NOT NULL``; district ⟺ ``school_code IS NULL AND
district_code IS NOT NULL``; state ⟺ ``district_code IS NULL``).

Design decisions (carried verbatim from the two source transforms — the merge
changes routing and the contract, never the per-file value handling):

- **Four eras per family, detected by column signature, never by year range.**
  Era 1 (2014, CSV): year column ``SCHOOL_YEAR``. Era 2 (2015-2016, CSV):
  ``FISCAL_YEAR``. Era 3 (2017-2019, .xls): the school family adds a redundant
  ``sys_sch`` column (``str(SYSTEM_ID)+str(SCHOOL_ID)`` — dropped). Era 4
  (2020-2024, .xls): adds ``K12_POVERTY_STUDENT_CT`` / ``K12_STUDENT_COUNT``.
- **2017/2018 methodology-note header quirk.** Both families' 2017 and 2018
  .xls files carry a free-text note on row 0 with the real header on row 1.
  The school family promotes row 0 in place (content-detected); the district
  family re-reads with pandas ``header=1``. Both are preserved unchanged.
- **Pair-shared metric vocabulary**: bronze ``direct_cert_perc`` (0-100,
  bounded) → ``direct_cert_rate`` (0-1, ``unit: proportion``, ÷100 then
  rounded to 3 decimals — lossless for the published one-decimal precision and
  collapses .xls binary-float artifacts like ``82.400002`` → ``0.824``);
  ``K12_POVERTY_STUDENT_CT`` → ``num_direct_cert_students`` (numerator);
  ``K12_STUDENT_COUNT`` → ``num_k12_students`` (denominator). The K-12
  qualifier is load-bearing — the NSLP K-12 poverty base is not the
  October/March FTE enrollment other topics publish.
- **Counts are NULL before FY2020** in both families — the source did not
  publish them. Pinned by quality checks in both directions.
- **ID formatting**: ``district_code`` = ``SYSTEM_ID`` zfill(3) (pads standard
  3-digit codes; 7-digit charter / State-School codes and 3-digit state-agency
  codes pass through; never truncate). ``school_code`` = ``SCHOOL_ID`` zfill(4)
  (school family only). The school family's redundant ``sys_sch`` is dropped.
- **Statewide aggregate is partial**: the ``SYSTEM_ID=999`` state row exists
  only 2022-2024; no state rows are synthesized for earlier years. The
  published state counts equal the district-detail sums exactly in all three
  years (pinned by ``state_counts_equal_district_sums``).
- **No demographic column** (no era of either family publishes a breakdown);
  **no suppression** anywhere (``suppressed_to_null=False``; every file is
  100% numeric with zero nulls — pinned by ``direct_cert_rate_never_null``);
  **no §4b masks** (every value is physically possible: rate ∈ [0,1] after
  scaling, counts ≥ 0, numerator ≤ denominator in every published row).
- **Two methodology breaks documented, never mutated**: FY2017 excludes foster
  students (FY2018+ include them); FY2024 adds the Medicaid DC-M category,
  roughly doubling certified counts. Recorded in the contract and README; the
  data passes through verbatim.

Judgment calls (non-interactive merge):

1. ``default_detail`` is left to auto-derivation, which resolves to the finest
   level present (``schools``), matching the platform convention (e.g.
   ``attendance``). Not overridden.
2. The cross-level "school rows sum to their district row" invariant is NOT
   asserted: the school and district families are independent GOSA downloads
   whose K-12 bases need not reconcile exactly, and neither source transform
   verified it. Only the within-family ``state == sum(districts)`` identity
   (verified in bronze) is pinned.
3. The rate↔counts reconciliation tolerance is the looser 0.002 of the two
   source transforms, which safely covers worst-case rounding for both
   families (max observed deviation in either is 0.0005).
"""

import logging
from pathlib import Path

import pandas as pd
import polars as pl

from src.utils.metadata import write_data_dictionary
from src.utils.readers import (
    SUPPRESSION_VALUES,
    extract_year_from_filename,
    list_bronze_files,
    read_bronze_file,
)
from src.utils.transformers import (
    TransformManifest,
    assert_no_natural_key_collisions,
    deduplicate_by_detail_level,
    detect_era_by_columns,
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

TOPIC = "direct_certification"
BRONZE_DIR = Path("data/bronze/education/gosa/direct_certification")
GOLD_DIR = Path("data/gold/education/direct_certification")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
# No `demographic` column — neither family publishes any breakdown (§5).
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "direct_cert_rate",
    "num_direct_cert_students",
    "num_k12_students",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "direct_cert_rate": pl.Float64,
    "num_direct_cert_students": pl.Int64,
    "num_k12_students": pl.Int64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = [
    "direct_cert_rate",
    "num_direct_cert_students",
    "num_k12_students",
]

NATURAL_KEYS: list[str] = ["year", "district_code", "school_code", "detail_level"]


# =============================================================================
# SCHOOL FAMILY — readers + era transform (rows: detail_level "school")
# =============================================================================

# Era-detection signatures, most-specific first: Era 4 is a strict superset of
# Era 3 (adds the K12 counts), Era 3 a strict superset of Era 2 (adds sys_sch),
# and Era 1 differs from Era 2 only in the year-column name.
SCHOOL_ERA_SIGNATURES: dict[str, list[str]] = {
    "era_4_2020_2024_xls_counts": [
        "FISCAL_YEAR",
        "sys_sch",
        "SYSTEM_ID",
        "SCHOOL_ID",
        "direct_cert_perc",
        "K12_POVERTY_STUDENT_CT",
        "K12_STUDENT_COUNT",
    ],
    "era_3_2017_2019_xls_sys_sch": [
        "FISCAL_YEAR",
        "sys_sch",
        "SYSTEM_ID",
        "SCHOOL_ID",
        "direct_cert_perc",
    ],
    "era_2_2015_2016_csv_fiscal_year": [
        "FISCAL_YEAR",
        "SYSTEM_ID",
        "SCHOOL_ID",
        "direct_cert_perc",
    ],
    "era_1_2014_csv_school_year": [
        "SCHOOL_YEAR",
        "SYSTEM_ID",
        "SCHOOL_ID",
        "direct_cert_perc",
    ],
}

SCHOOL_ERA_YEAR_COLUMN: dict[str, str] = {
    "era_4_2020_2024_xls_counts": "FISCAL_YEAR",
    "era_3_2017_2019_xls_sys_sch": "FISCAL_YEAR",
    "era_2_2015_2016_csv_fiscal_year": "FISCAL_YEAR",
    "era_1_2014_csv_school_year": "SCHOOL_YEAR",
}

SCHOOL_ERAS_WITH_COUNTS: frozenset[str] = frozenset({"era_4_2020_2024_xls_counts"})


def _promote_note_row_header(df: pl.DataFrame, label: str) -> pl.DataFrame:
    """Promote row 0 to the header when row 0 holds the real column names.

    The 2017 and 2018 school-family .xls files carry a free-text methodology
    note in their first sheet row, so the shared reader parses the note as the
    header and the real header (FISCAL_YEAR, sys_sch, ...) as the first data
    row. Detected by content — no year column among the parsed headers but a
    year column name in row 0 — so the fix is robust to GOSA adding/removing
    the note in a future republication.
    """
    year_columns = {"FISCAL_YEAR", "SCHOOL_YEAR"}
    if year_columns & set(df.columns):
        return df

    first_row = [str(v) if v is not None else "" for v in df.row(0)]
    if not (year_columns & set(first_row)):
        raise ValueError(
            f"{label}: no year column in the header or in row 0 — "
            f"unrecognized layout. Columns: {df.columns}; row 0: {first_row}"
        )

    logger.info(
        "%s: row 0 is the real header (parsed header is a methodology note "
        "row) — promoting and dropping 1 header row",
        label,
    )
    return df.slice(1).rename(dict(zip(df.columns, first_row)))


def _assert_school_id_shapes(df: pl.DataFrame, label: str) -> None:
    """Hard-stop on any school-family geography code the rules do not cover.

    A malformed code would silently mis-derive the fact table's FK keys, so
    district_code must be a 3-digit standard code or a 7-digit state-charter
    authorizer code, and school_code must be exactly 4 digits after
    zero-filling.
    """
    bad_district = df.filter(
        ~pl.col("district_code").str.contains(r"^\d+$")
        | ~pl.col("district_code").str.len_chars().is_in([3, 7])
    )
    bad_school = df.filter(~pl.col("school_code").str.contains(r"^\d{4}$"))
    if bad_district.height or bad_school.height:
        raise ValueError(
            f"{label}: {bad_district.height} district code(s) / "
            f"{bad_school.height} school code(s) match no known shape — "
            f"districts: {bad_district['district_code'].head(5).to_list()}, "
            f"schools: {bad_school['school_code'].head(5).to_list()}"
        )


def _transform_school_era(
    df: pl.DataFrame,
    year: int,
    era: str,
    label: str,
) -> pl.DataFrame:
    """Transform one school-family bronze file (any era) to gold shape.

    Every row in every school-family era is a single school (no aggregate rows
    exist in this family), so detail_level is the constant "school".
    """
    # Year guard: the in-file year column must be single-valued and equal to
    # the filename year — a mismatch would mean a mislabeled republication.
    year_col = SCHOOL_ERA_YEAR_COLUMN[era]
    file_years = df[year_col].str.strip_chars().cast(pl.Float64).cast(pl.Int64).unique()
    if file_years.to_list() != [year]:
        raise ValueError(
            f"{label}: in-file {year_col} values {file_years.to_list()} != "
            f"filename year {year}"
        )

    # Era 4 publishes the rate's numerator and denominator; earlier eras do
    # not, so both counts become typed NULLs there.
    if era in SCHOOL_ERAS_WITH_COUNTS:
        count_exprs = [
            pl.col("K12_POVERTY_STUDENT_CT")
            .str.strip_chars()
            .cast(pl.Int64, strict=False)
            .alias("num_direct_cert_students"),
            pl.col("K12_STUDENT_COUNT")
            .str.strip_chars()
            .cast(pl.Int64, strict=False)
            .alias("num_k12_students"),
        ]
    else:
        logger.info(
            "%s: K12 count columns not published in this era — emitting NULL "
            "num_direct_cert_students / num_k12_students",
            label,
        )
        count_exprs = [
            pl.lit(None).cast(pl.Int64).alias("num_direct_cert_students"),
            pl.lit(None).cast(pl.Int64).alias("num_k12_students"),
        ]

    df = df.select(
        pl.lit(year).cast(pl.Int32).alias("year"),
        # 3-digit standard codes zero-fill to 3; 7-digit state-charter
        # authorizer codes (e.g. 7820108) are longer so zfill is a no-op.
        pl.col("SYSTEM_ID").str.strip_chars().str.zfill(3).alias("district_code"),
        # CSVs (2014-2016) publish zero-padded 4-char codes; .xls years publish
        # unpadded 3/4-digit codes — zfill(4) unifies both.
        pl.col("SCHOOL_ID").str.strip_chars().str.zfill(4).alias("school_code"),
        # Bronze publishes 0-100 at one-decimal precision with binary float
        # artifacts in the .xls years (82.400002); divide onto the 0-1 scale
        # per §4 and round to 3 decimals to restore published precision.
        (pl.col("direct_cert_perc").str.strip_chars().cast(pl.Float64, strict=False))
        .truediv(100.0)
        .round(3)
        .alias("direct_cert_rate"),
        *count_exprs,
        pl.lit("school").alias("detail_level"),
    )

    _assert_school_id_shapes(df, label)
    return df


def _transform_school_file(
    path: Path, manifest: TransformManifest
) -> pl.DataFrame | None:
    """Read one school-family bronze file, detect its era, transform it."""
    # All-string read: keeps the CSVs' zero-padded school codes intact and
    # makes every cast explicit (.xls files already read all-string).
    df, loss = read_bronze_file(path, infer_schema_length=0, return_loss=True)

    year = extract_year_from_filename(path.name)
    if year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")
    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])

    # 2017/2018 carry a methodology-note row above the real header; promote
    # BEFORE era detection so the signatures see the true columns.
    df = _promote_note_row_header(df, path.name)

    era = detect_era_by_columns(df, SCHOOL_ERA_SIGNATURES)
    if era is None:
        raise ValueError(
            f"{path.name}: no school-family era signature matched columns {df.columns}"
        )
    label = f"school/{era} {path.name}"

    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)

    if df.height == 0:
        logger.warning("%s: bronze file is empty, skipping", path.name)
        return None

    logger.info(
        "Processing %s as school/%s (year %d, %d rows)", path.name, era, year, df.height
    )
    return _transform_school_era(df, year, era, label)


# =============================================================================
# DISTRICT FAMILY — readers + era transform (rows: "district" / "state")
# =============================================================================

# The statewide aggregate sentinel: SYSTEM_ID=999 ("State of Georgia"),
# published 2022+ only. No other SYSTEM_ID can equal "999" — 3-digit district
# codes stop at 799/890/891 and charter codes are 7 digits.
STATE_SYSTEM_ID = "999"

# Era-detection signatures, most-specific first. Era 1's set is a strict
# superset of Era 2's (adds counts); Era 3 differs from Era 2 only by
# SCHOOL_YEAR in place of FISCAL_YEAR.
DISTRICT_ERA_SIGNATURES: dict[str, list[str]] = {
    "era_1_2020_2024_with_counts": [
        "FISCAL_YEAR",
        "SYSTEM_ID",
        "SYSTEM_NAME",
        "direct_cert_perc",
        "K12_POVERTY_STUDENT_CT",
        "K12_STUDENT_COUNT",
    ],
    "era_2_2015_2019_pct_only": [
        "FISCAL_YEAR",
        "SYSTEM_ID",
        "SYSTEM_NAME",
        "direct_cert_perc",
    ],
    "era_3_2014_school_year": [
        "SCHOOL_YEAR",
        "SYSTEM_ID",
        "SYSTEM_NAME",
        "direct_cert_perc",
    ],
}

DISTRICT_YEAR_SOURCE_BY_ERA: dict[str, str] = {
    "era_1_2020_2024_with_counts": "FISCAL_YEAR",
    "era_2_2015_2019_pct_only": "FISCAL_YEAR",
    "era_3_2014_school_year": "SCHOOL_YEAR",
}

DISTRICT_ERA_WITH_COUNTS = "era_1_2020_2024_with_counts"


def _read_district_file(path: Path) -> tuple[pl.DataFrame, dict]:
    """Read one district-family bronze file, fixing the 2017/2018 note quirk.

    The 2017 and 2018 XLS files carry a free-text methodology caveat on row 0
    and the real column headers on row 1, so the default read promotes the
    note text to a column name. The shared reader exposes no header-row
    argument; when the note header is detected the file is re-read directly via
    pandas with ``header=1`` using the same engine/dtype/na_values.
    """
    # infer_schema_length=0 forces all CSV columns to Utf8 (§4.3b) so every
    # cast below is explicit; the XLS path already reads everything as str.
    df, loss = read_bronze_file(path, infer_schema_length=0, return_loss=True)

    note_header = any(
        isinstance(col, str) and col.startswith("*Note:") for col in df.columns
    )
    if not note_header:
        return df, loss

    logger.info(
        "%s: methodology note on row 0 detected — re-reading with header=1",
        path.name,
    )
    pdf = pd.read_excel(
        path,
        engine="xlrd",
        dtype=str,
        header=1,
        na_values=list(SUPPRESSION_VALUES),
    )
    df = pl.from_pandas(pdf)
    # Excel reads have raw == parsed by construction (pandas loads the whole
    # sheet); rebuild the loss dict from the fixed frame.
    return df, {"raw_rows": df.height, "parsed_rows": df.height, "format": "xls"}


def _transform_district_common(df: pl.DataFrame, year: int, era: str) -> pl.DataFrame:
    """Transform one district-family bronze file (any era) to gold shape.

    Rows are "district" detail except the SYSTEM_ID=999 statewide row, which is
    tagged "state"; district_code for the state row is NULLed downstream by
    null_aggregate_geography.
    """
    # Rename-coverage guard (§4.1): the era signature pins every expected
    # source column; surface unexpected extras loudly.
    expected = set(DISTRICT_ERA_SIGNATURES[era])
    extras = [c for c in df.columns if c not in expected]
    if extras:
        logger.warning(
            "Year %d (district/%s): unexpected bronze columns ignored: %s",
            year,
            era,
            extras,
        )

    df = df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.col("SYSTEM_ID").str.strip_chars().str.zfill(3).alias("district_code"),
        pl.lit(None).cast(pl.Utf8).alias("school_code"),
        (pl.col("direct_cert_perc").cast(pl.Float64, strict=False) / 100.0)
        .round(3)
        .alias("direct_cert_rate"),
        pl.when(pl.col("SYSTEM_ID").str.strip_chars() == STATE_SYSTEM_ID)
        .then(pl.lit("state"))
        .otherwise(pl.lit("district"))
        .alias("detail_level"),
    )

    # Numerator/denominator counts exist only in Era 1 (2020+); earlier eras
    # materialize typed NULL columns (the source did not publish them).
    if era == DISTRICT_ERA_WITH_COUNTS:
        df = df.with_columns(
            pl.col("K12_POVERTY_STUDENT_CT")
            .cast(pl.Int64, strict=False)
            .alias("num_direct_cert_students"),
            pl.col("K12_STUDENT_COUNT")
            .cast(pl.Int64, strict=False)
            .alias("num_k12_students"),
        )
    else:
        logger.info(
            "Year %d (district/%s): count columns not published pre-FY2020 — "
            "emitting NULL num_direct_cert_students / num_k12_students",
            year,
            era,
        )
        df = df.with_columns(
            pl.lit(None).cast(pl.Int64).alias("num_direct_cert_students"),
            pl.lit(None).cast(pl.Int64).alias("num_k12_students"),
        )

    return df.select(STANDARD_COLUMNS)


def _transform_district_file(
    path: Path, manifest: TransformManifest
) -> pl.DataFrame | None:
    """Read one district-family bronze file, detect its era, transform it."""
    df, loss = _read_district_file(path)

    era = detect_era_by_columns(df, DISTRICT_ERA_SIGNATURES)
    if era is None:
        raise ValueError(
            f"{path.name}: no district-family era signature matched "
            f"columns {df.columns}"
        )

    # Year comes from the in-file year column; the filename year is the
    # cross-check. Every file carries exactly one year value.
    year_col = DISTRICT_YEAR_SOURCE_BY_ERA[era]
    year_values = df[year_col].cast(pl.Int32, strict=False).unique().to_list()
    if len(year_values) != 1 or year_values[0] is None:
        raise ValueError(
            f"{path.name}: expected one {year_col} value, got {year_values}"
        )
    year = int(year_values[0])
    filename_year = extract_year_from_filename(path.name)
    if filename_year is not None and filename_year != year:
        raise ValueError(
            f"{path.name}: filename year {filename_year} != data year {year}"
        )

    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])
    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)

    if df.height == 0:
        logger.warning("Year %d: bronze file is empty, skipping: %s", year, path.name)
        return None

    logger.info(
        "Processing %s as district/%s (year %d, %d rows)",
        path.name,
        era,
        year,
        df.height,
    )
    return _transform_district_common(df, year, era)


# =============================================================================
# Per-file dispatch (route by filename family infix)
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Dispatch one bronze file to the school or district family transform.

    The merged bronze dir holds both download families; the ``_school_`` /
    ``_district_`` infix in the filename selects the per-family reader + era
    logic. Anything else is an unrecognized file and must stop the pipeline.
    """
    name = path.name
    if "_school_" in name:
        return _transform_school_file(path, manifest)
    if "_district_" in name:
        return _transform_district_file(path, manifest)
    raise ValueError(
        f"{name}: cannot route — filename carries neither '_school_' nor "
        f"'_district_' family infix"
    )


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for the merged direct_certification."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file from BOTH families (read-loss
    # accounted per file; the same year is recorded once per family and the
    # manifest accumulates the two bronze counts into the year total).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR):
        result = transform_file(path, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize columns/dtypes across eras + families and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)
    logger.info("Combined %d rows across %d files", combined.height, len(all_dfs))

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean an era-routing or ID-formatting bug and must raise, never be
    # silently deduped. The detail_level is part of the natural key, so a
    # school and a district row that happen to share (year, district_code)
    # never collide (school rows carry a non-NULL school_code).
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: each file is one non-overlapping fiscal year with no in-file
    # duplicates, so dedup is purely defensive. sort_col="direct_cert_rate"
    # prefers a row with a reported rate over a blank placeholder if a future
    # republication introduces duplicates.
    pre_dedup = dict(combined.group_by("year").len().iter_rows())
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code"],
        district_keys=["year", "district_code"],
        state_keys=["year"],
        sort_col="direct_cert_rate",
    )
    post_dedup = dict(combined.group_by("year").len().iter_rows())
    for year in sorted(pre_dedup):
        removed = pre_dedup[year] - post_dedup.get(year, 0)
        if removed > 0:
            manifest.record_filtered(year, removed, "duplicate_rows_deduped")

    # 4. Geography nulling via the shared domain rules: the state rows
    # (SYSTEM_ID=999, 2022+) get district_code NULLed; district rows keep
    # school_code NULL; school rows keep both keys. No §4b masks apply (every
    # bronze value is physically possible).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. The count columns are 100% NULL for 2014-2019 (not
    # published before FY2020) — a publication boundary, not a spike; the
    # counts_* quality checks enforce the real invariant. Only year +
    # detail_level are universally non-null (district rows NULL school_code,
    # state rows NULL both geography keys).
    spike_result = check_null_rate_spikes(combined, ["direct_cert_rate"])
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(combined, required_non_null=["year", "detail_level"])

    # 5. Manifest stats on the FINAL DataFrame, then export to schools /
    # districts / states parquet by detail level.
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(combined, GOLD_DIR, STANDARD_COLUMNS)
    manifest.write(GOLD_DIR)

    # 6. Contract + README from the in-code column declaration. detail_levels /
    # default_detail are auto-discovered from the gold layout the export just
    # wrote (schools/districts/states -> default schools).
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

    # 7. ALWAYS LAST: validate the gold just written against the contract just
    # emitted. Raises GoldValidationError -> non-zero exit.
    run_topic_validation(GOLD_DIR)


def _emit_contract_and_readme(year_range: tuple[int, int]) -> None:
    """Emit the ODCS contract and gold README via ``write_data_dictionary``.

    The column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level``. Quality checks discriminate detail level by the
    geography-key NULL pattern (detail_level is implicit in the parquet
    filename and absent from the unioned validation view).
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Share of K-12 students directly certified for free school meals "
            "across Georgia public schools and districts, published by GOSA "
            "for fiscal years 2014-2024 (FY2024 = the 2023-24 school year). "
            "Direct certification is the automatic, categorical-eligibility "
            "subset of free/reduced-price meal eligibility — a student is "
            "directly certified because their household participates in SNAP "
            "or TANF, the student is homeless, unaccompanied youth, foster, or "
            "migrant, or (from FY2024) the household's Medicaid income is at or "
            "below the free/reduced-price-lunch standard — with no household "
            "application required. One fact table at three detail levels: "
            "school (one row per school), district (one row per district / "
            "system, including charters, state agencies, and State Schools), "
            "and state (the statewide 'State of Georgia' aggregate, published "
            "2022-2024 only). From FY2020 the underlying numerator and "
            "denominator counts are also published. Merges the formerly "
            "separate direct_certification_school and "
            "direct_certification_district topics."
        ),
        title="Direct Certification for Free School Meals",
        summary=(
            "Share of K-12 students automatically eligible for free school "
            "meals via SNAP/TANF and other programs, by Georgia school, "
            "district, and state, 2014-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Georgia fiscal year, equal to the ending (spring) "
                    "calendar year of the school year (FY2024 = 2023-24). Read "
                    "from the in-file FISCAL_YEAR column (SCHOOL_YEAR in the "
                    "2014 files) and cross-checked against the filename year in "
                    "both download families."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "null_meaning": (
                    "NULL only on the statewide aggregate (state) rows "
                    "(2022-2024); populated on every school and district row."
                ),
                "description": (
                    "GOSA district/system code (FK to districts dimension), "
                    "zero-padded to 3 digits; 7-digit charter and State-School "
                    "codes and 3-digit state-agency codes are preserved "
                    "unchanged. NULL on the statewide aggregate rows. Beyond "
                    "the ~180 standard county/city districts the series "
                    "includes 799 (combined State Schools, 2020+), 890 (Dept. "
                    "of Corrections, 2019 only), 891 (Dept. of Juvenile "
                    "Justice, 2017+), 7991893-7991895 (individual State "
                    "Schools, 2014-2019; superseded by the combined 799 row "
                    "from 2020), and 782xxxx/783xxxx state and commission "
                    "charter schools."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0103",
                "null_meaning": (
                    "Populated only on school-detail rows; NULL on every "
                    "district-detail and state-detail row (those levels have "
                    "no school code). The column is shared across the "
                    "education key shape."
                ),
                "description": (
                    "GOSA school code, zero-padded to 4 characters (composite "
                    "FK to schools dimension with district_code; not globally "
                    "unique on its own). Populated on school rows only — "
                    "district and state aggregate rows carry NULL. The "
                    "2014-2016 CSVs publish the padded form natively; the "
                    "2017-2024 .xls files publish unpadded 3/4-digit codes "
                    "that are zero-filled to match."
                ),
            },
            {
                "name": "direct_cert_rate",
                "key_metric": True,
                "type": "float64",
                "unit": "proportion",
                "example": 0.69,
                "short_description": (
                    "Share of K-12 students automatically eligible for free "
                    "meals (via SNAP/TANF, foster, homeless, migrant, or "
                    "Medicaid), on a 0-1 scale."
                ),
                "description": (
                    "Share of K-12 students directly certified for free school "
                    "meals, on the 0-1 scale (0.69 = 69%%). Bronze publishes "
                    "0-100 (integer percent in 2014-2016, one-decimal float "
                    "thereafter); divided by 100 per data-cleaning-standards "
                    "§4 and rounded to 3 decimals to strip .xls binary-float "
                    "artifacts (82.400002 -> 0.824). Bounded — never exceeds "
                    "1.0 in any year. Never NULL (the source has no "
                    "suppression). Where the FY2020+ counts exist, the rate "
                    "reconciles with num_direct_cert_students / "
                    "num_k12_students to within one-decimal-percent rounding "
                    "(max observed deviation 0.0005). Two methodology breaks: "
                    "FY2017 excludes foster students (FY2018+ re-includes "
                    "them), and FY2024 adds the Medicaid (DC-M) category — "
                    "comparisons crossing 2016->2017, 2017->2018, or "
                    "2023->2024 are not apples-to-apples."
                ),
            },
            {
                "name": "num_direct_cert_students",
                "metric_component": "numerator",
                "type": "int64",
                "unit": "count",
                "example": 2233,
                "null_meaning": (
                    "NULL for FY2014-FY2019: the source did not publish the "
                    "underlying counts before FY2020. Populated for every row "
                    "(all detail levels) from 2020 on. NOT suppression."
                ),
                "description": (
                    "Headcount of K-12 students directly certified — the "
                    "numerator of direct_cert_rate (bronze "
                    "K12_POVERTY_STUDENT_CT). Published FY2020 onward only; "
                    "NULL for 2014-2019. Always at most num_k12_students "
                    "(enforced by a quality check)."
                ),
            },
            {
                "name": "num_k12_students",
                "metric_component": "denominator",
                "type": "int64",
                "unit": "count",
                "example": 3238,
                "null_meaning": (
                    "NULL for FY2014-FY2019: the source did not publish the "
                    "underlying counts before FY2020. Populated for every row "
                    "(all detail levels) from 2020 on. NOT suppression."
                ),
                "description": (
                    "Total K-12 enrollment used as the denominator of "
                    "direct_cert_rate (the NSLP K-12 enrollment base — not the "
                    "October/March FTE enrollment published by the enrollment "
                    "topics; bronze K12_STUDENT_COUNT). Published FY2020 "
                    "onward only; NULL for 2014-2019. Strictly positive where "
                    "present (enforced by a quality check)."
                ),
            },
        ],
        source="GOSA",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        # No suppression anywhere in either family — every system/school
        # publishes a numeric rate in every year (pinned by
        # direct_cert_rate_never_null).
        suppressed_to_null=False,
        limitations=(
            "Three detail levels (school, district, state) in one fact table, "
            "split by parquet filename; school_code is NULL on district/state "
            "rows and district_code is NULL on state rows. The statewide "
            "aggregate exists only for 2022-2024; earlier years publish no "
            "state row and pre-2020 years lack the counts needed to "
            "reconstruct one. The underlying counts (num_direct_cert_students, "
            "num_k12_students) are published only from FY2020 and are NULL "
            "before that. School-level rows and district-level rows come from "
            "two independent GOSA downloads whose K-12 bases need not "
            "reconcile exactly, so school rows are NOT guaranteed to sum to "
            "their district row. Two methodology breaks limit year-over-year "
            "comparison: FY2017 rates EXCLUDE foster students (FY2018+ include "
            "them), and FY2024 adds the Medicaid DC-M category, roughly "
            "doubling certified counts — comparisons crossing 2016->2017, "
            "2017->2018, or 2023->2024 are not apples-to-apples. The State "
            "Schools representation changes across eras: three individual "
            "7-digit rows (7991893-7991895) through 2019, one combined 799 "
            "row from 2020. No suppression exists in this topic — NULL never "
            "means suppressed."
        ),
        notes=[
            (
                "Three detail levels: school (one row per school, both "
                "geography keys populated), district (one row per "
                "district/system, school_code NULL), and state (the "
                "'State of Georgia' aggregate, 2022-2024 only, both geography "
                "keys NULL). schools.parquet under every year partition, "
                "districts.parquet under every year partition, states.parquet "
                "for 2022-2024 only. detail_level is implicit in the filename "
                "and is not a stored column."
            ),
            (
                "direct_cert_rate is on the 0-1 scale (bronze publishes 0-100; "
                "divided by 100 per data-cleaning-standards §4 and rounded to "
                "3 decimals, lossless for the published precision). It is a "
                "bounded proportion — the numerator is a subset of the "
                "denominator by definition."
            ),
            (
                "FY2017 methodology break (from the note embedded in the 2017 "
                "and 2018 source files of both families): 2017 direct "
                "certification counts exclude foster students and FY2018+ "
                "include them — do not read 2017 -> 2018 movement as a trend. "
                "Values are carried through verbatim."
            ),
            (
                "FY2024 methodology break: Georgia joined the USDA Direct "
                "Certification with Medicaid (DC-M) Demonstration Project in "
                "2023-24 (per GOSA, https://gosa.georgia.gov/directcert), "
                "adding a Medicaid income category. Rates jump sharply "
                "(district mean ~0.38 -> ~0.63); verified in bronze. Values "
                "are carried through verbatim."
            ),
            (
                "Underlying counts are published only from FY2020 "
                "(num_direct_cert_students, num_k12_students); 2014-2019 "
                "rows are NULL for both. The published statewide row's counts "
                "equal the sums over the district-detail rows exactly in all "
                "three years it exists (2022-2024) — pinned by a quality "
                "check."
            ),
            (
                "Non-standard district codes kept as district rows: 799 "
                "(combined State Schools, 2020+), 890 (Dept. of Corrections, "
                "2019 only), 891 (Dept. of Juvenile Justice, 2017+), "
                "7991893-7991895 (individual State Schools, 2014-2019), and "
                "7-digit 782xxxx/783xxxx charter codes. All resolve in the "
                "districts dimension."
            ),
            (
                "School-level and district-level rows come from two "
                "independent GOSA downloads. They share metric semantics but "
                "their K-12 bases are not guaranteed to reconcile, so school "
                "rows within a district are NOT asserted to sum to that "
                "district's row."
            ),
            (
                "No demographic column: neither family publishes any race, "
                "gender, or economic-status breakdown in any era."
            ),
        ],
        quality_checks=[
            {
                "name": "school_code_requires_district_code",
                "description": (
                    "Structural fact: a school-detail row (school_code "
                    "populated) always nests under a district, so a non-NULL "
                    "school_code with a NULL district_code is an impossible "
                    "geography-key pattern — it would mean a school row lost "
                    "its district or a malformed aggregate."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE school_code IS NOT NULL AND district_code IS NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "district_code_length_3_or_7",
                "description": (
                    "Where populated, district_code is a 3-character standard "
                    "county/city / state-agency code or a 7-character charter "
                    "/ State-School code — any other length means the ID "
                    "formatting regressed."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE district_code IS NOT NULL "
                    "AND LENGTH(district_code) NOT IN (3, 7)"
                ),
                "mustBe": 0,
            },
            {
                "name": "school_code_length_4",
                "description": (
                    "Where populated (school-detail rows), school_code is "
                    "always zero-padded to exactly 4 characters, matching the "
                    "schools dimension key format."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE school_code IS NOT NULL AND LENGTH(school_code) <> 4"
                ),
                "mustBe": 0,
            },
            {
                "name": "direct_cert_rate_never_null",
                "description": (
                    "Neither family has suppression: every school, district, "
                    "and state row in every published year carries a numeric "
                    "rate (verified across all 22 bronze files). A NULL means "
                    "a parsing regression or a new suppression regime — either "
                    "must be analyzed."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE direct_cert_rate IS NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "counts_null_before_2020",
                "description": (
                    "The numerator/denominator counts were first published in "
                    "FY2020 in both families; any non-NULL count before 2020 "
                    "is fabricated data and must be analyzed."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year < 2020 AND "
                    "(num_direct_cert_students IS NOT NULL OR "
                    "num_k12_students IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "counts_present_2020_onward",
                "description": (
                    "From FY2020 every row at every detail level publishes "
                    "both counts (verified: zero NULLs in the 2020-2024 bronze "
                    "files of both families). A NULL means a parsing/cast "
                    "regression — counts and rate must arrive together."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year >= 2020 AND "
                    "(num_direct_cert_students IS NULL OR "
                    "num_k12_students IS NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "num_k12_students_positive_when_present",
                "description": (
                    "Where the denominator is published (FY2020+), total K-12 "
                    "enrollment must be strictly positive — a zero denominator "
                    "cannot produce the published rate."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE num_k12_students "
                    "IS NOT NULL AND num_k12_students <= 0"
                ),
                "mustBe": 0,
            },
            {
                "name": "direct_cert_numerator_within_denominator",
                "description": (
                    "The directly-certified headcount is a subset of K-12 "
                    "enrollment, so the numerator must never exceed the "
                    "denominator where both are published (FY2020+), at every "
                    "detail level."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "num_direct_cert_students IS NOT NULL AND "
                    "num_k12_students IS NOT NULL AND "
                    "num_direct_cert_students > num_k12_students"
                ),
                "mustBe": 0,
            },
            {
                "name": "direct_cert_rate_matches_counts",
                "description": (
                    "Component reconciliation: where all three values are "
                    "published (FY2020+), the rate must equal "
                    "numerator/denominator within 0.002 on the 0-1 scale — the "
                    "bronze rate is rounded to one decimal on the 0-100 scale "
                    "and gold rounds to 3 decimals, so 0.002 is ~2x worst-case "
                    "rounding; verified max observed deviation is 0.0005 in "
                    "both families."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE direct_cert_rate "
                    "IS NOT NULL AND num_direct_cert_students IS NOT NULL "
                    "AND num_k12_students IS NOT NULL AND "
                    "num_k12_students > 0 AND ABS(direct_cert_rate - "
                    "(CAST(num_direct_cert_students AS DOUBLE) / "
                    "num_k12_students)) > 0.002"
                ),
                "mustBe": 0,
            },
            {
                "name": "no_state_rows_before_2022",
                "description": (
                    "Structural fact: the statewide 'State of Georgia' row "
                    "(both geography keys NULL) is published only from 2022. A "
                    "row with NULL district_code in an earlier year means a "
                    "fabricated aggregate or an ID parse failure — either must "
                    "be analyzed."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE district_code IS NULL AND year < 2022"
                ),
                "mustBe": 0,
            },
            {
                "name": "one_state_row_per_year_2022_onward",
                "description": (
                    "Every year from 2022 carries exactly one statewide "
                    "aggregate row (district_code IS NULL). Zero means the "
                    "published state row was lost; more than one means a "
                    "duplicated or mis-classified aggregate."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year FROM {object} "
                    "WHERE year >= 2022 GROUP BY year "
                    "HAVING SUM(CASE WHEN district_code IS NULL THEN 1 "
                    "ELSE 0 END) <> 1) AS bad_years"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_counts_equal_district_sums",
                "description": (
                    "Component reconciliation: in every year that publishes a "
                    "statewide row (2022-2024), its numerator and denominator "
                    "equal the sums over the district-DETAIL rows exactly "
                    "(verified in bronze). District-detail rows are the "
                    "school_code IS NULL AND district_code IS NOT NULL rows — "
                    "school-detail rows are excluded so they are not "
                    "double-counted against the state total."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year, "
                    "MAX(CASE WHEN district_code IS NULL THEN "
                    "num_direct_cert_students END) AS state_num, "
                    "MAX(CASE WHEN district_code IS NULL THEN "
                    "num_k12_students END) AS state_den, "
                    "SUM(CASE WHEN district_code IS NOT NULL "
                    "AND school_code IS NULL THEN "
                    "num_direct_cert_students END) AS district_num, "
                    "SUM(CASE WHEN district_code IS NOT NULL "
                    "AND school_code IS NULL THEN "
                    "num_k12_students END) AS district_den "
                    "FROM {object} GROUP BY year) AS by_year "
                    "WHERE state_num IS NOT NULL AND state_den IS NOT NULL "
                    "AND (state_num <> district_num OR state_den <> district_den)"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
