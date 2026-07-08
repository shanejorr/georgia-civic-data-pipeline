"""Transform educator_qualifications_out_of_field_teachers to gold.

Source: Governor's Office of Student Achievement (GOSA) — Out-of-Field
teacher FTE report, school years 2017-18 through 2023-24 (7 CSV files, one
per year). For every Georgia public school, school district, and the state,
the source publishes total teacher FTE, the FTE of teachers assigned to a
subject for which they are not certified ("out of field"), and that count
as an integer percentage of total FTE. Each entity carries three
poverty-stratum rows: Total, High Poverty, and Low Poverty.

Design decisions (from bronze-data-structure.md + data-cleaning-standards):

- **Two column-name eras, one tidy shape, detected by column signature.**
  Era 1 (2023-2024): `#CATEGORY_DESC` (constant `Out_of_Field`) +
  `CATEGORY_FTE` / `CATEGORY_FTE_PCT`. Era 2 (2018-2022): `OUTOFFIELD_FTE`
  / `OUTOFFIELD_FTE_PCT`. In THIS topic the `OUTOFFIELD_*` headers carry
  GENUINE out-of-field values in every year (2021 state total: 6,281.9).
  Do NOT confuse them with the sibling emergency-credentials topic, whose
  2018-2021 bronze re-uses the same `OUTOFFIELD_*` header names for
  Emergency-credential values (its 2021 state total is 9,796.9) — never
  "reconcile" this topic against those same-named columns.
- **`#CATEGORY_DESC` and `LABEL_LVL_3_DESC` are verified constants**
  (`Out_of_Field`, `Teachers`) and dropped; the era function raises if the
  source ever adds another category or workforce role.
- **`LABEL_LVL_2_DESC` -> `poverty_subgroup`** (`total` / `high_poverty` /
  `low_poverty`): a SCHOOL-poverty stratum, not a student demographic — it
  deliberately does not map to the global demographics dimension and the
  topic has no `demographic` column.
- **Name-to-code resolution is the core difficulty**: bronze publishes only
  district/school NAMES. Codes are resolved via the shared
  `src/etl/education/gosa/_educator_lookups.py` resolver — year-aware
  certified_personnel lookups first, then curated pins/aliases, then the
  guarded mechanical dimension matches. Rows that remain unresolvable are
  dropped ONLY when covered by a documented predicate (placeholder charter
  containers, SOURCE_GAP entries); anything else unresolved RAISES, so new
  bronze name patterns can never silently drop data. Every drop is logged
  and manifest-recorded via record_filtered. This topic does NOT wire in
  `is_force_drop_district_agg` — that predicate exists solely for the
  inexperienced topic's hybrid-rescue path and would change this gold.
- **Dropped-row classes** (all manifest-recorded per year):
  * `state_charter_placeholder_district` — 2023 generic truncated charter
    container labels ("State Charter Schools "/"-") whose school name could
    not be independently rescued. These are redundant district-aggregate
    republications of the bare school-name rows already in gold (every
    state-charter district except 7991895 has exactly one school), so
    dropping prevents double-counting — deliberate, not data loss. This
    class also covers the 2023 truncated twin rows "State Charter Schools
    II- Genesis Innovation Academy" (Boys/Girls distinguisher erased at 52
    chars; two same-named bronze rows with divergent metrics that no
    single dim entity can faithfully receive). The drop is LOSSLESS: the
    2023 file separately publishes both campuses under their bare school
    names with the same metrics (7830615/0615 = 31.1/20.3/0.65;
    7830616/0616 = 29.6/23.3/0.79), and both bare-name rows are in gold —
    only the truncated-to-campus attribution is ambiguous, so the
    redundant truncated pair is dropped.
  * `source_gap_district` / `source_gap_school` — documented entities with
    no single faithful dimension target (K-8/K-12 combined campuses the dim
    splits, closed schools, pre-merge sibling pairs, Ivy Prep Kirkwood,
    etc.). Fidelity over coverage: binding to the nearest-named dim row
    would mis-attribute facts.
- **Suppression begins in 2022, not 2021.** 2018-2021 files contain ZERO
  `TFS` markers in any column (verified by direct count; the structure
  doc's "TFS begins appearing in FTE in 2021-2022" was amended — 2021 has
  none). From 2022 onward `TFS` masks values below 10 (~88%% of
  school-level out-of-field counts). Consumers should read NULL as "< 10"
  for 2022+ but as genuinely missing pre-2022 (where it does not occur).
- **2018-2021 `out_of_field_fte = 0` zero-spike (known anomaly,
  preserved).** Pre-suppression files carry implausibly high
  concentrations of literal 0 in the out-of-field count (2018: 98
  school-level zeros, 2.9%%; 2019: 111; 2020: 1,645 — 48%% of school rows;
  2021: 616). The 2020 rate is almost certainly an undocumented
  suppression-as-zero encoding, but it cannot be mechanically separated
  from true zeros, so every bronze 0 passes through as 0.0 per bronze
  fidelity. Documented in the contract; downstream analysts must handle
  2018-2021 zeros explicitly.
- **`out_of_field_fte_rate` is a bounded proportion (§4a).** Bronze
  publishes an integer 0-100 percent (verified min 0 / max 100 across all
  years); divided by 100. No §4b masks apply: no impossible values exist
  in any year.
- **Tiny-FTE rate deviations (preserved, check scoped).** In 2018-2021, 26
  rows at micro programs with total_fte < 3 publish an integer percent
  that deviates from out_of_field_fte/total_fte by up to 0.57 (e.g. Evans
  County "Second Chance" 2020: 1.0/1.0 published as 50%%) — GOSA evidently
  computed the percent from unrounded FTE values where the 0.1-FTE
  rounding dominates at this scale. The published rate is
  extreme-but-conceivable, not impossible, so it is preserved (§4b); the
  reconciliation quality check is scoped to total_fte >= 3, where the
  worst observed deviation across all years is 0.0124.
- **Scope anomalies in the FTE denominator (preserved + documented).** The
  2019 file reports a ~37%% broader teacher population at EVERY detail
  level (state total_fte 162,256.2 vs 118,009.1 in 2018 / 110,800.8 in
  2020). The 2018 file mixes scopes ACROSS levels: school rows are on the
  broad scope (statewide school-row sum 157,557.3) while district/state
  rows are narrow (state row 118,009.1) — 2018 school rows do NOT sum to
  their district or state aggregates. Same pattern as the sibling
  emergency topic (shared FTE denominator); preserved per §4b.
- **Dedup collapses 2023 charter republications.** The bronze name key is
  unique within each year file except one truncated 2023 twin (dropped as
  a placeholder, see above), but the 2023 file publishes several
  single-school state-charter entities TWICE: once under the specific
  container district label and once under the generic placeholder
  container (bare school name and/or 52-char-truncated "...- All Sc"
  aggregate form). After resolution both publications bind to the same
  (year, district_code, school_code, poverty_subgroup) key with IDENTICAL
  metrics, and dedup collapses them (recorded via record_filtered). The
  collision guard runs first, so only identical-metric duplicates can ever
  be collapsed. Tie-break `sort_col="out_of_field_fte"` (v1-consistent)
  prefers a row with a reported count over a suppressed placeholder on any
  future republication.
- **Quality checks (§15b)**, all verified against bronze across all 7
  years: numerator within denominator (`out_of_field_fte <= total_fte`;
  0 violations); rate reconciliation at total_fte >= 3 (|oof/total − rate|
  <= 0.015; observed max 0.0124); school-level strata rows mirror the
  school's Total row (a school IS its stratum; verified on all three
  metrics, 0.001 tolerance); no school in both strata; district/state
  HP+LP within Total + 0.25 (observed max excess 0.1 — FTE rounding at
  Greene 2021/2022 and Richmond 2021, same rows as the emergency sibling);
  exactly 3 state rows per year.

Judgment calls (non-interactive run):

1. The 2023 Genesis Boys/Girls truncated twin rows are dropped under the
   placeholder predicate rather than arbitrarily attributed: the 52-char
   truncation erased the campus distinguisher and the two bronze rows
   carry divergent metrics (31.1/20.3/0.65 vs 29.6/23.3/0.79), so any
   single-target bind would mis-attribute one campus's facts.
2. Rate-reconciliation check scoped to total_fte >= 3 (not a global 0.57
   tolerance): a tolerance that admits the tiny-FTE outliers would be
   decorative for the other 16,777 rows; the scope keeps the check sharp
   where the data supports it, and the excluded rows are documented.
3. Unresolvable-name drops kept exactly at the v1-verified predicate set
   (placeholder containers + SOURCE_GAP entries) rather than widening any
   mechanical match rule — fidelity over coverage.
4. `poverty_subgroup` kept as a topic categorical (not `demographic`): the
   strata describe the school's poverty quartile membership, not student
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

TOPIC = "educator_qualifications_out_of_field_teachers"
BRONZE_DIR = Path(
    "data/bronze/education/gosa/educator_qualifications_out_of_field_teachers"
)
GOLD_DIR = Path("data/gold/education/educator_qualifications_out_of_field_teachers")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# `LABEL_LVL_2_DESC` -> poverty_subgroup (snake_case per §10). A poverty
# stratum of schools, NOT a student demographic (see module docstring).
POVERTY_SUBGROUP_MAP: dict[str, str] = {
    "Total": "total",
    "High Poverty": "high_poverty",
    "Low Poverty": "low_poverty",
}

# Era-detection signatures (column presence), most specific first: Era 1's
# `#CATEGORY_DESC` is unique to it; Era 2 carries the OUTOFFIELD_* metric
# pair (genuine out-of-field values in this topic — see module docstring).
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
    "era_2_2018_2022_outoffield_named": [
        "LONG_SCHOOL_YEAR",
        "SCHOOL_DSTRCT_NM",
        "INSTN_NAME",
        "LABEL_LVL_3_DESC",
        "LABEL_LVL_2_DESC",
        "FTE",
        "OUTOFFIELD_FTE",
        "OUTOFFIELD_FTE_PCT",
    ],
}

# Bronze metric source columns per era (total_fte source is `FTE` in both).
ERA_METRIC_COLUMNS: dict[str, tuple[str, str]] = {
    "era_1_2023_2024_category_desc": ("CATEGORY_FTE", "CATEGORY_FTE_PCT"),
    "era_2_2018_2022_outoffield_named": ("OUTOFFIELD_FTE", "OUTOFFIELD_FTE_PCT"),
}

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export splitting, then dropped by export_to_parquet().
# No `demographic` column — poverty_subgroup is a school-poverty stratum.
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "poverty_subgroup",
    "total_fte",
    "out_of_field_fte",
    "out_of_field_fte_rate",
    "detail_level",
]

# All three metrics are Float64: FTEs are fractional (e.g. 42.5) and the
# rate lives on the 0-1 decimal scale.
TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "poverty_subgroup": pl.Utf8,
    "total_fte": pl.Float64,
    "out_of_field_fte": pl.Float64,
    "out_of_field_fte_rate": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = [
    "total_fte",
    "out_of_field_fte",
    "out_of_field_fte_rate",
]

NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "poverty_subgroup",
    "detail_level",
]

# Separator for (district_name, school_name) pair-membership masks; never
# appears in GOSA name cells.
_PAIR_SEP = "\x1f"


# =============================================================================
# Era transform
# =============================================================================


def _assert_constant_column(
    df: pl.DataFrame, column: str, expected: str, label: str
) -> None:
    """Raise if a verified-constant bronze column carries any other value.

    A new value (e.g. a second #CATEGORY_DESC category) means the pipeline
    needs a schema decision, not silent passthrough.
    """
    observed = set(df[column].unique().to_list())
    if observed - {expected}:
        raise ValueError(
            f"{label}: expected {column} == {expected!r} only, saw {sorted(observed)}"
        )


def _transform_era(
    df: pl.DataFrame,
    year: int,
    era: str,
    manifest: TransformManifest,
    label: str,
) -> pl.DataFrame:
    """Transform one bronze file (either era) to the pre-resolution gold shape.

    Verifies the era's constant columns, derives detail_level from the name
    sentinels, recodes the poverty stratum, and casts the metric trio. The
    raw name columns are retained for the resolution step in
    transform_file().
    """
    fte_col, pct_col = ERA_METRIC_COLUMNS[era]
    # Rename-coverage guard: a missing metric column would silently NULL the
    # whole year (the classic rename bug) — fail loudly instead.
    missing = [c for c in ("FTE", fte_col, pct_col) if c not in df.columns]
    if missing:
        raise ValueError(f"{label}: expected metric columns missing: {missing}")

    # Era 1 encodes the report category as a row dimension — verify it is
    # the constant `Out_of_Field` before dropping it.
    if era == "era_1_2023_2024_category_desc":
        _assert_constant_column(df, "#CATEGORY_DESC", "Out_of_Field", label)
    # Workforce role is constant `Teachers` in both eras.
    _assert_constant_column(df, "LABEL_LVL_3_DESC", "Teachers", label)

    # One batched with_columns: (a) detail level from the name sentinels —
    # state rows pair the two state sentinels; district aggregates end with
    # "- All Schools" (regular hyphen + space, prefix == SCHOOL_DSTRCT_NM);
    # everything else is a school row; (b) poverty stratum recode — the
    # sentinel default surfaces any future new stratum as an unmapped value,
    # failing manifest.write().
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
        pl.col("LABEL_LVL_2_DESC")
        .replace_strict(POVERTY_SUBGROUP_MAP, default="99999999")
        .alias("poverty_subgroup"),
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
        pl.col("poverty_subgroup"),
        # All-string read: TFS already became NULL via the reader's
        # suppression list; strict=False catches any stray non-numeric.
        # True zeros (and the 2018-2021 suppression-as-zero anomaly)
        # survive the cast — see module docstring.
        pl.col("FTE").cast(pl.Float64, strict=False).alias("total_fte"),
        pl.col(fte_col).cast(pl.Float64, strict=False).alias("out_of_field_fte"),
        # Bronze publishes an integer 0-100 percent (verified across all
        # years); divide by 100 onto the 0-1 scale per §4.
        (pl.col(pct_col).cast(pl.Float64, strict=False) / 100.0).alias(
            "out_of_field_fte_rate"
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
    same result as per-row resolution, ~3x fewer resolver calls.
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
    """Drop the documented unresolvable rows, recording each class.

    Three classes (see module docstring + _educator_lookups rationale):
    placeholder charter containers, district-level source gaps, and
    school-level source gaps. Each predicate fires only on rows the
    resolver left unresolved, so a future rescue (new pin/alias) takes
    precedence automatically. is_force_drop_district_agg is deliberately
    NOT applied here (inexperienced-topic-only — see module docstring).
    """
    # Placeholder charter containers — redundant aggregate republications.
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
    # name columns are never schema-inferred (leading zeros, sentinels).
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
    # bronze processing. The year-aware build is cached process-wide.
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

    # 3. Collision guard BEFORE dedup: duplicate natural keys with divergent
    # metrics mean an alias collapsed two coexisting entities — raise so the
    # alias is fixed, never let dedup pick a silent winner.
    assert_no_natural_key_collisions(
        combined,
        natural_keys=NATURAL_KEYS,
        metric_cols=METRIC_COLUMNS,
        label=TOPIC,
    )
    # Tie-break: bronze keys are unique after the documented drops except
    # the 2023 charter republications (identical metrics). sort_col=
    # "out_of_field_fte" (v1-consistent) prefers a row with a reported
    # count over a suppressed placeholder on any future republication.
    pre_dedup = dict(combined.group_by("year").len().iter_rows())
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code", "poverty_subgroup"],
        district_keys=["year", "district_code", "poverty_subgroup"],
        state_keys=["year", "poverty_subgroup"],
        sort_col="out_of_field_fte",
    )
    post_dedup = dict(combined.group_by("year").len().iter_rows())
    for year in sorted(pre_dedup):
        removed = pre_dedup[year] - post_dedup.get(year, 0)
        if removed > 0:
            manifest.record_filtered(year, removed, "duplicate_rows_deduped")

    # 4. Geography nulling — the resolution chain already leaves state rows
    # (NULL, NULL) and district rows school_code=NULL, but the shared rule
    # source keeps transform and validator in lockstep. No §4b masks apply
    # (verified: bronze percent within [0, 100] in every year; the 2019
    # statewide scope shift and the 2018-2021 zero-spike are preserved +
    # documented, not masked).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. The suppression-era split (no TFS pre-2022 vs
    # heavy TFS 2022+) legitimately shifts per-year NULL rates — surfaced
    # as a warning, documented in the contract.
    spikes = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spikes.status == "warning":
        logger.warning(
            "NULL-rate spikes (expected at the 2022 suppression boundary): %s",
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
            "Georgia Office of Student Achievement (GOSA) Out-of-Field "
            "teacher FTE report. For every Georgia public school, school "
            "district, and the state as a whole, reports the total teacher "
            "full-time equivalent (`total_fte`), the FTE of teachers "
            "assigned to a subject for which they are not certified "
            "(`out_of_field_fte`), and the out-of-field FTE as a "
            "percentage of total FTE (`out_of_field_fte_rate`, on a 0-1 "
            "decimal scale). Each entity has three rows — Total, High "
            "Poverty, and Low Poverty — reporting the same three metrics "
            "across poverty strata of schools. Coverage spans the "
            "2017-2018 school year through 2023-2024."
        ),
        title="Out-of-Field Teachers",
        summary=(
            "Share of Georgia teachers assigned to a subject they are not "
            "certified in, by school, district, and poverty stratum, "
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
                    "whose names cannot be resolved are dropped only under "
                    "documented predicates; the transform manifest records "
                    "each dropped class and count per year."
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
                "name": "poverty_subgroup",
                "type": "string",
                "nullable": False,
                "example": "total",
                "validValues": sorted(POVERTY_SUBGROUP_MAP.values()),
                "short_description": (
                    "School-poverty stratum the row covers: all schools "
                    "(total), or only the highest- or lowest-poverty "
                    "quartile; a school-poverty level, not a student "
                    "demographic."
                ),
                "description": (
                    "Poverty stratum of the schools whose FTE this row "
                    "aggregates. `total` covers all schools in the entity; "
                    "`high_poverty` covers only the entity's schools in the "
                    "state's highest-poverty quartile; `low_poverty` only "
                    "those in the lowest-poverty quartile. Per GOSA's K-12 "
                    "Teacher & Leader Workforce Reports, a school's poverty "
                    "level is defined by its direct-certification rate (the "
                    "share of students directly certified for free/reduced-"
                    "price meals) — higher direct certification means higher "
                    "poverty. For a school-level row the stratum describes "
                    "the school itself, so `high_poverty`/`low_poverty` rows "
                    "duplicate that school's `total` row (enforced by a "
                    "quality check). This is a SCHOOL-poverty stratum, NOT a "
                    "student demographic — it does not map to the global "
                    "demographics dimension."
                ),
            },
            {
                "name": "total_fte",
                "metric_component": "denominator",
                "type": "float64",
                "unit": "count",
                "example": 42.5,
                "null_meaning": (
                    "Suppressed by the GOSA reporting floor (`TFS`, fewer "
                    "than 10 teachers); suppression exists from the 2022 "
                    "file onward — 2018-2021 contain no suppression."
                ),
                "description": (
                    "Total teacher full-time equivalent count in the entity "
                    "(or in the poverty subgroup). Fractional FTEs are real "
                    "(e.g. 42.5). NULL when suppressed by the GOSA "
                    "reporting floor (`TFS`, < 10 teachers; 2022 onward "
                    "only). Denominator of `out_of_field_fte_rate`. The "
                    "2019 statewide level (162,256.2) is ~37%% above "
                    "neighboring years (2018: 118,009.1; 2020: 110,800.8) — "
                    "a broader teacher population GOSA reported that year "
                    "at every detail level; and the 2018 file mixes scopes "
                    "across levels (school rows broad, district/state rows "
                    "narrow). Preserved faithfully per data-cleaning-"
                    "standards §4b (extreme-but-conceivable)."
                ),
            },
            {
                "name": "out_of_field_fte",
                "metric_component": "numerator",
                "type": "float64",
                "unit": "count",
                "example": 4.2,
                "null_meaning": (
                    "Suppressed (`TFS`, < 10 FTE) — 2022 onward. 2018-2021 "
                    "files have no suppression, so NULL does not occur "
                    "there; but see the description for the 2018-2021 "
                    "suppression-as-zero anomaly."
                ),
                "description": (
                    "Teacher FTE assigned to a subject for which the "
                    "teacher is not certified (teaching out of field) in "
                    "the entity (or poverty subgroup). NULL when suppressed "
                    "(`TFS`, < 10 FTE) — observed from 2022 onward (~88%% "
                    "of school-level rows). KNOWN ANOMALY: 2018-2021 files "
                    "have no explicit suppression but carry implausibly "
                    "high concentrations of literal 0 (2020: 48%% of "
                    "school-level rows; 2021: 18%%) that almost certainly "
                    "encode suppression as zero. True zeros cannot be "
                    "mechanically separated, so every bronze 0 is preserved "
                    "as 0.0 — treat 2018-2021 zeros with caution (school-"
                    "level aggregates including 2020 are biased toward "
                    "zero). Numerator of `out_of_field_fte_rate`. In this "
                    "topic the 2018-2022 bronze OUTOFFIELD_FTE column "
                    "carries genuine out-of-field values (unlike the "
                    "sibling emergency-credentials topic, whose 2018-2021 "
                    "bronze mislabels Emergency values under the same "
                    "header)."
                ),
            },
            {
                "name": "out_of_field_fte_rate",
                "key_metric": True,
                "type": "float64",
                "unit": "proportion",
                "example": 0.11,
                "null_meaning": (
                    "The bronze percentage itself was suppressed (`TFS`) — "
                    "2022 onward. The rate can be non-NULL while "
                    "`out_of_field_fte` is suppressed, and vice versa — "
                    "GOSA suppresses each cell independently."
                ),
                "short_description": (
                    "Share of teacher FTE assigned out of field, on a 0-1 "
                    "scale (out_of_field_fte / total_fte)."
                ),
                "description": (
                    "`out_of_field_fte` / `total_fte` on a 0-1 decimal "
                    "scale. Bronze publishes an integer 0-100 percent "
                    "(verified range 0-100 across all years); divided by "
                    "100 per data-cleaning-standards §4. Because GOSA "
                    "rounds the percent to an integer computed from "
                    "unrounded FTE values, the published rate deviates from "
                    "out_of_field_fte/total_fte by up to 0.0124 at entities "
                    "with total_fte >= 3 (enforced within 0.015 by a "
                    "quality check scoped to total_fte >= 3). At 26 "
                    "tiny-FTE rows (total_fte < 3, 2018-2021 alternative "
                    "programs) the published percent deviates by up to 0.57 "
                    "from the rounded-FTE quotient (e.g. 1.0/1.0 published "
                    "as 50%%) — GOSA evidently computed those percents from "
                    "unrounded FTE values; the published rate is preserved "
                    "per §4b (extreme-but-conceivable, not impossible)."
                ),
            },
        ],
        source="Governor's Office of Student Achievement (GOSA)",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        limitations=(
            "Cross-topic lineage caveat: the sibling emergency-credentials "
            "topic's 2018-2021 bronze files re-use the column headers "
            "OUTOFFIELD_FTE / OUTOFFIELD_FTE_PCT for Emergency-credential "
            "values (its 2021 state total is 9,796.9). THIS topic's bronze "
            "is the genuine out-of-field report (2021 state total 6,281.9) "
            "— do not reconcile the two by column name. Suppression is "
            "era-asymmetric: 2018-2021 files contain no TFS markers at all, "
            "while 2022 onward suppress values below 10 with TFS (treat "
            "NULL as 'value < 10' for 2022+; NULL does not occur before "
            "2022). KNOWN ANOMALY: 2018-2021 out_of_field_fte carries "
            "implausibly many literal zeros (48%% of 2020 school rows) that "
            "almost certainly encode suppression as 0; all zeros are "
            "preserved per bronze fidelity and consumers must handle "
            "2018-2021 zeros explicitly. The FTE denominator has scope "
            "shifts: the 2019 file reports a ~37%% broader teacher "
            "population at every detail level, and the 2018 file mixes "
            "scopes ACROSS levels (school rows broad — statewide school-row "
            "total_fte sums to 157,557.3 — while district and state rows "
            "are narrow, state row 118,009.1), so 2018 school rows do NOT "
            "sum to their district or state aggregates. The source "
            "publishes only district/school NAMES, so codes are resolved by "
            "name against the education dimensions via the shared educator-"
            "topic resolver (year-aware certified_personnel lookups, "
            "curated code pins, guarded matching); rows that cannot be "
            "resolved are dropped only under documented predicates — "
            "redundant 2023 truncated charter-container aggregates and "
            "cataloged source gaps — with per-year counts in the transform "
            "manifest. State rows have NULL district_code and school_code; "
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
                "Dropped-row classes: (1) 2023 generic truncated charter-"
                "container labels ('State Charter Schools '/'-') — redundant "
                "district-aggregate republications of the bare school-name "
                "rows already in gold (every state-charter district except "
                "7991895 has exactly one school); dropping prevents double-"
                "counting. This class includes the 2023 'State Charter "
                "Schools II- Genesis Innovation Academy' truncated twins "
                "(Boys/Girls distinguisher erased at 52 chars; the two rows "
                "carry divergent metrics, so no single-target bind is "
                "faithful). (2) Documented source gaps — entities with no "
                "single faithful dimension target (K-8/K-12 combined "
                "campuses the dimension splits, closed schools, pre-merge "
                "sibling pairs, Ivy Prep Kirkwood). (3) 2023 duplicate "
                "charter republications — several single-school state-"
                "charter entities published both under their specific "
                "container district label and under the generic placeholder "
                "container; after name resolution both bind to the same key "
                "with identical metrics and are deduplicated (recorded as "
                "duplicate_rows_deduped in the manifest)."
            ),
            (
                "CRITICAL cross-topic distinction — in THIS topic the "
                "2018-2022 bronze columns OUTOFFIELD_FTE / "
                "OUTOFFIELD_FTE_PCT carry genuine out-of-field values. The "
                "sibling educator_qualifications_emergency_and_provisional_"
                "credentials topic re-uses the same header names in its "
                "2018-2021 files for Emergency-credential values (GOSA "
                "mislabel; 2021 state totals: 9,796.9 there vs 6,281.9 "
                "here). Never cross-validate the two topics by bronze "
                "column name."
            ),
            (
                "Suppression is era-asymmetric: 2018-2021 files contain "
                "zero TFS markers in any column (verified by direct count); "
                "2022+ mask values below 10 with TFS (NULL in gold). The "
                "per-year NULL-rate shift at the 2022 boundary is expected "
                "and documented."
            ),
            (
                "2018-2021 zero-spike anomaly: out_of_field_fte carries "
                "implausibly high concentrations of literal 0 before "
                "explicit suppression begins (2018: 2.9%% of school rows; "
                "2019: 3.3%%; 2020: 48%%; 2021: 18%%). The 2020 rate is "
                "almost certainly an undocumented suppression-as-zero "
                "encoding. All zeros pass through to gold as 0.0 (bronze "
                "fidelity); downstream analysts should treat 2018-2021 "
                "out_of_field_fte = 0 rows explicitly — aggregates that "
                "include 2020 will be biased toward zero."
            ),
            (
                "poverty_subgroup is a SCHOOL-poverty stratum (total / "
                "high_poverty / low_poverty), NOT a student demographic; the "
                "topic has no demographic column. For school-level rows the "
                "stratum row duplicates the school's total row (a school IS "
                "its stratum) — enforced by quality checks; district/state "
                "rows aggregate only the schools in that stratum."
            ),
            (
                "FTE-denominator scope anomalies: the 2019 file reports a "
                "~37%% broader teacher population at every detail level "
                "(state total_fte 162,256.2 vs 118,009.1 in 2018 and "
                "110,800.8 in 2020); the 2018 file mixes scopes across "
                "levels — school rows broad (statewide school-row sum "
                "157,557.3) vs district/state rows narrow (state row "
                "118,009.1, 1.335x) — so 2018 school rows do not sum to "
                "their district or state aggregates. Same pattern as the "
                "sibling emergency topic (shared FTE denominator). All "
                "values preserved per §4b; within-row rates remain "
                "internally consistent at every level."
            ),
        ],
        quality_checks=[
            {
                "name": "out_of_field_fte_within_total_fte",
                "description": (
                    "The out-of-field FTE count never exceeds the total "
                    "teacher FTE it is drawn from (verified across all "
                    "bronze years: zero violations)."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE out_of_field_fte IS NOT NULL "
                    "AND total_fte IS NOT NULL "
                    "AND out_of_field_fte > total_fte"
                ),
                "mustBe": 0,
            },
            {
                "name": "out_of_field_fte_rate_reconciles_with_components",
                "description": (
                    "out_of_field_fte_rate reconciles with out_of_field_fte "
                    "/ total_fte within 0.015 on the 0-1 scale, scoped to "
                    "rows with total_fte >= 3. Tolerance and scope derived "
                    "from bronze: GOSA publishes an integer percent "
                    "computed from unrounded FTE values, so the worst "
                    "in-scope deviation is 0.0124; below 3 FTE the 0.1-FTE "
                    "rounding dominates and 26 tiny alternative-program "
                    "rows (2018-2021) deviate by up to 0.57 — those "
                    "published rates are preserved per §4b and documented "
                    "in the column description."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE total_fte IS NOT NULL "
                    "AND out_of_field_fte IS NOT NULL "
                    "AND out_of_field_fte_rate IS NOT NULL "
                    "AND total_fte >= 3 "
                    "AND ABS(out_of_field_fte / total_fte "
                    "- out_of_field_fte_rate) > 0.015"
                ),
                "mustBe": 0,
            },
            {
                "name": "school_poverty_stratum_mirrors_total",
                "description": (
                    "A school-level high_poverty or low_poverty row "
                    "duplicates the same school's total row (a school IS its "
                    "poverty stratum; the stratum rows are republications, "
                    "not sub-populations). Checked on all three metrics "
                    "(total_fte, out_of_field_fte, out_of_field_fte_rate) "
                    "with a 0.001 float tolerance and null-safe guards — "
                    "GOSA suppresses each cell independently, so a "
                    "comparison is made only when both sides are non-NULL."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, school_code, "
                    "MAX(CASE WHEN poverty_subgroup = 'total' THEN total_fte "
                    "END) AS t, "
                    "MAX(CASE WHEN poverty_subgroup = 'high_poverty' THEN "
                    "total_fte END) AS hp, "
                    "MAX(CASE WHEN poverty_subgroup = 'low_poverty' THEN "
                    "total_fte END) AS lp, "
                    "MAX(CASE WHEN poverty_subgroup = 'total' THEN "
                    "out_of_field_fte END) AS to_, "
                    "MAX(CASE WHEN poverty_subgroup = 'high_poverty' THEN "
                    "out_of_field_fte END) AS hpo, "
                    "MAX(CASE WHEN poverty_subgroup = 'low_poverty' THEN "
                    "out_of_field_fte END) AS lpo, "
                    "MAX(CASE WHEN poverty_subgroup = 'total' THEN "
                    "out_of_field_fte_rate END) AS tr, "
                    "MAX(CASE WHEN poverty_subgroup = 'high_poverty' THEN "
                    "out_of_field_fte_rate END) AS hpr, "
                    "MAX(CASE WHEN poverty_subgroup = 'low_poverty' THEN "
                    "out_of_field_fte_rate END) AS lpr "
                    "FROM {object} WHERE school_code IS NOT NULL "
                    "GROUP BY year, district_code, school_code"
                    ") WHERE (t IS NOT NULL AND hp IS NOT NULL AND "
                    "ABS(hp - t) > 0.001) "
                    "OR (t IS NOT NULL AND lp IS NOT NULL AND "
                    "ABS(lp - t) > 0.001) "
                    "OR (to_ IS NOT NULL AND hpo IS NOT NULL AND "
                    "ABS(hpo - to_) > 0.001) "
                    "OR (to_ IS NOT NULL AND lpo IS NOT NULL AND "
                    "ABS(lpo - to_) > 0.001) "
                    "OR (tr IS NOT NULL AND hpr IS NOT NULL AND "
                    "ABS(hpr - tr) > 0.001) "
                    "OR (tr IS NOT NULL AND lpr IS NOT NULL AND "
                    "ABS(lpr - tr) > 0.001)"
                ),
                "mustBe": 0,
            },
            {
                "name": "school_never_in_both_poverty_strata",
                "description": (
                    "The high/low poverty quartiles are disjoint, so no "
                    "school carries both a high_poverty and a low_poverty "
                    "row in the same year (verified across all bronze "
                    "years)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, school_code FROM {object} "
                    "WHERE school_code IS NOT NULL "
                    "AND poverty_subgroup IN ('high_poverty', 'low_poverty') "
                    "GROUP BY year, district_code, school_code "
                    "HAVING COUNT(DISTINCT poverty_subgroup) > 1"
                    ") AS bad"
                ),
                "mustBe": 0,
            },
            {
                "name": "aggregate_poverty_strata_within_total",
                "description": (
                    "At district and state level the high-poverty and "
                    "low-poverty strata are disjoint subsets of the entity, "
                    "so high_poverty + low_poverty <= total + 0.25 when all "
                    "three are reported — checked on both total_fte and "
                    "out_of_field_fte. The 0.25 tolerance covers GOSA's "
                    "0.1-FTE rounding (observed worst excess: 0.1 at Greene "
                    "County 2021/2022 and Richmond County 2021)."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, district_code, "
                    "MAX(CASE WHEN poverty_subgroup = 'total' THEN total_fte "
                    "END) AS t, "
                    "MAX(CASE WHEN poverty_subgroup = 'high_poverty' THEN "
                    "total_fte END) AS hp, "
                    "MAX(CASE WHEN poverty_subgroup = 'low_poverty' THEN "
                    "total_fte END) AS lp, "
                    "MAX(CASE WHEN poverty_subgroup = 'total' THEN "
                    "out_of_field_fte END) AS to_, "
                    "MAX(CASE WHEN poverty_subgroup = 'high_poverty' THEN "
                    "out_of_field_fte END) AS hpo, "
                    "MAX(CASE WHEN poverty_subgroup = 'low_poverty' THEN "
                    "out_of_field_fte END) AS lpo "
                    "FROM {object} WHERE school_code IS NULL "
                    "GROUP BY year, district_code"
                    ") WHERE (t IS NOT NULL AND hp IS NOT NULL AND lp IS NOT "
                    "NULL AND hp + lp > t + 0.25) "
                    "OR (to_ IS NOT NULL AND hpo IS NOT NULL AND lpo IS NOT "
                    "NULL AND hpo + lpo > to_ + 0.25)"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_rows_exactly_three_per_year",
                "description": (
                    "Structural fact: every year carries exactly three "
                    "state-level rows (district_code IS NULL) — one per "
                    "poverty stratum."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year FROM {object} WHERE district_code IS NULL "
                    "GROUP BY year "
                    "HAVING COUNT(*) <> 3 "
                    "OR COUNT(DISTINCT poverty_subgroup) <> 3"
                    ") AS bad"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
