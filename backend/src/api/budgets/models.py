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
    period: BudgetPeriod = Field(default=BudgetPeriod.MONTHLY, description="Budget period")
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
    period: BudgetPeriod | None = Field(None, description="New budget period")
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


class BudgetForecastItem(BaseModel):
    """Forecast data for a single budget."""

    budget_id: str = Field(..., description="Budget UUID")
    tag_id: str = Field(..., description="Tag UUID")
    tag_name: str = Field(..., description="Tag name")
    tag_colour: str | None = Field(None, description="Tag colour (hex)")
    budget_amount: Decimal = Field(..., description="Budget limit")
    currency: str = Field(..., description="Currency code")
    period: BudgetPeriod = Field(..., description="Budget period")
    spent_amount: Decimal = Field(..., description="Amount spent in current period")
    remaining_amount: Decimal = Field(..., description="Remaining budget")
    percentage_used: Decimal = Field(..., description="Percentage of budget used")
    budget_status: str = Field(..., description="Current status: ok, warning, exceeded")
    days_remaining: int = Field(..., description="Days remaining in current period")
    daily_avg_spending: Decimal = Field(
        ..., description="Historical daily average spending (last 90 days)"
    )
    days_until_exhausted: Decimal | None = Field(
        None, description="Projected days until budget exhausted"
    )
    projected_exceed_date: str | None = Field(
        None, description="Date when budget is projected to be exceeded"
    )
    will_exceed_in_period: bool = Field(
        ..., description="Whether budget will exceed before period ends"
    )
    projected_percentage: Decimal = Field(
        ..., description="Projected percentage used at end of period"
    )
    risk_level: str = Field(..., description="Risk level: low, medium, high, critical")


class BudgetForecastResponse(BaseModel):
    """Response model for budget forecasts."""

    forecasts: list[BudgetForecastItem] = Field(..., description="Budget forecasts")
    budgets_at_risk: int = Field(
        ..., description="Number of budgets projected to exceed in current period"
    )
