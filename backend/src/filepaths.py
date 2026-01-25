"""Filepaths for the project."""

from pathlib import Path

# backend/ directory (where src/ lives)
BACKEND_DIR = Path(__file__).parent.parent

# Project root (parent of backend/)
PROJECT_ROOT = BACKEND_DIR.parent

# DuckDB File (in data/ subdirectory for Docker volume mounting)
DUCKDB_PATH = BACKEND_DIR / "data" / "analytics.duckdb"
