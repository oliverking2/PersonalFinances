"""GoCardless Dagster Sync Assets.

These assets sync data from raw GoCardless tables (gc_requisition_links,
gc_bank_accounts, gc_balances) to the unified tables (connections, accounts).

Assets can be configured with a connection_id to filter to a specific connection:
    run_config = {"ops": {"*": {"config": {"connection_id": "uuid-here"}}}}
"""

from typing import Optional
from uuid import UUID

from dagster import (
    AssetExecutionContext,
    AssetKey,
    Config,
    Definitions,
    asset,
)
from sqlalchemy.orm import Session

from src.orchestration.resources import PostgresDatabase
from src.postgres.common.enums import AccountStatus, ConnectionStatus, Provider
from src.postgres.common.models import Account, Connection
from src.postgres.common.operations.notifications import check_budgets_and_notify
from src.postgres.common.operations.sync import (
    mark_missing_accounts_inactive,
    sync_all_gocardless_accounts,
    sync_all_gocardless_connections,
    sync_all_gocardless_institutions,
    sync_all_gocardless_transactions,
    sync_gocardless_connection,
)
from src.postgres.common.operations.tag_rules import bulk_apply_rules


class ConnectionScopeConfig(Config):
    """Config for scoping sync to a specific connection."""

    connection_id: Optional[str] = None


def _get_connection_for_sync(
    session: Session, connection_id: str, context: AssetExecutionContext
) -> Optional[Connection]:
    """Get a specific connection for syncing.

    :param session: SQLAlchemy session.
    :param connection_id: Connection UUID as string.
    :param context: Asset execution context for logging.
    :returns: Connection or None if not found.
    """
    try:
        conn_uuid = UUID(connection_id)
    except ValueError:
        context.log.error(f"Invalid connection_id format: {connection_id}")
        return None

    connection = session.get(Connection, conn_uuid)
    if connection is None:
        context.log.error(f"Connection not found: {connection_id}")
        return None

    if connection.provider != Provider.GOCARDLESS.value:
        context.log.error(f"Connection {connection_id} is not a GoCardless connection")
        return None

    context.log.info(f"Scoped sync to connection {connection_id}")
    return connection


@asset(
    key=AssetKey(["sync", "gocardless", "connections"]),
    deps=[AssetKey(["source", "gocardless", "extract", "requisitions"])],
    group_name="gocardless",
    description="Sync GoCardless requisitions to unified connections table.",
    required_resource_keys={"postgres_database"},
)
def sync_gc_connections(context: AssetExecutionContext, config: ConnectionScopeConfig) -> None:
    """Sync GoCardless requisitions to the unified connections table.

    This asset reads from gc_requisition_links and updates the
    connections table. Depends on requisition extraction to ensure
    gc_requisition_links has latest status from GoCardless.
    """
    postgres_database: PostgresDatabase = context.resources.postgres_database
    context.log.info("Starting GoCardless connection sync")

    with postgres_database.get_session() as session:
        # If scoped to a specific connection, sync only that one
        if config.connection_id:
            connection = _get_connection_for_sync(session, config.connection_id, context)
            if connection is None:
                return  # Error already logged

            synced = sync_gocardless_connection(session, connection)
            context.log.info(f"Synced single connection: id={synced.id}, status={synced.status}")
            return

        # Otherwise sync all connections
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
def sync_gc_accounts(context: AssetExecutionContext, config: ConnectionScopeConfig) -> None:
    """Sync GoCardless bank accounts to the unified accounts table.

    This asset reads from gc_bank_accounts and gc_balances, then upserts
    to the accounts table. Depends on connection sync and balance extraction
    to ensure all data is up to date.
    """
    postgres_database: PostgresDatabase = context.resources.postgres_database
    context.log.info("Starting GoCardless account sync")

    with postgres_database.get_session() as session:
        # If scoped to a specific connection, sync only that one
        if config.connection_id:
            connection = _get_connection_for_sync(session, config.connection_id, context)
            if connection is None:
                return  # Error already logged

            if connection.status != ConnectionStatus.ACTIVE.value:
                context.log.warning(
                    f"Connection {connection.id} is not active (status={connection.status}), "
                    f"skipping account sync"
                )
                return

            accounts = sync_all_gocardless_accounts(session, connection)
            synced_ids = {acc.provider_id for acc in accounts}
            inactive_count = mark_missing_accounts_inactive(session, connection, synced_ids)
            if inactive_count:
                context.log.info(
                    f"Marked {inactive_count} accounts inactive for connection {connection.id}"
                )
            context.log.info(f"Synced {len(accounts)} accounts for connection {connection.id}")
            return

        # Otherwise sync all active connections
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
def sync_gc_institutions(context: AssetExecutionContext, config: ConnectionScopeConfig) -> None:
    """Sync GoCardless institutions to the unified institutions table.

    This asset reads from gc_institutions and upserts to the
    institutions table. Depends on extraction asset to populate gc_institutions first.

    Note: This asset does not filter by connection_id as institutions are global.
    The config parameter is accepted for consistency with other sync assets.
    """
    postgres_database: PostgresDatabase = context.resources.postgres_database
    context.log.info("Starting GoCardless institution sync")

    # Institutions are global, not connection-scoped
    if config.connection_id:
        context.log.info(
            "connection_id provided but institutions are global - syncing all institutions"
        )

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
    description="Sync GoCardless transactions to unified transactions table and apply auto-tagging rules.",
    required_resource_keys={"postgres_database"},
)
def sync_gc_transactions(context: AssetExecutionContext, config: ConnectionScopeConfig) -> None:  # noqa: PLR0912
    """Sync GoCardless transactions to the unified transactions table.

    This asset reads from gc_transactions and upserts to the transactions table.
    After syncing, applies auto-tagging rules to any untagged transactions.
    Depends on account sync and transaction extraction to ensure all data is up to date.
    """
    postgres_database: PostgresDatabase = context.resources.postgres_database
    context.log.info("Starting GoCardless transaction sync")

    with postgres_database.get_session() as session:
        # If scoped to a specific connection, sync only accounts for that connection
        if config.connection_id:
            connection = _get_connection_for_sync(session, config.connection_id, context)
            if connection is None:
                return  # Error already logged

            accounts = (
                session.query(Account)
                .filter(
                    Account.connection_id == connection.id,
                    Account.status == AccountStatus.ACTIVE.value,
                )
                .all()
            )

            if not accounts:
                context.log.warning(f"No active accounts found for connection {connection.id}")
                return

            total_transactions = 0
            for account in accounts:
                transactions = sync_all_gocardless_transactions(session, account)
                total_transactions += len(transactions)

            context.log.info(
                f"Synced {total_transactions} transactions for connection {connection.id}"
            )

            # Apply auto-tagging rules to untagged transactions for this user
            tagged_count = bulk_apply_rules(
                session,
                connection.user_id,
                account_ids=[acc.id for acc in accounts],
                untagged_only=True,
            )
            if tagged_count > 0:
                context.log.info(
                    f"Auto-tagged {tagged_count} transactions for user {connection.user_id}"
                )

            # Check budgets and create notifications if thresholds are exceeded
            notifications_created = check_budgets_and_notify(session, connection.user_id)
            if notifications_created > 0:
                context.log.info(
                    f"Created {notifications_created} budget notifications for user {connection.user_id}"
                )
            return

        # Otherwise sync all active accounts from all active connections
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

        # Apply auto-tagging rules for each user with synced accounts
        # Group accounts by user to apply rules once per user
        user_accounts: dict[UUID, list[UUID]] = {}
        for account in accounts:
            user_id = account.connection.user_id
            if user_id not in user_accounts:
                user_accounts[user_id] = []
            user_accounts[user_id].append(account.id)

        total_tagged = 0
        total_notifications = 0
        for user_id, account_ids in user_accounts.items():
            tagged_count = bulk_apply_rules(
                session,
                user_id,
                account_ids=account_ids,
                untagged_only=True,
            )
            total_tagged += tagged_count
            if tagged_count > 0:
                context.log.info(f"Auto-tagged {tagged_count} transactions for user {user_id}")

            # Check budgets and create notifications for each user
            notifications_created = check_budgets_and_notify(session, user_id)
            total_notifications += notifications_created
            if notifications_created > 0:
                context.log.info(
                    f"Created {notifications_created} budget notifications for user {user_id}"
                )

        if total_tagged > 0:
            context.log.info(f"Total auto-tagged: {total_tagged} transactions")

        if total_notifications > 0:
            context.log.info(f"Total budget notifications created: {total_notifications}")


sync_asset_defs = Definitions(
    assets=[
        sync_gc_connections,
        sync_gc_accounts,
        sync_gc_institutions,
        sync_gc_transactions,
    ]
)
