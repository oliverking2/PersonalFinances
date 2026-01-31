"""Dbt Dagster Definitions."""

from dagster import AssetSelection, Definitions, ScheduleDefinition, define_asset_job

from src.orchestration.dbt.assets import dbt_models
from src.orchestration.dbt.resources import dbt_resource

# Job to trigger all dbt models manually
dbt_build_job = define_asset_job(
    name="dbt_build_job",
    selection=AssetSelection.assets(dbt_models),
    description="Build all dbt models (run + test).",
)

# Schedule the dbt build to run daily at 5 AM (after provider syncs complete)
dbt_build_schedule = ScheduleDefinition(
    job=dbt_build_job,
    cron_schedule="0 5 * * *",
)

dbt_defs = Definitions(
    resources={"dbt": dbt_resource},
    assets=[dbt_models],
    jobs=[dbt_build_job],
    schedules=[dbt_build_schedule],
)
