"""Filepaths for the project."""

from pathlib import Path

# backend/ directory (where src/ lives)
BACKEND_DIR = Path(__file__).parent.parent

# Project root (parent of backend/)
PROJECT_ROOT = BACKEND_DIR.parent

# DuckDB File
DUCKDB_PATH = BACKEND_DIR / "analytics.duckdb"
