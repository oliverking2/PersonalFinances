"""Module containing functions for managing requisitions with GoCardless.

This module provides functions to interact with GoCardless Bank Account Data API
for requisition management, including fetching and deleting requisition data.
"""

from typing import Dict, Any, List

import requests

from src.gocardless.api.auth import GoCardlessCredentials

# Configure logging

from src.utils.logging import get_logger

logger = get_logger("gocardless_api_requisition")


def fetch_all_requisition_data(creds: GoCardlessCredentials) -> List[Dict[str, Any]]:
    """Fetch all requisition JSON data from GoCardless.

    Retrieves the requisition data, including its status and linked account IDs, from the
    GoCardless Bank Account Data API.

    :param creds: GoCardlessCredentials object.
    :returns: The JSON response as a dictionary.
    :raises requests.RequestException: If there's an error communicating with the GoCardless API.
    """
    logger.info("Fetching requisition data from GoCardless")
    url = "https://bankaccountdata.gocardless.com/api/v2/requisitions"
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {creds.access_token}"})
        r.raise_for_status()
        logger.debug("Successfully retrieved requisition data")
        return r.json()["results"]
    except requests.RequestException as e:
        logger.error(f"Failed to fetch requisition data: {e!s}")
        raise


def fetch_requisition_data_by_id(creds: GoCardlessCredentials, req_id: str) -> Dict[str, Any]:
    """Fetch the full requisition JSON from GoCardless.

    Retrieves the requisition data, including its status and linked account IDs, from the
    GoCardless Bank Account Data API.

    :param req_id: The requisition ID to retrieve.
    :param creds: GoCardlessCredentials object.
    :returns: The JSON response as a dictionary.
    :raises requests.RequestException: If there's an error communicating with the GoCardless API.
    """
    logger.info(f"Fetching requisition data from GoCardless for ID: {req_id}")
    url = f"https://bankaccountdata.gocardless.com/api/v2/requisitions/{req_id}"
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {creds.access_token}"})
        r.raise_for_status()
        logger.debug(f"Successfully retrieved requisition data for ID: {req_id}")
        return r.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch requisition data for ID {req_id}: {e!s}")
        raise


def delete_requisition_data_by_id(creds: GoCardlessCredentials, req_id: str) -> Dict[str, Any]:
    """Delete a requisition from GoCardless.

    :param req_id: The requisition ID to delete
    :param creds: GoCardlessCredentials object for authentication
    :returns: The JSON response as a dictionary
    :raises requests.RequestException: If there's an error communicating with the GoCardless API
    """
    logger.info(f"Deleting requisition data from GoCardless for ID: {req_id}")
    url = f"https://bankaccountdata.gocardless.com/api/v2/requisitions/{req_id}"
    try:
        r = requests.delete(url, headers={"Authorization": f"Bearer {creds.access_token}"})
        r.raise_for_status()
        logger.info(f"Successfully deleted requisition data for ID: {req_id}")
        return r.json()
    except requests.RequestException as e:
        logger.error(f"Failed to delete requisition data for ID {req_id}: {e!s}")
        raise
