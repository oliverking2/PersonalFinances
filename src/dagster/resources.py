"""Common dagster resources."""

from dagster import Definitions, resource, InitResourceContext
from dagster_aws.s3 import s3_resource

from src.gocardless.api.core import GoCardlessCredentials

from dagster import ConfigurableResource
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Iterator, Optional

from src.utils.definitions import gocardless_database_url


class PostgresDatabase(ConfigurableResource[None]):
    """GoCardless database resource for Dagster."""

    database_url: str
    _engine: Optional[Engine] = None
    _session_factory: Optional[sessionmaker[Session]] = None

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


resource_defs = Definitions(
    resources={
        "s3": s3_resource,
        "gocardless_api": gocardless_api_resource,
        "postgres_database": PostgresDatabase(database_url=gocardless_database_url()),
    }
)
