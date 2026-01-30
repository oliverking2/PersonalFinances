"""Trading 212 Dagster Extraction Assets.

These assets extract data from the Trading 212 API and write to Postgres.
"""

from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

from dagster import (
    AssetExecutionContext,
    AssetKey,
    Config,
    Definitions,
    asset,
)

from src.orchestration.resources import PostgresDatabase
from src.postgres.trading212.models import T212ApiKey
from src.postgres.trading212.operations.api_keys import (
    get_all_api_keys_for_sync,
    get_api_key_by_id,
    update_api_key_status,
)
from src.postgres.trading212.operations.cash_balances import upsert_cash_balance
from src.postgres.trading212.operations.history import (
    upsert_dividend,
    upsert_order,
    upsert_transaction,
)
from src.providers.trading212.api.core import Trading212Client
from src.providers.trading212.exceptions import Trading212AuthError, Trading212Error
from src.utils.security import decrypt_api_key


class T212ExtractionConfig(Config):
    """Config for scoping extraction to a specific API key."""

    api_key_id: Optional[str] = None


def _extract_cash_for_api_key(
    api_key: T212ApiKey,
    context: AssetExecutionContext,
    postgres_database: PostgresDatabase,
) -> bool:
    """Extract cash balance for a single API key.

    :param api_key: The T212ApiKey record.
    :param context: Dagster execution context.
    :param postgres_database: Database resource.
    :returns: True if successful, False if failed.
    """
    context.log.info(f"Extracting cash for API key {api_key.id} ({api_key.friendly_name})")

    try:
        # Decrypt API key
        decrypted_key = decrypt_api_key(api_key.api_key_encrypted)
    except ValueError as e:
        context.log.error(f"Failed to decrypt API key {api_key.id}: {e}")
        with postgres_database.get_session() as session:
            update_api_key_status(
                session,
                api_key.id,
                status="error",
                error_message="Failed to decrypt API key",
            )
        return False

    try:
        # Create client and fetch data
        client = Trading212Client(decrypted_key)

        # Get account info to update metadata
        account_info = client.get_account_info()

        # Get cash balance
        cash = client.get_cash()

        # Save to database
        with postgres_database.get_session() as session:
            # Update API key with account info and successful status
            update_api_key_status(
                session,
                api_key.id,
                status="active",
                error_message=None,
                t212_account_id=account_info.account_id,
                currency_code=account_info.currency_code,
                last_synced_at=datetime.now(UTC),
            )

            # Insert cash balance snapshot
            upsert_cash_balance(
                session,
                api_key.id,
                free=cash.free,
                blocked=cash.blocked,
                invested=cash.invested,
                pie_cash=cash.pie_cash,
                ppl=cash.ppl,
                result=cash.result,
                total=cash.total,
            )

        context.log.info(
            f"Successfully extracted cash for API key {api_key.id}: "
            f"total={cash.total}, ppl={cash.ppl}"
        )
        return True

    except Trading212AuthError as e:
        context.log.error(f"Authentication failed for API key {api_key.id}: {e}")
        with postgres_database.get_session() as session:
            update_api_key_status(
                session,
                api_key.id,
                status="error",
                error_message="API key invalid or revoked",
            )
        return False

    except Trading212Error as e:
        context.log.error(f"API error for API key {api_key.id}: {e}")
        # Don't mark as error for transient failures
        return False


@asset(
    key=AssetKey(["source", "trading212", "extract", "cash"]),
    group_name="trading212",
    description="Extract cash balances from Trading 212 API to Postgres.",
    required_resource_keys={"postgres_database"},
)
def trading212_extract_cash(context: AssetExecutionContext, config: T212ExtractionConfig) -> None:
    """Extract cash balances from Trading 212 API to Postgres.

    For each active API key, fetches the current cash balance and stores
    a snapshot in t212_cash_balances.
    """
    postgres_database: PostgresDatabase = context.resources.postgres_database

    # Collect API key IDs to process (we store IDs, not objects, to avoid detached instance issues)
    api_key_ids: list[UUID] = []

    with postgres_database.get_session() as session:
        if config.api_key_id:
            # Extract for specific API key
            try:
                api_key_uuid = UUID(config.api_key_id)
            except ValueError:
                context.log.error(f"Invalid api_key_id format: {config.api_key_id}")
                return

            api_key = get_api_key_by_id(session, api_key_uuid)
            if api_key is None:
                context.log.error(f"API key not found: {config.api_key_id}")
                return

            api_key_ids = [api_key.id]
            context.log.info(f"Scoped extraction to API key {config.api_key_id}")
        else:
            # Extract for all active API keys
            api_keys = get_all_api_keys_for_sync(session)
            api_key_ids = [k.id for k in api_keys]
            context.log.info(f"Found {len(api_key_ids)} active API keys")

    if not api_key_ids:
        context.log.info("No Trading 212 API keys to extract")
        return

    success_count = 0
    for api_key_id in api_key_ids:
        # Fetch fresh api_key object for each extraction
        with postgres_database.get_session() as session:
            api_key = get_api_key_by_id(session, api_key_id)
            if api_key is None:
                context.log.warning(f"API key {api_key_id} no longer exists, skipping")
                continue
            if _extract_cash_for_api_key(api_key, context, postgres_database):
                success_count += 1

    context.log.info(f"Extraction complete: {success_count}/{len(api_key_ids)} API keys successful")


def _extract_orders_for_api_key(
    api_key: T212ApiKey,
    context: AssetExecutionContext,
    postgres_database: PostgresDatabase,
) -> bool:
    """Extract orders for a single API key.

    :param api_key: The T212ApiKey record.
    :param context: Dagster execution context.
    :param postgres_database: Database resource.
    :returns: True if successful, False if failed.
    """
    context.log.info(f"Extracting orders for API key {api_key.id} ({api_key.friendly_name})")

    try:
        decrypted_key = decrypt_api_key(api_key.api_key_encrypted)
    except ValueError as e:
        context.log.error(f"Failed to decrypt API key {api_key.id}: {e}")
        return False

    try:
        client = Trading212Client(decrypted_key)
        orders = client.get_orders()

        with postgres_database.get_session() as session:
            for order in orders:
                upsert_order(
                    session,
                    api_key.id,
                    t212_order_id=order.order_id,
                    parent_order_id=order.parent_order_id,
                    ticker=order.ticker,
                    instrument_name=order.instrument_name,
                    order_type=order.order_type,
                    status=order.status,
                    quantity=order.quantity,
                    filled_quantity=order.filled_quantity,
                    filled_value=order.filled_value,
                    limit_price=order.limit_price,
                    stop_price=order.stop_price,
                    fill_price=order.fill_price,
                    currency=order.currency,
                    date_created=order.date_created,
                    date_executed=order.date_executed,
                    date_modified=order.date_modified,
                )

        context.log.info(f"Extracted {len(orders)} orders for API key {api_key.id}")
        return True

    except Trading212AuthError as e:
        context.log.error(f"Authentication failed for API key {api_key.id}: {e}")
        return False

    except Trading212Error as e:
        context.log.error(f"API error for API key {api_key.id}: {e}")
        return False


def _extract_dividends_for_api_key(
    api_key: T212ApiKey,
    context: AssetExecutionContext,
    postgres_database: PostgresDatabase,
) -> bool:
    """Extract dividends for a single API key.

    :param api_key: The T212ApiKey record.
    :param context: Dagster execution context.
    :param postgres_database: Database resource.
    :returns: True if successful, False if failed.
    """
    context.log.info(f"Extracting dividends for API key {api_key.id} ({api_key.friendly_name})")

    try:
        decrypted_key = decrypt_api_key(api_key.api_key_encrypted)
    except ValueError as e:
        context.log.error(f"Failed to decrypt API key {api_key.id}: {e}")
        return False

    try:
        client = Trading212Client(decrypted_key)
        dividends = client.get_dividends()

        with postgres_database.get_session() as session:
            for div in dividends:
                upsert_dividend(
                    session,
                    api_key.id,
                    t212_reference=div.reference,
                    ticker=div.ticker,
                    instrument_name=div.instrument_name,
                    amount=div.amount,
                    amount_in_euro=div.amount_in_euro,
                    gross_amount_per_share=div.gross_amount_per_share,
                    quantity=div.quantity,
                    currency=div.currency,
                    dividend_type=div.dividend_type,
                    paid_on=div.paid_on,
                )

        context.log.info(f"Extracted {len(dividends)} dividends for API key {api_key.id}")
        return True

    except Trading212AuthError as e:
        context.log.error(f"Authentication failed for API key {api_key.id}: {e}")
        return False

    except Trading212Error as e:
        context.log.error(f"API error for API key {api_key.id}: {e}")
        return False


def _extract_transactions_for_api_key(
    api_key: T212ApiKey,
    context: AssetExecutionContext,
    postgres_database: PostgresDatabase,
) -> bool:
    """Extract transactions for a single API key.

    :param api_key: The T212ApiKey record.
    :param context: Dagster execution context.
    :param postgres_database: Database resource.
    :returns: True if successful, False if failed.
    """
    context.log.info(f"Extracting transactions for API key {api_key.id} ({api_key.friendly_name})")

    try:
        decrypted_key = decrypt_api_key(api_key.api_key_encrypted)
    except ValueError as e:
        context.log.error(f"Failed to decrypt API key {api_key.id}: {e}")
        return False

    try:
        client = Trading212Client(decrypted_key)
        transactions = client.get_transactions()

        with postgres_database.get_session() as session:
            for txn in transactions:
                upsert_transaction(
                    session,
                    api_key.id,
                    t212_reference=txn.reference,
                    transaction_type=txn.transaction_type,
                    amount=txn.amount,
                    currency=txn.currency,
                    date_time=txn.date_time,
                )

        context.log.info(f"Extracted {len(transactions)} transactions for API key {api_key.id}")
        return True

    except Trading212AuthError as e:
        context.log.error(f"Authentication failed for API key {api_key.id}: {e}")
        return False

    except Trading212Error as e:
        context.log.error(f"API error for API key {api_key.id}: {e}")
        return False


@asset(
    key=AssetKey(["source", "trading212", "extract", "orders"]),
    group_name="trading212",
    description="Extract order history from Trading 212 API to Postgres.",
    required_resource_keys={"postgres_database"},
)
def trading212_extract_orders(context: AssetExecutionContext, config: T212ExtractionConfig) -> None:
    """Extract order history from Trading 212 API to Postgres."""
    postgres_database: PostgresDatabase = context.resources.postgres_database
    api_key_ids: list[UUID] = []

    with postgres_database.get_session() as session:
        if config.api_key_id:
            try:
                api_key_uuid = UUID(config.api_key_id)
            except ValueError:
                context.log.error(f"Invalid api_key_id format: {config.api_key_id}")
                return
            api_key = get_api_key_by_id(session, api_key_uuid)
            if api_key is None:
                context.log.error(f"API key not found: {config.api_key_id}")
                return
            api_key_ids = [api_key.id]
        else:
            api_keys = get_all_api_keys_for_sync(session)
            api_key_ids = [k.id for k in api_keys]

    if not api_key_ids:
        context.log.info("No Trading 212 API keys to extract orders from")
        return

    success_count = 0
    for api_key_id in api_key_ids:
        with postgres_database.get_session() as session:
            api_key = get_api_key_by_id(session, api_key_id)
            if api_key is None:
                continue
            if _extract_orders_for_api_key(api_key, context, postgres_database):
                success_count += 1

    context.log.info(f"Order extraction complete: {success_count}/{len(api_key_ids)} successful")


@asset(
    key=AssetKey(["source", "trading212", "extract", "dividends"]),
    group_name="trading212",
    description="Extract dividend history from Trading 212 API to Postgres.",
    required_resource_keys={"postgres_database"},
)
def trading212_extract_dividends(
    context: AssetExecutionContext, config: T212ExtractionConfig
) -> None:
    """Extract dividend history from Trading 212 API to Postgres."""
    postgres_database: PostgresDatabase = context.resources.postgres_database
    api_key_ids: list[UUID] = []

    with postgres_database.get_session() as session:
        if config.api_key_id:
            try:
                api_key_uuid = UUID(config.api_key_id)
            except ValueError:
                context.log.error(f"Invalid api_key_id format: {config.api_key_id}")
                return
            api_key = get_api_key_by_id(session, api_key_uuid)
            if api_key is None:
                context.log.error(f"API key not found: {config.api_key_id}")
                return
            api_key_ids = [api_key.id]
        else:
            api_keys = get_all_api_keys_for_sync(session)
            api_key_ids = [k.id for k in api_keys]

    if not api_key_ids:
        context.log.info("No Trading 212 API keys to extract dividends from")
        return

    success_count = 0
    for api_key_id in api_key_ids:
        with postgres_database.get_session() as session:
            api_key = get_api_key_by_id(session, api_key_id)
            if api_key is None:
                continue
            if _extract_dividends_for_api_key(api_key, context, postgres_database):
                success_count += 1

    context.log.info(f"Dividend extraction complete: {success_count}/{len(api_key_ids)} successful")


@asset(
    key=AssetKey(["source", "trading212", "extract", "transactions"]),
    group_name="trading212",
    description="Extract transaction history from Trading 212 API to Postgres.",
    required_resource_keys={"postgres_database"},
)
def trading212_extract_transactions(
    context: AssetExecutionContext, config: T212ExtractionConfig
) -> None:
    """Extract transaction history from Trading 212 API to Postgres."""
    postgres_database: PostgresDatabase = context.resources.postgres_database
    api_key_ids: list[UUID] = []

    with postgres_database.get_session() as session:
        if config.api_key_id:
            try:
                api_key_uuid = UUID(config.api_key_id)
            except ValueError:
                context.log.error(f"Invalid api_key_id format: {config.api_key_id}")
                return
            api_key = get_api_key_by_id(session, api_key_uuid)
            if api_key is None:
                context.log.error(f"API key not found: {config.api_key_id}")
                return
            api_key_ids = [api_key.id]
        else:
            api_keys = get_all_api_keys_for_sync(session)
            api_key_ids = [k.id for k in api_keys]

    if not api_key_ids:
        context.log.info("No Trading 212 API keys to extract transactions from")
        return

    success_count = 0
    for api_key_id in api_key_ids:
        with postgres_database.get_session() as session:
            api_key = get_api_key_by_id(session, api_key_id)
            if api_key is None:
                continue
            if _extract_transactions_for_api_key(api_key, context, postgres_database):
                success_count += 1

    context.log.info(
        f"Transaction extraction complete: {success_count}/{len(api_key_ids)} successful"
    )


extraction_asset_defs = Definitions(
    assets=[
        trading212_extract_cash,
        trading212_extract_orders,
        trading212_extract_dividends,
        trading212_extract_transactions,
    ]
)
