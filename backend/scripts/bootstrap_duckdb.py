"""Bootstraps DuckDB with the required extensions.

Usage:
    cd backend
    poetry run bootstrap-duckdb
"""

import duckdb
from src.filepaths import ROOT_DIR

DB_PATH = ROOT_DIR / "analytics.duckdb"


def bootstrap() -> None:
    """Bootstrap DuckDB with the required extensions."""
    con = duckdb.connect(DB_PATH)
    con.execute("INSTALL postgres;")
    con.execute("LOAD postgres;")
    con.close()
    print("DuckDB bootstrap complete.")


if __name__ == "__main__":
    bootstrap()
