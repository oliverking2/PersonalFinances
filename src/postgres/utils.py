"""Utils for postgres."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


def create_session(database_url: str) -> Session:
    """Create a SQLAlchemy session for the given database URL.

    :param database_url: The database URL to connect to.
    :return: A SQLAlchemy session object.
    """
    engine = create_engine(database_url)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return session_local()
