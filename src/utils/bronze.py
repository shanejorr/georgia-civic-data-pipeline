"""Bronze data utilities for downloading and uploading raw source files."""

import logging
import re
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

from src.utils.s3 import upload

logger = logging.getLogger(__name__)

# Base path for local bronze data storage
BRONZE_DATA_DIR = Path("data/bronze")


def to_snake_case(filename: str) -> str:
    """Convert a filename to snake_case while preserving the extension.

    Handles camelCase, PascalCase, spaces, hyphens, and other common patterns.

    Args:
        filename: The original filename (e.g., "MyDataFile.csv",
            "School Enrollment 2024.xlsx", "some-file-name.xls").

    Returns:
        The filename converted to snake_case (e.g., "my_data_file.csv",
        "school_enrollment_2024.xlsx", "some_file_name.xls").

    Example:
        >>> to_snake_case("School Enrollment 2024.xlsx")
        'school_enrollment_2024.xlsx'
        >>> to_snake_case("MyDataFile.CSV")
        'my_data_file.csv'
    """
    # Split into stem and extension
    path = Path(filename)
    stem = path.stem
    extension = path.suffix.lower()

    # URL decode any encoded characters
    stem = unquote(stem)

    # Insert underscore before uppercase letters (handle camelCase/PascalCase)
    stem = re.sub(r"([a-z])([A-Z])", r"\1_\2", stem)

    # Insert underscore between letters and numbers
    stem = re.sub(r"([a-zA-Z])(\d)", r"\1_\2", stem)
    stem = re.sub(r"(\d)([a-zA-Z])", r"\1_\2", stem)

    # Replace spaces, hyphens, and multiple underscores with single underscore
    stem = re.sub(r"[\s\-]+", "_", stem)
    stem = re.sub(r"_+", "_", stem)

    # Remove non-alphanumeric characters except underscores
    stem = re.sub(r"[^a-zA-Z0-9_]", "", stem)

    # Convert to lowercase and strip leading/trailing underscores
    stem = stem.lower().strip("_")

    return f"{stem}{extension}"


def extract_filename_from_url(url: str) -> str:
    """Extract the filename from a URL.

    Args:
        url: The source URL (e.g., "https://example.com/data/file.csv").

    Returns:
        The filename extracted from the URL path.

    Raises:
        ValueError: If no filename can be extracted from the URL.

    Example:
        >>> extract_filename_from_url("https://example.com/data/enrollment.csv")
        'enrollment.csv'
    """
    parsed = urlparse(url)
    path = unquote(parsed.path)

    # Get the last segment of the path
    filename = Path(path).name

    if not filename or "." not in filename:
        raise ValueError(f"Could not extract filename from URL: {url}")

    return filename


def download_from_url(
    url: str,
    folder: str,
    filename: str | None = None,
    timeout: int = 60,
    skip_existing: bool = False,
) -> Path | None:
    """Download a raw data file from a URL and save to local bronze directory.

    Downloads the file from the specified URL and saves it to
    data/bronze/{folder}/{snake_case_filename}. The filename is automatically
    converted to snake_case.

    Args:
        url: The source URL to download from.
        folder: Subdirectory within bronze (e.g., "education/enrollment").
        filename: Optional override filename. If not provided, extracted from URL.
        timeout: Request timeout in seconds. Defaults to 60.
        skip_existing: If True, skip download if file already exists locally.
            Defaults to False.

    Returns:
        Path to the downloaded file, or None if skipped.

    Raises:
        requests.RequestException: If the download fails.
        ValueError: If no filename can be determined.

    Example:
        >>> download_from_url(
        ...     url="https://gosa.georgia.gov/data/Enrollment2024.xlsx",
        ...     folder="education/enrollment",
        ... )
        PosixPath('data/bronze/education/enrollment/enrollment_2024.xlsx')
    """
    # Determine filename
    if filename is None:
        filename = extract_filename_from_url(url)

    # Convert to snake_case
    snake_filename = to_snake_case(filename)

    # Build local path
    local_path = BRONZE_DATA_DIR / folder / snake_filename
    local_path.parent.mkdir(parents=True, exist_ok=True)

    # Skip if file exists and skip_existing is True
    if skip_existing and local_path.exists():
        logger.info("Skipping existing file: %s", local_path)
        return None

    logger.info("Downloading %s to %s", url, local_path)

    # Download with streaming for large files
    response = requests.get(url, timeout=timeout, stream=True)
    response.raise_for_status()

    with open(local_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    logger.info("Download complete: %s", local_path)
    return local_path


def upload_to_s3(
    local_path: Path,
    folder: str,
    description: str | None = None,
    source_url: str | None = None,
    original_filename: str | None = None,
    download_date: str | None = None,
) -> str | None:
    """Upload a local bronze file to S3 with optional metadata.

    Uploads the file to s3://georgia-data-bronze/{folder}/{filename}.

    Args:
        local_path: Path to the local file to upload.
        folder: S3 key prefix (e.g., "education/enrollment").
        description: Human-readable description of the data.
        source_url: Original URL where the data was downloaded from.
        original_filename: Original filename before snake_case conversion.
        download_date: ISO 8601 date when the file was downloaded.

    Returns:
        The full S3 URI on success, or None if upload was skipped.

    Raises:
        FileNotFoundError: If the local file does not exist.
        ClientError: If the S3 upload fails.

    Example:
        >>> upload_to_s3(
        ...     local_path=Path("data/bronze/education/enrollment.xlsx"),
        ...     folder="education/enrollment",
        ...     description="K-12 enrollment by county",
        ... )
        's3://georgia-data-bronze/education/enrollment/enrollment.xlsx'
    """
    key = f"{folder}/{local_path.name}"

    # Build metadata dict from provided values
    metadata: dict[str, str] = {}
    if description:
        metadata["description"] = description
    if source_url:
        metadata["source_url"] = source_url
    if original_filename:
        metadata["original_filename"] = original_filename
    if download_date:
        metadata["download_date"] = download_date

    return upload(
        local_path=local_path,
        bucket="bronze",
        key=key,
        metadata=metadata if metadata else None,
    )


def download_and_upload(
    url: str,
    folder: str,
    filename: str | None = None,
    description: str | None = None,
    timeout: int = 60,
    skip_existing: bool = False,
) -> tuple[Path | None, str | None]:
    """Download a file from URL and upload to S3 bronze bucket with metadata.

    Convenience function that combines download_from_url and upload_to_s3.
    Automatically populates metadata: source_url, download_date, original_filename.

    Args:
        url: The source URL to download from.
        folder: Subdirectory for both local storage and S3 key prefix.
        filename: Optional override filename.
        description: Human-readable description of the data.
        timeout: Request timeout in seconds. Defaults to 60.
        skip_existing: If True, skip download if file already exists locally.
            Defaults to False.

    Returns:
        Tuple of (local_path, s3_uri). Both may be None if download was skipped.

    Example:
        >>> download_and_upload(
        ...     url="https://gosa.georgia.gov/data/Enrollment2024.xlsx",
        ...     folder="education/enrollment",
        ...     description="K-12 enrollment by county",
        ... )
        (PosixPath('data/bronze/education/enrollment/enrollment_2024.xlsx'),
         's3://georgia-data-bronze/education/enrollment/enrollment_2024.xlsx')
    """
    # Extract original filename before download converts to snake_case
    original_filename = filename if filename else extract_filename_from_url(url)

    local_path = download_from_url(
        url=url,
        folder=folder,
        filename=filename,
        timeout=timeout,
        skip_existing=skip_existing,
    )

    # If download was skipped, return None for both
    if local_path is None:
        return None, None

    # Upload with auto-populated metadata
    s3_uri = upload_to_s3(
        local_path=local_path,
        folder=folder,
        description=description,
        source_url=url,
        original_filename=original_filename,
        download_date=date.today().isoformat(),
    )
    return local_path, s3_uri
