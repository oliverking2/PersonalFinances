"""Standard definitions module."""

import os

from dotenv import load_dotenv

load_dotenv()

env = os.getenv("ENVIRONMENT")

MYSQL_HOST = "localhost" if env == "localhost" else os.getenv("MYSQL_HOST")

DAGSTER_DATABASE_URL = (
    f"mysql+mysqlconnector://{os.getenv('MYSQL_DAGSTER_USER')}:{os.getenv('MYSQL_DAGSTER_PASSWORD')}@"
    f"{MYSQL_HOST}:3306/{os.getenv('MYSQL_DAGSTER_DATABASE')}"
)
GOCARDLESS_DATABASE_URL = (
    f"mysql+mysqlconnector://{os.getenv('MYSQL_GOCARDLESS_USER')}:{os.getenv('MYSQL_GOCARDLESS_PASSWORD')}@"
    f"{MYSQL_HOST}:3306/{os.getenv('MYSQL_GOCARDLESS_DATABASE')}"
)
