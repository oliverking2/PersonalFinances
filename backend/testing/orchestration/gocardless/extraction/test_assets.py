"""Tests for GoCardless Dagster extraction assets.

These tests focus on the underlying database operations since
Dagster assets are tested via their integration with the orchestration layer.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from src.postgres.gocardless.models import Balance, BankAccount, GoCardlessTransaction
from src.postgres.gocardless.operations.balances import upsert_balances
from src.postgres.gocardless.operations.transactions import upsert_transactions


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
            db_session.query(GoCardlessTransaction)
            .filter(GoCardlessTransaction.account_id == test_bank_account.id)
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

    def test_upsert_transactions_handles_empty_response(
        self,
        db_session: Session,
        test_bank_account: BankAccount,
    ) -> None:
        """Test that empty transaction responses are handled correctly."""
        transactions_response = {
            "transactions": {
                "booked": [],
                "pending": [],
            }
        }

        count = upsert_transactions(db_session, test_bank_account.id, transactions_response)
        db_session.commit()

        assert count == 0

    def test_upsert_balances_handles_empty_response(
        self,
        db_session: Session,
        test_bank_account: BankAccount,
    ) -> None:
        """Test that empty balance responses are handled correctly."""
        balances_response = {"balances": []}

        count = upsert_balances(db_session, test_bank_account.id, balances_response)
        db_session.commit()

        assert count == 0
