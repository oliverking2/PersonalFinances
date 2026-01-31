"""Sync operations for keeping unified tables in sync with provider tables.

This module provides operations to sync data from raw provider tables
(e.g., gc_requisition_links, gc_bank_accounts) to the unified tables
(connections, accounts).
"""

from datetime import UTC, datetime
from decimal import Decimal

from dagster import get_dagster_logger
from sqlalchemy.orm import Session

from src.postgres.common.enums import (
    AccountStatus,
    AccountType,
    ConnectionStatus,
    Provider,
    map_gc_account_status,
    map_gc_requisition_status,
)
from src.postgres.common.models import Account, Connection, Institution, Transaction
from src.postgres.common.operations.balance_snapshots import create_balance_snapshot
from src.postgres.gocardless.models import (
    Balance,
    BankAccount,
    GoCardlessInstitution,
    GoCardlessTransaction,
    RequisitionLink,
)
from src.postgres.trading212.models import (
    T212ApiKey,
    T212CashBalance,
    T212Dividend,
    T212Order,
    T212Transaction,
)

logger = get_dagster_logger()


def sync_gocardless_connection(
    session: Session,
    connection: Connection,
) -> Connection:
    """Sync a Connection from its corresponding GoCardless requisition.

    Updates the Connection status and friendly name from the raw requisition.

    :param session: SQLAlchemy session.
    :param connection: Existing Connection to update.
    :returns: The updated Connection.
    """
    # Look up the corresponding requisition
    logger.debug(
        f"Looking up requisition for connection: id={connection.id}, "
        f"provider_id={connection.provider_id}"
    )
    requisition = session.get(RequisitionLink, connection.provider_id)
    if not requisition:
        logger.warning(
            f"Requisition not found in gc_requisition_links table for connection: "
            f"id={connection.id}, provider_id={connection.provider_id}. "
            f"This connection will not be synced."
        )
        return connection

    old_status = connection.status
    status = map_gc_requisition_status(requisition.status)

    # Update connection from requisition
    connection.status = status.value
    connection.friendly_name = requisition.friendly_name
    connection.synced_at = datetime.now(UTC)
    session.flush()

    logger.info(
        f"Updated connection: id={connection.id}, "
        f"provider_id={connection.provider_id}, "
        f"status={old_status} -> {status.value}, "
        f"requisition_status={requisition.status}"
    )
    return connection


def _get_latest_balance(
    session: Session,
    account_id: str,
) -> Balance | None:
    """Get the most recent balance for a GoCardless bank account.

    Prefers interimAvailable, then closingAvailable, then any available type.

    :param session: SQLAlchemy session.
    :param account_id: GoCardless bank account ID.
    :returns: Latest Balance or None if no balances exist.
    """
    # Priority order for balance types
    balance_type_priority = [
        "interimAvailable",
        "closingAvailable",
        "interimBooked",
        "closingBooked",
        "expected",
    ]

    for balance_type in balance_type_priority:
        balance = (
            session.query(Balance)
            .filter(
                Balance.account_id == account_id,
                Balance.balance_type == balance_type,
            )
            .first()
        )
        if balance:
            return balance

    # Fall back to any balance
    return session.query(Balance).filter(Balance.account_id == account_id).first()


def sync_gocardless_account(
    session: Session,
    bank_account: BankAccount,
    connection: Connection,
) -> Account:
    """Sync a GoCardless bank account to the unified Account table.

    Creates or updates an Account based on the bank account data.
    Also syncs the latest balance if available.

    :param session: SQLAlchemy session.
    :param bank_account: GoCardless BankAccount to sync.
    :param connection: Parent Connection for this account.
    :returns: The created or updated Account.
    """
    status = map_gc_account_status(bank_account.status)

    # Check if account already exists
    existing = (
        session.query(Account)
        .filter(
            Account.connection_id == connection.id,
            Account.provider_id == bank_account.id,
        )
        .first()
    )

    # Get latest balance
    balance = _get_latest_balance(session, bank_account.id)
    now = datetime.now(UTC)

    if existing:
        # Update existing account
        existing.status = status.value
        existing.name = bank_account.name
        existing.iban = bank_account.iban
        existing.currency = bank_account.currency
        existing.synced_at = now
        existing.last_synced_at = now  # Track when data was last synced

        if balance:
            existing.balance_amount = Decimal(str(balance.balance_amount))
            existing.balance_currency = balance.balance_currency
            existing.balance_type = balance.balance_type
            existing.balance_updated_at = balance.last_change_date or now

            # Create balance snapshot for historical tracking
            create_balance_snapshot(
                session=session,
                account_id=existing.id,
                balance_amount=Decimal(str(balance.balance_amount)),
                balance_currency=balance.balance_currency,
                balance_type=balance.balance_type,
                source_updated_at=balance.last_change_date,
            )

        session.flush()
        logger.info(
            f"Updated account: id={existing.id}, "
            f"provider_id={bank_account.id}, status={status.value}"
        )
        return existing

    # Create new account
    account = Account(
        connection_id=connection.id,
        provider_id=bank_account.id,
        account_type=AccountType.BANK.value,
        display_name=bank_account.display_name,
        name=bank_account.name,
        iban=bank_account.iban,
        currency=bank_account.currency,
        status=status.value,
        synced_at=now,
        last_synced_at=now,  # Track when data was last synced
    )

    if balance:
        account.balance_amount = Decimal(str(balance.balance_amount))
        account.balance_currency = balance.balance_currency
        account.balance_type = balance.balance_type
        account.balance_updated_at = balance.last_change_date or now

    session.add(account)
    session.flush()

    # Create initial balance snapshot for historical tracking
    if balance:
        create_balance_snapshot(
            session=session,
            account_id=account.id,
            balance_amount=Decimal(str(balance.balance_amount)),
            balance_currency=balance.balance_currency,
            balance_type=balance.balance_type,
            source_updated_at=balance.last_change_date,
        )

    logger.info(
        f"Created account: id={account.id}, "
        f"connection_id={connection.id}, provider_id={bank_account.id}"
    )
    return account


def sync_all_gocardless_connections(session: Session) -> list[Connection]:
    """Sync all GoCardless connections from their raw requisitions.

    Updates status and friendly name for all existing GoCardless connections.

    :param session: SQLAlchemy session.
    :returns: List of synced Connection objects.
    """
    connections = (
        session.query(Connection).filter(Connection.provider == Provider.GOCARDLESS.value).all()
    )

    logger.info(f"Found {len(connections)} GoCardless connections in database")

    if not connections:
        # Check raw requisition table to help diagnose
        requisition_count = session.query(RequisitionLink).count()
        logger.warning(
            f"No connections with provider='gocardless' found. "
            f"gc_requisition_links table has {requisition_count} records. "
            f"Connections are created when users link accounts via the API."
        )
        return []

    synced = []
    for conn in connections:
        synced_conn = sync_gocardless_connection(session, conn)
        synced.append(synced_conn)

    logger.info(f"Synced {len(synced)} GoCardless connections")
    return synced


def sync_all_gocardless_accounts(
    session: Session,
    connection: Connection,
) -> list[Account]:
    """Sync all GoCardless bank accounts for a connection.

    :param session: SQLAlchemy session.
    :param connection: Parent Connection to sync accounts for.
    :returns: List of synced Account objects.
    """
    logger.info(
        f"Syncing accounts for connection: id={connection.id}, "
        f"provider_id={connection.provider_id}, name={connection.friendly_name}"
    )

    bank_accounts = (
        session.query(BankAccount)
        .filter(BankAccount.requisition_id == connection.provider_id)
        .all()
    )

    logger.info(
        f"Found {len(bank_accounts)} bank accounts in gc_bank_accounts "
        f"for requisition_id={connection.provider_id}"
    )

    if not bank_accounts:
        logger.warning(
            f"No bank accounts found for connection {connection.id}. "
            f"Check that gc_bank_accounts has records with requisition_id={connection.provider_id}. "
            f"Run the extraction assets first to populate gc_bank_accounts."
        )
        return []

    accounts = []
    for bank_account in bank_accounts:
        account = sync_gocardless_account(session, bank_account, connection)
        accounts.append(account)

    logger.info(f"Synced {len(accounts)} accounts for connection: id={connection.id}")
    return accounts


def mark_missing_accounts_inactive(
    session: Session,
    connection: Connection,
    synced_provider_ids: set[str],
) -> int:
    """Mark accounts as inactive if they're no longer in the provider data.

    :param session: SQLAlchemy session.
    :param connection: Parent Connection.
    :param synced_provider_ids: Set of provider IDs that were just synced.
    :returns: Number of accounts marked inactive.
    """
    count = 0
    existing_accounts = (
        session.query(Account)
        .filter(
            Account.connection_id == connection.id,
            Account.status == AccountStatus.ACTIVE.value,
        )
        .all()
    )

    for account in existing_accounts:
        if account.provider_id not in synced_provider_ids:
            account.status = AccountStatus.INACTIVE.value
            count += 1
            logger.info(
                f"Marked account inactive: id={account.id}, provider_id={account.provider_id}"
            )

    session.flush()
    return count


def sync_gocardless_institution(
    session: Session,
    gc_institution: GoCardlessInstitution,
) -> Institution:
    """Sync a unified Institution from a GoCardless institution row.

    :param session: SQLAlchemy session.
    :param gc_institution: GoCardless institution record from gc_institutions.
    :returns: The created or updated Institution.
    """
    existing = session.get(Institution, gc_institution.id)

    if existing:
        existing.provider = Provider.GOCARDLESS.value
        existing.name = gc_institution.name
        existing.logo_url = gc_institution.logo
        existing.countries = gc_institution.countries
        session.flush()
        logger.info(f"Updated institution: id={existing.id}, provider=gocardless")
        return existing

    institution = Institution(
        id=gc_institution.id,
        provider=Provider.GOCARDLESS.value,
        name=gc_institution.name,
        logo_url=gc_institution.logo,
        countries=gc_institution.countries,
    )
    session.add(institution)
    session.flush()
    logger.info(f"Created institution: id={institution.id}, provider=gocardless")
    return institution


def sync_all_gocardless_institutions(session: Session) -> list[Institution]:
    """Sync all GoCardless institutions from gc_institutions into unified institutions.

    :param session: SQLAlchemy session.
    :returns: List of synced Institution objects.
    """
    gc_institutions = session.query(GoCardlessInstitution).all()
    logger.info(f"Found {len(gc_institutions)} GoCardless institutions in gc_institutions")

    if not gc_institutions:
        logger.warning(
            "No GoCardless institutions found in gc_institutions. "
            "Run the extraction step first to populate gc_institutions."
        )
        return []

    synced: list[Institution] = []
    for gc_inst in gc_institutions:
        inst = sync_gocardless_institution(session, gc_inst)
        synced.append(inst)

    logger.info(f"Synced {len(synced)} GoCardless institutions")
    return synced


def sync_gocardless_transaction(
    session: Session,
    gc_transaction: GoCardlessTransaction,
    account: Account,
) -> Transaction:
    """Sync a unified Transaction from a GoCardless transaction row.

    :param session: SQLAlchemy session.
    :param gc_transaction: GoCardless transaction record from gc_transactions.
    :param account: The unified Account this transaction belongs to.
    :returns: The created or updated Transaction.
    """
    # Find existing transaction by account_id and provider_id
    existing = (
        session.query(Transaction)
        .filter(
            Transaction.account_id == account.id,
            Transaction.provider_id == gc_transaction.transaction_id,
        )
        .first()
    )

    # Determine counterparty (creditor for outgoing, debtor for incoming)
    if gc_transaction.transaction_amount < 0:
        counterparty_name = gc_transaction.creditor_name
        counterparty_account = gc_transaction.creditor_account
    else:
        counterparty_name = gc_transaction.debtor_name
        counterparty_account = gc_transaction.debtor_account

    # Convert date to datetime if present
    booking_datetime = None
    if gc_transaction.booking_datetime:
        booking_datetime = gc_transaction.booking_datetime
    elif gc_transaction.booking_date:
        booking_datetime = datetime.combine(
            gc_transaction.booking_date, datetime.min.time(), tzinfo=UTC
        )

    value_datetime = None
    if gc_transaction.value_date:
        value_datetime = datetime.combine(
            gc_transaction.value_date, datetime.min.time(), tzinfo=UTC
        )

    now = datetime.now(UTC)

    if existing:
        existing.booking_date = booking_datetime
        existing.value_date = value_datetime
        existing.amount = gc_transaction.transaction_amount
        existing.currency = gc_transaction.currency
        existing.counterparty_name = counterparty_name
        existing.counterparty_account = counterparty_account
        existing.description = gc_transaction.remittance_information
        existing.synced_at = now
        session.flush()
        return existing

    transaction = Transaction(
        account_id=account.id,
        provider_id=gc_transaction.transaction_id,
        booking_date=booking_datetime,
        value_date=value_datetime,
        amount=gc_transaction.transaction_amount,
        currency=gc_transaction.currency,
        counterparty_name=counterparty_name,
        counterparty_account=counterparty_account,
        description=gc_transaction.remittance_information,
        synced_at=now,
    )
    session.add(transaction)
    session.flush()
    return transaction


def sync_all_gocardless_transactions(
    session: Session,
    account: Account,
) -> list[Transaction]:
    """Sync all GoCardless transactions for an account.

    :param session: SQLAlchemy session.
    :param account: The unified Account to sync transactions for.
    :returns: List of synced Transaction objects.
    """
    # Get the GoCardless account ID from the unified account's provider_id
    gc_account_id = account.provider_id

    gc_transactions = (
        session.query(GoCardlessTransaction)
        .filter(GoCardlessTransaction.account_id == gc_account_id)
        .all()
    )

    logger.info(f"Found {len(gc_transactions)} GoCardless transactions for account {account.id}")

    if not gc_transactions:
        return []

    synced: list[Transaction] = []
    for gc_txn in gc_transactions:
        txn = sync_gocardless_transaction(session, gc_txn, account)
        synced.append(txn)

    logger.info(f"Synced {len(synced)} transactions for account {account.id}")
    return synced


# Trading 212 sync operations


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
    from uuid import UUID  # noqa: PLC0415

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
    from uuid import UUID  # noqa: PLC0415

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
