"""Dagster assets for dbt."""

from typing import Generator

from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets
from dagster_dbt.core.dbt_event_iterator import DbtEventIterator

from src.dagster.dbt.resources import dbt_project


@dbt_assets(
    manifest=dbt_project.manifest_path,
)
def dbt_models(
    context: AssetExecutionContext, dbt: DbtCliResource
) -> Generator[DbtEventIterator, None, None]:
    """Materialise all dbt models via `dbt build`.

    Dagster treats each dbt model as a software defined asset.
    """
    yield from dbt.cli(["build"], context=context).stream()
