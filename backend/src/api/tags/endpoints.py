"""Tag API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
from src.api.responses import BAD_REQUEST, RESOURCE_RESPONSES, UNAUTHORIZED
from src.api.tags.models import (
    TagCreateRequest,
    TagListResponse,
    TagResponse,
    TagUpdateRequest,
)
from src.postgres.auth.models import User
from src.postgres.common.models import Tag
from src.postgres.common.operations.tags import (
    MAX_TAGS_PER_USER,
    StandardTagDeletionError,
    count_tags_by_user_id,
    create_tag,
    delete_tag,
    get_tag_by_id,
    get_tag_by_name,
    get_tag_usage_counts,
    get_tags_by_user_id,
    hide_tag,
    unhide_tag,
    update_tag,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=TagListResponse,
    summary="List tags",
    responses=UNAUTHORIZED,
)
def list_tags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TagListResponse:
    """List all tags for the authenticated user with usage counts."""
    tags = get_tags_by_user_id(db, current_user.id)
    usage_counts = get_tag_usage_counts(db, current_user.id)

    return TagListResponse(
        tags=[_to_response(tag, usage_counts.get(tag.id, 0)) for tag in tags],
        total=len(tags),
    )


@router.post(
    "",
    response_model=TagResponse,
    status_code=201,
    summary="Create tag",
    responses={**UNAUTHORIZED, **BAD_REQUEST},
)
def create_new_tag(
    request: TagCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TagResponse:
    """Create a new tag for categorising transactions."""
    # Check tag limit
    tag_count = count_tags_by_user_id(db, current_user.id)
    if tag_count >= MAX_TAGS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"Tag limit reached ({MAX_TAGS_PER_USER})",
        )

    # Check for duplicate name
    existing = get_tag_by_name(db, current_user.id, request.name.strip())
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Tag already exists: {request.name}",
        )

    tag = create_tag(db, current_user.id, request.name, request.colour)
    db.commit()
    db.refresh(tag)
    logger.info(f"Created tag: id={tag.id}, name={tag.name}")
    return _to_response(tag, 0)


@router.get(
    "/{tag_id}",
    response_model=TagResponse,
    summary="Get tag by ID",
    responses=RESOURCE_RESPONSES,
)
def get_tag(
    tag_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TagResponse:
    """Retrieve a specific tag by its UUID."""
    tag = get_tag_by_id(db, tag_id)
    if not tag or tag.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Tag not found: {tag_id}")

    usage_counts = get_tag_usage_counts(db, current_user.id)
    return _to_response(tag, usage_counts.get(tag.id, 0))


@router.put(
    "/{tag_id}",
    response_model=TagResponse,
    summary="Update tag",
    responses={**RESOURCE_RESPONSES, **BAD_REQUEST},
)
def update_existing_tag(
    tag_id: UUID,
    request: TagUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TagResponse:
    """Update a tag's name and/or colour."""
    tag = get_tag_by_id(db, tag_id)
    if not tag or tag.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Tag not found: {tag_id}")

    # Check for name conflict if changing name
    if request.name and request.name.strip() != tag.name:
        existing = get_tag_by_name(db, current_user.id, request.name.strip())
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Tag already exists: {request.name}",
            )

    updated = update_tag(db, tag_id, request.name, request.colour)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Tag not found: {tag_id}")

    db.commit()
    db.refresh(updated)
    logger.info(f"Updated tag: id={tag_id}")

    usage_counts = get_tag_usage_counts(db, current_user.id)
    return _to_response(updated, usage_counts.get(updated.id, 0))


@router.delete(
    "/{tag_id}",
    status_code=204,
    summary="Delete tag",
    responses={**RESOURCE_RESPONSES, **BAD_REQUEST},
)
def delete_existing_tag(
    tag_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a tag, removing it from all associated transactions.

    Standard tags cannot be deleted; use the hide endpoint instead.
    """
    tag = get_tag_by_id(db, tag_id)
    if not tag or tag.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Tag not found: {tag_id}")

    try:
        deleted = delete_tag(db, tag_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Tag not found: {tag_id}")
    except StandardTagDeletionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db.commit()
    logger.info(f"Deleted tag: id={tag_id}")


@router.put(
    "/{tag_id}/hide",
    response_model=TagResponse,
    summary="Hide tag",
    responses=RESOURCE_RESPONSES,
)
def hide_existing_tag(
    tag_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TagResponse:
    """Hide a tag from the UI (it will remain on existing transactions)."""
    tag = get_tag_by_id(db, tag_id)
    if not tag or tag.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Tag not found: {tag_id}")

    updated = hide_tag(db, tag_id)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Tag not found: {tag_id}")

    db.commit()
    db.refresh(updated)
    logger.info(f"Hid tag: id={tag_id}")

    usage_counts = get_tag_usage_counts(db, current_user.id)
    return _to_response(updated, usage_counts.get(updated.id, 0))


@router.put(
    "/{tag_id}/unhide",
    response_model=TagResponse,
    summary="Unhide tag",
    responses=RESOURCE_RESPONSES,
)
def unhide_existing_tag(
    tag_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TagResponse:
    """Unhide a previously hidden tag."""
    tag = get_tag_by_id(db, tag_id)
    if not tag or tag.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Tag not found: {tag_id}")

    updated = unhide_tag(db, tag_id)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Tag not found: {tag_id}")

    db.commit()
    db.refresh(updated)
    logger.info(f"Unhid tag: id={tag_id}")

    usage_counts = get_tag_usage_counts(db, current_user.id)
    return _to_response(updated, usage_counts.get(updated.id, 0))


def _to_response(tag: Tag, usage_count: int = 0) -> TagResponse:
    """Convert a Tag model to response."""
    return TagResponse(
        id=str(tag.id),
        name=tag.name,
        colour=tag.colour,
        is_standard=tag.is_standard,
        is_hidden=tag.is_hidden,
        usage_count=usage_count,
        created_at=tag.created_at,
        updated_at=tag.updated_at,
    )
