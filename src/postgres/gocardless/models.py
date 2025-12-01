"""GoCardless database model definitions."""

from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import (
    String,
    DateTime,
    Numeric,
    JSON,
    ForeignKey,
    Integer,
    Boolean,
    create_engine,
)
from sqlalchemy.orm import relationship, mapped_column, Mapped

from src.utils.definitions import gocardless_database_url
from src.postgres.core import Base


class RequisitionLink(Base):
    """Database model for GoCardless requisition links.

    Stores information about bank account connection requests and their status.
    Each requisition represents a request to connect to a specific bank account.
    """

    __tablename__ = "requisition_links"

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

    # one-to-many → BankAccount.requisition_id
    accounts: Mapped[List["BankAccount"]] = relationship(
        "BankAccount", back_populates="requisition"
    )


class BankAccount(Base):
    """Database model for bank accounts.

    Stores detailed information about bank accounts retrieved from GoCardless API.
    Each account is linked to a requisition and can have multiple transactions and balances.
    """

    __tablename__ = "bank_accounts"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    bban: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    bic: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    cash_account_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    iban: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    linked_accounts: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    msisdn: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    owner_address_unstructured: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    owner_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    product: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    scan: Mapped[Optional[str]] = mapped_column(String(14), nullable=True)
    usage: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)

    requisition_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("requisition_links.id"), nullable=True
    )

    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="account"
    )
    balances: Mapped[List["Balance"]] = relationship("Balance", back_populates="account")
    requisition: Mapped[Optional[RequisitionLink]] = relationship(
        "RequisitionLink", back_populates="accounts"
    )


class Transaction(Base):
    """Database model for bank transactions.

    Stores individual transaction records retrieved from bank accounts via GoCardless API.
    Each transaction belongs to a specific bank account and contains payment details.
    """

    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    account_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("bank_accounts.id"), nullable=False
    )
    booking_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    booking_date_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    value_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    value_date_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    transaction_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    transaction_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    creditor_name: Mapped[Optional[str]] = mapped_column(String(176), nullable=True)
    debtor_name: Mapped[Optional[str]] = mapped_column(String(176), nullable=True)
    end_to_end_id: Mapped[Optional[str]] = mapped_column(String(35), nullable=True)
    entry_reference: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    additional_information: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    additional_data_structured: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    balance_after: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    account: Mapped[BankAccount] = relationship("BankAccount", back_populates="transactions")


class Balance(Base):
    """Database model for account balances.

    Stores balance information for bank accounts retrieved from GoCardless API.
    Each balance record represents the account balance at a specific point in time.
    """

    __tablename__ = "balances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("bank_accounts.id"), nullable=False
    )
    balance_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    balance_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    balance_type: Mapped[str] = mapped_column(String(50), nullable=False)
    credit_limit_included: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    last_change_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    account: Mapped[BankAccount] = relationship("BankAccount", back_populates="balances")


if __name__ == "__main__":
    engine = create_engine(gocardless_database_url(), echo=True, future=True)
    # session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    Base.metadata.create_all(bind=engine)
