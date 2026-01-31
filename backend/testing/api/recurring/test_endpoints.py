"""Tests for recurring patterns API endpoints."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.enums import (
    RecurringDirection,
    RecurringFrequency,
    RecurringSource,
    RecurringStatus,
)
from src.postgres.common.models import RecurringPattern


def _create_pattern(
    session: Session,
    user: User,
    name: str = "Netflix",
    amount: Decimal = Decimal("15.99"),
    frequency: RecurringFrequency = RecurringFrequency.MONTHLY,
    status: RecurringStatus = RecurringStatus.ACTIVE,
    source: RecurringSource = RecurringSource.MANUAL,
    direction: RecurringDirection = RecurringDirection.EXPENSE,
) -> RecurringPattern:
    """Create a pattern for testing."""
    now = datetime.now(UTC)
    pattern = RecurringPattern(
        user_id=user.id,
        name=name,
        expected_amount=amount,
        currency="GBP",
        frequency=frequency.value,
        direction=direction.value,
        status=status.value,
        source=source.value,
        amount_tolerance_pct=Decimal("10.0"),
        match_count=0,
        anchor_date=now,
        last_matched_date=now - timedelta(days=15),
        next_expected_date=now + timedelta(days=15),
    )
    session.add(pattern)
    session.commit()
    return pattern


class TestListPatterns:
    """Tests for GET /api/recurring/patterns endpoint."""

    def test_returns_empty_list_when_no_patterns(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return empty list when user has no patterns."""
        response = client.get("/api/recurring/patterns", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["patterns"] == []
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
        _create_pattern(api_db_session, test_user_in_db, "Netflix")
        _create_pattern(api_db_session, test_user_in_db, "Spotify")

        response = client.get("/api/recurring/patterns", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_filters_by_status(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should filter by status."""
        _create_pattern(api_db_session, test_user_in_db, "Active", status=RecurringStatus.ACTIVE)
        _create_pattern(
            api_db_session,
            test_user_in_db,
            "Pending",
            status=RecurringStatus.PENDING,
            source=RecurringSource.DETECTED,
        )

        response = client.get("/api/recurring/patterns?status=active", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["patterns"][0]["status"] == "active"

    def test_requires_authentication(self, client: TestClient) -> None:
        """Should require authentication."""
        response = client.get("/api/recurring/patterns")
        assert response.status_code == 401


class TestGetPattern:
    """Tests for GET /api/recurring/patterns/{id} endpoint."""

    def test_returns_pattern(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return pattern by ID."""
        pattern = _create_pattern(api_db_session, test_user_in_db)

        response = client.get(f"/api/recurring/patterns/{pattern.id}", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(pattern.id)
        assert data["name"] == "Netflix"

    def test_returns_404_for_not_found(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for non-existent pattern."""
        response = client.get(
            "/api/recurring/patterns/00000000-0000-0000-0000-000000000000",
            headers=api_auth_headers,
        )

        assert response.status_code == 404


class TestAcceptPattern:
    """Tests for POST /api/recurring/patterns/{id}/accept endpoint."""

    def test_accepts_pending_pattern(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should accept a pending pattern."""
        pattern = _create_pattern(
            api_db_session,
            test_user_in_db,
            status=RecurringStatus.PENDING,
            source=RecurringSource.DETECTED,
        )

        response = client.post(
            f"/api/recurring/patterns/{pattern.id}/accept", headers=api_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"

    def test_returns_404_for_not_found(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for non-existent pattern."""
        response = client.post(
            "/api/recurring/patterns/00000000-0000-0000-0000-000000000000/accept",
            headers=api_auth_headers,
        )

        assert response.status_code == 404


class TestDeletePattern:
    """Tests for DELETE /api/recurring/patterns/{id} endpoint."""

    def test_deletes_pattern(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should delete a pattern."""
        pattern = _create_pattern(api_db_session, test_user_in_db)

        response = client.delete(f"/api/recurring/patterns/{pattern.id}", headers=api_auth_headers)

        assert response.status_code == 204


class TestPausePattern:
    """Tests for POST /api/recurring/patterns/{id}/pause endpoint."""

    def test_pauses_pattern(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should pause a pattern."""
        pattern = _create_pattern(api_db_session, test_user_in_db, status=RecurringStatus.ACTIVE)

        response = client.post(
            f"/api/recurring/patterns/{pattern.id}/pause", headers=api_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"


class TestResumePattern:
    """Tests for POST /api/recurring/patterns/{id}/resume endpoint."""

    def test_resumes_paused_pattern(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should resume a paused pattern."""
        pattern = _create_pattern(api_db_session, test_user_in_db, status=RecurringStatus.PAUSED)

        response = client.post(
            f"/api/recurring/patterns/{pattern.id}/resume", headers=api_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"


class TestCancelPattern:
    """Tests for POST /api/recurring/patterns/{id}/cancel endpoint."""

    def test_cancels_pattern(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should cancel a pattern."""
        pattern = _create_pattern(api_db_session, test_user_in_db, status=RecurringStatus.ACTIVE)

        response = client.post(
            f"/api/recurring/patterns/{pattern.id}/cancel", headers=api_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["end_date"] is not None


class TestUpdatePattern:
    """Tests for PUT /api/recurring/patterns/{id} endpoint."""

    def test_updates_name(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should update display name."""
        pattern = _create_pattern(api_db_session, test_user_in_db)

        response = client.put(
            f"/api/recurring/patterns/{pattern.id}",
            headers=api_auth_headers,
            json={"name": "Netflix Premium"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Netflix Premium"

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
            f"/api/recurring/patterns/{pattern.id}",
            headers=api_auth_headers,
            json={"notes": "Family plan"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Family plan"


class TestCreatePattern:
    """Tests for POST /api/recurring/patterns endpoint."""

    def test_creates_manual_pattern(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should create a manual pattern."""
        response = client.post(
            "/api/recurring/patterns",
            headers=api_auth_headers,
            json={
                "name": "Gym Membership",
                "expected_amount": 29.99,
                "frequency": "monthly",
                "direction": "expense",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Gym Membership"
        assert data["status"] == "active"
        assert data["source"] == "manual"


class TestGetUpcomingBills:
    """Tests for GET /api/recurring/upcoming endpoint."""

    def test_returns_upcoming_bills(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return upcoming bills within date range."""
        pattern = _create_pattern(api_db_session, test_user_in_db, status=RecurringStatus.ACTIVE)
        # Set next date to 3 days from now
        pattern.next_expected_date = datetime.now(UTC) + timedelta(days=3)
        api_db_session.commit()

        response = client.get("/api/recurring/upcoming?days=7", headers=api_auth_headers)

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
        """Should exclude paused patterns from upcoming."""
        pattern = _create_pattern(api_db_session, test_user_in_db, status=RecurringStatus.PAUSED)
        pattern.next_expected_date = datetime.now(UTC) + timedelta(days=3)
        api_db_session.commit()

        response = client.get("/api/recurring/upcoming?days=7", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["upcoming"]) == 0


class TestGetSummary:
    """Tests for GET /api/recurring/summary endpoint."""

    def test_returns_summary_statistics(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return summary statistics."""
        _create_pattern(
            api_db_session,
            test_user_in_db,
            "a",
            status=RecurringStatus.PENDING,
            source=RecurringSource.DETECTED,
        )
        _create_pattern(api_db_session, test_user_in_db, "b", status=RecurringStatus.ACTIVE)
        _create_pattern(api_db_session, test_user_in_db, "c", status=RecurringStatus.ACTIVE)

        response = client.get("/api/recurring/summary", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 3
        assert data["active_count"] == 2
        assert data["pending_count"] == 1
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
            "/api/recurring/patterns?min_confidence=2.0",  # > 1.0
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
        pattern1 = _create_pattern(
            api_db_session,
            test_user_in_db,
            "High",
            status=RecurringStatus.PENDING,
            source=RecurringSource.DETECTED,
        )
        pattern1.confidence_score = Decimal("0.9")

        pattern2 = _create_pattern(
            api_db_session,
            test_user_in_db,
            "Low",
            status=RecurringStatus.PENDING,
            source=RecurringSource.DETECTED,
        )
        pattern2.confidence_score = Decimal("0.3")
        api_db_session.commit()

        response = client.get(
            "/api/recurring/patterns?min_confidence=0.5", headers=api_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["patterns"][0]["name"] == "High"
