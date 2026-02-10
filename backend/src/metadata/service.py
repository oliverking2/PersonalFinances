"""Metadata service for building LLM-friendly schema summaries."""

from __future__ import annotations

import logging

from src.duckdb import get_all_sample_questions, get_semantic_datasets
from src.metadata.models import (
    DatasetSummary,
    DimensionSummary,
    MeasureSummary,
    SchemaContext,
)

logger = logging.getLogger(__name__)


class MetadataService:
    """Builds compact schema context from dbt semantic metadata."""

    @staticmethod
    def get_schema_context() -> SchemaContext:
        """Build full schema context with all datasets.

        :returns: SchemaContext with dataset summaries and totals.
        """
        datasets = get_semantic_datasets()
        summaries = []
        total_measures = 0
        total_dimensions = 0

        for ds in datasets:
            measures = [
                MeasureSummary(name=m.name, agg=m.agg, description=m.description)
                for m in ds.measures
            ]
            dimensions = [
                DimensionSummary(name=d.name, type=d.type, description=d.description)
                for d in ds.dimensions
            ]
            total_measures += len(measures)
            total_dimensions += len(dimensions)

            summaries.append(
                DatasetSummary(
                    name=ds.name,
                    friendly_name=ds.friendly_name,
                    description=ds.description,
                    time_grain=ds.time_grain,
                    measures=measures,
                    dimensions=dimensions,
                    sample_questions=ds.sample_questions,
                )
            )

        return SchemaContext(
            datasets=summaries,
            total_measures=total_measures,
            total_dimensions=total_dimensions,
        )

    @staticmethod
    def get_schema_summary() -> str:
        """Build a compact text summary of the schema for the LLM system prompt.

        :returns: Multi-line text block describing all datasets (~2000 tokens).
        """
        context = MetadataService.get_schema_context()
        lines = [
            f"Available datasets: {len(context.datasets)}",
            f"Total measures: {context.total_measures}, "
            f"Total dimensions: {context.total_dimensions}",
            "",
        ]

        for ds in context.datasets:
            lines.append(f"## {ds.friendly_name} (dataset: {ds.name})")
            lines.append(f"  {ds.description}")
            if ds.time_grain:
                lines.append(f"  Time grain: {ds.time_grain}")

            if ds.measures:
                lines.append("  Measures:")
                for m in ds.measures:
                    desc = f" - {m.description}" if m.description else ""
                    lines.append(f"    - {m.name} ({m.agg}){desc}")

            if ds.dimensions:
                lines.append("  Dimensions:")
                for d in ds.dimensions:
                    desc = f" - {d.description}" if d.description else ""
                    lines.append(f"    - {d.name} ({d.type}){desc}")

            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def get_suggestions() -> list[str]:
        """Get sample questions from all datasets.

        :returns: Flat list of sample questions.
        """
        return get_all_sample_questions()
