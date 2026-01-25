"""DuckDB connection management.

Provides read-only connections to the analytics.duckdb database.
Uses connection-per-request pattern (DuckDB is fast, no pooling needed).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import duckdb

logger = logging.getLogger(__name__)

# Default timeout for queries (10 seconds)
DEFAULT_QUERY_TIMEOUT_SECONDS = 10

# Maximum rows to return from a query
MAX_RESULT_ROWS = 10_000


def _get_database_path() -> Path:
    """Get the path to the DuckDB analytics database.

    :returns: Path to analytics.duckdb file.
    :raises FileNotFoundError: If database file doesn't exist.
    """
    # Default path relative to backend directory
    backend_dir = Path(__file__).parent.parent.parent
    db_path = backend_dir / "analytics.duckdb"

    # Allow override via environment variable
    if env_path := os.environ.get("DUCKDB_PATH"):
        db_path = Path(env_path)

    if not db_path.exists():
        raise FileNotFoundError(f"DuckDB database not found at {db_path}")

    return db_path


def get_connection() -> duckdb.DuckDBPyConnection:
    """Create a read-only connection to the analytics database.

    :returns: DuckDB connection configured for read-only access.
    :raises FileNotFoundError: If database file doesn't exist.
    """
    db_path = _get_database_path()
    logger.debug(f"Opening DuckDB connection: path={db_path}")
    return duckdb.connect(str(db_path), read_only=True)


def execute_query(
    query: str,
    params: dict[str, Any] | None = None,
    timeout_seconds: int = DEFAULT_QUERY_TIMEOUT_SECONDS,
    max_rows: int = MAX_RESULT_ROWS,
) -> list[dict[str, Any]]:
    """Execute a parameterized query and return results as dictionaries.

    :param query: SQL query with named parameter placeholders ($name).
    :param params: Dictionary of parameter values.
    :param timeout_seconds: Query timeout in seconds.
    :param max_rows: Maximum rows to return.
    :returns: List of result rows as dictionaries.
    :raises TimeoutError: If query exceeds timeout.
    :raises duckdb.Error: If query fails.
    """
    conn = get_connection()
    try:
        # Set query timeout
        conn.execute(f"SET statement_timeout = '{timeout_seconds}s'")

        # Add row limit to query if not already present
        limited_query = query
        if "LIMIT" not in query.upper():
            limited_query = f"{query} LIMIT {max_rows}"

        logger.debug(f"Executing query: {limited_query[:100]}...")
        result = conn.execute(limited_query, params) if params else conn.execute(limited_query)

        # Fetch results as list of dicts
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()

        return [dict(zip(columns, row)) for row in rows]

    finally:
        conn.close()


def check_connection() -> bool:
    """Check if the DuckDB database is accessible.

    :returns: True if database is accessible, False otherwise.
    """
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
        return True
    except Exception as e:
        logger.warning(f"DuckDB connection check failed: {e}")
        return False
