"""S3 client for export file storage.

Provides functions to upload export files and generate pre-signed download URLs.
"""

import logging
import os
import re
from datetime import datetime
from uuid import UUID

import boto3
from botocore.config import Config
from mypy_boto3_s3 import S3Client

logger = logging.getLogger(__name__)

# Default URL expiry time in seconds (1 hour)
DEFAULT_URL_EXPIRY_SECONDS = 3600


def get_s3_client() -> S3Client:
    """Get a configured S3 client.

    Uses AWS credentials from environment or IAM role.

    :returns: boto3 S3 client.
    """
    region = os.environ.get("AWS_REGION", "eu-west-2")
    return boto3.client(
        "s3",
        region_name=region,
        config=Config(signature_version="s3v4"),
    )


def _sanitize_filename(name: str) -> str:
    """Sanitize a string for use in a filename.

    Replaces spaces with underscores and removes special characters.

    :param name: The name to sanitize.
    :returns: Sanitized filename-safe string.
    """
    # Replace spaces with underscores
    name = name.replace(" ", "_")
    # Remove any characters that aren't alphanumeric, underscore, or hyphen
    name = re.sub(r"[^\w\-]", "", name)
    # Convert to lowercase for consistency
    return name.lower()


def upload_export(
    content: bytes,
    user_id: UUID,
    job_id: UUID,
    file_format: str,
    dataset_name: str | None = None,
) -> str:
    """Upload an export file to S3.

    :param content: File content as bytes.
    :param user_id: User ID for path isolation.
    :param job_id: Job ID for unique filename.
    :param file_format: File format (csv/parquet).
    :param dataset_name: Optional dataset name for a friendlier filename.
    :returns: S3 key of uploaded file.
    :raises ValueError: If S3_EXPORTS_BUCKET is not configured.
    """
    bucket = os.environ.get("S3_EXPORTS_BUCKET")
    if not bucket:
        raise ValueError("S3_EXPORTS_BUCKET environment variable not set")

    # Build filename: dataset_name_YYYY-MM-DD_HHMM_shortid.format or fallback to job_id
    # Short ID suffix ensures uniqueness for concurrent/repeated exports
    short_id = str(job_id)[:8]
    if dataset_name:
        safe_name = _sanitize_filename(dataset_name)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        filename = f"{safe_name}_{timestamp}_{short_id}.{file_format}"
    else:
        filename = f"{job_id}.{file_format}"

    # Build S3 key with user isolation
    key = f"exports/{user_id}/{filename}"

    # Determine content type
    content_type = "text/csv" if file_format == "csv" else "application/octet-stream"

    client = get_s3_client()
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=content,
        ContentType=content_type,
    )

    logger.info(f"Uploaded export: bucket={bucket}, key={key}, size={len(content)} bytes")
    return key


def generate_download_url(s3_key: str, expires_in: int = DEFAULT_URL_EXPIRY_SECONDS) -> str:
    """Generate a pre-signed download URL for an S3 object.

    :param s3_key: S3 object key.
    :param expires_in: URL expiry in seconds (default 1 hour).
    :returns: Pre-signed URL for download.
    :raises ValueError: If S3_EXPORTS_BUCKET is not configured.
    """
    bucket = os.environ.get("S3_EXPORTS_BUCKET")
    if not bucket:
        raise ValueError("S3_EXPORTS_BUCKET environment variable not set")

    client = get_s3_client()
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": s3_key},
        ExpiresIn=expires_in,
    )

    logger.debug(f"Generated download URL: key={s3_key}, expires_in={expires_in}s")
    return url
