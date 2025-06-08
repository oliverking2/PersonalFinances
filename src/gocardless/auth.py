"""Module containing the Auth for GoCardless."""

import os

import dotenv


class GoCardlessCredentials:
    """GoCardless Credentials Class."""

    def __init__(self) -> None:
        """Initialise the credentials class."""
        dotenv.load_dotenv()

        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
