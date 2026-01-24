"""Tests for GoCardless API core module."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.providers.gocardless.api.core import (
    REQUEST_TIMEOUT,
    GoCardlessCredentials,
    GoCardlessRateLimitError,
)


@pytest.fixture
def mock_env_vars() -> Generator[None]:
    """Mock GoCardless environment variables."""
    with patch.dict(
        "os.environ",
        {"GC_SECRET_ID": "test_secret_id", "GC_SECRET_KEY": "test_secret_key"},
    ):
        yield


@pytest.fixture
def mock_session() -> Generator[MagicMock]:
    """Mock requests.Session."""
    with patch("src.providers.gocardless.api.core.requests.Session") as mock_session_class:
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance
        yield mock_session_instance


@pytest.fixture
def gocardless_creds(mock_env_vars: None, mock_session: MagicMock) -> GoCardlessCredentials:
    """Create GoCardlessCredentials with mocked dependencies."""
    return GoCardlessCredentials()


class TestGetAccessToken:
    """Tests for _get_access_token method."""

    def test_get_access_token_success(
        self, gocardless_creds: GoCardlessCredentials, mock_session: MagicMock
    ) -> None:
        """Test successful token retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access": "test_token",
            "access_expires": 3600,
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        token = gocardless_creds._get_access_token()

        assert token == "test_token"
        mock_session.post.assert_called_once()
        call_kwargs = mock_session.post.call_args[1]
        assert call_kwargs["timeout"] == REQUEST_TIMEOUT

    def test_get_access_token_timeout(
        self, gocardless_creds: GoCardlessCredentials, mock_session: MagicMock
    ) -> None:
        """Test token request timeout handling."""
        mock_session.post.side_effect = requests.exceptions.Timeout()

        with pytest.raises(requests.exceptions.Timeout):
            gocardless_creds._get_access_token()

    def test_get_access_token_network_error(
        self, gocardless_creds: GoCardlessCredentials, mock_session: MagicMock
    ) -> None:
        """Test token request network error handling."""
        mock_session.post.side_effect = requests.exceptions.ConnectionError()

        with pytest.raises(requests.exceptions.ConnectionError):
            gocardless_creds._get_access_token()

    def test_get_access_token_invalid_response(
        self, gocardless_creds: GoCardlessCredentials, mock_session: MagicMock
    ) -> None:
        """Test handling of invalid response format."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"invalid": "response"}
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        with pytest.raises(KeyError):
            gocardless_creds._get_access_token()


class TestMakeGetRequest:
    """Tests for make_get_request method."""

    def test_make_get_request_success(
        self, gocardless_creds: GoCardlessCredentials, mock_session: MagicMock
    ) -> None:
        """Test successful GET request."""
        # Mock token response
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access": "test_token",
            "access_expires": 3600,
        }
        mock_token_response.raise_for_status = MagicMock()

        # Mock GET response
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"data": "test"}
        mock_get_response.raise_for_status = MagicMock()

        mock_session.post.return_value = mock_token_response
        mock_session.get.return_value = mock_get_response

        result = gocardless_creds.make_get_request("https://api.example.com/test")

        assert result == {"data": "test"}
        mock_session.get.assert_called_once()
        call_kwargs = mock_session.get.call_args[1]
        assert call_kwargs["timeout"] == REQUEST_TIMEOUT

    def test_make_get_request_rate_limit(
        self, gocardless_creds: GoCardlessCredentials, mock_session: MagicMock
    ) -> None:
        """Test rate limit handling on GET request."""
        # Mock token response
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access": "test_token",
            "access_expires": 3600,
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_token_response

        # Mock rate limit response
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_session.get.return_value = mock_response

        with pytest.raises(GoCardlessRateLimitError):
            gocardless_creds.make_get_request("https://api.example.com/test")


class TestMakePostRequest:
    """Tests for make_post_request method."""

    def test_make_post_request_success(
        self, gocardless_creds: GoCardlessCredentials, mock_session: MagicMock
    ) -> None:
        """Test successful POST request."""
        # First call is token, second is the actual request
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access": "test_token",
            "access_expires": 3600,
        }
        mock_token_response.raise_for_status = MagicMock()

        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"id": "new-resource"}
        mock_post_response.raise_for_status = MagicMock()

        mock_session.post.side_effect = [mock_token_response, mock_post_response]

        result = gocardless_creds.make_post_request(
            "https://api.example.com/create", body={"name": "test"}
        )

        assert result == {"id": "new-resource"}
        # Second call should have timeout
        call_kwargs = mock_session.post.call_args_list[1][1]
        assert call_kwargs["timeout"] == REQUEST_TIMEOUT

    def test_make_post_request_rate_limit(
        self, gocardless_creds: GoCardlessCredentials, mock_session: MagicMock
    ) -> None:
        """Test rate limit handling on POST request."""
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access": "test_token",
            "access_expires": 3600,
        }
        mock_token_response.raise_for_status = MagicMock()

        mock_rate_limit_response = MagicMock()
        mock_rate_limit_response.status_code = 429
        mock_rate_limit_response.text = "Rate limit exceeded"

        mock_session.post.side_effect = [mock_token_response, mock_rate_limit_response]

        with pytest.raises(GoCardlessRateLimitError):
            gocardless_creds.make_post_request("https://api.example.com/create")


class TestMakeDeleteRequest:
    """Tests for make_delete_request method."""

    def test_make_delete_request_success(
        self, gocardless_creds: GoCardlessCredentials, mock_session: MagicMock
    ) -> None:
        """Test successful DELETE request."""
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access": "test_token",
            "access_expires": 3600,
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_token_response

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"deleted": True}
        mock_response.raise_for_status = MagicMock()
        mock_session.delete.return_value = mock_response

        result = gocardless_creds.make_delete_request("https://api.example.com/resource/123")

        assert result == {"deleted": True}
        call_kwargs = mock_session.delete.call_args[1]
        assert call_kwargs["timeout"] == REQUEST_TIMEOUT

    def test_make_delete_request_rate_limit(
        self, gocardless_creds: GoCardlessCredentials, mock_session: MagicMock
    ) -> None:
        """Test rate limit handling on DELETE request."""
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access": "test_token",
            "access_expires": 3600,
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_token_response

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_session.delete.return_value = mock_response

        with pytest.raises(GoCardlessRateLimitError):
            gocardless_creds.make_delete_request("https://api.example.com/resource/123")


class TestMakePutRequest:
    """Tests for make_put_request method."""

    def test_make_put_request_success(
        self, gocardless_creds: GoCardlessCredentials, mock_session: MagicMock
    ) -> None:
        """Test successful PUT request."""
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access": "test_token",
            "access_expires": 3600,
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_token_response

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"updated": True}
        mock_response.raise_for_status = MagicMock()
        mock_session.put.return_value = mock_response

        result = gocardless_creds.make_put_request(
            "https://api.example.com/resource/123", body={"name": "updated"}
        )

        assert result == {"updated": True}
        call_kwargs = mock_session.put.call_args[1]
        assert call_kwargs["timeout"] == REQUEST_TIMEOUT

    def test_make_put_request_rate_limit(
        self, gocardless_creds: GoCardlessCredentials, mock_session: MagicMock
    ) -> None:
        """Test rate limit handling on PUT request."""
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access": "test_token",
            "access_expires": 3600,
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_token_response

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_session.put.return_value = mock_response

        with pytest.raises(GoCardlessRateLimitError):
            gocardless_creds.make_put_request("https://api.example.com/resource/123")


class TestRetryLogic:
    """Tests for retry logic on transient failures."""

    def test_retry_on_connection_error(
        self, gocardless_creds: GoCardlessCredentials, mock_session: MagicMock
    ) -> None:
        """Test that connection errors trigger retries."""
        # Mock token response
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access": "test_token",
            "access_expires": 3600,
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_token_response

        # First two calls fail, third succeeds
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {"data": "test"}
        mock_success_response.raise_for_status = MagicMock()

        mock_session.get.side_effect = [
            requests.exceptions.ConnectionError(),
            requests.exceptions.ConnectionError(),
            mock_success_response,
        ]

        result = gocardless_creds.make_get_request("https://api.example.com/test")

        assert result == {"data": "test"}
        assert mock_session.get.call_count == 3

    def test_retry_on_server_error(
        self, gocardless_creds: GoCardlessCredentials, mock_session: MagicMock
    ) -> None:
        """Test that 5xx errors trigger retries."""
        # Mock token response
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access": "test_token",
            "access_expires": 3600,
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_token_response

        # First call fails with 500, second succeeds
        mock_error_response = MagicMock()
        mock_error_response.status_code = 500

        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {"data": "test"}
        mock_success_response.raise_for_status = MagicMock()

        def raise_for_status_on_error() -> None:
            raise requests.exceptions.HTTPError(response=mock_error_response)

        mock_error_response.raise_for_status = raise_for_status_on_error

        mock_session.get.side_effect = [mock_error_response, mock_success_response]

        result = gocardless_creds.make_get_request("https://api.example.com/test")

        assert result == {"data": "test"}
        assert mock_session.get.call_count == 2

    def test_no_retry_on_client_error(
        self, gocardless_creds: GoCardlessCredentials, mock_session: MagicMock
    ) -> None:
        """Test that 4xx errors do not trigger retries."""
        # Mock token response
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access": "test_token",
            "access_expires": 3600,
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_token_response

        # 400 error should not retry
        mock_error_response = MagicMock()
        mock_error_response.status_code = 400

        def raise_for_status_on_error() -> None:
            raise requests.exceptions.HTTPError(response=mock_error_response)

        mock_error_response.raise_for_status = raise_for_status_on_error
        mock_session.get.return_value = mock_error_response

        with pytest.raises(requests.exceptions.HTTPError):
            gocardless_creds.make_get_request("https://api.example.com/test")

        # Should only be called once (no retries)
        assert mock_session.get.call_count == 1
