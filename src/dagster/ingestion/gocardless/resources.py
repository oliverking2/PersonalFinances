"""GoCardless Dagster Resources."""

import os
import requests
from dagster import resource, InitResourceContext
from dotenv import load_dotenv
from requests import Session

from src.gocardless.api.auth import GoCardlessCredentials
from sqlalchemy import create_engine, Engine

load_dotenv()


@resource
def gocardless_api_resource(_context: InitResourceContext) -> Session:
    """Create a GoCardlessCredentials Session with the access token."""
    creds = GoCardlessCredentials()
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {creds.access_token}",
            "Accept": "application/json",
        }
    )
    return session


@resource
def mysql_db_resource(_context: InitResourceContext) -> Engine:
    """SQLAlchemy engine for MySQL."""
    url = f"mysql+mysqlconnector://root:{os.getenv('MYSQL_ROOT_PASSWORD')}@mysql:3306/{os.getenv('MYSQL_GOCARDLESS_DATABASE')}"
    return create_engine(url)
