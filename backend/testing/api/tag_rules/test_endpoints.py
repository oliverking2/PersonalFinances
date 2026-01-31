"""Tests for tag rules API endpoints."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.models import Tag, TagRule


@pytest.fixture
def test_tag_in_db(api_db_session: Session, test_user_in_db: User) -> Tag:
    """Create a tag in the database."""
    tag = Tag(
        user_id=test_user_in_db.id,
        name="Groceries",
        colour="#00FF00",
    )
    api_db_session.add(tag)
    api_db_session.commit()
    return tag


@pytest.fixture
def test_rule_in_db(api_db_session: Session, test_user_in_db: User, test_tag_in_db: Tag) -> TagRule:
    """Create a tag rule in the database."""
    rule = TagRule(
        user_id=test_user_in_db.id,
        name="Tesco Rule",
        tag_id=test_tag_in_db.id,
        conditions={"merchant_contains": "tesco"},
        priority=1,
        enabled=True,
    )
    api_db_session.add(rule)
    api_db_session.commit()
    return rule


@pytest.fixture
def test_rules_in_db(
    api_db_session: Session, test_user_in_db: User, test_tag_in_db: Tag
) -> list[TagRule]:
    """Create multiple tag rules in the database."""
    rules = [
        TagRule(
            user_id=test_user_in_db.id,
            name="Tesco Rule",
            tag_id=test_tag_in_db.id,
            conditions={"merchant_contains": "tesco"},
            priority=1,
            enabled=True,
        ),
        TagRule(
            user_id=test_user_in_db.id,
            name="Sainsbury Rule",
            tag_id=test_tag_in_db.id,
            conditions={"merchant_contains": "sainsbury"},
            priority=2,
            enabled=True,
        ),
        TagRule(
            user_id=test_user_in_db.id,
            name="Disabled Rule",
            tag_id=test_tag_in_db.id,
            conditions={"merchant_contains": "asda"},
            priority=3,
            enabled=False,
        ),
    ]
    for rule in rules:
        api_db_session.add(rule)
    api_db_session.commit()
    return rules


class TestListRules:
    """Tests for GET /api/tag-rules endpoint."""

    def test_returns_rules_for_user(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_rules_in_db: list[TagRule],
    ) -> None:
        """Should return all rules for authenticated user."""
        response = client.get("/api/tag-rules", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["rules"]) == 3

    def test_filters_by_tag_id(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_rules_in_db: list[TagRule],
        test_tag_in_db: Tag,
    ) -> None:
        """Should filter rules by tag ID."""
        response = client.get(
            f"/api/tag-rules?tag_id={test_tag_in_db.id}",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert all(r["tag_id"] == str(test_tag_in_db.id) for r in data["rules"])

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Should return 401 without authentication."""
        response = client.get("/api/tag-rules")
        assert response.status_code == 401


class TestCreateRule:
    """Tests for POST /api/tag-rules endpoint."""

    def test_creates_rule(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_tag_in_db: Tag,
    ) -> None:
        """Should create a new tag rule."""
        response = client.post(
            "/api/tag-rules",
            headers=api_auth_headers,
            json={
                "name": "New Rule",
                "tag_id": str(test_tag_in_db.id),
                "conditions": {"merchant_contains": "test"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Rule"
        assert data["tag_id"] == str(test_tag_in_db.id)
        assert data["conditions"]["merchant_contains"] == "test"
        assert data["enabled"] is True

    def test_returns_400_for_invalid_tag(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 400 for invalid tag ID."""
        response = client.post(
            "/api/tag-rules",
            headers=api_auth_headers,
            json={
                "name": "Bad Rule",
                "tag_id": str(uuid4()),
                "conditions": {"merchant_contains": "test"},
            },
        )

        assert response.status_code == 400


class TestGetRule:
    """Tests for GET /api/tag-rules/{id} endpoint."""

    def test_returns_rule(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_rule_in_db: TagRule,
    ) -> None:
        """Should return rule by ID."""
        response = client.get(
            f"/api/tag-rules/{test_rule_in_db.id}",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_rule_in_db.id)
        assert data["name"] == "Tesco Rule"

    def test_returns_404_for_nonexistent(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for nonexistent rule."""
        response = client.get(
            f"/api/tag-rules/{uuid4()}",
            headers=api_auth_headers,
        )

        assert response.status_code == 404


class TestUpdateRule:
    """Tests for PUT /api/tag-rules/{id} endpoint."""

    def test_updates_rule_name(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_rule_in_db: TagRule,
    ) -> None:
        """Should update rule name."""
        response = client.put(
            f"/api/tag-rules/{test_rule_in_db.id}",
            headers=api_auth_headers,
            json={"name": "Updated Rule"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Rule"

    def test_updates_rule_conditions(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_rule_in_db: TagRule,
    ) -> None:
        """Should update rule conditions."""
        response = client.put(
            f"/api/tag-rules/{test_rule_in_db.id}",
            headers=api_auth_headers,
            json={"conditions": {"merchant_contains": "updated"}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["conditions"]["merchant_contains"] == "updated"

    def test_returns_404_for_nonexistent(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for nonexistent rule."""
        response = client.put(
            f"/api/tag-rules/{uuid4()}",
            headers=api_auth_headers,
            json={"name": "Updated"},
        )

        assert response.status_code == 404


class TestDeleteRule:
    """Tests for DELETE /api/tag-rules/{id} endpoint."""

    def test_deletes_rule(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_rule_in_db: TagRule,
    ) -> None:
        """Should delete rule."""
        response = client.delete(
            f"/api/tag-rules/{test_rule_in_db.id}",
            headers=api_auth_headers,
        )

        assert response.status_code == 204

    def test_returns_404_for_nonexistent(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for nonexistent rule."""
        response = client.delete(
            f"/api/tag-rules/{uuid4()}",
            headers=api_auth_headers,
        )

        assert response.status_code == 404


class TestReorderRules:
    """Tests for POST /api/tag-rules/reorder endpoint."""

    def test_reorders_rules(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_rules_in_db: list[TagRule],
    ) -> None:
        """Should reorder rules."""
        # Reverse the order
        new_order = [str(r.id) for r in reversed(test_rules_in_db)]
        response = client.post(
            "/api/tag-rules/reorder",
            headers=api_auth_headers,
            json={"rule_ids": new_order},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["rules"]) == 3
        # Rules should be reordered (first rule should have priority 0)
        assert data["rules"][0]["priority"] == 0


class TestApplyRules:
    """Tests for POST /api/tag-rules/apply endpoint."""

    def test_applies_rules(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_rules_in_db: list[TagRule],
    ) -> None:
        """Should apply rules and return count."""
        response = client.post(
            "/api/tag-rules/apply",
            headers=api_auth_headers,
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert "tagged_count" in data
