"""Sync operations for keeping unified tables in sync with provider tables.

This module provides operations to sync data from raw provider tables
(e.g., gc_requisition_links, gc_bank_accounts) to the unified tables
(connections, accounts).
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from src.postgres.common.enums import (
    AccountStatus,
    AccountType,
    Provider,
    map_gc_account_status,
    map_gc_requisition_status,
)
from src.postgres.common.models import Account, Connection
from src.postgres.gocardless.models import Balance, BankAccount, RequisitionLink

logger = logging.getLogger(__name__)


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
    requisition = session.get(RequisitionLink, connection.provider_id)
    if not requisition:
        logger.warning(
            f"Requisition not found for connection: id={connection.id}, "
            f"provider_id={connection.provider_id}"
        )
        return connection

    status = map_gc_requisition_status(requisition.status)

    # Update connection from requisition
    connection.status = status.value
    connection.friendly_name = requisition.friendly_name
    connection.synced_at = datetime.now(UTC)
    session.flush()

    logger.info(
        f"Updated connection: id={connection.id}, "
        f"provider_id={connection.provider_id}, status={status.value}"
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

        if balance:
            existing.balance_amount = Decimal(str(balance.balance_amount))
            existing.balance_currency = balance.balance_currency
            existing.balance_type = balance.balance_type
            existing.balance_updated_at = balance.last_change_date or now

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
    )

    if balance:
        account.balance_amount = Decimal(str(balance.balance_amount))
        account.balance_currency = balance.balance_currency
        account.balance_type = balance.balance_type
        account.balance_updated_at = balance.last_change_date or now

    session.add(account)
    session.flush()
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
    bank_accounts = (
        session.query(BankAccount)
        .filter(BankAccount.requisition_id == connection.provider_id)
        .all()
    )

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
