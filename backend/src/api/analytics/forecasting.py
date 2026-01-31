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


@router.get(
    "/forecast",
    response_model=CashFlowForecastResponse,
    summary="Get cash flow forecast",
    responses={**UNAUTHORIZED, **INTERNAL_ERROR},
)
def get_forecast(
    start_date: date | None = Query(None, description="Start date (defaults to today)"),
    end_date: date | None = Query(None, description="End date (defaults to start + 90 days)"),
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
        return _get_forecast_from_cache(current_user, effective_start, effective_end)

    # For extended ranges, compute dynamically
    return _compute_forecast_dynamically(current_user, effective_start, effective_end)


def _get_forecast_from_cache(
    current_user: User, start_date: date, end_date: date
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

    return _build_forecast_response_from_rows(rows)


def _compute_forecast_dynamically(
    current_user: User, start_date: date, end_date: date
) -> CashFlowForecastResponse:
    """Compute forecast dynamically for extended date ranges."""
    # Fetch data from DuckDB (same as scenario endpoint)
    patterns, planned, net_worth = _fetch_scenario_data(current_user.id, [], [])

    starting_balance = Decimal(str(net_worth["starting_balance"]))
    currency = str(net_worth["currency"])
    as_of_date = net_worth["as_of_date"]

    # Generate forecast dates for the requested range
    days_count = (end_date - start_date).days + 1
    forecast_dates = [start_date + timedelta(days=i) for i in range(days_count)]

    # Build events and compute forecast
    daily_events = _build_daily_events(patterns, planned, {}, forecast_dates)

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
    current_user: User = Depends(get_current_user),
) -> WeeklyForecastResponse:
    """Get weekly aggregated cash flow forecast for easier visualisation."""
    # Get daily forecast first (handles caching vs dynamic computation)
    daily_response = get_forecast(start_date, end_date, current_user)

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
    # Build patterns query with exclusions
    patterns_query = """
        SELECT pattern_id, display_name, direction, expected_amount, currency, frequency,
               next_expected_date
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


def _build_daily_events(
    patterns: list[dict[str, Any]],
    planned: list[dict[str, Any]],
    amount_mods: dict[str, Decimal],
    forecast_dates: list[date],
) -> dict[date, list[dict[str, Any]]]:
    """Build daily event dictionary from patterns and planned transactions.

    :param patterns: Recurring patterns from database.
    :param planned: Planned transactions from database.
    :param amount_mods: Pattern ID to modified amount mapping.
    :param forecast_dates: List of dates in the forecast period.
    :returns: Dictionary mapping dates to lists of cash flow events.
    """
    daily_events: dict[date, list[dict[str, Any]]] = {d: [] for d in forecast_dates}

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

    # Generate forecast dates
    today = date.today()
    forecast_dates = [today + timedelta(days=i) for i in range(90)]

    # Build events and compute forecast
    daily_events = _build_daily_events(patterns, planned, amount_mods, forecast_dates)
    daily_data, summary = _compute_forecast_from_events(
        daily_events, forecast_dates, starting_balance
    )

    return CashFlowForecastResponse(
        currency=currency,
        as_of_date=as_of_date,
        summary=summary,
        daily=daily_data,
    )
