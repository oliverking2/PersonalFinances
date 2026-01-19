"""Tests for GoCardless API core module."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.providers.gocardless.api.core import (
    REQUEST_TIMEOUT,
    GoCardlessCredentials,
    GoCardlessRateLimitError,
)


@pytest.fixture
def mock_ssm_params() -> MagicMock:
    """Mock SSM parameter retrieval."""
    with patch("src.providers.gocardless.api.core.get_parameter_data_from_ssm") as mock:
        mock.side_effect = ["test_secret_id", "test_secret_key"]
        yield mock


@pytest.fixture
def mock_boto_client() -> MagicMock:
    """Mock boto3 client creation."""
    with patch("src.providers.gocardless.api.core.boto3.client") as mock:
        yield mock


@pytest.fixture
def gocardless_creds(
    mock_boto_client: MagicMock, mock_ssm_params: MagicMock
) -> GoCardlessCredentials:
    """Create GoCardlessCredentials with mocked dependencies."""
    return GoCardlessCredentials()


class TestGetAccessToken:
    """Tests for _get_access_token method."""

    @patch("src.providers.gocardless.api.core.requests.post")
    def test_get_access_token_success(
        self, mock_post: MagicMock, gocardless_creds: GoCardlessCredentials
    ) -> None:
        """Test successful token retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access": "test_token",
            "access_expires": 3600,
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        token = gocardless_creds._get_access_token()

        assert token == "test_token"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["timeout"] == REQUEST_TIMEOUT

    @patch("src.providers.gocardless.api.core.requests.post")
    def test_get_access_token_timeout(
        self, mock_post: MagicMock, gocardless_creds: GoCardlessCredentials
    ) -> None:
        """Test token request timeout handling."""
        mock_post.side_effect = requests.exceptions.Timeout()

        with pytest.raises(requests.exceptions.Timeout):
            gocardless_creds._get_access_token()

    @patch("src.providers.gocardless.api.core.requests.post")
    def test_get_access_token_network_error(
        self, mock_post: MagicMock, gocardless_creds: GoCardlessCredentials
    ) -> None:
        """Test token request network error handling."""
        mock_post.side_effect = requests.exceptions.ConnectionError()

        with pytest.raises(requests.exceptions.ConnectionError):
            gocardless_creds._get_access_token()

    @patch("src.providers.gocardless.api.core.requests.post")
    def test_get_access_token_invalid_response(
        self, mock_post: MagicMock, gocardless_creds: GoCardlessCredentials
    ) -> None:
        """Test handling of invalid response format."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"invalid": "response"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with pytest.raises(KeyError):
            gocardless_creds._get_access_token()


class TestMakeGetRequest:
    """Tests for make_get_request method."""

    @patch("src.providers.gocardless.api.core.requests.post")
    @patch("src.providers.gocardless.api.core.requests.get")
    def test_make_get_request_success(
        self,
        mock_get: MagicMock,
        mock_post: MagicMock,
        gocardless_creds: GoCardlessCredentials,
    ) -> None:
        """Test successful GET request."""
        # Mock token response
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access": "test_token",
            "access_expires": 3600,
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_token_response

        # Mock GET response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = gocardless_creds.make_get_request("https://api.example.com/test")

        assert result == {"data": "test"}
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["timeout"] == REQUEST_TIMEOUT

    @patch("src.providers.gocardless.api.core.requests.post")
    @patch("src.providers.gocardless.api.core.requests.get")
    def test_make_get_request_rate_limit(
        self,
        mock_get: MagicMock,
        mock_post: MagicMock,
        gocardless_creds: GoCardlessCredentials,
    ) -> None:
        """Test rate limit handling on GET request."""
        # Mock token response
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access": "test_token",
            "access_expires": 3600,
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_token_response

        # Mock rate limit response
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_get.return_value = mock_response

        with pytest.raises(GoCardlessRateLimitError):
            gocardless_creds.make_get_request("https://api.example.com/test")


class TestMakePostRequest:
    """Tests for make_post_request method."""

    @patch("src.providers.gocardless.api.core.requests.post")
    def test_make_post_request_success(
        self, mock_post: MagicMock, gocardless_creds: GoCardlessCredentials
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

        mock_post.side_effect = [mock_token_response, mock_post_response]

        result = gocardless_creds.make_post_request(
            "https://api.example.com/create", body={"name": "test"}
        )

        assert result == {"id": "new-resource"}
        # Second call should have timeout
        call_kwargs = mock_post.call_args_list[1][1]
        assert call_kwargs["timeout"] == REQUEST_TIMEOUT

    @patch("src.providers.gocardless.api.core.requests.post")
    def test_make_post_request_rate_limit(
        self, mock_post: MagicMock, gocardless_creds: GoCardlessCredentials
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

        mock_post.side_effect = [mock_token_response, mock_rate_limit_response]

        with pytest.raises(GoCardlessRateLimitError):
            gocardless_creds.make_post_request("https://api.example.com/create")


class TestMakeDeleteRequest:
    """Tests for make_delete_request method."""

    @patch("src.providers.gocardless.api.core.requests.post")
    @patch("src.providers.gocardless.api.core.requests.delete")
    def test_make_delete_request_success(
        self,
        mock_delete: MagicMock,
        mock_post: MagicMock,
        gocardless_creds: GoCardlessCredentials,
    ) -> None:
        """Test successful DELETE request."""
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access": "test_token",
            "access_expires": 3600,
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_token_response

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"deleted": True}
        mock_response.raise_for_status = MagicMock()
        mock_delete.return_value = mock_response

        result = gocardless_creds.make_delete_request("https://api.example.com/resource/123")

        assert result == {"deleted": True}
        call_kwargs = mock_delete.call_args[1]
        assert call_kwargs["timeout"] == REQUEST_TIMEOUT

    @patch("src.providers.gocardless.api.core.requests.post")
    @patch("src.providers.gocardless.api.core.requests.delete")
    def test_make_delete_request_rate_limit(
        self,
        mock_delete: MagicMock,
        mock_post: MagicMock,
        gocardless_creds: GoCardlessCredentials,
    ) -> None:
        """Test rate limit handling on DELETE request."""
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access": "test_token",
            "access_expires": 3600,
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_token_response

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_delete.return_value = mock_response

        with pytest.raises(GoCardlessRateLimitError):
            gocardless_creds.make_delete_request("https://api.example.com/resource/123")


class TestMakePutRequest:
    """Tests for make_put_request method."""

    @patch("src.providers.gocardless.api.core.requests.post")
    @patch("src.providers.gocardless.api.core.requests.put")
    def test_make_put_request_success(
        self,
        mock_put: MagicMock,
        mock_post: MagicMock,
        gocardless_creds: GoCardlessCredentials,
    ) -> None:
        """Test successful PUT request."""
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access": "test_token",
            "access_expires": 3600,
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_token_response

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"updated": True}
        mock_response.raise_for_status = MagicMock()
        mock_put.return_value = mock_response

        result = gocardless_creds.make_put_request(
            "https://api.example.com/resource/123", body={"name": "updated"}
        )

        assert result == {"updated": True}
        call_kwargs = mock_put.call_args[1]
        assert call_kwargs["timeout"] == REQUEST_TIMEOUT

    @patch("src.providers.gocardless.api.core.requests.post")
    @patch("src.providers.gocardless.api.core.requests.put")
    def test_make_put_request_rate_limit(
        self,
        mock_put: MagicMock,
        mock_post: MagicMock,
        gocardless_creds: GoCardlessCredentials,
    ) -> None:
        """Test rate limit handling on PUT request."""
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access": "test_token",
            "access_expires": 3600,
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_token_response

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_put.return_value = mock_response

        with pytest.raises(GoCardlessRateLimitError):
            gocardless_creds.make_put_request("https://api.example.com/resource/123")
