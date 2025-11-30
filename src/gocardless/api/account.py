"""Module containing functions for managing bank accounts with GoCardless.

This module provides functions to interact with GoCardless Bank Account Data API
for account management, including fetching account details and information.
"""

from typing import Dict, Any
import logging

import requests

from src.gocardless.api.auth import GoCardlessCredentials


logger = logging.getLogger("gocardless_api_account")


def fetch_account_data_by_id(creds: GoCardlessCredentials, account_id: str) -> Dict[str, Any]:
    """Fetch a single bank account's details from GoCardless.

    Retrieves detailed information for the given bank account ID from the GoCardless Bank Account Data API.

    :param creds: GoCardlessCredentials object for authentication
    :param account_id: The unique identifier of the bank account
    :returns: The account details as a dictionary
    :raises requests.RequestException: If there's an error communicating with the GoCardless API
    """
    logger.info(f"Fetching account details from GoCardless for account ID: {account_id}")
    url = f"https://bankaccountdata.gocardless.com/api/v2/accounts/{account_id}"
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {creds.access_token}"})
        r.raise_for_status()
        logger.debug(f"Successfully retrieved account details for ID: {account_id}")
        return r.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch account details for ID {account_id}: {e!s}")
        raise
