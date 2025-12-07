"""Dagster assets for dbt."""

from typing import Generator

import dagster as dg
from dagster_dbt import DbtCliResource, dbt_assets

from src.dagster.dbt.resources import dbt_project


@dbt_assets(manifest=dbt_project.manifest_path)
def dbt_models(
    context: dg.AssetExecutionContext, dbt: DbtCliResource
) -> Generator[dg.Event, None, None]:
    """Materialise all dbt models via `dbt build`.

    Dagster treats each dbt model as a software defined asset.
    """
    yield from dbt.cli(["build"], context=context).stream()
