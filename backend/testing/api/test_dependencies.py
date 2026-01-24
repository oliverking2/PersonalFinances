"""Tests for FastAPI dependencies."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db, get_gocardless_credentials
from src.postgres.auth.models import User
from src.providers.gocardless.api.core import GoCardlessCredentials


class TestGetDb:
    """Tests for get_db dependency."""

    @patch("src.api.dependencies.create_session")
    @patch("src.api.dependencies.gocardless_database_url")
    def test_yields_session(self, mock_db_url: MagicMock, mock_create_session: MagicMock) -> None:
        """Should yield a database session."""
        mock_db_url.return_value = "postgresql://test"
        mock_session = MagicMock(spec=Session)
        mock_create_session.return_value = mock_session

        gen = get_db()
        session = next(gen)

        assert session is mock_session
        mock_create_session.assert_called_once_with("postgresql://test")

    @patch("src.api.dependencies.create_session")
    @patch("src.api.dependencies.gocardless_database_url")
    def test_closes_session_on_exit(
        self, mock_db_url: MagicMock, mock_create_session: MagicMock
    ) -> None:
        """Should close the session when generator exits."""
        mock_db_url.return_value = "postgresql://test"
        mock_session = MagicMock(spec=Session)
        mock_create_session.return_value = mock_session

        gen = get_db()
        next(gen)

        # Exhaust the generator
        with pytest.raises(StopIteration):
            next(gen)

        mock_session.close.assert_called_once()

    @patch("src.api.dependencies.create_session")
    @patch("src.api.dependencies.gocardless_database_url")
    def test_closes_session_on_exception(
        self, mock_db_url: MagicMock, mock_create_session: MagicMock
    ) -> None:
        """Should close the session even if an exception occurs."""
        mock_db_url.return_value = "postgresql://test"
        mock_session = MagicMock(spec=Session)
        mock_create_session.return_value = mock_session

        gen = get_db()
        next(gen)

        # Simulate an exception during request handling
        with pytest.raises(ValueError):
            gen.throw(ValueError("test error"))

        mock_session.close.assert_called_once()


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @patch("src.api.dependencies.get_user_by_id")
    @patch("src.api.dependencies.decode_access_token")
    def test_returns_user_with_valid_token(
        self, mock_decode: MagicMock, mock_get_user: MagicMock
    ) -> None:
        """Should return user when token is valid."""
        mock_decode.return_value = "user-uuid-123"
        mock_user = MagicMock(spec=User)
        mock_get_user.return_value = mock_user
        mock_db = MagicMock(spec=Session)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token")

        result = get_current_user(credentials=credentials, db=mock_db)

        assert result is mock_user
        mock_decode.assert_called_once_with("valid-token")
        mock_get_user.assert_called_once_with(mock_db, "user-uuid-123")

    def test_raises_401_when_no_credentials(self) -> None:
        """Should raise 401 when no credentials provided."""
        mock_db = MagicMock(spec=Session)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=None, db=mock_db)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Not authenticated"

    @patch("src.api.dependencies.decode_access_token")
    def test_raises_401_when_token_invalid(self, mock_decode: MagicMock) -> None:
        """Should raise 401 when token is invalid."""
        mock_decode.return_value = None  # Invalid token returns None
        mock_db = MagicMock(spec=Session)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-token")

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=credentials, db=mock_db)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid or expired token"

    @patch("src.api.dependencies.get_user_by_id")
    @patch("src.api.dependencies.decode_access_token")
    def test_raises_401_when_user_not_found(
        self, mock_decode: MagicMock, mock_get_user: MagicMock
    ) -> None:
        """Should raise 401 when user not found in database."""
        mock_decode.return_value = "user-uuid-123"
        mock_get_user.return_value = None  # User not found
        mock_db = MagicMock(spec=Session)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token")

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=credentials, db=mock_db)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "User not found"


class TestGetGocardlessCredentials:
    """Tests for get_gocardless_credentials dependency."""

    @patch("src.api.dependencies.GoCardlessCredentials")
    def test_returns_credentials_instance(self, mock_creds_class: MagicMock) -> None:
        """Should return a GoCardlessCredentials instance."""
        mock_creds = MagicMock(spec=GoCardlessCredentials)
        mock_creds_class.return_value = mock_creds

        result = get_gocardless_credentials()

        assert result is mock_creds
        mock_creds_class.assert_called_once_with()
