"""dbt manifest parser for dataset discovery.

Parses the dbt manifest.json to discover available datasets and their schemas.
Datasets are dbt models with `meta.dataset: true` in their schema.yml.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DatasetColumn:
    """Schema column for a dataset."""

    name: str
    description: str
    data_type: str | None = None


@dataclass
class DatasetFilters:
    """Filter column configuration for a dataset."""

    date_column: str | None = None
    account_id_column: str | None = None
    tag_id_column: str | None = None


@dataclass
class Dataset:
    """A discoverable analytics dataset from dbt."""

    id: str  # Model name (e.g., "fct_transactions")
    friendly_name: str
    description: str
    group: str  # "facts", "dimensions", "aggregations"
    time_grain: str | None = None  # "day", "month", etc.
    schema_name: str = "mart"
    columns: list[DatasetColumn] | None = None
    filters: DatasetFilters = field(default_factory=DatasetFilters)


def _get_manifest_path() -> Path:
    """Get the path to the dbt manifest.json file.

    :returns: Path to manifest.json.
    :raises FileNotFoundError: If manifest doesn't exist.
    """
    # Default path relative to backend directory
    backend_dir = Path(__file__).parent.parent.parent
    manifest_path = backend_dir / "dbt" / "target" / "manifest.json"

    # Allow override via environment variable
    if env_path := os.environ.get("DBT_MANIFEST_PATH"):
        manifest_path = Path(env_path)

    if not manifest_path.exists():
        raise FileNotFoundError(
            f"dbt manifest not found at {manifest_path}. Run 'dbt build' to generate it."
        )

    return manifest_path


def _load_manifest() -> dict[str, Any]:
    """Load and parse the dbt manifest.json.

    :returns: Parsed manifest dictionary.
    """
    manifest_path = _get_manifest_path()
    logger.debug(f"Loading dbt manifest: path={manifest_path}")

    with manifest_path.open() as f:
        return json.load(f)


def _extract_filters(meta: dict[str, Any]) -> DatasetFilters:
    """Extract filter configuration from model metadata.

    :param meta: Model metadata dictionary.
    :returns: DatasetFilters configuration.
    """
    filters_meta = meta.get("filters", {})
    return DatasetFilters(
        date_column=filters_meta.get("date_column"),
        account_id_column=filters_meta.get("account_id_column"),
        tag_id_column=filters_meta.get("tag_id_column"),
    )


def get_datasets() -> list[Dataset]:
    """Get all available datasets from the dbt manifest.

    Datasets are models in the 3_mart folder with `meta.dataset: true`.

    :returns: List of available datasets.
    """
    try:
        manifest = _load_manifest()
    except FileNotFoundError:
        logger.warning("dbt manifest not found, returning empty dataset list")
        return []

    datasets = []
    nodes = manifest.get("nodes", {})

    for node_id, node in nodes.items():
        # Only look at models
        if not node_id.startswith("model."):
            continue

        # Check if this model is marked as a dataset
        meta = node.get("meta", {})
        if not meta.get("dataset"):
            continue

        # Extract dataset info
        dataset = Dataset(
            id=node.get("name", ""),
            friendly_name=meta.get("friendly_name", node.get("name", "")),
            description=node.get("description", ""),
            group=meta.get("group", "unknown"),
            time_grain=meta.get("time_grain"),
            schema_name=node.get("schema", "mart"),
            filters=_extract_filters(meta),
        )
        datasets.append(dataset)

    logger.debug(f"Found {len(datasets)} datasets in manifest")
    return datasets


def get_dataset_schema(dataset_id: str) -> Dataset | None:
    """Get detailed schema for a specific dataset.

    :param dataset_id: The dataset model name (e.g., "fct_transactions").
    :returns: Dataset with columns populated, or None if not found.
    """
    try:
        manifest = _load_manifest()
    except FileNotFoundError:
        return None

    # Find the model node
    node_key = f"model.dbt_project.{dataset_id}"
    node = manifest.get("nodes", {}).get(node_key)

    if not node:
        return None

    meta = node.get("meta", {})
    if not meta.get("dataset"):
        return None

    # Extract column info
    columns = []
    for col_name, col_info in node.get("columns", {}).items():
        columns.append(
            DatasetColumn(
                name=col_name,
                description=col_info.get("description", ""),
                data_type=col_info.get("data_type"),
            )
        )

    return Dataset(
        id=node.get("name", ""),
        friendly_name=meta.get("friendly_name", node.get("name", "")),
        description=node.get("description", ""),
        group=meta.get("group", "unknown"),
        time_grain=meta.get("time_grain"),
        schema_name=node.get("schema", "mart"),
        columns=columns,
        filters=_extract_filters(meta),
    )
