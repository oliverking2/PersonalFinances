"""Recurring patterns API endpoints."""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
from src.api.recurring.models import (
    CreateFromTransactionsRequest,
    LinkTransactionRequest,
    PatternTransactionResponse,
    PatternTransactionsResponse,
    RecurringPatternCreateRequest,
    RecurringPatternListResponse,
    RecurringPatternResponse,
    RecurringPatternUpdateRequest,
    RecurringSummaryResponse,
    UpcomingBillResponse,
    UpcomingBillsResponse,
)
from src.api.responses import BAD_REQUEST, RESOURCE_RESPONSES, UNAUTHORIZED
from src.postgres.auth.models import User
from src.postgres.common.enums import (
    RecurringDirection,
    RecurringFrequency,
    RecurringSource,
    RecurringStatus,
)
from src.postgres.common.models import RecurringPattern, RecurringPatternTransaction
from src.postgres.common.operations.recurring_patterns import (
    accept_pattern,
    calculate_monthly_total,
    calculate_monthly_totals_by_direction,
    cancel_pattern,
    count_patterns_by_direction,
    count_patterns_by_status,
    create_pattern,
    create_pattern_from_transactions,
    delete_pattern,
    get_pattern_by_id,
    get_pattern_transactions,
    get_patterns_by_user_id,
    get_upcoming_patterns,
    link_transaction_to_pattern,
    pause_pattern,
    relink_pattern_transactions,
    resume_pattern,
    unlink_transaction_from_pattern,
    update_pattern,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# List & Summary
# =============================================================================


@router.get(
    "/patterns",
    response_model=RecurringPatternListResponse,
    summary="List recurring patterns",
    responses=UNAUTHORIZED,
)
def list_patterns(
    status: RecurringStatus | None = Query(None, description="Filter by status"),
    frequency: RecurringFrequency | None = Query(None, description="Filter by frequency"),
    source: RecurringSource | None = Query(None, description="Filter by source"),
    min_confidence: float | None = Query(
        None, ge=0.0, le=1.0, description="Minimum confidence score"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecurringPatternListResponse:
    """List all recurring patterns for the authenticated user."""
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
        source=source,
        min_confidence=min_conf_decimal,
    )

    monthly_total = calculate_monthly_total(db, current_user.id)

    return RecurringPatternListResponse(
        patterns=[_to_response(p) for p in patterns],
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
    """Get upcoming bills within the specified date range (active patterns only)."""
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
    response_model=RecurringSummaryResponse,
    summary="Get recurring pattern statistics",
    responses=UNAUTHORIZED,
)
def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecurringSummaryResponse:
    """Get summary statistics for recurring patterns."""
    monthly_totals = calculate_monthly_totals_by_direction(db, current_user.id)
    status_counts = count_patterns_by_status(db, current_user.id)
    direction_counts = count_patterns_by_direction(db, current_user.id)

    total_count = sum(status_counts.values())
    active_count = status_counts.get(RecurringStatus.ACTIVE, 0)
    pending_count = status_counts.get(RecurringStatus.PENDING, 0)
    paused_count = status_counts.get(RecurringStatus.PAUSED, 0)
    expense_count = direction_counts.get(RecurringDirection.EXPENSE, 0)
    income_count = direction_counts.get(RecurringDirection.INCOME, 0)

    return RecurringSummaryResponse(
        monthly_total=monthly_totals["net"],
        monthly_expenses=monthly_totals["expenses"],
        monthly_income=monthly_totals["income"],
        total_count=total_count,
        expense_count=expense_count,
        income_count=income_count,
        active_count=active_count,
        pending_count=pending_count,
        paused_count=paused_count,
    )


# =============================================================================
# CRUD
# =============================================================================


@router.post(
    "/patterns",
    response_model=RecurringPatternResponse,
    status_code=201,
    summary="Create pattern",
    responses={**UNAUTHORIZED, **BAD_REQUEST},
)
def create_recurring_pattern(
    request: RecurringPatternCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecurringPatternResponse:
    """Manually create a new recurring pattern."""
    anchor = (
        datetime.combine(request.anchor_date, datetime.min.time(), tzinfo=UTC)
        if request.anchor_date
        else datetime.now(UTC)
    )

    account_id = UUID(request.account_id) if request.account_id else None

    pattern = create_pattern(
        db,
        user_id=current_user.id,
        name=request.name,
        expected_amount=request.expected_amount,
        frequency=request.frequency,
        direction=request.direction,
        anchor_date=anchor,
        account_id=account_id,
        currency=request.currency,
        status=RecurringStatus.ACTIVE,
        source=RecurringSource.MANUAL,
        merchant_contains=request.merchant_contains,
        amount_tolerance_pct=request.amount_tolerance_pct,
        advanced_rules=request.advanced_rules,
        notes=request.notes,
    )

    db.commit()
    db.refresh(pattern)
    logger.info(f"Created pattern: id={pattern.id}, name={pattern.name}")
    return _to_response(pattern)


@router.post(
    "/patterns/from-transactions",
    response_model=RecurringPatternResponse,
    status_code=201,
    summary="Create pattern from transactions",
    responses={**UNAUTHORIZED, **BAD_REQUEST},
)
def create_from_transactions(
    request: CreateFromTransactionsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecurringPatternResponse:
    """Create a pattern from selected transactions."""
    transaction_ids = [UUID(tid) for tid in request.transaction_ids]

    pattern = create_pattern_from_transactions(
        db,
        user_id=current_user.id,
        transaction_ids=transaction_ids,
        name=request.name,
        frequency=request.frequency,
        merchant_contains=request.merchant_contains,
        notes=request.notes,
    )

    if not pattern:
        raise HTTPException(status_code=400, detail="Invalid transactions")

    db.commit()
    db.refresh(pattern)
    logger.info(
        f"Created pattern from transactions: id={pattern.id}, transactions={len(transaction_ids)}"
    )
    return _to_response(pattern)


@router.get(
    "/patterns/{pattern_id}",
    response_model=RecurringPatternResponse,
    summary="Get pattern by ID",
    responses=RESOURCE_RESPONSES,
)
def get_pattern(
    pattern_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecurringPatternResponse:
    """Retrieve a specific pattern by its UUID."""
    pattern = get_pattern_by_id(db, pattern_id)
    if not pattern or pattern.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

    return _to_response(pattern)


@router.put(
    "/patterns/{pattern_id}",
    response_model=RecurringPatternResponse,
    summary="Update pattern",
    responses={**RESOURCE_RESPONSES, **BAD_REQUEST},
)
def update_recurring_pattern(
    pattern_id: UUID,
    request: RecurringPatternUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecurringPatternResponse:
    """Update a pattern's details."""
    pattern = get_pattern_by_id(db, pattern_id)
    if not pattern or pattern.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

    updated = update_pattern(
        db,
        pattern_id,
        name=request.name,
        notes=request.notes,
        expected_amount=request.expected_amount,
        frequency=request.frequency,
        merchant_contains=request.merchant_contains,
        amount_tolerance_pct=request.amount_tolerance_pct,
        advanced_rules=request.advanced_rules,
    )

    if not updated:
        raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

    db.commit()
    db.refresh(updated)
    logger.info(f"Updated pattern: id={pattern_id}")
    return _to_response(updated)


@router.delete(
    "/patterns/{pattern_id}",
    status_code=204,
    summary="Delete pattern",
    responses=RESOURCE_RESPONSES,
)
def delete_recurring_pattern(
    pattern_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a pattern (can be re-detected later if dismissed pending)."""
    pattern = get_pattern_by_id(db, pattern_id)
    if not pattern or pattern.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

    deleted = delete_pattern(db, pattern_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

    db.commit()
    logger.info(f"Deleted pattern: id={pattern_id}")


# =============================================================================
# Status Transitions
# =============================================================================


@router.post(
    "/patterns/{pattern_id}/accept",
    response_model=RecurringPatternResponse,
    summary="Accept pending pattern",
    responses=RESOURCE_RESPONSES,
)
def accept_pending_pattern(
    pattern_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecurringPatternResponse:
    """Accept a pending pattern (pending -> active)."""
    pattern = get_pattern_by_id(db, pattern_id)
    if not pattern or pattern.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

    accepted = accept_pattern(db, pattern_id)
    if not accepted:
        raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

    db.commit()
    db.refresh(accepted)
    logger.info(f"Accepted pattern: id={pattern_id}")
    return _to_response(accepted)


@router.post(
    "/patterns/{pattern_id}/pause",
    response_model=RecurringPatternResponse,
    summary="Pause pattern",
    responses=RESOURCE_RESPONSES,
)
def pause_recurring_pattern(
    pattern_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecurringPatternResponse:
    """Pause a pattern (temporarily stop tracking)."""
    pattern = get_pattern_by_id(db, pattern_id)
    if not pattern or pattern.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

    paused = pause_pattern(db, pattern_id)
    if not paused:
        raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

    db.commit()
    db.refresh(paused)
    logger.info(f"Paused pattern: id={pattern_id}")
    return _to_response(paused)


@router.post(
    "/patterns/{pattern_id}/resume",
    response_model=RecurringPatternResponse,
    summary="Resume paused pattern",
    responses=RESOURCE_RESPONSES,
)
def resume_recurring_pattern(
    pattern_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecurringPatternResponse:
    """Resume a paused pattern (paused -> active)."""
    pattern = get_pattern_by_id(db, pattern_id)
    if not pattern or pattern.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

    resumed = resume_pattern(db, pattern_id)
    if not resumed:
        raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

    db.commit()
    db.refresh(resumed)
    logger.info(f"Resumed pattern: id={pattern_id}")
    return _to_response(resumed)


@router.post(
    "/patterns/{pattern_id}/cancel",
    response_model=RecurringPatternResponse,
    summary="Cancel pattern",
    responses=RESOURCE_RESPONSES,
)
def cancel_recurring_pattern(
    pattern_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecurringPatternResponse:
    """Cancel a pattern (no longer recurring)."""
    pattern = get_pattern_by_id(db, pattern_id)
    if not pattern or pattern.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

    cancelled = cancel_pattern(db, pattern_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

    db.commit()
    db.refresh(cancelled)
    logger.info(f"Cancelled pattern: id={pattern_id}")
    return _to_response(cancelled)


@router.post(
    "/patterns/{pattern_id}/relink",
    response_model=RecurringPatternResponse,
    summary="Re-run transaction matching",
    responses=RESOURCE_RESPONSES,
)
def relink_transactions(
    pattern_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecurringPatternResponse:
    """Re-run matching rules and update linked transactions."""
    pattern = get_pattern_by_id(db, pattern_id)
    if not pattern or pattern.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

    match_count = relink_pattern_transactions(db, pattern_id)

    db.commit()
    db.refresh(pattern)
    logger.info(f"Relinked pattern: id={pattern_id}, match_count={match_count}")
    return _to_response(pattern)


# =============================================================================
# Transaction Links
# =============================================================================


@router.get(
    "/patterns/{pattern_id}/transactions",
    response_model=PatternTransactionsResponse,
    summary="Get pattern transactions",
    responses=RESOURCE_RESPONSES,
)
def get_transactions_for_pattern(
    pattern_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatternTransactionsResponse:
    """Get all transactions linked to a pattern."""
    pattern = get_pattern_by_id(db, pattern_id)
    if not pattern or pattern.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

    transactions = get_pattern_transactions(db, pattern_id)

    # Get is_manual flag for each transaction
    links = (
        db.query(RecurringPatternTransaction)
        .filter(RecurringPatternTransaction.pattern_id == pattern_id)
        .all()
    )
    manual_flags = {link.transaction_id: link.is_manual for link in links}

    return PatternTransactionsResponse(
        transactions=[
            PatternTransactionResponse(
                id=str(txn.id),
                booking_date=txn.booking_date.date() if txn.booking_date else None,
                amount=float(txn.amount),
                currency=txn.currency,
                description=txn.description,
                merchant_name=txn.counterparty_name,
                is_manual=manual_flags.get(txn.id, False),
            )
            for txn in transactions
        ],
        total=len(transactions),
    )


@router.post(
    "/patterns/{pattern_id}/transactions",
    response_model=PatternTransactionsResponse,
    status_code=201,
    summary="Link transaction to pattern",
    responses={**RESOURCE_RESPONSES, **BAD_REQUEST},
)
def link_transaction(
    pattern_id: UUID,
    request: LinkTransactionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatternTransactionsResponse:
    """Manually link a transaction to a pattern."""
    pattern = get_pattern_by_id(db, pattern_id)
    if not pattern or pattern.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

    transaction_id = UUID(request.transaction_id)
    link = link_transaction_to_pattern(db, pattern_id, transaction_id, is_manual=True)

    if not link:
        raise HTTPException(status_code=400, detail="Transaction not found")

    db.commit()
    logger.info(f"Linked transaction {transaction_id} to pattern {pattern_id}")

    # Return updated transaction list
    return get_transactions_for_pattern(pattern_id, db, current_user)


@router.delete(
    "/patterns/{pattern_id}/transactions/{transaction_id}",
    status_code=204,
    summary="Unlink transaction from pattern",
    responses=RESOURCE_RESPONSES,
)
def unlink_transaction(
    pattern_id: UUID,
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Unlink a transaction from a pattern."""
    pattern = get_pattern_by_id(db, pattern_id)
    if not pattern or pattern.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

    unlinked = unlink_transaction_from_pattern(db, pattern_id, transaction_id)
    if not unlinked:
        raise HTTPException(
            status_code=404,
            detail=f"Transaction {transaction_id} not linked to pattern {pattern_id}",
        )

    db.commit()
    logger.info(f"Unlinked transaction {transaction_id} from pattern {pattern_id}")


# =============================================================================
# Helper Functions
# =============================================================================


def _to_response(pattern: RecurringPattern) -> RecurringPatternResponse:
    """Convert a RecurringPattern model to API response."""
    monthly = _to_monthly_equivalent(abs(pattern.expected_amount), pattern.frequency_enum)

    return RecurringPatternResponse(
        id=str(pattern.id),
        name=pattern.name,
        expected_amount=pattern.expected_amount,
        currency=pattern.currency,
        frequency=pattern.frequency_enum,
        direction=pattern.direction_enum,
        status=pattern.status_enum,
        source=pattern.source_enum,
        merchant_contains=pattern.merchant_contains,
        amount_tolerance_pct=pattern.amount_tolerance_pct,
        advanced_rules=pattern.advanced_rules,
        account_id=str(pattern.account_id) if pattern.account_id else None,
        next_expected_date=pattern.next_expected_date,
        last_matched_date=pattern.last_matched_date,
        end_date=pattern.end_date,
        match_count=pattern.match_count,
        monthly_equivalent=monthly,
        confidence_score=pattern.confidence_score,
        occurrence_count=pattern.occurrence_count,
        detection_reason=pattern.detection_reason,
        notes=pattern.notes,
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
        name=pattern.name,
        expected_amount=pattern.expected_amount,
        currency=pattern.currency,
        next_expected_date=pattern.next_expected_date,  # type: ignore[arg-type]
        frequency=pattern.frequency_enum,
        direction=pattern.direction_enum,
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
