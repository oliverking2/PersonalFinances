"""Security utilities for authentication.

This module provides password hashing, JWT token management, and
refresh token generation utilities.
"""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from src.utils.definitions import (
    access_token_expire_minutes,
    jwt_algorithm,
    jwt_secret,
)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    :param password: Plain text password to hash.
    :return: Bcrypt hashed password.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    :param plain_password: Plain text password to verify.
    :param hashed_password: Bcrypt hashed password to check against.
    :return: True if password matches, False otherwise.
    """
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def generate_refresh_token() -> str:
    """Generate a cryptographically secure refresh token.

    :return: URL-safe base64 encoded token (256 bits of entropy).
    """
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token for storage.

    :param token: Plain text refresh token.
    :return: Bcrypt hashed token.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(token.encode(), salt).decode()


def verify_refresh_token(plain_token: str, hashed_token: str) -> bool:
    """Verify a refresh token against its stored hash.

    :param plain_token: Plain text refresh token to verify.
    :param hashed_token: Bcrypt hashed token to check against.
    :return: True if token matches, False otherwise.
    """
    return bcrypt.checkpw(plain_token.encode(), hashed_token.encode())


def create_access_token(user_id: UUID, expires_minutes: int | None = None) -> str:
    """Create a JWT access token for a user.

    :param user_id: User ID to encode in the token.
    :param expires_minutes: Optional custom expiry in minutes. Defaults to config value.
    :return: Encoded JWT string.
    """
    if expires_minutes is None:
        expires_minutes = access_token_expire_minutes()

    expire = datetime.now(UTC) + timedelta(minutes=expires_minutes)
    payload = {
        "sub": str(user_id),
        "iat": datetime.now(UTC),
        "exp": expire,
    }
    return jwt.encode(payload, jwt_secret(), algorithm=jwt_algorithm())


def decode_access_token(token: str) -> UUID | None:
    """Decode and validate a JWT access token.

    :param token: JWT token string to decode.
    :return: User ID from the token, or None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, jwt_secret(), algorithms=[jwt_algorithm()])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None
        return UUID(user_id_str)
    except (JWTError, ValueError):
        return None
