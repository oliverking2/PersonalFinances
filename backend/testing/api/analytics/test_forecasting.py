"""Tests for forecasting API endpoints."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient


class TestGetForecast:
    """Tests for GET /api/analytics/forecast."""

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Unauthenticated requests are rejected."""
        response = client.get("/api/analytics/forecast")
        assert response.status_code == 401

    def test_returns_forecast_data(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Returns full forecast with summary and daily data."""
        today = date.today()
        mock_rows = [
            {
                "forecast_date": today,
                "currency": "GBP",
                "starting_balance": Decimal("10000.00"),
                "as_of_date": today - timedelta(days=1),
                "daily_change": Decimal("-50.00"),
                "daily_income": Decimal("0.00"),
                "daily_expenses": Decimal("50.00"),
                "event_count": 1,
                "cumulative_change": Decimal("-50.00"),
                "projected_balance": Decimal("9950.00"),
                "days_from_now": 0,
                "forecast_week": 1,
            },
            {
                "forecast_date": today + timedelta(days=1),
                "currency": "GBP",
                "starting_balance": Decimal("10000.00"),
                "as_of_date": today - timedelta(days=1),
                "daily_change": Decimal("2000.00"),
                "daily_income": Decimal("2000.00"),
                "daily_expenses": Decimal("0.00"),
                "event_count": 1,
                "cumulative_change": Decimal("1950.00"),
                "projected_balance": Decimal("11950.00"),
                "days_from_now": 1,
                "forecast_week": 1,
            },
        ]

        with patch("src.api.analytics.forecasting.execute_query", return_value=mock_rows):
            response = client.get("/api/analytics/forecast", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["currency"] == "GBP"
        assert data["as_of_date"] == (today - timedelta(days=1)).isoformat()

        # Check summary (Decimal serialized as strings)
        summary = data["summary"]
        assert summary["starting_balance"] == "10000.00"
        assert summary["ending_balance"] == "11950.00"
        assert summary["total_income"] == "2000.00"
        assert summary["total_expenses"] == "50.00"
        assert summary["net_change"] == "1950.00"
        assert summary["runway_days"] is None  # Never goes negative
        assert summary["min_balance"] == "9950.00"

        # Check daily data
        assert len(data["daily"]) == 2
        assert data["daily"][0]["forecast_date"] == today.isoformat()
        assert data["daily"][0]["daily_change"] == "-50.00"
        assert data["daily"][1]["projected_balance"] == "11950.00"

    def test_calculates_runway_when_balance_goes_negative(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Runway is calculated when projected balance goes negative."""
        today = date.today()
        mock_rows = [
            {
                "forecast_date": today,
                "currency": "GBP",
                "starting_balance": Decimal("1000.00"),
                "as_of_date": today - timedelta(days=1),
                "daily_change": Decimal("-200.00"),
                "daily_income": Decimal("0.00"),
                "daily_expenses": Decimal("200.00"),
                "event_count": 1,
                "cumulative_change": Decimal("-200.00"),
                "projected_balance": Decimal("800.00"),
                "days_from_now": 0,
                "forecast_week": 1,
            },
            {
                "forecast_date": today + timedelta(days=5),
                "currency": "GBP",
                "starting_balance": Decimal("1000.00"),
                "as_of_date": today - timedelta(days=1),
                "daily_change": Decimal("-200.00"),
                "daily_income": Decimal("0.00"),
                "daily_expenses": Decimal("200.00"),
                "event_count": 1,
                "cumulative_change": Decimal("-1200.00"),
                "projected_balance": Decimal("-200.00"),  # Goes negative
                "days_from_now": 5,
                "forecast_week": 1,
            },
        ]

        with patch("src.api.analytics.forecasting.execute_query", return_value=mock_rows):
            response = client.get("/api/analytics/forecast", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["runway_days"] == 5

    def test_returns_503_when_duckdb_unavailable(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Returns 503 when DuckDB database is not available."""
        with patch(
            "src.api.analytics.forecasting.execute_query",
            side_effect=FileNotFoundError("DuckDB not found"),
        ):
            response = client.get("/api/analytics/forecast", headers=api_auth_headers)

        assert response.status_code == 503
        assert "Analytics database not available" in response.json()["detail"]

    def test_returns_404_when_no_data(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Returns 404 when no forecast data exists for user."""
        with patch("src.api.analytics.forecasting.execute_query", return_value=[]):
            response = client.get("/api/analytics/forecast", headers=api_auth_headers)

        assert response.status_code == 404
        assert "No forecast data available" in response.json()["detail"]


class TestGetWeeklyForecast:
    """Tests for GET /api/analytics/forecast/weekly."""

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Unauthenticated requests are rejected."""
        response = client.get("/api/analytics/forecast/weekly")
        assert response.status_code == 401

    def test_returns_weekly_aggregated_data(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Returns weekly aggregated forecast data (aggregated from daily data)."""
        today = date.today()
        # Weekly endpoint now internally calls get_forecast, so we need daily format
        # Create 14 days of data across 2 weeks
        mock_rows = []
        for i in range(14):
            forecast_date = today + timedelta(days=i)
            week_num = (i // 7) + 1
            # Week 1: more income, Week 2: more expenses
            if i < 7:
                daily_income = Decimal("285.71")  # ~2000/7
                daily_expenses = Decimal("71.43")  # ~500/7
            else:
                daily_income = Decimal("0.00")
                daily_expenses = Decimal("114.29")  # ~800/7

            mock_rows.append(
                {
                    "forecast_date": forecast_date,
                    "currency": "GBP",
                    "starting_balance": Decimal("10000.00"),
                    "as_of_date": today,
                    "daily_change": daily_income - daily_expenses,
                    "daily_income": daily_income,
                    "daily_expenses": daily_expenses,
                    "event_count": 1,
                    "cumulative_change": Decimal("0.00"),
                    "projected_balance": Decimal("10000.00") + (i * Decimal("100.00")),
                    "days_from_now": i,
                    "forecast_week": week_num,
                }
            )

        with patch("src.api.analytics.forecasting.execute_query", return_value=mock_rows):
            response = client.get("/api/analytics/forecast/weekly", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["currency"] == "GBP"
        assert len(data["weeks"]) == 2

        week1 = data["weeks"][0]
        assert week1["week_number"] == 1
        # Week 1 has 7 days of income/expenses
        assert float(week1["total_income"]) > 0
        assert float(week1["total_expenses"]) > 0

    def test_returns_503_when_duckdb_unavailable(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Returns 503 when DuckDB database is not available."""
        with patch(
            "src.api.analytics.forecasting.execute_query",
            side_effect=FileNotFoundError("DuckDB not found"),
        ):
            response = client.get("/api/analytics/forecast/weekly", headers=api_auth_headers)

        assert response.status_code == 503

    def test_returns_404_when_no_data(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Returns 404 when no forecast data exists for user."""
        with patch("src.api.analytics.forecasting.execute_query", return_value=[]):
            response = client.get("/api/analytics/forecast/weekly", headers=api_auth_headers)

        assert response.status_code == 404


class TestCalculateScenario:
    """Tests for POST /api/analytics/forecast/scenario."""

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Unauthenticated requests are rejected."""
        response = client.post("/api/analytics/forecast/scenario", json={})
        assert response.status_code == 401

    def test_returns_scenario_forecast(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Returns modified forecast based on scenario parameters."""
        today = date.today()

        # Mock patterns data
        patterns = [
            {
                "pattern_id": "pattern-1",
                "display_name": "Netflix",
                "direction": "expense",
                "expected_amount": Decimal("15.99"),
                "currency": "GBP",
                "frequency": "monthly",
                "next_expected_date": today + timedelta(days=5),
            },
        ]

        # Mock planned transactions (empty)
        planned: list[dict] = []

        # Mock net worth
        net_worth = [
            {
                "starting_balance": Decimal("5000.00"),
                "currency": "GBP",
                "as_of_date": today - timedelta(days=1),
            }
        ]

        def mock_execute(query: str, params: dict | None = None) -> list:
            if "fct_recurring_patterns" in query:
                return patterns
            if "src_planned_transactions" in query:
                return planned
            if "fct_net_worth_history" in query:
                return net_worth
            return []

        with patch("src.api.analytics.forecasting.execute_query", side_effect=mock_execute):
            response = client.post(
                "/api/analytics/forecast/scenario",
                headers=api_auth_headers,
                json={},  # No exclusions - baseline scenario
            )

        assert response.status_code == 200
        data = response.json()

        assert data["currency"] == "GBP"
        assert len(data["daily"]) == 90
        # Starting balance should be preserved
        assert data["summary"]["starting_balance"] == "5000.00"

    def test_excludes_patterns_from_forecast(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Excluded patterns are not included in the forecast."""
        today = date.today()

        # Pattern that would be excluded
        patterns = [
            {
                "pattern_id": "pattern-to-exclude",
                "display_name": "Expensive Sub",
                "direction": "expense",
                "expected_amount": Decimal("100.00"),
                "currency": "GBP",
                "frequency": "monthly",
                "next_expected_date": today + timedelta(days=10),
            },
        ]

        planned: list[dict] = []
        net_worth = [
            {
                "starting_balance": Decimal("5000.00"),
                "currency": "GBP",
                "as_of_date": today - timedelta(days=1),
            }
        ]

        def mock_execute(query: str, params: dict | None = None) -> list:
            if "fct_recurring_patterns" in query:
                # Check if exclusion filter is applied
                if params and "excl_0" in params:
                    return []  # Pattern excluded
                return patterns
            if "src_planned_transactions" in query:
                return planned
            if "fct_net_worth_history" in query:
                return net_worth
            return []

        with patch("src.api.analytics.forecasting.execute_query", side_effect=mock_execute):
            response = client.post(
                "/api/analytics/forecast/scenario",
                headers=api_auth_headers,
                json={"exclude_patterns": ["pattern-to-exclude"]},
            )

        assert response.status_code == 200
        data = response.json()

        # With pattern excluded, no expenses should be recorded
        assert Decimal(data["summary"]["total_expenses"]) == Decimal("0")

    def test_applies_amount_modifications(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Amount modifications are applied to patterns."""
        today = date.today()

        patterns = [
            {
                "pattern_id": "rent-pattern",
                "display_name": "Rent",
                "direction": "expense",
                "expected_amount": Decimal("1000.00"),
                "currency": "GBP",
                "frequency": "monthly",
                "next_expected_date": today,  # Due today
            },
        ]

        planned: list[dict] = []
        net_worth = [
            {
                "starting_balance": Decimal("5000.00"),
                "currency": "GBP",
                "as_of_date": today - timedelta(days=1),
            }
        ]

        def mock_execute(query: str, params: dict | None = None) -> list:
            if "fct_recurring_patterns" in query:
                return patterns
            if "src_planned_transactions" in query:
                return planned
            if "fct_net_worth_history" in query:
                return net_worth
            return []

        with patch("src.api.analytics.forecasting.execute_query", side_effect=mock_execute):
            response = client.post(
                "/api/analytics/forecast/scenario",
                headers=api_auth_headers,
                json={"modifications": [{"pattern_id": "rent-pattern", "new_amount": "1200.00"}]},
            )

        assert response.status_code == 200
        data = response.json()

        # The first day should have the modified expense amount
        # Rent is monthly, so it appears on day 0 and around day 30, 60
        day_0 = data["daily"][0]
        assert day_0["daily_expenses"] == "1200.00"

    def test_returns_503_when_duckdb_unavailable(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Returns 503 when DuckDB database is not available."""
        with patch(
            "src.api.analytics.forecasting.execute_query",
            side_effect=FileNotFoundError("DuckDB not found"),
        ):
            response = client.post(
                "/api/analytics/forecast/scenario",
                headers=api_auth_headers,
                json={},
            )

        assert response.status_code == 503

    def test_returns_404_when_no_net_worth_data(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Returns 404 when no net worth data exists for user."""

        def mock_execute(query: str, params: dict | None = None) -> list:
            if "fct_recurring_patterns" in query:
                return []
            if "src_planned_transactions" in query:
                return []
            if "fct_net_worth_history" in query:
                return []  # No net worth data
            return []

        with patch("src.api.analytics.forecasting.execute_query", side_effect=mock_execute):
            response = client.post(
                "/api/analytics/forecast/scenario",
                headers=api_auth_headers,
                json={},
            )

        assert response.status_code == 404
        assert "No net worth data available" in response.json()["detail"]


class TestGetForecastDateRange:
    """Tests for GET /api/analytics/forecast with date range parameters."""

    def test_accepts_custom_date_range(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Custom date range parameters are applied to the query."""
        today = date.today()
        start = today
        end = today + timedelta(days=30)

        mock_rows = [
            {
                "forecast_date": start + timedelta(days=i),
                "currency": "GBP",
                "starting_balance": Decimal("10000.00"),
                "as_of_date": today,
                "daily_change": Decimal("0.00"),
                "daily_income": Decimal("0.00"),
                "daily_expenses": Decimal("0.00"),
                "event_count": 0,
                "cumulative_change": Decimal("0.00"),
                "projected_balance": Decimal("10000.00"),
                "days_from_now": i,
                "forecast_week": (i // 7) + 1,
            }
            for i in range(31)
        ]

        with patch("src.api.analytics.forecasting.execute_query", return_value=mock_rows):
            response = client.get(
                f"/api/analytics/forecast?start_date={start}&end_date={end}",
                headers=api_auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["daily"]) == 31

    def test_rejects_invalid_date_range(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Returns 400 when end_date is before start_date."""
        today = date.today()
        start = today + timedelta(days=30)
        end = today

        response = client.get(
            f"/api/analytics/forecast?start_date={start}&end_date={end}",
            headers=api_auth_headers,
        )

        assert response.status_code == 400
        assert "end_date must be after start_date" in response.json()["detail"]

    def test_rejects_range_exceeding_maximum(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Returns 400 when date range exceeds 730 days."""
        today = date.today()
        start = today
        end = today + timedelta(days=800)

        response = client.get(
            f"/api/analytics/forecast?start_date={start}&end_date={end}",
            headers=api_auth_headers,
        )

        assert response.status_code == 400
        assert "cannot exceed 730 days" in response.json()["detail"]


class TestGetForecastEvents:
    """Tests for GET /api/analytics/forecast/events."""

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Unauthenticated requests are rejected."""
        response = client.get("/api/analytics/forecast/events?forecast_date=2026-02-15")
        assert response.status_code == 401

    def test_returns_events_for_date(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Returns events that match the specified forecast date."""
        forecast_date = date.today() + timedelta(days=15)

        patterns = [
            {
                "pattern_id": "pattern-1",
                "display_name": "Netflix",
                "direction": "expense",
                "expected_amount": Decimal("15.99"),
                "currency": "GBP",
                "frequency": "monthly",
                "next_expected_date": forecast_date,  # Matches the query date
            },
        ]

        planned = [
            {
                "transaction_id": "planned-1",
                "display_name": "Car Insurance",
                "direction": "expense",
                "amount": Decimal("-450.00"),
                "currency": "GBP",
                "frequency": None,
                "next_expected_date": forecast_date,  # Matches the query date
                "end_date": None,
            },
        ]

        net_worth = [
            {
                "starting_balance": Decimal("5000.00"),
                "currency": "GBP",
                "as_of_date": date.today(),
            }
        ]

        def mock_execute(query: str, params: dict | None = None) -> list:
            if "fct_recurring_patterns" in query:
                return patterns
            if "src_planned_transactions" in query:
                return planned
            if "fct_net_worth_history" in query:
                return net_worth
            return []

        with patch("src.api.analytics.forecasting.execute_query", side_effect=mock_execute):
            response = client.get(
                f"/api/analytics/forecast/events?forecast_date={forecast_date}",
                headers=api_auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        assert data["forecast_date"] == forecast_date.isoformat()
        assert data["event_count"] == 2
        assert len(data["events"]) == 2

        # Check event details
        event_names = {e["name"] for e in data["events"]}
        assert "Netflix" in event_names
        assert "Car Insurance" in event_names

    def test_returns_empty_when_no_events(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Returns empty events list when no events match the date."""
        forecast_date = date.today() + timedelta(days=15)

        # No patterns or planned transactions match the date
        patterns = [
            {
                "pattern_id": "pattern-1",
                "display_name": "Netflix",
                "direction": "expense",
                "expected_amount": Decimal("15.99"),
                "currency": "GBP",
                "frequency": "monthly",
                "next_expected_date": date.today() + timedelta(days=30),  # Different date
            },
        ]

        net_worth = [
            {
                "starting_balance": Decimal("5000.00"),
                "currency": "GBP",
                "as_of_date": date.today(),
            }
        ]

        def mock_execute(query: str, params: dict | None = None) -> list:
            if "fct_recurring_patterns" in query:
                return patterns
            if "src_planned_transactions" in query:
                return []
            if "fct_net_worth_history" in query:
                return net_worth
            return []

        with patch("src.api.analytics.forecasting.execute_query", side_effect=mock_execute):
            response = client.get(
                f"/api/analytics/forecast/events?forecast_date={forecast_date}",
                headers=api_auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        assert data["event_count"] == 0
        assert len(data["events"]) == 0
