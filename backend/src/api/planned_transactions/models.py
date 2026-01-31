"""Pydantic models for planned transactions endpoints."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from src.postgres.common.enums import RecurringFrequency


class PlannedTransactionResponse(BaseModel):
    """Response model for a planned transaction."""

    id: str = Field(..., description="Planned transaction UUID")
    name: str = Field(..., description="Name/description")
    amount: Decimal = Field(..., description="Amount (positive = income, negative = expense)")
    currency: str = Field(..., description="Currency code")
    frequency: RecurringFrequency | None = Field(
        None, description="Recurrence frequency (null = one-time)"
    )
    next_expected_date: datetime | None = Field(
        None, description="When this transaction is next expected"
    )
    end_date: datetime | None = Field(None, description="When recurring transactions should stop")
    account_id: str | None = Field(None, description="Linked account UUID")
    account_name: str | None = Field(None, description="Linked account display name")
    notes: str | None = Field(None, description="Optional notes")
    enabled: bool = Field(..., description="Whether this is active")
    direction: str = Field(..., description="Transaction direction: income or expense")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class PlannedTransactionListResponse(BaseModel):
    """Response model for listing planned transactions."""

    transactions: list[PlannedTransactionResponse] = Field(
        ..., description="List of planned transactions"
    )
    total: int = Field(..., description="Total number of transactions")


class PlannedTransactionSummaryResponse(BaseModel):
    """Response model for planned transaction summary."""

    total_planned: int = Field(..., description="Total planned transactions")
    income_count: int = Field(..., description="Number of income entries")
    expense_count: int = Field(..., description="Number of expense entries")
    monthly_income: Decimal = Field(..., description="Total monthly income (normalised)")
    monthly_expenses: Decimal = Field(..., description="Total monthly expenses (normalised)")
    monthly_net: Decimal = Field(..., description="Net monthly amount (income - expenses)")


class PlannedTransactionCreateRequest(BaseModel):
    """Request model for creating a planned transaction."""

    name: str = Field(..., min_length=1, max_length=100, description="Name/description")
    amount: Decimal = Field(..., description="Amount (positive = income, negative = expense)")
    currency: str = Field(default="GBP", max_length=3, description="Currency code")
    frequency: RecurringFrequency | None = Field(
        None, description="Recurrence frequency (null = one-time)"
    )
    next_expected_date: datetime | None = Field(
        None, description="When this transaction is next expected"
    )
    end_date: datetime | None = Field(None, description="When recurring transactions should stop")
    account_id: str | None = Field(None, description="Linked account UUID")
    notes: str | None = Field(None, max_length=1000, description="Optional notes")
    enabled: bool = Field(default=True, description="Whether this is active")


class PlannedTransactionUpdateRequest(BaseModel):
    """Request model for updating a planned transaction."""

    name: str | None = Field(None, min_length=1, max_length=100, description="New name")
    amount: Decimal | None = Field(None, description="New amount")
    currency: str | None = Field(None, max_length=3, description="New currency code")
    frequency: RecurringFrequency | None = Field(
        None, description="New frequency (use 'null' string to clear)"
    )
    next_expected_date: datetime | None = Field(None, description="New expected date")
    end_date: datetime | None = Field(None, description="New end date")
    account_id: str | None = Field(None, description="New account link")
    notes: str | None = Field(None, max_length=1000, description="New notes")
    enabled: bool | None = Field(None, description="Enable or disable")
    # Special flags to clear nullable fields
    clear_frequency: bool = Field(default=False, description="Set frequency to null")
    clear_end_date: bool = Field(default=False, description="Set end_date to null")
    clear_account_id: bool = Field(default=False, description="Set account_id to null")
    clear_notes: bool = Field(default=False, description="Set notes to null")
