"""Analytics API endpoints."""

import logging
from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.analytics.models import (
    AnalyticsStatusResponse,
    DatasetColumnResponse,
    DatasetListResponse,
    DatasetQueryResponse,
    DatasetResponse,
    DatasetSchemaResponse,
    RefreshResponse,
)
from src.api.dependencies import get_current_user, get_db
from src.duckdb.client import check_connection, execute_query
from src.duckdb.manifest import get_dataset_schema, get_datasets
from src.duckdb.queries import build_dataset_query
from src.postgres.auth.models import User
from src.postgres.common.enums import JobStatus, JobType
from src.postgres.common.models import Job
from src.postgres.common.operations.connections import get_connections_by_user_id
from src.postgres.common.operations.tags import get_tags_by_user_id
from src.providers.dagster import trigger_job

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_user_account_ids(db: Session, user: User) -> list[UUID]:
    """Get all account IDs for a user.

    :param db: Database session.
    :param user: Authenticated user.
    :returns: List of account UUIDs.
    """
    connections = get_connections_by_user_id(db, user.id)
    return [acc.id for conn in connections for acc in conn.accounts]


def _validate_account_ids(db: Session, user: User, account_ids: list[UUID]) -> list[UUID]:
    """Validate and filter account IDs to those owned by the user.

    :param db: Database session.
    :param user: Authenticated user.
    :param account_ids: Requested account IDs.
    :returns: Valid account IDs owned by user.
    """
    user_account_ids = set(_get_user_account_ids(db, user))
    return [aid for aid in account_ids if aid in user_account_ids]


def _validate_tag_ids(db: Session, user: User, tag_ids: list[UUID]) -> list[UUID]:
    """Validate and filter tag IDs to those owned by the user.

    :param db: Database session.
    :param user: Authenticated user.
    :param tag_ids: Requested tag IDs.
    :returns: Valid tag IDs owned by user.
    """
    user_tags = get_tags_by_user_id(db, user.id)
    user_tag_ids = {tag.id for tag in user_tags}
    return [tid for tid in tag_ids if tid in user_tag_ids]


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Serialize a row for JSON response.

    Converts date objects to ISO strings and handles other non-JSON types.

    :param row: Row dictionary from DuckDB.
    :returns: JSON-serializable dictionary.
    """
    result = {}
    for key, value in row.items():
        if isinstance(value, date):
            result[key] = value.isoformat()
        elif isinstance(value, UUID):
            result[key] = str(value)
        else:
            result[key] = value
    return result


# Dataset discovery endpoints


@router.get("/status", response_model=AnalyticsStatusResponse, summary="Get analytics status")
def get_analytics_status(
    current_user: User = Depends(get_current_user),
) -> AnalyticsStatusResponse:
    """Get the status of the analytics system.

    Checks if DuckDB database and dbt manifest are available.

    :param current_user: Authenticated user.
    :returns: Analytics system status.
    """
    duckdb_ok = check_connection()
    datasets = get_datasets()

    return AnalyticsStatusResponse(
        duckdb_available=duckdb_ok,
        manifest_available=len(datasets) > 0,
        dataset_count=len(datasets),
        last_refresh=None,  # TODO: Track last refresh time
    )


@router.get("/datasets", response_model=DatasetListResponse, summary="List datasets")
def list_datasets(
    current_user: User = Depends(get_current_user),
) -> DatasetListResponse:
    """List available analytics datasets.

    Returns datasets marked with `meta.dataset: true` in dbt schema.yml.

    :param current_user: Authenticated user.
    :returns: List of available datasets.
    """
    datasets = get_datasets()

    return DatasetListResponse(
        datasets=[
            DatasetResponse(
                id=ds.id,
                friendly_name=ds.friendly_name,
                description=ds.description,
                group=ds.group,
                time_grain=ds.time_grain,
            )
            for ds in datasets
        ],
        total=len(datasets),
    )


@router.get(
    "/datasets/{dataset_id}/schema",
    response_model=DatasetSchemaResponse,
    summary="Get dataset schema",
)
def get_dataset_schema_endpoint(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
) -> DatasetSchemaResponse:
    """Get detailed schema for a dataset.

    :param dataset_id: Dataset model name (e.g., "fct_transactions").
    :param current_user: Authenticated user.
    :returns: Dataset with column definitions.
    :raises HTTPException: If dataset not found.
    """
    dataset = get_dataset_schema(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")

    return DatasetSchemaResponse(
        id=dataset.id,
        friendly_name=dataset.friendly_name,
        description=dataset.description,
        group=dataset.group,
        time_grain=dataset.time_grain,
        columns=[
            DatasetColumnResponse(
                name=col.name,
                description=col.description,
                data_type=col.data_type,
            )
            for col in (dataset.columns or [])
        ],
    )


# Generic dataset query endpoint


@router.get(
    "/datasets/{dataset_id}/query",
    response_model=DatasetQueryResponse,
    summary="Query a dataset",
)
def query_dataset(  # noqa: PLR0913
    dataset_id: str,
    start_date: date | None = Query(None, description="Start date filter"),
    end_date: date | None = Query(None, description="End date filter"),
    account_ids: list[UUID] = Query(default=[], description="Filter by account IDs"),
    tag_ids: list[UUID] = Query(default=[], description="Filter by tag IDs"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum rows to return"),
    offset: int = Query(0, ge=0, description="Number of rows to skip"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DatasetQueryResponse:
    """Query a dataset with optional filters.

    Returns rows from the specified dataset, filtered by the user's data.
    All queries are automatically scoped to the authenticated user.

    :param dataset_id: Dataset model name (e.g., "fct_transactions").
    :param start_date: Optional start date filter.
    :param end_date: Optional end date filter.
    :param account_ids: Optional filter by account IDs.
    :param tag_ids: Optional filter by tag IDs.
    :param limit: Maximum rows to return (default 1000, max 10000).
    :param offset: Number of rows to skip for pagination.
    :param db: Database session.
    :param current_user: Authenticated user.
    :returns: Query results.
    :raises HTTPException: If dataset not found or query fails.
    """
    # Validate dataset exists
    dataset = get_dataset_schema(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")

    # Validate filters
    valid_account_ids = (
        _validate_account_ids(db, current_user, account_ids) if account_ids else None
    )
    valid_tag_ids = _validate_tag_ids(db, current_user, tag_ids) if tag_ids else None

    # Build and execute query
    query, params = build_dataset_query(
        dataset=dataset,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        account_ids=valid_account_ids,
        tag_ids=valid_tag_ids,
        limit=limit,
        offset=offset,
    )

    try:
        rows = execute_query(query, params)
    except FileNotFoundError:
        logger.warning(f"DuckDB database not available for dataset query: {dataset_id}")
        return DatasetQueryResponse(
            dataset_id=dataset_id,
            rows=[],
            row_count=0,
            filters_applied={},
        )
    except Exception as e:
        logger.exception(f"Failed to execute dataset query: {e}")
        raise HTTPException(status_code=500, detail="Analytics query failed") from e

    # Build filters applied dict
    filters_applied: dict[str, Any] = {}
    if start_date:
        filters_applied["start_date"] = start_date.isoformat()
    if end_date:
        filters_applied["end_date"] = end_date.isoformat()
    if valid_account_ids:
        filters_applied["account_ids"] = [str(aid) for aid in valid_account_ids]
    if valid_tag_ids:
        filters_applied["tag_ids"] = [str(tid) for tid in valid_tag_ids]

    # Serialize rows for JSON response
    serialized_rows = [_serialize_row(row) for row in rows]

    return DatasetQueryResponse(
        dataset_id=dataset_id,
        rows=serialized_rows,
        row_count=len(serialized_rows),
        filters_applied=filters_applied,
    )


# Refresh endpoint


@router.post("/refresh", response_model=RefreshResponse, summary="Trigger analytics refresh")
def trigger_refresh(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RefreshResponse:
    """Trigger a refresh of analytics data.

    Runs dbt to rebuild mart tables from the latest PostgreSQL data.

    :param db: Database session.
    :param current_user: Authenticated user.
    :returns: Job information for tracking refresh progress.
    """
    # Create a job record to track the refresh
    job = Job(
        job_type=JobType.SYNC.value,  # Reusing SYNC type for analytics refresh
        status=JobStatus.PENDING.value,
        user_id=current_user.id,
        entity_type="analytics",
        entity_id=None,
    )
    db.add(job)
    db.flush()

    # Trigger dbt via Dagster
    # The dbt assets are configured to run together as a job
    run_id = trigger_job("dbt_build_job")

    if run_id:
        job.dagster_run_id = run_id
        job.status = JobStatus.RUNNING.value
        message = "Analytics refresh started"
        logger.info(f"Analytics refresh triggered: job_id={job.id}, run_id={run_id}")
    else:
        job.status = JobStatus.FAILED.value
        job.error_message = "Dagster unavailable"
        message = "Failed to trigger refresh - Dagster unavailable"
        logger.warning(f"Analytics refresh failed: job_id={job.id}, dagster unavailable")

    db.commit()

    return RefreshResponse(
        job_id=str(job.id),
        dagster_run_id=run_id,
        status=job.status,
        message=message,
    )
