"""Recurring patterns Dagster definitions.

Defines assets and jobs for syncing recurring patterns.
"""

from dagster import (
    AssetSelection,
    Definitions,
    define_asset_job,
)

from src.orchestration.recurring_patterns.assets import sync_recurring_patterns

# Job to sync recurring patterns (for manual runs)
# The asset has automation_condition=any_deps_updated() so it runs automatically after dbt
sync_recurring_patterns_job = define_asset_job(
    name="sync_recurring_patterns_job",
    selection=AssetSelection.assets(sync_recurring_patterns),
    description="Sync detected recurring patterns from dbt mart to PostgreSQL.",
)

# Export definitions
recurring_patterns_defs = Definitions(
    assets=[sync_recurring_patterns],
    jobs=[sync_recurring_patterns_job],
)
