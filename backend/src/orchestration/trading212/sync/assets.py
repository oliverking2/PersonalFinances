"""Trading 212 Dagster Sync Assets.

These assets sync data from raw Trading 212 tables (t212_api_keys,
t212_cash_balances) to the unified tables (connections, accounts).
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
from src.postgres.common.enums import ConnectionStatus, Provider
from src.postgres.common.models import Account, Connection
from src.postgres.common.operations.sync import (
    sync_all_trading212_accounts,
    sync_all_trading212_connections,
    sync_all_trading212_transactions,
    sync_trading212_connection,
)
from src.postgres.trading212.models import T212ApiKey


class T212SyncConfig(Config):
    """Config for scoping sync to a specific API key."""

    api_key_id: Optional[str] = None


def _get_api_key_and_connection(
    session: Session, api_key_id: str, context: AssetExecutionContext
) -> tuple[Optional[T212ApiKey], Optional[Connection]]:
    """Get API key and its associated connection for syncing.

    :param session: SQLAlchemy session.
    :param api_key_id: API key UUID as string.
    :param context: Asset execution context for logging.
    :returns: Tuple of (api_key, connection) or (None, None) if not found.
    """
    try:
        key_uuid = UUID(api_key_id)
    except ValueError:
        context.log.error(f"Invalid api_key_id format: {api_key_id}")
        return None, None

    api_key = session.get(T212ApiKey, key_uuid)
    if api_key is None:
        context.log.error(f"API key not found: {api_key_id}")
        return None, None

    # Find the associated connection
    connection = (
        session.query(Connection)
        .filter(
            Connection.provider == Provider.TRADING212.value,
            Connection.provider_id == api_key_id,
        )
        .first()
    )

    context.log.info(f"Scoped sync to API key {api_key_id}")
    return api_key, connection


@asset(
    key=AssetKey(["sync", "trading212", "connections"]),
    deps=[AssetKey(["source", "trading212", "extract", "cash"])],
    group_name="trading212",
    description="Sync Trading 212 API keys to unified connections table.",
    required_resource_keys={"postgres_database"},
)
def sync_t212_connections(context: AssetExecutionContext, config: T212SyncConfig) -> None:
    """Sync Trading 212 API keys to the unified connections table.

    This asset reads from t212_api_keys and updates the connections table.
    Depends on cash extraction to ensure API key status is up to date.
    """
    postgres_database: PostgresDatabase = context.resources.postgres_database
    context.log.info("Starting Trading 212 connection sync")

    with postgres_database.get_session() as session:
        # If scoped to a specific API key, sync only that one
        if config.api_key_id:
            api_key, _ = _get_api_key_and_connection(session, config.api_key_id, context)
            if api_key is None:
                return  # Error already logged

            synced = sync_trading212_connection(session, api_key)
            context.log.info(f"Synced single connection: id={synced.id}, status={synced.status}")
            return

        # Otherwise sync all connections
        connections = sync_all_trading212_connections(session)

        if not connections:
            context.log.info("No Trading 212 connections to sync")
            return

        active_count = sum(1 for c in connections if c.status == ConnectionStatus.ACTIVE.value)
        error_count = sum(1 for c in connections if c.status == ConnectionStatus.ERROR.value)
        context.log.info(
            f"Synced {len(connections)} connections: {active_count} active, {error_count} error"
        )


@asset(
    key=AssetKey(["sync", "trading212", "accounts"]),
    deps=[AssetKey(["sync", "trading212", "connections"])],
    group_name="trading212",
    description="Sync Trading 212 accounts to unified accounts table.",
    required_resource_keys={"postgres_database"},
)
def sync_t212_accounts(context: AssetExecutionContext, config: T212SyncConfig) -> None:
    """Sync Trading 212 accounts to the unified accounts table.

    This asset reads from t212_api_keys and t212_cash_balances, then upserts
    to the accounts table. Depends on connection sync to ensure all data is up to date.
    """
    postgres_database: PostgresDatabase = context.resources.postgres_database
    context.log.info("Starting Trading 212 account sync")

    with postgres_database.get_session() as session:
        # If scoped to a specific API key, sync only that connection
        if config.api_key_id:
            _, connection = _get_api_key_and_connection(session, config.api_key_id, context)
            if connection is None:
                context.log.warning(f"No connection found for API key {config.api_key_id}")
                return

            accounts = sync_all_trading212_accounts(session, connection)
            context.log.info(f"Synced {len(accounts)} accounts for connection {connection.id}")
            return

        # Otherwise sync all active connections
        connections = (
            session.query(Connection)
            .filter(
                Connection.provider == Provider.TRADING212.value,
                Connection.status == ConnectionStatus.ACTIVE.value,
            )
            .all()
        )

        context.log.info(f"Found {len(connections)} active Trading 212 connections")

        if not connections:
            context.log.info("No active Trading 212 connections to sync accounts for")
            return

        total_accounts = 0
        for connection in connections:
            accounts = sync_all_trading212_accounts(session, connection)
            total_accounts += len(accounts)

        context.log.info(f"Synced {total_accounts} accounts across {len(connections)} connections")


@asset(
    key=AssetKey(["sync", "trading212", "transactions"]),
    deps=[
        AssetKey(["sync", "trading212", "accounts"]),
        AssetKey(["source", "trading212", "extract", "orders"]),
        AssetKey(["source", "trading212", "extract", "dividends"]),
        AssetKey(["source", "trading212", "extract", "transactions"]),
    ],
    group_name="trading212",
    description="Sync Trading 212 orders, dividends, and transactions to unified transactions table.",
    required_resource_keys={"postgres_database"},
)
def sync_t212_transactions(context: AssetExecutionContext, config: T212SyncConfig) -> None:
    """Sync Trading 212 transactions to the unified transactions table.

    This asset reads from t212_orders, t212_dividends, and t212_transactions,
    then upserts to the unified transactions table. Depends on accounts sync
    to ensure accounts exist before creating transactions.
    """
    postgres_database: PostgresDatabase = context.resources.postgres_database
    context.log.info("Starting Trading 212 transaction sync")

    with postgres_database.get_session() as session:
        # If scoped to a specific API key, sync only that connection
        if config.api_key_id:
            _, connection = _get_api_key_and_connection(session, config.api_key_id, context)
            if connection is None:
                context.log.warning(f"No connection found for API key {config.api_key_id}")
                return

            # Get the account for this connection
            account = session.query(Account).filter(Account.connection_id == connection.id).first()
            if account is None:
                context.log.warning(f"No account found for connection {connection.id}")
                return

            txns = sync_all_trading212_transactions(session, account, config.api_key_id)
            context.log.info(f"Synced {len(txns)} transactions for connection {connection.id}")
            return

        # Otherwise sync all active connections
        connections = (
            session.query(Connection)
            .filter(
                Connection.provider == Provider.TRADING212.value,
                Connection.status == ConnectionStatus.ACTIVE.value,
            )
            .all()
        )

        context.log.info(f"Found {len(connections)} active Trading 212 connections")

        if not connections:
            context.log.info("No active Trading 212 connections to sync transactions for")
            return

        total_transactions = 0
        for connection in connections:
            # Get the account for this connection
            account = session.query(Account).filter(Account.connection_id == connection.id).first()
            if account is None:
                context.log.warning(f"No account found for connection {connection.id}, skipping")
                continue

            txns = sync_all_trading212_transactions(session, account, connection.provider_id)
            total_transactions += len(txns)

        context.log.info(
            f"Synced {total_transactions} transactions across {len(connections)} connections"
        )


sync_asset_defs = Definitions(
    assets=[
        sync_t212_connections,
        sync_t212_accounts,
        sync_t212_transactions,
    ]
)
