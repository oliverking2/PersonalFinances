"""Connection API endpoints."""

import logging
import os
from datetime import UTC, datetime
from http import HTTPStatus
from uuid import UUID

import requests
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from src.api.connections.models import (
    ConnectionListResponse,
    ConnectionResponse,
    CreateConnectionRequest,
    CreateConnectionResponse,
    InstitutionResponse,
    OAuthCallbackResponse,
    ReauthoriseConnectionResponse,
    UpdateConnectionRequest,
)
from src.api.dependencies import get_current_user, get_db, get_gocardless_credentials
from src.api.jobs.models import JobResponse
from src.api.responses import (
    BAD_GATEWAY,
    INTERNAL_ERROR,
    RESOURCE_RESPONSES,
    RESOURCE_WRITE_RESPONSES,
    UNAUTHORIZED,
)
from src.postgres.auth.models import User
from src.postgres.common.enums import ConnectionStatus, JobStatus, JobType, Provider
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
from src.postgres.common.operations.jobs import (
    create_job,
    get_latest_job_for_entity,
    update_job_status,
)
from src.postgres.gocardless.models import RequisitionLink
from src.postgres.gocardless.operations.requisitions import (
    add_requisition_link,
    update_requisition_record,
)
from src.providers.dagster import (
    GOCARDLESS_CONNECTION_SYNC_JOB,
    TRADING212_SYNC_JOB,
    build_gocardless_run_config,
    build_trading212_run_config,
    trigger_job,
)
from src.providers.gocardless.api.core import GoCardlessCredentials
from src.providers.gocardless.api.requisition import (
    create_link,
    delete_requisition_data_by_id,
    get_requisition_data_by_id,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=ConnectionListResponse,
    summary="List all connections",
    responses=UNAUTHORIZED,
)
def list_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConnectionListResponse:
    """List all bank connections for the authenticated user."""
    connections = get_connections_by_user_id(db, current_user.id)
    return ConnectionListResponse(
        connections=[_to_response(conn, db) for conn in connections],
        total=len(connections),
    )


@router.get("/callback", response_model=OAuthCallbackResponse, summary="OAuth callback")
def oauth_callback(
    ref: str = Query(..., description="Requisition reference from GoCardless"),
    db: Session = Depends(get_db),
    creds: GoCardlessCredentials = Depends(get_gocardless_credentials),
) -> OAuthCallbackResponse:
    """Process GoCardless OAuth callback after bank authorisation.

    Called by frontend after user completes bank authorisation flow.
    """
    try:
        # Look up the requisition by ID (ref is the requisition ID)
        requisition = db.get(RequisitionLink, ref)
        if not requisition:
            logger.warning(f"Callback received for unknown requisition: ref={ref}")
            return OAuthCallbackResponse(success=False, reason="unknown_requisition")

        # Fetch latest status from GoCardless
        gc_data = get_requisition_data_by_id(creds, ref)
        new_status = gc_data.get("status", requisition.status)

        # Update requisition record
        update_requisition_record(db, ref, gc_data)

        # Find the associated connection
        connection = get_connection_by_provider_id(db, Provider.GOCARDLESS, ref)
        if not connection:
            logger.warning(f"No connection found for requisition: ref={ref}")
            return OAuthCallbackResponse(success=False, reason="no_connection")

        # Map GoCardless status to ConnectionStatus
        if new_status == "LN":
            # Linked - connection is active
            update_connection_status(db, connection.id, ConnectionStatus.ACTIVE)
            logger.info(f"Connection activated: id={connection.id}")

            # Auto-trigger sync for the newly activated connection
            job = create_job(
                db,
                user_id=connection.user_id,
                job_type=JobType.SYNC,
                entity_type="connection",
                entity_id=connection.id,
            )

            run_config = build_gocardless_run_config(str(connection.id))
            run_id = trigger_job(GOCARDLESS_CONNECTION_SYNC_JOB, run_config)

            if run_id:
                update_job_status(db, job.id, JobStatus.RUNNING, dagster_run_id=run_id)
                logger.info(
                    f"Auto-triggered sync for connection {connection.id}: job={job.id}, run={run_id}"
                )
            else:
                update_job_status(
                    db, job.id, JobStatus.FAILED, error_message="Job runner unavailable"
                )
                logger.warning(
                    f"Failed to auto-trigger sync for connection {connection.id}: Job runner unavailable"
                )

        elif new_status in ("EX", "RJ", "SA", "GA"):
            # Expired, Rejected, Suspended, or Giving Access error
            update_connection_status(db, connection.id, ConnectionStatus.EXPIRED)
            logger.info(f"Connection expired/rejected: id={connection.id}, status={new_status}")
        # CR (Created) stays as PENDING

        db.commit()
        logger.info(f"OAuth callback processed: ref={ref}, status={new_status}")
        return OAuthCallbackResponse(success=True, reason=None)

    except Exception as e:
        logger.exception(f"Error processing OAuth callback: ref={ref}, error={e}")
        db.rollback()
        return OAuthCallbackResponse(success=False, reason="internal_error")


@router.get(
    "/{connection_id}",
    response_model=ConnectionResponse,
    summary="Get connection by ID",
    responses=RESOURCE_RESPONSES,
)
def get_connection(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConnectionResponse:
    """Retrieve a specific bank connection by its UUID."""
    connection = get_connection_by_id(db, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")
    if connection.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")
    return _to_response(connection, db)


@router.post(
    "",
    response_model=CreateConnectionResponse,
    summary="Create new connection",
    responses={**RESOURCE_RESPONSES, **INTERNAL_ERROR},
)
def create_connection(
    request: CreateConnectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    creds: GoCardlessCredentials = Depends(get_gocardless_credentials),
) -> CreateConnectionResponse:
    """Create a new bank connection via GoCardless OAuth flow.

    Returns an authorisation link for the user to complete at their bank.
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
    responses=RESOURCE_RESPONSES,
)
def update_connection(
    connection_id: UUID,
    request: UpdateConnectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConnectionResponse:
    """Update a connection's friendly name."""
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
    return _to_response(updated, db)


@router.delete(
    "/{connection_id}",
    status_code=204,
    summary="Delete connection",
    responses={**RESOURCE_RESPONSES, **BAD_GATEWAY},
)
def delete_connection_endpoint(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    creds: GoCardlessCredentials = Depends(get_gocardless_credentials),
) -> Response:
    """Delete a bank connection locally and revoke access on GoCardless.

    Local deletion proceeds even if GoCardless revocation fails.
    """
    connection = get_connection_by_id(db, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")
    if connection.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")

    gocardless_error: Exception | None = None

    # Delete on GoCardless if this is a GoCardless connection
    if connection.provider == Provider.GOCARDLESS.value and connection.provider_id:
        try:
            delete_requisition_data_by_id(creds, connection.provider_id)
            logger.info(f"Deleted GoCardless requisition: id={connection.provider_id}")
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == HTTPStatus.NOT_FOUND:
                # Already deleted on GoCardless - treat as success
                logger.info(f"GoCardless requisition already deleted: id={connection.provider_id}")
            else:
                # Other error - log but continue with local deletion
                logger.exception(
                    f"Failed to delete GoCardless requisition: id={connection.provider_id}"
                )
                gocardless_error = e
        except Exception as e:
            # Unexpected error - log but continue with local deletion
            logger.exception(
                f"Failed to delete GoCardless requisition: id={connection.provider_id}"
            )
            gocardless_error = e
    elif not connection.provider_id:
        logger.warning(f"Connection has no provider_id: id={connection_id}")

    # Always delete locally
    delete_connection(db, connection_id)
    db.commit()
    logger.info(f"Deleted connection: id={connection_id}")

    # If GoCardless deletion failed, return 502 to inform the user
    if gocardless_error:
        raise HTTPException(
            status_code=502,
            detail="Connection deleted locally, but failed to revoke bank access. "
            "The bank connection will expire automatically.",
        )

    return Response(status_code=204)


@router.post(
    "/{connection_id}/reauthorise",
    response_model=ReauthoriseConnectionResponse,
    summary="Reauthorise connection",
    responses=RESOURCE_WRITE_RESPONSES,
)
def reauthorise_connection(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    creds: GoCardlessCredentials = Depends(get_gocardless_credentials),
) -> ReauthoriseConnectionResponse:
    """Generate a new authorisation URL for an expired or pending connection."""
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


@router.post(
    "/{connection_id}/sync",
    status_code=202,
    response_model=JobResponse,
    summary="Trigger connection sync",
    responses=RESOURCE_WRITE_RESPONSES,
)
def trigger_connection_sync(
    connection_id: UUID,
    full_sync: bool = Query(
        False, description="If true, ignore transaction watermark and fetch all history"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobResponse:
    """Trigger a background job to sync data from the bank for this connection."""
    connection = get_connection_by_id(db, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")
    if connection.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")

    if connection.status != ConnectionStatus.ACTIVE.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot sync connection with status '{connection.status}'. "
            f"Connection must be active.",
        )

    # Create job record
    job = create_job(
        db,
        user_id=current_user.id,
        job_type=JobType.SYNC,
        entity_type="connection",
        entity_id=connection_id,
    )

    # Trigger appropriate Dagster job based on provider
    if connection.provider == Provider.TRADING212.value:
        # Trading 212 uses the provider_id (T212 API key ID) for sync
        run_config = build_trading212_run_config(connection.provider_id)
        run_id = trigger_job(TRADING212_SYNC_JOB, run_config)
    else:
        # GoCardless uses the connection ID
        run_config = build_gocardless_run_config(str(connection_id), full_sync=full_sync)
        run_id = trigger_job(GOCARDLESS_CONNECTION_SYNC_JOB, run_config)

    if run_id:
        update_job_status(db, job.id, JobStatus.RUNNING, dagster_run_id=run_id)
        logger.info(f"Triggered sync for connection {connection_id}: job={job.id}, run={run_id}")
    else:
        update_job_status(db, job.id, JobStatus.FAILED, error_message="Job runner unavailable")
        logger.warning(
            f"Failed to trigger sync for connection {connection_id}: Job runner unavailable"
        )

    db.commit()
    db.refresh(job)

    return JobResponse(
        id=str(job.id),
        job_type=JobType(job.job_type),
        status=JobStatus(job.status),
        entity_type=job.entity_type,
        entity_id=str(job.entity_id) if job.entity_id else None,
        dagster_run_id=job.dagster_run_id,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


def _to_response(connection: Connection, db: Session) -> ConnectionResponse:
    """Convert a Connection model to response, including latest sync job."""
    # Get latest sync job for this connection
    latest_job = get_latest_job_for_entity(db, "connection", connection.id, JobType.SYNC)
    latest_sync_job = None
    if latest_job:
        latest_sync_job = JobResponse(
            id=str(latest_job.id),
            job_type=JobType(latest_job.job_type),
            status=JobStatus(latest_job.status),
            entity_type=latest_job.entity_type,
            entity_id=str(latest_job.entity_id) if latest_job.entity_id else None,
            dagster_run_id=latest_job.dagster_run_id,
            error_message=latest_job.error_message,
            created_at=latest_job.created_at,
            started_at=latest_job.started_at,
            completed_at=latest_job.completed_at,
        )

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
        latest_sync_job=latest_sync_job,
    )
