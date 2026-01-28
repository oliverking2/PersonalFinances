"""Tests for alerts API endpoints."""

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.enums import AlertType
from src.postgres.common.models import Tag
from src.postgres.common.operations.alerts import create_alert
from src.postgres.common.operations.budgets import create_budget


class TestAlertEndpoints:
    """Tests for alert CRUD endpoints."""

    def test_list_alerts_empty(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return empty list when no alerts exist."""
        response = client.get("/api/alerts", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["alerts"] == []
        assert data["total"] == 0
        assert data["pending_count"] == 0

    def test_list_alerts_with_data(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return alerts for user."""
        # Create tag and budget
        tag = Tag(user_id=test_user_in_db.id, name="Test", colour="#000000")
        api_db_session.add(tag)
        api_db_session.commit()

        budget = create_budget(
            api_db_session,
            user_id=test_user_in_db.id,
            tag_id=tag.id,
            amount=Decimal("500.00"),
        )
        api_db_session.commit()

        # Create alert
        create_alert(
            api_db_session,
            user_id=test_user_in_db.id,
            budget_id=budget.id,
            alert_type=AlertType.BUDGET_WARNING,
            period_key="2026-01",
            budget_amount=Decimal("500.00"),
            spent_amount=Decimal("420.00"),
        )
        api_db_session.commit()

        response = client.get("/api/alerts", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) == 1
        assert data["total"] == 1
        assert data["pending_count"] == 1

    def test_get_alert(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should retrieve a specific alert."""
        tag = Tag(user_id=test_user_in_db.id, name="Test", colour="#000000")
        api_db_session.add(tag)
        api_db_session.commit()

        budget = create_budget(api_db_session, test_user_in_db.id, tag.id, Decimal("500.00"))
        api_db_session.commit()

        alert = create_alert(
            api_db_session,
            test_user_in_db.id,
            budget.id,
            AlertType.BUDGET_WARNING,
            "2026-01",
            Decimal("500.00"),
            Decimal("420.00"),
        )
        api_db_session.commit()

        response = client.get(f"/api/alerts/{alert.id}", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(alert.id)
        assert data["alert_type"] == "budget_warning"
        assert data["status"] == "pending"

    def test_get_alert_not_found(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for non-existent alert."""
        response = client.get(
            "/api/alerts/00000000-0000-0000-0000-000000000000",
            headers=api_auth_headers,
        )

        assert response.status_code == 404


class TestAlertAcknowledge:
    """Tests for alert acknowledgement endpoints."""

    def test_acknowledge_alert(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should acknowledge an alert."""
        tag = Tag(user_id=test_user_in_db.id, name="Test", colour="#000000")
        api_db_session.add(tag)
        api_db_session.commit()

        budget = create_budget(api_db_session, test_user_in_db.id, tag.id, Decimal("500.00"))
        api_db_session.commit()

        alert = create_alert(
            api_db_session,
            test_user_in_db.id,
            budget.id,
            AlertType.BUDGET_WARNING,
            "2026-01",
            Decimal("500.00"),
            Decimal("420.00"),
        )
        api_db_session.commit()

        response = client.put(
            f"/api/alerts/{alert.id}/acknowledge",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "acknowledged"
        assert data["acknowledged_at"] is not None

    def test_acknowledge_all_alerts(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should acknowledge all pending alerts."""
        tag = Tag(user_id=test_user_in_db.id, name="Test", colour="#000000")
        api_db_session.add(tag)
        api_db_session.commit()

        budget = create_budget(api_db_session, test_user_in_db.id, tag.id, Decimal("500.00"))
        api_db_session.commit()

        create_alert(
            api_db_session,
            test_user_in_db.id,
            budget.id,
            AlertType.BUDGET_WARNING,
            "2026-01",
            Decimal("500.00"),
            Decimal("420.00"),
        )
        create_alert(
            api_db_session,
            test_user_in_db.id,
            budget.id,
            AlertType.BUDGET_EXCEEDED,
            "2026-01",
            Decimal("500.00"),
            Decimal("520.00"),
        )
        api_db_session.commit()

        response = client.put("/api/alerts/acknowledge-all", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["pending_count"] == 0


class TestAlertCount:
    """Tests for alert count endpoint."""

    def test_get_count_empty(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return zero when no pending alerts."""
        response = client.get("/api/alerts/count", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["pending_count"] == 0

    def test_get_count_with_alerts(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should count pending alerts."""
        tag = Tag(user_id=test_user_in_db.id, name="Test", colour="#000000")
        api_db_session.add(tag)
        api_db_session.commit()

        budget = create_budget(api_db_session, test_user_in_db.id, tag.id, Decimal("500.00"))
        api_db_session.commit()

        create_alert(
            api_db_session,
            test_user_in_db.id,
            budget.id,
            AlertType.BUDGET_WARNING,
            "2026-01",
            Decimal("500.00"),
            Decimal("420.00"),
        )
        create_alert(
            api_db_session,
            test_user_in_db.id,
            budget.id,
            AlertType.BUDGET_EXCEEDED,
            "2026-01",
            Decimal("500.00"),
            Decimal("520.00"),
        )
        api_db_session.commit()

        response = client.get("/api/alerts/count", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["pending_count"] == 2


class TestAlertAuth:
    """Tests for alert endpoint authentication."""

    def test_requires_auth(self, client: TestClient) -> None:
        """Should return 401 without authentication."""
        response = client.get("/api/alerts")
        assert response.status_code == 401
