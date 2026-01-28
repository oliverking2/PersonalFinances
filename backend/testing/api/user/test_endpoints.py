"""Tests for user API endpoints."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.postgres.auth.models import User


class TestGetTelegramStatus:
    """Tests for GET /api/user/telegram endpoint."""

    def test_returns_not_linked_when_no_chat_id(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return is_linked=False when not linked."""
        response = client.get("/api/user/telegram", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_linked"] is False
        assert data["chat_id"] is None

    def test_returns_linked_with_masked_chat_id(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return is_linked=True with masked chat ID when linked."""
        test_user_in_db.telegram_chat_id = "123456789"
        api_db_session.commit()

        response = client.get("/api/user/telegram", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_linked"] is True
        assert data["chat_id"] == "12*****89"

    def test_requires_authentication(self, client: TestClient) -> None:
        """Should return 401 when not authenticated."""
        response = client.get("/api/user/telegram")

        assert response.status_code == 401


class TestGenerateTelegramLinkCode:
    """Tests for POST /api/user/telegram/link endpoint."""

    def test_generates_code(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should generate a link code for the user."""
        response = client.post("/api/user/telegram/link", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "code" in data
        assert len(data["code"]) == 8
        assert data["expires_in_seconds"] > 0
        assert "instructions" in data

    def test_fails_when_already_linked(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 400 when Telegram is already linked."""
        test_user_in_db.telegram_chat_id = "123456789"
        api_db_session.commit()

        response = client.post("/api/user/telegram/link", headers=api_auth_headers)

        assert response.status_code == 400
        assert "already linked" in response.json()["detail"]

    def test_requires_authentication(self, client: TestClient) -> None:
        """Should return 401 when not authenticated."""
        response = client.post("/api/user/telegram/link")

        assert response.status_code == 401


class TestUnlinkTelegram:
    """Tests for DELETE /api/user/telegram endpoint."""

    def test_unlinks_telegram(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should unlink Telegram from the user."""
        test_user_in_db.telegram_chat_id = "123456789"
        api_db_session.commit()

        response = client.delete("/api/user/telegram", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

        # Verify it's actually unlinked
        api_db_session.refresh(test_user_in_db)
        assert test_user_in_db.telegram_chat_id is None

    def test_fails_when_not_linked(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 400 when Telegram is not linked."""
        response = client.delete("/api/user/telegram", headers=api_auth_headers)

        assert response.status_code == 400
        assert "not linked" in response.json()["detail"]

    def test_requires_authentication(self, client: TestClient) -> None:
        """Should return 401 when not authenticated."""
        response = client.delete("/api/user/telegram")

        assert response.status_code == 401
