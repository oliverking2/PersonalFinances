"""Tests for Telegram database operations."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.telegram import (
    TelegramLinkCode,
    cleanup_expired_link_codes,
    create_link_code,
    get_or_create_polling_cursor,
    update_polling_cursor,
    validate_and_consume_link_code,
)


class TestGetOrCreatePollingCursor:
    """Tests for get_or_create_polling_cursor operation."""

    def test_creates_cursor_when_none_exists(self, db_session: Session) -> None:
        """Should create a new cursor with default values."""
        cursor = get_or_create_polling_cursor(db_session)
        db_session.commit()

        assert cursor.id == 1
        assert cursor.last_update_id == 0
        assert cursor.updated_at is not None

    def test_returns_existing_cursor(self, db_session: Session) -> None:
        """Should return existing cursor without creating new one."""
        cursor1 = get_or_create_polling_cursor(db_session)
        cursor1.last_update_id = 100
        db_session.commit()

        cursor2 = get_or_create_polling_cursor(db_session)

        assert cursor2.id == cursor1.id
        assert cursor2.last_update_id == 100


class TestUpdatePollingCursor:
    """Tests for update_polling_cursor operation."""

    def test_updates_cursor_value(self, db_session: Session) -> None:
        """Should update the last_update_id."""
        cursor = update_polling_cursor(db_session, 12345)
        db_session.commit()

        assert cursor.last_update_id == 12345

    def test_updates_timestamp(self, db_session: Session) -> None:
        """Should update the updated_at timestamp."""
        cursor = get_or_create_polling_cursor(db_session)
        db_session.commit()

        old_timestamp = cursor.updated_at
        cursor = update_polling_cursor(db_session, 100)
        db_session.commit()

        assert cursor.updated_at >= old_timestamp


class TestCreateLinkCode:
    """Tests for create_link_code operation."""

    def test_creates_code_for_user(self, db_session: Session, test_user: User) -> None:
        """Should create a link code for the user."""
        code = create_link_code(db_session, test_user.id)
        db_session.commit()

        assert code.user_id == test_user.id
        assert len(code.code) == 8
        # Handle SQLite's lack of timezone support
        expires_at = code.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        assert expires_at > datetime.now(UTC)

    def test_code_is_alphanumeric(self, db_session: Session, test_user: User) -> None:
        """Should generate alphanumeric codes without ambiguous characters."""
        code = create_link_code(db_session, test_user.id)
        db_session.commit()

        # Should only contain uppercase letters and digits, no 0, O, I, 1, L
        for char in code.code:
            assert char.isalnum()
            assert char not in "0OI1L"

    def test_deletes_existing_codes_for_user(self, db_session: Session, test_user: User) -> None:
        """Should delete any existing codes before creating a new one."""
        code1 = create_link_code(db_session, test_user.id)
        db_session.commit()
        first_code = code1.code

        code2 = create_link_code(db_session, test_user.id)
        db_session.commit()

        # First code should be gone
        existing = (
            db_session.query(TelegramLinkCode)
            .filter(TelegramLinkCode.code == first_code)
            .one_or_none()
        )
        assert existing is None
        assert code2.code != first_code


class TestValidateAndConsumeLinkCode:
    """Tests for validate_and_consume_link_code operation."""

    def test_returns_user_id_for_valid_code(self, db_session: Session, test_user: User) -> None:
        """Should return user_id when code is valid."""
        code = create_link_code(db_session, test_user.id)
        db_session.commit()

        user_id = validate_and_consume_link_code(db_session, code.code)
        db_session.commit()

        assert user_id == test_user.id

    def test_deletes_code_after_validation(self, db_session: Session, test_user: User) -> None:
        """Should delete the code after successful validation."""
        code = create_link_code(db_session, test_user.id)
        db_session.commit()
        code_value = code.code

        validate_and_consume_link_code(db_session, code_value)
        db_session.commit()

        # Code should be gone
        existing = (
            db_session.query(TelegramLinkCode)
            .filter(TelegramLinkCode.code == code_value)
            .one_or_none()
        )
        assert existing is None

    def test_returns_none_for_invalid_code(self, db_session: Session) -> None:
        """Should return None for non-existent code."""
        user_id = validate_and_consume_link_code(db_session, "INVALID1")
        assert user_id is None

    def test_returns_none_for_expired_code(self, db_session: Session, test_user: User) -> None:
        """Should return None and delete expired code."""
        code = create_link_code(db_session, test_user.id)
        # Manually expire the code
        code.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db_session.commit()
        code_value = code.code

        user_id = validate_and_consume_link_code(db_session, code_value)
        db_session.commit()

        assert user_id is None
        # Code should be deleted
        existing = (
            db_session.query(TelegramLinkCode)
            .filter(TelegramLinkCode.code == code_value)
            .one_or_none()
        )
        assert existing is None

    def test_handles_lowercase_input(self, db_session: Session, test_user: User) -> None:
        """Should validate codes case-insensitively."""
        code = create_link_code(db_session, test_user.id)
        db_session.commit()

        # Codes are stored uppercase, but input can be lowercase
        user_id = validate_and_consume_link_code(db_session, code.code.lower())
        db_session.commit()

        assert user_id == test_user.id


class TestCleanupExpiredLinkCodes:
    """Tests for cleanup_expired_link_codes operation."""

    def test_deletes_expired_codes(self, db_session: Session, test_user: User) -> None:
        """Should delete all expired codes."""
        code = create_link_code(db_session, test_user.id)
        code.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db_session.commit()

        count = cleanup_expired_link_codes(db_session)
        db_session.commit()

        assert count == 1

    def test_keeps_valid_codes(self, db_session: Session, test_user: User) -> None:
        """Should not delete non-expired codes."""
        create_link_code(db_session, test_user.id)
        db_session.commit()

        count = cleanup_expired_link_codes(db_session)
        db_session.commit()

        assert count == 0
