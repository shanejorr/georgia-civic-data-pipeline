"""Object-store upload/download utilities for the Georgia Data Platform.

Gold and bronze live in Cloudflare R2 (S3-compatible). The client talks to the
R2 endpoint via boto3; the returned ``s3://bucket/key`` URIs are the same scheme
DuckDB resolves through its R2 secret on the read side.
"""

import logging
import os
from pathlib import Path
from typing import Literal

import boto3

logger = logging.getLogger(__name__)

# Bucket configuration
BUCKET_NAMES: dict[str, str] = {
    "bronze": "georgia-data-bronze",
    "gold": "georgia-data-gold",
}

# R2's S3 API uses a fixed "auto" region.
R2_REGION = "auto"


def _r2_endpoint_url() -> str:
    """Build the account-scoped R2 S3 endpoint from the environment."""
    account_id = os.environ.get("R2_ACCOUNT_ID")
    if not account_id:
        raise RuntimeError(
            "R2_ACCOUNT_ID is not set — required to upload/download against "
            "Cloudflare R2. Set R2_ACCOUNT_ID / R2_ACCESS_KEY_ID / "
            "R2_SECRET_ACCESS_KEY in the environment."
        )
    return f"https://{account_id}.r2.cloudflarestorage.com"


def _get_s3_client():
    """Create a boto3 client pointed at Cloudflare R2.

    Credentials and account id come from the environment (R2_ACCESS_KEY_ID /
    R2_SECRET_ACCESS_KEY / R2_ACCOUNT_ID). R2 rejects some of botocore's default
    flexible checksums, so request them only when the operation requires it —
    honored by modern botocore, silently ignored by older versions.

    Returns:
        boto3 S3 client bound to the R2 endpoint.
    """
    os.environ.setdefault("AWS_REQUEST_CHECKSUM_CALCULATION", "when_required")
    os.environ.setdefault("AWS_RESPONSE_CHECKSUM_VALIDATION", "when_required")

    access_key = os.environ.get("R2_ACCESS_KEY_ID")
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY")
    if not (access_key and secret_key):
        raise RuntimeError(
            "R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY are not set — required to "
            "upload/download against Cloudflare R2."
        )

    session = boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=R2_REGION,
    )
    return session.client("s3", endpoint_url=_r2_endpoint_url())


def _get_bucket_name(bucket: Literal["bronze", "gold"]) -> str:
    """Resolve bucket type to actual bucket name.

    Args:
        bucket: Either "bronze" for raw data or "gold" for processed data.

    Returns:
        The full S3 bucket name.

    Raises:
        ValueError: If bucket type is not recognized.
    """
    if bucket not in BUCKET_NAMES:
        raise ValueError(f"Unknown bucket type: {bucket}. Must be 'bronze' or 'gold'.")
    return BUCKET_NAMES[bucket]


def _build_partitioned_key(key: str, partition_by: dict[str, str]) -> str:
    """Insert partition path segments before the filename.

    Args:
        key: The base S3 key (e.g., "education/enrollment/data.parquet").
        partition_by: Partition key-value pairs (e.g., {"year": "2024"}).

    Returns:
        Key with partition path inserted
        (e.g., "education/enrollment/year=2024/data.parquet").
    """
    key_path = Path(key)
    parent = str(key_path.parent)
    filename = key_path.name

    # Build partition path segments
    partition_parts = "/".join(f"{k}={v}" for k, v in partition_by.items())

    # Combine: parent/partition_parts/filename
    if parent and parent != ".":
        return f"{parent}/{partition_parts}/{filename}"
    return f"{partition_parts}/{filename}"


def upload(
    local_path: Path,
    bucket: Literal["bronze", "gold"],
    key: str,
    partition_by: dict[str, str] | None = None,
    metadata: dict[str, str] | None = None,
) -> str | None:
    """Upload a file to S3.

    Args:
        local_path: Path to the local file to upload.
        bucket: Target bucket type - "bronze" for raw data, "gold" for processed data.
        key: S3 object key (path within the bucket).
        partition_by: Optional partition key-value pairs. If provided, partition path
            segments are inserted before the filename (e.g., {"year": "2024"} creates
            "year=2024/" in the path).
        metadata: Optional metadata key-value pairs to attach to the S3 object.
            Common keys: source_url, download_date, description, original_filename.

    Returns:
        The full S3 URI (s3://bucket/key) on success, or None if upload was skipped.

    Raises:
        FileNotFoundError: If the local file does not exist.
        ClientError: If the S3 upload fails.

    Example:
        >>> upload(
        ...     local_path=Path("data/gold/education/enrollment.parquet"),
        ...     bucket="gold",
        ...     key="education/enrollment/data.parquet",
        ...     partition_by={"year": "2024"},
        ... )
        's3://georgia-data-gold/education/enrollment/year=2024/data.parquet'
    """
    # Check if uploads should be skipped (local development)
    if os.environ.get("SKIP_S3_UPLOAD"):
        logger.info("Skipping S3 upload (SKIP_S3_UPLOAD is set): %s", local_path)
        return None

    # Validate local file exists
    if not local_path.exists():
        raise FileNotFoundError(f"Local file not found: {local_path}")

    # Resolve bucket name and build final key
    bucket_name = _get_bucket_name(bucket)
    final_key = _build_partitioned_key(key, partition_by) if partition_by else key

    # Upload to S3
    s3_client = _get_s3_client()
    logger.info("Uploading %s to s3://%s/%s", local_path, bucket_name, final_key)

    extra_args = {"Metadata": metadata} if metadata else None
    s3_client.upload_file(str(local_path), bucket_name, final_key, ExtraArgs=extra_args)

    s3_uri = f"s3://{bucket_name}/{final_key}"
    logger.info("Upload complete: %s", s3_uri)
    return s3_uri


def download(
    bucket: Literal["bronze", "gold"],
    key: str,
    local_path: Path,
) -> Path:
    """Download a file from S3.

    Args:
        bucket: Source bucket type - "bronze" for raw data, "gold" for processed data.
        key: S3 object key (path within the bucket).
        local_path: Local path where the file should be saved.

    Returns:
        The local path where the file was saved.

    Raises:
        ClientError: If the S3 download fails (e.g., file not found).

    Example:
        >>> download(
        ...     bucket="gold",
        ...     key="crosswalks/counties.parquet",
        ...     local_path=Path("data/gold/crosswalks/counties.parquet"),
        ... )
        PosixPath('data/gold/crosswalks/counties.parquet')
    """
    bucket_name = _get_bucket_name(bucket)

    # Create parent directories if needed
    local_path.parent.mkdir(parents=True, exist_ok=True)

    # Download from S3
    s3_client = _get_s3_client()
    logger.info("Downloading s3://%s/%s to %s", bucket_name, key, local_path)

    s3_client.download_file(bucket_name, key, str(local_path))

    logger.info("Download complete: %s", local_path)
    return local_path
