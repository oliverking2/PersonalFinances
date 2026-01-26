"""GoCardless Dagster Extraction Assets.

These assets extract data from the GoCardless API and write to Postgres.
dbt then reads from Postgres and transforms into DuckDB for analytics.

Assets can be configured with a connection_id to filter to a specific connection:
    run_config = {"ops": {"*": {"config": {"connection_id": "uuid-here"}}}}
"""

from datetime import date
from typing import Optional
from uuid import UUID

from dagster import (
    AssetExecutionContext,
    AssetKey,
    Config,
    Definitions,
    asset,
)
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from src.orchestration.resources import PostgresDatabase
from src.postgres.common.models import Connection
from src.postgres.gocardless.operations.balances import upsert_balances
from src.postgres.gocardless.operations.bank_accounts import (
    get_active_accounts,
    get_transaction_watermark,
    update_transaction_watermark,
    upsert_bank_account_details,
    upsert_bank_accounts,
)
from src.postgres.gocardless.operations.institutions import upsert_institutions
from src.postgres.gocardless.operations.requisitions import upsert_requisitions
from src.postgres.gocardless.operations.transactions import upsert_transactions
from src.providers.gocardless.api.account import (
    get_account_details_by_id,
    get_account_metadata_by_id,
    get_balance_data_by_id,
    get_transaction_data_by_id,
)
from src.providers.gocardless.api.core import GoCardlessCredentials, GoCardlessRateLimitError
from src.providers.gocardless.api.institutions import get_institutions
from src.providers.gocardless.api.requisition import (
    get_all_requisition_data,
    get_requisition_data_by_id,
)


class ConnectionScopeConfig(Config):
    """Config for scoping extraction to a specific connection."""

    connection_id: Optional[str] = None


def _get_requisition_id_for_connection(
    session: Session, connection_id: str, context: AssetExecutionContext
) -> Optional[str]:
    """Get the requisition ID for a connection.

    :param session: SQLAlchemy session.
    :param connection_id: Connection UUID as string.
    :param context: Asset execution context for logging.
    :returns: Requisition ID (provider_id) or None if connection not found.
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

    context.log.info(f"Scoped to connection {connection_id}, requisition {connection.provider_id}")
    return connection.provider_id


@asset(
    key=AssetKey(["source", "gocardless", "extract", "transactions"]),
    deps=[AssetKey(["source", "gocardless", "extract", "bank_accounts"])],
    group_name="gocardless",
    description="Extract transactions from GoCardless to Postgres.",
    required_resource_keys={"gocardless_api", "postgres_database"},
)
def gocardless_extract_transactions(
    context: AssetExecutionContext, config: ConnectionScopeConfig
) -> None:
    """Extract bank account transactions from GoCardless to Postgres."""
    creds: GoCardlessCredentials = context.resources.gocardless_api
    postgres_database: PostgresDatabase = context.resources.postgres_database

    today = date.today()

    with postgres_database.get_session() as session:
        # Determine requisition filter if scoped to a connection
        requisition_id = None
        if config.connection_id:
            requisition_id = _get_requisition_id_for_connection(
                session, config.connection_id, context
            )
            if requisition_id is None:
                return  # Error already logged

        for account in get_active_accounts(session, requisition_id):
            watermark = get_transaction_watermark(session, account.id)

            context.log.info(f"Watermark for account {account.id}: {watermark}")
            date_start = today + relativedelta(days=-90) if watermark is None else watermark

            # Go a few days further back to add some overlap in case any data was missed
            date_start += relativedelta(days=-3)

            context.log.info(
                f"Extracting transactions for account {account.id} from {date_start} to {today}"
            )

            try:
                raw_transactions = get_transaction_data_by_id(
                    creds, account.id, date_start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
                )
            except GoCardlessRateLimitError:
                context.log.warning(f"Rate limit exceeded for account {account.id}")
                continue

            # Upsert to Postgres
            count = upsert_transactions(session, account.id, raw_transactions)
            context.log.info(f"Upserted {count} transactions for account {account.id}")

            update_transaction_watermark(session, account.id, today)
            context.log.info(f"Updated watermark for account {account.id}")


@asset(
    key=AssetKey(["source", "gocardless", "extract", "account_details"]),
    deps=[AssetKey(["source", "gocardless", "extract", "bank_accounts"])],
    group_name="gocardless",
    description="Extract account details from GoCardless to Postgres.",
    required_resource_keys={"gocardless_api", "postgres_database"},
)
def gocardless_extract_account_details(
    context: AssetExecutionContext, config: ConnectionScopeConfig
) -> None:
    """Extract bank account details from GoCardless to Postgres."""
    creds: GoCardlessCredentials = context.resources.gocardless_api
    postgres_database: PostgresDatabase = context.resources.postgres_database

    with postgres_database.get_session() as session:
        # Determine requisition filter if scoped to a connection
        requisition_id = None
        if config.connection_id:
            requisition_id = _get_requisition_id_for_connection(
                session, config.connection_id, context
            )
            if requisition_id is None:
                return  # Error already logged

        accounts = get_active_accounts(session, requisition_id)
        for account in accounts:
            context.log.info(f"Extracting account details for {account.id}")

            account_data = get_account_details_by_id(creds, account.id)

            upsert_bank_account_details(session, account.id, account_data)
            context.log.info(f"Updated account details for {account.id}")


@asset(
    key=AssetKey(["source", "gocardless", "extract", "account_balances"]),
    deps=[AssetKey(["source", "gocardless", "extract", "bank_accounts"])],
    group_name="gocardless",
    description="Extract account balances from GoCardless to Postgres.",
    required_resource_keys={"gocardless_api", "postgres_database"},
)
def gocardless_extract_balances(
    context: AssetExecutionContext, config: ConnectionScopeConfig
) -> None:
    """Extract bank account balances from GoCardless to Postgres."""
    creds: GoCardlessCredentials = context.resources.gocardless_api
    postgres_database: PostgresDatabase = context.resources.postgres_database

    with postgres_database.get_session() as session:
        # Determine requisition filter if scoped to a connection
        requisition_id = None
        if config.connection_id:
            requisition_id = _get_requisition_id_for_connection(
                session, config.connection_id, context
            )
            if requisition_id is None:
                return  # Error already logged

        accounts = get_active_accounts(session, requisition_id)
        for account in accounts:
            context.log.info(f"Extracting balance for account {account.id}")

            balance_data = get_balance_data_by_id(creds, account.id)

            count = upsert_balances(session, account.id, balance_data)
            context.log.info(f"Upserted {count} balances for account {account.id}")


@asset(
    key=AssetKey(["source", "gocardless", "extract", "institutions"]),
    group_name="gocardless",
    description="Extract institutions from GoCardless to Postgres.",
    required_resource_keys={"gocardless_api", "postgres_database"},
)
def gocardless_extract_institutions(
    context: AssetExecutionContext, config: ConnectionScopeConfig
) -> None:
    """Extract institution metadata from GoCardless to Postgres.

    Note: This asset does not filter by connection_id as institutions are global.
    The config parameter is accepted for consistency with other extraction assets.
    """
    creds: GoCardlessCredentials = context.resources.gocardless_api
    postgres_database: PostgresDatabase = context.resources.postgres_database

    # Institutions are global, not connection-scoped
    if config.connection_id:
        context.log.info(
            "connection_id provided but institutions are global - extracting all institutions"
        )

    context.log.info("Fetching institutions from GoCardless API")
    institutions = get_institutions(creds)
    context.log.info(f"Fetched {len(institutions)} institutions from GoCardless")

    with postgres_database.get_session() as session:
        count = upsert_institutions(session, institutions)
        context.log.info(f"Upserted {count} institutions into gc_institutions")


@asset(
    key=AssetKey(["source", "gocardless", "extract", "requisitions"]),
    group_name="gocardless",
    description="Extract requisition status from GoCardless to Postgres.",
    required_resource_keys={"gocardless_api", "postgres_database"},
)
def gocardless_extract_requisitions(
    context: AssetExecutionContext, config: ConnectionScopeConfig
) -> None:
    """Extract requisition status from GoCardless to Postgres.

    Updates existing requisitions with latest status from GoCardless API.
    Does not create new requisitions (those are created via OAuth flow).

    Note: This asset fetches all requisitions from GoCardless API regardless of
    connection_id, as the GoCardless API doesn't support filtering. The config
    parameter is accepted for consistency with other extraction assets.
    """
    creds: GoCardlessCredentials = context.resources.gocardless_api
    postgres_database: PostgresDatabase = context.resources.postgres_database

    # Requisition status is fetched globally from GoCardless API
    if config.connection_id:
        context.log.info(
            "connection_id provided but requisitions are fetched globally from GoCardless"
        )

    context.log.info("Fetching requisitions from GoCardless API")
    requisitions = get_all_requisition_data(creds)
    context.log.info(f"Fetched {len(requisitions)} requisitions from GoCardless")

    with postgres_database.get_session() as session:
        count = upsert_requisitions(session, requisitions)
        context.log.info(f"Updated {count} requisitions in gc_requisition_links")


@asset(
    key=AssetKey(["source", "gocardless", "extract", "bank_accounts"]),
    group_name="gocardless",
    description="Extract bank account metadata from GoCardless requisitions to Postgres.",
    required_resource_keys={"gocardless_api", "postgres_database"},
)
def gocardless_extract_bank_accounts(
    context: AssetExecutionContext, config: ConnectionScopeConfig
) -> None:
    """Extract bank account metadata from GoCardless requisitions to Postgres.

    For each requisition, fetches the account IDs from the 'accounts' field,
    then calls the account metadata endpoint to get status, IBAN, currency, etc.
    This creates/updates BankAccount records in gc_bank_accounts.

    This asset should run BEFORE account_details, balances, and transactions
    extraction, as those assets require BankAccount records to already exist.
    """
    creds: GoCardlessCredentials = context.resources.gocardless_api
    postgres_database: PostgresDatabase = context.resources.postgres_database

    with postgres_database.get_session() as session:
        # Determine requisition filter if scoped to a connection
        requisition_id = None
        if config.connection_id:
            requisition_id = _get_requisition_id_for_connection(
                session, config.connection_id, context
            )
            if requisition_id is None:
                return  # Error already logged

        # Fetch requisitions from GoCardless API
        if requisition_id:
            # Fetch specific requisition by ID
            context.log.info(f"Fetching requisition {requisition_id} from GoCardless")
            try:
                requisition = get_requisition_data_by_id(creds, requisition_id)
                requisitions = [requisition]
            except Exception as e:
                context.log.error(f"Failed to fetch requisition {requisition_id}: {e}")
                return
        else:
            # Fetch all requisitions
            context.log.info("Fetching all requisitions from GoCardless")
            requisitions = get_all_requisition_data(creds)

        context.log.info(f"Processing {len(requisitions)} requisitions for bank accounts")

        total_accounts = 0
        for req in requisitions:
            req_id = req["id"]
            account_ids = req.get("accounts", [])

            if not account_ids:
                context.log.debug(f"Requisition {req_id} has no linked accounts")
                continue

            context.log.info(f"Requisition {req_id} has {len(account_ids)} accounts")

            # Fetch metadata for each account
            accounts_data = []
            for account_id in account_ids:
                try:
                    metadata = get_account_metadata_by_id(creds, account_id)
                    accounts_data.append(metadata)
                    context.log.debug(f"Fetched metadata for account {account_id}")
                except GoCardlessRateLimitError:
                    context.log.warning(f"Rate limit hit fetching account {account_id}")
                    continue
                except Exception as e:
                    context.log.warning(f"Failed to fetch account {account_id}: {e}")
                    continue

            if accounts_data:
                upsert_bank_accounts(session, req_id, accounts_data)
                total_accounts += len(accounts_data)
                context.log.info(f"Upserted {len(accounts_data)} accounts for requisition {req_id}")

        context.log.info(f"Extracted {total_accounts} bank accounts total")


extraction_asset_defs = Definitions(
    assets=[
        gocardless_extract_transactions,
        gocardless_extract_account_details,
        gocardless_extract_balances,
        gocardless_extract_institutions,
        gocardless_extract_requisitions,
        gocardless_extract_bank_accounts,
    ]
)
