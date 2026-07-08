"""Transform bronze georgia_student_growth_model_end_of_grade files into gold facts.

Source: Georgia Insights / GaDOE — Georgia Student Growth Model (GSGM /
Student Growth Percentile) on End-of-Grade Milestones assessments. Bronze
ships 18 Excel workbooks: six reporting years (2015-2019, 2023; no files for
the COVID years 2020-2022) x three detail levels (State, System, School).
There are no demographic breakdowns anywhere in this bronze — every row is
"All Students" — so per data-cleaning-standards §5 the ``demographic`` column
is omitted from gold. Grade is the primary row axis (``grade_level``).

File shapes (era routing is STRUCTURAL — the header rows of the first sheet
are probed, never the filename year):

- ``flat_header_row1`` — 2015: row 0 title banner, row 1 a flat
  subject-prefixed header (``ELA: N Tested``, ``Math: Median SGP``, ...).
- ``flat_header_row2`` — 2016-2017: row 1 is a subject super-header but row 2
  repeats the subject prefix in every metric name, so reading row 2 alone
  yields the same flat subject-prefixed layout as 2015.
- ``two_row_pivot`` — 2018, 2019, 2023: row 1 carries the subject
  super-header (``English Language Arts`` / ``Mathematics`` / ... / ``RESA``)
  and row 2 the unprefixed metric names; read with pandas ``header=[1, 2]``.

Reads use pandas ``dtype=str`` with the topic suppression markers as
``na_values`` (``----`` 2015-2017, ``TFS`` 2017-2018, true null 2019, ``--``
2023); whole-sheet Excel reads cannot drop records at parse time, so
read-loss raw == parsed by construction and no read-loss events are
recorded. Every sheet in this bronze is pure data — an authoring-time scan
of all 79 sheets found zero footnote/legend/empty rows — so the only row
filter is the defensive unparseable-grade drop (ledgered if it ever fires).

Design decisions (each re-verified against bronze during authoring):

- **Wide → long unpivot.** Each (sheet row x subject block) becomes one gold
  row keyed (year, detail_level, district_code, school_code, grade_level,
  subject). 2015-2016 publish four subjects (ELA, Math, Science, Social
  Studies); 2017+ only ELA + Math.

- **Grade resolution.** Per-grade rows come from an in-file ``Grade`` /
  ``GRADE`` column when present (2015-2018 per-grade sheets; 2016-2019 +
  2023 state sheets) and from the sheet name otherwise (2019 + 2023
  system/school per-grade sheets, whose ``Grade`` column was dropped).
  The published AllGrades aggregate (2015-2019 only) is preserved as
  ``grade_level="all"`` because its ``sgp_median`` cannot be reconstructed
  from per-grade medians (median of medians != overall median). 2023
  publishes no AllGrades rows at any detail level.

- **Geographic identifier evolution.** 2015 system files mis-label the
  system-code column ``State`` (state files carry the literal ``Georgia``
  there instead — the rename is detail-level-contextual). 2015-2017 school
  files use a single 7-digit ``KEY`` = system_code*10000 + school_code,
  split into the two gold codes. 2018+ publish separate ``System Code`` /
  ``School Code`` columns (string-typed in 2019; the 2023 school codes are
  4-digit and NOT globally unique — the composite key handles that).

- **Charter campus promotion.** 2015-2017 school-level rows key the State /
  Commission Charter campuses under the bare SYSTEM codes 782/783 (via the
  KEY prefix); 2018+ files publish the 7-digit campus codes (782xxxx /
  783xxxx) directly. The shared ``_charter_district_promotion`` module
  rewrites the early school-level rows to the campus codes in ``main()``
  (ledgered per year as manifest ``reclassified`` events). No bare 782/783
  DISTRICT-level rows exist anywhere in this bronze — even the 2015-2017
  system files already publish the 7-digit campus codes as district rows
  (verified per file) — so the promotion only ever fires on school rows.
  The single ``799`` ("State Schools") district row in 2015-2017 system
  files is a genuine umbrella aggregate (one row per sheet, named "State
  Schools") — unlike the Milestones bronze there is no shared-code
  ambiguity, so no 799 remap is needed; ``799`` is a valid districts-
  dimension FK.

- **Percent scale.** All ``%`` columns ship 0-100 in every era (integers
  2015-2018, decimals 2019+) and are divided by 100 to the canonical 0-1
  scale. ``sgp_median`` keeps its natural 1-99 percentile scale (Float64 —
  even cohorts yield ``.5`` medians).

- **Era 6 (2023) metric break.** ``Number Tested``, ``% Received SGP`` and
  the achievement percentages are gone; a three-bucket SGP split
  (``% Low/Typical/High Growth``) replaces the single
  ``% Typical or High Growth``. The era-specific metrics live in separate
  gold columns (NULL where unreported) — they are NOT comparable
  (``pct_sgp_typical_growth`` excludes high growth;
  ``pct_sgp_typical_or_high_growth`` includes it).

- **§4b mask — empty-cohort sentinel medians.** 2016 (school + system) and
  2018 (school) publish whole-row ``0`` blocks for subject cohorts with no
  test takers: ``N Tested = 0``, ``N Received SGP = 0``, ``Median SGP = 0``
  and every percentage 0. A median is undefined on an empty cohort and 0 is
  outside the valid 1-99 SGP domain, so ``sgp_median`` is NULLed on rows
  where ``num_sgp_received == 0 AND sgp_median == 0``
  (``_null_empty_cohort_sgp_median``, recorded via ``record_masked``). The
  companion zero counts and zero percentages on those rows are *possible*
  values (0 of 0 students) and are preserved per the §4b
  extreme-but-conceivable default.

- **Dedup tie-break.** Each (year, detail_level) is fed by exactly one
  bronze file and natural keys are unique within files, so dedup is purely
  defensive; ``sort_col="num_tested"`` prefers a row with a reported count
  over a placeholder. ``assert_no_natural_key_collisions`` runs first so
  any promotion-induced duplicate key with DIVERGENT metrics fails loudly
  instead of being silently resolved.

Natural key (post-transform):
    (year, detail_level, district_code, school_code, grade_level, subject)
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import polars as pl

from src.etl.education.georgiainsights._charter_district_promotion import (
    promote_charter_system_to_campus_district,
)
from src.utils.grades import normalize_grade_column
from src.utils.metadata import write_data_dictionary
from src.utils.readers import SUPPRESSION_VALUES, list_bronze_files
from src.utils.subjects import apply_subject_normalization
from src.utils.transformers import (
    TransformManifest,
    assert_no_natural_key_collisions,
    deduplicate_by_detail_level,
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

TOPIC = "georgia_student_growth_model_end_of_grade"
BRONZE_DIR = Path(
    "data/bronze/education/georgiainsights/georgia_student_growth_model_end_of_grade"
)
GOLD_DIR = Path("data/gold/education/georgia_student_growth_model_end_of_grade")

# Topic suppression markers on top of the shared set (`TFS` etc.):
# `----` (2015-2017) and `--` (2023). 2019 uses true null (no marker).
_TOPIC_SUPPRESSION_VALUES: set[str] = SUPPRESSION_VALUES | {"----", "--"}

# =============================================================================
# Normalization maps
# =============================================================================

SUBJECT_ELA = "english_language_arts"
SUBJECT_MATH = "mathematics"
SUBJECT_SCIENCE = "science"
SUBJECT_SOCIAL_STUDIES = "social_studies"

# Flat-era subject prefix token (text before `: ` in `ELA: N Tested`,
# uppercased) -> gold subject. Unknown prefixes leave the column intact,
# which then fails loudly in _rename_and_drop.
_PREFIX_SUBJECT_MAP: dict[str, str] = {
    "ELA": SUBJECT_ELA,
    "MATH": SUBJECT_MATH,
    "SCIENCE": SUBJECT_SCIENCE,
    "SOCIAL STUDIES": SUBJECT_SOCIAL_STUDIES,
}

# Two-row-pivot subject super-header (canonicalized) -> gold subject.
# `RESA` and the Unnamed ID supers are handled separately; anything else
# raises (a new super-header means new bronze structure to review).
_SUPERHEADER_SUBJECT_MAP: dict[str, str] = {
    "ENGLISH LANGUAGE ARTS": SUBJECT_ELA,
    "MATHEMATICS": SUBJECT_MATH,
    "SCIENCE": SUBJECT_SCIENCE,
    "SOCIAL STUDIES": SUBJECT_SOCIAL_STUDIES,
}

# Canonicalized bronze header (uppercase, newline/whitespace collapsed) ->
# gold column or routing marker. Any header whose canonical form is missing
# here raises in _rename_and_drop — that is how silently-NULLed metrics from
# new/renamed bronze headers are caught. Full 18-file header inventory was
# re-verified during authoring.
_BRONZE_HEADER_MAP: dict[str, str] = {
    # Identifier columns.
    "SYSTEM CODE": "district_code",  # 2018+; string-typed in 2019
    "SYSTEM ID": "district_code",  # 2016-2017 system files
    "SCHOOL CODE": "school_code",  # 2018+ school files (4-digit, composite)
    # 2015 only: the system/school files mis-label the system-code column
    # `State` (values 601, 602, ...); the state files carry the literal
    # "Georgia" under the same header. Resolved by detail level.
    "STATE": "_state_or_district",
    # 2015-2017 school files: 7-digit KEY = system*10000 + school.
    "KEY": "_compound_key",
    "GRADE": "_grade_raw",
    # Dimension attributes — never in fact tables.
    "SYSTEM NAME": "_drop",
    "SCHOOL NAME": "_drop",
    "RESANAME_RPT": "_drop",  # 2023 system/school RESA grouping
    # Metric columns (unprefixed canonical forms; the flat eras' short
    # `N Tested` and the 2018+ long `Number Tested` map to one gold name).
    "N TESTED": "num_tested",
    "NUMBER TESTED": "num_tested",
    "N RECEIVED SGP": "num_sgp_received",
    "NUMBER RECEIVED SGP": "num_sgp_received",
    "% RECEIVED SGP": "sgp_received_rate",
    "MEDIAN SGP": "sgp_median",
    "% PROFICIENT LEARNER AND ABOVE": "pct_proficient_learner_or_above",
    "% DEVELOPING LEARNER AND ABOVE": "pct_developing_learner_or_above",
    "% TYPICAL OR HIGH GROWTH": "pct_sgp_typical_or_high_growth",
    # Era 6 (2023) three-bucket SGP split.
    "% LOW GROWTH": "pct_sgp_low_growth",
    "% TYPICAL GROWTH": "pct_sgp_typical_growth",
    "% HIGH GROWTH": "pct_sgp_high_growth",
}

# In-file Grade / GRADE column value (stripped, uppercased, trailing `.0`
# removed) -> canonical gold grade_level. Only grades 4-8 exist (an SGP
# requires a prior-year score; grade 3 is the first tested EOG grade).
_GRADE_VALUE_MAP: dict[str, str] = {
    "ALL": "all",
    "4": "04",
    "5": "05",
    "6": "06",
    "7": "07",
    "8": "08",
}

VALID_GRADE_LEVELS: set[str] = {"all", "04", "05", "06", "07", "08"}

# =============================================================================
# Gold schema
# =============================================================================

METRIC_COLUMNS: list[str] = [
    "num_tested",
    "num_sgp_received",
    "sgp_received_rate",
    "sgp_median",
    "pct_proficient_learner_or_above",
    "pct_developing_learner_or_above",
    "pct_sgp_typical_or_high_growth",
    "pct_sgp_low_growth",
    "pct_sgp_typical_growth",
    "pct_sgp_high_growth",
]

STANDARD_COLUMNS: list[str] = [
    "year",
    "district_code",
    "school_code",
    "detail_level",
    "grade_level",
    "subject",
    *METRIC_COLUMNS,
]

# sgp_median is a percentile rank kept on its natural 1-99 scale; Float64
# because even SGP populations yield half-integer medians (.5).
TARGET_TYPES: dict[str, pl.DataType] = {
    "year": pl.Int32,
    "district_code": pl.Utf8,
    "school_code": pl.Utf8,
    "detail_level": pl.Utf8,
    "grade_level": pl.Utf8,
    "subject": pl.Utf8,
    "num_tested": pl.Int64,
    "num_sgp_received": pl.Int64,
    "sgp_received_rate": pl.Float64,
    "sgp_median": pl.Float64,
    "pct_proficient_learner_or_above": pl.Float64,
    "pct_developing_learner_or_above": pl.Float64,
    "pct_sgp_typical_or_high_growth": pl.Float64,
    "pct_sgp_low_growth": pl.Float64,
    "pct_sgp_typical_growth": pl.Float64,
    "pct_sgp_high_growth": pl.Float64,
}

# Percent columns divided by 100 to the canonical 0-1 scale. Counts and the
# sgp_median percentile keep their natural scales. sgp_received_rate is a
# 0-1 rate too (bronze ships 0-100) but lacks the pct_ prefix, so it is
# added explicitly.
_PCT_COLUMNS: set[str] = {c for c in METRIC_COLUMNS if c.startswith("pct_")} | {
    "sgp_received_rate"
}

# Guard keys: detail_level participates because district codes repeat across
# detail levels (a district aggregate and its schools share district_code).
NATURAL_KEYS: list[str] = [
    "year",
    "detail_level",
    "district_code",
    "school_code",
    "grade_level",
    "subject",
]


@dataclass
class CategoricalLedgers:
    """Raw-label → gold-value ledgers accumulated across files for the manifest."""

    subject: dict[str, str] = field(default_factory=dict)
    grade_level: dict[str, str] = field(default_factory=dict)


# =============================================================================
# Filename / sheet / header parsing
# =============================================================================


def _parse_filename(filename: str) -> tuple[int, str]:
    """Extract (year, detail_level) from a bronze filename.

    Two conventions: `GSGM_EOG_YYYY_{State|System|School}[_Level].xls[x]`
    (2015-2019) and `SGP_EOG_Aggs_{State|System|School}_Level_YYYY.xlsx`
    (2023). The filename year is the data year ("Spring YYYY" = school year
    ending in YYYY); the 2016 state file's sheet tab still says 2015, so the
    sheet name is never trusted for year inference.
    """
    year_match = re.search(r"20\d{2}", filename)
    if not year_match:
        raise ValueError(f"Cannot parse year from filename: {filename!r}")
    year = int(year_match.group())

    lower = filename.lower()
    if "school" in lower:
        detail = "school"
    elif "system" in lower:
        detail = "district"  # bronze "System" = gold "district"
    elif "state" in lower:
        detail = "state"
    else:
        raise ValueError(f"Cannot parse detail level from filename: {filename!r}")
    return year, detail


def _canonical_colname(name: object) -> str:
    """Collapse header inconsistencies for map lookups.

    Bronze headers embed newlines (`Number\\nTested`, `%\\n Received SGP`),
    double spaces (`Science:  % Received SGP`), and per-era case differences
    (`and above` vs `and Above`). Returns an uppercase whitespace-collapsed
    form so every variant resolves to one map key.
    """
    s = str(name).replace("\n", " ").replace("\r", " ")
    return " ".join(s.split()).strip().upper()


# Subject-prefixed flat-era metric header, e.g. `ELA: N TESTED` (canonical
# form). The prefix token must be a known subject; `(.+)` is the metric.
_PREFIX_RE = re.compile(r"^([A-Za-z ]+):\s*(.+)$")


def _split_subject_prefix(canonical: str) -> tuple[str | None, str]:
    """Split a canonicalized flat-era header into (subject, metric part).

    Returns (None, header) when the header carries no known subject prefix
    (identifier columns like `KEY`, `SYSTEM NAME`, `GRADE`).
    """
    match = _PREFIX_RE.match(canonical)
    if not match:
        return None, canonical
    subject = _PREFIX_SUBJECT_MAP.get(match.group(1).strip())
    if subject is None:
        return None, canonical
    return subject, match.group(2).strip()


def _parse_grade_from_sheet_name(sheet_name: str) -> str | None:
    """Grade from a sheet name: `EOG_Grade4_2019_System` / `Grade7_School_2023`.

    AllGrades sheets return the canonical `"all"` aggregate label. Returns
    None when the sheet name has no recognizable grade token.
    """
    if "allgrades" in sheet_name.lower():
        return "all"
    match = re.search(r"Grade\s*(\d)", sheet_name)
    if match and 4 <= int(match.group(1)) <= 8:
        return f"{int(match.group(1)):02d}"
    return None


def _excel_engine(path: Path) -> str:
    return "xlrd" if path.suffix.lower() == ".xls" else "openpyxl"


def _detect_file_shape(path: Path) -> str:
    """STRUCTURAL shape detection: probe the first sheet's header rows.

    - subject-prefixed names (`ELA: ...`) on row 1 → flat_header_row1 (2015)
    - subject-prefixed names on row 2 → flat_header_row2 (2016-2017; row 1
      is a super-header but row 2 alone is already a complete flat header)
    - otherwise row 1 must carry a known subject super-header →
      two_row_pivot (2018+). Anything else raises (new bronze structure).
    """
    probe = pd.read_excel(
        path, sheet_name=0, header=None, nrows=3, dtype=str, engine=_excel_engine(path)
    )

    def _cells(i: int) -> list[str]:
        if i >= len(probe):
            return []
        return [str(v) for v in probe.iloc[i].tolist() if not pd.isna(v)]

    def _has_prefixed(cells: list[str]) -> bool:
        return any(
            _split_subject_prefix(_canonical_colname(c))[0] is not None for c in cells
        )

    if _has_prefixed(_cells(1)):
        return "flat_header_row1"
    if _has_prefixed(_cells(2)):
        return "flat_header_row2"
    supers = {_canonical_colname(c) for c in _cells(1)}
    if supers & set(_SUPERHEADER_SUBJECT_MAP):
        return "two_row_pivot"
    raise ValueError(
        f"{path.name}: unrecognized sheet structure (header rows: "
        f"{_cells(1)!r} / {_cells(2)!r})"
    )


# =============================================================================
# Column rename / ID formatting / metric casting
# =============================================================================


def _rename_and_drop(df: pl.DataFrame, source: str, detail_level: str) -> pl.DataFrame:
    """Rename canonicalized bronze columns to gold names; drop dim attributes.

    Raises on any unknown column — an unmapped header would otherwise become
    a silently NULL gold metric. The 2015 `STATE` header is contextual: it
    holds the system code in system/school files (→ district_code) and the
    literal "Georgia" in state files (→ dropped).
    """
    passthrough = {"subject"}
    unknown = [
        c for c in df.columns if c not in _BRONZE_HEADER_MAP and c not in passthrough
    ]
    if unknown:
        raise ValueError(
            f"{source}: unknown bronze columns (add to _BRONZE_HEADER_MAP): {unknown}"
        )

    rename: dict[str, str] = {}
    drop: list[str] = []
    for col in df.columns:
        if col in passthrough:
            continue
        dest = _BRONZE_HEADER_MAP[col]
        if dest == "_state_or_district":
            if detail_level == "state":
                drop.append(col)
            else:
                rename[col] = "district_code"
        elif dest == "_drop":
            drop.append(col)
        else:
            rename[col] = dest
    return df.rename(rename).drop(drop)


def _split_compound_key(df: pl.DataFrame) -> pl.DataFrame:
    """Split the 2015-2017 school `KEY` (7 digits: DDDSSSS) into both codes."""
    if "_compound_key" not in df.columns:
        return df
    key = (
        pl.col("_compound_key")
        .cast(pl.Utf8, strict=False)
        .str.replace(r"\.0$", "")
        .str.zfill(7)
    )
    return df.with_columns(
        key.str.slice(0, 3).alias("district_code"),
        key.str.slice(3, 4).alias("school_code"),
    ).drop("_compound_key")


def _format_ids(df: pl.DataFrame) -> pl.DataFrame:
    """Zero-pad district (3) / school (4) codes; zfill never truncates.

    The `.0` strip handles pandas float-stringified ints (a column with
    NULLs is inferred float64, so `dtype=str` yields `"601.0"`).
    """
    exprs = []
    for col, width in (("district_code", 3), ("school_code", 4)):
        if col in df.columns:
            exprs.append(
                pl.col(col)
                .cast(pl.Utf8, strict=False)
                .str.replace(r"\.0$", "")
                .str.zfill(width)
                .alias(col)
            )
    return df.with_columns(exprs) if exprs else df


def _cast_and_scale_metrics(df: pl.DataFrame) -> pl.DataFrame:
    """Cast metric columns to target dtypes; divide percents by 100.

    `strict=False` lands any residual suppression string as NULL. Counts and
    `sgp_median` keep their natural scales. Bronze ships percents on 0-100
    in every era (integer-valued 2015-2018, decimal 2019+) — re-verified per
    era during authoring — so a single /100 applies across eras.
    """
    exprs = []
    for col in METRIC_COLUMNS:
        if col not in df.columns:
            continue
        if col in _PCT_COLUMNS:
            exprs.append(
                (pl.col(col).cast(pl.Float64, strict=False) / 100.0).alias(col)
            )
        else:
            exprs.append(pl.col(col).cast(TARGET_TYPES[col], strict=False).alias(col))
    return df.with_columns(exprs) if exprs else df


# =============================================================================
# Sheet readers
# =============================================================================


def _concat_subject_frames(frames: list[pl.DataFrame], source: str) -> pl.DataFrame:
    """Concat per-subject frames; all blocks in a sheet must be uniform."""
    col_sets = {tuple(sorted(f.columns)) for f in frames}
    if len(col_sets) != 1:
        raise ValueError(f"{source}: subject blocks have divergent columns: {col_sets}")
    ordered = sorted(frames[0].columns)
    return pl.concat([f.select(ordered) for f in frames], how="vertical")


def _read_flat_sheet(
    path: Path,
    sheet_name: str,
    header_row: int,
    detail_level: str,
    ledgers: CategoricalLedgers,
) -> pl.DataFrame | None:
    """Read one flat-era sheet (subject-prefixed columns) into long format."""
    pdf = pd.read_excel(
        path,
        sheet_name=sheet_name,
        header=header_row,
        dtype=str,
        na_values=sorted(_TOPIC_SUPPRESSION_VALUES),
        engine=_excel_engine(path),
    )
    df = pl.from_pandas(pdf)
    if df.height == 0:
        return None
    # Defensive: drop fully-empty rows (none observed in any sheet).
    df = df.filter(~pl.all_horizontal(pl.all().is_null()))

    df = df.rename({c: _canonical_colname(c) for c in df.columns})

    # Partition columns into identifiers vs per-subject metric blocks.
    id_cols: list[str] = []
    blocks: dict[str, list[tuple[str, str]]] = {}  # subject -> [(col, metric)]
    for col in df.columns:
        subject, metric = _split_subject_prefix(col)
        if subject is None:
            id_cols.append(col)
        else:
            blocks.setdefault(subject, []).append((col, metric))
    if not blocks:
        raise ValueError(
            f"{path.name}:{sheet_name}: no subject-prefixed metric columns found"
        )

    frames: list[pl.DataFrame] = []
    for subject, cols in blocks.items():  # insertion order = column order
        raw_prefix = _canonical_colname(cols[0][0].split(":", 1)[0])
        ledgers.subject[raw_prefix] = subject
        sub = df.select(id_cols + [c for c, _ in cols]).rename(
            {c: _canonical_colname(m) for c, m in cols}
        )
        frames.append(sub.with_columns(pl.lit(subject).alias("subject")))
    out = _concat_subject_frames(frames, f"{path.name}:{sheet_name}")
    return _rename_and_drop(out, f"{path.name}:{sheet_name}", detail_level)


def _read_two_row_pivot_sheet(
    path: Path,
    sheet_name: str,
    detail_level: str,
    ledgers: CategoricalLedgers,
) -> pl.DataFrame | None:
    """Read one two-row-pivot sheet (subject super-header) into long format.

    Pandas `header=[1, 2]` yields MultiIndex columns; identifier columns sit
    under `Unnamed: N_level_0` supers, metric columns under a subject super,
    and the 2023 `RESAName_RPT` under a `RESA` super (dropped — dimension
    attribute). Unknown supers raise.
    """
    pdf = pd.read_excel(
        path,
        sheet_name=sheet_name,
        header=[1, 2],
        dtype=str,
        na_values=sorted(_TOPIC_SUPPRESSION_VALUES),
        engine=_excel_engine(path),
    )
    if pdf.empty:
        return None

    pairs: list[tuple[str, str]] = []
    for super_, metric in pdf.columns:
        super_str = str(super_)
        if super_str.startswith("Unnamed:"):
            super_canon = "__id__"
        else:
            super_canon = _canonical_colname(super_str)
        pairs.append((super_canon, _canonical_colname(metric)))
    flat_names = [f"c{i}" for i in range(len(pairs))]
    pdf.columns = flat_names

    df = pl.from_pandas(pdf)
    df = df.filter(~pl.all_horizontal(pl.all().is_null()))

    id_sel: dict[str, str] = {}  # flat name -> canonical destination header
    blocks: dict[str, list[tuple[str, str]]] = {}  # subject -> [(flat, metric)]
    for flat, (super_canon, metric) in zip(flat_names, pairs):
        if super_canon == "__id__":
            id_sel[flat] = metric
        elif super_canon == "RESA":
            # RESA grouping column — force the canonical name so
            # _rename_and_drop drops it as a dimension attribute.
            id_sel[flat] = "RESANAME_RPT"
        elif super_canon in _SUPERHEADER_SUBJECT_MAP:
            subject = _SUPERHEADER_SUBJECT_MAP[super_canon]
            ledgers.subject[super_canon] = subject
            blocks.setdefault(subject, []).append((flat, metric))
        else:
            raise ValueError(
                f"{path.name}:{sheet_name}: unknown subject super-header "
                f"{super_canon!r} (add to _SUPERHEADER_SUBJECT_MAP)"
            )
    if not blocks:
        raise ValueError(f"{path.name}:{sheet_name}: no subject metric blocks found")

    frames: list[pl.DataFrame] = []
    for subject, cols in blocks.items():  # insertion order = column order
        sub = df.select(list(id_sel) + [c for c, _ in cols]).rename(
            {**id_sel, **{c: m for c, m in cols}}
        )
        frames.append(sub.with_columns(pl.lit(subject).alias("subject")))
    out = _concat_subject_frames(frames, f"{path.name}:{sheet_name}")
    return _rename_and_drop(out, f"{path.name}:{sheet_name}", detail_level)


def _finalize_sheet_frame(
    df: pl.DataFrame,
    source: str,
    year: int,
    detail_level: str,
    sheet_grade: str | None,
    ledgers: CategoricalLedgers,
) -> pl.DataFrame:
    """Shared tail: split key, format IDs, cast metrics, resolve grade."""
    df = _split_compound_key(df)
    df = _format_ids(df)
    df = _cast_and_scale_metrics(df)

    if "_grade_raw" in df.columns:
        # In-file grade column wins over the sheet-name token (the 2016
        # state sheet tab is mis-labeled 2015; only the column is trusted).
        normalized_raw = (
            pl.col("_grade_raw")
            .cast(pl.Utf8)
            .str.strip_chars()
            .str.to_uppercase()
            .str.replace(r"\.0$", "")
        )
        for raw in (
            df.select(normalized_raw.alias("g"))["g"].drop_nulls().unique().to_list()
        ):
            gold = _GRADE_VALUE_MAP.get(raw)
            if gold is None:
                logger.warning(f"{source}: unparseable grade value {raw!r}")
            else:
                ledgers.grade_level[raw] = gold
        df = df.with_columns(
            normalized_raw.replace_strict(_GRADE_VALUE_MAP, default=None).alias(
                "grade_level"
            )
        ).drop("_grade_raw")
    else:
        if sheet_grade is None:
            raise ValueError(f"{source}: no grade column and no sheet-name grade token")
        token = "ALLGRADES" if sheet_grade == "all" else f"GRADE{int(sheet_grade)}"
        ledgers.grade_level[token] = sheet_grade
        df = df.with_columns(pl.lit(sheet_grade).cast(pl.Utf8).alias("grade_level"))

    return df.with_columns(
        pl.lit(year).cast(pl.Int32).alias("year"),
        pl.lit(detail_level).cast(pl.Utf8).alias("detail_level"),
    )


def transform_file(
    path: Path, manifest: TransformManifest, ledgers: CategoricalLedgers
) -> pl.DataFrame | None:
    """Transform one bronze workbook into a long frame; record manifest entries.

    Whole-sheet Excel reads cannot drop records at parse time (read-loss
    raw == parsed by construction), so no read-loss events are recorded.
    """
    year, detail_level = _parse_filename(path.name)
    shape = _detect_file_shape(path)
    logger.info(f"{path.name}: year={year} detail={detail_level} shape={shape}")

    frames: list[pl.DataFrame] = []
    for sheet_name in pd.ExcelFile(path, engine=_excel_engine(path)).sheet_names:
        source = f"{path.name}:{sheet_name}"
        if shape == "two_row_pivot":
            df = _read_two_row_pivot_sheet(path, sheet_name, detail_level, ledgers)
        else:
            header_row = 1 if shape == "flat_header_row1" else 2
            df = _read_flat_sheet(path, sheet_name, header_row, detail_level, ledgers)
        if df is None or df.height == 0:
            logger.warning(f"{source}: no data rows")
            continue
        frames.append(
            _finalize_sheet_frame(
                df,
                source,
                year,
                detail_level,
                _parse_grade_from_sheet_name(sheet_name),
                ledgers,
            )
        )
    if not frames:
        raise ValueError(f"{path.name}: no data rows read from any sheet")

    frames = harmonize_columns(frames, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(frames, how="vertical")

    manifest.record_file(path, year, shape, combined.height, combined.columns)
    manifest.record_bronze(year, combined.height)
    return combined


# =============================================================================
# §4b mask
# =============================================================================


def _null_empty_cohort_sgp_median(
    df: pl.DataFrame, manifest: TransformManifest
) -> pl.DataFrame:
    """NULL the bronze sentinel `sgp_median = 0` on empty-cohort rows (§4b).

    2016 (school + system) and 2018 (school) publish all-zero metric blocks
    for cohorts with no test takers. A median is undefined with no students
    and 0 is outside the valid 1-99 SGP domain, so it would misread as
    "lowest possible growth" rather than "no data". Only `sgp_median` is
    NULLed; the row and its (possible) zero counts survive. The contract's
    [1, 99] range guard stays enforceable because of this mask.
    """
    empty_cohort = (pl.col("num_sgp_received") == 0) & (pl.col("sgp_median") == 0)
    masked = df.filter(empty_cohort)
    if masked.height == 0:
        return df
    years = sorted(masked["year"].unique().to_list())
    manifest.record_masked(
        column="sgp_median",
        count=masked.height,
        reason=(
            "bronze sentinel 0 on empty-cohort rows (num_sgp_received == 0); "
            "median undefined and 0 is outside the 1-99 SGP domain"
        ),
        years=years,
    )
    return df.with_columns(
        pl.when(empty_cohort)
        .then(None)
        .otherwise(pl.col("sgp_median"))
        .alias("sgp_median")
    )


# =============================================================================
# Pipeline orchestration
# =============================================================================


def main() -> None:
    """Run the full bronze-to-gold pipeline for GSGM EOG."""
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)
    ledgers = CategoricalLedgers()
    frames: list[pl.DataFrame] = []

    for path in list_bronze_files(BRONZE_DIR, extensions=[".xls", ".xlsx"]):
        df = transform_file(path, manifest, ledgers)
        if df is not None and df.height > 0:
            frames.append(df)
    if not frames:
        raise RuntimeError("No bronze data transformed — check bronze directory")

    # Eras carry different metric subsets (no SGP buckets before 2023; no
    # num_tested / achievement metrics in 2023); harmonize fills typed NULLs.
    frames = harmonize_columns(frames, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(frames, how="vertical")
    logger.info(f"Combined all frames: {combined.height:,} rows")

    # §10a backstops: local parsing already emits canonical values; the
    # shared normalizers keep the vocabulary aligned with the registries.
    combined = combined.with_columns(
        normalize_grade_column("grade_level").alias("grade_level"),
        apply_subject_normalization("subject").alias("subject"),
    )

    # Defensive grade filter: keep per-grade rows AND the published
    # AllGrades aggregate ("all" — its sgp_median cannot be reconstructed
    # from per-grade medians). No sheet in this bronze produces unparseable
    # grades (authoring-time scan), so this should drop 0 rows; ledgered if
    # it ever fires.
    bad = combined.filter(
        ~pl.col("grade_level").is_in(sorted(VALID_GRADE_LEVELS))
        | pl.col("grade_level").is_null()
    )
    if bad.height:
        for yr, n in bad.group_by("year").agg(pl.len().alias("n")).sort("year").rows():
            manifest.record_filtered(int(yr), int(n), "unparseable_grade_row")
        logger.warning(f"Dropped {bad.height} unparseable-grade rows")
        combined = combined.filter(
            pl.col("grade_level").is_in(sorted(VALID_GRADE_LEVELS))
        )

    # Categorical ledgers (100%-coverage review artifacts).
    manifest.record_categorical(
        column="grade_level",
        map_dict=dict(sorted(ledgers.grade_level.items())),
        bronze_series=pl.Series("grade_raw", sorted(ledgers.grade_level)),
        gold_series=combined["grade_level"],
    )
    manifest.record_categorical(
        column="subject",
        map_dict=dict(sorted(ledgers.subject.items())),
        bronze_series=pl.Series("subject_raw", sorted(ledgers.subject)),
        gold_series=combined["subject"],
    )

    # Charter SYSTEM → CAMPUS district codes on school-level rows
    # (2015-2017 school files key charter campuses under the bare 782/783
    # system codes via the KEY prefix; 2018+ publish 7-digit campus codes).
    # Ledgered as manifest reclassified events by the shared module. Runs
    # BEFORE the collision guard + dedup so any rewrite-induced duplicate
    # is surfaced by the standard machinery.
    combined = promote_charter_system_to_campus_district(combined, manifest=manifest)

    # Guard BEFORE dedup: duplicate keys with DIVERGENT metrics mean an
    # alias/promotion bug and must fail loudly, never be silently resolved.
    assert_no_natural_key_collisions(combined, NATURAL_KEYS, METRIC_COLUMNS)

    # Defensive dedup: each (year, detail_level) comes from exactly one
    # bronze file and keys are unique within files (the guard above would
    # have raised otherwise). sort_col="num_tested" prefers a row with a
    # reported count over a placeholder if a true duplicate ever appears.
    combined = deduplicate_by_detail_level(
        combined,
        school_keys=["year", "district_code", "school_code", "grade_level", "subject"],
        district_keys=["year", "district_code", "grade_level", "subject"],
        state_keys=["year", "grade_level", "subject"],
        sort_col="num_tested",
    )

    # Shared geography-nulling rules (validator reads the same config).
    combined = null_aggregate_geography(
        combined,
        detail_level_col="detail_level",
        geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
    )

    # §4b mask — after harmonize/dedup/geography-nulling, before manifest
    # stats and export.
    combined = _null_empty_cohort_sgp_median(combined, manifest)

    validate_output(combined, required_non_null=["year", "detail_level", "grade_level"])

    # Manifest stats on the FINAL frame, then export.
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(combined, GOLD_DIR, STANDARD_COLUMNS)
    manifest.write(GOLD_DIR)

    # Known legitimate NULL spikes (warnings only): the 2023 metric break
    # NULLs num_tested / sgp_received_rate / achievement / typical-or-high
    # for 2023 and the three SGP buckets for 2015-2019.
    spike = check_null_rate_spikes(combined, METRIC_COLUMNS)
    if spike.status == "warning":
        for detail in spike.details or []:
            logger.warning(f"NULL rate spike: {detail}")

    write_data_dictionary(
        output_dir=GOLD_DIR,
        name=TOPIC,
        description=(
            "Georgia Student Growth Model (GSGM / SGP) on End-of-Grade "
            "(EOG) Milestones assessments. Each row is a (year x detail_level "
            "x geography x subject x grade) cohort's growth-related measures: "
            "Median Student Growth Percentile (1-99 ordinal), share of "
            "students at or above Typical growth (SGP >= 35), and (in 2023 "
            "only) a three-bucket SGP split (Low < 35, Typical 35-65, "
            "High > 65). 2015-2019 also report achievement-level percentages "
            "(Proficient / Developing Learner and above) on the underlying "
            "EOG assessment. Data covers reporting years 2015, 2016, 2017, "
            "2018, 2019, and 2023. No GSGM was reported during COVID years "
            "2020-2022. 2015-2016 report four subjects (ELA, Math, Science, "
            "Social Studies); 2017-2019 report only ELA + Math; 2023 reports "
            "only ELA + Math."
        ),
        title="Student Growth Model (SGM) End-of-Grade Results",
        summary=(
            "Student growth percentiles on Georgia Milestones grades 4-8 "
            "tests by school, district, grade, and subject, 2015-2023."
        ),
        columns=[
            {
                "name": "year",
                "type": "int32",
                "description": (
                    "Ending calendar year of the school year (spring year). "
                    "E.g., 2017 = school year 2016-2017. Data published "
                    "years are 2015, 2016, 2017, 2018, 2019, 2023."
                ),
                "nullable": False,
                "example": 2017,
            },
            {
                "name": "district_code",
                "type": "string",
                "description": (
                    "3-digit GOSA district/system code (FK to districts "
                    "dimension). 7-digit charter / state-school codes are "
                    "preserved in full; 2015-2017 school-level rows published "
                    "under the bare charter SYSTEM codes 782/783 are promoted "
                    "to the 7-digit campus code (system + school code) used "
                    "by 2018+ files. NULL for state-level rows."
                ),
                "nullable": True,
                "example": "601",
            },
            {
                "name": "school_code",
                "type": "string",
                "description": (
                    "4-digit GOSA school code (FK to schools dimension, "
                    "composite with district_code). NULL for district- and "
                    "state-level rows."
                ),
                "nullable": True,
                "example": "0177",
            },
            {
                "name": "grade_level",
                "type": "string",
                "description": (
                    "Grade level as a zero-padded 2-char string categorical, "
                    "matching the rest of the per-grade education topics. "
                    'Per-grade rows carry `"04"`-`"08"` (EOG SGP is only '
                    "reported for grades 4-8 because an SGP requires a "
                    "prior-year score, and grade 3 is the first tested "
                    "grade). The published AllGrades aggregate (2015-2019 "
                    'only) is preserved as `"all"` because its '
                    "`sgp_median` cannot be reconstructed from the per-grade "
                    'medians — analogous to the `"all"` value used in the '
                    "`demographic` column for cross-demographic aggregates. "
                    "2023 has no AllGrades row in bronze."
                ),
                "short_description": (
                    "Grade tested, 04 through 08 (grade 3 has no prior score "
                    "for growth); 'all' is the across-grades aggregate."
                ),
                "nullable": False,
                "example": "04",
                "validValues": ["all", "04", "05", "06", "07", "08"],
            },
            {
                "name": "subject",
                "type": "string",
                "description": (
                    "Snake-case subject label. 2015-2016 report four "
                    "subjects (english_language_arts, mathematics, science, "
                    "social_studies); 2017+ reports only english_language_arts "
                    "and mathematics."
                ),
                "short_description": (
                    "The content area tested (english_language_arts, "
                    "mathematics, science, social_studies)."
                ),
                "nullable": False,
                "example": "english_language_arts",
                "validValues": [
                    "english_language_arts",
                    "mathematics",
                    "science",
                    "social_studies",
                ],
            },
            {
                "name": "num_tested",
                "unit": "count",
                "type": "int64",
                "description": (
                    "Number of students who took the EOG assessment. NULL in "
                    "2023 (Era 6 does not report this column — see "
                    "bronze-data-structure.md §Era 6)."
                ),
                "nullable": True,
                "example": 180,
            },
            {
                "name": "num_sgp_received",
                "unit": "count",
                "metric_component": "denominator",
                "type": "int64",
                "description": (
                    "Number of students with enough prior-year scores to "
                    "receive a Student Growth Percentile (subset of num_tested "
                    "in 2015-2019; the only count metric reported in 2023)."
                ),
                "nullable": True,
                "example": 176,
            },
            {
                "name": "sgp_received_rate",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share of tested students who received an SGP "
                    "(num_sgp_received / num_tested). 0-1 decimal scale. NULL "
                    "in 2023 (not reported)."
                ),
                "nullable": True,
                "example": 0.98,
            },
            {
                "name": "sgp_median",
                "unit": "percentile",
                "key_metric": True,
                "type": "float64",
                "value_min": 1,
                "value_max": 99,
                "description": (
                    "Median Student Growth Percentile on the 1-99 ordinal "
                    "scale (the true SGP domain — there is no 0 or 100 SGP, "
                    "so the range guard is tightened from the percentile "
                    "default [0, 100] to [1, 99]). "
                    "NOT converted to 0-1 — it's a percentile rank, "
                    "preserved verbatim per data-cleaning-standards §4. "
                    "Statewide median is 50 by construction. Values can be "
                    "`.5` halves (e.g., 44.5). NULL on empty-cohort rows "
                    "(num_sgp_received == 0): a median is undefined with no "
                    "students, and bronze's sentinel 0 there is outside the "
                    "valid 1-99 scale, so it is nulled rather than carried "
                    "(which is why the tightened [1, 99] guard holds). The "
                    "mask is recorded in the transform manifest "
                    "(masked_values)."
                ),
                "short_description": (
                    "Median student growth percentile (1-99); 50 is average "
                    "growth, higher means faster growth than similar peers."
                ),
                "nullable": True,
                "example": 47.0,
            },
            {
                "name": "pct_proficient_learner_or_above",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share of students at the Proficient Learner achievement "
                    "level or higher on the EOG assessment (0-1 scale; "
                    "bronze / 100). NULL in 2023 (metric dropped)."
                ),
                "nullable": True,
                "example": 0.27,
            },
            {
                "name": "pct_developing_learner_or_above",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share of students at the Developing Learner achievement "
                    "level or higher on the EOG assessment (0-1 scale; "
                    "bronze / 100). NULL in 2023 (metric dropped)."
                ),
                "nullable": True,
                "example": 0.65,
            },
            {
                "name": "pct_sgp_typical_or_high_growth",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share of SGP-scored students with SGP >= 35 (Typical "
                    "or High growth). 0-1 scale. NULL in 2023 — Era 6 "
                    "replaced this with the three-bucket SGP split below."
                ),
                "nullable": True,
                "example": 0.63,
            },
            {
                "name": "pct_sgp_low_growth",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share of SGP-scored students in the Low Growth band "
                    "(SGP < 35). 0-1 scale. Era 6 (2023) only; NULL for "
                    "2015-2019."
                ),
                "nullable": True,
                "example": 0.34,
            },
            {
                "name": "pct_sgp_typical_growth",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share of SGP-scored students in the Typical Growth band "
                    "(35 <= SGP <= 65). 0-1 scale. Era 6 only; NULL for "
                    "2015-2019. NOT the same as pct_sgp_typical_or_high_growth "
                    "— Era 1-5's `% Typical or High` lumps typical and high "
                    "together (SGP >= 35)."
                ),
                "nullable": True,
                "example": 0.31,
            },
            {
                "name": "pct_sgp_high_growth",
                "unit": "proportion",
                "type": "float64",
                "description": (
                    "Share of SGP-scored students in the High Growth band "
                    "(SGP > 65). 0-1 scale. Era 6 only; NULL for 2015-2019."
                ),
                "nullable": True,
                "example": 0.34,
            },
        ],
        source=(
            "Georgia Insights (GaDOE) — Georgia Student Growth Model on "
            "End-of-Grade Milestones assessments"
        ),
        source_url="https://georgiainsights.gadoe.org/data-downloads/",
        update_frequency="annual",
        year_range=(int(combined["year"].min()), int(combined["year"].max())),
        partitioned_by=["year"],
        notes=[
            (
                "No GSGM data exists for 2020-2022 — GSGM was not reported "
                "during those COVID-era years. The gold fact table emits "
                "year partitions only for 2015, 2016, 2017, 2018, 2019, "
                "and 2023."
            ),
            (
                "Only grades 4-8 have SGP data because an SGP requires a "
                "prior-year score (grade 3 is the first tested grade at "
                "EOG). The 2015-2019 publications also include an "
                'AllGrades aggregate row, preserved here as grade_level="all" '
                "so the published sgp_median for the full grade-4-8 "
                "cohort survives. 2023 does not publish an AllGrades row."
            ),
            (
                "2015-2016 report four subjects (ELA, Math, Science, Social "
                "Studies). Starting 2017, only ELA and Math are reported."
            ),
            (
                "Era 1-5 and Era 6 report different growth metrics. "
                "pct_sgp_typical_or_high_growth (2015-2019) is the share with "
                "SGP >= 35 — a single two-bucket flag. Era 6 (2023) "
                "replaces that with three buckets: pct_sgp_low_growth "
                "(SGP < 35), pct_sgp_typical_growth (35 <= SGP <= 65), "
                "and pct_sgp_high_growth (SGP > 65). pct_sgp_typical_growth "
                "is NOT equivalent to pct_sgp_typical_or_high_growth — the 2023 "
                "typical excludes high."
            ),
            (
                "All percent columns are on 0-1 decimal scale per data-"
                "cleaning-standards §4 (bronze ships on 0-100; we divide by "
                "100). sgp_median is preserved on its natural 1-99 "
                "ordinal scale."
            ),
            (
                "Suppression markers differ across eras: ---- in "
                "2015-2017 (mixed with TFS in 2017), TFS in 2018, true "
                "null in 2019, and -- in 2023. All land as NULL in gold "
                "via na_values on read and strict=False on cast."
            ),
        ],
        quality_checks=[
            {
                "name": "num_sgp_received_le_num_tested",
                "description": (
                    "Students receiving an SGP are a subset of those tested, "
                    "so num_sgp_received <= num_tested where both are present."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "num_sgp_received IS NOT NULL "
                    "AND num_tested IS NOT NULL "
                    "AND num_sgp_received > num_tested"
                ),
                "mustBe": 0,
            },
            {
                "name": "sgp_received_rate_matches_counts",
                "description": (
                    "sgp_received_rate equals num_sgp_received / num_tested "
                    "(+/-0.02 for publisher rounding) where the counts and "
                    "the rate are all present and num_tested > 0."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "sgp_received_rate IS NOT NULL "
                    "AND num_sgp_received IS NOT NULL "
                    "AND num_tested IS NOT NULL "
                    "AND num_tested > 0 "
                    "AND ABS(sgp_received_rate "
                    "- (CAST(num_sgp_received AS DOUBLE) / num_tested)) > 0.02"
                ),
                "mustBe": 0,
            },
            {
                "name": "proficient_le_developing_or_above",
                "description": (
                    "Proficient-or-above is nested within Developing-or-above, "
                    "so pct_proficient_learner_or_above <= "
                    "pct_developing_learner_or_above where both are present."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "pct_proficient_learner_or_above IS NOT NULL "
                    "AND pct_developing_learner_or_above IS NOT NULL "
                    "AND pct_proficient_learner_or_above "
                    "> pct_developing_learner_or_above + 0.0001"
                ),
                "mustBe": 0,
            },
            {
                "name": "sgp_growth_bands_sum_to_one",
                "description": (
                    "The three 2023 SGP growth bands (Low, Typical, High) "
                    "partition the SGP-scored students and sum to 1.0 "
                    "(+/-0.02) where all three are present."
                ),
                "dimension": "consistency",
                "query": (
                    "SELECT COUNT(*) FROM {object} WHERE "
                    "pct_sgp_low_growth IS NOT NULL "
                    "AND pct_sgp_typical_growth IS NOT NULL "
                    "AND pct_sgp_high_growth IS NOT NULL "
                    "AND ABS(pct_sgp_low_growth + pct_sgp_typical_growth "
                    "+ pct_sgp_high_growth - 1.0) > 0.02"
                ),
                "mustBe": 0,
            },
        ],
    )

    summary = manifest.tracker.summary()
    logger.info(
        f"Done. Bronze rows: {summary['total_bronze']:,}; "
        f"Gold rows: {summary['total_gold']:,}; "
        f"Years: {summary['years_processed']}"
    )

    # ALWAYS LAST: validate gold against the contract just emitted.
    run_topic_validation(GOLD_DIR)


if __name__ == "__main__":
    main()
