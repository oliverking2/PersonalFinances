"""Module containing functions for managing requisitions with GoCardless.

This module provides functions to interact with GoCardless Bank Account Data API
for requisition management, including fetching and deleting requisition data.
"""

from typing import Any

from src.gocardless.api.core import GoCardlessCredentials

# Configure logging
from src.utils.logging import setup_dagster_logger

logger = setup_dagster_logger("gocardless_api_requisition")


def get_all_requisition_data(creds: GoCardlessCredentials) -> list[dict[str, Any]]:
    """Fetch all requisition JSON data from GoCardless.

    Retrieves the requisition data, including its status and linked account IDs, from the
    GoCardless Bank Account Data API.

    :param creds: GoCardlessCredentials object.
    :returns: The JSON response as a dictionary.
    :raises requests.RequestException: If there's an error communicating with the GoCardless API.
    """
    logger.info("Fetching requisition data from GoCardless")
    url = "https://bankaccountdata.gocardless.com/api/v2/requisitions"

    resp = creds.make_get_request(url)
    if not isinstance(resp, dict):
        raise ValueError("Response from GoCardless not in expected format.")

    return resp["results"]


def get_requisition_data_by_id(creds: GoCardlessCredentials, req_id: str) -> dict[str, Any]:
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

    resp = creds.make_get_request(url)
    if not isinstance(resp, dict):
        raise ValueError("Response from GoCardless not in expected format.")

    return resp


def delete_requisition_data_by_id(creds: GoCardlessCredentials, req_id: str) -> dict[str, Any]:
    """Delete a requisition from GoCardless.

    :param req_id: The requisition ID to delete
    :param creds: GoCardlessCredentials object for authentication
    :returns: The JSON response as a dictionary
    :raises requests.RequestException: If there's an error communicating with the GoCardless API
    """
    logger.info(f"Deleting requisition data from GoCardless for ID: {req_id}")
    url = f"https://bankaccountdata.gocardless.com/api/v2/requisitions/{req_id}"

    return creds.make_delete_request(url)


def create_link(creds: GoCardlessCredentials, callback: str, institution_id: str) -> dict[str, Any]:
    """Create a link with GoCardless.

    :param creds: GoCardlessCredentials object for authentication
    :param callback: The callback URL to redirect to after the user completes the requisition flow
    :param institution_id: The ID of the institution to connect to
    :returns: The JSON response as a dictionary
    """
    payload = {"redirect": callback, "institution_id": institution_id}

    return creds.make_post_request(
        "https://bankaccountdata.gocardless.com/api/v2/requisitions/", body=payload
    )


if __name__ == "__main__":
    creds = GoCardlessCredentials()
    print(get_all_requisition_data(creds))
