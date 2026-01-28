"""Alerts API endpoints."""

import logging
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.alerts.models import (
    AlertCountResponse,
    AlertListResponse,
    AlertResponse,
)
from src.api.dependencies import get_current_user, get_db
from src.api.responses import RESOURCE_RESPONSES, UNAUTHORIZED
from src.postgres.auth.models import User
from src.postgres.common.enums import AlertStatus
from src.postgres.common.models import SpendingAlert
from src.postgres.common.operations.alerts import (
    acknowledge_alert,
    acknowledge_all_alerts,
    get_alert_by_id,
    get_alerts_by_user_id,
    get_pending_alerts_count,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=AlertListResponse,
    summary="List alerts",
    responses=UNAUTHORIZED,
)
def list_alerts(
    status: AlertStatus | None = Query(None, description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=100, description="Max alerts to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertListResponse:
    """List spending alerts for the authenticated user."""
    alerts = get_alerts_by_user_id(db, current_user.id, status=status, limit=limit)
    pending_count = get_pending_alerts_count(db, current_user.id)

    return AlertListResponse(
        alerts=[_to_response(a) for a in alerts],
        total=len(alerts),
        pending_count=pending_count,
    )


@router.get(
    "/count",
    response_model=AlertCountResponse,
    summary="Get pending alert count",
    responses=UNAUTHORIZED,
)
def get_alert_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertCountResponse:
    """Get the count of pending (unread) alerts."""
    count = get_pending_alerts_count(db, current_user.id)
    return AlertCountResponse(pending_count=count)


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Get alert by ID",
    responses=RESOURCE_RESPONSES,
)
def get_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertResponse:
    """Retrieve a specific alert by its UUID."""
    alert = get_alert_by_id(db, alert_id)
    if not alert or alert.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")

    return _to_response(alert)


@router.put(
    "/{alert_id}/acknowledge",
    response_model=AlertResponse,
    summary="Acknowledge alert",
    responses=RESOURCE_RESPONSES,
)
def acknowledge_alert_endpoint(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertResponse:
    """Mark an alert as acknowledged."""
    alert = get_alert_by_id(db, alert_id)
    if not alert or alert.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")

    acknowledged = acknowledge_alert(db, alert_id)
    if not acknowledged:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")

    db.commit()
    db.refresh(acknowledged)
    logger.info(f"Acknowledged alert: id={alert_id}")
    return _to_response(acknowledged)


@router.put(
    "/acknowledge-all",
    response_model=AlertCountResponse,
    summary="Acknowledge all alerts",
    responses=UNAUTHORIZED,
)
def acknowledge_all_alerts_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertCountResponse:
    """Mark all pending alerts as acknowledged."""
    count = acknowledge_all_alerts(db, current_user.id)
    db.commit()
    logger.info(f"Acknowledged {count} alerts for user: user_id={current_user.id}")
    return AlertCountResponse(pending_count=0)


def _to_response(alert: SpendingAlert) -> AlertResponse:
    """Convert a SpendingAlert model to API response.

    :param alert: Database model.
    :return: API response model.
    """
    percentage = (
        (alert.spent_amount / alert.budget_amount * 100)
        if alert.budget_amount > 0
        else Decimal("0")
    )

    # Get tag info from budget
    tag_name = "Unknown"
    tag_colour = None
    if alert.budget and alert.budget.tag:
        tag_name = alert.budget.tag.name
        tag_colour = alert.budget.tag.colour

    return AlertResponse(
        id=str(alert.id),
        budget_id=str(alert.budget_id),
        tag_name=tag_name,
        tag_colour=tag_colour,
        alert_type=alert.alert_type_enum,
        status=alert.status_enum,
        period_key=alert.period_key,
        budget_amount=alert.budget_amount,
        spent_amount=alert.spent_amount,
        percentage_used=percentage,
        message=alert.message,
        created_at=alert.created_at,
        acknowledged_at=alert.acknowledged_at,
    )
