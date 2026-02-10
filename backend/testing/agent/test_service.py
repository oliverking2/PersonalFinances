"""Tests for the agent service orchestration."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.agent.guardrails import RateLimitExceededError, reset_rate_limit_store
from src.agent.llm import QueryPlanError
from src.agent.models import ChartSpec
from src.agent.service import AgentError, AgentService
from src.duckdb.semantic import InvalidQueryError, QueryProvenance, QueryResult, QuerySpec


@pytest.fixture(autouse=True)
def _clean_rate_limit() -> None:
    """Reset rate limit between tests."""
    reset_rate_limit_store()


def _make_query_result(
    data: list[dict[str, Any]] | None = None,
    dataset_name: str = "fct_transactions",
) -> QueryResult:
    """Build a minimal QueryResult for testing."""
    if data is None:
        data = [{"total_amount": 500, "period": "2025-01"}]
    return QueryResult(
        data=data,
        provenance=QueryProvenance(
            dataset_name=dataset_name,
            friendly_name="Transactions",
            measures_queried=["total_amount"],
            dimensions_queried=["period"],
            filters_applied=[],
            row_count=len(data),
            query_duration_ms=12.5,
        ),
    )


def _make_query_spec() -> QuerySpec:
    """Build a minimal QuerySpec for testing."""
    return QuerySpec(dataset="fct_transactions", measures=["total_amount"])


class TestAgentServiceAsk:
    """Tests for AgentService.ask."""

    @patch("src.agent.service.generate_response")
    @patch("src.agent.service.execute_semantic_query")
    @patch("src.agent.service.generate_query_plan")
    @patch("src.agent.service.MetadataService.get_schema_summary")
    def test_returns_full_response(
        self,
        mock_schema: MagicMock,
        mock_plan: MagicMock,
        mock_execute: MagicMock,
        mock_response: MagicMock,
    ) -> None:
        """Should orchestrate the full pipeline and return AgentResponse."""
        mock_schema.return_value = "schema text"
        mock_plan.return_value = _make_query_spec()
        mock_execute.return_value = _make_query_result()
        mock_response.return_value = {
            "answer": "You spent £500.",
            "chart_spec": None,
            "suggestions": ["What about this month?"],
        }

        result = AgentService.ask("How much did I spend?", uuid4())

        assert result.answer == "You spent £500."
        assert result.provenance.dataset_name == "fct_transactions"
        assert len(result.data) == 1
        assert result.suggestions == ["What about this month?"]

    @patch("src.agent.service.enforce_rate_limit")
    def test_propagates_rate_limit_error(self, mock_rate_limit: MagicMock) -> None:
        """Should propagate RateLimitExceededError."""
        mock_rate_limit.side_effect = RateLimitExceededError("Exceeded")

        with pytest.raises(RateLimitExceededError):
            AgentService.ask("test", uuid4())

    @patch("src.agent.service.MetadataService.get_schema_summary")
    @patch("src.agent.service.generate_query_plan")
    def test_raises_agent_error_on_plan_failure(
        self, mock_plan: MagicMock, mock_schema: MagicMock
    ) -> None:
        """Should raise AgentError when query planning fails."""
        mock_schema.return_value = "schema"
        mock_plan.side_effect = QueryPlanError("LLM failed")

        with pytest.raises(AgentError, match="wasn't able to understand"):
            AgentService.ask("nonsense", uuid4())

    @patch("src.agent.service.execute_semantic_query")
    @patch("src.agent.service.generate_query_plan")
    @patch("src.agent.service.MetadataService.get_schema_summary")
    def test_raises_agent_error_on_invalid_query(
        self, mock_schema: MagicMock, mock_plan: MagicMock, mock_execute: MagicMock
    ) -> None:
        """Should raise AgentError when query execution fails."""
        mock_schema.return_value = "schema"
        mock_plan.return_value = _make_query_spec()
        mock_execute.side_effect = InvalidQueryError("Unknown measure")

        with pytest.raises(AgentError, match="couldn't run that query"):
            AgentService.ask("bad query", uuid4())

    @patch("src.agent.service.MetadataService.get_suggestions")
    @patch("src.agent.service.execute_semantic_query")
    @patch("src.agent.service.generate_query_plan")
    @patch("src.agent.service.MetadataService.get_schema_summary")
    def test_handles_empty_results(
        self,
        mock_schema: MagicMock,
        mock_plan: MagicMock,
        mock_execute: MagicMock,
        mock_suggestions: MagicMock,
    ) -> None:
        """Should return a friendly message when no data is found."""
        mock_schema.return_value = "schema"
        mock_plan.return_value = _make_query_spec()
        mock_execute.return_value = _make_query_result(data=[])
        mock_suggestions.return_value = ["Q1", "Q2", "Q3", "Q4"]

        result = AgentService.ask("spending in 2099", uuid4())

        assert "no data" in result.answer.lower() or "wasn't able to find" in result.answer.lower()
        assert result.data == []
        assert result.provenance.row_count == 0
        assert len(result.suggestions) == 3

    @patch("src.agent.service.MetadataService.get_suggestions")
    @patch("src.agent.service.generate_response")
    @patch("src.agent.service.execute_semantic_query")
    @patch("src.agent.service.generate_query_plan")
    @patch("src.agent.service.MetadataService.get_schema_summary")
    def test_fallback_on_response_generation_failure(
        self,
        mock_schema: MagicMock,
        mock_plan: MagicMock,
        mock_execute: MagicMock,
        mock_response: MagicMock,
        mock_suggestions: MagicMock,
    ) -> None:
        """Should return raw data when response generation fails."""
        mock_schema.return_value = "schema"
        mock_plan.return_value = _make_query_spec()
        mock_execute.return_value = _make_query_result()
        mock_response.side_effect = QueryPlanError("LLM down")
        mock_suggestions.return_value = ["S1", "S2", "S3"]

        result = AgentService.ask("How much?", uuid4())

        assert "Transactions" in result.answer
        assert len(result.data) == 1
        assert result.chart_spec is None

    @patch("src.agent.service.generate_response")
    @patch("src.agent.service.execute_semantic_query")
    @patch("src.agent.service.generate_query_plan")
    @patch("src.agent.service.MetadataService.get_schema_summary")
    def test_includes_chart_spec_from_llm(
        self,
        mock_schema: MagicMock,
        mock_plan: MagicMock,
        mock_execute: MagicMock,
        mock_response: MagicMock,
    ) -> None:
        """Should include chart spec when LLM suggests one."""
        mock_schema.return_value = "schema"
        mock_plan.return_value = _make_query_spec()
        mock_execute.return_value = _make_query_result()
        mock_response.return_value = {
            "answer": "Trend data",
            "chart_spec": ChartSpec(chart_type="line", x_axis="period", y_axis="total_amount"),
            "suggestions": [],
        }

        result = AgentService.ask("Show trend", uuid4())

        assert result.chart_spec is not None
        assert result.chart_spec.chart_type == "line"
