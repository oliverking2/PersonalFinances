"""Spending pace API endpoint.

Compares current month spending against a 90-day historical daily average
to show whether the user is spending faster or slower than usual.
"""

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.api.dependencies import get_current_user
from src.api.responses import INTERNAL_ERROR, UNAUTHORIZED
from src.duckdb.client import execute_query
from src.postgres.auth.models import User

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response Model
# ---------------------------------------------------------------------------


class SpendingPaceResponse(BaseModel):
    """Spending pace comparison for the current month."""

    month_spending_so_far: str = Field(description="Total spending this month so far")
    expected_spending: str = Field(description="Expected spending based on 90-day average")
    projected_month_total: str = Field(description="Projected total for the full month")
    pace_ratio: float | None = Field(description="Actual / expected ratio (>1 = spending faster)")
    pace_status: str = Field(description="ahead, on_track, behind, or no_history")
    amount_difference: str = Field(description="Actual minus expected (positive = overspending)")
    days_elapsed: int = Field(description="Days elapsed in current month")
    days_in_month: int = Field(description="Total days in current month")
    currency: str = Field(description="Currency code")


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/spending-pace",
    response_model=SpendingPaceResponse,
    summary="Get spending pace",
    responses={**UNAUTHORIZED, **INTERNAL_ERROR},
)
def get_spending_pace(
    current_user: User = Depends(get_current_user),
) -> SpendingPaceResponse:
    """Compare current month spending against a 90-day historical daily average."""
    query = """
        SELECT *
        FROM main_mart.fct_spending_pace
        WHERE user_id = $user_id
        ORDER BY month_spending_so_far DESC
        LIMIT 1
    """

    try:
        rows = execute_query(query, {"user_id": str(current_user.id)})
    except FileNotFoundError:
        logger.warning("DuckDB database not available for spending pace query")
        return _empty_response()
    except Exception as e:
        logger.exception(f"Failed to query spending pace: {e}")
        return _empty_response()

    if not rows:
        return _empty_response()

    row = rows[0]
    return SpendingPaceResponse(
        month_spending_so_far=str(row.get("month_spending_so_far", Decimal("0"))),
        expected_spending=str(row.get("expected_spending", Decimal("0"))),
        projected_month_total=str(row.get("projected_month_total", Decimal("0"))),
        pace_ratio=float(row["pace_ratio"]) if row.get("pace_ratio") is not None else None,
        pace_status=row.get("pace_status", "no_history"),
        amount_difference=str(row.get("amount_difference", Decimal("0"))),
        days_elapsed=int(row.get("days_elapsed", 0)),
        days_in_month=int(row.get("days_in_month", 0)),
        currency=row.get("currency", "GBP"),
    )


def _empty_response() -> SpendingPaceResponse:
    """Return a safe default response when no data is available.

    :returns: SpendingPaceResponse with zero values and no_history status.
    """
    return SpendingPaceResponse(
        month_spending_so_far="0",
        expected_spending="0",
        projected_month_total="0",
        pace_ratio=None,
        pace_status="no_history",
        amount_difference="0",
        days_elapsed=0,
        days_in_month=0,
        currency="GBP",
    )
