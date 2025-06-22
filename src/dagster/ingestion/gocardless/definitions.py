"""GoCardless Dagster Definitions."""

from dagster import Definitions

from src.dagster.ingestion.gocardless.schedules import gocardless_requisition_schedule

defs = Definitions(
    schedules=[gocardless_requisition_schedule],
)
