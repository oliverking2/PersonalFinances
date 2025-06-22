"""Standard definitions module.

This module contains configuration constants and database connection strings
used throughout the application. It loads environment variables and constructs
database URLs for different services.
"""

import logging
import os

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.debug("Environment variables loaded")

env = os.getenv("ENVIRONMENT")
logger.info(f"Running in environment: {env}")

POSTGRES_HOST = "localhost" if env == "local" else os.getenv("POSTGRES_HOST")
logger.debug(f"PostgreSQL host configured as: {POSTGRES_HOST}")

DAGSTER_DATABASE_URL = (
    f"postgresql+psycopg2://{os.getenv('POSTGRES_DAGSTER_USER')}:{os.getenv('POSTGRES_DAGSTER_PASSWORD')}@"
    f"{POSTGRES_HOST}:5432/{os.getenv('POSTGRES_DAGSTER_DATABASE')}"
)
GOCARDLESS_DATABASE_URL = (
    f"postgresql+psycopg2://{os.getenv('POSTGRES_GOCARDLESS_USER')}:{os.getenv('POSTGRES_GOCARDLESS_PASSWORD')}@"
    f"{POSTGRES_HOST}:5432/{os.getenv('POSTGRES_GOCARDLESS_DATABASE')}"
)

logger.debug("Database URLs configured successfully")
