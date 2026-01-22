"""Transaction API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.api.transactions.models import TransactionListResponse, TransactionQueryParams

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=TransactionListResponse, summary="List transactions")
def list_transactions(
    params: TransactionQueryParams = Depends(),
    db: Session = Depends(get_db),
) -> TransactionListResponse:
    """List transactions with optional filters.

    Transactions are stored in S3 as Parquet files and queried via DuckDB.

    :param params: Query parameters for filtering.
    :param db: Database session.
    :returns: List of transactions.
    """
    # TODO: Implement transaction querying from DuckDB/S3
    _ = params
    raise HTTPException(status_code=501, detail="Not implemented yet")
