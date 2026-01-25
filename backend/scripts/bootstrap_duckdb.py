"""Bootstraps DuckDB with the required extensions.

Usage:
    cd backend
    poetry run bootstrap-duckdb
"""

import duckdb
from src.filepaths import DUCKDB_PATH


def bootstrap() -> None:
    """Bootstrap DuckDB with the required extensions."""
    # Ensure the parent directory exists
    DUCKDB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(DUCKDB_PATH)
    con.execute("INSTALL postgres;")
    con.execute("LOAD postgres;")
    con.close()
    print("DuckDB bootstrap complete.")


if __name__ == "__main__":
    bootstrap()
