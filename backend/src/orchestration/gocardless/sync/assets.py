"""GoCardless Dagster Sync Assets.

These assets sync data from raw GoCardless tables (gc_requisition_links,
gc_bank_accounts, gc_balances) to the unified tables (connections, accounts).
"""

from dagster import (
    AssetExecutionContext,
    AssetKey,
    Definitions,
    asset,
)

from src.orchestration.resources import PostgresDatabase
from src.postgres.common.enums import ConnectionStatus, Provider
from src.postgres.common.models import Connection
from src.postgres.common.operations.sync import (
    mark_missing_accounts_inactive,
    sync_all_gocardless_accounts,
    sync_all_gocardless_connections,
)


@asset(
    key=AssetKey(["sync", "gocardless", "connections"]),
    group_name="gocardless",
    description="Sync GoCardless requisitions to unified connections table.",
    required_resource_keys={"postgres_database"},
)
def sync_gc_connections(context: AssetExecutionContext) -> None:
    """Sync GoCardless requisitions to the unified connections table.

    This asset reads from gc_requisition_links and updates the
    connections table. It syncs all GoCardless connections regardless of user.
    """
    postgres_database: PostgresDatabase = context.resources.postgres_database
    context.log.info("Starting GoCardless connection sync")

    with postgres_database.get_session() as session:
        connections = sync_all_gocardless_connections(session)

        if not connections:
            context.log.warning(
                "No GoCardless connections found to sync. "
                "Ensure connections exist in the 'connections' table with provider='gocardless'."
            )
            return

        active_count = sum(1 for c in connections if c.status == ConnectionStatus.ACTIVE.value)
        expired_count = sum(1 for c in connections if c.status == ConnectionStatus.EXPIRED.value)
        context.log.info(
            f"Synced {len(connections)} connections: {active_count} active, {expired_count} expired"
        )


@asset(
    key=AssetKey(["sync", "gocardless", "accounts"]),
    deps=[AssetKey(["sync", "gocardless", "connections"])],
    group_name="gocardless",
    description="Sync GoCardless bank accounts to unified accounts table.",
    required_resource_keys={"postgres_database"},
)
def sync_gc_accounts(context: AssetExecutionContext) -> None:
    """Sync GoCardless bank accounts to the unified accounts table.

    This asset reads from gc_bank_accounts and gc_balances, then upserts
    to the accounts table. It depends on sync_gc_connections to ensure
    connection statuses are updated first.
    """
    postgres_database: PostgresDatabase = context.resources.postgres_database
    context.log.info("Starting GoCardless account sync")

    with postgres_database.get_session() as session:
        # Get all active GoCardless connections
        connections = (
            session.query(Connection)
            .filter(
                Connection.provider == Provider.GOCARDLESS.value,
                Connection.status == ConnectionStatus.ACTIVE.value,
            )
            .all()
        )

        context.log.info(f"Found {len(connections)} active GoCardless connections")

        if not connections:
            # Check if there are any connections at all to provide better diagnostics
            all_gc_connections = (
                session.query(Connection)
                .filter(Connection.provider == Provider.GOCARDLESS.value)
                .all()
            )
            if all_gc_connections:
                statuses: dict[str, int] = {}
                for conn in all_gc_connections:
                    statuses[conn.status] = statuses.get(conn.status, 0) + 1
                context.log.warning(
                    f"No active connections found, but {len(all_gc_connections)} GoCardless "
                    f"connections exist with statuses: {statuses}"
                )
            else:
                context.log.warning(
                    "No GoCardless connections found in database. "
                    "Ensure you have created a connection via the API first."
                )
            return

        total_accounts = 0
        for connection in connections:
            accounts = sync_all_gocardless_accounts(session, connection)
            total_accounts += len(accounts)

            # Mark any missing accounts as inactive
            synced_ids = {acc.provider_id for acc in accounts}
            inactive_count = mark_missing_accounts_inactive(session, connection, synced_ids)
            if inactive_count:
                context.log.info(
                    f"Marked {inactive_count} accounts inactive for connection {connection.id}"
                )

        context.log.info(f"Synced {total_accounts} accounts across {len(connections)} connections")


sync_asset_defs = Definitions(
    assets=[
        sync_gc_connections,
        sync_gc_accounts,
    ]
)
