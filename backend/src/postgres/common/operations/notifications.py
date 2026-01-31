"""Notification database operations.

This module provides CRUD operations for Notification entities.
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import String, cast, func
from sqlalchemy.orm import Session

from src.postgres.common.enums import NotificationType
from src.postgres.common.models import Budget, Notification, Transaction, TransactionSplit

logger = logging.getLogger(__name__)


def get_notification_by_id(session: Session, notification_id: UUID) -> Notification | None:
    """Get a notification by its ID.

    :param session: SQLAlchemy session.
    :param notification_id: Notification's UUID.
    :return: Notification if found, None otherwise.
    """
    return session.get(Notification, notification_id)


def get_notifications_by_user_id(
    session: Session,
    user_id: UUID,
    *,
    unread_only: bool = False,
    limit: int | None = None,
    offset: int | None = None,
) -> list[Notification]:
    """Get notifications for a user.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param unread_only: If True, only return unread notifications.
    :param limit: Maximum number of notifications to return.
    :param offset: Number of notifications to skip.
    :return: List of notifications ordered by creation date (newest first).
    """
    query = session.query(Notification).filter(Notification.user_id == user_id)

    if unread_only:
        query = query.filter(Notification.read == False)  # noqa: E712

    query = query.order_by(Notification.created_at.desc())

    if offset is not None:
        query = query.offset(offset)

    if limit is not None:
        query = query.limit(limit)

    return query.all()


def get_unread_count(session: Session, user_id: UUID) -> int:
    """Get the count of unread notifications for a user.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :return: Number of unread notifications.
    """
    return (
        session.query(func.count(Notification.id))
        .filter(
            Notification.user_id == user_id,
            Notification.read == False,  # noqa: E712
        )
        .scalar()
        or 0
    )


def create_notification(
    session: Session,
    user_id: UUID,
    notification_type: NotificationType,
    title: str,
    message: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> Notification:
    """Create a new notification.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param notification_type: Type of notification.
    :param title: Notification title (max 100 chars).
    :param message: Notification message (max 500 chars).
    :param metadata: Optional type-specific data stored in extra_data field.
    :return: Created Notification.
    """
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type.value,
        title=title[:100],
        message=message[:500],
        extra_data=metadata or {},
    )
    session.add(notification)
    session.flush()

    logger.info(
        f"Created notification: id={notification.id}, type={notification_type.value}, "
        f"user_id={user_id}"
    )
    return notification


def create_budget_notification(
    session: Session,
    user_id: UUID,
    notification_type: NotificationType,
    title: str,
    message: str,
    *,
    budget_id: UUID,
    tag_name: str,
    period_key: str,
    budget_amount: float,
    spent_amount: float,
    percentage: int,
) -> Notification | None:
    """Create a budget notification with deduplication.

    If a notification of the same type already exists for this budget and period,
    returns None without creating a duplicate.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param notification_type: Type of budget notification.
    :param title: Notification title.
    :param message: Notification message.
    :param budget_id: Budget's UUID.
    :param tag_name: Name of the budget tag.
    :param period_key: Period key for deduplication (e.g., "2026-01").
    :param budget_amount: Budget amount.
    :param spent_amount: Amount spent.
    :param percentage: Percentage of budget used.
    :return: Created Notification, or None if duplicate exists.
    """
    # Check for existing notification with same budget/period/type
    # We need to check extra_data fields, which requires a more complex query
    existing = (
        session.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.notification_type == notification_type.value,
            cast(Notification.extra_data["budget_id"], String) == str(budget_id),
            cast(Notification.extra_data["period_key"], String) == period_key,
        )
        .first()
    )

    if existing is not None:
        logger.debug(
            f"Skipping duplicate budget notification: budget_id={budget_id}, "
            f"type={notification_type.value}, period={period_key}"
        )
        return None

    metadata = {
        "budget_id": str(budget_id),
        "tag_name": tag_name,
        "period_key": period_key,
        "budget_amount": budget_amount,
        "spent_amount": spent_amount,
        "percentage": percentage,
    }

    return create_notification(
        session,
        user_id,
        notification_type,
        title,
        message,
        metadata=metadata,
    )


def mark_as_read(session: Session, notification_id: UUID) -> Notification | None:
    """Mark a notification as read.

    :param session: SQLAlchemy session.
    :param notification_id: Notification's UUID.
    :return: Updated Notification, or None if not found.
    """
    notification = get_notification_by_id(session, notification_id)
    if notification is None:
        return None

    if not notification.read:
        notification.read = True
        notification.read_at = datetime.now(UTC)
        session.flush()
        logger.info(f"Marked notification as read: id={notification_id}")

    return notification


def mark_all_as_read(session: Session, user_id: UUID) -> int:
    """Mark all unread notifications as read for a user.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :return: Number of notifications marked as read.
    """
    now = datetime.now(UTC)
    result = (
        session.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.read == False,  # noqa: E712
        )
        .update(
            {
                Notification.read: True,
                Notification.read_at: now,
            }
        )
    )

    session.flush()
    logger.info(f"Marked {result} notifications as read for user: user_id={user_id}")
    return result


def delete_notification(session: Session, notification_id: UUID) -> bool:
    """Delete a notification.

    :param session: SQLAlchemy session.
    :param notification_id: Notification's UUID.
    :return: True if deleted, False if not found.
    """
    notification = get_notification_by_id(session, notification_id)
    if notification is None:
        return False

    session.delete(notification)
    session.flush()
    logger.info(f"Deleted notification: id={notification_id}")
    return True


def delete_old_notifications(session: Session, days: int = 30) -> int:
    """Delete read notifications older than the specified number of days.

    This is used for cleanup to prevent unbounded storage growth.
    Only deletes read notifications; unread ones are preserved indefinitely.

    :param session: SQLAlchemy session.
    :param days: Delete read notifications older than this many days.
    :return: Number of notifications deleted.
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)
    result = (
        session.query(Notification)
        .filter(
            Notification.read == True,  # noqa: E712
            Notification.created_at < cutoff,
        )
        .delete()
    )

    session.flush()
    if result > 0:
        logger.info(f"Deleted {result} old read notifications (older than {days} days)")
    return result


def _calculate_budget_spending(session: Session, budget: Budget) -> Decimal:
    """Calculate total spending for a budget in the current period.

    :param session: SQLAlchemy session.
    :param budget: Budget entity.
    :return: Total spent amount for the budget's tag in current period.
    """
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = (
        session.query(func.coalesce(func.sum(TransactionSplit.amount), 0))
        .join(Transaction, TransactionSplit.transaction_id == Transaction.id)
        .filter(
            TransactionSplit.tag_id == budget.tag_id,
            Transaction.booking_date >= month_start,
            Transaction.amount < 0,  # Only spending transactions
        )
        .scalar()
    )

    return Decimal(str(result)) if result else Decimal("0")


def check_budgets_and_notify(session: Session, user_id: UUID) -> int:
    """Check all enabled budgets for a user and create notifications if needed.

    Creates BUDGET_WARNING notifications when spending reaches the warning threshold.
    Creates BUDGET_EXCEEDED notifications when spending exceeds the budget.

    Notifications are deduplicated by (budget_id, period_key) so each budget
    can only trigger one warning and one exceeded notification per period.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :return: Number of notifications created.
    """
    # Get all enabled budgets for user
    budgets = (
        session.query(Budget).filter(Budget.user_id == user_id, Budget.enabled.is_(True)).all()
    )

    if not budgets:
        return 0

    # Get current period key
    now = datetime.now(UTC)
    period_key = now.strftime("%Y-%m")

    # Threshold for exceeded budget (100%)
    exceeded_threshold = 100

    notifications_created = 0

    for budget in budgets:
        spent = _calculate_budget_spending(session, budget)
        if budget.amount <= 0:
            continue

        percentage = int(spent / budget.amount * 100)
        tag_name = budget.tag.name if budget.tag else "Unknown"
        warning_pct = int(budget.warning_threshold * 100)

        # Check if exceeded (100%+)
        if percentage >= exceeded_threshold:
            notification = create_budget_notification(
                session,
                user_id,
                NotificationType.BUDGET_EXCEEDED,
                title="Budget Exceeded",
                message=f"Your {tag_name} budget has been exceeded ({percentage}% spent).",
                budget_id=budget.id,
                tag_name=tag_name,
                period_key=period_key,
                budget_amount=float(budget.amount),
                spent_amount=float(spent),
                percentage=percentage,
            )
            if notification:
                notifications_created += 1

        # Check if at warning level (but not yet exceeded)
        elif percentage >= warning_pct:
            notification = create_budget_notification(
                session,
                user_id,
                NotificationType.BUDGET_WARNING,
                title="Budget Warning",
                message=f"Your {tag_name} budget is at {percentage}% (warning at {warning_pct}%).",
                budget_id=budget.id,
                tag_name=tag_name,
                period_key=period_key,
                budget_amount=float(budget.amount),
                spent_amount=float(spent),
                percentage=percentage,
            )
            if notification:
                notifications_created += 1

    if notifications_created > 0:
        logger.info(
            f"Created {notifications_created} budget notifications for user: user_id={user_id}"
        )

    return notifications_created
