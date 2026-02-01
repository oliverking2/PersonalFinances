"""Pydantic models for manual assets endpoints."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from src.postgres.common.enums import ManualAssetType


class ManualAssetResponse(BaseModel):
    """Response model for a manual asset."""

    id: str = Field(..., description="Asset UUID")
    asset_type: ManualAssetType = Field(..., description="Type of asset")
    custom_type: str | None = Field(None, description="Custom type label")
    display_type: str = Field(..., description="Display name for the asset type")
    is_liability: bool = Field(..., description="Whether this counts against net worth")
    name: str = Field(..., description="Asset name")
    notes: str | None = Field(None, description="User notes")
    current_value: float = Field(..., description="Current value")
    currency: str = Field(..., description="Currency code")
    interest_rate: float | None = Field(None, description="Interest rate (for loans)")
    acquisition_date: datetime | None = Field(None, description="When the asset was acquired")
    acquisition_value: float | None = Field(None, description="Original purchase price")
    is_active: bool = Field(..., description="Whether the asset is active")
    value_updated_at: datetime = Field(..., description="When the value was last updated")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class ManualAssetListResponse(BaseModel):
    """Response model for listing manual assets."""

    assets: list[ManualAssetResponse] = Field(..., description="List of manual assets")
    total: int = Field(..., description="Total number of assets")


class ManualAssetSummaryResponse(BaseModel):
    """Response model for manual assets summary."""

    total_assets: float = Field(..., description="Sum of all asset values")
    total_liabilities: float = Field(..., description="Sum of all liability values")
    net_impact: float = Field(..., description="Net impact on net worth (assets - liabilities)")
    asset_count: int = Field(..., description="Number of active assets")
    liability_count: int = Field(..., description="Number of active liabilities")


class ManualAssetCreateRequest(BaseModel):
    """Request model for creating a manual asset."""

    name: str = Field(..., min_length=1, max_length=100, description="Asset name")
    asset_type: ManualAssetType = Field(..., description="Type of asset")
    current_value: Decimal = Field(..., ge=0, description="Current value")
    custom_type: str | None = Field(
        None, max_length=50, description="Custom type label (e.g., 'My Honda Civic')"
    )
    is_liability: bool | None = Field(None, description="Override default liability classification")
    currency: str = Field(default="GBP", max_length=3, description="Currency code")
    notes: str | None = Field(None, description="User notes")
    interest_rate: Decimal | None = Field(
        None, ge=0, le=100, description="Interest rate (for loans/mortgages)"
    )
    acquisition_date: date | None = Field(None, description="When the asset was acquired")
    acquisition_value: Decimal | None = Field(None, ge=0, description="Original purchase price")


class ManualAssetUpdateRequest(BaseModel):
    """Request model for updating a manual asset."""

    name: str | None = Field(None, min_length=1, max_length=100, description="New name")
    custom_type: str | None = Field(None, max_length=50, description="New custom type label")
    is_liability: bool | None = Field(None, description="New liability status")
    notes: str | None = Field(None, description="New notes")
    interest_rate: Decimal | None = Field(None, ge=0, le=100, description="New interest rate")
    acquisition_date: date | None = Field(None, description="New acquisition date")
    acquisition_value: Decimal | None = Field(None, ge=0, description="New acquisition value")
    # Clear flags for optional fields
    clear_custom_type: bool = Field(default=False, description="Clear the custom type")
    clear_notes: bool = Field(default=False, description="Clear notes")
    clear_interest_rate: bool = Field(default=False, description="Clear interest rate")
    clear_acquisition_date: bool = Field(default=False, description="Clear acquisition date")
    clear_acquisition_value: bool = Field(default=False, description="Clear acquisition value")


class ValueUpdateRequest(BaseModel):
    """Request model for updating an asset's value."""

    new_value: Decimal = Field(..., ge=0, description="New current value")
    notes: str | None = Field(None, max_length=500, description="Reason for the value change")


class ValueSnapshotResponse(BaseModel):
    """Response model for a value history snapshot."""

    id: int = Field(..., description="Snapshot ID")
    value: float = Field(..., description="Value at this point")
    currency: str = Field(..., description="Currency code")
    notes: str | None = Field(None, description="Note about the value change")
    captured_at: datetime = Field(..., description="When this snapshot was captured")

    model_config = {"from_attributes": True}


class ValueHistoryResponse(BaseModel):
    """Response model for asset value history."""

    asset_id: str = Field(..., description="Asset UUID")
    snapshots: list[ValueSnapshotResponse] = Field(..., description="Value history snapshots")
    total: int = Field(..., description="Total number of snapshots")
