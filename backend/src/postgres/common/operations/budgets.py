"""Budget database operations.

This module provides CRUD operations for Budget entities.
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from src.postgres.common.enums import BudgetPeriod
from src.postgres.common.models import Budget

logger = logging.getLogger(__name__)

# Calendar constants for date calculations
_OCTOBER = 10  # Start of Q4
_DECEMBER = 12  # Last month of the year


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
    period: BudgetPeriod | None = None,
    warning_threshold: Decimal | None = None,
    enabled: bool | None = None,
) -> Budget | None:
    """Update a budget.

    :param session: SQLAlchemy session.
    :param budget_id: Budget's UUID.
    :param amount: New budget amount.
    :param currency: New currency code.
    :param period: New budget period.
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

    if period is not None:
        budget.period = period.value

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


def get_period_date_range(period: BudgetPeriod) -> tuple[datetime, datetime]:
    """Get the current period date range for a budget period.

    :param period: Budget period type.
    :return: Tuple of (period_start, period_end) as UTC datetimes.
    """
    now = datetime.now(UTC)

    if period == BudgetPeriod.WEEKLY:
        # ISO week: Monday 00:00 to Sunday 23:59:59
        # weekday() returns 0 for Monday, 6 for Sunday
        days_since_monday = now.weekday()
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
            days=days_since_monday
        )
        period_end = period_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

    elif period == BudgetPeriod.QUARTERLY:
        # Calendar quarter: Q1 (Jan-Mar), Q2 (Apr-Jun), Q3 (Jul-Sep), Q4 (Oct-Dec)
        quarter = (now.month - 1) // 3  # 0-indexed quarter
        quarter_start_month = quarter * 3 + 1  # 1, 4, 7, or 10
        period_start = now.replace(
            month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        # End of quarter: last day of the 3rd month
        if quarter_start_month == _OCTOBER:
            period_end = now.replace(
                year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(seconds=1)
        else:
            period_end = now.replace(
                month=quarter_start_month + 3, day=1, hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(seconds=1)

    elif period == BudgetPeriod.ANNUAL:
        # Calendar year: Jan 1 to Dec 31
        period_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        period_end = now.replace(
            year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(seconds=1)

    else:
        # MONTHLY: 1st of month to last day of month
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Calculate last day of month by going to next month and subtracting a second
        if now.month == _DECEMBER:
            next_month = now.replace(
                year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
            )
        else:
            next_month = now.replace(
                month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0
            )
        period_end = next_month - timedelta(seconds=1)

    return period_start, period_end


def get_current_period_key(period: BudgetPeriod) -> str:
    """Get the current period key for a budget period.

    :param period: Budget period type.
    :return: Period key string in format appropriate for the period type.
             - Weekly: "2026-W05"
             - Monthly: "2026-01"
             - Quarterly: "2026-Q1"
             - Annual: "2026"
    """
    now = datetime.now(UTC)

    if period == BudgetPeriod.WEEKLY:
        # ISO week number
        iso_year, iso_week, _ = now.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    if period == BudgetPeriod.QUARTERLY:
        quarter = (now.month - 1) // 3 + 1  # 1-4
        return f"{now.year}-Q{quarter}"
    if period == BudgetPeriod.ANNUAL:
        return str(now.year)
    # MONTHLY
    return now.strftime("%Y-%m")
