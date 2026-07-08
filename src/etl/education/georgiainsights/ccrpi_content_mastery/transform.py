"""Transform bronze ccrpi_content_mastery files into gold fact tables.

Source: Georgia Insights (GaDOE) — CCRPI Content Mastery reports student
proficiency on Georgia state assessments in core academic subjects at the
school, district, and (2014+) state level, broken out by demographic
subgroup, grade cluster, and (2012-2017) assessment type. 13 bronze files
span 2012-2025; there is no 2020 file (Georgia paused CCRPI during COVID).

The headline content-mastery metric carries four source-side labels across
eras, all landing in the single gold column ``indicator_score`` on its
natural 0-100 score scale (score columns are exempt from the 0-1 percentage
convention per education CLAUDE.md):

    2012-2014  "Meets & Exceeds Rate" / "Meets Exceeds Rate"  (0-100)
    2015-2017  "Weighted Proficiency Rate"   (0-100; exceeds 100 by design,
                                              max observed 146.154 in 2017)
    2018-2019  "Indicator Score"             (0-100)
    2021       "Achievement Rate"            (0-100 + "100.00+" sentinel)
    2022-2025  "Indicator Score"             (0-100 + "100.00+" in 2023)

Design decisions (every invariant re-verified against THIS topic's 13 bronze
files during authoring — see bronze-data-structure.md, incl. its Corrections
section):

- **Multi-sheet, string-typed reads.** 2012-2013 (.xls) and 2015-2017 split
  data alphabetically across 3 sheets; 2021-2022 carry an empty ``FAQs``
  metadata sheet that is skipped. The shared ``read_bronze_file`` reads only
  a workbook's first sheet, so reading goes through a local pandas helper
  (precedent: attendance_dashboard's ``_read_data_sheets``) using
  ``dtype=str`` + ``SUPPRESSION_VALUES`` — string typing both preserves the
  literal ``"ALL"`` aggregate sentinels that a type-inferred read coerces to
  NULL (2017, 2019, 2022-2025) and keeps zero-padded school codes intact.
  Excel reads load whole sheets, so read-loss raw == parsed by construction.

- **Header canonicalization before sheet concat.** Bronze headers drift in
  case ("System Id" vs "System ID"), punctuation ("MEETS & EXCEEDS RATE" vs
  2013-sheet-3's "Meets Exceeds Rate"), and whitespace. Headers are
  canonicalized (uppercase, ``&`` stripped, whitespace collapsed) before
  concatenation so 2013's mixed-case third sheet unites with sheets 1-2
  instead of producing silent all-null twin columns.

- **Era routing by column signature** (``detect_era_by_columns``), not year
  ranges. The 2024 file hides its header under a row-0 disclaimer; era
  detection failing at ``header_row=0`` triggers one retry at
  ``header_row=1`` rather than a filename-conditional.

- **"ALL" sentinels mark aggregates in EVERY year 2014+.** Re-verified with
  string-typed reads: the bronze cells are the literal string ``"ALL"`` in
  all of 2014-2025 (state = ALL/ALL, district = code/ALL). The
  "null Int64 IDs" described for 2019/2022+ in earlier drafts of the
  structure doc are an artifact of type-inferred reads. 2012-2013 have no
  aggregate rows (school-level only).

- **RTC pseudo-district (2015-2017).** ``System ID="RTC"`` rows (160/year,
  all with ``School ID="ALL"``) aggregate Residential Treatment Center
  facilities. ``RTC`` is an allowlisted pseudo-district code in the
  districts dimension (education CLAUDE.md), so these rows are kept as
  district-level facts with ``district_code="RTC"``. No school-level rows
  carry ``System ID="RTC"`` in any year (re-verified).

- **participation_rate → 0-1, unit=ratio.** Bronze ships 0-100 in
  2012-2017 and 2021-2022 (divided by 100 here) and 0-1 in 2018-2019 and
  2023-2025 (passed through). 2012 has 21 rows and 2013 has 73 rows with
  raw participation above 100 (max 105.9 / 108.4) — transfers-in inflate
  the tested/enrolled ratio, a real source quirk GaDOE began capping in
  2014. These are extreme-but-conceivable (§4b): preserved verbatim after
  /100 scaling (gold max 1.084), hence ``unit: ratio`` not ``proportion``.

- **"100.00+" score sentinel.** 2021 Achievement Rate ships 1,772 rows and
  2023 Indicator Score ships 2,683 rows with the literal string
  ``"100.00+"`` (a top-cap marker, NOT suppression; no other year has it —
  re-verified across all 13 files; the 2023 occurrence was missing from the
  structure doc and is documented in its Corrections section). Handling:
    * 2021: reconstructed from the learner-band columns via GaDOE's
      published weighting ``0.5*developing + proficient + 1.5*distinguished``
      (on the bronze 0-100 scale). The formula was re-verified against all
      52,699 numeric 2021 rows: max deviation 0.005 = exactly half the last
      published decimal, i.e. pure rounding. All 1,772 sentinel rows have
      numeric bands; reconstructed values span [100.005, 150.0].
    * 2023: no learner-band columns exist to reconstruct from, so sentinel
      rows are capped at 100.0 — preserving the "at/above 100" signal
      instead of nulling real top-performer scores.
  Both repairs are recorded via ``manifest.record_reclassified``. Any
  "100.00+" appearing in an era without an explicit policy raises.

- **Learner bands (2021-2022 only) → 0-1, unit=proportion.** The four
  ``pct_<level>_learner`` columns ship 0-100 (max exactly 100.0) and are
  divided by 100. Suppression is all-or-nothing across the four bands and
  the composite score (0 partial rows in either year — authored as quality
  checks). Cumulative ``pct_developing_learner_or_above`` /
  ``pct_proficient_learner_or_above`` are derived here (suppression-aware
  addition, NULL-propagating) and clipped at 1.0 — band sums overshoot by
  at most 0.0002 from independent 2-decimal rounding.

- **Band partition defect (2021).** Band sums equal 1.0 within rounding for
  >99.7%% of rows, but 2021 ships 146 rows (mostly High/ELA) whose bands sum
  materially below 1 (worst: 0.7646) — a genuine source defect, preserved
  per §4b (each band value is individually possible; only the partition
  identity fails). The partition quality check is therefore exact for 2022
  and budget-scoped for 2021 (26 rows beyond the 0.025 tolerance).

- **Asian / Pacific Islander is the combined bucket (§5b).** Every era
  publishes the explicit ``Asian/Pacific Islander`` label and never a
  separate Asian or Pacific Islander row; the shared aliases canonicalize
  it to ``asian_pacific_islander``. The split keys are never emitted.

- **No demographic collisions.** The 12 bronze subgroup labels collapse to
  10 canonical keys only via era spelling drift of the SAME concept
  (``American Indian/Alaskan`` vs ``... Native``; ``Students With/with
  Disability``) — never two distinct labels in one file mapping to one key
  (re-verified: zero duplicate natural keys in every file). The natural-key
  collision guard in ``main()`` would catch any future label drift; the v1
  pipeline's silent defensive mean-aggregation is intentionally dropped so
  collisions fail loudly instead.

- **Dedup tie-break**: each bronze year ships exactly one file and the
  natural key is unique within every file (re-verified, all 13 files), so
  dedup is purely defensive; ``sort_col="indicator_score"`` prefers a row
  with a reported score over a placeholder if a duplicate ever appears.

- **No §4b NULL masks.** Every observed value is within its metric's
  possible domain: scores ≥ 0 everywhere, indicator_targets within
  [1.7, 95], bands
  within [0, 1], participation documented above.

Natural key: (year, district_code, school_code, demographic, detail_level,
grade_cluster, subject). ``assessment_type`` looked like a key column
(2012-2017 use two test programs — CRCT/EOCT, then EOG/EOC) but the programs
never collide on the same (grade_cluster, subject) pair, so it is functionally
determined by the rest of the key; it is NULL for 2018+ where the bronze drops
the column. Both it and ``ccrpi_flag`` (a derived performance attribute) are
excluded from the contract grain via ``exclude_from_grain`` — keeping
``assessment_type`` in the grain forced serving-layer consumers to pin one
value, which silently excluded every 2018+ (NULL-era) row.
"""

import logging
from pathlib import Path

import pandas as pd
import polars as pl

from src.utils.demographics import (
    DEMOGRAPHIC_ALIASES,
    normalize_demographic_column,
)
from src.utils.metadata import write_data_dictionary
from src.utils.readers import (
    SUPPRESSION_VALUES,
    extract_year_from_filename,
    list_bronze_files,
)
from src.utils.subjects import apply_subject_normalization
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

TOPIC = "ccrpi_content_mastery"
BRONZE_DIR = Path("data/bronze/education/georgiainsights/ccrpi_content_mastery")
GOLD_DIR = Path("data/gold/education/ccrpi_content_mastery")
SOURCE_URL = "https://georgiainsights.gadoe.org/data-downloads/"

# Non-data sheets skipped by the multi-sheet reader. `FAQs` (2021-2022) is
# an empty metadata sheet; the other names are defensive for future files.
SKIP_SHEETS: set[str] = {"FAQs", "Read Me", "ReadMe", "Notes"}

# Aggregate-row sentinel in the ID columns (every year 2014+; upper-case in
# this source). Becomes NULL in gold after detail-level derivation.
GEOGRAPHY_SENTINEL = "ALL"

# Top-cap score sentinel ("at or above 100") in 2021 Achievement Rate and
# 2023 Indicator Score. NOT a suppression marker — see module docstring.
SCORE_CAP_SENTINEL = "100.00+"

# Era signatures over canonicalized (uppercase, &-stripped) headers. Order
# matters: detect_era_by_columns returns the first full match, so the
# signatures that share columns with later eras come first.
ERA_SIGNATURES: dict[str, list[str]] = {
    # 2012-2014: CRCT/EOCT program, Meets & Exceeds Rate metric.
    "era_1_meets_exceeds_2012_2014": [
        "MEETS EXCEEDS RATE",
        "ASSESSMENT TYPE",
        "REPORTING CATEGORY",
    ],
    # 2015-2017: EOG/EOC program, Weighted Proficiency Rate metric.
    "era_2_weighted_proficiency_2015_2017": [
        "WEIGHTED PROFICIENCY RATE",
        "ASSESSMENT TYPE",
        "REPORTING CATEGORY",
    ],
    # 2018-2019 + 2023-2025: Indicator Score with Target and Flag.
    "era_3_indicator_target_flag": [
        "INDICATOR",
        "INDICATOR SCORE",
        "TARGET",
        "FLAG",
        "REPORTING LABEL",
    ],
    # 2021: Achievement Rate + plain learner-band columns.
    "era_4_achievement_rate_2021": [
        "CONTENT AREA",
        "ACHIEVEMENT RATE",
        "BEGINNING LEARNER",
    ],
    # 2022: Indicator Score + "or Level N" learner-band columns.
    "era_5_learner_levels_2022": [
        "CONTENT AREA",
        "INDICATOR SCORE",
        "BEGINNING LEARNER OR LEVEL 1",
    ],
}

# Era-specific bronze->working rename maps plus behavior flags consumed by
# _transform_common. Keys are canonicalized headers (uppercase, no `&`).
_BASE_RENAME: dict[str, str] = {
    "SCHOOL YEAR": "year",
    "SYSTEM ID": "district_code",
    "SCHOOL ID": "school_code",
    "GRADE CLUSTER": "grade_cluster_raw",
}
ERA_CONFIGS: dict[str, dict] = {
    "era_1_meets_exceeds_2012_2014": {
        "rename": {
            **_BASE_RENAME,
            "REPORTING CATEGORY": "demographic_raw",
            "ASSESSMENT TYPE": "assessment_type_raw",
            "ASSESSMENT SUBJECT": "subject_raw",
            "PARTICIPATION RATE": "participation_rate_raw",
            "MEETS EXCEEDS RATE": "indicator_score_raw",
        },
        "participation_is_0_100": True,
        "has_assessment_type": True,
        "has_target_flag": False,
        "has_learner_cols": False,
        "score_sentinel_policy": None,
    },
    "era_2_weighted_proficiency_2015_2017": {
        "rename": {
            **_BASE_RENAME,
            "REPORTING CATEGORY": "demographic_raw",
            "ASSESSMENT TYPE": "assessment_type_raw",
            "ASSESSMENT SUBJECT": "subject_raw",
            "PARTICIPATION RATE": "participation_rate_raw",
            "WEIGHTED PROFICIENCY RATE": "indicator_score_raw",
        },
        "participation_is_0_100": True,
        "has_assessment_type": True,
        "has_target_flag": False,
        "has_learner_cols": False,
        "score_sentinel_policy": None,
    },
    "era_3_indicator_target_flag": {
        "rename": {
            **_BASE_RENAME,
            "REPORTING LABEL": "demographic_raw",
            "INDICATOR": "subject_raw",
            "PARTICIPATION RATE": "participation_rate_raw",
            "INDICATOR SCORE": "indicator_score_raw",
            "TARGET": "indicator_target_raw",
            "FLAG": "flag_raw",
        },
        "participation_is_0_100": False,  # already 0-1 in 2018-19 / 2023-25
        "has_assessment_type": False,
        "has_target_flag": True,
        "has_learner_cols": False,
        # 2023 ships 2,683 "100.00+" rows with no learner bands to
        # reconstruct from -> cap at 100.0 (2018/2019/2024/2025 have none).
        "score_sentinel_policy": "cap",
    },
    "era_4_achievement_rate_2021": {
        "rename": {
            **_BASE_RENAME,
            "REPORTING LABEL": "demographic_raw",
            "CONTENT AREA": "subject_raw",
            "PARTICIPATION RATE": "participation_rate_raw",
            "BEGINNING LEARNER": "pct_beginning_learner_raw",
            "DEVELOPING LEARNER": "pct_developing_learner_raw",
            "PROFICIENT LEARNER": "pct_proficient_learner_raw",
            "DISTINGUISHED LEARNER": "pct_distinguished_learner_raw",
            "ACHIEVEMENT RATE": "indicator_score_raw",
        },
        "participation_is_0_100": True,  # 2021 returns to the 0-100 scale
        "has_assessment_type": False,
        "has_target_flag": False,
        "has_learner_cols": True,
        # 1,772 "100.00+" rows, all with numeric bands -> reconstruct.
        "score_sentinel_policy": "reconstruct",
    },
    "era_5_learner_levels_2022": {
        "rename": {
            **_BASE_RENAME,
            "REPORTING LABEL": "demographic_raw",
            "CONTENT AREA": "subject_raw",
            "PARTICIPATION RATE": "participation_rate_raw",
            "BEGINNING LEARNER OR LEVEL 1": "pct_beginning_learner_raw",
            "DEVELOPING LEARNER OR LEVEL 2": "pct_developing_learner_raw",
            "PROFICIENT LEARNER OR LEVEL 3": "pct_proficient_learner_raw",
            "DISTINGUISHED LEARNER OR LEVEL 4": "pct_distinguished_learner_raw",
            "INDICATOR SCORE": "indicator_score_raw",
        },
        "participation_is_0_100": True,  # 2022 ships 0-100
        "has_assessment_type": False,
        "has_target_flag": False,
        "has_learner_cols": True,
        "score_sentinel_policy": None,  # verified: no "100.00+" in 2022
    },
}

# Subject normalization. Source vocabulary spans 13 granular subjects
# (2012-2014 CRCT/EOCT), 12 (2015-2017 EOG/EOC, with Algebra/Geometry
# replacing Mathematics-1/-2), and 4 broad indicators (2018+). The
# 2021-2022 label `English` is the same concept as `English Language Arts`.
# CRCT `Reading` is a distinct CRCT subject, NOT an ELA alias. Values are
# upper-cased + stripped before lookup (bronze pads `Science` and `Reading`
# with trailing spaces in several years).
SUBJECT_MAP: dict[str, str] = {
    "ENGLISH LANGUAGE ARTS": "english_language_arts",
    "ENGLISH": "english_language_arts",
    "MATHEMATICS": "mathematics",
    "SCIENCE": "science",
    "SOCIAL STUDIES": "social_studies",
    "READING": "reading",
    "9TH GRADE LITERATURE AND COMPOSITION": "9th_grade_literature_and_composition",
    "AMERICAN LITERATURE AND COMPOSITION": "american_literature_and_composition",
    "BIOLOGY": "biology",
    "ECONOMICS/BUSINESS/FREE ENTERPRISE": "economics_business_free_enterprise",
    "PHYSICAL SCIENCE": "physical_science",
    "US HISTORY": "us_history",
    "MATHEMATICS-1": "mathematics_1",
    "MATHEMATICS-2": "mathematics_2",
    "ALGEBRA I/COORDINATE ALGEBRA": "algebra_i_coordinate_algebra",
    "GEOMETRY/ANALYTIC GEOMETRY": "geometry_analytic_geometry",
}

# Test program (2012-2017 only). The acronyms ARE the canonical program
# names per education CLAUDE.md ("assessment_type" vocabulary).
ASSESSMENT_TYPE_MAP: dict[str, str] = {
    "CRCT": "crct",
    "EOCT": "eoct",
    "EOG": "eog",
    "EOC": "eoc",
}

# Single-letter bronze grade clusters -> descriptive snake_case.
GRADE_CLUSTER_MAP: dict[str, str] = {
    "E": "elementary",
    "M": "middle",
    "H": "high",
}

# CCRPI color flag -> descriptive values per data-cleaning-standards §16.
# Bronze `NA` becomes NULL at read time via SUPPRESSION_VALUES.
CCRPI_FLAG_MAP: dict[str, str] = {
    "G": "green",
    "G*": "green_star",
    "Y": "yellow",
    "R": "red",
}

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "detail_level",
    "grade_cluster",
    "assessment_type",
    "subject",
    "participation_rate",
    "indicator_score",
    "pct_beginning_learner",
    "pct_developing_learner",
    "pct_proficient_learner",
    "pct_distinguished_learner",
    "pct_developing_learner_or_above",
    "pct_proficient_learner_or_above",
    "indicator_target",
    "ccrpi_flag",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "demographic": pl.Utf8,
    "detail_level": pl.Utf8,
    "grade_cluster": pl.Utf8,
    "assessment_type": pl.Utf8,
    "subject": pl.Utf8,
    "participation_rate": pl.Float64,
    "indicator_score": pl.Float64,
    "pct_beginning_learner": pl.Float64,
    "pct_developing_learner": pl.Float64,
    "pct_proficient_learner": pl.Float64,
    "pct_distinguished_learner": pl.Float64,
    "pct_developing_learner_or_above": pl.Float64,
    "pct_proficient_learner_or_above": pl.Float64,
    "indicator_target": pl.Float64,
    "ccrpi_flag": pl.Utf8,
}

LEARNER_BAND_COLUMNS: list[str] = [
    "pct_beginning_learner",
    "pct_developing_learner",
    "pct_proficient_learner",
    "pct_distinguished_learner",
]
OR_ABOVE_COLUMNS: list[str] = [
    "pct_developing_learner_or_above",
    "pct_proficient_learner_or_above",
]

# Metric columns for manifest stats + the null-rate spike check. Columns
# absent from an era are 100% NULL for its years (genuine bronze gaps,
# documented in the contract) — the spike check warns on them by design.
METRIC_COLUMNS: list[str] = [
    "participation_rate",
    "indicator_score",
    *LEARNER_BAND_COLUMNS,
    *OR_ABOVE_COLUMNS,
    "indicator_target",
]

NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "detail_level",
    "grade_cluster",
    "assessment_type",
    "subject",
]

# The 10 canonical demographic keys this topic publishes (contract enum).
# 12 bronze labels collapse to 10 keys via cross-era spelling drift only.
DEMOGRAPHIC_VALUES: list[str] = sorted(
    [
        "all",
        # Race — combined Asian/Pacific Islander bucket (§5b); the source
        # never publishes separate Asian or Pacific Islander rows.
        "native_american",
        "asian_pacific_islander",
        "black",
        "hispanic",
        "multiracial",
        "white",
        # Special populations.
        "economically_disadvantaged",
        "english_learners",
        "students_with_disabilities",
    ]
)


# =============================================================================
# Bronze reading (multi-sheet xls/xlsx with header canonicalization)
# =============================================================================


def _canonicalize_header(name: str) -> str:
    """Collapse bronze header drift into one canonical uppercase key.

    Handles case drift ("System Id" / "System ID" / "SYSTEM ID"),
    punctuation drift ("MEETS & EXCEEDS RATE" vs 2013-sheet-3's
    "Meets Exceeds Rate"), embedded newlines, and whitespace runs.
    """
    cleaned = name.replace("\n", " ").replace("\r", " ").replace("&", " ")
    return " ".join(cleaned.split()).upper()


def _read_data_sheets(path: Path, header_row: int = 0) -> tuple[pl.DataFrame, dict]:
    """Read every data sheet of one bronze workbook and concatenate them.

    The shared ``read_bronze_file`` reads only a workbook's first sheet, but
    8 of the 13 bronze files carry multiple sheets (2012-2017 split data
    alphabetically across 3 sheets; 2021-2022 add an empty ``FAQs`` metadata
    sheet). Sheets are read directly via pandas with the same ``dtype=str``
    + ``SUPPRESSION_VALUES`` conventions as the shared XLSX path:
    ``dtype=str`` preserves the literal ``"ALL"`` aggregate sentinels and
    zero-padded codes that type inference destroys, and suppression markers
    (``TFS``, ``Too Few Students``, ``NA``, …) arrive as NULL. Headers are
    canonicalized per sheet BEFORE concatenation so 2013's mixed-case third
    sheet unites with its all-caps siblings instead of forming all-null twin
    columns.

    Args:
        path: Bronze .xls / .xlsx file (pandas picks xlrd / openpyxl).
        header_row: 0-indexed header row; the 2024 file needs 1 because row
            0 holds a disclaimer paragraph.

    Returns:
        ``(df, loss)`` — the concatenated all-Utf8 frame and a read-loss
        dict. Excel reads load whole sheets via pandas (rows cannot be
        dropped at parse time), so raw == parsed by construction.
    """
    xl = pd.ExcelFile(path)
    frames: list[pd.DataFrame] = []
    for sheet_name in xl.sheet_names:
        if sheet_name in SKIP_SHEETS:
            logger.info("  Skipping non-data sheet: %r", sheet_name)
            continue
        pdf = pd.read_excel(
            path,
            sheet_name=sheet_name,
            dtype=str,
            na_values=list(SUPPRESSION_VALUES),
            header=header_row,
        )
        pdf.columns = [_canonicalize_header(c) for c in pdf.columns]
        frames.append(pdf)
    if not frames:
        raise ValueError(f"{path.name}: no data sheets read (all skipped?)")

    df = pl.from_pandas(pd.concat(frames, ignore_index=True))
    loss = {"raw_rows": df.height, "parsed_rows": df.height, "format": "excel"}
    return df, loss


# =============================================================================
# Shared helpers
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


def _apply_categorical_map(
    df: pl.DataFrame,
    raw_col: str,
    gold_col: str,
    mapping: dict[str, str],
    manifest: TransformManifest,
    *,
    uppercase: bool = True,
) -> pl.DataFrame:
    """Strip/uppercase a raw column, map it strictly, and record the result.

    ``replace_strict(default=None)`` keeps NULL as NULL and turns any
    unmapped bronze value into NULL — which ``record_categorical`` counts as
    unmapped, making ``manifest.write()`` raise before bad gold lands. The
    normalized (stripped/uppercased) series is what hits the map, so THAT is
    recorded as "bronze observed" — bronze quirks like trailing-space
    ``"Science       "`` would otherwise show as false-positive unmapped.
    """
    raw_expr = pl.col(raw_col).cast(pl.Utf8).str.strip_chars()
    if uppercase:
        raw_expr = raw_expr.str.to_uppercase()
    normalized = df.select(raw_expr.alias("_norm"))["_norm"]
    df = df.with_columns(raw_expr.replace_strict(mapping, default=None).alias(gold_col))
    manifest.record_categorical(
        column=gold_col,
        map_dict=mapping,
        bronze_series=normalized,
        gold_series=df[gold_col],
    )
    return df.drop(raw_col)


# =============================================================================
# Era-generic transform
# =============================================================================


def _derive_keys(df: pl.DataFrame, year: int) -> pl.DataFrame:
    """Derive detail_level and the gold geography/year key columns.

    Detail level comes from the "ALL" sentinels — read BEFORE nulling them,
    or state (ALL/ALL) becomes indistinguishable from district (code/ALL).
    2012-2013 have no sentinels, so every row falls through to "school".
    """
    # Year cross-check: every file's School Year column is a single value
    # equal to the filename year. A mismatch means a misnamed or mis-filled
    # file — fail loudly rather than partition under the wrong year.
    sheet_years = {int(float(v)) for v in df["year"].drop_nulls().unique().to_list()}
    if sheet_years != {year}:
        raise ValueError(
            f"{TOPIC} {year}: sheet School Year values {sorted(sheet_years)} "
            f"disagree with filename year {year}"
        )

    # The (ALL, <code>) quadrant is structurally absent in every year; it
    # has no derivable level, so its appearance must fail loudly.
    is_dist_all = pl.col("district_code") == GEOGRAPHY_SENTINEL
    is_sch_all = pl.col("school_code") == GEOGRAPHY_SENTINEL
    bad_quadrant = df.filter(is_dist_all & ~is_sch_all.fill_null(False)).height
    if bad_quadrant:
        raise ValueError(
            f"{TOPIC} {year}: {bad_quadrant} row(s) with System ID='ALL' but "
            f"a concrete School ID — unknown detail level"
        )
    return df.with_columns(
        pl.when(is_dist_all & is_sch_all)
        .then(pl.lit("state"))
        .when(is_sch_all)
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .alias("detail_level"),
        # Geography keys: "ALL" -> NULL; zfill(3) pads 3-digit district codes
        # while passing 7-digit charter codes AND the allowlisted "RTC"
        # pseudo-district (3 chars, unchanged) through; zfill(4) restores
        # leading zeros on school codes (e.g. "182" -> "0182").
        pl.when(is_dist_all)
        .then(None)
        .otherwise(pl.col("district_code").str.zfill(3))
        .alias("district_code"),
        pl.when(is_sch_all)
        .then(None)
        .otherwise(pl.col("school_code").str.zfill(4))
        .alias("school_code"),
        pl.col("year").cast(pl.Int32, strict=False).alias("year"),
    )


def _normalize_categoricals(
    df: pl.DataFrame, year: int, era: str, manifest: TransformManifest
) -> pl.DataFrame:
    """Normalize demographic, grade_cluster, assessment_type, and subject.

    Demographic normalization goes through the shared canonical path (§5),
    recording the effective slice of the alias map — only the aliases this
    file's labels actually hit — so the manifest stays reviewable while the
    unmapped guard still flags any label the shared map cannot place.
    """
    cfg = ERA_CONFIGS[era]
    df = df.with_columns(
        normalize_demographic_column("demographic_raw").alias("demographic")
    )
    observed_upper = {
        str(v).strip().upper()
        for v in df["demographic_raw"].drop_nulls().unique().to_list()
    }
    effective_map = {
        k: v for k, v in DEMOGRAPHIC_ALIASES.items() if k in observed_upper
    }
    manifest.record_categorical(
        column="demographic",
        map_dict=effective_map,
        bronze_series=df["demographic_raw"],
        gold_series=df["demographic"],
    )
    df = df.drop("demographic_raw")

    # Grade cluster: E/M/H -> elementary/middle/high.
    df = _apply_categorical_map(
        df, "grade_cluster_raw", "grade_cluster", GRADE_CLUSTER_MAP, manifest
    )

    # Assessment type (2012-2017 only): CRCT/EOCT then EOG/EOC. NULL for
    # 2018+ where the bronze drops the column entirely.
    if cfg["has_assessment_type"]:
        df = _apply_categorical_map(
            df, "assessment_type_raw", "assessment_type", ASSESSMENT_TYPE_MAP, manifest
        )
    else:
        logger.info("Year %d (%s): no Assessment Type column — NULL fill", year, era)
        df = df.with_columns(pl.lit(None).cast(pl.Utf8).alias("assessment_type"))

    # Subject: topic-local map (strip handles the trailing-space `Science`/
    # `Reading` quirks), then the shared spelling resolver so this topic
    # stays aligned with sibling assessment topics (§10a/§16). The shared
    # pass is a no-op on current values — pure drift insurance.
    df = _apply_categorical_map(df, "subject_raw", "subject", SUBJECT_MAP, manifest)
    return df.with_columns(apply_subject_normalization("subject").alias("subject"))


def _transform_scores(
    df: pl.DataFrame, year: int, era: str, manifest: TransformManifest
) -> pl.DataFrame:
    """Cast/scale participation_rate and indicator_score (incl. sentinels).

    Participation rate -> 0-1 (unit: ratio): 2012-2017 and 2021-2022 ship
    0-100; 2018-2019 and 2023-2025 already ship 0-1. Indicator score stays
    on its 0-100 scale; the "100.00+" top-cap sentinel is repaired per the
    era policy, and an occurrence in an era without a policy raises.
    """
    cfg = ERA_CONFIGS[era]
    # strict=False nulls any residual marker the reader missed (era-1/2
    # "No Data" is not in SUPPRESSION_VALUES and is nulled here).
    participation = pl.col("participation_rate_raw").cast(pl.Float64, strict=False)
    if cfg["participation_is_0_100"]:
        participation = participation / 100.0
    df = df.with_columns(participation.alias("participation_rate")).drop(
        "participation_rate_raw"
    )

    # Indicator score: 0-100 score scale, preserved — exceeds 100 by design
    # in 2015-2017 and via 2021 reconstruction.
    sentinel_count = df.filter(
        pl.col("indicator_score_raw") == SCORE_CAP_SENTINEL
    ).height
    policy = cfg["score_sentinel_policy"]
    numeric_score = pl.col("indicator_score_raw").cast(pl.Float64, strict=False)
    if sentinel_count and policy is None:
        raise ValueError(
            f"{TOPIC} {year}: {sentinel_count} unexpected '{SCORE_CAP_SENTINEL}' "
            f"score sentinel(s) in era {era} with no handling policy"
        )
    if policy == "reconstruct":
        # 2021: rebuild the capped score from the learner bands via GaDOE's
        # published weighting (re-verified on all numeric 2021 rows to
        # within 0.005 = rounding). Bands are still on 0-100 here.
        reconstructed = (
            pl.col("pct_developing_learner_raw").cast(pl.Float64, strict=False) * 0.5
            + pl.col("pct_proficient_learner_raw").cast(pl.Float64, strict=False)
            + pl.col("pct_distinguished_learner_raw").cast(pl.Float64, strict=False)
            * 1.5
        )
        score = (
            pl.when(pl.col("indicator_score_raw") == SCORE_CAP_SENTINEL)
            .then(reconstructed)
            .otherwise(numeric_score)
        )
        if sentinel_count:
            manifest.record_reclassified(
                year,
                sentinel_count,
                "indicator_score '100.00+' top-cap sentinel reconstructed from "
                "learner bands (0.5*developing + proficient + 1.5*distinguished)",
            )
    elif policy == "cap":
        # 2023: no learner bands exist to reconstruct from — cap at 100.0
        # to preserve the at/above-100 signal instead of nulling it.
        score = (
            pl.when(pl.col("indicator_score_raw") == SCORE_CAP_SENTINEL)
            .then(pl.lit(100.0))
            .otherwise(numeric_score)
        )
        if sentinel_count:
            manifest.record_reclassified(
                year,
                sentinel_count,
                "indicator_score '100.00+' top-cap sentinel capped at 100.0 "
                "(no learner bands available to reconstruct the true value)",
            )
    else:
        score = numeric_score
    return df.with_columns(score.alias("indicator_score")).drop("indicator_score_raw")


def _transform_bands_target_flag(
    df: pl.DataFrame, year: int, era: str, manifest: TransformManifest
) -> pl.DataFrame:
    """Transform the era-optional metric blocks: learner bands, target, flag.

    Learner bands (2021-2022 only): 0-100 -> 0-1 proportions, then the
    `_or_above` cumulatives (suppression-aware NULL-propagating addition,
    clipped at 1.0 — independent 2-decimal rounding lets band sums overshoot
    1.0 by at most 0.0002). Target/flag (2018-2019, 2023-2025 only): the
    indicator_target is a 0-100 score; bronze `NA`/`TFS` became NULL at read,
    and every 2024 mathematics row is NULL by design (no math targets that
    year). Absent
    blocks are NULL-filled so the cross-era schema stays uniform.
    """
    cfg = ERA_CONFIGS[era]
    if cfg["has_learner_cols"]:
        df = df.with_columns(
            [
                (pl.col(f"{c}_raw").cast(pl.Float64, strict=False) / 100.0).alias(c)
                for c in LEARNER_BAND_COLUMNS
            ]
        ).drop([f"{c}_raw" for c in LEARNER_BAND_COLUMNS])
        df = df.with_columns(
            (
                pl.col("pct_developing_learner")
                + pl.col("pct_proficient_learner")
                + pl.col("pct_distinguished_learner")
            )
            .clip(upper_bound=1.0)
            .alias("pct_developing_learner_or_above"),
            (pl.col("pct_proficient_learner") + pl.col("pct_distinguished_learner"))
            .clip(upper_bound=1.0)
            .alias("pct_proficient_learner_or_above"),
        )
    else:
        logger.info("Year %d (%s): no learner-band columns — NULL fill", year, era)
        df = df.with_columns(
            [
                pl.lit(None).cast(pl.Float64).alias(c)
                for c in LEARNER_BAND_COLUMNS + OR_ABOVE_COLUMNS
            ]
        )

    # The indicator_target is on the same 0-100 score scale as
    # indicator_score; the flag map recodes G/G*/Y/R to descriptive values
    # per §16.
    if cfg["has_target_flag"]:
        df = df.with_columns(
            pl.col("indicator_target_raw")
            .cast(pl.Float64, strict=False)
            .alias("indicator_target")
        ).drop("indicator_target_raw")
        df = _apply_categorical_map(
            df, "flag_raw", "ccrpi_flag", CCRPI_FLAG_MAP, manifest, uppercase=False
        )
    else:
        logger.info("Year %d (%s): no Target/Flag columns — NULL fill", year, era)
        df = df.with_columns(
            pl.lit(None).cast(pl.Float64).alias("indicator_target"),
            pl.lit(None).cast(pl.Utf8).alias("ccrpi_flag"),
        )
    return df


def _transform_common(
    df: pl.DataFrame,
    year: int,
    era: str,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Transform one canonical-header bronze frame into gold rows.

    All five eras converge on the same gold schema; era differences are
    expressed declaratively in ERA_CONFIGS (rename map + behavior flags)
    so a column can never be silently skipped by a divergent code path.
    """
    rename_map: dict[str, str] = ERA_CONFIGS[era]["rename"]
    _require_columns(df, list(rename_map), f"{TOPIC} {year}")
    df = df.rename(rename_map)
    df = _derive_keys(df, year)
    df = _normalize_categoricals(df, year, era, manifest)
    df = _transform_scores(df, year, era, manifest)
    df = _transform_bands_target_flag(df, year, era, manifest)
    return df.select(STANDARD_COLUMNS)


# =============================================================================
# File dispatcher
# =============================================================================


def transform_file(
    path: Path, year: int, manifest: TransformManifest
) -> pl.DataFrame | None:
    """Read one bronze workbook, detect its era, and transform it.

    Era detection failing at header_row=0 triggers one retry at header_row=1
    — the 2024 file hides its header under a row-0 disclaimer, and the retry
    generalizes to any future disclaimer-topped file without a filename
    conditional.
    """
    df, loss = _read_data_sheets(path, header_row=0)
    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        logger.info(
            "%s: era detection failed at header_row=0 — retrying at "
            "header_row=1 (disclaimer row?)",
            path.name,
        )
        df, loss = _read_data_sheets(path, header_row=1)
        era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(
            f"{path.name} (year={year}): no era signature matches columns "
            f"{sorted(df.columns)} — update ERA_SIGNATURES for new schemas"
        )

    # Excel reads cannot drop rows (raw == parsed by construction), so this
    # records nothing unless pandas/pyarrow behavior ever changes.
    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])
    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)

    if df.height == 0:
        logger.warning("Year %d: bronze file %s is empty, skipping", year, path.name)
        return None
    logger.info(
        "Processing %s (year=%d, era=%s, %d rows)", path.name, year, era, df.height
    )
    return _transform_common(df, year, era, manifest)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for ccrpi_content_mastery."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file (read-loss accounted per file).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR, extensions=[".xls", ".xlsx"]):
        year = extract_year_from_filename(path.name)
        if year is None:
            raise ValueError(f"Cannot extract year from filename: {path.name}")
        result = transform_file(path, year, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize columns/dtypes across eras and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)
    logger.info("Combined %d rows across %d files", combined.height, len(all_dfs))

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean an alias-collapse bug and must raise, not be deduped away.
    # (Re-verified: the natural key is unique within every bronze file, and
    # the 12 bronze demographic labels never collide within one file, so no
    # aggregate_demographic_collisions step is needed.)
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: each year ships in exactly one file with a unique natural
    # key (verified), so dedup is defensive only; prefer the row with a
    # reported (non-null, higher) indicator_score over a placeholder.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=[k for k in NATURAL_KEYS if k != "detail_level"],
        district_keys=[
            k for k in NATURAL_KEYS if k not in ("detail_level", "school_code")
        ],
        state_keys=[
            k
            for k in NATURAL_KEYS
            if k not in ("detail_level", "school_code", "district_code")
        ],
        sort_col="indicator_score",
    )

    # 4. Geography nulling (shared domain rules — transform and validator
    # read the same dict, so they cannot disagree). No §4b masks: every
    # observed value is within its metric's possible domain (module
    # docstring documents the preserved extreme-but-conceivable values).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. Expected NULL-rate spikes (documented bronze gaps):
    # learner bands outside 2021-2022, indicator_target/ccrpi_flag outside
    # 2018-2019/2023-2025, assessment_type for 2018+, and the 2024
    # mathematics indicator_target suppression.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning(
            "NULL-rate spikes (expected bronze gaps): %s", spike_result.details
        )
    validate_output(combined, required_non_null=["year", "detail_level", "demographic"])

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
        # 2.0.0: assessment_type dropped from the row grain (functionally
        # determined by grade_cluster + subject) — a breaking grain change.
        version="2.0.0",
        description=(
            "CCRPI Content Mastery measures student proficiency on Georgia "
            "state assessments in core academic subjects at the school, "
            "district, and (2014+) state level, broken out by demographic "
            "subgroup, grade cluster, and (2012-2017) assessment type. The "
            "primary `indicator_score` metric unifies four source labels "
            "across eras: Meets & Exceeds Rate (2012-2014, CRCT/EOCT), "
            "Weighted Proficiency Rate (2015-2017, EOG/EOC; exceeds 100 by "
            "design), Indicator Score (2018-2019, 2022-2025), and "
            "Achievement Rate (2021). 2021-2022 add four learner-band "
            "proportions with derived `_or_above` cumulatives; 2018-2019 "
            "and 2023-2025 add an improvement `indicator_target` and a color "
            "`ccrpi_flag`. 2020 is absent — Georgia paused CCRPI during "
            "COVID. This is the deep-dive into the Content Mastery component "
            "only (by demographic, subject, and assessment type); the overall "
            "CCRPI score and the side-by-side scorecard of all five "
            "rolled-up component scores live in the `ccrpi_scoring_by_component` "
            "topic (the CCRPI overview), which this topic does not duplicate."
        ),
        title="CCRPI Content Mastery",
        summary=(
            "Georgia student proficiency scores on state assessments (the "
            "CCRPI Content Mastery component) by subject, grade cluster, and "
            "demographic subgroup, 2012-2025."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2025,
                "description": (
                    "Ending calendar year of the school year (2025 = "
                    "2024-2025). Sourced from the bronze `School Year` "
                    "column, cross-checked against the filename year. 2020 "
                    "does not exist (COVID pause)."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "3-digit GOSA district code (zero-padded) for standard "
                    "districts; 7-digit code for state-charter systems; the "
                    "allowlisted pseudo-district code `RTC` (Residential "
                    "Treatment Center aggregate, 2015-2017 only). NULL for "
                    "state-level rows. FK to districts dimension."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0182",
                "description": (
                    "4-digit GOSA school code (zero-padded; bronze strips "
                    "leading zeros from some codes). NULL for district- and "
                    "state-level rows. FK to schools dimension (composite "
                    "key with district_code)."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "black",
                "validValues": DEMOGRAPHIC_VALUES,
                "short_description": (
                    "Which student group the row covers - `all`, a race, or "
                    "a special population (economically disadvantaged, "
                    "English learners, students with disabilities)."
                ),
                "description": (
                    "Canonical demographic code (FK to demographics "
                    "dimension). `all` is the unfiltered total. Race uses "
                    "the combined `asian_pacific_islander` bucket — the "
                    "source publishes the explicit `Asian/Pacific Islander` "
                    "label in every era and never separate Asian or Pacific "
                    "Islander rows. Cross-era label spellings (`American "
                    "Indian/Alaskan [Native]`, `Students With/with "
                    "Disability`) fold into single canonical keys."
                ),
            },
            {
                "name": "grade_cluster",
                "type": "string",
                "nullable": False,
                "example": "elementary",
                "validValues": sorted(set(GRADE_CLUSTER_MAP.values())),
                "short_description": (
                    "Grade band the row covers: elementary, middle, or high."
                ),
                "description": (
                    "Grade cluster the row aggregates: `elementary`, "
                    "`middle`, or `high` (bronze single-letter E/M/H "
                    "expanded). A cluster of grades, not a single grade — "
                    "distinct from `grade_level` per §16."
                ),
            },
            {
                "name": "assessment_type",
                "type": "string",
                "exclude_from_grain": True,
                "example": "eog",
                "validValues": sorted(set(ASSESSMENT_TYPE_MAP.values())),
                "short_description": (
                    "Which state testing program the score came from "
                    "(CRCT/EOCT or EOG/EOC); NULL for 2018 and later."
                ),
                "description": (
                    "Georgia state assessment program: `crct`/`eoct` "
                    "(2012-2014) or `eog`/`eoc` (2015-2017). NULL for every "
                    "2018+ row — the source dropped the column when CCRPI "
                    "consolidated to four broad indicators. An attribute of "
                    "the row, not part of the grain: the two programs never "
                    "report the same (grade_cluster, subject) pair, so it is "
                    "functionally determined by the rest of the key."
                ),
                "null_meaning": (
                    "Row is from 2018+ where the source no longer reports "
                    "an assessment program breakdown."
                ),
            },
            {
                "name": "subject",
                "type": "string",
                "nullable": False,
                "example": "mathematics",
                "validValues": sorted(set(SUBJECT_MAP.values())),
                "short_description": (
                    "Academic subject tested (e.g. mathematics, science); "
                    "broad areas from 2018, more granular subjects before."
                ),
                "description": (
                    "Academic subject assessed, snake_case. 2018+ uses 4 "
                    "broad areas (english_language_arts, mathematics, "
                    "science, social_studies); 2012-2017 split into 12-13 "
                    "granular subjects (CRCT `reading` is a distinct subject, "
                    "not an ELA alias). The 2021-2022 label `English` folds "
                    "into `english_language_arts`. Social studies has "
                    "roughly half the rows of other subjects in 2021+ "
                    "(assessed only in high school and part of middle)."
                ),
            },
            {
                "name": "participation_rate",
                "type": "float64",
                "unit": "ratio",
                "example": 0.987,
                "null_meaning": (
                    "Suppressed by GaDOE (`Too Few Students`/`TFS`, "
                    "`No Data`, or `NA`)."
                ),
                "description": (
                    "Share of eligible students assessed, 0-1 decimal "
                    "scale. Bronze ships 0-100 in 2012-2017 and 2021-2022 "
                    "(divided by 100 here) and 0-1 in 2018-2019 and "
                    "2023-2025 (passed through). 94 rows (21 in 2012, 73 in "
                    "2013; max 1.059/1.084 after scaling) legitimately "
                    "exceed 1.0 — transfers-in inflated the tested/enrolled "
                    "ratio before GaDOE began capping in 2014. Preserved "
                    "verbatim, hence unit `ratio`, not `proportion`. "
                    "State-level participation collapses to ~0.65 in 2021 "
                    "(COVID-year testing disruption) versus ~0.98-0.99 in "
                    "every other year — faithful to bronze, not a scaling "
                    "artifact."
                ),
            },
            {
                "name": "indicator_score",
                "type": "float64",
                "unit": "score",
                "value_min": 0,
                "key_metric": True,
                "example": 74.3,
                "short_description": (
                    "Content-mastery proficiency score on a 0-100 scale "
                    "(can exceed 100 in some years by design); NULL when "
                    "suppressed."
                ),
                "null_meaning": (
                    "Suppressed by GaDOE (`Too Few Students`/`TFS`, "
                    "`No Data`, or `NA`)."
                ),
                "description": (
                    "Primary content-mastery metric on its natural 0-100 "
                    "SCORE scale (exempt from the 0-1 percentage "
                    "convention). Unifies Meets & Exceeds Rate (2012-2014), "
                    "Weighted Proficiency Rate (2015-2017 — exceeds 100 by "
                    "design, max observed 146.154), Indicator Score "
                    "(2018-2019, 2022-2025), and Achievement Rate (2021). "
                    "No upper bound is declared because >100 is "
                    "legitimate. The `100.00+` top-cap sentinel is repaired "
                    "two ways: 2021 (1,772 rows) reconstructed from the "
                    "learner bands as 0.5*developing + proficient + "
                    "1.5*distinguished (verified to rounding precision on "
                    "all numeric 2021 rows; reconstructed values span "
                    "[100.005, 150.0]); 2023 (2,683 rows) capped at 100.0 "
                    "because no learner bands exist that year to "
                    "reconstruct from."
                ),
            },
            {
                "name": "pct_beginning_learner",
                "type": "float64",
                "unit": "proportion",
                "example": 0.21,
                "null_meaning": (
                    "Year outside 2021-2022 (bands not published), or "
                    "suppressed by GaDOE (all four bands suppress "
                    "together)."
                ),
                "description": (
                    "Share of students at the Beginning Learner band, 0-1 "
                    "scale (bronze 0-100 divided by 100). Published only "
                    "for 2021-2022; NULL every other year."
                ),
            },
            {
                "name": "pct_developing_learner",
                "type": "float64",
                "unit": "proportion",
                "example": 0.34,
                "null_meaning": (
                    "Year outside 2021-2022 (bands not published), or "
                    "suppressed by GaDOE (all four bands suppress "
                    "together)."
                ),
                "description": (
                    "Share at the Developing Learner band, 0-1 scale. "
                    "Published only for 2021-2022; NULL every other year."
                ),
            },
            {
                "name": "pct_proficient_learner",
                "type": "float64",
                "unit": "proportion",
                "example": 0.29,
                "null_meaning": (
                    "Year outside 2021-2022 (bands not published), or "
                    "suppressed by GaDOE (all four bands suppress "
                    "together)."
                ),
                "description": (
                    "Share at the Proficient Learner band, 0-1 scale. "
                    "Published only for 2021-2022; NULL every other year."
                ),
            },
            {
                "name": "pct_distinguished_learner",
                "type": "float64",
                "unit": "proportion",
                "example": 0.16,
                "null_meaning": (
                    "Year outside 2021-2022 (bands not published), or "
                    "suppressed by GaDOE (all four bands suppress "
                    "together)."
                ),
                "description": (
                    "Share at the Distinguished Learner band, 0-1 scale. "
                    "Published only for 2021-2022; NULL every other year. "
                    "The four bands sum to 1.0 within rounding except for "
                    "146 defective 2021 source rows (worst sum 0.7646) — "
                    "preserved as published."
                ),
            },
            {
                "name": "pct_developing_learner_or_above",
                "type": "float64",
                "unit": "proportion",
                "example": 0.79,
                "null_meaning": (
                    "NULL whenever the underlying bands are NULL (year "
                    "outside 2021-2022, or suppressed)."
                ),
                "description": (
                    "Derived cumulative: developing + proficient + "
                    "distinguished, 0-1 scale, clipped at 1.0 (independent "
                    "rounding can overshoot by up to 0.0002). NULL when any "
                    "summand is NULL. Only populated for 2021-2022."
                ),
            },
            {
                "name": "pct_proficient_learner_or_above",
                "type": "float64",
                "unit": "proportion",
                "example": 0.45,
                "null_meaning": (
                    "NULL whenever the underlying bands are NULL (year "
                    "outside 2021-2022, or suppressed)."
                ),
                "description": (
                    "Derived cumulative: proficient + distinguished, 0-1 "
                    "scale, clipped at 1.0. NULL when any summand is NULL. "
                    "Only populated for 2021-2022."
                ),
            },
            {
                "name": "indicator_target",
                "type": "float64",
                "unit": "score",
                "value_min": 0,
                "value_max": 100,
                "example": 82.5,
                "null_meaning": (
                    "Year outside 2018-2019/2023-2025, suppressed (`NA`/"
                    "`TFS`), or a 2024 mathematics row (no math targets "
                    "computed that year)."
                ),
                "description": (
                    "CCRPI improvement target on the same 0-100 scale as "
                    "indicator_score (observed range [1.7, 95.0]; unlike "
                    "indicator_score it is bounded at 100). Published only "
                    "for 2018-2019 and 2023-2025. Every 2024 mathematics "
                    "row is NULL by design — GaDOE computed no math targets "
                    "during the new-math-standards rollout. NOT cross-topic "
                    "comparable: each CCRPI topic's target inherits its "
                    "companion metric's scale (§16)."
                ),
            },
            {
                "name": "ccrpi_flag",
                "type": "string",
                "exclude_from_grain": True,
                "example": "green",
                "validValues": sorted(set(CCRPI_FLAG_MAP.values())),
                "short_description": (
                    "Performance color flag (green, green_star, yellow, "
                    "red); published only 2018-2019 and 2023-2025."
                ),
                "null_meaning": (
                    "Year outside 2018-2019/2023-2025, bronze `NA` (not "
                    "rated), or a 2024 mathematics row (no math flags that "
                    "year)."
                ),
                "description": (
                    "CCRPI performance color flag: `green`, `green_star` "
                    "(green with caveat), `yellow`, or `red` (bronze "
                    "G/G*/Y/R recoded per §16). Published only for "
                    "2018-2019 and 2023-2025; bronze `NA` becomes NULL. A "
                    "derived performance attribute functionally determined "
                    "by the rest of the row key, so it is excluded from the "
                    "contract grain."
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
                "Year coverage: 2012-2019 and 2021-2025. 2020 is absent "
                "because Georgia paused CCRPI during COVID — do not "
                "interpolate."
            ),
            (
                "indicator_score and indicator_target are on the natural "
                "0-100 SCORE "
                "scale; participation_rate and the six pct_*_learner "
                "columns are on the 0-1 decimal scale."
            ),
            (
                "2015-2017 Weighted Proficiency Rate legitimately exceeds "
                "100 (students exceeding the standard earn weighted credit; "
                "max observed 146.154), so indicator_score declares no "
                "upper bound."
            ),
            (
                "`100.00+` top-cap sentinel: 2021 Achievement Rate (1,772 "
                "rows) is reconstructed from the learner bands as "
                "0.5*developing + proficient + 1.5*distinguished; 2023 "
                "Indicator Score (2,683 rows) is capped at 100.0 (no bands "
                "exist in 2023 to reconstruct from). No other year ships "
                "the sentinel."
            ),
            (
                "participation_rate has 94 rows above 1.0 (21 in 2012, 73 "
                "in 2013; max 1.084) — transfers-in inflated the "
                "tested/enrolled ratio before GaDOE began capping at 100 in "
                "2014. Preserved verbatim (unit: ratio)."
            ),
            (
                "2021 ships 146 rows (mostly high-school ELA) whose four "
                "learner bands sum materially below 1.0 (worst 0.7646) — a "
                "verified source defect, preserved as published; the "
                "partition quality check is exact for 2022 and "
                "budget-scoped for 2021."
            ),
            (
                "assessment_type is NULL for all 2018+ rows (column dropped "
                "at source); learner bands are NULL outside 2021-2022; "
                "indicator_target/ccrpi_flag are NULL outside "
                "2018-2019/2023-2025, "
                "and NULL for every 2024 mathematics row (no math targets "
                "that year). These are bronze publication gaps, not "
                "transform bugs."
            ),
            (
                "Race uses the combined `asian_pacific_islander` bucket: "
                "every era publishes the explicit `Asian/Pacific Islander` "
                "label and never separate Asian or Pacific Islander rows; "
                "the split keys are never emitted."
            ),
            (
                "The `RTC` (Residential Treatment Center) pseudo-district "
                "aggregates state RTC facilities in 2015-2017 and is an "
                "allowlisted district_code in the districts dimension "
                "(district_type `state_special`)."
            ),
            (
                "2012-2013 publish school-level rows only; state and "
                "district aggregates begin in 2014. State rows have NULL "
                "district_code and school_code; district rows have NULL "
                "school_code."
            ),
        ],
        quality_checks=[
            {
                "name": "learner_band_partition_2022",
                "description": (
                    "In 2022 the four learner-band proportions partition "
                    "the tested population: they sum to 1.0 within 0.025 on "
                    "every fully-populated row. Verified against bronze: 0 "
                    "violations (worst 2022 deviation is 0.0218). 2021 is "
                    "covered by a budget-scoped check because it ships "
                    "verified defective rows."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year = 2022 "
                    "AND pct_beginning_learner IS NOT NULL "
                    "AND pct_developing_learner IS NOT NULL "
                    "AND pct_proficient_learner IS NOT NULL "
                    "AND pct_distinguished_learner IS NOT NULL "
                    "AND ABS(pct_beginning_learner + pct_developing_learner "
                    "+ pct_proficient_learner + pct_distinguished_learner "
                    "- 1.0) > 0.025"
                ),
                "mustBe": 0,
            },
            {
                "name": "learner_band_partition_2021_budget",
                "description": (
                    "2021 ships 146 rows whose bands sum materially below "
                    "1.0 (verified source defect, preserved per §4b), of "
                    "which 26 deviate beyond the 0.025 tolerance. This "
                    "budget check pins the defect from growing (allows <30 "
                    "for float-boundary jitter) while still catching any "
                    "transform-introduced scale error, which would violate "
                    "by tens of thousands of rows."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year = 2021 "
                    "AND pct_beginning_learner IS NOT NULL "
                    "AND pct_developing_learner IS NOT NULL "
                    "AND pct_proficient_learner IS NOT NULL "
                    "AND pct_distinguished_learner IS NOT NULL "
                    "AND ABS(pct_beginning_learner + pct_developing_learner "
                    "+ pct_proficient_learner + pct_distinguished_learner "
                    "- 1.0) > 0.025"
                ),
                "mustBeLessThan": 30,
            },
            {
                "name": "or_above_cumulative_consistency",
                "description": (
                    "The derived cumulatives equal the clipped sums of "
                    "their bands on every populated row: "
                    "pct_developing_learner_or_above = LEAST(developing + "
                    "proficient + distinguished, 1.0) and "
                    "pct_proficient_learner_or_above = LEAST(proficient + "
                    "distinguished, 1.0), to float precision (1e-9). "
                    "Structural: the transform derives them exactly this "
                    "way."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(pct_developing_learner_or_above IS NOT NULL AND "
                    "ABS(pct_developing_learner_or_above - "
                    "LEAST(pct_developing_learner + pct_proficient_learner "
                    "+ pct_distinguished_learner, 1.0)) > 0.000000001) "
                    "OR (pct_proficient_learner_or_above IS NOT NULL AND "
                    "ABS(pct_proficient_learner_or_above - "
                    "LEAST(pct_proficient_learner + "
                    "pct_distinguished_learner, 1.0)) > 0.000000001)"
                ),
                "mustBe": 0,
            },
            {
                "name": "learner_band_co_suppression",
                "description": (
                    "Learner-band suppression is all-or-nothing: the four "
                    "band proportions and the two derived cumulatives are "
                    "either all populated or all NULL on every row. "
                    "Verified against bronze 2021-2022: 0 partially "
                    "suppressed rows."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(pct_beginning_learner IS NULL) <> "
                    "(pct_developing_learner IS NULL) OR "
                    "(pct_beginning_learner IS NULL) <> "
                    "(pct_proficient_learner IS NULL) OR "
                    "(pct_beginning_learner IS NULL) <> "
                    "(pct_distinguished_learner IS NULL) OR "
                    "(pct_beginning_learner IS NULL) <> "
                    "(pct_developing_learner_or_above IS NULL) OR "
                    "(pct_beginning_learner IS NULL) <> "
                    "(pct_proficient_learner_or_above IS NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "learner_bands_only_2021_2022",
                "description": (
                    "Structural: learner-band columns are published only in "
                    "2021-2022 — every band and cumulative is NULL for all "
                    "other years."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "year NOT IN (2021, 2022) AND ("
                    "pct_beginning_learner IS NOT NULL OR "
                    "pct_developing_learner IS NOT NULL OR "
                    "pct_proficient_learner IS NOT NULL OR "
                    "pct_distinguished_learner IS NOT NULL OR "
                    "pct_developing_learner_or_above IS NOT NULL OR "
                    "pct_proficient_learner_or_above IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "score_band_co_null_2021_2022",
                "description": (
                    "In 2021-2022 the composite score and the learner bands "
                    "suppress together: indicator_score is NULL exactly "
                    "when the bands are NULL. Verified against bronze: 0 "
                    "mismatches in either year (the 2021 `100.00+` sentinel "
                    "rows all carry numeric bands)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "year IN (2021, 2022) AND "
                    "(indicator_score IS NULL) <> "
                    "(pct_beginning_learner IS NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "assessment_type_era_coverage",
                "description": (
                    "Structural: assessment_type is populated on every "
                    "2012-2017 row (bronze ships the column with zero "
                    "nulls) and NULL on every 2018+ row (column dropped at "
                    "source)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(year <= 2017 AND assessment_type IS NULL) OR "
                    "(year >= 2018 AND assessment_type IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "indicator_target_flag_era_coverage",
                "description": (
                    "Structural: indicator_target and ccrpi_flag are "
                    "published only in 2018-2019 and 2023-2025 — both NULL "
                    "for every other year."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "year NOT IN (2018, 2019, 2023, 2024, 2025) AND "
                    "(indicator_target IS NOT NULL OR ccrpi_flag IS NOT NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "indicator_target_flag_2024_mathematics_null",
                "description": (
                    "Every 2024 mathematics row has NULL indicator_target "
                    "and ccrpi_flag — GaDOE computed neither during the "
                    "2023-2024 new-math-standards rollout (bronze ships "
                    "literal `NA` on all 32,470 math rows; verified)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year = 2024 "
                    "AND subject = 'mathematics' "
                    "AND (indicator_target IS NOT NULL OR ccrpi_flag IS NOT "
                    "NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "indicator_score_bounded_years",
                "description": (
                    "indicator_score never exceeds 100 in the years whose "
                    "bronze metric is structurally capped at 100: "
                    "2012-2014 (Meets & Exceeds Rate), 2018-2019 and "
                    "2022/2024/2025 (Indicator Score), and 2023 (enforced "
                    "by the `100.00+` cap repair). Verified: per-year max "
                    "is exactly 100.0 in all nine years. Only 2015-2017 "
                    "(Weighted Proficiency Rate, by design) and 2021 "
                    "(sentinel reconstruction) may exceed 100, so a "
                    "scale error in the bounded years cannot pass "
                    "silently."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year IN "
                    "(2012, 2013, 2014, 2018, 2019, 2022, 2023, 2024, 2025) "
                    "AND indicator_score IS NOT NULL "
                    "AND indicator_score > 100"
                ),
                "mustBe": 0,
            },
            {
                "name": "indicator_score_structural_ceiling",
                "description": (
                    "indicator_score never exceeds 150 in any year — the "
                    "hard structural ceiling of the CCRPI weighting (max "
                    "weight 1.5 x 100). Observed maxima: 146.154 (2017 "
                    "Weighted Proficiency Rate) and exactly 150.0 (2021 "
                    "sentinel reconstruction at 100%% distinguished). A "
                    "0-100 column read as basis points or a double-scaled "
                    "year would violate immediately."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "indicator_score IS NOT NULL AND indicator_score > 150"
                ),
                "mustBe": 0,
            },
            {
                "name": "participation_rate_above_one_only_2012_2013",
                "description": (
                    "participation_rate exceeds 1.0 only in 2012-2013 (94 "
                    "verified bronze rows, max 1.084 — transfers-in "
                    "inflating the tested/enrolled ratio before GaDOE began "
                    "capping at 100 in 2014). From 2014 on the source caps "
                    "at 100%%, so any later value above 1.0 is a scale "
                    "error, not a quirk."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE year >= 2014 "
                    "AND participation_rate IS NOT NULL "
                    "AND participation_rate > 1.0"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
