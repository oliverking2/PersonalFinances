"""Module containing functions for managing requisitions with GoCardless.

This module provides functions to interact with GoCardless Bank Account Data API
for requisition management, including fetching and deleting requisition data.
"""

from typing import Dict, Any, List


from src.gocardless.api.core import GoCardlessCredentials

# Configure logging

from src.utils.logging import get_logger

logger = get_logger("gocardless_api_requisition")


def get_all_requisition_data(creds: GoCardlessCredentials) -> List[Dict[str, Any]]:
    """Fetch all requisition JSON data from GoCardless.

    Retrieves the requisition data, including its status and linked account IDs, from the
    GoCardless Bank Account Data API.

    :param creds: GoCardlessCredentials object.
    :returns: The JSON response as a dictionary.
    :raises requests.RequestException: If there's an error communicating with the GoCardless API.
    """
    logger.info("Fetching requisition data from GoCardless")
    url = "https://bankaccountdata.gocardless.com/api/v2/requisitions"

    return creds.make_get_request(url)["results"]


def get_requisition_data_by_id(creds: GoCardlessCredentials, req_id: str) -> Dict[str, Any]:
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

    return creds.make_get_request(url)


def delete_requisition_data_by_id(creds: GoCardlessCredentials, req_id: str) -> Dict[str, Any]:
    """Delete a requisition from GoCardless.

    :param req_id: The requisition ID to delete
    :param creds: GoCardlessCredentials object for authentication
    :returns: The JSON response as a dictionary
    :raises requests.RequestException: If there's an error communicating with the GoCardless API
    """
    logger.info(f"Deleting requisition data from GoCardless for ID: {req_id}")
    url = f"https://bankaccountdata.gocardless.com/api/v2/requisitions/{req_id}"

    return creds.make_delete_request(url)


if __name__ == "__main__":
    creds = GoCardlessCredentials()
    print(get_all_requisition_data(creds))
