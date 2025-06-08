"""Module containing the Auth for GoCardless."""

import os
import time
from typing import Optional

from dotenv import load_dotenv
import requests


class GoCardlessError(Exception):
    """GoCardless Error Class."""


class GoCardlessCredentials:
    """GoCardless Credentials Class."""

    def __init__(self) -> None:
        """Initialise the credentials class."""
        load_dotenv()

        secret_id = os.getenv("SECRET_ID")
        secret_key = os.getenv("SECRET_KEY")

        if secret_id is None:
            raise EnvironmentError("SECRET_ID not set.")
        if secret_key is None:
            raise EnvironmentError("SECRET_KEY not set.")

        self.secret_id: str = secret_id
        self.secret_key: str = secret_key

        self._access_token: Optional[str] = None
        self.access_token_expiry: Optional[float] = None

    def get_access_token(self) -> str:
        """Get the access token."""
        payload = {
            "secret_id": self.secret_id,
            "secret_key": self.secret_key,
        }
        response = requests.post(
            "https://bankaccountdata.gocardless.com/api/v2/token/new/", json=payload
        )
        response.raise_for_status()

        response_json = response.json()

        self._access_token = response_json["access"]
        self.access_token_expiry = time.time() + response_json["access_expires"] - 10

        return self._access_token

    @property
    def access_token(self) -> str:
        """Get the access token."""
        if self.access_token_expiry is None:
            # initial run, get a token
            return self.get_access_token()

        if time.time() > self.access_token_expiry:
            # if expired, get a new one
            return self.get_access_token()

        if self._access_token is not None:
            return self._access_token

        raise ValueError("Access Token Failure.")


if __name__ == "__main__":
    creds = GoCardlessCredentials()
    print(creds.access_token)
