"""DuckDB connection management.

Provides read-only connections to the persistent analytics DuckDB file written by dbt.
"""

from __future__ import annotations

import logging
from typing import Any

import duckdb
from src.filepaths import DUCKDB_PATH

logger = logging.getLogger(__name__)

# Default timeout for queries (10 seconds)
DEFAULT_QUERY_TIMEOUT_SECONDS = 10

# Maximum rows to return from a query
MAX_RESULT_ROWS = 10_000


def get_connection() -> duckdb.DuckDBPyConnection:
    """Create a read-only connection to the analytics DuckDB file.

    :returns: DuckDB connection.
    :raises FileNotFoundError: If the DuckDB file does not exist.
    """
    if not DUCKDB_PATH.exists():
        raise FileNotFoundError(f"Analytics database not found at {DUCKDB_PATH}")
    return duckdb.connect(str(DUCKDB_PATH), read_only=True)


def execute_query(
    query: str,
    params: dict[str, Any] | None = None,
    max_rows: int = MAX_RESULT_ROWS,
) -> list[dict[str, Any]]:
    """Execute a parameterized query and return results as dictionaries.

    :param query: SQL query with named parameter placeholders ($name).
    :param params: Dictionary of parameter values.
    :param max_rows: Maximum rows to return.
    :returns: List of result rows as dictionaries.
    :raises FileNotFoundError: If the DuckDB file does not exist.
    :raises duckdb.Error: If query fails.
    """
    conn = get_connection()
    try:
        limited_query = query if "LIMIT" in query.upper() else f"{query} LIMIT {max_rows}"
        logger.debug(f"Executing query: {limited_query[:100]}...")
        result = conn.execute(limited_query, params) if params else conn.execute(limited_query)
        columns = [desc[0].lower() for desc in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]
    finally:
        conn.close()


def check_connection() -> bool:
    """Check if the analytics database is accessible.

    :returns: True if accessible, False otherwise.
    """
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
        return True
    except Exception as e:
        logger.warning(f"DuckDB connection check failed: {e}")
        return False
