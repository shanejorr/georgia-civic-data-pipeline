"""Transform USSC individual-offender datafiles into a GA federal-district fact table.

Source: US Sentencing Commission "offenders sentenced" annual national
datafiles (opafy{YY}nid), FY2002-FY2025 — one row per individual sentenced
under the federal system in a fiscal year. Gold aggregates to
``federal_district x fiscal_year x demographic`` for Georgia's three federal
judicial districts (DISTRICT 32 = Northern, 33 = Middle, 34 = Southern).

Design decisions (from bronze-data-structure.md, the USSC codebook
FY99-FY25, and data-cleaning-standards):

- **Grain: year x federal_district x demographic; detail_level='federal_district'.**
  ``year`` is the FEDERAL FISCAL YEAR (Oct 1 - Sep 30 ending in that year),
  from the filename (``opafy{YY}``) and soft-verified against the in-file
  calendar sentencing year SENTYR where it exists (FY2004-FY2023: SENTYR must
  be fy-1 (Oct-Dec) or fy (Jan-Sep)). ``federal_district`` is a NEW sub-state
  grain — the counties dimension does not apply, so no ``county_fips`` column
  is carried (precedent: gdc/inmate_population's geography-free statewide
  table). All rows are tagged ``detail_level='federal_district'`` so export
  writes ``federal_districts.parquet`` (the shared federal-district detail
  level); ``null_aggregate_geography`` is not called because no geography
  column exists.
- **PII is aggregated away.** Bronze is individual-offender microdata. The
  transform reads ONLY an explicit allowlist of columns (DISTRICT, SENTTOT,
  MONSEX, USSCIDN, SENTYR) — the offender ``NAME`` field documented in the
  codebook appears in none of the 24 files' layouts/headers and could never
  be materialized because reads are allowlist-only. Offender-level frames
  exist only in memory, only for Georgia rows, and only long enough to be
  aggregated; gold contains district-year aggregates exclusively. USSCIDN is
  used solely for an in-memory within-year duplicate guard.
- **Format eras (detected structurally from zip members, not year ranges).**
  FY2002-FY2011 zips carry a fixed-width ``.dat`` (no header) plus the
  ``.sas`` layout script whose INPUT statement gives 1-indexed column
  positions — the transform parses each year's own INPUT statement
  (case-insensitive: FY2010 uses lowercase names) and streams the ``.dat``
  member line by line from the zip (never extracted, never fully loaded;
  every line is asserted to be exactly LRECL chars so truncation fails
  loudly). FY2012-FY2025 zips carry a single very wide CSV (18k-27k
  columns); only the allowlist columns are materialized via
  ``pl.read_csv(columns=...)`` on the zip member stream. The shared
  ``read_bronze_file`` cannot read members inside zips (and must never see a
  1.5-4 GB extraction), so both readers are custom, with read-loss accounting
  reconstructed from physical line counts (CSV: raw lines - header vs parsed
  rows; fixed-width: parity by construction).
- **National files are filtered to Georgia as early as possible** (DISTRICT
  in {32,33,34}; CIRCDIST's alternate 92/93/94 scheme deliberately unused)
  and processed ONE fiscal year at a time; only ~1.2-2.6k-row GA mini-frames
  are ever concatenated. Row-count anchors are pinned for FY2002/FY2012
  (verified during authoring) and FY2024 (61,678 national rows, the
  structure-doc anchor) so a refresh that truncates a file fails loudly.
- **Metrics (lean, uniform across all 24 years):** ``offenders_sentenced``
  (row count; key metric), ``num_with_prison_sentence`` (offenders whose
  sentence includes reported prison time: SENTTOT non-missing), and
  ``avg_sentence_months`` / ``median_sentence_months`` over SENTTOT with the
  Commission's SENTTCAP cap applied. Per the codebook, SENTTOT is total
  prison months EXCLUDING alternatives, with probation-only and zero terms
  set to missing, and life sentences coded 470; the Commission's own
  length-of-imprisonment analyses use the capped variant (SENTTCAP, FY2018+:
  range 0.01-469.99, 470 reserved for life), so determinate sentences longer
  than 470 months are capped at 469.99 every year (FY2024 GA: 4 values above
  470, max 1,200, plus 5 life-coded exactly-470s left untouched), yielding
  one uniform methodology across the whole series instead of pooling capped
  early-era values with uncapped late-era ones. Medians are polars medians
  (linear interpolation on even counts), both stats rounded to 2 decimals.
- **§4b masks (defensive; zero occurrences observed in FY2002/12/24 GA
  rows):** SENTTOT sentinel codes >= 9992 (the 9992/9996/9997/9998 zone that
  belongs to TOTPRISN's coding) and non-positive SENTTOT values (impossible:
  the codebook sets zero terms to missing; range floor 0.01) are NULLed at
  the offender level before aggregation, counted per year, and recorded via
  ``manifest.record_masked`` under the bronze column name SENTTOT (the mask
  feeds three gold columns, so it is recorded against the input).
- **Demographic = gender only (all/male/female).** MONSEX is 0=Male 1=Female
  (2=Other added FY2024). Male/female rows are mutually exclusive; offenders
  with missing MONSEX (~0-6%% by year) or MONSEX=2 are included in the 'all'
  row ONLY (never a synthesized 'other' row — not a canonical demographic),
  so male+female <= all (authored quality check). Race splits are DEFERRED:
  NEWRACE collapses to White/Black/Hispanic/Other, and 'Other' conflates
  Asian, Pacific Islander, Native American and multiracial — it cannot be
  expressed in the canonical mutually-exclusive race vocabulary (judgment
  item; MONRACE+HISPORIG could support a future combined-bucket mapping).
- **Departure/variance metrics are deliberately NOT published**: the USSC
  recoded BOOKERCD/departure derivations from FY2018, so a pooled
  share-with-departure series would cross a methodology break; versioning it
  is deferred rather than shipped half-usable (judgment item). Broad
  offense-type / drug-type counts are likewise deferred (the primary-offense
  categorization changed at FY2018 with OFFGUIDE, and drug-type variables
  were restructured in FY2018).
- **FY2018 time-served refinement (documented, not versioned):** from FY2018
  "time served only" cases carry SENTTOT = 0.03 months instead of missing.
  This slightly widens ``num_with_prison_sentence`` and nudges averages down
  from FY2018 onward; the Commission treats SENTTOT as one continuous series
  and the affected group is small, so the change is documented in the
  contract limitations rather than versioned as a break (judgment item).
- **No suppression** (``suppressed_to_null=False``): USSC publishes complete
  unsuppressed microdata; the only NULLs in gold are avg/median on cells with
  zero reported prison sentences (co-null quality check).
- **Year floor >= 2000** applied defensively (all files are FY2002-FY2025)
  and enforced by the ``no_pre_2000_years`` quality check, per the
  platform-wide year floor.
- **Dedup tie-break.** Each fiscal year comes from exactly one national zip
  and one single-pass aggregation, so natural-key collisions are impossible
  by construction; the collision guard runs first and
  ``deduplicate_by_levels(sort_col="offenders_sentenced")`` remains as the
  documented safety net (prefer the fuller row) should a future refresh ever
  add an overlapping file.
"""

import io
import logging
import re
import zipfile
from pathlib import Path

import polars as pl

from src.utils.demographics import DEMOGRAPHIC_ALIASES, normalize_demographic_column
from src.utils.metadata import write_data_dictionary
from src.utils.transformers import (
    FEDERAL_DISTRICT_DETAIL_LEVEL_FILES,
    TransformManifest,
    assert_no_natural_key_collisions,
    deduplicate_by_levels,
    export_to_parquet,
    harmonize_columns,
    validate_output,
)
from src.utils.validators import check_null_rate_spikes, run_topic_validation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

TOPIC = "district_sentences"
BRONZE_DIR = Path("data/bronze/criminal_justice/federal_justice/district_sentences")
GOLD_DIR = Path("data/gold/criminal_justice/district_sentences")
SOURCE_URL = "https://www.ussc.gov/research/datafiles/commission-datafiles"

YEAR_FLOOR = 2000

# DISTRICT -> gold federal_district (USSC codebook Appendix A / DISTRICT
# format: 32='Georgia North', 33='Georgia Mid', 34='Georgia South'). The
# alternate circuit-ordered CIRCDIST scheme (92/93/94) is deliberately unused.
DISTRICT_MAP: dict[str, str] = {
    "32": "georgia_northern",
    "33": "georgia_middle",
    "34": "georgia_southern",
}

# MONSEX codes (codebook): 0=Male, 1=Female, 2=Other (added FY2024), blank =
# missing. Only Male/Female become demographic rows; Other/missing offenders
# are counted in the 'all' row only (see module docstring).
MONSEX_LABELS: dict[str, str] = {"0": "Male", "1": "Female", "2": "Other"}

# Columns read from bronze (the PII allowlist — nothing else is ever
# materialized). SENTYR exists only FY2004-FY2023 and is optional.
REQUIRED_VARS = ["DISTRICT", "SENTTOT", "MONSEX", "USSCIDN"]
OPTIONAL_VARS = ["SENTYR"]

# Sentence-length handling (codebook SENTTOT / SENTTCAP / Appendix B):
# life = 470 months by Commission convention; determinate sentences LONGER
# than 470 months are capped at 469.99 so they never collide with the life
# code (SENTTCAP semantics: range 0.01-469.99, 470 reserved for life).
# Values >= 9992 belong to TOTPRISN's sentinel zone and are impossible in
# SENTTOT (defensive §4b mask), as are non-positive values (zero terms are
# set to missing at source; range floor is 0.01).
LIFE_SENTENCE_MONTHS = 470.0
DETERMINATE_CAP_MONTHS = 469.99
SENTINEL_FLOOR = 9992.0

# Row-count anchors (verified at authoring; FY2024 national count is the
# structure-doc anchor). A refresh that changes these fails loudly.
NATIONAL_ROW_ANCHORS: dict[int, int] = {2002: 64_366, 2012: 84_173, 2024: 61_678}
GEORGIA_ROW_ANCHORS: dict[int, int] = {2002: 1_429, 2012: 1_646, 2024: 1_272}

METRIC_COLUMNS: list[str] = [
    "offenders_sentenced",
    "num_with_prison_sentence",
    "avg_sentence_months",
    "median_sentence_months",
]

# Gold fact column order. `detail_level` is carried through dedup and export
# splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "federal_district",
    "demographic",
    *METRIC_COLUMNS,
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "federal_district": pl.Utf8,
    "demographic": pl.Utf8,
    "offenders_sentenced": pl.Int64,
    "num_with_prison_sentence": pl.Int64,
    "avg_sentence_months": pl.Float64,
    "median_sentence_months": pl.Float64,
    "detail_level": pl.Utf8,
}

NATURAL_KEYS: list[str] = ["year", "federal_district", "demographic", "detail_level"]

FILENAME_RE = re.compile(r"^opafy(\d{2})nid(_csv)?\.zip$")


# =============================================================================
# Bronze readers (zip members are streamed; nothing is extracted to disk)
# =============================================================================


def _fiscal_year_from_name(name: str) -> int:
    """Fiscal year from the opafy{YY}nid zip filename (YY 02-25 -> 2002-2025)."""
    m = FILENAME_RE.match(name)
    if not m:
        raise ValueError(f"Unrecognized bronze filename: {name}")
    return 2000 + int(m.group(1))


def _member(zf: zipfile.ZipFile, suffix: str) -> str | None:
    """The single zip member with the given suffix (case-insensitive)."""
    hits = [n for n in zf.namelist() if n.lower().endswith(suffix)]
    if len(hits) > 1:
        raise ValueError(f"Multiple {suffix} members in zip: {hits}")
    return hits[0] if hits else None


def _parse_sas_layout(sas_text: str) -> tuple[int, dict[str, tuple[int, int]]]:
    """Parse LRECL and {VAR: (start, end)} 1-indexed positions from a .sas script.

    The INPUT statement uses SAS column input (``VAR [$] start[-end]``); no
    decimal specifiers exist in any year (verified across FY2002-FY2011).
    Variable names are matched case-insensitively (FY2010 uses lowercase).
    """
    lrecl_m = re.search(r"LRECL\s*=\s*(\d+)", sas_text, re.I)
    input_m = re.search(r"\bINPUT\b(.*?);", sas_text, re.S | re.I)
    if not lrecl_m or not input_m:
        raise ValueError("SAS layout script missing LRECL or INPUT statement")
    tokens = re.findall(
        r"([A-Za-z][A-Za-z0-9_]*)\s*(\$)?\s*(\d+)(?:\s*-\s*(\d+))?",
        input_m.group(1),
    )
    positions = {
        name.upper(): (int(start), int(end or start))
        for name, _dollar, start, end in tokens
    }
    if not positions:
        raise ValueError("No variables parsed from SAS INPUT statement")
    return int(lrecl_m.group(1)), positions


def _read_fixed_width_year(path: Path, fy: int) -> tuple[pl.DataFrame, int, int]:
    """Stream one FY2002-FY2011 .dat member; return (national frame, raw, parsed).

    Only the allowlist byte ranges are sliced from each line; every line is
    asserted to be exactly LRECL chars so a truncated/corrupt record fails
    loudly instead of yielding shifted fields. The returned frame is national
    but holds only the 5 allowlist columns (a few MB).
    """
    with zipfile.ZipFile(path) as zf:
        sas_name = _member(zf, ".sas")
        dat_name = _member(zf, ".dat")
        if not sas_name or not dat_name:
            raise ValueError(f"{path.name}: expected .sas + .dat members")
        lrecl, positions = _parse_sas_layout(zf.read(sas_name).decode("latin-1"))

        missing = [v for v in REQUIRED_VARS if v not in positions]
        if missing:
            raise ValueError(f"{path.name}: layout lacks required vars {missing}")
        present = REQUIRED_VARS + [v for v in OPTIONAL_VARS if v in positions]
        for v in OPTIONAL_VARS:
            if v not in positions:
                logger.info(
                    "%s: optional column %s absent from layout (expected: "
                    "SENTYR exists only FY2004-FY2023)",
                    path.name,
                    v,
                )
        slices = {v: (positions[v][0] - 1, positions[v][1]) for v in present}

        data: dict[str, list[str | None]] = {v: [] for v in present}
        n_lines = 0
        with zf.open(dat_name) as f:
            buf = io.BufferedReader(f, buffer_size=1 << 20)
            for line in buf:
                line = line.rstrip(b"\r\n")
                if len(line) != lrecl:
                    raise ValueError(
                        f"{path.name}:{dat_name} line {n_lines + 1} is "
                        f"{len(line)} chars, expected LRECL={lrecl} — "
                        "truncated or corrupt record"
                    )
                n_lines += 1
                for var, (a, b) in slices.items():
                    field = line[a:b].strip()
                    data[var].append(field.decode("latin-1") if field else None)

    df = pl.DataFrame(data, schema={v: pl.Utf8 for v in present})
    logger.info("%s: streamed %d fixed-width records (FY%d)", path.name, n_lines, fy)
    return df, n_lines, df.height


def _read_csv_year(path: Path, fy: int) -> tuple[pl.DataFrame, int, int]:
    """Read one FY2012-FY2025 CSV member; return (national frame, raw, parsed).

    Pass 1 streams the member to count physical lines (read-loss accounting)
    and capture the header; pass 2 materializes ONLY the allowlist columns
    (the files carry 18k-27k columns — never read them all) with
    ``infer_schema_length=0`` (all Utf8; codes are cast explicitly later).
    """
    with zipfile.ZipFile(path) as zf:
        csv_name = _member(zf, ".csv")
        if not csv_name:
            raise ValueError(f"{path.name}: expected a .csv member")

        # Pass 1: physical line count + header capture, streamed in chunks.
        n_newlines = 0
        header_buf = b""
        header_done = False
        last_byte = b""
        with zf.open(csv_name) as f:
            while chunk := f.read(1 << 20):
                n_newlines += chunk.count(b"\n")
                if not header_done:
                    header_buf += chunk
                    if b"\n" in header_buf:
                        header_buf = header_buf.split(b"\n", 1)[0]
                        header_done = True
                last_byte = chunk[-1:]
        raw_lines = n_newlines + (1 if last_byte not in (b"\n", b"") else 0)
        header = [
            c.strip().strip('"')
            for c in header_buf.decode("utf-8", errors="replace")
            .rstrip("\r")
            .split(",")
        ]
        by_upper = {c.upper(): c for c in header}

        missing = [v for v in REQUIRED_VARS if v not in by_upper]
        if missing:
            raise ValueError(f"{path.name}: CSV header lacks required {missing}")
        wanted = [by_upper[v] for v in REQUIRED_VARS] + [
            by_upper[v] for v in OPTIONAL_VARS if v in by_upper
        ]
        for v in OPTIONAL_VARS:
            if v not in by_upper:
                logger.info(
                    "%s: optional column %s absent from header (expected: "
                    "SENTYR exists only FY2004-FY2023)",
                    path.name,
                    v,
                )

        # Pass 2: materialize only the allowlist columns. utf8-lossy because
        # some years (e.g. FY2017) carry non-UTF-8 bytes in free-text fields
        # we never materialize; the allowlist columns are pure ASCII codes.
        with zf.open(csv_name) as f:
            df = pl.read_csv(
                f, columns=wanted, infer_schema_length=0, encoding="utf8-lossy"
            )

    df = df.rename(
        {by_upper[v]: v for v in REQUIRED_VARS + OPTIONAL_VARS if v in by_upper}
    )
    logger.info(
        "%s: read %d of %d CSV columns, %d rows (FY%d)",
        path.name,
        len(wanted),
        len(header),
        df.height,
        fy,
    )
    return df, raw_lines - 1, df.height  # raw minus the header line


# =============================================================================
# Per-year transform: national frame -> Georgia offender mini-frame
# =============================================================================


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame:
    """Read one annual zip, filter to Georgia, and return the offender frame.

    The returned mini-frame (year, district_code, monsex_raw, sex_label,
    sentence_months_raw) holds only Georgia rows — never concatenate national
    frames. Bronze counts are national; the non-Georgia drop is recorded as
    an explicit filter event.
    """
    fy = _fiscal_year_from_name(path.name)
    with zipfile.ZipFile(path) as zf:
        is_csv = _member(zf, ".csv") is not None

    # Era is detected structurally from the zip's members, never year ranges.
    if is_csv:
        era = "csv_wide"
        df, raw_rows, parsed_rows = _read_csv_year(path, fy)
    else:
        era = "fixed_width_sas_layout"
        df, raw_rows, parsed_rows = _read_fixed_width_year(path, fy)

    manifest.record_read_loss(fy, path.name, raw_rows, parsed_rows)
    manifest.record_file(path, fy, era, df.height, df.columns)
    manifest.record_bronze(fy, df.height)
    if fy in NATIONAL_ROW_ANCHORS and df.height != NATIONAL_ROW_ANCHORS[fy]:
        raise ValueError(
            f"FY{fy}: national row count {df.height:,} != pinned anchor "
            f"{NATIONAL_ROW_ANCHORS[fy]:,}"
        )

    # Georgia filter, as early as possible: DISTRICT in {32, 33, 34}.
    df = df.with_columns(
        pl.col("DISTRICT").str.strip_chars().cast(pl.Int32, strict=False).alias("_dist")
    )
    n_null_dist = df.filter(pl.col("_dist").is_null()).height
    if n_null_dist:
        logger.warning(
            "FY%d: %d rows with missing/non-numeric DISTRICT (cannot be "
            "attributed to any district; dropped with the non-GA rows)",
            fy,
            n_null_dist,
        )
    ga = df.filter(pl.col("_dist").is_in([32, 33, 34]))
    manifest.record_filtered(fy, df.height - ga.height, "non_georgia_district_row")
    logger.info("FY%d: kept %d Georgia rows of %d national", fy, ga.height, df.height)
    if fy in GEORGIA_ROW_ANCHORS and ga.height != GEORGIA_ROW_ANCHORS[fy]:
        raise ValueError(
            f"FY{fy}: Georgia row count {ga.height:,} != pinned anchor "
            f"{GEORGIA_ROW_ANCHORS[fy]:,}"
        )

    # Within-year duplicate-offender guard (USSCIDN is the per-year record id).
    n_null_id = ga["USSCIDN"].null_count()
    if n_null_id:
        logger.warning("FY%d: %d GA rows with missing USSCIDN", fy, n_null_id)
    non_null_ids = ga.filter(pl.col("USSCIDN").is_not_null())["USSCIDN"]
    if non_null_ids.n_unique() != len(non_null_ids):
        raise ValueError(f"FY{fy}: duplicate USSCIDN values among GA rows")

    # Fiscal-year agreement (structure-doc ETL consideration 6): SENTYR is the
    # CALENDAR sentencing year, so a FY{fy} file may only contain fy-1
    # (Oct-Dec) or fy (Jan-Sep). Missing values are allowed.
    if "SENTYR" in ga.columns:
        sentyr = ga["SENTYR"].str.strip_chars().cast(pl.Int32, strict=False)
        bad = sentyr.filter(~sentyr.is_in([fy - 1, fy]) & sentyr.is_not_null())
        if len(bad):
            raise ValueError(
                f"FY{fy}: {len(bad)} GA rows with SENTYR outside "
                f"{{{fy - 1}, {fy}}}: {sorted(set(bad.to_list()))[:5]}"
            )

    return ga.select(
        pl.lit(fy, dtype=pl.Int32).alias("year"),
        pl.col("_dist").cast(pl.Utf8).alias("district_code"),
        pl.col("MONSEX").str.strip_chars().alias("monsex_raw"),
        pl.col("SENTTOT").str.strip_chars().alias("senttot_raw"),
    )


# =============================================================================
# Offender-level cleaning + aggregation
# =============================================================================


def _clean_offenders(
    offenders: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Recode district/sex, parse + mask + cap sentence months (offender level)."""
    # federal_district recode (32/33/34 -> georgia_*), recorded on the manifest.
    offenders = offenders.with_columns(
        pl.col("district_code").replace_strict(DISTRICT_MAP).alias("federal_district")
    )
    manifest.record_categorical(
        column="federal_district",
        map_dict=DISTRICT_MAP,
        bronze_series=offenders["district_code"],
        gold_series=offenders["federal_district"],
    )

    # MONSEX -> label. Unmapped codes would block via the manifest guard;
    # NULLs pass through (missing sex -> counted in 'all' only).
    offenders = offenders.with_columns(
        pl.col("monsex_raw")
        .replace_strict(MONSEX_LABELS, default=None)
        .alias("sex_label")
    )
    unmapped_sex = offenders.filter(
        pl.col("monsex_raw").is_not_null() & pl.col("sex_label").is_null()
    )
    manifest.record_categorical(
        column="offender_sex",
        map_dict=MONSEX_LABELS,
        bronze_series=offenders["monsex_raw"],
        gold_series=offenders["sex_label"],
    )
    if unmapped_sex.height:
        # record_categorical already tallied these as unmapped (blocking).
        logger.error(
            "Unmapped MONSEX codes: %s",
            unmapped_sex["monsex_raw"].unique().sort().to_list(),
        )
    n_other = offenders.filter(pl.col("sex_label") == "Other").height
    n_missing_sex = offenders["monsex_raw"].null_count()
    logger.info(
        "Sex coverage: %d 'Other' (MONSEX=2, FY2024+) and %d missing-sex "
        "offenders are counted in the 'all' rows only",
        n_other,
        n_missing_sex,
    )

    # SENTTOT: parse ('.'/blank -> NULL is already None from the readers),
    # then the defensive §4b masks, then the 470 life/long-sentence cap.
    offenders = offenders.with_columns(
        pl.col("senttot_raw")
        .str.replace(r"^\.$", "")  # a bare SAS missing dot, defensive
        .cast(pl.Float64, strict=False)
        .alias("senttot")
    )
    n_unparseable = offenders.filter(
        pl.col("senttot_raw").is_not_null()
        & ~pl.col("senttot_raw").is_in(["", "."])  # SAS missing markers
        & pl.col("senttot").is_null()
    ).height
    if n_unparseable:
        raise ValueError(
            f"{n_unparseable} non-numeric SENTTOT values — unexpected format"
        )

    # §4b mask 1: sentinel codes >= 9992 (life/unspecified/death zone) are
    # impossible in SENTTOT (life is 470 by convention) -> NULL, recorded.
    sentinel_years = offenders.filter(pl.col("senttot") >= SENTINEL_FLOOR)
    if sentinel_years.height:
        manifest.record_masked(
            column="SENTTOT",
            count=sentinel_years.height,
            reason="sentinel_code_ge_9992_masked_to_null_before_averaging",
            years=sentinel_years["year"].unique().to_list(),
        )
    # §4b mask 2: non-positive sentence months are impossible (codebook sets
    # zero terms to missing; range floor 0.01) -> NULL, recorded.
    nonpos = offenders.filter(pl.col("senttot") <= 0)
    if nonpos.height:
        manifest.record_masked(
            column="SENTTOT",
            count=nonpos.height,
            reason="nonpositive_sentence_months_impossible_per_codebook",
            years=nonpos["year"].unique().to_list(),
        )
    offenders = offenders.with_columns(
        pl.when((pl.col("senttot") >= SENTINEL_FLOOR) | (pl.col("senttot") <= 0))
        .then(None)
        .otherwise(pl.col("senttot"))
        .alias("senttot")
    )

    # Uniform SENTTCAP cap (Commission convention, codebook Appendix B):
    # determinate sentences LONGER than 470 months are capped at 469.99;
    # exactly-470 values are the life-sentence code and stay 470. A cap is a
    # documented methodological choice, not a §4b mask.
    n_capped = offenders.filter(pl.col("senttot") > LIFE_SENTENCE_MONTHS).height
    if n_capped:
        logger.info(
            "Capped %d determinate SENTTOT values above %d months to %.2f "
            "(uniform SENTTCAP series; life sentences keep the 470 code)",
            n_capped,
            int(LIFE_SENTENCE_MONTHS),
            DETERMINATE_CAP_MONTHS,
        )
    # when/then preserves NULLs (a NULL comparison is null -> otherwise branch
    # keeps the NULL; probation/masked sentences never become capped months).
    return offenders.with_columns(
        pl.when(pl.col("senttot") > LIFE_SENTENCE_MONTHS)
        .then(pl.lit(DETERMINATE_CAP_MONTHS))
        .otherwise(pl.col("senttot"))
        .alias("sentence_months")
    )


def _aggregate(offenders: pl.DataFrame, manifest: TransformManifest) -> pl.DataFrame:
    """Aggregate offender rows to year x federal_district x demographic."""
    aggs = [
        pl.len().cast(pl.Int64).alias("offenders_sentenced"),
        pl.col("sentence_months")
        .count()
        .cast(pl.Int64)
        .alias("num_with_prison_sentence"),
        pl.col("sentence_months").mean().round(2).alias("avg_sentence_months"),
        pl.col("sentence_months").median().round(2).alias("median_sentence_months"),
    ]
    all_rows = (
        offenders.group_by("year", "federal_district")
        .agg(aggs)
        .with_columns(pl.lit("All").alias("demographic_raw"))
    )
    gender_rows = (
        offenders.filter(pl.col("sex_label").is_in(["Male", "Female"]))
        .group_by("year", "federal_district", "sex_label")
        .agg(aggs)
        .rename({"sex_label": "demographic_raw"})
    )
    result = pl.concat([all_rows, gender_rows.select(all_rows.columns)])

    # Canonical demographic normalization (shared path), recorded with the
    # effective alias slice actually hit (per data-cleaning-standards §4.3a).
    result = result.with_columns(
        normalize_demographic_column("demographic_raw").alias("demographic")
    )
    observed = result["demographic_raw"].unique().to_list()
    manifest.record_categorical(
        column="demographic",
        map_dict={lbl.upper(): DEMOGRAPHIC_ALIASES[lbl.upper()] for lbl in observed},
        bronze_series=result["demographic_raw"],
        gold_series=result["demographic"],
    )
    return result.drop("demographic_raw").with_columns(
        pl.lit("federal_district").alias("detail_level")
    )


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for district_sentences."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    zips = sorted(p for p in BRONZE_DIR.glob("opafy*nid*.zip"))
    if len(zips) != 24:
        raise ValueError(f"Expected 24 annual zips, found {len(zips)}")

    # 1. One fiscal year at a time (memory: national files are 1.2-4.1 GB
    # uncompressed); only Georgia mini-frames are kept.
    ga_frames: list[pl.DataFrame] = []
    for path in zips:
        ga_frames.append(transform_file(path, manifest))
    offenders = pl.concat(ga_frames)
    logger.info(
        "Georgia offender rows across all years: %d (FY%d-FY%d)",
        offenders.height,
        int(offenders["year"].min()),
        int(offenders["year"].max()),
    )

    # Defensive platform year floor (all files are FY2002+ already).
    pre_floor = offenders.filter(pl.col("year") < YEAR_FLOOR)
    if pre_floor.height:
        for year, count in pre_floor.group_by("year").len().sort("year").iter_rows():
            manifest.record_filtered(year, count, "pre_2000_year_floor")
        offenders = offenders.filter(pl.col("year") >= YEAR_FLOOR)
        logger.warning("Year floor %d: dropped %d rows", YEAR_FLOOR, pre_floor.height)

    # 2. Offender-level cleaning (recodes, §4b masks, cap), then aggregation.
    offenders = _clean_offenders(offenders, manifest)
    result = _aggregate(offenders, manifest)
    logger.info(
        "Aggregated %d offender rows -> %d gold rows",
        offenders.height,
        result.height,
    )

    # 3. Harmonize to the gold schema (one pass — eras already share it).
    combined = pl.concat(harmonize_columns([result], STANDARD_COLUMNS, TARGET_TYPES))

    # 4. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # would mean an aggregation bug and must raise, not be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: each fiscal year comes from exactly one national zip and one
    # single-pass aggregation, so collisions are impossible by construction;
    # sort_col is the documented safety net (prefer the fuller row) should a
    # future refresh ever add an overlapping file.
    combined = deduplicate_by_levels(
        combined,
        {"federal_district": ["year", "federal_district", "demographic"]},
        sort_col="offenders_sentenced",
    )

    # 5. No geography nulling: the topic has no geography columns at all
    # (federal-district grain; county_fips omitted — see module docstring).
    # §4b masks were applied at the offender level in _clean_offenders().
    spike = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike.details)
    validate_output(
        combined,
        required_non_null=["year", "federal_district", "demographic", "detail_level"],
    )

    # 6. Manifest stats on the FINAL DataFrame, then export.
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(
        combined,
        GOLD_DIR,
        STANDARD_COLUMNS,
        detail_level_files=FEDERAL_DISTRICT_DETAIL_LEVEL_FILES,
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
    ``detail_level`` — the contract's properties (and the validator's schema
    check) follow it.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Individuals sentenced in Georgia's three federal judicial "
            "districts (Northern, Middle, Southern), by federal fiscal year "
            "and gender, aggregated from the US Sentencing Commission's "
            "national individual-offender datafiles (one record per person "
            "sentenced under the federal Sentencing Reform Act), "
            "FY2002-FY2025. Each row carries the count of sentenced "
            "individuals plus the average and median prison sentence in "
            "months (USSC SENTTOT: prison time only — probation-only "
            "sentences are excluded from the length statistics, life "
            "sentences carry the Commission's 470-month code, and "
            "determinate sentences longer than 470 months are capped at "
            "469.99 to match the Commission's SENTTCAP "
            "length-of-imprisonment methodology uniformly across "
            "all years). The federal-district grain is sub-state and does "
            "not map to counties; the year is the FEDERAL FISCAL YEAR "
            "(October 1 - September 30, ending in the stated year)."
        ),
        title="Federal Court Sentences by Georgia District",
        summary=(
            "Individuals sentenced in Georgia's three federal judicial "
            "districts, with average and median prison-sentence months, by "
            "federal fiscal year and gender, FY2002 onward (US Sentencing "
            "Commission)."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2024,
                "description": (
                    "FEDERAL FISCAL YEAR of sentencing (October 1 of the "
                    "prior calendar year through September 30 of this year), "
                    "not a calendar year. FY2002 is the earliest served year "
                    "(the platform serves 2000 forward; this source's "
                    "earliest consistently-coded public datafile era begins "
                    "at FY2002)."
                ),
            },
            {
                "name": "federal_district",
                "type": "string",
                "nullable": False,
                "validValues": sorted(DISTRICT_MAP.values()),
                "example": "georgia_northern",
                "short_description": (
                    "Georgia federal judicial district where the individual "
                    "was sentenced (georgia_northern, georgia_middle, "
                    "georgia_southern)."
                ),
                "description": (
                    "Federal judicial district in which the individual was "
                    "sentenced (USSC DISTRICT codes 32 = Northern District "
                    "of Georgia, 33 = Middle, 34 = Southern). This is a "
                    "sub-state FEDERAL COURT geography, not a county "
                    "geography — districts span many counties and do not "
                    "join the counties dimension."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "all",
                "short_description": (
                    "Gender of the sentenced individual (male / female), "
                    "plus the all total."
                ),
                "description": (
                    "Gender demographic of the sentenced individuals (USSC "
                    "MONSEX): male and female rows are mutually exclusive; "
                    "the all row is the unfiltered total. Individuals with "
                    "unreported gender (roughly 0-6%% depending on year) and "
                    "the small number coded Other (a MONSEX code added in "
                    "FY2024; no Georgia rows yet) are included in the all "
                    "row only, so male + female can fall slightly short of "
                    "all. No race breakdown is served: the USSC public "
                    "race recode (NEWRACE) collapses to "
                    "White/Black/Hispanic/Other and cannot be expressed in "
                    "the platform's mutually exclusive race vocabulary."
                ),
            },
            {
                "name": "offenders_sentenced",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "key_metric": True,
                "example": 477,
                "short_description": (
                    "Individuals sentenced in the district, fiscal year, and "
                    "demographic group."
                ),
                "description": (
                    "Number of individuals sentenced under the federal "
                    "Sentencing Reform Act in the district and fiscal year "
                    "for the demographic group (one bronze record per "
                    "sentenced individual; USSC counts sentenced "
                    "individuals, not case filings or terminations). "
                    "Additive across the three districts; within a "
                    "district-year, sum only within one demographic "
                    "category (male + female <= all; the difference is "
                    "individuals with unreported or Other gender)."
                ),
            },
            {
                "name": "num_with_prison_sentence",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "example": 430,
                "short_description": (
                    "Individuals in the group whose sentence included "
                    "reported prison time — the denominator of the sentence-"
                    "length statistics."
                ),
                "description": (
                    "Number of sentenced individuals in the group whose "
                    "sentence included a reported prison term (USSC SENTTOT "
                    "non-missing). Probation-only sentences, fine-only "
                    "sentences, and the rare records whose prison term "
                    "could not be determined are excluded — this is the "
                    "exact denominator of avg_sentence_months and "
                    "median_sentence_months. From FY2018 the USSC reports "
                    "time-served-only sentences as 0.03 months instead of "
                    "missing, which slightly widens this count from FY2018 "
                    "onward."
                ),
            },
            {
                "name": "avg_sentence_months",
                "type": "float64",
                "example": 78.42,
                "null_meaning": (
                    "NULL only when no individual in the group had a "
                    "reported prison term (num_with_prison_sentence = 0)."
                ),
                "short_description": (
                    "Mean prison sentence in months among those receiving "
                    "prison time (life counted as 470 months; determinate "
                    "sentences capped at 469.99)."
                ),
                "description": (
                    "Mean prison-sentence length in months among "
                    "individuals whose sentence included reported prison "
                    "time (denominator: num_with_prison_sentence). Follows "
                    "the Commission's length-of-imprisonment methodology "
                    "(SENTTCAP): life sentences carry the 470-month code "
                    "and determinate sentences longer than 470 months are "
                    "capped at 469.99, uniformly "
                    "across all years; probation-only sentences are "
                    "excluded entirely; alternative confinement (home/"
                    "community detention) months are not counted. Months, "
                    "not a 0-1 rate — no unit class applies, so the [0.01, "
                    "470] range is enforced by an authored quality check. "
                    "From FY2018, time-served-only sentences enter as 0.03 "
                    "months (previously excluded as missing), a small "
                    "downward nudge documented by the source."
                ),
            },
            {
                "name": "median_sentence_months",
                "type": "float64",
                "example": 60.0,
                "null_meaning": (
                    "NULL only when no individual in the group had a "
                    "reported prison term (num_with_prison_sentence = 0)."
                ),
                "short_description": (
                    "Median prison sentence in months among those receiving "
                    "prison time (life counted as 470 months)."
                ),
                "description": (
                    "Median prison-sentence length in months among "
                    "individuals whose sentence included reported prison "
                    "time (same population, capping, and caveats as "
                    "avg_sentence_months; linear interpolation between the "
                    "two middle values for even counts). More robust than "
                    "the mean to the handful of very long or life (470) "
                    "sentences in a district-year."
                ),
            },
        ],
        source=(
            "US Sentencing Commission, Individual Offender Datafiles "
            "(Standardized Research Data, opafy{YY}nid), FY2002-FY2025"
        ),
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        suppressed_to_null=False,
        usage=(
            "Cite the US Sentencing Commission's individual offender "
            "datafiles. year is the FEDERAL FISCAL YEAR (Oct-Sep). Counts "
            "are sentenced individuals, never case filings — do not "
            "reconcile against court-caseload statistics. Sum "
            "offenders_sentenced across districts freely, but within one "
            "demographic category only (male + female <= all). Never "
            "average avg_sentence_months across rows without weighting by "
            "num_with_prison_sentence. Sentence-length statistics describe "
            "prison sentences only (probation-only sentences excluded) "
            "with life counted as 470 months and determinate sentences "
            "longer than 470 months capped at 469.99 (Commission SENTTCAP "
            "convention)."
        ),
        limitations=(
            "The grain is the federal judicial district (sub-state court "
            "geography): rows do not join the counties dimension and there "
            "is no county_fips column. year is the federal fiscal year "
            "(Oct 1 - Sep 30). The platform's year floor is 2000; this "
            "series begins at FY2002, the earliest zip published in the "
            "source's consistently-coded public datafile era. Sentence "
            "length uses USSC SENTTOT with the SENTTCAP cap (life = 470, "
            "determinate sentences over 470 months capped at 469.99, "
            "Commission convention), so a district-year's mean is "
            "insensitive to the exact length of extreme sentences; from "
            "FY2018 time-served-only sentences enter as 0.03 months rather "
            "than missing (source methodology refinement, small effect). "
            "Individuals with unreported gender (roughly 0-6%% by year) and "
            "the FY2024+ Other gender code appear in the all rows only, so "
            "male + female can fall slightly short of all. Departure/"
            "variance rates, offense-type, drug-type, race, age, and "
            "citizenship breakdowns are deliberately not served: the USSC "
            "recoded departure/variance and offense-categorization "
            "variables at FY2018 (a methodology break that must be "
            "versioned, not pooled) and the public race recode conflates "
            "all non-White/Black/Hispanic groups into Other. The source "
            "publishes complete unsuppressed microdata; NULL appears only "
            "in the sentence-length statistics of a group with no prison "
            "sentences."
        ),
        quality_checks=[
            {
                "name": "no_pre_2000_years",
                "description": (
                    "Platform year floor: every served row is fiscal year "
                    "2000 or later (the source series here starts at "
                    "FY2002)."
                ),
                "dimension": "consistency",
                "query": "SELECT COUNT(*) FROM {object} WHERE year < 2000",
                "mustBe": 0,
            },
            {
                "name": "offenders_sentenced_at_least_one",
                "description": (
                    "Rows exist only for groups with at least one sentenced "
                    "individual — a zero or NULL count means the "
                    "aggregation broke."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE offenders_sentenced "
                    "IS NULL OR offenders_sentenced < 1"
                ),
                "mustBe": 0,
            },
            {
                "name": "gender_counts_within_all_total",
                "description": (
                    "Gender rows are mutually exclusive subsets of the all "
                    "row: male + female offenders_sentenced must not exceed "
                    "the all total for any district-year (individuals with "
                    "unreported/Other gender make the inequality strict)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, federal_district, "
                    "MAX(CASE WHEN demographic = 'all' THEN "
                    "offenders_sentenced END) AS all_cnt, "
                    "SUM(CASE WHEN demographic IN ('male', 'female') THEN "
                    "offenders_sentenced END) AS gender_sum "
                    "FROM {object} GROUP BY year, federal_district"
                    ") WHERE gender_sum IS NOT NULL AND (all_cnt IS NULL "
                    "OR gender_sum > all_cnt)"
                ),
                "mustBe": 0,
            },
            {
                "name": "all_row_present_per_district_year",
                "description": (
                    "Every (year, federal_district) group carries its "
                    "demographic='all' total row."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, federal_district, "
                    "MAX(CASE WHEN demographic = 'all' THEN 1 ELSE 0 END) "
                    "AS has_all FROM {object} "
                    "GROUP BY year, federal_district"
                    ") WHERE has_all = 0"
                ),
                "mustBe": 0,
            },
            {
                "name": "three_districts_every_year",
                "description": (
                    "Georgia has exactly three federal judicial districts "
                    "and each sentences hundreds of individuals every "
                    "fiscal year — a year with fewer district values means "
                    "a lost file or broken filter."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, COUNT(DISTINCT federal_district) AS nd "
                    "FROM {object} GROUP BY year"
                    ") WHERE nd != 3"
                ),
                "mustBe": 0,
            },
            {
                "name": "prison_sentence_count_within_offenders",
                "description": (
                    "The sentence-length denominator is a subset of the "
                    "group: 0 <= num_with_prison_sentence <= "
                    "offenders_sentenced on every row."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "num_with_prison_sentence IS NULL OR "
                    "num_with_prison_sentence < 0 OR "
                    "num_with_prison_sentence > offenders_sentenced"
                ),
                "mustBe": 0,
            },
            {
                "name": "sentence_stats_co_null_with_denominator",
                "description": (
                    "avg/median sentence months are NULL exactly when the "
                    "group has no reported prison sentences "
                    "(num_with_prison_sentence = 0), and present otherwise."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(num_with_prison_sentence = 0 AND "
                    "(avg_sentence_months IS NOT NULL OR "
                    "median_sentence_months IS NOT NULL)) OR "
                    "(num_with_prison_sentence > 0 AND "
                    "(avg_sentence_months IS NULL OR "
                    "median_sentence_months IS NULL))"
                ),
                "mustBe": 0,
            },
            {
                "name": "avg_sentence_months_within_cap",
                "description": (
                    "Mean sentence months lies in (0, 470]: SENTTOT's floor "
                    "is 0.01, determinate sentences over 470 months are "
                    "capped at 469.99, and 470 is the life code (SENTTCAP "
                    "convention), so any value outside the range means the "
                    "masking/capping regressed. Authored because months "
                    "have no unit class."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "avg_sentence_months IS NOT NULL AND "
                    "(avg_sentence_months <= 0 OR avg_sentence_months > 470)"
                ),
                "mustBe": 0,
            },
            {
                "name": "median_sentence_months_within_cap",
                "description": (
                    "Median sentence months lies in (0, 470] (same bounds "
                    "and rationale as avg_sentence_months)."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "median_sentence_months IS NOT NULL AND "
                    "(median_sentence_months <= 0 OR "
                    "median_sentence_months > 470)"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
