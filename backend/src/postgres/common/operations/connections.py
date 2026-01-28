"""Connection database operations.

This module provides CRUD operations for Connection entities.
"""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from src.postgres.common.enums import ConnectionStatus, Provider
from src.postgres.common.models import Connection

logger = logging.getLogger(__name__)


def get_connection_by_id(session: Session, connection_id: UUID) -> Connection | None:
    """Get a connection by its ID.

    :param session: SQLAlchemy session.
    :param connection_id: Connection's UUID.
    :return: Connection if found, None otherwise.
    """
    return session.get(Connection, connection_id)


def get_connection_by_provider_id(
    session: Session,
    provider: Provider,
    provider_id: str,
) -> Connection | None:
    """Get a connection by its provider and provider-specific ID.

    :param session: SQLAlchemy session.
    :param provider: Provider enum.
    :param provider_id: Provider-specific ID (e.g., GoCardless requisition ID).
    :return: Connection if found, None otherwise.
    """
    return (
        session.query(Connection)
        .filter(
            Connection.provider == provider.value,
            Connection.provider_id == provider_id,
        )
        .first()
    )


def get_connections_by_user_id(
    session: Session,
    user_id: UUID,
    status: ConnectionStatus | None = None,
) -> list[Connection]:
    """Get all connections for a user.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param status: Filter by status (optional).
    :return: List of connections.
    """
    query = session.query(Connection).filter(Connection.user_id == user_id)

    if status is not None:
        query = query.filter(Connection.status == status.value)

    return query.order_by(Connection.created_at.desc()).all()


def create_connection(
    session: Session,
    user_id: UUID,
    provider: Provider,
    provider_id: str,
    institution_id: str,
    friendly_name: str,
    status: ConnectionStatus,
    created_at: datetime,
    expires_at: datetime | None = None,
) -> Connection:
    """Create a new connection.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param provider: Provider enum.
    :param provider_id: Provider-specific ID.
    :param institution_id: Institution ID (foreign key).
    :param friendly_name: User-friendly name for the connection.
    :param status: Connection status.
    :param created_at: When the connection was created.
    :param expires_at: When the connection expires (optional).
    :return: Created Connection entity.
    """
    connection = Connection(
        user_id=user_id,
        provider=provider.value,
        provider_id=provider_id,
        institution_id=institution_id,
        friendly_name=friendly_name,
        status=status.value,
        created_at=created_at,
        expires_at=expires_at,
    )
    session.add(connection)
    session.flush()
    logger.info(
        f"Created connection: id={connection.id}, user_id={user_id}, "
        f"provider={provider.value}, institution_id={institution_id}"
    )
    return connection


def update_connection_friendly_name(
    session: Session,
    connection_id: UUID,
    friendly_name: str,
) -> Connection | None:
    """Update a connection's friendly name.

    :param session: SQLAlchemy session.
    :param connection_id: Connection's UUID.
    :param friendly_name: New friendly name.
    :return: Updated Connection, or None if not found.
    """
    connection = get_connection_by_id(session, connection_id)
    if connection is None:
        return None

    connection.friendly_name = friendly_name
    session.flush()
    logger.info(f"Updated connection friendly_name: id={connection_id}")
    return connection


def update_connection_status(
    session: Session,
    connection_id: UUID,
    status: ConnectionStatus,
    expires_at: datetime | None = None,
) -> Connection | None:
    """Update a connection's status.

    :param session: SQLAlchemy session.
    :param connection_id: Connection's UUID.
    :param status: New status.
    :param expires_at: New expiry date (optional).
    :return: Updated Connection, or None if not found.
    """
    connection = get_connection_by_id(session, connection_id)
    if connection is None:
        return None

    connection.status = status.value
    if expires_at is not None:
        connection.expires_at = expires_at
    session.flush()
    logger.info(f"Updated connection status: id={connection_id}, status={status.value}")
    return connection


def delete_connection(session: Session, connection_id: UUID) -> bool:
    """Delete a connection and its associated accounts.

    :param session: SQLAlchemy session.
    :param connection_id: Connection's UUID.
    :return: True if deleted, False if not found.
    """
    connection = get_connection_by_id(session, connection_id)
    if connection is None:
        return False

    session.delete(connection)
    session.flush()
    logger.info(f"Deleted connection: id={connection_id}")
    return True
