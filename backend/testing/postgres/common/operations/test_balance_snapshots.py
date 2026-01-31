"""Tests for balance snapshot operations."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from src.postgres.common.models import Account, BalanceSnapshot
from src.postgres.common.operations.balance_snapshots import (
    count_snapshots_for_account,
    create_balance_snapshot,
    get_latest_snapshot_for_account,
    get_snapshots_for_account,
)


class TestCreateBalanceSnapshot:
    """Tests for create_balance_snapshot operation."""

    def test_creates_snapshot_with_required_fields(
        self, db_session: Session, test_account: Account
    ) -> None:
        """Should create snapshot with required fields only."""
        result = create_balance_snapshot(
            db_session,
            account_id=test_account.id,
            balance_amount=Decimal("1500.50"),
            balance_currency="GBP",
        )
        db_session.commit()

        assert result.id is not None
        assert result.account_id == test_account.id
        assert result.balance_amount == Decimal("1500.50")
        assert result.balance_currency == "GBP"
        assert result.balance_type is None
        assert result.total_value is None
        assert result.unrealised_pnl is None
        assert result.source_updated_at is None
        assert result.captured_at is not None

    def test_creates_snapshot_with_all_fields(
        self, db_session: Session, test_account: Account
    ) -> None:
        """Should create snapshot with all optional fields."""
        source_time = datetime.now(UTC) - timedelta(hours=1)
        result = create_balance_snapshot(
            db_session,
            account_id=test_account.id,
            balance_amount=Decimal("2500.00"),
            balance_currency="GBP",
            balance_type="interimAvailable",
            total_value=Decimal("10000.00"),
            unrealised_pnl=Decimal("500.00"),
            source_updated_at=source_time,
        )
        db_session.commit()

        assert result.balance_type == "interimAvailable"
        assert result.total_value == Decimal("10000.00")
        assert result.unrealised_pnl == Decimal("500.00")
        # Compare without timezone as SQLite doesn't preserve timezone info
        assert result.source_updated_at is not None
        assert result.source_updated_at.replace(tzinfo=None) == source_time.replace(tzinfo=None)

    def test_creates_multiple_snapshots_for_same_account(
        self, db_session: Session, test_account: Account
    ) -> None:
        """Should allow multiple snapshots for the same account."""
        snapshot1 = create_balance_snapshot(
            db_session,
            account_id=test_account.id,
            balance_amount=Decimal("1000.00"),
            balance_currency="GBP",
        )
        db_session.commit()

        snapshot2 = create_balance_snapshot(
            db_session,
            account_id=test_account.id,
            balance_amount=Decimal("1100.00"),
            balance_currency="GBP",
        )
        db_session.commit()

        assert snapshot1.id != snapshot2.id
        assert snapshot1.balance_amount == Decimal("1000.00")
        assert snapshot2.balance_amount == Decimal("1100.00")


class TestGetLatestSnapshotForAccount:
    """Tests for get_latest_snapshot_for_account operation."""

    def test_returns_latest_snapshot(self, db_session: Session, test_account: Account) -> None:
        """Should return the most recent snapshot."""
        # Create older snapshot
        create_balance_snapshot(
            db_session,
            account_id=test_account.id,
            balance_amount=Decimal("1000.00"),
            balance_currency="GBP",
        )
        db_session.commit()

        # Create newer snapshot
        newer = create_balance_snapshot(
            db_session,
            account_id=test_account.id,
            balance_amount=Decimal("1500.00"),
            balance_currency="GBP",
        )
        db_session.commit()

        result = get_latest_snapshot_for_account(db_session, test_account.id)

        assert result is not None
        assert result.id == newer.id
        assert result.balance_amount == Decimal("1500.00")

    def test_returns_none_when_no_snapshots(
        self, db_session: Session, test_account: Account
    ) -> None:
        """Should return None when account has no snapshots."""
        result = get_latest_snapshot_for_account(db_session, test_account.id)

        assert result is None

    def test_returns_none_for_nonexistent_account(self, db_session: Session) -> None:
        """Should return None for nonexistent account ID."""
        result = get_latest_snapshot_for_account(db_session, uuid4())

        assert result is None


class TestGetSnapshotsForAccount:
    """Tests for get_snapshots_for_account operation."""

    def test_returns_all_snapshots_ordered(
        self, db_session: Session, test_account: Account
    ) -> None:
        """Should return snapshots ordered by captured_at ascending."""
        snapshot1 = create_balance_snapshot(
            db_session,
            account_id=test_account.id,
            balance_amount=Decimal("1000.00"),
            balance_currency="GBP",
        )
        db_session.commit()

        snapshot2 = create_balance_snapshot(
            db_session,
            account_id=test_account.id,
            balance_amount=Decimal("1100.00"),
            balance_currency="GBP",
        )
        db_session.commit()

        result = get_snapshots_for_account(db_session, test_account.id)

        assert len(result) == 2
        assert result[0].id == snapshot1.id
        assert result[1].id == snapshot2.id

    def test_filters_by_start_date(self, db_session: Session, test_account: Account) -> None:
        """Should filter snapshots by start date."""
        # Create a snapshot with specific captured_at
        old_snapshot = BalanceSnapshot(
            account_id=test_account.id,
            balance_amount=Decimal("1000.00"),
            balance_currency="GBP",
            captured_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        db_session.add(old_snapshot)

        new_snapshot = BalanceSnapshot(
            account_id=test_account.id,
            balance_amount=Decimal("1500.00"),
            balance_currency="GBP",
            captured_at=datetime(2024, 6, 1, tzinfo=UTC),
        )
        db_session.add(new_snapshot)
        db_session.commit()

        # Filter to only include snapshots from 2024-05-01 onwards
        result = get_snapshots_for_account(
            db_session,
            test_account.id,
            start_date=datetime(2024, 5, 1, tzinfo=UTC),
        )

        assert len(result) == 1
        assert result[0].balance_amount == Decimal("1500.00")

    def test_filters_by_end_date(self, db_session: Session, test_account: Account) -> None:
        """Should filter snapshots by end date."""
        old_snapshot = BalanceSnapshot(
            account_id=test_account.id,
            balance_amount=Decimal("1000.00"),
            balance_currency="GBP",
            captured_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        db_session.add(old_snapshot)

        new_snapshot = BalanceSnapshot(
            account_id=test_account.id,
            balance_amount=Decimal("1500.00"),
            balance_currency="GBP",
            captured_at=datetime(2024, 6, 1, tzinfo=UTC),
        )
        db_session.add(new_snapshot)
        db_session.commit()

        # Filter to only include snapshots before 2024-03-01
        result = get_snapshots_for_account(
            db_session,
            test_account.id,
            end_date=datetime(2024, 3, 1, tzinfo=UTC),
        )

        assert len(result) == 1
        assert result[0].balance_amount == Decimal("1000.00")

    def test_respects_limit(self, db_session: Session, test_account: Account) -> None:
        """Should respect the limit parameter."""
        for i in range(5):
            create_balance_snapshot(
                db_session,
                account_id=test_account.id,
                balance_amount=Decimal(f"{1000 + i * 100}.00"),
                balance_currency="GBP",
            )
        db_session.commit()

        result = get_snapshots_for_account(db_session, test_account.id, limit=3)

        assert len(result) == 3

    def test_returns_empty_for_account_with_no_snapshots(
        self, db_session: Session, test_account: Account
    ) -> None:
        """Should return empty list when account has no snapshots."""
        result = get_snapshots_for_account(db_session, test_account.id)

        assert result == []


class TestCountSnapshotsForAccount:
    """Tests for count_snapshots_for_account operation."""

    def test_returns_correct_count(self, db_session: Session, test_account: Account) -> None:
        """Should return correct snapshot count."""
        for _ in range(3):
            create_balance_snapshot(
                db_session,
                account_id=test_account.id,
                balance_amount=Decimal("1000.00"),
                balance_currency="GBP",
            )
        db_session.commit()

        result = count_snapshots_for_account(db_session, test_account.id)

        assert result == 3

    def test_returns_zero_for_no_snapshots(
        self, db_session: Session, test_account: Account
    ) -> None:
        """Should return 0 when account has no snapshots."""
        result = count_snapshots_for_account(db_session, test_account.id)

        assert result == 0

    def test_returns_zero_for_nonexistent_account(self, db_session: Session) -> None:
        """Should return 0 for nonexistent account ID."""
        result = count_snapshots_for_account(db_session, uuid4())

        assert result == 0
