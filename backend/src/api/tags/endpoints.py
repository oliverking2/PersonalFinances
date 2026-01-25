"""Tag API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
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
    count_tags_by_user_id,
    create_tag,
    delete_tag,
    get_tag_by_id,
    get_tag_by_name,
    get_tag_usage_counts,
    get_tags_by_user_id,
    update_tag,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=TagListResponse, summary="List tags")
def list_tags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TagListResponse:
    """List all tags for the authenticated user.

    :param db: Database session.
    :param current_user: Authenticated user.
    :returns: List of tags with usage counts.
    """
    tags = get_tags_by_user_id(db, current_user.id)
    usage_counts = get_tag_usage_counts(db, current_user.id)

    return TagListResponse(
        tags=[_to_response(tag, usage_counts.get(tag.id, 0)) for tag in tags],
        total=len(tags),
    )


@router.post("", response_model=TagResponse, status_code=201, summary="Create tag")
def create_new_tag(
    request: TagCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TagResponse:
    """Create a new tag.

    :param request: Tag creation data.
    :param db: Database session.
    :param current_user: Authenticated user.
    :returns: Created tag.
    :raises HTTPException: If tag limit reached or name already exists.
    """
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


@router.get("/{tag_id}", response_model=TagResponse, summary="Get tag by ID")
def get_tag(
    tag_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TagResponse:
    """Get a specific tag by ID.

    :param tag_id: Tag UUID to retrieve.
    :param db: Database session.
    :param current_user: Authenticated user.
    :returns: Tag details.
    :raises HTTPException: If tag not found or not owned by user.
    """
    tag = get_tag_by_id(db, tag_id)
    if not tag or tag.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Tag not found: {tag_id}")

    usage_counts = get_tag_usage_counts(db, current_user.id)
    return _to_response(tag, usage_counts.get(tag.id, 0))


@router.put("/{tag_id}", response_model=TagResponse, summary="Update tag")
def update_existing_tag(
    tag_id: UUID,
    request: TagUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TagResponse:
    """Update a tag's name and/or colour.

    :param tag_id: Tag UUID to update.
    :param request: Update request data.
    :param db: Database session.
    :param current_user: Authenticated user.
    :returns: Updated tag.
    :raises HTTPException: If tag not found or name conflict.
    """
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


@router.delete("/{tag_id}", status_code=204, summary="Delete tag")
def delete_existing_tag(
    tag_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a tag.

    This removes the tag from all transactions.

    :param tag_id: Tag UUID to delete.
    :param db: Database session.
    :param current_user: Authenticated user.
    :raises HTTPException: If tag not found or not owned by user.
    """
    tag = get_tag_by_id(db, tag_id)
    if not tag or tag.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Tag not found: {tag_id}")

    deleted = delete_tag(db, tag_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Tag not found: {tag_id}")

    db.commit()
    logger.info(f"Deleted tag: id={tag_id}")


def _to_response(tag: Tag, usage_count: int = 0) -> TagResponse:
    """Convert a Tag model to response."""
    return TagResponse(
        id=str(tag.id),
        name=tag.name,
        colour=tag.colour,
        usage_count=usage_count,
        created_at=tag.created_at,
        updated_at=tag.updated_at,
    )
