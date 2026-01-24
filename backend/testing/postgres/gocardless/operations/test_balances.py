"""Tests for GoCardless balance operations."""

from decimal import Decimal

from sqlalchemy.orm import Session

from src.postgres.gocardless.models import Balance, BankAccount
from src.postgres.gocardless.operations.balances import upsert_balances


class TestUpsertBalances:
    """Tests for upsert_balances operation."""

    def test_creates_new_balances(
        self,
        db_session: Session,
        test_bank_account: BankAccount,
    ) -> None:
        """Should create new balance records from API response."""
        balances_response = {
            "balances": [
                {
                    "balanceAmount": {"amount": "1500.50", "currency": "GBP"},
                    "balanceType": "interimAvailable",
                    "creditLimitIncluded": False,
                    "lastChangeDateTime": "2026-01-24T10:00:00Z",
                },
                {
                    "balanceAmount": {"amount": "1400.00", "currency": "GBP"},
                    "balanceType": "closingBooked",
                },
            ]
        }

        result = upsert_balances(db_session, test_bank_account.id, balances_response)
        db_session.commit()

        assert result == 2

        # Verify balances were created
        balances = (
            db_session.query(Balance).filter(Balance.account_id == test_bank_account.id).all()
        )
        assert len(balances) == 2

        interim = next(b for b in balances if b.balance_type == "interimAvailable")
        assert interim.balance_amount == Decimal("1500.50")
        assert interim.balance_currency == "GBP"
        assert interim.credit_limit_included is False

    def test_updates_existing_balances(
        self,
        db_session: Session,
        test_bank_account: BankAccount,
    ) -> None:
        """Should update existing balance when same type exists."""
        # Create initial balance
        initial_balance = Balance(
            account_id=test_bank_account.id,
            balance_amount=Decimal("1000.00"),
            balance_currency="GBP",
            balance_type="interimAvailable",
        )
        db_session.add(initial_balance)
        db_session.commit()

        # Upsert with new amount
        balances_response = {
            "balances": [
                {
                    "balanceAmount": {"amount": "1500.00", "currency": "GBP"},
                    "balanceType": "interimAvailable",
                },
            ]
        }

        result = upsert_balances(db_session, test_bank_account.id, balances_response)
        db_session.commit()

        assert result == 1

        # Verify balance was updated (not duplicated)
        balances = (
            db_session.query(Balance).filter(Balance.account_id == test_bank_account.id).all()
        )
        assert len(balances) == 1
        assert balances[0].balance_amount == Decimal("1500.00")

    def test_handles_empty_response(
        self,
        db_session: Session,
        test_bank_account: BankAccount,
    ) -> None:
        """Should handle empty balances response gracefully."""
        result = upsert_balances(db_session, test_bank_account.id, {"balances": []})
        assert result == 0

        result = upsert_balances(db_session, test_bank_account.id, {})
        assert result == 0

    def test_skips_balance_without_type(
        self,
        db_session: Session,
        test_bank_account: BankAccount,
    ) -> None:
        """Should skip balances without balanceType."""
        balances_response = {
            "balances": [
                {
                    "balanceAmount": {"amount": "1500.00", "currency": "GBP"},
                    # No balanceType
                },
            ]
        }

        result = upsert_balances(db_session, test_bank_account.id, balances_response)
        db_session.commit()

        assert result == 0
