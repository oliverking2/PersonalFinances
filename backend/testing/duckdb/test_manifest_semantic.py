"""Tests for semantic metadata parsing in manifest.py.

Uses a mock manifest JSON to test parsing without needing a real dbt manifest.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from src.duckdb.manifest import (
    SemanticDataset,
    _extract_semantic,
    _generate_dataset_id,
    get_all_sample_questions,
    get_semantic_dataset,
    get_semantic_datasets,
)


def _make_manifest(models: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a minimal manifest structure with the given models.

    :param models: List of model node dicts.
    :returns: Manifest dict with nodes populated.
    """
    nodes = {}
    for model in models:
        name = model["name"]
        key = f"model.dbt_project.{name}"
        nodes[key] = {
            "name": name,
            "description": model.get("description", ""),
            "schema": model.get("schema", "mart"),
            "meta": model.get("meta", {}),
            "columns": model.get("columns", {}),
        }
    return {"nodes": nodes}


SAMPLE_META: dict[str, Any] = {
    "dataset": True,
    "friendly_name": "Monthly Trends",
    "group": "aggregations",
    "time_grain": "month",
    "filters": {"date_column": "month_start"},
    "semantic": {
        "measures": [
            {
                "name": "total_income",
                "expr": "total_income",
                "agg": "sum",
                "description": "Total income",
            },
            {
                "name": "total_spending",
                "expr": "total_spending",
                "agg": "sum",
                "description": "Total spending",
            },
        ],
        "dimensions": [
            {
                "name": "month_start",
                "expr": "month_start",
                "type": "time",
                "description": "Month start date",
            },
            {
                "name": "currency",
                "expr": "currency",
                "type": "categorical",
                "description": "Currency code",
            },
        ],
        "sample_questions": [
            "What is my income trend?",
            "How much did I spend last month?",
        ],
    },
}


# ---------------------------------------------------------------------------
# _extract_semantic tests
# ---------------------------------------------------------------------------


class TestExtractSemantic:
    """Tests for the _extract_semantic helper."""

    def test_parses_measures(self) -> None:
        """Should parse measures from meta.semantic."""
        measures, _, _ = _extract_semantic(SAMPLE_META)

        assert len(measures) == 2
        assert measures[0].name == "total_income"
        assert measures[0].expr == "total_income"
        assert measures[0].agg == "sum"
        assert measures[0].description == "Total income"

    def test_parses_dimensions(self) -> None:
        """Should parse dimensions from meta.semantic."""
        _, dimensions, _ = _extract_semantic(SAMPLE_META)

        assert len(dimensions) == 2
        assert dimensions[0].name == "month_start"
        assert dimensions[0].type == "time"
        assert dimensions[1].name == "currency"
        assert dimensions[1].type == "categorical"

    def test_parses_sample_questions(self) -> None:
        """Should parse sample questions from meta.semantic."""
        _, _, questions = _extract_semantic(SAMPLE_META)

        assert len(questions) == 2
        assert "What is my income trend?" in questions

    def test_missing_semantic_block(self) -> None:
        """Should return empty lists when semantic block is missing."""
        measures, dimensions, questions = _extract_semantic({"dataset": True})

        assert measures == []
        assert dimensions == []
        assert questions == []

    def test_empty_semantic_block(self) -> None:
        """Should return empty lists when semantic block is empty."""
        measures, dimensions, questions = _extract_semantic({"semantic": {}})

        assert measures == []
        assert dimensions == []
        assert questions == []

    def test_skips_malformed_measures(self) -> None:
        """Should skip measures missing required fields."""
        meta = {
            "semantic": {
                "measures": [
                    {"name": "valid", "expr": "x", "agg": "sum"},
                    {"name": "missing_expr"},  # Missing expr and agg
                    "not a dict",
                ],
            },
        }
        measures, _, _ = _extract_semantic(meta)
        assert len(measures) == 1
        assert measures[0].name == "valid"

    def test_skips_malformed_dimensions(self) -> None:
        """Should skip dimensions missing required fields."""
        meta = {
            "semantic": {
                "dimensions": [
                    {"name": "valid", "expr": "x", "type": "categorical"},
                    {"name": "missing_type"},  # Missing expr and type
                ],
            },
        }
        _, dimensions, _ = _extract_semantic(meta)
        assert len(dimensions) == 1

    def test_skips_invalid_agg_values(self) -> None:
        """Should skip measures with invalid agg values and keep valid ones."""
        meta = {
            "semantic": {
                "measures": [
                    {"name": "valid", "expr": "x", "agg": "sum"},
                    {"name": "invalid_agg", "expr": "y", "agg": "median"},
                    {"name": "also_valid", "expr": "z", "agg": "count_distinct"},
                ],
            },
        }
        measures, _, _ = _extract_semantic(meta)
        assert len(measures) == 2
        assert measures[0].name == "valid"
        assert measures[1].name == "also_valid"

    def test_skips_non_string_questions(self) -> None:
        """Should skip non-string sample questions."""
        meta = {
            "semantic": {
                "sample_questions": ["Valid question?", 123, None],
            },
        }
        _, _, questions = _extract_semantic(meta)
        assert questions == ["Valid question?"]


# ---------------------------------------------------------------------------
# get_semantic_datasets tests
# ---------------------------------------------------------------------------


class TestGetSemanticDatasets:
    """Tests for get_semantic_datasets."""

    @patch("src.duckdb.manifest._load_manifest")
    def test_returns_datasets_with_semantic_metadata(self, mock_load: Any) -> None:
        """Should return datasets with measures and dimensions parsed."""
        manifest = _make_manifest(
            [
                {
                    "name": "fct_monthly_trends",
                    "description": "Monthly trends",
                    "meta": SAMPLE_META,
                },
            ]
        )
        mock_load.return_value = manifest

        datasets = get_semantic_datasets()

        assert len(datasets) == 1
        ds = datasets[0]
        assert isinstance(ds, SemanticDataset)
        assert ds.name == "fct_monthly_trends"
        assert ds.friendly_name == "Monthly Trends"
        assert len(ds.measures) == 2
        assert len(ds.dimensions) == 2
        assert len(ds.sample_questions) == 2

    @patch("src.duckdb.manifest._load_manifest")
    def test_skips_non_dataset_models(self, mock_load: Any) -> None:
        """Should skip models without dataset: true."""
        manifest = _make_manifest(
            [
                {
                    "name": "int_intermediate",
                    "meta": {"dataset": False, "group": "intermediate"},
                },
                {
                    "name": "fct_monthly_trends",
                    "meta": SAMPLE_META,
                },
            ]
        )
        mock_load.return_value = manifest

        datasets = get_semantic_datasets()
        assert len(datasets) == 1
        assert datasets[0].name == "fct_monthly_trends"

    @patch("src.duckdb.manifest._load_manifest")
    def test_returns_empty_on_file_not_found(self, mock_load: Any) -> None:
        """Should return empty list when manifest is not found."""
        mock_load.side_effect = FileNotFoundError("not found")

        datasets = get_semantic_datasets()
        assert datasets == []

    @patch("src.duckdb.manifest._load_manifest")
    def test_multiple_datasets(self, mock_load: Any) -> None:
        """Should return multiple datasets."""
        manifest = _make_manifest(
            [
                {"name": "fct_monthly_trends", "meta": SAMPLE_META},
                {
                    "name": "dim_accounts",
                    "meta": {
                        "dataset": True,
                        "friendly_name": "Accounts",
                        "group": "dimensions",
                        "filters": {"account_id_column": "account_id"},
                        "semantic": {
                            "measures": [
                                {"name": "account_count", "expr": "account_id", "agg": "count"},
                            ],
                            "dimensions": [
                                {
                                    "name": "account_type",
                                    "expr": "account_type",
                                    "type": "categorical",
                                },
                            ],
                            "sample_questions": ["How many accounts do I have?"],
                        },
                    },
                },
            ]
        )
        mock_load.return_value = manifest

        datasets = get_semantic_datasets()
        assert len(datasets) == 2
        names = {ds.name for ds in datasets}
        assert names == {"fct_monthly_trends", "dim_accounts"}


# ---------------------------------------------------------------------------
# get_semantic_dataset tests
# ---------------------------------------------------------------------------


class TestGetSemanticDataset:
    """Tests for get_semantic_dataset."""

    @patch("src.duckdb.manifest._load_manifest")
    def test_lookup_by_name(self, mock_load: Any) -> None:
        """Should return a dataset by model name."""
        manifest = _make_manifest(
            [
                {"name": "fct_monthly_trends", "meta": SAMPLE_META},
            ]
        )
        mock_load.return_value = manifest

        ds = get_semantic_dataset("fct_monthly_trends")

        assert ds is not None
        assert ds.name == "fct_monthly_trends"
        assert len(ds.measures) == 2

    @patch("src.duckdb.manifest._load_manifest")
    def test_lookup_by_uuid(self, mock_load: Any) -> None:
        """Should return a dataset by UUID."""
        manifest = _make_manifest(
            [
                {"name": "fct_monthly_trends", "meta": SAMPLE_META},
            ]
        )
        mock_load.return_value = manifest

        dataset_id = _generate_dataset_id("fct_monthly_trends")
        ds = get_semantic_dataset(dataset_id)

        assert ds is not None
        assert ds.name == "fct_monthly_trends"

    @patch("src.duckdb.manifest._load_manifest")
    def test_returns_none_for_unknown_name(self, mock_load: Any) -> None:
        """Should return None for an unknown model name."""
        manifest = _make_manifest(
            [
                {"name": "fct_monthly_trends", "meta": SAMPLE_META},
            ]
        )
        mock_load.return_value = manifest

        ds = get_semantic_dataset("nonexistent")
        assert ds is None

    @patch("src.duckdb.manifest._load_manifest")
    def test_returns_none_for_non_dataset(self, mock_load: Any) -> None:
        """Should return None for a model that isn't a dataset."""
        manifest = _make_manifest(
            [
                {"name": "int_intermediate", "meta": {"dataset": False}},
            ]
        )
        mock_load.return_value = manifest

        ds = get_semantic_dataset("int_intermediate")
        assert ds is None

    @patch("src.duckdb.manifest._load_manifest")
    def test_returns_none_on_file_not_found(self, mock_load: Any) -> None:
        """Should return None when manifest is not found."""
        mock_load.side_effect = FileNotFoundError("not found")

        ds = get_semantic_dataset("fct_monthly_trends")
        assert ds is None


# ---------------------------------------------------------------------------
# get_all_sample_questions tests
# ---------------------------------------------------------------------------


class TestGetAllSampleQuestions:
    """Tests for get_all_sample_questions."""

    @patch("src.duckdb.manifest._load_manifest")
    def test_collects_questions_across_datasets(self, mock_load: Any) -> None:
        """Should collect questions from all datasets."""
        manifest = _make_manifest(
            [
                {"name": "fct_monthly_trends", "meta": SAMPLE_META},
                {
                    "name": "dim_accounts",
                    "meta": {
                        "dataset": True,
                        "friendly_name": "Accounts",
                        "group": "dimensions",
                        "semantic": {
                            "measures": [
                                {"name": "count", "expr": "id", "agg": "count"},
                            ],
                            "dimensions": [],
                            "sample_questions": ["How many accounts?"],
                        },
                    },
                },
            ]
        )
        mock_load.return_value = manifest

        questions = get_all_sample_questions()

        assert len(questions) == 3
        assert "What is my income trend?" in questions
        assert "How many accounts?" in questions

    @patch("src.duckdb.manifest._load_manifest")
    def test_returns_empty_when_no_questions(self, mock_load: Any) -> None:
        """Should return empty list when no datasets have questions."""
        manifest = _make_manifest(
            [
                {
                    "name": "fct_empty",
                    "meta": {
                        "dataset": True,
                        "friendly_name": "Empty",
                        "group": "facts",
                        "semantic": {},
                    },
                },
            ]
        )
        mock_load.return_value = manifest

        questions = get_all_sample_questions()
        assert questions == []
