"""Trading 212 API models."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class AddT212ConnectionRequest(BaseModel):
    """Request to add a new Trading 212 connection."""

    api_key: str = Field(..., min_length=1, description="Trading 212 API key")
    friendly_name: str = Field(
        ..., min_length=1, max_length=128, description="User-provided name for this connection"
    )


class T212ConnectionResponse(BaseModel):
    """Trading 212 connection response."""

    id: str = Field(..., description="API key record ID")
    friendly_name: str = Field(..., description="User-provided name")
    t212_account_id: str | None = Field(None, description="Trading 212 account ID")
    currency_code: str | None = Field(None, description="Account base currency")
    status: str = Field(..., description="Connection status (active/error)")
    error_message: str | None = Field(None, description="Error message if status is error")
    last_synced_at: datetime | None = Field(None, description="Last successful sync timestamp")
    created_at: datetime = Field(..., description="When the connection was created")

    model_config = {"from_attributes": True}


class T212ConnectionListResponse(BaseModel):
    """List of Trading 212 connections."""

    connections: list[T212ConnectionResponse]
    total: int


class T212CashBalanceResponse(BaseModel):
    """Trading 212 cash balance response."""

    free: Decimal = Field(..., description="Free cash available")
    blocked: Decimal = Field(..., description="Cash blocked by orders")
    invested: Decimal = Field(..., description="Cash invested in positions")
    pie_cash: Decimal = Field(..., description="Cash in pies")
    ppl: Decimal = Field(..., description="Unrealised profit/loss")
    result: Decimal = Field(..., description="Realised profit/loss")
    total: Decimal = Field(..., description="Total account value")
    fetched_at: datetime = Field(..., description="When balance was fetched")

    model_config = {"from_attributes": True}
