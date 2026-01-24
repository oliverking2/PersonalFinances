"""GoCardless Transaction database operations."""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from src.postgres.gocardless.models import Transaction

logger = logging.getLogger(__name__)


def _parse_date(date_str: str | None) -> date | None:
    """Parse a date string in YYYY-MM-DD format."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        logger.warning(f"Could not parse date: {date_str}")
        return None


def _parse_datetime(dt_str: str | None) -> datetime | None:
    """Parse an ISO datetime string."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except ValueError:
        logger.warning(f"Could not parse datetime: {dt_str}")
        return None


def upsert_transactions(
    session: Session, account_id: str, transactions_response: dict[str, Any]
) -> int:
    """Upsert transactions from GoCardless API response.

    Handles both booked and pending transactions. Uses account_id + transaction_id
    as the unique key for upserting.

    :param session: SQLAlchemy session.
    :param account_id: The bank account ID.
    :param transactions_response: Raw response from GoCardless transactions API.
    :returns: Number of transactions upserted.
    """
    transactions_data = transactions_response.get("transactions", {})
    booked = transactions_data.get("booked", [])
    pending = transactions_data.get("pending", [])

    count = 0
    now = datetime.now()

    # Process booked transactions
    for txn in booked:
        count += _upsert_single_transaction(session, account_id, txn, "booked", now)

    # Process pending transactions
    for txn in pending:
        count += _upsert_single_transaction(session, account_id, txn, "pending", now)

    session.flush()
    logger.info(f"Upserted {count} transactions for account {account_id}")
    return count


def _upsert_single_transaction(
    session: Session,
    account_id: str,
    txn: dict[str, Any],
    status: str,
    extracted_at: datetime,
) -> int:
    """Upsert a single transaction.

    :param session: SQLAlchemy session.
    :param account_id: The bank account ID.
    :param txn: Transaction data from API.
    :param status: Transaction status (booked/pending).
    :param extracted_at: When the extraction occurred.
    :returns: 1 if upserted, 0 if skipped.
    """
    transaction_id = txn.get("transactionId") or txn.get("internalTransactionId")
    if not transaction_id:
        logger.warning(f"Transaction missing ID, skipping: {txn}")
        return 0

    # Find existing transaction
    existing = (
        session.query(Transaction)
        .filter(
            Transaction.account_id == account_id,
            Transaction.transaction_id == transaction_id,
        )
        .first()
    )

    # Parse amount
    amount_data = txn.get("transactionAmount", {})
    amount = Decimal(amount_data.get("amount", "0"))
    currency = amount_data.get("currency", "")

    # Parse remittance info (can be string or array)
    remittance = txn.get("remittanceInformationUnstructured", "")
    if isinstance(remittance, list):
        remittance = " ".join(remittance)
    if not remittance:
        remittance_array = txn.get("remittanceInformationUnstructuredArray", [])
        if remittance_array:
            remittance = " ".join(remittance_array)

    if existing:
        # Update existing transaction
        existing.booking_date = _parse_date(txn.get("bookingDate"))
        existing.value_date = _parse_date(txn.get("valueDate"))
        existing.booking_datetime = _parse_datetime(txn.get("bookingDateTime"))
        existing.transaction_amount = amount
        existing.currency = currency
        existing.creditor_name = txn.get("creditorName")
        existing.creditor_account = txn.get("creditorAccount", {}).get("iban")
        existing.debtor_name = txn.get("debtorName")
        existing.debtor_account = txn.get("debtorAccount", {}).get("iban")
        existing.remittance_information = remittance
        existing.bank_transaction_code = txn.get("bankTransactionCode")
        existing.proprietary_bank_code = txn.get("proprietaryBankTransactionCode")
        existing.status = status
        existing.internal_transaction_id = txn.get("internalTransactionId")
        existing.extracted_at = extracted_at
    else:
        # Create new transaction
        transaction = Transaction(
            account_id=account_id,
            transaction_id=transaction_id,
            booking_date=_parse_date(txn.get("bookingDate")),
            value_date=_parse_date(txn.get("valueDate")),
            booking_datetime=_parse_datetime(txn.get("bookingDateTime")),
            transaction_amount=amount,
            currency=currency,
            creditor_name=txn.get("creditorName"),
            creditor_account=txn.get("creditorAccount", {}).get("iban")
            if isinstance(txn.get("creditorAccount"), dict)
            else None,
            debtor_name=txn.get("debtorName"),
            debtor_account=txn.get("debtorAccount", {}).get("iban")
            if isinstance(txn.get("debtorAccount"), dict)
            else None,
            remittance_information=remittance,
            bank_transaction_code=txn.get("bankTransactionCode"),
            proprietary_bank_code=txn.get("proprietaryBankTransactionCode"),
            status=status,
            internal_transaction_id=txn.get("internalTransactionId"),
            extracted_at=extracted_at,
        )
        session.add(transaction)

    return 1
