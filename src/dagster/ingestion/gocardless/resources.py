"""GoCardless Dagster Resources."""

import os
import requests
from dagster import resource, InitResourceContext
from dotenv import load_dotenv

from src.gocardless.api.auth import GoCardlessCredentials
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

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
def postgresql_db_engine_resource(_context: InitResourceContext) -> Engine:
    """SQLAlchemy engine for PostgreSQL."""
    url = f"postgresql+psycopg2://postgres:{os.getenv('POSTGRES_ROOT_PASSWORD')}@postgres:5432/{os.getenv('POSTGRES_GOCARDLESS_DATABASE')}"
    return create_engine(url)


@resource
def postgresql_db_session_resource(_context: InitResourceContext) -> Session:
    """SQLAlchemy session for PostgreSQL."""
    url = f"postgresql+psycopg2://postgres:{os.getenv('POSTGRES_ROOT_PASSWORD')}@postgres:5432/{os.getenv('POSTGRES_GOCARDLESS_DATABASE')}"
    engine = create_engine(url)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return session_local()
