"""Pydantic models for analytics endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# Dataset discovery models


class EnumFilterResponse(BaseModel):
    """An enum filter with predefined options."""

    name: str = Field(..., description="Column name in the dataset")
    label: str = Field(..., description="Display label for the filter")
    options: list[str] = Field(..., description="Allowed values")


class NumericFilterResponse(BaseModel):
    """A numeric filter for min/max range filtering."""

    name: str = Field(..., description="Column name in the dataset")
    label: str = Field(..., description="Display label for the filter")


class DatasetFiltersResponse(BaseModel):
    """Available filter columns for a dataset."""

    date_column: str | None = Field(default=None, description="Column name for date filtering")
    account_id_column: str | None = Field(
        default=None, description="Column name for account filtering"
    )
    tag_id_column: str | None = Field(default=None, description="Column name for tag filtering")
    enum_filters: list[EnumFilterResponse] = Field(
        default_factory=list, description="Enum filters with predefined options"
    )
    numeric_filters: list[NumericFilterResponse] = Field(
        default_factory=list, description="Numeric filters for range filtering"
    )


class DatasetColumnResponse(BaseModel):
    """Schema column for a dataset."""

    name: str = Field(..., description="Column name")
    description: str = Field(..., description="Column description")
    data_type: str | None = Field(None, description="Data type")


class DatasetResponse(BaseModel):
    """An analytics dataset available for querying."""

    id: UUID = Field(..., description="Dataset identifier (UUID)")
    dataset_name: str = Field(..., description="dbt model name (e.g., fct_transactions)")
    friendly_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Dataset description")
    group: str = Field(..., description="Dataset group (facts, dimensions, aggregations)")
    time_grain: str | None = Field(None, description="Time grain for aggregations (day, month)")
    filters: DatasetFiltersResponse = Field(
        default_factory=lambda: DatasetFiltersResponse(),
        description="Available filter columns",
    )


class DatasetListResponse(BaseModel):
    """Response for listing available datasets."""

    datasets: list[DatasetResponse] = Field(..., description="List of datasets")
    total: int = Field(..., description="Total count")


class DatasetSchemaResponse(DatasetResponse):
    """Dataset with full schema information."""

    columns: list[DatasetColumnResponse] = Field(..., description="Column definitions")


# Generic dataset query models


class DatasetQueryResponse(BaseModel):
    """Response for querying a dataset."""

    dataset_id: UUID = Field(..., description="Dataset identifier (UUID)")
    dataset_name: str = Field(..., description="dbt model name")
    rows: list[dict[str, Any]] = Field(..., description="Query result rows")
    row_count: int = Field(..., description="Number of rows returned")
    filters_applied: dict[str, Any] = Field(
        default_factory=dict, description="Filters that were applied"
    )


# Refresh models


class RefreshResponse(BaseModel):
    """Response for analytics refresh trigger."""

    job_id: str = Field(..., description="Job UUID for tracking")
    dagster_run_id: str | None = Field(None, description="Job run ID if available")
    status: str = Field(..., description="Job status")
    message: str = Field(..., description="Status message")


# Analytics status


class AnalyticsStatusResponse(BaseModel):
    """Response for analytics system status."""

    duckdb_available: bool = Field(..., description="Whether DuckDB database is accessible")
    manifest_available: bool = Field(..., description="Whether dbt manifest is available")
    dataset_count: int = Field(..., description="Number of available datasets")
    last_refresh: datetime | None = Field(None, description="Last successful refresh time")
