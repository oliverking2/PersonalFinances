"""Message handlers for the Telegram bot.

Provides handlers for processing commands like /link for account linking.
"""

from __future__ import annotations

import logging
import re

from sqlalchemy.orm import Session

from src.postgres.auth.operations.users import (
    get_user_by_telegram_chat_id,
    link_telegram,
)
from src.postgres.telegram import validate_and_consume_link_code
from src.telegram.models import TelegramUpdate

logger = logging.getLogger(__name__)

# Pattern for /link command with code
LINK_PATTERN = re.compile(r"^/link\s+([A-Za-z0-9]+)$")


def handle_link_command(
    session: Session,
    update: TelegramUpdate,
) -> str:
    """Handle the /link command for account linking.

    :param session: Database session.
    :param update: The Telegram update containing the message.
    :returns: Response message to send back.
    """
    if update.message is None:
        return "Invalid message."

    chat_id = str(update.message.chat.id)
    text = update.message.get_text_with_urls() or ""

    # Check if already linked
    existing_user = get_user_by_telegram_chat_id(session, chat_id)
    if existing_user:
        return (
            f"This chat is already linked to account '{existing_user.username}'. "
            "Unlink from the web app first to link to a different account."
        )

    # Parse the code
    match = LINK_PATTERN.match(text.strip())
    if not match:
        return (
            "To link your account, use: /link <code>\n\n"
            "Get a code from the Settings page in the web app."
        )

    code = match.group(1)

    # Validate and consume the code
    user_id = validate_and_consume_link_code(session, code)
    if user_id is None:
        return "Invalid or expired code. Please generate a new code from the Settings page."

    # Link the account
    user = link_telegram(session, user_id, chat_id)
    if user is None:
        return "Failed to link account. User not found."

    logger.info(f"Telegram linked via bot: user_id={user_id}, chat_id={chat_id}")

    return f"Successfully linked to account '{user.username}'. You will now receive notifications here."


def handle_start_command(update: TelegramUpdate) -> str:
    """Handle the /start command.

    :param update: The Telegram update containing the message.
    :returns: Welcome message.
    """
    return (
        "Welcome to Personal Finances Bot!\n\n"
        "To link your account:\n"
        "1. Go to Settings in the web app\n"
        "2. Click 'Link Telegram'\n"
        "3. Send /link <code> here\n\n"
        "Once linked, you'll receive notifications about:\n"
        "- Budget warnings and alerts\n"
        "- Large transactions\n"
        "- Weekly summaries"
    )


def handle_help_command(update: TelegramUpdate) -> str:
    """Handle the /help command.

    :param update: The Telegram update containing the message.
    :returns: Help message.
    """
    return (
        "Available commands:\n\n"
        "/link <code> - Link your account\n"
        "/status - Check link status\n"
        "/help - Show this help message"
    )


def handle_status_command(session: Session, update: TelegramUpdate) -> str:
    """Handle the /status command.

    :param session: Database session.
    :param update: The Telegram update containing the message.
    :returns: Status message.
    """
    if update.message is None:
        return "Invalid message."

    chat_id = str(update.message.chat.id)
    user = get_user_by_telegram_chat_id(session, chat_id)

    if user:
        return f"Linked to account: {user.username}"
    return "Not linked to any account. Use /link <code> to link."


def _dispatch_command(session: Session, update: TelegramUpdate, text: str) -> str | None:
    """Dispatch a command to the appropriate handler.

    :param session: Database session.
    :param update: The Telegram update containing the message.
    :param text: The message text.
    :returns: Response message, or None if not a command.
    """
    if text.startswith("/start"):
        return handle_start_command(update)
    if text.startswith("/help"):
        return handle_help_command(update)
    if text.startswith("/link"):
        return handle_link_command(session, update)
    if text.startswith("/status"):
        return handle_status_command(session, update)
    if text.startswith("/"):
        return "Unknown command. Use /help to see available commands."
    return None


def process_message(session: Session, update: TelegramUpdate) -> str | None:
    """Process an incoming message and return a response.

    :param session: Database session.
    :param update: The Telegram update containing the message.
    :returns: Response message, or None if no response needed.
    """
    if update.message is None:
        return None

    text = (update.message.get_text_with_urls() or "").strip()
    if not text:
        return None

    return _dispatch_command(session, update, text)
