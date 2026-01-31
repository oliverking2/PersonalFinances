"""Subscription API endpoints."""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
from src.api.responses import BAD_REQUEST, RESOURCE_RESPONSES, UNAUTHORIZED
from src.api.subscriptions.models import (
    SubscriptionCreateRequest,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionSummaryResponse,
    SubscriptionTransactionResponse,
    SubscriptionTransactionsResponse,
    SubscriptionUpdateRequest,
    UpcomingBillResponse,
    UpcomingBillsResponse,
)
from src.postgres.auth.models import User
from src.postgres.common.enums import RecurringDirection, RecurringFrequency, RecurringStatus
from src.postgres.common.models import RecurringPattern
from src.postgres.common.operations.recurring_patterns import (
    calculate_monthly_total,
    calculate_monthly_totals_by_direction,
    confirm_pattern,
    count_patterns_by_direction,
    count_patterns_by_status,
    create_pattern,
    dismiss_pattern,
    get_pattern_by_id,
    get_pattern_transactions,
    get_patterns_by_user_id,
    get_upcoming_patterns,
    pause_pattern,
    update_pattern,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=SubscriptionListResponse,
    summary="List subscriptions",
    responses=UNAUTHORIZED,
)
def list_subscriptions(
    status: RecurringStatus | None = Query(None, description="Filter by status"),
    frequency: RecurringFrequency | None = Query(None, description="Filter by frequency"),
    min_confidence: float | None = Query(
        None, ge=0.0, le=1.0, description="Minimum confidence score"
    ),
    include_dismissed: bool = Query(False, description="Include dismissed patterns"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionListResponse:
    """List all recurring patterns/subscriptions for the authenticated user."""
    # Convert min_confidence to Decimal safely
    min_conf_decimal = None
    if min_confidence is not None:
        try:
            min_conf_decimal = Decimal(str(min_confidence))
        except (ValueError, ArithmeticError):
            raise HTTPException(status_code=400, detail="Invalid min_confidence value")

    patterns = get_patterns_by_user_id(
        db,
        current_user.id,
        status=status,
        frequency=frequency,
        min_confidence=min_conf_decimal,
        include_dismissed=include_dismissed,
    )

    monthly_total = calculate_monthly_total(db, current_user.id)

    return SubscriptionListResponse(
        subscriptions=[_to_response(p) for p in patterns],
        total=len(patterns),
        monthly_total=monthly_total,
    )


@router.get(
    "/upcoming",
    response_model=UpcomingBillsResponse,
    summary="Get upcoming bills",
    responses=UNAUTHORIZED,
)
def get_upcoming_bills(
    days: int = Query(default=7, ge=1, le=90, description="Days to look ahead"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UpcomingBillsResponse:
    """Get upcoming bills within the specified date range."""
    patterns = get_upcoming_patterns(db, current_user.id, days=days)

    now = datetime.now(UTC)
    end_date = now + timedelta(days=days)

    total_expected = sum((abs(p.expected_amount) for p in patterns), Decimal("0"))

    return UpcomingBillsResponse(
        upcoming=[_to_upcoming_response(p) for p in patterns],
        total_expected=total_expected,
        date_range={
            "start": now.date().isoformat(),
            "end": end_date.date().isoformat(),
        },
    )


@router.get(
    "/summary",
    response_model=SubscriptionSummaryResponse,
    summary="Get subscription statistics",
    responses=UNAUTHORIZED,
)
def get_subscription_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionSummaryResponse:
    """Get summary statistics for subscriptions."""
    monthly_totals = calculate_monthly_totals_by_direction(db, current_user.id)
    status_counts = count_patterns_by_status(db, current_user.id)
    direction_counts = count_patterns_by_direction(db, current_user.id)

    total_count = sum(status_counts.values())
    confirmed_count = status_counts.get(RecurringStatus.CONFIRMED, 0)
    detected_count = status_counts.get(RecurringStatus.DETECTED, 0)
    paused_count = status_counts.get(RecurringStatus.PAUSED, 0)
    expense_count = direction_counts.get(RecurringDirection.EXPENSE, 0)
    income_count = direction_counts.get(RecurringDirection.INCOME, 0)

    return SubscriptionSummaryResponse(
        monthly_total=monthly_totals["net"],
        monthly_expenses=monthly_totals["expenses"],
        monthly_income=monthly_totals["income"],
        total_count=total_count,
        expense_count=expense_count,
        income_count=income_count,
        confirmed_count=confirmed_count,
        detected_count=detected_count,
        paused_count=paused_count,
    )


@router.post(
    "",
    response_model=SubscriptionResponse,
    status_code=201,
    summary="Create subscription",
    responses={**UNAUTHORIZED, **BAD_REQUEST},
)
def create_subscription(
    request: SubscriptionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionResponse:
    """Manually create a new subscription/recurring pattern."""
    anchor = (
        datetime.combine(request.anchor_date, datetime.min.time(), tzinfo=UTC)
        if request.anchor_date
        else datetime.now(UTC)
    )

    account_id = UUID(request.account_id) if request.account_id else None

    pattern = create_pattern(
        db,
        user_id=current_user.id,
        merchant_pattern=request.merchant_pattern,
        expected_amount=request.expected_amount,
        frequency=request.frequency,
        anchor_date=anchor,
        account_id=account_id,
        currency=request.currency,
        status=RecurringStatus.MANUAL,
        display_name=request.display_name,
        notes=request.notes,
        confidence_score=Decimal("1.0"),
    )

    db.commit()
    db.refresh(pattern)
    logger.info(f"Created subscription: id={pattern.id}, merchant={pattern.merchant_pattern}")
    return _to_response(pattern)


@router.get(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Get subscription by ID",
    responses=RESOURCE_RESPONSES,
)
def get_subscription(
    subscription_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionResponse:
    """Retrieve a specific subscription by its UUID."""
    pattern = get_pattern_by_id(db, subscription_id)
    if not pattern or pattern.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Subscription not found: {subscription_id}")

    return _to_response(pattern)


@router.get(
    "/{subscription_id}/transactions",
    response_model=SubscriptionTransactionsResponse,
    summary="Get subscription transactions",
    responses=RESOURCE_RESPONSES,
)
def get_subscription_transactions(
    subscription_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionTransactionsResponse:
    """Get all transactions linked to a subscription."""
    pattern = get_pattern_by_id(db, subscription_id)
    if not pattern or pattern.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Subscription not found: {subscription_id}")

    transactions = get_pattern_transactions(db, subscription_id)

    return SubscriptionTransactionsResponse(
        transactions=[
            SubscriptionTransactionResponse(
                id=str(txn.id),
                booking_date=txn.booking_date,
                amount=float(txn.amount),
                currency=txn.currency,
                description=txn.description,
                merchant_name=txn.counterparty_name,
            )
            for txn in transactions
        ],
        total=len(transactions),
    )


@router.put(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Update subscription",
    responses={**RESOURCE_RESPONSES, **BAD_REQUEST},
)
def update_subscription(
    subscription_id: UUID,
    request: SubscriptionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionResponse:
    """Update a subscription's details or status."""
    pattern = get_pattern_by_id(db, subscription_id)
    if not pattern or pattern.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Subscription not found: {subscription_id}")

    updated = update_pattern(
        db,
        subscription_id,
        status=request.status,
        display_name=request.display_name,
        notes=request.notes,
        expected_amount=request.expected_amount,
        frequency=request.frequency,
    )

    if not updated:
        raise HTTPException(status_code=404, detail=f"Subscription not found: {subscription_id}")

    db.commit()
    db.refresh(updated)
    logger.info(f"Updated subscription: id={subscription_id}")
    return _to_response(updated)


@router.delete(
    "/{subscription_id}",
    status_code=204,
    summary="Dismiss subscription",
    responses=RESOURCE_RESPONSES,
)
def delete_subscription(
    subscription_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Dismiss a subscription (marks as not recurring/false positive)."""
    pattern = get_pattern_by_id(db, subscription_id)
    if not pattern or pattern.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Subscription not found: {subscription_id}")

    dismissed = dismiss_pattern(db, subscription_id)
    if not dismissed:
        raise HTTPException(status_code=404, detail=f"Subscription not found: {subscription_id}")

    db.commit()
    logger.info(f"Dismissed subscription: id={subscription_id}")


@router.put(
    "/{subscription_id}/confirm",
    response_model=SubscriptionResponse,
    summary="Confirm subscription",
    responses=RESOURCE_RESPONSES,
)
def confirm_subscription(
    subscription_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionResponse:
    """Confirm a detected subscription as recurring."""
    pattern = get_pattern_by_id(db, subscription_id)
    if not pattern or pattern.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Subscription not found: {subscription_id}")

    confirmed = confirm_pattern(db, subscription_id)
    if not confirmed:
        raise HTTPException(status_code=404, detail=f"Subscription not found: {subscription_id}")

    db.commit()
    db.refresh(confirmed)
    logger.info(f"Confirmed subscription: id={subscription_id}")
    return _to_response(confirmed)


@router.put(
    "/{subscription_id}/pause",
    response_model=SubscriptionResponse,
    summary="Pause subscription",
    responses=RESOURCE_RESPONSES,
)
def pause_subscription(
    subscription_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionResponse:
    """Pause a subscription (temporarily hide from upcoming bills)."""
    pattern = get_pattern_by_id(db, subscription_id)
    if not pattern or pattern.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Subscription not found: {subscription_id}")

    paused = pause_pattern(db, subscription_id)
    if not paused:
        raise HTTPException(status_code=404, detail=f"Subscription not found: {subscription_id}")

    db.commit()
    db.refresh(paused)
    logger.info(f"Paused subscription: id={subscription_id}")
    return _to_response(paused)


def _to_response(pattern: RecurringPattern) -> SubscriptionResponse:
    """Convert a RecurringPattern model to API response."""
    monthly = _to_monthly_equivalent(abs(pattern.expected_amount), pattern.frequency_enum)

    return SubscriptionResponse(
        id=str(pattern.id),
        merchant_pattern=pattern.merchant_pattern,
        display_name=pattern.display_name or pattern.merchant_pattern,
        expected_amount=pattern.expected_amount,
        currency=pattern.currency,
        frequency=pattern.frequency_enum,
        direction=pattern.direction_enum,
        status=pattern.status_enum,
        confidence_score=pattern.confidence_score,
        occurrence_count=pattern.occurrence_count,
        account_id=str(pattern.account_id) if pattern.account_id else None,
        notes=pattern.notes,
        last_occurrence_date=pattern.last_occurrence_date,
        next_expected_date=pattern.next_expected_date,
        monthly_equivalent=monthly,
        created_at=pattern.created_at,
        updated_at=pattern.updated_at,
    )


def _to_upcoming_response(pattern: RecurringPattern) -> UpcomingBillResponse:
    """Convert a RecurringPattern model to upcoming bill response."""
    now = datetime.now(UTC)
    days_until = 0
    if pattern.next_expected_date:
        delta = pattern.next_expected_date - now
        days_until = max(0, delta.days)

    return UpcomingBillResponse(
        id=str(pattern.id),
        display_name=pattern.display_name or pattern.merchant_pattern,
        merchant_pattern=pattern.merchant_pattern,
        expected_amount=pattern.expected_amount,
        currency=pattern.currency,
        next_expected_date=pattern.next_expected_date,  # type: ignore[arg-type]
        frequency=pattern.frequency_enum,
        direction=pattern.direction_enum,
        confidence_score=pattern.confidence_score,
        status=pattern.status_enum,
        days_until=days_until,
    )


def _to_monthly_equivalent(amount: Decimal, frequency: RecurringFrequency) -> Decimal:
    """Convert amount to monthly equivalent."""
    multipliers = {
        RecurringFrequency.WEEKLY: Decimal("4.33"),
        RecurringFrequency.FORTNIGHTLY: Decimal("2.17"),
        RecurringFrequency.MONTHLY: Decimal("1"),
        RecurringFrequency.QUARTERLY: Decimal("1") / Decimal("3"),
        RecurringFrequency.ANNUAL: Decimal("1") / Decimal("12"),
        RecurringFrequency.IRREGULAR: Decimal("1"),
    }
    return amount * multipliers.get(frequency, Decimal("1"))
