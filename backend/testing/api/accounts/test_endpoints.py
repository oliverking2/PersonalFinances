"""Tests for account API endpoints."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.accounts.endpoints import _normalize_credit_card_balance
from src.postgres.auth.models import User
from src.postgres.common.enums import AccountCategory, AccountStatus, ConnectionStatus, Provider
from src.postgres.common.models import Account, Connection, Institution
from src.utils.security import create_access_token, hash_password

# test_institution_in_db, test_connection_in_db, and test_account_in_db
# are provided by the shared conftest.py


@pytest.fixture
def test_account_with_balance_in_db(
    api_db_session: Session, test_connection_in_db: Connection
) -> Account:
    """Create an account with balance fields populated."""
    account = Account(
        connection_id=test_connection_in_db.id,
        provider_id="test-gc-account-with-balance",
        status=AccountStatus.ACTIVE.value,
        name="Test Account With Balance",
        display_name="My Account",
        iban="GB00TEST00000000001234",
        currency="GBP",
        balance_amount=Decimal("1234.56"),
        balance_currency="GBP",
        balance_type="interimAvailable",
        balance_updated_at=datetime.now(),
    )
    api_db_session.add(account)
    api_db_session.commit()
    return account


class TestListAccounts:
    """Tests for GET /api/accounts endpoint."""

    def test_returns_all_user_accounts(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_account_in_db: Account,
    ) -> None:
        """Should return all accounts for authenticated user."""
        response = client.get("/api/accounts", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["accounts"]) >= 1

        acc = data["accounts"][0]
        assert acc["id"] == str(test_account_in_db.id)
        assert acc["connection_id"] == str(test_account_in_db.connection_id)
        assert acc["name"] == "Test Account"
        assert acc["display_name"] == "My Account"
        assert acc["status"] == "active"

    def test_filters_by_connection_id(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_account_in_db: Account,
        test_connection_in_db: Connection,
    ) -> None:
        """Should filter accounts by connection_id."""
        response = client.get(
            f"/api/accounts?connection_id={test_connection_in_db.id}",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert all(
            acc["connection_id"] == str(test_connection_in_db.id) for acc in data["accounts"]
        )

    def test_returns_404_for_invalid_connection_id(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_institution_in_db: Institution,
    ) -> None:
        """Should return 404 for connection not owned by user."""
        response = client.get(
            f"/api/accounts?connection_id={uuid4()}",
            headers=api_auth_headers,
        )

        assert response.status_code == 404

    def test_includes_balance_when_available(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_account_with_balance_in_db: Account,
    ) -> None:
        """Should include balance in response when available."""
        response = client.get("/api/accounts", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        acc = data["accounts"][0]
        assert acc["balance"] is not None
        assert acc["balance"]["amount"] == 1234.56
        assert acc["balance"]["currency"] == "GBP"
        assert acc["balance"]["type"] == "interimAvailable"

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """Should return 401 without authentication."""
        response = client.get("/api/accounts")

        assert response.status_code == 401


class TestGetAccount:
    """Tests for GET /api/accounts/{id} endpoint."""

    def test_returns_account(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_account_in_db: Account,
    ) -> None:
        """Should return account for authenticated user."""
        response = client.get(
            f"/api/accounts/{test_account_in_db.id}",
            headers=api_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_account_in_db.id)
        assert data["name"] == "Test Account"

    def test_returns_404_for_nonexistent(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_institution_in_db: Institution,
    ) -> None:
        """Should return 404 for nonexistent account."""
        response = client.get(
            f"/api/accounts/{uuid4()}",
            headers=api_auth_headers,
        )

        assert response.status_code == 404

    def test_returns_404_for_other_users_account(
        self,
        client: TestClient,
        api_db_session: Session,
        test_institution_in_db: Institution,
    ) -> None:
        """Should return 404 for account owned by another user."""
        # Create another user and their connection/account
        other_user = User(
            username="otheruser",
            password_hash=hash_password("password"),
            first_name="Other",
            last_name="User",
        )
        api_db_session.add(other_user)
        api_db_session.commit()

        other_conn = Connection(
            user_id=other_user.id,
            provider=Provider.GOCARDLESS.value,
            provider_id="other-req-id",
            institution_id=test_institution_in_db.id,
            friendly_name="Other Connection",
            status=ConnectionStatus.ACTIVE.value,
            created_at=datetime.now(),
        )
        api_db_session.add(other_conn)
        api_db_session.commit()

        other_acc = Account(
            connection_id=other_conn.id,
            provider_id="other-gc-acc-id",
            status=AccountStatus.ACTIVE.value,
            name="Other Account",
        )
        api_db_session.add(other_acc)
        api_db_session.commit()

        # Create requesting user
        requesting_user = User(
            username="requestuser",
            password_hash=hash_password("password"),
            first_name="Request",
            last_name="User",
        )
        api_db_session.add(requesting_user)
        api_db_session.commit()

        token = create_access_token(requesting_user.id)
        response = client.get(
            f"/api/accounts/{other_acc.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404


class TestUpdateAccount:
    """Tests for PATCH /api/accounts/{id} endpoint."""

    def test_updates_display_name(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_account_in_db: Account,
    ) -> None:
        """Should update account's display name."""
        response = client.patch(
            f"/api/accounts/{test_account_in_db.id}",
            headers=api_auth_headers,
            json={"display_name": "Updated Display Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Updated Display Name"

    def test_clears_display_name(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_account_in_db: Account,
    ) -> None:
        """Should clear display name when set to null."""
        response = client.patch(
            f"/api/accounts/{test_account_in_db.id}",
            headers=api_auth_headers,
            json={"display_name": None},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] is None

    def test_returns_404_for_nonexistent(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_institution_in_db: Institution,
    ) -> None:
        """Should return 404 for nonexistent account."""
        response = client.patch(
            f"/api/accounts/{uuid4()}",
            headers=api_auth_headers,
            json={"display_name": "New Name"},
        )

        assert response.status_code == 404


class TestNormalizeCreditCardBalance:
    """Tests for _normalize_credit_card_balance helper."""

    def test_amex_style_negative_balance(self) -> None:
        """Should return absolute value for negative balance (amount owed)."""
        result = _normalize_credit_card_balance(-500.0, 5000.0)
        assert result == 500.0

    def test_nationwide_style_positive_balance_with_limit(self) -> None:
        """Should convert available credit to amount owed."""
        # Balance is 1500 (available), limit is 2000 -> owed 500
        result = _normalize_credit_card_balance(1500.0, 2000.0)
        assert result == 500.0

    def test_no_credit_limit(self) -> None:
        """Should return absolute value when no credit limit set."""
        result = _normalize_credit_card_balance(-750.0, None)
        assert result == 750.0

    def test_no_credit_limit_positive_balance(self) -> None:
        """Should return absolute value for positive balance without credit limit."""
        result = _normalize_credit_card_balance(300.0, None)
        assert result == 300.0

    def test_zero_balance(self) -> None:
        """Should return zero when balance is zero."""
        result = _normalize_credit_card_balance(0.0, 5000.0)
        assert result == 0.0

    def test_overpayment_returns_zero(self) -> None:
        """Should return zero when available credit exceeds limit (overpayment)."""
        # Balance is 6000 (available), limit is 5000 -> owed max(0, -1000) = 0
        result = _normalize_credit_card_balance(6000.0, 5000.0)
        assert result == 0.0

    def test_full_limit_used(self) -> None:
        """Should return full credit limit when available credit is zero."""
        result = _normalize_credit_card_balance(0.0, 3000.0)
        assert result == 0.0

    def test_positive_balance_equals_limit(self) -> None:
        """Should return zero when available credit equals limit (nothing owed)."""
        result = _normalize_credit_card_balance(5000.0, 5000.0)
        assert result == 0.0


class TestCreditCardNegativeBalance:
    """Tests for credit card accounts returning negative balance in API responses."""

    @pytest.fixture
    def test_credit_card_account_in_db(
        self, api_db_session: Session, test_connection_in_db: Connection
    ) -> Account:
        """Create a credit card account with balance and credit limit."""
        account = Account(
            connection_id=test_connection_in_db.id,
            provider_id="test-cc-account",
            status=AccountStatus.ACTIVE.value,
            name="Test Credit Card",
            display_name="My Credit Card",
            currency="GBP",
            category=AccountCategory.CREDIT_CARD.value,
            credit_limit=Decimal("5000.00"),
            # Amex-style: negative balance = amount owed
            balance_amount=Decimal("-1500.00"),
            balance_currency="GBP",
            balance_type="interimAvailable",
            balance_updated_at=datetime.now(),
        )
        api_db_session.add(account)
        api_db_session.commit()
        return account

    def test_credit_card_returns_negative_balance(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_credit_card_account_in_db: Account,
    ) -> None:
        """Should return negative balance for credit card (liability)."""
        response = client.get("/api/accounts", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        acc = data["accounts"][0]
        assert acc["balance"]["amount"] == -1500.0
        assert acc["category"] == "credit_card"

    @pytest.fixture
    def test_nationwide_cc_in_db(
        self, api_db_session: Session, test_connection_in_db: Connection
    ) -> Account:
        """Create a Nationwide-style credit card (positive balance = available credit)."""
        account = Account(
            connection_id=test_connection_in_db.id,
            provider_id="test-nationwide-cc",
            status=AccountStatus.ACTIVE.value,
            name="Nationwide CC",
            display_name="Nationwide Credit Card",
            currency="GBP",
            category=AccountCategory.CREDIT_CARD.value,
            credit_limit=Decimal("2000.00"),
            # Nationwide-style: positive balance = available credit
            balance_amount=Decimal("1500.00"),
            balance_currency="GBP",
            balance_type="interimAvailable",
            balance_updated_at=datetime.now(),
        )
        api_db_session.add(account)
        api_db_session.commit()
        return account

    def test_nationwide_style_returns_negative_balance(
        self,
        client: TestClient,
        api_auth_headers: dict[str, str],
        test_nationwide_cc_in_db: Account,
    ) -> None:
        """Should return negative balance for Nationwide-style credit card."""
        response = client.get("/api/accounts", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        acc = data["accounts"][0]
        # Available: 1500, limit: 2000 -> owed: 500 -> negated: -500
        assert acc["balance"]["amount"] == -500.0
        assert acc["category"] == "credit_card"
