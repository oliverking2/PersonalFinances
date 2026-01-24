"""Core database models setup."""

from collections.abc import Generator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base class for all database tables.

    Provides the declarative base for SQLAlchemy ORM models.
    """


@lru_cache(maxsize=4)
def get_engine(database_url: str) -> Engine:
    """Get or create an engine for the given database URL.

    Engines are cached to enable connection pooling across requests.
    Uses sensible pool defaults for production workloads.

    :param database_url: The database URL to connect to.
    :returns: A SQLAlchemy engine with connection pooling.
    """
    return create_engine(
        database_url,
        pool_size=5,
        max_overflow=10,
        pool_recycle=3600,
        pool_pre_ping=True,
    )


def create_session(database_url: str) -> Session:
    """Create a SQLAlchemy session for the given database URL.

    :param database_url: The database URL to connect to.
    :returns: A SQLAlchemy session object.
    """
    engine = get_engine(database_url)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return session_local()


@contextmanager
def session_scope(database_url: str) -> Generator[Session]:
    """Provide a transactional scope around a series of operations.

    Automatically commits on success, rolls back on exception, and
    closes the session when done.

    :param database_url: The database URL to connect to.
    :yields: A SQLAlchemy session object.

    Example::

        with session_scope(database_url) as session:
            user = session.get(User, user_id)
            user.name = "New Name"
        # Committed automatically
    """
    session = create_session(database_url)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
