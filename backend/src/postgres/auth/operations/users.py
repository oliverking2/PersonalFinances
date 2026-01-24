"""User database operations.

This module provides CRUD operations for User entities.
"""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.utils.security import hash_password

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
