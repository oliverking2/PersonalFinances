"""Standard definitions module.

This module contains configuration constants and database connection strings
used throughout the application. It loads environment variables and constructs
database URLs for different services.
"""

import os

from dotenv import load_dotenv

from src.utils.logging import setup_dagster_logger

logger = setup_dagster_logger(__name__)


# Load environment variables
load_dotenv()


def get_host() -> str:
    """Retrieve the hostname of the current machine.

    This function fetches the hostname of the machine on which the code
    is being executed. The hostname is determined dynamically and is returned
    as a string.

    :return: The hostname of the current machine.
    """
    env = os.getenv("ENVIRONMENT")
    logger.info(f"Running in environment: {env}")

    postgres_host = "localhost" if env == "local" else os.getenv("POSTGRES_HOST")
    if not postgres_host:
        raise ValueError("Environment variable POSTGRES_HOST not set.")
    logger.debug(f"PostgreSQL host configured as: {postgres_host}")
    return postgres_host


def dagster_database_url() -> str:
    """Generate a PostgreSQL database connection URL for Dagster.

    :return: The constructed database URL as a string.
    """
    host = get_host()
    url = (
        f"postgresql+psycopg2://{os.getenv('POSTGRES_USERNAME')}:{os.getenv('POSTGRES_PASSWORD')}@"
        f"{host}:5432/{os.getenv('POSTGRES_DAGSTER_DATABASE')}"
    )
    logger.info(f"Database URL: {url}")
    return url


def gocardless_database_url() -> str:
    """Generate a PostgreSQL database connection URL for GoCardless.

    :return: The constructed database URL as a string.
    """
    host = get_host()
    url = (
        f"postgresql+psycopg2://{os.getenv('POSTGRES_USERNAME')}:{os.getenv('POSTGRES_PASSWORD')}@"
        f"{host}:5432/{os.getenv('POSTGRES_GOCARDLESS_DATABASE')}"
    )
    logger.info(f"Database URL: {url}")
    return url
