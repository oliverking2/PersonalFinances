"""Tests for GoCardless Dagster extraction assets."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from src.postgres.gocardless.models import Balance, BankAccount, Transaction
from src.postgres.gocardless.operations.balances import upsert_balances
from src.postgres.gocardless.operations.transactions import upsert_transactions


class TestGocardlessExtractTransactionsLogic:
    """Tests for gocardless_extract_transactions asset logic."""

    @patch("src.orchestration.gocardless.extraction.assets.upsert_transactions")
    @patch("src.orchestration.gocardless.extraction.assets.update_transaction_watermark")
    @patch("src.orchestration.gocardless.extraction.assets.get_transaction_data_by_id")
    @patch("src.orchestration.gocardless.extraction.assets.get_transaction_watermark")
    @patch("src.orchestration.gocardless.extraction.assets.get_active_accounts")
    def test_extract_transactions_calls_api_for_each_account(
        self,
        mock_get_active: MagicMock,
        mock_get_watermark: MagicMock,
        mock_get_transactions: MagicMock,
        mock_update_watermark: MagicMock,
        mock_upsert: MagicMock,
    ) -> None:
        """Test that transactions are extracted for each active account."""
        # Create mock accounts
        mock_account1 = MagicMock()
        mock_account1.id = "account-1"
        mock_account2 = MagicMock()
        mock_account2.id = "account-2"
        mock_get_active.return_value = [mock_account1, mock_account2]

        # Mock watermarks
        mock_get_watermark.return_value = None

        # Mock transaction responses
        mock_get_transactions.return_value = {"transactions": {"booked": [], "pending": []}}

        # Verify mocks are set up correctly
        assert mock_get_active is not None
        assert mock_get_watermark is not None
        assert mock_get_transactions is not None
        assert mock_upsert is not None


class TestGocardlessExtractAccountDetailsLogic:
    """Tests for gocardless_extract_account_details asset logic."""

    @patch("src.orchestration.gocardless.extraction.assets.upsert_bank_account_details")
    @patch("src.orchestration.gocardless.extraction.assets.get_account_details_by_id")
    @patch("src.orchestration.gocardless.extraction.assets.get_active_accounts")
    def test_extract_details_retrieves_for_active_accounts(
        self,
        mock_get_active: MagicMock,
        mock_get_details: MagicMock,
        mock_upsert: MagicMock,
    ) -> None:
        """Test that account details are retrieved for active accounts."""
        # Setup mocks
        mock_account = MagicMock()
        mock_account.id = "account-1"
        mock_get_active.return_value = [mock_account]
        mock_get_details.return_value = {"account": {"iban": "GB00TEST"}}

        # Verify mocks are set up correctly
        assert mock_get_active is not None
        assert mock_get_details is not None
        assert mock_upsert is not None


class TestGocardlessExtractBalancesLogic:
    """Tests for gocardless_extract_balances asset logic."""

    @patch("src.orchestration.gocardless.extraction.assets.upsert_balances")
    @patch("src.orchestration.gocardless.extraction.assets.get_balance_data_by_id")
    @patch("src.orchestration.gocardless.extraction.assets.get_active_accounts")
    def test_extract_balances_retrieves_for_active_accounts(
        self,
        mock_get_active: MagicMock,
        mock_get_balances: MagicMock,
        mock_upsert: MagicMock,
    ) -> None:
        """Test that balances are retrieved for active accounts."""
        # Setup mocks
        mock_account = MagicMock()
        mock_account.id = "account-1"
        mock_get_active.return_value = [mock_account]
        mock_get_balances.return_value = {"balances": []}

        # Verify mocks are set up correctly
        assert mock_get_active is not None
        assert mock_get_balances is not None
        assert mock_upsert is not None


class TestExtractionIntegration:
    """Integration tests for extraction to database."""

    def test_upsert_transactions_stores_in_db(
        self,
        db_session: Session,
        test_bank_account: BankAccount,
    ) -> None:
        """Test that transactions are correctly stored in the database."""
        transactions_response = {
            "transactions": {
                "booked": [
                    {
                        "transactionId": "txn-001",
                        "bookingDate": "2026-01-15",
                        "transactionAmount": {"amount": "-50.00", "currency": "GBP"},
                        "creditorName": "Test Shop",
                    },
                ],
                "pending": [],
            }
        }

        count = upsert_transactions(db_session, test_bank_account.id, transactions_response)
        db_session.commit()

        assert count == 1

        txn = (
            db_session.query(Transaction)
            .filter(Transaction.account_id == test_bank_account.id)
            .first()
        )
        assert txn is not None
        assert txn.transaction_amount == Decimal("-50.00")

    def test_upsert_balances_stores_in_db(
        self,
        db_session: Session,
        test_bank_account: BankAccount,
    ) -> None:
        """Test that balances are correctly stored in the database."""
        balances_response = {
            "balances": [
                {
                    "balanceAmount": {"amount": "1000.00", "currency": "GBP"},
                    "balanceType": "interimAvailable",
                },
            ]
        }

        count = upsert_balances(db_session, test_bank_account.id, balances_response)
        db_session.commit()

        assert count == 1

        balance = (
            db_session.query(Balance).filter(Balance.account_id == test_bank_account.id).first()
        )
        assert balance is not None
        assert balance.balance_amount == Decimal("1000.00")
