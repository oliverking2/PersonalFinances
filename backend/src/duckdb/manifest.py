"""dbt manifest parser for dataset discovery.

Parses the dbt manifest.json to discover available datasets and their schemas.
Datasets are dbt models with `meta.dataset: true` in their schema.yml.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

from src.filepaths import BACKEND_DIR

# Namespace for generating deterministic UUIDs from dataset names
DATASET_UUID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace

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

    id: UUID  # Deterministic UUID generated from model name
    name: str  # dbt model name (e.g., "fct_transactions")
    friendly_name: str
    description: str
    group: str  # "facts", "dimensions", "aggregations"
    time_grain: str | None = None  # "day", "month", etc.
    schema_name: str = "mart"
    columns: list[DatasetColumn] | None = None
    filters: DatasetFilters = field(default_factory=DatasetFilters)


def _generate_dataset_id(name: str) -> UUID:
    """Generate a deterministic UUID for a dataset from its name.

    :param name: dbt model name.
    :returns: UUID5 based on the name.
    """
    return uuid.uuid5(DATASET_UUID_NAMESPACE, name)


def _get_manifest_path() -> Path:
    """Get the path to the dbt manifest.json file.

    :returns: Path to manifest.json.
    :raises FileNotFoundError: If manifest doesn't exist.
    """
    # Default path relative to backend directory
    manifest_path = BACKEND_DIR / "dbt" / "target" / "manifest.json"

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


def _load_catalog() -> dict[str, Any] | None:
    """Load and parse the dbt catalog.json if available.

    The catalog contains actual column types from the database.

    :returns: Parsed catalog dictionary, or None if not available.
    """
    catalog_path = BACKEND_DIR / "dbt" / "target" / "catalog.json"

    if not catalog_path.exists():
        logger.debug("dbt catalog not found, column types will be unavailable")
        return None

    with catalog_path.open() as f:
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
        model_name = node.get("name", "")
        dataset = Dataset(
            id=_generate_dataset_id(model_name),
            name=model_name,
            friendly_name=meta.get("friendly_name", model_name),
            description=node.get("description", ""),
            group=meta.get("group", "unknown"),
            time_grain=meta.get("time_grain"),
            schema_name=node.get("schema", "mart"),
            filters=_extract_filters(meta),
        )
        datasets.append(dataset)

    logger.debug(f"Found {len(datasets)} datasets in manifest")
    return datasets


def get_dataset_schema(dataset_id: UUID | str) -> Dataset | None:
    """Get detailed schema for a specific dataset.

    :param dataset_id: The dataset UUID or model name (e.g., "fct_transactions").
    :returns: Dataset with columns populated, or None if not found.
    """
    try:
        manifest = _load_manifest()
    except FileNotFoundError:
        return None

    # If UUID provided, find matching dataset by iterating
    if isinstance(dataset_id, UUID):
        for node_id, node in manifest.get("nodes", {}).items():
            if not node_id.startswith("model."):
                continue
            model_name = node.get("name", "")
            if _generate_dataset_id(model_name) == dataset_id:
                meta = node.get("meta", {})
                if meta.get("dataset"):
                    return _build_dataset_with_columns(node, meta, model_name)
        return None

    # String provided - look up by model name
    node_key = f"model.dbt_project.{dataset_id}"
    node = manifest.get("nodes", {}).get(node_key)

    if not node:
        return None

    meta = node.get("meta", {})
    if not meta.get("dataset"):
        return None

    model_name = node.get("name", "")
    return _build_dataset_with_columns(node, meta, model_name)


def _build_dataset_with_columns(
    node: dict[str, Any], meta: dict[str, Any], model_name: str
) -> Dataset:
    """Build a Dataset with columns from a manifest node.

    Merges column descriptions from manifest with types from catalog.

    :param node: Manifest node dictionary.
    :param meta: Node metadata dictionary.
    :param model_name: dbt model name.
    :returns: Dataset with columns populated.
    """
    # Load catalog for column types
    catalog = _load_catalog()
    catalog_columns: dict[str, dict[str, Any]] = {}

    if catalog:
        node_key = f"model.dbt_project.{model_name}"
        catalog_node = catalog.get("nodes", {}).get(node_key, {})
        catalog_columns = catalog_node.get("columns", {})

    # Build columns from manifest, enriched with catalog types
    columns = []
    manifest_columns = node.get("columns", {})

    # If manifest has columns defined, use those (preserves order and descriptions)
    if manifest_columns:
        for col_name, col_info in manifest_columns.items():
            # Look up type from catalog (case-insensitive match)
            data_type = None
            for cat_col_name, cat_col_info in catalog_columns.items():
                if cat_col_name.lower() == col_name.lower():
                    data_type = cat_col_info.get("type")
                    break

            columns.append(
                DatasetColumn(
                    name=col_name,
                    description=col_info.get("description", ""),
                    data_type=data_type,
                )
            )
    # Otherwise, use catalog columns directly
    elif catalog_columns:
        for col_name, col_info in catalog_columns.items():
            columns.append(
                DatasetColumn(
                    name=col_name.lower(),  # Normalize to lowercase
                    description="",
                    data_type=col_info.get("type"),
                )
            )

    return Dataset(
        id=_generate_dataset_id(model_name),
        name=model_name,
        friendly_name=meta.get("friendly_name", model_name),
        description=node.get("description", ""),
        group=meta.get("group", "unknown"),
        time_grain=meta.get("time_grain"),
        schema_name=node.get("schema", "mart"),
        columns=columns,
        filters=_extract_filters(meta),
    )
