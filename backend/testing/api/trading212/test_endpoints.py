"""Tests for Trading 212 API endpoints."""

from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.trading212.operations.api_keys import create_api_key
from src.postgres.trading212.operations.cash_balances import upsert_cash_balance
from src.providers.trading212.api.core import AccountInfo, CashBalance
from src.utils.security import encrypt_api_key


class TestListT212Connections:
    """Tests for GET /api/trading212."""

    def test_list_empty(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Listing with no connections should return empty list."""
        response = client.get("/api/trading212", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["connections"] == []
        assert data["total"] == 0

    def test_list_with_connections(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Listing should return user's connections."""
        create_api_key(
            api_db_session,
            user_id=test_user_in_db.id,
            api_key_encrypted=encrypt_api_key("test-key"),
            friendly_name="My ISA",
            t212_account_id="12345",
            currency_code="GBP",
        )
        api_db_session.commit()

        response = client.get("/api/trading212", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["connections"][0]["friendly_name"] == "My ISA"
        assert data["connections"][0]["currency_code"] == "GBP"

    def test_list_requires_auth(self, client: TestClient) -> None:
        """Listing without auth should return 401."""
        response = client.get("/api/trading212")

        assert response.status_code == 401


class TestAddT212Connection:
    """Tests for POST /api/trading212."""

    @patch("src.api.trading212.endpoints.Trading212Client")
    def test_add_connection_success(
        self,
        mock_client_class: MagicMock,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Adding a valid connection should create records."""
        # Mock the Trading212Client
        mock_client = MagicMock()
        mock_client.get_account_info.return_value = AccountInfo(
            currency_code="GBP",
            account_id="12345",
        )
        mock_client.get_cash.return_value = CashBalance(
            free=Decimal("100.00"),
            blocked=Decimal("0.00"),
            invested=Decimal("500.00"),
            pie_cash=Decimal("0.00"),
            ppl=Decimal("25.00"),
            result=Decimal("0.00"),
            total=Decimal("625.00"),
        )
        mock_client_class.return_value = mock_client

        response = client.post(
            "/api/trading212",
            headers=api_auth_headers,
            json={
                "api_key": "test-api-key",
                "friendly_name": "My ISA",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["friendly_name"] == "My ISA"
        assert data["currency_code"] == "GBP"
        assert data["status"] == "active"

    @patch("src.api.trading212.endpoints.Trading212Client")
    def test_add_connection_invalid_key(
        self,
        mock_client_class: MagicMock,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Adding with invalid API key should return 400."""
        from src.providers.trading212.exceptions import Trading212AuthError  # noqa: PLC0415

        mock_client = MagicMock()
        mock_client.get_account_info.side_effect = Trading212AuthError("Invalid key")
        mock_client_class.return_value = mock_client

        response = client.post(
            "/api/trading212",
            headers=api_auth_headers,
            json={
                "api_key": "invalid-key",
                "friendly_name": "Test",
            },
        )

        assert response.status_code == 400
        assert "Invalid API key" in response.json()["detail"]

    def test_add_connection_requires_auth(self, client: TestClient) -> None:
        """Adding without auth should return 401."""
        response = client.post(
            "/api/trading212",
            json={
                "api_key": "test-key",
                "friendly_name": "Test",
            },
        )

        assert response.status_code == 401


class TestDeleteT212Connection:
    """Tests for DELETE /api/trading212/{id}."""

    def test_delete_connection_success(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Deleting a connection should remove it."""
        api_key = create_api_key(
            api_db_session,
            user_id=test_user_in_db.id,
            api_key_encrypted=encrypt_api_key("test-key"),
            friendly_name="To Delete",
        )
        api_db_session.commit()

        response = client.delete(
            f"/api/trading212/{api_key.id}",
            headers=api_auth_headers,
        )

        assert response.status_code == 204

    def test_delete_connection_not_found(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Deleting non-existent connection should return 404."""
        response = client.delete(
            f"/api/trading212/{uuid4()}",
            headers=api_auth_headers,
        )

        assert response.status_code == 404


class TestGetT212Balance:
    """Tests for GET /api/trading212/{id}/balance."""

    def test_get_balance_success(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Getting balance should return latest cash balance."""
        api_key = create_api_key(
            api_db_session,
            user_id=test_user_in_db.id,
            api_key_encrypted=encrypt_api_key("test-key"),
            friendly_name="Test",
        )
        upsert_cash_balance(
            api_db_session,
            api_key.id,
            free=Decimal("100.00"),
            blocked=Decimal("0.00"),
            invested=Decimal("500.00"),
            pie_cash=Decimal("0.00"),
            ppl=Decimal("25.00"),
            result=Decimal("0.00"),
            total=Decimal("625.00"),
        )
        api_db_session.commit()

        response = client.get(
            f"/api/trading212/{api_key.id}/balance",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == "625.00"
        assert data["ppl"] == "25.00"

    def test_get_balance_no_data(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Getting balance with no data should return 404."""
        api_key = create_api_key(
            api_db_session,
            user_id=test_user_in_db.id,
            api_key_encrypted=encrypt_api_key("test-key"),
            friendly_name="Test",
        )
        api_db_session.commit()

        response = client.get(
            f"/api/trading212/{api_key.id}/balance",
            headers=api_auth_headers,
        )

        assert response.status_code == 404
