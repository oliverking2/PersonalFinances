"""Account database operations.

This module provides CRUD operations for Account entities.
"""

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from src.postgres.common.enums import AccountCategory, AccountStatus
from src.postgres.common.models import Account

logger = logging.getLogger(__name__)


def get_account_by_id(session: Session, account_id: UUID) -> Account | None:
    """Get an account by its ID.

    :param session: SQLAlchemy session.
    :param account_id: Account's UUID.
    :return: Account if found, None otherwise.
    """
    return session.get(Account, account_id)


def get_accounts_by_connection_id(
    session: Session,
    connection_id: UUID,
    status: AccountStatus | None = None,
) -> list[Account]:
    """Get all accounts for a connection.

    :param session: SQLAlchemy session.
    :param connection_id: Connection's UUID.
    :param status: Filter by status (optional).
    :return: List of accounts.
    """
    query = session.query(Account).filter(Account.connection_id == connection_id)

    if status is not None:
        query = query.filter(Account.status == status.value)

    return query.order_by(Account.name).all()


def create_account(  # noqa: PLR0913
    session: Session,
    connection_id: UUID,
    provider_id: str,
    status: AccountStatus,
    display_name: str | None = None,
    name: str | None = None,
    iban: str | None = None,
    currency: str | None = None,
) -> Account:
    """Create a new account.

    :param session: SQLAlchemy session.
    :param connection_id: Parent connection's UUID.
    :param provider_id: Provider-specific account ID.
    :param status: Account status.
    :param display_name: User-editable display name (optional).
    :param name: Provider-sourced name (optional).
    :param iban: IBAN (optional).
    :param currency: Currency code (optional).
    :return: Created Account entity.
    """
    account = Account(
        connection_id=connection_id,
        provider_id=provider_id,
        status=status.value,
        display_name=display_name,
        name=name,
        iban=iban,
        currency=currency,
    )
    session.add(account)
    session.flush()
    logger.info(
        f"Created account: id={account.id}, connection_id={connection_id}, "
        f"provider_id={provider_id}"
    )
    return account


def update_account(  # noqa: PLR0913
    session: Session,
    account_id: UUID,
    display_name: str | None = None,
    category: AccountCategory | None = None,
    min_balance: Decimal | None = None,
    *,
    clear_display_name: bool = False,
    clear_category: bool = False,
    clear_min_balance: bool = False,
) -> Account | None:
    """Update an account's settings.

    :param session: SQLAlchemy session.
    :param account_id: Account's UUID.
    :param display_name: New display name (only updates if not None).
    :param category: New category (only updates if not None).
    :param min_balance: New min balance (only updates if not None).
    :param clear_display_name: Set to True to explicitly clear display_name.
    :param clear_category: Set to True to explicitly clear category.
    :param clear_min_balance: Set to True to explicitly clear min_balance.
    :return: Updated Account, or None if not found.
    """
    account = get_account_by_id(session, account_id)
    if account is None:
        return None

    updated_fields = []

    if display_name is not None or clear_display_name:
        account.display_name = display_name
        updated_fields.append("display_name")

    if category is not None or clear_category:
        account.category = category.value if category else None
        updated_fields.append("category")

    if min_balance is not None or clear_min_balance:
        account.min_balance = min_balance
        updated_fields.append("min_balance")

    if updated_fields:
        session.flush()
        logger.info(f"Updated account: id={account_id}, fields={updated_fields}")

    return account
