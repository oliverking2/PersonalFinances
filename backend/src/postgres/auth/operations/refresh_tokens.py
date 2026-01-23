"""Refresh token database operations.

This module provides operations for managing refresh tokens,
including creation, rotation, revocation, and replay detection.
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from src.postgres.auth.models import RefreshToken, User
from src.utils.definitions import refresh_token_expire_days
from src.utils.security import generate_refresh_token, hash_refresh_token, verify_refresh_token

logger = logging.getLogger(__name__)


def create_refresh_token(  # noqa: PLR0913
    session: Session,
    user: User,
    expires_days: int | None = None,
    user_agent: str | None = None,
    ip_address: str | None = None,
    rotated_from_id: UUID | None = None,
) -> tuple[str, RefreshToken]:
    """Create a new refresh token for a user.

    :param session: SQLAlchemy session.
    :param user: User to create token for.
    :param expires_days: Optional custom expiry in days. Defaults to config value.
    :param user_agent: Optional user agent string from request.
    :param ip_address: Optional IP address from request.
    :param rotated_from_id: Optional ID of the token this was rotated from.
    :return: Tuple of (raw_token, RefreshToken entity).
    """
    if expires_days is None:
        expires_days = refresh_token_expire_days()

    raw_token = generate_refresh_token()
    token_hash = hash_refresh_token(raw_token)
    expires_at = datetime.now(UTC) + timedelta(days=expires_days)

    token = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
        rotated_from=rotated_from_id,
    )
    session.add(token)
    session.flush()

    logger.info(f"Created refresh token: user_id={user.id}, token_id={token.id}")
    return raw_token, token


def find_token_by_raw_value(session: Session, raw_token: str) -> RefreshToken | None:
    """Find a refresh token by its raw value.

    This iterates through active tokens and verifies the hash.
    For MVP, this is acceptable. Add SHA256 lookup hash for scale.

    :param session: SQLAlchemy session.
    :param raw_token: Raw token string to find.
    :return: RefreshToken if found, None otherwise.
    """
    # Get all tokens (including revoked for replay detection)
    # We check expiry in Python to handle timezone-naive datetimes from SQLite
    tokens = session.query(RefreshToken).all()
    now = datetime.now(UTC)

    for token in tokens:
        expires_at = token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if expires_at > now and verify_refresh_token(raw_token, token.token_hash):
            return token

    return None


def is_token_valid(token: RefreshToken) -> bool:
    """Check if a refresh token is valid (not revoked and not expired).

    :param token: RefreshToken to check.
    :return: True if valid, False otherwise.
    """
    now = datetime.now(UTC)
    # Handle naive datetimes from SQLite (test environment)
    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return token.revoked_at is None and expires_at > now


def revoke_token(session: Session, token: RefreshToken) -> None:
    """Revoke a refresh token.

    :param session: SQLAlchemy session.
    :param token: RefreshToken to revoke.
    """
    token.revoked_at = datetime.now(UTC)
    session.flush()
    logger.info(f"Revoked refresh token: token_id={token.id}, user_id={token.user_id}")


def revoke_all_user_tokens(session: Session, user_id: UUID) -> int:
    """Revoke all refresh tokens for a user.

    Used for replay detection to invalidate entire session chain.

    :param session: SQLAlchemy session.
    :param user_id: User ID whose tokens to revoke.
    :return: Number of tokens revoked.
    """
    now = datetime.now(UTC)
    result = (
        session.query(RefreshToken)
        .filter(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .update({"revoked_at": now})
    )
    session.flush()
    logger.warning(
        f"Revoked all tokens for user (potential replay attack): "
        f"user_id={user_id}, tokens_revoked={result}"
    )
    return result


def rotate_token(
    session: Session,
    old_token: RefreshToken,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[str, RefreshToken]:
    """Rotate a refresh token (revoke old, create new).

    :param session: SQLAlchemy session.
    :param old_token: Token to rotate.
    :param user_agent: Optional user agent string from request.
    :param ip_address: Optional IP address from request.
    :return: Tuple of (raw_token, new RefreshToken entity).
    """
    # Revoke the old token
    revoke_token(session, old_token)

    # Create new token linked to the old one
    raw_token, new_token = create_refresh_token(
        session,
        old_token.user,
        user_agent=user_agent,
        ip_address=ip_address,
        rotated_from_id=old_token.id,
    )

    logger.info(
        f"Rotated refresh token: old_id={old_token.id}, new_id={new_token.id}, "
        f"user_id={old_token.user_id}"
    )
    return raw_token, new_token
