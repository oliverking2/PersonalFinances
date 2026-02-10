"""Tests for the metadata service."""

from __future__ import annotations

from unittest.mock import patch

from src.duckdb.manifest import DatasetFilters, Dimension, Measure, SemanticDataset
from src.duckdb.manifest import _generate_dataset_id as generate_dataset_id
from src.metadata.service import MetadataService


def _make_dataset(
    name: str = "fct_test",
    friendly_name: str = "Test Dataset",
    measures: list[Measure] | None = None,
    dimensions: list[Dimension] | None = None,
    sample_questions: list[str] | None = None,
) -> SemanticDataset:
    """Build a minimal SemanticDataset for testing."""
    return SemanticDataset(
        id=generate_dataset_id(name),
        name=name,
        friendly_name=friendly_name,
        description="A test dataset.",
        group="facts",
        time_grain="month",
        schema_name="mart",
        filters=DatasetFilters(),
        measures=measures or [Measure(name="total", expr="amount", agg="sum", description="Total")],
        dimensions=dimensions
        or [Dimension(name="period", expr="date", type="time", description="Period")],
        sample_questions=sample_questions or ["How much did I spend?"],
    )


class TestGetSchemaContext:
    """Tests for MetadataService.get_schema_context."""

    @patch("src.metadata.service.get_semantic_datasets")
    def test_returns_empty_context_when_no_datasets(self, mock_datasets: object) -> None:
        """Should return empty context when no datasets exist."""
        mock_datasets.return_value = []  # type: ignore[attr-defined]

        ctx = MetadataService.get_schema_context()

        assert ctx.datasets == []
        assert ctx.total_measures == 0
        assert ctx.total_dimensions == 0

    @patch("src.metadata.service.get_semantic_datasets")
    def test_returns_datasets_with_summaries(self, mock_datasets: object) -> None:
        """Should map semantic datasets to summaries correctly."""
        mock_datasets.return_value = [_make_dataset()]  # type: ignore[attr-defined]

        ctx = MetadataService.get_schema_context()

        assert len(ctx.datasets) == 1
        ds = ctx.datasets[0]
        assert ds.name == "fct_test"
        assert ds.friendly_name == "Test Dataset"
        assert len(ds.measures) == 1
        assert ds.measures[0].name == "total"
        assert ds.measures[0].agg == "sum"
        assert len(ds.dimensions) == 1
        assert ds.dimensions[0].name == "period"
        assert ctx.total_measures == 1
        assert ctx.total_dimensions == 1

    @patch("src.metadata.service.get_semantic_datasets")
    def test_excludes_expr_from_summaries(self, mock_datasets: object) -> None:
        """Should not expose SQL expressions to the LLM."""
        mock_datasets.return_value = [_make_dataset()]  # type: ignore[attr-defined]

        ctx = MetadataService.get_schema_context()

        ds = ctx.datasets[0]
        # MeasureSummary and DimensionSummary should not have 'expr'
        assert not hasattr(ds.measures[0], "expr")
        assert not hasattr(ds.dimensions[0], "expr")

    @patch("src.metadata.service.get_semantic_datasets")
    def test_aggregates_totals_across_datasets(self, mock_datasets: object) -> None:
        """Should sum measures and dimensions across multiple datasets."""
        mock_datasets.return_value = [  # type: ignore[attr-defined]
            _make_dataset(name="fct_a"),
            _make_dataset(
                name="fct_b",
                measures=[
                    Measure(name="m1", expr="x", agg="sum", description=""),
                    Measure(name="m2", expr="y", agg="avg", description=""),
                ],
            ),
        ]

        ctx = MetadataService.get_schema_context()

        assert ctx.total_measures == 3
        assert ctx.total_dimensions == 2


class TestGetSchemaSummary:
    """Tests for MetadataService.get_schema_summary."""

    @patch("src.metadata.service.get_semantic_datasets")
    def test_returns_text_summary(self, mock_datasets: object) -> None:
        """Should return a multi-line text summary."""
        mock_datasets.return_value = [_make_dataset()]  # type: ignore[attr-defined]

        summary = MetadataService.get_schema_summary()

        assert "Available datasets: 1" in summary
        assert "Test Dataset" in summary
        assert "fct_test" in summary
        assert "total (sum)" in summary
        assert "period (time)" in summary

    @patch("src.metadata.service.get_semantic_datasets")
    def test_includes_time_grain(self, mock_datasets: object) -> None:
        """Should include time grain when present."""
        mock_datasets.return_value = [_make_dataset()]  # type: ignore[attr-defined]

        summary = MetadataService.get_schema_summary()

        assert "Time grain: month" in summary


class TestGetSuggestions:
    """Tests for MetadataService.get_suggestions."""

    @patch("src.metadata.service.get_all_sample_questions")
    def test_returns_sample_questions(self, mock_questions: object) -> None:
        """Should return sample questions from all datasets."""
        mock_questions.return_value = ["Q1", "Q2"]  # type: ignore[attr-defined]

        suggestions = MetadataService.get_suggestions()

        assert suggestions == ["Q1", "Q2"]

    @patch("src.metadata.service.get_all_sample_questions")
    def test_returns_empty_list_when_no_questions(self, mock_questions: object) -> None:
        """Should return empty list when no sample questions exist."""
        mock_questions.return_value = []  # type: ignore[attr-defined]

        suggestions = MetadataService.get_suggestions()

        assert suggestions == []
