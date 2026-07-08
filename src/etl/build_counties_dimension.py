"""Build the global counties dimension table.

Produces data/gold/_dimensions/counties.parquet from the maintained Census
crosswalk (data/gold/crosswalks/ga_census_crosswalk.parquet): one row per
Georgia county with its 5-digit FIPS code and title-case name.

Usage:
    uv run python -m src.etl.build_counties_dimension
"""

import logging
import re
from pathlib import Path

import polars as pl

from src.utils.crosswalks import (
    check_county_overrides,
    load_census_crosswalk,
    load_counties_dimension,
)
from src.utils.dimension_contract_emitter import emit_counties_contract

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data/gold/_dimensions")
OUTPUT_FILE = OUTPUT_DIR / "counties.parquet"

GA_COUNTY_COUNT = 159
_FIPS_PATTERN = re.compile(r"^13\d{3}$")


class DimensionBuildError(RuntimeError):
    """Raised when the freshly built dimension fails its health assertions."""


def build_counties_dimension() -> pl.DataFrame:
    """Build the counties dimension DataFrame from the Census crosswalk.

    The crosswalk's county_name values carry a trailing ' GA' state suffix
    (e.g. 'Fulton GA') which is stripped; names are otherwise already title
    case.
    """
    crosswalk = load_census_crosswalk()
    df = (
        crosswalk.select(
            pl.col("county").alias("county_fips"),
            pl.col("county_name")
            .str.replace(r"\s+GA$", "")
            .str.strip_chars()
            .alias("county_name"),
        )
        .unique()
        .sort("county_fips")
    )
    return df


def _assert_counties_health(df: pl.DataFrame) -> None:
    """Hard gates: exactly 159 counties, unique 5-digit '13'-prefixed PK."""
    if df.height != GA_COUNTY_COUNT:
        raise DimensionBuildError(
            f"counties: expected {GA_COUNTY_COUNT} rows, got {df.height}"
        )
    dupes = df.filter(pl.col("county_fips").is_duplicated())
    if dupes.height > 0:
        raise DimensionBuildError(
            f"counties: duplicate FIPS codes: {dupes['county_fips'].to_list()}"
        )
    bad_fips = [
        v for v in df["county_fips"].to_list() if not v or not _FIPS_PATTERN.match(v)
    ]
    if bad_fips:
        raise DimensionBuildError(f"counties: malformed FIPS codes: {bad_fips}")
    empty_names = df.filter(
        pl.col("county_name").is_null() | (pl.col("county_name").str.len_chars() == 0)
    )
    if empty_names.height > 0:
        raise DimensionBuildError(
            f"counties: empty names for: {empty_names['county_fips'].to_list()}"
        )


def main() -> None:
    """Build and export the counties dimension table."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    df = build_counties_dimension()
    _assert_counties_health(df)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.write_parquet(OUTPUT_FILE)
    logger.info(f"Wrote {df.height} counties to {OUTPUT_FILE}")

    # The override self-test needs the parquet just written (lru-cached loader
    # may hold a stale copy from an earlier call in the same process).
    load_counties_dimension.cache_clear()
    problems = check_county_overrides()
    if problems:
        raise DimensionBuildError(
            "counties: COUNTY_NAME_OVERRIDES problems: " + "; ".join(problems)
        )
    logger.info("COUNTY_NAME_OVERRIDES targets all resolve")

    # Emit the git-tracked ODCS contract for the global counties dimension.
    contract = emit_counties_contract()
    logger.info(f"Emitted counties dimension contract to {contract}")

    # Run the contract's own quality SQL against the parquet just written.
    from src.utils import contract_reader
    from src.utils.validators import check_contract_quality_sql

    result = check_contract_quality_sql(
        OUTPUT_FILE, contract_reader.load_contract(contract)
    )
    if result.status == "fail":
        raise DimensionBuildError(
            f"counties: contract quality checks failed — "
            f"{result.details or [result.message]}"
        )
    logger.info(f"counties.parquet: {result.message}")


if __name__ == "__main__":
    main()
