"""Account API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.accounts.models import (
    AccountBalance,
    AccountListResponse,
    AccountResponse,
    AccountUpdateRequest,
)
from src.api.dependencies import get_current_user, get_db
from src.api.responses import RESOURCE_RESPONSES, RESOURCE_WRITE_RESPONSES
from src.postgres.auth.models import User
from src.postgres.common.enums import AccountStatus
from src.postgres.common.models import Account
from src.postgres.common.operations.accounts import (
    get_account_by_id,
    get_accounts_by_connection_id,
    update_account_display_name,
)
from src.postgres.common.operations.connections import (
    get_connection_by_id,
    get_connections_by_user_id,
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
        # Get all accounts for user's connections
        connections = get_connections_by_user_id(db, current_user.id)
        accounts = []
        for conn in connections:
            accounts.extend(get_accounts_by_connection_id(db, conn.id))

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
    account = get_account_by_id(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")

    # Verify user owns the parent connection
    if account.connection.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")

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
    account = get_account_by_id(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")

    # Verify user owns the parent connection
    if account.connection.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")

    updated = update_account_display_name(db, account_id, request.display_name)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")

    db.commit()
    db.refresh(updated)
    logger.info(f"Updated account: id={account_id}")
    return _to_response(updated)


def _to_response(account: Account) -> AccountResponse:
    """Convert an Account model to response."""
    balance = None
    if account.balance_amount is not None and account.balance_currency is not None:
        balance = AccountBalance(
            amount=float(account.balance_amount),
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
        last_synced_at=account.last_synced_at,
    )
