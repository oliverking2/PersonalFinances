"""Dagster assets for dbt."""

from typing import Generator, Optional, Mapping, Any

from dagster import (
    AssetExecutionContext,
    AutomationCondition,
)
from dagster_dbt import DbtCliResource, dbt_assets, DagsterDbtTranslator
from dagster_dbt.core.dbt_event_iterator import DbtEventIterator

from src.dagster.dbt.resources import dbt_project


class CustomDbtTranslator(DagsterDbtTranslator):
    """Override the default DagsterDbtTranslator to add custom automation conditions."""

    def get_automation_condition(
        self, dbt_resource_props: Mapping[str, Any]
    ) -> Optional[AutomationCondition]:
        """Add custom automation conditions for dbt resources."""
        tags: list[str] = dbt_resource_props.get("tags", [])

        # Eager: run whenever any upstream updates
        if "auto_eager" in tags:
            return AutomationCondition.eager()

        # Cron: run once per cron tick, after upstreams have updated
        if "auto_hourly" in tags:
            return AutomationCondition.on_cron("@hourly")

        # No automation for everything else; manual or scheduled via jobs
        return None


@dbt_assets(manifest=dbt_project.manifest_path, dagster_dbt_translator=CustomDbtTranslator())
def dbt_models(
    context: AssetExecutionContext, dbt: DbtCliResource
) -> Generator[DbtEventIterator, None, None]:
    """Materialise all dbt models via `dbt build`.

    Dagster treats each dbt model as a software defined asset.
    """
    yield from (
        dbt.cli(["build"], context=context).stream()
        # .fetch_row_counts()
        # .fetch_column_metadata()
    )
