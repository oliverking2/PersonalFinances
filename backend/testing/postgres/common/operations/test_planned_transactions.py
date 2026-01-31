"""Tests for planned transaction database operations."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.enums import RecurringFrequency
from src.postgres.common.operations.planned_transactions import (
    _normalise_to_monthly,
    create_planned_transaction,
    delete_planned_transaction,
    get_planned_expense_total,
    get_planned_income_total,
    get_planned_transaction_by_id,
    get_planned_transactions_by_user_id,
    get_upcoming_planned_transactions,
    update_planned_transaction,
)


class TestPlannedTransactionCRUD:
    """Tests for basic planned transaction CRUD operations."""

    def test_create_income_transaction(self, db_session: Session, test_user: User) -> None:
        """Should create an income (positive amount) transaction."""
        txn = create_planned_transaction(
            db_session,
            user_id=test_user.id,
            name="Freelance Payment",
            amount=Decimal("1500.00"),
        )
        db_session.commit()

        assert txn.id is not None
        assert txn.user_id == test_user.id
        assert txn.name == "Freelance Payment"
        assert txn.amount == Decimal("1500.00")
        assert txn.currency == "GBP"
        assert txn.frequency is None  # One-time by default
        assert txn.enabled is True
        assert txn.is_income is True
        assert txn.is_expense is False

    def test_create_expense_transaction(self, db_session: Session, test_user: User) -> None:
        """Should create an expense (negative amount) transaction."""
        expected_date = datetime(2026, 6, 1, tzinfo=UTC)
        txn = create_planned_transaction(
            db_session,
            user_id=test_user.id,
            name="Annual Insurance",
            amount=Decimal("-600.00"),
            frequency=RecurringFrequency.ANNUAL,
            next_expected_date=expected_date,
        )
        db_session.commit()

        assert txn.amount == Decimal("-600.00")
        assert txn.frequency == RecurringFrequency.ANNUAL.value
        # Compare date components (SQLite strips timezone in tests)
        assert txn.next_expected_date is not None
        assert txn.next_expected_date.year == expected_date.year
        assert txn.next_expected_date.month == expected_date.month
        assert txn.next_expected_date.day == expected_date.day
        assert txn.is_income is False
        assert txn.is_expense is True

    def test_create_recurring_with_end_date(self, db_session: Session, test_user: User) -> None:
        """Should create a recurring transaction with an end date."""
        start = datetime(2026, 2, 1, tzinfo=UTC)
        end = datetime(2026, 8, 1, tzinfo=UTC)

        txn = create_planned_transaction(
            db_session,
            user_id=test_user.id,
            name="Temp Contract",
            amount=Decimal("2000.00"),
            frequency=RecurringFrequency.MONTHLY,
            next_expected_date=start,
            end_date=end,
            notes="6-month freelance contract",
        )
        db_session.commit()

        # Compare date components (SQLite strips timezone in tests)
        assert txn.next_expected_date is not None
        assert txn.next_expected_date.year == start.year
        assert txn.next_expected_date.month == start.month
        assert txn.end_date is not None
        assert txn.end_date.year == end.year
        assert txn.end_date.month == end.month
        assert txn.notes == "6-month freelance contract"

    def test_get_by_id(self, db_session: Session, test_user: User) -> None:
        """Should retrieve a planned transaction by ID."""
        txn = create_planned_transaction(
            db_session,
            user_id=test_user.id,
            name="Test",
            amount=Decimal("100.00"),
        )
        db_session.commit()

        result = get_planned_transaction_by_id(db_session, txn.id)
        assert result is not None
        assert result.id == txn.id

    def test_get_by_id_not_found(self, db_session: Session) -> None:
        """Should return None for non-existent transaction."""
        result = get_planned_transaction_by_id(db_session, uuid4())
        assert result is None


class TestPlannedTransactionList:
    """Tests for listing planned transactions."""

    def test_get_all_by_user(self, db_session: Session, test_user: User) -> None:
        """Should get all planned transactions for a user."""
        create_planned_transaction(db_session, test_user.id, "Income 1", Decimal("1000"))
        create_planned_transaction(db_session, test_user.id, "Expense 1", Decimal("-200"))
        db_session.commit()

        result = get_planned_transactions_by_user_id(db_session, test_user.id)
        assert len(result) == 2

    def test_filter_enabled_only(self, db_session: Session, test_user: User) -> None:
        """Should filter to only enabled transactions."""
        create_planned_transaction(db_session, test_user.id, "Active", Decimal("100"), enabled=True)
        create_planned_transaction(
            db_session, test_user.id, "Disabled", Decimal("200"), enabled=False
        )
        db_session.commit()

        result = get_planned_transactions_by_user_id(db_session, test_user.id, enabled_only=True)
        assert len(result) == 1
        assert result[0].name == "Active"

    def test_filter_by_direction_income(self, db_session: Session, test_user: User) -> None:
        """Should filter to income only (positive amounts)."""
        create_planned_transaction(db_session, test_user.id, "Income", Decimal("1000"))
        create_planned_transaction(db_session, test_user.id, "Expense", Decimal("-200"))
        db_session.commit()

        result = get_planned_transactions_by_user_id(db_session, test_user.id, direction="income")
        assert len(result) == 1
        assert result[0].name == "Income"

    def test_filter_by_direction_expense(self, db_session: Session, test_user: User) -> None:
        """Should filter to expenses only (negative amounts)."""
        create_planned_transaction(db_session, test_user.id, "Income", Decimal("1000"))
        create_planned_transaction(db_session, test_user.id, "Expense", Decimal("-200"))
        db_session.commit()

        result = get_planned_transactions_by_user_id(db_session, test_user.id, direction="expense")
        assert len(result) == 1
        assert result[0].name == "Expense"

    def test_order_by_next_expected_date(self, db_session: Session, test_user: User) -> None:
        """Should order by next_expected_date ascending."""
        create_planned_transaction(
            db_session,
            test_user.id,
            "Later",
            Decimal("100"),
            next_expected_date=datetime(2026, 6, 1, tzinfo=UTC),
        )
        create_planned_transaction(
            db_session,
            test_user.id,
            "Sooner",
            Decimal("100"),
            next_expected_date=datetime(2026, 2, 1, tzinfo=UTC),
        )
        db_session.commit()

        result = get_planned_transactions_by_user_id(db_session, test_user.id)
        assert result[0].name == "Sooner"
        assert result[1].name == "Later"


class TestUpcomingTransactions:
    """Tests for getting upcoming planned transactions."""

    def test_get_upcoming_within_range(self, db_session: Session, test_user: User) -> None:
        """Should return transactions within the date range."""
        from_date = datetime(2026, 2, 1, tzinfo=UTC)
        to_date = datetime(2026, 2, 28, tzinfo=UTC)

        # Within range
        create_planned_transaction(
            db_session,
            test_user.id,
            "In Range",
            Decimal("-100"),
            next_expected_date=datetime(2026, 2, 15, tzinfo=UTC),
        )
        # Before range
        create_planned_transaction(
            db_session,
            test_user.id,
            "Before",
            Decimal("-50"),
            next_expected_date=datetime(2026, 1, 15, tzinfo=UTC),
        )
        # After range
        create_planned_transaction(
            db_session,
            test_user.id,
            "After",
            Decimal("-75"),
            next_expected_date=datetime(2026, 3, 15, tzinfo=UTC),
        )
        db_session.commit()

        result = get_upcoming_planned_transactions(
            db_session, test_user.id, from_date=from_date, to_date=to_date
        )
        assert len(result) == 1
        assert result[0].name == "In Range"

    def test_excludes_disabled(self, db_session: Session, test_user: User) -> None:
        """Should exclude disabled transactions."""
        from_date = datetime(2026, 2, 1, tzinfo=UTC)
        to_date = datetime(2026, 2, 28, tzinfo=UTC)

        create_planned_transaction(
            db_session,
            test_user.id,
            "Disabled",
            Decimal("-100"),
            next_expected_date=datetime(2026, 2, 15, tzinfo=UTC),
            enabled=False,
        )
        db_session.commit()

        result = get_upcoming_planned_transactions(
            db_session, test_user.id, from_date=from_date, to_date=to_date
        )
        assert len(result) == 0

    def test_excludes_past_end_date(self, db_session: Session, test_user: User) -> None:
        """Should exclude transactions with end_date before from_date."""
        from_date = datetime(2026, 3, 1, tzinfo=UTC)
        to_date = datetime(2026, 3, 31, tzinfo=UTC)

        # End date is before from_date - should be excluded
        create_planned_transaction(
            db_session,
            test_user.id,
            "Ended",
            Decimal("-100"),
            next_expected_date=datetime(2026, 3, 15, tzinfo=UTC),
            end_date=datetime(2026, 2, 28, tzinfo=UTC),
        )
        # No end date - should be included
        create_planned_transaction(
            db_session,
            test_user.id,
            "Open",
            Decimal("-100"),
            next_expected_date=datetime(2026, 3, 15, tzinfo=UTC),
        )
        db_session.commit()

        result = get_upcoming_planned_transactions(
            db_session, test_user.id, from_date=from_date, to_date=to_date
        )
        assert len(result) == 1
        assert result[0].name == "Open"


class TestPlannedTransactionUpdate:
    """Tests for updating planned transactions."""

    def test_update_basic_fields(self, db_session: Session, test_user: User) -> None:
        """Should update name, amount, and currency."""
        txn = create_planned_transaction(db_session, test_user.id, "Original", Decimal("100"))
        db_session.commit()

        result = update_planned_transaction(
            db_session,
            txn.id,
            name="Updated",
            amount=Decimal("200"),
            currency="EUR",
        )
        db_session.commit()

        assert result is not None
        assert result.name == "Updated"
        assert result.amount == Decimal("200")
        assert result.currency == "EUR"

    def test_update_frequency(self, db_session: Session, test_user: User) -> None:
        """Should update frequency from one-time to recurring."""
        txn = create_planned_transaction(db_session, test_user.id, "Test", Decimal("100"))
        db_session.commit()

        assert txn.frequency is None  # One-time

        result = update_planned_transaction(
            db_session,
            txn.id,
            frequency=RecurringFrequency.MONTHLY,
        )
        db_session.commit()

        assert result is not None
        assert result.frequency == RecurringFrequency.MONTHLY.value

    def test_clear_frequency_to_one_time(self, db_session: Session, test_user: User) -> None:
        """Should clear frequency to make it one-time."""
        txn = create_planned_transaction(
            db_session,
            test_user.id,
            "Test",
            Decimal("100"),
            frequency=RecurringFrequency.MONTHLY,
        )
        db_session.commit()

        result = update_planned_transaction(db_session, txn.id, frequency=None)
        db_session.commit()

        assert result is not None
        assert result.frequency is None

    def test_update_enabled(self, db_session: Session, test_user: User) -> None:
        """Should update enabled state."""
        txn = create_planned_transaction(db_session, test_user.id, "Test", Decimal("100"))
        db_session.commit()

        result = update_planned_transaction(db_session, txn.id, enabled=False)
        db_session.commit()

        assert result is not None
        assert result.enabled is False

    def test_update_not_found(self, db_session: Session) -> None:
        """Should return None when updating non-existent transaction."""
        result = update_planned_transaction(db_session, uuid4(), name="Test")
        assert result is None


class TestPlannedTransactionDelete:
    """Tests for deleting planned transactions."""

    def test_delete_transaction(self, db_session: Session, test_user: User) -> None:
        """Should delete a planned transaction."""
        txn = create_planned_transaction(db_session, test_user.id, "Test", Decimal("100"))
        db_session.commit()

        result = delete_planned_transaction(db_session, txn.id)
        db_session.commit()

        assert result is True
        assert get_planned_transaction_by_id(db_session, txn.id) is None

    def test_delete_not_found(self, db_session: Session) -> None:
        """Should return False when deleting non-existent transaction."""
        result = delete_planned_transaction(db_session, uuid4())
        assert result is False


class TestPlannedTransactionTotals:
    """Tests for calculating monthly totals."""

    def test_income_total_monthly(self, db_session: Session, test_user: User) -> None:
        """Should calculate total monthly income."""
        create_planned_transaction(
            db_session,
            test_user.id,
            "Salary",
            Decimal("3000"),
            frequency=RecurringFrequency.MONTHLY,
        )
        create_planned_transaction(
            db_session,
            test_user.id,
            "Side gig",
            Decimal("500"),
            frequency=RecurringFrequency.MONTHLY,
        )
        db_session.commit()

        total = get_planned_income_total(db_session, test_user.id)
        assert total == Decimal("3500")

    def test_income_total_annual_normalised(self, db_session: Session, test_user: User) -> None:
        """Should normalise annual income to monthly."""
        create_planned_transaction(
            db_session,
            test_user.id,
            "Bonus",
            Decimal("12000"),
            frequency=RecurringFrequency.ANNUAL,
        )
        db_session.commit()

        total = get_planned_income_total(db_session, test_user.id)
        # 12000 * 0.083 = 996
        assert total == Decimal("996.000")

    def test_income_excludes_one_time(self, db_session: Session, test_user: User) -> None:
        """Should exclude one-time income from recurring total."""
        create_planned_transaction(
            db_session,
            test_user.id,
            "One-time gift",
            Decimal("500"),
            frequency=None,  # One-time
        )
        create_planned_transaction(
            db_session,
            test_user.id,
            "Monthly",
            Decimal("100"),
            frequency=RecurringFrequency.MONTHLY,
        )
        db_session.commit()

        total = get_planned_income_total(db_session, test_user.id)
        assert total == Decimal("100")

    def test_income_excludes_disabled(self, db_session: Session, test_user: User) -> None:
        """Should exclude disabled transactions."""
        create_planned_transaction(
            db_session,
            test_user.id,
            "Disabled",
            Decimal("1000"),
            frequency=RecurringFrequency.MONTHLY,
            enabled=False,
        )
        db_session.commit()

        total = get_planned_income_total(db_session, test_user.id)
        assert total == Decimal("0")

    def test_expense_total(self, db_session: Session, test_user: User) -> None:
        """Should calculate total monthly expenses (absolute value)."""
        create_planned_transaction(
            db_session,
            test_user.id,
            "Rent",
            Decimal("-1200"),
            frequency=RecurringFrequency.MONTHLY,
        )
        create_planned_transaction(
            db_session,
            test_user.id,
            "Insurance",
            Decimal("-600"),
            frequency=RecurringFrequency.ANNUAL,
        )
        db_session.commit()

        total = get_planned_expense_total(db_session, test_user.id)
        # 1200 + (600 * 0.083) = 1200 + 49.8 = 1249.80
        expected = Decimal("1200") + Decimal("600") * Decimal("0.083")
        assert total == expected


class TestNormaliseToMonthly:
    """Tests for the monthly normalisation helper."""

    def test_weekly(self) -> None:
        """Weekly amounts multiplied by 4.33."""
        result = _normalise_to_monthly(Decimal("100"), RecurringFrequency.WEEKLY)
        assert result == Decimal("433.00")

    def test_fortnightly(self) -> None:
        """Fortnightly amounts multiplied by 2.17."""
        result = _normalise_to_monthly(Decimal("100"), RecurringFrequency.FORTNIGHTLY)
        assert result == Decimal("217.00")

    def test_monthly(self) -> None:
        """Monthly amounts unchanged."""
        result = _normalise_to_monthly(Decimal("100"), RecurringFrequency.MONTHLY)
        assert result == Decimal("100")

    def test_quarterly(self) -> None:
        """Quarterly amounts divided by 3."""
        result = _normalise_to_monthly(Decimal("300"), RecurringFrequency.QUARTERLY)
        assert result == Decimal("99.00")

    def test_annual(self) -> None:
        """Annual amounts divided by 12."""
        result = _normalise_to_monthly(Decimal("1200"), RecurringFrequency.ANNUAL)
        assert result == Decimal("99.600")
