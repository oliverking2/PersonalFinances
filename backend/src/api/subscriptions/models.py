"""Pydantic models for subscription endpoints."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from src.postgres.common.enums import RecurringFrequency, RecurringStatus


class SubscriptionResponse(BaseModel):
    """Response model for a subscription/recurring pattern."""

    id: str = Field(..., description="Pattern UUID")
    merchant_pattern: str = Field(..., description="Normalised merchant name")
    display_name: str = Field(..., description="User-friendly display name")
    expected_amount: Decimal = Field(..., description="Expected transaction amount")
    currency: str = Field(..., description="Currency code")
    frequency: RecurringFrequency = Field(..., description="Payment frequency")
    status: RecurringStatus = Field(..., description="Pattern status")
    confidence_score: Decimal = Field(..., description="Detection confidence (0.0-1.0)")
    occurrence_count: int = Field(..., description="Number of matched transactions")
    account_id: str | None = Field(None, description="Associated account UUID")
    notes: str | None = Field(None, description="User notes")
    last_occurrence_date: datetime | None = Field(None, description="Most recent transaction date")
    next_expected_date: datetime | None = Field(None, description="Next expected payment date")
    monthly_equivalent: Decimal = Field(..., description="Amount converted to monthly equivalent")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class SubscriptionListResponse(BaseModel):
    """Response model for listing subscriptions."""

    subscriptions: list[SubscriptionResponse] = Field(..., description="List of subscriptions")
    total: int = Field(..., description="Total number of subscriptions")
    monthly_total: Decimal = Field(..., description="Total monthly recurring spend")


class SubscriptionCreateRequest(BaseModel):
    """Request model for creating a subscription manually."""

    merchant_pattern: str = Field(
        ..., min_length=1, max_length=256, description="Merchant name/pattern"
    )
    expected_amount: Decimal = Field(..., description="Expected amount (negative)")
    frequency: RecurringFrequency = Field(..., description="Payment frequency")
    currency: str = Field(default="GBP", max_length=3, description="Currency code")
    account_id: str | None = Field(None, description="Optional account UUID")
    display_name: str | None = Field(None, max_length=100, description="Display name override")
    notes: str | None = Field(None, description="Notes")
    anchor_date: date | None = Field(None, description="Reference date (defaults to today)")


class SubscriptionUpdateRequest(BaseModel):
    """Request model for updating a subscription."""

    status: RecurringStatus | None = Field(None, description="New status")
    display_name: str | None = Field(None, max_length=100, description="New display name")
    notes: str | None = Field(None, description="New notes")
    expected_amount: Decimal | None = Field(None, description="New expected amount")
    frequency: RecurringFrequency | None = Field(None, description="New frequency")


class UpcomingBillResponse(BaseModel):
    """Response model for an upcoming bill."""

    id: str = Field(..., description="Pattern UUID")
    display_name: str = Field(..., description="Display name")
    merchant_pattern: str = Field(..., description="Merchant pattern")
    expected_amount: Decimal = Field(..., description="Expected amount")
    currency: str = Field(..., description="Currency code")
    next_expected_date: datetime = Field(..., description="Expected date")
    frequency: RecurringFrequency = Field(..., description="Payment frequency")
    confidence_score: Decimal = Field(..., description="Confidence score")
    status: RecurringStatus = Field(..., description="Pattern status")
    days_until: int = Field(..., description="Days until payment")

    model_config = {"from_attributes": True}


class UpcomingBillsResponse(BaseModel):
    """Response model for upcoming bills list."""

    upcoming: list[UpcomingBillResponse] = Field(..., description="Upcoming bills")
    total_expected: Decimal = Field(..., description="Total expected outgoing")
    date_range: dict[str, str] = Field(..., description="Date range (start and end dates)")


class SubscriptionSummaryResponse(BaseModel):
    """Response model for subscription statistics."""

    monthly_total: Decimal = Field(..., description="Total monthly recurring spend")
    total_count: int = Field(..., description="Total subscriptions")
    confirmed_count: int = Field(..., description="Confirmed subscriptions")
    detected_count: int = Field(..., description="Detected (unconfirmed) subscriptions")
    paused_count: int = Field(..., description="Paused subscriptions")


class SubscriptionTransactionResponse(BaseModel):
    """Response model for a transaction linked to a subscription."""

    id: str = Field(..., description="Transaction UUID")
    booking_date: date | None = Field(None, description="Transaction date")
    amount: float = Field(..., description="Transaction amount")
    currency: str = Field(..., description="Currency code")
    description: str | None = Field(None, description="Transaction description")
    merchant_name: str | None = Field(None, description="Merchant name")


class SubscriptionTransactionsResponse(BaseModel):
    """Response model for subscription transactions list."""

    transactions: list[SubscriptionTransactionResponse] = Field(
        ..., description="Linked transactions"
    )
    total: int = Field(..., description="Total number of linked transactions")
