"""GoCardless Dagster Schedules."""

from dagster import ScheduleDefinition

from src.dagster.ingestion.gocardless.jobs import requisition_sync_job

# update requisitions every hour
gocardless_requisition_schedule = ScheduleDefinition(
    job=requisition_sync_job, cron_schedule="0 * * * *"
)
