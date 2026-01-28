"""Tests for connection API endpoints."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
import requests
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.enums import AccountStatus, ConnectionStatus, Provider
from src.postgres.common.models import Account, Connection, Institution
from src.postgres.gocardless.models import RequisitionLink
from src.utils.security import create_access_token, hash_password


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
def test_expired_connection_in_db(
    api_db_session: Session, test_user_in_db: User, test_institution_in_db: Institution
) -> Connection:
    """Create an expired connection in the database."""
    connection = Connection(
        user_id=test_user_in_db.id,
        provider=Provider.GOCARDLESS.value,
        provider_id="test-expired-req-id",
        institution_id=test_institution_in_db.id,
        friendly_name="Expired Connection",
        status=ConnectionStatus.EXPIRED.value,
        created_at=datetime.now(),
    )
    api_db_session.add(connection)
    api_db_session.commit()
    return connection


@pytest.fixture
def test_pending_connection_in_db(
    api_db_session: Session, test_user_in_db: User, test_institution_in_db: Institution
) -> Connection:
    """Create a pending connection in the database (OAuth flow abandoned)."""
    connection = Connection(
        user_id=test_user_in_db.id,
        provider=Provider.GOCARDLESS.value,
        provider_id="test-pending-req-id",
        institution_id=test_institution_in_db.id,
        friendly_name="Pending Connection",
        status=ConnectionStatus.PENDING.value,
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
    )
    api_db_session.add(account)
    api_db_session.commit()
    return account


@pytest.fixture
def mock_gocardless_api() -> MagicMock:
    """Create a mock for GoCardless API responses."""
    return MagicMock()


class TestListConnections:
    """Tests for GET /api/connections endpoint."""

    def test_returns_user_connections(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_connection_in_db: Connection,
        test_account_in_db: Account,
    ) -> None:
        """Should return connections for authenticated user."""
        response = client.get("/api/connections", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["connections"]) >= 1

        conn = data["connections"][0]
        assert conn["id"] == str(test_connection_in_db.id)
        assert conn["friendly_name"] == "Test Connection"
        assert conn["provider"] == "gocardless"
        assert conn["status"] == "active"
        assert conn["account_count"] == 1
        assert "institution" in conn
        assert conn["institution"]["id"] == "CHASE_CHASGB2L"
        assert conn["institution"]["name"] == "Chase UK"

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Should return 401 without authentication."""
        response = client.get("/api/connections")

        assert response.status_code == 401


class TestGetConnection:
    """Tests for GET /api/connections/{id} endpoint."""

    def test_returns_connection(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_connection_in_db: Connection,
    ) -> None:
        """Should return connection for authenticated user."""
        response = client.get(
            f"/api/connections/{test_connection_in_db.id}",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_connection_in_db.id)
        assert data["friendly_name"] == "Test Connection"

    def test_returns_404_for_nonexistent(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_institution_in_db: Institution,
    ) -> None:
        """Should return 404 for nonexistent connection."""
        response = client.get(
            f"/api/connections/{uuid4()}",
            headers=api_auth_headers,
        )

        assert response.status_code == 404

    def test_returns_404_for_other_users_connection(
        self,
        client: TestClient,
        api_db_session: Session,
        test_institution_in_db: Institution,
    ) -> None:
        """Should return 404 for connection owned by another user."""
        # Create another user and their connection
        other_user = User(
            username="otheruser",
            password_hash=hash_password("password"),
            first_name="Other",
            last_name="User",
        )
        api_db_session.add(other_user)
        api_db_session.commit()

        other_conn = Connection(
            user_id=other_user.id,
            provider=Provider.GOCARDLESS.value,
            provider_id="other-req-id",
            institution_id=test_institution_in_db.id,
            friendly_name="Other Connection",
            status=ConnectionStatus.ACTIVE.value,
            created_at=datetime.now(),
        )
        api_db_session.add(other_conn)
        api_db_session.commit()

        # Create another user who tries to access it
        requesting_user = User(
            username="requestuser",
            password_hash=hash_password("password"),
            first_name="Request",
            last_name="User",
        )
        api_db_session.add(requesting_user)
        api_db_session.commit()

        token = create_access_token(requesting_user.id)
        response = client.get(
            f"/api/connections/{other_conn.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404


class TestUpdateConnection:
    """Tests for PATCH /api/connections/{id} endpoint."""

    def test_updates_friendly_name(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_connection_in_db: Connection,
    ) -> None:
        """Should update connection's friendly name."""
        response = client.patch(
            f"/api/connections/{test_connection_in_db.id}",
            headers=api_auth_headers,
            json={"friendly_name": "Updated Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["friendly_name"] == "Updated Name"

    def test_returns_404_for_nonexistent(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_institution_in_db: Institution,
    ) -> None:
        """Should return 404 for nonexistent connection."""
        response = client.patch(
            f"/api/connections/{uuid4()}",
            headers=api_auth_headers,
            json={"friendly_name": "New Name"},
        )

        assert response.status_code == 404


class TestDeleteConnection:
    """Tests for DELETE /api/connections/{id} endpoint."""

    @patch("src.api.connections.endpoints.delete_requisition_data_by_id")
    def test_deletes_connection_and_revokes_on_gocardless(
        self,
        mock_delete_requisition: MagicMock,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_connection_in_db: Connection,
        api_db_session: Session,
    ) -> None:
        """Should delete connection locally and revoke on GoCardless."""
        mock_delete_requisition.return_value = {"summary": "deleted"}

        conn_id = str(test_connection_in_db.id)
        provider_id = test_connection_in_db.provider_id

        response = client.delete(
            f"/api/connections/{conn_id}",
            headers=api_auth_headers,
        )

        assert response.status_code == 204
        assert response.content == b""

        # Verify GoCardless API was called with correct requisition ID
        mock_delete_requisition.assert_called_once()
        call_args = mock_delete_requisition.call_args
        assert call_args[0][1] == provider_id

        # Verify connection deleted locally
        api_db_session.expire_all()
        assert api_db_session.get(Connection, test_connection_in_db.id) is None

    @patch("src.api.connections.endpoints.delete_requisition_data_by_id")
    def test_delete_succeeds_when_gocardless_returns_404(
        self,
        mock_delete_requisition: MagicMock,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_connection_in_db: Connection,
        api_db_session: Session,
    ) -> None:
        """Should succeed when GoCardless requisition already deleted."""
        # Simulate GoCardless 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_delete_requisition.side_effect = requests.HTTPError(response=mock_response)

        conn_id = str(test_connection_in_db.id)
        response = client.delete(
            f"/api/connections/{conn_id}",
            headers=api_auth_headers,
        )

        # Should still return 204 (goal achieved - requisition gone)
        assert response.status_code == 204

        # Verify connection deleted locally
        api_db_session.expire_all()
        assert api_db_session.get(Connection, test_connection_in_db.id) is None

    @patch("src.api.connections.endpoints.delete_requisition_data_by_id")
    def test_delete_returns_502_when_gocardless_fails(
        self,
        mock_delete_requisition: MagicMock,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_connection_in_db: Connection,
        api_db_session: Session,
    ) -> None:
        """Should return 502 when GoCardless deletion fails, but still delete locally."""
        # Simulate GoCardless 500 error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_delete_requisition.side_effect = requests.HTTPError(response=mock_response)

        conn_id = str(test_connection_in_db.id)
        response = client.delete(
            f"/api/connections/{conn_id}",
            headers=api_auth_headers,
        )

        # Should return 502 to inform user
        assert response.status_code == 502
        assert "failed to revoke bank access" in response.json()["detail"]

        # But connection should still be deleted locally
        api_db_session.expire_all()
        assert api_db_session.get(Connection, test_connection_in_db.id) is None

    @patch("src.api.connections.endpoints.delete_requisition_data_by_id")
    def test_delete_cascades_to_accounts(
        self,
        mock_delete_requisition: MagicMock,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_connection_in_db: Connection,
        test_account_in_db: Account,
        api_db_session: Session,
    ) -> None:
        """Should cascade delete to accounts."""
        mock_delete_requisition.return_value = {"summary": "deleted"}

        conn_id = str(test_connection_in_db.id)
        account_id = test_account_in_db.id

        response = client.delete(
            f"/api/connections/{conn_id}",
            headers=api_auth_headers,
        )

        assert response.status_code == 204

        # Verify both connection and account deleted
        api_db_session.expire_all()
        assert api_db_session.get(Connection, test_connection_in_db.id) is None
        assert api_db_session.get(Account, account_id) is None

    def test_returns_404_for_nonexistent(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_institution_in_db: Institution,
    ) -> None:
        """Should return 404 for nonexistent connection."""
        response = client.delete(
            f"/api/connections/{uuid4()}",
            headers=api_auth_headers,
        )

        assert response.status_code == 404

    @patch("src.api.connections.endpoints.delete_requisition_data_by_id")
    def test_returns_404_for_other_users_connection(
        self,
        mock_delete_requisition: MagicMock,
        client: TestClient,
        api_db_session: Session,
        test_institution_in_db: Institution,
    ) -> None:
        """Should return 404 for connection owned by another user."""
        # Create another user and their connection
        other_user = User(
            username="deleteotheruser",
            password_hash=hash_password("password"),
            first_name="Other",
            last_name="User",
        )
        api_db_session.add(other_user)
        api_db_session.commit()

        other_conn = Connection(
            user_id=other_user.id,
            provider=Provider.GOCARDLESS.value,
            provider_id="other-delete-req-id",
            institution_id=test_institution_in_db.id,
            friendly_name="Other Connection",
            status=ConnectionStatus.ACTIVE.value,
            created_at=datetime.now(),
        )
        api_db_session.add(other_conn)
        api_db_session.commit()

        # Create another user who tries to delete it
        requesting_user = User(
            username="deleterequestuser",
            password_hash=hash_password("password"),
            first_name="Request",
            last_name="User",
        )
        api_db_session.add(requesting_user)
        api_db_session.commit()

        token = create_access_token(requesting_user.id)
        response = client.delete(
            f"/api/connections/{other_conn.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
        # GoCardless should not have been called
        mock_delete_requisition.assert_not_called()


class TestCreateConnection:
    """Tests for POST /api/connections endpoint."""

    @patch("src.api.connections.endpoints.create_link")
    def test_creates_connection_success(
        self,
        mock_create_link: MagicMock,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_institution_in_db: Institution,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Should create connection and return OAuth link."""
        # Set environment variable
        monkeypatch.setenv("GC_CALLBACK_URL", "http://localhost:8000/api/connections/callback")

        # Mock GoCardless API response
        mock_create_link.return_value = {
            "id": "new-req-id-123",
            "created": "2026-01-24T12:00:00Z",
            "redirect": "http://localhost:8000/api/connections/callback",
            "status": "CR",
            "institution_id": "CHASE_CHASGB2L",
            "agreement": "agreement-id",
            "reference": "ref-123",
            "link": "https://ob.gocardless.com/psd2/start/new-req-id-123",
            "ssn": None,
            "account_selection": False,
            "redirect_immediate": False,
        }

        response = client.post(
            "/api/connections",
            headers=api_auth_headers,
            json={
                "institution_id": "CHASE_CHASGB2L",
                "friendly_name": "My Chase Account",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["link"] == "https://ob.gocardless.com/psd2/start/new-req-id-123"

    def test_returns_404_for_invalid_institution(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for non-existent institution."""
        response = client.post(
            "/api/connections",
            headers=api_auth_headers,
            json={
                "institution_id": "NONEXISTENT_BANK",
                "friendly_name": "My Bank",
            },
        )

        assert response.status_code == 404
        assert "Institution not found" in response.json()["detail"]

    def test_returns_401_without_auth(
        self,
        client: TestClient,
        test_institution_in_db: Institution,
    ) -> None:
        """Should return 401 without authentication."""
        response = client.post(
            "/api/connections",
            json={
                "institution_id": "CHASE_CHASGB2L",
                "friendly_name": "My Chase",
            },
        )

        assert response.status_code == 401


class TestReauthoriseConnection:
    """Tests for POST /api/connections/{id}/reauthorise endpoint."""

    @patch("src.api.connections.endpoints.create_link")
    def test_reauthorises_expired_connection(
        self,
        mock_create_link: MagicMock,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_expired_connection_in_db: Connection,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Should generate new auth link for expired connection."""
        # Set environment variable
        monkeypatch.setenv("GC_CALLBACK_URL", "http://localhost:8000/api/connections/callback")

        # Mock GoCardless API response
        mock_create_link.return_value = {
            "id": "reauth-req-id-456",
            "created": "2026-01-24T12:00:00Z",
            "redirect": "http://localhost:8000/api/connections/callback",
            "status": "CR",
            "institution_id": "CHASE_CHASGB2L",
            "agreement": "agreement-id",
            "reference": "ref-456",
            "link": "https://ob.gocardless.com/psd2/start/reauth-req-id-456",
            "ssn": None,
            "account_selection": False,
            "redirect_immediate": False,
        }

        response = client.post(
            f"/api/connections/{test_expired_connection_in_db.id}/reauthorise",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_expired_connection_in_db.id)
        assert data["link"] == "https://ob.gocardless.com/psd2/start/reauth-req-id-456"

    @patch("src.api.connections.endpoints.create_link")
    def test_reauthorises_pending_connection(
        self,
        mock_create_link: MagicMock,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_pending_connection_in_db: Connection,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Should generate new auth link for pending connection (abandoned OAuth)."""
        monkeypatch.setenv("GC_CALLBACK_URL", "http://localhost:8000/api/connections/callback")

        mock_create_link.return_value = {
            "id": "retry-req-id-789",
            "created": "2026-01-24T12:00:00Z",
            "redirect": "http://localhost:8000/api/connections/callback",
            "status": "CR",
            "institution_id": "CHASE_CHASGB2L",
            "agreement": "agreement-id",
            "reference": "ref-789",
            "link": "https://ob.gocardless.com/psd2/start/retry-req-id-789",
            "ssn": None,
            "account_selection": False,
            "redirect_immediate": False,
        }

        response = client.post(
            f"/api/connections/{test_pending_connection_in_db.id}/reauthorise",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_pending_connection_in_db.id)
        assert data["link"] == "https://ob.gocardless.com/psd2/start/retry-req-id-789"

    def test_returns_400_for_active_connection(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_connection_in_db: Connection,
    ) -> None:
        """Should return 400 if connection is already active."""
        response = client.post(
            f"/api/connections/{test_connection_in_db.id}/reauthorise",
            headers=api_auth_headers,
        )

        assert response.status_code == 400
        assert "cannot be reauthorised" in response.json()["detail"]

    def test_returns_404_for_nonexistent_connection(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_institution_in_db: Institution,
    ) -> None:
        """Should return 404 for nonexistent connection."""
        response = client.post(
            f"/api/connections/{uuid4()}/reauthorise",
            headers=api_auth_headers,
        )

        assert response.status_code == 404

    def test_returns_404_for_other_users_connection(
        self,
        client: TestClient,
        api_db_session: Session,
        test_institution_in_db: Institution,
    ) -> None:
        """Should return 404 for connection owned by another user."""
        # Create another user and their expired connection
        other_user = User(
            username="otheruser2",
            password_hash=hash_password("password"),
            first_name="Other",
            last_name="User",
        )
        api_db_session.add(other_user)
        api_db_session.commit()

        other_conn = Connection(
            user_id=other_user.id,
            provider=Provider.GOCARDLESS.value,
            provider_id="other-expired-req-id",
            institution_id=test_institution_in_db.id,
            friendly_name="Other Expired Connection",
            status=ConnectionStatus.EXPIRED.value,
            created_at=datetime.now(),
        )
        api_db_session.add(other_conn)
        api_db_session.commit()

        # Create another user who tries to reauthorise it
        requesting_user = User(
            username="requestuser2",
            password_hash=hash_password("password"),
            first_name="Request",
            last_name="User",
        )
        api_db_session.add(requesting_user)
        api_db_session.commit()

        token = create_access_token(requesting_user.id)
        response = client.post(
            f"/api/connections/{other_conn.id}/reauthorise",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404


class TestOAuthCallback:
    """Tests for GET /api/connections/callback endpoint."""

    @patch("src.api.connections.endpoints.get_requisition_data_by_id")
    def test_callback_success_linked(
        self,
        mock_get_requisition: MagicMock,
        client: TestClient,
        api_db_session: Session,
        test_connection_in_db: Connection,
    ) -> None:
        """Should process callback and return success JSON."""
        # Create a requisition for the existing connection
        requisition = RequisitionLink(
            id=test_connection_in_db.provider_id,
            created=datetime.now(),
            updated=datetime.now(),
            redirect="http://localhost:3000/accounts",
            status="CR",
            institution_id=test_connection_in_db.institution_id,
            agreement="agreement-id",
            reference="ref-123",
            link="https://ob.gocardless.com/psd2/start/test-req-id",
            ssn=None,
            account_selection=False,
            redirect_immediate=False,
            friendly_name="Test Connection",
        )
        api_db_session.add(requisition)

        # Update connection to PENDING status
        test_connection_in_db.status = ConnectionStatus.PENDING.value
        api_db_session.commit()

        # Mock GoCardless returning linked status
        mock_get_requisition.return_value = {"status": "LN"}

        response = client.get(
            "/api/connections/callback",
            params={"ref": test_connection_in_db.provider_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["reason"] is None

        # Verify connection status was updated
        api_db_session.expire_all()
        updated_conn = api_db_session.get(Connection, test_connection_in_db.id)
        assert updated_conn is not None
        assert updated_conn.status == ConnectionStatus.ACTIVE.value

    def test_callback_unknown_requisition(
        self,
        client: TestClient,
    ) -> None:
        """Should return error JSON for unknown requisition."""
        response = client.get(
            "/api/connections/callback",
            params={"ref": "nonexistent-req-id"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["reason"] == "unknown_requisition"
