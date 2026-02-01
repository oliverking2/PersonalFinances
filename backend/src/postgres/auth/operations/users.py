"""User database operations.

This module provides CRUD operations for User entities.
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.utils.security import hash_password

# Account lockout settings
MAX_FAILED_ATTEMPTS = 10
LOCKOUT_DURATION_MINUTES = 30

logger = logging.getLogger(__name__)


def get_user_by_id(session: Session, user_id: UUID) -> User | None:
    """Get a user by their ID.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :return: User if found, None otherwise.
    """
    return session.get(User, user_id)


def get_user_by_username(session: Session, username: str) -> User | None:
    """Get a user by their username.

    Username is normalised to lowercase before lookup.

    :param session: SQLAlchemy session.
    :param username: User's username.
    :return: User if found, None otherwise.
    """
    normalised_username = username.lower().strip()
    return session.query(User).filter(User.username == normalised_username).first()


def create_user(
    session: Session,
    username: str,
    password: str,
    first_name: str,
    last_name: str,
) -> User:
    """Create a new user.

    Username is normalised to lowercase before storage.

    :param session: SQLAlchemy session.
    :param username: User's username.
    :param password: Plain text password (will be hashed).
    :param first_name: User's first name.
    :param last_name: User's last name.
    :return: Created User entity.
    """
    normalised_username = username.lower().strip()
    user = User(
        username=normalised_username,
        password_hash=hash_password(password),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
    )
    session.add(user)
    session.flush()
    logger.info(f"Created user: id={user.id}, username={normalised_username}")
    return user


def get_user_by_telegram_chat_id(session: Session, chat_id: str) -> User | None:
    """Get a user by their linked Telegram chat ID.

    :param session: SQLAlchemy session.
    :param chat_id: Telegram chat ID.
    :return: User if found, None otherwise.
    """
    return session.query(User).filter(User.telegram_chat_id == chat_id).first()


def link_telegram(session: Session, user_id: UUID, chat_id: str) -> User | None:
    """Link a Telegram chat ID to a user account.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param chat_id: Telegram chat ID to link.
    :return: Updated User if found, None otherwise.
    """
    user = session.get(User, user_id)
    if user is None:
        return None

    user.telegram_chat_id = chat_id
    session.flush()
    logger.info(f"Linked Telegram: user_id={user_id}, chat_id={chat_id}")
    return user


def unlink_telegram(session: Session, user_id: UUID) -> User | None:
    """Unlink Telegram from a user account.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :return: Updated User if found, None otherwise.
    """
    user = session.get(User, user_id)
    if user is None:
        return None

    old_chat_id = user.telegram_chat_id
    user.telegram_chat_id = None
    session.flush()
    logger.info(f"Unlinked Telegram: user_id={user_id}, old_chat_id={old_chat_id}")
    return user


def is_user_locked(user: User) -> bool:
    """Check if a user account is currently locked.

    :param user: User entity.
    :return: True if locked and lockout hasn't expired.
    """
    if user.locked_until is None:
        return False
    return datetime.now(UTC) < user.locked_until


def record_failed_login(session: Session, user: User) -> None:
    """Record a failed login attempt, locking the account if threshold reached.

    :param session: SQLAlchemy session.
    :param user: User entity.
    """
    user.failed_login_attempts += 1

    if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
        user.locked_until = datetime.now(UTC) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        logger.warning(
            f"Account locked: user_id={user.id}, "
            f"failed_attempts={user.failed_login_attempts}, "
            f"locked_until={user.locked_until}"
        )
    else:
        logger.debug(
            f"Failed login attempt: user_id={user.id}, "
            f"failed_attempts={user.failed_login_attempts}/{MAX_FAILED_ATTEMPTS}"
        )

    session.flush()


def reset_failed_login_attempts(session: Session, user: User) -> None:
    """Reset failed login attempts after successful login.

    :param session: SQLAlchemy session.
    :param user: User entity.
    """
    if user.failed_login_attempts > 0 or user.locked_until is not None:
        user.failed_login_attempts = 0
        user.locked_until = None
        session.flush()
        logger.debug(f"Reset failed login attempts: user_id={user.id}")
