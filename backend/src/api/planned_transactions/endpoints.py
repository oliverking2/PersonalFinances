"""Planned transactions API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
from src.api.planned_transactions.models import (
    PlannedTransactionCreateRequest,
    PlannedTransactionListResponse,
    PlannedTransactionResponse,
    PlannedTransactionSummaryResponse,
    PlannedTransactionUpdateRequest,
)
from src.api.responses import BAD_REQUEST, RESOURCE_RESPONSES, UNAUTHORIZED
from src.postgres.auth.models import User
from src.postgres.common.models import Account, PlannedTransaction
from src.postgres.common.operations.planned_transactions import (
    _NOT_SET,
    create_planned_transaction,
    delete_planned_transaction,
    get_planned_expense_total,
    get_planned_income_total,
    get_planned_transaction_by_id,
    get_planned_transactions_by_user_id,
    update_planned_transaction,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=PlannedTransactionListResponse,
    summary="List planned transactions",
    responses=UNAUTHORIZED,
)
def list_planned_transactions(
    direction: str | None = Query(None, description="Filter by direction: 'income' or 'expense'"),
    enabled_only: bool = Query(False, description="Only return enabled transactions"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlannedTransactionListResponse:
    """List all planned transactions for the authenticated user."""
    transactions = get_planned_transactions_by_user_id(
        db,
        current_user.id,
        enabled_only=enabled_only,
        direction=direction,
    )

    return PlannedTransactionListResponse(
        transactions=[_to_response(txn) for txn in transactions],
        total=len(transactions),
    )


@router.get(
    "/summary",
    response_model=PlannedTransactionSummaryResponse,
    summary="Get planned transaction summary",
    responses=UNAUTHORIZED,
)
def get_planned_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlannedTransactionSummaryResponse:
    """Get summary statistics for planned transactions."""
    transactions = get_planned_transactions_by_user_id(db, current_user.id)

    income_count = sum(1 for t in transactions if t.amount > 0)
    expense_count = sum(1 for t in transactions if t.amount < 0)

    monthly_income = get_planned_income_total(db, current_user.id)
    monthly_expenses = get_planned_expense_total(db, current_user.id)

    return PlannedTransactionSummaryResponse(
        total_planned=len(transactions),
        income_count=income_count,
        expense_count=expense_count,
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        monthly_net=monthly_income - monthly_expenses,
    )


@router.post(
    "",
    response_model=PlannedTransactionResponse,
    status_code=201,
    summary="Create planned transaction",
    responses={**UNAUTHORIZED, **BAD_REQUEST},
)
def create_planned_transaction_endpoint(
    request: PlannedTransactionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlannedTransactionResponse:
    """Create a new planned transaction for income or expense forecasting."""
    account_id = None
    if request.account_id:
        account_id = UUID(request.account_id)
        # Verify account exists and belongs to user
        account = db.get(Account, account_id)
        if not account or account.connection.user_id != current_user.id:
            raise HTTPException(status_code=404, detail=f"Account not found: {request.account_id}")

    transaction = create_planned_transaction(
        db,
        user_id=current_user.id,
        name=request.name,
        amount=request.amount,
        currency=request.currency,
        frequency=request.frequency,
        next_expected_date=request.next_expected_date,
        end_date=request.end_date,
        account_id=account_id,
        notes=request.notes,
        enabled=request.enabled,
    )

    db.commit()
    db.refresh(transaction)
    logger.info(f"Created planned transaction: id={transaction.id}, name={request.name}")
    return _to_response(transaction)


@router.get(
    "/{transaction_id}",
    response_model=PlannedTransactionResponse,
    summary="Get planned transaction by ID",
    responses=RESOURCE_RESPONSES,
)
def get_planned_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlannedTransactionResponse:
    """Retrieve a specific planned transaction by its UUID."""
    transaction = get_planned_transaction_by_id(db, transaction_id)
    if not transaction or transaction.user_id != current_user.id:
        raise HTTPException(
            status_code=404, detail=f"Planned transaction not found: {transaction_id}"
        )

    return _to_response(transaction)


@router.put(
    "/{transaction_id}",
    response_model=PlannedTransactionResponse,
    summary="Update planned transaction",
    responses={**RESOURCE_RESPONSES, **BAD_REQUEST},
)
def update_planned_transaction_endpoint(
    transaction_id: UUID,
    request: PlannedTransactionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlannedTransactionResponse:
    """Update a planned transaction's settings."""
    transaction = get_planned_transaction_by_id(db, transaction_id)
    if not transaction or transaction.user_id != current_user.id:
        raise HTTPException(
            status_code=404, detail=f"Planned transaction not found: {transaction_id}"
        )

    # Handle account_id validation if provided
    account_id = _NOT_SET
    if request.clear_account_id:
        account_id = None
    elif request.account_id:
        account_uuid = UUID(request.account_id)
        account = db.get(Account, account_uuid)
        if not account or account.connection.user_id != current_user.id:
            raise HTTPException(status_code=404, detail=f"Account not found: {request.account_id}")
        account_id = account_uuid

    # Handle nullable fields with clear flags
    frequency = _NOT_SET
    if request.clear_frequency:
        frequency = None
    elif request.frequency is not None:
        frequency = request.frequency

    end_date = _NOT_SET
    if request.clear_end_date:
        end_date = None
    elif request.end_date is not None:
        end_date = request.end_date

    notes = _NOT_SET
    if request.clear_notes:
        notes = None
    elif request.notes is not None:
        notes = request.notes

    updated = update_planned_transaction(
        db,
        transaction_id,
        name=request.name,
        amount=request.amount,
        currency=request.currency,
        frequency=frequency,
        next_expected_date=request.next_expected_date,
        end_date=end_date,
        account_id=account_id,
        notes=notes,
        enabled=request.enabled,
    )

    if not updated:
        raise HTTPException(
            status_code=404, detail=f"Planned transaction not found: {transaction_id}"
        )

    db.commit()
    db.refresh(updated)
    logger.info(f"Updated planned transaction: id={transaction_id}")
    return _to_response(updated)


@router.delete(
    "/{transaction_id}",
    status_code=204,
    summary="Delete planned transaction",
    responses=RESOURCE_RESPONSES,
)
def delete_planned_transaction_endpoint(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a planned transaction."""
    transaction = get_planned_transaction_by_id(db, transaction_id)
    if not transaction or transaction.user_id != current_user.id:
        raise HTTPException(
            status_code=404, detail=f"Planned transaction not found: {transaction_id}"
        )

    deleted = delete_planned_transaction(db, transaction_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"Planned transaction not found: {transaction_id}"
        )

    db.commit()
    logger.info(f"Deleted planned transaction: id={transaction_id}")


def _to_response(transaction: PlannedTransaction) -> PlannedTransactionResponse:
    """Convert a PlannedTransaction model to API response.

    :param transaction: Database model.
    :returns: API response model.
    """
    account_name = None
    if transaction.account:
        account_name = transaction.account.display_name or transaction.account.name

    return PlannedTransactionResponse(
        id=str(transaction.id),
        name=transaction.name,
        amount=transaction.amount,
        currency=transaction.currency,
        frequency=transaction.frequency_enum,
        next_expected_date=transaction.next_expected_date,
        end_date=transaction.end_date,
        account_id=str(transaction.account_id) if transaction.account_id else None,
        account_name=account_name,
        notes=transaction.notes,
        enabled=transaction.enabled,
        direction="income" if transaction.is_income else "expense",
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
    )
