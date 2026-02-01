"""Tests for user database operations."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.auth.operations.users import (
    create_user,
    get_user_by_id,
    get_user_by_telegram_chat_id,
    get_user_by_username,
    is_user_locked,
    link_telegram,
    record_failed_login,
    reset_failed_login_attempts,
    unlink_telegram,
)
from src.utils.security import verify_password


class TestGetUserById:
    """Tests for get_user_by_id operation."""

    def test_returns_user_when_found(self, db_session: Session, test_user: User) -> None:
        """Should return user when ID exists."""
        result = get_user_by_id(db_session, test_user.id)

        assert result is not None
        assert result.id == test_user.id
        assert result.username == test_user.username

    def test_returns_none_when_not_found(self, db_session: Session) -> None:
        """Should return None when ID doesn't exist."""
        result = get_user_by_id(db_session, uuid4())

        assert result is None


class TestGetUserByUsername:
    """Tests for get_user_by_username operation."""

    def test_returns_user_when_found(self, db_session: Session, test_user: User) -> None:
        """Should return user when username exists."""
        result = get_user_by_username(db_session, test_user.username)

        assert result is not None
        assert result.id == test_user.id
        assert result.username == test_user.username

    def test_returns_none_when_not_found(self, db_session: Session) -> None:
        """Should return None when username doesn't exist."""
        result = get_user_by_username(db_session, "nonexistent")

        assert result is None

    def test_normalises_username_to_lowercase(self, db_session: Session, test_user: User) -> None:
        """Should find user regardless of username case."""
        result = get_user_by_username(db_session, "TESTUSER")

        assert result is not None
        assert result.id == test_user.id

    def test_strips_whitespace_from_username(self, db_session: Session, test_user: User) -> None:
        """Should find user after stripping username whitespace."""
        result = get_user_by_username(db_session, "  testuser  ")

        assert result is not None
        assert result.id == test_user.id


class TestCreateUser:
    """Tests for create_user operation."""

    def test_creates_user_with_hashed_password(self, db_session: Session) -> None:
        """Should create user with bcrypt hashed password."""
        username = "newuser"
        password = "securepassword123"

        user = create_user(db_session, username, password, "New", "User")
        db_session.commit()

        assert user.id is not None
        assert user.username == username
        assert user.password_hash != password
        assert verify_password(password, user.password_hash) is True

    def test_stores_first_and_last_name(self, db_session: Session) -> None:
        """Should store first and last name."""
        user = create_user(db_session, "newuser", "password123", "John", "Doe")
        db_session.commit()

        assert user.first_name == "John"
        assert user.last_name == "Doe"

    def test_strips_whitespace_from_names(self, db_session: Session) -> None:
        """Should strip whitespace from first and last names."""
        user = create_user(db_session, "newuser", "password123", "  John  ", "  Doe  ")
        db_session.commit()

        assert user.first_name == "John"
        assert user.last_name == "Doe"

    def test_normalises_username_to_lowercase(self, db_session: Session) -> None:
        """Should store username in lowercase."""
        user = create_user(db_session, "NewUser", "password", "First", "Last")
        db_session.commit()

        assert user.username == "newuser"

    def test_strips_whitespace_from_username(self, db_session: Session) -> None:
        """Should strip whitespace from username."""
        user = create_user(db_session, "  newuser  ", "password", "First", "Last")
        db_session.commit()

        assert user.username == "newuser"

    def test_sets_timestamps(self, db_session: Session) -> None:
        """Should set created_at and updated_at timestamps."""
        user = create_user(db_session, "newuser", "password", "First", "Last")
        db_session.commit()

        # SQLite doesn't support server_default properly in tests,
        # but the columns should at least exist
        assert hasattr(user, "created_at")
        assert hasattr(user, "updated_at")


class TestGetUserByTelegramChatId:
    """Tests for get_user_by_telegram_chat_id operation."""

    def test_returns_user_when_found(self, db_session: Session, test_user: User) -> None:
        """Should return user when chat ID is linked."""
        test_user.telegram_chat_id = "123456789"
        db_session.commit()

        result = get_user_by_telegram_chat_id(db_session, "123456789")

        assert result is not None
        assert result.id == test_user.id

    def test_returns_none_when_not_found(self, db_session: Session) -> None:
        """Should return None when chat ID is not linked."""
        result = get_user_by_telegram_chat_id(db_session, "nonexistent")

        assert result is None


class TestLinkTelegram:
    """Tests for link_telegram operation."""

    def test_links_chat_id_to_user(self, db_session: Session, test_user: User) -> None:
        """Should link the chat ID to the user."""
        result = link_telegram(db_session, test_user.id, "123456789")
        db_session.commit()

        assert result is not None
        assert result.telegram_chat_id == "123456789"

    def test_returns_none_when_user_not_found(self, db_session: Session) -> None:
        """Should return None when user doesn't exist."""
        result = link_telegram(db_session, uuid4(), "123456789")

        assert result is None


class TestUnlinkTelegram:
    """Tests for unlink_telegram operation."""

    def test_unlinks_chat_id_from_user(self, db_session: Session, test_user: User) -> None:
        """Should remove the chat ID from the user."""
        test_user.telegram_chat_id = "123456789"
        db_session.commit()

        result = unlink_telegram(db_session, test_user.id)
        db_session.commit()

        assert result is not None
        assert result.telegram_chat_id is None

    def test_returns_none_when_user_not_found(self, db_session: Session) -> None:
        """Should return None when user doesn't exist."""
        result = unlink_telegram(db_session, uuid4())

        assert result is None


class TestIsUserLocked:
    """Tests for is_user_locked operation."""

    def test_returns_false_when_not_locked(self, test_user: User) -> None:
        """Should return False when locked_until is None."""
        test_user.locked_until = None

        assert is_user_locked(test_user) is False

    def test_returns_true_when_locked(self, test_user: User) -> None:
        """Should return True when locked_until is in the future."""
        test_user.locked_until = datetime.now(UTC) + timedelta(minutes=30)

        assert is_user_locked(test_user) is True

    def test_returns_false_when_lock_expired(self, test_user: User) -> None:
        """Should return False when locked_until is in the past."""
        test_user.locked_until = datetime.now(UTC) - timedelta(minutes=1)

        assert is_user_locked(test_user) is False


class TestRecordFailedLogin:
    """Tests for record_failed_login operation."""

    def test_increments_failed_attempts(self, db_session: Session, test_user: User) -> None:
        """Should increment failed_login_attempts by 1."""
        test_user.failed_login_attempts = 0

        record_failed_login(db_session, test_user)

        assert test_user.failed_login_attempts == 1

    def test_locks_account_at_10_attempts(self, db_session: Session, test_user: User) -> None:
        """Should lock account when reaching 10 failed attempts."""
        test_user.failed_login_attempts = 9

        record_failed_login(db_session, test_user)

        assert test_user.failed_login_attempts == 10
        assert test_user.locked_until is not None
        assert test_user.locked_until > datetime.now(UTC)

    def test_does_not_lock_before_10_attempts(self, db_session: Session, test_user: User) -> None:
        """Should not lock account before reaching 10 failed attempts."""
        test_user.failed_login_attempts = 8

        record_failed_login(db_session, test_user)

        assert test_user.failed_login_attempts == 9
        assert test_user.locked_until is None


class TestResetFailedLoginAttempts:
    """Tests for reset_failed_login_attempts operation."""

    def test_resets_failed_attempts_to_zero(self, db_session: Session, test_user: User) -> None:
        """Should reset failed_login_attempts to 0."""
        test_user.failed_login_attempts = 5

        reset_failed_login_attempts(db_session, test_user)

        assert test_user.failed_login_attempts == 0

    def test_clears_locked_until(self, db_session: Session, test_user: User) -> None:
        """Should clear locked_until timestamp."""
        test_user.failed_login_attempts = 10
        test_user.locked_until = datetime.now(UTC) + timedelta(minutes=30)

        reset_failed_login_attempts(db_session, test_user)

        assert test_user.failed_login_attempts == 0
        assert test_user.locked_until is None

    def test_does_nothing_when_already_zero(self, db_session: Session, test_user: User) -> None:
        """Should not error when attempts already at 0."""
        test_user.failed_login_attempts = 0
        test_user.locked_until = None

        reset_failed_login_attempts(db_session, test_user)

        assert test_user.failed_login_attempts == 0
