"""Trading 212 cash balance database operations."""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from src.postgres.trading212.models import T212CashBalance

logger = logging.getLogger(__name__)


def upsert_cash_balance(
    session: Session,
    api_key_id: UUID,
    *,
    free: Decimal,
    blocked: Decimal,
    invested: Decimal,
    pie_cash: Decimal,
    ppl: Decimal,
    result: Decimal,
    total: Decimal,
) -> T212CashBalance:
    """Insert a new cash balance snapshot for a Trading 212 API key.

    Creates a new historical record each time. For the latest balance,
    use get_latest_cash_balance().

    :param session: SQLAlchemy session.
    :param api_key_id: The T212ApiKey record ID.
    :param free: Free cash available for trading.
    :param blocked: Cash blocked (pending orders).
    :param invested: Cash invested in positions.
    :param pie_cash: Cash allocated to pies.
    :param ppl: Profit/loss (unrealised P&L).
    :param result: Realised P&L.
    :param total: Total account value.
    :returns: The created T212CashBalance record.
    """
    balance = T212CashBalance(
        api_key_id=api_key_id,
        free=free,
        blocked=blocked,
        invested=invested,
        pie_cash=pie_cash,
        ppl=ppl,
        result=result,
        total=total,
        fetched_at=datetime.now(UTC),
    )
    session.add(balance)
    session.flush()
    logger.info(f"Created T212 cash balance: api_key_id={api_key_id}, total={total}")
    return balance


def get_latest_cash_balance(session: Session, api_key_id: UUID) -> T212CashBalance | None:
    """Get the most recent cash balance snapshot for a Trading 212 API key.

    :param session: SQLAlchemy session.
    :param api_key_id: The T212ApiKey record ID.
    :returns: The most recent T212CashBalance record, or None if no balances exist.
    """
    return (
        session.query(T212CashBalance)
        .filter(T212CashBalance.api_key_id == api_key_id)
        .order_by(T212CashBalance.fetched_at.desc())
        .first()
    )


def get_cash_balance_history(
    session: Session,
    api_key_id: UUID,
    *,
    limit: int = 30,
) -> list[T212CashBalance]:
    """Get historical cash balance snapshots for a Trading 212 API key.

    :param session: SQLAlchemy session.
    :param api_key_id: The T212ApiKey record ID.
    :param limit: Maximum number of records to return (default 30).
    :returns: List of T212CashBalance records, most recent first.
    """
    return (
        session.query(T212CashBalance)
        .filter(T212CashBalance.api_key_id == api_key_id)
        .order_by(T212CashBalance.fetched_at.desc())
        .limit(limit)
        .all()
    )
