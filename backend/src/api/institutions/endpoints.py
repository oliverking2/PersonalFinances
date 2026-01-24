"""Institution API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
from src.api.institutions.models import InstitutionListResponse, InstitutionResponse
from src.postgres.auth.models import User
from src.postgres.common.enums import Provider
from src.postgres.common.models import Institution
from src.postgres.common.operations.institutions import (
    get_institution_by_id,
    list_institutions,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=InstitutionListResponse, summary="List institutions")
def list_institutions_endpoint(
    provider: Provider | None = Query(None, description="Filter by provider"),
    country: str | None = Query(None, description="Filter by country code (e.g., GB)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InstitutionListResponse:
    """List available institutions for connecting accounts.

    :param provider: Optional filter by provider.
    :param country: Optional filter by country code.
    :param db: Database session.
    :param current_user: Authenticated user.
    :returns: List of institutions.
    """
    institutions = list_institutions(db, provider=provider, country=country)

    return InstitutionListResponse(
        institutions=[_to_response(inst) for inst in institutions],
        total=len(institutions),
    )


@router.get(
    "/{institution_id}",
    response_model=InstitutionResponse,
    summary="Get institution by ID",
)
def get_institution(
    institution_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InstitutionResponse:
    """Get a specific institution by ID.

    :param institution_id: Institution ID to retrieve.
    :param db: Database session.
    :param current_user: Authenticated user.
    :returns: Institution details.
    :raises HTTPException: If institution not found.
    """
    institution = get_institution_by_id(db, institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail=f"Institution not found: {institution_id}")
    return _to_response(institution)


def _to_response(institution: Institution) -> InstitutionResponse:
    """Convert an Institution model to response."""
    return InstitutionResponse(
        id=institution.id,
        provider=Provider(institution.provider),
        name=institution.name,
        logo_url=institution.logo_url,
        countries=institution.countries if institution.countries else None,
    )
