"""Transform bronze enrollment_october_disability files into gold facts.

Source: Georgia Insights (GaDOE) "FTE Enrollment by Grade Disability" — the
October Cycle 1 (``-1``) FTE headcount of Georgia public school students
receiving special-education services, broken out by the 17 GaDOE/IDEA
disability categories at the **district level only**, fiscal years
2014-2026. Despite "by Grade" in the filename, the files carry no per-grade
breakdown — only district x disability category.

Design decisions (every invariant re-verified against THIS topic's 13
bronze CSVs during authoring — see bronze-data-structure.md):

- **Single era, one District file per year.** All 13 files share one
  post-strip column set: ``System ID``, ``System Name``, and the 17
  disability code columns (AUT .. VI) in fixed order. Bronze headers carry
  inconsistent leading/trailing whitespace (`` System Name``, ``  BL``,
  ``VI ``) — every header is stripped at read. Each CSV opens with a 4-line
  GaDOE preamble; the local reader skips it, verifies the line-2 title, and
  cross-checks the preamble's ``Fiscal Year YYYY-1`` against the filename
  year (all 13 agree). Year exists ONLY there — there is no year column in
  the data.

- **Read loss is measured, not assumed.** The local CSV reader counts the
  raw data lines (total lines minus 4 preamble minus 1 header — no quoted
  multi-line fields exist in this source) and records raw vs parsed per
  file. Verified raw == parsed for all 13 files.

- **District-only topic.** No state-aggregate row and no school rows exist
  in any file (re-verified: every ``System ID`` is a 3-digit standard or
  7-digit charter/specialty code — no blank/whitespace state sentinel, no
  other shapes). Only ``districts.parquet`` is emitted per year; per the
  education domain convention the fact still carries an always-NULL
  ``school_code`` so every education fact shares the key-column shape,
  guarded by the ``school_code_always_null`` contract check.

- **``*`` is the only suppression marker.** Re-verified cell-by-cell: every
  disability cell in all 13 files is either an unpadded integer or ``*``
  (no empty strings, no whitespace padding, no other markers). ``*`` means
  the true count is non-zero but below 10 (GaDOE small-cell rule): every
  non-suppressed value is >= 10, and each file's overall minimum is exactly
  10 (re-verified; per-COLUMN minimums range 10-15, and the structure doc's
  stronger "exactly 10 in every column" claim is corrected there), so gold
  enforces ``num_students IS NULL OR >= 10`` via the
  ``num_students_respects_suppression_floor`` contract check. The ``DB``
  (deaf_blind) column is 100%% suppressed in all 13 years — deaf_blind
  rows exist but num_students is always NULL. Suppressed cells become
  NULL (rows preserved) — standard section 8 handling, not a section 4b
  mask, so no ``record_masked`` entry.

- **No published total column / no 'all' category.** Bronze publishes only
  the 17 per-category counts — no row-wise total, no state row, no school
  rows — so there is no partition-sums or hierarchy-reconciliation check
  to author (section 15b shapes verified inapplicable). The structural
  facts that DO hold (17-category block per district, suppression floor,
  always-NULL school_code) are authored as contract checks instead.

- **Disability is modeled as a ``demographic`` FK.** The 17 IDEA category
  codes split the fixed population "students receiving special-education
  services" by primary exceptionality; they are published in the
  ``demographic`` column as an FK into the global demographics dimension's
  ``disability`` demographic_category. Codes map 1:1 to the dimension's
  snake_case disability values via the topic-local
  ``DISABILITY_CATEGORY_MAP`` (17 in -> 17 out, no collisions), recorded in
  the manifest with zero unmapped values. There is no ``all`` row — this
  topic publishes only the 17 disability categories, at the district level.

- **Blank ``System Name`` for IDs 7991893/7991894/7991895 (2014-2019).**
  The three state schools (Atlanta Area School for the Deaf, GA Academy
  for the Blind, GA School for the Deaf) appear as 7-digit
  pseudo-districts with empty-string names in 2014-2019, then drop out of
  this report from 2020. They are real records with non-suppressed counts;
  names are a dimension concern (the districts dimension carries
  hand-coded names for these IDs), so the rows pass through untouched.

- **No collisions, no dedup expected.** Each year's file carries one row
  per ``System ID`` (re-verified: zero duplicate IDs in any file) and
  years never overlap, so the collision guard expects zero duplicate keys;
  ``deduplicate_by_detail_level`` still runs with an explicit tie-break
  (``sort_col="num_students"`` — prefer the row with a reported count)
  purely as drift protection.

- **No section 4b masks**: suppressed cells aside, every count parses as a
  non-negative integer; no impossible values exist in any file.
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

TOPIC = "enrollment_october_disability"
BRONZE_DIR = Path("data/bronze/education/georgiainsights/enrollment_october_disability")
GOLD_DIR = Path("data/gold/education/enrollment_october_disability")
SOURCE_URL = "https://georgiainsights.gadoe.org/data-downloads/"

# Filename: "... Fiscal Year2014-1 District.csv" (no space before the year;
# `-1` = Cycle 1 / October). The preamble's line 2 writes the year WITH a
# space ("Fiscal Year 2014-1 Data Report") — two distinct patterns.
FILENAME_PATTERN = re.compile(r"Fiscal Year(\d{4})-1 District\.csv$")
PREAMBLE_TITLE = "FTE Enrollment by Disability"
PREAMBLE_YEAR_PATTERN = re.compile(r"Fiscal Year (\d{4})-1")

# Lines before the header row in every bronze CSV (masthead, title, count
# date, near-blank spacer). The header is line 5.
PREAMBLE_LINES = 4

# GaDOE/IDEA disability category code -> canonical snake_case gold value.
# The 17 codes are the post-strip bronze column headers, byte-identical in
# fixed order across all 13 files (verified). 1:1 map — no collisions.
DISABILITY_CATEGORY_MAP: dict[str, str] = {
    "AUT": "autism",
    "BL": "blind_low_vision",
    "D": "deaf",
    "DB": "deaf_blind",
    "EBD": "emotional_behavioral_disorder",
    "HH": "hospital_homebound",
    "MID": "mild_intellectual_disability",
    "MoID": "moderate_intellectual_disability",
    "OHI": "other_health_impairment",
    "OI": "orthopedic_impairment",
    "PID": "profound_intellectual_disability",
    "SDD": "significant_developmental_delay",
    "SI": "speech_language_impairment",
    "SID": "severe_intellectual_disability",
    "SLD": "specific_learning_disability",
    "TBI": "traumatic_brain_injury",
    "VI": "visual_impairment",
}

# Bronze disability columns in source order (the unpivot `on` list).
DISABILITY_COLUMNS: list[str] = list(DISABILITY_CATEGORY_MAP.keys())

# Canonical disability vocabulary this topic publishes — the snake values
# the map produces are exactly the demographics dimension's `disability`
# demographic_category codes (contract enum / FK allowed values).
DISABILITY_CATEGORY_VALUES: list[str] = sorted(DISABILITY_CATEGORY_MAP.values())

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "detail_level",
    "num_students",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "demographic": pl.Utf8,
    "detail_level": pl.Utf8,
    "num_students": pl.Int64,
}

METRIC_COLUMNS: list[str] = ["num_students"]

# Natural key for the collision guard. One file per year with unique System
# IDs (verified) -> zero duplicate keys expected; the guard is drift
# protection.
NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "detail_level",
]


# =============================================================================
# Bronze reading
# =============================================================================


def _read_bronze_csv(path: Path, year: int) -> tuple[pl.DataFrame, dict]:
    """Read one bronze CSV: verify the preamble, strip headers, count loss.

    The shared ``read_bronze_file`` cannot skip the 4-line GaDOE preamble,
    so this local reader handles it: it verifies the line-2 title and
    cross-checks the preamble year against the filename year (a mismatch
    means a misnamed or mis-filled file — fail loudly), and reads everything
    as Utf8 (``infer_schema_length=0`` — preserves the ``*`` suppression
    marker and unpadded code strings). No ``null_values`` list is
    registered: ``*`` is converted explicitly downstream after a
    digits-or-asterisk conformance guard.

    Returns:
        ``(df, loss)`` — the all-Utf8 frame with stripped headers and a
        read-loss dict. Raw rows are counted from the file's data lines
        (total lines minus preamble minus header); this source has no
        quoted multi-line fields, so raw == parsed is expected (verified
        for all 13 files).
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
    # Strip the source's inconsistent header whitespace (" System Name",
    # "  BL", "VI ") so downstream code uses clean names.
    df = df.rename({c: c.strip() for c in df.columns})

    raw_rows = len(lines) - PREAMBLE_LINES - 1  # minus header line
    loss = {"raw_rows": raw_rows, "parsed_rows": df.height, "format": "csv"}
    return df, loss


# =============================================================================
# Per-file transform (single era)
# =============================================================================


def _transform_file_frame(
    df: pl.DataFrame,
    year: int,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Transform one bronze District file for one year.

    Single-era topic: all 13 files share one post-strip column set, so there
    is no era dispatch — this is the only shape.
    """
    context = f"{TOPIC} {year}"
    # Rename-coverage guard: a missing bronze column would silently vanish
    # from the unpivot (losing a whole disability category), so absence
    # fails loudly.
    required = {"System ID", "System Name", *DISABILITY_COLUMNS}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(
            f"{context}: expected bronze column(s) missing: {missing}. "
            f"Present: {sorted(df.columns)}"
        )

    # Every System ID must be a 3-digit standard or 7-digit
    # charter/specialty code (verified: no state sentinel, no other shapes
    # in any file). An unexpected shape — e.g. a whitespace state row
    # appearing in a future refresh — fails loudly instead of being minted
    # into a phantom district by zfill.
    bad_ids = df.filter(~pl.col("System ID").str.contains(r"^(\d{3}|\d{7})$"))
    if bad_ids.height:
        raise ValueError(
            f"{context}: {bad_ids.height} row(s) with unexpected System ID "
            f"shape (not 3 or 7 digits): "
            f"{bad_ids['System ID'].head(5).to_list()}"
        )

    # Cell-conformance guard: every disability cell must be digits or the
    # `*` suppression marker (verified for all 13 files). Anything else
    # would silently become NULL in the strict=False cast below — fail
    # loudly so a new marker is classified deliberately.
    nonconforming = df.select(
        pl.sum_horizontal(
            ~pl.col(c).str.contains(r"^(\*|\d+)$") for c in DISABILITY_COLUMNS
        ).sum()
    ).item()
    if nonconforming:
        raise ValueError(
            f"{context}: {nonconforming} disability cell(s) are neither "
            f"digits nor the '*' suppression marker"
        )

    suppressed = df.select(
        pl.sum_horizontal((pl.col(c) == "*").sum() for c in DISABILITY_COLUMNS)
    ).item()
    logger.info(
        "Year %d: %d of %d disability cells suppressed ('*' -> NULL)",
        year,
        suppressed,
        df.height * len(DISABILITY_COLUMNS),
    )

    df = df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        # District-only topic — every row is a district row.
        pl.lit("district").alias("detail_level"),
        # zfill(3) pads 3-digit standard codes and passes 7-digit
        # charter/specialty codes through unchanged (never truncate).
        pl.col("System ID").str.zfill(3).alias("district_code"),
        # No school-level data exists; uniform NULL keeps the shared
        # education key-column shape (education CLAUDE.md).
        pl.lit(None).cast(pl.Utf8).alias("school_code"),
        # `*` (suppressed: true count 1-9) -> NULL via strict=False; the
        # conformance guard above proves nothing else can be coerced.
        *[pl.col(c).cast(pl.Int64, strict=False).alias(c) for c in DISABILITY_COLUMNS],
    )

    # Tidy long format (section 9): one row per (year, district, disability
    # category). The 17 bronze code columns become `demographic` values
    # (FK to the demographics dimension's `disability` category) via the 1:1
    # topic-local map.
    long_df = df.unpivot(
        index=["year", "district_code", "school_code", "detail_level"],
        on=DISABILITY_COLUMNS,
        variable_name="disability_code",
        value_name="num_students",
    )
    bronze_codes = long_df["disability_code"]
    long_df = long_df.with_columns(
        pl.col("disability_code")
        .replace_strict(DISABILITY_CATEGORY_MAP, default=None)
        .alias("demographic")
    )
    manifest.record_categorical(
        column="demographic",
        map_dict=DISABILITY_CATEGORY_MAP,
        bronze_series=bronze_codes,
        gold_series=long_df["demographic"],
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
            f"Unexpected bronze filename (no 'Fiscal YearYYYY-1 "
            f"District.csv' suffix): {path.name}"
        )
    year = int(match.group(1))

    df, loss = _read_bronze_csv(path, year)
    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])
    # Single-era topic; the era name documents why there is no dispatch.
    manifest.record_file(
        path, year, "era_1_2014_2026_fte_cycle1_disability", df.height, df.columns
    )
    manifest.record_bronze(year, df.height)

    if df.height == 0:
        logger.warning("Year %d: bronze file %s is empty, skipping", year, path.name)
        return None
    logger.info("Processing %s (year %d, %d rows)", path.name, year, df.height)
    return _transform_file_frame(df, year, manifest)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for this topic."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file (one District file per year).
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

    # 3. Collision guard BEFORE dedup: one file per year with unique System
    # IDs (verified) -> zero duplicate keys expected; any duplicate with
    # divergent counts raises here instead of being deduped away.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )

    # Tie-break: no duplicates exist (guard above), so the winner is
    # irrelevant; sort_col="num_students" states the preference explicitly
    # (keep the row with a reported, larger count) as drift protection.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code", "demographic"],
        district_keys=["year", "district_code", "demographic"],
        state_keys=["year", "demographic"],
        sort_col="num_students",
    )

    # 4. Geography nulling (shared domain rules — transform and validator
    # read the same dict, so they cannot disagree). District rows keep
    # district_code and have school_code NULL — already true by
    # construction. No section 4b masks (see module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. num_students is NOT required non-null — `*`
    # suppression (counts 1-9) legitimately NULLs it.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(
        combined,
        required_non_null=["year", "detail_level", "demographic"],
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
            "Georgia Insights (GaDOE) FTE Enrollment by Disability — the "
            "October Cycle 1 FTE headcount of Georgia public school "
            "students receiving special-education services, broken out by "
            "the 17 GaDOE/IDEA disability categories (autism, specific "
            "learning disability, speech-language impairment, etc.) at the "
            "school-district level, fiscal years 2014-2026. District-only: "
            "the source publishes no state aggregate and no school-level "
            "rows. Counts below 10 are suppressed to NULL by the source's "
            "small-cell rule."
        ),
        title="Special Education Enrollment by Disability",
        summary=(
            "District-level headcounts of students in special education by "
            "the 17 IDEA disability categories, from the October FTE count, "
            "2014-2026."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2026,
                "description": (
                    "Fiscal year of the October FTE count (2026 = October "
                    "2025, i.e. the 2025-2026 school year). Sourced from "
                    "the bronze filename, cross-checked against each "
                    "file's preamble."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "nullable": False,
                "example": "601",
                "description": (
                    "3-digit GOSA district code (zero-padded) for standard "
                    "districts; 7-digit code for state charters and "
                    "specialty schools, including the 2014-2019 "
                    "pseudo-districts 7991893/7991894/7991895 for the "
                    "three state schools (published with blank names by "
                    "the source; named in the districts dimension). Never "
                    "NULL — this topic has no state-level rows. FK to "
                    "districts dimension."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "description": (
                    "Always NULL — GaDOE publishes this disability "
                    "breakdown at the district level only. The column is "
                    "kept so every education fact table shares the same "
                    "key-column shape."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "specific_learning_disability",
                "validValues": DISABILITY_CATEGORY_VALUES,
                "short_description": (
                    "One of 17 IDEA disability categories (e.g. autism, "
                    "specific learning disability); no `all` total row."
                ),
                "description": (
                    "Primary exceptionality — the GaDOE/IDEA disability "
                    "category (FK to the global demographics dimension's "
                    "'disability' demographic_category). One of 17 "
                    "snake_case values mapped 1:1 from the bronze code "
                    "columns (AUT -> autism, SLD -> "
                    "specific_learning_disability, ...). Every row's "
                    "population is students receiving special-education "
                    "services, split by their single primary disability. "
                    "This topic publishes only the 17 disability categories "
                    "at the district level — there is no 'all' total row "
                    "(the source publishes none)."
                ),
            },
            {
                "name": "num_students",
                "type": "int64",
                "unit": "count",
                "key_metric": True,
                "example": 247,
                "null_meaning": (
                    "Suppressed by the source's small-cell rule: the true "
                    "count is non-zero but below 10."
                ),
                "short_description": (
                    "Count of special-education students in the disability "
                    "category; NULL means suppressed (count 1-9), not zero."
                ),
                "description": (
                    "FTE headcount of students served in the disability "
                    "category for the (year, district) cell. Raw count, "
                    "not scaled. NULL means the source suppressed the "
                    "cell ('*': true count 1-9); every published value is "
                    ">= 10 (verified in every column of every year)."
                ),
            },
        ],
        source="Georgia Insights (GaDOE)",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        notes=[
            (
                "District-only topic: the source publishes no state "
                "aggregate row and no school-level file. school_code is "
                "always NULL; summing district rows is the only way to "
                "approximate a state figure, and it undercounts because "
                "suppressed cells (counts 1-9) are NULL."
            ),
            (
                "Small-cell suppression: '*' (the only marker, verified "
                "across all 13 files) means the true count is 1-9; every "
                "published value is >= 10 and each year's overall minimum "
                "is exactly 10. Suppressed cells are NULL in gold; rows "
                "are preserved."
            ),
            (
                "deaf_blind is 100% suppressed in every year (no Georgia "
                "district ever reports 10+ deaf-blind FTE students), so "
                "its num_students is always NULL — the rows are kept to "
                "preserve the complete 17-category block."
            ),
            (
                "Despite 'by Grade Disability' in the bronze filenames, "
                "the files contain no per-grade breakdown — only district "
                "x disability category."
            ),
            (
                "IDs 7991893/7991894/7991895 (the three state schools) "
                "appear 2014-2019 with blank names in bronze, then drop "
                "out of this report from 2020. Their rows are kept; names "
                "resolve via the districts dimension."
            ),
        ],
        quality_checks=[
            {
                "name": "school_code_always_null",
                "description": (
                    "Structural fact: this is a district-only topic — "
                    "GaDOE publishes no school-level disability breakdown, "
                    "so school_code is NULL on every row."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE school_code IS NOT NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "district_block_complete_17_categories",
                "description": (
                    "Every (year, district) entity publishes the complete "
                    "17-category disability block — bronze carries all 17 "
                    "columns for every district row in every year "
                    "(suppressed cells included as NULL), so a short block "
                    "means rows were lost in transform."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year, district_code "
                    "FROM {object} GROUP BY year, district_code "
                    "HAVING COUNT(*) <> 17) t"
                ),
                "mustBe": 0,
            },
            {
                "name": "num_students_respects_suppression_floor",
                "description": (
                    "Suppression behavior: GaDOE suppresses counts below "
                    "10 to '*' (NULL in gold), so every published "
                    "num_students is >= 10 — verified for every cell of "
                    "every bronze year (each file's overall minimum is "
                    "exactly 10). A value 0-9 would mean the suppression "
                    "handling broke."
                ),
                "dimension": "accuracy",
                "query": ("SELECT COUNT(*) FROM {object} WHERE num_students < 10"),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
