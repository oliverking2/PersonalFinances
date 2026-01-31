"""Account API endpoints."""

import logging
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.accounts.models import (
    AccountBalance,
    AccountListResponse,
    AccountResponse,
    AccountUpdateRequest,
)
from src.api.common.helpers import verify_user_owns_account
from src.api.dependencies import get_current_user, get_db
from src.api.responses import RESOURCE_RESPONSES, RESOURCE_WRITE_RESPONSES
from src.postgres.auth.models import User
from src.postgres.common.enums import AccountCategory, AccountStatus
from src.postgres.common.models import Account
from src.postgres.common.operations.accounts import (
    get_accounts_by_connection_id,
    update_account,
)
from src.postgres.common.operations.connections import (
    get_accounts_by_user_id,
    get_connection_by_id,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=AccountListResponse,
    summary="List accounts",
    responses=RESOURCE_RESPONSES,
)
def list_accounts(
    connection_id: UUID | None = Query(None, description="Filter by connection ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountListResponse:
    """List all bank accounts for the authenticated user."""
    if connection_id:
        # Verify user owns this connection
        connection = get_connection_by_id(db, connection_id)
        if not connection or connection.user_id != current_user.id:
            raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")
        accounts = get_accounts_by_connection_id(db, connection_id)
    else:
        # Get all accounts for user using eager loading (single query)
        accounts = get_accounts_by_user_id(db, current_user.id)

    return AccountListResponse(
        accounts=[_to_response(acc) for acc in accounts],
        total=len(accounts),
    )


@router.get(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Get account by ID",
    responses=RESOURCE_RESPONSES,
)
def get_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountResponse:
    """Retrieve a specific bank account by its UUID."""
    account = verify_user_owns_account(db, account_id, current_user)
    return _to_response(account)


@router.patch(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Update account",
    responses=RESOURCE_WRITE_RESPONSES,
)
def patch_account(
    account_id: UUID,
    request: AccountUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountResponse:
    """Update an account's display name, category, or minimum balance."""
    # Verify ownership (raises 404 if not found or not owned)
    verify_user_owns_account(db, account_id, current_user)

    # Check which fields were explicitly provided in the request
    # This allows us to differentiate between "not provided" and "explicitly set to null"
    fields_set = request.model_fields_set

    # Parse category if provided
    category = None
    clear_category = False
    if "category" in fields_set:
        if request.category is not None:
            try:
                category = AccountCategory(request.category)
            except ValueError:
                valid_values = [c.value for c in AccountCategory]
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid category: {request.category}. Must be one of: {valid_values}",
                )
        else:
            clear_category = True

    # Convert min_balance to Decimal if provided
    min_balance = None
    clear_min_balance = False
    if "min_balance" in fields_set:
        if request.min_balance is not None:
            min_balance = Decimal(str(request.min_balance))
        else:
            clear_min_balance = True

    # Convert credit_limit to Decimal if provided
    credit_limit = None
    clear_credit_limit = False
    if "credit_limit" in fields_set:
        if request.credit_limit is not None:
            credit_limit = Decimal(str(request.credit_limit))
        else:
            clear_credit_limit = True

    # Handle display_name
    display_name = request.display_name if "display_name" in fields_set else None
    clear_display_name = "display_name" in fields_set and request.display_name is None

    updated = update_account(
        db,
        account_id,
        display_name=display_name,
        category=category,
        min_balance=min_balance,
        credit_limit=credit_limit,
        clear_display_name=clear_display_name,
        clear_category=clear_category,
        clear_min_balance=clear_min_balance,
        clear_credit_limit=clear_credit_limit,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")

    db.commit()
    db.refresh(updated)
    logger.info(f"Updated account: id={account_id}")
    return _to_response(updated)


def _normalize_credit_card_balance(
    balance_amount: float,
    credit_limit: float | None,
) -> float:
    """Normalize credit card balance to always represent amount owed.

    Different banks report credit card balances differently:
    - Some report negative values (amount owed, e.g., Amex)
    - Some report positive values (available credit, e.g., Nationwide)

    This function normalizes to: positive = amount owed, zero/negative = credit available.

    :param balance_amount: Raw balance from bank.
    :param credit_limit: User-configured credit limit.
    :returns: Normalized balance (positive = owed).
    """
    if credit_limit is None:
        # No credit limit set, can't normalize - return absolute value as "owed"
        return abs(balance_amount)

    if balance_amount <= 0:
        # Negative or zero balance = amount owed (Amex style)
        return abs(balance_amount)

    # Positive balance = available credit (Nationwide style)
    # Amount owed = credit_limit - available
    return max(0, credit_limit - balance_amount)


def _to_response(account: Account) -> AccountResponse:
    """Convert an Account model to response."""
    balance = None
    if account.balance_amount is not None and account.balance_currency is not None:
        amount = float(account.balance_amount)

        # Normalize credit card balances to always show "amount owed"
        if account.category == AccountCategory.CREDIT_CARD.value:
            credit_limit = float(account.credit_limit) if account.credit_limit is not None else None
            amount = _normalize_credit_card_balance(amount, credit_limit)

        balance = AccountBalance(
            amount=amount,
            currency=account.balance_currency,
            type=account.balance_type or "unknown",
        )

    return AccountResponse(
        id=str(account.id),
        connection_id=str(account.connection_id),
        display_name=account.display_name,
        name=account.name,
        iban=account.iban,
        currency=account.currency,
        status=AccountStatus(account.status),
        balance=balance,
        category=account.category,
        min_balance=float(account.min_balance) if account.min_balance is not None else None,
        credit_limit=float(account.credit_limit) if account.credit_limit is not None else None,
        last_synced_at=account.last_synced_at,
    )
