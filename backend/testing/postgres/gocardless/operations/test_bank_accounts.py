"""Tests for GoCardless bank account database operations."""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from src.postgres.gocardless.models import BankAccount, RequisitionLink
from src.postgres.gocardless.operations.bank_accounts import (
    get_active_accounts,
    get_transaction_watermark,
    update_transaction_watermark,
    upsert_bank_account_details,
    upsert_bank_accounts,
)


class TestUpsertBankAccounts:
    """Tests for upsert_bank_accounts function."""

    def test_upsert_bank_accounts_creates_new(
        self, db_session: Session, test_requisition_link: RequisitionLink
    ) -> None:
        """Test that new accounts are created."""
        accounts = [
            {
                "id": "new-account-1",
                "status": "READY",
                "currency": "GBP",
                "iban": "GB00TEST00000000001111",
            },
            {
                "id": "new-account-2",
                "status": "READY",
                "currency": "EUR",
                "iban": "GB00TEST00000000002222",
            },
        ]

        upsert_bank_accounts(db_session, test_requisition_link.id, accounts)

        # Verify accounts were created
        acc1 = db_session.get(BankAccount, "new-account-1")
        acc2 = db_session.get(BankAccount, "new-account-2")

        assert acc1 is not None
        assert acc1.currency == "GBP"
        assert acc1.requisition_id == test_requisition_link.id

        assert acc2 is not None
        assert acc2.currency == "EUR"

    def test_upsert_bank_accounts_updates_existing(
        self, db_session: Session, test_bank_account: BankAccount
    ) -> None:
        """Test that existing accounts are updated."""
        accounts = [
            {
                "id": test_bank_account.id,
                "status": "SUSPENDED",
                "currency": "USD",
                "iban": "GB00NEWIBAN00000000",
            }
        ]

        upsert_bank_accounts(db_session, test_bank_account.requisition_id, accounts)

        # Verify account was updated
        updated = db_session.get(BankAccount, test_bank_account.id)
        assert updated is not None
        assert updated.status == "SUSPENDED"
        assert updated.currency == "USD"
        assert updated.iban == "GB00NEWIBAN00000000"

    def test_upsert_bank_accounts_empty_list(
        self, db_session: Session, test_requisition_link: RequisitionLink
    ) -> None:
        """Test upserting empty list does nothing."""
        upsert_bank_accounts(db_session, test_requisition_link.id, [])

        # No error should be raised
        assert True


class TestGetActiveAccounts:
    """Tests for get_active_accounts function."""

    def test_get_active_accounts_returns_ready_accounts(
        self, db_session: Session, test_bank_account: BankAccount
    ) -> None:
        """Test that only READY accounts are returned."""
        result = get_active_accounts(db_session)

        assert len(result) == 1
        assert result[0].id == test_bank_account.id

    def test_get_active_accounts_excludes_non_ready(
        self, db_session: Session, test_requisition_link: RequisitionLink
    ) -> None:
        """Test that non-READY accounts are excluded."""
        # Create a suspended account
        suspended = BankAccount(
            id="suspended-account",
            requisition_id=test_requisition_link.id,
            status="SUSPENDED",
            currency="GBP",
        )
        db_session.add(suspended)
        db_session.commit()

        result = get_active_accounts(db_session)

        assert len(result) == 0

    def test_get_active_accounts_empty(self, db_session: Session) -> None:
        """Test get_active_accounts with no accounts."""
        result = get_active_accounts(db_session)

        assert result == []


class TestGetTransactionWatermark:
    """Tests for get_transaction_watermark function."""

    def test_get_transaction_watermark_returns_date(
        self, db_session: Session, test_bank_account: BankAccount
    ) -> None:
        """Test that watermark date is returned."""
        # Set a watermark
        test_bank_account.dg_transaction_extract_date = date(2024, 1, 15)
        db_session.commit()

        result = get_transaction_watermark(db_session, test_bank_account.id)

        assert result == date(2024, 1, 15)

    def test_get_transaction_watermark_returns_none(
        self, db_session: Session, test_bank_account: BankAccount
    ) -> None:
        """Test that None is returned when no watermark exists."""
        result = get_transaction_watermark(db_session, test_bank_account.id)

        assert result is None

    def test_get_transaction_watermark_not_found(self, db_session: Session) -> None:
        """Test that ValueError is raised for non-existent account."""
        with pytest.raises(ValueError, match="not found"):
            get_transaction_watermark(db_session, "non-existent-id")


class TestUpdateTransactionWatermark:
    """Tests for update_transaction_watermark function."""

    def test_update_transaction_watermark_success(
        self, db_session: Session, test_bank_account: BankAccount
    ) -> None:
        """Test successful watermark update."""
        new_date = date(2024, 2, 20)

        update_transaction_watermark(db_session, test_bank_account.id, new_date)

        updated = db_session.get(BankAccount, test_bank_account.id)
        assert updated is not None
        assert updated.dg_transaction_extract_date == new_date

    def test_update_transaction_watermark_not_found(self, db_session: Session) -> None:
        """Test that ValueError is raised for non-existent account."""
        with pytest.raises(ValueError, match="not found"):
            update_transaction_watermark(db_session, "non-existent-id", date(2024, 1, 1))


class TestUpsertBankAccountDetails:
    """Tests for upsert_bank_account_details function."""

    def test_updates_account_details(
        self, db_session: Session, test_bank_account: BankAccount
    ) -> None:
        """Test that account details are updated from API response."""
        details_response = {
            "account": {
                "currency": "USD",
                "name": "Updated Account Name",
                "product": "Current Account",
                "cashAccountType": "CACC",
                "ownerName": "John Doe",
            }
        }

        result = upsert_bank_account_details(db_session, test_bank_account.id, details_response)
        db_session.commit()

        assert result.id == test_bank_account.id
        assert result.currency == "USD"
        assert result.name == "Updated Account Name"
        assert result.product == "Current Account"
        assert result.cash_account_type == "CACC"
        assert result.owner_name == "John Doe"

    def test_handles_partial_details(
        self, db_session: Session, test_bank_account: BankAccount
    ) -> None:
        """Test that partial details update only specified fields."""
        original_currency = test_bank_account.currency
        details_response = {
            "account": {
                "name": "New Name Only",
            }
        }

        result = upsert_bank_account_details(db_session, test_bank_account.id, details_response)
        db_session.commit()

        assert result.name == "New Name Only"
        assert result.currency == original_currency  # Unchanged

    def test_raises_for_nonexistent_account(self, db_session: Session) -> None:
        """Test that ValueError is raised for non-existent account."""
        with pytest.raises(ValueError, match="not found"):
            upsert_bank_account_details(db_session, "nonexistent-id", {"account": {}})
