"""Planned transaction database operations.

This module provides CRUD operations for PlannedTransaction entities.
Used for manual entry of irregular income/expenses for cash flow forecasting.
"""

import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.postgres.common.enums import RecurringFrequency
from src.postgres.common.models import PlannedTransaction

logger = logging.getLogger(__name__)

# Sentinel for distinguishing "not provided" from "set to None"
_NOT_SET = object()


def get_planned_transaction_by_id(
    session: Session,
    transaction_id: UUID,
) -> PlannedTransaction | None:
    """Get a planned transaction by its ID.

    :param session: SQLAlchemy session.
    :param transaction_id: PlannedTransaction's UUID.
    :return: PlannedTransaction if found, None otherwise.
    """
    return session.get(PlannedTransaction, transaction_id)


def get_planned_transactions_by_user_id(
    session: Session,
    user_id: UUID,
    *,
    enabled_only: bool = False,
    direction: str | None = None,
) -> list[PlannedTransaction]:
    """Get all planned transactions for a user.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param enabled_only: If True, only return enabled transactions.
    :param direction: Filter by direction - 'income' (positive) or 'expense' (negative).
    :return: List of planned transactions ordered by next_expected_date.
    """
    query = session.query(PlannedTransaction).filter(PlannedTransaction.user_id == user_id)

    if enabled_only:
        query = query.filter(PlannedTransaction.enabled.is_(True))

    if direction == "income":
        query = query.filter(PlannedTransaction.amount > 0)
    elif direction == "expense":
        query = query.filter(PlannedTransaction.amount < 0)

    return query.order_by(PlannedTransaction.next_expected_date.asc().nullslast()).all()


def get_upcoming_planned_transactions(
    session: Session,
    user_id: UUID,
    *,
    from_date: datetime,
    to_date: datetime,
) -> list[PlannedTransaction]:
    """Get planned transactions within a date range.

    Returns enabled transactions where:
    - next_expected_date is within the range
    - AND (end_date is null OR end_date >= from_date)

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param from_date: Start of date range (inclusive).
    :param to_date: End of date range (inclusive).
    :return: List of upcoming planned transactions.
    """
    return (
        session.query(PlannedTransaction)
        .filter(
            PlannedTransaction.user_id == user_id,
            PlannedTransaction.enabled.is_(True),
            PlannedTransaction.next_expected_date.isnot(None),
            PlannedTransaction.next_expected_date >= from_date,
            PlannedTransaction.next_expected_date <= to_date,
            or_(
                PlannedTransaction.end_date.is_(None),
                PlannedTransaction.end_date >= from_date,
            ),
        )
        .order_by(PlannedTransaction.next_expected_date.asc())
        .all()
    )


def create_planned_transaction(
    session: Session,
    user_id: UUID,
    name: str,
    amount: Decimal,
    *,
    currency: str = "GBP",
    frequency: RecurringFrequency | None = None,
    next_expected_date: datetime | None = None,
    end_date: datetime | None = None,
    account_id: UUID | None = None,
    notes: str | None = None,
    enabled: bool = True,
) -> PlannedTransaction:
    """Create a new planned transaction.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param name: Name/description (e.g., "Annual Insurance", "Freelance Payment").
    :param amount: Amount (positive = income, negative = expense).
    :param currency: Currency code (default GBP).
    :param frequency: Recurrence frequency (None = one-time).
    :param next_expected_date: When this transaction is next expected.
    :param end_date: When recurring transactions should stop (optional).
    :param account_id: Optional linked account.
    :param notes: Optional notes.
    :param enabled: Whether this is active (default True).
    :return: Created PlannedTransaction entity.
    """
    transaction = PlannedTransaction(
        user_id=user_id,
        name=name,
        amount=amount,
        currency=currency,
        frequency=frequency.value if frequency else None,
        next_expected_date=next_expected_date,
        end_date=end_date,
        account_id=account_id,
        notes=notes,
        enabled=enabled,
    )
    session.add(transaction)
    session.flush()

    direction = "income" if amount > 0 else "expense"
    logger.info(
        f"Created planned transaction: id={transaction.id}, user_id={user_id}, "
        f"name={name}, amount={amount}, direction={direction}"
    )
    return transaction


def update_planned_transaction(
    session: Session,
    transaction_id: UUID,
    *,
    name: str | None = None,
    amount: Decimal | None = None,
    currency: str | None = None,
    frequency: RecurringFrequency | None | object = _NOT_SET,
    next_expected_date: datetime | None | object = _NOT_SET,
    end_date: datetime | None | object = _NOT_SET,
    account_id: UUID | None | object = _NOT_SET,
    notes: str | None | object = _NOT_SET,
    enabled: bool | None = None,
) -> PlannedTransaction | None:
    """Update a planned transaction.

    Use _NOT_SET sentinel for nullable fields that shouldn't be updated.
    Use None to clear nullable fields.

    :param session: SQLAlchemy session.
    :param transaction_id: PlannedTransaction's UUID.
    :param name: New name.
    :param amount: New amount.
    :param currency: New currency.
    :param frequency: New frequency (None = one-time).
    :param next_expected_date: New next expected date.
    :param end_date: New end date.
    :param account_id: New account link.
    :param notes: New notes.
    :param enabled: New enabled state.
    :return: Updated PlannedTransaction, or None if not found.
    """
    transaction = get_planned_transaction_by_id(session, transaction_id)
    if transaction is None:
        return None

    if name is not None:
        transaction.name = name

    if amount is not None:
        transaction.amount = amount

    if currency is not None:
        transaction.currency = currency

    if frequency is not _NOT_SET:
        transaction.frequency = frequency.value if frequency else None  # type: ignore[attr-defined]

    if next_expected_date is not _NOT_SET:
        transaction.next_expected_date = next_expected_date  # type: ignore[assignment]

    if end_date is not _NOT_SET:
        transaction.end_date = end_date  # type: ignore[assignment]

    if account_id is not _NOT_SET:
        transaction.account_id = account_id  # type: ignore[assignment]

    if notes is not _NOT_SET:
        transaction.notes = notes  # type: ignore[assignment]

    if enabled is not None:
        transaction.enabled = enabled

    session.flush()
    logger.info(f"Updated planned transaction: id={transaction_id}")
    return transaction


def delete_planned_transaction(session: Session, transaction_id: UUID) -> bool:
    """Delete a planned transaction.

    :param session: SQLAlchemy session.
    :param transaction_id: PlannedTransaction's UUID.
    :return: True if deleted, False if not found.
    """
    transaction = get_planned_transaction_by_id(session, transaction_id)
    if transaction is None:
        return False

    session.delete(transaction)
    session.flush()
    logger.info(f"Deleted planned transaction: id={transaction_id}")
    return True


def get_planned_income_total(
    session: Session,
    user_id: UUID,
) -> Decimal:
    """Get total monthly income from planned transactions.

    Aggregates enabled income (positive amounts), normalising to monthly:
    - Weekly: multiply by 4.33
    - Fortnightly: multiply by 2.17
    - Monthly: as-is
    - Quarterly: divide by 3
    - Annual: divide by 12
    - One-time: excluded

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :return: Total normalised monthly income.
    """
    transactions = get_planned_transactions_by_user_id(
        session, user_id, enabled_only=True, direction="income"
    )

    total = Decimal("0")
    for txn in transactions:
        if txn.frequency is None:
            # One-time: skip for recurring monthly total
            continue

        freq = RecurringFrequency(txn.frequency)
        normalised = _normalise_to_monthly(txn.amount, freq)
        total += normalised

    return total


def get_planned_expense_total(
    session: Session,
    user_id: UUID,
) -> Decimal:
    """Get total monthly expenses from planned transactions.

    Aggregates enabled expenses (negative amounts), normalising to monthly.
    Returns absolute value (positive number).

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :return: Total normalised monthly expenses (absolute value).
    """
    transactions = get_planned_transactions_by_user_id(
        session, user_id, enabled_only=True, direction="expense"
    )

    total = Decimal("0")
    for txn in transactions:
        if txn.frequency is None:
            # One-time: skip for recurring monthly total
            continue

        freq = RecurringFrequency(txn.frequency)
        normalised = _normalise_to_monthly(abs(txn.amount), freq)
        total += normalised

    return total


def _normalise_to_monthly(amount: Decimal, frequency: RecurringFrequency) -> Decimal:
    """Normalise an amount to monthly equivalent.

    :param amount: The original amount.
    :param frequency: The frequency of the transaction.
    :return: Monthly-normalised amount.
    """
    multipliers = {
        RecurringFrequency.WEEKLY: Decimal("4.33"),
        RecurringFrequency.FORTNIGHTLY: Decimal("2.17"),
        RecurringFrequency.MONTHLY: Decimal("1"),
        RecurringFrequency.QUARTERLY: Decimal("0.33"),
        RecurringFrequency.ANNUAL: Decimal("0.083"),
        RecurringFrequency.IRREGULAR: Decimal("1"),  # Assume monthly for irregular
    }
    multiplier = multipliers.get(frequency, Decimal("1"))
    return amount * multiplier
