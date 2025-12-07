"""Bootstraps DuckDB with the required extensions."""

import duckdb
from filepaths import ROOT_DIR

DB_PATH = ROOT_DIR / "analytics.duckdb"


def bootstrap() -> None:
    """Bootstrap DuckDB with the required extensions."""
    con = duckdb.connect(DB_PATH)
    con.execute("INSTALL httpfs;")
    con.execute("LOAD httpfs;")
    con.close()


if __name__ == "__main__":
    bootstrap()
    print("DuckDB bootstrap complete.")
