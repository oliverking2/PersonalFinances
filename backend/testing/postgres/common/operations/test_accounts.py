"""Tests for account operations."""

from uuid import uuid4

from sqlalchemy.orm import Session

from src.postgres.common.enums import AccountStatus
from src.postgres.common.models import Account, Connection
from src.postgres.common.operations.accounts import (
    create_account,
    get_account_by_id,
    get_accounts_by_connection_id,
    update_account_display_name,
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


class TestUpdateAccountDisplayName:
    """Tests for update_account_display_name operation."""

    def test_updates_display_name(self, db_session: Session, test_account: Account) -> None:
        """Should update the display name."""
        result = update_account_display_name(db_session, test_account.id, "Updated Display Name")
        db_session.commit()

        assert result is not None
        assert result.display_name == "Updated Display Name"

    def test_clears_display_name(self, db_session: Session, test_account: Account) -> None:
        """Should clear display name when set to None."""
        result = update_account_display_name(db_session, test_account.id, None)
        db_session.commit()

        assert result is not None
        assert result.display_name is None

    def test_returns_none_when_not_found(
        self, db_session: Session, test_connection: Connection
    ) -> None:
        """Should return None when account doesn't exist."""
        result = update_account_display_name(db_session, uuid4(), "Name")

        assert result is None
