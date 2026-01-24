"""Tests for authentication API endpoints."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.app import app
from src.api.dependencies import get_db
from src.postgres.auth import models as _auth_models  # noqa: F401
from src.postgres.auth.models import User
from src.postgres.auth.operations.refresh_tokens import create_refresh_token
from src.postgres.core import Base
from src.utils.security import create_access_token, hash_password


@pytest.fixture(scope="function")
def api_db_session() -> Generator[Session]:
    """Create a test database session for API tests.

    Uses StaticPool to ensure all connections share the same in-memory database.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Single connection shared across all uses
    )
    Base.metadata.create_all(engine)

    session_factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,  # Prevent attribute expiration after commit
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
            pass  # Don't close - the fixture owns the session

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


class TestRegister:
    """Tests for POST /auth/register endpoint."""

    def test_register_success(self, client: TestClient) -> None:
        """Should create user and return user info."""
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "password": "securepassword123",
                "first_name": "New",
                "last_name": "User",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert data["first_name"] == "New"
        assert data["last_name"] == "User"
        assert "id" in data

    def test_register_duplicate_username(self, client: TestClient, test_user_in_db: User) -> None:
        """Should return 409 for duplicate username."""
        response = client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "password": "anotherpassword123",
                "first_name": "Test",
                "last_name": "User",
            },
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "Username already exists"

    def test_register_username_too_short(self, client: TestClient) -> None:
        """Should return 422 for username shorter than 3 characters."""
        response = client.post(
            "/auth/register",
            json={
                "username": "ab",
                "password": "securepassword123",
                "first_name": "Test",
                "last_name": "User",
            },
        )

        assert response.status_code == 422

    def test_register_password_too_short(self, client: TestClient) -> None:
        """Should return 422 for password shorter than 8 characters."""
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "password": "short",
                "first_name": "Test",
                "last_name": "User",
            },
        )

        assert response.status_code == 422


class TestLogin:
    """Tests for POST /auth/login endpoint."""

    def test_login_success(self, client: TestClient, test_user_in_db: User) -> None:
        """Should return access token and set refresh cookie on valid credentials."""
        response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "testpassword123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "expires_in" in data
        assert data["expires_in"] == 900  # 15 minutes in seconds
        assert "refresh_token" in response.cookies

    def test_login_invalid_username(self, client: TestClient) -> None:
        """Should return 401 for non-existent username."""
        response = client.post(
            "/auth/login",
            json={"username": "nonexistent", "password": "anypassword"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"

    def test_login_invalid_password(self, client: TestClient, test_user_in_db: User) -> None:
        """Should return 401 for incorrect password."""
        response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "wrongpassword"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"

    def test_login_case_insensitive_username(
        self, client: TestClient, test_user_in_db: User
    ) -> None:
        """Should accept username regardless of case."""
        response = client.post(
            "/auth/login",
            json={"username": "TESTUSER", "password": "testpassword123"},
        )

        assert response.status_code == 200


class TestRefresh:
    """Tests for POST /auth/refresh endpoint."""

    def test_refresh_success(
        self, client: TestClient, api_db_session: Session, test_user_in_db: User
    ) -> None:
        """Should return new access token and rotate refresh token."""
        # Create a refresh token
        raw_token, _ = create_refresh_token(api_db_session, test_user_in_db)
        api_db_session.commit()

        # Set cookie and make request
        client.cookies.set("refresh_token", raw_token)
        response = client.post("/auth/refresh")

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "expires_in" in data
        # New cookie should be set (rotation)
        assert "refresh_token" in response.cookies

    def test_refresh_no_cookie(self, client: TestClient) -> None:
        """Should return 401 when no refresh token cookie."""
        response = client.post("/auth/refresh")

        assert response.status_code == 401
        assert response.json()["detail"] == "Refresh token required"

    def test_refresh_invalid_token(self, client: TestClient) -> None:
        """Should return 401 for invalid token."""
        client.cookies.set("refresh_token", "invalid-token-value")
        response = client.post("/auth/refresh")

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid refresh token"

    def test_refresh_expired_token(
        self, client: TestClient, api_db_session: Session, test_user_in_db: User
    ) -> None:
        """Should return 401 for expired token."""
        # Create an expired refresh token
        raw_token, token = create_refresh_token(api_db_session, test_user_in_db)
        token.expires_at = datetime.now(UTC) - timedelta(days=1)
        api_db_session.commit()

        client.cookies.set("refresh_token", raw_token)
        response = client.post("/auth/refresh")

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid refresh token"

    def test_refresh_replay_detection(
        self, client: TestClient, api_db_session: Session, test_user_in_db: User
    ) -> None:
        """Should revoke all tokens when replay is detected."""
        # Create and immediately revoke a token (simulating rotation)
        raw_token, token = create_refresh_token(api_db_session, test_user_in_db)
        token.revoked_at = datetime.now(UTC)
        api_db_session.commit()

        # Try to use the revoked token
        client.cookies.set("refresh_token", raw_token)
        response = client.post("/auth/refresh")

        assert response.status_code == 401
        assert response.json()["detail"] == "Token has been revoked"


class TestLogout:
    """Tests for POST /auth/logout endpoint."""

    def test_logout_success(
        self, client: TestClient, api_db_session: Session, test_user_in_db: User
    ) -> None:
        """Should revoke token and clear cookie."""
        raw_token, token = create_refresh_token(api_db_session, test_user_in_db)
        api_db_session.commit()

        client.cookies.set("refresh_token", raw_token)
        response = client.post("/auth/logout")

        assert response.status_code == 200
        assert response.json() == {"ok": True}

        # Token should be revoked in database
        api_db_session.refresh(token)
        assert token.revoked_at is not None

    def test_logout_no_cookie(self, client: TestClient) -> None:
        """Should succeed even without cookie."""
        response = client.post("/auth/logout")

        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_logout_invalid_token(self, client: TestClient) -> None:
        """Should succeed even with invalid token."""
        client.cookies.set("refresh_token", "invalid-token")
        response = client.post("/auth/logout")

        assert response.status_code == 200
        assert response.json() == {"ok": True}


class TestMe:
    """Tests for GET /auth/me endpoint."""

    def test_me_success(self, client: TestClient, test_user_in_db: User) -> None:
        """Should return user info for valid token."""
        token = create_access_token(test_user_in_db.id)

        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_user_in_db.id)
        assert data["username"] == test_user_in_db.username
        assert data["first_name"] == test_user_in_db.first_name
        assert data["last_name"] == test_user_in_db.last_name

    def test_me_no_token(self, client: TestClient) -> None:
        """Should return 401 without token."""
        response = client.get("/auth/me")

        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

    def test_me_invalid_token(self, client: TestClient) -> None:
        """Should return 401 for invalid token."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or expired token"

    def test_me_expired_token(self, client: TestClient, test_user_in_db: User) -> None:
        """Should return 401 for expired token."""
        token = create_access_token(test_user_in_db.id, expires_minutes=-1)

        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or expired token"
