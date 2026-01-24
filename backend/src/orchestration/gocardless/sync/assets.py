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
from src.postgres.common.enums import AccountStatus, ConnectionStatus, Provider
from src.postgres.common.models import Account, Connection
from src.postgres.common.operations.sync import (
    mark_missing_accounts_inactive,
    sync_all_gocardless_accounts,
    sync_all_gocardless_connections,
    sync_all_gocardless_institutions,
    sync_all_gocardless_transactions,
)


@asset(
    key=AssetKey(["sync", "gocardless", "connections"]),
    deps=[AssetKey(["source", "gocardless", "extract", "requisitions"])],
    group_name="gocardless",
    description="Sync GoCardless requisitions to unified connections table.",
    required_resource_keys={"postgres_database"},
)
def sync_gc_connections(context: AssetExecutionContext) -> None:
    """Sync GoCardless requisitions to the unified connections table.

    This asset reads from gc_requisition_links and updates the
    connections table. Depends on requisition extraction to ensure
    gc_requisition_links has latest status from GoCardless.
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
    deps=[
        AssetKey(["sync", "gocardless", "connections"]),
        AssetKey(["source", "gocardless", "extract", "account_balances"]),
    ],
    group_name="gocardless",
    description="Sync GoCardless bank accounts to unified accounts table.",
    required_resource_keys={"postgres_database"},
)
def sync_gc_accounts(context: AssetExecutionContext) -> None:
    """Sync GoCardless bank accounts to the unified accounts table.

    This asset reads from gc_bank_accounts and gc_balances, then upserts
    to the accounts table. Depends on connection sync and balance extraction
    to ensure all data is up to date.
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


@asset(
    key=AssetKey(["sync", "gocardless", "institutions"]),
    deps=[AssetKey(["source", "gocardless", "extract", "institutions"])],
    group_name="gocardless",
    description="Sync GoCardless institutions to unified institutions table.",
    required_resource_keys={"postgres_database"},
)
def sync_gc_institutions(context: AssetExecutionContext) -> None:
    """Sync GoCardless institutions to the unified institutions table.

    This asset reads from gc_institutions and upserts to the
    institutions table. Depends on extraction asset to populate gc_institutions first.
    """
    postgres_database: PostgresDatabase = context.resources.postgres_database
    context.log.info("Starting GoCardless institution sync")

    with postgres_database.get_session() as session:
        institutions = sync_all_gocardless_institutions(session)

        if not institutions:
            context.log.warning(
                "No GoCardless institutions found to sync. "
                "Ensure gc_institutions is populated first."
            )
            return

        context.log.info(f"Synced {len(institutions)} institutions")


@asset(
    key=AssetKey(["sync", "gocardless", "transactions"]),
    deps=[
        AssetKey(["sync", "gocardless", "accounts"]),
        AssetKey(["source", "gocardless", "extract", "transactions"]),
    ],
    group_name="gocardless",
    description="Sync GoCardless transactions to unified transactions table.",
    required_resource_keys={"postgres_database"},
)
def sync_gc_transactions(context: AssetExecutionContext) -> None:
    """Sync GoCardless transactions to the unified transactions table.

    This asset reads from gc_transactions and upserts to the transactions table.
    Depends on account sync and transaction extraction to ensure all data is up to date.
    """
    postgres_database: PostgresDatabase = context.resources.postgres_database
    context.log.info("Starting GoCardless transaction sync")

    with postgres_database.get_session() as session:
        # Get all active accounts from active GoCardless connections
        accounts = (
            session.query(Account)
            .join(Connection)
            .filter(
                Connection.provider == Provider.GOCARDLESS.value,
                Connection.status == ConnectionStatus.ACTIVE.value,
                Account.status == AccountStatus.ACTIVE.value,
            )
            .all()
        )

        context.log.info(f"Found {len(accounts)} active GoCardless accounts")

        if not accounts:
            context.log.warning(
                "No active GoCardless accounts found. Ensure accounts are synced first."
            )
            return

        total_transactions = 0
        for account in accounts:
            transactions = sync_all_gocardless_transactions(session, account)
            total_transactions += len(transactions)

        context.log.info(
            f"Synced {total_transactions} transactions across {len(accounts)} accounts"
        )


sync_asset_defs = Definitions(
    assets=[
        sync_gc_connections,
        sync_gc_accounts,
        sync_gc_institutions,
        sync_gc_transactions,
    ]
)
