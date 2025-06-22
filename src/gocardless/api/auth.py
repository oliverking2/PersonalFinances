"""Module containing the Auth for GoCardless."""

import logging
import os
import time
from typing import Optional

from dotenv import load_dotenv
import requests

logger = logging.getLogger(__name__)


class GoCardlessError(Exception):
    """Custom exception class for GoCardless API errors.

    This exception is raised when GoCardless API operations fail.
    """


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
        load_dotenv()

        secret_id = os.getenv("GOCARDLESS_API_SECRET_ID")
        secret_key = os.getenv("GOCARDLESS_API_SECRET_KEY")

        if secret_id is None:
            logger.error("GOCARDLESS_API_SECRET_ID environment variable not set")
            raise EnvironmentError("GOCARDLESS_API_SECRET_ID not set.")
        if secret_key is None:
            logger.error("GOCARDLESS_API_SECRET_KEY environment variable not set")
            raise EnvironmentError("GOCARDLESS_API_SECRET_KEY not set.")

        self.secret_id: str = secret_id
        self.secret_key: str = secret_key

        self._access_token: Optional[str] = None
        self.access_token_expiry: Optional[float] = None

        logger.info("GoCardless credentials initialised successfully")

    def get_access_token(self) -> str:
        """Fetch a new access token from GoCardless API.

        :returns: New access token string
        :raises requests.RequestException: If API request fails
        :raises KeyError: If response doesn't contain expected fields
        """
        logger.debug("Requesting new access token from GoCardless API")
        payload = {
            "secret_id": self.secret_id,
            "secret_key": self.secret_key,
        }

        try:
            response = requests.post(
                "https://bankaccountdata.gocardless.com/api/v2/token/new/", json=payload
            )
            response.raise_for_status()

            response_json = response.json()

            self._access_token = response_json["access"]
            self.access_token_expiry = time.time() + response_json["access_expires"] - 10

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
        if self.access_token_expiry is None:
            # initial run, get a token
            logger.debug("No token expiry set, fetching initial token")
            return self.get_access_token()

        if time.time() > self.access_token_expiry:
            # if expired, get a new one
            logger.debug("Access token expired, refreshing")
            return self.get_access_token()

        if self._access_token is not None:
            logger.debug("Using existing valid access token")
            return self._access_token

        logger.error("Access token failure - unable to obtain valid token")
        raise ValueError("Access Token Failure.")


if __name__ == "__main__":
    creds = GoCardlessCredentials()
    print(creds.access_token)
