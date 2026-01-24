"""Jobs API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
from src.api.jobs.models import JobListResponse, JobResponse
from src.postgres.auth.models import User
from src.postgres.common.enums import JobStatus, JobType
from src.postgres.common.models import Job
from src.postgres.common.operations.jobs import (
    get_job_by_id,
    get_jobs_by_user,
    update_job_status,
)
from src.providers.dagster import get_run_status

logger = logging.getLogger(__name__)

router = APIRouter()


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


@router.get("/{job_id}", response_model=JobResponse, summary="Get job by ID")
def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobResponse:
    """Get a specific job by ID.

    If the job is still running, this endpoint will check Dagster for the
    actual status and update the job record accordingly.

    :param job_id: Job UUID to retrieve.
    :param db: Database session.
    :param current_user: Authenticated user.
    :returns: Job details.
    :raises HTTPException: If job not found or not owned by user.
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
            db.commit()
            db.refresh(job)
            logger.info(f"Job {job_id} completed (Dagster status: SUCCESS)")
        elif dagster_status in ("FAILURE", "CANCELED"):
            update_job_status(
                db,
                job.id,
                JobStatus.FAILED,
                error_message=f"Dagster run {dagster_status.lower()}",
            )
            db.commit()
            db.refresh(job)
            logger.info(f"Job {job_id} failed (Dagster status: {dagster_status})")

    return _to_response(job)


@router.get("", response_model=JobListResponse, summary="List jobs")
def list_jobs(  # noqa: PLR0913
    entity_type: str | None = Query(None, description="Filter by entity type"),
    entity_id: UUID | None = Query(None, description="Filter by entity ID"),
    job_type: JobType | None = Query(None, description="Filter by job type"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of jobs to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobListResponse:
    """List jobs for the authenticated user.

    :param entity_type: Optional filter by entity type (e.g., 'connection').
    :param entity_id: Optional filter by entity ID.
    :param job_type: Optional filter by job type.
    :param limit: Maximum number of jobs to return.
    :param db: Database session.
    :param current_user: Authenticated user.
    :returns: List of jobs.
    """
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
