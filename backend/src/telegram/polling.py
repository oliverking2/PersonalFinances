"""Long polling runner for Telegram bot.

Provides a simple polling mechanism for receiving Telegram updates.
Used for 2FA flows and receiving user responses.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from src.postgres.core import session_scope
from src.postgres.telegram import get_or_create_polling_cursor, update_polling_cursor
from src.telegram.client import TelegramClient, TelegramClientError
from src.telegram.models import TelegramUpdate
from src.telegram.utils.config import TelegramConfig, get_telegram_settings
from src.telegram.utils.formatting import format_message
from src.utils.definitions import database_url

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Type alias for message handler callback
MessageCallback = Callable[[TelegramUpdate], Awaitable[str | None]]


class UnauthorisedChatError(Exception):
    """Raised when a message is received from an unauthorised chat."""

    def __init__(self, chat_id: str) -> None:
        """Initialise the error.

        :param chat_id: The unauthorised chat ID.
        """
        self.chat_id = chat_id
        super().__init__(f"Unauthorised chat: {chat_id}")


class PollingRunner:
    """Async long polling runner for receiving Telegram updates.

    Runs a continuous async loop that:
    1. Polls Telegram for updates using long polling
    2. Delegates updates to registered callback
    3. Persists the polling offset
    4. Handles graceful shutdown on SIGINT/SIGTERM
    """

    def __init__(
        self,
        client: TelegramClient | None = None,
        settings: TelegramConfig | None = None,
        message_callback: MessageCallback | None = None,
    ) -> None:
        """Initialise the polling runner.

        :param client: Telegram client. If not provided, creates one from env.
        :param settings: Telegram settings. If not provided, loads from env.
        :param message_callback: Async callback for handling messages.
            Receives TelegramUpdate, returns response text or None.
        """
        self._settings = settings or get_telegram_settings()
        self._client = client or TelegramClient(
            bot_token=self._settings.bot_token,
            poll_timeout=self._settings.poll_timeout,
        )
        self._message_callback = message_callback
        self._running = False
        self._consecutive_errors = 0

    def set_message_callback(self, callback: MessageCallback) -> None:
        """Set the message callback handler.

        :param callback: Async function that receives updates and returns responses.
        """
        self._message_callback = callback

    async def run(self) -> None:
        """Start the async polling loop.

        Runs until shutdown signal is received or stop() is called.
        """
        self._running = True
        self._setup_signal_handlers()

        logger.info(
            f"Starting Telegram polling runner: poll_timeout={self._settings.poll_timeout}s"
        )

        try:
            await self._polling_loop()
        except asyncio.CancelledError:
            logger.info("Polling loop cancelled")
        finally:
            await self._client.close()
            logger.info("Polling runner stopped")

    def stop(self) -> None:
        """Signal the polling loop to stop."""
        logger.info("Stopping polling runner...")
        self._running = False

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        if sys.platform == "win32":
            logger.warning("Signal handlers not supported on Windows, use Ctrl+C")
            return

        try:
            loop = asyncio.get_running_loop()

            def signal_handler() -> None:
                logger.info("Received shutdown signal")
                self.stop()

            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, signal_handler)
        except RuntimeError:
            logger.warning("Could not set up signal handlers (no running event loop)")

    async def _polling_loop(self) -> None:
        """Execute the main async polling loop."""
        offset = await asyncio.to_thread(self._get_initial_offset)
        logger.info(f"Starting polling from offset={offset}")

        while self._running:
            try:
                updates = await self._client.get_updates(offset=offset)
                self._consecutive_errors = 0

                if not updates:
                    continue

                for update in updates:
                    await self._process_update(update)

                # Update offset to highest update_id + 1
                max_update_id = max(u.update_id for u in updates)
                offset = max_update_id + 1

                await asyncio.to_thread(self._persist_offset, max_update_id)

            except TelegramClientError as e:
                await self._handle_polling_error(e)

    def _get_initial_offset(self) -> int | None:
        """Get the initial offset from the database.

        :returns: Initial offset or None if no cursor exists.
        """
        with session_scope(database_url()) as session:
            cursor = get_or_create_polling_cursor(session)
            return cursor.last_update_id + 1 if cursor.last_update_id > 0 else None

    def _persist_offset(self, max_update_id: int) -> None:
        """Persist the polling offset to the database.

        :param max_update_id: The maximum update ID to persist.
        """
        with session_scope(database_url()) as session:
            update_polling_cursor(session, max_update_id)

    def _is_chat_allowed(self, chat_id: str) -> bool:
        """Check if a chat ID is in the allowlist.

        :param chat_id: The chat ID to check.
        :returns: True if allowed or no allowlist configured.
        """
        if not self._settings.allowed_chat_ids_set:
            return True  # No allowlist means all chats allowed
        return chat_id in self._settings.allowed_chat_ids_set

    async def _process_update(self, update: TelegramUpdate) -> None:
        """Process a single update.

        :param update: The Telegram update to process.
        """
        if update.message is None:
            logger.debug(f"Ignoring update without message: update_id={update.update_id}")
            return

        message = update.message
        chat_id = str(message.chat.id)
        text = message.get_text_with_urls()

        if not text:
            logger.debug(f"Ignoring message without text: chat_id={chat_id}")
            return

        if not self._is_chat_allowed(chat_id):
            logger.warning(f"Received message from unauthorised chat: chat_id={chat_id}")
            return

        logger.info(f"Processing message: chat_id={chat_id}, text={text[:50]}...")

        try:
            if self._message_callback:
                response = await self._message_callback(update)
                if response:
                    await self._send_response(chat_id, response)
        except Exception:
            logger.exception(f"Error processing update: update_id={update.update_id}")
            await self._send_error_response(chat_id)

    async def _send_response(self, chat_id: str, text: str) -> None:
        """Send a response message to a chat.

        :param chat_id: Target chat ID.
        :param text: Response text (may contain Markdown).
        """
        try:
            formatted_text, parse_mode = format_message(text)
            await self._client.send_message(formatted_text, chat_id=chat_id, parse_mode=parse_mode)
            logger.debug(f"Sent response to chat_id={chat_id}")
        except TelegramClientError:
            logger.exception(f"Failed to send response to chat_id={chat_id}")

    async def _send_error_response(self, chat_id: str) -> None:
        """Send a generic error response to a chat.

        :param chat_id: Target chat ID.
        """
        try:
            await self._client.send_message(
                "Sorry, I encountered an error. Please try again.",
                chat_id=chat_id,
                parse_mode="",
            )
        except TelegramClientError:
            logger.exception(f"Failed to send error response to chat_id={chat_id}")

    async def _handle_polling_error(self, error: TelegramClientError) -> None:
        """Handle an error during polling with exponential backoff.

        :param error: The error that occurred.
        """
        self._consecutive_errors += 1
        logger.warning(f"Polling error (consecutive: {self._consecutive_errors}): {error}")

        if self._consecutive_errors >= self._settings.max_consecutive_errors:
            logger.error(
                f"Max consecutive errors reached ({self._settings.max_consecutive_errors}), "
                f"backing off for {self._settings.backoff_delay}s"
            )
            await asyncio.sleep(self._settings.backoff_delay)
            self._consecutive_errors = 0
        else:
            await asyncio.sleep(self._settings.error_retry_delay)


async def wait_for_reply(
    client: TelegramClient,
    chat_id: str,
    prompt: str,
    timeout_seconds: int = 300,
    poll_interval: int = 2,
) -> str | None:
    """Send a message and wait for a reply from the user.

    Useful for 2FA flows where you need to ask for a code and wait for response.

    :param client: Telegram client to use.
    :param chat_id: Chat ID to send to and receive from.
    :param prompt: Message to send asking for input.
    :param timeout_seconds: Maximum time to wait for reply.
    :param poll_interval: Seconds between polling attempts.
    :returns: The user's reply text, or None if timeout.
    """
    # Send the prompt
    await client.send_message(prompt, chat_id=chat_id)

    # Get initial offset
    with session_scope(database_url()) as session:
        cursor = get_or_create_polling_cursor(session)
        offset = cursor.last_update_id + 1 if cursor.last_update_id > 0 else None

    # Poll for reply
    elapsed = 0
    while elapsed < timeout_seconds:
        try:
            updates = await client.get_updates(offset=offset, timeout=poll_interval)

            for update in updates:
                if update.message and str(update.message.chat.id) == chat_id:
                    reply_text = update.message.get_text_with_urls()
                    if reply_text:
                        # Update cursor
                        with session_scope(database_url()) as session:
                            update_polling_cursor(session, update.update_id)
                        return reply_text

                # Update offset even if not the message we want
                if updates:
                    offset = max(u.update_id for u in updates) + 1

        except TelegramClientError as e:
            logger.warning(f"Polling error while waiting for reply: {e}")

        elapsed += poll_interval

    logger.warning(f"Timeout waiting for reply from chat_id={chat_id}")
    return None
