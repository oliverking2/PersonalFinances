"""Tests for job database operations."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.enums import JobStatus, JobType
from src.postgres.common.models import Job
from src.postgres.common.operations.jobs import (
    create_job,
    get_job_by_id,
    get_jobs_by_user,
    get_latest_job_for_entity,
    update_job_status,
)


class TestCreateJob:
    """Tests for create_job function."""

    def test_creates_job(self, db_session: Session, test_user: User) -> None:
        """Should create a job with correct fields."""
        job = create_job(db_session, test_user.id, JobType.SYNC)
        db_session.commit()

        assert job.id is not None
        assert job.user_id == test_user.id
        assert job.job_type == JobType.SYNC.value
        assert job.status == JobStatus.PENDING.value

    def test_creates_job_with_entity(self, db_session: Session, test_user: User) -> None:
        """Should create a job with entity reference."""
        entity_id = uuid4()
        job = create_job(
            db_session,
            test_user.id,
            JobType.SYNC,
            entity_type="connection",
            entity_id=entity_id,
        )
        db_session.commit()

        assert job.entity_type == "connection"
        assert job.entity_id == entity_id


class TestGetJobById:
    """Tests for get_job_by_id function."""

    def test_returns_job_when_exists(self, db_session: Session, test_user: User) -> None:
        """Should return job when it exists."""
        job = Job(
            user_id=test_user.id,
            job_type=JobType.SYNC.value,
            status=JobStatus.PENDING.value,
            created_at=datetime.now(UTC),
        )
        db_session.add(job)
        db_session.commit()

        result = get_job_by_id(db_session, job.id)

        assert result is not None
        assert result.id == job.id

    def test_returns_none_when_not_found(self, db_session: Session) -> None:
        """Should return None when job not found."""
        result = get_job_by_id(db_session, uuid4())

        assert result is None


class TestUpdateJobStatus:
    """Tests for update_job_status function."""

    def test_updates_status(self, db_session: Session, test_user: User) -> None:
        """Should update job status."""
        job = Job(
            user_id=test_user.id,
            job_type=JobType.SYNC.value,
            status=JobStatus.PENDING.value,
            created_at=datetime.now(UTC),
        )
        db_session.add(job)
        db_session.commit()

        result = update_job_status(db_session, job.id, JobStatus.RUNNING)
        db_session.commit()

        assert result is not None
        assert result.status == JobStatus.RUNNING.value

    def test_sets_started_at_when_running(self, db_session: Session, test_user: User) -> None:
        """Should set started_at when transitioning to RUNNING."""
        job = Job(
            user_id=test_user.id,
            job_type=JobType.SYNC.value,
            status=JobStatus.PENDING.value,
            created_at=datetime.now(UTC),
        )
        db_session.add(job)
        db_session.commit()

        assert job.started_at is None

        result = update_job_status(db_session, job.id, JobStatus.RUNNING)
        db_session.commit()

        assert result is not None
        assert result.started_at is not None

    def test_sets_completed_at_when_completed(self, db_session: Session, test_user: User) -> None:
        """Should set completed_at when transitioning to COMPLETED."""
        job = Job(
            user_id=test_user.id,
            job_type=JobType.SYNC.value,
            status=JobStatus.RUNNING.value,
            started_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db_session.add(job)
        db_session.commit()

        result = update_job_status(db_session, job.id, JobStatus.COMPLETED)
        db_session.commit()

        assert result is not None
        assert result.completed_at is not None

    def test_sets_completed_at_when_failed(self, db_session: Session, test_user: User) -> None:
        """Should set completed_at when transitioning to FAILED."""
        job = Job(
            user_id=test_user.id,
            job_type=JobType.SYNC.value,
            status=JobStatus.RUNNING.value,
            started_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db_session.add(job)
        db_session.commit()

        result = update_job_status(
            db_session,
            job.id,
            JobStatus.FAILED,
            error_message="Something went wrong",
        )
        db_session.commit()

        assert result is not None
        assert result.completed_at is not None
        assert result.error_message == "Something went wrong"

    def test_sets_dagster_run_id(self, db_session: Session, test_user: User) -> None:
        """Should set dagster_run_id when provided."""
        job = Job(
            user_id=test_user.id,
            job_type=JobType.SYNC.value,
            status=JobStatus.PENDING.value,
            created_at=datetime.now(UTC),
        )
        db_session.add(job)
        db_session.commit()

        result = update_job_status(
            db_session,
            job.id,
            JobStatus.RUNNING,
            dagster_run_id="dagster-123",
        )
        db_session.commit()

        assert result is not None
        assert result.dagster_run_id == "dagster-123"

    def test_returns_none_when_not_found(self, db_session: Session) -> None:
        """Should return None when job not found."""
        result = update_job_status(db_session, uuid4(), JobStatus.RUNNING)

        assert result is None


class TestGetLatestJobForEntity:
    """Tests for get_latest_job_for_entity function."""

    def test_returns_most_recent_job(self, db_session: Session, test_user: User) -> None:
        """Should return most recent job for entity."""
        entity_id = uuid4()

        # Create older job
        old_job = Job(
            user_id=test_user.id,
            job_type=JobType.SYNC.value,
            status=JobStatus.COMPLETED.value,
            entity_type="connection",
            entity_id=entity_id,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        db_session.add(old_job)

        # Create newer job
        new_job = Job(
            user_id=test_user.id,
            job_type=JobType.SYNC.value,
            status=JobStatus.RUNNING.value,
            entity_type="connection",
            entity_id=entity_id,
            created_at=datetime(2024, 1, 15, tzinfo=UTC),
        )
        db_session.add(new_job)
        db_session.commit()

        result = get_latest_job_for_entity(db_session, "connection", entity_id)

        assert result is not None
        assert result.id == new_job.id

    def test_filters_by_job_type(self, db_session: Session, test_user: User) -> None:
        """Should filter by job type when provided."""
        entity_id = uuid4()

        job = Job(
            user_id=test_user.id,
            job_type=JobType.SYNC.value,
            status=JobStatus.COMPLETED.value,
            entity_type="connection",
            entity_id=entity_id,
            created_at=datetime.now(UTC),
        )
        db_session.add(job)
        db_session.commit()

        # Should find with matching type
        result = get_latest_job_for_entity(
            db_session, "connection", entity_id, job_type=JobType.SYNC
        )
        assert result is not None

        # Should not find with non-matching type
        result = get_latest_job_for_entity(
            db_session, "connection", entity_id, job_type=JobType.EXPORT
        )
        assert result is None

    def test_returns_none_when_no_jobs(self, db_session: Session) -> None:
        """Should return None when no jobs exist for entity."""
        result = get_latest_job_for_entity(db_session, "connection", uuid4())

        assert result is None


class TestGetJobsByUser:
    """Tests for get_jobs_by_user function."""

    def test_returns_jobs_for_user(self, db_session: Session, test_user: User) -> None:
        """Should return jobs for the user."""
        job = Job(
            user_id=test_user.id,
            job_type=JobType.SYNC.value,
            status=JobStatus.COMPLETED.value,
            created_at=datetime.now(UTC),
        )
        db_session.add(job)
        db_session.commit()

        result = get_jobs_by_user(db_session, test_user.id)

        assert len(result) == 1
        assert result[0].id == job.id

    def test_filters_by_job_type(self, db_session: Session, test_user: User) -> None:
        """Should filter by job type."""
        sync_job = Job(
            user_id=test_user.id,
            job_type=JobType.SYNC.value,
            status=JobStatus.COMPLETED.value,
            created_at=datetime.now(UTC),
        )
        db_session.add(sync_job)
        db_session.commit()

        result = get_jobs_by_user(db_session, test_user.id, job_type=JobType.SYNC)
        assert len(result) == 1

        result = get_jobs_by_user(db_session, test_user.id, job_type=JobType.EXPORT)
        assert len(result) == 0

    def test_filters_by_entity_type(self, db_session: Session, test_user: User) -> None:
        """Should filter by entity type."""
        job = Job(
            user_id=test_user.id,
            job_type=JobType.SYNC.value,
            status=JobStatus.COMPLETED.value,
            entity_type="connection",
            entity_id=uuid4(),
            created_at=datetime.now(UTC),
        )
        db_session.add(job)
        db_session.commit()

        result = get_jobs_by_user(db_session, test_user.id, entity_type="connection")
        assert len(result) == 1

        result = get_jobs_by_user(db_session, test_user.id, entity_type="account")
        assert len(result) == 0

    def test_filters_by_entity_id(self, db_session: Session, test_user: User) -> None:
        """Should filter by entity ID."""
        entity_id = uuid4()
        job = Job(
            user_id=test_user.id,
            job_type=JobType.SYNC.value,
            status=JobStatus.COMPLETED.value,
            entity_type="connection",
            entity_id=entity_id,
            created_at=datetime.now(UTC),
        )
        db_session.add(job)
        db_session.commit()

        result = get_jobs_by_user(db_session, test_user.id, entity_id=entity_id)
        assert len(result) == 1

        result = get_jobs_by_user(db_session, test_user.id, entity_id=uuid4())
        assert len(result) == 0

    def test_respects_limit(self, db_session: Session, test_user: User) -> None:
        """Should respect limit parameter."""
        for _ in range(5):
            job = Job(
                user_id=test_user.id,
                job_type=JobType.SYNC.value,
                status=JobStatus.COMPLETED.value,
                created_at=datetime.now(UTC),
            )
            db_session.add(job)
        db_session.commit()

        result = get_jobs_by_user(db_session, test_user.id, limit=2)

        assert len(result) == 2

    def test_returns_empty_for_other_user(self, db_session: Session, test_user: User) -> None:
        """Should return empty list for user with no jobs."""
        job = Job(
            user_id=test_user.id,
            job_type=JobType.SYNC.value,
            status=JobStatus.COMPLETED.value,
            created_at=datetime.now(UTC),
        )
        db_session.add(job)
        db_session.commit()

        result = get_jobs_by_user(db_session, uuid4())

        assert len(result) == 0
