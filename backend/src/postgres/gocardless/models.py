"""GoCardless database model definitions."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.postgres.common.models import _JSONType
from src.postgres.core import Base


class RequisitionLink(Base):
    """Database model for GoCardless requisition links.

    Stores information about bank account connection requests and their status.
    Each requisition represents a request to connect to a specific bank account.
    """

    __tablename__ = "gc_requisition_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    redirect: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(4), nullable=False)
    institution_id: Mapped[str] = mapped_column(String(50), nullable=False)
    agreement: Mapped[str] = mapped_column(String(36), nullable=False)
    reference: Mapped[str] = mapped_column(String(36), nullable=False)
    link: Mapped[str] = mapped_column(String(512), nullable=False)
    ssn: Mapped[str | None] = mapped_column(String(64), nullable=True)
    account_selection: Mapped[bool] = mapped_column(Boolean, nullable=False)
    redirect_immediate: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Dagster tracking columns
    friendly_name: Mapped[str] = mapped_column(String(128), nullable=False)
    dg_account_expired: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # one-to-many → BankAccount.requisition_id
    accounts: Mapped[list["BankAccount"]] = relationship(
        "BankAccount", back_populates="requisition"
    )


class BankAccount(Base):
    """Database model for bank accounts.

    Stores detailed information about bank accounts retrieved from GoCardless API.
    Each account is linked to a requisition and can have multiple transactions and balances.
    """

    __tablename__ = "gc_bank_accounts"

    # Gocardless columns
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    bban: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bic: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cash_account_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    details: Mapped[str | None] = mapped_column(String(512), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    iban: Mapped[str | None] = mapped_column(String(200), nullable=True)
    linked_accounts: Mapped[str | None] = mapped_column(String(128), nullable=True)
    msisdn: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    owner_address_unstructured: Mapped[str | None] = mapped_column(String(256), nullable=True)
    owner_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    product: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str | None] = mapped_column(String(7), nullable=True)
    scan: Mapped[str | None] = mapped_column(String(14), nullable=True)
    usage: Mapped[str | None] = mapped_column(String(4), nullable=True)

    # Dagster tracking columns
    dg_transaction_extract_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationships
    requisition_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("gc_requisition_links.id"), nullable=True
    )

    balances: Mapped[list["Balance"]] = relationship("Balance", back_populates="account")
    requisition: Mapped[RequisitionLink | None] = relationship(
        "RequisitionLink", back_populates="accounts"
    )


class Balance(Base):
    """Database model for account balances.

    Stores balance information for bank accounts retrieved from GoCardless API.
    Each balance record represents the account balance at a specific point in time.
    """

    __tablename__ = "gc_balances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("gc_bank_accounts.id"), nullable=False
    )
    balance_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    balance_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    balance_type: Mapped[str] = mapped_column(String(50), nullable=False)
    credit_limit_included: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_change_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    account: Mapped[BankAccount] = relationship("BankAccount", back_populates="balances")


class GoCardlessTransaction(Base):
    """Database model for bank transactions.

    Stores transaction data from GoCardless API.
    Uses transaction_id + account_id as unique key since transaction_id
    may not be globally unique across banks.
    """

    __tablename__ = "gc_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("gc_bank_accounts.id"), nullable=False, index=True
    )
    transaction_id: Mapped[str] = mapped_column(String(256), nullable=False)
    booking_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    booking_datetime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    transaction_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    # Counterparty info
    creditor_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    creditor_account: Mapped[str | None] = mapped_column(String(64), nullable=True)
    debtor_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    debtor_account: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Description fields
    remittance_information: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    bank_transaction_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    proprietary_bank_code: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="booked")

    # Metadata
    internal_transaction_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    extracted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    account: Mapped[BankAccount] = relationship("BankAccount")

    __table_args__ = (
        UniqueConstraint(
            "account_id", "transaction_id", name="uq_gc_transactions_account_transaction"
        ),
        {"sqlite_autoincrement": True},
    )


class EndUserAgreement(Base):
    """Database model for end user agreements."""

    __tablename__ = "gc_end_user_agreements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    institution_id: Mapped[str] = mapped_column(String(100), nullable=False)
    max_historical_days: Mapped[int] = mapped_column(Integer, nullable=False)
    access_valid_for_days: Mapped[int] = mapped_column(Integer, nullable=False)
    access_scope: Mapped[str] = mapped_column(String(200), nullable=False)
    accepted: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    reconfirmation: Mapped[bool] = mapped_column(Boolean, nullable=False)


class GoCardlessInstitution(Base):
    """Raw GoCardless institution metadata.

    Store as much as practical in this provider-specific table.
    Unified Institution mapping should stay minimal.
    """

    __tablename__ = "gc_institutions"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    bic: Mapped[str | None] = mapped_column(String(32), nullable=True)
    logo: Mapped[str | None] = mapped_column(String(512), nullable=True)
    countries: Mapped[list[str] | None] = mapped_column(_JSONType, nullable=True)
