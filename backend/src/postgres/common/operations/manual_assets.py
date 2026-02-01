"""Manual asset database operations.

This module provides CRUD operations for ManualAsset and ManualAssetValueSnapshot entities.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from src.postgres.common.enums import ManualAssetType, get_default_is_liability
from src.postgres.common.models import ManualAsset, ManualAssetValueSnapshot

logger = logging.getLogger(__name__)


def get_manual_asset_by_id(session: Session, asset_id: UUID) -> ManualAsset | None:
    """Get a manual asset by its ID.

    :param session: SQLAlchemy session.
    :param asset_id: Asset's UUID.
    :return: ManualAsset if found, None otherwise.
    """
    return session.get(ManualAsset, asset_id)


def get_manual_assets_by_user_id(
    session: Session,
    user_id: UUID,
    *,
    include_inactive: bool = False,
    is_liability: bool | None = None,
) -> list[ManualAsset]:
    """Get all manual assets for a user.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param include_inactive: Include soft-deleted assets.
    :param is_liability: Filter by liability status (None for all).
    :return: List of assets ordered by creation date descending.
    """
    query = session.query(ManualAsset).filter(ManualAsset.user_id == user_id)

    if not include_inactive:
        query = query.filter(ManualAsset.is_active.is_(True))

    if is_liability is not None:
        query = query.filter(ManualAsset.is_liability == is_liability)

    return query.order_by(ManualAsset.created_at.desc()).all()


def get_manual_assets_summary(
    session: Session,
    user_id: UUID,
) -> dict[str, Decimal]:
    """Get summary totals for a user's manual assets.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :return: Dictionary with total_assets, total_liabilities, and net_impact.
    """
    assets = get_manual_assets_by_user_id(session, user_id, include_inactive=False)

    total_assets = Decimal("0")
    total_liabilities = Decimal("0")

    for asset in assets:
        if asset.is_liability:
            total_liabilities += asset.current_value
        else:
            total_assets += asset.current_value

    return {
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_impact": total_assets - total_liabilities,
    }


def create_manual_asset(
    session: Session,
    user_id: UUID,
    name: str,
    asset_type: ManualAssetType,
    current_value: Decimal,
    *,
    custom_type: str | None = None,
    is_liability: bool | None = None,
    currency: str = "GBP",
    notes: str | None = None,
    interest_rate: Decimal | None = None,
    acquisition_date: datetime | None = None,
    acquisition_value: Decimal | None = None,
) -> ManualAsset:
    """Create a new manual asset.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param name: Asset display name.
    :param asset_type: Type of asset (from ManualAssetType enum).
    :param current_value: Current value of the asset.
    :param custom_type: Custom type label (e.g., "My Honda Civic" instead of "Vehicle").
    :param is_liability: Whether this counts against net worth (defaults based on type).
    :param currency: Currency code (default GBP).
    :param notes: Optional notes about the asset.
    :param interest_rate: Optional interest rate (for loans/mortgages).
    :param acquisition_date: When the asset was acquired.
    :param acquisition_value: Original purchase price.
    :return: Created ManualAsset entity.
    """
    # Determine is_liability from type if not explicitly provided
    if is_liability is None:
        is_liability = get_default_is_liability(asset_type)

    now = datetime.now(UTC)

    asset = ManualAsset(
        user_id=user_id,
        name=name[:100],
        asset_type=asset_type.value,
        custom_type=custom_type[:50] if custom_type else None,
        is_liability=is_liability,
        current_value=current_value,
        currency=currency,
        notes=notes,
        interest_rate=interest_rate,
        acquisition_date=acquisition_date,
        acquisition_value=acquisition_value,
        is_active=True,
        value_updated_at=now,
    )
    session.add(asset)
    session.flush()

    # Create initial value snapshot
    snapshot = ManualAssetValueSnapshot(
        asset_id=asset.id,
        value=current_value,
        currency=currency,
        notes="Initial value",
        captured_at=now,
    )
    session.add(snapshot)
    session.flush()

    logger.info(
        f"Created manual asset: id={asset.id}, user_id={user_id}, "
        f"type={asset_type.value}, name={name}"
    )
    return asset


_NOT_SET = object()


def update_manual_asset(
    session: Session,
    asset_id: UUID,
    *,
    name: str | None = None,
    custom_type: str | None | object = _NOT_SET,
    is_liability: bool | None = None,
    notes: str | None | object = _NOT_SET,
    interest_rate: Decimal | None | object = _NOT_SET,
    acquisition_date: datetime | None | object = _NOT_SET,
    acquisition_value: Decimal | None | object = _NOT_SET,
) -> ManualAsset | None:
    """Update a manual asset's details (not value - use update_manual_asset_value for that).

    :param session: SQLAlchemy session.
    :param asset_id: Asset's UUID.
    :param name: New asset name.
    :param custom_type: New custom type label (pass None to clear).
    :param is_liability: New liability status.
    :param notes: New notes (pass None to clear).
    :param interest_rate: New interest rate (pass None to clear).
    :param acquisition_date: New acquisition date (pass None to clear).
    :param acquisition_value: New acquisition value (pass None to clear).
    :return: Updated ManualAsset, or None if not found.
    """
    asset = get_manual_asset_by_id(session, asset_id)
    if asset is None:
        return None

    if name is not None:
        asset.name = name[:100]

    if custom_type is not _NOT_SET:
        asset.custom_type = custom_type[:50] if isinstance(custom_type, str) else None

    if is_liability is not None:
        asset.is_liability = is_liability

    if notes is not _NOT_SET:
        asset.notes = notes if isinstance(notes, str) else None

    if interest_rate is not _NOT_SET:
        asset.interest_rate = interest_rate if isinstance(interest_rate, Decimal) else None

    if acquisition_date is not _NOT_SET:
        asset.acquisition_date = (
            acquisition_date if isinstance(acquisition_date, datetime) else None
        )

    if acquisition_value is not _NOT_SET:
        asset.acquisition_value = (
            acquisition_value if isinstance(acquisition_value, Decimal) else None
        )

    session.flush()
    logger.info(f"Updated manual asset: id={asset_id}")
    return asset


def update_manual_asset_value(
    session: Session,
    asset_id: UUID,
    new_value: Decimal,
    *,
    notes: str | None = None,
) -> ManualAsset | None:
    """Update a manual asset's value and create a history snapshot.

    :param session: SQLAlchemy session.
    :param asset_id: Asset's UUID.
    :param new_value: New current value.
    :param notes: Optional note explaining the value change.
    :return: Updated ManualAsset, or None if not found.
    """
    asset = get_manual_asset_by_id(session, asset_id)
    if asset is None:
        return None

    now = datetime.now(UTC)

    # Update the asset value
    asset.current_value = new_value
    asset.value_updated_at = now

    # Create value snapshot
    snapshot = ManualAssetValueSnapshot(
        asset_id=asset.id,
        value=new_value,
        currency=asset.currency,
        notes=notes,
        captured_at=now,
    )
    session.add(snapshot)

    session.flush()
    logger.info(f"Updated manual asset value: id={asset_id}, new_value={new_value}")
    return asset


def get_manual_asset_value_history(
    session: Session,
    asset_id: UUID,
    *,
    limit: int = 100,
) -> list[ManualAssetValueSnapshot]:
    """Get the value history for a manual asset.

    :param session: SQLAlchemy session.
    :param asset_id: Asset's UUID.
    :param limit: Maximum number of snapshots to return.
    :return: List of snapshots ordered by captured_at descending (most recent first).
    """
    return (
        session.query(ManualAssetValueSnapshot)
        .filter(ManualAssetValueSnapshot.asset_id == asset_id)
        .order_by(ManualAssetValueSnapshot.captured_at.desc())
        .limit(limit)
        .all()
    )


def delete_manual_asset(
    session: Session,
    asset_id: UUID,
    *,
    hard_delete: bool = False,
) -> bool:
    """Delete a manual asset (soft delete by default).

    :param session: SQLAlchemy session.
    :param asset_id: Asset's UUID.
    :param hard_delete: If True, permanently delete the asset and its history.
    :return: True if deleted, False if not found.
    """
    asset = get_manual_asset_by_id(session, asset_id)
    if asset is None:
        return False

    if hard_delete:
        session.delete(asset)
        logger.info(f"Hard deleted manual asset: id={asset_id}")
    else:
        asset.is_active = False
        logger.info(f"Soft deleted manual asset: id={asset_id}")

    session.flush()
    return True


def restore_manual_asset(
    session: Session,
    asset_id: UUID,
) -> ManualAsset | None:
    """Restore a soft-deleted manual asset.

    :param session: SQLAlchemy session.
    :param asset_id: Asset's UUID.
    :return: Restored ManualAsset, or None if not found.
    """
    asset = session.get(ManualAsset, asset_id)
    if asset is None:
        return None

    asset.is_active = True
    session.flush()
    logger.info(f"Restored manual asset: id={asset_id}")
    return asset
