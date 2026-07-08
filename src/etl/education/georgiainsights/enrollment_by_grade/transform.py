"""Transform bronze enrollment_by_grade files into gold fact tables.

Source: Georgia Insights (GaDOE) "FTE Enrollment by Grade Level(PK-12)" — the
FTE headcount of Georgia public school students broken out by grade level
(Pre-K, Kindergarten, Grades 1-12) for every school, district, and the state.
GaDOE takes the count twice per school year: the October Cycle 1 (``-1``,
fall) snapshot and the March Cycle 3 (``-3``, spring) snapshot. This topic
merges both snapshots into one fact table, folding the snapshot period into an
``enrollment_period`` column (``fall`` / ``spring``) so a single grain row is
one (year, geography, period, grade) cell — matching the period vocabulary of
the GOSA ``enrollment_by_grade_level`` topic.

The fall half spans fiscal years 2010-2026 (34 CSVs); the spring half spans
2010-2025 (32 CSVs); 66 CSVs total. Grade is the primary row axis, so per the
education domain grade-in-demographic policy it lives in ``grade_level``
(canonical codes ``pk``/``k``/``01``..``12``/``all``) and there is no
``demographic`` column.

Design decisions (every invariant re-verified against this topic's bronze
during the prior single-period transforms — see bronze-data-structure.md):

- **Two periods, one transform body.** October (``-1``, fall) and March
  (``-3``, spring) files share one layout: a 4-line GaDOE preamble, then a
  District CSV (17 columns) + a School CSV (18 columns, adding the typo'd
  ``SChool Name``) per fiscal year. The only structural difference between the
  two periods is the filename suffix and the in-file preamble caption. The
  period is parsed from the filename suffix (``-1`` -> fall, ``-3`` -> spring)
  and threaded through every row as ``enrollment_period``.

- **Read loss is measured, not assumed.** The local CSV reader counts the raw
  data lines (total lines minus 4 preamble minus 1 header — no quoted
  multi-line fields exist in this source) and records raw vs parsed per file.
  Verified raw == parsed for all 66 files.

- **The bronze ``Total`` column survives as ``grade_level = 'all'``.** It
  equals the row-wise sum of the 14 grade columns bit-exact on every bronze
  row (verified for both periods), so it is folded into the same unpivot as
  the grade columns and mapped to ``all`` — analysts get the total without
  recomputing it, and the ``all_equals_sum_of_grades`` contract check keeps the
  identity enforced.

- **School-file ``System Total`` rows are dropped.** Each School file carries
  one per-district aggregate row (``SChool Name`` strips to ``System Total``)
  that is bit-equal to the corresponding District-file row (verified for every
  district in every year of both periods). The District file is the canonical
  district layer; the duplicate aggregates are dropped before the unpivot and
  recorded via ``manifest.record_filtered``.

- **State rows are published twice per year per period** — both the District
  and the School file end with an identical ``State-Wide Total`` row (verified
  bit-equal). The natural-key collision guard (keyed on
  ``enrollment_period``) proves the twins agree, then
  ``deduplicate_by_detail_level`` keeps one copy. The fall and spring state
  rows are distinct keys (different ``enrollment_period``), so the two periods
  never collide with each other.

- **No suppression.** Every grade/Total cell in all 66 files parses as a
  non-negative integer — there are no ``*``/``TFS``-style markers anywhere
  (verified cell-by-cell). A 0 is a real reported value (grade not offered at
  the entity). The contract is emitted with ``suppressed_to_null=False``,
  ``num_students`` is declared non-nullable, and a ``num_students_never_null``
  quality check keeps the fact enforceable.

- **State schools era split preserved as-is.** The three state schools
  (Atlanta Area School for the Deaf, GA Academy for the Blind, GA School for
  the Deaf) appear consolidated under district ``799`` in some years and as
  three 7-digit pseudo-districts ``7991893``/``7991894``/``7991895`` (school
  names ``1893-N/A`` etc.) in the split era (spring: 2011-2019; fall:
  2012-2019). Bronze identifiers are preserved as-is rather than remapped to
  799 — rewriting bronze IDs is discouraged, and the districts/schools
  dimensions already carry the pseudo-district entities with hand-coded names.
  Because IDs are never remapped, the slightly different split boundary
  between the two periods is documentation-only and needs no branching here.

- **Geography**: state rows carry ``System ID == " "`` (single space);
  whitespace-only maps to NULL BEFORE zfill so it cannot masquerade as
  district "000". District codes are 3-digit standard or 7-digit
  charter/specialty (verified: no other shapes) — zfill(3) pads defensively
  without truncating. School codes come from the 4-digit prefix of
  ``SChool Name`` (``NNNN-Name``; 100%% pattern conformance verified on every
  non-aggregate school row); zfill(4) is defensive.

- **No section 4b masks**: counts are non-negative by construction (no
  non-numeric values exist in any count cell) and no impossible values exist.

- **No collisions**: the 15 grade labels ("all" + 14 bronze grade columns)
  map 1:1 onto 15 distinct canonical ``grade_level`` codes, and bronze carries
  no duplicate (district, school) identity within any file; the collision
  guard still runs before dedup and would catch any future drift.
"""

import logging
import re
from pathlib import Path

import polars as pl

from src.utils.grades import GRADE_LEVEL_MAP, normalize_grade_column
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

TOPIC = "enrollment_by_grade"
BRONZE_DIR = Path("data/bronze/education/georgiainsights/enrollment_by_grade")
GOLD_DIR = Path("data/gold/education/enrollment_by_grade")
SOURCE_URL = "https://georgiainsights.gadoe.org/data-downloads/"

# Filename: "... Fiscal Year2010-1 District.csv" or "... Fiscal Year2010-3
# School.csv" (no space before the year). The cycle suffix encodes the
# snapshot period: `-1` = Cycle 1 / October / fall; `-3` = Cycle 3 / March /
# spring. The preamble's line 2 writes the year WITH a space ("Fiscal Year
# 2010-1 Data Report") — two distinct patterns.
FILENAME_PATTERN = re.compile(r"Fiscal Year(\d{4})-([13]) (District|School)\.csv$")
PREAMBLE_TITLE = "FTE Enrollment by Grade Level(PK-12)"
# Validate the preamble year against the filename year, allowing either cycle
# suffix (the per-file value is checked against the parsed cycle below).
PREAMBLE_YEAR_PATTERN = re.compile(r"Fiscal Year (\d{4})-([13])")

# Cycle suffix -> enrollment_period (the GOSA enrollment_by_grade_level
# vocabulary): Cycle 1 (October) is the fall snapshot; Cycle 3 (March) is the
# spring snapshot.
CYCLE_TO_PERIOD: dict[str, str] = {
    "1": "fall",
    "3": "spring",
}
ENROLLMENT_PERIOD_VALUES: list[str] = ["fall", "spring"]

# Lines before the header row in every bronze CSV (masthead, title, count
# date, near-blank spacer). The header is line 5.
PREAMBLE_LINES = 4

# The 14 per-grade bronze columns, post header-strip, in source order.
GRADE_COLUMNS: list[str] = [
    "Grade PK",
    "Grade KK",
    *[f"Grade {n:02d}" for n in range(1, 13)],
]

# Effective slice of the shared GRADE_LEVEL_MAP this topic exercises (the 15
# aliases actually hit, not the whole map). Keys are the uppercased bronze
# labels normalize_grade_column sees: the 14 stripped grade column headers plus
# the literal "all" total label.
EFFECTIVE_GRADE_MAP: dict[str, str] = {
    label: GRADE_LEVEL_MAP[label]
    for label in [c.upper() for c in GRADE_COLUMNS] + ["ALL"]
}

# Canonical grade_level vocabulary this topic publishes (contract enum).
GRADE_LEVEL_VALUES: list[str] = sorted(EFFECTIVE_GRADE_MAP.values())

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "enrollment_period",
    "grade_level",
    "detail_level",
    "num_students",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "enrollment_period": pl.Utf8,
    "grade_level": pl.Utf8,
    "detail_level": pl.Utf8,
    "num_students": pl.Int64,
}

METRIC_COLUMNS: list[str] = ["num_students"]

# Natural key for the collision guard. Includes enrollment_period (so the two
# snapshot periods are distinct cells) and detail_level (so the expected
# state-row twins — District file copy + School file copy, identical values —
# are checked for divergence within the state level itself).
NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "enrollment_period",
    "grade_level",
    "detail_level",
]


# =============================================================================
# Bronze reading
# =============================================================================


def _read_bronze_csv(path: Path, year: int) -> tuple[pl.DataFrame, dict]:
    """Read one bronze CSV: verify the preamble, strip headers, count loss.

    The shared ``read_bronze_file`` cannot skip the 4-line GaDOE preamble, so
    this local reader handles it: it verifies the line-2 title and cross-checks
    the preamble year against the filename year (a mismatch means a misnamed or
    mis-filled file — fail loudly), then reads everything as Utf8
    (``infer_schema_length=0`` — preserves the whitespace state sentinel and
    any zero-padded codes). No ``null_values`` list is registered: this source
    has no suppression markers anywhere (verified cell-by-cell across all 66
    files), so every count cell must parse as an integer downstream.

    Returns:
        ``(df, loss)`` — the all-Utf8 frame with stripped headers and a
        read-loss dict. Raw rows are counted from the file's data lines (total
        lines minus preamble minus header); this source has no quoted
        multi-line fields, so raw == parsed is expected (verified all 66 files).
    """
    raw_bytes = path.read_bytes()
    lines = raw_bytes.decode("utf-8").splitlines()
    title_line = lines[1] if len(lines) > 1 else ""
    if PREAMBLE_TITLE not in title_line:
        raise ValueError(
            f"{path.name}: preamble line 2 does not contain the expected "
            f"title {PREAMBLE_TITLE!r}: {title_line[:100]!r}"
        )
    preamble_match = PREAMBLE_YEAR_PATTERN.search(title_line)
    if preamble_match is None or int(preamble_match.group(1)) != year:
        raise ValueError(
            f"{path.name}: preamble year disagrees with filename year "
            f"{year}: {title_line[:100]!r}"
        )

    # Parse from the bytes already in memory — one physical read per file.
    df = pl.read_csv(raw_bytes, skip_rows=PREAMBLE_LINES, infer_schema_length=0)
    # Strip the source's inconsistent leading header whitespace (" System
    # Name", " Grade PK", " SChool Name") so downstream code uses clean names.
    # The "SChool" typo is preserved — it is the real header.
    df = df.rename({c: c.strip() for c in df.columns})

    raw_rows = len(lines) - PREAMBLE_LINES - 1  # minus header line
    loss = {"raw_rows": raw_rows, "parsed_rows": df.height, "format": "csv"}
    return df, loss


# =============================================================================
# Per-file transform (single layout, two periods)
# =============================================================================


def _transform_file_frame(
    df: pl.DataFrame,
    year: int,
    period: str,
    detail_level_source: str,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Transform one bronze file (District or School) for one year/period.

    All 66 files share one post-strip column set; the only structural
    difference is the School files' extra ``SChool Name`` column (and their
    per-district ``System Total`` rows). The period is a constant per file,
    parsed from the filename and threaded onto every row.
    """
    # Rename-coverage guard: a missing bronze column would silently become NULL
    # in gold, so absence fails loudly. Required set depends on level.
    context = f"{TOPIC} {year} {period} {detail_level_source}"
    required = {"System ID", "System Name", "Total", *GRADE_COLUMNS}
    if detail_level_source == "school":
        required.add("SChool Name")
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(
            f"{context}: expected bronze column(s) missing: {missing}. "
            f"Present: {sorted(df.columns)}"
        )

    # State-aggregate rows carry System ID == " " (single space sentinel;
    # null-or-whitespace matched defensively). Everything else in a District
    # file is a district row; everything else in a School file is a school row
    # or a per-district "System Total" aggregate handled below.
    is_state = pl.col("System ID").is_null() | (
        pl.col("System ID").str.strip_chars().str.len_chars() == 0
    )
    df = df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.lit(period).alias("enrollment_period"),
        pl.when(is_state)
        .then(pl.lit("state"))
        .otherwise(pl.lit(detail_level_source))
        .alias("detail_level"),
    )

    if detail_level_source == "school":
        # Drop the per-district " System Total" aggregate rows: they are
        # bit-equal to the same year's District-file rows on all 15 counts
        # (verified for every district in every year), and the District file is
        # the canonical district layer.
        pre_drop = df.height
        df = df.filter(
            ~(
                (pl.col("detail_level") == "school")
                & (pl.col("SChool Name").str.strip_chars() == "System Total")
            )
        )
        dropped = pre_drop - df.height
        manifest.record_filtered(
            year,
            dropped,
            "system_total_rows_dropped_redundant_with_district_file",
        )
        logger.info(
            "Year %d %s (school): dropped %d 'System Total' rows "
            "(bit-equal district aggregates; District file is canonical)",
            year,
            period,
            dropped,
        )
        # Every remaining school row must carry the "NNNN-Name" code prefix
        # (verified 100%% conformance) — an unparseable name would silently
        # produce a NULL school_code, so it fails loudly instead.
        bad_names = df.filter(
            (pl.col("detail_level") == "school")
            & ~pl.col("SChool Name").str.contains(r"^\d{4}-")
        )
        if bad_names.height:
            raise ValueError(
                f"{context}: {bad_names.height} school row(s) whose SChool "
                f"Name lacks the NNNN- code prefix: "
                f"{bad_names['SChool Name'].head(5).to_list()}"
            )
        # SChool Name packs "NNNN-School Name"; extract the leading 4-digit code
        # (anchored, so the state row's whitespace name yields NULL). zfill(4)
        # is defensive (verified already 4 digits).
        school_code = pl.col("SChool Name").str.extract(r"^(\d{4})-", 1).str.zfill(4)
    else:
        # District files carry no school-level rows; uniform NULL keeps the
        # shared key-column shape (education CLAUDE.md).
        school_code = pl.lit(None).cast(pl.Utf8)

    df = df.with_columns(
        # Whitespace state sentinel -> NULL BEFORE zfill (otherwise zfill would
        # mint a phantom district "000"); zfill(3) pads 3-digit standard codes
        # and passes 7-digit charter/specialty codes through.
        pl.when(is_state)
        .then(None)
        .otherwise(pl.col("System ID"))
        .str.zfill(3)
        .alias("district_code"),
        school_code.alias("school_code"),
        # No suppression in this source — every cell is an integer. strict=False
        # is belt-and-braces; validate_output() requires num_students non-null,
        # so a stray non-numeric value still fails.
        *[
            pl.col(c).cast(pl.Int64, strict=False).alias(c)
            for c in [*GRADE_COLUMNS, "Total"]
        ],
    )

    # Tidy long format (section 9). The pre-aggregated `Total` column (==
    # row-wise sum of the 14 grades, bit-exact bronze invariant) is held aside
    # as the grade_level='all' sub-frame BEFORE the grade unpivot so it can
    # never double-count as a grade bucket.
    id_vars = [
        "year",
        "district_code",
        "school_code",
        "enrollment_period",
        "detail_level",
    ]
    long_cols = [*id_vars, "grade_raw", "num_students"]
    total_df = df.select(
        *id_vars,
        pl.lit("all").alias("grade_raw"),
        pl.col("Total").alias("num_students"),
    ).select(long_cols)
    grades_df = df.unpivot(
        index=id_vars,
        on=GRADE_COLUMNS,
        variable_name="grade_raw",
        value_name="num_students",
    ).select(long_cols)
    long_df = pl.concat([total_df, grades_df], how="vertical")

    # Grade is the primary row axis -> canonical grade_level via the shared
    # normalizer ("Grade PK" -> pk, "Grade KK" -> k, "Grade 01" -> 01, ...,
    # "all" -> all). Unmatched values become the sentinel, which the manifest's
    # unmapped guard turns into a hard failure.
    bronze_grade = long_df["grade_raw"]
    long_df = long_df.with_columns(
        normalize_grade_column("grade_raw").alias("grade_level")
    )
    manifest.record_categorical(
        column="grade_level",
        map_dict=EFFECTIVE_GRADE_MAP,
        bronze_series=bronze_grade,
        gold_series=long_df["grade_level"],
    )

    return long_df.select(STANDARD_COLUMNS)


# =============================================================================
# File dispatcher
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read and transform one bronze CSV (read-loss accounted)."""
    match = FILENAME_PATTERN.search(path.name)
    if match is None:
        raise ValueError(
            f"Unexpected bronze filename (no 'Fiscal YearYYYY-[1|3] "
            f"District|School.csv' suffix): {path.name}"
        )
    year = int(match.group(1))
    cycle = match.group(2)
    period = CYCLE_TO_PERIOD[cycle]
    detail_level_source = match.group(3).lower()

    df, loss = _read_bronze_csv(path, year)
    # Cross-check the filename cycle against the preamble cycle (one period per
    # file) — a mismatch means a misnamed file, not a parse choice.
    title_line = path.read_bytes().decode("utf-8").splitlines()[1]
    preamble_match = PREAMBLE_YEAR_PATTERN.search(title_line)
    if preamble_match is not None and preamble_match.group(2) != cycle:
        raise ValueError(
            f"{path.name}: filename cycle -{cycle} disagrees with preamble "
            f"cycle -{preamble_match.group(2)}: {title_line[:100]!r}"
        )

    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])
    # Single layout, two periods; the era name documents why there is no
    # per-period dispatch beyond the constant column.
    manifest.record_file(
        path, year, f"era_1_2010_2026_fte_{period}_grade", df.height, df.columns
    )
    manifest.record_bronze(year, df.height)

    if df.height == 0:
        logger.warning("Year %d: bronze file %s is empty, skipping", year, path.name)
        return None
    logger.info(
        "Processing %s (year %d, %s, %s, %d rows)",
        path.name,
        year,
        period,
        detail_level_source,
        df.height,
    )
    return _transform_file_frame(df, year, period, detail_level_source, manifest)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for this topic."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file (four per year: fall/spring x
    # District/School, except the spring half stops at 2025).
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

    # 3. Collision guard BEFORE dedup: the only expected duplicate keys are the
    # state-row twins (each year/period's District and School file both carry
    # the State-Wide Total row — verified identical). The guard tolerates
    # identical twins and raises on divergent values, so a future mismatch
    # between the two files surfaces instead of being deduped away. Keyed on
    # enrollment_period, so fall and spring never alias each other.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )

    # Record the state-twin removal per year before dedup erases the evidence:
    # per (year, period), 15 duplicate state rows drop (14 grades + 'all').
    state_dupes = (
        combined.filter(pl.col("detail_level") == "state")
        .group_by("year")
        .agg(
            (pl.len() - pl.struct("enrollment_period", "grade_level").n_unique()).alias(
                "dupes"
            )
        )
        .sort("year")
    )
    for row in state_dupes.iter_rows(named=True):
        if row["dupes"]:
            manifest.record_filtered(
                int(row["year"]),
                int(row["dupes"]),
                "duplicate_state_rows_district_and_school_files_both_publish_them",
            )

    # Tie-break: state twins are value-identical (guard above proves it), so the
    # winner is irrelevant; sort_col="num_students" states the preference
    # explicitly (keep the row with a reported, larger count). enrollment_period
    # is part of every key so the two snapshots dedup independently.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=[
            "year",
            "district_code",
            "school_code",
            "enrollment_period",
            "grade_level",
        ],
        district_keys=[
            "year",
            "district_code",
            "enrollment_period",
            "grade_level",
        ],
        state_keys=["year", "enrollment_period", "grade_level"],
        sort_col="num_students",
    )

    # 4. Geography nulling (shared domain rules — transform and validator read
    # the same dict, so they cannot disagree). No section 4b masks: counts are
    # non-negative by construction and no impossible values exist.
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. num_students is required non-null because this source
    # has no suppression — a NULL means a parse bug, not small-cell masking.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(
        combined,
        required_non_null=[
            "year",
            "detail_level",
            "enrollment_period",
            "grade_level",
            "num_students",
        ],
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

    # 7. ALWAYS LAST: validate the gold just written against the contract just
    # emitted. Raises GoldValidationError -> non-zero exit.
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
            "Georgia Insights (GaDOE) FTE Enrollment by Grade Level(PK-12) — "
            "the FTE headcount of Georgia public school students broken out by "
            "grade level (pre-kindergarten, kindergarten, grades 1-12, plus an "
            "'all' total row) for every school, district, and the state. GaDOE "
            "counts enrollment twice per school year: the October Cycle 1 "
            "(fall) snapshot and the March Cycle 3 (spring) snapshot; both are "
            "preserved as distinct rows via the enrollment_period column. The "
            "fall half spans fiscal years 2010-2026 and the spring half "
            "2010-2025. Grade is the row axis and lives in grade_level — there "
            "are no demographic breakouts in this topic."
        ),
        title="Enrollment by Grade Level (Fall and Spring)",
        summary=(
            "Public school student headcounts by grade level (PK-12) from the "
            "October (fall) and March (spring) FTE counts, per school, "
            "district, and state, 2010-2026."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2026,
                "description": (
                    "Fiscal year of the FTE count (school year ending in this "
                    "year; e.g. 2026 = the 2025-2026 school year). Sourced "
                    "from the bronze filename, cross-checked against each "
                    "file's preamble. The spring (March) snapshot is present "
                    "through 2025; the fall (October) snapshot through 2026."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "3-digit GOSA district code (zero-padded) for standard "
                    "districts; 7-digit code for state charters and specialty "
                    "schools, including the pseudo-districts "
                    "7991893/7991894/7991895 for the three state schools "
                    "(reported under district 799 in other years). NULL for "
                    "state-level rows. FK to districts dimension."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0103",
                "description": (
                    "4-digit GOSA school code, extracted from the bronze "
                    "`SChool Name` (`NNNN-Name`) prefix. NULL for state- and "
                    "district-level rows. FK to schools dimension (composite "
                    "key with district_code)."
                ),
            },
            {
                "name": "enrollment_period",
                "type": "string",
                "nullable": False,
                "example": "fall",
                "validValues": ENROLLMENT_PERIOD_VALUES,
                "short_description": (
                    "Enrollment snapshot within the school year: fall "
                    "(October) or spring (March); never sum across them."
                ),
                "description": (
                    "Enrollment-count snapshot within the school year: 'fall' "
                    "(GaDOE October Cycle 1 count, first Tuesday of October) "
                    "or 'spring' (March Cycle 3 count, third Tuesday of "
                    "March). Both snapshots exist for nearly every entity — "
                    "queries wanting one headline count per year must filter "
                    "to a single period, never sum across them."
                ),
            },
            {
                "name": "grade_level",
                "type": "string",
                "nullable": False,
                "example": "01",
                "validValues": GRADE_LEVEL_VALUES,
                "short_description": (
                    "Grade: `pk`, `k`, `01`-`12`, or `all` for the entity "
                    "total (sum of the 14 grade rows)."
                ),
                "description": (
                    "Canonical grade code per data-cleaning-standards "
                    "section 16: 'pk' (pre-kindergarten), 'k' (kindergarten), "
                    "zero-padded '01'..'12', and 'all' for the entity's "
                    "pre-aggregated total row (the bronze `Total` column, "
                    "which equals the sum of the 14 grade rows bit-exact)."
                ),
            },
            {
                "name": "num_students",
                "type": "int64",
                "unit": "count",
                "key_metric": True,
                "nullable": False,
                "example": 247,
                "short_description": (
                    "FTE student headcount for the grade cell; never "
                    "suppressed, so a 0 means the grade is not offered."
                ),
                "description": (
                    "FTE student headcount for the (year, geography, period, "
                    "grade) cell. Raw count, not scaled. Never NULL — this "
                    "source publishes no suppression markers — and a 0 is a "
                    "real reported value (the grade is not offered at the "
                    "entity). For grade_level='all', equals the sum of the "
                    "entity's 14 grade rows in that period."
                ),
            },
        ],
        source="Georgia Insights (GaDOE)",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        suppressed_to_null=False,
        notes=[
            (
                "Two snapshots per school year: 'fall' is the October Cycle 1 "
                "FTE count and 'spring' is the March Cycle 3 count. Both are "
                "preserved as distinct rows via enrollment_period — filter to "
                "one period for a single headline count per year; never sum "
                "across periods."
            ),
            (
                "No suppression: every count cell in all 66 bronze files is a "
                "clean non-negative integer — zeros are real values (grade "
                "not offered), not masked cells."
            ),
            (
                "The grade_level='all' row is the bronze `Total` column, "
                "verified bit-exact equal to the sum of the 14 grade rows on "
                "every bronze row. Filter grade_level != 'all' when summing "
                "across grades to avoid double-counting."
            ),
            (
                "Per-district `System Total` rows in the School bronze file "
                "are dropped — bit-equal duplicates of the District file rows, "
                "which are the canonical district layer. Both files publish an "
                "identical State-Wide Total row per period; the transform "
                "keeps one copy."
            ),
            (
                "State-schools era split: the three state schools (Atlanta "
                "Area School for the Deaf, GA Academy for the Blind, GA School "
                "for the Deaf) report as 7-digit pseudo-districts "
                "7991893/7991894/7991895 instead of under district 799 in the "
                "split era (spring 2011-2019; fall 2012-2019); bronze "
                "identifiers are preserved as-is."
            ),
        ],
        quality_checks=[
            {
                "name": "all_equals_sum_of_grades",
                "description": (
                    "Within each (year, geography, enrollment_period) entity, "
                    "the grade_level='all' row exists and equals the sum of "
                    "the 14 individual grade rows — the bronze `Total` column "
                    "is the row-wise sum of the grade columns (verified "
                    "bit-exact on every bronze row of both periods; no "
                    "suppression, so the identity is exact with zero "
                    "tolerance)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year, district_code, "
                    "school_code, enrollment_period, MAX(CASE WHEN "
                    "grade_level = 'all' THEN num_students END) AS all_count, "
                    "SUM(CASE WHEN grade_level <> 'all' THEN num_students "
                    "ELSE 0 END) AS grade_sum FROM {object} GROUP BY year, "
                    "district_code, school_code, enrollment_period) t "
                    "WHERE t.all_count IS NULL OR t.all_count <> t.grade_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "entity_grade_block_complete",
                "description": (
                    "Every (year, geography, enrollment_period) entity "
                    "publishes the complete 15-row grade block: 'all' + 'pk' + "
                    "'k' + '01'..'12'. Bronze publishes all 15 counts (incl. "
                    "zeros) for every entity in every year — a short block "
                    "means rows were lost in transform."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year, district_code, "
                    "school_code, enrollment_period FROM {object} GROUP BY "
                    "year, district_code, school_code, enrollment_period "
                    "HAVING COUNT(*) <> 15) t"
                ),
                "mustBe": 0,
            },
            {
                "name": "enrollment_period_in_allowed_values",
                "description": (
                    "enrollment_period is exactly one of the two canonical "
                    "snapshot codes (fall, spring) — any other value means a "
                    "cycle-suffix parse or mapping regression."
                ),
                "dimension": "conformity",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE enrollment_period IS NULL "
                    "OR enrollment_period NOT IN ('fall', 'spring')"
                ),
                "mustBe": 0,
            },
            {
                "name": "both_periods_present",
                "description": (
                    "Both snapshot periods are published: the fact table "
                    "contains at least one 'fall' row and at least one "
                    "'spring' row (a single-period result would mean one "
                    "family's bronze files were dropped during the merge)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT 2 - COUNT(DISTINCT enrollment_period) FROM {object} "
                    "WHERE enrollment_period IN ('fall', 'spring')"
                ),
                "mustBe": 0,
            },
            {
                "name": "num_students_never_null",
                "description": (
                    "num_students is never NULL: this source has no "
                    "suppression — every count cell in every bronze file "
                    "parses as a non-negative integer (verified cell-by-cell "
                    "across all 66 files)."
                ),
                "dimension": "completeness",
                "query": ("SELECT COUNT(*) FROM {object} WHERE num_students IS NULL"),
                "mustBe": 0,
            },
            {
                "name": "state_equals_sum_of_districts",
                "description": (
                    "Per (year, enrollment_period, grade_level), the state row "
                    "equals the sum of all district rows — verified exact for "
                    "every grade in every year of both periods (FTE counts are "
                    "integers with no suppression, so no tolerance is needed)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, enrollment_period, grade_level, "
                    "MAX(CASE WHEN district_code IS NULL THEN num_students "
                    "END) AS state_count, "
                    "SUM(CASE WHEN district_code IS NOT NULL AND "
                    "school_code IS NULL THEN num_students ELSE 0 END) "
                    "AS district_sum "
                    "FROM {object} GROUP BY year, enrollment_period, "
                    "grade_level) t "
                    "WHERE t.state_count IS NULL "
                    "OR t.state_count <> t.district_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "schools_sum_to_district",
                "description": (
                    "Per (year, enrollment_period, district, grade_level), the "
                    "school rows sum to the district row, and every district "
                    "has both a district row and at least one school row — "
                    "verified exact for every district and grade in every year "
                    "of both periods."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, enrollment_period, district_code, "
                    "grade_level, "
                    "MAX(CASE WHEN school_code IS NULL THEN num_students "
                    "END) AS district_count, "
                    "SUM(CASE WHEN school_code IS NOT NULL THEN "
                    "num_students END) AS school_sum "
                    "FROM {object} WHERE district_code IS NOT NULL "
                    "GROUP BY year, enrollment_period, district_code, "
                    "grade_level) t "
                    "WHERE t.district_count IS NULL OR t.school_sum IS NULL "
                    "OR t.district_count <> t.school_sum"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
