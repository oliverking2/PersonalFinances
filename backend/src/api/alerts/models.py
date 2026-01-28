"""Pydantic models for alerts endpoints."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from src.postgres.common.enums import AlertStatus, AlertType


class AlertResponse(BaseModel):
    """Response model for a spending alert."""

    id: str = Field(..., description="Alert UUID")
    budget_id: str = Field(..., description="Budget UUID")
    tag_name: str = Field(..., description="Budget tag name")
    tag_colour: str | None = Field(None, description="Budget tag colour")
    alert_type: AlertType = Field(..., description="Type of alert")
    status: AlertStatus = Field(..., description="Alert status")
    period_key: str = Field(..., description="Budget period key")
    budget_amount: Decimal = Field(..., description="Budget amount at time of alert")
    spent_amount: Decimal = Field(..., description="Amount spent at time of alert")
    percentage_used: Decimal = Field(..., description="Percentage of budget used")
    message: str | None = Field(None, description="Alert message")
    created_at: datetime = Field(..., description="When alert was created")
    acknowledged_at: datetime | None = Field(None, description="When alert was acknowledged")

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    """Response model for listing alerts."""

    alerts: list[AlertResponse] = Field(..., description="List of alerts")
    total: int = Field(..., description="Total number of alerts")
    pending_count: int = Field(..., description="Number of pending (unread) alerts")


class AlertCountResponse(BaseModel):
    """Response model for alert count."""

    pending_count: int = Field(..., description="Number of pending (unread) alerts")
