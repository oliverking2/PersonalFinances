"""Pydantic models for account endpoints."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from src.postgres.common.enums import AccountStatus


class AccountBalance(BaseModel):
    """Balance information for an account."""

    amount: Decimal = Field(..., description="Balance amount")
    currency: str = Field(..., description="Currency code")
    type: str = Field(..., description="Balance type")


class AccountResponse(BaseModel):
    """Response model for a bank account."""

    id: str = Field(..., description="Account UUID")
    connection_id: str = Field(..., description="Parent connection UUID")
    display_name: str | None = Field(None, description="User-editable display name")
    name: str | None = Field(None, description="Provider-sourced account name")
    iban: str | None = Field(None, description="IBAN")
    currency: str | None = Field(None, description="Currency code")
    status: AccountStatus = Field(..., description="Account status")
    balance: AccountBalance | None = Field(None, description="Current balance")
    last_synced_at: datetime | None = Field(None, description="Last data sync timestamp")

    model_config = {"from_attributes": True}


class AccountListResponse(BaseModel):
    """Response model for listing accounts."""

    accounts: list[AccountResponse] = Field(..., description="List of accounts")
    total: int = Field(..., description="Total number of accounts")


class AccountUpdateRequest(BaseModel):
    """Request model for updating an account."""

    display_name: str | None = Field(None, max_length=128, description="New display name")
