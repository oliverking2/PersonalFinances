"""Module containing the Auth for GoCardless."""

import time
from typing import Optional, Dict, Any, List, Union

from dotenv import load_dotenv
import requests
import boto3

from src.aws.ssm_parameters import get_parameter_data_from_ssm
from src.utils.logging import setup_dagster_logger

logger = setup_dagster_logger(__name__)


RATE_LIMIT_STATUS_CODE = 429


class GoCardlessError(Exception):
    """Custom exception class for GoCardless API errors.

    This exception is raised when GoCardless API operations fail.
    """


class GoCardlessRateLimitError(GoCardlessError):
    """Custom exception class for GoCardless API Rate Limit errors."""


class GoCardlessCredentials:
    """GoCardless API credentials manager.

    Handles authentication and token management for GoCardless API access.
    Automatically refreshes access tokens when they expire.
    """

    def __init__(self) -> None:
        """Initialise the credentials class.

        :raises EnvironmentError: If required environment variables are not set
        """
        logger.debug("Initialising GoCardless credentials")

        ssm_client = boto3.client("ssm")
        load_dotenv()

        secret_id = get_parameter_data_from_ssm(ssm_client, "/secrets/gocardless/secret_id")
        secret_key = get_parameter_data_from_ssm(ssm_client, "/secrets/gocardless/secret_key")

        self._secret_id: str = secret_id
        self._secret_key: str = secret_key

        self._access_token: Optional[str] = None
        self._access_token_expiry: Optional[float] = None

        logger.info("GoCardless credentials initialised successfully")

    def _get_access_token(self) -> str:
        """Fetch a new access token from GoCardless API.

        :returns: New access token string
        :raises requests.RequestException: If API request fails
        :raises KeyError: If response doesn't contain expected fields
        """
        logger.debug("Requesting new access token from GoCardless API")
        payload = {
            "secret_id": self._secret_id,
            "secret_key": self._secret_key,
        }

        try:
            response = requests.post(
                "https://bankaccountdata.gocardless.com/api/v2/token/new/", json=payload
            )
            response.raise_for_status()

            response_json = response.json()

            self._access_token = response_json["access"]
            self._access_token_expiry = time.time() + response_json["access_expires"] - 10

            logger.info("Successfully obtained new access token")
            return self._access_token
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

        :returns: Valid access token string
        :raises ValueError: If token cannot be obtained
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

    def make_get_request(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Make a GET request to the specified URL using the current access token."""
        r = requests.get(
            url, headers={"Authorization": f"Bearer {self.access_token}"}, params=params
        )
        if r.status_code == RATE_LIMIT_STATUS_CODE:
            raise GoCardlessRateLimitError(f"Error fetching data from GoCardless API: {r.text}")

        r.raise_for_status()

        return r.json()

    def make_post_request(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a POST request to the specified URL using the current access token."""
        r = requests.post(
            url, headers={"Authorization": f"Bearer {self.access_token}"}, params=params, json=body
        )
        r.raise_for_status()

        return r.json()

    def make_delete_request(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a DELETE request to the specified URL using the current access token."""
        r = requests.delete(
            url, headers={"Authorization": f"Bearer {self.access_token}"}, params=params
        )
        r.raise_for_status()

        return r.json()

    def make_put_request(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a PUT request to the specified URL using the current access token."""
        r = requests.put(
            url, headers={"Authorization": f"Bearer {self.access_token}"}, params=params, json=body
        )
        r.raise_for_status()

        return r.json()


if __name__ == "__main__":
    creds = GoCardlessCredentials()
    print(creds.access_token)
