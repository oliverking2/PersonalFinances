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


def build_dataset_query(  # noqa: PLR0913
    dataset: Dataset,
    user_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    account_ids: list[UUID] | None = None,
    tag_ids: list[UUID] | None = None,
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

    # Add ordering based on date column if available
    if dataset.filters.date_column:
        query += f" ORDER BY {dataset.filters.date_column} DESC"

    # Add pagination
    query += f" LIMIT {limit} OFFSET {offset}"

    return query, params
