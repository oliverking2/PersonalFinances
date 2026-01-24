"""Connection API endpoints."""

import logging
import os
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from src.api.connections.models import (
    ConnectionListResponse,
    ConnectionResponse,
    CreateConnectionRequest,
    CreateConnectionResponse,
    InstitutionResponse,
    ReauthoriseConnectionResponse,
    UpdateConnectionRequest,
)
from src.api.dependencies import get_current_user, get_db, get_gocardless_credentials
from src.postgres.auth.models import User
from src.postgres.common.enums import ConnectionStatus, Provider
from src.postgres.common.models import Connection
from src.postgres.common.operations.connections import (
    create_connection as db_create_connection,
)
from src.postgres.common.operations.connections import (
    delete_connection,
    get_connection_by_id,
    get_connection_by_provider_id,
    get_connections_by_user_id,
    update_connection_friendly_name,
    update_connection_status,
)
from src.postgres.common.operations.institutions import get_institution_by_id
from src.postgres.gocardless.models import RequisitionLink
from src.postgres.gocardless.operations.requisitions import (
    add_requisition_link,
    update_requisition_record,
)
from src.providers.gocardless.api.core import GoCardlessCredentials
from src.providers.gocardless.api.requisition import (
    create_link,
    get_requisition_data_by_id,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=ConnectionListResponse, summary="List all connections")
def list_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConnectionListResponse:
    """List all bank connections for the authenticated user.

    :param db: Database session.
    :param current_user: Authenticated user.
    :returns: List of connections.
    """
    connections = get_connections_by_user_id(db, current_user.id)
    return ConnectionListResponse(
        connections=[_to_response(conn) for conn in connections],
        total=len(connections),
    )


@router.get("/callback", summary="OAuth callback")
def oauth_callback(
    ref: str = Query(..., description="Requisition reference from GoCardless"),
    db: Session = Depends(get_db),
    creds: GoCardlessCredentials = Depends(get_gocardless_credentials),
) -> RedirectResponse:
    """Handle OAuth callback from GoCardless.

    This endpoint is called after the user completes the bank authorisation flow.
    It updates the requisition and connection status, then redirects to the frontend.

    :param ref: Requisition reference (the requisition ID we sent to GoCardless).
    :param db: Database session.
    :param creds: GoCardless credentials.
    :returns: Redirect to frontend with success or error status.
    """
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

    try:
        # Look up the requisition by ID (ref is the requisition ID)
        requisition = db.get(RequisitionLink, ref)
        if not requisition:
            logger.warning(f"Callback received for unknown requisition: ref={ref}")
            return RedirectResponse(
                url=f"{frontend_url}/accounts?callback=error&reason=unknown_requisition"
            )

        # Fetch latest status from GoCardless
        gc_data = get_requisition_data_by_id(creds, ref)
        new_status = gc_data.get("status", requisition.status)

        # Update requisition record
        update_requisition_record(db, ref, gc_data)

        # Find the associated connection
        connection = get_connection_by_provider_id(db, Provider.GOCARDLESS, ref)
        if not connection:
            logger.warning(f"No connection found for requisition: ref={ref}")
            return RedirectResponse(
                url=f"{frontend_url}/accounts?callback=error&reason=no_connection"
            )

        # Map GoCardless status to ConnectionStatus
        if new_status == "LN":
            # Linked - connection is active
            update_connection_status(db, connection.id, ConnectionStatus.ACTIVE)
            logger.info(f"Connection activated: id={connection.id}")
        elif new_status in ("EX", "RJ", "SA", "GA"):
            # Expired, Rejected, Suspended, or Giving Access error
            update_connection_status(db, connection.id, ConnectionStatus.EXPIRED)
            logger.info(f"Connection expired/rejected: id={connection.id}, status={new_status}")
        # CR (Created) stays as PENDING

        db.commit()
        logger.info(f"OAuth callback processed: ref={ref}, status={new_status}")
        return RedirectResponse(url=f"{frontend_url}/accounts?callback=success")

    except Exception as e:
        logger.exception(f"Error processing OAuth callback: ref={ref}, error={e}")
        db.rollback()
        return RedirectResponse(url=f"{frontend_url}/accounts?callback=error&reason=internal_error")


@router.get("/{connection_id}", response_model=ConnectionResponse, summary="Get connection by ID")
def get_connection(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConnectionResponse:
    """Get a specific connection by ID.

    :param connection_id: Connection UUID to retrieve.
    :param db: Database session.
    :param current_user: Authenticated user.
    :returns: Connection details.
    :raises HTTPException: If connection not found or not owned by user.
    """
    connection = get_connection_by_id(db, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")
    if connection.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")
    return _to_response(connection)


@router.post("", response_model=CreateConnectionResponse, summary="Create new connection")
def create_connection(
    request: CreateConnectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    creds: GoCardlessCredentials = Depends(get_gocardless_credentials),
) -> CreateConnectionResponse:
    """Create a new bank connection.

    This endpoint initiates the GoCardless OAuth flow by creating a requisition
    and returning the authorisation link.

    :param request: Connection creation request.
    :param db: Database session.
    :param current_user: Authenticated user.
    :param creds: GoCardless credentials.
    :returns: Connection with authorisation link.
    :raises HTTPException: If institution not found or GoCardless API fails.
    """
    # Validate institution exists
    institution = get_institution_by_id(db, request.institution_id)
    if not institution:
        raise HTTPException(
            status_code=404,
            detail=f"Institution not found: {request.institution_id}",
        )

    # Get callback URL from environment
    callback_url = os.getenv("GC_CALLBACK_URL")
    if not callback_url:
        logger.error("GC_CALLBACK_URL environment variable not set")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: callback URL not configured",
        )

    try:
        # Create requisition with GoCardless
        link_data = create_link(creds, callback_url, request.institution_id)
        logger.info(
            f"Created GoCardless requisition: id={link_data['id']}, "
            f"institution={request.institution_id}"
        )

        # Store requisition in database
        requisition = add_requisition_link(db, link_data, request.friendly_name)

        # Create connection record
        connection = db_create_connection(
            session=db,
            user_id=current_user.id,
            provider=Provider.GOCARDLESS,
            provider_id=requisition.id,
            institution_id=request.institution_id,
            friendly_name=request.friendly_name,
            status=ConnectionStatus.PENDING,
            created_at=datetime.now(UTC),
        )

        db.commit()
        logger.info(
            f"Created connection: id={connection.id}, user_id={current_user.id}, "
            f"requisition_id={requisition.id}"
        )

        return CreateConnectionResponse(
            id=str(connection.id),
            link=link_data["link"],
        )

    except Exception as e:
        logger.exception(f"Failed to create connection: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to create bank connection. Please try again.",
        ) from e


@router.patch(
    "/{connection_id}",
    response_model=ConnectionResponse,
    summary="Update connection",
)
def update_connection(
    connection_id: UUID,
    request: UpdateConnectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConnectionResponse:
    """Update a connection's friendly name.

    :param connection_id: Connection UUID to update.
    :param request: Update request data.
    :param db: Database session.
    :param current_user: Authenticated user.
    :returns: Updated connection.
    :raises HTTPException: If connection not found or not owned by user.
    """
    connection = get_connection_by_id(db, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")
    if connection.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")

    updated = update_connection_friendly_name(db, connection_id, request.friendly_name)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")

    db.commit()
    db.refresh(updated)
    logger.info(f"Updated connection: id={connection_id}")
    return _to_response(updated)


@router.delete("/{connection_id}", summary="Delete connection")
def delete_connection_endpoint(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a bank connection.

    :param connection_id: Connection UUID to delete.
    :param db: Database session.
    :param current_user: Authenticated user.
    :returns: Confirmation message.
    :raises HTTPException: If connection not found or not owned by user.
    """
    connection = get_connection_by_id(db, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")
    if connection.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")

    delete_connection(db, connection_id)
    db.commit()
    logger.info(f"Deleted connection: id={connection_id}")
    return {"message": f"Connection {connection_id} deleted"}


@router.post(
    "/{connection_id}/reauthorise",
    response_model=ReauthoriseConnectionResponse,
    summary="Reauthorise connection",
)
def reauthorise_connection(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    creds: GoCardlessCredentials = Depends(get_gocardless_credentials),
) -> ReauthoriseConnectionResponse:
    """Generate a new authorisation URL for a connection that needs (re)authorisation.

    Creates a new requisition for the same institution and updates the connection
    to use the new requisition ID. Works for both EXPIRED connections and PENDING
    connections where the user abandoned the OAuth flow.

    :param connection_id: Connection UUID to reauthorise.
    :param db: Database session.
    :param current_user: Authenticated user.
    :param creds: GoCardless credentials.
    :returns: Reauthorisation link.
    :raises HTTPException: If connection not found, not owned by user, or already active.
    """
    connection = get_connection_by_id(db, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")
    if connection.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")

    # Only allow reauthorisation for EXPIRED or PENDING connections
    allowed_statuses = {ConnectionStatus.EXPIRED.value, ConnectionStatus.PENDING.value}
    if connection.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Connection cannot be reauthorised. Current status: {connection.status}",
        )

    # Get callback URL from environment
    callback_url = os.getenv("GC_CALLBACK_URL")
    if not callback_url:
        logger.error("GC_CALLBACK_URL environment variable not set")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: callback URL not configured",
        )

    try:
        # Create new requisition for the same institution
        link_data = create_link(creds, callback_url, connection.institution_id)
        logger.info(
            f"Created reauthorisation requisition: id={link_data['id']}, "
            f"institution={connection.institution_id}"
        )

        # Store new requisition
        requisition = add_requisition_link(db, link_data, connection.friendly_name)

        # Update connection to use new requisition
        connection.provider_id = requisition.id
        connection.status = ConnectionStatus.PENDING.value
        db.flush()

        db.commit()
        logger.info(
            f"Reauthorised connection: id={connection_id}, new_requisition_id={requisition.id}"
        )

        return ReauthoriseConnectionResponse(
            id=str(connection.id),
            link=link_data["link"],
        )

    except Exception as e:
        logger.exception(f"Failed to reauthorise connection: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to reauthorise connection. Please try again.",
        ) from e


def _to_response(connection: Connection) -> ConnectionResponse:
    """Convert a Connection model to response."""
    return ConnectionResponse(
        id=str(connection.id),
        friendly_name=connection.friendly_name,
        provider=Provider(connection.provider),
        institution=InstitutionResponse(
            id=connection.institution.id,
            name=connection.institution.name,
            logo_url=connection.institution.logo_url,
        ),
        status=ConnectionStatus(connection.status),
        account_count=len(connection.accounts) if connection.accounts else 0,
        created_at=connection.created_at,
        expires_at=connection.expires_at,
    )
