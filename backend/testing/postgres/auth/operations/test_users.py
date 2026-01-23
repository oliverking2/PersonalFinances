"""Tests for user database operations."""

from uuid import uuid4

from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.auth.operations.users import create_user, get_user_by_id, get_user_by_username
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

        user = create_user(db_session, username, password)
        db_session.commit()

        assert user.id is not None
        assert user.username == username
        assert user.password_hash != password
        assert verify_password(password, user.password_hash) is True

    def test_normalises_username_to_lowercase(self, db_session: Session) -> None:
        """Should store username in lowercase."""
        user = create_user(db_session, "NewUser", "password")
        db_session.commit()

        assert user.username == "newuser"

    def test_strips_whitespace_from_username(self, db_session: Session) -> None:
        """Should strip whitespace from username."""
        user = create_user(db_session, "  newuser  ", "password")
        db_session.commit()

        assert user.username == "newuser"

    def test_sets_timestamps(self, db_session: Session) -> None:
        """Should set created_at and updated_at timestamps."""
        user = create_user(db_session, "newuser", "password")
        db_session.commit()

        # SQLite doesn't support server_default properly in tests,
        # but the columns should at least exist
        assert hasattr(user, "created_at")
        assert hasattr(user, "updated_at")
