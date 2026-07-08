"""Transform bronze pathway_graduation_rate files into gold fact tables.

Source: Georgia Insights (GaDOE) — the CCRPI "Pathways" Readiness indicator.
Despite the topic name (which mirrors the GaDOE file label "Pathways
Graduation Rates"), this is NOT a graduation rate: it measures, among each
graduating cohort, the share who completed a coherent three-course sequence
("pathway") in each of four elective areas:

    - Advanced Academic (AP / IB / dual enrollment)
    - World Language (three or more courses in a single world language)
    - Fine Arts (a three-course Fine Arts sequence)
    - CTAE (three sequenced CTAE courses in a single program area)

Bronze: four xlsx files, one per cohort year 2021-2024, each a single data
sheet with the same 9-column schema (dtype drift only — sidestepped by the
shared reader's ``dtype=str`` Excel path). Rows cover state (SYSTEM ID =
"ALL"), district (SCHOOL ID = "ALL"), and school levels; exactly one state
row per file (re-verified). No demographic breakdown and no categorical
columns — the grain is one row per (year, district_code, school_code).

Key decisions (each re-verified against bronze during authoring):

- **Percentage scale.** All four rates ship on the 0-100 scale and are
  standard percentages (NOT on the education domain's score/rating
  exception list) -> divided by 100 to the canonical 0-1 gold scale, with
  ``unit: proportion`` (a cohort share cannot exceed 1; bronze max is 100.0
  in every year).

- **2021 zero-encoded suppression (the §4b-style mask).** The 2021 file
  carries ZERO text suppression markers; 2022-2024 carry NA/TFS (and not a
  single literal 0 cell — re-verified). 2021 instead encodes "no applicable
  students" as 0.0 at the same specialty-school/small-district row
  identities that appear as NA/TFS in 2022-2024 (e.g. 622/0112 KidsPeace:
  2021 = (0,0,0,0), 2024 = (NA,NA,NA,NA)). With no denominator column there
  is no clean signal, so the conservative heuristic from
  bronze-data-structure.md is adopted: rows where ALL FOUR rates are
  exactly 0 in 2021 (47 rows, re-verified) are masked to NULL — a cohort
  completing no pathway in any of the four areas is implausible — while
  partial-zero 2021 rows are preserved as genuine single-pathway zeros.
  Applied via ``_null_2021_zero_suppression`` in ``main()`` after
  geography nulling and before manifest stats/export; recorded via
  ``manifest.record_masked`` per column; guarded by the
  ``no_all_zero_pathway_rows`` contract quality check. Remaining 2021
  zeros are ambiguous ("0%%" vs suppressed) — documented in the contract
  limitations.

- **IDs.** "ALL" sentinels -> NULL BEFORE zfill (so "ALL" is never
  padded); district zfill(3) preserves the 7-digit state-charter codes
  (7820108, 7820120, ...); school zfill(4) aligns the 3-char codes that
  appear in 2021-2023 with the uniformly 4-char 2024 format.

- **Detail level from the ID-null pattern** (state = both NULL, district =
  school NULL, school = both present). The fourth quadrant (district "ALL"
  with a concrete school) is structurally absent in every file
  (re-verified) and raises if it ever appears.

- **Dedup tie-break.** Bronze has zero duplicate (year, district, school)
  keys in any file (re-verified) and each year is exactly one file, so
  dedup is purely defensive. ``sort_col="advanced_academic_pathway_rate"``
  — prefer the row with a published rate over an all-null placeholder if a
  republish ever introduces one.

- **Read loss.** Whole-sheet Excel reads via pandas cannot drop rows, so
  raw == parsed by construction; the loss dict is still recorded so the
  manifest carries the accounting.

- **No demographic column** (§5: every row would be "all") and no
  topic-local categorical maps, so the manifest records no categorical
  mappings — unmapped_count == 0 by construction.

Cross-column invariants authored as contract quality checks (§15b):
``one_state_row_per_year`` (bronze publishes exactly one state row per
file) and ``no_all_zero_pathway_rows`` (the 2021 mask's guard; 2022-2024
bronze contains no zero cells at all). The four rates are INDEPENDENT,
OVERLAPPING per-area completion rates — they do not partition the cohort
and routinely sum above 1.0, so no partition-sums-to-one check applies.
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

TOPIC = "pathway_graduation_rate"
BRONZE_DIR = Path("data/bronze/education/georgiainsights/pathway_graduation_rate")
GOLD_DIR = Path("data/gold/education/pathway_graduation_rate")
SOURCE_URL = "https://georgiainsights.gadoe.org/data-downloads/"

# Aggregate-row sentinel in SYSTEM ID / SCHOOL ID (literal string under the
# shared reader's dtype=str Excel path in every year). Becomes NULL in gold.
AGGREGATE_SENTINEL = "ALL"

# Single era: all four 2021-2024 files share the same 9-column schema
# (re-verified; only cell dtypes drift, which dtype=str reading absorbs).
# Column-signature detection still beats year ranges if GaDOE ever ships a
# mid-series schema change.
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_1_2021_2024": [
        "COHORT YEAR",
        "SYSTEM ID",
        "SCHOOL ID",
        "ADVANCED ACADEMIC",
        "WORLD LANGUAGE",
        "FINE ARTS",
        "CTAE",
    ],
}

# Bronze -> gold renames. SYSTEM NAME / SCHOOL NAME are dimension
# attributes (districts/schools dimensions) and are dropped from the fact.
COLUMN_RENAME_MAP: dict[str, str] = {
    "COHORT YEAR": "year",
    "SYSTEM ID": "district_code",
    "SCHOOL ID": "school_code",
    "ADVANCED ACADEMIC": "advanced_academic_pathway_rate",
    "WORLD LANGUAGE": "world_language_pathway_rate",
    "FINE ARTS": "fine_arts_pathway_rate",
    "CTAE": "ctae_pathway_rate",
}

# Gold column order. `detail_level` is carried for the per-level export
# split and dropped by export_to_parquet() (the filename encodes it).
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "detail_level",
    "advanced_academic_pathway_rate",
    "world_language_pathway_rate",
    "fine_arts_pathway_rate",
    "ctae_pathway_rate",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "detail_level": pl.Utf8,
    "advanced_academic_pathway_rate": pl.Float64,
    "world_language_pathway_rate": pl.Float64,
    "fine_arts_pathway_rate": pl.Float64,
    "ctae_pathway_rate": pl.Float64,
}

METRIC_COLUMNS: list[str] = [
    "advanced_academic_pathway_rate",
    "world_language_pathway_rate",
    "fine_arts_pathway_rate",
    "ctae_pathway_rate",
]

# Natural key for the pre-dedup collision guard. detail_level is included
# so the guard mirrors the per-level dedup keys (geography NULLs already
# encode the level by this point, but the explicit column keeps the guard
# aligned with the contract grain).
NATURAL_KEYS: list[str] = ["year", "district_code", "school_code", "detail_level"]


# =============================================================================
# Era transform
# =============================================================================


def _transform_one_year(df: pl.DataFrame, year: int, era: str) -> pl.DataFrame:
    """Transform one bronze file's frame into gold-shape rows.

    All four files share one logical schema (single era), so this is the
    only transform path. Steps: rename, drop dimension-attribute name
    columns, NULL the "ALL" sentinels, zfill IDs, derive detail_level,
    cast year, cast + rescale the four pathway rates to 0-1.
    """
    # Rename-coverage guard: an unmatched source column silently becomes
    # NULL in gold — the most common data-loss bug — so fail loudly.
    missing = [c for c in COLUMN_RENAME_MAP if c not in df.columns]
    if missing:
        raise ValueError(
            f"Year {year} ({era}): bronze missing expected column(s) "
            f"{missing}. Present: {sorted(df.columns)}"
        )
    df = df.rename(COLUMN_RENAME_MAP)

    # Name columns belong in the districts/schools dimensions, never in
    # the fact table (education CLAUDE.md "Columns NOT Stored in Fact
    # Tables").
    df = df.drop([c for c in ("SYSTEM NAME", "SCHOOL NAME") if c in df.columns])

    # "ALL" sentinels -> NULL BEFORE zfill (zfill would otherwise pad the
    # sentinel string and aggregate rows would leak fake geography keys).
    df = df.with_columns(
        pl.when(pl.col("district_code") == AGGREGATE_SENTINEL)
        .then(None)
        .otherwise(pl.col("district_code"))
        .alias("district_code"),
        pl.when(pl.col("school_code") == AGGREGATE_SENTINEL)
        .then(None)
        .otherwise(pl.col("school_code"))
        .alias("school_code"),
    )

    # The fourth quadrant (district "ALL" with a concrete school) is
    # structurally absent in every bronze file (re-verified) — raise if a
    # future republish ever introduces it, because its detail level would
    # be ambiguous.
    orphan = df.filter(
        pl.col("district_code").is_null() & pl.col("school_code").is_not_null()
    ).height
    if orphan:
        raise ValueError(
            f"Year {year}: {orphan} row(s) with district 'ALL' but a "
            f"concrete school code — unknown detail level"
        )

    # ID formatting per education CLAUDE.md: zfill(3) pads standard
    # 3-digit district codes while passing 7-digit state-charter codes
    # through; zfill(4) aligns the 3-char school codes seen in 2021-2023
    # with 2024's uniformly 4-char format. zfill is a no-op on NULL, so
    # the aggregate rows nulled above stay NULL.
    df = df.with_columns(
        pl.col("district_code").str.zfill(3),
        pl.col("school_code").str.zfill(4),
    )

    # Detail level from the ID-null pattern (state = both NULL, district =
    # school NULL, school = both present) — the only level signal in this
    # source (no Reporting Level column).
    df = df.with_columns(
        pl.when(pl.col("district_code").is_null())
        .then(pl.lit("state"))
        .when(pl.col("school_code").is_null())
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .alias("detail_level")
    )

    # COHORT YEAR arrives as Utf8 under the dtype=str read; all values are
    # 4-digit year strings (verified upstream in transform_file).
    df = df.with_columns(pl.col("year").cast(pl.Int32, strict=False))

    # Pathway rate casts + 0-100 -> 0-1 rescale. NA/TFS already became
    # NULL at read via SUPPRESSION_VALUES; strict=False is
    # belt-and-suspenders for any residue.
    df = df.with_columns(
        [
            (pl.col(c).cast(pl.Float64, strict=False) / 100.0).alias(c)
            for c in METRIC_COLUMNS
        ]
    )

    return df.select(STANDARD_COLUMNS)


# =============================================================================
# File dispatcher
# =============================================================================


def transform_file(
    path: Path, filename_year: int, manifest: TransformManifest
) -> pl.DataFrame | None:
    """Read and transform a single bronze file.

    The data year comes from the in-file COHORT YEAR column (single value
    per file, source of truth per the structure doc), cross-checked
    against the filename year — a mismatch raises rather than silently
    re-stamping a year.
    """
    df, loss = read_bronze_file(path, return_loss=True)
    if df.height == 0:
        logger.warning("%s: bronze file is empty, skipping", path.name)
        return None

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        # Unrecognized schema is a hard failure — silently skipping would
        # quietly drop a year from gold.
        raise ValueError(
            f"{path.name}: could not detect era from columns {df.columns}. "
            f"Update ERA_SIGNATURES if this is a new schema."
        )

    # Year cross-check: exactly one COHORT YEAR value, equal to the
    # filename year (re-verified for all four files).
    year_vals = df["COHORT YEAR"].drop_nulls().unique().to_list()
    if len(year_vals) != 1:
        raise ValueError(
            f"{path.name}: expected exactly one COHORT YEAR value, found {year_vals}"
        )
    year = int(year_vals[0])
    if year != filename_year:
        raise ValueError(
            f"{path.name}: in-file COHORT YEAR {year} != filename year "
            f"{filename_year} — these agree in every known file"
        )

    # Whole-sheet Excel reads cannot drop rows (raw == parsed by
    # construction); recorded so the manifest carries the accounting.
    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])
    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)

    result = _transform_one_year(df, year, era)
    logger.info("Processed %s (year=%d): %d rows", path.name, year, result.height)
    return result


# =============================================================================
# 2021 zero-encoded suppression mask
# =============================================================================


def _null_2021_zero_suppression(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """NULL all four rates on 2021 rows where all four are exactly 0.

    The 2021 file encodes "no applicable students" as 0.0 instead of the
    NA/TFS markers used from 2022 on (re-verified: 2021 has 368 zero cells
    and no text markers; 2022-2024 have NA/TFS and not a single zero
    cell). A row where ALL FOUR pathway rates are 0 is almost certainly
    that encoding — a graduating cohort completing no pathway in any of
    the four areas is implausible — and the same row identities appear as
    NA/NA/NA/NA in later years (e.g. 622/0112 KidsPeace). Partial-zero
    rows are preserved as genuine single-pathway zeros. Scoped to 2021:
    the marker convention makes any later-year zero a real rate.

    Expected mask: 47 rows x 4 columns (re-verified against bronze).
    """
    all_zero = pl.all_horizontal([pl.col(c) == 0.0 for c in METRIC_COLUMNS])
    mask = (pl.col("year") == 2021) & all_zero
    affected = df.filter(mask).height
    if affected:
        for col in METRIC_COLUMNS:
            manifest.record_masked(
                column=col,
                count=affected,
                reason=(
                    "2021 zero-encoded suppression: all four pathway rates "
                    "exactly 0 ('no applicable students' encoding; 2022+ "
                    "uses NA/TFS markers for the same row identities)"
                ),
                years=[2021],
            )
    logger.info(
        "2021 zero-suppression mask: %d row(s) had all four rates == 0 "
        "(expected 47); all four metrics NULLed on those rows",
        affected,
    )
    return df.with_columns(
        [pl.when(mask).then(None).otherwise(pl.col(c)).alias(c) for c in METRIC_COLUMNS]
    )


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for pathway_graduation_rate."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform each bronze file (one xlsx per cohort year).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR, extensions=[".xlsx"]):
        filename_year = extract_year_from_filename(path.name)
        if filename_year is None:
            raise ValueError(f"Cannot parse a year from filename: {path.name!r}")
        result = transform_file(path, filename_year, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize dtypes/order (single era — still enforces consistency)
    # and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs, how="vertical")
    logger.info("Combined %d rows across %d files", combined.height, len(all_dfs))

    # 3. Collision guard BEFORE dedup: duplicate keys carrying divergent
    # rates would mean an alias-collapse/republish bug, not a tie to break.
    # Bronze has zero duplicate keys (re-verified), so this should never
    # fire.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Defensive dedup (one file per year, no cross-file overlap possible).
    # Tie-break: prefer the row with a published advanced_academic rate
    # over an all-null placeholder if a republish ever introduces twins.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code"],
        district_keys=["year", "district_code"],
        state_keys=["year"],
        sort_col="advanced_academic_pathway_rate",
    )

    # 4. Geography nulling via the shared domain rules (the "ALL" -> NULL
    # mapping upstream already did this; running the shared helper keeps
    # transform and validator on one rule source), then the 2021
    # zero-suppression mask at the standard seam (after dedup/nulling,
    # before manifest stats and export).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )
    combined = _null_2021_zero_suppression(combined, manifest)

    # Informational NULL-rate spike check. World Language has the highest
    # suppression rate (~42-44%% NULL in 2022-2024 vs ~7%% in 2021, where
    # only the masked all-zero rows are NULL) — low-side years are not
    # flagged, so no warning is expected.
    spikes = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spikes.status == "warning":
        logger.warning("NULL-rate spikes: %s", spikes.details)

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

    Column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level`` — the contract properties (and the validator's schema
    check) follow it.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Georgia's CCRPI 'Pathways' completion indicator at the state, "
            "district, and school level, 2021-2024. NOTE ON THE TOPIC NAME: "
            "despite `pathway_graduation_rate` (which mirrors the "
            "GaDOE/Georgia Insights file label 'Pathways Graduation "
            "Rates'), this is the CCRPI Readiness 'Pathway Completion' "
            "indicator — NOT a graduation rate. It measures, among each "
            "graduating cohort, the share who completed a coherent "
            "three-course sequence ('pathway') in each of four elective "
            "areas: Advanced Academic (AP/IB/dual enrollment), World "
            "Language, Fine Arts, and CTAE (Career, Technical, and "
            "Agricultural Education). For actual graduation rates see "
            "`graduation_rate_4_year_cohort` and `ccrpi_graduation_rate`. "
            "The four area rates are INDEPENDENT, OVERLAPPING per-area "
            "completion rates — they do NOT partition the cohort and "
            "routinely sum above 1.0 (a student completing two pathways is "
            "counted in both). No demographic breakdown. Source: Georgia "
            "Insights / GaDOE."
        ),
        title="CCRPI Pathway Completion Rates",
        summary=(
            "Share of each graduating cohort completing a course pathway in "
            "four elective areas, by school and district, 2021-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Cohort graduation year (e.g., 2024 = the 2023-2024 "
                    "graduating cohort). Sourced from the in-file COHORT "
                    "YEAR column, which equals the filename year in every "
                    "bronze file."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "625",
                "description": (
                    "GOSA district code (FK to districts dimension). "
                    "Standard 3-digit codes are zero-padded; 7-digit "
                    "state-charter network codes (e.g., '7820120') pass "
                    "through unchanged. NULL on the state-level aggregate "
                    "row."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0411",
                "description": (
                    "4-digit GOSA school code (FK to schools dimension; "
                    "composite key with district_code). Bronze 2021-2023 "
                    "files mix 3- and 4-char school IDs; 3-char codes are "
                    "zero-padded to align with 2024's uniformly 4-char "
                    "format ('195' -> '0195'). NULL on state- and "
                    "district-level aggregate rows."
                ),
            },
            {
                "name": "advanced_academic_pathway_rate",
                "type": "float64",
                "unit": "proportion",
                "example": 0.995,
                "null_meaning": (
                    "Suppressed (bronze 'TFS') or no applicable students "
                    "(bronze 'NA' in 2022-2024; all-four-zero encoding in "
                    "2021, masked at transform time)."
                ),
                "description": (
                    "Share of the graduating cohort who completed an "
                    "Advanced Academic pathway (AP, IB, or dual "
                    "enrollment), 0-1 scale (bronze ships 0-100; divided "
                    "by 100). One of four INDEPENDENT, OVERLAPPING "
                    "per-area completion rates — they do not partition the "
                    "cohort and routinely sum above 1.0."
                ),
            },
            {
                "name": "world_language_pathway_rate",
                "type": "float64",
                "unit": "proportion",
                "example": 0.9926,
                "null_meaning": (
                    "Suppressed (bronze 'TFS') or no applicable students "
                    "(bronze 'NA' in 2022-2024; all-four-zero encoding in "
                    "2021, masked at transform time)."
                ),
                "description": (
                    "Share of the graduating cohort who completed three or "
                    "more courses in a single world language, 0-1 scale. "
                    "One of four independent, overlapping per-area "
                    "completion rates. Has the highest NULL rate of the "
                    "four (~42-44%% in 2022-2024) — World Language is the "
                    "least common pathway at smaller schools."
                ),
            },
            {
                "name": "fine_arts_pathway_rate",
                "type": "float64",
                "unit": "proportion",
                "example": 0.9789,
                "null_meaning": (
                    "Suppressed (bronze 'TFS') or no applicable students "
                    "(bronze 'NA' in 2022-2024; all-four-zero encoding in "
                    "2021, masked at transform time)."
                ),
                "description": (
                    "Share of the graduating cohort who completed a "
                    "three-course Fine Arts sequence (visual arts, music, "
                    "theater, dance), 0-1 scale. One of four independent, "
                    "overlapping per-area completion rates."
                ),
            },
            {
                "name": "ctae_pathway_rate",
                "type": "float64",
                "unit": "proportion",
                "key_metric": True,
                "example": 0.9824,
                "null_meaning": (
                    "Suppressed (bronze 'TFS') or no applicable students "
                    "(bronze 'NA' in 2022-2024; all-four-zero encoding in "
                    "2021, masked at transform time)."
                ),
                "description": (
                    "Share of the graduating cohort who completed a CTAE "
                    "(Career, Technical, and Agricultural Education) "
                    "pathway — three sequenced CTAE courses in a single "
                    "program area — 0-1 scale. One of four independent, "
                    "overlapping per-area completion rates."
                ),
                "short_description": (
                    "Share of the cohort completing a CTAE (career/technical) "
                    "course pathway, on a 0-1 scale."
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
                "Year coverage: 2021-2024. The Pathways indicator is a "
                "relatively new CCRPI component first published for the "
                "2021 cohort; no 2020 file exists (CCRPI scoring was "
                "suspended for the COVID graduation class). The upstream "
                "Georgia Insights catalog lists a 2025 file "
                "(data_sources/education/georgiainsights.md: Years "
                "2021-2025) that has not yet been ingested into bronze."
            ),
            (
                "All four pathway rates are on the 0-1 decimal scale "
                "(bronze ships 0-100; divided by 100). They are standard "
                "percentages, not on the education domain's score/rating "
                "exception list."
            ),
            (
                "Suppression: bronze 'NA' (no applicable students) and "
                "'TFS' (too few students) markers in 2022-2024 map to "
                "NULL. The 2021 file has no text markers and instead "
                "encodes 'no applicable students' as 0.0 — the transform "
                "masks the 47 rows where all four rates are exactly 0 "
                "(recorded in the manifest) and preserves partial-zero "
                "rows as genuine single-pathway zeros."
            ),
        ],
        limitations=(
            "Suppressed cells are NULL (not zero). State rows have NULL "
            "district_code and school_code; district rows have NULL "
            "school_code. The four area rates "
            "(advanced_academic_pathway_rate, world_language_pathway_rate, "
            "fine_arts_pathway_rate, ctae_pathway_rate) are INDEPENDENT, "
            "OVERLAPPING per-area completion rates, NOT a partition of the "
            "cohort: a student who completes more than one pathway is "
            "counted in each, so the four rates routinely sum above 1.0 — "
            "do not sum them or treat them as mutually exclusive shares. "
            "2021 zero-encoding: the 2021 bronze file carries no text "
            "suppression markers (unlike the 'NA'/'TFS' used from 2022 on) "
            "and encodes 'no applicable students' as 0.0. The transform "
            "NULLs the 47 rows where all four rates are exactly 0.0 "
            "(implausible as genuine rates; the same row identities appear "
            "as NA/TFS in later years) and preserves partial-zero 2021 "
            "rows — leaving 180 surviving 2021 zero cells (~18%% of 2021 "
            "rows) ambiguous between a genuine 0%% rate and suppression; "
            "171 of the 180 appear as NA/TFS at the same identities in "
            "2022, so most are likely suppression. "
            "Coverage is 2021-2024; a 2025 source file exists upstream but "
            "is not yet ingested."
        ),
        quality_checks=[
            {
                "name": "one_state_row_per_year",
                "description": (
                    "Every bronze file carries exactly one state aggregate "
                    "row (SYSTEM ID = 'ALL'), so gold must have exactly "
                    "one row with NULL district_code per year (verified "
                    "against all four bronze files)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year FROM {object} "
                    "WHERE district_code IS NULL GROUP BY year "
                    "HAVING COUNT(*) <> 1)"
                ),
                "mustBe": 0,
            },
            {
                "name": "no_all_zero_pathway_rows",
                "description": (
                    "Guard for the 2021 zero-encoded-suppression mask: no "
                    "gold row may carry exactly 0 in all four pathway "
                    "rates. 2021's 47 such bronze rows are the "
                    "'no applicable students' encoding (masked to NULL); "
                    "2022-2024 bronze uses NA/TFS markers and contains no "
                    "zero cells at all (verified)."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE advanced_academic_pathway_rate = 0 "
                    "AND world_language_pathway_rate = 0 "
                    "AND fine_arts_pathway_rate = 0 "
                    "AND ctae_pathway_rate = 0"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
