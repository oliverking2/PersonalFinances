"""Configure standard logging."""

import logging
import os
import sys
from collections.abc import Iterable

from dagster import get_dagster_logger


def _set_logger_levels(names: Iterable[str], level: int) -> None:
    """Set multiple loggers to the same level.

    :param names: Logger names to configure.
    :param level: Log level to set.
    """
    for name in names:
        logging.getLogger(name).setLevel(level)


def configure_logging() -> None:
    """Configure application logging based on environment.

    Log level is determined by:
    1. LOG_LEVEL environment variable (if set)
    2. DEBUG for local environment (ENVIRONMENT=local)
    3. INFO otherwise (container/production)

    Configures the root logger and silences noisy third-party loggers.
    """
    # Determine log level
    log_level_str = os.getenv("LOG_LEVEL")
    if log_level_str:
        log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    elif os.getenv("ENVIRONMENT") == "local":
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    # Configure root logger with our format
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        stream=sys.stdout,
        force=True,  # Override any existing configuration
    )

    # Ensure uvicorn loggers propagate to root (don't attach their own handlers)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lib_logger = logging.getLogger(name)
        lib_logger.handlers.clear()
        lib_logger.propagate = True

    # Uvicorn access logs (optional via env var)
    access_enabled = os.getenv("LOG_UVICORN_ACCESS", "false").strip().lower() == "true"
    if not access_enabled:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # HTTP client noise (httpx/httpcore spam DEBUG on every request)
    _set_logger_levels(
        ("httpx", "httpcore", "httpcore.http11", "httpcore.connection"),
        logging.WARNING,
    )

    # Set our application loggers to the configured level
    logging.getLogger("src").setLevel(log_level)

    # Log the configuration
    logging.getLogger(__name__).info(
        "Logging configured: level=%s", logging.getLevelName(log_level)
    )


def setup_dagster_logger(name: str) -> logging.Logger:
    """Create a logger with the specified name which is linked to the dagster logger.

    :param name: Logger name.
    :return: Configured logger instance.
    """
    return get_dagster_logger(name=name)
