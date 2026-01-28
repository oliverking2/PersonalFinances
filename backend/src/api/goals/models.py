"""Pydantic models for goals endpoints."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from src.postgres.common.enums import GoalStatus, GoalTrackingMode


class GoalResponse(BaseModel):
    """Response model for a savings goal."""

    id: str = Field(..., description="Goal UUID")
    name: str = Field(..., description="Goal name")
    target_amount: Decimal = Field(..., description="Target savings amount")
    current_amount: Decimal = Field(
        ..., description="Current saved amount (calculated for non-manual modes)"
    )
    currency: str = Field(..., description="Currency code")
    deadline: datetime | None = Field(None, description="Target date")
    account_id: str | None = Field(None, description="Linked account UUID")
    account_name: str | None = Field(None, description="Linked account name")
    tracking_mode: GoalTrackingMode = Field(..., description="How progress is tracked")
    starting_balance: Decimal | None = Field(
        None, description="Account balance at goal creation (delta mode)"
    )
    target_balance: Decimal | None = Field(
        None, description="Target account balance (target_balance mode)"
    )
    status: GoalStatus = Field(..., description="Goal status")
    notes: str | None = Field(None, description="User notes")
    progress_percentage: Decimal = Field(..., description="Progress percentage (0-100)")
    days_remaining: int | None = Field(None, description="Days until deadline")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class GoalListResponse(BaseModel):
    """Response model for listing goals."""

    goals: list[GoalResponse] = Field(..., description="List of goals")
    total: int = Field(..., description="Total number of goals")


class GoalCreateRequest(BaseModel):
    """Request model for creating a goal."""

    name: str = Field(..., min_length=1, max_length=100, description="Goal name")
    target_amount: Decimal = Field(..., gt=0, description="Target savings amount")
    current_amount: Decimal = Field(
        default=Decimal("0"), ge=0, description="Starting amount (manual mode only)"
    )
    currency: str = Field(default="GBP", max_length=3, description="Currency code")
    deadline: date | None = Field(None, description="Target date (YYYY-MM-DD)")
    account_id: str | None = Field(None, description="Link to account for auto-tracking")
    tracking_mode: GoalTrackingMode = Field(
        default=GoalTrackingMode.MANUAL,
        description="How progress is tracked: manual, balance, delta, or target_balance",
    )
    target_balance: Decimal | None = Field(
        None, gt=0, description="Target account balance (required for target_balance mode)"
    )
    notes: str | None = Field(None, description="User notes")


class GoalUpdateRequest(BaseModel):
    """Request model for updating a goal."""

    name: str | None = Field(None, min_length=1, max_length=100, description="New name")
    target_amount: Decimal | None = Field(None, gt=0, description="New target amount")
    current_amount: Decimal | None = Field(None, ge=0, description="New current amount")
    deadline: date | None = Field(None, description="New deadline")
    account_id: str | None = Field(None, description="New account link")
    notes: str | None = Field(None, description="New notes")
    clear_deadline: bool = Field(default=False, description="Clear the deadline")
    clear_account: bool = Field(default=False, description="Clear the account link")
    clear_notes: bool = Field(default=False, description="Clear notes")


class ContributeRequest(BaseModel):
    """Request model for contributing to a goal."""

    amount: Decimal = Field(..., description="Amount to add (positive) or withdraw (negative)")


class GoalSummaryResponse(BaseModel):
    """Response model for goals summary statistics."""

    total_goals: int = Field(..., description="Total number of goals")
    active_goals: int = Field(..., description="Number of active goals")
    completed_goals: int = Field(..., description="Number of completed goals")
    total_target: Decimal = Field(..., description="Sum of all target amounts")
    total_saved: Decimal = Field(..., description="Sum of all current amounts")
    overall_progress: Decimal = Field(..., description="Overall progress percentage")
