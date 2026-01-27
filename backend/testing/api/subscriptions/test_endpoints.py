"""Tests for subscription API endpoints."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.enums import RecurringFrequency, RecurringStatus
from src.postgres.common.models import RecurringPattern


def _create_pattern(  # noqa: PLR0913
    session: Session,
    user: User,
    merchant: str = "netflix_£15",
    amount: Decimal = Decimal("-15.99"),
    frequency: RecurringFrequency = RecurringFrequency.MONTHLY,
    status: RecurringStatus = RecurringStatus.DETECTED,
) -> RecurringPattern:
    """Create a pattern for testing."""
    now = datetime.now(UTC)
    pattern = RecurringPattern(
        user_id=user.id,
        merchant_pattern=merchant,
        expected_amount=amount,
        currency="GBP",
        frequency=frequency.value,
        status=status.value,
        confidence_score=Decimal("0.85"),
        occurrence_count=5,
        anchor_date=now,
        last_occurrence_date=now - timedelta(days=15),
        next_expected_date=now + timedelta(days=15),
    )
    session.add(pattern)
    session.commit()
    return pattern


class TestListSubscriptions:
    """Tests for GET /api/subscriptions endpoint."""

    def test_returns_empty_list_when_no_patterns(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return empty list when user has no patterns."""
        response = client.get("/api/subscriptions", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["subscriptions"] == []
        assert data["total"] == 0
        assert float(data["monthly_total"]) == 0

    def test_returns_user_patterns(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return all patterns for the user."""
        _create_pattern(api_db_session, test_user_in_db, "netflix_£15")
        _create_pattern(api_db_session, test_user_in_db, "spotify_£10")

        response = client.get("/api/subscriptions", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_excludes_dismissed_by_default(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should exclude dismissed patterns by default."""
        _create_pattern(
            api_db_session, test_user_in_db, "dismissed", status=RecurringStatus.DISMISSED
        )

        response = client.get("/api/subscriptions", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_includes_dismissed_when_requested(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should include dismissed when include_dismissed=true."""
        _create_pattern(
            api_db_session, test_user_in_db, "dismissed", status=RecurringStatus.DISMISSED
        )

        response = client.get("/api/subscriptions?include_dismissed=true", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_filters_by_status(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should filter by status."""
        _create_pattern(
            api_db_session, test_user_in_db, "detected", status=RecurringStatus.DETECTED
        )
        _create_pattern(
            api_db_session, test_user_in_db, "confirmed", status=RecurringStatus.CONFIRMED
        )

        response = client.get("/api/subscriptions?status=confirmed", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["subscriptions"][0]["status"] == "confirmed"

    def test_requires_authentication(self, client: TestClient) -> None:
        """Should require authentication."""
        response = client.get("/api/subscriptions")
        assert response.status_code == 401


class TestGetSubscription:
    """Tests for GET /api/subscriptions/{id} endpoint."""

    def test_returns_subscription(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return subscription by ID."""
        pattern = _create_pattern(api_db_session, test_user_in_db)

        response = client.get(f"/api/subscriptions/{pattern.id}", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(pattern.id)
        assert data["merchant_pattern"] == "netflix_£15"

    def test_returns_404_for_not_found(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for non-existent subscription."""
        response = client.get(
            "/api/subscriptions/00000000-0000-0000-0000-000000000000",
            headers=api_auth_headers,
        )

        assert response.status_code == 404


class TestConfirmSubscription:
    """Tests for PUT /api/subscriptions/{id}/confirm endpoint."""

    def test_confirms_subscription(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should confirm a detected subscription."""
        pattern = _create_pattern(api_db_session, test_user_in_db)

        response = client.put(f"/api/subscriptions/{pattern.id}/confirm", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "confirmed"

    def test_returns_404_for_not_found(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for non-existent subscription."""
        response = client.put(
            "/api/subscriptions/00000000-0000-0000-0000-000000000000/confirm",
            headers=api_auth_headers,
        )

        assert response.status_code == 404


class TestDismissSubscription:
    """Tests for DELETE /api/subscriptions/{id} endpoint."""

    def test_dismisses_subscription(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should dismiss a subscription."""
        pattern = _create_pattern(api_db_session, test_user_in_db)

        response = client.delete(f"/api/subscriptions/{pattern.id}", headers=api_auth_headers)

        assert response.status_code == 204

        # Verify it's dismissed
        api_db_session.refresh(pattern)
        assert pattern.status == RecurringStatus.DISMISSED.value


class TestPauseSubscription:
    """Tests for PUT /api/subscriptions/{id}/pause endpoint."""

    def test_pauses_subscription(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should pause a subscription."""
        pattern = _create_pattern(api_db_session, test_user_in_db, status=RecurringStatus.CONFIRMED)

        response = client.put(f"/api/subscriptions/{pattern.id}/pause", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"


class TestUpdateSubscription:
    """Tests for PUT /api/subscriptions/{id} endpoint."""

    def test_updates_display_name(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should update display name."""
        pattern = _create_pattern(api_db_session, test_user_in_db)

        response = client.put(
            f"/api/subscriptions/{pattern.id}",
            headers=api_auth_headers,
            json={"display_name": "Netflix Premium"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Netflix Premium"

    def test_updates_notes(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should update notes."""
        pattern = _create_pattern(api_db_session, test_user_in_db)

        response = client.put(
            f"/api/subscriptions/{pattern.id}",
            headers=api_auth_headers,
            json={"notes": "Family plan"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Family plan"


class TestCreateSubscription:
    """Tests for POST /api/subscriptions endpoint."""

    def test_creates_manual_subscription(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should create a manual subscription."""
        response = client.post(
            "/api/subscriptions",
            headers=api_auth_headers,
            json={
                "merchant_pattern": "gym membership",
                "expected_amount": -29.99,
                "frequency": "monthly",
                "display_name": "Gym",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["merchant_pattern"] == "gym membership"
        assert data["status"] == "manual"
        assert data["display_name"] == "Gym"


class TestGetUpcomingBills:
    """Tests for GET /api/subscriptions/upcoming endpoint."""

    def test_returns_upcoming_bills(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return upcoming bills within date range."""
        pattern = _create_pattern(api_db_session, test_user_in_db, status=RecurringStatus.CONFIRMED)
        # Set next date to 3 days from now
        pattern.next_expected_date = datetime.now(UTC) + timedelta(days=3)
        api_db_session.commit()

        response = client.get("/api/subscriptions/upcoming?days=7", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["upcoming"]) == 1
        assert "total_expected" in data
        assert "date_range" in data

    def test_excludes_paused_bills(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should exclude paused subscriptions from upcoming."""
        pattern = _create_pattern(api_db_session, test_user_in_db, status=RecurringStatus.PAUSED)
        pattern.next_expected_date = datetime.now(UTC) + timedelta(days=3)
        api_db_session.commit()

        response = client.get("/api/subscriptions/upcoming?days=7", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["upcoming"]) == 0


class TestGetSubscriptionSummary:
    """Tests for GET /api/subscriptions/summary endpoint."""

    def test_returns_summary_statistics(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return summary statistics."""
        _create_pattern(api_db_session, test_user_in_db, "a", status=RecurringStatus.DETECTED)
        _create_pattern(api_db_session, test_user_in_db, "b", status=RecurringStatus.CONFIRMED)
        _create_pattern(api_db_session, test_user_in_db, "c", status=RecurringStatus.CONFIRMED)

        response = client.get("/api/subscriptions/summary", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 3
        assert data["confirmed_count"] == 2
        assert data["detected_count"] == 1
        assert "monthly_total" in data


class TestMinConfidenceValidation:
    """Tests for min_confidence parameter validation."""

    def test_rejects_invalid_min_confidence(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should reject invalid min_confidence value."""
        response = client.get(
            "/api/subscriptions?min_confidence=2.0",  # > 1.0
            headers=api_auth_headers,
        )

        assert response.status_code == 422  # Validation error

    def test_filters_by_min_confidence(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should filter by minimum confidence score."""
        pattern1 = _create_pattern(api_db_session, test_user_in_db, "high")
        pattern1.confidence_score = Decimal("0.9")

        pattern2 = _create_pattern(api_db_session, test_user_in_db, "low")
        pattern2.confidence_score = Decimal("0.3")
        api_db_session.commit()

        response = client.get("/api/subscriptions?min_confidence=0.5", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["subscriptions"][0]["merchant_pattern"] == "high"
