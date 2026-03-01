"""Bootstraps DuckDB with the required extensions.

Usage:
    cd backend
    poetry run bootstrap-duckdb
"""

import duckdb
from src.filepaths import DUCKDB_PATH


def bootstrap() -> None:
    """Bootstrap DuckDB with the required extensions."""
    DUCKDB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(DUCKDB_PATH)
    con.execute("INSTALL postgres;")
    con.execute("LOAD postgres;")
    con.close()

    # Create parquet mart directory for dbt post-hook exports
    parquet_mart_dir = DUCKDB_PATH.parent / "parquet" / "mart"
    parquet_mart_dir.mkdir(parents=True, exist_ok=True)

    print("DuckDB bootstrap complete.")


if __name__ == "__main__":
    bootstrap()
