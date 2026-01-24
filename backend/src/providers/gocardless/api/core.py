"""Module containing the Auth for GoCardless."""

import os
import time
from typing import Any

import requests
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from src.utils.logging import setup_dagster_logger

logger = setup_dagster_logger(__name__)


RATE_LIMIT_STATUS_CODE = 429
REQUEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
SERVER_ERROR_MIN = 500
SERVER_ERROR_MAX = 600


class GoCardlessError(Exception):
    """Custom exception class for GoCardless API errors.

    This exception is raised when GoCardless API operations fail.
    """


class GoCardlessRateLimitError(GoCardlessError):
    """Custom exception class for GoCardless API Rate Limit errors."""


def _is_retryable_error(exception: BaseException) -> bool:
    """Determine if an exception should trigger a retry.

    Retries on:
    - Connection errors (network issues)
    - Timeout errors
    - Server errors (5xx status codes)

    :param exception: The exception to check.
    :returns: True if the request should be retried.
    """
    if isinstance(exception, requests.exceptions.ConnectionError):
        return True
    if isinstance(exception, requests.exceptions.Timeout):
        return True
    if isinstance(exception, requests.exceptions.HTTPError):
        response = exception.response
        if response is not None and SERVER_ERROR_MIN <= response.status_code < SERVER_ERROR_MAX:
            return True
    return False


def _log_retry(retry_state: Any) -> None:
    """Log retry attempts for debugging.

    :param retry_state: The tenacity retry state.
    """
    exception = retry_state.outcome.exception()
    attempt = retry_state.attempt_number
    logger.warning(f"Request failed (attempt {attempt}/{MAX_RETRIES}): {exception!s}")


class GoCardlessCredentials:
    """GoCardless API credentials manager.

    Handles authentication and token management for GoCardless API access.
    Automatically refreshes access tokens when they expire.
    """

    def __init__(self) -> None:
        """Initialise the credentials class.

        :raises EnvironmentError: If required environment variables are not set.
        """
        logger.debug("Initialising GoCardless credentials")

        secret_id = os.environ.get("GC_SECRET_ID")
        secret_key = os.environ.get("GC_SECRET_KEY")

        if not secret_id or not secret_key:
            raise OSError("GC_SECRET_ID and GC_SECRET_KEY environment variables must be set")

        self._secret_id: str = secret_id
        self._secret_key: str = secret_key

        self._access_token: str | None = None
        self._access_token_expiry: float | None = None

        self._session = requests.Session()

        logger.info("GoCardless credentials initialised successfully")

    def _get_access_token(self) -> str:
        """Fetch a new access token from GoCardless API.

        :returns: New access token string.
        :raises requests.RequestException: If API request fails.
        :raises KeyError: If response doesn't contain expected fields.
        """
        logger.debug("Requesting new access token from GoCardless API")
        payload = {
            "secret_id": self._secret_id,
            "secret_key": self._secret_key,
        }

        try:
            response = self._session.post(
                "https://bankaccountdata.gocardless.com/api/v2/token/new/",
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            response_json = response.json()

            self._access_token = response_json["access"]
            self._access_token_expiry = time.time() + response_json["access_expires"] - 10

            logger.info("Successfully obtained new access token")
            return self._access_token
        except requests.exceptions.Timeout:
            logger.error(f"Token request timed out after {REQUEST_TIMEOUT}s")
            raise
        except requests.RequestException as e:
            logger.error(f"Failed to obtain access token: {e}")
            raise
        except KeyError as e:
            logger.error(f"Unexpected response format from GoCardless API: {e}")
            raise

    @property
    def access_token(self) -> str:
        """Get a valid access token, refreshing if necessary.

        Automatically handles token expiry and refreshes tokens when needed.

        :returns: Valid access token string.
        :raises ValueError: If token cannot be obtained.
        """
        if self._access_token_expiry is None:
            # initial run, get a token
            logger.debug("No token expiry set, fetching initial token")
            return self._get_access_token()

        if time.time() > self._access_token_expiry:
            # if expired, get a new one
            logger.debug("Access token expired, refreshing")
            return self._get_access_token()

        if self._access_token is not None:
            logger.debug("Using existing valid access token")
            return self._access_token

        logger.error("Access token failure - unable to obtain valid token")
        raise ValueError("Access Token Failure.")

    def _check_rate_limit(self, response: requests.Response) -> None:
        """Check if response indicates rate limiting.

        :param response: The HTTP response to check.
        :raises GoCardlessRateLimitError: If rate limited.
        """
        if response.status_code == RATE_LIMIT_STATUS_CODE:
            raise GoCardlessRateLimitError(f"Rate limited by GoCardless API: {response.text}")

    @retry(
        retry=retry_if_exception(_is_retryable_error),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=_log_retry,
        reraise=True,
    )
    def make_get_request(
        self, url: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Make a GET request to the specified URL using the current access token.

        Automatically retries on transient failures with exponential backoff.

        :param url: The URL to request.
        :param params: Optional query parameters.
        :returns: Parsed JSON response.
        :raises GoCardlessRateLimitError: If rate limited.
        :raises requests.RequestException: If request fails after retries.
        """
        r = self._session.get(
            url,
            headers={"Authorization": f"Bearer {self.access_token}"},
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        self._check_rate_limit(r)
        r.raise_for_status()

        return r.json()

    @retry(
        retry=retry_if_exception(_is_retryable_error),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=_log_retry,
        reraise=True,
    )
    def make_post_request(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a POST request to the specified URL using the current access token.

        Automatically retries on transient failures with exponential backoff.

        :param url: The URL to request.
        :param params: Optional query parameters.
        :param body: Optional JSON body.
        :returns: Parsed JSON response.
        :raises GoCardlessRateLimitError: If rate limited.
        :raises requests.RequestException: If request fails after retries.
        """
        r = self._session.post(
            url,
            headers={"Authorization": f"Bearer {self.access_token}"},
            params=params,
            json=body,
            timeout=REQUEST_TIMEOUT,
        )
        self._check_rate_limit(r)
        r.raise_for_status()

        return r.json()

    @retry(
        retry=retry_if_exception(_is_retryable_error),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=_log_retry,
        reraise=True,
    )
    def make_delete_request(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a DELETE request to the specified URL using the current access token.

        Automatically retries on transient failures with exponential backoff.

        :param url: The URL to request.
        :param params: Optional query parameters.
        :returns: Parsed JSON response.
        :raises GoCardlessRateLimitError: If rate limited.
        :raises requests.RequestException: If request fails after retries.
        """
        r = self._session.delete(
            url,
            headers={"Authorization": f"Bearer {self.access_token}"},
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        self._check_rate_limit(r)
        r.raise_for_status()

        return r.json()

    @retry(
        retry=retry_if_exception(_is_retryable_error),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=_log_retry,
        reraise=True,
    )
    def make_put_request(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a PUT request to the specified URL using the current access token.

        Automatically retries on transient failures with exponential backoff.

        :param url: The URL to request.
        :param params: Optional query parameters.
        :param body: Optional JSON body.
        :returns: Parsed JSON response.
        :raises GoCardlessRateLimitError: If rate limited.
        :raises requests.RequestException: If request fails after retries.
        """
        r = self._session.put(
            url,
            headers={"Authorization": f"Bearer {self.access_token}"},
            params=params,
            json=body,
            timeout=REQUEST_TIMEOUT,
        )
        self._check_rate_limit(r)
        r.raise_for_status()

        return r.json()
