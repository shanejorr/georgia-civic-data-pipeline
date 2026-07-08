"""Transform bronze postsecondary_c11 files into gold fact tables.

Source: Governor's Office of Student Achievement (GOSA) — Postsecondary C11
Report, publication years 2012-2024 (13 bronze files; one HS graduating
cohort each, cohorts 2010-2022). For every Georgia public high school, plus
official district and state rollups, the report publishes two raw counts per
demographic subgroup: total high school graduates and how many of those
graduates enrolled in any postsecondary institution (in-state or
out-of-state, 2-year or 4-year), tracked roughly one year after graduation.

Design decisions (from bronze-data-structure.md and data-cleaning-standards;
authored non-interactively — judgment calls recorded here):

- **Metric names are the pre-decided sibling-pair vocabulary**:
  ``num_graduates`` (Int64, unit count — matches the §16 canonical name for
  HS-graduate counts) and ``num_enrolled_in_college`` (Int64, unit count —
  shared with the postsecondary_c12 sibling so the pair stays
  join-compatible). No rates are published in bronze; consumers derive the
  enrollment rate as num_enrolled_in_college / num_graduates.
- **Four eras, one long-format target.** Era 1 (2012 file, cohort 2010):
  XLSX, three-row header, 13 demographic groups (no Pacific Islander).
  Era 2 (2013-2014, cohorts 2011-2012): XLSX, two-row header (no TFS note
  row), 14 groups. Era 3 (2015-2022, cohorts 2013-2020): XLSX, three-row
  header, 14 groups. Era 4 (2023-2024, cohorts 2021-2022): flat CSV, 14
  groups, plus constant ``#RPT_NAME`` and publication-year
  ``REPORTING_YEAR`` columns (both dropped; ``#RPT_NAME`` is guarded as a
  constant). Era detection is by column signature on the stitched/flat
  frame; the Era 2 vs Era 3 split (identical columns, different header
  depth) is refined from the located header-row index.
- **Excel header stitching bypasses ``read_bronze_file``.** The shared
  reader has no multi-row-header support and would promote the row-0 TFS
  note (Eras 1/3) to column names. Files are read via pandas
  ``header=None`` with the same ``dtype=str`` + ``na_values`` the shared
  XLSX path uses; the metric-header row is located by its literal
  ``School Year`` first cell (never a hardcoded index), the sparse
  demographic-group row above it is forward-filled across merged cells, and
  the two are stitched into unique ``{group}|{metric}`` names. Sheets are
  always read by index 0 — sheet names vary per year and the 2014/2022
  ``SQL`` reference sheets are thereby skipped. Excel reads load whole
  sheets (raw == parsed by construction), so read loss is structurally
  zero; header rows are sheet structure, not data records.
- **Year is the HS graduating-cohort year**, read from the in-file
  ``School Year`` / ``SCHOOL_YEAR`` column (single value per file) — NOT
  the filename year. The consistent filename = cohort + 2 offset and (Era
  4) ``REPORTING_YEAR`` = filename year are both enforced as cross-checks,
  so a mis-shipped file cannot mislabel a whole cohort.
- **Asian / Pacific Islander uses the split convention (§5b).** Eras 2-4
  publish separate Asian and Pacific Islander groups, and the §5b math
  test confirms the seven race buckets are mutually exclusive: their
  state-level sums equal the all-students total EXACTLY in 2011-2018,
  2020, and 2022 (within 8 in 2019 and 1 in 2021 — tiny unreported-race
  residues, preserved). Era 1 (cohort 2010) has no Pacific Islander group
  and its six race buckets fall SHORT of the total by 957 graduates
  (~1.1%% — far more than the ~0.1-0.2%% NHPI share): students outside the
  six buckets are dropped from the race axis, not folded into "Asian"
  (2010-11 was the federal race-reporting transition year), so bare
  ``Asian`` stays ``asian`` in every era — never remapped to the combined
  bucket. No rollup rows are synthesized.
- **2010 Pacific Islander rows are absent, not fabricated.** Era 1 has no
  Pacific Islander columns, so gold simply has no pacific_islander rows
  for year 2010 (there is no bronze source to NULL out; preserving bronze
  granularity beats emitting fabricated all-NULL rows). Pinned by the
  pacific_islander_absent_in_2010 / present_2011_onward quality checks.
- **Suppression is per-cell and one-directional.** The publisher encodes
  ``CASE WHEN {metric} < 10 THEN 'TFS'`` per metric cell (confirmed by the
  2014/2022 SQL sheets), so ``num_enrolled_in_college`` can be suppressed
  while ``num_graduates`` is published — but never the reverse, because
  enrolled <= graduates means a suppressed num_graduates (< 10) forces
  the enrolled count below 10 too. Verified across all 13 files: zero
  rows with num_graduates NULL and num_enrolled_in_college published;
  zero published values below 10; zero rows with enrolled > graduates;
  zero suppressed cells on state rows. All four facts are pinned as
  quality checks. ~51-53%% of metric cells are TFS in every file —
  bronze-real, uniform across years.
- **No §4b masks.** A full scan of all 13 bronze files found no impossible
  values: every published cell is a non-negative integer >= 10, and
  num_enrolled_in_college never exceeds num_graduates. No ``_null_*``
  helper exists and the manifest carries no ``masked_values`` section.
- **Geography.** detail_level derives from the ``ALL`` sentinels in the
  (district code, school code) pair: ALL/ALL -> state, code/ALL ->
  district, code/code -> school. Sentinels become NULL inline and the
  shared ``null_aggregate_geography`` re-applies the domain rules.
  district_code is zfill(3) (preserves 7-digit charter codes; never
  truncate), school_code zfill(4) (bronze padding varies by year:
  integers 2012/2015-2019, zero-padded strings 2013-2014/2020-2024).
- **Dedup tie-break.** Each bronze file covers exactly one cohort year,
  years never overlap across files, and the per-file
  (district, school) grain is unique (verified: zero duplicate pairs in
  all 13 files), so no duplicates are expected. ``sort_col=
  "num_graduates"`` is the documented safety net: prefer the row with a
  published (non-null, larger) graduate count over a suppressed
  placeholder.
- **No demographic-subgroup collisions.** The 13/14 bronze labels map to
  13/14 distinct canonical keys via the shared aliases (verified), so
  ``aggregate_demographic_collisions`` is not needed; the collision guard
  in ``main()`` would surface any surprise.
"""

import logging
from pathlib import Path

import pandas as pd
import polars as pl

from src.utils.demographics import (
    DEMOGRAPHIC_ALIASES,
    normalize_demographic_column,
)
from src.utils.metadata import write_data_dictionary
from src.utils.readers import (
    SUPPRESSION_VALUES,
    extract_year_from_filename,
    list_bronze_files,
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

TOPIC = "postsecondary_c11"
BRONZE_DIR = Path("data/bronze/education/gosa/postsecondary_c11")
GOLD_DIR = Path("data/gold/education/postsecondary_c11")
SOURCE_URL = "https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data"

# Filename year = HS graduating-cohort year + 2 in every file (publication
# lag); enforced as a cross-check on the in-file cohort year.
FILENAME_YEAR_OFFSET = 2

# Aggregate-row sentinel in the district-code (state rows) and school-code
# (state + district rows) columns. Becomes NULL in gold, never a key value.
GEOGRAPHY_SENTINEL = "ALL"

# The two metric labels on the Excel metric-header row. Any other label in a
# metric position fails the stitch loudly (rename-coverage guard, §4.1).
HS_GRADS_LABEL = "Total High School Graduates"
IN_COLLEGE_LABEL = (
    "Number of High School Graduates Enrolled in Postsecondary Institution"
)

# Stitched-name suffixes for the two metrics of each demographic group.
HS_SUFFIX = "hs_grads"
COLLEGE_SUFFIX = "in_college"

# Era 4 constant-column guard value.
ERA4_RPT_NAME = "C11 Report Metrics"

# Era-detection signatures on the stitched (Excel) or flat (CSV) columns,
# most-specific first. Era 1's signature is a subset of the Era 2/3 frames
# (which add Pacific Islander), so era_23 must be listed before era_1; the
# Era 2 vs Era 3 split (same columns, 2- vs 3-row header) is refined from
# the located header-row index in transform_file().
ERA_SIGNATURES: dict[str, list[str]] = {
    "era_4_2023_2024_csv": [
        "#RPT_NAME",
        "REPORTING_YEAR",
        "SCHOOL_YEAR",
        "SCHOOL_DISTRCT_CD",
        "INSTN_NUMBER",
        "TOTAL_HS_GRADS",
        "TOTAL_ENROLLED_IN_COLLEGE",
    ],
    "era_23_xlsx_14_groups": [
        "School Year",
        "School District Code",
        "School Code",
        f"Pacific Islander|{HS_SUFFIX}",
        f"Pacific Islander|{COLLEGE_SUFFIX}",
    ],
    "era_1_2012_xlsx_13_groups": [
        "School Year",
        "School District Code",
        "School Code",
        f"Asian|{HS_SUFFIX}",
        f"Asian|{COLLEGE_SUFFIX}",
    ],
}

# Demographic-group tokens embedded in the Era 4 CSV column names. TOTAL is
# irregular: its enrolled column is TOTAL_ENROLLED_IN_COLLEGE, not
# TOTAL_IN_COLLEGE. All tokens resolve via the shared DEMOGRAPHIC_ALIASES.
CSV_GROUP_TOKENS: list[str] = [
    "TOTAL",
    "MALE",
    "FEMALE",
    "FRL",
    "MIGRANT",
    "LEP",
    "SWD",
    "HISPANIC",
    "TWOORMORE",
    "NATIVE",
    "ASIAN",
    "BLACK",
    "WHITE",
    "PACIFIC",
]

# Expected demographic-group counts per era (structural guard).
EXPECTED_GROUP_COUNTS: dict[str, int] = {
    "era_1_2012_xlsx_13_groups": 13,
    "era_2_2013_2014_xlsx_2row_header": 14,
    "era_3_2015_2022_xlsx_3row_header": 14,
    "era_4_2023_2024_csv": 14,
}

# Gold fact column order. `detail_level` is carried through dedup /
# geography-nulling / export-splitting, then dropped by export_to_parquet().
STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "num_graduates",
    "num_enrolled_in_college",
    "detail_level",
]

TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "demographic": pl.Utf8,
    "num_graduates": pl.Int64,
    "num_enrolled_in_college": pl.Int64,
    "detail_level": pl.Utf8,
}

METRIC_COLUMNS: list[str] = ["num_graduates", "num_enrolled_in_college"]

NATURAL_KEYS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "demographic",
    "detail_level",
]

# The 14 canonical demographic keys this topic publishes (13 in 2010, which
# lacks pacific_islander). Used for the contract enum and quality checks.
DEMOGRAPHIC_VALUES: list[str] = sorted(
    [
        "all",
        "asian",
        "black",
        "economically_disadvantaged",
        "english_learners",
        "female",
        "hispanic",
        "male",
        "migrant",
        "multiracial",
        "native_american",
        "pacific_islander",
        "students_with_disabilities",
        "white",
    ]
)

# The seven mutually exclusive race buckets (split Asian/PI convention —
# see module docstring). At the state level these sum to the `all` total
# exactly in most years (within 8 in 2019 and 1 in 2021), which the
# race-partition quality check enforces for 2011+ (2010 lacks the Pacific
# Islander bucket and undercounts by ~1.1%, so it is excluded).
RACE_BUCKET_KEYS: list[str] = [
    "asian",
    "black",
    "hispanic",
    "multiracial",
    "native_american",
    "pacific_islander",
    "white",
]

# Observed maximum state-level |race sum - all| residue in 2011+ (8 in the
# 2019 cohort, 1 in 2021, 0 elsewhere): a handful of graduates without a
# reported race. The race-partition check tolerates exactly this.
RACE_PARTITION_TOLERANCE = 8


# =============================================================================
# Casting helpers
# =============================================================================


def _to_int_expr(col: str) -> pl.Expr:
    """Cast an all-string bronze count column to Int64 via Float64.

    Suppression markers (TFS) already arrived as NULL from the na_values
    read; the Float64 hop tolerates decimal-formatted counts ("16.0")
    without silently nulling them, and ``strict=False`` nulls any other
    non-numeric residue instead of failing the cast.
    """
    return pl.col(col).str.strip_chars().cast(pl.Float64, strict=False).cast(pl.Int64)


# =============================================================================
# Bronze reading (Excel multi-row-header stitching)
# =============================================================================


def _read_excel_stitched(path: Path) -> tuple[pl.DataFrame, int, dict]:
    """Read one bronze Excel file, stitching its 2- or 3-row header.

    The shared reader has no multi-row-header support, so the sheet is read
    directly via pandas with the same ``dtype=str`` + ``na_values`` the
    shared XLSX path uses (TFS cells arrive as NULL). The metric-header row
    is located by its literal ``School Year`` first cell — row 2 in the
    three-row layout (Eras 1/3, where row 0 is the TFS note), row 1 in the
    two-row layout (Era 2) — never a hardcoded index. The sparse
    demographic-group row above it is forward-filled across merged cells
    and combined with the metric row into unique ``{group}|{metric}``
    column names. Sheet 0 is always taken by index (names vary per year;
    the 2014/2022 ``SQL`` reference sheets are skipped by construction).

    Args:
        path: Bronze XLSX file path.

    Returns:
        ``(df, header_rows, loss)`` — the stitched all-Utf8 frame, the
        number of header rows above the data (2 or 3, used to refine Era 2
        vs Era 3), and a read-loss dict. Excel reads load whole sheets via
        pandas (nothing is dropped), so raw == parsed by construction; the
        header rows are sheet structure, not data records.
    """
    pdf = pd.read_excel(
        path,
        sheet_name=0,
        header=None,
        dtype=str,
        na_values=list(SUPPRESSION_VALUES),
        engine="openpyxl",
    )

    # Locate the metric-header row by its literal first cell. Searching the
    # first 4 rows tolerates both the 2-row and 3-row layouts.
    header_idx = next(
        (
            i
            for i in range(min(4, len(pdf)))
            if str(pdf.iloc[i, 0]).strip() == "School Year"
        ),
        None,
    )
    if header_idx is None or header_idx < 1:
        raise ValueError(
            f"{path.name}: could not locate the 'School Year' metric-header "
            f"row in the first 4 rows — unexpected sheet layout"
        )

    # Demographic-group labels sit one row above the metric row, populated
    # only above the first column of each merged pair — forward-fill them.
    demo_row = pdf.iloc[header_idx - 1].ffill()
    metric_row = pdf.iloc[header_idx]

    names: list[str] = []
    for col in range(pdf.shape[1]):
        metric = str(metric_row[col]).strip()
        if col < 5:
            # Identifier columns carry their own names on the metric row.
            names.append(metric)
            continue
        group = str(demo_row[col]).strip()
        if metric == HS_GRADS_LABEL:
            names.append(f"{group}|{HS_SUFFIX}")
        elif metric == IN_COLLEGE_LABEL:
            names.append(f"{group}|{COLLEGE_SUFFIX}")
        else:
            # Rename-coverage guard (§4.1): an unrecognized metric label
            # would otherwise silently drop a source column.
            raise ValueError(
                f"{path.name}: unrecognized metric header {metric!r} in "
                f"column {col} (group {group!r})"
            )

    data = pdf.iloc[header_idx + 1 :].reset_index(drop=True)
    data.columns = names
    df = pl.from_pandas(data)
    loss = {"raw_rows": df.height, "parsed_rows": df.height, "format": "xlsx"}
    return df, header_idx, loss


# =============================================================================
# Metric-pair resolution per era
# =============================================================================


def _excel_group_pairs(df: pl.DataFrame, label: str) -> dict[str, tuple[str, str]]:
    """Map each demographic-group label to its (hs_grads, in_college) pair.

    Every stitched metric column is consumed; a group missing either half of
    its pair raises (a half-pair means the header stitch misfired).
    """
    pairs: dict[str, dict[str, str]] = {}
    for col in df.columns:
        if "|" not in col:
            continue
        group, suffix = col.rsplit("|", 1)
        pairs.setdefault(group, {})[suffix] = col
    incomplete = {
        g: m for g, m in pairs.items() if set(m) != {HS_SUFFIX, COLLEGE_SUFFIX}
    }
    if incomplete:
        raise ValueError(f"{label}: incomplete metric pairs: {incomplete}")
    return {g: (m[HS_SUFFIX], m[COLLEGE_SUFFIX]) for g, m in sorted(pairs.items())}


def _csv_group_pairs(df: pl.DataFrame, label: str) -> dict[str, tuple[str, str]]:
    """Map each Era 4 CSV group token to its (hs_grads, in_college) pair.

    TOTAL is irregular (TOTAL_ENROLLED_IN_COLLEGE). All expected columns
    must exist (rename-coverage guard); unexpected metric-shaped extras are
    surfaced loudly so a new subgroup can never be silently ignored.
    """
    pairs: dict[str, tuple[str, str]] = {}
    for token in CSV_GROUP_TOKENS:
        hs_col = f"{token}_HS_GRADS"
        college_col = (
            "TOTAL_ENROLLED_IN_COLLEGE" if token == "TOTAL" else f"{token}_IN_COLLEGE"
        )
        missing = [c for c in (hs_col, college_col) if c not in df.columns]
        if missing:
            raise ValueError(f"{label}: expected CSV column(s) missing: {missing}")
        pairs[token] = (hs_col, college_col)

    consumed = {c for pair in pairs.values() for c in pair} | {
        "#RPT_NAME",
        "REPORTING_YEAR",
        "SCHOOL_YEAR",
        "SCHOOL_DISTRCT_CD",
        "SCHOOL_DSTRCT_NM",
        "INSTN_NUMBER",
        "INSTN_NAME",
    }
    extras = [c for c in df.columns if c not in consumed]
    if extras:
        logger.warning("%s: unexpected bronze columns ignored: %s", label, extras)
    return pairs


# =============================================================================
# Wide-to-long unpivot (shared across eras)
# =============================================================================


def _unpivot_to_long(
    df: pl.DataFrame,
    pairs: dict[str, tuple[str, str]],
    year: int,
    district_col: str,
    school_col: str,
    manifest: TransformManifest,
) -> pl.DataFrame:
    """Unpivot one wide bronze frame into the tidy gold shape.

    One sub-frame per demographic group (each group contributes two metric
    columns), concatenated into one row per (entity, demographic) — the §9
    multi-metric unpivot pattern.

    Args:
        df: Wide all-Utf8 bronze frame.
        pairs: Demographic-group label -> (hs_grads col, in_college col).
        year: HS graduating-cohort year (already validated).
        district_col: Bronze district-code column name.
        school_col: Bronze school-code column name.
        manifest: Manifest for the demographic categorical recording.

    Returns:
        Long DataFrame with STANDARD_COLUMNS.
    """
    district_clean = pl.col(district_col).str.strip_chars()
    school_clean = pl.col(school_col).str.strip_chars()

    frames: list[pl.DataFrame] = []
    for group, (hs_col, college_col) in pairs.items():
        frames.append(
            df.select(
                pl.lit(year).cast(pl.Int32).alias("year"),
                # ALL sentinels -> NULL inline (never carried into gold);
                # zfill pads 3-digit district / 4-digit school codes and
                # passes 7-digit charter codes through unchanged.
                pl.when(district_clean == GEOGRAPHY_SENTINEL)
                .then(None)
                .otherwise(district_clean.str.zfill(3))
                .alias("district_code"),
                pl.when(school_clean == GEOGRAPHY_SENTINEL)
                .then(None)
                .otherwise(school_clean.str.zfill(4))
                .alias("school_code"),
                pl.lit(group).alias("_demographic_raw"),
                _to_int_expr(hs_col).alias("num_graduates"),
                _to_int_expr(college_col).alias("num_enrolled_in_college"),
                # Detail level from the ALL sentinels: ALL/ALL -> state,
                # code/ALL -> district, code/code -> school.
                pl.when(district_clean == GEOGRAPHY_SENTINEL)
                .then(pl.lit("state"))
                .when(school_clean == GEOGRAPHY_SENTINEL)
                .then(pl.lit("district"))
                .otherwise(pl.lit("school"))
                .alias("detail_level"),
            )
        )
    long_df = pl.concat(frames)

    # Demographics: shared-alias normalization (§5). Bare "Asian" stays
    # `asian` — this topic uses the split convention (§5b; see docstring).
    long_df = long_df.with_columns(
        normalize_demographic_column("_demographic_raw").alias("demographic")
    )
    # Record the effective slice of the shared alias map (§4.3a): only the
    # aliases this file's labels actually hit, so the manifest stays
    # reviewable while the unmapped guard still flags any unplaced label.
    observed_upper = {
        str(v).strip().upper()
        for v in long_df["_demographic_raw"].drop_nulls().unique().to_list()
    }
    effective_map = {
        k: v for k, v in DEMOGRAPHIC_ALIASES.items() if k in observed_upper
    }
    manifest.record_categorical(
        column="demographic",
        map_dict=effective_map,
        bronze_series=long_df["_demographic_raw"],
        gold_series=long_df["demographic"],
    )
    return long_df.select(STANDARD_COLUMNS)


# =============================================================================
# Per-file transform
# =============================================================================


def _single_value(df: pl.DataFrame, col: str, label: str) -> str:
    """Return the single non-null value of a column, raising otherwise."""
    values = df[col].drop_nulls().str.strip_chars().unique().to_list()
    if len(values) != 1:
        raise ValueError(f"{label}: expected one {col} value, got {values}")
    return values[0]


def transform_file(path: Path, manifest: TransformManifest) -> pl.DataFrame:
    """Read one bronze file, detect its era, and transform it to gold shape.

    Year resolution: the in-file cohort-year column is authoritative; the
    filename must equal cohort + 2 (the series' publication lag) and, in
    Era 4, REPORTING_YEAR must equal the filename year — so a mis-shipped
    file cannot silently mislabel a whole cohort.

    Args:
        path: Bronze file path.
        manifest: Manifest for read-loss / file / bronze-count /
            categorical recording.

    Returns:
        Gold-shaped DataFrame with STANDARD_COLUMNS.
    """
    filename_year = extract_year_from_filename(path.name)
    if filename_year is None:
        raise ValueError(f"Cannot extract year from filename: {path.name}")

    if path.suffix.lower() == ".csv":
        # All-string read (§4.3b): codes keep leading zeros, sentinels are
        # never inference casualties, TFS arrives as NULL.
        df, loss = read_bronze_file(path, infer_schema_length=0, return_loss=True)
        header_rows = 1
    else:
        df, header_rows, loss = _read_excel_stitched(path)

    era = detect_era_by_columns(df, ERA_SIGNATURES)
    if era is None:
        raise ValueError(f"{path.name}: no era signature matched columns {df.columns}")
    if era == "era_23_xlsx_14_groups":
        # Eras 2 and 3 share one column set; the structural difference is
        # the header depth (2-row in 2013-2014, 3-row with the TFS note in
        # 2015-2022), already located by the stitcher.
        era = (
            "era_2_2013_2014_xlsx_2row_header"
            if header_rows == 1
            else "era_3_2015_2022_xlsx_3row_header"
        )

    if era == "era_4_2023_2024_csv":
        # Constant guard: any other value means non-C11 rows are mixed in.
        rpt_name = _single_value(df, "#RPT_NAME", path.name)
        if rpt_name != ERA4_RPT_NAME:
            raise ValueError(f"{path.name}: unexpected #RPT_NAME {rpt_name!r}")
        reporting_year = int(_single_value(df, "REPORTING_YEAR", path.name))
        if reporting_year != filename_year:
            raise ValueError(
                f"{path.name}: REPORTING_YEAR {reporting_year} disagrees "
                f"with filename year {filename_year}"
            )
        year_col, district_col, school_col = (
            "SCHOOL_YEAR",
            "SCHOOL_DISTRCT_CD",
            "INSTN_NUMBER",
        )
        pairs = _csv_group_pairs(df, path.name)
    else:
        year_col, district_col, school_col = (
            "School Year",
            "School District Code",
            "School Code",
        )
        pairs = _excel_group_pairs(df, path.name)

    # The cohort year is the gold `year`; filename = cohort + 2 always.
    year = int(_single_value(df, year_col, path.name))
    if filename_year != year + FILENAME_YEAR_OFFSET:
        raise ValueError(
            f"{path.name}: filename year {filename_year} != cohort year "
            f"{year} + {FILENAME_YEAR_OFFSET}"
        )

    # Structural guard: the demographic-group count per era is fixed (13 in
    # 2012, 14 everywhere else); a different count means a layout change.
    expected_groups = EXPECTED_GROUP_COUNTS[era]
    if len(pairs) != expected_groups:
        raise ValueError(
            f"{path.name} ({era}): expected {expected_groups} demographic "
            f"groups, found {len(pairs)}: {sorted(pairs)}"
        )

    manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])
    manifest.record_file(path, year, era, df.height, df.columns)
    manifest.record_bronze(year, df.height)
    logger.info(
        "Processing %s as %s (cohort year %d, %d rows x %d groups)",
        path.name,
        era,
        year,
        df.height,
        len(pairs),
    )

    return _unpivot_to_long(df, pairs, year, district_col, school_col, manifest)


# =============================================================================
# Main pipeline
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for postsecondary_c11."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    # 1. Read + transform every bronze file (read-loss accounted per file).
    all_dfs: list[pl.DataFrame] = []
    for path in list_bronze_files(BRONZE_DIR):
        result = transform_file(path, manifest)
        if result is not None and result.height > 0:
            all_dfs.append(result)
    if not all_dfs:
        raise ValueError(f"No bronze data produced any rows under {BRONZE_DIR}")

    # 2. Harmonize columns/dtypes across eras and concatenate.
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)
    logger.info("Combined %d rows across %d files", combined.height, len(all_dfs))

    # 3. Collision guard BEFORE dedup: duplicate keys with divergent metrics
    # mean an alias/era-routing bug and must raise, not be deduped away.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Tie-break: each bronze file is a distinct cohort year with no overlap,
    # and the per-file grain is unique (verified across all 13 files), so no
    # duplicates are expected; prefer the row with a published (non-null,
    # larger) num_graduates over a suppressed placeholder as the safety net.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code", "demographic"],
        district_keys=["year", "district_code", "demographic"],
        state_keys=["year", "demographic"],
        sort_col="num_graduates",
    )

    # 4. Geography nulling (shared domain rules). No §4b masks: the full
    # bronze scan found no impossible values (see module docstring).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # Pre-export sanity. Suppression NULL rates are heavy (~51-53% of metric
    # cells) but uniform across years, so no spike is expected.
    spike_result = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike_result.status == "warning":
        logger.warning("NULL-rate spikes: %s", spike_result.details)
    validate_output(combined, required_non_null=["year", "detail_level", "demographic"])

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
    """Emit the ODCS contract and gold README via ``write_data_dictionary``.

    Kept out of ``main()`` so the pipeline flow stays readable. The column
    declaration order MUST match STANDARD_COLUMNS minus ``detail_level`` —
    the contract's properties (and the validator's schema check) follow it.
    """
    race_list = ", ".join(f"'{k}'" for k in RACE_BUCKET_KEYS)
    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Postsecondary enrollment outcomes (GOSA C11 report) for Georgia "
            "public high school graduating cohorts: the number of high "
            "school graduates and the number of those graduates who "
            "enrolled in any postsecondary institution (in-state or "
            "out-of-state, 2-year or 4-year, tracked roughly one year after "
            "graduation), by demographic subgroup, for every Georgia public "
            "high school plus official district and state rollups. Covers "
            "HS graduating cohorts 2010-2022 (published 2012-2024). No "
            "rates are published — consumers derive the enrollment rate as "
            "num_enrolled_in_college / num_graduates."
        ),
        title="Postsecondary Enrollment of HS Graduates (C11, Nationwide)",
        summary=(
            "How many Georgia public high school graduates enrolled in "
            "college anywhere in the US, by school, district, and "
            "demographic subgroup, 2010-2022 cohorts."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "nullable": False,
                "example": 2022,
                "description": (
                    "High school graduating-cohort year (spring calendar "
                    "year of graduation, e.g. 2022 for the class of "
                    "2021-22) — NOT the publication year, which is "
                    "consistently cohort + 2. Read from the source's "
                    "School Year / SCHOOL_YEAR column and cross-checked "
                    "against the filename offset."
                ),
            },
            {
                "name": "district_code",
                "type": "string",
                "example": "601",
                "description": (
                    "GOSA district code (FK to districts dimension): "
                    "3-digit zero-padded county/city codes or 7-digit "
                    "state-charter codes. NULL on state-level rows."
                ),
            },
            {
                "name": "school_code",
                "type": "string",
                "example": "0103",
                "description": (
                    "GOSA school code, zero-padded to 4 characters "
                    "(composite FK to schools dimension with district_code; "
                    "not globally unique on its own). NULL on district- and "
                    "state-level rows."
                ),
            },
            {
                "name": "demographic",
                "type": "string",
                "nullable": False,
                "example": "all",
                "validValues": DEMOGRAPHIC_VALUES,
                "short_description": (
                    "Student subgroup the row covers (race, gender, economic, "
                    "or special-population); 'all' is the cohort total. Race "
                    "uses the split asian / pacific_islander convention."
                ),
                "description": (
                    "Demographic subgroup (FK to the global demographics "
                    "dimension). Race buckets use the post-1997 OMB SPLIT "
                    "convention — asian and pacific_islander are separate, "
                    "mutually exclusive groups (the seven race buckets sum "
                    "to the 'all' total at the state level within a residue "
                    "of at most 8 graduates in every year from 2011). The "
                    "2010 cohort (published 2012) has no pacific_islander "
                    "rows — the source did not publish the group that year "
                    "— and its six race buckets undercount the total by "
                    "~1.1%% (race-reporting transition year). 'all' is the "
                    "unfiltered total and overlaps every other value; "
                    "subgroups are mutually exclusive only within their own "
                    "category (race, gender, economic, special population)."
                ),
            },
            {
                "name": "num_graduates",
                "type": "int64",
                "unit": "count",
                "example": 162,
                "null_meaning": (
                    "Suppressed by GOSA (TFS = Too Few Students: the cell's "
                    "count is below the n=10 reporting threshold)."
                ),
                "description": (
                    "Number of students in the demographic subgroup who "
                    "graduated high school in the cohort year. Published "
                    "values are always >= 10 because GOSA suppresses "
                    "smaller cells per metric (TFS); ~51-53%% of metric "
                    "cells are suppressed in every file, concentrated in "
                    "small subgroups (Migrant, Pacific Islander, American "
                    "Indian/Alaskan Native, LEP) at school level. If "
                    "num_graduates is suppressed, num_enrolled_in_college "
                    "is always suppressed too (enrolled <= graduates)."
                ),
            },
            {
                "name": "num_enrolled_in_college",
                "type": "int64",
                "unit": "count",
                "key_metric": True,
                "example": 100,
                "short_description": (
                    "Count of the cohort's graduates who enrolled in any US "
                    "college within about a year; divide by num_graduates "
                    "for the college-going rate."
                ),
                "null_meaning": (
                    "Suppressed by GOSA (TFS = Too Few Students: the cell's "
                    "count is below the n=10 reporting threshold). Can be "
                    "suppressed while num_graduates is published, because "
                    "suppression is applied per metric cell."
                ),
                "description": (
                    "Of the subgroup's high school graduates, the number "
                    "who enrolled in any postsecondary institution "
                    "(in-state or out-of-state, 2-year or 4-year), tracked "
                    "roughly one year after graduation. Never exceeds "
                    "num_graduates where both are published (enforced by a "
                    "quality check). Named to match the "
                    "postsecondary_c12 sibling for cross-topic "
                    "comparability. Published values are always >= 10 "
                    "(GOSA's per-cell suppression threshold)."
                ),
            },
        ],
        source="GOSA",
        source_url=SOURCE_URL,
        update_frequency="annual",
        year_range=year_range,
        partitioned_by=["year"],
        # Derived prose plus the suppression-scale and convention caveats
        # consumers need.
        limitations=(
            "Suppressed cells are NULL (not zero): GOSA suppresses any "
            "metric cell below the n=10 reporting threshold (TFS), which "
            "blanks ~51-53%% of metric cells in every file — small "
            "subgroups (Migrant, Pacific Islander, American Indian/Alaskan "
            "Native, LEP) are almost entirely suppressed at school level, "
            "and summing only published subgroup counts undercounts true "
            "totals (use district or state rows for official aggregates). "
            "Suppression is per metric cell, so num_enrolled_in_college "
            "can be NULL while num_graduates is published. year is the HS "
            "graduating-cohort year, not the publication year (cohort + "
            "2). The 2010 cohort has no pacific_islander rows and its race "
            "buckets undercount the total by ~1.1%%. State rows have NULL "
            "district_code and school_code; district rows have NULL "
            "school_code. The race axis uses the split asian / "
            "pacific_islander convention — not comparable row-for-row with "
            "combined-convention topics without aggregating these rows at "
            "query time."
        ),
        notes=[
            (
                "Four bronze eras, one gold shape: 2012 XLSX (three-row "
                "header, 13 demographic groups — no Pacific Islander), "
                "2013-2014 XLSX (two-row header, 14 groups), 2015-2022 "
                "XLSX (three-row header, 14 groups), 2023-2024 CSV (flat "
                "header, 14 groups). Excel demographic labels live on a "
                "merged header row and are forward-filled before "
                "unpivoting."
            ),
            (
                "year is the HS graduating-cohort year read from the "
                "in-file School Year / SCHOOL_YEAR column; the filename "
                "carries the publication year (= cohort + 2, enforced as a "
                "cross-check). Era 4's REPORTING_YEAR (publication year) "
                "and constant #RPT_NAME are dropped."
            ),
            (
                "Suppression marker is the literal 'TFS' (Too Few "
                "Students). The publisher's own SQL (embedded in the 2014 "
                "and 2022 files) shows CASE WHEN {metric} < 10 THEN 'TFS', "
                "i.e. per-cell suppression at n=10 — so published values "
                "are always >= 10 (pinned by a quality check) and "
                "num_enrolled_in_college can be suppressed alone, but a "
                "suppressed num_graduates always implies a suppressed "
                "num_enrolled_in_college (enrolled <= graduates; pinned)."
            ),
            (
                "Asian / Pacific Islander uses the SPLIT convention (§5b): "
                "the source publishes separate Asian and Pacific Islander "
                "groups from 2011, and the seven race buckets sum exactly "
                "to the all-students total at the state level in 2011-2018, "
                "2020 and 2022 (within 8 in 2019 and 1 in 2021 — tiny "
                "unreported-race residues, preserved as published). Bare "
                "'Asian' in the 2010 file is genuinely Asian-only: the six "
                "race buckets fall SHORT of the total by 957 graduates "
                "(~1.1%%, far more than the ~0.1-0.2%% NHPI share), so "
                "unbucketed students are dropped from the race axis, not "
                "folded into Asian. No rollup rows are synthesized."
            ),
            (
                "The 2010 cohort has no pacific_islander rows: the 2012 "
                "file publishes 13 demographic groups (Pacific Islander "
                "was added with the 2013 publication). Rows are absent, "
                "not emitted with NULL metrics — there is no bronze source "
                "to NULL out. Pinned by quality checks in both directions."
            ),
            (
                "Male + female graduate and enrolled counts sum EXACTLY to "
                "the all-students total at the state level in every cohort "
                "year 2010-2022 (verified in bronze; pinned by a quality "
                "check). State rows are never suppressed."
            ),
            (
                "Metric NULL rates are high (~51-53%% of metric cells) but "
                "uniform across years — heavy suppression is bronze-real, "
                "not a transform defect."
            ),
            (
                "No rates are published in bronze; derive the enrollment "
                "rate as num_enrolled_in_college / num_graduates (NULL "
                "when either side is suppressed)."
            ),
        ],
        quality_checks=[
            {
                "name": "enrolled_never_exceeds_graduates",
                "description": (
                    "num_enrolled_in_college counts a subset of the row's "
                    "graduates, so it can never exceed num_graduates where "
                    "both are published (verified: zero violations across "
                    "all 13 bronze files)."
                ),
                "dimension": "accuracy",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "num_graduates IS NOT NULL AND "
                    "num_enrolled_in_college IS NOT NULL AND "
                    "num_enrolled_in_college > num_graduates"
                ),
                "mustBe": 0,
            },
            {
                "name": "suppressed_graduates_implies_suppressed_enrolled",
                "description": (
                    "GOSA suppresses per metric cell at n=10; a suppressed "
                    "num_graduates (< 10) forces the enrolled count below "
                    "10 too, so no row may publish num_enrolled_in_college "
                    "while num_graduates is NULL (verified: zero such rows "
                    "in any bronze file). The reverse is legal — enrolled "
                    "can be suppressed alone."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "num_graduates IS NULL AND "
                    "num_enrolled_in_college IS NOT NULL"
                ),
                "mustBe": 0,
            },
            {
                "name": "published_counts_meet_reporting_threshold",
                "description": (
                    "Every published value is >= 10 — the publisher's own "
                    "SQL (embedded in the 2014/2022 files) suppresses any "
                    "cell below 10 as TFS. A smaller value means a "
                    "suppression regression or a column-swap error."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "(num_graduates IS NOT NULL AND num_graduates < 10) "
                    "OR (num_enrolled_in_college IS NOT NULL AND "
                    "num_enrolled_in_college < 10)"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_rows_never_suppressed",
                "description": (
                    "GOSA publishes unsuppressed statewide aggregates for "
                    "every subgroup in every year (verified across all 13 "
                    "files): state-level rows (district_code and "
                    "school_code both NULL) must carry both metrics."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "district_code IS NULL AND school_code IS NULL AND "
                    "(num_graduates IS NULL OR "
                    "num_enrolled_in_college IS NULL)"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_gender_partition_sums_to_all",
                "description": (
                    "At the state level male + female sums exactly to the "
                    "'all' total for both metrics in every cohort year "
                    "(verified in bronze for all 13 years; state rows are "
                    "never suppressed, so the sums are NULL-safe)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year, "
                    "SUM(CASE WHEN demographic IN ('male', 'female') THEN "
                    "num_graduates ELSE 0 END) AS mf_grads, "
                    "MAX(CASE WHEN demographic = 'all' THEN num_graduates "
                    "END) AS all_grads, "
                    "SUM(CASE WHEN demographic IN ('male', 'female') THEN "
                    "num_enrolled_in_college ELSE 0 END) AS mf_enrolled, "
                    "MAX(CASE WHEN demographic = 'all' THEN "
                    "num_enrolled_in_college END) AS all_enrolled "
                    "FROM {object} WHERE district_code IS NULL AND "
                    "school_code IS NULL GROUP BY year) AS by_year "
                    "WHERE mf_grads <> all_grads "
                    "OR mf_enrolled <> all_enrolled"
                ),
                "mustBe": 0,
            },
            {
                "name": "state_race_partition_sums_to_all_2011_onward",
                "description": (
                    "From 2011 the seven mutually exclusive race buckets "
                    "(split Asian/PI convention, §5b) partition each "
                    "state-level total for both metrics within a residue "
                    "of at most 8 (exact in 2011-2018, 2020, 2022; off by "
                    "8 in 2019 and 1 in 2021 — a handful of graduates "
                    "without a reported race, preserved as published). "
                    "2010 is excluded: its six buckets undercount by "
                    "~1.1%% (no Pacific Islander group; race-reporting "
                    "transition year)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year, "
                    f"SUM(CASE WHEN demographic IN ({race_list}) THEN "
                    "num_graduates ELSE 0 END) AS race_grads, "
                    "MAX(CASE WHEN demographic = 'all' THEN num_graduates "
                    "END) AS all_grads, "
                    f"SUM(CASE WHEN demographic IN ({race_list}) THEN "
                    "num_enrolled_in_college ELSE 0 END) AS race_enrolled, "
                    "MAX(CASE WHEN demographic = 'all' THEN "
                    "num_enrolled_in_college END) AS all_enrolled "
                    "FROM {object} WHERE district_code IS NULL AND "
                    "school_code IS NULL AND year >= 2011 "
                    "GROUP BY year) AS by_year "
                    f"WHERE ABS(race_grads - all_grads) > "
                    f"{RACE_PARTITION_TOLERANCE} "
                    f"OR ABS(race_enrolled - all_enrolled) > "
                    f"{RACE_PARTITION_TOLERANCE}"
                ),
                "mustBe": 0,
            },
            {
                "name": "pacific_islander_absent_in_2010",
                "description": (
                    "Structural fact: the 2012 file (cohort 2010) publishes "
                    "13 demographic groups with no Pacific Islander; gold "
                    "must carry no pacific_islander rows for 2010 (rows are "
                    "absent, never fabricated with NULL metrics)."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "demographic = 'pacific_islander' AND year = 2010"
                ),
                "mustBe": 0,
            },
            {
                "name": "pacific_islander_present_2011_onward",
                "description": (
                    "Structural fact: every cohort year from 2011 publishes "
                    "the Pacific Islander group; a year without "
                    "pacific_islander rows means an unpivot or alias "
                    "regression."
                ),
                "dimension": "completeness",
                "query": (
                    "SELECT COUNT(*) FROM (SELECT year FROM {object} "
                    "WHERE year >= 2011 GROUP BY year HAVING "
                    "SUM(CASE WHEN demographic = 'pacific_islander' THEN 1 "
                    "ELSE 0 END) = 0) AS bad_years"
                ),
                "mustBe": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
