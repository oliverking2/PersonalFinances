"""Tests for spending pace API endpoint."""

from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient


class TestGetSpendingPace:
    """Tests for GET /api/analytics/spending-pace."""

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Unauthenticated requests are rejected."""
        response = client.get("/api/analytics/spending-pace")
        assert response.status_code == 401

    def test_returns_pace_data(self, client: TestClient, api_auth_headers: dict[str, str]) -> None:
        """Returns spending pace with valid data."""
        mock_rows = [
            {
                "user_id": "test-user-id",
                "currency": "GBP",
                "month_spending_so_far": Decimal("450.00"),
                "days_elapsed": 15,
                "days_in_month": 28,
                "avg_daily_spending": Decimal("18.50"),
                "expected_spending": Decimal("277.50"),
                "projected_month_total": Decimal("518.00"),
                "pace_ratio": Decimal("1.62"),
                "pace_status": "ahead",
                "amount_difference": Decimal("172.50"),
            }
        ]

        with patch(
            "src.api.analytics.spending_pace.execute_query",
            return_value=mock_rows,
        ):
            response = client.get("/api/analytics/spending-pace", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["month_spending_so_far"] == "450.00"
        assert data["expected_spending"] == "277.50"
        assert data["projected_month_total"] == "518.00"
        assert data["pace_ratio"] == 1.62
        assert data["pace_status"] == "ahead"
        assert data["amount_difference"] == "172.50"
        assert data["days_elapsed"] == 15
        assert data["days_in_month"] == 28
        assert data["currency"] == "GBP"

    def test_returns_no_history_when_no_data(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Returns safe defaults when no data is available."""
        with patch(
            "src.api.analytics.spending_pace.execute_query",
            return_value=[],
        ):
            response = client.get("/api/analytics/spending-pace", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["pace_status"] == "no_history"
        assert data["month_spending_so_far"] == "0"
        assert data["expected_spending"] == "0"
        assert data["pace_ratio"] is None

    def test_returns_defaults_when_duckdb_unavailable(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Returns safe defaults when DuckDB is not available."""
        with patch(
            "src.api.analytics.spending_pace.execute_query",
            side_effect=FileNotFoundError("DuckDB not found"),
        ):
            response = client.get("/api/analytics/spending-pace", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["pace_status"] == "no_history"
        assert data["pace_ratio"] is None

    def test_returns_defaults_on_query_error(
        self, client: TestClient, api_auth_headers: dict[str, str]
    ) -> None:
        """Returns safe defaults when query fails."""
        with patch(
            "src.api.analytics.spending_pace.execute_query",
            side_effect=RuntimeError("Query failed"),
        ):
            response = client.get("/api/analytics/spending-pace", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["pace_status"] == "no_history"
