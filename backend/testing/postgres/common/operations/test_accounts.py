"""Tests for account operations."""

from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from src.postgres.common.enums import AccountCategory, AccountStatus
from src.postgres.common.models import Account, Connection
from src.postgres.common.operations.accounts import (
    create_account,
    get_account_by_id,
    get_accounts_by_connection_id,
    update_account,
)


class TestGetAccountById:
    """Tests for get_account_by_id operation."""

    def test_returns_account_when_found(self, db_session: Session, test_account: Account) -> None:
        """Should return account when it exists."""
        result = get_account_by_id(db_session, test_account.id)

        assert result is not None
        assert result.id == test_account.id

    def test_returns_none_when_not_found(
        self, db_session: Session, test_connection: Connection
    ) -> None:
        """Should return None when account doesn't exist."""
        result = get_account_by_id(db_session, uuid4())

        assert result is None


class TestGetAccountsByConnectionId:
    """Tests for get_accounts_by_connection_id operation."""

    def test_returns_connection_accounts(
        self, db_session: Session, test_account: Account, test_connection: Connection
    ) -> None:
        """Should return all accounts for a connection."""
        result = get_accounts_by_connection_id(db_session, test_connection.id)

        assert len(result) >= 1
        assert any(acc.id == test_account.id for acc in result)

    def test_filters_by_status(
        self, db_session: Session, test_account: Account, test_connection: Connection
    ) -> None:
        """Should filter by status when specified."""
        result = get_accounts_by_connection_id(
            db_session, test_connection.id, status=AccountStatus.ACTIVE
        )

        assert all(acc.status == AccountStatus.ACTIVE.value for acc in result)

    def test_returns_empty_for_connection_with_no_accounts(
        self, db_session: Session, test_connection: Connection
    ) -> None:
        """Should return empty list for connection without accounts."""
        result = get_accounts_by_connection_id(db_session, uuid4())

        assert result == []


class TestCreateAccount:
    """Tests for create_account operation."""

    def test_creates_account(self, db_session: Session, test_connection: Connection) -> None:
        """Should create account with all fields."""
        result = create_account(
            db_session,
            connection_id=test_connection.id,
            provider_id="new-gc-account-id",
            status=AccountStatus.ACTIVE,
            display_name="New Display Name",
            name="New Account",
            iban="GB00NEW000000000001234",
            currency="GBP",
        )
        db_session.commit()

        assert result.id is not None
        assert result.connection_id == test_connection.id
        assert result.provider_id == "new-gc-account-id"
        assert result.status == AccountStatus.ACTIVE.value
        assert result.display_name == "New Display Name"
        assert result.name == "New Account"
        assert result.iban == "GB00NEW000000000001234"
        assert result.currency == "GBP"

    def test_creates_account_with_minimal_fields(
        self, db_session: Session, test_connection: Connection
    ) -> None:
        """Should create account with only required fields."""
        result = create_account(
            db_session,
            connection_id=test_connection.id,
            provider_id="minimal-account-id",
            status=AccountStatus.ACTIVE,
        )
        db_session.commit()

        assert result.id is not None
        assert result.display_name is None
        assert result.name is None


class TestUpdateAccount:
    """Tests for update_account operation."""

    def test_updates_display_name(self, db_session: Session, test_account: Account) -> None:
        """Should update the display name."""
        result = update_account(db_session, test_account.id, display_name="Updated Display Name")
        db_session.commit()

        assert result is not None
        assert result.display_name == "Updated Display Name"

    def test_clears_display_name(self, db_session: Session, test_account: Account) -> None:
        """Should clear display name when clear_display_name is True."""
        # First set a display name
        update_account(db_session, test_account.id, display_name="Some Name")
        db_session.commit()

        # Then clear it
        result = update_account(db_session, test_account.id, clear_display_name=True)
        db_session.commit()

        assert result is not None
        assert result.display_name is None

    def test_updates_category(self, db_session: Session, test_account: Account) -> None:
        """Should update the category."""
        result = update_account(db_session, test_account.id, category=AccountCategory.CREDIT_CARD)
        db_session.commit()

        assert result is not None
        assert result.category == AccountCategory.CREDIT_CARD.value

    def test_clears_category(self, db_session: Session, test_account: Account) -> None:
        """Should clear category when clear_category is True."""
        # First set a category
        update_account(db_session, test_account.id, category=AccountCategory.BANK_ACCOUNT)
        db_session.commit()

        # Then clear it
        result = update_account(db_session, test_account.id, clear_category=True)
        db_session.commit()

        assert result is not None
        assert result.category is None

    def test_updates_min_balance(self, db_session: Session, test_account: Account) -> None:
        """Should update the min_balance."""
        result = update_account(db_session, test_account.id, min_balance=Decimal("500.00"))
        db_session.commit()

        assert result is not None
        assert result.min_balance == Decimal("500.00")

    def test_clears_min_balance(self, db_session: Session, test_account: Account) -> None:
        """Should clear min_balance when clear_min_balance is True."""
        # First set a min_balance
        update_account(db_session, test_account.id, min_balance=Decimal("100.00"))
        db_session.commit()

        # Then clear it
        result = update_account(db_session, test_account.id, clear_min_balance=True)
        db_session.commit()

        assert result is not None
        assert result.min_balance is None

    def test_updates_multiple_fields(self, db_session: Session, test_account: Account) -> None:
        """Should update multiple fields at once."""
        result = update_account(
            db_session,
            test_account.id,
            display_name="Multi Update",
            category=AccountCategory.DEBIT_CARD,
            min_balance=Decimal("250.50"),
        )
        db_session.commit()

        assert result is not None
        assert result.display_name == "Multi Update"
        assert result.category == AccountCategory.DEBIT_CARD.value
        assert result.min_balance == Decimal("250.50")

    def test_returns_none_when_not_found(
        self, db_session: Session, test_connection: Connection
    ) -> None:
        """Should return None when account doesn't exist."""
        result = update_account(db_session, uuid4(), display_name="Name")

        assert result is None
