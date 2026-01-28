"""Savings goal database operations.

This module provides CRUD operations for SavingsGoal entities.
"""

import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from src.postgres.common.enums import GoalStatus, GoalTrackingMode
from src.postgres.common.models import Account, SavingsGoal

logger = logging.getLogger(__name__)


def get_goal_by_id(session: Session, goal_id: UUID) -> SavingsGoal | None:
    """Get a savings goal by its ID.

    :param session: SQLAlchemy session.
    :param goal_id: Goal's UUID.
    :return: SavingsGoal if found, None otherwise.
    """
    return session.get(SavingsGoal, goal_id)


def get_goals_by_user_id(
    session: Session,
    user_id: UUID,
    *,
    status: GoalStatus | None = None,
    include_inactive: bool = False,
) -> list[SavingsGoal]:
    """Get all savings goals for a user.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param status: Filter by specific status.
    :param include_inactive: Include completed and cancelled goals.
    :return: List of goals ordered by deadline (nulls last) then target amount.
    """
    query = session.query(SavingsGoal).filter(SavingsGoal.user_id == user_id)

    if status is not None:
        query = query.filter(SavingsGoal.status == status.value)
    elif not include_inactive:
        query = query.filter(
            SavingsGoal.status.in_([GoalStatus.ACTIVE.value, GoalStatus.PAUSED.value])
        )

    # Order by deadline (nulls last), then by target amount descending
    return query.order_by(
        SavingsGoal.deadline.is_(None),
        SavingsGoal.deadline,
        SavingsGoal.target_amount.desc(),
    ).all()


def create_goal(
    session: Session,
    user_id: UUID,
    name: str,
    target_amount: Decimal,
    *,
    current_amount: Decimal = Decimal("0"),
    currency: str = "GBP",
    deadline: datetime | None = None,
    account_id: UUID | None = None,
    tracking_mode: GoalTrackingMode = GoalTrackingMode.MANUAL,
    target_balance: Decimal | None = None,
    notes: str | None = None,
) -> SavingsGoal:
    """Create a new savings goal.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param name: Goal name.
    :param target_amount: Target savings amount.
    :param current_amount: Starting amount (default 0, used for manual mode).
    :param currency: Currency code (default GBP).
    :param deadline: Optional target date.
    :param account_id: Optional account to link for automatic tracking.
    :param tracking_mode: How progress is tracked (manual, balance, delta, target_balance).
    :param target_balance: Target account balance for target_balance mode.
    :param notes: Optional user notes.
    :return: Created SavingsGoal entity.
    :raises ValueError: If tracking mode requirements are not met.
    """
    # Validate tracking mode requirements
    if tracking_mode != GoalTrackingMode.MANUAL and account_id is None:
        raise ValueError(f"Account is required for {tracking_mode.value} tracking mode")

    if tracking_mode == GoalTrackingMode.TARGET_BALANCE and target_balance is None:
        raise ValueError("Target balance is required for target_balance tracking mode")

    # For delta mode, snapshot the current account balance as starting_balance
    starting_balance: Decimal | None = None
    if tracking_mode == GoalTrackingMode.DELTA and account_id is not None:
        account = session.get(Account, account_id)
        if account:
            starting_balance = account.balance_amount or Decimal("0")

    goal = SavingsGoal(
        user_id=user_id,
        name=name[:100],
        target_amount=target_amount,
        current_amount=current_amount,
        currency=currency,
        deadline=deadline,
        account_id=account_id,
        tracking_mode=tracking_mode.value,
        starting_balance=starting_balance,
        target_balance=target_balance,
        status=GoalStatus.ACTIVE.value,
        notes=notes,
    )
    session.add(goal)
    session.flush()

    logger.info(
        f"Created savings goal: id={goal.id}, user_id={user_id}, "
        f"name={name}, mode={tracking_mode.value}"
    )
    return goal


_NOT_SET = object()


def update_goal(
    session: Session,
    goal_id: UUID,
    *,
    name: str | None = None,
    target_amount: Decimal | None = None,
    current_amount: Decimal | None = None,
    deadline: datetime | None | object = _NOT_SET,
    account_id: UUID | None | object = _NOT_SET,
    notes: str | None | object = _NOT_SET,
) -> SavingsGoal | None:
    """Update a savings goal.

    :param session: SQLAlchemy session.
    :param goal_id: Goal's UUID.
    :param name: New goal name.
    :param target_amount: New target amount.
    :param current_amount: New current amount.
    :param deadline: New deadline (pass None to clear).
    :param account_id: New account link (pass None to clear).
    :param notes: New notes (pass None to clear).
    :return: Updated SavingsGoal, or None if not found.
    """
    goal = get_goal_by_id(session, goal_id)
    if goal is None:
        return None

    if name is not None:
        goal.name = name[:100]

    if target_amount is not None:
        goal.target_amount = target_amount

    if current_amount is not None:
        goal.current_amount = current_amount

    if deadline is not _NOT_SET:
        goal.deadline = deadline if isinstance(deadline, datetime) else None

    if account_id is not _NOT_SET:
        goal.account_id = account_id if isinstance(account_id, UUID) else None

    if notes is not _NOT_SET:
        goal.notes = notes if isinstance(notes, str) else None

    session.flush()
    logger.info(f"Updated savings goal: id={goal_id}")
    return goal


class ContributionNotAllowedError(Exception):
    """Raised when contribution is not allowed for a goal's tracking mode."""

    pass


def contribute_to_goal(
    session: Session,
    goal_id: UUID,
    amount: Decimal,
) -> SavingsGoal | None:
    """Add a contribution to a savings goal.

    Only allowed for goals with manual tracking mode.

    :param session: SQLAlchemy session.
    :param goal_id: Goal's UUID.
    :param amount: Amount to add (can be negative for withdrawals).
    :return: Updated SavingsGoal, or None if not found.
    :raises ContributionNotAllowedError: If goal is not in manual tracking mode.
    """
    goal = get_goal_by_id(session, goal_id)
    if goal is None:
        return None

    # Only allow contributions for manual tracking mode
    if goal.tracking_mode_enum != GoalTrackingMode.MANUAL:
        raise ContributionNotAllowedError(
            f"Contributions only allowed for manual tracking mode, "
            f"goal is using {goal.tracking_mode} mode"
        )

    goal.current_amount = goal.current_amount + amount

    # Auto-complete if target reached
    if goal.current_amount >= goal.target_amount:
        goal.status = GoalStatus.COMPLETED.value
        logger.info(f"Savings goal completed: id={goal_id}")

    session.flush()
    logger.info(f"Contributed to savings goal: id={goal_id}, amount={amount}")
    return goal


def complete_goal(session: Session, goal_id: UUID) -> SavingsGoal | None:
    """Mark a savings goal as completed.

    :param session: SQLAlchemy session.
    :param goal_id: Goal's UUID.
    :return: Updated SavingsGoal, or None if not found.
    """
    goal = get_goal_by_id(session, goal_id)
    if goal is None:
        return None

    goal.status = GoalStatus.COMPLETED.value
    session.flush()
    logger.info(f"Completed savings goal: id={goal_id}")
    return goal


def pause_goal(session: Session, goal_id: UUID) -> SavingsGoal | None:
    """Pause a savings goal.

    :param session: SQLAlchemy session.
    :param goal_id: Goal's UUID.
    :return: Updated SavingsGoal, or None if not found.
    """
    goal = get_goal_by_id(session, goal_id)
    if goal is None:
        return None

    goal.status = GoalStatus.PAUSED.value
    session.flush()
    logger.info(f"Paused savings goal: id={goal_id}")
    return goal


def resume_goal(session: Session, goal_id: UUID) -> SavingsGoal | None:
    """Resume a paused savings goal.

    :param session: SQLAlchemy session.
    :param goal_id: Goal's UUID.
    :return: Updated SavingsGoal, or None if not found.
    """
    goal = get_goal_by_id(session, goal_id)
    if goal is None:
        return None

    if goal.status_enum == GoalStatus.PAUSED:
        goal.status = GoalStatus.ACTIVE.value
        session.flush()
        logger.info(f"Resumed savings goal: id={goal_id}")

    return goal


def cancel_goal(session: Session, goal_id: UUID) -> SavingsGoal | None:
    """Cancel a savings goal.

    :param session: SQLAlchemy session.
    :param goal_id: Goal's UUID.
    :return: Updated SavingsGoal, or None if not found.
    """
    goal = get_goal_by_id(session, goal_id)
    if goal is None:
        return None

    goal.status = GoalStatus.CANCELLED.value
    session.flush()
    logger.info(f"Cancelled savings goal: id={goal_id}")
    return goal


def delete_goal(session: Session, goal_id: UUID) -> bool:
    """Delete a savings goal.

    :param session: SQLAlchemy session.
    :param goal_id: Goal's UUID.
    :return: True if deleted, False if not found.
    """
    goal = get_goal_by_id(session, goal_id)
    if goal is None:
        return False

    session.delete(goal)
    session.flush()
    logger.info(f"Deleted savings goal: id={goal_id}")
    return True
