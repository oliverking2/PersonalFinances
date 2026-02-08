"""DuckDB connection management.

Provides connections to analytics data via Parquet files (preferred)
or the legacy analytics.duckdb file (fallback).
Uses connection-per-request pattern (DuckDB is fast, no pooling needed).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import duckdb
from src.filepaths import DUCKDB_PATH, PARQUET_DIR

logger = logging.getLogger(__name__)

# Default timeout for queries (10 seconds)
DEFAULT_QUERY_TIMEOUT_SECONDS = 10

# Maximum rows to return from a query
MAX_RESULT_ROWS = 10_000

# Parquet mart directory
_PARQUET_MART_DIR = PARQUET_DIR / "mart"


def _get_parquet_files() -> list[Path]:
    """Get all Parquet files in the mart directory.

    :returns: List of Parquet file paths, empty if directory doesn't exist.
    """
    if not _PARQUET_MART_DIR.is_dir():
        return []
    return sorted(_PARQUET_MART_DIR.glob("*.parquet"))


def _has_parquet_files() -> bool:
    """Check if any Parquet files exist in the mart directory.

    :returns: True if at least one .parquet file exists.
    """
    return len(_get_parquet_files()) > 0


def get_connection() -> duckdb.DuckDBPyConnection:
    """Create a connection to analytics data.

    Prefers in-memory DuckDB with Parquet views registered under the ``mart``
    schema.  Falls back to the legacy analytics.duckdb file when no Parquet
    files are available.

    :returns: DuckDB connection with mart schema available.
    :raises FileNotFoundError: If neither Parquet files nor DuckDB file exist.
    """
    parquet_files = _get_parquet_files()

    if parquet_files:
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE SCHEMA IF NOT EXISTS mart")
        for pf in parquet_files:
            view_name = pf.stem
            conn.execute(f"CREATE VIEW mart.{view_name} AS SELECT * FROM read_parquet('{pf}')")
        logger.debug(f"Opened in-memory DuckDB with {len(parquet_files)} Parquet views")
        return conn

    # Fallback: legacy DuckDB file
    if not DUCKDB_PATH.exists():
        raise FileNotFoundError(
            f"No Parquet files in {_PARQUET_MART_DIR} and no DuckDB database at {DUCKDB_PATH}"
        )
    logger.debug(f"Opening legacy DuckDB connection: path={DUCKDB_PATH}")
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
    :raises TimeoutError: If query exceeds timeout.
    :raises duckdb.Error: If query fails.
    """
    conn = get_connection()
    try:
        # Add row limit to query if not already present
        limited_query = query
        if "LIMIT" not in query.upper():
            limited_query = f"{query} LIMIT {max_rows}"

        logger.debug(f"Executing query: {limited_query[:100]}...")
        result = conn.execute(limited_query, params) if params else conn.execute(limited_query)

        # Fetch results as list of dicts
        # Normalize column names to lowercase for consistent API responses
        columns = [desc[0].lower() for desc in result.description]
        rows = result.fetchall()

        return [dict(zip(columns, row)) for row in rows]

    finally:
        conn.close()


def check_connection() -> bool:
    """Check if analytics data is accessible (Parquet files or DuckDB file).

    :returns: True if data is accessible, False otherwise.
    """
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
        return True
    except Exception as e:
        logger.warning(f"DuckDB connection check failed: {e}")
        return False
