"""Pydantic models for institution endpoints."""

from pydantic import BaseModel, Field

from src.postgres.common.enums import Provider


class InstitutionResponse(BaseModel):
    """Response model for an institution."""

    id: str = Field(..., description="Institution ID (provider-specific)")
    provider: Provider = Field(..., description="Data provider")
    name: str = Field(..., description="Institution name")
    logo_url: str | None = Field(None, description="URL to institution logo")
    countries: list[str] | None = Field(None, description="Supported country codes")

    model_config = {"from_attributes": True}


class InstitutionListResponse(BaseModel):
    """Response model for listing institutions."""

    institutions: list[InstitutionResponse] = Field(..., description="List of institutions")
    total: int = Field(..., description="Total number of institutions")
