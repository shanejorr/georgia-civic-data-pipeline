"""Transform bronze english_learner_exit_rate files into gold fact tables.

Source: Governor's Office of Student Achievement (GOSA) — annual English
Learner (EL) program exit activity, FY2019-FY2024 (FY2024 = the 2023-24
school year). For every Georgia LEA (standard districts, state/commission
charter LEAs, and state-agency systems) plus one statewide aggregate row per
fiscal year, three metrics are published:

    - ``num_el_exits``    — EL students who exited the EL program.
    - ``num_el_students`` — total EL enrollment for the fiscal year.
    - ``el_exit_rate``     — exit rate, 0-1 scale (bronze 0-100, /100 per §4).

Bronze layout: 12 CSVs — ``district_FY{YYYY}.csv`` + ``state_FY{YYYY}.csv``
for each of FY2019-FY2024. The bronze is the merged product of two legacy
GOSA topics (``_district_level`` + ``_state_level``); a third legacy topic
(``_3yr_for_report_card``, FY2021-FY2024) republished identical values and
was dropped during the merge (row-by-row diff: zero mismatches — see
bronze-data-structure.md "Provenance").

Design decisions (from bronze-data-structure.md and data-cleaning-standards;
authored non-interactively — judgment calls recorded here):

- **Filename-prefix routing is mandatory, era detection within each group.**
  The district FY2023 file and the state FY2023 file carry IDENTICAL column
  sets (#RPT_NAME, FISCAL_YEAR, SYSTEM_ID, SYSTEM_NAME + the three metrics),
  so column-only routing cannot distinguish them. Files route by the
  ``district_`` / ``state_`` filename prefix; within each group the era is
  detected by column signature (resilient to a republication that adds or
  drops ``#RPT_NAME`` for a different year):
    - District Era 1 (FY2019-2022, FY2024): 6 columns, no ``#RPT_NAME``.
    - District Era 2 (FY2023): Era 1 + a constant ``#RPT_NAME`` column.
    - State Era 1 (FY2019-2021): ``STATE_``-prefixed metric columns.
    - State Era 2 (FY2022, FY2024): unprefixed metric columns.
    - State Era 3 (FY2023): Era 2 + constant ``#RPT_NAME`` / ``SYSTEM_ID`` /
      ``SYSTEM_NAME`` columns (all ``"State of Georgia"`` or the report
      name) — dropped; the state role is encoded by detail_level + NULL keys.
- **Suppression**: the literal ``TFS`` ("too few students") in district
  files only; ``read_bronze_file`` nulls it via SUPPRESSION_VALUES. State
  rows are never suppressed (statewide EL enrollment >100k). Verified
  suppression hierarchy: EL_STUDENT_COUNT is suppressed only when
  EL_EXIT_COUNT is too (zero rows with a count and no enrollment) — pinned
  by student_count_null_implies_exit_count_null.
- **FY2024 EL_EXIT_RATE quirk (§4b-adjacent mask).** In FY2019-2023 the
  rate is co-suppressed with the counts (all three cells read ``TFS``
  together). In FY2024 GOSA published a numeric EL_EXIT_RATE for every
  district row — including 130 rows where EL_EXIT_COUNT is TFS. The
  published rates on those 130 rows span 0-100 (65 read ``0``); 57 of the
  130 also suppress EL_STUDENT_COUNT, among them Ivy Preparatory Academy
  (SYSTEM_ID 7820612) with both counts TFS and the rate reading ``100``.
  Those rates are not derivable from suppressed counts and cannot
  be verified, so they are treated as suppressed: ``_null_unverifiable_rates``
  NULLs ``el_exit_rate`` wherever either count is NULL (a no-op in
  2019-2023, 130 cells masked in 2024 — recorded via
  ``manifest.record_masked``). This pins one uniform suppression invariant
  across all years: rate present <=> both counts present (quality checks
  el_exit_rate_requires_counts + el_exit_rate_present_when_counts_present).
- **Rate is a bounded proportion, not rounded.** Bronze publishes 0-100
  (district: one decimal; state: two decimals); divided by 100 per §4 and
  carried at full float precision — verified bronze range 0-100, so the
  scaled value is within [0, 1] (``unit: proportion``). Reconciliation:
  |rate - exit/students| <= 0.0006 on the 0-1 scale wherever all three are
  published (one-decimal rounding on the 0-100 scale bounds the error at
  0.0005; observed max deviation 0.00050000000000071 — float epsilon
  included in the tolerance).
- **District code formatting**: ``SYSTEM_ID`` cast to Utf8 + ``zfill(3)``
  pads standard 3-digit codes (601-899) and preserves 7-digit charter /
  state-school codes unchanged; never truncate. Charter LEAs (782xxxx /
  783xxxx), the combined State Schools row (799, FY2021+), the individual
  ``State Schools-…`` rows (7991893-7991895, FY2019 only — FY2020
  publishes no State Schools rows at all), and state agencies (890) are
  all first-class district rows — preserve bronze granularity, no
  cross-era synthesis of either State Schools representation.
- **District 890 (Dept. of Corrections) has a NULL SYSTEM_NAME in FY2023**
  with all metrics suppressed; the row is emitted (names live in the
  districts dimension, which resolves 890 via DISTRICT_NAME_OVERRIDES).
- **No demographic column** (§5): no race/gender/economic breakdowns exist
  in any era — every row is the all-EL-students total. Consequently this
  transform applies **no categorical recodings at all** (no demographic, no
  subject, no grade), so ``manifest.record_categorical`` is never called and
  the manifest's categorical_mappings section is empty by design.
- **District-and-state geography; ``school_code`` always NULL** per
  ``src/etl/education/CLAUDE.md`` (pinned by school_code_always_null).
  No school-level detail exists for this metric.
- **``detail_level`` is transient**: carried through dedup / geography
  nulling / export splitting, then dropped by ``export_to_parquet`` (the
  detail level is encoded in the output filename — districts.parquet /
  states.parquet — per the education domain conventions and validator
  check 5, which forbids the column in fact tables).
- **No state-vs-district-sum reconciliation check**: most district rows are
  suppressed (54-62%% of exit counts per year), so non-suppressed district
  sums cannot reconstruct the state total — the shape does not apply.
- **Dedup tie-break**: one bronze file per (file group, fiscal year) with
  unique SYSTEM_IDs in every district file (verified: zero duplicates), so
  no duplicate keys are expected; ``sort_col="num_el_exits"`` is the
  documented safety net — prefer a row with a populated exit count over a
  hypothetical all-null placeholder.
- **Year**: from the in-file FISCAL_YEAR column (already the ending
  calendar year; FY2024 = 2023-24 school year), required to be a single
  value per file and cross-checked against the filename year — a mismatch
  raises.
"""

import logging
from pathlib import Path

import polars as pl

from src.utils.metadata import write_data_dictionary
from src.utils.readers import (
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

TOPIC = "english_learner_exit_rate"
BRONZE_DIR = Path("data/bronze/education/gosa/english_learner_exit_rate")
GOLD_DIR = Path("data/gold/education/english_learner_exit_rate")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# District-group era signatures, most-specific first: Era 2's signature
# (presence of #RPT_NAME) is a strict superset of Era 1's, so it must lead.
DISTRICT_ERA_SIGNATURES: dict[str, list[str]] = {
    "district_era_2_rpt_name": [
        "#RPT_NAME",
        "FISCAL_YEAR",
        "SYSTEM_ID",
        "EL_EXIT_COUNT",
        "EL_STUDENT_COUNT",
        "EL_EXIT_RATE",
    ],
    "district_era_1_no_rpt_name": [
        "FISCAL_YEAR",
        "SYSTEM_ID",
        "EL_EXIT_COUNT",
        "EL_STUDENT_COUNT",
        "EL_EXIT_RATE",
    ],
}

# State-group era signatures, most-specific first: Era 3 (#RPT_NAME present)
# is a strict superset of Era 2; Era 1 is keyed on the STATE_ prefix; Era 2
# (the most generic unprefixed signature) is last.
STATE_ERA_SIGNATURES: dict[str, list[str]] = {
    "state_era_3_rpt_name": [
        "#RPT_NAME",
        "FISCAL_YEAR",
        "EL_EXIT_COUNT",
        "EL_STUDENT_COUNT",
        "EL_EXIT_RATE",
    ],
    "state_era_1_state_prefix": [
        "FISCAL_YEAR",
        "STATE_EL_EXIT_COUNT",
        "STATE_EL_STUDENT_COUNT",
        "STATE_EL_EXIT_RATE",
    ],
    "state_era_2_no_prefix": [
        "FISCAL_YEAR",
        "EL_EXIT_COUNT",
        "EL_STUDENT_COUNT",
        "EL_EXIT_RATE",
    ],
}

# Columns each era handler must drop / rename before the shared gold body.
# State Era 3's SYSTEM_ID / SYSTEM_NAME are the constant "State of Georgia"
# sentinel — the state role is encoded by detail_level + NULL geography keys.
STATE_PREFIX_RENAMES: dict[str, str] = {
    "STATE_EL_EXIT_COUNT": "EL_EXIT_COUNT",
    "STATE_EL_STUDENT_COUNT": "EL_STUDENT_COUNT",
    "STATE_EL_EXIT_RATE": "EL_EXIT_RATE",
}

# Gold fact column order. `detail_level` is transient — carried through
# dedup / geography-nulling / export splitting, then dropped by
# export_to_parquet (detail is encoded in the output filename).
# No `demographic` column — no demographic breakdowns exist in any era (§5).
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "num_el_exits",
    "num_el_students",
    "el_exit_rate",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "num_el_exits": pl.Int64,
    "num_el_students": pl.Int64,
    "el_exit_rate": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = [
    "num_el_exits",
    "num_el_students",
    "el_exit_rate",
]

NATURAL_KEYS: list[str] = ["year", "district_code", "school_code", "detail_level"]


# =============================================================================
# Shared gold body (district and state rows differ only in the geography key)
# =============================================================================


def _to_gold(df: pl.DataFrame, year: int, detail_level: str) -> pl.DataFrame:
    """Project a prepared bronze frame onto the gold fact columns.

    The caller has already dropped era-specific constants and renamed the
    STATE_-prefixed columns, so every frame arrives with the three canonical
    uppercase metric columns (district frames additionally carry SYSTEM_ID).

    Args:
        df: All-Utf8 bronze frame (TFS already NULLed by read_bronze_file).
        year: Fiscal year, validated against FISCAL_YEAR and the filename.
        detail_level: ``"district"`` or ``"state"`` (from the filename prefix).

    Returns:
        Gold-shaped DataFrame in STANDARD_COLUMNS order.
    """
    # Rename-coverage guard (§4.1): the three metric columns must be present
    # post-rename, and district frames must carry SYSTEM_ID. A silent schema
    # change fails loudly here rather than producing NULL gold.
    required = {"EL_EXIT_COUNT", "EL_STUDENT_COUNT", "EL_EXIT_RATE"}
    if detail_level == "district":
        required = required | {"SYSTEM_ID"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Year {year} ({detail_level}): expected bronze columns missing "
            f"after era prep: {sorted(missing)}. Found: {df.columns}"
        )
    # Surface unexpected extras loudly: a new bronze metric column must never
    # be silently ignored. FISCAL_YEAR is consumed upstream; SYSTEM_NAME is a
    # dimension attribute intentionally left out of the fact table (§2).
    known = required | {"FISCAL_YEAR", "SYSTEM_NAME"}
    extras = [c for c in df.columns if c not in known]
    if extras:
        logger.warning(
            "Year %d (%s): unexpected bronze columns ignored: %s",
            year,
            detail_level,
            extras,
        )

    # district_code: zfill(3) pads standard 3-digit codes (601-899) while
    # preserving 7-digit charter / state-school codes unchanged; never
    # truncate. State rows get a typed NULL (the statewide aggregate has no
    # district identity; null_aggregate_geography re-asserts this later).
    if detail_level == "district":
        district_code = pl.col("SYSTEM_ID").cast(pl.Utf8).str.zfill(3)
    else:
        district_code = pl.lit(None).cast(pl.Utf8)

    # Metric casts: TFS suppression is already NULL from read_bronze_file;
    # strict=False is the defensive guard for any unexpected non-numeric.
    # The rate is rescaled 0-100 -> 0-1 per §4 (bounded proportion: bronze
    # range is 0-100, so the scaled value cannot exceed 1).
    return df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        district_code.alias("district_code"),
        # school_code: always NULL — no school-level detail for this metric;
        # kept so every education fact table shares the same key shape.
        pl.lit(None).cast(pl.Utf8).alias("school_code"),
        pl.col("EL_EXIT_COUNT").cast(pl.Int64, strict=False).alias("num_el_exits"),
        pl.col("EL_STUDENT_COUNT")
        .cast(pl.Int64, strict=False)
        .alias("num_el_students"),
        (pl.col("EL_EXIT_RATE").cast(pl.Float64, strict=False) / 100.0).alias(
            "el_exit_rate"
        ),
        pl.lit(detail_level).cast(pl.Utf8).alias("detail_level"),
    ).select(STANDARD_COLUMNS)


def _prepare_for_era(df: pl.DataFrame, era: str) -> pl.DataFrame:
    """Drop era-specific constants and canonicalize metric column names.

    Args:
        df: Raw bronze frame.
        era: Era identifier from detect_era_by_columns.

    Returns:
        Frame with the canonical uppercase metric columns and no constants.
    """
    # #RPT_NAME (district 2023 + state 2023) is a constant report-name
    # string with no analytic signal; State Era 3 additionally carries
    # SYSTEM_ID / SYSTEM_NAME both constant "State of Georgia" — the state
    # role is encoded via detail_level + NULL geography keys instead.
    if era == "district_era_2_rpt_name":
        return df.drop("#RPT_NAME")
    if era == "state_era_3_rpt_name":
        return df.drop("#RPT_NAME", "SYSTEM_ID", "SYSTEM_NAME")
    if era == "state_era_1_state_prefix":
        return df.rename(STATE_PREFIX_RENAMES)
    # district_era_1_no_rpt_name / state_era_2_no_prefix need no prep.
    return df


# =============================================================================
# File orchestration
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read one bronze file, route it, detect its era, and transform it.

    Routing is by filename prefix (``district_`` / ``state_``) because the
    district FY2023 and state FY2023 files carry identical column sets —
    column-only routing would be ambiguous. Era detection within each group
    is by column signature.

    Args:
        path: Bronze file path.
        manifest: Manifest for read-loss / file / bronze-count recording.

    Returns:
        Gold-shaped DataFrame, or None for an empty file.
    """
    # infer_schema_length=0 forces all columns to Utf8 (§4.3b) so every cast
    # is explicit and zero-padded codes survive; read_bronze_file also NULLs
    # the TFS suppression marker via SUPPRESSION_VALUES.
    df, loss = read_bronze_file(path, infer_schema_length=0, return_loss=True)

    # --- Route by filename prefix to the correct era-signature group ------
    if path.name.startswith("district_"):
        detail_level, era_signatures = "district", DISTRICT_ERA_SIGNATURES
    elif path.name.startswith("state_"):
        detail_level, era_signatures = "state", STATE_ERA_SIGNATURES
    else:
        raise ValueError(
            f"{path.name}: filename must start with 'district_' or 'state_' "
            f"(the FY2023 files are column-identical across groups, so the "
            f"prefix is the only reliable routing key)"
        )

    era = detect_era_by_columns(df, era_signatures)
    if era is None:
        raise ValueError(
            f"{path.name}: no {detail_level}-group era signature matched "
            f"columns {df.columns}"
        )

    # Year from the in-file FISCAL_YEAR column (the data is authoritative),
    # cross-checked against the filename year — a mismatch means a
    # mis-shipped file and must raise, not be silently trusted.
    year_values = df["FISCAL_YEAR"].cast(pl.Int32, strict=False).unique().to_list()
    if len(year_values) != 1 or year_values[0] is None:
        raise ValueError(
            f"{path.name}: expected one FISCAL_YEAR value, got {year_values}"
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
        "Processing %s as %s (%s level, year %d, %d rows)",
        path.name,
        era,
        detail_level,
        year,
        df.height,
    )
    return _to_gold(_prepare_for_era(df, era), year, detail_level)


# =============================================================================
# FY2024 unverifiable-rate mask
# =============================================================================


def _null_unverifiable_rates(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """NULL el_exit_rate wherever either underlying count is suppressed.

    In FY2019-2023 the bronze co-suppresses the rate with the counts (all
    three cells read TFS together), so this rule is a no-op there. In FY2024
    GOSA published a numeric EL_EXIT_RATE for every district row, including
    130 rows whose EL_EXIT_COUNT is TFS — the published rates span 0-100
    (65 read 0); 57 of the 130 also suppress EL_STUDENT_COUNT, among them
    SYSTEM_ID 7820612 / Ivy Preparatory Academy with both counts TFS and a
    rate of 100. Those values cannot be
    derived from — or verified against — the suppressed counts, so they are
    treated as suppressed too. Applying the rule uniformly across all years
    pins one consistent invariant: rate present <=> both counts present.

    Args:
        df: Combined post-dedup / post-geography-nulling DataFrame.
        manifest: Manifest to record the masked cells against.

    Returns:
        DataFrame with the unverifiable rates NULLed.
    """
    mask = pl.col("el_exit_rate").is_not_null() & (
        pl.col("num_el_exits").is_null() | pl.col("num_el_students").is_null()
    )
    affected = df.filter(mask)
    if affected.height > 0:
        years = sorted(affected["year"].unique().to_list())
        manifest.record_masked(
            column="el_exit_rate",
            count=affected.height,
            reason=(
                "Numeric bronze EL_EXIT_RATE published alongside TFS-suppressed "
                "counts (FY2024 quirk); unverifiable, treated as suppressed"
            ),
            years=years,
        )
        logger.warning(
            "Masked %d el_exit_rate value(s) with suppressed counts (years %s)",
            affected.height,
            years,
        )
    return df.with_columns(
        pl.when(mask).then(None).otherwise(pl.col("el_exit_rate")).alias("el_exit_rate")
    )


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for english_learner_exit_rate."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file (read-loss accounted per file).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR):
        result = transform_file(path, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize columns/dtypes across eras and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)
    logger.info("Combined %d rows across %d files", combined.height, len(all_dfs))

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean a routing or ID-formatting bug and must raise, not be deduped
    # away silently.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: one bronze file per (file group, fiscal year) with unique
    # SYSTEM_IDs in every district file (verified: zero duplicates), so no
    # duplicate keys are expected; prefer the row with a populated exit
    # count over a hypothetical all-null placeholder as the safety net.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code"],  # no school rows
        district_keys=["year", "district_code"],
        state_keys=["year"],
        sort_col="num_el_exits",
    )

    # 4. Geography nulling via the shared domain rules (state rows already
    # carry NULL keys from _to_gold; the shared helper keeps transform and
    # validator on the single EDUCATION_DOMAIN_CONFIG rule source), then the
    # FY2024 unverifiable-rate mask.
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )
    combined = _null_unverifiable_rates(combined, manifest)

    # Pre-export sanity. The per-year NULL rate of every metric tracks the
    # underlying TFS suppression rate (54-62%% of district exit counts per
    # year), which is roughly uniform — the mask above makes el_exit_rate
    # track it in FY2024 too, so no spike is expected.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(combined, required_non_null=["year", "detail_level"])

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

    Kept out of ``main()`` so the pipeline flow stays readable. The column
    declaration order MUST match STANDARD_COLUMNS minus ``detail_level`` —
    the contract's properties (and the validator's schema check) follow it.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Governor's Office of Student Achievement (GOSA) annual English "
            "Learner (EL) program exit activity. For every Georgia LEA — "
            "standard county/city districts, state and commission charter "
            "schools, State Schools, and state-agency systems — plus a "
            "single statewide aggregate row, reports the number of EL "
            "students who exited EL services, the total EL enrollment used "
            "as the denominator, and the resulting exit rate per fiscal "
            "year. Coverage is fiscal years 2019-2024 (FY2024 = the 2023-24 "
            "school year) at the district and state detail levels; no "
            "school-level detail is published. District cells below the "
            "privacy threshold are suppressed in bronze as TFS and are NULL "
            "in gold; state totals are never suppressed. This topic is the "
            "merged successor to three legacy GOSA source topics "
            "(english_learners_el_exit_rate_district_level, _state_level, "
            "and _3yr_for_report_card) that published the same metric set; "
            "the report-card edition duplicated the district/state values "
            "exactly and was dropped during the merge."
        ),
        title="English Learner Program Exit Rate",
        summary=(
            "Rate at which Georgia English Learner students exit EL "
            "services by district and statewide, fiscal years 2019-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Georgia fiscal year, equal to the ending (spring) "
                    "calendar year of the school year (FY2024 = 2023-24). "
                    "Read from the bronze FISCAL_YEAR column and "
                    "cross-checked against the filename year."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "GOSA district/system code (FK to districts dimension), "
                    "zero-padded to 3 digits; 7-digit charter and "
                    "state-school codes are preserved unchanged. NULL on the "
                    "statewide aggregate rows. Beyond the standard "
                    "county/city districts the series includes 782xxxx/"
                    "783xxxx charter LEAs, the combined State Schools row "
                    "(799, FY2021+; individual State Schools rows 7991893-"
                    "7991895 in FY2019 only — none in FY2020), and the "
                    "Dept. of Corrections (890)."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "null_meaning": (
                    "Always NULL — EL exit activity is published at the "
                    "district and state levels only; the column exists so "
                    "every education fact table shares the same key shape."
                ),
                "description": (
                    "GOSA school code (composite FK to schools dimension "
                    "with district_code). Always NULL in this topic "
                    "(enforced by a quality check) — no school-level detail "
                    "is published for this metric."
                ),
            },
            {
                "name": "num_el_exits",
                "type": "int64",
                "metric_component": "numerator",
                "unit": "count",
                "example": 46,
                "description": (
                    "Number of English Learner students who exited the EL "
                    "program during the fiscal year. NULL when the bronze "
                    "source suppressed the cell as TFS (too few students); "
                    "published values are always 10 or more. State rows are "
                    "never suppressed."
                ),
            },
            {
                "name": "num_el_students",
                "type": "int64",
                "metric_component": "denominator",
                "unit": "count",
                "example": 715,
                "description": (
                    "Total English Learner enrollment for the fiscal year — "
                    "the denominator of el_exit_rate. NULL when suppressed "
                    "as TFS; suppressed only when num_el_exits is also "
                    "suppressed (enforced by a quality check). State rows "
                    "are never suppressed."
                ),
            },
            {
                "name": "el_exit_rate",
                "type": "float64",
                "key_metric": True,
                "unit": "proportion",
                "example": 0.064,
                "short_description": (
                    "Share of English Learner students who exited EL "
                    "services during the year, on a 0-1 scale."
                ),
                "description": (
                    "EL program exit rate on the 0-1 scale (0.064 = 6.4%%; "
                    "bronze publishes 0-100 and is divided by 100 per "
                    "data-cleaning-standards §4). NULL whenever either "
                    "num_el_exits or num_el_students is suppressed: in "
                    "FY2019-2023 the bronze co-suppresses all three cells, "
                    "and in FY2024 GOSA published numeric rates "
                    "even for the 130 district rows with suppressed counts — "
                    "those rates are unverifiable and are NULLed by the "
                    "transform (recorded in the manifest). Where published, "
                    "the rate reconciles with num_el_exits / "
                    "num_el_students within 0.0006 (enforced by a quality "
                    "check)."
                ),
            },
        ],
        source="GOSA",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        limitations=(
            "District and state detail only: school_code is always NULL — no "
            "school-level data is published for this metric. Suppressed "
            "cells are NULL (not zero): district rows below the privacy "
            "threshold are suppressed in bronze as TFS; published counts are "
            "always >= 10. A row may carry num_el_students while "
            "num_el_exits and el_exit_rate are NULL (the exit cohort is "
            "below the threshold even though total EL enrollment is not). "
            "State totals are never suppressed. el_exit_rate is NULL "
            "whenever either count is suppressed — including 130 FY2024 "
            "district rows where GOSA published unverifiable numeric rates "
            "alongside suppressed counts (treated as suppressed). The State "
            "Schools representation changes across years: individual "
            "7-digit rows (7991893-7991895) in FY2019 only, no State "
            "Schools rows at all in FY2020, one combined 799 row from "
            "FY2021 — a long-run State Schools series requires handling "
            "both representations and the FY2020 gap."
        ),
        notes=[
            (
                "Two detail levels: district (one row per LEA per fiscal "
                "year) and state (one statewide aggregate row per fiscal "
                "year). Files are split per year into districts.parquet and "
                "states.parquet; the detail level is encoded in the filename "
                "and is not a column in the parquet output. No "
                "schools.parquet is emitted."
            ),
            (
                "el_exit_rate is on the 0-1 scale (0.064 = 6.4%). Bronze "
                "publishes 0-100 (district files to one decimal, state files "
                "to two); the transform divides by 100 per "
                "data-cleaning-standards §4."
            ),
            (
                "Suppression: district cells below the privacy threshold "
                "carry the literal 'TFS' (Too Few Students) in bronze and "
                "are NULL in gold. Published counts are always >= 10. State "
                "rows are never suppressed (statewide EL enrollment exceeds "
                "100k students)."
            ),
            (
                "FY2024 EL_EXIT_RATE anomaly (district rows only): in "
                "FY2019-2023 the rate is co-suppressed with the counts (all "
                "three cells read TFS together); in FY2024 GOSA published a "
                "numeric rate for every district row, including 130 rows "
                "with a TFS-suppressed exit count — rates spanning 0-100 "
                "(65 read 0; 57 of the 130 also suppress the student "
                "count, among them Ivy Preparatory Academy / 7820612 with "
                "a rate of 100). These are "
                "unverifiable and treated as suppressed — the transform "
                "NULLs el_exit_rate whenever either count is NULL, recorded "
                "in the transform manifest as a masked-value event."
            ),
            (
                "No demographic column: the source publishes no race, "
                "gender, or economic-status breakdowns — every row is the "
                "all-EL-students total."
            ),
            (
                "District 890 (Dept. of Corrections) has a NULL SYSTEM_NAME "
                "in the FY2023 bronze with all metrics suppressed; the row "
                "is emitted with NULL metrics and the districts dimension "
                "resolves the name."
            ),
            (
                "State Schools representation: FY2019 publishes individual "
                "'State Schools-…' rows (7991893-7991895: Atlanta Area "
                "School for the Deaf, Georgia Academy for the Blind, "
                "Georgia School for the Deaf); FY2020 publishes no State "
                "Schools rows at all; from FY2021 a single combined 799 "
                "row appears. Both representations are preserved verbatim "
                "— no cross-era synthesis."
            ),
            (
                "This topic supersedes three legacy GOSA topics "
                "(english_learners_el_exit_rate_district_level, "
                "_state_level, _3yr_for_report_card). A row-by-row diff "
                "showed the report-card edition duplicated the "
                "district/state values exactly for FY2021-2024, so it was "
                "dropped during the bronze merge."
            ),
        ],
        quality_checks=[
            {
                "name": "school_code_always_null",
                "description": (
                    "Structural fact: EL exit activity is published at the "
                    "district and state levels only — school_code (kept for "
                    "the shared education key shape) must be NULL on every "
                    "row."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE school_code IS NOT NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "one_state_row_per_year",
                "description": (
                    "Every fiscal year carries exactly one statewide "
                    "aggregate row (district_code IS NULL). Zero means the "
                    "state file was lost; more than one means a duplicated "
                    "or mis-routed aggregate."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year FROM {object} "
                    "GROUP BY year "
                    "HAVING SUM(CASE WHEN district_code IS NULL THEN 1 "
                    "ELSE 0 END) <> 1) AS bad_years"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_metrics_never_null",
                "description": (
                    "State totals are never suppressed (statewide EL "
                    "enrollment >100k; verified across all six state "
                    "files). A NULL on a state row means a parsing "
                    "regression or a new suppression regime — either must "
                    "be analyzed."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE district_code IS "
                    "NULL AND (num_el_exits IS NULL OR num_el_students IS "
                    "NULL OR el_exit_rate IS NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "exit_count_within_student_count",
                "description": (
                    "Students who exit the EL program are a subset of EL "
                    "enrollment, so the exit count can never exceed the "
                    "student count where both are published (verified: zero "
                    "violations in all six district files)."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE num_el_exits IS "
                    "NOT NULL AND num_el_students IS NOT NULL AND "
                    "num_el_exits > num_el_students"
                ),
                "mustBe": 0,
            },
            {
                "name": "student_count_null_implies_exit_count_null",
                "description": (
                    "Suppression hierarchy: if total EL enrollment is below "
                    "the privacy threshold, the (smaller) exit cohort must "
                    "be too — no row carries an exit count without an "
                    "enrollment count (verified in all six district files)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE num_el_students "
                    "IS NULL AND num_el_exits IS NOT NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "el_exit_rate_requires_counts",
                "description": (
                    "Co-null rule pinning the FY2024 quirk mask: a "
                    "published rate with either underlying count suppressed "
                    "is unverifiable and must be NULL — el_exit_rate is "
                    "non-NULL only where both counts are non-NULL."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE el_exit_rate IS "
                    "NOT NULL AND (num_el_exits IS NULL OR "
                    "num_el_students IS NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "el_exit_rate_present_when_counts_present",
                "description": (
                    "Converse co-null rule: every bronze row that publishes "
                    "both counts also publishes the rate (verified: zero "
                    "exceptions in all 12 files), so a NULL rate alongside "
                    "two non-NULL counts means a cast or mask regression."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE el_exit_rate IS "
                    "NULL AND num_el_exits IS NOT NULL AND "
                    "num_el_students IS NOT NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "el_exit_rate_reconciles_with_counts",
                "description": (
                    "Component reconciliation: where all three values are "
                    "published, the rate must equal num_el_exits / "
                    "num_el_students within 0.0006 on the 0-1 scale. The "
                    "district bronze rounds the rate to one decimal on the "
                    "0-100 scale (max rounding error 0.05 -> 0.0005 after "
                    "/100; state files round to two decimals -> 0.00005); "
                    "0.0006 adds float-epsilon headroom. Verified max "
                    "observed deviation: 0.0005."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE el_exit_rate IS "
                    "NOT NULL AND num_el_exits IS NOT NULL AND "
                    "num_el_students IS NOT NULL AND num_el_students > 0 "
                    "AND ABS(el_exit_rate - (CAST(num_el_exits AS DOUBLE) "
                    "/ num_el_students)) > 0.0006"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
