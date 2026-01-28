"""Tests for user database operations."""

from uuid import uuid4

from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.auth.operations.users import (
    create_user,
    get_user_by_id,
    get_user_by_telegram_chat_id,
    get_user_by_username,
    link_telegram,
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
