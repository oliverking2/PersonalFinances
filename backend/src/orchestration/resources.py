"""Common dagster resources."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config
from dagster import ConfigurableResource, Definitions, InitResourceContext, resource
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.providers.gocardless.api.core import GoCardlessCredentials
from src.utils.definitions import gocardless_database_url

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

# Timeout configuration for boto3 clients (in seconds)
BOTO3_CONNECT_TIMEOUT = 30
BOTO3_READ_TIMEOUT = 60


class PostgresDatabase(ConfigurableResource[None]):
    """GoCardless database resource for Dagster."""

    database_url: str
    _engine: Engine | None = None
    _session_factory: sessionmaker[Session] | None = None

    def setup_for_execution(self, context: InitResourceContext) -> None:
        """Initialize the database engine."""
        self._engine = create_engine(self.database_url)
        self._session_factory = sessionmaker(bind=self._engine)

    @property
    def engine(self) -> Engine:
        """Get the SQLAlchemy engine."""
        if self._engine is None:
            raise RuntimeError("PostgresDatabase not initialized for execution.")
        return self._engine

    @property
    def session_factory(self) -> sessionmaker[Session]:
        """Get the SQLAlchemy session factory."""
        if self._session_factory is None:
            raise RuntimeError("PostgresDatabase not initialized for execution.")
        return self._session_factory

    @contextmanager
    def get_session(self) -> Iterator[Session]:
        """Get a database session with automatic cleanup."""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


@resource
def gocardless_api_resource() -> GoCardlessCredentials:
    """Create a GoCardlessCredentials object for use in other resources and ops."""
    return GoCardlessCredentials()


@resource
def s3_resource_with_timeout() -> S3Client:
    """Create an S3 client with timeout configuration.

    :returns: A boto3 S3 client with connect and read timeouts configured.
    """
    return boto3.client(
        "s3",
        config=Config(
            connect_timeout=BOTO3_CONNECT_TIMEOUT,
            read_timeout=BOTO3_READ_TIMEOUT,
        ),
    )


resource_defs = Definitions(
    resources={
        "s3": s3_resource_with_timeout,
        "gocardless_api": gocardless_api_resource,
        "postgres_database": PostgresDatabase(database_url=gocardless_database_url()),
    }
)
