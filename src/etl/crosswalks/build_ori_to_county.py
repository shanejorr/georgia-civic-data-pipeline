"""Build the FBI ORI -> county FIPS crosswalk for Georgia agencies.

Produces data/gold/crosswalks/ori_to_county.parquet (+ .csv) from two bronze
snapshots:

- CDE agency roster (``data/bronze/_crosswalks/ori_to_county/
  cde_agency_by_state_abbr_ga.json``): the FBI Crime Data Explorer's own GA
  agency list — ORI, agency name/type, county assignment(s), NIBRS start date.
- LEE master file (``data/bronze/criminal_justice/fbi_cde/
  law_enforcement_employees/lee_1960_2025.csv``): agency×year employee counts
  whose GA rows carry a ``county_name`` per ORI — covers historical ORIs that
  have dropped off the current roster.

Some agencies span multiple counties (comma-joined in both sources, e.g.
"BARROW, GWINNETT, HALL, JACKSON"). The crosswalk keeps ONE row per ORI:
``county_fips`` is the first-listed (primary) county — use it for county
rollups so agency totals are never double-counted — and ``all_county_fips``
carries the full pipe-joined list with a ``multi_county`` flag.

Usage:
    uv run python -m src.etl.crosswalks.build_ori_to_county
"""

import json
import logging
import re
from pathlib import Path

import polars as pl

from src.utils.crosswalks import (
    COUNTY_NAME_OVERRIDES,
    load_counties_dimension,
    normalize_county_name_expr,
)

logger = logging.getLogger(__name__)

ROSTER_FILE = Path(
    "data/bronze/_crosswalks/ori_to_county/cde_agency_by_state_abbr_ga.json"
)
LEE_FILE = Path(
    "data/bronze/criminal_justice/fbi_cde/law_enforcement_employees/lee_1960_2025.csv"
)

OUTPUT_DIR = Path("data/gold/crosswalks")
OUTPUT_PARQUET = OUTPUT_DIR / "ori_to_county.parquet"
OUTPUT_CSV = OUTPUT_DIR / "ori_to_county.csv"


class CrosswalkBuildError(RuntimeError):
    """Raised when the freshly built crosswalk fails its health assertions."""


def _roster_agencies() -> pl.DataFrame:
    """GA agencies from the CDE roster JSON (dict keyed by county string)."""
    raw = json.loads(ROSTER_FILE.read_text())
    rows = []
    for agencies in raw.values():
        for a in agencies:
            rows.append(
                {
                    "ori": a["ori"],
                    "agency_name": a.get("agency_name"),
                    "agency_type": a.get("agency_type_name"),
                    "counties_raw": a.get("counties"),
                    "is_nibrs": bool(a.get("is_nibrs")),
                    "nibrs_start_date": a.get("nibrs_start_date"),
                }
            )
    # The same agency appears once per county key it spans; counties_raw is
    # identical on each copy, so plain unique() collapses them.
    return pl.DataFrame(rows).unique(subset=["ori"], keep="first")


def _lee_agencies() -> pl.DataFrame:
    """GA ORIs from the LEE master file — latest year's county per ORI."""
    lee = (
        pl.scan_csv(LEE_FILE, infer_schema_length=10000)
        .filter(pl.col("state_abbr") == "GA")
        .select(
            ["ori", "pub_agency_name", "agency_type_name", "county_name", "data_year"]
        )
        .collect()
    )
    return (
        lee.sort("data_year", descending=True)
        .unique(subset=["ori"], keep="first")
        .select(
            pl.col("ori"),
            pl.col("pub_agency_name").alias("lee_agency_name"),
            pl.col("agency_type_name").alias("lee_agency_type"),
            pl.col("county_name").alias("lee_counties_raw"),
        )
    )


def _county_name_to_fips_map() -> dict[str, str]:
    """Normalized county name -> FIPS from the dimension + manual overrides."""
    counties = load_counties_dimension()
    lookup = counties.select(
        normalize_county_name_expr("county_name").alias("name"),
        pl.col("county_fips"),
    )
    mapping = dict(lookup.iter_rows())
    for source_name, target in COUNTY_NAME_OVERRIDES.items():
        if target in mapping:
            mapping[source_name] = mapping[target]
    return mapping


# Primary-county overrides for multi-county agencies whose ORI carries no
# numeric county ordinal. Atlanta PD spans DeKalb + Fulton; its seat and the
# overwhelming majority of its jurisdiction are Fulton.
ORI_PRIMARY_OVERRIDES: dict[str, str] = {
    "GAAPD0000": "13121",
}


def _ordinal_to_fips_map() -> dict[int, str]:
    """FBI ORI county ordinal (GA{NNN}...) -> county FIPS.

    Georgia ORIs embed the county's ordinal in the official alphabetical
    ordering, which is exactly the FIPS-ascending order of the 159 counties
    (verified empirically: 708/710 single-county agencies match; the 2
    exceptions are roster quirks where the roster's own county wins anyway).
    """
    counties = load_counties_dimension().sort("county_fips")
    return {i + 1: fips for i, fips in enumerate(counties["county_fips"].to_list())}


def build_ori_to_county() -> pl.DataFrame:
    """Combine roster + LEE into one row per ORI with resolved FIPS."""
    roster = _roster_agencies()
    lee = _lee_agencies()

    df = roster.join(lee, on="ori", how="full", coalesce=True)
    df = df.with_columns(
        pl.coalesce(pl.col("agency_name"), pl.col("lee_agency_name")).alias(
            "agency_name"
        ),
        pl.coalesce(pl.col("agency_type"), pl.col("lee_agency_type")).alias(
            "agency_type"
        ),
        pl.coalesce(pl.col("counties_raw"), pl.col("lee_counties_raw")).alias(
            "counties_raw"
        ),
        pl.col("is_nibrs").fill_null(False),
    ).drop(["lee_agency_name", "lee_agency_type", "lee_counties_raw"])

    fips_map = _county_name_to_fips_map()

    def resolve(counties_raw: str | None) -> list[str] | None:
        # Statewide agencies (GBI, GSP HQ, Ports Authority) carry
        # "NOT SPECIFIED" — they have no county; NULL keeps them out of
        # county rollups.
        if not counties_raw or counties_raw.strip().upper() == "NOT SPECIFIED":
            return None
        out = []
        for name in counties_raw.split(","):
            key = " ".join(name.strip().lower().split())
            fips = fips_map.get(key)
            out.append(fips if fips else f"UNMATCHED:{name.strip()}")
        return out

    df = df.with_columns(
        pl.col("counties_raw")
        .map_elements(resolve, return_dtype=pl.List(pl.Utf8))
        .alias("fips_list")
    )

    # Primary county. Single-county agencies: the roster's county wins (the
    # FBI's own assignment). Multi-county agencies: the roster's list is
    # alphabetical, NOT primacy-ordered — taking the first entry misattributed
    # e.g. Atlanta PD to DeKalb. The ORI's embedded county ordinal is the
    # agency's official home county; use it when it is one of the listed
    # counties, else ORI_PRIMARY_OVERRIDES.
    ordinal_map = _ordinal_to_fips_map()

    def primary(row: dict) -> str | None:
        fips_list = row["fips_list"]
        if not fips_list:
            return None
        if len(fips_list) == 1:
            return fips_list[0]
        m = re.match(r"^GA(\d{3})", row["ori"])
        if m:
            ordinal_fips = ordinal_map.get(int(m.group(1)))
            if ordinal_fips in fips_list:
                return ordinal_fips
        override = ORI_PRIMARY_OVERRIDES.get(row["ori"])
        if override in fips_list:
            return override
        return f"UNRESOLVED:{row['ori']}"

    df = df.with_columns(
        pl.struct(["ori", "fips_list"])
        .map_elements(primary, return_dtype=pl.Utf8)
        .alias("county_fips"),
        pl.col("fips_list").list.join("|").alias("all_county_fips"),
        (pl.col("fips_list").list.len() > 1).alias("multi_county"),
    )
    return df.select(
        [
            "ori",
            "agency_name",
            "agency_type",
            "county_fips",
            "all_county_fips",
            "multi_county",
            "is_nibrs",
            "nibrs_start_date",
        ]
    ).sort("ori")


def _assert_health(df: pl.DataFrame) -> None:
    """Hard gates: unique ORI, every county name resolved, plausible volume."""
    dupes = df.filter(pl.col("ori").is_duplicated())
    if dupes.height > 0:
        raise CrosswalkBuildError(
            f"ori_to_county: duplicate ORIs: {dupes['ori'].head(10).to_list()}"
        )
    unresolved = df.filter(
        pl.col("county_fips").str.contains("UNRESOLVED", literal=True)
    )
    if unresolved.height > 0:
        raise CrosswalkBuildError(
            f"ori_to_county: {unresolved.height} multi-county ORIs whose "
            "primary county can't be derived from the ORI ordinal (add to "
            "ORI_PRIMARY_OVERRIDES): "
            + str(unresolved.select(["ori", "agency_name"]).head(15).rows())
        )
    unmatched = df.filter(
        pl.col("all_county_fips").str.contains("UNMATCHED", literal=True)
    )
    if unmatched.height > 0:
        raise CrosswalkBuildError(
            f"ori_to_county: {unmatched.height} ORIs with unresolvable county "
            "names (add to COUNTY_NAME_OVERRIDES): "
            + str(
                unmatched.select(["ori", "agency_name", "all_county_fips"])
                .head(15)
                .rows()
            )
        )
    # NULL county is legitimate for statewide agencies (counties "NOT
    # SPECIFIED"), but should stay a small handful.
    no_county = df.filter(pl.col("county_fips").is_null())
    if no_county.height > 25:
        raise CrosswalkBuildError(
            f"ori_to_county: {no_county.height} ORIs with no county — far more "
            "than the known statewide agencies: "
            + str(no_county.select(["ori", "agency_name"]).head(15).rows())
        )
    if no_county.height > 0:
        logger.info(
            f"{no_county.height} statewide agencies with NULL county: "
            f"{no_county['ori'].to_list()}"
        )
    if df.height < 600:
        raise CrosswalkBuildError(
            f"ori_to_county: only {df.height} ORIs — expected 800+ "
            "(roster + LEE union); a source read likely failed"
        )


def main() -> None:
    """Build and export the ori_to_county crosswalk."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    df = build_ori_to_county()
    _assert_health(df)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.write_parquet(OUTPUT_PARQUET)
    df.write_csv(OUTPUT_CSV)

    multi = df.filter(pl.col("multi_county")).height
    logger.info(
        f"Wrote {df.height} ORIs ({multi} multi-county) to "
        f"{OUTPUT_PARQUET} and {OUTPUT_CSV}"
    )


if __name__ == "__main__":
    main()
