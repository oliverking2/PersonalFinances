"""Metadata service for analytics schema context.

Provides a thin adapter over dbt semantic datasets for LLM prompt generation.
"""

from src.metadata.models import DatasetSummary, DimensionSummary, MeasureSummary, SchemaContext
from src.metadata.service import MetadataService

__all__ = [
    "DatasetSummary",
    "DimensionSummary",
    "MeasureSummary",
    "MetadataService",
    "SchemaContext",
]
