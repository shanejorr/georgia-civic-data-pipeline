"""File reading utilities for bronze data files.

This module provides unified file reading for CSV, XLS, and XLSX formats,
with automatic format detection and consistent output handling.
"""

import logging
import re
from pathlib import Path

import pandas as pd
import polars as pl

logger = logging.getLogger(__name__)

# Suppression values that should be converted to null
SUPPRESSION_VALUES = {
    "TFS",
    "tfs",
    "Too Few Students",
    "Too few students",
    "N/A",
    "n/a",
    "NA",
    "na",
    "*",
    "**",
    "***",
    "-",
}


def _detect_file_type(path: Path) -> str:
    """Detect actual file type by checking magic bytes.

    Some bronze files have incorrect extensions (e.g., XLS files with .csv extension).
    This function checks the file magic bytes to determine the true format.

    Args:
        path: Path to the file.

    Returns:
        One of: "csv", "xls", "xlsx"
    """
    with open(path, "rb") as f:
        header = f.read(8)

    # XLS (OLE2 Compound Document) magic bytes: D0 CF 11 E0 A1 B1 1A E1
    if header[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "xls"

    # XLSX (ZIP archive) magic bytes: PK (50 4B)
    if header[:2] == b"PK":
        return "xlsx"

    # Default to CSV for text files
    return "csv"


def _count_raw_csv_rows(path: Path) -> int:
    """Count raw data lines in a CSV (non-empty lines minus the header).

    This is an **upper bound** on the true record count: a quoted field
    containing newlines spans multiple physical lines but is one record. The
    read-loss accounting therefore only flags ``parsed < raw`` (possible
    loss), never ``parsed > raw``.
    """
    raw = 0
    with open(path, "rb") as fh:
        for line in fh:
            if line.strip():
                raw += 1
    return max(raw - 1, 0)


def read_bronze_file(
    path: Path,
    null_values: set[str] | None = None,
    infer_schema_length: int = 10000,
    return_loss: bool = False,
    encoding: str = "utf8",
) -> pl.DataFrame | tuple[pl.DataFrame, dict]:
    """Read a bronze data file (CSV, XLS, or XLSX) into a Polars DataFrame.

    Automatically detects file format based on magic bytes (not just extension)
    and uses appropriate reader. Handles common data suppression values as nulls.

    Args:
        path: Path to the file to read.
        null_values: Additional values to treat as null. TFS and common
            suppression markers are always included.
        infer_schema_length: Number of rows to use for schema inference (CSV only).
        return_loss: When True, also return a read-loss accounting dict
            ``{"raw_rows", "parsed_rows", "format"}``. ``raw_rows`` is the
            pre-parse record count (CSV: physical data-line count, an upper
            bound when fields contain quoted newlines; Excel: parity with the
            parsed frame — pandas does not drop rows). A ``parsed_rows <
            raw_rows`` delta means the parser dropped/merged records
            (malformed rows, truncation) and must be investigated — record it
            via ``TransformManifest.record_read_loss``.
        encoding: CSV byte encoding passed through to ``pl.read_csv``
            (``"utf8"`` or ``"utf8-lossy"``). Use ``"utf8-lossy"`` for sources
            with stray Windows-1252 bytes (e.g. the juvenile clearinghouse
            placements file) so invalid sequences decode to U+FFFD instead of
            failing the polars read and falling back to the slow pandas
            latin-1 path (which would mis-decode those bytes).

    Returns:
        Polars DataFrame, or ``(DataFrame, loss_dict)`` when ``return_loss``.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file format is not supported.

    Examples:
        >>> df = read_bronze_file(Path("data/bronze/education/act_scores_2024.csv"))
        >>> df, loss = read_bronze_file(
        ...     Path("data/bronze/education/act_scores_2006.xls"), return_loss=True
        ... )
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # Combine default and custom null values
    all_null_values = SUPPRESSION_VALUES.copy()
    if null_values:
        all_null_values.update(null_values)

    # Detect actual file type from magic bytes (handles mislabeled files)
    file_type = _detect_file_type(path)
    declared_suffix = path.suffix.lower()

    if file_type != declared_suffix.lstrip("."):
        logger.warning(
            "File %s has extension %s but is actually %s format",
            path.name,
            declared_suffix,
            file_type,
        )

    if file_type == "csv":
        df = _read_csv(path, all_null_values, infer_schema_length, encoding)
    elif file_type == "xls":
        df = _read_xls(path, all_null_values)
    elif file_type == "xlsx":
        df = _read_xlsx(path, all_null_values)
    else:
        raise ValueError(f"Unsupported file format: {file_type}")

    if not return_loss:
        return df

    # CSV readers can silently drop malformed/truncated rows
    # (ignore_errors=True, on_bad_lines="warn", the truncated-row fixer);
    # raw-vs-parsed accounting makes that loss visible to the manifest.
    # Excel reads load whole sheets via pandas, so raw == parsed by
    # construction.
    if file_type == "csv":
        raw_rows = _count_raw_csv_rows(path)
    else:
        raw_rows = df.height
    loss = {"raw_rows": raw_rows, "parsed_rows": df.height, "format": file_type}
    if df.height < raw_rows:
        logger.warning(
            "Read loss in %s: raw=%d parsed=%d (%d row(s) dropped at read "
            "time — investigate; raw is an upper bound for quoted multi-line "
            "fields)",
            path.name,
            raw_rows,
            df.height,
            raw_rows - df.height,
        )
    return df, loss


def _read_csv(
    path: Path,
    null_values: set[str],
    infer_schema_length: int,
    encoding: str = "utf8",
) -> pl.DataFrame:
    """Read a CSV file into a Polars DataFrame.

    Args:
        path: Path to CSV file.
        null_values: Values to treat as null.
        infer_schema_length: Number of rows for schema inference.
        encoding: Byte encoding for polars ("utf8" or "utf8-lossy").

    Returns:
        Polars DataFrame.
    """
    logger.debug("Reading CSV: %s", path)

    try:
        return pl.read_csv(
            path,
            null_values=list(null_values),
            infer_schema_length=infer_schema_length,
            ignore_errors=True,  # Handle malformed rows gracefully
            encoding=encoding,
        )
    except Exception as e:
        logger.warning("Polars CSV read failed, falling back to pandas: %s", e)
        # Fallback to pandas for problematic CSVs with encoding fallbacks
        encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
        for encoding in encodings:
            try:
                pdf = pd.read_csv(
                    path,
                    na_values=list(null_values),
                    low_memory=False,
                    encoding=encoding,
                    on_bad_lines="warn",  # Skip malformed/truncated rows
                )
                logger.debug("Successfully read CSV with %s encoding", encoding)
                return pl.from_pandas(pdf)
            except UnicodeDecodeError:
                continue
            except pd.errors.ParserError as parse_error:
                logger.warning(
                    "Parser error with %s encoding: %s", encoding, parse_error
                )
                continue

        # Final fallback: try reading as StringIO after fixing truncation issues
        logger.warning("Attempting to read truncated CSV by fixing incomplete rows")
        try:
            return _read_truncated_csv(path, null_values)
        except Exception as truncate_error:
            logger.warning("Truncated CSV fix failed: %s", truncate_error)

        raise ValueError(f"Could not read CSV with any supported encoding: {path}")


def _read_truncated_csv(path: Path, null_values: set[str]) -> pl.DataFrame:
    """Read a truncated CSV file by removing incomplete final rows.

    Some bronze CSV files are truncated mid-row (e.g., due to export errors).
    This function reads the file, removes any incomplete rows at the end,
    and parses the remaining valid content.

    Args:
        path: Path to truncated CSV file.
        null_values: Values to treat as null.

    Returns:
        Polars DataFrame with valid rows only.
    """
    import io

    # Read file content
    content = path.read_text(encoding="utf-8", errors="replace")

    # Find the last complete row (ends with newline followed by valid row start or EOF)
    lines = content.split("\n")

    # Remove trailing empty lines
    while lines and not lines[-1].strip():
        lines.pop()

    if not lines:
        raise ValueError(f"Empty CSV file: {path}")

    # Check if last line is incomplete (odd number of quotes = unclosed string)
    # A simple heuristic: if last line has odd quotes and doesn't end with quote+comma
    last_line = lines[-1]
    if last_line.count('"') % 2 != 0:
        logger.warning(
            "Removing incomplete final row from %s (had %d characters)",
            path.name,
            len(last_line),
        )
        lines.pop()

    # Reconstruct the CSV content
    fixed_content = "\n".join(lines)

    # Parse with polars from string
    return pl.read_csv(
        io.StringIO(fixed_content),
        null_values=list(null_values),
        infer_schema_length=10000,
        ignore_errors=True,
    )


def _read_xls(path: Path, null_values: set[str]) -> pl.DataFrame:
    """Read a legacy XLS file into a Polars DataFrame.

    Uses pandas with xlrd engine for legacy Excel format support.

    Args:
        path: Path to XLS file.
        null_values: Values to treat as null.

    Returns:
        Polars DataFrame.
    """
    logger.debug("Reading XLS: %s", path)

    # xlrd is required for .xls files
    # Read all columns as strings to avoid type conversion issues with mixed types.
    pdf = pd.read_excel(
        path,
        engine="xlrd",
        na_values=list(null_values),
        dtype=str,
    )
    return pl.from_pandas(pdf)


def _read_xlsx(path: Path, null_values: set[str]) -> pl.DataFrame:
    """Read an XLSX file into a Polars DataFrame.

    Uses pandas with openpyxl engine for modern Excel format.

    Args:
        path: Path to XLSX file.
        null_values: Values to treat as null.

    Returns:
        Polars DataFrame.
    """
    logger.debug("Reading XLSX: %s", path)

    # Read all columns as strings to avoid type conversion issues with mixed types.
    pdf = pd.read_excel(
        path,
        engine="openpyxl",
        na_values=list(null_values),
        dtype=str,
    )
    return pl.from_pandas(pdf)


def extract_year_from_filename(filename: str) -> int | None:
    """Extract a 4-digit year from a filename.

    Looks for patterns like 'data_2024.csv' or 'report_2023-24.xlsx'.

    Args:
        filename: The filename to parse.

    Returns:
        The extracted year as an integer, or None if not found.

    Examples:
        >>> extract_year_from_filename("act_scores_2024.csv")
        2024
        >>> extract_year_from_filename("enrollment_2023-2024.xlsx")
        2024
        >>> extract_year_from_filename("enrollment_2023-24.xlsx")
        2024
        >>> extract_year_from_filename("data.csv")
        None
    """
    # School-year spans first — they must win over the bare-year pattern,
    # otherwise "2023-24" would match "2023" and return the starting year.
    # Full span: "2023-2024" -> 2024 (the ending year).
    match = re.search(r"20[0-9]{2}-(20[0-9]{2})", filename)
    if match:
        return int(match.group(1))

    # Short span: "2023-24" -> 2024. (?![0-9]) keeps "2023-2024" from
    # matching here with suffix "20".
    match = re.search(r"(20[0-9]{2})-([0-9]{2})(?![0-9])", filename)
    if match:
        start_year = int(match.group(1))
        suffix = int(match.group(2))
        end_year = (start_year // 100) * 100 + suffix
        if end_year < start_year:
            # Century rollover (e.g., "2099-00").
            end_year += 100
        return end_year

    # Bare 4-digit year (2000-2099).
    match = re.search(r"20[0-9]{2}", filename)
    if match:
        return int(match.group())

    return None


def format_school_year(year: int) -> str:
    """Convert a calendar year to school year format.

    School years span two calendar years (e.g., 2023-2024 school year
    ends in calendar year 2024).

    Args:
        year: The ending calendar year of the school year.

    Returns:
        School year in "YYYY-YYYY" format.

    Examples:
        >>> format_school_year(2024)
        '2023-2024'
        >>> format_school_year(2011)
        '2010-2011'
    """
    return f"{year - 1}-{year}"


def format_school_year_expr(year: pl.Expr) -> pl.Expr:
    """Convert a calendar year expression to school year format.

    This is the vectorized Polars equivalent of `format_school_year()` and avoids
    Python UDFs (`map_elements`) for better performance.

    Args:
        year: Polars expression containing the ending calendar year of the school year.

    Returns:
        Polars expression producing school year strings in "YYYY-YYYY" format.

    Examples:
        >>> import polars as pl
        >>> pl.DataFrame({"year": [2024]}).with_columns(
        ...     format_school_year_expr(pl.col("year")).alias("school_year")
        ... )["school_year"].to_list()
        ['2023-2024']
    """
    year_int = year.cast(pl.Int32, strict=False)
    return pl.concat_str(
        [
            (year_int - 1).cast(pl.Utf8),
            pl.lit("-"),
            year_int.cast(pl.Utf8),
        ]
    )


def parse_school_year(school_year: str) -> int:
    """Parse a school year string to get the ending year.

    Handles various formats like "2023-24", "2023-2024", "2023-24".

    Args:
        school_year: School year string.

    Returns:
        The ending calendar year.

    Examples:
        >>> parse_school_year("2023-24")
        2024
        >>> parse_school_year("2023-2024")
        2024
        >>> parse_school_year("2010-11")
        2011
    """
    # Remove any whitespace
    school_year = school_year.strip()

    # Try "YYYY-YYYY" format
    match = re.match(r"(\d{4})-(\d{4})", school_year)
    if match:
        return int(match.group(2))

    # Try "YYYY-YY" format
    match = re.match(r"(\d{4})-(\d{2})", school_year)
    if match:
        start_year = int(match.group(1))
        end_suffix = int(match.group(2))
        # Determine century
        start_century = start_year // 100
        if end_suffix < start_year % 100:
            # Crossed century boundary (e.g., 1999-00)
            return (start_century + 1) * 100 + end_suffix
        return start_century * 100 + end_suffix

    raise ValueError(f"Unable to parse school year: '{school_year}'")


def list_bronze_files(
    directory: Path,
    extensions: list[str] | None = None,
) -> list[Path]:
    """List all bronze data files in a directory.

    Args:
        directory: Directory to search.
        extensions: File extensions to include (default: [".csv", ".xls", ".xlsx"]).

    Returns:
        List of file paths sorted by name.
    """
    if extensions is None:
        extensions = [".csv", ".xls", ".xlsx"]

    files = []
    for ext in extensions:
        files.extend(directory.glob(f"*{ext}"))

    return sorted(files, key=lambda p: p.name)
