"""Tests for Trading 212 API client."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.providers.trading212.api.core import (
    AccountInfo,
    CashBalance,
    Trading212Client,
)
from src.providers.trading212.exceptions import (
    Trading212AuthError,
    Trading212Error,
    Trading212RateLimitError,
)


class TestTrading212Client:
    """Tests for Trading212Client."""

    def test_client_initialisation(self) -> None:
        """Client should initialise with API key."""
        client = Trading212Client("test-api-key")

        assert client._api_key == "test-api-key"

    @patch("src.providers.trading212.api.core.requests.Session.get")
    def test_get_cash_success(self, mock_get: MagicMock) -> None:
        """Get cash should return CashBalance dataclass."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "free": 100.50,
            "blocked": 0.00,
            "invested": 500.00,
            "pieCash": 50.00,
            "ppl": 25.00,
            "result": 10.00,
            "total": 675.50,
        }
        mock_get.return_value = mock_response

        client = Trading212Client("test-key")
        result = client.get_cash()

        assert isinstance(result, CashBalance)
        assert result.free == Decimal("100.50")
        assert result.invested == Decimal("500.00")
        assert result.ppl == Decimal("25.00")
        assert result.total == Decimal("675.50")

    @patch("src.providers.trading212.api.core.requests.Session.get")
    def test_get_account_info_success(self, mock_get: MagicMock) -> None:
        """Get account info should return AccountInfo dataclass."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "currencyCode": "GBP",
            "id": 12345,
        }
        mock_get.return_value = mock_response

        client = Trading212Client("test-key")
        result = client.get_account_info()

        assert isinstance(result, AccountInfo)
        assert result.currency_code == "GBP"
        assert result.account_id == "12345"

    @patch("src.providers.trading212.api.core.requests.Session.get")
    def test_auth_error(self, mock_get: MagicMock) -> None:
        """401 response should raise Trading212AuthError."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response

        client = Trading212Client("invalid-key")

        with pytest.raises(Trading212AuthError, match="authentication failed"):
            client.get_cash()

    @patch("src.providers.trading212.api.core.requests.Session.get")
    def test_rate_limit_error(self, mock_get: MagicMock) -> None:
        """429 response should raise Trading212RateLimitError."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 429
        mock_response.text = "Too Many Requests"
        mock_get.return_value = mock_response

        client = Trading212Client("test-key")

        with pytest.raises(Trading212RateLimitError, match="Rate limited"):
            client.get_cash()

    @patch("src.providers.trading212.api.core.requests.Session.get")
    def test_generic_error(self, mock_get: MagicMock) -> None:
        """Other error responses should raise Trading212Error."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        client = Trading212Client("test-key")

        with pytest.raises(Trading212Error, match="API error"):
            client.get_cash()

    @patch("src.providers.trading212.api.core.requests.Session.get")
    def test_validate_api_key_calls_account_info(self, mock_get: MagicMock) -> None:
        """Validate API key should call get_account_info."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "currencyCode": "GBP",
            "id": 12345,
        }
        mock_get.return_value = mock_response

        client = Trading212Client("test-key")
        result = client.validate_api_key()

        assert result.currency_code == "GBP"
        mock_get.assert_called_once()


class TestCashBalanceDataclass:
    """Tests for CashBalance dataclass."""

    def test_cash_balance_fields(self) -> None:
        """CashBalance should have all expected fields."""
        balance = CashBalance(
            free=Decimal("100.00"),
            blocked=Decimal("10.00"),
            invested=Decimal("500.00"),
            pie_cash=Decimal("50.00"),
            ppl=Decimal("25.00"),
            result=Decimal("10.00"),
            total=Decimal("695.00"),
        )

        assert balance.free == Decimal("100.00")
        assert balance.blocked == Decimal("10.00")
        assert balance.invested == Decimal("500.00")
        assert balance.pie_cash == Decimal("50.00")
        assert balance.ppl == Decimal("25.00")
        assert balance.result == Decimal("10.00")
        assert balance.total == Decimal("695.00")


class TestAccountInfoDataclass:
    """Tests for AccountInfo dataclass."""

    def test_account_info_fields(self) -> None:
        """AccountInfo should have all expected fields."""
        info = AccountInfo(
            currency_code="GBP",
            account_id="12345",
        )

        assert info.currency_code == "GBP"
        assert info.account_id == "12345"
