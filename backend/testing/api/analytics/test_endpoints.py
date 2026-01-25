"""Tests for analytics API endpoints."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.duckdb.manifest import DATASET_UUID_NAMESPACE, Dataset, DatasetColumn
from src.postgres.auth.models import User
from src.postgres.common.enums import AccountStatus, ConnectionStatus, Provider
from src.postgres.common.models import Account, Connection, Institution, Tag


def _dataset_uuid(name: str) -> uuid.UUID:
    """Generate deterministic UUID for a dataset name."""
    return uuid.uuid5(DATASET_UUID_NAMESPACE, name)


@pytest.fixture
def test_institution_in_db(api_db_session: Session) -> Institution:
    """Create an institution in the database."""
    institution = Institution(
        id="CHASE_CHASGB2L",
        provider=Provider.GOCARDLESS.value,
        name="Chase UK",
        logo_url="https://cdn.nordigen.com/ais/CHASE_CHASGB2L.png",
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
        provider_id="test-req-id",
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
        provider_id="test-gc-account-id",
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
        name="Groceries",
        colour="#00FF00",
    )
    api_db_session.add(tag)
    api_db_session.commit()
    return tag


@pytest.fixture
def mock_datasets() -> list[Dataset]:
    """Create mock dataset objects."""
    return [
        Dataset(
            id=_dataset_uuid("fct_transactions"),
            name="fct_transactions",
            friendly_name="Transactions",
            description="Transaction data",
            group="facts",
            time_grain=None,
        ),
        Dataset(
            id=_dataset_uuid("fct_monthly_trends"),
            name="fct_monthly_trends",
            friendly_name="Monthly Trends",
            description="Monthly trends",
            group="aggregations",
            time_grain="month",
        ),
    ]


class TestGetAnalyticsStatus:
    """Tests for GET /api/analytics/status endpoint."""

    def test_returns_status_when_available(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        mock_datasets: list[Dataset],
    ) -> None:
        """Should return analytics status."""
        with (
            patch("src.api.analytics.endpoints.check_connection") as mock_check,
            patch("src.api.analytics.endpoints.get_datasets") as mock_get_datasets,
        ):
            mock_check.return_value = True
            mock_get_datasets.return_value = mock_datasets

            response = client.get("/api/analytics/status", headers=api_auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["duckdb_available"] is True
            assert data["manifest_available"] is True
            assert data["dataset_count"] == 2

    def test_returns_unavailable_when_no_duckdb(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should indicate unavailable when DuckDB not accessible."""
        with (
            patch("src.api.analytics.endpoints.check_connection") as mock_check,
            patch("src.api.analytics.endpoints.get_datasets") as mock_get_datasets,
        ):
            mock_check.return_value = False
            mock_get_datasets.return_value = []

            response = client.get("/api/analytics/status", headers=api_auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["duckdb_available"] is False
            assert data["manifest_available"] is False

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Should return 401 without authentication."""
        response = client.get("/api/analytics/status")
        assert response.status_code == 401


class TestListDatasets:
    """Tests for GET /api/analytics/datasets endpoint."""

    def test_returns_available_datasets(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        mock_datasets: list[Dataset],
    ) -> None:
        """Should return list of available datasets."""
        with patch("src.api.analytics.endpoints.get_datasets") as mock_get:
            mock_get.return_value = mock_datasets

            response = client.get("/api/analytics/datasets", headers=api_auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["datasets"]) == 2
            assert data["datasets"][0]["dataset_name"] == "fct_transactions"
            assert data["datasets"][0]["id"] == str(_dataset_uuid("fct_transactions"))
            assert data["datasets"][1]["time_grain"] == "month"

    def test_returns_empty_when_no_datasets(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return empty list when no datasets available."""
        with patch("src.api.analytics.endpoints.get_datasets") as mock_get:
            mock_get.return_value = []

            response = client.get("/api/analytics/datasets", headers=api_auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["datasets"] == []


class TestGetDatasetSchema:
    """Tests for GET /api/analytics/datasets/{id}/schema endpoint."""

    def test_returns_schema(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return dataset schema with columns."""
        dataset_id = _dataset_uuid("fct_transactions")
        mock_dataset = Dataset(
            id=dataset_id,
            name="fct_transactions",
            friendly_name="Transactions",
            description="Transaction data",
            group="facts",
            columns=[
                DatasetColumn(name="transaction_id", description="Transaction UUID"),
                DatasetColumn(name="amount", description="Amount"),
            ],
        )
        with patch("src.api.analytics.endpoints.get_dataset_schema") as mock_get:
            mock_get.return_value = mock_dataset

            response = client.get(
                f"/api/analytics/datasets/{dataset_id}/schema",
                headers=api_auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == str(dataset_id)
            assert data["dataset_name"] == "fct_transactions"
            assert len(data["columns"]) == 2
            assert data["columns"][0]["name"] == "transaction_id"

    def test_returns_404_for_unknown_dataset(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for unknown dataset."""
        unknown_id = uuid4()
        with patch("src.api.analytics.endpoints.get_dataset_schema") as mock_get:
            mock_get.return_value = None

            response = client.get(
                f"/api/analytics/datasets/{unknown_id}/schema",
                headers=api_auth_headers,
            )

            assert response.status_code == 404


class TestQueryDataset:
    """Tests for GET /api/analytics/datasets/{id}/query endpoint."""

    def test_returns_query_results(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_tag_in_db: Tag,
    ) -> None:
        """Should return query results from dataset."""
        dataset_id = _dataset_uuid("fct_daily_spending_by_tag")
        mock_dataset = Dataset(
            id=dataset_id,
            name="fct_daily_spending_by_tag",
            friendly_name="Daily Spending by Tag",
            description="Spending by tag",
            group="aggregations",
            time_grain="day",
        )
        mock_rows = [
            {
                "spending_date": date(2024, 1, 15),
                "tag_id": str(test_tag_in_db.id),
                "tag_name": "Groceries",
                "total_spending": 150.50,
            }
        ]

        with (
            patch("src.api.analytics.endpoints.get_dataset_schema") as mock_schema,
            patch("src.api.analytics.endpoints.execute_query") as mock_exec,
        ):
            mock_schema.return_value = mock_dataset
            mock_exec.return_value = mock_rows

            response = client.get(
                f"/api/analytics/datasets/{dataset_id}/query"
                "?start_date=2024-01-01&end_date=2024-01-31",
                headers=api_auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["dataset_id"] == str(dataset_id)
            assert data["dataset_name"] == "fct_daily_spending_by_tag"
            assert data["row_count"] == 1
            assert data["rows"][0]["tag_name"] == "Groceries"
            assert data["rows"][0]["spending_date"] == "2024-01-15"
            assert data["filters_applied"]["start_date"] == "2024-01-01"

    def test_returns_empty_when_duckdb_unavailable(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return empty results when DuckDB unavailable."""
        dataset_id = _dataset_uuid("fct_transactions")
        mock_dataset = Dataset(
            id=dataset_id,
            name="fct_transactions",
            friendly_name="Transactions",
            description="Transactions",
            group="facts",
        )

        with (
            patch("src.api.analytics.endpoints.get_dataset_schema") as mock_schema,
            patch("src.api.analytics.endpoints.execute_query") as mock_exec,
        ):
            mock_schema.return_value = mock_dataset
            mock_exec.side_effect = FileNotFoundError("DuckDB not found")

            response = client.get(
                f"/api/analytics/datasets/{dataset_id}/query",
                headers=api_auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["rows"] == []
            assert data["row_count"] == 0

    def test_returns_404_for_unknown_dataset(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for unknown dataset."""
        unknown_id = uuid4()
        with patch("src.api.analytics.endpoints.get_dataset_schema") as mock_get:
            mock_get.return_value = None

            response = client.get(
                f"/api/analytics/datasets/{unknown_id}/query",
                headers=api_auth_headers,
            )

            assert response.status_code == 404

    def test_validates_account_ids(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_account_in_db: Account,
    ) -> None:
        """Should filter to only user-owned accounts."""
        dataset_id = _dataset_uuid("fct_transactions")
        mock_dataset = Dataset(
            id=dataset_id,
            name="fct_transactions",
            friendly_name="Transactions",
            description="Transactions",
            group="facts",
        )

        with (
            patch("src.api.analytics.endpoints.get_dataset_schema") as mock_schema,
            patch("src.api.analytics.endpoints.execute_query") as mock_exec,
        ):
            mock_schema.return_value = mock_dataset
            mock_exec.return_value = []

            valid_account_id = str(test_account_in_db.id)
            invalid_account_id = str(uuid4())

            response = client.get(
                f"/api/analytics/datasets/{dataset_id}/query"
                f"?account_ids={valid_account_id}&account_ids={invalid_account_id}",
                headers=api_auth_headers,
            )

            assert response.status_code == 200
            # Only the valid account should be in filters
            data = response.json()
            if data["filters_applied"].get("account_ids"):
                assert valid_account_id in data["filters_applied"]["account_ids"]
                assert invalid_account_id not in data["filters_applied"]["account_ids"]

    def test_supports_pagination(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should support limit and offset parameters."""
        dataset_id = _dataset_uuid("fct_transactions")
        mock_dataset = Dataset(
            id=dataset_id,
            name="fct_transactions",
            friendly_name="Transactions",
            description="Transactions",
            group="facts",
        )

        with (
            patch("src.api.analytics.endpoints.get_dataset_schema") as mock_schema,
            patch("src.api.analytics.endpoints.execute_query") as mock_exec,
            patch("src.api.analytics.endpoints.build_dataset_query") as mock_build,
        ):
            mock_schema.return_value = mock_dataset
            mock_exec.return_value = []
            mock_build.return_value = ("SELECT * FROM mart.fct_transactions", {})

            response = client.get(
                f"/api/analytics/datasets/{dataset_id}/query?limit=50&offset=100",
                headers=api_auth_headers,
            )

            assert response.status_code == 200
            # Verify build_dataset_query was called with limit and offset
            mock_build.assert_called_once()
            call_kwargs = mock_build.call_args.kwargs
            assert call_kwargs["dataset"] == mock_dataset
            assert call_kwargs["limit"] == 50
            assert call_kwargs["offset"] == 100


class TestRefreshAnalytics:
    """Tests for POST /api/analytics/refresh endpoint."""

    def test_triggers_refresh_job(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should trigger Dagster job and return job info."""
        with patch("src.api.analytics.endpoints.trigger_job") as mock_trigger:
            mock_trigger.return_value = "test-run-id-123"

            response = client.post("/api/analytics/refresh", headers=api_auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["dagster_run_id"] == "test-run-id-123"
            assert data["status"] == "running"
            assert "job_id" in data

    def test_handles_dagster_unavailable(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should handle Dagster unavailable gracefully."""
        with patch("src.api.analytics.endpoints.trigger_job") as mock_trigger:
            mock_trigger.return_value = None  # Dagster unavailable

            response = client.post("/api/analytics/refresh", headers=api_auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["dagster_run_id"] is None
            assert data["status"] == "failed"
            assert "unavailable" in data["message"].lower()
