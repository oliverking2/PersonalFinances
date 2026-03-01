"""Dagster assets for dbt."""

from collections.abc import Generator
from typing import Any

from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets

from src.orchestration.dbt.resources import dbt_project


@dbt_assets(manifest=dbt_project.manifest_path)
def dbt_models(context: AssetExecutionContext, dbt: DbtCliResource) -> Generator[Any]:
    """Materialise all dbt models via `dbt build`.

    Dagster treats each dbt model as a software defined asset.
    """
    yield from (
        dbt.cli(["build"], context=context).stream().fetch_row_counts().fetch_column_metadata()
    )
