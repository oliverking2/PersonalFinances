"""Goals API endpoints."""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
from src.api.goals.models import (
    ContributeRequest,
    GoalCreateRequest,
    GoalListResponse,
    GoalResponse,
    GoalSummaryResponse,
    GoalUpdateRequest,
)
from src.api.responses import BAD_REQUEST, RESOURCE_RESPONSES, UNAUTHORIZED
from src.postgres.auth.models import User
from src.postgres.common.enums import GoalStatus, GoalTrackingMode
from src.postgres.common.models import Account, Connection, SavingsGoal
from src.postgres.common.operations.goals import (
    ContributionNotAllowedError,
    cancel_goal,
    complete_goal,
    contribute_to_goal,
    create_goal,
    delete_goal,
    get_goal_by_id,
    get_goals_by_user_id,
    pause_goal,
    resume_goal,
    update_goal,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=GoalListResponse,
    summary="List goals",
    responses=UNAUTHORIZED,
)
def list_goals(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalListResponse:
    """List all savings goals for the authenticated user."""
    goals = get_goals_by_user_id(db, current_user.id, include_inactive=include_inactive)

    return GoalListResponse(
        goals=[_to_response(g, db) for g in goals],
        total=len(goals),
    )


@router.get(
    "/summary",
    response_model=GoalSummaryResponse,
    summary="Get goals summary",
    responses=UNAUTHORIZED,
)
def get_goals_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalSummaryResponse:
    """Get summary statistics for all goals."""
    goals = get_goals_by_user_id(db, current_user.id, include_inactive=True)

    total_target = Decimal("0")
    total_saved = Decimal("0")
    active_count = 0
    completed_count = 0

    for goal in goals:
        total_target += goal.target_amount
        # Use calculated current amount based on tracking mode
        total_saved += _calculate_current_amount(goal, db)

        if goal.status_enum == GoalStatus.ACTIVE:
            active_count += 1
        elif goal.status_enum == GoalStatus.COMPLETED:
            completed_count += 1

    overall_progress = (total_saved / total_target * 100) if total_target > 0 else Decimal("0")

    return GoalSummaryResponse(
        total_goals=len(goals),
        active_goals=active_count,
        completed_goals=completed_count,
        total_target=total_target,
        total_saved=total_saved,
        overall_progress=overall_progress,
    )


@router.post(
    "",
    response_model=GoalResponse,
    status_code=201,
    summary="Create goal",
    responses={**UNAUTHORIZED, **BAD_REQUEST},
)
def create_goal_endpoint(
    request: GoalCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalResponse:
    """Create a new savings goal."""
    account_id = None
    if request.account_id:
        account_id = UUID(request.account_id)
        # Verify account exists and belongs to user
        account = db.get(Account, account_id)
        if not account:
            raise HTTPException(status_code=404, detail=f"Account not found: {request.account_id}")
        # Check account belongs to user through connection
        connection = db.get(Connection, account.connection_id)
        if not connection or connection.user_id != current_user.id:
            raise HTTPException(status_code=404, detail=f"Account not found: {request.account_id}")

    deadline = None
    if request.deadline:
        deadline = datetime.combine(request.deadline, datetime.min.time(), tzinfo=UTC)

    try:
        goal = create_goal(
            db,
            user_id=current_user.id,
            name=request.name,
            target_amount=request.target_amount,
            current_amount=request.current_amount,
            currency=request.currency,
            deadline=deadline,
            account_id=account_id,
            tracking_mode=request.tracking_mode,
            target_balance=request.target_balance,
            notes=request.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db.commit()
    db.refresh(goal)
    logger.info(f"Created goal: id={goal.id}, name={goal.name}, mode={goal.tracking_mode}")
    return _to_response(goal, db)


@router.get(
    "/{goal_id}",
    response_model=GoalResponse,
    summary="Get goal by ID",
    responses=RESOURCE_RESPONSES,
)
def get_goal(
    goal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalResponse:
    """Retrieve a specific goal by its UUID."""
    goal = get_goal_by_id(db, goal_id)
    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    return _to_response(goal, db)


@router.put(
    "/{goal_id}",
    response_model=GoalResponse,
    summary="Update goal",
    responses={**RESOURCE_RESPONSES, **BAD_REQUEST},
)
def update_goal_endpoint(
    goal_id: UUID,
    request: GoalUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalResponse:
    """Update a goal's details."""
    goal = get_goal_by_id(db, goal_id)
    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    # Handle deadline
    deadline = goal.deadline  # Keep existing by default
    if request.clear_deadline:
        deadline = None
    elif request.deadline:
        deadline = datetime.combine(request.deadline, datetime.min.time(), tzinfo=UTC)

    # Handle account_id
    account_id = goal.account_id  # Keep existing by default
    if request.clear_account:
        account_id = None
    elif request.account_id:
        account_id = UUID(request.account_id)
        # Verify account exists and belongs to user
        account = db.get(Account, account_id)
        if not account:
            raise HTTPException(status_code=404, detail=f"Account not found: {request.account_id}")
        connection = db.get(Connection, account.connection_id)
        if not connection or connection.user_id != current_user.id:
            raise HTTPException(status_code=404, detail=f"Account not found: {request.account_id}")

    # Handle notes
    notes = goal.notes  # Keep existing by default
    if request.clear_notes:
        notes = None
    elif request.notes is not None:
        notes = request.notes

    updated = update_goal(
        db,
        goal_id,
        name=request.name,
        target_amount=request.target_amount,
        current_amount=request.current_amount,
        deadline=deadline,
        account_id=account_id,
        notes=notes,
    )

    if not updated:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    db.commit()
    db.refresh(updated)
    logger.info(f"Updated goal: id={goal_id}")
    return _to_response(updated, db)


@router.post(
    "/{goal_id}/contribute",
    response_model=GoalResponse,
    summary="Contribute to goal",
    responses={**RESOURCE_RESPONSES, **BAD_REQUEST},
)
def contribute_to_goal_endpoint(
    goal_id: UUID,
    request: ContributeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalResponse:
    """Add a contribution to a savings goal (manual tracking mode only)."""
    goal = get_goal_by_id(db, goal_id)
    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    if goal.status_enum != GoalStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot contribute to {goal.status} goal",
        )

    try:
        updated = contribute_to_goal(db, goal_id, request.amount)
    except ContributionNotAllowedError:
        raise HTTPException(
            status_code=400,
            detail="Contributions only allowed for manual tracking mode",
        )

    if not updated:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    db.commit()
    db.refresh(updated)
    logger.info(f"Contributed to goal: id={goal_id}, amount={request.amount}")
    return _to_response(updated, db)


@router.put(
    "/{goal_id}/complete",
    response_model=GoalResponse,
    summary="Mark goal complete",
    responses=RESOURCE_RESPONSES,
)
def complete_goal_endpoint(
    goal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalResponse:
    """Mark a savings goal as completed."""
    goal = get_goal_by_id(db, goal_id)
    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    completed = complete_goal(db, goal_id)
    if not completed:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    db.commit()
    db.refresh(completed)
    logger.info(f"Completed goal: id={goal_id}")
    return _to_response(completed, db)


@router.put(
    "/{goal_id}/pause",
    response_model=GoalResponse,
    summary="Pause goal",
    responses=RESOURCE_RESPONSES,
)
def pause_goal_endpoint(
    goal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalResponse:
    """Pause a savings goal."""
    goal = get_goal_by_id(db, goal_id)
    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    paused = pause_goal(db, goal_id)
    if not paused:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    db.commit()
    db.refresh(paused)
    logger.info(f"Paused goal: id={goal_id}")
    return _to_response(paused, db)


@router.put(
    "/{goal_id}/resume",
    response_model=GoalResponse,
    summary="Resume goal",
    responses=RESOURCE_RESPONSES,
)
def resume_goal_endpoint(
    goal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalResponse:
    """Resume a paused savings goal."""
    goal = get_goal_by_id(db, goal_id)
    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    resumed = resume_goal(db, goal_id)
    if not resumed:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    db.commit()
    db.refresh(resumed)
    logger.info(f"Resumed goal: id={goal_id}")
    return _to_response(resumed, db)


@router.put(
    "/{goal_id}/cancel",
    response_model=GoalResponse,
    summary="Cancel goal",
    responses=RESOURCE_RESPONSES,
)
def cancel_goal_endpoint(
    goal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalResponse:
    """Cancel a savings goal."""
    goal = get_goal_by_id(db, goal_id)
    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    cancelled = cancel_goal(db, goal_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    db.commit()
    db.refresh(cancelled)
    logger.info(f"Cancelled goal: id={goal_id}")
    return _to_response(cancelled, db)


@router.delete(
    "/{goal_id}",
    status_code=204,
    summary="Delete goal",
    responses=RESOURCE_RESPONSES,
)
def delete_goal_endpoint(
    goal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a savings goal."""
    goal = get_goal_by_id(db, goal_id)
    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    deleted = delete_goal(db, goal_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    db.commit()
    logger.info(f"Deleted goal: id={goal_id}")


def _calculate_current_amount(goal: SavingsGoal, db: Session) -> Decimal:
    """Calculate current amount based on tracking mode.

    :param goal: SavingsGoal model.
    :param db: Database session for fetching account balance.
    :return: Calculated current amount.
    """
    # Manual mode: use stored value directly
    if goal.tracking_mode_enum == GoalTrackingMode.MANUAL:
        return goal.current_amount

    # Non-manual modes require an account with a balance
    if not goal.account_id:
        return Decimal("0")

    account = db.get(Account, goal.account_id)
    if not account:
        return Decimal("0")

    balance = account.balance_amount or Decimal("0")

    # Balance mode: mirror account balance directly
    # Target balance mode: show current balance (progress is towards target_balance)
    if goal.tracking_mode_enum in (GoalTrackingMode.BALANCE, GoalTrackingMode.TARGET_BALANCE):
        return balance

    # Delta mode: progress = current balance - starting balance
    if goal.tracking_mode_enum == GoalTrackingMode.DELTA:
        starting = goal.starting_balance or Decimal("0")
        return balance - starting

    # Fallback to stored value
    return goal.current_amount


def _calculate_progress(goal: SavingsGoal, current_amount: Decimal) -> Decimal:
    """Calculate progress percentage based on tracking mode.

    :param goal: SavingsGoal model.
    :param current_amount: The calculated current amount.
    :return: Progress percentage (0-100+).
    """
    if goal.tracking_mode_enum == GoalTrackingMode.TARGET_BALANCE:
        # Progress towards target_balance
        target = goal.target_balance or goal.target_amount
        if target <= 0:
            return Decimal("0")
        return current_amount / target * 100
    # Progress towards target_amount
    if goal.target_amount <= 0:
        return Decimal("0")
    return current_amount / goal.target_amount * 100


def _to_response(goal: SavingsGoal, db: Session) -> GoalResponse:
    """Convert a SavingsGoal model to API response.

    :param goal: Database model.
    :param db: Database session for calculating current amount.
    :return: API response model.
    """
    current_amount = _calculate_current_amount(goal, db)
    progress = _calculate_progress(goal, current_amount)

    days_remaining = None
    if goal.deadline:
        now = datetime.now(UTC)
        deadline = goal.deadline
        # Ensure deadline is timezone-aware for comparison
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=UTC)
        delta = deadline - now
        days_remaining = max(0, delta.days)

    return GoalResponse(
        id=str(goal.id),
        name=goal.name,
        target_amount=goal.target_amount,
        current_amount=current_amount,
        currency=goal.currency,
        deadline=goal.deadline,
        account_id=str(goal.account_id) if goal.account_id else None,
        account_name=goal.account.display_name if goal.account else None,
        tracking_mode=goal.tracking_mode_enum,
        starting_balance=goal.starting_balance,
        target_balance=goal.target_balance,
        status=goal.status_enum,
        notes=goal.notes,
        progress_percentage=progress,
        days_remaining=days_remaining,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )
