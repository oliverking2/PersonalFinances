"""Budget API endpoints."""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.api.budgets.models import (
    BudgetCreateRequest,
    BudgetListResponse,
    BudgetResponse,
    BudgetSummaryResponse,
    BudgetUpdateRequest,
    BudgetWithSpendingResponse,
)
from src.api.dependencies import get_current_user, get_db
from src.api.responses import BAD_REQUEST, RESOURCE_RESPONSES, UNAUTHORIZED
from src.postgres.auth.models import User
from src.postgres.common.models import Budget, Tag, Transaction, TransactionSplit
from src.postgres.common.operations.budgets import (
    create_budget,
    delete_budget,
    get_budget_by_id,
    get_budget_by_tag,
    get_budgets_by_user_id,
    update_budget,
)

logger = logging.getLogger(__name__)

# Threshold for determining exceeded budget (100%)
EXCEEDED_THRESHOLD = 100

router = APIRouter()


@router.get(
    "",
    response_model=BudgetListResponse,
    summary="List budgets",
    responses=UNAUTHORIZED,
)
def list_budgets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BudgetListResponse:
    """List all budgets for the authenticated user with current spending."""
    budgets = get_budgets_by_user_id(db, current_user.id)

    # Calculate spending for each budget
    budget_responses = []
    for budget in budgets:
        spent = _calculate_budget_spending(db, budget, current_user.id)
        budget_responses.append(_to_response_with_spending(budget, spent))

    return BudgetListResponse(
        budgets=budget_responses,
        total=len(budget_responses),
    )


@router.get(
    "/summary",
    response_model=BudgetSummaryResponse,
    summary="Get budget summary",
    responses=UNAUTHORIZED,
)
def get_budget_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BudgetSummaryResponse:
    """Get summary statistics for all budgets."""
    budgets = get_budgets_by_user_id(db, current_user.id)

    total_budgeted = Decimal("0")
    total_spent = Decimal("0")
    active_budgets = 0
    on_track = 0
    warning = 0
    exceeded = 0

    for budget in budgets:
        if budget.enabled:
            active_budgets += 1
            total_budgeted += budget.amount
            spent = _calculate_budget_spending(db, budget, current_user.id)
            total_spent += spent

            percentage = (spent / budget.amount * 100) if budget.amount > 0 else Decimal("0")
            if percentage >= EXCEEDED_THRESHOLD:
                exceeded += 1
            elif percentage >= budget.warning_threshold * 100:
                warning += 1
            else:
                on_track += 1

    return BudgetSummaryResponse(
        total_budgets=len(budgets),
        active_budgets=active_budgets,
        total_budgeted=total_budgeted,
        total_spent=total_spent,
        budgets_on_track=on_track,
        budgets_warning=warning,
        budgets_exceeded=exceeded,
    )


@router.post(
    "",
    response_model=BudgetResponse,
    status_code=201,
    summary="Create budget",
    responses={**UNAUTHORIZED, **BAD_REQUEST},
)
def create_budget_endpoint(
    request: BudgetCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BudgetResponse:
    """Create a new budget for a tag category."""
    tag_id = UUID(request.tag_id)

    # Verify tag exists and belongs to user
    tag = db.get(Tag, tag_id)
    if not tag or tag.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Tag not found: {request.tag_id}")

    # Check for existing budget on this tag
    existing = get_budget_by_tag(db, current_user.id, tag_id)
    if existing:
        raise HTTPException(status_code=400, detail=f"Budget already exists for tag: {tag.name}")

    budget = create_budget(
        db,
        user_id=current_user.id,
        tag_id=tag_id,
        amount=request.amount,
        currency=request.currency,
        warning_threshold=request.warning_threshold,
    )

    db.commit()
    db.refresh(budget)
    logger.info(f"Created budget: id={budget.id}, tag={tag.name}")
    return _to_response(budget)


@router.get(
    "/{budget_id}",
    response_model=BudgetWithSpendingResponse,
    summary="Get budget by ID",
    responses=RESOURCE_RESPONSES,
)
def get_budget(
    budget_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BudgetWithSpendingResponse:
    """Retrieve a specific budget by its UUID."""
    budget = get_budget_by_id(db, budget_id)
    if not budget or budget.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Budget not found: {budget_id}")

    spent = _calculate_budget_spending(db, budget, current_user.id)
    return _to_response_with_spending(budget, spent)


@router.put(
    "/{budget_id}",
    response_model=BudgetResponse,
    summary="Update budget",
    responses={**RESOURCE_RESPONSES, **BAD_REQUEST},
)
def update_budget_endpoint(
    budget_id: UUID,
    request: BudgetUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BudgetResponse:
    """Update a budget's settings."""
    budget = get_budget_by_id(db, budget_id)
    if not budget or budget.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Budget not found: {budget_id}")

    updated = update_budget(
        db,
        budget_id,
        amount=request.amount,
        currency=request.currency,
        warning_threshold=request.warning_threshold,
        enabled=request.enabled,
    )

    if not updated:
        raise HTTPException(status_code=404, detail=f"Budget not found: {budget_id}")

    db.commit()
    db.refresh(updated)
    logger.info(f"Updated budget: id={budget_id}")
    return _to_response(updated)


@router.delete(
    "/{budget_id}",
    status_code=204,
    summary="Delete budget",
    responses=RESOURCE_RESPONSES,
)
def delete_budget_endpoint(
    budget_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a budget."""
    budget = get_budget_by_id(db, budget_id)
    if not budget or budget.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Budget not found: {budget_id}")

    deleted = delete_budget(db, budget_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Budget not found: {budget_id}")

    db.commit()
    logger.info(f"Deleted budget: id={budget_id}")


def _calculate_budget_spending(
    db: Session,
    budget: Budget,
    user_id: UUID,
) -> Decimal:
    """Calculate total spending for a budget in the current period.

    :param db: Database session.
    :param budget: Budget entity.
    :param user_id: User's UUID.
    :return: Total spent amount for the budget's tag in current period.
    """
    # Get current month's date range
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Query spending from transaction splits for this tag in current month
    # Spending is recorded as positive amounts in splits (absolute value)
    result = (
        db.query(func.coalesce(func.sum(TransactionSplit.amount), 0))
        .join(Transaction, TransactionSplit.transaction_id == Transaction.id)
        .filter(
            TransactionSplit.tag_id == budget.tag_id,
            Transaction.booking_date >= month_start,
            Transaction.amount < 0,  # Only spending transactions
        )
        .scalar()
    )

    return Decimal(str(result)) if result else Decimal("0")


def _to_response(budget: Budget) -> BudgetResponse:
    """Convert a Budget model to API response.

    :param budget: Database model.
    :return: API response model.
    """
    return BudgetResponse(
        id=str(budget.id),
        tag_id=str(budget.tag_id),
        tag_name=budget.tag.name if budget.tag else "Unknown",
        tag_colour=budget.tag.colour if budget.tag else None,
        amount=budget.amount,
        currency=budget.currency,
        period=budget.period_enum,
        warning_threshold=budget.warning_threshold,
        enabled=budget.enabled,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
    )


def _to_response_with_spending(
    budget: Budget,
    spent_amount: Decimal,
) -> BudgetWithSpendingResponse:
    """Convert a Budget model to API response with spending data.

    :param budget: Database model.
    :param spent_amount: Amount spent in current period.
    :return: API response model with spending.
    """
    remaining = budget.amount - spent_amount
    percentage = (spent_amount / budget.amount * 100) if budget.amount > 0 else Decimal("0")

    if percentage >= EXCEEDED_THRESHOLD:
        status = "exceeded"
    elif percentage >= budget.warning_threshold * 100:
        status = "warning"
    else:
        status = "ok"

    return BudgetWithSpendingResponse(
        id=str(budget.id),
        tag_id=str(budget.tag_id),
        tag_name=budget.tag.name if budget.tag else "Unknown",
        tag_colour=budget.tag.colour if budget.tag else None,
        amount=budget.amount,
        currency=budget.currency,
        period=budget.period_enum,
        warning_threshold=budget.warning_threshold,
        enabled=budget.enabled,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
        spent_amount=spent_amount,
        remaining_amount=remaining,
        percentage_used=percentage,
        status=status,
    )
