"""Trading 212 database model definitions.

Stores API key credentials, cash balance snapshots, orders, dividends,
and transactions for Trading 212 integration.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.postgres.core import Base


def _utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(UTC)


class T212ApiKey(Base):
    """Database model for Trading 212 API keys.

    Stores encrypted API keys for Trading 212 Invest API access.
    Each user can have multiple API keys for different T212 accounts.
    """

    __tablename__ = "t212_api_keys"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    friendly_name: Mapped[str] = mapped_column(String(128), nullable=False)

    # Trading 212 account metadata (from API)
    t212_account_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    currency_code: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # Status: active = API key works, error = invalid/revoked
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )

    # Relationships
    cash_balances: Mapped[list["T212CashBalance"]] = relationship(
        "T212CashBalance",
        back_populates="api_key",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_t212_api_keys_user_id", "user_id"),
        Index("idx_t212_api_keys_status", "status"),
    )


class T212CashBalance(Base):
    """Database model for Trading 212 cash balance snapshots.

    Stores historical cash balance data from the Trading 212 equity/account/cash endpoint.
    Each record represents a point-in-time snapshot of the account's cash position.
    """

    __tablename__ = "t212_cash_balances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key_id: Mapped[UUID] = mapped_column(
        ForeignKey("t212_api_keys.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Cash balance components from T212 API
    free: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    blocked: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    invested: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    pie_cash: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    ppl: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)  # Profit/loss
    result: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    # Timestamp when balance was fetched
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    # Relationships
    api_key: Mapped[T212ApiKey] = relationship(
        "T212ApiKey",
        back_populates="cash_balances",
    )

    __table_args__ = (
        Index("idx_t212_cash_balances_api_key_id", "api_key_id"),
        Index("idx_t212_cash_balances_fetched_at", "fetched_at"),
    )


class T212Order(Base):
    """Database model for Trading 212 order history.

    Stores historical buy/sell orders from the Trading 212 equity/history/orders endpoint.
    """

    __tablename__ = "t212_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key_id: Mapped[UUID] = mapped_column(
        ForeignKey("t212_api_keys.id", ondelete="CASCADE"),
        nullable=False,
    )

    # T212 order identifiers
    t212_order_id: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Instrument details
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    instrument_name: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Order type and status
    order_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # MARKET, LIMIT, STOP, STOP_LIMIT
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # FILLED, REJECTED, CANCELLED

    # Quantities
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    filled_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    filled_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    # Prices
    limit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    stop_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    fill_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

    # Currency and fees
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    # Timestamps from T212
    date_created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    date_executed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_modified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Local timestamp
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    # Relationships
    api_key: Mapped[T212ApiKey] = relationship("T212ApiKey")

    __table_args__ = (
        Index("idx_t212_orders_api_key_id", "api_key_id"),
        Index("idx_t212_orders_t212_order_id", "t212_order_id"),
        Index("idx_t212_orders_date_created", "date_created"),
        Index("idx_t212_orders_ticker", "ticker"),
    )


class T212Dividend(Base):
    """Database model for Trading 212 dividend history.

    Stores dividend payments from the Trading 212 equity/history/dividends endpoint.
    """

    __tablename__ = "t212_dividends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key_id: Mapped[UUID] = mapped_column(
        ForeignKey("t212_api_keys.id", ondelete="CASCADE"),
        nullable=False,
    )

    # T212 dividend identifiers
    t212_reference: Mapped[str] = mapped_column(String(64), nullable=False)

    # Instrument details
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    instrument_name: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Payment details
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    amount_in_euro: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    gross_amount_per_share: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    # Type: ORDINARY, SPECIAL, etc.
    dividend_type: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Timestamps
    paid_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    # Relationships
    api_key: Mapped[T212ApiKey] = relationship("T212ApiKey")

    __table_args__ = (
        Index("idx_t212_dividends_api_key_id", "api_key_id"),
        Index("idx_t212_dividends_t212_reference", "t212_reference"),
        Index("idx_t212_dividends_paid_on", "paid_on"),
        Index("idx_t212_dividends_ticker", "ticker"),
    )


class T212Transaction(Base):
    """Database model for Trading 212 transaction history.

    Stores cash movements from the Trading 212 equity/history/transactions endpoint.
    This includes deposits, withdrawals, interest, fees, etc.
    """

    __tablename__ = "t212_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key_id: Mapped[UUID] = mapped_column(
        ForeignKey("t212_api_keys.id", ondelete="CASCADE"),
        nullable=False,
    )

    # T212 transaction identifiers
    t212_reference: Mapped[str] = mapped_column(String(64), nullable=False)

    # Transaction type: DEPOSIT, WITHDRAWAL, DIVIDEND, INTEREST, FEE, etc.
    transaction_type: Mapped[str] = mapped_column(String(64), nullable=False)

    # Amount details
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    # Timestamps
    date_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    # Relationships
    api_key: Mapped[T212ApiKey] = relationship("T212ApiKey")

    __table_args__ = (
        Index("idx_t212_transactions_api_key_id", "api_key_id"),
        Index("idx_t212_transactions_t212_reference", "t212_reference"),
        Index("idx_t212_transactions_date_time", "date_time"),
        Index("idx_t212_transactions_type", "transaction_type"),
    )
