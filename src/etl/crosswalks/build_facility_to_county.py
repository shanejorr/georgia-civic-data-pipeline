"""Build the facility -> county FIPS crosswalk.

Produces data/gold/crosswalks/facility_to_county.parquet (+ .csv) from two
bronze snapshots under data/bronze/_crosswalks/facility_to_county/:

- Deportation Data Project facilities file (``ddp_facilities-latest.parquet``):
  ICE detention facilities keyed by ``detention_facility_code`` — the facility
  identifier used across ICE workbooks and DDP record-level files — with
  county FIPS per facility. National coverage kept so ICE transforms can join
  first and filter to Georgia after.
- Archived HIFLD Prison Boundaries layer
  (``hifld_prison_boundaries.zstd.parquet``): state/county/federal facilities
  (prisons, jails, ICE centers) keyed by HIFLD ``FACILITYID``. Georgia rows
  only — kept for GDC/jail facility mapping in later topics.

The two ID namespaces are disambiguated by the ``source`` column
(``ddp_ice`` / ``hifld``). Georgia rows are validated against the global
counties dimension.

Usage:
    uv run python -m src.etl.crosswalks.build_facility_to_county
"""

import logging
from pathlib import Path

import polars as pl

from src.utils.crosswalks import load_counties_dimension

logger = logging.getLogger(__name__)

BRONZE_DIR = Path("data/bronze/_crosswalks/facility_to_county")
DDP_FILE = BRONZE_DIR / "ddp_facilities-latest.parquet"
HIFLD_FILE = BRONZE_DIR / "hifld_prison_boundaries.zstd.parquet"

OUTPUT_DIR = Path("data/gold/crosswalks")
OUTPUT_PARQUET = OUTPUT_DIR / "facility_to_county.parquet"
OUTPUT_CSV = OUTPUT_DIR / "facility_to_county.csv"

STANDARD_COLUMNS = [
    "facility_id",
    "facility_name",
    "facility_type",
    "source",
    "city",
    "state",
    "county_fips",
]


class CrosswalkBuildError(RuntimeError):
    """Raised when the freshly built crosswalk fails its health assertions."""


# Facilities the DDP source leaves un-geocoded (NULL county_fips_code).
# SAVHOLD is the ICE hold room in Savannah — the Chatham County seat.
FACILITY_FIPS_OVERRIDES: dict[str, str] = {
    "SAVHOLD": "13051",
}

# Georgia ICE facilities absent from the DDP facilities snapshot entirely
# (their stints rows carry NULL state, so DDP never geocoded them), but that
# appear in the ICE detention workbooks and/or the DDP daily-population panel
# with real (small) populations. Verified against the DDP stints file
# (detention_facility names) and the ICE FY workbooks on 2026-07-02.
SUPPLEMENTAL_DDP_FACILITIES: list[dict[str, str]] = [
    # Whitfield County Jail, Dalton GA — in ICE FY2022 workbook (State=GA)
    # and FY2019/FY2021/FY2022 detention-management snapshots.
    {
        "facility_id": "WHITFGA",
        "facility_name": "Whitfield County Jail",
        "city": "Dalton",
        "state": "GA",
        "county_fips": "13313",
    },
    # DeKalb County Jail, Decatur GA — daily-population panel (max 1 detainee).
    {
        "facility_id": "DEKABGA",
        "facility_name": "DeKalb County Jail",
        "city": "Decatur",
        "state": "GA",
        "county_fips": "13089",
    },
    # D. Ray James Prison, Folkston GA (BOP contract facility on the Folkston
    # campus; closed 2021, distinct DETLOC from the FIPC* processing centers).
    {
        "facility_id": "GADRYJM",
        "facility_name": "D. Ray James Prison",
        "city": "Folkston",
        "state": "GA",
        "county_fips": "13049",
    },
]


def _ddp_facilities() -> pl.DataFrame:
    """ICE facilities from the DDP snapshot (national, one row per code)."""
    df = pl.read_parquet(DDP_FILE)
    return df.select(
        pl.col("detention_facility_code").alias("facility_id"),
        pl.col("name").alias("facility_name"),
        pl.lit("ICE_DETENTION").alias("facility_type"),
        pl.lit("ddp_ice").alias("source"),
        pl.col("city"),
        pl.col("state"),
        pl.col("county_fips_code").alias("county_fips"),
    ).filter(pl.col("facility_id").is_not_null())


def _apply_fips_overrides(df: pl.DataFrame) -> pl.DataFrame:
    """Fill county_fips for facilities the source leaves un-geocoded."""
    facility_id = pl.col("facility_id")
    return df.with_columns(
        pl.when(pl.col("county_fips").is_null())
        .then(facility_id.replace_strict(FACILITY_FIPS_OVERRIDES, default=None))
        .otherwise(pl.col("county_fips"))
        .alias("county_fips")
    )


def _hifld_ga_facilities() -> pl.DataFrame:
    """Georgia prison/jail facilities from the archived HIFLD layer."""
    df = pl.read_parquet(HIFLD_FILE)
    return (
        df.filter(pl.col("STATE") == "GA")
        .select(
            pl.col("FACILITYID").cast(pl.Utf8).alias("facility_id"),
            pl.col("NAME").alias("facility_name"),
            pl.col("TYPE").alias("facility_type"),
            pl.lit("hifld").alias("source"),
            pl.col("CITY").alias("city"),
            pl.col("STATE").alias("state"),
            pl.col("COUNTYFIPS").cast(pl.Utf8).alias("county_fips"),
        )
        .filter(pl.col("facility_id").is_not_null())
    )


def _supplemental_ddp_facilities() -> pl.DataFrame:
    """Manually curated GA facilities missing from the DDP snapshot."""
    return (
        pl.DataFrame(SUPPLEMENTAL_DDP_FACILITIES)
        .with_columns(
            pl.lit("ICE_DETENTION").alias("facility_type"),
            pl.lit("ddp_ice").alias("source"),
        )
        .select(STANDARD_COLUMNS)
    )


def build_facility_to_county() -> pl.DataFrame:
    """Combine the two sources into one crosswalk frame."""
    ddp = _ddp_facilities()
    supplemental = _supplemental_ddp_facilities().filter(
        # Defensive: if a future DDP snapshot starts covering these codes,
        # the snapshot row wins and the manual row is dropped.
        ~pl.col("facility_id").is_in(ddp["facility_id"].implode())
    )
    df = pl.concat(
        [ddp, supplemental.select(ddp.columns), _hifld_ga_facilities()],
        how="vertical",
    )
    df = _apply_fips_overrides(df)
    return df.select(STANDARD_COLUMNS).sort(["source", "facility_id"])


def _assert_health(df: pl.DataFrame) -> None:
    """Hard gates: unique (source, facility_id); GA FIPS resolve to the dim."""
    dupes = df.filter(pl.struct(["source", "facility_id"]).is_duplicated())
    if dupes.height > 0:
        raise CrosswalkBuildError(
            "facility_to_county: duplicate (source, facility_id) rows: "
            f"{dupes.select(['source', 'facility_id']).head(10).rows()}"
        )

    counties = set(load_counties_dimension()["county_fips"].to_list())
    ga = df.filter(pl.col("state") == "GA")
    bad = ga.filter(
        pl.col("county_fips").is_null() | ~pl.col("county_fips").is_in(counties)
    )
    if bad.height > 0:
        raise CrosswalkBuildError(
            f"facility_to_county: {bad.height} GA rows with county_fips not in "
            "the counties dimension: "
            + str(
                bad.select(["facility_id", "facility_name", "county_fips"])
                .head(10)
                .rows()
            )
        )
    # The two anchor ICE facilities must be present and correctly mapped.
    anchors = {"STEWART": "13259", "FOLKSTON": "13049"}
    for name_fragment, fips in anchors.items():
        hit = ga.filter(
            pl.col("facility_name").str.to_uppercase().str.contains(name_fragment)
            & (pl.col("county_fips") == fips)
        )
        if hit.height == 0:
            raise CrosswalkBuildError(
                f"facility_to_county: anchor facility '{name_fragment}' not "
                f"found with county_fips={fips}"
            )


def main() -> None:
    """Build and export the facility_to_county crosswalk."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    df = build_facility_to_county()
    _assert_health(df)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.write_parquet(OUTPUT_PARQUET)
    df.write_csv(OUTPUT_CSV)

    ga_count = df.filter(pl.col("state") == "GA").height
    logger.info(
        f"Wrote {df.height} facilities ({ga_count} GA) to {OUTPUT_PARQUET} "
        f"and {OUTPUT_CSV}"
    )


if __name__ == "__main__":
    main()
