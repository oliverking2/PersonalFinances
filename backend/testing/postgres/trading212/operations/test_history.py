"""Tests for Trading 212 history operations (orders, dividends, transactions)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.trading212.models import T212ApiKey
from src.postgres.trading212.operations.history import (
    get_dividends_for_api_key,
    get_orders_for_api_key,
    get_transactions_for_api_key,
    upsert_dividend,
    upsert_order,
    upsert_transaction,
)


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user."""
    user = User(
        id=uuid4(),
        username="testuser",
        password_hash="hashed",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_api_key(db_session: Session, test_user: User) -> T212ApiKey:
    """Create a test T212 API key."""
    api_key = T212ApiKey(
        id=uuid4(),
        user_id=test_user.id,
        api_key_encrypted="encrypted_key",
        friendly_name="Test Account",
        t212_account_id="T212_TEST_123",
        currency_code="GBP",
        status="active",
    )
    db_session.add(api_key)
    db_session.commit()
    return api_key


# =============================================================================
# Orders Tests
# =============================================================================


class TestUpsertOrder:
    """Tests for upsert_order function."""

    def test_creates_new_order(self, db_session: Session, test_api_key: T212ApiKey) -> None:
        """Should create a new order when none exists."""
        now = datetime.now(UTC)

        order = upsert_order(
            db_session,
            test_api_key.id,
            t212_order_id="ORDER_001",
            ticker="AAPL",
            order_type="MARKET",
            status="FILLED",
            currency="USD",
            date_created=now,
            instrument_name="Apple Inc.",
            quantity=Decimal("10"),
            filled_quantity=Decimal("10"),
            filled_value=Decimal("1500.00"),
            fill_price=Decimal("150.00"),
            date_executed=now,
        )
        db_session.commit()

        assert order.id is not None
        assert order.t212_order_id == "ORDER_001"
        assert order.ticker == "AAPL"
        assert order.order_type == "MARKET"
        assert order.status == "FILLED"
        assert order.currency == "USD"
        assert order.instrument_name == "Apple Inc."
        assert order.quantity == Decimal("10")
        assert order.filled_quantity == Decimal("10")
        assert order.fill_price == Decimal("150.00")

    def test_creates_order_with_minimal_fields(
        self, db_session: Session, test_api_key: T212ApiKey
    ) -> None:
        """Should create order with only required fields."""
        now = datetime.now(UTC)

        order = upsert_order(
            db_session,
            test_api_key.id,
            t212_order_id="ORDER_002",
            ticker="TSLA",
            order_type="LIMIT",
            status="PENDING",
            currency="USD",
            date_created=now,
        )
        db_session.commit()

        assert order.id is not None
        assert order.t212_order_id == "ORDER_002"
        assert order.instrument_name is None
        assert order.quantity is None
        assert order.limit_price is None

    def test_updates_existing_order(self, db_session: Session, test_api_key: T212ApiKey) -> None:
        """Should update an existing order when t212_order_id matches."""
        now = datetime.now(UTC)

        # Create initial order
        order = upsert_order(
            db_session,
            test_api_key.id,
            t212_order_id="ORDER_003",
            ticker="MSFT",
            order_type="MARKET",
            status="PENDING",
            currency="USD",
            date_created=now,
        )
        db_session.commit()
        original_id = order.id

        # Update the order
        updated_order = upsert_order(
            db_session,
            test_api_key.id,
            t212_order_id="ORDER_003",
            ticker="MSFT",
            order_type="MARKET",
            status="FILLED",
            currency="USD",
            date_created=now,
            filled_quantity=Decimal("5"),
            filled_value=Decimal("1500.00"),
            fill_price=Decimal("300.00"),
            date_executed=now,
        )
        db_session.commit()

        # Should be same record
        assert updated_order.id == original_id
        assert updated_order.status == "FILLED"
        assert updated_order.filled_quantity == Decimal("5")
        assert updated_order.fill_price == Decimal("300.00")

    def test_creates_order_with_stop_and_limit_prices(
        self, db_session: Session, test_api_key: T212ApiKey
    ) -> None:
        """Should store stop and limit prices for complex orders."""
        now = datetime.now(UTC)

        order = upsert_order(
            db_session,
            test_api_key.id,
            t212_order_id="ORDER_004",
            ticker="GOOGL",
            order_type="STOP_LIMIT",
            status="PENDING",
            currency="USD",
            date_created=now,
            limit_price=Decimal("140.00"),
            stop_price=Decimal("135.00"),
        )
        db_session.commit()

        assert order.limit_price == Decimal("140.00")
        assert order.stop_price == Decimal("135.00")


class TestGetOrdersForApiKey:
    """Tests for get_orders_for_api_key function."""

    def test_returns_orders_for_api_key(
        self, db_session: Session, test_api_key: T212ApiKey
    ) -> None:
        """Should return all orders for the given API key."""
        now = datetime.now(UTC)

        # Create multiple orders
        for i in range(3):
            upsert_order(
                db_session,
                test_api_key.id,
                t212_order_id=f"ORDER_{i}",
                ticker="AAPL",
                order_type="MARKET",
                status="FILLED",
                currency="USD",
                date_created=now - timedelta(days=i),
            )
        db_session.commit()

        orders = get_orders_for_api_key(db_session, test_api_key.id)

        assert len(orders) == 3
        # Should be ordered by date descending (most recent first)
        assert orders[0].t212_order_id == "ORDER_0"
        assert orders[2].t212_order_id == "ORDER_2"

    def test_filters_by_since_date(self, db_session: Session, test_api_key: T212ApiKey) -> None:
        """Should filter orders by since_date."""
        now = datetime.now(UTC)

        # Create orders at different times
        upsert_order(
            db_session,
            test_api_key.id,
            t212_order_id="OLD_ORDER",
            ticker="AAPL",
            order_type="MARKET",
            status="FILLED",
            currency="USD",
            date_created=now - timedelta(days=10),
        )
        upsert_order(
            db_session,
            test_api_key.id,
            t212_order_id="NEW_ORDER",
            ticker="AAPL",
            order_type="MARKET",
            status="FILLED",
            currency="USD",
            date_created=now - timedelta(days=1),
        )
        db_session.commit()

        # Filter for recent orders only
        orders = get_orders_for_api_key(
            db_session, test_api_key.id, since_date=now - timedelta(days=5)
        )

        assert len(orders) == 1
        assert orders[0].t212_order_id == "NEW_ORDER"

    def test_returns_empty_list_when_no_orders(
        self, db_session: Session, test_api_key: T212ApiKey
    ) -> None:
        """Should return empty list when no orders exist."""
        orders = get_orders_for_api_key(db_session, test_api_key.id)
        assert orders == []

    def test_does_not_return_other_api_key_orders(
        self, db_session: Session, test_api_key: T212ApiKey, test_user: User
    ) -> None:
        """Should only return orders for the specified API key."""
        now = datetime.now(UTC)

        # Create another API key
        other_api_key = T212ApiKey(
            id=uuid4(),
            user_id=test_user.id,
            api_key_encrypted="other_key",
            friendly_name="Other Account",
            t212_account_id="T212_OTHER",
            currency_code="GBP",
            status="active",
        )
        db_session.add(other_api_key)
        db_session.commit()

        # Create orders for both API keys
        upsert_order(
            db_session,
            test_api_key.id,
            t212_order_id="MY_ORDER",
            ticker="AAPL",
            order_type="MARKET",
            status="FILLED",
            currency="USD",
            date_created=now,
        )
        upsert_order(
            db_session,
            other_api_key.id,
            t212_order_id="OTHER_ORDER",
            ticker="TSLA",
            order_type="MARKET",
            status="FILLED",
            currency="USD",
            date_created=now,
        )
        db_session.commit()

        orders = get_orders_for_api_key(db_session, test_api_key.id)

        assert len(orders) == 1
        assert orders[0].t212_order_id == "MY_ORDER"


# =============================================================================
# Dividends Tests
# =============================================================================


class TestUpsertDividend:
    """Tests for upsert_dividend function."""

    def test_creates_new_dividend(self, db_session: Session, test_api_key: T212ApiKey) -> None:
        """Should create a new dividend when none exists."""
        paid_on = datetime.now(UTC)

        dividend = upsert_dividend(
            db_session,
            test_api_key.id,
            t212_reference="DIV_001",
            ticker="AAPL",
            amount=Decimal("25.50"),
            currency="USD",
            paid_on=paid_on,
            instrument_name="Apple Inc.",
            amount_in_euro=Decimal("23.00"),
            gross_amount_per_share=Decimal("0.25"),
            quantity=Decimal("100"),
            dividend_type="ORDINARY",
        )
        db_session.commit()

        assert dividend.id is not None
        assert dividend.t212_reference == "DIV_001"
        assert dividend.ticker == "AAPL"
        assert dividend.amount == Decimal("25.50")
        assert dividend.currency == "USD"
        assert dividend.instrument_name == "Apple Inc."
        assert dividend.amount_in_euro == Decimal("23.00")
        assert dividend.gross_amount_per_share == Decimal("0.25")
        assert dividend.quantity == Decimal("100")
        assert dividend.dividend_type == "ORDINARY"

    def test_creates_dividend_with_minimal_fields(
        self, db_session: Session, test_api_key: T212ApiKey
    ) -> None:
        """Should create dividend with only required fields."""
        paid_on = datetime.now(UTC)

        dividend = upsert_dividend(
            db_session,
            test_api_key.id,
            t212_reference="DIV_002",
            ticker="MSFT",
            amount=Decimal("10.00"),
            currency="USD",
            paid_on=paid_on,
        )
        db_session.commit()

        assert dividend.id is not None
        assert dividend.instrument_name is None
        assert dividend.amount_in_euro is None
        assert dividend.dividend_type is None

    def test_updates_existing_dividend(self, db_session: Session, test_api_key: T212ApiKey) -> None:
        """Should update an existing dividend when reference matches."""
        paid_on = datetime.now(UTC)

        # Create initial dividend
        dividend = upsert_dividend(
            db_session,
            test_api_key.id,
            t212_reference="DIV_003",
            ticker="NVDA",
            amount=Decimal("5.00"),
            currency="USD",
            paid_on=paid_on,
        )
        db_session.commit()
        original_id = dividend.id

        # Update the dividend
        updated_dividend = upsert_dividend(
            db_session,
            test_api_key.id,
            t212_reference="DIV_003",
            ticker="NVDA",
            amount=Decimal("5.50"),  # Updated amount
            currency="USD",
            paid_on=paid_on,
            dividend_type="SPECIAL",  # Add type
        )
        db_session.commit()

        # Should be same record
        assert updated_dividend.id == original_id
        assert updated_dividend.amount == Decimal("5.50")
        assert updated_dividend.dividend_type == "SPECIAL"


class TestGetDividendsForApiKey:
    """Tests for get_dividends_for_api_key function."""

    def test_returns_dividends_for_api_key(
        self, db_session: Session, test_api_key: T212ApiKey
    ) -> None:
        """Should return all dividends for the given API key."""
        now = datetime.now(UTC)

        # Create multiple dividends
        for i in range(3):
            upsert_dividend(
                db_session,
                test_api_key.id,
                t212_reference=f"DIV_{i}",
                ticker="AAPL",
                amount=Decimal("10.00"),
                currency="USD",
                paid_on=now - timedelta(days=i),
            )
        db_session.commit()

        dividends = get_dividends_for_api_key(db_session, test_api_key.id)

        assert len(dividends) == 3
        # Should be ordered by paid_on descending
        assert dividends[0].t212_reference == "DIV_0"
        assert dividends[2].t212_reference == "DIV_2"

    def test_filters_by_since_date(self, db_session: Session, test_api_key: T212ApiKey) -> None:
        """Should filter dividends by since_date."""
        now = datetime.now(UTC)

        # Create dividends at different times
        upsert_dividend(
            db_session,
            test_api_key.id,
            t212_reference="OLD_DIV",
            ticker="AAPL",
            amount=Decimal("10.00"),
            currency="USD",
            paid_on=now - timedelta(days=30),
        )
        upsert_dividend(
            db_session,
            test_api_key.id,
            t212_reference="NEW_DIV",
            ticker="AAPL",
            amount=Decimal("10.00"),
            currency="USD",
            paid_on=now - timedelta(days=1),
        )
        db_session.commit()

        dividends = get_dividends_for_api_key(
            db_session, test_api_key.id, since_date=now - timedelta(days=7)
        )

        assert len(dividends) == 1
        assert dividends[0].t212_reference == "NEW_DIV"

    def test_returns_empty_list_when_no_dividends(
        self, db_session: Session, test_api_key: T212ApiKey
    ) -> None:
        """Should return empty list when no dividends exist."""
        dividends = get_dividends_for_api_key(db_session, test_api_key.id)
        assert dividends == []


# =============================================================================
# Transactions Tests
# =============================================================================


class TestUpsertTransaction:
    """Tests for upsert_transaction function."""

    def test_creates_new_transaction(self, db_session: Session, test_api_key: T212ApiKey) -> None:
        """Should create a new transaction when none exists."""
        now = datetime.now(UTC)

        txn = upsert_transaction(
            db_session,
            test_api_key.id,
            t212_reference="TXN_001",
            transaction_type="DEPOSIT",
            amount=Decimal("1000.00"),
            currency="GBP",
            date_time=now,
        )
        db_session.commit()

        assert txn.id is not None
        assert txn.t212_reference == "TXN_001"
        assert txn.transaction_type == "DEPOSIT"
        assert txn.amount == Decimal("1000.00")
        assert txn.currency == "GBP"

    def test_updates_existing_transaction(
        self, db_session: Session, test_api_key: T212ApiKey
    ) -> None:
        """Should update an existing transaction when reference matches."""
        now = datetime.now(UTC)

        # Create initial transaction
        txn = upsert_transaction(
            db_session,
            test_api_key.id,
            t212_reference="TXN_002",
            transaction_type="WITHDRAWAL",
            amount=Decimal("500.00"),
            currency="GBP",
            date_time=now,
        )
        db_session.commit()
        original_id = txn.id

        # Update the transaction
        updated_txn = upsert_transaction(
            db_session,
            test_api_key.id,
            t212_reference="TXN_002",
            transaction_type="WITHDRAWAL",
            amount=Decimal("600.00"),  # Updated amount
            currency="GBP",
            date_time=now,
        )
        db_session.commit()

        # Should be same record
        assert updated_txn.id == original_id
        assert updated_txn.amount == Decimal("600.00")

    def test_creates_different_transaction_types(
        self, db_session: Session, test_api_key: T212ApiKey
    ) -> None:
        """Should handle various transaction types."""
        now = datetime.now(UTC)

        # Test various transaction types
        types = ["DEPOSIT", "WITHDRAWAL", "INTEREST", "FEE"]
        for i, txn_type in enumerate(types):
            txn = upsert_transaction(
                db_session,
                test_api_key.id,
                t212_reference=f"TXN_TYPE_{i}",
                transaction_type=txn_type,
                amount=Decimal("100.00"),
                currency="GBP",
                date_time=now,
            )
            assert txn.transaction_type == txn_type

        db_session.commit()


class TestGetTransactionsForApiKey:
    """Tests for get_transactions_for_api_key function."""

    def test_returns_transactions_for_api_key(
        self, db_session: Session, test_api_key: T212ApiKey
    ) -> None:
        """Should return all transactions for the given API key."""
        now = datetime.now(UTC)

        # Create multiple transactions
        for i in range(3):
            upsert_transaction(
                db_session,
                test_api_key.id,
                t212_reference=f"TXN_{i}",
                transaction_type="DEPOSIT",
                amount=Decimal("100.00"),
                currency="GBP",
                date_time=now - timedelta(days=i),
            )
        db_session.commit()

        transactions = get_transactions_for_api_key(db_session, test_api_key.id)

        assert len(transactions) == 3
        # Should be ordered by date_time descending
        assert transactions[0].t212_reference == "TXN_0"
        assert transactions[2].t212_reference == "TXN_2"

    def test_filters_by_since_date(self, db_session: Session, test_api_key: T212ApiKey) -> None:
        """Should filter transactions by since_date."""
        now = datetime.now(UTC)

        # Create transactions at different times
        upsert_transaction(
            db_session,
            test_api_key.id,
            t212_reference="OLD_TXN",
            transaction_type="DEPOSIT",
            amount=Decimal("100.00"),
            currency="GBP",
            date_time=now - timedelta(days=30),
        )
        upsert_transaction(
            db_session,
            test_api_key.id,
            t212_reference="NEW_TXN",
            transaction_type="WITHDRAWAL",
            amount=Decimal("50.00"),
            currency="GBP",
            date_time=now - timedelta(days=1),
        )
        db_session.commit()

        transactions = get_transactions_for_api_key(
            db_session, test_api_key.id, since_date=now - timedelta(days=7)
        )

        assert len(transactions) == 1
        assert transactions[0].t212_reference == "NEW_TXN"

    def test_returns_empty_list_when_no_transactions(
        self, db_session: Session, test_api_key: T212ApiKey
    ) -> None:
        """Should return empty list when no transactions exist."""
        transactions = get_transactions_for_api_key(db_session, test_api_key.id)
        assert transactions == []
