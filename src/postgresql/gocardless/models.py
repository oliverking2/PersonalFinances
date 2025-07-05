"""GoCardless database model definitions."""

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Numeric,
    JSON,
    ForeignKey,
    Integer,
    Boolean,
    create_engine,
)
from sqlalchemy.orm import relationship, DeclarativeBase

from src.utils.definitions import gocardless_database_url


class Base(DeclarativeBase):
    """Base class for all database tables.

    Provides the declarative base for SQLAlchemy ORM models.
    """


class RequisitionLink(Base):
    """Database model for GoCardless requisition links.

    Stores information about bank account connection requests and their status.
    Each requisition represents a request to connect to a specific bank account.
    """

    __tablename__ = "requisition_links"

    id = Column(String(36), primary_key=True)
    created = Column(DateTime, nullable=False)
    updated = Column(DateTime, nullable=False)
    redirect = Column(String(255), nullable=False)
    status = Column(String(4), nullable=False)
    institution_id = Column(String(50), nullable=False)
    agreement = Column(String(36), nullable=False)
    reference = Column(String(36), nullable=False)
    link = Column(String(512), nullable=False)
    ssn = Column(String(64), nullable=True)
    account_selection = Column(Boolean, nullable=False)
    redirect_immediate = Column(Boolean, nullable=False)

    # one-to-many → BankAccount.requisition_id
    accounts = relationship(
        "BankAccount",
        back_populates="requisition",
    )


class BankAccount(Base):
    """Database model for bank accounts.

    Stores detailed information about bank accounts retrieved from GoCardless API.
    Each account is linked to a requisition and can have multiple transactions and balances.
    """

    __tablename__ = "bank_accounts"

    id = Column(String(128), primary_key=True)
    bban = Column(String(128), nullable=True)
    bic = Column(String(128), nullable=True)
    cash_account_type = Column(String(50), nullable=True)
    currency = Column(String(3), nullable=True)
    details = Column(String(512), nullable=True)
    display_name = Column(String(128), nullable=True)
    iban = Column(String(200), nullable=True)
    linked_accounts = Column(String(128), nullable=True)
    msisdn = Column(String(64), nullable=True)
    name = Column(String(128), nullable=True)
    owner_address_unstructured = Column(String(256), nullable=True)
    owner_name = Column(String(256), nullable=True)
    product = Column(String(64), nullable=True)
    status = Column(String(7), nullable=True)
    scan = Column(String(14), nullable=True)
    usage = Column(String(4), nullable=True)

    requisition_id = Column(
        String(36),
        ForeignKey("requisition_links.id"),
        nullable=True,
    )

    # relationships
    transactions = relationship(
        "Transaction",
        back_populates="account",
    )
    balances = relationship(
        "Balance",
        back_populates="account",
    )
    requisition = relationship(
        "RequisitionLink",
        back_populates="accounts",
    )


class Transaction(Base):
    """Database model for bank transactions.

    Stores individual transaction records retrieved from bank accounts via GoCardless API.
    Each transaction belongs to a specific bank account and contains payment details.
    """

    __tablename__ = "transactions"

    id = Column(String(32), primary_key=True)
    account_id = Column(
        String(128),
        ForeignKey("bank_accounts.id"),
        nullable=False,
    )
    booking_date = Column(DateTime, nullable=True)
    booking_date_time = Column(DateTime, nullable=True)
    value_date = Column(DateTime, nullable=True)
    value_date_time = Column(DateTime, nullable=True)
    transaction_amount = Column(Numeric(12, 2), nullable=False)
    transaction_currency = Column(String(3), nullable=False)
    creditor_name = Column(String(176), nullable=True)
    debtor_name = Column(String(176), nullable=True)
    end_to_end_id = Column(String(35), nullable=True)
    entry_reference = Column(String(128), nullable=True)
    additional_information = Column(String(512), nullable=True)
    additional_data_structured = Column(JSON, nullable=True)
    balance_after = Column(JSON, nullable=True)

    account = relationship("BankAccount", back_populates="transactions")


class Balance(Base):
    """Database model for account balances.

    Stores balance information for bank accounts retrieved from GoCardless API.
    Each balance record represents the account balance at a specific point in time.
    """

    __tablename__ = "balances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(
        String(128),
        ForeignKey("bank_accounts.id"),
        nullable=False,
    )
    balance_amount = Column(Numeric(12, 2), nullable=False)
    balance_currency = Column(String(3), nullable=False)
    balance_type = Column(String(50), nullable=False)
    credit_limit_included = Column(Boolean, nullable=True)
    last_change_date = Column(DateTime, nullable=True)

    account = relationship("BankAccount", back_populates="balances")


if __name__ == "__main__":
    engine = create_engine(gocardless_database_url(), echo=True, future=True)
    # session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    Base.metadata.create_all(bind=engine)
