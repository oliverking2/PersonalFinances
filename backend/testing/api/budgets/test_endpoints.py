"""Tests for budget API endpoints."""

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.models import Tag


class TestBudgetEndpoints:
    """Tests for budget CRUD endpoints."""

    def test_list_budgets_empty(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return empty list when no budgets exist."""
        response = client.get("/api/budgets", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["budgets"] == []
        assert data["total"] == 0

    def test_create_budget(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should create a new budget."""
        # Create a tag first
        tag = Tag(user_id=test_user_in_db.id, name="Groceries", colour="#10b981")
        api_db_session.add(tag)
        api_db_session.commit()

        response = client.post(
            "/api/budgets",
            headers=api_auth_headers,
            json={
                "tag_id": str(tag.id),
                "amount": 500.00,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tag_id"] == str(tag.id)
        assert data["tag_name"] == "Groceries"
        assert Decimal(str(data["amount"])) == Decimal("500.00")
        assert data["enabled"] is True

    def test_create_budget_invalid_tag(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for invalid tag ID."""
        response = client.post(
            "/api/budgets",
            headers=api_auth_headers,
            json={
                "tag_id": "00000000-0000-0000-0000-000000000000",
                "amount": 500.00,
            },
        )

        assert response.status_code == 404

    def test_create_budget_duplicate(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 400 when budget already exists for tag."""
        tag = Tag(user_id=test_user_in_db.id, name="Test", colour="#000000")
        api_db_session.add(tag)
        api_db_session.commit()

        # Create first budget
        client.post(
            "/api/budgets",
            headers=api_auth_headers,
            json={"tag_id": str(tag.id), "amount": 500.00},
        )

        # Try to create duplicate
        response = client.post(
            "/api/budgets",
            headers=api_auth_headers,
            json={"tag_id": str(tag.id), "amount": 600.00},
        )

        assert response.status_code == 400

    def test_get_budget(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should retrieve a specific budget."""
        tag = Tag(user_id=test_user_in_db.id, name="Test", colour="#000000")
        api_db_session.add(tag)
        api_db_session.commit()

        create_response = client.post(
            "/api/budgets",
            headers=api_auth_headers,
            json={"tag_id": str(tag.id), "amount": 500.00},
        )
        budget_id = create_response.json()["id"]

        response = client.get(f"/api/budgets/{budget_id}", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == budget_id
        assert "spent_amount" in data
        assert "remaining_amount" in data
        assert "percentage_used" in data
        assert "status" in data

    def test_get_budget_not_found(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for non-existent budget."""
        response = client.get(
            "/api/budgets/00000000-0000-0000-0000-000000000000",
            headers=api_auth_headers,
        )

        assert response.status_code == 404

    def test_update_budget(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should update a budget."""
        tag = Tag(user_id=test_user_in_db.id, name="Test", colour="#000000")
        api_db_session.add(tag)
        api_db_session.commit()

        create_response = client.post(
            "/api/budgets",
            headers=api_auth_headers,
            json={"tag_id": str(tag.id), "amount": 500.00},
        )
        budget_id = create_response.json()["id"]

        response = client.put(
            f"/api/budgets/{budget_id}",
            headers=api_auth_headers,
            json={"amount": 600.00, "enabled": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert Decimal(str(data["amount"])) == Decimal("600.00")
        assert data["enabled"] is False

    def test_delete_budget(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should delete a budget."""
        tag = Tag(user_id=test_user_in_db.id, name="Test", colour="#000000")
        api_db_session.add(tag)
        api_db_session.commit()

        create_response = client.post(
            "/api/budgets",
            headers=api_auth_headers,
            json={"tag_id": str(tag.id), "amount": 500.00},
        )
        budget_id = create_response.json()["id"]

        response = client.delete(f"/api/budgets/{budget_id}", headers=api_auth_headers)

        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/api/budgets/{budget_id}", headers=api_auth_headers)
        assert get_response.status_code == 404


class TestBudgetSummary:
    """Tests for budget summary endpoint."""

    def test_get_summary_empty(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return zero counts when no budgets exist."""
        response = client.get("/api/budgets/summary", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_budgets"] == 0
        assert data["active_budgets"] == 0

    def test_get_summary_with_budgets(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return correct summary statistics."""
        # Create tags and budgets
        tag1 = Tag(user_id=test_user_in_db.id, name="Food", colour="#10b981")
        tag2 = Tag(user_id=test_user_in_db.id, name="Transport", colour="#6366f1")
        api_db_session.add_all([tag1, tag2])
        api_db_session.commit()

        client.post(
            "/api/budgets",
            headers=api_auth_headers,
            json={"tag_id": str(tag1.id), "amount": 500.00},
        )
        client.post(
            "/api/budgets",
            headers=api_auth_headers,
            json={"tag_id": str(tag2.id), "amount": 200.00},
        )

        response = client.get("/api/budgets/summary", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_budgets"] == 2
        assert data["active_budgets"] == 2
        assert Decimal(str(data["total_budgeted"])) == Decimal("700.00")


class TestBudgetAuth:
    """Tests for budget endpoint authentication."""

    def test_requires_auth(self, client: TestClient) -> None:
        """Should return 401 without authentication."""
        response = client.get("/api/budgets")
        assert response.status_code == 401
