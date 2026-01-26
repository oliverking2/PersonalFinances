"""Pydantic models for transaction endpoints."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class TransactionTagResponse(BaseModel):
    """Minimal tag info for transaction responses."""

    id: str = Field(..., description="Tag UUID")
    name: str = Field(..., description="Tag name")
    colour: str | None = Field(None, description="Hex colour code")
    is_auto: bool = Field(False, description="Whether this tag was auto-applied by a rule")
    rule_id: str | None = Field(None, description="ID of the rule that applied this tag")
    rule_name: str | None = Field(None, description="Name of the rule that applied this tag")


class TransactionSplitResponse(BaseModel):
    """Response model for a transaction split."""

    id: str = Field(..., description="Split UUID")
    tag_id: str = Field(..., description="Tag UUID")
    tag_name: str = Field(..., description="Tag name")
    tag_colour: str | None = Field(None, description="Tag hex colour code")
    amount: float = Field(..., description="Split amount (always positive)")
    is_auto: bool = Field(False, description="Whether this was auto-applied by a rule")
    rule_id: str | None = Field(None, description="ID of the rule that applied this tag")
    rule_name: str | None = Field(None, description="Name of the rule that applied this tag")


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
    user_note: str | None = Field(None, description="User-added note")
    tags: list[TransactionTagResponse] = Field(
        default_factory=list, description="User-defined tags"
    )
    splits: list[TransactionSplitResponse] = Field(
        default_factory=list, description="Transaction splits for budgeting"
    )


class TransactionListResponse(BaseModel):
    """Response model for listing transactions."""

    transactions: list[TransactionResponse] = Field(..., description="List of transactions")
    total: int = Field(..., description="Total number of transactions")
    page: int = Field(1, description="Current page")
    page_size: int = Field(50, description="Page size")


class TransactionQueryParams(BaseModel):
    """Query parameters for filtering transactions.

    Note: account_ids and tag_ids are defined as separate Query params
    in the endpoint because FastAPI doesn't correctly parse list params
    when using Query() inside a Pydantic model with Depends().
    """

    start_date: date | None = Field(None, description="Filter from date")
    end_date: date | None = Field(None, description="Filter to date")
    min_amount: Decimal | None = Field(None, description="Minimum amount")
    max_amount: Decimal | None = Field(None, description="Maximum amount")
    search: str | None = Field(None, description="Search in description")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=100, description="Page size")


class TransactionTagsRequest(BaseModel):
    """Request model for adding tags to a transaction."""

    tag_ids: list[str] = Field(..., min_length=1, description="List of tag UUIDs to add")


class TransactionTagsResponse(BaseModel):
    """Response model after modifying transaction tags."""

    transaction_id: str = Field(..., description="Transaction UUID")
    tags: list[TransactionTagResponse] = Field(..., description="Tags on this transaction")


class BulkTagRequest(BaseModel):
    """Request model for bulk tagging transactions."""

    transaction_ids: list[str] = Field(..., min_length=1, description="Transaction UUIDs")
    add_tag_ids: list[str] = Field(default_factory=list, description="Tags to add")
    remove_tag_ids: list[str] = Field(default_factory=list, description="Tags to remove")


class BulkTagResponse(BaseModel):
    """Response model for bulk tagging."""

    updated_count: int = Field(..., description="Number of transactions updated")


# -----------------------------------------------------------------------------
# Split Models
# -----------------------------------------------------------------------------


class SplitRequest(BaseModel):
    """Request model for a single split."""

    tag_id: str = Field(..., description="Tag UUID")
    amount: float = Field(..., gt=0, description="Split amount (must be positive)")


class SetSplitsRequest(BaseModel):
    """Request model for setting transaction splits."""

    splits: list[SplitRequest] = Field(
        ..., min_length=1, description="List of splits (must sum to transaction amount)"
    )


class TransactionSplitsResponse(BaseModel):
    """Response model for transaction splits."""

    transaction_id: str = Field(..., description="Transaction UUID")
    splits: list[TransactionSplitResponse] = Field(..., description="Transaction splits")


class UpdateNoteRequest(BaseModel):
    """Request model for updating transaction note."""

    user_note: str | None = Field(None, max_length=512, description="User note (null to clear)")
