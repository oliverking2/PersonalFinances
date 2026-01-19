"""Tests for GoCardless API account module."""

from unittest.mock import MagicMock

import pytest

from src.providers.gocardless.api.account import (
    get_account_details_by_id,
    get_account_metadata_by_id,
    get_balance_data_by_id,
    get_transaction_data_by_id,
)


class TestGetAccountMetadataById:
    """Tests for get_account_metadata_by_id function."""

    def test_get_account_metadata_success(self, mock_gocardless_credentials: MagicMock) -> None:
        """Test successful account metadata retrieval."""
        mock_gocardless_credentials.make_get_request.return_value = {
            "id": "test-account-id",
            "status": "READY",
            "institution_id": "CHASE_CHASGB2L",
        }

        result = get_account_metadata_by_id(mock_gocardless_credentials, "test-account-id")

        assert result["id"] == "test-account-id"
        assert result["status"] == "READY"
        mock_gocardless_credentials.make_get_request.assert_called_once_with(
            "https://bankaccountdata.gocardless.com/api/v2/accounts/test-account-id"
        )

    def test_get_account_metadata_invalid_response(
        self, mock_gocardless_credentials: MagicMock
    ) -> None:
        """Test handling of invalid response format."""
        mock_gocardless_credentials.make_get_request.return_value = ["not", "a", "dict"]

        with pytest.raises(ValueError, match="not in expected format"):
            get_account_metadata_by_id(mock_gocardless_credentials, "test-account-id")


class TestGetTransactionDataById:
    """Tests for get_transaction_data_by_id function."""

    def test_get_transaction_data_success(self, mock_gocardless_credentials: MagicMock) -> None:
        """Test successful transaction data retrieval."""
        mock_gocardless_credentials.make_get_request.return_value = {
            "transactions": {
                "booked": [{"transactionId": "txn-001", "amount": "-50.00"}],
                "pending": [],
            }
        }

        result = get_transaction_data_by_id(
            mock_gocardless_credentials, "test-account-id", "2024-01-01", "2024-01-31"
        )

        assert "transactions" in result
        assert len(result["transactions"]["booked"]) == 1
        mock_gocardless_credentials.make_get_request.assert_called_once_with(
            "https://bankaccountdata.gocardless.com/api/v2/accounts/test-account-id/transactions",
            params={"date_from": "2024-01-01", "date_to": "2024-01-31"},
        )

    def test_get_transaction_data_invalid_response(
        self, mock_gocardless_credentials: MagicMock
    ) -> None:
        """Test handling of invalid response format."""
        mock_gocardless_credentials.make_get_request.return_value = []

        with pytest.raises(ValueError, match="not in expected format"):
            get_transaction_data_by_id(
                mock_gocardless_credentials, "test-account-id", "2024-01-01", "2024-01-31"
            )


class TestGetBalanceDataById:
    """Tests for get_balance_data_by_id function."""

    def test_get_balance_data_success(self, mock_gocardless_credentials: MagicMock) -> None:
        """Test successful balance data retrieval."""
        mock_gocardless_credentials.make_get_request.return_value = {
            "balances": [
                {
                    "balanceAmount": {"amount": "1000.00", "currency": "GBP"},
                    "balanceType": "interimAvailable",
                }
            ]
        }

        result = get_balance_data_by_id(mock_gocardless_credentials, "test-account-id")

        assert "balances" in result
        assert len(result["balances"]) == 1
        mock_gocardless_credentials.make_get_request.assert_called_once_with(
            "https://bankaccountdata.gocardless.com/api/v2/accounts/test-account-id/balances"
        )

    def test_get_balance_data_invalid_response(
        self, mock_gocardless_credentials: MagicMock
    ) -> None:
        """Test handling of invalid response format."""
        mock_gocardless_credentials.make_get_request.return_value = []

        with pytest.raises(ValueError, match="not in expected format"):
            get_balance_data_by_id(mock_gocardless_credentials, "test-account-id")


class TestGetAccountDetailsById:
    """Tests for get_account_details_by_id function."""

    def test_get_account_details_success(self, mock_gocardless_credentials: MagicMock) -> None:
        """Test successful account details retrieval."""
        mock_gocardless_credentials.make_get_request.return_value = {
            "account": {
                "iban": "GB00TEST00000000001234",
                "currency": "GBP",
                "name": "Test Account",
            }
        }

        result = get_account_details_by_id(mock_gocardless_credentials, "test-account-id")

        assert "account" in result
        assert result["account"]["iban"] == "GB00TEST00000000001234"
        mock_gocardless_credentials.make_get_request.assert_called_once_with(
            "https://bankaccountdata.gocardless.com/api/v2/accounts/test-account-id/details"
        )

    def test_get_account_details_invalid_response(
        self, mock_gocardless_credentials: MagicMock
    ) -> None:
        """Test handling of invalid response format."""
        mock_gocardless_credentials.make_get_request.return_value = []

        with pytest.raises(ValueError, match="not in expected format"):
            get_account_details_by_id(mock_gocardless_credentials, "test-account-id")
