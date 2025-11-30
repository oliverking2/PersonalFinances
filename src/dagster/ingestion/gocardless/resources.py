"""GoCardless Dagster Resources."""

import requests
from dagster import resource, InitResourceContext, get_dagster_logger

from src.gocardless.api.auth import GoCardlessCredentials
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

from src.utils.definitions import gocardless_database_url

logger = get_dagster_logger()


@resource
def gocardless_api_resource(_context: InitResourceContext) -> requests.Session:
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
def postgres_db_engine_resource(_context: InitResourceContext) -> Engine:
    """SQLAlchemy engine for PostgreSQL."""
    logger.info(f"Database URL: {gocardless_database_url()}")
    return create_engine(gocardless_database_url())


@resource
def postgres_db_session_resource(_context: InitResourceContext) -> Session:
    """SQLAlchemy session for PostgreSQL."""
    logger.info(f"Database URL: {gocardless_database_url()}")
    engine = create_engine(gocardless_database_url())
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return session_local()
