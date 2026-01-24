"""Tests for GoCardless transaction operations."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from src.postgres.gocardless.models import BankAccount, GoCardlessTransaction
from src.postgres.gocardless.operations.transactions import upsert_transactions


class TestUpsertTransactions:
    """Tests for upsert_transactions operation."""

    def test_creates_booked_transactions(
        self,
        db_session: Session,
        test_bank_account: BankAccount,
    ) -> None:
        """Should create booked transactions from API response."""
        transactions_response = {
            "transactions": {
                "booked": [
                    {
                        "transactionId": "txn-001",
                        "bookingDate": "2026-01-15",
                        "valueDate": "2026-01-15",
                        "transactionAmount": {"amount": "-50.00", "currency": "GBP"},
                        "creditorName": "Test Shop",
                        "remittanceInformationUnstructured": "Purchase at Test Shop",
                    },
                    {
                        "transactionId": "txn-002",
                        "bookingDate": "2026-01-16",
                        "valueDate": "2026-01-16",
                        "transactionAmount": {"amount": "1000.00", "currency": "GBP"},
                        "debtorName": "Employer Ltd",
                        "remittanceInformationUnstructured": "Salary Jan 2026",
                    },
                ],
                "pending": [],
            }
        }

        result = upsert_transactions(db_session, test_bank_account.id, transactions_response)
        db_session.commit()

        assert result == 2

        # Verify transactions were created
        txns = (
            db_session.query(GoCardlessTransaction)
            .filter(GoCardlessTransaction.account_id == test_bank_account.id)
            .all()
        )
        assert len(txns) == 2

        txn1 = next(t for t in txns if t.transaction_id == "txn-001")
        assert txn1.transaction_amount == Decimal("-50.00")
        assert txn1.currency == "GBP"
        assert txn1.creditor_name == "Test Shop"
        assert txn1.status == "booked"
        assert txn1.booking_date == date(2026, 1, 15)

        txn2 = next(t for t in txns if t.transaction_id == "txn-002")
        assert txn2.transaction_amount == Decimal("1000.00")
        assert txn2.debtor_name == "Employer Ltd"
        assert txn2.remittance_information == "Salary Jan 2026"

    def test_creates_pending_transactions(
        self,
        db_session: Session,
        test_bank_account: BankAccount,
    ) -> None:
        """Should create pending transactions from API response."""
        transactions_response = {
            "transactions": {
                "booked": [],
                "pending": [
                    {
                        "transactionId": "pending-001",
                        "transactionAmount": {"amount": "-25.00", "currency": "GBP"},
                        "creditorName": "Online Store",
                    },
                ],
            }
        }

        result = upsert_transactions(db_session, test_bank_account.id, transactions_response)
        db_session.commit()

        assert result == 1

        txn = (
            db_session.query(GoCardlessTransaction)
            .filter(GoCardlessTransaction.transaction_id == "pending-001")
            .first()
        )
        assert txn is not None
        assert txn.status == "pending"
        assert txn.transaction_amount == Decimal("-25.00")

    def test_updates_existing_transactions(
        self,
        db_session: Session,
        test_bank_account: BankAccount,
    ) -> None:
        """Should update existing transaction when same account_id + transaction_id exists."""
        # Create initial transaction
        initial_txn = GoCardlessTransaction(
            account_id=test_bank_account.id,
            transaction_id="txn-001",
            booking_date=date(2026, 1, 15),
            transaction_amount=Decimal("-50.00"),
            currency="GBP",
            creditor_name="Old Name",
            status="booked",
            extracted_at=datetime.now(),
        )
        db_session.add(initial_txn)
        db_session.commit()
        original_id = initial_txn.id

        # Upsert with updated details
        transactions_response = {
            "transactions": {
                "booked": [
                    {
                        "transactionId": "txn-001",
                        "bookingDate": "2026-01-15",
                        "transactionAmount": {"amount": "-50.00", "currency": "GBP"},
                        "creditorName": "Updated Name",
                        "remittanceInformationUnstructured": "Updated description",
                    },
                ],
                "pending": [],
            }
        }

        result = upsert_transactions(db_session, test_bank_account.id, transactions_response)
        db_session.commit()

        assert result == 1

        # Verify only one transaction exists
        txns = (
            db_session.query(GoCardlessTransaction)
            .filter(GoCardlessTransaction.account_id == test_bank_account.id)
            .all()
        )
        assert len(txns) == 1
        assert txns[0].id == original_id
        assert txns[0].creditor_name == "Updated Name"
        assert txns[0].remittance_information == "Updated description"

    def test_handles_empty_response(
        self,
        db_session: Session,
        test_bank_account: BankAccount,
    ) -> None:
        """Should handle empty transactions response gracefully."""
        result = upsert_transactions(
            db_session, test_bank_account.id, {"transactions": {"booked": [], "pending": []}}
        )
        assert result == 0

        result = upsert_transactions(db_session, test_bank_account.id, {"transactions": {}})
        assert result == 0

        result = upsert_transactions(db_session, test_bank_account.id, {})
        assert result == 0

    def test_skips_transaction_without_id(
        self,
        db_session: Session,
        test_bank_account: BankAccount,
    ) -> None:
        """Should skip transactions without transactionId or internalTransactionId."""
        transactions_response = {
            "transactions": {
                "booked": [
                    {
                        # No transactionId
                        "bookingDate": "2026-01-15",
                        "transactionAmount": {"amount": "-50.00", "currency": "GBP"},
                    },
                ],
                "pending": [],
            }
        }

        result = upsert_transactions(db_session, test_bank_account.id, transactions_response)
        db_session.commit()

        assert result == 0

    def test_uses_internal_transaction_id_as_fallback(
        self,
        db_session: Session,
        test_bank_account: BankAccount,
    ) -> None:
        """Should use internalTransactionId when transactionId is missing."""
        transactions_response = {
            "transactions": {
                "booked": [
                    {
                        "internalTransactionId": "internal-001",
                        "bookingDate": "2026-01-15",
                        "transactionAmount": {"amount": "-50.00", "currency": "GBP"},
                    },
                ],
                "pending": [],
            }
        }

        result = upsert_transactions(db_session, test_bank_account.id, transactions_response)
        db_session.commit()

        assert result == 1

        txn = (
            db_session.query(GoCardlessTransaction)
            .filter(GoCardlessTransaction.transaction_id == "internal-001")
            .first()
        )
        assert txn is not None
        assert txn.internal_transaction_id == "internal-001"

    def test_handles_remittance_array(
        self,
        db_session: Session,
        test_bank_account: BankAccount,
    ) -> None:
        """Should join remittanceInformationUnstructuredArray into single string."""
        transactions_response = {
            "transactions": {
                "booked": [
                    {
                        "transactionId": "txn-001",
                        "transactionAmount": {"amount": "-50.00", "currency": "GBP"},
                        "remittanceInformationUnstructuredArray": [
                            "Line 1",
                            "Line 2",
                            "Line 3",
                        ],
                    },
                ],
                "pending": [],
            }
        }

        result = upsert_transactions(db_session, test_bank_account.id, transactions_response)
        db_session.commit()

        assert result == 1

        txn = (
            db_session.query(GoCardlessTransaction)
            .filter(GoCardlessTransaction.transaction_id == "txn-001")
            .first()
        )
        assert txn is not None
        assert txn.remittance_information == "Line 1 Line 2 Line 3"

    def test_handles_list_remittance(
        self,
        db_session: Session,
        test_bank_account: BankAccount,
    ) -> None:
        """Should join list remittanceInformationUnstructured into single string."""
        transactions_response = {
            "transactions": {
                "booked": [
                    {
                        "transactionId": "txn-001",
                        "transactionAmount": {"amount": "-50.00", "currency": "GBP"},
                        "remittanceInformationUnstructured": ["Part A", "Part B"],
                    },
                ],
                "pending": [],
            }
        }

        result = upsert_transactions(db_session, test_bank_account.id, transactions_response)
        db_session.commit()

        assert result == 1

        txn = (
            db_session.query(GoCardlessTransaction)
            .filter(GoCardlessTransaction.transaction_id == "txn-001")
            .first()
        )
        assert txn is not None
        assert txn.remittance_information == "Part A Part B"
