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
    BudgetPeriod,
    ConnectionStatus,
    GoalStatus,
    GoalTrackingMode,
    JobStatus,
    JobType,
    ManualAssetType,
    NotificationType,
    Provider,
    RecurringDirection,
    RecurringFrequency,
    RecurringSource,
    RecurringStatus,
    TransactionStatus,
    get_default_is_liability,
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
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=TransactionStatus.ACTIVE.value
    )
    reconciled_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("transactions.id"),
        nullable=True,
    )

    # Relationships
    account: Mapped[Account] = relationship("Account")
    # All tagging is done via splits (unified model - default 100% for single tag)
    splits: Mapped[list["TransactionSplit"]] = relationship(
        "TransactionSplit",
        back_populates="transaction",
        cascade="all, delete-orphan",
    )
    # Recurring pattern links (for subscription detection)
    pattern_links: Mapped[list["RecurringPatternTransaction"]] = relationship(
        "RecurringPatternTransaction",
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
    job_metadata: Mapped[dict[str, Any]] = mapped_column(_JSONType, nullable=False, default=dict)
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
        Index("idx_transaction_splits_rule_id", "rule_id"),
        Index(
            "idx_transaction_splits_unique",
            "transaction_id",
            "tag_id",
            unique=True,
        ),
    )


class RecurringPattern(Base):
    """Database model for recurring payment patterns.

    Stores detected and user-confirmed recurring payment patterns (subscriptions,
    bills, regular payments). Patterns can be auto-detected from transaction
    history or manually created by users.

    Design philosophy: opt-in model where detection suggests patterns and users
    accept wanted ones (pending -> active).
    """

    __tablename__ = "recurring_patterns"

    # Identity
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    account_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    tag_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tags.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Display
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Amount & scheduling
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RecurringDirection.EXPENSE.value
    )

    # Timing
    anchor_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    next_expected_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_matched_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Status & source
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RecurringStatus.PENDING.value
    )
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RecurringSource.DETECTED.value
    )

    # Matching - common case (dedicated columns for performance)
    merchant_contains: Mapped[str | None] = mapped_column(String(256), nullable=True)
    amount_tolerance_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("10.0")
    )

    # Matching - advanced (JSONB for edge cases)
    # Schema: {"merchant_exact": str, "merchant_regex": str,
    #          "description_contains": str, "description_not_contains": str}
    advanced_rules: Mapped[dict[str, Any] | None] = mapped_column(_JSONType, nullable=True)

    # Stats
    match_count: Mapped[int] = mapped_column(default=0, nullable=False)

    # Detection metadata (for detected patterns)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    occurrence_count: Mapped[int | None] = mapped_column(nullable=True)
    detection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # AI/future extensibility
    ai_metadata: Mapped[dict[str, Any] | None] = mapped_column(_JSONType, nullable=True)

    # Audit
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
    account: Mapped[Account | None] = relationship("Account")
    tag: Mapped["Tag | None"] = relationship("Tag")
    transactions: Mapped[list["RecurringPatternTransaction"]] = relationship(
        "RecurringPatternTransaction",
        back_populates="pattern",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_recurring_patterns_user_id", "user_id"),
        Index("idx_recurring_patterns_status", "status"),
        Index("idx_recurring_patterns_next_date", "next_expected_date"),
        Index(
            "idx_recurring_patterns_user_merchant",
            "user_id",
            "merchant_contains",
            "account_id",
            unique=False,  # Not unique - multiple patterns can match same merchant
        ),
    )

    @property
    def frequency_enum(self) -> RecurringFrequency:
        """Get frequency as RecurringFrequency enum."""
        return RecurringFrequency(self.frequency)

    @property
    def status_enum(self) -> RecurringStatus:
        """Get status as RecurringStatus enum."""
        return RecurringStatus(self.status)

    @property
    def direction_enum(self) -> RecurringDirection:
        """Get direction as RecurringDirection enum."""
        return RecurringDirection(self.direction)

    @property
    def source_enum(self) -> RecurringSource:
        """Get source as RecurringSource enum."""
        return RecurringSource(self.source)


class RecurringPatternTransaction(Base):
    """Database model for pattern-transaction links.

    Links recurring patterns to their matching transactions for
    audit trail and transaction history display.

    Constraint: Each transaction can only be linked to ONE pattern.
    This prevents confusion in forecasting and ensures a recurring
    transaction is definitionally one specific recurring charge.
    """

    __tablename__ = "recurring_pattern_transactions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    pattern_id: Mapped[UUID] = mapped_column(
        ForeignKey("recurring_patterns.id", ondelete="CASCADE"),
        nullable=False,
    )
    transaction_id: Mapped[UUID] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
    )

    matched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )
    is_manual: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    pattern: Mapped["RecurringPattern"] = relationship(
        "RecurringPattern",
        back_populates="transactions",
    )
    transaction: Mapped["Transaction"] = relationship(
        "Transaction",
        back_populates="pattern_links",
    )

    __table_args__ = (
        Index("idx_pattern_transactions_pattern", "pattern_id"),
        # Unique constraint: one pattern per transaction
        Index(
            "idx_pattern_transactions_transaction_unique",
            "transaction_id",
            unique=True,
        ),
    )


class Budget(Base):
    """Database model for monthly budgets per tag.

    Budgets allow users to set spending limits for specific categories (tags).
    Each user can have one budget per tag.
    """

    __tablename__ = "budgets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_id: Mapped[UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    period: Mapped[str] = mapped_column(
        String(20), nullable=False, default=BudgetPeriod.MONTHLY.value
    )
    warning_threshold: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, default=Decimal("0.80")
    )
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
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
        Index("idx_budgets_user_id", "user_id"),
        Index("idx_budgets_user_tag", "user_id", "tag_id", unique=True),
    )

    @property
    def period_enum(self) -> BudgetPeriod:
        """Get period as BudgetPeriod enum."""
        return BudgetPeriod(self.period)


class SavingsGoal(Base):
    """Database model for savings goals.

    Goals support multiple tracking modes:
    - manual: User tracks contributions manually
    - balance: Mirrors linked account balance directly
    - delta: Progress = current balance - starting balance
    - target_balance: Goal completes when account reaches target balance
    """

    __tablename__ = "savings_goals"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # Link to account for automatic balance tracking
    account_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Tracking mode determines how progress is calculated
    tracking_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default=GoalTrackingMode.MANUAL.value
    )
    # Starting balance snapshot for delta mode
    starting_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    # Target balance for target_balance mode (account balance to reach)
    target_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=GoalStatus.ACTIVE.value)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    account: Mapped[Account | None] = relationship("Account")

    __table_args__ = (
        Index("idx_savings_goals_user_id", "user_id"),
        Index("idx_savings_goals_status", "status"),
    )

    @property
    def status_enum(self) -> GoalStatus:
        """Get status as GoalStatus enum."""
        return GoalStatus(self.status)

    @property
    def tracking_mode_enum(self) -> GoalTrackingMode:
        """Get tracking_mode as GoalTrackingMode enum."""
        return GoalTrackingMode(self.tracking_mode)


class Notification(Base):
    """Database model for in-app notifications.

    A unified notification model that supports multiple notification types:
    budget warnings/exceeded, export complete/failed, sync complete/failed.
    Type-specific data is stored in the extra_data JSONB field.

    Deduplication for budget notifications is done by checking extra_data for
    matching (budget_id, period_key). Other notification types don't need
    deduplication.
    """

    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    notification_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    read: Mapped[bool] = mapped_column(default=False, nullable=False)
    extra_data: Mapped[dict[str, Any]] = mapped_column(_JSONType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("idx_notifications_user_id", "user_id"),
        Index("idx_notifications_user_read", "user_id", "read"),
        Index("idx_notifications_created_at", "created_at"),
    )

    @property
    def notification_type_enum(self) -> NotificationType:
        """Get notification_type as NotificationType enum."""
        return NotificationType(self.notification_type)


class BalanceSnapshot(Base):
    """Database model for historical balance snapshots.

    Captures balance data at each sync to build historical trends.
    Append-only table - no updates, just inserts to preserve full history.
    Provider-agnostic, unified structure for all account types.
    """

    __tablename__ = "balance_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Balance fields (unified across providers)
    balance_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    balance_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    balance_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # For investment accounts
    total_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    unrealised_pnl: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    # Metadata
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    # Relationships
    account: Mapped[Account] = relationship("Account")

    __table_args__ = (
        Index("idx_balance_snapshots_account_captured", "account_id", "captured_at"),
        Index("idx_balance_snapshots_captured_at", "captured_at"),
    )


class PlannedTransaction(Base):
    """Database model for planned income and expenses.

    Allows users to manually enter irregular income (freelance payments, bonuses)
    and expenses (annual insurance, holiday) that aren't auto-detected by
    recurring pattern detection. Used in cash flow forecasting.

    Amount convention:
    - Positive = income
    - Negative = expense

    Frequency:
    - null = one-time event
    - weekly/fortnightly/monthly/quarterly/annual = recurring
    """

    __tablename__ = "planned_transactions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Basic info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")

    # Recurrence
    frequency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    next_expected_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Optional account link
    account_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Additional info
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Metadata
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
    account: Mapped[Account | None] = relationship("Account")

    __table_args__ = (
        Index("idx_planned_transactions_user_id", "user_id"),
        Index("idx_planned_transactions_next_date", "next_expected_date"),
        Index("idx_planned_transactions_user_enabled", "user_id", "enabled"),
    )

    @property
    def frequency_enum(self) -> RecurringFrequency | None:
        """Get frequency as RecurringFrequency enum, or None if one-time."""
        return RecurringFrequency(self.frequency) if self.frequency else None

    @property
    def is_income(self) -> bool:
        """Check if this is an income (positive amount)."""
        return self.amount > 0

    @property
    def is_expense(self) -> bool:
        """Check if this is an expense (negative amount)."""
        return self.amount < 0


class FinancialMilestone(Base):
    """Database model for net worth milestones.

    Simple targets for net worth tracking. Displayed as horizontal lines
    on the net worth chart. Automatically marked as achieved when net worth
    exceeds the target.
    """

    __tablename__ = "financial_milestones"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    target_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # Display colour for chart annotation (hex code)
    colour: Mapped[str] = mapped_column(String(7), nullable=False, default="#f59e0b")
    # Achievement tracking
    achieved: Mapped[bool] = mapped_column(default=False, nullable=False)
    achieved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    __table_args__ = (Index("idx_financial_milestones_user_id", "user_id"),)


class ManualAsset(Base):
    """Database model for manually tracked assets and liabilities.

    Allows users to track assets (property, vehicles, pensions) and liabilities
    (student loans, mortgages) that aren't connected via banking APIs. These
    integrate with net worth calculations and support historical value tracking.

    The is_liability field determines whether the asset counts positively or
    negatively towards net worth. It defaults based on asset_type but can be
    overridden (e.g., for negative equity property).
    """

    __tablename__ = "manual_assets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Type and classification
    asset_type: Mapped[str] = mapped_column(String(30), nullable=False)
    custom_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_liability: Mapped[bool] = mapped_column(nullable=False)

    # Display
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Value tracking
    current_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")

    # Optional financial details
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    acquisition_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    acquisition_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Timestamps
    value_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
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
    value_snapshots: Mapped[list["ManualAssetValueSnapshot"]] = relationship(
        "ManualAssetValueSnapshot",
        back_populates="asset",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_manual_assets_user_id", "user_id"),
        Index("idx_manual_assets_user_active", "user_id", "is_active"),
    )

    @property
    def asset_type_enum(self) -> ManualAssetType:
        """Get asset_type as ManualAssetType enum."""
        return ManualAssetType(self.asset_type)

    @property
    def display_type(self) -> str:
        """Get the display name for the asset type.

        Returns custom_type if set, otherwise a formatted version of asset_type.
        """
        if self.custom_type:
            return self.custom_type
        return self.asset_type.replace("_", " ").title()

    @classmethod
    def default_is_liability(cls, asset_type: ManualAssetType) -> bool:
        """Get the default is_liability value for an asset type.

        :param asset_type: The manual asset type.
        :returns: True if this type is typically a liability.
        """
        return get_default_is_liability(asset_type)


class ManualAssetValueSnapshot(Base):
    """Database model for manual asset value history.

    Append-only table tracking value changes over time. Each update to a
    manual asset's value creates a new snapshot for historical tracking.
    """

    __tablename__ = "manual_asset_value_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("manual_assets.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Value at this point in time
    value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    # Optional note for why the value changed
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # When this snapshot was captured
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    # Relationships
    asset: Mapped["ManualAsset"] = relationship(
        "ManualAsset",
        back_populates="value_snapshots",
    )

    __table_args__ = (
        Index("idx_manual_asset_snapshots_asset_captured", "asset_id", "captured_at"),
    )
