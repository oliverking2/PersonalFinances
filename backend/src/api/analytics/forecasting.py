"""Forecasting API endpoints.

Provides simplified access to cash flow forecast data with computed values
like runway (days until balance goes negative).
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.api.dependencies import get_current_user
from src.api.responses import INTERNAL_ERROR, UNAUTHORIZED
from src.duckdb.client import execute_query
from src.postgres.auth.models import User

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Budget Integration Types
# ---------------------------------------------------------------------------


class BudgetForForecast:
    """Budget data needed for forecast calculations.

    :param budget_id: The budget's UUID.
    :param tag_id: Associated tag UUID.
    :param tag_name: Tag display name.
    :param amount: Budget amount.
    :param period: Budget period (weekly, monthly, etc.).
    :param period_start: Period start date.
    :param period_end: Period end date.
    :param spent_amount: Amount already spent in period.
    :param currency: Currency code.
    """

    def __init__(  # noqa: D107
        self,
        budget_id: str,
        tag_id: str,
        tag_name: str,
        amount: Decimal,
        period: str,
        period_start: date,
        period_end: date,
        spent_amount: Decimal,
        currency: str,
    ) -> None:
        self.budget_id = budget_id
        self.tag_id = tag_id
        self.tag_name = tag_name
        self.amount = amount
        self.period = period
        self.period_start = period_start
        self.period_end = period_end
        self.spent_amount = spent_amount
        self.currency = currency

    @property
    def days_in_period(self) -> int:
        """Total days in the budget period."""
        return (self.period_end - self.period_start).days + 1

    @property
    def remaining_amount(self) -> Decimal:
        """Amount remaining in budget after spending."""
        return max(Decimal("0"), self.amount - self.spent_amount)


# Scenario models


class PatternModification(BaseModel):
    """Modification to a recurring pattern for scenario analysis."""

    pattern_id: str = Field(..., description="Pattern ID to modify")
    new_amount: Decimal | None = Field(None, description="Override amount (None = exclude)")


class ScenarioRequest(BaseModel):
    """Request to calculate a 'what-if' forecast scenario."""

    exclude_patterns: list[str] = Field(
        default_factory=list, description="Pattern IDs to exclude from forecast"
    )
    exclude_planned: list[str] = Field(
        default_factory=list, description="Planned transaction IDs to exclude"
    )
    modifications: list[PatternModification] = Field(
        default_factory=list, description="Patterns with modified amounts"
    )


router = APIRouter()


class ForecastDayResponse(BaseModel):
    """A single day's forecast data."""

    forecast_date: date = Field(..., description="Date of the forecast")
    daily_change: Decimal = Field(..., description="Net cash flow for this day")
    daily_income: Decimal = Field(..., description="Total expected income")
    daily_expenses: Decimal = Field(..., description="Total expected expenses")
    event_count: int = Field(..., description="Number of cash flow events")
    projected_balance: Decimal = Field(..., description="Projected balance at end of day")
    days_from_now: int = Field(..., description="Days from today")
    forecast_week: int = Field(..., description="Week number in forecast (1-based)")


class ForecastSummaryResponse(BaseModel):
    """Summary statistics for the forecast period."""

    starting_balance: Decimal = Field(..., description="Starting net worth")
    ending_balance: Decimal = Field(..., description="Projected balance at end of forecast")
    total_income: Decimal = Field(..., description="Total expected income in period")
    total_expenses: Decimal = Field(..., description="Total expected expenses in period")
    net_change: Decimal = Field(..., description="Net change over forecast period")
    runway_days: int | None = Field(
        None, description="Days until balance goes negative (None if never)"
    )
    min_balance: Decimal = Field(..., description="Minimum projected balance in period")
    min_balance_date: date | None = Field(None, description="Date of minimum projected balance")


class CashFlowForecastResponse(BaseModel):
    """Complete cash flow forecast response."""

    currency: str = Field(..., description="Currency of all amounts")
    as_of_date: date = Field(..., description="Date of starting balance snapshot")
    summary: ForecastSummaryResponse = Field(..., description="Summary statistics")
    daily: list[ForecastDayResponse] = Field(..., description="Daily forecast data")


# Default forecast range in days (1 year to match dbt model)
DEFAULT_FORECAST_DAYS = 365
# Maximum forecast range in days (2 years)
MAX_FORECAST_DAYS = 730
# Calendar constants
DECEMBER = 12
LAST_QUARTER = 3


@router.get(
    "/forecast",
    response_model=CashFlowForecastResponse,
    summary="Get cash flow forecast",
    responses={**UNAUTHORIZED, **INTERNAL_ERROR},
)
def get_forecast(
    start_date: date | None = Query(None, description="Start date (defaults to today)"),
    end_date: date | None = Query(None, description="End date (defaults to start + 90 days)"),
    include_manual_assets: bool = Query(True, description="Include manual assets in net worth"),
    current_user: User = Depends(get_current_user),
) -> CashFlowForecastResponse:
    """Get cash flow forecast for a configurable date range.

    Combines recurring patterns (subscriptions, income) with planned transactions
    to project future balances. Includes runway calculation for financial planning.
    """
    # Normalise date range
    today = date.today()
    effective_start = start_date or today
    effective_end = end_date or (effective_start + timedelta(days=DEFAULT_FORECAST_DAYS))

    # Validate range
    if effective_end < effective_start:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    days_requested = (effective_end - effective_start).days + 1
    if days_requested > MAX_FORECAST_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Forecast range cannot exceed {MAX_FORECAST_DAYS} days (2 years)",
        )

    # For requests within the default range from today, try the cached dbt data first
    days_from_today = (effective_end - today).days
    use_cached = effective_start >= today and days_from_today <= DEFAULT_FORECAST_DAYS

    if use_cached:
        return _get_forecast_from_cache(
            current_user, effective_start, effective_end, include_manual_assets
        )

    # For extended ranges, compute dynamically
    return _compute_forecast_dynamically(
        current_user, effective_start, effective_end, include_manual_assets
    )


def _get_manual_assets_adjustment(user_id: str) -> Decimal:
    """Get the net impact of manual assets for adjusting forecast.

    :param user_id: User ID to query.
    :returns: Net manual assets value (assets - liabilities).
    """
    query = """
        SELECT
            COALESCE(SUM(CASE WHEN NOT is_liability THEN asset_value ELSE 0 END), 0)
            - COALESCE(SUM(CASE WHEN is_liability THEN asset_value ELSE 0 END), 0)
            AS net_manual_assets
        FROM main_mart.int_manual_asset_daily_values
        WHERE user_id = $user_id AND value_date = CURRENT_DATE
    """
    try:
        rows = execute_query(query, {"user_id": user_id})
        if rows and rows[0].get("net_manual_assets") is not None:
            return Decimal(str(rows[0]["net_manual_assets"]))
    except Exception:
        # If the query fails (e.g., table doesn't exist), return 0
        pass
    return Decimal("0")


def _fetch_budgets_for_forecast(user_id: str) -> list[BudgetForForecast]:
    """Fetch active budgets with current period spending.

    :param user_id: User ID to query.
    :returns: List of budgets with spending data.
    """
    query = """
        SELECT
            budget_id,
            tag_id,
            tag_name,
            budget_amount,
            currency,
            period,
            period_start,
            period_end,
            spent_amount
        FROM main_mart.fct_budget_vs_actual
        WHERE user_id = $user_id
    """
    try:
        rows = execute_query(query, {"user_id": user_id})
    except Exception as e:
        logger.warning(f"Failed to fetch budgets for forecast: {e}")
        return []

    budgets = []
    for row in rows:
        budgets.append(
            BudgetForForecast(
                budget_id=str(row["budget_id"]),
                tag_id=str(row["tag_id"]),
                tag_name=row["tag_name"],
                amount=Decimal(str(row["budget_amount"])),
                period=row["period"],
                period_start=row["period_start"],
                period_end=row["period_end"],
                spent_amount=Decimal(str(row["spent_amount"])),
                currency=row["currency"],
            )
        )
    return budgets


def _fetch_pattern_tag_mapping(user_id: str) -> dict[str, str]:
    """Get the primary tag for each recurring pattern based on matched transactions.

    Uses the most common tag from transactions linked to each pattern.

    :param user_id: User ID to query.
    :returns: Dictionary mapping pattern_id to tag_id.
    """
    # Query the most common tag for each pattern's matched transactions
    query = """
        WITH pattern_transaction_tags AS (
            -- Get tags for transactions linked to recurring patterns
            SELECT
                rpt.pattern_id,
                ts.tag_id,
                COUNT(*) AS tag_count
            FROM main_source.src_recurring_pattern_transactions rpt
            JOIN main_source.src_transaction_splits ts
                ON rpt.transaction_id = ts.transaction_id
            JOIN main_source.src_unified_recurring_patterns rp
                ON rpt.pattern_id = rp.id
            WHERE rp.user_id = $user_id
              AND ts.tag_id IS NOT NULL
            GROUP BY rpt.pattern_id, ts.tag_id
        ),
        ranked_tags AS (
            -- Rank tags by frequency for each pattern
            SELECT
                pattern_id,
                tag_id,
                tag_count,
                ROW_NUMBER() OVER (
                    PARTITION BY pattern_id
                    ORDER BY tag_count DESC
                ) AS rank
            FROM pattern_transaction_tags
        )
        SELECT pattern_id, tag_id
        FROM ranked_tags
        WHERE rank = 1
    """
    try:
        rows = execute_query(query, {"user_id": user_id})
    except Exception as e:
        logger.warning(f"Failed to fetch pattern-tag mapping: {e}")
        return {}

    return {str(row["pattern_id"]): str(row["tag_id"]) for row in rows}


def _calculate_pattern_monthly_equivalent(
    amount: Decimal, frequency: str, direction: str
) -> Decimal:
    """Calculate the monthly equivalent of a recurring pattern amount.

    :param amount: Pattern amount (positive).
    :param frequency: Pattern frequency (weekly, fortnightly, monthly, etc.).
    :param direction: 'income' or 'expense'.
    :returns: Monthly equivalent as positive amount.
    """
    multipliers = {
        "weekly": Decimal("4.33"),
        "fortnightly": Decimal("2.17"),
        "monthly": Decimal("1"),
        "quarterly": Decimal("0.33"),
        "annual": Decimal("0.083"),
    }
    multiplier = multipliers.get(frequency, Decimal("1"))
    return abs(amount) * multiplier


def _add_budget_events(
    daily_events: dict[date, list[dict[str, Any]]],
    budgets: list[BudgetForForecast],
    tag_pattern_monthly: dict[str, Decimal],
    forecast_dates: list[date],
) -> None:
    """Add budget-based expenses to daily events.

    For each budget, calculates remaining spending beyond tracked patterns and
    spreads it across the forecast period.

    :param daily_events: Dictionary to add events to (mutated).
    :param budgets: List of budgets with spending data.
    :param tag_pattern_monthly: Map of tag_id to monthly equivalent of patterns.
    :param forecast_dates: List of dates in the forecast period.
    """
    today = date.today()

    for budget in budgets:
        # Calculate monthly equivalent of patterns tagged with this budget
        pattern_monthly = tag_pattern_monthly.get(budget.tag_id, Decimal("0"))

        # Budget remainder = budget amount minus pattern spending
        # If patterns exceed budget, remainder is 0 (patterns alone cover it)
        budget_remainder = max(Decimal("0"), budget.amount - pattern_monthly)

        if budget_remainder <= 0:
            # Patterns fully cover or exceed budget, no additional expense needed
            continue

        # For each forecast date, check if it falls within a budget period
        # and add the prorated budget remainder as daily expense
        for fcast_date in forecast_dates:
            # Get the budget period containing this date
            period_start, period_end = _get_period_boundaries(budget.period, fcast_date)

            # Check if this is the current period (contains today)
            is_current_period = period_start <= today <= period_end

            if is_current_period:
                # For current period: use remaining budget spread over remaining days
                # remaining_budget = budget_amount - spent_amount (from BudgetForForecast)
                current_remaining = max(Decimal("0"), budget.remaining_amount - pattern_monthly)
                if current_remaining <= 0:
                    continue

                # Remaining days in period (from today to period end)
                remaining_days = (period_end - today).days + 1
                if remaining_days > 0 and fcast_date >= today:
                    daily_amount = current_remaining / Decimal(str(remaining_days))
                    daily_events[fcast_date].append(
                        {
                            "direction": "expense",
                            "amount": -abs(daily_amount),
                            "source": f"budget:{budget.tag_name}",
                        }
                    )
            # For future periods: spread full budget remainder across the period
            # Only add on the first day of each period to avoid duplication
            elif fcast_date == period_start:
                daily_events[fcast_date].append(
                    {
                        "direction": "expense",
                        "amount": -abs(budget_remainder),
                        "source": f"budget:{budget.tag_name}",
                    }
                )


def _get_period_boundaries(period: str, for_date: date) -> tuple[date, date]:
    """Get the start and end dates for a budget period containing the given date.

    :param period: Budget period (weekly, monthly, quarterly, annual).
    :param for_date: Date to find period for.
    :returns: Tuple of (period_start, period_end).
    """
    if period == "weekly":
        # ISO week: Monday to Sunday
        start = for_date - timedelta(days=for_date.weekday())
        end = start + timedelta(days=6)
    elif period == "monthly":
        start = for_date.replace(day=1)
        # Last day of month
        if for_date.month == DECEMBER:
            end = for_date.replace(year=for_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = for_date.replace(month=for_date.month + 1, day=1) - timedelta(days=1)
    elif period == "quarterly":
        quarter = (for_date.month - 1) // 3
        start = date(for_date.year, quarter * 3 + 1, 1)
        if quarter == LAST_QUARTER:
            end = date(for_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(for_date.year, (quarter + 1) * 3 + 1, 1) - timedelta(days=1)
    elif period == "annual":
        start = date(for_date.year, 1, 1)
        end = date(for_date.year, DECEMBER, 31)
    else:
        # Default to monthly
        start = for_date.replace(day=1)
        if for_date.month == DECEMBER:
            end = for_date.replace(year=for_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = for_date.replace(month=for_date.month + 1, day=1) - timedelta(days=1)

    return start, end


def _get_forecast_from_cache(
    current_user: User, start_date: date, end_date: date, include_manual_assets: bool = True
) -> CashFlowForecastResponse:
    """Get forecast from dbt-cached data (for ranges within 1 year from today)."""
    query = """
        SELECT
            forecast_date,
            currency,
            starting_balance,
            as_of_date,
            daily_change,
            daily_income,
            daily_expenses,
            event_count,
            cumulative_change,
            projected_balance,
            days_from_now,
            forecast_week
        FROM main_mart.fct_cash_flow_forecast
        WHERE user_id = $user_id
          AND forecast_date >= $start_date
          AND forecast_date <= $end_date
        ORDER BY forecast_date ASC
    """
    params = {"user_id": current_user.id, "start_date": start_date, "end_date": end_date}

    try:
        rows = execute_query(query, params)
    except FileNotFoundError:
        logger.warning("DuckDB database not available for forecast query")
        raise HTTPException(status_code=503, detail="Analytics database not available")
    except Exception as e:
        logger.exception(f"Failed to execute forecast query: {e}")
        raise HTTPException(status_code=500, detail="Forecast query failed") from e

    if not rows:
        raise HTTPException(status_code=404, detail="No forecast data available")

    # If excluding manual assets, adjust all balance values
    asset_adjustment = Decimal("0")
    if not include_manual_assets:
        asset_adjustment = _get_manual_assets_adjustment(str(current_user.id))
        # Adjust the rows - subtract manual assets from all balances
        rows = [
            {
                **row,
                "starting_balance": Decimal(str(row["starting_balance"])) - asset_adjustment,
                "projected_balance": Decimal(str(row["projected_balance"])) - asset_adjustment,
            }
            for row in rows
        ]

    return _build_forecast_response_from_rows(rows)


def _compute_forecast_dynamically(
    current_user: User, start_date: date, end_date: date, include_manual_assets: bool = True
) -> CashFlowForecastResponse:
    """Compute forecast dynamically for extended date ranges."""
    # Fetch data from DuckDB (same as scenario endpoint)
    patterns, planned, net_worth = _fetch_scenario_data(current_user.id, [], [])

    starting_balance = Decimal(str(net_worth["starting_balance"]))
    currency = str(net_worth["currency"])
    as_of_date = net_worth["as_of_date"]

    # If excluding manual assets, adjust the starting balance
    if not include_manual_assets:
        asset_adjustment = _get_manual_assets_adjustment(str(current_user.id))
        starting_balance -= asset_adjustment

    # Fetch budgets for forecast integration
    budgets = _fetch_budgets_for_forecast(str(current_user.id))

    # Generate forecast dates for the requested range
    days_count = (end_date - start_date).days + 1
    forecast_dates = [start_date + timedelta(days=i) for i in range(days_count)]

    # Build events and compute forecast (with budget integration)
    daily_events = _build_daily_events(patterns, planned, {}, forecast_dates, budgets)

    # Adjust starting balance if start_date is in the future
    # We need to account for events between today and start_date
    today = date.today()
    if start_date > today:
        lead_in_dates = [today + timedelta(days=i) for i in range((start_date - today).days)]
        lead_in_events = _build_daily_events(patterns, planned, {}, lead_in_dates)
        for d in lead_in_dates:
            for event in lead_in_events[d]:
                starting_balance += event["amount"]

    daily_data, summary = _compute_forecast_from_events(
        daily_events, forecast_dates, starting_balance
    )

    return CashFlowForecastResponse(
        currency=currency,
        as_of_date=as_of_date,
        summary=summary,
        daily=daily_data,
    )


def _build_forecast_response_from_rows(rows: list[dict[str, Any]]) -> CashFlowForecastResponse:
    """Build a CashFlowForecastResponse from database rows."""
    first_row = rows[0]
    last_row = rows[-1]

    # Calculate summary statistics
    total_income = sum((Decimal(str(r["daily_income"])) for r in rows), Decimal("0"))
    total_expenses = sum((Decimal(str(r["daily_expenses"])) for r in rows), Decimal("0"))

    # Find minimum balance and runway
    min_balance = Decimal(str(first_row["projected_balance"]))
    min_balance_date: date | None = first_row["forecast_date"]
    runway_days: int | None = None

    for row in rows:
        balance = Decimal(str(row["projected_balance"]))
        if balance < min_balance:
            min_balance = balance
            min_balance_date = row["forecast_date"]

        # Track first day balance goes negative
        if runway_days is None and balance < 0:
            runway_days = int(row["days_from_now"])

    starting_balance = Decimal(str(first_row["starting_balance"]))
    ending_balance = Decimal(str(last_row["projected_balance"]))

    summary = ForecastSummaryResponse(
        starting_balance=starting_balance,
        ending_balance=ending_balance,
        total_income=total_income,
        total_expenses=total_expenses,
        net_change=ending_balance - starting_balance,
        runway_days=runway_days,
        min_balance=min_balance,
        min_balance_date=min_balance_date,
    )

    daily = [
        ForecastDayResponse(
            forecast_date=row["forecast_date"],
            daily_change=Decimal(str(row["daily_change"])),
            daily_income=Decimal(str(row["daily_income"])),
            daily_expenses=Decimal(str(row["daily_expenses"])),
            event_count=int(row["event_count"]),
            projected_balance=Decimal(str(row["projected_balance"])),
            days_from_now=int(row["days_from_now"]),
            forecast_week=int(row["forecast_week"]),
        )
        for row in rows
    ]

    return CashFlowForecastResponse(
        currency=str(first_row["currency"]),
        as_of_date=first_row["as_of_date"],
        summary=summary,
        daily=daily,
    )


class ForecastWeeklyResponse(BaseModel):
    """Weekly aggregated forecast data."""

    week_number: int = Field(..., description="Week number (1-based)")
    week_start: date = Field(..., description="First day of the week")
    week_end: date = Field(..., description="Last day of the week")
    total_income: Decimal = Field(..., description="Total income for the week")
    total_expenses: Decimal = Field(..., description="Total expenses for the week")
    net_change: Decimal = Field(..., description="Net change for the week")
    ending_balance: Decimal = Field(..., description="Projected balance at week end")


class WeeklyForecastResponse(BaseModel):
    """Weekly aggregated forecast response."""

    currency: str = Field(..., description="Currency of all amounts")
    weeks: list[ForecastWeeklyResponse] = Field(..., description="Weekly forecast data")


@router.get(
    "/forecast/weekly",
    response_model=WeeklyForecastResponse,
    summary="Get weekly forecast summary",
    responses={**UNAUTHORIZED, **INTERNAL_ERROR},
)
def get_weekly_forecast(
    start_date: date | None = Query(None, description="Start date (defaults to today)"),
    end_date: date | None = Query(None, description="End date (defaults to start + 90 days)"),
    include_manual_assets: bool = Query(True, description="Include manual assets in net worth"),
    current_user: User = Depends(get_current_user),
) -> WeeklyForecastResponse:
    """Get weekly aggregated cash flow forecast for easier visualisation."""
    # Get daily forecast first (handles caching vs dynamic computation)
    daily_response = get_forecast(start_date, end_date, include_manual_assets, current_user)

    # Aggregate daily data into weeks
    weeks_map: dict[int, dict[str, Any]] = {}

    for day in daily_response.daily:
        week_num = day.forecast_week
        if week_num not in weeks_map:
            weeks_map[week_num] = {
                "week_start": day.forecast_date,
                "week_end": day.forecast_date,
                "total_income": Decimal("0"),
                "total_expenses": Decimal("0"),
                "net_change": Decimal("0"),
                "ending_balance": day.projected_balance,
            }

        week = weeks_map[week_num]
        week["week_end"] = day.forecast_date
        week["total_income"] += day.daily_income
        week["total_expenses"] += day.daily_expenses
        week["net_change"] += day.daily_change
        week["ending_balance"] = day.projected_balance  # Last day's balance

    weeks = [
        ForecastWeeklyResponse(
            week_number=week_num,
            week_start=data["week_start"],
            week_end=data["week_end"],
            total_income=data["total_income"],
            total_expenses=data["total_expenses"],
            net_change=data["net_change"],
            ending_balance=data["ending_balance"],
        )
        for week_num, data in sorted(weeks_map.items())
    ]

    return WeeklyForecastResponse(currency=daily_response.currency, weeks=weeks)


# ---------------------------------------------------------------------------
# Forecast Events Endpoint
# ---------------------------------------------------------------------------


class ForecastEventResponse(BaseModel):
    """A single cash flow event on a forecast date."""

    source_type: str = Field(..., description="Event source: 'recurring' or 'planned'")
    name: str = Field(..., description="Display name of the pattern or transaction")
    amount: Decimal = Field(..., description="Signed amount (negative for expenses)")
    frequency: str | None = Field(None, description="Recurrence frequency if applicable")


class ForecastEventsResponse(BaseModel):
    """Response containing all events for a specific forecast date."""

    forecast_date: date = Field(..., description="The date being queried")
    events: list[ForecastEventResponse] = Field(..., description="List of cash flow events")
    event_count: int = Field(..., description="Total number of events")


@router.get(
    "/forecast/events",
    response_model=ForecastEventsResponse,
    summary="Get forecast events for a specific date",
    responses={**UNAUTHORIZED, **INTERNAL_ERROR},
)
def get_forecast_events(
    forecast_date: date = Query(..., description="Date to get events for"),
    current_user: User = Depends(get_current_user),
) -> ForecastEventsResponse:
    """Get detailed transaction/pattern information for a specific forecast date."""
    # Fetch patterns and planned transactions
    patterns, planned, _ = _fetch_scenario_data(current_user.id, [], [])

    events: list[ForecastEventResponse] = []

    # Process recurring patterns
    for pat in patterns:
        next_date = pat["next_expected_date"]
        if isinstance(next_date, str):
            next_date = date.fromisoformat(next_date)

        if _matches_frequency(forecast_date, next_date, pat["frequency"]):
            direction = pat["direction"]
            raw_amount = Decimal(str(pat["expected_amount"]))
            signed_amount = abs(raw_amount) if direction == "income" else -abs(raw_amount)

            events.append(
                ForecastEventResponse(
                    source_type="recurring",
                    name=str(pat["display_name"]),
                    amount=signed_amount,
                    frequency=str(pat["frequency"]),
                )
            )

    # Process planned transactions
    for plan in planned:
        next_date = plan["next_expected_date"]
        end_date = plan.get("end_date")
        frequency = plan.get("frequency")

        if isinstance(next_date, str):
            next_date = date.fromisoformat(next_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)

        # Check if this planned transaction applies to the forecast date
        if end_date and forecast_date > end_date:
            continue

        if frequency:
            if _matches_frequency(forecast_date, next_date, frequency):
                events.append(
                    ForecastEventResponse(
                        source_type="planned",
                        name=str(plan["display_name"]),
                        amount=Decimal(str(plan["amount"])),
                        frequency=frequency,
                    )
                )
        elif forecast_date == next_date:
            # One-time planned transaction
            events.append(
                ForecastEventResponse(
                    source_type="planned",
                    name=str(plan["display_name"]),
                    amount=Decimal(str(plan["amount"])),
                    frequency=None,
                )
            )

    return ForecastEventsResponse(
        forecast_date=forecast_date,
        events=events,
        event_count=len(events),
    )


# Scenario calculation helpers


def _matches_frequency(fcast_date: date, next_date: date, frequency: str) -> bool:
    """Check if a forecast date matches the expected frequency pattern.

    :param fcast_date: The forecast date to check.
    :param next_date: The next expected date from the pattern.
    :param frequency: The frequency (weekly, fortnightly, monthly, quarterly, annual).
    :returns: True if the date matches the frequency pattern.
    """
    if fcast_date < next_date:
        return False

    days_diff = (fcast_date - next_date).days
    same_day = fcast_date.day == next_date.day
    month_diff = (fcast_date.year - next_date.year) * 12 + (fcast_date.month - next_date.month)

    result = False
    if frequency == "weekly":
        result = days_diff % 7 == 0
    elif frequency == "fortnightly":
        result = days_diff % 14 == 0
    elif frequency == "monthly":
        result = same_day
    elif frequency == "quarterly":
        result = same_day and month_diff >= 0 and month_diff % 3 == 0
    elif frequency == "annual":
        result = same_day and fcast_date.month == next_date.month

    return result


def _build_exclusion_clause(ids: list[str], prefix: str, params: dict[str, Any]) -> str:
    """Build a SQL exclusion clause for a list of IDs.

    :param ids: List of IDs to exclude.
    :param prefix: Parameter prefix for unique naming.
    :param params: Dictionary to add parameters to (mutated).
    :returns: SQL clause string like "AND col NOT IN ($p0,$p1)".
    """
    if not ids:
        return ""

    placeholders = []
    for i, pid in enumerate(ids):
        param_name = f"{prefix}_{i}"
        placeholders.append(f"${param_name}")
        params[param_name] = pid

    return f" AND id NOT IN ({','.join(placeholders)})"


def _fetch_scenario_data(
    user_id: Any,
    pattern_exclusions: list[str],
    planned_exclusions: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Fetch patterns, planned transactions, and net worth for scenario calculation.

    :param user_id: The user's ID.
    :param pattern_exclusions: Pattern IDs to exclude.
    :param planned_exclusions: Planned transaction IDs to exclude.
    :returns: Tuple of (patterns, planned, net_worth_row).
    :raises HTTPException: If database unavailable or no data found.
    """
    # Build patterns query with exclusions (include tag_id for budget linking)
    patterns_query = """
        SELECT pattern_id, display_name, direction, expected_amount, currency, frequency,
               next_expected_date, tag_id
        FROM main_mart.fct_recurring_patterns
        WHERE user_id = $user_id AND status NOT IN ('dismissed', 'paused')
          AND next_expected_date IS NOT NULL
    """
    params: dict[str, Any] = {"user_id": user_id}

    if pattern_exclusions:
        placeholders = []
        for i, pid in enumerate(pattern_exclusions):
            param_name = f"excl_{i}"
            placeholders.append(f"${param_name}")
            params[param_name] = pid
        patterns_query += f" AND pattern_id NOT IN ({','.join(placeholders)})"

    # Build planned transactions query with exclusions
    planned_query = """
        SELECT id AS transaction_id, name AS display_name,
               CASE WHEN amount > 0 THEN 'income' ELSE 'expense' END AS direction,
               amount, currency, frequency, next_expected_date, end_date
        FROM main_source.src_planned_transactions
        WHERE user_id = $user_id AND enabled = TRUE AND next_expected_date IS NOT NULL
          AND (end_date IS NULL OR end_date >= CURRENT_DATE)
    """
    planned_params: dict[str, Any] = {"user_id": user_id}

    if planned_exclusions:
        placeholders = []
        for i, pid in enumerate(planned_exclusions):
            param_name = f"pexcl_{i}"
            placeholders.append(f"${param_name}")
            planned_params[param_name] = pid
        planned_query += f" AND id NOT IN ({','.join(placeholders)})"

    net_worth_query = """
        SELECT net_worth AS starting_balance, currency, balance_date AS as_of_date
        FROM main_mart.fct_net_worth_history WHERE user_id = $user_id
        ORDER BY balance_date DESC LIMIT 1
    """

    try:
        patterns = execute_query(patterns_query, params)
        planned = execute_query(planned_query, planned_params)
        net_worth_rows = execute_query(net_worth_query, {"user_id": user_id})
    except FileNotFoundError:
        logger.warning("DuckDB database not available for scenario query")
        raise HTTPException(status_code=503, detail="Analytics database not available")
    except Exception as e:
        logger.exception(f"Failed to execute scenario query: {e}")
        raise HTTPException(status_code=500, detail="Scenario query failed") from e

    if not net_worth_rows:
        raise HTTPException(status_code=404, detail="No net worth data available")

    return patterns, planned, net_worth_rows[0]


def _build_daily_events(  # noqa: PLR0912
    patterns: list[dict[str, Any]],
    planned: list[dict[str, Any]],
    amount_mods: dict[str, Decimal],
    forecast_dates: list[date],
    budgets: list[BudgetForForecast] | None = None,
) -> dict[date, list[dict[str, Any]]]:
    """Build daily event dictionary from patterns, planned transactions, and budgets.

    :param patterns: Recurring patterns from database.
    :param planned: Planned transactions from database.
    :param amount_mods: Pattern ID to modified amount mapping.
    :param forecast_dates: List of dates in the forecast period.
    :param budgets: Optional list of budgets for forecast integration.
    :returns: Dictionary mapping dates to lists of cash flow events.
    """
    daily_events: dict[date, list[dict[str, Any]]] = {d: [] for d in forecast_dates}

    # Build a map of tag_id -> sum of monthly equivalent for patterns with that tag
    # This helps us calculate budget remainder (budget - tagged patterns)
    tag_pattern_monthly: dict[str, Decimal] = {}
    for pat in patterns:
        tag_id = pat.get("tag_id")
        if tag_id:
            monthly_equiv = _calculate_pattern_monthly_equivalent(
                Decimal(str(pat["expected_amount"])),
                pat["frequency"],
                pat["direction"],
            )
            tag_pattern_monthly[str(tag_id)] = (
                tag_pattern_monthly.get(str(tag_id), Decimal("0")) + monthly_equiv
            )

    # Process budget-based expenses (spending beyond tracked patterns)
    if budgets:
        _add_budget_events(daily_events, budgets, tag_pattern_monthly, forecast_dates)

    # Process recurring patterns
    for pat in patterns:
        pattern_id = str(pat["pattern_id"])
        direction = pat["direction"]
        raw_amount = amount_mods.get(pattern_id, Decimal(str(pat["expected_amount"])))
        signed_amount = abs(raw_amount) if direction == "income" else -abs(raw_amount)

        next_date = pat["next_expected_date"]
        if isinstance(next_date, str):
            next_date = date.fromisoformat(next_date)

        for fcast_date in forecast_dates:
            if _matches_frequency(fcast_date, next_date, pat["frequency"]):
                daily_events[fcast_date].append(
                    {
                        "direction": direction,
                        "amount": signed_amount,
                    }
                )

    # Process planned transactions
    for plan in planned:
        direction = plan["direction"]
        amount = Decimal(str(plan["amount"]))
        next_date = plan["next_expected_date"]
        end_date = plan.get("end_date")
        frequency = plan.get("frequency")

        if isinstance(next_date, str):
            next_date = date.fromisoformat(next_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)

        if frequency:
            for fcast_date in forecast_dates:
                if end_date and fcast_date > end_date:
                    continue
                if _matches_frequency(fcast_date, next_date, frequency):
                    daily_events[fcast_date].append({"direction": direction, "amount": amount})
        elif next_date in daily_events:
            daily_events[next_date].append({"direction": direction, "amount": amount})

    return daily_events


def _compute_forecast_from_events(
    daily_events: dict[date, list[dict[str, Any]]],
    forecast_dates: list[date],
    starting_balance: Decimal,
) -> tuple[list[ForecastDayResponse], ForecastSummaryResponse]:
    """Compute forecast response data from daily events.

    :param daily_events: Dictionary mapping dates to event lists.
    :param forecast_dates: Ordered list of forecast dates.
    :param starting_balance: Starting net worth balance.
    :returns: Tuple of (daily_data, summary).
    """
    daily_data: list[ForecastDayResponse] = []
    running_balance = starting_balance
    total_income = Decimal("0")
    total_expenses = Decimal("0")
    min_balance = starting_balance
    min_balance_date: date | None = None
    runway_days: int | None = None

    for i, fcast_date in enumerate(forecast_dates):
        events = daily_events[fcast_date]
        daily_change = sum((e["amount"] for e in events), Decimal("0"))
        daily_income = sum(
            (e["amount"] for e in events if e["direction"] == "income"), Decimal("0")
        )
        daily_expenses = sum(
            (abs(e["amount"]) for e in events if e["direction"] == "expense"), Decimal("0")
        )

        running_balance += daily_change
        total_income += daily_income
        total_expenses += daily_expenses

        if running_balance < min_balance:
            min_balance = running_balance
            min_balance_date = fcast_date

        if runway_days is None and running_balance < 0:
            runway_days = i

        daily_data.append(
            ForecastDayResponse(
                forecast_date=fcast_date,
                daily_change=daily_change,
                daily_income=daily_income,
                daily_expenses=daily_expenses,
                event_count=len(events),
                projected_balance=running_balance,
                days_from_now=i,
                forecast_week=(i // 7) + 1,
            )
        )

    summary = ForecastSummaryResponse(
        starting_balance=starting_balance,
        ending_balance=running_balance,
        total_income=total_income,
        total_expenses=total_expenses,
        net_change=running_balance - starting_balance,
        runway_days=runway_days,
        min_balance=min_balance,
        min_balance_date=min_balance_date,
    )

    return daily_data, summary


@router.post(
    "/forecast/scenario",
    response_model=CashFlowForecastResponse,
    summary="Calculate a 'what-if' forecast scenario",
    responses={**UNAUTHORIZED, **INTERNAL_ERROR},
)
def calculate_scenario(
    scenario: ScenarioRequest,
    current_user: User = Depends(get_current_user),
) -> CashFlowForecastResponse:
    """Calculate a modified forecast with excluded or adjusted patterns.

    Use this to model scenarios like 'what if I cancel this subscription?' or
    'what if my rent increases?'. Excludes specified patterns and applies amount
    modifications to show the projected impact on your balance.
    """
    # Build exclusion lists
    pattern_exclusions = scenario.exclude_patterns + [
        m.pattern_id for m in scenario.modifications if m.new_amount is None
    ]
    amount_mods = {m.pattern_id: m.new_amount for m in scenario.modifications if m.new_amount}

    # Fetch data from DuckDB
    patterns, planned, net_worth = _fetch_scenario_data(
        current_user.id, pattern_exclusions, scenario.exclude_planned
    )

    starting_balance = Decimal(str(net_worth["starting_balance"]))
    currency = str(net_worth["currency"])
    as_of_date = net_worth["as_of_date"]

    # Fetch budgets for forecast integration
    budgets = _fetch_budgets_for_forecast(str(current_user.id))

    # Generate forecast dates
    today = date.today()
    forecast_dates = [today + timedelta(days=i) for i in range(90)]

    # Build events and compute forecast (with budget integration)
    daily_events = _build_daily_events(patterns, planned, amount_mods, forecast_dates, budgets)
    daily_data, summary = _compute_forecast_from_events(
        daily_events, forecast_dates, starting_balance
    )

    return CashFlowForecastResponse(
        currency=currency,
        as_of_date=as_of_date,
        summary=summary,
        daily=daily_data,
    )
