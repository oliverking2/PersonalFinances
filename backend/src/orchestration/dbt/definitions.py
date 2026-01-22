"""Dbt Dagster Definitions."""

from dagster import Definitions

from src.orchestration.dbt.assets import dbt_models
from src.orchestration.dbt.resources import dbt_resource

dbt_defs = Definitions(
    resources={"dbt": dbt_resource},
    assets=[dbt_models],
)
