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
        """Returns weekly aggregated forecast data."""
        today = date.today()
        mock_rows = [
            {
                "forecast_week": 1,
                "week_start": today,
                "week_end": today + timedelta(days=6),
                "total_income": Decimal("2000.00"),
                "total_expenses": Decimal("500.00"),
                "net_change": Decimal("1500.00"),
                "ending_balance": Decimal("11500.00"),
                "currency": "GBP",
            },
            {
                "forecast_week": 2,
                "week_start": today + timedelta(days=7),
                "week_end": today + timedelta(days=13),
                "total_income": Decimal("0.00"),
                "total_expenses": Decimal("800.00"),
                "net_change": Decimal("-800.00"),
                "ending_balance": Decimal("10700.00"),
                "currency": "GBP",
            },
        ]

        with patch("src.api.analytics.forecasting.execute_query", return_value=mock_rows):
            response = client.get("/api/analytics/forecast/weekly", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["currency"] == "GBP"
        assert len(data["weeks"]) == 2

        week1 = data["weeks"][0]
        assert week1["week_number"] == 1
        assert week1["total_income"] == "2000.00"
        assert week1["total_expenses"] == "500.00"
        assert week1["net_change"] == "1500.00"
        assert week1["ending_balance"] == "11500.00"

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
