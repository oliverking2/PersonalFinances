"""Connection (requisition) API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.connections.models import (
    ConnectionListResponse,
    ConnectionResponse,
    CreateConnectionRequest,
    CreateConnectionResponse,
)
from src.api.dependencies import get_db
from src.postgres.gocardless.models import RequisitionLink

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=ConnectionListResponse, summary="List all connections")
def list_connections(db: Session = Depends(get_db)) -> ConnectionListResponse:
    """List all bank connections.

    :param db: Database session.
    :returns: List of connections.
    """
    connections = db.query(RequisitionLink).all()
    return ConnectionListResponse(
        connections=[_to_response(conn) for conn in connections],
        total=len(connections),
    )


@router.get("/{connection_id}", response_model=ConnectionResponse, summary="Get connection by ID")
def get_connection(connection_id: str, db: Session = Depends(get_db)) -> ConnectionResponse:
    """Get a specific connection by ID.

    :param connection_id: Connection ID to retrieve.
    :param db: Database session.
    :returns: Connection details.
    :raises HTTPException: If connection not found.
    """
    connection = db.get(RequisitionLink, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")
    return _to_response(connection)


@router.post("", response_model=CreateConnectionResponse, summary="Create new connection")
def create_connection(
    request: CreateConnectionRequest,
    db: Session = Depends(get_db),
) -> CreateConnectionResponse:
    """Create a new bank connection.

    This endpoint initiates the GoCardless OAuth flow.

    :param request: Connection creation request.
    :param db: Database session.
    :returns: Connection with authorization link.
    """
    # TODO: Implement GoCardless requisition creation
    # This will need to:
    # 1. Create an end user agreement
    # 2. Create a requisition
    # 3. Return the authorization link
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.delete("/{connection_id}", summary="Delete connection")
def delete_connection(
    connection_id: str,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Delete a bank connection.

    :param connection_id: Connection ID to delete.
    :param db: Database session.
    :returns: Confirmation message.
    :raises HTTPException: If connection not found.
    """
    connection = db.get(RequisitionLink, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")

    db.delete(connection)
    db.commit()
    logger.info(f"Deleted connection: id={connection_id}")
    return {"message": f"Connection {connection_id} deleted"}


def _to_response(connection: RequisitionLink) -> ConnectionResponse:
    """Convert a RequisitionLink model to response."""
    return ConnectionResponse(
        id=connection.id,
        institution_id=connection.institution_id,
        status=connection.status,
        friendly_name=connection.friendly_name,
        created=connection.created,
        link=connection.link,
        account_count=len(connection.accounts) if connection.accounts else 0,
        expired=connection.dg_account_expired,
    )
