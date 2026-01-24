"""Common database models for provider-agnostic data.

This module defines standardised tables that abstract over provider-specific
tables (e.g., gc_requisition_links, gc_bank_accounts) to provide a unified
view for the frontend.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.postgres.common.enums import AccountStatus, ConnectionStatus, Provider
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

    # Balance fields (synced from provider tables)
    balance_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    balance_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    balance_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    balance_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    connection: Mapped[Connection] = relationship(
        "Connection",
        back_populates="accounts",
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
