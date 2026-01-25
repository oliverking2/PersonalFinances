"""Dbt Dagster Definitions."""

from dagster import AssetSelection, Definitions, define_asset_job

from src.orchestration.dbt.assets import dbt_models
from src.orchestration.dbt.resources import dbt_resource

# Job to trigger all dbt models manually
dbt_build_job = define_asset_job(
    name="dbt_build_job",
    selection=AssetSelection.assets(dbt_models),
    description="Build all dbt models (run + test).",
)

dbt_defs = Definitions(
    resources={"dbt": dbt_resource},
    assets=[dbt_models],
    jobs=[dbt_build_job],
)
