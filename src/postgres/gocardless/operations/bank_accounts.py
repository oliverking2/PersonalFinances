"""GoCardless Bank Account database operations."""

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from src.postgres.gocardless.models import BankAccount
from src.utils.logging import setup_dagster_logger

logger = setup_dagster_logger(__name__)


def upsert_bank_accounts(session: Session, req_id: str, accounts: list[dict[str, Any]]) -> None:
    """Upsert each BankAccount record related to a requisition.

    Iterates over account detail dictionaries, creating or updating BankAccount entries
    linked to the specified requisition.

    :param session: SQLAlchemy session for database operations
    :param req_id: The requisition ID to associate with each account.
    :param accounts: List of account detail dictionaries from GoCardless.
    :returns: None
    :raises: Exception if there's an error updating the database
    """
    logger.info(f"Upserting {len(accounts)} bank accounts for requisition ID: {req_id}")
    try:
        new_accounts = 0
        updated_accounts = 0

        for info in accounts:
            acc_id = info.get("id")
            acc = session.get(BankAccount, acc_id)
            if not acc:
                logger.debug(f"Creating new bank account record for ID: {acc_id}")
                acc = BankAccount(id=acc_id)
                session.add(acc)
                new_accounts += 1
            else:
                logger.debug(f"Updating existing bank account record for ID: {acc_id}")
                updated_accounts += 1

            # Map fields from account details
            acc.requisition_id = req_id
            acc.bban = info.get("bban")
            acc.bic = info.get("bic")
            acc.cash_account_type = info.get("cash_account_type")
            acc.currency = info.get("currency") or acc.currency
            acc.details = info.get("details")
            acc.display_name = info.get("display_name")
            acc.iban = info.get("iban")
            acc.linked_accounts = info.get("linked_accounts")
            acc.msisdn = info.get("msisdn")
            acc.name = info.get("name")
            acc.owner_address_unstructured = info.get("owner_address_unstructured")
            acc.owner_name = info.get("owner_name")
            acc.product = info.get("product")
            acc.status = info.get("status")
            acc.scan = info.get("scan")
            acc.usage = info.get("usage")

        session.commit()
        logger.info(
            f"Successfully upserted bank accounts: {new_accounts} new, {updated_accounts} updated"
        )
    except Exception as e:
        logger.error(f"Failed to upsert bank accounts for requisition ID {req_id}: {e!s}")
        raise


def get_active_accounts(session: Session) -> list[BankAccount]:
    """Get a list of active bank accounts."""
    return session.query(BankAccount).filter(BankAccount.status == "READY").all()


def get_transaction_watermark(session: Session, account_id: str) -> date | None:
    """Get the watermark for the most recent extract for a given bank account."""
    account = session.get(BankAccount, account_id)
    if account is None:
        raise ValueError(f"Bank account with ID {account_id} not found")

    return account.dg_transaction_extract_date


def update_transaction_watermark(session: Session, account_id: str, date: date) -> None:
    """Update the watermark for the most recent extract for a given bank account."""
    account = session.get(BankAccount, account_id)
    if account is None:
        raise ValueError(f"Bank account with ID {account_id} not found")

    account.dg_transaction_extract_date = date
    session.commit()
    logger.info(f"Updated watermark for bank account {account_id}: {date}")


if __name__ == "__main__":
    from src.postgres.utils import create_session
    from src.utils.definitions import gocardless_database_url

    session = create_session(gocardless_database_url())

    print(get_transaction_watermark(session, "73ed675f-12fe-4d85-88d3-d439976ec662"))
