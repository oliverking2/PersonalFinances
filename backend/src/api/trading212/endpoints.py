"""Trading 212 API endpoints."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
from src.api.jobs.models import JobResponse
from src.api.responses import RESOURCE_RESPONSES, RESOURCE_WRITE_RESPONSES
from src.api.trading212.models import (
    AddT212ConnectionRequest,
    T212CashBalanceResponse,
    T212ConnectionListResponse,
    T212ConnectionResponse,
)
from src.postgres.auth.models import User
from src.postgres.common.enums import (
    AccountStatus,
    AccountType,
    ConnectionStatus,
    JobStatus,
    JobType,
    Provider,
)
from src.postgres.common.models import Account, Connection, Institution
from src.postgres.common.operations.jobs import create_job, update_job_status
from src.postgres.trading212.operations.api_keys import (
    create_api_key,
    delete_api_key,
    get_api_key_by_id,
    get_api_keys_by_user,
    update_api_key_status,
)
from src.postgres.trading212.operations.cash_balances import (
    get_latest_cash_balance,
    upsert_cash_balance,
)
from src.providers.dagster import TRADING212_SYNC_JOB, build_trading212_run_config, trigger_job
from src.providers.trading212.api.core import Trading212Client
from src.providers.trading212.exceptions import Trading212AuthError, Trading212Error
from src.utils.security import decrypt_api_key, encrypt_api_key

logger = logging.getLogger(__name__)

router = APIRouter()


def _ensure_trading212_institution(db: Session) -> Institution:
    """Ensure the Trading 212 institution exists."""
    institution_id = "TRADING212"
    existing = db.get(Institution, institution_id)

    if existing:
        return existing

    institution = Institution(
        id=institution_id,
        provider=Provider.TRADING212.value,
        name="Trading 212",
        logo_url="https://www.trading212.com/favicon.ico",
        countries=["GB"],
    )
    db.add(institution)
    db.flush()
    return institution


def _to_response(api_key_record: object) -> T212ConnectionResponse:
    """Convert a T212ApiKey model to API response."""
    return T212ConnectionResponse(
        id=str(api_key_record.id),  # type: ignore[attr-defined]
        friendly_name=api_key_record.friendly_name,  # type: ignore[attr-defined]
        t212_account_id=api_key_record.t212_account_id,  # type: ignore[attr-defined]
        currency_code=api_key_record.currency_code,  # type: ignore[attr-defined]
        status=api_key_record.status,  # type: ignore[attr-defined]
        error_message=api_key_record.error_message,  # type: ignore[attr-defined]
        last_synced_at=api_key_record.last_synced_at,  # type: ignore[attr-defined]
        created_at=api_key_record.created_at,  # type: ignore[attr-defined]
    )


@router.get(
    "",
    response_model=T212ConnectionListResponse,
    summary="List Trading 212 connections",
    responses=RESOURCE_RESPONSES,
)
def list_t212_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> T212ConnectionListResponse:
    """List all Trading 212 connections for the authenticated user."""
    api_keys = get_api_keys_by_user(db, current_user.id)
    return T212ConnectionListResponse(
        connections=[_to_response(key) for key in api_keys],
        total=len(api_keys),
    )


@router.post(
    "",
    response_model=T212ConnectionResponse,
    status_code=201,
    summary="Add Trading 212 connection",
    responses=RESOURCE_WRITE_RESPONSES,
)
def add_t212_connection(
    request: AddT212ConnectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> T212ConnectionResponse:
    """Add a new Trading 212 connection by providing an API key.

    The API key is validated against the Trading 212 API before being stored.
    A Connection and Account are automatically created.
    """
    # Validate the API key by calling T212 API
    try:
        client = Trading212Client(request.api_key)
        account_info = client.get_account_info()
        cash = client.get_cash()
    except Trading212AuthError as e:
        logger.warning(f"Invalid T212 API key: {e}")
        raise HTTPException(status_code=400, detail="Invalid API key") from e
    except Trading212Error as e:
        logger.error(f"T212 API error during validation: {e}")
        raise HTTPException(
            status_code=502, detail="Failed to validate API key with Trading 212"
        ) from e

    # Encrypt and store the API key
    encrypted_key = encrypt_api_key(request.api_key)
    api_key_record = create_api_key(
        db,
        user_id=current_user.id,
        api_key_encrypted=encrypted_key,
        friendly_name=request.friendly_name,
        t212_account_id=account_info.account_id,
        currency_code=account_info.currency_code,
    )

    # Store initial cash balance
    upsert_cash_balance(
        db,
        api_key_record.id,
        free=cash.free,
        blocked=cash.blocked,
        invested=cash.invested,
        pie_cash=cash.pie_cash,
        ppl=cash.ppl,
        result=cash.result,
        total=cash.total,
    )

    # Update last synced timestamp
    update_api_key_status(
        db,
        api_key_record.id,
        status="active",
        last_synced_at=datetime.now(UTC),
    )

    # Ensure institution exists
    _ensure_trading212_institution(db)

    # Create Connection record
    connection = Connection(
        user_id=current_user.id,
        provider=Provider.TRADING212.value,
        provider_id=str(api_key_record.id),
        institution_id="TRADING212",
        friendly_name=request.friendly_name,
        status=ConnectionStatus.ACTIVE.value,
        created_at=datetime.now(UTC),
        synced_at=datetime.now(UTC),
    )
    db.add(connection)
    db.flush()

    # Create Account record
    account = Account(
        connection_id=connection.id,
        provider_id=account_info.account_id or str(api_key_record.id),
        account_type=AccountType.TRADING.value,
        display_name=request.friendly_name,
        currency=account_info.currency_code,
        status=AccountStatus.ACTIVE.value,
        total_value=cash.total,
        unrealised_pnl=cash.ppl,
        balance_amount=cash.free,
        balance_currency=account_info.currency_code,
        balance_type="cash",
        balance_updated_at=datetime.now(UTC),
        synced_at=datetime.now(UTC),
        last_synced_at=datetime.now(UTC),
    )
    db.add(account)

    db.commit()
    db.refresh(api_key_record)

    logger.info(
        f"Created T212 connection: api_key_id={api_key_record.id}, "
        f"connection_id={connection.id}, account_id={account.id}"
    )

    return _to_response(api_key_record)


@router.get(
    "/{api_key_id}",
    response_model=T212ConnectionResponse,
    summary="Get Trading 212 connection",
    responses=RESOURCE_RESPONSES,
)
def get_t212_connection(
    api_key_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> T212ConnectionResponse:
    """Get a specific Trading 212 connection by ID."""
    api_key = get_api_key_by_id(db, api_key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail=f"Connection not found: {api_key_id}")
    if api_key.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Connection not found: {api_key_id}")

    return _to_response(api_key)


@router.delete(
    "/{api_key_id}",
    status_code=204,
    summary="Delete Trading 212 connection",
    responses=RESOURCE_RESPONSES,
)
def delete_t212_connection(
    api_key_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Delete a Trading 212 connection.

    This removes the API key and associated Connection/Account records.
    """
    api_key = get_api_key_by_id(db, api_key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail=f"Connection not found: {api_key_id}")
    if api_key.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Connection not found: {api_key_id}")

    # Delete the Connection (cascades to Account via FK)
    connection = (
        db.query(Connection)
        .filter(
            Connection.provider == Provider.TRADING212.value,
            Connection.provider_id == str(api_key_id),
        )
        .first()
    )
    if connection:
        db.delete(connection)

    # Delete the API key (cascades to cash balances)
    deleted = delete_api_key(db, api_key_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Connection not found: {api_key_id}")

    db.commit()
    logger.info(f"Deleted T212 connection: api_key_id={api_key_id}")

    return Response(status_code=204)


@router.post(
    "/{api_key_id}/sync",
    status_code=202,
    response_model=JobResponse,
    summary="Sync Trading 212 connection",
    responses=RESOURCE_WRITE_RESPONSES,
)
def trigger_t212_sync(
    api_key_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobResponse:
    """Trigger a background sync for a Trading 212 connection."""
    api_key = get_api_key_by_id(db, api_key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail=f"Connection not found: {api_key_id}")
    if api_key.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Connection not found: {api_key_id}")

    if api_key.status != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot sync connection with status '{api_key.status}'. Connection must be active.",
        )

    # Find the associated Connection for job tracking
    connection = (
        db.query(Connection)
        .filter(
            Connection.provider == Provider.TRADING212.value,
            Connection.provider_id == str(api_key_id),
        )
        .first()
    )

    # Create job record
    job = create_job(
        db,
        user_id=current_user.id,
        job_type=JobType.SYNC,
        entity_type="connection",
        entity_id=connection.id if connection else None,
    )

    # Trigger Dagster job
    run_config = build_trading212_run_config(str(api_key_id))
    run_id = trigger_job(TRADING212_SYNC_JOB, run_config)

    if run_id:
        update_job_status(db, job.id, JobStatus.RUNNING, dagster_run_id=run_id)
        logger.info(f"Triggered T212 sync: api_key_id={api_key_id}, job={job.id}, run={run_id}")
    else:
        # Dagster unavailable - do inline sync
        logger.info(f"Dagster unavailable, performing inline sync for api_key_id={api_key_id}")
        try:
            decrypted_key = decrypt_api_key(api_key.api_key_encrypted)
            client = Trading212Client(decrypted_key)
            account_info = client.get_account_info()
            cash = client.get_cash()

            # Update API key metadata
            update_api_key_status(
                db,
                api_key_id,
                status="active",
                t212_account_id=account_info.account_id,
                currency_code=account_info.currency_code,
                last_synced_at=datetime.now(UTC),
            )

            # Store cash balance
            upsert_cash_balance(
                db,
                api_key_id,
                free=cash.free,
                blocked=cash.blocked,
                invested=cash.invested,
                pie_cash=cash.pie_cash,
                ppl=cash.ppl,
                result=cash.result,
                total=cash.total,
            )

            # Update Account if exists
            if connection:
                account = db.query(Account).filter(Account.connection_id == connection.id).first()
                if account:
                    account.total_value = cash.total
                    account.unrealised_pnl = cash.ppl
                    account.balance_amount = cash.free
                    account.balance_updated_at = datetime.now(UTC)
                    account.last_synced_at = datetime.now(UTC)

            update_job_status(db, job.id, JobStatus.COMPLETED)
            logger.info(f"Inline T212 sync completed: api_key_id={api_key_id}")

        except Trading212AuthError as e:
            logger.error(f"T212 auth error during sync: {e}")
            update_api_key_status(
                db, api_key_id, status="error", error_message="API key invalid or revoked"
            )
            update_job_status(db, job.id, JobStatus.FAILED, error_message="API key invalid")

        except Exception as e:
            logger.exception(f"T212 sync failed: {e}")
            update_job_status(db, job.id, JobStatus.FAILED, error_message=str(e))

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


@router.get(
    "/{api_key_id}/balance",
    response_model=T212CashBalanceResponse,
    summary="Get latest cash balance",
    responses=RESOURCE_RESPONSES,
)
def get_t212_balance(
    api_key_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> T212CashBalanceResponse:
    """Get the latest cash balance for a Trading 212 connection."""
    api_key = get_api_key_by_id(db, api_key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail=f"Connection not found: {api_key_id}")
    if api_key.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Connection not found: {api_key_id}")

    balance = get_latest_cash_balance(db, api_key_id)
    if not balance:
        raise HTTPException(status_code=404, detail="No balance data available")

    return T212CashBalanceResponse(
        free=balance.free,
        blocked=balance.blocked,
        invested=balance.invested,
        pie_cash=balance.pie_cash,
        ppl=balance.ppl,
        result=balance.result,
        total=balance.total,
        fetched_at=balance.fetched_at,
    )
