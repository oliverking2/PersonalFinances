"""Analytics export endpoints.

Provides endpoints for creating and monitoring dataset exports.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
from src.api.responses import BAD_REQUEST, RESOURCE_RESPONSES, UNAUTHORIZED
from src.duckdb.manifest import get_dataset_schema
from src.postgres.auth.models import User
from src.postgres.common.enums import JobStatus, JobType
from src.postgres.common.operations.connections import get_connections_by_user_id
from src.postgres.common.operations.jobs import create_job, get_job_by_id, get_jobs_by_user
from src.postgres.common.operations.tags import get_tags_by_user_id
from src.providers.dagster import build_export_run_config, trigger_job
from src.providers.dagster.client import DATASET_EXPORT_JOB
from src.providers.s3 import generate_download_url

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class EnumFilterRequest(BaseModel):
    """A single enum filter with selected values."""

    column: str = Field(..., description="Column name to filter")
    values: list[str] = Field(..., description="Selected values to include")


class NumericFilterRequest(BaseModel):
    """A single numeric filter with min/max range."""

    column: str = Field(..., description="Column name to filter")
    min: float | None = Field(None, description="Minimum value (inclusive)")
    max: float | None = Field(None, description="Maximum value (inclusive)")


class CreateExportRequest(BaseModel):
    """Request to create a dataset export."""

    dataset_id: UUID = Field(..., description="Dataset UUID to export")
    format: Literal["csv", "parquet"] = Field("csv", description="Export format")
    start_date: str | None = Field(None, description="Start date filter (ISO format)")
    end_date: str | None = Field(None, description="End date filter (ISO format)")
    account_ids: list[UUID] | None = Field(None, description="Filter by account IDs")
    tag_ids: list[UUID] | None = Field(None, description="Filter by tag IDs")
    enum_filters: list[EnumFilterRequest] | None = Field(None, description="Enum column filters")
    numeric_filters: list[NumericFilterRequest] | None = Field(
        None, description="Numeric column filters"
    )


class CreateExportResponse(BaseModel):
    """Response after creating an export job."""

    job_id: UUID = Field(..., description="Job UUID for tracking")
    status: str = Field(..., description="Job status (pending, running, failed)")
    message: str = Field(..., description="Status message")


class ExportStatusResponse(BaseModel):
    """Response for export status with download URL."""

    job_id: UUID = Field(..., description="Job UUID")
    status: str = Field(..., description="Job status")
    dataset_id: UUID | None = Field(None, description="Dataset UUID")
    dataset_name: str | None = Field(None, description="Dataset name")
    format: str | None = Field(None, description="Export format")
    row_count: int | None = Field(None, description="Number of rows exported")
    file_size_bytes: int | None = Field(None, description="File size in bytes")
    download_url: str | None = Field(None, description="Pre-signed download URL (1 hour expiry)")
    expires_at: datetime | None = Field(None, description="When the download URL expires")
    error_message: str | None = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Job creation time")
    completed_at: datetime | None = Field(None, description="Job completion time")


class ExportListItem(BaseModel):
    """A single export in the list response."""

    job_id: UUID = Field(..., description="Job UUID")
    status: str = Field(..., description="Job status (pending, running, completed, failed)")
    dataset_id: UUID | None = Field(None, description="Dataset UUID")
    dataset_name: str | None = Field(None, description="Dataset name")
    format: str | None = Field(None, description="Export format (csv, parquet)")
    row_count: int | None = Field(None, description="Number of rows exported")
    file_size_bytes: int | None = Field(None, description="File size in bytes")
    error_message: str | None = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Job creation time")
    completed_at: datetime | None = Field(None, description="Job completion time")
    filters: dict[str, Any] | None = Field(None, description="Filters applied to export")


class ExportListResponse(BaseModel):
    """Response for listing export jobs."""

    exports: list[ExportListItem] = Field(..., description="List of exports")
    total: int = Field(..., description="Total count")


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _validate_account_ids(db: Session, user: User, account_ids: list[UUID]) -> list[UUID]:
    """Validate and filter account IDs to those owned by the user.

    :param db: Database session.
    :param user: Authenticated user.
    :param account_ids: Requested account IDs.
    :returns: Valid account IDs owned by user.
    """
    connections = get_connections_by_user_id(db, user.id)
    user_account_ids = {acc.id for conn in connections for acc in conn.accounts}
    return [aid for aid in account_ids if aid in user_account_ids]


def _validate_tag_ids(db: Session, user: User, tag_ids: list[UUID]) -> list[UUID]:
    """Validate and filter tag IDs to those owned by the user.

    :param db: Database session.
    :param user: Authenticated user.
    :param tag_ids: Requested tag IDs.
    :returns: Valid tag IDs owned by user.
    """
    user_tags = get_tags_by_user_id(db, user.id)
    user_tag_ids = {tag.id for tag in user_tags}
    return [tid for tid in tag_ids if tid in user_tag_ids]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/exports",
    response_model=ExportListResponse,
    summary="List export jobs",
    responses=UNAUTHORIZED,
)
def list_exports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExportListResponse:
    """List all export jobs for the current user, newest first."""
    jobs = get_jobs_by_user(
        db,
        user_id=current_user.id,
        job_type=JobType.EXPORT,
        limit=50,
    )

    exports = []
    for job in jobs:
        meta = job.job_metadata or {}
        dataset_id_str = meta.get("dataset_id")
        exports.append(
            ExportListItem(
                job_id=job.id,
                status=job.status,
                dataset_id=UUID(dataset_id_str) if dataset_id_str else None,
                dataset_name=meta.get("dataset_name"),
                format=meta.get("format"),
                row_count=meta.get("row_count"),
                file_size_bytes=meta.get("file_size_bytes"),
                error_message=job.error_message,
                created_at=job.created_at,
                completed_at=job.completed_at,
                filters=meta.get("filters"),
            )
        )

    return ExportListResponse(exports=exports, total=len(exports))


@router.post(
    "/exports",
    response_model=CreateExportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create dataset export",
    responses={**UNAUTHORIZED, **BAD_REQUEST},
)
def create_export(
    request: CreateExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreateExportResponse:
    """Create an async export job for a dataset.

    The job runs in Dagster and uploads the export to S3. Use GET /exports/{job_id}
    to check status and get the download URL when complete.
    """
    # Validate dataset exists
    dataset = get_dataset_schema(request.dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dataset not found: {request.dataset_id}",
        )

    # Validate filter IDs belong to user
    valid_account_ids: list[str] | None = None
    valid_tag_ids: list[str] | None = None

    if request.account_ids:
        validated = _validate_account_ids(db, current_user, request.account_ids)
        if not validated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid account IDs provided",
            )
        valid_account_ids = [str(aid) for aid in validated]

    if request.tag_ids:
        validated = _validate_tag_ids(db, current_user, request.tag_ids)
        if not validated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid tag IDs provided",
            )
        valid_tag_ids = [str(tid) for tid in validated]

    # Convert filter requests to serializable format
    enum_filters_data: list[dict[str, Any]] | None = None
    numeric_filters_data: list[dict[str, Any]] | None = None

    if request.enum_filters:
        enum_filters_data = [{"column": f.column, "values": f.values} for f in request.enum_filters]

    if request.numeric_filters:
        numeric_filters_data = [
            {"column": f.column, "min": f.min, "max": f.max} for f in request.numeric_filters
        ]

    # Create job record with initial metadata
    job = create_job(
        session=db,
        user_id=current_user.id,
        job_type=JobType.EXPORT,
        entity_type="dataset",
        entity_id=request.dataset_id,
        metadata={
            "dataset_id": str(request.dataset_id),
            "dataset_name": dataset.name,
            "format": request.format,
            "filters": {
                "start_date": request.start_date,
                "end_date": request.end_date,
                "account_ids": valid_account_ids,
                "tag_ids": valid_tag_ids,
                "enum_filters": enum_filters_data,
                "numeric_filters": numeric_filters_data,
            },
        },
    )

    # Build Dagster run config
    run_config = build_export_run_config(
        job_id=str(job.id),
        user_id=str(current_user.id),
        dataset_id=str(request.dataset_id),
        file_format=request.format,
        start_date=request.start_date,
        end_date=request.end_date,
        account_ids=valid_account_ids,
        tag_ids=valid_tag_ids,
        enum_filters=enum_filters_data,
        numeric_filters=numeric_filters_data,
    )

    # Trigger Dagster job
    run_id = trigger_job(DATASET_EXPORT_JOB, run_config)

    if run_id:
        job.dagster_run_id = run_id
        job.status = JobStatus.PENDING.value
        message = "Export job created and queued"
        logger.info(f"Export job created: job_id={job.id}, run_id={run_id}")
    else:
        job.status = JobStatus.FAILED.value
        job.error_message = "Job runner unavailable"
        message = "Failed to create export - Job runner unavailable"
        logger.warning(f"Export job failed to trigger: job_id={job.id}")

    db.commit()

    return CreateExportResponse(
        job_id=job.id,
        status=job.status,
        message=message,
    )


@router.get(
    "/exports/{job_id}",
    response_model=ExportStatusResponse,
    summary="Get export status",
    responses=RESOURCE_RESPONSES,
)
def get_export_status(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExportStatusResponse:
    """Get export job status and download URL if complete.

    Returns a pre-signed S3 URL (1 hour expiry) when the export is complete.
    The URL is regenerated on each request.
    """
    job = get_job_by_id(db, job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Export job not found: {job_id}")

    # Verify ownership
    if job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Export job not found: {job_id}")

    # Verify it's an export job
    if job.job_type != JobType.EXPORT.value:
        raise HTTPException(status_code=404, detail=f"Export job not found: {job_id}")

    # Extract metadata
    metadata = job.job_metadata or {}
    dataset_id = metadata.get("dataset_id")
    dataset_name = metadata.get("dataset_name")
    file_format = metadata.get("format")
    row_count = metadata.get("row_count")
    file_size_bytes = metadata.get("file_size_bytes")
    s3_key = metadata.get("s3_key")

    # Generate download URL if complete
    download_url: str | None = None
    expires_at: datetime | None = None

    if job.status == JobStatus.COMPLETED.value and s3_key:
        try:
            download_url = generate_download_url(s3_key, expires_in=3600)
            expires_at = datetime.now(UTC) + timedelta(hours=1)
        except Exception as e:
            logger.error(f"Failed to generate download URL: {e}")
            # Don't fail the request, just omit the URL

    return ExportStatusResponse(
        job_id=job.id,
        status=job.status,
        dataset_id=UUID(dataset_id) if dataset_id else None,
        dataset_name=dataset_name,
        format=file_format,
        row_count=row_count,
        file_size_bytes=file_size_bytes,
        download_url=download_url,
        expires_at=expires_at,
        error_message=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )
