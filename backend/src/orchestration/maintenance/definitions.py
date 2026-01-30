"""Dagster definitions for maintenance jobs."""

from dagster import Definitions

from src.orchestration.maintenance.jobs import (
    maintenance_cleanup_job,
    maintenance_cleanup_schedule,
)

maintenance_defs = Definitions(
    jobs=[maintenance_cleanup_job],
    schedules=[maintenance_cleanup_schedule],
)
