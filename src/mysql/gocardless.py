"""Setup for the GoCardless database."""

import os

from dotenv import load_dotenv
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
from sqlalchemy.orm import relationship, sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all tables."""


class RequisitionLink(Base):
    """Requisition link table."""

    __tablename__ = "requisition_links"

    id = Column(String(36), primary_key=True)
    created = Column(DateTime, nullable=False)
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
    """Bank Account table."""

    __tablename__ = "bank_accounts"

    id = Column(String(128), primary_key=True)
    bban = Column(String(128), nullable=True)
    bic = Column(String(128), nullable=True)
    cash_account_type = Column(String(50), nullable=True)
    currency = Column(String(3), nullable=False)
    details = Column(String(512), nullable=True)
    display_name = Column(String(128), nullable=True)
    iban = Column(String(34), nullable=True)
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
    """Transaction table."""

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
    """Balance table."""

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
    load_dotenv()

    DATABASE_URL = f"mysql+mysqlconnector://root:{os.getenv('MYSQL_ROOT_PASSWORD')}@localhost:3306/{os.getenv('MYSQL_GOCARDLESS_DATABASE')}"

    engine = create_engine(DATABASE_URL, echo=True, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    Base.metadata.create_all(bind=engine)
