"""Tests for planned transactions API endpoints."""

from decimal import Decimal

from fastapi.testclient import TestClient


class TestPlannedTransactionEndpoints:
    """Tests for planned transaction CRUD endpoints."""

    def test_list_transactions_empty(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return empty list when no planned transactions exist."""
        response = client.get("/api/planned-transactions", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["transactions"] == []
        assert data["total"] == 0

    def test_create_income_transaction(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should create a planned income transaction."""
        response = client.post(
            "/api/planned-transactions",
            headers=api_auth_headers,
            json={
                "name": "Freelance Payment",
                "amount": 1500.00,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Freelance Payment"
        assert Decimal(str(data["amount"])) == Decimal("1500.00")
        assert data["direction"] == "income"
        assert data["enabled"] is True
        assert data["frequency"] is None

    def test_create_expense_transaction(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should create a planned expense transaction."""
        response = client.post(
            "/api/planned-transactions",
            headers=api_auth_headers,
            json={
                "name": "Annual Insurance",
                "amount": -600.00,
                "frequency": "annual",
                "next_expected_date": "2026-06-01T00:00:00Z",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Annual Insurance"
        assert Decimal(str(data["amount"])) == Decimal("-600.00")
        assert data["direction"] == "expense"
        assert data["frequency"] == "annual"
        assert "2026-06-01" in data["next_expected_date"]

    def test_create_with_end_date(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should create a recurring transaction with end date."""
        response = client.post(
            "/api/planned-transactions",
            headers=api_auth_headers,
            json={
                "name": "Temp Contract",
                "amount": 2000.00,
                "frequency": "monthly",
                "next_expected_date": "2026-02-01T00:00:00Z",
                "end_date": "2026-08-01T00:00:00Z",
                "notes": "6-month freelance contract",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["frequency"] == "monthly"
        assert "2026-02-01" in data["next_expected_date"]
        assert "2026-08-01" in data["end_date"]
        assert data["notes"] == "6-month freelance contract"

    def test_get_transaction_by_id(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should retrieve a specific planned transaction."""
        create_response = client.post(
            "/api/planned-transactions",
            headers=api_auth_headers,
            json={"name": "Test", "amount": 100.00},
        )
        transaction_id = create_response.json()["id"]

        response = client.get(
            f"/api/planned-transactions/{transaction_id}",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == transaction_id
        assert data["name"] == "Test"

    def test_get_transaction_not_found(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for non-existent transaction."""
        response = client.get(
            "/api/planned-transactions/00000000-0000-0000-0000-000000000000",
            headers=api_auth_headers,
        )

        assert response.status_code == 404

    def test_list_with_direction_filter(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should filter by direction."""
        # Create income and expense
        client.post(
            "/api/planned-transactions",
            headers=api_auth_headers,
            json={"name": "Income", "amount": 1000.00},
        )
        client.post(
            "/api/planned-transactions",
            headers=api_auth_headers,
            json={"name": "Expense", "amount": -200.00},
        )

        # Filter by income
        response = client.get(
            "/api/planned-transactions?direction=income",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["transactions"][0]["name"] == "Income"

    def test_list_enabled_only(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should filter to only enabled transactions."""
        # Create enabled and disabled
        client.post(
            "/api/planned-transactions",
            headers=api_auth_headers,
            json={"name": "Enabled", "amount": 100.00, "enabled": True},
        )
        client.post(
            "/api/planned-transactions",
            headers=api_auth_headers,
            json={"name": "Disabled", "amount": 200.00, "enabled": False},
        )

        response = client.get(
            "/api/planned-transactions?enabled_only=true",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["transactions"][0]["name"] == "Enabled"


class TestPlannedTransactionUpdate:
    """Tests for updating planned transactions."""

    def test_update_basic_fields(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should update name, amount, and currency."""
        create_response = client.post(
            "/api/planned-transactions",
            headers=api_auth_headers,
            json={"name": "Original", "amount": 100.00},
        )
        transaction_id = create_response.json()["id"]

        response = client.put(
            f"/api/planned-transactions/{transaction_id}",
            headers=api_auth_headers,
            json={"name": "Updated", "amount": 200.00, "currency": "EUR"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated"
        assert Decimal(str(data["amount"])) == Decimal("200.00")
        assert data["currency"] == "EUR"

    def test_update_frequency(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should update frequency from one-time to recurring."""
        create_response = client.post(
            "/api/planned-transactions",
            headers=api_auth_headers,
            json={"name": "Test", "amount": 100.00},
        )
        transaction_id = create_response.json()["id"]

        response = client.put(
            f"/api/planned-transactions/{transaction_id}",
            headers=api_auth_headers,
            json={"frequency": "monthly"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["frequency"] == "monthly"

    def test_clear_frequency(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should clear frequency to make one-time."""
        create_response = client.post(
            "/api/planned-transactions",
            headers=api_auth_headers,
            json={"name": "Test", "amount": 100.00, "frequency": "monthly"},
        )
        transaction_id = create_response.json()["id"]

        response = client.put(
            f"/api/planned-transactions/{transaction_id}",
            headers=api_auth_headers,
            json={"clear_frequency": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["frequency"] is None

    def test_update_enabled(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should update enabled state."""
        create_response = client.post(
            "/api/planned-transactions",
            headers=api_auth_headers,
            json={"name": "Test", "amount": 100.00},
        )
        transaction_id = create_response.json()["id"]

        response = client.put(
            f"/api/planned-transactions/{transaction_id}",
            headers=api_auth_headers,
            json={"enabled": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False

    def test_update_not_found(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 when updating non-existent transaction."""
        response = client.put(
            "/api/planned-transactions/00000000-0000-0000-0000-000000000000",
            headers=api_auth_headers,
            json={"name": "Test"},
        )

        assert response.status_code == 404


class TestPlannedTransactionDelete:
    """Tests for deleting planned transactions."""

    def test_delete_transaction(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should delete a planned transaction."""
        create_response = client.post(
            "/api/planned-transactions",
            headers=api_auth_headers,
            json={"name": "Test", "amount": 100.00},
        )
        transaction_id = create_response.json()["id"]

        response = client.delete(
            f"/api/planned-transactions/{transaction_id}",
            headers=api_auth_headers,
        )

        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(
            f"/api/planned-transactions/{transaction_id}",
            headers=api_auth_headers,
        )
        assert get_response.status_code == 404

    def test_delete_not_found(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 when deleting non-existent transaction."""
        response = client.delete(
            "/api/planned-transactions/00000000-0000-0000-0000-000000000000",
            headers=api_auth_headers,
        )

        assert response.status_code == 404


class TestPlannedTransactionSummary:
    """Tests for planned transaction summary endpoint."""

    def test_summary_empty(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return zeros when no transactions exist."""
        response = client.get(
            "/api/planned-transactions/summary",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_planned"] == 0
        assert data["income_count"] == 0
        assert data["expense_count"] == 0
        assert Decimal(str(data["monthly_income"])) == Decimal("0")
        assert Decimal(str(data["monthly_expenses"])) == Decimal("0")

    def test_summary_with_transactions(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return correct summary statistics."""
        # Create income and expenses
        client.post(
            "/api/planned-transactions",
            headers=api_auth_headers,
            json={"name": "Salary", "amount": 3000.00, "frequency": "monthly"},
        )
        client.post(
            "/api/planned-transactions",
            headers=api_auth_headers,
            json={"name": "Rent", "amount": -1200.00, "frequency": "monthly"},
        )

        response = client.get(
            "/api/planned-transactions/summary",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_planned"] == 2
        assert data["income_count"] == 1
        assert data["expense_count"] == 1
        assert Decimal(str(data["monthly_income"])) == Decimal("3000")
        assert Decimal(str(data["monthly_expenses"])) == Decimal("1200")
        assert Decimal(str(data["monthly_net"])) == Decimal("1800")


class TestPlannedTransactionAuth:
    """Tests for authentication requirements."""

    def test_list_requires_auth(self, client: TestClient) -> None:
        """Should return 401 without auth token."""
        response = client.get("/api/planned-transactions")
        assert response.status_code == 401

    def test_create_requires_auth(self, client: TestClient) -> None:
        """Should return 401 without auth token."""
        response = client.post(
            "/api/planned-transactions",
            json={"name": "Test", "amount": 100.00},
        )
        assert response.status_code == 401

    def test_get_requires_auth(self, client: TestClient) -> None:
        """Should return 401 without auth token."""
        response = client.get("/api/planned-transactions/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 401

    def test_update_requires_auth(self, client: TestClient) -> None:
        """Should return 401 without auth token."""
        response = client.put(
            "/api/planned-transactions/00000000-0000-0000-0000-000000000000",
            json={"name": "Test"},
        )
        assert response.status_code == 401

    def test_delete_requires_auth(self, client: TestClient) -> None:
        """Should return 401 without auth token."""
        response = client.delete("/api/planned-transactions/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 401
