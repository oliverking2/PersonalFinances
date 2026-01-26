"""Common database models for provider-agnostic data.

This module defines standardised tables that abstract over provider-specific
tables (e.g., gc_requisition_links, gc_bank_accounts) to provide a unified
view for the frontend.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Import User to ensure SQLAlchemy knows about the users table when resolving
# the Connection.user_id foreign key. Without this, operations that use Connection
# without importing auth.models will fail with NoReferencedTableError.
from src.postgres.auth.models import User  # noqa: F401
from src.postgres.common.enums import (
    AccountCategory,
    AccountStatus,
    AccountType,
    ConnectionStatus,
    JobStatus,
    JobType,
    Provider,
)
from src.postgres.core import Base

# Use JSON type that falls back gracefully to SQLite JSON while using JSONB on PostgreSQL
_JSONType = JSON().with_variant(JSONB(), "postgresql")


def _utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(UTC)


class Institution(Base):
    """Database model for institution metadata.

    Stores information about financial institutions from various providers.
    The ID is the provider's institution identifier (e.g., NATIONWIDE_NAIAGB21).
    """

    __tablename__ = "institutions"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    countries: Mapped[list[str] | None] = mapped_column(_JSONType, nullable=True)
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

    connections: Mapped[list["Connection"]] = relationship(
        "Connection",
        back_populates="institution",
    )


class Connection(Base):
    """Database model for standardised connections.

    Represents a user's connection to a financial institution, abstracting
    over provider-specific concepts (e.g., GoCardless requisitions).
    """

    __tablename__ = "connections"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_id: Mapped[str] = mapped_column(String(128), nullable=False)
    institution_id: Mapped[str] = mapped_column(
        ForeignKey("institutions.id"),
        nullable=False,
    )
    friendly_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    # Relationships
    institution: Mapped[Institution] = relationship(
        "Institution",
        back_populates="connections",
    )
    accounts: Mapped[list["Account"]] = relationship(
        "Account",
        back_populates="connection",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_connections_user_id", "user_id"),
        Index("idx_connections_provider_provider_id", "provider", "provider_id", unique=True),
    )

    @property
    def status_enum(self) -> ConnectionStatus:
        """Get status as ConnectionStatus enum."""
        return ConnectionStatus(self.status)

    @property
    def provider_enum(self) -> Provider:
        """Get provider as Provider enum."""
        return Provider(self.provider)


class Account(Base):
    """Database model for standardised accounts.

    Represents a financial account within a connection, abstracting over
    provider-specific concepts (e.g., GoCardless bank accounts).
    """

    __tablename__ = "accounts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    connection_id: Mapped[UUID] = mapped_column(
        ForeignKey("connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_id: Mapped[str] = mapped_column(String(128), nullable=False)
    account_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AccountType.BANK.value
    )
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    iban: Mapped[str | None] = mapped_column(String(200), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    # User-configurable settings
    category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    min_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    credit_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    # Balance fields (synced from provider tables - bank accounts)
    balance_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    balance_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    balance_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    balance_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Investment fields (for trading/investment accounts)
    total_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    unrealised_pnl: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    # Relationships
    connection: Mapped[Connection] = relationship(
        "Connection",
        back_populates="accounts",
    )
    holdings: Mapped[list["Holding"]] = relationship(
        "Holding",
        back_populates="account",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_accounts_connection_id", "connection_id"),
        Index(
            "idx_accounts_connection_provider_id",
            "connection_id",
            "provider_id",
            unique=True,
        ),
    )

    @property
    def status_enum(self) -> AccountStatus:
        """Get status as AccountStatus enum."""
        return AccountStatus(self.status)

    @property
    def account_type_enum(self) -> AccountType:
        """Get account_type as AccountType enum."""
        return AccountType(self.account_type)

    @property
    def category_enum(self) -> AccountCategory | None:
        """Get category as AccountCategory enum, or None if not set."""
        return AccountCategory(self.category) if self.category else None


class Holding(Base):
    """Database model for investment holdings.

    Represents a position in an investment or trading account.
    Used for Trading212 positions, Vanguard fund holdings, etc.
    """

    __tablename__ = "holdings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    average_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    current_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    current_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    unrealised_pnl: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )

    # Relationships
    account: Mapped[Account] = relationship(
        "Account",
        back_populates="holdings",
    )

    __table_args__ = (
        Index("idx_holdings_account_id", "account_id"),
        Index("idx_holdings_account_ticker", "account_id", "ticker", unique=True),
    )


class Transaction(Base):
    """Database model for standardised transactions.

    Represents a financial transaction within an account, abstracting over
    provider-specific concepts (e.g., GoCardless transactions).
    """

    __tablename__ = "transactions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_id: Mapped[str] = mapped_column(String(256), nullable=False)
    booking_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    value_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    # Counterparty info
    counterparty_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    counterparty_account: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Description
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Classification
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # User-added note (useful for split context or personal annotations)
    user_note: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Metadata
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    # Relationships
    account: Mapped[Account] = relationship("Account")
    # All tagging is done via splits (unified model - default 100% for single tag)
    splits: Mapped[list["TransactionSplit"]] = relationship(
        "TransactionSplit",
        back_populates="transaction",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_transactions_account_id", "account_id"),
        Index("idx_transactions_booking_date", "booking_date"),
        Index(
            "idx_transactions_account_provider_id",
            "account_id",
            "provider_id",
            unique=True,
        ),
    )


class Job(Base):
    """Database model for background jobs.

    Tracks the status of asynchronous jobs such as data sync operations,
    exports, and other long-running tasks. Jobs can be associated with
    a specific entity (e.g., a connection) or be global.
    """

    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[UUID | None] = mapped_column(nullable=True)
    dagster_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("idx_jobs_user_status", "user_id", "status"),
        Index("idx_jobs_entity", "entity_type", "entity_id"),
    )

    @property
    def job_type_enum(self) -> JobType:
        """Get job_type as JobType enum."""
        return JobType(self.job_type)

    @property
    def status_enum(self) -> JobStatus:
        """Get status as JobStatus enum."""
        return JobStatus(self.status)


class Tag(Base):
    """Database model for user-defined tags.

    Tags are user-scoped labels for categorising transactions.
    Each user can create up to 100 tags with unique names.

    Standard tags are pre-defined and seeded for each user on registration.
    They cannot be deleted but can be hidden from the UI.
    """

    __tablename__ = "tags"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    colour: Mapped[str | None] = mapped_column(String(7), nullable=True)
    is_standard: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(default=False, nullable=False)
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

    __table_args__ = (
        Index("idx_tags_user_id", "user_id"),
        Index("idx_tags_user_name", "user_id", "name", unique=True),
    )


class TagRule(Base):
    """Database model for auto-tagging rules.

    Rules define conditions for automatically tagging transactions.
    They are evaluated in priority order (lowest number = highest priority).
    """

    __tablename__ = "tag_rules"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    tag_id: Mapped[UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(default=0, nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Filter conditions stored as JSON (see RuleConditions TypedDict in operations/tag_rules.py)
    conditions: Mapped[dict[str, Any]] = mapped_column(_JSONType, nullable=False, default=dict)

    # Account filter kept as FK for referential integrity
    account_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"),
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
    tag: Mapped["Tag"] = relationship("Tag")

    __table_args__ = (
        Index("idx_tag_rules_user_id", "user_id"),
        Index("idx_tag_rules_user_priority", "user_id", "priority"),
    )


class TransactionSplit(Base):
    """Database model for transaction splits (unified tagging model).

    All transaction tagging is done via splits. A simple tag is a 100% split.
    Complex splits allocate amounts across multiple tags for accurate budgeting.

    For example:
    - Simple: £50 coffee -> 100% to Dining tag
    - Split: £100 supermarket -> £60 Groceries + £40 Household

    The sum of all splits should equal the transaction amount (absolute value).
    This constraint is enforced at the application level, not in the database.
    """

    __tablename__ = "transaction_splits"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    transaction_id: Mapped[UUID] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_id: Mapped[UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    # Auto-tagging metadata
    is_auto: Mapped[bool] = mapped_column(default=False, nullable=False)
    rule_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tag_rules.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    # Relationship to get rule details
    rule: Mapped["TagRule | None"] = relationship("TagRule")

    # Relationships
    transaction: Mapped["Transaction"] = relationship(
        "Transaction",
        back_populates="splits",
    )
    tag: Mapped["Tag"] = relationship("Tag")

    __table_args__ = (
        Index("idx_transaction_splits_transaction", "transaction_id"),
        Index("idx_transaction_splits_tag", "tag_id"),
        Index(
            "idx_transaction_splits_unique",
            "transaction_id",
            "tag_id",
            unique=True,
        ),
    )
