"""Balance snapshot database operations.

This module provides operations for creating and querying balance snapshots,
used to track historical account balances over time.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from src.postgres.common.models import BalanceSnapshot

logger = logging.getLogger(__name__)


def create_balance_snapshot(
    session: Session,
    account_id: UUID,
    balance_amount: Decimal,
    balance_currency: str,
    balance_type: str | None = None,
    total_value: Decimal | None = None,
    unrealised_pnl: Decimal | None = None,
    source_updated_at: datetime | None = None,
) -> BalanceSnapshot:
    """Create a new balance snapshot for an account.

    Captures the current balance state for historical tracking.
    This is an append-only operation - snapshots are never updated.

    :param session: SQLAlchemy session.
    :param account_id: Account UUID.
    :param balance_amount: Current balance amount.
    :param balance_currency: Currency code (ISO 4217).
    :param balance_type: Balance type (e.g., interimAvailable, cash).
    :param total_value: Total portfolio value (for investment accounts).
    :param unrealised_pnl: Unrealised profit/loss (for investment accounts).
    :param source_updated_at: When the provider last updated this balance.
    :returns: Created BalanceSnapshot entity.
    """
    snapshot = BalanceSnapshot(
        account_id=account_id,
        balance_amount=balance_amount,
        balance_currency=balance_currency,
        balance_type=balance_type,
        total_value=total_value,
        unrealised_pnl=unrealised_pnl,
        source_updated_at=source_updated_at,
        captured_at=datetime.now(UTC),
    )
    session.add(snapshot)
    session.flush()
    logger.debug(
        f"Created balance snapshot: account_id={account_id}, "
        f"balance={balance_amount} {balance_currency}"
    )
    return snapshot


def get_latest_snapshot_for_account(
    session: Session,
    account_id: UUID,
) -> BalanceSnapshot | None:
    """Get the most recent balance snapshot for an account.

    :param session: SQLAlchemy session.
    :param account_id: Account UUID.
    :returns: Latest BalanceSnapshot or None if no snapshots exist.
    """
    return (
        session.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id)
        .order_by(BalanceSnapshot.captured_at.desc())
        .first()
    )


def get_snapshots_for_account(
    session: Session,
    account_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int | None = None,
) -> list[BalanceSnapshot]:
    """Get balance snapshots for an account within a date range.

    :param session: SQLAlchemy session.
    :param account_id: Account UUID.
    :param start_date: Start of date range (inclusive).
    :param end_date: End of date range (inclusive).
    :param limit: Maximum number of snapshots to return.
    :returns: List of BalanceSnapshot entities, ordered by captured_at ascending.
    """
    query = session.query(BalanceSnapshot).filter(BalanceSnapshot.account_id == account_id)

    if start_date:
        query = query.filter(BalanceSnapshot.captured_at >= start_date)
    if end_date:
        query = query.filter(BalanceSnapshot.captured_at <= end_date)

    query = query.order_by(BalanceSnapshot.captured_at.asc())

    if limit:
        query = query.limit(limit)

    return query.all()


def count_snapshots_for_account(
    session: Session,
    account_id: UUID,
) -> int:
    """Count total balance snapshots for an account.

    :param session: SQLAlchemy session.
    :param account_id: Account UUID.
    :returns: Number of snapshots.
    """
    return session.query(BalanceSnapshot).filter(BalanceSnapshot.account_id == account_id).count()
