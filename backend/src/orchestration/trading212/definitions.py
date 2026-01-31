"""Trading 212 Dagster definitions.

Aggregates extraction and sync assets for Trading 212 integration.
"""

from dagster import (
    AssetKey,
    AssetSelection,
    Definitions,
    ScheduleDefinition,
    define_asset_job,
)

from src.orchestration.trading212.extraction.assets import extraction_asset_defs
from src.orchestration.trading212.sync.assets import sync_asset_defs

# Trading 212 sync job - runs extraction and sync assets
# Used for manual refresh from the UI
TRADING212_SYNC_ASSETS = [
    # Extraction (from Trading 212 API to raw tables)
    AssetKey(["source", "trading212", "extract", "cash"]),
    AssetKey(["source", "trading212", "extract", "orders"]),
    AssetKey(["source", "trading212", "extract", "dividends"]),
    AssetKey(["source", "trading212", "extract", "transactions"]),
    # Sync (from raw tables to unified tables)
    AssetKey(["sync", "trading212", "connections"]),
    AssetKey(["sync", "trading212", "accounts"]),
    AssetKey(["sync", "trading212", "transactions"]),
]

trading212_sync_job = define_asset_job(
    name="trading212_sync_job",
    selection=AssetSelection.assets(*TRADING212_SYNC_ASSETS),
    description="Sync Trading 212: extract cash/orders/dividends/transactions and sync to unified tables.",
)

# Schedule the sync job to run daily at 4:30 AM (after GoCardless at 4 AM)
trading212_sync_schedule = ScheduleDefinition(
    job=trading212_sync_job,
    cron_schedule="30 4 * * *",
)

# Merge all definitions
trading212_defs = Definitions.merge(
    extraction_asset_defs,
    sync_asset_defs,
    Definitions(
        jobs=[trading212_sync_job],
        schedules=[trading212_sync_schedule],
    ),
)
