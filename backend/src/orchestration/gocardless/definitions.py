"""GoCardless Dagster Definitions."""

from dagster import (
    AssetKey,
    AssetSelection,
    Definitions,
    ScheduleDefinition,
    define_asset_job,
)

from src.orchestration.gocardless.background_jobs.daily_jobs import daily_job_defs
from src.orchestration.gocardless.extraction.assets import extraction_asset_defs
from src.orchestration.gocardless.sync.assets import sync_asset_defs

# Full sync job - runs all assets including global ones (institutions, requisitions)
# Used by the daily schedule
gocardless_sync_job = define_asset_job(
    name="gocardless_sync_job",
    selection=AssetSelection.groups("gocardless"),
    description="Full sync: extract all data from GoCardless API and sync to unified tables.",
)

# Connection-scoped sync job - only runs assets relevant to a specific connection
# Excludes institutions and requisitions (global data)
# Used for manual refresh and post-OAuth sync
CONNECTION_SYNC_ASSETS = [
    # Extraction (from GoCardless API to raw tables)
    # bank_accounts must run first to create BankAccount records before other assets can use them
    AssetKey(["source", "gocardless", "extract", "bank_accounts"]),
    AssetKey(["source", "gocardless", "extract", "transactions"]),
    AssetKey(["source", "gocardless", "extract", "account_details"]),
    AssetKey(["source", "gocardless", "extract", "account_balances"]),
    # Sync (from raw tables to unified tables)
    AssetKey(["sync", "gocardless", "accounts"]),
    AssetKey(["sync", "gocardless", "transactions"]),
]

gocardless_connection_sync_job = define_asset_job(
    name="gocardless_connection_sync_job",
    selection=AssetSelection.assets(*CONNECTION_SYNC_ASSETS),
    description="Connection-scoped sync: extract and sync data for a specific connection.",
)

# Schedule the full job to run daily at 4 AM
gocardless_sync_schedule = ScheduleDefinition(
    job=gocardless_sync_job,
    cron_schedule="0 4 * * *",
)

# Merge all definitions
gocardless_defs = Definitions.merge(
    extraction_asset_defs,
    daily_job_defs,
    sync_asset_defs,
    Definitions(
        jobs=[gocardless_sync_job, gocardless_connection_sync_job],
        schedules=[gocardless_sync_schedule],
    ),
)
