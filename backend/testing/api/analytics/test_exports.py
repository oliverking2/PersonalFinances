"""Tests for analytics export API endpoints."""

import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.duckdb.manifest import DATASET_UUID_NAMESPACE, Dataset
from src.postgres.auth.models import User
from src.postgres.common.enums import (
    AccountStatus,
    ConnectionStatus,
    JobStatus,
    JobType,
    Provider,
)
from src.postgres.common.models import Account, Connection, Institution, Job, Tag


def _dataset_uuid(name: str) -> uuid.UUID:
    """Generate deterministic UUID for a dataset name."""
    return uuid.uuid5(DATASET_UUID_NAMESPACE, name)


@pytest.fixture
def test_institution_in_db(api_db_session: Session) -> Institution:
    """Create an institution in the database."""
    institution = Institution(
        id="TEST_INSTITUTION",
        provider=Provider.GOCARDLESS.value,
        name="Test Bank",
        logo_url="https://example.com/logo.png",
        countries=["GB"],
    )
    api_db_session.add(institution)
    api_db_session.commit()
    return institution


@pytest.fixture
def test_connection_in_db(
    api_db_session: Session, test_user_in_db: User, test_institution_in_db: Institution
) -> Connection:
    """Create a connection in the database."""
    connection = Connection(
        user_id=test_user_in_db.id,
        provider=Provider.GOCARDLESS.value,
        provider_id="test-req-id-export",
        institution_id=test_institution_in_db.id,
        friendly_name="Test Connection",
        status=ConnectionStatus.ACTIVE.value,
        created_at=datetime.now(),
    )
    api_db_session.add(connection)
    api_db_session.commit()
    return connection


@pytest.fixture
def test_account_in_db(api_db_session: Session, test_connection_in_db: Connection) -> Account:
    """Create an account in the database."""
    account = Account(
        connection_id=test_connection_in_db.id,
        provider_id="test-gc-account-id-export",
        status=AccountStatus.ACTIVE.value,
        name="Test Account",
        display_name="My Account",
        iban="GB00TEST00000000001234",
        currency="GBP",
        balance_amount=Decimal("1000.00"),
        balance_currency="GBP",
    )
    api_db_session.add(account)
    api_db_session.commit()
    return account


@pytest.fixture
def test_tag_in_db(api_db_session: Session, test_user_in_db: User) -> Tag:
    """Create a tag in the database."""
    tag = Tag(
        user_id=test_user_in_db.id,
        name="TestTag",
        colour="#FF0000",
    )
    api_db_session.add(tag)
    api_db_session.commit()
    return tag


@pytest.fixture
def mock_dataset() -> Dataset:
    """Create a mock dataset."""
    return Dataset(
        id=_dataset_uuid("fct_transactions"),
        name="fct_transactions",
        friendly_name="Transactions",
        description="Transaction data",
        group="facts",
    )


@pytest.fixture
def test_export_job_in_db(api_db_session: Session, test_user_in_db: User) -> Job:
    """Create an export job in the database."""
    job = Job(
        user_id=test_user_in_db.id,
        job_type=JobType.EXPORT.value,
        status=JobStatus.COMPLETED.value,
        entity_type="dataset",
        entity_id=_dataset_uuid("fct_transactions"),
        job_metadata={
            "dataset_id": str(_dataset_uuid("fct_transactions")),
            "dataset_name": "fct_transactions",
            "format": "csv",
            "s3_key": "exports/user-id/job-id.csv",
            "row_count": 100,
            "file_size_bytes": 5000,
        },
    )
    api_db_session.add(job)
    api_db_session.commit()
    return job


class TestCreateExport:
    """Tests for POST /api/analytics/exports endpoint."""

    def test_creates_export_job(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        mock_dataset: Dataset,
    ) -> None:
        """Should create export job and trigger Dagster."""
        with (
            patch("src.api.analytics.exports.get_dataset_schema") as mock_schema,
            patch("src.api.analytics.exports.trigger_job") as mock_trigger,
        ):
            mock_schema.return_value = mock_dataset
            mock_trigger.return_value = "test-dagster-run-id"

            response = client.post(
                "/api/analytics/exports",
                json={
                    "dataset_id": str(mock_dataset.id),
                    "format": "csv",
                },
                headers=api_auth_headers,
            )

            assert response.status_code == 202
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "pending"
            assert "created" in data["message"].lower()

    def test_creates_export_with_filters(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        mock_dataset: Dataset,
        test_account_in_db: Account,
        test_tag_in_db: Tag,
    ) -> None:
        """Should create export job with filters."""
        with (
            patch("src.api.analytics.exports.get_dataset_schema") as mock_schema,
            patch("src.api.analytics.exports.trigger_job") as mock_trigger,
        ):
            mock_schema.return_value = mock_dataset
            mock_trigger.return_value = "test-dagster-run-id"

            response = client.post(
                "/api/analytics/exports",
                json={
                    "dataset_id": str(mock_dataset.id),
                    "format": "parquet",
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31",
                    "account_ids": [str(test_account_in_db.id)],
                    "tag_ids": [str(test_tag_in_db.id)],
                },
                headers=api_auth_headers,
            )

            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "pending"

    def test_returns_400_for_invalid_dataset(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 400 for non-existent dataset."""
        with patch("src.api.analytics.exports.get_dataset_schema") as mock_schema:
            mock_schema.return_value = None

            response = client.post(
                "/api/analytics/exports",
                json={
                    "dataset_id": str(uuid4()),
                    "format": "csv",
                },
                headers=api_auth_headers,
            )

            assert response.status_code == 400
            assert "not found" in response.json()["detail"].lower()

    def test_returns_400_for_invalid_account_ids(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        mock_dataset: Dataset,
    ) -> None:
        """Should return 400 if no valid account IDs provided."""
        with patch("src.api.analytics.exports.get_dataset_schema") as mock_schema:
            mock_schema.return_value = mock_dataset

            response = client.post(
                "/api/analytics/exports",
                json={
                    "dataset_id": str(mock_dataset.id),
                    "format": "csv",
                    "account_ids": [str(uuid4())],  # Invalid account ID
                },
                headers=api_auth_headers,
            )

            assert response.status_code == 400
            assert "account" in response.json()["detail"].lower()

    def test_returns_400_for_invalid_tag_ids(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        mock_dataset: Dataset,
    ) -> None:
        """Should return 400 if no valid tag IDs provided."""
        with patch("src.api.analytics.exports.get_dataset_schema") as mock_schema:
            mock_schema.return_value = mock_dataset

            response = client.post(
                "/api/analytics/exports",
                json={
                    "dataset_id": str(mock_dataset.id),
                    "format": "csv",
                    "tag_ids": [str(uuid4())],  # Invalid tag ID
                },
                headers=api_auth_headers,
            )

            assert response.status_code == 400
            assert "tag" in response.json()["detail"].lower()

    def test_handles_dagster_unavailable(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        mock_dataset: Dataset,
    ) -> None:
        """Should handle Dagster unavailable gracefully."""
        with (
            patch("src.api.analytics.exports.get_dataset_schema") as mock_schema,
            patch("src.api.analytics.exports.trigger_job") as mock_trigger,
        ):
            mock_schema.return_value = mock_dataset
            mock_trigger.return_value = None  # Dagster unavailable

            response = client.post(
                "/api/analytics/exports",
                json={
                    "dataset_id": str(mock_dataset.id),
                    "format": "csv",
                },
                headers=api_auth_headers,
            )

            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "failed"
            assert "unavailable" in data["message"].lower()

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Should return 401 without authentication."""
        response = client.post(
            "/api/analytics/exports",
            json={"dataset_id": str(uuid4()), "format": "csv"},
        )
        assert response.status_code == 401


class TestGetExportStatus:
    """Tests for GET /api/analytics/exports/{job_id} endpoint."""

    def test_returns_completed_export_with_download_url(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_export_job_in_db: Job,
    ) -> None:
        """Should return status with download URL for completed export."""
        with patch("src.api.analytics.exports.generate_download_url") as mock_url:
            mock_url.return_value = "https://presigned-url.example.com"

            response = client.get(
                f"/api/analytics/exports/{test_export_job_in_db.id}",
                headers=api_auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == str(test_export_job_in_db.id)
            assert data["status"] == "completed"
            assert data["download_url"] == "https://presigned-url.example.com"
            assert data["row_count"] == 100
            assert data["file_size_bytes"] == 5000
            assert data["expires_at"] is not None

    def test_returns_pending_export_without_url(
        self,
        api_db_session: Session,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_user_in_db: User,
    ) -> None:
        """Should return status without URL for pending export."""
        pending_job = Job(
            user_id=test_user_in_db.id,
            job_type=JobType.EXPORT.value,
            status=JobStatus.PENDING.value,
            entity_type="dataset",
            job_metadata={
                "dataset_id": str(_dataset_uuid("fct_transactions")),
                "dataset_name": "fct_transactions",
                "format": "csv",
            },
        )
        api_db_session.add(pending_job)
        api_db_session.commit()

        response = client.get(
            f"/api/analytics/exports/{pending_job.id}",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["download_url"] is None
        assert data["expires_at"] is None

    def test_returns_failed_export_with_error(
        self,
        api_db_session: Session,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_user_in_db: User,
    ) -> None:
        """Should return error message for failed export."""
        failed_job = Job(
            user_id=test_user_in_db.id,
            job_type=JobType.EXPORT.value,
            status=JobStatus.FAILED.value,
            entity_type="dataset",
            error_message="DuckDB connection failed",
            job_metadata={
                "dataset_id": str(_dataset_uuid("fct_transactions")),
            },
        )
        api_db_session.add(failed_job)
        api_db_session.commit()

        response = client.get(
            f"/api/analytics/exports/{failed_job.id}",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_message"] == "DuckDB connection failed"

    def test_returns_404_for_nonexistent_job(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for non-existent job."""
        response = client.get(
            f"/api/analytics/exports/{uuid4()}",
            headers=api_auth_headers,
        )
        assert response.status_code == 404

    def test_returns_404_for_other_users_job(
        self,
        api_db_session: Session,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for another user's job."""
        other_user = User(
            username="otheruser",
            password_hash="hashed",
            first_name="Other",
            last_name="User",
        )
        api_db_session.add(other_user)
        api_db_session.flush()

        other_job = Job(
            user_id=other_user.id,
            job_type=JobType.EXPORT.value,
            status=JobStatus.COMPLETED.value,
            job_metadata={},
        )
        api_db_session.add(other_job)
        api_db_session.commit()

        response = client.get(
            f"/api/analytics/exports/{other_job.id}",
            headers=api_auth_headers,
        )
        assert response.status_code == 404

    def test_returns_404_for_non_export_job(
        self,
        api_db_session: Session,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_user_in_db: User,
    ) -> None:
        """Should return 404 for job with wrong type."""
        sync_job = Job(
            user_id=test_user_in_db.id,
            job_type=JobType.SYNC.value,  # Not an export
            status=JobStatus.COMPLETED.value,
            job_metadata={},
        )
        api_db_session.add(sync_job)
        api_db_session.commit()

        response = client.get(
            f"/api/analytics/exports/{sync_job.id}",
            headers=api_auth_headers,
        )
        assert response.status_code == 404

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Should return 401 without authentication."""
        response = client.get(f"/api/analytics/exports/{uuid4()}")
        assert response.status_code == 401
