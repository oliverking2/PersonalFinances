"""Analytics API endpoints."""

import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.analytics.exports import router as exports_router
from src.api.analytics.forecasting import router as forecasting_router
from src.api.analytics.models import (
    AnalyticsStatusResponse,
    DatasetColumnResponse,
    DatasetFiltersResponse,
    DatasetListResponse,
    DatasetQueryResponse,
    DatasetResponse,
    DatasetSchemaResponse,
    EnumFilterResponse,
    NumericFilterResponse,
    RefreshResponse,
)
from src.api.common.helpers import get_user_account_ids
from src.api.dependencies import get_current_user, get_db
from src.api.responses import INTERNAL_ERROR, RESOURCE_RESPONSES, UNAUTHORIZED
from src.duckdb.client import check_connection, execute_query
from src.duckdb.manifest import DatasetFilters, get_dataset_schema, get_datasets
from src.duckdb.queries import build_dataset_query
from src.filepaths import DUCKDB_PATH
from src.postgres.auth.models import User
from src.postgres.common.enums import JobStatus, JobType
from src.postgres.common.models import Job
from src.postgres.common.operations.tags import get_tags_by_user_id
from src.providers.dagster import trigger_job

logger = logging.getLogger(__name__)

router = APIRouter()

# Include sub-routers
router.include_router(exports_router)
router.include_router(forecasting_router)


def _get_last_refresh_time() -> datetime | None:
    """Get the last time the DuckDB database was modified.

    :returns: Modification time as UTC datetime, or None if file doesn't exist.
    """
    if not DUCKDB_PATH.exists():
        return None
    mtime = DUCKDB_PATH.stat().st_mtime
    return datetime.fromtimestamp(mtime, tz=UTC)


def _validate_account_ids(db: Session, user: User, account_ids: list[UUID]) -> list[UUID]:
    """Validate and filter account IDs to those owned by the user.

    :param db: Database session.
    :param user: Authenticated user.
    :param account_ids: Requested account IDs.
    :returns: Valid account IDs owned by user.
    """
    user_account_ids = set(get_user_account_ids(db, user))
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

    - Normalizes column names to snake_case
    - Converts date objects to ISO strings
    - Converts Decimal to int/float
    - Handles other non-JSON types

    :param row: Row dictionary from DuckDB.
    :returns: JSON-serializable dictionary with snake_case keys.
    """
    result: dict[str, Any] = {}
    for key, value in row.items():
        # Normalize column name to snake_case
        key_normalized = key.lower()

        if isinstance(value, date):
            result[key_normalized] = value.isoformat()
        elif isinstance(value, UUID):
            result[key_normalized] = str(value)
        elif isinstance(value, Decimal):
            # Convert to int if whole number, otherwise float
            result[key_normalized] = (
                int(value) if value == value.to_integral_value() else float(value)
            )
        else:
            result[key_normalized] = value
    return result


def _build_filters_response(filters: DatasetFilters) -> DatasetFiltersResponse:
    """Build a DatasetFiltersResponse from a DatasetFilters object.

    :param filters: Internal DatasetFilters object.
    :returns: API response model.
    """
    return DatasetFiltersResponse(
        date_column=filters.date_column,
        account_id_column=filters.account_id_column,
        tag_id_column=filters.tag_id_column,
        enum_filters=[
            EnumFilterResponse(name=f.name, label=f.label, options=f.options)
            for f in filters.enum_filters
        ],
        numeric_filters=[
            NumericFilterResponse(name=f.name, label=f.label) for f in filters.numeric_filters
        ],
    )


# Dataset discovery endpoints


@router.get(
    "/status",
    response_model=AnalyticsStatusResponse,
    summary="Get analytics status",
    responses=UNAUTHORIZED,
)
def get_analytics_status(
    current_user: User = Depends(get_current_user),
) -> AnalyticsStatusResponse:
    """Check if DuckDB database and dbt manifest are available."""
    duckdb_ok = check_connection()
    datasets = get_datasets()

    return AnalyticsStatusResponse(
        duckdb_available=duckdb_ok,
        manifest_available=len(datasets) > 0,
        dataset_count=len(datasets),
        last_refresh=_get_last_refresh_time(),
    )


@router.get(
    "/datasets",
    response_model=DatasetListResponse,
    summary="List datasets",
    responses=UNAUTHORIZED,
)
def list_datasets(
    current_user: User = Depends(get_current_user),
) -> DatasetListResponse:
    """List available analytics datasets from dbt manifest."""
    datasets = get_datasets()

    return DatasetListResponse(
        datasets=[
            DatasetResponse(
                id=ds.id,
                dataset_name=ds.name,
                friendly_name=ds.friendly_name,
                description=ds.description,
                group=ds.group,
                time_grain=ds.time_grain,
                filters=_build_filters_response(ds.filters),
            )
            for ds in datasets
        ],
        total=len(datasets),
    )


@router.get(
    "/datasets/{dataset_id}/schema",
    response_model=DatasetSchemaResponse,
    summary="Get dataset schema",
    responses=RESOURCE_RESPONSES,
)
def get_dataset_schema_endpoint(
    dataset_id: UUID,
    current_user: User = Depends(get_current_user),
) -> DatasetSchemaResponse:
    """Get detailed schema for a dataset including column definitions."""
    dataset = get_dataset_schema(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")

    return DatasetSchemaResponse(
        id=dataset.id,
        dataset_name=dataset.name,
        friendly_name=dataset.friendly_name,
        description=dataset.description,
        group=dataset.group,
        time_grain=dataset.time_grain,
        filters=_build_filters_response(dataset.filters),
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
    responses={**RESOURCE_RESPONSES, **INTERNAL_ERROR},
)
def query_dataset(
    dataset_id: UUID,
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

    Results are automatically scoped to the authenticated user's data.
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
        logger.warning(f"DuckDB database not available for dataset query: {dataset.name}")
        return DatasetQueryResponse(
            dataset_id=dataset.id,
            dataset_name=dataset.name,
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
        dataset_id=dataset.id,
        dataset_name=dataset.name,
        rows=serialized_rows,
        row_count=len(serialized_rows),
        filters_applied=filters_applied,
    )


# Refresh endpoint


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    summary="Trigger analytics refresh",
    responses=UNAUTHORIZED,
)
def trigger_refresh(
    redirect_to: str | None = Query(
        None, description="URL to redirect to after completion (for notifications)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RefreshResponse:
    """Trigger a dbt rebuild of mart tables from the latest PostgreSQL data."""
    # Create a job record to track the refresh
    job = Job(
        job_type=JobType.SYNC.value,  # Reusing SYNC type for analytics refresh
        status=JobStatus.PENDING.value,
        user_id=current_user.id,
        entity_type="analytics",
        entity_id=None,
        job_metadata={"redirect_to": redirect_to} if redirect_to else {},
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
