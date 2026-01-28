"""Tests for Telegram message handlers."""

from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.telegram import create_link_code
from src.telegram.handlers import (
    handle_help_command,
    handle_link_command,
    handle_start_command,
    handle_status_command,
    process_message,
)
from src.telegram.models import TelegramChat, TelegramMessageInfo, TelegramUpdate


def _create_update(text: str, chat_id: int = 12345) -> TelegramUpdate:
    """Create a TelegramUpdate with a message for testing.

    :param text: Message text.
    :param chat_id: Chat ID.
    :returns: TelegramUpdate instance.
    """
    return TelegramUpdate(
        update_id=1,
        message=TelegramMessageInfo(
            message_id=1,
            date=1234567890,
            chat=TelegramChat(id=chat_id, type="private"),
            text=text,
        ),
    )


class TestHandleStartCommand:
    """Tests for handle_start_command."""

    def test_returns_welcome_message(self) -> None:
        """Should return a welcome message with instructions."""
        update = _create_update("/start")
        response = handle_start_command(update)

        assert "Welcome" in response
        assert "/link" in response


class TestHandleHelpCommand:
    """Tests for handle_help_command."""

    def test_returns_help_message(self) -> None:
        """Should return help message with available commands."""
        update = _create_update("/help")
        response = handle_help_command(update)

        assert "/link" in response
        assert "/status" in response
        assert "/help" in response


class TestHandleStatusCommand:
    """Tests for handle_status_command."""

    def test_returns_not_linked_when_no_user(self, db_session: Session) -> None:
        """Should indicate not linked when chat is not linked to any user."""
        update = _create_update("/status", chat_id=99999)
        response = handle_status_command(db_session, update)

        assert "Not linked" in response

    def test_returns_linked_status_with_username(
        self, db_session: Session, test_user: User
    ) -> None:
        """Should show linked account when chat is linked."""
        test_user.telegram_chat_id = "12345"
        db_session.commit()

        update = _create_update("/status", chat_id=12345)
        response = handle_status_command(db_session, update)

        assert "Linked" in response
        assert test_user.username in response


class TestHandleLinkCommand:
    """Tests for handle_link_command."""

    def test_returns_instructions_without_code(self, db_session: Session) -> None:
        """Should return instructions when no code provided."""
        update = _create_update("/link")
        response = handle_link_command(db_session, update)

        assert "/link <code>" in response

    def test_returns_error_for_invalid_code(self, db_session: Session) -> None:
        """Should return error for invalid code."""
        update = _create_update("/link INVALID1")
        response = handle_link_command(db_session, update)

        assert "Invalid" in response or "expired" in response

    def test_links_account_with_valid_code(self, db_session: Session, test_user: User) -> None:
        """Should link account when code is valid."""
        link_code = create_link_code(db_session, test_user.id)
        db_session.commit()

        update = _create_update(f"/link {link_code.code}", chat_id=99999)
        response = handle_link_command(db_session, update)
        db_session.commit()

        assert "Successfully" in response
        assert test_user.username in response

        # Verify the link
        db_session.refresh(test_user)
        assert test_user.telegram_chat_id == "99999"

    def test_fails_when_chat_already_linked(self, db_session: Session, test_user: User) -> None:
        """Should return error when chat is already linked to another account."""
        test_user.telegram_chat_id = "12345"
        db_session.commit()

        update = _create_update("/link ANYCODE1", chat_id=12345)
        response = handle_link_command(db_session, update)

        assert "already linked" in response


class TestProcessMessage:
    """Tests for process_message handler."""

    def test_handles_start_command(self, db_session: Session) -> None:
        """Should delegate /start to start handler."""
        update = _create_update("/start")
        response = process_message(db_session, update)

        assert response is not None
        assert "Welcome" in response

    def test_handles_help_command(self, db_session: Session) -> None:
        """Should delegate /help to help handler."""
        update = _create_update("/help")
        response = process_message(db_session, update)

        assert response is not None
        assert "/link" in response

    def test_handles_status_command(self, db_session: Session) -> None:
        """Should delegate /status to status handler."""
        update = _create_update("/status")
        response = process_message(db_session, update)

        assert response is not None
        assert "Not linked" in response or "Linked" in response

    def test_handles_link_command(self, db_session: Session) -> None:
        """Should delegate /link to link handler."""
        update = _create_update("/link TEST1234")
        response = process_message(db_session, update)

        assert response is not None

    def test_returns_unknown_command_for_invalid_command(self, db_session: Session) -> None:
        """Should return error for unknown commands."""
        update = _create_update("/unknown")
        response = process_message(db_session, update)

        assert response is not None
        assert "Unknown command" in response

    def test_returns_none_for_regular_message(self, db_session: Session) -> None:
        """Should return None for non-command messages."""
        update = _create_update("Hello, bot!")
        response = process_message(db_session, update)

        assert response is None

    def test_returns_none_for_empty_message(self, db_session: Session) -> None:
        """Should return None for empty messages."""
        update = TelegramUpdate(update_id=1, message=None)
        response = process_message(db_session, update)

        assert response is None
