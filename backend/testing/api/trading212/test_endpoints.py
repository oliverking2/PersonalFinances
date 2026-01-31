"""Tests for Trading 212 API endpoints."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.enums import Provider
from src.postgres.common.models import Institution
from src.postgres.trading212.models import T212ApiKey, T212CashBalance
from src.providers.trading212.exceptions import Trading212AuthError


@pytest.fixture
def test_t212_institution_in_db(api_db_session: Session) -> Institution:
    """Create Trading 212 institution in database."""
    institution = Institution(
        id="TRADING212",
        provider=Provider.TRADING212.value,
        name="Trading 212",
        logo_url="https://www.trading212.com/favicon.ico",
        countries=["GB"],
    )
    api_db_session.add(institution)
    api_db_session.commit()
    return institution


@pytest.fixture
def test_t212_api_key_in_db(api_db_session: Session, test_user_in_db: User) -> T212ApiKey:
    """Create a T212 API key in the database."""
    api_key = T212ApiKey(
        user_id=test_user_in_db.id,
        api_key_encrypted="encrypted_test_key",
        friendly_name="Test T212 Account",
        t212_account_id="T212_12345",
        currency_code="GBP",
        status="active",
        last_synced_at=datetime.now(UTC),
    )
    api_db_session.add(api_key)
    api_db_session.commit()
    return api_key


@pytest.fixture
def test_t212_cash_balance_in_db(
    api_db_session: Session, test_t212_api_key_in_db: T212ApiKey
) -> T212CashBalance:
    """Create a T212 cash balance in the database."""
    balance = T212CashBalance(
        api_key_id=test_t212_api_key_in_db.id,
        free=Decimal("1000.00"),
        blocked=Decimal("100.00"),
        invested=Decimal("5000.00"),
        pie_cash=Decimal("0.00"),
        ppl=Decimal("250.50"),
        result=Decimal("150.00"),
        total=Decimal("6350.50"),
        fetched_at=datetime.now(UTC),
    )
    api_db_session.add(balance)
    api_db_session.commit()
    return balance


class TestListT212Connections:
    """Tests for GET /api/trading212 endpoint."""

    def test_returns_connections_for_user(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_t212_api_key_in_db: T212ApiKey,
    ) -> None:
        """Should return all T212 connections for authenticated user."""
        response = client.get("/api/trading212", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["connections"]) == 1
        assert data["connections"][0]["friendly_name"] == "Test T212 Account"

    def test_returns_empty_list_when_no_connections(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_user_in_db: User,
    ) -> None:
        """Should return empty list when user has no T212 connections."""
        response = client.get("/api/trading212", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["connections"] == []

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Should return 401 without authentication."""
        response = client.get("/api/trading212")
        assert response.status_code == 401


class TestAddT212Connection:
    """Tests for POST /api/trading212 endpoint."""

    @patch("src.api.trading212.endpoints.Trading212Client")
    def test_creates_connection_with_valid_key(
        self,
        mock_client_class: MagicMock,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_t212_institution_in_db: Institution,
    ) -> None:
        """Should create connection when API key is valid."""
        # Mock T212 API responses
        mock_client = MagicMock()
        mock_client.get_account_info.return_value = MagicMock(
            account_id="T212_99999",
            currency_code="GBP",
        )
        mock_client.get_cash.return_value = MagicMock(
            free=Decimal("500.00"),
            blocked=Decimal("0.00"),
            invested=Decimal("1000.00"),
            pie_cash=Decimal("0.00"),
            ppl=Decimal("50.00"),
            result=Decimal("0.00"),
            total=Decimal("1550.00"),
        )
        mock_client_class.return_value = mock_client

        response = client.post(
            "/api/trading212",
            headers=api_auth_headers,
            json={
                "api_key": "test_api_key_12345",
                "friendly_name": "My T212 Account",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["friendly_name"] == "My T212 Account"
        assert data["t212_account_id"] == "T212_99999"
        assert data["currency_code"] == "GBP"
        assert data["status"] == "active"

    @patch("src.api.trading212.endpoints.Trading212Client")
    def test_returns_400_for_invalid_key(
        self,
        mock_client_class: MagicMock,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 400 when API key is invalid."""
        mock_client_class.side_effect = Trading212AuthError("Invalid API key")

        response = client.post(
            "/api/trading212",
            headers=api_auth_headers,
            json={
                "api_key": "invalid_key",
                "friendly_name": "Bad Account",
            },
        )

        assert response.status_code == 400
        assert "Invalid API key" in response.json()["detail"]


class TestGetT212Connection:
    """Tests for GET /api/trading212/{api_key_id} endpoint."""

    def test_returns_connection(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_t212_api_key_in_db: T212ApiKey,
    ) -> None:
        """Should return connection by ID."""
        response = client.get(
            f"/api/trading212/{test_t212_api_key_in_db.id}",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_t212_api_key_in_db.id)
        assert data["friendly_name"] == "Test T212 Account"

    def test_returns_404_for_nonexistent(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for nonexistent connection."""
        response = client.get(
            f"/api/trading212/{uuid4()}",
            headers=api_auth_headers,
        )

        assert response.status_code == 404


class TestDeleteT212Connection:
    """Tests for DELETE /api/trading212/{api_key_id} endpoint."""

    def test_deletes_connection(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_t212_api_key_in_db: T212ApiKey,
    ) -> None:
        """Should delete connection."""
        response = client.delete(
            f"/api/trading212/{test_t212_api_key_in_db.id}",
            headers=api_auth_headers,
        )

        assert response.status_code == 204

    def test_returns_404_for_nonexistent(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for nonexistent connection."""
        response = client.delete(
            f"/api/trading212/{uuid4()}",
            headers=api_auth_headers,
        )

        assert response.status_code == 404


class TestGetT212Balance:
    """Tests for GET /api/trading212/{api_key_id}/balance endpoint."""

    def test_returns_balance(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_t212_api_key_in_db: T212ApiKey,
        test_t212_cash_balance_in_db: T212CashBalance,
    ) -> None:
        """Should return latest cash balance."""
        response = client.get(
            f"/api/trading212/{test_t212_api_key_in_db.id}/balance",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert float(data["free"]) == 1000.00
        assert float(data["total"]) == 6350.50

    def test_returns_404_when_no_balance(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_t212_api_key_in_db: T212ApiKey,
    ) -> None:
        """Should return 404 when no balance data."""
        response = client.get(
            f"/api/trading212/{test_t212_api_key_in_db.id}/balance",
            headers=api_auth_headers,
        )

        assert response.status_code == 404

    def test_returns_404_for_nonexistent_connection(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for nonexistent connection."""
        response = client.get(
            f"/api/trading212/{uuid4()}/balance",
            headers=api_auth_headers,
        )

        assert response.status_code == 404
