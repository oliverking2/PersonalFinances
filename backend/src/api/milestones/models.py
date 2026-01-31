"""Pydantic models for financial milestones API."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class MilestoneResponse(BaseModel):
    """Response model for a financial milestone."""

    id: UUID = Field(..., description="Milestone UUID")
    user_id: UUID = Field(..., description="Owner's UUID")
    name: str = Field(..., description="Milestone name")
    target_amount: Decimal = Field(..., description="Net worth target")
    target_date: datetime | None = Field(None, description="Optional deadline")
    colour: str = Field(..., description="Display colour (hex)")
    achieved: bool = Field(..., description="Whether milestone has been reached")
    achieved_at: datetime | None = Field(None, description="When milestone was achieved")
    notes: str | None = Field(None, description="User notes")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class MilestoneCreateRequest(BaseModel):
    """Request model for creating a milestone."""

    name: str = Field(..., min_length=1, max_length=100, description="Milestone name")
    target_amount: Decimal = Field(..., gt=0, description="Net worth target")
    target_date: datetime | None = Field(None, description="Optional deadline")
    colour: str = Field(
        "#f59e0b",
        pattern=r"^#[0-9a-fA-F]{6}$",
        description="Display colour (hex)",
    )
    notes: str | None = Field(None, max_length=500, description="User notes")


class MilestoneUpdateRequest(BaseModel):
    """Request model for updating a milestone."""

    name: str | None = Field(None, min_length=1, max_length=100, description="New name")
    target_amount: Decimal | None = Field(None, gt=0, description="New target")
    target_date: datetime | None = Field(None, description="New deadline")
    clear_target_date: bool = Field(False, description="Set to true to clear target_date")
    colour: str | None = Field(
        None,
        pattern=r"^#[0-9a-fA-F]{6}$",
        description="New colour (hex)",
    )
    notes: str | None = Field(None, max_length=500, description="New notes")
    clear_notes: bool = Field(False, description="Set to true to clear notes")


class MilestoneListResponse(BaseModel):
    """Response for listing milestones."""

    milestones: list[MilestoneResponse] = Field(..., description="List of milestones")
    total: int = Field(..., description="Total count")
