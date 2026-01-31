"""Unified Dagster definitions.

Aggregates unified gate assets and provides scheduling.
"""

from dagster import (
    AssetSelection,
    Definitions,
    ScheduleDefinition,
    define_asset_job,
)

from src.orchestration.unified.assets import (
    sync_unified_accounts,
    sync_unified_connections,
    sync_unified_transactions,
)
from src.orchestration.unified.assets import (
    unified_defs as unified_asset_defs,
)

# Job to materialize unified gate assets (runs after provider syncs)
unified_sync_job = define_asset_job(
    name="unified_sync_job",
    selection=AssetSelection.assets(
        sync_unified_accounts,
        sync_unified_connections,
        sync_unified_transactions,
    ),
    description="Materialize unified gate assets after provider syncs complete.",
)

# Schedule to run at 4:45 AM (after GoCardless at 4 AM and Trading 212 at 4:30 AM)
unified_sync_schedule = ScheduleDefinition(
    job=unified_sync_job,
    cron_schedule="45 4 * * *",
)

# Merge all definitions
unified_defs = Definitions.merge(
    unified_asset_defs,
    Definitions(
        jobs=[unified_sync_job],
        schedules=[unified_sync_schedule],
    ),
)
