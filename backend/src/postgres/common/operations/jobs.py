"""Job database operations.

This module provides CRUD operations for Job entities.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.postgres.common.enums import JobStatus, JobType
from src.postgres.common.models import Job

logger = logging.getLogger(__name__)


def create_job(
    session: Session,
    user_id: UUID,
    job_type: JobType,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
) -> Job:
    """Create a new job.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID who initiated the job.
    :param job_type: Type of job (sync, export, etc.).
    :param entity_type: Type of entity this job relates to (optional).
    :param entity_id: ID of the related entity (optional).
    :returns: Created Job entity.
    """
    job = Job(
        user_id=user_id,
        job_type=job_type.value,
        status=JobStatus.PENDING.value,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    session.add(job)
    session.flush()
    logger.info(
        f"Created job: id={job.id}, type={job_type.value}, user_id={user_id}, "
        f"entity_type={entity_type}, entity_id={entity_id}"
    )
    return job


def get_job_by_id(session: Session, job_id: UUID) -> Job | None:
    """Get a job by its ID.

    :param session: SQLAlchemy session.
    :param job_id: Job's UUID.
    :returns: Job if found, None otherwise.
    """
    return session.get(Job, job_id)


def update_job_status(
    session: Session,
    job_id: UUID,
    status: JobStatus,
    dagster_run_id: str | None = None,
    error_message: str | None = None,
) -> Job | None:
    """Update a job's status.

    :param session: SQLAlchemy session.
    :param job_id: Job's UUID.
    :param status: New status.
    :param dagster_run_id: Dagster run ID (optional, set when job starts).
    :param error_message: Error message (optional, set when job fails).
    :returns: Updated Job, or None if not found.
    """
    job = get_job_by_id(session, job_id)
    if job is None:
        return None

    job.status = status.value

    if dagster_run_id is not None:
        job.dagster_run_id = dagster_run_id

    if error_message is not None:
        job.error_message = error_message

    # Update timestamps based on status
    now = datetime.now(UTC)
    if status == JobStatus.RUNNING and job.started_at is None:
        job.started_at = now
    elif status in (JobStatus.COMPLETED, JobStatus.FAILED):
        job.completed_at = now
        if job.started_at is None:
            job.started_at = now

    session.flush()
    logger.info(f"Updated job status: id={job_id}, status={status.value}")
    return job


def get_latest_job_for_entity(
    session: Session,
    entity_type: str,
    entity_id: UUID,
    job_type: JobType | None = None,
) -> Job | None:
    """Get the most recent job for a specific entity.

    :param session: SQLAlchemy session.
    :param entity_type: Type of entity (e.g., 'connection').
    :param entity_id: Entity's UUID.
    :param job_type: Filter by job type (optional).
    :returns: Most recent Job if found, None otherwise.
    """
    query = session.query(Job).filter(
        Job.entity_type == entity_type,
        Job.entity_id == entity_id,
    )

    if job_type is not None:
        query = query.filter(Job.job_type == job_type.value)

    return query.order_by(desc(Job.created_at)).first()


def get_jobs_by_user(
    session: Session,
    user_id: UUID,
    job_type: JobType | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    limit: int = 20,
) -> list[Job]:
    """Get jobs for a user with optional filters.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param job_type: Filter by job type (optional).
    :param entity_type: Filter by entity type (optional).
    :param entity_id: Filter by entity ID (optional).
    :param limit: Maximum number of jobs to return.
    :returns: List of jobs, ordered by creation date descending.
    """
    query = session.query(Job).filter(Job.user_id == user_id)

    if job_type is not None:
        query = query.filter(Job.job_type == job_type.value)

    if entity_type is not None:
        query = query.filter(Job.entity_type == entity_type)

    if entity_id is not None:
        query = query.filter(Job.entity_id == entity_id)

    return query.order_by(desc(Job.created_at)).limit(limit).all()
