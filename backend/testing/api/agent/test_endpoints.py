"""Tests for agent API endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.agent.guardrails import RateLimitExceededError
from src.agent.models import AgentResponse, QueryProvenanceResponse
from src.agent.service import AgentError
from src.postgres.auth.models import User


class TestAskEndpoint:
    """Tests for POST /api/agent/ask."""

    def test_requires_authentication(self, client: TestClient) -> None:
        """Should require authentication."""
        response = client.post("/api/agent/ask", json={"question": "How much?"})

        assert response.status_code == 401

    def test_validates_question_min_length(
        self,
        client: TestClient,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should reject questions shorter than 3 characters."""
        response = client.post(
            "/api/agent/ask",
            json={"question": "ab"},
            headers=api_auth_headers,
        )

        assert response.status_code == 422

    def test_validates_question_max_length(
        self,
        client: TestClient,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should reject questions longer than 500 characters."""
        response = client.post(
            "/api/agent/ask",
            json={"question": "x" * 501},
            headers=api_auth_headers,
        )

        assert response.status_code == 422

    @patch("src.api.agent.endpoints.AgentService.ask")
    def test_returns_agent_response(
        self,
        mock_ask: MagicMock,
        client: TestClient,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return a successful agent response."""
        mock_ask.return_value = AgentResponse(
            answer="You spent £500.",
            provenance=QueryProvenanceResponse(
                dataset_name="fct_transactions",
                friendly_name="Transactions",
                measures_queried=["total_amount"],
                dimensions_queried=[],
                filters_applied=[],
                row_count=1,
                query_duration_ms=10.0,
            ),
            data=[{"total_amount": 500}],
            chart_spec=None,
            suggestions=["What about next month?"],
        )

        response = client.post(
            "/api/agent/ask",
            json={"question": "How much did I spend?"},
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "You spent £500."
        assert data["provenance"]["dataset_name"] == "fct_transactions"
        assert data["data"] == [{"total_amount": 500}]
        assert len(data["suggestions"]) == 1

    @patch("src.api.agent.endpoints.AgentService.ask")
    def test_returns_429_on_rate_limit(
        self,
        mock_ask: MagicMock,
        client: TestClient,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 429 when rate limit is exceeded."""
        mock_ask.side_effect = RateLimitExceededError("Rate limit exceeded.")

        response = client.post(
            "/api/agent/ask",
            json={"question": "How much did I spend?"},
            headers=api_auth_headers,
        )

        assert response.status_code == 429
        assert "rate limit" in response.json()["detail"].lower()

    @patch("src.api.agent.endpoints.AgentService.ask")
    def test_returns_400_on_agent_error(
        self,
        mock_ask: MagicMock,
        client: TestClient,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 400 when agent cannot process the question."""
        mock_ask.side_effect = AgentError("I wasn't able to understand that question.")

        response = client.post(
            "/api/agent/ask",
            json={"question": "gibberish question here"},
            headers=api_auth_headers,
        )

        assert response.status_code == 400
        assert "understand" in response.json()["detail"].lower()

    @patch("src.api.agent.endpoints.AgentService.ask")
    def test_returns_500_on_unexpected_error(
        self,
        mock_ask: MagicMock,
        client: TestClient,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 500 on unexpected errors."""
        mock_ask.side_effect = RuntimeError("Something broke")

        response = client.post(
            "/api/agent/ask",
            json={"question": "How much did I spend?"},
            headers=api_auth_headers,
        )

        assert response.status_code == 500


class TestSuggestionsEndpoint:
    """Tests for GET /api/agent/suggestions."""

    def test_requires_authentication(self, client: TestClient) -> None:
        """Should require authentication."""
        response = client.get("/api/agent/suggestions")

        assert response.status_code == 401

    @patch("src.api.agent.endpoints.MetadataService.get_suggestions")
    def test_returns_suggestions(
        self,
        mock_suggestions: MagicMock,
        client: TestClient,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return sample questions."""
        mock_suggestions.return_value = ["How much did I spend?", "What are my top categories?"]

        response = client.get("/api/agent/suggestions", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["suggestions"]) == 2

    @patch("src.api.agent.endpoints.MetadataService.get_suggestions")
    def test_returns_empty_suggestions(
        self,
        mock_suggestions: MagicMock,
        client: TestClient,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return empty list when no suggestions exist."""
        mock_suggestions.return_value = []

        response = client.get("/api/agent/suggestions", headers=api_auth_headers)

        assert response.status_code == 200
        assert response.json()["suggestions"] == []
