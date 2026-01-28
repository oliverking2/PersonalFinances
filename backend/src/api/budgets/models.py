"""Pydantic models for budget endpoints."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from src.postgres.common.enums import BudgetPeriod


class BudgetResponse(BaseModel):
    """Response model for a budget."""

    id: str = Field(..., description="Budget UUID")
    tag_id: str = Field(..., description="Tag UUID for this budget category")
    tag_name: str = Field(..., description="Tag name")
    tag_colour: str | None = Field(None, description="Tag colour (hex)")
    amount: Decimal = Field(..., description="Budget amount limit")
    currency: str = Field(..., description="Currency code")
    period: BudgetPeriod = Field(..., description="Budget period")
    warning_threshold: Decimal = Field(..., description="Warning threshold (0.0-1.0)")
    enabled: bool = Field(..., description="Whether budget is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class BudgetWithSpendingResponse(BudgetResponse):
    """Budget response with current spending data."""

    spent_amount: Decimal = Field(..., description="Amount spent in current period")
    remaining_amount: Decimal = Field(..., description="Remaining budget")
    percentage_used: Decimal = Field(..., description="Percentage of budget used")
    status: str = Field(..., description="Budget status: ok, warning, exceeded")


class BudgetListResponse(BaseModel):
    """Response model for listing budgets."""

    budgets: list[BudgetWithSpendingResponse] = Field(
        ..., description="List of budgets with spending"
    )
    total: int = Field(..., description="Total number of budgets")


class BudgetCreateRequest(BaseModel):
    """Request model for creating a budget."""

    tag_id: str = Field(..., description="Tag UUID for this budget category")
    amount: Decimal = Field(..., gt=0, description="Budget amount limit")
    currency: str = Field(default="GBP", max_length=3, description="Currency code")
    warning_threshold: Decimal = Field(
        default=Decimal("0.80"),
        ge=0,
        le=1,
        description="Warning threshold (0.0-1.0)",
    )


class BudgetUpdateRequest(BaseModel):
    """Request model for updating a budget."""

    amount: Decimal | None = Field(None, gt=0, description="New budget amount")
    currency: str | None = Field(None, max_length=3, description="New currency code")
    warning_threshold: Decimal | None = Field(None, ge=0, le=1, description="New warning threshold")
    enabled: bool | None = Field(None, description="Enable or disable budget")


class BudgetSummaryResponse(BaseModel):
    """Response model for budget summary statistics."""

    total_budgets: int = Field(..., description="Total number of budgets")
    active_budgets: int = Field(..., description="Number of enabled budgets")
    total_budgeted: Decimal = Field(..., description="Total budgeted amount")
    total_spent: Decimal = Field(..., description="Total spent across all budgets")
    budgets_on_track: int = Field(..., description="Budgets under warning threshold")
    budgets_warning: int = Field(..., description="Budgets at warning level")
    budgets_exceeded: int = Field(..., description="Budgets that have been exceeded")
