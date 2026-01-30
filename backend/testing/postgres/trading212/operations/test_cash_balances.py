"""Tests for Trading 212 cash balance operations."""

from decimal import Decimal

from sqlalchemy.orm import Session

from src.postgres.trading212.operations.api_keys import create_api_key
from src.postgres.trading212.operations.cash_balances import (
    get_cash_balance_history,
    get_latest_cash_balance,
    upsert_cash_balance,
)

# Import User type for type hints
if True:
    from src.postgres.auth.models import User


class TestUpsertCashBalance:
    """Tests for upsert_cash_balance operation."""

    def test_upsert_creates_balance(self, db_session: Session, test_user: "User") -> None:
        """Upserting a cash balance should create a new record."""
        api_key = create_api_key(
            db_session,
            user_id=test_user.id,
            api_key_encrypted="key",
            friendly_name="Test",
        )

        balance = upsert_cash_balance(
            db_session,
            api_key.id,
            free=Decimal("100.50"),
            blocked=Decimal("0.00"),
            invested=Decimal("500.00"),
            pie_cash=Decimal("50.00"),
            ppl=Decimal("25.00"),
            result=Decimal("10.00"),
            total=Decimal("675.50"),
        )

        assert balance.id is not None
        assert balance.api_key_id == api_key.id
        assert balance.free == Decimal("100.50")
        assert balance.invested == Decimal("500.00")
        assert balance.ppl == Decimal("25.00")
        assert balance.total == Decimal("675.50")

    def test_upsert_creates_multiple_snapshots(
        self, db_session: Session, test_user: "User"
    ) -> None:
        """Upserting multiple times should create separate snapshots."""
        api_key = create_api_key(
            db_session,
            user_id=test_user.id,
            api_key_encrypted="key",
            friendly_name="Test",
        )

        # Create first balance
        upsert_cash_balance(
            db_session,
            api_key.id,
            free=Decimal("100.00"),
            blocked=Decimal("0.00"),
            invested=Decimal("500.00"),
            pie_cash=Decimal("0.00"),
            ppl=Decimal("0.00"),
            result=Decimal("0.00"),
            total=Decimal("600.00"),
        )

        # Create second balance
        upsert_cash_balance(
            db_session,
            api_key.id,
            free=Decimal("200.00"),
            blocked=Decimal("0.00"),
            invested=Decimal("500.00"),
            pie_cash=Decimal("0.00"),
            ppl=Decimal("50.00"),
            result=Decimal("0.00"),
            total=Decimal("750.00"),
        )

        history = get_cash_balance_history(db_session, api_key.id)
        assert len(history) == 2


class TestGetLatestCashBalance:
    """Tests for get_latest_cash_balance operation."""

    def test_get_latest_returns_most_recent(self, db_session: Session, test_user: "User") -> None:
        """Getting latest balance should return most recent snapshot."""
        api_key = create_api_key(
            db_session,
            user_id=test_user.id,
            api_key_encrypted="key",
            friendly_name="Test",
        )

        # Create multiple balances
        upsert_cash_balance(
            db_session,
            api_key.id,
            free=Decimal("100.00"),
            blocked=Decimal("0.00"),
            invested=Decimal("0.00"),
            pie_cash=Decimal("0.00"),
            ppl=Decimal("0.00"),
            result=Decimal("0.00"),
            total=Decimal("100.00"),
        )
        upsert_cash_balance(
            db_session,
            api_key.id,
            free=Decimal("200.00"),
            blocked=Decimal("0.00"),
            invested=Decimal("0.00"),
            pie_cash=Decimal("0.00"),
            ppl=Decimal("0.00"),
            result=Decimal("0.00"),
            total=Decimal("200.00"),
        )

        latest = get_latest_cash_balance(db_session, api_key.id)

        assert latest is not None
        assert latest.total == Decimal("200.00")

    def test_get_latest_no_balances(self, db_session: Session, test_user: "User") -> None:
        """Getting latest when no balances exist should return None."""
        api_key = create_api_key(
            db_session,
            user_id=test_user.id,
            api_key_encrypted="key",
            friendly_name="Test",
        )

        latest = get_latest_cash_balance(db_session, api_key.id)

        assert latest is None


class TestGetCashBalanceHistory:
    """Tests for get_cash_balance_history operation."""

    def test_history_limited(self, db_session: Session, test_user: "User") -> None:
        """History should respect limit parameter."""
        api_key = create_api_key(
            db_session,
            user_id=test_user.id,
            api_key_encrypted="key",
            friendly_name="Test",
        )

        # Create 5 balances
        for i in range(5):
            upsert_cash_balance(
                db_session,
                api_key.id,
                free=Decimal(str(i * 100)),
                blocked=Decimal("0.00"),
                invested=Decimal("0.00"),
                pie_cash=Decimal("0.00"),
                ppl=Decimal("0.00"),
                result=Decimal("0.00"),
                total=Decimal(str(i * 100)),
            )

        history = get_cash_balance_history(db_session, api_key.id, limit=3)

        assert len(history) == 3
        # Should be in descending order by fetched_at
        assert history[0].total == Decimal("400.00")
