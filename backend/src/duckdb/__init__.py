"""DuckDB analytics client.

This module provides read-only access to the DuckDB analytics database
built by dbt from PostgreSQL source data.
"""

from src.duckdb.client import check_connection, execute_query, get_connection
from src.duckdb.manifest import (
    Dataset,
    DatasetColumn,
    DatasetFilters,
    Dimension,
    Measure,
    SemanticDataset,
    get_all_sample_questions,
    get_dataset_schema,
    get_datasets,
    get_semantic_dataset,
    get_semantic_datasets,
)
from src.duckdb.queries import build_dataset_query
from src.duckdb.semantic import (
    InvalidQueryError,
    QueryFilter,
    QueryProvenance,
    QueryResult,
    QuerySpec,
    build_semantic_query,
    execute_semantic_query,
    validate_query_spec,
)

__all__ = [
    "Dataset",
    "DatasetColumn",
    "DatasetFilters",
    "Dimension",
    "InvalidQueryError",
    "Measure",
    "QueryFilter",
    "QueryProvenance",
    "QueryResult",
    "QuerySpec",
    "SemanticDataset",
    "build_dataset_query",
    "build_semantic_query",
    "check_connection",
    "execute_query",
    "execute_semantic_query",
    "get_all_sample_questions",
    "get_connection",
    "get_dataset_schema",
    "get_datasets",
    "get_semantic_dataset",
    "get_semantic_datasets",
    "validate_query_spec",
]
