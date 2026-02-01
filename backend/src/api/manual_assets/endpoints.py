"""Manual assets API endpoints."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
from src.api.manual_assets.models import (
    ManualAssetCreateRequest,
    ManualAssetListResponse,
    ManualAssetResponse,
    ManualAssetSummaryResponse,
    ManualAssetUpdateRequest,
    ValueHistoryResponse,
    ValueSnapshotResponse,
    ValueUpdateRequest,
)
from src.api.responses import BAD_REQUEST, RESOURCE_RESPONSES, UNAUTHORIZED
from src.postgres.auth.models import User
from src.postgres.common.models import ManualAsset
from src.postgres.common.operations.manual_assets import (
    create_manual_asset,
    delete_manual_asset,
    get_manual_asset_by_id,
    get_manual_asset_value_history,
    get_manual_assets_by_user_id,
    get_manual_assets_summary,
    update_manual_asset,
    update_manual_asset_value,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=ManualAssetListResponse,
    summary="List manual assets",
    responses=UNAUTHORIZED,
)
def list_manual_assets(
    include_inactive: bool = False,
    is_liability: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ManualAssetListResponse:
    """List all manual assets for the authenticated user."""
    assets = get_manual_assets_by_user_id(
        db,
        current_user.id,
        include_inactive=include_inactive,
        is_liability=is_liability,
    )

    return ManualAssetListResponse(
        assets=[_to_response(a) for a in assets],
        total=len(assets),
    )


@router.get(
    "/summary",
    response_model=ManualAssetSummaryResponse,
    summary="Get manual assets summary",
    responses=UNAUTHORIZED,
)
def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ManualAssetSummaryResponse:
    """Get summary totals for manual assets (assets, liabilities, net impact)."""
    summary = get_manual_assets_summary(db, current_user.id)

    # Get counts
    assets = get_manual_assets_by_user_id(db, current_user.id, include_inactive=False)
    asset_count = sum(1 for a in assets if not a.is_liability)
    liability_count = sum(1 for a in assets if a.is_liability)

    return ManualAssetSummaryResponse(
        total_assets=float(summary["total_assets"]),
        total_liabilities=float(summary["total_liabilities"]),
        net_impact=float(summary["net_impact"]),
        asset_count=asset_count,
        liability_count=liability_count,
    )


@router.post(
    "",
    response_model=ManualAssetResponse,
    status_code=201,
    summary="Create manual asset",
    responses={**UNAUTHORIZED, **BAD_REQUEST},
)
def create_manual_asset_endpoint(
    request: ManualAssetCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ManualAssetResponse:
    """Create a new manual asset or liability."""
    acquisition_date = None
    if request.acquisition_date:
        acquisition_date = datetime.combine(
            request.acquisition_date, datetime.min.time(), tzinfo=UTC
        )

    asset = create_manual_asset(
        db,
        user_id=current_user.id,
        name=request.name,
        asset_type=request.asset_type,
        current_value=request.current_value,
        custom_type=request.custom_type,
        is_liability=request.is_liability,
        currency=request.currency,
        notes=request.notes,
        interest_rate=request.interest_rate,
        acquisition_date=acquisition_date,
        acquisition_value=request.acquisition_value,
    )

    db.commit()
    db.refresh(asset)
    logger.info(f"Created manual asset: id={asset.id}, type={asset.asset_type}, name={asset.name}")
    return _to_response(asset)


@router.get(
    "/{asset_id}",
    response_model=ManualAssetResponse,
    summary="Get manual asset by ID",
    responses=RESOURCE_RESPONSES,
)
def get_manual_asset(
    asset_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ManualAssetResponse:
    """Retrieve a specific manual asset by its UUID."""
    asset = get_manual_asset_by_id(db, asset_id)
    if not asset or asset.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Asset not found: {asset_id}")

    return _to_response(asset)


@router.patch(
    "/{asset_id}",
    response_model=ManualAssetResponse,
    summary="Update manual asset",
    responses=RESOURCE_RESPONSES,
)
def update_manual_asset_endpoint(
    asset_id: UUID,
    request: ManualAssetUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ManualAssetResponse:
    """Update a manual asset's details (not value - use /update-value for that)."""
    asset = get_manual_asset_by_id(db, asset_id)
    if not asset or asset.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Asset not found: {asset_id}")

    # Build update kwargs
    # Handle custom_type
    custom_type = asset.custom_type
    if request.clear_custom_type:
        custom_type = None
    elif request.custom_type is not None:
        custom_type = request.custom_type

    # Handle notes
    notes = asset.notes
    if request.clear_notes:
        notes = None
    elif request.notes is not None:
        notes = request.notes

    # Handle interest_rate
    interest_rate = asset.interest_rate
    if request.clear_interest_rate:
        interest_rate = None
    elif request.interest_rate is not None:
        interest_rate = request.interest_rate

    # Handle acquisition_date
    acquisition_date = asset.acquisition_date
    if request.clear_acquisition_date:
        acquisition_date = None
    elif request.acquisition_date is not None:
        acquisition_date = datetime.combine(
            request.acquisition_date, datetime.min.time(), tzinfo=UTC
        )

    # Handle acquisition_value
    acquisition_value = asset.acquisition_value
    if request.clear_acquisition_value:
        acquisition_value = None
    elif request.acquisition_value is not None:
        acquisition_value = request.acquisition_value

    updated = update_manual_asset(
        db,
        asset_id,
        name=request.name,
        custom_type=custom_type,
        is_liability=request.is_liability,
        notes=notes,
        interest_rate=interest_rate,
        acquisition_date=acquisition_date,
        acquisition_value=acquisition_value,
    )

    if not updated:
        raise HTTPException(status_code=404, detail=f"Asset not found: {asset_id}")

    db.commit()
    db.refresh(updated)
    logger.info(f"Updated manual asset: id={asset_id}")
    return _to_response(updated)


@router.post(
    "/{asset_id}/update-value",
    response_model=ManualAssetResponse,
    summary="Update asset value",
    responses=RESOURCE_RESPONSES,
)
def update_value_endpoint(
    asset_id: UUID,
    request: ValueUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ManualAssetResponse:
    """Update a manual asset's current value and record the change in history."""
    asset = get_manual_asset_by_id(db, asset_id)
    if not asset or asset.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Asset not found: {asset_id}")

    updated = update_manual_asset_value(
        db,
        asset_id,
        new_value=request.new_value,
        notes=request.notes,
    )

    if not updated:
        raise HTTPException(status_code=404, detail=f"Asset not found: {asset_id}")

    db.commit()
    db.refresh(updated)
    logger.info(f"Updated manual asset value: id={asset_id}, new_value={request.new_value}")
    return _to_response(updated)


@router.get(
    "/{asset_id}/history",
    response_model=ValueHistoryResponse,
    summary="Get value history",
    responses=RESOURCE_RESPONSES,
)
def get_value_history(
    asset_id: UUID,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ValueHistoryResponse:
    """Get the value history for a manual asset."""
    asset = get_manual_asset_by_id(db, asset_id)
    if not asset or asset.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Asset not found: {asset_id}")

    snapshots = get_manual_asset_value_history(db, asset_id, limit=limit)

    return ValueHistoryResponse(
        asset_id=str(asset_id),
        snapshots=[
            ValueSnapshotResponse(
                id=s.id,
                value=float(s.value),
                currency=s.currency,
                notes=s.notes,
                captured_at=s.captured_at,
            )
            for s in snapshots
        ],
        total=len(snapshots),
    )


@router.delete(
    "/{asset_id}",
    status_code=204,
    summary="Delete manual asset",
    responses=RESOURCE_RESPONSES,
)
def delete_manual_asset_endpoint(
    asset_id: UUID,
    hard_delete: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a manual asset (soft delete by default)."""
    asset = get_manual_asset_by_id(db, asset_id)
    if not asset or asset.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Asset not found: {asset_id}")

    deleted = delete_manual_asset(db, asset_id, hard_delete=hard_delete)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Asset not found: {asset_id}")

    db.commit()
    logger.info(f"Deleted manual asset: id={asset_id}, hard_delete={hard_delete}")


def _to_response(asset: ManualAsset) -> ManualAssetResponse:
    """Convert a ManualAsset model to API response.

    :param asset: Database model.
    :returns: API response model.
    """
    return ManualAssetResponse(
        id=str(asset.id),
        asset_type=asset.asset_type_enum,
        custom_type=asset.custom_type,
        display_type=asset.display_type,
        is_liability=asset.is_liability,
        name=asset.name,
        notes=asset.notes,
        current_value=float(asset.current_value),
        currency=asset.currency,
        interest_rate=float(asset.interest_rate) if asset.interest_rate is not None else None,
        acquisition_date=asset.acquisition_date,
        acquisition_value=float(asset.acquisition_value) if asset.acquisition_value else None,
        is_active=asset.is_active,
        value_updated_at=asset.value_updated_at,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )
