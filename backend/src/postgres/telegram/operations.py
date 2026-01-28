"""Database operations for Telegram polling state."""

from __future__ import annotations

import logging
import secrets
import string
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from src.postgres.telegram.models import TelegramLinkCode, TelegramPollingCursor

logger = logging.getLogger(__name__)

# Link codes expire after 10 minutes
LINK_CODE_EXPIRY_MINUTES = 10


def _generate_link_code() -> str:
    """Generate a random 8-character alphanumeric link code.

    :returns: Random code string.
    """
    alphabet = string.ascii_uppercase + string.digits
    # Remove ambiguous characters (0, O, I, 1, L)
    alphabet = (
        alphabet.replace("0", "")
        .replace("O", "")
        .replace("I", "")
        .replace("1", "")
        .replace("L", "")
    )
    return "".join(secrets.choice(alphabet) for _ in range(8))


def create_link_code(session: Session, user_id: UUID) -> TelegramLinkCode:
    """Create a new Telegram link code for a user.

    Deletes any existing codes for the user first.

    :param session: Database session.
    :param user_id: User ID to create the code for.
    :returns: The created link code.
    """
    # Delete any existing codes for this user
    session.query(TelegramLinkCode).filter(TelegramLinkCode.user_id == user_id).delete()

    now = datetime.now(UTC)
    code = TelegramLinkCode(
        user_id=user_id,
        code=_generate_link_code(),
        created_at=now,
        expires_at=now + timedelta(minutes=LINK_CODE_EXPIRY_MINUTES),
    )
    session.add(code)
    session.flush()

    logger.info(f"Created link code for user_id={user_id}")
    return code


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware UTC.

    SQLite doesn't store timezone info, so we need to handle naive datetimes.

    :param dt: Datetime to convert.
    :returns: Timezone-aware UTC datetime.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def validate_and_consume_link_code(session: Session, code: str) -> UUID | None:
    """Validate a link code and return the user_id if valid.

    If valid, the code is deleted to prevent reuse.

    :param session: Database session.
    :param code: The link code to validate.
    :returns: User ID if code is valid, None otherwise.
    """
    link_code = (
        session.query(TelegramLinkCode).filter(TelegramLinkCode.code == code.upper()).one_or_none()
    )

    if link_code is None:
        logger.debug(f"Link code not found: {code}")
        return None

    # Check expiry (handle SQLite's lack of timezone support)
    expires_at = _ensure_utc(link_code.expires_at)
    if expires_at < datetime.now(UTC):
        logger.debug(f"Link code expired: {code}")
        session.delete(link_code)
        session.flush()
        return None

    user_id = link_code.user_id

    # Delete the code to prevent reuse
    session.delete(link_code)
    session.flush()

    logger.info(f"Link code validated and consumed: user_id={user_id}")
    return user_id


def cleanup_expired_link_codes(session: Session) -> int:
    """Delete all expired link codes.

    :param session: Database session.
    :returns: Number of codes deleted.
    """
    now = datetime.now(UTC)
    count = session.query(TelegramLinkCode).filter(TelegramLinkCode.expires_at < now).delete()
    session.flush()
    if count > 0:
        logger.info(f"Cleaned up {count} expired link codes")
    return count


def get_or_create_polling_cursor(session: Session) -> TelegramPollingCursor:
    """Get or create the polling cursor record.

    There is only ever one cursor record (id=1).

    :param session: Database session.
    :returns: The polling cursor.
    """
    cursor = (
        session.query(TelegramPollingCursor).filter(TelegramPollingCursor.id == 1).one_or_none()
    )
    if cursor is None:
        cursor = TelegramPollingCursor(id=1, last_update_id=0)
        session.add(cursor)
        session.flush()
        logger.info("Created new polling cursor")
    return cursor


def update_polling_cursor(
    session: Session,
    last_update_id: int,
) -> TelegramPollingCursor:
    """Update the polling cursor with a new offset.

    :param session: Database session.
    :param last_update_id: The new last update ID.
    :returns: The updated cursor.
    """
    cursor = get_or_create_polling_cursor(session)
    cursor.last_update_id = last_update_id
    cursor.updated_at = datetime.now(UTC)
    session.flush()
    logger.debug(f"Updated polling cursor: last_update_id={last_update_id}")
    return cursor
