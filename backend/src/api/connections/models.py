"""Pydantic models for connection endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field

from src.postgres.common.enums import ConnectionStatus, Provider


class InstitutionResponse(BaseModel):
    """Nested institution details within a connection."""

    id: str = Field(..., description="Institution ID")
    name: str = Field(..., description="Institution name")
    logo_url: str | None = Field(None, description="URL to institution logo")


class ConnectionResponse(BaseModel):
    """Response model for a bank connection."""

    id: str = Field(..., description="Connection UUID")
    friendly_name: str = Field(..., description="User-friendly name")
    provider: Provider = Field(..., description="Data provider")
    institution: InstitutionResponse = Field(..., description="Institution details")
    status: ConnectionStatus = Field(..., description="Connection status")
    account_count: int = Field(0, description="Number of linked accounts")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: datetime | None = Field(None, description="Expiration timestamp")

    model_config = {"from_attributes": True}


class ConnectionListResponse(BaseModel):
    """Response model for listing connections."""

    connections: list[ConnectionResponse] = Field(..., description="List of connections")
    total: int = Field(..., description="Total number of connections")


class CreateConnectionRequest(BaseModel):
    """Request model for creating a new connection."""

    institution_id: str = Field(..., description="Institution ID to connect to")
    friendly_name: str = Field(..., min_length=1, max_length=128, description="Friendly name")


class CreateConnectionResponse(BaseModel):
    """Response model for connection creation."""

    id: str = Field(..., description="Connection UUID")
    link: str = Field(..., description="Authorisation link to redirect user to")


class UpdateConnectionRequest(BaseModel):
    """Request model for updating a connection."""

    friendly_name: str = Field(..., min_length=1, max_length=128, description="New friendly name")


class ReauthoriseConnectionResponse(BaseModel):
    """Response model for connection reauthorisation."""

    id: str = Field(..., description="Connection UUID")
    link: str = Field(..., description="Reauthorisation link")
