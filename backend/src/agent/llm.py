"""LLM wrapper for Bedrock API calls."""

from __future__ import annotations

import json
import logging
import os
from datetime import date
from typing import Any

import boto3
from mypy_boto3_bedrock_runtime import BedrockRuntimeClient

from src.agent.models import ChartSeries, ChartSpec
from src.agent.prompts import QUERY_PLANNER_SYSTEM, RESPONSE_GENERATOR_SYSTEM
from src.duckdb.semantic import QueryFilter, QuerySpec

logger = logging.getLogger(__name__)

# Default model ID for Bedrock
_DEFAULT_MODEL_ID = "us.anthropic.claude-sonnet-4-5-v1-0"

# Maximum rows to include in the response generation prompt
_MAX_RESPONSE_ROWS = 50


class QueryPlanError(Exception):
    """Raised when the LLM fails to produce a valid query plan."""


# Tool schema for Call 1: question → QuerySpec
_QUERY_TOOL = {
    "toolSpec": {
        "name": "build_query",
        "description": "Build a structured query from the user's question.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "dataset": {
                        "type": "string",
                        "description": "Dataset name to query (e.g., fct_transactions).",
                    },
                    "measures": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of measure names to aggregate.",
                    },
                    "dimensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of dimension names to group by.",
                    },
                    "filters": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "dimension": {"type": "string"},
                                "operator": {
                                    "type": "string",
                                    "enum": [
                                        "eq",
                                        "neq",
                                        "gt",
                                        "gte",
                                        "lt",
                                        "lte",
                                        "in",
                                        "not_in",
                                        "between",
                                    ],
                                },
                                "value": {
                                    "description": (
                                        "Filter value. String for eq/neq/gt/gte/lt/lte, "
                                        "array for in/not_in/between."
                                    ),
                                },
                            },
                            "required": ["dimension", "operator", "value"],
                        },
                        "description": "Filters to apply.",
                    },
                    "time_granularity": {
                        "type": "string",
                        "enum": ["day", "week", "month", "quarter", "year"],
                        "description": "Time granularity for date dimensions.",
                    },
                    "order_by": {
                        "type": "string",
                        "description": "Column to sort by (must be a queried measure or dimension).",
                    },
                    "order_direction": {
                        "type": "string",
                        "enum": ["ASC", "DESC"],
                        "description": "Sort direction.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum rows to return.",
                    },
                },
                "required": ["dataset", "measures"],
            },
        },
    },
}

# Tool schema for Call 2: results → narrative response
_RESPONSE_TOOL = {
    "toolSpec": {
        "name": "format_response",
        "description": "Format the query results into a narrative response.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "Natural language answer to the user's question.",
                    },
                    "chart_type": {
                        "type": "string",
                        "enum": ["line", "bar", "pie", "area"],
                        "description": "Chart type for visualisation (optional).",
                    },
                    "chart_x_axis": {
                        "type": "string",
                        "description": "Column name for x-axis.",
                    },
                    "chart_y_axis": {
                        "type": "string",
                        "description": "Column name for y-axis.",
                    },
                    "chart_title": {
                        "type": "string",
                        "description": "Chart title.",
                    },
                    "chart_series": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "key": {"type": "string"},
                                "label": {"type": "string"},
                            },
                            "required": ["key", "label"],
                        },
                        "description": "Data series for the chart.",
                    },
                    "suggestions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "2-3 follow-up questions the user might ask.",
                    },
                },
                "required": ["answer", "suggestions"],
            },
        },
    },
}


def _get_client() -> BedrockRuntimeClient:
    """Create a Bedrock Runtime client.

    :returns: boto3 Bedrock Runtime client.
    """
    region = os.environ.get("AWS_BEDROCK_REGION", "us-east-1")
    return boto3.client("bedrock-runtime", region_name=region)


def _get_model_id() -> str:
    """Get the configured Bedrock model ID.

    :returns: Model ID string.
    """
    return os.environ.get("BEDROCK_MODEL_ID", _DEFAULT_MODEL_ID)


def _extract_tool_input(response: Any, tool_name: str) -> dict[str, Any]:
    """Extract tool input from a Bedrock converse response.

    :param response: Bedrock converse API response.
    :param tool_name: Expected tool name.
    :returns: Tool input dictionary.
    :raises QueryPlanError: If the response doesn't contain the expected tool use.
    """
    output = response.get("output", {})
    message = output.get("message", {})
    content_blocks = message.get("content", [])

    for block in content_blocks:
        if "toolUse" in block:
            tool_use = block["toolUse"]
            if tool_use.get("name") == tool_name:
                return tool_use.get("input", {})

    raise QueryPlanError(f"LLM did not call the {tool_name} tool")


def generate_query_plan(question: str, schema_summary: str) -> QuerySpec:
    """Use the LLM to translate a question into a QuerySpec.

    :param question: User's natural language question.
    :param schema_summary: Compact schema description for context.
    :returns: QuerySpec ready for execution.
    :raises QueryPlanError: If the LLM fails to produce a valid plan.
    """
    system_prompt = QUERY_PLANNER_SYSTEM.format(
        schema_summary=schema_summary,
        today=date.today().isoformat(),
    )

    client = _get_client()

    try:
        response = client.converse(
            modelId=_get_model_id(),
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": [{"text": question}]}],
            toolConfig={
                "tools": [_QUERY_TOOL],  # type: ignore[list-item]
                "toolChoice": {"tool": {"name": "build_query"}},
            },
        )
    except Exception as e:
        logger.exception(f"Bedrock API call failed: {e}")
        raise QueryPlanError(f"Failed to generate query plan: {e}") from e

    tool_input = _extract_tool_input(response, "build_query")

    logger.info(
        f"Query plan generated: dataset={tool_input.get('dataset')}, "
        f"measures={tool_input.get('measures')}"
    )

    # Parse filters
    filters = []
    for f in tool_input.get("filters", []):
        filters.append(
            QueryFilter(
                dimension=f["dimension"],
                operator=f["operator"],
                value=f["value"],
            )
        )

    return QuerySpec(
        dataset=tool_input["dataset"],
        measures=tool_input["measures"],
        dimensions=tool_input.get("dimensions", []),
        filters=filters,
        time_granularity=tool_input.get("time_granularity"),
        order_by=tool_input.get("order_by"),
        order_direction=tool_input.get("order_direction", "ASC"),
        limit=tool_input.get("limit", 1000),
    )


def generate_response(
    question: str,
    data: list[dict[str, Any]],
    provenance_summary: str,
) -> dict[str, Any]:
    """Use the LLM to generate a narrative response from query results.

    :param question: User's original question.
    :param data: Query result rows (truncated to _MAX_RESPONSE_ROWS).
    :param provenance_summary: Human-readable summary of what was queried.
    :returns: Dict with answer, optional chart_spec, and suggestions.
    :raises QueryPlanError: If the LLM fails to produce a valid response.
    """
    truncated_data = data[:_MAX_RESPONSE_ROWS]
    data_text = json.dumps(truncated_data, default=str)

    user_prompt = (
        f"Question: {question}\n\n"
        f"Query details: {provenance_summary}\n\n"
        f"Results ({len(data)} rows"
        f"{', showing first ' + str(_MAX_RESPONSE_ROWS) if len(data) > _MAX_RESPONSE_ROWS else ''}"
        f"):\n{data_text}"
    )

    client = _get_client()

    try:
        response = client.converse(
            modelId=_get_model_id(),
            system=[{"text": RESPONSE_GENERATOR_SYSTEM}],
            messages=[{"role": "user", "content": [{"text": user_prompt}]}],
            toolConfig={
                "tools": [_RESPONSE_TOOL],  # type: ignore[list-item]
                "toolChoice": {"tool": {"name": "format_response"}},
            },
        )
    except Exception as e:
        logger.exception(f"Bedrock response generation failed: {e}")
        raise QueryPlanError(f"Failed to generate response: {e}") from e

    tool_input = _extract_tool_input(response, "format_response")

    # Build chart spec if provided
    chart_spec = None
    if tool_input.get("chart_type") and tool_input.get("chart_x_axis"):
        series = None
        if tool_input.get("chart_series"):
            series = [
                ChartSeries(key=s["key"], label=s["label"]) for s in tool_input["chart_series"]
            ]
        chart_spec = ChartSpec(
            chart_type=tool_input["chart_type"],
            x_axis=tool_input["chart_x_axis"],
            y_axis=tool_input.get("chart_y_axis", ""),
            series=series,
            title=tool_input.get("chart_title"),
        )

    return {
        "answer": tool_input["answer"],
        "chart_spec": chart_spec,
        "suggestions": tool_input.get("suggestions", []),
    }
