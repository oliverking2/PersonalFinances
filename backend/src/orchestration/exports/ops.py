"""Dataset export operations.

Dagster op for exporting datasets to S3 as CSV or Parquet files.
"""

import csv
import io
import json
import logging
from datetime import date
from typing import Any, Optional
from uuid import UUID

import pyarrow as pa
import pyarrow.parquet as pq
from dagster import Config, OpExecutionContext, op

from src.duckdb.client import execute_query
from src.duckdb.manifest import get_dataset_schema
from src.duckdb.queries import build_dataset_query
from src.postgres.auth.models import User
from src.postgres.common.enums import JobStatus
from src.postgres.common.operations.jobs import update_job_status
from src.providers.s3 import generate_download_url, upload_export
from src.telegram.client import TelegramClient
from src.telegram.utils.config import get_telegram_settings

logger = logging.getLogger(__name__)


class DatasetExportConfig(Config):
    """Configuration for dataset export op.

    Note: Uses Optional[] instead of | None due to Dagster Config limitations.
    Filters are passed as JSON strings because Dagster Config doesn't support
    complex nested types like list[dict].
    """

    job_id: str
    user_id: str
    dataset_id: str
    file_format: str = "csv"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    account_ids: Optional[list[str]] = None
    tag_ids: Optional[list[str]] = None
    # JSON-encoded filters (Dagster doesn't support list[dict] in Config)
    enum_filters_json: Optional[str] = None
    numeric_filters_json: Optional[str] = None


def _convert_to_csv(rows: list[dict[str, Any]], columns: list[str]) -> bytes:
    """Convert query results to CSV bytes.

    :param rows: List of row dictionaries.
    :param columns: List of column names for header order.
    :returns: CSV content as bytes.
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def _sanitize_value_for_parquet(value: Any) -> Any:
    """Recursively convert values that PyArrow cannot handle natively.

    Converts UUIDs to strings so PyArrow can infer the schema.
    Handles nested dicts and lists.

    :param value: Value that may need conversion.
    :returns: Value converted to PyArrow-compatible type.
    """
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: _sanitize_value_for_parquet(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_value_for_parquet(item) for item in value]
    return value


def _sanitize_row_for_parquet(row: dict[str, Any]) -> dict[str, Any]:
    """Convert values that PyArrow cannot handle natively.

    Converts UUIDs to strings so PyArrow can infer the schema.

    :param row: Row dictionary with potentially unsupported types.
    :returns: Row with all values converted to PyArrow-compatible types.
    """
    return {key: _sanitize_value_for_parquet(value) for key, value in row.items()}


def _convert_to_parquet(rows: list[dict[str, Any]]) -> bytes:
    """Convert query results to Parquet bytes.

    :param rows: List of row dictionaries.
    :returns: Parquet content as bytes.
    """
    # Sanitize rows to convert UUIDs and other unsupported types
    sanitized_rows = [_sanitize_row_for_parquet(row) for row in rows]
    table = pa.Table.from_pylist(sanitized_rows)
    output = io.BytesIO()
    pq.write_table(table, output)
    return output.getvalue()


def _send_telegram_notification(
    user: User,
    dataset_name: str,
    row_count: int,
    download_url: str,
) -> None:
    """Send Telegram notification for completed export.

    Only sends if user has linked their Telegram account.

    :param user: User who requested the export.
    :param dataset_name: Name of the exported dataset.
    :param row_count: Number of rows in the export.
    :param download_url: Pre-signed download URL.
    """
    if not user.telegram_chat_id:
        logger.debug(f"User {user.id} has no Telegram chat ID, skipping notification")
        return

    try:
        settings = get_telegram_settings()
    except Exception:
        logger.debug("Telegram not configured, skipping notification")
        return

    if not settings.bot_token:
        logger.debug("Telegram bot token not configured, skipping notification")
        return

    client = TelegramClient(bot_token=settings.bot_token)
    message = (
        f"<b>Export Ready</b>\n\n"
        f"Your <b>{dataset_name}</b> export is ready.\n"
        f"Rows: {row_count:,}\n\n"
        f'<a href="{download_url}">Download File</a>\n\n'
        f"<i>Link expires in 1 hour</i>"
    )

    try:
        client.send_message_sync(text=message, chat_id=user.telegram_chat_id)
        logger.info(f"Sent export notification to user {user.id}")
    except Exception as e:
        # Don't fail the export if notification fails
        logger.warning(f"Failed to send Telegram notification: {e}")


@op(required_resource_keys={"postgres_database"})
def export_dataset(context: OpExecutionContext, config: DatasetExportConfig) -> None:
    """Export a dataset to S3.

    1. Mark job as RUNNING
    2. Load dataset schema from manifest
    3. Build query (no row limit for exports)
    4. Execute against DuckDB
    5. Convert to CSV/Parquet bytes
    6. Upload to S3
    7. Update job metadata with file info
    8. Mark job as COMPLETED
    9. Send Telegram notification if user has chat_id

    :param context: Dagster execution context.
    :param config: Export configuration.
    """
    job_id = UUID(config.job_id)
    user_id = UUID(config.user_id)
    dataset_id = UUID(config.dataset_id)

    db = context.resources.postgres_database

    with db.get_session() as session:
        # Mark job as running
        update_job_status(session, job_id, JobStatus.RUNNING)
        context.log.info(f"Starting export: job_id={job_id}, dataset_id={dataset_id}")

    try:
        # Load dataset schema
        dataset = get_dataset_schema(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset not found: {dataset_id}")

        # Parse filter parameters
        start_date_parsed = date.fromisoformat(config.start_date) if config.start_date else None
        end_date_parsed = date.fromisoformat(config.end_date) if config.end_date else None
        account_ids_parsed = (
            [UUID(aid) for aid in config.account_ids] if config.account_ids else None
        )
        tag_ids_parsed = [UUID(tid) for tid in config.tag_ids] if config.tag_ids else None

        # Parse JSON-encoded filters
        enum_filters = json.loads(config.enum_filters_json) if config.enum_filters_json else None
        numeric_filters = (
            json.loads(config.numeric_filters_json) if config.numeric_filters_json else None
        )

        # Build query - use very large limit for exports (effectively unlimited)
        query, params = build_dataset_query(
            dataset=dataset,
            user_id=user_id,
            start_date=start_date_parsed,
            end_date=end_date_parsed,
            account_ids=account_ids_parsed,
            tag_ids=tag_ids_parsed,
            enum_filters=enum_filters,
            numeric_filters=numeric_filters,
            limit=10_000_000,  # Effectively unlimited for exports
            offset=0,
        )

        context.log.info(f"Executing export query for dataset: {dataset.name}")

        # Execute query against DuckDB
        rows = execute_query(query, params, max_rows=10_000_000)
        row_count = len(rows)

        context.log.info(f"Query returned {row_count} rows")

        # Get column names from first row (or dataset schema)
        if rows:
            columns = list(rows[0].keys())
        elif dataset.columns:
            columns = [col.name for col in dataset.columns]
        else:
            columns = []

        # Convert to target format
        if config.file_format == "parquet":
            content = _convert_to_parquet(rows)
        else:
            content = _convert_to_csv(rows, columns)

        file_size = len(content)
        context.log.info(f"Converted to {config.file_format}: {file_size} bytes")

        # Upload to S3
        s3_key = upload_export(
            content, user_id, job_id, config.file_format, dataset_name=dataset.name
        )
        context.log.info(f"Uploaded to S3: {s3_key}")

        # Generate download URL for notification
        download_url = generate_download_url(s3_key)

        # Update job with success metadata
        with db.get_session() as session:
            update_job_status(
                session,
                job_id,
                JobStatus.COMPLETED,
                metadata={
                    "dataset_id": str(dataset_id),
                    "dataset_name": dataset.name,
                    "format": config.file_format,
                    "s3_key": s3_key,
                    "row_count": row_count,
                    "file_size_bytes": file_size,
                    "filters": {
                        "start_date": config.start_date,
                        "end_date": config.end_date,
                        "account_ids": config.account_ids,
                        "tag_ids": config.tag_ids,
                        "enum_filters": enum_filters,
                        "numeric_filters": numeric_filters,
                    },
                },
            )

            # Send Telegram notification
            user = session.get(User, user_id)
            if user:
                _send_telegram_notification(
                    user=user,
                    dataset_name=dataset.friendly_name,
                    row_count=row_count,
                    download_url=download_url,
                )

        context.log.info(f"Export completed: job_id={job_id}, rows={row_count}")

    except Exception as e:
        context.log.error(f"Export failed: {e}")

        # Mark job as failed with user-friendly error message
        with db.get_session() as session:
            update_job_status(
                session,
                job_id,
                JobStatus.FAILED,
                error_message="Export failed. Please try again or contact support.",
            )

        raise
