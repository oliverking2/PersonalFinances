"""Pydantic models for notifications endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.postgres.common.enums import NotificationType


class NotificationResponse(BaseModel):
    """Response model for a notification."""

    id: str = Field(..., description="Notification UUID")
    notification_type: NotificationType = Field(..., description="Type of notification")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    read: bool = Field(..., description="Whether the notification has been read")
    metadata: dict[str, Any] = Field(..., description="Type-specific metadata")
    created_at: datetime = Field(..., description="When the notification was created")
    read_at: datetime | None = Field(None, description="When the notification was read")

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """Response model for listing notifications."""

    notifications: list[NotificationResponse] = Field(..., description="List of notifications")
    total: int = Field(..., description="Total number of notifications returned")
    unread_count: int = Field(..., description="Number of unread notifications")


class NotificationCountResponse(BaseModel):
    """Response model for notification count."""

    unread_count: int = Field(..., description="Number of unread notifications")
