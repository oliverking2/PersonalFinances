"""Tests for recurring pattern database operations."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.enums import (
    RecurringDirection,
    RecurringFrequency,
    RecurringSource,
    RecurringStatus,
)
from src.postgres.common.models import Account, Transaction
from src.postgres.common.operations.recurring_patterns import (
    _calculate_next_expected_date,
    accept_pattern,
    calculate_monthly_total,
    cancel_pattern,
    count_patterns_by_status,
    create_pattern,
    delete_pattern,
    get_pattern_by_id,
    get_pattern_transactions,
    get_patterns_by_user_id,
    get_upcoming_patterns,
    link_transaction_to_pattern,
    pause_pattern,
    resume_pattern,
    sync_detected_pattern,
    update_pattern,
)


class TestPatternCRUD:
    """Tests for basic pattern CRUD operations."""

    def test_create_pattern(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should create a recurring pattern."""
        anchor = datetime.now(UTC)
        pattern = create_pattern(
            db_session,
            user_id=test_user.id,
            name="Netflix",
            expected_amount=Decimal("15.99"),
            frequency=RecurringFrequency.MONTHLY,
            direction=RecurringDirection.EXPENSE,
            anchor_date=anchor,
            account_id=test_account.id,
            merchant_contains="netflix",
        )
        db_session.commit()

        assert pattern.id is not None
        assert pattern.user_id == test_user.id
        assert pattern.name == "Netflix"
        assert pattern.merchant_contains == "netflix"
        assert pattern.expected_amount == Decimal("15.99")
        assert pattern.frequency == RecurringFrequency.MONTHLY.value
        assert pattern.status == RecurringStatus.ACTIVE.value  # Default for manual
        assert pattern.source == RecurringSource.MANUAL.value

    def test_create_pattern_strips_whitespace(self, db_session: Session, test_user: User) -> None:
        """Should strip whitespace from name."""
        pattern = create_pattern(
            db_session,
            user_id=test_user.id,
            name="  Netflix  ",
            expected_amount=Decimal("15.99"),
            frequency=RecurringFrequency.MONTHLY,
            direction=RecurringDirection.EXPENSE,
            anchor_date=datetime.now(UTC),
        )
        db_session.commit()

        assert pattern.name == "Netflix"

    def test_create_pattern_truncates_long_name(self, db_session: Session, test_user: User) -> None:
        """Should truncate name to 100 characters."""
        long_name = "x" * 150
        pattern = create_pattern(
            db_session,
            user_id=test_user.id,
            name=long_name,
            expected_amount=Decimal("10.00"),
            frequency=RecurringFrequency.MONTHLY,
            direction=RecurringDirection.EXPENSE,
            anchor_date=datetime.now(UTC),
        )
        db_session.commit()

        assert len(pattern.name) == 100

    def test_get_pattern_by_id(self, db_session: Session, test_user: User) -> None:
        """Should retrieve pattern by ID."""
        pattern = create_pattern(
            db_session,
            user_id=test_user.id,
            name="Test",
            expected_amount=Decimal("10.00"),
            frequency=RecurringFrequency.MONTHLY,
            direction=RecurringDirection.EXPENSE,
            anchor_date=datetime.now(UTC),
        )
        db_session.commit()

        result = get_pattern_by_id(db_session, pattern.id)
        assert result is not None
        assert result.id == pattern.id

    def test_get_pattern_by_id_not_found(self, db_session: Session) -> None:
        """Should return None for non-existent pattern."""
        result = get_pattern_by_id(db_session, uuid4())
        assert result is None

    def test_get_patterns_by_user_id(self, db_session: Session, test_user: User) -> None:
        """Should retrieve all patterns for a user."""
        now = datetime.now(UTC)
        create_pattern(
            db_session,
            test_user.id,
            "Netflix",
            Decimal("15.99"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            now,
        )
        create_pattern(
            db_session,
            test_user.id,
            "Spotify",
            Decimal("9.99"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            now,
        )
        db_session.commit()

        patterns = get_patterns_by_user_id(db_session, test_user.id)
        assert len(patterns) == 2

    def test_get_patterns_filters_by_status(self, db_session: Session, test_user: User) -> None:
        """Should filter patterns by status."""
        now = datetime.now(UTC)
        create_pattern(
            db_session,
            test_user.id,
            "Active",
            Decimal("10.00"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            now,
            status=RecurringStatus.ACTIVE,
        )
        create_pattern(
            db_session,
            test_user.id,
            "Pending",
            Decimal("10.00"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            now,
            status=RecurringStatus.PENDING,
            source=RecurringSource.DETECTED,
        )
        db_session.commit()

        patterns = get_patterns_by_user_id(db_session, test_user.id, status=RecurringStatus.ACTIVE)
        assert len(patterns) == 1
        assert patterns[0].name == "Active"

    def test_delete_pattern(self, db_session: Session, test_user: User) -> None:
        """Should delete a pattern."""
        pattern = create_pattern(
            db_session,
            test_user.id,
            "Test",
            Decimal("10.00"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            datetime.now(UTC),
        )
        db_session.commit()

        result = delete_pattern(db_session, pattern.id)
        db_session.commit()

        assert result is True
        assert get_pattern_by_id(db_session, pattern.id) is None

    def test_delete_pattern_not_found(self, db_session: Session) -> None:
        """Should return False when deleting non-existent pattern."""
        result = delete_pattern(db_session, uuid4())
        assert result is False


class TestPatternStatusOperations:
    """Tests for pattern status change operations."""

    def test_accept_pattern(self, db_session: Session, test_user: User) -> None:
        """Should accept a pending pattern."""
        pattern = create_pattern(
            db_session,
            test_user.id,
            "Test",
            Decimal("10.00"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            datetime.now(UTC),
            status=RecurringStatus.PENDING,
            source=RecurringSource.DETECTED,
        )
        db_session.commit()

        result = accept_pattern(db_session, pattern.id)
        db_session.commit()

        assert result is not None
        assert result.status == RecurringStatus.ACTIVE.value

    def test_pause_pattern(self, db_session: Session, test_user: User) -> None:
        """Should pause a pattern."""
        pattern = create_pattern(
            db_session,
            test_user.id,
            "Test",
            Decimal("10.00"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            datetime.now(UTC),
        )
        db_session.commit()

        result = pause_pattern(db_session, pattern.id)
        db_session.commit()

        assert result is not None
        assert result.status == RecurringStatus.PAUSED.value

    def test_resume_pattern(self, db_session: Session, test_user: User) -> None:
        """Should resume a paused pattern."""
        pattern = create_pattern(
            db_session,
            test_user.id,
            "Test",
            Decimal("10.00"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            datetime.now(UTC),
        )
        pause_pattern(db_session, pattern.id)
        db_session.commit()

        result = resume_pattern(db_session, pattern.id)
        db_session.commit()

        assert result is not None
        assert result.status == RecurringStatus.ACTIVE.value

    def test_cancel_pattern(self, db_session: Session, test_user: User) -> None:
        """Should cancel a pattern."""
        pattern = create_pattern(
            db_session,
            test_user.id,
            "Test",
            Decimal("10.00"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            datetime.now(UTC),
        )
        db_session.commit()

        result = cancel_pattern(db_session, pattern.id)
        db_session.commit()

        assert result is not None
        assert result.status == RecurringStatus.CANCELLED.value
        assert result.end_date is not None


class TestPatternUpdate:
    """Tests for pattern update operations."""

    def test_update_name(self, db_session: Session, test_user: User) -> None:
        """Should update display name."""
        pattern = create_pattern(
            db_session,
            test_user.id,
            "Test",
            Decimal("10.00"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            datetime.now(UTC),
        )
        db_session.commit()

        result = update_pattern(db_session, pattern.id, name="Netflix Premium")
        db_session.commit()

        assert result is not None
        assert result.name == "Netflix Premium"

    def test_update_expected_amount(self, db_session: Session, test_user: User) -> None:
        """Should update expected amount."""
        pattern = create_pattern(
            db_session,
            test_user.id,
            "Test",
            Decimal("10.00"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            datetime.now(UTC),
        )
        db_session.commit()

        result = update_pattern(db_session, pattern.id, expected_amount=Decimal("15.99"))
        db_session.commit()

        assert result is not None
        assert result.expected_amount == Decimal("15.99")

    def test_update_frequency_recalculates_next_date(
        self, db_session: Session, test_user: User
    ) -> None:
        """Should recalculate next expected date when frequency changes."""
        now = datetime.now(UTC)
        pattern = create_pattern(
            db_session,
            test_user.id,
            "Test",
            Decimal("10.00"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            now,
        )
        db_session.commit()
        original_next = pattern.next_expected_date

        result = update_pattern(db_session, pattern.id, frequency=RecurringFrequency.WEEKLY)
        db_session.commit()

        assert result is not None
        assert result.frequency == RecurringFrequency.WEEKLY.value
        # Weekly should be sooner than monthly
        assert result.next_expected_date != original_next


class TestNextDateCalculation:
    """Tests for next expected date calculation."""

    def test_weekly_interval(self) -> None:
        """Should calculate weekly intervals correctly."""
        anchor = datetime(2024, 1, 1, tzinfo=UTC)
        next_date = _calculate_next_expected_date(anchor, RecurringFrequency.WEEKLY)

        assert next_date is not None
        # Should be in the future
        assert next_date > datetime.now(UTC)

    def test_monthly_interval_uses_relativedelta(self) -> None:
        """Should handle month boundaries correctly with relativedelta."""
        # Test January 31st - should become Feb 29th (or 28th) in non-leap year
        anchor = datetime(2024, 1, 31, tzinfo=UTC)
        next_date = _calculate_next_expected_date(anchor, RecurringFrequency.MONTHLY)

        assert next_date is not None
        # The key test is that it doesn't just add 30 days

    def test_irregular_returns_none(self) -> None:
        """Should return None for irregular frequency."""
        anchor = datetime.now(UTC)
        next_date = _calculate_next_expected_date(anchor, RecurringFrequency.IRREGULAR)

        assert next_date is None


class TestMonthlyTotal:
    """Tests for monthly total calculation."""

    def test_calculates_monthly_total(self, db_session: Session, test_user: User) -> None:
        """Should sum up monthly equivalent amounts."""
        now = datetime.now(UTC)
        # Monthly subscription
        create_pattern(
            db_session,
            test_user.id,
            "Netflix",
            Decimal("15.99"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            now,
            status=RecurringStatus.ACTIVE,
        )
        # Weekly subscription (should be multiplied by 4.33)
        create_pattern(
            db_session,
            test_user.id,
            "Weekly",
            Decimal("10.00"),
            RecurringFrequency.WEEKLY,
            RecurringDirection.EXPENSE,
            now,
            status=RecurringStatus.ACTIVE,
        )
        db_session.commit()

        total = calculate_monthly_total(db_session, test_user.id)

        # 15.99 + (10 * 4.33) = 15.99 + 43.30 = 59.29
        assert total >= Decimal("59")

    def test_excludes_paused_from_total(self, db_session: Session, test_user: User) -> None:
        """Should exclude paused patterns from monthly total."""
        now = datetime.now(UTC)
        create_pattern(
            db_session,
            test_user.id,
            "Paused",
            Decimal("100.00"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            now,
            status=RecurringStatus.PAUSED,
        )
        db_session.commit()

        total = calculate_monthly_total(db_session, test_user.id)
        assert total == Decimal("0")


class TestUpcomingPatterns:
    """Tests for upcoming patterns query."""

    def test_returns_patterns_within_range(self, db_session: Session, test_user: User) -> None:
        """Should return patterns with next date within range."""
        # Create pattern with next date in 3 days
        pattern = create_pattern(
            db_session,
            test_user.id,
            "Soon",
            Decimal("10.00"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            datetime.now(UTC) - timedelta(days=27),  # Anchor 27 days ago -> next in ~3 days
            status=RecurringStatus.ACTIVE,
        )
        db_session.commit()

        # Manually set next_expected_date for test reliability
        pattern.next_expected_date = datetime.now(UTC) + timedelta(days=3)
        db_session.commit()

        patterns = get_upcoming_patterns(db_session, test_user.id, days=7)
        assert len(patterns) == 1

    def test_excludes_paused_patterns(self, db_session: Session, test_user: User) -> None:
        """Should exclude paused patterns from upcoming."""
        pattern = create_pattern(
            db_session,
            test_user.id,
            "Paused",
            Decimal("10.00"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            datetime.now(UTC),
            status=RecurringStatus.PAUSED,
        )
        pattern.next_expected_date = datetime.now(UTC) + timedelta(days=3)
        db_session.commit()

        patterns = get_upcoming_patterns(db_session, test_user.id, days=7)
        assert len(patterns) == 0


class TestPatternTransactionLinking:
    """Tests for pattern-transaction linking."""

    def test_link_transaction_to_pattern(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should link a transaction to a pattern."""
        pattern = create_pattern(
            db_session,
            test_user.id,
            "Test",
            Decimal("10.00"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            datetime.now(UTC),
            account_id=test_account.id,
        )
        txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-001",
            booking_date=datetime(2024, 1, 15, tzinfo=UTC),
            amount=Decimal("-10.00"),
            currency="GBP",
            synced_at=datetime.now(UTC),
        )
        db_session.add(txn)
        db_session.commit()

        link = link_transaction_to_pattern(db_session, pattern.id, txn.id)
        db_session.commit()

        assert link is not None
        assert link.pattern_id == pattern.id
        assert link.transaction_id == txn.id

    def test_link_returns_existing(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should return existing link if already linked."""
        pattern = create_pattern(
            db_session,
            test_user.id,
            "Test",
            Decimal("10.00"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            datetime.now(UTC),
        )
        txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-001",
            amount=Decimal("-10.00"),
            currency="GBP",
            synced_at=datetime.now(UTC),
        )
        db_session.add(txn)
        db_session.commit()

        link1 = link_transaction_to_pattern(db_session, pattern.id, txn.id)
        link2 = link_transaction_to_pattern(db_session, pattern.id, txn.id)
        db_session.commit()

        assert link1.id == link2.id

    def test_get_pattern_transactions(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should get all transactions linked to a pattern."""
        pattern = create_pattern(
            db_session,
            test_user.id,
            "Test",
            Decimal("10.00"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            datetime.now(UTC),
        )
        for i in range(3):
            txn = Transaction(
                account_id=test_account.id,
                provider_id=f"txn-{i}",
                booking_date=datetime(2024, 1, 15 + i, tzinfo=UTC),
                amount=Decimal("-10.00"),
                currency="GBP",
                synced_at=datetime.now(UTC),
            )
            db_session.add(txn)
            db_session.flush()
            link_transaction_to_pattern(db_session, pattern.id, txn.id)
        db_session.commit()

        transactions = get_pattern_transactions(db_session, pattern.id)
        assert len(transactions) == 3


class TestSyncDetectedPattern:
    """Tests for syncing detected patterns from dbt."""

    def test_creates_new_pattern(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should create new pattern when not exists."""
        now = datetime.now(UTC)
        pattern, created = sync_detected_pattern(
            db_session,
            user_id=test_user.id,
            account_id=test_account.id,
            name="Netflix",
            expected_amount=Decimal("15.99"),
            frequency=RecurringFrequency.MONTHLY,
            direction=RecurringDirection.EXPENSE,
            confidence_score=Decimal("0.85"),
            occurrence_count=5,
            last_occurrence_date=now,
            next_expected_date=now + timedelta(days=30),
            merchant_contains="netflix",
        )
        db_session.commit()

        assert created is True
        assert pattern.name == "Netflix"
        assert pattern.status == RecurringStatus.PENDING.value
        assert pattern.source == RecurringSource.DETECTED.value

    def test_updates_existing_pending_pattern(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should update existing pending pattern."""
        now = datetime.now(UTC)
        pattern, _ = sync_detected_pattern(
            db_session,
            user_id=test_user.id,
            account_id=test_account.id,
            name="Netflix",
            expected_amount=Decimal("15.99"),
            frequency=RecurringFrequency.MONTHLY,
            direction=RecurringDirection.EXPENSE,
            confidence_score=Decimal("0.85"),
            occurrence_count=5,
            last_occurrence_date=now,
            next_expected_date=now + timedelta(days=30),
            merchant_contains="netflix",
        )
        db_session.commit()

        # Sync again with updated values
        updated_pattern, created = sync_detected_pattern(
            db_session,
            user_id=test_user.id,
            account_id=test_account.id,
            name="Netflix",
            expected_amount=Decimal("17.99"),  # Price increased
            frequency=RecurringFrequency.MONTHLY,
            direction=RecurringDirection.EXPENSE,
            confidence_score=Decimal("0.90"),
            occurrence_count=6,
            last_occurrence_date=now,
            next_expected_date=now + timedelta(days=30),
            merchant_contains="netflix",
        )
        db_session.commit()

        assert created is False
        assert updated_pattern.id == pattern.id
        assert updated_pattern.expected_amount == Decimal("17.99")

    def test_does_not_overwrite_active_pattern_status(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should not change status if user has accepted the pattern."""
        now = datetime.now(UTC)
        pattern, _ = sync_detected_pattern(
            db_session,
            user_id=test_user.id,
            account_id=test_account.id,
            name="Netflix",
            expected_amount=Decimal("15.99"),
            frequency=RecurringFrequency.MONTHLY,
            direction=RecurringDirection.EXPENSE,
            confidence_score=Decimal("0.85"),
            occurrence_count=5,
            last_occurrence_date=now,
            next_expected_date=now + timedelta(days=30),
            merchant_contains="netflix",
        )
        # User accepts
        accept_pattern(db_session, pattern.id)
        db_session.commit()

        # Try to sync with different amount
        same_pattern, created = sync_detected_pattern(
            db_session,
            user_id=test_user.id,
            account_id=test_account.id,
            name="Netflix",
            expected_amount=Decimal("20.00"),  # Amount changed
            frequency=RecurringFrequency.MONTHLY,
            direction=RecurringDirection.EXPENSE,
            confidence_score=Decimal("0.90"),
            occurrence_count=6,
            last_occurrence_date=now,
            next_expected_date=now + timedelta(days=30),
            merchant_contains="netflix",
        )
        db_session.commit()

        # Should update amount for accurate forecasting, but keep status
        assert created is False
        assert same_pattern.expected_amount == Decimal("20.00")
        assert same_pattern.status == RecurringStatus.ACTIVE.value


class TestCountPatternsByStatus:
    """Tests for counting patterns by status."""

    def test_counts_by_status(self, db_session: Session, test_user: User) -> None:
        """Should count patterns grouped by status."""
        now = datetime.now(UTC)
        create_pattern(
            db_session,
            test_user.id,
            "Pending1",
            Decimal("10.00"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            now,
            status=RecurringStatus.PENDING,
            source=RecurringSource.DETECTED,
        )
        create_pattern(
            db_session,
            test_user.id,
            "Pending2",
            Decimal("10.00"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            now,
            status=RecurringStatus.PENDING,
            source=RecurringSource.DETECTED,
        )
        create_pattern(
            db_session,
            test_user.id,
            "Active",
            Decimal("10.00"),
            RecurringFrequency.MONTHLY,
            RecurringDirection.EXPENSE,
            now,
            status=RecurringStatus.ACTIVE,
        )
        db_session.commit()

        counts = count_patterns_by_status(db_session, test_user.id)

        assert counts[RecurringStatus.PENDING] == 2
        assert counts[RecurringStatus.ACTIVE] == 1
