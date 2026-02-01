"""Jobs API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
from src.api.jobs.models import JobListResponse, JobResponse
from src.api.responses import RESOURCE_RESPONSES, UNAUTHORIZED
from src.postgres.auth.models import User
from src.postgres.common.enums import JobStatus, JobType, NotificationType
from src.postgres.common.models import Connection, Job
from src.postgres.common.operations.jobs import (
    get_job_by_id,
    get_jobs_by_user,
    update_job_status,
)
from src.postgres.common.operations.notifications import create_notification
from src.providers.dagster import get_run_status

logger = logging.getLogger(__name__)

router = APIRouter()


def _create_sync_notification(
    db: Session,
    job: Job,
    *,
    success: bool,
    error_message: str | None = None,
) -> None:
    """Create a notification for sync job completion/failure.

    :param db: Database session.
    :param job: Job entity.
    :param success: Whether the sync succeeded.
    :param error_message: Error message if sync failed.
    """
    # Handle analytics refresh separately with its own notification types
    if job.entity_type == "analytics":
        redirect_to = job.job_metadata.get("redirect_to", "/insights/analytics")
        if success:
            create_notification(
                db,
                job.user_id,
                NotificationType.ANALYTICS_REFRESH_COMPLETE,
                title="Analytics Refreshed",
                message="Your analytics data has been updated.",
                metadata={
                    "job_id": str(job.id),
                    "redirect_to": redirect_to,
                },
            )
        else:
            create_notification(
                db,
                job.user_id,
                NotificationType.ANALYTICS_REFRESH_FAILED,
                title="Analytics Refresh Failed",
                message="Failed to refresh analytics data. Please try again.",
                metadata={
                    "job_id": str(job.id),
                    "redirect_to": redirect_to,
                    "error_message": error_message,
                },
            )
        return

    # Handle bank sync notifications
    entity_name = "data"
    if job.entity_type == "connection" and job.entity_id:
        connection = db.get(Connection, job.entity_id)
        if connection:
            entity_name = connection.friendly_name

    if success:
        create_notification(
            db,
            job.user_id,
            NotificationType.SYNC_COMPLETE,
            title="Sync Complete",
            message=f"Your {entity_name} sync completed successfully.",
            metadata={
                "job_id": str(job.id),
                "connection_name": entity_name,
            },
        )
    else:
        create_notification(
            db,
            job.user_id,
            NotificationType.SYNC_FAILED,
            title="Sync Failed",
            message=f"Your {entity_name} sync failed. Please try again.",
            metadata={
                "job_id": str(job.id),
                "connection_name": entity_name,
                "error_message": error_message,
            },
        )


def _to_response(job: Job) -> JobResponse:
    """Convert a Job model to response."""
    return JobResponse(
        id=str(job.id),
        job_type=JobType(job.job_type),
        status=JobStatus(job.status),
        entity_type=job.entity_type,
        entity_id=str(job.entity_id) if job.entity_id else None,
        dagster_run_id=job.dagster_run_id,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job by ID",
    responses=RESOURCE_RESPONSES,
)
def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobResponse:
    """Retrieve a specific job by its UUID.

    If the job is still running, checks Dagster for the actual status and
    updates the job record accordingly.
    """
    job = get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    if job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # If still running, check Dagster for actual status
    if job.status == JobStatus.RUNNING.value and job.dagster_run_id:
        dagster_status = get_run_status(job.dagster_run_id)
        if dagster_status == "SUCCESS":
            update_job_status(db, job.id, JobStatus.COMPLETED)

            # Create sync complete notification for sync jobs
            if job.job_type == JobType.SYNC.value:
                _create_sync_notification(db, job, success=True)

            db.commit()
            db.refresh(job)
            logger.info(f"Job {job_id} completed (Dagster status: SUCCESS)")
        elif dagster_status in ("FAILURE", "CANCELED"):
            error_msg = f"Job {dagster_status.lower()}"
            update_job_status(
                db,
                job.id,
                JobStatus.FAILED,
                error_message=error_msg,
            )

            # Create sync failed notification for sync jobs
            if job.job_type == JobType.SYNC.value:
                _create_sync_notification(db, job, success=False, error_message=error_msg)

            db.commit()
            db.refresh(job)
            logger.info(f"Job {job_id} failed (Dagster status: {dagster_status})")

    return _to_response(job)


@router.get(
    "",
    response_model=JobListResponse,
    summary="List jobs",
    responses=UNAUTHORIZED,
)
def list_jobs(
    entity_type: str | None = Query(None, description="Filter by entity type"),
    entity_id: UUID | None = Query(None, description="Filter by entity ID"),
    job_type: JobType | None = Query(None, description="Filter by job type"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of jobs to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobListResponse:
    """List jobs for the authenticated user with optional filters."""
    jobs = get_jobs_by_user(
        db,
        user_id=current_user.id,
        job_type=job_type,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )

    return JobListResponse(
        jobs=[_to_response(job) for job in jobs],
        total=len(jobs),
    )
