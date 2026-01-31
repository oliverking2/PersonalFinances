"""Pydantic models for recurring pattern endpoints."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from src.postgres.common.enums import (
    RecurringDirection,
    RecurringFrequency,
    RecurringSource,
    RecurringStatus,
)

# =============================================================================
# Response Models
# =============================================================================


class RecurringPatternResponse(BaseModel):
    """Response model for a recurring pattern."""

    id: str = Field(..., description="Pattern UUID")
    name: str = Field(..., description="Display name")
    expected_amount: Decimal = Field(..., description="Expected transaction amount")
    currency: str = Field(..., description="Currency code")
    frequency: RecurringFrequency = Field(..., description="Payment frequency")
    direction: RecurringDirection = Field(..., description="Payment direction (expense/income)")
    status: RecurringStatus = Field(..., description="Pattern status")
    source: RecurringSource = Field(..., description="How pattern was created")

    # Matching rules
    merchant_contains: str | None = Field(None, description="Merchant name match string")
    amount_tolerance_pct: Decimal = Field(..., description="Amount tolerance percentage")
    advanced_rules: dict[str, Any] | None = Field(None, description="Advanced matching rules")

    # Account
    account_id: str | None = Field(None, description="Associated account UUID")

    # Timing
    next_expected_date: datetime | None = Field(None, description="Next expected payment date")
    last_matched_date: datetime | None = Field(None, description="Most recent matched transaction")
    end_date: datetime | None = Field(None, description="End date for cancelled patterns")

    # Stats
    match_count: int = Field(..., description="Number of linked transactions")
    monthly_equivalent: Decimal = Field(..., description="Amount converted to monthly equivalent")

    # Detection metadata (for detected patterns)
    confidence_score: Decimal | None = Field(None, description="Detection confidence (0.0-1.0)")
    occurrence_count: int | None = Field(None, description="Number of detected transactions")
    detection_reason: str | None = Field(None, description="Why pattern was detected")

    # User notes
    notes: str | None = Field(None, description="User notes")

    # Audit
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class RecurringPatternListResponse(BaseModel):
    """Response model for listing patterns."""

    patterns: list[RecurringPatternResponse] = Field(..., description="List of patterns")
    total: int = Field(..., description="Total number of patterns")
    monthly_total: Decimal = Field(..., description="Total monthly recurring (active only)")


class UpcomingBillResponse(BaseModel):
    """Response model for an upcoming bill."""

    id: str = Field(..., description="Pattern UUID")
    name: str = Field(..., description="Display name")
    expected_amount: Decimal = Field(..., description="Expected amount")
    currency: str = Field(..., description="Currency code")
    next_expected_date: datetime = Field(..., description="Expected date")
    frequency: RecurringFrequency = Field(..., description="Payment frequency")
    direction: RecurringDirection = Field(..., description="Payment direction")
    days_until: int = Field(..., description="Days until payment")

    model_config = {"from_attributes": True}


class UpcomingBillsResponse(BaseModel):
    """Response model for upcoming bills list."""

    upcoming: list[UpcomingBillResponse] = Field(..., description="Upcoming bills")
    total_expected: Decimal = Field(..., description="Total expected outgoing")
    date_range: dict[str, str] = Field(..., description="Date range (start and end dates)")


class RecurringSummaryResponse(BaseModel):
    """Response model for recurring pattern statistics."""

    monthly_total: Decimal = Field(..., description="Net monthly (income - expenses)")
    monthly_expenses: Decimal = Field(..., description="Total monthly recurring expenses")
    monthly_income: Decimal = Field(..., description="Total monthly recurring income")
    total_count: int = Field(..., description="Total patterns")
    expense_count: int = Field(..., description="Number of expense patterns")
    income_count: int = Field(..., description="Number of income patterns")
    active_count: int = Field(..., description="Active patterns")
    pending_count: int = Field(..., description="Pending patterns (awaiting review)")
    paused_count: int = Field(..., description="Paused patterns")


class PatternTransactionResponse(BaseModel):
    """Response model for a transaction linked to a pattern."""

    id: str = Field(..., description="Transaction UUID")
    booking_date: date | None = Field(None, description="Transaction date")
    amount: float = Field(..., description="Transaction amount")
    currency: str = Field(..., description="Currency code")
    description: str | None = Field(None, description="Transaction description")
    merchant_name: str | None = Field(None, description="Merchant name")
    is_manual: bool = Field(..., description="Whether user manually linked")


class PatternTransactionsResponse(BaseModel):
    """Response model for pattern transactions list."""

    transactions: list[PatternTransactionResponse] = Field(..., description="Linked transactions")
    total: int = Field(..., description="Total number of linked transactions")


# =============================================================================
# Request Models
# =============================================================================


class RecurringPatternCreateRequest(BaseModel):
    """Request model for creating a pattern manually."""

    name: str = Field(..., min_length=1, max_length=100, description="Display name")
    expected_amount: Decimal = Field(..., description="Expected amount")
    frequency: RecurringFrequency = Field(..., description="Payment frequency")
    direction: RecurringDirection = Field(
        default=RecurringDirection.EXPENSE, description="Income or expense"
    )
    currency: str = Field(default="GBP", max_length=3, description="Currency code")
    account_id: str | None = Field(None, description="Optional account UUID")
    merchant_contains: str | None = Field(
        None, max_length=256, description="Merchant name to match"
    )
    amount_tolerance_pct: Decimal = Field(
        default=Decimal("10.0"), ge=0, le=100, description="Amount tolerance %"
    )
    advanced_rules: dict[str, Any] | None = Field(None, description="Advanced matching rules")
    notes: str | None = Field(None, description="Notes")
    anchor_date: date | None = Field(None, description="Reference date (defaults to today)")


class RecurringPatternUpdateRequest(BaseModel):
    """Request model for updating a pattern."""

    name: str | None = Field(None, max_length=100, description="New display name")
    expected_amount: Decimal | None = Field(None, description="New expected amount")
    frequency: RecurringFrequency | None = Field(None, description="New frequency")
    notes: str | None = Field(None, description="New notes")
    merchant_contains: str | None = Field(None, max_length=256, description="New merchant match")
    amount_tolerance_pct: Decimal | None = Field(None, ge=0, le=100, description="New tolerance %")
    advanced_rules: dict[str, Any] | None = Field(None, description="New advanced rules")


class CreateFromTransactionsRequest(BaseModel):
    """Request model for creating a pattern from transactions."""

    transaction_ids: list[str] = Field(..., min_length=1, description="Transaction UUIDs to link")
    name: str = Field(..., min_length=1, max_length=100, description="Display name")
    frequency: RecurringFrequency = Field(..., description="Payment frequency")
    merchant_contains: str | None = Field(
        None, max_length=256, description="Optional merchant match"
    )
    notes: str | None = Field(None, description="Notes")


class LinkTransactionRequest(BaseModel):
    """Request model for manually linking a transaction."""

    transaction_id: str = Field(..., description="Transaction UUID to link")
