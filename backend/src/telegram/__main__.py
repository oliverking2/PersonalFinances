"""Entry point for running Telegram polling as a module.

Allows running with: python -m src.telegram

This runs the bot with full command handling (link, status, etc.).
"""

import asyncio
import logging

from dotenv import load_dotenv

from src.postgres.core import session_scope
from src.telegram import PollingRunner, TelegramUpdate
from src.telegram.handlers import process_message
from src.utils.definitions import database_url
from src.utils.logging import configure_logging

logger = logging.getLogger(__name__)


async def message_handler(update: TelegramUpdate) -> str | None:
    """Handle incoming messages with database access.

    :param update: The Telegram update.
    :returns: Response message or None.
    """
    with session_scope(database_url()) as session:
        return process_message(session, update)


def main() -> None:
    """Entry point for running the Telegram polling bot."""
    load_dotenv()
    configure_logging()

    runner = PollingRunner(message_callback=message_handler)
    logger.info("Starting Personal Finances bot - ready for commands")

    asyncio.run(runner.run())


if __name__ == "__main__":
    main()
