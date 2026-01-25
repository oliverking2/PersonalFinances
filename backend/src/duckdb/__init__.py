"""DuckDB analytics client.

This module provides read-only access to the DuckDB analytics database
built by dbt from PostgreSQL source data.
"""

from src.duckdb.client import check_connection, execute_query, get_connection
from src.duckdb.manifest import (
    Dataset,
    DatasetColumn,
    DatasetFilters,
    get_dataset_schema,
    get_datasets,
)
from src.duckdb.queries import build_dataset_query

__all__ = [
    "Dataset",
    "DatasetColumn",
    "DatasetFilters",
    "build_dataset_query",
    "check_connection",
    "execute_query",
    "get_connection",
    "get_dataset_schema",
    "get_datasets",
]
