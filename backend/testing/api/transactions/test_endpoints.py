"""Tests for transaction API endpoints."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.postgres.common.models import Account, Transaction

# test_institution_in_db, test_connection_in_db, and test_account_in_db
# are provided by the shared conftest.py


@pytest.fixture
def test_transactions_in_db(
    api_db_session: Session, test_account_in_db: Account
) -> list[Transaction]:
    """Create multiple transactions in the database."""
    now = datetime.now(UTC)
    transactions = [
        Transaction(
            account_id=test_account_in_db.id,
            provider_id="txn-001",
            booking_date=datetime(2024, 1, 15, tzinfo=UTC),
            value_date=datetime(2024, 1, 15, tzinfo=UTC),
            amount=Decimal("-50.00"),
            currency="GBP",
            counterparty_name="Tesco",
            description="Groceries",
            category="groceries",
            synced_at=now,
        ),
        Transaction(
            account_id=test_account_in_db.id,
            provider_id="txn-002",
            booking_date=datetime(2024, 1, 14, tzinfo=UTC),
            value_date=datetime(2024, 1, 14, tzinfo=UTC),
            amount=Decimal("3000.00"),
            currency="GBP",
            counterparty_name="Acme Corp",
            description="Salary",
            category="income",
            synced_at=now,
        ),
        Transaction(
            account_id=test_account_in_db.id,
            provider_id="txn-003",
            booking_date=datetime(2024, 1, 13, tzinfo=UTC),
            value_date=datetime(2024, 1, 13, tzinfo=UTC),
            amount=Decimal("-15.99"),
            currency="GBP",
            counterparty_name="Netflix",
            description="Subscription",
            category="subscriptions",
            synced_at=now,
        ),
    ]
    for txn in transactions:
        api_db_session.add(txn)
    api_db_session.commit()
    return transactions


class TestListTransactions:
    """Tests for GET /api/transactions endpoint."""

    def test_returns_transactions_for_user(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_transactions_in_db: list[Transaction],
    ) -> None:
        """Should return transactions for authenticated user."""
        response = client.get("/api/transactions", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["transactions"]) == 3
        assert data["page"] == 1
        assert data["page_size"] == 50

    def test_returns_transactions_ordered_by_date_desc(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_transactions_in_db: list[Transaction],
    ) -> None:
        """Should return transactions ordered by booking date descending."""
        response = client.get("/api/transactions", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        dates = [t["booking_date"] for t in data["transactions"]]
        assert dates == sorted(dates, reverse=True)

    def test_filters_by_account_ids(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_transactions_in_db: list[Transaction],
        test_account_in_db: Account,
    ) -> None:
        """Should filter transactions by account_ids."""
        response = client.get(
            f"/api/transactions?account_ids={test_account_in_db.id}",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert all(t["account_id"] == str(test_account_in_db.id) for t in data["transactions"])

    def test_filters_by_date_range(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_transactions_in_db: list[Transaction],
    ) -> None:
        """Should filter transactions by date range."""
        response = client.get(
            "/api/transactions?start_date=2024-01-14&end_date=2024-01-15",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        dates = [t["booking_date"] for t in data["transactions"]]
        assert all("2024-01-14" <= d <= "2024-01-15" for d in dates)

    def test_filters_by_min_amount(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_transactions_in_db: list[Transaction],
    ) -> None:
        """Should filter transactions by minimum amount."""
        response = client.get(
            "/api/transactions?min_amount=0",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1  # Only the salary
        assert float(data["transactions"][0]["amount"]) > 0

    def test_filters_by_search(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_transactions_in_db: list[Transaction],
    ) -> None:
        """Should filter transactions by search term."""
        response = client.get(
            "/api/transactions?search=Netflix",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["transactions"][0]["merchant_name"] == "Netflix"

    def test_paginates_results(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_transactions_in_db: list[Transaction],
    ) -> None:
        """Should paginate results."""
        response = client.get(
            "/api/transactions?page=1&page_size=2",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["transactions"]) == 2
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["page_size"] == 2

    def test_returns_empty_for_invalid_account_id(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_transactions_in_db: list[Transaction],
    ) -> None:
        """Should return empty results for account not owned by user."""
        response = client.get(
            f"/api/transactions?account_ids={uuid4()}",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["transactions"]) == 0

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Should return 401 without authentication."""
        response = client.get("/api/transactions")

        assert response.status_code == 401

    def test_transaction_response_format(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_transactions_in_db: list[Transaction],
        test_account_in_db: Account,
    ) -> None:
        """Should return transactions in expected format with correct values."""
        response = client.get("/api/transactions", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        # First transaction is most recent (2024-01-15, Tesco)
        txn = data["transactions"][0]

        # Verify actual values match fixture data, not just key presence
        assert txn["id"] == str(test_transactions_in_db[0].id)
        assert txn["account_id"] == str(test_account_in_db.id)
        assert txn["booking_date"] == "2024-01-15"
        assert txn["value_date"] == "2024-01-15"
        assert float(txn["amount"]) == -50.00
        assert txn["currency"] == "GBP"
        assert txn["description"] == "Groceries"
        assert txn["merchant_name"] == "Tesco"
        assert txn["category"] == "groceries"
        # Check tags and splits are arrays (even if empty)
        assert isinstance(txn["tags"], list)
        assert isinstance(txn["splits"], list)
