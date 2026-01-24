"""Tests for account API endpoints."""

from collections.abc import Generator
from datetime import datetime
from decimal import Decimal
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


@pytest.fixture
def test_account_with_balance_in_db(
    api_db_session: Session, test_connection_in_db: Connection
) -> Account:
    """Create an account with balance fields populated."""
    account = Account(
        connection_id=test_connection_in_db.id,
        provider_id="test-gc-account-with-balance",
        status=AccountStatus.ACTIVE.value,
        name="Test Account With Balance",
        display_name="My Account",
        iban="GB00TEST00000000001234",
        currency="GBP",
        balance_amount=Decimal("1234.56"),
        balance_currency="GBP",
        balance_type="interimAvailable",
        balance_updated_at=datetime.now(),
    )
    api_db_session.add(account)
    api_db_session.commit()
    return account


class TestListAccounts:
    """Tests for GET /api/accounts endpoint."""

    def test_returns_all_user_accounts(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_account_in_db: Account,
    ) -> None:
        """Should return all accounts for authenticated user."""
        response = client.get("/api/accounts", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["accounts"]) >= 1

        acc = data["accounts"][0]
        assert acc["id"] == str(test_account_in_db.id)
        assert acc["connection_id"] == str(test_account_in_db.connection_id)
        assert acc["name"] == "Test Account"
        assert acc["display_name"] == "My Account"
        assert acc["status"] == "active"

    def test_filters_by_connection_id(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_account_in_db: Account,
        test_connection_in_db: Connection,
    ) -> None:
        """Should filter accounts by connection_id."""
        response = client.get(
            f"/api/accounts?connection_id={test_connection_in_db.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert all(
            acc["connection_id"] == str(test_connection_in_db.id) for acc in data["accounts"]
        )

    def test_returns_404_for_invalid_connection_id(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_institution_in_db: Institution,
    ) -> None:
        """Should return 404 for connection not owned by user."""
        response = client.get(
            f"/api/accounts?connection_id={uuid4()}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_includes_balance_when_available(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_account_with_balance_in_db: Account,
    ) -> None:
        """Should include balance in response when available."""
        response = client.get("/api/accounts", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        acc = data["accounts"][0]
        assert acc["balance"] is not None
        assert acc["balance"]["amount"] == "1234.56"
        assert acc["balance"]["currency"] == "GBP"
        assert acc["balance"]["type"] == "interimAvailable"

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Should return 401 without authentication."""
        response = client.get("/api/accounts")

        assert response.status_code == 401


class TestGetAccount:
    """Tests for GET /api/accounts/{id} endpoint."""

    def test_returns_account(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_account_in_db: Account,
    ) -> None:
        """Should return account for authenticated user."""
        response = client.get(
            f"/api/accounts/{test_account_in_db.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_account_in_db.id)
        assert data["name"] == "Test Account"

    def test_returns_404_for_nonexistent(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_institution_in_db: Institution,
    ) -> None:
        """Should return 404 for nonexistent account."""
        response = client.get(
            f"/api/accounts/{uuid4()}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_returns_404_for_other_users_account(
        self,
        client: TestClient,
        api_db_session: Session,
        test_institution_in_db: Institution,
    ) -> None:
        """Should return 404 for account owned by another user."""
        # Create another user and their connection/account
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

        other_acc = Account(
            connection_id=other_conn.id,
            provider_id="other-gc-acc-id",
            status=AccountStatus.ACTIVE.value,
            name="Other Account",
        )
        api_db_session.add(other_acc)
        api_db_session.commit()

        # Create requesting user
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
            f"/api/accounts/{other_acc.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404


class TestUpdateAccount:
    """Tests for PATCH /api/accounts/{id} endpoint."""

    def test_updates_display_name(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_account_in_db: Account,
    ) -> None:
        """Should update account's display name."""
        response = client.patch(
            f"/api/accounts/{test_account_in_db.id}",
            headers=auth_headers,
            json={"display_name": "Updated Display Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Updated Display Name"

    def test_clears_display_name(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_account_in_db: Account,
    ) -> None:
        """Should clear display name when set to null."""
        response = client.patch(
            f"/api/accounts/{test_account_in_db.id}",
            headers=auth_headers,
            json={"display_name": None},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] is None

    def test_returns_404_for_nonexistent(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_institution_in_db: Institution,
    ) -> None:
        """Should return 404 for nonexistent account."""
        response = client.patch(
            f"/api/accounts/{uuid4()}",
            headers=auth_headers,
            json={"display_name": "New Name"},
        )

        assert response.status_code == 404
