"""Tests for goals API endpoints."""

from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.enums import AccountStatus, AccountType, ConnectionStatus, Provider
from src.postgres.common.models import Account, Connection, Institution


@pytest.fixture
def api_test_institution(api_db_session: Session) -> Institution:
    """Create a test institution for API tests."""
    institution = Institution(
        id="TEST_BANK_GB",
        provider=Provider.GOCARDLESS.value,
        name="Test Bank",
        logo_url="https://example.com/logo.png",
        countries=["GB"],
    )
    api_db_session.add(institution)
    api_db_session.commit()
    return institution


@pytest.fixture
def api_test_connection(
    api_db_session: Session, test_user_in_db: User, api_test_institution: Institution
) -> Connection:
    """Create a test connection for API tests."""
    connection = Connection(
        user_id=test_user_in_db.id,
        provider=Provider.GOCARDLESS.value,
        provider_id="test-req-id",
        institution_id=api_test_institution.id,
        friendly_name="Test Connection",
        status=ConnectionStatus.ACTIVE.value,
        created_at=datetime.now(),
    )
    api_db_session.add(connection)
    api_db_session.commit()
    return connection


@pytest.fixture
def api_test_account(api_db_session: Session, api_test_connection: Connection) -> Account:
    """Create a test account for API tests with balance."""
    account = Account(
        connection_id=api_test_connection.id,
        provider_id="test-gc-account-id",
        account_type=AccountType.BANK.value,
        status=AccountStatus.ACTIVE.value,
        name="Test Savings Account",
        display_name="My Savings",
        iban="GB00TEST00000000001234",
        currency="GBP",
        balance_amount=Decimal("5000.00"),
        balance_currency="GBP",
        balance_type="interimAvailable",
    )
    api_db_session.add(account)
    api_db_session.commit()
    return account


class TestGoalEndpoints:
    """Tests for goal CRUD endpoints."""

    def test_list_goals_empty(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return empty list when no goals exist."""
        response = client.get("/api/goals", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["goals"] == []
        assert data["total"] == 0

    def test_create_goal(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should create a new goal."""
        response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={
                "name": "Emergency Fund",
                "target_amount": 5000.00,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Emergency Fund"
        assert Decimal(str(data["target_amount"])) == Decimal("5000.00")
        assert Decimal(str(data["current_amount"])) == Decimal("0")
        assert data["status"] == "active"

    def test_create_goal_with_initial_amount(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should create a goal with starting amount."""
        response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={
                "name": "Vacation",
                "target_amount": 3000.00,
                "current_amount": 500.00,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert Decimal(str(data["current_amount"])) == Decimal("500.00")

    def test_create_goal_with_deadline(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should create a goal with deadline."""
        response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={
                "name": "Holiday",
                "target_amount": 2000.00,
                "deadline": "2027-06-01",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["deadline"] is not None
        assert data["days_remaining"] is not None

    def test_get_goal(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should retrieve a specific goal."""
        create_response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={"name": "Test Goal", "target_amount": 1000.00},
        )
        goal_id = create_response.json()["id"]

        response = client.get(f"/api/goals/{goal_id}", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == goal_id
        assert "progress_percentage" in data

    def test_get_goal_not_found(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for non-existent goal."""
        response = client.get(
            "/api/goals/00000000-0000-0000-0000-000000000000",
            headers=api_auth_headers,
        )

        assert response.status_code == 404

    def test_update_goal(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should update a goal."""
        create_response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={"name": "Original", "target_amount": 1000.00},
        )
        goal_id = create_response.json()["id"]

        response = client.put(
            f"/api/goals/{goal_id}",
            headers=api_auth_headers,
            json={"name": "Updated", "target_amount": 2000.00},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated"
        assert Decimal(str(data["target_amount"])) == Decimal("2000.00")

    def test_delete_goal(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should delete a goal."""
        create_response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={"name": "Test", "target_amount": 1000.00},
        )
        goal_id = create_response.json()["id"]

        response = client.delete(f"/api/goals/{goal_id}", headers=api_auth_headers)

        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/api/goals/{goal_id}", headers=api_auth_headers)
        assert get_response.status_code == 404


class TestGoalContributions:
    """Tests for goal contribution endpoint."""

    def test_contribute_to_goal(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should add contribution to goal."""
        create_response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={"name": "Test", "target_amount": 1000.00},
        )
        goal_id = create_response.json()["id"]

        response = client.post(
            f"/api/goals/{goal_id}/contribute",
            headers=api_auth_headers,
            json={"amount": 200.00},
        )

        assert response.status_code == 200
        data = response.json()
        assert Decimal(str(data["current_amount"])) == Decimal("200.00")

    def test_contribute_auto_completes(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should auto-complete goal when target reached."""
        create_response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={"name": "Test", "target_amount": 100.00, "current_amount": 90.00},
        )
        goal_id = create_response.json()["id"]

        response = client.post(
            f"/api/goals/{goal_id}/contribute",
            headers=api_auth_headers,
            json={"amount": 15.00},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_contribute_to_paused_goal_fails(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should fail to contribute to paused goal."""
        create_response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={"name": "Test", "target_amount": 1000.00},
        )
        goal_id = create_response.json()["id"]

        # Pause the goal
        client.put(f"/api/goals/{goal_id}/pause", headers=api_auth_headers)

        # Try to contribute
        response = client.post(
            f"/api/goals/{goal_id}/contribute",
            headers=api_auth_headers,
            json={"amount": 100.00},
        )

        assert response.status_code == 400


class TestGoalStatusActions:
    """Tests for goal status action endpoints."""

    def test_complete_goal(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should mark goal as completed."""
        create_response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={"name": "Test", "target_amount": 1000.00},
        )
        goal_id = create_response.json()["id"]

        response = client.put(f"/api/goals/{goal_id}/complete", headers=api_auth_headers)

        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    def test_pause_and_resume_goal(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should pause and resume a goal."""
        create_response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={"name": "Test", "target_amount": 1000.00},
        )
        goal_id = create_response.json()["id"]

        # Pause
        pause_response = client.put(f"/api/goals/{goal_id}/pause", headers=api_auth_headers)
        assert pause_response.status_code == 200
        assert pause_response.json()["status"] == "paused"

        # Resume
        resume_response = client.put(f"/api/goals/{goal_id}/resume", headers=api_auth_headers)
        assert resume_response.status_code == 200
        assert resume_response.json()["status"] == "active"

    def test_cancel_goal(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should cancel a goal."""
        create_response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={"name": "Test", "target_amount": 1000.00},
        )
        goal_id = create_response.json()["id"]

        response = client.put(f"/api/goals/{goal_id}/cancel", headers=api_auth_headers)

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"


class TestGoalSummary:
    """Tests for goals summary endpoint."""

    def test_get_summary_empty(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return zero counts when no goals exist."""
        response = client.get("/api/goals/summary", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_goals"] == 0
        assert data["active_goals"] == 0

    def test_get_summary_with_goals(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return correct summary statistics."""
        # Create goals
        client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={"name": "Goal 1", "target_amount": 1000.00, "current_amount": 500.00},
        )
        g2_response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={"name": "Goal 2", "target_amount": 2000.00, "current_amount": 1000.00},
        )
        g2_id = g2_response.json()["id"]

        # Complete one
        client.put(f"/api/goals/{g2_id}/complete", headers=api_auth_headers)

        response = client.get("/api/goals/summary", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_goals"] == 2
        assert data["active_goals"] == 1
        assert data["completed_goals"] == 1


class TestGoalAuth:
    """Tests for goal endpoint authentication."""

    def test_requires_auth(self, client: TestClient) -> None:
        """Should return 401 without authentication."""
        response = client.get("/api/goals")
        assert response.status_code == 401

    def test_update_goal_with_other_users_account_fails(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        api_db_session: Session,
    ) -> None:
        """Should not allow linking goal to another user's account."""
        # Create another user with their own account
        other_user = User(
            username="other_user",
            password_hash="fake_hash",
        )
        api_db_session.add(other_user)
        api_db_session.flush()

        institution = Institution(
            id="OTHER_BANK_GB",
            provider=Provider.GOCARDLESS.value,
            name="Other Bank",
            logo_url="https://example.com/other.png",
            countries=["GB"],
        )
        api_db_session.add(institution)
        api_db_session.flush()

        other_connection = Connection(
            user_id=other_user.id,
            provider=Provider.GOCARDLESS.value,
            provider_id="other-req-id",
            institution_id=institution.id,
            friendly_name="Other Connection",
            status=ConnectionStatus.ACTIVE.value,
            created_at=datetime.now(),
        )
        api_db_session.add(other_connection)
        api_db_session.flush()

        other_account = Account(
            connection_id=other_connection.id,
            provider_id="other-account-id",
            account_type=AccountType.BANK.value,
            status=AccountStatus.ACTIVE.value,
            name="Other Account",
            display_name="Not Mine",
            currency="GBP",
        )
        api_db_session.add(other_account)
        api_db_session.commit()

        # Create a goal as the test user
        create_response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={
                "name": "My Goal",
                "target_amount": 1000.00,
            },
        )
        assert create_response.status_code == 201
        goal_id = create_response.json()["id"]

        # Try to link it to the other user's account
        update_response = client.put(
            f"/api/goals/{goal_id}",
            headers=api_auth_headers,
            json={
                "account_id": str(other_account.id),
            },
        )

        assert update_response.status_code == 404
        assert "not found" in update_response.json()["detail"].lower()


class TestGoalTrackingModes:
    """Tests for goal tracking modes feature."""

    def test_create_manual_goal(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should create a manual tracking goal by default."""
        response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={
                "name": "Manual Savings",
                "target_amount": 1000.00,
                "current_amount": 100.00,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tracking_mode"] == "manual"
        assert Decimal(str(data["current_amount"])) == Decimal("100.00")

    def test_create_balance_goal(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        api_test_account: Account,
    ) -> None:
        """Should create a balance tracking goal linked to account."""
        response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={
                "name": "ISA Balance",
                "target_amount": 10000.00,
                "account_id": str(api_test_account.id),
                "tracking_mode": "balance",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tracking_mode"] == "balance"
        assert data["account_id"] == str(api_test_account.id)
        # Current amount should mirror account balance
        assert Decimal(str(data["current_amount"])) == Decimal("5000.00")

    def test_create_delta_goal(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        api_test_account: Account,
    ) -> None:
        """Should create a delta tracking goal with starting balance snapshot."""
        response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={
                "name": "Save 2000",
                "target_amount": 2000.00,
                "account_id": str(api_test_account.id),
                "tracking_mode": "delta",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tracking_mode"] == "delta"
        assert data["account_id"] == str(api_test_account.id)
        # Starting balance should be captured from account
        assert Decimal(str(data["starting_balance"])) == Decimal("5000.00")
        # Current amount = current balance - starting balance = 0
        assert Decimal(str(data["current_amount"])) == Decimal("0")

    def test_create_target_balance_goal(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        api_test_account: Account,
    ) -> None:
        """Should create a target_balance tracking goal."""
        response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={
                "name": "Emergency Fund 10k",
                "target_amount": 10000.00,  # Used for progress display
                "target_balance": 10000.00,  # Actual target
                "account_id": str(api_test_account.id),
                "tracking_mode": "target_balance",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tracking_mode"] == "target_balance"
        assert Decimal(str(data["target_balance"])) == Decimal("10000.00")
        # Current amount shows account balance
        assert Decimal(str(data["current_amount"])) == Decimal("5000.00")
        # Progress should be 50% towards 10k target
        assert Decimal(str(data["progress_percentage"])) == Decimal("50")

    def test_balance_mode_requires_account(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should reject balance mode without account."""
        response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={
                "name": "Missing Account",
                "target_amount": 1000.00,
                "tracking_mode": "balance",
            },
        )

        assert response.status_code == 400
        assert "account" in response.json()["detail"].lower()

    def test_delta_mode_requires_account(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should reject delta mode without account."""
        response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={
                "name": "Missing Account",
                "target_amount": 1000.00,
                "tracking_mode": "delta",
            },
        )

        assert response.status_code == 400
        assert "account" in response.json()["detail"].lower()

    def test_target_balance_mode_requires_target(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        api_test_account: Account,
    ) -> None:
        """Should reject target_balance mode without target_balance field."""
        response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={
                "name": "Missing Target",
                "target_amount": 1000.00,
                "account_id": str(api_test_account.id),
                "tracking_mode": "target_balance",
            },
        )

        assert response.status_code == 400
        assert "target balance" in response.json()["detail"].lower()

    def test_contribute_to_manual_goal_allowed(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should allow contributions to manual tracking goals."""
        # Create manual goal
        create_response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={
                "name": "Manual Goal",
                "target_amount": 1000.00,
                "tracking_mode": "manual",
            },
        )
        goal_id = create_response.json()["id"]

        # Contribute
        response = client.post(
            f"/api/goals/{goal_id}/contribute",
            headers=api_auth_headers,
            json={"amount": 200.00},
        )

        assert response.status_code == 200
        assert Decimal(str(response.json()["current_amount"])) == Decimal("200.00")

    def test_contribute_to_balance_goal_blocked(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        api_test_account: Account,
    ) -> None:
        """Should block contributions to balance tracking goals."""
        # Create balance goal
        create_response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={
                "name": "Balance Goal",
                "target_amount": 10000.00,
                "account_id": str(api_test_account.id),
                "tracking_mode": "balance",
            },
        )
        goal_id = create_response.json()["id"]

        # Try to contribute
        response = client.post(
            f"/api/goals/{goal_id}/contribute",
            headers=api_auth_headers,
            json={"amount": 200.00},
        )

        assert response.status_code == 400
        assert "manual" in response.json()["detail"].lower()

    def test_contribute_to_delta_goal_blocked(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        api_test_account: Account,
    ) -> None:
        """Should block contributions to delta tracking goals."""
        # Create delta goal
        create_response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={
                "name": "Delta Goal",
                "target_amount": 2000.00,
                "account_id": str(api_test_account.id),
                "tracking_mode": "delta",
            },
        )
        goal_id = create_response.json()["id"]

        # Try to contribute
        response = client.post(
            f"/api/goals/{goal_id}/contribute",
            headers=api_auth_headers,
            json={"amount": 200.00},
        )

        assert response.status_code == 400
        assert "manual" in response.json()["detail"].lower()

    def test_goal_response_includes_tracking_fields(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should include tracking mode fields in response."""
        # Create goal
        create_response = client.post(
            "/api/goals",
            headers=api_auth_headers,
            json={
                "name": "Test Goal",
                "target_amount": 1000.00,
            },
        )
        goal_id = create_response.json()["id"]

        # Get goal
        response = client.get(f"/api/goals/{goal_id}", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "tracking_mode" in data
        assert "starting_balance" in data
        assert "target_balance" in data
