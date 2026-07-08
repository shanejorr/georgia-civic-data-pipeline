"""Transform educator_qualifications_emergency_and_provisional_credentials to gold.

Source: Governor's Office of Student Achievement (GOSA) — Emergency-credential
teacher FTE report, school years 2017-18 through 2023-24 (7 CSV files, one
per year). For every Georgia public school, school district, and the state,
the source publishes total teacher FTE, the FTE of teachers holding an
Emergency teaching credential, and that count as an integer percentage of
total FTE. Each entity carries three poverty-stratum rows: Total, High
Poverty, and Low Poverty.

Design decisions (from bronze-data-structure.md + data-cleaning-standards):

- **Three column-name eras, one tidy shape, detected by column signature.**
  Era 1 (2023-2024): `#CATEGORY_DESC` (constant `Emergency`) +
  `CATEGORY_FTE` / `CATEGORY_FTE_PCT`. Era 2 (2022): `Emergency_FTE` /
  `Emergency_FTE_PCT`. Era 3 (2018-2021): columns NAMED `OUTOFFIELD_FTE` /
  `OUTOFFIELD_FTE_PCT` but carrying Emergency-credential values — a
  confirmed GOSA header mis-labeling (the 2021 state total here is 9,796.9
  while the genuine out-of-field topic's 2021 state total is 6,281.9). The
  Era 3 rename to the emergency metric trio is the deliberate correction of
  that mis-labeling and must not be "fixed" back.
- **`#CATEGORY_DESC` and `LABEL_LVL_3_DESC` are verified constants**
  (`Emergency`, `Teachers`) and dropped; the era functions raise if the
  source ever adds another category (e.g. an actual Provisional row — none
  exist in bronze despite the topic name) or role.
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
  and manifest-recorded via record_filtered.
- **Dropped-row classes** (all manifest-recorded per year):
  * `state_charter_placeholder_district` — 2023 generic truncated charter
    container labels ("State Charter Schools "/"-") whose school name could
    not be independently rescued. These are redundant district-aggregate
    republications of the bare school-name rows already in gold (every
    state-charter district except 7991895 has exactly one school), so
    dropping prevents double-counting; prior data reviews verified this
    delta as PASS — it is deliberate, not data loss.
  * `source_gap_district` / `source_gap_school` — documented entities with
    no single faithful dimension target (K-8/K-12 combined campuses the dim
    splits, closed schools, pre-merge sibling pairs, Ivy Prep Kirkwood,
    etc.). Fidelity over coverage: binding to the nearest-named dim row
    would mis-attribute facts.
- **Era-asymmetric suppression.** 2018-2020 publish true zeros with no
  suppression; 2021+ mask any value below 10 with `TFS` (-> NULL via the
  all-string read + strict=False cast). Consumers should read NULL as
  "< 10" for 2021+ but as genuinely missing pre-2021. Zeros in 2018-2020
  are real measurements and are preserved.
- **`emergency_fte_rate` is a bounded proportion (§4a).** Bronze publishes
  an integer 0-100 percent (verified min 0 / max 100 across all years);
  divided by 100. No §4b masks apply: no impossible values exist in any
  year (the 2019 statewide FTE level, ~37%% above neighboring years, is a
  population-scope change GOSA published at every detail level that year —
  extreme-but-conceivable, preserved and documented).
- **Dedup collapses 2023 charter republications (32 rows).** The bronze
  name key is unique within each year file, but the 2023 file publishes
  several single-school state-charter entities TWICE: once under the
  specific container district label and once under the generic placeholder
  container (as the bare school name and/or the 52-char-truncated
  "...- All Sc" aggregate form). After resolution both publications bind to
  the same (year, district_code, school_code, poverty_subgroup) key with
  IDENTICAL metrics, and dedup collapses them — 32 rows in 2023, recorded
  via record_filtered. The collision guard runs first, so only
  identical-metric duplicates can ever be collapsed; divergent-metric
  duplicates raise. Tie-break `sort_col="emergency_fte"` is documented for
  the hypothetical future case of a republication with differing
  suppression (prefer the row with a reported count).
- **Quality checks (§15b)**, all verified against bronze across all 7 years:
  numerator within denominator (`emergency_fte <= total_fte`; 0 violations);
  rate reconciliation (|emergency_fte/total_fte − emergency_fte_rate| <=
  0.015 — observed max 0.0121 in 2020 at a 1.9-FTE school, from GOSA's
  integer-percent rounding against fractional FTE); school-level strata
  rows mirror the school's Total row (a school IS its stratum; verified on
  all three metrics); no school in both strata; district/state HP+LP within
  Total + 0.25 (observed max excess 0.1 — FTE rounding at Greene 2021/2022
  and Richmond 2021); exactly 3 state rows per year.

Judgment calls (non-interactive run):

1. Era 3 columns read as Emergency metrics per the structure doc's
   cross-topic numeric proof; documented in the contract limitations.
2. Unresolvable-name drops kept exactly at the v1-verified predicate set
   (placeholder containers + SOURCE_GAP entries) rather than widening any
   mechanical match rule — fidelity over coverage, and byte-parity with the
   approved v1 baseline.
3. Rate-reconciliation tolerance set to 0.015 (not the naive 0.005
   integer-rounding bound) because GOSA computes the integer percent from
   unrounded FTE values while publishing FTEs rounded to 0.1 — the bound was
   derived empirically from the worst observed bronze deviation (0.0121).
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

TOPIC = "educator_qualifications_emergency_and_provisional_credentials"
BRONZE_DIR = Path(
    "data/bronze/education/gosa/"
    "educator_qualifications_emergency_and_provisional_credentials"
)
GOLD_DIR = Path(
    "data/gold/education/educator_qualifications_emergency_and_provisional_credentials"
)
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# `LABEL_LVL_2_DESC` -> poverty_subgroup (snake_case per §10). A poverty
# stratum of schools, NOT a student demographic (see module docstring).
POVERTY_SUBGROUP_MAP: dict[str, str] = {
    "Total": "total",
    "High Poverty": "high_poverty",
    "Low Poverty": "low_poverty",
}

# Era-detection signatures (column presence), most specific first: Era 1's
# `#CATEGORY_DESC` is unique to it; Era 2 vs Era 3 differ in the metric
# column pair.
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
    "era_2_2022_emergency_named": [
        "LONG_SCHOOL_YEAR",
        "SCHOOL_DSTRCT_NM",
        "INSTN_NAME",
        "LABEL_LVL_3_DESC",
        "LABEL_LVL_2_DESC",
        "FTE",
        "Emergency_FTE",
        "Emergency_FTE_PCT",
    ],
    "era_3_2018_2021_outoffield_mislabeled": [
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

# Bronze metric source columns per era (total_fte source is `FTE` in every
# era). Era 3's OUTOFFIELD_* headers carry Emergency values — see docstring.
ERA_METRIC_COLUMNS: dict[str, tuple[str, str]] = {
    "era_1_2023_2024_category_desc": ("CATEGORY_FTE", "CATEGORY_FTE_PCT"),
    "era_2_2022_emergency_named": ("Emergency_FTE", "Emergency_FTE_PCT"),
    "era_3_2018_2021_outoffield_mislabeled": ("OUTOFFIELD_FTE", "OUTOFFIELD_FTE_PCT"),
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
    "emergency_fte",
    "emergency_fte_rate",
    "detail_level",
]

# All three metrics are Float64: FTEs are fractional (e.g. 34.8) and the
# rate lives on the 0-1 decimal scale.
TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "poverty_subgroup": pl.Utf8,
    "total_fte": pl.Float64,
    "emergency_fte": pl.Float64,
    "emergency_fte_rate": pl.Float64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = ["total_fte", "emergency_fte", "emergency_fte_rate"]

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
# Era transforms
# =============================================================================


def _assert_constant_column(
    df: pl.DataFrame, column: str, expected: str, label: str
) -> None:
    """Raise if a verified-constant bronze column carries any other value.

    A new value (e.g. an actual Provisional category) means the pipeline
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
    """Transform one bronze file (any era) to the pre-resolution gold shape.

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

    # Era 1 encodes the credential category as a row dimension — verify it
    # is the constant `Emergency` before dropping it (no Provisional rows
    # exist anywhere in bronze despite the topic name).
    if era == "era_1_2023_2024_category_desc":
        _assert_constant_column(df, "#CATEGORY_DESC", "Emergency", label)
    # Workforce role is constant `Teachers` in every era.
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
        # True zeros (2018-2020, pre-suppression) survive the cast.
        pl.col("FTE").cast(pl.Float64, strict=False).alias("total_fte"),
        pl.col(fte_col).cast(pl.Float64, strict=False).alias("emergency_fte"),
        # Bronze publishes an integer 0-100 percent (verified across all
        # years); divide by 100 onto the 0-1 scale per §4.
        (pl.col(pct_col).cast(pl.Float64, strict=False) / 100.0).alias(
            "emergency_fte_rate"
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
    same result as per-row resolution, ~25x fewer resolver calls.
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
    precedence automatically.
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
    # Tie-break: bronze keys are unique after the documented drops, so dedup
    # is purely defensive. sort_col="emergency_fte" prefers a row with a
    # reported count over a suppressed placeholder on any future
    # republication.
    pre_dedup = dict(combined.group_by("year").len().iter_rows())
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code", "poverty_subgroup"],
        district_keys=["year", "district_code", "poverty_subgroup"],
        state_keys=["year", "poverty_subgroup"],
        sort_col="emergency_fte",
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
    # statewide FTE level is preserved + documented, not masked).
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
            "Georgia Office of Student Achievement (GOSA) Emergency-credential "
            "teacher FTE report. For every Georgia public school, school "
            "district, and the state as a whole, reports the total teacher "
            "full-time equivalent (`total_fte`), the FTE of teachers holding "
            "an Emergency teaching credential (`emergency_fte`), and the "
            "emergency-credentialed FTE as a percentage of total FTE "
            "(`emergency_fte_rate`, on a 0-1 decimal scale). Each entity has "
            "three rows — Total, High Poverty, and Low Poverty — reporting "
            "the same three metrics across poverty strata of schools. "
            "Coverage spans the 2017-2018 school year through 2023-2024. "
            "Despite the topic name referencing 'Provisional' credentials, "
            "no provisional rows appear in the source; only Emergency is "
            "reported."
        ),
        title="Emergency-Credentialed Teachers",
        summary=(
            "Share of Georgia teachers holding an emergency credential by "
            "school, district, and school-poverty stratum, 2018-2024."
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
                    "than 10 teachers); suppression exists from the 2021 "
                    "file onward."
                ),
                "description": (
                    "Total teacher full-time equivalent count in the entity "
                    "(or in the poverty subgroup). Fractional FTEs are "
                    "real (e.g. 34.8). NULL when suppressed by the GOSA "
                    "reporting floor (`TFS`, < 10 teachers). Denominator of "
                    "`emergency_fte_rate`. The 2019 statewide level "
                    "(162,256.2) is ~37%% above neighboring years (2018: "
                    "118,009.1; 2020: 110,800.8) — a broader teacher "
                    "population GOSA reported that year at every detail "
                    "level, preserved faithfully per data-cleaning-"
                    "standards §4b (extreme-but-conceivable)."
                ),
            },
            {
                "name": "emergency_fte",
                "metric_component": "numerator",
                "type": "float64",
                "unit": "count",
                "example": 1.5,
                "null_meaning": (
                    "Suppressed (`TFS`, < 10 FTE) — 2021 onward. Pre-2021 "
                    "files have no suppression, so NULL does not occur and "
                    "0.0 is a true zero."
                ),
                "description": (
                    "Teacher FTE holding an Emergency teaching credential in "
                    "the entity (or poverty subgroup). NULL when suppressed "
                    "(`TFS`, < 10 FTE) — observed from 2021 onward. True "
                    "zeros (no emergency-credentialed teachers) are "
                    "preserved as 0.0 in 2018-2020, before GOSA introduced "
                    "suppression for this report. Numerator of "
                    "`emergency_fte_rate`. Sourced from bronze columns "
                    "CATEGORY_FTE (2023-24), Emergency_FTE (2022), and the "
                    "MIS-LABELED OUTOFFIELD_FTE (2018-21) — see the "
                    "limitations note."
                ),
            },
            {
                "name": "emergency_fte_rate",
                "key_metric": True,
                "type": "float64",
                "unit": "proportion",
                "example": 0.05,
                "null_meaning": (
                    "The bronze percentage itself was suppressed (`TFS`). "
                    "The rate can be non-NULL while `emergency_fte` is "
                    "suppressed, and vice versa — GOSA suppresses each cell "
                    "independently."
                ),
                "short_description": (
                    "Share of teacher FTE holding an emergency credential, "
                    "on a 0-1 scale (emergency_fte / total_fte)."
                ),
                "description": (
                    "`emergency_fte` / `total_fte` on a 0-1 decimal scale. "
                    "Bronze publishes an integer 0-100 percent (verified "
                    "range 0-100 across all years); divided by 100 per "
                    "data-cleaning-standards §4. Because GOSA rounds the "
                    "percent to an integer computed from unrounded FTE "
                    "values, the published rate can deviate from "
                    "emergency_fte/total_fte by up to ~0.012 at small "
                    "schools (worst observed: 0.0121 at a 1.9-FTE program "
                    "in 2020); a quality check enforces reconciliation "
                    "within 0.015. The rate is preserved from bronze even "
                    "when `emergency_fte` is suppressed — e.g. a row can "
                    "have emergency_fte=NULL with a non-NULL rate."
                ),
            },
        ],
        source="Governor's Office of Student Achievement (GOSA)",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        limitations=(
            "Source-lineage caveat: in the 2018-2021 bronze files (Era 3) the "
            "metric columns are NAMED `OUTOFFIELD_FTE` / `OUTOFFIELD_FTE_PCT`, "
            "but the VALUES they carry are Emergency-credential FTE counts, "
            "not out-of-field counts — a confirmed GOSA source mis-labeling "
            "(the 2021 state total here, 9,796.9, differs from the genuine "
            "out-of-field report's 6,281.9). The transform reads these as "
            "emergency_fte / emergency_fte_rate; do not re-interpret those "
            "years as out-of-field data. Despite the topic name, no "
            "'Provisional' rows appear in the source — only Emergency is "
            "reported. Suppression is era-asymmetric: 2018-2020 publish a "
            "real `0` (true zero emergency-credentialed teachers), while 2021 "
            "onward suppress any value below 10 with `TFS` (treat NULL as "
            "'count < 10' for 2021+ but as genuinely missing pre-2021); "
            "emergency_fte_rate may be non-null even when emergency_fte is "
            "suppressed. 2019 statewide FTE is ~37%% above neighboring years "
            "(a broader teacher population GOSA reported that year), "
            "preserved faithfully per data-cleaning-standards §4b. The 2018 "
            "file mixes scopes ACROSS detail levels: school rows are on the "
            "broad teacher-population scope while district and state rows are "
            "on the narrow scope (statewide school-row total_fte sums to "
            "157,557.3 vs the state row's 118,009.1, a 1.335x ratio; e.g. "
            "Gwinnett's district aggregate is 11,170.0 while its school rows "
            "sum to 22,190.6) — 2018 school rows do NOT sum to their district "
            "or state aggregates. The source "
            "publishes only district/school NAMES, so codes are resolved by "
            "name against the education dimensions via the shared educator-"
            "topic resolver (year-aware certified_personnel lookups, curated "
            "code pins, guarded matching); rows that cannot be resolved are "
            "dropped only under documented predicates — redundant 2023 "
            "truncated charter-container aggregates and cataloged source "
            "gaps — with per-year counts in the transform manifest. State "
            "rows have NULL district_code and school_code; district rows "
            "have NULL school_code."
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
                "counting and was verified PASS by prior data reviews. "
                "(2) Documented source gaps — entities with no single "
                "faithful dimension target (K-8/K-12 combined campuses the "
                "dimension splits, closed schools, pre-merge sibling pairs, "
                "Ivy Prep Kirkwood). Binding these to the nearest-named "
                "dimension row would mis-attribute facts. (3) 2023 "
                "duplicate charter republications — the 2023 file publishes "
                "several single-school state-charter entities both under "
                "their specific container district label and under the "
                "generic placeholder container; after name resolution both "
                "bind to the same key with identical metrics and are "
                "deduplicated (recorded as duplicate_rows_deduped in the "
                "manifest)."
            ),
            (
                "CRITICAL — in Era 3 (2018-2021 files) the bronze metric "
                "columns are NAMED OUTOFFIELD_FTE / OUTOFFIELD_FTE_PCT but "
                "carry Emergency-credential values (GOSA re-used the legacy "
                "header when first publishing the Emergency report; confirmed "
                "numerically against the separate out-of-field topic). The "
                "transform renames them to emergency_fte / "
                "emergency_fte_rate and must not be changed to treat them as "
                "out-of-field metrics."
            ),
            (
                "Despite the topic name, no Provisional rows appear in "
                "bronze: the 2023-2024 #CATEGORY_DESC column is the constant "
                "'Emergency'. If GOSA ever adds Provisional rows, the Era 1 "
                "constant assertion fires and the transform exits non-zero — "
                "extend the schema deliberately before re-running."
            ),
            (
                "Suppression is era-asymmetric: 2018-2020 publish true zeros "
                "with no suppression; 2021+ mask values below 10 with TFS "
                "(NULL in gold). Treat NULL as 'count < 10' for 2021+ but as "
                "genuinely missing pre-2021. The per-year NULL-rate shift at "
                "the 2021 boundary is expected and documented."
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
                "2019 statewide FTE anomaly: state-level total_fte=162,256.2 "
                "and emergency_fte=13,743.3 are ~37%% above neighboring years "
                "(2018: 118,009.1; 2020: 110,800.8). The level shift is "
                "present at every detail level in the 2019 file and reflects "
                "a broader teacher population GOSA reported that year; "
                "values preserved per §4b, and emergency_fte_rate (0.08 for "
                "the state total) is unaffected by the scope change."
            ),
            (
                "2018 cross-level scope inconsistency: unlike 2019 (broad "
                "scope at every level), the 2018 file mixes scopes ACROSS "
                "detail levels — school rows use the broad teacher-population "
                "scope while district and state rows use the narrow scope. "
                "Statewide, 2018 school-row total_fte sums to 157,557.3 vs "
                "the state row's 118,009.1 (1.335x); e.g. Gwinnett's district "
                "aggregate is 11,170.0 while its school rows sum to 22,190.6. "
                "All values are preserved faithfully per §4b, but 2018 school "
                "rows must not be expected to sum to their district or state "
                "aggregates. Within-row rates remain internally consistent at "
                "every level."
            ),
        ],
        quality_checks=[
            {
                "name": "emergency_fte_within_total_fte",
                "description": (
                    "The emergency-credentialed FTE count never exceeds the "
                    "total teacher FTE it is drawn from (verified across all "
                    "bronze years: zero violations)."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE emergency_fte IS NOT NULL AND total_fte IS NOT NULL "
                    "AND emergency_fte > total_fte"
                ),
                "mustBe": 0,
            },
            {
                "name": "emergency_fte_rate_reconciles_with_components",
                "description": (
                    "emergency_fte_rate reconciles with emergency_fte / "
                    "total_fte within 0.015 on the 0-1 scale. Tolerance "
                    "derived from bronze: GOSA publishes an integer percent "
                    "computed from unrounded FTE values, so the worst "
                    "observed deviation is 0.0121 (2020, a 1.9-FTE program); "
                    "the naive integer-rounding bound of 0.005 is too tight."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE total_fte IS NOT NULL AND emergency_fte IS NOT NULL "
                    "AND emergency_fte_rate IS NOT NULL AND total_fte > 0 "
                    "AND ABS(emergency_fte / total_fte - emergency_fte_rate) "
                    "> 0.015"
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
                    "(total_fte, emergency_fte, emergency_fte_rate) with a "
                    "0.001 float tolerance and null-safe guards — GOSA "
                    "suppresses each cell independently, so a comparison is "
                    "made only when both sides are non-NULL."
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
                    "emergency_fte END) AS te, "
                    "MAX(CASE WHEN poverty_subgroup = 'high_poverty' THEN "
                    "emergency_fte END) AS hpe, "
                    "MAX(CASE WHEN poverty_subgroup = 'low_poverty' THEN "
                    "emergency_fte END) AS lpe, "
                    "MAX(CASE WHEN poverty_subgroup = 'total' THEN "
                    "emergency_fte_rate END) AS tr, "
                    "MAX(CASE WHEN poverty_subgroup = 'high_poverty' THEN "
                    "emergency_fte_rate END) AS hpr, "
                    "MAX(CASE WHEN poverty_subgroup = 'low_poverty' THEN "
                    "emergency_fte_rate END) AS lpr "
                    "FROM {object} WHERE school_code IS NOT NULL "
                    "GROUP BY year, district_code, school_code"
                    ") WHERE (t IS NOT NULL AND hp IS NOT NULL AND "
                    "ABS(hp - t) > 0.001) "
                    "OR (t IS NOT NULL AND lp IS NOT NULL AND "
                    "ABS(lp - t) > 0.001) "
                    "OR (te IS NOT NULL AND hpe IS NOT NULL AND "
                    "ABS(hpe - te) > 0.001) "
                    "OR (te IS NOT NULL AND lpe IS NOT NULL AND "
                    "ABS(lpe - te) > 0.001) "
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
                    "emergency_fte. The 0.25 tolerance covers GOSA's 0.1-FTE "
                    "rounding (observed worst excess: 0.1 at Greene County "
                    "2021/2022 and Richmond County 2021)."
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
                    "emergency_fte END) AS te, "
                    "MAX(CASE WHEN poverty_subgroup = 'high_poverty' THEN "
                    "emergency_fte END) AS hpe, "
                    "MAX(CASE WHEN poverty_subgroup = 'low_poverty' THEN "
                    "emergency_fte END) AS lpe "
                    "FROM {object} WHERE school_code IS NULL "
                    "GROUP BY year, district_code"
                    ") WHERE (t IS NOT NULL AND hp IS NOT NULL AND lp IS NOT "
                    "NULL AND hp + lp > t + 0.25) "
                    "OR (te IS NOT NULL AND hpe IS NOT NULL AND lpe IS NOT "
                    "NULL AND hpe + lpe > te + 0.25)"
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
