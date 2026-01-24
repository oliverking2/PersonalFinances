"""Pydantic models for transaction endpoints."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class TransactionResponse(BaseModel):
    """Response model for a transaction."""

    id: str = Field(..., description="Transaction ID")
    account_id: str = Field(..., description="Account ID")
    booking_date: date | None = Field(None, description="Booking date")
    value_date: date | None = Field(None, description="Value date")
    # Use float for JSON serialization - Decimal would serialize as string
    amount: float = Field(..., description="Transaction amount")
    currency: str = Field(..., description="Currency code")
    description: str | None = Field(None, description="Transaction description")
    merchant_name: str | None = Field(None, description="Merchant name")
    category: str | None = Field(None, description="Transaction category")


class TransactionListResponse(BaseModel):
    """Response model for listing transactions."""

    transactions: list[TransactionResponse] = Field(..., description="List of transactions")
    total: int = Field(..., description="Total number of transactions")
    page: int = Field(1, description="Current page")
    page_size: int = Field(50, description="Page size")


class TransactionQueryParams(BaseModel):
    """Query parameters for filtering transactions."""

    account_id: UUID | None = Field(None, description="Filter by account ID")
    start_date: date | None = Field(None, description="Filter from date")
    end_date: date | None = Field(None, description="Filter to date")
    min_amount: Decimal | None = Field(None, description="Minimum amount")
    max_amount: Decimal | None = Field(None, description="Maximum amount")
    search: str | None = Field(None, description="Search in description")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=100, description="Page size")
