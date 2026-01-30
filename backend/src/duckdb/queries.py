"""Parameterized query builders for analytics endpoints.

All queries filter by user_id to ensure data isolation.
Uses named parameters ($name) for safe parameterization.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from src.duckdb.manifest import Dataset


def _format_uuid_list(uuids: list[UUID]) -> str:
    """Format a list of UUIDs for SQL IN clause.

    :param uuids: List of UUIDs.
    :returns: Formatted string for SQL.
    """
    return ", ".join(f"'{u!s}'" for u in uuids)


def _format_string_list(values: list[str]) -> str:
    """Format a list of strings for SQL IN clause.

    :param values: List of string values.
    :returns: Formatted string for SQL.
    """
    return ", ".join(f"'{v}'" for v in values)


def _get_valid_column_names(dataset: Dataset) -> set[str]:
    """Get the set of valid column names for a dataset.

    Used to validate filter column names against SQL injection.

    :param dataset: Dataset with filter configuration.
    :returns: Set of valid column names.
    """
    valid_columns: set[str] = set()

    for ef in dataset.filters.enum_filters:
        valid_columns.add(ef.name)

    for nf in dataset.filters.numeric_filters:
        valid_columns.add(nf.name)

    return valid_columns


def _apply_enum_filters(
    query: str,
    enum_filters: list[dict[str, Any]],
    valid_columns: set[str],
) -> str:
    """Apply enum filters to a query.

    :param query: Current query string.
    :param enum_filters: List of enum filter dicts with column and values.
    :param valid_columns: Set of valid column names for validation.
    :returns: Updated query string.
    """
    for ef in enum_filters:
        column = ef.get("column")
        values = ef.get("values")
        if column and column in valid_columns and values:
            values_list = _format_string_list(values)
            query += f" AND {column} IN ({values_list})"
    return query


def _apply_numeric_filters(
    query: str,
    params: dict[str, Any],
    numeric_filters: list[dict[str, Any]],
    valid_columns: set[str],
) -> str:
    """Apply numeric filters to a query.

    :param query: Current query string.
    :param params: Query parameters dict (mutated in place).
    :param numeric_filters: List of numeric filter dicts with column, min, max.
    :param valid_columns: Set of valid column names for validation.
    :returns: Updated query string.
    """
    for idx, nf in enumerate(numeric_filters):
        column = nf.get("column")
        min_val = nf.get("min")
        max_val = nf.get("max")
        if column and column in valid_columns:
            if min_val is not None:
                param_name = f"numeric_min_{idx}"
                query += f" AND {column} >= ${param_name}"
                params[param_name] = min_val
            if max_val is not None:
                param_name = f"numeric_max_{idx}"
                query += f" AND {column} <= ${param_name}"
                params[param_name] = max_val
    return query


def build_dataset_query(
    dataset: Dataset,
    user_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    account_ids: list[UUID] | None = None,
    tag_ids: list[UUID] | None = None,
    enum_filters: list[dict[str, Any]] | None = None,
    numeric_filters: list[dict[str, Any]] | None = None,
    limit: int = 1000,
    offset: int = 0,
) -> tuple[str, dict[str, Any]]:
    """Build a query for a dataset with common filters.

    Uses the dataset's filter configuration from dbt metadata to determine
    which columns to filter on.

    :param dataset: Dataset object with schema and filter configuration.
    :param user_id: User ID to filter by.
    :param start_date: Optional start date filter.
    :param end_date: Optional end date filter.
    :param account_ids: Optional list of account IDs to filter by.
    :param tag_ids: Optional list of tag IDs to filter by.
    :param enum_filters: Optional list of enum filters (column + values).
    :param numeric_filters: Optional list of numeric filters (column + min/max).
    :param limit: Maximum rows to return.
    :param offset: Number of rows to skip.
    :returns: Tuple of (query string, parameters dict).
    """
    query = f"SELECT * FROM {dataset.schema_name}.{dataset.name} WHERE user_id = $user_id"
    params: dict[str, Any] = {"user_id": str(user_id)}

    # Apply date filter if dataset has a date column configured
    if dataset.filters.date_column:
        if start_date:
            query += f" AND {dataset.filters.date_column} >= $start_date"
            params["start_date"] = start_date
        if end_date:
            query += f" AND {dataset.filters.date_column} <= $end_date"
            params["end_date"] = end_date

    # Apply account filter if dataset has an account_id column configured
    if dataset.filters.account_id_column and account_ids:
        account_list = _format_uuid_list(account_ids)
        query += f" AND {dataset.filters.account_id_column} IN ({account_list})"

    # Apply tag filter if dataset has a tag_id column configured
    if dataset.filters.tag_id_column and tag_ids:
        tag_list = _format_uuid_list(tag_ids)
        query += f" AND {dataset.filters.tag_id_column} IN ({tag_list})"

    # Get valid column names for filter validation
    valid_columns = _get_valid_column_names(dataset)

    # Apply enum and numeric filters
    if enum_filters:
        query = _apply_enum_filters(query, enum_filters, valid_columns)

    if numeric_filters:
        query = _apply_numeric_filters(query, params, numeric_filters, valid_columns)

    # Add ordering based on date column if available
    if dataset.filters.date_column:
        query += f" ORDER BY {dataset.filters.date_column} DESC"

    # Add pagination
    query += f" LIMIT {limit} OFFSET {offset}"

    return query, params
