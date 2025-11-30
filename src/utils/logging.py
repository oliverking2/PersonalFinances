"""Configure standard logging."""

import logging

from dagster import get_dagster_logger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)


def get_logger(name: str) -> logging.Logger:
    """Create a logger with the specified name which is linked to the dagster logger."""
    return get_dagster_logger(name=name)
