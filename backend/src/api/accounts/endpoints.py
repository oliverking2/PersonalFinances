"""Account API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.accounts.models import AccountListResponse, AccountResponse, AccountUpdateRequest
from src.api.dependencies import get_db
from src.postgres.gocardless.models import BankAccount
from src.postgres.gocardless.operations.bank_accounts import get_active_accounts

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=AccountListResponse, summary="List all active accounts")
def list_accounts(db: Session = Depends(get_db)) -> AccountListResponse:
    """List all active bank accounts.

    :param db: Database session.
    :returns: List of active accounts.
    """
    accounts = get_active_accounts(db)
    return AccountListResponse(
        accounts=[_to_response(acc) for acc in accounts],
        total=len(accounts),
    )


@router.get("/{account_id}", response_model=AccountResponse, summary="Get account by ID")
def get_account(account_id: str, db: Session = Depends(get_db)) -> AccountResponse:
    """Get a specific account by ID.

    :param account_id: Account ID to retrieve.
    :param db: Database session.
    :returns: Account details.
    :raises HTTPException: If account not found.
    """
    account = db.get(BankAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")
    return _to_response(account)


@router.patch("/{account_id}", response_model=AccountResponse, summary="Update account")
def update_account(
    account_id: str,
    request: AccountUpdateRequest,
    db: Session = Depends(get_db),
) -> AccountResponse:
    """Update an account's details.

    :param account_id: Account ID to update.
    :param request: Update request data.
    :param db: Database session.
    :returns: Updated account.
    :raises HTTPException: If account not found.
    """
    account = db.get(BankAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")

    if request.display_name is not None:
        account.display_name = request.display_name

    db.commit()
    db.refresh(account)
    logger.info(f"Updated account: id={account_id}")
    return _to_response(account)


def _to_response(account: BankAccount) -> AccountResponse:
    """Convert a BankAccount model to response."""
    return AccountResponse(
        id=account.id,
        name=account.name,
        display_name=account.display_name,
        iban=account.iban,
        currency=account.currency,
        owner_name=account.owner_name,
        status=account.status,
        product=account.product,
        requisition_id=account.requisition_id,
        transaction_extract_date=account.dg_transaction_extract_date,
    )
