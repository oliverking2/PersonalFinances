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


def get_postgres_host() -> str:
    """Get PostgreSQL hostname from environment.

    :return: The PostgreSQL hostname.
    :raises ValueError: If POSTGRES_HOSTNAME is not set.
    """
    postgres_host = os.getenv("POSTGRES_HOSTNAME")
    if not postgres_host:
        raise ValueError("Environment variable POSTGRES_HOSTNAME not set.")
    logger.debug(f"PostgreSQL host configured as: {postgres_host}")
    return postgres_host


def get_postgres_port() -> int:
    """Get PostgreSQL port from environment.

    :return: The PostgreSQL port (default: 5432).
    """
    return int(os.getenv("POSTGRES_PORT", "5432"))


def _mask_password_in_url(url: str) -> str:
    """Mask password in a database URL for safe logging.

    :param url: The database URL containing credentials.
    :return: The URL with password replaced by asterisks.
    """
    # Find the password between : and @ after the username
    # Format: postgresql+psycopg2://username:password@host:port/database
    if "://" in url and "@" in url:
        prefix_end = url.index("://") + 3
        at_pos = url.index("@")
        credentials = url[prefix_end:at_pos]
        if ":" in credentials:
            username = credentials.split(":")[0]
            return f"{url[:prefix_end]}{username}:****@{url[at_pos + 1 :]}"
    return url


def dagster_database_url() -> str:
    """Generate a PostgreSQL database connection URL for Dagster.

    :return: The constructed database URL as a string.
    """
    host = get_postgres_host()
    port = get_postgres_port()
    url = (
        f"postgresql+psycopg2://{os.getenv('POSTGRES_USERNAME')}:{os.getenv('POSTGRES_PASSWORD')}@"
        f"{host}:{port}/{os.getenv('POSTGRES_DAGSTER_DATABASE')}"
    )
    logger.info(f"Database URL: {_mask_password_in_url(url)}")
    return url


def database_url() -> str:
    """Generate the main PostgreSQL database connection URL.

    :return: The constructed database URL as a string.
    """
    host = get_postgres_host()
    port = get_postgres_port()
    url = (
        f"postgresql+psycopg2://{os.getenv('POSTGRES_USERNAME')}:{os.getenv('POSTGRES_PASSWORD')}@"
        f"{host}:{port}/{os.getenv('POSTGRES_DATABASE')}"
    )
    logger.info(f"Database URL: {_mask_password_in_url(url)}")
    return url


# Alias for backwards compatibility
def gocardless_database_url() -> str:
    """Generate the main database URL (legacy alias).

    :return: The constructed database URL as a string.
    """
    return database_url()


# JWT Authentication Configuration
def jwt_secret() -> str:
    """Get the JWT signing secret from environment.

    :return: The JWT secret key.
    :raises ValueError: If JWT_SECRET is not set.
    """
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise ValueError("Environment variable JWT_SECRET must be set")
    return secret


def jwt_algorithm() -> str:
    """Get the JWT algorithm from environment.

    :return: The JWT algorithm (default: HS256).
    """
    return os.getenv("JWT_ALGORITHM", "HS256")


def access_token_expire_minutes() -> int:
    """Get access token expiry in minutes.

    :return: Access token expiry in minutes (default: 15).
    """
    return int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))


def refresh_token_expire_days() -> int:
    """Get refresh token expiry in days.

    :return: Refresh token expiry in days (default: 30).
    """
    return int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))


def is_local_environment() -> bool:
    """Check if running in local development environment.

    :return: True if ENVIRONMENT is 'local', False otherwise.
    """
    return os.getenv("ENVIRONMENT") == "local"
