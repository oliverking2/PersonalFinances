"""Tests for milestones API endpoints."""

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.operations.financial_milestones import create_milestone


class TestListMilestones:
    """Tests for GET /api/milestones."""

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Unauthenticated requests are rejected."""
        response = client.get("/api/milestones")
        assert response.status_code == 401

    def test_returns_empty_list(self, client: TestClient, api_auth_headers: dict[str, str]) -> None:
        """Returns empty list when user has no milestones."""
        response = client.get("/api/milestones", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["milestones"] == []
        assert data["total"] == 0

    def test_returns_user_milestones(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        api_db_session: Session,
        test_user_in_db: User,
    ) -> None:
        """Returns milestones for authenticated user."""
        # Create milestones
        create_milestone(
            api_db_session,
            test_user_in_db.id,
            name="Emergency Fund",
            target_amount=Decimal("10000.00"),
        )
        create_milestone(
            api_db_session,
            test_user_in_db.id,
            name="First £100K",
            target_amount=Decimal("100000.00"),
        )
        api_db_session.commit()

        response = client.get("/api/milestones", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        # Ordered by target_amount ascending
        assert data["milestones"][0]["name"] == "Emergency Fund"
        assert data["milestones"][1]["name"] == "First £100K"

    def test_filters_by_achieved_status(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        api_db_session: Session,
        test_user_in_db: User,
    ) -> None:
        """Filters milestones by achieved status."""
        m1 = create_milestone(
            api_db_session,
            test_user_in_db.id,
            name="Achieved",
            target_amount=Decimal("1000.00"),
        )
        m1.achieved = True
        create_milestone(
            api_db_session,
            test_user_in_db.id,
            name="Pending",
            target_amount=Decimal("2000.00"),
        )
        api_db_session.commit()

        # Filter achieved only
        response = client.get(
            "/api/milestones", params={"achieved": True}, headers=api_auth_headers
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["milestones"][0]["name"] == "Achieved"

        # Filter pending only
        response = client.get(
            "/api/milestones", params={"achieved": False}, headers=api_auth_headers
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["milestones"][0]["name"] == "Pending"


class TestGetMilestone:
    """Tests for GET /api/milestones/{milestone_id}."""

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Unauthenticated requests are rejected."""
        response = client.get(f"/api/milestones/{uuid4()}")
        assert response.status_code == 401

    def test_returns_404_for_missing(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Returns 404 for non-existent milestone."""
        response = client.get(f"/api/milestones/{uuid4()}", headers=api_auth_headers)
        assert response.status_code == 404

    def test_returns_milestone(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        api_db_session: Session,
        test_user_in_db: User,
    ) -> None:
        """Returns milestone details."""
        milestone = create_milestone(
            api_db_session,
            test_user_in_db.id,
            name="Emergency Fund",
            target_amount=Decimal("10000.00"),
            colour="#10b981",
            notes="For rainy days",
        )
        api_db_session.commit()

        response = client.get(f"/api/milestones/{milestone.id}", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Emergency Fund"
        assert data["target_amount"] == "10000.00"
        assert data["colour"] == "#10b981"
        assert data["notes"] == "For rainy days"
        assert data["achieved"] is False


class TestCreateMilestone:
    """Tests for POST /api/milestones."""

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Unauthenticated requests are rejected."""
        response = client.post("/api/milestones", json={"name": "Test", "target_amount": 1000})
        assert response.status_code == 401

    def test_creates_milestone(self, client: TestClient, api_auth_headers: dict[str, str]) -> None:
        """Creates a new milestone."""
        response = client.post(
            "/api/milestones",
            json={
                "name": "Emergency Fund",
                "target_amount": 10000,
                "colour": "#10b981",
                "notes": "For emergencies",
            },
            headers=api_auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Emergency Fund"
        assert data["target_amount"] == "10000"
        assert data["colour"] == "#10b981"
        assert data["achieved"] is False

    def test_validates_required_fields(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Validates required fields."""
        response = client.post(
            "/api/milestones",
            json={"name": "Test"},  # Missing target_amount
            headers=api_auth_headers,
        )
        assert response.status_code == 422


class TestUpdateMilestone:
    """Tests for PATCH /api/milestones/{milestone_id}."""

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Unauthenticated requests are rejected."""
        response = client.patch(f"/api/milestones/{uuid4()}", json={"name": "New"})
        assert response.status_code == 401

    def test_returns_404_for_missing(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Returns 404 for non-existent milestone."""
        response = client.patch(
            f"/api/milestones/{uuid4()}",
            json={"name": "New"},
            headers=api_auth_headers,
        )
        assert response.status_code == 404

    def test_updates_milestone(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        api_db_session: Session,
        test_user_in_db: User,
    ) -> None:
        """Updates milestone fields."""
        milestone = create_milestone(
            api_db_session,
            test_user_in_db.id,
            name="Old Name",
            target_amount=Decimal("10000.00"),
        )
        api_db_session.commit()

        response = client.patch(
            f"/api/milestones/{milestone.id}",
            json={"name": "New Name", "target_amount": 20000},
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["target_amount"] == "20000"


class TestAchieveMilestone:
    """Tests for POST /api/milestones/{milestone_id}/achieve."""

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Unauthenticated requests are rejected."""
        response = client.post(f"/api/milestones/{uuid4()}/achieve")
        assert response.status_code == 401

    def test_marks_milestone_as_achieved(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        api_db_session: Session,
        test_user_in_db: User,
    ) -> None:
        """Marks milestone as achieved."""
        milestone = create_milestone(
            api_db_session,
            test_user_in_db.id,
            name="Test",
            target_amount=Decimal("10000.00"),
        )
        api_db_session.commit()

        response = client.post(f"/api/milestones/{milestone.id}/achieve", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["achieved"] is True
        assert data["achieved_at"] is not None

    def test_returns_400_if_already_achieved(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        api_db_session: Session,
        test_user_in_db: User,
    ) -> None:
        """Returns 400 if milestone is already achieved."""
        milestone = create_milestone(
            api_db_session,
            test_user_in_db.id,
            name="Test",
            target_amount=Decimal("10000.00"),
        )
        milestone.achieved = True
        api_db_session.commit()

        response = client.post(f"/api/milestones/{milestone.id}/achieve", headers=api_auth_headers)

        assert response.status_code == 400
        assert "already achieved" in response.json()["detail"]


class TestDeleteMilestone:
    """Tests for DELETE /api/milestones/{milestone_id}."""

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Unauthenticated requests are rejected."""
        response = client.delete(f"/api/milestones/{uuid4()}")
        assert response.status_code == 401

    def test_returns_404_for_missing(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Returns 404 for non-existent milestone."""
        response = client.delete(f"/api/milestones/{uuid4()}", headers=api_auth_headers)
        assert response.status_code == 404

    def test_deletes_milestone(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        api_db_session: Session,
        test_user_in_db: User,
    ) -> None:
        """Deletes a milestone."""
        milestone = create_milestone(
            api_db_session,
            test_user_in_db.id,
            name="Test",
            target_amount=Decimal("10000.00"),
        )
        api_db_session.commit()

        response = client.delete(f"/api/milestones/{milestone.id}", headers=api_auth_headers)

        assert response.status_code == 204

        # Verify deleted
        response = client.get(f"/api/milestones/{milestone.id}", headers=api_auth_headers)
        assert response.status_code == 404
