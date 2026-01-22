"""Pydantic models for account endpoints."""

from datetime import date

from pydantic import BaseModel, Field


class AccountResponse(BaseModel):
    """Response model for a bank account."""

    id: str = Field(..., description="Unique account identifier")
    name: str | None = Field(None, description="Account name")
    display_name: str | None = Field(None, description="Display name")
    iban: str | None = Field(None, description="IBAN")
    currency: str | None = Field(None, description="Currency code")
    owner_name: str | None = Field(None, description="Account owner name")
    status: str | None = Field(None, description="Account status")
    product: str | None = Field(None, description="Product type")
    requisition_id: str | None = Field(None, description="Associated requisition ID")
    transaction_extract_date: date | None = Field(
        None, description="Last transaction extraction date"
    )

    model_config = {"from_attributes": True}


class AccountListResponse(BaseModel):
    """Response model for listing accounts."""

    accounts: list[AccountResponse] = Field(..., description="List of accounts")
    total: int = Field(..., description="Total number of accounts")


class AccountUpdateRequest(BaseModel):
    """Request model for updating an account."""

    display_name: str | None = Field(None, description="New display name")
