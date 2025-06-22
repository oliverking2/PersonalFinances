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

MYSQL_HOST = "localhost" if env == "local" else os.getenv("MYSQL_HOST")
logger.debug(f"MySQL host configured as: {MYSQL_HOST}")

DAGSTER_DATABASE_URL = (
    f"mysql+mysqlconnector://{os.getenv('MYSQL_DAGSTER_USER')}:{os.getenv('MYSQL_DAGSTER_PASSWORD')}@"
    f"{MYSQL_HOST}:3306/{os.getenv('MYSQL_DAGSTER_DATABASE')}"
)
GOCARDLESS_DATABASE_URL = (
    f"mysql+mysqlconnector://{os.getenv('MYSQL_GOCARDLESS_USER')}:{os.getenv('MYSQL_GOCARDLESS_PASSWORD')}@"
    f"{MYSQL_HOST}:3306/{os.getenv('MYSQL_GOCARDLESS_DATABASE')}"
)

logger.debug("Database URLs configured successfully")
