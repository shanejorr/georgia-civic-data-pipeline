"""Transform FJC IDB criminal defendant microdata into a district-year fact table.

Source: Federal Judicial Center Integrated Database (IDB), criminal defendants
filed/terminated/pending, FY1996-present (``cr96on_0.zip`` -> ``cr96on.txt``:
tab-delimited, 144 columns, ~6.3M national defendant-level rows). Gold
aggregates Georgia's three federal judicial districts to
``federal_district x year`` (fiscal year) with four count metrics.

System dependency: the zip uses **Deflate64** ("enhanced-64k") compression,
which Python's stdlib ``zipfile`` cannot decompress (NotImplementedError).
The member is therefore STREAMED with the system ``unzip -p`` binary via
subprocess -- ``unzip`` must be on PATH. The zip is never extracted to disk
(provenance contract) and the 3.5 GB member is never materialized: rows are
filtered line-by-line to Georgia districts and the fiscal-year floor before
anything is retained.

Design decisions (from bronze-data-structure.md, the "Criminal IDB: 1996 to
Present" codebook, and data-cleaning-standards):

- **Grain: federal_district x year, FY2000 forward.** ``federal_district``
  holds ``georgia_northern`` (DISTRICT 3E) / ``georgia_middle`` (3G) /
  ``georgia_southern`` (3J). Filtering uses DISTRICT only -- never CIRCUIT
  (Georgia moved from the 5th to the 11th Circuit in 1981, so a circuit
  filter is unsafe by convention for this source family). The IDB reaches
  back to FY1996 in this file (and to 1970 in a separate period file that is
  not ingested), but gold is intentionally floored at FY2000 per the project
  year floor; pre-floor Georgia rows are counted and recorded as filtered
  events (``pre_2000_fiscal_year_floor``), never materialized into gold.
- **A FISCALYR row is a snapshot record, not a filing.** Per the codebook,
  each fiscal-year snapshot contains one record per defendant *filed OR
  terminated during that FY, or pending at its end* -- so raw row counts per
  FISCALYR triple-count pending defendants. Metrics therefore use the
  AOUSC's own 0/1 count flags, which the codebook prescribes for matching
  the published "D" tables: ``defendants_filed`` = sum(CTFILTRN) ("Count
  Filings Including Transfers") and ``defendants_terminated`` = sum(CTTRTRN)
  ("Count Terminations Including Transfers") per district-FY. Although the
  2016 codebook says the flags were created in FY2012 and back-calculated to
  FY2005, the current extract carries them fully populated (0/1, zero
  missing) for every year 1996-2026 -- verified empirically, and CTTRTRN
  matches "TERMDATE falls in the row's FISCALYR" exactly in every Georgia
  fiscal year, confirming the flag semantics. The *including transfers*
  variants are used because that is the AOUSC district-table convention
  (an inter-district transfer is real workload for the receiving district);
  the excluding-transfers variants differ by under ~1.5%% in every Georgia
  year, and the double-count caveat is documented in the contract.
- **``felony_defendants_filed``**: filed defendants (CTFILTRN=1) whose most
  severe filing charge is a felony (FOFFLVL1 = 4; codebook: 1 = petty
  offense, 3 = class A misdemeanor, 4 = felony). Using the first/most-severe
  filing offense is the documented simple choice -- FTITLE1/FOFFLVL1 is the
  charge the AOUSC itself sorts to slot 1 by severity. FOFFLVL1 is fully
  populated (never -8) on flagged filings in this extract; unknown values
  hard-fail rather than miscount.
- **``defendants_convicted``**: terminated defendants (CTTRTRN=1) whose
  final disposition is a conviction -- DISP1 in {4 guilty plea, 5 nolo
  contendere, 8 convicted by court, 9 convicted by jury, 17/19 guilty but
  insane}. The codebook states the AOUSC uses TERMINATION DISPOSITION CODE 1
  when reporting a defendant's final disposition. NARA commitments (10) and
  pretrial diversion (12) are deliberately NOT counted as convictions. Any
  DISP1 value outside the codebook vocabulary hard-fails.
- **Sentence metrics are deliberately excluded.** PRISTOT/PROBTOT/FINETOT
  encode life imprisonment (-4), death (-5), sealed (-3), guilty-no-sentence
  (-2), under-one-month (-1) and missing (-8) as sentinel values; NULLing
  the sentinels before averaging (the only §4b-compliant option) would
  silently drop exactly the most severe sentences from a mean, producing a
  biased statistic. Sentencing at the same district grain is the USSC
  district_sentences topic's job. No offense-mix categorical is emitted
  either -- lean counts beat speculative categoricals (orchestrator design).
- **No county geography.** The IDB COUNTY column is documented unreliable
  for criminal data (bronze-data-structure.md ETL #6), so this topic serves
  a NEW sub-state, non-county grain: no ``county_fips`` column exists, the
  counties dimension does not apply, and every row is tagged
  ``detail_level='federal_district'`` so export writes
  ``federal_districts.parquet`` (the shared federal-district detail level;
  the validator's geography checks skip absent columns).
  ``federal_district`` is a plain grain categorical, not a dimension FK.
- **PII never leaves the stream.** Bronze rows are defendant-level and carry
  NAME plus docket/defendant identifiers. The streaming parser retains only
  the six analytic fields (FISCALYR, DISTRICT, FOFFLVL1, DISP1, CTFILTRN,
  CTTRTRN) -- NAME and every case identifier are never selected, and gold is
  pure district-year aggregates.
- **Densified grid; missing district-year = true zero.** The IDB is a
  complete census of federal criminal defendants, so after filtering, a
  district-fiscal-year with no rows means zero filings, not missing data.
  The 3-district x year grid is densified with zero-filled metrics (a no-op
  today -- every cell has activity) and the contract enforces exactly three
  district rows per year and never-NULL metrics.
- **Snapshot anchors.** The stream hard-fails unless the national data-row
  count (6,299,908) and the per-district Georgia totals (3E=80,277,
  3G=45,937, 3J=43,188 across FY1996-2026) match bronze-data-structure.md
  exactly. A bronze refresh (blocked anyway by the checksum freshness gate
  until re-analysis) must update these anchors from the refreshed structure
  doc.
- **Dedup tie-break.** A single bronze member aggregated in one group_by
  pass makes natural-key collisions impossible by construction; the
  collision guard runs first, and ``deduplicate_by_levels(
  sort_col="defendants_filed")`` remains as the documented safety net
  (prefer the row with the larger filing count) should a future refresh ever
  add an overlapping file.
- **No §4b masks.** Every metric is a sum of validated 0/1 flags -- no
  impossible values can occur; domain membership of every consumed code is
  hard-asserted instead. The source publishes complete unsuppressed
  microdata (``suppressed_to_null=False``).
- **Quality checks (§15b).** No partition-sums or co-null shapes exist (no
  proportion family, no NULLs); the authored checks are the subset facts
  (felony <= filed, convicted <= terminated) and the structural facts
  (FY2000 floor, complete 3-district grid, never-NULL non-negative counts).
- **FY2026 is a partial year** (the IDB updates quarterly; this snapshot was
  retrieved 2026-07-04, mid-FY2026) -- documented in the contract.
"""

import io
import logging
import shutil
import subprocess
from collections import Counter
from pathlib import Path

import polars as pl

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

TOPIC = "district_filings"
BRONZE_DIR = Path("data/bronze/criminal_justice/federal_justice/district_filings")
GOLD_DIR = Path("data/gold/criminal_justice/district_filings")
ZIP_PATH = BRONZE_DIR / "cr96on_0.zip"
ZIP_MEMBER = "cr96on.txt"
SOURCE_URL = (
    "https://www.fjc.gov/research/idb/criminal-defendants-filed-terminated-"
    "and-pending-fy-1996-present"
)

# Project year floor: the IDB reaches back to FY1996 in this file, but gold
# serves FY2000 forward only (pre-floor rows are counted, recorded as
# filtered events, and never materialized).
YEAR_FLOOR = 2000

# Snapshot QA anchors from bronze-data-structure.md (2026-07-04 checksums).
# The freshness gate blocks a changed zip until re-analysis; a legitimate
# refresh must update these anchors from the refreshed structure doc.
EXPECTED_NATIONAL_ROWS = 6_299_908
EXPECTED_GA_ROWS_BY_DISTRICT = {"3E": 80_277, "3G": 45_937, "3J": 43_188}
EXPECTED_COLUMN_COUNT = 144

# Georgia's federal judicial districts (codebook DISTRICT vocabulary).
# Filter on DISTRICT only -- never CIRCUIT (5th -> 11th Circuit recode).
DISTRICT_MAP: dict[str, str] = {
    "3E": "georgia_northern",
    "3G": "georgia_middle",
    "3J": "georgia_southern",
}
FEDERAL_DISTRICT_VALUES: list[str] = sorted(DISTRICT_MAP.values())

# The six analytic fields retained from the 144-column layout. NAME, docket
# and defendant identifiers are never selected (PII stays in the stream).
NEEDED_COLUMNS: list[str] = [
    "FISCALYR",
    "DISTRICT",
    "FOFFLVL1",
    "DISP1",
    "CTFILTRN",
    "CTTRTRN",
]

# Era signature: the FY1996-forward NewSTATS layout. Detected on the header
# (column inspection), never on year ranges.
ERA = "newstats_fy1996_forward_144col"
ERA_SIGNATURE_COLUMNS = ["FISCALYR", "DISTRICT", "CTFILTRN", "CTTRTRN", "D2FOFFCD1"]

# Codebook vocabularies. Any observed value outside these sets hard-fails --
# a new upstream code must be classified deliberately, never miscounted.
KNOWN_DISP1_CODES = {"-8"} | {str(c) for c in (*range(0, 6), *range(8, 22))}
# DISP1 codes that mean the defendant was convicted (codebook, "Termination
# Disposition Code"): 4 guilty plea, 5 nolo contendere, 8 convicted by court
# after trial, 9 convicted by jury after trial, 17/19 guilty but insane.
# NARA commitments (10) and pretrial diversion (12) are NOT convictions.
CONVICTION_DISP1_CODES = {"4", "5", "8", "9", "17", "19"}
# Filing offense level of the most severe filing charge: 1 petty offense,
# 3 class A misdemeanor, 4 felony, -8 missing.
KNOWN_FOFFLVL1_CODES = {"-8", "1", "3", "4"}
FELONY_FOFFLVL1 = "4"
KNOWN_FLAG_VALUES = {"0", "1"}

METRIC_COLUMNS: list[str] = [
    "defendants_filed",
    "felony_defendants_filed",
    "defendants_terminated",
    "defendants_convicted",
]

# Gold fact column order. `detail_level` is carried through dedup and export
# splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "federal_district",
    *METRIC_COLUMNS,
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "federal_district": pl.Utf8,
    **{c: pl.Int64 for c in METRIC_COLUMNS},
    "detail_level": pl.Utf8,
}

NATURAL_KEYS: list[str] = ["year", "federal_district", "detail_level"]


# =============================================================================
# Streaming bronze read (Deflate64 zip -> filtered Georgia rows)
# =============================================================================


def _open_member_stream() -> subprocess.Popen:
    """Open ``unzip -p`` streaming the tab-delimited member to stdout.

    The zip's Deflate64 compression is unsupported by stdlib ``zipfile``, so
    the system ``unzip`` binary does the decompression; the member is never
    extracted to disk.
    """
    if not ZIP_PATH.exists():
        raise FileNotFoundError(f"Bronze zip missing: {ZIP_PATH}")
    if shutil.which("unzip") is None:
        raise RuntimeError(
            "System dependency missing: `unzip` is required to stream the "
            f"Deflate64-compressed {ZIP_PATH.name} (stdlib zipfile cannot "
            "decompress compression method 9)."
        )
    return subprocess.Popen(
        ["unzip", "-p", str(ZIP_PATH), ZIP_MEMBER],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _parse_header(header_line: str) -> dict[str, int]:
    """Validate the 144-column era signature and return name -> index."""
    header = header_line.rstrip("\r\n").split("\t")
    if len(header) != EXPECTED_COLUMN_COUNT:
        raise ValueError(
            f"{ZIP_MEMBER}: header has {len(header)} columns, expected "
            f"{EXPECTED_COLUMN_COUNT} -- layout changed, re-run "
            "/bronze-data-structure before transforming"
        )
    missing_sig = [c for c in ERA_SIGNATURE_COLUMNS if c not in header]
    if missing_sig:
        raise ValueError(
            f"{ZIP_MEMBER}: era signature columns missing {missing_sig} -- "
            f"not the {ERA} layout"
        )
    missing = [c for c in NEEDED_COLUMNS if c not in header]
    if missing:
        raise ValueError(f"{ZIP_MEMBER}: required columns missing: {missing}")
    return {name: i for i, name in enumerate(header)}


def _stream_georgia_rows(manifest: TransformManifest) -> pl.DataFrame:
    """Stream the national member and retain Georgia rows at/above the floor.

    One pass over ~6.3M lines: a cheap 3-field split reads FISCALYR and
    DISTRICT for every row (national per-FY accounting); only Georgia rows at
    or above the fiscal-year floor are fully split, field-count validated,
    and retained -- and only the six analytic fields, never NAME or case
    identifiers. Pre-floor Georgia rows are counted for the manifest but
    never materialized.
    """
    proc = _open_member_stream()
    assert proc.stdout is not None
    stream = io.TextIOWrapper(proc.stdout, encoding="utf-8", errors="replace")

    header_line = stream.readline()
    if not header_line:
        raise ValueError(f"{ZIP_MEMBER}: empty stream (no header)")
    col_index = _parse_header(header_line)
    needed_idx = [col_index[c] for c in NEEDED_COLUMNS]

    national_by_fy: Counter[int] = Counter()
    ga_by_fy: Counter[int] = Counter()
    ga_by_district: Counter[str] = Counter()
    retained: list[tuple[str, ...]] = []
    raw_rows = 0

    for line in stream:
        line = line.rstrip("\r\n")
        if not line:
            continue
        raw_rows += 1
        # Cheap prefilter: FISCALYR is field 0, DISTRICT field 2 -- a
        # 3-split avoids fully splitting ~6.15M non-Georgia rows.
        parts = line.split("\t", 3)
        if len(parts) < 4:
            raise ValueError(
                f"{ZIP_MEMBER}: malformed data line {raw_rows} "
                f"(<4 tab-separated fields): {line[:120]!r}"
            )
        try:
            fiscal_year = int(parts[0])
        except ValueError as exc:
            raise ValueError(
                f"{ZIP_MEMBER}: non-numeric FISCALYR {parts[0]!r} at data "
                f"line {raw_rows}"
            ) from exc
        national_by_fy[fiscal_year] += 1
        district = parts[2]
        if district not in DISTRICT_MAP:
            continue
        ga_by_district[district] += 1
        ga_by_fy[fiscal_year] += 1
        if fiscal_year < YEAR_FLOOR:
            # Pre-floor Georgia rows: counted (filtered events below), never
            # materialized -- the project year floor is FY2000.
            continue
        fields = line.split("\t")
        if len(fields) != EXPECTED_COLUMN_COUNT:
            raise ValueError(
                f"{ZIP_MEMBER}: Georgia row at data line {raw_rows} has "
                f"{len(fields)} fields, expected {EXPECTED_COLUMN_COUNT}"
            )
        retained.append(tuple(fields[i] for i in needed_idx))

    stderr = proc.stderr.read() if proc.stderr else b""
    if proc.wait() != 0:
        raise RuntimeError(
            f"unzip -p {ZIP_PATH.name} {ZIP_MEMBER} failed "
            f"(exit {proc.returncode}): {stderr.decode(errors='replace')[:500]}"
        )

    _verify_anchors_and_record(
        manifest, col_index, raw_rows, national_by_fy, ga_by_fy, ga_by_district
    )
    logger.info(
        "Retained %s Georgia rows at/above FY%d", f"{len(retained):,}", YEAR_FLOOR
    )

    return pl.DataFrame(
        retained,
        schema={c: pl.Utf8 for c in NEEDED_COLUMNS},
        orient="row",
    )


def _verify_anchors_and_record(
    manifest: TransformManifest,
    col_index: dict[str, int],
    raw_rows: int,
    national_by_fy: Counter,
    ga_by_fy: Counter,
    ga_by_district: Counter,
) -> None:
    """Verify snapshot anchors, then record stream accounting on the manifest.

    Anchors pin extraction fidelity to bronze-data-structure.md (a bronze
    refresh -- blocked by the checksum freshness gate until re-analysis --
    must update them from the refreshed structure doc). Bronze rows are the
    national per-FY row counts; the non-Georgia drop and the pre-floor
    Georgia drop are explicit filtered events, so bronze-vs-gold arithmetic
    stays explainable.
    """
    if raw_rows != EXPECTED_NATIONAL_ROWS:
        raise ValueError(
            f"{ZIP_MEMBER}: streamed {raw_rows:,} data rows, expected "
            f"{EXPECTED_NATIONAL_ROWS:,} (bronze-data-structure.md) -- "
            "refresh the structure doc and these anchors together"
        )
    if dict(ga_by_district) != EXPECTED_GA_ROWS_BY_DISTRICT:
        raise ValueError(
            f"Georgia district row counts {dict(ga_by_district)} != expected "
            f"{EXPECTED_GA_ROWS_BY_DISTRICT} (bronze-data-structure.md)"
        )
    logger.info(
        "Streamed %s: %s national rows; Georgia rows by district %s (anchors verified)",
        ZIP_MEMBER,
        f"{raw_rows:,}",
        dict(ga_by_district),
    )

    manifest.record_file(
        ZIP_PATH,
        max(national_by_fy),
        ERA,
        raw_rows,
        sorted(col_index, key=col_index.get),
    )
    # Parity by construction (any malformed line raised during streaming);
    # recorded for the standard accounting trail -- no-ops when parsed == raw.
    manifest.record_read_loss(max(national_by_fy), ZIP_PATH.name, raw_rows, raw_rows)
    for fy in sorted(national_by_fy):
        manifest.record_bronze(fy, national_by_fy[fy])
        non_ga = national_by_fy[fy] - ga_by_fy.get(fy, 0)
        if non_ga:
            manifest.record_filtered(fy, non_ga, "non_georgia_district_row")
        if fy < YEAR_FLOOR and ga_by_fy.get(fy, 0):
            manifest.record_filtered(fy, ga_by_fy[fy], "pre_2000_fiscal_year_floor")
    pre_floor_ga = sum(n for fy, n in ga_by_fy.items() if fy < YEAR_FLOOR)
    logger.info(
        "Year floor FY%d: dropped %s pre-floor Georgia rows (FY%d-FY%d)",
        YEAR_FLOOR,
        f"{pre_floor_ga:,}",
        min(ga_by_fy),
        YEAR_FLOOR - 1,
    )


# =============================================================================
# Aggregation
# =============================================================================


def _assert_code_domains(ga: pl.DataFrame) -> None:
    """Hard-fail on any code outside the codebook vocabulary.

    A future refresh introducing a new disposition/offense-level code must be
    classified deliberately (conviction or not; felony or not) -- silently
    treating it as "not counted" would understate the affected metric.
    """
    for col, known in [
        ("CTFILTRN", KNOWN_FLAG_VALUES),
        ("CTTRTRN", KNOWN_FLAG_VALUES),
        ("DISP1", KNOWN_DISP1_CODES),
        ("FOFFLVL1", KNOWN_FOFFLVL1_CODES),
    ]:
        observed = set(ga[col].unique().to_list())
        unknown = observed - known
        if unknown:
            raise ValueError(
                f"{col}: values outside the codebook vocabulary {sorted(unknown)} "
                "-- classify them deliberately before serving"
            )


def _aggregate_to_district_year(
    ga: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """Aggregate defendant rows to the densified district x fiscal-year grid.

    Metrics are sums of the AOUSC 0/1 count flags (see module docstring for
    the flag semantics and why raw row counts would be wrong). The grid is
    densified because the IDB is a complete census: a missing district-year
    means zero filings (true zero), never missingness -- a no-op on current
    data, where every cell has activity.
    """
    _assert_code_domains(ga)
    ga = ga.with_columns(
        pl.col("FISCALYR").cast(pl.Int32).alias("year"),
        (pl.col("CTFILTRN") == "1").alias("_filed"),
        (pl.col("CTTRTRN") == "1").alias("_terminated"),
    )

    agg = (
        ga.group_by("year", "DISTRICT")
        .agg(
            pl.col("_filed").sum().cast(pl.Int64).alias("defendants_filed"),
            (pl.col("_filed") & (pl.col("FOFFLVL1") == FELONY_FOFFLVL1))
            .sum()
            .cast(pl.Int64)
            .alias("felony_defendants_filed"),
            pl.col("_terminated").sum().cast(pl.Int64).alias("defendants_terminated"),
            (pl.col("_terminated") & pl.col("DISP1").is_in(CONVICTION_DISP1_CODES))
            .sum()
            .cast(pl.Int64)
            .alias("defendants_convicted"),
        )
        .sort("year", "DISTRICT")
    )

    # Densify: full district x fiscal-year grid, zero-filled. True zeros by
    # census completeness (documented in the contract).
    years = range(YEAR_FLOOR, int(agg["year"].max()) + 1)
    grid = pl.DataFrame(
        {"year": [y for y in years for _ in DISTRICT_MAP]},
        schema={"year": pl.Int32},
    ).with_columns(
        pl.Series("DISTRICT", sorted(DISTRICT_MAP) * len(years), dtype=pl.Utf8)
    )
    dense = grid.join(agg, on=["year", "DISTRICT"], how="left")
    zero_filled = dense.filter(pl.col("defendants_filed").is_null()).height
    if zero_filled:
        logger.warning(
            "Densified %d district-year cells with zero activity (true zeros "
            "by census completeness): %s",
            zero_filled,
            dense.filter(pl.col("defendants_filed").is_null())
            .select("year", "DISTRICT")
            .to_dicts(),
        )
    dense = dense.with_columns([pl.col(c).fill_null(0) for c in METRIC_COLUMNS])

    # District code -> canonical federal_district categorical.
    dense = dense.with_columns(
        pl.col("DISTRICT").replace_strict(DISTRICT_MAP).alias("federal_district")
    )
    manifest.record_categorical(
        column="federal_district",
        map_dict=DISTRICT_MAP,
        bronze_series=ga["DISTRICT"],
        gold_series=dense["federal_district"],
    )

    # Single uniform grain: the federal district IS the geography, so every
    # row is a 'federal_district'-file row (see module docstring).
    return dense.with_columns(pl.lit("federal_district").alias("detail_level")).drop(
        "DISTRICT"
    )


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for district_filings."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Stream-filter the national member to Georgia rows, then aggregate
    #    to the densified district x fiscal-year grid.
    ga = _stream_georgia_rows(manifest)
    result = _aggregate_to_district_year(ga, manifest)
    logger.info(
        "Aggregated %s defendant rows -> %d district-year rows (FY%d-FY%d)",
        f"{ga.height:,}",
        result.height,
        int(result["year"].min()),
        int(result["year"].max()),
    )

    # 2. Harmonize to the gold schema (single era, so a one-frame pass).
    combined = pl.concat(harmonize_columns([result], STANDARD_COLUMNS, TARGET_TYPES))

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # would mean an aggregation bug and must raise, not be silently deduped.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: one bronze member aggregated in a single group_by pass makes
    # collisions impossible by construction; sort_col "defendants_filed" is
    # the documented safety net (prefer the row with the larger filing count)
    # should a future refresh ever add an overlapping file.
    combined = deduplicate_by_levels(
        combined,
        {"federal_district": ["year", "federal_district"]},
        sort_col="defendants_filed",
    )

    # 4. No geography nulling (no geography columns exist -- the counties
    # dimension does not apply to this district-grain topic) and no §4b
    # masks (metrics are sums of hard-asserted 0/1 flags; impossible values
    # cannot occur).
    spike = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike.details)
    validate_output(
        combined,
        required_non_null=["year", "federal_district", "detail_level"],
    )
    for col in METRIC_COLUMNS:
        if combined[col].null_count():
            raise ValueError(f"{col}: NULLs after densification (must be true zeros)")

    # 5. Manifest stats on the FINAL DataFrame, then export.
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(
        combined,
        GOLD_DIR,
        STANDARD_COLUMNS,
        detail_level_files=FEDERAL_DISTRICT_DETAIL_LEVEL_FILES,
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
    ``detail_level`` -- the contract's properties (and the validator's
    schema check) follow it.
    """
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Criminal defendants filed, terminated, and convicted in "
            "Georgia's three federal judicial districts (Northern, Middle, "
            "Southern), by federal fiscal year (October 1 - September 30), "
            "FY2000 forward, aggregated from the Federal Judicial Center's "
            "Integrated Database (IDB) defendant-level records. Counts "
            "follow the Administrative Office of the U.S. Courts (AOUSC) "
            "published-table conventions: a defendant is counted as filed or "
            "terminated in a fiscal year via the AOUSC count flags "
            "(including inter-district transfers), a felony filing is a "
            "defendant whose most severe filing charge is a felony, and a "
            "conviction is a termination whose final disposition is a "
            "guilty plea, nolo contendere plea, bench or jury conviction, "
            "or guilty-but-insane verdict. This is a federal-district-grain "
            "dataset: districts span many counties, so no county geography "
            "applies."
        ),
        title="Federal Criminal Defendants Filed by District",
        summary=(
            "Criminal defendants filed, terminated, and convicted in "
            "Georgia's three federal court districts per federal fiscal "
            "year, FY2000 onward, from the Federal Judicial Center's "
            "Integrated Database."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2025,
                "description": (
                    "Federal FISCAL year (October 1 of the prior calendar "
                    "year through September 30; e.g. 2025 = Oct 2024 - Sep "
                    "2025) -- the IDB snapshot fiscal year. Serving starts "
                    "at FY2000 (project year floor); the final year is "
                    "partial until the fiscal year closes (FY2026 covers "
                    "roughly its first three quarters in the current "
                    "snapshot)."
                ),
            },
            {
                "name": "federal_district",
                "type": "string",
                "nullable": False,
                "validValues": FEDERAL_DISTRICT_VALUES,
                "example": "georgia_northern",
                "short_description": (
                    "Georgia federal judicial district: georgia_northern "
                    "(Atlanta), georgia_middle (Macon/Columbus), "
                    "georgia_southern (Savannah/Augusta)."
                ),
                "description": (
                    "Georgia federal judicial district where the case was "
                    "located: georgia_northern (Atlanta; IDB code 3E), "
                    "georgia_middle (Macon/Columbus; 3G), georgia_southern "
                    "(Savannah/Augusta; 3J). Federal districts span many "
                    "counties and do not align with any county geography -- "
                    "this column is the dataset's own geographic grain, not "
                    "a foreign key to the counties dimension."
                ),
            },
            {
                "name": "defendants_filed",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "key_metric": True,
                "example": 607,
                "short_description": (
                    "Criminal defendants filed in the district during the "
                    "fiscal year (AOUSC counting rules, including "
                    "inter-district transfers)."
                ),
                "description": (
                    "Number of criminal defendants filed in the district "
                    "during the fiscal year, counted with the AOUSC's "
                    "'Count Filings Including Transfers' flag -- the "
                    "convention of the published Judicial Business D "
                    "tables. Includes defendants received by inter-district "
                    "transfer and proceedings recommenced by reopen, "
                    "remand, appeal, or retrial; a defendant transferred "
                    "between districts is counted in both, so summing "
                    "districts can double-count a small number of "
                    "defendants (the excluding-transfers variant differs "
                    "by under 1.5%% in every Georgia year). 0 is a true "
                    "zero (complete census). Petty offenses assigned to "
                    "magistrate judges are not reported to the AOUSC and "
                    "are therefore not counted."
                ),
            },
            {
                "name": "felony_defendants_filed",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "example": 599,
                "short_description": (
                    "Filed defendants whose most severe filing charge is a "
                    "felony (subset of defendants_filed)."
                ),
                "description": (
                    "Filed defendants (subset of defendants_filed) whose "
                    "most severe filing charge carries the felony offense "
                    "level (IDB FOFFLVL1 = 4). The remainder of "
                    "defendants_filed are class A misdemeanor or petty-"
                    "offense filings. Classification uses the first (most "
                    "severe) of up to five filing charges, as sorted by the "
                    "AOUSC's severity code; the offense level is populated "
                    "for every counted filing in the served years. 0 is a "
                    "true zero."
                ),
            },
            {
                "name": "defendants_terminated",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "example": 575,
                "short_description": (
                    "Criminal defendants whose case terminated in the "
                    "district during the fiscal year (AOUSC counting "
                    "rules, including inter-district transfers)."
                ),
                "description": (
                    "Number of criminal defendants whose case was "
                    "terminated (closed) in the district during the fiscal "
                    "year, counted with the AOUSC's 'Count Terminations "
                    "Including Transfers' flag (equivalent to the "
                    "termination date falling inside the fiscal year -- "
                    "verified exactly in every served year). Terminations "
                    "in a fiscal year include cases filed in earlier years, "
                    "so this is not a subset of the same year's "
                    "defendants_filed. 0 is a true zero."
                ),
            },
            {
                "name": "defendants_convicted",
                "type": "int64",
                "unit": "count",
                "nullable": False,
                "example": 507,
                "short_description": (
                    "Terminated defendants convicted on at least one count "
                    "(guilty plea, nolo, bench/jury conviction; subset of "
                    "defendants_terminated)."
                ),
                "description": (
                    "Terminated defendants (subset of "
                    "defendants_terminated) whose final disposition on the "
                    "most severely disposed charge is a conviction: guilty "
                    "plea, nolo contendere plea, conviction by the court "
                    "after trial, conviction by jury, or guilty-but-insane "
                    "verdict (IDB DISP1 codes 4, 5, 8, 9, 17, 19 -- the "
                    "field the AOUSC uses to report a defendant's final "
                    "disposition). Dismissals, acquittals, pretrial "
                    "diversions, NARA commitments, transfers, and mistrials "
                    "are not counted as convictions. 0 is a true zero."
                ),
            },
        ],
        source=(
            "Federal Judicial Center, Integrated Database (IDB) -- criminal "
            "defendants filed, terminated, and pending, FY1996 to present"
        ),
        source_url=SOURCE_URL,
        update_frequency=(
            "quarterly (IDB refresh); served as an annual fiscal-year series"
        ),
        year_range=year_range,
        suppressed_to_null=False,
        usage=(
            "Cite the Federal Judicial Center's Integrated Database (IDB), "
            "criminal defendants file (US government work, public domain). "
            "Counts follow AOUSC published-table conventions including "
            "inter-district transfers: a transferred defendant is counted "
            "in both districts, so statewide sums can slightly double-count "
            "(under 1.5%%). Filings and terminations are independent "
            "fiscal-year event counts -- terminations include cases filed "
            "in earlier years, so defendants_convicted relates to "
            "defendants_terminated (same year), never to defendants_filed. "
            "Rates per resident require an external population denominator "
            "(not served here)."
        ),
        limitations=(
            "The source reaches back to FY1996 in the IDB's current-format "
            "criminal file (and to 1970 in an earlier-format archive that "
            "is not ingested), but this dataset is intentionally floored at "
            "FY2000 (project year floor). The final fiscal year is partial "
            "until it closes -- FY2026 covers roughly its first three "
            "quarters in the current snapshot (the IDB updates quarterly), "
            "so treat the latest year as provisional; its filing counts may "
            "also include late-reported proceedings that commenced in the "
            "prior fiscal year (subsequent quarterly refreshes reconcile "
            "these to the proceeding year), so year-over-year comparisons "
            "should exclude the in-progress year. Data are served at "
            "federal-district grain only: the IDB's county field is "
            "documented as unreliable for criminal cases, and federal "
            "districts span many counties, so no county breakdown is "
            "possible. Sentence length, probation, and fine metrics are "
            "deliberately not served: the IDB encodes life sentences, death "
            "sentences, and sealed sentences as sentinel codes whose "
            "exclusion would bias any average (the U.S. Sentencing "
            "Commission district_sentences topic covers sentencing at the "
            "same district grain). Petty offenses assigned to magistrate "
            "judges are not reported to the AOUSC. Counts include "
            "inter-district transfers (counted in both districts) and "
            "reopened proceedings, per the AOUSC published-table "
            "convention. Zero values are true zeros (complete census of "
            "federal criminal defendants); the source has no suppression."
        ),
        quality_checks=[
            {
                "name": "no_pre_2000_fiscal_years",
                "description": (
                    "Gold serves FY2000 forward only (project year floor) "
                    "-- earlier fiscal years exist in the source and must "
                    "never appear."
                ),
                "dimension": "consistency",
                "query": "SELECT COUNT(*) FROM {object} WHERE year < 2000",
                "mustBe": 0,
            },
            {
                "name": "district_year_grid_complete",
                "description": (
                    "The grid is densified: every served fiscal year must "
                    "carry exactly one row for each of the three Georgia "
                    "federal districts (a missing district-year would be a "
                    "silently dropped true zero)."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM ("
                    "SELECT year, COUNT(DISTINCT federal_district) AS n_districts, "
                    "COUNT(*) AS n_rows FROM {object} GROUP BY year"
                    ") WHERE n_districts != 3 OR n_rows != 3"
                ),
                "mustBe": 0,
            },
            {
                "name": "metrics_never_null",
                "description": (
                    "The IDB is a complete census and the grid is "
                    "zero-densified -- every metric is a real count, so a "
                    "NULL means the densification broke, never real "
                    "missingness."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "defendants_filed IS NULL OR felony_defendants_filed IS NULL "
                    "OR defendants_terminated IS NULL OR defendants_convicted "
                    "IS NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "felony_filed_within_filed",
                "description": (
                    "felony_defendants_filed counts a subset of "
                    "defendants_filed (most severe filing charge is a "
                    "felony), so it can never exceed the filing count."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "felony_defendants_filed > defendants_filed"
                ),
                "mustBe": 0,
            },
            {
                "name": "convicted_within_terminated",
                "description": (
                    "defendants_convicted counts a subset of "
                    "defendants_terminated (terminations whose final "
                    "disposition is a conviction), so it can never exceed "
                    "the termination count."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "defendants_convicted > defendants_terminated"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
