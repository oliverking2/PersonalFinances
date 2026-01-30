"""Database operations for Trading 212 history (orders, dividends, transactions)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.postgres.trading212.models import T212Dividend, T212Order, T212Transaction

# =============================================================================
# Orders Operations
# =============================================================================


def upsert_order(
    session: Session,
    api_key_id: UUID,
    *,
    t212_order_id: str,
    ticker: str,
    order_type: str,
    status: str,
    currency: str,
    date_created: datetime,
    parent_order_id: str | None = None,
    instrument_name: str | None = None,
    quantity: Decimal | None = None,
    filled_quantity: Decimal | None = None,
    filled_value: Decimal | None = None,
    limit_price: Decimal | None = None,
    stop_price: Decimal | None = None,
    fill_price: Decimal | None = None,
    date_executed: datetime | None = None,
    date_modified: datetime | None = None,
) -> T212Order:
    """Insert or update a Trading 212 order.

    :param session: SQLAlchemy session.
    :param api_key_id: The T212 API key ID.
    :param t212_order_id: T212's unique order identifier.
    :param ticker: Instrument ticker symbol.
    :param order_type: Order type (MARKET, LIMIT, etc.).
    :param status: Order status (FILLED, CANCELLED, etc.).
    :param currency: Order currency.
    :param date_created: When the order was created.
    :param parent_order_id: Parent order ID if child order.
    :param instrument_name: Human-readable instrument name.
    :param quantity: Requested quantity.
    :param filled_quantity: Filled quantity.
    :param filled_value: Total filled value.
    :param limit_price: Limit price.
    :param stop_price: Stop price.
    :param fill_price: Average fill price.
    :param date_executed: When executed.
    :param date_modified: When last modified.
    :returns: The upserted order.
    """
    # Check for existing order
    existing = session.execute(
        select(T212Order).where(
            T212Order.api_key_id == api_key_id,
            T212Order.t212_order_id == t212_order_id,
        )
    ).scalar_one_or_none()

    if existing:
        # Update existing order
        existing.parent_order_id = parent_order_id
        existing.ticker = ticker
        existing.instrument_name = instrument_name
        existing.order_type = order_type
        existing.status = status
        existing.quantity = quantity
        existing.filled_quantity = filled_quantity
        existing.filled_value = filled_value
        existing.limit_price = limit_price
        existing.stop_price = stop_price
        existing.fill_price = fill_price
        existing.currency = currency
        existing.date_created = date_created
        existing.date_executed = date_executed
        existing.date_modified = date_modified
        session.flush()
        return existing

    # Create new order
    order = T212Order(
        api_key_id=api_key_id,
        t212_order_id=t212_order_id,
        parent_order_id=parent_order_id,
        ticker=ticker,
        instrument_name=instrument_name,
        order_type=order_type,
        status=status,
        quantity=quantity,
        filled_quantity=filled_quantity,
        filled_value=filled_value,
        limit_price=limit_price,
        stop_price=stop_price,
        fill_price=fill_price,
        currency=currency,
        date_created=date_created,
        date_executed=date_executed,
        date_modified=date_modified,
    )
    session.add(order)
    session.flush()
    return order


def get_orders_for_api_key(
    session: Session,
    api_key_id: UUID,
    since_date: datetime | None = None,
) -> list[T212Order]:
    """Get orders for an API key.

    :param session: SQLAlchemy session.
    :param api_key_id: The T212 API key ID.
    :param since_date: Optional filter for orders after this date.
    :returns: List of orders.
    """
    query = select(T212Order).where(T212Order.api_key_id == api_key_id)
    if since_date:
        query = query.where(T212Order.date_created >= since_date)
    query = query.order_by(T212Order.date_created.desc())
    return list(session.execute(query).scalars().all())


# =============================================================================
# Dividends Operations
# =============================================================================


def upsert_dividend(
    session: Session,
    api_key_id: UUID,
    *,
    t212_reference: str,
    ticker: str,
    amount: Decimal,
    currency: str,
    paid_on: datetime,
    instrument_name: str | None = None,
    amount_in_euro: Decimal | None = None,
    gross_amount_per_share: Decimal | None = None,
    quantity: Decimal | None = None,
    dividend_type: str | None = None,
) -> T212Dividend:
    """Insert or update a Trading 212 dividend.

    :param session: SQLAlchemy session.
    :param api_key_id: The T212 API key ID.
    :param t212_reference: T212's unique dividend reference.
    :param ticker: Instrument ticker symbol.
    :param amount: Net dividend amount.
    :param currency: Payment currency.
    :param paid_on: Payment date.
    :param instrument_name: Human-readable instrument name.
    :param amount_in_euro: Amount in EUR.
    :param gross_amount_per_share: Gross dividend per share.
    :param quantity: Number of shares held.
    :param dividend_type: Dividend type (ORDINARY, SPECIAL).
    :returns: The upserted dividend.
    """
    # Check for existing dividend
    existing = session.execute(
        select(T212Dividend).where(
            T212Dividend.api_key_id == api_key_id,
            T212Dividend.t212_reference == t212_reference,
        )
    ).scalar_one_or_none()

    if existing:
        # Update existing dividend
        existing.ticker = ticker
        existing.instrument_name = instrument_name
        existing.amount = amount
        existing.amount_in_euro = amount_in_euro
        existing.gross_amount_per_share = gross_amount_per_share
        existing.quantity = quantity
        existing.currency = currency
        existing.dividend_type = dividend_type
        existing.paid_on = paid_on
        session.flush()
        return existing

    # Create new dividend
    dividend = T212Dividend(
        api_key_id=api_key_id,
        t212_reference=t212_reference,
        ticker=ticker,
        instrument_name=instrument_name,
        amount=amount,
        amount_in_euro=amount_in_euro,
        gross_amount_per_share=gross_amount_per_share,
        quantity=quantity,
        currency=currency,
        dividend_type=dividend_type,
        paid_on=paid_on,
    )
    session.add(dividend)
    session.flush()
    return dividend


def get_dividends_for_api_key(
    session: Session,
    api_key_id: UUID,
    since_date: datetime | None = None,
) -> list[T212Dividend]:
    """Get dividends for an API key.

    :param session: SQLAlchemy session.
    :param api_key_id: The T212 API key ID.
    :param since_date: Optional filter for dividends after this date.
    :returns: List of dividends.
    """
    query = select(T212Dividend).where(T212Dividend.api_key_id == api_key_id)
    if since_date:
        query = query.where(T212Dividend.paid_on >= since_date)
    query = query.order_by(T212Dividend.paid_on.desc())
    return list(session.execute(query).scalars().all())


# =============================================================================
# Transactions Operations
# =============================================================================


def upsert_transaction(
    session: Session,
    api_key_id: UUID,
    *,
    t212_reference: str,
    transaction_type: str,
    amount: Decimal,
    currency: str,
    date_time: datetime,
) -> T212Transaction:
    """Insert or update a Trading 212 transaction.

    :param session: SQLAlchemy session.
    :param api_key_id: The T212 API key ID.
    :param t212_reference: T212's unique transaction reference.
    :param transaction_type: Transaction type (DEPOSIT, WITHDRAWAL, etc.).
    :param amount: Transaction amount.
    :param currency: Transaction currency.
    :param date_time: Transaction timestamp.
    :returns: The upserted transaction.
    """
    # Check for existing transaction
    existing = session.execute(
        select(T212Transaction).where(
            T212Transaction.api_key_id == api_key_id,
            T212Transaction.t212_reference == t212_reference,
        )
    ).scalar_one_or_none()

    if existing:
        # Update existing transaction
        existing.transaction_type = transaction_type
        existing.amount = amount
        existing.currency = currency
        existing.date_time = date_time
        session.flush()
        return existing

    # Create new transaction
    transaction = T212Transaction(
        api_key_id=api_key_id,
        t212_reference=t212_reference,
        transaction_type=transaction_type,
        amount=amount,
        currency=currency,
        date_time=date_time,
    )
    session.add(transaction)
    session.flush()
    return transaction


def get_transactions_for_api_key(
    session: Session,
    api_key_id: UUID,
    since_date: datetime | None = None,
) -> list[T212Transaction]:
    """Get transactions for an API key.

    :param session: SQLAlchemy session.
    :param api_key_id: The T212 API key ID.
    :param since_date: Optional filter for transactions after this date.
    :returns: List of transactions.
    """
    query = select(T212Transaction).where(T212Transaction.api_key_id == api_key_id)
    if since_date:
        query = query.where(T212Transaction.date_time >= since_date)
    query = query.order_by(T212Transaction.date_time.desc())
    return list(session.execute(query).scalars().all())
