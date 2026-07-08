"""Transform bronze placements data into a gold county/year fact table.

Source: Georgia Juvenile Justice Data Clearinghouse (juveniledata.georgiacourts.gov),
"Decision Point Placements Raw Data" — one cumulative CSV (2010-2025, ~434k
rows) of juvenile x placement x offense-record rows for youths held in secure
DJJ facilities: RYDCs (Regional Youth Detention Centers, pre-adjudication
secure detention) and YDCs (Youth Development Campuses, post-commitment
secure confinement).

Design decisions (from bronze-data-structure.md and data-cleaning-standards):

- **PII rule: placement/offense-level rows never reach gold.** Bronze rows
  carry a pseudonymized youth ID (`newjuvenileid`). The transform reduces to
  placement-grain records and then aggregates to county/year (x demographic
  x facility type) cells; the youth ID is consumed to derive distinct-youth
  and distinct-placement counts and is never exported. No additional
  small-cell suppression is applied: the source itself publishes the
  pseudonymized placement-level file, so county/year aggregates are strictly
  less disclosive than the public source (same rationale as the
  decision_points sibling).
- **Placement identity = distinct (youth, admitted date, site) tuple within a
  year block** (structure doc ETL #5). The source's own duplicate flags are
  broken for 2014 (they under-mark duplicates: 19,186 unflagged rows vs
  10,343 actual distinct placements) and `Placement Count` is unreliable
  (ETL #6, not constant within youth-year), so both are ignored and all
  counts are derived from the rows themselves via the robust tuple key.
- **Year semantics: `Year` = "placement active during year"** (verified:
  433,825/433,844 rows satisfy admitted <= Year <= terminated-or-open). A
  multi-year stay appears once in each year it was active, so served-counts
  in adjacent years share stays and MUST NOT be summed across years. Two
  placement measures are served per cell:
  - `num_new_placements` (key metric): placements whose admission date falls
    in the row's year — aligned with the clearinghouse's official "new
    instances of secure detention / secure confinement" measures. Per the
    definitions page, the official measure excludes transfers between
    same-type facilities from "new instances"; a transfer appears here as a
    new (site, admitted-date) tuple and is not detectable, so gold slightly
    OVERSTATES the official measure (documented in the contract). The
    structure doc's illustrative new-admission figures (2010: 9,955 ...
    2025: 3,706) do not exactly match any reconstructible tuple recipe
    (this transform: 2010: 10,512; 2025: 3,752, ~5% above); the doc's own
    sanctioned placement key filtered to admission-year==Year is used and the
    delta is flagged for data review (judgment item).
  - `num_placements`: all placements active during the year
    (served-during-year), the doc's robust per-year placement count
    (2010: 16,299 ... 2025: 6,081 — reproduced exactly).
- **County concept: County of Residence** (structure doc ETL #9 recommended
  primary geography — where youths are from). Arrest / Facility / Offense
  county are alternate concepts and are not served; Facility County covers
  only the ~30 facility locations and would misattribute youths.
- **OUT OF STATE residence rows (~2.5% of rows)** cannot carry a county FIPS:
  excluded from county-level rows (recorded via record_filtered), included in
  the state-level rollup, so statewide totals cover the full published
  universe (decision_points precedent). Bare "MACON" is Macon County (13193),
  a real county in this 160-name list — see COUNTY_NAME_OVERRIDES note.
- **State rollup is synthesized from the placement-level microdata.** Bronze
  has no state rows; the source has no suppression and gold is built from
  the complete file, so state rows are exact and preserve information county
  rows cannot reconstruct: statewide distinct-youth counts (a youth residing
  in two counties across placements counts once statewide) and the OUT OF
  STATE contribution.
- **Demographic axes.** Race (White/Black/AmInd/Asian/Other/Hispanic) and
  gender (MALE/FEMALE) are youth attributes on every bronze row (zero
  nulls). Gold packs three overlapping axes into `demographic`: `all`, one
  row per race value, one row per gender value; consumers filter to one axis.
- **Asian / Pacific Islander (S5b).** Individual-level data with one
  mutually-exclusive race bucket per row, no Pacific Islander bucket
  anywhere, an explicit `Other` catch-all, and an unused race code 5 — the
  state-level math test is inapplicable by construction. Bare `Asian` is
  mapped to `asian`, consistent with the decision_points sibling (same
  source, same 6-bucket scheme), with the caveat documented in the contract:
  Pacific Islander youths most plausibly land in `other`. `Hispanic` is
  coded by the source as a race-level bucket.
- **facility_type categorical: `rydc` / `ydc` / `all`.** The two facility
  types drive the source's two official measures, so they are a grain
  categorical. An `all` rollup row is emitted per cell because
  `num_youth` is NOT additive across facility types (a youth can be held in
  both an RYDC and a YDC in the same year) — the rollup preserves a
  distinct-youth total consumers cannot reconstruct (mirrors the
  grade_level='all' convention). Placement counts DO partition exactly
  across rydc/ydc (each placement has one resolved type) — enforced as a
  quality check. 214 placement tuples (~0.15%) carry BOTH site types in
  their rows (MACON / AUGUSTA / EASTMAN campuses house both an RYDC and a
  YDC); each is resolved to its modal site type, ties to RYDC (the
  pre-adjudication default, 96% of rows) — logged and bounded by a <1%
  runtime guard.
- **Attribute consistency within a placement tuple is guarded, not assumed.**
  Residence county, race, and gender are verified unique within every
  placement tuple at runtime (currently zero conflicts) — a violation would
  break the partition invariants and hard-fails the run.
- **S4b masks (bronze-side, pre-aggregation).** Seven `Admitted Date` values
  are the sentinel `01-01-1900` — impossible for a 2010+ placement — and are
  NULLed (rows preserved: they still count as served placements, but cannot
  be classified as new admissions; recorded via record_masked). 16 rows
  (5 youths) violate the year window entirely (`Year` outside
  [admitted, terminated]) — known-bad per the structure doc; dropped with
  record_filtered. No gold-side masks apply: all gold metrics are counts
  derived by len/n_unique and cannot be out of domain.
- **Columns intentionally not served:** offense fields (free-text
  descriptions would need a curated category mapping — ETL #14; omitted for
  v1), length-of-stay statistics (derivable from the date pair; deferred as
  a possible additive column — judgment item), Site Name / Facility County
  (facility-level detail below county grain), `Gender Code` / `Race Code`
  (verified 1:1 redundant with their labels at runtime, then dropped),
  `Other offenses` (fully derivable from Offense Date), duplicate flags
  (dedup bookkeeping, broken for 2014), `Placement Count` (unreliable).
- **Dedup tie-break.** A single bronze file feeds gold and every cell is
  produced by one group_by, so post-aggregation duplicates are impossible by
  construction; `deduplicate_by_levels(sort_col="num_placements")` remains
  as the documented safety net (prefer the fuller row) should a future
  refresh add an overlapping file. The collision guard runs first and
  surfaces any divergent duplicate as a hard error.
- **No suppression.** The source publishes clean row-level data with no
  markers, so `suppressed_to_null=False`; every gold cell exists only where
  activity occurred and all three metrics are always non-NULL (zeros are
  possible only for num_new_placements).
- **Read with encoding="utf8-lossy".** The file carries invalid UTF-8
  (Windows-1252 en-dashes) confined to `Offense Description`, which gold
  does not serve; lossy decode is safe and keeps the fast polars read path.
"""

import datetime as dt
import logging
from pathlib import Path

import polars as pl

from src.utils.crosswalks import add_county_fips
from src.utils.demographics import DEMOGRAPHIC_ALIASES, normalize_demographic_column
from src.utils.metadata import write_data_dictionary
from src.utils.readers import list_bronze_files, read_bronze_file
from src.utils.transformers import (
    COUNTY_DETAIL_LEVEL_FILES,
    TransformManifest,
    assert_no_natural_key_collisions,
    deduplicate_by_levels,
    detect_era_by_columns,
    export_to_parquet,
    harmonize_columns,
    null_aggregate_geography,
    validate_output,
)
from src.utils.validators import (
    CRIMINAL_JUSTICE_DOMAIN_CONFIG,
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

TOPIC = "placements"
BRONZE_DIR = Path("data/bronze/criminal_justice/juvenile_clearinghouse/placements")
GOLD_DIR = Path("data/gold/criminal_justice/placements")
SOURCE_URL = "https://juveniledata.georgiacourts.gov/dashboards-reports/"

# Era detection by column signature (single cumulative file, one schema across
# all years; a future schema change must hard-fail, not silently misparse).
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_1_2010_2025_placement_level": [
        "Year",
        "newjuvenileid",
        "Site Name",
        "Site Type",
        "County of Residence",
        "Admitted Date",
        "Date Terminated",
    ],
}

# Bronze columns the transform depends on (rename-coverage guard). The offense
# columns, duplicate flags, Placement Count, and the redundant code columns
# are deliberately unused (see module docstring).
REQUIRED_COLUMNS: list[str] = [
    "Year",
    "newjuvenileid",
    "Gender",
    "Gender Code",
    "Race Value",
    "Race Code",
    "Site Name",
    "Site Type",
    "County of Residence",
    "Admitted Date",
    "Date Terminated",
]

# Site Type (stripped) -> gold facility_type. Recorded on the manifest; any
# new bronze label lands unmapped and blocks the run.
FACILITY_TYPE_MAP: dict[str, str] = {
    "RYDC": "rydc",
    "YDC": "ydc",
}

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "county_fips",
    "demographic",
    "facility_type",
    "num_new_placements",
    "num_placements",
    "num_youth",
    "detail_level",
]

METRIC_COLUMNS: list[str] = [
    "num_new_placements",
    "num_placements",
    "num_youth",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "county_fips": pl.Utf8,
    "demographic": pl.Utf8,
    "facility_type": pl.Utf8,
    **{c: pl.Int64 for c in METRIC_COLUMNS},
    "detail_level": pl.Utf8,
}

NATURAL_KEYS: list[str] = [
    "year",
    "county_fips",
    "demographic",
    "facility_type",
    "detail_level",
]

# Residence value carried by youths held in Georgia facilities but not
# resident in a Georgia county — excluded from county rows, included in the
# state rollup (see module docstring).
OUT_OF_STATE_LABEL = "OUT OF STATE"

# Impossible admission date published by the source (7 rows) — a placement in
# a 2010+ year block cannot have started in 1900. NULLed per S4b.
SENTINEL_ADMISSION_DATE = dt.date(1900, 1, 1)

# The demographic values gold can emit (used by the partition quality checks
# and the contract enum documentation, kept in one place so they cannot
# drift). Same 6-bucket race scheme as the decision_points sibling.
RACE_DEMOGRAPHICS: list[str] = [
    "asian",
    "black",
    "hispanic",
    "native_american",
    "other",
    "white",
]
GENDER_DEMOGRAPHICS: list[str] = ["female", "male"]

FACILITY_TYPES: list[str] = ["all", "rydc", "ydc"]


# =============================================================================
# Guards
# =============================================================================


def _require_columns(df: pl.DataFrame, required: list[str], label: str) -> None:
    """Raise if any expected bronze column is absent (rename-coverage guard).

    An unmatched source column silently becomes NULL in gold — the most
    common data-loss bug — so a missing expected column is a hard stop.
    """
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"{label}: expected bronze column(s) missing: {missing}. "
            f"Present: {df.columns}"
        )


def _assert_code_label_bijection(df: pl.DataFrame) -> None:
    """Verify Gender Code / Race Code are exactly 1:1 with their labels.

    The structure doc verifies the bijection on the current file (ETL #13);
    this cheap invariant re-proves it on every refresh before the code
    columns are dropped as redundant. A violation means the source's coding
    scheme changed and the label columns can no longer be trusted blindly.
    """
    for code_col, label_col in [("Gender Code", "Gender"), ("Race Code", "Race Value")]:
        pairs = df.select(code_col, label_col).unique()
        n_codes = pairs[code_col].n_unique()
        n_labels = pairs[label_col].n_unique()
        if not (pairs.height == n_codes == n_labels):
            raise ValueError(
                f"{code_col} <-> {label_col} is no longer 1:1: "
                f"{pairs.sort(code_col).to_dicts()}"
            )


def _parse_day_first_date(col: str) -> pl.Expr:
    """Parse a DD-MM-YYYY bronze date string (day-first, never auto-infer).

    strict=False so NULLs pass through; the caller asserts the parse
    introduced no new NULLs (the structure doc verifies all non-null values
    in all three date columns parse cleanly under %d-%m-%Y).
    """
    return pl.col(col).str.strip_chars().str.to_date("%d-%m-%Y", strict=False)


# =============================================================================
# Placement-level reduction
# =============================================================================


def _clean_rows(df: pl.DataFrame, manifest: TransformManifest) -> pl.DataFrame:
    """Cast, strip, date-parse, and apply the two S4b cleanups to bronze rows.

    Returns one row per bronze row (minus the 16 dropped year-window
    violations) with the derived columns the reduction needs. Ordering:
    per-year bronze counts are recorded BEFORE any row removal.
    """
    df = df.with_columns(
        pl.col("Year").str.strip_chars().cast(pl.Int32, strict=True).alias("year"),
        pl.col("newjuvenileid").str.strip_chars().alias("juvenile_id"),
        pl.col("Site Name").str.strip_chars().alias("site_name"),
        # Site Type is right-padded to 10 chars on every bronze row.
        pl.col("Site Type").str.strip_chars().alias("site_type_raw"),
        pl.col("County of Residence").str.strip_chars().alias("residence_county"),
        pl.col("Race Value").str.strip_chars().alias("race_raw"),
        pl.col("Gender").str.strip_chars().alias("gender_raw"),
        _parse_day_first_date("Admitted Date").alias("admitted_date"),
        _parse_day_first_date("Date Terminated").alias("terminated_date"),
    )

    # Per-year bronze accounting on the raw rows.
    for row in df.group_by("year").len().sort("year").iter_rows(named=True):
        manifest.record_bronze(row["year"], row["len"])

    # Day-first parsing must not introduce NULLs beyond the raw ones (the
    # structure doc proves 0 parse failures); a new NULL means the source
    # date format changed and must be analyzed, not passed on.
    for raw_col, parsed_col in [
        ("Admitted Date", "admitted_date"),
        ("Date Terminated", "terminated_date"),
    ]:
        new_nulls = df[parsed_col].null_count() - df[raw_col].null_count()
        if new_nulls:
            raise ValueError(
                f"{raw_col}: {new_nulls} value(s) failed the %d-%m-%Y parse — "
                "source date format changed; investigate before proceeding"
            )

    # These columns are fully populated in bronze (zero nulls per the
    # structure doc); the partition invariants depend on that.
    for col in (
        "juvenile_id",
        "site_name",
        "site_type_raw",
        "residence_county",
        "race_raw",
        "gender_raw",
    ):
        if df[col].null_count():
            raise ValueError(f"'{col}' has NULLs — bronze regressed; investigate")

    # S4b mask: sentinel 01-01-1900 admission dates are impossible for 2010+
    # placements -> NULL the date (rows preserved; they remain served
    # placements but cannot be classified as new admissions).
    sentinel_mask = pl.col("admitted_date") == SENTINEL_ADMISSION_DATE
    sentinel = df.filter(sentinel_mask)
    if sentinel.height:
        years = sorted(sentinel["year"].unique().to_list())
        logger.warning(
            "Masking %d sentinel 01-01-1900 Admitted Date value(s) to NULL "
            "(years %s) — impossible admission date, S4b",
            sentinel.height,
            years,
        )
        manifest.record_masked(
            column="admitted_date",
            count=sentinel.height,
            reason=(
                "sentinel 01-01-1900 admission date NULLed before aggregation "
                "(impossible for a 2010+ placement); rows kept as served "
                "placements, excluded from num_new_placements"
            ),
            years=years,
        )
        df = df.with_columns(
            pl.when(sentinel_mask)
            .then(pl.lit(None, dtype=pl.Date))
            .otherwise(pl.col("admitted_date"))
            .alias("admitted_date")
        )

    # Known-bad rows: Year entirely outside [admitted, terminated-or-open]
    # (16 rows / 5 youths per the structure doc) — the placement provably was
    # not active in the row's year block, so the row cannot be attributed.
    adm_year = pl.col("admitted_date").dt.year()
    term_year = pl.col("terminated_date").dt.year()
    violation_mask = pl.col("admitted_date").is_not_null() & (
        (pl.col("year") < adm_year)
        | (term_year.is_not_null() & (pl.col("year") > term_year))
    )
    violations = df.filter(violation_mask)
    if violations.height:
        logger.warning(
            "Dropping %d year-window-violating row(s) (%d youth(s); years %s) "
            "— Year outside [admitted, terminated], known-bad per structure doc",
            violations.height,
            violations["juvenile_id"].n_unique(),
            sorted(violations["year"].unique().to_list()),
        )
        for row in violations.group_by("year").len().sort("year").iter_rows(named=True):
            manifest.record_filtered(
                row["year"], row["len"], "year_window_violation_row_dropped"
            )
        df = df.filter(~violation_mask)

    return df


def _reduce_to_placements(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Collapse offense-level rows to one row per placement tuple.

    Placement identity is the structure doc's robust key: (year block,
    youth, admitted date, site name). Offense rows and true duplicate rows
    (ETL #11) collapse into their placement. Attribute resolution:

    - residence county / race / gender: guarded unique within every tuple
      (currently zero conflicts) — .first() is then exact, not a choice.
    - site type: 214 tuples (~0.15%) span both RYDC and YDC rows (campuses
      housing both facility types); resolved to the modal type, ties to RYDC
      (the pre-adjudication default, 96% of rows). Bounded by a <1% guard.
    """
    placements = df.group_by(["year", "juvenile_id", "admitted_date", "site_name"]).agg(
        pl.col("residence_county").first(),
        pl.col("race_raw").first(),
        pl.col("gender_raw").first(),
        pl.col("residence_county").n_unique().alias("_n_county"),
        pl.col("race_raw").n_unique().alias("_n_race"),
        pl.col("gender_raw").n_unique().alias("_n_gender"),
        (pl.col("site_type_raw") == "RYDC").sum().alias("_n_rydc_rows"),
        (pl.col("site_type_raw") == "YDC").sum().alias("_n_ydc_rows"),
        pl.col("site_type_raw").n_unique().alias("_n_site_types"),
    )

    # Hard guard: county/race/gender must be constant within a placement
    # tuple, or the demographic/geography partitions would double-count.
    for col, label in [
        ("_n_county", "residence county"),
        ("_n_race", "race"),
        ("_n_gender", "gender"),
    ]:
        conflicted = placements.filter(pl.col(col) > 1)
        if conflicted.height:
            raise ValueError(
                f"{conflicted.height} placement tuple(s) carry >1 distinct "
                f"{label} — partition invariants would break; sample: "
                f"{conflicted.head(5).to_dicts()}"
            )

    # Modal site-type resolution (ties -> RYDC), with a share guard so a
    # source regression cannot silently blur the rydc/ydc split.
    mixed = placements.filter(pl.col("_n_site_types") > 1)
    if mixed.height:
        share = mixed.height / placements.height
        logger.warning(
            "%d placement tuple(s) (%.2f%%) span both site types (dual-type "
            "campuses); resolving each to its modal type, ties to RYDC",
            mixed.height,
            100 * share,
        )
        if share > 0.01:
            raise ValueError(
                f"Mixed-site-type placement share {share:.2%} exceeds 1% — "
                "source structure changed; re-analyze before aggregating"
            )
    placements = placements.with_columns(
        pl.when(pl.col("_n_rydc_rows") >= pl.col("_n_ydc_rows"))
        .then(pl.lit("rydc"))
        .otherwise(pl.lit("ydc"))
        .alias("facility_type"),
        # New-admission flag: admission date falls in the row's year block.
        # NULL admission dates (3 raw + 7 masked sentinels) count as served
        # but never as new.
        (pl.col("admitted_date").dt.year() == pl.col("year"))
        .fill_null(False)
        .alias("is_new"),
    )

    # Record the facility-type recode on the manifest from the raw stripped
    # site-type labels (row grain, pre-modal-resolution — every bronze label
    # must map or the run blocks).
    manifest.record_categorical(
        column="facility_type",
        map_dict=FACILITY_TYPE_MAP,
        bronze_series=df["site_type_raw"],
        gold_series=df["site_type_raw"].replace_strict(FACILITY_TYPE_MAP, default=None),
    )

    logger.info(
        "Reduced %d offense-level rows to %d placement tuples (%d youths)",
        df.height,
        placements.height,
        placements["juvenile_id"].n_unique(),
    )
    return placements.drop(
        "_n_county",
        "_n_race",
        "_n_gender",
        "_n_rydc_rows",
        "_n_ydc_rows",
        "_n_site_types",
    )


# =============================================================================
# Demographics + geography
# =============================================================================


def _record_demographic_mapping(df: pl.DataFrame, manifest: TransformManifest) -> None:
    """Record the demographic recode on the manifest (per skill rule 4.3a).

    Demographics use the shared DEMOGRAPHIC_ALIASES, never a topic-local map;
    the manifest records the EFFECTIVE slice — the aliases actually hit by
    the observed race + gender labels — which keeps map_used reviewable while
    preserving the unmapped guard (a label missing from the aliases stays out
    of the map and is counted as unmapped, which blocks the run).
    """
    bronze_series = pl.concat([df["race_raw"], df["gender_raw"]])
    gold_series = pl.concat(
        [
            df.select(normalize_demographic_column("race_raw").alias("d"))["d"],
            df.select(normalize_demographic_column("gender_raw").alias("d"))["d"],
        ]
    )
    observed = bronze_series.drop_nulls().unique().to_list()
    effective_map = {
        label: DEMOGRAPHIC_ALIASES[label.strip().upper()]
        for label in observed
        if label.strip().upper() in DEMOGRAPHIC_ALIASES
    }
    manifest.record_categorical(
        column="demographic",
        map_dict=effective_map,
        bronze_series=bronze_series,
        gold_series=gold_series,
    )


def _resolve_county_fips(df: pl.DataFrame, manifest: TransformManifest) -> pl.DataFrame:
    """Join county FIPS by residence name; hard-stop on unexpected misses.

    All 159 Georgia county names resolve against the global counties
    dimension (bare MACON is Macon County 13193 — the global crosswalk
    deliberately carries no macon->bibb override); only OUT OF STATE is
    legitimately FIPS-less (state rollup only). Any other unmatched name
    means the crosswalk or the source changed and must be fixed via
    COUNTY_NAME_OVERRIDES, never silently NULLed.
    """
    df = add_county_fips(df, "residence_county")
    unmatched = df.filter(
        pl.col("county_fips").is_null()
        & (pl.col("residence_county") != OUT_OF_STATE_LABEL)
    )
    if unmatched.height:
        raise ValueError(
            "Unmatched county name(s) — add to COUNTY_NAME_OVERRIDES: "
            f"{unmatched['residence_county'].unique().sort().to_list()}"
        )

    # Record the observed name -> FIPS mapping. OUT OF STATE maps to an
    # explicit non-FIPS marker so the manifest shows it handled deliberately
    # (excluded from county rows, kept in state rows) rather than unmapped.
    county_map = {
        row["residence_county"]: row["county_fips"]
        for row in df.select("residence_county", "county_fips")
        .unique()
        .drop_nulls("county_fips")
        .to_dicts()
    }
    county_map[OUT_OF_STATE_LABEL] = "state_rollup_only_no_county_fips"
    manifest.record_categorical(
        column="county_fips",
        map_dict=county_map,
        bronze_series=df["residence_county"],
        gold_series=df["county_fips"],
    )
    return df


# =============================================================================
# Aggregation to gold cells
# =============================================================================


def _aggregation_exprs() -> list[pl.Expr]:
    """Cell-level aggregations over placement-grain rows.

    At placement grain each row IS one distinct placement tuple, so
    num_placements is a plain row count and num_new_placements a flag sum.
    Distinct-youth counts use n_unique(juvenile_id) — a youth can hold
    several placements per cell — and are therefore NOT additive across
    cells (counties, demographics, facility types, or years).
    """
    return [
        pl.col("is_new").sum().alias("num_new_placements"),
        pl.len().alias("num_placements"),
        pl.col("juvenile_id").n_unique().alias("num_youth"),
    ]


def _aggregate_slices(
    base: pl.DataFrame, geo_cols: list[str], detail_level: str
) -> pl.DataFrame:
    """Aggregate one detail level across demographic x facility-type slices.

    Demographic axis: `all` (every youth), per-race, per-gender — three
    overlapping axes packed into `demographic` per project convention (S5a:
    within-axis values are mutually exclusive per placement; `all` overlaps
    everything). Facility axis: `all` (both types) plus the resolved
    rydc/ydc split. Grouping happens on the ALREADY-normalized demographic,
    so labels aliasing to one canonical value aggregate, never dedup.
    """
    frames = []
    for demo_expr in (
        pl.lit("all"),
        normalize_demographic_column("race_raw"),
        normalize_demographic_column("gender_raw"),
    ):
        for facility_expr in (pl.lit("all"), pl.col("facility_type")):
            frames.append(
                base.with_columns(
                    demo_expr.alias("demographic"),
                    facility_expr.alias("facility_group"),
                )
                .group_by(["year", *geo_cols, "demographic", "facility_group"])
                .agg(_aggregation_exprs())
            )
    out = (
        pl.concat(frames)
        .rename({"facility_group": "facility_type"})
        .with_columns(pl.lit(detail_level).alias("detail_level"))
    )
    if "county_fips" not in geo_cols:
        out = out.with_columns(pl.lit(None).cast(pl.Utf8).alias("county_fips"))
    return out


def _transform_placement_level(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Transform the placement-level file into county + state gold rows.

    Cleans and guards the bronze rows, reduces to placement grain, resolves
    county FIPS, then aggregates to county/year and state/year cells across
    the demographic and facility-type slices. juvenile_id is consumed by the
    aggregation — no youth-level data leaves this function (PII rule).
    """
    _require_columns(df, REQUIRED_COLUMNS, "era_1_2010_2025")
    _assert_code_label_bijection(df)

    rows = _clean_rows(df, manifest)
    placements = _reduce_to_placements(rows, manifest)
    _record_demographic_mapping(placements, manifest)
    placements = _resolve_county_fips(placements, manifest)

    # County rows exclude OUT OF STATE residents (no FIPS to key on); the
    # state rollup keeps them so statewide totals cover the full universe.
    oos = placements.filter(pl.col("county_fips").is_null())
    if oos.height:
        logger.info(
            "Excluding %d OUT OF STATE placement tuple(s) from county-level "
            "rows (kept in the state rollup)",
            oos.height,
        )
        for row in oos.group_by("year").len().sort("year").iter_rows(named=True):
            manifest.record_filtered(
                row["year"],
                row["len"],
                "out_of_state_placements_excluded_from_county_level_kept_in_state",
            )

    counties = _aggregate_slices(
        placements.filter(pl.col("county_fips").is_not_null()),
        geo_cols=["county_fips"],
        detail_level="county",
    )
    # State rows aggregate ALL placements (in-state + OUT OF STATE): exact,
    # because the source is unsuppressed microdata, and they carry statewide
    # distinct-youth counts a consumer cannot rebuild from county rows.
    states = _aggregate_slices(placements, geo_cols=[], detail_level="state")

    logger.info(
        "Aggregated %d placement tuples into %d county and %d state cells",
        placements.height,
        counties.height,
        states.height,
    )
    return pl.concat(
        [counties.select(STANDARD_COLUMNS), states.select(STANDARD_COLUMNS)]
    )


# =============================================================================
# File routing
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame | None:
    """Read one bronze file, verify its era signature, and transform it.

    All-string read (infer_schema_length=0) per skill rule 4.3b with
    encoding="utf8-lossy" (the file carries invalid Windows-1252 bytes,
    confined to the unused Offense Description column). The file spans
    2010-2025 internally, so file-level manifest events are keyed to the
    latest data year.
    """
    df, loss = read_bronze_file(
        path, return_loss=True, infer_schema_length=0, encoding="utf8-lossy"
    )
    # Defensive header cleanup so stray padding cannot dodge era detection.
    df = df.rename({c: c.strip() for c in df.columns if c != c.strip()})

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{path.name}: no era signature matched columns {df.columns}")

    latest_year = int(df["Year"].cast(pl.Int32).max())
    manifest.record_read_loss(
        latest_year, path.name, loss["raw_rows"], loss["parsed_rows"]
    )
    manifest.record_file(path, latest_year, era, df.height, df.columns)
    logger.info("Processing %s as %s (%d rows)", path.name, era, df.height)
    return _transform_placement_level(df, manifest)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for placements."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file (read-loss accounted per file).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR):
        result = transform_file(path, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize columns/dtypes and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)
    logger.info("Combined %d gold-shaped rows", combined.height)

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean an aggregation bug and must raise, not be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: one bronze file feeds gold and every cell comes from one
    # group_by, so duplicates are impossible by construction; sort_col
    # "num_placements" is the documented safety net (prefer the fuller row)
    # should a future refresh introduce an overlapping file.
    combined = deduplicate_by_levels(
        combined,
        {
            "county": ["year", "county_fips", "demographic", "facility_type"],
            "state": ["year", "demographic", "facility_type"],
        },
        sort_col="num_placements",
    )

    # 4. Geography nulling (shared domain rules). The S4b masks are bronze-side
    # (sentinel admission dates, year-window rows) and were applied before
    # aggregation; gold metrics are len/n_unique counts and cannot be out of
    # domain, so no gold-side _null_* helper applies.
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=CRIMINAL_JUSTICE_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. Metrics are fully non-null (no suppression), so any
    # null-rate spike would indicate a transform regression.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(
        combined,
        required_non_null=["year", "detail_level", "demographic", "facility_type"],
    )

    # 5. Manifest stats on the FINAL DataFrame, then export.
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(
        combined,
        GOLD_DIR,
        STANDARD_COLUMNS,
        detail_level_files=COUNTY_DETAIL_LEVEL_FILES,
    )
    manifest.write(GOLD_DIR)

    # 6. Contract from the in-code column declaration.
    _emit_contract(
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


def _emit_contract(year_range: tuple[int, int]) -> None:
    """Emit the ODCS contract via ``write_data_dictionary``.

    The column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level`` — the contract's properties (and the validator's schema
    check) follow it.
    """
    demographic_values = sorted(["all", *RACE_DEMOGRAPHICS, *GENDER_DEMOGRAPHICS])
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Secure juvenile placements in Georgia Department of Juvenile "
            "Justice facilities by the youth's county of residence, "
            "2010-2025, aggregated from the Georgia Juvenile Justice Data "
            "Clearinghouse's pseudonymized placement-level file. Per county, "
            "year, demographic group, and facility type (RYDC secure "
            "detention / YDC secure confinement): new placements started in "
            "the year, placements active during the year, and distinct "
            "youths held."
        ),
        title="Juvenile Secure Placements",
        summary=(
            "Youths held in Georgia's secure juvenile facilities — RYDC "
            "detention and YDC confinement — with new-placement, "
            "active-placement, and distinct-youth counts by county of "
            "residence, race, and gender, 2010-2025."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "Calendar year the placement was ACTIVE (source 'Year'). "
                    "A stay spanning multiple years is counted in each year "
                    "it was active, so num_placements and num_youth must "
                    "never be summed across years; num_new_placements "
                    "attributes each placement to its admission year only."
                ),
            },
            {
                "name": "county_fips",
                "type": "string",
                "example": "13121",
                "description": (
                    "5-digit county FIPS code (state prefix 13) of the "
                    "youth's COUNTY OF RESIDENCE (where youths are from, not "
                    "where the facility sits); FK to the counties dimension. "
                    "NULL on state-level rows. Youths whose residence the "
                    "source labels OUT OF STATE (~2.5%% of placement rows) "
                    "carry no county and appear only in the state rollup."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "all",
                "validValues": demographic_values,
                "short_description": (
                    "Youth group the row covers: every youth (all), one race "
                    "group, or one gender group."
                ),
                "description": (
                    "Demographic slice. Three overlapping axes are packed "
                    "into this column: 'all' (every youth), race "
                    "(asian/black/hispanic/native_american/other/white), and "
                    "gender (male/female) — filter to one axis; summing "
                    "across axes double-counts. Race values follow the "
                    "source's 6-bucket scheme: hispanic is a mutually "
                    "exclusive race-level bucket, and no Pacific Islander "
                    "bucket exists anywhere in the source — bare source "
                    "'Asian' is mapped to asian as published (consistent "
                    "with the decision_points dataset from the same source), "
                    "with any Pacific Islander youths most plausibly "
                    "reported in the explicit 'other' catch-all. Each "
                    "placement carries exactly one race and one gender, so "
                    "placement counts partition exactly across each axis; "
                    "distinct-youth counts may not (a youth's reported race "
                    "could differ across placements)."
                ),
            },
            {
                "name": "facility_type",
                "type": "string",
                "nullable": False,
                "example": "rydc",
                "validValues": FACILITY_TYPES,
                "short_description": (
                    "Secure facility type: rydc (pre-adjudication detention), "
                    "ydc (post-commitment confinement), or all (both)."
                ),
                "description": (
                    "Secure facility type: rydc (Regional Youth Detention "
                    "Center — short-term, largely pre-adjudication secure "
                    "detention; ~96%% of placements), ydc (Youth Development "
                    "Campus — long-term post-commitment secure confinement), "
                    "or all (both types combined). The 'all' rollup is "
                    "served because num_youth is NOT additive across "
                    "facility types (a youth can be held in both an RYDC and "
                    "a YDC in the same year); placement counts DO partition "
                    "exactly across rydc + ydc. 214 placements (~0.15%%) at "
                    "campuses housing both facility types carried both "
                    "labels in the source and were resolved to their modal "
                    "type (ties to rydc). Filter to one value; summing "
                    "across all three double-counts."
                ),
            },
            {
                "name": "num_new_placements",
                "type": "int64",
                "unit": "count",
                "key_metric": True,
                "example": 42,
                "short_description": (
                    "Secure placements newly started in the year — new "
                    "detention (rydc) or confinement (ydc) instances."
                ),
                "description": (
                    "Placements whose admission date falls in the row's year "
                    "— the closest reconstruction of the Clearinghouse's "
                    "official 'new instances of secure detention / secure "
                    "confinement' measures. A placement is a distinct "
                    "(youth, admission date, facility) stay. Slightly "
                    "OVERSTATES the official measure: the official "
                    "definition excludes transfers between same-type "
                    "facilities, which are not detectable in the source "
                    "(a transfer appears as a new stay at the receiving "
                    "facility). Additive across counties, race values, "
                    "gender values, facility types, and years. 5 placements "
                    "(from 10 bronze rows: 3 with a missing admission date, "
                    "7 published as an impossible 01-01-1900 sentinel and "
                    "NULLed) are counted in num_placements but never here."
                ),
            },
            {
                "name": "num_placements",
                "type": "int64",
                "unit": "count",
                "example": 64,
                "description": (
                    "Distinct placements (youth x admission date x facility) "
                    "ACTIVE at any point during the year, including stays "
                    "begun in earlier years. NOT additive across years (a "
                    "multi-year stay is counted in each year it was active); "
                    "additive across counties, demographic values within one "
                    "axis, and facility types. Always >= num_new_placements "
                    "and >= 1 (rows exist only where placements occurred)."
                ),
            },
            {
                "name": "num_youth",
                "type": "int64",
                "unit": "count",
                "example": 48,
                "description": (
                    "Distinct youths (pseudonymized source IDs) held in the "
                    "cell during the year. NOT additive along any axis: a "
                    "youth with placements in two counties, both facility "
                    "types, or multiple years counts once in each cell but "
                    "once in the corresponding rollup — use the 'all' "
                    "facility row and state rows for unduplicated totals."
                ),
            },
        ],
        source="Georgia Juvenile Justice Data Clearinghouse",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        suppressed_to_null=False,
        usage=(
            "Attribute the Georgia Juvenile Justice Data Clearinghouse "
            "(juveniledata.georgiacourts.gov). Filter demographic to one axis "
            "at a time ('all', the race values, or the gender values) AND "
            "facility_type to one value ('all', 'rydc', or 'ydc'); use state "
            "rows for statewide figures instead of summing county rows "
            "(distinct-youth counts are not additive, and out-of-state "
            "residents appear only in the state rollup). Compare "
            "num_new_placements across years for trend analysis; "
            "num_placements and num_youth are active-during-year measures "
            "that must not be summed across years."
        ),
        limitations=(
            "State rows have NULL county_fips. The source publishes no "
            "suppression — metric values are never NULL and zeros appear "
            "only in num_new_placements (a cell can hold only carried-over "
            "placements). Counties are the youth's county of RESIDENCE; "
            "youths labeled OUT OF STATE (~2.5%% of placements) appear only "
            "in state rows, so county figures sum slightly below the state "
            "row. num_new_placements slightly overstates the official "
            "'new instances' measures because transfers between same-type "
            "facilities are not detectable in the source. num_placements "
            "and num_youth count presence during the year, not admissions — "
            "never sum them across years; num_youth is not additive along "
            "any axis. The panel is sparse: an absent county-year-cell "
            "means no matching placements existed, not missing data. "
            "Offense detail and length-of-stay statistics present in the "
            "source's placement-level file are not served in this dataset."
        ),
        quality_checks=[
            {
                "name": "new_placements_within_placements",
                "description": (
                    "Placements newly admitted in the year are a subset of "
                    "placements active during it, so num_new_placements must "
                    "not exceed num_placements in any cell."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "num_new_placements IS NOT NULL AND num_placements IS NOT "
                    "NULL AND num_new_placements > num_placements"
                ),
                "mustBe": 0,
            },
            {
                "name": "youth_within_placements",
                "description": (
                    "Every counted youth holds at least one placement in the "
                    "cell, so num_youth must not exceed num_placements."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE num_youth IS NOT NULL "
                    "AND num_placements IS NOT NULL AND "
                    "num_youth > num_placements"
                ),
                "mustBe": 0,
            },
            {
                "name": "cells_exist_only_where_activity",
                "description": (
                    "The source has no suppression and cells are emitted only "
                    "where placements occurred: all three metrics must be "
                    "non-NULL and num_placements/num_youth at least 1 "
                    "(num_new_placements may be 0 for carried-over-only "
                    "cells)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "num_new_placements IS NULL OR num_placements IS NULL OR "
                    "num_youth IS NULL OR num_placements < 1 OR num_youth < 1"
                ),
                "mustBe": 0,
            },
            {
                # Pivot-with-conditional-aggregation, never a self-join (S15b).
                "name": "facility_partition_num_placements",
                "description": (
                    "Each placement resolves to exactly one facility type, so "
                    "per (year, county_fips, demographic) the rydc + ydc "
                    "rows' num_placements must sum to the facility_type='all' "
                    "row. GROUP BY treats the NULL county_fips of state rows "
                    "as one group, so the invariant is enforced at both "
                    "levels."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, demographic, "
                    "MAX(CASE WHEN facility_type = 'all' THEN num_placements "
                    "END) AS total, "
                    "SUM(CASE WHEN facility_type IN ('rydc','ydc') THEN "
                    "num_placements END) AS split_sum "
                    "FROM {object} GROUP BY year, county_fips, demographic"
                    ") WHERE total IS NOT NULL AND split_sum IS NOT NULL "
                    "AND total != split_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "facility_partition_num_new_placements",
                "description": (
                    "Same partition as facility_partition_num_placements for "
                    "the headline metric: rydc + ydc num_new_placements must "
                    "sum to the facility_type='all' row."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, demographic, "
                    "MAX(CASE WHEN facility_type = 'all' THEN "
                    "num_new_placements END) AS total, "
                    "SUM(CASE WHEN facility_type IN ('rydc','ydc') THEN "
                    "num_new_placements END) AS split_sum "
                    "FROM {object} GROUP BY year, county_fips, demographic"
                    ") WHERE total IS NOT NULL AND split_sum IS NOT NULL "
                    "AND total != split_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "race_partition_num_placements",
                "description": (
                    "Each placement carries exactly one race value (guarded "
                    "at transform time), so per (year, county_fips, "
                    "facility_type) the six race rows' num_placements must "
                    "sum to the demographic='all' row."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, facility_type, "
                    "MAX(CASE WHEN demographic = 'all' THEN num_placements "
                    "END) AS total, "
                    "SUM(CASE WHEN demographic IN ('asian','black','hispanic',"
                    "'native_american','other','white') THEN num_placements "
                    "END) AS race_sum "
                    "FROM {object} GROUP BY year, county_fips, facility_type"
                    ") WHERE total IS NOT NULL AND race_sum IS NOT NULL "
                    "AND total != race_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "gender_partition_num_placements",
                "description": (
                    "Each placement carries exactly one gender value (guarded "
                    "at transform time), so per (year, county_fips, "
                    "facility_type) the male + female rows' num_placements "
                    "must sum to the demographic='all' row."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, county_fips, facility_type, "
                    "MAX(CASE WHEN demographic = 'all' THEN num_placements "
                    "END) AS total, "
                    "SUM(CASE WHEN demographic IN ('female','male') THEN "
                    "num_placements END) AS gender_sum "
                    "FROM {object} GROUP BY year, county_fips, facility_type"
                    ") WHERE total IS NOT NULL AND gender_sum IS NOT NULL "
                    "AND total != gender_sum"
                ),
                "mustBe": 0,
            },
            {
                "name": "county_placements_within_state_total",
                "description": (
                    "Each placement belongs to exactly one residence county "
                    "(or OUT OF STATE), so per (year, demographic, "
                    "facility_type) the county rows' num_placements must sum "
                    "to AT MOST the state row (the gap is exactly the "
                    "out-of-state placements kept only in the state rollup)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, demographic, facility_type, "
                    "MAX(CASE WHEN county_fips IS NULL THEN num_placements "
                    "END) AS state_total, "
                    "SUM(CASE WHEN county_fips IS NOT NULL THEN "
                    "num_placements END) AS county_sum "
                    "FROM {object} GROUP BY year, demographic, facility_type"
                    ") WHERE state_total IS NOT NULL AND county_sum IS NOT "
                    "NULL AND county_sum > state_total"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
