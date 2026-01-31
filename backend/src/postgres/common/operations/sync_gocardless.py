"""GoCardless sync operations for keeping unified tables in sync with provider tables.

This module provides operations to sync data from raw GoCardless tables
(e.g., gc_requisition_links, gc_bank_accounts) to the unified tables
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
    Provider,
    TransactionStatus,
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

logger = get_dagster_logger()

# Maximum days difference between pending and booked transaction dates for reconciliation
RECONCILIATION_DATE_TOLERANCE_DAYS = 5


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


def _find_matching_pending_transaction(
    session: Session,
    account_id: UUID,
    amount: Decimal,
    booking_date: datetime | None,
    counterparty_name: str | None,
) -> Transaction | None:
    """Find a pending transaction that matches the given booked transaction.

    Matches on: same account, same amount, booking date within 5 days,
    and similar counterparty name (if both present).

    :param session: SQLAlchemy session.
    :param account_id: Account UUID.
    :param amount: Transaction amount.
    :param booking_date: Booking datetime.
    :param counterparty_name: Counterparty name.
    :returns: Matching pending transaction or None.
    """
    # Query for active (non-reconciled) transactions with matching amount
    query = session.query(Transaction).filter(
        Transaction.account_id == account_id,
        Transaction.amount == amount,
        Transaction.status == TransactionStatus.ACTIVE.value,
    )

    candidates = query.all()

    for candidate in candidates:
        # Check booking date is within 5 days
        if booking_date and candidate.booking_date:
            date_diff = abs((booking_date - candidate.booking_date).days)
            if date_diff > RECONCILIATION_DATE_TOLERANCE_DAYS:
                continue

        # Check counterparty similarity (simple substring match)
        if counterparty_name and candidate.counterparty_name:
            # Normalise for comparison
            booked_name = counterparty_name.lower().replace(" ", "")
            pending_name = candidate.counterparty_name.lower().replace(" ", "")
            # Check if one contains the other (handles "NETFLIX" vs "NETFLIX.COM*123")
            if booked_name not in pending_name and pending_name not in booked_name:
                continue

        # Found a match
        return candidate

    return None


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

    # If this is a booked transaction, look for matching pending to reconcile
    if gc_transaction.status == "booked":
        pending = _find_matching_pending_transaction(
            session,
            account.id,
            gc_transaction.transaction_amount,
            booking_datetime,
            counterparty_name,
        )
        if pending and pending.id != transaction.id:
            pending.status = TransactionStatus.RECONCILED.value
            pending.reconciled_by_id = transaction.id
            session.flush()
            logger.info(f"Reconciled pending transaction {pending.id} with booked {transaction.id}")

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
