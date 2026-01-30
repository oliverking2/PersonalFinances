"""Notifications API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
from src.api.notifications.models import (
    NotificationCountResponse,
    NotificationListResponse,
    NotificationResponse,
)
from src.api.responses import RESOURCE_RESPONSES, UNAUTHORIZED
from src.postgres.auth.models import User
from src.postgres.common.models import Notification
from src.postgres.common.operations.notifications import (
    delete_notification,
    get_notification_by_id,
    get_notifications_by_user_id,
    get_unread_count,
    mark_all_as_read,
    mark_as_read,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List notifications",
    responses=UNAUTHORIZED,
)
def list_notifications(
    unread_only: bool = Query(False, description="Only return unread notifications"),
    limit: int = Query(default=50, ge=1, le=100, description="Max notifications to return"),
    offset: int = Query(default=0, ge=0, description="Number of notifications to skip"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationListResponse:
    """List notifications for the authenticated user, newest first."""
    notifications = get_notifications_by_user_id(
        db, current_user.id, unread_only=unread_only, limit=limit, offset=offset
    )
    unread_count = get_unread_count(db, current_user.id)

    return NotificationListResponse(
        notifications=[_to_response(n) for n in notifications],
        total=len(notifications),
        unread_count=unread_count,
    )


@router.get(
    "/count",
    response_model=NotificationCountResponse,
    summary="Get unread notification count",
    responses=UNAUTHORIZED,
)
def get_notification_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationCountResponse:
    """Get the count of unread notifications for badge display."""
    count = get_unread_count(db, current_user.id)
    return NotificationCountResponse(unread_count=count)


@router.put(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark notification as read",
    responses=RESOURCE_RESPONSES,
)
def mark_notification_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationResponse:
    """Mark a specific notification as read."""
    notification = get_notification_by_id(db, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Notification not found: {notification_id}")

    updated = mark_as_read(db, notification_id)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Notification not found: {notification_id}")

    db.commit()
    db.refresh(updated)
    logger.info(f"Marked notification as read: id={notification_id}")
    return _to_response(updated)


@router.put(
    "/read-all",
    response_model=NotificationCountResponse,
    summary="Mark all notifications as read",
    responses=UNAUTHORIZED,
)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationCountResponse:
    """Mark all unread notifications as read."""
    count = mark_all_as_read(db, current_user.id)
    db.commit()
    logger.info(f"Marked {count} notifications as read for user: user_id={current_user.id}")
    return NotificationCountResponse(unread_count=0)


@router.delete(
    "/{notification_id}",
    status_code=204,
    summary="Delete notification",
    responses=RESOURCE_RESPONSES,
)
def delete_notification_endpoint(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a notification."""
    notification = get_notification_by_id(db, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Notification not found: {notification_id}")

    deleted = delete_notification(db, notification_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Notification not found: {notification_id}")

    db.commit()
    logger.info(f"Deleted notification: id={notification_id}")


def _to_response(notification: Notification) -> NotificationResponse:
    """Convert a Notification model to API response.

    :param notification: Database model.
    :returns: API response model.
    """
    return NotificationResponse(
        id=str(notification.id),
        notification_type=notification.notification_type_enum,
        title=notification.title,
        message=notification.message,
        read=notification.read,
        metadata=notification.extra_data,
        created_at=notification.created_at,
        read_at=notification.read_at,
    )
