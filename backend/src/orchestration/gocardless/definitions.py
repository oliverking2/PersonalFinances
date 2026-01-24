"""GoCardless Dagster Definitions."""

from dagster import (
    AssetSelection,
    Definitions,
    ScheduleDefinition,
    define_asset_job,
)

from src.orchestration.gocardless.background_jobs.definitions import gocardless_background_job_defs
from src.orchestration.gocardless.extraction.assets import extraction_asset_defs
from src.orchestration.gocardless.sync.assets import sync_asset_defs

# Create a job that runs all assets in the "gocardless" group
gocardless_sync_job = define_asset_job(
    name="gocardless_sync_job",
    selection=AssetSelection.groups("gocardless"),
    description="Extract data from GoCardless API and sync to unified tables.",
)

# Schedule the job to run daily at 4 AM
gocardless_sync_schedule = ScheduleDefinition(
    job=gocardless_sync_job,
    cron_schedule="0 4 * * *",
)

# Merge all definitions
gocardless_defs = Definitions.merge(
    extraction_asset_defs,
    gocardless_background_job_defs,
    sync_asset_defs,
    Definitions(
        jobs=[gocardless_sync_job],
        schedules=[gocardless_sync_schedule],
    ),
)
