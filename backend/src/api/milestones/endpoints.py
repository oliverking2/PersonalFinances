"""Financial milestones API endpoints."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
from src.api.milestones.models import (
    MilestoneCreateRequest,
    MilestoneListResponse,
    MilestoneResponse,
    MilestoneUpdateRequest,
)
from src.api.responses import BAD_REQUEST, RESOURCE_RESPONSES, RESOURCE_WRITE_RESPONSES
from src.postgres.auth.models import User
from src.postgres.common.operations.financial_milestones import (
    create_milestone,
    delete_milestone,
    get_milestone_by_id,
    get_milestones_by_user_id,
    mark_milestone_achieved,
    update_milestone,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=MilestoneListResponse,
    summary="List financial milestones",
    responses=RESOURCE_RESPONSES,
)
def list_milestones(
    achieved: bool | None = Query(None, description="Filter by achieved status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MilestoneListResponse:
    """Get all financial milestones for the authenticated user."""
    milestones = get_milestones_by_user_id(
        db,
        current_user.id,
        achieved_only=achieved is True,
        pending_only=achieved is False if achieved is not None else False,
    )

    return MilestoneListResponse(
        milestones=[MilestoneResponse.model_validate(m) for m in milestones],
        total=len(milestones),
    )


@router.get(
    "/{milestone_id}",
    response_model=MilestoneResponse,
    summary="Get a milestone",
    responses=RESOURCE_RESPONSES,
)
def get_milestone(
    milestone_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MilestoneResponse:
    """Get a specific milestone by ID."""
    milestone = get_milestone_by_id(db, milestone_id)

    if milestone is None or milestone.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Milestone not found")

    return MilestoneResponse.model_validate(milestone)


@router.post(
    "",
    response_model=MilestoneResponse,
    status_code=201,
    summary="Create a milestone",
    responses={**RESOURCE_RESPONSES, **BAD_REQUEST},
)
def create_milestone_endpoint(
    request: MilestoneCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MilestoneResponse:
    """Create a new financial milestone."""
    milestone = create_milestone(
        db,
        current_user.id,
        name=request.name,
        target_amount=request.target_amount,
        target_date=request.target_date,
        colour=request.colour,
        notes=request.notes,
    )
    db.commit()

    logger.info(f"Created milestone: id={milestone.id}, user_id={current_user.id}")
    return MilestoneResponse.model_validate(milestone)


@router.patch(
    "/{milestone_id}",
    response_model=MilestoneResponse,
    summary="Update a milestone",
    responses=RESOURCE_WRITE_RESPONSES,
)
def update_milestone_endpoint(
    milestone_id: UUID,
    request: MilestoneUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MilestoneResponse:
    """Update an existing milestone."""
    # Verify ownership
    existing = get_milestone_by_id(db, milestone_id)
    if existing is None or existing.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Milestone not found")

    # Build update kwargs
    update_kwargs: dict[str, Any] = {}
    if request.name is not None:
        update_kwargs["name"] = request.name
    if request.target_amount is not None:
        update_kwargs["target_amount"] = request.target_amount
    if request.colour is not None:
        update_kwargs["colour"] = request.colour

    # Handle nullable fields with clear flags
    if request.clear_target_date:
        update_kwargs["target_date"] = None
    elif request.target_date is not None:
        update_kwargs["target_date"] = request.target_date

    if request.clear_notes:
        update_kwargs["notes"] = None
    elif request.notes is not None:
        update_kwargs["notes"] = request.notes

    milestone = update_milestone(db, milestone_id, **update_kwargs)
    db.commit()

    logger.info(f"Updated milestone: id={milestone_id}")
    return MilestoneResponse.model_validate(milestone)


@router.post(
    "/{milestone_id}/achieve",
    response_model=MilestoneResponse,
    summary="Mark milestone as achieved",
    responses=RESOURCE_RESPONSES,
)
def achieve_milestone_endpoint(
    milestone_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MilestoneResponse:
    """Manually mark a milestone as achieved."""
    # Verify ownership
    existing = get_milestone_by_id(db, milestone_id)
    if existing is None or existing.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Milestone not found")

    if existing.achieved:
        raise HTTPException(status_code=400, detail="Milestone already achieved")

    milestone = mark_milestone_achieved(db, milestone_id)
    db.commit()

    logger.info(f"Marked milestone as achieved: id={milestone_id}")
    return MilestoneResponse.model_validate(milestone)


@router.delete(
    "/{milestone_id}",
    status_code=204,
    summary="Delete a milestone",
    responses=RESOURCE_RESPONSES,
)
def delete_milestone_endpoint(
    milestone_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a milestone."""
    # Verify ownership
    existing = get_milestone_by_id(db, milestone_id)
    if existing is None or existing.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Milestone not found")

    delete_milestone(db, milestone_id)
    db.commit()

    logger.info(f"Deleted milestone: id={milestone_id}")
