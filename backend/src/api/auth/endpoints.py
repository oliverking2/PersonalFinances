"""Authentication API endpoints."""

import logging

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from src.api.auth.models import (
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from src.api.dependencies import get_current_user, get_db
from src.postgres.auth.models import User
from src.postgres.auth.operations.refresh_tokens import (
    create_refresh_token,
    find_token_by_raw_value,
    is_token_valid,
    revoke_all_user_tokens,
    revoke_token,
    rotate_token,
)
from src.postgres.auth.operations.users import create_user, get_user_by_username
from src.utils.definitions import access_token_expire_minutes, is_local_environment
from src.utils.security import create_access_token, verify_password

logger = logging.getLogger(__name__)

router = APIRouter()


def _set_refresh_cookie(response: Response, token: str) -> None:
    """Set the refresh token cookie on the response.

    :param response: FastAPI Response object.
    :param token: Refresh token value.
    """
    is_local = is_local_environment()
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=not is_local,
        samesite="lax",
        path="/auth",
        max_age=60 * 60 * 24 * 30,  # 30 days
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Clear the refresh token cookie.

    :param response: FastAPI Response object.
    """
    is_local = is_local_environment()
    response.set_cookie(
        key="refresh_token",
        value="",
        httponly=True,
        secure=not is_local,
        samesite="lax",
        path="/auth",
        max_age=0,
    )


def _get_client_info(request: Request) -> tuple[str | None, str | None]:
    """Extract client info from request for audit logging.

    :param request: FastAPI Request object.
    :return: Tuple of (user_agent, ip_address).
    """
    user_agent = request.headers.get("user-agent")
    # Get real IP, considering proxies
    forwarded = request.headers.get("x-forwarded-for")
    ip_address: str | None
    if forwarded:
        ip_address = forwarded.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else None
    return user_agent, ip_address


@router.post("/login", response_model=TokenResponse, summary="Authenticate user")
def login(
    request: Request,
    response: Response,
    login_request: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user and return access token.

    Sets a refresh token cookie for subsequent token refreshes.

    :param request: FastAPI Request object.
    :param response: FastAPI Response object.
    :param login_request: Login credentials.
    :param db: Database session.
    :return: Access token response.
    :raises HTTPException: 401 if credentials are invalid.
    """
    logger.debug(f"Login attempt: username={login_request.username}")
    user = get_user_by_username(db, login_request.username)

    if not user:
        logger.warning(f"Login failed: username={login_request.username}, reason=user_not_found")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(login_request.password, user.password_hash):
        logger.warning(f"Login failed: username={login_request.username}, reason=invalid_password")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_agent, ip_address = _get_client_info(request)

    # Create tokens
    access_token = create_access_token(user.id)
    raw_refresh_token, _ = create_refresh_token(
        db,
        user,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    db.commit()

    # Set refresh token cookie
    _set_refresh_cookie(response, raw_refresh_token)

    logger.info(f"Login success: user_id={user.id}")
    return TokenResponse(
        access_token=access_token,
        expires_in=access_token_expire_minutes() * 60,
    )


@router.post("/register", response_model=UserResponse, summary="Register new user")
def register(
    register_request: RegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Register a new user.

    :param register_request: Registration details.
    :param db: Database session.
    :return: Created user information.
    :raises HTTPException: 409 if username already exists.
    """
    logger.debug(f"Registration attempt: username={register_request.username}")
    # Check if username already exists
    existing = get_user_by_username(db, register_request.username)
    if existing:
        logger.debug(f"Registration failed: username={register_request.username} already exists")
        raise HTTPException(status_code=409, detail="Username already exists")

    user = create_user(
        db,
        register_request.username,
        register_request.password,
        register_request.first_name,
        register_request.last_name,
    )
    db.commit()

    logger.info(f"User registered: user_id={user.id}, username={user.username}")
    return UserResponse(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None),
) -> TokenResponse:
    """Exchange refresh token for new access token.

    Performs token rotation: old token is revoked, new one is issued.
    Implements replay detection: if a revoked token is reused, all
    tokens for the user are revoked.

    :param request: FastAPI Request object.
    :param response: FastAPI Response object.
    :param db: Database session.
    :param refresh_token: Refresh token from cookie.
    :return: New access token response.
    :raises HTTPException: 401 if token is invalid, expired, or revoked.
    """
    logger.debug("Token refresh attempt")
    if not refresh_token:
        logger.debug("Token refresh failed: no cookie present")
        raise HTTPException(status_code=401, detail="Refresh token required")

    token = find_token_by_raw_value(db, refresh_token)

    if not token:
        logger.debug("Token refresh failed: token not found in database")
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Check for replay attack (token already revoked but hash matches)
    if token.revoked_at is not None:
        user_agent, ip_address = _get_client_info(request)
        logger.warning(
            f"Replay attack detected: user_id={token.user_id}, token_id={token.id}, "
            f"ip={ip_address}, user_agent={user_agent}"
        )
        # Revoke ALL tokens for this user
        revoke_all_user_tokens(db, token.user_id)
        db.commit()
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Token has been revoked")

    if not is_token_valid(token):
        logger.debug(f"Token refresh failed: token expired, user_id={token.user_id}")
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user_agent, ip_address = _get_client_info(request)

    # Rotate token
    new_raw_token, _ = rotate_token(
        db,
        token,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    # Create new access token
    access_token = create_access_token(token.user_id)

    db.commit()

    # Set new refresh token cookie
    _set_refresh_cookie(response, new_raw_token)

    logger.info(f"Token refresh success: user_id={token.user_id}")
    return TokenResponse(
        access_token=access_token,
        expires_in=access_token_expire_minutes() * 60,
    )


@router.post("/logout", response_model=LogoutResponse, summary="Logout user")
def logout(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None),
) -> LogoutResponse:
    """Logout user by revoking their refresh token.

    Clears the refresh token cookie regardless of token validity.

    :param response: FastAPI Response object.
    :param db: Database session.
    :param refresh_token: Refresh token from cookie.
    :return: Logout confirmation.
    """
    logger.debug("Logout request received")
    if refresh_token:
        token = find_token_by_raw_value(db, refresh_token)
        if token and token.revoked_at is None:
            revoke_token(db, token)
            db.commit()
            logger.info(f"Logout: user_id={token.user_id}")
        elif token:
            logger.debug(f"Logout: token already revoked, user_id={token.user_id}")
        else:
            logger.debug("Logout: token not found in database")
    else:
        logger.debug("Logout: no refresh token cookie present")

    _clear_refresh_cookie(response)
    return LogoutResponse(ok=True)


@router.get("/me", response_model=UserResponse, summary="Get current user")
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Get the currently authenticated user's information.

    :param current_user: Authenticated user from JWT token.
    :return: User information.
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
    )
