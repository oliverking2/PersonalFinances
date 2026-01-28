"""Transaction database operations.

This module provides query operations for Transaction entities.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from src.postgres.common.models import Transaction, TransactionSplit

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _date_to_datetime_start(d: date) -> datetime:
    """Convert a date to datetime at start of day (midnight UTC)."""
    return datetime.combine(d, time.min, tzinfo=UTC)


def _date_to_datetime_end(d: date) -> datetime:
    """Convert a date to datetime at end of day (23:59:59.999999 UTC)."""
    return datetime.combine(d, time.max, tzinfo=UTC)


@dataclass
class TransactionQueryResult:
    """Result of a transaction query with pagination info."""

    transactions: list[Transaction]
    total: int
    page: int
    page_size: int


def get_transactions_for_user(
    session: Session,
    account_ids: list[UUID],
    *,
    tag_ids: list[UUID] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    min_amount: Decimal | None = None,
    max_amount: Decimal | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> TransactionQueryResult:
    """Get transactions for a list of account IDs with optional filters.

    :param session: SQLAlchemy session.
    :param account_ids: List of account UUIDs to query.
    :param tag_ids: Filter to transactions with any of these tags (OR logic).
    :param start_date: Filter from this date (inclusive).
    :param end_date: Filter to this date (inclusive).
    :param min_amount: Minimum transaction amount.
    :param max_amount: Maximum transaction amount.
    :param search: Search term for description/counterparty.
    :param page: Page number (1-indexed).
    :param page_size: Number of items per page.
    :return: TransactionQueryResult with transactions and pagination info.
    """
    if not account_ids:
        return TransactionQueryResult(
            transactions=[],
            total=0,
            page=page,
            page_size=page_size,
        )

    query = session.query(Transaction).filter(Transaction.account_id.in_(account_ids))

    # Apply tag filter (join with transaction_splits if needed)
    # Uses OR logic: transactions with ANY of the specified tags
    if tag_ids:
        query = query.join(TransactionSplit).filter(TransactionSplit.tag_id.in_(tag_ids)).distinct()

    # Apply date filters (convert date to datetime for proper comparison)
    if start_date is not None:
        start_dt = _date_to_datetime_start(start_date)
        query = query.filter(Transaction.booking_date >= start_dt)

    if end_date is not None:
        end_dt = _date_to_datetime_end(end_date)
        query = query.filter(Transaction.booking_date <= end_dt)

    # Apply amount filters
    if min_amount is not None:
        query = query.filter(Transaction.amount >= min_amount)

    if max_amount is not None:
        query = query.filter(Transaction.amount <= max_amount)

    # Apply search filter (case-insensitive)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Transaction.description.ilike(search_pattern))
            | (Transaction.counterparty_name.ilike(search_pattern))
        )

    # Get total count before pagination
    total = query.count()

    # Apply ordering and pagination
    query = query.order_by(Transaction.booking_date.desc().nullslast(), Transaction.id.desc())
    offset = (page - 1) * page_size
    transactions = query.offset(offset).limit(page_size).all()

    logger.info(
        f"Queried transactions: count={len(transactions)}, total={total}, "
        f"page={page}, page_size={page_size}"
    )

    return TransactionQueryResult(
        transactions=transactions,
        total=total,
        page=page,
        page_size=page_size,
    )


def get_transactions_for_account(
    session: Session,
    account_id: UUID,
    *,
    page: int = 1,
    page_size: int = 50,
) -> TransactionQueryResult:
    """Get transactions for a single account.

    Convenience wrapper around get_transactions_for_user for single-account queries.

    :param session: SQLAlchemy session.
    :param account_id: Account UUID to query.
    :param page: Page number (1-indexed).
    :param page_size: Number of items per page.
    :return: TransactionQueryResult with transactions and pagination info.
    """
    return get_transactions_for_user(
        session,
        account_ids=[account_id],
        page=page,
        page_size=page_size,
    )
