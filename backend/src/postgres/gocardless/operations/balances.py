"""GoCardless Balance database operations."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from src.postgres.gocardless.models import Balance

logger = logging.getLogger(__name__)


def upsert_balances(session: Session, account_id: str, balances_response: dict[str, Any]) -> int:
    """Upsert balance records for a bank account.

    Parses the GoCardless balances API response and upserts balance records.
    Uses account_id + balance_type as the unique key for upserting.

    :param session: SQLAlchemy session.
    :param account_id: The bank account ID.
    :param balances_response: Raw response from GoCardless balances API.
    :returns: Number of balances upserted.
    """
    balances = balances_response.get("balances", [])
    if not balances:
        logger.warning(f"No balances found in response for account {account_id}")
        return 0

    count = 0
    for balance_data in balances:
        balance_amount_data = balance_data.get("balanceAmount", {})
        balance_type = balance_data.get("balanceType")

        if not balance_type:
            logger.warning(f"Balance missing balanceType for account {account_id}")
            continue

        # Find existing balance by account_id and balance_type
        existing = (
            session.query(Balance)
            .filter(
                Balance.account_id == account_id,
                Balance.balance_type == balance_type,
            )
            .first()
        )

        if existing:
            # Update existing balance
            existing.balance_amount = Decimal(balance_amount_data.get("amount", "0"))
            existing.balance_currency = balance_amount_data.get("currency", "")
            existing.credit_limit_included = balance_data.get("creditLimitIncluded")
            if balance_data.get("lastChangeDateTime"):
                existing.last_change_date = datetime.fromisoformat(
                    balance_data["lastChangeDateTime"].replace("Z", "+00:00")
                )
            logger.debug(f"Updated balance: account={account_id}, type={balance_type}")
        else:
            # Create new balance
            last_change_date = None
            if balance_data.get("lastChangeDateTime"):
                last_change_date = datetime.fromisoformat(
                    balance_data["lastChangeDateTime"].replace("Z", "+00:00")
                )

            balance = Balance(
                account_id=account_id,
                balance_amount=Decimal(balance_amount_data.get("amount", "0")),
                balance_currency=balance_amount_data.get("currency", ""),
                balance_type=balance_type,
                credit_limit_included=balance_data.get("creditLimitIncluded"),
                last_change_date=last_change_date,
            )
            session.add(balance)
            logger.debug(f"Created balance: account={account_id}, type={balance_type}")

        count += 1

    session.flush()
    logger.info(f"Upserted {count} balances for account {account_id}")
    return count
