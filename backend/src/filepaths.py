"""Filepaths for the project."""

import os
from pathlib import Path

# backend/ directory (where src/ lives)
BACKEND_DIR = Path(__file__).parent.parent

# Project root (parent of backend/)
PROJECT_ROOT = BACKEND_DIR.parent

# DuckDB File - configurable via env var for server deployments
# Default: backend/data/analytics.duckdb
DUCKDB_PATH = Path(os.environ.get("DUCKDB_PATH", BACKEND_DIR / "data" / "analytics.duckdb"))
