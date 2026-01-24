"""Transaction API endpoints."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
from src.api.transactions.models import (
    TransactionListResponse,
    TransactionQueryParams,
    TransactionResponse,
)
from src.postgres.auth.models import User
from src.postgres.common.models import Transaction
from src.postgres.common.operations.connections import get_connections_by_user_id
from src.postgres.common.operations.transactions import get_transactions_for_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=TransactionListResponse, summary="List transactions")
def list_transactions(
    params: TransactionQueryParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionListResponse:
    """List transactions with optional filters.

    Returns transactions for all accounts belonging to the authenticated user.
    Can be filtered by account_id, date range, amount range, and search term.

    :param params: Query parameters for filtering.
    :param db: Database session.
    :param current_user: Authenticated user.
    :returns: Paginated list of transactions.
    """
    # Get all account IDs for this user
    connections = get_connections_by_user_id(db, current_user.id)
    account_ids = [acc.id for conn in connections for acc in conn.accounts]

    # If filtering by specific account, verify user owns it
    if params.account_id is not None:
        if params.account_id not in account_ids:
            # Return empty result for accounts user doesn't own
            return TransactionListResponse(
                transactions=[],
                total=0,
                page=params.page,
                page_size=params.page_size,
            )
        # Filter to just the requested account
        account_ids = [params.account_id]

    # Query transactions
    result = get_transactions_for_user(
        db,
        account_ids=account_ids,
        start_date=params.start_date,
        end_date=params.end_date,
        min_amount=params.min_amount,
        max_amount=params.max_amount,
        search=params.search,
        page=params.page,
        page_size=params.page_size,
    )

    return TransactionListResponse(
        transactions=[_to_response(txn) for txn in result.transactions],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


def _to_response(txn: Transaction) -> TransactionResponse:
    """Convert a Transaction model to API response."""
    return TransactionResponse(
        id=str(txn.id),
        account_id=str(txn.account_id),
        booking_date=txn.booking_date.date() if txn.booking_date else None,
        value_date=txn.value_date.date() if txn.value_date else None,
        amount=txn.amount,
        currency=txn.currency,
        description=txn.description,
        merchant_name=txn.counterparty_name,
        category=txn.category,
    )
