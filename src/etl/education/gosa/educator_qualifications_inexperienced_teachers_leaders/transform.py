"""Transform educator_qualifications_inexperienced_teachers_leaders to gold.

Source: Governor's Office of Student Achievement (GOSA) — Inexperienced
Teachers and Leaders report, school years 2017-18 through 2023-24 (7 CSV
files, one per year). For every Georgia public school, school district, and
the state, the source publishes total educator FTE, the FTE of educators
classified as Inexperienced (within the first years of their career, per the
ESSA inexperienced-educator standard), and that count as an integer
percentage of total FTE. Unlike the sibling emergency / out-of-field topics
(Teachers-only), this topic reports BOTH Teachers and Leaders
(principals/assistant principals), and the Leaders workforce introduces two
extra poverty-subgroup values (`not_applicable`, `unknown`).

Design decisions (from bronze-data-structure.md + data-cleaning-standards):

- **Two column-name eras, one tidy shape, detected by column signature.**
  Era 1 (2023-2024): `#CATEGORY_DESC` (verified constant `Inexperienced`,
  dropped) + `CATEGORY_FTE` / `CATEGORY_FTE_PCT`. Era 2 (2018-2022):
  `INEXPERIENCED_FTE` / `INEXPERIENCED_FTE_PCT`. No mislabeled-column era
  exists in this topic (unlike the emergency sibling).
- **`LABEL_LVL_3_DESC` -> `role`** (`teachers` / `leaders`) — a real fact
  categorical here (the sibling topics are Teachers-only and drop it).
- **`LABEL_LVL_2_DESC` -> `poverty_subgroup`** (`total` / `high_poverty` /
  `low_poverty` / `not_applicable` / `unknown`): a SCHOOL-poverty stratum,
  not a student demographic — no `demographic` column in this topic.
  `not_applicable` and `unknown` appear on Leaders rows only (verified:
  zero Teachers rows carry them in any year).
- **Name-to-code resolution is the core difficulty**: bronze publishes only
  district/school NAMES. Codes are resolved via the shared
  `src/etl/education/gosa/_educator_lookups.py` resolver — year-aware
  certified_personnel lookups first, then curated pins/aliases, then the
  guarded mechanical dimension matches. Rows that remain unresolvable are
  dropped ONLY under documented predicates; anything else unresolved RAISES.
- **52-char INSTN_NAME truncation repair (2023-2024 only).** GOSA truncates
  INSTN_NAME at exactly 52 chars and truncates the charter-container
  district label to a generic placeholder ("State Charter Schools " / "-").
  Two repair branches, both gated on (placeholder district AND length 52)
  and both manifest-recorded via record_reclassified:
  * **Suffix restoration** — the cut fell inside the trailing
    "- All Schools" (e.g. "...Atlanta SMART Academy- All"): the row is a
    district aggregate whose entity name fully survived. Strip the
    truncated suffix to recover the entity name.
  * **Hybrid rescue** — the cut fell INSIDE the entity name, before any of
    "- All Schools" survived (e.g. "...Atlanta Heights Charter Sc",
    exactly 52 chars, starting with a charter-container prefix): treat as
    a district aggregate keyed on the truncated entity name. These rows
    carry Leaders data no bare school-name partner publishes — dropping
    them would lose real signal.
  Both branches write the entity name into SCHOOL_DSTRCT_NM (and
  "<entity>- All Schools" into INSTN_NAME) so the shared district resolver
  — whose MANUAL_DISTRICT_CODE_OVERRIDES carries explicit pins for the
  ambiguous 52-char forms — binds the district code.
- **Dropped-row classes** (all manifest-recorded per year):
  * `state_charter_placeholder_district` — unresolved rows under the
    generic truncated charter-container labels. Recorded ZERO rows in
    the current run: every bare school-name row under the 2023-2024
    placeholder containers resolves via the shared resolver
    (school-first fallback / placeholder rescue / campus pins), and the
    rebuild-era schools dim fixed the former Statesboro STEAM FK orphan.
    Kept as a documented guard against future bronze drift.
  * `source_gap_district` / `source_gap_school` — documented entities with
    no single faithful dimension target (Ivy Prep Kirkwood, the
    distinguisher-erased "...Foothills Charter High School" truncation,
    K-8 split campuses, closed schools, etc.).
  * `force_drop_ambiguous_truncated_district_aggregate` — the
    "State Charter Schools II- Genesis Innovation Academy" truncation
    erased the Boys/Girls distinguisher, so the hybrid-rescued aggregate
    RESOLVES — arbitrarily, to one of two sister campuses
    (7830615/7830616). The bare school-name rows publish the correct
    per-campus values, so the resolved aggregate is a redundant,
    arbitrarily-attributed double-count. Dropped at district level
    regardless of resolution via `is_force_drop_district_agg` (this is the
    only educator topic that wires the predicate in). 4 rows in 2023,
    3 in 2024. Prior data reviews verified this drop deliberate.
  * `duplicate_rows_deduped` — the 2024 truncation "State Charter
    Schools- Utopian Academy for the Arts " collapses TWO entities
    (Charter School 7820121 + Trilith 7820619) onto one pinned district
    key, but their Leaders/Total metric tuples are IDENTICAL
    ((NULL, NULL, 1.0) — both TFS-suppressed with rate 100), so the
    collision guard passes and dedup collapses the pair to one row
    (1 row, 2024 only). The same-named 2024 Leaders/Low Poverty
    truncated row is single and stays. Known attribution caveat: both
    surviving truncated-name aggregates are bound to the pinned 7820121
    even though the Low Poverty row almost certainly describes the
    Trilith campus (7820619, whose school row is the only Low Poverty
    Utopian stratum) — preserved as-is to match the v1-approved
    handling and documented in the contract.
- **Era-asymmetric suppression.** 2018-2020 publish true zeros with no
  suppression (723-765 genuine-zero rows per year); 2021+ mask values below
  the reporting floor of 10 with `TFS` (-> NULL via the all-string read +
  strict=False cast). Read NULL as "< 10" for 2021+ but as genuinely
  missing pre-2021.
- **No §4b masks.** No impossible values exist: the bronze percent is
  within [0, 100] in every year, FTEs are non-negative. Six bronze rows
  (2018-2020 Leaders at tiny programs) carry `inexperienced_fte` exceeding
  `total_fte` by exactly 0.1 — an artifact of GOSA rounding each FTE to
  0.1 independently; extreme-but-conceivable, preserved + documented (the
  numerator-within-denominator quality check carries a 0.15 tolerance).
- **Quality checks (§15b)**, all verified against bronze across all 7
  years: numerator within denominator (+0.15 rounding tolerance; 6 bronze
  rows sit at exactly +0.1); rate reconciliation within 0.10 where
  total_fte >= 10 (GOSA computes the integer percent from unrounded FTEs;
  observed max deviation 0.09 at 10-FTE programs — below the floor the
  published rounded FTEs are too coarse for the check to be meaningful);
  school-level stratum rows mirror the school's Total row on both FTE
  metrics (a school IS its stratum; verified exact); at most one non-total
  stratum per school-role; Teachers never carry `not_applicable`/`unknown`;
  district/state HP+LP within Total + 0.55 (observed max excess 0.5,
  Greene County Leaders 2020); exactly 6 state rows per year (2 roles x
  total/high_poverty/low_poverty — `not_applicable`/`unknown` never appear
  at state level).
- **v1-parity outcome: DIFFERS, fully accounted (verified row-by-row
  against the approved v1 gold pulled read-only from S3, whose hash
  matches the v1 baseline).** 20 v1 rows -> 17 new rows, all 2023-2024,
  four classes, each a deliberate fix of the v1 "lowest-code dedup"
  footgun (cf. the rebuild's shared resolver, which is year-aware-first
  and cardinality-guarded):
  (1) Coweta Charter Academy district aggregates (6 rows) rebind
  7830601 -> 7830610 via the shared pin — v1 fragmented the entity
  (school rows at 7830610/0610, district aggregates at the school-less
  7830601 twin); gold now keys both levels to one district code.
  (2) Coastal Middle School (Savannah-Chatham, 5 rows) rebinds
  (625, 0198) -> (625, 0311): certified_personnel publishes 0311 for
  this school in EVERY year 2011-2024, and v1 itself used 0311 for
  2018-2022 — its 2023-2024 rows fell to the lowest-code dim join
  (0198, a same-named twin) because the bronze district-name truncation
  ("Savannah-Chatham Count") defeated v1's year-aware lookup. The new
  gold keeps the school's series continuous at 0311.
  (3) Oakhurst Elementary School (City Schools of Decatur, 6 rows)
  rebinds (773, 0103) -> (773, 0105) — identical pattern to (2);
  certified_personnel says 0105 in every year, v1 broke the series at
  2023.
  (4) Barrow Arts and Sciences Academy 2023 (3 rows) dropped: cert
  personnel 2023 publishes BOTH 0300 and 0309 for the name and the dim
  carries both twins, so any single binding is a guess; v1 guessed 0300
  via lowest-code. Documented SOURCE_GAP_SCHOOLS drop (2021/2022/2024
  rows still bind 0300 via unambiguous cert personnel).

Judgment calls (non-interactive run):

1. The v1 transform carried an "atlanta city" -> "atlanta public schools"
   district expansion. Verified obsolete: no bronze year of this topic
   contains "Atlanta City" (every year publishes "Atlanta Public Schools"),
   so no topic-specific `district_name_expansions` are passed — the
   resolver's residual guard would surface the name if it ever reappears.
2. Unresolvable-name drops kept exactly at the documented predicate set
   (placeholder containers + SOURCE_GAP entries + the Genesis FORCE_DROP)
   rather than widening any mechanical match rule — fidelity over coverage.
3. The 2024 Utopian Leaders/Total truncated pair (two physical campuses
   collapsed onto one pinned key) carries IDENTICAL metric tuples, so it is
   collapsed by dedup rather than dropped — the surviving row is a faithful
   aggregate for the pinned 7820121. The companion Leaders/Low Poverty row
   stays bound to 7820121 despite likely describing the Trilith campus;
   preserved to match the v1-approved handling, documented in the contract.
4. Rate-reconciliation scoped to total_fte >= 10 with tolerance 0.10:
   below 10 FTE, GOSA's 0.1-rounded published FTEs deviate from the
   unrounded-percent by up to 0.9 (e.g. 0.1/0.1 = 1.0 vs published 10%%),
   so an unscoped check would be vacuous noise rather than an invariant.
5. `poverty_subgroup` kept as a topic categorical (not `demographic`): the
   strata describe school-poverty quartile membership, not student
   subpopulations.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

from src.etl.education.gosa._educator_lookups import (
    DISTRICT_AGG_SUFFIX,
    STATE_DISTRICT_SENTINEL,
    STATE_INSTN_SENTINEL,
    EducatorNameResolver,
    is_force_drop_district_agg,
    is_source_gap_district,
    is_source_gap_school,
    is_state_charter_placeholder_district,
    load_dimension_lookups,
    load_year_aware_lookups,
)
from src.utils.metadata import write_data_dictionary
from src.utils.readers import (
    extract_year_from_filename,
    list_bronze_files,
    parse_school_year,
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

TOPIC = "educator_qualifications_inexperienced_teachers_leaders"
BRONZE_DIR = Path(
    "data/bronze/education/gosa/educator_qualifications_inexperienced_teachers_leaders"
)
GOLD_DIR = Path(
    "data/gold/education/educator_qualifications_inexperienced_teachers_leaders"
)
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# `LABEL_LVL_3_DESC` -> role (snake_case per §10). Both values are real in
# every year — this topic is the only educator-qualifications topic that
# reports Leaders alongside Teachers.
ROLE_MAP: dict[str, str] = {
    "Teachers": "teachers",
    "Leaders": "leaders",
}

# `LABEL_LVL_2_DESC` -> poverty_subgroup (snake_case per §10). A poverty
# stratum of schools, NOT a student demographic (see module docstring).
# `Not Applicable` / `Unknown` appear on Leaders rows only.
POVERTY_SUBGROUP_MAP: dict[str, str] = {
    "Total": "total",
    "High Poverty": "high_poverty",
    "Low Poverty": "low_poverty",
    "Not Applicable": "not_applicable",
    "Unknown": "unknown",
}

# Era-detection signatures (column presence), most specific first: Era 1's
# `#CATEGORY_DESC` is unique to it; Era 2 carries the metric pair in the
# column names instead.
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_1_2023_2024_category_desc": [
        "#CATEGORY_DESC",
        "LONG_SCHOOL_YEAR",
        "SCHOOL_DSTRCT_NM",
        "INSTN_NAME",
        "LABEL_LVL_3_DESC",
        "LABEL_LVL_2_DESC",
        "FTE",
        "CATEGORY_FTE",
        "CATEGORY_FTE_PCT",
    ],
    "era_2_2018_2022_inexperienced_named": [
        "LONG_SCHOOL_YEAR",
        "SCHOOL_DSTRCT_NM",
        "INSTN_NAME",
        "LABEL_LVL_3_DESC",
        "LABEL_LVL_2_DESC",
        "FTE",
        "INEXPERIENCED_FTE",
        "INEXPERIENCED_FTE_PCT",
    ],
}

# Bronze metric source columns per era (total_fte source is `FTE` in both).
ERA_METRIC_COLUMNS: dict[str, tuple[str, str]] = {
    "era_1_2023_2024_category_desc": ("CATEGORY_FTE", "CATEGORY_FTE_PCT"),
    "era_2_2018_2022_inexperienced_named": (
        "INEXPERIENCED_FTE",
        "INEXPERIENCED_FTE_PCT",
    ),
}

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export splitting, then dropped by export_to_parquet().
# No `demographic` column — poverty_subgroup is a school-poverty stratum.
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "role",
    "poverty_subgroup",
    "total_fte",
    "inexperienced_fte",
    "inexperienced_fte_rate",
    "detail_level",
]

# All three metrics are Float64: FTEs are fractional (e.g. 58.2) and the
# rate lives on the 0-1 decimal scale.
TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "role": pl.Utf8,
    "poverty_subgroup": pl.Utf8,
    "total_fte": pl.Float64,
    "inexperienced_fte": pl.Float64,
    "inexperienced_fte_rate": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = ["total_fte", "inexperienced_fte", "inexperienced_fte_rate"]

# Per-detail-level natural keys (collision guard + dedup). Guards run per
# level so a key column that is uniformly NULL at that level (school_code at
# district grain, district_code at state grain) never joins NULL-vs-NULL —
# polars group_by treats NULL == NULL but join does not, and mixing the two
# would silently mask divergent duplicates.
SCHOOL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "role",
    "poverty_subgroup",
]
DISTRICT_KEYS: list[str] = ["year", "district_code", "role", "poverty_subgroup"]
STATE_KEYS: list[str] = ["year", "role", "poverty_subgroup"]

# GOSA's hard INSTN_NAME truncation point in the 2023-2024 files. Both
# repair branches key on names of exactly this length.
_GOSA_TRUNCATION_LEN = 52

# Every truncation point of the trailing "- All Schools" suffix from "- A"
# through "- All School" (a full "- All Schools" ending is handled by the
# normal ends_with detail-level test, not this regex).
_TRUNCATED_ALL_SCHOOLS_RE = r"- A(l(l(\s(S(c(h(o(o(l)?)?)?)?)?)?)?)?)?$"

# Charter-container prefixes that signal a hybrid-rescue candidate: a
# 52-char INSTN_NAME starting with one of these (with no surviving piece of
# "- All Schools") is a district-aggregate label cut mid-entity-name.
_CHARTER_INSTN_PREFIXES = ("State Charter Schools", "Commission Charter Schools")

# Separator for (district_name, school_name) pair-membership masks; never
# appears in GOSA name cells.
_PAIR_SEP = "\x1f"


# =============================================================================
# Era transforms
# =============================================================================


def _assert_constant_column(
    df: pl.DataFrame, column: str, expected: str, label: str
) -> None:
    """Raise if a verified-constant bronze column carries any other value.

    A new value (e.g. a second qualification category) means the pipeline
    needs a schema decision, not silent passthrough.
    """
    observed = set(df[column].unique().to_list())
    if observed - {expected}:
        raise ValueError(
            f"{label}: expected {column} == {expected!r} only, saw {sorted(observed)}"
        )


def _repair_truncated_placeholder_aggregates(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Repair 52-char-truncated district-aggregate rows (2023-2024 quirk).

    GOSA's 2023-2024 files truncate the charter-container district label to
    a generic placeholder AND truncate INSTN_NAME at exactly 52 chars. Two
    repair branches (mutually exclusive, see module docstring):

    * suffix restoration — the cut fell inside the trailing "- All Schools"
      (regex match), so the entity name fully survived;
    * hybrid rescue — the cut fell inside the entity name itself (row
      starts with a charter-container prefix, no surviving "- A...").

    Both branches write the recovered entity name into SCHOOL_DSTRCT_NM and
    "<entity>- All Schools" into INSTN_NAME, so detail-level detection
    classifies the row as a district aggregate and the shared resolver
    (with its explicit 52-char-truncation pins) binds the district code.
    Each repair is recorded via manifest.record_reclassified.
    """
    placeholder_names = [
        n
        for n in df["SCHOOL_DSTRCT_NM"].unique().to_list()
        if is_state_charter_placeholder_district(n)
    ]
    if not placeholder_names:
        return df

    is_placeholder = pl.col("SCHOOL_DSTRCT_NM").is_in(placeholder_names)
    is_cut = pl.col("INSTN_NAME").str.len_chars() == _GOSA_TRUNCATION_LEN
    suffix_hit = pl.col("INSTN_NAME").str.contains(_TRUNCATED_ALL_SCHOOLS_RE)
    starts_charter = pl.any_horizontal(
        [pl.col("INSTN_NAME").str.starts_with(p) for p in _CHARTER_INSTN_PREFIXES]
    )

    # Materialize both masks BEFORE any mutation so they agree on which rows
    # to rewrite (the second mutation must not re-evaluate against a
    # partially-mutated frame).
    df = df.with_columns(
        (is_placeholder & is_cut & suffix_hit).alias("_restore"),
        (is_placeholder & is_cut & starts_charter & ~suffix_hit).alias("_hybrid"),
    )
    n_restore = int(df["_restore"].sum())
    n_hybrid = int(df["_hybrid"].sum())
    if n_restore:
        manifest.record_reclassified(
            year, n_restore, "restored_truncated_all_schools_suffix"
        )
    if n_hybrid:
        manifest.record_reclassified(
            year, n_hybrid, "hybrid_rescued_truncated_district_aggregate"
        )
    if not (n_restore or n_hybrid):
        return df.drop("_restore", "_hybrid")

    # Recover the entity name: strip the truncated "- All Schools" tail
    # (restore branch) or the trailing space/hyphen junk left by the
    # mid-entity cut (hybrid branch).
    entity = (
        pl.when(pl.col("_restore"))
        .then(pl.col("INSTN_NAME").str.replace(_TRUNCATED_ALL_SCHOOLS_RE, ""))
        .when(pl.col("_hybrid"))
        .then(pl.col("INSTN_NAME").str.strip_chars_end(" -"))
        .otherwise(None)
    )
    df = df.with_columns(entity.alias("_entity"))
    repaired = pl.col("_entity").is_not_null()
    df = df.with_columns(
        pl.when(repaired)
        .then(pl.col("_entity"))
        .otherwise(pl.col("SCHOOL_DSTRCT_NM"))
        .alias("SCHOOL_DSTRCT_NM"),
        pl.when(repaired)
        .then(pl.col("_entity") + pl.lit(DISTRICT_AGG_SUFFIX))
        .otherwise(pl.col("INSTN_NAME"))
        .alias("INSTN_NAME"),
    )
    logger.info(
        "Year %d: repaired %d suffix-truncated + %d mid-entity-truncated "
        "placeholder district aggregates",
        year,
        n_restore,
        n_hybrid,
    )
    return df.drop("_restore", "_hybrid", "_entity")


def _transform_era(
    df: pl.DataFrame,
    year: int,
    era: str,
    manifest: TransformManifest,
    label: str,
) -> pl.DataFrame:
    """Transform one bronze file (either era) to the pre-resolution shape.

    Verifies the era's constant column, repairs the 2023-2024 truncated
    placeholder aggregates, derives detail_level from the name sentinels,
    recodes role + poverty stratum, and casts the metric trio. The raw name
    columns are retained for the resolution step in transform_file().
    """
    fte_col, pct_col = ERA_METRIC_COLUMNS[era]
    # Rename-coverage guard: a missing metric column would silently NULL the
    # whole year (the classic rename bug) — fail loudly instead.
    missing = [c for c in ("FTE", fte_col, pct_col) if c not in df.columns]
    if missing:
        raise ValueError(f"{label}: expected metric columns missing: {missing}")

    # Era 1 encodes the qualification category as a row dimension — verify
    # it is the constant `Inexperienced` before dropping it.
    if era == "era_1_2023_2024_category_desc":
        _assert_constant_column(df, "#CATEGORY_DESC", "Inexperienced", label)

    # 2023-2024 truncation repair must run BEFORE detail-level detection —
    # it is what turns the truncated placeholder rows back into district
    # aggregates.
    df = _repair_truncated_placeholder_aggregates(df, year, manifest)

    # One batched with_columns: (a) detail level from the name sentinels —
    # state rows pair the two state sentinels; district aggregates end with
    # "- All Schools" (regular hyphen + space, prefix == SCHOOL_DSTRCT_NM);
    # everything else is a school row; (b) role + poverty recodes — the
    # sentinel default surfaces any future new value as unmapped, failing
    # manifest.write().
    df = df.with_columns(
        pl.when(
            (pl.col("SCHOOL_DSTRCT_NM") == STATE_DISTRICT_SENTINEL)
            & (pl.col("INSTN_NAME") == STATE_INSTN_SENTINEL)
        )
        .then(pl.lit("state"))
        .when(pl.col("INSTN_NAME").str.ends_with(DISTRICT_AGG_SUFFIX))
        .then(pl.lit("district"))
        .otherwise(pl.lit("school"))
        .alias("detail_level"),
        pl.col("LABEL_LVL_3_DESC")
        .replace_strict(ROLE_MAP, default="99999999")
        .alias("role"),
        pl.col("LABEL_LVL_2_DESC")
        .replace_strict(POVERTY_SUBGROUP_MAP, default="99999999")
        .alias("poverty_subgroup"),
    )
    manifest.record_categorical(
        column="role",
        map_dict=ROLE_MAP,
        bronze_series=df["LABEL_LVL_3_DESC"],
        gold_series=df["role"],
    )
    manifest.record_categorical(
        column="poverty_subgroup",
        map_dict=POVERTY_SUBGROUP_MAP,
        bronze_series=df["LABEL_LVL_2_DESC"],
        gold_series=df["poverty_subgroup"],
    )

    return df.select(
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.col("SCHOOL_DSTRCT_NM").alias("district_name_raw"),
        pl.col("INSTN_NAME").alias("instn_name_raw"),
        pl.col("detail_level"),
        pl.col("role"),
        pl.col("poverty_subgroup"),
        # All-string read: TFS already became NULL via the reader's
        # suppression list; strict=False catches any stray non-numeric.
        # True zeros (2018-2020, pre-suppression) survive the cast.
        pl.col("FTE").cast(pl.Float64, strict=False).alias("total_fte"),
        pl.col(fte_col).cast(pl.Float64, strict=False).alias("inexperienced_fte"),
        # Bronze publishes an integer 0-100 percent (verified across all
        # years); divide by 100 onto the 0-1 scale per §4.
        (pl.col(pct_col).cast(pl.Float64, strict=False) / 100.0).alias(
            "inexperienced_fte_rate"
        ),
    )


# =============================================================================
# Name resolution + documented drops
# =============================================================================


def _attach_codes(
    df: pl.DataFrame, year: int, resolver: EducatorNameResolver
) -> pl.DataFrame:
    """Resolve (district_code, school_code) for every row via the shared chain.

    Resolution depends only on (year, district_name, instn_name,
    detail_level), so it runs once per distinct combination and joins back —
    same result as per-row resolution, far fewer resolver calls.
    """
    combos = df.select("district_name_raw", "instn_name_raw", "detail_level").unique(
        maintain_order=True
    )
    resolved = [
        resolver.resolve_row(year, district_name, instn_name, detail)
        for district_name, instn_name, detail in combos.iter_rows()
    ]
    codes = combos.with_columns(
        pl.Series("district_code", [dc for dc, _ in resolved], dtype=pl.Utf8),
        pl.Series("school_code", [sc for _, sc in resolved], dtype=pl.Utf8),
    )
    return df.join(
        codes, on=["district_name_raw", "instn_name_raw", "detail_level"], how="left"
    )


def _drop_documented_gaps(
    df: pl.DataFrame, year: int, manifest: TransformManifest
) -> pl.DataFrame:
    """Drop the documented unresolvable / unattributable rows, per class.

    Four classes (see module docstring + _educator_lookups rationale):
    placeholder charter containers (unresolved only), district-level source
    gaps (unresolved only), the Genesis force-drop (district aggregates
    dropped REGARDLESS of resolution — the truncated name binds arbitrarily
    to one of two sister campuses), and school-level source gaps. The
    unresolved-only predicates fire after the resolver, so a future rescue
    (new pin/alias) takes precedence automatically.
    """
    # Placeholder charter containers + district source gaps — unresolved
    # district names only.
    unresolved_names = (
        df.filter(
            pl.col("district_code").is_null()
            & (pl.col("district_name_raw") != STATE_DISTRICT_SENTINEL)
        )["district_name_raw"]
        .unique()
        .to_list()
    )
    placeholder_names = {
        n for n in unresolved_names if is_state_charter_placeholder_district(n)
    }
    gap_district_names = {n for n in unresolved_names if is_source_gap_district(n)}

    for names, reason in (
        (placeholder_names, "state_charter_placeholder_district"),
        (gap_district_names, "source_gap_district"),
    ):
        if not names:
            continue
        mask = (
            pl.col("district_code").is_null()
            & (pl.col("district_name_raw") != STATE_DISTRICT_SENTINEL)
            & pl.col("district_name_raw").is_in(sorted(names))
        )
        count = df.filter(mask).height
        if count:
            logger.info(
                "Year %d: dropping %d row(s) — %s: %s",
                year,
                count,
                reason,
                sorted(names),
            )
            manifest.record_filtered(year, count, reason)
            df = df.filter(~mask)

    # Genesis force-drop: a RESOLVED district aggregate under the
    # distinguisher-erased truncated name is an arbitrarily-attributed
    # double-count of the bare school-name rows — drop at district level
    # regardless of the (arbitrary) code it bound to.
    force_names = {
        n
        for n in df.filter(pl.col("detail_level") == "district")["district_name_raw"]
        .unique()
        .to_list()
        if is_force_drop_district_agg(n)
    }
    if force_names:
        mask = (pl.col("detail_level") == "district") & pl.col(
            "district_name_raw"
        ).is_in(sorted(force_names))
        count = df.filter(mask).height
        if count:
            logger.info(
                "Year %d: dropping %d row(s) — force_drop_ambiguous_truncated_"
                "district_aggregate: %s",
                year,
                count,
                sorted(force_names),
            )
            manifest.record_filtered(
                year, count, "force_drop_ambiguous_truncated_district_aggregate"
            )
            df = df.filter(~mask)

    # School-level source gaps — keyed on the (district, school) name pair;
    # only rows the resolver could not bind (school_code NULL) are eligible.
    pair_key = pl.concat_str(
        pl.col("district_name_raw").str.to_lowercase().str.strip_chars(),
        pl.lit(_PAIR_SEP),
        pl.col("instn_name_raw").str.to_lowercase().str.strip_chars(),
    )
    candidates = df.filter(
        (pl.col("detail_level") == "school") & pl.col("school_code").is_null()
    )
    gap_pairs = {
        f"{d.lower().strip()}{_PAIR_SEP}{s.lower().strip()}"
        for d, s in candidates.select("district_name_raw", "instn_name_raw")
        .unique()
        .iter_rows()
        if is_source_gap_school(d, s)
    }
    if gap_pairs:
        mask = (
            (pl.col("detail_level") == "school")
            & pl.col("school_code").is_null()
            & pair_key.is_in(sorted(gap_pairs))
        )
        count = df.filter(mask).height
        if count:
            logger.info(
                "Year %d: dropping %d school row(s) — source_gap_school: %s",
                year,
                count,
                sorted(p.replace(_PAIR_SEP, " / ") for p in gap_pairs),
            )
            manifest.record_filtered(year, count, "source_gap_school")
            df = df.filter(~mask)

    return df


def _assert_fully_resolved(df: pl.DataFrame, year: int) -> None:
    """BLOCKING residual guard: any row still unresolved after the curated
    maps, the resolver chain, and the documented gap drops is a regression
    (a new bronze name pattern) — raise so it gets a pin/alias/gap entry
    instead of silently dropping data."""
    bad_district = df.filter(
        pl.col("district_code").is_null()
        & (pl.col("district_name_raw") != STATE_DISTRICT_SENTINEL)
    )
    if bad_district.height:
        offenders = (
            bad_district.group_by("district_name_raw")
            .len()
            .sort("len", descending=True)
            .head(20)
            .rows()
        )
        raise RuntimeError(
            f"Year {year}: {bad_district.height} row(s) with unresolved district "
            f"names not covered by any override or documented gap. Add a "
            f"MANUAL_DISTRICT_* entry or a SOURCE_GAP entry in "
            f"_educator_lookups.py. Offenders: {offenders}"
        )

    bad_school = df.filter(
        (pl.col("detail_level") == "school") & pl.col("school_code").is_null()
    )
    if bad_school.height:
        offenders = (
            bad_school.group_by("district_name_raw", "instn_name_raw")
            .len()
            .sort("len", descending=True)
            .head(20)
            .rows()
        )
        raise RuntimeError(
            f"Year {year}: {bad_school.height} school row(s) with unresolved "
            f"school names not covered by SCHOOL_NAME_ALIASES or "
            f"SOURCE_GAP_SCHOOLS. Offenders: {offenders}"
        )


# =============================================================================
# Per-file dispatch
# =============================================================================


def transform_file(
    path: Path,
    manifest: TransformManifest,
    resolver: EducatorNameResolver,
) -> pl.DataFrame | None:
    """Read one bronze CSV, transform, resolve codes, and apply drops."""
    # All-string read: TFS coexists with numerics until the era cast, and
    # name columns are never schema-inferred.
    df, loss = read_bronze_file(path, infer_schema_length=0, return_loss=True)

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{path.name}: no era signature matched {df.columns}")

    # The LONG_SCHOOL_YEAR column is the authoritative year (ending calendar
    # year); the filename matches it in every file but is only a cross-check.
    year = parse_school_year(df["LONG_SCHOOL_YEAR"].drop_nulls()[0])
    filename_year = extract_year_from_filename(path.name)
    if filename_year is not None and filename_year != year:
        logger.warning(
            "%s: filename year %d != LONG_SCHOOL_YEAR-derived %d — using the column",
            path.name,
            filename_year,
            year,
        )

    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])
    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)
    if df.height == 0:
        logger.warning("%s: bronze file is empty, skipping", path.name)
        return None

    label = f"{era} {path.name}"
    logger.info("Processing %s (year=%d, rows=%d)", label, year, df.height)

    result = _transform_era(df, year, era, manifest, label)
    result = _attach_codes(result, year, resolver)
    result = _drop_documented_gaps(result, year, manifest)
    _assert_fully_resolved(result, year)

    # Names live in the dimensions, not the fact table (§2).
    return result.drop("district_name_raw", "instn_name_raw").select(STANDARD_COLUMNS)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for this topic."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # Lookup tables load up front so a missing dimension fails before any
    # bronze processing. The year-aware build is cached process-wide. No
    # topic-specific district_name_expansions: the v1-era "atlanta city"
    # alias is obsolete (verified absent from every bronze year).
    resolver = EducatorNameResolver(
        dims=load_dimension_lookups(),
        year_aware=load_year_aware_lookups(),
    )

    # 1. Read + transform each bronze file (read-loss accounted per file).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR, extensions=[".csv"]):
        result = transform_file(path, manifest, resolver)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize dtypes across eras and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)
    logger.info("Combined %d rows across %d files", combined.height, len(all_dfs))

    # 3. Collision guard BEFORE dedup, run per detail level so uniformly-NULL
    # key columns never enter a NULL-vs-NULL join: duplicate natural keys
    # with divergent metrics mean an alias collapsed two coexisting entities
    # — raise so the alias is fixed, never let dedup pick a silent winner.
    for level, keys in (
        ("school", SCHOOL_KEYS),
        ("district", DISTRICT_KEYS),
        ("state", STATE_KEYS),
    ):
        assert_no_natural_key_collisions(
            combined.filter(pl.col("detail_level") == level),
            natural_keys=keys,
            metric_cols=METRIC_COLUMNS,
            label=f"{TOPIC} [{level}]",
        )
    # Tie-break: bronze keys are unique after the documented drops, so dedup
    # is purely defensive (the guard above ensures only identical-metric
    # duplicates can reach it). sort_col="inexperienced_fte" prefers a row
    # with a reported count over a suppressed placeholder on any future
    # republication.
    pre_dedup = dict(combined.group_by("year").len().iter_rows())
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=SCHOOL_KEYS,
        district_keys=DISTRICT_KEYS,
        state_keys=STATE_KEYS,
        sort_col="inexperienced_fte",
    )
    post_dedup = dict(combined.group_by("year").len().iter_rows())
    for year in sorted(pre_dedup):
        removed = pre_dedup[year] - post_dedup.get(year, 0)
        if removed > 0:
            manifest.record_filtered(year, removed, "duplicate_rows_deduped")

    # 4. Geography nulling — the resolution chain already leaves state rows
    # (NULL, NULL) and district rows school_code=NULL, but the shared rule
    # source keeps transform and validator in lockstep. No §4b masks apply
    # (verified: bronze percent within [0, 100] in every year; the six
    # +0.1-FTE numerator-rounding rows are preserved + documented, not
    # masked).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. The suppression-era split (true zeros pre-2021 vs
    # TFS-NULLs 2021+) legitimately shifts per-year NULL rates — surfaced as
    # a warning, documented in the contract.
    spikes = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spikes.status == "warning":
        logger.warning(
            "NULL-rate spikes (expected at the 2021 suppression boundary): %s",
            spikes.details,
        )
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
    """Emit the ODCS contract + README. Column order == STANDARD_COLUMNS
    minus detail_level."""
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Georgia Office of Student Achievement (GOSA) Inexperienced "
            "Teachers and Leaders report. For every Georgia public school, "
            "school district, and the state as a whole, reports the total "
            "educator full-time equivalent (`total_fte`), the FTE of "
            "educators classified as Inexperienced — within the first years "
            "of their career, per the ESSA inexperienced-educator standard — "
            "(`inexperienced_fte`), and the inexperienced FTE as a "
            "percentage of total FTE (`inexperienced_fte_rate`, on a 0-1 "
            "decimal scale). Unlike the sibling educator-qualifications "
            "topics (Teachers-only), this dataset reports both Teachers and "
            "Leaders (`role`), and each entity carries rows across school-"
            "poverty strata (`poverty_subgroup`: total, high_poverty, "
            "low_poverty, plus not_applicable and unknown for Leaders). "
            "Coverage spans the 2017-2018 school year through 2023-2024."
        ),
        title="Inexperienced Teachers and Leaders",
        summary=(
            "Share of Georgia teachers and leaders in their first career "
            "years by school, district, role, and poverty stratum, "
            "2018-2024."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Ending calendar year of the school year. Year 2024 = "
                    "2023-2024 school year. Derived from the bronze "
                    "`LONG_SCHOOL_YEAR` column's ending year."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "nullable": True,
                "example": "601",
                "description": (
                    "3-digit GOSA district code (zero-padded) for standard "
                    "districts; 7-digit charter code for charter / "
                    "specialty-school districts; NULL for state-level "
                    "aggregate rows. FK to the education districts "
                    "dimension. Because the source publishes only district "
                    "NAMES (no codes), codes are resolved against "
                    "`data/gold/education/_dimensions/districts.parquet` via "
                    "the shared educator-topic resolver (year-aware "
                    "certified_personnel lookups, curated code pins, and "
                    "guarded name matching — see "
                    "src/etl/education/gosa/_educator_lookups.py). Rows "
                    "whose names cannot be resolved or faithfully attributed "
                    "are dropped only under documented predicates; the "
                    "transform manifest records each dropped class and count "
                    "per year."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "nullable": True,
                "example": "0103",
                "description": (
                    "4-digit GOSA school code (zero-padded); NULL for "
                    "district-level and state-level aggregate rows. FK to "
                    "the education schools dimension (composite key with "
                    "district_code). Resolved by name via the shared "
                    "educator-topic resolver; school-level rows whose name "
                    "cannot be resolved to a dimension entry are dropped "
                    "under documented source-gap predicates only (counts in "
                    "the transform manifest)."
                ),
            },
            {
                "name": "role",
                "type": "string",
                "nullable": False,
                "example": "teachers",
                "validValues": sorted(ROLE_MAP.values()),
                "short_description": (
                    "Workforce role the row measures: teachers or leaders "
                    "(principals and assistant principals)."
                ),
                "description": (
                    "Workforce role the row measures: `teachers` or "
                    "`leaders` (principals / assistant principals). Unlike "
                    "the sibling emergency / out-of-field educator-"
                    "qualifications topics (Teachers-only), this dataset "
                    "reports both roles."
                ),
            },
            {
                "name": "poverty_subgroup",
                "type": "string",
                "nullable": False,
                "example": "total",
                "validValues": sorted(POVERTY_SUBGROUP_MAP.values()),
                "short_description": (
                    "School-poverty stratum the row covers (total, high, or "
                    "low poverty; Leaders add not_applicable/unknown); a "
                    "school-poverty level, not a student demographic."
                ),
                "description": (
                    "Poverty stratum of the schools whose FTE this row "
                    "aggregates. `total` covers all schools in the entity; "
                    "`high_poverty` / `low_poverty` cover only the entity's "
                    "schools in the state's highest- / lowest-poverty "
                    "quartile (per GOSA's K-12 Teacher & Leader Workforce "
                    "Reports, school poverty is defined by the direct-"
                    "certification rate). Leaders rows additionally carry "
                    "`not_applicable` (the dominant Leaders stratum) and "
                    "`unknown` (rare — chiefly Department of Juvenile "
                    "Justice facilities, plus isolated Mitchell County 2022 "
                    "and Gwinnett County 2024 rows); Teachers rows never "
                    "carry either (enforced by a quality check). For a "
                    "school-level row the stratum describes the school "
                    "itself, so a stratum row duplicates that school's "
                    "`total` row (enforced by a quality check). This is a "
                    "SCHOOL-poverty stratum, NOT a student demographic — it "
                    "does not map to the global demographics dimension."
                ),
            },
            {
                "name": "total_fte",
                "metric_component": "denominator",
                "type": "float64",
                "unit": "count",
                "example": 65.5,
                "null_meaning": (
                    "Suppressed by the GOSA reporting floor (`TFS`, fewer "
                    "than 10 FTE); suppression exists from the 2021 file "
                    "onward. Pre-2021 files have no suppression."
                ),
                "description": (
                    "Total educator full-time equivalent count in the "
                    "entity for the given role and poverty subgroup. For "
                    "`poverty_subgroup = total` this is the entity's total "
                    "role FTE; for other strata it is the FTE in just that "
                    "stratum of schools. Fractional FTEs are real (e.g. "
                    "58.2). NULL when suppressed by the GOSA reporting "
                    "floor (`TFS`, < 10 FTE) — 2021 onward. Denominator of "
                    "`inexperienced_fte_rate`."
                ),
            },
            {
                "name": "inexperienced_fte",
                "metric_component": "numerator",
                "type": "float64",
                "unit": "count",
                "example": 33.0,
                "null_meaning": (
                    "Suppressed (`TFS`, < 10 FTE) — 2021 onward. Pre-2021 "
                    "files have no suppression, so NULL does not occur and "
                    "0.0 is a true zero."
                ),
                "description": (
                    "Educator FTE classified as Inexperienced (within the "
                    "first years of their career, per the ESSA "
                    "inexperienced-educator standard) in the entity for the "
                    "given role and poverty subgroup. NULL when suppressed "
                    "(`TFS`, < 10 FTE) — observed from 2021 onward. True "
                    "zeros (no inexperienced educators) are preserved as "
                    "0.0 in 2018-2020, before GOSA introduced suppression "
                    "for this report. Numerator of `inexperienced_fte_rate`. "
                    "WARNING — not additive across hierarchy levels for "
                    "Teachers: school-row sums exceed the district row and "
                    "district-row sums exceed the state row by ~1.4x in "
                    "every year (bronze-native; consistent with experience "
                    "measured relative to the reporting unit — new-to-school "
                    "vs new-to-district vs new-to-profession). Never derive "
                    "an aggregate by summing lower-level rows; use the "
                    "published row for the level you need. Leaders rows and "
                    "`total_fte` DO reconcile across levels (~1.000). "
                    "Six 2018-2020 Leaders rows at tiny programs exceed "
                    "`total_fte` by exactly 0.1 (e.g. 2.0 vs 1.9 at "
                    "Randolph Clay High School 2018) — an artifact of GOSA "
                    "rounding each FTE to 0.1 independently; preserved per "
                    "data-cleaning-standards §4b (extreme-but-conceivable)."
                ),
            },
            {
                "name": "inexperienced_fte_rate",
                "key_metric": True,
                "type": "float64",
                "unit": "proportion",
                "example": 0.5,
                "null_meaning": (
                    "The bronze percentage itself was suppressed (`TFS`). "
                    "The rate can be non-NULL while `inexperienced_fte` is "
                    "suppressed, and vice versa — GOSA suppresses each cell "
                    "independently."
                ),
                "short_description": (
                    "Share of educator FTE classified as inexperienced, on "
                    "a 0-1 scale (inexperienced_fte / total_fte)."
                ),
                "description": (
                    "`inexperienced_fte` / `total_fte` on a 0-1 decimal "
                    "scale. Bronze publishes an integer 0-100 percent "
                    "(verified range 0-100 across all years); divided by "
                    "100 per data-cleaning-standards §4. GOSA computes the "
                    "integer percent from UNROUNDED FTE values while "
                    "publishing FTEs rounded to 0.1, so at small programs "
                    "the published rate deviates from "
                    "inexperienced_fte/total_fte (up to 0.9 below 10 FTE, "
                    "e.g. published 0.1/0.1 with rate 0.10; at or above the "
                    "10-FTE reporting floor the worst observed deviation is "
                    "0.09). A quality check enforces reconciliation within "
                    "0.10 where total_fte >= 10. The rate is preserved from "
                    "bronze even when `inexperienced_fte` is suppressed."
                ),
            },
        ],
        source="Governor's Office of Student Achievement (GOSA)",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        limitations=(
            "Suppression is era-asymmetric: 2018-2020 publish a real `0` "
            "(true zero inexperienced educators, 723-765 rows per year), "
            "while 2021 onward suppress any value below 10 with `TFS` "
            "(treat NULL as 'value < 10' for 2021+ but as genuinely missing "
            "pre-2021); inexperienced_fte_rate may be non-null even when "
            "inexperienced_fte is suppressed. The source publishes only "
            "district/school NAMES, so codes are resolved by name against "
            "the education dimensions via the shared educator-topic "
            "resolver (year-aware certified_personnel lookups, curated code "
            "pins, guarded matching); rows that cannot be resolved or "
            "faithfully attributed are dropped only under documented "
            "predicates — unresolved truncated charter-container "
            "placeholders, cataloged source gaps (e.g. Ivy Prep Kirkwood), "
            "and the ambiguous 52-char-truncated Genesis Innovation Academy "
            "district aggregates (Boys/Girls distinguisher erased; bare "
            "school rows carry the real values) — with per-year counts in "
            "the transform manifest. District-level coverage for Genesis "
            "Innovation Academy is therefore missing in 2023-2024 while its "
            "school-level rows are complete. The 2024 truncated Utopian "
            "Academy aggregates (one Leaders/Total identical-metric pair "
            "collapsed by dedup, plus a single Leaders/Low Poverty row) are "
            "all bound to the pinned main campus 7820121 even though the "
            "truncated name also covers the Trilith campus 7820619 — the "
            "Low Poverty row likely describes Trilith; preserved as "
            "published and matching the v1-approved handling. "
            "Six 2018-2020 Leaders rows carry inexperienced_fte "
            "exceeding total_fte by exactly 0.1 (independent 0.1-FTE "
            "rounding; preserved per data-cleaning-standards §4b). "
            "Teachers `inexperienced_fte` does NOT aggregate across "
            "hierarchy levels: school-row sums exceed the district row and "
            "district-row sums exceed the state row by ~1.4x in every year "
            "(consistent with experience measured relative to the reporting "
            "unit); never derive aggregates by summing lower-level rows. "
            "The 2019 file's Teachers FTE levels run ~40%% above adjacent "
            "years statewide (162,256.2 vs 118,009.1 in 2018 / 110,800.8 "
            "in 2020) and the 2018 file's school-level total_fte can sum "
            "above the district row (149 of 205 districts) — treat "
            "2018-2019 levels as a distinct measurement basis when "
            "trending. State rows have NULL district_code and school_code; "
            "district rows have NULL school_code."
        ),
        notes=[
            (
                "Three detail levels are present in every year (schools, "
                "districts, state). Split by filename per year partition: "
                "schools.parquet, districts.parquet, states.parquet. "
                "Aggregate rows have NULL geography keys."
            ),
            (
                "The bronze source publishes only district and school NAMES, "
                "not codes. Codes are resolved via the shared educator-topic "
                "resolver in src/etl/education/gosa/_educator_lookups.py: "
                "year-aware certified_personnel (name -> code) lookups first "
                "(faithful at each year's name boundary), then curated "
                "district-code pins / aliases, then guarded mechanical "
                "matching against the dimensions. Unresolvable rows are "
                "dropped only under documented predicates; every drop is "
                "recorded per year in _transform_manifest.json "
                "(filtered_explicit_by_reason)."
            ),
            (
                "2023-2024 truncation repair: GOSA truncates INSTN_NAME at "
                "exactly 52 characters and truncates charter-container "
                "district labels to generic placeholders ('State Charter "
                "Schools '/'-'). District-aggregate rows whose '- All "
                "Schools' suffix was cut (fully or partially) are repaired "
                "in place — the entity name is recovered from INSTN_NAME "
                "and the row is reclassified as a district aggregate "
                "(recorded as reclassified_events in the manifest). The "
                "ambiguous truncation that erases the Genesis Innovation "
                "Academy Boys/Girls distinguisher is dropped instead — the "
                "school-level rows carry the faithful per-campus values. "
                "The 2024 Utopian Academy truncation covers two campuses "
                "(main 7820121 + Trilith 7820619) whose Leaders/Total "
                "aggregates are identical and collapse to one row via "
                "dedup, bound to the pinned 7820121."
            ),
            (
                "Unlike the sibling educator_qualifications topics "
                "(Teachers-only), this dataset reports both Teachers and "
                "Leaders. Row counts are ~70%% larger than the siblings' "
                "because of the Leaders rows."
            ),
            (
                "poverty_subgroup is a SCHOOL-poverty stratum (total / "
                "high_poverty / low_poverty / not_applicable / unknown), "
                "NOT a student demographic; the topic has no demographic "
                "column. not_applicable and unknown appear on Leaders rows "
                "only — `unknown` is chiefly Department of Juvenile Justice "
                "facilities, plus isolated Mitchell County 2022 and "
                "Gwinnett County 2024 rows. For school-level rows the "
                "stratum row duplicates the school's total row (a school IS "
                "its stratum) — enforced by quality checks; district/state "
                "stratum rows cover only the schools in that stratum "
                "(membership scoping — NOT arithmetic additivity; see the "
                "inexperienced-FTE non-additivity note)."
            ),
            (
                "Teachers `inexperienced_fte` is NOT additive across "
                "hierarchy levels — bronze-native, in every year: school-row "
                "sums exceed the district row, and district-row sums exceed "
                "the state row by 1.38-1.49x (e.g. 2020: state 25,767 vs "
                "district sum 37,747.1 vs school sum 47,470.7, while "
                "total_fte reconciles to within ±6 FTE at all levels). "
                "Consistent with GOSA measuring experience relative to the "
                "reporting unit (new-to-school vs new-to-district vs "
                "new-to-profession), though GOSA does not document the "
                "computation. Leaders rows reconcile (~1.000-1.002 "
                "pre-suppression). Never derive an aggregate by summing "
                "lower-level rows; a hierarchy-additivity quality check is "
                "deliberately NOT authored because the data does not "
                "satisfy one."
            ),
            (
                "2018-2019 source-era level anomalies, preserved as "
                "published per §4b: the 2019 file's statewide Teachers "
                "Total FTE (162,256.2) runs ~40%% above 2018 (118,009.1) "
                "and 2020 (110,800.8) — broad-based across districts, "
                "suggesting a wider certificated-staff basis that year; and "
                "in the 2018 file 149 of 205 districts have school-level "
                "total_fte summing above the district row (e.g. Bibb County "
                "611: district 1,718.0 vs school sum 2,342.9), an "
                "early-era multi-school-assignment double-count at school "
                "level that drops to <=9 districts/year afterwards. Treat "
                "2018-2019 levels as a distinct measurement basis when "
                "trending."
            ),
            (
                "Suppression is era-asymmetric: 2018-2020 publish true "
                "zeros with no suppression; 2021+ mask values below 10 "
                "with TFS (NULL in gold). Treat NULL as 'value < 10' for "
                "2021+ but as genuinely missing pre-2021. The per-year "
                "NULL-rate shift at the 2021 boundary is expected and "
                "documented."
            ),
            (
                "Schema eras: Era 1 (2023-2024) encodes the qualification "
                "category in a #CATEGORY_DESC row dimension (verified "
                "constant 'Inexperienced') with CATEGORY_FTE / "
                "CATEGORY_FTE_PCT metric columns; Era 2 (2018-2022) encodes "
                "it in the column names (INEXPERIENCED_FTE / "
                "INEXPERIENCED_FTE_PCT). Gold harmonizes both to "
                "inexperienced_fte / inexperienced_fte_rate."
            ),
        ],
        quality_checks=[
            {
                "name": "inexperienced_fte_within_total_fte",
                "description": (
                    "The inexperienced FTE count never exceeds the total "
                    "FTE it is drawn from, beyond GOSA's independent "
                    "0.1-FTE rounding. Six bronze rows (2018-2020 Leaders "
                    "at tiny programs) exceed by exactly 0.1; the 0.15 "
                    "tolerance covers that rounding artifact while still "
                    "catching any real numerator/denominator inversion."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE inexperienced_fte IS NOT NULL "
                    "AND total_fte IS NOT NULL "
                    "AND inexperienced_fte > total_fte + 0.15"
                ),
                "mustBe": 0,
            },
            {
                "name": "inexperienced_fte_rate_reconciles_with_components",
                "description": (
                    "inexperienced_fte_rate reconciles with "
                    "inexperienced_fte / total_fte within 0.10 on the 0-1 "
                    "scale, scoped to total_fte >= 10 (the GOSA reporting "
                    "floor). GOSA computes the integer percent from "
                    "unrounded FTE values while publishing FTEs rounded to "
                    "0.1, so below 10 FTE the published components are too "
                    "coarse for reconciliation (observed deviation up to "
                    "0.9 at 0.1-FTE programs); at or above the floor the "
                    "worst observed deviation is 0.09."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE total_fte IS NOT NULL AND total_fte >= 10 "
                    "AND inexperienced_fte IS NOT NULL "
                    "AND inexperienced_fte_rate IS NOT NULL "
                    "AND ABS(inexperienced_fte / total_fte - "
                    "inexperienced_fte_rate) > 0.10"
                ),
                "mustBe": 0,
            },
            {
                "name": "school_poverty_stratum_mirrors_total",
                "description": (
                    "A school-level stratum row (high_poverty, low_poverty, "
                    "not_applicable, or unknown) duplicates the same "
                    "school's total row for the same role — a school IS its "
                    "poverty stratum; the stratum rows are republications, "
                    "not sub-populations. Checked on both FTE metrics with "
                    "a 0.001 float tolerance; verified exact in bronze for "
                    "every year on all three metrics."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, school_code, role, "
                    "MAX(CASE WHEN poverty_subgroup = 'total' THEN total_fte "
                    "END) AS t_tot, "
                    "MAX(CASE WHEN poverty_subgroup <> 'total' THEN total_fte "
                    "END) AS s_tot, "
                    "MAX(CASE WHEN poverty_subgroup = 'total' THEN "
                    "inexperienced_fte END) AS t_inx, "
                    "MAX(CASE WHEN poverty_subgroup <> 'total' THEN "
                    "inexperienced_fte END) AS s_inx "
                    "FROM {object} WHERE school_code IS NOT NULL "
                    "GROUP BY year, district_code, school_code, role"
                    ") WHERE (t_tot IS NOT NULL AND s_tot IS NOT NULL AND "
                    "ABS(s_tot - t_tot) > 0.001) "
                    "OR (t_inx IS NOT NULL AND s_inx IS NOT NULL AND "
                    "ABS(s_inx - t_inx) > 0.001)"
                ),
                "mustBe": 0,
            },
            {
                "name": "school_role_single_poverty_stratum",
                "description": (
                    "The poverty strata are disjoint, so a school carries "
                    "at most ONE non-total stratum row per role per year "
                    "(its own stratum). Verified across all bronze years: "
                    "no school-role group ever carries two distinct "
                    "non-total strata."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, school_code, role "
                    "FROM {object} WHERE school_code IS NOT NULL "
                    "AND poverty_subgroup <> 'total' "
                    "GROUP BY year, district_code, school_code, role "
                    "HAVING COUNT(DISTINCT poverty_subgroup) > 1"
                    ") AS bad"
                ),
                "mustBe": 0,
            },
            {
                "name": "teachers_never_not_applicable_or_unknown",
                "description": (
                    "Structural fact: the not_applicable and unknown "
                    "poverty strata exist only for the Leaders workforce — "
                    "zero Teachers rows carry them in any bronze year."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE role = 'teachers' "
                    "AND poverty_subgroup IN ('not_applicable', 'unknown')"
                ),
                "mustBe": 0,
            },
            {
                "name": "aggregate_poverty_strata_within_total",
                "description": (
                    "At district and state level the high-poverty and "
                    "low-poverty strata are disjoint subsets of the "
                    "entity's role workforce, so high_poverty + low_poverty "
                    "<= total + 0.55 when all three are reported. The 0.55 "
                    "tolerance covers GOSA's 0.1-FTE rounding (observed "
                    "worst excess: 0.5 at Greene County Leaders 2020)."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, role, "
                    "MAX(CASE WHEN poverty_subgroup = 'total' THEN total_fte "
                    "END) AS t, "
                    "MAX(CASE WHEN poverty_subgroup = 'high_poverty' THEN "
                    "total_fte END) AS hp, "
                    "MAX(CASE WHEN poverty_subgroup = 'low_poverty' THEN "
                    "total_fte END) AS lp "
                    "FROM {object} WHERE school_code IS NULL "
                    "GROUP BY year, district_code, role"
                    ") WHERE t IS NOT NULL AND hp IS NOT NULL AND lp IS NOT "
                    "NULL AND hp + lp > t + 0.55"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_rows_exactly_six_per_year",
                "description": (
                    "Structural fact: every year carries exactly six "
                    "state-level rows (district_code IS NULL) — 2 roles x "
                    "3 poverty strata (total, high_poverty, low_poverty; "
                    "not_applicable/unknown never appear at state level)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year FROM {object} WHERE district_code IS NULL "
                    "GROUP BY year "
                    "HAVING COUNT(*) <> 6 "
                    "OR COUNT(DISTINCT role || '/' || poverty_subgroup) <> 6 "
                    "OR SUM(CASE WHEN poverty_subgroup NOT IN "
                    "('total', 'high_poverty', 'low_poverty') "
                    "THEN 1 ELSE 0 END) > 0"
                    ") AS bad"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
