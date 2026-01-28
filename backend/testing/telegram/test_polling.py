"""Tests for Telegram polling module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.telegram.models import TelegramChat, TelegramMessageInfo, TelegramUpdate
from src.telegram.polling import PollingRunner, UnauthorisedChatError


class TestPollingRunnerInit:
    """Tests for PollingRunner initialisation."""

    def test_init_with_defaults(self) -> None:
        """Test initialisation with default values."""
        with patch("src.telegram.polling.get_telegram_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                bot_token="test-token",
                poll_timeout=30,
                allowed_chat_ids_set=frozenset(),
            )

            runner = PollingRunner()

            assert runner._running is False
            assert runner._consecutive_errors == 0
            assert runner._message_callback is None

    def test_init_with_callback(self) -> None:
        """Test initialisation with message callback."""

        async def callback(update: TelegramUpdate) -> str | None:
            return "response"

        with patch("src.telegram.polling.get_telegram_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                bot_token="test-token",
                poll_timeout=30,
                allowed_chat_ids_set=frozenset(),
            )

            runner = PollingRunner(message_callback=callback)

            assert runner._message_callback is callback


class TestPollingRunnerChatAllowlist:
    """Tests for chat allowlist functionality."""

    def test_is_chat_allowed_with_empty_allowlist(self) -> None:
        """Test that all chats are allowed when allowlist is empty."""
        with patch("src.telegram.polling.get_telegram_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                bot_token="test-token",
                poll_timeout=30,
                allowed_chat_ids_set=frozenset(),
            )

            runner = PollingRunner()

            assert runner._is_chat_allowed("12345") is True
            assert runner._is_chat_allowed("99999") is True

    def test_is_chat_allowed_with_allowlist(self) -> None:
        """Test that only allowlisted chats are allowed."""
        with patch("src.telegram.polling.get_telegram_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                bot_token="test-token",
                poll_timeout=30,
                allowed_chat_ids_set=frozenset(["12345", "67890"]),
            )

            runner = PollingRunner()

            assert runner._is_chat_allowed("12345") is True
            assert runner._is_chat_allowed("67890") is True
            assert runner._is_chat_allowed("99999") is False


class TestPollingRunnerProcessUpdate:
    """Tests for update processing."""

    @pytest.mark.asyncio
    async def test_process_update_ignores_update_without_message(self) -> None:
        """Test that updates without messages are ignored."""
        with patch("src.telegram.polling.get_telegram_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                bot_token="test-token",
                poll_timeout=30,
                allowed_chat_ids_set=frozenset(),
            )

            callback = AsyncMock(return_value=None)
            runner = PollingRunner(message_callback=callback)

            update = TelegramUpdate(update_id=1, message=None)
            await runner._process_update(update)

            callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_update_ignores_message_without_text(self) -> None:
        """Test that messages without text are ignored."""
        with patch("src.telegram.polling.get_telegram_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                bot_token="test-token",
                poll_timeout=30,
                allowed_chat_ids_set=frozenset(),
            )

            callback = AsyncMock(return_value=None)
            runner = PollingRunner(message_callback=callback)

            update = TelegramUpdate(
                update_id=1,
                message=TelegramMessageInfo(
                    message_id=1,
                    date=1234567890,
                    chat=TelegramChat(id=12345, type="private"),
                    text=None,
                ),
            )
            await runner._process_update(update)

            callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_update_ignores_unauthorised_chat(self) -> None:
        """Test that messages from unauthorised chats are ignored."""
        with patch("src.telegram.polling.get_telegram_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                bot_token="test-token",
                poll_timeout=30,
                allowed_chat_ids_set=frozenset(["allowed-chat"]),
            )

            callback = AsyncMock(return_value=None)
            runner = PollingRunner(message_callback=callback)

            update = TelegramUpdate(
                update_id=1,
                message=TelegramMessageInfo(
                    message_id=1,
                    date=1234567890,
                    chat=TelegramChat(id=12345, type="private"),
                    text="Hello",
                ),
            )
            await runner._process_update(update)

            callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_update_calls_callback(self) -> None:
        """Test that callback is called for valid messages."""
        with patch("src.telegram.polling.get_telegram_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                bot_token="test-token",
                poll_timeout=30,
                allowed_chat_ids_set=frozenset(),
            )

            callback = AsyncMock(return_value=None)
            runner = PollingRunner(message_callback=callback)
            runner._client = AsyncMock()

            update = TelegramUpdate(
                update_id=1,
                message=TelegramMessageInfo(
                    message_id=1,
                    date=1234567890,
                    chat=TelegramChat(id=12345, type="private"),
                    text="Hello",
                ),
            )
            await runner._process_update(update)

            callback.assert_called_once_with(update)

    @pytest.mark.asyncio
    async def test_process_update_sends_response(self) -> None:
        """Test that callback response is sent back to chat."""
        with patch("src.telegram.polling.get_telegram_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                bot_token="test-token",
                poll_timeout=30,
                allowed_chat_ids_set=frozenset(),
            )

            callback = AsyncMock(return_value="Response text")
            runner = PollingRunner(message_callback=callback)
            runner._client = AsyncMock()
            runner._send_response = AsyncMock()

            update = TelegramUpdate(
                update_id=1,
                message=TelegramMessageInfo(
                    message_id=1,
                    date=1234567890,
                    chat=TelegramChat(id=12345, type="private"),
                    text="Hello",
                ),
            )
            await runner._process_update(update)

            runner._send_response.assert_called_once_with("12345", "Response text")


class TestUnauthorisedChatError:
    """Tests for UnauthorisedChatError."""

    def test_error_message(self) -> None:
        """Test error message format."""
        error = UnauthorisedChatError("12345")

        assert error.chat_id == "12345"
        assert "12345" in str(error)
        assert "Unauthorised" in str(error)
