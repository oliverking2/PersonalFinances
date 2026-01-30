"""Trading 212 API key database operations."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from src.postgres.trading212.models import T212ApiKey

logger = logging.getLogger(__name__)


def create_api_key(
    session: Session,
    *,
    user_id: UUID,
    api_key_encrypted: str,
    friendly_name: str,
    t212_account_id: str | None = None,
    currency_code: str | None = None,
) -> T212ApiKey:
    """Create a new Trading 212 API key record.

    :param session: SQLAlchemy session.
    :param user_id: ID of the user who owns this API key.
    :param api_key_encrypted: Fernet-encrypted API key.
    :param friendly_name: User-provided name for this connection.
    :param t212_account_id: Trading 212 account ID from API (optional).
    :param currency_code: Account currency code from API (optional).
    :returns: The created T212ApiKey record.
    """
    api_key = T212ApiKey(
        user_id=user_id,
        api_key_encrypted=api_key_encrypted,
        friendly_name=friendly_name,
        t212_account_id=t212_account_id,
        currency_code=currency_code,
        status="active",
    )
    session.add(api_key)
    session.flush()
    logger.info(f"Created T212 API key: id={api_key.id}, user_id={user_id}")
    return api_key


def get_api_key_by_id(session: Session, api_key_id: UUID) -> T212ApiKey | None:
    """Get a Trading 212 API key by its ID.

    :param session: SQLAlchemy session.
    :param api_key_id: The API key record ID.
    :returns: The T212ApiKey record, or None if not found.
    """
    return session.get(T212ApiKey, api_key_id)


def get_api_keys_by_user(session: Session, user_id: UUID) -> list[T212ApiKey]:
    """Get all Trading 212 API keys for a user.

    :param session: SQLAlchemy session.
    :param user_id: The user's ID.
    :returns: List of T212ApiKey records for the user.
    """
    return (
        session.query(T212ApiKey)
        .filter(T212ApiKey.user_id == user_id)
        .order_by(T212ApiKey.created_at.desc())
        .all()
    )


def get_active_api_keys(session: Session, user_id: UUID) -> list[T212ApiKey]:
    """Get all active Trading 212 API keys for a user.

    :param session: SQLAlchemy session.
    :param user_id: The user's ID.
    :returns: List of active T212ApiKey records for the user.
    """
    return (
        session.query(T212ApiKey)
        .filter(
            T212ApiKey.user_id == user_id,
            T212ApiKey.status == "active",
        )
        .order_by(T212ApiKey.created_at.desc())
        .all()
    )


def get_all_api_keys_for_sync(session: Session) -> list[T212ApiKey]:
    """Get all active Trading 212 API keys for syncing.

    Used by Dagster jobs to fetch data for all users.

    :param session: SQLAlchemy session.
    :returns: List of all active T212ApiKey records.
    """
    return (
        session.query(T212ApiKey)
        .filter(T212ApiKey.status == "active")
        .order_by(T212ApiKey.created_at.asc())
        .all()
    )


def update_api_key_status(
    session: Session,
    api_key_id: UUID,
    *,
    status: str,
    error_message: str | None = None,
    t212_account_id: str | None = None,
    currency_code: str | None = None,
    last_synced_at: datetime | None = None,
) -> T212ApiKey | None:
    """Update the status and metadata of a Trading 212 API key.

    :param session: SQLAlchemy session.
    :param api_key_id: The API key record ID.
    :param status: New status ('active' or 'error').
    :param error_message: Error message if status is 'error'.
    :param t212_account_id: Trading 212 account ID from API.
    :param currency_code: Account currency code from API.
    :param last_synced_at: Timestamp of last successful sync.
    :returns: The updated T212ApiKey record, or None if not found.
    """
    api_key = session.get(T212ApiKey, api_key_id)
    if not api_key:
        logger.warning(f"T212 API key not found: id={api_key_id}")
        return None

    api_key.status = status
    api_key.error_message = error_message

    if t212_account_id is not None:
        api_key.t212_account_id = t212_account_id
    if currency_code is not None:
        api_key.currency_code = currency_code
    if last_synced_at is not None:
        api_key.last_synced_at = last_synced_at

    api_key.updated_at = datetime.now(UTC)
    session.flush()

    logger.info(f"Updated T212 API key: id={api_key_id}, status={status}")
    return api_key


def delete_api_key(session: Session, api_key_id: UUID, user_id: UUID) -> bool:
    """Delete a Trading 212 API key.

    :param session: SQLAlchemy session.
    :param api_key_id: The API key record ID.
    :param user_id: The user's ID (for ownership verification).
    :returns: True if deleted, False if not found or not owned by user.
    """
    api_key = session.get(T212ApiKey, api_key_id)
    if not api_key:
        logger.warning(f"T212 API key not found: id={api_key_id}")
        return False

    if api_key.user_id != user_id:
        logger.warning(f"T212 API key ownership mismatch: id={api_key_id}, user_id={user_id}")
        return False

    session.delete(api_key)
    session.flush()
    logger.info(f"Deleted T212 API key: id={api_key_id}")
    return True
