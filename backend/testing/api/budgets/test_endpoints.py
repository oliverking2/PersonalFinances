"""Tests for budget API endpoints."""

from decimal import Decimal
from unittest.mock import patch

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


class TestBudgetPeriod:
    """Tests for budget period field."""

    def test_create_budget_with_weekly_period(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should create a budget with weekly period."""
        tag = Tag(user_id=test_user_in_db.id, name="Coffee", colour="#8B4513")
        api_db_session.add(tag)
        api_db_session.commit()

        response = client.post(
            "/api/budgets",
            headers=api_auth_headers,
            json={
                "tag_id": str(tag.id),
                "amount": 50.00,
                "period": "weekly",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["period"] == "weekly"

    def test_create_budget_with_quarterly_period(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should create a budget with quarterly period."""
        tag = Tag(user_id=test_user_in_db.id, name="Insurance", colour="#4169E1")
        api_db_session.add(tag)
        api_db_session.commit()

        response = client.post(
            "/api/budgets",
            headers=api_auth_headers,
            json={
                "tag_id": str(tag.id),
                "amount": 300.00,
                "period": "quarterly",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["period"] == "quarterly"

    def test_create_budget_with_annual_period(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should create a budget with annual period."""
        tag = Tag(user_id=test_user_in_db.id, name="Holiday", colour="#FF6347")
        api_db_session.add(tag)
        api_db_session.commit()

        response = client.post(
            "/api/budgets",
            headers=api_auth_headers,
            json={
                "tag_id": str(tag.id),
                "amount": 3000.00,
                "period": "annual",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["period"] == "annual"

    def test_create_budget_defaults_to_monthly(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should default to monthly period when not specified."""
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
        assert data["period"] == "monthly"

    def test_update_budget_period(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should update budget period."""
        tag = Tag(user_id=test_user_in_db.id, name="Test", colour="#000000")
        api_db_session.add(tag)
        api_db_session.commit()

        create_response = client.post(
            "/api/budgets",
            headers=api_auth_headers,
            json={"tag_id": str(tag.id), "amount": 500.00, "period": "monthly"},
        )
        budget_id = create_response.json()["id"]

        response = client.put(
            f"/api/budgets/{budget_id}",
            headers=api_auth_headers,
            json={"period": "weekly"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "weekly"


class TestBudgetForecast:
    """Tests for budget forecast endpoint."""

    def test_forecast_returns_empty_when_no_budgets(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return empty forecasts when no budgets exist."""
        # Mock DuckDB query since dbt model doesn't exist in test environment
        with patch("src.api.budgets.endpoints.execute_query") as mock_query:
            mock_query.return_value = []

            response = client.get("/api/budgets/forecast", headers=api_auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["forecasts"] == []
            assert data["budgets_at_risk"] == 0

    def test_forecast_returns_budgets_at_risk(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should count budgets at risk correctly."""
        # Mock DuckDB query with sample forecast data
        with patch("src.api.budgets.endpoints.execute_query") as mock_query:
            mock_query.return_value = [
                {
                    "budget_id": "00000000-0000-0000-0000-000000000001",
                    "tag_id": "00000000-0000-0000-0000-000000000010",
                    "tag_name": "Groceries",
                    "tag_colour": "#10b981",
                    "budget_amount": Decimal("500.00"),
                    "currency": "GBP",
                    "period": "monthly",
                    "spent_amount": Decimal("450.00"),
                    "remaining_amount": Decimal("50.00"),
                    "percentage_used": Decimal("90.00"),
                    "budget_status": "warning",
                    "days_remaining": 10,
                    "daily_avg_spending": Decimal("15.00"),
                    "days_until_exhausted": Decimal("3.33"),
                    "projected_exceed_date": "2026-02-04",
                    "will_exceed_in_period": True,
                    "projected_percentage": Decimal("135.00"),
                    "risk_level": "critical",
                },
                {
                    "budget_id": "00000000-0000-0000-0000-000000000002",
                    "tag_id": "00000000-0000-0000-0000-000000000020",
                    "tag_name": "Transport",
                    "tag_colour": "#6366f1",
                    "budget_amount": Decimal("200.00"),
                    "currency": "GBP",
                    "period": "monthly",
                    "spent_amount": Decimal("50.00"),
                    "remaining_amount": Decimal("150.00"),
                    "percentage_used": Decimal("25.00"),
                    "budget_status": "ok",
                    "days_remaining": 10,
                    "daily_avg_spending": Decimal("5.00"),
                    "days_until_exhausted": Decimal("30.00"),
                    "projected_exceed_date": None,
                    "will_exceed_in_period": False,
                    "projected_percentage": Decimal("75.00"),
                    "risk_level": "low",
                },
            ]

            response = client.get("/api/budgets/forecast", headers=api_auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert len(data["forecasts"]) == 2
            # Only critical budget is at risk
            assert data["budgets_at_risk"] == 1

    def test_forecast_requires_auth(self, client: TestClient) -> None:
        """Should return 401 without authentication."""
        response = client.get("/api/budgets/forecast")
        assert response.status_code == 401


class TestBudgetAuth:
    """Tests for budget endpoint authentication."""

    def test_requires_auth(self, client: TestClient) -> None:
        """Should return 401 without authentication."""
        response = client.get("/api/budgets")
        assert response.status_code == 401
