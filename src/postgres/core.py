"""Core database models setup."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database tables.

    Provides the declarative base for SQLAlchemy ORM models.
    """
