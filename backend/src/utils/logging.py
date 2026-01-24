"""Configure standard logging."""

import logging
import os
import sys

from dagster import get_dagster_logger


def configure_logging() -> None:
    """Configure application logging based on environment.

    Log level is determined by:
    1. LOG_LEVEL environment variable (if set)
    2. DEBUG for local environment (ENVIRONMENT=local)
    3. INFO otherwise (container/production)

    Configures the root logger and sets uvicorn loggers to match.
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

    # Apply same format to uvicorn loggers
    formatter = logging.Formatter(log_format, datefmt=date_format)
    for uvicorn_logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.handlers = []  # Remove default handlers
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        uvicorn_logger.addHandler(handler)
        uvicorn_logger.propagate = False

    # Keep uvicorn access logs at INFO to avoid noise
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)

    # Set our application loggers to the configured level
    logging.getLogger("src").setLevel(log_level)

    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={logging.getLevelName(log_level)}")


def setup_dagster_logger(name: str) -> logging.Logger:
    """Create a logger with the specified name which is linked to the dagster logger.

    :param name: Logger name.
    :return: Configured logger instance.
    """
    return get_dagster_logger(name=name)
