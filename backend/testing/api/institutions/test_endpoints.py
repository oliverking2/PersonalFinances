"""Tests for institution API endpoints."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.app import app
from src.api.dependencies import get_db
from src.postgres.auth.models import User
from src.postgres.common.enums import Provider
from src.postgres.common.models import Institution
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
def test_institutions_in_db(api_db_session: Session) -> list[Institution]:
    """Create multiple institutions in the database."""
    institutions = [
        Institution(
            id="CHASE_CHASGB2L",
            provider=Provider.GOCARDLESS.value,
            name="Chase UK",
            logo_url="https://cdn.nordigen.com/ais/CHASE_CHASGB2L.png",
            countries=["GB"],
        ),
        Institution(
            id="MONZO_MONZGB2L",
            provider=Provider.GOCARDLESS.value,
            name="Monzo",
            logo_url="https://cdn.nordigen.com/ais/MONZO_MONZGB2L.png",
            countries=["GB"],
        ),
        Institution(
            id="REVOLUT_REVOGB21",
            provider=Provider.GOCARDLESS.value,
            name="Revolut",
            logo_url="https://cdn.nordigen.com/ais/REVOLUT_REVOGB21.png",
            countries=["GB", "IE"],
        ),
    ]
    for inst in institutions:
        api_db_session.add(inst)
    api_db_session.commit()
    return institutions


class TestListInstitutions:
    """Tests for GET /api/institutions endpoint."""

    def test_returns_all_institutions(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_institutions_in_db: list[Institution],
    ) -> None:
        """Should return all institutions."""
        response = client.get("/api/institutions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["institutions"]) == 3

        # Check structure
        inst = data["institutions"][0]
        assert "id" in inst
        assert "provider" in inst
        assert "name" in inst
        assert "logo_url" in inst
        assert "countries" in inst

    def test_filters_by_provider(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_institutions_in_db: list[Institution],
    ) -> None:
        """Should filter by provider."""
        response = client.get(
            "/api/institutions?provider=gocardless",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert all(inst["provider"] == "gocardless" for inst in data["institutions"])

    def test_filters_by_country(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_institutions_in_db: list[Institution],
    ) -> None:
        """Should filter by country."""
        response = client.get(
            "/api/institutions?country=IE",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Only Revolut supports IE
        assert data["total"] == 1
        assert data["institutions"][0]["id"] == "REVOLUT_REVOGB21"

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Should return 401 without authentication."""
        response = client.get("/api/institutions")

        assert response.status_code == 401


class TestGetInstitution:
    """Tests for GET /api/institutions/{id} endpoint."""

    def test_returns_institution(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_institutions_in_db: list[Institution],
    ) -> None:
        """Should return institution by ID."""
        response = client.get(
            "/api/institutions/CHASE_CHASGB2L",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "CHASE_CHASGB2L"
        assert data["name"] == "Chase UK"
        assert data["provider"] == "gocardless"

    def test_returns_404_for_nonexistent(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for nonexistent institution."""
        response = client.get(
            "/api/institutions/NONEXISTENT_ID",
            headers=auth_headers,
        )

        assert response.status_code == 404
