"""Tests for institution API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.postgres.common.enums import Provider
from src.postgres.common.models import Institution


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
        api_auth_headers: dict[str, str],
        test_institutions_in_db: list[Institution],
    ) -> None:
        """Should return all institutions."""
        response = client.get("/api/institutions", headers=api_auth_headers)

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
        api_auth_headers: dict[str, str],
        test_institutions_in_db: list[Institution],
    ) -> None:
        """Should filter by provider."""
        response = client.get(
            "/api/institutions?provider=gocardless",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert all(inst["provider"] == "gocardless" for inst in data["institutions"])

    def test_filters_by_country(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_institutions_in_db: list[Institution],
    ) -> None:
        """Should filter by country."""
        response = client.get(
            "/api/institutions?country=IE",
            headers=api_auth_headers,
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
        api_auth_headers: dict[str, str],
        test_institutions_in_db: list[Institution],
    ) -> None:
        """Should return institution by ID."""
        response = client.get(
            "/api/institutions/CHASE_CHASGB2L",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "CHASE_CHASGB2L"
        assert data["name"] == "Chase UK"
        assert data["provider"] == "gocardless"

    def test_returns_404_for_nonexistent(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for nonexistent institution."""
        response = client.get(
            "/api/institutions/NONEXISTENT_ID",
            headers=api_auth_headers,
        )

        assert response.status_code == 404
