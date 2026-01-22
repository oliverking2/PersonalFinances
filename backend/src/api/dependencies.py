"""FastAPI dependencies for dependency injection."""

from collections.abc import Generator

from sqlalchemy.orm import Session

from src.postgres.core import create_session
from src.utils.definitions import gocardless_database_url


def get_db() -> Generator[Session]:
    """Get a database session.

    Yields a SQLAlchemy session and ensures cleanup after the request.

    :yields: SQLAlchemy session.
    """
    session = create_session(gocardless_database_url())
    try:
        yield session
    finally:
        session.close()
