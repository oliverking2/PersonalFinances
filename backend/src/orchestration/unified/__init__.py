"""Unified orchestration assets.

These assets provide a single dependency point for multi-provider data,
used by dbt to ensure all provider syncs complete before running transforms.
"""

from src.orchestration.unified.definitions import unified_defs

__all__ = ["unified_defs"]
