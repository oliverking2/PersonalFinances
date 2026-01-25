"""Pydantic models for tag endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class TagResponse(BaseModel):
    """Response model for a tag."""

    id: str = Field(..., description="Tag UUID")
    name: str = Field(..., description="Tag name")
    colour: str | None = Field(None, description="Hex colour code (e.g., #10B981)")
    usage_count: int = Field(0, description="Number of transactions with this tag")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class TagListResponse(BaseModel):
    """Response model for listing tags."""

    tags: list[TagResponse] = Field(..., description="List of tags")
    total: int = Field(..., description="Total number of tags")


class TagCreateRequest(BaseModel):
    """Request model for creating a tag."""

    name: str = Field(..., min_length=1, max_length=50, description="Tag name")
    colour: str | None = Field(
        None,
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Hex colour code (e.g., #10B981)",
    )


class TagUpdateRequest(BaseModel):
    """Request model for updating a tag."""

    name: str | None = Field(None, min_length=1, max_length=50, description="New tag name")
    colour: str | None = Field(
        None,
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="New hex colour code",
    )


class TransactionTagsRequest(BaseModel):
    """Request model for adding tags to a transaction."""

    tag_ids: list[str] = Field(..., min_length=1, description="List of tag UUIDs to add")


class TransactionTagsResponse(BaseModel):
    """Response model for transaction tags."""

    transaction_id: str = Field(..., description="Transaction UUID")
    tags: list[TagResponse] = Field(..., description="Tags on this transaction")


class BulkTagRequest(BaseModel):
    """Request model for bulk tagging transactions."""

    transaction_ids: list[str] = Field(..., min_length=1, description="Transaction UUIDs")
    add_tag_ids: list[str] = Field(default_factory=list, description="Tags to add")
    remove_tag_ids: list[str] = Field(default_factory=list, description="Tags to remove")


class BulkTagResponse(BaseModel):
    """Response model for bulk tagging."""

    updated_count: int = Field(..., description="Number of transactions updated")
