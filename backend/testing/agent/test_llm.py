"""Tests for LLM wrapper functions."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.agent.llm import (
    QueryPlanError,
    _extract_tool_input,
    generate_query_plan,
    generate_response,
)


def _make_converse_response(tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    """Build a mock Bedrock converse response with tool use."""
    return {
        "output": {
            "message": {
                "content": [
                    {
                        "toolUse": {
                            "toolUseId": "test-id",
                            "name": tool_name,
                            "input": tool_input,
                        }
                    }
                ]
            }
        }
    }


class TestExtractToolInput:
    """Tests for _extract_tool_input."""

    def test_extracts_matching_tool_input(self) -> None:
        """Should extract input when tool name matches."""
        response = _make_converse_response("build_query", {"dataset": "fct_test"})

        result = _extract_tool_input(response, "build_query")

        assert result == {"dataset": "fct_test"}

    def test_raises_when_tool_not_found(self) -> None:
        """Should raise QueryPlanError when tool is not in response."""
        response = _make_converse_response("other_tool", {})

        with pytest.raises(QueryPlanError, match="did not call"):
            _extract_tool_input(response, "build_query")

    def test_raises_when_no_content(self) -> None:
        """Should raise QueryPlanError when response has no content."""
        response: dict[str, Any] = {"output": {"message": {"content": []}}}

        with pytest.raises(QueryPlanError, match="did not call"):
            _extract_tool_input(response, "build_query")

    def test_handles_text_content_blocks(self) -> None:
        """Should skip text blocks and find tool use."""
        response: dict[str, Any] = {
            "output": {
                "message": {
                    "content": [
                        {"text": "Thinking..."},
                        {
                            "toolUse": {
                                "toolUseId": "test",
                                "name": "build_query",
                                "input": {"dataset": "fct_x"},
                            }
                        },
                    ]
                }
            }
        }

        result = _extract_tool_input(response, "build_query")

        assert result["dataset"] == "fct_x"


class TestGenerateQueryPlan:
    """Tests for generate_query_plan."""

    @patch("src.agent.llm._get_client")
    def test_returns_query_spec(self, mock_get_client: MagicMock) -> None:
        """Should parse tool output into a QuerySpec."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.converse.return_value = _make_converse_response(
            "build_query",
            {
                "dataset": "fct_transactions",
                "measures": ["total_amount"],
                "dimensions": ["period"],
                "time_granularity": "month",
                "order_by": "period",
                "order_direction": "ASC",
                "limit": 12,
            },
        )

        spec = generate_query_plan("How much did I spend?", "schema text")

        assert spec.dataset == "fct_transactions"
        assert spec.measures == ["total_amount"]
        assert spec.dimensions == ["period"]
        assert spec.time_granularity == "month"
        assert spec.order_by == "period"
        assert spec.order_direction == "ASC"
        assert spec.limit == 12

    @patch("src.agent.llm._get_client")
    def test_parses_filters(self, mock_get_client: MagicMock) -> None:
        """Should parse filter objects into QueryFilter dataclasses."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.converse.return_value = _make_converse_response(
            "build_query",
            {
                "dataset": "fct_transactions",
                "measures": ["total_amount"],
                "filters": [
                    {
                        "dimension": "period",
                        "operator": "between",
                        "value": ["2025-01-01", "2025-01-31"],
                    },
                ],
            },
        )

        spec = generate_query_plan("Spending last month", "schema")

        assert len(spec.filters) == 1
        assert spec.filters[0].dimension == "period"
        assert spec.filters[0].operator == "between"
        assert spec.filters[0].value == ["2025-01-01", "2025-01-31"]

    @patch("src.agent.llm._get_client")
    def test_raises_on_api_error(self, mock_get_client: MagicMock) -> None:
        """Should raise QueryPlanError when Bedrock API call fails."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.converse.side_effect = Exception("API unavailable")

        with pytest.raises(QueryPlanError, match="Failed to generate"):
            generate_query_plan("test question", "schema")

    @patch("src.agent.llm._get_client")
    def test_uses_defaults_for_missing_fields(self, mock_get_client: MagicMock) -> None:
        """Should use defaults when optional fields are missing."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.converse.return_value = _make_converse_response(
            "build_query",
            {"dataset": "fct_test", "measures": ["count"]},
        )

        spec = generate_query_plan("How many?", "schema")

        assert spec.dimensions == []
        assert spec.filters == []
        assert spec.time_granularity is None
        assert spec.order_by is None
        assert spec.order_direction == "ASC"
        assert spec.limit == 1000


class TestGenerateResponse:
    """Tests for generate_response."""

    @patch("src.agent.llm._get_client")
    def test_returns_answer_and_suggestions(self, mock_get_client: MagicMock) -> None:
        """Should parse narrative answer and suggestions."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.converse.return_value = _make_converse_response(
            "format_response",
            {
                "answer": "You spent £500 last month.",
                "suggestions": ["How about this month?", "Breakdown by category?"],
            },
        )

        result = generate_response(
            "How much?",
            [{"total": 500}],
            "fct_transactions: measures=[total]",
        )

        assert result["answer"] == "You spent £500 last month."
        assert len(result["suggestions"]) == 2
        assert result["chart_spec"] is None

    @patch("src.agent.llm._get_client")
    def test_returns_chart_spec_when_provided(self, mock_get_client: MagicMock) -> None:
        """Should build ChartSpec when chart fields are present."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.converse.return_value = _make_converse_response(
            "format_response",
            {
                "answer": "Here's your spending over time.",
                "chart_type": "line",
                "chart_x_axis": "period",
                "chart_y_axis": "total",
                "chart_title": "Monthly Spending",
                "chart_series": [{"key": "total", "label": "Spending"}],
                "suggestions": ["Next question?"],
            },
        )

        result = generate_response("Show trend", [{"period": "2025-01", "total": 500}], "summary")

        assert result["chart_spec"] is not None
        assert result["chart_spec"].chart_type == "line"
        assert result["chart_spec"].x_axis == "period"
        assert result["chart_spec"].y_axis == "total"
        assert result["chart_spec"].title == "Monthly Spending"
        assert len(result["chart_spec"].series) == 1

    @patch("src.agent.llm._get_client")
    def test_raises_on_api_error(self, mock_get_client: MagicMock) -> None:
        """Should raise QueryPlanError when Bedrock API call fails."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.converse.side_effect = Exception("API down")

        with pytest.raises(QueryPlanError, match="Failed to generate"):
            generate_response("question", [{"x": 1}], "summary")
