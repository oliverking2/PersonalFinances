"""Trading 212 sync operations for keeping unified tables in sync with provider tables.

This module provides operations to sync data from raw Trading 212 tables
(e.g., t212_api_keys, t212_cash_balances) to the unified tables
(connections, accounts, transactions).
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from dagster import get_dagster_logger
from sqlalchemy.orm import Session

from src.postgres.common.enums import (
    AccountStatus,
    AccountType,
    ConnectionStatus,
    Provider,
)
from src.postgres.common.models import Account, Connection, Institution, Transaction
from src.postgres.common.operations.balance_snapshots import create_balance_snapshot
from src.postgres.trading212.models import (
    T212ApiKey,
    T212CashBalance,
    T212Dividend,
    T212Order,
    T212Transaction,
)

logger = get_dagster_logger()


def ensure_trading212_institution(session: Session) -> Institution:
    """Ensure the Trading 212 institution exists.

    Creates the institution if it doesn't exist.

    :param session: SQLAlchemy session.
    :returns: The Trading 212 Institution.
    """
    institution_id = "TRADING212"
    existing = session.get(Institution, institution_id)

    if existing:
        return existing

    institution = Institution(
        id=institution_id,
        provider=Provider.TRADING212.value,
        name="Trading 212",
        logo_url="https://www.trading212.com/favicon.ico",
        countries=["GB"],
    )
    session.add(institution)
    session.flush()
    logger.info(f"Created Trading 212 institution: id={institution_id}")
    return institution


def sync_trading212_connection(
    session: Session,
    api_key: T212ApiKey,
) -> Connection:
    """Sync or create a Connection from a Trading 212 API key.

    :param session: SQLAlchemy session.
    :param api_key: The T212ApiKey record.
    :returns: The synced Connection.
    """
    # Ensure institution exists
    ensure_trading212_institution(session)

    # Map API key status to connection status
    status = ConnectionStatus.ACTIVE if api_key.status == "active" else ConnectionStatus.ERROR

    # Look for existing connection
    existing = (
        session.query(Connection)
        .filter(
            Connection.provider == Provider.TRADING212.value,
            Connection.provider_id == str(api_key.id),
        )
        .first()
    )

    now = datetime.now(UTC)

    if existing:
        old_status = existing.status
        existing.status = status.value
        existing.friendly_name = api_key.friendly_name
        existing.synced_at = now
        session.flush()
        logger.info(
            f"Updated T212 connection: id={existing.id}, status={old_status} -> {status.value}"
        )
        return existing

    # Create new connection
    connection = Connection(
        user_id=api_key.user_id,
        provider=Provider.TRADING212.value,
        provider_id=str(api_key.id),
        institution_id="TRADING212",
        friendly_name=api_key.friendly_name,
        status=status.value,
        created_at=api_key.created_at,
        synced_at=now,
    )
    session.add(connection)
    session.flush()
    logger.info(f"Created T212 connection: id={connection.id}, api_key_id={api_key.id}")
    return connection


def sync_trading212_account(
    session: Session,
    api_key: T212ApiKey,
    connection: Connection,
) -> Account:
    """Sync or create an Account from Trading 212 API key data.

    :param session: SQLAlchemy session.
    :param api_key: The T212ApiKey record with account info.
    :param connection: The parent Connection.
    :returns: The synced Account.
    """
    # Use T212 account ID as provider_id, or fall back to api_key id
    provider_id = api_key.t212_account_id or str(api_key.id)

    # Map API key status to account status
    status = AccountStatus.ACTIVE if api_key.status == "active" else AccountStatus.INACTIVE

    # Look for existing account
    existing = (
        session.query(Account)
        .filter(
            Account.connection_id == connection.id,
            Account.provider_id == provider_id,
        )
        .first()
    )

    # Get latest cash balance
    latest_balance = (
        session.query(T212CashBalance)
        .filter(T212CashBalance.api_key_id == api_key.id)
        .order_by(T212CashBalance.fetched_at.desc())
        .first()
    )

    now = datetime.now(UTC)

    if existing:
        existing.status = status.value
        existing.currency = api_key.currency_code
        existing.synced_at = now
        existing.last_synced_at = api_key.last_synced_at

        if latest_balance:
            existing.total_value = latest_balance.total
            existing.unrealised_pnl = latest_balance.ppl
            existing.balance_amount = latest_balance.free  # Free cash
            existing.balance_currency = api_key.currency_code
            existing.balance_type = "cash"
            existing.balance_updated_at = latest_balance.fetched_at

            # Create balance snapshot for historical tracking
            if api_key.currency_code:
                create_balance_snapshot(
                    session=session,
                    account_id=existing.id,
                    balance_amount=latest_balance.free,
                    balance_currency=api_key.currency_code,
                    balance_type="cash",
                    total_value=latest_balance.total,
                    unrealised_pnl=latest_balance.ppl,
                    source_updated_at=latest_balance.fetched_at,
                )

        session.flush()
        logger.info(
            f"Updated T212 account: id={existing.id}, "
            f"total_value={latest_balance.total if latest_balance else 'N/A'}"
        )
        return existing

    # Create new account
    account = Account(
        connection_id=connection.id,
        provider_id=provider_id,
        account_type=AccountType.TRADING.value,
        display_name=api_key.friendly_name,
        currency=api_key.currency_code,
        status=status.value,
        synced_at=now,
        last_synced_at=api_key.last_synced_at,
    )

    if latest_balance:
        account.total_value = latest_balance.total
        account.unrealised_pnl = latest_balance.ppl
        account.balance_amount = latest_balance.free
        account.balance_currency = api_key.currency_code
        account.balance_type = "cash"
        account.balance_updated_at = latest_balance.fetched_at

    session.add(account)
    session.flush()

    # Create initial balance snapshot for historical tracking
    if latest_balance and api_key.currency_code:
        create_balance_snapshot(
            session=session,
            account_id=account.id,
            balance_amount=latest_balance.free,
            balance_currency=api_key.currency_code,
            balance_type="cash",
            total_value=latest_balance.total,
            unrealised_pnl=latest_balance.ppl,
            source_updated_at=latest_balance.fetched_at,
        )

    logger.info(
        f"Created T212 account: id={account.id}, "
        f"connection_id={connection.id}, provider_id={provider_id}"
    )
    return account


def sync_all_trading212_connections(session: Session) -> list[Connection]:
    """Sync all Trading 212 connections from active API keys.

    :param session: SQLAlchemy session.
    :returns: List of synced Connection objects.
    """
    api_keys = session.query(T212ApiKey).all()
    logger.info(f"Found {len(api_keys)} Trading 212 API keys")

    if not api_keys:
        return []

    synced = []
    for api_key in api_keys:
        connection = sync_trading212_connection(session, api_key)
        synced.append(connection)

    logger.info(f"Synced {len(synced)} Trading 212 connections")
    return synced


def sync_all_trading212_accounts(
    session: Session,
    connection: Connection,
) -> list[Account]:
    """Sync Trading 212 account for a connection.

    :param session: SQLAlchemy session.
    :param connection: The Connection to sync accounts for.
    :returns: List of synced Account objects (single account per connection).
    """
    # Get the API key for this connection
    api_key_id = UUID(connection.provider_id)
    api_key = session.get(T212ApiKey, api_key_id)

    if not api_key:
        logger.warning(f"API key not found for connection {connection.id}")
        return []

    account = sync_trading212_account(session, api_key, connection)
    return [account]


# =============================================================================
# Trading 212 Transaction Sync
# =============================================================================


def sync_trading212_order_transaction(
    session: Session,
    t212_order: T212Order,
    account: Account,
) -> Transaction | None:
    """Sync a T212 order to the unified Transaction table.

    Only syncs filled orders (actual executed trades).

    :param session: SQLAlchemy session.
    :param t212_order: The T212Order record.
    :param account: The unified Account.
    :returns: The synced Transaction, or None if not applicable.
    """
    # Only sync filled orders
    if t212_order.status != "FILLED":
        return None

    # Use order ID as provider_id, prefixed with "order_" to distinguish
    provider_id = f"order_{t212_order.t212_order_id}"

    # Check for existing
    existing = (
        session.query(Transaction)
        .filter(
            Transaction.account_id == account.id,
            Transaction.provider_id == provider_id,
        )
        .first()
    )

    # Determine amount: filled_value is the total cost/proceeds
    # Negative for buys, positive for sells (based on filled_value sign or order type)
    amount = t212_order.filled_value or Decimal("0")

    # Build description
    action = "Buy" if amount < 0 else "Sell"
    description = f"{action} {t212_order.filled_quantity} {t212_order.ticker}"
    if t212_order.instrument_name:
        description += f" ({t212_order.instrument_name})"

    if existing:
        existing.booking_date = t212_order.date_executed or t212_order.date_created
        existing.value_date = t212_order.date_executed or t212_order.date_created
        existing.amount = amount
        existing.currency = t212_order.currency
        existing.counterparty_name = t212_order.ticker
        existing.description = description
        existing.synced_at = datetime.now(UTC)
        session.flush()
        return existing

    transaction = Transaction(
        account_id=account.id,
        provider_id=provider_id,
        booking_date=t212_order.date_executed or t212_order.date_created,
        value_date=t212_order.date_executed or t212_order.date_created,
        amount=amount,
        currency=t212_order.currency,
        counterparty_name=t212_order.ticker,
        description=description,
        synced_at=datetime.now(UTC),
    )
    session.add(transaction)
    session.flush()
    return transaction


def sync_trading212_dividend_transaction(
    session: Session,
    t212_dividend: T212Dividend,
    account: Account,
) -> Transaction:
    """Sync a T212 dividend to the unified Transaction table.

    :param session: SQLAlchemy session.
    :param t212_dividend: The T212Dividend record.
    :param account: The unified Account.
    :returns: The synced Transaction.
    """
    # Use dividend reference as provider_id, prefixed
    provider_id = f"dividend_{t212_dividend.t212_reference}"

    existing = (
        session.query(Transaction)
        .filter(
            Transaction.account_id == account.id,
            Transaction.provider_id == provider_id,
        )
        .first()
    )

    # Build description
    description = f"Dividend from {t212_dividend.ticker}"
    if t212_dividend.instrument_name:
        description += f" ({t212_dividend.instrument_name})"
    if t212_dividend.dividend_type:
        description += f" - {t212_dividend.dividend_type}"

    if existing:
        existing.booking_date = t212_dividend.paid_on
        existing.value_date = t212_dividend.paid_on
        existing.amount = t212_dividend.amount
        existing.currency = t212_dividend.currency
        existing.counterparty_name = t212_dividend.ticker
        existing.description = description
        existing.synced_at = datetime.now(UTC)
        session.flush()
        return existing

    transaction = Transaction(
        account_id=account.id,
        provider_id=provider_id,
        booking_date=t212_dividend.paid_on,
        value_date=t212_dividend.paid_on,
        amount=t212_dividend.amount,
        currency=t212_dividend.currency,
        counterparty_name=t212_dividend.ticker,
        description=description,
        synced_at=datetime.now(UTC),
    )
    session.add(transaction)
    session.flush()
    return transaction


def sync_trading212_cash_transaction(
    session: Session,
    t212_txn: T212Transaction,
    account: Account,
) -> Transaction:
    """Sync a T212 cash transaction to the unified Transaction table.

    :param session: SQLAlchemy session.
    :param t212_txn: The T212Transaction record.
    :param account: The unified Account.
    :returns: The synced Transaction.
    """
    # Use transaction reference as provider_id, prefixed
    provider_id = f"txn_{t212_txn.t212_reference}"

    existing = (
        session.query(Transaction)
        .filter(
            Transaction.account_id == account.id,
            Transaction.provider_id == provider_id,
        )
        .first()
    )

    # Build description based on transaction type
    type_descriptions = {
        "DEPOSIT": "Deposit",
        "WITHDRAWAL": "Withdrawal",
        "INTEREST": "Interest payment",
        "FEE": "Fee",
        "DIVIDEND": "Dividend",
    }
    description = type_descriptions.get(
        t212_txn.transaction_type, t212_txn.transaction_type.replace("_", " ").title()
    )

    if existing:
        existing.booking_date = t212_txn.date_time
        existing.value_date = t212_txn.date_time
        existing.amount = t212_txn.amount
        existing.currency = t212_txn.currency
        existing.description = description
        existing.synced_at = datetime.now(UTC)
        session.flush()
        return existing

    transaction = Transaction(
        account_id=account.id,
        provider_id=provider_id,
        booking_date=t212_txn.date_time,
        value_date=t212_txn.date_time,
        amount=t212_txn.amount,
        currency=t212_txn.currency,
        description=description,
        synced_at=datetime.now(UTC),
    )
    session.add(transaction)
    session.flush()
    return transaction


def sync_all_trading212_transactions(
    session: Session,
    account: Account,
    api_key_id: str,
) -> list[Transaction]:
    """Sync all Trading 212 transactions for an account.

    This syncs orders, dividends, and cash transactions to the unified
    Transaction table.

    :param session: SQLAlchemy session.
    :param account: The unified Account to sync transactions for.
    :param api_key_id: The T212 API key UUID string.
    :returns: List of synced Transaction objects.
    """
    api_key_uuid = UUID(api_key_id)
    synced: list[Transaction] = []

    # Sync orders (only filled)
    orders = session.query(T212Order).filter(T212Order.api_key_id == api_key_uuid).all()
    for order in orders:
        txn = sync_trading212_order_transaction(session, order, account)
        if txn:
            synced.append(txn)

    # Sync dividends
    dividends = session.query(T212Dividend).filter(T212Dividend.api_key_id == api_key_uuid).all()
    for div in dividends:
        txn = sync_trading212_dividend_transaction(session, div, account)
        synced.append(txn)

    # Sync cash transactions
    transactions = (
        session.query(T212Transaction).filter(T212Transaction.api_key_id == api_key_uuid).all()
    )
    for t212_txn in transactions:
        txn = sync_trading212_cash_transaction(session, t212_txn, account)
        synced.append(txn)

    logger.info(
        f"Synced {len(synced)} Trading 212 transactions for account {account.id}: "
        f"{len(orders)} orders, {len(dividends)} dividends, {len(transactions)} cash transactions"
    )
    return synced
