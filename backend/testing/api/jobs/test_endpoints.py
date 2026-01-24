"""Tests for jobs API endpoints."""

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.enums import JobStatus, JobType
from src.postgres.common.models import Job


@pytest.fixture
def test_job_in_db(api_db_session: Session, test_user_in_db: User) -> Job:
    """Create a completed job in the database."""
    job = Job(
        job_type=JobType.SYNC.value,
        status=JobStatus.COMPLETED.value,
        user_id=test_user_in_db.id,
        entity_type="connection",
        entity_id=uuid4(),
        dagster_run_id="dagster-run-123",
        created_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    api_db_session.add(job)
    api_db_session.commit()
    return job


@pytest.fixture
def test_running_job_in_db(api_db_session: Session, test_user_in_db: User) -> Job:
    """Create a running job in the database."""
    job = Job(
        job_type=JobType.SYNC.value,
        status=JobStatus.RUNNING.value,
        user_id=test_user_in_db.id,
        entity_type="connection",
        entity_id=uuid4(),
        dagster_run_id="dagster-run-456",
        created_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
    )
    api_db_session.add(job)
    api_db_session.commit()
    return job


@pytest.fixture
def test_jobs_in_db(api_db_session: Session, test_user_in_db: User) -> list[Job]:
    """Create multiple jobs in the database."""
    connection_id = uuid4()
    jobs = [
        Job(
            job_type=JobType.SYNC.value,
            status=JobStatus.COMPLETED.value,
            user_id=test_user_in_db.id,
            entity_type="connection",
            entity_id=connection_id,
            created_at=datetime.now(UTC),
        ),
        Job(
            job_type=JobType.SYNC.value,
            status=JobStatus.RUNNING.value,
            user_id=test_user_in_db.id,
            entity_type="connection",
            entity_id=connection_id,
            created_at=datetime.now(UTC),
        ),
        Job(
            job_type=JobType.SYNC.value,
            status=JobStatus.PENDING.value,
            user_id=test_user_in_db.id,
            entity_type="connection",
            entity_id=uuid4(),  # Different entity
            created_at=datetime.now(UTC),
        ),
    ]
    for job in jobs:
        api_db_session.add(job)
    api_db_session.commit()
    return jobs


class TestGetJob:
    """Tests for GET /api/jobs/{job_id} endpoint."""

    def test_returns_job(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_job_in_db: Job,
    ) -> None:
        """Should return job details."""
        response = client.get(f"/api/jobs/{test_job_in_db.id}", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_job_in_db.id)
        assert data["job_type"] == JobType.SYNC.value
        assert data["status"] == JobStatus.COMPLETED.value
        assert data["entity_type"] == "connection"

    def test_returns_404_for_nonexistent_job(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for nonexistent job."""
        response = client.get(f"/api/jobs/{uuid4()}", headers=api_auth_headers)

        assert response.status_code == 404

    def test_returns_404_for_other_users_job(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        api_db_session: Session,
    ) -> None:
        """Should return 404 for job owned by another user."""
        other_user = User(
            username="otheruser",
            password_hash="hash",
            first_name="Other",
            last_name="User",
        )
        api_db_session.add(other_user)
        api_db_session.flush()

        job = Job(
            job_type=JobType.SYNC.value,
            status=JobStatus.COMPLETED.value,
            user_id=other_user.id,
            created_at=datetime.now(UTC),
        )
        api_db_session.add(job)
        api_db_session.commit()

        response = client.get(f"/api/jobs/{job.id}", headers=api_auth_headers)

        assert response.status_code == 404

    def test_returns_401_without_auth(
        self,
        client: TestClient,
        test_job_in_db: Job,
    ) -> None:
        """Should return 401 without authentication."""
        response = client.get(f"/api/jobs/{test_job_in_db.id}")

        assert response.status_code == 401

    @patch("src.api.jobs.endpoints.get_run_status")
    def test_updates_running_job_when_dagster_completes(
        self,
        mock_get_run_status: patch,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_running_job_in_db: Job,
    ) -> None:
        """Should update job status when Dagster reports completion."""
        mock_get_run_status.return_value = "SUCCESS"

        response = client.get(
            f"/api/jobs/{test_running_job_in_db.id}",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == JobStatus.COMPLETED.value

    @patch("src.api.jobs.endpoints.get_run_status")
    def test_updates_running_job_when_dagster_fails(
        self,
        mock_get_run_status: patch,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_running_job_in_db: Job,
    ) -> None:
        """Should update job status when Dagster reports failure."""
        mock_get_run_status.return_value = "FAILURE"

        response = client.get(
            f"/api/jobs/{test_running_job_in_db.id}",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == JobStatus.FAILED.value
        assert "failure" in data["error_message"].lower()


class TestListJobs:
    """Tests for GET /api/jobs endpoint."""

    def test_returns_jobs_for_user(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_jobs_in_db: list[Job],
    ) -> None:
        """Should return jobs for authenticated user."""
        response = client.get("/api/jobs", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["jobs"]) == 3

    def test_returns_empty_list_for_user_with_no_jobs(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return empty list when user has no jobs."""
        response = client.get("/api/jobs", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["jobs"] == []

    def test_filters_by_entity_type(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_jobs_in_db: list[Job],
    ) -> None:
        """Should filter jobs by entity_type."""
        response = client.get(
            "/api/jobs?entity_type=connection",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert all(j["entity_type"] == "connection" for j in data["jobs"])

    def test_filters_by_entity_id(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_jobs_in_db: list[Job],
    ) -> None:
        """Should filter jobs by entity_id."""
        entity_id = test_jobs_in_db[0].entity_id
        response = client.get(
            f"/api/jobs?entity_id={entity_id}",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # First two jobs have the same entity_id
        assert data["total"] == 2

    def test_filters_by_job_type(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_jobs_in_db: list[Job],
    ) -> None:
        """Should filter jobs by job_type."""
        response = client.get(
            "/api/jobs?job_type=sync",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert all(j["job_type"] == JobType.SYNC.value for j in data["jobs"])

    def test_respects_limit(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_jobs_in_db: list[Job],
    ) -> None:
        """Should respect limit parameter."""
        response = client.get("/api/jobs?limit=2", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 2

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Should return 401 without authentication."""
        response = client.get("/api/jobs")

        assert response.status_code == 401
