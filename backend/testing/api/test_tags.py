"""Tests for tag API endpoints."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.operations.tags import create_tag


class TestListTags:
    """Tests for GET /api/tags endpoint."""

    def test_returns_empty_list_when_no_tags(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return empty list when user has no tags."""
        response = client.get("/api/tags", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["tags"] == []
        assert data["total"] == 0

    def test_returns_user_tags(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return all tags for the user."""
        create_tag(api_db_session, test_user_in_db.id, "Groceries", "#10B981")
        create_tag(api_db_session, test_user_in_db.id, "Entertainment")
        api_db_session.commit()

        response = client.get("/api/tags", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        names = {t["name"] for t in data["tags"]}
        assert names == {"Groceries", "Entertainment"}

    def test_requires_authentication(self, client: TestClient) -> None:
        """Should require authentication."""
        response = client.get("/api/tags")
        assert response.status_code == 401


class TestCreateTag:
    """Tests for POST /api/tags endpoint."""

    def test_creates_tag(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should create a new tag."""
        response = client.post(
            "/api/tags",
            headers=api_auth_headers,
            json={"name": "Groceries", "colour": "#10B981"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Groceries"
        assert data["colour"] == "#10B981"
        assert data["usage_count"] == 0

    def test_creates_tag_without_colour(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should create tag without colour."""
        response = client.post(
            "/api/tags",
            headers=api_auth_headers,
            json={"name": "Test"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["colour"] is None

    def test_rejects_duplicate_name(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should reject duplicate tag names."""
        create_tag(api_db_session, test_user_in_db.id, "Groceries")
        api_db_session.commit()

        response = client.post(
            "/api/tags",
            headers=api_auth_headers,
            json={"name": "Groceries"},
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_validates_colour_format(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should validate colour is valid hex format."""
        response = client.post(
            "/api/tags",
            headers=api_auth_headers,
            json={"name": "Test", "colour": "invalid"},
        )

        assert response.status_code == 422  # Validation error


class TestGetTag:
    """Tests for GET /api/tags/{tag_id} endpoint."""

    def test_returns_tag(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return tag by ID."""
        tag = create_tag(api_db_session, test_user_in_db.id, "Test", "#10B981")
        api_db_session.commit()

        response = client.get(f"/api/tags/{tag.id}", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test"
        assert data["colour"] == "#10B981"

    def test_returns_404_for_not_found(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for non-existent tag."""
        response = client.get(
            "/api/tags/00000000-0000-0000-0000-000000000000",
            headers=api_auth_headers,
        )

        assert response.status_code == 404


class TestUpdateTag:
    """Tests for PUT /api/tags/{tag_id} endpoint."""

    def test_updates_tag_name(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should update tag name."""
        tag = create_tag(api_db_session, test_user_in_db.id, "Old Name")
        api_db_session.commit()

        response = client.put(
            f"/api/tags/{tag.id}",
            headers=api_auth_headers,
            json={"name": "New Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"

    def test_updates_tag_colour(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should update tag colour."""
        tag = create_tag(api_db_session, test_user_in_db.id, "Test", "#000000")
        api_db_session.commit()

        response = client.put(
            f"/api/tags/{tag.id}",
            headers=api_auth_headers,
            json={"colour": "#FFFFFF"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["colour"] == "#FFFFFF"


class TestDeleteTag:
    """Tests for DELETE /api/tags/{tag_id} endpoint."""

    def test_deletes_tag(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should delete tag."""
        tag = create_tag(api_db_session, test_user_in_db.id, "Test")
        api_db_session.commit()

        response = client.delete(f"/api/tags/{tag.id}", headers=api_auth_headers)

        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/api/tags/{tag.id}", headers=api_auth_headers)
        assert get_response.status_code == 404

    def test_returns_404_for_not_found(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for non-existent tag."""
        response = client.delete(
            "/api/tags/00000000-0000-0000-0000-000000000000",
            headers=api_auth_headers,
        )

        assert response.status_code == 404
