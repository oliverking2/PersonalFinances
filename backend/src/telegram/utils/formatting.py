"""Telegram message formatting utilities.

Converts Markdown to Telegram's MarkdownV2 format for proper rendering.
"""

from abc import ABC, abstractmethod

import telegramify_markdown


class MessageFormatter(ABC):
    """Abstract base class for message formatters.

    Implementations convert standard Markdown to platform-specific formats.
    """

    @abstractmethod
    def format(self, markdown: str) -> tuple[str, str]:
        """Convert Markdown text to platform-specific format.

        :param markdown: Standard Markdown text.
        :returns: Tuple of (formatted_text, parse_mode).
        """
        ...


class TelegramFormatter(MessageFormatter):
    """Formatter for Telegram messages using MarkdownV2.

    Uses telegramify-markdown library to convert standard Markdown
    to Telegram's MarkdownV2 format with proper escaping.
    """

    def format(self, markdown: str) -> tuple[str, str]:
        """Convert Markdown to Telegram MarkdownV2 format.

        :param markdown: Standard Markdown text.
        :returns: Tuple of (markdownv2_text, "MarkdownV2").
        """
        formatted = telegramify_markdown.markdownify(markdown)
        return formatted, "MarkdownV2"


# Default formatter instance
_default_formatter: MessageFormatter = TelegramFormatter()


def get_formatter() -> MessageFormatter:
    """Get the default message formatter.

    :returns: The configured MessageFormatter instance.
    """
    return _default_formatter


def format_message(markdown: str) -> tuple[str, str]:
    """Convert Markdown to Telegram format using the default formatter.

    :param markdown: Standard Markdown text.
    :returns: Tuple of (formatted_text, parse_mode).
    """
    return _default_formatter.format(markdown)
