"""Budget database operations.

This module provides CRUD operations for Budget entities.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from src.postgres.common.enums import BudgetPeriod
from src.postgres.common.models import Budget

logger = logging.getLogger(__name__)


def get_budget_by_id(session: Session, budget_id: UUID) -> Budget | None:
    """Get a budget by its ID.

    :param session: SQLAlchemy session.
    :param budget_id: Budget's UUID.
    :return: Budget if found, None otherwise.
    """
    return session.get(Budget, budget_id)


def get_budgets_by_user_id(
    session: Session,
    user_id: UUID,
    *,
    enabled_only: bool = False,
) -> list[Budget]:
    """Get all budgets for a user.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param enabled_only: If True, only return enabled budgets.
    :return: List of budgets ordered by amount (descending).
    """
    query = session.query(Budget).filter(Budget.user_id == user_id)

    if enabled_only:
        query = query.filter(Budget.enabled.is_(True))

    return query.order_by(Budget.amount.desc()).all()


def get_budget_by_tag(
    session: Session,
    user_id: UUID,
    tag_id: UUID,
) -> Budget | None:
    """Get a budget by user and tag.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param tag_id: Tag's UUID.
    :return: Budget if found, None otherwise.
    """
    return session.query(Budget).filter(Budget.user_id == user_id, Budget.tag_id == tag_id).first()


def create_budget(
    session: Session,
    user_id: UUID,
    tag_id: UUID,
    amount: Decimal,
    *,
    currency: str = "GBP",
    period: BudgetPeriod = BudgetPeriod.MONTHLY,
    warning_threshold: Decimal = Decimal("0.80"),
    enabled: bool = True,
) -> Budget:
    """Create a new budget.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param tag_id: Tag's UUID for this budget category.
    :param amount: Budget amount limit.
    :param currency: Currency code (default GBP).
    :param period: Budget period (default MONTHLY).
    :param warning_threshold: Percentage threshold for warning alerts (0.0-1.0).
    :param enabled: Whether the budget is active.
    :return: Created Budget entity.
    """
    budget = Budget(
        user_id=user_id,
        tag_id=tag_id,
        amount=amount,
        currency=currency,
        period=period.value,
        warning_threshold=warning_threshold,
        enabled=enabled,
    )
    session.add(budget)
    session.flush()

    logger.info(f"Created budget: id={budget.id}, user_id={user_id}, tag_id={tag_id}")
    return budget


_NOT_SET = object()


def update_budget(
    session: Session,
    budget_id: UUID,
    *,
    amount: Decimal | None = None,
    currency: str | None = None,
    warning_threshold: Decimal | None = None,
    enabled: bool | None = None,
) -> Budget | None:
    """Update a budget.

    :param session: SQLAlchemy session.
    :param budget_id: Budget's UUID.
    :param amount: New budget amount.
    :param currency: New currency code.
    :param warning_threshold: New warning threshold (0.0-1.0).
    :param enabled: New enabled state.
    :return: Updated Budget, or None if not found.
    """
    budget = get_budget_by_id(session, budget_id)
    if budget is None:
        return None

    if amount is not None:
        budget.amount = amount

    if currency is not None:
        budget.currency = currency

    if warning_threshold is not None:
        budget.warning_threshold = warning_threshold

    if enabled is not None:
        budget.enabled = enabled

    session.flush()
    logger.info(f"Updated budget: id={budget_id}")
    return budget


def delete_budget(session: Session, budget_id: UUID) -> bool:
    """Delete a budget.

    This also removes all related spending alerts (via CASCADE).

    :param session: SQLAlchemy session.
    :param budget_id: Budget's UUID.
    :return: True if deleted, False if not found.
    """
    budget = get_budget_by_id(session, budget_id)
    if budget is None:
        return False

    session.delete(budget)
    session.flush()
    logger.info(f"Deleted budget: id={budget_id}")
    return True


def get_current_period_key(period: BudgetPeriod) -> str:
    """Get the current period key for a budget period.

    :param period: Budget period type.
    :return: Period key string (e.g., "2026-01" for monthly).
    """
    now = datetime.now(UTC)
    if period == BudgetPeriod.MONTHLY:
        return now.strftime("%Y-%m")
    # Extend for other periods when needed
    return now.strftime("%Y-%m")
