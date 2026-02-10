"""Agent service orchestrating the question → query → response pipeline."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from src.agent.guardrails import enforce_rate_limit, handle_empty_results
from src.agent.llm import QueryPlanError, generate_query_plan, generate_response
from src.agent.models import AgentResponse, QueryProvenanceResponse
from src.duckdb.semantic import InvalidQueryError, execute_semantic_query
from src.metadata.service import MetadataService

logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Raised when the agent fails to process a question."""


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Serialize a query result row to JSON-safe types.

    :param row: Row dictionary from DuckDB.
    :returns: JSON-serializable dictionary.
    """
    result: dict[str, Any] = {}
    for key, value in row.items():
        key_normalized = key.lower()
        if isinstance(value, date):
            result[key_normalized] = value.isoformat()
        elif isinstance(value, UUID):
            result[key_normalized] = str(value)
        elif isinstance(value, Decimal):
            result[key_normalized] = (
                int(value) if value == value.to_integral_value() else float(value)
            )
        else:
            result[key_normalized] = value
    return result


class AgentService:
    """Orchestrates the agent pipeline: question → query → response."""

    @staticmethod
    def ask(question: str, user_id: UUID) -> AgentResponse:
        """Process a natural language question.

        :param question: User's question.
        :param user_id: Authenticated user ID.
        :returns: AgentResponse with answer, data, and provenance.
        :raises AgentError: If the question cannot be processed.
        :raises RateLimitExceededError: If the user has exceeded the rate limit.
        """
        # 1. Rate limit
        enforce_rate_limit(user_id)

        # 2. Get schema context
        schema_summary = MetadataService.get_schema_summary()

        # 3. LLM Call 1: question → QuerySpec
        try:
            spec = generate_query_plan(question, schema_summary)
        except QueryPlanError as e:
            logger.warning(f"Query plan failed: user_id={user_id}, error={e}")
            raise AgentError(
                "I wasn't able to understand that question. Please try rephrasing."
            ) from e

        # 4. Execute query
        try:
            result = execute_semantic_query(spec, user_id)
        except InvalidQueryError as e:
            logger.warning(f"Query execution failed: user_id={user_id}, error={e}")
            raise AgentError(f"I couldn't run that query: {e}") from e

        # 5. Handle empty results
        if not result.data:
            empty_msg = handle_empty_results(question)
            provenance = QueryProvenanceResponse(
                dataset_name=result.provenance.dataset_name,
                friendly_name=result.provenance.friendly_name,
                measures_queried=result.provenance.measures_queried,
                dimensions_queried=result.provenance.dimensions_queried,
                filters_applied=result.provenance.filters_applied,
                row_count=0,
                query_duration_ms=result.provenance.query_duration_ms,
            )
            return AgentResponse(
                answer=empty_msg,
                provenance=provenance,
                data=[],
                chart_spec=None,
                suggestions=MetadataService.get_suggestions()[:3],
            )

        # 6. Serialize data rows
        serialized_data = [_serialize_row(row) for row in result.data]

        # 7. Build provenance summary for LLM
        provenance_summary = (
            f"Queried {result.provenance.friendly_name} "
            f"({result.provenance.dataset_name}): "
            f"measures={result.provenance.measures_queried}, "
            f"dimensions={result.provenance.dimensions_queried}"
        )
        if result.provenance.filters_applied:
            provenance_summary += f", filters={result.provenance.filters_applied}"

        # 8. LLM Call 2: results → narrative
        try:
            llm_response = generate_response(question, serialized_data, provenance_summary)
        except QueryPlanError:
            # Fallback: return raw data without narrative
            logger.warning(f"Response generation failed, returning raw data: user_id={user_id}")
            llm_response = {
                "answer": (
                    f"Here are the results from {result.provenance.friendly_name}. "
                    f"I found {result.provenance.row_count} rows of data."
                ),
                "chart_spec": None,
                "suggestions": MetadataService.get_suggestions()[:3],
            }

        # 9. Build response
        provenance = QueryProvenanceResponse(
            dataset_name=result.provenance.dataset_name,
            friendly_name=result.provenance.friendly_name,
            measures_queried=result.provenance.measures_queried,
            dimensions_queried=result.provenance.dimensions_queried,
            filters_applied=result.provenance.filters_applied,
            row_count=result.provenance.row_count,
            query_duration_ms=result.provenance.query_duration_ms,
        )

        return AgentResponse(
            answer=llm_response["answer"],
            provenance=provenance,
            data=serialized_data,
            chart_spec=llm_response.get("chart_spec"),
            suggestions=llm_response.get("suggestions", []),
        )
