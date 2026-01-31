"""Tests for notifications API endpoints."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.enums import NotificationType
from src.postgres.common.models import Notification


@pytest.fixture
def test_notification_in_db(api_db_session: Session, test_user_in_db: User) -> Notification:
    """Create a notification in the database."""
    notification = Notification(
        user_id=test_user_in_db.id,
        notification_type=NotificationType.BUDGET_WARNING.value,
        title="Budget Alert",
        message="You've used 80% of your Dining budget",
        read=False,
    )
    api_db_session.add(notification)
    api_db_session.commit()
    return notification


@pytest.fixture
def test_notifications_in_db(api_db_session: Session, test_user_in_db: User) -> list[Notification]:
    """Create multiple notifications in the database."""
    notifications = [
        Notification(
            user_id=test_user_in_db.id,
            notification_type=NotificationType.BUDGET_WARNING.value,
            title="Budget Alert 1",
            message="Warning message 1",
            read=False,
        ),
        Notification(
            user_id=test_user_in_db.id,
            notification_type=NotificationType.BUDGET_EXCEEDED.value,
            title="Budget Alert 2",
            message="Exceeded message",
            read=True,
        ),
        Notification(
            user_id=test_user_in_db.id,
            notification_type=NotificationType.SYNC_COMPLETE.value,
            title="Sync Complete",
            message="Your accounts have been synced",
            read=False,
        ),
    ]
    for n in notifications:
        api_db_session.add(n)
    api_db_session.commit()
    return notifications


class TestListNotifications:
    """Tests for GET /api/notifications endpoint."""

    def test_returns_notifications_for_user(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_notifications_in_db: list[Notification],
    ) -> None:
        """Should return notifications for authenticated user."""
        response = client.get("/api/notifications", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["notifications"]) == 3
        assert data["unread_count"] == 2

    def test_filters_unread_only(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_notifications_in_db: list[Notification],
    ) -> None:
        """Should filter to unread notifications only."""
        response = client.get("/api/notifications?unread_only=true", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(not n["read"] for n in data["notifications"])

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Should return 401 without authentication."""
        response = client.get("/api/notifications")
        assert response.status_code == 401


class TestGetNotificationCount:
    """Tests for GET /api/notifications/count endpoint."""

    def test_returns_unread_count(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_notifications_in_db: list[Notification],
    ) -> None:
        """Should return count of unread notifications."""
        response = client.get("/api/notifications/count", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["unread_count"] == 2

    def test_returns_zero_when_no_notifications(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_user_in_db: User,
    ) -> None:
        """Should return 0 when user has no notifications."""
        response = client.get("/api/notifications/count", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["unread_count"] == 0


class TestMarkNotificationRead:
    """Tests for PUT /api/notifications/{id}/read endpoint."""

    def test_marks_notification_as_read(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_notification_in_db: Notification,
    ) -> None:
        """Should mark notification as read."""
        response = client.put(
            f"/api/notifications/{test_notification_in_db.id}/read",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["read"] is True
        assert data["read_at"] is not None

    def test_returns_404_for_nonexistent(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for nonexistent notification."""
        response = client.put(
            f"/api/notifications/{uuid4()}/read",
            headers=api_auth_headers,
        )

        assert response.status_code == 404


class TestMarkAllNotificationsRead:
    """Tests for PUT /api/notifications/read-all endpoint."""

    def test_marks_all_as_read(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_notifications_in_db: list[Notification],
    ) -> None:
        """Should mark all notifications as read."""
        response = client.put(
            "/api/notifications/read-all",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["unread_count"] == 0


class TestDeleteNotification:
    """Tests for DELETE /api/notifications/{id} endpoint."""

    def test_deletes_notification(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_notification_in_db: Notification,
    ) -> None:
        """Should delete notification."""
        response = client.delete(
            f"/api/notifications/{test_notification_in_db.id}",
            headers=api_auth_headers,
        )

        assert response.status_code == 204

    def test_returns_404_for_nonexistent(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for nonexistent notification."""
        response = client.delete(
            f"/api/notifications/{uuid4()}",
            headers=api_auth_headers,
        )

        assert response.status_code == 404
