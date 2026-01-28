"""Spending alert database operations.

This module provides CRUD operations for SpendingAlert entities.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.postgres.common.enums import AlertStatus, AlertType
from src.postgres.common.models import SpendingAlert

logger = logging.getLogger(__name__)


def get_alert_by_id(session: Session, alert_id: UUID) -> SpendingAlert | None:
    """Get a spending alert by its ID.

    :param session: SQLAlchemy session.
    :param alert_id: Alert's UUID.
    :return: SpendingAlert if found, None otherwise.
    """
    return session.get(SpendingAlert, alert_id)


def get_alerts_by_user_id(
    session: Session,
    user_id: UUID,
    *,
    status: AlertStatus | None = None,
    limit: int | None = None,
) -> list[SpendingAlert]:
    """Get all spending alerts for a user.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param status: Filter by status (None for all).
    :param limit: Maximum number of alerts to return.
    :return: List of alerts ordered by creation date (newest first).
    """
    query = session.query(SpendingAlert).filter(SpendingAlert.user_id == user_id)

    if status is not None:
        query = query.filter(SpendingAlert.status == status.value)

    query = query.order_by(SpendingAlert.created_at.desc())

    if limit is not None:
        query = query.limit(limit)

    return query.all()


def get_pending_alerts_count(session: Session, user_id: UUID) -> int:
    """Get the count of pending (unacknowledged) alerts for a user.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :return: Number of pending alerts.
    """
    return (
        session.query(func.count(SpendingAlert.id))
        .filter(
            SpendingAlert.user_id == user_id,
            SpendingAlert.status == AlertStatus.PENDING.value,
        )
        .scalar()
        or 0
    )


def create_alert(
    session: Session,
    user_id: UUID,
    budget_id: UUID,
    alert_type: AlertType,
    period_key: str,
    budget_amount: Decimal,
    spent_amount: Decimal,
    *,
    message: str | None = None,
) -> SpendingAlert | None:
    """Create a new spending alert with deduplication.

    If an alert of the same type already exists for this budget and period,
    returns None without creating a duplicate.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param budget_id: Budget's UUID.
    :param alert_type: Type of alert.
    :param period_key: Period key for deduplication (e.g., "2026-01").
    :param budget_amount: Budget amount at time of alert.
    :param spent_amount: Amount spent at time of alert.
    :param message: Optional alert message.
    :return: Created SpendingAlert, or None if duplicate exists.
    """
    # Check for existing alert (deduplication)
    existing = (
        session.query(SpendingAlert)
        .filter(
            SpendingAlert.user_id == user_id,
            SpendingAlert.budget_id == budget_id,
            SpendingAlert.alert_type == alert_type.value,
            SpendingAlert.period_key == period_key,
        )
        .first()
    )

    if existing is not None:
        logger.debug(
            f"Skipping duplicate alert: budget_id={budget_id}, "
            f"type={alert_type.value}, period={period_key}"
        )
        return None

    alert = SpendingAlert(
        user_id=user_id,
        budget_id=budget_id,
        alert_type=alert_type.value,
        status=AlertStatus.PENDING.value,
        period_key=period_key,
        budget_amount=budget_amount,
        spent_amount=spent_amount,
        message=message[:500] if message else None,
    )
    session.add(alert)
    session.flush()

    logger.info(
        f"Created spending alert: id={alert.id}, budget_id={budget_id}, "
        f"type={alert_type.value}, period={period_key}"
    )
    return alert


def acknowledge_alert(session: Session, alert_id: UUID) -> SpendingAlert | None:
    """Acknowledge a spending alert.

    :param session: SQLAlchemy session.
    :param alert_id: Alert's UUID.
    :return: Updated SpendingAlert, or None if not found.
    """
    alert = get_alert_by_id(session, alert_id)
    if alert is None:
        return None

    alert.status = AlertStatus.ACKNOWLEDGED.value
    alert.acknowledged_at = datetime.now(UTC)
    session.flush()

    logger.info(f"Acknowledged spending alert: id={alert_id}")
    return alert


def acknowledge_all_alerts(session: Session, user_id: UUID) -> int:
    """Acknowledge all pending alerts for a user.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :return: Number of alerts acknowledged.
    """
    now = datetime.now(UTC)
    result = (
        session.query(SpendingAlert)
        .filter(
            SpendingAlert.user_id == user_id,
            SpendingAlert.status == AlertStatus.PENDING.value,
        )
        .update(
            {
                SpendingAlert.status: AlertStatus.ACKNOWLEDGED.value,
                SpendingAlert.acknowledged_at: now,
            }
        )
    )

    session.flush()
    logger.info(f"Acknowledged {result} alerts for user: user_id={user_id}")
    return result


def delete_alert(session: Session, alert_id: UUID) -> bool:
    """Delete a spending alert.

    :param session: SQLAlchemy session.
    :param alert_id: Alert's UUID.
    :return: True if deleted, False if not found.
    """
    alert = get_alert_by_id(session, alert_id)
    if alert is None:
        return False

    session.delete(alert)
    session.flush()
    logger.info(f"Deleted spending alert: id={alert_id}")
    return True
