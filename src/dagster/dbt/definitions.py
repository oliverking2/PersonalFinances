"""Dbt Dagster Definitions."""

from dagster import Definitions

from src.dagster.dbt.assets import dbt_models
from src.dagster.dbt.resources import dbt_resource

dbt_defs = Definitions(
    resources={"dbt": dbt_resource},
    assets=[dbt_models],
)
