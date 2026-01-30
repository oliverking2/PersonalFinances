"""Unified sync assets for multi-provider dbt dependencies.

These assets don't perform any work - they exist purely to provide a single
dependency point for dbt models that need to wait for all providers to sync.
"""

from dagster import AssetKey, Definitions, asset


@asset(
    key=AssetKey(["sync", "unified", "accounts"]),
    deps=[
        AssetKey(["sync", "gocardless", "accounts"]),
        AssetKey(["sync", "trading212", "accounts"]),
    ],
    group_name="unified",
    description="Unified accounts sync gate - depends on all provider account syncs.",
)
def sync_unified_accounts() -> None:
    """Gate asset for unified accounts table.

    This asset has no implementation - it exists to provide a single
    dependency point for dbt models that read from the accounts table.
    """


@asset(
    key=AssetKey(["sync", "unified", "connections"]),
    deps=[
        AssetKey(["sync", "gocardless", "connections"]),
        AssetKey(["sync", "trading212", "connections"]),
    ],
    group_name="unified",
    description="Unified connections sync gate - depends on all provider connection syncs.",
)
def sync_unified_connections() -> None:
    """Gate asset for unified connections table.

    This asset has no implementation - it exists to provide a single
    dependency point for dbt models that read from the connections table.
    """


@asset(
    key=AssetKey(["sync", "unified", "transactions"]),
    deps=[
        AssetKey(["sync", "gocardless", "transactions"]),
        AssetKey(["sync", "trading212", "transactions"]),
    ],
    group_name="unified",
    description="Unified transactions sync gate - depends on all provider transaction syncs.",
)
def sync_unified_transactions() -> None:
    """Gate asset for unified transactions table.

    This asset has no implementation - it exists to provide a single
    dependency point for dbt models that read from the transactions table.
    """


unified_defs = Definitions(
    assets=[
        sync_unified_accounts,
        sync_unified_connections,
        sync_unified_transactions,
    ]
)
