"""Connection API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
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
from src.api.dependencies import get_current_user, get_db
from src.postgres.auth.models import User
from src.postgres.common.enums import ConnectionStatus, Provider
from src.postgres.common.models import Connection
from src.postgres.common.operations.connections import (
    delete_connection,
    get_connection_by_id,
    get_connections_by_user_id,
    update_connection_friendly_name,
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
) -> CreateConnectionResponse:
    """Create a new bank connection.

    This endpoint initiates the GoCardless OAuth flow.

    :param request: Connection creation request.
    :param db: Database session.
    :param current_user: Authenticated user.
    :returns: Connection with authorisation link.
    """
    # TODO: Implement GoCardless requisition creation
    # This will need to:
    # 1. Create an end user agreement
    # 2. Create a requisition
    # 3. Create connection record
    # 4. Return the authorisation link
    raise HTTPException(status_code=501, detail="Not implemented yet")


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
) -> ReauthoriseConnectionResponse:
    """Generate a new authorisation URL for an expired connection.

    :param connection_id: Connection UUID to reauthorise.
    :param db: Database session.
    :param current_user: Authenticated user.
    :returns: Reauthorisation link.
    :raises HTTPException: If connection not found or not owned by user.
    """
    connection = get_connection_by_id(db, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")
    if connection.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")

    # TODO: Implement GoCardless reauthorisation
    # This will need to:
    # 1. Create a new requisition for the same institution
    # 2. Update the connection record
    # 3. Return the new authorisation link
    raise HTTPException(status_code=501, detail="Not implemented yet")


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
