"""Tests for transaction database operations."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from src.postgres.common.models import Account, Transaction
from src.postgres.common.operations.transactions import (
    get_transactions_for_account,
    get_transactions_for_user,
)


class TestGetTransactionsForUser:
    """Tests for get_transactions_for_user function."""

    def test_returns_transactions_for_accounts(
        self, db_session: Session, test_account: Account
    ) -> None:
        """Should return transactions for the given account IDs."""
        txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-001",
            booking_date=datetime(2024, 1, 15, tzinfo=UTC),
            amount=Decimal("-50.00"),
            currency="GBP",
            description="Test transaction",
            synced_at=datetime.now(UTC),
        )
        db_session.add(txn)
        db_session.commit()

        result = get_transactions_for_user(db_session, [test_account.id])

        assert result.total == 1
        assert len(result.transactions) == 1
        assert result.transactions[0].id == txn.id

    def test_returns_empty_for_no_accounts(self, db_session: Session) -> None:
        """Should return empty result when no account IDs provided."""
        result = get_transactions_for_user(db_session, [])

        assert result.total == 0
        assert result.transactions == []

    def test_filters_by_start_date(self, db_session: Session, test_account: Account) -> None:
        """Should filter transactions by start date."""
        early_txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-early",
            booking_date=datetime(2024, 1, 1, tzinfo=UTC),
            amount=Decimal("-10.00"),
            currency="GBP",
            synced_at=datetime.now(UTC),
        )
        late_txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-late",
            booking_date=datetime(2024, 1, 15, tzinfo=UTC),
            amount=Decimal("-20.00"),
            currency="GBP",
            synced_at=datetime.now(UTC),
        )
        db_session.add_all([early_txn, late_txn])
        db_session.commit()

        result = get_transactions_for_user(
            db_session, [test_account.id], start_date=date(2024, 1, 10)
        )

        assert result.total == 1
        assert result.transactions[0].id == late_txn.id

    def test_filters_by_end_date(self, db_session: Session, test_account: Account) -> None:
        """Should filter transactions by end date."""
        early_txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-early",
            booking_date=datetime(2024, 1, 1, tzinfo=UTC),
            amount=Decimal("-10.00"),
            currency="GBP",
            synced_at=datetime.now(UTC),
        )
        late_txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-late",
            booking_date=datetime(2024, 1, 15, tzinfo=UTC),
            amount=Decimal("-20.00"),
            currency="GBP",
            synced_at=datetime.now(UTC),
        )
        db_session.add_all([early_txn, late_txn])
        db_session.commit()

        result = get_transactions_for_user(
            db_session, [test_account.id], end_date=date(2024, 1, 10)
        )

        assert result.total == 1
        assert result.transactions[0].id == early_txn.id

    def test_filters_by_min_amount(self, db_session: Session, test_account: Account) -> None:
        """Should filter transactions by minimum amount."""
        small_txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-small",
            booking_date=datetime(2024, 1, 1, tzinfo=UTC),
            amount=Decimal("-10.00"),
            currency="GBP",
            synced_at=datetime.now(UTC),
        )
        large_txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-large",
            booking_date=datetime(2024, 1, 15, tzinfo=UTC),
            amount=Decimal("1000.00"),
            currency="GBP",
            synced_at=datetime.now(UTC),
        )
        db_session.add_all([small_txn, large_txn])
        db_session.commit()

        result = get_transactions_for_user(db_session, [test_account.id], min_amount=Decimal("0"))

        assert result.total == 1
        assert result.transactions[0].id == large_txn.id

    def test_filters_by_max_amount(self, db_session: Session, test_account: Account) -> None:
        """Should filter transactions by maximum amount."""
        small_txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-small",
            booking_date=datetime(2024, 1, 1, tzinfo=UTC),
            amount=Decimal("-10.00"),
            currency="GBP",
            synced_at=datetime.now(UTC),
        )
        large_txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-large",
            booking_date=datetime(2024, 1, 15, tzinfo=UTC),
            amount=Decimal("1000.00"),
            currency="GBP",
            synced_at=datetime.now(UTC),
        )
        db_session.add_all([small_txn, large_txn])
        db_session.commit()

        result = get_transactions_for_user(db_session, [test_account.id], max_amount=Decimal("0"))

        assert result.total == 1
        assert result.transactions[0].id == small_txn.id

    def test_filters_by_search_description(
        self, db_session: Session, test_account: Account
    ) -> None:
        """Should filter transactions by search term in description."""
        grocery_txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-grocery",
            booking_date=datetime(2024, 1, 1, tzinfo=UTC),
            amount=Decimal("-50.00"),
            currency="GBP",
            description="Grocery shopping at Tesco",
            synced_at=datetime.now(UTC),
        )
        salary_txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-salary",
            booking_date=datetime(2024, 1, 15, tzinfo=UTC),
            amount=Decimal("3000.00"),
            currency="GBP",
            description="Monthly salary",
            synced_at=datetime.now(UTC),
        )
        db_session.add_all([grocery_txn, salary_txn])
        db_session.commit()

        result = get_transactions_for_user(db_session, [test_account.id], search="Tesco")

        assert result.total == 1
        assert result.transactions[0].id == grocery_txn.id

    def test_filters_by_search_counterparty(
        self, db_session: Session, test_account: Account
    ) -> None:
        """Should filter transactions by search term in counterparty name."""
        txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-001",
            booking_date=datetime(2024, 1, 1, tzinfo=UTC),
            amount=Decimal("-50.00"),
            currency="GBP",
            counterparty_name="Netflix",
            synced_at=datetime.now(UTC),
        )
        db_session.add(txn)
        db_session.commit()

        result = get_transactions_for_user(db_session, [test_account.id], search="Netflix")

        assert result.total == 1

    def test_search_is_case_insensitive(self, db_session: Session, test_account: Account) -> None:
        """Should search case-insensitively."""
        txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-001",
            booking_date=datetime(2024, 1, 1, tzinfo=UTC),
            amount=Decimal("-50.00"),
            currency="GBP",
            description="NETFLIX SUBSCRIPTION",
            synced_at=datetime.now(UTC),
        )
        db_session.add(txn)
        db_session.commit()

        result = get_transactions_for_user(db_session, [test_account.id], search="netflix")

        assert result.total == 1

    def test_paginates_results(self, db_session: Session, test_account: Account) -> None:
        """Should paginate results correctly."""
        for i in range(10):
            txn = Transaction(
                account_id=test_account.id,
                provider_id=f"txn-{i:03d}",
                booking_date=datetime(2024, 1, i + 1, tzinfo=UTC),
                amount=Decimal("-10.00"),
                currency="GBP",
                synced_at=datetime.now(UTC),
            )
            db_session.add(txn)
        db_session.commit()

        result = get_transactions_for_user(db_session, [test_account.id], page=1, page_size=3)

        assert result.total == 10
        assert len(result.transactions) == 3
        assert result.page == 1
        assert result.page_size == 3

    def test_orders_by_booking_date_descending(
        self, db_session: Session, test_account: Account
    ) -> None:
        """Should order transactions by booking date descending."""
        for i in range(3):
            txn = Transaction(
                account_id=test_account.id,
                provider_id=f"txn-{i:03d}",
                booking_date=datetime(2024, 1, i + 1, tzinfo=UTC),
                amount=Decimal("-10.00"),
                currency="GBP",
                synced_at=datetime.now(UTC),
            )
            db_session.add(txn)
        db_session.commit()

        result = get_transactions_for_user(db_session, [test_account.id])

        dates = [t.booking_date for t in result.transactions]
        assert dates == sorted(dates, reverse=True)


class TestGetTransactionsForAccount:
    """Tests for get_transactions_for_account function."""

    def test_returns_transactions_for_account(
        self, db_session: Session, test_account: Account
    ) -> None:
        """Should return transactions for a single account."""
        txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-001",
            booking_date=datetime(2024, 1, 15, tzinfo=UTC),
            amount=Decimal("-50.00"),
            currency="GBP",
            synced_at=datetime.now(UTC),
        )
        db_session.add(txn)
        db_session.commit()

        result = get_transactions_for_account(db_session, test_account.id)

        assert result.total == 1
        assert result.transactions[0].id == txn.id

    def test_returns_empty_for_nonexistent_account(self, db_session: Session) -> None:
        """Should return empty result for nonexistent account."""
        result = get_transactions_for_account(db_session, uuid4())

        assert result.total == 0
        assert result.transactions == []

    def test_respects_pagination(self, db_session: Session, test_account: Account) -> None:
        """Should respect pagination parameters."""
        for i in range(5):
            txn = Transaction(
                account_id=test_account.id,
                provider_id=f"txn-{i:03d}",
                booking_date=datetime(2024, 1, i + 1, tzinfo=UTC),
                amount=Decimal("-10.00"),
                currency="GBP",
                synced_at=datetime.now(UTC),
            )
            db_session.add(txn)
        db_session.commit()

        result = get_transactions_for_account(db_session, test_account.id, page=2, page_size=2)

        assert result.total == 5
        assert len(result.transactions) == 2
        assert result.page == 2
