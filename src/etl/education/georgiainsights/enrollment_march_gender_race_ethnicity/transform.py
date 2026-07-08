"""Transform bronze enrollment_march_gender_race_ethnicity files into gold fact tables.

Source: Georgia Insights (GaDOE) "FTE Enrollment by Race/Ethnicity and
Gender" — the March Cycle 3 (``-3``) FTE headcount of Georgia public school
students, cross-classified by gender (Female / Male) and by seven mutually
exclusive race/ethnicity buckets, for every school, district, and the state,
fiscal years 2010-2025. The companion topic
``enrollment_october_gender_race_ethnicity`` reports the same breakdown from
the October Cycle 1 count; the race/gender vocabulary both topics share lives
in ``src/etl/education/georgiainsights/_enrollment_race_lookups.py``.

Design decisions (every invariant re-verified against THIS topic's 32 bronze
CSVs during authoring — see bronze-data-structure.md):

- **Single era, two files per year.** District and School counts live in
  separate CSVs per year; all 32 files share one post-strip column set
  (School files add only ``School ID``). Bronze headers carry inconsistent
  leading/trailing whitespace — every header is ``.strip()``-ed at read.
  Each CSV opens with a 4-line preamble; the reader skips it, verifies the
  line-2 title, and cross-checks the preamble's ``Fiscal Year YYYY-3``
  against the filename year (all 32 agree). Year exists ONLY there — there
  is no year column in the data.

- **Read loss is measured, not assumed.** The local CSV reader counts the
  raw data lines (total lines minus 4 preamble minus 1 header — no quoted
  multi-line fields exist in this source) and records raw vs parsed per
  file. Verified raw == parsed for all 32 files.

- **Race x gender two-column convention** (education CLAUDE.md): bronze
  publishes a true cross-classification, so each axis is its own fact
  column — ``race`` takes canonical race keys, ``gender`` takes
  ``male``/``female``. Flattening into a single ``demographic`` column would
  fabricate cells the source does not measure.

- **Split Asian / Pacific Islander convention (section 5b)**: bronze has
  separate ``Race Asian`` and ``Race Pacific Islander`` columns in every
  file, so gold publishes the split ``asian`` / ``pacific_islander`` keys
  and never a combined rollup. ``Ethnic Hispanic`` is a non-overlapping
  ethnicity bucket (GaDOE FTE coding gives Hispanic ethnicity precedence
  over race) — the seven buckets partition total enrollment (March 2025
  state: 1,396,583 race + 340,147 Hispanic = 1,736,730 published total).
  Decision encoded once for both sibling topics in the shared lookups
  module.

- **Gender ``Total`` rows are dropped** before unpivot: ``Total`` equals
  ``Female + Male`` on every fully published cell (verified on all 115,889
  complete (geography, race) triples across 32 files — 0 violations), so
  keeping it would force every consumer to filter it out to avoid
  double-counting. Recorded per file via ``manifest.record_filtered``.

- **State rows are published twice per year** — both the District and the
  School file carry the same 3 state-aggregate rows (verified identical for
  all 16 years). The natural-key collision guard proves the twins agree,
  then ``deduplicate_by_detail_level`` keeps one copy (tie-break
  ``sort_col="num_students"`` is irrelevant for identical twins but stated
  explicitly). The drop is recorded per year via ``record_filtered``.

- **Suppression**: ``*`` is the only marker in any of the seven count
  columns across all 32 files (verified); it becomes NULL via the reader's
  ``null_values`` list. Suppression is column-by-column, not row-by-row.
  The observed floor is exactly 15 — no non-null count below 15 exists
  anywhere in bronze — and state-level cells are never suppressed; both
  facts are authored as contract quality checks.

- **Geography**: state rows carry ``System ID == ""`` (and ``School ID ==
  "State-Wide"`` in School files); empty string maps to NULL BEFORE zfill
  so it cannot masquerade as district "000". District codes are 3-digit
  standard or 7-digit charter (verified: no other shapes) — zfill(3) pads
  defensively without truncating. School codes come from the 4-digit prefix
  of ``School ID`` (``NNNN-Name``; 100%% pattern conformance verified),
  split on the first hyphen only; zfill(4) is defensive. School files
  contain no district-aggregate rows (verified 0) — guarded with a hard
  raise.

- **No section 4b masks**: counts are non-negative by construction (the
  only non-numeric bronze value is the ``*`` suppression marker) and no
  impossible values exist.

- **No demographic collisions**: the seven bronze buckets map 1:1 onto
  seven distinct canonical race keys and bronze carries no duplicate
  natural keys within any file (verified), so
  ``aggregate_demographic_collisions`` is not needed; the collision guard
  still runs before dedup and would catch any future drift.
"""

import logging
import re
from pathlib import Path

import polars as pl

from src.etl.education.georgiainsights._enrollment_race_lookups import (
    GENDER_MAP,
    GENDER_TOTAL_LABEL,
    GENDER_VALUES,
    RACE_ETHNICITY_COLUMNS,
    RACE_ETHNICITY_TO_RACE,
    RACE_VALUES,
    require_race_columns,
)
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

TOPIC = "enrollment_march_gender_race_ethnicity"
BRONZE_DIR = Path(
    "data/bronze/education/georgiainsights/enrollment_march_gender_race_ethnicity"
)
GOLD_DIR = Path("data/gold/education/enrollment_march_gender_race_ethnicity")
SOURCE_URL = "https://georgiainsights.gadoe.org/data-downloads/"

# Filename: "... Fiscal Year2010-3 District.csv" (no space before the year;
# `-3` = Cycle 3 / March). The preamble's line 2 writes the year WITH a
# space ("Fiscal Year 2010-3 Data Report") — two distinct patterns.
FILENAME_PATTERN = re.compile(r"Fiscal Year(\d{4})-3 (District|School)\.csv$")
PREAMBLE_TITLE = "FTE Enrollment by Race/Ethnicity and Gender"
PREAMBLE_YEAR_PATTERN = re.compile(r"Fiscal Year (\d{4})-3")

# Lines before the header row in every bronze CSV (masthead, title, count
# date, near-blank spacer). The header is line 5.
PREAMBLE_LINES = 4

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "race",
    "gender",
    "detail_level",
    "num_students",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "race": pl.Utf8,
    "gender": pl.Utf8,
    "detail_level": pl.Utf8,
    "num_students": pl.Int64,
}

METRIC_COLUMNS: list[str] = ["num_students"]

# Natural key for the collision guard. Includes detail_level so the expected
# state-row twins (District file copy + School file copy, identical values)
# are checked for divergence within the state level itself.
NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "race",
    "gender",
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
    means a misnamed or mis-filled file — fail loudly), reads everything as
    Utf8 (``infer_schema_length=0`` — preserves the empty-string state
    sentinel and zero-padded codes), and registers ``*`` (the source's only
    suppression marker, verified across all 32 files) as a null value.

    Returns:
        ``(df, loss)`` — the all-Utf8 frame with stripped headers and a
        read-loss dict. Raw rows are counted from the file's data lines
        (total lines minus preamble minus header); this source has no
        quoted multi-line fields, so raw == parsed is expected (verified
        for all 32 files).
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
    df = pl.read_csv(
        raw_bytes,
        skip_rows=PREAMBLE_LINES,
        infer_schema_length=0,
        null_values=["*"],
    )
    # Strip the source's inconsistent leading/trailing header whitespace
    # ("  Gender", "  Two or more Races ") so downstream code uses clean names.
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
    detail_level_source: str,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Transform one bronze file (District or School) for one year.

    Single-era topic: all 32 files share one post-strip column set; the only
    structural difference is the School files' extra ``School ID`` column,
    which maps 1:1 to the caller's ``detail_level_source``.
    """
    # Rename-coverage guard: a missing bronze column would silently become
    # NULL in gold, so absence fails loudly. Required set depends on level.
    context = f"{TOPIC} {year} {detail_level_source}"
    require_race_columns(df.columns, context)
    base_required = ["System ID", "System Name", "Gender"]
    if detail_level_source == "school":
        base_required.append("School ID")
    missing = [c for c in base_required if c not in df.columns]
    if missing:
        raise ValueError(
            f"{context}: expected bronze column(s) missing: {missing}. "
            f"Present: {sorted(df.columns)}"
        )

    # State-aggregate rows carry System ID == "" (quoted empty string in the
    # raw CSV; null-or-empty handled defensively). Everything else in a
    # District file is a district row; everything else in a School file is a
    # school row — School files carry no district-aggregate rows (verified 0
    # across all 16 years; guarded below).
    is_state = pl.col("System ID").is_null() | (pl.col("System ID") == "")
    if detail_level_source == "school":
        district_aggregates = df.filter(
            ~(pl.col("System ID").is_null() | (pl.col("System ID") == ""))
            & (pl.col("School ID") == "State-Wide")
        ).height
        if district_aggregates:
            raise ValueError(
                f"{context}: {district_aggregates} unexpected district-"
                f"aggregate row(s) (concrete System ID with School ID="
                f"'State-Wide') — unknown detail level"
            )

    df = df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.when(is_state)
        .then(pl.lit("state"))
        .otherwise(pl.lit(detail_level_source))
        .alias("detail_level"),
    )

    # Drop the redundant `Total` gender rows BEFORE the x7 unpivot: Total ==
    # Female + Male on every fully published cell (verified, 0 violations),
    # and keeping it would double-count any sum over gender.
    pre_drop = df.height
    df = df.filter(pl.col("Gender") != GENDER_TOTAL_LABEL)
    dropped_total = pre_drop - df.height
    manifest.record_filtered(
        year,
        dropped_total,
        "gender_total_rows_dropped_redundant_with_female_plus_male",
    )
    logger.info(
        "Year %d (%s): dropped %d 'Total' gender rows (= Female + Male)",
        year,
        detail_level_source,
        dropped_total,
    )

    # Gender becomes its own fact column (race x gender two-column
    # convention — education CLAUDE.md). Strict map; unmapped -> sentinel.
    bronze_gender = df["Gender"]
    df = df.with_columns(
        pl.col("Gender").replace_strict(GENDER_MAP, default="99999999").alias("gender")
    )
    manifest.record_categorical(
        column="gender",
        map_dict=GENDER_MAP,
        bronze_series=bronze_gender,
        gold_series=df["gender"],
    )

    # District code: empty-string state sentinel -> NULL BEFORE zfill
    # (otherwise "".zfill(3) would mint a phantom district "000"); zfill(3)
    # pads 3-digit standard codes and passes 7-digit charter codes through.
    district_code = (
        pl.when(is_state).then(None).otherwise(pl.col("System ID")).str.zfill(3)
    )
    if detail_level_source == "school":
        # School ID packs "NNNN-School Name"; the 4-digit code prefix is
        # extracted on the FIRST hyphen only (school names can contain
        # hyphens). State rows' "State-Wide" fails the regex -> NULL, which
        # is correct. zfill(4) is defensive (verified already 4-digit).
        school_code = pl.col("School ID").str.extract(r"^(\d{4})-", 1).str.zfill(4)
    else:
        # District files carry no school-level rows; uniform NULL keeps the
        # shared key-column shape.
        school_code = pl.lit(None).cast(pl.Utf8)
    df = df.with_columns(
        district_code.alias("district_code"),
        school_code.alias("school_code"),
        # The reader already nulled `*`; strict=False is belt-and-braces for
        # any stray non-numeric value (none observed across 32 files).
        *[
            pl.col(c).cast(pl.Int64, strict=False).alias(c)
            for c in RACE_ETHNICITY_COLUMNS
        ],
    )

    # Tidy long format (section 9): unpivot the seven wide race/ethnicity
    # count columns into (race_ethnicity_raw, num_students) pairs.
    df = df.unpivot(
        index=["year", "district_code", "school_code", "detail_level", "gender"],
        on=RACE_ETHNICITY_COLUMNS,
        variable_name="race_ethnicity_raw",
        value_name="num_students",
    )

    # Map the bronze column names to canonical race keys (shared lookups
    # module; split Asian/Pacific Islander convention — see module
    # docstring). 1:1 map, so no collision aggregation is needed.
    bronze_race = df["race_ethnicity_raw"]
    df = df.with_columns(
        pl.col("race_ethnicity_raw")
        .replace_strict(RACE_ETHNICITY_TO_RACE, default="99999999")
        .alias("race")
    )
    manifest.record_categorical(
        column="race",
        map_dict=RACE_ETHNICITY_TO_RACE,
        bronze_series=bronze_race,
        gold_series=df["race"],
    )

    return df.select(STANDARD_COLUMNS)


# =============================================================================
# File dispatcher
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read and transform one bronze CSV (read-loss accounted)."""
    match = FILENAME_PATTERN.search(path.name)
    if match is None:
        raise ValueError(
            f"Unexpected bronze filename (no 'Fiscal YearYYYY-3 "
            f"District|School.csv' suffix): {path.name}"
        )
    year = int(match.group(1))
    detail_level_source = match.group(2).lower()

    df, loss = _read_bronze_csv(path, year)
    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])
    # Single-era topic; the era name documents why there is no dispatch.
    manifest.record_file(
        path, year, "era_1_2010_2025_fte_cycle3", df.height, df.columns
    )
    manifest.record_bronze(year, df.height)

    if df.height == 0:
        logger.warning("Year %d: bronze file %s is empty, skipping", year, path.name)
        return None
    logger.info(
        "Processing %s (year %d, %s, %d rows)",
        path.name,
        year,
        detail_level_source,
        df.height,
    )
    return _transform_file_frame(df, year, detail_level_source, manifest)


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

    # 3. Collision guard BEFORE dedup: the only expected duplicate keys are
    # the state-row twins (each year's District and School file both carry
    # the 3 state rows — verified identical for all 16 years). The guard
    # tolerates identical twins and raises on divergent values, so a future
    # mismatch between the two files surfaces instead of being deduped away.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )

    # Record the state-twin removal per year before dedup erases the
    # evidence: per year, 2 gender x 7 race = 14 duplicate state rows drop.
    state_dupes = (
        combined.filter(pl.col("detail_level") == "state")
        .group_by("year")
        .agg((pl.len() - pl.struct(["race", "gender"]).n_unique()).alias("dupes"))
        .sort("year")
    )
    for row in state_dupes.iter_rows(named=True):
        manifest.record_filtered(
            int(row["year"]),
            int(row["dupes"]),
            "duplicate_state_rows_district_and_school_files_both_publish_them",
        )

    # Tie-break: state twins are value-identical (guard above proves it), so
    # the winner is irrelevant; sort_col="num_students" states the
    # preference explicitly (keep the row with a reported, larger count).
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code", "race", "gender"],
        district_keys=["year", "district_code", "race", "gender"],
        state_keys=["year", "race", "gender"],
        sort_col="num_students",
    )

    # 4. Geography nulling (shared domain rules — transform and validator
    # read the same dict, so they cannot disagree). No section 4b masks:
    # counts are non-negative by construction and no impossible values
    # exist (see module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. Suppression rates drift slowly across years (the
    # multiracial population grows, so its suppression falls) — the spike
    # check warns if any year is anomalous.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(
        combined, required_non_null=["year", "detail_level", "race", "gender"]
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
            "Georgia Insights (GaDOE) FTE Enrollment by Race/Ethnicity and "
            "Gender — the March Cycle 3 FTE headcount of Georgia public "
            "school students, cross-classified by gender and by seven "
            "mutually exclusive race/ethnicity buckets (Hispanic, American "
            "Indian, Asian, Black, Pacific Islander, White, Two or more "
            "Races), for every school, district, and the state, fiscal "
            "years 2010-2025. This is the spring snapshot; the companion "
            "topic enrollment_october_gender_race_ethnicity reports the "
            "October Cycle 1 count. Source gender `Total` rows are dropped "
            "(redundant with Female + Male)."
        ),
        title="March Enrollment by Race and Gender",
        summary=(
            "Public school student headcounts by race/ethnicity and gender "
            "from the March FTE count, per school, district, and state, "
            "2010-2025."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2025,
                "description": (
                    "Fiscal year of the March FTE count (2025 = March 2025, "
                    "i.e. the 2024-2025 school year). Sourced from the "
                    "bronze filename, cross-checked against each file's "
                    "preamble."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "3-digit GOSA district code (zero-padded) for standard "
                    "districts; 7-digit code for state charters. NULL for "
                    "state-level rows. FK to districts dimension."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0103",
                "description": (
                    "4-digit GOSA school code, extracted from the bronze "
                    "`School ID` (`NNNN-Name`) prefix. NULL for state- and "
                    "district-level rows. FK to schools dimension "
                    "(composite key with district_code)."
                ),
            },
            {
                "name": "race",
                "type": "string",
                "nullable": False,
                "example": "black",
                "validValues": RACE_VALUES,
                "short_description": (
                    "One of seven mutually exclusive race/ethnicity buckets; "
                    "Hispanic is a separate bucket, not a race overlay."
                ),
                "description": (
                    "Race/ethnicity bucket (canonical race demographic "
                    "keys, published as `race` because this topic is a "
                    "race x gender cross-classification). Split "
                    "Asian/Pacific Islander convention: `asian` and "
                    "`pacific_islander` are separate buckets, never the "
                    "combined rollup. `hispanic` is a non-overlapping "
                    "ethnicity bucket — GaDOE FTE coding gives Hispanic "
                    "ethnicity precedence over race, so a Hispanic student "
                    "is counted ONLY under `hispanic` and the seven values "
                    "partition total enrollment; do not treat `hispanic` "
                    "as a Hispanic-of-any-race overlay."
                ),
            },
            {
                "name": "gender",
                "type": "string",
                "nullable": False,
                "example": "female",
                "validValues": GENDER_VALUES,
                "short_description": (
                    "Student gender, female or male; the source's redundant "
                    "Total rows are dropped."
                ),
                "description": (
                    "Student gender (`female` / `male`). The source's "
                    "third value, `Total`, equals Female + Male on every "
                    "fully published cell and is dropped during transform."
                ),
            },
            {
                "name": "num_students",
                "type": "int64",
                "unit": "count",
                "key_metric": True,
                "example": 309028,
                "null_meaning": (
                    "Suppressed by GaDOE (bronze `*` marker) — small cells "
                    "below the 15-student floor. Suppression is per "
                    "race/ethnicity cell, not per row."
                ),
                "short_description": (
                    "FTE student headcount for the race x gender cell; NULL "
                    "means suppressed (small cell), not zero."
                ),
                "description": (
                    "FTE student headcount for the (year, geography, race, "
                    "gender) cell. Raw count, not scaled. NULL when "
                    "suppressed in source; every non-null value is >= 15 "
                    "(the observed suppression floor across all 32 bronze "
                    "files). State-level cells are never suppressed."
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
                "Hispanic is a separate, non-overlapping ethnicity bucket "
                "— not a Hispanic-of-any-race overlay. The six race buckets "
                "are non-Hispanic. Verified for March 2025 state totals: "
                "1,396,583 (six race buckets) + 340,147 (Hispanic) = "
                "1,736,730 = published statewide FTE enrollment."
            ),
            (
                "Source `Total` gender rows are dropped (Total = Female + "
                "Male on all 115,889 fully published cells across 32 bronze "
                "files — 0 violations). Sum the two gold gender rows to "
                "reconstruct totals, modulo NULL suppression."
            ),
            (
                "Suppression marker `*` becomes NULL. Suppression is "
                "column-by-column per race/ethnicity bucket — a geography "
                "can have some buckets suppressed and others published. "
                "American Indian and Pacific Islander are heavily "
                "suppressed at the school level (~99.9%% in 2025); the "
                "observed floor is 15 (no non-null count below 15 exists "
                "anywhere in bronze)."
            ),
            (
                "Both the District and the School bronze CSV for each year "
                "publish identical copies of the 3 state-aggregate rows "
                "(verified equal for all 16 years); the transform keeps "
                "one copy, so gold state rows are unique per (year, race, "
                "gender)."
            ),
        ],
        quality_checks=[
            {
                "name": "num_students_above_suppression_floor",
                "description": (
                    "Every non-null num_students is at or above 15 — the "
                    "observed GaDOE small-cell suppression floor (verified: "
                    "the minimum non-null value across all 32 bronze files "
                    "2010-2025 is exactly 15; smaller cells are suppressed "
                    "to `*`)."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE num_students IS NOT NULL AND num_students < 15"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_rows_never_suppressed",
                "description": (
                    "State-level cells are never suppressed: every "
                    "(year, race, gender) state row carries a non-null "
                    "num_students (verified: 0 suppressed state cells "
                    "across all 32 bronze files)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE district_code IS NULL AND school_code IS NULL "
                    "AND num_students IS NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_race_gender_partition_complete",
                "description": (
                    "Every year publishes the complete state-level race x "
                    "gender cross-classification: exactly 14 state rows "
                    "(7 race/ethnicity buckets x 2 genders) per year, "
                    "after the duplicate state copies from the District "
                    "and School files are reduced to one."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year FROM {object} "
                    "WHERE district_code IS NULL AND school_code IS NULL "
                    "GROUP BY year HAVING COUNT(*) <> 14) AS bad_years"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
