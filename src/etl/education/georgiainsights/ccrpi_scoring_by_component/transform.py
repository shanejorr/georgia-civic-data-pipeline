"""Transform bronze ccrpi_scoring_by_component files into gold fact tables.

Source: Georgia Insights (GaDOE) — CCRPI Scoring by Component reports the
building blocks of Georgia's College and Career Ready Performance Index
(CCRPI) accountability score at the school, district, and state level,
broken out by Grade Cluster (Elementary / Middle / High). There is NO
demographic subgroup breakdown: the grain is one row per (year, geography,
grade_cluster).

Bronze: 12 single-data-sheet Excel files, one per year, 2012-2019 and
2022-2025 (2020/2021 absent — Georgia paused CCRPI during COVID). The
metric set evolves across four column-signature eras:

    Era 1 (2012-2013) — UPPERCASE headers, no Grade Configuration. CCRPI
        component POINTS on per-component scales (Achievement max ~60,
        Progress max ~22, Achievement Gap max 15, ED/EL/SWD Performance
        max 10, ETB max 2, Challenge max 10) plus the aggregated CCRPI
        Score and Single Score (0-100 with bonus-point overshoot).
    Era 2 (2014-2017) — Title Case headers (casing drifts: `System Id`
        2014-2015 vs `System ID` 2016-2017), adds `Grade Configuration`.
        Same POINTS metric set; the Progress component was redesigned for
        2015 (max jumps ~22 -> 40) and the Achievement Gap cap dropped
        15 -> 10 in 2015 (re-verified; the structure doc's "15 through
        2016" claim is corrected in its Corrections section).
    Era 3 (2018-2019, 2022) — metric set SWITCHES to five component
        SCORES on a 0-100 scale (Content Mastery, Progress, Closing Gaps,
        Readiness, Graduation Rate), keeping the aggregated CCRPI Score +
        Single Score. 2018 embeds newlines in four headers; 2022 ships a
        COVID disclaimer row above the headers and publishes Progress /
        Closing Gaps / CCRPI Score / Single Score as blanket `NA`.
    Era 4 (2023-2025) — same five component scores, DROPS the two
        aggregate columns. 2023's sheet is `CCRPI by Component` (no
        "Scoring").

Era 1-2 POINTS and Era 3-4 SCORES are different measurements on different
scales — NOT comparable. Gold carries them as separate columns, each
populated only in its source era; the era-scoped NULL structure is pinned
by authored quality checks.

Key decisions (each re-verified against bronze during authoring — see
bronze-data-structure.md, incl. its Corrections section):

- **String-typed single-sheet reads.** The shared ``read_bronze_file``
  cannot target a named sheet, so reads go through a local pandas helper
  (precedent: ccrpi_graduation_rate / ccrpi_content_mastery) with
  ``dtype=str`` + ``na_values=SUPPRESSION_VALUES``. String typing
  preserves the literal ``ALL`` / ``RTC`` ID sentinels and zero-padded
  school codes that numeric inference destroys. Re-verified: under
  dtype=str, ``SYSTEM ID`` is NEVER null in any year — state rows carry
  the literal string ``ALL`` in every year (the structure doc's
  "Int64 null" state encodings for 2017/2018/2022-2025 are polars
  type-inference artifacts; corrected in the doc). Whole-sheet Excel
  reads cannot drop rows, so read-loss raw == parsed by construction and
  no read-loss events are recorded.

- **2022 disclaimer row, self-detected.** Sheets are read at header_row=0
  and re-read at header_row=1 when the six required ID/key columns are
  absent — self-verifying for any future disclaimer-topped republish
  (precedent: ccrpi_graduation_rate ``_read_sheet_required``). Only the
  2022 file trips the retry today.

- **Year cross-check.** Every file carries a single-valued `SCHOOL YEAR`
  column; the transform asserts it equals the filename year (verified:
  all 12 files match; some filenames also embed a publication date, e.g.
  the 2014 file republished 03.10.2016, which `extract_year_from_filename`
  correctly ignores by taking the first 4-digit token).

- **Era routing by column signature** via ``detect_era_by_columns`` on
  canonicalized headers (uppercase, newline->space, whitespace collapsed
  — unifies 2013's trailing-space ``SCHOOL ID ``, Era 2 `Id`/`ID` casing
  drift, and 2018's embedded newlines). More-specific signatures first:
  Era 3 before Era 4 (Era 4's signature is a proper subset of Era 3's),
  Era 2 before Era 1 (same reason).

- **Detail level from ID sentinels, name cross-checked.** state =
  ``SYSTEM ID == 'ALL'``; district = ``SCHOOL ID == 'ALL'`` (system is a
  real code, incl. ``RTC``); school = everything else. The name columns
  (`All Systems` / `All Schools` / `All RTC Schools`) are cross-checked
  and any disagreement raises. Sentinels are NULLed before zfill so
  ``ALL`` is never zero-padded.

- **RTC pseudo-district KEPT (deliberate v1-parity break, +9 rows).**
  2015, 2016, and 2017 each ship 3 district-level rows with the literal
  ``SYSTEM ID == 'RTC'`` (`Residential Treatment Center` / `All RTC
  Schools`), aggregating state RTC facilities per grade cluster. ``RTC``
  is an allowlisted pseudo-district code in the districts dimension
  (education CLAUDE.md, district_type `state_special`), and the sibling
  topics ccrpi_content_mastery (2015-2017) and ccrpi_graduation_rate
  (2015-2018) already publish the same entity's rows. The v1 transform
  dropped these 9 rows on the (incorrect) premise that they carried no
  district code and appeared only in 2017 — bronze ships the ``RTC``
  code explicitly in all three years. Keeping them preserves published
  data and cross-topic consistency; the parity delta is exactly these 9
  rows in year=2015/2016/2017 districts.parquet.

- **Dedup is a guarded no-op.** The natural key (SYSTEM ID, SCHOOL ID,
  GRADE CLUSTER) is unique within every bronze file (re-verified: 0
  duplicate keys in all 12 years) and `year` is in the gold key, so
  cross-file collisions are impossible. ``assert_no_natural_key_collisions``
  guards the combined frame, ``deduplicate_by_detail_level`` runs as a
  safety net (tie-break: prefer non-null, then higher, ccrpi_score), and
  main() raises if it ever removes a row — a removal would mean a new
  duplicate source that needs investigation, not silent resolution.

- **Suppression.** `NA` (all eras), `TFS` (2019, 2022-2025), and
  `Too Few Students` (2018) become NULL at read via SUPPRESSION_VALUES;
  the strict=False Float64 cast catches any residual non-numerics.
  Re-verified: 2018 ships `Too Few Students` in Content Mastery (68),
  Readiness (21), AND Graduation Rate (28) — the structure doc's
  "only Readiness" claim is another type-inference artifact, corrected.
  No `100.00+` top-cap sentinel exists anywhere in this bronze
  (re-verified; unlike the ccrpi_content_mastery sibling).

- **Scales.** CCRPI component points and the 0-100 component/aggregate
  scores keep their natural scales (education CLAUDE.md percentage-scale
  exceptions, unit=score). ``graduation_rate`` is a RATE: bronze 0-100 is
  divided by 100 inside each file's transform (chunk-preserving, matching
  v1's per-file division) to the 0-1 proportion scale. Era 3-4 component
  scores are bounded [0, 100] in bronze (re-verified per year), so the
  contract pins value_min/value_max; the aggregates legitimately exceed
  100 in Era 1-2 (bonus points, max 110.3 in 2016) and carry no bounds.

- **No §4b masks and an empty drop/filter ledger.** Every bronze row
  lands in gold (37,279 rows in = 37,279 out) and every observed value is
  inside its metric's domain: points non-negative, Era 3-4 scores within
  [0, 100], graduation rate within [0, 100] bronze / [0, 1] gold, and the
  over-100 Era 1-2 aggregates are by-design bonus overshoot
  (extreme-but-conceivable -> preserved + documented).

- **Bronze-verified invariants authored as quality checks**: era-scoped
  NULL structure (points era vs score era vs Era 4 / COVID-2022
  aggregate blackout), the exact Era 1-2 component reconciliation
  ``achievement + progress + gap + challenge = ccrpi_score`` (0
  violations, max |diff| 0.0 across 2012-2017), the Era 1-2 co-null trio
  (achievement/etb/challenge, 0 row mismatches), and the structural
  "graduation_rate only on high-cluster rows" fact (verified in all six
  Era 3-4 years).

Natural key: (year, district_code, school_code, detail_level,
grade_cluster). `grade_configuration` (a school attribute) and the name
columns are dimension concerns and are not carried to gold.
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

TOPIC = "ccrpi_scoring_by_component"
BRONZE_DIR = Path("data/bronze/education/georgiainsights/ccrpi_scoring_by_component")
GOLD_DIR = Path("data/gold/education/ccrpi_scoring_by_component")
SOURCE_URL = "https://georgiainsights.gadoe.org/data-downloads/"

# Per-year data sheet. 2012-2013 also ship empty Sheet2/Sheet3 placeholders
# (reading them errors), 2017 uses a custom name, 2023 omits "Scoring", and
# 2022 adds a FAQs metadata sheet — hence an explicit map instead of
# first-sheet heuristics.
SHEET_NAME_BY_YEAR: dict[int, str] = {
    2012: "Sheet1",
    2013: "Sheet1",
    2014: "Sheet 1",
    2015: "Sheet 1",
    2016: "Sheet 1",
    2017: "2017_CCRPI Scoring by Component",
    2018: "CCRPI Scoring by Component",
    2019: "CCRPI Scoring by Component",
    2022: "CCRPI Scoring by Component",
    2023: "CCRPI by Component",  # Era 4 oddity: omits "Scoring".
    2024: "CCRPI Scoring by Component",
    2025: "CCRPI Scoring by Component",
}

# Canonical key columns present in every era — used both as the rename-
# coverage guard and to auto-detect a disclaimer row above the headers
# (2022): when these are absent at header_row=0, re-read at header_row=1.
REQUIRED_CANONICAL_COLUMNS: list[str] = [
    "SCHOOL YEAR",
    "SYSTEM ID",
    "SYSTEM NAME",
    "SCHOOL ID",
    "SCHOOL NAME",
    "GRADE CLUSTER",
]

# Aggregate-row sentinel in the ID columns (literal string under dtype=str
# in every year — re-verified; never an actual null). Becomes NULL in gold.
AGGREGATE_SENTINEL = "ALL"

# Allowlisted pseudo-district code (districts dimension, education
# CLAUDE.md): Residential Treatment Center aggregate, bronze 2015-2017.
RTC_DISTRICT_CODE = "RTC"

# Era signatures on canonical (uppercased, newline-stripped, whitespace-
# collapsed) headers. detect_era_by_columns returns the FIRST signature
# fully present, so more-specific signatures come first: Era 4's columns
# are a proper subset of Era 3's, and Era 1's of Era 2's.
ERA_SIGNATURES: dict[str, list[str]] = {
    # 2018-2019, 2022: score-era metrics + aggregated CCRPI/Single Score.
    "era_3_scores_with_aggregates": [
        "GRADE CONFIGURATION",
        "CONTENT MASTERY",
        "PROGRESS",
        "CLOSING GAPS",
        "READINESS",
        "GRADUATION RATE",
        "CCRPI SCORE",
        "SINGLE SCORE",
    ],
    # 2023-2025: score-era metrics only (aggregates dropped at source).
    "era_4_scores_no_aggregates": [
        "GRADE CONFIGURATION",
        "CONTENT MASTERY",
        "PROGRESS",
        "CLOSING GAPS",
        "READINESS",
        "GRADUATION RATE",
    ],
    # 2014-2017: points-era metrics + Grade Configuration.
    "era_2_points_with_config": [
        "GRADE CONFIGURATION",
        "ACHIEVEMENT POINTS",
        "PROGRESS POINTS",
        "ACHIEVEMENT GAP POINTS",
        "ED/EL/SWD PERFORMANCE",
        "ETB POINTS",
        "CHALLENGE POINTS",
        "CCRPI SCORE",
        "SINGLE SCORE",
    ],
    # 2012-2013: points-era metrics, no Grade Configuration.
    "era_1_points_no_config": [
        "ACHIEVEMENT POINTS",
        "PROGRESS POINTS",
        "ACHIEVEMENT GAP POINTS",
        "ED/EL/SWD PERFORMANCE",
        "ETB POINTS",
        "CHALLENGE POINTS",
        "CCRPI SCORE",
        "SINGLE SCORE",
    ],
}

# E/M/H -> descriptive snake_case (§10). Every era uses the single letters.
GRADE_CLUSTER_MAP: dict[str, str] = {
    "E": "elementary",
    "M": "middle",
    "H": "high",
}

# Canonical bronze header -> gold column, per metric family. Which families
# a file ships is exactly what the era signature detected; absent-family
# columns are NULL-filled by harmonize_columns (structural absence, not a
# rename bug).
POINTS_METRIC_RENAMES: dict[str, str] = {
    "ACHIEVEMENT POINTS": "achievement_points",
    "PROGRESS POINTS": "progress_points",
    "ACHIEVEMENT GAP POINTS": "achievement_gap_points",
    "ED/EL/SWD PERFORMANCE": "ed_el_swd_performance",
    "ETB POINTS": "etb_points",
    "CHALLENGE POINTS": "challenge_points",
}
SCORE_METRIC_RENAMES: dict[str, str] = {
    "CONTENT MASTERY": "content_mastery",
    "PROGRESS": "progress",
    "CLOSING GAPS": "closing_gaps",
    "READINESS": "readiness",
    "GRADUATION RATE": "graduation_rate",
}
AGGREGATE_METRIC_RENAMES: dict[str, str] = {
    "CCRPI SCORE": "ccrpi_score",
    "SINGLE SCORE": "ccrpi_single_score",
}

# Which metric families each era ships (drives renames + rename coverage).
ERA_METRIC_FAMILIES: dict[str, list[dict[str, str]]] = {
    "era_1_points_no_config": [POINTS_METRIC_RENAMES, AGGREGATE_METRIC_RENAMES],
    "era_2_points_with_config": [POINTS_METRIC_RENAMES, AGGREGATE_METRIC_RENAMES],
    "era_3_scores_with_aggregates": [SCORE_METRIC_RENAMES, AGGREGATE_METRIC_RENAMES],
    "era_4_scores_no_aggregates": [SCORE_METRIC_RENAMES],
}

# Gold fact column order. `detail_level` is carried through geography
# nulling / export splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "detail_level",
    "grade_cluster",
    # Points-era metrics (Era 1-2, 2012-2017).
    "achievement_points",
    "progress_points",
    "achievement_gap_points",
    "ed_el_swd_performance",
    "etb_points",
    "challenge_points",
    # Score-era metrics (Era 3-4, 2018+).
    "content_mastery",
    "progress",
    "closing_gaps",
    "readiness",
    "graduation_rate",
    # Aggregated scores (Era 1-3; dropped at source from 2023, all-NA 2022).
    "ccrpi_score",
    "ccrpi_single_score",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "detail_level": pl.Utf8,
    "grade_cluster": pl.Utf8,
    "achievement_points": pl.Float64,
    "progress_points": pl.Float64,
    "achievement_gap_points": pl.Float64,
    "ed_el_swd_performance": pl.Float64,
    "etb_points": pl.Float64,
    "challenge_points": pl.Float64,
    "content_mastery": pl.Float64,
    "progress": pl.Float64,
    "closing_gaps": pl.Float64,
    "readiness": pl.Float64,
    "graduation_rate": pl.Float64,
    "ccrpi_score": pl.Float64,
    "ccrpi_single_score": pl.Float64,
}

METRIC_COLUMNS: list[str] = [
    "achievement_points",
    "progress_points",
    "achievement_gap_points",
    "ed_el_swd_performance",
    "etb_points",
    "challenge_points",
    "content_mastery",
    "progress",
    "closing_gaps",
    "readiness",
    "graduation_rate",
    "ccrpi_score",
    "ccrpi_single_score",
]

NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "detail_level",
    "grade_cluster",
]


# =============================================================================
# Bronze reading (string-typed pandas, named sheet, disclaimer-aware)
# =============================================================================


def _canonicalize_column_name(name: str) -> str:
    """Return the canonical UPPERCASE key for a bronze header.

    Collapses every observed header drift into one keyspace: case (`System
    Id` / `System ID` / `SYSTEM ID`), 2018's embedded newlines (`Content
    \\nMastery`, `Closing\\nGaps`, `CCRPI\\nScore`, `Single \\nScore`), and
    2013's trailing space on `SCHOOL ID `.
    """
    cleaned = str(name).replace("\n", " ").replace("\r", " ")
    return " ".join(cleaned.split()).upper()


def _read_data_sheet(path: Path, year: int) -> pl.DataFrame:
    """Read the year's data sheet as an all-Utf8 frame, headers canonical.

    ``dtype=str`` preserves the literal `ALL` / `RTC` ID sentinels and
    zero-padded school codes that numeric inference destroys;
    ``na_values=SUPPRESSION_VALUES`` turns `NA` / `TFS` / `Too Few
    Students` into NULL at read. The 2022 file ships a COVID disclaimer in
    row 0: rather than hardcode its header offset, read at header_row=0 and
    retry at header_row=1 when the required key columns are absent —
    self-verifying for any future disclaimer-topped republish.
    """
    sheet = SHEET_NAME_BY_YEAR.get(year)
    if sheet is None:
        raise ValueError(
            f"{path.name}: no data sheet mapped for year {year}. Add it to "
            "SHEET_NAME_BY_YEAR after running /bronze-data-structure."
        )

    def _read(header_row: int) -> pl.DataFrame:
        pdf = pd.read_excel(
            path,
            sheet_name=sheet,
            dtype=str,
            na_values=list(SUPPRESSION_VALUES),
            header=header_row,
        )
        pdf.columns = [_canonicalize_column_name(c) for c in pdf.columns]
        return pl.from_pandas(pdf)

    df = _read(header_row=0)
    if all(c in df.columns for c in REQUIRED_CANONICAL_COLUMNS):
        return df
    logger.info(
        "  %s :: %r: key columns absent at header_row=0 — retrying at "
        "header_row=1 (disclaimer row)",
        path.name,
        sheet,
    )
    df = _read(header_row=1)
    missing = [c for c in REQUIRED_CANONICAL_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"{path.name} sheet {sheet!r}: required column(s) {missing} not "
            f"found at header_row 0 or 1. Present: {sorted(df.columns)}"
        )
    return df


# =============================================================================
# Shared transform helpers
# =============================================================================


def _require_columns(df: pl.DataFrame, required: list[str], label: str) -> None:
    """Raise if any expected bronze column is absent (rename-coverage guard).

    An unmatched source column silently becomes NULL in gold — the most
    common data-loss bug — so a missing column fails loudly instead.
    """
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"{label}: expected bronze column(s) missing: {missing}. "
            f"Present: {sorted(df.columns)}"
        )


def _assert_in_file_year(df: pl.DataFrame, year: int, path: Path) -> None:
    """Cross-check the in-file SCHOOL YEAR against the filename year.

    Every bronze file carries exactly one SCHOOL YEAR value and it matches
    the filename year in all 12 files (re-verified) — some filenames also
    embed a later publication date (e.g. the 2014 file republished
    03.10.2016), which must never win. Raises on any disagreement.
    """
    seen = (
        df["SCHOOL YEAR"].cast(pl.Utf8).str.strip_chars().drop_nulls().unique()
    ).to_list()
    if seen != [str(year)]:
        raise ValueError(
            f"{path.name}: in-file SCHOOL YEAR {seen} != filename year {year}."
        )


def _derive_detail_level(df: pl.DataFrame, path: Path) -> pl.DataFrame:
    """Derive detail_level from ID sentinels, cross-checked against names.

    Primary signal (uniform across all 12 years under dtype=str reads):
        state    -> SYSTEM ID == 'ALL'   (SCHOOL ID is also 'ALL')
        district -> SCHOOL ID == 'ALL'   (SYSTEM ID is a real code, incl.
                                          the RTC pseudo-district 2015-2017)
        school   -> everything else
    Cross-check signal: SYSTEM NAME == 'All Systems' must coincide exactly
    with the state rows, and SCHOOL NAME in ('All Schools', 'All RTC
    Schools') with the state+district rows. Any disagreement raises — the
    two encodings have never diverged in bronze, so a mismatch means a new
    source quirk that needs human review.
    """
    df = df.with_columns(
        pl.when(pl.col("district_code") == AGGREGATE_SENTINEL)
        .then(pl.lit("state"))
        .when(pl.col("school_code") == AGGREGATE_SENTINEL)
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .alias("detail_level"),
    )

    name_state = pl.col("system_name") == "All Systems"
    name_aggregate = pl.col("school_name").is_in(["All Schools", "All RTC Schools"])
    disagree = df.filter(
        (name_state != (pl.col("detail_level") == "state"))
        | (name_aggregate != (pl.col("detail_level") != "school"))
    )
    if disagree.height > 0:
        sample = disagree.select(
            ["district_code", "school_code", "system_name", "school_name"]
        ).head(10)
        raise ValueError(
            f"{path.name}: ID-sentinel vs name-column detail-level "
            f"disagreement on {disagree.height} row(s). Sample:\n{sample}"
        )
    return df


def _null_id_sentinels_and_format(df: pl.DataFrame) -> pl.DataFrame:
    """NULL the `ALL` ID sentinels, then zero-pad the real codes.

    `ALL` must become NULL BEFORE zfill so the sentinel is never padded
    into a fake code. zfill(3) pads 3-digit district codes while passing
    7-digit charter / state-school operator codes and the 3-char `RTC`
    pseudo-district unchanged (never truncate); zfill(4) repairs the
    un-padded school codes some years ship (e.g. `100` -> `0100` in 2017
    and 2024).
    """
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
    return df.with_columns(
        pl.col("district_code").cast(pl.Utf8).str.zfill(3),
        pl.col("school_code").cast(pl.Utf8).str.zfill(4),
    )


def _map_grade_cluster(df: pl.DataFrame, manifest: TransformManifest) -> pl.DataFrame:
    """Map bronze E/M/H to elementary/middle/high and record the mapping.

    `default=None` surfaces any unmapped bronze value to the manifest,
    whose write() raises on unmapped_count > 0.
    """
    raw_expr = pl.col("grade_cluster_raw").cast(pl.Utf8).str.strip_chars()
    bronze_series = df.with_columns(raw_expr.alias("_norm"))["_norm"]
    df = df.with_columns(
        raw_expr.replace_strict(GRADE_CLUSTER_MAP, default=None).alias("grade_cluster")
    )
    manifest.record_categorical(
        column="grade_cluster",
        map_dict=GRADE_CLUSTER_MAP,
        bronze_series=bronze_series,
        gold_series=df["grade_cluster"],
    )
    return df.drop("grade_cluster_raw")


# =============================================================================
# Per-file transform
# =============================================================================


def transform_file(
    path: Path, year: int, manifest: TransformManifest
) -> pl.DataFrame | None:
    """Read one bronze file, detect its era, and transform it to gold shape.

    All four eras share one pipeline; the era only determines which metric
    families are renamed + cast (the signature that routed the file is the
    same column set the renames consume, so coverage is verified twice).
    """
    df = _read_data_sheet(path, year)
    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(
            f"{path.name} (year={year}): could not detect era from columns "
            f"{sorted(df.columns)}. Update ERA_SIGNATURES if this is a new "
            "schema."
        )
    logger.info(
        "%s: era=%s, bronze_rows=%s, bronze_cols=%d",
        path.name,
        era,
        f"{df.height:,}",
        len(df.columns),
    )
    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)
    if df.height == 0:
        logger.warning("Year %d: bronze file is empty, skipping", year)
        return None

    _assert_in_file_year(df, year, path)

    # Keys + names. Grade Configuration (Era 2-4) is a school attribute
    # (grade-offering list) that belongs to the schools dimension, not this
    # fact table — it is simply never selected.
    key_renames = {
        "SYSTEM ID": "district_code",
        "SYSTEM NAME": "system_name",
        "SCHOOL ID": "school_code",
        "SCHOOL NAME": "school_name",
        "GRADE CLUSTER": "grade_cluster_raw",
    }
    metric_renames: dict[str, str] = {}
    for family in ERA_METRIC_FAMILIES[era]:
        metric_renames.update(family)
    _require_columns(
        df, REQUIRED_CANONICAL_COLUMNS + sorted(metric_renames), f"{path.name} ({era})"
    )
    df = df.rename({**key_renames, **metric_renames})

    # Detail level BEFORE sentinel-nulling (the sentinels are the signal).
    df = _derive_detail_level(df, path)
    df = _null_id_sentinels_and_format(df)

    df = df.with_columns(pl.lit(year).cast(pl.Int32).alias("year"))
    df = _map_grade_cluster(df, manifest)

    # Metric casts: strict=False turns any residual non-numeric string into
    # NULL (the reader already nulled NA/TFS/Too Few Students). The 2022
    # blanket-NA columns (Progress / Closing Gaps / CCRPI Score / Single
    # Score) become all-NULL here.
    df = df.with_columns(
        [pl.col(c).cast(pl.Float64, strict=False) for c in metric_renames.values()]
    )

    # graduation_rate is a RATE, not a CCRPI score: bronze ships 0-100,
    # gold uses the 0-1 proportion scale (§4). Divided per file, inside the
    # single-chunk frame, to keep float kernels chunk-stable.
    if "graduation_rate" in df.columns:
        df = df.with_columns((pl.col("graduation_rate") / 100.0))

    present = [c for c in STANDARD_COLUMNS if c in df.columns]
    return df.select(present)


# =============================================================================
# Pipeline orchestration
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for ccrpi_scoring_by_component."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file. Whole-sheet Excel reads cannot
    # drop rows (read-loss raw == parsed by construction), so no read-loss
    # events exist to record.
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR, extensions=[".xls", ".xlsx"]):
        year = extract_year_from_filename(path.name)
        if year is None:
            raise ValueError(f"Cannot determine data year for: {path.name}")
        result = transform_file(path, year, manifest)
        if result is not None:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize + concat across eras: era-absent metric families
    # (points columns for 2018+, score columns for 2012-2017, aggregates
    # for 2023+) are NULL-filled as Float64 per TARGET_TYPES — structural
    # bronze absence, pinned by the era-scoped quality checks.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)
    logger.info(
        "Combined %s rows across %d files", f"{combined.height:,}", len(all_dfs)
    )

    # 3. Collision guard BEFORE dedup, so divergent twins raise instead of
    # being silently resolved. Dedup is a defensive no-op today: the
    # natural key is unique in all 12 bronze files (re-verified, 0
    # duplicate keys) and `year` separates files. Tie-break, should a
    # future republish ship identical twins: prefer the row with a
    # non-null (then higher) ccrpi_score — actual data over placeholders.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    pre_dedup_height = combined.height
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code", "grade_cluster"],
        district_keys=["year", "district_code", "grade_cluster"],
        state_keys=["year", "grade_cluster"],
        sort_col="ccrpi_score",
    )
    if combined.height != pre_dedup_height:
        raise ValueError(
            f"Dedup removed {pre_dedup_height - combined.height} row(s) but "
            "bronze is key-unique — investigate the new duplicate source."
        )

    # 4. Geography nulling (shared domain rules — transform and validator
    # read the same dict). No §4b masks: every observed value is within its
    # metric's domain (module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Expected NULL-rate spikes (documented bronze structure, not bugs):
    # points metrics 100% NULL 2018+; score metrics 100% NULL 2012-2017;
    # aggregates 100% NULL 2022+ (COVID blackout, then dropped at source);
    # progress/closing_gaps 100% NULL 2022; graduation_rate NULL on every
    # non-high cluster row.
    spikes = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spikes.status == "warning":
        logger.warning("NULL-rate spikes (expected era structure): %s", spikes.details)
    validate_output(
        combined, required_non_null=["year", "detail_level", "grade_cluster"]
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

    Column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level`` — the contract properties (and the validator's schema
    check) follow it.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Components of Georgia's College and Career Ready Performance "
            "Index (CCRPI) accountability score at the school, district, "
            "and state level by grade cluster (elementary / middle / "
            "high), 2012-2025 (no 2020-2021 — COVID pause). The metric "
            "set evolves across four source eras: 2012-2017 publish CCRPI "
            "component POINTS on per-component scales (achievement, "
            "progress, achievement gap, ED/EL/SWD performance, ETB and "
            "challenge bonus points); 2018+ publish five component SCORES "
            "on a 0-100 scale (content mastery, progress, closing gaps, "
            "readiness, graduation rate). The aggregated ccrpi_score and "
            "ccrpi_single_score accompany 2012-2019 (suppressed for 2022, "
            "dropped at source from 2023). Points-era and score-era "
            "metrics are different measurements on different scales — "
            "each column is populated only in its source era and the two "
            "families are NOT comparable. No demographic breakdown. "
            "This is the CCRPI OVERVIEW / SCORECARD topic — the most "
            "important CCRPI entry point and the only single-query view of a "
            "school's accountability picture: the SOLE source of the overall "
            "ccrpi_single_score and the per-cluster ccrpi_score, the only "
            "topic presenting all five component scores side by side, and "
            "the only home of the 2012-2017 points-era breakdown. It differs "
            "from the per-component topics (ccrpi_content_mastery, "
            "ccrpi_progress, ccrpi_readiness, ccrpi_graduation_rate) by being "
            "WIDE and SHALLOW — one rolled-up score per component at the "
            "all-student / grade-cluster grain, with no demographic, subject, "
            "indicator, or sub-indicator axis. Those topics are the "
            "complementary NARROW and DEEP view, each drilling a single "
            "component down by demographic and sub-measure but publishing "
            "neither the overall score nor the cross-component scorecard. Use "
            "this topic for the headline score and the component scorecard; "
            "use a component topic for within-component detail."
        ),
        title="CCRPI Scores and Components",
        summary=(
            "Georgia's overall CCRPI accountability score plus its component "
            "scores, by school, district, and state and grade cluster, "
            "2012-2025."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Ending calendar year of the school year (e.g., 2024 = "
                    "2023-2024). 2020 and 2021 are absent: Georgia paused "
                    "CCRPI calculation during the COVID pandemic. Verified "
                    "against each file's in-file School Year column."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "3-digit GOSA district code (zero-padded) for standard "
                    "districts; 7-digit code for state-charter / "
                    "state-school operators; the allowlisted "
                    "pseudo-district code `RTC` (Residential Treatment "
                    "Center aggregate, 2015-2017 only, district-level "
                    "rows). NULL for state-level rows. FK to the districts "
                    "dimension."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0103",
                "description": (
                    "4-digit GOSA school code (zero-padded; 2017 and 2024 "
                    "bronze ship un-padded values that zfill repairs). NULL "
                    "for district- and state-level rows. FK to the schools "
                    "dimension (composite key with district_code)."
                ),
            },
            {
                "name": "grade_cluster",
                "type": "string",
                "nullable": False,
                "example": "elementary",
                "validValues": sorted(set(GRADE_CLUSTER_MAP.values())),
                "short_description": (
                    "Grade band the row covers: elementary, middle, or high "
                    "(a K-12 school appears in up to three rows per year)."
                ),
                "description": (
                    "CCRPI grade cluster: `elementary`, `middle`, or "
                    "`high` (bronze single letters E/M/H recoded). Every "
                    "entity is reported once per cluster it serves; a K-12 "
                    "school appears in up to three rows per year."
                ),
            },
            {
                "name": "achievement_points",
                "type": "float64",
                "unit": "score",
                "example": 45.3,
                "null_meaning": (
                    "Suppressed at source (`NA`), or a score-era row "
                    "(2018+) where this points metric no longer exists."
                ),
                "description": (
                    "CCRPI Achievement points (points era 2012-2017 only; "
                    "observed range 2.6-59.9, max ~60 by design). NULL for "
                    "all 2018+ rows. Co-null with etb_points and "
                    "challenge_points on every points-era row (enforced as "
                    "a quality check)."
                ),
            },
            {
                "name": "progress_points",
                "type": "float64",
                "unit": "score",
                "example": 17.3,
                "null_meaning": (
                    "Suppressed at source (`NA`) or true-null (entities "
                    "without measurable progress, e.g. new schools), or a "
                    "score-era row (2018+)."
                ),
                "description": (
                    "CCRPI Progress points (points era 2012-2017 only). "
                    "CAVEAT: the Progress component was redesigned for "
                    "2015 — max ~22 in 2012-2014 vs max 40 in 2015-2017 — "
                    "under the same bronze column; values are preserved "
                    "verbatim, so period-over-period comparisons must stay "
                    "within one sub-era. NULL for all 2018+ rows."
                ),
            },
            {
                "name": "achievement_gap_points",
                "type": "float64",
                "unit": "score",
                "example": 11.3,
                "null_meaning": (
                    "Suppressed at source (`NA`) or true-null, or a "
                    "score-era row (2018+)."
                ),
                "description": (
                    "CCRPI Achievement Gap points (points era 2012-2017 "
                    "only). Cap changed mid-era: max 15 in 2012-2014, max "
                    "10 in 2015-2017 (verified per year in bronze). NULL "
                    "for all 2018+ rows."
                ),
            },
            {
                "name": "ed_el_swd_performance",
                "type": "float64",
                "unit": "score",
                "example": 3.5,
                "null_meaning": (
                    "Suppressed at source (`NA`) or true-null (2013 ships "
                    "82 blank cells), or a score-era row (2018+)."
                ),
                "description": (
                    "Economically Disadvantaged / English Learner / "
                    "Students With Disabilities subgroup performance "
                    "points (points era 2012-2017 only; range 0-10). The "
                    "points-era predecessor of the score-era closing_gaps "
                    "subgroup component — measured on a different scale "
                    "and NOT comparable to it. NULL for all 2018+ rows."
                ),
            },
            {
                "name": "etb_points",
                "type": "float64",
                "unit": "score",
                "example": 1.0,
                "null_meaning": (
                    "Suppressed at source (`NA`), or a score-era row (2018+)."
                ),
                "description": (
                    "Exceeding the Bar bonus points (points era 2012-2017 "
                    "only). Cap drifts by framework: max 2.0 in 2012-2013, "
                    "3.0 in 2014, 2.5 in 2015-2017. NULL for all 2018+ "
                    "rows."
                ),
            },
            {
                "name": "challenge_points",
                "type": "float64",
                "unit": "score",
                "example": 3.5,
                "null_meaning": (
                    "Suppressed at source (`NA`), or a score-era row (2018+)."
                ),
                "description": (
                    "Challenge bonus points (points era 2012-2017 only; "
                    "range 0-10): the bonus bucket added on top of the "
                    "three base components, predominantly ED/EL/SWD "
                    "performance + ETB points. Participates in the exact "
                    "identity achievement_points + progress_points + "
                    "achievement_gap_points + challenge_points = "
                    "ccrpi_score (0 violations source-wide; enforced as a "
                    "quality check). NULL for all 2018+ rows."
                ),
            },
            {
                "name": "content_mastery",
                "type": "float64",
                "unit": "score",
                "value_min": 0,
                "value_max": 100,
                "example": 68.4,
                "null_meaning": (
                    "Suppressed at source (`NA`, `TFS`, `Too Few "
                    "Students`), or a points-era row (2012-2017)."
                ),
                "description": (
                    "CCRPI Content Mastery component score, 0-100 scale "
                    "(score columns are exempt from the 0-1 percentage "
                    "convention; components are capped at 100 by GaDOE "
                    "rules — verified [0, 100] in every year). Score era "
                    "(2018+) only; NULL for all 2012-2017 rows."
                ),
            },
            {
                "name": "progress",
                "type": "float64",
                "unit": "score",
                "value_min": 0,
                "value_max": 100,
                "example": 72.5,
                "null_meaning": (
                    "Suppressed at source (`NA`, `TFS`), the 2022 "
                    "component-wide COVID suspension, or a points-era row "
                    "(2012-2017)."
                ),
                "description": (
                    "CCRPI Progress component score, 0-100 scale. Score "
                    "era (2018+) only; NULL for all 2012-2017 rows and "
                    "100%% NULL in 2022 (federally-approved one-year COVID "
                    "modification suspended the component; bronze ships "
                    "blanket `NA`)."
                ),
            },
            {
                "name": "closing_gaps",
                "type": "float64",
                "unit": "score",
                "value_min": 0,
                "value_max": 100,
                "example": 54.1,
                "null_meaning": (
                    "Suppressed at source (literal `NA` markers — "
                    "196/228/207 cells in 2023/2024/2025, zero blank "
                    "cells), the 2022 component-wide COVID suspension, "
                    "or a points-era row (2012-2017)."
                ),
                "description": (
                    "CCRPI Closing Gaps component score, 0-100 scale — the "
                    "score-era successor of the points-era "
                    "ed_el_swd_performance subgroup metric (different "
                    "scale, not comparable). Score era (2018+) only; NULL "
                    "for all 2012-2017 rows and 100%% NULL in 2022 (COVID "
                    "modification)."
                ),
            },
            {
                "name": "readiness",
                "type": "float64",
                "unit": "score",
                "value_min": 0,
                "value_max": 100,
                "example": 77.0,
                "null_meaning": (
                    "Suppressed at source (`NA`, `TFS`, `Too Few "
                    "Students`), or a points-era row (2012-2017)."
                ),
                "description": (
                    "CCRPI Readiness component score, 0-100 scale. Score "
                    "era (2018+) only; NULL for all 2012-2017 rows. The "
                    "only score component published for every cluster in "
                    "2022."
                ),
            },
            {
                "name": "graduation_rate",
                "type": "float64",
                "unit": "proportion",
                "example": 0.813,
                "null_meaning": (
                    "Not a high-cluster row (elementary / middle have no "
                    "graduation rate), suppressed at source (`NA`, `TFS`, "
                    "`Too Few Students`), or a points-era row (2012-2017)."
                ),
                "description": (
                    "CCRPI Graduation Rate component on the 0-1 decimal "
                    "scale (bronze ships 0-100; divided by 100 per the "
                    "rate-column standard — the only rescaled column in "
                    "this topic). Score era (2018+) only, and non-NULL "
                    "exclusively on `high` grade-cluster rows in every "
                    "year (verified; enforced as a quality check)."
                ),
            },
            {
                "name": "ccrpi_score",
                "type": "float64",
                "unit": "score",
                "example": 74.2,
                "null_meaning": (
                    "Suppressed at source (`NA`), the 2022 COVID "
                    "suppression, or a 2023+ row where the source dropped "
                    "the column."
                ),
                "description": (
                    "Aggregated per-cluster CCRPI score on a 0-100 scale. "
                    "Legitimately exceeds 100 in the points era via ETB / "
                    "Challenge bonus points (observed max 110.3 in 2016; "
                    "by design, not capped — hence no contract bounds). In "
                    "the points era it equals achievement_points + "
                    "progress_points + achievement_gap_points + "
                    "challenge_points exactly (quality-checked). Published "
                    "2012-2019; 100%% NULL for 2022 (COVID modification) "
                    "and 2023+ (column dropped at source)."
                ),
            },
            {
                "name": "ccrpi_single_score",
                "type": "float64",
                "unit": "score",
                "key_metric": True,
                "example": 74.2,
                "short_description": (
                    "The entity's overall CCRPI accountability score on a "
                    "0-100 scale; published 2012-2019, NULL from 2022 on."
                ),
                "null_meaning": (
                    "Suppressed at source (`NA`), the 2022 COVID "
                    "suppression, or a 2023+ row where the source dropped "
                    "the column."
                ),
                "description": (
                    "Single (overall) CCRPI score of the entity — the "
                    "cross-cluster rollup, so an entity spanning multiple "
                    "clusters repeats one value across its rows while "
                    "ccrpi_score varies per cluster. 0-100 scale with "
                    "points-era bonus overshoot (observed max 110.3 in "
                    "2016). Published 2012-2019; 100%% NULL for 2022 and "
                    "2023+ (same coverage as ccrpi_score)."
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
                "Year coverage: 2012-2019 and 2022-2025. 2020 and 2021 are "
                "absent because Georgia paused CCRPI calculation during "
                "the COVID pandemic — do not interpolate them."
            ),
            (
                "Four source eras, two metric families. 2012-2017 publish "
                "component POINTS (per-component scales); 2018+ publish "
                "component SCORES (0-100). The families measure different "
                "things on different scales and are NOT comparable; each "
                "column is populated only in its source era, and the "
                "era-scoped NULL structure is enforced by contract quality "
                "checks."
            ),
            (
                "2022 partial publication: Progress, Closing Gaps, CCRPI "
                "Score, and Single Score are 100% NULL (bronze ships "
                "blanket `NA` under a federally-approved one-year COVID "
                "modification, described in the 2022 file's disclaimer "
                "row). Rows are retained — Content Mastery, Readiness, "
                "and high-cluster Graduation Rate carry real numbers."
            ),
            (
                "Points-era sub-era scale changes under unchanged column "
                "names: progress_points max ~22 (2012-2014) vs 40 "
                "(2015-2017); achievement_gap_points max 15 (2012-2014) "
                "vs 10 (2015-2017); etb_points max 2.0 / 3.0 / 2.5 "
                "(2012-2013 / 2014 / 2015-2017). Values preserved "
                "verbatim — stay within one framework sub-era for trends."
            ),
            (
                "The `RTC` (Residential Treatment Center) pseudo-district "
                "aggregates state RTC facilities as district-level rows "
                "(3 per year, one per grade cluster) in 2015-2017 and is "
                "an allowlisted district_code in the districts dimension "
                "(district_type `state_special`), consistent with the "
                "ccrpi_content_mastery and ccrpi_graduation_rate topics. "
                "The previous pipeline generation dropped these 9 rows; "
                "they are now preserved."
            ),
            (
                "ccrpi_score vs ccrpi_single_score: ccrpi_score is the "
                "per-grade-cluster score; ccrpi_single_score is the "
                "entity's overall (cross-cluster) score repeated on each "
                "of its cluster rows. They coincide for single-cluster "
                "entities. Both legitimately exceed 100 in the points era "
                "(bonus points; observed max 110.3 in 2016) — preserved, "
                "not capped."
            ),
            (
                "graduation_rate is the only column rescaled to the 0-1 "
                "proportion convention (bronze 0-100 / 100). All other "
                "metrics keep their natural CCRPI point / 0-100 score "
                "scales per the education-domain percentage-scale "
                "exceptions."
            ),
            (
                "Suppression markers `NA` (all eras), `TFS` (2019, "
                "2022-2025), and `Too Few Students` (2018 — in Content "
                "Mastery, Readiness, AND Graduation Rate) become NULL. "
                "2023-2025 ship Closing Gaps suppression as literal `NA` "
                "markers (196/228/207 cells; zero blank cells — a "
                "'blank cells' reading is a schema-inference artifact). "
                "No `100.00+` top-cap sentinel exists anywhere in this "
                "topic's bronze (unlike ccrpi_content_mastery)."
            ),
            (
                "`Grade Configuration` (the school's grade-offering list, "
                "2014+) is a school attribute, not a fact of this topic — "
                "it is not carried to gold."
            ),
        ],
        quality_checks=[
            {
                "name": "points_metrics_null_in_score_era",
                "description": (
                    "Structural: the six points-era metrics "
                    "(achievement/progress/achievement-gap/ED-EL-SWD/ETB/"
                    "challenge points) ceased publication with the 2018 "
                    "CCRPI redesign — bronze 2018+ does not carry the "
                    "columns, so every 2018+ row must be NULL on all six."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year >= 2018 AND "
                    "(achievement_points IS NOT NULL OR progress_points IS "
                    "NOT NULL OR achievement_gap_points IS NOT NULL OR "
                    "ed_el_swd_performance IS NOT NULL OR etb_points IS "
                    "NOT NULL OR challenge_points IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "score_metrics_null_in_points_era",
                "description": (
                    "Structural: the five score-era components (content "
                    "mastery, progress, closing gaps, readiness, "
                    "graduation rate) were introduced by the 2018 CCRPI "
                    "redesign — bronze 2012-2017 does not carry the "
                    "columns, so every 2012-2017 row must be NULL on all "
                    "five."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year <= 2017 AND "
                    "(content_mastery IS NOT NULL OR progress IS NOT NULL "
                    "OR closing_gaps IS NOT NULL OR readiness IS NOT NULL "
                    "OR graduation_rate IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "aggregate_scores_null_from_2022",
                "description": (
                    "ccrpi_score and ccrpi_single_score end with 2019: the "
                    "2022 file ships both as blanket `NA` (COVID "
                    "modification) and 2023+ files drop the columns "
                    "entirely — every year >= 2022 row must be NULL on "
                    "both."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year >= 2022 AND "
                    "(ccrpi_score IS NOT NULL OR ccrpi_single_score IS "
                    "NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "covid_2022_progress_closing_gaps_null",
                "description": (
                    "The federally-approved one-year COVID modification "
                    "suspended the Progress and Closing Gaps components "
                    "for 2022 — bronze ships blanket `NA`, so every 2022 "
                    "row must be NULL on both."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year = 2022 AND "
                    "(progress IS NOT NULL OR closing_gaps IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "single_score_constant_within_entity_year",
                "description": (
                    "ccrpi_single_score is an entity-level value repeated "
                    "across an entity's grade-cluster rows — within "
                    "(year, district_code, school_code) every non-NULL "
                    "ccrpi_single_score must be identical. Verified: 0 "
                    "violations across 19,303 entity-years."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year, district_code, "
                    "school_code FROM {object} WHERE ccrpi_single_score "
                    "IS NOT NULL GROUP BY year, district_code, "
                    "school_code HAVING COUNT(DISTINCT "
                    "ccrpi_single_score) > 1)"
                ),
                "mustBe": 0,
            },
            {
                "name": "points_era_components_sum_to_ccrpi_score",
                "description": (
                    "Component reconciliation, points era: ccrpi_score = "
                    "achievement_points + progress_points + "
                    "achievement_gap_points + challenge_points wherever "
                    "all five are published. Verified EXACT in bronze "
                    "(max |diff| 0.0, 0 violations across 2012-2017); "
                    "0.05 tolerance covers float representation only. Not "
                    "applicable to the score era, where ccrpi_score is a "
                    "weighted (not additive) combination."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year <= 2017 AND "
                    "achievement_points IS NOT NULL AND progress_points "
                    "IS NOT NULL AND achievement_gap_points IS NOT NULL "
                    "AND challenge_points IS NOT NULL AND ccrpi_score IS "
                    "NOT NULL AND ABS(achievement_points + "
                    "progress_points + achievement_gap_points + "
                    "challenge_points - ccrpi_score) > 0.05"
                ),
                "mustBe": 0,
            },
            {
                "name": "points_era_achievement_etb_challenge_co_null",
                "description": (
                    "Co-null trio, points era: achievement_points, "
                    "etb_points, and challenge_points are suppressed "
                    "together or published together on every 2012-2017 "
                    "row (verified: 0 row-level mismatches in all six "
                    "years)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year <= 2017 AND "
                    "((achievement_points IS NULL) <> (etb_points IS "
                    "NULL) OR (achievement_points IS NULL) <> "
                    "(challenge_points IS NULL))"
                ),
                "mustBe": 0,
            },
            {
                "name": "graduation_rate_high_cluster_only",
                "description": (
                    "Structural: GaDOE publishes the CCRPI Graduation "
                    "Rate component only on high-cluster rows — verified "
                    "in every score-era year (elementary/middle rows ship "
                    "`NA` without exception, including K-12 entities, "
                    "whose rate lands on their `high` row)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE graduation_rate "
                    "IS NOT NULL AND grade_cluster <> 'high'"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
