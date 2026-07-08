"""Geography crosswalk utilities for building dimension tables.

Provides Census geographic identifier matching (school district codes,
FIPS codes) used when building dimension tables. Fact tables store only
natural keys (district_code, school_code); Census IDs are resolved at
query time by joining fact tables to dimensions.
"""

import logging
import re
from functools import lru_cache
from pathlib import Path

import polars as pl

logger = logging.getLogger(__name__)

# Default path to crosswalk files
CROSSWALK_DIR = Path("data/gold/crosswalks")
CENSUS_CROSSWALK_FILE = "ga_census_crosswalk.parquet"


@lru_cache(maxsize=1)
def load_census_crosswalk(path: Path | None = None) -> pl.DataFrame:
    """Load the Census crosswalk file.

    The crosswalk contains mappings between Census geographic identifiers
    including county FIPS, tract, place, zip, and school district codes.

    Args:
        path: Optional path to crosswalk file. Defaults to standard location.

    Returns:
        DataFrame with crosswalk data.

    Raises:
        FileNotFoundError: If crosswalk file doesn't exist.
    """
    if path is None:
        path = CROSSWALK_DIR / CENSUS_CROSSWALK_FILE

    if not path.exists():
        raise FileNotFoundError(
            f"Crosswalk file not found: {path}. Run crosswalk build script first."
        )

    logger.debug("Loading Census crosswalk from %s", path)
    return pl.read_parquet(path)


def load_school_district_crosswalk(path: Path | None = None) -> pl.DataFrame:
    """Load school district crosswalk with normalized names for joining.

    Returns a DataFrame with unique school districts and their normalized
    names for joining to GOSA data. The normalized name strips common
    suffixes like "School District" for matching.

    Args:
        path: Optional path to crosswalk file.

    Returns:
        DataFrame with columns:
        - district_census_id: Census school district code (e.g., "00060")
        - district_name_full: Full name (e.g., "Appling County School District")
        - district_name_normalized: Normalized for joining (e.g., "appling county")
    """
    df = load_census_crosswalk(path)

    # Get unique school districts
    districts = (
        df.select(["school_district", "school_district_name"])
        .unique()
        .rename(
            {
                "school_district": "district_census_id",
                "school_district_name": "district_name_full",
            }
        )
    )

    # Add normalized name column for joining (vectorized; no Python UDF).
    districts = districts.with_columns(
        normalize_district_name_expr("district_name_full").alias(
            "district_name_normalized"
        )
    )

    return districts


# Suffixes stripped from district names during normalization.
# Order matters: longer/more-specific matches first so that
# "county schools" wins over the shorter "schools".
_DISTRICT_NAME_SUFFIXES: list[str] = [
    " school district",
    " public schools",
    " city schools",
    " county schools",
    " schools",
]


def normalize_district_name(name: str) -> str:
    """Normalize a school district name for matching.

    Strips common suffixes and normalizes to lowercase for consistent
    matching between different data sources. Prefer the vectorized
    `normalize_district_name_expr()` inside Polars pipelines.

    Args:
        name: The district name to normalize.

    Returns:
        Normalized name (lowercase, stripped of common suffixes).

    Examples:
        >>> normalize_district_name("Appling County School District")
        'appling county'
        >>> normalize_district_name("Atlanta City School District")
        'atlanta city'
        >>> normalize_district_name("Appling County")
        'appling county'
        >>> normalize_district_name("Dalton Public Schools")
        'dalton city'
    """
    if not name:
        return ""

    normalized = name.lower().strip()

    for suffix in _DISTRICT_NAME_SUFFIXES:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break

    # Handle "public" prefix (e.g., "dalton public" -> "dalton city")
    if normalized.endswith(" public"):
        normalized = normalized[:-7] + " city"

    normalized = " ".join(normalized.split())

    return normalized


def normalize_district_name_expr(col: str | pl.Expr) -> pl.Expr:
    """Vectorized Polars expression for district name normalization.

    Equivalent to `normalize_district_name()` but without Python UDFs, which
    are 10-100x slower than native Polars expressions on larger inputs.

    Args:
        col: Column name (str) or Polars expression containing raw names.

    Returns:
        Polars expression producing the normalized name.
    """
    expr = pl.col(col) if isinstance(col, str) else col
    normalized = expr.cast(pl.Utf8).str.strip_chars().str.to_lowercase()

    # Strip the first matching suffix. str.replace's `literal=True` + anchored
    # regex (`$`) isn't available, so we use str.replace with a regex pattern
    # anchored to end-of-string. Longer suffixes first means chained replaces
    # won't double-strip.
    for suffix in _DISTRICT_NAME_SUFFIXES:
        normalized = normalized.str.replace(rf"{re.escape(suffix)}$", "", literal=False)

    # "X public" -> "X city" (e.g., "dalton public" -> "dalton city")
    normalized = normalized.str.replace(r" public$", " city", literal=False)

    # Collapse any runs of whitespace (replace + strip).
    normalized = normalized.str.replace_all(r"\s+", " ").str.strip_chars()

    return normalized


# Manual mapping from GOSA normalized names to Census normalized names.
# Used for districts where automatic normalization doesn't match.
DISTRICT_NAME_OVERRIDES: dict[str, str] = {
    # Combined city-county districts (GOSA uses hyphenated, Census uses county)
    "thomaston-upson county": "upson county",
    "griffin-spalding county": "spalding county",
    "savannah-chatham county": "chatham county",
    # City districts where GOSA uses different naming
    "city schools of decatur": "decatur city",
    "dalton": "dalton city",  # "Dalton Public Schools" normalizes to "dalton"
    "atlanta": "atlanta city",  # "Atlanta Public Schools" normalizes to "atlanta"
    # Dougherty is special - Census doesn't include "county"
    "dougherty county": "dougherty",
    # GOSA uses "Polk School District", Census uses "Polk County School District"
    "polk": "polk county",
    # Abbreviated names from early-era Georgia Milestones files (2014-2015)
    "chattahoochee": "chattahoochee county",
    "taliaferro co": "taliaferro county",
    "thomaston upson county": "upson county",  # space variant of hyphenated form
    "thomastonupson county": "upson county",  # no-separator variant
}


# Charter schools, commission charter schools, and state specialty schools
# use 7-digit GOSA district codes (782xxxx, 783xxxx, 799xxxx) that have no
# Census school district equivalent. This map links each school's GOSA code
# to the Census district ID of its host county's primary school district,
# enabling geographic linkage for cross-dataset analysis.
CHARTER_SCHOOL_CENSUS_MAP: dict[str, str] = {
    # State Charter Schools (782xxxx)
    "7820108": "05670",  # Mountain Education Charter HS → White County SD
    "7820110": "01500",  # Odyssey Charter School → Coweta County SD
    "7820112": "01230",  # Scholars Academy Charter → Clayton County SD
    "7820119": "02280",  # Graduation Achievement Center → Fulton County SD
    "7820120": "02280",  # Georgia Cyber Academy (virtual) → Fulton County SD
    "7820121": "01230",  # Utopian Academy For The Arts → Clayton County SD
    "7820210": "01230",  # Scholars Academy School → Clayton County SD
    "7820212": "01110",  # Cherokee Charter Academy → Cherokee County SD
    "7820312": "02280",  # Heritage Preparatory Academy → Fulton County SD
    "7820410": "02280",  # Atlanta Heights Charter → Fulton County SD
    "7820412": "02550",  # Georgia Connections Academy (virtual) → Gwinnett County SD
    "7820512": "01740",  # Ivy Prep Young Men's Leadership → DeKalb County SD
    "7820612": "01740",  # Ivy Preparatory Academy (Kirkwood) → DeKalb County SD
    "7820613": "03480",  # Foothills Charter/Regional HS → Madison County SD
    "7820614": "02280",  # International Charter School of Atlanta → Fulton County SD
    "7820615": "03390",  # Scintilla Charter Academy → Lowndes County SD
    "7820616": "04380",  # GA School For Innovation & Classics → Richmond County SD
    "7820617": "01230",  # DuBois Integrity Academy → Clayton County SD
    "7820618": "00810",  # Coastal Plains Charter HS → Candler County SD
    "7820619": "02130",  # Utopian Academy Trilith → Fayette County SD
    "7820620": "01470",  # Discovery Regional HS → Cook County SD
    "7820622": "01110",  # Cherokee Classical Academy → Cherokee County SD
    # Commission Charter Schools (783xxxx)
    "7830103": "00630",  # Statesboro STEAM Academy / CCAT → Bulloch County SD
    "7830110": "02550",  # Ivy Prep at Gwinnett → Gwinnett County SD
    "7830112": "02280",  # Peachtree Hope Charter → Fulton County SD
    "7830210": "00750",  # Pataula Charter Academy → Calhoun County SD
    "7830310": "02280",  # Fulton Leadership Academy → Fulton County SD
    "7830410": "02280",  # Atlanta Heights Charter → Fulton County SD
    "7830510": "01740",  # Museum School Avondale Estates → DeKalb County SD
    "7830601": "01500",  # Coweta Charter Academy → Coweta County SD
    "7830610": "01500",  # Coweta Charter Academy → Coweta County SD
    "7830611": "00420",  # Cirrus Academy Charter → Bibb County SD
    "7830612": "04350",  # Southwest Georgia STEM Charter → Randolph County SD
    "7830613": "02550",  # Brookhaven Innovation Academy → Gwinnett County SD
    "7830614": "02130",  # Liberty Tech Charter Academy → Fayette County SD
    "7830615": "02280",  # Genesis Innovation Academy (Boys) → Fulton County SD
    "7830616": "02280",  # Genesis Innovation Academy (Girls) → Fulton County SD
    "7830617": "02280",  # Resurgence Hall Charter → Fulton County SD
    "7830618": "01410",  # SAIL Charter Academy → Columbia County SD
    "7830619": "01290",  # International Academy of Smyrna → Cobb County SD
    "7830620": "02550",  # International Charter Academy of GA → Gwinnett County SD
    "7830621": "02280",  # SLAM Academy of Atlanta → Fulton County SD
    "7830623": "00420",  # Academy For Classical Education → Bibb County SD
    "7830624": "01710",  # Spring Creek Charter Academy → Decatur County SD
    "7830625": "02550",  # Yi Hwang Academy → Gwinnett County SD
    "7830626": "04620",  # Furlow Charter School → Sumter County SD
    "7830627": "02280",  # Atlanta Smart Academy → Fulton County SD
    "7830628": "02280",  # Ethos Classical Charter → Fulton County SD
    "7830629": "02280",  # Harriet Tubman School → Fulton County SD
    "7830630": "03690",  # Baconton Community Charter → Mitchell County SD
    "7830632": "02280",  # Atlanta Unbound Academy → Fulton County SD
    "7830633": "01860",  # D.E.L.T.A. Steam Academy → Douglas County SD
    "7830634": "01740",  # Georgia Fugees Academy → DeKalb County SD
    "7830636": "01290",  # Northwest Classical Academy → Cobb County SD
    "7830637": "01740",  # DeKalb Brilliance Academy → DeKalb County SD
    "7830638": "01740",  # Peace Academy Charter → DeKalb County SD
    "7830639": "01290",  # Miles Ahead Charter → Cobb County SD
    "7830640": "02280",  # Liberation Academy → Fulton County SD
    "7830641": "02280",  # Resurgence Hall Middle Academy → Fulton County SD
    "7830642": "02280",  # Destinations Career Academy (virtual) → Fulton County SD
    "7830643": "01290",  # Amana Academy West Atlanta → Cobb County SD
    "7830644": "01740",  # The Anchor School → DeKalb County SD
    "7830645": "01860",  # Zest Preparatory Academy → Douglas County SD
    "7830646": "01230",  # Sankofa Montessori → Clayton County SD
    "7830647": "02280",  # Rise Preparatory Charter → Fulton County SD
    "7830648": "02820",  # Excelsior Village Academies → Henry County SD
    "7830649": "04380",  # Rocky Creek Charter Academy → Richmond County SD
    "7830650": "02940",  # Four Points Preparatory Academy → Jackson County SD
    "7830651": "02280",  # Movement School South Fulton → Fulton County SD
    "7830652": "01860",  # Simple Vue Academy Charter → Douglas County SD
    # State Specialty Schools (799xxxx)
    "7991893": "01740",  # Atlanta Area School For The Deaf → DeKalb County SD
    "7991894": "00420",  # Georgia Academy For The Blind → Bibb County SD
    "7991895": "02190",  # Georgia School For The Deaf → Floyd County SD
}


def check_crosswalk_overrides(crosswalk_path: Path | None = None) -> list[str]:
    """Verify the manual override maps still point at real crosswalk entries.

    The crosswalk parquet is a maintained artifact; if Census renames a
    district (or the artifact is regenerated differently), an override whose
    target no longer exists silently stops matching. The dimension build runs
    this and fails on any problem.

    Returns:
        Problem description strings (empty == all overrides valid).
    """
    crosswalk = load_school_district_crosswalk(crosswalk_path)
    known_names = set(crosswalk["district_name_normalized"].to_list())
    known_census_ids = set(crosswalk["district_census_id"].to_list())

    problems: list[str] = []
    for gosa_name, census_name in sorted(DISTRICT_NAME_OVERRIDES.items()):
        if census_name not in known_names:
            problems.append(
                f"DISTRICT_NAME_OVERRIDES[{gosa_name!r}] -> {census_name!r}: "
                "target name not in crosswalk"
            )
    for code, census_id in sorted(CHARTER_SCHOOL_CENSUS_MAP.items()):
        if census_id not in known_census_ids:
            problems.append(
                f"CHARTER_SCHOOL_CENSUS_MAP[{code!r}] -> {census_id!r}: "
                "target census ID not in crosswalk"
            )
    return problems


def add_census_district_code(
    df: pl.DataFrame,
    district_name_col: str = "district_name",
    output_col: str = "district_census_id",
    district_code_col: str | None = "district_code",
    crosswalk_path: Path | None = None,
) -> pl.DataFrame:
    """Join Census school district code to a DataFrame.

    Matches districts by normalized name (case-insensitive, ignoring
    common suffixes like "School District"). Also applies manual overrides
    for districts with known naming mismatches, and maps charter schools
    (7-digit GOSA district codes) to their host county's Census district.

    Args:
        df: Source DataFrame with district names.
        district_name_col: Column containing district names to match.
        output_col: Name for the output Census code column.
        district_code_col: Column containing GOSA district codes for
            charter school lookup. Set to None to skip. Defaults to
            "district_code" and is only used if the column exists.
        crosswalk_path: Optional path to crosswalk file.

    Returns:
        DataFrame with Census district code column added.

    Examples:
        >>> df = pl.DataFrame({"district_name": ["Appling County", "Fulton County"]})
        >>> df = add_census_district_code(df)
        >>> df["district_census_id"].to_list()
        ['00060', '01380']
    """
    # Load crosswalk
    districts = load_school_district_crosswalk(crosswalk_path)

    # Drop existing output column if present to avoid duplicate column on join.
    # This handles cases where a placeholder column was added by transform functions.
    if output_col in df.columns:
        df = df.drop(output_col)

    # Add normalized name to source DataFrame, then apply overrides.
    # Both steps are vectorized Polars expressions (no Python UDFs).
    # replace_strict with `default=<same expr>` leaves unmapped names unchanged.
    normalized_expr = normalize_district_name_expr(district_name_col)
    df = df.with_columns(
        normalized_expr.replace_strict(
            DISTRICT_NAME_OVERRIDES, default=normalized_expr
        ).alias("_district_name_normalized")
    )

    # Join on normalized name
    df = df.join(
        districts.select(["district_census_id", "district_name_normalized"]),
        left_on="_district_name_normalized",
        right_on="district_name_normalized",
        how="left",
    )

    # Rename output column if needed
    if output_col != "district_census_id":
        df = df.rename({"district_census_id": output_col})

    # Clean up temp column
    df = df.drop("_district_name_normalized")

    # Fill charter school Census IDs by GOSA district code lookup.
    # Charter/commission/specialty schools have 7-digit codes that don't
    # match any Census district by name. Map them to their host county's
    # primary school district for geographic linkage.
    if district_code_col and district_code_col in df.columns:
        code_col = pl.col(district_code_col).cast(pl.Utf8)
        charter_keys = list(CHARTER_SCHOOL_CENSUS_MAP.keys())
        df = df.with_columns(
            pl.when(pl.col(output_col).is_null() & code_col.is_in(charter_keys))
            .then(code_col.replace_strict(CHARTER_SCHOOL_CENSUS_MAP, default=None))
            .otherwise(pl.col(output_col))
            .alias(output_col)
        )

    return df


# =============================================================================
# County name -> FIPS (criminal_justice and other county-grain domains)
# =============================================================================

# Default path to the global counties dimension (built by
# src/etl/build_counties_dimension.py from the census crosswalk).
COUNTIES_DIMENSION_PATH = Path("data/gold/_dimensions/counties.parquet")

# Manual mapping from normalized source county names to normalized dimension
# names. Sources (GSA jail report, GDC PDFs, DDS) sometimes use consolidated
# city-county government names; the Census county list uses the county name.
COUNTY_NAME_OVERRIDES: dict[str, str] = {
    # Consolidated city-county governments
    "athens-clarke": "clarke",
    "athens clarke": "clarke",
    "athens": "clarke",
    "augusta-richmond": "richmond",
    "augusta richmond": "richmond",
    "augusta": "richmond",
    "columbus-muscogee": "muscogee",
    "columbus muscogee": "muscogee",
    "columbus": "muscogee",
    "macon-bibb": "bibb",
    "macon bibb": "bibb",
    # NOTE: no bare "macon" entry — Macon County (FIPS 13193) is a real,
    # separate Georgia county, so bare "Macon" is ambiguous (it silently
    # misattributed Macon County youths to Bibb in the juvenile clearinghouse
    # source). A source that publishes bare "Macon" MEANING Macon-Bibb must
    # resolve it topic-locally, never via this global default.
    "cusseta-chattahoochee": "chattahoochee",
    "cusseta chattahoochee": "chattahoochee",
    "cusseta": "chattahoochee",
    "georgetown-quitman": "quitman",
    "georgetown quitman": "quitman",
    "georgetown": "quitman",
    "preston-webster": "webster",
    "preston webster": "webster",
    # Spacing variant: OJJDP EZAPOP publishes "De Kalb County"; the Census
    # county list (and the counties dimension) spells it "DeKalb". Unambiguous
    # (there is no other Kalb), so the mapping is safe as a global default.
    "de kalb": "dekalb",
}


def normalize_county_name_expr(col: str | pl.Expr) -> pl.Expr:
    """Vectorized normalization of county names for FIPS matching.

    Lowercases, strips a trailing ' GA' state suffix and 'county'/'co.'
    suffixes, and collapses whitespace. Pair with COUNTY_NAME_OVERRIDES for
    consolidated-government names.
    """
    expr = pl.col(col) if isinstance(col, str) else col
    normalized = expr.cast(pl.Utf8).str.strip_chars().str.to_lowercase()
    normalized = normalized.str.replace(r",? (ga|georgia)$", "", literal=False)
    normalized = normalized.str.replace(r" county$", "", literal=False)
    normalized = normalized.str.replace(r" co\.?$", "", literal=False)
    normalized = normalized.str.replace_all(r"\s+", " ").str.strip_chars()
    return normalized


@lru_cache(maxsize=1)
def load_counties_dimension(path: Path | None = None) -> pl.DataFrame:
    """Load the global counties dimension (county_fips, county_name)."""
    if path is None:
        path = COUNTIES_DIMENSION_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Counties dimension not found: {path}. "
            "Run `uv run python -m src.etl.build_counties_dimension` first."
        )
    return pl.read_parquet(path)


def add_county_fips(
    df: pl.DataFrame,
    county_name_col: str,
    output_col: str = "county_fips",
    dimension_path: Path | None = None,
) -> pl.DataFrame:
    """Join 5-digit county FIPS to a DataFrame by county name.

    Matches counties by normalized name against the global counties dimension,
    applying COUNTY_NAME_OVERRIDES for consolidated-government names first.
    Unmatched names get NULL — callers must surface those via the manifest's
    unmapped tracking (blocking) rather than letting them pass silently.

    Args:
        df: Source DataFrame with county names.
        county_name_col: Column containing county names to match.
        output_col: Name for the output FIPS column.
        dimension_path: Optional override for the counties dimension parquet.

    Returns:
        DataFrame with the county FIPS column added.
    """
    counties = load_counties_dimension(dimension_path)
    lookup = counties.select(
        normalize_county_name_expr("county_name").alias("_county_name_normalized"),
        pl.col("county_fips").alias(output_col),
    )

    if output_col in df.columns:
        df = df.drop(output_col)

    normalized_expr = normalize_county_name_expr(county_name_col)
    df = df.with_columns(
        normalized_expr.replace_strict(
            COUNTY_NAME_OVERRIDES, default=normalized_expr
        ).alias("_county_name_normalized")
    )
    df = df.join(lookup, on="_county_name_normalized", how="left")
    return df.drop("_county_name_normalized")


def check_county_overrides(dimension_path: Path | None = None) -> list[str]:
    """Verify COUNTY_NAME_OVERRIDES targets resolve to real dimension counties.

    Mirrors check_crosswalk_overrides: the counties dimension build runs this
    and fails on any problem, so a stale override can't silently stop matching.

    Returns:
        Problem description strings (empty == all overrides valid).
    """
    counties = load_counties_dimension(dimension_path)
    known_names = set(
        counties.select(normalize_county_name_expr("county_name")).to_series().to_list()
    )
    problems: list[str] = []
    for source_name, target in sorted(COUNTY_NAME_OVERRIDES.items()):
        if target not in known_names:
            problems.append(
                f"COUNTY_NAME_OVERRIDES[{source_name!r}] -> {target!r}: "
                "target name not in counties dimension"
            )
    return problems
