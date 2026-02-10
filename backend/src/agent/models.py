"""Pydantic models for agent responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class QueryProvenanceResponse(BaseModel):
    """Provenance metadata about how a query result was produced."""

    dataset_name: str
    friendly_name: str
    measures_queried: list[str]
    dimensions_queried: list[str]
    filters_applied: list[str]
    row_count: int
    query_duration_ms: float


class ChartSeries(BaseModel):
    """A single data series for a chart."""

    key: str
    label: str


class ChartSpec(BaseModel):
    """Specification for rendering a chart from the query results."""

    chart_type: str  # line, bar, pie, area
    x_axis: str
    y_axis: str
    series: list[ChartSeries] | None = None
    title: str | None = None


class AgentResponse(BaseModel):
    """Full response from the agent API."""

    answer: str
    provenance: QueryProvenanceResponse
    data: list[dict[str, Any]]
    chart_spec: ChartSpec | None = None
    suggestions: list[str]
