"""Pydantic models for connection endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class ConnectionResponse(BaseModel):
    """Response model for a bank connection (requisition)."""

    id: str = Field(..., description="Requisition ID")
    institution_id: str = Field(..., description="Institution ID")
    status: str = Field(..., description="Connection status")
    friendly_name: str = Field(..., description="User-friendly name")
    created: datetime = Field(..., description="Creation timestamp")
    link: str = Field(..., description="Authorization link")
    account_count: int = Field(0, description="Number of linked accounts")
    expired: bool = Field(False, description="Whether the connection has expired")

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

    id: str = Field(..., description="Requisition ID")
    link: str = Field(..., description="Authorization link to redirect user to")
