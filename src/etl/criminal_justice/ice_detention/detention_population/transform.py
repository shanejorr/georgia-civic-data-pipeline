"""Transform bronze ICE detention data into a county-grain gold fact table.

Sources (two feeds, see bronze-data-structure.md and _provenance.md):

- **Feed 2a — DDP ``detention-management.xlsx``, sheet ``Facilities``** (the
  Deportation Data Project's collation of every biweekly snapshot of the ICE
  detention-statistics workbooks' Facilities sheet, FY2019-FY2026). PRIMARY
  source for the fiscal-year rows: one snake_case parse covers all workbook
  layout eras, includes FY2019 (absent from Feed 1), and its full intra-year
  snapshot history lets us recover facilities ICE dropped mid-year.
- **Feed 2b — DDP ``facilities-daily-population-latest.parquet``** (daily
  facility headcounts from FOIA record-level data, 2022-10-01 - 2026-03-10).
  PRIMARY source for the monthly rows.
- **Feed 1 — ICE fiscal-year workbooks (FY2020-FY2026)**: VERIFICATION ONLY.
  Every GA facility row in every workbook is compared metric-by-metric against
  the collation row this transform selected; any divergence hard-fails the
  run. (Verified: workbook values equal the collation's latest snapshot per
  fiscal year exactly.) The two FY2025 workbooks are byte-identical; only one
  is verified, the other recorded as an excluded duplicate.

Design decisions:

- **Grain: county x fiscal year x month, two detail levels (county, state).**
  ``year`` is the FEDERAL FISCAL YEAR (Oct 1 - Sep 30) on every row — the
  only coherent choice because the ICE ADP metrics are fiscal-year averages.
  ``month`` is a string categorical: ``"01"``-``"12"`` for calendar months
  within the fiscal year (months 10-12 fall in the prior calendar year), or
  ``"all"`` for the fiscal-year-total row (mirroring the ``demographic='all'``
  aggregation-lane pattern). Monthly rows subdivide the fiscal year, so the
  ``all`` row is a legitimate aggregate of its months.
- **Two metric families share the grain.** Fiscal-year rows (month='all')
  carry the ICE workbook ADP breakdowns (security level, gender x
  criminality, threat level, mandatory detention) plus guaranteed-minimum
  beds; monthly rows carry the DDP daily-panel means (total, by gender,
  convicted-criminal, possibly-under-18). ``avg_daily_population`` is the one
  metric populated on BOTH row kinds: on fiscal-year rows it is the sum of
  the four gender x criminality ADP components (each ADP breakdown family
  sums to total ADP to within 1e-6 — verified across all GA facility-FYs);
  on monthly rows it is the monthly mean of daily ``n_detained``. The daily
  ``n_detained`` mean reproduces the workbook fiscal-year ADP to ~0.5%%
  (Stewart FY2024: 1528.4 vs 1533.6; the midnight count is ~2%% lower), so
  the two definitions describe the same concept; the midnight headcount is
  deliberately not served as a redundant near-duplicate.
- **Latest-snapshot-per-facility, not per fiscal year.** ICE drops a facility
  from later snapshots when it stops holding ICE detainees mid-year (Irwin
  County FY2021 after the Sep 2021 ICE order, Cobb/Whitfield FY2021, Floyd
  FY2024) — taking the fiscal year's last snapshot would silently lose them.
  Each facility's fiscal-year row is taken from the LAST snapshot in which
  ICE published that facility that year (keyed on the resolved facility code
  so mid-year renames — 'MAIN - FOLKSTON IPC (D RAY JAMES)' -> 'FOLKSTON MAIN
  IPC' — collapse to one series). For facilities dropped mid-year the value
  is ICE's last published fiscal-YTD average for that year; documented in the
  contract.
- **Facility -> county via the maintained crosswalk**
  (``data/gold/crosswalks/facility_to_county.parquet``, ``source ==
  'ddp_ice'``), per the criminal_justice domain convention. The crosswalk's
  GA rows define the Georgia facility universe for the daily panel (which has
  no state column). Workbook/collation facility NAMES (which drift across
  years: case variants, truncation, renames) resolve to facility codes via
  the topic-local ``FACILITY_NAME_TO_CODE`` map (hand-built from the DDP
  stints file's (code, name) pairs and verified against the crosswalk); any
  unmapped GA name hard-fails. Facility codes never reach gold — rows are
  aggregated to county before export.
- **ALOS is NOT served (judgment call).** Average length of stay is a
  facility-level statistic that cannot be correctly aggregated to county
  grain without stay-level weights (an ADP-weighted mean is mathematically
  wrong — ALOS composes by completed stays, not by population). The
  collation's 'Facility ALOS' sheet is therefore skipped.
- **Book-ins are NOT served (judgment call).** Deriving county-month book-in
  counts requires the individual-level stints file, whose reliability DDP
  itself flags (hospital stints omitted, ``likely_duplicate`` rows, unclear
  historical completeness). Conservative choice: stays/stints remain
  bronze-only PII sources and contribute nothing to gold.
- **PII gate.** The record-level stays/stints parquets are never read for
  metrics; gold carries county-level aggregates only, from the already
  facility-aggregated collation and daily-population files.
- **Partial calendar months at the panel edges are dropped** (2026-03 covers
  10 of 31 days): a mean over a fraction of a month would masquerade as that
  month's average. Recorded via ``record_filtered``.
- **Zero-population county-months are real.** County jails with dormant IGSAs
  (Bartow, Bryan, Chatham...) publish real zeros in the daily panel — kept.
- **No suppression in either source** (``suppressed_to_null=False``). The
  collation's ``guaranteed_minimum`` non-numeric placeholders ('*', blank,
  NBSP) mean "no contractual guaranteed minimum" and become NULL via the
  strict=False cast (counted and logged; null_meaning documents it).
- **No S4b masks apply**: every ADP/headcount value in scope is non-negative
  and finite (verified); fractional ADP values are correct (fiscal-YTD
  averages), so nothing is provably impossible.
- **Dedup tie-break.** Natural-key collisions are impossible by construction
  (each sub-frame is produced by a group_by on the natural key, and the four
  sub-frames are disjoint on month/detail_level), and the collision guard
  runs first. ``deduplicate_by_levels(sort_col='avg_daily_population')``
  remains as the documented safety net: prefer the row with the larger
  (non-null) headline metric should a future refresh introduce overlap.
- **Attribution (required by DDP).** Fiscal-year rows: "government statistics
  published by ICE, collated by the Deportation Data Project"; monthly rows:
  "government data provided by ICE in response to a FOIA request, processed
  by the Deportation Data Project" — both carried into the contract usage.
"""

import hashlib
import logging
from pathlib import Path

import pandas as pd
import polars as pl

from src.utils.metadata import write_data_dictionary
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

TOPIC = "detention_population"
BRONZE_DIR = Path("data/bronze/criminal_justice/ice_detention/detention_population")
DDP_DIR = BRONZE_DIR / "ddp"
GOLD_DIR = Path("data/gold/criminal_justice/detention_population")
CROSSWALK_PATH = Path("data/gold/crosswalks/facility_to_county.parquet")
SOURCE_URL = "https://www.ice.gov/detain/detention-management"

COLLATION_FILE = DDP_DIR / "detention-management.xlsx"
DAILY_FILE = DDP_DIR / "facilities-daily-population-latest.parquet"

# Workbook/collation facility name -> ICE DETLOC code. Keys are normalized
# (uppercased, whitespace-collapsed) raw names observed across FY2019-FY2026;
# built from the DDP stints file's (code, name) pairs during bronze analysis.
# Renames map to one code so a facility's fiscal-year series stays contiguous
# ('MAIN - FOLKSTON IPC (D RAY JAMES)' and 'FOLKSTON MAIN IPC' are the same
# processing center; 'ATLANTA US PEN' and 'FCI ATLANTA' are both BOPATL).
# Any GA name that fails this map hard-stops the transform.
FACILITY_NAME_TO_CODE: dict[str, str] = {
    "ANNEX - FOLKSTON IPC": "FIPCAGA",
    "FOLKSTON ANNEX IPC": "FIPCAGA",
    "MAIN - FOLKSTON IPC (D RAY JAMES)": "FIPCMGA",
    "FOLKSTON MAIN IPC": "FIPCMGA",
    "FOLKSTON D RAY ICE PROCES": "FIPCDGA",
    "FOLKSTON D RAY ICE PROCESSING CTR": "FIPCDGA",
    # The BOP-contract D. Ray James Prison (closed 2021) has its own DETLOC,
    # distinct from the later FIPCDGA processing center on the same campus.
    "D. RAY JAMES PRISON": "GADRYJM",
    "STEWART DETENTION CENTER": "STWRTGA",
    "IRWIN COUNTY DETENTION CENTER": "IRWINGA",
    "ROBERT A DEYTON DETENTION": "RADDFGA",
    "ROBERT A DEYTON DETENTION FAC": "RADDFGA",
    "ROBERT A DEYTON DETENTION FACILITY": "RADDFGA",
    "ROBERT A. DEYTON DETENTION FACILITY": "RADDFGA",
    "COBB COUNTY JAIL": "COBBJGA",
    "FLOYD COUNTY JAIL": "FLOYDGA",
    "WHITFIELD COUNTY JAIL": "WHITFGA",
    "ATLANTA US PEN": "BOPATL",
    "FCI ATLANTA": "BOPATL",
}

# Collation (snake_case) metric column -> gold column. The 13 ADP breakdowns
# are fiscal-YTD averages (fractional floats); guaranteed_minimum is an
# integer contractual bed floor.
COLLATION_METRIC_TO_GOLD: dict[str, str] = {
    "level_a": "adp_security_level_a",
    "level_b": "adp_security_level_b",
    "level_c": "adp_security_level_c",
    "level_d": "adp_security_level_d",
    "male_crim": "adp_male_criminal",
    "male_non_crim": "adp_male_noncriminal",
    "female_crim": "adp_female_criminal",
    "female_non_crim": "adp_female_noncriminal",
    "ice_threat_level_1": "adp_threat_level_1",
    "ice_threat_level_2": "adp_threat_level_2",
    "ice_threat_level_3": "adp_threat_level_3",
    "no_ice_threat_level": "adp_no_threat_level",
    "mandatory": "adp_mandatory_detention",
    "guaranteed_minimum": "guaranteed_minimum_beds",
}

# Workbook (Feed 1) header -> collation snake_case column, for verification.
# The FY-prefixed ALOS column is not compared (ALOS is not served).
WORKBOOK_TO_COLLATION: dict[str, str] = {
    "Level A": "level_a",
    "Level B": "level_b",
    "Level C": "level_c",
    "Level D": "level_d",
    "Male Crim": "male_crim",
    "Male Non-Crim": "male_non_crim",
    "Female Crim": "female_crim",
    "Female Non-Crim": "female_non_crim",
    "ICE Threat Level 1": "ice_threat_level_1",
    "ICE Threat Level 2": "ice_threat_level_2",
    "ICE Threat Level 3": "ice_threat_level_3",
    "No ICE Threat Level": "no_ice_threat_level",
    "Mandatory": "mandatory",
    "Guaranteed Minimum": "guaranteed_minimum",
}

# Daily-panel column -> gold monthly column (monthly mean of the daily count).
DAILY_METRIC_TO_GOLD: dict[str, str] = {
    "n_detained": "avg_daily_population",
    "n_detained_male": "avg_daily_male",
    "n_detained_female": "avg_daily_female",
    "n_detained_convicted_criminal": "avg_daily_convicted_criminal",
    "n_detained_possibly_under_18": "avg_daily_possibly_under_18",
}

# Feed-1 workbook era signatures (inspection-tail drift; the 23-column core
# incl. every served metric is identical in all eras). Most specific first.
WORKBOOK_ERA_SIGNATURES: dict[str, list[str]] = {
    "era3_odo_nakamoto_split": ["ODO Inspection End Date"],
    "era1_second_to_last_full": ["Second to Last Inspection Rating"],
    "era2_second_to_last_trimmed": ["Second to Last Inspection Type"],
    "era4_pending_fy25": ["Pending FY25 Inspection"],
    "era5_last_final_rating": ["Last Final Rating"],
}

MONTHLY_ONLY_METRICS: list[str] = [
    "avg_daily_male",
    "avg_daily_female",
    "avg_daily_convicted_criminal",
    "avg_daily_possibly_under_18",
]
FY_ONLY_METRICS: list[str] = list(COLLATION_METRIC_TO_GOLD.values())
METRIC_COLUMNS: list[str] = [
    "avg_daily_population",
    *MONTHLY_ONLY_METRICS,
    *FY_ONLY_METRICS,
]

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "county_fips",
    "month",
    *METRIC_COLUMNS,
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "county_fips": pl.Utf8,
    "month": pl.Utf8,
    **{c: pl.Float64 for c in METRIC_COLUMNS},
    "guaranteed_minimum_beds": pl.Int64,
    "detail_level": pl.Utf8,
}

NATURAL_KEYS: list[str] = ["year", "month", "county_fips", "detail_level"]

MONTH_VALUES: list[str] = [f"{m:02d}" for m in range(1, 13)] + ["all"]

# Tolerance for the workbook-vs-collation verification (same floats parsed
# from the same source files through two text paths).
VERIFY_TOLERANCE = 0.005


# =============================================================================
# Shared helpers
# =============================================================================


def _normalize_name(col: str) -> pl.Expr:
    """Normalize a raw facility name for FACILITY_NAME_TO_CODE lookup."""
    return pl.col(col).str.to_uppercase().str.replace_all(r"\s+", " ").str.strip_chars()


def _null_aware_sum(col: str) -> pl.Expr:
    """Sum ignoring NULLs, but yield NULL (not 0) when every value is NULL.

    County/state aggregates cover the facilities that published values; a
    county whose facilities all lack a metric gets NULL, never a fake zero.
    """
    return (
        pl.when(pl.col(col).count() > 0).then(pl.col(col).sum()).otherwise(None)
    ).alias(col)


def _load_ga_crosswalk() -> pl.DataFrame:
    """Load GA rows of the facility -> county crosswalk (facility universe).

    The crosswalk (source == 'ddp_ice') is the maintained artifact mapping
    ICE DETLOC codes to county FIPS; its GA rows define which facilities in
    the (state-less) daily panel belong to Georgia.
    """
    xw = (
        pl.read_parquet(CROSSWALK_PATH)
        .filter((pl.col("source") == "ddp_ice") & (pl.col("state") == "GA"))
        .select("facility_id", "county_fips")
    )
    if xw.filter(pl.col("county_fips").is_null()).height:
        raise ValueError("facility_to_county has GA rows with NULL county_fips")
    # Every code the name map can produce must resolve in the crosswalk —
    # otherwise a facility would silently drop out of the county rollup.
    missing = sorted(set(FACILITY_NAME_TO_CODE.values()) - set(xw["facility_id"]))
    if missing:
        raise ValueError(
            "FACILITY_NAME_TO_CODE target codes missing from the crosswalk "
            f"(update src/etl/crosswalks/build_facility_to_county.py): {missing}"
        )
    return xw


# =============================================================================
# Feed 2a — DDP collation: fiscal-year facility rows
# =============================================================================


def transform_collation(manifest: TransformManifest) -> pl.DataFrame:
    """Parse the DDP Facilities collation into one row per GA facility-FY.

    Selection rule: per (fiscal_year, facility_code), keep the row from the
    LATEST file_date snapshot in which ICE published that facility that year
    (see module docstring — a plain latest-per-FY loses facilities dropped
    mid-year, e.g. Irwin County in FY2021).
    """
    # Direct pandas read: read_bronze_file only reads a file's FIRST sheet,
    # but this 23-sheet workbook keeps its data in the named 'Facilities'
    # sheet. All-string dtypes (the structure doc's infer_schema_length=0
    # guidance) + explicit strict=False casts below.
    pdf = pd.read_excel(COLLATION_FILE, sheet_name="Facilities", dtype=str)
    df = pl.from_pandas(pdf)
    manifest.record_file(
        COLLATION_FILE, 2026, "ddp_collation_facilities", df.height, df.columns
    )
    # Excel reads have raw/parsed parity (pandas drops no rows) — no-op record.
    manifest.record_read_loss(2026, COLLATION_FILE.name, df.height, df.height)

    # Scope: Georgia only. The State column is authoritative in this feed
    # (footnote prose rows and the one misaligned NV row carry non-GA/null
    # State and are excluded here as well).
    national = df.height
    df = df.filter(pl.col("state") == "GA")
    logger.info(
        "Collation: %d GA facility-snapshot rows kept of %d national "
        "(non-GA rows are out of topic scope)",
        df.height,
        national,
    )

    # Resolve drifting names to stable facility codes; unmapped names must
    # hard-stop (a new FY snapshot can introduce a new variant).
    df = df.with_columns(_normalize_name("name").alias("_name_norm"))
    df = df.with_columns(
        pl.col("_name_norm")
        .replace_strict(FACILITY_NAME_TO_CODE, default=None)
        .alias("facility_code")
    )
    unmapped = df.filter(pl.col("facility_code").is_null())
    if unmapped.height:
        raise ValueError(
            "Unmapped GA facility name(s) — add to FACILITY_NAME_TO_CODE: "
            f"{unmapped['_name_norm'].unique().sort().to_list()}"
        )
    manifest.record_categorical(
        column="facility_code",
        map_dict=FACILITY_NAME_TO_CODE,
        bronze_series=df["_name_norm"],
        gold_series=df["facility_code"],
    )

    # Cast metrics. guaranteed_minimum carries non-numeric "no contractual
    # floor" placeholders ('*', blank, NBSP) -> NULL via strict=False; count
    # and log them so the conversion is visible.
    gm_placeholders = df.filter(
        pl.col("guaranteed_minimum").is_not_null()
        & pl.col("guaranteed_minimum").cast(pl.Float64, strict=False).is_null()
    )
    if gm_placeholders.height:
        logger.info(
            "Collation: %d guaranteed_minimum placeholder value(s) -> NULL "
            "(no contractual floor): %s",
            gm_placeholders.height,
            gm_placeholders["guaranteed_minimum"].unique().to_list(),
        )
    df = df.with_columns(
        [
            pl.col(c).cast(pl.Float64, strict=False).alias(c)
            for c in COLLATION_METRIC_TO_GOLD
        ]
        + [
            pl.col("fiscal_year").cast(pl.Int32).alias("year"),
        ]
    )

    for row in df.group_by("year").len().sort("year").to_dicts():
        manifest.record_bronze(row["year"], row["len"])

    # Latest snapshot PER FACILITY per fiscal year (file_date is an ISO
    # datetime string — lexicographic max is chronological max).
    selected = (
        df.sort("file_date")
        .group_by("year", "facility_code", maintain_order=True)
        .last()
    )
    superseded = df.height - selected.height
    for row in (
        df.join(
            selected.select("year", "facility_code", "file_date"),
            on=["year", "facility_code", "file_date"],
            how="anti",
        )
        .group_by("year")
        .len()
        .sort("year")
        .to_dicts()
    ):
        manifest.record_filtered(
            row["year"], row["len"], "superseded_intra_fiscal_year_snapshot"
        )
    logger.info(
        "Collation: selected %d facility-FY rows (%d superseded snapshot rows dropped)",
        selected.height,
        superseded,
    )

    selected = selected.rename(COLLATION_METRIC_TO_GOLD).with_columns(
        # Total fiscal-year ADP: the gender x criminality family sums to the
        # facility's total ADP (each breakdown family does, to within 1e-6 —
        # verified across all GA facility-FYs in bronze analysis).
        (
            pl.col("adp_male_criminal")
            + pl.col("adp_male_noncriminal")
            + pl.col("adp_female_criminal")
            + pl.col("adp_female_noncriminal")
        ).alias("avg_daily_population"),
    )
    return selected.select(
        "year", "facility_code", "avg_daily_population", *FY_ONLY_METRICS
    )


# =============================================================================
# Feed 1 — ICE workbooks: verification of the collation-selected values
# =============================================================================


def _read_workbook_facilities(path: Path) -> pl.DataFrame:
    """Read a workbook's Facilities sheet (header-row position drifts).

    ``read_bronze_file`` cannot be used for these workbooks: it reads only a
    file's first sheet (here the methodology 'Header' sheet), while the data
    lives in a named sheet whose title carries FY suffixes and stray spaces
    (match on substring). The header row (first cell 'Name') sits at a
    different index per era, so it is located by scanning, never hardcoded.
    Excel reads have raw/parsed parity (pandas drops no rows), so read-loss
    accounting is a no-op for this feed.
    """
    xls = pd.ExcelFile(path)
    fac_names = [s for s in xls.sheet_names if "facilities" in s.lower()]
    if len(fac_names) != 1:
        raise ValueError(f"{path.name}: expected 1 Facilities sheet, got {fac_names}")
    # Parse ONLY the Facilities sheet (the other 5-12 sheets are national/AOR
    # aggregates, out of scope) with no header and all-string cells.
    raw = pl.from_pandas(xls.parse(fac_names[0], header=None, dtype=str))

    header_idx = next(
        (i for i, v in enumerate(raw[:, 0].to_list()) if str(v).strip() == "Name"),
        None,
    )
    if header_idx is None:
        raise ValueError(f"{path.name}: no header row with first cell 'Name'")
    header = [
        str(v).strip() if v is not None else f"_unnamed_{i}"
        for i, v in enumerate(raw.row(header_idx))
    ]
    data = raw.slice(header_idx + 1)
    data.columns = header
    return data


def verify_against_workbooks(fac_fy: pl.DataFrame, manifest: TransformManifest) -> None:
    """Hard-fail unless every workbook GA row matches its collation row.

    Feed 1 is the official ICE publication; the collation is DDP's parse of
    the same files. Every metric of every GA facility row in every workbook
    must equal the value this transform selected from the collation (the
    workbook facility set is the fiscal year's final snapshot — a subset of
    the per-facility-latest selection, which additionally recovers
    facilities dropped mid-year).
    """
    seen_hashes: dict[str, Path] = {}
    problems: list[str] = []
    for path in sorted(BRONZE_DIR.glob("ice_detention_stats_fy*.xlsx")):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen_hashes:
            # The two FY2025 files are byte-identical snapshots of the same
            # EOY publication — verify one, record the other as excluded.
            manifest.record_file(path, 2025, "EXCLUDED_duplicate_byte_identical", 0, [])
            logger.info(
                "EXCLUDED %s: byte-identical to %s",
                path.name,
                seen_hashes[digest].name,
            )
            continue
        seen_hashes[digest] = path

        fy = int(path.name.split("_fy")[1][:4])
        wb = _read_workbook_facilities(path)
        era = detect_era_by_columns(wb, WORKBOOK_ERA_SIGNATURES)
        if era is None:
            raise ValueError(f"{path.name}: no workbook era signature matched")
        manifest.record_file(
            path, fy, f"{era}_verification_only", wb.height, wb.columns
        )

        ga = wb.filter(pl.col("State") == "GA").with_columns(
            _normalize_name("Name").alias("_name_norm")
        )
        ga = ga.with_columns(
            pl.col("_name_norm")
            .replace_strict(FACILITY_NAME_TO_CODE, default=None)
            .alias("facility_code")
        )
        if ga.filter(pl.col("facility_code").is_null()).height:
            raise ValueError(
                f"{path.name}: unmapped GA facility name(s): "
                f"{ga.filter(pl.col('facility_code').is_null())['_name_norm'].to_list()}"
            )
        ga = ga.with_columns(
            [
                pl.col(raw_col)
                .cast(pl.Float64, strict=False)
                .alias(COLLATION_METRIC_TO_GOLD[coll_col])
                for raw_col, coll_col in WORKBOOK_TO_COLLATION.items()
            ]
        )

        joined = ga.join(
            fac_fy.filter(pl.col("year") == fy),
            on="facility_code",
            how="left",
            suffix="_sel",
        )
        for row in joined.to_dicts():
            if row["year"] is None:
                problems.append(
                    f"{path.name}: {row['facility_code']} absent from the "
                    "collation selection"
                )
                continue
            for gold_col in COLLATION_METRIC_TO_GOLD.values():
                wb_val, sel_val = row[gold_col], row[f"{gold_col}_sel"]
                if wb_val is None and sel_val is None:
                    continue
                if (
                    wb_val is None
                    or sel_val is None
                    or abs(wb_val - sel_val) > VERIFY_TOLERANCE
                ):
                    problems.append(
                        f"{path.name}: {row['facility_code']} {gold_col}: "
                        f"workbook={wb_val} vs collation-selected={sel_val}"
                    )
    if problems:
        raise ValueError(
            "Workbook-vs-collation verification failed "
            f"({len(problems)} mismatches):\n" + "\n".join(problems[:20])
        )
    logger.info(
        "Verification passed: every GA facility metric in every ICE workbook "
        "matches the collation-selected value (tolerance %s)",
        VERIFY_TOLERANCE,
    )


# =============================================================================
# Feed 2b — DDP daily population: monthly county rows
# =============================================================================


def transform_daily(
    manifest: TransformManifest, crosswalk: pl.DataFrame
) -> pl.DataFrame:
    """Aggregate the daily facility panel to county x fiscal-year x month.

    County-day totals are summed across the county's facilities, then
    averaged over the days of each complete calendar month. Every GA facility
    has a row for every panel day (verified: no gaps), so the county-day sum
    is never silently understated by missing facility-days.
    """
    df = pl.read_parquet(DAILY_FILE)
    manifest.record_file(
        DAILY_FILE, 2026, "ddp_daily_population", df.height, df.columns
    )
    manifest.record_read_loss(2026, DAILY_FILE.name, df.height, df.height)

    # Scope: Georgia facilities per the crosswalk (this panel has no state
    # column; crosswalk GA membership is the maintained, auditable universe).
    # Defensive: the inner join below silently drops any panel code missing
    # from the crosswalk. Georgia county-facility DETLOC codes end in "GA"
    # (hold rooms / BOP sites are a known static set already in the
    # crosswalk), so a new GA-suffixed code missing from the crosswalk must
    # fail loudly instead of vanishing from the county rollup.
    unmapped_ga = sorted(
        {
            c
            for c in df["detention_facility_code"].unique().to_list()
            if c and c.endswith("GA")
        }
        - set(crosswalk["facility_id"])
    )
    if unmapped_ga:
        raise ValueError(
            "Daily panel has GA-suffixed facility codes missing from the "
            "crosswalk (update src/etl/crosswalks/build_facility_to_county.py): "
            f"{unmapped_ga}"
        )
    national = df.height
    df = df.join(
        crosswalk,
        left_on="detention_facility_code",
        right_on="facility_id",
        how="inner",
    )
    logger.info(
        "Daily panel: %d GA facility-day rows kept of %d national",
        df.height,
        national,
    )
    # Record the panel's facility -> county recode too (merges with the
    # fiscal-year side's call, so the manifest covers every code that
    # contributed to gold, not just the workbook-published facilities).
    manifest.record_categorical(
        column="county_fips",
        map_dict=dict(crosswalk.iter_rows()),
        bronze_series=df["detention_facility_code"],
        gold_series=df["county_fips"],
    )

    df = df.with_columns(
        # Federal fiscal year: Oct-Dec belong to the NEXT labeled year.
        (pl.col("date").dt.year() + (pl.col("date").dt.month() >= 10).cast(pl.Int32))
        .cast(pl.Int32)
        .alias("year"),
        pl.col("date").dt.strftime("%m").alias("month"),
    )
    for row in df.group_by("year").len().sort("year").to_dicts():
        manifest.record_bronze(row["year"], row["len"])

    # Drop partial months at the panel edges: a mean over a fraction of a
    # month would masquerade as that month's average (2026-03: 10 of 31 days).
    coverage = (
        df.group_by("year", "month")
        .agg(
            pl.col("date").n_unique().alias("_days_observed"),
            pl.col("date").first().dt.month_end().dt.day().alias("_days_in_month"),
        )
        .with_columns(
            (pl.col("_days_observed") < pl.col("_days_in_month")).alias("_partial")
        )
    )
    partial = coverage.filter(pl.col("_partial"))
    if partial.height:
        for row in (
            df.join(partial.select("year", "month"), on=["year", "month"])
            .group_by("year")
            .len()
            .sort("year")
            .to_dicts()
        ):
            manifest.record_filtered(
                row["year"], row["len"], "partial_calendar_month_at_panel_edge"
            )
        logger.warning(
            "Dropped partial month(s) at the panel edge: %s",
            [
                f"FY{r['year']}-{r['month']} ({r['_days_observed']}/"
                f"{r['_days_in_month']} days)"
                for r in partial.sort("year", "month").to_dicts()
            ],
        )
        df = df.join(partial.select("year", "month"), on=["year", "month"], how="anti")

    # County-day totals across facilities, then the monthly mean of the
    # daily totals (equivalent to summing facility means on this gap-free
    # panel, but robust to partial facility coverage).
    county_day = df.group_by("county_fips", "year", "month", "date").agg(
        [pl.col(c).sum().alias(c) for c in DAILY_METRIC_TO_GOLD]
    )
    county_month = (
        county_day.group_by("county_fips", "year", "month")
        .agg([pl.col(c).mean().alias(g) for c, g in DAILY_METRIC_TO_GOLD.items()])
        .with_columns(pl.lit("county").alias("detail_level"))
    )
    logger.info(
        "Daily panel: %d county-month rows across %d counties",
        county_month.height,
        county_month["county_fips"].n_unique(),
    )
    return county_month


# =============================================================================
# Rollups
# =============================================================================


def build_county_fy_rows(
    fac_fy: pl.DataFrame, crosswalk: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Roll facility-FY rows up to county fiscal-year rows (month='all')."""
    df = fac_fy.join(
        crosswalk, left_on="facility_code", right_on="facility_id", how="left"
    )
    if df.filter(pl.col("county_fips").is_null()).height:
        raise ValueError("facility-FY rows with no county_fips after crosswalk join")
    manifest.record_categorical(
        column="county_fips",
        map_dict=dict(crosswalk.iter_rows()),
        bronze_series=df["facility_code"],
        gold_series=df["county_fips"],
    )
    return (
        df.group_by("year", "county_fips")
        .agg([_null_aware_sum(c) for c in ["avg_daily_population", *FY_ONLY_METRICS]])
        .with_columns(
            pl.lit("all").alias("month"),
            pl.lit("county").alias("detail_level"),
        )
    )


def build_state_rows(county_rows: pl.DataFrame, metrics: list[str]) -> pl.DataFrame:
    """Sum county rows to one statewide row per (year, month)."""
    return (
        county_rows.group_by("year", "month")
        .agg([_null_aware_sum(c) for c in metrics])
        .with_columns(
            pl.lit(None).cast(pl.Utf8).alias("county_fips"),
            pl.lit("state").alias("detail_level"),
        )
    )


def record_excluded_files(manifest: TransformManifest) -> None:
    """Record bronze files deliberately not ingested, with reasons."""
    for name, era in [
        ("detention-stays-latest.parquet", "EXCLUDED_pii_record_level_source"),
        ("detention-stints-latest.parquet", "EXCLUDED_pii_record_level_source"),
        ("ddp_codebook.html", "EXCLUDED_documentation"),
        ("ddp_codebook-facilities.html", "EXCLUDED_documentation"),
        ("ddp_codebook-facilities-daily-population.html", "EXCLUDED_documentation"),
    ]:
        path = DDP_DIR / name
        rows = (
            int(pl.scan_parquet(path).select(pl.len()).collect().item())
            if path.suffix == ".parquet"
            else 0
        )
        manifest.record_file(path, 2026, era, rows, [])
        logger.info("EXCLUDED %s (%s)", name, era)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for detention_population."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)
    record_excluded_files(manifest)

    crosswalk = _load_ga_crosswalk()

    # 1. Fiscal-year facility rows from the DDP collation, verified
    #    metric-by-metric against every ICE workbook (hard-fail on mismatch).
    fac_fy = transform_collation(manifest)
    verify_against_workbooks(fac_fy, manifest)

    # 2. County rollups: fiscal-year rows (month='all') + monthly rows.
    county_fy = build_county_fy_rows(fac_fy, crosswalk, manifest)
    county_month = transform_daily(manifest, crosswalk)

    # 3. Statewide rollups per row kind, then harmonize + concat.
    state_fy = build_state_rows(county_fy, ["avg_daily_population", *FY_ONLY_METRICS])
    state_month = build_state_rows(
        county_month, ["avg_daily_population", *MONTHLY_ONLY_METRICS]
    )
    combined = pl.concat(
        harmonize_columns(
            [county_month, state_month, county_fy, state_fy],
            STANDARD_COLUMNS,
            TARGET_TYPES,
        )
    )
    logger.info("Combined %d gold-shaped rows", combined.height)

    # Round the averaged/summed float metrics to 6 dp. polars runs the group_by
    # mean()/sum() aggregations multi-threaded, so float summation order (and
    # thus the last ~1e-13 ULP of a daily-mean or a statewide sum) varies run to
    # run — enough to change the parquet bytes and trip the approved-gold sha256
    # drift baseline on an otherwise-identical re-run. 6 dp is far below any
    # meaningful precision for a daily-population average and collapses the noise
    # to a deterministic value. guaranteed_minimum_beds is Int64 (not a metric).
    combined = combined.with_columns(
        [pl.col(c).round(6) for c in METRIC_COLUMNS]
    )

    months_seen = combined["month"]
    manifest.record_categorical(
        column="month",
        map_dict={m: m for m in MONTH_VALUES},
        bronze_series=months_seen,
        gold_series=months_seen,
    )

    # 4. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean an aggregation bug and must raise, not be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: collisions are impossible by construction (group_by outputs
    # on disjoint month/detail_level lanes); sort_col avg_daily_population is
    # the documented safety net — prefer the row with the larger non-null
    # headline metric should a future refresh introduce overlap.
    combined = deduplicate_by_levels(
        combined,
        {
            "county": ["year", "month", "county_fips"],
            "state": ["year", "month"],
        },
        sort_col="avg_daily_population",
    )

    # 5. Geography nulling (shared domain rules; state rows already NULL).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=CRIMINAL_JUSTICE_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. NULL-rate spikes are EXPECTED and structural: the
    # monthly metric family is NULL on every fiscal-year row (and monthly
    # rows only exist from FY2023, when the DDP daily panel begins), and the
    # fiscal-year ADP breakdowns are NULL on every monthly row.
    spike = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike.status == "warning":
        logger.warning(
            "NULL-rate spikes (documented structural cause — two metric "
            "families on one grain): %s",
            spike.details,
        )
    validate_output(combined, required_non_null=["year", "month", "detail_level"])

    # 6. Manifest stats on the FINAL DataFrame, then export.
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(
        combined,
        GOLD_DIR,
        STANDARD_COLUMNS,
        detail_level_files=COUNTY_DETAIL_LEVEL_FILES,
    )
    manifest.write(GOLD_DIR)

    # 7. Contract from the in-code column declaration.
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

    # 8. ALWAYS LAST: validate the gold just written against the contract
    # just emitted. Raises GoldValidationError -> non-zero exit.
    run_topic_validation(GOLD_DIR)


def _emit_contract(year_range: tuple[int, int]) -> None:
    """Emit the ODCS contract via ``write_data_dictionary``.

    The column declaration order MUST match STANDARD_COLUMNS minus
    ``detail_level``.
    """
    fy_only_null = (
        "Populated on fiscal-year rows (month = 'all') only; NULL on monthly "
        "rows. Also NULL where ICE did not publish the facility's breakdown "
        "(the FY2019 snapshot omits ADP for the two Folkston IPCs)."
    )
    monthly_only_null = (
        "Populated on monthly rows only (which begin October 2022 = FY2023, "
        "when the DDP daily panel starts); NULL on fiscal-year rows "
        "(month = 'all')."
    )
    adp_desc_suffix = (
        " Fiscal-YTD average daily population — fractional by construction "
        "(person-days divided by days elapsed in the fiscal year). For a "
        "facility ICE stopped using mid-year, the value is ICE's last "
        "published fiscal-YTD average for that year."
    )
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "ICE immigration-detention population held in Georgia facilities "
            "(Stewart Detention Center, the three Folkston ICE processing "
            "centers, Irwin County, Robert A. Deyton, federal prison "
            "holds, and county jails with intergovernmental agreements), "
            "rolled up to the county level. Fiscal-year rows (month = 'all', "
            "FY2019 onward) carry ICE's official average daily population "
            "(ADP) broken down three independent ways — security "
            "classification level, gender x criminality, and ICE threat "
            "level — plus ADP subject to mandatory detention and contractual "
            "guaranteed-minimum beds, sourced from the Deportation Data "
            "Project's collation of ICE's detention-management workbooks and "
            "verified against the ICE workbooks themselves. Monthly rows "
            "(FY2023 onward) carry monthly means of daily facility "
            "headcounts — total, by gender, convicted-criminal, and possibly "
            "under 18 — computed from the Deportation Data Project's "
            "FOIA-based daily facility population panel. The year column is "
            "the FEDERAL FISCAL YEAR (October 1 - September 30): monthly "
            "rows for October-December fall in the prior calendar year, and "
            "each fiscal year's 'all' row is the fiscal-year average, not a "
            "calendar-year one."
        ),
        title="ICE Detention Population by County",
        summary=(
            "Average daily ICE detention population in Georgia facilities by "
            "county, per federal fiscal year and month, with security, "
            "criminality, and threat-level breakdowns."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2025,
                "short_description": (
                    "Federal fiscal year (October 1 of the prior calendar "
                    "year through September 30)."
                ),
                "description": (
                    "FEDERAL FISCAL YEAR (October 1 - September 30), not the "
                    "calendar year: fiscal year 2025 spans 2024-10-01 to "
                    "2025-09-30. All metrics — the fiscal-year ADP averages "
                    "and the monthly means — are keyed to this fiscal "
                    "calendar. The current (latest) fiscal year is a "
                    "year-to-date snapshot, not a final full-year value: its "
                    "'all' row averages October 1 through ICE's latest "
                    "workbook snapshot date, and its monthly rows run "
                    "through the last complete month of the DDP daily panel."
                ),
            },
            {
                "name": "county_fips",
                "type": "string",
                "example": "13259",
                "null_meaning": "NULL on statewide rollup rows.",
                "description": (
                    "5-digit county FIPS code (state prefix 13) of the "
                    "county containing the detention facility or facilities; "
                    "FK to the counties dimension. NULL on statewide rollup "
                    "rows. Stewart Detention Center is 13259 (Stewart "
                    "County); the three Folkston ICE processing centers roll "
                    "up to 13049 (Charlton County); the Atlanta federal "
                    "penitentiary and hold rooms roll up to 13121 (Fulton "
                    "County). A county's value sums every ICE facility "
                    "located in it."
                ),
            },
            {
                "name": "month",
                "type": "string",
                "nullable": False,
                "example": "all",
                "validValues": MONTH_VALUES,
                "short_description": (
                    "Calendar month within the fiscal year ('01'-'12'), or "
                    "'all' for the fiscal-year-total row."
                ),
                "description": (
                    "Calendar month as a zero-padded string ('01'-'12'), or "
                    "'all' for the fiscal-year row. Months '10'-'12' belong "
                    "to the fiscal year's opening quarter and therefore fall "
                    "in the PRIOR calendar year (year=2025, month='11' is "
                    "November 2024). Monthly rows exist from FY2023 "
                    "(October 2022) onward — the extent of the DDP daily "
                    "panel — and cover complete calendar months only "
                    "(a trailing partial month is dropped, e.g. March 2026 "
                    "with 10 of 31 days published). Fiscal-year 'all' rows "
                    "exist for every year from FY2019."
                ),
            },
            {
                "name": "avg_daily_population",
                "type": "float64",
                "unit": "count",
                "key_metric": True,
                "example": 2025.8,
                "null_meaning": (
                    "NULL only where ICE published no ADP for any of the "
                    "county's facilities that fiscal year (FY2019 Folkston "
                    "IPCs)."
                ),
                "short_description": (
                    "Average daily ICE detention population across the "
                    "county's facilities (fractional: an average, not a "
                    "headcount)."
                ),
                "description": (
                    "Average daily detained population, summed across the "
                    "county's ICE facilities. The only metric populated on "
                    "both row kinds. On fiscal-year rows (month='all') it is "
                    "ICE's official fiscal-YTD ADP (the sum of the four "
                    "gender x criminality ADP components, each of ICE's "
                    "three published breakdowns sums to total ADP). On "
                    "monthly rows it is the monthly mean of the DDP daily "
                    "panel's n_detained (distinct individuals detained at "
                    "any point in the day) — this definition reproduces "
                    "ICE's fiscal-year ADP to within about 2 percent. "
                    "Values are fractional averages; never round them to "
                    "headcounts."
                ),
            },
            {
                "name": "avg_daily_male",
                "type": "float64",
                "unit": "count",
                "example": 1758.3,
                "null_meaning": monthly_only_null,
                "description": (
                    "Monthly mean of the daily count of detained people "
                    "ICE records as male." + " " + monthly_only_null + " "
                    "avg_daily_male + avg_daily_female can fall slightly "
                    "short of avg_daily_population (gender occasionally "
                    "unrecorded); it never exceeds it."
                ),
            },
            {
                "name": "avg_daily_female",
                "type": "float64",
                "unit": "count",
                "example": 155.0,
                "null_meaning": monthly_only_null,
                "description": (
                    "Monthly mean of the daily count of detained people ICE "
                    "records as female. " + monthly_only_null
                ),
            },
            {
                "name": "avg_daily_convicted_criminal",
                "type": "float64",
                "unit": "count",
                "example": 590.2,
                "null_meaning": monthly_only_null,
                "description": (
                    "Monthly mean of the daily count of detained people with "
                    "a criminal conviction (ICE's classification). " + monthly_only_null
                ),
            },
            {
                "name": "avg_daily_possibly_under_18",
                "type": "float64",
                "unit": "count",
                "example": 0.1,
                "null_meaning": monthly_only_null,
                "description": (
                    "Monthly mean of the daily count of detained people DDP "
                    "flags as possibly under 18 (based on recorded birth "
                    "year). Near zero at Georgia facilities. " + monthly_only_null
                ),
            },
            {
                "name": "adp_security_level_a",
                "type": "float64",
                "unit": "count",
                "example": 1022.4,
                "null_meaning": fy_only_null,
                "description": (
                    "ADP of detainees classified at security level A (lowest "
                    "custody level of ICE's A-D classification)." + adp_desc_suffix
                ),
            },
            {
                "name": "adp_security_level_b",
                "type": "float64",
                "unit": "count",
                "example": 300.5,
                "null_meaning": fy_only_null,
                "description": (
                    "ADP of detainees classified at security level B." + adp_desc_suffix
                ),
            },
            {
                "name": "adp_security_level_c",
                "type": "float64",
                "unit": "count",
                "example": 350.9,
                "null_meaning": fy_only_null,
                "description": (
                    "ADP of detainees classified at security level C." + adp_desc_suffix
                ),
            },
            {
                "name": "adp_security_level_d",
                "type": "float64",
                "unit": "count",
                "example": 352.0,
                "null_meaning": fy_only_null,
                "description": (
                    "ADP of detainees classified at security level D "
                    "(highest custody level)." + adp_desc_suffix
                ),
            },
            {
                "name": "adp_male_criminal",
                "type": "float64",
                "unit": "count",
                "example": 539.4,
                "null_meaning": fy_only_null,
                "description": (
                    "ADP of male detainees with a criminal conviction (ICE's "
                    "'Male Crim' category)." + adp_desc_suffix
                ),
            },
            {
                "name": "adp_male_noncriminal",
                "type": "float64",
                "unit": "count",
                "example": 1161.3,
                "null_meaning": fy_only_null,
                "description": (
                    "ADP of male detainees without a criminal conviction."
                    + adp_desc_suffix
                ),
            },
            {
                "name": "adp_female_criminal",
                "type": "float64",
                "unit": "count",
                "example": 57.4,
                "null_meaning": fy_only_null,
                "description": (
                    "ADP of female detainees with a criminal conviction."
                    + adp_desc_suffix
                ),
            },
            {
                "name": "adp_female_noncriminal",
                "type": "float64",
                "unit": "count",
                "example": 267.7,
                "null_meaning": fy_only_null,
                "description": (
                    "ADP of female detainees without a criminal conviction. "
                    "The four gender x criminality components sum to "
                    "avg_daily_population on fiscal-year rows." + adp_desc_suffix
                ),
            },
            {
                "name": "adp_threat_level_1",
                "type": "float64",
                "unit": "count",
                "example": 200.3,
                "null_meaning": fy_only_null,
                "description": (
                    "ADP of detainees at ICE threat level 1 (highest-priority "
                    "criminal history under ICE's 1-3 scheme)." + adp_desc_suffix
                ),
            },
            {
                "name": "adp_threat_level_2",
                "type": "float64",
                "unit": "count",
                "example": 120.5,
                "null_meaning": fy_only_null,
                "description": (
                    "ADP of detainees at ICE threat level 2." + adp_desc_suffix
                ),
            },
            {
                "name": "adp_threat_level_3",
                "type": "float64",
                "unit": "count",
                "example": 150.7,
                "null_meaning": fy_only_null,
                "description": (
                    "ADP of detainees at ICE threat level 3." + adp_desc_suffix
                ),
            },
            {
                "name": "adp_no_threat_level",
                "type": "float64",
                "unit": "count",
                "example": 1554.3,
                "null_meaning": fy_only_null,
                "description": (
                    "ADP of detainees with no ICE threat level (no known "
                    "criminal history). The four threat-level components sum "
                    "to avg_daily_population on fiscal-year rows." + adp_desc_suffix
                ),
            },
            {
                "name": "adp_mandatory_detention",
                "type": "float64",
                "unit": "count",
                "example": 1345.7,
                "null_meaning": fy_only_null,
                "description": (
                    "ADP of detainees subject to mandatory detention (a "
                    "subset of total ADP, not a member of a partition)."
                    + adp_desc_suffix
                ),
            },
            {
                "name": "guaranteed_minimum_beds",
                "type": "int64",
                "unit": "count",
                "example": 1600,
                "null_meaning": (
                    "NULL when no facility in the county has a contractual "
                    "guaranteed-minimum bed count that fiscal year (ICE "
                    "publishes a blank or placeholder), and on all monthly "
                    "rows."
                ),
                "description": (
                    "Contractual guaranteed-minimum beds (the bed floor ICE "
                    "pays for regardless of occupancy), summed over the "
                    "county's facilities that have one. Fiscal-year rows "
                    "only. Not a population count — compare with "
                    "avg_daily_population to gauge contract utilization."
                ),
            },
        ],
        source=(
            "U.S. Immigration and Customs Enforcement detention statistics "
            "(via the Deportation Data Project)"
        ),
        source_url=SOURCE_URL,
        update_frequency="biweekly (ICE workbook snapshots); irregular (DDP releases)",
        year_range=year_range,
        suppressed_to_null=False,
        usage=(
            "Cite both sources per the Deportation Data Project's "
            "requirement: fiscal-year rows are 'government statistics "
            "published by ICE, collated by the Deportation Data Project, and "
            "analyzed by Georgia Civic Data'; monthly rows are 'government "
            "data provided by ICE in response to a FOIA request, processed "
            "by the Deportation Data Project, and analyzed by Georgia Civic "
            "Data'. Filter month = 'all' for fiscal-year ADP series and "
            "month != 'all' for the monthly series — the two families come "
            "from different publications and reconcile only approximately "
            "(within about 2 percent). Remember the year column is the "
            "federal fiscal year: October-December monthly rows fall in the "
            "prior calendar year."
        ),
        limitations=(
            "State rows have NULL county_fips. The year column is the "
            "FEDERAL FISCAL YEAR (Oct 1 - Sep 30). The latest fiscal year is "
            "a year-to-date snapshot (its 'all' row averages Oct 1 through "
            "ICE's latest biweekly workbook snapshot; ICE also silently "
            "revises closed years). Fiscal-year rows cover the facilities "
            "ICE published each year (6-9 in Georgia); a facility ICE "
            "stopped using mid-year keeps its last published fiscal-YTD "
            "value (e.g. Irwin County FY2021, absent from ICE's end-of-year "
            "workbook, is recovered from its final intra-year snapshot). "
            "Monthly rows cover FY2023 onward only (the DDP daily panel "
            "starts 2022-10-01) and always include all 14 counties that "
            "ever held ICE detainees in the panel — county jails with "
            "dormant agreements carry real zeros, not missing data. The "
            "FY2019 snapshot omits ADP for the two Folkston IPCs "
            "(guaranteed-minimum beds only). Average length of stay and "
            "book-in counts are deliberately not served: neither aggregates "
            "correctly from facility publications to county grain without "
            "record-level weights. No values are suppressed; NULL means ICE "
            "published no value for that cell's source."
        ),
        quality_checks=[
            {
                "name": "monthly_metrics_null_on_fiscal_year_rows",
                "description": (
                    "The daily-panel metric family exists only on monthly "
                    "rows — every fiscal-year ('all') row must carry NULL "
                    "for all four monthly-only metrics."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE month = 'all' AND ("
                    + " OR ".join(f"{c} IS NOT NULL" for c in MONTHLY_ONLY_METRICS)
                    + ")"
                ),
                "mustBe": 0,
            },
            {
                "name": "fiscal_year_metrics_null_on_monthly_rows",
                "description": (
                    "The ICE workbook ADP breakdowns are fiscal-year values "
                    "— every monthly row must carry NULL for all fourteen "
                    "fiscal-year-only metrics."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE month != 'all' AND ("
                    + " OR ".join(f"{c} IS NOT NULL" for c in FY_ONLY_METRICS)
                    + ")"
                ),
                "mustBe": 0,
            },
            {
                "name": "monthly_rows_start_fy2023",
                "description": (
                    "Monthly rows exist only from FY2023 (the DDP daily "
                    "panel starts 2022-10-01, which is fiscal year 2023) — "
                    "guards the October-December fiscal-year attribution: a "
                    "regression in the +1 FY logic would land Oct-Dec 2022 "
                    "rows at year=2022."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} "
                    "WHERE month != 'all' AND year < 2023"
                ),
                "mustBe": 0,
            },
            {
                "name": "adp_gender_criminality_partition_sums_to_total",
                "description": (
                    "ICE's gender x criminality breakdown partitions total "
                    "ADP — the four components must sum to "
                    "avg_daily_population on fiscal-year rows (tolerance "
                    "0.05 for float aggregation)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE month = 'all' "
                    "AND avg_daily_population IS NOT NULL "
                    "AND adp_male_criminal IS NOT NULL "
                    "AND adp_male_noncriminal IS NOT NULL "
                    "AND adp_female_criminal IS NOT NULL "
                    "AND adp_female_noncriminal IS NOT NULL "
                    "AND ABS(adp_male_criminal + adp_male_noncriminal + "
                    "adp_female_criminal + adp_female_noncriminal - "
                    "avg_daily_population) > 0.05"
                ),
                "mustBe": 0,
            },
            {
                "name": "adp_security_level_partition_sums_to_total",
                "description": (
                    "ICE's security-level breakdown partitions total ADP — "
                    "levels A-D must sum to avg_daily_population on "
                    "fiscal-year rows (verified to 1e-6 at the facility "
                    "level; tolerance 0.05 after county/state aggregation)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE month = 'all' "
                    "AND avg_daily_population IS NOT NULL "
                    "AND adp_security_level_a IS NOT NULL "
                    "AND adp_security_level_b IS NOT NULL "
                    "AND adp_security_level_c IS NOT NULL "
                    "AND adp_security_level_d IS NOT NULL "
                    "AND ABS(adp_security_level_a + adp_security_level_b + "
                    "adp_security_level_c + adp_security_level_d - "
                    "avg_daily_population) > 0.05"
                ),
                "mustBe": 0,
            },
            {
                "name": "adp_threat_level_partition_sums_to_total",
                "description": (
                    "ICE's threat-level breakdown partitions total ADP — "
                    "levels 1-3 plus no-threat-level must sum to "
                    "avg_daily_population on fiscal-year rows (tolerance "
                    "0.05)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE month = 'all' "
                    "AND avg_daily_population IS NOT NULL "
                    "AND adp_threat_level_1 IS NOT NULL "
                    "AND adp_threat_level_2 IS NOT NULL "
                    "AND adp_threat_level_3 IS NOT NULL "
                    "AND adp_no_threat_level IS NOT NULL "
                    "AND ABS(adp_threat_level_1 + adp_threat_level_2 + "
                    "adp_threat_level_3 + adp_no_threat_level - "
                    "avg_daily_population) > 0.05"
                ),
                "mustBe": 0,
            },
            {
                "name": "adp_mandatory_within_total",
                "description": (
                    "Detainees subject to mandatory detention are a subset "
                    "of the detained population — adp_mandatory_detention "
                    "can never exceed avg_daily_population."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE month = 'all' "
                    "AND adp_mandatory_detention IS NOT NULL "
                    "AND avg_daily_population IS NOT NULL "
                    "AND adp_mandatory_detention > avg_daily_population + 0.05"
                ),
                "mustBe": 0,
            },
            {
                "name": "monthly_gender_split_within_total",
                "description": (
                    "The daily panel's gender counts never exceed the total "
                    "(they can fall slightly short when gender is "
                    "unrecorded) — avg_daily_male + avg_daily_female must "
                    "not exceed avg_daily_population on monthly rows."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE month != 'all' "
                    "AND avg_daily_male IS NOT NULL "
                    "AND avg_daily_female IS NOT NULL "
                    "AND avg_daily_population IS NOT NULL "
                    "AND avg_daily_male + avg_daily_female > "
                    "avg_daily_population + 0.01"
                ),
                "mustBe": 0,
            },
            {
                "name": "monthly_subset_metrics_within_total",
                "description": (
                    "Convicted-criminal and possibly-under-18 counts are "
                    "subsets of the detained population — neither monthly "
                    "mean can exceed avg_daily_population."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE month != 'all' "
                    "AND avg_daily_population IS NOT NULL AND ("
                    "(avg_daily_convicted_criminal IS NOT NULL AND "
                    "avg_daily_convicted_criminal > avg_daily_population + 0.01) "
                    "OR (avg_daily_possibly_under_18 IS NOT NULL AND "
                    "avg_daily_possibly_under_18 > avg_daily_population + 0.01))"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_adp_equals_sum_of_counties",
                "description": (
                    "Statewide rows are built by summing the county rows — "
                    "the state avg_daily_population must equal the county "
                    "sum for every (year, month) (tolerance 0.01 for float "
                    "re-aggregation)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, month, "
                    "MAX(CASE WHEN county_fips IS NULL THEN "
                    "avg_daily_population END) AS state_total, "
                    "SUM(CASE WHEN county_fips IS NOT NULL THEN "
                    "avg_daily_population END) AS county_sum "
                    "FROM {object} GROUP BY year, month"
                    ") WHERE state_total IS NOT NULL AND county_sum IS NOT "
                    "NULL AND ABS(state_total - county_sum) > 0.01"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
