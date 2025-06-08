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
    """Base Table."""


class BankAccount(Base):
    """Bank Account table."""

    __tablename__ = "bank_accounts"
    id = Column(String(128), primary_key=True)  # resourceId :contentReference[oaicite:1]{index=1}
    bban = Column(String(128), nullable=True)  # Optional :contentReference[oaicite:2]{index=2}
    bic = Column(String(128), nullable=True)  # Optional :contentReference[oaicite:3]{index=3}
    cash_account_type = Column(
        String(50), nullable=True
    )  # Optional :contentReference[oaicite:4]{index=4}
    currency = Column(String(3), nullable=False)  # Mandatory :contentReference[oaicite:5]{index=5}
    details = Column(String(512), nullable=True)  # Optional :contentReference[oaicite:6]{index=6}
    display_name = Column(
        String(128), nullable=True
    )  # Optional :contentReference[oaicite:7]{index=7}
    iban = Column(String(34), nullable=True)  # Optional :contentReference[oaicite:8]{index=8}
    linked_accounts = Column(
        String(128), nullable=True
    )  # Optional :contentReference[oaicite:9]{index=9}
    msisdn = Column(String(64), nullable=True)  # Optional :contentReference[oaicite:10]{index=10}
    name = Column(String(128), nullable=True)  # Optional :contentReference[oaicite:11]{index=11}
    owner_address_unstructured = Column(
        String(256), nullable=True
    )  # Optional :contentReference[oaicite:12]{index=12}
    owner_name = Column(
        String(256), nullable=True
    )  # Optional :contentReference[oaicite:13]{index=13}
    product = Column(String(64), nullable=True)  # Optional :contentReference[oaicite:14]{index=14}
    status = Column(
        String(7), nullable=True
    )  # Optional (“enabled”, “deleted”, “blocked”) :contentReference[oaicite:15]{index=15}
    scan = Column(
        String(14), nullable=True
    )  # Optional, UK sort+acct :contentReference[oaicite:16]{index=16}
    usage = Column(
        String(4), nullable=True
    )  # Optional (“PRIV”, “ORGA”) :contentReference[oaicite:17]{index=17}

    # Relationships
    transactions = relationship("Transaction", back_populates="account")
    balances = relationship("Balance", back_populates="account")


class Transaction(Base):
    """Transaction Table."""

    __tablename__ = "transactions"
    id = Column(
        String(32), primary_key=True
    )  # internalTransactionId :contentReference[oaicite:19]{index=19}
    account_id = Column(String(128), ForeignKey("bank_accounts.id"), nullable=False)
    booking_date = Column(
        DateTime, nullable=True
    )  # bookingDate :contentReference[oaicite:20]{index=20}
    booking_date_time = Column(
        DateTime, nullable=True
    )  # bookingDateTime :contentReference[oaicite:21]{index=21}
    value_date = Column(
        DateTime, nullable=True
    )  # valueDate :contentReference[oaicite:22]{index=22}
    value_date_time = Column(
        DateTime, nullable=True
    )  # valueDateTime :contentReference[oaicite:23]{index=23}
    transaction_amount = Column(
        Numeric(12, 2), nullable=False
    )  # transactionAmount.amount :contentReference[oaicite:24]{index=24}
    transaction_currency = Column(
        String(3), nullable=False
    )  # transactionAmount.currency :contentReference[oaicite:25]{index=25}
    creditor_name = Column(
        String(176), nullable=True
    )  # creditorName :contentReference[oaicite:26]{index=26}
    debtor_name = Column(
        String(176), nullable=True
    )  # debtorName :contentReference[oaicite:27]{index=27}
    end_to_end_id = Column(
        String(35), nullable=True
    )  # endToEndId :contentReference[oaicite:28]{index=28}
    entry_reference = Column(
        String(128), nullable=True
    )  # entryReference :contentReference[oaicite:29]{index=29}
    additional_information = Column(
        String(512), nullable=True
    )  # additionalInformation :contentReference[oaicite:30]{index=30}
    additional_data_structured = Column(
        JSON, nullable=True
    )  # additionalDataStructured :contentReference[oaicite:31]{index=31}
    balance_after = Column(
        JSON, nullable=True
    )  # balanceAfterTransaction :contentReference[oaicite:32]{index=32}

    account = relationship("BankAccount", back_populates="transactions")


class Balance(Base):
    """Balance Table."""

    __tablename__ = "balances"
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String(128), ForeignKey("bank_accounts.id"), nullable=False)
    balance_amount = Column(
        Numeric(12, 2), nullable=False
    )  # balanceAmount.amount :contentReference[oaicite:34]{index=34}
    balance_currency = Column(
        String(3), nullable=False
    )  # balanceAmount.currency :contentReference[oaicite:35]{index=35}
    balance_type = Column(
        String(50), nullable=False
    )  # balanceType :contentReference[oaicite:36]{index=36}
    credit_limit_included = Column(
        Boolean, nullable=True
    )  # creditLimitIncluded :contentReference[oaicite:37]{index=37}
    last_change_date = Column(
        DateTime, nullable=True
    )  # lastChangeDateTime :contentReference[oaicite:38]{index=38}

    account = relationship("BankAccount", back_populates="balances")


if __name__ == "__main__":
    load_dotenv()

    DATABASE_URL = f"mysql+mysqlconnector://root:{os.getenv('MYSQL_ROOT_PASSWORD')}@localhost:3306/{os.getenv('MYSQL_GOCARDLESS_DATABASE')}"

    engine = create_engine(DATABASE_URL, echo=True, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    Base.metadata.create_all(bind=engine)
