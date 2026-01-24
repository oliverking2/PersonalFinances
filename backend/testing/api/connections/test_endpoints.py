"""Tests for connection API endpoints."""

from collections.abc import Generator
from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.app import app
from src.api.dependencies import get_db
from src.postgres.auth.models import User
from src.postgres.common.enums import AccountStatus, ConnectionStatus, Provider
from src.postgres.common.models import Account, Connection, Institution
from src.postgres.core import Base
from src.utils.security import create_access_token, hash_password


@pytest.fixture(scope="function")
def api_db_session() -> Generator[Session]:
    """Create a test database session for API tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    session_factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(api_db_session: Session) -> Generator[TestClient]:
    """Create test client with overridden database dependency."""

    def override_get_db() -> Generator[Session]:
        try:
            yield api_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_in_db(api_db_session: Session) -> User:
    """Create a user directly in the database for testing."""
    user = User(
        username="testuser",
        password_hash=hash_password("testpassword123"),
        first_name="Test",
        last_name="User",
    )
    api_db_session.add(user)
    api_db_session.commit()
    return user


@pytest.fixture
def auth_headers(test_user_in_db: User) -> dict[str, str]:
    """Create authentication headers with a valid JWT token."""
    token = create_access_token(test_user_in_db.id)
    return {"Authorization": f"Bearer {token}"}


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
    )
    api_db_session.add(account)
    api_db_session.commit()
    return account


class TestListConnections:
    """Tests for GET /api/connections endpoint."""

    def test_returns_user_connections(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_connection_in_db: Connection,
        test_account_in_db: Account,
    ) -> None:
        """Should return connections for authenticated user."""
        response = client.get("/api/connections", headers=auth_headers)

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
        auth_headers: dict[str, str],
        test_connection_in_db: Connection,
    ) -> None:
        """Should return connection for authenticated user."""
        response = client.get(
            f"/api/connections/{test_connection_in_db.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_connection_in_db.id)
        assert data["friendly_name"] == "Test Connection"

    def test_returns_404_for_nonexistent(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_institution_in_db: Institution,
    ) -> None:
        """Should return 404 for nonexistent connection."""
        response = client.get(
            f"/api/connections/{uuid4()}",
            headers=auth_headers,
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
        auth_headers: dict[str, str],
        test_connection_in_db: Connection,
    ) -> None:
        """Should update connection's friendly name."""
        response = client.patch(
            f"/api/connections/{test_connection_in_db.id}",
            headers=auth_headers,
            json={"friendly_name": "Updated Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["friendly_name"] == "Updated Name"

    def test_returns_404_for_nonexistent(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_institution_in_db: Institution,
    ) -> None:
        """Should return 404 for nonexistent connection."""
        response = client.patch(
            f"/api/connections/{uuid4()}",
            headers=auth_headers,
            json={"friendly_name": "New Name"},
        )

        assert response.status_code == 404


class TestDeleteConnection:
    """Tests for DELETE /api/connections/{id} endpoint."""

    def test_deletes_connection(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_connection_in_db: Connection,
        api_db_session: Session,
    ) -> None:
        """Should delete connection."""
        conn_id = str(test_connection_in_db.id)
        response = client.delete(
            f"/api/connections/{conn_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "deleted" in response.json()["message"]

        # Verify deleted
        api_db_session.expire_all()
        assert api_db_session.get(Connection, test_connection_in_db.id) is None

    def test_returns_404_for_nonexistent(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_institution_in_db: Institution,
    ) -> None:
        """Should return 404 for nonexistent connection."""
        response = client.delete(
            f"/api/connections/{uuid4()}",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestCreateConnection:
    """Tests for POST /api/connections endpoint."""

    def test_returns_501_not_implemented(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_institution_in_db: Institution,
    ) -> None:
        """Should return 501 (not implemented yet)."""
        response = client.post(
            "/api/connections",
            headers=auth_headers,
            json={
                "institution_id": "CHASE_CHASGB2L",
                "friendly_name": "My Chase",
            },
        )

        assert response.status_code == 501


class TestReauthoriseConnection:
    """Tests for POST /api/connections/{id}/reauthorise endpoint."""

    def test_returns_501_not_implemented(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_connection_in_db: Connection,
    ) -> None:
        """Should return 501 (not implemented yet)."""
        response = client.post(
            f"/api/connections/{test_connection_in_db.id}/reauthorise",
            headers=auth_headers,
        )

        assert response.status_code == 501
