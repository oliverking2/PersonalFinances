"""Telegram integration for notifications and 2FA.

Provides:
- TelegramClient: Send messages, receive updates
- TelegramConfig: Configuration via environment variables
- PollingRunner: Long polling for receiving messages
- wait_for_reply: Simple 2FA helper function
- process_message: Default message handler with /link, /status commands
"""

from src.telegram.client import TelegramClient, TelegramClientError
from src.telegram.handlers import process_message
from src.telegram.models import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    SendMessageResult,
    TelegramChat,
    TelegramMessageInfo,
    TelegramUpdate,
    TelegramUser,
)
from src.telegram.polling import PollingRunner, UnauthorisedChatError, wait_for_reply
from src.telegram.utils import TelegramConfig, TelegramMode, get_telegram_settings

__all__ = [
    "CallbackQuery",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "PollingRunner",
    "SendMessageResult",
    "TelegramChat",
    "TelegramClient",
    "TelegramClientError",
    "TelegramConfig",
    "TelegramMessageInfo",
    "TelegramMode",
    "TelegramUpdate",
    "TelegramUser",
    "UnauthorisedChatError",
    "get_telegram_settings",
    "process_message",
    "wait_for_reply",
]
