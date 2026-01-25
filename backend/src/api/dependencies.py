"""FastAPI dependencies for dependency injection."""

import secrets
from collections.abc import Generator

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.auth.operations.users import get_user_by_id
from src.postgres.core import create_session
from src.providers.gocardless.api.core import GoCardlessCredentials
from src.utils.definitions import admin_token, gocardless_database_url, is_local_environment
from src.utils.security import decode_access_token

# Optional bearer token - doesn't auto-raise 401
_bearer_scheme = HTTPBearer(auto_error=False)

# Admin bearer token - required for protected admin endpoints
_admin_bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session]:
    """Get a database session.

    Yields a SQLAlchemy session and ensures cleanup after the request.

    :yields: SQLAlchemy session.
    """
    session = create_session(gocardless_database_url())
    try:
        yield session
    finally:
        session.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT token.

    :param credentials: Bearer token credentials from Authorization header.
    :param db: Database session.
    :return: Authenticated User entity.
    :raises HTTPException: 401 if token is missing, invalid, or user not found.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def get_gocardless_credentials() -> GoCardlessCredentials:
    """Get GoCardless API credentials.

    Creates a new GoCardlessCredentials instance that handles
    token management and API authentication.

    :returns: GoCardless credentials with active access token.
    """
    return GoCardlessCredentials()


def require_admin_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_admin_bearer_scheme),
) -> None:
    """Verify admin token for protected operations.

    In local environment, this check is skipped if no admin token is configured.
    In non-local environments, an admin token is always required.

    :param credentials: Bearer token credentials from Authorization header.
    :raises HTTPException: 401 if token is missing or invalid.
    """
    configured_token = admin_token()

    # In local environment with no token configured, allow access
    if is_local_environment() and not configured_token:
        return

    # Token is required in non-local environments
    if not configured_token:
        raise HTTPException(
            status_code=401,
            detail="Admin token not configured",
        )

    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Admin token required",
        )

    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(credentials.credentials, configured_token):
        raise HTTPException(
            status_code=401,
            detail="Invalid admin token",
        )
