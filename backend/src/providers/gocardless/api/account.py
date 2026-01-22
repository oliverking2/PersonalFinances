"""Module containing functions for managing bank accounts with GoCardless.

This module provides functions to interact with GoCardless Bank Account Data API
for account management, including fetching account details and information.
"""

from typing import Any

from src.providers.gocardless.api.core import GoCardlessCredentials
from src.utils.logging import setup_dagster_logger

logger = setup_dagster_logger("gocardless_api_account")


def get_account_metadata_by_id(creds: GoCardlessCredentials, account_id: str) -> dict[str, Any]:
    """Fetch a single bank account's details from GoCardless.

    Retrieves detailed information for the given bank account ID from the GoCardless Bank Account Data API.

    :param creds: GoCardlessCredentials object for authentication
    :param account_id: The unique identifier of the bank account
    :returns: The account details as a dictionary
    :raises requests.RequestException: If there's an error communicating with the GoCardless API
    """
    logger.info(f"Fetching account details from GoCardless for account ID: {account_id}")
    url = f"https://bankaccountdata.gocardless.com/api/v2/accounts/{account_id}"

    resp = creds.make_get_request(url)
    if not isinstance(resp, dict):
        raise ValueError("Response from GoCardless not in expected format.")

    return resp


def get_transaction_data_by_id(
    creds: GoCardlessCredentials, account_id: str, date_from: str, date_to: str
) -> dict[str, Any]:
    """Fetch transaction data from the GoCardless API for the specified account and date range.

    The function communicates with the GoCardless API to retrieve transaction details of the given
    account within the defined date range. Returns a list of transaction records containing details
    such as date, amount, and other related metadata. It raises an exception if the HTTP request
    fails.

    :param creds: GoCardlessCredentials object for authentication
    :param account_id: The unique identifier of the bank account
    :param date_from: The start date (inclusive) of the transaction range, in YYYY-MM-DD format
    :param date_to: The end date (inclusive) of the transaction range, in YYYY-MM-DD format
    :returns: A list of transaction records as dictionaries

    """
    logger.info("Fetching transaction data from GoCardless")
    url = f"https://bankaccountdata.gocardless.com/api/v2/accounts/{account_id}/transactions"
    params = {"date_from": date_from, "date_to": date_to}

    resp = creds.make_get_request(url, params=params)
    if not isinstance(resp, dict):
        raise ValueError("Response from GoCardless not in expected format.")

    return resp


def get_balance_data_by_id(creds: GoCardlessCredentials, account_id: str) -> dict[str, Any]:
    """Fetch balance data from the GoCardless API for the specified account.

    :param creds: GoCardlessCredentials object for authentication
    :param account_id: The unique identifier of the bank account
    :returns: A dictionary containing balance information
    """
    logger.info("Fetching balance data from GoCardless")
    url = f"https://bankaccountdata.gocardless.com/api/v2/accounts/{account_id}/balances"
    resp = creds.make_get_request(url)
    if not isinstance(resp, dict):
        raise ValueError("Response from GoCardless not in expected format.")

    return resp


def get_account_details_by_id(creds: GoCardlessCredentials, account_id: str) -> dict[str, Any]:
    """Fetch account details from the GoCardless API for the specified account.

    :param creds: GoCardlessCredentials object for authentication
    :param account_id: The unique identifier of the bank account
    :returns: A dictionary containing account details
    """
    logger.info("Fetching account details from GoCardless")
    url = f"https://bankaccountdata.gocardless.com/api/v2/accounts/{account_id}/details"
    resp = creds.make_get_request(url)
    if not isinstance(resp, dict):
        raise ValueError("Response from GoCardless not in expected format.")

    return resp


if __name__ == "__main__":
    creds = GoCardlessCredentials()
    print(
        get_transaction_data_by_id(
            creds, "b200ae31-e334-4918-814e-147aab73318b", "2025-11-01", "2025-11-30"
        )
    )
