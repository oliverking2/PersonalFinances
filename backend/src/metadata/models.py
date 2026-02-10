"""Pydantic models for metadata service output."""

from __future__ import annotations

from pydantic import BaseModel


class MeasureSummary(BaseModel):
    """A measure available in a dataset, without SQL expressions."""

    name: str
    agg: str
    description: str


class DimensionSummary(BaseModel):
    """A dimension available in a dataset, without SQL expressions."""

    name: str
    type: str
    description: str


class DatasetSummary(BaseModel):
    """Summary of a single dataset for LLM context."""

    name: str
    friendly_name: str
    description: str
    time_grain: str | None
    measures: list[MeasureSummary]
    dimensions: list[DimensionSummary]
    sample_questions: list[str]


class SchemaContext(BaseModel):
    """Full schema context for the LLM system prompt."""

    datasets: list[DatasetSummary]
    total_measures: int
    total_dimensions: int
